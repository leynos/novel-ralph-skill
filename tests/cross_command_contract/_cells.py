"""The constructible (command, channel) cell table for the cross-command suite.

This module is the spine of Work items 2 and 4 (roadmap 6.3.2): it enumerates,
per command and per exit-code channel, the concrete ``working/`` tree that
constructs that cell, and binds each to its tree-builder so the driven tests can
assert exactly the cells the corpus can reach. The unconstructible (command,
channel) pairs are *not* enumerated here; they are carried as documented gaps in
the package docstring (``tests/cross_command_contract/__init__.py``) and the
developers-guide, the §6.2.1 way (carry combinatorial gaps knowingly rather than
silently; design §9 lines 819-821).

The cells are empirically verified (ExecPlan Surprises & discoveries). The
``done``/``wordcount`` exit-4 channels and every command's exit-1 channel except
``done``'s are unreachable over the corpus and so are absent here by design.

This module is inside ``PYTHON_TARGETS`` (``Makefile``), so it carries a module
docstring, a docstring on every helper, and raises :class:`AssertionError`
directly rather than using a bare ``assert``.
"""

from __future__ import annotations

import typing as typ
from itertools import starmap

from contract_drive_support import build_phase_tree

from novel_ralph_skill.commands import (
    _compile,
    _desloppify,
    _novel_done,
    _wordcount,
    novel_state,
)
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts

# The coherent phase whose tree drives ``novel compile --check`` to exit 0
# (a populated manifest with a matching ``compiled.md``); the eight pre-drafting
# phases refuse with exit 3 and ``drafting`` diverges with exit 4.
_COMPILE_SUCCESS_PHASE: typ.Final[str] = "final-pass"
# A coherent phase the read commands pass over (exit 0): a populated manifest so
# ``novel wordcount`` and ``novel state check`` report a body, not a refusal.
_COHERENT_PHASE: typ.Final[str] = "drafting"
# The pre-drafting phase whose empty manifest drives ``novel compile --check``
# into its *body-produced* state arm (exit 3), distinct from the shared
# no-``working/`` state arm every command shares.
_COMPILE_STATE_PHASE: typ.Final[str] = "premise"
# The ``incoherent_tree`` variant that makes ``novel state check`` find a
# violation and exit 4 (``tests/test_novel_state_check.py``).
_INCOHERENT_VARIANT: typ.Final[str] = "consecutive-clean-over-target"


class ChannelCell(typ.NamedTuple):
    """One driven (command, channel) cell: how to build its tree and drive it.

    Attributes
    ----------
    command_name : str
        The spaced ``novel <verb>`` console name the envelope stamps.
    channel : ExitCode
        The exit-code channel this cell constructs.
    build_app : Callable[[], cyclopts.App]
        The command's ``build_app`` factory.
    argv : list[str]
        The argument vector that drives the command into ``channel``.
    build_working : Callable[[Path], Path] | None
        A builder ``(tmp_path) -> working_path`` materialising the cell's tree,
        or ``None`` for the no-``working/`` state arm where the cwd has no tree.
    """

    command_name: str
    channel: ExitCode
    build_app: cabc.Callable[[], cyclopts.App]
    argv: list[str]
    build_working: cabc.Callable[[Path], Path] | None


def _phase(name: str) -> cabc.Callable[[Path], Path]:
    """Return a builder materialising the coherent ``name`` phase tree.

    Parameters
    ----------
    name : str
        The phase enum member name to build.

    Returns
    -------
    Callable[[Path], Path]
        A callable ``(tmp_path) -> working_path`` building the phase tree.
    """

    def _build(tmp_path: Path) -> Path:
        """Build the coherent ``name`` phase tree under ``tmp_path``."""
        return build_phase_tree(name, tmp_path)

    return _build


def _incoherent(variant: str) -> cabc.Callable[[Path], Path]:
    """Return a builder materialising the named incoherent variant tree.

    The variant is built directly from the corpus ``INCOHERENT_VARIANTS`` mapping
    so the cell needs no fixture; ``novel state check`` finds its violation and
    exits 4 over it.

    Parameters
    ----------
    variant : str
        The ``INCOHERENT_VARIANTS`` key to build.

    Returns
    -------
    Callable[[Path], Path]
        A callable ``(tmp_path) -> working_path`` building the variant tree.
    """

    def _build(tmp_path: Path) -> Path:
        """Build the incoherent ``variant`` tree under ``tmp_path``."""
        import working_corpus as wc

        dest = tmp_path / "incoherent"
        dest.mkdir(exist_ok=True)
        # ``INCOHERENT_VARIANTS`` maps each key to a ``(spec, violation_name)``
        # pair (the ``incoherent_tree`` fixture unpacks the same shape); the
        # first element is the spec to build.
        spec, _violation = wc.INCOHERENT_VARIANTS[variant]
        return wc.build_working_tree(spec, dest)

    return _build


