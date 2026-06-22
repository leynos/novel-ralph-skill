"""Shared pytest scaffolding for the ``tests/`` tree.

This module is the single home for the test-suite helpers that were previously
copied across modules: the project-root path, the parsed ``pyproject.toml``, a
repo-relative file reader, and a TOML-table accessor. Every helper is exposed as
a pytest fixture so consuming modules receive it by parameter name with no
inter-module import; this removes the duplication and the cross-module private
import that six post-merge audits flagged (``docs/issues/audit-1.2.1.md``
Finding 3, ``audit-1.2.3.md`` Findings 1-2, ``audit-1.2.4.md`` Finding 2,
``audit-1.2.5.md`` Findings 1-3 and 5, ``audit-1.2.6.md`` Findings 1-2).

``tests/conftest.py`` is inside ``PYTHON_TARGETS`` (``Makefile``), so it is
subject to the full Ruff lint and format, 100% ``interrogate`` docstring
coverage, Pylint, and ``ty`` typecheck gates. The ``**/test_*.py``
``per-file-ignores`` do not match this file, so it carries no bare ``assert``;
guards that must fail raise :class:`AssertionError` directly.
"""

from __future__ import annotations

import re
import sysconfig
import tomllib
import typing as typ
from pathlib import Path

import pytest
from cuprum import ProgramCatalogue, ProjectSettings

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from cuprum.program import Program

# Leading run of a PEP 508 requirement string before any version specifier,
# extras bracket, marker, or whitespace; this is the bare distribution name.
_DIST_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root, the parent of the ``tests/`` directory.

    Returns
    -------
    Path
        The absolute path to the worktree root.
    """
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pyproject(project_root: Path) -> dict[str, object]:
    """Return the parsed ``pyproject.toml`` for the worktree.

    Parameters
    ----------
    project_root : Path
        The repository root supplying the ``pyproject.toml`` location.

    Returns
    -------
    dict[str, object]
        The decoded top-level TOML mapping.
    """
    return tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture
def read_repo_text(project_root: Path) -> cabc.Callable[..., str]:
    """Return a reader for a repo-relative UTF-8 text file.

    Parameters
    ----------
    project_root : Path
        The repository root the returned reader joins its parts under.

    Returns
    -------
    Callable[..., str]
        A callable ``(*parts: str) -> str`` that joins ``parts`` under
        ``project_root`` and returns the file's UTF-8 text.
    """

    def _read(*parts: str) -> str:
        """Return the UTF-8 text of the repo-relative file named by ``parts``."""
        return project_root.joinpath(*parts).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def toml_table() -> cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]]:
    """Return an accessor that narrows a mapping value to a TOML table.

    Returns
    -------
    Callable[[Mapping[str, object], str], dict[str, object]]
        A callable ``(parent, key) -> dict[str, object]`` returning the ``key``
        sub-table of ``parent`` or raising :class:`AssertionError` when the
        value is not a table.
    """

    def _table(parent: cabc.Mapping[str, object], key: str) -> dict[str, object]:
        """Return the ``key`` sub-table of ``parent`` or raise on a non-table."""
        value = parent[key]
        match value:
            case dict():
                return typ.cast("dict[str, object]", value)
            case _:
                msg = f"[{key}] must be a TOML table, got {type(value)}"
                raise AssertionError(msg)

    return _table


@pytest.fixture
def dist_name() -> cabc.Callable[[str], str | None]:
    """Return a PEP 508 bare-distribution-name normaliser.

    The returned callable reduces a requirement string to its bare distribution
    name: the leading run before any extras bracket, version operator, marker,
    or whitespace. It is the single home for this normalisation, consumed by the
    interrogate-gate and contract-test-deps suites by fixture name
    (``docs/issues/audit-1.2.7.md`` Finding 2).

    Returns
    -------
    Callable[[str], str | None]
        A callable ``(spec) -> str | None`` returning the bare distribution
        name of ``spec`` (e.g. ``hypothesis[cli]>=6.0`` -> ``hypothesis``), or
        ``None`` when ``spec`` does not begin with a valid name.
    """

    def _normalise(spec: str) -> str | None:
        """Return the bare distribution name of ``spec`` or ``None``."""
        match = _DIST_NAME.match(spec.strip())
        return match.group(0) if match else None

    return _normalise


@pytest.fixture
def single_program_catalogue() -> cabc.Callable[[str, Program], ProgramCatalogue]:
    """Return a builder for a one-program cuprum catalogue.

    The builder mirrors the single-``ProjectSettings``, single-``Program`` shape
    the console-scripts e2e constructs repeatedly. cuprum 0.1.0 allowlists any
    ``Program`` string, including an absolute path; the catalogue allowlist, not
    the ``Program`` type, is the execution gate.

    Returns
    -------
    Callable[[str, Program], ProgramCatalogue]
        A callable ``(name, program) -> ProgramCatalogue`` building a catalogue
        whose sole project allowlists exactly ``program``.
    """

    def _build(name: str, program: Program) -> ProgramCatalogue:
        """Return a one-project catalogue allowlisting ``program`` under ``name``."""
        return ProgramCatalogue(
            projects=(
                ProjectSettings(
                    name=name,
                    programs=(program,),
                    documentation_locations=(),
                    noise_rules=(),
                ),
            )
        )

    return _build


@pytest.fixture
def venv_scripts_dir() -> cabc.Callable[[Path], Path]:
    """Return the venv executable-scripts-directory resolver.

    The resolver uses the ``venv`` install scheme and is POSIX-only per ADR-006
    (``docs/adr-006-console-scripts-e2e-posix-policy.md``); modules consuming it
    keep their own POSIX ``pytestmark`` skip guard.

    Returns
    -------
    Callable[[Path], Path]
        A callable ``(venv_dir) -> Path`` returning ``venv_dir``'s
        executable-scripts directory (``bin`` on POSIX).
    """

    def _resolve(venv_dir: Path) -> Path:
        """Return the ``venv``-scheme scripts directory for ``venv_dir``."""
        scripts = sysconfig.get_path(
            "scripts",
            "venv",
            vars={"base": str(venv_dir), "platbase": str(venv_dir)},
        )
        return Path(scripts)

    return _resolve
