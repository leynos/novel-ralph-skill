"""The shared, pure reconciliation derivation behind ``check`` and ``reconcile``.

:func:`derive_reconciliation` is the one pure ``(State, working_dir) ->
Reconciliation`` function both disk-aware ``check`` and the ``reconcile`` mutator
call (design §5.4; roadmap task 2.3.2). ``check`` renders the result read-only;
``reconcile`` enacts it. ``reconcile`` recomputes it **independently** — it never
consumes a payload ``check`` serialised — but because both call this one function
they cannot disagree (Decision Log D-SHARED). A cross-check test pins the
equality.

The derivation is **total**: it returns a :class:`Reconciliation` for every
constructible :class:`~novel_ralph_skill.state.schema.State` over any
``working_dir`` and never raises. Its precedence (D-WORDCOUNT, D-REPORT,
D-COMPLETE) is total and deterministic:

1. Any **refuse-class** disk-evidence violation — the three contradictions
   (``manifest-disk-bijection``, ``done-flag-without-draft``,
   ``compiled-matches-drafts``) or the reported-not-repaired
   ``cursor-plan-present`` — dominates and yields :attr:`ReconcileAction.REFUSE`.
2. Else an uncleared ``[pending_turn]`` (``pending-turn-cleared`` fired) yields
   :attr:`ReconcileAction.COMPLETE_PENDING_TURN` when every *missing* declared
   path is recomputable (``state.toml``/``log.md``), else
   :attr:`ReconcileAction.ROLLBACK_PENDING_TURN` (an unrecoverable artefact — a
   ``draft.md`` or a ``done.flag`` — did not land; D-COMPLETE).
3. Else ``word-counts-match-drafts`` fired yields
   :attr:`ReconcileAction.RECOUNT`, carrying the disk-derived ``current`` and
   ``by_chapter`` so the mutator writes them without re-reading disk.
4. Else ``log-present`` fired yields :attr:`ReconcileAction.RECREATE_LOG`: the
   partial-``init`` bootstrap (``log.md`` absent beside a present ``state.toml``).
   ``log-present`` is **not** refuse-class — ``log.md`` is recomputable (empty at
   ``init``, append-only after), so the mutator recreates it without fabricating
   an agent judgement (roadmap task 2.3.4; design §5.4).
5. Else :attr:`ReconcileAction.NONE` (coherent; nothing to do).

No disk-evidence violation ever falls through to ``NONE`` while ``check`` exits
4 (round-2 blocking point 4): ``cursor-plan-present`` maps to ``REFUSE`` like the
contradictions and ``log-present`` maps to ``RECREATE_LOG``, so the only ``NONE``
is a genuinely coherent tree.
"""

from __future__ import annotations

import dataclasses
import enum
import typing as typ
from pathlib import PurePosixPath

