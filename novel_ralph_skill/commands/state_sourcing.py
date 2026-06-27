"""The neutral, public state-sourcing home for the command layer.

This module is the single home for *where* a command looks
(:data:`WORKING_DIR_NAME`, :func:`working_dir`, :func:`state_path`), *what
counts* as a state-input fault (:data:`STATE_INPUT_ERRORS`), *how* a failed load
is rendered as the contract's exit-``3`` error (:func:`_state_input_error`,
:func:`load_or_state_error`), and *how* a faulted draft read is guarded
(:func:`draft_read_guard`). Every command — the ``novel state`` subgroup, the
four leaf verbs, and the mutators — imports the seam directly from here, so the
``working/`` location, the state-input fault vocabulary, the load-and-translate
boundary, and the draft-read guard live in exactly one place (AGENTS.md "clear
file boundaries"), mirroring the
:mod:`novel_ralph_skill.commands._state_mutators` carve-out.

``WORKING_DIR_NAME`` itself now originates in
:mod:`novel_ralph_skill.contract.names` — it is a *contract* fact, the token
every envelope stamps into ``working_dir`` — and is re-exported here for
back-compatibility (roadmap 7.3.6 WI2). This module therefore imports only from
:mod:`novel_ralph_skill.state`, :mod:`novel_ralph_skill.contract.runner`, and
:mod:`novel_ralph_skill.contract.names` — never from ``novel_state``. All three
imports point *down* into the ``state`` and ``contract`` layers; this
no-``novel_state``-import rule is a constraint, not an incidental (ExecPlan
Decision Log): the mutator modules import *from* this home, so this home
importing from a command module would reintroduce the cycle the carve-out avoids.
"""

from __future__ import annotations

import contextlib
import pathlib
import tomllib
import typing as typ

from novel_ralph_skill.contract.names import WORKING_DIR_NAME
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import load_state

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from importlib.resources.abc import Traversable

    from novel_ralph_skill.state import State

# The public state-sourcing seam: the neutral home's exported surface. The
# underscore-private actionable-message formatters move with the module but stay
# module-private (only ``load_or_state_error`` and ``draft_read_guard`` are
# public); ``INSPECT_REPAIR_REMEDY`` is module-internal, not part of the seam.
__all__ = [
    "STATE_INPUT_ERRORS",
    "WORKING_DIR_NAME",
    "draft_read_guard",
    "load_or_state_error",
    "resolved_working_dir",
    "state_path",
    "working_dir",
]


def working_dir() -> pathlib.Path:
    """Return the fixed cwd-relative ``working/`` directory (design line 151).

    The single ``WORKING_DIR_NAME``-anchored accessor for the working root, so
    ``_check``, ``init``, and the mutators resolve the same cwd-relative directory
    rather than each rebuilding ``pathlib.Path(WORKING_DIR_NAME)`` (Decision B4/B5).
    """
    return pathlib.Path(WORKING_DIR_NAME)


def resolved_working_dir() -> pathlib.Path:
    """Return the absolute, resolved ``working/`` for the envelope/result label.

    Built on :func:`working_dir`, this returns ``working_dir().resolve()`` — the
    absolute, normalised path the command actually looked at — so the production
    entry point can stamp *where* it resolved rather than the bare ``"working"``
    token. ``Path.resolve()`` runs non-strict, so it succeeds even when
    ``working/`` does not yet exist (the exit-``3`` "no working/" arm and
    ``novel state init`` both rely on this), making a stray ``cd`` into
    ``working/`` visible as ``.../working/working`` (roadmap §6.3.4; Decision D2).
    """
    return working_dir().resolve()


def state_path() -> pathlib.Path:
    """Return the fixed cwd-relative ``working/state.toml`` path.

    The single accessor every command routes through (``_check``, ``init``, and
    the ``set-cursor``/``advance-phase``/``recount``/``reconcile`` mutators), so the
    canonical ``state.toml`` path is built in one place (audit:1.3.5; audit:2.2.2).
    """
    return working_dir() / "state.toml"


