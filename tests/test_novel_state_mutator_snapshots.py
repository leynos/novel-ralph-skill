"""Machine-mode envelope snapshots for the ``novel-state`` mutators (roadmap 2.2.2).

These pin the rendered machine-mode JSON envelope for each mutator's success and
refusal paths (design §9 "Snapshot tests pin the machine-mode JSON envelope per
command"). Nondeterministic fields are normalised so a snapshot identifies a real
contract change, not churn: the ``created_at`` timestamp ``init`` stamps is
redacted, and the envelope carries no absolute path (``working_dir`` is the fixed
``"working"`` token). Each snapshot is paired with a semantic assertion on the
exit code and the envelope ``ok`` so the snapshot is not the only guard (AGENTS.md
"pair them with semantic assertions").
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec
    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel-state"
# Redact the RFC 3339 timestamp ``init`` stamps into ``[novel].created_at`` (it
# never reaches the envelope today, but normalise defensively per AGENTS.md).
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?"
)


def _drive(argv: list[str]) -> tuple[int, str]:
    """Run ``argv`` through ``run`` and return ``(exit_code, raw_stdout)``."""
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _normalise(raw: str) -> str:
    """Redact nondeterministic fields from the rendered envelope."""
    return _TIMESTAMP.sub("<timestamp>", raw)


def test_init_success_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``init``'s success envelope (exit ``0``, ``ok: true``)."""
    monkeypatch.chdir(tmp_path)
    code, raw = _drive(["init", "--title", "T", "--slug", "s"])
    assert code == ExitCode.SUCCESS
    assert json.loads(raw)["ok"] is True
    assert _normalise(raw) == snapshot


def test_set_cursor_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-cursor``'s success envelope: ``result`` is the cursor it set."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names the cursor and carries no ``violations``
    # read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"current_chapter": 2, "current_scene": 0, "current_beat": 0}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_set_cursor_refusal_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-cursor``'s refusal envelope (exit ``3``, ``ok: false``)."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-cursor", "--chapter", "99"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot


def test_advance_phase_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``advance-phase``'s success envelope: ``result`` names the transition."""
    working = phase_state_tree("premise")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["advance-phase"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names the transition and carries no
    # ``violations`` read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"from": "premise", "to": "treatment"}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_advance_phase_refusal_envelope_snapshot(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``advance-phase``'s out-of-order refusal envelope (exit ``3``)."""
    _spec, working, _expected = incoherent_tree("completed-prefix-gap")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["advance-phase"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot
