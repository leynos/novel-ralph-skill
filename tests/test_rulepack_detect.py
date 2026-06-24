"""Unit tests for the pure ``desloppify`` detection core (roadmap 5.1.2).

These pin :func:`novel_ralph_skill.rulepack.detect.detect`, the pure aggregation
over a :class:`~novel_ralph_skill.rulepack.RulePack` and in-memory chapter text
(design §4.4, §6.1, §9). The core has no filesystem and no ``sys.exit``, so it is
exercised directly here with hand-built :class:`Rule`/:class:`RulePack` shapes.

The suite pins the boundary cases design §9 names: a ``manuscript`` rule exactly
at and one over threshold; a ``per_page`` rule exactly at and one over a
hand-computed density; an empty manuscript with no ``ZeroDivisionError``; the
non-overlapping ``finditer`` count; the per-line, per-chapter ``LineHit``
bookkeeping; and the three defect-3 line-scan cases — a multi-line negative (a
span split across a hard line break is undetected in v1), a cross-sentence
negative (a bounded lazy window does not over-match a distant token), and a
single-line positive.
"""

from __future__ import annotations

import re

import pytest

from novel_ralph_skill.rulepack.detect import (
    DetectionReport,
    LineHit,
    RuleFinding,
    ScannedChapter,
    detect,
)
from novel_ralph_skill.rulepack.schema import Rule, RuleBasis, RulePack


def _rule(
    rule_id: str,
    pattern: str,
    *,
    threshold: int,
    per_page: int | None = None,
) -> Rule:
    """Build one :class:`Rule` with its pattern precompiled, no flags.

    Passing ``per_page`` makes the rule a :attr:`RuleBasis.PER_PAGE` rule with
    that page size; omitting it builds a :attr:`RuleBasis.MANUSCRIPT` rule.
    """
    basis = RuleBasis.PER_PAGE if per_page is not None else RuleBasis.MANUSCRIPT
    return Rule(
        id=rule_id,
        pattern=pattern,
        compiled=re.compile(pattern),
        threshold=threshold,
        basis=basis,
        page_words=per_page,
    )


def _pack(*rules: Rule, name: str = "test") -> RulePack:
    """Build a one-version :class:`RulePack` over ``rules``."""
    return RulePack(schema_version=1, pack=name, rules=rules)


def _only(report: DetectionReport) -> RuleFinding:
    """Return the sole finding of a single-rule report."""
    assert len(report.findings) == 1, (
        f"expected exactly one finding, got {len(report.findings)}"
    )
    return report.findings[0]


def test_manuscript_rule_at_threshold_passes() -> None:
    """A ``manuscript`` rule with exactly ``threshold`` hits passes."""
    pack = _pack(_rule("tic", r"tic", threshold=2))
    report = detect(pack, [ScannedChapter(number=1, text="tic tic")])
    finding = _only(report)
    assert finding.count == 2, f"two hits expected, got {finding.count}"
    assert finding.passed is True, "count at threshold must pass"
    assert finding.density is None, "manuscript rule has no density"
    assert report.passed is True, "report passes when its only rule passes"


def test_manuscript_rule_over_threshold_fails() -> None:
    """A ``manuscript`` rule one hit over ``threshold`` fails."""
    pack = _pack(_rule("tic", r"tic", threshold=2))
    report = detect(pack, [ScannedChapter(number=1, text="tic tic tic")])
    finding = _only(report)
    assert finding.count == 3, f"three hits expected, got {finding.count}"
    assert finding.passed is False, "count over threshold must fail"
    assert report.passed is False, "report fails when any rule fails"


def test_per_page_rule_at_density_threshold_passes() -> None:
    """A ``per_page`` rule exactly at its hand-computed density passes.

    Twelve words over a six-word page is two pages; four hits is a density of
    exactly ``2.0`` per page, the threshold, so the rule passes.
    """
    rule = _rule("dash", r"-", threshold=2, per_page=6)
    text = "- - - - w w w w w w w w"  # 12 tokens, 4 hits, 2 pages
    report = detect(_pack(rule), [ScannedChapter(number=1, text=text)])
    finding = _only(report)
    assert finding.count == 4, f"four hits expected, got {finding.count}"
    assert finding.density == pytest.approx(2.0), (
        f"density 2.0 expected, got {finding.density}"
    )
    assert finding.passed is True, "density at threshold must pass"


