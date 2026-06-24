"""Pure word-count report derivation and envelope projection (task 6.1.1).

This module holds the pure aggregation behind the ``wordcount`` command (design
§4.5): given the novel target, the chapter manifest, and the disk-recounted
per-chapter drafted counts, it derives the per-chapter and cumulative report —
words, percentage of target, the distance to the next knitting gate, the delta
against the chapter target, and the 30/50/80% gate triggers — and projects it
into the shared envelope's :class:`~novel_ralph_skill.contract.runner.CommandOutcome`.
It lives beside the command body (:mod:`novel_ralph_skill.commands._wordcount`)
so that module stays within the 400-line cap, exactly as ``_desloppify_report.py``
sits beside ``_desloppify.py`` (ExecPlan Decision Log D-SPLIT).

Two single sources of truth are reused, never re-spelled (ExecPlan Constraints):
the gate thresholds are :data:`novel_ralph_skill.state.GATE_THRESHOLDS`
(``(0.30, 0.50, 0.80)``), and the drafted-ratio numerator is
``sum(by_chapter.values())`` recomputed from disk — the same numerator
``_check_gate_ratio_consistent`` uses (``validate.py:263``; Decision Log D-NUM).

The report reports the *derived trigger* (``ratio >= threshold``), distinct from
the recorded ``[gates.knitting]`` boolean: a recorded gate flag also encodes "and
the knitting pass integrated and logged" (design lines 590-596), which disk does
not store. ``wordcount`` never reads or reconciles ``[gates]``; it derives the
geometry from the drafted total only (Constraint "Triggers, not gate flags").

The "next" gate is the lowest threshold the drafted ratio has **not** yet reached
(``ratio < threshold``); at a ratio of exactly ``0.30`` the 30% gate is
*triggered* and the *next* gate is ``0.50`` (distance > 0), pinning the
``>=``-trigger / ``<``-next tie-break (ExecPlan A3). Past the final (80%) gate the
report carries ``next_gate_threshold`` and ``next_gate_distance`` both ``None``
(JSON ``null``) — never a negative distance (Decision Log D-NOGATE). When
``target <= 0`` every derived percentage and the gate geometry short-circuit to
``None`` rather than dividing, mirroring the validator's and oracle's totality
guard (``validate.py:261``; ExecPlan Risk "target <= 0").
"""

from __future__ import annotations

import dataclasses
import math
import typing as typ

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome
from novel_ralph_skill.state import GATE_THRESHOLDS

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state import ChapterEntry


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterReport:
    """One chapter's drafted-word report row (design §4.5).

    Attributes
    ----------
    number : int
        The one-based chapter number.
    words : int
        The chapter's drafted word count, recounted from disk.
    target_words : int
        The chapter's planned target (``ChapterEntry.target_words``).
    percent_of_chapter_target : float | None
        ``words / target_words`` as a percentage, or ``None`` when the chapter
        target is non-positive (no meaningful ratio).
    delta_against_target : int
        ``words - target_words``: positive when over, negative when under the
        chapter's planned length.
    """

    number: int
    words: int
    target_words: int
    percent_of_chapter_target: float | None
    delta_against_target: int


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class CumulativeReport:
    """The whole-manuscript cumulative report block (design §4.5).

    Attributes
    ----------
    current : int
        The drafted total ``sum(by_chapter.values())`` recounted from disk.
    target : int
        The novel target word count (``[word_counts].target``).
    percent_of_target : float | None
        ``current / target`` as a percentage, or ``None`` when ``target <= 0``.
    gate_triggered_30, gate_triggered_50, gate_triggered_80 : bool
        Whether the drafted ratio has reached each :data:`GATE_THRESHOLDS`
        element (``ratio >= threshold``); always ``False`` when ``target <= 0``.
    next_gate_threshold : float | None
        The ratio of the lowest gate the drafted ratio has **not** yet reached,
        or ``None`` past the final gate (or when ``target <= 0``).
    next_gate_distance : int | None
        The words still needed to reach :attr:`next_gate_threshold`, never
        negative, or ``None`` when no further gate remains (or ``target <= 0``).
    """

    current: int
    target: int
    percent_of_target: float | None
    gate_triggered_30: bool
    gate_triggered_50: bool
    gate_triggered_80: bool
    next_gate_threshold: float | None
    next_gate_distance: int | None


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class WordcountReport:
    """The full ``wordcount`` report: per-chapter rows plus the cumulative block.

    Attributes
    ----------
    chapters : tuple[ChapterReport, ...]
        One row per manifest chapter, ascending by ``number``.
    cumulative : CumulativeReport
        The whole-manuscript totals and gate geometry.
    """

    chapters: tuple[ChapterReport, ...]
    cumulative: CumulativeReport


