"""Cross-command error-channel shape pin (roadmap 6.3.2 Work item 4).

For each of the five spaced commands this module drives the two command-agnostic
diagnostic arms in-process — the usage arm (an unknown ``--nope`` option, exit 2,
``CycloptsError``) and the state arm (no ``working/``, exit 3, ``StateInputError``)
— and asserts that, with the variable ``messages`` field redacted, the envelope
skeleton is *identical* across all five commands for each arm: ``ok: false``,
empty ``result``, the six fields in order, ``schema_version == 1``,
``working_dir == "working"`` (design §3.2; ADR-003 Table 2). The only datum that
varies across the ten cells is the redacted ``command`` string and the
``messages`` field, so this is the cross-command *identity* form of the §6.2.8
per-read-command error arms, extended over all five commands.

For the actionable-finding arm (exit 4) each *constructible* command is bound to
its concrete tree (cell table): ``novel compile --check`` over a ``drafting``
tree, ``novel state check`` over an ``incoherent_tree`` variant, and
``novel desloppify`` over an em-dash-flood draft. ``novel done`` and
``novel wordcount`` have **no** exit-4 arm over the corpus, so they are carried
as documented gaps (package docstring), never asserted. The exit-4 ``result`` is
command-specific and not empty (it carries ``violations``/``diverged``), so this
module asserts the skeleton and field-type identity across the three commands and
snapshots each command's ``result`` separately, never asserting two commands'
``result`` equal.

These are body-less or body-produced diagnostic arms, **not** the help/version
carve-out (``run`` exits 0 with no envelope there); the suite never drives
help/version.
"""

from __future__ import annotations

import json
import typing as typ

import pytest
from contract_drive_support import CommandSpec, assert_no_volatile_fields

from novel_ralph_skill.commands import novel_state
from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES
from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION
from novel_ralph_skill.contract.exit_codes import ExitCode

from . import WORKING_DIR_CONSTANT
from ._cells import CONSTRUCTIBLE_CELLS, MUTATOR_STATE_ARMS, materialise
from ._identity_assertions import assert_envelope_skeleton

if typ.TYPE_CHECKING:
    from pathlib import Path

    from contract_drive_support import Driver
    from syrupy.assertion import SnapshotAssertion

    from ._cells import ChannelCell, MutatorArm

# The spaced command name every ``novel state`` mutator stamps into its envelope.
_STATE_COMMAND = "novel state"
_MUTATOR_IDS: tuple[str, ...] = tuple(arm.verb for arm in MUTATOR_STATE_ARMS)


def _expected_diagnostic_skeleton(command: str) -> dict[str, object]:
    """Return the redacted ok-false diagnostic skeleton for ``command``.

    The shared skeleton every usage/state arm shares once ``messages`` is
    redacted: ``ok: false``, empty ``result``, the six fields in order,
    ``schema_version == 1``, ``working_dir == "working"``.

    Parameters
    ----------
    command : str
        The spaced command name the skeleton stamps.

    Returns
    -------
    dict[str, object]
        The redacted skeleton to assert equal across commands.
    """
    return {
        "command": command,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "ok": False,
        "working_dir": WORKING_DIR_CONSTANT,
        "result": {},
        "messages": ["<redacted>"],
    }


# The two command-agnostic diagnostic arms, one cell per (command, arm).
_DIAGNOSTIC_CELLS: tuple[ChannelCell, ...] = tuple(
    cell
    for cell in CONSTRUCTIBLE_CELLS
    if cell.channel in {ExitCode.USAGE_ERROR, ExitCode.STATE_ERROR}
)
_DIAGNOSTIC_IDS: tuple[str, ...] = tuple(
    f"{cell.command_name}-{cell.channel.name}" for cell in _DIAGNOSTIC_CELLS
)

# The actionable-finding arm, constructible for exactly three commands.
_FINDING_CELLS: tuple[ChannelCell, ...] = tuple(
    cell for cell in CONSTRUCTIBLE_CELLS if cell.channel is ExitCode.ACTIONABLE_FINDING
)
_FINDING_IDS: tuple[str, ...] = tuple(cell.command_name for cell in _FINDING_CELLS)


def _spec(cell: ChannelCell) -> CommandSpec:
    """Return the :class:`CommandSpec` driving ``cell``'s command over its argv."""
    return CommandSpec(cell.command_name, cell.build_app, cell.argv)


