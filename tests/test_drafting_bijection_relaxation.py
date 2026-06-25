"""Unit and property tests for the phase-gated drafting bijection relaxation.

These pin ADR 009 (roadmap task 2.1.7): while ``state.phase.current ==
Phase.DRAFTING`` and the keyword-only ``relax_drafting`` flag is set, the
``manifest-disk-bijection`` invariant relaxes to disk-subset-of-manifest — a
manifest entry without a directory stops firing, but an orphan directory and a
manifest gap still fire in every phase, and the exact bijection re-tightens at
``final-pass`` and ``done``.

The strict default is exercised here too (the regression guard the corpus
agreement suite and ``derive_reconciliation`` rely on), alongside the
``word-counts-cover-drafts`` boundary (Decision D6) and the out-of-loop wiring's
union-order preservation. A Hypothesis property sweeps the phase x tree-shape
matrix. The corpus spec library is taken by the sanctioned ``working_corpus as
wc`` value import the other corpus suites use.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state import (
    DISK_EVIDENCE_INVARIANT_NAMES,
    DONE_FLAG_WITHOUT_DRAFT,
    MANIFEST_DISK_BIJECTION,
    PENDING_TURN_CLEARED,
    WORD_COUNTS_COVER_DRAFTS,
    check_disk_evidence,
    load_state,
)
from novel_ralph_skill.state.disk_evidence import _check_manifest_disk_bijection
from novel_ralph_skill.state.phase import Phase

if typ.TYPE_CHECKING:
    from pathlib import Path


def _build_bijection_tree(
    tmp_path: Path,
    *,
    phase: str,
    on_disk: tuple[int, ...],
    manifest_only: tuple[int, ...] = (),
) -> Path:
    """Materialise a tree whose manifest and on-disk chapter sets are decoupled."""
    # ``on_disk`` are chapters drafted with a matching ``chapter-NN/`` directory and
    # a manifest entry; ``manifest_only`` are manifest entries with no directory (the
    # missing-directory direction). The two together form the manifest; the
    # directories alone form the on-disk set. The cursor sits on chapter 0 so the
    # cursor-plan predicate never demands an absent plan, and no ``done.flag`` is
    # written, so only the bijection direction varies.
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=100,
            draft_words=100,
            has_done_flag=False,
        )
        for number in on_disk
    )
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        phase_current=phase,
        phase_completed=tuple(wc.PHASE_ORDER[: wc.PHASE_ORDER.index(phase)]),
        chapters=chapters,
        manifest_only_numbers=manifest_only,
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
    )
    return wc.build_working_tree(spec, tmp_path)


def _bijection_verdict(working_dir: Path, *, relax: bool) -> set[str]:
    """Return the bijection predicate's verdict name set for a tree."""
    state = load_state(working_dir / "state.toml")
    violation = _check_manifest_disk_bijection(state, working_dir, relax_drafting=relax)
    return set() if violation is None else {violation.invariant}


def _bijection_detail(working_dir: Path, *, relax: bool) -> str:
    """Return the fired bijection violation's detail text for a tree."""
    state = load_state(working_dir / "state.toml")
    violation = _check_manifest_disk_bijection(state, working_dir, relax_drafting=relax)
    assert violation is not None, "expected a fired bijection violation"
    return violation.detail


def test_strict_default_fires_on_drafting_subset(tmp_path: Path) -> None:
    """The strict default still fires the bijection on a drafting subset.

    A drafting tree whose disk is a subset of the manifest (manifest ``{1,2,3}``,
    on-disk ``{1,2}``) fires ``manifest-disk-bijection`` under the default strict
    flag. This is the regression guard the corpus agreement suite and
    ``derive_reconciliation`` rely on: the relaxation must not leak into the
    strict path (ADR 009 / D1).
    """
    working = _build_bijection_tree(
        tmp_path, phase="drafting", on_disk=(1, 2), manifest_only=(3,)
    )
    assert _bijection_verdict(working, relax=False) == {MANIFEST_DISK_BIJECTION}


def test_relaxed_flag_silent_on_drafting_subset(tmp_path: Path) -> None:
    """The relaxed flag accepts a drafting disk-subset of the manifest (ADR 009).

    The same subset tree (manifest ``{1,2,3}``, on-disk ``{1,2}``) yields no
    ``manifest-disk-bijection`` violation under ``relax_drafting`` while
    ``phase == drafting`` — the missing-directory direction is suppressed.
    """
    working = _build_bijection_tree(
        tmp_path, phase="drafting", on_disk=(1, 2), manifest_only=(3,)
    )
    assert _bijection_verdict(working, relax=True) == set()


