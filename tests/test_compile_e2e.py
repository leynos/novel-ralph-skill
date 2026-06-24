"""End-to-end reachability of ``novel-compile`` (roadmap task 4.1.1).

This proves the externally observable command-line behaviour of the now-real
command: driven through ``stub.novel_compile()`` (the installed console-script
body) against a prepared drafting tree, ``novel-compile`` resolves, exits ``0``,
emits an envelope naming the written ``compiled.md``, and writes the file with
the ordered draft concatenation. An empty-manifest tree refuses with exit ``3``.

The slower wheel-build install e2e for the spine lives in
``tests/test_console_scripts_e2e.py``; this fast entry-point check is the
cheapest proof that ``novel-compile`` is wired into the real console-script path
(mirroring ``tests/test_recount_e2e.py``).
"""

from __future__ import annotations

import json
import sys
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import stub
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-compile"


def _drafting_tree(tmp_path: Path) -> tuple[Path, str]:
    """Build a coherent three-chapter ``drafting`` tree; return it and its compile.

    Returns
    -------
    tuple[pathlib.Path, str]
        The materialised ``working/`` path and the expected ``compiled.md`` bytes.
    """
    counts = (3, 5, 4)
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(counts, start=1)
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
    working = wc.build_working_tree(spec, tmp_path)
    expected = wc.concatenate_drafts([wc.draft_body(count) for count in counts])
    return working, expected


def test_entry_point_compile_reachable_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-compile`` is reachable through the entry point and writes the file."""
    working, expected = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_compile()
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compiled"] == "working/manuscript/compiled.md"
    compiled = working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == expected


def test_entry_point_compile_empty_manifest_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty-manifest tree refuses with exit ``3`` and writes no ``compiled.md``."""
    working = wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_compile()
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert json.loads(capsys.readouterr().out)["ok"] is False
    assert not (working / "manuscript" / "compiled.md").exists()
