"""Gate tying the command-name registry to ``[project.scripts]``.

The registry (:mod:`novel_ralph_skill.commands.names`) is the single source of
truth for the console-script names; ``pyproject.toml [project.scripts]`` remains
authoritative for the runtime binding because the build backend reads it
verbatim. These tests keep the two in lockstep: a rename or a dropped/added
entry point in either source diverges and fails here, so the names cannot
silently drift.

Roadmap task 1.2.15 (ADR 007) retired the legacy five, so the
``[project.scripts]`` view is the single ``novel`` multiplexer, while the
*operations* intent is asserted separately against the spaced
:data:`SUBCOMMAND_NAMES`.
"""

from __future__ import annotations

import importlib
import typing as typ

from novel_ralph_skill.commands import names
from novel_ralph_skill.contract import names as contract_names

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def test_registry_reexports_contract_vocabulary() -> None:
    """The registry re-exports the *same* contract vocabulary objects (no fork).

    Roadmap task 7.3.6 relocated the command-name vocabulary into
    :mod:`novel_ralph_skill.contract.names`; ``commands.names`` re-exports it.
    The identity check proves the re-export cannot silently fork into a second
    copy.
    """
    assert names.SUBCOMMAND_NAMES is contract_names.SUBCOMMAND_NAMES
    assert names.MULTIPLEXER_NAME is contract_names.MULTIPLEXER_NAME
    assert names.ENVELOPE_COMMAND_NAMES is contract_names.ENVELOPE_COMMAND_NAMES


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
    registry-derived table keys (the single ``novel`` entry) catches a
    reordering that the order-insensitive dict equality above would miss.
    """
    assert list(project_scripts(pyproject)) == list(names.project_scripts_table())


def test_multiplexer_entry_point_resolves_to_a_callable() -> None:
    """The ``novel`` script target resolves to a callable ``main``.

    The multiplexer binds to its own module, so the script table's ``novel``
    target must point at a real callable (ADR 007).
    """
    target = names.project_scripts_table()[names.MULTIPLEXER_NAME]
    module_path, _, func = target.partition(":")
    module = importlib.import_module(module_path)
    assert callable(getattr(module, func))


def test_script_table_is_novel_only() -> None:
    """The ``[project.scripts]`` view is exactly the single ``novel`` entry."""
    assert tuple(names.project_scripts_table()) == ("novel",)


def test_subcommand_names_pin_the_five_spaced_operations() -> None:
    """The spaced subcommand vocabulary pins the five ADR-007 operations."""
    assert names.SUBCOMMAND_NAMES == (
        "novel state",
        "novel done",
        "novel compile",
        "novel desloppify",
        "novel wordcount",
    )
