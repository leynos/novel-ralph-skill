"""Unit and property tests for the re-keyed ``word-counts-cover-drafts`` detector.

These pin roadmap task 2.3.8: while ``state.phase.current == Phase.DRAFTING`` and
the keyword-only ``relax_drafting`` flag is set, ``word-counts-cover-drafts`` keys
off the **on-disk drafted subset** (the directory-present chapters) and fires only
the *missing* direction — a drafted chapter whose ``by_chapter`` key the table
omits. Outside that exact shape the predicate defers exactly as the roadmap-2.3.6
detector did. A Hypothesis property pins convergence: after a manifest-keyed
recount the re-keyed detector is silent, so it never re-fires on its own repair
(Decisions D2, D6; Constraint 7).

The corpus spec library is taken by the sanctioned ``working_corpus as wc`` value
import the other corpus suites use.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from hypothesis import given, settings
from hypothesis import strategies as st
from working_corpus._oracle_disk import (
    _check_word_counts_cover_drafts as _oracle_cover_drafts,
)

from novel_ralph_skill.state import (
    WORD_COUNTS_COVER_DRAFTS,
    check_disk_evidence,
    load_state,
)
from novel_ralph_skill.state.disk_evidence import (
    _check_word_counts_cover_drafts,
    _check_word_counts_match_drafts,
)
from novel_ralph_skill.state.wordcount import recount_words

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path


def _drafting_subset_spec(
    *,
    drafted: int,
    manifest_len: int,
    by_chapter: cabc.Mapping[str, int],
    empty_drafted: cabc.Set[int] = frozenset(),
) -> wc.WorkingTreeSpec:
    """Return a relaxed drafting subset spec: ``drafted`` dirs of ``manifest_len``.

    Chapters ``1..drafted`` are fully on disk (directory plus draft); chapters
    ``drafted+1..manifest_len`` are real planned manifest entries with no
    ``chapter-NN/`` directory, so the manifest is contiguous from 1 and the
    on-disk set is a coherent subset. ``by_chapter`` is the table the caller wants
    to pin (omitting or covering drafted keys). The phase is ``drafting`` and the
    cursor sits on chapter 0 so only the cover-drafts direction varies.

    ``empty_drafted`` names drafted chapters whose ``chapter-NN/`` directory is
    still present but whose ``draft.md`` is empty (count ``0``). Decision D6 pins
    "drafted means directory-present, not non-empty ``draft.md``", so such a
    chapter is on disk and still requires a ``by_chapter`` key; this exercises the
    directory-present, empty-draft case the always-non-empty drafts cannot reach.
    """
    drafted_specs = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=100,
            draft_words=0 if number in empty_drafted else 100,
            has_done_flag=False,
        )
        for number in range(1, drafted + 1)
    )
    planned_specs = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=100,
            draft_words=0,
            has_done_flag=False,
            write_directory=False,
        )
        for number in range(drafted + 1, manifest_len + 1)
    )
    return dc.replace(
        wc.COHERENT_BASELINE,
        chapters=(*drafted_specs, *planned_specs),
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
        by_chapter_override=dict(by_chapter),
        current_words_override=sum(by_chapter.values()),
    )


def test_cover_drafts_relaxed_fires_on_omitted_drafted_key(tmp_path: Path) -> None:
    """A relaxed drafting subset omitting a drafted key fires cover-drafts.

    Manifest ``{1,2,3}``, on-disk ``{1,2}``, phase drafting, table missing the
    drafted ``"02"`` key: ``_check_word_counts_cover_drafts(relax_drafting=True)``
    fires (the missing direction, Decision D2). Under the strict default the same
    predicate defers (``None``) because the manifest and disk are not in bijection.
    """
    spec = _drafting_subset_spec(
        drafted=2, manifest_len=3, by_chapter={"01": 100, "03": 0}
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    relaxed = _check_word_counts_cover_drafts(state, working, relax_drafting=True)
    assert relaxed is not None, "relaxed predicate must fire on an omitted drafted key"
    assert relaxed.invariant == WORD_COUNTS_COVER_DRAFTS, "wrong invariant fired"
    assert _check_word_counts_cover_drafts(state, working) is None, (
        "strict default must defer without bijection"
    )


def test_match_drafts_silent_on_omitted_drafted_key_subset(tmp_path: Path) -> None:
    """The value detector is silent on the omitted-drafted-key relaxed subset.

    Pins Constraint 3 (orthogonality) directly at the predicate level: on the
    relaxed drafting subset where ``word-counts-cover-drafts`` fires (manifest
    ``{1,2,3}``, on-disk ``{1,2}``, table omitting the drafted ``"02"`` key), the
    shared-key value detector ``_check_word_counts_match_drafts`` must stay
    silent. It compares only keys shared between the manifest-keyed recount and
    the table, and the omitted ``"02"`` key is absent from the table, so no shared
    key diverges. The full-verdict suites prove this only indirectly via
    membership; this hardens the no-double-fire invariant on the *relaxed* path
    directly (distinct from step 7.15, which targets the strict predicate).
    """
    spec = _drafting_subset_spec(
        drafted=2, manifest_len=3, by_chapter={"01": 100, "03": 0}
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    # The cover detector fires here — this is the relaxed omitted-drafted-key tree.
    assert (
        _check_word_counts_cover_drafts(state, working, relax_drafting=True) is not None
    ), "guard: this subset must fire the cover detector"
    assert _check_word_counts_match_drafts(state, working) is None, (
        "the value detector must not co-fire on the omitted-drafted-key subset"
    )


def test_cover_drafts_relaxed_silent_on_coherent_subset(tmp_path: Path) -> None:
    """A relaxed drafting subset whose table covers the drafted set is silent.

    Manifest ``{1,2,3}``, on-disk ``{1,2}``, phase drafting, table covering both
    drafted keys (and carrying the undrafted manifest key ``"03"=0``): the
    relaxed predicate fires nothing, pinning the missing-only semantics and the
    convergence boundary (Decision D2, D6).
    """
    spec = _drafting_subset_spec(
        drafted=2, manifest_len=3, by_chapter={"01": 100, "02": 100, "03": 0}
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    assert (
        _check_word_counts_cover_drafts(state, working, relax_drafting=True) is None
    ), "a table covering every drafted key must keep the relaxed detector silent"


def test_cover_drafts_relaxed_silent_on_empty_drafted_dir(tmp_path: Path) -> None:
    """A drafted but empty-draft directory carrying its ``0`` key stays silent.

    Pins Decision D6 (drafted means directory-present, not non-empty
    ``draft.md``): chapter ``02``'s ``chapter-02/`` directory is present but its
    ``draft.md`` is empty, so it is on disk and requires a ``by_chapter`` key. A
    table covering it with ``"02": 0`` keeps the relaxed detector silent — a
    future refactor to a non-empty filter (dropping the empty-draft chapter from
    the drafted set) would wrongly silence on a missing key, which this case
    catches.
    """
    spec = _drafting_subset_spec(
        drafted=2,
        manifest_len=3,
        by_chapter={"01": 100, "02": 0, "03": 0},
        empty_drafted={2},
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    assert (
        _check_word_counts_cover_drafts(state, working, relax_drafting=True) is None
    ), "an empty-draft drafted directory covered by its 0 key must stay silent"


def test_cover_drafts_relaxed_converges_on_empty_drafted_dir(tmp_path: Path) -> None:
    """An empty-draft drafted directory fires when omitted, converges after RECOUNT.

    The convergence counterpart of the coherence case (Decision D6, Constraint
    7): chapter ``02``'s directory is present with an empty ``draft.md``, and the
    table omits its key, so the relaxed detector fires the missing direction. A
    manifest-keyed ``recount_words`` writes ``"02": 0`` (an empty draft counts as
    ``0``, not an absence), covering every drafted key, so the missing-only
    detector is silent — the directory-present, count-``0`` chapter converges.
    """
    spec = _drafting_subset_spec(
        drafted=2,
        manifest_len=3,
        by_chapter={"01": 100, "03": 0},  # omits the empty-draft "02" key
        empty_drafted={2},
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    assert (
        _check_word_counts_cover_drafts(state, working, relax_drafting=True) is not None
    ), "an omitted empty-draft drafted key must fire the relaxed detector"

    _current, recounted = recount_words(working, state.chapters)
    assert recounted["02"] == 0, "an empty draft must recount to a 0 key, not absence"
    repaired = dc.replace(
        state,
        word_counts=dc.replace(
            state.word_counts,
            current=sum(recounted.values()),
            by_chapter=dict(recounted),
        ),
    )
    assert (
        _check_word_counts_cover_drafts(repaired, working, relax_drafting=True) is None
    ), "a manifest-keyed recount writing the 0 key must converge"


def test_full_relaxed_verdict_empty_on_coherent_subset(tmp_path: Path) -> None:
    """A coherent relaxed subset yields an empty *full* relaxed verdict (D2, D4).

    The whole-detector counterpart to the predicate-level coherence test: a
    relaxed drafting subset (manifest ``{1,2,3}``, on-disk ``{1,2}``) whose
    ``by_chapter`` covers both drafted keys (and carries the undrafted manifest
    key ``"03"=0``) yields ``check_disk_evidence(..., relax_drafting_bijection=
    True) == ()``. With the bijection relaxed and cover-drafts firing only on the
    missing direction, a coherent mid-draft tree exits clean — the convergence
    boundary the contract flip (Decision D4) preserves.
    """
    spec = _drafting_subset_spec(
        drafted=2, manifest_len=3, by_chapter={"01": 100, "02": 100, "03": 0}
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    relaxed = check_disk_evidence(state, working, relax_drafting_bijection=True)
    assert not relaxed, "a coherent relaxed drafting subset yields an empty verdict"


@settings(max_examples=60, deadline=None)
@given(
    manifest_len=st.integers(min_value=2, max_value=4),
    seed=st.integers(min_value=0, max_value=8),
)
def test_cover_drafts_relaxed_converges_after_manifest_recount(
    manifest_len: int, seed: int, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """After a manifest-keyed recount the relaxed detector is silent (convergence).

    Constructive (no rejection sampling, per the hypothesis filtering trap): pick
    ``1 <= drafted < manifest_len`` and an omitted drafted key, build the relaxed
    drafting subset whose table drops that key (so the relaxed detector fires),
    then write the manifest-keyed ``recount_words`` table and assert the relaxed
    detector is silent — the manifest-keyed RECOUNT covers every drafted key, so
    the missing-only detector never re-fires on its own repair (Constraint 7).
    """
    drafted = 1 + seed % (manifest_len - 1)
    omitted = 1 + seed % drafted
    table = {
        f"{number:02d}": 100 for number in range(1, drafted + 1) if number != omitted
    }
    table.update({
        f"{number:02d}": 0 for number in range(drafted + 1, manifest_len + 1)
    })
    tmp_path = tmp_path_factory.mktemp("cover-converge")
    spec = _drafting_subset_spec(
        drafted=drafted, manifest_len=manifest_len, by_chapter=table
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    # The omitted drafted key makes the relaxed detector fire before the recount.
    assert (
        _check_word_counts_cover_drafts(state, working, relax_drafting=True) is not None
    ), "the omitted drafted key must fire the relaxed detector pre-recount"

    # Re-key off the manifest exactly as a RECOUNT does, then re-check.
    _current, recounted = recount_words(working, state.chapters)
    repaired = dc.replace(
        state,
        word_counts=dc.replace(
            state.word_counts,
            current=sum(recounted.values()),
            by_chapter=dict(recounted),
        ),
    )
    assert (
        _check_word_counts_cover_drafts(repaired, working, relax_drafting=True) is None
    ), "a manifest-keyed recount must converge: the detector must not re-fire"


@pytest.mark.parametrize(
    "by_chapter",
    [
        {"01": 100, "03": 0},  # omits the drafted "02" key
        {"01": 100, "02": 100, "03": 0},  # covers the drafted set
    ],
    ids=["omits-drafted-key", "covers-drafted-set"],
)
def test_relaxed_cover_twin_agrees_with_production(
    by_chapter: dict[str, int], tmp_path: Path
) -> None:
    """The relaxed production cover predicate agrees with the relaxed oracle twin.

    The relaxed analogue of the strict twin-agreement suite (developers' guide
    deliberate-twin discipline, roadmap task 2.3.8): on a relaxed drafting subset
    (manifest ``{1,2,3}``, on-disk ``{1,2}``), the production
    ``check_disk_evidence(..., relax_drafting_bijection=True)`` and the relaxed
    oracle ``_check_word_counts_cover_drafts(..., relax_drafting=True)`` must agree
    on the ``word-counts-cover-drafts`` name — both fire on an omitted drafted key
    and both stay silent on a table that covers the drafted set. Both sides read
    the same materialised tree, so the test compares like with like.
    """
    # The drafted on-disk set is {1, 2}; the predicate fires iff a drafted key is
    # absent from the table — derived from the data so no boolean param is needed.
    drafted_keys = {"01", "02"}
    expect_fires = not drafted_keys <= set(by_chapter)
    spec = _drafting_subset_spec(drafted=2, manifest_len=3, by_chapter=by_chapter)
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")

    production_fires = WORD_COUNTS_COVER_DRAFTS in {
        v.invariant
        for v in check_disk_evidence(state, working, relax_drafting_bijection=True)
    }
    oracle_coherent = _oracle_cover_drafts(working, relax_drafting=True)
    assert production_fires is not oracle_coherent, by_chapter
    assert production_fires is expect_fires, by_chapter
