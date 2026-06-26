"""Pytest fixture plugin exposing the installed ``novel`` multiplexer script.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py`` (roadmap 6.2.4). It owns ``installed_novel_state``, the
module-scoped fixture that builds a wheel, installs it into a fresh ``uv`` venv,
and returns the absolute path of the installed ``novel`` console-script, and
``assert_installed_state_error``, the function-scoped harness that runs the
installed script over a bad ``state.toml`` and asserts the exit-3 state-error
contract (exit 3, ``ok: false``, no traceback, and a non-blank operator message;
ExecPlan addendum 6.2.6.2) shared by the ``recount``, ``reconcile``, and
``wordcount`` installed exit-3 proofs. Roadmap
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

import json
import sysconfig
import typing as typ
from pathlib import Path

import pytest
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc


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


@pytest.fixture
def assert_installed_state_error(
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> cabc.Callable[..., None]:
    """Return a harness asserting the installed exit-3 state-error contract.

    The installed exit-3 proofs across ``recount``, ``reconcile``, and
    ``wordcount`` each ran the built console-script over a bad ``state.toml`` and
    asserted the same triple: exit ``3``, an ``ok: false`` envelope, and no
    ``Traceback`` on stderr. Design §10 also requires a state fault to yield a
    *message*, not a stack trace, yet the proofs pinned no message content — a
    regression emitting an empty ``messages`` list would have passed unnoticed.
    This fixture folds the run and the full contract (the existing triple plus a
    non-blank-message check) into one shared asserter, without coupling to any
    wording the contract does not fix (ExecPlan addendum 6.2.6.2). It lives in
    this installed-binary plugin (beside ``installed_novel_state``) rather than in
    ``conftest`` so the latter stays within the 400-line module cap. Bundling the
    catalogue builder here also keeps each consuming test within the project's
    four-argument gate (Pylint ``too-many-arguments``).

    Parameters
    ----------
    single_program_catalogue : Callable[[str, Program], ProgramCatalogue]
        The one-program catalogue builder the harness uses to allowlist the
        script under test.

    Returns
    -------
    Callable[..., None]
        A callable ``(script_path, run_dir, *argv) -> None`` that runs
        ``script_path`` over ``argv`` in ``run_dir`` and asserts the exit-3
        state-error contract, raising :class:`AssertionError` on any breach.
    """

    def _assert(script_path: Path, run_dir: Path, *argv: str) -> None:
        """Run the installed script over ``argv`` and assert the exit-3 contract."""
        prog = Program(str(script_path))
        catalogue = single_program_catalogue("installed-state-error", prog)
        result = sh.make(prog, catalogue=catalogue)(*argv).run_sync(
            context=ExecutionContext(cwd=run_dir), capture=True
        )
        if result.exit_code != ExitCode.STATE_ERROR:
            msg = (
                f"expected exit {ExitCode.STATE_ERROR.value}, got "
                f"{result.exit_code}; stderr={result.stderr!r}"
            )
            raise AssertionError(msg)
        envelope = typ.cast("dict[str, object]", json.loads(result.stdout or "{}"))
        if envelope.get("ok") is not False:
            msg = f"exit-3 envelope must be ok: false; got {envelope!r}"
            raise AssertionError(msg)
        if "Traceback" in (result.stderr or ""):
            msg = f"exit-3 path must emit no traceback; got {result.stderr!r}"
            raise AssertionError(msg)
        messages = envelope.get("messages")
        lines = messages if isinstance(messages, list) else []
        if not any(isinstance(line, str) and line.strip() for line in lines):
            msg = (
                "exit-3 envelope must carry a non-blank operator message; "
                f"got messages={messages!r} in {envelope!r}"
            )
            raise AssertionError(msg)

    return _assert
