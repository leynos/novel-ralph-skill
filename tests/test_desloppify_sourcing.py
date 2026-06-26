"""Unit tests for ``desloppify`` chapter text sourcing (roadmap task 5.1.2).

These pin :func:`novel_ralph_skill.commands._desloppify.source_chapters`, the
helper that turns the ``working/`` tree into the
:class:`~novel_ralph_skill.rulepack.detect.ScannedChapter` sequence the detection
core consumes (design §4.4, §5.1). The suite proves the manifest-driven scope
(whole manuscript vs ``--chapter N``), the absent-draft-is-empty-text benign
case, and the exit-2 vs exit-3 fault split: a ``--chapter`` outside the manifest
raises the exit-2-bound :class:`DesloppifyUsageError`, while an undecodable draft
or a missing ``state.toml`` raises the exit-3-bound
:class:`~novel_ralph_skill.contract.runner.StateInputError`.

The tests build a coherent ``working/`` from the corpus ``baseline_tree`` fixture
and ``monkeypatch.chdir`` into its parent so the fixed ``./working/`` resolves
there, mirroring ``tests/test_novel_state_check.py``.
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify import (
    DesloppifyUsageError,
    source_chapters,
)
from novel_ralph_skill.contract.runner import StateInputError

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path


def _draft_path(working: Path, number: int) -> Path:
    """Return the ``draft.md`` path for ``number`` under ``working``."""
    return working / "manuscript" / f"chapter-{number:02d}" / "draft.md"


def _first_chapter_number(working: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """Return the lowest manifest chapter number for ``working``."""
    with monkeypatch.context() as patched:
        patched.chdir(working.parent)
        return source_chapters(None)[0].number


def test_whole_manuscript_sources_all_chapters_in_order(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``--chapter`` sources every manifest chapter in ascending order."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    chapters = source_chapters(None)
    numbers = [chapter.number for chapter in chapters]
    assert numbers == sorted(numbers), f"chapters not ascending: {numbers}"
    assert numbers, "baseline manifest must contain at least one chapter"
    # Each non-empty draft's text is the file's text, proving the right file.
    for chapter in chapters:
        path = _draft_path(working, chapter.number)
        if path.exists():
            assert chapter.text == path.read_text(encoding="utf-8"), (
                f"chapter {chapter.number} text does not match its draft"
            )


def test_single_chapter_scope_sources_only_that_chapter(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--chapter N`` sources only chapter ``N``."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    first = source_chapters(None)[0].number
    chapters = source_chapters(first)
    assert [chapter.number for chapter in chapters] == [first], (
        "single-chapter scope must source exactly the named chapter"
    )


def test_absent_draft_yields_empty_text(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An absent ``draft.md`` contributes empty text, not a fault."""
    working = baseline_tree()
    first = _first_chapter_number(working, monkeypatch)
    _draft_path(working, first).unlink()
    monkeypatch.chdir(working.parent)
    chapters = source_chapters(first)
    assert not chapters[0].text, (
        f"absent draft must source empty text, got {chapters[0].text!r}"
    )


def test_chapter_outside_manifest_raises_usage_error(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``--chapter`` absent from the manifest raises the exit-2 usage fault."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(DesloppifyUsageError, match=r"no chapter 9999 in the manifest"):
        source_chapters(9999)


def test_undecodable_draft_raises_state_input_error(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An undecodable ``draft.md`` raises the exit-3-bound state error."""
    working = baseline_tree()
    first = _first_chapter_number(working, monkeypatch)
    # Invalid UTF-8 bytes make ``read_text(encoding="utf-8")`` raise
    # ``UnicodeDecodeError`` (a ``ValueError`` subclass in STATE_INPUT_ERRORS).
    _draft_path(working, first).write_bytes(b"\xff\xfe valid words here")
    monkeypatch.chdir(working.parent)
    with pytest.raises(StateInputError, match=r"cannot read chapter drafts"):
        source_chapters(first)


def test_missing_state_raises_state_input_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cwd with no ``./working/state.toml`` raises the exit-3-bound state error."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(StateInputError, match=r"no novel working/ found in"):
        source_chapters(None)
