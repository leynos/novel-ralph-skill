"""The deliberately incoherent variants and the ``done.flag`` permutations.

``INCOHERENT_VARIANTS`` maps each named variant to a ``(spec, invariant-name)``
pair: the spec breaks exactly the one §5.2 or §5.4 invariant the string names and
no other (the corpus self-test proves the isolation). Every variant is a minimal
mutation of ``COHERENT_BASELINE`` so the broken invariant is the only difference.

``DONE_FLAG_PERMUTATIONS`` (Work item 4) carries coherent multi-chapter trees
differing only in which chapters carry ``done.flag``.
"""

from __future__ import annotations

import dataclasses as dc

from . import _oracle as oracle
from ._library import COHERENT_BASELINE
from ._specs import GATE_THRESHOLDS, ChapterSpec, WorkingTreeSpec

_BASE = COHERENT_BASELINE
_BASE_CHAPTERS = _BASE.chapters


def _consistent_gates(chapters: tuple[ChapterSpec, ...]) -> dict[str, bool]:
    """Return knitting-gate booleans honestly crossed by ``chapters`` drafts."""
    ratio = sum(chapter.draft_words for chapter in chapters) / _BASE.target_words
    low, mid, high = GATE_THRESHOLDS
    return {
        "done_30": ratio >= low,
        "done_50": ratio >= mid,
        "done_80": ratio >= high,
    }


def _with_chapters(
    chapters: tuple[ChapterSpec, ...], **changes: object
) -> WorkingTreeSpec:
    """Return the baseline with replaced chapters, honest gates, and changes.

    Explicit gate booleans in ``changes`` override the honest defaults, so a
    gate-inconsistency variant can deliberately set a gate against the ratio.
    """
    fields: dict[str, object] = {"chapters": chapters, **_consistent_gates(chapters)}
    fields.update(changes)
    return dc.replace(_BASE, **fields)


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
    }


INCOHERENT_VARIANTS: dict[str, tuple[WorkingTreeSpec, str]] = (
    _build_incoherent_variants()
)


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
