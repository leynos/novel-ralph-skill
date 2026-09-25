"""Contract tests for the Pylint lint tier.

The tier runs a pinned Pylint as a uv tool on managed PyPy 3.12. Two
properties of that tier are easy to lose without any test noticing: the
interpreter pin, which decides the grammar Pylint parses with, and the
`syntax-error` message, which decides whether a module that grammar cannot
parse fails the lint or is skipped without a word. Both regressed silently
before: a bare `pypy` moved to a newer PyPy with no commit here, and a
disabled `syntax-error` let unparseable modules go unlinted.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = _REPO_ROOT / "Makefile"
CONFIG_PATH = _REPO_ROOT / "pyproject.toml"


def _makefile_variable(name: str) -> str:
    """Return the value assigned to a Makefile variable.

    Parameters
    ----------
    name : str
        The variable name, assigned with ``=`` or ``?=``.

    Returns
    -------
    str
        The assigned value with surrounding whitespace removed.
    """
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}\s*\??=\s*(.+)$", text, flags=re.MULTILINE)
    assert match is not None, f"{name} is not defined in the Makefile"
    return match.group(1).strip()


def test_pylint_tier_pins_the_interpreter() -> None:
    """The tier must name the interpreter whose grammar it parses with."""
    assert _makefile_variable("PYLINT_PYTHON") == "pypy@3.12", (
        "PYLINT_PYTHON must stay pypy@3.12: bare pypy follows uv's next release"
    )


def test_pylint_tier_runs_the_pinned_release_on_managed_python() -> None:
    """The tier must run the pinned Pylint on a uv-managed interpreter."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", _makefile_variable("PYLINT_VERSION")), (
        "PYLINT_VERSION must pin an exact Pylint release"
    )
    command = _makefile_variable("PYLINT")
    for fragment in (
        "tool run --managed-python --python $(PYLINT_PYTHON)",
        "--from 'pylint==$(PYLINT_VERSION)' pylint",
    ):
        assert fragment in command, f"PYLINT must contain {fragment!r}: {command}"


def test_pylint_reports_unparseable_modules() -> None:
    """The Pylint policy must not disable `syntax-error`."""
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    disabled = config["tool"]["pylint"]["messages control"]["disable"]
    assert "syntax-error" not in disabled, (
        "pyproject.toml must not disable syntax-error: a module the interpreter "
        f"cannot parse would then be skipped silently; disable={disabled!r}"
    )
