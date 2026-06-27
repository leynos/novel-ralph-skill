"""The single home for the envelope-``messages``-carrying exception base.

Every deterministic command emits the shared JSON envelope, whose ``messages``
array carries human-oriented prose the harness never parses (design §3.1;
:doc:`adr-003-shared-interface-contract`). When a command body fails, it reads
``exc.messages`` off the raised exception to populate that array.

This module gives that storage one home. :class:`EnvelopeMessagesError` records
``self.messages`` once, as an immutable ``tuple[str, ...]`` captured at
construction (the freeze-on-construct decision). The domain error types across
the ``contract``, ``rulepack``, ``ledger``, and command layers subclass it
rather than each repeating the same ``__init__`` body, so a future change to the
envelope-messages contract has a single point of change. :class:`BodyUsageError`
is the shared marker the body-detected exit-``2`` faults fan out through (see
:func:`~novel_ralph_skill.contract.runner.usage_error_outcome`). The module
imports nothing from the package, so every other layer may depend on it without
inviting an import cycle.
"""

from __future__ import annotations


class EnvelopeMessagesError(Exception):
    """A domain error carrying human prose for the envelope's ``messages``.

    The base records its varargs prose once, so the domain error types across the
    ``contract``, ``rulepack``, ``ledger``, and command layers that subclass it —
    among them :class:`~novel_ralph_skill.contract.runner.StateInputError`,
    :class:`BodyUsageError` (and its command leaves), and the ``rulepack`` and
    ``ledger`` content/file faults — share one storage site for the envelope's
    ``messages`` (design §3.1; ADR-003). The body-detected usage faults route the
    exit-``2`` envelope they build through
    :func:`~novel_ralph_skill.contract.runner.usage_error_outcome`.
    """

    def __init__(self, *messages: str) -> None:
        """Record the human-prose messages once, for the error envelope.

        Parameters
        ----------
        *messages : str
            Human-oriented notes describing the fault, captured verbatim as an
            immutable tuple for the envelope the command body will build.
        """
        super().__init__(*messages)
        self.messages: tuple[str, ...] = messages


class BodyUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit ``2`` (design §3.2).

    The shared marker base for a usage fault a command *body* detects after the
    Cyclopts parser has accepted the invocation — the parser cannot catch it, so
    it never reaches the runner's ``CycloptsError`` arm. Each command module
    keeps a thin domain subclass naming its own trigger (a no-flag ``set-gate``,
    a ``--chapter`` outside the manifest), but the exit-``2`` envelope every such
    fault produces is built once by
    :func:`~novel_ralph_skill.contract.runner.usage_error_outcome`. The optional
    ``messages`` payload is recorded once by :class:`EnvelopeMessagesError`.
    """
