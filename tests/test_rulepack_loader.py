"""Boundary and channel tests for the rule-pack loader (roadmap 5.1.1).

These cover the validating loader's two halves: :func:`load_rulepack` (the thin
``tomllib`` file convenience) and :func:`parse_rulepack` (the pure mapping-in
boundary). The headline assertion is
:func:`test_bad_pattern_names_rule`: loading a pack whose rule ``id = "broken"``
carries an uncompilable ``pattern`` raises :class:`RulePackError` naming
``broken`` — the roadmap 5.1.1 success criterion that an invalid regular
expression fails loudly, naming the rule.

The two failure channels are kept distinct: malformed *content* raises
:class:`RulePackError` (the command maps it to exit 2), while an absent or
undecodable *file* raises :class:`RulePackFileError` (exit 3).
"""

from __future__ import annotations

import re
import typing as typ
from pathlib import Path

import pytest

from novel_ralph_skill.rulepack import (
    RuleBasis,
    RulePack,
    RulePackError,
    RulePackFileError,
    load_rulepack,
    parse_rulepack,
)

_RULEPACKS = Path(__file__).resolve().parent / "data" / "rulepacks"


def _fixture(name: str) -> Path:
    """Return the path to a rule-pack fixture by file name."""
    return _RULEPACKS / name


def test_valid_pack_loads_with_compiled_patterns() -> None:
    """``valid.toml`` yields two rules with compiled patterns and a page size."""
    pack = load_rulepack(_fixture("valid.toml"))
    assert isinstance(pack, RulePack)
    assert pack.schema_version == 1
    assert pack.pack == "ai-isms"
    assert len(pack.rules) == 2

    manuscript, per_page = pack.rules
    assert manuscript.id == "tapestry"
    assert manuscript.basis is RuleBasis.MANUSCRIPT
    assert manuscript.threshold == 0
    assert manuscript.page_words is None
    assert isinstance(manuscript.compiled, re.Pattern)
    assert manuscript.compiled.search("a tapestry of lies") is not None

    assert per_page.id == "delve"
    assert per_page.basis is RuleBasis.PER_PAGE
    assert per_page.threshold == 5
    assert per_page.page_words == 300
    assert per_page.compiled.search("let us delve in") is not None


def test_bad_pattern_names_rule() -> None:
    """An uncompilable pattern fails loudly, naming the offending rule.

    This is the roadmap 5.1.1 success criterion, asserted directly: the raised
    :class:`RulePackError` carries ``rule_id == "broken"`` and a message naming
    ``broken``.
    """
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("bad-pattern.toml"))
    error = excinfo.value
    assert error.rule_id == "broken"
    assert any("broken" in message for message in error.messages)


def test_bad_version_is_a_pack_level_fault() -> None:
    """An unsupported ``schema_version`` raises naming the version, not a rule."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("bad-version.toml"))
    error = excinfo.value
    assert error.rule_id is None
    assert any("2" in message for message in error.messages)


@pytest.mark.parametrize(
    ("fixture_name", "rule_id"),
    [
        ("unknown-basis.toml", "perparagraph"),
        ("per-page-missing-page-words.toml", "delve"),
        ("negative-threshold.toml", "tapestry"),
        ("missing-pattern.toml", "noprose"),
        ("non-string-pattern.toml", "numericpattern"),
        ("non-integer-threshold.toml", "stringthreshold"),
        ("float-threshold.toml", "floatthreshold"),
        ("non-integer-page-words.toml", "stringpagewords"),
        ("stray-page-words.toml", "straypagewords"),
        ("unknown-rule-key.toml", "typokey"),
        ("duplicate-id.toml", "x"),
    ],
)
def test_rule_level_faults_name_the_rule(fixture_name: str, rule_id: str) -> None:
    """Each rule-level fault raises :class:`RulePackError` naming its rule id.

    These are the exit-2 content faults, including every missing/wrong-typed
    field a non-validating (cast-only) boundary would wave through; their
    presence proves the boundary validates rather than coerces.
    """
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture(fixture_name))
    error = excinfo.value
    assert error.rule_id == rule_id
    assert any(rule_id in message for message in error.messages)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "non-integer-schema-version.toml",
        "missing-pack.toml",
        "missing-rule-array.toml",
        "empty-rule-array.toml",
        "unknown-pack-key.toml",
        # A missing 'id' is a pack-level fault: the rule cannot be named, so the
        # error names its array index instead (rule_id is None).
        "missing-id.toml",
    ],
)
def test_pack_level_faults_name_no_rule(fixture_name: str) -> None:
    """Each pack-level fault raises :class:`RulePackError` with ``rule_id is None``."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture(fixture_name))
    assert excinfo.value.rule_id is None


