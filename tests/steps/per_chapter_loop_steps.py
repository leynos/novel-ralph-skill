"""Step definitions for the per-chapter deterministic-loop scenario (6.2.2).

These prove the roadmap 6.2.2 clause: the deterministic spine — ``recount``,
``novel-done``, ``wordcount``, ``desloppify``, and ``novel-compile --check`` —
*composes* over a real ``working/`` tree (design §7.2, Figure 3). Where roadmap
6.2.1 proved each command's machine/human envelope per phase in isolation, this
suite drives the per-chapter pipeline as a single ordered drive and asserts the
three deterministic decisions that gate the loop (design §9 lines 814-847): a
clean pass, a caught stale compile (§4.2, §4.3, §10), a reported crossed knitting
gate (§4.5), and a refused out-of-order phase advance (§3.2, §4.1).

Every command runs through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, the entry path the
harness and an operator use, mirroring :mod:`tests.steps.torn_turn_recovery_steps`
and :mod:`tests.steps.advance_phase_steps`. The read surface is composed of five
different Cyclopts apps, so :func:`_run_capturing` selects the matching
``build_app`` factory and ``RunContext`` for each ``command_name`` rather than
binding a single module-level app (ExecPlan advisory A3). ``novel-compile`` is
always driven with ``["--check"]`` — its bare invocation *writes* ``compiled.md``,
which the read-only loop must never do (ExecPlan D-CHECK-ARGV;
:mod:`tests.test_compile_check_snapshots`).

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_per_chapter_loop_bdd.py``.
"""

from __future__ import annotations

