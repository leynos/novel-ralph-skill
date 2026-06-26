"""Snapshot the ``set-gate`` success ``result`` payload (roadmap 2.2.4; syrupy).

Pins the write-shaped ``result`` of a representative ``--knitting-30`` repair
success — the mutator names what it changed and never echoes ``check``'s
``violations`` read shape (design §3.3; audit-2.2.2 Finding 2). The envelope
carries no timestamp, so the snapshot is the ``result`` mapping alone, paired with
a semantic assertion on the exit code (AGENTS.md "pair snapshots with semantic
assertions").
"""

from __future__ import annotations

import json
import typing as typ

import pytest
from _gate_drafting_fixtures import build, gate_lags_ratio_spec

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel state"


def test_set_gate_success_result_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """The ``--knitting-30`` repair success ``result`` matches the snapshot."""
    working = build(gate_lags_ratio_spec(), tmp_path)
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["set-gate", "--knitting-30"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    assert typ.cast("int", excinfo.value.code) == ExitCode.SUCCESS, (
        "the repair success must exit 0"
    )
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == snapshot, "the write-shaped result must match the snapshot"
