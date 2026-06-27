r"""Unit tests for the shared ``loaderkit`` per-line scan primitive (roadmap 7.2.2).

These pin :func:`~novel_ralph_skill.loaderkit.scan.scan_pattern` against the
byte-identical behaviour the former ``_scan_rule``/``_scan_device`` bodies share,
constructing :class:`ScannedChapter`/:class:`LineHit` directly (as
``tests/test_rulepack_detect.py`` does). The example cases cover the load-bearing
v1 discipline — two hits on one line, hits across chapters, and the multi-line
negative where ``.`` cannot cross ``\n`` — and a Hypothesis property pins the
line-attribution invariant over arbitrary multi-line chapter text.
"""

from __future__ import annotations

import datetime as dt
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.loaderkit.scan import scan_pattern
from novel_ralph_skill.rulepack.detect import LineHit, ScannedChapter


def _line_hit(chapter: int, line: int) -> LineHit:
    """Construct a :class:`LineHit`, the constructor ``scan_pattern`` calls back."""
    return LineHit(chapter=chapter, line=line)


def test_two_hits_one_line_carry_same_line_number() -> None:
    """Two matches on one line yield two hits sharing that line number."""
    pattern = re.compile(r"ab")
    chapters = [ScannedChapter(number=1, text="ab ab")]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)
    assert count == 2
    assert hits == (LineHit(chapter=1, line=1), LineHit(chapter=1, line=1))


def test_hits_across_chapters_carry_right_chapter() -> None:
    """Hits in two chapters carry each chapter's number."""
    pattern = re.compile(r"x")
    chapters = [
        ScannedChapter(number=1, text="x"),
        ScannedChapter(number=2, text="x\nx"),
    ]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)
    assert count == 3
    assert hits == (
        LineHit(chapter=1, line=1),
        LineHit(chapter=2, line=1),
        LineHit(chapter=2, line=2),
    )


def test_multi_line_span_split_yields_zero_hits() -> None:
    r"""A span split across a hard line break is undetected: ``.`` cannot cross ``\n``.

    This is the load-bearing v1 single-line-coverage discipline: a pattern that
    would match across the line break finds nothing once the text is split per
    line.
    """
    pattern = re.compile(r"foo.bar")
    chapters = [ScannedChapter(number=1, text="foo\nbar")]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)
    assert count == 0
    assert not hits


def test_count_matches_len_and_lines_in_scan_order() -> None:
    """The count equals ``len(hits)`` and hits are in ascending scan order."""
    pattern = re.compile(r"z")
    chapters = [
        ScannedChapter(number=1, text="z\nz z"),
        ScannedChapter(number=2, text="z"),
    ]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)
    assert count == len(hits) == 4
    assert hits == (
        LineHit(chapter=1, line=1),
        LineHit(chapter=1, line=2),
        LineHit(chapter=1, line=2),
        LineHit(chapter=2, line=1),
    )


@settings(deadline=dt.timedelta(seconds=5), max_examples=100)
@given(
    lines=st.lists(
        st.text(alphabet="aX ", min_size=0, max_size=12),
        min_size=1,
        max_size=8,
    )
)
def test_line_attribution_matches_physical_line(lines: list[str]) -> None:
    """Every emitted hit's ``line`` is the 1-based index of its physical line.

    For arbitrary multi-line chapter text, each hit must be attributed to the line
    the match actually fell on — the invariant the per-line scan exists to keep.
    The property recomputes the expected per-line hit counts independently of
    :func:`scan_pattern` and asserts the emitted ``LineHit.line`` indices agree.
    """
    text = "\n".join(lines)
    pattern = re.compile(r"X")
    chapters = [ScannedChapter(number=1, text=text)]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)

    expected: list[int] = []
    for index, physical_line in enumerate(text.splitlines(), start=1):
        expected.extend(index for _match in pattern.finditer(physical_line))

    assert count == len(expected)
    assert [hit.line for hit in hits] == expected
    assert all(hit.chapter == 1 for hit in hits)
