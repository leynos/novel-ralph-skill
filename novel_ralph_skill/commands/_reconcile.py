"""The ``reconcile`` mutator body (roadmap task 2.3.2; design §3.4, §4.1, §5.4).

``reconcile`` writes the disk-authoritative reconciliation a stale ``state.toml``
implies and logs it as the audit receipt (design §5.4). It derives the
reconciliation **independently** of ``check`` (it never consumes ``check``'s
payload) by calling the same shared
:func:`~novel_ralph_skill.state.derive_reconciliation` (D-SHARED), then dispatches
on the action:

- ``NONE`` → exit ``0``, no write, no log (a coherent tree; nothing to repair).
- ``RECREATE_LOG`` → recreate the absent ``log.md`` as the partial-``init``
  repair, append a ``recreate-log`` receipt (the append-mode open *is* the
  create), write **no** ``state.toml`` change, exit ``0`` (roadmap task 2.3.4).
- ``RECOUNT`` → rewrite ``[word_counts]`` from the drafts (exactly as ``recount``
  does), validate the proposed document, log a ``recount`` receipt, exit ``0``.
- ``COMPLETE_PENDING_TURN`` → write each recomputable missing declared artefact
  (re-derive ``[word_counts]`` when ``state.toml`` is a missing declared path; the
  ``log.md`` receipt is itself one of the remaining artefacts), clear the torn
  record, log a ``complete-pending-turn`` receipt, exit ``0`` (D-COMPLETE).
- ``ROLLBACK_PENDING_TURN`` → clear the torn record, delete nothing, log a
  ``rollback-pending-turn`` receipt, exit ``0``.
- ``REFUSE`` → write no state change, append a ``refuse`` receipt, exit ``4``
  (covers the contradictions and ``cursor-plan-present``; D-REPORT).

``reconcile`` is the project's first genuinely multi-file mutator: a state-writing
action touches ``state.toml`` *and* ``log.md``, so it brackets the pair with a
``[pending_turn]`` of its own — but **not** via the ``pending_turn`` context
manager, which clears on ``__exit__`` with no hook to land the ``log.md`` receipt
*before* the clear (D-SELF). It drives the lower-level seam manually in the fixed
order ``open_pending_turn`` + write → state edit → ``log.md`` append →
``clear_pending_turn`` + write (D-SELF, D-LOG), so a crash at any step leaves a
populated ``operation="reconcile"`` record a subsequent ``reconcile`` re-derives
and finishes, and a completed run leaves a coherent tree with the receipt on disk.

It lives beside :mod:`novel_ralph_skill.commands._recount` and reuses that
module's load/refuse helpers and the inline-table builder rather than duplicating
the mutator contract (AGENTS.md "clear file boundaries").
"""

from __future__ import annotations

import datetime as dt
import typing as typ

from novel_ralph_skill.commands._recount import _inline_by_chapter
from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _refuse_if_incoherent,
    _state_path,
    _state_view_or_state_error,
    _working_dir,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome
