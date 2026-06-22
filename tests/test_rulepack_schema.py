"""Unit tests for the typed rule-pack schema and error types (roadmap 5.1.1).

These pin the *shapes* this task delivers — the closed :class:`RuleBasis` set,
the frozen, slotted :class:`Rule` and :class:`RulePack`, the schema-version
constant, and the two failure-channel exceptions — independent of any parsing.
The boundary behaviour that builds these from a decoded mapping is covered in
``tests/test_rulepack_loader.py``.
"""

from __future__ import annotations

import dataclasses
import re

import pytest

from novel_ralph_skill.rulepack import (
    RULEPACK_SCHEMA_VERSION,
    Rule,
    RuleBasis,
    RulePack,
    RulePackError,
    RulePackFileError,
)


def _make_rule() -> Rule:
    """Return a representative :class:`Rule` with distinct field values.

    Distinct, non-default values per field make a transposition bug observable
    in the round-trip assertions below.
    """
    return Rule(
        id="emdash",
        pattern=r"\bvery\b",
        compiled=re.compile(r"\bvery\b"),
        threshold=3,
        basis=RuleBasis.PER_PAGE,
        page_words=300,
    )


def test_rule_fields_round_trip_to_their_attributes() -> None:
    """Every :class:`Rule` field lands on its own attribute without transposition."""
    rule = _make_rule()
    assert rule.id == "emdash"
    assert rule.pattern == r"\bvery\b"
    assert rule.compiled.pattern == r"\bvery\b"
    assert rule.threshold == 3
    assert rule.basis is RuleBasis.PER_PAGE
    assert rule.page_words == 300


def test_rulepack_fields_round_trip_to_their_attributes() -> None:
    """Every :class:`RulePack` field lands on its own attribute."""
    rule = _make_rule()
    pack = RulePack(schema_version=1, pack="ai-isms", rules=(rule,))
    assert pack.schema_version == 1
    assert pack.pack == "ai-isms"
    assert pack.rules == (rule,)


@pytest.mark.parametrize(
    ("instance", "cls", "field_name", "new_value"),
    [
        (_make_rule(), Rule, "threshold", 9),
        (RulePack(schema_version=1, pack="ai-isms", rules=()), RulePack, "pack", "x"),
    ],
)
def test_schema_objects_are_frozen_and_slotted(
    instance: object,
    cls: type,
    field_name: str,
    new_value: object,
) -> None:
    """A schema object rejects attribute assignment and declares ``__slots__``.

    A non-literal attribute name exercises the frozen guard without a static
    read-only-assignment error from the type checker (and without tripping
    ruff's "use assignment instead of setattr" rule on a literal name).
    """
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field_name, new_value)
    assert hasattr(cls, "__slots__")


def test_rule_basis_has_exactly_the_two_members() -> None:
    """:class:`RuleBasis` is the closed two-member set with the §6.1 values."""
    assert tuple(RuleBasis) == (RuleBasis.MANUSCRIPT, RuleBasis.PER_PAGE)
    assert RuleBasis.MANUSCRIPT == "manuscript"
    assert RuleBasis.PER_PAGE == "per_page"
    assert RuleBasis("per_page") is RuleBasis.PER_PAGE


def test_schema_version_constant_is_one() -> None:
    """The rule-pack schema version is ``1`` (design §6.1)."""
    assert RULEPACK_SCHEMA_VERSION == 1


def test_rulepack_error_carries_rule_id_and_messages() -> None:
    """:class:`RulePackError` records ``rule_id`` and ``messages``."""
    error = RulePackError("rule 'broken' has a bad pattern", rule_id="broken")
    assert error.rule_id == "broken"
    assert error.messages == ("rule 'broken' has a bad pattern",)
    assert isinstance(error, Exception)


def test_rulepack_error_rule_id_defaults_to_none() -> None:
    """A pack-level :class:`RulePackError` names no rule (``rule_id is None``)."""
    error = RulePackError("schema_version 2 is unsupported")
    assert error.rule_id is None
    assert error.messages == ("schema_version 2 is unsupported",)


def test_rulepack_file_error_carries_messages() -> None:
    """:class:`RulePackFileError` records ``messages`` for the exit-3 envelope."""
    error = RulePackFileError("pack file is absent")
    assert error.messages == ("pack file is absent",)
    assert isinstance(error, Exception)


def test_the_two_error_types_are_distinct() -> None:
    """The two failure channels are distinct, unrelated exception types."""
    assert RulePackError is not RulePackFileError
    assert not issubclass(RulePackError, RulePackFileError)
    assert not issubclass(RulePackFileError, RulePackError)
