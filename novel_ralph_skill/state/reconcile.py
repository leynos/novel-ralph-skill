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

1. A torn ``set-chapters`` turn whose only refuse-class violation is a
   ``manifest-disk-bijection`` **fully explained** by its declared-but-missing
   ``chapter-NN/`` directories is classified ahead of the refuse arm and yields
   :attr:`ReconcileAction.COMPLETE_PENDING_TURN` (it materialises the empty,
   manifest-derived directories; ADR 008, design §5.4, ExecPlan Decision Log D8).
   This is the **one** sanctioned exception to refuse-class precedence: the
   manifest is already on disk (the writer persists it at the intent write, D10),
   so the only outstanding work is deterministic, judgement-free directories —
   recomputable exactly like ``log.md``. Any *unexplained* bijection break (a
   stray draft, an orphan directory, a manifest gap the pending turn does not
   account for, or a second refuse-class violation) still REFUSEs.
1a. Else a relaxed drafting subset cover gap — no ``[pending_turn]``, phase
   ``drafting``, a coherent disk-subset-of-manifest break whose lone refuse-class
   violation is ``manifest-disk-bijection``, and the re-keyed
   ``word-counts-cover-drafts`` detector reporting a drafted chapter the table
   omits — yields :attr:`ReconcileAction.RECOUNT` (roadmap task 2.3.8, D3). This
   scoped, drafting-gated pre-arm runs strictly after the ``set-chapters``
   COMPLETE arm (B1) and before the refuse arm (B2), so ``reconcile`` (strict)
   agrees with the verdict ``check`` (relaxed) already reports for the same tree
   (D7) without relaxing the strict bijection.
2. Else any **refuse-class** disk-evidence violation — the three contradictions
   (``manifest-disk-bijection``, ``done-flag-without-draft``,
   ``compiled-matches-drafts``) or the reported-not-repaired
   ``cursor-plan-present`` — dominates and yields :attr:`ReconcileAction.REFUSE`.
3. Else an uncleared ``[pending_turn]`` (``pending-turn-cleared`` fired) yields
   :attr:`ReconcileAction.COMPLETE_PENDING_TURN` when every *missing* declared
   path is recomputable (``state.toml``/``log.md``), else
   :attr:`ReconcileAction.ROLLBACK_PENDING_TURN` (an unrecoverable artefact — a
   ``draft.md`` or a ``done.flag`` — did not land; D-COMPLETE).
4. Else a ``word-counts`` disk-evidence violation — ``word-counts-match-drafts``
   (shared-key value divergence) or ``word-counts-cover-drafts`` (key-set
   coverage divergence; roadmap task 2.3.6) — yields
   :attr:`ReconcileAction.RECOUNT`, carrying the disk-derived ``current`` and
   ``by_chapter`` so the mutator writes them without re-reading disk. A recount
   re-keys ``by_chapter`` off the manifest, so the one action repairs both the
   value and the coverage divergence.
5. Else ``log-present`` fired yields :attr:`ReconcileAction.RECREATE_LOG`: the
   partial-``init`` bootstrap (``log.md`` absent beside a present ``state.toml``).
   ``log-present`` is **not** refuse-class — ``log.md`` is recomputable (empty at
   ``init``, append-only after), so the mutator recreates it without fabricating
   an agent judgement (roadmap task 2.3.4; design §5.4).
6. Else :attr:`ReconcileAction.NONE` (coherent; nothing to do).

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

