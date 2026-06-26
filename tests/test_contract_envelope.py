"""Unit and snapshot tests for the envelope data type and renderers.

These cover roadmap task 1.3.1 Work item 3: that ``build_envelope`` derives
``ok`` solely from the exit code, rejects an unregistered command, and that the
two renderers honour the contract (machine mode emits the six keys in fixed
order; human mode surfaces the messages, not the raw ``result`` JSON). Two
syrupy snapshots pin the rendered shape of a representative success envelope;
the per-code snapshot matrix lands in Work item 5.
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands.names import (
    ENVELOPE_COMMAND_NAMES,
    SUBCOMMAND_NAMES,
)
from novel_ralph_skill.contract.envelope import (
    ENVELOPE_SCHEMA_VERSION,
    build_envelope,
    render_human,
    render_machine,
)
from novel_ralph_skill.contract.exit_codes import ExitCode, is_ok

if typ.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

_FIXED_FIELD_ORDER = (
    "command",
    "schema_version",
    "ok",
    "working_dir",
    "result",
    "messages",
)


@pytest.mark.parametrize("code", list(ExitCode))
def test_ok_is_derived_from_code(code: ExitCode) -> None:
    """``ok`` is ``True`` exactly for :data:`ExitCode.SUCCESS`.

    Parameters
    ----------
    code : ExitCode
        The exit code under test.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[0],
        working_dir="working",
        code=code,
        result={},
        messages=[],
    )
    assert env.ok is (code is ExitCode.SUCCESS)
    assert env.ok is is_ok(code)


def test_build_envelope_rejects_unknown_command() -> None:
    """An unregistered ``command`` raises :class:`ValueError`.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    with pytest.raises(ValueError, match="unknown command"):
        build_envelope(
            command="not-a-command",
            working_dir="working",
            code=ExitCode.SUCCESS,
            result={},
            messages=[],
        )


@pytest.mark.parametrize("command", list(ENVELOPE_COMMAND_NAMES))
def test_build_envelope_accepts_the_superset(command: str) -> None:
    """Every member of the envelope-guard superset is accepted (ADR 007).

    The guard is the spaced ``novel <verb>`` names plus the bare ``"novel"``
    surface, so the multiplexer validates every command name it stamps
    (Decision Log D1).

    Parameters
    ----------
    command : str
        A registered command or spaced subcommand name under test.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    env = build_envelope(
        command=command,
        working_dir="working",
        code=ExitCode.SUCCESS,
        result={},
        messages=[],
    )
    assert env.command == command


def test_envelope_guard_is_the_decoupled_superset() -> None:
    """The guard superset contains every spaced subcommand name plus ``novel``.

    Pins the multiplexer-only surface (ADR 007): the spaced ``novel <verb>``
    subcommand vocabulary is subsumed by the envelope guard, and the bare
    ``"novel"`` surface is present for the body-less help/version arms.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    assert set(SUBCOMMAND_NAMES) <= set(ENVELOPE_COMMAND_NAMES)
    assert "novel" in ENVELOPE_COMMAND_NAMES


def test_build_envelope_stamps_schema_version() -> None:
    """The envelope carries the module's schema-version constant.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[0],
        working_dir="working",
        code=ExitCode.SUCCESS,
        result={},
        messages=[],
    )
    assert env.schema_version == ENVELOPE_SCHEMA_VERSION


def test_render_machine_emits_fixed_field_order() -> None:
    """Machine mode emits the six keys in the fixed contract order.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[1],
        working_dir="working",
        code=ExitCode.ACTIONABLE_FINDING,
        result={"divergent": ["ch01"]},
        messages=["compiled.md diverges from chapter drafts"],
    )
    rendered = render_machine(env)
    parsed = json.loads(rendered)
    assert tuple(parsed) == _FIXED_FIELD_ORDER
    # ok mirrors the code; the harness gates on this, not on the prose.
    assert parsed["ok"] is is_ok(ExitCode.ACTIONABLE_FINDING)
    assert parsed["result"] == {"divergent": ["ch01"]}


def test_render_human_lists_messages_without_result_json() -> None:
    """Human mode writes each message on its own line and hides ``result``.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[1],
        working_dir="working",
        code=ExitCode.ACTIONABLE_FINDING,
        result={"divergent": ["ch01"]},
        messages=["first note", "second note"],
    )
    rendered = render_human(env)
    assert "  - first note" in rendered
    assert "  - second note" in rendered
    # The machine-only result payload must not leak into the human channel.
    assert "divergent" not in rendered
    assert "ch01" not in rendered


def test_render_machine_success_snapshot(snapshot: SnapshotAssertion) -> None:
    """Pin the machine rendering of a representative success envelope.

    ``working_dir`` is the design's own literal token ``"working"``; the
    envelope carries no timestamp or other path field, so there is nothing else
    to normalise (AGENTS.md snapshot guidance).

    Parameters
    ----------
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[0],
        working_dir="working",
        code=ExitCode.SUCCESS,
        result={"cursor": "ch01"},
        messages=["state initialised"],
    )
    rendered = render_machine(env)
    # Pair the snapshot with a semantic assertion so it is not the only guard.
    assert json.loads(rendered)["ok"] is True
    assert rendered == snapshot


def test_render_human_success_snapshot(snapshot: SnapshotAssertion) -> None:
    """Pin the human rendering of a representative success envelope.

    Parameters
    ----------
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[0],
        working_dir="working",
        code=ExitCode.SUCCESS,
        result={"cursor": "ch01"},
        messages=["state initialised"],
    )
    rendered = render_human(env)
    assert "ok: True" in rendered
    assert rendered == snapshot
