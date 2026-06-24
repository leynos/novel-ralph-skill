"""The incoherent variants, ``done.flag`` permutations, and divergent tables.

``INCOHERENT_VARIANTS`` maps each named variant to a ``(spec, invariant-name)``
pair: the spec breaks exactly the one §5.2 or §5.4 invariant the string names and
no other (the corpus self-test proves the isolation). Every variant is a minimal
mutation of ``COHERENT_BASELINE`` so the broken invariant is the only difference.

``DONE_FLAG_PERMUTATIONS`` carries coherent multi-chapter trees differing only in
which chapters carry ``done.flag``.

``DIVERGENT_TABLE_VARIANTS`` (roadmap 2.1.5, 2.1.6) carries trees whose
``[word_counts].by_chapter`` table deliberately *belies* the on-disk ``draft.md``
bodies on both the drafted-words total and the drafted-chapters count. The
over-counting member makes the table *over*-state both quantities; the
under-counting member makes it *under*-state them. Neither is an
``INCOHERENT_VARIANTS`` member — under the spec-draft :func:`corpus_check` each
breaks at least one owned proxy while the table-reading §5.2 validator breaks none,
a deliberate validator-versus-oracle disagreement both the single-invariant
self-test and the agreement suites forbid for an incoherent variant. The
over-counting tree fires both owned proxies (``consecutive-clean-within-drafted``
and ``gate-ratio-consistent``); the under-counting tree fires only
``gate-ratio-consistent``, because an under-counted table chapter ceiling is
smaller than the live count and so cannot drive ``consecutive-clean-within-drafted``
on the live side. Both also trip the disk-evidence ``word-counts-match-drafts``
(per-chapter value divergence) and ``word-counts-cover-drafts`` (the override key
count differs from the manifest, a genuine key-set coverage gap; roadmap task
2.3.6), which the two word-count predicates legitimately split between them. The
category exists to *exercise* that documented disagreement so
the whole-corpus live-draft agreement loop is discriminating: the under-counting
tree kills a ``min(live, table)``-style mutant of ``live_draft_counts`` the
over-counting tree alone misses. Each is a finding to investigate, not a drift to
align away.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

from . import _oracle as oracle
from . import _reconcile_variants as reconcile_variants
from ._specs import ChapterSpec, WorkingTreeSpec
from ._variant_base import (
    BASE as _BASE,
)
from ._variant_base import (
    BASE_CHAPTERS as _BASE_CHAPTERS,
)
from ._variant_base import (
    with_chapters as _with_chapters,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path


def _flag_first_chapter_empty() -> WorkingTreeSpec:
    """Return a spec whose first flagged chapter has an empty ``draft.md``."""
    first, *rest = _BASE_CHAPTERS
    empty = dc.replace(first, draft_words=0, has_done_flag=True)
    return _with_chapters((empty, *rest))


def _flag_first_chapter_absent_draft() -> WorkingTreeSpec:
    """Return a spec whose first flagged chapter has *no* ``draft.md`` at all.

    The chapter carries a ``done.flag`` but the builder suppresses its
    ``draft.md`` write (``write_draft=False``), so on disk the directory holds a
    flag beside an absent draft — the design §5.4 case the always-written empty
    draft cannot reach. ``draft_words`` stays 0 so the oracle's
    ``has_done_flag and draft_words == 0`` branch flags it exactly as it flags
    the empty-draft case.
    """
    first, *rest = _BASE_CHAPTERS
    absent = dc.replace(first, draft_words=0, has_done_flag=True, write_draft=False)
    return _with_chapters((absent, *rest))


def _gate_true_below_threshold() -> WorkingTreeSpec:
    """Return a spec flipping a gate true while ``current`` stays honest.

    Only the ``done_80`` boolean is forced true on a tree whose honest
    ``current/target`` ratio is below the 0.80 threshold; ``current`` is never
    overridden, so invariant 3 stays satisfied and only invariant 7 breaks. The
    baseline's drafted total crosses 0.80, so the chapters are shrunk to drop the
    ratio below it while keeping all three gate booleans set as the baseline had
    them — except ``done_80``, which is now inconsistent.
    """
    smaller = tuple(
        dc.replace(chapter, draft_words=4000, target_words=4000)
        for chapter in _BASE_CHAPTERS
    )
    # 12000 / 80000 = 0.15: below every threshold, so all three gates must be
    # false to be consistent. Forcing done_80 true is the lone invariant-7 break.
    return _with_chapters(smaller, done_30=False, done_50=False, done_80=True)


def _build_incoherent_variants() -> dict[str, tuple[WorkingTreeSpec, str]]:
    """Return the incoherent-variant mapping (spec plus its one invariant name)."""
    first = _BASE_CHAPTERS[0]
    extra = ChapterSpec(
        number=len(_BASE_CHAPTERS) + 1,
        slug=f"chapter-{len(_BASE_CHAPTERS) + 1:02d}",
        title="Extra",
        target_words=1000,
        draft_words=1000,
        has_done_flag=False,
        in_manifest=False,
    )
    return {
        "phase-not-in-enum": (
            dc.replace(_BASE, phase_current="not-a-phase"),
            oracle.PHASE_IN_ENUM,
        ),
        "completed-prefix-gap": (
            dc.replace(_BASE, phase_completed=("premise", "characters")),
            oracle.COMPLETED_PREFIX,
        ),
        "by-chapter-sum-mismatch": (
            # ``current`` is forced to 1 while ``by_chapter`` still derives from
            # the drafts, so on disk ``sum(by_chapter) != current`` — the genuine
            # design §5.2 invariant-3 violation (not a corpus-internal mismatch).
            dc.replace(_BASE, current_words_override=1),
            oracle.BY_CHAPTER_SUM,
        ),
        "consecutive-clean-over-target": (
            dc.replace(_BASE, consecutive_clean=2, convergence_target=1),
            oracle.CONSECUTIVE_CLEAN_WITHIN_TARGET,
        ),
        "convergence-target-below-one": (
            dc.replace(_BASE, consecutive_clean=0, convergence_target=0),
            oracle.CONVERGENCE_TARGET_AT_LEAST_ONE,
        ),
        "consecutive-clean-over-chapters-drafted": (
            _with_chapters(
                (dc.replace(first, has_done_flag=False),),
                consecutive_clean=2,
                convergence_target=3,
                current_chapter=1,
            ),
            oracle.CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
        ),
        "manifest-extra-entry": (
            dc.replace(_BASE, manifest_only_numbers=(len(_BASE_CHAPTERS) + 1,)),
            oracle.MANIFEST_DISK_BIJECTION,
        ),
        "draft-without-manifest-entry": (
            _with_chapters((*_BASE_CHAPTERS, extra)),
            oracle.MANIFEST_DISK_BIJECTION,
        ),
        "cursor-past-current-chapter": (
            dc.replace(_BASE, current_chapter=len(_BASE_CHAPTERS) + 5),
            oracle.CURSOR_COHERENT,
        ),
        "scene-cursor-without-plan": (
            # ``current_scene`` is non-zero but the current chapter carries no
            # ``scenes.md`` (``has_scene_plan`` defaults False). The other cursor
            # stays 0 and the other plan flag stays default, so only the
            # disk-evidence ``cursor-plan-present`` name breaks.
            dc.replace(_BASE, current_scene=1),
            oracle.CURSOR_PLAN_PRESENT,
        ),
        "beat-cursor-without-plan": (
            # ``current_beat`` is non-zero but the current chapter carries no
            # ``beats.md``; the scene cursor stays 0, so only
            # ``cursor-plan-present`` breaks.
            dc.replace(_BASE, current_beat=1),
            oracle.CURSOR_PLAN_PRESENT,
        ),
        "scene-cursor-past-current-chapter": (
            # ``current_chapter == 0`` (no current chapter) with a non-zero
            # ``current_scene``: a scene cursor past the nonexistent current
            # chapter. The disk-evidence ``cursor-plan-present`` guard skips a
            # zero ``current_chapter``, so only the pure-state ``cursor-coherent``
            # name breaks.
            dc.replace(_BASE, current_chapter=0, current_scene=1, current_beat=0),
            oracle.CURSOR_COHERENT,
        ),
        "beat-cursor-past-current-chapter": (
            # The same with a non-zero ``current_beat`` and a zero
            # ``current_scene``; only ``cursor-coherent`` breaks.
            dc.replace(_BASE, current_chapter=0, current_scene=0, current_beat=1),
            oracle.CURSOR_COHERENT,
        ),
        "gate-true-below-threshold": (
            _gate_true_below_threshold(),
            oracle.GATE_RATIO_CONSISTENT,
        ),
        "done-flag-empty-draft": (
            _flag_first_chapter_empty(),
            oracle.DONE_FLAG_WITHOUT_DRAFT,
        ),
        "done-flag-absent-draft": (
            _flag_first_chapter_absent_draft(),
            oracle.DONE_FLAG_WITHOUT_DRAFT,
        ),
        "compiled-not-concatenation-of-drafts": (
            dc.replace(_BASE, compiled="not the real concatenation"),
            oracle.COMPILED_MATCHES_DRAFTS,
        ),
        "uncleared-pending-turn": (
            dc.replace(
                _BASE,
                pending_turn={
                    "operation": "write-draft",
                    "paths": ["working/manuscript/chapter-03/draft.md"],
                },
            ),
            oracle.PENDING_TURN_CLEARED,
        ),
        "word-counts-cover-drafts-omits-drafted-chapter": (
            reconcile_variants.cover_omits_drafted_chapter(),
            oracle.WORD_COUNTS_COVER_DRAFTS,
        ),
        "word-counts-cover-drafts-extra-table-key": (
            reconcile_variants.cover_extra_table_key(),
            oracle.WORD_COUNTS_COVER_DRAFTS,
        ),
        "done-flag-real-draft-undercount": (
            reconcile_variants.done_flag_real_draft_undercount(),
            oracle.WORD_COUNTS_MATCH_DRAFTS,
        ),
        "done-claim-stale-word-counts": (
            reconcile_variants.done_claim_stale_word_counts(),
            oracle.WORD_COUNTS_MATCH_DRAFTS,
        ),
        "pending-turn-complete-recomputable": (
            reconcile_variants.pending_turn_complete_recomputable(),
            oracle.PENDING_TURN_CLEARED,
        ),
        "pending-turn-rollback-unrecoverable": (
            reconcile_variants.pending_turn_rollback_unrecoverable(),
            oracle.PENDING_TURN_CLEARED,
        ),
        "partial-init": (
            # A coherent baseline; ``_remove_log_md`` (in ``_POST_BUILD_MUTATIONS``)
            # unlinks its ``log.md`` after the build so it breaks exactly
            # ``log-present`` (roadmap task 2.3.4).
            _BASE,
            oracle.LOG_PRESENT,
        ),
    }


INCOHERENT_VARIANTS: dict[str, tuple[WorkingTreeSpec, str]] = (
    _build_incoherent_variants()
)


def _remove_log_md(working_dir: Path) -> None:
    """Unlink ``working/log.md`` to materialise the partial-``init`` bootstrap.

    The corpus builder always writes an empty ``log.md``, so the log-absent tree
    roadmap task 2.3.4 detects can only be produced by removing it after the build.
    Applied by the ``incoherent_tree`` fixture for the ``partial-init`` variant and
    nowhere else, so the tree is log-absent exactly where the corpus tests read it.
    """
    (working_dir / "log.md").unlink()


# Post-build mutations keyed by variant name, applied by the ``incoherent_tree``
# fixture after ``build_working_tree``. The registry exists only for the variants
# whose incoherence the spec cannot express (the builder always writes ``log.md``);
# leaving ``INCOHERENT_VARIANTS``'s ``(spec, name)`` shape untouched for the
# existing subscript consumers.
_POST_BUILD_MUTATIONS: dict[str, cabc.Callable[[Path], None]] = {
    "partial-init": _remove_log_md,
}


def _flagged(flags: tuple[bool, ...]) -> WorkingTreeSpec:
    """Return a coherent baseline whose chapters carry ``flags`` ``done.flag``s.

    Every chapter keeps its baseline ``draft_words > 0``, so a flagged chapter is
    never a flag-beside-empty-draft case and the tree stays coherent; only the
    flag pattern varies across permutations.
    """
    chapters = tuple(
        dc.replace(chapter, has_done_flag=flag)
        for chapter, flag in zip(_BASE_CHAPTERS, flags, strict=True)
    )
    return _with_chapters(chapters)


# Coherent multi-chapter trees differing only in which chapters carry
# ``done.flag``: none flagged, all flagged, a leading prefix flagged, and a
# non-contiguous subset flagged (the case a done-predicate must treat as
# not-all-done because a flagged chapter follows an unflagged one).
DONE_FLAG_PERMUTATIONS: dict[str, WorkingTreeSpec] = {
    "none-flagged": _flagged((False, False, False)),
    "all-flagged": _flagged((True, True, True)),
    "leading-prefix-flagged": _flagged((True, True, False)),
    "non-contiguous-subset-flagged": _flagged((True, False, True)),
}
