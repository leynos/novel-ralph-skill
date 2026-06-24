"""The pure per-clause ``novel-done`` predicate engine (design §4.2).

:func:`evaluate_done` is the read-only twin of the §4.2 done predicate
(``skill/novel-ralph/references/done-conditions.md`` "Novel-level predicate",
lines 145-186): it decides, clause by clause, whether the novel is finished by
reading the typed :class:`~novel_ralph_skill.state.schema.State` and the on-disk
``working/`` tree, and returns a structured :class:`DoneClauses` carrying one
boolean per clause. It mirrors the shape of
:mod:`novel_ralph_skill.state.disk_evidence` — per-clause functions, a
``chapter-NN`` path derivation shared through
:func:`~novel_ralph_skill.state._disk_paths._chapter_dir_name`, and a
benign-absent / propagate-everything-else fault boundary — but inverts the
verdict polarity: this detector returns ``True`` when a clause *holds*.

The six clause names and their order are fixed by design §4.2's JSON (lines
320-334) and re-spelled here as :data:`DoneClauses` fields:
``phase_is_done``, ``final_pass_complete``, ``all_chapters_flagged``,
``knitting_gates_passed``, ``compile_consistent``, ``no_unresolved_blockers``.

This module makes no narrative judgement and writes nothing to disk on any path
(ADR-001; design §3.3 puts ``novel-done`` in the read-only checker column). The
chapter set is the **manifest** (``state.chapters``), not an outline parse — the
deliberate, design §4.3-justified divergence from the reference recorded in the
ExecPlan Decision Log D-CLAUSES.

Fault boundary (ExecPlan D-FAULT): an *absent* on-disk artefact (no
``done.flag``, no review, no ``critic-notes.md``, no ``compiled.md``) is a benign
"clause not satisfied" and yields a false clause; every other read fault
(``PermissionError``, ``UnicodeDecodeError``) propagates for the command layer to
translate to the exit-``3`` state-error channel. Only :class:`FileNotFoundError`
is absorbed; :func:`pathlib.Path.exists` already maps a missing path to ``False``
without raising, so the ``done.flag``/review/compile existence reads never raise,
and the only read that can fault — the ``critic-notes.md`` body read — is guarded
so an absent file is benign while an undecodable one propagates.
"""

from __future__ import annotations

import dataclasses
import typing as typ

from novel_ralph_skill.state._disk_paths import _chapter_dir_name
from novel_ralph_skill.state.phase import Phase

if typ.TYPE_CHECKING:
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# The three knitting-gate percentages, the single source of truth shared between
# the gate booleans and the ``reviews/knitting-NN.md`` file names so the two
# cannot drift (``done-conditions.md`` lines 164-170; design §5.2 invariant 7).
KNITTING_PERCENTAGES: typ.Final[tuple[int, int, int]] = (30, 50, 80)

