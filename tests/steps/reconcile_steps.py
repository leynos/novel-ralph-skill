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
import re
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
    drafts_before: dict[str, bytes]
    check_code: int | None = None
    reconcile_code: int | None = None
    recheck_code: int | None = None


def _draft_bytes(working: Path) -> dict[str, bytes]:
    """Return every chapter ``draft.md`` as raw bytes, keyed by relative path.

    Drafts are author-owned narrative: ``reconcile`` may only rewrite
    ``state.toml`` and ``log.md``, so capturing the exact bytes lets a later step
    assert byte-for-byte draft integrity across the repair.
    """
    return {
        str(p.relative_to(working)): p.read_bytes()
        for p in working.rglob("draft.md")
        if p.is_file()
    }


def _assert_drafts_unchanged(outcome: _Outcome) -> None:
    """Assert every chapter ``draft.md`` is byte-for-byte identical post-reconcile.

    ``reconcile`` repairs only the recomputable pair (``state.toml``/``log.md``);
    the author-owned drafts must be untouched. Comparing the full path→bytes
    mapping pins both that no draft body changed and that no ``draft.md`` was added
    or removed, beyond the coarser "no file removed" check.
    """
    drafts_after = _draft_bytes(outcome.working)
    assert drafts_after == outcome.drafts_before, (
        "reconcile must leave every chapter draft.md byte-for-byte identical; "
        "only state.toml and log.md may change"
    )


def _run(working: Path, command: str, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``command`` through ``run`` from ``working.parent``; return the code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command="novel state", working_dir="working", human=False),
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
    return _Outcome(
        working=working, files_before=files, drafts_before=_draft_bytes(working)
    )


def _relaxed_subset_cover_gap_spec() -> wc.WorkingTreeSpec:
    """Return a mid-draft relaxed subset whose by_chapter omits a drafted key.

    Manifest ``{1,2,3}``, on-disk ``{1,2}`` (chapter 3 is a real planned manifest
    entry with no directory), phase ``drafting``, with the drafted ``"02"`` key
    dropped from ``[word_counts].by_chapter``. The relaxed ``check`` suppresses the
    missing-directory ``manifest-disk-bijection`` break and fires
    ``word-counts-cover-drafts`` instead, which ``reconcile`` repairs by re-keying
    off the manifest (roadmap task 2.3.8). This mirrors the e2e fixture so the
    black-box scenario pins the same operator-visible contract.
    """
    drafted = tuple(
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
    planned = wc.ChapterSpec(
        number=3,
        slug="chapter-03",
        title="Chapter 3",
        target_words=100,
        draft_words=0,
        has_done_flag=False,
        write_directory=False,
    )
    return dc.replace(
        wc.COHERENT_BASELINE,
        chapters=(*drafted, planned),
        current_chapter=0,
        consecutive_clean=0,
        convergence_target=1,
        done_30=False,
        done_50=False,
        done_80=False,
        final_pass_complete=False,
        compiled=None,
        by_chapter_override={"01": 100, "03": 0},
        current_words_override=100,
    )


@given(
    "a mid-draft relaxed subset whose by_chapter omits a drafted chapter's key",
    target_fixture="outcome",
)
def relaxed_subset_cover_gap_tree(tmp_path: Path) -> _Outcome:
    """Build the mid-draft relaxed-subset cover-gap tree (roadmap task 2.3.8).

    Returns
    -------
    _Outcome
        The built ``working/`` path and the set of files present before any
        repair; the exit codes are filled in by the run steps.
    """
    working = wc.build_working_tree(_relaxed_subset_cover_gap_spec(), tmp_path)
    files = {str(p.relative_to(working)) for p in working.rglob("*") if p.is_file()}
    return _Outcome(
        working=working, files_before=files, drafts_before=_draft_bytes(working)
    )


@given(
    "a partial-init tree whose log.md is absent beside a present state.toml",
    target_fixture="outcome",
)
def partial_init_tree(tmp_path: Path) -> _Outcome:
    """Build a coherent baseline and unlink ``log.md`` (the partial-``init`` case).

    Returns
    -------
    _Outcome
        The built ``working/`` path and the set of files present after ``log.md``
        is removed; the exit codes are filled in by the run steps.
    """
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    (working / "log.md").unlink()
    files = {str(p.relative_to(working)) for p in working.rglob("*") if p.is_file()}
    return _Outcome(
        working=working, files_before=files, drafts_before=_draft_bytes(working)
    )


@then("reconcile exits 0 and recreates log.md")
def reconcile_recreates_log(outcome: _Outcome) -> None:
    """Assert ``reconcile`` exited ``0`` and ``log.md`` is present again."""
    assert outcome.reconcile_code == ExitCode.SUCCESS, (
        f"expected reconcile exit 0, got {outcome.reconcile_code}"
    )
    assert (outcome.working / "log.md").exists(), "reconcile must recreate log.md"


@then("reconcile removes no working file and logs a recreate-log recovery entry")
def reconcile_recreate_log_keeps_files(outcome: _Outcome) -> None:
    """Assert no file was removed and a ``recreate-log`` receipt was appended."""
    after = {
        str(p.relative_to(outcome.working))
        for p in outcome.working.rglob("*")
        if p.is_file()
    }
    assert outcome.files_before <= after, "reconcile must remove no working/ file"
    _assert_drafts_unchanged(outcome)
    log = (outcome.working / "log.md").read_text(encoding="utf-8")
    assert "recreate-log" in log, "reconcile must append a recreate-log recovery entry"


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
    """Assert no file removed and a structured ``recount`` receipt was appended.

    The receipt is pinned as the design's audited reconciliation entry rather than
    a bare ``recount`` substring: a single ``log.md`` line that names the
    ``reconcile: recount`` operation and the repaired field set (``[word_counts]``,
    with the disk-derived ``current`` total and chapter count). This survives a
    behaviour-preserving refactor of the prose but fails if the operation or the
    repaired fields drift.
    """
    after = {
        str(p.relative_to(outcome.working))
        for p in outcome.working.rglob("*")
        if p.is_file()
    }
    assert outcome.files_before <= after, "reconcile must remove no working/ file"
    _assert_drafts_unchanged(outcome)
    log = (outcome.working / "log.md").read_text(encoding="utf-8")
    # The drafts hold {"01": 0, "02": 24000, "03": 20800} → 44800 across 3 chapters.
    receipt = re.search(
        r"^- \S+ reconcile: recount: "
        r"recounting \[word_counts\] from the drafts: "
        r"current 44800 across 3 chapters$",
        log,
        re.MULTILINE,
    )
    assert receipt is not None, (
        "reconcile must append a structured recount receipt pinning the "
        "reconcile: recount operation and the repaired [word_counts] field set "
        f"(current 44800 across 3 chapters); got log.md:\n{log}"
    )


@then("a follow-up check exits 0")
def follow_up_check_clean(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert the reconciled tree re-checks clean at exit ``0``."""
    outcome.recheck_code = _run(outcome.working, "check", monkeypatch)
    assert outcome.recheck_code == ExitCode.SUCCESS, (
        f"expected follow-up check exit 0, got {outcome.recheck_code}"
    )
