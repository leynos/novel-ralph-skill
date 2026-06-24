"""Hypothesis property coverage of the ai-isms pack's structural robustness.

These generalise the example-based ai-isms validation (``test_ai_isms_pack.py``)
over a range of *orderings*: the pack is data a maintainer hand-edits, so a future
re-ordering or hand-merge must not change which rules load or break compilation.
The properties draw their rules from the *loaded* pack rather than synthesising
arbitrary regexes (so no ``re.compile`` is wasted and the filtering trap does not
apply, mirroring ``tests/test_rulepack_properties.py``):

* ordering invariance — for any permutation of the pack's rules fed back through
  :func:`parse_rulepack`, the pack still loads, preserves the rule-id *set*, and
  every pattern compiles;
* non-negative threshold — every loaded rule carries ``threshold >= 0`` and every
  ``per_page`` rule (none today) would carry a positive ``page_words``; restated
  as a property so a future hand-edit that violates the loader's own invariant is
  caught at the pack level.

Each property carries an explicit bounded ``@settings``; the permutation space of
five rules is tiny, so the run stays well inside the global per-test timeout.
"""

from __future__ import annotations

import datetime as dt

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands._desloppify_report import ai_isms_pack_path
from novel_ralph_skill.rulepack import (
    RULEPACK_SCHEMA_VERSION,
    RuleBasis,
    load_rulepack,
    parse_rulepack,
)

# A decoded rule entry and a whole pack, as rebuilt from the loaded pack below.
type _RuleMapping = dict[str, object]
type _PackMapping = dict[str, object]

_PROPERTY_SETTINGS = settings(
    max_examples=100,
    deadline=dt.timedelta(milliseconds=400),
)


def _loaded_rule_mappings() -> list[_RuleMapping]:
    """Return the shipped ai-isms rules as raw, re-parseable TOML-style mappings.

    Rebuilds each loaded :class:`~novel_ralph_skill.rulepack.Rule` into the decoded
    mapping :func:`parse_rulepack` accepts, so a permutation of these can be fed
    back through the loader. ``page_words`` is present only for ``per_page`` rules,
    keeping every mapping valid by construction (no filtering).
    """
    rules = load_rulepack(ai_isms_pack_path()).rules
    mappings: list[_RuleMapping] = []
    for rule in rules:
        mapping: _RuleMapping = {
            "id": rule.id,
            "pattern": rule.pattern,
            "threshold": rule.threshold,
            "basis": str(rule.basis),
        }
        if rule.basis is RuleBasis.PER_PAGE:
            mapping["page_words"] = rule.page_words
        mappings.append(mapping)
    return mappings


def _pack_of(rules: list[_RuleMapping]) -> _PackMapping:
    """Wrap rule mappings into a decoded ai-isms pack mapping."""
    return {
        "schema_version": RULEPACK_SCHEMA_VERSION,
        "pack": "ai-isms",
        "rule": rules,
    }


@pytest.fixture(scope="module")
def loaded_rule_mappings() -> list[_RuleMapping]:
    """Load the shipped ai-isms rules once per module as re-parseable mappings."""
    return _loaded_rule_mappings()


@pytest.fixture(scope="module")
def expected_ids(loaded_rule_mappings: list[_RuleMapping]) -> frozenset[object]:
    """Return the shipped rule-id set, computed once per module."""
    return frozenset(mapping["id"] for mapping in loaded_rule_mappings)


@given(data=st.data())
@_PROPERTY_SETTINGS
def test_any_ordering_loads_and_compiles(
    data: st.DataObject,
    loaded_rule_mappings: list[_RuleMapping],
    expected_ids: frozenset[object],
) -> None:
    """Any permutation of the pack's rules parses, preserving ids and compilation.

    The permutation strategy draws from the loaded rule list, so every input is a
    valid re-ordering of the real pack — there is nothing to ``assume`` away. The
    property pairs the "no-raise" parse with a real check: the id *set* is
    preserved and every compiled pattern is a usable matcher.
    """
    ordering = data.draw(st.permutations(loaded_rule_mappings))
    pack = parse_rulepack(_pack_of(list(ordering)))
    assert frozenset(rule.id for rule in pack.rules) == expected_ids
    for rule in pack.rules:
        # The loader compiled the pattern; confirm the compiled matcher kept the
        # authored source verbatim (no escape doubling) and is a usable matcher
        # that scans without raising.
        assert rule.compiled.pattern == rule.pattern, (
            f"{rule.id} compiled source drifted from authored pattern"
        )
        rule.compiled.search("probe text the matcher must scan without raising")


def test_thresholds_non_negative_and_page_words_positive(
    loaded_rule_mappings: list[_RuleMapping],
) -> None:
    """Every loaded rule has ``threshold >= 0`` and valid ``page_words``.

    The invariant is the loader's own, restated at the pack level so a future
    hand-edit that smuggles in a negative threshold (or drops a ``per_page``
    rule's ``page_words``) is caught here. The pack has only five rows, so the
    test iterates every loaded rule rather than sampling one — the "every loaded
    rule" invariant is checked exhaustively (CodeRabbit WI3 finding).
    """
    pack = parse_rulepack(_pack_of(loaded_rule_mappings))
    for rule in pack.rules:
        assert rule.threshold >= 0, f"{rule.id} has negative threshold {rule.threshold}"
        if rule.basis is RuleBasis.PER_PAGE:
            assert rule.page_words is not None, (
                f"{rule.id} per_page rule lacks page_words"
            )
            assert rule.page_words > 0, (
                f"{rule.id} per_page rule has non-positive page_words {rule.page_words}"
            )
        else:
            assert rule.page_words is None, (
                f"{rule.id} manuscript rule carries page_words {rule.page_words}"
            )