def _percent(numerator: int, denominator: int) -> float | None:
    """Return ``numerator / denominator`` as a percentage, or ``None`` if degenerate.

    A non-positive ``denominator`` has no meaningful ratio, so the report carries
    ``None`` rather than dividing — the totality guard the validator and oracle
    share (``validate.py:261``).
    """
    if denominator <= 0:
        return None
    return numerator / denominator * 100.0


def _chapter_reports(
    manifest: cabc.Sequence[ChapterEntry],
    by_chapter: cabc.Mapping[str, int],
) -> tuple[ChapterReport, ...]:
    """Project each manifest chapter into its :class:`ChapterReport` row.

    Iterates the manifest ascending by ``number`` (the authoritative order), keys
    the drafted count off the zero-padded two-digit string ``recount_words``
    emits, and computes the per-chapter percentage and target delta. A chapter the
    drafted mapping does not carry contributes ``0`` words, so a report row exists
    for every manifest chapter even before its draft lands.
    """
    return tuple(
        ChapterReport(
            number=entry.number,
            words=(words := by_chapter.get(f"{entry.number:02d}", 0)),
            target_words=entry.target_words,
            percent_of_chapter_target=_percent(words, entry.target_words),
            delta_against_target=words - entry.target_words,
        )
        for entry in sorted(manifest, key=lambda entry: entry.number)
    )


def _gate_geometry(
    current: int, target: int
) -> tuple[tuple[bool, bool, bool], float | None, int | None]:
    """Derive the gate triggers and the next-gate threshold and distance.

    The triggers are ``ratio >= threshold`` for each :data:`GATE_THRESHOLDS`
    element (the ``>=`` half of the A3 tie-break). The "next" gate is the lowest
    threshold the ratio has **not** yet reached (the ``<`` half), so at a ratio of
    exactly ``0.30`` the next gate is ``0.50``, never ``0.30`` at distance ``0``.
    Past the final gate both the next-gate threshold and distance are ``None``
    (D-NOGATE). When ``target <= 0`` there is no ratio, so the triggers are all
    ``False`` and both next-gate fields are ``None`` (the totality guard).

    Returns
    -------
    tuple[tuple[bool, bool, bool], float | None, int | None]
        The three triggers, the next-gate threshold (or ``None``), and the
        non-negative next-gate distance in words (or ``None``).
    """
    if target <= 0:
        return (False, False, False), None, None
    ratio = current / target
    triggers = tuple(ratio >= threshold for threshold in GATE_THRESHOLDS)
    next_threshold = next(
        (threshold for threshold in GATE_THRESHOLDS if ratio < threshold), None
    )
    if next_threshold is None:
        return typ.cast("tuple[bool, bool, bool]", triggers), None, None
    # ``ceil`` so the reported distance, once drafted, lands the ratio at or past
    # the threshold rather than one word short of it; ``max(0, …)`` is belt-and-
    # braces for the boundary where ``ratio < threshold`` holds yet the float
    # arithmetic rounds the words-needed to zero.
    distance = max(0, math.ceil(next_threshold * target - current))
    return typ.cast("tuple[bool, bool, bool]", triggers), next_threshold, distance


