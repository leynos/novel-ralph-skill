"""Hypothesis property coverage of the rule-pack loader's validation invariants.

These generalise the example-based loader tests (roadmap 5.1.1) over a range of
inputs, covering the invariants that *are* an invariant over a range of inputs:

* round-trip fidelity — :func:`parse_rulepack` accepts every well-formed pack
  and preserves rule count, order, and each rule's ``id``/``threshold``/``basis``;
* schema-version rejection — any version other than the expected one raises;
* the headline "names the offending rule" invariant — any rule whose ``pattern``
  is uncompilable raises :class:`RulePackError` whose ``rule_id`` is that rule's
  ``id``, generalised across patterns and positions.

Following the ``tests/test_contract_properties.py`` precedent, every input comes
from a strategy (no function-scoped fixtures, which would trip
``HealthCheck.function_scoped_fixture``); each property carries an explicit
bounded ``@settings`` and draws patterns from a small curated set so every
``re.compile`` is cheap, keeping each test well inside the global 30 s per-test
timeout under ``pytest -n auto``.
"""

from __future__ import annotations

import datetime as dt
import typing as typ

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.rulepack import (
    RULEPACK_SCHEMA_VERSION,
    RuleBasis,
    RulePackError,
    parse_rulepack,
)

# A decoded rule entry and a whole pack, as the strategies below build them.
type _RuleMapping = dict[str, object]
type _PackMapping = dict[str, object]


def _rules_of(pack: _PackMapping) -> list[_RuleMapping]:
    """Return the pack's mutable rule list, typed for in-place mutation.

    The strategies build ``pack["rule"]`` as a ``list[dict[str, object]]``; this
    restates that fact for the type checker so a test can index and mutate an
    entry without a stream of ``isinstance`` narrowings.
    """
    return typ.cast("list[_RuleMapping]", pack["rule"])


# Cheap-to-compile, always-valid regular-expression sources. Drawing patterns
# from a curated set keeps every ``re.compile`` sub-millisecond, so no
# pathological generated pattern can blow the deadline (B3).
_VALID_PATTERNS = ("very", r"\bdelve\b", "a+b", "tapestry|mosaic", r"\d{2}")

# A curated set of sources ``re.compile`` rejects eagerly, used to prove the
# "names the offending rule" invariant across patterns.
_UNCOMPILABLE_PATTERNS = ("a(", "[", "(?P<>x)", "*", r"\1")

_PROPERTY_SETTINGS = settings(
    max_examples=100,
    deadline=dt.timedelta(milliseconds=400),
)

# Identifiers that never collide with a TOML key or each other within a pack.
_rule_ids = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=1,
    max_size=8,
)


@st.composite
def _well_formed_rule(draw: st.DrawFn, *, rule_id: str) -> _RuleMapping:
    """Build one well-formed rule mapping with the given ``id``.

    ``page_words`` is present if and only if the basis is ``per_page``, so the
    rule is valid by construction (no filtering).
    """
    basis = draw(st.sampled_from(list(RuleBasis)))
    rule: _RuleMapping = {
        "id": rule_id,
        "pattern": draw(st.sampled_from(_VALID_PATTERNS)),
        "threshold": draw(st.integers(min_value=0, max_value=1000)),
        "basis": str(basis),
    }
    if basis is RuleBasis.PER_PAGE:
        rule["page_words"] = draw(st.integers(min_value=1, max_value=2000))
    return rule


@st.composite
def _well_formed_pack(draw: st.DrawFn) -> _PackMapping:
    """Build a well-formed rule-pack mapping with distinct rule ids."""
    ids = draw(st.lists(_rule_ids, min_size=1, max_size=6, unique=True))
    rules = [draw(_well_formed_rule(rule_id=rule_id)) for rule_id in ids]
    return {
        "schema_version": RULEPACK_SCHEMA_VERSION,
        "pack": draw(_rule_ids),
        "rule": rules,
    }


@given(raw=_well_formed_pack())
@_PROPERTY_SETTINGS
def test_well_formed_packs_round_trip(raw: _PackMapping) -> None:
    """Every well-formed pack parses and preserves rule count, order, and fields."""
    pack = parse_rulepack(raw)
    rules = _rules_of(raw)
    assert len(pack.rules) == len(rules)
    for parsed, source in zip(pack.rules, rules, strict=True):
        assert parsed.id == source["id"]
        assert parsed.threshold == source["threshold"]
        # Compare against the enum member, not its string, so a regression that
        # left ``basis`` as a plain string would fail here.
        assert isinstance(parsed.basis, RuleBasis)
        assert parsed.basis is RuleBasis(source["basis"])


@given(
    raw=_well_formed_pack(),
    bad_version=st.integers(min_value=-50, max_value=50).filter(
        lambda value: value != RULEPACK_SCHEMA_VERSION
    ),
)
@_PROPERTY_SETTINGS
def test_unexpected_schema_version_is_rejected(
    raw: _PackMapping, bad_version: int
) -> None:
    """Any ``schema_version`` other than the expected one raises a pack-level fault.

    The single ``.filter`` excludes exactly one value from a 101-value range, so
    the rejection budget is never a concern (the filtering trap does not apply).
    """
    raw["schema_version"] = bad_version
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id is None


@given(
    raw=_well_formed_pack(),
    bad_pattern=st.sampled_from(_UNCOMPILABLE_PATTERNS),
    target=st.integers(min_value=0),
)
@_PROPERTY_SETTINGS
def test_uncompilable_pattern_names_its_rule(
    raw: _PackMapping, bad_pattern: str, target: int
) -> None:
    """An uncompilable pattern raises naming exactly the rule that carries it.

    Generalises the headline criterion across patterns and positions: the bad
    pattern is injected into the rule at ``target`` modulo the pack size, and the
    raised error's ``rule_id`` must equal that rule's ``id``.
    """
    rules = _rules_of(raw)
    offending = rules[target % len(rules)]
    offending["pattern"] = bad_pattern
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == offending["id"]


@given(
    raw=_well_formed_pack(),
    target=st.integers(min_value=0),
    bad_threshold=st.one_of(
        st.text(max_size=4),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
    ),
)
@_PROPERTY_SETTINGS
def test_non_integer_threshold_names_its_rule(
    raw: _PackMapping, target: int, bad_threshold: object
) -> None:
    """A non-integer ``threshold`` (string, float, or bool) raises naming the rule.

    This exercises the ``_require_int`` type guard's exhaustiveness — including
    the ``bool``-is-``int`` trap — across a range of invalid types, rather than
    being treated as a valid integer threshold.
    """
    rules = _rules_of(raw)
    offending = rules[target % len(rules)]
    offending["threshold"] = bad_threshold
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == offending["id"]
