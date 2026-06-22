"""Typed, read-only model and validating loader for a versioned rule pack.

This package models a *rule pack* — a versioned TOML file of prose-detection
rules (design §6.1) — as frozen, fully typed Python objects, and provides the
validating boundary that turns a decoded TOML mapping into that shape. It
defines the :class:`RulePack`, :class:`Rule`, and :class:`RuleBasis` shapes, the
:data:`RULEPACK_SCHEMA_VERSION` constant, the two typed failure channels
:class:`RulePackError` (malformed content) and :class:`RulePackFileError`
(absent or undecodable file), and the :func:`parse_rulepack` /
:func:`load_rulepack` boundary the ``desloppify`` slop detector (roadmap task
5.1.2) consumes.

The loader is read-only and detect-only (ADR-001): it compiles patterns and
validates structure, never judging prose. A malformed pack fails loudly through
:class:`RulePackError`, naming the offending rule; an absent or undecodable pack
file fails through :class:`RulePackFileError`. The package emits no envelope and
never calls :func:`sys.exit`; exit-code translation is the command body's job.
"""

from __future__ import annotations

from novel_ralph_skill.rulepack.errors import RulePackError, RulePackFileError
from novel_ralph_skill.rulepack.parse import load_rulepack, parse_rulepack
from novel_ralph_skill.rulepack.schema import (
    RULEPACK_SCHEMA_VERSION,
    Rule,
    RuleBasis,
    RulePack,
)

__all__ = [
    "RULEPACK_SCHEMA_VERSION",
    "Rule",
    "RuleBasis",
    "RulePack",
    "RulePackError",
    "RulePackFileError",
    "load_rulepack",
    "parse_rulepack",
]
