"""``Violation.detail`` prose coverage for the §5.2 pure-state validator.

Every other suite asserts on ``violation.invariant`` (the machine name) but none
on ``violation.detail``, the human-readable prose surfaced in the envelope's
``messages`` and the ``--human`` rendering. A predicate could compute a wrong or
empty ``detail`` — an f-string referencing the wrong attribute, say — and every
existing test would still pass. This module brings the human-facing channel under
the same coverage as the machine-name channel: each case breaks exactly one
invariant from a known coherent baseline and asserts the resulting ``detail`` is
non-empty and surfaces the offending values (audit:2.1.2 finding 8).

The baseline is built directly here rather than imported from the property suite:
importing values or helpers from another test module is forbidden (the
developers-guide "Shared test scaffolding" rule), and a focused self-contained
baseline keeps each detail case readable beside its expected substrings.
"""

from __future__ import annotations

import dataclasses as dc

import pytest

from novel_ralph_skill.state import (
    BY_CHAPTER_SUM,
    COMPLETED_PREFIX,
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
    Violation,
    WordCounts,
    validate_state,
)


def _baseline() -> State:
    """Build a coherent two-chapter drafting state for the detail cases.

    Both chapters carry 4000 drafted words (``current`` 8000), the convergence
    target is 1 with no clean passes yet, the knitting gates match the drafted
    ratio (8000 / 80000 = 0.1, below every threshold, so all gates are false),
    and the cursor sits at the end of the manifest. Perturbing one field breaks
    exactly one invariant.
    """
    chapters = tuple(
        ChapterEntry(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=40000,
        )
        for index in range(2)
    )
    return State(
        schema_version=1,
        novel=NovelMeta(
            title="Working Title",
            slug="working-title",
            target_word_count=80000,
            created_at="2026-06-22T00:00:00Z",
        ),
        phase=PhaseState(
            current=PHASE_ORDER[8],
            completed=PHASE_ORDER[:8],
        ),
        chapters=chapters,
        drafting=Drafting(
            current_chapter=2,
            current_scene=0,
            current_beat=0,
            critic=CriticState(
                pass_number=1,
                consecutive_clean=0,
                convergence_target=1,
                last_finding_counts=FindingCounts(blocker=0, major=0, minor=0, taste=0),
            ),
            fangirl=FangirlState(last_chapter_passed=0),
        ),
        gates=Gates(
            knitting=KnittingGates(done_30=False, done_50=False, done_80=False),
            final=FinalGate(final_pass_complete=False),
        ),
        word_counts=WordCounts(
            target=80000,
            current=8000,
            by_chapter={"01": 4000, "02": 4000},
        ),
    )


def _violation_for(state: State, invariant: str) -> Violation:
    """Return the single ``Violation`` ``state`` raises, asserting it is ``invariant``.

    Asserts the verdict names exactly ``invariant`` so each detail case breaks
    precisely the invariant under test, then returns that violation.
    """
    verdict = validate_state(state)
    actual = [violation.invariant for violation in verdict]
    assert set(actual) == {invariant}, f"expected only {invariant!r}, got {actual!r}"
    return verdict[0]


def _break_phase(state: State) -> State:
    """Break ``phase-in-enum`` by setting an out-of-enum current phase."""
    return dc.replace(state, phase=dc.replace(state.phase, current="not-a-phase"))


def _break_completed_prefix(state: State) -> State:
    """Break ``completed-prefix`` without leaving the enum (clears ``completed``)."""
    return dc.replace(state, phase=dc.replace(state.phase, completed=()))


def _break_by_chapter_sum(state: State) -> State:
    """Break ``by-chapter-sum`` by nudging ``current`` off the drafted total."""
    drafted_total = sum(state.word_counts.by_chapter.values())
    return dc.replace(
        state,
        word_counts=dc.replace(state.word_counts, current=drafted_total + 1),
    )


def _break_within_target(state: State) -> State:
    """Break ``consecutive-clean-within-target`` (clean above the target ceiling)."""
    return dc.replace(
        state,
        drafting=dc.replace(
            state.drafting,
            critic=dc.replace(
                state.drafting.critic, consecutive_clean=2, convergence_target=1
            ),
        ),
    )


