"""End-to-end proof that the five console-scripts install and run.

This is the roadmap task 1.2.1 success criterion made executable: build a wheel
from this package, install it into a throwaway virtual environment, and confirm
all five console-scripts resolve on disk and exit ``2`` when run with no
arguments. The build, venv, and install steps run ``uv`` (a bare program name)
through a local cuprum catalogue per the scripting standards. The installed
scripts are then run **by absolute path** via one scoped ``subprocess.run``,
because cuprum's catalogue allowlists bare program names only and exposes no API
to execute an absolute path, and ``uv run`` would resolve against the project
environment rather than the freshly built wheel.

The test is slow (build + venv + install + five subprocess runs), so it is
marked ``slow`` and given an explicit 180s per-test timeout that supersedes the
30s project default under ``-n auto``.
"""

from __future__ import annotations

import subprocess  # noqa: S404 - runs installed scripts by absolute path only
import sys
import sysconfig
import typing as typ
from pathlib import Path

import pytest
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program

if typ.TYPE_CHECKING:
    from cuprum.sh import CommandResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CATALOGUE = ProgramCatalogue(
    projects=(
        ProjectSettings(
            name="novel-ralph-e2e",
            programs=(Program("uv"),),
            documentation_locations=(),
            noise_rules=(),
        ),
    )
)
_uv = sh.make(Program("uv"), catalogue=_CATALOGUE)

COMMAND_NAMES = (
    "novel-state",
    "novel-done",
    "novel-compile",
    "desloppify",
    "wordcount",
)


def _require_success(result: CommandResult, step: str) -> None:
    """Fail the test if a cuprum-run ``uv`` step did not exit ``0``."""
    if result.exit_code != 0:
        msg = f"uv {step} failed (exit {result.exit_code}): {result.stderr}"
        raise AssertionError(msg)


def _venv_scripts_dir(venv_dir: Path) -> Path:
    """Return the venv's executable-scripts directory across platforms."""
    scheme = "nt_user" if sys.platform == "win32" else "posix_prefix"
    bin_name = sysconfig.get_path("scripts", scheme, vars={"base": str(venv_dir)})
    return Path(bin_name)


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_console_scripts_install_and_exit_two(tmp_path: Path) -> None:
    """Build, install, and run all five console-scripts; each exits ``2``."""
    wheel_dir = tmp_path / "wheels"
    venv_dir = tmp_path / "venv"

    _require_success(
        _uv(
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

    _require_success(_uv("venv", str(venv_dir)).run_sync(), "venv")

    scripts_dir = _venv_scripts_dir(venv_dir)
    venv_python = scripts_dir / ("python.exe" if sys.platform == "win32" else "python")
    _require_success(
        _uv(
            "pip",
            "install",
            "--python",
            str(venv_python),
            str(wheels[0]),
        ).run_sync(),
        "pip install",
    )

    for command_name in COMMAND_NAMES:
        script_path = scripts_dir / command_name
        assert script_path.exists(), f"{command_name} not installed at {script_path}"
        result = subprocess.run(  # noqa: S603 - absolute tmp_path, not user input
            [str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2, (
            f"{command_name} exited {result.returncode}, expected 2"
        )
        assert "Traceback" not in result.stderr
        assert command_name in result.stderr