from novel_ralph_skill.state.disk_evidence import (
    COMPILED_MATCHES_DRAFTS,
    CURSOR_PLAN_PRESENT,
    DONE_FLAG_WITHOUT_DRAFT,
    LOG_PRESENT,
    MANIFEST_DISK_BIJECTION,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_MATCH_DRAFTS,
    check_disk_evidence,
    disk_word_counts,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import PendingTurn, State

# The refuse-class disk-evidence names: the three §5.4 contradictions plus the
# reported-not-repaired ``cursor-plan-present`` (D-REPORT). Any one present means
# disk contradicts itself (or carries a plan-less cursor ``reconcile`` cannot
# synthesise without fabricating prose), so the verdict is REFUSE.
_REFUSE_CLASS: frozenset[str] = frozenset({
    MANIFEST_DISK_BIJECTION,
    DONE_FLAG_WITHOUT_DRAFT,
    COMPILED_MATCHES_DRAFTS,
    CURSOR_PLAN_PRESENT,
})

# The basenames a torn turn's missing declared path may carry for ``reconcile`` to
# *complete* it (recompute and write): the recomputable artefacts (D-COMPLETE).
# Any other missing artefact (a ``draft.md`` body, a ``done.flag``) is
# unrecoverable from disk, so the turn is rolled back instead.
_RECOMPUTABLE_BASENAMES: frozenset[str] = frozenset({"state.toml", "log.md"})


class ReconcileAction(enum.StrEnum):
    """The disk-authoritative action a reconciliation implies (design §5.4)."""

    NONE = "none"
    RECOUNT = "recount"
    RECREATE_LOG = "recreate-log"
    COMPLETE_PENDING_TURN = "complete-pending-turn"
    ROLLBACK_PENDING_TURN = "rollback-pending-turn"
    REFUSE = "refuse"


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Reconciliation:
    """The disk-authoritative reconciliation ``check`` reports and ``reconcile`` enacts.

    Attributes
    ----------
    action : ReconcileAction
        The action the tree implies (recount / complete / rollback / refuse / none).
    discrepancies : tuple[str, ...]
        The disk-evidence invariant names that drove the action, in detector order.
    detail : str
        Human-readable prose for the envelope ``result`` and the ``log.md`` receipt.
    recounted_current : int | None
        For :attr:`ReconcileAction.RECOUNT`, the disk-derived total to write; else
        ``None``.
    recounted_by_chapter : collections.abc.Mapping[str, int] | None
        For :attr:`ReconcileAction.RECOUNT`, the disk-derived per-chapter mapping;
        else ``None``.
    operation : str | None
        For the two pending-turn actions, the torn turn's declared operation; else
        ``None``.
    missing_paths : tuple[str, ...]
        For the two pending-turn actions, the declared paths not yet on disk (the
        recomputable subset for COMPLETE, the unrecoverable trigger for ROLLBACK);
        else an empty tuple.
    """

    action: ReconcileAction
    discrepancies: tuple[str, ...]
    detail: str
    recounted_current: int | None = None
    recounted_by_chapter: cabc.Mapping[str, int] | None = None
    operation: str | None = None
    missing_paths: tuple[str, ...] = ()


def _refuse(discrepancies: cabc.Sequence[str]) -> Reconciliation:
    """Return a REFUSE reconciliation naming the refused discrepancies."""
    names = ", ".join(discrepancies)
    return Reconciliation(
        action=ReconcileAction.REFUSE,
        discrepancies=tuple(discrepancies),
        detail=f"disk evidence refuses repair: {names}",
    )


def _missing_declared_paths(
    paths: cabc.Sequence[str], working_dir: Path
) -> tuple[str, ...]:
    """Return the declared ``paths`` not present on disk, relative to ``working_dir``.

    A declared path is recorded relative to the project root (``working/...``); the
    materialised tree puts ``working/`` at ``working_dir``, so a declared
    ``working/<rest>`` lands at ``working_dir / <rest>``. A path that does not start
    with ``working/`` is joined under ``working_dir`` as-is (defensive; the
    producers always prefix it).
    """
    missing: list[str] = []
    for path in paths:
        relative = path.removeprefix("working/")
        if not (working_dir / relative).exists():
            missing.append(path)
    return tuple(missing)


def _classify_pending_turn(
    pending: PendingTurn, working_dir: Path, discrepancies: cabc.Sequence[str]
) -> Reconciliation:
    """Return the COMPLETE/ROLLBACK reconciliation for an uncleared ``[pending_turn]``.

    Computes the declared paths still missing from disk and chooses by D-COMPLETE:
    every missing path recomputable (``state.toml``/``log.md``) → COMPLETE (the
    dispatch re-derives those artefacts and clears the record); any missing path
    unrecoverable (a ``draft.md``/``done.flag``) → ROLLBACK (the record is cleared,
    the partial artefacts left in place). A record over a fully-landed turn (nothing
    missing) is a stale marker → COMPLETE with an empty missing set (the dispatch
    just clears it).
    """
    missing = _missing_declared_paths(pending.paths, working_dir)
    unrecoverable = tuple(
        path
        for path in missing
        if PurePosixPath(path).name not in _RECOMPUTABLE_BASENAMES
    )
    if unrecoverable:
        return Reconciliation(
            action=ReconcileAction.ROLLBACK_PENDING_TURN,
            discrepancies=tuple(discrepancies),
            detail=(
                f"rolling back torn turn {pending.operation!r}: unrecoverable "
                f"artefact(s) {list(unrecoverable)} did not land"
            ),
            operation=pending.operation,
            missing_paths=missing,
        )
    return Reconciliation(
        action=ReconcileAction.COMPLETE_PENDING_TURN,
        discrepancies=tuple(discrepancies),
        detail=(
            f"completing torn turn {pending.operation!r}: writing the remaining "
            f"recomputable artefact(s) {list(missing)}"
        ),
        operation=pending.operation,
        missing_paths=missing,
    )


def _recount(
    state: State, working_dir: Path, discrepancies: cabc.Sequence[str]
) -> Reconciliation:
    """Return the RECOUNT reconciliation carrying the disk-derived word counts."""
    current, by_chapter = disk_word_counts(state, working_dir)
    return Reconciliation(
        action=ReconcileAction.RECOUNT,
        discrepancies=tuple(discrepancies),
        detail=(
            f"recounting [word_counts] from the drafts: current {current} across "
            f"{len(by_chapter)} chapters"
        ),
        recounted_current=current,
        recounted_by_chapter=dict(by_chapter),
    )


def derive_reconciliation(state: State, working_dir: Path) -> Reconciliation:
    """Classify ``state``/``working_dir`` into the disk-authoritative reconciliation.

    Pure and total: returns a :class:`Reconciliation` for every ``State`` over any
    ``working_dir`` and never raises. The precedence (refuse-class → pending-turn →
    recount → none) is fixed and deterministic (D-WORDCOUNT, D-REPORT, D-COMPLETE);
    see the module docstring.

    Parameters
    ----------
    state : State
        The parsed ``state.toml`` to reconcile against disk.
    working_dir : pathlib.Path
        The materialised ``working/`` directory.

    Returns
    -------
    Reconciliation
        The action, discrepancies, detail, and action-specific payload.
    """
    fired = [
        violation.invariant for violation in check_disk_evidence(state, working_dir)
    ]
    refuse = [name for name in fired if name in _REFUSE_CLASS]
    if refuse:
        return _refuse(refuse)
    if state.pending_turn is not None and PENDING_TURN_CLEARED in fired:
        return _classify_pending_turn(
            state.pending_turn, working_dir, [PENDING_TURN_CLEARED]
        )
    if WORD_COUNTS_MATCH_DRAFTS in fired:
        return _recount(state, working_dir, [WORD_COUNTS_MATCH_DRAFTS])
    if LOG_PRESENT in fired:
        return Reconciliation(
            action=ReconcileAction.RECREATE_LOG,
            discrepancies=(LOG_PRESENT,),
            detail="recreating the absent log.md receipt",
        )
    return Reconciliation(
        action=ReconcileAction.NONE,
        discrepancies=(),
        detail="state is coherent against disk; nothing to reconcile",
    )
