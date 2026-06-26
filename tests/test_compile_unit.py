"""Unit, round-trip-oracle, ordering, and property tests for ``novel-compile``.

These pin the roadmap 4.1.1 write path: :func:`compile_manuscript` concatenates
the chapter drafts in ascending manifest order, joined by the production
``DRAFT_SEPARATOR``, and writes ``working/manuscript/compiled.md`` atomically; it
returns a write-shaped ``CommandOutcome`` (no ``violations``) and is
byte-for-byte idempotent on a second run.

The load-bearing pin is the round-trip oracle: after a compile, the §5.4
``compiled-matches-drafts`` disk-evidence invariant reports no violation, so the
write path and the invariant agree on what a coherent ``compiled.md`` is
(ExecPlan Risk "output diverges from compiled-matches-drafts"). Refusals — an
empty/absent manifest, a missing ``state.toml``, an undecodable ``draft.md`` —
each route to exit ``3`` and leave any prior ``compiled.md`` intact. Every test
``monkeypatch.chdir``s into the prepared tree's parent first, because
``novel-compile`` resolves a cwd-relative ``working/`` (ExecPlan D-CWD).
"""

from __future__ import annotations

import typing as typ
import uuid

import pytest
import working_corpus as wc
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands._compile import compile_manuscript
from novel_ralph_skill.commands.novel_state import state_path, working_dir
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import (
    COMPILED_MATCHES_DRAFTS,
    DRAFT_SEPARATOR,
    check_disk_evidence,
    load_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path


def _drafting_tree(
    tmp_path: Path,
    counts: tuple[int, ...] = (3, 5, 4),
) -> Path:
    """Build a coherent ``drafting`` tree (no ``compiled.md``) and return it.

    Each chapter's ``draft.md`` carries ``counts[i]`` deterministic words, so the
    expected concatenation is exact and the tree carries no ``compiled.md`` (the
    drafting-era spec leaves it unwritten), modelling a stale/absent compile the
    command must regenerate.
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


def _expected_compiled(counts: tuple[int, ...]) -> str:
    """Return the ordered concatenation the command must write for ``counts``."""
    return wc.concatenate_drafts([wc.draft_body(count) for count in counts])


def test_compile_writes_ordered_concatenation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coherent drafting tree compiles to the ordered draft concatenation."""
    counts = (3, 5, 4)
    working = _drafting_tree(tmp_path, counts)
    monkeypatch.chdir(working.parent)

    outcome = compile_manuscript()

    assert outcome.code == ExitCode.SUCCESS, (
        "a coherent drafting tree must compile cleanly"
    )
    compiled = working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == _expected_compiled(counts), (
        "compiled.md must equal the ordered draft concatenation"
    )


def test_compile_result_is_write_shaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The success ``result`` names the write, never a checker's read shape."""
    counts = (3, 5, 4)
    working = _drafting_tree(tmp_path, counts)
    monkeypatch.chdir(working.parent)

    outcome = compile_manuscript()

    expected_bytes = len(_expected_compiled(counts).encode("utf-8"))
    assert dict(outcome.result) == {
        "compiled": "working/manuscript/compiled.md",
        "chapters": 3,
        "bytes": expected_bytes,
    }, "the success result must name the written path, chapters, and byte length"
    assert "violations" not in outcome.result, (
        "a mutator result must not carry a checker's violations read shape"
    )


def test_compile_is_byte_for_byte_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second compile over unchanged drafts leaves ``compiled.md`` unchanged."""
    working = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    compiled = working / "manuscript" / "compiled.md"

    compile_manuscript()
    first = compiled.read_bytes()
    compile_manuscript()
    second = compiled.read_bytes()

    assert second == first, "a second compile must be byte-for-byte identical"


def test_compile_round_trips_clean_under_disk_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A freshly compiled tree reports no ``compiled-matches-drafts`` violation.

    This is the load-bearing pin that the write path and the §5.4 invariant agree:
    after a compile, :func:`check_disk_evidence` finds no
    ``compiled-matches-drafts`` divergence, so ``novel-state check`` is clean.
    """
    working = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)

    compile_manuscript()

    violations = check_disk_evidence(load_state(state_path()), working_dir())
    names = {violation.invariant for violation in violations}
    assert COMPILED_MATCHES_DRAFTS not in names, (
        f"a freshly compiled tree diverged: {names}"
    )


