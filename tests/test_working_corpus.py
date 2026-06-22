"""Self-tests for the on-disk ``working/`` fixture corpus (roadmap 1.3.2).

The corpus data, builder, and oracle live in the ``working_corpus`` package and
are consumed here by pytest fixture parameter name; this module never performs a
runtime value import of corpus data. The only cross-module symbols it names are
the spec *types*, imported under ``if TYPE_CHECKING:`` via the sanctioned
``from conftest import …`` carve-out (developers-guide "Shared test
scaffolding").

These tests prove the builder materialises the tree each spec claims, writes a
``tomlkit``-round-trippable ``state.toml`` carrying every §5.1 schema table, and
that the coherent/incoherent split is real and isolated.
"""

from __future__ import annotations

import dataclasses as dc
import re
import tomllib
import typing as typ

import tomlkit

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import ChapterSpec, RepoTextReader, WorkingTreeSpec


def _read_state(working: Path) -> dict[str, typ.Any]:
    """Return the decoded ``state.toml`` mapping under ``working``."""
    return tomllib.loads((working / "state.toml").read_text(encoding="utf-8"))


def _minimal_spec(
    make_chapter: cabc.Callable[..., ChapterSpec],
    make_tree: cabc.Callable[..., WorkingTreeSpec],
) -> WorkingTreeSpec:
    """Return a minimal two-chapter coherent spec for the builder unit tests."""
    return make_tree(
        phase_current="drafting",
        phase_completed=(
            "premise",
            "treatment",
            "characters",
            "conflict-analysis",
            "setting",
            "reader-fit",
            "stc",
            "chapter-planning",
        ),
        chapters=(
            make_chapter(
                number=1,
                slug="one",
                title="One",
                target_words=3200,
                draft_words=4,
                has_done_flag=True,
            ),
            make_chapter(
                number=2,
                slug="two",
                title="Two",
                target_words=3500,
                draft_words=6,
                has_done_flag=False,
            ),
        ),
        target_words=80000,
        consecutive_clean=1,
        convergence_target=1,
        current_chapter=2,
        compiled="AUTO",
    )


