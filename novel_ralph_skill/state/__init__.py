"""Typed, read-only model of ``state.toml`` and the lifecycle phase enum.

This package wraps the harness's primary on-disk memory (``state.toml``;
design §5.1, ``skill/novel-ralph/references/state-layout.md``) as frozen,
fully typed Python objects, plus the closed :class:`Phase` enum that orders the
novel's lifecycle. It is the *shape* the §5.2 validator (roadmap task 2.1.2) and
the ``tomlkit`` round-trip helper (task 2.2.1) consume.

The schema, phase enum, and parser are read-only: they model and parse
``state.toml`` but perform no CLI and no invariant validation (validation is
task 2.1.2; the CLI is task 2.2.2). The *writer* — the lossless ``tomlkit``
round-trip, the atomic temp-file-plus-``Path.replace`` write, and the
``[pending_turn]`` intent bracket — lives in
:mod:`novel_ralph_skill.state.document` (task 2.2.1, delivered) and is
re-exported here.
"""

from __future__ import annotations

from novel_ralph_skill.state.document import (
    clear_pending_turn,
    document_to_state,
    load_document,
    open_pending_turn,
    pending_turn,
    write_document_atomically,
)
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
from novel_ralph_skill.state.validate import (
    BY_CHAPTER_SUM,
    COMPLETED_PREFIX,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
    PHASE_IN_ENUM,
    PURE_STATE_INVARIANT_NAMES,
    Violation,
    validate_state,
)

__all__ = [
    "BY_CHAPTER_SUM",
    "COMPLETED_PREFIX",
    "CONSECUTIVE_CLEAN_WITHIN_DRAFTED",
    "CONSECUTIVE_CLEAN_WITHIN_TARGET",
    "CONVERGENCE_TARGET_AT_LEAST_ONE",
    "CURSOR_COHERENT",
    "GATE_RATIO_CONSISTENT",
    "PHASE_IN_ENUM",
    "PHASE_ORDER",
    "PURE_STATE_INVARIANT_NAMES",
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
    "Violation",
    "WordCounts",
    "clear_pending_turn",
    "document_to_state",
    "load_document",
    "load_state",
    "open_pending_turn",
    "parse_state",
    "pending_turn",
    "validate_state",
    "write_document_atomically",
]
