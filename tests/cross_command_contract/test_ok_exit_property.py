"""Cross-command ok/exit-code mapping pin (roadmap 6.3.2 Work item 2).

This module has two distinct parts with different mechanisms (ADR-003 Table 2;
design §3.2: "``ok`` mirrors the exit code"):

- **Part A — the pure Hypothesis property (no disk).** One ``@given`` property
  drives a *synthetic* :class:`~novel_ralph_skill.contract.runner.CommandOutcome`
  through :func:`~novel_ralph_skill.contract.runner.run` and parses the emitted
  envelope, asserting ``ok`` is ``True`` if and only if the exit code is 0,
  sampling ``code`` over every :class:`ExitCode` and ``command`` over every
  :data:`SUBCOMMAND_NAMES` member. It runs entirely in-process with no
  ``tmp_path`` and no ``monkeypatch.chdir``: the synthetic outcome is returned by
  a builder modelled on the shared ``wrapper_app`` fixture, so no function-scoped
  fixture is taken under ``@given`` (``HealthCheck.function_scoped_fixture``),
  exactly as ``tests/test_contract_properties.py`` does. This proves the ok/exit
  biconditional over the *full* code x command space on the real ``run`` seam.

- **Part B — the driven example cells (plain pytest, disk allowed).** Plain
  ``@pytest.mark.parametrize`` tests (never ``@given``, so the function-scoped
  ``tmp_path`` and ``drive`` fixtures are permitted) drive each *real* command
  into each of its constructible channels from the cell table
  (``tests/cross_command_contract/_cells.py``) and assert the ``(code, ok)`` pair.
  The unconstructible (command, channel) pairs — ``done``/``wordcount`` exit 4,
  every command's exit 1 except ``done``'s — are carried as documented gaps in
  the package docstring, never asserted as unreachable channels.

The grouping the roadmap calls "0/1 → benign, 2/3/4 → ok:false" is the harness
*response* class (loop versus stop), **not** the ``ok`` field: the contract is
``ok`` true **iff** the code is 0, so benign-negative (code 1) is ``ok: false``.
The assertions pin the iff so a future reader does not "correct" the suite.
"""

from __future__ import annotations

import json
import typing as typ

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novel_ralph_skill.commands.names import SUBCOMMAND_NAMES
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, RunContext, run

from ._cells import CELL_IDS, CONSTRUCTIBLE_CELLS, materialise

if typ.TYPE_CHECKING:
    from pathlib import Path

    from contract_drive_support import CommandSpec, Driver

    from ._cells import ChannelCell


@given(
    code=st.sampled_from(list(ExitCode)),
    command=st.sampled_from(list(SUBCOMMAND_NAMES)),
)
def test_ok_iff_success_over_run(code: ExitCode, command: str) -> None:
    """``ok`` is ``True`` iff the exit code is 0, over the pure ``run`` surface.

    Drives a synthetic ``CommandOutcome`` of ``code`` through ``run`` for every
    ``command`` and parses the emitted envelope, asserting the ok/exit
    biconditional on the real shared seam across the full code x command space.
    No disk, no ``chdir``, no function-scoped fixture: the app is built inline
    via :func:`~novel_ralph_skill.contract.runner.make_contract_app`, mirroring
    the ``wrapper_app`` fixture, so ``@given`` takes only strategy-drawn values.

    Parameters
    ----------
    code : ExitCode
        The synthetic outcome's exit code, sampled over every member.
    command : str
        A registered spaced subcommand name, sampled over every member.
    """
    import contextlib
    import io

    from novel_ralph_skill.contract.runner import make_contract_app

    app = make_contract_app(command)

    @app.command
    def act() -> CommandOutcome:
        """Return the synthetic outcome carrying the sampled exit code."""
        return CommandOutcome(code=code)

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            app,
            ["act"],
            RunContext(command=command, working_dir="working", human=False),
        )
    exited = typ.cast("int", excinfo.value.code)
    envelope = typ.cast("dict[str, object]", json.loads(stream.getvalue()))
    assert exited == code
    assert envelope["ok"] is (code == ExitCode.SUCCESS)


@pytest.mark.parametrize("cell", CONSTRUCTIBLE_CELLS, ids=CELL_IDS)
def test_driven_cell_code_and_ok(
    cell: ChannelCell,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """Each constructible (command, channel) cell reaches its code with matching ok.

    Drives the real command into the cell's channel over its bound tree and
    asserts the captured exit code equals the channel's code and the parsed
    envelope ``ok`` equals ``(code == 0)``. The parametrize ids name each
    ``command-CHANNEL`` cell so a reviewer sees which pairs are asserted and,
    by their absence, which are carried gaps (package docstring).

    Parameters
    ----------
    cell : ChannelCell
        The constructible (command, channel) cell to drive.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = materialise(cell, tmp_path)
    command = _spec(cell)
    code, raw = drive(command, working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == cell.channel
    assert envelope["ok"] is (cell.channel == ExitCode.SUCCESS)


def _spec(cell: ChannelCell) -> CommandSpec:
    """Return the :class:`CommandSpec` driving ``cell``'s command over its argv.

    Parameters
    ----------
    cell : ChannelCell
        The cell whose command and argv to bundle.

    Returns
    -------
    CommandSpec
        The ``(name, build_app, argv)`` spec the ``drive`` fixture consumes.
    """
    from contract_drive_support import CommandSpec as _CommandSpec

    return _CommandSpec(cell.command_name, cell.build_app, cell.argv)
