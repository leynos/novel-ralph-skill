"""The ``novel-done`` predicate corpus: the all-hold tree and its clause failers.

Roadmap task 3.1.1's success criterion is a tree where all six ``novel-done``
clauses hold (so the predicate exits ``0``) plus, for each clause, a tree that
toggles exactly that clause false (so the predicate exits ``1``). These specs are
**new**, added beside ``PHASE_STATES``/``COHERENT_BASELINE`` without mutating
them (ExecPlan D-CORPUS, R-CHURN): the disk-evidence detector ignores
``reviews/`` and ``critic-notes.md``, so the existing trees stay byte-identical.

The all-hold spec is the ``done`` phase shape — three flagged, drafted chapters
crossing all three knitting gates, ``final_pass_complete``, a present
``compiled.md`` — with the two new artefacts added: all three
``reviews/knitting-NN.md`` present and a clean (absent) ``critic-notes.md``. Each
failer is :func:`dataclasses.replace` of the all-hold spec toggling one clause,
so the failer set differs from the all-hold tree in exactly one artefact.

Every spec here is also coherent under the §5.2 / §5.4 corpus oracle (the gate
booleans match the honest draft ratio, the manifest is in bijection with disk),
so a tree is "not done" only on the ``novel-done`` clause it is built to fail,
never on an incidental structural violation.
"""

from __future__ import annotations

import dataclasses as dc

from ._specs import (
    COMPILED_AUTO,
    GATE_THRESHOLDS,
    ChapterSpec,
    WorkingTreeSpec,
    concatenate_drafts,
    draft_body,
)

# The phase prefix preceding ``done`` (``premise`` … ``final-pass``), mirroring
# the ``PHASE_STATES["done"]`` completed prefix without importing the mapping.
_DONE_COMPLETED: tuple[str, ...] = (
    "premise",
    "treatment",
    "characters",
    "conflict-analysis",
    "setting",
    "reader-fit",
    "stc",
    "chapter-planning",
    "drafting",
    "final-pass",
)

_TARGET_WORDS: int = 80000
# Three drafted chapters summing to 68800 words (0.86 of the target), so all
# three knitting gates (0.30 / 0.50 / 0.80) are honestly crossed — matching the
# shared ``done`` phase shape so the all-hold tree is §5.2-coherent.
_DRAFTED_WORDS: tuple[int, ...] = (24000, 24000, 20800)

# The three knitting percentages whose reviews the all-hold tree carries.
ALL_KNITTING_REVIEWS: tuple[int, int, int] = (30, 50, 80)

# A clean ``critic-notes.md`` body: a BLOCKER line resolved by the ``[resolved]``
# token, proving the clause honours the resolution token (D-BLOCKER).
RESOLVED_BLOCKER_NOTE: str = "BLOCKER the pacing sagged in the middle [resolved]\n"

# An *unresolved* BLOCKER: a line that starts with ``BLOCKER`` and carries no
# ``[resolved]`` token, so the ``no_unresolved_blockers`` clause is false.
UNRESOLVED_BLOCKER_NOTE: str = "BLOCKER the climax contradicts chapter 2\n"

# A near-miss note: the body merely mentions resolution in prose, so the
# substring rule still classifies the BLOCKER as unresolved (advisory A5).
NEAR_MISS_BLOCKER_NOTE: str = (
    "BLOCKER the subplot dangles\nThe author says this was resolved later.\n"
)

# An incidental-resolution note: a live BLOCKER that quotes the ``[resolved]``
# token *mid-line*, not as the trailing marker. The substring rule wrongly
# cleared it (the false-clean direction); the positional rule keeps it
# unresolved (D-BLOCKER-POSITIONAL; audit-3.1.1 Finding 3).
INCIDENTAL_RESOLVED_BLOCKER_NOTE: str = (
    "BLOCKER the ending still depends on the [resolved] issue in chapter 2\n"
)


