"""The named specification library: the eleven phase states and the baseline.

``PHASE_STATES`` maps each phase enum member (``premise`` … ``done``, design
§5.1 lines 402-405) to a coherent :class:`WorkingTreeSpec` whose
``phase.current`` is that member and whose ``phase.completed`` is the exact
in-order prefix preceding it (invariants 1 and 2). The pre-drafting phases carry
an empty chapter manifest and a zeroed cursor; ``drafting``, ``final-pass``, and
``done`` carry a small populated manifest with matching ``chapter-NN/``
directories, drafts, gate booleans consistent with their word counts, and (for
``final-pass``/``done``) a coherent ``compiled.md``.

``COHERENT_BASELINE`` is the canonical mid-drafting coherent tree the incoherent
variants (Work item 3) mutate.
"""

from __future__ import annotations

from ._specs import COMPILED_AUTO, GATE_THRESHOLDS, ChapterSpec, WorkingTreeSpec

# The eleven phase enum members, in order (design §5.1 lines 402-405; mirrored in
# ``state-layout.md`` lines 122-134). This is the corpus's single in-order list;
# the per-phase completed prefix is sliced from it.
PHASE_ORDER: tuple[str, ...] = (
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
    "done",
)

# The novel target every corpus tree shares, and the drafting chapter word
# counts that determine the knitting-gate booleans. The three drafted chapters
# sum to 68800 words, 0.86 of the 80000 target, so all three gates (0.30 / 0.50 /
# 0.80, :data:`GATE_THRESHOLDS`) are honestly crossed.
_TARGET_WORDS: int = 80000
_DRAFTED_WORDS: tuple[int, ...] = (24000, 24000, 20800)


def _drafted_chapters(*, all_flagged: bool) -> tuple[ChapterSpec, ...]:
    """Return the shared drafting-era manifest, flagging all or all-but-last."""
    return tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=words,
            draft_words=words,
            has_done_flag=all_flagged or index < len(_DRAFTED_WORDS) - 1,
        )
        for index, words in enumerate(_DRAFTED_WORDS)
    )


def _crossed_gates() -> tuple[bool, bool, bool]:
    """Return the knitting-gate booleans the drafted total honestly crosses."""
    ratio = sum(_DRAFTED_WORDS) / _TARGET_WORDS
    low, mid, high = GATE_THRESHOLDS
    return ratio >= low, ratio >= mid, ratio >= high


def _pre_drafting_spec(phase: str, completed: tuple[str, ...]) -> WorkingTreeSpec:
    """Return a coherent pre-drafting spec (empty manifest, zeroed cursor)."""
    return WorkingTreeSpec(
        phase_current=phase,
        phase_completed=completed,
        chapters=(),
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
    )


def _drafting_spec(phase: str, completed: tuple[str, ...]) -> WorkingTreeSpec:
    """Return a coherent drafting-era spec; complete phases flag and compile."""
    is_complete = phase in {"final-pass", "done"}
    chapters = _drafted_chapters(all_flagged=is_complete)
    done_30, done_50, done_80 = _crossed_gates()
    return WorkingTreeSpec(
        phase_current=phase,
        phase_completed=completed,
        chapters=chapters,
        target_words=_TARGET_WORDS,
        consecutive_clean=1,
        convergence_target=1,
        current_chapter=len(chapters),
        compiled=COMPILED_AUTO if is_complete else None,
        final_pass_complete=phase == "done",
        done_30=done_30,
        done_50=done_50,
        done_80=done_80,
    )


def _spec_for_phase(phase: str, completed: tuple[str, ...]) -> WorkingTreeSpec:
    """Return the coherent spec for a single phase enum member."""
    if phase in {"drafting", "final-pass", "done"}:
        return _drafting_spec(phase, completed)
    return _pre_drafting_spec(phase, completed)


def _build_phase_states() -> dict[str, WorkingTreeSpec]:
    """Return the ``PHASE_STATES`` mapping built from :data:`PHASE_ORDER`."""
    return {
        phase: _spec_for_phase(phase, PHASE_ORDER[:index])
        for index, phase in enumerate(PHASE_ORDER)
    }


PHASE_STATES: dict[str, WorkingTreeSpec] = _build_phase_states()

# The canonical mid-drafting coherent tree the Work item 3 variants mutate.
COHERENT_BASELINE: WorkingTreeSpec = PHASE_STATES["drafting"]
