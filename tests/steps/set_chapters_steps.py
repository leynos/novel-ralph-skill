"""Step definitions for the ``set-chapters`` behavioural scenarios.

These drive the ``set-chapters`` mutator (and ``check``/``reconcile`` where the
scenario follows up) through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, so the externally
observable exit code is what each scenario asserts (roadmap task 2.2.3; design
§4.1, §5.1, §5.2, §5.4; ADR 008). Fixture state — the built ``working/`` path, the
captured exit code, and the pre-run ``state.toml`` bytes for the refusal scenarios
— flows between steps through ``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_set_chapters_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, parsers, then, when

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "novel-state"
_COHERENT_PLAN = (
    '[{"number": 1, "slug": "the-summons", "title": "The Summons", '
    '"target_words": 3200}, '
    '{"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800}]'
)
_NON_CONTIGUOUS_PLAN = (
    '[{"number": 1, "slug": "a", "title": "A", "target_words": 10}, '
    '{"number": 3, "slug": "c", "title": "C", "target_words": 30}]'
)
_DUPLICATE_NUMBER_PLAN = (
    '[{"number": 1, "slug": "a", "title": "A", "target_words": 10}, '
    '{"number": 1, "slug": "b", "title": "B", "target_words": 20}]'
)


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree, the pre-run bytes, and the exit codes across the steps."""

    working: Path
    before: bytes
    exit_code: int | None = None


def _run(working: Path, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``argv`` through ``run`` from ``working.parent``; return the exit code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


def _build(working: Path) -> _Outcome:
    """Return an ``_Outcome`` carrying the tree and its current ``state.toml`` bytes."""
    return _Outcome(working=working, before=(working / "state.toml").read_bytes())


@given("an initialised tree with an empty chapter manifest", target_fixture="outcome")
def empty_manifest_tree(tmp_path: Path) -> _Outcome:
    """Build a ``chapter-planning`` tree whose ``[chapters]`` is empty."""
    return _build(wc.build_working_tree(wc.PHASE_STATES["chapter-planning"], tmp_path))


@given("a tree whose chapter manifest is already populated", target_fixture="outcome")
def populated_manifest_tree(tmp_path: Path) -> _Outcome:
    """Build a ``drafting`` tree whose ``[chapters]`` already carries chapters."""
    return _build(wc.build_working_tree(wc.PHASE_STATES["drafting"], tmp_path))


def _torn_chapter(number: int, *, on_disk: bool) -> wc.ChapterSpec:
    """Return a manifest chapter; ``on_disk=False`` makes it manifest-only."""
    return wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=20000,
        draft_words=4 if on_disk else 0,
        has_done_flag=False,
        in_manifest=on_disk,
    )


@given(
    "a torn set-chapters turn with three planned chapters and only chapter-01 on disk",
    target_fixture="outcome",
)
def torn_set_chapters_tree(tmp_path: Path) -> _Outcome:
    """Build a partial-directory torn ``set-chapters`` turn (manifest 1-3, disk 1).

    Mirrors a real torn turn: ``[chapters]`` carries all three, ``by_chapter`` is
    zero-seeded per chapter (as ``set-chapters`` writes it), and the
    ``operation="set-chapters"`` ``[pending_turn]`` declares the two missing
    directories. Only ``chapter-01/`` is on disk, so ``manifest-disk-bijection``
    fires — the case that REFUSEs under the old precedence (round-2 B1).
    """
    by_chapter: cabc.Mapping[str, int] = {"01": 4, "02": 0, "03": 0}
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=(_torn_chapter(1, on_disk=True),),
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=3,
        manifest_only_numbers=(2, 3),
        by_chapter_override=by_chapter,
        current_words_override=4,
        pending_turn={
            "operation": "set-chapters",
            "paths": [
                "working/state.toml",
                "working/manuscript/chapter-02",
                "working/manuscript/chapter-03",
            ],
        },
    )
    return _build(wc.build_working_tree(spec, tmp_path))


@when("set-chapters runs with a coherent two-chapter plan")
def run_coherent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``set-chapters`` with the coherent plan."""
    outcome.exit_code = _run(
        outcome.working, ["set-chapters", "--chapters", _COHERENT_PLAN], monkeypatch
    )


@when("set-chapters runs with a non-contiguous plan")
def run_non_contiguous(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``set-chapters`` with a plan whose numbers skip 2."""
    outcome.exit_code = _run(
        outcome.working,
        ["set-chapters", "--chapters", _NON_CONTIGUOUS_PLAN],
        monkeypatch,
    )


@when("set-chapters runs with a duplicate-number plan")
def run_duplicate(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``set-chapters`` with a plan that repeats chapter number 1."""
    outcome.exit_code = _run(
        outcome.working,
        ["set-chapters", "--chapters", _DUPLICATE_NUMBER_PLAN],
        monkeypatch,
    )


@when("check runs against the torn tree")
def run_check_torn(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``check`` against the torn tree and capture its exit code."""
    outcome.exit_code = _run(outcome.working, ["check"], monkeypatch)


@when("reconcile runs against the torn tree")
def run_reconcile_torn(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``reconcile`` against the torn tree and capture its exit code."""
    outcome.exit_code = _run(outcome.working, ["reconcile"], monkeypatch)


@then(parsers.parse("set-chapters exits {code:d}"))
def assert_set_chapters_exit(outcome: _Outcome, code: int) -> None:
    """Assert ``set-chapters`` exited with ``code``."""
    assert outcome.exit_code == code, f"expected exit {code}, got {outcome.exit_code}"


@then(parsers.parse("check exits {code:d}"))
def assert_check_exit(outcome: _Outcome, code: int) -> None:
    """Assert the captured ``check`` exit code is ``code``."""
    assert outcome.exit_code == code, (
        f"expected check exit {code}, got {outcome.exit_code}"
    )


@then(parsers.parse("reconcile exits {code:d}"))
def assert_reconcile_exit(outcome: _Outcome, code: int) -> None:
    """Assert the captured ``reconcile`` exit code is ``code``."""
    assert outcome.exit_code == code, (
        f"expected reconcile exit {code}, got {outcome.exit_code}"
    )


@then("state.toml records the two planned chapters in ascending order")
def assert_manifest(outcome: _Outcome) -> None:
    """Assert ``[chapters]`` holds the two planned chapters, numbers 1 then 2."""
    from novel_ralph_skill.state import document_to_state, load_document

    state = document_to_state(load_document(outcome.working / "state.toml"))
    assert [chapter.number for chapter in state.chapters] == [1, 2], (
        "set-chapters must write the ascending two-chapter manifest"
    )


@then(parsers.parse("the chapter directories {first} and {second} exist"))
def assert_chapter_dirs(outcome: _Outcome, first: str, second: str) -> None:
    """Assert both named ``chapter-NN`` directories exist on disk."""
    manuscript = outcome.working / "manuscript"
    for name in (first, second):
        assert (manuscript / name).is_dir(), f"{name} must exist"


@then("a follow-up check exits 0")
def assert_follow_up_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a subsequent ``check`` exits 0 (the tree is coherent)."""
    code = _run(outcome.working, ["check"], monkeypatch)
    assert code == ExitCode.SUCCESS, f"the follow-up check must exit 0, got {code}"


@then("state.toml is byte-for-byte unchanged")
def assert_unchanged(outcome: _Outcome) -> None:
    """Assert a refused command left ``state.toml`` byte-for-byte intact."""
    after = (outcome.working / "state.toml").read_bytes()
    assert after == outcome.before, (
        "a refused set-chapters must leave state.toml intact"
    )
