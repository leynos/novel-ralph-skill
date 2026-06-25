"""Behavioural dispatch tests for the ``novel`` multiplexer (roadmap 1.2.12).

ADR 007 makes ``novel`` a pure dispatch layer over the five existing operations.
This module is the in-process proof that the dispatcher changes no behaviour:
every operation is driven through the multiplexer and through its legacy entry
point over the *same* corpus tree, and the two envelopes and exit codes are
asserted **equal** modulo the ``command`` field (the multiplexer stamps the
spaced ``"novel done"`` while the legacy path stamps ``"novel-done"`` — Decision
Log D1). Every exit arm is covered: exit 0 success, exit 1 benign negative, exit
4 actionable finding, exit 2 usage error, exit 3 state/input error, and the
help/version/bare arms that emit no envelope.

The unit shape tests live in ``tests/test_multiplexer_dispatch.py``; the shared
``driver`` fixture and the five-operation registry come from
``tests/multiplexer_support.py`` (registered through ``conftest``).
"""

from __future__ import annotations

import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import (
    _compile,
    _desloppify,
    _novel_done,
    _wordcount,
    novel,
    novel_state,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import parse_global_flags

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts

    # The ``driver`` fixture's value type, imported under ``TYPE_CHECKING`` only
    # (the developers-guide shared-type carve-out); the fixture itself is consumed
    # by name, never by a runtime value import.
    from multiplexer_support import Driver


class _Operation(typ.NamedTuple):
    """One dispatched operation paired with its legacy build_app and argv.

    ``spaced`` is the multiplexer subcommand argv (``["state", "check"]``);
    ``legacy_name``/``legacy_build`` are the console-script name and ``build_app``
    the legacy entry point drives. Bundling these keeps the test parameter lists
    within the project's argument-count gate (Pylint ``too-many-arguments``).
    """

    legacy_name: str
    legacy_build: cabc.Callable[[], cyclopts.App]
    spaced: list[str]


# The five operations, each as a (legacy entry point, multiplexer argv) twin.
# ``novel-compile`` is driven with ``--check`` (the read-only checker), never the
# bare write path (the trap documented in
# ``tests/test_compile_check_snapshots.py``).
_OPERATIONS: tuple[_Operation, ...] = (
    _Operation("novel-state", novel_state.build_app, ["state", "check"]),
    _Operation("novel-done", _novel_done.build_app, ["done"]),
    _Operation("novel-compile", _compile.build_app, ["compile", "--check"]),
    _Operation("desloppify", _desloppify.build_app, ["desloppify"]),
    _Operation("wordcount", _wordcount.build_app, ["wordcount"]),
)
_OPERATION_IDS: tuple[str, ...] = tuple(op.legacy_name for op in _OPERATIONS)


def _strip_command(envelope: str) -> dict[str, object]:
    """Parse a machine envelope and drop its ``command`` field for comparison.

    The legacy path stamps ``"novel-done"`` and the multiplexer stamps the spaced
    ``"novel done"`` (Decision Log D1), so an equality assertion compares every
    field *except* ``command``.

    Parameters
    ----------
    envelope : str
        The rendered machine-mode JSON envelope.

    Returns
    -------
    dict[str, object]
        The parsed envelope with ``command`` removed.
    """
    parsed: dict[str, object] = json.loads(envelope)
    del parsed["command"]
    return parsed


def _chdir_to_drafting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Materialise the coherent ``drafting`` corpus tree and chdir into its parent.

    The ``drafting`` phase carries a populated three-chapter manifest, so it
    exercises exit 0 (``state check``/``wordcount``/``desloppify``), exit 1
    (``done`` on an unsatisfied tree), and exit 4 (``compile --check`` on a
    divergent tree) without hand-curating per-operation trees. ``monkeypatch.chdir``
    is auto-reverted and xdist-safe (never a bare ``os.chdir``).

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Supplies the auto-reverted ``chdir``.
    tmp_path : Path
        The per-test temporary directory the tree is built under.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["drafting"], tmp_path)
    monkeypatch.chdir(working.parent)


