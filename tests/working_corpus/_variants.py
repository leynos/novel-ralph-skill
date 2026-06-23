"""The incoherent variants, ``done.flag`` permutations, and divergent tables.

``INCOHERENT_VARIANTS`` maps each named variant to a ``(spec, invariant-name)``
pair: the spec breaks exactly the one §5.2 or §5.4 invariant the string names and
no other (the corpus self-test proves the isolation). Every variant is a minimal
mutation of ``COHERENT_BASELINE`` so the broken invariant is the only difference.

``DONE_FLAG_PERMUTATIONS`` carries coherent multi-chapter trees differing only in
which chapters carry ``done.flag``.

``DIVERGENT_TABLE_VARIANTS`` (roadmap 2.1.5) carries trees whose
``[word_counts].by_chapter`` table deliberately *belies* the on-disk ``draft.md``
bodies: the table over-counts both the drafted-words total and the
drafted-chapters count. Such a tree is **not** an ``INCOHERENT_VARIANTS`` member —
under the spec-draft :func:`corpus_check` it breaks two owned proxies
(``consecutive-clean-within-drafted`` and ``gate-ratio-consistent``) while the
table-reading §5.2 validator breaks none, a deliberate validator-versus-oracle
disagreement both the single-invariant self-test and the agreement suites forbid
for an incoherent variant. The category exists to *exercise* that documented
disagreement, so the whole-corpus live-draft agreement loop is discriminating; it
is a finding to investigate, not a drift to align away.
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


def _divergent_table_spec() -> WorkingTreeSpec:
    """Return a tree whose ``by_chapter`` table over-counts its on-disk drafts.

    The tree drafts two chapters of 4000 words each (live: 8000 words, two
    drafted chapters) against an 80000 target, but overrides ``by_chapter`` to
    three entries of 30000 (table: 90000 words, three entries ``> 0``) with
    ``current`` pinned to the table sum so ``by-chapter-sum`` stays silent
    (Decision Log D3). All three knitting gates are forced ``True``,
    ``consecutive_clean`` is 3 with a matching ``convergence_target``, and
    ``current_chapter`` is pinned to 2 so ``cursor-coherent`` stays silent under
    the live read.

    Because ``_with_chapters`` inherits the baseline's cursor and counter fields
    and leaves the override fields unset, every divergent field is set explicitly
    here rather than relying on inheritance (round-2 advisory A4). Under the
    spec-draft :func:`corpus_check` the live 0.10 ratio contradicts the
    all-``True`` gates and the counter 3 exceeds the two drafted chapters, so the
    oracle names both proxies; the table-reading §5.2 validator, seeing a 1.125
    ratio and three drafted entries, names neither. That disagreement is the
    discriminator the whole-corpus live-draft agreement loop needs.
    """
    chapters = tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=40000,
            draft_words=4000,
            has_done_flag=False,
        )
        for index in range(2)
    )
    return _with_chapters(
        chapters,
        consecutive_clean=3,
        convergence_target=3,
        current_chapter=2,
        by_chapter_override={"01": 30000, "02": 30000, "03": 30000},
        current_words_override=90000,
        done_30=True,
        done_50=True,
        done_80=True,
    )


# Divergent-table trees (roadmap 2.1.5): the ``[word_counts].by_chapter`` table
# over-counts both proxy quantities relative to the on-disk drafts, so the
# draft-reading live oracle and the table-reading §5.2 validator disagree on the
# two proxies. Not an ``INCOHERENT_VARIANTS`` member (Decision Log D1): it breaks
# two owned names under ``corpus_check`` while the validator breaks none.
DIVERGENT_TABLE_VARIANTS: dict[str, WorkingTreeSpec] = {
    "by-chapter-override-over-counts-drafts": _divergent_table_spec(),
}
