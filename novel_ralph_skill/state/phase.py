"""The closed, ordered phase enum of the novel's lifecycle.

This is the single home of the eleven lifecycle phases the harness marches
through (design §5.1; ``skill/novel-ralph/references/state-layout.md`` "Phase
enum"). Every later command names a phase through :class:`Phase` rather than a
bare string, so the set is closed and the order is canonical.

``Phase`` is a :class:`enum.StrEnum`, so a member *is* its kebab-case string
value: ``Phase.CONFLICT_ANALYSIS == "conflict-analysis"`` and
``Phase("conflict-analysis") is Phase.CONFLICT_ANALYSIS``. Members are named in
``UPPER_SNAKE`` with the kebab-case value spelled explicitly, so the on-disk
spelling never depends on the member name. The enum is read-only here; the §5.2
invariants over phases (forward-only completion) are enforced by
``novel-state check`` (roadmap task 2.1.2), not by this module.
"""

from __future__ import annotations

import enum


class Phase(enum.StrEnum):
    """The eleven ordered lifecycle phases of the novel (design §5.1)."""

    PREMISE = "premise"
    """Premise capture; the first phase."""

    TREATMENT = "treatment"
    """Treatment of the premise into a narrative shape."""

    CHARACTERS = "characters"
    """Character work: the cast, relationships, and physicalities."""

    CONFLICT_ANALYSIS = "conflict-analysis"
    """Conflict analysis: mapping the story's tensions and pressures."""

    SETTING = "setting"
    """Setting and world-building."""

    READER_FIT = "reader-fit"
    """Reader fit: audience and comparable-title analysis."""

    STC = "stc"
    """Save the Cat beat planning (genre and beat sheet)."""

    CHAPTER_PLANNING = "chapter-planning"
    """Chapter planning: the outline that populates the ``[chapters]`` manifest."""

    DRAFTING = "drafting"
    """Drafting; the phase that contains the inner Ralph loop."""

    # The member name contains "PASS", which trips ruff's hardcoded-password
    # heuristic (S105) on the line below; this is a lifecycle phase value, not a
    # secret, so the inline suppression is intentional.
    FINAL_PASS = "final-pass"  # noqa: S105
    """Final pass over the whole compiled manuscript."""

    DONE = "done"
    """Terminal phase; the novel is complete."""


PHASE_ORDER: tuple[Phase, ...] = tuple(Phase)
"""The canonical phase order as a tuple, mirroring ``list(Phase)``.

Provided for callers that prefer an explicit ordered tuple over iterating the
enum; it is exactly ``tuple(Phase)`` in design §5.1 order
(``premise`` … ``done``).
"""
