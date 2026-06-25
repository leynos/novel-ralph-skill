"""The ``desloppify --ledger`` mode sourcing and dispatch (roadmap task 7.1.2).

``desloppify --ledger PATH`` enforces a per-novel device ledger (design §6.3): it
recomputes each rationed device's spend from the chapter drafts on disk and
reports any device over its ration, without editing prose or judging whether a
device *should* have been spent (ADR-001). This module keeps that mode's loading,
sourcing, and fault routing out of the command body
(:mod:`novel_ralph_skill.commands._desloppify`) so that module stays within the
AGENTS.md 400-line cap, mirroring the ``_desloppify``/``_desloppify_report``
split.

The ledger is **whole-manuscript** by design — it rations *across* the book
(``max_count`` totals, chapter-window checks) — so ``--ledger`` cannot be combined
with the single-chapter ``--chapter`` scan; the command body rejects that
combination as an exit-2 usage fault (ExecPlan Decision Log "mutually exclusive
with ``--chapter``"). Here the chapters are always sourced whole
(``source_chapters(None)``), reusing the proven chapter-number attribution the
window checks depend on.

Fault routing follows the contract (design §3.2): a malformed ledger
(:class:`~novel_ralph_skill.ledger.LedgerError`) is a usage error (exit 2), mapped
locally to a :class:`~novel_ralph_skill.contract.runner.CommandOutcome`; an
absent/unreadable/undecodable ledger file
(:class:`~novel_ralph_skill.ledger.LedgerFileError`) is a state/input error (exit
3), re-raised as :class:`~novel_ralph_skill.contract.runner.StateInputError`. The
two ledger errors are caught here rather than in the shared ``run`` wrapper,
keeping the ledger→contract coupling out of the shared seam (mirrors the rulepack
handling in ``_desloppify``).
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.ledger import LedgerError, LedgerFileError, load_ledger
from novel_ralph_skill.ledger.detect import detect_ledger
from novel_ralph_skill.ledger.report import ledger_report_outcome

if typ.TYPE_CHECKING:
    import pathlib


def ledger_scan(ledger_path: pathlib.Path) -> CommandOutcome:
    """Enforce the device ledger at ``ledger_path`` over the whole manuscript.

    Loads the ledger (mapping its two typed faults to exit 2 / 3), sources every
    manifest chapter via ``desloppify``'s shared whole-manuscript sourcing, runs
    the pure chapter-aware detector, and projects the report into the envelope
    outcome. The chapters are always sourced whole (``source_chapters(None)``)
    because the ledger rations across the manuscript; the command body has already
    rejected any ``--ledger`` + ``--chapter`` combination as an exit-2 usage fault
    before this is called.

    Parameters
    ----------
    ledger_path : pathlib.Path
        The ``--ledger PATH`` filesystem path to the per-novel device ledger.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with empty ``violations`` when every device is
        within its ration, ``ExitCode.ACTIONABLE_FINDING`` (exit 4) naming the
        over-ration devices otherwise, or ``ExitCode.USAGE_ERROR`` (exit 2) when
        the ledger content is malformed.

    Raises
    ------
    StateInputError
        When the ledger file or a chapter draft is unreadable, or ``state.toml``
        is missing/unparseable (the exit-3 channel).
    """
    # Imported lazily to avoid a module-import cycle: ``_desloppify`` imports this
    # module for its dispatch, and ``source_chapters`` lives in ``_desloppify``.
    from novel_ralph_skill.commands._desloppify import source_chapters

    try:
        ledger = load_ledger(ledger_path)
    except LedgerError as exc:
        # Malformed ledger *content* is a usage error (exit 2); map it locally to
        # a CommandOutcome rather than coupling the shared runner to the ledger.
        return CommandOutcome(
            code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
        )
    except LedgerFileError as exc:
        # An absent/unreadable/undecodable ledger *file* is the exit-3 state
        # channel, which the shared runner already maps from StateInputError.
        msg = f"cannot read device ledger: {exc}"
        raise StateInputError(msg) from exc
    chapters = source_chapters(None)
    return ledger_report_outcome(detect_ledger(ledger, chapters))