def test_missing_id_names_the_rule_index() -> None:
    """A rule without an ``id`` names its array index (``0``), having no id to name."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("missing-id.toml"))
    error = excinfo.value
    assert error.rule_id is None
    assert any("0" in message for message in error.messages)


def test_non_integer_threshold_is_not_coerced() -> None:
    """A string ``threshold`` raises rather than being treated as the integer 0."""
    with pytest.raises(RulePackError):
        load_rulepack(_fixture("non-integer-threshold.toml"))


def test_non_integer_schema_version_is_not_coerced() -> None:
    """A string ``schema_version`` raises rather than being cast to the integer 1."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("non-integer-schema-version.toml"))
    assert excinfo.value.rule_id is None


def test_absent_file_is_the_state_channel(tmp_path: Path) -> None:
    """A non-existent path raises :class:`RulePackFileError` (exit-3), not exit-2."""
    with pytest.raises(RulePackFileError):
        load_rulepack(tmp_path / "does-not-exist.toml")


def test_undecodable_toml_is_the_state_channel() -> None:
    """Undecodable TOML raises :class:`RulePackFileError`, not :class:`RulePackError`.

    A decode fault is an input fault (exit 3), distinct from a structurally
    valid TOML that violates the schema (exit 2).
    """
    with pytest.raises(RulePackFileError):
        load_rulepack(_fixture("undecodable.toml"))


def _valid_mapping() -> dict[str, object]:
    """Return a well-formed decoded rule-pack mapping for direct parse tests."""
    return {
        "schema_version": 1,
        "pack": "ai-isms",
        "rule": [
            {
                "id": "tapestry",
                "pattern": r"\btapestry\b",
                "threshold": 0,
                "basis": "manuscript",
            }
        ],
    }


def test_parse_rulepack_accepts_a_well_formed_mapping() -> None:
    """:func:`parse_rulepack` validates a good mapping without a filesystem."""
    pack = parse_rulepack(_valid_mapping())
    assert pack.rules[0].id == "tapestry"
    assert pack.rules[0].basis is RuleBasis.MANUSCRIPT


def test_parse_rulepack_rejects_bad_pattern_in_memory() -> None:
    """An in-memory uncompilable pattern raises naming the rule."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    rules[0]["pattern"] = "a("
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "tapestry"


def test_parse_rulepack_rejects_missing_id_in_memory() -> None:
    """A rule mapping with no ``id`` names the rule index, ``rule_id is None``."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    del rules[0]["id"]
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id is None
    assert any("0" in message for message in excinfo.value.messages)


def test_parse_rulepack_rejects_string_threshold_in_memory() -> None:
    """An in-memory string ``threshold`` raises rather than being treated as 0."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    rules[0]["threshold"] = "0"
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "tapestry"


def test_parse_rulepack_rejects_bool_threshold_in_memory() -> None:
    """A ``bool`` ``threshold`` raises: ``isinstance(True, int)`` must not pass."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    rules[0]["threshold"] = True
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "tapestry"


def test_unknown_rule_key_names_the_key() -> None:
    """A misspelled rule field is rejected, naming the rule and the offending key."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("unknown-rule-key.toml"))
    error = excinfo.value
    assert error.rule_id == "typokey"
    assert any("thresold" in message for message in error.messages)


def test_unknown_pack_key_names_the_key() -> None:
    """A stray top-level key is rejected at pack level, naming the offending key."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("unknown-pack-key.toml"))
    error = excinfo.value
    assert error.rule_id is None
    assert any("extra" in message for message in error.messages)


def test_duplicate_id_names_the_colliding_id() -> None:
    """Two rules sharing an ``id`` are rejected, naming the duplicated id."""
    with pytest.raises(RulePackError) as excinfo:
        load_rulepack(_fixture("duplicate-id.toml"))
    error = excinfo.value
    assert error.rule_id == "x"
    assert any("x" in message for message in error.messages)


def test_parse_rulepack_rejects_unknown_rule_key_in_memory() -> None:
    """An in-memory unknown rule key raises naming the rule, not silently ignored."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    rules[0]["thresold"] = 99
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "tapestry"


def test_parse_rulepack_rejects_unknown_pack_key_in_memory() -> None:
    """An in-memory stray pack key raises at pack level, not silently ignored."""
    raw = _valid_mapping()
    raw["extra"] = "y"
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id is None


def test_parse_rulepack_rejects_duplicate_ids_in_memory() -> None:
    """Two in-memory rules sharing an ``id`` raise naming the colliding id."""
    raw = _valid_mapping()
    rules = typ.cast("list[dict[str, object]]", raw["rule"])
    rules.append(dict(rules[0]))
    with pytest.raises(RulePackError) as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "tapestry"
