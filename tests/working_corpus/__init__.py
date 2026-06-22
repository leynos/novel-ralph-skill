"""On-disk ``working/`` fixture corpus package for the test suite.

This package is the corpus data and builder for roadmap task 1.3.2. Its public
surface (re-exported here) is the specification dataclasses, the tree builder,
the compile helper and its constants, and — added in later work items — the
named specification library, the incoherent variants, the ``done.flag``
permutations, and the corpus-local structural oracle.

``tests/conftest.py`` is the single runtime importer of this package: it
re-exposes every datum as a pytest fixture so test modules consume the corpus by
fixture parameter name and never by a runtime value import (the developers-guide
"Shared test scaffolding" rule). The spec *types* are re-exported from
``conftest`` under its ``TYPE_CHECKING`` guard so a test annotation uses the
sanctioned ``from conftest import WorkingTreeSpec`` carve-out.

The corpus is anchored to the design's authoritative artefacts rather than to
any not-yet-existent schema type: ``docs/novel-ralph-harness-design.md`` §5.1
(schema and phase enum) and §5.2 (invariants), and
``skill/novel-ralph/references/state-layout.md`` (the authoritative on-disk
layout). The typed schema (roadmap task 2.1.1) and the §5.2 validator (task
2.1.2) consume this corpus; this package invents neither.
"""

from __future__ import annotations

from ._builder import build_working_tree
from ._library import COHERENT_BASELINE, PHASE_ORDER, PHASE_STATES
from ._oracle import CORPUS_INVARIANT_NAMES, corpus_check
from ._specs import (
    COMPILED_AUTO,
    CORPUS_SEPARATOR,
    GATE_THRESHOLDS,
    ChapterSpec,
    WorkingTreeSpec,
    by_chapter_key,
    chapter_dir_name,
    concatenate_drafts,
    derive_by_chapter,
    draft_body,
)
from ._variants import DONE_FLAG_PERMUTATIONS, INCOHERENT_VARIANTS

__all__ = [
    "COHERENT_BASELINE",
    "COMPILED_AUTO",
    "CORPUS_INVARIANT_NAMES",
    "CORPUS_SEPARATOR",
    "DONE_FLAG_PERMUTATIONS",
    "GATE_THRESHOLDS",
    "INCOHERENT_VARIANTS",
    "PHASE_ORDER",
    "PHASE_STATES",
    "ChapterSpec",
    "WorkingTreeSpec",
    "build_working_tree",
    "by_chapter_key",
    "chapter_dir_name",
    "concatenate_drafts",
    "corpus_check",
    "derive_by_chapter",
    "draft_body",
]
