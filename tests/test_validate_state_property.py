"""Hypothesis property suite for the §5.2 pure-state validator (roadmap 2.1.2).

This is the §2.3 "state coherence … demonstrated by property-based tests over
generated states" verification made executable. The ``coherent_states`` strategy
constructs a :class:`~novel_ralph_skill.state.State` satisfying every pure-state
invariant *by construction* (avoiding the filtering trap), and the property
asserts :func:`~novel_ralph_skill.state.validate_state` returns the empty verdict
for it. The ``one_perturbation`` strategy breaks exactly one named invariant and
the property asserts the verdict is exactly that invariant's singleton — the
"rejects invalid" half, with the name correct.

Targeted example-based tests pin the boundary cases the roadmap names
(``consecutive_clean`` on and over the ``convergence_target`` ceiling; a raised
target accepting a higher ``consecutive_clean``), the B1 decoupling (a gate-only
break names only ``gate-ratio-consistent``; a ``current``-only break names only
``by-chapter-sum``), and the B7 ``target <= 0`` guard (a ``target == 0`` and a
negative-``target`` state each yield no ``gate-ratio-consistent`` violation
rather than a ``ZeroDivisionError``). These assert the exact verdict directly,
independent of the behavioural suite, so a silent empty-verdict bug fails here.
"""

# This property suite grows one perturbation and one focused case per pure-state
# invariant, so it sits above the default module-line ceiling; the per-invariant
# isolation is clearer kept in one module than split across files.
# pylint: disable=too-many-lines

from __future__ import annotations

import dataclasses as dc

from hypothesis import given
from hypothesis import strategies as st

from novel_ralph_skill.state import (
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
    PHASE_IN_ENUM,
    PHASE_ORDER,
    ChapterEntry,
    CriticState,
    Drafting,
    FangirlState,
    FinalGate,
    FindingCounts,
    Gates,
    KnittingGates,
    NovelMeta,
    PhaseState,
    State,
    WordCounts,
    validate_state,
)

# Read the validator's own gate-threshold triple rather than redeclaring it: the
# production constant is the single §5.2 source of truth, so this suite cannot
# silently agree with a wrong validator by mirroring an independent copy
# (audit:2.1.2 finding 1).
from novel_ralph_skill.state.validate import _GATE_THRESHOLDS


def _by_chapter_key(number: int) -> str:
    """Return the zero-padded two-digit ``by_chapter`` key for ``number``."""
    return f"{number:02d}"


@dc.dataclass(frozen=True, kw_only=True, slots=True)
class _StateParams:
    """The primitive components a strategy or example assembles a ``State`` from."""

    phase_index: int
    chapter_words: tuple[int, ...]
    target: int
    current: int
    gates: tuple[bool, bool, bool]
    consecutive_clean: int
    convergence_target: int
    current_chapter: int
    current_scene: int = 0
    current_beat: int = 0


def _build_state(params: _StateParams) -> State:
    """Assemble a :class:`State` from the primitive ``params``."""
    chapters = tuple(
        ChapterEntry(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=max(words, 1),
        )
        for index, words in enumerate(params.chapter_words)
    )
    by_chapter = {
        _by_chapter_key(index + 1): words
        for index, words in enumerate(params.chapter_words)
    }
    done_30, done_50, done_80 = params.gates
    return State(
        schema_version=1,
        novel=NovelMeta(
            title="Working Title",
            slug="working-title",
            target_word_count=params.target,
            created_at="2026-06-22T00:00:00Z",
        ),
        phase=PhaseState(
            current=PHASE_ORDER[params.phase_index],
            completed=PHASE_ORDER[: params.phase_index],
        ),
        chapters=chapters,
        drafting=Drafting(
            current_chapter=params.current_chapter,
            current_scene=params.current_scene,
            current_beat=params.current_beat,
            critic=CriticState(
                pass_number=1,
                consecutive_clean=params.consecutive_clean,
                convergence_target=params.convergence_target,
                last_finding_counts=FindingCounts(blocker=0, major=0, minor=0, taste=0),
            ),
            fangirl=FangirlState(last_chapter_passed=0),
        ),
        gates=Gates(
            knitting=KnittingGates(done_30=done_30, done_50=done_50, done_80=done_80),
            final=FinalGate(final_pass_complete=False),
        ),
        word_counts=WordCounts(
            target=params.target, current=params.current, by_chapter=by_chapter
        ),
    )


