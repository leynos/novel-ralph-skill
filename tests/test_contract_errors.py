"""Unit tests for the shared envelope-messages exception base (roadmap 1.3.4).

These pin the contract of :class:`EnvelopeMessagesError` — the single home for
the envelope's human-prose ``messages`` (design §3.1; ADR-003) — and the
cross-layer hierarchy that the three domain exceptions form by subclassing it.

They also pin the concrete-binding leg of roadmap task 7.2.5 (addendum 7.2.5.1):
the four real loader-family errors must actually subclass the shared
``loaderkit`` bases, and the within-family and cross-family distinctness must
hold, so a future hand-edit cannot silently re-fork a binding or re-parent an
error while the suite stays green.
"""

from __future__ import annotations

from novel_ralph_skill.contract import EnvelopeMessagesError, StateInputError
from novel_ralph_skill.contract import errors as contract_errors
from novel_ralph_skill.ledger import LedgerError, LedgerFileError
from novel_ralph_skill.loaderkit.errors import PackError, PackFileError
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


def test_real_content_errors_bind_the_pack_error_base() -> None:
    """The real content errors subclass the shared exit-``2`` base (7.2.5).

    Pins the concrete-binding leg of the success criterion for the *real*
    classes: both :class:`RulePackError` and :class:`LedgerError` must subclass
    :class:`~novel_ralph_skill.loaderkit.errors.PackError`, so the consolidation
    cannot silently re-fork a private copy of the content base while the suite
    stays green.
    """
    assert issubclass(RulePackError, PackError), (
        "RulePackError must bind the shared loaderkit content base"
    )
    assert issubclass(LedgerError, PackError), (
        "LedgerError must bind the shared loaderkit content base"
    )


def test_real_file_errors_bind_the_pack_file_error_base() -> None:
    """The real file errors subclass the shared exit-``3`` base (7.2.5).

    Pins the concrete-binding leg for the *real* file classes: both
    :class:`RulePackFileError` and :class:`LedgerFileError` must subclass
    :class:`~novel_ralph_skill.loaderkit.errors.PackFileError`, so neither
    family can re-fork a private copy of the file base undetected.
    """
    assert issubclass(RulePackFileError, PackFileError), (
        "RulePackFileError must bind the shared loaderkit file base"
    )
    assert issubclass(LedgerFileError, PackFileError), (
        "LedgerFileError must bind the shared loaderkit file base"
    )


def test_ledger_errors_remain_unrelated() -> None:
    """The ledger family fans out from the base rather than chaining siblings.

    Mirrors :func:`test_rulepack_errors_remain_unrelated` for the ledger family:
    neither :class:`LedgerError` nor :class:`LedgerFileError` subclasses the
    other, so the exit-``2`` content catch and the exit-``3`` file catch stay
    separable.
    """
    assert not issubclass(LedgerError, LedgerFileError), (
        "LedgerError must not subclass LedgerFileError"
    )
    assert not issubclass(LedgerFileError, LedgerError), (
        "LedgerFileError must not subclass LedgerError"
    )


def test_content_errors_are_distinct_across_families() -> None:
    """The two families' content errors are unrelated siblings (Risk-3).

    Both :class:`RulePackError` and :class:`LedgerError` bind the same
    :class:`~novel_ralph_skill.loaderkit.errors.PackError` base, yet neither
    subclasses the other: a rule-pack content catch must never swallow a ledger
    content fault, nor the reverse. Pins the cross-family distinctness the
    Risk-3 mitigation references so the shared base cannot collapse the families
    into one catchable type.
    """
    assert not issubclass(RulePackError, LedgerError), (
        "RulePackError must not subclass LedgerError"
    )
    assert not issubclass(LedgerError, RulePackError), (
        "LedgerError must not subclass RulePackError"
    )
