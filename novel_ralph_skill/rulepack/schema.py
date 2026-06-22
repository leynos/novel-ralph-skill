"""Frozen, typed dataclasses for a versioned rule pack (design §6.1).

A *rule pack* is a versioned TOML file of prose-detection rules. Each rule names
a regular-expression ``pattern``, a ``threshold`` (the allowed number of hits),
and a counting ``basis`` (how the hits are tallied), so the deterministic slop
detector ``desloppify`` (roadmap task 5.1.2) can report uniform per-hit
structured output without baking the rules into code (design §4.4 and §6.1).

This module carries the *shapes* only: the closed :class:`RuleBasis` set, the
per-rule :class:`Rule`, and the whole :class:`RulePack`. It performs no parsing
and no validation; the validating boundary constructor that builds these from a
decoded TOML mapping lives in :mod:`novel_ralph_skill.rulepack.parse`, mirroring
how ``novel_ralph_skill/state/schema.py`` carries shapes while
``novel_ralph_skill/state/parse.py`` constructs them.

The objects follow the frozen, slotted, keyword-only house style of
``novel_ralph_skill/contract/envelope.py`` and
``novel_ralph_skill/state/schema.py``.
"""

from __future__ import annotations

import dataclasses
import enum
import typing as typ

if typ.TYPE_CHECKING:
    import re


RULEPACK_SCHEMA_VERSION: int = 1
"""The current rule-pack schema version (design §6.1).

This version is independent of the envelope's and ``state.toml``'s
``schema_version`` numbers (design §3.1): a rule pack carries its own version, so
the rule vocabulary can evolve without forcing an envelope or state bump. The
loader validates this value rather than silently coercing it.
"""


class RuleBasis(enum.StrEnum):
    """The closed set of hit-counting bases a rule may use (design §6.1).

    A :class:`enum.StrEnum`, so a member *is* its TOML string value:
    ``RuleBasis.PER_PAGE == "per_page"`` and
    ``RuleBasis("per_page") is RuleBasis.PER_PAGE``. The set is closed so a typo
    in a pack's ``basis`` field fails loudly at load time rather than silently
    disabling the rule (ExecPlan Decision Log "basis is a closed set").
    """

    MANUSCRIPT = "manuscript"
    """Count hits across the whole manuscript against a single ``threshold``."""

    PER_PAGE = "per_page"
    """Count hits per notional page of ``page_words`` words against ``threshold``."""


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Rule:
    """One prose-detection rule of a rule pack (design §6.1).

    Attributes
    ----------
    id : str
        The rule's stable identifier, named in any structured output and in any
        loader error that flags this rule.
    pattern : str
        The regular-expression source, kept verbatim for reporting so the
        emitted finding can echo the authored pattern.
    compiled : re.Pattern[str]
        The compiled form of :attr:`pattern`, compiled once at load time so the
        detection logic (task 5.1.2) never recompiles per match.
    threshold : int
        The allowed number of hits; a non-negative integer. ``0`` is zero
        tolerance.
    basis : RuleBasis
        How hits are tallied: across the whole manuscript or per notional page.
    page_words : int | None
        The notional page size in words, a positive integer when
        :attr:`basis` is :attr:`RuleBasis.PER_PAGE`, and ``None`` otherwise.
    """

    id: str
    pattern: str
    compiled: re.Pattern[str]
    threshold: int
    basis: RuleBasis
    page_words: int | None


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class RulePack:
    """A whole versioned rule pack (design §6.1).

    Attributes
    ----------
    schema_version : int
        The rule-pack schema version (currently
        :data:`RULEPACK_SCHEMA_VERSION`), independent of the envelope and state
        versions (design §3.1).
    pack : str
        The pack's name (for example ``"ai-isms"``), echoed in reporting.
    rules : tuple[Rule, ...]
        The rules in authoring order. The tuple is already immutable, so no
        further freezing is needed.
    """

    schema_version: int
    pack: str
    rules: tuple[Rule, ...]
