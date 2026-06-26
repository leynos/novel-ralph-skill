"""Guard the deflation-compensation mechanism in ``SKILL.md``.

Beta testing (roadmap 6.1.2) exposed that the drafting-plus-desloppify loop is
net-deflationary: the desloppify pass removes 10-20% of a chapter
(``skill/novel-ralph/references/desloppify-checklist.md``) and the spiteful
critic cuts further, so a finished novel lands short of its target. The fix is
an explicit expand-to-target step woven into the Phase 8 per-chapter loop and
the Phase 9 final pass, driven by the figures ``wordcount`` already reports
(design §4.5 and §7.2, ``docs/novel-ralph-harness-design.md``).

This module pins that mechanism so a future edit cannot silently remove it. It
reads ``SKILL.md`` in process through the shared ``read_repo_text`` fixture
(``tests/conftest.py``) — no subprocess, no import of ``novel_ralph_skill`` —
mirroring the prose-guard pattern in ``tests/test_state_layout_reference.py``.
The file text is sliced into the Phase 8 and Phase 9 regions by heading offsets,
then small, stable *mechanism* substrings (not whole sentences) are asserted
within each region, per the brittleness mitigation in the ExecPlan's Risks.

The guard deliberately checks only that the mechanism is *present* and recorded.
It cannot detect a wrong **insertion point** (for example, the Phase 8 expand
step placed after the fangirl pass instead of before desloppify) or a wrong
**Phase 9 ordering** (expansion following a destructive pass). Those are
load-bearing prose-correctness properties verified by human review (the
ExecPlan's Stage D), not by a substring scan.
"""

from __future__ import annotations

import typing as typ

import pytest

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

_SKILL_PARTS = ("skill", "novel-ralph", "SKILL.md")

_PHASE_8_HEADING = "### Phase 8"
_PHASE_9_HEADING = "### Phase 9"


def _slice_between(text: str, start_marker: str, end_marker: str) -> str:
    """Return the text between ``start_marker`` and ``end_marker``.

    Pure string slicing over the file text. ``start_marker`` must appear before
    ``end_marker``; the returned slice runs from the start of ``start_marker``
    up to (but excluding) ``end_marker``. Both markers must be present, so a
    renamed or removed heading fails loudly rather than yielding an empty
    region that silently passes the substring assertions.
    """
    start = text.find(start_marker)
    assert start != -1, f"marker {start_marker!r} not found in SKILL.md"
    end = text.find(end_marker, start + len(start_marker))
    assert end != -1, (
        f"marker {end_marker!r} not found after {start_marker!r} in SKILL.md"
    )
    return text[start:end]


@pytest.fixture
def skill_text(read_repo_text: RepoTextReader) -> str:
    """Return the UTF-8 text of ``skill/novel-ralph/SKILL.md``."""
    return read_repo_text(*_SKILL_PARTS)


@pytest.fixture
def phase_8_region(skill_text: str) -> str:
    """Return the Phase 8 region, between its heading and the Phase 9 heading."""
    return _slice_between(skill_text, _PHASE_8_HEADING, _PHASE_9_HEADING).lower()


@pytest.fixture
def phase_9_region(skill_text: str) -> str:
    """Return the Phase 9 region, from its heading to the next H2 or EOF.

    Phase 9 is the last numbered phase, so it may be the final section. The
    region therefore runs to the next level-two heading when one follows, and
    otherwise to end-of-file, rather than asserting a trailing heading exists.
    """
    start = skill_text.find(_PHASE_9_HEADING)
    assert start != -1, f"marker {_PHASE_9_HEADING!r} not found in SKILL.md"
    end = skill_text.find("\n## ", start + len(_PHASE_9_HEADING))
    region = skill_text[start:] if end == -1 else skill_text[start:end]
    return region.lower()


class TestDeflationGuard:
    """Pin the presence of the expand-to-target deflation-compensation step."""

    def test_skill_names_the_expand_to_target_mechanism(
        self,
        skill_text: str,
    ) -> None:
        """``SKILL.md`` names the expand-to-target mechanism by name.

        The roadmap success criterion is an explicit deflation-compensation
        mechanism; the chosen mechanism is the expand-to-target step (not target
        inflation), so its name must appear somewhere in the file.
        """
        haystack = skill_text.lower()
        assert "expand to target" in haystack or "expand-to-target" in haystack, (
            "SKILL.md must name the expand-to-target step (roadmap 6.1.2)"
        )

    def test_phase_8_expand_step_reads_wordcount(
        self,
        phase_8_region: str,
    ) -> None:
        """The Phase 8 expand step reads ``wordcount`` for its target delta."""
        assert "expand to target" in phase_8_region or (
            "expand-to-target" in phase_8_region
        ), "the Phase 8 loop must carry an expand-to-target step (roadmap 6.1.2)"
        assert "wordcount" in phase_8_region, (
            "the Phase 8 expand step must read the delta from wordcount (ADR-001)"
        )

    def test_phase_8_re_measures_with_wordcount(
        self,
        phase_8_region: str,
    ) -> None:
        """The Phase 8 region re-measures, not just measures.

        ``wordcount`` must appear at least twice in the region — once to read the
        delta and once to confirm the band closed after the destructive passes
        cut — so a step that reads the delta but never confirms closure cannot
        pass. The guard cannot prove the re-measure is positioned correctly
        (human review, ExecPlan Stage D); it only forbids the trivially
        incomplete "read delta, expand, done".
        """
        assert phase_8_region.count("wordcount") >= 2, (
            "the Phase 8 expand step must re-invoke wordcount to confirm the "
            "band closed (measure then re-measure)"
        )

    def test_phase_9_expand_step_reads_wordcount(
        self,
        phase_9_region: str,
    ) -> None:
        """The Phase 9 final pass names ``wordcount`` in its expand step."""
        assert "expand to target" in phase_9_region or (
            "expand-to-target" in phase_9_region
        ), "the Phase 9 final pass must carry an expand-to-target step"
        assert "wordcount" in phase_9_region, (
            "the Phase 9 expand step must read the cumulative total from "
            "wordcount (ADR-001)"
        )

    def test_rationale_is_recorded(
        self,
        skill_text: str,
    ) -> None:
        """The rationale for the step is recorded near it.

        The roadmap requires the rationale recorded: the prose must reference the
        deflation it compensates for and the target it expands toward.
        """
        haystack = skill_text.lower()
        assert "deflation" in haystack or "deflationary" in haystack, (
            "SKILL.md must record why the expand step exists (the "
            "net-deflationary drafting-plus-desloppify loop)"
        )
        assert "target" in haystack, (
            "the rationale must reference the (unchanged) target the step "
            "expands the draft toward"
        )
