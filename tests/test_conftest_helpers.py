"""Focused unit tests for the shared ``tests/conftest.py`` fixtures.

These pin the logic worth verifying in the consolidated scaffolding: the
``toml_table`` accessor's happy and unhappy paths, the ``read_repo_text`` reader,
the parsed ``pyproject`` shape, that ``project_root`` resolves to the worktree
directory, and that ``single_program_catalogue`` builds a usable cuprum
allowlist. They consume the fixtures the same way production test modules do, so
they also prove the conftest wiring.
"""

from __future__ import annotations

import typing as typ

import pytest
from cuprum import sh
from cuprum.program import Program

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue


def test_project_root_is_the_worktree(project_root: Path) -> None:
    """The ``project_root`` fixture points at the directory holding ``tests``."""
    assert (project_root / "tests").is_dir(), (
        f"project_root {project_root} has no tests/ directory"
    )
    assert (project_root / "pyproject.toml").is_file(), (
        f"project_root {project_root} has no pyproject.toml"
    )


def test_pyproject_exposes_package_name(
    pyproject: dict[str, object],
    toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
) -> None:
    """The parsed ``pyproject`` carries the package name under ``[project]``."""
    project = toml_table(pyproject, "project")
    assert project["name"] == "novel-ralph-skill", (
        f"unexpected [project] name: {project['name']!r}"
    )


def test_read_repo_text_reads_a_known_marker(
    read_repo_text: cabc.Callable[..., str],
) -> None:
    """``read_repo_text`` reads a repo file and returns its UTF-8 text."""
    text = read_repo_text("pyproject.toml")
    assert "[project]" in text, "pyproject.toml text is missing the [project] table"


def test_toml_table_returns_the_sub_table(
    toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
) -> None:
    """``toml_table`` returns the nested table for a table-valued key."""
    parent: dict[str, object] = {"section": {"key": "value"}}
    assert toml_table(parent, "section") == {"key": "value"}, (
        "toml_table did not return the nested table verbatim"
    )


def test_toml_table_rejects_a_non_table(
    toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
) -> None:
    """``toml_table`` raises :class:`AssertionError` for a non-table value."""
    parent: dict[str, object] = {"scalar": 7}
    with pytest.raises(AssertionError, match="must be a TOML table"):
        toml_table(parent, "scalar")


def test_single_program_catalogue_builds_usable_allowlist(
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> None:
    """The factory allowlists the program and ``sh.make`` resolves it.

    Building the catalogue and resolving the program proves the factory yields a
    usable allowlist without paying the slow wheel-build-and-install e2e cost.
    """
    program = Program("uv")
    catalogue = single_program_catalogue("x", program)

    assert program in catalogue.allowlist, (
        f"{program} missing from catalogue allowlist {catalogue.allowlist}"
    )
    # cuprum.sh.make resolves the program through the catalogue eagerly; for an
    # allowlisted program it must return a usable SafeCmdBuilder rather than
    # raising UnknownProgramError. Asserting on the returned builder (and the
    # SafeCmd it constructs) makes that "does not raise" guarantee explicit.
    builder = sh.make(program, catalogue=catalogue)
    assert callable(builder), (
        f"sh.make returned a non-callable {builder!r} for allowlisted {program}"
    )
    command = builder()
    assert command.program == program, (
        f"builder produced SafeCmd.program {command.program!r}, expected {program!r}"
    )


def test_single_program_catalogue_accepts_absolute_path(
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> None:
    """An absolute-path program string is a valid, allowlisted ``Program``.

    cuprum 0.1.0 treats ``Program`` as a bare ``str`` with no path validation;
    the catalogue allowlist is the gate. Pinning this so a future cuprum bump
    that adds path validation fails loudly here rather than in the slow e2e.
    """
    program = Program("/usr/bin/true")
    catalogue = single_program_catalogue("abs", program)

    assert program in catalogue.allowlist, (
        f"absolute-path {program} missing from allowlist {catalogue.allowlist}"
    )
