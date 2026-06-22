"""Parse tests for the typed ``state.toml`` schema (roadmap 2.1.1).

The tests are split into a breadth coverage pass and a depth without-loss pass,
because the §1.3.2 corpus surface makes exact word-count values nameable only
for trees the test authors itself (see the ExecPlan
``docs/execplans/roadmap-2-1-1.md`` Decision Log "the without-loss test is split
in two"):

* :func:`test_every_coherent_tree_parses` is the breadth guarantee — every
  coherent library tree decodes, its phases resolve and round-trip to the spec,
  its manifest is ascending, and ``pending_turn`` is ``None``.
* :func:`test_authored_spec_parses_without_loss` is the depth guarantee — a
  test-authored spec reproduces every field exactly.
* :func:`test_last_finding_counts_land_on_their_attributes` and
  :func:`test_uncleared_pending_turn_parses` cover the two fields the library
  trees cannot vary (the hard-coded finding counts and the populated
  ``[pending_turn]``).

Corpus data is consumed only through the sanctioned fixtures; spec *types* are
imported under the ``TYPE_CHECKING`` carve-out (developers-guide "Shared test
scaffolding").
"""

from __future__ import annotations

import itertools
import typing as typ

from novel_ralph_skill.state import (
    CriticState,
    Phase,
    State,
    load_state,
    parse_state,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import ChapterSpec, WorkingTreeSpec


def test_every_coherent_tree_parses(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
) -> None:
    """Every coherent corpus tree decodes with phases resolving and no pending turn.

    This is the breadth half of the §2.1.1 criterion: the baseline and all
    eleven phase states parse without raising, their phases round-trip to the
    spec's declared strings, the manifest is ascending by number, and the
    settled trees carry no ``[pending_turn]``. It deliberately names no derived
    ``current``/``by_chapter`` value, since those are not on the spec and the
    deriving helpers are not sanctioned fixtures.
    """
    assert coherent_oracle_cases, "expected at least the baseline plus phases"
    for spec, working in coherent_oracle_cases:
        state = load_state(working / "state.toml")
        assert isinstance(state, State)
        assert isinstance(state.phase.current, Phase)
        assert all(isinstance(member, Phase) for member in state.phase.completed)
        assert str(state.phase.current) == spec.phase_current
        completed = tuple(str(member) for member in state.phase.completed)
        assert completed == spec.phase_completed
        numbers = [entry.number for entry in state.chapters]
        assert numbers == sorted(numbers)
        assert all(a < b for a, b in itertools.pairwise(numbers))
        assert state.pending_turn is None


def _two_chapter_spec(
    make_chapter: cabc.Callable[..., ChapterSpec],
    make_tree: cabc.Callable[..., WorkingTreeSpec],
) -> WorkingTreeSpec:
    """Return a coherent two-chapter spec with distinct, non-default values.

    Distinct ``slug``/``title``/``number``/``target_words`` per chapter make a
    transposition bug observable, and ``convergence_target=2`` (non-default)
    proves the parser reads the field rather than hard-coding the default.
    """
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
                slug="ignition",
                title="Ignition",
                target_words=3200,
                draft_words=4,
                has_done_flag=True,
            ),
            make_chapter(
                number=2,
                slug="afterburn",
                title="Afterburn",
                target_words=3500,
                draft_words=6,
                has_done_flag=False,
            ),
        ),
        target_words=80000,
        consecutive_clean=1,
        convergence_target=2,
        current_chapter=2,
        current_scene=3,
        current_beat=5,
        compiled="AUTO",
    )


