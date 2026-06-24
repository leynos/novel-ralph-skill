"""Unit and property tests for the pure ``novel-done`` predicate engine.

These pin :mod:`novel_ralph_skill.state.done_predicate` (roadmap task 3.1.1):
each clause is driven independently true and false over hand-built ``tmp_path``
trees, :class:`~novel_ralph_skill.state.done_predicate.DoneClauses` is shown to
be the six-way conjunction with a design-ordered failure list, and a Hypothesis
property pins ``all_hold == all(...)`` and the ``failed_clause_names`` ordering
over the boolean cross-product (``python-verification``: an invariant over the
boolean cross-product is Hypothesis's adversary, not CrossHair's or mutmut's).

The disk-aware clauses read a real ``State`` parsed from a materialised corpus
tree (``load_state``), so the predicate sees exactly the shape production does;
the state-only clauses craft a ``State`` from that base with
:func:`dataclasses.replace` so a single field flips without rebuilding the whole
dataclass tree.
"""

from __future__ import annotations

import dataclasses
import tempfile
import typing as typ
from pathlib import Path

import pytest
import working_corpus as wc
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state import Phase, load_state
from novel_ralph_skill.state.compile_model import (
    concatenate_drafts,
    present_draft_bodies,
)
from novel_ralph_skill.state.done_predicate import (
    DoneClauses,
    all_chapters_flagged,
    compile_consistent,
    evaluate_done,
    final_pass_complete,
    knitting_gates_passed,
    phase_is_done,
)

if typ.TYPE_CHECKING:
    from novel_ralph_skill.state.schema import State

_CLAUSE_FIELDS: tuple[str, ...] = tuple(
    field.name for field in dataclasses.fields(DoneClauses)
)