def _crossed_gates() -> tuple[bool, bool, bool]:
    """Return the knitting-gate booleans the drafted total honestly crosses."""
    ratio = sum(_DRAFTED_WORDS) / _TARGET_WORDS
    low, mid, high = GATE_THRESHOLDS
    return ratio >= low, ratio >= mid, ratio >= high


def _all_hold_chapters() -> tuple[ChapterSpec, ...]:
    """Return three flagged, drafted, clean-notes chapters for the all-hold tree."""
    return tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=words,
            draft_words=words,
            has_done_flag=True,
        )
        for index, words in enumerate(_DRAFTED_WORDS)
    )


def _all_hold_spec() -> WorkingTreeSpec:
    """Return the all-six-clauses-hold ``done`` tree spec."""
    done_30, done_50, done_80 = _crossed_gates()
    chapters = _all_hold_chapters()
    return WorkingTreeSpec(
        phase_current="done",
        phase_completed=_DONE_COMPLETED,
        chapters=chapters,
        target_words=_TARGET_WORDS,
        consecutive_clean=1,
        convergence_target=1,
        current_chapter=len(chapters),
        compiled=COMPILED_AUTO,
        final_pass_complete=True,
        done_30=done_30,
        done_50=done_50,
        done_80=done_80,
        knitting_reviews=ALL_KNITTING_REVIEWS,
    )


DONE_PREDICATE_ALL_HOLD: WorkingTreeSpec = _all_hold_spec()


def _unflag_first_chapter(spec: WorkingTreeSpec) -> WorkingTreeSpec:
    """Return ``spec`` with the first chapter's ``done.flag`` removed."""
    first, *rest = spec.chapters
    return dc.replace(spec, chapters=(dc.replace(first, has_done_flag=False), *rest))


def _note_on_first_chapter(spec: WorkingTreeSpec, note: str) -> WorkingTreeSpec:
    """Return ``spec`` with ``note`` written as the first chapter's critic notes."""
    first, *rest = spec.chapters
    return dc.replace(spec, chapters=(dc.replace(first, critic_notes=note), *rest))


# The per-clause failers: each toggles exactly one ``novel-done`` clause false,
# keyed by the clause name the all-hold tree would otherwise satisfy. Two
# distinct ``knitting_gates_passed`` failers are modelled — a missing review file
# and a false gate boolean — so both halves of the clause are exercised.
DONE_PREDICATE_FAILERS: dict[str, WorkingTreeSpec] = {
    "phase_is_done": dc.replace(DONE_PREDICATE_ALL_HOLD, phase_current="final-pass"),
    "final_pass_complete": dc.replace(
        DONE_PREDICATE_ALL_HOLD, final_pass_complete=False
    ),
    "all_chapters_flagged": _unflag_first_chapter(DONE_PREDICATE_ALL_HOLD),
    "knitting_review_missing": dc.replace(
        DONE_PREDICATE_ALL_HOLD, knitting_reviews=(30, 80)
    ),
    "knitting_gate_false": dc.replace(DONE_PREDICATE_ALL_HOLD, done_50=False),
    "compile_consistent": dc.replace(DONE_PREDICATE_ALL_HOLD, compiled=None),
    "no_unresolved_blockers": _note_on_first_chapter(
        DONE_PREDICATE_ALL_HOLD, UNRESOLVED_BLOCKER_NOTE
    ),
}

# A ``[resolved]``-BLOCKER tree still holds (the resolution token is honoured),
# and a near-miss BLOCKER tree whose body merely mentions resolution in prose
# stays *not* done (the substring rule's edge; advisory A5).
DONE_PREDICATE_RESOLVED_BLOCKER: WorkingTreeSpec = _note_on_first_chapter(
    DONE_PREDICATE_ALL_HOLD, RESOLVED_BLOCKER_NOTE
)
DONE_PREDICATE_NEAR_MISS_BLOCKER: WorkingTreeSpec = _note_on_first_chapter(
    DONE_PREDICATE_ALL_HOLD, NEAR_MISS_BLOCKER_NOTE
)
# An incidental-resolution tree: a live BLOCKER quoting ``[resolved]`` mid-line
# stays *not* done. This pins the false-clean direction the positional anchor
# closes (D-BLOCKER-POSITIONAL; audit-3.1.1 Finding 3); it differs from the
# all-hold tree only in the first chapter's note body, so it fails on exactly
# the ``no_unresolved_blockers`` clause.
DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER: WorkingTreeSpec = _note_on_first_chapter(
    DONE_PREDICATE_ALL_HOLD, INCIDENTAL_RESOLVED_BLOCKER_NOTE
)

