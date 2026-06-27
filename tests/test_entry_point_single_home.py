"""Structural guard that ``novel.main`` re-spells no entry-point plumbing (7.3.5).

Roadmap task 7.3.5 lifts the build-:class:`RunContext`-then-call-``run`` plumbing
out of the ``novel`` entry point and into the contract-level
:func:`~novel_ralph_skill.contract.runner.drive` seam, so the plumbing lives in
one explicit home (the step-7.3 command-facade single-home hypothesis). This
module pins that invariant statically: an ``ast`` walk over the ``main``
``FunctionDef`` asserts its body constructs no inline ``RunContext`` and calls
``run`` nowhere directly — it routes solely through ``drive``. A future entry
point that re-inlined the plumbing (re-opening the silent-skew failure mode the
task names) would fail here rather than shipping.

The "exactly one production console-script entry point" half of the single-home
invariant is already pinned by
``tests/test_legacy_surface_retired.py::test_pyproject_scripts_is_novel_only``
and ``::test_script_table_is_novel_only`` (via the shared
``pyproject``/``project_scripts`` conftest fixtures, Decision Log D7); this module
references those rather than re-parsing ``pyproject.toml`` (the developers-guide
"Shared test scaffolding" rule).

This guard and the migrated 1.3.6 routing tripwire
(``tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam``)
describe the **same** post-extraction surface — ``main`` routes through ``drive``,
not ``run`` — and are complementary, not contradictory (Decision Log D5).
"""

from __future__ import annotations

import ast
import inspect

from novel_ralph_skill.commands import novel

# The plumbing symbols ``main`` must not call directly after the extraction:
# ``RunContext`` (no inline context construction) and ``run`` (no direct drive).
# Both now live only behind the ``drive`` seam.
_FORBIDDEN_CALLEES = frozenset({"RunContext", "run"})


def _callee_name(call: ast.Call) -> str | None:
    """Return the simple callee name of ``call`` (``Name`` id or ``Attribute`` tail).

    ``RunContext(...)`` and ``run(...)`` parse as ``ast.Name`` callees;
    ``module.run(...)`` parses as an ``ast.Attribute`` whose ``attr`` tail is the
    name. Anything else (a subscript, a call result) yields ``None`` and is not a
    forbidden callee.
    """
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _calls_in_executable_body(func_def: ast.FunctionDef) -> list[ast.Call]:
    """Return the ``Call`` nodes in ``func_def``'s own body, skipping nested scopes.

    ``ast.walk`` descends into nested functions, lambdas, and class bodies, so a
    plain walk would attribute a ``run``/``RunContext`` call hidden inside a
    nested helper to ``main`` — or double-count a nested ``drive`` call. This
    walks only the executable statements of ``func_def`` itself, pruning the
    subtree at any nested scope boundary (``FunctionDef``/``AsyncFunctionDef``/
    ``Lambda``/``ClassDef``) so the guards describe ``main``'s direct surface.
    """
    calls: list[ast.Call] = []
    nested_scopes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ClassDef,
    )
    # Seed the stack from ``main``'s body, not ``func_def`` itself, so its own
    # FunctionDef node does not count as a pruned nested scope.
    stack: list[ast.AST] = list(func_def.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Call):
            calls.append(node)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nested_scopes):
                continue
            stack.append(child)
    return calls


def _main_function_def() -> ast.FunctionDef:
    """Return the ``ast`` ``FunctionDef`` node for ``novel.main``.

    Parses ``novel.py``'s source and locates the module-scope ``main`` definition,
    mirroring the in-repo ``ast`` scanner pattern (``tests/test_state_sourcing_home``
    and the mount-table laziness guard) rather than a brittle substring scan.
    """
    tree = ast.parse(inspect.getsource(novel))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    message = "novel.main FunctionDef not found in the module source"
    raise AssertionError(message)


def test_main_constructs_no_inline_runcontext_or_run_call() -> None:
    """``novel.main`` makes no direct ``RunContext``/``run`` call (single home).

    Walks the ``Call`` nodes in ``main``'s own executable body (skipping nested
    scopes) and asserts none resolves to ``RunContext`` or ``run``: the
    build-context-then-``run`` plumbing lives only behind ``drive``. A docstring
    mention of ``RunContext`` cannot false-fail because only ``Call`` callees are
    inspected, not free text.
    """
    main_def = _main_function_def()
    offending = sorted({
        name
        for call in _calls_in_executable_body(main_def)
        if (name := _callee_name(call)) in _FORBIDDEN_CALLEES
    })
    assert not offending, (
        "novel.main re-inlines entry-point plumbing instead of routing through "
        f"the drive seam: it calls {offending}"
    )


def test_main_routes_through_the_drive_seam() -> None:
    """``novel.main`` calls ``drive`` exactly once (the single entry-point home).

    The positive complement of the forbidden-callee guard: the plumbing did not
    merely disappear, it moved behind exactly one ``drive`` call.
    """
    main_def = _main_function_def()
    drive_calls = [
        call
        for call in _calls_in_executable_body(main_def)
        if _callee_name(call) == "drive"
    ]
    assert len(drive_calls) == 1, (
        "novel.main must route through exactly one drive() call; found "
        f"{len(drive_calls)}"
    )
