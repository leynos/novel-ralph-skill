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

The guard checks both that the mechanism is *present* and recorded and that the
load-bearing *ordering* holds. Addendum 6.1.2.1 mechanises the ordinal property
that earlier relied on human review: in the Phase 8 region the re-measurement
``wordcount`` must fall after the desloppify step, and in the Phase 9 region the
expand step must sit after the structural-only critic and before
``complete-final-pass``, so no destructive pass can follow expansion. The guard
still cannot judge prose quality or confirm the expanded material is substantive
rather than padding; those remain human-review concerns (the ExecPlan's Stage D).
"""

from __future__ import annotations

import typing as typ

import pytest

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

_SKILL_PARTS = ("skill", "novel-ralph", "SKILL.md")

_PHASE_8_HEADING = "### Phase 8"
_PHASE_9_HEADING = "### Phase 9"

# Ordering anchors (lowercased, matching the region fixtures). The Phase 8
# re-measure must fall after the desloppify step heading; the Phase 9 expand
# step must sit after the structural critic and before complete-final-pass.
_PHASE_8_DESLOPPIFY_STEP = "e. desloppify"
_PHASE_9_STRUCTURAL_CRITIC = "structural issues invisible"
_PHASE_9_FINAL_VERB = "complete-final-pass"


def _require_index(haystack: str, needle: str, *, context: str) -> int:
    """Return the offset of ``needle`` in ``haystack`` or fail loudly.

    ``str.find`` returns ``-1`` when absent, which would silently corrupt an
    ordinal comparison; this raises an assertion naming the missing anchor
    instead so a renamed step heading fails with a clear message.
    """
    index = haystack.find(needle)
    assert index != -1, f"ordering anchor {needle!r} missing from {context}"
    return index


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

    def test_phase_8_pins_the_over_expansion_headroom(
        self,
        phase_8_region: str,
    ) -> None:
        """The Phase 8 region budgets the destructive cut as deliberate headroom.

        Without this the guard would pass even with the convergence defect
        fix-round-1 corrected: a pre-cut draft expanded only to the band lands
        short once desloppify and the critic trim it. The mechanism is to
        over-expand the pre-cut draft above the chapter target by the expected
        loss, so the chapter lands within the band after the cuts. Pin both the
        over-expand cue and the headroom cue, which together encode that
        budgeting property.
        """
        assert "over-expand" in phase_8_region, (
            "the Phase 8 expand step must over-expand the pre-cut draft to "
            "budget the desloppify-plus-critic cut, not expand only to the band"
        )
        assert "headroom" in phase_8_region, (
            "the Phase 8 expand step must frame the over-expansion as deliberate "
            "headroom for the destructive passes"
        )

    def test_phase_8_re_measure_follows_desloppify(
        self,
        phase_8_region: str,
    ) -> None:
        """The Phase 8 re-measure ``wordcount`` falls after desloppify.

        The expand step measures before the destructive passes and re-measures
        after them, so the final ``wordcount`` mention in the loop must sit
        after the desloppify step heading. A refactor that moved the re-measure
        ahead of desloppify — confirming the band before the cuts — would defeat
        the over-expansion design and is caught here, not left to human review.
        """
        desloppify_at = _require_index(
            phase_8_region,
            _PHASE_8_DESLOPPIFY_STEP,
            context="the Phase 8 region",
        )
        last_wordcount_at = phase_8_region.rfind("wordcount")
        assert last_wordcount_at != -1, "wordcount missing from the Phase 8 region"
        assert last_wordcount_at > desloppify_at, (
            "the Phase 8 re-measurement wordcount must follow the desloppify "
            "step (measure, cut, then re-measure)"
        )

    def test_phase_9_expand_sits_after_critic_and_before_final_verb(
        self,
        phase_9_region: str,
    ) -> None:
        """The Phase 9 expand step is bracketed by the critic and the final verb.

        Expansion must run after the structural-only critic and before
        ``complete-final-pass`` so no destructive pass follows it to re-open the
        gap. This ordinal check mechanises the Phase 9 ordering the substring
        guard alone could not prove.
        """
        critic_at = _require_index(
            phase_9_region,
            _PHASE_9_STRUCTURAL_CRITIC,
            context="the Phase 9 region",
        )
        final_verb_at = _require_index(
            phase_9_region,
            _PHASE_9_FINAL_VERB,
            context="the Phase 9 region",
        )
        expand_at = phase_9_region.find("expand to target")
        if expand_at == -1:
            expand_at = phase_9_region.find("expand-to-target")
        assert expand_at != -1, "expand-to-target step missing from the Phase 9 region"
        assert critic_at < expand_at < final_verb_at, (
            "the Phase 9 expand step must sit after the structural-only critic "
            "and before complete-final-pass (no destructive pass after it)"
        )
