"""Snapshot tests for the ``desloppify --ledger`` envelope (roadmap 7.1.2).

These pin the *shape* of the ledger envelope for the boundary pair — a clean pass
and an over-ration device — while paired semantic assertions pin the *behaviour*
(exit code, ``violations`` membership), so the snapshot is never the only guard
(AGENTS.md "avoid snapshot-only coverage"), following
``tests/test_desloppify_snapshots.py``.

The ledger envelope is deterministic (no timestamp, no absolute path: the ledger
path is not echoed into ``result``), so nothing needs redacting; a volatile-field
guard pins that no timestamp or absolute path can silently churn the snapshot.
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel desloppify"

# A one-device ledger rationing ``sternum`` to two spends across the manuscript.
_LEDGER = """\
schema_version = 1

[[device]]
id = "sternum"
pattern = "\\\\bsternum\\\\b"
max_count = 2
"""

# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path, an ISO-8601 date, or a clock time.
_VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"
    r"|/[^/\"\s]+/"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}:\d{2}:\d{2}"
)


def _run_capture(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object]]:
    """Drive ``desloppify`` over ``argv`` and return ``(exit_code, envelope)``."""
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    raw = capsys.readouterr().out
    return int(typ.cast("int", excinfo.value.code)), json.loads(raw)


def _write_all_drafts(working: Path, text: str) -> None:
    """Write ``text`` to every existing chapter ``draft.md`` under ``working``."""
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text(text, encoding="utf-8")


def _first_chapter_dir(working: Path) -> Path:
    """Return the lowest-numbered ``chapter-NN`` directory under ``working``."""
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "baseline tree must contain at least one chapter directory"
    return chapters[0]


def _ledger_at(tmp_path: Path) -> str:
    """Write the test ledger under ``tmp_path`` and return its path."""
    ledger = tmp_path / "device-ledger.toml"
    ledger.write_text(_LEDGER, encoding="utf-8")
    return str(ledger)


def _assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path."""
    rendered = json.dumps(envelope)
    match = _VOLATILE_PATTERN.search(rendered)
    assert match is None, (
        f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        if match is not None
        else ""
    )
    # Match each volatile name as a JSON *key* (``"name":``) rather than a bare
    # substring, so a legitimate human message such as "spent 3 times" does not
    # trip the ``time`` guard.
    for key in ("timestamp", "created_at", "now", "time"):
        assert f'"{key}":' not in rendered, f"unexpected volatile key {key!r}"


def test_clean_ledger_envelope_snapshot(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """A within-ration scan snapshots ``ok: true`` with empty violations at exit 0."""
    working = baseline_tree()
    _write_all_drafts(working, "a plain calm line\n")
    _first_chapter_dir(working).joinpath("draft.md").write_text(
        "sternum\nsternum\n", encoding="utf-8"
    )
    ledger = _ledger_at(working.parent)
    monkeypatch.chdir(working.parent)
    code, envelope = _run_capture(["--ledger", ledger], capsys)
    assert code == ExitCode.SUCCESS, "a within-ration scan must exit 0"
    assert envelope["ok"] is True, "a clean ledger envelope reports ok=True"
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["violations"] == [], "a clean ledger has no violations"
    # The ledger path obeys the same clean-pass findings contract as the
    # rule-pack path (roadmap 7.1.3): a within-ration scan slims its trail to
    # the over-ration devices, so the sole passing ``sternum`` device drops out
    # and the findings list is empty.
    assert result["findings"] == [], "a within-ration ledger slims to no findings"
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot, "the clean ledger envelope shape must match"


def test_over_ration_envelope_snapshot(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """An over-ration device snapshots ``ok: false`` naming it at exit ``4``."""
    working = baseline_tree()
    _write_all_drafts(working, "a plain calm line\n")
    # Three "sternum" over max_count 2 is exactly one spend past the ration.
    _first_chapter_dir(working).joinpath("draft.md").write_text(
        "sternum\nsternum\nsternum\n", encoding="utf-8"
    )
    ledger = _ledger_at(working.parent)
    monkeypatch.chdir(working.parent)
    code, envelope = _run_capture(["--ledger", ledger], capsys)
    assert code == ExitCode.ACTIONABLE_FINDING, "an over-ration scan must exit 4"
    assert envelope["ok"] is False, "an over-ration envelope reports ok=False"
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["violations"] == ["sternum"], "the over-ration device is named"
    findings = typ.cast("list[dict[str, object]]", result["findings"])
    sternum = next(f for f in findings if f["device_id"] == "sternum")
    assert sternum["count"] == 3, "the recomputed spend is three hits"
    assert sternum["passed"] is False, "the over-ration device fails"
    lines = typ.cast("list[dict[str, int]]", sternum["lines"])
    keys = [(hit["chapter"], hit["line"]) for hit in lines]
    assert keys == sorted(keys), f"lines not in (chapter, line) order: {keys}"
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot, "the over-ration envelope shape must match"
