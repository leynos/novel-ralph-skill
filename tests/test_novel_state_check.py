"""Behavioural and end-to-end tests for ``novel-state check`` (roadmap 2.1.2).

These pin the externally observable contract of the read-only ``check``
subcommand (design §4.1, §3.1-§3.4; ADR-003 §3.1): a coherent ``working/`` tree
exits ``0`` with an ``ok: true`` envelope and an empty ``result.violations``; an
incoherent tree exits ``4`` (``ACTIONABLE_FINDING``) naming the breached
invariants; a missing or unparseable ``state.toml`` exits ``3`` (state error);
and ``--help``/``--version`` exit ``0`` with no envelope. They also pin the
global-flag convention (the entry point pre-parses ``--human`` before ``run``;
the ``run``-driven cases inject the synthetic ``working_dir="working"`` label to
pin envelope *shape*, while the real ``novel.main()`` entry point stamps the
*absolute resolved* ``working/`` path so a misresolution is visible, roadmap
§6.3.4; Decision Log B3/B4), the ``parse_global_flags`` splitter, the
checker/mutator segregation
(``check`` writes nothing; design §3.3), and the installed-script e2e.

The command is driven both through :func:`novel_ralph_skill.contract.runner.run`
(mirroring ``test_contract_runner.py`` and the ``wrapper_app`` fixture) and
through the real ``novel.main()`` entry point, the latter always under an
explicit ``monkeypatch.chdir`` into a materialised fixture parent so the default
``./working/`` resolves there and never depends on the ambient cwd (advisory A6).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import typing as typ

import pytest
from cross_command_contract import ENVELOPE_KEY_ORDER
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

from novel_ralph_skill.commands import novel
from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract import parse_global_flags
from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec
    from cuprum import ProgramCatalogue

_COMMAND = "novel state"
_ENVELOPE_FIELDS = frozenset(
    {"command", "schema_version", "ok", "working_dir", "result", "messages"},
)


def _run_check(
    argv: list[str],
    *,
    human: bool = False,
) -> None:
    """Drive the ``novel-state`` app over ``argv`` through :func:`run`."""
    run(
        build_app(),
        argv,
        RunContext(command=_COMMAND, working_dir="working", human=human),
    )


def _capture_envelope(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    """Return the JSON envelope ``run`` emitted to stdout."""
    return json.loads(capsys.readouterr().out)


def test_check_coherent_tree_exits_zero(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A coherent ``./working/`` exits ``0`` with ``ok: true`` and no violations."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run_check(["check"])
    assert excinfo.value.code == ExitCode.SUCCESS
    envelope = _capture_envelope(capsys)
    assert envelope["ok"] is True
    assert typ.cast("dict[str, object]", envelope["result"])["violations"] == []


def test_check_missing_working_dir_exits_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A cwd with no ``./working/`` exits ``3`` (state error) with ``ok: false``."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        _run_check(["check"])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert _capture_envelope(capsys)["ok"] is False


def test_check_unparseable_state_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unparseable ``./working/state.toml`` exits ``3`` (state error)."""
    working = baseline_tree()
    (working / "state.toml").write_text("not = toml =", encoding="utf-8")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run_check(["check"])
    assert excinfo.value.code == ExitCode.STATE_ERROR
    assert _capture_envelope(capsys)["ok"] is False


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_check_meta_flags_exit_zero_without_envelope(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state --help``/``--version`` exit ``0`` with no envelope."""
    with pytest.raises(SystemExit) as excinfo:
        _run_check([flag])
    assert excinfo.value.code == ExitCode.SUCCESS
    # The run exemption: Cyclopts prints help/version and returns a
    # non-CommandOutcome, so run emits no envelope (no JSON object on stdout).
    assert "command" not in capsys.readouterr().out


def test_check_envelope_shape(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The envelope carries the fixed field set, command, and ``working_dir``."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit):
        _run_check(["check"])
    envelope = _capture_envelope(capsys)
    assert frozenset(envelope) == _ENVELOPE_FIELDS
    assert envelope["command"] == _COMMAND
    assert envelope["working_dir"] == "working"


def test_check_writes_nothing(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``check`` is a checker: the ``working/`` tree is byte-for-byte unchanged."""
    working = baseline_tree()
    before = {
        path: path.read_bytes() for path in sorted(working.rglob("*")) if path.is_file()
    }
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit):
        _run_check(["check"])
    after = {
        path: path.read_bytes() for path in sorted(working.rglob("*")) if path.is_file()
    }
    assert after == before


