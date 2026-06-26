"""Step definitions for the cross-class actionable exit-3 message scenario.

These drive one command of each class — a mutator (``novel state recount``), a
checker (``novel state check``), and a reader (``novel wordcount``) — from a
directory with no ``working/`` tree, and assert the roadmap §6.3.1 success
criterion: each exits ``3`` with an actionable message that names the current
directory and the ``novel state init`` remedy, carries no raw ``Errno`` or
traceback, and is byte-for-byte identical across the three classes (proving both
load boundaries route through the one shared helper).

The commands are driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the surface
matrix does, so the externally observable exit code and rendered envelope are
what the scenario asserts. Each runner ``chdir``s into the prepared empty
directory first, because every command resolves a cwd-relative
``working/state.toml``.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_state_input_message_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

import pytest
from pytest_bdd import given, then, when

from novel_ralph_skill.commands import _wordcount, novel_state
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts


@dc.dataclass(frozen=True, slots=True)
class _CommandClass:
    """One command class to exercise: its label, console name, factory, and argv."""

    label: str
    command: str
    build_app: cabc.Callable[[], cyclopts.App]
    argv: list[str]


# The three command classes the success criterion names: a mutator (``recount``),
# a checker (``check``), and a reader (``wordcount``). The trio crosses both load
# boundaries — ``check``/``wordcount`` through the reader loader and ``recount``
# through the mutator loader — so an identical message across them proves the two
# boundaries share one helper.
_COMMANDS: tuple[_CommandClass, ...] = (
    _CommandClass("mutator", "novel state", novel_state.build_app, ["recount"]),
    _CommandClass("checker", "novel state", novel_state.build_app, ["check"]),
    _CommandClass("reader", "novel wordcount", _wordcount.build_app, []),
)


@dc.dataclass(slots=True)
class _CrossClassOutcome:
    """The empty working directory and the per-class exit codes and messages."""

    directory: Path
    results: dict[str, tuple[int, tuple[str, ...]]] = dc.field(default_factory=dict)


def _run_command(
    klass: _CommandClass,
    directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, tuple[str, ...]]:
    """Drive one command from ``directory`` via ``run``; return code and messages."""
    monkeypatch.chdir(directory)
    with pytest.raises(SystemExit) as excinfo:
        run(
            klass.build_app(),
            klass.argv,
            RunContext(command=klass.command, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    envelope = json.loads(capsys.readouterr().out or "{}")
    return code, tuple(envelope.get("messages", ()))


@given(
    "a directory with no novel working/ tree",
    target_fixture="outcome",
)
def empty_directory(tmp_path: Path) -> _CrossClassOutcome:
    """Return a freshly created directory that carries no ``working/`` subtree.

    Returns
    -------
    _CrossClassOutcome
        The empty directory; the per-class results are filled in by the run step.
    """
    return _CrossClassOutcome(directory=tmp_path)


@when("the mutator, the checker, and the reader each run from that directory")
def run_each_class(
    outcome: _CrossClassOutcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive each command class from the empty directory, capturing code and prose."""
    for klass in _COMMANDS:
        outcome.results[klass.label] = _run_command(
            klass, outcome.directory, monkeypatch, capsys
        )


@then("each command exits 3")
def asserts_each_exits_three(outcome: _CrossClassOutcome) -> None:
    """Assert every command class exited ``3`` (the state-input channel)."""
    for label, (code, _messages) in outcome.results.items():
        assert code == ExitCode.STATE_ERROR, f"the {label} should exit 3, got {code}"


@then("each message names the current directory and the 'novel state init' remedy")
def asserts_actionable(outcome: _CrossClassOutcome) -> None:
    """Assert each class's message names the cwd and the ``novel state init`` remedy."""
    cwd = str(outcome.directory)
    for label, (_code, messages) in outcome.results.items():
        text = "\n".join(messages)
        assert cwd in text, f"the {label} message must name the cwd; got {messages!r}"
        assert "working/" in text, f"the {label} message must name working/"
        assert "novel state init" in text, (
            f"the {label} message must offer the init remedy; got {messages!r}"
        )


@then("no message contains a raw Errno or a traceback")
def asserts_no_noise(outcome: _CrossClassOutcome) -> None:
    """Assert no class's message leaks a raw ``Errno`` or a traceback marker."""
    for label, (_code, messages) in outcome.results.items():
        text = "\n".join(messages)
        assert "Errno" not in text, f"the {label} message must not leak an Errno"
        assert "Traceback" not in text, f"the {label} message must not leak a traceback"


@then("the message is identical across the mutator, the checker, and the reader")
def asserts_identical(outcome: _CrossClassOutcome) -> None:
    """Assert the message text is byte-for-byte identical across the three classes."""
    messages = {label: result[1] for label, result in outcome.results.items()}
    distinct = set(messages.values())
    assert len(distinct) == 1, (
        f"all classes must emit identical prose; got {messages!r}"
    )
