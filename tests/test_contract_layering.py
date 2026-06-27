"""Layering guard that the contract package never imports a commands module.

The contract layer sits *below* commands (ADR 003), so no module under
``novel_ralph_skill.contract`` may import a ``novel_ralph_skill.commands``
module: that would be a forbidden ``contract`` -> ``commands`` inversion. This
guard pins the rule statically over the **whole** ``contract`` package
(roadmap task 7.3.6), not merely the ``drive`` seam's home module
``novel_ralph_skill.contract.runner`` (roadmap task 7.3.5, the original
narrower guard, retained here as a focused special case).

The package-wide walk closes the inversion class for good: a future edit that
imported, say, ``commands.names`` or ``commands.state_sourcing`` into *any*
contract module — the way ``contract/envelope.py`` formerly imported
``commands.names.ENVELOPE_COMMAND_NAMES`` (the edge 7.3.6 removed) — fails here
rather than silently inverting the dependency.

This complements the import-laziness guard in
``tests/test_multiplexer_mount_table.py`` (importing ``novel`` pulls in no leaf
module): together they keep the contract layer orthogonal to the command layer
in both directions.

Each contract module's source is read statically (via
:func:`importlib.util.find_spec`, never executed) so the guard does not itself
import the contract runner — or any other contract module — at collection time.
Note that ``contract/finding_outcome.py`` carries a ``:func:`` docstring
cross-reference to a ``commands`` symbol; that is *not* an import, and the
``ast`` walk inspects only ``import``/``from``/dynamic-import nodes, so it does
not trip on the docstring (round-2 advisory 1).

Examples
--------
Run this guard alone with::

    uv run python -m pytest tests/test_contract_layering.py
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import pkgutil

# The fully qualified name and package of the seam's home module. Resolving the
# source statically (rather than importing the module) keeps this guard from
# executing the contract runner during collection.
_SEAM_MODULE = "novel_ralph_skill.contract.runner"
_SEAM_PACKAGE = "novel_ralph_skill.contract"

# The package prefix the contract layer must not import from. The contract layer
# sits below commands, so any import of a ``novel_ralph_skill.commands`` module
# from the seam's home module is a layering inversion.
_COMMANDS_PACKAGE = "novel_ralph_skill.commands"


# Scopes whose bodies do not run at module-import time: a function or lambda body
# is entered only when the callable is later invoked, so a deferred import inside
# a helper must be pruned from the module-scope scan. A *class* body, by contrast,
# executes when the class statement runs at import time, so it is **not** pruned —
# a class-level import (or ``import_module`` assignment) is a real module-scope
# import. The method ``FunctionDef`` nodes inside the class are still pruned when
# the walk reaches them.
_NESTED_SCOPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
)

# The dynamic-import callables a module-scope statement could use to dodge a
# static ``import``/``from`` scan: ``importlib.import_module("x")`` and the
# builtin ``__import__("x")``. Only string-literal first arguments are
# resolvable statically; a computed name is left to the laziness guard.
_DYNAMIC_IMPORT_NAMES = frozenset({"import_module", "__import__"})


def _resolve_import_from(node: ast.ImportFrom, package: str) -> set[str]:
    """Return the absolute module names a ``from … import …`` statement targets.

    Records both the source module and each imported member as a candidate
    module name, because an imported member can itself be a submodule: ``from
    novel_ralph_skill import commands`` must resolve to
    ``novel_ralph_skill.commands`` (the member), not merely the parent package.
    Relative imports (``from ..commands import names`` or ``from .. import
    commands``) are resolved against ``package`` so package-relative syntax cannot
    bypass the layering guard. Wildcard ``import *`` carries no member name and
    contributes only the source module.
    """
    if node.level:
        source = importlib.util.resolve_name(
            "." * node.level + (node.module or ""), package
        )
    elif node.module is not None:
        source = node.module
    else:  # pragma: no cover - an absolute ``from`` always names a module
        return set()
    candidates = {source}
    candidates.update(
        f"{source}.{alias.name}" for alias in node.names if alias.name != "*"
    )
    return candidates


def _callee_name(call: ast.Call) -> str | None:
    """Return the simple callee name of ``call`` (``Name`` id or ``Attribute`` tail).

    ``__import__("x")`` parses as an ``ast.Name`` callee; ``importlib.
    import_module("x")`` parses as an ``ast.Attribute`` whose ``attr`` tail is
    ``import_module``. Anything else yields ``None``.
    """
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_literal(node: ast.expr | None) -> str | None:
    """Return ``node``'s value if it is a string-literal constant, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _import_module_package(call: ast.Call, default: str) -> str:
    """Return the anchor ``import_module`` resolves a relative name against.

    ``import_module(name, package)`` accepts the anchor package as a second
    positional argument or a ``package=`` keyword; a string literal there is
    honoured so a relative dynamic import is resolved against the anchor the call
    actually uses, not the importing module's own package. A non-literal or
    absent anchor falls back to ``default``.
    """
    if len(call.args) > 1 and (literal := _string_literal(call.args[1])) is not None:
        return literal
    for keyword in call.keywords:
        if (
            keyword.arg == "package"
            and (literal := _string_literal(keyword.value)) is not None
        ):
            return literal
    return default


