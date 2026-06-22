"""The shared interface contract: JSON envelope, exit codes, and output modes.

This package is the one contract every deterministic command shares (ADR 003,
design 3.1 and 3.2): a machine-mode JSON envelope on stdout, a ``--human``
rendering switch, and the disambiguated exit-code table. It is built once here
(roadmap task 1.3.1) and reused by every command slice rather than each
re-inventing an output shape.

The public surface re-exported here is :class:`Envelope`, :func:`build_envelope`,
:func:`render_machine`, :func:`render_human`, :data:`ENVELOPE_SCHEMA_VERSION`,
:class:`ExitCode`, :func:`is_ok`, :class:`CommandOutcome`, :class:`RunContext`,
:class:`StateInputError`, and :func:`run`.
"""

from __future__ import annotations

from novel_ralph_skill.contract.envelope import (
    ENVELOPE_SCHEMA_VERSION,
    Envelope,
    build_envelope,
    render_human,
    render_machine,
)
from novel_ralph_skill.contract.exit_codes import ExitCode, is_ok
from novel_ralph_skill.contract.runner import (
    CommandOutcome,
    RunContext,
    StateInputError,
    run,
)

__all__ = [
    "ENVELOPE_SCHEMA_VERSION",
    "CommandOutcome",
    "Envelope",
    "ExitCode",
    "RunContext",
    "StateInputError",
    "build_envelope",
    "is_ok",
    "render_human",
    "render_machine",
    "run",
]
