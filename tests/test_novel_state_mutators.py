"""Command-contract tests for the ``novel-state`` mutators (roadmap 2.2.2).

These pin the externally observable contract of the three state-mutating
subcommands — ``init``, ``set-cursor``, and ``advance-phase`` (design §4.1,
§3.2, §5.2) — that the spine has so far left unregistered. Each mutator *writes*
``state.toml`` through the ``tomlkit`` round-trip plus atomic write (task 2.2.1),
validates the proposed state against the §5.2 invariants before persisting, and
refuses an incoherent transition with exit ``3`` (``STATE_ERROR``) — never the
benign exit ``1`` the loop continues on (design §3.2 lines 199-205; ADR-003
§3.2).

The tests mirror ``tests/test_novel_state_check.py``: a ``_run_mutator`` helper
drives the app through :func:`novel_ralph_skill.contract.runner.run` with a
``RunContext(command="novel state", working_dir="working", …)``, and a
``_capture_envelope`` reads the JSON envelope from ``capsys``. All three mutators
are registered, so every test here is active (the bodies were marked
``xfail(strict=True)`` only while their subcommand was still pending in work
items 2-4).
"""

from __future__ import annotations

import json
import typing as typ

import pytest

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec

_COMMAND = "novel state"


def _run_mutator(argv: list[str], *, human: bool = False) -> None:
    """Drive the ``novel-state`` app over ``argv`` through :func:`run`."""
    run(
        build_app(),
        argv,
        RunContext(command=_COMMAND, working_dir="working", human=human),
    )


def _capture_envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """Return the JSON envelope ``run`` emitted to stdout."""
    return json.loads(capsys.readouterr().out)


def _drive_and_capture(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object]]:
    """Run ``argv`` and return ``(exit_code, envelope)``."""
    with pytest.raises(SystemExit) as excinfo:
        _run_mutator(argv)
    code = typ.cast("int", excinfo.value.code)
    return code, _capture_envelope(capsys)


# --- ``init`` -----------------------------------------------------------------


def test_init_bootstraps_coherent_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``init`` creates a coherent ``working/`` that ``check`` accepts."""
    monkeypatch.chdir(tmp_path)
    code, _ = _drive_and_capture(
        ["init", "--title", "T", "--slug", "s", "--target-word-count", "80000"],
        capsys,
    )
    assert code == ExitCode.SUCCESS
    state_path = tmp_path / "working" / "state.toml"
    assert state_path.exists()
    # A follow-up ``check`` accepts the freshly initialised tree.
    check_code, check_env = _drive_and_capture(["check"], capsys)
    assert check_code == ExitCode.SUCCESS
    assert check_env["ok"] is True


def test_init_writes_premise_phase_and_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The initial state names ``premise``, an empty manifest, and the target."""
    import tomllib

    monkeypatch.chdir(tmp_path)
    code, _ = _drive_and_capture(
        ["init", "--title", "T", "--slug", "s", "--target-word-count", "80000"],
        capsys,
    )
    assert code == ExitCode.SUCCESS
    raw = tomllib.loads((tmp_path / "working" / "state.toml").read_text("utf-8"))
    assert raw["phase"]["current"] == "premise"
    assert raw["phase"]["completed"] == []
    assert raw["chapters"] == []
    assert raw["novel"]["target_word_count"] == 80000


