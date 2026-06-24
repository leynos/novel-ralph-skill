"""In-process tests for the wired ``novel-done`` command (roadmap task 3.1.1).

These drive the real ``novel-done`` Cyclopts app through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
``tests/test_desloppify_command.py`` (``monkeypatch.chdir`` into a materialised
``working/`` parent, ``capsys`` to read the emitted envelope). They pin every
observable exit-code outcome from the ExecPlan purpose (design §4.2, §3.2): the
all-six-clauses-hold tree exits ``0`` with ``ok: true``; each single-clause-fail
tree exits ``1`` with ``ok: false`` (including the absent-``compiled.md`` tree,
proving the existence half drives a benign ``1`` rather than a false ``0``); a
missing/unparseable ``state.toml`` and an undecodable ``critic-notes.md`` each
exit ``3`` (the D-FAULT negative test); and a stray positional token exits ``2``
(the runner's ``CycloptsError`` arm). No 3.1.1 path exits ``4``.
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

_COMMAND = "novel-done"
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
