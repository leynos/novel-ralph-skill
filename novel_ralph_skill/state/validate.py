"""The §5.2 pure-state invariant validator behind ``novel-state check``.

:func:`validate_state` is the pure function that decides whether a parsed
:class:`~novel_ralph_skill.state.schema.State` contradicts *itself* under the
design §5.2 invariants — the checker half of the §5.4 checker/mutator split. It
reads nothing from disk beyond the ``state.toml`` that produced the ``State``;
the §5.4 disk-evidence invariants (``manifest-disk-bijection``,
``done-flag-without-draft``, ``compiled-matches-drafts``,
``pending-turn-cleared``) are roadmap task 2.3.2's and are **not** checked here.

The validator owns eight invariant names, each spelled exactly as the design
§5.2 wording and the corpus oracle's ``CORPUS_INVARIANT_NAMES`` entry so task
2.1.3's cross-check keys on one vocabulary (the equality is pinned by a test,
and the constants are defined here rather than imported from ``tests/``). Design
§5.2 invariant 4 is split into three named sub-rules
(``consecutive-clean-within-target``, ``convergence-target-at-least-one``, and
``consecutive-clean-within-drafted``) so a verdict pins exactly the sub-rule it
breaks. It is a pure ``State -> tuple[Violation, ...]`` composed of one small
predicate per invariant, assembled in design §5.2 order so the verdict order is
deterministic.

The validator is **total**: every predicate returns a ``Violation | None`` for
every constructible ``State`` with no unguarded arithmetic. The gate-ratio
predicate in particular short-circuits when ``word_counts.target <= 0`` rather
than dividing by it, exactly mirroring the oracle's
``_check_gate_ratio_consistent`` guard, so an arbitrary ``target == 0`` state
yields a verdict rather than a ``ZeroDivisionError`` (Decision Log B7).
"""

from __future__ import annotations

import dataclasses
import typing as typ

from novel_ralph_skill.state.phase import PHASE_ORDER

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state.schema import State

# The pure-state §5.2 invariant names this task owns. Each string equals the
# corresponding design §5.2 wording and the corpus oracle's
# CORPUS_INVARIANT_NAMES entry (the equality is pinned by a test).
PHASE_IN_ENUM: typ.Final = "phase-in-enum"
COMPLETED_PREFIX: typ.Final = "completed-prefix"
BY_CHAPTER_SUM: typ.Final = "by-chapter-sum"
# Design §5.2 invariant 4 bundles three distinct sub-rules; each is named
# separately so a verdict pins exactly the sub-rule it breaks, matching the
# corpus oracle's CORPUS_INVARIANT_NAMES split (task 2.1.3's cross-check keys on
# these same strings).
CONSECUTIVE_CLEAN_WITHIN_TARGET: typ.Final = "consecutive-clean-within-target"
CONVERGENCE_TARGET_AT_LEAST_ONE: typ.Final = "convergence-target-at-least-one"
CONSECUTIVE_CLEAN_WITHIN_DRAFTED: typ.Final = "consecutive-clean-within-drafted"
CURSOR_COHERENT: typ.Final = "cursor-coherent"
GATE_RATIO_CONSISTENT: typ.Final = "gate-ratio-consistent"

# The owned set, in design §5.2 order, for callers (and task 2.3.2) that need to
# distinguish a pure-state verdict from the disk-evidence verdict.
PURE_STATE_INVARIANT_NAMES: tuple[str, ...] = (
    PHASE_IN_ENUM,
    COMPLETED_PREFIX,
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
)

# The §5.2 knitting-gate thresholds (design §5.2 bullet 7): the 30%, 50%, and
# 80% drafted-total ratios the three knitting-gate booleans must each match.
# Public so cross-module callers (the corpus and property suites) and the corpus
# oracle's independent copy can pin against one source of truth rather than
# reaching across the package boundary for a module-private name.
GATE_THRESHOLDS: tuple[float, float, float] = (0.30, 0.50, 0.80)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Violation:
    """One named §5.2 invariant breach with a human-readable detail.

    Attributes
    ----------
    invariant : str
        The breached invariant name, drawn from :data:`PURE_STATE_INVARIANT_NAMES`.
    detail : str
        Human-readable prose describing the breach for the envelope's
        ``messages``.
    """

    invariant: str
    detail: str


