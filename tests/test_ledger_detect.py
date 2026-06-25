"""Unit tests for the pure chapter-aware device-ledger detector (roadmap 7.1.2).

These pin :func:`novel_ralph_skill.ledger.detect.detect_ledger`, the pure
aggregation over a :class:`~novel_ralph_skill.ledger.schema.DeviceLedger` and
in-memory chapter text (design §6.3). The detector has no filesystem and no
``sys.exit``, so it is exercised directly here with hand-built
:class:`Device`/:class:`DeviceLedger` shapes and synthesised
:class:`~novel_ralph_skill.rulepack.detect.ScannedChapter`s.

The suite pins one breach and one clean case per constraint kind (``max_count``,
``allowed_chapters``, ``retired_after_chapter``, ``reserved_for_chapter``), the
explicit per-chapter attribution (a hit in chapter 5 is attributed to chapter 5),
the ``max_count``-plus-window pairing, and the recompute-from-disk behaviour
expressed as: the count equals the literal total ``finditer`` hits across the
supplied chapters, so removing a spend lowers the count with no ledger edit.
"""

from __future__ import annotations

import dataclasses
import re

import pytest

from novel_ralph_skill.ledger.detect import DeviceFinding, LedgerReport, detect_ledger
from novel_ralph_skill.ledger.schema import Device, DeviceLedger
from novel_ralph_skill.rulepack.detect import ScannedChapter


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class _Ration:
    """A typed grouping of the four optional rationing fields for the factory.

    Grouping the rationing fields into one config object keeps the :func:`_device`
    factory within the project argument-count gate while preserving each field's
    type (a ``**kwargs`` forward would erase them). A test names only the
    constraint it exercises; the rest default to ``None``.
    """

    max_count: int | None = None
    allowed_chapters: tuple[int, ...] | None = None
    retired_after_chapter: int | None = None
    reserved_for_chapter: int | None = None


def _device(device_id: str, pattern: str, ration: _Ration | None = None) -> Device:
    """Build one :class:`Device` with its pattern precompiled, no flags.

    The rationing fields are supplied via a typed :class:`_Ration` config so this
    factory stays within the argument-count gate while mirroring the :class:`Device`
    dataclass. ``ration`` defaults to ``None`` (a fresh empty :class:`_Ration`) so a
    test that only needs a pattern omits it.
    """
    ration = ration or _Ration()
    return Device(
        id=device_id,
        pattern=pattern,
        compiled=re.compile(pattern),
        max_count=ration.max_count,
        allowed_chapters=ration.allowed_chapters,
        retired_after_chapter=ration.retired_after_chapter,
        reserved_for_chapter=ration.reserved_for_chapter,
    )


def _ledger(*devices: Device) -> DeviceLedger:
    """Build a one-version :class:`DeviceLedger` over ``devices``."""
    return DeviceLedger(schema_version=1, devices=devices)


def _only(report: LedgerReport) -> DeviceFinding:
    """Return the report's single finding, asserting there is exactly one."""
    assert len(report.findings) == 1, (
        f"expected exactly one finding, got {len(report.findings)}"
    )
    return report.findings[0]


def test_max_count_at_bound_passes() -> None:
    """A ``max_count`` device with exactly ``max_count`` hits passes."""
    ledger = _ledger(_device("bloom", r"bloom", _Ration(max_count=2)))
    report = detect_ledger(ledger, [ScannedChapter(number=1, text="bloom\nbloom")])
    finding = _only(report)
    assert finding.count == 2, f"two hits expected, got {finding.count}"
    assert finding.passed is True, "count at max_count must pass"
    assert finding.offending_chapters == (), "within ration: no offending chapters"
    assert report.passed is True, "report passes when its only device passes"


def test_max_count_over_bound_fails() -> None:
    """A ``max_count`` device one hit over its bound fails."""
    ledger = _ledger(_device("sternum", r"sternum", _Ration(max_count=3)))
    text = "sternum\nsternum\nsternum\nsternum"
    report = detect_ledger(ledger, [ScannedChapter(number=1, text=text)])
    finding = _only(report)
    assert finding.count == 4, f"four hits expected, got {finding.count}"
    assert finding.passed is False, "count over max_count must fail"
    assert finding.ration_kind == "max_count", "bare max_count device has no window"
    assert report.passed is False, "report fails when its only device fails"


# Each window constraint, as a pre-built device, paired with two clean chapters it
# permits. Parametrising the three windows collapses the otherwise-identical "used
# only inside → passes" cases while keeping the standalone-function style of
# ``test_rulepack_detect.py``; pre-building the device keeps the typed factory call
# out of the parametrize data (a ``**dict`` forward would erase the field types).
_WINDOW_PASS_CASES = (
    (_device("motif", r"motif", _Ration(allowed_chapters=(1, 3, 8))), (1, 3)),
    (_device("motif", r"motif", _Ration(retired_after_chapter=7)), (1, 7)),
    (_device("motif", r"motif", _Ration(reserved_for_chapter=12)), (12, 12)),
)
# Each window constraint (as a pre-built device) paired with the chapter that
# breaches it, the expected sole offender, and the ration kind the finding echoes.
_WINDOW_FAIL_CASES = (
    (
        _device("motif", r"motif", _Ration(allowed_chapters=(1, 3, 8))),
        5,
        "allowed_chapters",
    ),
    (
        _device("motif", r"motif", _Ration(retired_after_chapter=7)),
        9,
        "retired_after_chapter",
    ),
    (
        _device("motif", r"motif", _Ration(reserved_for_chapter=12)),
        4,
        "reserved_for_chapter",
    ),
)