def build_report(
    *,
    target: int,
    manifest: cabc.Sequence[ChapterEntry],
    by_chapter: cabc.Mapping[str, int],
) -> WordcountReport:
    """Derive the per-chapter and cumulative ``wordcount`` report (design §4.5).

    Pure aggregation: no I/O, no second counter, no re-spelled threshold literal.
    The numerator is ``sum(by_chapter.values())`` recomputed from disk (Decision
    Log D-NUM); the gate thresholds come from :data:`GATE_THRESHOLDS` (Constraint
    "Single gate-threshold source").

    Parameters
    ----------
    target : int
        The novel target word count (``[word_counts].target``).
    manifest : collections.abc.Sequence[ChapterEntry]
        The chapter manifest (``state.chapters``).
    by_chapter : collections.abc.Mapping[str, int]
        The per-chapter drafted counts keyed by the zero-padded two-digit chapter
        string, as :func:`~novel_ralph_skill.state.recount_words` emits them.

    Returns
    -------
    WordcountReport
        The frozen report: one row per manifest chapter plus the cumulative block.

    Examples
    --------
    A two-chapter manuscript drafted to exactly the 30% gate reports the 30% gate
    triggered and the 50% gate as next::

        report = build_report(target=10000, manifest=manifest, by_chapter=counts)
        assert report.cumulative.gate_triggered_30 is True
        assert report.cumulative.next_gate_threshold == 0.50
    """
    current = sum(by_chapter.values())
    triggers, next_threshold, next_distance = _gate_geometry(current, target)
    cumulative = CumulativeReport(
        current=current,
        target=target,
        percent_of_target=_percent(current, target),
        gate_triggered_30=triggers[0],
        gate_triggered_50=triggers[1],
        gate_triggered_80=triggers[2],
        next_gate_threshold=next_threshold,
        next_gate_distance=next_distance,
    )
    return WordcountReport(
        chapters=_chapter_reports(manifest, by_chapter), cumulative=cumulative
    )


def _chapter_payload(chapter: ChapterReport) -> dict[str, object]:
    """Project one :class:`ChapterReport` row into its machine ``result`` payload."""
    return {
        "number": chapter.number,
        "words": chapter.words,
        "target_words": chapter.target_words,
        "percent_of_chapter_target": chapter.percent_of_chapter_target,
        "delta_against_target": chapter.delta_against_target,
    }


def _cumulative_payload(cumulative: CumulativeReport) -> dict[str, object]:
    """Project the :class:`CumulativeReport` block into its machine ``result``."""
    return {
        "current": cumulative.current,
        "target": cumulative.target,
        "percent_of_target": cumulative.percent_of_target,
        "gate_triggered_30": cumulative.gate_triggered_30,
        "gate_triggered_50": cumulative.gate_triggered_50,
        "gate_triggered_80": cumulative.gate_triggered_80,
        "next_gate_threshold": cumulative.next_gate_threshold,
        "next_gate_distance": cumulative.next_gate_distance,
    }


def _cumulative_message(cumulative: CumulativeReport) -> str:
    """Return the one-line human summary for the cumulative block (design §3.1)."""
    if cumulative.percent_of_target is None:
        return f"drafted {cumulative.current} words (no target set)"
    percent = f"{cumulative.percent_of_target:.1f}% of target"
    if cumulative.next_gate_distance is None:
        return (
            f"drafted {cumulative.current} of {cumulative.target} words "
            f"({percent}); all knitting gates reached"
        )
    gate_percent = f"{(cumulative.next_gate_threshold or 0.0) * 100:.0f}%"
    return (
        f"drafted {cumulative.current} of {cumulative.target} words ({percent}); "
        f"next knitting gate at {gate_percent} "
        f"({cumulative.next_gate_distance} words to go)"
    )


def report_outcome(report: WordcountReport) -> CommandOutcome:
    """Project a :class:`WordcountReport` into its success :class:`CommandOutcome`.

    ``wordcount`` is a read-only report, so it always exits ``0`` (ExecPlan
    Decision Log D-EXIT): a crossed gate is information the report surfaces, not a
    refusal or an actionable finding. ``result`` carries the machine payload — the
    per-chapter ``chapters`` list and the ``cumulative`` block — while ``messages``
    carries a single human-prose summary line the harness never parses (design
    §3.1; ADR-003).

    Parameters
    ----------
    report : WordcountReport
        The derived per-chapter and cumulative report.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` carrying the report payload.
    """
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={
            "chapters": [_chapter_payload(chapter) for chapter in report.chapters],
            "cumulative": _cumulative_payload(report.cumulative),
        },
        messages=[_cumulative_message(report.cumulative)],
    )
