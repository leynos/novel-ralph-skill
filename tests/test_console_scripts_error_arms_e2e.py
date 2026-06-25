"""Installed-binary proofs of the two command-agnostic diagnostic arms.

The shared runner (``novel_ralph_skill.contract.runner.run``) stamps two
diagnostic envelopes *before any command body runs*: the usage error (exit 2,
``CycloptsError``) on an unknown subcommand or bad arguments, and the
state-or-input error (exit 3, ``StateInputError``) on a missing or unparseable
``state.toml`` or an absent working directory (design 3.2; ADR-003 3.1). Task
6.2.8 crossed both arms in-process for all five read commands. This module
crosses the **installed** half of that gap for one representative command,
``novel-state``, over a built wheel: it observes the real console-script exiting
2 on a malformed invocation and 3 on an absent ``working/``, each in machine and
human mode, asserting the ``--human`` stamp survives the subprocess boundary and
that the ``ok: false`` envelope skeleton matches the in-process contract.

The arms are command-agnostic — they are stamped by the shared ``run`` wrapper,
not by any command body — so 6.2.8's all-five in-process proof makes one
representative installed command sufficient (Decision D-ONECMD).

These e2es are POSIX-only (ADR-006): every external program runs by absolute
path through a one-project cuprum ``ProgramCatalogue`` allowlist, with no raw
``subprocess`` and no ``uv run`` resolution of the project environment. The
built-and-installed script is supplied by the module-scoped
``installed_novel_state`` fixture (``tests/installed_binary_fixtures.py``), so
the wheel is built once for the module and every case reuses it.
"""

from __future__ import annotations

import json
import os
import typing as typ

import pytest
import working_corpus as wc
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="installed-binary e2e is POSIX-only; see ADR 006",
)

_COMMAND = "novel-state"
# ``novel-state`` is a command-group app: a bare ``novel-state`` prints help and
# exits 0, so a read subcommand routes the invocation onto the real path (the
# same reason ``test_console_scripts_e2e.py`` records for ``_REAL_PATH_ARGV``).
_READ_SUBCOMMAND: tuple[str, ...] = ("check",)


class _ErrorArm(typ.NamedTuple):
    """One command-agnostic diagnostic arm of the installed console-script."""

    label: str  # "usage" | "state"
    extra_argv: tuple[str, ...]  # appended after the read subcommand
    build_working: bool  # whether to materialise an (empty) working/ tree
    expected_code: ExitCode
    message_prefix: str


_USAGE_ARM = _ErrorArm(
    label="usage",
    extra_argv=("--nope",),
    # A real tree so only the argv is at fault. This is for parity with the
    # 6.2.8 matrix convention, not necessity: the usage error fires at Cyclopts
    # parse time before any state load, so it would exit 2 even with no tree.
    build_working=True,
    expected_code=ExitCode.USAGE_ERROR,
    message_prefix="Unknown option:",
)
_STATE_ARM = _ErrorArm(
    label="state",
    extra_argv=(),
    build_working=False,  # no working/ -> exit-3 state arm
    expected_code=ExitCode.STATE_ERROR,
    message_prefix="cannot load working/state.toml",
)
_ARMS: tuple[_ErrorArm, ...] = (_USAGE_ARM, _STATE_ARM)


@pytest.fixture
def run_installed(
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult]:
    """Return a runner for the installed ``novel-state`` over a built wheel.

    Closes over the module-scoped install and the one-program catalogue builder
    so callers pass only ``(run_dir, argv)`` — keeping every consumer within the
    four-parameter Pylint gate, mirroring the matrix ``drive`` fixture
    (``tests/test_command_surface_matrix.py`` lines 380-417).

    Parameters
    ----------
    single_program_catalogue : Callable[[str, Program], ProgramCatalogue]
        The one-project catalogue builder from ``tests/conftest.py``.
    installed_novel_state : Path
        The absolute path of the installed ``novel-state`` console-script,
        supplied by the module-scoped ``installed_novel_state`` fixture.

    Returns
    -------
    Callable[[Path, tuple[str, ...]], sh.CommandResult]
        A runner taking ``(run_dir, argv)`` and returning the command result.
    """
    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-error-arm", prog)
    builder = sh.make(prog, catalogue=catalogue)

    def _run(run_dir: Path, argv: tuple[str, ...]) -> sh.CommandResult:
        """Run ``argv`` against the installed script with ``cwd=run_dir``."""
        return builder(*argv).run_sync(
            context=ExecutionContext(cwd=run_dir), capture=True
        )

    return _run


