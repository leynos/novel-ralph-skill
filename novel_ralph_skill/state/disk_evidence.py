"""The §5.4 disk-evidence invariant detector behind disk-aware ``check``.

:func:`check_disk_evidence` is the §5.4 twin of
:func:`~novel_ralph_skill.state.validate.validate_state`: where the validator
decides whether a :class:`~novel_ralph_skill.state.schema.State` contradicts
*itself*, this detector decides whether the state has drifted from the on-disk
``working/`` tree. It reads the manuscript directory and ``state.toml``-derived
view together and returns the disk-evidence invariants the tree violates (design
§3.3, §5.4; roadmap task 2.3.2).

It owns eight invariant names. Five are the names already reserved by the corpus
oracle's ``CORPUS_INVARIANT_NAMES`` (``manifest-disk-bijection``,
``done-flag-without-draft``, ``compiled-matches-drafts``,
``pending-turn-cleared``, ``cursor-plan-present``); ``word-counts-match-drafts``
was added by task 2.3.2 — the disk-vs-table per-chapter word-count *value*
divergence that realises the roadmap's done-claim case (ExecPlan Decision Log
D-WORDCOUNT); ``log-present`` (task 2.3.4) is the partial-``init`` bootstrap
where ``state.toml`` is present but ``log.md`` is absent (``init`` writes
``state.toml`` first, ``log.md`` second, and refuses re-runs); and
``word-counts-cover-drafts`` (roadmap task 2.3.6) is the orthogonal *key-set*
coverage divergence — a ``by_chapter`` table that omits a drafted manifest
chapter or carries a key the manifest never declared. Each name is spelled
exactly as the corpus oracle's matching entry, and the equality is pinned by a
test (D-NAMES).

The predicates are **deliberate twins** of the same-named checks in
``tests/working_corpus/_oracle.py`` (the oracle's disk-evidence checks read the
materialised ``working/`` tree, this detector reads the materialised ``State``
and the same disk). The duplication is
intentional: the oracle is an independent cross-check and must not import the
thing it checks, and vice versa. The two sides are pinned to agree on every
corpus tree by ``tests/test_novel_state_check_disk.py``'s agreement suite and the
``tests/test_disk_evidence.py`` twin-equality tests (the deliberate-twin policy,
developers' guide §"Invariant validation").

The manuscript-comparing twins all read disk on both sides (roadmap task
2.3.3): the corpus ``_check_manifest_disk_bijection``,
``_check_done_flag_without_draft``, and ``_check_compiled_matches_drafts`` were
rerouted from reading the ``WorkingTreeSpec`` to reading the materialised
``working/`` tree, joining the ``cursor-plan``, ``by-chapter-sum``, and
``word-counts-match-drafts`` twins that already did. The ``log-present`` twin
(task 2.3.4) likewise reads disk on both sides — it compares ``log.md``'s
presence rather than the manuscript — and the ``word-counts-cover-drafts`` twin
(task 2.3.6) reads the manifest-keyed recount, so the cross-check is genuinely
disk-vs-disk on every invariant.

The detector is **total**: every predicate returns a ``Violation | None`` for
every constructible ``State`` over any ``working_dir``. The word-count predicate
reuses the shared :func:`~novel_ralph_skill.state.wordcount.recount_words`, the
one counting rule (``len(text.split())``), so no second counter exists.

:func:`check_disk_evidence` is **strict by default**. The keyword-only
``relax_drafting_bijection`` flag (ADR 009; roadmap task 2.1.7) relaxes the
``manifest-disk-bijection`` invariant to disk-subset-of-manifest while
``state.phase.current == Phase.DRAFTING`` — a manifest entry without a directory
stops firing, though an orphan directory and a manifest gap still fire in every
phase. Only the user-facing ``check`` passes ``True``;
``derive_reconciliation`` and the corpus agreement suite keep the strict default,
so the torn ``set-chapters`` COMPLETE precedence (ADR 008) and the oracle twin are
unaffected.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state._disk_paths import (
    _chapter_dir_name,
    _on_disk_chapter_numbers,
)
from novel_ralph_skill.state._disk_word_counts import (
    WORD_COUNTS_COVER_DRAFTS,
    WORD_COUNTS_MATCH_DRAFTS,
    _check_word_counts_cover_drafts,
    _check_word_counts_match_drafts,
)
from novel_ralph_skill.state.compile_model import (
    CompiledComparison,
    compiled_matches_drafts,
)
from novel_ralph_skill.state.phase import Phase
from novel_ralph_skill.state.validate import Violation

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# The §5.4 disk-evidence invariant names this module owns. The first five are
# the names the corpus oracle already reserved (``CORPUS_INVARIANT_NAMES``);
# ``word-counts-match-drafts`` was added by task 2.3.2 (D-WORDCOUNT);
# ``log-present`` was added by task 2.3.4; and ``word-counts-cover-drafts`` is
# new this task (2.3.6). The two ``word-counts-*`` names are defined beside their
# predicates in ``_disk_word_counts`` and re-exported here so this module's
# vocabulary stays single-homed. Each string equals the oracle's matching entry
# (the equality is pinned by a test).
MANIFEST_DISK_BIJECTION: typ.Final = "manifest-disk-bijection"
DONE_FLAG_WITHOUT_DRAFT: typ.Final = "done-flag-without-draft"
COMPILED_MATCHES_DRAFTS: typ.Final = "compiled-matches-drafts"
PENDING_TURN_CLEARED: typ.Final = "pending-turn-cleared"
CURSOR_PLAN_PRESENT: typ.Final = "cursor-plan-present"
LOG_PRESENT: typ.Final = "log-present"

# The owned set, in design §5.2/§5.4 order, for callers that need to distinguish
# the disk-evidence verdict from the pure-state verdict. The order is the corpus
# oracle's disk-evidence subset order, with the word-count value name (task
# 2.3.2), the partial-``init`` ``log-present`` name (task 2.3.4), and the
# key-set ``word-counts-cover-drafts`` name (task 2.3.6) appended last, lowest
# precedence.
DISK_EVIDENCE_INVARIANT_NAMES: tuple[str, ...] = (
    MANIFEST_DISK_BIJECTION,
    CURSOR_PLAN_PRESENT,
    DONE_FLAG_WITHOUT_DRAFT,
    COMPILED_MATCHES_DRAFTS,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_MATCH_DRAFTS,
    LOG_PRESENT,
    WORD_COUNTS_COVER_DRAFTS,
)


def _check_manifest_disk_bijection(
    state: State, working_dir: Path, *, relax_drafting: bool = False
) -> Violation | None:
    """Return a violation when manifest and chapter dirs are not in bijection.

    Every ``state.chapters`` entry must have its on-disk ``chapter-NN/`` directory
    and vice versa, and the manifest must be contiguous from 1 with no gaps. The
    break is classified into its two directions: ``orphans = on_disk - manifest``
    (a directory with no manifest entry, the ``draft-without-manifest-entry``
    variant) and ``missing = manifest - on_disk`` (a manifest entry with no
    directory, the ``manifest-extra-entry`` variant), plus the manifest-contiguity
    check. The strict verdict fires when any of the three holds — equivalent to the
    historical ``manifest == on_disk and contiguous``.

    When ``relax_drafting`` is set and ``state.phase.current == Phase.DRAFTING``, a
    break whose **only** broken direction is ``missing`` (no orphan, contiguous
    manifest) returns ``None``: during drafting the on-disk chapter set may honestly
    be a subset of the manifest (ADR 009; design §5.2 invariant 5). The orphan
    direction and the contiguity check still fire in every phase, and the exact
    bijection re-tightens at ``final-pass``/``done``. The default
    (``relax_drafting=False``) is strict, so ``derive_reconciliation`` and the
    corpus agreement suite read the unchanged bijection. Disk-reading twin of the
    oracle's ``_check_manifest_disk_bijection`` (both sides read disk; roadmap
    2.3.3, 2.1.7).
    """
    manifest = {chapter.number for chapter in state.chapters}
    on_disk = _on_disk_chapter_numbers(working_dir)
    orphans = on_disk - manifest
    missing = manifest - on_disk
    contiguous = sorted(manifest) == list(range(1, len(manifest) + 1))
    # A subset (no orphan, contiguous manifest) whose only break is the
    # missing-directory direction; the drafting relaxation suppresses exactly this.
    coherent_subset = not orphans and contiguous
    if coherent_subset and not missing:
        return None
    drafting = relax_drafting and state.phase.current == Phase.DRAFTING
    if drafting and coherent_subset:
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


def _check_compiled_matches_drafts(state: State, working_dir: Path) -> Violation | None:
    """Return a violation when ``compiled.md`` is not the concatenated drafts.

    The comparison verdict comes from the shared single production site
    :func:`~novel_ralph_skill.state.compile_model.compiled_matches_drafts`, which
    recomputes the ordered concatenation through the one
    :func:`~novel_ralph_skill.state.compile_model.present_draft_bodies` /
    :func:`~novel_ralph_skill.state.compile_model.concatenate_drafts` read-and-join
    rule the ``novel-compile`` write path also uses, so a freshly compiled tree is
    coherent here by construction (ExecPlan D-READ; design §4.3/§9). This detector
    projects the three-valued verdict to its absent-file polarity: only a
    *present-and-diverging* ``compiled.md`` (:attr:`CompiledComparison.DIVERGES`)
    is a violation; an *absent* one (:attr:`CompiledComparison.ABSENT`) trivially
    satisfies the check (nothing to diverge from), exactly as the oracle's
    ``_check_compiled_matches_drafts`` treats it (D-COMPILE; audit-3.1.1 Finding 2).
    """
    if compiled_matches_drafts(state, working_dir) is not CompiledComparison.DIVERGES:
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


def _check_log_present(_state: State, working_dir: Path) -> Violation | None:
    """Return a violation when ``state.toml`` is present but ``log.md`` is absent.

    The partial-``init`` bootstrap (roadmap task 2.3.4): ``init`` writes
    ``state.toml`` first and ``log.md`` second and refuses any re-run while
    ``state.toml`` exists, so a crash between the two writes leaves ``log.md``
    absent beside a present ``state.toml`` — a tree nothing else detects. The
    ``state`` parameter is unused (the caller already loaded ``state``, proving
    ``state.toml`` is present), so it is named ``_state`` to satisfy Ruff ARG001,
    matching ``_check_pending_turn_cleared(state, _working_dir)``.
    """
    if (working_dir / "log.md").exists():
        return None
    return Violation(
        invariant=LOG_PRESENT,
        detail="log.md is absent beside a present state.toml (partial init)",
    )


# The seven non-bijection predicates, assembled in
# :data:`DISK_EVIDENCE_INVARIANT_NAMES` order (minus the bijection, element 0). The
# bijection predicate is lifted out of this loop because it alone takes the
# keyword-only ``relax_drafting`` flag (ADR 009): a per-predicate kwarg cannot be
# threaded through this uniform-signature tuple without widening every predicate.
# ``check_disk_evidence`` calls the bijection first with the flag, then runs this
# tail, so the union order stays byte-for-byte the historical single-loop order.
_TAIL_PREDICATES: tuple[cabc.Callable[[State, Path], Violation | None], ...] = (
    _check_cursor_plan_present,
    _check_done_flag_without_draft,
    _check_compiled_matches_drafts,
    _check_pending_turn_cleared,
    _check_word_counts_match_drafts,
    _check_log_present,
    _check_word_counts_cover_drafts,
)

# The full predicate sequence, bijection first, for any reference that needs the
# whole detector in :data:`DISK_EVIDENCE_INVARIANT_NAMES` order. The bijection is
# stored with its default (strict) flag here; ``check_disk_evidence`` calls it
# directly so it can thread the relaxation flag.
_PREDICATES: tuple[cabc.Callable[[State, Path], Violation | None], ...] = (
    _check_manifest_disk_bijection,
    *_TAIL_PREDICATES,
)


def check_disk_evidence(
    state: State,
    working_dir: Path,
    *,
    relax_drafting_bijection: bool = False,
) -> tuple[Violation, ...]:
    """Return the §5.4 disk-evidence invariants ``state`` violates against disk.

    An empty tuple means the state is coherent against the on-disk ``working/``
    tree under the disk-evidence invariants this detector owns. Pure-state
    invariants (§5.2) are not checked here; ``check`` unions the two verdicts. The
    verdict is ordered by :data:`DISK_EVIDENCE_INVARIANT_NAMES`.

    The bijection predicate is evaluated first and out of the
    :data:`_TAIL_PREDICATES` loop so it can receive ``relax_drafting_bijection``;
    because the bijection is element 0 of
    :data:`DISK_EVIDENCE_INVARIANT_NAMES` and the tail keeps the remaining names in
    order, the head-then-tail assembly reproduces the historical single-loop order
    byte-for-byte.

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` to check against disk.
    working_dir : pathlib.Path
        The materialised ``working/`` directory holding ``manuscript/``.
    relax_drafting_bijection : bool, optional
        When ``True`` and ``state.phase.current == Phase.DRAFTING``, the
        ``manifest-disk-bijection`` invariant relaxes to disk-subset-of-manifest:
        a manifest entry without a directory no longer fires, though an orphan
        directory or a manifest gap still do (ADR 009). Defaults to ``False``
        (strict), which ``derive_reconciliation`` and the corpus agreement suite
        rely on; only the user-facing ``check`` passes ``True``.

    Returns
    -------
    tuple[Violation, ...]
        The ordered disk-evidence violations, or an empty tuple when coherent.
    """
    head = _check_manifest_disk_bijection(
        state, working_dir, relax_drafting=relax_drafting_bijection
    )
    tail = (predicate(state, working_dir) for predicate in _TAIL_PREDICATES)
    return tuple(violation for violation in (head, *tail) if violation is not None)
