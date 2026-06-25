"""Hypothesis property suite for the manifest-coherence validator (roadmap 2.2.3).

The validator :func:`manifest_coherence_violations` is a pure, total
``Sequence[ChapterPlanEntry] -> tuple[str, ...]`` function over an input range, so
Hypothesis is the right adversary (``python-verification``): a plan constructed to
satisfy every rule yields an empty verdict, and a plan with exactly one breach
injected yields a verdict naming the matching rule.

The ``coherent_plans`` strategy builds a valid plan *by construction* (numbers a
permutation of ``1..n``, unique slugs, positive targets) to avoid the filtering
trap; the perturbation strategies derive a single breach from a coherent seed and
assert the named rule appears in the verdict. Mirrors
``tests/test_validate_state_property.py``.
"""

from __future__ import annotations

import dataclasses as dc

from hypothesis import given
from hypothesis import strategies as st

from novel_ralph_skill.commands._set_chapters import (
    CHAPTERS_NON_EMPTY,
    NUMBERS_CONTIGUOUS_FROM_1,
    NUMBERS_UNIQUE,
    SLUGS_UNIQUE,
    TARGET_WORDS_POSITIVE,
    ChapterPlanEntry,
    manifest_coherence_violations,
)


@st.composite
def coherent_plans(draw: st.DrawFn) -> list[ChapterPlanEntry]:
    """Build a coherent chapter plan: numbers ``1..n``, unique slugs, positive targets.

    Constructed valid (no rejection sampling): the numbers are a shuffled
    ``range(1, n+1)``, the slugs are distinct ``chapter-NN`` strings, and every
    ``target_words`` is at least 1.
    """
    size = draw(st.integers(min_value=1, max_value=8))
    numbers = draw(st.permutations(list(range(1, size + 1))))
    targets = draw(
        st.lists(
            st.integers(min_value=1, max_value=100_000),
            min_size=size,
            max_size=size,
        )
    )
    return [
        ChapterPlanEntry(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=target,
        )
        for number, target in zip(numbers, targets, strict=True)
    ]


@given(plan=coherent_plans())
def test_coherent_plan_has_empty_verdict(plan: list[ChapterPlanEntry]) -> None:
    """A plan satisfying every rule yields the empty verdict (accept)."""
    verdict = manifest_coherence_violations(plan)
    assert not verdict, f"a coherent plan must yield no violations, got {verdict}"


def test_empty_plan_is_refused() -> None:
    """The empty plan yields exactly ``chapters-non-empty`` (the boundary case)."""
    assert manifest_coherence_violations([]) == (CHAPTERS_NON_EMPTY,)


@given(plan=coherent_plans())
def test_duplicate_number_is_named(plan: list[ChapterPlanEntry]) -> None:
    """Appending a chapter that repeats a number names ``numbers-unique``."""
    duplicate = dc.replace(plan[0], slug="chapter-dup")
    verdict = manifest_coherence_violations([*plan, duplicate])
    assert NUMBERS_UNIQUE in verdict, f"a repeated number must name it, got {verdict}"


@given(plan=coherent_plans())
def test_duplicate_slug_is_named(plan: list[ChapterPlanEntry]) -> None:
    """A plan whose two chapters share a slug names ``slugs-unique``.

    The injected chapter keeps numbering contiguous (``n+1``) and a positive
    target, so the *only* rule it breaks is the shared slug.
    """
    clash = dc.replace(plan[0], number=len(plan) + 1)
    verdict = manifest_coherence_violations([*plan, clash])
    assert verdict == (SLUGS_UNIQUE,), f"a shared slug must name only it, got {verdict}"


@given(plan=coherent_plans())
def test_gap_is_named(plan: list[ChapterPlanEntry]) -> None:
    """Shifting every number up by 1 (so 1 is absent) names the contiguity rule."""
    shifted = [dc.replace(entry, number=entry.number + 1) for entry in plan]
    verdict = manifest_coherence_violations(shifted)
    assert NUMBERS_CONTIGUOUS_FROM_1 in verdict, (
        f"a gap at 1 must name contiguity, got {verdict}"
    )


@given(
    plan=coherent_plans(),
    bad_target=st.integers(min_value=-1000, max_value=0),
)
def test_non_positive_target_is_named(
    plan: list[ChapterPlanEntry], bad_target: int
) -> None:
    """A non-positive ``target_words`` names ``target-words-positive``."""
    plan[0] = dc.replace(plan[0], target_words=bad_target)
    verdict = manifest_coherence_violations(plan)
    assert TARGET_WORDS_POSITIVE in verdict, (
        f"a non-positive target must name it, got {verdict}"
    )