def test_init_refuses_existing_state(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``init`` refuses (exit ``3``) when ``working/state.toml`` already exists."""
    working = baseline_tree()
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, envelope = _drive_and_capture(["init", "--title", "T", "--slug", "s"], capsys)
    assert code == ExitCode.STATE_ERROR
    assert envelope["ok"] is False
    assert (working / "state.toml").read_bytes() == before


def test_init_creates_directory_skeleton_and_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``init`` creates the six Initialisation subdirectories and ``log.md``."""
    monkeypatch.chdir(tmp_path)
    code, _ = _drive_and_capture(["init", "--title", "T", "--slug", "s"], capsys)
    assert code == ExitCode.SUCCESS
    working = tmp_path / "working"
    skeleton = ("characters", "world", "reader", "plan", "manuscript", "reviews")
    for name in skeleton:
        assert (working / name).is_dir(), f"{name} subdirectory missing"
    assert (working / "log.md").exists()


# --- ``set-cursor`` -----------------------------------------------------------


def test_set_cursor_success(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An in-range cursor move exits ``0`` and ``check`` still accepts the tree."""
    working = phase_state_tree("drafting")
    monkeypatch.chdir(working.parent)
    # ``chapter=2`` is within ``1..len(chapters)`` for the three-chapter drafting
    # tree; scene/beat stay at their valid defaults (AR2-2).
    code, envelope = _drive_and_capture(
        ["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"], capsys
    )
    assert code == ExitCode.SUCCESS
    # The write-shaped success ``result`` names the cursor it set, not the
    # checker's ``violations`` read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"current_chapter": 2, "current_scene": 0, "current_beat": 0}
    assert "violations" not in result
    check_code, _ = _drive_and_capture(["check"], capsys)
    assert check_code == ExitCode.SUCCESS
    import tomllib

    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    assert raw["drafting"]["current_chapter"] == 2


def test_set_cursor_refuses_chapter_past_manifest(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A chapter past the manifest exits ``3``, names ``cursor-coherent``, no write."""
    working = phase_state_tree("drafting")
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, envelope = _drive_and_capture(["set-cursor", "--chapter", "99"], capsys)
    assert code == ExitCode.STATE_ERROR
    # The exit-3 channel carries the breached invariant name in ``messages``
    # (the ``run`` StateInputError arm emits no ``result``).
    messages = typ.cast("list[str]", envelope["messages"])
    assert any("cursor-coherent" in message for message in messages)
    assert (working / "state.toml").read_bytes() == before


def test_set_cursor_refuses_scene_without_chapter(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A scene set while ``chapter == 0`` exits ``3`` and leaves state intact."""
    working = phase_state_tree("drafting")
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, _ = _drive_and_capture(
        ["set-cursor", "--chapter", "0", "--scene", "1"], capsys
    )
    assert code == ExitCode.STATE_ERROR
    assert (working / "state.toml").read_bytes() == before


# --- ``advance-phase`` --------------------------------------------------------


def test_advance_phase_success_pre_drafting(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Advancing a coherent pre-drafting phase marches forward; ``check`` accepts."""
    working = phase_state_tree("premise")
    monkeypatch.chdir(working.parent)
    code, envelope = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.SUCCESS
    # The write-shaped success ``result`` names the transition it made, not the
    # checker's ``violations`` read shape (roadmap 1.3.5; audit-2.2.2 Finding 2).
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"from": "premise", "to": "treatment"}
    assert "violations" not in result
    import tomllib

    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    assert raw["phase"]["current"] == "treatment"
    assert raw["phase"]["completed"] == ["premise"]
    check_code, _ = _drive_and_capture(["check"], capsys)
    assert check_code == ExitCode.SUCCESS


def test_advance_phase_success_into_drafting(
    populated_chapter_planning_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Advancing into ``drafting`` with a populated manifest exits ``0``."""
    working = populated_chapter_planning_tree()
    monkeypatch.chdir(working.parent)
    code, envelope = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.SUCCESS
    result = typ.cast("dict[str, object]", envelope["result"])
    assert result == {"from": "chapter-planning", "to": "drafting"}
    assert "violations" not in result
    check_code, _ = _drive_and_capture(["check"], capsys)
    assert check_code == ExitCode.SUCCESS


def test_advance_phase_persists_phase_not_transition_labels(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The on-disk write records ``phase``, never the ``from``/``to`` labels.

    The ``{from, to}`` keys are *transition labels* the envelope reports, not
    on-disk schema keys (design §3.1; developers-guide "State mutators"). This
    proves that intent against the written ``state.toml``, not just in prose:
    after a successful advance, ``[phase].current`` and ``[phase].completed``
    are updated and no ``from``/``to`` key was persisted anywhere — at the top
    level or inside any table (roadmap 1.3.5.2; audit:1.3.5).
    """
    working = phase_state_tree("premise")
    monkeypatch.chdir(working.parent)
    code, _ = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.SUCCESS

    import tomllib

    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    # The persisted representation of the transition is the phase table.
    assert raw["phase"]["current"] == "treatment"
    assert raw["phase"]["completed"] == ["premise"]
    # The transition labels never reach disk: not at the top level, and not
    # inside any persisted table.
    assert "from" not in raw
    assert "to" not in raw
    for table_name, table in raw.items():
        if isinstance(table, dict):
            assert "from" not in table, f"unexpected 'from' key in [{table_name}]"
            assert "to" not in table, f"unexpected 'to' key in [{table_name}]"


def test_advance_phase_refuses_out_of_order(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An out-of-order prior state refuses with exit ``3`` and writes nothing."""
    _spec, working, _expected = incoherent_tree("completed-prefix-gap")
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, _ = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.STATE_ERROR
    assert (working / "state.toml").read_bytes() == before


def test_advance_phase_refuses_from_done(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Advancing from the terminal ``done`` phase exits ``3``."""
    working = phase_state_tree("done")
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, _ = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.STATE_ERROR
    assert (working / "state.toml").read_bytes() == before


def test_advance_phase_refuses_empty_manifest_into_drafting(
    phase_state_tree: cabc.Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Advancing into ``drafting`` from an empty manifest exits ``3``."""
    working = phase_state_tree("chapter-planning")
    before = (working / "state.toml").read_bytes()
    monkeypatch.chdir(working.parent)
    code, _ = _drive_and_capture(["advance-phase"], capsys)
    assert code == ExitCode.STATE_ERROR
    assert (working / "state.toml").read_bytes() == before


# --- Missing / unparseable / structurally-incomplete state --------------------


@pytest.mark.parametrize(
    "command",
    [["set-cursor", "--chapter", "1"], ["advance-phase"]],
    ids=["set-cursor", "advance-phase"],
)
class TestMutatorLoadFaults:
    """Both stateful mutators map every load fault to exit ``3``."""

    def test_missing_state_exits_three(
        self,
        command: list[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A cwd with no ``working/state.toml`` exits ``3``."""
        monkeypatch.chdir(tmp_path)
        code, _ = _drive_and_capture(command, capsys)
        assert code == ExitCode.STATE_ERROR

    def test_unparseable_state_exits_three(
        self,
        command: list[str],
        baseline_tree: cabc.Callable[[], Path],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An unparseable ``working/state.toml`` exits ``3``."""
        working = baseline_tree()
        (working / "state.toml").write_text("not = toml =", encoding="utf-8")
        monkeypatch.chdir(working.parent)
        code, _ = _drive_and_capture(command, capsys)
        assert code == ExitCode.STATE_ERROR

    def test_structurally_incomplete_state_exits_three(
        self,
        command: list[str],
        baseline_tree: cabc.Callable[[], Path],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        r"""Valid TOML missing required tables exits ``3``, never ``1`` (BR2-1).

        ``"schema_version = 1\n"`` parses cleanly under ``load_document`` but is
        rejected by ``document_to_state`` -> ``parse_state`` (``NonExistentKey``).
        Routing that fault through ``_state_view_or_state_error`` keeps it on the
        exit-``3`` channel; an unwrapped fault would exit ``1`` (Tolerance
        "Refusal-code regression").
        """
        working = baseline_tree()
        (working / "state.toml").write_text("schema_version = 1\n", encoding="utf-8")
        monkeypatch.chdir(working.parent)
        code, _ = _drive_and_capture(command, capsys)
        assert code == ExitCode.STATE_ERROR
