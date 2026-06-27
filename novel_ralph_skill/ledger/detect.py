r"""The pure chapter-aware device-ledger detector (roadmap task 7.1.2; design §6.3).

This module is the pure aggregation at the heart of ``desloppify --ledger``:
given a loaded :class:`~novel_ralph_skill.ledger.schema.DeviceLedger` and the
in-memory text of the scanned chapters, it counts each device's spends and
evaluates whether the manuscript on disk has overspent the device's ration. It
performs no filesystem access, calls no :func:`sys.exit`, and builds no envelope,
so it is trivially unit-testable. Exit-code translation and text sourcing are the
command body's job (:mod:`novel_ralph_skill.commands._desloppify_ledger`).

It mirrors :mod:`novel_ralph_skill.rulepack.detect`: detection scans **line by
line**, not over whole-chapter text. The loader compiles every pattern with no
flags, so ``.`` cannot cross ``\n``; splitting each chapter into physical lines
and running :meth:`re.Pattern.finditer` per line makes the ``{chapter, line}``
attribution exact and bounds every match to a single line. A multi-token device
must therefore use a bounded non-newline window ``[^\n]{0,N}?`` rather than greedy
``.*`` (the same v1 limitation the rule-pack detector documents).

The current spend is **recomputed from the chapter text on every run**: the count
is the literal total of ``finditer`` hits across the scanned lines, with no
semantic gate (design §6.3 "recomputed from disk on every run"). The detector
reuses :class:`~novel_ralph_skill.rulepack.detect.ScannedChapter` and
:class:`~novel_ralph_skill.rulepack.detect.LineHit` so the chapter-number
attribution the window checks depend on is identical to the rule-pack path.

The result shapes follow the package's frozen, slotted, keyword-only house style.
"""

from __future__ import annotations

import dataclasses
import typing as typ

from novel_ralph_skill.loaderkit.scan import scan_pattern
from novel_ralph_skill.rulepack.detect import LineHit

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.ledger.schema import Device, DeviceLedger
    from novel_ralph_skill.rulepack.detect import ScannedChapter


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DeviceFinding:
    """One device's aggregated rationing result (design §6.3).

    Attributes
    ----------
    device_id : str
        The device's stable identifier, named in the report and any message.
    pattern : str
        The authored pattern source, echoed for reporting.
    count : int
        The total number of literal ``finditer`` hits across every scanned line
        of every chapter (the recomputed-from-disk spend).
    ration_kind : str
        Which ration the device carries: ``"max_count"``, ``"allowed_chapters"``,
        ``"retired_after_chapter"``, or ``"reserved_for_chapter"``. When
        ``max_count`` pairs with a window constraint, this is the window kind and
        :attr:`max_count` carries the paired count bound.
    max_count : int | None
        The paired or sole ``max_count`` bound, or ``None`` when the device has no
        ``max_count``.
    bound : tuple[int, ...] | None
        The window bound: the allowed-chapter tuple for ``allowed_chapters``, or a
        single-element tuple holding ``N`` for ``retired_after_chapter`` /
        ``reserved_for_chapter``, or ``None`` for a bare ``max_count`` device.
    offending_chapters : tuple[int, ...]
        The distinct hit chapters that breach the window constraint, ascending; an
        empty tuple when the window (if any) is satisfied. A ``max_count`` breach
        leaves this empty (the breach is a total, not a chapter).
    passed : bool
        Whether the device is within its whole ration (both the ``max_count`` and
        the window constraint, when paired).
    lines : tuple[LineHit, ...]
        The ``(chapter, line)`` of every hit, in scan order (ascending chapter,
        then ascending line, then left-to-right within a line).
    """

    device_id: str
    pattern: str
    count: int
    ration_kind: str
    max_count: int | None
    bound: tuple[int, ...] | None
    offending_chapters: tuple[int, ...]
    passed: bool
    lines: tuple[LineHit, ...]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class LedgerReport:
    """The whole-ledger detection result over the scanned chapters.

    Attributes
    ----------
    findings : tuple[DeviceFinding, ...]
        One finding per device, in the ledger's authoring order.
    passed : bool
        ``True`` if and only if every device is within its ration.
    """

    findings: tuple[DeviceFinding, ...]
    passed: bool


def _scan_device(
    device: Device, chapters: cabc.Sequence[ScannedChapter]
) -> tuple[int, tuple[LineHit, ...]]:
    r"""Count one device's literal matches per physical line.

    Splits each chapter into physical lines and runs the device's precompiled
    pattern over each line independently, recording the one-based line index. The
    no-flags compilation means ``.`` cannot cross ``\n``, so a per-line scan makes
    the ``{chapter, line}`` attribution exact and bounds every match to one line.

    Parameters
    ----------
    device : Device
        The device whose precompiled pattern is scanned.
    chapters : collections.abc.Sequence[ScannedChapter]
        The scanned chapters, in order.

    Returns
    -------
    tuple[int, tuple[LineHit, ...]]
        The total literal match count and the per-match ``LineHit`` tuple, in scan
        order.
    """
    return scan_pattern(
        device.compiled,
        chapters,
        line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line),
    )


