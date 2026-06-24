"""Step definitions for the ``novel-done`` six-clause behavioural scenarios.

These drive the wired ``novel-done`` app against the §1.3.2 corpus trees and
assert the roadmap 3.1.1 success criterion: the predicate exits ``0`` **only** on
the all-six-clauses-hold tree, and exits ``1`` while any single clause is false
(design §4.2, §3.2). The all-hold "exits 0" scenario is the load-bearing half
(R-ALLHOLD); each failer scenario toggles exactly one clause false.

The app is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the contract
and command tests do, so the externally observable exit code and the emitted
envelope are what the scenario asserts. The runner step ``chdir``'s into the
prepared tree's parent first because ``novel-done`` resolves a cwd-relative
``working/`` (Decision Log D-CWD), as the recount steps do. Fixture state flows
between steps through ``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_novel_done_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, parsers, then, when

from novel_ralph_skill.commands._novel_done import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

# The two failer keys whose toggled artefact breaks the ``knitting_gates_passed``
# clause; every other failer key is the clause name it breaks.
_CLAUSE_FOR_FAILER: dict[str, str] = {
    "knitting_review_missing": "knitting_gates_passed",
    "knitting_gate_false": "knitting_gates_passed",
}


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree and the exit code/envelope captured across the steps."""

    working: Path
    exit_code: int | None = None
    envelope: dict[str, object] | None = None


def _run_novel_done(
    working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict[str, object]]:
    """Drive ``novel-done`` from ``working.parent``; return ``(code, envelope)``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command="novel-done", working_dir="working", human=False),
        )
    envelope = json.loads(capsys.readouterr().out)
    return typ.cast("int", excinfo.value.code), envelope


@given("a working tree where all six done clauses hold", target_fixture="outcome")
def all_hold_tree(tmp_path: Path) -> _Outcome:
    """Build the all-six-clauses-hold tree.

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    return _Outcome(working=wc.build_working_tree(wc.DONE_PREDICATE_ALL_HOLD, tmp_path))


@given(
    parsers.parse('a working tree that fails only the "{clause}" clause'),
    target_fixture="outcome",
)
def single_failer_tree(clause: str, tmp_path: Path) -> _Outcome:
    """Build the named single-clause failer tree.

    Returns
    -------
    _Outcome
        The built ``working/`` path for the named failer.
    """
    spec = wc.DONE_PREDICATE_FAILERS[clause]
    return _Outcome(working=wc.build_working_tree(spec, tmp_path))


@given(
    'a working tree whose first chapter has a live "### B1" BLOCKER finding',
    target_fixture="outcome",
)
def live_blocker_finding_tree(tmp_path: Path) -> _Outcome:
    """Build the live-finding tree from real critic-personas-shaped output.

    The first chapter's ``critic-notes.md`` is a ``## BLOCKER`` section with a
    live ``### B1 — …`` finding (``UNRESOLVED_BLOCKER_NOTE``; roadmap 3.1.5), the
    real producer format the old ``startswith("BLOCKER")`` grammar never caught
    (audit-3.1.4 Finding 1). This is the externally observable proof that genuine
    critic output now drives ``novel-done`` to exit ``1``.

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    return _Outcome(
        working=wc.build_working_tree(
            wc.DONE_PREDICATE_FAILERS["no_unresolved_blockers"], tmp_path
        )
    )


@given(
    'a working tree whose first chapter quotes "[resolved]" mid-finding',
    target_fixture="outcome",
)
def incidental_resolved_blocker_tree(tmp_path: Path) -> _Outcome:
    """Build the incidental-resolution tree (the false-clean BLOCKER near-miss).

    The first chapter's ``critic-notes.md`` holds a live ``### B1`` finding whose
    label quotes ``[resolved]`` mid-line, not as the trailing marker, so the
    positional rule keeps it unresolved (D-BLOCKER-POSITIONAL; roadmap 3.1.5).
    This is a deliberate twin of the ``no_unresolved_blockers`` failer, not a new
    member of ``DONE_PREDICATE_FAILERS``.

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    return _Outcome(
        working=wc.build_working_tree(
            wc.DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER, tmp_path
        )
    )


@given(
    "an otherwise-complete working tree whose compiled.md is stale",
    target_fixture="outcome",
)
def sole_stale_compile_tree(tmp_path: Path) -> _Outcome:
    """Build the sole-stale-compile tree (the exit-``4`` carve-out fixture).

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    return _Outcome(
        working=wc.build_working_tree(wc.DONE_PREDICATE_SOLE_STALE_COMPILE, tmp_path)
    )


@given(
    "a mid-draft working tree whose compiled.md is stale",
    target_fixture="outcome",
)
def mid_draft_stale_tree(tmp_path: Path) -> _Outcome:
    """Build the mid-draft-stale tree (a drafting clause unmet plus a stale compile).

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    return _Outcome(
        working=wc.build_working_tree(wc.DONE_PREDICATE_MID_DRAFT_STALE, tmp_path)
    )


@when("novel-done runs against that tree")
def run_novel_done(
    outcome: _Outcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive ``novel-done`` through ``run`` and capture the code and envelope."""
    outcome.exit_code, outcome.envelope = _run_novel_done(
        outcome.working, monkeypatch, capsys
    )


@then("novel-done exits 0")
def asserts_exit_zero(outcome: _Outcome) -> None:
    """Assert the predicate exited ``0`` (every clause holds)."""
    assert outcome.exit_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.exit_code}"
    )


@then("novel-done exits 1")
def asserts_exit_one(outcome: _Outcome) -> None:
    """Assert the predicate exited ``1`` (benign not-yet-done)."""
    assert outcome.exit_code == ExitCode.BENIGN_NEGATIVE, (
        f"expected exit 1, got {outcome.exit_code}"
    )


@then("novel-done exits 4")
def asserts_exit_four(outcome: _Outcome) -> None:
    """Assert the predicate exited ``4`` (the stale-present compile carve-out)."""
    assert outcome.exit_code == ExitCode.ACTIONABLE_FINDING, (
        f"expected exit 4, got {outcome.exit_code}"
    )


@then("every clause in the result is true")
def asserts_all_clauses_true(outcome: _Outcome) -> None:
    """Assert the envelope's ``result`` reports every clause true."""
    assert outcome.envelope is not None
    result = typ.cast("dict[str, object]", outcome.envelope["result"])
    assert all(value is True for value in result.values()), (
        f"expected every clause true, got {result}"
    )


@then(parsers.parse('the result reports "{clause}" false'))
def asserts_clause_false(clause: str, outcome: _Outcome) -> None:
    """Assert the envelope's ``result`` reports the named clause false."""
    assert outcome.envelope is not None
    result = typ.cast("dict[str, object]", outcome.envelope["result"])
    key = _CLAUSE_FOR_FAILER.get(clause, clause)
    assert result[key] is False, f"expected {key!r} false, got {result}"
