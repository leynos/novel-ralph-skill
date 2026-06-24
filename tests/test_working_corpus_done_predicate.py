"""Corpus tests for the ``novel-done`` predicate specs and their oracle twins.

These pin roadmap task 3.1.1's Work item 2: the builder writes
``reviews/knitting-NN.md`` and ``critic-notes.md`` exactly as specified and adds
no other files (R-CHURN guard); the all-hold spec materialises every artefact the
six clauses need and drives them all true; the two oracle twins (D-TWIN) agree
with the production predicate on every ``novel-done`` corpus tree; and the
existing ``PHASE_STATES``/``COHERENT_BASELINE`` trees still materialise without a
``reviews/`` directory or any ``critic-notes.md`` (the byte-identity guard).

The corpus is consumed entirely by fixture (the all-hold/failer/edge tree
factories and the two oracle twins), so no runtime value import of the corpus
package is needed (the developers-guide "Shared test scaffolding" rule).
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state import load_state
from novel_ralph_skill.state.done_predicate import (
    DoneClauses,
    evaluate_done,
    knitting_gates_passed,
    no_unresolved_blockers,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from working_corpus import WorkingTreeSpec

# The relative paths the two new artefacts occupy under a ``working/`` tree, used
# by the byte-identity guard to assert the existing specs introduce neither.
_NEW_ARTEFACT_GLOBS: tuple[str, ...] = (
    "reviews",
    "manuscript/chapter-*/critic-notes.md",
)


def _evaluate(working: Path) -> DoneClauses:
    """Return the ``evaluate_done`` verdict over a materialised tree."""
    return evaluate_done(load_state(working / "state.toml"), working)


def test_all_hold_tree_materialises_every_clause(
    all_hold_tree: cabc.Callable[[], Path],
) -> None:
    """The all-hold tree writes every artefact the six clauses need; all hold."""
    working = all_hold_tree()
    # Each new artefact is on disk exactly as the spec declares.
    reviews = working / "reviews"
    assert {p.name for p in reviews.glob("knitting-*.md")} == {
        "knitting-30.md",
        "knitting-50.md",
        "knitting-80.md",
    }
    # The clean (absent) critic notes case: no chapter carries a notes file.
    assert not list((working / "manuscript").glob("chapter-*/critic-notes.md"))
    clauses = _evaluate(working)
    assert clauses.all_hold is True


def test_failers_each_break_exactly_one_clause(
    done_predicate_failer_names: tuple[str, ...],
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
) -> None:
    """Each named failer drives its mapped clause false and exactly one clause."""
    # The failer key maps to the clause it breaks, except the two
    # knitting_gates_passed halves which both fail that one clause.
    clause_for = {
        "knitting_review_missing": "knitting_gates_passed",
        "knitting_gate_false": "knitting_gates_passed",
    }
    for name in done_predicate_failer_names:
        _spec, working = done_predicate_failer_tree(name)
        clauses = _evaluate(working)
        expected = clause_for.get(name, name)
        assert clauses.failed_clause_names == (expected,), (
            f"failer {name!r} should break only {expected!r}, "
            f"got {clauses.failed_clause_names}"
        )


def test_blocker_edges(
    blocker_edge_trees: cabc.Callable[[], tuple[Path, Path]],
) -> None:
    """A ``[resolved]`` BLOCKER holds; a near-miss prose mention does not."""
    resolved, near_miss = blocker_edge_trees()
    assert _evaluate(resolved).all_hold is True
    near = _evaluate(near_miss)
    assert near.failed_clause_names == ("no_unresolved_blockers",)


def test_reviews_oracle_twin_agrees(
    all_hold_tree: cabc.Callable[[], Path],
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    oracle_reviews_present: cabc.Callable[[Path], bool],
) -> None:
    """The review-existence twin agrees with the production review half (D-TWIN).

    The clause also reads the gate booleans, so the twin is pinned to the
    review-presence factor only: it equals ``knitting_gates_passed`` exactly when
    every gate boolean is true (the all-hold tree), and tracks the review
    presence on the review-missing failer.
    """
    working = all_hold_tree()
    state = load_state(working / "state.toml")
    assert oracle_reviews_present(working) is True
    assert knitting_gates_passed(state, working) is True

    _spec, missing = done_predicate_failer_tree("knitting_review_missing")
    missing_state = load_state(missing / "state.toml")
    assert oracle_reviews_present(missing) is False
    assert knitting_gates_passed(missing_state, missing) is False


def test_blocker_oracle_twin_agrees(
    all_hold_tree: cabc.Callable[[], Path],
    done_predicate_failer_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    blocker_edge_trees: cabc.Callable[[], tuple[Path, Path]],
    oracle_no_blockers: cabc.Callable[[Path], bool],
) -> None:
    """The BLOCKER-scan twin equals the production clause on every tree (D-TWIN)."""
    cases: list[Path] = [all_hold_tree()]
    _spec, blocking = done_predicate_failer_tree("no_unresolved_blockers")
    cases.append(blocking)
    cases.extend(blocker_edge_trees())
    for working in cases:
        state = load_state(working / "state.toml")
        assert oracle_no_blockers(working) == no_unresolved_blockers(state, working)


def test_existing_specs_have_no_new_artefacts(
    phase_names: tuple[str, ...],
    phase_state_tree: cabc.Callable[[str], Path],
    baseline_tree: cabc.Callable[[], Path],
) -> None:
    """No ``PHASE_STATES``/baseline tree gains a ``reviews/`` or ``critic-notes.md``.

    The R-CHURN / byte-identity guard: Work item 2 added the two artefacts only
    via new opt-in fields defaulting off, so every pre-existing spec materialises
    exactly as before — no ``reviews/`` directory and no ``critic-notes.md``.
    """
    trees = [baseline_tree(), *(phase_state_tree(name) for name in phase_names)]
    for working in trees:
        for glob in _NEW_ARTEFACT_GLOBS:
            assert not list(working.glob(glob)), (
                f"existing tree {working} unexpectedly carries {glob}"
            )