# The exceptions a missing or malformed ``state.toml`` raises through
# ``load_state``; each is translated to ``StateInputError`` (the exit-``3``
# state-error channel). Named once here so the "what counts as a state-input
# error" vocabulary has a single home the four mutators and the corpus test
# reuse rather than hand-listing it independently (audit:2.1.2 finding 4).
STATE_INPUT_ERRORS: tuple[type[Exception], ...] = (
    OSError,
    tomllib.TOMLDecodeError,
    KeyError,
    ValueError,
    TypeError,
)

# The shared inspect/repair remedy tail both the present-but-corrupt
# ``_state_input_error`` arm and ``_draft_read_error`` interpolate. Folding it
# into one constant makes their parity structural: a one-sided re-wording can no
# longer drift the tail apart, and only the lead-in separator (a semicolon vs an
# em-dash) now differs between the two messages (Addendum 6.3.5.1).
INSPECT_REPAIR_REMEDY = "inspect and repair it, or restore it from a known-good copy"


def _state_input_error(path: pathlib.Path, exc: Exception) -> StateInputError:
    """Build the actionable exit-``3`` ``StateInputError`` for a failed state load.

    The single source of truth for the message both load boundaries emit — the
    reader loader :func:`load_or_state_error` here and the mutator loader
    :func:`~novel_ralph_skill.commands._state_mutators._load_document_or_state_error`
    — so the two cannot drift apart (roadmap §6.3.1). It replaces the raw
    operating-system text with prose naming where the command looked and how to
    recover (``scripting-standards.md``).

    The two arms carry different remedies (Decision D2). A missing ``working/``
    (``path.parent``) or ``state.toml`` means the command ran from the wrong
    directory, so the message names the cwd and points at ``novel state init``. A
    present-but-unparseable file would not be repaired by ``init``, so its message
    names the path and asks for inspection or repair instead. Neither arm leaks an
    ``Errno``; the caller chains ``exc`` via ``from``.

    Parameters
    ----------
    path : pathlib.Path
        The ``state.toml`` the load targeted; its parent is the reported
        ``working/`` directory.
    exc : Exception
        The caught :data:`STATE_INPUT_ERRORS` member (chained by the caller).

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    if not path.parent.exists() or not path.exists():
        cwd = pathlib.Path.cwd()
        message = (
            f"no novel working/ found in {cwd}; run from the novel root, "
            "or run 'novel state init' to create one"
        )
    else:
        message = f"{path} is unreadable or corrupt; {INSPECT_REPAIR_REMEDY}"
    return StateInputError(message)


def _file_fault_error(message: str) -> StateInputError:
    """Wrap an already-built actionable ``message`` in a ``StateInputError``.

    The single-arm constructor the four path-only file-fault formatters
    (:func:`_draft_read_error`, :func:`_compile_write_error`,
    :func:`_rule_pack_read_error`, :func:`_device_ledger_read_error`) share. Each
    builds its own actionable prose from the offending artefact path and hands it
    here, so the near-identical ``return StateInputError(message)`` tail lives in
    one place (audit:6.3.8 Findings 1-2). The caught exception is not threaded
    through: these formatters render from the path alone, so the caller keeps it
    solely for ``raise … from exc`` chaining — ``messages`` carries only the
    actionable prose, no ``Errno``/``{exc}`` repr/traceback (Decision D2).

    Parameters
    ----------
    message : str
        The actionable prose the formatter built; carried verbatim.

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    return StateInputError(message)


