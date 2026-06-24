"""Unit tests for the stub console-script command surface.

The five stubs share one :func:`~novel_ralph_skill.commands.stub.make_stub_app`
factory, so these tests drive the factory's app in-process and pin every
argument path the roadmap success criterion and the Cyclopts parser carve-outs
require. The apps are driven directly (``app([...])`` inside a
``pytest.raises(SystemExit)`` guard) because ``cyclopts.testing.invoke`` does
not exist in the locked cyclopts 4.18.0.
"""

from __future__ import annotations

import sys
import typing as typ

import pytest

from novel_ralph_skill.commands import stub
from novel_ralph_skill.commands.names import COMMAND_ENTRY_POINTS, COMMAND_NAMES
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

# As of roadmap task 6.1.1 **all five** entry points drive their real Cyclopts
# apps: each resolves ``./working/state.toml`` and exits ``3`` (state error) when
# no ``working/`` is present, not the stub's ``2`` (Decision Log B6, D-TRIPWIRE).
# ``wordcount`` is the last promotion (task 6.1.1), joining ``novel-state``
# (2.1.2), ``desloppify`` (5.1.2), ``novel-compile`` (4.1.1), and ``novel-done``
# (3.1.1). Each command's own behaviour is pinned by its dedicated suite
# (``tests/test_novel_state_check.py``, ``tests/test_desloppify_command.py``,
# ``tests/test_compile_e2e.py``, ``tests/test_novel_done_command.py``,
# ``tests/test_wordcount_command.py``); ``test_entry_point_callable_drives_real_app``
# below asserts the shared property that every entry point is real.
_REAL_COMMANDS: frozenset[str] = frozenset({
    "novel-state",
    "desloppify",
    "novel-compile",
    "novel-done",
    "wordcount",
})
# Promoting ``wordcount`` makes ``_REAL_COMMANDS`` cover every registered name,
# so no entry point remains stubbed. The dual assertion lives in
# ``test_entry_point_callable_drives_real_app`` below, parametrized over **all**
# entry points and guarded by ``assert COMMAND_ENTRY_POINTS`` so the parametrize
# set can never silently empty (Decision Log D-TRIPWIRE). The ``_REAL_COMMANDS``
# set is retained as the documented expectation that every command is real; a
# future regression that demoted one would drop it from the set and the
# all-real assertion would fire.
assert COMMAND_ENTRY_POINTS, "the command registry must not be empty"
assert set(COMMAND_NAMES) <= _REAL_COMMANDS, "every command must be a real app"
ALL_ENTRY_POINTS: tuple[tuple[str, cabc.Callable[[], None]], ...] = tuple(
    (name, getattr(stub, func)) for name, func in COMMAND_ENTRY_POINTS.items()
)

# ``novel-state`` is a command-group app: a bare invocation with no subcommand
# prints help and exits 0, so it only resolves ``./working/state.toml`` (and
# reaches the exit-3 state-error path on an absent tree) when given a read-only
# subcommand. The other four commands carry a default body, so a bare invocation
# already drives their real path. This map supplies the extra argv token each
# command needs to reach its state-resolving path under an absent ``working/``.
_REAL_PATH_ARGV: dict[str, list[str]] = {"novel-state": ["check"]}


@pytest.mark.parametrize("name", COMMAND_NAMES)
@pytest.mark.parametrize("args", [[], ["foo"]], ids=["no-arg", "positional"])
def test_command_result_exits_two(
    name: str,
    args: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The no-arg and positional-token command results exit ``2``."""
    app = stub.make_stub_app(name)
    with pytest.raises(SystemExit) as excinfo:
        app(args, exit_on_error=False)
    assert excinfo.value.code == stub.STUB_EXIT_CODE
    captured = capsys.readouterr()
    assert name in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("name", COMMAND_NAMES)
def test_unknown_option_exits_one(name: str) -> None:
    """An unknown ``--option`` is rejected by the parser and exits ``1``.

    This carve-out is provisional until roadmap task 1.3.1 wires "bad arguments
    -> 2"; it pins the locked framework's current behaviour so a reader does
    not mistake the parser's exit ``1`` for a stub bug.
    """
    app = stub.make_stub_app(name)
    with pytest.raises(SystemExit) as excinfo:
        app(["--nope"])
    assert excinfo.value.code == 1


@pytest.mark.parametrize("name", COMMAND_NAMES)
@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_meta_flags_exit_zero(name: str, flag: str) -> None:
    """The ``--help`` and ``--version`` parser carve-outs each exit ``0``."""
    app = stub.make_stub_app(name)
    with pytest.raises(SystemExit) as excinfo:
        app([flag], exit_on_error=False)
    assert excinfo.value.code == 0


@pytest.mark.parametrize(
    "entry", ALL_ENTRY_POINTS, ids=[name for name, _ in ALL_ENTRY_POINTS]
)
def test_entry_point_callable_drives_real_app(
    entry: tuple[str, cabc.Callable[[], None]],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Every console-script callable drives a real app, not the stub (D-TRIPWIRE).

    ``wordcount`` was the last stub (roadmap task 6.1.1); promoting it empties the
    old "still-stubbed" set, so the previous "still-stubbed exits 2" parametrize
    would collect zero items and silently skip. This replacement asserts the dual:
    under a clean argv and a cwd with no ``working/``, each real callable resolves
    ``./working/state.toml``, finds it absent, and raises the exit-``3`` state-error
    path — never the stub's ``2``, never a stub greeting on stderr. This is the
    same real-callable behaviour ``tests/test_novel_state_check.py`` already pins
    for ``novel-state`` under an explicit ``chdir``.
    """
    name, entry_point = entry
    # An argv that reaches the command's state-resolving path (a read-only
    # subcommand for the ``novel-state`` command group, bare otherwise); chdir
    # into an empty tmp dir so ``./working/`` is absent and the real app takes its
    # state-error route rather than a stub message.
    monkeypatch.setattr(sys, "argv", [name, *_REAL_PATH_ARGV.get(name, [])])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        entry_point()
    assert excinfo.value.code == ExitCode.STATE_ERROR, (
        f"{name} must take the real exit-3 state-error path, got {excinfo.value.code}"
    )
    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.err, (
        f"{name} must not emit a stub greeting"
    )
    assert "Traceback" not in captured.err
    # The real apps emit their JSON envelope on stdout, never the stub's stderr.
    assert "not yet implemented" not in captured.out