# The literal token marking a BLOCKER line resolved (ExecPlan D-BLOCKER). A
# ``critic-notes.md`` line whose stripped text starts with ``BLOCKER`` and does
# not contain this substring is an unresolved blocker. The token is the
# reference's spelling; the corpus pins the substring rule's edge with a
# near-miss spec.
_BLOCKER_PREFIX: typ.Final = "BLOCKER"
# why: the token spells a resolution marker, not a credential; the S105
# hardcoded-password heuristic only sees the literal string assignment.
_RESOLVED_TOKEN: typ.Final = "[resolved]"  # noqa: S105


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DoneClauses:
    """The six per-clause booleans of the §4.2 done predicate.

    Each field is one clause's verdict: ``True`` when the clause holds on disk,
    ``False`` otherwise. The field order is design §4.2's JSON order, which
    :func:`evaluate_done` preserves and :meth:`failed_clause_names` reports in.

    Attributes
    ----------
    phase_is_done : bool
        ``state.phase.current`` is :data:`~novel_ralph_skill.state.phase.Phase.DONE`.
    final_pass_complete : bool
        ``state.gates.final.final_pass_complete`` is ``True``.
    all_chapters_flagged : bool
        Every manifest chapter has an on-disk ``done.flag``.
    knitting_gates_passed : bool
        All three knitting gate booleans are ``True`` and all three
        ``reviews/knitting-NN.md`` exist.
    compile_consistent : bool
        ``manuscript/compiled.md`` exists (existence-only in 3.1.1;
        D-COMPILE-EXISTENCE).
    no_unresolved_blockers : bool
        No manifest chapter's ``critic-notes.md`` carries an unresolved BLOCKER.
    """

    phase_is_done: bool
    final_pass_complete: bool
    all_chapters_flagged: bool
    knitting_gates_passed: bool
    compile_consistent: bool
    no_unresolved_blockers: bool

    @property
    def all_hold(self) -> bool:
        """Whether every clause holds (the six-way conjunction).

        Examples
        --------
        >>> clauses = DoneClauses(
        ...     phase_is_done=True,
        ...     final_pass_complete=True,
        ...     all_chapters_flagged=True,
        ...     knitting_gates_passed=True,
        ...     compile_consistent=True,
        ...     no_unresolved_blockers=True,
        ... )
        >>> clauses.all_hold
        True
        """
        return all(getattr(self, field.name) for field in dataclasses.fields(self))

    @property
    def failed_clause_names(self) -> tuple[str, ...]:
        """The names of the false clauses, in design §4.2 order.

        The ordered tuple feeds the envelope's human ``messages`` so an operator
        sees exactly which clauses are unmet, in the canonical clause order.

        Examples
        --------
        >>> clauses = DoneClauses(
        ...     phase_is_done=False,
        ...     final_pass_complete=True,
        ...     all_chapters_flagged=True,
        ...     knitting_gates_passed=True,
        ...     compile_consistent=False,
        ...     no_unresolved_blockers=True,
        ... )
        >>> clauses.failed_clause_names
        ('phase_is_done', 'compile_consistent')
        """
        return tuple(
            field.name
            for field in dataclasses.fields(self)
            if not getattr(self, field.name)
        )

    def as_result(self) -> dict[str, bool]:
        """Return the clauses as the envelope ``result`` mapping in §4.2 order.

        Examples
        --------
        >>> clauses = DoneClauses(
        ...     phase_is_done=True,
        ...     final_pass_complete=False,
        ...     all_chapters_flagged=True,
        ...     knitting_gates_passed=True,
        ...     compile_consistent=True,
        ...     no_unresolved_blockers=True,
        ... )
        >>> clauses.as_result()["final_pass_complete"]
        False
        """
        return {
            field.name: getattr(self, field.name) for field in dataclasses.fields(self)
        }


def phase_is_done(state: State) -> bool:
    """Return whether ``state.phase.current`` is the terminal ``done`` phase."""
    return state.phase.current is Phase.DONE


def final_pass_complete(state: State) -> bool:
    """Return whether the ``[gates.final]`` final-pass flag is set."""
    return state.gates.final.final_pass_complete


def all_chapters_flagged(state: State, working_dir: Path) -> bool:
    """Return whether every manifest chapter has an on-disk ``done.flag``.

    Each manifest chapter (``state.chapters``) must carry a
    ``manuscript/chapter-NN/done.flag``; an absent flag is a benign false clause,
    not a fault. An empty manifest holds vacuously.
    """
    manuscript = working_dir / "manuscript"
    return all(
        (manuscript / _chapter_dir_name(chapter.number) / "done.flag").exists()
        for chapter in state.chapters
    )