def _kebab(member: object) -> str:
    """Render a phase as the kebab string an operator reads in ``state.toml``.

    A :class:`~novel_ralph_skill.state.phase.Phase` is a :class:`enum.StrEnum`,
    so ``str(member)`` is its kebab-case value (``Phase.PREMISE`` →
    ``"premise"``) rather than the ``<Phase.PREMISE: 'premise'>`` repr. An
    out-of-enum ``current`` (the ``phase-in-enum`` breach) is already a plain
    string, so ``str`` renders it verbatim — keeping the detail prose in the
    on-disk vocabulary either way.
    """
    return str(member)


def _kebab_tuple(members: cabc.Iterable[object]) -> str:
    """Render a tuple of phases as kebab strings (e.g. ``(premise, treatment)``)."""
    return f"({', '.join(_kebab(member) for member in members)})"


def _check_phase_in_enum(state: State) -> Violation | None:
    """Return a violation when ``phase.current`` is outside the enum (inv 1)."""
    if state.phase.current in PHASE_ORDER:
        return None
    return Violation(
        invariant=PHASE_IN_ENUM,
        detail=f"phase.current {_kebab(state.phase.current)} is not a Phase member",
    )


def _check_completed_prefix(state: State) -> Violation | None:
    """Return a violation when ``completed`` is not the enum prefix (inv 2).

    A ``phase.current`` outside the enum is invariant 1's concern, so an
    out-of-enum current phase passes here (it has no defined prefix), mirroring
    the oracle's ``_check_completed_prefix`` so a bad phase reports exactly
    ``phase-in-enum`` and not two violations.
    """
    if state.phase.current not in PHASE_ORDER:
        return None
    expected = PHASE_ORDER[: PHASE_ORDER.index(state.phase.current)]
    if tuple(state.phase.completed) == expected:
        return None
    return Violation(
        invariant=COMPLETED_PREFIX,
        detail=(
            f"phase.completed {_kebab_tuple(state.phase.completed)} is not the "
            f"in-order prefix {_kebab_tuple(expected)} for current "
            f"{_kebab(state.phase.current)}"
        ),
    )


def _check_by_chapter_sum(state: State) -> Violation | None:
    """Return a violation when ``by_chapter`` does not sum to ``current`` (inv 3)."""
    drafted_total = sum(state.word_counts.by_chapter.values())
    if drafted_total == state.word_counts.current:
        return None
    return Violation(
        invariant=BY_CHAPTER_SUM,
        detail=(
            f"sum(by_chapter) {drafted_total} != current {state.word_counts.current}"
        ),
    )


def _check_consecutive_clean_within_target(state: State) -> Violation | None:
    """Return a violation when ``consecutive_clean`` exceeds its ceiling (inv 4a).

    Requires ``0 <= consecutive_clean <= convergence_target``: the counter is
    non-negative and never exceeds the configured ``convergence_target`` ceiling.
    A ``convergence_target`` below 1 is
    :func:`_check_convergence_target_at_least_one`'s concern, mirroring the
    corpus oracle's ``_check_consecutive_clean_within_target`` split.
    """
    critic = state.drafting.critic
    clean = critic.consecutive_clean
    target = critic.convergence_target
    if 0 <= clean <= target:
        return None
    return Violation(
        invariant=CONSECUTIVE_CLEAN_WITHIN_TARGET,
        detail=(
            f"consecutive_clean {clean} is outside [0, convergence_target {target}]"
        ),
    )


def _check_convergence_target_at_least_one(state: State) -> Violation | None:
    """Return a violation when ``convergence_target`` is below one (inv 4b).

    Design §5.2 invariant 4 rejects a ``convergence_target`` below 1 outright,
    independently of the ``consecutive_clean`` value it bounds, mirroring the
    corpus oracle's ``_check_convergence_target_at_least_one`` split.
    """
    target = state.drafting.critic.convergence_target
    if target >= 1:
        return None
    return Violation(
        invariant=CONVERGENCE_TARGET_AT_LEAST_ONE,
        detail=f"convergence_target {target} is below 1",
    )


