"""End-to-end proof of the mid-draft cover-gap repair path (roadmap 2.3.8).

The user-visible Purpose scenario, driven through the fast entry point
(``novel.main()`` via ``sys.argv`` + ``SystemExit``, the installed console-script
body): a relaxed drafting subset (manifest ``{1,2,3}``, on-disk ``{1,2}``, phase
``drafting``) whose ``[word_counts].by_chapter`` omits the drafted ``"02"`` key
exits ``4`` on ``word-counts-cover-drafts`` (not ``manifest-disk-bijection`` — the
relaxed ``check`` suppresses it) with a ``recount`` reconciliation (Decision D7);
``reconcile`` re-keys ``by_chapter`` off the manifest (exit ``0``); and a
re-``check`` exits ``0``.

The fast path needs no cuprum (Decision D5); the slow installed-binary variant is
deliberately omitted because the fast path already proves the behaviour and the
sibling slow e2es use the broken ``capture=True`` idiom under the locked cuprum
0.1.0 (Decision D5). The corpus spec library is taken by the sanctioned
``working_corpus as wc`` value import.
"""

from __future__ import annotations

import dataclasses as dc
import json
import sys
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import novel
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel state"


def _relaxed_subset_cover_gap_spec() -> wc.WorkingTreeSpec:
    """Return a relaxed drafting subset whose by_chapter omits a drafted key.

    Manifest ``{1,2,3}``, on-disk ``{1,2}`` (chapter 3 is a real planned manifest
    entry with no directory), phase ``drafting``, with the drafted ``"02"`` key
    dropped from ``[word_counts].by_chapter``. The user-facing relaxed ``check``
    suppresses the missing-directory bijection break and fires
    ``word-counts-cover-drafts`` instead (roadmap task 2.3.8).
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


def test_entry_point_relaxed_subset_cover_gap_repaired_then_check_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A mid-draft cover gap exits 4, RECOUNTs, then re-checks clean (roadmap 2.3.8).

    The user-visible proof of the Purpose scenario: a relaxed drafting subset
    (manifest ``{1,2,3}``, on-disk ``{1,2}``, phase drafting) whose ``by_chapter``
    omits the drafted ``"02"`` key exits ``4`` on ``word-counts-cover-drafts`` —
    NOT on ``manifest-disk-bijection`` (the relaxed ``check`` suppresses it) — and
    reports a ``recount`` reconciliation (pinning Decision D7: ``check``'s reported
    action matches the repair ``reconcile`` enacts, not ``refuse``). ``reconcile``
    then re-keys ``by_chapter`` off the manifest (exit ``0``, action ``recount``,
    supplying the missing drafted key and the ``0`` undrafted key), and a
    re-``check`` exits ``0``.
    """
    working = wc.build_working_tree(_relaxed_subset_cover_gap_spec(), tmp_path)
    monkeypatch.chdir(working.parent)

    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "check"])
    with pytest.raises(SystemExit) as check_before:
        novel.main()
    assert check_before.value.code == ExitCode.ACTIONABLE_FINDING, (
        "the relaxed check must exit 4 on the mid-draft cover gap"
    )
    before_env = json.loads(capsys.readouterr().out)
    before_result = typ.cast("dict[str, object]", before_env["result"])
    violations = typ.cast("list[str]", before_result["violations"])
    assert "word-counts-cover-drafts" in violations, (
        "the cover gap must surface word-counts-cover-drafts"
    )
    assert "manifest-disk-bijection" not in violations, (
        "the relaxed check must suppress the missing-directory bijection break"
    )
    reconciliation = typ.cast("dict[str, object]", before_result["reconciliation"])
    assert reconciliation["action"] == "recount", (
        "check must report a recount reconciliation, not refuse (D7)"
    )

    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "reconcile"])
    with pytest.raises(SystemExit) as reconcile_exit:
        novel.main()
    assert reconcile_exit.value.code == ExitCode.SUCCESS, (
        "reconcile must exit 0 after repairing the cover gap"
    )
    reconcile_result = typ.cast(
        "dict[str, object]", json.loads(capsys.readouterr().out)["result"]
    )
    assert reconcile_result["action"] == "recount", "reconcile must enact a recount"
    assert reconcile_result["by_chapter"] == {"01": 100, "02": 100, "03": 0}, (
        "reconcile must re-key off the manifest, supplying the missing drafted key"
    )

    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), "check"])
    with pytest.raises(SystemExit) as check_after:
        novel.main()
    assert check_after.value.code == ExitCode.SUCCESS, (
        "the re-check must exit 0 once by_chapter is re-keyed"
    )