def test_authored_spec_parses_without_loss(
    tmp_path: Path,
    make_chapter_spec: cabc.Callable[..., ChapterSpec],
    make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
    build_tree: cabc.Callable[..., Path],
) -> None:
    """A test-authored tree reproduces every declared field on the parsed state.

    This is the depth half of the §2.1.1 criterion. Because the test declares
    every value, it asserts the parsed :class:`State` reproduces them exactly:
    the schema version, novel metadata, the drafting cursor, the phases as
    members, a non-default ``convergence_target``, the word counts including the
    ``by_chapter`` mapping and its sum, and the ``[chapters]`` manifest order.
    """
    spec = _two_chapter_spec(make_chapter_spec, make_working_tree_spec)
    working = build_tree(spec, tmp_path)
    state = load_state(working / "state.toml")

    assert state.schema_version == 1
    assert state.novel.title == "Working Title"
    assert state.novel.slug == "working-title"
    assert state.novel.target_word_count == 80000
    assert state.novel.created_at == "2026-05-23T14:00:00Z"

    assert state.phase.current is Phase.DRAFTING
    assert state.phase.completed == (
        Phase.PREMISE,
        Phase.TREATMENT,
        Phase.CHARACTERS,
        Phase.CONFLICT_ANALYSIS,
        Phase.SETTING,
        Phase.READER_FIT,
        Phase.STC,
        Phase.CHAPTER_PLANNING,
    )

    assert state.drafting.current_chapter == 2
    assert state.drafting.current_scene == 3
    assert state.drafting.current_beat == 5
    assert state.drafting.critic.convergence_target == 2
    assert state.drafting.fangirl.last_chapter_passed == 0

    assert state.word_counts.target == 80000
    assert state.word_counts.by_chapter == {"01": 4, "02": 6}
    assert state.word_counts.current == 10

    assert tuple(
        (entry.number, entry.slug, entry.title, entry.target_words)
        for entry in state.chapters
    ) == (
        (1, "ignition", "Ignition", 3200),
        (2, "afterburn", "Afterburn", 3500),
    )

    assert state.pending_turn is None


def test_last_finding_counts_land_on_their_attributes() -> None:
    """Distinct non-zero finding counts each land on their own attribute.

    The corpus hard-codes all four counts to zero, so a transposition could
    pass unseen there. This exercises :func:`parse_state` directly with the
    ``state-layout.md`` example tally ``blocker=0, major=2, minor=4, taste=7``,
    proving each count reaches its own :class:`CriticState` attribute.
    """
    raw = _minimal_raw_state(
        last_finding_counts={
            "blocker": 0,
            "major": 2,
            "minor": 4,
            "taste": 7,
        }
    )
    critic = parse_state(raw).drafting.critic
    assert isinstance(critic, CriticState)
    counts = critic.last_finding_counts
    assert counts.blocker == 0
    assert counts.major == 2
    assert counts.minor == 4
    assert counts.taste == 7


def test_uncleared_pending_turn_parses(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """The ``uncleared-pending-turn`` variant parses a populated ``PendingTurn``.

    The variant writes ``paths`` as a TOML array; asserting against a ``tuple``
    proves :func:`parse_state` coerced the decoded ``list`` rather than leaving
    it on the ``tuple``-typed field. The schema judges only structural presence;
    whether the turn should be cleared is the §5.2 validator's concern (2.1.2).
    """
    _spec, working, _expected = incoherent_tree("uncleared-pending-turn")
    pending = load_state(working / "state.toml").pending_turn
    assert pending is not None
    assert pending.operation == "write-draft"
    assert pending.paths == ("working/manuscript/chapter-03/draft.md",)


def _minimal_raw_state(*, last_finding_counts: dict[str, int]) -> dict[str, object]:
    """Return a minimal decoded ``state.toml`` mapping for a direct parse test.

    The shape matches what ``tomllib.load`` returns: nested ``dict`` tables and
    ``list`` arrays. ``last_finding_counts`` is injected so a caller can vary the
    one field the corpus fixes at zero.
    """
    return {
        "schema_version": 1,
        "novel": {
            "title": "Working Title",
            "slug": "working-title",
            "target_word_count": 80000,
            "created_at": "2026-05-23T14:00:00Z",
        },
        "phase": {"current": "drafting", "completed": ["premise"]},
        "drafting": {
            "current_chapter": 1,
            "current_scene": 0,
            "current_beat": 0,
            "critic": {
                "pass": 1,
                "consecutive_clean": 0,
                "convergence_target": 1,
                "last_finding_counts": last_finding_counts,
            },
            "fangirl": {"last_chapter_passed": 0},
        },
        "gates": {
            "knitting": {
                "done_30": False,
                "done_50": False,
                "done_80": False,
            },
            "final": {"final_pass_complete": False},
        },
        "word_counts": {"target": 80000, "current": 0, "by_chapter": {}},
        "chapters": [
            {
                "number": 1,
                "slug": "one",
                "title": "One",
                "target_words": 3200,
            }
        ],
    }
