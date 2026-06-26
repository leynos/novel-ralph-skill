"""Shared ``working/`` tree builders for the gate/drafting mutator suites.

Roadmap task 2.2.4 needs three ``set-gate`` fixtures the named corpus does not
ship — ``COHERENT_BASELINE`` has a 0.86 drafted ratio with every gate already
true, so it cannot exercise an observable gate flip (ExecPlan Decision D8/B2).
These builders construct each tree directly from
:class:`working_corpus.WorkingTreeSpec`, mirroring the ratio-shrinking pattern
``working_corpus._variants._gate_true_below_threshold`` uses, so the suites share
one definition of each tree rather than repeating the spec in every module.

The validator's drafted ratio is ``sum(by_chapter) / target`` (not ``current``;
``validate.py:_check_gate_ratio_consistent``), so each ``draft_words`` total
divided by 80000 is the ratio the §5.2 ``gate-ratio-consistent`` invariant binds.
"""

from __future__ import annotations

import typing as typ

import working_corpus as wc
from working_corpus import ChapterSpec, WorkingTreeSpec

if typ.TYPE_CHECKING:
    from pathlib import Path

# The eight in-order completed phases of a ``drafting``-phase tree, so each
# constructed spec carries a coherent ``phase.completed`` prefix.
_DRAFTING_COMPLETED: tuple[str, ...] = (
    "premise",
    "treatment",
    "characters",
    "conflict-analysis",
    "setting",
    "reader-fit",
    "stc",
    "chapter-planning",
)
_TARGET_WORDS = 80000


def gate_spec(
    *,
    draft_words: int,
    done_30: bool = False,
    done_50: bool = False,
    done_80: bool = False,
) -> WorkingTreeSpec:
    """Return a coherent-shaped ``drafting`` spec with the named gates and drafts.

    Three chapters each draft ``draft_words`` words against an 80000 target, so the
    drafted ratio is ``3 * draft_words / 80000``. The gate booleans are set
    verbatim, so the caller decides whether the resulting tree is gate-coherent.

    Parameters
    ----------
    draft_words : int
        The per-chapter drafted word count (each chapter targets 80000).
    done_30, done_50, done_80 : bool
        The knitting-gate booleans written to ``[gates.knitting]``.

    Returns
    -------
    WorkingTreeSpec
        The constructed three-chapter drafting spec.
    """
    chapters = tuple(
        ChapterSpec(
            number=index + 1,
            slug=f"chapter-{index + 1:02d}",
            title=f"Chapter {index + 1}",
            target_words=_TARGET_WORDS,
            draft_words=draft_words,
            has_done_flag=False,
        )
        for index in range(3)
    )
    return WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=_DRAFTING_COMPLETED,
        chapters=chapters,
        target_words=_TARGET_WORDS,
        # ``consecutive_clean=0`` keeps the prior coherent on invariant 4c even when
        # the drawn ``draft_words`` is 0 (no drafted chapter to have earned a clean
        # pass), so a property prior isolates invariant 7 (the gate-ratio binding).
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=3,
        done_30=done_30,
        done_50=done_50,
        done_80=done_80,
    )


def gate_lags_ratio_spec() -> WorkingTreeSpec:
    """Return the incoherent repair prior: ratio 0.45, all knitting gates false.

    ``3 * 12000 / 80000 = 0.45`` crosses 0.30 but not 0.50/0.80, so all-false is
    incoherent (invariant 7 mandates ``done_30`` true). ``set-gate --knitting-30``
    repairs it to coherent.
    """
    return gate_spec(draft_words=12000)


def ratio_not_crossed_spec() -> WorkingTreeSpec:
    """Return a coherent sub-threshold prior: ratio 0.15, all knitting gates false.

    ``3 * 4000 / 80000 = 0.15`` is below every threshold, so all-false is coherent.
    Asserting ``done_30`` true here contradicts the ratio (refused, exit 3).
    """
    return gate_spec(draft_words=4000)


def ratio_crossed_coherent_spec() -> WorkingTreeSpec:
    """Return a coherent crossed prior: ratio 0.45 with ``done_30`` already true.

    The idempotent-no-op and false-after-crossed-refusal prior.
    """
    return gate_spec(draft_words=12000, done_30=True)


def build(spec: WorkingTreeSpec, dest: Path) -> Path:
    """Materialise ``spec`` under ``dest`` and return the ``working/`` path."""
    return wc.build_working_tree(spec, dest)