def test_per_page_rule_over_density_threshold_fails() -> None:
    """A ``per_page`` rule one hit over its density threshold fails."""
    rule = _rule("dash", r"-", threshold=2, per_page=6)
    text = "- - - - - w w w w w w w"  # 12 tokens, 5 hits, 2 pages -> 2.5
    report = detect(_pack(rule), [ScannedChapter(number=1, text=text)])
    finding = _only(report)
    assert finding.count == 5, f"five hits expected, got {finding.count}"
    assert finding.density == pytest.approx(2.5), (
        f"density 2.5 expected, got {finding.density}"
    )
    assert finding.passed is False, "density over threshold must fail"


def test_two_hits_one_line_carry_same_line_number() -> None:
    """Two hits on one line give ``count == 2`` and two same-line ``LineHit``s."""
    pack = _pack(_rule("tic", r"tic", threshold=5))
    report = detect(pack, [ScannedChapter(number=1, text="tic and tic")])
    finding = _only(report)
    assert finding.count == 2, f"two hits expected, got {finding.count}"
    assert finding.lines == (
        LineHit(chapter=1, line=1),
        LineHit(chapter=1, line=1),
    ), f"both hits on line 1 expected, got {finding.lines}"


def test_hits_across_chapters_carry_right_chapter() -> None:
    """Hits in chapters 1 and 2 carry the correct chapter and line."""
    pack = _pack(_rule("tic", r"tic", threshold=5))
    report = detect(
        pack,
        [
            ScannedChapter(number=1, text="quiet\ntic here"),
            ScannedChapter(number=2, text="tic there"),
        ],
    )
    finding = _only(report)
    assert finding.count == 2, f"two hits expected, got {finding.count}"
    assert finding.lines == (
        LineHit(chapter=1, line=2),
        LineHit(chapter=2, line=1),
    ), f"per-chapter line numbers expected, got {finding.lines}"


def test_empty_manuscript_passes_without_zero_division() -> None:
    """An empty manuscript passes every rule and counts zero words."""
    rule = _rule("dash", r"-", threshold=0, per_page=6)
    report = detect(_pack(rule), [])
    finding = _only(report)
    assert report.total_words == 0, (
        f"empty manuscript counts zero words, got {report.total_words}"
    )
    assert finding.count == 0, f"no hits expected, got {finding.count}"
    assert finding.density == pytest.approx(0.0), (
        f"zero density expected, got {finding.density}"
    )
    assert finding.passed is True, "empty manuscript passes every rule"
    assert report.passed is True, "empty manuscript report passes"


def test_overlapping_matches_counted_non_overlapping() -> None:
    """A pattern that could overlap counts non-overlapping ``finditer`` matches."""
    pack = _pack(_rule("aa", r"aa", threshold=5))
    # "aaaa" yields two non-overlapping matches, not three overlapping ones.
    report = detect(pack, [ScannedChapter(number=1, text="aaaa")])
    assert _only(report).count == 2, "aaaa yields two non-overlapping matches"


def test_multi_line_span_split_yields_zero_hits() -> None:
    """A multi-token span split across a hard line break is undetected (v1)."""
    pattern = r"(?i)\bit'?s not just\b[^\n]{0,80}?\bit'?s\b"
    pack = _pack(_rule("it-s-not-just", pattern, threshold=0))
    text = "It's not just cold,\nit's freezing."
    report = detect(pack, [ScannedChapter(number=1, text=text)])
    finding = _only(report)
    assert finding.count == 0, f"split span undetected in v1, got {finding.count}"
    assert finding.passed is True, "zero hits passes the rule"


def test_cross_sentence_bounded_window_does_not_over_match() -> None:
    """A bounded lazy window does not match two distant unrelated tokens."""
    pattern = r"(?i)\bit'?s not just\b[^\n]{0,80}?\bit'?s\b"
    pack = _pack(_rule("it-s-not-just", pattern, threshold=0))
    filler = "word " * 30  # > 80 chars of filler between the tokens
    text = f"It's not just here. {filler}It's elsewhere."
    report = detect(pack, [ScannedChapter(number=1, text=text)])
    assert _only(report).count == 0, "bounded window must not span distant tokens"


def test_single_line_span_yields_one_hit() -> None:
    """A single-line "it's not just X, it's Y" yields exactly one hit."""
    pattern = r"(?i)\bit'?s not just\b[^\n]{0,80}?\bit'?s\b"
    pack = _pack(_rule("it-s-not-just", pattern, threshold=0))
    text = "It's not just cold, it's freezing."
    report = detect(pack, [ScannedChapter(number=1, text=text)])
    finding = _only(report)
    assert finding.count == 1, f"one hit expected, got {finding.count}"
    assert finding.lines == (LineHit(chapter=1, line=1),), (
        f"hit on line 1 expected, got {finding.lines}"
    )
    assert finding.passed is False, "one hit over a zero threshold must fail"
