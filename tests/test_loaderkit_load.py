"""Unit tests for the shared ``loaderkit`` load primitives (roadmap 7.2.2).

These pin :func:`~novel_ralph_skill.loaderkit.load.entries`,
:func:`~novel_ralph_skill.loaderkit.load.compile_pattern`,
:func:`~novel_ralph_skill.loaderkit.load.reject_duplicate_ids`, and
:func:`~novel_ralph_skill.loaderkit.load.load_toml` against sentinel bundles.

Because **no** existing rule-pack or ledger suite asserts the empty-array,
at-index, must-be-array-of-tables, or duplicate-id strings (only one rule-pack
test pins the ``"array of tables"`` substring), this suite pins those messages in
full, verbatim, for **both** noun sets — the load-bearing prose pin that closes
the silent-drift hazard the container-noun (``pack``/``ledger``) split creates.
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.loaderkit.coerce import CoercionErrors
from novel_ralph_skill.loaderkit.load import (
    EntriesMessages,
    compile_pattern,
    entries,
    load_toml,
    reject_duplicate_ids,
)

if typ.TYPE_CHECKING:
    import pathlib


class _SentinelError(EnvelopeMessagesError):
    """A test-local content error recording the offending id the bundle passed."""

    def __init__(self, *messages: str, offending_id: str | None = None) -> None:
        """Record the messages and the offending id for assertions."""
        super().__init__(*messages)
        self.offending_id: str | None = offending_id


class _SentinelFileError(EnvelopeMessagesError):
    """A test-local file error standing in for ``*FileError``."""


def _bundle(
    *, per_id_noun: str = "rule", per_level_noun: str = "rule pack"
) -> CoercionErrors:
    """Build a :class:`CoercionErrors` raising :class:`_SentinelError`."""
    return CoercionErrors(
        content_error=lambda msg, oid: _SentinelError(msg, offending_id=oid),
        per_id_noun=per_id_noun,
        per_level_noun=per_level_noun,
    )


# The two pack families' verbatim ``EntriesMessages`` bindings, copied
# byte-for-byte from the former ``rulepack/parse.py`` and ``ledger/parse.py``
# ``_entries`` bodies. These are the strings the reroutes must reproduce exactly.
_RULE_MESSAGES = EntriesMessages(
    not_array="'rule' must be an array of tables, got {type_name}",
    empty="'rule' array is empty; a pack must declare at least one rule",
    non_mapping="rule at index {index} must be a table, got {type_name}",
)
_DEVICE_MESSAGES = EntriesMessages(
    not_array="'device' must be an array of tables, got {type_name}",
    empty="'device' array is empty; a ledger must declare at least one device",
    non_mapping="device at index {index} must be a table, got {type_name}",
)


def test_entries_returns_sequence_for_valid_array() -> None:
    """:func:`entries` returns the entry sequence for a valid array of tables."""
    bundle = _bundle()
    raw = {"rule": [{"id": "a"}, {"id": "b"}]}
    result = entries(raw, array_key="rule", messages=_RULE_MESSAGES, errors=bundle)
    assert list(result) == [{"id": "a"}, {"id": "b"}]


def test_entries_missing_array_raises() -> None:
    """:func:`entries` raises a require fault when the array key is absent.

    The ``match`` pins the require-branch prose so the test cannot pass on an
    unrelated sentinel failure.
    """
    bundle = _bundle()
    with pytest.raises(
        _SentinelError, match=r"rule pack is missing required key 'rule'"
    ):
        entries({}, array_key="rule", messages=_RULE_MESSAGES, errors=bundle)


@pytest.mark.parametrize(
    ("messages", "array_key", "expected"),
    [
        (_RULE_MESSAGES, "rule", "'rule' must be an array of tables, got int"),
        (_DEVICE_MESSAGES, "device", "'device' must be an array of tables, got int"),
    ],
)
def test_entries_not_array_pins_message(
    messages: EntriesMessages, array_key: str, expected: str
) -> None:
    """:func:`entries` pins the not-array message verbatim for both noun sets."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        entries({array_key: 7}, array_key=array_key, messages=messages, errors=bundle)
    assert excinfo.value.messages[0] == expected


