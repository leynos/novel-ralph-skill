"""End-to-end proof the installed ``wordcount`` reports over a real wheel/venv.

This is the design §9 installed-binary success criterion for ``wordcount``
(roadmap task 6.1.1): build a wheel from this package, install it into a throwaway
virtual environment, materialise a coherent ``working/`` tree, and run the
installed ``wordcount`` **by absolute path** through a cuprum catalogue that
**registers that exact path**. The registration is the execution gate
(``cuprum/sh.py:make`` calls ``catalogue.lookup``, which raises
``UnknownProgramError`` for any unregistered program), so the test reuses the
``single_program_catalogue`` fixture exactly as ``tests/test_desloppify_e2e.py``
and ``tests/test_console_scripts_e2e.py`` do.

The corpus baseline tree is drafted past the 80% knitting gate, so the installed
binary exits ``0`` and its stdout JSON envelope carries the cumulative report with
``gate_triggered_80: true`` and a non-negative ``next_gate_distance`` (``null``
past the final gate). This e2e is POSIX-only (ADR-006) and slow (build + venv +
install), so it is skipped off POSIX and given an explicit 180s timeout that
supersedes the 30s project default.
"""

from __future__ import annotations

import json
import os
import shutil
import typing as typ
from pathlib import Path

import pytest
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from cuprum import ProgramCatalogue

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _build_and_install_wordcount(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> Path:
    """Build a wheel, install it into a fresh venv, and return the ``wordcount``."""
    venv_dir = tmp_path / "venv"
    uv = sh.make(
        Program("uv"),
        catalogue=single_program_catalogue("wordcount-e2e", Program("uv")),
    )
    build = uv(
        "build", "--wheel", str(_PROJECT_ROOT), "--out-dir", str(tmp_path / "wheels")
    ).run_sync()
    assert build.exit_code == 0, build.stderr
    wheels = sorted((tmp_path / "wheels").glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels}"

    assert uv("venv", str(venv_dir)).run_sync().exit_code == 0
    scripts_dir = venv_scripts_dir(venv_dir)
    install = uv(
        "pip", "install", "--python", str(scripts_dir / "python"), str(wheels[0])
    ).run_sync()
    assert install.exit_code == 0, install.stderr

    script_path = scripts_dir / "wordcount"
    assert script_path.exists(), f"wordcount not installed at {script_path}"
    return script_path


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_wordcount_reports_gate_triggers(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``wordcount`` reports the cumulative gate triggers and exits 0.

    The corpus baseline is drafted past the 80% gate, so the report carries
    ``gate_triggered_80: true`` and a per-chapter table that sums to ``current``.
    Proves the real ``wordcount`` travels in the wheel and runs end-to-end. The
    180s timeout supersedes the 30s project default.
    """
    script_path = _build_and_install_wordcount(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-report"
    dest.mkdir()
    shutil.copytree(baseline_tree(), dest / "working")

    prog = Program(str(script_path))
    catalogue = single_program_catalogue("wordcount-run", prog)
    result = sh.make(prog, catalogue=catalogue)().run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert result.exit_code == 0, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True
    cumulative = envelope["result"]["cumulative"]
    assert cumulative["gate_triggered_80"] is True
    distance = cumulative["next_gate_distance"]
    assert distance is None or distance >= 0, "next-gate distance is non-negative"
    chapters = envelope["result"]["chapters"]
    assert sum(row["words"] for row in chapters) == cumulative["current"]
