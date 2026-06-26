"""Scoped precedence predicates for the reconciliation derivation.

These pure helpers classify the two scoped exceptions that run ahead of the
refuse-class arm in
:func:`~novel_ralph_skill.state.reconcile.derive_reconciliation`: the torn
``set-chapters`` COMPLETE precedence (ADR 008, Decision D8) and the relaxed
drafting-subset cover-gap RECOUNT pre-arm (roadmap task 2.3.8, Decision D3). They
live in their own module so ``reconcile.py`` stays within the AGENTS.md 400-line
cap once the second pre-arm is added, and are imported back into ``reconcile`` so
every existing caller resolves unchanged.

The refuse-class vocabulary (:data:`_REFUSE_CLASS`), the recomputable-basename set
(:data:`_RECOMPUTABLE_BASENAMES`), and the declared-path reader
(:func:`_missing_declared_paths`) live here too because the predicates and the
reconciliation builders both read them; ``reconcile`` re-imports each so its
precedence and pending-turn classification are unchanged.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state._disk_paths import (
    _classify_bijection,
    _declared_chapter_numbers,
    _on_disk_chapter_numbers,
)
from novel_ralph_skill.state._disk_word_counts import _check_word_counts_cover_drafts
from novel_ralph_skill.state.disk_evidence import (
    COMPILED_MATCHES_DRAFTS,
    CURSOR_PLAN_PRESENT,
    DONE_FLAG_WITHOUT_DRAFT,
    MANIFEST_DISK_BIJECTION,
)
from novel_ralph_skill.state.phase import Phase
from novel_ralph_skill.state.schema import SET_CHAPTERS_OPERATION

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# The refuse-class disk-evidence names: the three §5.4 contradictions plus the
# reported-not-repaired ``cursor-plan-present`` (D-REPORT). Any one present means
# disk contradicts itself (or carries a plan-less cursor ``reconcile`` cannot
# synthesise without fabricating prose), so the verdict is REFUSE — *except* the
# two scoped exceptions below, each of which fires only when the fired refuse-class
# is exactly ``{manifest-disk-bijection}`` so it never masks a second contradiction.
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


def _set_chapters_turn_explains_bijection(
    state: State, working_dir: Path, fired: cabc.Sequence[str]
) -> bool:
    """Return whether a torn ``set-chapters`` turn fully explains the bijection break.

    True only when ALL hold (the scoped precedence exception; ADR 008, D8):

    - ``state.pending_turn`` is present with ``operation == "set-chapters"``;
    - the fired refuse-class set is **exactly** ``{manifest-disk-bijection}`` (no
      other refuse-class member, so the branch never masks a second contradiction);
    - the bijection break is **fully explained** by the pending turn's
      declared-but-missing chapter directories: the manifest is contiguous from 1,
      the on-disk chapter numbers are a subset of the manifest, and the manifest
      minus the on-disk set equals exactly the missing declared chapter numbers.

    When false the existing REFUSE arm runs unchanged, so any unexplained break — a
    stray draft, an orphan directory, a manifest gap the turn does not account for,
    or a malformed declaration — still REFUSEs.
    """
    pending = state.pending_turn
    if pending is None or pending.operation != SET_CHAPTERS_OPERATION:
        return False
    fired_refuse = {name for name in fired if name in _REFUSE_CLASS}
    if fired_refuse != {MANIFEST_DISK_BIJECTION}:
        return False
    break_ = _classify_bijection(
        (chapter.number for chapter in state.chapters),
        _on_disk_chapter_numbers(working_dir),
    )
    # The manifest must be contiguous from 1 with the on-disk set its subset (no
    # orphan) — exactly ``coherent_subset`` — before the missing dirs can explain
    # the break.
    if not break_.coherent_subset:
        return False
    missing_declared = _declared_chapter_numbers(
        _missing_declared_paths(pending.paths, working_dir)
    )
    if missing_declared is None:
        return False
    return break_.missing == missing_declared


def _drafting_subset_cover_gap(
    state: State, working_dir: Path, fired: cabc.Sequence[str]
) -> bool:
    """Return whether a relaxed drafting subset carries a repairable cover gap.

    True only when ALL hold (the scoped, drafting-gated pre-arm; roadmap task
    2.3.8, Decision D3):

    - ``state.pending_turn`` is ``None`` — no uncleared ``[pending_turn]``, so a
      torn non-``set-chapters`` turn (e.g. ``write-draft``) on a coherent subset
      with a cover gap falls through to the pending-turn arm for its
      COMPLETE/ROLLBACK rather than being masked (review blocking point B2);
    - ``state.phase.current == Phase.DRAFTING`` — the only phase the bijection
      relaxation accepts a disk subset of the manifest (ADR 009);
    - the strict bijection break is a coherent subset (no orphan, contiguous
      manifest, ``on_disk < manifest``) — the shape ADR 009 certifies honest;
    - the fired refuse-class set is **exactly** ``{manifest-disk-bijection}`` (the
      analogue of :func:`_set_chapters_turn_explains_bijection`'s guard), so a
      co-occurring second contradiction still REFUSEs (B2); and
    - the re-keyed cover-drafts detector (``relax_drafting=True``) reports a
      missing-direction violation — a drafted chapter the table omits.

    When false the existing precedence runs unchanged, so the strict bijection
    still REFUSEs on any non-subset break and a non-drafting phase, and the
    set-chapters COMPLETE and pending-turn arms keep their precedence
    (Constraint 1, ADR 008).
    """
    if state.pending_turn is not None:
        return False
    if state.phase.current != Phase.DRAFTING:
        return False
    manifest = {chapter.number for chapter in state.chapters}
    on_disk = _on_disk_chapter_numbers(working_dir)
    is_subset = (
        on_disk < manifest and _classify_bijection(manifest, on_disk).coherent_subset
    )
    if not is_subset:
        return False
    fired_refuse = {name for name in fired if name in _REFUSE_CLASS}
    if fired_refuse != {MANIFEST_DISK_BIJECTION}:
        return False
    return (
        _check_word_counts_cover_drafts(state, working_dir, relax_drafting=True)
        is not None
    )