def _em_dash_flood(tmp_path: Path) -> Path:
    """Build a ``drafting`` tree whose first draft floods em dashes (exit-4 cell).

    Overwrites the lowest-numbered chapter's ``draft.md`` with an em-dash flood
    (six em dashes in well under 300 words, past the density threshold of five)
    and clears the other drafts so only the flood drives the verdict, exactly the
    ``tests/test_desloppify_command.py`` construction.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Path
        The materialised ``working/`` path whose ``novel desloppify`` exits 4.
    """
    working = build_phase_tree(_COHERENT_PHASE, tmp_path)
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    if not chapters:
        msg = "drafting tree must contain at least one chapter directory"
        raise AssertionError(msg)
    flood = "word—word—word—word—word—word—word " + "filler " * 20
    chapters[0].joinpath("draft.md").write_text(flood, encoding="utf-8")
    for chapter_dir in chapters[1:]:
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text("plain calm words here\n", encoding="utf-8")
    return working


# The constructible body-produced cells (exit 0/1/4), one per (command, channel)
# the corpus can reach. The shared usage (2) and state (3) arms are enumerated
# separately in ``_error_cells`` because they are command-agnostic.
_BODY_CELLS: typ.Final[tuple[ChannelCell, ...]] = (
    ChannelCell(
        "novel state",
        ExitCode.SUCCESS,
        novel_state.build_app,
        ["check"],
        _phase(_COHERENT_PHASE),
    ),
    ChannelCell(
        "novel state",
        ExitCode.ACTIONABLE_FINDING,
        novel_state.build_app,
        ["check"],
        _incoherent(_INCOHERENT_VARIANT),
    ),
    ChannelCell(
        "novel done",
        ExitCode.BENIGN_NEGATIVE,
        _novel_done.build_app,
        [],
        _phase(_COHERENT_PHASE),
    ),
    ChannelCell(
        "novel wordcount",
        ExitCode.SUCCESS,
        _wordcount.build_app,
        [],
        _phase(_COHERENT_PHASE),
    ),
    ChannelCell(
        "novel compile",
        ExitCode.SUCCESS,
        _compile.build_app,
        ["--check"],
        _phase(_COMPILE_SUCCESS_PHASE),
    ),
    ChannelCell(
        "novel compile",
        ExitCode.STATE_ERROR,
        _compile.build_app,
        ["--check"],
        _phase(_COMPILE_STATE_PHASE),
    ),
    ChannelCell(
        "novel compile",
        ExitCode.ACTIONABLE_FINDING,
        _compile.build_app,
        ["--check"],
        _phase(_COHERENT_PHASE),
    ),
    ChannelCell(
        "novel desloppify",
        ExitCode.SUCCESS,
        _desloppify.build_app,
        [],
        _phase(_COHERENT_PHASE),
    ),
    ChannelCell(
        "novel desloppify",
        ExitCode.ACTIONABLE_FINDING,
        _desloppify.build_app,
        [],
        _em_dash_flood,
    ),
)


def _read_command_specs() -> tuple[
    tuple[str, cabc.Callable[[], cyclopts.App], list[str]], ...
]:
    """Return the five (name, build_app, body-argv) read surfaces.

    Returns
    -------
    tuple[tuple[str, Callable[[], cyclopts.App], list[str]], ...]
        One ``(name, build_app, argv)`` triple per command, the body-producing
        argv the shared usage/state arms append their tokens to.
    """
    return (
        ("novel state", novel_state.build_app, ["check"]),
        ("novel done", _novel_done.build_app, []),
        ("novel wordcount", _wordcount.build_app, []),
        ("novel compile", _compile.build_app, ["--check"]),
        ("novel desloppify", _desloppify.build_app, []),
    )


def _usage_cell(
    name: str, build_app: cabc.Callable[[], cyclopts.App], argv: list[str]
) -> ChannelCell:
    """Return the usage (exit 2) cell for a command: ``--nope`` over its tree.

    An unknown ``--nope`` option appended to the body argv faults at parse before
    the body runs, so a coherent ``working/`` tree leaves only the argv at fault.

    Parameters
    ----------
    name : str
        The spaced console name.
    build_app : Callable[[], cyclopts.App]
        The command's ``build_app`` factory.
    argv : list[str]
        The command's body-producing argv.

    Returns
    -------
    ChannelCell
        The usage-arm cell driving the command to exit 2.
    """
    return ChannelCell(
        name,
        ExitCode.USAGE_ERROR,
        build_app,
        [*argv, "--nope"],
        _phase(_COHERENT_PHASE),
    )


