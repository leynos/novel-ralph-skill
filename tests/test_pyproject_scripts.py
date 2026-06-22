"""Fast guard on the ``[project.scripts]`` console-script table.

Parsing ``pyproject.toml`` directly catches a typo'd, renamed, or dropped entry
point without building a wheel, so the slow end-to-end test can assume the table
is correct. The five names are fixed by ADR 005; the expected table is derived
from the single source of truth (:mod:`novel_ralph_skill.commands.names`) rather
than re-declared here.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands import names

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def test_project_scripts_table_lists_the_five_commands(
    pyproject: dict[str, object],
    project_scripts: cabc.Callable[[cabc.Mapping[str, object]], dict[str, object]],
) -> None:
    """The ``[project.scripts]`` table lists exactly the five expected names."""
    assert project_scripts(pyproject) == names.project_scripts_table()
