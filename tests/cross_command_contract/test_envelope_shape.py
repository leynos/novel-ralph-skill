"""Cross-command envelope-shape contract pin (roadmap 6.3.2 Work item 1).

Drives each of the five spaced commands in-process through
:func:`novel_ralph_skill.contract.runner.run` over one representative coherent
``working/`` tree and asserts every command's envelope carries the *same* six
contract-fixed keys in the same order with the same field types (design §3.1;
ADR-003). The per-command ``result``/``messages`` payloads differ — a checker
reports ``violations`` while a mutator names what it changed (§3.3) — so they are
redacted to fixed tokens before snapshotting; this module pins only the shared
skeleton. Machine mode parses and asserts the key order and types; human mode
asserts presence (non-empty, names the command) per design §9, never byte-pinned.

The ``--help``/``--version`` arms are deliberately *not* driven: ``run`` exits 0
with no envelope on those arms (``runner.py`` lines 241-245), so the "every
invocation emits the six-field envelope" claim is scoped to the body-producing
and diagnostic arms, never the help/version carve-out.
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from . import BODY_PHASE, COMMANDS
from ._identity_assertions import assert_envelope_skeleton, redact_skeleton

if typ.TYPE_CHECKING:
    from pathlib import Path

    from contract_drive_support import CommandSpec, Driver
    from syrupy.assertion import SnapshotAssertion

from contract_drive_support import assert_no_volatile_fields, build_phase_tree

_COMMAND_IDS: tuple[str, ...] = tuple(command.name for command in COMMANDS)


@pytest.mark.parametrize("command", COMMANDS, ids=_COMMAND_IDS)
def test_machine_envelope_skeleton_identity(
    command: CommandSpec,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """Every command's machine envelope carries the shared skeleton and types.

    Drives the command over the coherent ``BODY_PHASE`` tree and asserts the
    six contract keys in order, the contract field types, ``working_dir`` the
    fixed constant, ``schema_version == 1``, and ``ok`` true iff the exit code is
    0. This is the cross-command *identity* claim: the only field varying across
    the five cells is the redacted ``command`` string and the command-specific
    ``result``/``messages`` payload.

    Parameters
    ----------
    command : CommandSpec
        The spaced command surface under test.
    tmp_path : Path
        The per-test temporary directory the tree is built under.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = build_phase_tree(BODY_PHASE, tmp_path)
    code, raw = drive(command, working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert_envelope_skeleton(envelope, command=command.name, code=code)


@pytest.mark.parametrize("command", COMMANDS, ids=_COMMAND_IDS)
def test_machine_envelope_skeleton_snapshot(
    command: CommandSpec,
    tmp_path: Path,
    drive: Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot the redacted machine envelope skeleton per command.

    The ``result`` and ``messages`` payloads are redacted to fixed tokens so the
    snapshot pins only the contract-fixed skeleton (field set, order, and the
    ``command``/``schema_version``/``ok``/``working_dir`` values) and cannot
    churn on a command's payload wording. The snapshot is paired with the
    semantic skeleton assertion and the volatile-field guard so it is not the
    only guard (AGENTS.md).

    Parameters
    ----------
    command : CommandSpec
        The spaced command surface under test.
    tmp_path : Path
        The per-test temporary directory the tree is built under.
    drive : Driver
        The shared in-process driver fixture.
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.
    """
    working = build_phase_tree(BODY_PHASE, tmp_path)
    code, raw = drive(command, working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert_envelope_skeleton(envelope, command=command.name, code=code)
    assert_no_volatile_fields(envelope)
    redacted = redact_skeleton(envelope)
    assert redacted == snapshot


@pytest.mark.parametrize("command", COMMANDS, ids=_COMMAND_IDS)
def test_human_mode_names_command(
    command: CommandSpec,
    tmp_path: Path,
    drive: Driver,
) -> None:
    """``--human`` renders a non-empty body naming the command for every command.

    The design asserts human mode for *presence* — it renders without error and
    is non-empty and names the command — not byte-for-byte (§9), so it is not
    snapshotted.

    Parameters
    ----------
    command : CommandSpec
        The spaced command surface under test.
    tmp_path : Path
        The per-test temporary directory the tree is built under.
    drive : Driver
        The shared in-process driver fixture.
    """
    working = build_phase_tree(BODY_PHASE, tmp_path)
    _code, rendered = drive(command, working, human=True)
    assert rendered.strip(), "human mode must render a non-empty report"
    assert command.name in rendered