from novel_ralph_skill.state import (
    SET_CHAPTERS_OPERATION,
    ReconcileAction,
    Reconciliation,
    clear_pending_turn,
    derive_reconciliation,
    open_pending_turn,
    reconciliation_payload,
    write_document_atomically,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import pathlib

    from tomlkit import TOMLDocument

# This mutator's own ``[pending_turn]`` operation tag and the two files its
# state-writing actions bracket; a crash leaves a populated record with this
# operation a subsequent ``reconcile`` re-derives and finishes (D-SELF).
_RECONCILE_OPERATION = "reconcile"
_RECONCILE_PATHS: tuple[str, ...] = ("state.toml", "log.md")


def _append_recovery_entry(working_dir: pathlib.Path, line: str) -> None:
    """Append one timestamped recovery receipt line to ``working/log.md``.

    The receipt is appended (UTF-8, append mode) so the existing turn log is
    preserved; a torn append loses only the receipt, never state (design §3.4 line
    237; D-LOG). The line carries an RFC 3339 UTC timestamp, the resolved action,
    and the discrepancy resolved or refused.
    """
    timestamp = dt.datetime.now(dt.UTC).isoformat()
    with (working_dir / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp} reconcile: {line}\n")


def _run_reconcile_bracket(
    path: pathlib.Path,
    working_dir: pathlib.Path,
    *,
    edit: cabc.Callable[[TOMLDocument], None],
    log_line: str,
) -> None:
    """Drive the D-SELF manual bracket: intent → edit → receipt → clear.

    In this exact fixed order (D-SELF, D-LOG):

    1. ``open_pending_turn`` reconcile's own intent record, then write — the intent
       lands first, so a crash before the clear is recoverable.
    2. apply ``edit`` to the same document (the recount, or the torn-turn clear).
    3. append ``log_line`` to ``log.md`` — the receipt lands before the clear.
    4. ``clear_pending_turn`` reconcile's record, then write — the bracket clears
       last, after both the state edit and the receipt are on disk.

    ``edit`` mutates the live document in place (it may also clear a *torn* turn's
    record, which step 1 has already replaced with reconcile's own). The loaded
    document is reused across both writes so an in-bracket edit survives the
    clean-exit write (design Decision Log).
    """
    document = _load_document_or_state_error(path)
    open_pending_turn(document, operation=_RECONCILE_OPERATION, paths=_RECONCILE_PATHS)
    write_document_atomically(document, path)
    edit(document)
    _append_recovery_entry(working_dir, log_line)
    clear_pending_turn(document)
    write_document_atomically(document, path)


def _recount_edit(
    reconciliation: Reconciliation,
) -> cabc.Callable[[TOMLDocument], None]:
    """Return an edit closure that rewrites ``[word_counts]`` from the recount.

    Mirrors the ``recount`` command's write exactly (fresh ordered inline
    ``by_chapter``, ``current = sum(by_chapter)``) and validates the proposed
    document before it is persisted, so a recount that would breach a §5.2
    invariant refuses with exit ``3`` and leaves the prior file intact (the
    sub-threshold guard means a coherent done-claim recount never trips this;
    D-GATES backstop).
    """
    current = reconciliation.recounted_current
    by_chapter = reconciliation.recounted_by_chapter
    if current is None or by_chapter is None:
        msg = "RECOUNT reconciliation is missing its disk-derived counts"
        raise ValueError(msg)

    def _edit(document: TOMLDocument) -> None:
        """Rewrite ``[word_counts]`` and refuse an incoherent proposed state."""
        document["word_counts"]["current"] = current
        document["word_counts"]["by_chapter"] = _inline_by_chapter(by_chapter)
        proposed = _state_view_or_state_error(document)
        _refuse_if_incoherent(proposed, context="reconcile recount")

    return _edit


def _create_missing_chapter_dirs(
    reconciliation: Reconciliation, working_dir: pathlib.Path
) -> None:
    """Materialise the missing ``chapter-NN/`` dirs a torn ``set-chapters`` declares.

    Derives the directories from ``reconciliation.missing_paths`` (the
    declared-but-missing chapter-dir paths, ``working/…``-rooted), not a re-read
    manifest, so the recovery fabricates no agent judgement — the manifest is
    already on disk (D10). Creation is idempotent (``mkdir(parents=True,
    exist_ok=True)``) and deletes nothing (Constraint "no deletion").
    """
    for path in reconciliation.missing_paths:
        relative = path.removeprefix("working/")
        (working_dir / relative).mkdir(parents=True, exist_ok=True)


def _pending_turn_edit(
    reconciliation: Reconciliation,
    working_dir: pathlib.Path,
) -> cabc.Callable[[TOMLDocument], None]:
    """Return an edit closure for a COMPLETE/ROLLBACK pending-turn recovery.

    For a COMPLETE whose missing declared paths include ``state.toml``, the edit
    re-derives ``[word_counts]`` from the drafts (the recomputable artefact). For a
    COMPLETE of a torn ``set-chapters`` turn (Work item 3a) the edit instead creates
    each missing ``chapter-NN/`` directory the persisted manifest declares (ADR 008,
    D8). For a ROLLBACK, or a COMPLETE whose only missing artefact is the ``log.md``
    receipt (written by the bracket's own step 3), the edit makes no further state
    change. The bracket's step 1 has already replaced the torn ``[pending_turn]``
    with reconcile's own record, and step 4 clears it, so the torn record is gone
    either way; this edit never deletes a ``working/`` file (Constraint "no
    deletion").
    """
    writes_state = any(
        path.endswith("state.toml") for path in reconciliation.missing_paths
    )
    completes_set_chapters = (
        reconciliation.action is ReconcileAction.COMPLETE_PENDING_TURN
        and reconciliation.operation == SET_CHAPTERS_OPERATION
    )

    def _edit(document: TOMLDocument) -> None:
        """Recompute ``[word_counts]`` or create the torn turn's chapter directories."""
        if completes_set_chapters:
            # The chapter dirs are deterministic, manifest-derived artefacts; the
            # persisted manifest is the agent's judgement and is left untouched.
            _create_missing_chapter_dirs(reconciliation, working_dir)
            return
        if not writes_state:
            return
        from novel_ralph_skill.state import disk_word_counts

        view = _state_view_or_state_error(document)
        current, by_chapter = disk_word_counts(view, working_dir)
        document["word_counts"]["current"] = current
        document["word_counts"]["by_chapter"] = _inline_by_chapter(by_chapter)
        _refuse_if_incoherent(
            _state_view_or_state_error(document),
            context="reconcile complete-pending-turn",
        )

    return _edit


def _write_outcome(reconciliation: Reconciliation) -> CommandOutcome:
    """Return the exit-``0`` write-shaped success outcome for a repair action.

    The ``result`` names the action and what changed (the write-shaped success
    vocabulary), never ``check``'s ``violations`` read shape (developers' guide;
    audit-2.2.2 Finding 2).
    """
    result = reconciliation_payload(reconciliation)
    return CommandOutcome(
        code=ExitCode.SUCCESS, result=result, messages=[reconciliation.detail]
    )


def _refuse_outcome(
    working_dir: pathlib.Path, reconciliation: Reconciliation
) -> CommandOutcome:
    """Append a ``refuse`` receipt and return the exit-``4`` refusal outcome.

    A ``REFUSE`` writes **no** state change (``state.toml`` is byte-for-byte
    unchanged); only ``log.md`` gains the refusal receipt, appended as a lone
    single-file append outside the ``[pending_turn]`` bracket (D-LOG). It reports
    the refused discrepancies and exits ``4``.
    """
    _append_recovery_entry(working_dir, f"refuse: {reconciliation.detail}")
    return CommandOutcome(
        code=ExitCode.ACTIONABLE_FINDING,
        result=reconciliation_payload(reconciliation),
        messages=[reconciliation.detail],
    )


def reconcile() -> CommandOutcome:
    """Write the disk-authoritative reconciliation; log it; exit ``0``/``4``.

    Loads ``working/state.toml`` through the ``tomlkit`` document path, derives the
    typed view (routing faults to exit ``3``), and recomputes the reconciliation
    independently via the shared
    :func:`~novel_ralph_skill.state.derive_reconciliation` (D-SHARED). It dispatches
    on the action (see the module docstring): the three state-writing actions run
    through the D-SELF manual bracket (intent → edit → receipt → clear), ``REFUSE``
    appends a lone receipt and exits ``4``, and ``NONE`` is an exit-``0`` no-op. It
    deletes no ``working/`` file on any path.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once a repair (or a coherent no-op) is written,
        carrying the write-shaped action ``result``; or
        ``ExitCode.ACTIONABLE_FINDING`` for a refused contradiction or
        ``cursor-plan-present`` (no state change written).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, a chapter ``draft.md`` is
        unreadable, or a proposed recount is incoherent (each the exit-``3``
        channel).
    """
    path = _state_path()
    working_dir = _working_dir()
    document = _load_document_or_state_error(path)
    state = _state_view_or_state_error(document)
    reconciliation = derive_reconciliation(state, working_dir)
    action = reconciliation.action

    if action is ReconcileAction.NONE:
        return CommandOutcome(
            code=ExitCode.SUCCESS,
            result=reconciliation_payload(reconciliation),
            messages=[reconciliation.detail],
        )
    if action is ReconcileAction.REFUSE:
        return _refuse_outcome(working_dir, reconciliation)
    if action is ReconcileAction.RECREATE_LOG:
        # The partial-``init`` repair: ``log.md`` is absent beside a present
        # ``state.toml``. ``_append_recovery_entry`` opens ``log.md`` in append
        # mode, which *creates* it, so the recreate and the receipt are one write.
        # No ``state.toml`` change, so this needs no D-SELF bracket (no torn turn
        # to re-derive: a crash leaves ``log.md`` still absent, which a subsequent
        # ``reconcile`` re-derives as RECREATE_LOG and finishes).
        _append_recovery_entry(working_dir, f"recreate-log: {reconciliation.detail}")
        return _write_outcome(reconciliation)
    if action is ReconcileAction.RECOUNT:
        edit = _recount_edit(reconciliation)
        log_line = f"recount: {reconciliation.detail}"
    else:
        # COMPLETE_PENDING_TURN or ROLLBACK_PENDING_TURN.
        edit = _pending_turn_edit(reconciliation, working_dir)
        log_line = f"{action}: {reconciliation.detail}"
    _run_reconcile_bracket(path, working_dir, edit=edit, log_line=log_line)
    return _write_outcome(reconciliation)