def _window(device: Device) -> tuple[str, tuple[int, ...] | None]:
    """Return the device's window ``(ration_kind, bound)`` pair.

    A device carries at most one window constraint (the loader enforces this); a
    bare ``max_count`` device has none. The bound is the allowed-chapter tuple for
    ``allowed_chapters`` or a single-element tuple ``(N,)`` for the boundary
    constraints, so the report can echo the authored bound uniformly.

    Parameters
    ----------
    device : Device
        The validated device.

    Returns
    -------
    tuple[str, tuple[int, ...] | None]
        The ration kind and its bound. For a bare ``max_count`` device this is
        ``("max_count", None)``.
    """
    if device.allowed_chapters is not None:
        return "allowed_chapters", device.allowed_chapters
    if device.retired_after_chapter is not None:
        return "retired_after_chapter", (device.retired_after_chapter,)
    if device.reserved_for_chapter is not None:
        return "reserved_for_chapter", (device.reserved_for_chapter,)
    return "max_count", None


def _window_offenders(
    device: Device, hit_chapters: cabc.Sequence[int]
) -> tuple[int, ...]:
    """Return the distinct hit chapters that breach the device's window, ascending.

    Reads each window constraint negatively (ExecPlan Decision Log): a hit chapter
    outside ``allowed_chapters`` offends; a hit chapter past
    ``retired_after_chapter`` offends; a hit chapter other than
    ``reserved_for_chapter`` offends. A bare ``max_count`` device has no window and
    so no window offenders. Zero hits is silent (the negative reading has no
    "must appear" floor; design §6.3 specifies none).

    Parameters
    ----------
    device : Device
        The validated device.
    hit_chapters : collections.abc.Sequence[int]
        The chapters the device was found in (one entry per hit; duplicates are
        collapsed here).

    Returns
    -------
    tuple[int, ...]
        The distinct offending chapters, ascending.
    """
    distinct = set(hit_chapters)
    if device.allowed_chapters is not None:
        allowed = set(device.allowed_chapters)
        offenders = {chapter for chapter in distinct if chapter not in allowed}
    elif device.retired_after_chapter is not None:
        limit = device.retired_after_chapter
        offenders = {chapter for chapter in distinct if chapter > limit}
    elif device.reserved_for_chapter is not None:
        reserved = device.reserved_for_chapter
        offenders = {chapter for chapter in distinct if chapter != reserved}
    else:
        offenders = set()
    return tuple(sorted(offenders))


def _finding(
    device: Device, *, count: int, lines: tuple[LineHit, ...]
) -> DeviceFinding:
    """Build one :class:`DeviceFinding`, evaluating the device's whole ration.

    A device passes when both its constraints hold: ``count <= max_count`` (when a
    ``max_count`` is set) *and* no chapter breaches the window constraint (when one
    is set). When ``max_count`` pairs with a window, both must hold.

    Parameters
    ----------
    device : Device
        The validated device supplying the ration.
    count : int
        The device's total literal match count.
    lines : tuple[LineHit, ...]
        The per-match ``LineHit`` tuple.

    Returns
    -------
    DeviceFinding
        The aggregated finding for ``device``.
    """
    ration_kind, bound = _window(device)
    offenders = _window_offenders(device, [hit.chapter for hit in lines])
    within_count = device.max_count is None or count <= device.max_count
    within_window = not offenders
    return DeviceFinding(
        device_id=device.id,
        pattern=device.pattern,
        count=count,
        ration_kind=ration_kind,
        max_count=device.max_count,
        bound=bound,
        offending_chapters=offenders,
        passed=within_count and within_window,
        lines=lines,
    )


def detect_ledger(
    ledger: DeviceLedger,
    chapters: cabc.Sequence[ScannedChapter],
) -> LedgerReport:
    """Evaluate ``ledger``'s devices over ``chapters`` into a report.

    Pure — a ledger and in-memory chapter text in, a :class:`LedgerReport` out —
    so any caller can reuse it without a filesystem. Each device is scanned line by
    line across every passed chapter, its spend tallied as the literal ``finditer``
    hit total (recomputed from the supplied text, never cached), and its ration
    evaluated: ``max_count`` against the total, and the one window constraint (if
    any) against the hit chapters.

    Parameters
    ----------
    ledger : DeviceLedger
        The loaded, validated device ledger to enforce.
    chapters : collections.abc.Sequence[ScannedChapter]
        The chapters to scan, in the order their findings' lines should appear.

    Returns
    -------
    LedgerReport
        One finding per device and the overall pass flag.
    """
    findings: list[DeviceFinding] = []
    for device in ledger.devices:
        count, lines = _scan_device(device, chapters)
        findings.append(_finding(device, count=count, lines=lines))
    return LedgerReport(
        findings=tuple(findings),
        passed=all(finding.passed for finding in findings),
    )