@pytest.mark.parametrize("op", _OPERATIONS, ids=_OPERATION_IDS)
def test_multiplexer_matches_legacy_over_drafting_tree(
    op: _Operation,
    driver: Driver,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Each operation emits the legacy envelope and exit code via the multiplexer.

    Drives the legacy entry point and the multiplexer over the *same* coherent
    ``drafting`` corpus tree and asserts the exit codes are equal and the
    envelopes are equal modulo the ``command`` field. This is the core
    no-behaviour-change proof across the five operations.
    """
    _chdir_to_drafting(monkeypatch, tmp_path)

    legacy_code, legacy_out = driver.legacy(
        op.legacy_build, op.spaced[1:], op.legacy_name
    )
    mux_code, mux_out = driver.mux(op.spaced)

    assert mux_code == legacy_code
    assert _strip_command(mux_out) == _strip_command(legacy_out)
    # The multiplexer stamps the spaced name; the legacy path the hyphenated one.
    assert json.loads(mux_out)["command"] == novel._command_name_for(op.spaced)
    assert json.loads(legacy_out)["command"] == op.legacy_name


def test_multiplexer_done_success_matches_legacy(
    all_hold_tree: cabc.Callable[[], Path],
    driver: Driver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``novel done`` exits 0 on a satisfied tree, matching the legacy path."""
    working = all_hold_tree()
    monkeypatch.chdir(working.parent)

    legacy_code, legacy_out = driver.legacy(_novel_done.build_app, [], "novel-done")
    mux_code, mux_out = driver.mux(["done"])

    assert legacy_code == ExitCode.SUCCESS
    assert mux_code == legacy_code
    assert _strip_command(mux_out) == _strip_command(legacy_out)


class _UsageFault(typ.NamedTuple):
    """One usage-fault argv paired with the message prefix it must surface.

    Bundling the argv and its expected fault into one parametrize cell keeps the
    test parameter list within the project's argument-count gate (Pylint
    ``too-many-arguments``), mirroring ``_ErrorArm`` in
    ``tests/test_command_surface_matrix.py``.
    """

    argv: list[str]
    fault: str


_USAGE_FAULTS: tuple[_UsageFault, ...] = (
    _UsageFault(["state", "bogus"], "Unknown command"),
    _UsageFault(["done", "extra"], "Unused"),
    # A leading ``--bad-option`` faults at the parent, which routes commands and
    # has no default body, so cyclopts reports an unknown *command* (still the
    # exit-2 usage arm) rather than an unknown option.
    _UsageFault(["--bad-option"], "Unknown command"),
    # An unknown option *under* a leaf faults as an unknown option, proving the
    # leaf's own parser still runs under the mount.
    _UsageFault(["done", "--bad-option"], "Unknown option"),
)
_USAGE_FAULT_IDS: tuple[str, ...] = (
    "unknown-subcommand",
    "extra-positional",
    "parent-bad-option",
    "leaf-unknown-option",
)


@pytest.mark.parametrize("case", _USAGE_FAULTS, ids=_USAGE_FAULT_IDS)
def test_multiplexer_usage_faults_exit_two(
    case: _UsageFault,
    driver: Driver,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A usage fault maps to exit 2 with the usage envelope (no body runs)."""
    _chdir_to_drafting(monkeypatch, tmp_path)

    code, out = driver.mux(case.argv)

    assert code == ExitCode.USAGE_ERROR
    envelope = json.loads(out)
    assert envelope["ok"] is False
    assert case.fault.lower() in " ".join(envelope["messages"]).lower()


def test_multiplexer_missing_working_exits_three(
    driver: Driver,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``novel state check`` with no ``working/`` raises the exit-3 state error."""
    monkeypatch.chdir(tmp_path)

    code, out = driver.mux(["state", "check"])

    assert code == ExitCode.STATE_ERROR
    assert json.loads(out)["ok"] is False


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["--version"],
        ["state", "--help"],
        ["done", "--help"],
        [],
    ],
    ids=["help", "version", "state-help", "done-help", "bare"],
)
def test_multiplexer_help_version_emit_no_envelope(
    argv: list[str], driver: Driver
) -> None:
    """Help/version/bare exit 0 and emit no JSON envelope on stdout."""
    code, out = driver.mux(argv)

    assert code == ExitCode.SUCCESS
    # No envelope: stdout is help/version text, never the machine JSON object.
    stripped = out.strip()
    if stripped.startswith("{"):
        msg = f"help/version unexpectedly emitted a JSON envelope: {stripped!r}"
        raise AssertionError(msg)


def test_main_drives_the_multiplexer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """``main`` parses ``--human``, derives the name, and drives via ``run``.

    Patches ``sys.argv`` so ``main`` reads the residual argv exactly as the
    installed console-script would, and asserts the human envelope is emitted at
    exit 0 for ``novel state check`` on a coherent tree.
    """
    _chdir_to_drafting(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", ["novel", "--human", "state", "check"])

    with pytest.raises(SystemExit) as excinfo:
        novel.main()

    assert int(typ.cast("int", excinfo.value.code)) == ExitCode.SUCCESS
    out = capsys.readouterr().out
    assert "command: novel state" in out
    # ``--human`` was consumed, so the residual argv reached the subcommand.
    assert "ok: True" in out


def test_parse_global_flags_underpins_main() -> None:
    """``main`` relies on ``parse_global_flags`` to split ``--human`` first.

    A regression guard for Decision Log D4: the name is derived from the residual
    argv *after* ``--human`` is removed, so ``--human`` never shifts the command
    token.
    """
    human, residual = parse_global_flags(["--human", "state", "check"])
    assert human is True
    assert novel._command_name_for(residual) == "novel state"
