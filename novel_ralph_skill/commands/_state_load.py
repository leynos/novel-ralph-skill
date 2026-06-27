"""The shared ``working/state.toml`` load boundary and its accessors.

This dependency-free leaf module hosts the single home for *where* a command
looks (``WORKING_DIR_NAME``, :func:`working_dir`, :func:`state_path`), *what
counts* as a state-input fault (:data:`STATE_INPUT_ERRORS`), and *how* a failed
load is rendered as the contract's exit-``3`` error (:func:`_state_input_error`,
:func:`_load_or_state_error`). It is re-exported by
:mod:`novel_ralph_skill.commands.novel_state`, so every command keeps importing
these symbols from ``novel_state`` while the command module stays within the
400-line cap (AGENTS.md "clear file boundaries"), mirroring the
:mod:`novel_ralph_skill.commands._state_mutators` carve-out.

It imports only from :mod:`novel_ralph_skill.state` and
:mod:`novel_ralph_skill.contract.runner` — never from ``novel_state`` — so the
shared actionable-message helper lives here without reversing the
``_state_mutators`` → ``novel_state`` import direction (ExecPlan Decision Log:
the helper must not create an import cycle).
"""

from __future__ import annotations

import pathlib
import tomllib
import typing as typ

from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import load_state

if typ.TYPE_CHECKING:
    from importlib.resources.abc import Traversable

    from novel_ralph_skill.state import State

# The fixed cwd-relative working directory the design records (design line 151);
# the same constant the entry point stamps into the ``RunContext.working_dir``,
# so the file ``check`` reads and the envelope's ``working_dir`` field cannot
# drift (Decision Log B4/B5). There is no ``--working-dir`` flag.
WORKING_DIR_NAME = "working"


def working_dir() -> pathlib.Path:
    """Return the fixed cwd-relative ``working/`` directory (design line 151).

    The single ``WORKING_DIR_NAME``-anchored accessor for the working root, so
    ``_check``, ``init``, and the mutators resolve the same cwd-relative
    directory rather than each rebuilding ``pathlib.Path(WORKING_DIR_NAME)``
    (Decision Log B4/B5).
    """
    return pathlib.Path(WORKING_DIR_NAME)


def resolved_working_dir() -> pathlib.Path:
    """Return the absolute, resolved ``working/`` for the envelope/result label.

    Built on :func:`working_dir` (the cwd-relative resolution rule documented at
    ``_state_load.py:32-48``), this returns ``working_dir().resolve()`` — the
    absolute, normalised path the command actually looked at — so the production
    entry point can stamp *where* it resolved rather than the bare ``"working"``
    token. ``Path.resolve()`` runs in its default non-strict mode, so it
    succeeds even when ``working/`` does not yet exist (the exit-``3`` "no
    working/" arm and ``novel state init`` both rely on this), making a stray
    ``cd`` into ``working/`` visible as ``.../working/working`` rather than a
    silent misresolution (roadmap §6.3.4; Decision Log D2).
    """
    return working_dir().resolve()


def state_path() -> pathlib.Path:
    """Return the fixed cwd-relative ``working/state.toml`` path.

    The single accessor every command routes through (``_check``, ``init``, and
    the ``set-cursor``/``advance-phase``/``recount``/``reconcile`` mutators), so
    the canonical ``state.toml`` path is constructed in exactly one place
    (audit:1.3.5; audit:2.2.2 Finding 3).
    """
    return working_dir() / "state.toml"


# The exceptions a missing or malformed ``state.toml`` raises through
# ``load_state``; each is translated to ``StateInputError`` (the exit-``3``
# state-error channel). Named once here so the "what counts as a state-input
# error" vocabulary has a single home the four later mutators reuse, and so the
# corpus test can pin its own parse-error list against this set rather than
# hand-listing it independently (audit:2.1.2 finding 4).
STATE_INPUT_ERRORS: tuple[type[Exception], ...] = (
    OSError,
    tomllib.TOMLDecodeError,
    KeyError,
    ValueError,
    TypeError,
)

