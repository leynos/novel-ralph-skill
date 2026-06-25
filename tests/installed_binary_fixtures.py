"""Pytest fixture plugin exposing the installed ``novel`` multiplexer script.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py`` (roadmap 6.2.4). It owns ``installed_novel_state``, the
module-scoped fixture that builds a wheel, installs it into a fresh ``uv`` venv,
and returns the absolute path of the installed ``novel`` console-script. Roadmap
task 1.2.13 re-points the fixture from the legacy ``novel-state`` script onto the
single ``novel`` multiplexer (the shipping surface): consumers now drive
``novel state …`` instead of ``novel-state …``. The fixture *name* is unchanged
so the five consumer modules bind it by the same parameter name; only the
resolved script basename changes. The legacy per-command scripts still ship in
the wheel until task 1.2.15, but the e2e drives the ``novel`` surface. It
retires the former cross-module ``_build_and_install_novel_state`` helper that
``test_reconcile_e2e.py`` imported from ``test_novel_state_check.py`` in breach of
the developers-guide "Shared test scaffolding" rule; consumers now receive the
script path by fixture parameter name.

It lives beside ``conftest.py`` rather than inside it solely because the fixture
surface would push ``conftest.py`` past the 400-line module cap (AGENTS.md lines
24-27); registering it as a plugin keeps the fixture available by name to every
installed-binary e2e module (``test_novel_state_check.py``,
``test_reconcile_e2e.py``, ``test_recount_e2e.py``) exactly as a ``conftest``
fixture would be.

The fixture is **module-scoped** so the slow wheel build, venv create, and
install run once per consuming module and every test reuses the one install
(Decision D-SCOPE). It depends only on the session-scoped ``tmp_path_factory``
because a module-scoped fixture cannot request the function-scoped ``tmp_path``,
``single_program_catalogue``, or ``venv_scripts_dir`` (pytest raises
``ScopeMismatch`` at collection); their logic is inlined as the two private
helpers below, exactly as ``test_ai_isms_e2e.py``'s ``installed_desloppify`` does.

Like ``conftest.py`` this module is inside ``PYTHON_TARGETS``, so it carries a
module docstring, a docstring on every fixture and helper, and raises
:class:`AssertionError` directly rather than using a bare ``assert``. The fixture
is POSIX-only per ADR-006; consuming modules carry their own POSIX skip guard.
"""

from __future__ import annotations

import sysconfig
from pathlib import Path

import pytest
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program


def _one_program_catalogue(name: str, program: Program) -> ProgramCatalogue:
    """Return a one-project cuprum catalogue allowlisting exactly ``program``.

    Inlined logic of the :func:`single_program_catalogue` fixture's builder: the
    module-scoped :func:`installed_novel_state` fixture cannot request that
    function-scoped fixture (pytest raises ``ScopeMismatch``), and the catalogue is
    a stateless value, so building it directly keeps the wheel install at module
    scope without a scope clash, exactly as ``test_ai_isms_e2e.py`` records.
    """
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


def _run_ok(command: sh.SafeCmd) -> None:
    """Run ``command`` synchronously and raise on a non-zero exit code.

    Folds the build/venv/install exit-code guards so the
    :func:`installed_novel_state` fixture body stays under the local-variable cap;
    the message carries ``stderr`` so a wheel or install failure surfaces directly.
    """
    result = command.run_sync()
    if result.exit_code != 0:
        raise AssertionError(result.stderr)


def _venv_scripts_dir(venv_dir: Path) -> Path:
    """Return ``venv_dir``'s executable-scripts directory (``bin`` on POSIX).

    Inlined logic of the :func:`venv_scripts_dir` fixture's resolver, for the same
    scope reason as :func:`_one_program_catalogue`. POSIX-only per ADR-006; the
    fixture's consumers carry the POSIX skip guard.
    """
    return Path(
        sysconfig.get_path(
            "scripts",
            "venv",
            vars={"base": str(venv_dir), "platbase": str(venv_dir)},
        )
    )


@pytest.fixture(scope="module")
def installed_novel_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel and install ``novel`` once per module; return its path.

    The wheel build, venv create, and install are the slow part of every installed
    e2e, so they run once per consuming module and every test reuses the one
    install (Decision D-SCOPE). The fixture depends only on the session-scoped
    ``tmp_path_factory`` because a module-scoped fixture cannot request the
    function-scoped ``tmp_path``, ``single_program_catalogue``, or
    ``venv_scripts_dir``; their logic is inlined as :func:`_one_program_catalogue`
    and :func:`_venv_scripts_dir`. Each consuming test still materialises its own
    throwaway ``working/`` tree under a per-test ``tmp_path``, so the cases stay
    independent. POSIX-only per ADR-006; consumers carry the POSIX skip guard.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        The session-scoped temporary-directory factory supplying the build root.

    Returns
    -------
    Path
        The absolute path to the installed ``novel`` multiplexer console-script.
    """
    build_root = tmp_path_factory.mktemp("novel-state-install")
    project_root = Path(__file__).resolve().parent.parent
    uv = sh.make(
        Program("uv"),
        catalogue=_one_program_catalogue("novel-state-e2e", Program("uv")),
    )
    _run_ok(
        uv(
            "build",
            "--wheel",
            str(project_root),
            "--out-dir",
            str(build_root / "wheels"),
        )
    )
    wheels = sorted((build_root / "wheels").glob("*.whl"))
    if len(wheels) != 1:
        msg = f"expected one wheel, found {wheels}"
        raise AssertionError(msg)

    venv_dir = build_root / "venv"
    _run_ok(uv("venv", str(venv_dir)))
    scripts_dir = _venv_scripts_dir(venv_dir)
    _run_ok(
        uv("pip", "install", "--python", str(scripts_dir / "python"), str(wheels[0]))
    )

    script_path = scripts_dir / "novel"
    if not script_path.exists():
        msg = f"novel not installed at {script_path}"
        raise AssertionError(msg)
    return script_path
