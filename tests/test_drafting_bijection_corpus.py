"""Corpus oracle-twin agreement and a positive case for the ADR 009 relaxation.

These keep the independent corpus oracle in lock-step with the relaxed production
path (the deliberate-twin discipline, developers' guide "Invariant validation")
and prove the relaxation through a coherent drafting-subset corpus tree:

- the **relaxed agreement** test pins that, on the drafting subset and on the
  ``final-pass``/``done`` exact-bijection trees, the relaxed production
  ``check_disk_evidence(..., relax_drafting_bijection=True)`` agrees with the
  relaxed oracle twin on the ``manifest-disk-bijection`` name;
- the **positive drafting-subset** case asserts the FULL relaxed verdict tuple is
  empty on a coherent subset (a real planned-but-undrafted chapter 3 present in
  the manifest but absent on disk), and that the SAME tree under the strict default
  fires exactly ``manifest-disk-bijection``.

The strict agreement suite (``test_novel_state_check_disk``) is untouched: it calls
``check_disk_evidence`` and the oracle twin with the strict default, so no strict
regression is introduced. The corpus spec library is taken by the sanctioned
``working_corpus as wc`` value import.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from working_corpus._oracle_disk import (
    _check_manifest_disk_bijection as _oracle_bijection,
)

from novel_ralph_skill.state import (
    MANIFEST_DISK_BIJECTION,
    check_disk_evidence,
    load_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path


def _coherent_drafting_subset_spec() -> wc.WorkingTreeSpec:
    """Return a coherent drafting subset: chapters 1-2 on disk, 3 manifest-only."""
    # Chapters 1 and 2 are fully drafted (directory, draft.md, by_chapter value);
    # chapter 3 is a real planned chapter (slug/title/target_words and a zero
    # by_chapter entry) whose directory the builder skips (write_directory=False),
    # so manifest = {1,2,3} but on-disk = {1,2}. The cursor sits on a present
    # chapter (2) with zeroed scene/beat so cursor-plan never demands an absent
    # plan, and every other disk-evidence predicate is satisfied by construction.
    drafted = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=100,
            draft_words=100,
            has_done_flag=False,
        )
        for number in (1, 2)
    )
    planned = wc.ChapterSpec(
        number=3,
        slug="chapter-03",
        title="Chapter 3",
        target_words=100,
        draft_words=0,
        has_done_flag=False,
        write_directory=False,
    )
    return dc.replace(
        wc.COHERENT_BASELINE,
        chapters=(*drafted, planned),
        current_chapter=2,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
    )


def test_positive_drafting_subset_relaxed_verdict_is_empty(tmp_path: Path) -> None:
    """A coherent drafting subset yields an empty FULL relaxed verdict (ADR 009).

    The relaxed checker treats the real planned-but-undrafted chapter 3 (manifest
    ``{1,2,3}``, on-disk ``{1,2}``) as coherent and every other disk-evidence
    predicate passes, so the full verdict is ``()`` — a genuinely clean exit-0
    tree. The SAME tree under the strict default fires exactly
    ``manifest-disk-bijection`` and nothing else, proving the relaxation is exactly
    the phase-gated flag and nothing more (resolves review r1 blocking item 2).
    """
    working = wc.build_working_tree(_coherent_drafting_subset_spec(), tmp_path)
    state = load_state(working / "state.toml")

    relaxed = check_disk_evidence(state, working, relax_drafting_bijection=True)
    assert not relaxed, "the full relaxed verdict on a coherent drafting subset is ()"

    strict = tuple(v.invariant for v in check_disk_evidence(state, working))
    assert strict == (MANIFEST_DISK_BIJECTION,)


@pytest.mark.parametrize("phase", ["drafting", "final-pass", "done"])
def test_relaxed_production_agrees_with_relaxed_oracle(
    phase: str, tmp_path: Path
) -> None:
    """The relaxed production bijection agrees with the relaxed oracle twin.

    The relaxed analogue of the strict agreement suite, scoped to the bijection
    name. For the drafting subset the relaxed verdict is coherent only at
    ``drafting``; the ``final-pass``/``done`` exact-bijection baselines are
    coherent in every phase. Both sides read the same materialised tree, so the
    test compares like with like (deliberate-twin discipline).
    """
    if phase == "drafting":
        working = wc.build_working_tree(_coherent_drafting_subset_spec(), tmp_path)
    else:
        working = wc.build_working_tree(wc.PHASE_STATES[phase], tmp_path)
    state = load_state(working / "state.toml")

    production_fires = MANIFEST_DISK_BIJECTION in {
        v.invariant
        for v in check_disk_evidence(state, working, relax_drafting_bijection=True)
    }
    oracle_coherent = _oracle_bijection(working, relax_drafting=True)
    assert production_fires is not oracle_coherent, phase
    # The drafting subset and the terminal exact-bijection trees are all coherent
    # under the relaxed bijection, so neither side fires.
    assert not production_fires, phase