def _draft_read_error(reported_dir: pathlib.Path) -> StateInputError:
    """Build the actionable exit-``3`` ``StateInputError`` for a faulted draft read.

    The single source of truth for the message the six *draft-read* boundaries
    emit (``_disk_evidence_or_state_error``, ``_recount``, ``_wordcount``,
    ``_novel_done``, ``_desloppify.source_chapters``, and ``_compile``'s two tails),
    so they cannot drift apart (roadmap §6.3.5). It is the draft-read sibling of
    :func:`_state_input_error`, replacing the raw operating-system text with prose
    that names the ``working/`` tree and asks for inspection or repair.

    Unlike :func:`_state_input_error`, this formatter has a single arm: a present
    ``working/`` tree whose ``draft.md`` (or ``compiled.md``) is corrupt is *not*
    repaired by ``novel state init`` — the tree already exists — so the message
    never advises ``init`` and instead names ``reported_dir`` and asks the operator
    to inspect or repair the offending artefact. It does **not** serve the
    structurally-incomplete ``state.toml`` fault, which routes through
    :func:`_state_input_error`'s present-but-corrupt arm (Decision D7; 6.3.1 D8).

    It renders from ``reported_dir`` alone, delegating the ``StateInputError`` wrap
    to :func:`_file_fault_error`. The shared guard :func:`draft_read_guard` is the
    single home for the ``try/except STATE_INPUT_ERRORS`` shell that re-raises
    through this formatter.

    Parameters
    ----------
    reported_dir : pathlib.Path
        The ``working/`` tree the command read; named verbatim in the message.

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    message = (
        f"cannot read the drafts under {reported_dir}; a draft.md (or "
        f"compiled.md) is unreadable or corrupt — {INSPECT_REPAIR_REMEDY}"
    )
    return _file_fault_error(message)


@contextlib.contextmanager
def draft_read_guard(reported_dir: pathlib.Path) -> cabc.Iterator[None]:
    """Translate a draft-read fault under ``reported_dir`` to exit ``3``.

    The single home for the ``try/except STATE_INPUT_ERRORS → _draft_read_error``
    shell the draft-read boundaries share (roadmap §7.3.3). Any member of
    :data:`STATE_INPUT_ERRORS` the wrapped read raises is re-raised as the
    actionable exit-``3`` :class:`~novel_ralph_skill.contract.runner.StateInputError`
    :func:`_draft_read_error` builds, chained via ``from`` so ``messages`` carries
    only the prose (no ``Errno``, ``{exc}`` repr, or traceback). An undecodable or
    unreadable ``draft.md`` thus reaches exit ``3`` (design §3.2) and cannot escape
    to the benign exit ``1``. It is the guard sibling of :func:`_draft_read_error`:
    the formatter owns *what* the message says; this manager owns *which* faults
    route to exit ``3``. The benign absent-``draft.md`` fault never reaches it (the
    readers return ``0``/``""``); an out-of-tuple exception propagates unchanged.

    Parameters
    ----------
    reported_dir : pathlib.Path
        The ``working/`` tree the read targeted; named in the actionable message.

    Yields
    ------
    None
        The guard wraps a block; it yields no resource.

    Raises
    ------
    StateInputError
        When the wrapped block raises a :data:`STATE_INPUT_ERRORS` member (the
        exit-``3`` channel), chained from that member via ``from``.

    Examples
    --------
    Route a recount's read fault to exit ``3`` naming the working tree::

        with draft_read_guard(working_dir):
            current, by_chapter = recount_words(working_dir, manifest)
    """
    try:
        yield
    except STATE_INPUT_ERRORS as exc:
        raise _draft_read_error(reported_dir) from exc


def _compile_write_error(target: pathlib.Path) -> StateInputError:
    """Build the exit-``3`` ``StateInputError`` for a faulted manuscript write.

    The write-shaped sibling of :func:`_draft_read_error` (roadmap §6.3.8). When
    :func:`novel compile <novel_ralph_skill.commands._compile.compile_manuscript>`
    cannot write ``working/manuscript/compiled.md`` — typically because the
    ``manuscript/`` directory is absent at write time, raising ``FileNotFoundError``
    — this replaces the raw operating-system text with prose that names the
    compiled-manuscript ``target`` and offers a write-shaped remedy
    (``scripting-standards.md``).

    Like :func:`_draft_read_error` it has a single arm and never advises
    ``novel state init``: the working tree exists; only the write target under it
    is missing, so the remedy is to re-create ``working/manuscript/`` (or restore
    the tree) and re-run (Decision D6 in the 6.3.5 plan). It keeps the
    ``"cannot write"`` stem the substring test pins, delegating the
    ``StateInputError`` wrap to :func:`_file_fault_error`.

    Parameters
    ----------
    target : pathlib.Path
        The compiled-manuscript path the write targeted; named in the message.

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    message = (
        f"cannot write {target}; ensure its parent directory "
        "working/manuscript/ exists (re-create it or restore the working tree), "
        "then re-run the compile"
    )
    return _file_fault_error(message)