def _state_cell(
    name: str, build_app: cabc.Callable[[], cyclopts.App], argv: list[str]
) -> ChannelCell:
    """Return the state (exit 3) cell for a command: its argv over no ``working/``.

    An absent ``working/`` makes every body raise ``StateInputError`` when it
    tries to load ``working/state.toml``.

    Parameters
    ----------
    name : str
        The spaced console name.
    build_app : Callable[[], cyclopts.App]
        The command's ``build_app`` factory.
    argv : list[str]
        The command's body-producing argv.

    Returns
    -------
    ChannelCell
        The state-arm cell driving the command to exit 3 (``build_working`` None).
    """
    return ChannelCell(name, ExitCode.STATE_ERROR, build_app, argv, None)


_ERROR_CELLS: typ.Final[tuple[ChannelCell, ...]] = (
    *starmap(_usage_cell, _read_command_specs()),
    *starmap(_state_cell, _read_command_specs()),
)

# Every constructible (command, channel) cell, body-produced plus the two shared
# diagnostic arms, in a stable order for parametrize ids.
CONSTRUCTIBLE_CELLS: typ.Final[tuple[ChannelCell, ...]] = (*_BODY_CELLS, *_ERROR_CELLS)

CELL_IDS: typ.Final[tuple[str, ...]] = tuple(
    f"{cell.command_name}-{cell.channel.name}" for cell in CONSTRUCTIBLE_CELLS
)


class MutatorArm(typ.NamedTuple):
    """One ``novel state`` mutator and a complete, valid argv for its state arm.

    A mutator reaches the exit-3 state channel only when its argv is otherwise
    *valid*: a missing required keyword-only argument faults at parse (exit 2)
    and masks the state channel (ExecPlan Surprises). Each ``argv`` here is the
    minimal valid form taken from the existing per-mutator suites, so driving it
    over a cwd with no ``working/`` reaches the ``working/state.toml`` load and
    refuses with exit 3. ``init`` is deliberately absent: it *creates*
    ``working/`` rather than refusing on its absence, so it has no state arm.

    Attributes
    ----------
    verb : str
        The mutator subcommand name (e.g. ``"set-cursor"``).
    argv : list[str]
        A complete, valid argv selecting the mutator and its required arguments.
    """

    verb: str
    argv: list[str]


# A coherent plan JSON for ``set-chapters`` (one chapter), the minimal valid
# ``--chapters`` value (``tests/test_set_chapters_e2e.py``).
_SET_CHAPTERS_PLAN: typ.Final[str] = (
    '[{"number":1,"slug":"c1","title":"C1","target_words":1000}]'
)

# The nine mutators that reach the exit-3 state arm over a cwd with no
# ``working/`` when driven with a complete, valid argv (empirically verified).
MUTATOR_STATE_ARMS: typ.Final[tuple[MutatorArm, ...]] = (
    MutatorArm("set-cursor", ["set-cursor", "--chapter", "1"]),
    MutatorArm("advance-phase", ["advance-phase"]),
    MutatorArm("recount", ["recount"]),
    MutatorArm("reconcile", ["reconcile"]),
    MutatorArm("set-chapters", ["set-chapters", "--chapters", _SET_CHAPTERS_PLAN]),
    MutatorArm("set-gate", ["set-gate", "--knitting-30"]),
    MutatorArm("complete-final-pass", ["complete-final-pass"]),
    MutatorArm("set-fangirl", ["set-fangirl", "--last-chapter", "1"]),
    MutatorArm("set-critic-pass", ["set-critic-pass", "--pass", "1"]),
)


def materialise(cell: ChannelCell, tmp_path: Path) -> Path:
    """Materialise ``cell``'s ``working/`` tree (or a missing one) under ``tmp_path``.

    For a ``build_working`` of ``None`` (the state arm) the cwd must have no
    ``working/``, so this returns a synthetic, *uncreated* ``working`` path under
    a fresh per-cell directory; the ``drive`` fixture reads only ``working.parent``
    and never stats ``working`` itself.

    Parameters
    ----------
    cell : ChannelCell
        The cell whose tree to build.
    tmp_path : Path
        The per-test temporary directory.

    Returns
    -------
    Path
        The ``working/`` path to drive the command from (its parent is the cwd).
    """
    if cell.build_working is None:
        root = tmp_path / "no-working"
        root.mkdir(exist_ok=True)
        return root / "working"  # deliberately NOT created
    return cell.build_working(tmp_path)
