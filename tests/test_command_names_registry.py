"""Gate tying the command-name registry to ``[project.scripts]``.

The registry (:mod:`novel_ralph_skill.commands.names`) is the single source of
truth for the console-script names; ``pyproject.toml [project.scripts]`` remains
authoritative for the runtime binding because the build backend reads it
verbatim. These tests keep the two in lockstep: a rename or a dropped/added
entry point in either source diverges and fails here, so the names cannot
silently drift.

Roadmap task 1.2.12 (ADR 007) adds the ``novel`` multiplexer beside the legacy
five, so the ``[project.scripts]`` view is now six entries, while the *operations*
intent is asserted separately against the spaced :data:`SUBCOMMAND_NAMES`.
"""

from __future__ import annotations

import importlib
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
    """The TOML parse order matches the registry-derived table order.

    ``tomllib`` preserves table key order, so comparing the parsed names to the
    registry-derived table keys (the legacy five then ``novel``) catches a
    reordering that the order-insensitive dict equality above would miss.
    """
    assert list(project_scripts(pyproject)) == list(names.project_scripts_table())


def test_entry_points_resolve_to_callables() -> None:
    """Every legacy registry entry-point function resolves to a callable."""
    for func in names.COMMAND_ENTRY_POINTS.values():
        assert callable(getattr(stub, func))


def test_multiplexer_entry_point_resolves_to_a_callable() -> None:
    """The ``novel`` script target resolves to a callable ``main``.

    The multiplexer binds to its own module rather than the stub, so the script
    table's ``novel`` target must point at a real callable just as the legacy
    five do (ADR 007).
    """
    target = names.project_scripts_table()[names.MULTIPLEXER_NAME]
    module_path, _, func = target.partition(":")
    module = importlib.import_module(module_path)
    assert callable(getattr(module, func))


def test_registry_pins_the_five_legacy_names() -> None:
    """The legacy registry pins exactly the five ADR-005 console-script names."""
    assert names.COMMAND_NAMES == (
        "novel-state",
        "novel-done",
        "novel-compile",
        "desloppify",
        "wordcount",
    )


def test_script_table_adds_the_novel_multiplexer() -> None:
    """The ``[project.scripts]`` view is the legacy five plus ``novel`` (ADR 007)."""
    assert tuple(names.project_scripts_table()) == (
        "novel-state",
        "novel-done",
        "novel-compile",
        "desloppify",
        "wordcount",
        "novel",
    )


def test_subcommand_names_pin_the_five_spaced_operations() -> None:
    """The spaced subcommand vocabulary pins the five ADR-007 operations."""
    assert names.SUBCOMMAND_NAMES == (
        "novel state",
        "novel done",
        "novel compile",
        "novel desloppify",
        "novel wordcount",
    )