def test_compile_orders_by_manifest_not_disk_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chapters built out of order still compile in ascending manifest order.

    The chapter specs are passed to the builder in a shuffled order, so a
    glob-derived join would diverge; the output must equal the manifest-ordered
    concatenation (ExecPlan Risk "non-deterministic write").
    """
    ordered_counts = (3, 5, 4)
    shuffled = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=ordered_counts[number - 1],
            has_done_flag=False,
        )
        # Build chapters 3, 1, 2 so the spec order differs from the manifest order.
        for number in (3, 1, 2)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=shuffled,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=3,
    )
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    compile_manuscript()

    compiled = working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == _expected_compiled(ordered_counts), (
        "compile must order by the manifest, not the disk-build order"
    )


def test_compile_absent_draft_contributes_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manifest chapter with no ``draft.md`` contributes ``""`` and succeeds.

    This pins the ``FileNotFoundError``-as-empty-string boundary against the
    ``UnicodeDecodeError``-as-exit-``3`` one: an undrafted manifest chapter is the
    empty body, exactly the disk-evidence read rule, so the compile still writes.
    """
    chapters = (
        wc.ChapterSpec(
            number=1,
            slug="chapter-01",
            title="Chapter 1",
            target_words=20000,
            draft_words=3,
            has_done_flag=False,
        ),
        wc.ChapterSpec(
            number=2,
            slug="chapter-02",
            title="Chapter 2",
            target_words=20000,
            draft_words=0,
            has_done_flag=False,
            write_draft=False,
        ),
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=2,
        by_chapter_override={"01": 3, "02": 0},
    )
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    outcome = compile_manuscript()

    assert outcome.code == ExitCode.SUCCESS, (
        "an undrafted manifest chapter must not block the compile"
    )
    compiled = working / "manuscript" / "compiled.md"
    # The second body is the empty string, so the output is "<ch1>\n\n".
    assert compiled.read_text(encoding="utf-8") == wc.concatenate_drafts([
        wc.draft_body(3),
        "",
    ]), "an absent draft.md must contribute the empty string"


def test_compile_empty_manifest_refuses_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty ``[chapters]`` manifest refuses with exit ``3`` and writes nothing."""
    working = wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path)
    monkeypatch.chdir(working.parent)

    with pytest.raises(StateInputError, match="manifest is absent or empty"):
        compile_manuscript()

    assert not (working / "manuscript" / "compiled.md").exists(), (
        "an empty-manifest refusal must write no compiled.md"
    )


def test_compile_missing_state_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing ``state.toml`` refuses with exit ``3`` (the state channel)."""
    (tmp_path / "working" / "manuscript").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(StateInputError, match="no novel working/ found in"):
        compile_manuscript()


def test_compile_undecodable_draft_refuses_and_keeps_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An undecodable ``draft.md`` refuses with exit ``3`` and keeps the prior file."""
    working = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    # Compile once to lay down a coherent prior compiled.md.
    compile_manuscript()
    compiled = working / "manuscript" / "compiled.md"
    prior = compiled.read_bytes()
    # Corrupt chapter 1's draft to invalid UTF-8.
    (working / "manuscript" / "chapter-01" / "draft.md").write_bytes(b"\xff\xfe")

    with pytest.raises(StateInputError, match="cannot read the drafts under"):
        compile_manuscript()

    assert compiled.read_bytes() == prior, (
        "a refused compile must leave the prior compiled.md intact"
    )


def test_compile_absent_manuscript_dir_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent ``manuscript/`` directory at write time refuses with exit ``3``.

    The state loads and the manifest is populated, but the temp-file creation in
    the atomic writer raises ``FileNotFoundError`` (an ``OSError``), routed to
    exit ``3`` rather than escaping to the benign exit ``1``.
    """
    working = _drafting_tree(tmp_path)
    monkeypatch.chdir(working.parent)
    # Remove the manuscript directory (and its drafts) after the state is built;
    # the read rule tolerates absent drafts (empty string), but the write needs
    # the directory.
    manuscript = working / "manuscript"
    for child in sorted(manuscript.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        else:
            child.rmdir()
    manuscript.rmdir()

    with pytest.raises(StateInputError, match="cannot write"):
        compile_manuscript()


# A contiguous manifest of chapter numbers 1..n paired with per-chapter word
# counts; building values directly keeps shrinking clean (the filtering trap).
@st.composite
def _contiguous_manifest(draw: st.DrawFn) -> list[int]:
    """Draw a list of per-chapter word counts for chapters ``1..len``."""
    size = draw(st.integers(min_value=1, max_value=6))
    return [draw(st.integers(min_value=0, max_value=30)) for _ in range(size)]


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(counts=_contiguous_manifest())
def test_compile_property_matches_join_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    counts: list[int],
) -> None:
    """Over any contiguous manifest, the compile equals the join and is stable.

    The written ``compiled.md`` equals ``DRAFT_SEPARATOR.join`` of the ordered
    draft bodies, and a second run yields identical bytes. A globally unique
    subdirectory per example isolates the function-scoped ``tmp_path`` across
    draws (the corpus builder writes into a fresh ``working/``).
    """
    dest = tmp_path / f"case-{uuid.uuid4().hex}"
    dest.mkdir()
    working = _drafting_tree(dest, tuple(counts))
    monkeypatch.chdir(working.parent)
    compiled = working / "manuscript" / "compiled.md"
    expected = DRAFT_SEPARATOR.join(wc.draft_body(count) for count in counts)

    compile_manuscript()
    first = compiled.read_text(encoding="utf-8")
    compile_manuscript()
    second = compiled.read_text(encoding="utf-8")

    assert first == expected, "compiled.md is not the separator-joined ordered bodies"
    assert second == first, "a second compile must be byte-for-byte identical"
