"""The console-script binding, re-exporting the contract command-name vocabulary.

Roadmap task 1.2.4 collapsed the previously duplicated name lists (in the
since-retired ``stub.py``, ``pyproject.toml``, and three test modules) onto this
one registry. Roadmap task 1.2.12 (ADR 007) stood up the ``novel`` multiplexer
beside the legacy five and added the *spaced* subcommand vocabulary the
multiplexer stamps into its envelopes; task 1.2.15 retired the legacy surface
(``stub.py`` among it), so the registry now describes exactly the single
``novel`` multiplexer the package ships.

Roadmap task 7.3.6 split this module's two responsibilities (ExecPlan Decision
Log D1):

- The **command-name vocabulary** — :data:`MULTIPLEXER_NAME`,
  :data:`SUBCOMMAND_NAMES`, :data:`ENVELOPE_COMMAND_NAMES`, and the derived
  spaced-name-to-verb accessor :data:`SUBCOMMAND_VERBS` / :func:`verb_for`
  (roadmap task 7.3.8) — is contract data the envelope guard enforces, so it now
  lives in :mod:`novel_ralph_skill.contract.names`. This module re-exports it for
  back-compatibility (every existing ``commands.names`` import keeps resolving),
  but the contract package owns it.
- The **console-script binding** — :data:`NOVEL_MODULE` and
  :func:`project_scripts_table` — derives the ``[project.scripts]`` table the
  build backend reads, binding the single ``novel`` multiplexer to its
  ``commands``-layer entry-point module. That is a packaging concern that
  legitimately references the commands layer, so it stays here and *consumes*
  the re-exported :data:`MULTIPLEXER_NAME` in the deliberate downward direction.
"""

from __future__ import annotations

from novel_ralph_skill.contract.names import (
    ENVELOPE_COMMAND_NAMES,
    MULTIPLEXER_NAME,
    SUBCOMMAND_NAMES,
    SUBCOMMAND_VERBS,
    verb_for,
)

__all__ = [
    "ENVELOPE_COMMAND_NAMES",
    "MULTIPLEXER_NAME",
    "NOVEL_MODULE",
    "SUBCOMMAND_NAMES",
    "SUBCOMMAND_VERBS",
    "project_scripts_table",
    "verb_for",
]

NOVEL_MODULE: str = "novel_ralph_skill.commands.novel"
"""The package module that hosts the ``novel`` multiplexer entry point."""

_MULTIPLEXER_ENTRY_POINT: str = "main"
"""The ``novel`` multiplexer entry-point function name in :data:`NOVEL_MODULE`."""


def project_scripts_table() -> dict[str, str]:
    """Return the ``[project.scripts]`` table derived from the registry.

    The table is the single ``novel`` multiplexer bound to :data:`NOVEL_MODULE`
    (ADR 007; task 1.2.15 retired the legacy five). It consumes
    :data:`MULTIPLEXER_NAME`, re-exported from
    :mod:`novel_ralph_skill.contract.names`, for the console-script name.

    Returns
    -------
    dict[str, str]
        A mapping of console-script name to its ``module:function`` entry-point
        target — exactly ``{"novel": …}``. A fresh dict is returned on each call
        so callers cannot mutate the registry through it.
    """
    return {MULTIPLEXER_NAME: f"{NOVEL_MODULE}:{_MULTIPLEXER_ENTRY_POINT}"}