class TestBuildWorkingTree:
    """Exercise :func:`build_working_tree` on minimal coherent specs."""

    def test_materialises_design_paths(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """The builder writes exactly the design paths, no earlier-draft paths."""
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        working = build_tree(spec, tmp_path)
        assert (working / "state.toml").is_file()
        assert (working / "manuscript" / "chapter-01" / "draft.md").is_file()
        assert (working / "manuscript" / "chapter-01" / "done.flag").is_file()
        assert (working / "manuscript" / "chapter-02" / "draft.md").is_file()
        assert not (working / "manuscript" / "chapter-02" / "done.flag").exists()
        assert (working / "manuscript" / "compiled.md").is_file()
        assert (working / "plan" / "chapter-outline.md").is_file()
        # The earlier-draft paths design §5.1 names as wrong must not appear.
        assert not (working / "compiled.md").exists()
        assert not (working / "chapter-01").exists()

    def test_state_decodes_to_declared_values(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """The read-back ``state.toml`` matches the spec, with string keys."""
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        working = build_tree(spec, tmp_path)
        state = _read_state(working)
        assert state["phase"]["current"] == "drafting"
        assert tuple(state["phase"]["completed"]) == spec.phase_completed
        word_counts = state["word_counts"]
        assert word_counts["target"] == 80000
        assert word_counts["by_chapter"] == {"01": 4, "02": 6}
        assert word_counts["current"] == 10
        assert state["drafting"]["critic"]["convergence_target"] == 1
        manifest = state["chapters"]
        assert [entry["number"] for entry in manifest] == [1, 2]

    def test_current_words_override_breaks_invariant_3_on_disk(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """``current_words_override`` yields ``sum(by_chapter) != current`` on disk.

        Without the override, design §5.2 invariant 3 holds on disk
        (``sum(by_chapter) == current``); the override writes ``current``
        verbatim while ``by_chapter`` still derives from the drafts, so the
        materialised ``state.toml`` carries a genuine invariant-3 violation —
        exactly what task 2.1.2's validator will read.
        """
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        coherent = _read_state(build_tree(spec, tmp_path))["word_counts"]
        assert sum(coherent["by_chapter"].values()) == coherent["current"]
        violating = build_tree(
            dc.replace(spec, current_words_override=1), tmp_path / "violating"
        )
        word_counts = _read_state(violating)["word_counts"]
        assert word_counts["current"] == 1
        assert sum(word_counts["by_chapter"].values()) != word_counts["current"]

    def test_state_carries_every_schema_table(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """Every §5.1 table a "parse without loss" consumer needs is present."""
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        state = _read_state(build_tree(spec, tmp_path))
        assert state["schema_version"] == 1
        assert state["novel"]["created_at"] == "2026-05-23T14:00:00Z"
        critic = state["drafting"]["critic"]
        assert set(critic["last_finding_counts"]) == {
            "blocker",
            "major",
            "minor",
            "taste",
        }
        assert state["drafting"]["fangirl"]["last_chapter_passed"] == 0
        assert set(state["gates"]["knitting"]) == {"done_30", "done_50", "done_80"}
        assert "final_pass_complete" in state["gates"]["final"]

    def test_round_trip_idempotent(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """A ``tomlkit`` parse-then-dump of ``state.toml`` is byte-idempotent."""
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        text = (build_tree(spec, tmp_path) / "state.toml").read_text(encoding="utf-8")
        assert tomlkit.dumps(tomlkit.parse(text)) == text, (
            "a tomlkit parse-then-dump altered state.toml, so the task-2.2.1 "
            "no-op round-trip could not preserve this corpus state file"
        )


class TestCompileModel:
    """Pin the §4.3/§9 concatenation compile model the corpus uses."""

    def test_auto_writes_concatenation(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        compile_probe: tuple[cabc.Callable[..., Path], cabc.Callable[..., str]],
    ) -> None:
        """``compiled="AUTO"`` writes the hash-equal concatenation of drafts."""
        build_tree, concatenate = compile_probe
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        manuscript = build_tree(spec, tmp_path) / "manuscript"
        compiled = (manuscript / "compiled.md").read_text(encoding="utf-8")
        drafts = [
            (manuscript / "chapter-01" / "draft.md").read_text(encoding="utf-8"),
            (manuscript / "chapter-02" / "draft.md").read_text(encoding="utf-8"),
        ]
        assert compiled == concatenate(drafts)

    def test_explicit_string_written_verbatim(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """A non-``AUTO`` ``compiled`` string is written exactly as given."""
        spec = _minimal_spec(make_chapter_spec, make_working_tree_spec)
        stale = dc.replace(spec, compiled="stale bytes")
        working = build_tree(stale, tmp_path)
        compiled = (working / "manuscript" / "compiled.md").read_text(encoding="utf-8")
        assert compiled == "stale bytes"


class TestDraftBody:
    """Pin the deterministic word-body helper the builder writes drafts with."""

    def test_word_count_is_exact(
        self,
        tmp_path: Path,
        make_chapter_spec: cabc.Callable[..., ChapterSpec],
        make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
        build_tree: cabc.Callable[..., Path],
    ) -> None:
        """``draft_words=N`` yields a draft with exactly ``N`` tokens."""
        spec = make_working_tree_spec(
            phase_current="drafting",
            phase_completed=(),
            chapters=(
                make_chapter_spec(
                    number=1,
                    slug="one",
                    title="One",
                    target_words=10,
                    draft_words=7,
                    has_done_flag=False,
                ),
                make_chapter_spec(
                    number=2,
                    slug="two",
                    title="Two",
                    target_words=10,
                    draft_words=0,
                    has_done_flag=False,
                ),
            ),
            target_words=100,
            consecutive_clean=0,
            convergence_target=1,
            current_chapter=1,
        )
        working = build_tree(spec, tmp_path)
        full = (working / "manuscript" / "chapter-01" / "draft.md").read_text(
            encoding="utf-8"
        )
        empty = (working / "manuscript" / "chapter-02" / "draft.md").read_text(
            encoding="utf-8"
        )
        assert len(full.split()) == 7
        assert not empty


# The phase enum block in ``state-layout.md`` (the "### Phase enum" / "In order:"
# section): one phase per line inside a fenced ``text`` block. Parsing the order
# from the reference keeps it the single source of truth rather than re-typing it
# in the test.
_PHASE_ENUM_RE = re.compile(
    r"### Phase enum\n+In order:\n+```text\n(?P<body>.*?)\n```",
    re.DOTALL,
)


def _phases_from_reference(text: str) -> tuple[str, ...]:
    """Return the ordered phase enum parsed from ``state-layout.md`` text."""
    match = _PHASE_ENUM_RE.search(text)
    if match is None:
        msg = "state-layout.md is missing the phase enum block"
        raise AssertionError(msg)
    # Each line is a phase name, optionally followed by an inline ``#`` comment
    # (e.g. ``drafting          # contains the inner Ralph loop``); take the
    # leading token only.
    return tuple(
        stripped.split()[0]
        for line in match.group("body").splitlines()
        if (stripped := line.strip())
    )


class TestPhaseStates:
    """Exercise the eleven coherent phase-state trees and their ordering."""

    def test_each_phase_materialises_in_order(
        self,
        phase_names: tuple[str, ...],
        phase_state_tree: cabc.Callable[[str], Path],
    ) -> None:
        """Each phase tree carries its phase and the in-order completed prefix."""
        for index, phase in enumerate(phase_names):
            working = phase_state_tree(phase)
            state = _read_state(working)
            assert state["phase"]["current"] == phase
            assert tuple(state["phase"]["completed"]) == phase_names[:index]

    def test_phase_names_match_reference(
        self,
        phase_names: tuple[str, ...],
        read_repo_text: RepoTextReader,
    ) -> None:
        """The phase tuple equals the enum parsed from ``state-layout.md``."""
        reference = read_repo_text(
            "skill", "novel-ralph", "references", "state-layout.md"
        )
        assert phase_names == _phases_from_reference(reference)

    def test_baseline_is_mid_drafting(
        self,
        baseline_tree: cabc.Callable[[], Path],
    ) -> None:
        """The coherent baseline is a populated mid-drafting tree."""
        state = _read_state(baseline_tree())
        assert state["phase"]["current"] == "drafting"
        assert state["chapters"], "the baseline must carry a populated manifest"


class TestCoherentIncoherentSplit:
    """Prove the coherent/incoherent split is real and isolated (Work item 3)."""

    def test_each_variant_breaks_exactly_its_invariant(
        self,
        incoherent_variant_names: tuple[str, ...],
        incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
    ) -> None:
        """Each incoherent variant fails on exactly its one named invariant."""
        for name in incoherent_variant_names:
            spec, working, expected = incoherent_tree(name)
            violations = check_corpus(spec, working)
            assert violations == (expected,), (
                f"variant {name!r} should break only {expected!r}, got {violations!r}"
            )

    def test_coherent_trees_pass_the_oracle(
        self,
        coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
    ) -> None:
        """The baseline and all eleven phase states pass the oracle clean."""
        for spec, working in coherent_oracle_cases:
            violations = check_corpus(spec, working)
            assert violations == (), (
                f"coherent tree {spec.phase_current!r} unexpectedly flagged "
                f"{violations!r}"
            )

    def test_every_invariant_name_is_exercised(
        self,
        incoherent_variant_names: tuple[str, ...],
        incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
        corpus_invariant_names: tuple[str, ...],
    ) -> None:
        """Every oracle invariant name is the target of at least one variant."""
        exercised = {incoherent_tree(name)[2] for name in incoherent_variant_names}
        assert exercised == set(corpus_invariant_names), (
            "the corpus must exercise every oracle invariant; missing: "
            f"{set(corpus_invariant_names) - exercised}"
        )
