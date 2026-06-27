"""Structural anti-drift tests for the shared draft-read guard (roadmap 7.3.3).

Pin the single-home property of the draft-read fault guard after roadmap task
7.3.3 lifts the ``try/except STATE_INPUT_ERRORS → _draft_read_error`` shell out
of the three named command modules (``_wordcount``, ``_recount``,
``_desloppify``) into the
:func:`novel_ralph_skill.commands.state_sourcing.draft_read_guard` context
manager. The guard is the single home for *which* draft-read faults become exit
``3`` and *how* they re-raise, so a future edit must not silently re-fork it back
into a command module (AGENTS.md "Duplicated code" heuristic; the roadmap
definition of done: "a test pins it so it cannot silently re-fork").

The structural assertions, walking each migrated module with :mod:`ast` (not raw
substring matching — following the ``_state_layout_scanner`` /
``test_state_sourcing_home`` pattern), are:

- each migrated module imports ``draft_read_guard`` from
  ``novel_ralph_skill.commands.state_sourcing``; and
- no migrated module contains an ``except STATE_INPUT_ERRORS`` handler whose body
  re-raises a call to ``_draft_read_error`` — i.e. the open-coded guard shell is
  gone.

The three *out-of-scope* draft-read boundaries (``_novel_done`` and ``_compile``'s
two tails) are deliberately **not** scanned: roadmap task 7.3.3 names only the
three commands above, and those three still open-code the shell pending a later
slice (execplan Decision D2), so including them would falsely fail this test.

The public-seam assertion (``draft_read_guard`` is public and in
``state_sourcing.__all__``) mirrors ``test_state_sourcing_home``'s seam check
rather than duplicating its whole module scan.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from novel_ralph_skill.commands import state_sourcing

_STATE_SOURCING_MODULE = "novel_ralph_skill.commands.state_sourcing"

# The three roadmap-named command modules migrated in this slice. The two
# out-of-scope boundaries (``_novel_done.py`` and ``_compile.py``) are excluded
# on purpose: they still open-code the guard shell (execplan Decision D2), so
# scanning them would falsely fail the "no open-coded handler" assertion.
_MIGRATED_MODULES = ("_wordcount.py", "_recount.py", "_desloppify.py")


def _module_path(name: str) -> pathlib.Path:
    """Return the path to a command module beside ``state_sourcing``."""
    return pathlib.Path(state_sourcing.__file__).parent / name


def _imports_guard(node: ast.AST) -> bool:
    """Return whether ``node`` imports ``draft_read_guard`` from the home module."""
    if not isinstance(node, ast.ImportFrom) or node.module != _STATE_SOURCING_MODULE:
        return False
    return any(alias.name == "draft_read_guard" for alias in node.names)


def _imports_guard_from_state_sourcing(tree: ast.AST) -> bool:
    """Return whether the module imports ``draft_read_guard`` from the home."""
    return any(_imports_guard(node) for node in ast.walk(tree))


def _raises_named_call(node: ast.AST, name: str) -> bool:
    """Return whether ``node`` is a ``raise <name>(...)`` statement."""
    if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
        return False
    func = node.exc.func
    return isinstance(func, ast.Name) and func.id == name


def _raises_draft_read_error(body: list[ast.stmt]) -> bool:
    """Return whether a handler body re-raises a ``_draft_read_error(...)`` call."""
    return any(
        _raises_named_call(sub, "_draft_read_error")
        for node in body
        for sub in ast.walk(node)
    )


def _is_guard_context(item: ast.withitem) -> bool:
    """Return whether a ``with`` item enters ``draft_read_guard(...)``."""
    expr = item.context_expr
    if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name):
        return False
    return expr.func.id == "draft_read_guard"


def _uses_guard_in_with(tree: ast.AST) -> bool:
    """Return whether the module enters a ``with draft_read_guard(...)`` block.

    Walks every ``with``/``async with`` item for a context expression that calls
    the bare ``Name`` ``draft_read_guard`` — proving the module actually *uses*
    the shared guard, not merely imports it.
    """
    return any(
        _is_guard_context(item)
        for node in ast.walk(tree)
        if isinstance(node, ast.With | ast.AsyncWith)
        for item in node.items
    )


def _is_open_coded_guard_handler(node: ast.AST) -> bool:
    """Return whether ``node`` is an open-coded draft-read guard handler.

    The shell is an ``except STATE_INPUT_ERRORS`` handler whose body re-raises a
    ``_draft_read_error(...)`` call; checking both halves avoids flagging an
    unrelated ``STATE_INPUT_ERRORS`` handler.
    """
    if not isinstance(node, ast.ExceptHandler):
        return False
    caught = node.type
    if not (isinstance(caught, ast.Name) and caught.id == "STATE_INPUT_ERRORS"):
        return False
    return _raises_draft_read_error(node.body)


def _has_open_coded_guard(tree: ast.AST) -> bool:
    """Return whether the module still open-codes the draft-read guard shell."""
    return any(_is_open_coded_guard_handler(node) for node in ast.walk(tree))


@pytest.mark.parametrize("module_name", _MIGRATED_MODULES, ids=_MIGRATED_MODULES)
def test_migrated_module_imports_the_shared_guard(module_name: str) -> None:
    """Each migrated module imports ``draft_read_guard`` from the neutral home."""
    tree = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
    assert _imports_guard_from_state_sourcing(tree), (
        f"{module_name} must import draft_read_guard from {_STATE_SOURCING_MODULE}"
    )


@pytest.mark.parametrize("module_name", _MIGRATED_MODULES, ids=_MIGRATED_MODULES)
def test_migrated_module_uses_the_shared_guard(module_name: str) -> None:
    """Each migrated module actually enters a ``with draft_read_guard(...)`` block.

    Importing the guard is necessary but not sufficient: this pins that each
    migrated module *delegates* its draft read to the shared guard, so a module
    that imported it but reverted to some other (or no) fault routing fails here.
    """
    tree = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
    assert _uses_guard_in_with(tree), (
        f"{module_name} must enter a `with draft_read_guard(...)` block, not merely "
        "import it"
    )


@pytest.mark.parametrize("module_name", _MIGRATED_MODULES, ids=_MIGRATED_MODULES)
def test_migrated_module_has_no_open_coded_guard(module_name: str) -> None:
    """No migrated module re-grows the open-coded guard shell.

    A reappearing ``except STATE_INPUT_ERRORS`` handler that re-raises
    ``_draft_read_error(...)`` would silently re-fork the single home; this guard
    fails on it so the consolidation cannot drift back.
    """
    tree = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
    assert not _has_open_coded_guard(tree), (
        f"{module_name} still open-codes the draft-read guard shell; delegate to "
        "state_sourcing.draft_read_guard instead"
    )


def test_guard_is_public_in_the_home_seam() -> None:
    """``draft_read_guard`` is public (no leading underscore) and in ``__all__``."""
    assert not state_sourcing.draft_read_guard.__name__.startswith("_"), (
        "draft_read_guard must be public, not an underscore-private name"
    )
    assert callable(state_sourcing.draft_read_guard), (
        "draft_read_guard must be callable as a context-manager factory"
    )
    assert "draft_read_guard" in state_sourcing.__all__, (
        "draft_read_guard must be exported in state_sourcing.__all__ (the seam)"
    )
