"""Per-code machine-mode envelope snapshots.

These pin the rendered envelope shape for each :class:`ExitCode` (roadmap task
1.3.1 Work item 5: "a snapshot pins the envelope shape for each code"). Each
snapshot normalises ``working_dir`` to the design's literal ``"working"`` token;
the envelope carries no timestamp and no other path field, so there is nothing
else to redact. Each snapshot is paired with a semantic assertion that the
parsed JSON ``ok`` matches the code, so the snapshot is not the only guard
(AGENTS.md "avoid snapshot-only coverage").
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands.names import SUBCOMMAND_NAMES
from novel_ralph_skill.contract.envelope import build_envelope, render_machine
from novel_ralph_skill.contract.exit_codes import ExitCode, is_ok

if typ.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


@pytest.mark.parametrize("code", list(ExitCode), ids=lambda code: code.name)
def test_machine_envelope_per_code_snapshot(
    code: ExitCode, snapshot: SnapshotAssertion
) -> None:
    """Pin the machine rendering of an envelope for ``code``.

    Parameters
    ----------
    code : ExitCode
        The exit code whose envelope shape is pinned.
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
        code=code,
        result={"code_name": code.name},
        messages=[f"exit code {int(code)}"],
    )
    rendered = render_machine(env)
    # Pair the snapshot with a semantic assertion so it is not the only guard.
    assert json.loads(rendered)["ok"] is is_ok(code)
    assert rendered == snapshot