# The shared inspect/repair remedy tail both the present-but-corrupt
# ``_state_input_error`` arm and ``_draft_read_error`` interpolate. Folding it
# into one constant makes the parity those sibling formatters already promise
# structural rather than incidental: a one-sided re-wording can no longer drift
# the tail apart, and only the lead-in separator (a semicolon for the
# ``state.toml`` arm, an em-dash for the draft-read arm) now differs between the
# two messages (Addendum 6.3.5.1).
INSPECT_REPAIR_REMEDY = "inspect and repair it, or restore it from a known-good copy"


def _state_input_error(path: pathlib.Path, exc: Exception) -> StateInputError:
    """Build the actionable exit-``3`` ``StateInputError`` for a failed state load.

    The single source of truth for the message both load boundaries emit — the
    reader loader :func:`_load_or_state_error` here and the mutator loader
    :func:`~novel_ralph_skill.commands._state_mutators._load_document_or_state_error`
    — so the two cannot drift apart (roadmap §6.3.1). It replaces the raw
    operating-system text (an ``Errno`` and a path-as-noise) with prose naming
    where the command looked and how to recover (``scripting-standards.md`` lines
    603-605, 678).

    The two arms carry different remedies (Decision Log D2). A missing ``working/``
    (``path.parent``) or ``state.toml`` means the command was run from the wrong
    directory, so the message names the cwd and points at ``novel state init``. A
    present-but-unparseable file would not be repaired by ``init``, so its message
    names the path and asks for inspection or repair instead. Neither arm leaks an
    ``Errno`` or a traceback; the caller chains ``exc`` via ``from`` for debugging
    while ``exc.messages`` carries only the actionable prose.

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
    through: these formatters render from the path alone and never read it, so the
    caller keeps it solely for ``raise … from exc`` chaining (Decision D2; the
    ``messages`` channel carries only actionable prose — no ``Errno``, no
    ``{exc}`` repr, no traceback).

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
    emit — ``_disk_evidence_or_state_error``, ``_recount``, ``_wordcount``,
    ``_novel_done``, ``_desloppify.source_chapters``, and ``_compile``'s two
    draft-read tails — so they cannot drift apart (roadmap §6.3.5). It is the
    draft-read sibling of :func:`_state_input_error`, replacing the raw
    operating-system text (an ``Errno``, a ``{exc}`` repr, a path-as-noise) with
    prose that names the ``working/`` tree the command read and asks for
    inspection or repair (``scripting-standards.md`` lines 603-605, 678).

    Unlike :func:`_state_input_error`, this formatter has a single arm. A present
    ``working/`` tree whose ``draft.md`` (or ``compiled.md``) is corrupt or
    unreadable is *not* repaired by ``novel state init`` — the tree already
    exists; only an artefact under it is faulted — so the message never advises
    ``init``. It always names ``reported_dir`` and asks the operator to inspect
    or repair the offending artefact, mirroring :func:`_state_input_error`'s
    present-but-corrupt arm but pointing at the ``working/`` tree rather than the
    ``state.toml`` path.

    It does **not** serve the structurally-incomplete ``state.toml`` fault: that
    is a *state-document* fault, not a draft fault, and routes through
    :func:`_state_input_error`'s present-but-corrupt arm instead, which names the
    ``state.toml`` path (the right artefact) and reuses 6.3.1's machinery
    (ExecPlan Decision D7; 6.3.1 Decision D8). It renders from ``reported_dir``
    alone; the caller keeps the caught exception solely for ``raise … from exc``
    chaining, so the ``messages`` channel carries only the actionable prose — no
    ``Errno``, no ``{exc}`` repr, no traceback.

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


def _compile_write_error(target: pathlib.Path) -> StateInputError:
    """Build the exit-``3`` ``StateInputError`` for a faulted manuscript write.

    The write-shaped sibling of :func:`_draft_read_error` (roadmap §6.3.8). When
    :func:`novel compile <novel_ralph_skill.commands._compile.compile_manuscript>`
    cannot write ``working/manuscript/compiled.md`` — typically because the
    ``manuscript/`` directory is absent at write time, raising
    ``FileNotFoundError`` (an ``OSError``) — this replaces the raw operating-system
    text (an ``Errno`` and a ``{exc}`` repr naming a private temp file) with prose
    that names the compiled-manuscript ``target`` and offers a write-shaped remedy
    (``scripting-standards.md`` lines 603-605, 678).

    Like :func:`_draft_read_error` it has a single arm and never advises
    ``novel state init``: the working tree exists; only the write target under it
    is missing, so the remedy is to re-create ``working/manuscript/`` (or restore
    the tree) and re-run, not to re-initialise state (Decision D6 in the 6.3.5
    plan). It keeps the ``"cannot write"`` stem the existing substring test pins.
    It renders from ``target`` alone; the caller keeps the caught exception solely
    for ``raise … from exc`` chaining, so the ``messages`` channel carries only the
    actionable prose — no ``Errno``, no ``{exc}`` repr, no traceback.

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
    cannot read its rule pack — because the ``--pack`` file is absent, unreadable,
    or undecodable, raising ``RulePackFileError`` — this replaces the raw
    operating-system text with prose that names ``pack_path`` and offers a
    file-shaped remedy (``scripting-standards.md`` lines 603-605, 678).

    It takes only the *path*, never the typed ``RulePackFileError`` (Decision D2):
    that error's own message already embeds a raw ``{exc}`` repr
    (``rulepack/parse.py:390``), so consuming it would re-leak the operating-system
    text this task exists to remove. The remedy names ``--pack`` because the path
    is operator-supplied: check it is correct and readable, or omit ``--pack`` to
    fall back to the shipped default pack. It renders from ``pack_path`` alone; the
    caller keeps the caught exception solely for ``raise … from exc`` chaining, so
    the ``messages`` channel carries only the actionable prose — no ``Errno``, no
    ``{exc}`` repr, no traceback.

    Parameters
    ----------
    pack_path : importlib.resources.abc.Traversable
        The resolved rule-pack path the read targeted; named in the message. It
        is a ``Traversable`` (not a bare ``pathlib.Path``) because the shipped
        default pack resolves through ``importlib.resources`` while a ``--pack``
        flag supplies a filesystem ``Path``; both stringify into the message.

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
    §6.3.8). When ``novel desloppify --ledger`` cannot read its device ledger —
    because the ``--ledger`` file is absent, unreadable, or undecodable, raising
    ``LedgerFileError`` — this replaces the raw operating-system text with prose
    that names ``ledger_path`` and offers a file-shaped remedy
    (``scripting-standards.md`` lines 603-605, 678).

    It takes only the *path*, never the typed ``LedgerFileError`` (Decision D2):
    that error's own message already embeds a raw ``{exc}`` repr
    (``ledger/parse.py:311``), so consuming it would re-leak the operating-system
    text this task exists to remove. The remedy names ``--ledger`` because the
    path is operator-supplied: check it is correct and readable. It renders from
    ``ledger_path`` alone; the caller keeps the caught exception solely for
    ``raise … from exc`` chaining, so the ``messages`` channel carries only the
    actionable prose — no ``Errno``, no ``{exc}`` repr, no traceback.

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


def _load_or_state_error(path: pathlib.Path) -> State:
    """Load ``path`` into a ``State``, translating load faults to ``StateInputError``.

    Owns the load-and-translate boundary so callers read as "load → validate →
    build outcome": it maps every member of :data:`STATE_INPUT_ERRORS` to the
    actionable error the shared :func:`_state_input_error` helper builds (the
    exit-``3`` state-error channel), and lets a coherent load return the parsed
    ``State`` unchanged. The mutator loader routes through the same helper, so both
    boundaries emit byte-for-byte identical prose (roadmap §6.3.1). Reusable by the
    four later mutators that hit the same boundary.

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
