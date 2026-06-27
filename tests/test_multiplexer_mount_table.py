"""Structural tests for the ``novel`` multiplexer construction table (7.3.2).

Roadmap task 7.3.2 collapses the five hand-copied mount lines in
:func:`novel_ralph_skill.commands.novel.build_multiplexer` onto a single
registry-driven construction table: a bare-verb-keyed mapping of mount verb to
the leaf module's ``build_app`` factory, consumed by one mount loop. This module
pins that table against the names registry so a dropped, drifted, or swapped
mount fails a test rather than shipping (ExecPlan Decision Log D1).

The seam the refactor exposes is the module-level helper
:func:`novel_ralph_skill.commands.novel._build_mount_table`, which returns the
ordered ``{verb: build_app}`` mapping. These tests assert: the table's verb set
equals the registry's bare-verb set (``_SUBCOMMAND_FOR_VERB``); each table value
is the leaf module's own ``build_app`` by object identity; and the built parent
app registers exactly the table's verbs. The behavioural parity these structural
guards complement lives in ``tests/test_multiplexer_behaviour.py``.
"""

from __future__ import annotations

import inspect
import typing as typ

import pytest

from novel_ralph_skill.commands import (
    _compile,
    _desloppify,
    _novel_done,
    _wordcount,
    novel,
    novel_state,
)

if typ.TYPE_CHECKING:
    from types import ModuleType

# The five ``(verb, leaf module)`` pairs the construction table must map, in the
# ADR 007 surface order. Each table value must be the leaf module's own
# ``build_app`` by object identity, so a swapped or wrapped builder fails.
_VERB_MODULE_PAIRS = (
    ("state", novel_state),
    ("done", _novel_done),
    ("compile", _compile),
    ("desloppify", _desloppify),
    ("wordcount", _wordcount),
)

# The five leaf module names whose imports the laziness invariant (Decision D2)
# requires live *inside* ``_build_mount_table``, never at module scope, so
# importing ``novel`` pulls in no leaf module.
_LEAF_MODULE_NAMES = tuple(
    module.__name__.rsplit(".", 1)[1] for _, module in _VERB_MODULE_PAIRS
)


def _build_mount_table_source() -> str:
    """Return the source text of ``novel._build_mount_table``.

    Used by the laziness guard to confirm the five deferred leaf imports live
    inside the helper body rather than at module scope.
    """
    return inspect.getsource(novel._build_mount_table)


def _novel_module_source_outside_mount_table() -> str:
    """Return ``novel``'s module source with the mount-table helper removed.

    The laziness guard asserts that no leaf-import statement survives in this
    remainder at module scope (column 0), so a future hoist of the construction
    table — and its leaf imports — to module level fails the guard.
    """
    module_source = inspect.getsource(novel)
    helper_source = _build_mount_table_source()
    return module_source.replace(helper_source, "")


def test_mount_table_verbs_equal_the_registry_bare_verbs() -> None:
    """The table's verb keys equal the registry's bare-verb set by construction.

    ``_SUBCOMMAND_FOR_VERB`` is keyed by the bare verbs (``"state"``, …); the
    construction table is keyed by the same bare verbs, so the two key sets must
    be equal. Comparing against ``_VERB_FOR_SUBCOMMAND`` (keyed by the *spaced*
    names) would always be ``False`` (disjoint sets), so the bare-verb map is the
    correct comparand.
    """
    assert set(novel._build_mount_table()) == set(novel._SUBCOMMAND_FOR_VERB)


@pytest.mark.parametrize(
    ("verb", "module"),
    _VERB_MODULE_PAIRS,
    ids=[verb for verb, _ in _VERB_MODULE_PAIRS],
)
def test_mount_table_value_is_the_leaf_build_app(verb: str, module: ModuleType) -> None:
    """Each table value is the leaf module's own ``build_app`` (object identity).

    A swapped or wrapped builder — for instance one that re-routed through a
    decorator or a copy — fails by identity rather than slipping past a mere
    callable check.
    """
    assert novel._build_mount_table()[verb] is module.build_app


def test_build_multiplexer_registers_exactly_the_table_verbs() -> None:
    """The built parent registers exactly the construction table's verbs.

    A Cyclopts ``App`` is a mapping of command name to sub-app; iterating it
    yields the built-in ``--help``/``-h``/``--version`` meta-commands too, so the
    flag keys are filtered out before the mount names are compared. Tying the
    registered names back to ``_build_mount_table()`` (and, via the test above, to
    the registry) means a dropped or drifted mount fails here.
    """
    app = novel.build_multiplexer()
    registered = {name for name in app if not name.startswith("-")}
    assert registered == set(novel._build_mount_table())


@pytest.mark.parametrize("leaf_name", _LEAF_MODULE_NAMES, ids=_LEAF_MODULE_NAMES)
def test_leaf_import_lives_inside_the_mount_table_helper(leaf_name: str) -> None:
    """Each leaf import lives inside ``_build_mount_table``, never at module scope.

    Pins the import-laziness invariant (ExecPlan Decision Log D2): importing
    ``novel`` must pull in no leaf module, so the five deferred leaf imports must
    live inside the helper body. The guard is a static, in-process textual
    inspection — a ``sys.modules`` absence check is structurally impossible here
    because this module imports the leaves at module scope for the identity tests
    above, so by the time any test runs the leaves are already resident.

    The check has two arms: the leaf name must appear in the helper's own source
    (the deferred import block is inside it), and the leaf name must **not**
    appear anywhere in ``novel``'s module source once the helper's source slice is
    removed (no module-scope leaf import survives). A future edit that hoists the
    construction table — and its leaf imports — to module level fails this guard's
    case for the hoisted leaf. (Self-proof: temporarily moving one leaf import to
    module scope turns this test red, confirming it is load-bearing.)
    """
    assert leaf_name in _build_mount_table_source()
    assert leaf_name not in _novel_module_source_outside_mount_table()
