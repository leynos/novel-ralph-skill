"""Property and mapping tests for the ok/exit-code contract.

These cover roadmap task 1.3.1 Work item 5. The Hypothesis property proves the
ok/exit-code biconditional (``ok`` is ``True`` if and only if the code is
``SUCCESS``) across every code and a range of commands/results/messages, and a
second property pins the four non-zero codes as ``ok: false`` and pairwise
distinct. The example-specific mappings the roadmap names — malformed invocation
maps to ``2``, an unparseable/missing ``state.toml`` maps to ``3`` — are asserted
as plain pytest cases through the :func:`run` wrapper.

All Hypothesis inputs come from strategies; no ``@given`` test takes a
function-scoped fixture, which would raise
``HealthCheck.function_scoped_fixture`` (Hypothesis Compatibility docs).
"""

from __future__ import annotations

import json
import typing as typ

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novel_ralph_skill.commands.names import SUBCOMMAND_NAMES
from novel_ralph_skill.contract.envelope import build_envelope
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    import cyclopts

_NON_ZERO_CODES = tuple(code for code in ExitCode if code is not ExitCode.SUCCESS)

# why: small JSON-serialisable values, so the generated result/messages exercise
# the envelope without tripping the renderer on exotic objects.
_json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(max_size=16),
)
_results = st.dictionaries(st.text(max_size=8), _json_scalars, max_size=4)
_messages = st.lists(st.text(max_size=24), max_size=4)


@given(
    code=st.sampled_from(list(ExitCode)),
    command=st.sampled_from(list(SUBCOMMAND_NAMES)),
    result=_results,
    messages=_messages,
)
def test_ok_iff_success(
    code: ExitCode,
    command: str,
    result: dict[str, object],
    messages: list[str],
) -> None:
    """``ok`` is ``True`` if and only if the exit code is ``SUCCESS``.

    Parameters
    ----------
    code : ExitCode
        The exit code under test.
    command : str
        A registered command name.
    result : dict[str, object]
        A generated machine-actionable payload.
    messages : list[str]
        Generated human-oriented notes.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    env = build_envelope(
        command=command,
        working_dir="working",
        code=code,
        result=result,
        messages=messages,
    )
    assert env.ok is (code is ExitCode.SUCCESS)


@given(code=st.sampled_from(_NON_ZERO_CODES))
def test_non_zero_codes_are_not_ok(code: ExitCode) -> None:
    """Every non-zero code yields ``ok: false``.

    Parameters
    ----------
    code : ExitCode
        A non-zero exit code.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    env = build_envelope(
        command=SUBCOMMAND_NAMES[0],
        working_dir="working",
        code=code,
        result={},
        messages=[],
    )
    assert env.ok is False


def test_non_zero_codes_are_pairwise_distinct() -> None:
    """The four non-zero codes are pairwise distinct integers.

    A test that would fail if anyone collapsed ``1`` and ``4`` (or any pair) into
    one value, defending the contract's load-bearing distinctions.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    values = [int(code) for code in _NON_ZERO_CODES]
    assert len(set(values)) == len(values)
    assert int(ExitCode.BENIGN_NEGATIVE) != int(ExitCode.ACTIONABLE_FINDING)
    assert int(ExitCode.USAGE_ERROR) != int(ExitCode.STATE_ERROR)


def _drive(app: cyclopts.App, argv: list[str]) -> int:
    """Drive ``app`` through :func:`run` and return the captured exit code.

    Parameters
    ----------
    app : cyclopts.App
        The app to drive.
    argv : list[str]
        The argument vector.

    Returns
    -------
    int
        The process exit code :func:`run` exited with.
    """
    context = RunContext(
        command=SUBCOMMAND_NAMES[0], working_dir="working", human=False
    )
    with pytest.raises(SystemExit) as excinfo:
        run(app, argv, context)
    code = excinfo.value.code
    assert isinstance(code, int)
    return code


def test_malformed_invocation_maps_to_two(
    capsys: pytest.CaptureFixture[str],
    wrapper_app: cabc.Callable[[CommandOutcome | None], cyclopts.App],
) -> None:
    """A malformed invocation maps to exit ``2`` (the roadmap-named case).

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures and drains stdout.
    wrapper_app : Callable[[CommandOutcome | None], cyclopts.App]
        The shared builder for a run-configured app.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    app = wrapper_app(CommandOutcome(code=ExitCode.SUCCESS))
    assert _drive(app, ["nope"]) == ExitCode.USAGE_ERROR
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_state_fault_maps_to_three(
    capsys: pytest.CaptureFixture[str],
    wrapper_app: cabc.Callable[[CommandOutcome | None], cyclopts.App],
) -> None:
    """An unparseable/missing ``state.toml`` maps to exit ``3``.

    Modelled via :class:`~novel_ralph_skill.contract.runner.StateInputError`,
    the contract's exit-``3`` channel.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures and drains stdout.
    wrapper_app : Callable[[CommandOutcome | None], cyclopts.App]
        The shared builder for a run-configured app.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    app = wrapper_app(None)
    assert _drive(app, ["act"]) == ExitCode.STATE_ERROR
    assert json.loads(capsys.readouterr().out)["ok"] is False
