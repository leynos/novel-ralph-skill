"""End-to-end proof that the five console-scripts install and run.

This is the roadmap task 1.2.1 success criterion made executable: build a wheel
from this package, install it into a throwaway virtual environment, and confirm
all five console-scripts resolve on disk and exit ``2`` when run with no
arguments. Every external program — ``uv`` (a bare name) for the build, venv,
and install steps, and the five installed console-scripts (run **by absolute
path**) — runs through a local cuprum catalogue per the scripting standards.
cuprum 0.1.0 allowlists any ``Program`` string, including an absolute path, and
executes it through ``asyncio.create_subprocess_exec``, so the installed scripts
need no raw ``subprocess``. ``uv run`` is avoided because it would resolve
against the project environment rather than the freshly built wheel.

This e2e is POSIX-only (ADR 006): CI runs the test suite only on
``ubuntu-latest``, so the test is skipped on non-POSIX platforms rather than
executing a broken Windows path.

The test is slow (build + venv + install + five script runs), so it is marked
``slow`` and given an explicit 180s per-test timeout that supersedes the 30s
project default under ``-n auto``.
"""

from __future__ import annotations

import os
import typing as typ
from pathlib import Path

import pytest
from cuprum import sh
from cuprum.program import Program

from novel_ralph_skill.commands.names import COMMAND_NAMES

# ``novel-state``, ``desloppify``, and ``novel-compile`` are excluded from the
# exit-``2`` loop: each real app resolves ``./working/`` and exits per its own
# contract (``3`` when no ``working/`` is present), not the stub's ``2`` (Decision
# Log B6; roadmap 5.1.2, 4.1.1). Their real e2es live in
# ``tests/test_novel_state_check.py``, ``tests/test_desloppify_e2e.py``, and
# ``tests/test_compile_e2e.py``. The two still-stubbed scripts (``novel-done``,
# ``wordcount``) keep the exit-``2`` contract here.
_REAL_COMMANDS: frozenset[str] = frozenset({
    "novel-state",
    "desloppify",
    "novel-compile",
})
_STILL_STUBBED_NAMES: tuple[str, ...] = tuple(
    name for name in COMMAND_NAMES if name not in _REAL_COMMANDS
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from cuprum import ProgramCatalogue
    from cuprum.sh import CommandResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# why: this e2e is POSIX-only (ADR 006). CI runs the test suite only on
# ubuntu-latest; the Windows/macOS matrix builds wheels and never runs pytest,
# so the old win32 branch was dead and wrong. Skip off POSIX rather than execute
# a broken path.
pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="console-scripts e2e is POSIX-only; see ADR 006",
)


def _require_success(result: CommandResult, step: str) -> None:
    """Fail the test if a cuprum-run ``uv`` step did not exit ``0``."""
    if result.exit_code != 0:
        msg = f"uv {step} failed (exit {result.exit_code}): {result.stderr}"
        raise AssertionError(msg)


def _assert_scripts_exit_two(
    scripts_dir: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> None:
    """Run each still-stubbed console-script by absolute path; assert exit ``2``."""
    for command_name in _STILL_STUBBED_NAMES:
        script_path = scripts_dir / command_name
        assert script_path.exists(), f"{command_name} not installed at {script_path}"
        # cuprum 0.1.0 allowlists any Program string, including an absolute path,
        # and runs it through asyncio.create_subprocess_exec; no subprocess
        # needed (see the module docstring and ADR 006).
        prog = Program(str(script_path))
        catalogue = single_program_catalogue("novel-ralph-e2e-scripts", prog)
        result = sh.make(prog, catalogue=catalogue)().run_sync(capture=True)
        assert result.exit_code == 2, (
            f"{command_name} exited {result.exit_code}, expected 2"
        )
        stderr = result.stderr or ""
        assert "Traceback" not in stderr
        assert command_name in stderr


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_console_scripts_install_and_exit_two(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """Build, install, and run the two still-stubbed scripts; each exits ``2``.

    ``novel-state``, ``desloppify``, and ``novel-compile`` now drive real apps
    and are covered by ``tests/test_novel_state_check.py``,
    ``tests/test_desloppify_e2e.py``, and ``tests/test_compile_e2e.py``
    respectively (Decision Log B6; roadmap 4.1.1); the remaining two scripts
    (``novel-done``, ``wordcount``) stay stubs and exit ``2`` here.
    """
    wheel_dir = tmp_path / "wheels"
    venv_dir = tmp_path / "venv"

    uv = sh.make(
        Program("uv"),
        catalogue=single_program_catalogue("novel-ralph-e2e", Program("uv")),
    )

    _require_success(
        uv(
            "build",
            "--wheel",
            str(_PROJECT_ROOT),
            "--out-dir",
            str(wheel_dir),
        ).run_sync(),
        "build",
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"

    _require_success(uv("venv", str(venv_dir)).run_sync(), "venv")

    scripts_dir = venv_scripts_dir(venv_dir)
    venv_python = scripts_dir / "python"
    _require_success(
        uv(
            "pip",
            "install",
            "--python",
            str(venv_python),
            str(wheels[0]),
        ).run_sync(),
        "pip install",
    )

    _assert_scripts_exit_two(scripts_dir, single_program_catalogue)
