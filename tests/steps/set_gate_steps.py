"""Step definitions for the ``set-gate`` behavioural scenarios.

Drives ``set-gate`` against the directly built gate/drafting trees and asserts the
three headline arms of the roadmap 2.2.4 success criterion: a ``--knitting-30``
repair on a crossed-ratio prior exits ``0``, writes ``done_30`` true, and leaves
the tree coherent so a follow-up ``novel-state check`` exits ``0``; the same flag
on a sub-threshold prior is refused with exit ``3`` and leaves ``state.toml``
byte-for-byte intact; and a no-flag ``set-gate`` faults with exit ``2`` (the
``GateDraftingUsageError`` usage channel) without mutating the file (design
sections 4.1, 5.2, 9).

The mutator is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, so the externally
observable exit code is what the scenarios assert. Fixture state (the built
``working/`` path, a snapshot of the prior bytes, and the captured exit code)
flows between steps through ``target_fixture`` returns, the pytest-bdd idiom for
sharing context without module-level mutable state. This module lives under
``tests/steps/`` (the directory ``pyproject.toml`` exempts from the
assert/argument-count rules) and is imported into the scenario binder
``tests/test_set_gate_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import tomllib
import typing as typ

import pytest
from _gate_drafting_fixtures import build, gate_lags_ratio_spec, ratio_not_crossed_spec
from pytest_bdd import given, then, when

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path


@dc.dataclass
class _Outcome:
    """The built tree, a snapshot of the prior bytes, and the captured exit codes."""

    working: Path
    before: bytes
    set_code: int | None = None
    check_code: int | None = None


def _drive(working: Path, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``argv`` through ``run`` from ``working.parent``; return the exit code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command="novel state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


@given(
    "a drafting tree whose drafted ratio has crossed 0.30 with done_30 false",
    target_fixture="outcome",
)
def crossed_ratio_tree(tmp_path: Path) -> _Outcome:
    """Build the 0.45-ratio prior whose knitting gates are all false.

    Returns
    -------
    _Outcome
        The built ``working/`` path and its prior bytes, ready for the run steps.
    """
    working = build(gate_lags_ratio_spec(), tmp_path)
    return _Outcome(working=working, before=(working / "state.toml").read_bytes())


@given(
    "a drafting tree whose drafted ratio is below every threshold with done_30 false",
    target_fixture="outcome",
)
def sub_threshold_tree(tmp_path: Path) -> _Outcome:
    """Build the 0.15-ratio prior whose knitting gates are all false.

    Returns
    -------
    _Outcome
        The built ``working/`` path and its prior bytes, ready for the run steps.
    """
    working = build(ratio_not_crossed_spec(), tmp_path)
    return _Outcome(working=working, before=(working / "state.toml").read_bytes())


@when("set-gate --knitting-30 runs against that tree")
def run_set_gate_knitting_30(
    outcome: _Outcome, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive ``set-gate --knitting-30`` and capture its exit code."""
    outcome.set_code = _drive(
        outcome.working, ["set-gate", "--knitting-30"], monkeypatch
    )


@when("set-gate runs against that tree with no gate flag")
def run_set_gate_no_flag(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive a no-flag ``set-gate`` and capture its exit code."""
    outcome.set_code = _drive(outcome.working, ["set-gate"], monkeypatch)


@then("set-gate exits 0")
def asserts_set_exit_zero(outcome: _Outcome) -> None:
    """Assert the repair exited ``0``."""
    assert outcome.set_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.set_code}"
    )


@then("set-gate exits 3")
def asserts_set_exit_three(outcome: _Outcome) -> None:
    """Assert the refusal exited ``3`` (state error)."""
    assert outcome.set_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {outcome.set_code}"
    )


@then("set-gate exits 2")
def asserts_set_exit_two(outcome: _Outcome) -> None:
    """Assert the no-flag fault exited ``2`` (usage error)."""
    assert outcome.set_code == ExitCode.USAGE_ERROR, (
        f"expected exit 2, got {outcome.set_code}"
    )


@then("gates.knitting.done_30 is true")
def asserts_gate_true(outcome: _Outcome) -> None:
    """Assert the on-disk knitting gate is now true."""
    raw = tomllib.loads((outcome.working / "state.toml").read_text("utf-8"))
    assert raw["gates"]["knitting"]["done_30"] is True, (
        "the repair must write done_30 true"
    )


@then("novel-state check exits 0")
def asserts_check_coherent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a follow-up ``novel-state check`` stays coherent (exit 0)."""
    outcome.check_code = _drive(outcome.working, ["check"], monkeypatch)
    assert outcome.check_code == ExitCode.SUCCESS, (
        f"expected check exit 0, got {outcome.check_code}"
    )


@then("the prior state.toml is byte-for-byte unchanged")
def asserts_state_unchanged(outcome: _Outcome) -> None:
    """Assert the refused or faulted run left ``state.toml`` byte-for-byte intact."""
    assert (outcome.working / "state.toml").read_bytes() == outcome.before, (
        "a refused or faulted set-gate must leave state.toml unchanged"
    )