def knitting_gates_passed(state: State, working_dir: Path) -> bool:
    """Return whether the three knitting gates are true and their reviews exist.

    All three ``state.gates.knitting.done_30/done_50/done_80`` booleans must be
    ``True`` **and** all three ``reviews/knitting-{30,50,80}.md`` files must
    exist (D-CLAUSES). The percentages and the gate booleans are taken from the
    one :data:`KNITTING_PERCENTAGES` source so the file names and the booleans
    cannot drift.
    """
    knitting = state.gates.knitting
    gate_for = {
        30: knitting.done_30,
        50: knitting.done_50,
        80: knitting.done_80,
    }
    reviews = working_dir / "reviews"
    return all(
        gate_for[percentage] and (reviews / f"knitting-{percentage}.md").exists()
        for percentage in KNITTING_PERCENTAGES
    )


def compile_consistent_exists(working_dir: Path) -> bool:
    """Return whether ``manuscript/compiled.md`` exists.

    Existence-only in 3.1.1: a present ``compiled.md`` holds, an absent one does
    not, so an *absent* compile can never be declared "done" (closing the
    exit-``0`` lie). Roadmap task 3.1.2 adds the hash comparison and the
    exit-``4`` carve-out so a present-but-stale compile is caught
    (ExecPlan D-COMPILE-EXISTENCE; the stale window is Risk R-STALE).
    """
    return (working_dir / "manuscript" / "compiled.md").exists()


def _contains_unresolved_blocker(notes_path: Path) -> bool:
    """Return whether ``notes_path`` carries an unresolved BLOCKER line.

    A line whose stripped text starts with ``BLOCKER`` (case-sensitive, the
    reference's spelling) and does not contain the literal ``[resolved]`` token
    is an unresolved blocker (ExecPlan D-BLOCKER). An absent file is clean (no
    blockers), exactly as the reference treats a missing notes file; every other
    read fault (an undecodable body, a permission error) propagates for the
    command layer to route to exit ``3``.
    """
    try:
        body = notes_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    return any(
        stripped.startswith(_BLOCKER_PREFIX) and _RESOLVED_TOKEN not in stripped
        for stripped in (line.strip() for line in body.splitlines())
    )


def no_unresolved_blockers(state: State, working_dir: Path) -> bool:
    """Return whether no manifest chapter has an unresolved BLOCKER finding.

    Scans each manifest chapter's ``manuscript/chapter-NN/critic-notes.md`` for
    an unresolved BLOCKER line (D-BLOCKER). An absent ``critic-notes.md`` is
    clean; an empty manifest holds vacuously.
    """
    manuscript = working_dir / "manuscript"
    return not any(
        _contains_unresolved_blocker(
            manuscript / _chapter_dir_name(chapter.number) / "critic-notes.md"
        )
        for chapter in state.chapters
    )


def evaluate_done(state: State, working_dir: Path) -> DoneClauses:
    """Return the six-clause :class:`DoneClauses` for ``state`` against disk.

    Assembles each clause in design §4.2 order. The two state-only clauses read
    ``state``; the four disk-aware clauses read the materialised ``working/``
    tree. This is a checker: it writes nothing on any path (ADR-001).

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` to evaluate.
    working_dir : pathlib.Path
        The materialised ``working/`` directory holding ``manuscript/`` and
        ``reviews/``.

    Returns
    -------
    DoneClauses
        One boolean per clause; :attr:`DoneClauses.all_hold` is ``True`` iff the
        novel is done.

    Raises
    ------
    OSError
        When a non-absent on-disk artefact is unreadable (e.g. a
        ``PermissionError`` or an undecodable ``critic-notes.md``); the command
        layer maps this to the exit-``3`` state-error channel (D-FAULT).
    """
    return DoneClauses(
        phase_is_done=phase_is_done(state),
        final_pass_complete=final_pass_complete(state),
        all_chapters_flagged=all_chapters_flagged(state, working_dir),
        knitting_gates_passed=knitting_gates_passed(state, working_dir),
        compile_consistent=compile_consistent_exists(working_dir),
        no_unresolved_blockers=no_unresolved_blockers(state, working_dir),
    )
