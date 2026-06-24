"""The recount-repairable reconciliation variant builders.

These build the incoherent trees the ``reconcile`` mutator repairs or recovers:
the roadmap-2.3.2 set (the over-count done-claim headline, the §5.4 under-count
worked case, and the complete/rollback pending-turn pair) and the roadmap-2.3.6
``word-counts-cover-drafts`` coverage pair (a table that omits a drafted manifest
chapter, and a table carrying an orphan key the manifest never declared). They
live beside the general §5.2/§5.4 variant builders in :mod:`._variants` (which
registers them into ``INCOHERENT_VARIANTS``) rather than inside it so that module
stays within the 400-line cap (AGENTS.md lines 24-27); both import the shared
baseline anchor and helpers from :mod:`._variant_base`.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

from ._specs import ChapterSpec
from ._variant_base import BASE, BASE_CHAPTERS, with_chapters

if typ.TYPE_CHECKING:
    from ._specs import WorkingTreeSpec


def done_flag_real_draft_undercount() -> WorkingTreeSpec:
    """Return the §5.4 worked case: a real ``done.flag`` over an under-counted draft.

    The baseline's first chapter already carries a ``done.flag`` over a non-empty
    24000-word draft (``_drafted_chapters`` flags the leading chapters). This
    variant leaves the chapters — and so the honest drafts and gates — untouched
    and only **under-counts** that first chapter in the ``[word_counts]`` table:
    ``by_chapter_override`` records ``20000`` for ``"01"`` against its real ``24000``
    drafted tokens, with the other two entries derived from their drafts.

    Because a ``done.flag`` sits beside a **non-empty** draft, the
    ``done-flag-without-draft`` contradiction (which keys on ``draft_words == 0``)
    never fires — the tree's sole disk-evidence violation is
    ``word-counts-match-drafts`` → ``RECOUNT`` (round-4 blocking point B2). The
    under-count is **strictly sub-threshold** (D-GATES): the table total
    ``20000 + 24000 + 20800 = 64800`` is ``0.81`` of the 80000 target, so it crosses
    exactly the 30/50/80% thresholds the honest 68800-word (``0.86``) draft total
    crosses; ``gate-ratio-consistent`` holds against both the table total and the
    post-recount draft total. ``current`` is pinned to the table sum so
    ``by-chapter-sum`` stays satisfied.
    """
    _first, second, third = BASE_CHAPTERS
    table = {
        "01": 20000,
        f"{second.number:02d}": second.draft_words,
        f"{third.number:02d}": third.draft_words,
    }
    return with_chapters(
        BASE_CHAPTERS,
        current_chapter=len(BASE_CHAPTERS),
        by_chapter_override=table,
        current_words_override=sum(table.values()),
    )


def done_claim_stale_word_counts() -> WorkingTreeSpec:
    """Return the roadmap headline: a settled tree claiming an uncorroborated done.

    The first baseline chapter is emptied — ``draft_words=0``, ``write_draft=False``,
    and **``has_done_flag=False``** — so on disk it is a chapter directory with no
    ``draft.md`` and no ``done.flag``; the ``by_chapter_override`` then records a
    **positive** ``10000`` for that chapter (the "done claim" the drafts do not
    corroborate), with the other two entries derived from their drafts and
    ``current`` pinned to the table sum so ``by-chapter-sum`` stays satisfied.

    ``has_done_flag=False`` is load-bearing: a ``done.flag`` over the empty draft
    would trip the ``done-flag-without-draft`` *contradiction* (refuse dominates
    recount), defeating "repaired by reconcile" (round-3 blocking point 2). With no
    flag, the tree's **sole** disk-evidence violation is ``word-counts-match-drafts``
    → ``RECOUNT`` — exactly the roadmap clause "state claims a chapter is done **but
    no done.flag exists**" (D-SCOPE).

    The phantom entry is **strictly sub-threshold** (D-GATES, round-4 B1): the table
    total ``10000 + 24000 + 20800 = 54800`` is ``0.685`` of the 80000 target, and the
    honest 44800-word draft total is ``0.56`` — both cross the 30/50% thresholds and
    neither crosses 80%, so ``consistent_gates`` (computed from the draft total)
    stays consistent with the table total before the recount and the draft total
    after it. ``gate-ratio-consistent`` is silent throughout, so the post-repair
    ``check`` exits ``0``.
    """
    first, second, third = BASE_CHAPTERS
    empty = dc.replace(first, draft_words=0, write_draft=False, has_done_flag=False)
    table = {
        "01": 10000,
        f"{second.number:02d}": second.draft_words,
        f"{third.number:02d}": third.draft_words,
    }
    return with_chapters(
        (empty, second, third),
        current_chapter=len(BASE_CHAPTERS),
        by_chapter_override=table,
        current_words_override=sum(table.values()),
    )


def cover_omits_drafted_chapter() -> WorkingTreeSpec:
    """Return a tree whose ``by_chapter`` omits a drafted manifest chapter.

    The tree drafts four chapters against the 80000 target — three of 32000 and a
    *small* fourth of 4000 (live total 100000, ratio 1.25, every knitting gate
    honestly ``True``) — and the override drops the small fourth chapter's ``"04"``
    key from ``[word_counts].by_chapter`` while keeping its non-empty ``draft.md``
    on disk. The manifest-keyed recount therefore carries ``"04"`` but the table
    does not: the ``word-counts-cover-drafts`` coverage gap (roadmap task 2.3.6).

    The omitted chapter is deliberately small so the surviving table sum
    (``96000``, ratio ``1.2``) stays in the **same all-gates-``True`` band** as the
    live total. This matters because the pure-state validator's
    ``gate-ratio-consistent`` reads ``sum(by_chapter.values())`` — the *table*
    sum, not the on-disk ``draft_words`` — so an omission that pushed the table
    ratio below ``0.80`` would flip ``done_80`` and double-fire that invariant
    (ExecPlan Surprise: the plan's Risk #2 conflated the oracle's draft-reading
    gate check with the validator's table-reading one). ``current`` is pinned to
    the reduced table sum so ``by-chapter-sum`` stays silent, the three retained
    keys keep their honest counts so the shared-key value match
    ``word-counts-match-drafts`` stays silent, and the manifest/disk bijection
    holds so the cover predicate fires on the lone hand-edited-key divergence. A
    ``RECOUNT`` re-keys ``by_chapter`` off the manifest, supplying the missing
    ``"04"`` key.
    """
    chapters = tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=words,
            draft_words=words,
            has_done_flag=False,
        )
        for index, words in enumerate((32000, 32000, 32000, 4000))
    )
    table = {f"{chapter.number:02d}": chapter.draft_words for chapter in chapters[:3]}
    return with_chapters(
        chapters,
        current_chapter=len(chapters),
        by_chapter_override=table,
        current_words_override=sum(table.values()),
    )


def cover_extra_table_key() -> WorkingTreeSpec:
    """Return a tree whose ``by_chapter`` carries a key with no manifest entry.

    The override keeps each drafted chapter's honest count and adds a ``"05"`` key
    the manifest never declares, so the table key set exceeds the manifest-keyed
    recount key set — the ``word-counts-cover-drafts`` coverage gap in the
    opposite direction (roadmap task 2.3.6). ``current`` is pinned to the new
    table sum so ``by-chapter-sum`` stays silent; the orphan key is table-only (no
    manifest entry and no ``manuscript/chapter-05`` directory) so
    ``manifest-disk-bijection`` stays silent; the shared keys keep their honest
    counts so ``word-counts-match-drafts`` stays silent. A ``RECOUNT`` re-keys
    ``by_chapter`` off the manifest, dropping the orphan ``"05"`` key.
    """
    first, second, third = BASE_CHAPTERS
    table = {
        f"{first.number:02d}": first.draft_words,
        f"{second.number:02d}": second.draft_words,
        f"{third.number:02d}": third.draft_words,
        "05": 100,
    }
    return with_chapters(
        (first, second, third),
        by_chapter_override=table,
        current_words_override=sum(table.values()),
    )


def pending_turn_complete_recomputable() -> WorkingTreeSpec:
    """Return an uncleared record whose declared paths are recomputable and present.

    The torn turn declared only the recomputable artefacts ``state.toml`` and
    ``log.md``, both of which the builder always materialises, so no declared path
    is missing: the record is a stale marker over a fully-landed turn, which the
    derivation classifies ``COMPLETE_PENDING_TURN`` with an empty missing set
    (``reconcile`` simply clears it; D-COMPLETE).
    """
    return dc.replace(
        BASE,
        pending_turn={
            "operation": "recount",
            "paths": ["working/state.toml", "working/log.md"],
        },
    )


def pending_turn_rollback_unrecoverable() -> WorkingTreeSpec:
    """Return an uncleared record whose missing declared path is an unrecoverable draft.

    The torn turn declared ``working/manuscript/chapter-99/draft.md`` — a chapter
    the baseline never materialises — so the declared artefact is a *missing
    unrecoverable* ``draft.md``: the derivation classifies ``ROLLBACK_PENDING_TURN``
    (the record is cleared, the partial artefacts left in place, prose never
    fabricated; D-COMPLETE).
    """
    return dc.replace(
        BASE,
        pending_turn={
            "operation": "write-draft",
            "paths": ["working/manuscript/chapter-99/draft.md"],
        },
    )
