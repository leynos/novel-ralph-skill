"""End-to-end proof that the five console-scripts install and run a real app.

This is the roadmap task 1.2.1 success criterion made executable, now in its
terminal all-real form (roadmap task 6.1.1): build a wheel from this package,
install it into a throwaway virtual environment, and confirm all five
console-scripts resolve on disk and, run **by absolute path** under a cwd with no
``working/``, exit ``3`` — each driving its real Cyclopts app onto the shared
state-error path rather than the stub's ``2``. Every external program — ``uv`` (a
bare name) for the build, venv, and install steps, and the five installed
console-scripts (run by absolute path) — runs through a local cuprum catalogue
per the scripting standards. cuprum 0.1.0 allowlists any ``Program`` string,
including an absolute path, and executes it through
``asyncio.create_subprocess_exec``, so the installed scripts need no raw
``subprocess``. ``uv run`` is avoided because it would resolve against the project
environment rather than the freshly built wheel.

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
from cuprum.sh import ExecutionContext

from novel_ralph_skill.commands.names import COMMAND_NAMES
from novel_ralph_skill.contract.exit_codes import ExitCode

# ``novel-state`` is a command-group app: a bare invocation prints help and exits
# 0, so it only reaches the exit-3 state-error path on an absent tree when given a
# read-only subcommand. The other four commands carry a default body and reach
# their real path bare. This map supplies the extra argv each command needs.
_REAL_PATH_ARGV: dict[str, tuple[str, ...]] = {"novel-state": ("check",)}

# As of roadmap task 6.1.1 **all five** console-scripts drive their real Cyclopts
# apps: each resolves ``./working/`` and exits ``3`` when no ``working/`` is
# present, not the stub's ``2`` (Decision Log B6, D-TRIPWIRE; roadmap 5.1.2,
# 4.1.1, 3.1.1, 2.1.2, 6.1.1). ``wordcount`` was the last promotion, which empties
# the old still-stubbed loop; rather than leave a vacuous wheel build,
# ``test_console_scripts_install_and_run_real`` asserts the all-real dual: every
# installed script resolves and runs its real state-error path. Per-command
# behaviour is pinned by the dedicated e2es (``tests/test_novel_state_check.py``,
# ``tests/test_desloppify_e2e.py``, ``tests/test_compile_e2e.py``,
# ``tests/test_novel_done_e2e.py``, ``tests/test_wordcount_e2e.py``).
_REAL_COMMANDS: frozenset[str] = frozenset({
    "novel-state",
    "desloppify",
    "novel-compile",
    "novel-done",
    "wordcount",
})
assert COMMAND_NAMES, "the command registry must not be empty"
assert set(COMMAND_NAMES) <= _REAL_COMMANDS, "every installed script must be real"

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


def _assert_scripts_real_state_error(
    scripts_dir: Path,
    run_cwd: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> None:
    """Run each installed console-script by absolute path; assert exit ``3``.

    Each script is run under ``run_cwd``, a directory with **no** ``working/``, so
    every real app resolves ``./working/state.toml``, finds it absent, and takes
    the shared exit-``3`` state-error path — never the stub's ``2`` and never a
    traceback. The loop covers **all** ``COMMAND_NAMES`` (guarded non-empty at
    module import), so promoting the last stub cannot silently make this guard
    vacuous (Decision Log D-TRIPWIRE).
    """
    for command_name in COMMAND_NAMES:
        script_path = scripts_dir / command_name
        assert script_path.exists(), f"{command_name} not installed at {script_path}"
        # cuprum 0.1.0 allowlists any Program string, including an absolute path,
        # and runs it through asyncio.create_subprocess_exec; no subprocess
        # needed (see the module docstring and ADR 006).
        prog = Program(str(script_path))
        catalogue = single_program_catalogue("novel-ralph-e2e-scripts", prog)
        extra = _REAL_PATH_ARGV.get(command_name, ())
        result = sh.make(prog, catalogue=catalogue)(*extra).run_sync(
            context=ExecutionContext(cwd=run_cwd), capture=True
        )
        assert result.exit_code == ExitCode.STATE_ERROR, (
            f"{command_name} exited {result.exit_code}, expected 3 (state error)"
        )
        stderr = result.stderr or ""
        assert "Traceback" not in stderr
        assert "not yet implemented" not in stderr, (
            f"{command_name} emitted a stub greeting; it must drive a real app"
        )


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_console_scripts_install_and_run_real(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """Build, install, and run every console-script; each takes its real exit-3 path.

    All five console-scripts (``novel-state``, ``desloppify``, ``novel-compile``,
    ``novel-done``, ``wordcount``) now drive real apps (Decision Log B6,
    D-TRIPWIRE; roadmap 2.1.2, 5.1.2, 4.1.1, 3.1.1, 6.1.1). Run by absolute path
    under a cwd with no ``working/``, each resolves ``./working/state.toml``,
    finds it absent, and exits ``3`` — the all-real install-and-run guard the last
    stub's promotion would otherwise have made vacuous.
    """
    wheel_dir = tmp_path / "wheels"
    venv_dir = tmp_path / "venv"
    run_cwd = tmp_path / "run"
    run_cwd.mkdir()

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

    _assert_scripts_real_state_error(scripts_dir, run_cwd, single_program_catalogue)
