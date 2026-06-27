"""Hypothesis property coverage of the device-ledger loader and detector.

These generalise the example-based ledger tests (roadmap 7.1.2) over a range of
inputs, covering the invariants that *are* an invariant over a range of inputs.
Hypothesis is the right adversary here (per ``python-verification``): these are
ordering/range invariants over loader and detector inputs, not contract
counter-examples (CrossHair) or test-suite mutation gaps (mutmut).

* loader robustness — for any permutation of the worked-example devices fed
  through :func:`parse_ledger`, the ledger loads and every device's pattern
  compiles (drawn from the loaded device list, never synthesised regex);
* loader invariants restated as properties — every device carries at least one
  rationing field and at most one window constraint, and every present numeric
  bound is positive with ``allowed_chapters`` a non-empty positive tuple;
* detector invariants — for chapters synthesised from a strategy over a fixed
  chapter-number pool and device-bearing/clean lines, every ``LineHit.chapter``
  is one of the scanned chapters' numbers, and each finding's ``count`` equals
  the number of its ``lines`` (the count cannot drift from the per-hit list).

Every input comes from a strategy (no function-scoped fixtures, which would trip
``HealthCheck.function_scoped_fixture``); each property carries an explicit
bounded ``@settings`` and draws from data the ledger/chapters actually contain
(no arbitrary-regex synthesis), so the strategies stay inside the filtering trap.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import tomllib
import typing as typ

from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.ledger import parse_ledger
from novel_ralph_skill.ledger.detect import detect_ledger
from novel_ralph_skill.ledger.schema import Device, DeviceLedger
from novel_ralph_skill.loaderkit.scan import ScannedChapter

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# A decoded device entry and a whole ledger, as the strategies below build them.
type _DeviceMapping = dict[str, object]
type _LedgerMapping = dict[str, object]

_PROPERTY_SETTINGS = settings(
    max_examples=100,
    deadline=dt.timedelta(milliseconds=400),
)

# The four window keys that may not co-exist, plus the bare count, as decoded
# device fragments. Each fragment is a *valid* one-ration device body; drawing
# from this fixed set keeps every device well-formed by construction (no
# filtering) and every pattern trivially compilable.
_DEVICE_RATIONS: tuple[dict[str, object], ...] = (
    {"max_count": 3},
    {"max_count": 1},
    {"allowed_chapters": [1, 3, 8]},
    {"retired_after_chapter": 7},
    {"reserved_for_chapter": 12},
    {"max_count": 3, "allowed_chapters": [1, 3, 8]},
)
# Cheap-to-compile, always-valid pattern sources (no arbitrary regex synthesis).
_VALID_PATTERNS = ("sternum", r"\bbloom\b", "truth of the thing", "motif", r"a+b")

_device_ids = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=1,
    max_size=8,
)


@st.composite
def _well_formed_device(draw: st.DrawFn, *, device_id: str) -> _DeviceMapping:
    """Build one well-formed device mapping with the given ``id``.

    The ration is drawn from :data:`_DEVICE_RATIONS`, so the device carries
    exactly one valid ration combination by construction (no filtering).
    """
    device: _DeviceMapping = {
        "id": device_id,
        "pattern": draw(st.sampled_from(_VALID_PATTERNS)),
    }
    device.update(draw(st.sampled_from(_DEVICE_RATIONS)))
    return device


@st.composite
def _well_formed_ledger(draw: st.DrawFn) -> _LedgerMapping:
    """Build a well-formed device-ledger mapping with distinct device ids."""
    ids = draw(st.lists(_device_ids, min_size=1, max_size=6, unique=True))
    devices = [draw(_well_formed_device(device_id=device_id)) for device_id in ids]
    return {"schema_version": 1, "device": devices}


def _window_count(device: Device) -> int:
    """Return how many window constraints ``device`` carries (0 or 1)."""
    return sum(
        field is not None
        for field in (
            device.allowed_chapters,
            device.retired_after_chapter,
            device.reserved_for_chapter,
        )
    )


@given(raw=_well_formed_ledger())
@_PROPERTY_SETTINGS
def test_well_formed_ledgers_load_and_compile(raw: _LedgerMapping) -> None:
    """Every well-formed ledger parses and every device's pattern compiles."""
    ledger = parse_ledger(raw)
    devices = typ.cast("list[_DeviceMapping]", raw["device"])
    assert len(ledger.devices) == len(devices), "device count must round-trip"
    for parsed, source in zip(ledger.devices, devices, strict=True):
        assert parsed.id == source["id"], "device id must round-trip in order"
        # The compiled pattern is a usable, equivalent pattern object.
        assert isinstance(parsed.compiled, re.Pattern), "pattern must be compiled"
        assert parsed.compiled.pattern == parsed.pattern, "compiled echoes the source"


@given(raw=_well_formed_ledger())
@_PROPERTY_SETTINGS
def test_loaded_devices_satisfy_ration_invariants(raw: _LedgerMapping) -> None:
    """Every loaded device carries one+ ration, at most one window, positive bounds."""
    ledger = parse_ledger(raw)
    for device in ledger.devices:
        rations = (
            device.max_count,
            device.allowed_chapters,
            device.retired_after_chapter,
            device.reserved_for_chapter,
        )
        assert any(field is not None for field in rations), (
            f"device {device.id!r} must carry at least one ration"
        )
        assert _window_count(device) <= 1, (
            f"device {device.id!r} must carry at most one window constraint"
        )
        for bound in (
            device.max_count,
            device.retired_after_chapter,
            device.reserved_for_chapter,
        ):
            assert bound is None or bound > 0, (
                f"device {device.id!r} numeric bound must be positive"
            )
        if device.allowed_chapters is not None:
            assert device.allowed_chapters, "allowed_chapters must be non-empty"
            assert all(chapter > 0 for chapter in device.allowed_chapters), (
                "allowed_chapters must be positive"
            )


