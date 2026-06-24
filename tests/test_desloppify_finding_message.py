"""Unit tests for ``_finding_message`` prose lines (roadmap addendum 5.1.2.4).

``_finding_message`` (``novel_ralph_skill.commands._desloppify_report``) builds
the one-line human-prose description for an over-threshold rule. It has two
branches keyed on ``finding.density``: a ``per_page`` rule reports its density
against the threshold and page size, while a ``manuscript`` rule reports its raw
count against the threshold. The per-page branch was previously uncovered (audit
5.1.2 Finding 4); both branches are pinned here so the message vocabulary the
``--human`` rendering surfaces cannot regress.
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.commands._desloppify_report import _finding_message
from novel_ralph_skill.rulepack.detect import RuleFinding
from novel_ralph_skill.rulepack.schema import RuleBasis


def _per_page_finding() -> RuleFinding:
    """Build an over-threshold ``per_page`` finding (density 4.50, threshold 3)."""
    return RuleFinding(
        rule_id="em-dash",
        pattern=r"—",
        count=9,
        threshold=3,
        basis=RuleBasis.PER_PAGE,
        page_words=300,
        density=4.5,
        passed=False,
        lines=(),
    )


def _manuscript_finding() -> RuleFinding:
    """Build an over-threshold ``manuscript`` finding (count 7, threshold 2)."""
    return RuleFinding(
        rule_id="load-bearing",
        pattern="load-bearing",
        count=7,
        threshold=2,
        basis=RuleBasis.MANUSCRIPT,
        page_words=None,
        density=None,
        passed=False,
        lines=(),
    )


class TestFindingMessage:
    """Pin both branches of ``_finding_message``.

    The per-page branch (a non-``None`` density) was the one the audit flagged
    as untested; the manuscript branch (a ``None`` density) anchors the contrast
    so neither prose form can regress into the other.
    """

    @pytest.mark.parametrize(
        ("finding", "expected"),
        [
            pytest.param(
                _per_page_finding(),
                "em-dash exceeds threshold (density 4.50 > 3 per 300 words)",
                id="per-page-density-branch",
            ),
            pytest.param(
                _manuscript_finding(),
                "load-bearing exceeds threshold (7 > 2)",
                id="manuscript-count-branch",
            ),
        ],
    )
    def test_message_renders_branch_specific_prose(
        self, finding: RuleFinding, expected: str
    ) -> None:
        """Each finding renders its branch's exact one-line prose."""
        message = _finding_message(finding)
        assert message == expected, (
            f"expected {expected!r} for {finding.basis.value} finding, got {message!r}"
        )
