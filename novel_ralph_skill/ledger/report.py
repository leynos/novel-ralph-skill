"""Envelope projection for ``desloppify --ledger`` (roadmap task 7.1.2).

This module holds the pure projection from a
:class:`~novel_ralph_skill.ledger.detect.LedgerReport` to the shared envelope's
:class:`~novel_ralph_skill.contract.runner.CommandOutcome`. It lives in the
``ledger`` package (not beside the rule-pack projection) because the ledger emits
its **own** payload: it must NOT reuse or alter the rule-pack ``_finding_payload``
(ExecPlan Constraint: do not pre-empt the per-hit payload-contract decisions
7.1.4/7.1.5). Roadmap 7.1.3 has now slimmed the audit trail: ``findings`` carries
only the over-ration devices, uniformly with the rule-pack path, so a
within-ration manuscript emits ``findings: []`` (the clean-pass findings
contract; developers' guide "The clean-pass findings contract"). The detection
core still aggregates a finding for every device; only this projection slims.

The projection follows the contract (design §3.1, §3.2; ADR-003): ``result``
carries the machine payload the harness reads — the over-ration ``violations``
list and the slimmed per-device ``findings`` trail — while ``messages`` carries
human prose the harness never parses (one line per over-ration device naming the
breach). A clean ledger exits ``0``; any over-ration device exits ``4``.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome

if typ.TYPE_CHECKING:
    from novel_ralph_skill.ledger.detect import DeviceFinding, LedgerReport


def _finding_payload(finding: DeviceFinding) -> dict[str, object]:
    """Project one :class:`DeviceFinding` into its machine ``result`` payload.

    Emits the device id and authored pattern, the recomputed ``count``, the ration
    kind and its bounds (``max_count`` and the window ``bound``), the
    ``offending_chapters`` (which chapter leaked, for a window breach), the
    ``passed`` flag, and the ``{chapter, line}`` hit list. This is the ledger's
    own payload, deliberately distinct from the rule-pack ``_finding_payload``.

    Parameters
    ----------
    finding : DeviceFinding
        The aggregated per-device finding to project.

    Returns
    -------
    dict[str, object]
        The JSON-serialisable per-device payload for the envelope's ``result``.
    """
    return {
        "device_id": finding.device_id,
        "pattern": finding.pattern,
        "count": finding.count,
        "ration_kind": finding.ration_kind,
        "max_count": finding.max_count,
        "bound": list(finding.bound) if finding.bound is not None else None,
        "offending_chapters": list(finding.offending_chapters),
        "passed": finding.passed,
        "lines": [{"chapter": hit.chapter, "line": hit.line} for hit in finding.lines],
    }


def _finding_message(finding: DeviceFinding) -> str:
    """Return the human-prose line for one over-ration device.

    Names the device and how it breached: a ``max_count`` total over its bound, or
    the offending chapters for a window constraint (an out-of-allowed-set use, a
    use after retirement, or a use outside the reserved chapter). When ``max_count``
    pairs with a window, both clauses appear if both are breached.

    Parameters
    ----------
    finding : DeviceFinding
        A device finding that breached its ration.

    Returns
    -------
    str
        A one-line description naming the device and the breach.
    """
    clauses: list[str] = []
    if finding.max_count is not None and finding.count > finding.max_count:
        clauses.append(f"spent {finding.count} times (max {finding.max_count})")
    if finding.offending_chapters:
        chapters = ", ".join(str(chapter) for chapter in finding.offending_chapters)
        if finding.ration_kind == "allowed_chapters":
            allowed = ", ".join(str(chapter) for chapter in finding.bound or ())
            clauses.append(
                f"used in chapter(s) {chapters} outside allowed {{{allowed}}}"
            )
        elif finding.ration_kind == "retired_after_chapter":
            limit = finding.bound[0] if finding.bound else "?"
            clauses.append(
                f"used in chapter(s) {chapters} after retirement chapter {limit}"
            )
        elif finding.ration_kind == "reserved_for_chapter":
            reserved = finding.bound[0] if finding.bound else "?"
            clauses.append(
                f"used in chapter(s) {chapters} outside reserved chapter {reserved}"
            )
    breach = "; ".join(clauses) or "over its ration"
    return f"{finding.device_id} {breach}"


def ledger_report_outcome(report: LedgerReport) -> CommandOutcome:
    """Build the success/finding :class:`CommandOutcome` from a ledger report.

    A clean report exits ``0``; any over-ration device exits ``4``
    (``ACTIONABLE_FINDING``). ``result`` carries the machine payload — the
    over-ration ``violations`` list (the checker read shape, design §3.3) and the
    slimmed per-device ``findings`` trail — while ``messages`` carries human prose:
    one line per over-ration device, or a single clean note. Per the clean-pass
    findings contract (roadmap 7.1.3; developers' guide "The clean-pass findings
    contract"), ``findings`` lists only the over-ration devices, so a clean ledger
    emits ``findings: []``; the detection core still aggregates every device.

    Parameters
    ----------
    report : LedgerReport
        The detection result over the scanned chapters.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with empty ``violations`` when every device is within
        ration, or ``ExitCode.ACTIONABLE_FINDING`` naming the over-ration devices.
    """
    failed = [finding for finding in report.findings if not finding.passed]
    code = ExitCode.SUCCESS if report.passed else ExitCode.ACTIONABLE_FINDING
    return CommandOutcome(
        code=code,
        result={
            "violations": [finding.device_id for finding in failed],
            # Slim the audit trail to the over-ration devices (the clean-pass
            # findings contract, roadmap 7.1.3; developers' guide "The clean-pass
            # findings contract"), so a within-ration manuscript emits
            # ``findings: []``. The detection core still aggregates every device;
            # only this projection slims, in lockstep with the rule-pack path.
            "findings": [_finding_payload(finding) for finding in failed],
        },
        messages=[_finding_message(finding) for finding in failed]
        or ["no rationing breaches detected"],
    )
