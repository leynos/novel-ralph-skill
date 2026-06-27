"""Typed, read-only model of ``state.toml`` and the lifecycle phase enum.

This package wraps the harness's primary on-disk memory (``state.toml``;
design §5.1, ``skill/novel-ralph/references/state-layout.md``) as frozen,
fully typed Python objects, plus the closed :class:`Phase` enum that orders the
novel's lifecycle. It is the *shape* the §5.2 validator (roadmap task 2.1.2) and
the ``tomlkit`` round-trip helper (task 2.2.1) consume.

The schema, phase enum, and parser are read-only: they model and parse
``state.toml`` but perform no CLI and no invariant validation (validation is
task 2.1.2). The *writer* — the lossless ``tomlkit`` round-trip, the atomic
temp-file-plus-``Path.replace`` write, and the ``[pending_turn]`` intent
bracket — lives in :mod:`novel_ralph_skill.state.document` (task 2.2.1,
delivered) and is re-exported here. The ``init`` initial-state builder
:func:`~novel_ralph_skill.state.initial.build_initial_document` (task 2.2.2,
delivered) is likewise re-exported here; the mutator subcommands that consume it
live in the ``commands`` package.
"""

from __future__ import annotations

from novel_ralph_skill.state._disk_paths import (
    _chapter_dir_name as chapter_dir_name,
)
from novel_ralph_skill.state._disk_word_counts import (
    WORD_COUNTS_COVER_DRAFTS,
    WORD_COUNTS_MATCH_DRAFTS,
    disk_word_counts,
)
from novel_ralph_skill.state.compile_model import (
    COMPILED_REL,
    DRAFT_SEPARATOR,
    CompiledComparison,
    compile_is_current,
    compiled_manuscript_path,
    compiled_matches_drafts,
    concatenate_drafts,
    present_draft_bodies,
)
from novel_ralph_skill.state.disk_evidence import (
    COMPILED_MATCHES_DRAFTS,
    CURSOR_PLAN_PRESENT,
    DISK_EVIDENCE_INVARIANT_NAMES,
    DONE_FLAG_WITHOUT_DRAFT,
    LOG_PRESENT,
    MANIFEST_DISK_BIJECTION,
    PENDING_TURN_CLEARED,
    check_disk_evidence,
)
from novel_ralph_skill.state.document import (
    build_inline_table,
    clear_pending_turn,
    document_to_state,
    load_document,
    open_pending_turn,
    pending_turn,
    write_document_atomically,
    write_text_atomically,
)
from novel_ralph_skill.state.initial import build_initial_document
from novel_ralph_skill.state.parse import load_state, parse_state
from novel_ralph_skill.state.phase import PHASE_ORDER, Phase
from novel_ralph_skill.state.reconcile import (
    ReconcileAction,
    Reconciliation,
    derive_reconciliation,
    reconciliation_payload,
)
from novel_ralph_skill.state.schema import (
    SET_CHAPTERS_OPERATION,
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
    GATE_THRESHOLDS,
    PHASE_IN_ENUM,
    PURE_STATE_INVARIANT_NAMES,
    Violation,
    validate_state,
)
from novel_ralph_skill.state.wordcount import recount_words

__all__ = [
    "BY_CHAPTER_SUM",
    "COMPILED_MATCHES_DRAFTS",
    "COMPILED_REL",
    "COMPLETED_PREFIX",
    "CONSECUTIVE_CLEAN_WITHIN_DRAFTED",
    "CONSECUTIVE_CLEAN_WITHIN_TARGET",
    "CONVERGENCE_TARGET_AT_LEAST_ONE",
    "CURSOR_COHERENT",
    "CURSOR_PLAN_PRESENT",
    "DISK_EVIDENCE_INVARIANT_NAMES",
    "DONE_FLAG_WITHOUT_DRAFT",
    "DRAFT_SEPARATOR",
    "GATE_RATIO_CONSISTENT",
    "GATE_THRESHOLDS",
    "LOG_PRESENT",
    "MANIFEST_DISK_BIJECTION",
    "PENDING_TURN_CLEARED",
    "PHASE_IN_ENUM",
    "PHASE_ORDER",
    "PURE_STATE_INVARIANT_NAMES",
    "SET_CHAPTERS_OPERATION",
    "WORD_COUNTS_COVER_DRAFTS",
    "WORD_COUNTS_MATCH_DRAFTS",
    "ChapterEntry",
    "CompiledComparison",
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
    "ReconcileAction",
    "Reconciliation",
    "State",
    "Violation",
    "WordCounts",
    "build_initial_document",
    "build_inline_table",
    "chapter_dir_name",
    "check_disk_evidence",
    "clear_pending_turn",
    "compile_is_current",
    "compiled_manuscript_path",
    "compiled_matches_drafts",
    "concatenate_drafts",
    "derive_reconciliation",
    "disk_word_counts",
    "document_to_state",
    "load_document",
    "load_state",
    "open_pending_turn",
    "parse_state",
    "pending_turn",
    "present_draft_bodies",
    "reconciliation_payload",
    "recount_words",
    "validate_state",
    "write_document_atomically",
    "write_text_atomically",
]
