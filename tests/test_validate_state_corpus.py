"""Corpus-oracle agreement and scope-boundary tests for the §5.2 validator.

This is the anti-drift guarantee roadmap task 2.1.3 extends to full on-disk
agreement. It asserts that :func:`~novel_ralph_skill.state.validate_state` keys
its verdict on the same invariant-name vocabulary as the §1.3.2 corpus oracle
(``CORPUS_INVARIANT_NAMES``), agrees with the oracle on every corpus tree once
both verdicts are restricted to the eight pure-state invariants this task owns,
and never emits any of the five disk-evidence names that task 2.3.2 owns.

The validator's name constants come from the production module
(:data:`~novel_ralph_skill.state.PURE_STATE_INVARIANT_NAMES`); the oracle's come
from the ``corpus_invariant_names`` fixture. The corpus is consumed by fixture
name only — never by a runtime value import — so the frozen corpus contract is
exercised, not duplicated.
"""

from __future__ import annotations

import typing as typ

import pytest
from _state_corpus_support import (
    DISK_EVIDENCE_NAMES,
    PARSE_ENFORCED_INVARIANTS,
    PARSE_ERRORS,
    load_succeeds,
    validator_verdict,
)

from novel_ralph_skill.commands.state_sourcing import STATE_INPUT_ERRORS
from novel_ralph_skill.state import (
    BY_CHAPTER_SUM,
    COMPLETED_PREFIX,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CURSOR_COHERENT,
    DISK_EVIDENCE_INVARIANT_NAMES,
    GATE_RATIO_CONSISTENT,
    GATE_THRESHOLDS,
    PHASE_IN_ENUM,
    PURE_STATE_INVARIANT_NAMES,
    load_state,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec

# The disk-evidence invariant names this task does NOT own (the validator must
# never emit any of them — the scope-boundary pin protecting task 2.3.2's
# surface) live in ``_state_corpus_support`` as ``DISK_EVIDENCE_NAMES``, shared
# with the live-draft suite and derived from the production owned/complement
# split. ``cursor-plan-present`` is the scene/beat-plan-presence sub-clause of
# design §5.2 invariant 6 — disk-evidence, so deferred to reconciliation task
# 2.3.2 like the four §5.4 names. ``word-counts-match-drafts`` is task 2.3.2's
# new disk-vs-table per-chapter word-count divergence (D-WORDCOUNT).


def test_owned_names_equal_corpus_vocabulary(
    corpus_invariant_names: tuple[str, ...],
) -> None:
    """The validator's eight owned constants equal the oracle's matching entries.

    Pins the shared vocabulary (developers-guide) so the validator and the corpus
    oracle cannot drift apart; the validator's constants are the production
    module's, the oracle's come by fixture.
    """
    owned = {
        PHASE_IN_ENUM,
        COMPLETED_PREFIX,
        BY_CHAPTER_SUM,
        CONSECUTIVE_CLEAN_WITHIN_TARGET,
        CONVERGENCE_TARGET_AT_LEAST_ONE,
        CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
        CURSOR_COHERENT,
        GATE_RATIO_CONSISTENT,
    }
    assert owned == set(corpus_invariant_names) - DISK_EVIDENCE_NAMES
    assert set(PURE_STATE_INVARIANT_NAMES) == owned
    # Task 2.3.2's disk-evidence detector owns exactly the six deferred names; pin
    # the production ``DISK_EVIDENCE_INVARIANT_NAMES`` tuple equal to the oracle's
    # disk-evidence subset so the two vocabularies cannot drift (D-NAMES).
    assert set(DISK_EVIDENCE_INVARIANT_NAMES) == DISK_EVIDENCE_NAMES
    assert set(DISK_EVIDENCE_INVARIANT_NAMES) == set(corpus_invariant_names) - owned


def test_corpus_gate_thresholds_equal_production(
    corpus_gate_thresholds: tuple[float, float, float],
) -> None:
    """The corpus's gate-threshold triple equals the production validator's.

    Pins the corpus's independent ``0.30 / 0.50 / 0.80`` copy to the §5.2 source
    of truth (mirroring :func:`test_owned_names_equal_corpus_vocabulary`) so the
    oracle's cross-check cannot silently drift from the validator (audit:2.1.2
    finding 1). The corpus keeps its own copy on purpose; this test keeps it
    honest.
    """
    assert corpus_gate_thresholds == GATE_THRESHOLDS


def test_parse_errors_subset_of_production_state_input_errors() -> None:
    """Pin this suite's parse-fault set as a subset of the production vocabulary.

    Pins the "what counts as a state-input error" vocabulary to one home: the
    shared ``PARSE_ERRORS`` (the on-disk parse faults, minus ``OSError``) must
    be a subset of the production ``STATE_INPUT_ERRORS`` so the test cannot drift
    from the exit-``3`` channel ``novel-state check`` actually translates
    (audit:2.1.2 finding 4).
    """
    assert set(PARSE_ERRORS) <= set(STATE_INPUT_ERRORS)


def test_coherent_trees_pass_the_validator(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
) -> None:
    """Every coherent corpus tree has an empty pure-state verdict."""
    for _spec, working_dir in coherent_oracle_cases:
        assert validator_verdict(working_dir) == set()


def test_incoherent_agreement_restricted_to_owned(
    incoherent_variant_names: tuple[str, ...],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
) -> None:
    """The validator agrees with the oracle on every variant, restricted to owned.

    Intersecting both the oracle's verdict and the validator's verdict with
    :data:`PURE_STATE_INVARIANT_NAMES` yields equal sets on every variant (strict;
    B1 makes this hold). For a variant whose label is a disk-evidence invariant,
    both restricted sets are empty (the validator correctly stays silent).
    """
    owned = set(PURE_STATE_INVARIANT_NAMES)
    for name in incoherent_variant_names:
        spec, working_dir, _expected = incoherent_tree(name)
        oracle_owned = set(check_corpus(spec, working_dir)) & owned
        if not load_succeeds(working_dir):
            # A parse-rejected tree: the parser enforces the owned invariant the
            # oracle labels before the validator runs, so the oracle's owned labels
            # must be a non-empty subset of the parse-enforced set.
            assert oracle_owned <= PARSE_ENFORCED_INVARIANTS, name
            assert oracle_owned, name
            continue
        validator_owned = validator_verdict(working_dir) & owned
        assert validator_owned == oracle_owned, name


def test_by_chapter_sum_variant_names_only_by_chapter_sum(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """The ``by-chapter-sum-mismatch`` variant names exactly ``by-chapter-sum``.

    The load-bearing B1 case: corrupting ``current`` must not also trip
    ``gate-ratio-consistent`` (the gate numerator is the drafted total, not
    ``current``), proving invariant 7 is decoupled from invariant 3.
    """
    _spec, working_dir, _expected = incoherent_tree("by-chapter-sum-mismatch")
    assert validator_verdict(working_dir) == {BY_CHAPTER_SUM}


def test_phase_in_enum_is_parser_enforced(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """The ``phase-not-in-enum`` tree is rejected by the parser, not the validator.

    ``phase-in-enum`` is enforced one layer earlier than ``validate_state``:
    ``parse_state`` raises ``ValueError`` constructing ``Phase(current)`` on an
    out-of-enum phase, so ``load_state`` rejects the tree (the production exit-``3``
    state-error channel) before the validator runs. This pins the boundary so the
    agreement suite's parse-rejection branch is exercised deliberately.
    """
    _spec, working_dir, expected = incoherent_tree("phase-not-in-enum")
    assert expected == PHASE_IN_ENUM
    assert not load_succeeds(working_dir)
    with pytest.raises(ValueError, match="not a valid Phase"):
        load_state(working_dir / "state.toml")


@pytest.mark.parametrize("kind", ["coherent", "incoherent"])
def test_validator_never_emits_deferred_names(
    kind: str,
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
    incoherent_variant_names: tuple[str, ...],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """The validator emits none of the four disk-evidence names on any tree.

    The scope-boundary pin: a future reader cannot mistake a deferred invariant
    for a missing one, and task 2.3.2's surface is protected.
    """
    if kind == "coherent":
        working_dirs = [working_dir for _spec, working_dir in coherent_oracle_cases]
    else:
        working_dirs = [incoherent_tree(name)[1] for name in incoherent_variant_names]
    for working_dir in working_dirs:
        # Skip parse-rejected trees: the validator never runs on them (the
        # exit-3 state-error channel), so it emits nothing — deferred or owned.
        if not load_succeeds(working_dir):
            continue
        assert validator_verdict(working_dir) & DISK_EVIDENCE_NAMES == set()
