"""Command-contract tests for ``novel-state complete-final-pass`` (roadmap 2.2.4).

``complete-final-pass`` is the zero-argument convenience verb that flips
``[gates.final].final_pass_complete`` true (``set-gate --final`` is the general
form). The final gate has no §5.2 binding, so the flip is accepted on any
structurally complete prior and is idempotent. A missing or structurally
incomplete ``state.toml`` is the exit-``3`` state channel.

Each invocation is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, so the externally
observable exit code and envelope are what these tests assert.
"""

from __future__ import annotations

import json
import tomllib
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "novel-state"


def _run(
    working: Path,
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict[str, object]]:
    """Drive ``argv`` from ``working.parent``; return ``(exit_code, envelope)``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    return code, json.loads(capsys.readouterr().out)


def _final_pass(working: Path) -> bool:
    """Return the on-disk ``[gates.final].final_pass_complete`` boolean."""
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    return typ.cast("bool", raw["gates"]["final"]["final_pass_complete"])


def test_complete_final_pass_flips_gate_and_check_stays_coherent(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``complete-final-pass`` exits 0, writes the gate true, and check stays 0."""
    working = phase_state_tree("final-pass")
    assert _final_pass(working) is False, "the final-pass tree starts with the gate off"
    code, envelope = _run(working, ["complete-final-pass"], monkeypatch, capsys)
    assert code == ExitCode.SUCCESS, "the flip must exit 0"
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"gates": {"final": {"final_pass_complete": True}}}, (
        "the result must name only the changed final gate"
    )
    assert _final_pass(working) is True, "final_pass_complete must be written true"
    check_code, check_env = _run(working, ["check"], monkeypatch, capsys)
    assert check_code == ExitCode.SUCCESS, "check must stay coherent after the flip"
    assert check_env["ok"] is True, "the post-flip check envelope must be ok"


def test_complete_final_pass_is_idempotent(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A second ``complete-final-pass`` re-writes the same value and exits 0."""
    working = phase_state_tree("final-pass")
    _run(working, ["complete-final-pass"], monkeypatch, capsys)
    code, _ = _run(working, ["complete-final-pass"], monkeypatch, capsys)
    assert code == ExitCode.SUCCESS, "re-running on a true gate must exit 0"
    assert _final_pass(working) is True, "final_pass_complete must stay true"


def test_complete_final_pass_missing_state_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing ``working/state.toml`` is the exit-3 state channel."""
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["complete-final-pass"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    envelope = json.loads(capsys.readouterr().out)
    assert code == ExitCode.STATE_ERROR, "a missing state.toml must exit 3"
    assert envelope["ok"] is False, "the state-error envelope must be ok: false"


def test_incomplete_state_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A structurally incomplete ``state.toml`` is the exit-3 state channel."""
    working = wc.build_working_tree(wc.PHASE_STATES["final-pass"], tmp_path)
    # Strip the [gates] table so the document parses but the view derivation fails.
    raw = (working / "state.toml").read_text("utf-8")
    truncated = raw.split("[gates", maxsplit=1)[0]
    (working / "state.toml").write_text(truncated, encoding="utf-8")
    code, envelope = _run(working, ["complete-final-pass"], monkeypatch, capsys)
    assert code == ExitCode.STATE_ERROR, "an incomplete state.toml must exit 3"
    assert envelope["ok"] is False, "the state-error envelope must be ok: false"
