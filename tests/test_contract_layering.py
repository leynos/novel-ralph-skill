"""Layering guard that the contract seam never imports a commands module (7.3.5).

The contract-level :func:`~novel_ralph_skill.contract.runner.drive` seam lifts the
entry-point drive plumbing into the contract layer (roadmap task 7.3.5). Its
home module — ``novel_ralph_skill.contract.runner`` — must not reach into the
commands layer to resolve the command name or working directory: the seam takes
those as already-resolved arguments. This pins the ADR 003 layering rule
(contract -> commands is a forbidden inversion) statically, so a future edit that
imported, say, ``commands.names`` or ``commands.state_sourcing`` into the seam's
home module would fail here rather than silently inverting the dependency.

This complements the import-laziness guard in
``tests/test_multiplexer_mount_table.py`` (importing ``novel`` pulls in no leaf
module): together they keep the seam orthogonal to the command layer in both
directions.

The seam module's source is read statically (via :func:`importlib.util.find_spec`,
never executed) so the guard does not itself import the contract runner at
collection time.

Examples
--------
Run this guard alone with::

    uv run python -m pytest tests/test_contract_layering.py
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib

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


def _read_seam_source() -> str:
    """Return the seam home module's source text without importing it.

    Resolves the module's file via :func:`importlib.util.find_spec` and reads it
    off disk, so the guard inspects the source statically rather than executing
    the contract runner at collection time.
    """
    spec = importlib.util.find_spec(_SEAM_MODULE)
    assert spec is not None, f"cannot locate {_SEAM_MODULE}"
    assert spec.origin is not None, f"{_SEAM_MODULE} has no source origin"
    return pathlib.Path(spec.origin).read_text(encoding="utf-8")


def test_contract_seam_home_imports_no_commands_module() -> None:
    """The ``drive`` seam's home module imports no ``commands`` module.

    Asserts ``novel_ralph_skill.contract.runner`` has no module-scope import of a
    ``novel_ralph_skill.commands`` module, pinning the Constraint that the seam
    takes resolved values as arguments rather than reaching into the command
    layer (no contract -> commands inversion).
    """
    offenders = sorted(
        module
        for module in _module_scope_imports(_read_seam_source(), _SEAM_PACKAGE)
        if module == _COMMANDS_PACKAGE or module.startswith(f"{_COMMANDS_PACKAGE}.")
    )
    assert not offenders, (
        "the contract seam's home module must not import a commands module "
        f"(contract -> commands inversion): {offenders}"
    )
