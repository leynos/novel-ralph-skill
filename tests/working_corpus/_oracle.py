"""The corpus-local structural oracle for the §5.2 / §5.4 invariants.

:func:`corpus_check` re-implements only the *structural* §5.2 invariants
(design §5.2 lines 436-456) plus the §5.4 contradictory-disk checks, returning
the tuple of invariant **names** a tree violates (an empty tuple means coherent).
It is a corpus-internal cross-check used to prove this task's coherent/incoherent
split, NOT the canonical validator: task 2.1.2 implements the real §5.2 validator
and asserts it agrees with these corpus labels by keying on the same
:data:`CORPUS_INVARIANT_NAMES` strings (advisory A5).

The compile check uses the design's §4.3/§9 content-hash model — it recomputes
the ordered ``concatenate_drafts`` of the present drafts and compares bytes —
never a separator/heading grammar the design does not define (design-review B1).

The physically-disk-reading predicates — the ones that take a ``working_dir`` and
read the materialised ``working/`` tree — live in the :mod:`._oracle_disk` sibling
(split out for file size; AGENTS.md 400-line cap) and are imported here so
:func:`corpus_check` keeps assembling them. Each is the disk-reading twin of the
same-named predicate in ``novel_ralph_skill/state/disk_evidence.py`` (roadmap task
2.3.3), except ``_check_by_chapter_sum``, which reads disk for the *pure-state*
``by-chapter-sum`` name (owned by ``validate_state``). The pure-spec
``_check_pending_turn_cleared`` stays here in ``_SPEC_CHECKS``.
"""

from __future__ import annotations

import typing as typ

