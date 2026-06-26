"""In-process tests for the wired ``novel-done`` command (roadmap tasks 3.1.1-3.1.2).

These drive the real ``novel-done`` Cyclopts app through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
``tests/test_desloppify_command.py`` (``monkeypatch.chdir`` into a materialised
``working/`` parent, ``capsys`` to read the emitted envelope). They pin every
observable exit-code outcome from the ExecPlan purpose (design §4.2, §3.2): the
all-six-clauses-hold tree exits ``0`` with ``ok: true``; each single-clause-fail
tree exits ``1`` with ``ok: false`` (including the absent-``compiled.md`` tree,
proving the absent compile drives a benign ``1`` rather than a false ``0``); the
sole-stale-*present*-compile tree exits ``4`` (the 3.1.2 ``ACTIONABLE_FINDING``
carve-out) while a mid-draft stale compile and a stale compile paired with each
other unmet clause stay at ``1`` (the carve-out is exclusive); a
missing/unparseable ``state.toml``, an undecodable ``critic-notes.md``, and an
undecodable ``compiled.md`` each exit ``3`` (the D-FAULT negative tests); and a
stray positional token exits ``2`` (the runner's ``CycloptsError`` arm).
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands._novel_done import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from working_corpus import WorkingTreeSpec

_COMMAND = "novel done"
_CLAUSE_KEYS: tuple[str, ...] = (
    "phase_is_done",
    "final_pass_complete",
    "all_chapters_flagged",
    "knitting_gates_passed",
    "compile_consistent",
    "no_unresolved_blockers",
)


def _run_capture(
    working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str] | None = None,
) -> tuple[int, dict[str, object]]:
    """Drive ``novel-done`` from ``working.parent``; return ``(code, envelope)``."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv or [],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    raw = capsys.readouterr().out
    return int(typ.cast("int", excinfo.value.code)), json.loads(raw)


def _first_chapter_dir(working: Path) -> Path:
    """Return the lowest-numbered ``chapter-NN`` directory under ``working``."""
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "tree must contain at least one chapter directory"
    return chapters[0]


def test_all_hold_tree_exits_zero(
    all_hold_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The all-six-clauses-hold tree exits ``0`` with every clause true."""
    code, envelope = _run_capture(all_hold_tree(), monkeypatch, capsys)
    assert code == ExitCode.SUCCESS
    assert envelope["ok"] is True
    result = typ.cast("dict[str, object]", envelope["result"])
    assert tuple(result) == _CLAUSE_KEYS
    assert all(value is True for value in result.values())


def test_each_failer_exits_one(
    done_predicate_failer_names: tuple[str, ...],
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each single-clause-fail tree exits ``1`` (never ``0`` and never ``4``)."""
    for name in done_predicate_failer_names:
        _spec, working = done_predicate_failer_tree(name)
        code, envelope = _run_capture(working, monkeypatch, capsys)
        assert code == ExitCode.BENIGN_NEGATIVE, (
            f"failer {name!r} should exit 1, got {code}"
        )
        assert code != ExitCode.ACTIONABLE_FINDING
        assert envelope["ok"] is False


def test_absent_compile_exits_one_not_zero(
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An otherwise-complete tree with no ``compiled.md`` exits ``1`` (B1)."""
    _spec, working = done_predicate_failer_tree("compile_consistent")
    assert not (working / "manuscript" / "compiled.md").exists()
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False


def test_sole_stale_present_compile_exits_four(
    sole_stale_compile_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A sole stale-*present* ``compiled.md`` exits ``4`` (the carve-out)."""
    working = sole_stale_compile_tree()
    assert (working / "manuscript" / "compiled.md").exists()
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False
    assert sum(1 for value in result.values() if value is False) == 1


def test_obvious_stale_present_compile_exits_four(
    obvious_stale_compile_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An obvious byte-and-count-divergent stale compile exits ``4`` (carve-out).

    Pins ``DONE_PREDICATE_OBVIOUS_STALE_COMPILE`` (roadmap 3.1.2.1): the
    plainly-wrong stale ``compiled.md`` control is now load-bearing, asserting the
    sole ``compile_consistent`` divergence fires the exit-``4`` carve-out exactly
    as its subtle count-coincident sibling does.
    """
    working = obvious_stale_compile_tree()
    assert (working / "manuscript" / "compiled.md").exists()
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False
    assert sum(1 for value in result.values() if value is False) == 1


def test_mid_draft_stale_compile_exits_one(
    mid_draft_stale_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale compile *alongside* a drafting clause stays exit ``1``."""
    code, envelope = _run_capture(mid_draft_stale_tree(), monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False
    assert result["phase_is_done"] is False


def test_stale_compile_with_each_other_clause_exits_one(
    sole_stale_compile_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale compile paired with *each* other unmet clause exits ``1``.

    Drives the carve-out's exclusivity: a present-but-stale ``compiled.md`` plus
    any second unmet clause must not fire the exit-``4`` carve-out, so the
    failure set has more than the single ``compile_consistent`` member.
    """
    working = sole_stale_compile_tree()
    manuscript = working / "manuscript"
    # Removing the first chapter's done.flag adds all_chapters_flagged to the
    # failure set beside the stale compile_consistent, so the carve-out must not
    # fire (the failure set is no longer the sole compile_consistent tuple).
    (_first_chapter_dir(working) / "done.flag").unlink()
    assert (manuscript / "compiled.md").exists()
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False
    assert result["all_chapters_flagged"] is False


def test_absent_sole_compile_exits_one_with_missing_message(
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An absent sole-failure ``compiled.md`` exits ``1`` and reports it missing.

    The absent-vs-stale split: the carve-out gates on ``compiled.md`` *existing*,
    so a sole ``compile_consistent`` failure caused by an *absent* compile stays
    exit ``1`` (D-CARVE), and the human message names it *missing* not stale (A-4).
    """
    _spec, working = done_predicate_failer_tree("compile_consistent")
    assert not (working / "manuscript" / "compiled.md").exists()
    code, envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.BENIGN_NEGATIVE
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compile_consistent"] is False
    assert sum(1 for value in result.values() if value is False) == 1
    messages = typ.cast("list[str]", envelope["messages"])
    assert any("missing" in line for line in messages)


def test_undecodable_compiled_exits_three(
    all_hold_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An undecodable ``compiled.md`` exits ``3``, not the benign ``1`` (R-FAULT)."""
    working = all_hold_tree()
    (working / "manuscript" / "compiled.md").write_bytes(b"\xff\xfe bad")
    code, _envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.STATE_ERROR


def test_missing_state_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An absent ``working/state.toml`` exits ``3`` (the state-error channel)."""
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    assert int(typ.cast("int", excinfo.value.code)) == ExitCode.STATE_ERROR


def test_undecodable_critic_notes_exits_three(
    all_hold_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An undecodable ``critic-notes.md`` exits ``3``, not the benign ``1``."""
    working = all_hold_tree()
    (_first_chapter_dir(working) / "critic-notes.md").write_bytes(b"\xff\xfe bad")
    code, _envelope = _run_capture(working, monkeypatch, capsys)
    assert code == ExitCode.STATE_ERROR


def test_stray_positional_exits_two(
    all_hold_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stray positional token is a usage error (exit ``2``)."""
    code, _envelope = _run_capture(
        all_hold_tree(), monkeypatch, capsys, argv=["unexpected"]
    )
    assert code == ExitCode.USAGE_ERROR
