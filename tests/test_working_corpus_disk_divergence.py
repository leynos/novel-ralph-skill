"""Divergence-proof self-tests for the disk-reading corpus oracle (roadmap 2.3.3).

Roadmap task 2.3.3 rerouted three corpus-oracle predicates
(``_check_manifest_disk_bijection``, ``_check_done_flag_without_draft``,
``_check_compiled_matches_drafts``) to read the materialised ``working/`` tree
rather than the ``WorkingTreeSpec``. These tests prove the reroute reads disk,
not spec: each builds a coherent tree whose ``state.toml`` agrees with the spec,
asserts ``corpus_check`` returns ``()`` on the unmutated tree, then performs a
**post-build disk-only mutation** (never a spec change) and asserts the exact
``corpus_check`` tuple in :data:`CORPUS_INVARIANT_NAMES` vocabulary order. A
spec-reading oracle would miss every mutation here.

This module is the focused home for the disk-divergence self-tests, carved out
of ``tests/test_working_corpus.py`` (already past the 400-line cap) mirroring the
``tests/test_working_corpus_divergent.py`` carve-out idiom. The corpus is consumed
by the ``build_tree`` and ``check_corpus`` fixtures plus the sanctioned
``working_corpus as wc`` value import for the ``COHERENT_BASELINE`` /
``COMPILED_AUTO`` *values* only (developers' guide §"Shared test scaffolding");
the spec *type* is named only under ``if TYPE_CHECKING:``.
"""

from __future__ import annotations

import dataclasses as dc
import shutil
import typing as typ

import working_corpus as wc

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec


class TestCorpusDiskDivergence:
    """Pin that the rerouted oracle predicates catch disk-only divergences.

    Each test builds a coherent ``COHERENT_BASELINE``-derived tree, asserts
    ``corpus_check`` is empty on the unmutated tree (so the flip is caused by the
    disk change, not an already-incoherent spec), then mutates the materialised
    disk and asserts the exact ``corpus_check`` tuple the planning probe measured
    (ExecPlan S1, S2). Two tests cover a clean single-invariant divergence; two
    cover a genuine multi-axis divergence whose two-name co-fire is the correct,
    intended behaviour (D-COFIRE1, D-COFIRE2).
    """

    def test_compiled_stale_against_disk_caught_after_count_preserving_edit(
        self,
        build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
        tmp_path: Path,
    ) -> None:
        """A count-preserving draft edit makes ``compiled.md`` stale on disk alone.

        Builds an ``AUTO``-compiled tree (the hash-equal compile), then overwrites
        one chapter's ``draft.md`` with the same token *count* but different bytes,
        so the whitespace-split word-count table is undisturbed while ``compiled.md``
        no longer matches the present drafts. The spec's ``draft_words`` is
        unchanged, so a spec-reading compiled check would still match the stale
        ``compiled.md``; the disk read catches the divergence. Clean singleton:
        ``(compiled-matches-drafts,)`` (D-CLEAN).
        """
        spec = dc.replace(wc.COHERENT_BASELINE, compiled=wc.COMPILED_AUTO)
        working = build_tree(spec, tmp_path)
        assert check_corpus(spec, working) == (), "unmutated AUTO-compiled tree"
        draft = working / "manuscript" / "chapter-01" / "draft.md"
        token_count = len(draft.read_text(encoding="utf-8").split())
        draft.write_text(" ".join(["XXXX"] * token_count), encoding="utf-8")
        assert check_corpus(spec, working) == ("compiled-matches-drafts",), (
            "count-preserving draft edit should make compiled.md stale on disk"
        )

    def test_manifest_bijection_caught_from_disk_after_extra_directory(
        self,
        build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
        tmp_path: Path,
    ) -> None:
        """A post-build ``mkdir`` of an unmanifested chapter breaks the bijection.

        Builds ``COHERENT_BASELINE`` (3-chapter manifest 1/2/3, no ``compiled.md``)
        then creates ``manuscript/chapter-04/`` on disk, absent from the manifest
        and carrying no ``draft.md``. The spec is unchanged and coherent, so a
        spec-reading bijection check returns ``()`` (ExecPlan S2); the disk read
        sees the extra directory. The added directory is absent from
        ``state.toml``'s ``[chapters]``, so the manifest-keyed word-count and
        done-flag reads never visit it and there is no ``compiled.md``, so this is
        a clean singleton: ``(manifest-disk-bijection,)`` (D-CLEAN2).
        """
        spec = wc.COHERENT_BASELINE
        working = build_tree(spec, tmp_path)
        assert check_corpus(spec, working) == (), "unmutated baseline tree"
        (working / "manuscript" / "chapter-04").mkdir()
        assert check_corpus(spec, working) == ("manifest-disk-bijection",), (
            "unmanifested chapter-04 directory should break the disk bijection"
        )

    def test_manifest_bijection_and_wordcount_cofire_after_directory_removed(
        self,
        build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
        tmp_path: Path,
    ) -> None:
        """Removing a chapter directory co-fires bijection and word-count checks.

        Builds ``COHERENT_BASELINE`` (chapters 24000/24000/20800) then removes
        ``manuscript/chapter-03/``, whose ``[word_counts].by_chapter`` entry is
        non-zero. The directory removal breaks the manifest-disk bijection (the
        manifest entry survives in ``state.toml``); the now-absent ``draft.md``
        reads as 0 tokens, diverging from the table's non-zero entry. The co-fire
        is the correct multi-axis divergence, pinned as the exact two-name tuple:
        ``(manifest-disk-bijection, word-counts-match-drafts)`` (D-COFIRE1).
        """
        spec = wc.COHERENT_BASELINE
        working = build_tree(spec, tmp_path)
        assert check_corpus(spec, working) == (), "unmutated baseline tree"
        shutil.rmtree(working / "manuscript" / "chapter-03")
        assert check_corpus(spec, working) == (
            "manifest-disk-bijection",
            "word-counts-match-drafts",
        ), "removing chapter-03 should co-fire bijection and word-count checks"

    def test_done_flag_and_wordcount_cofire_after_draft_emptied(
        self,
        build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
        tmp_path: Path,
    ) -> None:
        """Emptying a flagged chapter's draft co-fires done-flag and word-count.

        Builds ``COHERENT_BASELINE`` (chapters 1 and 2 flagged, non-empty drafts)
        then empties chapter 1's ``draft.md`` on disk while leaving its
        ``done.flag``. The flag now sits beside an empty draft (``done-flag``
        fires); the now-zero draft diverges from the table's 24000 entry
        (``word-counts`` fires). ``COHERENT_BASELINE`` writes no ``compiled.md``,
        so ``compiled-matches-drafts`` stays silent. Exact two-name tuple:
        ``(done-flag-without-draft, word-counts-match-drafts)`` (D-COFIRE2).
        """
        spec = wc.COHERENT_BASELINE
        working = build_tree(spec, tmp_path)
        assert check_corpus(spec, working) == (), "unmutated baseline tree"
        (working / "manuscript" / "chapter-01" / "draft.md").write_text(
            "", encoding="utf-8"
        )
        assert check_corpus(spec, working) == (
            "done-flag-without-draft",
            "word-counts-match-drafts",
        ), "emptying a flagged draft should co-fire done-flag and word-count checks"
