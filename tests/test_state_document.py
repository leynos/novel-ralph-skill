"""Round-trip, atomic-write, and ``[pending_turn]`` tests for ``document.py``.

These suites guard the write half of the ``state`` slice (roadmap task 2.2.1):
the lossless ``tomlkit`` round-trip (ADR-002 Functional req 1-2), the atomic
temp-file-plus-``Path.replace`` write (design §3.4), and the ``[pending_turn]``
intent bracket (design §3.4).

The round-trip *property* draws over a hand-authored, comment-and-layout-bearing
``state.toml`` (``COMMENT_BEARING_STATE_TOML``) rather than the comment-free
corpus, because the corpus builder emits no comments and so cannot guard
ADR-002's "including comments and whitespace" clause (ExecPlan round-1 review
B1/B2). The corpus sweep runs as an additional breadth case only.
"""

from __future__ import annotations

import tempfile
import typing as typ
from pathlib import Path

import pytest
import tomlkit
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state.document import (
    clear_pending_turn,
    document_to_state,
    load_document,
    open_pending_turn,
    pending_turn,
    write_document_atomically,
)
from novel_ralph_skill.state.parse import parse_state
from novel_ralph_skill.state.schema import PendingTurn

if typ.TYPE_CHECKING:
    from conftest import WorkingTreeSpec

# A hand-authored, schema-valid ``state.toml`` carrying block comments, an
# inline value comment, deliberate blank-line layout, an inline ``by_chapter``
# table, and an array-of-tables ``[[chapters]]``. This is the carrier of the
# comment-preservation guarantee: a byte-for-byte no-op round-trip over it
# constrains comment and whitespace preservation, which the comment-free corpus
# cannot (ExecPlan round-1 review B1/B2). The unique ``current = 3200`` line
# lets the surgical-mutation property assert a string-replacement oracle.
COMMENT_BEARING_STATE_TOML = """\
# novel-ralph state.toml — hand-authored layout for the round-trip property.
# This block comment, the inline comment below, the blank lines, the inline
# by_chapter table, and the [[chapters]] array-of-tables must all survive a
# no-op write byte-for-byte (ADR-002 Functional requirement 1).
schema_version = 1

[novel]
title = "The Lantern Keeper"
slug = "the-lantern-keeper"
target_word_count = 80000
created_at = "2026-06-22T09:00:00Z"

[phase]
current = "drafting"
completed = ["premise", "treatment", "characters"]

[drafting]
current_chapter = 2
current_scene = 0
current_beat = 0

[drafting.critic]
pass = 1
consecutive_clean = 0
convergence_target = 1
last_finding_counts = { blocker = 0, major = 0, minor = 0, taste = 0 }

[drafting.fangirl]
last_chapter_passed = 1

[gates.knitting]
done_30 = false
done_50 = false
done_80 = false

[gates.final]
final_pass_complete = false

[word_counts]
target = 80000
current = 3200  # running total across compiled chapters
by_chapter = { "01" = 3200 }

[[chapters]]
number = 1
slug = "chapter-01"
title = "Arrival"
target_words = 4000

[[chapters]]
number = 2
slug = "chapter-02"
title = "The Lighthouse"
target_words = 4000
"""


@st.composite
def _comment_bearing_documents(draw: st.DrawFn) -> str:
    """Return a comment-and-layout-bearing ``state.toml`` source string.

    Draws small permutations of :data:`COMMENT_BEARING_STATE_TOML` — varying the
    inline running-total comment text and the ``word_counts.current`` value — so
    the no-op property exercises a family of comment-bearing inputs rather than
    a single literal. Every draw is itself a valid, schema-parsable ``state.toml``
    that round-trips through ``tomlkit`` byte-for-byte, so the strategy
    constructs only valid inputs (no rejection sampling).
    """
    comment = draw(
        st.sampled_from((
            "running total across compiled chapters",
            "current word count, summed from drafts",
            "tally — keep in step with by_chapter",
        ))
    )
    current = draw(st.integers(min_value=0, max_value=999_999))
    return COMMENT_BEARING_STATE_TOML.replace(
        "current = 3200  # running total across compiled chapters",
        f"current = {current}  # {comment}",
    ).replace('by_chapter = { "01" = 3200 }', f'by_chapter = {{ "01" = {current} }}')


