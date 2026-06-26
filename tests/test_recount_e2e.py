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
_TARGET_WORDS: typ.Final = 80000
# The load-bearing actionable substrings each gate-breach proof asserts, derived
# from the pinned message template (ExecPlan Work item 2 "Acceptance substrings").
_UPWARD_SUBSTRINGS: typ.Final = (
    "crossed the 30% knitting threshold",
    "gate done_30 is still false",
    "set-gate --knitting-30",
    "Do not hand-edit [gates]",
)
_DOWNWARD_SUBSTRINGS: typ.Final = (
    "left drafting below the 80% knitting threshold",
    "gate done_80 is recorded true",
    "Adjudicate",
)


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


def test_entry_point_recount_upward_gate_breach_is_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The entry point refuses an upward gate breach with the actionable message.

    A fast, non-``slow`` proof that does not need the wheel build: a recount that
    crosses the 30% threshold while done_30 is false exits ``3`` with an
    ``ok: false`` envelope whose ``messages`` carry the upward remedy. The slower
    installed-binary variant proves the same against a real console-script.
    """
    working = wc.build_working_tree(_upward_gate_breach_spec(), tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "recount"])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.STATE_ERROR
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False
    messages = typ.cast("list[str]", envelope["messages"])
    for substring in _UPWARD_SUBSTRINGS:
        assert any(substring in line for line in messages), (
            f"no message contained {substring!r}; messages were {messages!r}"
        )


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


def _run_installed_recount(
    spec: wc.WorkingTreeSpec,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> dict[str, object]:
    """Build ``spec``, run the installed ``recount``, and return its exit-3 envelope.

    Asserts the installed mutator exits ``3`` with an ``ok: false`` envelope and no
    traceback, then returns the parsed envelope so the caller can assert on
    ``messages``. Shared by the upward and downward gate-breach installed proofs.
    """
    run_dir = tmp_path / "run"
    wc.build_working_tree(spec, run_dir)

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)("state", "recount").run_sync(
        context=ExecutionContext(cwd=run_dir), capture=True
    )
    assert result.exit_code == 3, result.stderr
    assert "Traceback" not in (result.stderr or "")
    envelope = typ.cast("dict[str, object]", json.loads(result.stdout or "{}"))
    assert envelope["ok"] is False
    return envelope


def _gate_breach_spec(
    *,
    draft_words: int,
    by_chapter_override: dict[str, int],
    current_words_override: int,
    gates: tuple[bool, bool, bool],
) -> wc.WorkingTreeSpec:
    """Return a one-chapter drafting spec whose recount breaches a knitting gate.

    The chapter drafts ``draft_words`` on disk while the hand-typed
    ``[word_counts]`` records ``by_chapter_override``/``current_words_override``,
    chosen so the prior state is coherent with ``gates`` — so the exit-3 refusal
    is the recount re-deriving the counts, not a pre-existing breach.
    """
    chapter = wc.ChapterSpec(
        number=1,
        slug="chapter-01",
        title="Chapter 1",
        target_words=_TARGET_WORDS,
        draft_words=draft_words,
        has_done_flag=False,
    )
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=(chapter,),
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=1,
        by_chapter_override=by_chapter_override,
        current_words_override=current_words_override,
        done_30=gates[0],
        done_50=gates[1],
        done_80=gates[2],
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_recount_downward_gate_breach_does_not_prescribe(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """The installed ``recount`` adjudicates a downward gate breach, never repairs.

    A recount that leaves drafting below the 80% threshold while done_80 is
    recorded true exits ``3`` with the downward message (adjudicate, restore or
    clear) and **no** ``set-gate --knitting-80`` verb on any ``messages`` line —
    proving the upward repair verb cannot leak onto the downward path at the
    installed boundary (resolves design-review B2 end to end).
    """
    envelope = _run_installed_recount(
        _downward_gate_breach_spec(),
        tmp_path,
        single_program_catalogue,
        installed_novel_state,
    )
    messages = typ.cast("list[str]", envelope["messages"])
    for substring in _DOWNWARD_SUBSTRINGS:
        assert any(substring in line for line in messages), (
            f"no message contained {substring!r}; messages were {messages!r}"
        )
    assert all("set-gate --knitting-80" not in line for line in messages), (
        f"the downward path must not prescribe set-gate; messages were {messages!r}"
    )


def _downward_gate_breach_spec() -> wc.WorkingTreeSpec:
    """Return a spec whose recount drops the ratio to 0.55 with done_80 true."""
    return _gate_breach_spec(
        draft_words=44000,
        by_chapter_override={"01": 68800},
        current_words_override=68800,
        gates=(True, True, True),
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_recount_upward_gate_breach_is_actionable(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """The installed ``recount`` refuses an upward gate breach with the remedy.

    A recount that crosses the 30% threshold while done_30 is false exits ``3``
    with an ``ok: false`` envelope whose ``messages`` carry the upward remedy
    (the crossed threshold, the recounted percentage, and the ``set-gate
    --knitting-30`` verb), proven against a real installed console-script.
    """
    envelope = _run_installed_recount(
        _upward_gate_breach_spec(),
        tmp_path,
        single_program_catalogue,
        installed_novel_state,
    )
    messages = typ.cast("list[str]", envelope["messages"])
    for substring in _UPWARD_SUBSTRINGS:
        assert any(substring in line for line in messages), (
            f"no message contained {substring!r}; messages were {messages!r}"
        )


def _upward_gate_breach_spec() -> wc.WorkingTreeSpec:
    """Return a spec whose recount lifts the ratio to 0.34 with done_30 false."""
    return _gate_breach_spec(
        draft_words=27200,
        by_chapter_override={"01": 100},
        current_words_override=100,
        gates=(False, False, False),
    )
