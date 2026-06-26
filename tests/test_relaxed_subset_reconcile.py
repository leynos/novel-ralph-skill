"""Reconcile derivation on a relaxed drafting subset cover gap (roadmap 2.3.8).

These pin the scoped, drafting-gated cover-drafts pre-arm in
:func:`novel_ralph_skill.state.derive_reconciliation` (Decision D3). The pre-arm
runs strictly AFTER the torn ``set-chapters`` COMPLETE arm (B1; pinned in
``test_set_chapters_reconcile``) and strictly BEFORE the refuse-class arm, gated
on no ``[pending_turn]`` AND a fired refuse-class of exactly
``{manifest-disk-bijection}`` (B2):

- a coherent drafting subset with a missing drafted cover key derives RECOUNT
  (re-keying ``by_chapter`` off the manifest) rather than REFUSE;
- a torn non-``set-chapters`` pending turn on such a subset is never masked into a
  RECOUNT (the ``pending_turn is None`` gate);
- a co-occurring second contradiction still REFUSEs (the exact-refuse-class gate).

The corpus spec library is taken by the sanctioned ``working_corpus as wc`` value
import the other corpus suites use.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import working_corpus as wc

from novel_ralph_skill.state import (
    ReconcileAction,
    derive_reconciliation,
    load_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path


def _drafting_subset_spec(
    *, by_chapter: dict[str, int], pending_turn: dict[str, object] | None = None
) -> wc.WorkingTreeSpec:
    """Return a relaxed drafting subset: manifest {1,2,3}, on-disk {1,2}, drafting.

    Chapters 1 and 2 are fully drafted (directory plus draft); chapter 3 is a real
    planned manifest entry with no directory (``write_directory=False``), so the
    manifest is the contiguous ``{1,2,3}`` and the on-disk set is the coherent
    subset ``{1,2}``. ``by_chapter`` is the table to pin; ``pending_turn`` seeds an
    optional torn turn so the B2 cases can co-occur a pending turn with a cover gap.
    """
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
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
        by_chapter_override=by_chapter,
        current_words_override=sum(by_chapter.values()),
        pending_turn=pending_turn,
    )


def test_relaxed_subset_cover_gap_recounts(tmp_path: Path) -> None:
    """A relaxed drafting subset cover gap derives RECOUNT, not REFUSE (D3).

    Manifest ``{1,2,3}``, on-disk ``{1,2}``, phase drafting, no pending turn, with
    the drafted ``"02"`` key omitted: the scoped cover-drafts pre-arm RECOUNTs
    (re-keying ``by_chapter`` off the manifest, supplying the missing drafted key
    and the ``0`` undrafted key) ahead of the strict refuse-class arm the bijection
    would otherwise drive (roadmap task 2.3.8).
    """
    spec = _drafting_subset_spec(by_chapter={"01": 100, "03": 0})
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action == ReconcileAction.RECOUNT
    assert reconciliation.discrepancies == ("word-counts-cover-drafts",)
    assert reconciliation.recounted_by_chapter == {"01": 100, "02": 100, "03": 0}
    assert reconciliation.recounted_current == 200


def test_relaxed_subset_torn_write_draft_is_not_recounted(
    tmp_path: Path,
) -> None:
    """A torn write-draft on a relaxed subset with a cover gap is not pre-empted (B2).

    A non-``set-chapters`` torn turn (``write-draft``) on a coherent drafting
    subset that also carries a cover gap must NOT be masked into a RECOUNT by the
    cover-drafts pre-arm: its ``pending_turn is None`` gate is false, so the pre-arm
    is silent. Under strict reconcile the firing ``manifest-disk-bijection`` is
    refuse-class and the refuse arm precedes the pending-turn arm, so the tree
    REFUSEs exactly as it does today — the pre-arm leaves the existing strict
    precedence (ADR 008/ADR 009) untouched. The decisive pin is that the pre-arm
    never RECOUNTs over an uncleared pending turn.
    """
    spec = _drafting_subset_spec(
        by_chapter={"01": 100, "03": 0},
        pending_turn={
            "operation": "write-draft",
            "paths": ["working/manuscript/chapter-99/draft.md"],
        },
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action != ReconcileAction.RECOUNT, (
        "the cover-drafts pre-arm must not mask an uncleared pending turn"
    )
    assert reconciliation.action == ReconcileAction.REFUSE, (
        "the strict bijection break still REFUSEs ahead of the pending-turn arm"
    )


def test_relaxed_subset_second_contradiction_still_refuses(tmp_path: Path) -> None:
    """A relaxed subset cover gap alongside a second contradiction REFUSEs (B2).

    A coherent drafting subset with a cover gap that ALSO carries a present-and-
    diverging ``compiled.md`` (the ``compiled-matches-drafts`` contradiction) fires
    a refuse-class set larger than ``{manifest-disk-bijection}``, so the exact-
    refuse-class gate keeps the pre-arm silent and the tree REFUSEs, never
    RECOUNTs.
    """
    spec = _drafting_subset_spec(by_chapter={"01": 100, "03": 0})
    working = wc.build_working_tree(spec, tmp_path)
    (working / "manuscript" / "compiled.md").write_text(
        "stale content diverging from the drafts", encoding="utf-8"
    )
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action == ReconcileAction.REFUSE, (
        "a co-occurring second contradiction must REFUSE, not RECOUNT"
    )