@pytest.mark.parametrize(("device", "chapters"), _WINDOW_PASS_CASES)
def test_window_inside_passes(device: Device, chapters: tuple[int, int]) -> None:
    """A windowed device used only inside its window passes with no offenders."""
    report = detect_ledger(
        _ledger(device),
        [ScannedChapter(number=number, text="motif") for number in chapters],
    )
    finding = _only(report)
    assert finding.passed is True, f"all hits inside {finding.ration_kind} must pass"
    assert finding.offending_chapters == (), "no chapter breaches the window"


@pytest.mark.parametrize(("device", "chapter", "kind"), _WINDOW_FAIL_CASES)
def test_window_breach_names_chapter(device: Device, chapter: int, kind: str) -> None:
    """A windowed device used in a breaching chapter fails, naming that chapter."""
    report = detect_ledger(
        _ledger(device), [ScannedChapter(number=chapter, text="motif")]
    )
    finding = _only(report)
    assert finding.passed is False, f"a hit breaching {kind} must fail"
    assert finding.offending_chapters == (chapter,), (
        f"chapter {chapter} must be the sole offender, got {finding.offending_chapters}"
    )
    assert finding.ration_kind == kind, "ration kind echoes the window"
    assert report.passed is False, "report fails when its only device fails"


def test_per_chapter_attribution_is_exact() -> None:
    """Each hit is attributed to the chapter it was found in."""
    ledger = _ledger(_device("motif", r"motif", _Ration(allowed_chapters=(1,))))
    report = detect_ledger(
        ledger,
        [
            ScannedChapter(number=2, text="line\nmotif"),
            ScannedChapter(number=5, text="motif\nline"),
        ],
    )
    finding = _only(report)
    chapters = {hit.chapter for hit in finding.lines}
    assert chapters == {2, 5}, f"hits must be attributed to 2 and 5, got {chapters}"
    # Chapter 2's hit is on the second line; chapter 5's on the first.
    by_chapter = {hit.chapter: hit.line for hit in finding.lines}
    assert by_chapter == {2: 2, 5: 1}, (
        f"per-chapter line attribution wrong: {by_chapter}"
    )
    assert finding.offending_chapters == (2, 5), "both chapters are outside allowed {1}"


def test_max_count_paired_with_window_requires_both() -> None:
    """A ``max_count`` + ``allowed_chapters`` device fails if either is breached."""
    device = _device(
        "sternum", r"sternum", _Ration(max_count=3, allowed_chapters=(1, 3, 8))
    )
    # Four hits (over max_count=3), all in chapter 5 (outside the allowed set):
    # both clauses breached.
    text = "sternum\nsternum\nsternum\nsternum"
    report = detect_ledger(_ledger(device), [ScannedChapter(number=5, text=text)])
    finding = _only(report)
    assert finding.count == 4, f"four hits expected, got {finding.count}"
    assert finding.passed is False, "both clauses breached must fail"
    assert finding.max_count == 3, "the paired max_count bound is echoed"
    assert finding.offending_chapters == (5,), "chapter 5 is outside the allowed set"


def test_max_count_paired_within_count_but_outside_window_fails() -> None:
    """The pairing fails on the window alone even when ``max_count`` holds."""
    device = _device("sternum", r"sternum", _Ration(max_count=3, allowed_chapters=(1,)))
    # Two hits (within max_count=3) but in chapter 2 (outside allowed {1}).
    report = detect_ledger(
        _ledger(device), [ScannedChapter(number=2, text="sternum sternum")]
    )
    finding = _only(report)
    assert finding.count == 2, f"two hits expected, got {finding.count}"
    assert finding.passed is False, "window breach fails even within max_count"
    assert finding.offending_chapters == (2,), "chapter 2 is outside allowed {1}"


def test_count_recomputed_from_supplied_text() -> None:
    """The count is the literal hit total; removing a spend lowers it.

    Expresses the recompute-from-disk behaviour purely: the same device over two
    different chapter texts yields the hit total of each, with no cached count, so
    editing a draft to drop a spend drops the finding.
    """
    device = _device("bloom", r"bloom", _Ration(max_count=1))
    over = detect_ledger(
        _ledger(device), [ScannedChapter(number=1, text="bloom\nbloom")]
    )
    assert _only(over).count == 2, "two literal hits in the original text"
    assert _only(over).passed is False, "two hits over max_count 1 must fail"
    # Removing one spend (recompute over the edited text) drops below the ration.
    under = detect_ledger(_ledger(device), [ScannedChapter(number=1, text="bloom")])
    assert _only(under).count == 1, "one literal hit after the spend is removed"
    assert _only(under).passed is True, "one hit at max_count 1 must pass"


def test_clean_ledger_with_multiple_devices_passes() -> None:
    """A ledger whose every device is within ration passes overall."""
    ledger = _ledger(
        _device("bloom", r"bloom", _Ration(max_count=2)),
        _device("truth", r"truth", _Ration(retired_after_chapter=7)),
    )
    report = detect_ledger(
        ledger,
        [
            ScannedChapter(number=1, text="bloom\ntruth"),
            ScannedChapter(number=2, text="bloom"),
        ],
    )
    assert report.passed is True, "every device within ration passes overall"
    assert len(report.findings) == 2, "one finding per device"
    assert all(finding.passed for finding in report.findings), (
        "no device should fail in a clean ledger"
    )
