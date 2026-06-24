"""End-to-end reachability of ``novel-state reconcile`` (roadmap 2.3.2, Work item 6).

Two proofs of the externally observable command-line behaviour of the new
subcommand:

- a fast entry-point check driven through ``stub.novel_state()`` (the installed
  console-script body), proving ``novel-state reconcile`` resolves, repairs the
  roadmap headline tree, and exits ``0`` with a write-shaped envelope;
- the slower wheel-build install e2e (POSIX-only, ADR-006): it builds and installs
  the wheel into a fresh venv, materialises a stale tree under the subprocess cwd,
  runs the installed ``novel-state reconcile`` (exit ``0``), and confirms a
  follow-up ``check`` is coherent (exit ``0``) — the recovery routine running as a
  real installed command, not a Python import.

The wheel build/install helper ``_build_and_install_novel_state`` is reused
verbatim from ``test_novel_state_check.py`` (D-CUPRUM: locked ``cuprum==0.1.0``).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import typing as typ

import pytest
import working_corpus as wc
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext
from test_novel_state_check import _build_and_install_novel_state

from novel_ralph_skill.commands import stub
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

_COMMAND = "novel-state"


def test_entry_point_reconcile_reachable_repairs_and_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state reconcile`` is reachable through the entry point and repairs."""
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND, "reconcile"])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_state()
    assert excinfo.value.code == ExitCode.SUCCESS, "reconcile must exit 0 on repair"
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["action"] == "recount", "reconcile must report the recount action"
    assert result["by_chapter"] == {"01": 0, "02": 24000, "03": 20800}, (
        "reconcile must write the disk-derived per-chapter counts"
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_reconcile_repairs_stale_tree(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """Build, install, and run ``novel-state reconcile`` against a stale tree.

    The installed script runs with cuprum's ``ExecutionContext(cwd=dest)`` so it
    resolves ``./working/state.toml``, repairs the stale ``[word_counts]`` (exit
    ``0``), and a follow-up ``check`` exits ``0``. The 180s timeout supersedes the
    30s project default.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    shutil.copytree(wc.build_working_tree(spec, tmp_path / "fixture"), dest / "working")

    script_path = _build_and_install_novel_state(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    prog = Program(str(script_path))
    catalogue = single_program_catalogue("novel-state-run", prog)

    reconcile_result = sh.make(prog, catalogue=catalogue)("reconcile").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert reconcile_result.exit_code == 0, reconcile_result.stderr
    reconcile_env = json.loads(reconcile_result.stdout or "{}")
    assert reconcile_env["ok"] is True
    assert typ.cast("dict[str, object]", reconcile_env["result"])["action"] == "recount"

    check_result = sh.make(prog, catalogue=catalogue)("check").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert check_result.exit_code == 0, check_result.stderr
