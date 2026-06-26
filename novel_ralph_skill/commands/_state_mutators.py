"""Body functions and load helpers for the ``novel-state`` state mutators.

This module hosts the *write* mutators of ``novel-state`` — ``set-cursor`` and
``advance-phase`` (roadmap task 2.2.2; design §4.1, §3.2, §5.2) — and the two
document-load fault helpers they share. It lives beside
:mod:`novel_ralph_skill.commands.novel_state` (which keeps the read-only
``check`` checker and the ``init`` builder-mutator) so the command module stays
within the 400-line cap once three mutator bodies land (AGENTS.md "clear file
boundaries"; ExecPlan Risk "module size").

The mutators load ``state.toml`` through :func:`load_document` (``tomlkit``), not
``load_state`` (``tomllib``), because they edit the live
:class:`~tomlkit.TOMLDocument` in place and re-write it losslessly (ADR-002;
design §5.3). Both the load and the typed-view derivation are routed to the
exit-``3`` channel: :func:`_load_document_or_state_error` wraps the
``load_document`` call and :func:`_state_view_or_state_error` wraps the
``document_to_state`` call, each under the **existing** ``STATE_INPUT_ERRORS``
tuple. The second wrap is load-bearing: a ``state.toml`` that is valid TOML but
structurally incomplete passes ``load_document`` cleanly and fails only inside
``document_to_state`` → ``parse_state``; left unwrapped that fault would exit
``1`` (``contract/runner.py:run`` catches only ``CycloptsError`` and
``StateInputError``), breaching the load-bearing exit-``3`` refusal contract
(design §3.2; ExecPlan Decision Log D8, BR2-1).

Every mutator validates the **proposed** state with :func:`validate_state` before
writing and refuses (exit ``3``, no write) when it would violate any §5.2
invariant, so a refusal leaves the prior ``state.toml`` byte-for-byte intact
(design §3.4; ExecPlan Constraint "Validate before persist").
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands.novel_state import (
    STATE_INPUT_ERRORS,
    _state_input_error,
)
from novel_ralph_skill.commands.novel_state import (
    state_path as _state_path,
)
from novel_ralph_skill.commands.novel_state import (
    working_dir as _working_dir,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import (
    PHASE_ORDER,
    Phase,
    document_to_state,
    load_document,
    validate_state,
    write_document_atomically,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import pathlib

    from tomlkit import TOMLDocument

    from novel_ralph_skill.state import State

# ``_state_path`` and ``_working_dir`` are re-exported from
# :mod:`novel_ralph_skill.commands.novel_state` (the single accessor home) for
# the sibling ``_recount``/``_reconcile`` mutator modules, which import them from
# here; ``__all__`` marks the re-export so the unused-import lint does not fire.
__all__ = [
    "_load_document_or_state_error",
    "_refuse_if_incoherent",
    "_state_path",
    "_state_view_or_state_error",
    "_working_dir",
    "advance_phase",
    "set_cursor",
]


def _load_document_or_state_error(path: pathlib.Path) -> TOMLDocument:
    """Load ``path`` into a ``tomlkit`` document, mapping faults to exit ``3``.

    Wraps :func:`load_document` under the same ``STATE_INPUT_ERRORS`` tuple the
    read-only loader uses; ``tomlkit`` parse faults are ``ValueError`` subclasses
    and ``parse_state``'s ``NonExistentKey`` is a ``KeyError`` subclass, so the
    existing tuple subsumes the document path without extension (ExecPlan
    Decision Log D4).

    The faulted-load message is built by the shared
    :func:`~novel_ralph_skill.commands.novel_state._state_input_error` helper —
    the same one the reader/checker loader
    (:func:`~novel_ralph_skill.commands.novel_state._load_or_state_error`) routes
    through — so the mutator and reader boundaries emit byte-for-byte identical
    actionable prose and cannot drift apart (roadmap §6.3.1).

    Parameters
    ----------
    path : pathlib.Path
        The ``state.toml`` to load.

    Returns
    -------
    tomlkit.TOMLDocument
        The style-preserving document.

    Raises
    ------
    StateInputError
        When ``path`` is missing or unparseable (the exit-``3`` channel).
    """
    try:
        return load_document(path)
    except STATE_INPUT_ERRORS as exc:
        raise _state_input_error(path, exc) from exc


def _state_view_or_state_error(document: TOMLDocument) -> State:
    """Derive the typed ``State`` read view, mapping faults to exit ``3``.

    A document that parses as TOML may still be structurally incomplete (a
    missing required table or key, or a bad phase string).
    ``document_to_state`` → ``parse_state`` then raises
    ``NonExistentKey``/``KeyError``/``TypeError``, and ``Phase(...)`` raises
    ``ValueError``. ``contract/runner.py:run`` catches only ``CycloptsError`` and
    ``StateInputError``, so an unwrapped fault here would exit ``1``, not the
    contract's ``3``. Wrapping the call under the same ``STATE_INPUT_ERRORS``
    tuple routes it to the exit-``3`` channel (ExecPlan Decision Log D8; BR2-1).

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        A loaded ``state.toml`` document.

    Returns
    -------
    State
        The typed, frozen read view.

    Raises
    ------
    StateInputError
        When the document is structurally incomplete (the exit-``3`` channel).
    """
    try:
        return document_to_state(document)
    except STATE_INPUT_ERRORS as exc:
        msg = f"state is structurally incomplete: {exc}"
        raise StateInputError(msg) from exc


def _refuse_if_incoherent(
    state: State,
    *,
    context: str,
    remedy: cabc.Callable[[State], cabc.Sequence[str]] | None = None,
) -> None:
    """Raise :class:`StateInputError` naming any §5.2 violations of ``state``.

    Centralises the validate-before-persist refusal so each mutator reads as
    "edit → derive view → refuse-if-incoherent → write". The raised error carries
    the breached invariant names first in its ``messages`` (the exit-``3`` ``run``
    arm emits only ``messages``, no ``result``), then each violation's detail, so
    an operator can name the breached invariant (design §4.1; ExecPlan Constraint
    "Validate before persist").

    A caller may pass a command-specific ``remedy`` callable. When the verdict is
    non-empty and ``remedy`` returns a non-empty sequence, its lines are appended
    after the per-violation details, so the operator advice (a CLI verb to run,
    say) lives in the command layer rather than the pure validator (design §3.3
    checker/mutator split). The keyword defaults to ``None``, so every existing
    caller is unchanged; ``remedy`` is called exactly once, on the same ``state``
    just validated, avoiding a second ``validate_state`` pass on the refusal path.

    Parameters
    ----------
    state : State
        The proposed (or prior) state to validate.
    context : str
        A short phrase naming the refused transition, for the message prefix.
    remedy : collections.abc.Callable[[State], collections.abc.Sequence[str]] | None
        An optional command-specific advice builder. Receives the validated
        ``state`` and returns the remedy lines to append (an empty sequence when
        it has no advice for this breach). ``None`` (the default) appends nothing.

    Raises
    ------
    StateInputError
        When ``validate_state(state)`` is non-empty (the exit-``3`` refusal).
    """
    verdict = validate_state(state)
    if not verdict:
        return
    names = ", ".join(violation.invariant for violation in verdict)
    summary = f"{context} would violate: {names}"
    # The envelope's ``messages`` carry the invariant names first (so an operator
    # and the refusal tests can name the breached invariant on the exit-3
    # channel), then each violation's detail, then any command-specific remedy
    # lines. The exit-3 ``run`` arm emits only ``messages`` (no ``result``), so
    # all of this prose must ride here.
    details = [violation.detail for violation in verdict]
    if remedy is not None:
        details.extend(remedy(state))
    raise StateInputError(summary, *details)


def set_cursor(*, chapter: int, scene: int, beat: int) -> CommandOutcome:
    """Set the drafting cursor; refuse an incoherent cursor with exit ``3``.

    Loads ``working/state.toml`` through the ``tomlkit`` document path, edits the
    ``[drafting]`` cursor scalars in place, validates the proposed state against
    the §5.2 invariants, and writes atomically only when it is coherent. An
    incoherent cursor (a chapter past the manifest, or a scene/beat set while the
    cursor names no chapter) refuses with exit ``3`` and writes nothing, leaving
    the prior ``state.toml`` byte-for-byte intact (design §4.1, §5.2 invariant 6,
    §3.2).

    Parameters
    ----------
    chapter : int
        The proposed ``[drafting].current_chapter``.
    scene : int
        The proposed ``[drafting].current_scene``.
    beat : int
        The proposed ``[drafting].current_beat``.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the coherent cursor is written, carrying the
        written cursor in ``result`` —
        ``{"current_chapter", "current_scene", "current_beat"}``. This is the
        write-shaped success vocabulary: a mutator names what it changed and
        never echoes the ``check`` query's ``violations`` read shape (design
        §3.1, §3.3; audit-2.2.2 Finding 2).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, or the proposed cursor
        is incoherent (each the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    # Derive the typed view first to prove the document is structurally complete
    # (a missing ``[drafting]`` table would otherwise make the scalar edit below
    # raise ``NonExistentKey`` uncaught -> exit 1, breaching the exit-3 contract;
    # BR2-1). The view is discarded; the document remains the write source.
    _state_view_or_state_error(document)
    drafting = document["drafting"]
    drafting["current_chapter"] = chapter
    drafting["current_scene"] = scene
    drafting["current_beat"] = beat
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="set-cursor")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={
            "current_chapter": chapter,
            "current_scene": scene,
            "current_beat": beat,
        },
        messages=[f"cursor set to chapter={chapter}, scene={scene}, beat={beat}"],
    )


