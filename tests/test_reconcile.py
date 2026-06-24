"""Behavioural tests for the ``reconcile`` mutator (roadmap task 2.3.2).

These pin the externally observable contract of ``reconcile`` through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper:

- the roadmap **headline** (`docs/roadmap.md:651-652`): a settled tree claiming an
  uncorroborated done chapter is detected by ``check`` at exit ``4``, repaired by
  ``reconcile`` at exit ``0`` (rewriting ``[word_counts]``, logging a ``recount``
  receipt, removing no file), and re-checked clean at exit ``0``;
- the §5.4 worked under-count case (round-4 B2), exercised the same way;
- the **post-repair gate-clean** guard (round-4 B1): both word-count variants are
  ``gate-ratio-consistent``-clean after ``RECOUNT``, and a constructed
  threshold-crossing tree's recount does **not** silently produce a clean
  exit-``0`` (the scope boundary, D-GATES);
- the pending-turn rollback/complete recoveries (no deletion, logged), and the
  sole-violation regression guard for the headline variant.

The corpus is taken by the sanctioned ``working_corpus as wc`` value import the
other corpus suites use; every ``reconcile``/``check`` call is preceded by a
``monkeypatch.chdir`` into the materialised tree's parent.
"""

from __future__ import annotations

import contextlib
import dataclasses as dc
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._reconcile import reconcile
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, StateInputError, run
from novel_ralph_skill.state import (
    GATE_RATIO_CONSISTENT,
    load_state,
    validate_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"


def _drive(
    working: Path, command: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, dict[str, object]]:
    """Run ``command`` from ``working.parent`` and return ``(exit_code, envelope)``."""
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), json.loads(stream.getvalue() or "{}")


def _result(envelope: dict[str, object]) -> dict[str, object]:
    """Return the ``result`` mapping from a captured envelope."""
    return typ.cast("dict[str, object]", envelope["result"])


def _present_files(working: Path) -> set[Path]:
    """Return the relative paths of every file under ``working``."""
    return {path.relative_to(working) for path in working.rglob("*") if path.is_file()}


def _assert_gate_clean(working: Path) -> None:
    """Assert the reconciled ``state.toml`` has no ``gate-ratio-consistent`` breach."""
    reconciled = load_state(working / "state.toml")
    gate_breaches = [
        v.invariant
        for v in validate_state(reconciled)
        if v.invariant == GATE_RATIO_CONSISTENT
    ]
    assert gate_breaches == [], "the reconciled tree must be gate-ratio-consistent"


