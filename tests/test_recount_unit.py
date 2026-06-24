"""Unit and property tests for the ``recount`` mutator body (roadmap 2.3.1).

These pin the ``recount`` body without the Cyclopts layer (mirroring
``tests/test_state_mutators_unit.py``):

- a two-chapter tree with wrong hand-typed counts recounts to the summed
  ``current`` and per-chapter table, returns exit ``0`` with a write-shaped
  ``result`` (no ``violations``), and a second run leaves ``state.toml``
  byte-for-byte identical (idempotence);
- the fault boundary: a missing, structurally-incomplete, or undecodable-draft
  state each raises ``StateInputError`` (exit ``3``) leaving the prior file
  intact, while an *absent* ``draft.md`` succeeds with that chapter at ``0`` —
  the two sides of the ``FileNotFoundError``-as-``0`` versus
  ``UnicodeDecodeError``-as-exit-``3`` line (Round-1 blocking 3);
- a legitimate refusal: a tree whose hand-typed counts pass the pure-state
  checker but whose disk-recounted ``by_chapter`` breaches the
  ``gate-ratio-consistent`` invariant refuses with exit ``3``, names the
  invariant, and leaves the file intact;
- a Hypothesis property: over generated per-chapter word counts against a fixed
  manifest, ``recount`` succeeds and the written state passes ``validate_state``
  with ``sum(by_chapter) == current`` (accept-iff-coherent).

The corpus spec/builder is used by direct value import (``working_corpus as wc``),
the carve-out the BDD step modules already use, so each test stays within
pylint's argument budget (only ``tmp_path``/``monkeypatch`` as fixtures). Every
``recount`` call is preceded by ``monkeypatch.chdir(working.parent)`` because
``recount`` resolves a cwd-relative ``working/state.toml`` (Decision Log D-CWD;
``test_state_mutators_unit.py:200-208``).
"""

from __future__ import annotations

import contextlib
import typing as typ
from itertools import starmap

import pytest
import working_corpus as wc
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands._recount import recount
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import (
    GATE_RATIO_CONSISTENT,
    document_to_state,
    load_document,
    validate_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

    from novel_ralph_skill.contract.runner import CommandOutcome

_TARGET_WORDS = 80000
# The completed prefix for a coherent ``drafting``-phase tree (``premise`` … ``stc``).
_DRAFTING_PREFIX = wc.PHASE_ORDER[:8]


def _chapter(
    number: int,
    draft_words: int,
    *,
    target_words: int = 20000,
    write_draft: bool = True,
) -> wc.ChapterSpec:
    """Return a minimal coherent :class:`ChapterSpec` for ``number``.

    ``write_draft=False`` models a chapter directory with no ``draft.md`` (the
    absent-draft case); ``target_words`` lets a gate-breach tree size its drafts.
    """
    return wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=target_words,
        draft_words=draft_words,
        has_done_flag=False,
        write_draft=write_draft,
    )


def _drafting_spec(
    chapters: tuple[wc.ChapterSpec, ...],
    *,
    by_chapter_override: dict[str, int] | None = None,
    current_words_override: int | None = None,
    gates: tuple[bool, bool, bool] = (False, False, False),
) -> wc.WorkingTreeSpec:
    """Return a coherent ``drafting``-phase spec over ``chapters``, with overrides.

    The overrides let a test pin a deliberately wrong hand-typed ``[word_counts]``
    (``by_chapter_override``/``current_words_override``) and force the knitting
    gates (``gates`` as ``(done_30, done_50, done_80)``), so a recount has
    something to correct or to breach.
    """
    done_30, done_50, done_80 = gates
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=_DRAFTING_PREFIX,
        chapters=chapters,
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        by_chapter_override=by_chapter_override,
        current_words_override=current_words_override,
        done_30=done_30,
        done_50=done_50,
        done_80=done_80,
    )


def _wrong_count_tree(tmp_path: Path) -> Path:
    """Build a two-chapter tree (3 + 5 words) with *wrong* hand-typed counts.

    The chapters draft three and five words on disk, but ``by_chapter_override``
    and ``current_words_override`` record a deliberately wrong total, so a recount
    has something to correct. The 8/80000 ratio crosses no gate, so the recounted
    state is coherent.
    """
    spec = _drafting_spec(
        (_chapter(1, 3), _chapter(2, 5)),
        by_chapter_override={"01": 999, "02": 999},
        current_words_override=1998,
    )
    return wc.build_working_tree(spec, tmp_path)


def test_recount_corrects_wrong_counts_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wrong-count tree recounts to the summed total; a second run is byte-stable."""
    working = _wrong_count_tree(tmp_path)
    monkeypatch.chdir(working.parent)

    outcome = recount()

    assert outcome.code == ExitCode.SUCCESS
    assert dict(outcome.result) == {
        "current": 8,
        "by_chapter": {"01": 3, "02": 5},
    }, f"recount should write the summed counts, got {dict(outcome.result)}"
    assert "violations" not in outcome.result, (
        "recount success result must not echo the check read shape"
    )

    document = load_document(working / "state.toml")
    assert document["word_counts"]["current"] == 8
    assert dict(document["word_counts"]["by_chapter"]) == {"01": 3, "02": 5}

    # A second recount over unchanged drafts is byte-for-byte identical.
    after_first = (working / "state.toml").read_bytes()
    recount()
    after_second = (working / "state.toml").read_bytes()
    assert after_second == after_first, "a second recount must be byte-stable"


def test_recount_absent_draft_counts_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A manifest chapter with no ``draft.md`` recounts to ``0`` and succeeds.

    This pins the benign ``FileNotFoundError``-as-``0`` side of the fault boundary
    opposite the undecodable-draft exit-``3`` case (Round-1 blocking 3).
    """
    spec = _drafting_spec(
        (_chapter(1, 4), _chapter(2, 0, write_draft=False)),
    )
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    outcome = recount()

    assert outcome.code == ExitCode.SUCCESS
    assert dict(outcome.result) == {"current": 4, "by_chapter": {"01": 4, "02": 0}}


