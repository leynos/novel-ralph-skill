"""Unit tests for the shared envelope-messages exception base (roadmap 1.3.4).

These pin the contract of :class:`EnvelopeMessagesError` — the single home for
the envelope's human-prose ``messages`` (design §3.1; ADR-003) — and the
cross-layer hierarchy that the three domain exceptions form by subclassing it.
"""

from __future__ import annotations

from novel_ralph_skill.contract import EnvelopeMessagesError, StateInputError
from novel_ralph_skill.contract import errors as contract_errors
from novel_ralph_skill.rulepack import RulePackError, RulePackFileError


def test_messages_round_trip_as_tuple() -> None:
    """The base captures its varargs prose once as an immutable tuple."""
    err = EnvelopeMessagesError("a", "b")
    assert err.messages == ("a", "b"), "messages should capture the varargs prose"
    assert isinstance(err.messages, tuple), "messages should be an immutable tuple"


def test_args_round_trip() -> None:
    """The base preserves :class:`Exception` ``args``/``str`` behaviour."""
    assert EnvelopeMessagesError("a").args == ("a",), (
        "args should round-trip the varargs prose"
    )


def test_base_is_an_exception() -> None:
    """The base remains a plain :class:`Exception` subclass."""
    assert isinstance(EnvelopeMessagesError("a"), Exception), (
        "the base must remain an Exception subclass"
    )


def test_importable_from_both_paths() -> None:
    """The base is importable from the module and the package surface."""
    assert contract_errors.EnvelopeMessagesError is EnvelopeMessagesError, (
        "module and package re-export must be the same class"
    )


def test_state_input_error_subclasses_base() -> None:
    """``StateInputError`` rebases onto the base and inherits its storage."""
    assert issubclass(StateInputError, EnvelopeMessagesError), (
        "StateInputError must subclass the shared base"
    )
    assert StateInputError("x").messages == ("x",), (
        "StateInputError must inherit the messages storage"
    )


def test_all_three_domain_errors_subclass_the_base() -> None:
    """The three domain exceptions fan out from the one shared base."""
    assert issubclass(StateInputError, EnvelopeMessagesError), (
        "StateInputError must subclass the shared base"
    )
    assert issubclass(RulePackError, EnvelopeMessagesError), (
        "RulePackError must subclass the shared base"
    )
    assert issubclass(RulePackFileError, EnvelopeMessagesError), (
        "RulePackFileError must subclass the shared base"
    )


def test_rulepack_errors_remain_unrelated() -> None:
    """The hierarchy fans out from the base rather than chaining siblings."""
    assert not issubclass(RulePackError, RulePackFileError), (
        "RulePackError must not subclass RulePackFileError"
    )
    assert not issubclass(RulePackFileError, RulePackError), (
        "RulePackFileError must not subclass RulePackError"
    )


def test_each_subclass_round_trips_its_payload() -> None:
    """Every subclass keeps its ``messages`` tuple and any extra attribute."""
    assert StateInputError("s").messages == ("s",), (
        "StateInputError must round-trip its messages"
    )
    assert RulePackFileError("f").messages == ("f",), (
        "RulePackFileError must round-trip its messages"
    )
    rule_pack_error = RulePackError("r", rule_id="r1")
    assert rule_pack_error.messages == ("r",), (
        "RulePackError must round-trip its messages"
    )
    assert rule_pack_error.rule_id == "r1", "RulePackError must keep its rule_id"
