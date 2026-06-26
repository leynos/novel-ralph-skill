"""Registration of the ``set-chapters`` subcommand on the ``novel-state`` app.

Proves the subcommand is wired into
:func:`novel_ralph_skill.commands.novel_state.build_app` and that Cyclopts resolves
the ``list[ChapterPlanEntry]`` keyword from a JSON array (Surprise S1), driving it
in-process through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper so the externally observable
exit code and envelope are what the test asserts. The companion installed-binary
proof lives in ``tests/test_set_chapters_e2e.py``.
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel state"
_PLAN_JSON = (
    '[{"number": 1, "slug": "the-summons", "title": "The Summons", '
    '"target_words": 3200}, '
    '{"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800}]'
)


def _drive(
    working: Path, argv: list[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, dict[str, object]]:
    """Run ``argv`` from ``working.parent`` and return ``(exit_code, envelope)``."""
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), json.loads(stream.getvalue() or "{}")


@pytest.fixture
def empty_manifest_tree(tmp_path: Path) -> Path:
    """Build a coherent ``chapter-planning`` tree with an empty ``[chapters]``."""
    return wc.build_working_tree(wc.PHASE_STATES["chapter-planning"], tmp_path)


def test_set_chapters_subcommand_resolves_and_exits_zero(
    empty_manifest_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``novel-state set-chapters --chapters '[...]'`` resolves and exits 0."""
    code, envelope = _drive(
        empty_manifest_tree, ["set-chapters", "--chapters", _PLAN_JSON], monkeypatch
    )
    assert code == ExitCode.SUCCESS, "the registered subcommand must exit 0"
    assert envelope["ok"] is True, "a successful set-chapters envelope must be ok"
    result = typ.cast("dict[str, object]", envelope["result"])
    chapters = typ.cast("list[dict[str, object]]", result["chapters"])
    assert [chapter["number"] for chapter in chapters] == [1, 2], (
        "the written manifest must carry the two planned chapters in order"
    )


def test_set_chapters_malformed_json_exits_two(
    empty_manifest_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed ``--chapters`` argument faults at parse with exit 2 (usage)."""
    code, envelope = _drive(
        empty_manifest_tree, ["set-chapters", "--chapters", "[{not json"], monkeypatch
    )
    assert code == ExitCode.USAGE_ERROR, "a shape fault is a usage error (exit 2)"
    assert envelope["ok"] is False, "a malformed plan must yield an ok: false envelope"