@pytest.mark.parametrize(
    ("messages", "array_key", "value"),
    [
        (_RULE_MESSAGES, "rule", "abc"),
        (_DEVICE_MESSAGES, "device", b"abc"),
    ],
)
def test_entries_rejects_str_and_bytes(
    messages: EntriesMessages, array_key: str, value: object
) -> None:
    """:func:`entries` rejects a ``str``/``bytes`` "array" as not an array."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        entries(
            {array_key: value},
            array_key=array_key,
            messages=messages,
            errors=bundle,
        )
    assert "must be an array of tables" in excinfo.value.messages[0]


@pytest.mark.parametrize(
    ("messages", "array_key", "expected"),
    [
        (
            _RULE_MESSAGES,
            "rule",
            "'rule' array is empty; a pack must declare at least one rule",
        ),
        (
            _DEVICE_MESSAGES,
            "device",
            "'device' array is empty; a ledger must declare at least one device",
        ),
    ],
)
def test_entries_empty_pins_message(
    messages: EntriesMessages, array_key: str, expected: str
) -> None:
    """:func:`entries` pins the empty-array message verbatim for both noun sets.

    This is the load-bearing pin: the container noun (``pack``/``ledger``) is
    neither :class:`CoercionErrors` noun, so a bundle-only ``entries`` could not
    reproduce it. Asserting the full string for both sets catches container-noun
    drift no existing suite would.
    """
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        entries({array_key: []}, array_key=array_key, messages=messages, errors=bundle)
    assert excinfo.value.messages[0] == expected


@pytest.mark.parametrize(
    ("messages", "array_key", "expected"),
    [
        (_RULE_MESSAGES, "rule", "rule at index 0 must be a table, got int"),
        (_DEVICE_MESSAGES, "device", "device at index 0 must be a table, got int"),
    ],
)
def test_entries_non_mapping_pins_message(
    messages: EntriesMessages, array_key: str, expected: str
) -> None:
    """:func:`entries` pins the at-index message verbatim for both noun sets."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        entries(
            {array_key: [7]},
            array_key=array_key,
            messages=messages,
            errors=bundle,
        )
    assert excinfo.value.messages[0] == expected


def test_compile_pattern_returns_compiled() -> None:
    """:func:`compile_pattern` returns the compiled pattern for a valid regex."""
    bundle = _bundle()
    compiled = compile_pattern(r"a+b", errors=bundle, offending_id="x")
    assert compiled.search("aaab") is not None


def test_compile_pattern_invalid_raises_naming_id_with_cause() -> None:
    """:func:`compile_pattern` raises naming the id, chaining the ``re.error``."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        compile_pattern("(unclosed", errors=bundle, offending_id="x")
    error = excinfo.value
    assert error.offending_id == "x"
    assert "rule 'x'" in error.messages[0]
    assert "invalid pattern" in error.messages[0]
    assert error.__cause__ is not None


def test_reject_duplicate_ids_silent_for_distinct() -> None:
    """:func:`reject_duplicate_ids` is silent when every id is distinct."""
    bundle = _bundle()
    reject_duplicate_ids(["a", "b", "c"], errors=bundle)


@pytest.mark.parametrize(
    ("per_id_noun", "per_level_noun", "expected"),
    [
        ("rule", "rule pack", "rule 'a' is defined more than once; ids must be unique"),
        (
            "device",
            "device ledger",
            "device 'a' is defined more than once; ids must be unique",
        ),
    ],
)
def test_reject_duplicate_ids_names_first_repeat(
    per_id_noun: str, per_level_noun: str, expected: str
) -> None:
    """:func:`reject_duplicate_ids` names the first authoring-order repeat verbatim.

    Feeding ``["a", "b", "a", "b"]`` proves first-duplicate-wins: ``'a'`` is named,
    not ``'b'``. The full message is pinned for both noun sets (no existing suite
    asserts it).
    """
    bundle = _bundle(per_id_noun=per_id_noun, per_level_noun=per_level_noun)
    with pytest.raises(_SentinelError) as excinfo:
        reject_duplicate_ids(["a", "b", "a", "b"], errors=bundle)
    assert excinfo.value.messages[0] == expected
    assert excinfo.value.offending_id == "a"


def test_load_toml_returns_decoded_mapping(tmp_path: pathlib.Path) -> None:
    """:func:`load_toml` returns the decoded mapping for a valid TOML file."""
    path = tmp_path / "doc.toml"
    path.write_text('schema_version = 1\n[[rule]]\nid = "a"\n', encoding="utf-8")
    raw = load_toml(path, noun="rule pack", file_error=_SentinelFileError)
    assert raw["schema_version"] == 1


@pytest.mark.parametrize("noun", ["rule pack", "device ledger"])
def test_load_toml_absent_path_raises_file_error(
    tmp_path: pathlib.Path, noun: str
) -> None:
    """:func:`load_toml` raises the file error for an absent path, with the noun."""
    path = tmp_path / "missing.toml"
    with pytest.raises(_SentinelFileError) as excinfo:
        load_toml(path, noun=noun, file_error=_SentinelFileError)
    assert f"cannot read {noun} at" in excinfo.value.messages[0]
    assert excinfo.value.__cause__ is not None


@pytest.mark.parametrize("noun", ["rule pack", "device ledger"])
def test_load_toml_undecodable_raises_file_error(
    tmp_path: pathlib.Path, noun: str
) -> None:
    """:func:`load_toml` raises the file error for undecodable bytes, with the noun."""
    path = tmp_path / "broken.toml"
    path.write_text("= not valid toml =", encoding="utf-8")
    with pytest.raises(_SentinelFileError) as excinfo:
        load_toml(path, noun=noun, file_error=_SentinelFileError)
    assert f"cannot read {noun} at" in excinfo.value.messages[0]
    assert excinfo.value.__cause__ is not None
