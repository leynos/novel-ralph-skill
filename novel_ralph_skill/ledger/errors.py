"""The two typed failure channels of the device-ledger loader (design §10).

A device ledger can fail to load in two distinct ways, and the design splits
them onto two exit codes (design §3.2, §10). This module gives each its own
typed exception so the ``desloppify --ledger`` command (roadmap task 7.1.2) maps
each to the right
:class:`~novel_ralph_skill.contract.exit_codes.ExitCode` without re-parsing a
message, mirroring ``novel_ralph_skill/rulepack/errors.py`` — both now bind the
same shared ``loaderkit.errors`` bases:

- :class:`LedgerError` — the ledger *content* is malformed (a bad
  ``schema_version``, a missing or wrong-typed field, an uncompilable
  ``pattern``, a device with no ration, a device combining two window
  constraints, or a non-positive bound). The command maps this to
  ``ExitCode.USAGE_ERROR`` (exit 2), naming the offending device.
- :class:`LedgerFileError` — the ledger *file* is absent, unreadable, or holds
  undecodable TOML. The command maps this to ``ExitCode.STATE_ERROR`` (exit 3).

Both bind the shared two-class shape from the neutral ``loaderkit`` leaf
(roadmap task 7.2.5): :class:`LedgerError` subclasses
:class:`~novel_ralph_skill.loaderkit.errors.PackError` (the exit-``2`` content
base) and :class:`LedgerFileError` subclasses
:class:`~novel_ralph_skill.loaderkit.errors.PackFileError` (the exit-``3`` file
base). Those bases in turn subclass
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` from the
``contract`` layer (the ``ledger`` → ``loaderkit`` → ``contract`` dependency
direction; design §3.1, §6.3): they store human-prose ``messages`` on the
instance for the envelope the command will build. Binding the shared bases here —
rather than re-spelling the two-class hierarchy — means a third loader family
inherits the primitive instead of cloning a third near-identical pair, mirroring
the coercion binding (roadmap task 7.2.2). The loader itself never calls
:func:`sys.exit` and emits no envelope; exit-code translation is the command
body's job.
"""

from __future__ import annotations

from novel_ralph_skill.loaderkit.errors import PackError, PackFileError


class LedgerError(PackError):
    """Malformed device-ledger *content*: the command maps this to exit 2.

    Raised by the loader when a decoded device ledger violates the v1 schema — a
    bad ``schema_version``, a missing or wrong-typed field, a ``pattern`` that
    will not compile, a device that carries no ration, a device combining two
    window constraints, a non-positive bound, or a duplicated id. ``device_id``
    names the offending device for a per-device fault, or is ``None`` for a
    ledger-level fault (such as a bad ``schema_version`` or an empty ``device``
    array). It binds the shared
    :class:`~novel_ralph_skill.loaderkit.errors.PackError` content base, keeping
    only the ``device_id`` keyword that is public and specific to this family.
    """

    def __init__(self, *messages: str, device_id: str | None = None) -> None:
        """Record the offending device and the human-prose messages.

        Parameters
        ----------
        *messages : str
            Human-oriented notes describing the content fault, for the envelope
            the ``desloppify --ledger`` command (task 7.1.2) will build.
        device_id : str | None
            The ``id`` of the offending device, or ``None`` for a ledger-level
            fault that names no single device.
        """
        super().__init__(*messages)
        self.device_id: str | None = device_id


class LedgerFileError(PackFileError):
    """An absent, unreadable, or undecodable ledger file: maps to exit 3.

    Raised by :func:`~novel_ralph_skill.ledger.parse.load_ledger` when the ledger
    file is missing, cannot be read, or holds TOML that ``tomllib`` cannot
    decode. A decode fault is an input fault (exit 3), kept distinct from a
    *structurally valid* TOML that violates the schema (which is
    :class:`LedgerError`, exit 2). It binds the shared
    :class:`~novel_ralph_skill.loaderkit.errors.PackFileError` base with no extra
    constructor, so it is handed to
    :func:`~novel_ralph_skill.loaderkit.load.load_toml` as its ``file_error=``
    callable; the human-prose ``messages`` are recorded once by the
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` base.
    """
