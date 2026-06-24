"""Whole-corpus live-draft agreement tests for the §5.2 validator.

This is roadmap task 2.1.3's on-disk cross-check. The §5.2 validator
(:func:`~novel_ralph_skill.state.validate_state`) reads only the ``[word_counts]``
table for its two pure-state proxies — the ``gate-ratio-consistent`` numerator
``sum(by_chapter.values())`` and the ``consecutive-clean-within-drafted`` ceiling,
the count of ``by_chapter`` entries ``> 0``. The developers' guide names both as
proxies for a real disk quantity ("chapters drafted" and the drafted-words total)
and promises this task reconciles them "against a live draft count".

The live-draft oracle (``working_corpus.live_draft_owned``, exposed through the
``check_live_draft`` fixture) recomputes **both** live quantities from the on-disk
``draft.md`` bodies — the drafted-words total and the drafted-chapters count, both
independent of the ``[word_counts]`` table — and reconciles the ``[gates.knitting]``
booleans against the live drafted-words ratio and the ``[drafting.critic].
consecutive_clean`` counter against the live drafted-chapters count. Comparing the
table-reading validator with the draft-reading oracle on every corpus tree pins
that the two agree on quantities neither one derived from the table they both
validate, and the ``by_chapter_override`` variants that separate the table from
the drafts on either proxy — the two ``DIVERGENT_TABLE_VARIANTS`` members
``"by-chapter-override-over-counts-drafts"`` and
``"by-chapter-override-under-counts-drafts"`` — surface as disagreements driven
from corpus data.

Because the coherent and incoherent §1.3.2 corpus trees keep
``by_chapter_override`` unset, the table and the drafts agree numerically on every
one of them, so the whole-corpus agreement test alone cannot tell a live-draft
read from a table read — a table-based mutant of ``live_draft_counts`` passes it.
``test_live_draft_discriminates_table_from_drafts`` closes that gap by iterating
every ``DIVERGENT_TABLE_VARIANTS`` corpus tree (where the table belies the drafts)
through the ``divergent_table_tree`` factory fixture and asserting, against a
per-variant expected verdict, that the oracle reads the drafts and disagrees with
the table-reading validator. The table over-counts both proxies on one tree (the
live oracle fires both) and under-counts both on the other (the live oracle fires
only ``gate-ratio-consistent``); the under-counting tree exists to kill a
``min(live, table)``-style mutant of ``live_draft_counts`` that the over-counting
tree alone cannot catch. The trees are first-class corpus variants, no longer
constructed in this module.

Both verdicts are restricted to ``CORPUS_INVARIANT_NAMES``'s eight pure-state
(owned) names before comparison; a disk-evidence variant therefore yields two
empty owned sets that agree, and the parse-enforced ``phase-not-in-enum`` tree is
treated as the parser enforcing the oracle's owned label before the validator
runs. The corpus is consumed by fixture name only — never by a runtime value
import.
"""

from __future__ import annotations

import typing as typ

from _state_corpus_support import (
    DISK_EVIDENCE_NAMES,
    PARSE_ENFORCED_INVARIANTS,
    load_succeeds,
    validator_verdict,
)

