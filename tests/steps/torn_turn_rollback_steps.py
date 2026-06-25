"""Step definitions for the torn-turn ROLLBACK scenario at the command boundary.

These prove the roadmap 6.2.7 success clause — the symmetric half of the
disposition task 6.2.5 proved for COMPLETE. A *real* §3.4 ``pending_turn``
bracket raises mid-turn over a coherent baseline, declaring an unrecoverable
``draft.md`` that never lands, and leaves an uncleared
``operation="write-draft"`` ``[pending_turn]`` on disk (the on-disk signature of
a torn turn whose missing artefact is unrecoverable). ``check`` reports it (exit
``4`` with a ``rollback-pending-turn`` reconciliation), and ``reconcile`` rolls
it back in a single pass (exit ``0``): the record is cleared, a
``rollback-pending-turn`` receipt is appended to ``log.md``, and a follow-up
``check`` is coherent (exit ``0``).

No v1 command opens a forward bracket declaring an unrecoverable artefact — the
only command that opens a bracket at all is ``reconcile``, and it declares only
the recomputable ``state.toml``/``log.md`` — so a crashed *command* always
classifies COMPLETE, never ROLLBACK (ExecPlan Decisions D-MECH, D-PRODUCER). The
faithful real producer for ROLLBACK is therefore the design §3.4 ``pending_turn``
context manager raising mid-turn, exactly as :mod:`tests.steps.torn_turn_steps`
drives it, here declaring an unrecoverable ``draft.md`` and paired with
command-boundary recovery.

Recovery is asserted under a *single* pass (D-ONEPASS): the torn record sits
over an otherwise-coherent tree, so one ``reconcile`` clears the record and the
tree is immediately coherent — unlike 6.2.5's two-pass crashed-recount loop.
Throughout, the author-owned ``draft.md`` bytes survive byte-for-byte and no
``working/`` file is removed (design §5.4 item 2: "Rolling back removes nothing").

Both commands are driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
:mod:`tests.steps.torn_turn_recovery_steps`; the runner steps ``chdir`` into the
prepared tree's parent first because both commands resolve a cwd-relative
``working/``. The step helpers are kept self-contained rather than shared with
:mod:`tests.steps.torn_turn_recovery_steps` (ExecPlan Decision D-DUP): the two
suites assert different dispositions and the helpers are a handful of lines.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_torn_turn_rollback_bdd.py``.
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

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import load_state
from novel_ralph_skill.state.document import pending_turn

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"

# The unrecoverable artefact the torn turn declares but never lands: a chapter
# the coherent baseline never materialises, so its basename is not in
# {"state.toml", "log.md"} and the missing path is unrecoverable → ROLLBACK
# (mirroring the pending-turn-rollback-unrecoverable corpus variant).
_UNRECOVERABLE_DRAFT = "working/manuscript/chapter-99/draft.md"


class _TornError(RuntimeError):
    """Sentinel raised inside the bracket to simulate a turn dying mid-write."""


@dc.dataclass(slots=True)
class _Outcome:
    """The torn tree plus the per-command exit codes captured across the steps."""

    working: Path
    files_before: set[str]
    drafts_before: dict[str, bytes]
    check_code: int | None = None
    check_envelope: dict[str, object] = dc.field(default_factory=dict)
    reconcile_code: int | None = None
    recheck_code: int | None = None


def _draft_bytes(working: Path) -> dict[str, bytes]:
    """Return every chapter ``draft.md`` as raw bytes, keyed by relative path.

    Drafts are author-owned narrative the rollback may never touch, so capturing
    the exact bytes lets a later step assert byte-for-byte draft integrity across
    both the torn write and the recovery.
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
    "a real pending_turn bracket raises mid-turn declaring an unrecoverable draft",
    target_fixture="outcome",
)
def torn_rollback_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Outcome:
    """Raise inside a real §3.4 ``pending_turn`` bracket to leave a ROLLBACK record.

    Builds the coherent baseline tree, then enters the §3.4 ``pending_turn``
    context manager over its ``state.toml`` declaring an unrecoverable
    ``draft.md`` (a chapter the baseline never materialises) and raises a
    ``_TornError`` before clean exit. The bracket persists its intent record
    *before* yielding, so the raise leaves the populated ``operation="write-draft"``
    record on disk — a genuine torn turn produced by the production primitive,
    not a hand-planted fixture field (Decisions D-MECH, D-PRODUCER). Because the
    declared ``draft.md`` never lands and is unrecoverable, the derivation
    classifies the record ``ROLLBACK_PENDING_TURN`` (D-COHERENT).

    Returns
    -------
    _Outcome
        The torn ``working/`` path and the files and draft bytes present after the
        torn write; the run steps fill in the exit codes.
    """
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    drafts_before = _draft_bytes(working)
    files_before = _present_files(working)

    # The bracket body must raise to simulate the torn turn, so pytest.raises
    # wraps the multi-statement body (PT012).
    with (  # noqa: PT012
        pytest.raises(_TornError),
        pending_turn(
            working / "state.toml",
            operation="write-draft",
            paths=[_UNRECOVERABLE_DRAFT],
        ),
    ):
        msg = "write-draft step died mid-turn before the draft landed"
        raise _TornError(msg)

    return _Outcome(
        working=working, files_before=files_before, drafts_before=drafts_before
    )