def test_relaxed_flag_still_fires_on_orphan_directory(tmp_path: Path) -> None:
    """An orphan directory fires the bijection even under the relaxed flag.

    A drafting tree with manifest ``{1,2}`` but an on-disk ``chapter-09/`` absent
    from the manifest still fires ``manifest-disk-bijection``: the relaxation is
    one-directional and never suppresses the orphan direction (ADR 009). The
    ``chapter-09/`` directory is created after materialisation so it has a
    directory but no manifest entry.
    """
    working = _build_bijection_tree(tmp_path, phase="drafting", on_disk=(1, 2))
    (working / "manuscript" / "chapter-09").mkdir()
    state = load_state(working / "state.toml")
    assert {chapter.number for chapter in state.chapters} == {1, 2}
    assert _bijection_verdict(working, relax=True) == {MANIFEST_DISK_BIJECTION}


def test_relaxed_flag_still_fires_on_non_contiguous_manifest(tmp_path: Path) -> None:
    """A manifest gap fires the bijection even under the relaxed flag.

    A drafting tree whose manifest skips a number (manifest ``{1,3}``, on-disk
    ``{1}``) still fires ``manifest-disk-bijection``: contiguity-from-1 is not
    relaxed (ADR 009).
    """
    working = _build_bijection_tree(
        tmp_path, phase="drafting", on_disk=(1,), manifest_only=(3,)
    )
    assert _bijection_verdict(working, relax=True) == {MANIFEST_DISK_BIJECTION}


def test_bijection_detail_names_each_broken_direction(tmp_path: Path) -> None:
    """The fired detail appends the broken direction(s) the predicate computed.

    A strict-default tree carrying an orphan directory, a missing manifest entry,
    and a manifest gap fires all three directions, so the enriched detail
    (audit:2.1.7 Finding 2) leads with the historical summary and appends each
    broken direction. Manifest ``{1,2,4}`` (gap at 3) with on-disk ``{1,2,9}``
    (chapter 9 orphan, chapter 4 missing) exercises every clause at once.
    """
    working = _build_bijection_tree(
        tmp_path, phase="drafting", on_disk=(1, 2), manifest_only=(4,)
    )
    (working / "manuscript" / "chapter-09").mkdir()
    detail = _bijection_detail(working, relax=False)
    assert detail.startswith("manifest chapters [1, 2, 4] are not in bijection")
    assert "orphan directories [9]" in detail
    assert "manifest entries without directories [4]" in detail
    assert "non-contiguous manifest" in detail


@pytest.mark.parametrize("phase", ["final-pass", "done"])
def test_relaxed_flag_fires_subset_at_terminal_phases(
    phase: str, tmp_path: Path
) -> None:
    """A manifest entry without a directory still fires at final-pass and done.

    The relaxation is gated on ``Phase.DRAFTING``; at the terminal phases the
    exact bijection is mandatory (the §4.3 ordering guarantee compile relies on),
    so a missing-directory subset fires ``manifest-disk-bijection`` even under the
    relaxed flag (ADR 009 / D3).
    """
    working = _build_bijection_tree(
        tmp_path, phase=phase, on_disk=(1, 2), manifest_only=(3,)
    )
    assert _bijection_verdict(working, relax=True) == {MANIFEST_DISK_BIJECTION}


def test_cover_drafts_silent_on_relaxed_subset_with_drifted_table(
    tmp_path: Path,
) -> None:
    """A drifted ``by_chapter`` table on a relaxed subset yields an empty verdict.

    This pins Decision D6: the relaxation removes only the
    ``manifest-disk-bijection`` signal, not a ``word-counts-cover-drafts`` one.
    ``_check_word_counts_cover_drafts`` already defers on ``manifest != on_disk``
    (its docstring), and a relaxed drafting subset always satisfies that, so the
    cover-drafts check never fired on such a tree under the strict detector. The
    same tree under the **strict** flag fires ``manifest-disk-bijection`` and
    *still not* cover-drafts, proving cover-drafts was already silent. This is the
    intended boundary, not an accident: the recount is untrustworthy off a
    non-bijective manifest, so cover-drafts cannot meaningfully run on a subset.
    """
    # Manifest {1,2,3}; on-disk {1,2}; by_chapter table also declares a key (04)
    # the manifest never names, so the table key set has drifted.
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        chapters=tuple(
            wc.ChapterSpec(
                number=number,
                slug=f"chapter-{number:02d}",
                title=f"Chapter {number}",
                target_words=100,
                draft_words=100,
                has_done_flag=False,
            )
            for number in (1, 2)
        ),
        manifest_only_numbers=(3,),
        by_chapter_override={"01": 100, "02": 100, "04": 100},
        current_words_override=300,
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")

    # Relaxed: the full verdict is empty — cover-drafts defers, the bijection is
    # relaxed, and the drifted table key surfaces nowhere.
    relaxed = check_disk_evidence(state, working, relax_drafting_bijection=True)
    assert not relaxed, "the full relaxed verdict on a clean drafting subset is ()"
    # Strict: only the bijection fires; cover-drafts is still silent (it deferred).
    strict = {v.invariant for v in check_disk_evidence(state, working)}
    assert strict == {MANIFEST_DISK_BIJECTION}
    assert WORD_COUNTS_COVER_DRAFTS not in strict


