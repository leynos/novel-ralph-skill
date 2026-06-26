"""Mutator success/refusal envelope identity pin + snapshots (roadmap 6.3.2 WI5).

For each ``novel state`` mutator this module drives its success path and one
refusal path in-process over a fresh per-cell tree and asserts the *envelope
skeleton* (six fields, order, types, ``working_dir``, ``schema_version``) is
identical to every other command's — the cross-command identity claim §6.2.1
explicitly carried as a gap (its module docstring lines 54-61). The success path
exits 0 with ``ok: true`` and a ``result`` mapping (its contents are
command-specific and snapshotted, never asserted equal across commands); the
refusal path exits 3 with ``ok: false``, an empty ``result``, and a non-blank
message — the same state-channel shape every command shares (design §3.1, §3.3).

The redacted success and refusal envelopes are snapshotted per mutator, reusing
the ``created_at`` timestamp redaction from
``tests/test_novel_state_mutator_snapshots.py``, paired with the semantic
exit-code/``ok`` assertions so a snapshot is not the only guard (AGENTS.md). Two
different mutators' ``result`` are never asserted equal — that would contradict
§3.1/§3.3; only the skeleton and the success/refusal exit-code-to-ok mapping are
asserted identical.
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest
from contract_drive_support import CommandSpec, assert_no_volatile_fields

from novel_ralph_skill.commands import novel_state
from novel_ralph_skill.contract.exit_codes import ExitCode

from ._identity_assertions import assert_envelope_skeleton
from ._mutator_cases import MUTATOR_CASES

if typ.TYPE_CHECKING:
    from pathlib import Path

    from contract_drive_support import Driver
    from syrupy.assertion import SnapshotAssertion

    from ._mutator_cases import MutatorCase

# The spaced command name every ``novel state`` mutator stamps into its envelope.
_STATE_COMMAND = "novel state"
_CASE_IDS: tuple[str, ...] = tuple(case.verb for case in MUTATOR_CASES)

# Redact the RFC 3339 timestamp ``init`` stamps into ``[novel].created_at`` so a
# snapshot identifies a real contract change, not churn (mirrors
# ``tests/test_novel_state_mutator_snapshots.py``).
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?"
)

# Redact the per-run temporary directory the actionable exit-3 message names (the
# §6.3.1 ``no novel working/ found in {cwd}`` remedy) so the refusal snapshot
# pins the shared message contract, not the volatile absolute path.
_CWD = re.compile(r"(no novel working/ found in )[^;]+(;)")


def _spec(argv: list[str]) -> CommandSpec:
    """Return a :class:`CommandSpec` driving ``novel state`` over ``argv``."""
    return CommandSpec(_STATE_COMMAND, novel_state.build_app, argv)


def _normalise(envelope: dict[str, object]) -> dict[str, object]:
    """Return ``envelope`` with timestamps, the cwd, and the body path redacted.

    Replaces any RFC 3339 timestamp with ``<timestamp>`` and the per-run
    temporary directory named by the §6.3.1 actionable exit-3 message with
    ``<cwd>``. ``init``'s ``result.working_dir`` body — which the production code
    now stamps with the absolute resolved path (roadmap §6.3.4) — is replaced
    with a stable ``<working-dir>`` token so the snapshot stays machine-
    independent; the *top-level* envelope ``working_dir`` is the synthetic
    ``drive`` label (the fixed ``"working"`` token) and is left verbatim.

    Parameters
    ----------
    envelope : dict[str, object]
        The parsed machine-mode envelope.

    Returns
    -------
    dict[str, object]
        The envelope re-parsed with timestamps, the cwd, and the body path
        redacted.
    """
    redacted = _TIMESTAMP.sub("<timestamp>", json.dumps(envelope))
    redacted = _CWD.sub(r"\1<cwd>\2", redacted)
    reparsed = typ.cast("dict[str, object]", json.loads(redacted))
    result = reparsed.get("result")
    if isinstance(result, dict) and "working_dir" in result:
        typ.cast("dict[str, object]", result)["working_dir"] = "<working-dir>"
    return reparsed


@pytest.mark.parametrize("case", MUTATOR_CASES, ids=_CASE_IDS)
def test_mutator_success_skeleton_identity(
    case: MutatorCase,
    tmp_path: Path,
    drive: Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Each mutator's success envelope shares the skeleton; its ``result`` is pinned.

    Drives the success path and asserts the shared skeleton (six fields in order,
    types, ``working_dir``, ``schema_version``), exit 0, ``ok: true``, and a
    ``result`` mapping. The command-specific ``result`` is snapshotted (redacted
    for the ``init`` timestamp), never asserted equal across mutators.

    Parameters
    ----------
    case : MutatorCase
        The mutator's success and refusal drive specs.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.
    """
    working = case.success_tree(tmp_path)
    code, raw = drive(_spec(case.success_argv), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.SUCCESS
    assert_envelope_skeleton(envelope, command=_STATE_COMMAND, code=code)
    assert envelope["ok"] is True
    assert isinstance(envelope["result"], dict)
    assert _normalise(envelope) == snapshot


@pytest.mark.parametrize("case", MUTATOR_CASES, ids=_CASE_IDS)
def test_mutator_refusal_skeleton_identity(
    case: MutatorCase,
    tmp_path: Path,
    drive: Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Each mutator's refusal envelope shares the state-channel skeleton.

    Drives the refusal path and asserts the shared skeleton, exit 3,
    ``ok: false``, an empty ``result``, and a non-blank message — the same
    state-channel shape every command shares. The redacted envelope is
    snapshotted, paired with the semantic assertions.

    Parameters
    ----------
    case : MutatorCase
        The mutator's success and refusal drive specs.
    tmp_path : Path
        The per-test temporary directory.
    drive : Driver
        The shared in-process driver fixture.
    snapshot : syrupy.assertion.SnapshotAssertion
        The syrupy snapshot fixture.
    """
    working = case.refusal_tree(tmp_path)
    code, raw = drive(_spec(case.refusal_argv), working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == ExitCode.STATE_ERROR
    assert_envelope_skeleton(envelope, command=_STATE_COMMAND, code=code)
    assert envelope["ok"] is False
    assert envelope["result"] == {}
    messages = typ.cast("list[str]", envelope["messages"])
    assert any(line.strip() for line in messages), "a refusal must carry a message"
    assert_no_volatile_fields({**envelope, "messages": ["<redacted>"]})
    assert _normalise(envelope) == snapshot
