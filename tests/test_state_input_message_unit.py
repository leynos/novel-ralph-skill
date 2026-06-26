"""Unit proof for the shared actionable state-input (exit-3) message helper.

These tests pin the executable specification for
:func:`novel_ralph_skill.commands.novel_state._state_input_error`: the message a
failed ``state.toml`` load emits on the exit-3 channel. They assert the two arms
Decision Log D2 distinguishes — a *missing* ``working/`` (where ``novel state
init`` is the remedy) versus a *present-but-corrupt* ``state.toml`` (where
``init`` is the wrong advice) — and that neither arm leaks a raw ``Errno`` or a
traceback marker into ``exc.messages`` (roadmap §6.3.1).

The cross-boundary parity proof lives in
``tests/test_state_input_message_parity.py``, which lands with the mutator
boundary that shares this helper.
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.commands.novel_state import (
    _load_or_state_error,
    _state_input_error,
    state_path,
    working_dir,
)
from novel_ralph_skill.contract.runner import StateInputError

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import pathlib


def _working_dir_state_path() -> pathlib.Path:
    """Return ``working/state.toml`` via the joined call shape (ExecPlan Risk 1)."""
    return working_dir() / "state.toml"


def _make_corrupt_state(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a ``working/state.toml`` that parses-faults, and return its path."""
    working = tmp_path / "working"
    working.mkdir()
    state = working / "state.toml"
    # Invalid TOML: an unterminated string is a ``TOMLDecodeError`` for both
    # ``tomllib`` and ``tomlkit``, so the corrupt arm fires after the file opens.
    state.write_text('cursor = "unterminated\n', encoding="utf-8")
    return state


@pytest.mark.parametrize(
    "path_factory",
    [
        pytest.param(state_path, id="state_path"),
        pytest.param(_working_dir_state_path, id="working_dir-joined"),
    ],
)
def test_missing_state_message_is_actionable(
    path_factory: cabc.Callable[[], pathlib.Path],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing ``working/`` yields the cwd-naming, ``init``-suggesting message.

    Exercises both call shapes from ExecPlan Risk 1 — the ``state_path()``
    accessor and the ``working_dir / "state.toml"`` join — to prove the helper
    derives its reported directory from the argument, not a fixed string.
    """
    monkeypatch.chdir(tmp_path)
    path = path_factory()

    error = _state_input_error(path, FileNotFoundError(2, "No such file"))

    (message,) = error.messages
    assert str(tmp_path) in message, "the message must name the current directory"
    assert "working/" in message, "the message must name the working/ tree"
    assert "novel state init" in message, "the message must offer the init remedy"
    assert "Errno" not in message, "the message must not leak a raw Errno"
    assert "Traceback" not in message, "the message must not leak a traceback"


def test_corrupt_state_message_omits_init_remedy(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A present-but-corrupt ``state.toml`` yields the repair message, not ``init``.

    ``novel state init`` would not repair a damaged file, so the corrupt arm must
    not advise it (Decision Log D2). The message names the path and asks for
    inspection or repair, with no raw ``Errno`` or traceback.
    """
    monkeypatch.chdir(tmp_path)
    state = _make_corrupt_state(tmp_path)

    with pytest.raises(StateInputError) as excinfo:
        _load_or_state_error(state)

    (message,) = excinfo.value.messages
    assert "novel state init" not in message, "init must not be advised for corruption"
    assert "state.toml" in message, "the corrupt message must name the path"
    assert "Errno" not in message, "the message must not leak a raw Errno"
    assert "Traceback" not in message, "the message must not leak a traceback"
