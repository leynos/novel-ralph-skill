"""The ``novel-state`` subcommand app and its global-flag pre-parse.

This module hosts the read-only ``novel-state`` Cyclopts app (design §4.1) and
the standard-library ``--human`` pre-parse the entry point performs before
:func:`novel_ralph_skill.contract.runner.run` is reached. It is the first
command on the real ``run`` path, so the conventions it sets — pre-parsing the
single ``--human`` global flag off argv (ADR-003 §3.1) and reading state from
the fixed cwd-relative ``working/`` directory (design line 151) — are the ones
the four later commands inherit.

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

import cyclopts

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import load_state, validate_state

# The fixed cwd-relative working directory the design records (design line 151);
# the same constant the entry point stamps into the ``RunContext.working_dir``,
# so the file ``check`` reads and the envelope's ``working_dir`` field cannot
# drift (Decision Log B4/B5). There is no ``--working-dir`` flag.
WORKING_DIR_NAME = "working"

_HUMAN_FLAG = "--human"


def parse_global_flags(argv: list[str]) -> tuple[bool, list[str]]:
    """Split the ``--human`` global flag off ``argv`` (ADR-003 §3.1).

    The shared :func:`novel_ralph_skill.contract.runner.run` stamps the
    ``--human`` selection into every envelope, including the usage (exit ``2``)
    and state-error (exit ``3``) paths where the command body never runs, so the
    flag must be resolved *before* ``run`` is called (Decision Log B3). This is a
    tiny standard-library splitter — no new dependency: it recognises a
    ``--human`` boolean in any position, removes every occurrence, and returns
    the selection alongside the residual argv. It parses no working-directory
    token; the working directory is the fixed ``working/`` constant (B4), never a
    flag.

    Parameters
    ----------
    argv : list[str]
        The raw argument vector (typically ``sys.argv[1:]``).

    Returns
    -------
    tuple[bool, list[str]]
        ``(human, residual)`` — whether ``--human`` was present, and ``argv``
        with every ``--human`` occurrence removed, the remaining tokens in
        order.
    """
    residual = [token for token in argv if token != _HUMAN_FLAG]
    human = len(residual) != len(argv)
    return human, residual


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
    try:
        state = load_state(path)
    except (
        OSError,
        tomllib.TOMLDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        msg = f"cannot load {path}: {exc}"
        raise StateInputError(msg) from exc

    verdict = validate_state(state)
    if not verdict:
        return CommandOutcome(
            code=ExitCode.SUCCESS,
            result={"violations": []},
            messages=["state is coherent"],
        )
    return CommandOutcome(
        code=ExitCode.ACTIONABLE_FINDING,
        result={"violations": [violation.invariant for violation in verdict]},
        messages=[violation.detail for violation in verdict],
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
