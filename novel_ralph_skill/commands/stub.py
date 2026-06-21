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

STUB_EXIT_CODE = 2
"""Exit code for an unimplemented command result (usage error, design 3.2)."""


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
    """Console-script entry point for ``novel-state`` (stub; exits ``2``)."""
    make_stub_app("novel-state")()


def novel_done() -> None:
    """Console-script entry point for ``novel-done`` (stub; exits ``2``)."""
    make_stub_app("novel-done")()


def novel_compile() -> None:
    """Console-script entry point for ``novel-compile`` (stub; exits ``2``)."""
    make_stub_app("novel-compile")()


def desloppify() -> None:
    """Console-script entry point for ``desloppify`` (stub; exits ``2``)."""
    make_stub_app("desloppify")()


def wordcount() -> None:
    """Console-script entry point for ``wordcount`` (stub; exits ``2``)."""
    make_stub_app("wordcount")()
