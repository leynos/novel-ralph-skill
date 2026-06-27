r"""The shared per-line scan primitive both pack detectors consume (design §6.1).

Roadmap task 7.2.2 consolidates the byte-identical ``_scan_rule``/``_scan_device``
bodies here. :func:`scan_pattern` splits each chapter into physical lines and runs
a precompiled pattern's :meth:`re.Pattern.finditer` per line, accumulating one hit
per match. The no-flags compilation the loaders use means ``.`` cannot cross
``\n``, so a per-line scan makes line numbers exact and bounds every match to one
line (the v1 single-line-coverage discipline; ADR-001).

The primitive carries no ``Rule``/``Device`` knowledge: the caller dereferences
``rule.compiled``/``device.compiled`` before calling, and supplies a ``line_hit``
constructor so this module never imports
:class:`~novel_ralph_skill.rulepack.detect.LineHit` at runtime. The
``ScannedChapter``/``LineHit`` shapes are referenced **only** under
:data:`typing.TYPE_CHECKING`, so there is no runtime ``loaderkit → rulepack`` edge
and the direction ``rulepack.detect → loaderkit.scan`` /
``ledger.detect → loaderkit.scan`` stays acyclic (Decision D-SCANTYPES).
"""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import re

    from novel_ralph_skill.rulepack.detect import LineHit, ScannedChapter


def scan_pattern(
    pattern: re.Pattern[str],
    chapters: cabc.Sequence[ScannedChapter],
    *,
    line_hit: cabc.Callable[[int, int], LineHit],
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
    line_hit : collections.abc.Callable[[int, int], LineHit]
        Constructs a :class:`LineHit` from ``(chapter_number, line_index)``; the
        caller passes ``lambda chapter, line: LineHit(chapter=chapter, line=line)``
        so this module never imports :class:`LineHit` at runtime.

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
                line_hit(chapter.number, index) for _match in pattern.finditer(line)
            )
    return len(hits), tuple(hits)
