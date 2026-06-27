"""Unit tests for the shared exit-2 usage-error envelope home (roadmap 7.3.7).

This module pins :func:`usage_error_outcome`, the single home for the exit-``2``
envelope a command *body* builds when it detects a bad invocation the Cyclopts
parser has already accepted (design §3.2; ADR-003; audit-2.2.4 Finding 1). It
also pins the :class:`BodyUsageError` marker base that the genuine body-usage
faults subclass. The helper is a pure total function over a small, enumerable
input space — an exception carrying recorded prose and one carrying none — so an
example-based unit test is the right adversary, since neither Hypothesis nor
CrossHair buys coverage these two cases do not (see ExecPlan WI1).
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.contract import (
    BodyUsageError,
    EnvelopeMessagesError,
    ExitCode,
    usage_error_outcome,
)
from novel_ralph_skill.contract import errors as contract_errors
from novel_ralph_skill.contract import runner as contract_runner

_FALLBACK_EXC = BodyUsageError()


@pytest.mark.parametrize(
    ("exc", "expected_messages"),
    [
        pytest.param(BodyUsageError("a", "b"), ("a", "b"), id="recorded-messages"),
        pytest.param(_FALLBACK_EXC, (str(_FALLBACK_EXC),), id="str-fallback"),
        pytest.param(EnvelopeMessagesError("x"), ("x",), id="broad-base"),
    ],
)
def test_usage_error_outcome_builds_exit_2_envelope(
    exc: EnvelopeMessagesError, expected_messages: tuple[str, ...]
) -> None:
    """The helper builds the exit-``2`` envelope for any envelope-messages fault.

    Covers the recorded-prose path, the ``str(exc)`` fallback when no prose was
    supplied, and the broad-base acceptance that lets the malformed-content arms
    (``RulePackError``, ``LedgerError``) delegate the identical envelope here
    rather than re-spelling it (Decision D2).
    """
    outcome = usage_error_outcome(exc)
    assert outcome.code == ExitCode.USAGE_ERROR, "must build the exit-2 outcome"
    assert len(outcome.result) == 0, "the usage outcome carries no result payload"
    assert tuple(outcome.messages) == expected_messages, (
        "the envelope messages should match the expected prose or str fallback"
    )


def test_body_usage_error_subclasses_envelope_base() -> None:
    """``BodyUsageError`` is an :class:`EnvelopeMessagesError` with shared storage."""
    assert issubclass(BodyUsageError, EnvelopeMessagesError), (
        "BodyUsageError must subclass the shared envelope-messages base"
    )
    assert BodyUsageError("m").messages == ("m",), (
        "BodyUsageError must inherit the messages storage"
    )


def test_symbols_importable_from_package_surface() -> None:
    """Both new symbols resolve on the package surface as the module objects."""
    assert contract_errors.BodyUsageError is BodyUsageError, (
        "module and package re-export of BodyUsageError must be the same class"
    )
    assert contract_runner.usage_error_outcome is usage_error_outcome, (
        "module and package re-export of usage_error_outcome must be the same"
    )
