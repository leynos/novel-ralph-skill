"""Typed, read-only model of ``state.toml`` and the lifecycle phase enum.

This package wraps the harness's primary on-disk memory (``state.toml``;
design §5.1, ``skill/novel-ralph/references/state-layout.md``) as frozen,
fully typed Python objects, plus the closed :class:`Phase` enum that orders the
novel's lifecycle. It is the *shape* the §5.2 validator (roadmap task 2.1.2) and
the ``tomlkit`` round-trip helper (task 2.2.1) consume.

The package is read-only: it parses and models ``state.toml`` but performs no
writing, no ``tomlkit`` mutation, no CLI, and no invariant validation. Writing
is task 2.2.1; validation is task 2.1.2; the CLI is task 2.2.2.
"""

from __future__ import annotations

from novel_ralph_skill.state.parse import load_state, parse_state
from novel_ralph_skill.state.phase import PHASE_ORDER, Phase
from novel_ralph_skill.state.schema import (
    ChapterEntry,
    CriticState,
    Drafting,
    FangirlState,
    FinalGate,
    FindingCounts,
    Gates,
    KnittingGates,
    NovelMeta,
    PendingTurn,
    PhaseState,
    State,
    WordCounts,
)

__all__ = [
    "PHASE_ORDER",
    "ChapterEntry",
    "CriticState",
    "Drafting",
    "FangirlState",
    "FinalGate",
    "FindingCounts",
    "Gates",
    "KnittingGates",
    "NovelMeta",
    "PendingTurn",
    "Phase",
    "PhaseState",
    "State",
    "WordCounts",
    "load_state",
    "parse_state",
]
