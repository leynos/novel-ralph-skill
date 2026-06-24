"""The shared ``run`` wrapper that drives a Cyclopts app to the contract.

Cyclopts maps usage errors to exit ``1`` by default, but the contract demands
exit ``2`` (design 3.2, ADR 003 Table 2); and Cyclopts's default
``result_action`` calls :func:`sys.exit` on a body's return value inside
``App.__call__``, which would pre-empt the wrapper's success-path envelope
emission. :func:`run` is the single shared seam that resolves both: it requires
the app to be built with ``result_action="return_value"`` so control returns to
the wrapper, then owns every :func:`sys.exit` and every envelope emission. The
five commands adopt :func:`run` rather than calling their ``App`` directly so
they share the exit-code translation without renegotiating it.

A command body returns a :class:`CommandOutcome` carrying its
:class:`~novel_ralph_skill.contract.exit_codes.ExitCode` and the envelope's
``result``/``messages``; a body raises :class:`StateInputError` to signal the
exit-``3`` state/input channel. ``--help``/``--version`` are handled by Cyclopts
and yield a non-:class:`CommandOutcome` return, which :func:`run` treats as the
help/version path: it exits ``0`` with no envelope.

This module also hosts the command-agnostic ``--human`` global-flag splitter,
:func:`parse_global_flags`, the pre-parse every command performs before
:func:`run` is called (ADR-003 §3.1). It lives here, beside the
``RunContext.human`` field it feeds, so the shared output-mode machinery sits in
one package rather than in a command module.
"""

from __future__ import annotations

import dataclasses
import sys
import typing as typ

import cyclopts
from cyclopts.exceptions import CycloptsError

from novel_ralph_skill._freeze import freeze_mapping, freeze_sequence
from novel_ralph_skill.contract.envelope import (
    build_envelope,
    render_human,
    render_machine,
)
from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc


_HUMAN_FLAG = "--human"


def make_contract_app(name: str) -> cyclopts.App:
    """Build a Cyclopts app wired to the four-flag contract :func:`run` requires.

    The app is constructed with ``result_action="return_value",
    exit_on_error=False, print_error=False, help_on_error=False`` so the shared
    :func:`run` wrapper owns every exit and envelope. The four-flag contract is
    specified in the :func:`run` docstring (runner.py lines 166-170); the flags
    serve the exit-code policy in design §3.2 / ADR-003 Table 2 but are not
    documented there. Callers register their ``@app.command``/``@app.default``
    bodies on the returned app exactly as before; this factory owns only the
    four-flag construction, co-located with the wrapper that demands it.

    Parameters
    ----------
    name : str
        The console-script name for the app (e.g. ``"novel-state"``).

    Returns
    -------
    cyclopts.App
        A freshly constructed app carrying the four required flags and ``name``,
        ready for the caller's command/default registration.
    """
    return cyclopts.App(
        name=name,
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )


