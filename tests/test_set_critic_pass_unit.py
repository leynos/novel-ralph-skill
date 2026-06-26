"""Command-contract tests for ``novel-state set-critic-pass`` (roadmap 2.2.4).

``set-critic-pass`` sets the on-disk ``[drafting.critic].pass`` key (the typed
attribute is ``CriticState.pass_number``; the schema renames it because ``pass``
is a Python keyword) under a write-time precondition the §5.2 validator does not
own (Decision D6; ADR 008 precedent): ``pass >= 1`` (passes are numbered from 1).
A ``pass >= 1`` set exits ``0`` and ``check`` stays coherent — the §5.2 critic
sub-rules bound ``consecutive_clean``/``convergence_target``, not ``pass``; a
``pass < 1`` set is refused with exit ``3`` naming the precondition, file
unchanged. A non-integer ``--pass`` faults at parse with exit ``2``.

Each invocation is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, so the externally
observable exit code and envelope are what these tests assert.
"""

from __future__ import annotations

import json
import tomllib
import typing as typ

import pytest

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


def _critic_pass(working: Path) -> int:
    """Return the on-disk ``[drafting.critic].pass`` value."""
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    return typ.cast("int", raw["drafting"]["critic"]["pass"])


def test_set_critic_pass_writes_and_stays_coherent(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``set-critic-pass --pass 2`` exits 0, writes ``pass = 2``, check stays 0."""
    working = phase_state_tree("drafting")
    code, envelope = _run(
        working, ["set-critic-pass", "--pass", "2"], monkeypatch, capsys
    )
    assert code == ExitCode.SUCCESS, "--pass 2 must exit 0"
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"drafting": {"critic": {"pass": 2}}}, (
        "the result must name only the changed critic pass"
    )
    assert _critic_pass(working) == 2, "the pass must be written verbatim"
    check_code, check_env = _run(working, ["check"], monkeypatch, capsys)
    assert check_code == ExitCode.SUCCESS, "check must stay coherent after the set"
    assert check_env["ok"] is True, "the post-set check envelope must be ok"


@pytest.mark.parametrize("value", [0, -1])
def test_set_critic_pass_below_one_exits_three(
    value: int,
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``pass < 1`` set is refused with exit 3 naming the precondition."""
    working = phase_state_tree("drafting")
    before = (working / "state.toml").read_bytes()
    code, envelope = _run(
        working, ["set-critic-pass", "--pass", str(value)], monkeypatch, capsys
    )
    assert code == ExitCode.STATE_ERROR, f"--pass {value} must exit 3"
    assert envelope["ok"] is False, "a refusal envelope must be ok: false"
    messages = typ.cast("list[str]", envelope["messages"])
    assert any("critic-pass-at-least-one" in message for message in messages), (
        "the refusal must name the breached precondition"
    )
    assert (working / "state.toml").read_bytes() == before, (
        "a refused set must leave state.toml unchanged"
    )


def test_set_critic_pass_non_integer_exits_two(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-integer ``--pass`` faults at parse with exit 2 (usage)."""
    working = phase_state_tree("drafting")
    before = (working / "state.toml").read_bytes()
    code, envelope = _run(
        working, ["set-critic-pass", "--pass", "notanumber"], monkeypatch, capsys
    )
    assert code == ExitCode.USAGE_ERROR, "a non-integer --pass must exit 2 (usage)"
    assert envelope["ok"] is False, "a usage-error envelope must be ok: false"
    assert (working / "state.toml").read_bytes() == before, (
        "a parse fault must leave state.toml unchanged"
    )
