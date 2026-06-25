"""Typed, read-only model and validating loader for a per-novel device ledger.

This package models a *device ledger* — a per-novel TOML file that rations a
novel's signature devices (design §6.3) — as frozen, fully typed Python objects,
and provides the validating boundary that turns a decoded TOML mapping into that
shape. It defines the :class:`DeviceLedger` and :class:`Device` shapes, the
:data:`LEDGER_SCHEMA_VERSION` constant, the two typed failure channels
:class:`LedgerError` (malformed content) and :class:`LedgerFileError` (absent or
undecodable file), and the :func:`parse_ledger` / :func:`load_ledger` boundary
the ``desloppify --ledger`` enforcement (roadmap task 7.1.2) consumes.

The package is a deliberate parallel to :mod:`novel_ralph_skill.rulepack`: it
shares the proven schema→parse→detect→report shape and the
:class:`~novel_ralph_skill.rulepack.detect.ScannedChapter` input type, but carries
its own chapter-aware rationing vocabulary (``max_count``, ``allowed_chapters``,
``retired_after_chapter``, ``reserved_for_chapter``) that the closed v1 rule-pack
schema cannot express, keeping the rule-pack contract frozen (ADR-003).

The loader is read-only and detect-only (ADR-001): it compiles patterns and
validates structure, never judging prose. A malformed ledger fails loudly through
:class:`LedgerError`, naming the offending device; an absent or undecodable ledger
file fails through :class:`LedgerFileError`. The package emits no envelope and
never calls :func:`sys.exit`; exit-code translation is the command body's job.
"""

from __future__ import annotations

from novel_ralph_skill.ledger.errors import LedgerError, LedgerFileError
from novel_ralph_skill.ledger.parse import load_ledger, parse_ledger
from novel_ralph_skill.ledger.schema import (
    LEDGER_SCHEMA_VERSION,
    Device,
    DeviceLedger,
)

__all__ = [
    "LEDGER_SCHEMA_VERSION",
    "Device",
    "DeviceLedger",
    "LedgerError",
    "LedgerFileError",
    "load_ledger",
    "parse_ledger",
]