# --- stale-compile specs (roadmap 3.1.2, D-CORPUS-STALE) ---------------------
#
# On the "header count" half of the success criterion (A-1): the corpus
# ``draft_body`` emits header-free bodies (``"word word word"``), so every corpus
# draft carries zero ``#``-prefixed lines and the "header count" coincidence is
# vacuously ``0 == 0`` on both sides. Adding header-bearing drafts would break the
# word-count derivation (``len(body.split()) != draft_words``) and cascade through
# the §5.2 corpus oracle, so this plan takes option 2 of the ExecPlan A-1 fork:
# the **word-total** coincidence is modelled here (a stale compile with the same
# whitespace-split token count as the true concatenation), and the genuine
# byte-fidelity property is discharged by the Work-item-1 Hypothesis
# byte-perturbation property, which falsifies any non-whitespace change regardless
# of header structure. No reviewer should read this as testing a literal non-zero
# header-count coincidence; under the header-free corpus that coincidence is
# vacuous.


def _count_coincident_stale_body(spec: WorkingTreeSpec) -> str:
    """Return a stale ``compiled.md`` body that is count-coincident but divergent.

    Recomputes the coherent ordered concatenation of ``spec``'s present drafts
    and swaps one ``"word"`` token for the equal-length ``"wxrd"``, so the
    whitespace-split token count is preserved (R-STALE-MISS) while at least one
    non-whitespace byte differs. The header count is preserved too — vacuously,
    since the header-free corpus drafts carry no ``#`` lines (A-1). Raises when
    the drafts contain no ``"word"`` token to swap, so a silently coherent body
    can never masquerade as stale.
    """
    bodies = [draft_body(chapter.draft_words) for chapter in spec.chapters]
    coherent = concatenate_drafts(bodies)
    stale = coherent.replace("word", "wxrd", 1)
    if stale == coherent:
        msg = "cannot derive a count-coincident stale body: no 'word' token"
        raise ValueError(msg)
    return stale


_STALE_COMPILED: str = _count_coincident_stale_body(DONE_PREDICATE_ALL_HOLD)

# The sole-stale-compile tree: every clause holds except ``compile_consistent``,
# which is false because ``compiled.md`` is present but byte-divergent (the
# count-coincident stale body). The load-bearing exit-``4`` fixture (D-CARVE).
DONE_PREDICATE_SOLE_STALE_COMPILE: WorkingTreeSpec = dc.replace(
    DONE_PREDICATE_ALL_HOLD, compiled=_STALE_COMPILED
)

# The mid-draft-stale tree: a drafting clause is unmet (``phase_current`` is not
# ``done``) *and* the same count-coincident stale ``compiled.md`` is present, so
# ``compile_consistent`` is false alongside ``phase_is_done``. Proves the
# exit-``4`` carve-out stays at exit ``1`` mid-draft (R-CARVE-MISFIRE).
DONE_PREDICATE_MID_DRAFT_STALE: WorkingTreeSpec = dc.replace(
    DONE_PREDICATE_ALL_HOLD, phase_current="final-pass", compiled=_STALE_COMPILED
)

# A plainly-wrong stale compile (byte- *and* count-divergent), the obvious
# control beside the subtle count-coincident one.
DONE_PREDICATE_OBVIOUS_STALE_COMPILE: WorkingTreeSpec = dc.replace(
    DONE_PREDICATE_ALL_HOLD, compiled="this is not the concatenation of any drafts"
)