def _successor_or_state_error(current: Phase) -> Phase:
    """Return the phase after ``current``; refuse the terminal phase with exit ``3``.

    ``advance-phase`` always moves to the immediate successor, so advancing from
    the terminal ``done`` (which has no successor in ``PHASE_ORDER``) is itself an
    illegal transition (design §5.1; ExecPlan Risk "advance-phase past done").

    Parameters
    ----------
    current : Phase
        The prior ``phase.current``.

    Returns
    -------
    Phase
        The immediate successor.

    Raises
    ------
    StateInputError
        When ``current`` is the terminal phase (the exit-``3`` refusal).
    """
    index = PHASE_ORDER.index(current)
    if index + 1 >= len(PHASE_ORDER):
        msg = (
            f"no phase after {current.value!r}; cannot advance from the terminal phase"
        )
        raise StateInputError(msg)
    return PHASE_ORDER[index + 1]


def advance_phase() -> CommandOutcome:
    """Advance ``phase.current`` to the next member; refuse skips with exit ``3``.

    Loads the document, refuses an already-incoherent prior state (the explicit
    guard that realises "refuses out-of-order completion": because the body takes
    no argument it can only ever move to the immediate successor, so the only
    out-of-order refusal is a prior whose ``completed`` is already not the
    in-order prefix; ExecPlan Decision Log D7), refuses advancing from the
    terminal ``done``, and refuses advancing into ``drafting`` with an empty
    chapter manifest (design §4.1 line 266 — a precondition the §5.2 validator
    does not own). On a coherent advance it appends the just-left phase to
    ``phase.completed``, sets ``phase.current`` to the successor, validates the
    proposed state (defence in depth), and writes atomically; every refusal exits
    ``3`` and writes nothing (design §4.1, §3.2, §5.1).

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the advance is written, carrying the transition
        in ``result`` — ``{"from", "to"}`` (the ``Phase.value`` strings). These
        are *transition labels* describing the move, not on-disk schema keys:
        ``state.toml`` has no ``[from]``/``[to]`` table; the persisted form is
        ``phase.current`` plus ``phase.completed``. As a mutator it names what it
        changed and never echoes the ``check`` query's ``violations`` read shape
        (design §3.1, §3.3; audit-2.2.2 Finding 2).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, the prior state is
        incoherent, the prior phase is terminal, or the advance into ``drafting``
        has an empty manifest (each the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    prior = _state_view_or_state_error(document)
    # Refuse an already-incoherent prior: an advance never launders a broken prior
    # into a coherent successor (Decision Log D7).
    _refuse_if_incoherent(prior, context="advance-phase from an incoherent state")
    successor = _successor_or_state_error(prior.phase.current)
    if successor is Phase.DRAFTING and not prior.chapters:
        msg = "advancing into drafting requires a populated chapter manifest"
        raise StateInputError(msg)
    document["phase"]["completed"].append(prior.phase.current.value)
    document["phase"]["current"] = successor.value
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="advance-phase")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={
            "from": prior.phase.current.value,
            "to": successor.value,
        },
        messages=[
            f"advanced phase from {prior.phase.current.value!r} to {successor.value!r}"
        ],
    )
