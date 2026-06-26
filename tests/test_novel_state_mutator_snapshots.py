"""Machine-mode envelope snapshots for the ``novel-state`` mutators (roadmap 2.2.2).

These pin the rendered machine-mode JSON envelope for each mutator's success and
refusal paths (design §9 "Snapshot tests pin the machine-mode JSON envelope per
command"). Nondeterministic fields are normalised so a snapshot identifies a real
contract change, not churn: the ``created_at`` timestamp ``init`` stamps is
redacted, and the envelope carries no absolute path (``working_dir`` is the fixed
``"working"`` token). Each snapshot is paired with a semantic assertion on the
exit code and the envelope ``ok`` so the snapshot is not the only guard (AGENTS.md
"pair them with semantic assertions").
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest
import working_corpus as wc
from _gate_drafting_fixtures import build, ratio_not_crossed_spec

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec
    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel state"
# Redact the RFC 3339 timestamp ``init`` stamps into ``[novel].created_at`` (it
# never reaches the envelope today, but normalise defensively per AGENTS.md).
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?"
)


def _drive(argv: list[str]) -> tuple[int, str]:
    """Run ``argv`` through ``run`` and return ``(exit_code, raw_stdout)``."""
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _normalise(raw: str) -> str:
    """Redact nondeterministic fields from the rendered envelope."""
    return _TIMESTAMP.sub("<timestamp>", raw)


def test_init_success_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``init``'s success envelope (exit ``0``, ``ok: true``)."""
    monkeypatch.chdir(tmp_path)
    code, raw = _drive(["init", "--title", "T", "--slug", "s"])
    assert code == ExitCode.SUCCESS
    assert json.loads(raw)["ok"] is True
    assert _normalise(raw) == snapshot


def test_set_cursor_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-cursor``'s success envelope: ``result`` is the cursor it set."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names the cursor and carries no ``violations``
    # read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"current_chapter": 2, "current_scene": 0, "current_beat": 0}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_set_cursor_refusal_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-cursor``'s refusal envelope (exit ``3``, ``ok: false``)."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-cursor", "--chapter", "99"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot


def test_advance_phase_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``advance-phase``'s success envelope: ``result`` names the transition."""
    working = phase_state_tree("premise")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["advance-phase"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names the transition and carries no
    # ``violations`` read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"from": "premise", "to": "treatment"}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_advance_phase_refusal_envelope_snapshot(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``advance-phase``'s out-of-order refusal envelope (exit ``3``)."""
    _spec, working, _expected = incoherent_tree("completed-prefix-gap")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["advance-phase"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot


def _recount_tree(tmp_path: Path) -> Path:
    """Build a small two-chapter ``drafting`` tree (3 + 5 words) for the snapshot."""
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in ((1, 3), (2, 5))
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        by_chapter_override={"01": 999, "02": 999},
        current_words_override=1998,
    )
    return wc.build_working_tree(spec, tmp_path)


def test_recount_success_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``recount``'s success envelope: ``result`` names the counts it wrote."""
    working = _recount_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["recount"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names the counts and carries no ``violations``
    # read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"current": 8, "by_chapter": {"01": 3, "02": 5}}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_complete_final_pass_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``complete-final-pass``'s success envelope: ``result`` names the gate."""
    working = phase_state_tree("final-pass")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["complete-final-pass"])
    assert code == ExitCode.SUCCESS
    # The write-shaped ``result`` names only the changed final gate and carries no
    # ``violations`` read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"gates": {"final": {"final_pass_complete": True}}}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_set_fangirl_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-fangirl``'s success envelope: ``result`` names the fangirl field."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-fangirl", "--last-chapter", "1"])
    assert code == ExitCode.SUCCESS
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"drafting": {"fangirl": {"last_chapter_passed": 1}}}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_set_fangirl_refusal_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-fangirl``'s out-of-manifest refusal envelope (exit ``3``)."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    # The ``drafting`` corpus tree carries a three-chapter manifest, so chapter 4
    # is past the manifest and the precondition refuses it.
    code, raw = _drive(["set-fangirl", "--last-chapter", "4"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot


def test_set_critic_pass_success_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-critic-pass``'s success envelope: ``result`` names the pass."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-critic-pass", "--pass", "2"])
    assert code == ExitCode.SUCCESS
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result == {"drafting": {"critic": {"pass": 2}}}
    assert "violations" not in result
    assert _normalise(raw) == snapshot


def test_set_critic_pass_refusal_envelope_snapshot(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-critic-pass``'s below-one refusal envelope (exit ``3``)."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    # Passes are numbered from 1, so ``--pass 0`` breaches the precondition.
    code, raw = _drive(["set-critic-pass", "--pass", "0"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot


def test_set_gate_refusal_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``set-gate``'s below-threshold refusal envelope (exit ``3``).

    The ``ratio_not_crossed`` prior drafts a 0.15 ratio with every knitting gate
    false, so asserting ``done_30`` contradicts the §5.2 ``gate-ratio-consistent``
    invariant and is refused.
    """
    working = build(ratio_not_crossed_spec(), tmp_path)
    monkeypatch.chdir(working.parent)
    code, raw = _drive(["set-gate", "--knitting-30"])
    assert code == ExitCode.STATE_ERROR
    assert json.loads(raw)["ok"] is False
    assert _normalise(raw) == snapshot
