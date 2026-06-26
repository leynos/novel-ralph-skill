"""End-to-end reachability of ``novel-compile`` (roadmap tasks 4.1.1, 4.1.2).

This proves the externally observable command-line behaviour of the now-real
command: driven through ``novel.main()`` (the installed console-script
body) against a prepared drafting tree, ``novel-compile`` resolves, exits ``0``,
emits an envelope naming the written ``compiled.md``, and writes the file with
the ordered draft concatenation. An empty-manifest tree refuses with exit ``3``.

The ``--check`` entry-point cases pin the read-only divergence checker through
the same real console-script body: a current compile exits ``0`` with
``diverged: false``, while a present-but-stale compile and an absent compile each
exit ``4`` with ``diverged: true`` (the absent case pins the polarity decision
that ``ABSENT`` is a finding, not vacuously satisfied), leaving any present
``compiled.md`` byte-for-byte unchanged and never writing an absent one. These
are the only layer that exercises ``parse_global_flags`` + ``_drive`` (where
``--human`` is stripped and the residual argv, including ``--check``, is
forwarded to ``run``), so they regression-pin that the kw-only ``--check`` flag
survives the pre-parse (ExecPlan R-ENTRYPOINT, D-ENTRYPOINT). The in-process
``run(build_app(), ["--check"], …)`` tests bypass that layer entirely.

The slower wheel-build install e2e for the spine lives in
``tests/test_console_scripts_e2e.py``; this fast entry-point check is the
cheapest proof that ``novel-compile`` is wired into the real console-script path
(mirroring ``tests/test_recount_e2e.py``).
"""

from __future__ import annotations

import json
import sys
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import novel
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel compile"


def _drafting_tree(tmp_path: Path) -> tuple[Path, str]:
    """Build a coherent three-chapter ``drafting`` tree; return it and its compile.

    Returns
    -------
    tuple[pathlib.Path, str]
        The materialised ``working/`` path and the expected ``compiled.md`` bytes.
    """
    counts = (3, 5, 4)
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(counts, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
    )
    working = wc.build_working_tree(spec, tmp_path)
    expected = wc.concatenate_drafts([wc.draft_body(count) for count in counts])
    return working, expected


def test_entry_point_compile_reachable_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-compile`` is reachable through the entry point and writes the file."""
    working, expected = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split()])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = json.loads(capsys.readouterr().out)
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["compiled"] == "working/manuscript/compiled.md"
    compiled = working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == expected


def _check_tree(compiled: str | None, tmp_path: Path) -> Path:
    """Build a coherent three-chapter tree carrying ``compiled`` on disk.

    ``compiled`` is :data:`working_corpus.COMPILED_AUTO` for the coherent
    compile or an arbitrary string for a present-but-stale one; the materialised
    ``compiled.md`` is what the entry-point ``--check`` cases inspect.
    """
    counts = (3, 5, 4)
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(counts, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        compiled=compiled,
    )
    return wc.build_working_tree(spec, tmp_path)


def test_entry_point_compile_check_current_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--check`` over a current compile exits ``0`` through the entry point.

    Drives the real console-script body ``novel.main()`` with ``sys.argv
    = [_COMMAND, "--check"]``, so the kw-only ``--check`` flag must survive the
    ``parse_global_flags`` + ``_drive`` pre-parse and reach the body (R-ENTRYPOINT).
    """
    working = _check_tree(wc.COMPILED_AUTO, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "--check"])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.SUCCESS
    result = typ.cast(
        "dict[str, object]", json.loads(capsys.readouterr().out)["result"]
    )
    assert result["diverged"] is False
    assert result["checked"] == "working/manuscript/compiled.md"
    assert compiled.read_bytes() == before, (
        "--check must not write through the entry point"
    )


def test_entry_point_compile_check_stale_exits_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--check`` over a present-but-stale compile exits ``4`` through the entry point.

    The finding branch of the entry-point pin: a stale ``compiled.md`` exits ``4``
    with ``diverged: true`` and is left byte-for-byte unchanged.
    """
    working = _check_tree("STALE — not the ordered concatenation", tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "--check"])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["diverged"] is True
    assert compiled.read_bytes() == before, (
        "--check must not write through the entry point"
    )


def test_entry_point_compile_check_absent_exits_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--check`` over an absent compile exits ``4`` through the entry point.

    Pins the polarity decision (``ABSENT`` treated as a finding, not vacuously
    satisfied) through the real console-script body: a tree carrying no
    ``compiled.md`` exits ``4`` with ``diverged: true`` and no ``compiled.md`` is
    written (``--check`` never regenerates).
    """
    working = _check_tree(None, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    assert not compiled.exists()
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "--check"])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["diverged"] is True
    assert not compiled.exists(), "--check must not write through the entry point"


def test_entry_point_compile_empty_manifest_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty-manifest tree refuses with exit ``3`` and writes no ``compiled.md``."""
    working = wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split()])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert json.loads(capsys.readouterr().out)["ok"] is False
    assert not (working / "manuscript" / "compiled.md").exists()
