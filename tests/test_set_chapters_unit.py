"""Unit tests for the ``set-chapters`` mutator body (roadmap 2.2.3).

These pin the ``set-chapters`` body without the Cyclopts layer (mirroring
``tests/test_recount_unit.py`` and ``tests/test_state_mutators_unit.py``). The
headline write proves a populated empty-manifest tree gets ``[chapters]`` written
in ascending number order, the on-disk ``chapter-NN/`` directories created, a
``log.md`` receipt appended, and a ``[pending_turn]``-clean tree on success. Later
work items extend the module with the manifest-coherence validator, the prior- and
incoherent-plan refusals, and the D10 ordering guarantee.

The corpus spec/builder is taken by the sanctioned ``working_corpus as wc`` value
import; every ``set_chapters`` call is preceded by ``monkeypatch.chdir`` because the
body resolves a cwd-relative ``working/state.toml``.
"""

from __future__ import annotations

import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._set_chapters import (
    CHAPTERS_NON_EMPTY,
    NUMBERS_CONTIGUOUS_FROM_1,
    NUMBERS_UNIQUE,
    SLUGS_UNIQUE,
    TARGET_WORDS_POSITIVE,
    ChapterPlanEntry,
    manifest_coherence_violations,
    set_chapters,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import (
    SET_CHAPTERS_OPERATION,
    chapter_dir_name,
    check_disk_evidence,
    document_to_state,
    load_document,
    validate_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

# A planned two-chapter manifest, given out of order so the body must sort it.
_PLAN: tuple[ChapterPlanEntry, ...] = (
    ChapterPlanEntry(number=2, slug="the-road", title="The Road", target_words=2800),
    ChapterPlanEntry(
        number=1, slug="the-summons", title="The Summons", target_words=3200
    ),
)


def _empty_manifest_tree(tmp_path: Path) -> Path:
    """Build a coherent ``chapter-planning`` tree with an empty ``[chapters]``.

    The ``chapter-planning`` phase state carries no chapters, so it is the
    precondition tree ``set-chapters`` populates.
    """
    return wc.build_working_tree(wc.PHASE_STATES["chapter-planning"], tmp_path)


def test_set_chapters_writes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A populated empty-manifest tree gets ``[chapters]`` written and dirs created."""
    working = _empty_manifest_tree(tmp_path)
    monkeypatch.chdir(working.parent)

    outcome = set_chapters(chapters=list(_PLAN))

    assert outcome.code == ExitCode.SUCCESS
    assert dict(outcome.result) == {
        "chapters": [
            {
                "number": 1,
                "slug": "the-summons",
                "title": "The Summons",
                "target_words": 3200,
            },
            {
                "number": 2,
                "slug": "the-road",
                "title": "The Road",
                "target_words": 2800,
            },
        ]
    }, f"set-chapters must write the ascending manifest, got {dict(outcome.result)}"
    assert "violations" not in outcome.result, (
        "set-chapters success result must not echo the check read shape"
    )

    state = document_to_state(load_document(working / "state.toml"))
    assert [chapter.number for chapter in state.chapters] == [1, 2]
    assert [chapter.slug for chapter in state.chapters] == ["the-summons", "the-road"]
    assert state.pending_turn is None, "a clean run leaves no [pending_turn]"
    # D13: by_chapter is zero-seeded per chapter so the §5.4 coverage holds and a
    # follow-up check exits 0 (no pure-state and no disk-evidence violation).
    assert dict(state.word_counts.by_chapter) == {"01": 0, "02": 0}
    assert not validate_state(state), "the written state must pass the §5.2 checker"
    assert not check_disk_evidence(state, working), (
        "the written tree must be coherent against disk so check exits 0"
    )

    for number in (1, 2):
        directory = working / "manuscript" / chapter_dir_name(number)
        assert directory.is_dir(), f"{directory} must be created"
    assert "set-chapters" in (working / "log.md").read_text(encoding="utf-8"), (
        "set-chapters must append a recovery receipt to log.md"
    )


def _entry(number: int, slug: str, *, target_words: int = 100) -> ChapterPlanEntry:
    """Return a ``ChapterPlanEntry`` with a positive default ``target_words``."""
    return ChapterPlanEntry(
        number=number, slug=slug, title=f"Chapter {number}", target_words=target_words
    )


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param(
            (_entry(1, "a"), _entry(2, "b")),
            (),
            id="coherent",
        ),
        pytest.param((), (CHAPTERS_NON_EMPTY,), id="empty-plan"),
        pytest.param(
            (_entry(2, "a"), _entry(3, "b")),
            (NUMBERS_CONTIGUOUS_FROM_1,),
            id="gap-at-1",
        ),
        pytest.param(
            (_entry(1, "a"), _entry(3, "b")),
            (NUMBERS_CONTIGUOUS_FROM_1,),
            id="missing-middle-number",
        ),
        pytest.param(
            (_entry(1, "a"), _entry(1, "b")),
            (NUMBERS_UNIQUE, NUMBERS_CONTIGUOUS_FROM_1),
            id="duplicate-number",
        ),
        pytest.param(
            (_entry(1, "dup"), _entry(2, "dup")),
            (SLUGS_UNIQUE,),
            id="duplicate-slug",
        ),
        pytest.param(
            (_entry(1, "a", target_words=0), _entry(2, "b")),
            (TARGET_WORDS_POSITIVE,),
            id="zero-target",
        ),
        pytest.param(
            (_entry(1, "a", target_words=-5), _entry(2, "b")),
            (TARGET_WORDS_POSITIVE,),
            id="negative-target",
        ),
    ],
)
def test_manifest_coherence_violations(
    entries: tuple[ChapterPlanEntry, ...],
    expected: tuple[str, ...],
) -> None:
    """The pure coherence validator names exactly the rules each plan breaks."""
    assert manifest_coherence_violations(entries) == expected


def _populated_manifest_tree(tmp_path: Path) -> Path:
    """Build a coherent ``drafting`` tree whose ``[chapters]`` is already populated."""
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=4,
            has_done_flag=False,
        )
        for number in (1, 2, 3)
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


def _refuses_leaving_file_intact(working: Path) -> StateInputError:
    """Run ``set_chapters`` expecting a refusal; assert ``state.toml`` is intact."""
    state_path = working / "state.toml"
    before = state_path.read_bytes() if state_path.exists() else None
    with pytest.raises(StateInputError) as excinfo:
        set_chapters(chapters=list(_PLAN))
    after = state_path.read_bytes() if state_path.exists() else None
    assert after == before, "a refused set-chapters must leave state.toml intact"
    return excinfo.value


def test_set_chapters_refuses_populated_prior_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-empty prior ``[chapters]`` is refused with exit 3 (D3), file intact."""
    working = _populated_manifest_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    error = _refuses_leaving_file_intact(working)
    assert "populated" in str(error), "the refusal must name the populated manifest"


def test_set_chapters_refuses_incoherent_plan_leaving_file_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-contiguous plan is refused with exit 3 and leaves state.toml intact."""
    working = _empty_manifest_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    state_path = working / "state.toml"
    before = state_path.read_bytes()
    with pytest.raises(StateInputError, match=NUMBERS_CONTIGUOUS_FROM_1):
        set_chapters(chapters=[_entry(1, "a"), _entry(3, "b")])
    assert state_path.read_bytes() == before, (
        "a refused incoherent plan must leave state.toml byte-for-byte intact"
    )


def test_set_chapters_preserves_hand_authored_comments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``tomlkit`` round-trip keeps a hand-authored ``state.toml`` comment."""
    working = _empty_manifest_tree(tmp_path)
    state_path = working / "state.toml"
    sentinel = "# hand-authored sentinel comment\n"
    state_path.write_text(
        sentinel + state_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.chdir(working.parent)

    set_chapters(chapters=list(_PLAN))

    assert sentinel in state_path.read_text(encoding="utf-8"), (
        "set-chapters must preserve the hand-authored comment (ADR 002 round-trip)"
    )


def test_set_chapters_persists_manifest_before_dirs_on_mkdir_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D10: a mkdir failure leaves the populated manifest + intent already on disk.

    Monkeypatch ``Path.mkdir`` to raise after the manifest+intent atomic write but
    during directory creation. The on-disk ``state.toml`` must already carry the
    populated ``[chapters]`` and the ``operation="set-chapters"`` ``[pending_turn]``,
    proving the manifest persists *before* any directory (Decision D10/B2).
    """
    working = _empty_manifest_tree(tmp_path)
    monkeypatch.chdir(working.parent)

    import pathlib

    real_mkdir = pathlib.Path.mkdir

    def _boom(
        self: pathlib.Path,
        mode: int = 0o777,
        *,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """Fail for the chapter directories; delegate any other mkdir."""
        if self.name.startswith("chapter-"):
            msg = "injected mkdir failure"
            raise OSError(msg)
        real_mkdir(self, mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(pathlib.Path, "mkdir", _boom)

    with pytest.raises(OSError, match="injected mkdir failure"):
        set_chapters(chapters=list(_PLAN))

    state = document_to_state(load_document(working / "state.toml"))
    assert [chapter.number for chapter in state.chapters] == [1, 2], (
        "the populated manifest must already be on disk before any directory"
    )
    assert state.pending_turn is not None, "the torn turn leaves a [pending_turn]"
    assert state.pending_turn.operation == SET_CHAPTERS_OPERATION
