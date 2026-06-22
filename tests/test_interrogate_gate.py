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

import operator
import typing as typ

from hypothesis import given
from hypothesis import strategies as st

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from conftest import RepoTextReader


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
        read_repo_text: RepoTextReader,
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
        dist_name: cabc.Callable[[str], str | None],
    ) -> None:
        """The ``interrogate`` distribution is declared as a dev dependency."""
        dev = toml_table(pyproject, "dependency-groups")["dev"]
        assert isinstance(dev, list), "[dependency-groups] dev must be a list"
        # Normalise each requirement string to its bare distribution name so the
        # match holds regardless of version specifiers, extras, or whitespace
        # (e.g. "interrogate", "interrogate>=1.7.0", or "interrogate[toml]").
        assert any(
            isinstance(spec, str) and dist_name(spec) == "interrogate" for spec in dev
        ), "interrogate must be declared in the dev dependency group"

    def test_dist_name_extracts_bare_name_property(
        self,
        dist_name: cabc.Callable[[str], str | None],
    ) -> None:
        """Property: ``dist_name`` extracts exactly the bare PEP 508 name.

        The function-scoped ``dist_name`` fixture is resolved here, by the plain
        outer test, and passed into an inner ``@given`` body as a closure
        variable. No fixture appears in the ``@given`` signature, so
        ``HealthCheck.function_scoped_fixture`` cannot fire — the convention
        :mod:`tests.test_contract_properties` already defends.
        """
        # Build the bare name directly so every generated specifier has a valid
        # leading name (no rejection sampling): an alphanumeric head and tail
        # with an internal run that may carry ``.``/``_``/``-``.
        alnum = st.sampled_from("abcXYZ012")
        internal = st.text(alphabet="abcXYZ012._-", max_size=8)
        name = st.builds(lambda a, m, z: a + m + z, alnum, internal, alnum)
        # The suffix is empty or a true delimiter (outside the PEP 503 name
        # alphabet) followed by an arbitrary tail, so the regex stops at the
        # delimiter and the bare-name invariant holds.
        delim = st.sampled_from(["[", "]", "<", ">", "=", "~", ";", " "])
        tail = st.text(alphabet="abc012[]<>=~;. _-", max_size=8)
        suffix = st.one_of(
            st.just(""),
            st.builds(operator.add, delim, tail),
        )

        @given(name=name, suffix=suffix)
        def _check(name: str, suffix: str) -> None:
            """Assert bare-name, well-formedness, and idempotence invariants."""
            got = dist_name(name + suffix)
            assert got == name, f"dist_name({name + suffix!r}) != {name!r}"
            assert got is not None  # guaranteed: name begins alphanumeric
            assert all(c.isalnum() or c in "._-" for c in got), (
                f"{got!r} carries a character outside the PEP 503 alphabet"
            )
            assert got[0].isalnum(), f"{got!r} must start alphanumeric"
            assert got[-1].isalnum(), f"{got!r} must end alphanumeric"
            assert dist_name(got) == got, f"dist_name not idempotent on {got!r}"

        _check()
