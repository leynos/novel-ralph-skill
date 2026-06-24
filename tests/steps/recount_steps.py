"""Step definitions for the ``recount`` re-derivation scenario.

These drive the ``recount`` mutator against a working tree with two drafted
chapters whose hand-typed ``[word_counts]`` are deliberately wrong, and assert the
roadmap success criteria: the recount exits ``0``, ``state.toml`` records the
summed counts derived from the drafts, and a second run over unchanged drafts
yields a byte-for-byte identical ``state.toml`` (idempotence; design §4.1, §5.2
invariant 3, §9).

The mutator is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the contract
tests do, so the externally observable exit code is what the scenario asserts.
The runner step ``chdir``'s into the prepared tree's parent first because
``recount`` resolves a cwd-relative ``working/state.toml`` (Decision Log D-CWD),
as the advance-phase steps do. Fixture state flows between steps through
``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_recount_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import load_document

if typ.TYPE_CHECKING:
    from pathlib import Path

# The two drafted chapters' true word counts; the hand-typed ``[word_counts]`` is
# set deliberately wrong so the recount has something to correct.
_TRUE_COUNTS: tuple[int, int] = (3, 5)


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree and the exit code captured across the scenario steps."""

    working: Path
    exit_code: int | None = None


def _run_recount(working: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``recount`` through ``run`` from ``working.parent``; return the code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["recount"],
            RunContext(command="novel-state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


@given(
    "a working tree with two drafted chapters whose hand-typed counts are wrong",
    target_fixture="outcome",
)
def wrong_count_tree(tmp_path: Path) -> _Outcome:
    """Build a two-chapter ``drafting`` tree with wrong hand-typed counts.

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(_TRUE_COUNTS, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        # Deliberately wrong hand-typed counts the recount must overwrite.
        by_chapter_override={"01": 999, "02": 999},
        current_words_override=1998,
    )
    return _Outcome(working=wc.build_working_tree(spec, tmp_path))


@when("recount runs against that tree")
def run_recount(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``recount`` through ``run`` and capture the exit code."""
    outcome.exit_code = _run_recount(outcome.working, monkeypatch)


@then("recount exits 0")
def asserts_exit_zero(outcome: _Outcome) -> None:
    """Assert the recount exited ``0`` (success)."""
    assert outcome.exit_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.exit_code}"
    )


@then("state.toml records the summed counts derived from the drafts")
def asserts_summed_counts(outcome: _Outcome) -> None:
    """Assert ``[word_counts]`` now matches the drafts: per-chapter and the sum."""
    document = load_document(outcome.working / "state.toml")
    by_chapter = dict(document["word_counts"]["by_chapter"])
    assert by_chapter == {"01": _TRUE_COUNTS[0], "02": _TRUE_COUNTS[1]}, (
        f"by_chapter should match the drafts, got {by_chapter}"
    )
    assert document["word_counts"]["current"] == sum(_TRUE_COUNTS), (
        "current should equal the summed draft counts"
    )


@then("a second recount leaves state.toml byte-for-byte unchanged")
def asserts_idempotent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a second recount over unchanged drafts is byte-for-byte identical."""
    before = (outcome.working / "state.toml").read_bytes()
    second_code = _run_recount(outcome.working, monkeypatch)
    assert second_code == ExitCode.SUCCESS, (
        f"the second recount should also exit 0, got {second_code}"
    )
    after = (outcome.working / "state.toml").read_bytes()
    assert after == before, "a second recount must leave state.toml byte-for-byte"