def parse_global_flags(argv: list[str]) -> tuple[bool, list[str]]:
    """Split the ``--human`` global flag off ``argv`` (ADR-003 §3.1).

    This is the command-agnostic pre-parse every command performs before
    :func:`run` is reached. :func:`run` stamps the ``--human`` selection into
    every envelope, including the usage (exit ``2``) and state-error (exit
    ``3``) paths where the command body never runs, so the flag must be resolved
    *before* ``run`` is called (Decision Log B3). This is a tiny
    standard-library splitter — no new dependency: it recognises a ``--human``
    boolean in any position, removes every occurrence, and returns the selection
    alongside the residual argv. It parses no working-directory token; the
    working directory is the fixed ``working/`` constant (B4), never a flag.

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


class StateInputError(EnvelopeMessagesError):
    """A command body raises this to signal the contract's exit-``3`` channel.

    A state or input fault — a missing or unparseable ``state.toml``, an absent
    working directory, or a refused mutator request — is the contract's exit
    ``3``, never the benign ``1`` (design 3.2 and 3.4). The optional
    ``messages`` payload, recorded once by the
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` base,
    carries human prose for the emitted envelope.
    """


@dataclasses.dataclass(frozen=True, kw_only=True)
class CommandOutcome:
    """The value a command body returns for :func:`run` to render.

    Attributes
    ----------
    code : ExitCode
        The command's exit code; ``0``/``1``/``4`` flow through unchanged.
    result : collections.abc.Mapping[str, object]
        The machine-actionable payload for the envelope's ``result`` field.
    messages : collections.abc.Sequence[str]
        Human-oriented notes for the envelope's ``messages`` field.
    """

    code: ExitCode
    result: cabc.Mapping[str, object] = dataclasses.field(default_factory=dict)
    messages: cabc.Sequence[str] = dataclasses.field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Freeze ``result``/``messages`` to read-only containers at construction."""
        object.__setattr__(self, "result", freeze_mapping(self.result))
        object.__setattr__(self, "messages", freeze_sequence(self.messages))


@dataclasses.dataclass(frozen=True, kw_only=True)
class RunContext:
    """The per-invocation context :func:`run` stamps into every envelope.

    Attributes
    ----------
    command : str
        The console-script name stamped into every envelope.
    working_dir : str
        The working directory recorded in every envelope.
    human : bool
        Whether to render the human rather than the machine envelope.
    """

    command: str
    working_dir: str
    human: bool


def _emit(context: RunContext, outcome: CommandOutcome) -> None:
    """Build and write one envelope to stdout in the active output mode.

    Parameters
    ----------
    context : RunContext
        The per-invocation command name, working directory, and output mode.
    outcome : CommandOutcome
        The exit code and the ``result``/``messages`` payload to render.
    """
    envelope = build_envelope(
        command=context.command,
        working_dir=context.working_dir,
        code=outcome.code,
        result=outcome.result,
        messages=outcome.messages,
    )
    rendered = render_human(envelope) if context.human else render_machine(envelope)
    print(rendered)


def run(
    app: cyclopts.App,
    argv: cabc.Sequence[str],
    context: RunContext,
) -> typ.NoReturn:
    """Drive ``app`` over ``argv`` and exit per the contract's code table.

    The app MUST be built with ``result_action="return_value", exit_on_error=
    False, print_error=False, help_on_error=False`` (pinned by the Work item 1
    tripwire): the first returns the body value to this wrapper, the rest make
    Cyclopts raise on a usage error rather than exit ``1`` and suppress its Rich
    panel so the wrapper owns the diagnostic channel.

    Parameters
    ----------
    app : cyclopts.App
        The command's Cyclopts app, configured as described above.
    argv : collections.abc.Sequence[str]
        The argument vector to parse (typically ``sys.argv[1:]``).
    context : RunContext
        The command name, working directory, and ``--human`` selection stamped
        into every envelope.

    Returns
    -------
    typing.NoReturn
        Always exits the process via :func:`sys.exit`.

    Raises
    ------
    SystemExit
        Always, carrying the contract exit code.
    """
    try:
        outcome = app(list(argv))
    except CycloptsError as exc:
        # A usage error: unknown subcommand/option or a missing argument. The
        # contract demands exit 2, not Cyclopts's native 1.
        _emit(
            context,
            CommandOutcome(code=ExitCode.USAGE_ERROR, messages=[str(exc)]),
        )
        sys.exit(ExitCode.USAGE_ERROR)
    except StateInputError as exc:
        # A state or input fault: the exit-3 channel (never the benign 1).
        _emit(
            context,
            CommandOutcome(code=ExitCode.STATE_ERROR, messages=list(exc.messages)),
        )
        sys.exit(ExitCode.STATE_ERROR)

    if not isinstance(outcome, CommandOutcome):
        # A --help/--version invocation: under exit_on_error=False Cyclopts
        # prints and returns a non-CommandOutcome value rather than exiting.
        # These are exempt from the envelope contract; exit 0 with no envelope.
        sys.exit(ExitCode.SUCCESS)

    # A normal body return: success / benign negative / actionable finding. The
    # body owns the 0/1/4 decision; the wrapper emits the envelope and exits.
    _emit(context, outcome)
    sys.exit(outcome.code)
