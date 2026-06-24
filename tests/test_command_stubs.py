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

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# ``novel-state`` is excluded: its entry point now drives the real app, which
# resolves ``./working/state.toml`` and exits ``3`` (state error) when no
# ``working/`` is present, not the stub's ``2`` (Decision Log B6). The four
# still-stubbed entry points keep the exit-``2`` contract; the real
# ``novel-state`` callable is driven only by ``tests/test_novel_state_check.py``,
# always under an explicit ``monkeypatch.chdir`` (advisory A6).
# ``desloppify`` now drives its real app too (roadmap task 5.1.2): it resolves
# ``./working/`` and exits per its own contract, not the stub's ``2``. It is
# covered by ``tests/test_desloppify_command.py``. ``novel-compile`` (roadmap task
# 4.1.1) likewise drives a real app and is covered by ``tests/test_compile_e2e.py``;
# the two remaining scripts (``novel-done``, ``wordcount``) keep the exit-``2``
# stub contract here.
_REAL_COMMANDS: frozenset[str] = frozenset({
    "novel-state",
    "desloppify",
    "novel-compile",
})
STILL_STUBBED_ENTRY_POINTS: tuple[tuple[str, cabc.Callable[[], None]], ...] = tuple(
    (name, getattr(stub, func))
    for name, func in COMMAND_ENTRY_POINTS.items()
    if name not in _REAL_COMMANDS
)


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


@pytest.mark.filterwarnings(
    "ignore:Cyclopts application invoked without tokens:UserWarning"
)
@pytest.mark.parametrize(("name", "entry_point"), STILL_STUBBED_ENTRY_POINTS)
def test_entry_point_callable_exits_two(
    name: str,
    entry_point: cabc.Callable[[], None],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each still-stubbed console-script callable runs its app and exits ``2``."""
    # The callable runs ``app()``, which parses ``sys.argv``; pin a clean,
    # no-argument argv so the bare command-result path is exercised.
    monkeypatch.setattr(sys, "argv", [name])
    with pytest.raises(SystemExit) as excinfo:
        entry_point()
    assert excinfo.value.code == stub.STUB_EXIT_CODE
    captured = capsys.readouterr()
    assert name in captured.err
    assert "Traceback" not in captured.err
