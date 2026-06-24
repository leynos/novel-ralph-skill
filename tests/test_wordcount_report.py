"""Unit tests for the pure ``build_report`` aggregation (roadmap task 6.1.1).

These exercise
:func:`novel_ralph_skill.commands._wordcount_report.build_report` in isolation —
no CLI, no disk — pinning the per-chapter delta arithmetic, the cumulative
percentage, the gate-trigger geometry, and the ``next_gate_distance`` at and
between thresholds (design §4.5). They assert the derived triggers agree
element-wise with :data:`novel_ralph_skill.state.GATE_THRESHOLDS` so a future
threshold edit propagates rather than drifting from a second literal (ExecPlan
Risk mitigation), and pin the ``target <= 0`` short-circuit and the past-final-gate
``None`` shape (Decision Log D-NOGATE).
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.commands._wordcount_report import build_report
from novel_ralph_skill.state import GATE_THRESHOLDS, ChapterEntry

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def _manifest(*targets: int) -> tuple[ChapterEntry, ...]:
    """Return a manifest of chapters with the given per-chapter targets."""
    return tuple(
        ChapterEntry(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=target,
        )
        for index, target in enumerate(targets)
    )


def _by_chapter(*words: int) -> dict[str, int]:
    """Return a per-chapter mapping keyed by the zero-padded chapter string."""
    return {f"{index + 1:02d}": count for index, count in enumerate(words)}


def test_per_chapter_delta_and_percentage() -> None:
    """Each row reports drafted words, the target delta, and the per-chapter %."""
    manifest = _manifest(10000, 10000)
    report = build_report(
        target=20000, manifest=manifest, by_chapter=_by_chapter(12000, 8000)
    )
    first, second = report.chapters
    assert first.words == 12000
    assert first.delta_against_target == 2000, "over-target delta is positive"
    assert first.percent_of_chapter_target == pytest.approx(120.0)
    assert second.delta_against_target == -2000, "under-target delta is negative"
    assert second.percent_of_chapter_target == pytest.approx(80.0)


def test_chapters_sum_to_current() -> None:
    """The per-chapter words sum to the cumulative ``current`` total."""
    manifest = _manifest(10000, 10000, 10000)
    report = build_report(
        target=30000, manifest=manifest, by_chapter=_by_chapter(3000, 4000, 5000)
    )
    assert sum(row.words for row in report.chapters) == report.cumulative.current
    assert report.cumulative.current == 12000
    assert report.cumulative.percent_of_target == pytest.approx(40.0)


def test_missing_chapter_count_contributes_zero() -> None:
    """A manifest chapter with no drafted entry reports ``0`` words, not absent."""
    manifest = _manifest(10000, 10000)
    # Only chapter 1 has a drafted count; chapter 2 is undrafted.
    report = build_report(target=20000, manifest=manifest, by_chapter={"01": 5000})
    assert [row.words for row in report.chapters] == [5000, 0]
    assert report.cumulative.current == 5000


@pytest.mark.parametrize(
    ("threshold_index", "expected_triggers", "expected_next"),
    [
        (0, (True, False, False), GATE_THRESHOLDS[1]),
        (1, (True, True, False), GATE_THRESHOLDS[2]),
        (2, (True, True, True), None),
    ],
)
def test_exactly_on_gate_triggers_and_next_is_higher(
    threshold_index: int,
    expected_triggers: tuple[bool, bool, bool],
    expected_next: float | None,
) -> None:
    """At exactly a gate the gate is reached and the next gate is the higher one.

    Pins the ``>=``-trigger / ``<``-next tie-break (ExecPlan A3): at a ratio of
    exactly 0.30 the 30% gate is *triggered* and the *next* gate is 0.50 with a
    positive distance, not the 30% gate at distance 0. The expected trigger tuple
    is spelled out per case rather than re-deriving ``ratio >= gate`` (which would
    just re-implement the production logic the test is meant to pin).
    """
    target = 10000
    threshold = GATE_THRESHOLDS[threshold_index]
    current = round(threshold * target)
    report = build_report(
        target=target, manifest=_manifest(target), by_chapter={"01": current}
    )
    cumulative = report.cumulative
    triggers = (
        cumulative.gate_triggered_30,
        cumulative.gate_triggered_50,
        cumulative.gate_triggered_80,
    )
    assert triggers == expected_triggers, (
        f"at exactly the {GATE_THRESHOLDS[threshold_index]:.0%} gate the triggers "
        f"must be {expected_triggers}, got {triggers}"
    )
    assert cumulative.next_gate_threshold == expected_next
    if expected_next is None:
        assert cumulative.next_gate_distance is None
    else:
        assert cumulative.next_gate_distance is not None
        assert cumulative.next_gate_distance > 0, "next-gate distance is positive"


def test_next_gate_distance_between_thresholds_is_non_negative() -> None:
    """Between gates the next-gate distance is the positive words still needed."""
    target = 10000
    # 40% drafted: 30% triggered, next gate 50% needs 1000 more words.
    report = build_report(
        target=target, manifest=_manifest(target), by_chapter={"01": 4000}
    )
    cumulative = report.cumulative
    assert cumulative.gate_triggered_30 is True
    assert cumulative.gate_triggered_50 is False
    assert cumulative.next_gate_threshold == GATE_THRESHOLDS[1]
    assert cumulative.next_gate_distance == 1000


def test_past_final_gate_has_no_next_gate() -> None:
    """Past the 80% gate both next-gate fields are ``None``, never negative."""
    target = 10000
    report = build_report(
        target=target, manifest=_manifest(target), by_chapter={"01": 9000}
    )
    cumulative = report.cumulative
    assert cumulative.gate_triggered_80 is True
    assert cumulative.next_gate_threshold is None
    assert cumulative.next_gate_distance is None


def test_target_zero_short_circuits() -> None:
    """``target == 0`` short-circuits: no triggers, no percentages, no division."""
    report = build_report(target=0, manifest=_manifest(0), by_chapter={"01": 4000})
    cumulative = report.cumulative
    assert cumulative.percent_of_target is None
    assert (
        cumulative.gate_triggered_30,
        cumulative.gate_triggered_50,
        cumulative.gate_triggered_80,
    ) == (False, False, False)
    assert cumulative.next_gate_threshold is None
    assert cumulative.next_gate_distance is None
    # The per-chapter percentage is likewise ``None`` when its target is zero.
    assert report.chapters[0].percent_of_chapter_target is None


def test_empty_manifest_reports_no_chapters() -> None:
    """An empty manifest yields no chapter rows and a zero drafted total."""
    manifest: cabc.Sequence[ChapterEntry] = ()
    report = build_report(target=20000, manifest=manifest, by_chapter={})
    assert not report.chapters, "an empty manifest yields no chapter rows"
    assert report.cumulative.current == 0
    assert report.cumulative.percent_of_target == pytest.approx(0.0)
