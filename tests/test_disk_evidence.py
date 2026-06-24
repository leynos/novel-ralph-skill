"""Unit, vocabulary, and twin-equality tests for the §5.4 disk-evidence detector.

These pin :func:`novel_ralph_skill.state.check_disk_evidence` (roadmap task
2.3.2) as the §5.4 twin of the pure-state validator:

- each disk-evidence predicate fires on its matching ``INCOHERENT_VARIANTS`` tree
  and is silent on the coherent baseline and the phase/``done.flag`` permutations;
- the six owned name constants equal the corpus oracle's disk-evidence subset
  (the shared-vocabulary pin, mirroring ``test_owned_names_equal_corpus_vocabulary``);
- the production ``compiled.md`` join helper equals the corpus
  ``concatenate_drafts`` byte-for-byte (the deliberate-twin pin);
- the production ``word-counts-match-drafts`` per-chapter verdict equals the new
  disk-reading corpus oracle on every corpus tree, including **both** word-count
  variants (the over-count divergent table and the §5.4 under-count case).

The corpus is consumed by fixture name where a fixture exists; the spec library
and the oracle's name vocabulary are taken by the sanctioned value import
``working_corpus as wc`` the other corpus suites use, so each test stays within
the argument-count gate.
"""

from __future__ import annotations

import typing as typ

import pytest
import working_corpus as wc
from _state_corpus_support import load_succeeds

from novel_ralph_skill.state import (
    COMPILED_MATCHES_DRAFTS,
    CURSOR_PLAN_PRESENT,
    DISK_EVIDENCE_INVARIANT_NAMES,
    DONE_FLAG_WITHOUT_DRAFT,
    MANIFEST_DISK_BIJECTION,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_MATCH_DRAFTS,
    check_disk_evidence,
    concatenate_drafts,
    load_state,
)
from novel_ralph_skill.state.disk_evidence import _check_word_counts_match_drafts

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec

# The disk-evidence subset of the corpus vocabulary, the names this detector owns.
_DISK_EVIDENCE_NAMES: frozenset[str] = frozenset(DISK_EVIDENCE_INVARIANT_NAMES)


def _disk_verdict(working_dir: Path) -> set[str]:
    """Return the disk-evidence invariant names the detector reports for a tree."""
    state = load_state(working_dir / "state.toml")
    return {
        violation.invariant for violation in check_disk_evidence(state, working_dir)
    }


def test_owned_disk_evidence_names_equal_corpus_subset(
    corpus_invariant_names: tuple[str, ...],
) -> None:
    """The six owned constants equal the oracle's disk-evidence name subset.

    The pure-state names (``validate_state``'s) are the complement; the six
    disk-evidence names are exactly what remains, so the production detector and
    the corpus oracle key on one vocabulary (D-NAMES).
    """
    pure_state = {
        "phase-in-enum",
        "completed-prefix",
        "by-chapter-sum",
        "consecutive-clean-within-target",
        "convergence-target-at-least-one",
        "consecutive-clean-within-drafted",
        "cursor-coherent",
        "gate-ratio-consistent",
    }
    expected = set(corpus_invariant_names) - pure_state
    assert expected == _DISK_EVIDENCE_NAMES, (
        "the detector's owned names must equal the oracle's disk-evidence subset"
    )
    assert set(DISK_EVIDENCE_INVARIANT_NAMES) == _DISK_EVIDENCE_NAMES, (
        "the ordered tuple and the owned set must carry the same names"
    )


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("manifest-extra-entry", MANIFEST_DISK_BIJECTION),
        ("draft-without-manifest-entry", MANIFEST_DISK_BIJECTION),
        ("done-flag-empty-draft", DONE_FLAG_WITHOUT_DRAFT),
        ("done-flag-absent-draft", DONE_FLAG_WITHOUT_DRAFT),
        ("compiled-not-concatenation-of-drafts", COMPILED_MATCHES_DRAFTS),
        ("uncleared-pending-turn", PENDING_TURN_CLEARED),
        ("scene-cursor-without-plan", CURSOR_PLAN_PRESENT),
        ("beat-cursor-without-plan", CURSOR_PLAN_PRESENT),
        ("done-flag-real-draft-undercount", WORD_COUNTS_MATCH_DRAFTS),
    ],
)
def test_predicate_fires_on_its_variant(
    variant: str,
    expected: str,
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """Each disk-evidence variant's sole detector violation is its named one."""
    _spec, working_dir, _label = incoherent_tree(variant)
    assert _disk_verdict(working_dir) == {expected}, variant


def test_detector_silent_on_coherent_trees(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
) -> None:
    """Every coherent corpus tree has an empty disk-evidence verdict."""
    for _spec, working_dir in coherent_oracle_cases:
        assert _disk_verdict(working_dir) == set(), working_dir


def test_detector_silent_on_done_flag_permutations(
    done_flag_permutation_names: tuple[str, ...],
    done_flag_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
) -> None:
    """A coherent ``done.flag`` permutation never trips a disk-evidence invariant."""
    for name in done_flag_permutation_names:
        _spec, working_dir = done_flag_tree(name)
        assert _disk_verdict(working_dir) == set(), name


def test_compiled_join_helper_equals_corpus(
    concatenate: cabc.Callable[[cabc.Sequence[str]], str],
) -> None:
    """The production concatenation equals the corpus helper byte-for-byte.

    The deliberate-twin pin (developers' guide): production
    :func:`concatenate_drafts` and the corpus ``concatenate_drafts`` must agree on
    every input so the ``compiled-matches-drafts`` verdict is computed identically
    on both sides (D-COMPILE).
    """
    cases: list[list[str]] = [
        [],
        ["only one body"],
        ["first body", "second body", "third body"],
        ["", "non-empty", ""],
    ]
    for drafts in cases:
        assert concatenate_drafts(drafts) == concatenate(drafts), drafts


def test_word_counts_twin_equals_corpus_oracle(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
    incoherent_variant_names: tuple[str, ...],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
) -> None:
    """The production word-count predicate equals the disk-reading corpus oracle.

    Both sides read disk (the production predicate via ``recount_words``, the
    oracle via the draft glob-and-split), so the test compares like with like on
    every corpus tree — the coherent set and every ``INCOHERENT_VARIANTS`` member,
    including both word-count variants (round-3 blocking point 1, round-4 B2).
    """
    cases: list[tuple[WorkingTreeSpec, Path]] = list(coherent_oracle_cases)
    for name in incoherent_variant_names:
        spec, working_dir, _label = incoherent_tree(name)
        cases.append((spec, working_dir))
    for spec, working_dir in cases:
        # A parse-rejected tree (the ``phase-not-in-enum`` variant) never reaches
        # the detector in production, so skip it exactly as the validator suites do.
        if not load_succeeds(working_dir):
            continue
        state = load_state(working_dir / "state.toml")
        production_fires = (
            _check_word_counts_match_drafts(state, working_dir) is not None
        )
        oracle_fires = WORD_COUNTS_MATCH_DRAFTS in wc.corpus_check(spec, working_dir)
        assert production_fires == oracle_fires, working_dir
