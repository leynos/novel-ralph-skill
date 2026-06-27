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

import ast
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


def _imported_names(node: ast.Import | ast.ImportFrom) -> frozenset[str]:
    """Return the leaf module names an import statement brings into scope.

    Both ``import x.y`` and ``from x import y`` introduce the binding ``y``; the
    laziness guard cares only about that bound leaf name, so the dotted prefix on
    an ``import`` and the package path on a ``from`` import are discarded. An
    aliased import (``import x as z``) binds the alias, which can never be a leaf
    name, so it is excluded.
    """
    return frozenset(
        alias.asname or alias.name.rsplit(".", 1)[-1] for alias in node.names
    )


def _module_scope_imported_leaves() -> frozenset[str]:
    """Return the leaf module names imported at ``novel``'s module scope.

    Walks the parsed module's top-level body for ``Import``/``ImportFrom`` nodes
    (``col_offset == 0``, never nested in a function or class) and collects the
    leaf names they bind, intersected with :data:`_LEAF_MODULE_NAMES`. The
    laziness invariant (Decision D2) requires this set be empty: importing
    ``novel`` must pull in no leaf module.
    """
    tree = ast.parse(inspect.getsource(novel))
    leaves: set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)) and stmt.col_offset == 0:
            leaves |= _imported_names(stmt) & frozenset(_LEAF_MODULE_NAMES)
    return frozenset(leaves)


def _mount_table_imported_leaves() -> frozenset[str]:
    """Return the leaf module names imported inside ``_build_mount_table``.

    Parses ``novel``'s source, locates the ``_build_mount_table`` ``FunctionDef``,
    and walks its body for ``Import``/``ImportFrom`` nodes, collecting the leaf
    names they bind. The deferred-import arm of the guard requires every leaf in
    :data:`_LEAF_MODULE_NAMES` appear here.
    """
    tree = ast.parse(inspect.getsource(novel))
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_build_mount_table"
    )
    leaves: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            leaves |= _imported_names(node)
    return frozenset(leaves)


def test_fixture_verbs_equal_the_registry_bare_verbs() -> None:
    """The ``_VERB_MODULE_PAIRS`` fixture verbs equal the registry's bare verbs.

    The fixture hand-pairs each bare verb with its leaf module for the identity
    and laziness tests above. This guard ties its verb keys back to the single
    registry (``_SUBCOMMAND_FOR_VERB``, bare-verb-keyed) so the test surface
    cannot silently drift from the registry the production mount loop reads — a
    renamed, dropped, or added registry verb fails here rather than leaving a
    stale fixture pinning a phantom mount (Addendum 7.3.2.2).
    """
    fixture_verbs = {verb for verb, _ in _VERB_MODULE_PAIRS}
    assert fixture_verbs == set(novel._SUBCOMMAND_FOR_VERB)


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


def test_build_multiplexer_registers_mounts_in_surface_order() -> None:
    """The registered mount order equals the registry's bare-verb order.

    The ``--help`` listing order — the one behaviourally observable consequence
    of mount order — is fixed by the order ``build_multiplexer`` iterates, which
    is ``list(novel._SUBCOMMAND_FOR_VERB)`` (the ADR 007 surface order). The
    sibling guards above assert mount *membership* by set-equality only; this
    pins the *sequence*, so a reordered registry or a mount loop that stopped
    reading it in order fails here. The mount loop, not the construction table's
    own iteration order, is what fixes the surface order, so this asserts against
    the registry the loop reads rather than against ``_build_mount_table()``.
    """
    app = novel.build_multiplexer()
    registered = [name for name in app if not name.startswith("-")]
    assert registered == list(novel._SUBCOMMAND_FOR_VERB)


@pytest.mark.parametrize("leaf_name", _LEAF_MODULE_NAMES, ids=_LEAF_MODULE_NAMES)
def test_leaf_import_lives_inside_the_mount_table_helper(leaf_name: str) -> None:
    """Each leaf import lives inside ``_build_mount_table``, never at module scope.

    Pins the import-laziness invariant (ExecPlan Decision Log D2): importing
    ``novel`` must pull in no leaf module, so the five deferred leaf imports must
    live inside the helper body. The guard is a static, in-process ``ast`` walk —
    a ``sys.modules`` absence check is structurally impossible here because this
    module imports the leaves at module scope for the identity tests above, so by
    the time any test runs the leaves are already resident.

    The check pins import *location* rather than string presence: the leaf must be
    imported inside the ``_build_mount_table`` ``FunctionDef`` body, and must
    **not** be imported by any module-scope (``col_offset == 0``)
    ``Import``/``ImportFrom`` node. Because it inspects parsed import statements
    rather than scanning raw source text, a docstring or comment that legitimately
    names a leaf module no longer false-fails the guard, and an aliased or
    differently-spelled import cannot slip past it. A future edit that hoists the
    construction table — and its leaf imports — to module level fails the
    module-scope arm for the hoisted leaf. (Self-proof: temporarily moving one
    leaf import to module scope turns this test red, confirming it is
    load-bearing — see the ``ast`` scanner pattern in
    ``tests/_state_layout_scanner.py``.)
    """
    assert leaf_name in _mount_table_imported_leaves()
    assert leaf_name not in _module_scope_imported_leaves()
