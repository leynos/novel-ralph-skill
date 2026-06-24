"""End-to-end reachability of ``novel-state recount`` (roadmap 2.3.1).

This proves the externally observable command-line behaviour of the new
subcommand: driven through ``stub.novel_state()`` (the installed console-script
body) against a prepared two-chapter tree, ``novel-state recount`` resolves,
exits ``0``, and emits an envelope naming the recounted ``{current, by_chapter}``
counts (AGENTS.md "externally observable workflows … command-line behaviour").

The slower wheel-build install e2e is covered for ``check`` by
``tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero``;
this fast entry-point check is the cheapest proof that the ``recount`` subcommand
is wired into the real console-script path.
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

_COMMAND = "novel-state"


def test_entry_point_recount_reachable_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state recount`` is reachable through the entry point (exit ``0``)."""
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
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND, "recount"])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_state()
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"current": 8, "by_chapter": {"01": 3, "02": 5}}
