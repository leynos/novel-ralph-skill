"""Single source of truth for the console-script and subcommand names.

Roadmap task 1.2.4 collapsed the previously duplicated name lists (in
``stub.py``, ``pyproject.toml``, and three test modules) onto this one registry.
Roadmap task 1.2.12 (ADR 007) extends it to carry the ``novel`` multiplexer
alongside the legacy five, and adds the *spaced* subcommand vocabulary the
multiplexer stamps into its envelopes — without disturbing the legacy surface,
which task 1.2.13 removes.

The registry now serves two decoupled roles:

- ``[project.scripts]`` binding. :data:`COMMAND_ENTRY_POINTS` records each
  console-script name once, paired with its ``module:function`` target;
  :func:`project_scripts_table` derives the table the build backend reads. As of
  task 1.2.12 this is the legacy five (bound to :data:`STUB_MODULE`) **plus** the
  single ``novel`` multiplexer (bound to :data:`NOVEL_MODULE`).
- Envelope command-name guard. :data:`ENVELOPE_COMMAND_NAMES` is the superset of
  the legacy five (:data:`COMMAND_NAMES`) and the spaced subcommand names
  (:data:`SUBCOMMAND_NAMES`, plus the bare ``"novel"`` surface). The envelope
  guard validates ``command`` against this superset, so both the legacy entry
  points (which stamp ``"novel-state"`` etc.) and the new multiplexer (which
  stamps ``"novel state"`` etc.) validate during the 1.2.12 -> 1.2.13 transition
  (ExecPlan Decision Log D1).

The legacy :data:`COMMAND_NAMES` tuple is unchanged (still exactly the five), so
the legacy entry points and their existing gates are untouched.
"""

from __future__ import annotations

import types

STUB_MODULE: str = "novel_ralph_skill.commands.stub"
"""The package module that hosts the five legacy stub entry-point functions."""

NOVEL_MODULE: str = "novel_ralph_skill.commands.novel"
"""The package module that hosts the ``novel`` multiplexer entry point."""

_COMMAND_ENTRY_POINTS: dict[str, str] = {
    "novel-state": "novel_state",
    "novel-done": "novel_done",
    "novel-compile": "novel_compile",
    "desloppify": "desloppify",
    "wordcount": "wordcount",
}

COMMAND_ENTRY_POINTS: types.MappingProxyType[str, str] = types.MappingProxyType(
    _COMMAND_ENTRY_POINTS
)
"""Ordered map of legacy console-script name to its stub entry-point function."""

COMMAND_NAMES: tuple[str, ...] = tuple(COMMAND_ENTRY_POINTS)
"""The five legacy console-script names, in registration order."""

# The bare multiplexer surface name and its entry-point target. ``novel`` binds
# to its own module's ``main`` (not the stub), so it is recorded separately from
# the stub-bound legacy five and folded into the script table by name.
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

# The envelope command-name guard superset: the legacy five, the five spaced
# subcommand names, and the bare ``"novel"`` surface (stamped on the body-less
# help/version arms, Decision Log D4). De-duplicated while preserving first-seen
# order so the guard's diagnostic lists the names deterministically.
ENVELOPE_COMMAND_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys((*COMMAND_NAMES, *SUBCOMMAND_NAMES, MULTIPLEXER_NAME))
)
"""Superset of the legacy five, the spaced names, and the bare ``"novel"``."""


def project_scripts_table() -> dict[str, str]:
    """Return the ``[project.scripts]`` table derived from the registry.

    The table is the legacy five (bound to :data:`STUB_MODULE`) followed by the
    single ``novel`` multiplexer (bound to :data:`NOVEL_MODULE`). The legacy five
    stay registered and working through task 1.2.12; task 1.2.13 removes them.

    Returns
    -------
    dict[str, str]
        A mapping of console-script name to its ``module:function`` entry-point
        target, in registration order (legacy five, then ``novel``). A fresh dict
        is returned on each call so callers cannot mutate the registry through it.
    """
    table = {
        name: f"{STUB_MODULE}:{func}" for name, func in COMMAND_ENTRY_POINTS.items()
    }
    table[MULTIPLEXER_NAME] = f"{NOVEL_MODULE}:{_MULTIPLEXER_ENTRY_POINT}"
    return table