def _gates_for_ratio(ratio: float) -> tuple[bool, bool, bool]:
    """Return the gate booleans the validator expects for ``ratio``.

    Uses the identical ``ratio >= threshold`` comparison the validator uses
    (not ``>``), so a state landing ``ratio`` exactly on a threshold cannot
    self-falsify on a floating-point tie (Decision Log A5).
    """
    low, mid, high = _GATE_THRESHOLDS
    return (ratio >= low, ratio >= mid, ratio >= high)


@st.composite
def coherent_states(draw: st.DrawFn) -> State:
    """Construct a ``State`` satisfying every pure-state §5.2 invariant.

    The phase is drawn from ``PHASE_ORDER`` with its exact prefix as
    ``completed``; ``by_chapter`` sums to ``current``; ``target >= 1`` (so the
    live gate-ratio path is exercised without tripping the ``target <= 0`` guard,
    B7); the gate booleans match the drafted-total ratio; ``convergence_target
    >= 1`` and ``consecutive_clean`` is drawn in ``[0, min(convergence_target,
    drafted_chapters)]`` (where ``drafted_chapters`` counts chapters with a
    positive drafted total, matching the validator's ``within-drafted`` proxy);
    and the cursor is non-negative with ``current_chapter <= len(chapters)``.
    When the drawn ``current_chapter`` is ``0`` the scene and beat sub-cursors
    are forced to ``0`` so the state satisfies the pure-state
    scene/beat-past-``current_chapter`` clause of invariant 6 (Decision Log D2).
    """
    phase_index = draw(st.integers(min_value=0, max_value=len(PHASE_ORDER) - 1))
    chapter_words = tuple(
        draw(
            st.lists(st.integers(min_value=0, max_value=20000), min_size=1, max_size=5)
        )
    )
    target = draw(st.integers(min_value=1, max_value=200000))
    drafted_total = sum(chapter_words)
    convergence_target = draw(st.integers(min_value=1, max_value=4))
    # The pure-state "chapters drafted" ceiling counts chapters with a positive
    # drafted total (mirroring the validator's ``within-drafted`` proxy), not the
    # manifest length: an all-zero chapter is planned but not yet drafted.
    drafted_chapters = sum(1 for words in chapter_words if words > 0)
    clean_ceiling = min(convergence_target, drafted_chapters)
    current_chapter = draw(st.integers(min_value=0, max_value=len(chapter_words)))
    # A zero ``current_chapter`` has no current chapter for a scene or beat to
    # belong to, so the cursor sub-counters must be zero (invariant 6, D2);
    # otherwise draw them in ``[0, 20]`` as before.
    cursor_ceiling = 0 if current_chapter == 0 else 20
    return _build_state(
        _StateParams(
            phase_index=phase_index,
            chapter_words=chapter_words,
            target=target,
            current=drafted_total,
            gates=_gates_for_ratio(drafted_total / target),
            consecutive_clean=draw(st.integers(min_value=0, max_value=clean_ceiling)),
            convergence_target=convergence_target,
            current_chapter=current_chapter,
            current_scene=draw(st.integers(min_value=0, max_value=cursor_ceiling)),
            current_beat=draw(st.integers(min_value=0, max_value=cursor_ceiling)),
        )
    )


@given(state=coherent_states())
def test_coherent_states_accepted(state: State) -> None:
    """Every coherent-by-construction state has an empty verdict (accepts valid)."""
    assert not validate_state(state)


def _perturb_phase(state: State) -> State:
    """Break ``phase-in-enum`` by setting an out-of-enum current phase."""
    return dc.replace(state, phase=dc.replace(state.phase, current="not-a-phase"))


def _perturb_by_chapter_sum(state: State) -> State:
    """Break ``by-chapter-sum`` by setting ``current`` off the by_chapter sum.

    Leaves the gate booleans honest against the drafted total, so on an
    otherwise coherent state the verdict is exactly ``{by-chapter-sum}`` (the B1
    decoupling: corrupting ``current`` does not also trip ``gate-ratio-consistent``).
    """
    drafted_total = sum(state.word_counts.by_chapter.values())
    return dc.replace(
        state,
        word_counts=dc.replace(state.word_counts, current=drafted_total + 1),
    )


