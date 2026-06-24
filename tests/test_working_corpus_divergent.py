"""Self-tests for the §1.3.2 divergent-table corpus category (roadmap 2.1.5+).

The divergent-table variants live in the ``working_corpus`` package's
``DIVERGENT_TABLE_VARIANTS`` mapping and are consumed here by pytest fixture
parameter name (``divergent_table_tree``, ``divergent_table_variant_names``);
this module never performs a runtime value import of the mapping. The only
cross-module symbols it names are the spec *type*, imported under
``if TYPE_CHECKING:`` via the sanctioned ``from conftest import …`` carve-out
(developers-guide "Shared test scaffolding").

This is the focused home for the divergent-table self-tests, carved out of
``tests/test_working_corpus.py`` so that module stays nearer the 400-line cap and
so the new under-counting self-tests land in a module that is itself under the cap
(mirroring the corpus fixture-plugin split idiom). The tests pin that each
divergent-table tree breaks its owned proxies under the spec-draft
:func:`corpus_check` while the table-reading §5.2 validator stays silent, and that
the category is excluded from ``INCOHERENT_VARIANTS``, so a future reader cannot
mistake the deliberate validator-versus-oracle disagreement for a bug.
"""

from __future__ import annotations

import typing as typ

from _state_corpus_support import validator_verdict

from novel_ralph_skill.state import PURE_STATE_INVARIANT_NAMES

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec


_OVER_COUNTING_KEY = "by-chapter-override-over-counts-drafts"
_UNDER_COUNTING_KEY = "by-chapter-override-under-counts-drafts"


class TestCorpusDivergentTable:
    """Pin the divergent-table category's shape, exclusion, and disagreement.

    The divergent-table variants (roadmap 2.1.5 over-counting, roadmap 2.1.6
    under-counting) are first-class §1.3.2 corpus members, separate from
    ``INCOHERENT_VARIANTS``: under the spec-draft :func:`corpus_check` each breaks
    at least one table-based proxy while the table-reading §5.2 validator breaks
    neither. These tests pin that the category is excluded from the incoherent set
    and that the two sides disagree exactly as designed — the over-counting tree on
    both gate/cursor proxies, the under-counting tree on ``gate-ratio-consistent``
    only — while roadmap task 2.3.2's disk-evidence ``word-counts-match-drafts``
    detector fires on both, since each table diverges from the on-disk drafts per
    chapter. A future reader cannot mistake the disagreement for a bug and "fix" it
    by aligning the oracles. Every tree is sourced from the corpus through the
    ``divergent_table_tree`` factory fixture, so the corpus stays consumed by
    fixture name and never by a runtime value import.
    """

    def test_divergent_table_breaks_both_proxies(
        self,
        divergent_table_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
    ) -> None:
        """``corpus_check`` names the two table-based proxies plus the disk-vs-table.

        The vocabulary order is ``consecutive-clean-within-drafted`` (index 5)
        before ``gate-ratio-consistent`` (index 9), and ``by-chapter-sum`` stays
        silent because ``current`` equals the override table sum (Decision Log
        D3). Roadmap task 2.3.2's ``word-counts-match-drafts`` (index 13) now also
        fires: the override table over-counts the on-disk drafts, which is exactly
        the disk-vs-table per-chapter divergence that detector owns (D-WORDCOUNT).
        """
        spec, working = divergent_table_tree(_OVER_COUNTING_KEY)
        assert check_corpus(spec, working) == (
            "consecutive-clean-within-drafted",
            "gate-ratio-consistent",
            "word-counts-match-drafts",
        )

    def test_divergent_table_not_in_incoherent_variants(
        self,
        divergent_table_variant_names: tuple[str, ...],
        incoherent_variant_names: tuple[str, ...],
    ) -> None:
        """The divergent-table keys are absent from ``INCOHERENT_VARIANTS``.

        Pins the Constraint that the variants form a separate category, so the
        single-invariant and validator-versus-oracle agreement self-tests never
        see them.
        """
        assert _OVER_COUNTING_KEY in divergent_table_variant_names
        assert _UNDER_COUNTING_KEY in divergent_table_variant_names
        assert set(divergent_table_variant_names).isdisjoint(incoherent_variant_names)

    def test_under_counting_table_breaks_only_gate_ratio(
        self,
        divergent_table_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
    ) -> None:
        """``corpus_check`` names ``gate-ratio-consistent`` plus the disk-vs-table.

        Among the gate and cursor proxies the under-counting tree breaks only
        ``gate-ratio-consistent``. The under-counting tree's verified shape
        (Decision Log D2): the live 1.125 ratio contradicts the all-``False``
        gates, so ``gate-ratio-consistent`` fires; ``consecutive-clean-within-drafted``
        stays silent because the ``consecutive_clean`` counter 2 is within both the
        live (3) and the under-counted table (2) drafted-chapter counts;
        ``by-chapter-sum`` stays silent because ``current`` equals the override
        table sum (Decision Log D3); and ``cursor-coherent`` stays silent because
        ``current_chapter`` 3 is within the three drafted chapters. Roadmap task
        2.3.2's disk-evidence ``word-counts-match-drafts`` (index 13) also fires:
        the override table under-counts the on-disk drafts per chapter, which is
        exactly the disk-vs-table divergence that detector owns (D-WORDCOUNT),
        symmetric to the over-counting tree. A drift in the gates or the drafts is
        caught immediately by the exact expectation.
        """
        spec, working = divergent_table_tree(_UNDER_COUNTING_KEY)
        assert check_corpus(spec, working) == (
            "gate-ratio-consistent",
            "word-counts-match-drafts",
        )

    def test_divergent_table_validator_stays_silent(
        self,
        divergent_table_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
        divergent_table_variant_names: tuple[str, ...],
    ) -> None:
        """The table-reading validator's owned verdict is empty on every tree.

        The disagreement's table side, pinned for both directions: on the
        over-counting tree the validator reads a 1.125 ratio and three drafted
        entries; on the under-counting tree it reads a 0.10 ratio and two drafted
        entries. Both match the tree's gates, so the §5.2 validator names neither
        proxy and the table side of the disagreement is empty for each member.
        """
        owned = set(PURE_STATE_INVARIANT_NAMES)
        for name in divergent_table_variant_names:
            _spec, working = divergent_table_tree(name)
            assert validator_verdict(working) & owned == set(), name
