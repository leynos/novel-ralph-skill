"""Unit tests for the ``init`` initial-state builder (roadmap 2.2.2).

These pin :func:`novel_ralph_skill.state.build_initial_document` directly,
without the CLI: the document it builds carries the **full** required table set
the strict ``parse_state`` boundary reads by subscription, so a freshly
initialised tree parses cleanly and validates coherent (design §5.1, §5.2;
ExecPlan Decision Log D5, Risk "init builds an unreadable document"). The
success-then-fields ordering is the B1 prevention — the parse must *succeed*
before any field assertion runs, so a missing table surfaces as the failure
rather than being masked by a later assertion. The ``created_at`` timestamp is
excluded from the equality assertions (advisory A2); only the structural fields
are pinned.
"""

from __future__ import annotations

import novel_ralph_skill.state as state_pkg
from novel_ralph_skill.state import (
    Phase,
    build_initial_document,
    parse_state,
    validate_state,
)

_CREATED_AT = "2026-06-23T00:00:00Z"


def test_build_initial_document_is_in_public_surface() -> None:
    """``build_initial_document`` is re-exported and named in ``__all__``."""
    assert "build_initial_document" in state_pkg.__all__
    assert state_pkg.build_initial_document is build_initial_document


def test_initial_document_parses_then_carries_initial_fields() -> None:
    """The initial document parses, then names ``premise`` and the target."""
    # Parse FIRST: a missing required table raises here, before any field
    # assertion can mask it (B1 prevention).
    state = parse_state(
        build_initial_document(
            title="T",
            slug="s",
            target_word_count=80000,
            created_at=_CREATED_AT,
        )
    )
    assert state.phase.current == Phase.PREMISE
    assert state.phase.completed == ()
    assert state.chapters == ()
    assert state.word_counts.target == 80000
    assert state.word_counts.current == 0
    assert state.word_counts.by_chapter == {}


def test_initial_state_is_coherent() -> None:
    """The initial state satisfies every §5.2 invariant (empty verdict)."""
    state = parse_state(
        build_initial_document(
            title="T",
            slug="s",
            target_word_count=80000,
            created_at=_CREATED_AT,
        )
    )
    assert not validate_state(state)


def test_initial_document_stores_title_slug_verbatim() -> None:
    """``title`` and ``slug`` are stored exactly as supplied (opaque strings)."""
    state = parse_state(
        build_initial_document(
            title="The Lantern Keeper",
            slug="the-lantern-keeper",
            target_word_count=120000,
            created_at=_CREATED_AT,
        )
    )
    assert state.novel.title == "The Lantern Keeper"
    assert state.novel.slug == "the-lantern-keeper"
    assert state.novel.target_word_count == 120000
