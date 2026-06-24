"""Step definitions for the ``reconcile`` recovery scenario.

These drive ``check`` and ``reconcile`` against the roadmap headline tree — a
settled ``working/`` tree whose ``[word_counts]`` claims a done chapter the
on-disk drafts do not corroborate — and assert the roadmap success clause: the
drift is detected by ``check`` at exit ``4`` with a ``recount`` reconciliation,
repaired by ``reconcile`` at exit ``0`` (rewriting ``[word_counts]`` from the
drafts, logging a recovery entry, removing no file), and re-checked clean at exit
``0`` (design §3.4, §4.1, §5.4).

Both commands are driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the other BDD
suites do, so the externally observable exit code is what the scenario asserts.
The runner step ``chdir``'s into the prepared tree's parent first because both
commands resolve a cwd-relative ``working/`` (Decision Log D-CWD). Fixture state
flows between steps through ``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_reconcile_bdd.py``.
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
from novel_ralph_skill.state import load_state

if typ.TYPE_CHECKING:
    from pathlib import Path


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree and the per-command exit codes captured across the steps."""

    working: Path
    files_before: set[str]
    check_code: int | None = None
    reconcile_code: int | None = None
    recheck_code: int | None = None


def _run(working: Path, command: str, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``command`` through ``run`` from ``working.parent``; return the code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command="novel-state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


@given(
    "a settled tree whose state claims a done chapter the drafts deny",
    target_fixture="outcome",
)
def stale_done_claim_tree(tmp_path: Path) -> _Outcome:
    """Build the roadmap headline ``done-claim-stale-word-counts`` tree.

    Returns
    -------
    _Outcome
        The built ``working/`` path and the set of files present before any
        repair; the exit codes are filled in by the run steps.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    files = {str(p.relative_to(working)) for p in working.rglob("*") if p.is_file()}
    return _Outcome(working=working, files_before=files)


@when("check runs against that tree")
def run_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``check`` and capture its exit code."""
    outcome.check_code = _run(outcome.working, "check", monkeypatch)


@then("check exits 4 reporting a recount reconciliation")
def check_exits_four(outcome: _Outcome) -> None:
    """Assert ``check`` flagged the drift at exit ``4``."""
    assert outcome.check_code == ExitCode.ACTIONABLE_FINDING, (
        f"expected check exit 4, got {outcome.check_code}"
    )


@when("reconcile runs against that tree")
def run_reconcile(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``reconcile`` and capture its exit code."""
    outcome.reconcile_code = _run(outcome.working, "reconcile", monkeypatch)


@then("reconcile exits 0 and rewrites the word counts from the drafts")
def reconcile_repairs(outcome: _Outcome) -> None:
    """Assert ``reconcile`` exited ``0`` and the table now matches the drafts."""
    assert outcome.reconcile_code == ExitCode.SUCCESS, (
        f"expected reconcile exit 0, got {outcome.reconcile_code}"
    )
    state = load_state(outcome.working / "state.toml")
    assert dict(state.word_counts.by_chapter) == {"01": 0, "02": 24000, "03": 20800}, (
        "the recount must rewrite [word_counts] to the disk-derived values"
    )


@then("reconcile removes no working file and logs a recount recovery entry")
def reconcile_logs_and_keeps_files(outcome: _Outcome) -> None:
    """Assert no file was removed and a ``recount`` receipt was appended."""
    after = {
        str(p.relative_to(outcome.working))
        for p in outcome.working.rglob("*")
        if p.is_file()
    }
    assert outcome.files_before <= after, "reconcile must remove no working/ file"
    log = (outcome.working / "log.md").read_text(encoding="utf-8")
    assert "recount" in log, "reconcile must append a recount recovery entry to log.md"


@then("a follow-up check exits 0")
def follow_up_check_clean(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert the reconciled tree re-checks clean at exit ``0``."""
    outcome.recheck_code = _run(outcome.working, "check", monkeypatch)
    assert outcome.recheck_code == ExitCode.SUCCESS, (
        f"expected follow-up check exit 0, got {outcome.recheck_code}"
    )
