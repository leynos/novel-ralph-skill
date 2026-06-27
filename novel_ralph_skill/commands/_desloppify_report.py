"""Envelope projection for the ``desloppify`` command (roadmap task 5.1.2).

This module holds the pure projection from a
:class:`~novel_ralph_skill.rulepack.detect.DetectionReport` to the shared
envelope's :class:`~novel_ralph_skill.contract.runner.CommandOutcome`, plus the
:func:`offenders_pack_path` resolver for the shipped §6 pack. It lives beside the
command body (:mod:`novel_ralph_skill.commands._desloppify`) so that module stays
within the 400-line cap (AGENTS.md "clear file boundaries"), exactly as
``_recount.py`` sits beside the mutator module.

The projection follows the contract (design §3.1, §3.3; ADR-003): ``result``
carries the machine payload the harness reads — ``pack``, ``total_words``, the
failed-rule ``violations`` list, and the slimmed ``findings`` trail (only the
over-threshold rules, per the clean-pass findings contract, roadmap 7.1.3; see
the developers' guide "The clean-pass findings contract") — while ``messages``
carries human prose the harness never parses. Each finding emits the
fields design §4.4 enumerates per hit: ``phrase`` (the rule's authored pattern
source), ``count``, ``density`` per N words, ``threshold``, ``passed``, and the
``lines`` numbers. ``basis`` is emitted as an explicit string so a future
non-``str`` ``RuleBasis`` cannot silently break the JSON contract (ExecPlan
round-1 advisory).
"""

from __future__ import annotations

import importlib.resources
import typing as typ

from novel_ralph_skill.contract.finding_outcome import build_finding_outcome

if typ.TYPE_CHECKING:
    from importlib.resources.abc import Traversable

    from novel_ralph_skill.contract.runner import CommandOutcome
    from novel_ralph_skill.rulepack.detect import DetectionReport, RuleFinding


def offenders_pack_path() -> Traversable:
    """Return the packaged §6 ``offenders.toml`` resource (ExecPlan Decision Log).

    Resolves the default rule pack shipped inside the package tree via
    :mod:`importlib.resources`, the stdlib-only way that survives wheel
    installation (the e2e proves the pack travels). The pack lives at
    ``novel_ralph_skill/rulepack/packs/offenders.toml`` and hatchling ships every
    non-``.py`` file under the package by default.

    The result is a :class:`~importlib.resources.abc.Traversable`, not a
    :class:`pathlib.Path`: a normal filesystem install yields a ``Path`` (which
    *is* a ``Traversable``), but a zipped install would yield a different
    ``Traversable``. ``load_rulepack`` accepts any ``Traversable`` because it only
    needs ``.open("rb")``, so returning the honest type avoids the unsafe cast a
    ``pathlib.Path`` annotation would require (CodeRabbit round-4 finding).

    Returns
    -------
    importlib.resources.abc.Traversable
        The shipped ``offenders.toml`` resource, openable in binary mode.
    """
    return importlib.resources.files("novel_ralph_skill.rulepack.packs").joinpath(
        "offenders.toml"
    )


def ai_isms_pack_path() -> Traversable:
    """Return the packaged ``ai-isms.toml`` resource (design §6.2; roadmap 7.1.1).

    Resolves the opt-in AI-ism pack shipped beside ``offenders.toml`` via
    :mod:`importlib.resources`, the stdlib-only way that survives wheel
    installation (the ai-isms e2e proves the pack travels). The pack lives at
    ``novel_ralph_skill/rulepack/packs/ai-isms.toml`` and hatchling ships every
    non-``.py`` file under the package by default, so it needs no build-config
    change. It is opt-in via ``desloppify --pack``; the default pack stays
    ``offenders.toml`` (ExecPlan scope; design §6.2).

    Returns a :class:`~importlib.resources.abc.Traversable`, not a
    :class:`pathlib.Path`, for the same reason :func:`offenders_pack_path` does:
    a filesystem install yields a ``Path`` (which *is* a ``Traversable``) while a
    zipped install would yield a different ``Traversable``, and ``load_rulepack``
    only needs ``.open("rb")``, so the honest type avoids an unsafe cast.

    Returns
    -------
    importlib.resources.abc.Traversable
        The shipped ``ai-isms.toml`` resource, openable in binary mode.
    """
    return importlib.resources.files("novel_ralph_skill.rulepack.packs").joinpath(
        "ai-isms.toml"
    )


