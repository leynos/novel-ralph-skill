"""Unit tests for the shared ``compiled_matches_drafts`` helper.

These pin :func:`novel_ralph_skill.state.compiled_matches_drafts` (roadmap task
3.1.3), the single production site that decides whether
``working/manuscript/compiled.md`` is the ordered concatenation of the present
drafts. The §5.4 detector and the ``compile_consistent`` done-clause both consume
it, each projecting the three-valued :class:`CompiledComparison` to its own
absent-file polarity, so the helper's three outcomes — ``ABSENT``, ``MATCHES``,
``DIVERGES`` — and its fault boundary are pinned here once.

Each tree is the coherent ``drafting`` corpus tree (no ``compiled.md``); the
tests write or remove ``compiled.md`` directly to drive each outcome. The
empty-manifest case replaces the parsed manifest with an empty one via
:func:`dataclasses.replace`, exercising the vacuous ``concatenate_drafts([]) ==
""`` path both callers rely on.
"""

from __future__ import annotations

import dataclasses
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.state import (
    CompiledComparison,
    compiled_matches_drafts,
    concatenate_drafts,
    load_state,
    present_draft_bodies,
)

if typ.TYPE_CHECKING:
    from pathlib import Path


def _drafting_tree(tmp_path: Path, counts: tuple[int, ...] = (3, 5, 4)) -> Path:
    """Build a coherent ``drafting`` tree (no ``compiled.md``) and return it.

    Each chapter's ``draft.md`` carries ``counts[i]`` deterministic words, so the
    expected concatenation is exact and the tree carries no ``compiled.md`` (the
    drafting-era spec leaves it unwritten), modelling the stale/absent compile
    the helper must classify.
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
    return wc.build_working_tree(spec, tmp_path)


def test_matches_on_fresh_compile(tmp_path: Path) -> None:
    """A ``compiled.md`` equal to the ordered join returns ``MATCHES``."""
    working = _drafting_tree(tmp_path)
    state = load_state(working / "state.toml")
    compiled = working / "manuscript" / "compiled.md"
    compiled.write_text(
        concatenate_drafts(present_draft_bodies(state, working)), encoding="utf-8"
    )

    assert compiled_matches_drafts(state, working) is CompiledComparison.MATCHES, (
        "a fresh compile equal to the ordered join must report MATCHES"
    )


def test_diverges_on_stale_compile(tmp_path: Path) -> None:
    """A present-but-stale ``compiled.md`` returns ``DIVERGES``."""
    working = _drafting_tree(tmp_path)
    state = load_state(working / "state.toml")
    compiled = working / "manuscript" / "compiled.md"
    compiled.write_text("stale content diverging from drafts", encoding="utf-8")

    assert compiled_matches_drafts(state, working) is CompiledComparison.DIVERGES, (
        "bytes differing from the ordered join must report DIVERGES"
    )


def test_absent_ignores_drafts(tmp_path: Path) -> None:
    """An absent ``compiled.md`` returns ``ABSENT`` regardless of the drafts."""
    working = _drafting_tree(tmp_path)
    state = load_state(working / "state.toml")
    assert not (working / "manuscript" / "compiled.md").exists()

    assert compiled_matches_drafts(state, working) is CompiledComparison.ABSENT, (
        "an absent compiled.md must report ABSENT"
    )


def test_empty_manifest_vacuous(tmp_path: Path) -> None:
    """An empty manifest matches an empty present compile and is absent otherwise.

    ``concatenate_drafts([]) == ""``, so a present empty ``compiled.md`` is the
    vacuous match both callers rely on, while an absent one is still ``ABSENT``.
    """
    working = _drafting_tree(tmp_path)
    state = dataclasses.replace(load_state(working / "state.toml"), chapters=())
    compiled = working / "manuscript" / "compiled.md"

    compiled.write_text("", encoding="utf-8")
    assert compiled_matches_drafts(state, working) is CompiledComparison.MATCHES, (
        "an empty compiled.md must match the empty join of an empty manifest"
    )

    compiled.unlink()
    assert compiled_matches_drafts(state, working) is CompiledComparison.ABSENT, (
        "an absent compiled.md under an empty manifest must report ABSENT"
    )


def test_propagates_undecodable_draft(tmp_path: Path) -> None:
    """A non-UTF-8 ``draft.md`` beside a present compile propagates the fault."""
    working = _drafting_tree(tmp_path)
    state = load_state(working / "state.toml")
    (working / "manuscript" / "compiled.md").write_text("anything", encoding="utf-8")
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "draft.md").write_bytes(b"\xff\xfe not utf-8")

    with pytest.raises(UnicodeDecodeError, match="utf-8"):
        compiled_matches_drafts(state, working)


def test_checks_existence_before_reading(tmp_path: Path) -> None:
    """An undecodable draft beside an *absent* compile returns ``ABSENT``, no raise.

    Pins that the helper performs the existence check before it reads any draft,
    so a future refactor that reads the drafts unconditionally is caught
    (advisory A1). Paired with the present-compile case above, the two together
    lock the ordering: the helper raises only when ``compiled.md`` is present.
    """
    working = _drafting_tree(tmp_path)
    state = load_state(working / "state.toml")
    assert not (working / "manuscript" / "compiled.md").exists()
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "draft.md").write_bytes(b"\xff\xfe not utf-8")

    assert compiled_matches_drafts(state, working) is CompiledComparison.ABSENT, (
        "an absent compiled.md must short-circuit before any draft is read"
    )
