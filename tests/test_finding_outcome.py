"""Unit tests for the shared finding-outcome builder (roadmap task 7.1.4).

These pin :func:`build_finding_outcome` in isolation, over a tiny local dummy
finding type that imports neither ``rulepack`` nor ``ledger`` — proving the
builder is generic over an opaque finding. They guard the four load-bearing
contracts: the failed-filter slimming, the clean-pass envelope, the
exit-code-from-``failed`` invariant (roadmap addendum 8.1.3.2 / its 7.1.3.2
twin), and the ``result`` key-insertion order the raw machine JSON depends on
(``render_machine`` does not sort keys, so the snapshots cannot guard order).
"""

from __future__ import annotations

import dataclasses
import typing as typ

from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.finding_outcome import build_finding_outcome

if typ.TYPE_CHECKING:
    from novel_ralph_skill.contract.runner import CommandOutcome


@dataclasses.dataclass(frozen=True)
class _DummyFinding:
    """A minimal opaque finding for builder tests.

    Carries only the fields the injected callables read: a slug ``ident``, a
    ``passed`` flag, and a ``note`` the payload/message projections echo.
    """

    ident: str
    passed: bool
    note: str


def _outcome(
    findings: tuple[_DummyFinding, ...],
    *,
    extra_result: dict[str, object] | None = None,
) -> CommandOutcome:
    """Call the builder with the dummy projections and optional ``extra_result``.

    Wires the id accessor, payload, message, and ``passed`` projections to the
    dummy finding's fields so each test only states the findings and, where it
    matters, the ``extra_result`` keys.
    """
    return build_finding_outcome(
        findings,
        identify=lambda finding: finding.ident,
        payload=lambda finding: {"ident": finding.ident, "note": finding.note},
        describe=lambda finding: f"breach: {finding.ident}",
        passed=lambda finding: finding.passed,
        clean_message="all clear",
        extra_result=extra_result,
    )


def test_builder_slims_to_failed_findings() -> None:
    """A mix of passing and failing findings projects only the failed ones.

    ``violations`` names exactly the failed ids, ``findings`` carries exactly
    their payloads, and ``messages`` holds one ``describe`` line per failed
    finding, so the gating data and the slimmed trail stay in lockstep.
    """
    findings = (
        _DummyFinding(ident="calm", passed=True, note="ok"),
        _DummyFinding(ident="smirked", passed=False, note="hit"),
        _DummyFinding(ident="plain", passed=True, note="ok"),
    )

    outcome = _outcome(findings)

    result = outcome.result
    projected = typ.cast("list[dict[str, object]]", result["findings"])
    assert result["violations"] == ["smirked"]
    assert [payload["ident"] for payload in projected] == ["smirked"]
    assert list(outcome.messages) == ["breach: smirked"]
    assert outcome.code is ExitCode.ACTIONABLE_FINDING


def test_builder_clean_pass_emits_empty_skeleton() -> None:
    """All-passing findings yield empty lists, success, and the clean message."""
    findings = (
        _DummyFinding(ident="calm", passed=True, note="ok"),
        _DummyFinding(ident="plain", passed=True, note="ok"),
    )

    outcome = _outcome(findings)

    assert outcome.result["violations"] == []
    assert outcome.result["findings"] == []
    assert list(outcome.messages) == ["all clear"]
    assert outcome.code is ExitCode.SUCCESS


def test_builder_derives_code_from_failed_not_external_flag() -> None:
    """The exit code follows the ``failed`` filter, closing 8.1.3.2/7.1.3.2.

    A single failing finding yields ``ACTIONABLE_FINDING`` regardless of any
    external "passed" signal, because the builder reads only the negation of the
    injected ``passed`` projection. This is the case the old
    ``report.passed``-derived code could get wrong; the builder is correct by
    construction.
    """
    findings = (_DummyFinding(ident="smirked", passed=False, note="hit"),)

    outcome = _outcome(findings)

    assert outcome.code is ExitCode.ACTIONABLE_FINDING


def test_builder_preserves_extra_result_key_order() -> None:
    """``extra_result`` keys precede ``violations``/``findings`` in order.

    The raw machine JSON preserves ``result`` insertion order (``render_machine``
    does not sort keys), so this pins the load-bearing order the snapshots cannot
    guard. With extra keys the order is the extras then ``violations`` then
    ``findings``; without them it is ``violations`` then ``findings``.
    """
    findings = (_DummyFinding(ident="smirked", passed=False, note="hit"),)

    with_extra = _outcome(findings, extra_result={"pack": "p", "total_words": 3})
    assert list(with_extra.result) == [
        "pack",
        "total_words",
        "violations",
        "findings",
    ]

    without_extra = _outcome(findings)
    assert list(without_extra.result) == ["violations", "findings"]


_FINDINGS = st.lists(
    st.builds(
        _DummyFinding,
        ident=st.text(min_size=1, max_size=8),
        passed=st.booleans(),
        note=st.text(max_size=8),
    ),
    max_size=8,
)


@settings(max_examples=200)
@given(findings=_FINDINGS)
def test_builder_exit_code_tracks_any_failed_finding(
    findings: list[_DummyFinding],
) -> None:
    """The exit code is ``ACTIONABLE_FINDING`` iff any finding failed.

    The four enumerated unit cases pin the exit-code-from-``failed`` contract over
    the deterministic boundary; this property hardens the closure against future
    builder edits over arbitrary pass/fail finding vectors. The oracle is the
    contract restated structurally — ``failed`` is the negation of the injected
    ``passed`` projection (roadmap addendum 8.1.3.2 / its 7.1.3.2 twin) — never the
    builder's own derivation, so the property would notice a builder that read an
    external ``passed`` flag instead. The findings come straight from a strategy
    over the ``passed`` booleans (no filtering), so shrinking yields a minimal
    counter-example.
    """
    outcome = _outcome(tuple(findings))

    any_failed = any(not finding.passed for finding in findings)
    expected = ExitCode.ACTIONABLE_FINDING if any_failed else ExitCode.SUCCESS
    assert outcome.code is expected