@pytest.mark.parametrize("cell", _DIAGNOSTIC_CELLS, ids=_DIAGNOSTIC_IDS)
def test_diagnostic_arm_skeleton_identity(
    cell: ChannelCell,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """The usage and state arms share one redacted skeleton across all commands.

    Drives the arm and asserts the redacted envelope equals the command-templated
    skeleton — ``ok: false``, empty ``result``, the six fields in order,
    ``schema_version == 1``, ``working_dir == "working"`` — so the only varying
    datum is the ``command`` string and the redacted ``messages``. A non-blank
    message (not a traceback) is asserted per design §10.

    Parameters
    ----------
    cell : ChannelCell
        The (command, diagnostic-arm) cell to drive.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = materialise(cell, tmp_path)
    code, raw = drive(_spec(cell), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == cell.channel
    assert_envelope_skeleton(envelope, command=cell.command_name, code=code)
    messages = typ.cast("list[str]", envelope["messages"])
    assert messages, "a diagnostic arm must carry at least one message"
    assert any(line.strip() for line in messages), "the message must be non-blank"
    redacted = {**envelope, "messages": ["<redacted>"]}
    assert_no_volatile_fields(redacted)
    assert redacted == _expected_diagnostic_skeleton(cell.command_name)


@pytest.mark.parametrize("cell", _DIAGNOSTIC_CELLS, ids=_DIAGNOSTIC_IDS)
def test_diagnostic_arm_human_presence(
    cell: ChannelCell,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """``--human`` renders a non-empty body naming the command for each arm.

    Proves the ``--human`` stamp reaches the body-less arms (ADR-003 §3.1): the
    same presence contract the body arms use, now over the exit-2/exit-3
    envelopes ``run`` produces when the body never returns a ``result``.

    Parameters
    ----------
    cell : ChannelCell
        The (command, diagnostic-arm) cell to drive.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = materialise(cell, tmp_path)
    _code, rendered = drive(_spec(cell), working, human=True)
    assert rendered.strip(), "human mode must render a non-empty report"
    assert cell.command_name in rendered


def test_diagnostic_arms_cover_all_five_commands() -> None:
    """Both diagnostic arms are constructible for all five commands.

    Guards the cell table's command-agnostic claim: every spaced command reaches
    exit 2 on ``--nope`` and exit 3 with no ``working/``, so the usage and state
    arms are the cross-command-identity arms (no carried gap here).
    """
    by_channel: dict[ExitCode, set[str]] = {
        ExitCode.USAGE_ERROR: set(),
        ExitCode.STATE_ERROR: set(),
    }
    for cell in _DIAGNOSTIC_CELLS:
        by_channel[cell.channel].add(cell.command_name)
    expected = {name for name in ENVELOPE_COMMAND_NAMES if name != "novel"}
    assert by_channel[ExitCode.USAGE_ERROR] == expected
    assert by_channel[ExitCode.STATE_ERROR] == expected


def test_finding_arm_covers_exactly_three_commands() -> None:
    """The actionable-finding arm is constructible for exactly three commands.

    Mirrors :func:`test_diagnostic_arms_cover_all_five_commands` for the exit-4
    channel, which is the channel the corpus cannot reach for every command:
    ``novel state check`` (an ``incoherent_tree`` variant), ``novel compile
    --check`` (a ``drafting`` tree), and ``novel desloppify`` (an em-dash-flood
    draft) reach it, but ``novel done`` and ``novel wordcount`` are carried gaps
    (package docstring). Because ``make test`` runs under xdist, where syrupy
    does not reliably fail on orphaned snapshots, a future deletion of a finding
    cell from ``_BODY_CELLS`` would silently reduce coverage; this guard asserts
    the finding cells cover exactly ``{novel state, novel compile,
    novel desloppify}`` so such a deletion fails loudly.
    """
    covered = {cell.command_name for cell in _FINDING_CELLS}
    assert covered == {"novel state", "novel compile", "novel desloppify"}


@pytest.mark.parametrize("cell", _FINDING_CELLS, ids=_FINDING_IDS)
def test_finding_arm_skeleton_identity(
    cell: ChannelCell,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """The exit-4 arm shares the ok-false skeleton across the constructible commands.

    Drives the constructible actionable-finding cell and asserts the shared
    skeleton and field types (six fields in order, ``schema_version``,
    ``working_dir``, ``ok: false``). The ``result`` is command-specific and not
    empty here (it carries ``violations``/``diverged``), so it is *not* asserted
    equal across commands — only its presence as a non-empty mapping is checked;
    its contents are snapshotted separately below.

    Parameters
    ----------
    cell : ChannelCell
        The constructible exit-4 (command, channel) cell.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = materialise(cell, tmp_path)
    code, raw = drive(_spec(cell), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.ACTIONABLE_FINDING
    assert_envelope_skeleton(envelope, command=cell.command_name, code=code)
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result, "the exit-4 result names the finding and is not empty"
    messages = typ.cast("list[str]", envelope["messages"])
    assert any(line.strip() for line in messages), "the finding must carry a message"


@pytest.mark.parametrize("cell", _FINDING_CELLS, ids=_FINDING_IDS)
def test_finding_arm_result_snapshot(
    cell: ChannelCell,
    tmp_path: Path,
    drive: Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot each constructible exit-4 command's ``result`` separately.

    The exit-4 ``result`` is command-specific (``novel state check`` reports
    ``violations``, ``novel compile`` reports ``diverged``, ``novel desloppify``
    reports its slimmed ``violations``), so each is pinned in its own snapshot
    block, paired with the skeleton and exit-code assertions so the snapshot is
    not the only guard (AGENTS.md). Two commands' ``result`` are never asserted
    equal.

    Parameters
    ----------
    cell : ChannelCell
        The constructible exit-4 (command, channel) cell.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.
    """
    working = materialise(cell, tmp_path)
    code, raw = drive(_spec(cell), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.ACTIONABLE_FINDING
    assert_no_volatile_fields(envelope)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == snapshot


def _mutator_spec(arm: MutatorArm, *, extra: list[str] | None = None) -> CommandSpec:
    """Return a :class:`CommandSpec` driving ``arm``'s mutator over ``argv + extra``.

    Parameters
    ----------
    arm : MutatorArm
        The mutator and its complete, valid argv.
    extra : list[str] | None
        Extra tokens appended to the argv (e.g. ``["--nope"]`` for the usage
        arm), or ``None`` for the bare valid argv.

    Returns
    -------
    CommandSpec
        The spec the ``drive`` fixture consumes, stamping ``"novel state"``.
    """
    return CommandSpec(
        _STATE_COMMAND, novel_state.build_app, [*arm.argv, *(extra or [])]
    )


@pytest.mark.parametrize("arm", MUTATOR_STATE_ARMS, ids=_MUTATOR_IDS)
def test_mutator_state_arm_skeleton_identity(
    arm: MutatorArm,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """Each mutator's state arm shares the same ok-false skeleton as the read arms.

    Drives the mutator with a complete, valid argv over a cwd with no
    ``working/`` so the body reaches the ``working/state.toml`` load and refuses
    with exit 3 (not the exit-2 usage fault a missing required argument would
    raise — ExecPlan Surprises). Asserts the redacted skeleton equals the same
    ``"novel state"`` diagnostic skeleton the read ``check`` arm yields, bringing
    the mutators into the cross-command state-channel identity §6.2.1 excluded.

    Parameters
    ----------
    arm : MutatorArm
        The mutator and its complete, valid argv.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    root = tmp_path / "no-working"
    root.mkdir(exist_ok=True)
    working = root / "working"  # deliberately NOT created
    code, raw = drive(_mutator_spec(arm), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.STATE_ERROR
    assert_envelope_skeleton(envelope, command=_STATE_COMMAND, code=code)
    messages = typ.cast("list[str]", envelope["messages"])
    assert any(line.strip() for line in messages), "the refusal must carry a message"
    redacted = {**envelope, "messages": ["<redacted>"]}
    assert_no_volatile_fields(redacted)
    assert redacted == _expected_diagnostic_skeleton(_STATE_COMMAND)


@pytest.mark.parametrize("arm", MUTATOR_STATE_ARMS, ids=_MUTATOR_IDS)
def test_mutator_usage_arm_skeleton_identity(
    arm: MutatorArm,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """Each mutator's usage arm shares the same ok-false skeleton across commands.

    Appends an unknown ``--nope`` option to the mutator's valid argv so it faults
    at parse with exit 2, and asserts the redacted skeleton equals the shared
    ``"novel state"`` diagnostic skeleton — the usage-channel identity the read
    commands also share.

    Parameters
    ----------
    arm : MutatorArm
        The mutator and its complete, valid argv.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    """
    # A coherent tree so only the ``--nope`` token is at fault, not the tree.
    working = materialise(CONSTRUCTIBLE_CELLS[0], tmp_path)
    code, raw = drive(_mutator_spec(arm, extra=["--nope"]), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.USAGE_ERROR
    assert_envelope_skeleton(envelope, command=_STATE_COMMAND, code=code)
    redacted = {**envelope, "messages": ["<redacted>"]}
    assert_no_volatile_fields(redacted)
    assert redacted == _expected_diagnostic_skeleton(_STATE_COMMAND)
