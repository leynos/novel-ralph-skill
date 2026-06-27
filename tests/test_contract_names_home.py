"""Structural and unit guards pinning the contract command-name vocabulary home.

Roadmap task 7.3.6 relocates the command-name vocabulary
(:data:`MULTIPLEXER_NAME`, :data:`SUBCOMMAND_NAMES`,
:data:`ENVELOPE_COMMAND_NAMES`) into :mod:`novel_ralph_skill.contract.names`, so
the ``contract`` package owns the contract vocabulary the envelope guard
enforces (ADR 003). :mod:`novel_ralph_skill.commands.names` re-exports it for
back-compatibility.

These tests pin two facts:

- the vocabulary is importable from ``contract.names`` with its pinned values,
  and the ``commands.names`` re-export is the *same object* (no second copy);
- ``contract.names`` imports nothing from ``novel_ralph_skill.commands`` at
  module scope, so no ``contract`` -> ``commands`` cycle can form (ExecPlan
  Decision Log D1).

The structural guard parses ``contract/names.py`` with :mod:`ast`, reusing the
module-scope import walk from :mod:`tests.test_contract_layering`, so it does not
depend on import-time side effects.
"""

from __future__ import annotations

import importlib.util
import pathlib

import novel_ralph_skill.contract as contract_package
from novel_ralph_skill.commands import names as commands_names
from novel_ralph_skill.commands import state_sourcing
from novel_ralph_skill.contract import names as contract_names
from tests.test_contract_layering import _module_scope_imports

_CONTRACT_NAMES_MODULE = "novel_ralph_skill.contract.names"
_CONTRACT_PACKAGE = "novel_ralph_skill.contract"
_COMMANDS_PACKAGE = "novel_ralph_skill.commands"


def _read_module_source(module: str) -> str:
    """Return ``module``'s source text without importing it.

    Resolves the module's file via :func:`importlib.util.find_spec` and reads it
    off disk, so the structural guard inspects the source statically.
    """
    spec = importlib.util.find_spec(module)
    assert spec is not None, f"cannot locate {module}"
    assert spec.origin is not None, f"{module} has no source origin"
    return pathlib.Path(spec.origin).read_text(encoding="utf-8")


def test_vocabulary_imports_from_contract_names() -> None:
    """The command-name vocabulary lives in ``contract.names`` with pinned values."""
    assert contract_names.MULTIPLEXER_NAME == "novel"
    assert contract_names.SUBCOMMAND_NAMES == (
        "novel state",
        "novel done",
        "novel compile",
        "novel desloppify",
        "novel wordcount",
    )
    # The guard superset: the five spaced names plus the bare ``"novel"``,
    # de-duplicated in first-seen order.
    assert contract_names.ENVELOPE_COMMAND_NAMES == (
        "novel state",
        "novel done",
        "novel compile",
        "novel desloppify",
        "novel wordcount",
        "novel",
    )


def test_commands_names_reexports_contract_vocabulary() -> None:
    """``commands.names`` re-exports the *same* vocabulary objects (no fork)."""
    assert commands_names.MULTIPLEXER_NAME is contract_names.MULTIPLEXER_NAME
    assert commands_names.SUBCOMMAND_NAMES is contract_names.SUBCOMMAND_NAMES
    assert (
        commands_names.ENVELOPE_COMMAND_NAMES is contract_names.ENVELOPE_COMMAND_NAMES
    )


def test_working_dir_name_imports_from_contract() -> None:
    """``WORKING_DIR_NAME`` resolves to ``"working"`` from the contract package.

    Both the package re-export (``contract.WORKING_DIR_NAME``) and the owning
    submodule (``contract.names.WORKING_DIR_NAME``) resolve to ``"working"``
    (roadmap 7.3.6 WI2).
    """
    assert contract_package.WORKING_DIR_NAME == "working"
    assert contract_names.WORKING_DIR_NAME == "working"
    assert contract_package.WORKING_DIR_NAME is contract_names.WORKING_DIR_NAME


def test_state_sourcing_reexports_contract_working_dir_name() -> None:
    """``state_sourcing`` re-exports the *same* ``WORKING_DIR_NAME`` (no fork).

    The identity check proves the constant now originates in ``contract.names``
    and is re-exported from ``state_sourcing`` rather than redefined there
    (roadmap 7.3.6 WI2).
    """
    assert state_sourcing.WORKING_DIR_NAME is contract_names.WORKING_DIR_NAME
    assert "WORKING_DIR_NAME" in state_sourcing.__all__


def test_contract_names_imports_no_commands_module() -> None:
    """``contract.names`` imports no ``commands`` module at module scope.

    Pins the no-cycle Constraint: the relocated vocabulary is pure naming data
    with no command dependency, so ``contract.names`` must not reach up into the
    commands layer (ExecPlan Decision Log D1).
    """
    offenders = sorted(
        module
        for module in _module_scope_imports(
            _read_module_source(_CONTRACT_NAMES_MODULE), _CONTRACT_PACKAGE
        )
        if module == _COMMANDS_PACKAGE or module.startswith(f"{_COMMANDS_PACKAGE}.")
    )
    assert not offenders, (
        "contract.names must not import a commands module "
        f"(contract -> commands inversion): {offenders}"
    )
