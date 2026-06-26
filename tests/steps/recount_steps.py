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
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, parsers, then, when

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import document_to_state, load_document, validate_state

if typ.TYPE_CHECKING:
    from pathlib import Path

# The two drafted chapters' true word counts; the hand-typed ``[word_counts]`` is
# set deliberately wrong so the recount has something to correct.
_TRUE_COUNTS: tuple[int, int] = (3, 5)
_TARGET_WORDS = 80000


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree and the exit code captured across the scenario steps."""

    working: Path
    exit_code: int | None = None
    messages: tuple[str, ...] = ()
    before: bytes | None = None


def _run_recount(working: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``recount`` through ``run`` from ``working.parent``; return the code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["recount"],
            RunContext(command="novel state", working_dir="working", human=False),
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


def _gate_chapter(number: int, draft_words: int) -> wc.ChapterSpec:
    """Return a coherent single chapter drafting ``draft_words`` against the target."""
    return wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=_TARGET_WORDS,
        draft_words=draft_words,
        has_done_flag=False,
    )


@then(parsers.parse('the recount message contains "{needle}"'))
def asserts_message_contains(outcome: _Outcome, needle: str) -> None:
    """Assert at least one envelope ``messages`` line contains ``needle``."""
    assert any(needle in line for line in outcome.messages), (
        f"no message contained {needle!r}; messages were {outcome.messages!r}"
    )


def _gate_breach_spec(
    *,
    draft_words: int,
    by_chapter_override: dict[str, int],
    current_words_override: int,
    gates: tuple[bool, bool, bool],
) -> wc.WorkingTreeSpec:
    """Return a one-chapter drafting spec whose recount will breach a knitting gate.

    The chapter drafts ``draft_words`` on disk while the hand-typed
    ``[word_counts]`` records ``by_chapter_override``/``current_words_override``,
    chosen so the prior state passes ``validate_state`` with ``gates`` — so the
    refusal is the *recount* re-deriving the counts, not a pre-existing breach.
    """
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=(_gate_chapter(1, draft_words),),
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=1,
        by_chapter_override=by_chapter_override,
        current_words_override=current_words_override,
        done_30=gates[0],
        done_50=gates[1],
        done_80=gates[2],
    )


@given(
    "a working tree whose recorded done_80 gate no longer matches its shrunken drafts",
    target_fixture="outcome",
)
def downward_gate_tree(tmp_path: Path) -> _Outcome:
    """Build a tree whose recount drops the ratio to 0.55 with done_80 true.

    The hand-typed counts cross 0.80 so the prior state is coherent with done_80
    true, but the drafts recount to 0.55 — isolating the single downward breach.

    Returns
    -------
    _Outcome
        The built ``working/`` path and its prior bytes.
    """
    return _coherent_gate_tree(
        tmp_path,
        _gate_breach_spec(
            draft_words=44000,
            by_chapter_override={"01": 68800},
            current_words_override=68800,
            gates=(True, True, True),
        ),
    )


@then("state.toml is left byte-for-byte unchanged")
def asserts_refused_state_unchanged(outcome: _Outcome) -> None:
    """Assert the refused recount left ``state.toml`` byte-for-byte intact."""
    assert outcome.before is not None, "the refusal scenario must record prior bytes"
    after = (outcome.working / "state.toml").read_bytes()
    assert after == outcome.before, "a refused recount must leave state.toml intact"


@then(parsers.parse('the recount message does not contain "{needle}"'))
def asserts_message_absent(outcome: _Outcome, needle: str) -> None:
    """Assert no envelope ``messages`` line contains ``needle``.

    Proves the downward path never prescribes the upward repair verb — the
    pre-mortem's most likely incident (design-review B2).
    """
    assert all(needle not in line for line in outcome.messages), (
        f"a message wrongly contained {needle!r}; messages were {outcome.messages!r}"
    )


@then("recount exits 3")
def asserts_recount_exit_three(outcome: _Outcome) -> None:
    """Assert the recount exited ``3`` (state error), never the benign ``1``."""
    assert outcome.exit_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {outcome.exit_code}"
    )


def _coherent_gate_tree(tmp_path: Path, spec: wc.WorkingTreeSpec) -> _Outcome:
    """Build ``spec`` and assert it is coherent before recount; return the outcome.

    The prior state must pass ``validate_state`` so the exit-3 refusal under test is
    the *recount* re-deriving the counts, not a pre-existing breach.
    """
    working = wc.build_working_tree(spec, tmp_path)
    prior = document_to_state(load_document(working / "state.toml"))
    assert not validate_state(prior), (
        "the hand-typed prior state must pass validate_state before recount"
    )
    return _Outcome(working=working, before=(working / "state.toml").read_bytes())


@given(
    "a working tree whose drafts have grown past the 30% knitting threshold while "
    "done_30 is still false",
    target_fixture="outcome",
)
def upward_gate_tree(tmp_path: Path) -> _Outcome:
    """Build a tree whose recount lifts the ratio to 0.34 with done_30 false.

    Returns
    -------
    _Outcome
        The built ``working/`` path and its prior bytes.
    """
    return _coherent_gate_tree(
        tmp_path,
        _gate_breach_spec(
            draft_words=27200,
            by_chapter_override={"01": 100},
            current_words_override=100,
            gates=(False, False, False),
        ),
    )


@when("recount runs against that tree")
def run_recount_capturing(
    outcome: _Outcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive ``recount`` and capture both the exit code and the envelope messages.

    Shares the ``When`` phrasing with the success scenario's run step; pytest-bdd
    binds whichever step the active scenario's ``Given`` produced. The exit-3
    envelope is printed to stdout by ``run``, so ``capsys`` reads its ``messages``.
    """
    outcome.exit_code = _run_recount(outcome.working, monkeypatch)
    envelope = json.loads(capsys.readouterr().out or "{}")
    outcome.messages = tuple(envelope.get("messages", ()))