def _run_installed_arm(
    arm: _ErrorArm,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
    *,
    human: bool,
) -> sh.CommandResult:
    """Drive one diagnostic arm in one output mode over the installed binary.

    Derives ``run_dir`` from ``tmp_path`` internally (dropping it as a
    parameter), so the signature lands at four total — three positional plus one
    keyword-only — within the Pylint argument-count gate, mirroring the matrix
    ``_drive_error_cell`` precedent.

    Parameters
    ----------
    arm : _ErrorArm
        The diagnostic arm to drive.
    tmp_path : Path
        The per-test temporary directory.
    run_installed : Callable[[Path, tuple[str, ...]], sh.CommandResult]
        The installed-runner fixture closing over the cached install.
    human : bool
        Whether to prepend ``--human`` to request the human rendering.

    Returns
    -------
    sh.CommandResult
        The result of running the installed ``novel-state`` for this arm.
    """
    run_dir = tmp_path / arm.label
    run_dir.mkdir(exist_ok=True)
    if arm.build_working:
        wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
    human_prefix = ("--human",) if human else ()
    argv = (*human_prefix, *_READ_SUBCOMMAND, *arm.extra_argv)
    return run_installed(run_dir, argv)


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize("arm", _ARMS, ids=[a.label for a in _ARMS])
def test_installed_error_arm_machine_envelope(
    arm: _ErrorArm,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
) -> None:
    """The installed binary stamps the machine ``ok: false`` envelope per arm.

    The installed ``novel-state`` exits with the arm's code (2 usage, 3 state)
    and prints the machine envelope to stdout: the named command, ``ok: false``,
    ``working_dir == "working"``, ``result == {}``, and exactly one message
    whose text begins with the arm's stable prefix (the message field is the
    only command-/platform-variable part, so it is asserted by prefix). No
    traceback reaches stderr (design 10 — a fault yields a message, not a stack
    trace). The wheel is built once for the module and reused; the 180s timeout
    supersedes the 30s project default.
    """
    result = _run_installed_arm(arm, tmp_path, run_installed, human=False)
    assert result.exit_code == arm.expected_code, (
        f"expected exit {arm.expected_code} for {arm.label} arm, "
        f"got {result.exit_code}; stderr: {result.stderr}"
    )
    assert "Traceback" not in (result.stderr or ""), (
        f"a state fault must yield a message, not a traceback: {result.stderr}"
    )
    envelope = json.loads(result.stdout or "{}")
    assert envelope["command"] == _COMMAND, (
        f"envelope must name the command: {envelope}"
    )
    assert envelope["ok"] is False, f"diagnostic arm must be ok: false: {envelope}"
    assert envelope["working_dir"] == "working", (
        f"envelope must carry working_dir 'working': {envelope}"
    )
    assert envelope["result"] == {}, f"diagnostic arm carries no result: {envelope}"
    messages = envelope["messages"]
    assert len(messages) == 1, f"expected exactly one message: {messages}"
    assert messages[0].startswith(arm.message_prefix), (
        f"message must begin with {arm.message_prefix!r}: {messages[0]!r}"
    )


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize("arm", _ARMS, ids=[a.label for a in _ARMS])
def test_installed_error_arm_human_stamp(
    arm: _ErrorArm,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
) -> None:
    """The ``--human`` stamp reaches the body-less arm over the subprocess boundary.

    Prepending ``--human`` on the installed binary's argv renders the
    line-oriented report beginning ``command: novel-state`` even on the
    body-less diagnostic arms, proving the global flag survives the subprocess
    boundary (the design 3.2 / ADR-003 3.1 point this task anchors). The
    rendering also carries the diagnostic message, not merely the header, so the
    arm's stable message prefix appears in the body. The arm still exits with
    its expected code.
    """
    result = _run_installed_arm(arm, tmp_path, run_installed, human=True)
    assert result.exit_code == arm.expected_code, (
        f"expected exit {arm.expected_code} for {arm.label} arm, "
        f"got {result.exit_code}; stderr: {result.stderr}"
    )
    rendered = (result.stdout or "").strip()
    assert rendered, "human mode must render a non-empty report"
    assert _COMMAND in rendered, f"human rendering must name the command: {rendered!r}"
    assert rendered.startswith(f"command: {_COMMAND}"), (
        f"human rendering must carry the --human stamp header: {rendered!r}"
    )
    assert arm.message_prefix in rendered, (
        f"human rendering must carry the diagnostic message "
        f"beginning {arm.message_prefix!r}: {rendered!r}"
    )
