"""The two typed failure channels of the rule-pack loader (design §10).

A rule pack can fail to load in two distinct ways, and the design splits them
onto two exit codes (design §4.4, §10). This module gives each its own typed
exception so the ``desloppify`` command (roadmap task 5.1.2) maps each to the
right :class:`~novel_ralph_skill.contract.exit_codes.ExitCode` without re-parsing
a message:

- :class:`RulePackError` — the pack *content* is malformed (a bad
  ``schema_version``, a missing or wrong-typed field, an unknown ``basis``, a
  non-positive ``page_words``, a negative ``threshold``, or an uncompilable
  ``pattern``). The command maps this to ``ExitCode.USAGE_ERROR`` (exit 2),
  naming the offending rule.
- :class:`RulePackFileError` — the pack *file* is absent, unreadable, or holds
  undecodable TOML. The command maps this to ``ExitCode.STATE_ERROR`` (exit 3).

Both mirror ``StateInputError`` in
:mod:`novel_ralph_skill.contract.runner`: they store human-prose ``messages`` on
the instance for the envelope the command will build. The loader itself never
calls :func:`sys.exit` and emits no envelope; exit-code translation is the
command body's job.
"""

from __future__ import annotations


class RulePackError(Exception):
    """Malformed rule-pack *content*: the command maps this to exit 2.

    Raised by the loader when a decoded rule pack violates the v1 schema — a bad
    ``schema_version``, a missing or wrong-typed field, an unknown ``basis``, a
    non-positive ``page_words``, a negative ``threshold``, or a ``pattern`` that
    will not compile. ``rule_id`` names the offending rule for a per-rule fault,
    or is ``None`` for a pack-level fault (such as a bad ``schema_version`` or a
    missing ``pack`` key).
    """

    def __init__(self, *messages: str, rule_id: str | None = None) -> None:
        """Record the offending rule and the human-prose messages.

        Parameters
        ----------
        *messages : str
            Human-oriented notes describing the content fault, for the envelope
            the ``desloppify`` command (task 5.1.2) will build.
        rule_id : str | None
            The ``id`` of the offending rule, or ``None`` for a pack-level fault
            that names no single rule.
        """
        super().__init__(*messages)
        self.messages: tuple[str, ...] = messages
        self.rule_id: str | None = rule_id


class RulePackFileError(Exception):
    """An absent, unreadable, or undecodable pack file: maps to exit 3.

    Raised by :func:`~novel_ralph_skill.rulepack.parse.load_rulepack` when the
    pack file is missing, cannot be read, or holds TOML that ``tomllib`` cannot
    decode. A decode fault is an input fault (exit 3), kept distinct from a
    *structurally valid* TOML that violates the schema (which is
    :class:`RulePackError`, exit 2).
    """

    def __init__(self, *messages: str) -> None:
        """Record the human-prose messages for the state-error envelope.

        Parameters
        ----------
        *messages : str
            Human-oriented notes describing the file or decode fault.
        """
        super().__init__(*messages)
        self.messages: tuple[str, ...] = messages
