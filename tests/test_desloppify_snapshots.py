"""Snapshot and ordering tests for the ``desloppify`` envelope (roadmap 5.1.2).

These complete design §9's coverage for ``desloppify``: snapshot the machine-mode
JSON envelope for the boundary pair design §9 names — a clean pass and a
manuscript with exactly one rule one hit past threshold — and pair each snapshot
with semantic assertions so the snapshot is never the only guard (AGENTS.md
"avoid snapshot-only coverage"), following
``tests/test_contract_envelope_snapshots.py``.

The semantic assertions pin the round-1 advisories: ``result.findings[].basis``
is a ``str`` (not a raw ``RuleBasis`` member); the envelope carries no timestamp
or absolute path that could churn the snapshot; and the ``lines`` list is in
deterministic ``(chapter, line)`` order.
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


# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path (a leading-slash or ``/segment/`` run, so an incidental single slash in a
# future rule id, pack name, or message does not trip the guard), an ISO-8601
# date (``2026-06-24``), or a clock time (``12:34:56``).
_VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"  # absolute path: a leading slash then a segment
    r"|/[^/\"\s]+/"  # or a ``/segment/`` run inside a longer path
    r"|\d{4}-\d{2}-\d{2}"  # ISO-8601 date
    r"|\d{2}:\d{2}:\d{2}"  # clock time
)


def _assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path.

    Pins the invariant that nothing volatile can silently churn the snapshot, so
    a future field addition that introduces one fails here rather than in review.
    The ``working_dir`` is the fixed ``working`` constant; no other field carries
    an absolute path, and there are no timestamps in this envelope. The guard
    matches absolute-path and timestamp *shapes* rather than a bare slash, so a
    future rule id, pack name, or message that legitimately carries one slash
    does not fail spuriously (addendum 5.1.2.2).
    """
    rendered = json.dumps(envelope)
    match = _VOLATILE_PATTERN.search(rendered)
    assert match is None, (
        f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        if match is not None
        else ""
    )
    for key in ("timestamp", "created_at", "now", "time"):
        assert key not in rendered, f"unexpected volatile key {key!r} in envelope"


def test_clean_pass_envelope_snapshot(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """A clean scan snapshots ``ok: true`` with empty violations at exit ``0``."""
    working = baseline_tree()
    _write_all_drafts(working, "A calm sentence with plain words.\n")
    monkeypatch.chdir(working.parent)
    code, envelope = _run_capture([], capsys)
    # Semantic guards paired with the snapshot.
    assert code == ExitCode.SUCCESS
    assert envelope["ok"] is True
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["violations"] == []
    # The clean-pass findings contract (roadmap 7.1.3, developers' guide):
    # a clean scan slims its audit trail to the over-threshold rules, so a
    # slop-free manuscript emits an empty findings list. This explicit guard is
    # load-bearing: the basis-type loop below is a no-op once findings is empty.
    findings = typ.cast("list[dict[str, object]]", result["findings"])
    assert findings == []
    for finding in findings:
        assert isinstance(finding["basis"], str), "basis must serialise as a str"
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


def test_one_hit_past_threshold_envelope_snapshot(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """One rule one hit past a zero threshold snapshots ``ok: false`` at exit ``4``.

    ``smirked`` has threshold 1, so a single use over a single-chapter scope is
    exactly one hit past its threshold — the design §9 boundary example.
    """
    working = baseline_tree()
    _write_all_drafts(working, "plain words only\n")
    first = min((working / "manuscript").glob("chapter-*"))
    # Two "smirked" over threshold 1 is exactly one hit past threshold.
    first.joinpath("draft.md").write_text(
        "He smirked once.\nShe smirked again.\n", encoding="utf-8"
    )
    monkeypatch.chdir(working.parent)
    number = int(first.name.removeprefix("chapter-"))
    code, envelope = _run_capture(["--chapter", str(number)], capsys)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["violations"] == ["smirked"]
    findings = typ.cast("list[dict[str, object]]", result["findings"])
    # Slimmed trail: only the single over-threshold rule survives (roadmap
    # 7.1.3), so the findings list is exactly the one failing ``smirked`` entry
    # with no passing rules alongside it.
    assert len(findings) == 1
    smirked = next(f for f in findings if f["rule_id"] == "smirked")
    assert isinstance(smirked["basis"], str), "basis must serialise as a str"
    # The enumerated per-hit ``phrase`` (design §4.4) carries the rule's pattern.
    assert smirked["phrase"], "each finding must emit the offender phrase"
    assert isinstance(smirked["phrase"], str), "phrase must serialise as a str"
    lines = typ.cast("list[dict[str, int]]", smirked["lines"])
    # Lines are in deterministic ascending (chapter, line) order.
    keys = [(hit["chapter"], hit["line"]) for hit in lines]
    assert keys == sorted(keys), f"lines not in (chapter, line) order: {keys}"
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot
