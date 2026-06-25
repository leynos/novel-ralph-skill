"""Step definitions for the torn-turn recovery scenario at the command boundary.

These prove the roadmap 6.2.5 success clause: a *real* ``novel-state reconcile``
invocation that crashes mid-write leaves an uncleared ``operation="reconcile"``
``[pending_turn]`` on disk (the on-disk signature of a torn turn), ``check``
reports it (exit ``4`` with a ``complete-pending-turn`` reconciliation), and
``reconcile`` — re-run under the harness re-entry model — recovers it (each run
exits ``0``) until a follow-up ``check`` is coherent (exit ``0``). The crash is
injected at the ``_reconcile._append_recovery_entry`` seam (append-then-raise),
exactly the seam :mod:`tests.test_reconcile_integration` validates, but reached
*through* the command runner rather than the body call: this crosses the
Cyclopts app and the shared ``run`` wrapper, so the torn record is the residue of
an actual mutator invocation at the command boundary (ExecPlan Decisions D-MECH,
D-INPROC), not a record hand-planted into a fixture (Constraint).

Recovery is asserted under a *bounded* re-entry loop, not a single pass: the
crashed ``reconcile`` was repairing stale word-counts, so it leaves its own
``operation="reconcile"`` record over a tree that still needs the recount; the
first recovery clears the leftover record and the second re-applies the recount,
mirroring the harness's idempotent re-entry (ExecPlan Decision D-CONVERGE,
documented in :mod:`tests.test_reconcile_integration`). Throughout, the
author-owned ``draft.md`` bytes survive byte-for-byte and no ``working/`` file is
removed (design §5.4; Constraint).

Both commands are driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
:mod:`tests.steps.reconcile_steps`; the runner steps ``chdir`` into the prepared
tree's parent first because both commands resolve a cwd-relative ``working/``.
The step helpers are kept self-contained rather than shared with
:mod:`tests.steps.reconcile_steps` (ExecPlan Decision D-DUP): the two suites
assert different things and the helpers are a handful of lines.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_torn_turn_recovery_bdd.py``.
"""

from __future__ import annotations

import contextlib
import dataclasses as dc
import io
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands import _reconcile
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import load_state

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"

# The crashed reconcile was repairing stale word-counts, so recovery takes two
# passes (clear the leftover record, then re-apply the recount); a small cap above
# that keeps the bound honest while leaving headroom for the documented convergence.
_MAX_RECOVERY_ATTEMPTS = 3

# The done-claim-stale-word-counts drafts hold {"01": 0, "02": 24000, "03": 20800},
# the recount convergence target the recovered tree must settle to.
_RECOUNT_TARGET = {"01": 0, "02": 24000, "03": 20800}


class _CrashError(RuntimeError):
    """Sentinel raised to simulate a crash after the recovery receipt is appended."""


@dc.dataclass(slots=True)
class _Outcome:
    """The crashed tree plus the per-command exit codes captured across the steps."""

    working: Path
    files_before: set[str]
    drafts_before: dict[str, bytes]
    check_code: int | None = None
    check_envelope: dict[str, object] = dc.field(default_factory=dict)
    recovered: bool = False
    recovery_passes: int = 0
    recheck_code: int | None = None


def _draft_bytes(working: Path) -> dict[str, bytes]:
    """Return every chapter ``draft.md`` as raw bytes, keyed by relative path.

    Drafts are author-owned narrative the recovery may never touch, so capturing
    the exact bytes lets a later step assert byte-for-byte draft integrity across
    both the crash and the recovery.
    """
    return {
        str(p.relative_to(working)): p.read_bytes()
        for p in working.rglob("draft.md")
        if p.is_file()
    }


def _present_files(working: Path) -> set[str]:
    """Return the relative paths of every regular file under ``working``."""
    return {str(p.relative_to(working)) for p in working.rglob("*") if p.is_file()}


def _run(working: Path, command: str, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``command`` through ``run`` from ``working.parent``; return the code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


def _run_capturing(
    working: Path, command: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, dict[str, object]]:
    """Drive ``command`` through ``run`` and return ``(exit_code, envelope)``."""
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), json.loads(stream.getvalue() or "{}")


@given(
    "a real reconcile command crashes mid-write over a stale tree",
    target_fixture="outcome",
)
def crashed_reconcile_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Outcome:
    """Crash a real ``reconcile`` command mid-write to leave a torn ``[pending_turn]``.

    Builds the roadmap headline ``done-claim-stale-word-counts`` tree (whose
    ``[word_counts]`` claims an uncorroborated done chapter), injects the crash at
    the ``_reconcile._append_recovery_entry`` seam (append-then-raise), and drives
    ``reconcile`` through the shared ``run`` wrapper — the command entry path. The
    crash propagates ``_CrashError`` out of the body before ``run`` reaches its
    ``sys.exit``, so the ``reconcile`` mutator leaves its own intent record on disk
    *after* writing it but *before* clearing it: a recoverable torn turn produced
    by a real mutator invocation (Decisions D-MECH, D-INPROC).

    Returns
    -------
    _Outcome
        The crashed ``working/`` path and the files and draft bytes present after
        the crash; the run steps fill in the exit codes.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    drafts_before = _draft_bytes(working)
    files_before = _present_files(working)

    real_append = _reconcile._append_recovery_entry

    def _append_then_crash(working_dir: Path, line: str) -> None:
        """Append the receipt (as production does) then raise, simulating a crash."""
        real_append(working_dir, line)
        raise _CrashError

    monkeypatch.setattr(_reconcile, "_append_recovery_entry", _append_then_crash)
    monkeypatch.chdir(working.parent)
    with pytest.raises(_CrashError):
        run(
            build_app(),
            ["reconcile"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    # Restore production behaviour so the recovery runs do not re-crash.
    monkeypatch.setattr(_reconcile, "_append_recovery_entry", real_append)
    return _Outcome(
        working=working, files_before=files_before, drafts_before=drafts_before
    )


@then("the crashed reconcile leaves an uncleared reconcile pending_turn on disk")
def crash_leaves_torn_record(outcome: _Outcome) -> None:
    """Assert the crash left a populated ``operation="reconcile"`` record.

    This is the producer half — the real-crash origin the roadmap clause demands —
    asserted on disk: the interrupted ``reconcile`` command must leave its own
    intent record, the on-disk signature of a recoverable torn turn rather than a
    corrupted state.
    """
    interrupted = load_state(outcome.working / "state.toml")
    assert interrupted.pending_turn is not None, (
        "the crashed reconcile command must leave a populated pending_turn record"
    )
    assert interrupted.pending_turn.operation == "reconcile", (
        "the leftover record must name reconcile as the in-flight operation"
    )


@when("check runs against that torn tree")
def run_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``check`` through the command boundary and capture code and envelope."""
    outcome.check_code, outcome.check_envelope = _run_capturing(
        outcome.working, "check", monkeypatch
    )


