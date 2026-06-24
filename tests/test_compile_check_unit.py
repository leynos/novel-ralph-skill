"""Unit tests for the ``novel-compile --check`` read-only divergence checker.

These pin the roadmap 4.1.2 checker (:func:`check_compiled`; design §4.3): with
``--check``, ``novel-compile`` reports whether ``compiled.md`` is the ordered
draft concatenation, **writes nothing on any path** (ADR-001; ExecPlan
R-NOWRITE), and projects the shared verdict to the ``compile_consistent``
polarity — only ``MATCHES`` is satisfied (exit ``0``), both ``DIVERGES`` and
``ABSENT`` are actionable findings (exit ``4``; ExecPlan D-POLARITY). The state
and input fault boundary (a missing/unparseable ``state.toml``, an empty
``[chapters]`` manifest, an undecodable ``draft.md``/``compiled.md``) routes to
exit ``3``, and a stray positional routes to exit ``2`` (D-FLAG).

**Driver requirement (ExecPlan D-CHECK-ARGV).** Every case drives
``run(build_app(), ["--check"], …)`` — passing ``["--check"]``, *not* ``[]`` —
through a dedicated :func:`_run_check` driver, never the ``[]``-argv write-path
helpers. A ``[]`` argv would exercise the write path and pass the no-write and
verdict assertions for the wrong reason (a false green). Each test
``monkeypatch.chdir``s into the prepared tree's parent first, because
``novel-compile`` resolves a cwd-relative ``working/`` (ExecPlan D-CWD).
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._compile import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-compile"
_COUNTS: tuple[int, ...] = (3, 5, 4)
# Deliberately stale bytes: present but not the ordered concatenation, so the
# verdict is DIVERGES.
_STALE_COMPILED = "STALE — not the ordered concatenation"


def _run_check(working: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    """Drive ``novel-compile --check`` through ``run``; return ``(code, stdout)``.

    Passes ``["--check"]`` (not ``[]``) so the checker, not the write path, is
    exercised (ExecPlan D-CHECK-ARGV).

    Returns
    -------
    tuple[int, str]
        The process exit code and the raw machine-mode envelope on stdout.
    """
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _compile_spec(compiled: str | None) -> wc.WorkingTreeSpec:
    """Return a three-chapter ``drafting`` spec carrying ``compiled`` on disk.

    ``compiled`` is :data:`working_corpus.COMPILED_AUTO` for the coherent
    compile, an arbitrary string for a stale one, or ``None`` for an absent one.
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
        for number, count in enumerate(_COUNTS, start=1)
    )
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        compiled=compiled,
    )


def _build(compiled: str | None, tmp_path: Path) -> Path:
    """Materialise a three-chapter tree with the given ``compiled.md`` state."""
    return wc.build_working_tree(_compile_spec(compiled), tmp_path)


def test_check_matches_exits_zero_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coherent compile reports ``diverged: false``, exits ``0``, writes nothing."""
    working = _build(wc.COMPILED_AUTO, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()

    code, raw = _run_check(working, monkeypatch)

    assert code == ExitCode.SUCCESS, "a coherent compile must satisfy --check"
    envelope = json.loads(raw)
    assert envelope["ok"] is True
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {
        "checked": "working/manuscript/compiled.md",
        "chapters": len(_COUNTS),
        "diverged": False,
    }
    assert compiled.read_bytes() == before, "--check must not mutate compiled.md"


def test_check_diverges_exits_four_and_leaves_stale_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A present-but-stale compile reports ``diverged: true`` and exits ``4``."""
    working = _build(_STALE_COMPILED, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()

    code, raw = _run_check(working, monkeypatch)

    assert code == ExitCode.ACTIONABLE_FINDING, "a stale compile is an exit-4 finding"
    envelope = json.loads(raw)
    assert envelope["ok"] is False
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result["diverged"] is True
    assert result["checked"] == "working/manuscript/compiled.md"
    assert compiled.read_bytes() == before, (
        "--check must leave the present stale compiled.md byte-for-byte unchanged"
    )


def test_check_absent_exits_four_and_creates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent compile reports ``diverged: true``, exits ``4``, creates nothing."""
    working = _build(None, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    assert not compiled.exists(), "premise: the tree starts with no compiled.md"

    code, raw = _run_check(working, monkeypatch)

    assert code == ExitCode.ACTIONABLE_FINDING, "an absent compile is an exit-4 finding"
    result = typ.cast("dict[str, object]", json.loads(raw)["result"])
    assert result["diverged"] is True
    assert not compiled.exists(), "--check must not create compiled.md"


def test_check_empty_manifest_exits_three_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty ``[chapters]`` manifest refuses with exit ``3``, writes nothing."""
    working = wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path)

    code, raw = _run_check(working, monkeypatch)

    assert code == ExitCode.STATE_ERROR, "an empty manifest is the exit-3 channel"
    assert json.loads(raw)["ok"] is False
    assert not (working / "manuscript" / "compiled.md").exists(), (
        "an empty-manifest refusal must write no compiled.md"
    )


def test_check_missing_state_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing ``state.toml`` refuses with exit ``3`` (the state channel)."""
    (tmp_path / "working" / "manuscript").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )

    assert excinfo.value.code == ExitCode.STATE_ERROR


def test_check_undecodable_draft_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An undecodable ``draft.md`` routes to exit ``3`` (the fault boundary)."""
    working = _build(wc.COMPILED_AUTO, tmp_path)
    # Corrupt chapter 1's draft to invalid UTF-8 so the verdict read raises.
    (working / "manuscript" / "chapter-01" / "draft.md").write_bytes(b"\xff\xfe")

    code, _ = _run_check(working, monkeypatch)

    assert code == ExitCode.STATE_ERROR, "an undecodable draft is the exit-3 channel"


def test_check_stray_positional_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stray positional routes to exit ``2`` (the kw-only flag did not loosen).

    Pins D-FLAG: ``--check`` is kw-only, so an unknown positional still raises a
    ``CycloptsError`` the shared runner routes to exit ``2``.
    """
    working = _build(wc.COMPILED_AUTO, tmp_path)
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check", "bogus"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )

    assert excinfo.value.code == ExitCode.USAGE_ERROR
