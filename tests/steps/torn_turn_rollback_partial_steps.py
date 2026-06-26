"""Step definitions for the partial-landed torn-turn ROLLBACK scenario.

These prove the roadmap 6.2.12 success clause — the *partial-landed* sibling of
the *never-landed* ROLLBACK scenario task 6.2.7 added. A *real* §3.4
``pending_turn`` bracket raises mid-turn over a coherent baseline, declaring an
unrecoverable next-chapter ``draft.md`` that never lands, and leaves an uncleared
``operation="write-draft"`` ``[pending_turn]`` on disk. Unlike 6.2.7, a *partial
draft residue did land*: the §3.4 temp-file remnant of a mid-write whose
``Path.replace`` never promoted it (S-ATOMIC). The residue is written **inside an
existing manifest chapter directory** so the refuse-class ``manifest-disk-
bijection`` invariant still holds and the disposition stays ROLLBACK rather than
short-circuiting to REFUSE on a new ``chapter-NN/`` directory (S-BIJECTION,
verified probes G/H; Decision D-PARTIAL). ``check`` reports the torn turn (exit
``4`` with a ``rollback-pending-turn`` reconciliation), and ``reconcile`` rolls
it back in a single pass (exit ``0``): the record is cleared, a
``rollback-pending-turn`` receipt is appended to ``log.md``, and a follow-up
``check`` is coherent (exit ``0``).

The defining proof of 6.2.12 (versus 6.2.7) is residue preservation: after
``reconcile``, the partial residue is asserted **still present and byte-for-byte
unchanged**, no ``working/`` file is removed, and no unexpected file is
fabricated — only ``state.toml`` and ``log.md`` may change (design §5.4 item 2:
"Rolling back removes nothing — the partial artefacts stay on disk, unreferenced
by state"). The residue's path is **not** referenced by ``state`` after recovery:
the manifest never declared its chapter, and the cleared ``pending_turn`` no
longer names anything.

The torn record is produced by the design §3.4 ``pending_turn`` context manager
raising mid-turn — the production producer of torn records — not a hand-planted
fixture field (Decisions D-MECH, D-PARTIAL). No v1 command opens a forward
bracket declaring an unrecoverable artefact, so a crashed *command* always
classifies COMPLETE, never ROLLBACK. Recovery is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper — the command entry path,
not the bracket primitive — mirroring :mod:`tests.steps.torn_turn_rollback_steps`;
the runner steps ``chdir`` into the prepared tree's parent first because both
commands resolve a cwd-relative ``working/``. Recovery is asserted under a
*single* pass (D-ONEPASS): the torn record sits over an otherwise-coherent tree,
so one ``reconcile`` clears the record and the tree is immediately coherent.

The step helpers are kept self-contained rather than shared with
:mod:`tests.steps.torn_turn_rollback_steps` (Decision D-DUP): the two suites
assert different residue-preservation facts and the helpers are a handful of
lines. This module lives under ``tests/steps/`` (the directory ``pyproject.toml``
exempts from the assert/argument-count rules) and is imported into the scenario
binder ``tests/test_torn_turn_rollback_partial_bdd.py``.
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

_COMMAND = "novel state"

# The unrecoverable artefact the torn turn declares but never lands: a chapter
# the coherent baseline never materialises, so its basename is not in
# {"state.toml", "log.md"} and the missing path is unrecoverable → ROLLBACK
# (mirroring the pending-turn-rollback-unrecoverable corpus variant).
_UNRECOVERABLE_DRAFT = "working/manuscript/chapter-99/draft.md"

# The partial draft residue the mid-write left behind: the §3.4 temp-file the
# Path.replace never promoted to draft.md (S-ATOMIC). It lands *inside an
# existing manifest chapter directory* (chapter-03, which the coherent baseline
# materialises) so it creates no new chapter-NN/ directory and the refuse-class
# manifest-disk bijection holds — keeping the disposition ROLLBACK, not REFUSE
# (S-BIJECTION, verified probe H; Decision D-PARTIAL).
_RESIDUE_RELPATH = "manuscript/chapter-03/draft.md.partial.tmp"
_RESIDUE_BODY = "partial draft body that landed mid-turn before Path.replace"


class _TornError(RuntimeError):
    """Sentinel raised inside the bracket to simulate a turn dying mid-write."""


@dc.dataclass(slots=True)
class _Outcome:
    """The torn tree plus the per-command state captured across the steps."""

    working: Path
    files_before: set[str]
    drafts_before: dict[str, bytes]
    residue_relpath: str
    residue_bytes_before: bytes
    check_code: int | None = None
    check_envelope: dict[str, object] = dc.field(default_factory=dict)
    reconcile_code: int | None = None
    recheck_code: int | None = None


def _draft_bytes(working: Path) -> dict[str, bytes]:
    """Return every chapter ``draft.md`` as raw bytes, keyed by relative path.

    Drafts are author-owned narrative the rollback may never touch, so capturing
    the exact bytes lets a later step assert byte-for-byte draft integrity across
    both the torn write and the recovery. The ``.tmp`` residue is *not* a
    ``draft.md`` and is captured separately, so it never enters this map.
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
    "a real pending_turn bracket raises mid-turn after a partial draft residue landed",
    target_fixture="outcome",
)
def torn_rollback_partial_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> _Outcome:
    """Raise inside a real §3.4 ``pending_turn`` bracket after landing a residue.

    Builds the coherent baseline tree, then enters the §3.4 ``pending_turn``
    context manager over its ``state.toml`` declaring an unrecoverable
    next-chapter ``draft.md`` (a chapter the baseline never materialises). Inside
    the bracket — before the raise — it writes a partial draft residue as a
    ``.tmp`` sibling inside an *existing* manifest chapter directory (chapter-03),
    the §3.4 temp-file remnant of a mid-write whose ``Path.replace`` never landed
    (S-ATOMIC), then raises a ``_TornError`` before clean exit. The bracket
    persists its intent record *before* yielding, so the raise leaves the
    populated ``operation="write-draft"`` record on disk — a genuine torn turn
    produced by the production primitive, not a hand-planted fixture field
    (Decisions D-MECH, D-PARTIAL). The residue lands inside an existing chapter so
    it creates no new ``chapter-NN/`` directory: the refuse-class manifest-disk
    bijection holds and the disposition stays ``ROLLBACK_PENDING_TURN``
    (S-BIJECTION, D-PARTIAL).

    Returns
    -------
    _Outcome
        The torn ``working/`` path; the files, draft bytes, and the partial
        residue path and bytes present after the torn write; the run steps fill
        in the exit codes.
    """
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    residue = working / _RESIDUE_RELPATH

    # The bracket body must land the residue and then raise to simulate the torn
    # mid-write, so pytest.raises wraps the multi-statement body (PT012).
    with (  # noqa: PT012
        pytest.raises(_TornError),
        pending_turn(
            working / "state.toml",
            operation="write-draft",
            paths=[_UNRECOVERABLE_DRAFT],
        ),
    ):
        residue.write_text(_RESIDUE_BODY, encoding="utf-8")
        msg = "write-draft step died mid-write after the partial residue landed"
        raise _TornError(msg)

    # Capture the recovery baseline *after* the torn write: the residue is now on
    # disk, so a later step can assert it survives the rollback byte-for-byte.
    return _Outcome(
        working=working,
        files_before=_present_files(working),
        drafts_before=_draft_bytes(working),
        residue_relpath=_RESIDUE_RELPATH,
        residue_bytes_before=residue.read_bytes(),
    )


