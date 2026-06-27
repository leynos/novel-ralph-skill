"""Structural tests pinning the neutral state-sourcing home (roadmap 7.3.1).

Pin the **public-home** property of the state-sourcing seam after it is lifted
out of :mod:`novel_ralph_skill.commands.novel_state` into the neutral,
public-named :mod:`novel_ralph_skill.commands.state_sourcing` home: the seam
imports cleanly from the neutral module, and ``load_or_state_error`` is a
public, callable name in the module's ``__all__`` (it carries no leading
underscore).

The complementary **no-`novel_state`-dependency** assertion checks that no
command module under ``novel_ralph_skill/commands/`` (other than
``novel_state.py`` itself, which keeps the genuine ``check``/``init`` surface)
imports any migrated seam symbol from ``novel_state``. It parses each module
with :mod:`ast` so a hit names the offending module precisely and does not
depend on import-time side effects.
"""

from __future__ import annotations

import ast
import pathlib

from novel_ralph_skill.commands import state_sourcing

# The public state-sourcing seam this home owns. ``load_or_state_error`` is the
# only formerly-underscore name promoted to public (roadmap 7.3.1 Decision D3);
# the actionable-message formatters stay module-private and so are not part of
# the public seam surface asserted here.
_PUBLIC_SEAM = (
    "STATE_INPUT_ERRORS",
    "WORKING_DIR_NAME",
    "load_or_state_error",
    "resolved_working_dir",
    "state_path",
    "working_dir",
)


def test_public_seam_is_importable_from_the_neutral_home() -> None:
    """The public seam imports from ``state_sourcing`` and is exported."""
    from novel_ralph_skill.commands.state_sourcing import (
        STATE_INPUT_ERRORS,
        WORKING_DIR_NAME,
        load_or_state_error,
        resolved_working_dir,
        state_path,
        working_dir,
    )

    # Reference the imports so the binding is exercised, not merely parsed.
    assert WORKING_DIR_NAME == "working"
    assert isinstance(STATE_INPUT_ERRORS, tuple)
    assert callable(working_dir)
    assert callable(resolved_working_dir)
    assert callable(state_path)
    assert callable(load_or_state_error)

    for name in _PUBLIC_SEAM:
        assert name in state_sourcing.__all__, (
            f"{name!r} must be in state_sourcing.__all__ (the public seam home)"
        )


def test_loader_name_is_public() -> None:
    """``load_or_state_error`` is public (no leading underscore) and callable."""
    assert not state_sourcing.load_or_state_error.__name__.startswith("_"), (
        "load_or_state_error must be public, not the underscore-private name"
    )
    assert callable(state_sourcing.load_or_state_error)
    assert "load_or_state_error" in state_sourcing.__all__


_NOVEL_STATE_MODULE = "novel_ralph_skill.commands.novel_state"

# Every migrated state-sourcing seam symbol — the public seam plus the
# underscore-private actionable-message formatters that move with the home. A
# command importing any of these from ``novel_state`` re-pins the seam onto the
# command facade, the dependency this task removes. ``INSPECT_REPAIR_REMEDY`` is
# deliberately excluded: it is module-internal to ``state_sourcing`` (no
# consumer imports it), so it is not a migrated seam symbol.
_SEAM_SYMBOLS = frozenset({
    "STATE_INPUT_ERRORS",
    "WORKING_DIR_NAME",
    "load_or_state_error",
    "state_path",
    "working_dir",
    "resolved_working_dir",
    "_state_input_error",
    "_draft_read_error",
    "_compile_write_error",
    "_rule_pack_read_error",
    "_device_ledger_read_error",
})


def _command_modules() -> list[pathlib.Path]:
    """Return every command module except ``novel_state.py`` and dunders."""
    commands_dir = pathlib.Path(state_sourcing.__file__).parent
    return sorted(
        path
        for path in commands_dir.glob("*.py")
        if path.name not in {"novel_state.py", "__init__.py"}
    )


def _seam_imports_from_novel_state(source: str) -> set[str]:
    """Return the seam names a module imports from ``novel_state``."""
    tree = ast.parse(source)
    return {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == _NOVEL_STATE_MODULE
        for alias in node.names
        if alias.name in _SEAM_SYMBOLS
    }


def test_no_command_imports_the_seam_from_novel_state() -> None:
    """No command re-pins a migrated seam symbol onto ``novel_state``."""
    offenders = {
        module.name: sorted(seams)
        for module in _command_modules()
        if (seams := _seam_imports_from_novel_state(module.read_text()))
    }
    assert not offenders, (
        "these command modules still import a migrated state-sourcing seam from "
        f"novel_state instead of state_sourcing: {offenders}"
    )
