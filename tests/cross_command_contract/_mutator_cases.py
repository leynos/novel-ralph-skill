"""Per-mutator success and refusal cases for the mutator-identity pin (WI5).

This module binds each ``novel state`` mutator to a complete, valid argv and a
tree-builder for its success path and one *content* refusal path (an incoherent
cursor, a skipped phase, a pre-existing ``state.toml`` for ``init``, a
below-threshold gate). The constructions reuse the proven trees the existing
per-mutator suites build (``tests/test_novel_state_mutator_snapshots.py``,
``tests/test_novel_state_mutators.py``) so the cross-command identity proof rides
on tree shapes already verified, never re-derived. The cross-command
state-channel refusal over a cwd with no ``working/`` is proven for *all* nine
state-reaching mutators by ``test_error_channels`` (``MUTATOR_STATE_ARMS``); this
module adds the *content* refusal and the *success* path each mutator owns.

This module is inside ``PYTHON_TARGETS`` (``Makefile``), so it carries a module
docstring, a docstring on every helper, and raises :class:`AssertionError`
directly rather than using a bare ``assert``.
"""

from __future__ import annotations

import typing as typ

import working_corpus as wc
from _gate_drafting_fixtures import ratio_crossed_coherent_spec, ratio_not_crossed_spec

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

# A coherent plan JSON for ``set-chapters`` success (one chapter), the minimal
# valid ``--chapters`` value (``tests/test_set_chapters_e2e.py``).
_SET_CHAPTERS_PLAN: typ.Final[str] = (
    '[{"number":1,"slug":"c1","title":"C1","target_words":1000}]'
)


class MutatorCase(typ.NamedTuple):
    """One mutator's success and refusal drive specs for the identity proof.

    Attributes
    ----------
    verb : str
        The mutator subcommand name (e.g. ``"set-cursor"``).
    success_argv : list[str]
        A complete, valid argv driving the mutator's success path (exit 0).
    success_tree : Callable[[Path], Path]
        A builder ``(tmp_path) -> working_path`` for the success tree.
    refusal_argv : list[str]
        A complete, valid argv driving a *content* refusal (exit 3).
    refusal_tree : Callable[[Path], Path]
        A builder ``(tmp_path) -> working_path`` for the refusal tree.
    """

    verb: str
    success_argv: list[str]
    success_tree: cabc.Callable[[Path], Path]
    refusal_argv: list[str]
    refusal_tree: cabc.Callable[[Path], Path]


def _phase(name: str) -> cabc.Callable[[Path], Path]:
    """Return a builder materialising the coherent ``name`` phase tree."""

    def _build(tmp_path: Path) -> Path:
        """Build the coherent ``name`` phase tree under a fresh subdirectory."""
        dest = tmp_path / f"phase-{name}"
        dest.mkdir(exist_ok=True)
        return wc.build_working_tree(wc.PHASE_STATES[name], dest)

    return _build


def _incoherent(variant: str) -> cabc.Callable[[Path], Path]:
    """Return a builder materialising the named incoherent variant tree."""

    def _build(tmp_path: Path) -> Path:
        """Build the incoherent ``variant`` tree under a fresh subdirectory."""
        dest = tmp_path / f"incoherent-{variant}"
        dest.mkdir(exist_ok=True)
        spec, _violation = wc.INCOHERENT_VARIANTS[variant]
        return wc.build_working_tree(spec, dest)

    return _build


def _recount_tree(tmp_path: Path) -> Path:
    """Build a two-chapter ``drafting`` tree with wrong hand-typed counts.

    Mirrors ``tests/test_novel_state_mutator_snapshots.py::_recount_tree``: the
    hand-typed ``[word_counts]`` is deliberately wrong, so ``recount`` corrects
    it and exits 0.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory.

    Returns
    -------
    Path
        The materialised ``working/`` path ``recount`` succeeds over.
    """
    dest = tmp_path / "recount"
    dest.mkdir(exist_ok=True)
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in ((1, 3), (2, 5))
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        by_chapter_override={"01": 999, "02": 999},
        current_words_override=1998,
    )
    return wc.build_working_tree(spec, dest)