def _write_state(content: str, directory: Path) -> Path:
    """Write ``content`` to a ``state.toml`` under ``directory`` and return it."""
    path = directory / "state.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_comment_bearing_fixture_parses() -> None:
    """The hand-authored fixture is schema-valid for ``parse_state``.

    Guards the fixture itself: if a later edit breaks its schema shape the
    round-trip property would test a meaningless input, so pin that the fixture
    parses to a typed :class:`State` with the expected identity.
    """
    state = parse_state(tomlkit.parse(COMMENT_BEARING_STATE_TOML))
    assert state.novel.title == "The Lantern Keeper", "fixture novel title drifted"
    assert state.word_counts.current == 3200, "fixture current word count drifted"
    assert len(state.chapters) == 2, "fixture must carry two array-of-tables chapters"


@settings(deadline=None)
@given(content=_comment_bearing_documents())
def test_noop_round_trip_is_byte_identical(content: str) -> None:
    """A no-op load-and-write over comment-bearing input is byte-for-byte stable.

    Reads the document, writes it back through the atomic writer with no edit,
    and compares the on-disk bytes. This is the §5.3 round-trip property
    design §9 names ("a no-op ``recount`` preserves formatting and comments")
    and ADR-002 Functional req 1's "including comments and whitespace"
    guarantee. It draws over comment-bearing input so the assertion genuinely
    constrains comment and whitespace preservation.

    A fresh ``tempfile.TemporaryDirectory`` per input (rather than the
    function-scoped ``tmp_path`` fixture) keeps each generated case isolated, as
    Hypothesis requires for fixtures that are not reset between draws.
    """
    with tempfile.TemporaryDirectory() as directory:
        path = _write_state(content, Path(directory))
        document = load_document(path)
        write_document_atomically(document, path)
        assert path.read_text(encoding="utf-8") == content, (
            "no-op round-trip lost comments or whitespace"
        )


def test_noop_round_trip_over_corpus_trees(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
) -> None:
    """A no-op write-back is byte-identical across every coherent corpus tree.

    Breadth over the real §5.1 schema shapes (the baseline and eleven phase
    states). This is *not* the carrier of the comment guarantee — the corpus
    builder emits no comments — but it confirms the round-trip holds over every
    state shape the harness actually produces.
    """
    for _spec, working_dir in coherent_oracle_cases:
        path = working_dir / "state.toml"
        original = path.read_text(encoding="utf-8")
        document = load_document(path)
        write_document_atomically(document, path)
        assert path.read_text(encoding="utf-8") == original, (
            f"no-op round-trip changed bytes for corpus tree {working_dir}"
        )


@settings(deadline=None)
@given(new_current=st.integers(min_value=0, max_value=999_999))
def test_surgical_mutation_rewrites_only_the_value(new_current: int) -> None:
    """Editing ``word_counts.current`` rewrites only that value's bytes.

    Over the comment-bearing fixture, set ``word_counts.current`` to a generated
    integer, write atomically, and assert the on-disk bytes equal a *string
    replacement* of the old value in the original — so only the touched value's
    bytes changed and every comment and blank-line layout survived. This is the
    "a real mutation changes only the targeted values, leaving surrounding
    formatting and comments intact" requirement of ADR-002 Functional req 2,
    pinned at the locked tomlkit 0.15.0 over comment-bearing input.

    The fixture's ``current = 3200`` line (with its trailing running-total
    comment) is a unique substring distinct from the ``by_chapter`` entry, so
    the string-replacement oracle targets exactly the edited value.
    """
    with tempfile.TemporaryDirectory() as directory:
        path = _write_state(COMMENT_BEARING_STATE_TOML, Path(directory))
        document = load_document(path)
        document["word_counts"]["current"] = new_current
        write_document_atomically(document, path)
        expected = COMMENT_BEARING_STATE_TOML.replace(
            "current = 3200  # running total across compiled chapters",
            f"current = {new_current}  # running total across compiled chapters",
        )
        out = path.read_text(encoding="utf-8")
        assert out == expected, "surgical mutation rewrote more than the value"
        assert "# running total across compiled chapters" in out, (
            "the inline value comment was lost"
        )
        assert out.startswith("# novel-ralph state.toml"), (
            "the leading block comment was lost"
        )


def test_atomic_write_emits_dumps_of_document(tmp_path: Path) -> None:
    """A successful write leaves ``tomlkit.dumps(document)`` on disk.

    The live file after a write equals the document's serialization exactly, so
    the writer adds no trailing newline or reflow of its own.
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    document = load_document(path)
    write_document_atomically(document, path)
    assert path.read_text(encoding="utf-8") == tomlkit.dumps(document)


def test_atomic_write_uses_temp_file_in_target_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The temporary file is created in the target's directory, not elsewhere.

    A temp file outside ``path.parent`` would put the rename across filesystems
    and lose atomicity (design §3.4). Capture the temp path through a
    ``Path.replace`` spy — the renamed source is the temp file — and assert its
    parent is ``path.parent``, then perform the real replace so the write
    completes.
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    document = load_document(path)
    seen_temp_parents: list[Path] = []
    real_replace = Path.replace

    def _spy_replace(self: Path, target: Path) -> None:
        """Record the temp file's parent then delegate to the real rename."""
        seen_temp_parents.append(self.parent)
        real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _spy_replace)
    write_document_atomically(document, path)
    assert seen_temp_parents == [path.parent], (
        "temp file was not created in path.parent"
    )


