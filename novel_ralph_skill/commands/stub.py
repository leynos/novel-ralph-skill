"""Stub console-script entry points for the deterministic spine.

Each of the five console-scripts (``novel-state``, ``novel-done``,
``novel-compile``, ``desloppify``, ``wordcount``) is wired here as a minimal
Cyclopts application that reports "not yet implemented" and exits ``2`` until
its real logic lands in a later roadmap slice. The shared :func:`make_stub_app`
factory keeps the five definitions in lockstep so they cannot drift.
"""

from __future__ import annotations

import sys

import cyclopts

from novel_ralph_skill.commands.names import COMMAND_ENTRY_POINTS
from novel_ralph_skill.commands.novel_state import (
    WORKING_DIR_NAME,
    build_app,
    parse_global_flags,
)
from novel_ralph_skill.contract.runner import RunContext, run

STUB_EXIT_CODE = 2
"""Exit code for an unimplemented command result (usage error, design 3.2)."""

_NAME_FOR: dict[str, str] = {func: name for name, func in COMMAND_ENTRY_POINTS.items()}
"""Reverse map from entry-point function name to its console-script name.

Built once from the registry so each entry-point body reads its name from the
single source of truth rather than re-spelling it inline (roadmap task 1.2.4).
"""


def make_stub_app(name: str) -> cyclopts.App:
    """Build a Cyclopts app whose command-result invocation exits ``2``.

    A default callback taking ``*tokens`` is registered so the no-argument path
    and any positional-token path both reach user code and exit with
    :data:`STUB_EXIT_CODE`. The ``*tokens`` parameter is load-bearing: without
    it a positional token raises ``UnusedCliTokensError`` and exits ``1``
    instead of reaching the body (verified against cyclopts 4.18.0). The
    Cyclopts parser handles three classes before the default runs and they are
    exempt from the exit-code contract (design 3.2 governs command results):
    ``--help``/``-h`` and ``--version`` exit ``0``, and an unknown ``--option``
    exits ``1``.

    Parameters
    ----------
    name : str
        The console-script name reported in the "not yet implemented" message.

    Returns
    -------
    cyclopts.App
        An app whose default callback writes the message to stderr and exits
        :data:`STUB_EXIT_CODE`. Running the app produces the exit, so the
        returned value is load-bearing rather than scaffolding.
    """
    app = cyclopts.App(name=name)

    @app.default
    def _not_implemented(*tokens: str) -> None:
        """Report that ``name`` is not yet implemented and exit ``2``."""
        del tokens  # accepted so positional tokens route here, not to an error
        # why: stubs emit human prose only; the JSON envelope is task 1.3.1.
        print(f"{name} is not yet implemented", file=sys.stderr)
        sys.exit(STUB_EXIT_CODE)

    return app


def novel_state() -> None:
    """Console-script entry point for ``novel-state`` (drives the real app).

    Unlike the four still-stubbed entry points, ``novel-state`` is wired to its
    real Cyclopts app (roadmap task 2.1.2). The single ``--human`` global flag is
    pre-parsed off ``sys.argv`` *before* :func:`run` is called, because ``run``
    stamps the human selection into the envelope even on the usage and
    state-error paths where the command body never executes (Decision Log B3).
    The working directory is the fixed ``working/`` constant the design records,
    not a flag (B4), so it is stamped into the :class:`RunContext`
    unconditionally and the residual argv (``--human`` removed) drives the app.
    """
    human, residual = parse_global_flags(sys.argv[1:])
    run(
        build_app(),
        residual,
        RunContext(
            command=_NAME_FOR["novel_state"],
            working_dir=WORKING_DIR_NAME,
            human=human,
        ),
    )


def novel_done() -> None:
    """Console-script entry point for ``novel-done`` (stub; exits ``2``)."""
    make_stub_app(_NAME_FOR["novel_done"])()


def novel_compile() -> None:
    """Console-script entry point for ``novel-compile`` (stub; exits ``2``)."""
    make_stub_app(_NAME_FOR["novel_compile"])()


def desloppify() -> None:
    """Console-script entry point for ``desloppify`` (stub; exits ``2``)."""
    make_stub_app(_NAME_FOR["desloppify"])()


def wordcount() -> None:
    """Console-script entry point for ``wordcount`` (stub; exits ``2``)."""
    make_stub_app(_NAME_FOR["wordcount"])()