def _rule_pack_read_error(pack_path: Traversable) -> StateInputError:
    """Build the actionable exit-``3`` ``StateInputError`` for a faulted rule-pack read.

    The rule-pack file-fault sibling of :func:`_draft_read_error` (roadmap
    §6.3.8). When :func:`novel desloppify <novel_ralph_skill.commands._desloppify>`
    cannot read its rule pack — the ``--pack`` file is absent, unreadable, or
    undecodable, raising ``RulePackFileError`` — this replaces the raw
    operating-system text with prose that names ``pack_path`` and offers a
    file-shaped remedy (``scripting-standards.md``).

    It takes only the *path*, never the typed ``RulePackFileError`` whose own
    message already embeds a raw ``{exc}`` repr that would re-leak the OS text
    (Decision D2). The remedy names ``--pack`` because the path is
    operator-supplied: check it is correct and readable, or omit ``--pack`` to fall
    back to the shipped default pack. It delegates the ``StateInputError`` wrap to
    :func:`_file_fault_error`.

    Parameters
    ----------
    pack_path : importlib.resources.abc.Traversable
        The resolved rule-pack path the read targeted; named in the message. It is
        a ``Traversable`` (not a ``pathlib.Path``) because the shipped default pack
        resolves through ``importlib.resources`` while ``--pack`` supplies a
        filesystem ``Path``; both stringify in.

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    message = (
        f"cannot read rule pack {pack_path}; check the --pack path is correct "
        "and readable, or omit --pack to use the shipped default pack"
    )
    return _file_fault_error(message)


def _device_ledger_read_error(ledger_path: pathlib.Path) -> StateInputError:
    """Build the actionable exit-``3`` ``StateInputError`` for a faulted ledger read.

    The device-ledger file-fault sibling of :func:`_draft_read_error` (roadmap
    §6.3.8). When ``novel desloppify --ledger`` cannot read its device ledger — the
    ``--ledger`` file is absent, unreadable, or undecodable, raising
    ``LedgerFileError`` — this replaces the raw operating-system text with prose
    that names ``ledger_path`` and offers a file-shaped remedy
    (``scripting-standards.md``).

    It takes only the *path*, never the typed ``LedgerFileError`` whose own
    message already embeds a raw ``{exc}`` repr that would re-leak the OS text
    (Decision D2). The remedy names ``--ledger`` because the path is
    operator-supplied: check it is correct and readable. It delegates the wrap to
    :func:`_file_fault_error`.

    Parameters
    ----------
    ledger_path : pathlib.Path
        The device-ledger path the read targeted; named in the message.

    Returns
    -------
    StateInputError
        The actionable error, ready to raise.
    """
    message = (
        f"cannot read device ledger {ledger_path}; check the --ledger path "
        "is correct and readable"
    )
    return _file_fault_error(message)


def load_or_state_error(path: pathlib.Path) -> State:
    """Load ``path`` into a ``State``, translating load faults to ``StateInputError``.

    Owns the load-and-translate boundary so callers read as "load → validate →
    build outcome": it maps every member of :data:`STATE_INPUT_ERRORS` to the
    actionable error the shared :func:`_state_input_error` helper builds (the
    exit-``3`` state-error channel), and lets a coherent load return the parsed
    ``State`` unchanged. The mutator loader routes through the same helper, so both
    boundaries emit identical prose (roadmap §6.3.1).

    Parameters
    ----------
    path : pathlib.Path
        The ``state.toml`` to load.

    Returns
    -------
    State
        The parsed, typed state.

    Raises
    ------
    StateInputError
        When ``path`` is missing or unparseable.
    """
    try:
        return load_state(path)
    except STATE_INPUT_ERRORS as exc:
        raise _state_input_error(path, exc) from exc
