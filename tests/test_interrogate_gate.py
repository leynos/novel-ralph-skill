"""Fast guard on the interrogate docstring-coverage gate.

The 100% docstring-coverage standard (AGENTS.md, ``docs/developers-guide.md``,
``docs/users-guide.md``) is enforced by ``interrogate``. This guard pins the
gate's wiring by static parse so a regression fails ``make test`` rather than
shipping silently: the threshold lives once in ``[tool.interrogate]`` (not as a
CLI literal), the Makefile ``lint-python`` recipe invokes ``interrogate`` over
``$(PYTHON_TARGETS)``, and ``interrogate`` is a declared dev dependency. It
parses ``pyproject.toml`` with ``tomllib`` and reads the ``Makefile`` as text;
it does not shell out to run ``interrogate``, because ``make lint`` already runs
the live gate.
"""

from __future__ import annotations

import re
import tomllib
import typing as typ
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Leading run of a PEP 508 requirement string before any version specifier,
# extras bracket, marker, or whitespace; this is the bare distribution name.
_DIST_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")


def _pyproject() -> dict[str, object]:
    """Parse and return the worktree ``pyproject.toml`` as a dict."""
    return tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _table(parent: dict[str, object], key: str) -> dict[str, object]:
    """Return the ``key`` sub-table of ``parent``, asserting it is a table."""
    value = parent[key]
    match value:
        case dict():
            return typ.cast("dict[str, object]", value)
        case _:
            msg = f"[{key}] must be a TOML table, got {type(value)}"
            raise AssertionError(msg)


def _dist_name(spec: str) -> str | None:
    """Return the bare distribution name of a PEP 508 requirement string."""
    match = _DIST_NAME.match(spec.strip())
    return match.group(0) if match else None


class TestInterrogateGate:
    """Pin the docstring-coverage gate's configuration, invocation, and deps."""

    def test_fail_under_is_one_hundred(self) -> None:
        """The interrogate gate is pinned to 100% docstring coverage."""
        interrogate = _table(_table(_pyproject(), "tool"), "interrogate")
        assert interrogate["fail-under"] == 100, (
            "[tool.interrogate] fail-under must be 100 so the 100% "
            "docstring-coverage standard is enforced for any auto-detecting "
            "invocation"
        )

    def test_makefile_invokes_interrogate(self) -> None:
        """A single Makefile recipe line runs interrogate over the targets."""
        makefile = (_PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
        # Same-line co-occurrence: deleting the interrogate recipe line must
        # fail this gate even though $(PYTHON_TARGETS) appears on several other
        # lines.
        assert any(
            "interrogate" in line and "$(PYTHON_TARGETS)" in line
            for line in makefile.splitlines()
        ), "a Makefile recipe line must invoke interrogate over $(PYTHON_TARGETS)"

    def test_interrogate_is_a_dev_dependency(self) -> None:
        """The ``interrogate`` distribution is declared as a dev dependency."""
        dev = _table(_pyproject(), "dependency-groups")["dev"]
        assert isinstance(dev, list), "[dependency-groups] dev must be a list"
        # Normalise each requirement string to its bare distribution name so the
        # match holds regardless of version specifiers, extras, or whitespace
        # (e.g. "interrogate", "interrogate>=1.7.0", or "interrogate[toml]").
        assert any(
            isinstance(spec, str) and _dist_name(spec) == "interrogate" for spec in dev
        ), "interrogate must be declared in the dev dependency group"