def test_check_incoherent_tree_exits_four(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An incoherent tree exits ``4`` naming the breached invariant."""
    _spec, working, expected = incoherent_tree("consecutive-clean-over-target")
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run_check(["check"])
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    envelope = _capture_envelope(capsys)
    assert envelope["ok"] is False
    violations = typ.cast("dict[str, object]", envelope["result"])["violations"]
    assert expected in typ.cast("list[str]", violations)


# --- The global-flag convention, driven through the real entry point (B3/B4) ---


def _drive_entry_point(
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run ``novel.main()`` with ``argv`` patched into ``sys.argv``."""
    monkeypatch.setattr(sys, "argv", [*_COMMAND.split(), *argv])
    novel.main()


def test_entry_point_human_flag_switches_rendering(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``novel-state --human check`` renders human output at exit ``0`` (B3)."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _drive_entry_point(["--human", "check"], monkeypatch)
    assert excinfo.value.code == ExitCode.SUCCESS
    out = capsys.readouterr().out
    # The human rendering is line-oriented prose, not a JSON object. The real
    # entry point stamps the absolute resolved ``working/`` path (roadmap 6.3.4).
    assert "command: novel state" in out
    expected_working_dir = str((working.parent / "working").resolve())
    assert f"working_dir: {expected_working_dir}" in out
    assert not out.lstrip().startswith("{")


def test_entry_point_usage_error_carries_working_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A usage error exits ``2`` carrying the absolute ``working_dir`` (B3/B4).

    Proves the entry point built the ``RunContext`` (stamping the absolute
    resolved ``working/`` path, roadmap 6.3.4) before ``run`` reached the
    body-less usage path.
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        _drive_entry_point(["bogus"], monkeypatch)
    assert excinfo.value.code == ExitCode.USAGE_ERROR
    envelope = _capture_envelope(capsys)
    assert envelope["ok"] is False
    assert envelope["working_dir"] == str((tmp_path / "working").resolve())


def test_entry_point_human_strip_still_drives_subcommand(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The residual argv after the ``--human`` strip still reaches ``check``."""
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _drive_entry_point(["--human", "check"], monkeypatch)
    # Reaching the check body (not a usage error) proves the strip left "check".
    assert excinfo.value.code == ExitCode.SUCCESS


def test_entry_point_exit_code_governed_by_chdir(
    baseline_tree: cabc.Callable[[], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The real callable's exit code follows the chdir'd ``working/`` (A6).

    Run once where ``./working/`` exists (exit ``0``) and once where it does not
    (exit ``3``), proving the invocation root never perturbs the verdict.
    """
    working = baseline_tree()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as ok_exit:
        _drive_entry_point(["check"], monkeypatch)
    assert ok_exit.value.code == ExitCode.SUCCESS
    capsys.readouterr()

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(SystemExit) as state_exit:
        _drive_entry_point(["check"], monkeypatch)
    assert state_exit.value.code == ExitCode.STATE_ERROR


# --- ``parse_global_flags`` unit tests ---


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--human", "check"], (True, ["check"])),
        (["check", "--human"], (True, ["check"])),
        (["check", "--human", "extra"], (True, ["check", "extra"])),
        (["check"], (False, ["check"])),
        (["--human", "check", "--human"], (True, ["check"])),
        (["check", "--foo"], (False, ["check", "--foo"])),
    ],
    ids=[
        "leading",
        "trailing",
        "between",
        "absent",
        "multiple",
        "other-flag-untouched",
    ],
)
def test_parse_global_flags(
    argv: list[str],
    expected: tuple[bool, list[str]],
) -> None:
    """``--human`` is recognised in any position and removed; others survive."""
    assert parse_global_flags(argv) == expected


# --- The installed-script e2e (Decision Log B6) ---


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_installed_novel_state_check_exits_zero(
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    installed_novel_state: Path,
) -> None:
    """Build, install, and run ``novel-state check`` against a coherent tree.

    The installed script runs with cuprum's ``ExecutionContext(cwd=dest)`` so it
    resolves ``./working/state.toml`` and exits ``0`` with ``ok: true``. The
    ``installed_novel_state`` fixture supplies the built-and-installed script path
    (built once per module). The 180s timeout supersedes the 30s project default
    (pyproject ``timeout = 30``).

    Beyond exit ``0`` and ``ok: true``, this is the installed-boundary success-arm
    *skeleton-identity* tripwire (roadmap 6.3.6): it pins the full exit-0 envelope
    skeleton over the wheel — the six contract keys in ``ENVELOPE_KEY_ORDER``,
    ``schema_version``, ``command == "novel state"`` (a member of
    ``ENVELOPE_COMMAND_NAMES``), the ``ok``-iff-exit-0 mapping, the
    resolved-absolute ``working_dir``, ``result["violations"] == []``, and
    ``str``-typed ``messages`` — against the same constants the in-process
    cross-command suite (``tests/cross_command_contract/``) uses, so the installed
    surface cannot silently diverge from the in-process contract pinned by 6.3.2.
    """
    dest = tmp_path / "run"
    dest.mkdir()
    # Materialise a coherent ``dest/working/`` for the subprocess cwd to resolve,
    # copied from the already-built baseline tree (the corpus fixtures build it
    # under the test's ``tmp_path``).
    shutil.copytree(baseline_tree(), dest / "working")

    prog = Program(str(installed_novel_state))
    catalogue = single_program_catalogue("novel-state-run", prog)
    result = sh.make(prog, catalogue=catalogue)("state", "check").run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert result.exit_code == 0, result.stderr
    # A clean run yields a message, not a stack trace (design §10).
    assert "Traceback" not in (result.stderr or "")
    envelope = json.loads(result.stdout or "{}")
    assert envelope["ok"] is True
    # The full exit-0 envelope-skeleton identity, observed over the wheel: the
    # six contract keys in the order ``render_machine`` emits them, the same
    # ``ENVELOPE_KEY_ORDER`` the in-process cross-command suite pins (6.3.2).
    assert tuple(envelope) == ENVELOPE_KEY_ORDER
    assert envelope["command"] == _COMMAND
    assert envelope["command"] in ENVELOPE_COMMAND_NAMES
    assert envelope["schema_version"] == ENVELOPE_SCHEMA_VERSION
    # ``ok`` is true iff the exit code is success (design §3.1), here over the
    # installed surface.
    assert envelope["ok"] is (result.exit_code == ExitCode.SUCCESS)
    # The installed binary stamps the resolved-absolute ``working_dir`` (roadmap
    # 6.3.4), not the ``"working"`` token the in-process suite asserts; compute
    # the expected value the production way from ``dest`` so symlink
    # normalisation under ``tmp_path`` cannot desynchronise the two sides.
    assert envelope["working_dir"] == str((dest / "working").resolve())
    # The checker's coherent-tree body payload: an empty ``violations`` list, the
    # installed mirror of ``test_check_coherent_tree_exits_zero``.
    assert isinstance(envelope["result"], dict)
    assert envelope["result"]["violations"] == []
    assert isinstance(envelope["messages"], list)
    assert all(isinstance(message, str) for message in envelope["messages"])
