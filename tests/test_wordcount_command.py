"""In-process exit-code contract tests for the wired ``wordcount`` command.

These drive the real ``wordcount`` Cyclopts app through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper (the ``_run_capture``
pattern from ``tests/test_desloppify_command.py``) and pin the exit-code contract
at its boundaries (design §9 "CLI error-path tests"; roadmap task 6.1.1): a
coherent tree exits ``0`` with ``command: "novel wordcount"``; an absent
``working/``,
an unparseable ``state.toml``, and an undecodable ``draft.md`` each exit ``3``;
an unknown ``--option`` exits ``2`` (the Cyclopts usage channel; ``wordcount``
takes no ``--chapter`` per ExecPlan Decision Log D-SCOPE); and ``--help`` exits
``0`` with no envelope. ``wordcount`` is a read-only report, so a coherent tree
never exits ``4`` (Decision Log D-EXIT).
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands._wordcount import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec

_COMMAND = "novel wordcount"


def _run_capture(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object]]:
    """Drive ``wordcount`` over ``argv`` and return ``(exit_code, envelope)``."""
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    raw = capsys.readouterr().out
    return int(typ.cast("int", excinfo.value.code)), json.loads(raw)


@pytest.fixture
def coherent_working(
    make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
    make_chapter_spec: cabc.Callable[..., object],
    build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
    tmp_path: Path,
) -> Path:
    """Materialise a small coherent drafting-era tree and return its ``working/``.

    Bundling the three corpus-builder fixtures here keeps each test's parameter
    list within the project's argument-count gate (Pylint ``too-many-arguments``)
    while still delivering a materialised tree by fixture name.
    """
    chapters = tuple(
        make_chapter_spec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=10000,
            draft_words=words,
            has_done_flag=False,
        )
        for number, words in ((1, 3000), (2, 2000))
    )
    spec = make_working_tree_spec(
        phase_current="drafting",
        phase_completed=(),
        chapters=chapters,
        target_words=20000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=2,
    )
    return build_tree(spec, tmp_path)


def test_coherent_tree_exits_zero(
    coherent_working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A coherent ``working/`` exits ``0`` with ``command: "novel wordcount"``."""
    monkeypatch.chdir(coherent_working.parent)
    code, envelope = _run_capture([], capsys)
    assert code == ExitCode.SUCCESS, f"expected exit 0, got {code}"
    assert envelope["command"] == "novel wordcount", envelope
    assert envelope["ok"] is True, envelope


def test_absent_working_dir_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A cwd with no ``./working/`` exits ``3`` (state error)."""
    monkeypatch.chdir(tmp_path)
    code, envelope = _run_capture([], capsys)
    assert code == ExitCode.STATE_ERROR, f"expected exit 3, got {code}"
    assert envelope["ok"] is False, envelope


def test_missing_state_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A present ``working/`` with no ``state.toml`` exits ``3`` (state error).

    The absent-``working/`` and unparseable-``state.toml`` cases bracket this
    shape, but the precise present-``working/``-without-``state.toml`` fault is
    pinned directly for ``recount``
    (``tests/test_recount_unit.py``'s ``test_recount_missing_state_refuses``) and
    not for ``wordcount``. Pinning it here makes the installed proof's truth
    self-contained per command rather than resting on the shared boundary
    argument (ExecPlan addendum 6.2.6.1).
    """
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path)
    code, envelope = _run_capture([], capsys)
    assert code == ExitCode.STATE_ERROR, f"expected exit 3, got {code}"
    assert envelope["ok"] is False, envelope


def test_unparseable_state_exits_three(
    coherent_working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unparseable ``state.toml`` exits ``3`` (state error)."""
    (coherent_working / "state.toml").write_text(
        "this is not = valid = toml", encoding="utf-8"
    )
    monkeypatch.chdir(coherent_working.parent)
    code, envelope = _run_capture([], capsys)
    assert code == ExitCode.STATE_ERROR, f"expected exit 3, got {code}"
    assert envelope["ok"] is False, envelope


def test_undecodable_draft_exits_three(
    coherent_working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An undecodable ``draft.md`` exits ``3`` rather than escaping to exit ``1``."""
    draft = coherent_working / "manuscript" / "chapter-01" / "draft.md"
    # An invalid UTF-8 byte sequence makes ``recount_words`` raise
    # ``UnicodeDecodeError``, which the command must route to the exit-3 channel.
    draft.write_bytes(b"\xff\xfe not valid utf-8 \x80")
    monkeypatch.chdir(coherent_working.parent)
    code, envelope = _run_capture([], capsys)
    assert code == ExitCode.STATE_ERROR, f"expected exit 3, got {code}"
    assert envelope["ok"] is False, envelope


def test_unknown_option_exits_two(
    coherent_working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unknown ``--option`` exits ``2`` (the Cyclopts usage channel)."""
    monkeypatch.chdir(coherent_working.parent)
    code, envelope = _run_capture(["--no-such-flag"], capsys)
    assert code == ExitCode.USAGE_ERROR, f"expected exit 2, got {code}"
    assert envelope["ok"] is False, envelope


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_meta_flags_exit_zero_without_envelope(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``wordcount --help``/``--version`` exit ``0`` with no envelope."""
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [flag],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    assert excinfo.value.code == ExitCode.SUCCESS, excinfo.value.code
    # The meta-flag path is exempt from the envelope contract: stdout carries
    # Cyclopts help/version prose, not a JSON envelope, so it must not parse as
    # JSON. Asserting on the parse (not a bare ``"command" not in out`` substring)
    # avoids a spurious failure if future help text legitimately contains the
    # word "command".
    out = capsys.readouterr().out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
