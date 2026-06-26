"""Snapshot and human-mode tests for the ``novel-done`` envelope (roadmap 3.1.1).

These complete design §9's coverage for ``novel-done``: snapshot the machine-mode
JSON envelope for the boundary pair design §4.2 names — the all-six-clauses-hold
tree (exit ``0``) and a one-clause-fails tree (exit ``1``) — and pair each
snapshot with semantic per-clause assertions so the snapshot is never the only
guard (AGENTS.md "avoid snapshot-only coverage"), following
``tests/test_desloppify_snapshots.py``. A human-mode presence test asserts
``--human`` renders without error and names the failed clauses (the §2.3 "human
mode asserted for presence" rule).

The corpus uses a fixed ``created_at`` and ``novel-done`` emits no timestamps or
paths beyond the fixed ``working`` constant, so nothing nondeterministic needs
redacting; a guard asserts no volatile field can silently churn the snapshot.
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest

from novel_ralph_skill.commands._novel_done import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion
    from working_corpus import WorkingTreeSpec

_COMMAND = "novel done"
_CLAUSE_KEYS: tuple[str, ...] = (
    "phase_is_done",
    "final_pass_complete",
    "all_chapters_flagged",
    "knitting_gates_passed",
    "compile_consistent",
    "no_unresolved_blockers",
)

# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path, an ISO-8601 date, or a clock time. Mirrors the desloppify snapshot guard.
_VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"
    r"|/[^/\"\s]+/"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}:\d{2}:\d{2}"
)


def _run_capture(
    working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    human: bool = False,
) -> tuple[int, dict[str, object]]:
    """Drive ``novel-done`` from ``working.parent``; return ``(code, envelope)``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command=_COMMAND, working_dir="working", human=human),
        )
    return int(typ.cast("int", excinfo.value.code)), json.loads(capsys.readouterr().out)


def _assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path."""
    rendered = json.dumps(envelope)
    match = _VOLATILE_PATTERN.search(rendered)
    assert match is None, (
        f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        if match is not None
        else ""
    )
    for key in ("timestamp", "created_at", "now", "time"):
        assert key not in rendered, f"unexpected volatile key {key!r} in envelope"


def test_all_hold_envelope_snapshot(
    all_hold_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """The all-hold tree snapshots ``ok: true`` with every clause true at exit ``0``."""
    code, envelope = _run_capture(all_hold_tree(), monkeypatch, capsys)
    assert code == ExitCode.SUCCESS
    assert envelope["ok"] is True
    result = typ.cast("dict[str, object]", envelope["result"])
    assert tuple(result) == _CLAUSE_KEYS
    assert all(value is True for value in result.values())
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


def test_one_clause_fails_envelope_snapshot(
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """A phase-not-done tree snapshots ``ok: false`` at exit ``1``."""
    _spec, working = done_predicate_failer_tree("phase_is_done")
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert tuple(result) == _CLAUSE_KEYS
    assert result["phase_is_done"] is False
    # Only the one toggled clause is false; the other five still hold.
    assert sum(1 for value in result.values() if value is False) == 1
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


def test_sole_stale_compile_envelope_snapshot(
    sole_stale_compile_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """The sole-stale-compile tree snapshots ``ok: false`` at exit ``4`` (3.1.2)."""
    code, envelope = _run_capture(sole_stale_compile_tree(), monkeypatch, capsys)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert tuple(result) == _CLAUSE_KEYS
    assert result["compile_consistent"] is False
    # Only ``compile_consistent`` is false; the other five still hold.
    assert sum(1 for value in result.values() if value is False) == 1
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


def _run_human(
    working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    """Drive ``novel-done --human`` from ``working.parent``; return ``(code, out)``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command=_COMMAND, working_dir="working", human=True),
        )
    return int(typ.cast("int", excinfo.value.code)), capsys.readouterr().out


def test_human_mode_names_failed_clause(
    sole_stale_compile_tree: cabc.Callable[[], Path],
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--human`` names the stale compile at exit ``4`` and the missing one at ``1``.

    Over the stale-present tree ``--human`` renders without error, exits ``4``,
    and names the stale compile; over the absent-compile sole-failure tree it
    renders without error, exits ``1``, and reports the compile *missing* rather
    than stale, so the carve-out boundary is not misleading (A-4; ADR-003).
    """
    code, rendered = _run_human(sole_stale_compile_tree(), monkeypatch, capsys)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert rendered.strip(), "human mode must render a non-empty report"
    assert "compile_consistent" in rendered
    assert "stale" in rendered

    _spec, absent = done_predicate_failer_tree("compile_consistent")
    assert not (absent / "manuscript" / "compiled.md").exists()
    code, rendered = _run_human(absent, monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    assert "compile_consistent" in rendered
    assert "missing" in rendered
