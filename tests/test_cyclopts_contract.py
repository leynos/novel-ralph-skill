"""Pin the load-bearing Cyclopts behaviours the contract wrapper depends on.

This is a version-and-behaviour tripwire for roadmap task 1.3.1, mirroring the
shape of :mod:`tests.test_tomlkit_dependency`. The shared output-mode wrapper
(``novel_ralph_skill.contract.runner.run``) translates Cyclopts's native
exit-code behaviour into the contract's disambiguated codes (design 3.2,
ADR 003). That translation rests on four Cyclopts v4.18.0 behaviours, each
pinned below so a silent ``uv`` re-resolution that bumps Cyclopts or changes a
default fails the suite loudly rather than breaking the harness at runtime:

1. An app built with ``exit_on_error=False`` *raises* a
   :class:`cyclopts.exceptions.CycloptsError` subclass on a usage error
   (unknown subcommand, unknown option, missing required argument) instead of
   calling :func:`sys.exit`, so the wrapper can map it to exit ``2``.
2. ``print_error=False, help_on_error=False`` suppress the Rich error panel, so
   the wrapper owns the diagnostic channel.
3. ``result_action="return_value"`` returns the command body's value unchanged
   to the caller instead of calling :func:`sys.exit` inside ``App.__call__``,
   so the wrapper owns every exit and envelope emission (round-2 B1).
4. Under ``exit_on_error=False`` a ``--help``/``--version`` invocation prints
   and **returns ``None``** rather than raising :class:`SystemExit`; the wrapper
   therefore treats a non-``ExitCode`` return as the help/version path and exits
   ``0`` without an envelope (implementation discovery, 2026-06-22).
"""

from __future__ import annotations

import typing as typ

import cyclopts
import pytest
from cyclopts.exceptions import (
    CycloptsError,
    MissingArgumentError,
    UnknownCommandError,
    UnknownOptionError,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# why: tracks the version pinned in uv.lock; bump in lockstep with a deliberate
# Cyclopts upgrade. This exact pin is the tripwire for a silent re-resolution
# that could change a default and break the exit-code contract while make all
# stays green.
LOCKED_CYCLOPTS_VERSION = "4.18.0"


def _make_app() -> cyclopts.App:
    """Build a throwaway app configured exactly as the contract wrapper builds it.

    Returns
    -------
    cyclopts.App
        An app with two named subcommands and **no** catch-all default, so an
        unknown subcommand raises :class:`UnknownCommandError` rather than
        routing to a default body.
    """
    app = cyclopts.App(
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )

    @app.command
    def greet(name: str) -> str:
        """Return a greeting (a trivial body exercised by the probes)."""
        return f"hello {name}"

    return app


def test_cyclopts_version_is_locked() -> None:
    """``cyclopts`` resolves to the locked version.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    assert cyclopts.__version__ == LOCKED_CYCLOPTS_VERSION


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["nope"], UnknownCommandError),
        (["greet", "--bad"], UnknownOptionError),
        (["greet"], MissingArgumentError),
    ],
)
def test_usage_errors_raise_cyclopts_error(
    argv: cabc.Sequence[str],
    expected: type[CycloptsError],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Usage errors raise a ``CycloptsError`` subclass and print no panel.

    Parameters
    ----------
    argv : collections.abc.Sequence[str]
        The argument vector that should trigger the usage error.
    expected : type[cyclopts.exceptions.CycloptsError]
        The precise error subclass the invocation must raise.
    capsys : pytest.CaptureFixture[str]
        Captures stdout and stderr to confirm panel suppression.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _make_app()
    with pytest.raises(expected) as excinfo:
        app(list(argv))
    assert isinstance(excinfo.value, CycloptsError)
    captured = capsys.readouterr()
    # print_error=False, help_on_error=False suppress the Rich error panel.
    assert not captured.err
    assert not captured.out


def test_return_value_returns_body_result_to_caller() -> None:
    """``result_action="return_value"`` returns the body value to the caller.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    app = _make_app()
    sentinel = object()

    @app.command
    def sentinel_body() -> object:
        """Return a unique sentinel to prove control returns to the caller."""
        return sentinel

    # The success path runs only because control returns here; under the default
    # result_action, App.__call__ would have called sys.exit on the value.
    assert app(["sentinel-body"]) is sentinel


def test_help_and_version_return_none_without_exiting() -> None:
    """Under ``exit_on_error=False``, ``--help``/``--version`` return ``None``.

    They print to stdout and return ``None`` rather than raising
    :class:`SystemExit`. The wrapper relies on a non-``ExitCode`` return being
    the help/version signal, so it exits ``0`` with no envelope.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    for argv in (["--help"], ["--version"]):
        app = _make_app()
        assert app(argv) is None