def _check_consecutive_clean_within_drafted(state: State) -> Violation | None:
    """Return a violation when ``consecutive_clean`` exceeds drafted chapters (inv 4c).

    ``consecutive_clean`` never exceeds the number of chapters drafted; a
    clean-pass count larger than the drafted set cannot have been earned. The
    pure-state proxy for "chapters drafted" is the count of ``word_counts.by_chapter``
    entries with a positive drafted total, mirroring the corpus oracle's
    ``_check_consecutive_clean_within_drafted`` (which counts chapters whose
    ``draft_words > 0``).
    """
    clean = state.drafting.critic.consecutive_clean
    drafted = sum(1 for words in state.word_counts.by_chapter.values() if words > 0)
    if clean <= drafted:
        return None
    return Violation(
        invariant=CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
        detail=(f"consecutive_clean {clean} exceeds the {drafted} drafted chapters"),
    )


def _check_cursor_coherent(state: State) -> Violation | None:
    """Return a violation when the drafting cursor is incoherent (inv 6).

    Bounds ``0 <= current_chapter <= len(state.chapters)`` and requires
    ``current_scene >= 0`` and ``current_beat >= 0``; and enforces the
    scene/beat-past-``current_chapter`` sub-clause in its only pure-state form:
    when ``current_chapter == 0`` there is no current chapter for a scene or
    beat to belong to, so both must be ``0`` (Decision Log D2). The
    disk-evidence "zero until plans exist" sub-clause remains task
    2.1.4-corpus / 2.3.2's and is not checked here.
    """
    drafting = state.drafting
    bounded = (
        0 <= drafting.current_chapter <= len(state.chapters)
        and drafting.current_scene >= 0
        and drafting.current_beat >= 0
    )
    scene_beat_past_chapter = drafting.current_chapter == 0 and (
        drafting.current_scene != 0 or drafting.current_beat != 0
    )
    if bounded and not scene_beat_past_chapter:
        return None
    return Violation(
        invariant=CURSOR_COHERENT,
        detail=(
            f"cursor (chapter={drafting.current_chapter}, "
            f"scene={drafting.current_scene}, beat={drafting.current_beat}) is "
            f"incoherent for {len(state.chapters)} manifest chapters"
        ),
    )


def _check_gate_ratio_consistent(state: State) -> Violation | None:
    """Return a violation when a knitting gate disagrees with the ratio (inv 7).

    The numerator is the **drafted total** ``sum(by_chapter.values())`` (not
    ``current``), matching the oracle and decoupling this invariant from
    invariant 3 (Decision Log B1). When ``target <= 0`` the predicate
    short-circuits with no violation rather than dividing, mirroring the oracle's
    ``if spec.target_words <= 0: return True`` guard (B7), so the validator is
    total over every constructible ``State``.
    """
    target = state.word_counts.target
    if target <= 0:
        return None
    drafted_total = sum(state.word_counts.by_chapter.values())
    ratio = drafted_total / target
    knitting = state.gates.knitting
    flags = (knitting.done_30, knitting.done_50, knitting.done_80)
    if all(
        flag == (ratio >= threshold)
        for flag, threshold in zip(flags, GATE_THRESHOLDS, strict=True)
    ):
        return None
    return Violation(
        invariant=GATE_RATIO_CONSISTENT,
        detail=(
            f"knitting gates {flags} disagree with drafted ratio {ratio:.4f} "
            f"against thresholds {GATE_THRESHOLDS}"
        ),
    )


# The per-invariant predicates, assembled in design §5.2 order so the verdict
# order is deterministic (stable for the agreement suite and any snapshot).
_PREDICATES: tuple[cabc.Callable[[State], Violation | None], ...] = (
    _check_phase_in_enum,
    _check_completed_prefix,
    _check_by_chapter_sum,
    _check_consecutive_clean_within_target,
    _check_convergence_target_at_least_one,
    _check_consecutive_clean_within_drafted,
    _check_cursor_coherent,
    _check_gate_ratio_consistent,
)


def validate_state(state: State) -> tuple[Violation, ...]:
    """Return the pure-state §5.2 invariants ``state`` violates (design §5.2).

    An empty tuple means the state is coherent under the pure-state invariants
    this validator owns. Disk-evidence invariants (§5.4) are not checked here.
    The verdict is ordered by :data:`PURE_STATE_INVARIANT_NAMES`.

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` to validate.

    Returns
    -------
    tuple[Violation, ...]
        The ordered violations, or an empty tuple when ``state`` is coherent.
    """
    return tuple(
        violation
        for violation in (predicate(state) for predicate in _PREDICATES)
        if violation is not None
    )
