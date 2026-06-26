"""End-to-end reachability of ``novel-state recount`` (roadmap 2.3.1, 6.2.4).

This proves the externally observable command-line behaviour of the subcommand:

- a fast entry-point check driven through ``novel.main()`` (the installed
  console-script body) against a prepared two-chapter tree, proving
  ``novel-state recount`` resolves, exits ``0``, and emits an envelope naming the
  recounted ``{current, by_chapter}`` counts (AGENTS.md "externally observable
  workflows … command-line behaviour");
- the slower wheel-build install e2es (POSIX-only, ADR-006; roadmap 6.2.4): the
  installed ``novel-state recount`` corrects wrong counts and exits ``0`` with the
  recounted envelope, and refuses a missing or unparseable ``state.toml`` by
  exiting ``3`` with an ``ok: false`` envelope and no traceback — the mutator and
  its exit-3 state-error path proven against a real installed console-script, not
  only in-process.

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

from novel_ralph_skill.commands import novel
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

_COMMAND = "novel state"
# The recounted oracle both proofs assert: chapters draft 3 and 5 words, so
# ``recount`` rewrites the deliberately wrong ``[word_counts]`` to this envelope.
_RECOUNTED_RESULT: typ.Final = {"current": 8, "by_chapter": {"01": 3, "02": 5}}


def _stale_two_chapter_spec() -> wc.WorkingTreeSpec:
    """Return a two-chapter drafting spec with deliberately wrong word counts.

    Chapters draft 3 and 5 words but the ``[word_counts]`` table claims 999 each
    and a 1998 total, so ``recount`` must rewrite them to ``_RECOUNTED_RESULT``.
    Shared by the in-process and installed-binary recount proofs so both assert the
    same oracle.

    Returns
    -------
    wc.WorkingTreeSpec
        The two-chapter drafting spec carrying the stale ``[word_counts]`` table.
    """
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
    return wc.WorkingTreeSpec(
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


def test_entry_point_recount_reachable_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state recount`` is reachable through the entry point (exit ``0``)."""
    working = wc.build_working_tree(_stale_two_chapter_spec(), tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "recount"])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == _RECOUNTED_RESULT


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_recount_exits_zero(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """Build, install, and run ``novel-state recount`` against a stale tree.

    The installed mutator runs with cuprum's ``ExecutionContext(cwd=run_dir)`` so
    it resolves ``./working/state.toml``, rewrites the deliberately wrong
    ``[word_counts]``, and exits ``0`` with the recounted envelope — the same
    ``{current, by_chapter}`` oracle the in-process proof asserts, now proven
    against a real installed console-script. The ``installed_novel_state`` fixture
    supplies the script path (built once per module). The 180s timeout supersedes
    the 30s project default.
    """
    run_dir = tmp_path / "run"
    wc.build_working_tree(_stale_two_chapter_spec(), run_dir)

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)("state", "recount").run_sync(
        context=ExecutionContext(cwd=run_dir), capture=True
    )
    assert result.exit_code == 0, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True
    assert typ.cast("dict[str, object]", envelope["result"]) == _RECOUNTED_RESULT


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize(
    "state_bytes",
    [None, b"not = toml ="],
    ids=["missing-state", "unparseable-state"],
)
def test_installed_novel_state_recount_state_error_exits_three(
    state_bytes: bytes | None,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """The installed ``novel-state recount`` exits ``3`` on a bad ``state.toml``.

    Two fault shapes drive the exit-3 state-or-input-error channel (design §3.2;
    ADR-003 Table 2): a ``working/`` with no ``state.toml`` (``state_bytes is
    None``) and a ``working/state.toml`` of invalid TOML (``b"not = toml ="``,
    mirroring the in-process ``check`` proof). Verification choice: the boundary is
    a small, enumerable pair, so a two-case ``parametrize`` is the right adversary,
    not Hypothesis (the in-process recount property coverage already exists). The
    installed mutator runs with cuprum's ``ExecutionContext(cwd=run_dir)`` so it
    resolves ``./working/state.toml``; driving the named mutator over an
    incoherent request proves the mutator-refusal-is-3 rule (design §3.2) at the
    installed boundary. Each case asserts exit ``3``, an ``ok: false`` envelope,
    and no traceback on stderr (design §10 — a state fault yields a message, not a
    stack trace). The ``installed_novel_state`` fixture supplies the script path
    (built once per module); the 180s timeout supersedes the 30s project default.
    """
    run_dir = tmp_path / "run"
    working_dir = run_dir / "working"
    working_dir.mkdir(parents=True)
    if state_bytes is not None:
        (working_dir / "state.toml").write_bytes(state_bytes)

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)("state", "recount").run_sync(
        context=ExecutionContext(cwd=run_dir), capture=True
    )
    assert result.exit_code == 3, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False
    assert "Traceback" not in (result.stderr or "")