def _perturb_gate(state: State) -> State:
    """Break ``gate-ratio-consistent`` by flipping one gate against the ratio.

    Leaves ``by_chapter`` and ``current`` consistent, so the verdict is exactly
    ``{gate-ratio-consistent}`` (the B1 decoupling, the gate-only direction).
    """
    knitting = state.gates.knitting
    flipped = dc.replace(knitting, done_30=not knitting.done_30)
    return dc.replace(state, gates=dc.replace(state.gates, knitting=flipped))


def _perturb_cursor_past_current_chapter(state: State) -> State:
    """Break ``cursor-coherent`` with a scene cursor past ``current_chapter``.

    Forces ``current_chapter == 0`` (no current chapter) while ``current_scene``
    is non-zero, the only pure-state form of the scene/beat-past-``current_chapter``
    sub-clause of invariant 6 (Decision Log D2). The cursor fields appear only in
    ``_check_cursor_coherent``, so from any coherent state this breaks exactly
    ``cursor-coherent``.
    """
    drafting = dc.replace(state.drafting, current_chapter=0, current_scene=1)
    return dc.replace(state, drafting=drafting)


_PERTURBATIONS = {
    PHASE_IN_ENUM: _perturb_phase,
    BY_CHAPTER_SUM: _perturb_by_chapter_sum,
    GATE_RATIO_CONSISTENT: _perturb_gate,
    CURSOR_COHERENT: _perturb_cursor_past_current_chapter,
}
# Invariant 4's three sub-rules (``within-target``, ``at-least-one``,
# ``within-drafted``) are not driven from arbitrary coherent states here: an
# arbitrary state may have zero drafted chapters, so a single perturbation can
# trip two sub-rules at once. They are pinned by the controlled example-based
# tests below, each breaking exactly one sub-rule from a known baseline.


@given(
    state=coherent_states(),
    invariant=st.sampled_from(sorted(_PERTURBATIONS)),
)
def test_single_perturbation_names_exactly_one(
    state: State,
    invariant: str,
) -> None:
    """Breaking one invariant yields exactly that invariant's singleton verdict."""
    perturbed = _PERTURBATIONS[invariant](state)
    verdict = {violation.invariant for violation in validate_state(perturbed)}
    assert verdict == {invariant}


def _baseline_coherent(
    *,
    target: int = 80000,
    chapter_words: tuple[int, ...] = (4000, 4000),
    consecutive_clean: int = 0,
    convergence_target: int = 1,
) -> State:
    """Build a coherent baseline state for the example-based boundary tests."""
    drafted_total = sum(chapter_words)
    gates = (
        _gates_for_ratio(drafted_total / target)
        if target > 0
        else (False, False, False)
    )
    return _build_state(
        _StateParams(
            phase_index=8,  # the drafting phase
            chapter_words=chapter_words,
            target=target,
            current=drafted_total,
            gates=gates,
            consecutive_clean=consecutive_clean,
            convergence_target=convergence_target,
            current_chapter=len(chapter_words),
        )
    )


def test_consecutive_clean_on_ceiling_accepted() -> None:
    """``consecutive_clean == convergence_target`` (and <= chapters) is accepted."""
    state = _baseline_coherent(consecutive_clean=2, convergence_target=2)
    assert not validate_state(state)


def test_consecutive_clean_over_ceiling_rejected() -> None:
    """``consecutive_clean == convergence_target + 1`` names only ``within-target``.

    With two drafted chapters the ``within-drafted`` sub-rule still holds
    (``2 <= 2``), so the verdict isolates ``consecutive-clean-within-target``.
    """
    state = _baseline_coherent(consecutive_clean=2, convergence_target=1)
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {CONSECUTIVE_CLEAN_WITHIN_TARGET}


def test_convergence_target_below_one_rejected() -> None:
    """A ``convergence_target`` of ``0`` names only ``convergence-target-at-least-one``.

    With ``consecutive_clean == 0`` the ``within-target`` sub-rule still holds
    (``0 <= 0 <= 0``), so the verdict isolates the ``at-least-one`` sub-rule.
    """
    state = _baseline_coherent(consecutive_clean=0, convergence_target=0)
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {CONVERGENCE_TARGET_AT_LEAST_ONE}


