"""The single home for the envelope-``messages``-carrying exception base.

Every deterministic command emits the shared JSON envelope, whose ``messages``
array carries human-oriented prose the harness never parses (design §3.1;
:doc:`adr-003-shared-interface-contract`). When a command body fails, it reads
``exc.messages`` off the raised exception to populate that array.

This module gives that storage one home. :class:`EnvelopeMessagesError` records
``self.messages`` once, as an immutable ``tuple[str, ...]`` captured at
construction (the freeze-on-construct decision). The domain error types across
the ``contract`` and ``rulepack`` layers subclass it rather than each repeating
the same ``__init__`` body, so a future change to the envelope-messages contract
has a single point of change. The module imports nothing from the package, so
``rulepack`` may depend on it without inviting an import cycle.
"""

from __future__ import annotations


class EnvelopeMessagesError(Exception):
    """A domain error carrying human prose for the envelope's ``messages``.

    The base records its varargs prose once, so the three domain exceptions that
    subclass it (:class:`~novel_ralph_skill.contract.runner.StateInputError`,
    :class:`~novel_ralph_skill.rulepack.errors.RulePackError`, and
    :class:`~novel_ralph_skill.rulepack.errors.RulePackFileError`) share one
    storage site for the envelope's ``messages`` (design §3.1; ADR-003).
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
