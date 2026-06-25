"""Shared ``driver`` fixture for the ``novel`` multiplexer dispatch suites.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py``, beside ``corpus_fixtures`` and its siblings. It is the
single home for the in-process drive fixture the unit suite
(``tests/test_multiplexer_dispatch.py``) and the behavioural suite
(``tests/test_multiplexer_behaviour.py``) share, so neither module re-spells the
driver mechanics. The fixture is consumed **by name** — never by a runtime value
import — exactly as the developers-guide "Shared test scaffolding" rule requires;
the :class:`Driver` *type* may be imported under ``TYPE_CHECKING`` to annotate
the fixture's value, the one sanctioned exception. Splitting the two suites keeps
each within the 400-line module cap (AGENTS.md lines 24-27); registering this as
a plugin keeps ``driver`` available by name exactly as a ``conftest`` fixture
would be.
"""

from __future__ import annotations

import dataclasses
import typing as typ

import pytest

from novel_ralph_skill.commands import novel
from novel_ralph_skill.commands.novel_state import WORKING_DIR_NAME
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    import cyclopts


class _MuxDrive(typ.Protocol):
    """The multiplexer drive arm: ``(argv, *, human) -> (code, stdout)``."""

    def __call__(self, argv: list[str], *, human: bool = ...) -> tuple[int, str]:
        """Drive the multiplexer over ``argv``; return ``(code, stdout)``."""


class _LegacyDrive(typ.Protocol):
    """The legacy-leaf drive arm: ``(build_app, argv, name) -> (code, stdout)``."""

    def __call__(
        self, build_app: cabc.Callable[[], cyclopts.App], argv: list[str], name: str
    ) -> tuple[int, str]:
        """Drive a legacy leaf over ``argv``; return ``(code, stdout)``."""


@dataclasses.dataclass(frozen=True)
class Driver:
    """An in-process driver bundling the multiplexer and legacy drive arms.

    Bundling ``capsys`` into one fixture keeps each behavioural test's parameter
    list within the project's argument-count gate (Pylint ``too-many-arguments``)
    while still delivering the capture mechanics by fixture name, exactly as
    ``tests/test_command_surface_matrix.py`` does. The two arms are closures over
    the test's ``capsys`` rather than methods, so they carry no unused ``self``.
    This type may be imported under ``TYPE_CHECKING`` by the consuming suites (the
    developers-guide shared-type carve-out); the fixture is consumed by name.

    Attributes
    ----------
    mux : _MuxDrive
        Drives the multiplexer over an argv, resolving the command name through
        ``novel``'s own ``_command_name_for``.
    legacy : _LegacyDrive
        Drives a legacy leaf ``build_app`` over an argv under the given name.
    """

    mux: _MuxDrive
    legacy: _LegacyDrive


@pytest.fixture
def driver(capsys: pytest.CaptureFixture[str]) -> Driver:
    """Return an in-process driver for the multiplexer and the legacy leaves.

    The multiplexer arm resolves its command name through ``novel``'s own
    :func:`~novel_ralph_skill.commands.novel._command_name_for`, so the test
    exercises the entry point's name derivation rather than re-spelling it. Both
    arms drive through the shared ``run`` wrapper, which always exits, so the
    :class:`SystemExit` code is the contract exit code and ``capsys`` captures the
    rendered envelope (if any).

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures the rendered stdout.

    Returns
    -------
    Driver
        A driver bundling the ``mux`` and ``legacy`` drive arms.
    """

    def _capture(
        app: cyclopts.App, argv: list[str], name: str, *, human: bool
    ) -> tuple[int, str]:
        """Drive ``app`` over ``argv`` through ``run``; return ``(code, stdout)``."""
        with pytest.raises(SystemExit) as excinfo:
            run(
                app,
                argv,
                RunContext(command=name, working_dir=WORKING_DIR_NAME, human=human),
            )
        return int(typ.cast("int", excinfo.value.code)), capsys.readouterr().out

    def _mux(argv: list[str], *, human: bool = False) -> tuple[int, str]:
        """Drive the multiplexer over ``argv``; return ``(code, stdout)``."""
        name = novel._command_name_for(argv)
        return _capture(novel.build_multiplexer(), argv, name, human=human)

    def _legacy(
        build_app: cabc.Callable[[], cyclopts.App], argv: list[str], name: str
    ) -> tuple[int, str]:
        """Drive a legacy leaf over ``argv``; return ``(code, stdout)``."""
        return _capture(build_app(), argv, name, human=False)

    return Driver(mux=_mux, legacy=_legacy)