def _gate_tree(
    spec_factory: cabc.Callable[[], wc.WorkingTreeSpec], label: str
) -> cabc.Callable[[Path], Path]:
    """Return a builder for a gate-drafting spec from ``_gate_drafting_fixtures``."""

    def _build(tmp_path: Path) -> Path:
        """Build the gate-drafting tree under a fresh subdirectory."""
        dest = tmp_path / f"gate-{label}"
        dest.mkdir(exist_ok=True)
        return wc.build_working_tree(spec_factory(), dest)

    return _build


def _bare_cwd(tmp_path: Path) -> Path:
    """Return a fresh empty directory's ``working/`` path (uncreated).

    Used for ``init``'s success cwd (it creates ``working/`` itself, so its cwd
    must have none) and for the ``reconcile`` state-arm refusal (its only exit-3
    channel is the no-``working/`` load fault). The ``drive`` fixture reads only
    ``working.parent``, so this returns an uncreated ``working`` path under a
    fresh empty directory.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory.

    Returns
    -------
    Path
        An uncreated ``working/`` path whose parent is an empty cwd.
    """
    dest = tmp_path / "bare"
    dest.mkdir(exist_ok=True)
    return dest / "working"


# The ten mutators' success and refusal cases, every refusal a real exit-3 cell.
# ``init`` succeeds over a bare cwd (it creates ``working/``) and refuses when
# ``state.toml`` pre-exists; the cursor/phase/gate/chapter mutators succeed over a
# coherent phase and refuse on an incoherent prior state; ``reconcile`` is exit
# 0/4 by design (it never refuses an incoherent tree with exit 3), so its exit-3
# refusal is the shared no-``working/`` load fault — the same state-channel
# skeleton every command shares.
MUTATOR_CASES: typ.Final[tuple[MutatorCase, ...]] = (
    MutatorCase(
        "init",
        ["init", "--title", "T", "--slug", "s"],
        _bare_cwd,
        ["init", "--title", "T", "--slug", "s"],
        _phase("drafting"),
    ),
    MutatorCase(
        "set-cursor",
        ["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"],
        _phase("drafting"),
        ["set-cursor", "--chapter", "99"],
        _phase("drafting"),
    ),
    MutatorCase(
        "advance-phase",
        ["advance-phase"],
        _phase("premise"),
        ["advance-phase"],
        _incoherent("completed-prefix-gap"),
    ),
    MutatorCase(
        "recount",
        ["recount"],
        _recount_tree,
        ["recount"],
        _incoherent("completed-prefix-gap"),
    ),
    # ``reconcile`` is exit 0/4 by design (§3.1): a content breach yields the
    # *actionable-finding* (exit 4, action ``refuse``) channel, not exit 3 — it
    # never refuses an incoherent tree with exit 3, it reconciles or finds. Its
    # only exit-3 channel is the shared no-``working/`` load fault, so its
    # identity refusal is that state arm (the same skeleton every command shares),
    # not a content breach.
    MutatorCase(
        "reconcile",
        ["reconcile"],
        _phase("drafting"),
        ["reconcile"],
        _bare_cwd,
    ),
    MutatorCase(
        "set-chapters",
        ["set-chapters", "--chapters", _SET_CHAPTERS_PLAN],
        _phase("chapter-planning"),
        ["set-chapters", "--chapters", _SET_CHAPTERS_PLAN],
        _incoherent("completed-prefix-gap"),
    ),
    MutatorCase(
        "set-gate",
        ["set-gate", "--knitting-30"],
        _gate_tree(ratio_crossed_coherent_spec, "crossed"),
        ["set-gate", "--knitting-30"],
        _gate_tree(ratio_not_crossed_spec, "not-crossed"),
    ),
    MutatorCase(
        "complete-final-pass",
        ["complete-final-pass"],
        _phase("final-pass"),
        ["complete-final-pass"],
        _incoherent("completed-prefix-gap"),
    ),
    MutatorCase(
        "set-fangirl",
        ["set-fangirl", "--last-chapter", "1"],
        _phase("drafting"),
        ["set-fangirl", "--last-chapter", "4"],
        _phase("drafting"),
    ),
    MutatorCase(
        "set-critic-pass",
        ["set-critic-pass", "--pass", "2"],
        _phase("drafting"),
        ["set-critic-pass", "--pass", "0"],
        _phase("drafting"),
    ),
)