@then("the torn turn leaves an uncleared write-draft pending_turn on disk")
def torn_leaves_record(outcome: _Outcome) -> None:
    """Assert the torn turn left a populated ``operation="write-draft"`` record.

    This is the producer half — the real-torn-turn origin the roadmap clause
    demands — asserted on disk: the interrupted bracket must leave its own intent
    record naming the declared unrecoverable ``draft.md``, the on-disk signature of
    a recoverable torn turn rather than a corrupted state.
    """
    interrupted = load_state(outcome.working / "state.toml")
    assert interrupted.pending_turn is not None, (
        "the torn pending_turn bracket must leave a populated record"
    )
    assert interrupted.pending_turn.operation == "write-draft", (
        "the leftover record must name write-draft as the in-flight operation"
    )
    assert tuple(interrupted.pending_turn.paths) == (_UNRECOVERABLE_DRAFT,), (
        "the leftover record must declare the unrecoverable draft.md path"
    )


@when("check runs against that torn tree")
def run_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``check`` through the command boundary and capture code and envelope."""
    outcome.check_code, outcome.check_envelope = _run_capturing(
        outcome.working, "check", monkeypatch
    )


@then("check exits 4 reporting a rollback-pending-turn reconciliation")
def check_reports_rollback(outcome: _Outcome) -> None:
    """Assert ``check`` flagged the torn turn at exit ``4`` with the ROLLBACK action.

    The envelope must name both the ``rollback-pending-turn`` action and the
    ``pending-turn-cleared`` discrepancy, distinguishing the ROLLBACK disposition
    from the COMPLETE sibling 6.2.5 proves and pinning that ``check`` reports the
    torn turn at the command boundary rather than some other drift.
    """
    assert outcome.check_code == ExitCode.ACTIONABLE_FINDING, (
        f"expected check exit 4, got {outcome.check_code}"
    )
    result = typ.cast("dict[str, object]", outcome.check_envelope["result"])
    reconciliation = typ.cast("dict[str, object]", result["reconciliation"])
    assert reconciliation["action"] == "rollback-pending-turn", (
        "check must report a rollback-pending-turn reconciliation for the torn turn"
    )
    discrepancies = typ.cast("list[str]", reconciliation["discrepancies"])
    assert "pending-turn-cleared" in discrepancies, (
        "check must name the pending-turn-cleared discrepancy for the torn turn"
    )


@when("reconcile rolls the torn turn back in a single pass")
def reconcile_rolls_back(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive a single ``reconcile`` through the command boundary; capture the code.

    Unlike 6.2.5's bounded re-entry loop, the ROLLBACK record sits over an
    otherwise-coherent tree, so a single pass clears the record and the tree is
    immediately coherent (D-ONEPASS). The follow-up coherence is asserted in a
    later step rather than looped here.
    """
    outcome.reconcile_code = _run(outcome.working, "reconcile", monkeypatch)


@then("reconcile clears the record and appends a rollback-pending-turn receipt")
def reconcile_clears_and_logs(outcome: _Outcome) -> None:
    """Assert the single ``reconcile`` cleared the record and logged the rollback.

    The recovered tree must carry no uncleared ``[pending_turn]`` and ``log.md``
    must carry the ``rollback-pending-turn`` receipt the rollback dispatch appends,
    proving the rollback both cleared the torn record *and* left an audit trail at
    the command boundary.
    """
    assert outcome.reconcile_code == ExitCode.SUCCESS, (
        f"expected reconcile exit 0, got {outcome.reconcile_code}"
    )
    recovered = load_state(outcome.working / "state.toml")
    assert recovered.pending_turn is None, (
        "the rolled-back tree must carry no uncleared pending_turn record"
    )
    log_text = (outcome.working / "log.md").read_text(encoding="utf-8")
    assert "rollback-pending-turn:" in log_text, (
        "reconcile must append a rollback-pending-turn receipt to log.md"
    )


@then("a follow-up check exits 0")
def follow_up_check_clean(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert the rolled-back tree re-checks clean at exit ``0`` in a single pass."""
    outcome.recheck_code = _run(outcome.working, "check", monkeypatch)
    assert outcome.recheck_code == ExitCode.SUCCESS, (
        f"expected follow-up check exit 0, got {outcome.recheck_code}"
    )


@then("the rollback removes no working file and the drafts are unchanged")
def rollback_preserves_files(outcome: _Outcome) -> None:
    """Assert the rollback removed no ``working/`` file and left the drafts intact.

    Rolling back removes nothing and fabricates no prose (design §5.4 item 2):
    every file present before the recovery must still be present, and the
    author-owned chapter drafts must be byte-for-byte identical across both the
    torn write and the recovery; only ``state.toml`` and ``log.md`` may change.
    """
    after = _present_files(outcome.working)
    assert outcome.files_before <= after, "rollback must remove no working/ file"
    drafts_after = _draft_bytes(outcome.working)
    assert drafts_after == outcome.drafts_before, (
        "rollback must leave every chapter draft.md byte-for-byte identical; "
        "only state.toml and log.md may change"
    )
