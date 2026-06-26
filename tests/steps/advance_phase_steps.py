"""Step definitions for the out-of-order ``advance-phase`` refusal scenario.

These drive the ``advance-phase`` mutator against the named corpus tree
``INCOHERENT_VARIANTS["completed-prefix-gap"]`` — a ``drafting``-phase tree whose
``phase.completed = ("premise", "characters")`` already violates the
``completed-prefix`` invariant — and assert the roadmap success criterion: the
advance exits ``3`` (state error), never the benign ``1``, and leaves
``state.toml`` byte-for-byte intact (design §3.2, §4.1, §9; ExecPlan Decision
Log D7).

The mutator is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the contract
tests do, so the externally observable exit code is what the scenario asserts.
Fixture state (the built ``working/`` path and the captured exit code) flows
between steps through ``target_fixture`` returns, the pytest-bdd idiom for
sharing context without module-level mutable state.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml``
exempts from the assert/argument-count rules) and is imported into the scenario
binder ``tests/test_advance_phase_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
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
    """The captured exit code and the prior bytes for the refusal assertions."""

    working: Path
    before: bytes
    exit_code: int | None = None


@given(
    "a working tree whose phase.completed is not the in-order prefix",
    target_fixture="outcome",
)
def out_of_order_tree(tmp_path: Path) -> _Outcome:
    """Build the ``completed-prefix-gap`` tree and record its prior bytes.

    Returns
    -------
    _Outcome
        The built ``working/`` path and the ``state.toml`` bytes before the run.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["completed-prefix-gap"]
    working = wc.build_working_tree(spec, tmp_path)
    before = (working / "state.toml").read_bytes()
    return _Outcome(working=working, before=before)


@when("advance-phase runs against that tree")
def run_advance_phase(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``advance-phase`` through ``run`` and capture the exit code."""
    monkeypatch.chdir(outcome.working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["advance-phase"],
            RunContext(command="novel state", working_dir="working", human=False),
        )
    outcome.exit_code = typ.cast("int", excinfo.value.code)


@then("advance-phase exits 3")
def asserts_exit_three(outcome: _Outcome) -> None:
    """Assert the advance exited ``3`` (state error), never the benign ``1``."""
    assert outcome.exit_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {outcome.exit_code}"
    )


@then("the prior state.toml is byte-for-byte unchanged")
def asserts_state_unchanged(outcome: _Outcome) -> None:
    """Assert the refused advance left ``state.toml`` byte-for-byte intact."""
    after = (outcome.working / "state.toml").read_bytes()
    assert after == outcome.before, "the refused advance mutated state.toml"