from novel_ralph_skill.state._disk_word_counts import (
    WORD_COUNTS_COVER_DRAFTS,
    WORD_COUNTS_MATCH_DRAFTS,
    disk_word_counts,
)
from novel_ralph_skill.state._reconcile_precedence import (
    _RECOMPUTABLE_BASENAMES,
    _REFUSE_CLASS,
    _drafting_subset_cover_gap,
    _missing_declared_paths,
    _set_chapters_turn_explains_bijection,
)
from novel_ralph_skill.state.disk_evidence import (
    DISK_EVIDENCE_INVARIANT_NAMES,
    LOG_PRESENT,
    MANIFEST_DISK_BIJECTION,
    PENDING_TURN_CLEARED,
    check_disk_evidence,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import PendingTurn, State

# The disk-evidence names a single ``RECOUNT`` repairs: the shared-key value
# divergence and the key-set coverage divergence (roadmap task 2.3.6). A recount
# rewrites ``current`` and re-keys ``by_chapter`` off the manifest, supplying any
# missing key and dropping any orphan key, so one action repairs both.
_RECOUNT_TRIGGERS: frozenset[str] = frozenset({
    WORD_COUNTS_MATCH_DRAFTS,
    WORD_COUNTS_COVER_DRAFTS,
})


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


def _complete_set_chapters_turn(
    pending: PendingTurn, working_dir: Path
) -> Reconciliation:
    """Return the COMPLETE reconciliation for an explained torn ``set-chapters`` turn.

    The caller has already proved
    :func:`_set_chapters_turn_explains_bijection`, so the bijection break fired and
    is fully explained by the pending turn's missing chapter directories.
    ``missing_paths`` carries exactly those declared-but-missing chapter-dir paths,
    so the ``reconcile`` dispatch (``commands/_reconcile.py``) materialises them
    without re-reading the manifest (ADR 008, design §5.4, D8).
    """
    missing = _missing_declared_paths(pending.paths, working_dir)
    return Reconciliation(
        action=ReconcileAction.COMPLETE_PENDING_TURN,
        discrepancies=(MANIFEST_DISK_BIJECTION,),
        detail=(
            "completing torn 'set-chapters' turn: creating the missing chapter "
            f"directories {list(missing)} the persisted manifest declares"
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


def _scoped_precedence_exception(
    state: State, working_dir: Path, fired: cabc.Sequence[str]
) -> Reconciliation | None:
    """Return a scoped pre-refuse-arm reconciliation, or ``None`` to fall through.

    The two exceptions that run ahead of the refuse-class arm, in their pinned
    order:

    1. A torn ``set-chapters`` turn whose lone refuse-class violation is a
       ``manifest-disk-bijection`` fully explained by its missing chapter dirs
       COMPLETEs (materialises the empty directories) rather than REFUSEs (ADR
       008, D8). The explicit ``pending is not None`` guard narrows the type for
       the checker without a bare ``assert``.
    2. Else a relaxed drafting subset whose only refuse-class break is the strict
       ``manifest-disk-bijection`` and which carries a missing drafted cover key
       RECOUNTs (re-keying ``by_chapter`` off the manifest) rather than REFUSEs,
       so ``reconcile`` (strict) agrees with the verdict ``check`` (relaxed) for
       the same tree (roadmap task 2.3.8, D3, D7). Pinned AFTER the set-chapters
       arm (B1) and gated on no pending turn and a single refuse-class member
       (B2), so it never masks a pending turn or a second contradiction.

    Returning ``None`` lets ``derive_reconciliation`` fall through to the strict
    refuse / pending-turn / recount / log precedence unchanged (Constraint 1).
    """
    pending = state.pending_turn
    if pending is not None and _set_chapters_turn_explains_bijection(
        state, working_dir, fired
    ):
        return _complete_set_chapters_turn(pending, working_dir)
    if _drafting_subset_cover_gap(state, working_dir, fired):
        return _recount(state, working_dir, [WORD_COUNTS_COVER_DRAFTS])
    return None


def derive_reconciliation(state: State, working_dir: Path) -> Reconciliation:
    """Classify ``state``/``working_dir`` into the disk-authoritative reconciliation.

    Pure and total: returns a :class:`Reconciliation` for every ``State`` over any
    ``working_dir`` and never raises. The precedence (explained ``set-chapters``
    turn → relaxed drafting-subset cover gap → refuse-class → pending-turn →
    recount → recreate-log → none) is fixed and deterministic (D-WORDCOUNT,
    D-REPORT, D-COMPLETE, D8, D3); see the module docstring.

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
    # Reconcile reads the STRICT bijection (default ``relax_drafting_bijection``;
    # ADR 009 / D1): the torn ``set-chapters`` COMPLETE precedence below is driven
    # by ``manifest-disk-bijection`` firing at ``phase=drafting``, so the
    # user-facing ``check`` relaxation must not reach this caller.
    fired = [
        violation.invariant for violation in check_disk_evidence(state, working_dir)
    ]
    # The two scoped exceptions that run ahead of the refuse arm (the torn
    # ``set-chapters`` COMPLETE, ADR 008/D8; then the relaxed drafting-subset
    # cover-gap RECOUNT, roadmap task 2.3.8/D3), in their pinned order.
    scoped = _scoped_precedence_exception(state, working_dir, fired)
    if scoped is not None:
        return scoped
    refuse = [name for name in fired if name in _REFUSE_CLASS]
    if refuse:
        return _refuse(refuse)
    if state.pending_turn is not None and PENDING_TURN_CLEARED in fired:
        return _classify_pending_turn(
            state.pending_turn, working_dir, [PENDING_TURN_CLEARED]
        )
    recount_names = [
        name
        for name in DISK_EVIDENCE_INVARIANT_NAMES
        if name in _RECOUNT_TRIGGERS and name in fired
    ]
    if recount_names:
        return _recount(state, working_dir, recount_names)
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