def _finding_payload(finding: RuleFinding) -> dict[str, object]:
    """Project one :class:`RuleFinding` into its machine ``result`` payload.

    Emits the enumerated contract fields per hit — ``phrase``, ``count``,
    ``density``, ``threshold``, ``passed``, and ``lines`` (design §4.4: "phrase,
    count, density per N words, threshold, pass or fail, and line numbers";
    roadmap 5.1.2). ``phrase`` carries the rule's authored pattern source
    (``finding.pattern``), the regex that names the offender; ``rule_id`` is
    retained alongside it as the stable slug the ``violations`` list references.

    Emits ``basis`` as an explicit string (``finding.basis.value``) rather than
    the raw :class:`~novel_ralph_skill.rulepack.RuleBasis` member:
    ``render_machine`` calls :func:`json.dumps` with no ``default=`` handler, so
    although a ``StrEnum`` member serialises as its bare value today, pinning
    ``.value`` keeps the contract stable if ``RuleBasis`` ever becomes a
    non-``str`` Enum (ExecPlan round-1 advisory; the snapshot test asserts
    ``basis`` is a ``str``).

    Parameters
    ----------
    finding : RuleFinding
        The aggregated per-rule finding to project.

    Returns
    -------
    dict[str, object]
        The JSON-serialisable per-rule payload for the envelope's ``result``.
    """
    return {
        "rule_id": finding.rule_id,
        "phrase": finding.pattern,
        "count": finding.count,
        "threshold": finding.threshold,
        "basis": finding.basis.value,
        "density": finding.density,
        "passed": finding.passed,
        "lines": [{"chapter": hit.chapter, "line": hit.line} for hit in finding.lines],
    }


def _finding_message(finding: RuleFinding) -> str:
    """Return the human-prose line for one over-threshold rule.

    Parameters
    ----------
    finding : RuleFinding
        A finding that exceeded its threshold.

    Returns
    -------
    str
        A one-line description naming the rule and how far past threshold it is.
    """
    if finding.density is not None:
        return (
            f"{finding.rule_id} exceeds threshold "
            f"(density {finding.density:.2f} > {finding.threshold} "
            f"per {finding.page_words} words)"
        )
    return (
        f"{finding.rule_id} exceeds threshold ({finding.count} > {finding.threshold})"
    )


def report_outcome(report: DetectionReport) -> CommandOutcome:
    """Build the success/finding :class:`CommandOutcome` from a report.

    A clean report exits ``0``; any rule over threshold exits ``4``
    (``ACTIONABLE_FINDING``). ``result`` carries the machine payload — ``pack``,
    ``total_words``, the failed-rule ``violations`` list (the checker read shape,
    design §3.3), and the slimmed ``findings`` trail — while ``messages`` carries
    human prose: one line per failed rule, or a single clean-pass note (design
    §3.1; ADR-003). Per the clean-pass findings contract (roadmap 7.1.3;
    developers' guide "The clean-pass findings contract"), ``findings`` lists
    only the over-threshold rules, so a clean pass emits ``findings: []``; the
    detection core still aggregates a finding for every rule.

    The envelope skeleton — the failed filter, the exit-code derivation, and the
    ``violations``/``findings``/``messages`` assembly — comes from the shared
    :func:`~novel_ralph_skill.contract.finding_outcome.build_finding_outcome`
    builder (roadmap 7.1.4); this function injects only the rule-pack details:
    the ``rule_id`` accessor, the per-hit :func:`_finding_payload`, the per-hit
    :func:`_finding_message`, the ``pack``/``total_words`` extra keys (inserted
    before ``violations``/``findings`` to preserve key order), and the clean-pass
    message. The builder derives the exit code from the same ``failed`` filter it
    projects (design §3.2), so a report whose ``passed`` flag disagrees with its
    findings can no longer emit a self-contradictory envelope.

    Parameters
    ----------
    report : DetectionReport
        The detection result over the scanned chapters.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with empty ``violations`` when clean, or
        ``ExitCode.ACTIONABLE_FINDING`` naming the offending rules.
    """
    return build_finding_outcome(
        report.findings,
        identify=lambda finding: finding.rule_id,
        payload=_finding_payload,
        describe=_finding_message,
        passed=lambda finding: finding.passed,
        clean_message="no slop detected",
        extra_result={"pack": report.pack, "total_words": report.total_words},
    )
