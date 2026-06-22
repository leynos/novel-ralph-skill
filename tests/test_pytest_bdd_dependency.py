"""Pin the ``pytest-bdd`` behavioural-test dependency for roadmap task 2.2.1.

This guard mirrors the load-bearing element of
:mod:`tests.test_tomlkit_dependency` and :mod:`tests.test_contract_test_deps`:
an exact version pin acting as a re-resolution tripwire (not a presence-only
check), plus confirmation that ``pytest-bdd`` is declared in
``[dependency-groups].dev``. ``pytest-bdd`` is the suite's first behavioural-test
dependency, mandated by AGENTS.md for behavioural tests; this task adds it for
the torn-turn scenario (ExecPlan work item 3). A silent ``uv`` re-resolution then
fails this guard, while a deliberate upgrade updates the pin visibly.

``pytest-bdd`` exposes no ``__version__`` attribute, so its version is read
through :func:`importlib.metadata.version`.
"""

from __future__ import annotations

import importlib.metadata
import typing as typ

import pytest_bdd

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# why: track the version uv.lock resolves; bump in lockstep with a deliberate
# upgrade. This exact pin is the re-resolution tripwire for the first
# behavioural-test dependency (ExecPlan work item 3).
LOCKED_PYTEST_BDD_VERSION = "8.1.0"


def test_pytest_bdd_imports_and_version() -> None:
    """``pytest-bdd`` imports and resolves to the locked version.

    The module-level ``import pytest_bdd`` proves the dependency resolves; the
    pin is read through :func:`importlib.metadata.version` because ``pytest-bdd``
    exposes no ``__version__`` attribute.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    assert pytest_bdd.__name__ == "pytest_bdd", "pytest_bdd failed to import"
    resolved = importlib.metadata.version("pytest-bdd")
    assert resolved == LOCKED_PYTEST_BDD_VERSION, (
        f"pytest-bdd resolved to {resolved}, expected {LOCKED_PYTEST_BDD_VERSION}"
    )


def test_pytest_bdd_is_declared_in_dev_group(
    pyproject: dict[str, object],
    toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
    dist_name: cabc.Callable[[str], str | None],
) -> None:
    """``pytest-bdd`` is declared in ``[dependency-groups].dev``.

    The dev group is read through the shared ``pyproject``/``toml_table``
    fixtures, and each requirement string is reduced to its bare distribution
    name through the shared ``dist_name`` normaliser, so the match holds
    regardless of the version operator or markers.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    dev = toml_table(pyproject, "dependency-groups")["dev"]
    assert isinstance(dev, list), "[dependency-groups] dev must be a list"
    assert any(
        isinstance(spec, str) and dist_name(spec) == "pytest-bdd" for spec in dev
    ), "pytest-bdd must be declared in the dev dependency group"