def test_atomic_write_leaves_prior_file_and_no_temp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure before the rename leaves the prior file and no stray temp file.

    Force ``Path.replace`` to raise, then assert the live ``state.toml`` is the
    prior bytes byte-for-byte and the target directory holds no leftover
    temporary file (the "untorn on crash" requirement, design §3.4).
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    document = load_document(path)
    document["word_counts"]["current"] = 9999

    def _boom(self: Path, target: Path) -> None:
        """Raise as if the rename failed mid-write."""
        del self, target
        msg = "simulated rename failure"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", _boom)
    with pytest.raises(OSError, match="simulated rename failure"):
        write_document_atomically(document, path)
    assert path.read_text(encoding="utf-8") == COMMENT_BEARING_STATE_TOML, (
        "a failed write must leave the prior coherent state.toml untorn"
    )
    leftovers = [
        child
        for child in tmp_path.iterdir()
        if child.name != "state.toml" and child.is_file()
    ]
    assert leftovers == [], f"a failed write left stray temp files: {leftovers}"


def test_open_pending_turn_round_trips_through_schema(tmp_path: Path) -> None:
    """``open_pending_turn`` writes a record ``parse_state`` reads back.

    The keys must match :class:`PendingTurn` so the schema parser reconstructs
    the operation and paths the writer recorded.
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    document = load_document(path)
    paths = ("working/state.toml", "working/manuscript/compiled.md")
    open_pending_turn(document, operation="recount", paths=paths)
    parsed = parse_state(document)
    assert parsed.pending_turn == PendingTurn(operation="recount", paths=paths)


def test_clear_pending_turn_restores_parsed_state(tmp_path: Path) -> None:
    """Opening then clearing ``[pending_turn]`` re-parses to the original state.

    The clear-restores contract is asserted at parsed-:class:`State` equality,
    not byte-for-byte: ``tomlkit`` table insertion-then-removal can leave a
    residual blank line (ExecPlan Risk "pending_turn whitespace"), but the
    cleared document must carry no ``[pending_turn]`` and re-parse to the
    original tables.
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    original = document_to_state(load_document(path))
    document = load_document(path)
    open_pending_turn(document, operation="set-cursor", paths=("working/state.toml",))
    clear_pending_turn(document)
    restored = document_to_state(document)
    assert restored == original, "clearing pending_turn did not restore the state"
    assert restored.pending_turn is None, "a cleared document still carries the record"


def test_clear_pending_turn_is_idempotent_on_settled_state(tmp_path: Path) -> None:
    """Clearing a document with no ``[pending_turn]`` is a safe no-op."""
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    document = load_document(path)
    clear_pending_turn(document)
    assert document_to_state(document).pending_turn is None


def test_pending_turn_clean_exit_clears_and_keeps_value_edit(tmp_path: Path) -> None:
    """A clean bracket exit clears the record and keeps an in-bracket value edit.

    This pins the A1 contract: the clean-exit write re-dumps the *yielded,
    caller-mutated* document, not a reloaded fresh copy, so a value edit made
    inside the bracket survives and ``[pending_turn]`` is cleared (ExecPlan
    Decision log).
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    with pending_turn(
        path, operation="recount", paths=("working/state.toml",)
    ) as document:
        # A real mutator (e.g. recount) edits state values on the yielded
        # document inside the bracket.
        document["word_counts"]["current"] = 5555
    final = document_to_state(load_document(path))
    assert final.pending_turn is None, "clean exit must clear pending_turn"
    assert final.word_counts.current == 5555, "in-bracket value edit was lost"


def test_pending_turn_writes_record_before_yield(tmp_path: Path) -> None:
    """The record is on disk while the bracket body runs.

    A reader during the artefact work sees the populated ``[pending_turn]``, so
    a crash mid-bracket leaves it for the next turn to reconcile (design §3.4).
    """
    path = _write_state(COMMENT_BEARING_STATE_TOML, tmp_path)
    with pending_turn(path, operation="advance-phase", paths=("working/state.toml",)):
        mid = parse_state(load_document(path))
        assert mid.pending_turn == PendingTurn(
            operation="advance-phase", paths=("working/state.toml",)
        ), "the record must be persisted before the bracket body runs"
