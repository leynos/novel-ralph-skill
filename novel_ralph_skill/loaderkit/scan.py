r"""The shared per-line scan primitive both pack detectors consume (design §6.1).

Roadmap task 7.2.2 consolidates the byte-identical ``_scan_rule``/``_scan_device``
bodies here, and roadmap 7.2.3 relocates their neutral input and output shapes —
:class:`ScannedChapter` and :class:`LineHit` — alongside them, so the per-line
scan's single home is complete. :func:`scan_pattern` splits each chapter into
physical lines and runs a precompiled pattern's :meth:`re.Pattern.finditer` per
line, accumulating one hit per match. The no-flags compilation the loaders use
means ``.`` cannot cross ``\n``, so a per-line scan makes line numbers exact and
bounds every match to one line (the v1 single-line-coverage discipline; ADR-001).

The primitive carries no ``Rule``/``Device`` knowledge: the caller dereferences
``rule.compiled``/``device.compiled`` before calling, and the ``line_hit``
constructor is the seam that keeps the shared body free of any ``Rule``/``Device``
knowledge. Both scan shapes are plain frozen dataclasses with only stdlib-typed
fields defined here, so this module imports neither ``rulepack`` nor ``ledger`` at
runtime *or* under :data:`typing.TYPE_CHECKING`; the direction
``rulepack.detect → loaderkit.scan`` / ``ledger.detect → loaderkit.scan`` stays
acyclic.
"""

from __future__ import annotations

import dataclasses
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import re


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ScannedChapter:
    """One chapter's number and in-memory draft text, the detection input.

    Attributes
    ----------
    number : int
        The one-based chapter number, echoed into every :class:`LineHit` so a
        whole-manuscript finding names the source chapter, not a synthesised
        global buffer (ExecPlan Risk "line numbers drift").
    text : str
        The chapter's draft body, scanned line by line.
    """

    number: int
    text: str


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class LineHit:
    """One pattern match located at ``(chapter, line)`` (design §4.4).

    Attributes
    ----------
    chapter : int
        The one-based chapter number the match was found in.
    line : int
        The one-based physical line index within that chapter.
    """

    chapter: int
    line: int


def scan_pattern(
    pattern: re.Pattern[str],
    chapters: cabc.Sequence[ScannedChapter],
    *,
    line_hit: cabc.Callable[..., LineHit],
) -> tuple[int, tuple[LineHit, ...]]:
    r"""Count one pattern's non-overlapping matches per physical line.

    Splits each chapter into physical lines and runs ``pattern`` over each line
    independently, recording the one-based line index directly (the enumeration
    index, no offset arithmetic). This is the line-by-line scan the loaders'
    no-flags compilation requires: ``.`` cannot cross ``\n``, so a per-line scan
    makes line numbers exact and bounds every match to one line.

    Parameters
    ----------
    pattern : re.Pattern[str]
        The precompiled pattern to scan (the caller dereferences
        ``rule.compiled``/``device.compiled`` first, so this primitive holds no
        ``Rule``/``Device`` knowledge).
    chapters : collections.abc.Sequence[ScannedChapter]
        The scanned chapters, in order.
    line_hit : collections.abc.Callable[..., LineHit]
        Constructs a :class:`LineHit`, called by keyword as
        ``line_hit(chapter=chapter_number, line=line_index)``; the caller passes
        the :class:`LineHit` class itself (``line_hit=LineHit``), or any keyword
        constructor with the same ``(*, chapter, line)`` signature. This callback
        is the seam that keeps the shared body free of any ``Rule``/``Device``
        knowledge, and the keyword-call convention lets the ``kw_only``
        :class:`LineHit` bind directly without an identity-lambda wrapper.

    Returns
    -------
    tuple[int, tuple[LineHit, ...]]
        The total non-overlapping match count and the per-match ``LineHit`` tuple,
        in scan order (ascending chapter, then line, then left-to-right).
    """
    hits: list[LineHit] = []
    for chapter in chapters:
        for index, line in enumerate(chapter.text.splitlines(), start=1):
            hits.extend(
                line_hit(chapter=chapter.number, line=index)
                for _match in pattern.finditer(line)
            )
    return len(hits), tuple(hits)
