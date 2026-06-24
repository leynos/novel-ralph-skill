"""In-process tests for the wired ``desloppify`` command (roadmap task 5.1.2).

These drive the real ``desloppify`` Cyclopts app through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
``tests/test_novel_state_check.py`` (``monkeypatch.chdir`` into a materialised
``working/`` parent, ``capsys`` to read the emitted envelope). They pin the three
observable exit-code outcomes from the ExecPlan purpose (design §4.4, §3.2): a
clean tree exits ``0`` with ``ok: true`` and empty ``violations``; an em-dash
flood exits ``4`` naming ``em-dash`` in ``result.violations``; and the exit-2
(bad ``--chapter`` / malformed pack) and exit-3 (absent pack file / absent
``working/``) fault routes are each distinguishable by exit code alone. The
``--help`` carve-out exits ``0`` with no envelope.
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "desloppify"
_BAD_PATTERN_PACK = "tests/data/rulepacks/bad-pattern.toml"


def _run(argv: list[str], *, human: bool = False) -> None:
    """Drive the ``desloppify`` app over ``argv`` through :func:`run`."""
    run(
        build_app(),
        argv,
        RunContext(command=_COMMAND, working_dir="working", human=human),
    )


def _envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """Return the JSON envelope ``run`` emitted to stdout."""
    return json.loads(capsys.readouterr().out)


def _result(envelope: dict[str, object]) -> dict[str, object]:
    """Return the ``result`` sub-mapping of ``envelope``."""
    return typ.cast("dict[str, object]", envelope["result"])


def _first_chapter_dir(working: Path) -> Path:
    """Return the lowest-numbered ``chapter-NN`` directory under ``working``."""
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "baseline tree must contain at least one chapter directory"
    return chapters[0]


def test_clean_tree_exits_zero(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A clean ``working/`` (no offenders) exits ``0`` with empty violations."""
    working = baseline_tree()
    # Overwrite every draft with offender-free prose so the §6 pack is clean.
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text("A calm sentence with plain words.\n", encoding="utf-8")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run([])
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = _envelope(capsys)
    assert envelope["ok"] is True
    assert _result(envelope)["violations"] == []


def test_em_dash_flood_exits_four(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An em-dash flood (>5 per 300 words) exits ``4`` naming ``em-dash``."""
    working = baseline_tree()
    # Six em dashes in well under 300 words is a density past the threshold of 5.
    flood = "word—word—word—word—word—word—word " + "filler " * 20
    _first_chapter_dir(working).joinpath("draft.md").write_text(flood, encoding="utf-8")
    # Clear any other drafts so only the flood drives the verdict.
    for chapter_dir in sorted((working / "manuscript").glob("chapter-*"))[1:]:
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text("plain calm words here\n", encoding="utf-8")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run([])
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    violations = typ.cast("list[str]", _result(envelope)["violations"])
    assert "em-dash" in violations, f"em-dash not in violations {violations}"


def test_malformed_pack_exits_two(
    baseline_tree: cabc.Callable[[], Path],
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--pack`` with malformed *content* exits ``2`` (usage error)."""
    working = baseline_tree()
    pack = (project_root / _BAD_PATTERN_PACK).resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", str(pack)])
    assert excinfo.value.code == ExitCode.USAGE_ERROR
    assert _envelope(capsys)["ok"] is False


def test_absent_pack_file_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--pack`` pointing at an absent file exits ``3`` (state error)."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", "/no/such/pack.toml"])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert _envelope(capsys)["ok"] is False


def test_chapter_outside_manifest_exits_two(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--chapter`` outside the manifest exits ``2`` (usage error)."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--chapter", "9999"])
    assert excinfo.value.code == ExitCode.USAGE_ERROR
    assert _envelope(capsys)["ok"] is False


def test_absent_working_dir_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A cwd with no ``./working/`` exits ``3`` (state error)."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        _run([])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert _envelope(capsys)["ok"] is False


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_meta_flags_exit_zero_without_envelope(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``desloppify --help``/``--version`` exit ``0`` with no envelope."""
    with pytest.raises(SystemExit) as excinfo:
        _run([flag])
    assert excinfo.value.code == ExitCode.SUCCESS
    assert "command" not in capsys.readouterr().out
