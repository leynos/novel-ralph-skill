"""Installed-script e2e for the ADR 009 drafting bijection relaxation (2.1.7).

These prove the externally observable workflow change through the **installed**
``novel-state`` console-script, run by absolute path through a cuprum
``ProgramCatalogue`` (the proven harness in ``test_console_scripts_e2e.py`` and
``test_novel_state_check.py``):

- a real ``working/`` tree at ``[phase].current == drafting`` whose manifest
  declares chapters 1..3 but whose disk holds only chapters 1 and 2 (a real
  planned-but-undrafted chapter 3) exits ``0`` — the mid-draft subset the
  relaxation now accepts (was exit ``4`` before this change). The exit-``0`` case
  also asserts the ``result`` JSON carries **no** ``reconciliation`` key, because a
  relaxed-clean subset yields an empty disk-evidence verdict and ``_check`` attaches
  reconciliation only when disk evidence fired;
- the SAME tree advanced to ``final-pass`` (the missing directory unchanged) exits
  ``4`` with ``manifest-disk-bijection`` in ``result.violations`` — the exact
  bijection re-tightens at the terminal phases (ADR 009 / D3).

The installed script is supplied by the module-scoped ``installed_novel_state``
fixture (built once per module). POSIX-only per ADR 006; the ``"check"`` subcommand
argv is mandatory because a bare ``novel-state`` prints help and exits ``0``. The
180s per-test timeout supersedes the 30s project default, reusing the proven
precedent (``test_console_scripts_e2e.py`` lines 127-128).
"""

from __future__ import annotations

import json
import os
import typing as typ

import pytest
import working_corpus as wc
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)

# The manifest-disk subset shape every case shares: chapters 1 and 2 are drafted
# on disk; chapter 3 is a real planned chapter present in the manifest but with no
# directory (write_directory=False), so manifest = {1,2,3} and on-disk = {1,2}.
_DRAFTED = tuple(
    wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=100,
        draft_words=100,
        has_done_flag=False,
    )
    for number in (1, 2)
)
_PLANNED = wc.ChapterSpec(
    number=3,
    slug="chapter-03",
    title="Chapter 3",
    target_words=100,
    draft_words=0,
    has_done_flag=False,
    write_directory=False,
)


def _subset_spec(phase: str) -> wc.WorkingTreeSpec:
    """Return the manifest-{1,2,3}/on-disk-{1,2} subset spec at ``phase``.

    The completed-phase prefix is the exact in-order slice of ``PHASE_ORDER``
    preceding ``phase`` (pure-state invariants 1 and 2), so only the bijection
    direction varies between the drafting and final-pass cases.
    """
    completed = wc.PHASE_ORDER[: wc.PHASE_ORDER.index(phase)]
    return wc.WorkingTreeSpec(
        phase_current=phase,
        phase_completed=completed,
        chapters=(*_DRAFTED, _PLANNED),
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=2,
    )


def _run_check(
    working_parent: Path,
    installed_novel_state: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> sh.CommandResult:
    """Run the installed ``novel-state check`` with ``working_parent`` as the cwd."""
    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-bijection-e2e", prog)
    return sh.make(prog, catalogue=catalogue)("state", "check").run_sync(
        context=ExecutionContext(cwd=working_parent), capture=True
    )


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_check_exits_zero_on_drafting_subset(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """A mid-drafting manifest subset exits ``0`` with no reconciliation (ADR 009).

    Manifest ``{1,2,3}``, on-disk ``{1,2}`` at ``[phase].current == drafting``: the
    relaxed checker accepts the subset, so the installed script exits ``0``. Because
    the disk-evidence verdict is empty, ``result`` carries no ``reconciliation``
    key — a clean tree implies no repair.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    wc.build_working_tree(_subset_spec("drafting"), dest)

    result = _run_check(dest, installed_novel_state, single_program_catalogue)
    assert result.exit_code == ExitCode.SUCCESS, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True, envelope
    assert envelope["result"]["violations"] == [], envelope
    assert "reconciliation" not in envelope["result"], envelope


@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_check_exits_four_at_final_pass(
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """The same subset advanced to ``final-pass`` exits ``4`` (ADR 009 / D3).

    Manifest ``{1,2,3}``, on-disk ``{1,2}`` at ``[phase].current == final-pass``:
    the exact bijection re-tightens at the terminal phases, so the missing
    chapter-03 directory fires ``manifest-disk-bijection`` and the installed script
    exits ``4`` with that name in ``result.violations``.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    wc.build_working_tree(_subset_spec("final-pass"), dest)

    result = _run_check(dest, installed_novel_state, single_program_catalogue)
    assert result.exit_code == ExitCode.ACTIONABLE_FINDING, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is False, envelope
    assert "manifest-disk-bijection" in envelope["result"]["violations"], envelope