@then("check exits 4 reporting a complete-pending-turn reconciliation")
def check_reports_torn_turn(outcome: _Outcome) -> None:
    """Assert ``check`` flagged the torn turn at exit ``4`` with the right action.

    The envelope must name both the ``complete-pending-turn`` action and the
    ``pending-turn-cleared`` discrepancy, pinning that ``check`` reports the torn
    turn at the command boundary rather than some other drift.
    """
    assert outcome.check_code == ExitCode.ACTIONABLE_FINDING, (
        f"expected check exit 4, got {outcome.check_code}"
    )
    result = typ.cast("dict[str, object]", outcome.check_envelope["result"])
    reconciliation = typ.cast("dict[str, object]", result["reconciliation"])
    assert reconciliation["action"] == "complete-pending-turn", (
        "check must report a complete-pending-turn reconciliation for the torn turn"
    )
    discrepancies = typ.cast("list[str]", reconciliation["discrepancies"])
    assert "pending-turn-cleared" in discrepancies, (
        "check must name the pending-turn-cleared discrepancy for the torn turn"
    )


@when("reconcile re-runs under bounded harness re-entry")
def reconcile_re_runs(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-run ``reconcile`` through the command boundary until ``check`` is clean.

    Mirrors the harness's idempotent re-entry: each ``reconcile`` must exit ``0``;
    the loop stops once a follow-up ``check`` exits ``0`` (the crashed recount
    converges in two passes — clear the leftover record, then re-apply the
    recount; D-CONVERGE). ``recovered`` records whether the bounded loop converged
    and ``recovery_passes`` the number of ``reconcile`` passes it took, so the exact
    two-pass count is pinned downstream rather than only the bound.
    """
    for _attempt in range(_MAX_RECOVERY_ATTEMPTS):
        code = _run(outcome.working, "reconcile", monkeypatch)
        outcome.recovery_passes += 1
        assert code == ExitCode.SUCCESS, "each recovery reconcile must exit 0"
        if _run(outcome.working, "check", monkeypatch) == ExitCode.SUCCESS:
            outcome.recovered = True
            break
    assert outcome.recovered, (
        "repeated reconcile must converge the interrupted tree within the bound"
    )


@then("reconcile recovers the torn turn and the pending_turn is cleared")
def reconcile_clears_record(outcome: _Outcome) -> None:
    """Assert the recovered tree is settled: no record, word counts repaired.

    The recovered tree must carry no uncleared ``[pending_turn]`` and its
    ``[word_counts]`` must hold the disk-derived recount the original drift
    needed, proving recovery both cleared the torn record *and* re-applied the
    still-pending recount. Convergence must take *exactly* two passes (clear the
    leftover record, then re-apply the recount; D-CONVERGE), so a regression that
    silently raises the re-entry pass count fails loudly rather than passing green
    inside the bound.
    """
    assert outcome.recovery_passes == 2, (
        "the crashed recount must converge in exactly two reconcile passes, took "
        f"{outcome.recovery_passes}"
    )
    recovered = load_state(outcome.working / "state.toml")
    assert recovered.pending_turn is None, (
        "the recovered tree must carry no uncleared pending_turn record"
    )
    assert dict(recovered.word_counts.by_chapter) == _RECOUNT_TARGET, (
        "recovery must re-apply the disk-derived recount the original drift needed"
    )


@then("a follow-up check exits 0")
def follow_up_check_clean(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert the recovered tree re-checks clean at exit ``0``."""
    outcome.recheck_code = _run(outcome.working, "check", monkeypatch)
    assert outcome.recheck_code == ExitCode.SUCCESS, (
        f"expected follow-up check exit 0, got {outcome.recheck_code}"
    )


@then("the recovery removes no working file and the drafts are unchanged")
def recovery_preserves_files(outcome: _Outcome) -> None:
    """Assert recovery removed no ``working/`` file and left the drafts intact.

    Recovery may only rewrite the recomputable pair (``state.toml``/``log.md``):
    every file present before the crash must still be present, and the author-owned
    chapter drafts must be byte-for-byte identical across both the crash and the
    recovery (design §5.4; Constraint "no deletion").
    """
    after = _present_files(outcome.working)
    assert outcome.files_before <= after, "recovery must remove no working/ file"
    drafts_after = _draft_bytes(outcome.working)
    assert drafts_after == outcome.drafts_before, (
        "recovery must leave every chapter draft.md byte-for-byte identical; "
        "only state.toml and log.md may change"
    )
