"""Command-contract tests for ``novel-state set-gate`` (roadmap 2.2.4).

``set-gate`` is the repair mutator for a knitting gate that lags its drafted
ratio (ExecPlan Decision D4; design §5.2 invariant 7). Following the ``set-cursor``
skeleton, it refuses no incoherent prior — it validates only the *proposed* state —
so the observable, validator-permitted transition is the incoherent→coherent
repair (a gate the ratio has crossed but the boolean still lags). A gate set that
contradicts the ratio (true below threshold, or false once crossed) is refused
with exit ``3`` and writes nothing; a no-flag invocation is a usage error (exit
``2``); ``--final`` has no §5.2 binding.

The refusal cases are pinned first (the load-bearing Constraint). Each mutator is
driven through the shared :func:`novel_ralph_skill.contract.runner.run` wrapper, so
the externally observable exit code and envelope are what these tests assert.
"""

from __future__ import annotations

import json
import tomllib
import typing as typ

import pytest
from _gate_drafting_fixtures import (
    build,
    gate_lags_ratio_spec,
    ratio_crossed_coherent_spec,
    ratio_not_crossed_spec,
)

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel state"


def _run(
    working: Path,
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict[str, object]]:
    """Drive ``argv`` and return ``(exit_code, envelope)`` read from ``capsys``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    return code, json.loads(capsys.readouterr().out)


def _read_gate(working: Path, key: str) -> bool:
    """Return the ``[gates.knitting]`` boolean ``key`` from the on-disk state."""
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    return typ.cast("bool", raw["gates"]["knitting"][key])


def test_set_gate_refuses_gate_true_below_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Asserting a knitting gate true below its ratio is refused with exit 3."""
    working = build(ratio_not_crossed_spec(), tmp_path)
    before = (working / "state.toml").read_bytes()
    code, envelope = _run(working, ["set-gate", "--knitting-30"], monkeypatch, capsys)
    assert code == ExitCode.STATE_ERROR, "a gate true below threshold must exit 3"
    assert envelope["ok"] is False, "a refusal envelope must be ok: false"
    messages = typ.cast("list[str]", envelope["messages"])
    assert any("gate-ratio-consistent" in message for message in messages), (
        "the refusal must name the breached gate-ratio-consistent invariant"
    )
    assert (working / "state.toml").read_bytes() == before, (
        "a refused set must leave state.toml unchanged"
    )


def test_set_gate_refuses_gate_false_after_crossed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Asserting a knitting gate false once its ratio has crossed exits 3."""
    working = build(ratio_crossed_coherent_spec(), tmp_path)
    before = (working / "state.toml").read_bytes()
    code, envelope = _run(
        working, ["set-gate", "--no-knitting-30"], monkeypatch, capsys
    )
    assert code == ExitCode.STATE_ERROR, "a gate false after crossing must exit 3"
    assert envelope["ok"] is False, "a refusal envelope must be ok: false"
    assert (working / "state.toml").read_bytes() == before, (
        "a refused set must leave state.toml unchanged"
    )


def test_set_gate_repairs_gate_that_lags_ratio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The repair happy path: ``--knitting-30`` flips a lagging gate; check stays 0."""
    working = build(gate_lags_ratio_spec(), tmp_path)
    code, envelope = _run(working, ["set-gate", "--knitting-30"], monkeypatch, capsys)
    assert code == ExitCode.SUCCESS, "the repair flip must exit 0"
    assert envelope["ok"] is True, "the repair envelope must be ok"
    result = typ.cast("dict[str, object]", envelope["result"])
    gates = typ.cast("dict[str, object]", result["gates"])
    assert gates == {"knitting": {"done_30": True}}, (
        "the result must name only the changed done_30 gate"
    )
    assert _read_gate(working, "done_30") is True, "done_30 must be written true"
    check_code, check_env = _run(working, ["check"], monkeypatch, capsys)
    assert check_code == ExitCode.SUCCESS, "check must stay coherent after the repair"
    assert check_env["ok"] is True, "the post-repair check envelope must be ok"


def test_set_gate_idempotent_no_op_on_coherent_prior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Re-asserting an already-true gate exits 0 and re-writes the same value."""
    working = build(ratio_crossed_coherent_spec(), tmp_path)
    code, envelope = _run(working, ["set-gate", "--knitting-30"], monkeypatch, capsys)
    assert code == ExitCode.SUCCESS, "re-asserting an already-true gate must exit 0"
    assert envelope["ok"] is True, "the idempotent re-assertion envelope must be ok"
    assert _read_gate(working, "done_30") is True, "done_30 must stay true"


def test_set_gate_final_flag_flips_final_pass_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--final`` flips ``final_pass_complete`` true; ``check`` stays coherent."""
    working = build(ratio_crossed_coherent_spec(), tmp_path)
    code, envelope = _run(working, ["set-gate", "--final"], monkeypatch, capsys)
    assert code == ExitCode.SUCCESS, "--final has no §5.2 binding and must exit 0"
    result = typ.cast("dict[str, object]", envelope["result"])
    gates = typ.cast("dict[str, object]", result["gates"])
    assert gates == {"final": {"final_pass_complete": True}}, (
        "the result must name only the changed final gate"
    )
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    assert raw["gates"]["final"]["final_pass_complete"] is True, (
        "final_pass_complete must be written true"
    )
    check_code, check_env = _run(working, ["check"], monkeypatch, capsys)
    assert check_code == ExitCode.SUCCESS, "check must stay coherent after --final"
    assert check_env["ok"] is True, "the post-final check envelope must be ok"


def test_set_gate_no_flag_is_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A no-flag ``set-gate`` exits 2 (usage) with a clean envelope, file unchanged.

    Drives the real :func:`run` and asserts the emitted exit-2 envelope (``ok``
    false, the no-flag message, no traceback), proving the
    ``GateDraftingUsageError`` + ``_set_gate_or_usage`` adapter produces the clean
    exit-2 envelope rather than crashing the runner (ExecPlan B5; Surprise S3).
    """
    working = build(gate_lags_ratio_spec(), tmp_path)
    before = (working / "state.toml").read_bytes()
    code, envelope = _run(working, ["set-gate"], monkeypatch, capsys)
    assert code == ExitCode.USAGE_ERROR, "a no-flag set-gate must exit 2 (usage)"
    assert envelope["ok"] is False, "a usage-error envelope must be ok: false"
    assert envelope["result"] == {}, "a usage error carries an empty result"
    messages = typ.cast("list[str]", envelope["messages"])
    assert any("at least one flag" in message for message in messages), (
        "the usage envelope must carry the no-flag message"
    )
    assert (working / "state.toml").read_bytes() == before, (
        "a usage error must leave state.toml unchanged"
    )
