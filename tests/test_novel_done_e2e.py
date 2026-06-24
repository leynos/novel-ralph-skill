"""End-to-end proof the installed ``novel-done`` evaluates the predicate (3.1.1).

This is the design §4.2 success criterion made executable: build a wheel from this
package, install it into a throwaway virtual environment, materialise a real
``working/`` tree, and run the installed ``novel-done`` **by absolute path**
through a cuprum catalogue that **registers that exact path**. The registration is
the execution gate, so the test reuses the ``single_program_catalogue`` fixture
exactly as ``tests/test_desloppify_e2e.py`` and ``tests/test_console_scripts_e2e.py``
do.

An all-six-clauses-hold tree exits ``0`` with ``ok: true`` in the stdout JSON; an
otherwise-complete tree whose ``compiled.md`` is absent exits ``1`` (proving an
absent compile drives a benign negative end-to-end, never a false ``0``); an
otherwise-complete tree whose ``compiled.md`` is present but stale exits ``4`` (the
3.1.2 ``ACTIONABLE_FINDING`` carve-out); and a mid-draft tree carrying the same
stale compile exits ``1`` (the carve-out stays benign mid-draft). This e2e is
POSIX-only (ADR-006) and slow (build + venv + install), so it is skipped off POSIX
and given an explicit 180s timeout that supersedes the 30s default.
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
    from cuprum.sh import CommandResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)


def _materialise_working(dest: Path, source_working: Path) -> None:
    """Copy a built ``working/`` tree into ``dest/working`` for the subprocess cwd.

    Copying the corpus-built tree (rather than hand-writing ``state.toml``) keeps
    the e2e in lock-step with the real state schema, exactly as
    ``tests/test_desloppify_e2e.py`` does.
    """
    shutil.copytree(source_working, dest / "working")


def _build_and_install_novel_done(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> Path:
    """Build a wheel, install it into a fresh venv, and return the ``novel-done``."""
    venv_dir = tmp_path / "venv"
    uv = sh.make(
        Program("uv"),
        catalogue=single_program_catalogue("novel-done-e2e", Program("uv")),
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

    script_path = scripts_dir / "novel-done"
    assert script_path.exists(), f"novel-done not installed at {script_path}"
    return script_path


def _run_in(
    script_path: Path,
    cwd: Path,
    catalogue_builder: cabc.Callable[[str, Program], ProgramCatalogue],
) -> CommandResult:
    """Run the installed ``novel-done`` with ``cwd`` set; capture the result."""
    prog = Program(str(script_path))
    catalogue = catalogue_builder("novel-done-run", prog)
    return sh.make(prog, catalogue=catalogue)().run_sync(
        context=ExecutionContext(cwd=cwd), capture=True
    )


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_done_all_hold_exits_zero(
    tmp_path: Path,
    all_hold_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel-done`` exits ``0`` over an all-six-clauses-hold tree."""
    script_path = _build_and_install_novel_done(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-done"
    dest.mkdir()
    _materialise_working(dest, all_hold_tree())

    result = _run_in(script_path, dest, single_program_catalogue)
    assert result.exit_code == 0, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_done_absent_compile_exits_one(
    tmp_path: Path,
    done_predicate_failer_tree: cabc.Callable[[str], tuple[object, Path]],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel-done`` exits ``1`` when ``compiled.md`` is absent."""
    script_path = _build_and_install_novel_done(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    _spec, source = done_predicate_failer_tree("compile_consistent")
    dest = tmp_path / "run-not-done"
    dest.mkdir()
    _materialise_working(dest, source)

    result = _run_in(script_path, dest, single_program_catalogue)
    assert result.exit_code == 1, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False
    assert envelope["result"]["compile_consistent"] is False


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_done_sole_stale_compile_exits_four(
    tmp_path: Path,
    sole_stale_compile_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel-done`` exits ``4`` over a sole stale-present compile."""
    script_path = _build_and_install_novel_done(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-stale"
    dest.mkdir()
    _materialise_working(dest, sole_stale_compile_tree())

    result = _run_in(script_path, dest, single_program_catalogue)
    assert result.exit_code == 4, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False
    assert envelope["result"]["compile_consistent"] is False


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_done_mid_draft_stale_exits_one(
    tmp_path: Path,
    mid_draft_stale_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel-done`` exits ``1`` over a mid-draft stale compile."""
    script_path = _build_and_install_novel_done(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-mid-draft"
    dest.mkdir()
    _materialise_working(dest, mid_draft_stale_tree())

    result = _run_in(script_path, dest, single_program_catalogue)
    assert result.exit_code == 1, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False
    assert envelope["result"]["compile_consistent"] is False
