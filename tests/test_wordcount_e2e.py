"""End-to-end proof installed ``novel wordcount`` reports over a real wheel/venv.

This is the design §9 installed-binary success criterion for ``wordcount``
(roadmap tasks 6.1.1, 6.2.6), re-pointed onto the single ``novel`` multiplexer
(roadmap task 1.2.13): build a wheel from this package, install it into a
throwaway virtual environment, materialise a ``working/`` tree, and run the
installed ``novel wordcount`` **by absolute path** through a cuprum catalogue
that **registers that exact path**. The registration is the execution gate
(``cuprum/sh.py:make`` calls ``catalogue.lookup``, which raises
``UnknownProgramError`` for any unregistered program), so the tests reuse the
``single_program_catalogue`` fixture exactly as ``tests/test_desloppify_e2e.py``
and ``tests/test_console_scripts_e2e.py`` do.

Two installed proofs live here:

- the happy path: the corpus baseline tree is drafted past the 80% knitting gate,
  so the installed binary exits ``0`` and its stdout JSON envelope carries the
  cumulative report with ``gate_triggered_80: true`` and a non-negative
  ``next_gate_distance`` (``null`` past the final gate); and
- the exit-3 path (roadmap 6.2.6): a ``working/`` whose ``state.toml`` is missing
  or unparseable drives the installed ``novel wordcount`` to exit ``3`` with an
  ``ok: false`` envelope and no traceback, mirroring the ``recount`` proof so
  each of ``recount``, ``reconcile``, and ``wordcount`` anchors its exit-3
  state-or-input-error path at the packaging boundary (audit Finding 6).

Both e2es are POSIX-only (ADR-006) and slow (build + venv + install), so they are
skipped off POSIX and given an explicit 180s timeout that supersedes the 30s
project default.
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


def _build_and_install_novel(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> Path:
    """Build a wheel, install it into a fresh venv, and return the ``novel`` script.

    Roadmap task 1.2.13 drives ``novel wordcount`` through the single ``novel``
    multiplexer, so the helper resolves the ``novel`` console-script rather than
    the legacy ``wordcount`` script (which still ships until task 1.2.15).
    """
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

    script_path = scripts_dir / "novel"
    assert script_path.exists(), f"novel not installed at {script_path}"
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
    """Installed ``novel wordcount`` reports the cumulative gate triggers; exits 0.

    The corpus baseline is drafted past the 80% gate, so the report carries
    ``gate_triggered_80: true`` and a per-chapter table that sums to ``current``.
    Proves the real ``wordcount`` travels in the wheel and runs end-to-end. The
    180s timeout supersedes the 30s project default.
    """
    script_path = _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-report"
    dest.mkdir()
    shutil.copytree(baseline_tree(), dest / "working")

    prog = Program(str(script_path))
    catalogue = single_program_catalogue("wordcount-run", prog)
    result = sh.make(prog, catalogue=catalogue)("wordcount").run_sync(
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


@pytest.fixture
def installed_novel_script(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> Path:
    """Build, install, and return the ``novel`` console-script for this module.

    Folds the two build collaborators (``single_program_catalogue`` and
    ``venv_scripts_dir``) into one fixture so a consuming test that also needs the
    shared ``assert_installed_state_error`` harness stays within the project's
    four-argument gate (Pylint ``too-many-arguments``). It defers to the module's
    ``_build_and_install_novel`` helper, so the build path is unchanged.
    """
    return _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize(
    "state_bytes",
    [None, b"not = toml ="],
    ids=["missing-state", "unparseable-state"],
)
def test_installed_wordcount_state_error_exits_three(
    state_bytes: bytes | None,
    tmp_path: Path,
    installed_novel_script: Path,
    assert_installed_state_error: cabc.Callable[..., None],
) -> None:
    """The installed ``novel wordcount`` exits ``3`` on a bad ``state.toml``.

    Two fault shapes drive the exit-3 state-or-input-error channel (design §3.2;
    ADR-003 Table 2 row 3): a ``working/`` with no ``state.toml`` (``state_bytes
    is None``) and a ``working/state.toml`` of invalid TOML (``b"not = toml ="``).
    The in-process ``test_absent_working_dir_exits_three`` and
    ``test_unparseable_state_exits_three`` (``tests/test_wordcount_command.py``)
    pin both shapes to exit ``3``; this proof re-asserts the same boundary at the
    real packaging layer. Verification choice: the boundary is a small, enumerable
    pair, so a two-case ``parametrize`` is the right adversary, not Hypothesis.
    Like ``state reconcile``, ``wordcount`` is now a subcommand of the single
    ``novel`` multiplexer, run as ``novel wordcount`` with no further arguments
    (the ``wordcount`` mount verb alone); it is built by this module's
    ``installed_novel_script`` fixture (which wraps ``_build_and_install_novel``).
    The shared ``assert_installed_state_error`` harness asserts the full exit-3
    contract: exit ``3``, an ``ok: false`` envelope, no traceback on stderr, and a
    non-blank operator message (design §10 — a state fault yields a message, not a
    stack trace; the exact wording is left unpinned because the contract does not
    fix it; ExecPlan addendum 6.2.6.2). The 180s timeout supersedes the 30s
    project default.
    """
    run_dir = tmp_path / "run-state-error"
    working_dir = run_dir / "working"
    working_dir.mkdir(parents=True)
    if state_bytes is not None:
        (working_dir / "state.toml").write_bytes(state_bytes)

    assert_installed_state_error(installed_novel_script, run_dir, "wordcount")