def _break_at_least_one(state: State) -> State:
    """Break ``convergence-target-at-least-one`` (target below one)."""
    return dc.replace(
        state,
        drafting=dc.replace(
            state.drafting,
            critic=dc.replace(
                state.drafting.critic, consecutive_clean=0, convergence_target=0
            ),
        ),
    )


def _break_within_drafted(state: State) -> State:
    """Break ``consecutive-clean-within-drafted`` (clean above one drafted chapter).

    Leaves one drafted chapter and raises ``convergence_target`` so the
    ``within-target`` sub-rule still holds, isolating the drafted ceiling.
    """
    with_one_drafted = dc.replace(
        state,
        word_counts=dc.replace(
            state.word_counts, current=4000, by_chapter={"01": 4000, "02": 0}
        ),
    )
    return dc.replace(
        with_one_drafted,
        drafting=dc.replace(
            with_one_drafted.drafting,
            critic=dc.replace(
                with_one_drafted.drafting.critic,
                consecutive_clean=2,
                convergence_target=3,
            ),
        ),
    )


def _break_cursor(state: State) -> State:
    """Break ``cursor-coherent`` by pointing the cursor past the manifest."""
    return dc.replace(state, drafting=dc.replace(state.drafting, current_chapter=5))


def _break_gate_ratio(state: State) -> State:
    """Break ``gate-ratio-consistent`` by flipping one gate against the ratio."""
    knitting = state.gates.knitting
    flipped = dc.replace(knitting, done_30=not knitting.done_30)
    return dc.replace(state, gates=dc.replace(state.gates, knitting=flipped))


# Each case breaks exactly one invariant from the shared baseline and lists the
# offending values its ``detail`` prose must surface, so a predicate computing a
# wrong or empty ``detail`` (e.g. an f-string on the wrong attribute) fails here
# rather than slipping past the machine-name assertions (audit:2.1.2 finding 8).
_DETAIL_CASES: tuple[tuple[str, State, tuple[str, ...]], ...] = (
    (PHASE_IN_ENUM, _break_phase(_baseline()), ("not-a-phase",)),
    (COMPLETED_PREFIX, _break_completed_prefix(_baseline()), ("completed", "prefix")),
    (BY_CHAPTER_SUM, _break_by_chapter_sum(_baseline()), ("8000", "8001")),
    (CONSECUTIVE_CLEAN_WITHIN_TARGET, _break_within_target(_baseline()), ("2", "1")),
    (CONVERGENCE_TARGET_AT_LEAST_ONE, _break_at_least_one(_baseline()), ("0", "1")),
    (CONSECUTIVE_CLEAN_WITHIN_DRAFTED, _break_within_drafted(_baseline()), ("2", "1")),
    (CURSOR_COHERENT, _break_cursor(_baseline()), ("5", "2")),
    (GATE_RATIO_CONSISTENT, _break_gate_ratio(_baseline()), ("0.3", "0.5", "0.8")),
)


@pytest.mark.parametrize(
    ("invariant", "state", "expected_substrings"),
    _DETAIL_CASES,
    ids=[name for name, _state, _subs in _DETAIL_CASES],
)
def test_violation_detail_names_the_offending_values(
    invariant: str,
    state: State,
    expected_substrings: tuple[str, ...],
) -> None:
    """Each predicate's ``detail`` is non-empty and names the offending values.

    Brings the human-facing message channel (the envelope's ``messages`` and the
    ``--human`` rendering) under the same coverage as the machine-name channel:
    a wrong or empty detail string would otherwise pass unnoticed because no
    other suite asserts on ``violation.detail`` (audit:2.1.2 finding 8).
    """
    violation = _violation_for(state, invariant)
    assert violation.detail, f"{invariant} produced an empty detail string"
    for substring in expected_substrings:
        assert substring in violation.detail, (
            f"{invariant} detail {violation.detail!r} is missing {substring!r}"
        )
