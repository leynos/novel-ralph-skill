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
from novel_ralph_skill.commands._desloppify_report import ai_isms_pack_path
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "novel desloppify"
_BAD_PATTERN_PACK = "tests/data/rulepacks/bad-pattern.toml"
_EXAMPLE_LEDGER = "tests/data/ledgers/example-device-ledger.toml"
_TWO_WINDOWS_LEDGER = "tests/data/ledgers/two-windows.toml"


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
    """A ``--pack`` pointing at an absent file exits ``3`` with actionable prose.

    The envelope names the offending pack path and offers a file-shaped remedy
    (check ``--pack`` or fall back to the shipped pack), and never leaks the raw
    OS text (an ``Errno`` or the stringified exception repr) — the §6.3.8
    invariant.
    """
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    pack = "/no/such/pack.toml"
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", pack])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    joined = "\n".join(typ.cast("list[str]", envelope["messages"]))
    assert pack in joined
    assert "--pack" in joined
    assert "Errno" not in joined
    assert "FileNotFoundError" not in joined


def test_undecodable_pack_file_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--pack`` whose TOML is undecodable exits ``3`` with actionable prose.

    A syntactically broken pack file faults during ``tomllib.load``, raising
    ``RulePackFileError`` (the exit-3 file channel, distinct from the exit-2
    malformed-content channel). The envelope names the pack path and offers the
    file-shaped remedy, with no raw ``TOMLDecodeError`` repr leaked.
    """
    working = baseline_tree()
    pack = (project_root / "tests/data/rulepacks/undecodable.toml").resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", str(pack)])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    joined = "\n".join(typ.cast("list[str]", envelope["messages"]))
    assert str(pack) in joined
    assert "--pack" in joined
    assert "Errno" not in joined
    assert "TOMLDecodeError" not in joined


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


def test_ai_isms_pack_flags_load_bearing(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--pack ai-isms.toml`` over a load-bearing draft exits ``4`` naming it.

    Proves the shipped ai-isms pack is usable through the documented ``--pack``
    flag (roadmap 7.1.1): an AI-ism in the manuscript drives an actionable
    finding, exactly as an offender does for the default pack.
    """
    working = baseline_tree()
    draft = "This paragraph is load-bearing in the argument.\n"
    _first_chapter_dir(working).joinpath("draft.md").write_text(draft, encoding="utf-8")
    for chapter_dir in sorted((working / "manuscript").glob("chapter-*"))[1:]:
        other = chapter_dir / "draft.md"
        if other.exists():
            other.write_text("plain calm words here\n", encoding="utf-8")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", str(ai_isms_pack_path())])
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    violations = typ.cast("list[str]", _result(envelope)["violations"])
    assert "load-bearing" in violations, f"load-bearing not in violations {violations}"


def test_ai_isms_pack_clean_tree_exits_zero(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--pack ai-isms.toml`` over AI-ism-free prose exits ``0`` with no findings."""
    working = baseline_tree()
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text("A calm sentence with plain words.\n", encoding="utf-8")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--pack", str(ai_isms_pack_path())])
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = _envelope(capsys)
    assert envelope["ok"] is True
    assert _result(envelope)["violations"] == []


def test_ledger_with_chapter_exits_two(
    baseline_tree: cabc.Callable[[], Path],
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--ledger`` combined with ``--chapter`` exits ``2`` (usage error).

    The device ledger rations across the whole manuscript, so a single-chapter
    scan cannot compute the ration faithfully; the combination is a body-detected
    usage fault (ExecPlan Decision Log "mutually exclusive with ``--chapter``").
    """
    working = baseline_tree()
    ledger = (project_root / _EXAMPLE_LEDGER).resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", str(ledger), "--chapter", "1"])
    assert excinfo.value.code == ExitCode.USAGE_ERROR
    assert _envelope(capsys)["ok"] is False


def test_absent_ledger_file_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--ledger`` pointing at an absent file exits ``3`` with actionable prose.

    The envelope names the offending ledger path and offers a file-shaped remedy
    (check ``--ledger``), and never leaks the raw OS text (an ``Errno`` or the
    stringified exception repr) — the §6.3.8 invariant.
    """
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    ledger = "/no/such/ledger.toml"
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", ledger])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    joined = "\n".join(typ.cast("list[str]", envelope["messages"]))
    assert ledger in joined
    assert "--ledger" in joined
    assert "Errno" not in joined
    assert "FileNotFoundError" not in joined


def test_undecodable_ledger_file_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--ledger`` whose TOML is undecodable exits ``3`` with actionable prose.

    A syntactically broken ledger file faults during ``tomllib.load``, raising
    ``LedgerFileError`` (the exit-3 file channel, distinct from the exit-2
    malformed-content channel). The envelope names the ledger path and offers the
    file-shaped remedy, with no raw ``TOMLDecodeError`` repr leaked.
    """
    working = baseline_tree()
    ledger = (project_root / "tests/data/ledgers/undecodable.toml").resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", str(ledger)])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    joined = "\n".join(typ.cast("list[str]", envelope["messages"]))
    assert str(ledger) in joined
    assert "--ledger" in joined
    assert "Errno" not in joined
    assert "TOMLDecodeError" not in joined


def test_malformed_ledger_exits_two(
    baseline_tree: cabc.Callable[[], Path],
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ``--ledger`` with malformed *content* exits ``2`` (usage error)."""
    working = baseline_tree()
    ledger = (project_root / _TWO_WINDOWS_LEDGER).resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", str(ledger)])
    assert excinfo.value.code == ExitCode.USAGE_ERROR
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