@then("the torn turn leaves an uncleared write-draft pending_turn on disk")
def torn_leaves_record(outcome: _Outcome) -> None:
    """Assert the torn turn left a populated ``operation="write-draft"`` record.

    This is the producer half — the real-torn-turn origin the roadmap clause
    demands — asserted on disk: the interrupted bracket must leave its own intent
    record naming the declared unrecoverable ``draft.md``, the on-disk signature
    of a recoverable torn turn rather than a corrupted state.
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


@then("the partial residue is present on disk and unreferenced by state")
def residue_present_and_unreferenced(outcome: _Outcome) -> None:
    """Assert the partial residue landed on disk yet is named by no state record.

    This pins the distinguishing pre-condition of 6.2.12 (versus 6.2.7): a
    *partial artefact did land*. The residue must exist on disk after the torn
    write, yet ``state`` must not reference it — the manifest never declared its
    chapter, and the uncleared ``pending_turn`` names only the unrecoverable
    ``draft.md`` that never landed, never the ``.tmp`` residue.
    """
    residue = outcome.working / outcome.residue_relpath
    assert residue.is_file(), "the partial residue must be present on disk"
    state = load_state(outcome.working / "state.toml")
    chapter_relpaths = {
        f"working/manuscript/{chapter.slug}/draft.md" for chapter in state.chapters
    }
    residue_workrel = f"working/{outcome.residue_relpath}"
    assert residue_workrel not in chapter_relpaths, (
        "the residue path must not be referenced by the chapter manifest"
    )
    assert state.pending_turn is not None, (
        "the torn record must still be populated before recovery"
    )
    assert residue_workrel not in tuple(state.pending_turn.paths), (
        "the uncleared pending_turn must not name the partial residue"
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
    from the COMPLETE sibling and from a misconstructed REFUSE (which the
    bijection-preserving residue placement avoids), and pinning that ``check``
    reports the torn turn at the command boundary rather than some other drift.
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

    The ROLLBACK record sits over an otherwise-coherent tree, so a single pass
    clears the record and the tree is immediately coherent (D-ONEPASS). The
    follow-up coherence is asserted in a later step rather than looped here.
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


@then("the rollback preserves the partial residue byte-for-byte and fabricates no file")
def rollback_preserves_residue(outcome: _Outcome) -> None:
    """Assert the rollback preserved the residue and fabricated or removed no file.

    This is the distinguishing proof of 6.2.12. Rolling back removes nothing and
    fabricates no prose (design §5.4 item 2): the partial residue must still be
    present and byte-for-byte unchanged, every file present before the recovery
    must still be present, the author-owned chapter drafts must be byte-for-byte
    identical, and the only files that may have appeared are ``state.toml`` and
    ``log.md`` — no unexpected file is fabricated. The residue remains
    unreferenced by ``state`` after recovery: the cleared ``pending_turn`` names
    nothing and the manifest never declared its chapter.
    """
    residue = outcome.working / outcome.residue_relpath
    assert residue.is_file(), "the rollback must leave the partial residue on disk"
    assert residue.read_bytes() == outcome.residue_bytes_before, (
        "the rollback must leave the partial residue byte-for-byte unchanged"
    )

    after = _present_files(outcome.working)
    assert outcome.files_before <= after, "rollback must remove no working/ file"
    fabricated = after - outcome.files_before
    assert fabricated <= {"state.toml", "log.md"}, (
        "rollback must fabricate no file beyond state.toml and log.md; "
        f"unexpected: {sorted(fabricated - {'state.toml', 'log.md'})}"
    )

    drafts_after = _draft_bytes(outcome.working)
    assert drafts_after == outcome.drafts_before, (
        "rollback must leave every chapter draft.md byte-for-byte identical; "
        "only state.toml and log.md may change"
    )

    recovered = load_state(outcome.working / "state.toml")
    assert recovered.pending_turn is None, (
        "the rolled-back state must reference the residue through no pending_turn"
    )
    residue_workrel = f"working/{outcome.residue_relpath}"
    chapter_relpaths = {
        f"working/manuscript/{chapter.slug}/draft.md" for chapter in recovered.chapters
    }
    assert residue_workrel not in chapter_relpaths, (
        "the manifest must not reference the preserved residue after recovery"
    )
