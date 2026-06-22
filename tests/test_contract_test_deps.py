"""Pin the two test-only dependencies the contract module's suites require.

Roadmap task 1.3.1 adds exactly two dev dependencies: ``hypothesis`` (for the
ok/exit-code property test) and ``syrupy`` (for the per-code envelope
snapshots). This guard mirrors the load-bearing element of
:mod:`tests.test_tomlkit_dependency`: an exact version pin acting as a
re-resolution tripwire (not a presence-only check), plus confirmation that each
dependency is declared in ``[dependency-groups].dev``. A silent ``uv``
re-resolution then fails this guard, while a deliberate upgrade updates the pin
visibly.

``syrupy`` does not expose ``__version__``, so its version is read through
:func:`importlib.metadata.version`; ``hypothesis`` exposes ``__version__``
directly.
"""

from __future__ import annotations

import importlib.metadata
import pathlib
import tomllib

import hypothesis

# why: track the versions uv.lock resolves; bump in lockstep with a deliberate
# upgrade. These exact pins are the re-resolution tripwires (round-2 B3).
LOCKED_HYPOTHESIS_VERSION = "6.155.7"
LOCKED_SYRUPY_VERSION = "5.3.2"

_PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"


def _dev_dependencies() -> list[str]:
    """Return the ``[dependency-groups].dev`` list from ``pyproject.toml``.

    Returns
    -------
    list[str]
        The raw dependency specifiers declared for the dev group.
    """
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["dependency-groups"]["dev"]


def test_hypothesis_import_and_version() -> None:
    """``hypothesis`` imports and resolves to the locked version.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    assert hypothesis.__version__ == LOCKED_HYPOTHESIS_VERSION


def test_syrupy_version() -> None:
    """``syrupy`` resolves to the locked version (via importlib metadata).

    ``syrupy`` exposes no ``__version__`` attribute, so the pin is read from the
    installed distribution metadata instead.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    assert importlib.metadata.version("syrupy") == LOCKED_SYRUPY_VERSION


def test_new_test_deps_are_declared_in_dev_group() -> None:
    """Both new dependencies are declared in ``[dependency-groups].dev``.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    declared = {
        spec.split()[0].split(">")[0].split("=")[0] for spec in _dev_dependencies()
    }
    assert "hypothesis" in declared
    assert "syrupy" in declared
