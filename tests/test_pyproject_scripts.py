"""Fast guard on the ``[project.scripts]`` console-script table.

Parsing ``pyproject.toml`` directly catches a typo'd, renamed, or dropped entry
point without building a wheel, so the slow end-to-end test can assume the table
is correct. The five names are fixed by ADR 005 and must map to the stub module
from work item 2.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_STUB_MODULE = "novel_ralph_skill.commands.stub"

EXPECTED_SCRIPTS = {
    "novel-state": f"{_STUB_MODULE}:novel_state",
    "novel-done": f"{_STUB_MODULE}:novel_done",
    "novel-compile": f"{_STUB_MODULE}:novel_compile",
    "desloppify": f"{_STUB_MODULE}:desloppify",
    "wordcount": f"{_STUB_MODULE}:wordcount",
}


def test_project_scripts_table_lists_the_five_commands() -> None:
    """The ``[project.scripts]`` table lists exactly the five expected names."""
    pyproject = tomllib.loads(
        (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    scripts = pyproject["project"]["scripts"]
    assert scripts == EXPECTED_SCRIPTS
