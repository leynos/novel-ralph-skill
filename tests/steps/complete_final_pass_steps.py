"""Step definitions for the ``complete-final-pass`` behavioural scenario.

Drives ``complete-final-pass`` against the coherent ``final-pass`` corpus tree
(whose ``final_pass_complete`` starts false) and asserts the roadmap 2.2.4 success
criterion: the flip exits ``0``, writes the gate true, and leaves the tree coherent
so a follow-up ``novel-state check`` exits ``0`` (design §4.1). The mutator is
driven through the shared :func:`novel_ralph_skill.contract.runner.run` wrapper, so
the externally observable exit code is what the scenario asserts.

Fixture state (the built ``working/`` path and the captured exit codes) flows
between steps through ``target_fixture`` returns, the pytest-bdd idiom for sharing
context without module-level mutable state. This module lives under
``tests/steps/`` (the directory ``pyproject.toml`` exempts from the
assert/argument-count rules) and is imported into the scenario binder
``tests/test_complete_final_pass_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import tomllib
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path


@dc.dataclass
class _Outcome:
    """The built tree and the captured exit codes for the scenario assertions."""

    working: Path
    flip_code: int | None = None
    check_code: int | None = None


def _drive(working: Path, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``argv`` through ``run`` from ``working.parent``; return the exit code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command="novel-state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


@given(
    "a coherent final-pass tree with the final gate off",
    target_fixture="outcome",
)
def coherent_final_pass_tree(tmp_path: Path) -> _Outcome:
    """Build the coherent ``final-pass`` tree (its final gate starts false).

    Returns
    -------
    _Outcome
        The built ``working/`` path, ready for the flip and check steps.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["final-pass"], tmp_path)
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    assert raw["gates"]["final"]["final_pass_complete"] is False, (
        "the final-pass tree must start with the final gate off"
    )
    return _Outcome(working=working)


@when("complete-final-pass runs against that tree")
def run_complete_final_pass(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``complete-final-pass`` and capture its exit code."""
    outcome.flip_code = _drive(outcome.working, ["complete-final-pass"], monkeypatch)


@then("complete-final-pass exits 0")
def asserts_flip_exit_zero(outcome: _Outcome) -> None:
    """Assert the flip exited ``0``."""
    assert outcome.flip_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.flip_code}"
    )


@then("gates.final.final_pass_complete is true")
def asserts_gate_true(outcome: _Outcome) -> None:
    """Assert the on-disk final gate is now true."""
    raw = tomllib.loads((outcome.working / "state.toml").read_text("utf-8"))
    assert raw["gates"]["final"]["final_pass_complete"] is True, (
        "the flip must write final_pass_complete true"
    )


@then("novel-state check exits 0")
def asserts_check_coherent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a follow-up ``novel-state check`` stays coherent (exit 0)."""
    outcome.check_code = _drive(outcome.working, ["check"], monkeypatch)
    assert outcome.check_code == ExitCode.SUCCESS, (
        f"expected check exit 0, got {outcome.check_code}"
    )
