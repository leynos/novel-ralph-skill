"""Step definitions for the ``novel-compile`` regeneration scenarios.

These drive ``novel-compile`` against a working tree with three drafted chapters
and a stale ``compiled.md``, and assert the roadmap 4.1.1 success criteria: the
compile exits ``0``, ``working/manuscript/compiled.md`` equals the manifest-ordered
draft concatenation, and a second run over unchanged drafts yields a byte-for-byte
identical file (determinism/idempotence; design §4.3, §10). The empty-manifest
scenario asserts the exit-``3`` refusal writes no ``compiled.md``.

The command is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the contract
tests do, so the externally observable exit code is what the scenario asserts.
The runner step ``chdir``s into the prepared tree's parent first because
``novel-compile`` resolves a cwd-relative ``working/`` (Decision Log D-CWD), as
the recount steps do. Fixture state flows between steps through
``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_compile_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands._compile import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

# The three drafted chapters' word counts; the expected concatenation is exact.
_COUNTS: tuple[int, ...] = (3, 5, 4)
# Deliberately stale bytes for the pre-existing compiled.md, so the compile has
# something to overwrite (and the idempotence assertion is meaningful).
_STALE_COMPILED = "STALE — not the ordered concatenation"


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree and the exit code captured across the scenario steps."""

    working: Path
    exit_code: int | None = None


def _run_compile(working: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``novel-compile`` through ``run`` from ``working.parent``; return code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command="novel-compile", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


def _expected_concatenation() -> str:
    """Return the manifest-ordered draft concatenation the compile must write."""
    return wc.concatenate_drafts([wc.draft_body(count) for count in _COUNTS])


@given(
    "a working tree with three drafted chapters and a stale compiled.md",
    target_fixture="outcome",
)
def drafting_tree_with_stale_compiled(tmp_path: Path) -> _Outcome:
    """Build a three-chapter ``drafting`` tree carrying a stale ``compiled.md``.

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
        for number, count in enumerate(_COUNTS, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        # A stale compiled.md the deterministic compile must overwrite.
        compiled=_STALE_COMPILED,
    )
    return _Outcome(working=wc.build_working_tree(spec, tmp_path))


@given(
    "a working tree whose chapter manifest is empty",
    target_fixture="outcome",
)
def empty_manifest_tree(tmp_path: Path) -> _Outcome:
    """Build a pre-drafting ``premise`` tree (empty manifest, no ``compiled.md``)."""
    return _Outcome(working=wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path))


@when("novel-compile runs against that tree")
def run_compile(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-compile`` through ``run`` and capture the exit code."""
    outcome.exit_code = _run_compile(outcome.working, monkeypatch)


@then("novel-compile exits 0")
def asserts_exit_zero(outcome: _Outcome) -> None:
    """Assert the compile exited ``0`` (success)."""
    assert outcome.exit_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.exit_code}"
    )


@then("novel-compile exits 3")
def asserts_exit_three(outcome: _Outcome) -> None:
    """Assert the compile refused with exit ``3`` (the state channel)."""
    assert outcome.exit_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {outcome.exit_code}"
    )


@then("compiled.md equals the manifest-ordered concatenation of the drafts")
def asserts_ordered_concatenation(outcome: _Outcome) -> None:
    """Assert ``compiled.md`` is the ascending-order draft concatenation."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == _expected_concatenation(), (
        "compiled.md must equal the manifest-ordered draft concatenation"
    )


@then("a second novel-compile leaves compiled.md byte-for-byte unchanged")
def asserts_idempotent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a second compile over unchanged drafts is byte-for-byte identical."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()
    second_code = _run_compile(outcome.working, monkeypatch)
    assert second_code == ExitCode.SUCCESS, (
        f"the second compile should also exit 0, got {second_code}"
    )
    after = compiled.read_bytes()
    assert after == before, "a second compile must leave compiled.md byte-for-byte"


@then("no compiled.md is written")
def asserts_no_compiled(outcome: _Outcome) -> None:
    """Assert the refusal wrote no ``compiled.md``."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    assert not compiled.exists(), "an empty-manifest refusal must write no compiled.md"