def _resolve_dynamic_import(call: ast.Call, package: str) -> str | None:
    """Return the module name a module-scope dynamic-import call targets, if static.

    Handles ``importlib.import_module("x")`` and ``__import__("x")`` with a
    string-literal first argument, resolving a relative target (a leading dot)
    against the anchor package the call uses (``import_module``'s ``package``
    argument when given, else ``package``). A computed (non-literal) argument is
    not statically resolvable and yields ``None``; such a case is left to the
    runtime import-laziness guard.
    """
    callee = _callee_name(call)
    if callee not in _DYNAMIC_IMPORT_NAMES or not call.args:
        return None
    name = _string_literal(call.args[0])
    if name is None:
        return None
    if name.startswith("."):
        anchor = (
            _import_module_package(call, package)
            if callee == "import_module"
            else package
        )
        return importlib.util.resolve_name(name, anchor)
    return name


def _module_scope_imports(source: str, package: str) -> set[str]:
    """Return the module names imported at module scope in ``source``.

    Collects ``import x`` targets, ``from x import …`` sources, and module-scope
    dynamic imports (``importlib.import_module("x")``/``__import__("x")`` with a
    string-literal argument) as *absolute* names. The walk descends through every
    node that runs at module-import time — including guarded/fallback bodies (``if
    TYPE_CHECKING``, ``try``/``except``, ``with``, loops, ``match``, and
    module-scope class bodies) and the expression trees of module-scope
    assignments — but prunes at function and lambda boundaries, since a deferred
    import inside a helper does not run at import time.
    """
    tree = ast.parse(source)
    modules: set[str] = set()
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, _NESTED_SCOPES):
            # A new scope: its body does not run at module-import time. Prune.
            continue
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.update(_resolve_import_from(node, package))
        elif isinstance(node, ast.Call) and (
            dynamic := _resolve_dynamic_import(node, package)
        ):
            modules.add(dynamic)
        stack.extend(ast.iter_child_nodes(node))
    return modules


def _read_module_source(module: str) -> str:
    """Return ``module``'s source text without importing it.

    Resolves the module's file via :func:`importlib.util.find_spec` and reads it
    off disk, so the guard inspects the source statically rather than executing
    the contract runner (or any other contract module) at collection time.
    """
    spec = importlib.util.find_spec(module)
    assert spec is not None, f"cannot locate {module}"
    assert spec.origin is not None, f"{module} has no source origin"
    return pathlib.Path(spec.origin).read_text(encoding="utf-8")


def _commands_imports(source: str, package: str) -> list[str]:
    """Return the ``commands`` modules ``source`` imports at module scope.

    A ``commands`` import is the package itself or any submodule of it; the
    result is sorted so a failure names the offenders deterministically.
    """
    return sorted(
        module
        for module in _module_scope_imports(source, package)
        if module == _COMMANDS_PACKAGE or module.startswith(f"{_COMMANDS_PACKAGE}.")
    )


def _contract_module_names() -> list[str]:
    """Return every importable module name under the ``contract`` package.

    Walks the package with :func:`pkgutil.iter_modules` over its ``__path__`` and
    includes the package's own ``__init__`` (which ``iter_modules`` does not
    yield), so the guard covers the package surface as well as its submodules.
    The list is sorted for a deterministic iteration order.
    """
    spec = importlib.util.find_spec(_SEAM_PACKAGE)
    assert spec is not None, f"cannot locate {_SEAM_PACKAGE}"
    assert spec.submodule_search_locations is not None, (
        f"{_SEAM_PACKAGE} is not a package"
    )
    names = {_SEAM_PACKAGE}
    names.update(
        f"{_SEAM_PACKAGE}.{info.name}"
        for info in pkgutil.iter_modules(spec.submodule_search_locations)
    )
    return sorted(names)


def test_contract_seam_home_imports_no_commands_module() -> None:
    """The ``drive`` seam's home module imports no ``commands`` module.

    Asserts ``novel_ralph_skill.contract.runner`` has no module-scope import of a
    ``novel_ralph_skill.commands`` module, pinning the Constraint that the seam
    takes resolved values as arguments rather than reaching into the command
    layer (no contract -> commands inversion). Retained as a focused special case
    of :func:`test_contract_package_imports_no_commands_module`.
    """
    offenders = _commands_imports(_read_module_source(_SEAM_MODULE), _SEAM_PACKAGE)
    assert not offenders, (
        "the contract seam's home module must not import a commands module "
        f"(contract -> commands inversion): {offenders}"
    )


def test_contract_package_imports_no_commands_module() -> None:
    """No module under the ``contract`` package imports a ``commands`` module.

    Widens the seam-only guard to the whole ``novel_ralph_skill.contract``
    package (roadmap 7.3.6), so the ``contract`` -> ``commands`` inversion class
    is closed for good: a future edit that imports any ``commands`` module into
    any contract module fails here. The walk is asserted non-empty so a packaging
    change that hides the modules cannot make the guard pass vacuously (round-2
    pre-mortem Scenario A).
    """
    modules = _contract_module_names()
    assert modules, "the contract package walk found no modules (guard is vacuous)"
    offenders = {
        module: imports
        for module in modules
        if (imports := _commands_imports(_read_module_source(module), _SEAM_PACKAGE))
    }
    assert not offenders, (
        "no contract module may import a commands module "
        f"(contract -> commands inversion): {offenders}"
    )