def _all_hold_tree(tmp_path: Path) -> tuple[State, Path]:
    """Build an all-six-clauses-hold tree and return its parsed state and path.

    Work item 1 owns no corpus spec for ``reviews/`` or ``critic-notes.md`` yet
    (Work item 2 adds them), so it starts from the coherent ``done`` phase state
    — which already flags every chapter, sets every gate, and writes a present
    ``compiled.md`` — and writes the three ``reviews/knitting-NN.md`` files
    directly so the disk-aware clauses all hold.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["done"], tmp_path)
    _write_reviews(working, (30, 50, 80))
    return load_state(working / "state.toml"), working


def _write_reviews(working: Path, percentages: tuple[int, ...]) -> None:
    """Write ``reviews/knitting-NN.md`` for each named percentage under ``working``."""
    reviews = working / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    for percentage in percentages:
        (reviews / f"knitting-{percentage}.md").write_text(
            f"# Knitting {percentage}\n", encoding="utf-8"
        )


# --- state-only clauses ------------------------------------------------------


def test_phase_is_done_true_and_false(tmp_path: Path) -> None:
    """``phase_is_done`` holds iff ``phase.current`` is the terminal phase."""
    state, _ = _all_hold_tree(tmp_path)
    assert phase_is_done(state) is True
    not_done = dataclasses.replace(
        state, phase=dataclasses.replace(state.phase, current=Phase.FINAL_PASS)
    )
    assert phase_is_done(not_done) is False


def test_final_pass_complete_true_and_false(tmp_path: Path) -> None:
    """``final_pass_complete`` mirrors the ``[gates.final]`` flag."""
    state, _ = _all_hold_tree(tmp_path)
    assert final_pass_complete(state) is True
    incomplete = dataclasses.replace(
        state,
        gates=dataclasses.replace(
            state.gates,
            final=dataclasses.replace(state.gates.final, final_pass_complete=False),
        ),
    )
    assert final_pass_complete(incomplete) is False


# --- disk-aware clauses ------------------------------------------------------


def test_all_chapters_flagged_true_and_false(tmp_path: Path) -> None:
    """``all_chapters_flagged`` holds iff every manifest chapter has a done.flag."""
    state, working = _all_hold_tree(tmp_path)
    assert all_chapters_flagged(state, working) is True
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "done.flag").unlink()
    assert all_chapters_flagged(state, working) is False


def test_knitting_gates_passed_true_and_false(tmp_path: Path) -> None:
    """``knitting_gates_passed`` needs both the gate booleans and the reviews."""
    state, working = _all_hold_tree(tmp_path)
    assert knitting_gates_passed(state, working) is True
    # Removing a review file alone fails the clause even with all gates true.
    (working / "reviews" / "knitting-50.md").unlink()
    assert knitting_gates_passed(state, working) is False


def test_knitting_gates_passed_false_when_gate_boolean_false(tmp_path: Path) -> None:
    """A false gate boolean fails the clause even with all three reviews present."""
    state, working = _all_hold_tree(tmp_path)
    one_gate_off = dataclasses.replace(
        state,
        gates=dataclasses.replace(
            state.gates,
            knitting=dataclasses.replace(state.gates.knitting, done_50=False),
        ),
    )
    assert knitting_gates_passed(one_gate_off, working) is False


def _expected_compiled(state: State, working: Path) -> str:
    """Return the byte-coherent ``compiled.md`` for the materialised tree."""
    return concatenate_drafts(present_draft_bodies(state, working))


def test_compile_consistent_present_coherent_and_absent(tmp_path: Path) -> None:
    """``compile_consistent`` is True for a coherent compile, False when absent.

    The all-hold tree writes the hash-equal concatenation, so the clause holds;
    removing ``compiled.md`` makes it false (an absent compile is never "done",
    preserving the 3.1.1 B1 soundness fix; R-EXISTENCE-REGRESS).
    """
    state, working = _all_hold_tree(tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == _expected_compiled(state, working)
    assert compile_consistent(state, working) is True
    compiled.unlink()
    assert compile_consistent(state, working) is False


def test_compile_consistent_false_when_present_but_stale(tmp_path: Path) -> None:
    """A present-but-divergent ``compiled.md`` is caught (R-STALE closed).

    This is the visible behaviour change from 3.1.1's existence-only clause: a
    present compile that no longer matches the drafts is now ``False`` where the
    old clause returned ``True``.
    """
    state, working = _all_hold_tree(tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    compiled.write_text("stale content diverging from drafts", encoding="utf-8")
    assert compile_consistent(state, working) is False


def test_compile_consistent_false_when_count_coincident(tmp_path: Path) -> None:
    """A stale compile with the same token and header count is still divergent.

    The predicate-truthfulness property (R-STALE-MISS): a body whose
    whitespace-split token count *and* header count match the drafts but whose
    non-whitespace bytes differ must still report divergence, because the clause
    compares bytes, not counts.
    """
    state, working = _all_hold_tree(tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    coherent = _expected_compiled(state, working)
    # Swap one "word" token for an equal-length, header-count-preserving token,
    # keeping the whitespace-split count identical while diverging by bytes.
    stale = coherent.replace("word", "wxrd", 1)
    assert stale != coherent
    assert len(stale.split()) == len(coherent.split())
    assert stale.count("\n#") == coherent.count("\n#")
    compiled.write_text(stale, encoding="utf-8")
    assert compile_consistent(state, working) is False


def test_compile_consistent_undecodable_propagates(tmp_path: Path) -> None:
    """An undecodable ``compiled.md`` propagates for the command layer (exit 3)."""
    state, working = _all_hold_tree(tmp_path)
    (working / "manuscript" / "compiled.md").write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(UnicodeDecodeError):
        compile_consistent(state, working)


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.integers(min_value=0, max_value=64), st.integers(min_value=33, max_value=126))
def test_compile_consistent_byte_perturbation_property(
    position: int, replacement: int
) -> None:
    """Any non-whitespace byte change falsifies the clause; the exact match holds.

    Hypothesis is the right adversary here (``python-verification``): an invariant
    over a range of single-byte perturbations of the coherent concatenation. The
    tree is rebuilt under a fresh temporary directory per example because a
    Hypothesis property body cannot take the function-scoped ``tmp_path`` fixture.

    ``deadline=None`` and a bounded ``max_examples`` are required because each
    example materialises a full corpus working tree and parses ``state.toml`` via
    ``_all_hold_tree``, so per-example runtime exceeds Hypothesis's default 200ms
    deadline under xdist contention — matching the convention used by the other
    filesystem-heavy property tests in this suite.
    """
    with tempfile.TemporaryDirectory() as raw:
        state, working = _all_hold_tree(Path(raw))
        compiled = working / "manuscript" / "compiled.md"
        coherent = compiled.read_text(encoding="utf-8")
        assert compile_consistent(state, working) is True
        if not coherent or position >= len(coherent):
            return
        char = coherent[position]
        if char.isspace():
            return
        perturbed = coherent[:position] + chr(replacement) + coherent[position + 1 :]
        if perturbed == coherent:
            return
        compiled.write_text(perturbed, encoding="utf-8")
        assert compile_consistent(state, working) is False


# --- aggregate and result shape ----------------------------------------------


def test_evaluate_done_all_hold(tmp_path: Path) -> None:
    """``evaluate_done`` reports every clause true on the all-hold tree."""
    state, working = _all_hold_tree(tmp_path)
    clauses = evaluate_done(state, working)
    assert clauses.all_hold is True
    assert not clauses.failed_clause_names


def test_evaluate_done_single_clause_fails(tmp_path: Path) -> None:
    """Toggling one artefact false leaves exactly that clause unmet."""
    state, working = _all_hold_tree(tmp_path)
    (working / "manuscript" / "compiled.md").unlink()
    clauses = evaluate_done(state, working)
    assert clauses.all_hold is False
    assert clauses.failed_clause_names == ("compile_consistent",)


def test_as_result_is_design_ordered(tmp_path: Path) -> None:
    """``as_result`` emits the six clause keys in design §4.2 order."""
    state, working = _all_hold_tree(tmp_path)
    result = evaluate_done(state, working).as_result()
    assert tuple(result) == _CLAUSE_FIELDS
    assert all(value is True for value in result.values())


# --- property: the conjunction and the failure ordering ----------------------


@given(st.lists(st.booleans(), min_size=6, max_size=6))
def test_all_hold_and_failures_match_booleans(values: list[bool]) -> None:
    """``all_hold`` is the conjunction and ``failed_clause_names`` lists the falses.

    Over every point in the boolean cross-product, ``all_hold`` equals
    ``all(values)`` and ``failed_clause_names`` is exactly the field names whose
    value is ``False``, in design order.
    """
    clauses = DoneClauses(**dict(zip(_CLAUSE_FIELDS, values, strict=True)))
    assert clauses.all_hold == all(values)
    expected = tuple(
        name for name, value in zip(_CLAUSE_FIELDS, values, strict=True) if not value
    )
    assert clauses.failed_clause_names == expected
