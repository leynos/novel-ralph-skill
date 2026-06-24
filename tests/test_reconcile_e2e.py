"""End-to-end reachability of ``novel-state reconcile`` (roadmap 2.3.2, 2.3.4).

Proofs of the externally observable command-line behaviour of the subcommand:

- fast entry-point checks driven through ``stub.novel_state()`` (the installed
  console-script body), proving ``novel-state reconcile`` resolves and repairs the
  roadmap headline ``recount`` tree and the partial-``init`` log-absent tree, each
  exiting ``0`` with a write-shaped envelope;
- the slower wheel-build install e2es (POSIX-only, ADR-006): each builds and
  installs the wheel into a fresh venv, materialises a stale or log-absent tree
  under the subprocess cwd, runs the installed ``novel-state reconcile`` (exit
  ``0``), and confirms a follow-up ``check`` is coherent (exit ``0``) — the
  recovery routine running as a real installed command, not a Python import.

The built-and-installed ``novel-state`` script is supplied by the module-scoped
``installed_novel_state`` fixture (``tests/installed_binary_fixtures.py``), so the
wheel is built once for the module and both installed e2es reuse it; the fixture
replaces the former cross-module ``_build_and_install_novel_state`` import
(roadmap 6.2.4; locked ``cuprum==0.1.0``).
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


def test_entry_point_reconcile_repairs_cover_gap_then_check_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reconcile supplies a `by_chapter` key the table omitted, then check is clean.

    Drives the roadmap task 2.3.6 headline through the entry point: a tree whose
    ``[word_counts].by_chapter`` omits the drafted ``"04"`` key exits ``4`` on
    ``word-counts-cover-drafts`` with a ``recount`` reconciliation; ``reconcile``
    writes the missing key with its drafted count; and a re-``check`` exits ``0``.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS[
        "word-counts-cover-drafts-omits-drafted-chapter"
    ]
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    monkeypatch.setattr(sys, "argv", [_COMMAND, "check"])
    with pytest.raises(SystemExit) as check_before:
        stub.novel_state()
    assert check_before.value.code == ExitCode.ACTIONABLE_FINDING
    before_env = json.loads(capsys.readouterr().out)
    before_result = typ.cast("dict[str, object]", before_env["result"])
    assert "word-counts-cover-drafts" in typ.cast(
        "list[str]", before_result["violations"]
    )
    reconciliation = typ.cast("dict[str, object]", before_result["reconciliation"])
    assert reconciliation["action"] == "recount"

    monkeypatch.setattr(sys, "argv", [_COMMAND, "reconcile"])
    with pytest.raises(SystemExit) as reconcile_exit:
        stub.novel_state()
    assert reconcile_exit.value.code == ExitCode.SUCCESS
    reconcile_result = typ.cast(
        "dict[str, object]", json.loads(capsys.readouterr().out)["result"]
    )
    assert reconcile_result["action"] == "recount"
    assert reconcile_result["by_chapter"] == {
        "01": 32000,
        "02": 32000,
        "03": 32000,
        "04": 4000,
    }

    monkeypatch.setattr(sys, "argv", [_COMMAND, "check"])
    with pytest.raises(SystemExit) as check_after:
        stub.novel_state()
    assert check_after.value.code == ExitCode.SUCCESS


def test_entry_point_reconcile_drops_orphan_cover_key_then_check_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reconcile drops an orphan `by_chapter` key, then check is clean.

    The symmetric coverage-gap direction to ``cover_gap_then_check_clean``: a tree
    whose ``[word_counts].by_chapter`` carries an orphan ``"05"`` key the manifest
    never declares exits ``4`` on ``word-counts-cover-drafts`` with a ``recount``
    reconciliation; ``reconcile`` re-keys the table off the three-chapter manifest,
    dropping the orphan key; and a re-``check`` exits ``0``.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["word-counts-cover-drafts-extra-table-key"]
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    monkeypatch.setattr(sys, "argv", [_COMMAND, "check"])
    with pytest.raises(SystemExit) as check_before:
        stub.novel_state()
    assert check_before.value.code == ExitCode.ACTIONABLE_FINDING
    before_env = json.loads(capsys.readouterr().out)
    before_result = typ.cast("dict[str, object]", before_env["result"])
    assert "word-counts-cover-drafts" in typ.cast(
        "list[str]", before_result["violations"]
    )
    reconciliation = typ.cast("dict[str, object]", before_result["reconciliation"])
    assert reconciliation["action"] == "recount"

    monkeypatch.setattr(sys, "argv", [_COMMAND, "reconcile"])
    with pytest.raises(SystemExit) as reconcile_exit:
        stub.novel_state()
    assert reconcile_exit.value.code == ExitCode.SUCCESS
    reconcile_result = typ.cast(
        "dict[str, object]", json.loads(capsys.readouterr().out)["result"]
    )
    assert reconcile_result["action"] == "recount"
    assert reconcile_result["by_chapter"] == {
        "01": 24000,
        "02": 24000,
        "03": 20800,
    }, "reconcile must re-key off the manifest, dropping the orphan key"

    monkeypatch.setattr(sys, "argv", [_COMMAND, "check"])
    with pytest.raises(SystemExit) as check_after:
        stub.novel_state()
    assert check_after.value.code == ExitCode.SUCCESS


def test_entry_point_reconcile_recreates_absent_log_md(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state reconcile`` recreates an absent ``log.md`` (partial init)."""
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    (working / "log.md").unlink()
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND, "reconcile"])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_state()
    assert excinfo.value.code == ExitCode.SUCCESS, "reconcile must exit 0 on repair"
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["action"] == "recreate-log", "reconcile must report recreate-log"
    assert (working / "log.md").exists(), "reconcile must recreate the absent log.md"


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_reconcile_recreates_absent_log_md(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """Build, install, and run ``novel-state reconcile`` against a log-absent tree.

    The partial-``init`` recovery running as a real installed command: the tree has
    ``state.toml`` but no ``log.md``, the installed ``reconcile`` recreates it (exit
    ``0``), and a follow-up ``check`` exits ``0``. The ``installed_novel_state``
    fixture supplies the script path (built once per module). The 180s timeout
    supersedes the 30s project default.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    shutil.copytree(
        wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path / "fixture"),
        dest / "working",
    )
    (dest / "working" / "log.md").unlink()

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)

    reconcile_result = sh.make(prog, catalogue=catalogue)("reconcile").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert reconcile_result.exit_code == 0, reconcile_result.stderr
    reconcile_env = json.loads(reconcile_result.stdout or "{}")
    assert reconcile_env["ok"] is True
    assert typ.cast("dict[str, object]", reconcile_env["result"])["action"] == (
        "recreate-log"
    )
    assert (dest / "working" / "log.md").exists(), (
        "the installed run must recreate log.md"
    )

    check_result = sh.make(prog, catalogue=catalogue)("check").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert check_result.exit_code == 0, check_result.stderr


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_reconcile_repairs_stale_tree(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """Build, install, and run ``novel-state reconcile`` against a stale tree.

    The installed script runs with cuprum's ``ExecutionContext(cwd=dest)`` so it
    resolves ``./working/state.toml``, repairs the stale ``[word_counts]`` (exit
    ``0``), and a follow-up ``check`` exits ``0``. The ``installed_novel_state``
    fixture supplies the script path (built once per module). The 180s timeout
    supersedes the 30s project default.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    shutil.copytree(wc.build_working_tree(spec, tmp_path / "fixture"), dest / "working")

    prog = Program(str(installed_novel_state))
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
