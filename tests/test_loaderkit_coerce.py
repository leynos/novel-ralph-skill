"""Unit tests for the shared ``loaderkit`` coercion primitives (roadmap 7.2.2).

These pin the error-factory seam directly: each primitive raises *whatever error
the bound :class:`~novel_ralph_skill.loaderkit.coerce.CoercionErrors` bundle
supplies* with the bundle's noun, proving the parameterisation is the single seam
a third pack family would bind, so the primitives cannot silently re-fork.

A sentinel bundle supplies a test-local
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` subclass that
records the offending id, so the tests can assert both the raised *type* and the
carried id without depending on the rule-pack or ledger error channels. The
``where`` prefix is pinned verbatim for both noun pairs (the load-bearing prose
claim).
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.loaderkit.coerce import (
    CoercionErrors,
    reject_unknown_keys,
    require,
    require_int,
    require_str,
    where,
)


class _SentinelError(EnvelopeMessagesError):
    """A test-local content error recording the offending id the bundle passed."""

    def __init__(self, *messages: str, offending_id: str | None = None) -> None:
        """Record the messages and the offending id for assertions."""
        super().__init__(*messages)
        self.offending_id: str | None = offending_id


def _sentinel_bundle(
    *, per_id_noun: str = "rule", per_level_noun: str = "rule pack"
) -> CoercionErrors:
    """Build a :class:`CoercionErrors` raising :class:`_SentinelError`."""
    return CoercionErrors(
        content_error=lambda msg, oid: _SentinelError(msg, offending_id=oid),
        per_id_noun=per_id_noun,
        per_level_noun=per_level_noun,
    )


def test_require_returns_present_value() -> None:
    """:func:`require` returns the value when the key is present."""
    bundle = _sentinel_bundle()
    assert require({"k": 7}, "k", errors=bundle, offending_id="x") == 7


def test_require_raises_naming_key_and_id() -> None:
    """:func:`require` raises the sentinel naming the key and the offending id."""
    bundle = _sentinel_bundle()
    with pytest.raises(_SentinelError) as excinfo:
        require({}, "pattern", errors=bundle, offending_id="x")
    error = excinfo.value
    assert error.offending_id == "x"
    assert any("'pattern'" in message for message in error.messages)
    assert any("rule 'x'" in message for message in error.messages)


def test_require_str_returns_narrowed_value() -> None:
    """:func:`require_str` returns the narrowed ``str`` for a string value."""
    bundle = _sentinel_bundle()
    assert require_str({"k": "v"}, "k", errors=bundle, offending_id="x") == "v"


def test_require_str_rejects_non_string() -> None:
    """:func:`require_str` raises the sentinel naming the field and its type."""
    bundle = _sentinel_bundle()
    with pytest.raises(_SentinelError) as excinfo:
        require_str({"k": 7}, "k", errors=bundle, offending_id="x")
    error = excinfo.value
    assert error.offending_id == "x"
    assert any("must be a string" in message for message in error.messages)
    assert any("got int" in message for message in error.messages)


def test_require_int_returns_narrowed_value() -> None:
    """:func:`require_int` returns the narrowed ``int`` for an integer value."""
    bundle = _sentinel_bundle()
    assert require_int({"k": 3}, "k", errors=bundle, offending_id="x") == 3


@pytest.mark.parametrize("value", [True, "3", 3.0])
def test_require_int_rejects_bool_str_and_float(value: object) -> None:
    """:func:`require_int` rejects ``bool``, ``str``, and ``float`` values."""
    bundle = _sentinel_bundle()
    with pytest.raises(_SentinelError) as excinfo:
        require_int({"k": value}, "k", errors=bundle, offending_id="x")
    assert any("must be an integer" in message for message in excinfo.value.messages)


def test_reject_unknown_keys_silent_when_all_allowed() -> None:
    """:func:`reject_unknown_keys` is silent when every key is allowed."""
    bundle = _sentinel_bundle()
    reject_unknown_keys(
        {"a": 1, "b": 2},
        frozenset({"a", "b", "c"}),
        errors=bundle,
        offending_id=None,
    )


def test_reject_unknown_keys_lists_unknown_and_allowed_sorted() -> None:
    """:func:`reject_unknown_keys` lists the unknown and the sorted allowed keys."""
    bundle = _sentinel_bundle()
    with pytest.raises(_SentinelError) as excinfo:
        reject_unknown_keys(
            {"b": 1, "a": 2, "z": 3, "c": 4},
            frozenset({"a", "b"}),
            errors=bundle,
            offending_id=None,
        )
    message = excinfo.value.messages[0]
    # Two unknown keys ('z', 'c') are listed sorted, proving the ordering.
    assert "unknown key(s) 'c', 'z'" in message
    assert "allowed keys are 'a', 'b'" in message


@pytest.mark.parametrize(
    ("per_id_noun", "per_level_noun", "offending_id", "expected"),
    [
        ("rule", "rule pack", "x", "rule 'x'"),
        ("rule", "rule pack", None, "rule pack"),
        ("device", "device ledger", "y", "device 'y'"),
        ("device", "device ledger", None, "device ledger"),
    ],
)
def test_where_pins_both_noun_pairs(
    per_id_noun: str,
    per_level_noun: str,
    offending_id: str | None,
    expected: str,
) -> None:
    """:func:`where` reproduces both noun pairs' prefixes verbatim."""
    bundle = _sentinel_bundle(per_id_noun=per_id_noun, per_level_noun=per_level_noun)
    assert where(bundle, offending_id) == expected
