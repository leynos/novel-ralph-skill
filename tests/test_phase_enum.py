"""Membership and order tests for the :class:`Phase` lifecycle enum (2.1.1).

The corpus's canonical phase order is delivered by the ``phase_names`` fixture,
so this module checks :class:`Phase` against the corpus without a runtime value
import of the corpus ``PHASE_ORDER`` constant (the developers-guide "Shared test
scaffolding" rule).
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.state import PHASE_ORDER, Phase


def test_member_values_are_kebab_case_strings() -> None:
    """Every member's value is its kebab-case on-disk string (design §5.1)."""
    # A StrEnum member *is* its string value; spot-check the kebab-case members
    # whose value differs from a naive lower-cased member name.
    # Map member -> expected kebab-case value; a dict keeps the comparison off a
    # bare ``member == "literal"`` line, which ruff's hardcoded-password
    # heuristic (S105) flags when the value looks like ``final-pass``.
    expected = {
        Phase.CONFLICT_ANALYSIS: "conflict-analysis",
        Phase.READER_FIT: "reader-fit",
        Phase.FINAL_PASS: "final-pass",
        Phase.PREMISE: "premise",
        Phase.DONE: "done",
    }
    for member, value in expected.items():
        assert str(member) == value
    # No member value carries an underscore; the on-disk spelling is kebab-case.
    assert all("_" not in str(member) for member in Phase)


def test_order_matches_corpus_phase_names(phase_names: tuple[str, ...]) -> None:
    """``list(Phase)`` equals the corpus ``phase_names`` order exactly."""
    assert tuple(str(member) for member in Phase) == phase_names


def test_phase_order_constant_mirrors_iteration() -> None:
    """``PHASE_ORDER`` is exactly ``tuple(Phase)`` in declaration order."""
    assert tuple(Phase) == PHASE_ORDER
    assert PHASE_ORDER[0] is Phase.PREMISE
    assert PHASE_ORDER[-1] is Phase.DONE


def test_kebab_value_resolves_to_member() -> None:
    """A kebab-case string resolves to the matching :class:`Phase` member."""
    assert Phase("conflict-analysis") is Phase.CONFLICT_ANALYSIS


def test_unknown_string_raises_value_error() -> None:
    """An unknown phase string raises :class:`ValueError` at the boundary."""
    with pytest.raises(ValueError, match="not-a-phase"):
        Phase("not-a-phase")