def test_union_verdict_preserves_invariant_name_order(tmp_path: Path) -> None:
    """A multi-violation tree returns names in ``DISK_EVIDENCE_INVARIANT_NAMES`` order.

    The bijection predicate is lifted out of the ``_TAIL_PREDICATES`` loop and
    called first, so this pins that the head-then-tail assembly reproduces the
    historical single-loop order. The tree fires the bijection (an orphan
    directory), ``done-flag-without-draft`` (a flag beside an empty draft), and
    ``pending-turn-cleared`` (an uncleared record) at once; the returned order
    must match their relative order in ``DISK_EVIDENCE_INVARIANT_NAMES``.
    """
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        chapters=(
            wc.ChapterSpec(
                number=1,
                slug="chapter-01",
                title="Chapter 1",
                target_words=100,
                draft_words=0,
                has_done_flag=True,
            ),
        ),
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
        by_chapter_override={"01": 0},
        current_words_override=0,
        pending_turn={"operation": "recount", "paths": ["state.toml"]},
    )
    working = wc.build_working_tree(spec, tmp_path)
    # Add an orphan directory so the bijection (element 0) fires.
    (working / "manuscript" / "chapter-09").mkdir()
    state = load_state(working / "state.toml")
    fired = [v.invariant for v in check_disk_evidence(state, working)]
    order = {name: index for index, name in enumerate(DISK_EVIDENCE_INVARIANT_NAMES)}
    assert fired == sorted(fired, key=lambda name: order[name])
    assert MANIFEST_DISK_BIJECTION in fired
    assert DONE_FLAG_WITHOUT_DRAFT in fired
    assert PENDING_TURN_CLEARED in fired
    # The bijection is element 0, so it must lead the verdict.
    assert fired[0] == MANIFEST_DISK_BIJECTION


# The four tree shapes the property sweeps, each a constructive (manifest,
# on_disk) pair built from a seed so no rejection sampling is needed (the
# hypothesis filtering-trap guidance).
_SHAPES: tuple[str, ...] = ("exact", "subset", "orphan", "non-contiguous")


@settings(max_examples=120, deadline=None)
@given(
    phase=st.sampled_from([member.value for member in Phase]),
    shape=st.sampled_from(_SHAPES),
    drafted=st.integers(min_value=1, max_value=3),
)
def test_relaxed_bijection_phase_shape_matrix(
    phase: str, shape: str, drafted: int, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The relaxed predicate matches the phase x shape table for every phase.

    ``subset`` is coherent iff ``phase == drafting``; ``exact`` is always
    coherent; ``orphan`` and ``non-contiguous`` are always violations. The
    strategy constructs each ``(manifest, on_disk)`` pair from the seed directly,
    so no ``assume`` filtering is needed (ADR 009 / D2; hypothesis filtering
    trap).
    """
    tmp_path = tmp_path_factory.mktemp("bijection")
    on_disk = tuple(range(1, drafted + 1))
    if shape == "exact":
        working = _build_bijection_tree(tmp_path, phase=phase, on_disk=on_disk)
        expected_violation = False
    elif shape == "subset":
        # Manifest holds one extra contiguous chapter with no directory.
        working = _build_bijection_tree(
            tmp_path, phase=phase, on_disk=on_disk, manifest_only=(drafted + 1,)
        )
        expected_violation = phase != Phase.DRAFTING.value
    elif shape == "orphan":
        working = _build_bijection_tree(tmp_path, phase=phase, on_disk=on_disk)
        (working / "manuscript" / "chapter-09").mkdir()
        expected_violation = True
    else:  # non-contiguous: drafted+2 is the dir-less manifest entry; drafted+1 is
        # the skipped gap, so the manifest is {1..drafted, drafted+2}.
        working = _build_bijection_tree(
            tmp_path, phase=phase, on_disk=on_disk, manifest_only=(drafted + 2,)
        )
        expected_violation = True
    fired = _bijection_verdict(working, relax=True)
    assert (fired == {MANIFEST_DISK_BIJECTION}) is expected_violation
