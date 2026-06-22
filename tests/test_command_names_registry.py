"""Gate tying the command-name registry to ``[project.scripts]``.

The registry (:mod:`novel_ralph_skill.commands.names`) is the single source of
truth for the five console-script names; ``pyproject.toml [project.scripts]``
remains authoritative for the runtime binding because the build backend reads it
verbatim. These tests keep the two in lockstep: a rename or a dropped/added
entry point in either source diverges and fails here, so the names cannot
silently drift.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands import names, stub

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def test_registry_matches_project_scripts(
    pyproject: dict[str, object],
    project_scripts: cabc.Callable[[cabc.Mapping[str, object]], dict[str, object]],
) -> None:
    """The registry-derived table equals ``[project.scripts]`` exactly."""
    assert project_scripts(pyproject) == names.project_scripts_table()


def test_registry_order_matches_table(
    pyproject: dict[str, object],
    project_scripts: cabc.Callable[[cabc.Mapping[str, object]], dict[str, object]],
) -> None:
    """The TOML parse order matches the registry's registration order.

    ``tomllib`` preserves table key order, so comparing the parsed names to
    :data:`~novel_ralph_skill.commands.names.COMMAND_NAMES` catches a reordering
    that the order-insensitive dict equality above would miss.
    """
    assert list(project_scripts(pyproject)) == list(names.COMMAND_NAMES)


def test_entry_points_resolve_to_callables() -> None:
    """Every registry entry-point function resolves to a callable on the stub."""
    for func in names.COMMAND_ENTRY_POINTS.values():
        assert callable(getattr(stub, func))


def test_registry_has_exactly_five_names() -> None:
    """The registry pins exactly the five ADR-005 console-script names."""
    assert names.COMMAND_NAMES == (
        "novel-state",
        "novel-done",
        "novel-compile",
        "desloppify",
        "wordcount",
    )
