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
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# Leading run of a PEP 508 requirement string before any version specifier,
# extras bracket, marker, or whitespace; this is the bare distribution name.
_DIST_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")


def _dist_name(spec: str) -> str | None:
    """Return the bare distribution name of a PEP 508 requirement string."""
    match = _DIST_NAME.match(spec.strip())
    return match.group(0) if match else None


class TestInterrogateGate:
    """Pin the docstring-coverage gate's configuration, invocation, and deps."""

    def test_fail_under_is_one_hundred(
        self,
        pyproject: dict[str, object],
        toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
    ) -> None:
        """The interrogate gate is pinned to 100% docstring coverage."""
        interrogate = toml_table(toml_table(pyproject, "tool"), "interrogate")
        assert interrogate["fail-under"] == 100, (
            "[tool.interrogate] fail-under must be 100 so the 100% "
            "docstring-coverage standard is enforced for any auto-detecting "
            "invocation"
        )

    def test_makefile_invokes_interrogate(
        self,
        read_repo_text: cabc.Callable[..., str],
    ) -> None:
        """A single Makefile recipe line runs interrogate over the targets."""
        makefile = read_repo_text("Makefile")
        # Same-line co-occurrence: deleting the interrogate recipe line must
        # fail this gate even though $(PYTHON_TARGETS) appears on several other
        # lines.
        assert any(
            "interrogate" in line and "$(PYTHON_TARGETS)" in line
            for line in makefile.splitlines()
        ), "a Makefile recipe line must invoke interrogate over $(PYTHON_TARGETS)"

    def test_interrogate_is_a_dev_dependency(
        self,
        pyproject: dict[str, object],
        toml_table: cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]],
    ) -> None:
        """The ``interrogate`` distribution is declared as a dev dependency."""
        dev = toml_table(pyproject, "dependency-groups")["dev"]
        assert isinstance(dev, list), "[dependency-groups] dev must be a list"
        # Normalise each requirement string to its bare distribution name so the
        # match holds regardless of version specifiers, extras, or whitespace
        # (e.g. "interrogate", "interrogate>=1.7.0", or "interrogate[toml]").
        assert any(
            isinstance(spec, str) and _dist_name(spec) == "interrogate" for spec in dev
        ), "interrogate must be declared in the dev dependency group"
