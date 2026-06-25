"""Torn ``set-chapters`` turn recovery via ``reconcile`` (roadmap 2.2.3, Work item 3a).

These pin the scoped precedence change (Decision D8, ADR 008): a torn
``set-chapters`` turn — a populated ``[chapters]`` over a populated
``operation="set-chapters"`` ``[pending_turn]`` with one or more declared
``chapter-NN/`` directories still missing — is COMPLETEd by ``reconcile`` (which
creates the missing directories and clears the record) rather than REFUSEd at the
``manifest-disk-bijection`` arm, *but only* when the break is fully explained by
the pending turn's missing chapter directories. Any unexplained break still
REFUSEs.

The decisive case is the **partial-directory** torn turn (manifest ``{1,2,3}``,
on-disk ``{1}``): it fires the bijection refuse-class, so under the old precedence
it short-circuited to REFUSE before the pending-turn branch (round-2 B1). The
negative cases prove the exception is scoped: an orphan directory, a second
refuse-class violation, and a missing dir the turn does not declare each still
REFUSE.

Trees are built with the ``working_corpus`` spec/builder: ``manifest_only_numbers``
adds manifest entries with no on-disk directory (the missing chapter dirs) and
``pending_turn`` stamps the torn ``[pending_turn]`` record.
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import (
    ReconcileAction,
    chapter_dir_name,
    derive_reconciliation,
    load_state,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "novel-state"


def _chapter_path(number: int) -> str:
    """Return the ``working/``-rooted declared path for a chapter directory."""
    return f"working/manuscript/{chapter_dir_name(number)}"


class _TornOptions(typ.NamedTuple):
    """The optional knobs of :func:`_torn_spec`, bundled to keep its arity small.

    - ``orphan`` chapters have an on-disk directory but **no** manifest entry
      (``in_manifest=False``), modelling an unexplained orphan directory;
    - ``declared`` overrides the chapter numbers the ``[pending_turn]`` names
      (default: ``manifest_only``);
    - ``extra_chapter_kwargs`` applies per-number ``ChapterSpec`` overrides (e.g. an
      empty draft beside a ``done.flag`` for the second-refuse-class case).
    """

    orphan: tuple[int, ...] = ()
    declared: tuple[int, ...] | None = None
    extra_chapter_kwargs: cabc.Mapping[int, dict[str, object]] | None = None


_DEFAULT_TORN_OPTIONS = _TornOptions()


def _torn_spec(
    on_disk: cabc.Sequence[int],
    manifest_only: cabc.Sequence[int],
    options: _TornOptions = _DEFAULT_TORN_OPTIONS,
) -> wc.WorkingTreeSpec:
    """Build a torn ``set-chapters`` tree spec mirroring a real torn turn.

    A real ``set-chapters`` turn persists the manifest **and** a zero-seeded
    ``[word_counts].by_chapter`` covering every manifest chapter (Decision D13), so
    the fixture seeds the same: ``by_chapter_override`` carries one key per manifest
    chapter (the on-disk drafted ones plus a ``0`` for each missing-dir chapter), so
    the only outstanding divergence is the missing directories — not a stale word
    table. ``on_disk`` chapters are in ``[chapters]`` with an on-disk directory and a
    small draft; ``manifest_only`` chapters are in ``[chapters]`` with no directory
    (the declared-but-missing dirs); see :class:`_TornOptions` for the rest. The
    ``[pending_turn]`` declares ``working/state.toml`` plus each declared dir.
    """
    extra = options.extra_chapter_kwargs or {}

    def _chapter(number: int, *, in_manifest: bool) -> wc.ChapterSpec:
        """Return a small coherent ``ChapterSpec``, applying any per-number override."""
        fields: dict[str, object] = {
            "number": number,
            "slug": f"chapter-{number:02d}",
            "title": f"Chapter {number}",
            "target_words": 20000,
            "draft_words": 4,
            "has_done_flag": False,
            "in_manifest": in_manifest,
        }
        fields.update(extra.get(number, {}))
        return wc.ChapterSpec(**typ.cast("dict[str, typ.Any]", fields))

    on_disk_specs = [_chapter(number, in_manifest=True) for number in on_disk]
    chapters = (
        *on_disk_specs,
        *(_chapter(number, in_manifest=False) for number in options.orphan),
    )
    # by_chapter covers exactly the manifest chapters (on_disk drafted + missing-dir
    # zeros), as a real set-chapters turn would have seeded it. The on-disk entries
    # use each chapter's effective draft_words so a per-number override (e.g. an
    # empty draft beside a done.flag) does not also trip word-counts-match-drafts.
    by_chapter = {f"{spec.number:02d}": spec.draft_words for spec in on_disk_specs}
    by_chapter.update({f"{number:02d}": 0 for number in manifest_only})
    declared_numbers = manifest_only if options.declared is None else options.declared
    paths = [
        "working/state.toml",
        *(_chapter_path(number) for number in declared_numbers),
    ]
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=max([*on_disk, *manifest_only], default=0),
        manifest_only_numbers=tuple(manifest_only),
        by_chapter_override=by_chapter,
        current_words_override=sum(by_chapter.values()),
        pending_turn={"operation": "set-chapters", "paths": paths},
    )


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


def _action(working: Path) -> ReconcileAction:
    """Return the action ``derive_reconciliation`` implies for the built tree."""
    return derive_reconciliation(load_state(working / "state.toml"), working).action


def test_partial_directory_torn_turn_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest {1,2,3}, on-disk {1}: COMPLETE (not REFUSE), dirs created, re-check 0.

    The decisive round-2 B1 case: the partial-directory torn turn fires the
    bijection refuse-class, so it short-circuited to REFUSE under the old precedence.

    This is also the ADR 009 / D1 reconcile-regression guard: the torn tree carries
    ``phase=drafting``, exactly the phase the user-facing ``check`` now relaxes. The
    relaxation is a default-strict flag on ``check_disk_evidence`` that only
    ``check`` sets, so ``derive_reconciliation`` keeps reading the **strict**
    bijection and this turn still COMPLETEs. A regression that leaked the relaxation
    into reconcile would silently flip this COMPLETE into a REFUSE/NONE.
    """
    working = wc.build_working_tree(
        _torn_spec(on_disk=(1,), manifest_only=(2, 3)), tmp_path
    )
    assert _action(working) is ReconcileAction.COMPLETE_PENDING_TURN, (
        "an explained partial-directory torn set-chapters turn must COMPLETE"
    )

    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, "reconcile must COMPLETE the explained torn turn"
    result = typ.cast("dict[str, object]", env["result"])
    assert result["action"] == "complete-pending-turn", (
        "reconcile must report the complete-pending-turn action"
    )

    for number in (2, 3):
        directory = working / "manuscript" / chapter_dir_name(number)
        assert directory.is_dir(), f"{directory} must be created by reconcile"
    assert load_state(working / "state.toml").pending_turn is None, (
        "reconcile must clear the torn [pending_turn]"
    )
    assert "complete-pending-turn" in (working / "log.md").read_text(
        encoding="utf-8"
    ), "reconcile must append a complete-pending-turn receipt"

    recheck, _re = _drive(working, "check", monkeypatch)
    assert recheck == ExitCode.SUCCESS, "the completed tree must re-check clean"


