"""Fast guard on the ``[project.scripts]`` console-script table.

Parsing ``pyproject.toml`` directly catches a typo'd, renamed, or dropped entry
point without building a wheel, so the slow end-to-end test can assume the table
is correct. The five names are fixed by ADR 005; the expected table is derived
from the single source of truth (:mod:`novel_ralph_skill.commands.names`) rather
than re-declared here.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from novel_ralph_skill.commands import names

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_project_scripts_table_lists_the_five_commands() -> None:
    """The ``[project.scripts]`` table lists exactly the five expected names."""
    pyproject = tomllib.loads(
        (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    scripts = pyproject["project"]["scripts"]
    assert scripts == names.project_scripts_table()
