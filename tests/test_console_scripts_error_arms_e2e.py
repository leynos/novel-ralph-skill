"""Installed-binary proofs of the two command-agnostic diagnostic arms.

The shared runner (``novel_ralph_skill.contract.runner.run``) stamps two
diagnostic envelopes *before any command body runs*: the usage error (exit 2,
``CycloptsError``) on an unknown subcommand or bad arguments, and the
state-or-input error (exit 3, ``StateInputError``) on a missing or unparseable
``state.toml`` or an absent working directory (design 3.2; ADR-003 3.1). Task
6.2.8 crossed both arms in-process for all five read commands. This module
crosses the **installed** half of that gap over a built wheel for two
representative commands — ``novel state`` (a command-group sub-app) and ``novel
desloppify`` (a leaf default command), both driven through the single ``novel``
multiplexer per roadmap task 1.2.13. It observes each real console-script exiting
2 on a malformed invocation and 3 on an absent ``working/``, in machine and human
mode, asserting the ``--human`` stamp survives the subprocess boundary and that
the ``ok: false`` envelope skeleton matches the in-process contract. The
dispatcher stamps the spaced subcommand name (``"novel state"`` or
``"novel desloppify"``) into every envelope.

The arms are command-agnostic — they are stamped by the shared ``run`` wrapper,
not by any command body. Decision D-ONECMD crossed only ``novel state`` on the
6.2.8 finding that the arms are stamped by the shared run wrapper, not the
command bodies. Addendum 6.2.10.1 widens the installed matrix to a second command
(``novel desloppify``, which differs structurally: a leaf default rather than a
sub-app routed through a read subcommand) as a command-sensitivity tripwire, so a
future change making the runner's arms command-sensitive — a command overriding
``--human`` pre-parse, or the ``working_dir`` default — is caught at the installed
boundary rather than silently uncovered.

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
from contract_drive_support import (
    WORKING_DIR_TOKEN,
    normalise_working_dir,
)
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="installed-binary e2e is POSIX-only; see ADR 006",
)


class _InstalledCommand(typ.NamedTuple):
    """One installed surface and the argv shape that routes it onto its arms.

    Bundling the spaced ``name`` with the ``mount_verb`` and ``read_subcommand``
    that compose the run argv keeps the parametrized tests' parameter lists
    within the project's argument-count gate while naming each field at the call
    site, mirroring ``test_command_surface_matrix.py``'s ``_ReadCommand``.

    Attributes
    ----------
    name : str
        The spaced ``novel <verb>`` name the dispatcher stamps into every
        envelope, including the body-less exit-2/exit-3 arms.
    mount_verb : tuple[str, ...]
        The verb mounting the command onto the ``novel`` multiplexer.
    read_subcommand : tuple[str, ...]
        Any read subcommand routing a command-group sub-app onto its real path;
        empty for a leaf default command.
    """

    name: str
    mount_verb: tuple[str, ...]
    read_subcommand: tuple[str, ...]


# ``novel state`` is a command-group sub-app of the ``novel`` multiplexer: a bare
# ``novel state`` prints help and exits 0, so a read subcommand routes the
# invocation onto the real path (the same reason ``test_console_scripts_e2e.py``
# records for ``_REAL_PATH_ARGV``). The run argv mounts the ``state`` verb ahead
# of the ``check`` read subcommand, so the builder receives ``("state", "check",
# …)`` and the dispatcher stamps the spaced ``"novel state"`` name into every
# envelope (ExecPlan Decision Log D3).
_STATE_COMMAND = _InstalledCommand(
    name="novel state",
    mount_verb=("state",),
    read_subcommand=("check",),
)
# ``novel desloppify`` is a leaf default command: the ``desloppify`` verb routes
# straight onto its body, so it carries no read subcommand. It differs
# structurally from ``novel state`` (sub-app + read subcommand), so crossing both
# arms over it as well is the command-sensitivity tripwire of addendum 6.2.10.1.
_DESLOPPIFY_COMMAND = _InstalledCommand(
    name="novel desloppify",
    mount_verb=("desloppify",),
    read_subcommand=(),
)
_COMMANDS: tuple[_InstalledCommand, ...] = (_STATE_COMMAND, _DESLOPPIFY_COMMAND)


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
    # The actionable exit-3 message names the cwd and the ``novel state init``
    # remedy (roadmap §6.3.1); the cwd tail is volatile, so pin the stable prefix.
    message_prefix="no novel working/ found in",
)
_ARMS: tuple[_ErrorArm, ...] = (_USAGE_ARM, _STATE_ARM)


@pytest.fixture
def run_installed(
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult]:
    """Return a runner for the installed ``novel`` multiplexer over a built wheel.

    Closes over the module-scoped install and the one-program catalogue builder
    so callers pass only ``(run_dir, argv)`` — keeping every consumer within the
    four-parameter Pylint gate, mirroring the matrix ``drive`` fixture
    (``tests/test_command_surface_matrix.py`` lines 380-417).

    Parameters
    ----------
    single_program_catalogue : Callable[[str, Program], ProgramCatalogue]
        The one-project catalogue builder from ``tests/conftest.py``.
    installed_novel_state : Path
        The absolute path of the installed ``novel`` multiplexer console-script,
        supplied by the module-scoped ``installed_novel_state`` fixture.

    Returns
    -------
    Callable[[Path, tuple[str, ...]], sh.CommandResult]
        A runner taking ``(run_dir, argv)`` and returning the command result.
    """
    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-error-arm", prog)
    builder = sh.make(prog, catalogue=catalogue)

    def _run(run_dir: Path, argv: tuple[str, ...]) -> sh.CommandResult:
        """Run ``argv`` against the installed script with ``cwd=run_dir``."""
        return builder(*argv).run_sync(
            context=ExecutionContext(cwd=run_dir), capture=True
        )

    return _run


class _Cell(typ.NamedTuple):
    """One ``(command, arm)`` cell of the installed error-arm matrix.

    Bundling the command with its arm keeps each parametrized test at a single
    parameter, mirroring ``test_command_surface_matrix.py``'s ``_ErrorCell``.
    """

    command: _InstalledCommand
    arm: _ErrorArm


_CELLS: tuple[_Cell, ...] = tuple(
    _Cell(command, arm) for command in _COMMANDS for arm in _ARMS
)
_CELL_IDS: tuple[str, ...] = tuple(
    f"{cell.command.mount_verb[0]}-{cell.arm.label}" for cell in _CELLS
)


def _run_installed_arm(
    cell: _Cell,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
    *,
    human: bool,
) -> tuple[sh.CommandResult, Path]:
    """Drive one ``(command, arm)`` cell in one output mode over the binary.

    Derives ``run_dir`` from ``tmp_path`` internally (dropping it as a
    parameter), so the signature lands at four total — three positional plus one
    keyword-only — within the Pylint argument-count gate, mirroring the matrix
    ``_drive_error_cell`` precedent. The run argv mounts the command's verb, then
    ``--human`` (when requested), then the command's read subcommand (empty for a
    leaf default), then the arm's extra argv. ``run_dir`` is returned alongside
    the result so the machine-envelope test can compute the absolute
    ``working_dir`` the binary stamps for *this* cell (roadmap §6.3.4).

    Parameters
    ----------
    cell : _Cell
        The command and diagnostic arm to drive.
    tmp_path : Path
        The per-test temporary directory.
    run_installed : Callable[[Path, tuple[str, ...]], sh.CommandResult]
        The installed-runner fixture closing over the cached install.
    human : bool
        Whether to prepend ``--human`` to request the human rendering.

    Returns
    -------
    tuple[sh.CommandResult, Path]
        The result of running the installed command for this cell, paired with
        the ``run_dir`` it ran in.
    """
    command, arm = cell
    run_dir = tmp_path / f"{command.mount_verb[0]}-{arm.label}"
    run_dir.mkdir(exist_ok=True)
    if arm.build_working:
        wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
    human_prefix = ("--human",) if human else ()
    argv = (
        *command.mount_verb,
        *human_prefix,
        *command.read_subcommand,
        *arm.extra_argv,
    )
    return run_installed(run_dir, argv), run_dir


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize("cell", _CELLS, ids=_CELL_IDS)
def test_installed_error_arm_machine_envelope(
    cell: _Cell,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
) -> None:
    """The installed binary stamps the machine ``ok: false`` envelope per cell.

    Each installed command exits with the arm's code (2 usage, 3 state) and
    prints the machine envelope to stdout: exactly one message whose text begins
    with the arm's stable prefix (the message field is the only
    command-/platform-variable part, so it is asserted by prefix), and — with
    that message redacted — the complete contract envelope including
    ``schema_version`` and the fixed field set. Pinning the whole envelope rather
    than a per-field skeleton makes the boundary proof a complete mirror of the
    in-process contract, so a ``schema_version`` bump or field-order regression
    cannot survive packaging unobserved at the subprocess boundary (addendum
    6.2.10.2). No traceback reaches stderr (design 10 — a fault yields a message,
    not a stack trace). The wheel is built once for the module and reused; the
    180s timeout supersedes the 30s project default.
    """
    command, arm = cell
    result, _run_dir = _run_installed_arm(cell, tmp_path, run_installed, human=False)
    assert result.exit_code == arm.expected_code, (
        f"expected exit {arm.expected_code} for {command.name} {arm.label} arm, "
        f"got {result.exit_code}; stderr: {result.stderr}"
    )
    assert "Traceback" not in (result.stderr or ""), (
        f"a state fault must yield a message, not a traceback: {result.stderr}"
    )
    envelope = json.loads(result.stdout or "{}")
    messages = envelope["messages"]
    assert len(messages) == 1, f"expected exactly one message: {messages}"
    assert messages[0].startswith(arm.message_prefix), (
        f"message must begin with {arm.message_prefix!r}: {messages[0]!r}"
    )
    # Pin the complete envelope contract at the installed boundary, redacting only
    # the message (the sole command-/platform-variable field, asserted by prefix
    # above). This mirrors the in-process matrix's full-envelope equality
    # (``tests/test_command_surface_matrix.py`` lines 449-458) so the boundary
    # proof is a complete mirror of the in-process contract: a ``schema_version``
    # bump or field-order regression — neither caught by the per-field skeleton —
    # cannot survive packaging unobserved at the subprocess boundary (addendum
    # 6.2.10.2). ``working_dir`` is now the absolute resolved path the binary
    # stamped from *this* cell's ``run_dir`` (roadmap §6.3.4); the shared
    # JSON-aware ``normalise_working_dir`` redacts that machine-dependent path to
    # the stable ``WORKING_DIR_TOKEN`` so this boundary proof stays
    # machine-independent without recomputing the resolved path here (addendum
    # 6.3.4.2).
    normalised = typ.cast(
        "dict[str, object]", json.loads(normalise_working_dir(result.stdout or "{}"))
    )
    redacted = {**normalised, "messages": ["<redacted>"]}
    assert redacted == {
        "command": command.name,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "ok": False,
        "working_dir": WORKING_DIR_TOKEN,
        "result": {},
        "messages": ["<redacted>"],
    }, f"boundary envelope must mirror the in-process contract: {envelope}"


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_inside_working_surfaces_footgun(
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
) -> None:
    """Running the binary from inside ``working/`` shows the visible footgun.

    Build a ``working/`` tree under ``run_dir`` and run ``novel state check`` with
    the binary's cwd *inside* ``working/``. The cwd-relative resolution then looks
    for ``working/working/state.toml``, exits 3, and stamps the absolute
    ``.../working/working`` path — so the misresolution a stray ``cd`` causes is
    now loud in the envelope field the agent reads rather than a silent
    ``"working"`` token (roadmap §6.3.4). This is the installed mirror of the
    in-process ``test_main_surfaces_inside_working_footgun`` case. The fixture
    constructs ``ExecutionContext(cwd=…)`` from its first argument, so the deeper
    cwd is reached by passing ``run_dir / "working"`` to it (advisory A6).
    """
    run_dir = tmp_path / "state-inside-working"
    run_dir.mkdir()
    wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
    inside_working = run_dir / "working"
    result = run_installed(inside_working, ("state", "check"))
    assert result.exit_code == ExitCode.STATE_ERROR, (
        f"running from inside working/ must exit 3; stderr: {result.stderr}"
    )
    envelope = json.loads(result.stdout or "{}")
    expected = str((inside_working / "working").resolve())
    assert envelope["working_dir"] == expected
    assert envelope["working_dir"].endswith("/working/working")


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize("cell", _CELLS, ids=_CELL_IDS)
def test_installed_error_arm_human_stamp(
    cell: _Cell,
    tmp_path: Path,
    run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
) -> None:
    """The ``--human`` stamp reaches the body-less arm over the subprocess boundary.

    Prepending ``--human`` on the installed binary's argv renders the
    line-oriented report beginning ``command: <name>`` even on the body-less
    diagnostic arms, proving the global flag survives the subprocess boundary
    (the design 3.2 / ADR-003 3.1 point this task anchors). The rendering also
    carries the diagnostic message, not merely the header, so the arm's stable
    message prefix appears in the body. The arm still exits with its expected
    code.
    """
    command, arm = cell
    result, _run_dir = _run_installed_arm(cell, tmp_path, run_installed, human=True)
    assert result.exit_code == arm.expected_code, (
        f"expected exit {arm.expected_code} for {command.name} {arm.label} arm, "
        f"got {result.exit_code}; stderr: {result.stderr}"
    )
    rendered = (result.stdout or "").strip()
    assert rendered, "human mode must render a non-empty report"
    assert command.name in rendered, (
        f"human rendering must name the command: {rendered!r}"
    )
    assert rendered.startswith(f"command: {command.name}"), (
        f"human rendering must carry the --human stamp header: {rendered!r}"
    )
    assert arm.message_prefix in rendered, (
        f"human rendering must carry the diagnostic message "
        f"beginning {arm.message_prefix!r}: {rendered!r}"
    )
