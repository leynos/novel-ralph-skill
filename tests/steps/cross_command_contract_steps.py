"""Step definitions for the cross-command contract scenario suite (roadmap 6.3.2).

These steps are the human-readable face of Work items 1, 2, and 4: they drive
each spaced command in-process through the shared ``drive`` fixture and assert
the same envelope-skeleton and exit-code invariants the in-code modules pin,
calling the same shared helpers
(``tests/cross_command_contract/_identity_assertions.py``) so the prose and the
in-code suites cannot silently diverge. Only the two command-agnostic arms
(usage, state) and the body-producing arm are crossed over the full five-command
``Examples`` table; the exit-4 channel — constructible for only three commands —
is asserted in the per-command-bound ``test_error_channels`` module, not a
five-row outline that would assert an unreachable channel for ``done``/
``wordcount`` (package docstring; cell table).

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_cross_command_contract_bdd.py``. Fixture state flows between steps
through ``target_fixture`` returns, the pytest-bdd idiom.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

from contract_drive_support import CommandSpec, build_phase_tree
from cross_command_contract import COMMANDS
from cross_command_contract._identity_assertions import assert_envelope_skeleton
from pytest_bdd import given, parsers, then, when

from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from pathlib import Path

    from contract_drive_support import Driver

# The coherent phase whose tree every command produces a body envelope over.
_BODY_PHASE = "final-pass"
_BY_NAME: dict[str, CommandSpec] = {command.name: command for command in COMMANDS}


@dc.dataclass(slots=True)
class _Driven:
    """The command, its working tree, and the captured drive result across steps."""

    command: CommandSpec
    working: Path
    exit_code: int | None = None
    envelope: dict[str, object] | None = None


def _spec_for(name: str) -> CommandSpec:
    """Return the registered :class:`CommandSpec` for the spaced ``name``."""
    spec = _BY_NAME.get(name)
    assert spec is not None, f"unknown command {name!r}"
    return spec


@given(
    parsers.parse('a coherent working tree for "{command}"'),
    target_fixture="driven",
)
def coherent_tree(command: str, tmp_path: Path) -> _Driven:
    """Build the coherent body tree for ``command`` under ``tmp_path``.

    Returns
    -------
    _Driven
        The command spec and its materialised ``working/`` tree.
    """
    spec = _spec_for(command)
    working = build_phase_tree(_BODY_PHASE, tmp_path)
    return _Driven(command=spec, working=working)


@given(
    parsers.parse('a cwd with no working tree for "{command}"'),
    target_fixture="driven",
)
def no_working_tree(command: str, tmp_path: Path) -> _Driven:
    """Bind ``command`` to a cwd with no ``working/`` (the state arm).

    Returns
    -------
    _Driven
        The command spec and a synthetic, uncreated ``working/`` path whose
        parent is an empty cwd.
    """
    spec = _spec_for(command)
    root = tmp_path / "no-working"
    root.mkdir(exist_ok=True)
    return _Driven(command=spec, working=root / "working")


@when(parsers.parse('"{command}" is driven in machine mode'))
def drive_machine(driven: _Driven, drive: Driver) -> None:
    """Drive the bound command in machine mode and capture the parsed envelope.

    The ``{command}`` token only selects the ``Examples`` row; the resolved spec
    is carried on ``driven`` from the ``Given`` step, so this step does not bind
    the parsed token.
    """
    code, raw = drive(driven.command, driven.working, human=False)
    driven.exit_code = code
    driven.envelope = typ.cast("dict[str, object]", json.loads(raw))


@when(parsers.parse('"{command}" is driven with an unknown option in machine mode'))
def drive_usage(driven: _Driven, drive: Driver) -> None:
    """Drive the bound command with an unknown ``--nope`` option (the usage arm).

    The ``{command}`` token only selects the ``Examples`` row; the resolved spec
    is carried on ``driven`` from the ``Given`` step.
    """
    usage_spec = driven.command._replace(argv=[*driven.command.argv, "--nope"])
    code, raw = drive(usage_spec, driven.working, human=False)
    driven.exit_code = code
    driven.envelope = typ.cast("dict[str, object]", json.loads(raw))


@then("the envelope carries the six contract fields in order with the contract types")
def asserts_skeleton(driven: _Driven) -> None:
    """Assert the parsed envelope carries the shared contract skeleton and types."""
    assert driven.envelope is not None, "the envelope must have been captured"
    assert driven.exit_code is not None, "the exit code must have been captured"
    assert_envelope_skeleton(
        driven.envelope, command=driven.command.name, code=driven.exit_code
    )


@then('working_dir is "working"')
def asserts_working_dir(driven: _Driven) -> None:
    """Assert ``working_dir`` is the fixed ``"working"`` constant."""
    assert driven.envelope is not None
    assert driven.envelope["working_dir"] == "working"


@then("ok mirrors the exit code")
def asserts_ok_mirrors(driven: _Driven) -> None:
    """Assert ``ok`` is true if and only if the exit code is 0."""
    assert driven.envelope is not None
    assert driven.exit_code is not None
    assert driven.envelope["ok"] is (driven.exit_code == ExitCode.SUCCESS)


@then("the command exits 3 with the ok-false skeleton and an empty result")
def asserts_state_channel(driven: _Driven) -> None:
    """Assert the state arm: exit 3, ``ok: false``, empty result, shared skeleton."""
    assert driven.exit_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {driven.exit_code}"
    )
    assert driven.envelope is not None
    assert_envelope_skeleton(
        driven.envelope, command=driven.command.name, code=driven.exit_code
    )
    assert driven.envelope["ok"] is False
    assert driven.envelope["result"] == {}


@then("the command exits 2 with the ok-false skeleton and an empty result")
def asserts_usage_channel(driven: _Driven) -> None:
    """Assert the usage arm: exit 2, ``ok: false``, empty result, shared skeleton."""
    assert driven.exit_code == ExitCode.USAGE_ERROR, (
        f"expected exit 2, got {driven.exit_code}"
    )
    assert driven.envelope is not None
    assert_envelope_skeleton(
        driven.envelope, command=driven.command.name, code=driven.exit_code
    )
    assert driven.envelope["ok"] is False
    assert driven.envelope["result"] == {}


@then("the envelope carries a non-blank message")
def asserts_non_blank_message(driven: _Driven) -> None:
    """Assert the diagnostic arm carries at least one non-blank message line."""
    assert driven.envelope is not None
    messages = typ.cast("list[str]", driven.envelope["messages"])
    assert messages, "a diagnostic arm must carry at least one message"
    assert all(isinstance(line, str) for line in messages)
    assert any(line.strip() for line in messages), "the message must be non-blank"
