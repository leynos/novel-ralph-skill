"""End-to-end proof installed ``novel desloppify`` ships its §6 pack (roadmap 5.1.2).

This is the design §9 success criterion made executable and the defence of the
ExecPlan Risk "pack not in wheel": build a wheel from this package, install it
into a throwaway virtual environment, materialise a ``working/`` tree with a
manifest and one offending draft, and run the installed ``novel desloppify``
**by absolute path** through a cuprum catalogue that **registers that exact
path** (the single ``novel`` script with the ``desloppify`` mount verb).
The registration is the execution gate (``cuprum/sh.py:make`` calls
``catalogue.lookup``, which raises ``UnknownProgramError`` for any unregistered
program), so the test reuses the ``single_program_catalogue`` fixture exactly as
``tests/test_console_scripts_e2e.py`` and ``tests/test_novel_state_check.py`` do.

An offending tree exits ``4`` and names the offending rule in the stdout JSON —
proving the packaged ``offenders.toml`` travelled in the wheel — and a clean tree
exits ``0``. This e2e is POSIX-only (ADR-006) and slow (build + venv + install),
so it is skipped off POSIX and given an explicit 180s timeout that supersedes the
30s project default.

This module also proves the per-novel device-ledger enforcement mode travels in
the wheel (roadmap 7.1.2; the defence of the Risk "ledger does not work after
install"): it writes a ``device-ledger.toml`` into the throwaway tree and runs the
installed ``novel desloppify --ledger <tree>/device-ledger.toml``. Unlike the packs, the
ledger is read from a filesystem ``--ledger PATH``, not the package tree, so this
proves the *mode* (the command code) travels, not a packaged resource. The ledger
e2e exercises a ``max_count`` over-spend only: every chapter draft is overwritten
with the same text, so three identical ``sternum`` hits over ``max_count = 2`` is
a robust over-ration regardless of chapter attribution, while a ``sternum``-free
tree is the within-ration zero-spend case (ExecPlan WI6 / round-1 condition 2).
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


def _materialise_working(dest: Path, baseline: Path, draft_text: str) -> None:
    """Copy ``baseline`` to ``dest/working`` and overwrite each draft with text.

    The corpus ``baseline_tree`` builds a coherent ``working/`` in the parent
    process; copying it into the subprocess cwd (rather than hand-writing
    ``state.toml``) keeps the e2e in lock-step with the real state schema, exactly
    as ``tests/test_novel_state_check.py`` does. Every chapter draft is overwritten
    with ``draft_text`` so the test controls exactly which offenders are present.
    """
    working = dest / "working"
    shutil.copytree(baseline, working)
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text(draft_text, encoding="utf-8")


def _build_and_install_novel(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> Path:
    """Build a wheel, install it into a fresh venv, and return the ``novel`` script.

    Roadmap task 1.2.13 drives ``novel desloppify`` through the single ``novel``
    multiplexer, so the helper resolves the ``novel`` console-script rather than
    the legacy ``desloppify`` script (which still ships until task 1.2.15).
    """
    venv_dir = tmp_path / "venv"
    uv = sh.make(
        Program("uv"),
        catalogue=single_program_catalogue("desloppify-e2e", Program("uv")),
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
def test_installed_desloppify_flags_offender(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel desloppify`` flags an em-dash flood and exits ``4``.

    Proves the packaged ``offenders.toml`` travels in the wheel: the subprocess
    resolves the shipped pack via ``importlib.resources`` and reports the em-dash
    finding. The 180s timeout supersedes the 30s project default.
    """
    script_path = _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-flag"
    dest.mkdir()
    flood = "word—word—word—word—word—word—word " + "filler " * 20
    _materialise_working(dest, baseline_tree(), flood)

    prog = Program(str(script_path))
    catalogue = single_program_catalogue("desloppify-run", prog)
    result = sh.make(prog, catalogue=catalogue)("desloppify").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert result.exit_code == 4, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False
    assert "em-dash" in envelope["result"]["violations"]


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_desloppify_clean_tree_exits_zero(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel desloppify`` exits ``0`` over offender-free prose."""
    script_path = _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-clean"
    dest.mkdir()
    _materialise_working(dest, baseline_tree(), "A calm sentence with plain words.\n")

    prog = Program(str(script_path))
    catalogue = single_program_catalogue("desloppify-run", prog)
    result = sh.make(prog, catalogue=catalogue)("desloppify").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is True


# A one-device ledger rationing ``sternum`` to two spends across the manuscript.
# Three identical hits per draft is an over-ration regardless of attribution.
_MAX_COUNT_LEDGER = """\
schema_version = 1

[[device]]
id = "sternum"
pattern = "\\\\bsternum\\\\b"
max_count = 2
"""


def _run_installed_ledger(
    script_path: Path,
    dest: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> sh.CommandResult:
    """Run installed ``novel desloppify --ledger`` in ``dest``; return the result.

    Writes the test ledger into ``dest`` and runs the installed script by absolute
    path through a catalogue that registers exactly that path (the cuprum
    execution gate), exactly as the rule-pack e2e runs the bare command.
    """
    ledger_path = dest / "device-ledger.toml"
    ledger_path.write_text(_MAX_COUNT_LEDGER, encoding="utf-8")
    prog = Program(str(script_path))
    catalogue = single_program_catalogue("desloppify-ledger-run", prog)
    return sh.make(prog, catalogue=catalogue)(
        "desloppify", "--ledger", str(ledger_path)
    ).run_sync(context=ExecutionContext(cwd=dest), capture=True)


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_desloppify_ledger_flags_over_ration(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """The installed ``novel desloppify --ledger`` flags an over-ration and exits ``4``.

    Proves the ledger enforcement mode travels in the wheel: the subprocess loads
    the filesystem ledger via ``--ledger PATH`` and reports the over-ration
    ``sternum``. The 180s timeout supersedes the 30s project default.
    """
    script_path = _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-ledger-flag"
    dest.mkdir()
    # Three "sternum" per draft over max_count 2 is an over-ration.
    _materialise_working(dest, baseline_tree(), "sternum\nsternum\nsternum\n")

    result = _run_installed_ledger(script_path, dest, single_program_catalogue)
    assert result.exit_code == 4, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False
    assert "sternum" in envelope["result"]["violations"]


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_desloppify_ledger_within_ration_exits_zero(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    venv_scripts_dir: cabc.Callable[[Path], Path],
) -> None:
    """Installed ``novel desloppify --ledger`` exits ``0`` over a within-ration tree."""
    script_path = _build_and_install_novel(
        tmp_path, single_program_catalogue, venv_scripts_dir
    )
    dest = tmp_path / "run-ledger-clean"
    dest.mkdir()
    # No "sternum" anywhere: a zero-spend manuscript is within max_count 2. (Every
    # draft carries the same text, so a positive per-draft count would multiply
    # across chapters and breach the whole-manuscript ration; zero spends is the
    # robust within-ration case here.)
    _materialise_working(dest, baseline_tree(), "a plain calm line\n")

    result = _run_installed_ledger(script_path, dest, single_program_catalogue)
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is True