from novel_ralph_skill.state import (
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    GATE_RATIO_CONSISTENT,
    PURE_STATE_INVARIANT_NAMES,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec

# The disk-evidence invariant names the validator never owns (a variant labelled
# with one of these yields two empty owned verdicts that agree) live in
# ``_state_corpus_support`` as ``DISK_EVIDENCE_NAMES``, shared with the corpus
# suite and derived from the production owned/complement split.

# Each divergent-table variant's verified live read and the owned verdict the
# live-draft oracle returns on it (the table-reading validator stays silent on
# every owned name for both). The over-counting tree makes the table over-state
# both proxy quantities, so the live oracle fires both proxies; the under-counting
# tree makes the table *under*-state them, and Decision Log D2 proves that on the
# under-counting tree only ``gate-ratio-consistent`` can fire on the live side
# (``consecutive-clean-within-drafted`` cannot, because the under-counted table
# chapter count is a smaller ceiling than the live count, never exceeded). The
# verdicts are asymmetric, so each key carries its own expectation rather than a
# single shared assertion.
_DIVERGENT_EXPECTATIONS: dict[str, tuple[tuple[int, int], frozenset[str]]] = {
    "by-chapter-override-over-counts-drafts": (
        (8000, 2),
        frozenset({GATE_RATIO_CONSISTENT, CONSECUTIVE_CLEAN_WITHIN_DRAFTED}),
    ),
    "by-chapter-override-under-counts-drafts": (
        (90000, 3),
        frozenset({GATE_RATIO_CONSISTENT}),
    ),
}


def test_live_draft_counts_equal_honest_draft_bases(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
    live_draft_counts: cabc.Callable[[Path], tuple[int, int]],
) -> None:
    """The live disk reads equal both honest-draft bases on every coherent tree.

    Pins the two live-count bases the cross-check reconciles against to the
    honest-draft bases the design names, so neither cross-check can silently
    change what number it reconciles: the live drafted-words total equals the
    oracle's invariant-7 numerator ``sum(chapter.draft_words)`` and the live
    drafted-chapters count equals the oracle's invariant-4c ceiling
    ``sum(1 for chapter in spec.chapters if chapter.draft_words > 0)``. This is
    the proof the live reads are genuinely live; the proxy-decoupling assertion
    below only proves they do not over-fire.
    """
    for spec, working_dir in coherent_oracle_cases:
        words_total, chapters_count = live_draft_counts(working_dir)
        expected_words = sum(chapter.draft_words for chapter in spec.chapters)
        expected_chapters = sum(
            1 for chapter in spec.chapters if chapter.draft_words > 0
        )
        assert words_total == expected_words
        assert chapters_count == expected_chapters


def test_live_draft_agreement_over_whole_corpus(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
    incoherent_variant_names: tuple[str, ...],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    check_live_draft: cabc.Callable[[WorkingTreeSpec, Path], set[str]],
) -> None:
    """The validator agrees with the live-draft oracle on every corpus tree.

    For every coherent tree, both the validator's owned verdict and the
    live-draft oracle's owned verdict are empty. For every incoherent variant:
    a parse-rejected tree (the ``phase-not-in-enum`` case) has the oracle's owned
    verdict as a non-empty subset of the parse-enforced set (the parser enforces
    the owned label before the validator runs; the oracle's ``tomllib`` reads
    tolerate the out-of-enum-phase tree, so the agreement is asserted only on the
    parse-enforced subset); otherwise the validator's owned verdict equals the
    live-draft oracle's owned verdict, and a variant whose label is an owned name
    yields exactly ``{expected}`` (the "rejected on its one named invariant"
    clause), while a variant whose label is a disk-evidence name yields two empty
    owned sets.
    """
    owned = set(PURE_STATE_INVARIANT_NAMES)
    for spec, working_dir in coherent_oracle_cases:
        assert validator_verdict(working_dir) & owned == set()
        assert check_live_draft(spec, working_dir) == set()
    for name in incoherent_variant_names:
        spec, working_dir, expected = incoherent_tree(name)
        oracle_owned = check_live_draft(spec, working_dir)
        if not load_succeeds(working_dir):
            assert oracle_owned, name
            assert oracle_owned <= PARSE_ENFORCED_INVARIANTS, name
            continue
        validator_owned = validator_verdict(working_dir) & owned
        assert validator_owned == oracle_owned, name
        if expected in owned:
            assert oracle_owned == {expected}, name
        else:
            assert expected in DISK_EVIDENCE_NAMES, name
            assert oracle_owned == set(), name


def test_live_draft_discriminates_table_from_drafts(
    divergent_table_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    divergent_table_variant_names: tuple[str, ...],
    live_draft_counts: cabc.Callable[[Path], tuple[int, int]],
    check_live_draft: cabc.Callable[[WorkingTreeSpec, Path], set[str]],
) -> None:
    """The live oracle reads the drafts, not the table, on every divergent tree.

    Every coherent and incoherent §1.3.2 corpus tree keeps
    ``[word_counts].by_chapter`` numerically equal to its on-disk drafts, so on
    those a live-draft read and a table read are indistinguishable and a
    table-based mutant of :func:`live_draft_counts` passes every other test in
    this module. The divergent-table trees this test exercises are first-class
    §1.3.2 corpus variants (``DIVERGENT_TABLE_VARIANTS``), sourced through the
    ``divergent_table_tree`` factory fixture rather than constructed in-module, so
    the discrimination is driven from corpus data through the standard fixture
    loop for *every* divergent variant.

    The two trees diverge in opposite directions, so each carries its own expected
    verdict in :data:`_DIVERGENT_EXPECTATIONS`. The over-counting tree drafts 8000
    words across two chapters against a table claiming 90000 words across three
    entries; its live read is ``(8000, 2)`` and the live oracle fires both proxies
    (the live 0.10 ratio contradicts the all-``True`` gates and
    ``consecutive_clean`` 3 exceeds the two live drafted chapters). The
    under-counting tree drafts 90000 words across three chapters against a table
    claiming 8000 words across two entries; its live read is ``(90000, 3)`` and the
    live oracle fires only ``gate-ratio-consistent`` (the live 1.125 ratio
    contradicts the all-``False`` gates, while ``consecutive_clean`` 2 stays within
    both the live and the table drafted-chapter counts — Decision Log D2).

    For each variant: assertion (a) — :func:`live_draft_counts` returns the
    **draft**-derived numbers, never the table-derived ones; assertion (b) — the
    live-draft oracle and the table-reading §5.2 validator **disagree** on the
    perturbed proxies, the validator naming none of them. A table-based read would
    collapse the oracle's verdict to the validator's, so the disagreement is
    exactly what proves the oracle is live. The under-counting tree is the variant
    that kills a ``min(live, table)``-style mutant of :func:`live_draft_counts`
    which "mishandles only over-counts" and survives the over-counting tree alone.
    """
    owned = set(PURE_STATE_INVARIANT_NAMES)
    for variant_name in divergent_table_variant_names:
        # A new, unpinned divergent variant must announce itself loudly rather
        # than silently skipping the discrimination assertion.
        assert variant_name in _DIVERGENT_EXPECTATIONS, variant_name
        expected_counts, expected_owned = _DIVERGENT_EXPECTATIONS[variant_name]
        spec, working_dir = divergent_table_tree(variant_name)
        assert live_draft_counts(working_dir) == expected_counts, variant_name
        oracle_owned = check_live_draft(spec, working_dir)
        validator_owned = validator_verdict(working_dir) & owned
        assert oracle_owned == set(expected_owned), variant_name
        assert validator_owned == set(), variant_name
        assert oracle_owned != validator_owned, variant_name


def test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    check_live_draft: cabc.Callable[[WorkingTreeSpec, Path], set[str]],
) -> None:
    """The table-only ``by-chapter-sum-mismatch`` fires neither live proxy.

    The load-bearing decoupling guard: the ``by-chapter-sum-mismatch`` variant
    forces ``current=1`` and leaves the drafts untouched, so on disk
    ``sum(by_chapter) != current`` (a genuine invariant-3 violation) while the
    live drafted-words ratio and the live drafted-chapters count are both
    unchanged. The live-draft oracle therefore names exactly ``{by-chapter-sum}``
    — not ``gate-ratio-consistent`` (the live ratio is unchanged) and not
    ``consecutive-clean-within-drafted`` (the live chapter count is unchanged) —
    matching the validator. Asserting both live proxies stay silent on a pure
    table mismatch proves they do not over-fire on it; the
    ``test_live_draft_counts_equal_honest_draft_bases`` self-test carries the
    liveness proof.
    """
    spec, working_dir, _expected = incoherent_tree("by-chapter-sum-mismatch")
    oracle_owned = check_live_draft(spec, working_dir)
    assert oracle_owned == {BY_CHAPTER_SUM}
    assert GATE_RATIO_CONSISTENT not in oracle_owned
    assert CONSECUTIVE_CLEAN_WITHIN_DRAFTED not in oracle_owned
    assert validator_verdict(working_dir) & set(PURE_STATE_INVARIANT_NAMES) == {
        BY_CHAPTER_SUM
    }
