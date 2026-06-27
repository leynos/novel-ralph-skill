r"""Unit tests for the shared ``loaderkit`` per-line scan primitive (roadmap 7.2.2).

These pin :func:`~novel_ralph_skill.loaderkit.scan.scan_pattern` against the
byte-identical behaviour the former ``_scan_rule``/``_scan_device`` bodies share,
constructing the neutral :class:`ScannedChapter`/:class:`LineHit` shapes directly
from their ``loaderkit`` home (roadmap 7.2.3). The example cases cover the
load-bearing v1 discipline — two hits on one line, hits across chapters, and the
multi-line negative where ``.`` cannot cross ``\n`` — and two Hypothesis
properties pin the line-attribution invariant over arbitrary multi-line chapter
text: one freeze property that echoes the implementation's :meth:`str.splitlines`
call, and one that derives the expected hits from an independent regex model over
the full universal-newline boundary class so a future narrowing of the splitting
choice (a move to ``split("\n")``) is caught rather than echoed (addendum
7.2.2.1). Two structural guards pin the single neutral home: the shapes are
defined in ``loaderkit.scan``, and a parametrised guard walks every module in the
``loaderkit`` package to prove none imports a pack domain.
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.loaderkit.scan import LineHit, ScannedChapter, scan_pattern


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
    This is the freeze property: it recomputes the expected per-line hit counts
    with :meth:`str.splitlines`, the same call :func:`scan_pattern` makes, so it
    pins the per-hit attribution but deliberately echoes the implementation's
    splitting choice. The sibling
    :func:`test_line_attribution_matches_independent_newline_model` pins that
    choice against an independent model (addendum 7.2.2.1).
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


# Every single-character boundary str.splitlines recognises. ``\r\n`` is the
# only multi-character boundary, and the interleaving strategy below never places
# two boundaries adjacently, so it cannot arise; modelling the single-character
# set is therefore complete for the inputs this property generates.
_UNIVERSAL_NEWLINE_BOUNDARIES = (
    "\n",
    "\r",
    "\v",
    "\f",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    "\u2028",
    "\u2029",
)

# An independent splitter over the full universal-newline boundary class. ``re``
# is a structurally different mechanism from :meth:`str.splitlines`, so this
# oracle shares no splitting machinery with :func:`scan_pattern`. Like
# ``splitlines`` (and unlike ``split``), it yields no trailing empty segment;
# the interleaving strategy never emits a trailing boundary, so the two agree on
# segment count for valid inputs while diverging the instant the implementation
# narrows its boundary set (e.g. a move to ``split("\n")``).
_BOUNDARY_RE = re.compile("[" + "".join(_UNIVERSAL_NEWLINE_BOUNDARIES) + "]")


def _split_on_universal_newline_independently(text: str) -> list[str]:
    r"""Split ``text`` on the universal-newline class without :meth:`str.splitlines`.

    The independent newline model: a regex split over every boundary character
    :meth:`str.splitlines` recognises, sharing no splitting machinery with
    :func:`scan_pattern`. A future narrowing of the implementation's boundary
    set \u2014 a move to ``split("\n")``, or dropping ``\r``/``\x85`` \u2014 would merge
    two physical lines the model still separates, shifting the line indices and
    tripping the property below.
    """
    return _BOUNDARY_RE.split(text)


@st.composite
def _boundary_separated_text(draw: st.DrawFn) -> str:
    r"""Build text whose only line boundaries are single universal-newline chars.

    Draws non-boundary tokens and interleaves a drawn boundary character between
    each adjacent pair, so boundaries never abut (no ``\r\n`` forms) and the text
    never starts or ends on a boundary. This keeps the regex oracle and
    :meth:`str.splitlines` in agreement on segment count for the correct
    implementation while exercising the full boundary class.
    """
    token = st.text(
        alphabet=st.characters(
            codec="utf-8",
            # Exclude every str.splitlines boundary so tokens carry no boundary
            # of their own; the interleaved separators are the only boundaries.
            exclude_characters="".join(_UNIVERSAL_NEWLINE_BOUNDARIES),
        ),
        min_size=0,
        max_size=12,
    )
    tokens = draw(st.lists(token, min_size=1, max_size=8))
    separators = draw(
        st.lists(
            st.sampled_from(_UNIVERSAL_NEWLINE_BOUNDARIES),
            min_size=len(tokens) - 1,
            max_size=len(tokens) - 1,
        )
    )
    pieces: list[str] = [tokens[0]]
    for separator, next_token in zip(separators, tokens[1:], strict=True):
        pieces.extend((separator, next_token))
    return "".join(pieces)


@settings(deadline=dt.timedelta(seconds=5), max_examples=200)
@given(text=_boundary_separated_text())
def test_line_attribution_matches_independent_newline_model(text: str) -> None:
    r"""Hits agree with a boundary-class oracle that never calls ``splitlines``.

    The sibling :func:`test_line_attribution_matches_physical_line` recomputes the
    expected hits with :meth:`str.splitlines`, the same call ``scan_pattern`` makes,
    so it cannot catch a line-splitting regression (a move to ``split("\n")`` or a
    dropped universal-newline boundary). This property derives the expected
    per-line hits from :func:`_split_on_universal_newline_independently`, a regex
    model over the full boundary class that shares no splitting machinery with the
    implementation, pinning the line-attribution contract against the
    implementation's own splitting choice rather than echoing it.
    """
    pattern = re.compile(r"X")
    chapters = [ScannedChapter(number=1, text=text)]
    count, hits = scan_pattern(pattern, chapters, line_hit=_line_hit)

    expected: list[int] = []
    for index, physical_line in enumerate(
        _split_on_universal_newline_independently(text), start=1
    ):
        expected.extend(index for _match in pattern.finditer(physical_line))

    assert count == len(expected)
    assert [hit.line for hit in hits] == expected
    assert all(hit.chapter == 1 for hit in hits)


def test_scan_shapes_are_defined_in_loaderkit() -> None:
    """The two scan shapes are defined in ``loaderkit.scan``, their single home."""
    assert ScannedChapter.__module__ == "novel_ralph_skill.loaderkit.scan"
    assert LineHit.__module__ == "novel_ralph_skill.loaderkit.scan"


def _loaderkit_module_paths() -> list[pathlib.Path]:
    """Return the source path of every module in the ``loaderkit`` package.

    Walking the package directory — rather than naming ``scan.py`` alone — keeps
    the import-direction guard honest as the package grows: a future regression in
    ``coerce.py``, ``load.py``, ``__init__.py``, or any module added later is caught
    too, not just one in ``scan.py``.
    """
    from novel_ralph_skill import loaderkit

    package_dir = pathlib.Path(loaderkit.__file__).parent
    return sorted(package_dir.glob("*.py"))


def test_scan_pattern_builds_every_hit_via_line_hit_callback() -> None:
    """`scan_pattern` builds each hit only through the supplied factory.

    The recording double ignores its arguments and returns one shared sentinel
    instance, so the ``hit is sentinel`` assertion proves ``scan_pattern`` uses
    the factory's *return value* verbatim and never constructs a hit by any other
    means. The sentinel is a :class:`LineHit` (not a bare ``object``) only to
    satisfy the ``line_hit`` callable's return annotation; its identity, not its
    fields, is what the test checks.
    """
    calls: list[tuple[int, int]] = []
    sentinel = LineHit(chapter=-1, line=-1)

    def recording_line_hit(chapter: int, line: int) -> LineHit:
        """Record each ``(chapter, line)`` call and return the shared sentinel."""
        calls.append((chapter, line))
        return sentinel

    pattern = re.compile(r"z")
    chapters = [
        ScannedChapter(number=3, text="z\nz z"),
        ScannedChapter(number=7, text="z"),
    ]
    count, hits = scan_pattern(pattern, chapters, line_hit=recording_line_hit)
    assert count == 4
    assert calls == [(3, 1), (3, 2), (3, 2), (7, 1)]
    assert all(hit is sentinel for hit in hits)


@pytest.mark.parametrize(
    "module_path",
    _loaderkit_module_paths(),
    ids=lambda path: path.name,
)
def test_loaderkit_module_imports_no_pack_domain(module_path: pathlib.Path) -> None:
    """Every ``loaderkit`` module imports nothing from a pack domain.

    The neutral-leaf invariant (design §6/§6.3, ADR-003) applies to the whole
    package: no ``loaderkit`` module may import ``rulepack`` or ``ledger``, so both
    packs can depend on ``loaderkit`` without an import cycle.
    """
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    banned = ("novel_ralph_skill.rulepack", "novel_ralph_skill.ledger")
    assert not [module for module in imported if module.startswith(banned)]
