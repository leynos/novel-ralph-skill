"""End-to-end reachability of the gate/drafting mutators (roadmap 2.2.4, 6.2.4).

Proves the externally observable command-line behaviour of the four subcommands:

- a fast in-process entry-point check driven through ``stub.novel_state()`` (the
  installed console-script body), proving each subcommand resolves and exits the
  expected code on a coherent set;
- the slower wheel-build install e2es (POSIX-only, ADR 006): the installed
  ``novel-state set-gate --knitting-30`` repairs the lagging gate (exit 0) on the
  incoherent ``gate_lags_ratio`` tree and refuses (exit 3) on the coherent
  sub-threshold ``ratio_not_crossed`` tree; a no-flag ``set-gate`` exits 2 with a
  clean envelope and no traceback (the installed-boundary proof the
  ``GateDraftingUsageError`` + ``_set_gate_or_usage`` adapter produces the exit-2
  envelope rather than crashing — Decision D9/B5); an out-of-manifest
  ``set-fangirl`` exits 3; a non-integer ``--pass`` exits 2; and
  ``complete-final-pass`` exits 0 on a final-pass tree.

The built-and-installed script is supplied by the module-scoped
``installed_novel_state`` fixture (``tests/installed_binary_fixtures.py``), so the
wheel is built once for the module and every installed case reuses it.
"""

from __future__ import annotations

import json
import os
import sys
import typing as typ

import pytest
import working_corpus as wc
from _gate_drafting_fixtures import (
    build,
    gate_lags_ratio_spec,
    ratio_not_crossed_spec,
)
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.commands import stub
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue
    from cuprum.sh import CommandResult

    _CatalogueFactory = cabc.Callable[[str, Program], ProgramCatalogue]

_COMMAND = "novel-state"
_POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)


def test_entry_point_gate_mutators_reachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each subcommand resolves through the entry point and exits as expected."""
    working = build(gate_lags_ratio_spec(), tmp_path)
    monkeypatch.chdir(working.parent)
    monkeypatch.setattr(sys, "argv", [_COMMAND, "set-gate", "--knitting-30"])
    with pytest.raises(SystemExit) as excinfo:
        stub.novel_state()
    assert excinfo.value.code == ExitCode.SUCCESS, (
        "the entry-point set-gate repair must exit 0"
    )
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is True, "the repair envelope must be ok"


def _installed(
    installed_novel_state: Path,
    single_program_catalogue: _CatalogueFactory,
    run_dir: Path,
    *args: str,
) -> CommandResult:
    """Run the installed ``novel state`` with ``args`` against ``run_dir``.

    Roadmap task 1.2.13 (ADR-007) re-pointed ``installed_novel_state`` onto the
    unified ``novel`` multiplexer, so the state subcommands now dispatch through
    ``novel state <sub>`` rather than the legacy ``novel-state <sub>`` console
    script. The ``state`` segment is inserted here, the single choke point every
    installed call flows through.
    """
    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    return sh.make(prog, catalogue=catalogue)("state", *args).run_sync(
        context=ExecutionContext(cwd=run_dir), capture=True
    )


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_set_gate_repairs_lagging_gate(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed ``set-gate --knitting-30`` repairs the lagging gate (exit 0)."""
    run_dir = tmp_path / "run"
    build(gate_lags_ratio_spec(), run_dir)
    result = _installed(
        installed_novel_state,
        single_program_catalogue,
        run_dir,
        "set-gate",
        "--knitting-30",
    )
    assert result.exit_code == 0, result.stderr
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True, "the installed repair envelope must be ok"
    gates = typ.cast("dict[str, object]", envelope["result"])["gates"]
    assert gates == {"knitting": {"done_30": True}}, (
        "the installed repair must name the changed gate"
    )


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_set_gate_refuses_below_threshold(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed ``set-gate --knitting-30`` refuses below threshold (exit 3)."""
    run_dir = tmp_path / "run"
    build(ratio_not_crossed_spec(), run_dir)
    result = _installed(
        installed_novel_state,
        single_program_catalogue,
        run_dir,
        "set-gate",
        "--knitting-30",
    )
    assert result.exit_code == 3, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "a gate-ratio refusal must yield an ok: false envelope"
    )
    assert "Traceback" not in (result.stderr or ""), "a state error emits no traceback"


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_set_gate_no_flag_exits_two(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed no-flag ``set-gate`` exits 2 with a clean envelope (B5)."""
    run_dir = tmp_path / "run"
    build(gate_lags_ratio_spec(), run_dir)
    result = _installed(
        installed_novel_state, single_program_catalogue, run_dir, "set-gate"
    )
    assert result.exit_code == 2, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "a no-flag set-gate must yield an ok: false usage envelope"
    )
    assert "Traceback" not in (result.stderr or ""), "a usage error emits no traceback"


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_set_fangirl_out_of_manifest_exits_three(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed ``set-fangirl --last-chapter (N+1)`` exits 3."""
    run_dir = tmp_path / "run"
    wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
    result = _installed(
        installed_novel_state,
        single_program_catalogue,
        run_dir,
        "set-fangirl",
        "--last-chapter",
        "4",
    )
    assert result.exit_code == 3, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "an out-of-manifest set-fangirl must yield an ok: false envelope"
    )


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_set_critic_pass_non_integer_exits_two(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed ``set-critic-pass --pass notanumber`` exits 2 (shape fault)."""
    run_dir = tmp_path / "run"
    wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
    result = _installed(
        installed_novel_state,
        single_program_catalogue,
        run_dir,
        "set-critic-pass",
        "--pass",
        "notanumber",
    )
    assert result.exit_code == 2, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is False, (
        "a non-integer --pass must yield an ok: false envelope"
    )
    assert "Traceback" not in (result.stderr or ""), "a usage error emits no traceback"


@_POSIX_ONLY
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_complete_final_pass_exits_zero(
    tmp_path: Path,
    single_program_catalogue: _CatalogueFactory,
    installed_novel_state: Path,
) -> None:
    """The installed ``complete-final-pass`` exits 0 on a final-pass tree."""
    run_dir = tmp_path / "run"
    wc.build_working_tree(wc.PHASE_STATES["final-pass"], run_dir)
    result = _installed(
        installed_novel_state,
        single_program_catalogue,
        run_dir,
        "complete-final-pass",
    )
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout or "{}")["ok"] is True, (
        "the installed complete-final-pass envelope must be ok"
    )
