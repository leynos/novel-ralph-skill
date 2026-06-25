"""Projection-level tests for the clean-pass findings contract (roadmap 7.1.3).

These pin the slimming at the smallest unit — the pure projection functions
:func:`report_outcome` and :func:`ledger_report_outcome` — independent of any
command run. Building a report with a mix of passing and failing findings and
asserting the projected ``result["findings"]`` lists exactly the failing entries
proves the slimming directly, so the contract is guarded below the snapshot
suites as well as within them (developers' guide "The clean-pass findings
contract").
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands._desloppify_report import report_outcome
from novel_ralph_skill.ledger.detect import DeviceFinding, LedgerReport
from novel_ralph_skill.ledger.report import ledger_report_outcome
from novel_ralph_skill.rulepack.detect import DetectionReport, RuleFinding
from novel_ralph_skill.rulepack.schema import RuleBasis


def _rule_finding(*, rule_id: str, count: int, threshold: int) -> RuleFinding:
    """Build a ``manuscript``-basis :class:`RuleFinding` for projection tests.

    The ``passed`` flag is derived from ``count <= threshold`` so a caller picks
    a passing or failing finding by choosing the counts, matching how the
    detection core aggregates.
    """
    return RuleFinding(
        rule_id=rule_id,
        pattern=rule_id,
        count=count,
        threshold=threshold,
        basis=RuleBasis.MANUSCRIPT,
        page_words=None,
        density=None,
        passed=count <= threshold,
        lines=(),
    )


def test_report_outcome_slims_findings_to_over_threshold() -> None:
    """The rule-pack projection lists only the failing rules in ``findings``.

    A report mixing two passing rules and one failing rule projects a single
    finding — the failing one — while ``violations`` still names exactly that
    rule, so the slimmed trail and the gating data stay in lockstep.
    """
    findings = (
        _rule_finding(rule_id="calm", count=0, threshold=2),
        _rule_finding(rule_id="smirked", count=3, threshold=1),
        _rule_finding(rule_id="plain", count=1, threshold=5),
    )
    report = DetectionReport(
        pack="offenders", total_words=100, findings=findings, passed=False
    )

    outcome = report_outcome(report)

    result = outcome.result
    projected = typ.cast("list[dict[str, object]]", result["findings"])
    assert [finding["rule_id"] for finding in projected] == ["smirked"]
    assert result["violations"] == ["smirked"]


def test_report_outcome_clean_pass_emits_empty_findings() -> None:
    """A clean rule-pack report projects ``findings: []`` and ``violations: []``."""
    findings = (
        _rule_finding(rule_id="calm", count=0, threshold=2),
        _rule_finding(rule_id="plain", count=1, threshold=5),
    )
    report = DetectionReport(
        pack="offenders", total_words=100, findings=findings, passed=True
    )

    outcome = report_outcome(report)

    assert outcome.result["findings"] == []
    assert outcome.result["violations"] == []


def _device_finding(*, device_id: str, count: int, max_count: int) -> DeviceFinding:
    """Build a ``max_count``-rationed :class:`DeviceFinding` for projection tests.

    The ``passed`` flag is derived from ``count <= max_count`` so a caller picks
    a within-ration or over-ration device by choosing the counts.
    """
    return DeviceFinding(
        device_id=device_id,
        pattern=device_id,
        count=count,
        ration_kind="max_count",
        max_count=max_count,
        bound=None,
        offending_chapters=(),
        passed=count <= max_count,
        lines=(),
    )


def test_ledger_report_outcome_slims_findings_to_over_ration() -> None:
    """The ledger projection lists only the over-ration devices in ``findings``.

    A report mixing a within-ration device and an over-ration device projects a
    single finding — the over-ration one — while ``violations`` names exactly
    that device, mirroring the rule-pack path's slimming.
    """
    findings = (
        _device_finding(device_id="rib", count=1, max_count=2),
        _device_finding(device_id="sternum", count=3, max_count=2),
    )
    report = LedgerReport(findings=findings, passed=False)

    outcome = ledger_report_outcome(report)

    result = outcome.result
    projected = typ.cast("list[dict[str, object]]", result["findings"])
    assert [finding["device_id"] for finding in projected] == ["sternum"]
    assert result["violations"] == ["sternum"]


def test_ledger_report_outcome_clean_pass_emits_empty_findings() -> None:
    """A within-ration ledger report projects ``findings: []`` and no violations."""
    findings = (_device_finding(device_id="rib", count=1, max_count=2),)
    report = LedgerReport(findings=findings, passed=True)

    outcome = ledger_report_outcome(report)

    assert outcome.result["findings"] == []
    assert outcome.result["violations"] == []
