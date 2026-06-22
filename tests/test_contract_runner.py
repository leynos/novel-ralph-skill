"""CLI error-path tests for the ``run`` wrapper's exit-code translation.

These are the "CLI error-path tests" design 9 assigns to the exit-code contract
(roadmap task 1.3.1 Work item 4). Each drives a minimal Cyclopts app through
:func:`run` and asserts the contract exit code and the emitted envelope. The
success/benign/actionable paths run only because the app is built with
``result_action="return_value"`` (the round-1 B1 regression guard), and the
``1``-versus-``4`` split is asserted as the harness-meaning distinction design 9
fixes for these tests.
"""

from __future__ import annotations

import json

import cyclopts
import pytest

from novel_ralph_skill.commands.names import COMMAND_NAMES
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import (
    CommandOutcome,
    RunContext,
    StateInputError,
    run,
)

_COMMAND = COMMAND_NAMES[0]
_STATE_FAULT = "state.toml is unparseable"


def _build_app(outcome: CommandOutcome | None = None) -> cyclopts.App:
    """Build a wrapper-configured app with one ``act`` subcommand.

    Parameters
    ----------
    outcome : CommandOutcome | None
        The outcome the ``act`` body returns. When ``None`` the body raises
        :class:`StateInputError` instead, to exercise the exit-``3`` path.

    Returns
    -------
    cyclopts.App
        An app configured exactly as :func:`run` requires, with no catch-all
        default so an unknown subcommand raises ``UnknownCommandError``.
    """
    app = cyclopts.App(
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )

    @app.command
    def act(name: str = "default") -> object:
        """Return the configured outcome, or raise the state-error sentinel."""
        del name
        if outcome is None:
            raise StateInputError(_STATE_FAULT)
        return outcome

    return app


def _run(app: cyclopts.App, argv: list[str], *, human: bool = False) -> None:
    """Drive ``app`` through :func:`run`, asserting it exits.

    Parameters
    ----------
    app : cyclopts.App
        The app to drive.
    argv : list[str]
        The argument vector.
    human : bool
        Whether to select the human rendering.
    """
    run(
        app,
        argv,
        RunContext(command=_COMMAND, working_dir="working", human=human),
    )


@pytest.mark.parametrize(
    "argv",
    [["nope"], ["act", "--bad"], ["act", "extra", "tokens", "here"]],
)
def test_usage_error_exits_two(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed invocation exits ``2`` with an ``ok: false`` envelope.

    Parameters
    ----------
    argv : list[str]
        The malformed argument vector.
    capsys : pytest.CaptureFixture[str]
        Captures stdout to inspect the emitted envelope.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(CommandOutcome(code=ExitCode.SUCCESS))
    with pytest.raises(SystemExit) as excinfo:
        _run(app, argv)
    assert excinfo.value.code == ExitCode.USAGE_ERROR
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ok"] is False
    assert parsed["command"] == _COMMAND


def test_state_error_exits_three(capsys: pytest.CaptureFixture[str]) -> None:
    """A body raising :class:`StateInputError` exits ``3``, ``ok: false``.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures stdout to inspect the emitted envelope.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(outcome=None)
    with pytest.raises(SystemExit) as excinfo:
        _run(app, ["act"])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ok"] is False
    assert parsed["messages"] == [_STATE_FAULT]


def test_success_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """A success outcome exits ``0`` with ``ok: true``.

    This path runs only because ``result_action="return_value"`` returned
    control to the wrapper (the B1 regression guard).

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures stdout to inspect the emitted envelope.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(CommandOutcome(code=ExitCode.SUCCESS, result={"cursor": "ch01"}))
    with pytest.raises(SystemExit) as excinfo:
        _run(app, ["act"])
    assert excinfo.value.code == ExitCode.SUCCESS
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ok"] is True
    assert parsed["result"] == {"cursor": "ch01"}


@pytest.mark.parametrize(
    "code",
    [ExitCode.BENIGN_NEGATIVE, ExitCode.ACTIONABLE_FINDING],
)
def test_body_code_flows_through(
    code: ExitCode, capsys: pytest.CaptureFixture[str]
) -> None:
    """The benign-negative and actionable-finding codes flow through unchanged.

    Parameters
    ----------
    code : ExitCode
        The body's returned exit code (``1`` or ``4``).
    capsys : pytest.CaptureFixture[str]
        Captures stdout to inspect the emitted envelope.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(CommandOutcome(code=code))
    with pytest.raises(SystemExit) as excinfo:
        _run(app, ["act"])
    assert excinfo.value.code == code
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_benign_and_actionable_are_not_interchangeable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The ``1`` and ``4`` codes are distinct and not interchangeable.

    This is the harness-meaning distinction design 9 assigns to the CLI
    error-path tests: both carry ``ok: false`` yet differ as exit codes, so a
    consumer can tell "keep drafting" (``1``) from "stop and adjudicate" (``4``).

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures stdout (drained after each invocation).

    Returns
    -------
    None
        The assertions raise on failure.
    """
    codes: dict[ExitCode, int] = {}
    for code in (ExitCode.BENIGN_NEGATIVE, ExitCode.ACTIONABLE_FINDING):
        app = _build_app(CommandOutcome(code=code))
        with pytest.raises(SystemExit) as excinfo:
            _run(app, ["act"])
        assert isinstance(excinfo.value.code, int)
        codes[code] = excinfo.value.code
        capsys.readouterr()  # drain so the next iteration starts clean
    assert codes[ExitCode.BENIGN_NEGATIVE] != codes[ExitCode.ACTIONABLE_FINDING]
    assert codes[ExitCode.BENIGN_NEGATIVE] == 1
    assert codes[ExitCode.ACTIONABLE_FINDING] == 4


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_help_and_version_exit_zero_without_envelope(
    flag: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--help``/``--version`` exit ``0`` and emit no envelope.

    Parameters
    ----------
    flag : str
        The meta flag under test.
    capsys : pytest.CaptureFixture[str]
        Captures stdout to confirm no envelope is emitted.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(CommandOutcome(code=ExitCode.SUCCESS))
    with pytest.raises(SystemExit) as excinfo:
        _run(app, [flag])
    assert excinfo.value.code == ExitCode.SUCCESS
    # Cyclopts prints the help/version text, but the wrapper emits no envelope:
    # stdout must not parse as the contract JSON object.
    out = capsys.readouterr().out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_human_flag_switches_rendering(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--human`` switches stdout to the human rendering at the same code.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures stdout to inspect the human rendering.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _build_app(
        CommandOutcome(code=ExitCode.SUCCESS, messages=["state initialised"])
    )
    with pytest.raises(SystemExit) as excinfo:
        _run(app, ["act"], human=True)
    assert excinfo.value.code == ExitCode.SUCCESS
    out = capsys.readouterr().out
    assert "ok: True" in out
    assert "  - state initialised" in out
    # The human rendering is not the machine JSON object.
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
