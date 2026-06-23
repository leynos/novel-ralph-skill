"""The read-only ``novel-state`` subcommand app and its working directory.

This module hosts the read-only ``novel-state`` Cyclopts app (design §4.1) and
its ``WORKING_DIR_NAME`` default. It is the first command on the real ``run``
path, so the conventions it sets — reading state from the fixed cwd-relative
``working/`` directory (design line 151) — are the ones the four later commands
inherit. The command-agnostic ``--human`` pre-parse the entry point performs
before :func:`novel_ralph_skill.contract.runner.run` is reached no longer lives
here; it is the shared
:func:`novel_ralph_skill.contract.parse_global_flags` splitter (ADR-003 §3.1),
which every command imports from the contract package rather than from a sibling
command module.

The ``check`` subcommand validates the §5.2 pure-state invariants (roadmap task
2.1.2) without writing (the checker half of the §5.4 checker/mutator split). It
loads ``./working/state.toml`` relative to the process cwd, applies
:func:`novel_ralph_skill.state.validate_state`, and returns a
:class:`~novel_ralph_skill.contract.runner.CommandOutcome`: exit ``0`` with an
empty ``result.violations`` when the state is coherent, or exit ``4``
(``ACTIONABLE_FINDING``) naming the violated invariants when it is not. A
missing or unparseable ``state.toml`` raises
:class:`~novel_ralph_skill.contract.runner.StateInputError` for the exit-``3``
state-error channel. The disk-evidence invariants (§5.4) are task 2.3.2's and
are not checked here.
"""

from __future__ import annotations

import pathlib
import tomllib
import typing as typ

import cyclopts

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import load_state, validate_state

if typ.TYPE_CHECKING:
    from novel_ralph_skill.state import State

# The fixed cwd-relative working directory the design records (design line 151);
# the same constant the entry point stamps into the ``RunContext.working_dir``,
# so the file ``check`` reads and the envelope's ``working_dir`` field cannot
# drift (Decision Log B4/B5). There is no ``--working-dir`` flag.
WORKING_DIR_NAME = "working"

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


def _load_or_state_error(path: pathlib.Path) -> State:
    """Load ``path`` into a ``State``, translating load faults to ``StateInputError``.

    Owns the load-and-translate boundary so callers read as "load → validate →
    build outcome": it maps every member of :data:`STATE_INPUT_ERRORS` to a
    :class:`~novel_ralph_skill.contract.runner.StateInputError` (the exit-``3``
    state-error channel) and lets a coherent load return the parsed ``State``
    unchanged. Reusable by the four later mutators that hit the same boundary.

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
        msg = f"cannot load {path}: {exc}"
        raise StateInputError(msg) from exc


def _check() -> CommandOutcome:
    """Validate ``./working/state.toml`` against the §5.2 pure-state invariants.

    Reads the fixed cwd-relative ``working/state.toml`` (design line 151),
    parses it, and applies :func:`novel_ralph_skill.state.validate_state`. A
    coherent state returns exit ``0``; a violation returns exit ``4`` naming the
    breached invariants in ``result.violations``. This is a checker: it writes
    nothing (design §3.3).

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with an empty ``violations`` list when coherent, or
        ``ExitCode.ACTIONABLE_FINDING`` naming the violated invariants.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable (the exit-``3``
        state-error channel).
    """
    path = pathlib.Path(WORKING_DIR_NAME) / "state.toml"
    state = _load_or_state_error(path)
    verdict = validate_state(state)
    # One verdict-driven constructor: an empty verdict is success, any violation
    # is an actionable finding. Computing the verdict once and projecting it into
    # a single outcome makes "empty verdict means success" a single expression
    # rather than two parallel constructors (audit:2.1.2 finding 5).
    code = ExitCode.SUCCESS if not verdict else ExitCode.ACTIONABLE_FINDING
    return CommandOutcome(
        code=code,
        result={"violations": [violation.invariant for violation in verdict]},
        messages=[violation.detail for violation in verdict] or ["state is coherent"],
    )


def build_app() -> cyclopts.App:
    """Build the ``novel-state`` Cyclopts app with its ``check`` subcommand.

    Wired with ``result_action="return_value", exit_on_error=False,
    print_error=False, help_on_error=False`` so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope
    (the ``wrapper_app`` fixture's contract). Exposes the read-only ``check``
    subcommand; the mutators (``init``/``set-cursor``/``advance-phase``/
    ``recount``/``reconcile``) are later tasks and are not registered here.

    The signature is deliberately zero-argument and stable (later tasks import
    it): the ``check`` body resolves its working directory from the process cwd
    (the fixed ``working/`` constant, Decision Log B4/B5), so the builder needs
    no per-invocation value to close over. There is no working-directory
    parameter and no Cyclopts working-dir option.

    Returns
    -------
    cyclopts.App
        The configured ``novel-state`` app exposing ``check``.
    """
    app = cyclopts.App(
        name="novel-state",
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )

    @app.command
    def check() -> CommandOutcome:
        """Validate the §5.2 pure-state invariants without writing (design §4.1)."""
        return _check()

    return app
