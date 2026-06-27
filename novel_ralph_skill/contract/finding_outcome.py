"""The single finding-outcome envelope skeleton (roadmap task 7.1.4).

The deterministic ``desloppify`` paths — the rule-pack projection
:func:`~novel_ralph_skill.commands._desloppify_report.report_outcome` and the
device-ledger projection
:func:`~novel_ralph_skill.ledger.report.ledger_report_outcome` — share one
envelope *skeleton*: filter a report's findings to the failed ones, derive the
exit code, assemble ``result`` (a ``violations`` slug list plus a slimmed
``findings`` payload list, behind any path-specific extra keys), and assemble
``messages`` as one human-prose line per failed finding or a single clean-pass
note. This module owns that skeleton in one place so the
violations-versus-findings relationship is changed once, not kept in lockstep
across two files by hand.

The builder is generic over an opaque finding type and takes every per-path
detail as an injected callable or value, so it lives in the lowest-layer
``contract`` package without importing ``rulepack`` or ``ledger`` types (no
import cycle; ``contract/errors.py`` records the no-cycle invariant). The per-hit
payload and message projections stay per-path and are injected unchanged; only
the envelope skeleton consolidates here.

The skeleton follows the shared contract (design §3.1, §3.2; ADR-003). Two
contracts are load-bearing:

- *Exit code from the failed filter*: the code derives from the same ``failed``
  list the builder filters (empty → :attr:`ExitCode.SUCCESS`, otherwise
  :attr:`ExitCode.ACTIONABLE_FINDING`),
  **not** from any external ``passed`` flag. For every real detection report the
  cores guarantee ``passed == not failed``, so the observable code is unchanged;
  deriving from ``failed`` closes the latent self-contradictory-envelope path
  (roadmap addendum 8.1.3.2 / its 7.1.3.2 twin) by construction.
- *Result key order*: ``extra_result`` keys are inserted first, in their given
  order, then ``violations``, then ``findings``. ``render_machine``
  (``contract/envelope.py``) serialises ``result`` with ``json.dumps`` and **no**
  ``sort_keys``, so the insertion order is observable in the raw machine JSON
  line; each path's order must be preserved verbatim.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def build_finding_outcome[Finding](  # noqa: PLR0913  # pylint: disable=too-many-arguments
    findings: cabc.Sequence[Finding],
    *,
    identify: cabc.Callable[[Finding], str],
    payload: cabc.Callable[[Finding], cabc.Mapping[str, object]],
    describe: cabc.Callable[[Finding], str],
    passed: cabc.Callable[[Finding], bool],
    clean_message: str,
    extra_result: cabc.Mapping[str, object] | None = None,
) -> CommandOutcome:
    """Assemble the shared finding-outcome :class:`CommandOutcome`.

    Filter ``findings`` to the failed ones, derive the exit code from that
    ``failed`` list, and project the shared envelope skeleton: ``result`` carries
    any ``extra_result`` keys (inserted first, in order), then the ``violations``
    slug list, then the slimmed ``findings`` payload list; ``messages`` carries
    one ``describe`` line per failed finding, or ``clean_message`` when none
    failed.

    Parameters
    ----------
    findings : collections.abc.Sequence
        Every finding the detection core aggregated, of an opaque finding type.
    identify : collections.abc.Callable
        Maps a failed finding to its ``violations`` slug (e.g. ``rule_id`` or
        ``device_id``).
    payload : collections.abc.Callable
        Maps a failed finding to its ``result.findings[]`` mapping. Injected
        unchanged per path; the builder never merges or alters it.
    describe : collections.abc.Callable
        Maps a failed finding to its human-prose ``messages`` line.
    passed : collections.abc.Callable
        Reports whether a finding passed; the negation selects the ``failed``
        filter that feeds ``violations``, ``findings``, the messages, and the
        exit code.
    clean_message : str
        The single ``messages`` line emitted when no finding failed.
    extra_result : collections.abc.Mapping or None, optional
        Path-specific ``result`` keys inserted before ``violations``/``findings``
        in their given order (e.g. ``pack``/``total_words`` for the rule-pack
        path). ``None`` (the default) inserts no extra keys.

    Returns
    -------
    CommandOutcome
        :attr:`~novel_ralph_skill.contract.ExitCode.SUCCESS` with empty
        ``violations``/``findings`` when no finding failed, otherwise
        :attr:`~novel_ralph_skill.contract.ExitCode.ACTIONABLE_FINDING` naming
        the failed findings.
    """
    failed = [finding for finding in findings if not passed(finding)]
    code = ExitCode.SUCCESS if not failed else ExitCode.ACTIONABLE_FINDING
    result: dict[str, object] = dict(extra_result or {})
    result["violations"] = [identify(finding) for finding in failed]
    result["findings"] = [payload(finding) for finding in failed]
    return CommandOutcome(
        code=code,
        result=result,
        messages=[describe(finding) for finding in failed] or [clean_message],
    )