def test_all_dirs_missing_torn_turn_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest {1,2}, on-disk {}: COMPLETE creates both directories, re-check 0."""
    working = wc.build_working_tree(
        _torn_spec(on_disk=(), manifest_only=(1, 2)), tmp_path
    )
    assert _action(working) is ReconcileAction.COMPLETE_PENDING_TURN, (
        "an all-dirs-missing torn set-chapters turn must COMPLETE"
    )

    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, "reconcile must COMPLETE the explained torn turn"
    assert typ.cast("dict[str, object]", env["result"])["action"] == (
        "complete-pending-turn"
    ), "reconcile must report the complete-pending-turn action"
    for number in (1, 2):
        assert (working / "manuscript" / chapter_dir_name(number)).is_dir(), (
            f"reconcile must create chapter-{number:02d}/"
        )
    recheck, _re = _drive(working, "check", monkeypatch)
    assert recheck == ExitCode.SUCCESS, "the completed tree must re-check clean"


def test_orphan_directory_still_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On-disk {1,2}+orphan {3}, manifest {1,2}: orphan dir unexplained → REFUSE."""
    working = wc.build_working_tree(
        _torn_spec(on_disk=(1, 2), manifest_only=(), options=_TornOptions(orphan=(3,))),
        tmp_path,
    )
    assert _action(working) is ReconcileAction.REFUSE, (
        "an orphan on-disk directory the manifest does not name must REFUSE"
    )
    code, _env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, (
        "an unexplained break must REFUSE with exit 4"
    )


def test_second_refuse_class_violation_still_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A done.flag over an empty draft adds a second contradiction → REFUSE.

    Chapter 1 is on disk with a ``done.flag`` over a zero-word draft (the
    ``done-flag-without-draft`` contradiction), so the fired refuse-class is more
    than ``{manifest-disk-bijection}`` and the scoped exception must not fire.
    """
    working = wc.build_working_tree(
        _torn_spec(
            on_disk=(1,),
            manifest_only=(2,),
            options=_TornOptions(
                extra_chapter_kwargs={
                    1: {"draft_words": 0, "write_draft": False, "has_done_flag": True}
                }
            ),
        ),
        tmp_path,
    )
    assert _action(working) is ReconcileAction.REFUSE, (
        "a second refuse-class violation must defeat the scoped exception"
    )
    code, _env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, (
        "an unexplained break must REFUSE with exit 4"
    )


def test_undeclared_missing_dir_still_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing dir the pending turn does not declare is unexplained → REFUSE.

    Manifest {1,2,3}, on-disk {1}, but the pending turn declares only chapter-02,
    so chapter-03 is missing yet undeclared: the break is not fully explained.
    """
    working = wc.build_working_tree(
        _torn_spec(
            on_disk=(1,),
            manifest_only=(2, 3),
            options=_TornOptions(declared=(2,)),
        ),
        tmp_path,
    )
    assert _action(working) is ReconcileAction.REFUSE, (
        "a missing dir the pending turn does not declare must REFUSE"
    )
    code, _env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, (
        "an unexplained break must REFUSE with exit 4"
    )


def test_reconcile_turn_regression_unaffected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A torn ``reconcile`` turn (the [word_counts] case) is unaffected by WI3a."""
    spec, _expected = wc.INCOHERENT_VARIANTS["pending-turn-complete-recomputable"]
    working = wc.build_working_tree(spec, tmp_path)
    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.SUCCESS, "a torn reconcile turn must still COMPLETE"
    assert typ.cast("dict[str, object]", env["result"])["action"] == (
        "complete-pending-turn"
    ), "the reconcile-turn regression must report complete-pending-turn"
    assert load_state(working / "state.toml").pending_turn is None, (
        "reconcile must clear the torn reconcile [pending_turn]"
    )