import contextlib
import dataclasses as dc
import io
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands import (
    _compile,
    _desloppify,
    _novel_done,
    _wordcount,
    novel_state,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts

# The drafted by-chapter totals every clean-pass assertion pins, derived from the
# corpus ``_DRAFTED_WORDS`` for the all-hold tree (the three drafted chapters sum
# to 68800). A no-op recount over this tree leaves the table at these values.
_DRAFTED_BY_CHAPTER: typ.Final[dict[str, int]] = {"01": 24000, "02": 24000, "03": 20800}
_DRAFTED_TOTAL: typ.Final = 68800

# Each loop command maps to its ``build_app`` factory: the read surface is five
# distinct Cyclopts apps, so the runner selects the matching one per command_name
# (advisory A3) rather than binding a single module-level app.
_BUILD_APPS: typ.Final[dict[str, cabc.Callable[[], cyclopts.App]]] = {
    "novel-state": novel_state.build_app,
    "novel-done": _novel_done.build_app,
    "wordcount": _wordcount.build_app,
    "desloppify": _desloppify.build_app,
    "novel-compile": _compile.build_app,
}


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree plus each command's captured ``(exit_code, envelope)``.

    The captures accumulate across the ``When`` steps so the ``Then`` steps assert
    the pinned envelope without re-driving the command boundary.
    """

    working: Path
    captures: dict[str, tuple[int, dict[str, object]]] = dc.field(default_factory=dict)
    state_before: bytes | None = None


def _run_capturing(
    working: Path,
    command_name: str,
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, dict[str, object]]:
    """Drive ``command_name`` through ``run`` and return ``(exit_code, envelope)``.

    Selects the matching ``build_app`` factory and passes a matching
    ``RunContext(command=command_name, ...)``, ``chdir``-ing into the tree's parent
    first because every command resolves a cwd-relative ``working/`` (advisory A3).
    The command runs inside ``pytest.raises(SystemExit)`` — the shared ``run``
    wrapper exits with the body's code — and its machine-mode stdout is parsed as
    the JSON envelope.
    """
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            _BUILD_APPS[command_name](),
            argv,
            RunContext(command=command_name, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    return code, json.loads(stream.getvalue() or "{}")


def _result(outcome: _Outcome, command_name: str) -> dict[str, object]:
    """Return the parsed ``result`` block from ``command_name``'s captured envelope."""
    _code, envelope = outcome.captures[command_name]
    return typ.cast("dict[str, object]", envelope["result"])


@given("a coherent fully-drafted working tree", target_fixture="outcome")
def coherent_tree(tmp_path: Path) -> _Outcome:
    """Build the all-hold tree (phase ``done``, all gates crossed, compile matching).

    ``DONE_PREDICATE_ALL_HOLD`` is the fully-done tree the clean pass reads: the
    drafts match the ``[word_counts]`` table (so ``recount`` is a no-op), every
    done clause holds, all three knitting gates are crossed, and ``compiled.md``
    matches the ordered draft concatenation.

    Returns
    -------
    _Outcome
        The built ``working/`` path with an empty capture map for the run steps.
    """
    working = wc.build_working_tree(wc.DONE_PREDICATE_ALL_HOLD, tmp_path)
    return _Outcome(working=working)


@when("recount runs against the loop tree")
def run_recount(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-state recount`` and capture its envelope."""
    outcome.captures["recount"] = _run_capturing(
        outcome.working, "novel-state", ["recount"], monkeypatch
    )


@then("recount exits 0 and reports the drafted by-chapter counts")
def recount_clean(outcome: _Outcome) -> None:
    """Assert the no-op recount exits 0 and leaves the drafted by-chapter totals.

    The drafts already match the table, so the recount is a no-op on the
    word-count values: it exits 0 and reports the drafted ``{current, by_chapter}``
    unchanged (ExecPlan Risk 2 — the clean pass reads a tree the mutator leaves at
    the drafted totals).
    """
    code, _envelope = outcome.captures["recount"]
    assert code == ExitCode.SUCCESS, f"expected recount exit 0, got {code}"
    result = _result(outcome, "recount")
    assert result["current"] == _DRAFTED_TOTAL
    assert result["by_chapter"] == _DRAFTED_BY_CHAPTER


@when("novel-done runs against the loop tree")
def run_novel_done(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-done`` and capture its envelope."""
    outcome.captures["novel-done"] = _run_capturing(
        outcome.working, "novel-done", [], monkeypatch
    )


@then("novel-done exits 0 and every done clause holds")
def novel_done_clean(outcome: _Outcome) -> None:
    """Assert ``novel-done`` declares the tree done: exit 0, every §4.2 clause true."""
    code, _envelope = outcome.captures["novel-done"]
    assert code == ExitCode.SUCCESS, f"expected novel-done exit 0, got {code}"
    result = _result(outcome, "novel-done")
    assert all(result.values()), f"every done clause must hold, got {result}"


@when("wordcount runs against the loop tree")
def run_wordcount(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``wordcount`` and capture its envelope."""
    outcome.captures["wordcount"] = _run_capturing(
        outcome.working, "wordcount", [], monkeypatch
    )


@then("wordcount exits 0 and reports all three knitting gates crossed")
def wordcount_gates_crossed(outcome: _Outcome) -> None:
    """Assert ``wordcount`` reports all three crossed gates over the drafted total.

    This is the load-bearing §4.5 step: the cumulative envelope must carry
    ``gate_triggered_30/50/80 == True`` (past the final gate) at the 68800-word
    drafted total. It is the "a crossed gate is reported" success criterion folded
    into the clean pass.
    """
    code, _envelope = outcome.captures["wordcount"]
    assert code == ExitCode.SUCCESS, f"expected wordcount exit 0, got {code}"
    cumulative = typ.cast(
        "dict[str, object]", _result(outcome, "wordcount")["cumulative"]
    )
    assert cumulative["current"] == _DRAFTED_TOTAL
    assert cumulative["gate_triggered_30"] is True
    assert cumulative["gate_triggered_50"] is True
    assert cumulative["gate_triggered_80"] is True


@when("desloppify runs against the loop tree")
def run_desloppify(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``desloppify`` and capture its envelope."""
    outcome.captures["desloppify"] = _run_capturing(
        outcome.working, "desloppify", [], monkeypatch
    )


@then("desloppify exits 0 with no violations over the drafted total")
def desloppify_clean(outcome: _Outcome) -> None:
    """Assert ``desloppify`` finds no violations over the drafted total: exit 0."""
    code, _envelope = outcome.captures["desloppify"]
    assert code == ExitCode.SUCCESS, f"expected desloppify exit 0, got {code}"
    result = _result(outcome, "desloppify")
    assert result["violations"] == []
    assert result["total_words"] == _DRAFTED_TOTAL


@when("novel-compile --check runs against the loop tree")
def run_compile_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-compile --check`` (the read surface) and capture its envelope."""
    outcome.captures["novel-compile"] = _run_capturing(
        outcome.working, "novel-compile", ["--check"], monkeypatch
    )


@then("novel-compile --check exits 0 and reports the compile is not diverged")
def compile_check_clean(outcome: _Outcome) -> None:
    """Assert ``novel-compile --check`` finds the compile matching: exit 0."""
    code, _envelope = outcome.captures["novel-compile"]
    assert code == ExitCode.SUCCESS, (
        f"expected novel-compile --check exit 0, got {code}"
    )
    assert _result(outcome, "novel-compile")["diverged"] is False


# --- gated decision: a stale compile is caught (§4.2, §4.3, §10) -------------


@given(
    "an otherwise-complete working tree whose compiled.md is byte-divergent",
    target_fixture="outcome",
)
def stale_compile_tree(tmp_path: Path) -> _Outcome:
    """Build the sole-stale-compile tree: every clause holds but the compile is stale.

    ``DONE_PREDICATE_SOLE_STALE_COMPILE`` is the all-hold tree carrying a
    count-coincident, byte-divergent ``compiled.md``. It exercises the
    otherwise-complete carve-out: ``novel-done`` surfaces the stale compile as an
    actionable finding (exit 4) and ``novel-compile --check`` reports it diverged
    (exit 4) — the §10 stale-compile failure mode at the loop boundary.

    Returns
    -------
    _Outcome
        The built ``working/`` path with an empty capture map for the run steps.
    """
    working = wc.build_working_tree(wc.DONE_PREDICATE_SOLE_STALE_COMPILE, tmp_path)
    return _Outcome(working=working)


@then("novel-done exits 4 reporting the compile is not consistent")
def novel_done_stale(outcome: _Outcome) -> None:
    """Assert ``novel-done`` flags the stale compile at exit 4, the carve-out."""
    code, _envelope = outcome.captures["novel-done"]
    assert code == ExitCode.ACTIONABLE_FINDING, (
        f"expected novel-done exit 4, got {code}"
    )
    assert _result(outcome, "novel-done")["compile_consistent"] is False


@then("novel-compile --check exits 4 reporting the compile is diverged")
def compile_check_stale(outcome: _Outcome) -> None:
    """Assert ``novel-compile --check`` reports the divergent compile at exit 4."""
    code, _envelope = outcome.captures["novel-compile"]
    assert code == ExitCode.ACTIONABLE_FINDING, (
        f"expected novel-compile --check exit 4, got {code}"
    )
    assert _result(outcome, "novel-compile")["diverged"] is True


# --- gated decision: an out-of-order phase advance is refused (§3.2, §4.1) ----


@given(
    "a working tree whose phase.completed skips the in-order prefix",
    target_fixture="outcome",
)
def out_of_order_tree(tmp_path: Path) -> _Outcome:
    """Build the ``completed-prefix-gap`` tree and record its prior ``state.toml``.

    ``INCOHERENT_VARIANTS["completed-prefix-gap"]`` is a ``drafting`` tree whose
    ``phase.completed = ("premise", "characters")`` skips the in-order prefix, so
    ``advance-phase`` must refuse it. The prior ``state.toml`` bytes are captured so
    a later step can assert the refused mutator left the file byte-for-byte intact.

    Returns
    -------
    _Outcome
        The built ``working/`` path and the captured prior ``state.toml`` bytes.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["completed-prefix-gap"]
    working = wc.build_working_tree(spec, tmp_path)
    return _Outcome(working=working, state_before=(working / "state.toml").read_bytes())


@when("advance-phase runs against the loop tree")
def run_advance_phase(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-state advance-phase`` and capture its envelope."""
    outcome.captures["advance-phase"] = _run_capturing(
        outcome.working, "novel-state", ["advance-phase"], monkeypatch
    )


@then("advance-phase exits 3 and leaves state.toml byte-for-byte intact")
def advance_phase_refused(outcome: _Outcome) -> None:
    """Assert the out-of-order advance exited 3 and never mutated ``state.toml``."""
    code, _envelope = outcome.captures["advance-phase"]
    assert code == ExitCode.STATE_ERROR, f"expected advance-phase exit 3, got {code}"
    after = (outcome.working / "state.toml").read_bytes()
    assert after == outcome.state_before, "the refused advance mutated state.toml"