@pytest.mark.parametrize(
    "variant",
    ["done-claim-stale-word-counts", "done-flag-real-draft-undercount"],
)
def test_word_count_tree_detected_repaired_and_gate_clean(
    variant: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A word-count-stale tree: check 4, reconcile 0, re-check 0, all gate-clean.

    The roadmap headline and the §5.4 worked case (rounds B1/B2): ``reconcile``
    rewrites ``[word_counts]`` to the disk-derived values, appends a ``recount``
    receipt, removes no file, and the reconciled ``state.toml`` is
    ``gate-ratio-consistent``-clean so the follow-up ``check`` exits ``0`` (the
    variants are sub-threshold by construction; D-GATES).
    """
    working = wc.build_working_tree(wc.INCOHERENT_VARIANTS[variant][0], tmp_path)
    files_before = _present_files(working)

    code, env = _drive(working, "check", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, variant
    assert "word-counts-match-drafts" in typ.cast(
        "list[str]", _result(env)["violations"]
    )

    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, variant
    result = _result(env)
    assert result["action"] == "recount", "reconcile must report the recount action"
    assert "violations" not in result, (
        "the write-shaped result must not echo the check read shape"
    )

    # No file removed; a recount receipt is appended.
    assert files_before <= _present_files(working), variant
    assert "recount" in (working / "log.md").read_text(encoding="utf-8"), (
        "reconcile must append a recount recovery entry to log.md"
    )

    # The reconciled state is gate-clean and the follow-up check exits 0.
    _assert_gate_clean(working)
    code, env = _drive(working, "check", monkeypatch)
    assert code == ExitCode.SUCCESS, variant
    assert _result(env)["violations"] == [], "the reconciled tree must re-check clean"


def test_reconcile_recount_writes_disk_derived_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The headline ``reconcile`` writes the disk-derived per-chapter table."""
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    _code, _env = _drive(working, "reconcile", monkeypatch)
    reconciled = load_state(working / "state.toml")
    # Chapter 01 is empty on disk, so its phantom 10000 entry recounts to 0.
    assert dict(reconciled.word_counts.by_chapter) == {
        "01": 0,
        "02": 24000,
        "03": 20800,
    }, "the recount must rewrite by_chapter to the disk-derived per-chapter counts"
    assert reconciled.word_counts.current == 44800, (
        "current must equal the summed disk-derived counts"
    )


def test_threshold_crossing_recount_does_not_silently_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A threshold-crossing done-claim is not silently repaired (scope boundary).

    Negative fixture for D-GATES: a phantom table entry large enough that removing
    it (the recount) drops the ratio across the 80% gate the recorded gates reflect
    would leave ``gate-ratio-consistent`` failing. ``reconcile`` must **not**
    produce a clean exit-``0`` recount — the ``recount``-style ``_refuse_if_incoherent``
    backstop refuses with exit ``3`` rather than writing a gate-inconsistent tree.
    """
    first, second, third = wc.COHERENT_BASELINE.chapters
    # Empty the first chapter on disk; its phantom table entry (40000) keeps the
    # *table* total above 80% (104800/80000 = 1.31) so the recorded gates are all
    # true and the pre-repair tree is gate-consistent, but the recount drops the
    # draft total to 44800/80000 = 0.56 — below 80% — so a [word_counts]-only
    # recount would leave done_80 stale (gate-ratio-consistent failing).
    empty = dc.replace(first, draft_words=0, write_draft=False, has_done_flag=False)
    table = {
        "01": 40000,
        f"{second.number:02d}": second.draft_words,
        f"{third.number:02d}": third.draft_words,
    }
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        chapters=(empty, second, third),
        by_chapter_override=table,
        current_words_override=sum(table.values()),
        done_30=True,
        done_50=True,
        done_80=True,
    )
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)
    with pytest.raises(StateInputError, match="gate-ratio-consistent"):
        reconcile()
    # The refusal left the prior state.toml byte-for-byte intact.
    assert load_state(working / "state.toml").gates.knitting.done_80 is True, (
        "the refused recount must leave the prior gates intact"
    )


def test_rollback_clears_record_and_keeps_every_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rollback tree: reconcile exit 0, record cleared, no file removed, logged."""
    spec, _expected = wc.INCOHERENT_VARIANTS["pending-turn-rollback-unrecoverable"]
    working = wc.build_working_tree(spec, tmp_path)
    files_before = _present_files(working)
    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, "rollback must exit 0"
    assert _result(env)["action"] == "rollback-pending-turn", (
        "reconcile must report the rollback-pending-turn action"
    )
    assert load_state(working / "state.toml").pending_turn is None, (
        "the torn pending_turn record must be cleared"
    )
    assert files_before <= _present_files(working), (
        "rollback must remove no working/ file"
    )
    assert "rollback-pending-turn" in (working / "log.md").read_text(
        encoding="utf-8"
    ), "rollback must append a recovery entry to log.md"
    recheck_code, _recheck = _drive(working, "check", monkeypatch)
    assert recheck_code == ExitCode.SUCCESS, "the recovered tree must re-check clean"


def test_complete_clears_record_and_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete tree: reconcile exit 0, record cleared, logged, re-check clean."""
    spec, _expected = wc.INCOHERENT_VARIANTS["pending-turn-complete-recomputable"]
    working = wc.build_working_tree(spec, tmp_path)
    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, "complete must exit 0"
    assert _result(env)["action"] == "complete-pending-turn", (
        "reconcile must report the complete-pending-turn action"
    )
    assert load_state(working / "state.toml").pending_turn is None, (
        "the stale pending_turn marker must be cleared"
    )
    assert "complete-pending-turn" in (working / "log.md").read_text(
        encoding="utf-8"
    ), "complete must append a recovery entry to log.md"
    recheck_code, _recheck = _drive(working, "check", monkeypatch)
    assert recheck_code == ExitCode.SUCCESS, "the recovered tree must re-check clean"


def test_headline_variant_sole_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The headline variant's only corpus violation is ``word-counts-match-drafts``.

    The round-3 blocking-point-2 regression guard: the variant must not silently
    regress into a ``REFUSE`` tree (e.g. by inheriting a ``done.flag`` over the
    empty draft).
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    assert wc.corpus_check(spec, working) == ("word-counts-match-drafts",), (
        "the headline variant must break exactly word-counts-match-drafts"
    )