from ._library import PHASE_ORDER
from ._oracle_disk import (
    WORD_COUNTS_COVER_DRAFTS,
    _check_by_chapter_sum,
    _check_compiled_matches_drafts,
    _check_cursor_plan_present,
    _check_done_flag_without_draft,
    _check_log_present,
    _check_manifest_disk_bijection,
    _check_word_counts_cover_drafts,
    _check_word_counts_match_drafts,
)
from ._specs import (
    GATE_THRESHOLDS,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from ._specs import WorkingTreeSpec

# The oracle's stable invariant-name vocabulary. Each string is the label
# :func:`corpus_check` returns for the matching §5.2 / §5.4 violation; task
# 2.1.2's validator keys its cross-check on these same strings.
PHASE_IN_ENUM = "phase-in-enum"
COMPLETED_PREFIX = "completed-prefix"
BY_CHAPTER_SUM = "by-chapter-sum"
# Design §5.2 invariant 4 bundles three distinct sub-rules; the oracle names
# each one separately so a variant pins exactly the sub-rule it breaks and no
# sub-rule can silently stop being exercised (task 2.1.2's cross-check keys on
# these same strings).
CONSECUTIVE_CLEAN_WITHIN_TARGET = "consecutive-clean-within-target"
CONVERGENCE_TARGET_AT_LEAST_ONE = "convergence-target-at-least-one"
CONSECUTIVE_CLEAN_WITHIN_DRAFTED = "consecutive-clean-within-drafted"
MANIFEST_DISK_BIJECTION = "manifest-disk-bijection"
CURSOR_COHERENT = "cursor-coherent"
# Disk-evidence: the scene/beat-plan-presence sub-clause of design §5.2
# invariant 6 ("zero until their plans exist"). It reads the built tree for the
# current chapter's ``scenes.md`` / ``beats.md`` (deferred to task 2.3.2).
CURSOR_PLAN_PRESENT = "cursor-plan-present"
GATE_RATIO_CONSISTENT = "gate-ratio-consistent"
DONE_FLAG_WITHOUT_DRAFT = "done-flag-without-draft"
COMPILED_MATCHES_DRAFTS = "compiled-matches-drafts"
PENDING_TURN_CLEARED = "pending-turn-cleared"
# Disk-evidence (roadmap task 2.3.2; ExecPlan D-WORDCOUNT): the disk-vs-table
# per-chapter word-count divergence. It reads the materialised ``draft.md``
# bodies from disk and compares them against the ``[word_counts]`` table.
WORD_COUNTS_MATCH_DRAFTS = "word-counts-match-drafts"
# Disk-evidence (roadmap task 2.3.4): the partial-``init`` bootstrap — ``log.md``
# absent beside a present ``state.toml``. It reads the built tree for ``log.md``.
LOG_PRESENT = "log-present"
# ``WORD_COUNTS_COVER_DRAFTS`` (roadmap task 2.3.6) is defined in ``_oracle_disk``
# beside the predicate that owns it and re-exported above so this module's
# vocabulary and ``corpus_check`` keep referencing it. It is the ``by_chapter``
# key-set coverage divergence — orthogonal to the shared-key value match
# :data:`WORD_COUNTS_MATCH_DRAFTS` owns.

CORPUS_INVARIANT_NAMES: tuple[str, ...] = (
    PHASE_IN_ENUM,
    COMPLETED_PREFIX,
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    MANIFEST_DISK_BIJECTION,
    CURSOR_COHERENT,
    CURSOR_PLAN_PRESENT,
    GATE_RATIO_CONSISTENT,
    DONE_FLAG_WITHOUT_DRAFT,
    COMPILED_MATCHES_DRAFTS,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_MATCH_DRAFTS,
    LOG_PRESENT,
    WORD_COUNTS_COVER_DRAFTS,
)


# The six structural §5.2 predicates below are deliberate twins of the
# production validator's same-named predicates in
# ``novel_ralph_skill/state/validate.py``. The duplication is intentional: the
# oracle is an independent cross-check and must NOT import the thing it checks.
# The two sides are pinned to agree on every corpus tree by the contract test
# ``test_incoherent_agreement_restricted_to_owned`` in
# ``tests/test_validate_state_corpus.py``; edit either predicate and that test
# must still hold (the deliberate-twin policy is recorded in the developers'
# guide §"Invariant validation").
def _check_phase_in_enum(spec: WorkingTreeSpec) -> bool:
    """Return True when ``phase.current`` is a member of the phase enum (inv 1)."""
    return spec.phase_current in PHASE_ORDER


def _check_completed_prefix(spec: WorkingTreeSpec) -> bool:
    """Return True when ``completed`` is the in-order enum prefix (invariant 2).

    A ``phase.current`` outside the enum is invariant 1's concern, not this
    one, so an out-of-enum phase passes here (it has no defined prefix); the
    check isolates a genuine prefix gap from a bad current phase.
    """
    if spec.phase_current not in PHASE_ORDER:
        return True
    expected = PHASE_ORDER[: PHASE_ORDER.index(spec.phase_current)]
    return spec.phase_completed == expected


def _check_consecutive_clean_within_target(spec: WorkingTreeSpec) -> bool:
    """Return True when ``consecutive_clean`` is within its ceiling (inv 4a).

    ``0 <= consecutive_clean <= convergence_target``: the counter is
    non-negative and never exceeds the configured ``convergence_target`` ceiling.
    A ``convergence_target`` below 1 is :func:`_check_convergence_target_at_least_one`'s
    concern, not this one.
    """
    return 0 <= spec.consecutive_clean <= spec.convergence_target


def _check_convergence_target_at_least_one(spec: WorkingTreeSpec) -> bool:
    """Return True when ``convergence_target`` is at least 1 (invariant 4b).

    Design §5.2 invariant 4 rejects a ``convergence_target`` below 1 outright,
    independently of the ``consecutive_clean`` value it bounds.
    """
    return spec.convergence_target >= 1


def _check_consecutive_clean_within_drafted(spec: WorkingTreeSpec) -> bool:
    """Return True when ``consecutive_clean`` is within drafted chapters (inv 4c).

    ``consecutive_clean`` never exceeds the number of chapters drafted; a
    clean-pass count larger than the drafted set cannot have been earned.
    """
    drafted = sum(1 for chapter in spec.chapters if chapter.draft_words > 0)
    return spec.consecutive_clean <= drafted


def _check_cursor_coherent(spec: WorkingTreeSpec) -> bool:
    """Return True when the drafting cursor is coherent (invariant 6).

    ``current_chapter`` never references a chapter past the drafted set; the
    scene and beat sub-cursors are non-negative; and a scene or beat cursor
    never references a chapter past ``current_chapter`` — read in its only
    pure-state form as: when ``current_chapter == 0`` there is no current
    chapter for a scene or beat to belong to, so both must be ``0`` (Decision
    Log D2). The disk-evidence "zero until plans exist" sub-clause is
    :func:`_check_cursor_plan_present`'s, not this one's.
    """
    if not (
        0 <= spec.current_chapter <= len(spec.chapters)
        and spec.current_scene >= 0
        and spec.current_beat >= 0
    ):
        return False
    if spec.current_chapter == 0:
        return spec.current_scene == 0 and spec.current_beat == 0
    return True


def _check_gate_ratio_consistent(spec: WorkingTreeSpec) -> bool:
    """Return True when each knitting gate matches its threshold (invariant 7).

    The ratio is computed from the honest on-disk draft total (the sum of the
    chapters' ``draft_words``), not from a ``by_chapter_override``, so the
    invariant-3 mismatch variant does not also perturb invariant 7.
    """
    if spec.target_words <= 0:
        return True
    drafted = sum(chapter.draft_words for chapter in spec.chapters)
    ratio = drafted / spec.target_words
    low, mid, high = GATE_THRESHOLDS
    gates = ((spec.done_30, low), (spec.done_50, mid), (spec.done_80, high))
    return all(flag == (ratio >= threshold) for flag, threshold in gates)


def _check_pending_turn_cleared(spec: WorkingTreeSpec) -> bool:
    """Return True when no uncleared ``[pending_turn]`` record is present (§3.4).

    A populated ``[pending_turn]`` is a torn turn: a coherent-looking tree whose
    state file still records an operation in flight, which reconciliation (task
    2.3.2) must clear.
    """
    return spec.pending_turn is None


# The structural checks that depend on the spec alone, keyed by invariant name.
# ``BY_CHAPTER_SUM``, ``MANIFEST_DISK_BIJECTION``, ``CURSOR_PLAN_PRESENT``,
# ``DONE_FLAG_WITHOUT_DRAFT``, ``COMPILED_MATCHES_DRAFTS``,
# ``WORD_COUNTS_MATCH_DRAFTS``, ``LOG_PRESENT`` and ``WORD_COUNTS_COVER_DRAFTS``
# are disk-evidence checks (they read the materialised ``working/`` tree), so they
# are applied separately in :func:`corpus_check` rather than listed here.
_SPEC_CHECKS: tuple[tuple[str, cabc.Callable[[WorkingTreeSpec], bool]], ...] = (
    (PHASE_IN_ENUM, _check_phase_in_enum),
    (COMPLETED_PREFIX, _check_completed_prefix),
    (CONSECUTIVE_CLEAN_WITHIN_TARGET, _check_consecutive_clean_within_target),
    (CONVERGENCE_TARGET_AT_LEAST_ONE, _check_convergence_target_at_least_one),
    (CONSECUTIVE_CLEAN_WITHIN_DRAFTED, _check_consecutive_clean_within_drafted),
    (CURSOR_COHERENT, _check_cursor_coherent),
    (GATE_RATIO_CONSISTENT, _check_gate_ratio_consistent),
    (PENDING_TURN_CLEARED, _check_pending_turn_cleared),
)


def corpus_check(spec: WorkingTreeSpec, working_dir: Path) -> tuple[str, ...]:
    """Return the invariant names ``spec`` / ``working_dir`` violate.

    An empty tuple means the tree is coherent under the corpus-local structural
    oracle. This is a corpus-internal cross-check, not the canonical §5.2
    validator (task 2.1.2).

    Parameters
    ----------
    spec : WorkingTreeSpec
        The specification the tree was built from.
    working_dir : Path
        The materialised ``working/`` directory (for the disk-evidence checks).

    Returns
    -------
    tuple[str, ...]
        The :data:`CORPUS_INVARIANT_NAMES` the tree violates, in vocabulary
        order.
    """
    passed = {name: check(spec) for name, check in _SPEC_CHECKS}
    passed[BY_CHAPTER_SUM] = _check_by_chapter_sum(working_dir)
    passed[MANIFEST_DISK_BIJECTION] = _check_manifest_disk_bijection(working_dir)
    passed[DONE_FLAG_WITHOUT_DRAFT] = _check_done_flag_without_draft(working_dir)
    passed[COMPILED_MATCHES_DRAFTS] = _check_compiled_matches_drafts(working_dir)
    passed[CURSOR_PLAN_PRESENT] = _check_cursor_plan_present(spec, working_dir)
    passed[WORD_COUNTS_MATCH_DRAFTS] = _check_word_counts_match_drafts(working_dir)
    passed[LOG_PRESENT] = _check_log_present(working_dir)
    passed[WORD_COUNTS_COVER_DRAFTS] = _check_word_counts_cover_drafts(working_dir)
    return tuple(name for name in CORPUS_INVARIANT_NAMES if not passed[name])
