"""End-to-end reachability of ``novel-state set-chapters`` (roadmap 2.2.3, 6.2.4).

This proves the externally observable command-line behaviour of the subcommand:

- a fast entry-point check driven through ``stub.novel_state()`` (the installed
  console-script body) against an empty-manifest tree, proving ``novel-state
  set-chapters`` resolves, exits ``0``, and emits the write-shaped ``{chapters}``
  envelope (AGENTS.md "externally observable workflows … command-line behaviour");
- the slower wheel-build install e2es (POSIX-only, ADR-006; roadmap 6.2.4): the
  installed ``novel-state set-chapters`` populates ``[chapters]`` and exits ``0``;
  a malformed JSON ``--chapters`` and a missing required field each exit ``2`` (the
  cyclopts shape-fault channel, Surprise S2); and a non-contiguous plan exits ``3``
  (the body's semantic refusal) — each ``ok: false`` with no traceback.

The built-and-installed script is supplied by the module-scoped
``installed_novel_state`` fixture (``tests/installed_binary_fixtures.py``), so the
wheel is built once for the module and every installed case reuses it.
"""

from __future__ import annotations

import json
import os
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
_PLAN_JSON = (
    '[{"number": 1, "slug": "the-summons", "title": "The Summons", '
    '"target_words": 3200}, '
    '{"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800}]'
)
# The written-chapters oracle both the entry-point and installed proofs assert.
_WRITTEN: typ.Final = [
    {"number": 1, "slug": "the-summons", "title": "The Summons", "target_words": 3200},
    {"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800},
]


def _empty_manifest_tree(dest: Path) -> Path:
    """Build a coherent ``chapter-planning`` tree with an empty ``[chapters]``."""
    return wc.build_working_tree(wc.PHASE_STATES["chapter-planning"], dest)


def test_entry_point_set_chapters_reachable_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state set-chapters`` is reachable through the entry point (exit 0)."""
    working = _empty_manifest_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(
        sys, "argv", [_COMMAND, "set-chapters", "--chapters", _PLAN_JSON]
    )
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_state()
    assert excinfo.value.code == ExitCode.SUCCESS, (
        "the entry-point set-chapters must exit 0"
    )
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["chapters"] == _WRITTEN, (
        "the envelope must carry the written-chapters oracle"
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_set_chapters_exits_zero(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """Build, install, and run ``novel-state set-chapters`` against an empty manifest.

    The installed mutator runs with cuprum's ``ExecutionContext(cwd=run_dir)`` so it
    resolves ``./working/state.toml``, populates ``[chapters]``, and exits ``0`` with
    the written-chapters envelope — the same ``{chapters}`` oracle the in-process
    proof asserts, now against a real installed console-script. The 180s timeout
    supersedes the 30s project default.
    """
    run_dir = tmp_path / "run"
    _empty_manifest_tree(run_dir)

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)(
        "set-chapters", "--chapters", _PLAN_JSON
    ).run_sync(context=ExecutionContext(cwd=run_dir), capture=True)
    assert result.exit_code == 0, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True, "the installed set-chapters envelope must be ok"
    assert typ.cast("dict[str, object]", envelope["result"])["chapters"] == _WRITTEN, (
        "the installed envelope must carry the written-chapters oracle"
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize(
    "chapters_arg",
    ["[{not json", '[{"number":1,"slug":"a"}]'],
    ids=["malformed-json", "missing-required-field"],
)
def test_installed_novel_state_set_chapters_shape_fault_exits_two(
    chapters_arg: str,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """A shape fault — malformed JSON or a missing field — exits ``2`` (usage error).

    Both routes raise a cyclopts ``CoercionError`` at parse, which the runner maps
    to exit ``2`` (Surprise S2; Decision D6), proving the exit-2 shape channel at
    the installed boundary. Each exits ``2`` with ``ok: false`` and no traceback.
    """
    run_dir = tmp_path / "run"
    _empty_manifest_tree(run_dir)

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)(
        "set-chapters", "--chapters", chapters_arg
    ).run_sync(context=ExecutionContext(cwd=run_dir), capture=True)
    assert result.exit_code == 2, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "a shape fault must yield an ok: false envelope"
    )
    assert "Traceback" not in (result.stderr or ""), "a usage error emits no traceback"


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_set_chapters_incoherent_exits_three(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """A non-contiguous plan exits ``3`` (the body's semantic refusal channel).

    Numbers ``[1, 3]`` parse cleanly (a well-typed JSON array) but break the
    ``numbers-contiguous-from-1`` coherence rule, so the body refuses with exit
    ``3`` (Decision D6), distinct from the exit-2 shape faults. ``ok: false`` with
    no traceback.
    """
    run_dir = tmp_path / "run"
    _empty_manifest_tree(run_dir)
    non_contiguous = (
        '[{"number": 1, "slug": "a", "title": "A", "target_words": 10}, '
        '{"number": 3, "slug": "c", "title": "C", "target_words": 30}]'
    )

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)(
        "set-chapters", "--chapters", non_contiguous
    ).run_sync(context=ExecutionContext(cwd=run_dir), capture=True)
    assert result.exit_code == 3, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "a semantic refusal must yield an ok: false envelope"
    )
    assert "Traceback" not in (result.stderr or ""), "a state error emits no traceback"
