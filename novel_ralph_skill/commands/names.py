"""Single source of truth for the console-script and subcommand names.

Roadmap task 1.2.4 collapsed the previously duplicated name lists (in the
since-retired ``stub.py``, ``pyproject.toml``, and three test modules) onto this
one registry. Roadmap task 1.2.12 (ADR 007) stood up the ``novel`` multiplexer
beside the legacy five and added the *spaced* subcommand vocabulary the
multiplexer stamps into its envelopes; task 1.2.15 retired the legacy surface
(``stub.py`` among it), so the registry now describes exactly the single
``novel`` multiplexer the package ships.

The registry serves two roles:

- ``[project.scripts]`` binding. :func:`project_scripts_table` derives the table
  the build backend reads: the single ``novel`` multiplexer bound to
  :data:`NOVEL_MODULE`.
- Envelope command-name guard. :data:`ENVELOPE_COMMAND_NAMES` is the spaced
  ``novel <verb>`` subcommand names (:data:`SUBCOMMAND_NAMES`) plus the bare
  ``"novel"`` surface. The envelope guard validates ``command`` against this set,
  so every name the multiplexer stamps (``"novel state"`` etc., plus ``"novel"``
  on the body-less help/version arms) validates (ExecPlan Decision Log D1).
"""

from __future__ import annotations

NOVEL_MODULE: str = "novel_ralph_skill.commands.novel"
"""The package module that hosts the ``novel`` multiplexer entry point."""

# The bare multiplexer surface name and its entry-point target. ``novel`` binds
# to its own module's ``main`` and is the sole console-script the package ships.
MULTIPLEXER_NAME: str = "novel"
"""The bare ``novel`` multiplexer console-script name (ADR 007)."""

_MULTIPLEXER_ENTRY_POINT: str = "main"
"""The ``novel`` multiplexer entry-point function name in :data:`NOVEL_MODULE`."""

# The spaced subcommand names the multiplexer stamps into its envelopes, one per
# operation, in the ADR 007 surface order. These are the single source the
# dispatcher's ``_command_name_for`` consults, so it never re-spells the names
# inline (ExecPlan Decision Log D4).
SUBCOMMAND_NAMES: tuple[str, ...] = (
    "novel state",
    "novel done",
    "novel compile",
    "novel desloppify",
    "novel wordcount",
)
"""The five spaced ``novel <verb>`` subcommand names, in surface order."""

# The envelope command-name guard superset: the five spaced subcommand names and
# the bare ``"novel"`` surface (stamped on the body-less help/version arms,
# Decision Log D4). De-duplicated while preserving first-seen order so the guard's
# diagnostic lists the names deterministically.
ENVELOPE_COMMAND_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys((*SUBCOMMAND_NAMES, MULTIPLEXER_NAME))
)
"""The spaced ``novel <verb>`` names plus the bare ``"novel"`` surface."""


def project_scripts_table() -> dict[str, str]:
    """Return the ``[project.scripts]`` table derived from the registry.

    The table is the single ``novel`` multiplexer bound to :data:`NOVEL_MODULE`
    (ADR 007; task 1.2.15 retired the legacy five).

    Returns
    -------
    dict[str, str]
        A mapping of console-script name to its ``module:function`` entry-point
        target — exactly ``{"novel": …}``. A fresh dict is returned on each call
        so callers cannot mutate the registry through it.
    """
    return {MULTIPLEXER_NAME: f"{NOVEL_MODULE}:{_MULTIPLEXER_ENTRY_POINT}"}
