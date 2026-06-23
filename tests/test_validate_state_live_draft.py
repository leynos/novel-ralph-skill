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
validate, so a future ``by_chapter_override`` variant that separated the table
from the drafts on either proxy would surface as a disagreement to investigate.

Because no §1.3.2 corpus tree sets ``by_chapter_override``, the table and the
drafts agree numerically on every corpus tree, so the whole-corpus agreement test
alone cannot tell a live-draft read from a table read — a table-based mutant of
``live_draft_counts`` passes it. ``test_live_draft_discriminates_table_from_drafts``
closes that gap by constructing the one tree where the table belies the drafts and
asserting the oracle reads the drafts and disagrees with the table-reading
validator on both proxies.

Both verdicts are restricted to ``CORPUS_INVARIANT_NAMES``'s eight pure-state
(owned) names before comparison; a disk-evidence variant therefore yields two
empty owned sets that agree, and the parse-enforced ``phase-not-in-enum`` tree is
treated as the parser enforcing the oracle's owned label before the validator
runs. The corpus is consumed by fixture name only — never by a runtime value
import.
"""

from __future__ import annotations

import typing as typ

import pytest
from _state_corpus_support import (
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

    from conftest import ChapterSpec, WorkingTreeSpec

# The five disk-evidence invariant names the validator never owns; a variant
# labelled with one of these yields two empty owned verdicts that agree.
_DISK_EVIDENCE_NAMES: frozenset[str] = frozenset(
    {
        "manifest-disk-bijection",
        "done-flag-without-draft",
        "compiled-matches-drafts",
        "pending-turn-cleared",
        "cursor-plan-present",
    },
)


@pytest.fixture
def corpus_builders(
    make_chapter_spec: cabc.Callable[..., ChapterSpec],
    make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
    build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
) -> tuple[
    cabc.Callable[..., ChapterSpec],
    cabc.Callable[..., WorkingTreeSpec],
    cabc.Callable[[WorkingTreeSpec, Path], Path],
]:
    """Return the chapter/tree constructors and the builder as one bundle.

    Bundling the three corpus constructor and builder callables keeps the
    :func:`divergent_table_tree` fixture's parameter list within the project's
    argument-count gate while still delivering each by fixture name (mirroring the
    ``compile_probe`` bundling fixture in ``corpus_fixtures``).
    """
    return make_chapter_spec, make_working_tree_spec, build_tree


@pytest.fixture
def divergent_table_tree(
    tmp_path: Path,
    corpus_builders: tuple[
        cabc.Callable[..., ChapterSpec],
        cabc.Callable[..., WorkingTreeSpec],
        cabc.Callable[[WorkingTreeSpec, Path], Path],
    ],
    phase_names: tuple[str, ...],
) -> tuple[WorkingTreeSpec, Path]:
    """Return a tree whose ``[word_counts].by_chapter`` table belies its drafts.

    No tree in the §1.3.2 corpus sets ``by_chapter_override``, so on every corpus
    tree the on-disk drafts and the ``[word_counts]`` table agree and a live-draft
    read is numerically indistinguishable from a table read. This fixture builds
    the one tree that separates them, so a test can prove the live-draft oracle is
    genuinely live: a table read would return different numbers and a different
    verdict.

    The tree drafts two chapters of 4000 words each (live: 8000 words, two drafted
    chapters) against an 80000 target, but overrides ``by_chapter`` to three
    entries of 30000 (table: 90000 words, three entries ``> 0``) with ``current``
    set to the table sum so ``by-chapter-sum`` stays silent. All three knitting
    gates are ``True`` and ``consecutive_clean`` is 3 with a matching
    ``convergence_target``. Under the live read the gates contradict the 0.10 ratio
    and the counter exceeds the two drafted chapters, so the live oracle names both
    proxy invariants; the table-reading §5.2 validator, seeing a 1.125 ratio and
    three drafted entries, names neither. The two therefore disagree on both
    proxies — the discrimination a same-numbers corpus tree cannot provide. The
    tree is built through the corpus constructor and builder fixtures, so the
    corpus is still consumed by fixture name and never by a runtime value import.
    """
    make_chapter_spec, make_working_tree_spec, build_tree = corpus_builders
    completed = phase_names[: phase_names.index("drafting")]
    spec = make_working_tree_spec(
        phase_current="drafting",
        phase_completed=completed,
        chapters=(
            make_chapter_spec(
                number=1,
                slug="chapter-01",
                title="Chapter 1",
                target_words=40000,
                draft_words=4000,
                has_done_flag=False,
            ),
            make_chapter_spec(
                number=2,
                slug="chapter-02",
                title="Chapter 2",
                target_words=40000,
                draft_words=4000,
                has_done_flag=False,
            ),
        ),
        target_words=80000,
        consecutive_clean=3,
        convergence_target=3,
        by_chapter_override={"01": 30000, "02": 30000, "03": 30000},
        current_words_override=90000,
        done_30=True,
        done_50=True,
        done_80=True,
        current_chapter=2,
    )
    return spec, build_tree(spec, tmp_path)


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
            assert expected in _DISK_EVIDENCE_NAMES, name
            assert oracle_owned == set(), name


def test_live_draft_discriminates_table_from_drafts(
    divergent_table_tree: tuple[WorkingTreeSpec, Path],
    live_draft_counts: cabc.Callable[[Path], tuple[int, int]],
    check_live_draft: cabc.Callable[[WorkingTreeSpec, Path], set[str]],
) -> None:
    """The live oracle reads the drafts, not the table, when the two diverge.

    Every §1.3.2 corpus tree keeps ``[word_counts].by_chapter`` numerically equal
    to its on-disk drafts (no variant sets ``by_chapter_override``), so on the
    corpus a live-draft read and a table read are indistinguishable and a
    table-based mutant of :func:`live_draft_counts` passes every other test in
    this module. This test builds the one tree that separates them — drafts of
    8000 words across two chapters against a table claiming 90000 words across
    three entries — and pins the discrimination directly.

    Assertion (a): :func:`live_draft_counts` returns the **draft**-derived numbers
    ``(8000, 2)``, never the table-derived ``(90000, 3)``. Assertion (b): the
    live-draft oracle and the table-reading §5.2 validator **disagree** on both
    perturbed proxies — the live oracle names ``gate-ratio-consistent`` (the live
    0.10 ratio contradicts the all-``True`` gates) and
    ``consecutive-clean-within-drafted`` (``consecutive_clean`` 3 exceeds the two
    live drafted chapters), while the validator, reading the table's 1.125 ratio
    and three drafted entries, names neither. A table-based read would collapse the
    oracle's verdict to the validator's, so the disagreement is exactly what proves
    the oracle is live.
    """
    spec, working_dir = divergent_table_tree
    assert live_draft_counts(working_dir) == (8000, 2)
    oracle_owned = check_live_draft(spec, working_dir)
    validator_owned = validator_verdict(working_dir) & set(PURE_STATE_INVARIANT_NAMES)
    assert oracle_owned == {GATE_RATIO_CONSISTENT, CONSECUTIVE_CLEAN_WITHIN_DRAFTED}
    assert validator_owned == set()
    assert oracle_owned != validator_owned


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
