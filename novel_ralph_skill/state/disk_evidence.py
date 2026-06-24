"""The §5.4 disk-evidence invariant detector behind disk-aware ``check``.

:func:`check_disk_evidence` is the §5.4 twin of
:func:`~novel_ralph_skill.state.validate.validate_state`: where the validator
decides whether a :class:`~novel_ralph_skill.state.schema.State` contradicts
*itself*, this detector decides whether the state has drifted from the on-disk
``working/`` tree. It reads the manuscript directory and ``state.toml``-derived
view together and returns the disk-evidence invariants the tree violates (design
§3.3, §5.4; roadmap task 2.3.2).

It owns six invariant names. Five are the names already reserved by the corpus
oracle's ``CORPUS_INVARIANT_NAMES`` (``manifest-disk-bijection``,
``done-flag-without-draft``, ``compiled-matches-drafts``,
``pending-turn-cleared``, ``cursor-plan-present``); the sixth,
``word-counts-match-drafts``, is **new this task** — the disk-vs-table per-chapter
word-count divergence that realises the roadmap's done-claim case (ExecPlan
Decision Log D-WORDCOUNT). Each name is spelled exactly as the corpus oracle's
matching entry, and the equality is pinned by a test (D-NAMES).

The predicates are **deliberate twins** of the same-named checks in
``tests/working_corpus/_oracle.py`` (the oracle's disk-evidence checks read the
materialised ``working/`` tree, this detector reads the materialised ``State``
and the same disk). The duplication is
intentional: the oracle is an independent cross-check and must not import the
thing it checks, and vice versa. The two sides are pinned to agree on every
corpus tree by ``tests/test_novel_state_check_disk.py``'s agreement suite and the
``tests/test_disk_evidence.py`` twin-equality tests (the deliberate-twin policy,
developers' guide §"Invariant validation").

All six twins now read disk on both sides (roadmap task 2.3.3): the corpus
``_check_manifest_disk_bijection``, ``_check_done_flag_without_draft``, and
``_check_compiled_matches_drafts`` were rerouted from reading the
``WorkingTreeSpec`` to reading the materialised ``working/`` tree, joining the
``cursor-plan``, ``by-chapter-sum``, and ``word-counts-match-drafts`` twins that
already did, so the cross-check is genuinely disk-vs-disk on every invariant.

The detector is **total**: every predicate returns a ``Violation | None`` for
every constructible ``State`` over any ``working_dir``. The word-count predicate
reuses the shared :func:`~novel_ralph_skill.state.wordcount.recount_words`, the
one counting rule (``len(text.split())``), so no second counter exists.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state.compile_model import concatenate_drafts
from novel_ralph_skill.state.validate import Violation
from novel_ralph_skill.state.wordcount import recount_words

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# The §5.4 disk-evidence invariant names this task owns. The first five are the
# names the corpus oracle already reserved (``CORPUS_INVARIANT_NAMES``); the
# sixth is new this task (D-WORDCOUNT). Each string equals the oracle's matching
# entry (the equality is pinned by a test).
MANIFEST_DISK_BIJECTION: typ.Final = "manifest-disk-bijection"
DONE_FLAG_WITHOUT_DRAFT: typ.Final = "done-flag-without-draft"
COMPILED_MATCHES_DRAFTS: typ.Final = "compiled-matches-drafts"
PENDING_TURN_CLEARED: typ.Final = "pending-turn-cleared"
CURSOR_PLAN_PRESENT: typ.Final = "cursor-plan-present"
WORD_COUNTS_MATCH_DRAFTS: typ.Final = "word-counts-match-drafts"

# The owned set, in design §5.2/§5.4 order, for callers that need to distinguish
# the disk-evidence verdict from the pure-state verdict. The order is the corpus
# oracle's disk-evidence subset order, with the new word-count name appended.
DISK_EVIDENCE_INVARIANT_NAMES: tuple[str, ...] = (
    MANIFEST_DISK_BIJECTION,
    CURSOR_PLAN_PRESENT,
    DONE_FLAG_WITHOUT_DRAFT,
    COMPILED_MATCHES_DRAFTS,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_MATCH_DRAFTS,
)


def _chapter_dir_name(number: int) -> str:
    """Return the ``chapter-NN`` directory name for a one-based chapter number."""
    return f"chapter-{number:02d}"


def _on_disk_chapter_numbers(working_dir: Path) -> set[int]:
    """Return the chapter numbers materialised under ``manuscript/``.

    Globs ``manuscript/chapter-*`` directories and parses the two-digit suffix.
    A directory whose suffix is not a valid ``chapter-NN`` integer is ignored, so
    a stray non-chapter directory never crashes the bijection check.
    """
    numbers: set[int] = set()
    for entry in (working_dir / "manuscript").glob("chapter-*"):
        if not entry.is_dir():
            continue
        suffix = entry.name.removeprefix("chapter-")
        if suffix.isdigit():
            numbers.add(int(suffix))
    return numbers


def _check_manifest_disk_bijection(state: State, working_dir: Path) -> Violation | None:
    """Return a violation when manifest and chapter dirs are not in bijection.

    Every ``state.chapters`` entry must have its on-disk ``chapter-NN/`` directory
    and vice versa, and the manifest must be contiguous from 1 with no gaps. A
    manifest entry with no directory (the ``manifest-extra-entry`` variant) and a
    directory with no manifest entry (the ``draft-without-manifest-entry`` variant)
    both break the bijection. Disk-reading twin of the oracle's
    ``_check_manifest_disk_bijection`` (both sides now read disk; roadmap 2.3.3).
    """
    manifest = {chapter.number for chapter in state.chapters}
    on_disk = _on_disk_chapter_numbers(working_dir)
    contiguous = sorted(manifest) == list(range(1, len(manifest) + 1))
    if manifest == on_disk and contiguous:
        return None
    return Violation(
        invariant=MANIFEST_DISK_BIJECTION,
        detail=(
            f"manifest chapters {sorted(manifest)} are not in bijection with the "
            f"on-disk chapter directories {sorted(on_disk)}"
        ),
    )


def _check_done_flag_without_draft(state: State, working_dir: Path) -> Violation | None:
    """Return a violation when a ``done.flag`` sits beside an empty/absent draft.

    For each manifest chapter, a ``done.flag`` beside a ``draft.md`` whose
    whitespace-split token count is zero — or beside no ``draft.md`` at all — is a
    contradiction: a chapter cannot be done with nothing drafted (design §5.4). A
    flag beside a *non-empty* draft is coherent and never fires (so the §5.4
    under-count worked case lands as ``word-counts-match-drafts``, not here).
    Disk-reading twin of the oracle's ``_check_done_flag_without_draft`` (both
    sides read each chapter's on-disk ``done.flag`` and ``draft.md``).
    """
    manuscript = working_dir / "manuscript"
    for chapter in state.chapters:
        chapter_dir = manuscript / _chapter_dir_name(chapter.number)
        if not (chapter_dir / "done.flag").exists():
            continue
        draft = chapter_dir / "draft.md"
        drafted = (
            len(draft.read_text(encoding="utf-8").split()) if draft.exists() else 0
        )
        if drafted == 0:
            return Violation(
                invariant=DONE_FLAG_WITHOUT_DRAFT,
                detail=(
                    f"chapter {chapter.number:02d} carries done.flag beside an "
                    f"empty or absent draft.md"
                ),
            )
    return None


def _present_draft_bodies(state: State, working_dir: Path) -> list[str]:
    """Return the present chapters' draft bodies in ascending chapter order.

    Reads each manifest chapter's ``draft.md`` as UTF-8 (an absent draft
    contributes the empty string), ordered by chapter number, so the concatenation
    twin compares like with the corpus ``_disk_present_draft_bodies``.
    """
    manuscript = working_dir / "manuscript"
    bodies: list[str] = []
    for chapter in sorted(state.chapters, key=lambda chapter: chapter.number):
        draft = manuscript / _chapter_dir_name(chapter.number) / "draft.md"
        bodies.append(draft.read_text(encoding="utf-8") if draft.exists() else "")
    return bodies


def _check_compiled_matches_drafts(state: State, working_dir: Path) -> Violation | None:
    """Return a violation when ``compiled.md`` is not the concatenated drafts.

    Recomputes the ordered :func:`concatenate_drafts` of the present drafts and
    compares ``compiled.md``'s bytes against it (design §4.3/§9). A tree with no
    ``compiled.md`` trivially satisfies the check (nothing to diverge from),
    exactly as the oracle's ``_check_compiled_matches_drafts`` treats it (D-COMPILE).
    """
    compiled = working_dir / "manuscript" / "compiled.md"
    if not compiled.exists():
        return None
    expected = concatenate_drafts(_present_draft_bodies(state, working_dir))
    if compiled.read_text(encoding="utf-8") == expected:
        return None
    return Violation(
        invariant=COMPILED_MATCHES_DRAFTS,
        detail="compiled.md is not the ordered concatenation of the present drafts",
    )


def _check_pending_turn_cleared(state: State, _working_dir: Path) -> Violation | None:
    """Return a violation when an uncleared ``[pending_turn]`` record is present.

    A populated ``state.pending_turn`` is a torn turn: a tree whose state file
    still records an operation in flight, which reconciliation must complete or
    roll back (design §3.4). Twin of the oracle's ``_check_pending_turn_cleared``.
    """
    if state.pending_turn is None:
        return None
    return Violation(
        invariant=PENDING_TURN_CLEARED,
        detail=(
            f"state records an uncleared pending_turn for "
            f"{state.pending_turn.operation!r}"
        ),
    )


def _check_cursor_plan_present(state: State, working_dir: Path) -> Violation | None:
    """Return a violation when a non-zero scene/beat cursor lacks its on-disk plan.

    The "zero until their plans exist" sub-clause of design §5.2 invariant 6: a
    non-zero ``current_scene`` requires the current chapter's ``scenes.md`` and a
    non-zero ``current_beat`` requires its ``beats.md`` (``state-layout.md`` lines
    38-39, 86-88). This is disk-evidence, so the pure-state validator cannot
    decide it. Guarded by ``0 < current_chapter <= len(chapters)`` so it never
    raises on a malformed cursor and leaves the degenerate ``current_chapter == 0``
    case to the pure-state ``cursor-coherent`` clause. Twin of the oracle's
    ``_check_cursor_plan_present``.
    """
    drafting = state.drafting
    if not 0 < drafting.current_chapter <= len(state.chapters):
        return None
    chapter_dir = (
        working_dir / "manuscript" / _chapter_dir_name(drafting.current_chapter)
    )
    scene_missing = (
        drafting.current_scene > 0 and not (chapter_dir / "scenes.md").exists()
    )
    beat_missing = drafting.current_beat > 0 and not (chapter_dir / "beats.md").exists()
    if not (scene_missing or beat_missing):
        return None
    return Violation(
        invariant=CURSOR_PLAN_PRESENT,
        detail=(
            f"cursor chapter {drafting.current_chapter} has a non-zero "
            f"scene/beat without its on-disk scenes.md/beats.md plan"
        ),
    )


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


# The per-invariant predicates, assembled in :data:`DISK_EVIDENCE_INVARIANT_NAMES`
# order so the verdict order is deterministic (stable for the agreement suite and
# any snapshot).
_PREDICATES: tuple[cabc.Callable[[State, Path], Violation | None], ...] = (
    _check_manifest_disk_bijection,
    _check_cursor_plan_present,
    _check_done_flag_without_draft,
    _check_compiled_matches_drafts,
    _check_pending_turn_cleared,
    _check_word_counts_match_drafts,
)


def check_disk_evidence(state: State, working_dir: Path) -> tuple[Violation, ...]:
    """Return the §5.4 disk-evidence invariants ``state`` violates against disk.

    An empty tuple means the state is coherent against the on-disk ``working/``
    tree under the disk-evidence invariants this detector owns. Pure-state
    invariants (§5.2) are not checked here; ``check`` unions the two verdicts. The
    verdict is ordered by :data:`DISK_EVIDENCE_INVARIANT_NAMES`.

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` to check against disk.
    working_dir : pathlib.Path
        The materialised ``working/`` directory holding ``manuscript/``.

    Returns
    -------
    tuple[Violation, ...]
        The ordered disk-evidence violations, or an empty tuple when coherent.
    """
    return tuple(
        violation
        for violation in (predicate(state, working_dir) for predicate in _PREDICATES)
        if violation is not None
    )
