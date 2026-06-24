"""Shared baseline anchor and helpers for the corpus variant builders.

The incoherent-variant builders span two modules — the general §5.2/§5.4 set in
:mod:`._variants` and the roadmap-2.3.2 reconciliation set in
:mod:`._reconcile_variants` — so each stays within the 400-line module cap
(AGENTS.md lines 24-27). Both anchor every variant to ``COHERENT_BASELINE`` and
build it through the same honest-gate helper, so this module owns that one anchor
and the two helpers, and both variant modules import them from here rather than
duplicating them (the deliberate single source of truth).
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

from ._library import COHERENT_BASELINE
from ._specs import GATE_THRESHOLDS

if typ.TYPE_CHECKING:
    from ._specs import ChapterSpec, WorkingTreeSpec

# The canonical mid-drafting coherent tree every incoherent variant mutates, and
# its chapter tuple, named once here so the two variant modules share one anchor.
BASE = COHERENT_BASELINE
BASE_CHAPTERS = BASE.chapters


def consistent_gates(chapters: tuple[ChapterSpec, ...]) -> dict[str, bool]:
    """Return knitting-gate booleans honestly crossed by ``chapters`` drafts."""
    ratio = sum(chapter.draft_words for chapter in chapters) / BASE.target_words
    low, mid, high = GATE_THRESHOLDS
    return {
        "done_30": ratio >= low,
        "done_50": ratio >= mid,
        "done_80": ratio >= high,
    }


def with_chapters(
    chapters: tuple[ChapterSpec, ...], **changes: object
) -> WorkingTreeSpec:
    """Return the baseline with replaced chapters, honest gates, and ``changes``.

    Explicit gate booleans in ``changes`` override the honest defaults, so a
    gate-inconsistency variant can deliberately set a gate against the ratio.
    """
    fields: dict[str, object] = {"chapters": chapters, **consistent_gates(chapters)}
    fields.update(changes)
    return dc.replace(BASE, **fields)
