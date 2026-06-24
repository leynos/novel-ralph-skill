"""Machine-mode envelope snapshot for ``novel-compile`` (roadmap task 4.1.1).

Pins the rendered machine-mode JSON envelope for the ``novel-compile`` success
path (design §9 "Snapshot tests pin the machine-mode JSON envelope per command").
Nondeterministic fields are normalised so the snapshot identifies a real contract
change, not churn: the ``compiled`` path is the working-relative token (not an
absolute path) and ``working_dir`` is the fixed ``"working"`` token, both by
construction (ExecPlan D-RESULT). The snapshot is paired with a semantic assertion
on the exit code, ``ok``, and the ``chapters``/``bytes`` values so it is not the
only guard (AGENTS.md "pair them with semantic assertions").
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._compile import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel-compile"
_COUNTS: tuple[int, ...] = (3, 5, 4)


def _drive() -> tuple[int, str]:
    """Run ``novel-compile`` through ``run`` and return ``(exit_code, raw_stdout)``."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _compile_tree(tmp_path: Path) -> Path:
    """Build a coherent three-chapter ``drafting`` tree (no ``compiled.md``)."""
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(_COUNTS, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
    )
    return wc.build_working_tree(spec, tmp_path)


def test_compile_success_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin ``novel-compile``'s success envelope: ``result`` names the write."""
    working = _compile_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    code, raw = _drive()
    assert code == ExitCode.SUCCESS
    envelope = json.loads(raw)
    assert envelope["ok"] is True
    # The write-shaped result names the path, chapters, and byte length and
    # carries no violations read shape (design §3.3; ExecPlan D-RESULT).
    result = typ.cast("dict[str, object]", envelope["result"])
    expected_bytes = len(
        wc.concatenate_drafts([wc.draft_body(count) for count in _COUNTS]).encode(
            "utf-8"
        )
    )
    assert result == {
        "compiled": "working/manuscript/compiled.md",
        "chapters": len(_COUNTS),
        "bytes": expected_bytes,
    }
    assert "violations" not in result
    # The envelope carries no absolute path, so it is deterministic with no
    # normalisation needed (the compiled path and working_dir are fixed tokens).
    assert raw == snapshot