# A small fixed pool of chapter numbers the detector strategy draws from, so the
# "attributed chapter is a scanned chapter" property has a known universe.
_CHAPTER_POOL = (1, 2, 3, 5, 8, 12)


@st.composite
def _scanned_chapters(draw: st.DrawFn) -> list[ScannedChapter]:
    """Synthesise distinct-numbered chapters of device-bearing and clean lines.

    Each chapter's text mixes ``"motif"`` lines (which the property's device
    matches) and clean lines, so the hit count varies while every hit stays
    attributable to the chapter's number. Numbers are drawn unique from
    :data:`_CHAPTER_POOL` so the scanned set is well-defined.
    """
    numbers = draw(
        st.lists(st.sampled_from(_CHAPTER_POOL), min_size=1, max_size=4, unique=True)
    )
    lines_strategy = st.lists(
        st.sampled_from(("motif here", "a calm clean line", "motif and motif")),
        min_size=0,
        max_size=5,
    )
    return [
        ScannedChapter(number=number, text="\n".join(draw(lines_strategy)))
        for number in numbers
    ]


# A single bare ``max_count`` device matching the synthesised ``"motif"`` lines,
# shared by the two detector properties below.
_MOTIF_DEVICE = Device(
    id="motif",
    pattern="motif",
    compiled=re.compile(r"motif"),
    max_count=1,
    allowed_chapters=None,
    retired_after_chapter=None,
    reserved_for_chapter=None,
)


@given(chapters=_scanned_chapters())
@_PROPERTY_SETTINGS
def test_hits_attributed_to_scanned_chapters(
    chapters: cabc.Sequence[ScannedChapter],
) -> None:
    """Every hit's chapter is one of the scanned chapters' numbers."""
    ledger = DeviceLedger(schema_version=1, devices=(_MOTIF_DEVICE,))
    report = detect_ledger(ledger, chapters)
    scanned_numbers = {chapter.number for chapter in chapters}
    finding = report.findings[0]
    for hit in finding.lines:
        assert hit.chapter in scanned_numbers, (
            f"hit chapter {hit.chapter} is not a scanned chapter {scanned_numbers}"
        )


@given(chapters=_scanned_chapters())
@_PROPERTY_SETTINGS
def test_count_equals_hit_total(chapters: cabc.Sequence[ScannedChapter]) -> None:
    """Each finding's ``count`` equals the number of its per-hit ``lines``."""
    ledger = DeviceLedger(schema_version=1, devices=(_MOTIF_DEVICE,))
    report = detect_ledger(ledger, chapters)
    finding = report.findings[0]
    assert finding.count == len(finding.lines), (
        f"count {finding.count} must equal hit total {len(finding.lines)}"
    )


def _decode(path: pathlib.Path) -> _LedgerMapping:
    """Decode a TOML ledger file into its raw mapping."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _device_body(device: Device) -> _DeviceMapping:
    """Project a loaded :class:`Device` back into its decoded ``[[device]]`` body."""
    body: _DeviceMapping = {"id": device.id, "pattern": device.pattern}
    if device.max_count is not None:
        body["max_count"] = device.max_count
    if device.allowed_chapters is not None:
        body["allowed_chapters"] = list(device.allowed_chapters)
    if device.retired_after_chapter is not None:
        body["retired_after_chapter"] = device.retired_after_chapter
    if device.reserved_for_chapter is not None:
        body["reserved_for_chapter"] = device.reserved_for_chapter
    return body


# The worked-example ledger's device bodies, decoded once at import. The
# permutation property reorders these (drawing only an index permutation, never a
# synthesised regex), so it stays inside the data the ledger actually contains.
# The path is derived from ``__file__`` so collection does not depend on the
# current working directory (the ``@given`` decoration needs the device count at
# import time, so this read-only deterministic data is loaded at module scope).
_EXAMPLE_LEDGER_PATH = (
    pathlib.Path(__file__).resolve().parent
    / "data"
    / "ledgers"
    / "example-device-ledger.toml"
)
_EXAMPLE_DEVICES = parse_ledger(_decode(_EXAMPLE_LEDGER_PATH)).devices
_EXAMPLE_BODIES = [_device_body(device) for device in _EXAMPLE_DEVICES]
_EXAMPLE_IDS = frozenset(device.id for device in _EXAMPLE_DEVICES)


@given(order=st.permutations(range(len(_EXAMPLE_BODIES))))
@_PROPERTY_SETTINGS
def test_example_ledger_permutations_load(order: cabc.Sequence[int]) -> None:
    """Any permutation of the worked-example devices parses and compiles."""
    reordered = {
        "schema_version": 1,
        "device": [_EXAMPLE_BODIES[index] for index in order],
    }
    parsed = parse_ledger(reordered)
    assert {device.id for device in parsed.devices} == _EXAMPLE_IDS, (
        "every permutation loads the same device set"
    )
    for device in parsed.devices:
        assert device.compiled.pattern == device.pattern, "pattern compiles"
