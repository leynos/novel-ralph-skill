"""The §5.4 word-count disk-evidence twins, split from the disk-evidence detector.

This module holds the disk-vs-table word-count cluster of
:mod:`novel_ralph_skill.state.disk_evidence` — the shared recount reader
:func:`disk_word_counts` and the two predicates it backs,
:func:`_check_word_counts_match_drafts` (the shared-key *value* divergence;
roadmap task 2.3.2) and :func:`_check_word_counts_cover_drafts` (the ``by_chapter``
*key-set* coverage divergence; roadmap task 2.3.6, re-keyed off the on-disk drafted
subset under the ADR 009 ``relax_drafting`` flag by roadmap task 2.3.8). They are
split out purely for file size (AGENTS.md 400-line cap) and re-exported through
``disk_evidence`` so every existing import site (``reconcile``, the ``state``
package, the tests) resolves unchanged.

The recount reuses the shared
:func:`~novel_ralph_skill.state.wordcount.recount_words`, the one counting rule
(``len(text.split())``), so no second counter exists. Each predicate is the
disk-reading twin of the same-named corpus oracle predicate; the two sides are
pinned to agree by the ``tests/test_disk_evidence.py`` twin-equality tests.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state._disk_paths import (
    _classify_bijection,
    _on_disk_chapter_numbers,
)
from novel_ralph_skill.state.phase import Phase
from novel_ralph_skill.state.validate import Violation
from novel_ralph_skill.state.wordcount import recount_words

WORD_COUNTS_MATCH_DRAFTS: typ.Final = "word-counts-match-drafts"
WORD_COUNTS_COVER_DRAFTS: typ.Final = "word-counts-cover-drafts"

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import State


def disk_word_counts(
    state: State, working_dir: Path
) -> tuple[int, cabc.Mapping[str, int]]:
    """Return the disk-derived ``(current, by_chapter)`` for ``state``'s manifest.

    Reuses the shared :func:`~novel_ralph_skill.state.wordcount.recount_words`
    over ``state.chapters`` — the one counting rule (``len(text.split())``) — so
    the disk-vs-table divergence and the ``reconcile`` recount derive the same
    numbers from the same reader (no second counter; D-WORDCOUNT). Exposed so the
    shared reconciliation can carry the recount payload without re-reading disk.

    Parameters
    ----------
    state : State
        The parsed ``state.toml``; its ``chapters`` manifest keys the recount.
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.

    Returns
    -------
    tuple[int, collections.abc.Mapping[str, int]]
        The recounted total and the ordered per-chapter mapping.
    """
    return recount_words(working_dir, state.chapters)


def _check_word_counts_match_drafts(
    state: State, working_dir: Path
) -> Violation | None:
    """Return a violation when the ``[word_counts]`` table is stale against drafts.

    Recomputes the per-chapter token counts from the on-disk drafts via
    :func:`disk_word_counts` and compares the recomputed ``by_chapter`` mapping
    against ``state.word_counts.by_chapter``. When they differ, the table is
    internally consistent but stale against the manuscript: the disk-vs-table
    divergence that realises the roadmap's done-claim case and its §5.4 under-count
    inverse (D-WORDCOUNT). This is the disk-reading signal the table-internal
    ``by-chapter-sum`` invariant cannot see.

    The comparison is over ``by_chapter`` **only**, never ``current``: ``current``
    versus ``sum(by_chapter)`` is the orthogonal table-internal ``by-chapter-sum``
    invariant's concern (D-WORDCOUNT). Keeping them orthogonal means a tree whose
    ``current`` is hand-corrupted (the ``by-chapter-sum-mismatch`` variant) trips
    only ``by-chapter-sum``, while a stale per-chapter table trips only this one; a
    ``RECOUNT`` (which rewrites both ``current`` and ``by_chapter``) satisfies both
    by construction. Twin of the corpus's new disk-reading
    ``_check_word_counts_match_drafts``.

    Only the **shared** chapter keys are compared. A key present in the
    recount but absent from the table (or the reverse) is a manifest-to-disk
    structural mismatch the ``manifest-disk-bijection`` contradiction owns, so this
    value-divergence predicate stays silent on it — the two invariants do not
    double-fire on one tree.
    """
    _current, by_chapter = disk_word_counts(state, working_dir)
    table = dict(state.word_counts.by_chapter)
    shared = set(by_chapter) & set(table)
    if all(by_chapter[key] == table[key] for key in shared):
        return None
    return Violation(
        invariant=WORD_COUNTS_MATCH_DRAFTS,
        detail="[word_counts].by_chapter table is stale against the on-disk drafts",
    )


def _drafted_subset_cover_violation(
    state: State, working_dir: Path, on_disk: cabc.Set[int]
) -> Violation | None:
    """Return a violation when a drafted on-disk chapter has no ``by_chapter`` key.

    The relaxed drafting-subset arm of :func:`_check_word_counts_cover_drafts`
    (roadmap task 2.3.8). "Drafted" means **directory-present** — the chapter
    numbers ``on_disk`` carries — not "non-empty ``draft.md``" (Decision D6): a
    chapter directory with an absent or empty draft (count ``0``) is still on disk
    and must carry a key, so convergence holds after the manifest-keyed
    ``recount_words`` writes its ``0`` key.

    Only the **missing** direction fires (Decision D2): a drafted chapter whose
    key the table omits. The symmetric *extra* direction is deliberately not
    checked here — the manifest-keyed ``recount_words`` writes a ``0``-valued key
    for every undrafted manifest chapter, so a table that legitimately carries
    those keys after a ``RECOUNT`` must not re-trip the detector on its own repair.
    """
    drafted_keys = {f"{number:02d}" for number in on_disk}
    table_keys = set(state.word_counts.by_chapter)
    missing = drafted_keys - table_keys
    if not missing:
        return None
    return Violation(
        invariant=WORD_COUNTS_COVER_DRAFTS,
        detail=(
            "[word_counts].by_chapter omits a drafted chapter's key during a "
            f"relaxed drafting subset: missing {sorted(missing)}"
        ),
    )


def _check_word_counts_cover_drafts(
    state: State, working_dir: Path, *, relax_drafting: bool = False
) -> Violation | None:
    """Return a violation when the ``by_chapter`` key set diverges from the drafts.

    Recomputes the manifest-keyed disk ``by_chapter`` via :func:`disk_word_counts`
    (one entry per manifest chapter) and compares its key set against
    ``state.word_counts.by_chapter``'s key set. A recount key absent from the
    table is a drafted manifest chapter the table omits; a table key absent from
    the recount is a key the manifest never declared. Both are pure key-coverage
    divergences a ``RECOUNT`` repairs by re-keying off the manifest (roadmap task
    2.3.6).

    This is orthogonal to the shared-key value match
    :func:`_check_word_counts_match_drafts` owns (which compares only the keys
    both sides share) and to the manifest-vs-disk-dir structural check
    :func:`~novel_ralph_skill.state.disk_evidence._check_manifest_disk_bijection`
    owns. At bijection (``manifest == on_disk``) it runs the full symmetric
    difference: the surviving signal is exactly the hand-edited-table key-set
    divergence (roadmap task 2.3.6). Twin of the corpus's
    ``_check_word_counts_cover_drafts``.

    When ``relax_drafting`` is set and ``state.phase.current == Phase.DRAFTING``
    and the manifest/disk break is a coherent subset (no orphan, contiguous
    manifest, ``on_disk < manifest``), it re-keys off the **on-disk drafted
    subset** and fires only the *missing* direction (roadmap task 2.3.8;
    Decisions D2, D6): a drafted chapter the table omits is flagged mid-draft.
    Outside that exact shape — a non-subset break, a non-drafting phase, or the
    strict default — it **defers** (``return None``) exactly as before: a
    non-bijective manifest is the ``manifest-disk-bijection`` invariant's signal,
    and the manifest-keyed recount would otherwise double-fire on every
    structural mismatch.
    """
    manifest = {chapter.number for chapter in state.chapters}
    on_disk = _on_disk_chapter_numbers(working_dir)
    if manifest == on_disk:
        _current, by_chapter = disk_word_counts(state, working_dir)
        table = dict(state.word_counts.by_chapter)
        missing = set(by_chapter) - set(table)
        extra = set(table) - set(by_chapter)
        if not (missing or extra):
            return None
        return Violation(
            invariant=WORD_COUNTS_COVER_DRAFTS,
            detail=(
                "[word_counts].by_chapter key set diverges from the manifest "
                f"drafts: missing {sorted(missing)}, extra {sorted(extra)}"
            ),
        )
    drafting = relax_drafting and state.phase.current == Phase.DRAFTING
    is_subset = (
        on_disk < manifest and _classify_bijection(manifest, on_disk).coherent_subset
    )
    if drafting and is_subset:
        return _drafted_subset_cover_violation(state, working_dir, on_disk)
    return None
