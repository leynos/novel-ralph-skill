"""Machine-mode envelope snapshots for ``novel-compile --check``.

Pins the rendered machine-mode JSON envelope for the ``--check`` checker on both
the ``MATCHES`` path (exit ``0``, ``diverged: false``) and the ``DIVERGES`` path
(exit ``4``, ``diverged: true``); design §9 ("Snapshot tests pin the machine-mode
JSON envelope per command"). The ``checked`` token is the working-relative
constant ``working/manuscript/compiled.md`` and ``working_dir`` is the fixed
``"working"`` token, both deterministic by construction, so no normalisation is
needed (ExecPlan D-RESULT). Each snapshot is paired with a semantic assertion on
the exit code, ``ok``, and ``result`` so it is not the only guard (AGENTS.md
"pair them with semantic assertions").

**Driver requirement (ExecPlan D-CHECK-ARGV).** :func:`_drive_check` passes
``["--check"]`` (not ``[]``) to ``run`` so the checker, not the write path, is
snapshotted; a ``[]``-argv copy would capture the write envelope and the
``diverged`` field would never appear.
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
# Present-but-stale bytes: the DIVERGES path.
_STALE_COMPILED = "STALE — not the ordered concatenation"


def _drive_check() -> tuple[int, str]:
    """Run ``novel-compile --check`` through ``run``; return ``(code, stdout)``."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _check_tree(compiled: str | None, tmp_path: Path) -> Path:
    """Build a three-chapter ``drafting`` tree carrying ``compiled`` on disk."""
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
        compiled=compiled,
    )
    return wc.build_working_tree(spec, tmp_path)


def test_check_matches_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin the ``--check`` MATCHES envelope: exit ``0``, ``diverged: false``."""
    working = _check_tree(wc.COMPILED_AUTO, tmp_path)
    monkeypatch.chdir(working.parent)
    code, raw = _drive_check()
    assert code == ExitCode.SUCCESS
    envelope = json.loads(raw)
    assert envelope["ok"] is True
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {
        "checked": "working/manuscript/compiled.md",
        "chapters": len(_COUNTS),
        "diverged": False,
    }
    assert "violations" not in result
    assert raw == snapshot


def test_check_diverges_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin the ``--check`` DIVERGES envelope: exit ``4``, ``diverged: true``."""
    working = _check_tree(_STALE_COMPILED, tmp_path)
    monkeypatch.chdir(working.parent)
    code, raw = _drive_check()
    assert code == ExitCode.ACTIONABLE_FINDING
    envelope = json.loads(raw)
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {
        "checked": "working/manuscript/compiled.md",
        "chapters": len(_COUNTS),
        "diverged": True,
    }
    assert "violations" not in result
    assert raw == snapshot
