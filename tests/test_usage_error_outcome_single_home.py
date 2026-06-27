"""Structural guard that the exit-2 usage envelope lives in one home (7.3.7).

Roadmap task 7.3.7 lifts the body-detected exit-``2`` ("usage error") envelope
into the single contract-layer home
:func:`~novel_ralph_skill.contract.runner.usage_error_outcome` (the step-7.3
command-facade single-home hypothesis). This module pins that invariant
statically: an ``ast`` walk over every module under
``novel_ralph_skill.commands`` asserts none of them re-spells the
``CommandOutcome(code=ExitCode.USAGE_ERROR, ...)`` construction inline — a
body-detected exit-2 envelope must route through the shared helper. A future
command module that re-inlined the idiom (re-opening the silent-drift failure
mode the task names) would fail here rather than shipping.

Scope exclusion (ExecPlan Decision D3): the scan covers the ``commands`` package
only. It deliberately does **not** scan ``novel_ralph_skill.contract.runner``,
whose ``CommandOutcome(code=ExitCode.USAGE_ERROR, ...)`` arm (the
``str(CycloptsError)`` path) is the legitimate single home for a *parser*-detected
usage fault — a different concern from a body-detected one. Folding it into the
helper would couple the runner to the body-fault shape; it stays the home of its
own arm. A future reader must not "fix" this guard by widening scope to the
runner.

The command modules' source is read statically (via
:func:`importlib.util.find_spec`, never executed) so the guard does not import the
command layer at collection time, mirroring
``tests/test_contract_layering.py``.

Examples
--------
Run this guard alone with::

    uv run python -m pytest tests/test_usage_error_outcome_single_home.py
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import typing as typ

# The package whose modules must route every body-detected exit-2 envelope through
# the shared helper rather than re-spelling the CommandOutcome construction inline.
_COMMANDS_PACKAGE = "novel_ralph_skill.commands"

# The callee and the ``code`` keyword value that together mark the exit-2 envelope
# construction the helper now owns.
_OUTCOME_CALLEE = "CommandOutcome"
_USAGE_ERROR_ATTR = "USAGE_ERROR"


def _callee_name(call: ast.Call) -> str | None:
    """Return the simple callee name of ``call`` (``Name`` id or ``Attribute`` tail).

    ``CommandOutcome(...)`` parses as an ``ast.Name`` callee; ``module.
    CommandOutcome(...)`` parses as an ``ast.Attribute`` whose ``attr`` tail is the
    name. Anything else (a subscript, a call result) yields ``None``.
    """
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_usage_error_keyword(keyword: ast.keyword) -> bool:
    """Return whether ``keyword`` is ``code=...USAGE_ERROR`` (the exit-2 marker).

    Matches a ``code`` keyword whose value is an ``ast.Attribute`` tail of
    ``USAGE_ERROR`` (``ExitCode.USAGE_ERROR``), the exit-code keyword the shared
    helper now owns. A ``code`` set to any other exit code (``SUCCESS``,
    ``ACTIONABLE_FINDING``, ``STATE_ERROR``) is a legitimate inline construction
    and is not matched.
    """
    return (
        keyword.arg == "code"
        and isinstance(keyword.value, ast.Attribute)
        and keyword.value.attr == _USAGE_ERROR_ATTR
    )


def _is_inline_usage_outcome(node: ast.AST) -> typ.TypeGuard[ast.Call]:
    """Return whether ``node`` is an inline exit-2 ``CommandOutcome`` call.

    A ``CommandOutcome(...)`` call carrying a ``code=...USAGE_ERROR`` keyword — the
    construction the shared
    :func:`~novel_ralph_skill.contract.runner.usage_error_outcome` home now owns,
    and therefore a re-spelled exit-2 envelope that should route through the helper.
    Narrows ``node`` to :class:`ast.Call` so callers may read its ``lineno``.
    """
    return (
        isinstance(node, ast.Call)
        and _callee_name(node) == _OUTCOME_CALLEE
        and any(_is_usage_error_keyword(kw) for kw in node.keywords)
    )


def _inline_usage_outcomes(source: str) -> list[int]:
    """Return the line numbers of inline exit-2 ``CommandOutcome`` calls in ``source``.

    Walks the whole module ``ast`` for every inline exit-2 ``CommandOutcome``
    construction (see :func:`_is_inline_usage_outcome`).
    """
    tree = ast.parse(source)
    return [node.lineno for node in ast.walk(tree) if _is_inline_usage_outcome(node)]


def _module_name(package_dir: pathlib.Path, path: pathlib.Path) -> str:
    """Return the dotted module name of ``path`` relative to the commands package.

    A package ``__init__.py`` resolves to its package name (the parent parts); any
    other ``*.py`` resolves to its file stem appended to its parent parts. The
    parts join under :data:`_COMMANDS_PACKAGE` so a nested subpackage module names
    correctly rather than colliding on a bare stem.
    """
    relative = path.relative_to(package_dir).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join((_COMMANDS_PACKAGE, *parts))


def _command_module_sources() -> dict[str, str]:
    """Return ``{module_name: source}`` for every module under the commands package.

    Resolves the package directory via :func:`importlib.util.find_spec` and reads
    each ``*.py`` file off disk (never importing it), so the guard inspects the
    source statically rather than executing the command layer at collection time.
    The walk recurses into subpackages (``rglob``), skipping ``__pycache__``, so
    every command module is scanned — including any future addition or nested
    subpackage — and a new command cannot reintroduce the inline idiom silently.
    """
    spec = importlib.util.find_spec(_COMMANDS_PACKAGE)
    assert spec is not None, f"cannot locate {_COMMANDS_PACKAGE}"
    assert spec.submodule_search_locations, (
        f"{_COMMANDS_PACKAGE} is not a package with a directory"
    )
    package_dir = pathlib.Path(spec.submodule_search_locations[0])
    return {
        _module_name(package_dir, path): path.read_text(encoding="utf-8")
        for path in sorted(package_dir.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def test_command_modules_route_exit_2_through_the_shared_helper() -> None:
    """No command module re-spells the exit-2 ``CommandOutcome`` inline (single home).

    Statically parses every module under ``novel_ralph_skill.commands`` and asserts
    none constructs a ``CommandOutcome(code=ExitCode.USAGE_ERROR, ...)`` inline:
    every body-detected exit-2 envelope must route through the shared
    :func:`~novel_ralph_skill.contract.runner.usage_error_outcome` home. The
    runner's own parser-fault arm is out of scope by design (Decision D3).
    """
    offenders = {
        module: lines
        for module, source in _command_module_sources().items()
        if (lines := _inline_usage_outcomes(source))
    }
    assert not offenders, (
        "command modules must route the exit-2 envelope through "
        "usage_error_outcome, not re-spell CommandOutcome(code=ExitCode."
        f"USAGE_ERROR, ...) inline: {offenders}"
    )


def test_guard_fires_on_a_synthetic_inline_construction() -> None:
    """The guard detects an inline exit-2 construction (positive control).

    Proves the scan would fire on a re-inlined site, so a passing
    single-home assertion cannot be a false pass from scanning nothing or from a
    matcher that never matches. Mirrors the "fails before, passes after"
    discipline the ExecPlan records for WI5.
    """
    inline = (
        "from novel_ralph_skill.contract import CommandOutcome, ExitCode\n"
        "def _scan():\n"
        "    return CommandOutcome(\n"
        "        code=ExitCode.USAGE_ERROR, messages=['x']\n"
        "    )\n"
    )
    assert _inline_usage_outcomes(inline), (
        "the guard must fire on an inline exit-2 CommandOutcome construction"
    )


def test_guard_ignores_non_usage_outcomes() -> None:
    """A non-exit-2 ``CommandOutcome`` is left alone (no over-broad matching).

    The success/finding/state arms legitimately build a ``CommandOutcome`` inline;
    the guard must match only the ``code=ExitCode.USAGE_ERROR`` construction the
    shared helper owns, never these.
    """
    success = (
        "from novel_ralph_skill.contract import CommandOutcome, ExitCode\n"
        "def _ok():\n"
        "    return CommandOutcome(code=ExitCode.SUCCESS, result={})\n"
    )
    assert not _inline_usage_outcomes(success), (
        "the guard must not match a non-USAGE_ERROR CommandOutcome construction"
    )