def _refuses_leaving_file_intact(working: Path) -> StateInputError:
    """Run ``recount`` expecting a refusal; assert the file is byte-for-byte intact.

    Returns the raised :class:`StateInputError` so the caller can inspect its
    message (the refusal reason).
    """
    state_path = working / "state.toml"
    before = state_path.read_bytes() if state_path.exists() else None
    with pytest.raises(StateInputError) as excinfo:
        recount()
    after = state_path.read_bytes() if state_path.exists() else None
    assert after == before, "a refused recount must leave state.toml intact"
    return excinfo.value


def test_recount_missing_state_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cwd with no ``working/state.toml`` refuses with exit ``3``."""
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path)
    _refuses_leaving_file_intact(tmp_path / "working")


def test_recount_incomplete_state_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A structurally-incomplete ``state.toml`` refuses with exit ``3``."""
    working = tmp_path / "working"
    working.mkdir()
    (working / "state.toml").write_text("schema_version = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _refuses_leaving_file_intact(working)


def test_recount_undecodable_draft_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An undecodable ``draft.md`` refuses with exit ``3`` and leaves the file intact.

    This pins the ``UnicodeDecodeError``-as-exit-``3`` side of the fault boundary
    (Round-1 blocking 3): the helper lets it propagate and the body re-raises it as
    ``StateInputError``.
    """
    working = _wrong_count_tree(tmp_path)
    draft = working / "manuscript" / wc.chapter_dir_name(1) / "draft.md"
    draft.write_bytes(b"\xff\xfe")
    monkeypatch.chdir(tmp_path)
    _refuses_leaving_file_intact(working)


def test_recount_legitimate_gate_breach_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A previously-coherent tree refuses once recounting breaches a gate.

    The hand-typed counts cross the 0.80 gate (so ``done_80=True`` is consistent
    and the pure-state checker passes), but the drafts on disk are empty, so
    recounting drops ``current`` to ``0`` and ``done_80=True`` now breaches
    ``gate-ratio-consistent``. This is correct validate-before-persist behaviour,
    not a bug (Risk "recount legitimately refuses"); the refusal must name the
    breached invariant.
    """
    spec = _drafting_spec(
        tuple(_chapter(number, 0, target_words=24000) for number in (1, 2, 3)),
        # Hand-typed counts cross 0.80 (68800/80000 = 0.86) so the checker passes.
        by_chapter_override={"01": 24000, "02": 24000, "03": 20800},
        current_words_override=68800,
        gates=(True, True, True),
    )
    working = wc.build_working_tree(spec, tmp_path)
    # Precondition: the hand-typed state passes the pure-state checker
    # ``novel-state check`` uses (``validate_state``), so the refusal is the
    # *recount* re-deriving the counts, not a pre-existing incoherence.
    prior = document_to_state(load_document(working / "state.toml"))
    assert not validate_state(prior), (
        "the hand-typed state must pass validate_state before recount"
    )
    monkeypatch.chdir(tmp_path)

    error = _refuses_leaving_file_intact(working)

    assert GATE_RATIO_CONSISTENT in str(error), (
        f"the refusal must name {GATE_RATIO_CONSISTENT!r}, got {error}"
    )


@st.composite
def _three_chapter_counts(draw: st.DrawFn) -> tuple[int, int, int]:
    """Draw a per-chapter word-count triple kept small to avoid crossing gates."""
    return (
        draw(st.integers(min_value=0, max_value=20)),
        draw(st.integers(min_value=0, max_value=20)),
        draw(st.integers(min_value=0, max_value=20)),
    )


# The tree is rebuilt and overwritten on every example, so the function-scoped
# ``tmp_path`` not resetting between generated inputs is harmless — each example
# reconstructs the subject before driving the body (mirroring
# ``test_state_mutators_unit.py``).
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(counts=_three_chapter_counts())
def test_recount_writes_coherent_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    counts: tuple[int, int, int],
) -> None:
    """``recount`` writes a state passing ``validate_state`` with ``sum == current``.

    Over generated per-chapter word counts against a fixed three-chapter manifest,
    the recounted state is always coherent and ``sum(by_chapter) == current``
    (accept-iff-coherent; design §5.2 invariant 3 holds by construction). The
    counts stay small so no knitting gate is crossed, keeping every recounted state
    coherent.
    """
    spec = _drafting_spec(
        tuple(starmap(_chapter, enumerate(counts, start=1))),
    )
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    outcome: CommandOutcome | None = None
    with contextlib.suppress(StateInputError):
        outcome = recount()

    assert outcome is not None, "small counts cross no gate, so recount must succeed"
    document = load_document(working / "state.toml")
    state = document_to_state(document)
    assert not validate_state(state), "the recounted state must be coherent"
    by_chapter = dict(document["word_counts"]["by_chapter"])
    assert sum(by_chapter.values()) == document["word_counts"]["current"]
    assert sum(by_chapter.values()) == sum(counts)
