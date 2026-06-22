"""The disambiguated exit-code vocabulary shared by every command.

These codes are the contract's load-bearing exit space (design 3.2, ADR 003
Table 2). Because :class:`ExitCode` subclasses :class:`int`, a member's value is
the process exit code directly, so ``sys.exit(ExitCode.SUCCESS)`` exits ``0``.
The split between :data:`ExitCode.BENIGN_NEGATIVE` (``1``) and
:data:`ExitCode.ACTIONABLE_FINDING` (``4``) is the contract's load-bearing
distinction: ``1`` is the steady-state "not finished yet" the harness loops on,
while ``4`` signals a finding only the agent can adjudicate or repair.
"""

from __future__ import annotations

import enum


class ExitCode(enum.IntEnum):
    """A command's process exit code, carrying its design 3.2 meaning."""

    SUCCESS = 0
    """Success; a checker is satisfied or a mutator applied. The harness proceeds."""

    BENIGN_NEGATIVE = 1
    """Benign negative; a predicate is not yet satisfied. The harness loops on."""

    USAGE_ERROR = 2
    """Usage error; the invocation is wrong (unknown subcommand, bad arguments)."""

    STATE_ERROR = 3
    """State or input error; ``state.toml`` is missing/unparseable, or the working
    directory is absent. The harness stops and recovers state."""

    ACTIONABLE_FINDING = 4
    """Actionable finding a deterministic detector surfaced; the agent adjudicates
    or repairs, then re-runs."""


def is_ok(code: ExitCode) -> bool:
    """Return whether ``code`` is the success code.

    This is the single home of the ``ok`` / exit-code biconditional: ``ok`` is
    ``True`` if and only if the exit code is :data:`ExitCode.SUCCESS` (ADR 003
    "Technical requirements").

    Parameters
    ----------
    code : ExitCode
        The exit code to classify.

    Returns
    -------
    bool
        ``True`` if and only if ``code`` is :data:`ExitCode.SUCCESS`.
    """
    return code is ExitCode.SUCCESS
