"""Single source of truth for the five console-script command names.

Roadmap task 1.2.4 collapses the previously duplicated name lists (in
``stub.py``, ``pyproject.toml``, and three test modules) onto this one registry.
The ordered mapping :data:`COMMAND_ENTRY_POINTS` records each console-script
name once, paired with its stub entry-point function name; the entry-point
functions, the unit tests, and the end-to-end test all derive their data from
here, and a dedicated gate asserts ``[project.scripts]`` agrees with
:func:`project_scripts_table`. The five names are fixed by ADR 005 and bound to
the stub module by ADR 004; this registry introduces no command and renames
none.
"""

from __future__ import annotations

import types

STUB_MODULE: str = "novel_ralph_skill.commands.stub"
"""The package module that hosts the five stub entry-point functions."""

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
"""Ordered map of console-script name to its stub entry-point function name."""

COMMAND_NAMES: tuple[str, ...] = tuple(COMMAND_ENTRY_POINTS)
"""The five console-script names, in registration order."""


def project_scripts_table() -> dict[str, str]:
    """Return the ``[project.scripts]`` table derived from the registry.

    Returns
    -------
    dict[str, str]
        A mapping of console-script name to its ``module:function``
        entry-point target, in registration order. A fresh dict is returned on
        each call so callers cannot mutate the registry through it.
    """
    return {
        name: f"{STUB_MODULE}:{func}" for name, func in COMMAND_ENTRY_POINTS.items()
    }