def test_consecutive_clean_over_chapters_drafted_rejected() -> None:
    """``consecutive_clean`` above the drafted count names only ``within-drafted``.

    One drafted chapter with ``consecutive_clean == 2`` and a raised
    ``convergence_target == 3`` keeps ``within-target`` satisfied (``2 <= 3``)
    while the drafted ceiling (``2 > 1``) breaks, isolating
    ``consecutive-clean-within-drafted``.
    """
    state = _baseline_coherent(
        chapter_words=(4000,),
        consecutive_clean=2,
        convergence_target=3,
    )
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {CONSECUTIVE_CLEAN_WITHIN_DRAFTED}


def test_raised_target_accepts_higher_clean() -> None:
    """A raised ``convergence_target`` accepts a ``consecutive_clean`` of ``2``.

    The roadmap-named success clause: the same ``consecutive_clean == 2`` is
    rejected under the default ``convergence_target == 1`` and accepted once the
    target is lifted to ``2`` (with two manifest chapters to clear the
    chapters-drafted ceiling).
    """
    accepted = _baseline_coherent(consecutive_clean=2, convergence_target=2)
    assert not validate_state(accepted)

    rejected = _baseline_coherent(consecutive_clean=2, convergence_target=1)
    verdict = {violation.invariant for violation in validate_state(rejected)}
    assert verdict == {CONSECUTIVE_CLEAN_WITHIN_TARGET}


def test_gate_only_break_names_only_gate_ratio() -> None:
    """A gate flipped against the ratio names only ``gate-ratio-consistent`` (B1)."""
    state = _perturb_gate(_baseline_coherent())
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {GATE_RATIO_CONSISTENT}


def test_current_only_break_names_only_by_chapter_sum() -> None:
    """A ``current`` off the by_chapter sum names only ``by-chapter-sum`` (B1)."""
    state = _perturb_by_chapter_sum(_baseline_coherent())
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {BY_CHAPTER_SUM}


def test_zero_target_yields_no_gate_violation() -> None:
    """A ``target == 0`` state yields no ``gate-ratio-consistent`` violation (B7).

    The predicate short-circuits instead of dividing, so a future un-guarded
    division surfaces as a failing assertion rather than a ``ZeroDivisionError``.
    """
    state = _baseline_coherent(target=0)
    # current must still equal the by_chapter sum to isolate the gate guard.
    state = dc.replace(state, word_counts=dc.replace(state.word_counts, current=8000))
    verdict = {violation.invariant for violation in validate_state(state)}
    assert GATE_RATIO_CONSISTENT not in verdict


def test_negative_target_yields_no_gate_violation() -> None:
    """A negative ``target`` likewise yields no ``gate-ratio-consistent`` violation."""
    state = _baseline_coherent(target=-1)
    state = dc.replace(state, word_counts=dc.replace(state.word_counts, current=8000))
    verdict = {violation.invariant for violation in validate_state(state)}
    assert GATE_RATIO_CONSISTENT not in verdict


def test_phase_in_enum_fires_for_directly_constructed_state() -> None:
    """A directly-built out-of-enum ``State`` names exactly ``phase-in-enum``.

    This is the in-memory side of the two-layer ``phase-in-enum`` enforcement.
    On the production (disk) path ``parse_state`` raises constructing
    ``Phase(current)``, so the validator's predicate never fires there — pinned
    by ``test_phase_in_enum_is_parser_enforced`` in
    ``tests/test_validate_state_corpus.py``. The validator must nonetheless stay
    total over any constructible ``State``, so a ``State`` built directly with an
    out-of-enum ``phase.current`` must yield exactly the ``phase-in-enum``
    violation (and not, e.g., also ``completed-prefix``). This named test makes
    that in-memory contract self-documenting rather than only exercised
    indirectly by the perturbation suite.
    """
    state = _perturb_phase(_baseline_coherent())
    verdict = {violation.invariant for violation in validate_state(state)}
    assert verdict == {PHASE_IN_ENUM}
