"""The divergent-table corpus trees (roadmap 2.1.5, 2.1.6).

These two specs make the ``[word_counts].by_chapter`` table deliberately *belie*
the on-disk drafts on both proxy quantities, so the draft-reading live oracle and
the table-reading §5.2 validator disagree. They are split out of
:mod:`tests.working_corpus._variants` purely for file size (AGENTS.md 400-line
cap) and re-exported through it so existing import sites resolve unchanged.

Neither tree is an ``INCOHERENT_VARIANTS`` member (Decision Log D1): each breaks
an owned name under ``corpus_check`` while the validator breaks none.
"""

from __future__ import annotations

from ._specs import ChapterSpec, WorkingTreeSpec
from ._variant_base import with_chapters as _with_chapters


def _over_counting_table_spec() -> WorkingTreeSpec:
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


def _under_counting_table_spec() -> WorkingTreeSpec:
    """Return a tree whose ``by_chapter`` table under-counts its on-disk drafts.

    The mirror of :func:`_over_counting_table_spec` (roadmap 2.1.6). The tree
    drafts three chapters of 30000 words each (live: 90000 words, three drafted
    chapters) against an 80000 target, but overrides ``by_chapter`` to two entries
    of 4000 (table: 8000 words, two entries ``> 0``) with ``current`` pinned to the
    table sum so ``by-chapter-sum`` stays silent (Decision Log D3). All three
    knitting gates are forced ``False``, ``consecutive_clean`` is 2 with a
    ``convergence_target`` of 3, and ``current_chapter`` is pinned to 3 so
    ``cursor-coherent`` stays silent under the live read.

    Because ``_with_chapters`` computes honest gates from the drafts (the live
    1.125 ratio would make ``_consistent_gates`` return all-``True``, the opposite
    of what the divergence needs), every divergent field — including the
    explicitly ``False`` gates — is set in ``changes`` rather than relying on
    inheritance.

    Unlike the over-counting tree this fires exactly **one** owned proxy under the
    spec-draft :func:`corpus_check`. The live 1.125 ratio contradicts the
    all-``False`` gates, so ``gate-ratio-consistent`` fires; but
    ``consecutive-clean-within-drafted`` cannot fire on the live side, because when
    the table *under*-counts the chapter count it becomes a *smaller* ceiling than
    the live count, never exceeded by a ``consecutive_clean`` (2) that stays within
    both the live (3) and the table (2) drafted-chapter counts (Decision Log D2).
    The table-reading §5.2 validator, seeing the table's 0.10 ratio matching the
    all-``False`` gates and two drafted entries, names neither proxy. That
    single-proxy disagreement is the discriminator that kills a
    ``min(live, table)``-style mutant of ``live_draft_counts`` which the
    over-counting tree alone cannot catch.
    """
    chapters = tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=30000,
            draft_words=30000,
            has_done_flag=False,
        )
        for index in range(3)
    )
    return _with_chapters(
        chapters,
        consecutive_clean=2,
        convergence_target=3,
        current_chapter=3,
        by_chapter_override={"01": 4000, "02": 4000},
        current_words_override=8000,
        done_30=False,
        done_50=False,
        done_80=False,
    )


# Divergent-table trees (roadmap 2.1.5, 2.1.6): the ``[word_counts].by_chapter``
# table deliberately *belies* the on-disk drafts on both proxy quantities, so the
# draft-reading live oracle and the table-reading §5.2 validator disagree. Neither
# is an ``INCOHERENT_VARIANTS`` member (Decision Log D1): each breaks an owned name
# under ``corpus_check`` while the validator breaks none. The over-counting member
# makes the table over-state both quantities (the live oracle fires both proxies);
# the under-counting member makes the table under-state them (the live oracle fires
# only ``gate-ratio-consistent`` — Decision Log D2). The under-counting tree exists
# to kill a ``min(live, table)``-style mutant of ``live_draft_counts`` that
# mishandles only over-counts and survives the over-counting tree alone.
DIVERGENT_TABLE_VARIANTS: dict[str, WorkingTreeSpec] = {
    "by-chapter-override-over-counts-drafts": _over_counting_table_spec(),
    "by-chapter-override-under-counts-drafts": _under_counting_table_spec(),
}
