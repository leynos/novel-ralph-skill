"""The combinatorial ``command x output-mode x phase`` matrix (roadmap 6.2.1).

This module proves the five read console-scripts behave correctly across the
*whole* verification surface — every ``command x output-mode x phase``
combination — rather than only in the isolated slices each command's own suite
already covers (design §2.3 lines 125-129; §9 lines 817-821). It contributes the
cross-product view the per-command suites do not: each of the five read commands
driven across the eleven coherent phase states, in both output modes.

Beyond the body-produced ``command x output-mode x phase`` cells (exit 0/1/4),
the matrix also crosses the two **command-agnostic diagnostic arms** the shared
``run`` wrapper stamps *before or instead of* a command body returning a value
(§3.2 lines 203-230; §9 lines 822-826): the usage-error arm (exit 2,
``CycloptsError``, triggered by an unknown option) and the state-error arm (exit
3, ``StateInputError``, triggered by an absent ``working/``). Both are crossed
with every read command in both output modes, proving the ``--human`` stamp
reaches the body-less arms (ADR-003 §3.1). Their ``messages`` field is the only
platform/command-variable datum (the exit-3 errno text and the exit-2 suggestion
suffix), so the snapshot redacts it and the message is asserted by its stable,
command-body-owned prefix.

The surface is bounded deliberately. The design carries the exhaustive
cross-product gaps "knowingly rather than silently" (§9 lines 819-821), so this
module documents exactly which cells are covered and which combinatorial gaps it
carries — see the ``Carried gaps`` section below.

Read surface (the phase-sensitive query commands). ``novel-state`` is a
multi-subcommand surface; this matrix treats its ``check`` *query* as the
phase-read unit and excludes its mutators (``init``, ``set-cursor``,
``advance-phase``, ``recount``, ``reconcile``), which are command/query
segregated (§3.3) and owned by their own suites and by tasks 6.2.2/6.2.5. The
other four commands register a single default callback. ``novel-compile`` is
driven with ``["--check"]`` (the read-only divergence checker), **never** ``[]``:
the bare ``[]`` argv runs the write path, which mutates ``compiled.md`` and emits
the write envelope rather than the ``diverged`` checker envelope (the repo
documents this trap at ``tests/test_compile_check_snapshots.py`` lines 13-16).

Drive seam. Every command is driven in-process through
:func:`novel_ralph_skill.contract.runner.run` over the ``working_corpus`` phase
trees, the same seam ``tests/test_novel_done_snapshots.py`` and
``tests/test_compile_check_snapshots.py`` use. This is the *fast* matrix;
installed-binary coverage is the separate scope of roadmap tasks 6.2.4/6.2.2, so
these tests carry no ``slow``/``timeout`` marks and consume cuprum nowhere.

Slugs. The corpus chapter slugs are fixed deterministic ``chapter-NN`` strings
built from the manifest index (``tests/working_corpus/_library.py``), so they do
not churn; the machine snapshot pins them verbatim as part of the machine
contract (§9 line 813) rather than normalising them away. The compile checker's
``working/manuscript/compiled.md`` token is likewise a fixed working-relative
contract constant (not a per-run path), so the volatile guard exempts it while the
snapshot still pins it verbatim.

Carried gaps (documented rather than silently omitted, §9 lines 819-821):

- **Mutator x phase** cross-products. ``novel-state``'s mutators (``init``,
  ``set-cursor``, ``advance-phase``, ``recount``, ``reconcile``) and
  ``novel-compile``'s write path are command/query segregated (§3.3) and are not
  the phase-read surface this task targets; they are covered by their own suites
  and by tasks 6.2.2/6.2.5.
- **Exhaustive eleven-phase cross-product** for the manifest-sensitive commands.
  ``novel-compile --check`` and ``desloppify`` are not eleven-phase-invariant but
  collapse to their *manifest* branches (compile: the exit-3/4/0 split keyed on
  the manifest+compiled state; desloppify: ``total_words`` 0 vs 68800). They are
  asserted as those real branches (Work item 4), not as eleven independent cells.
- **Incoherent-variant x phase** cross-products are covered by the validator
  suites (``tests/test_validate_state_corpus.py`` and the corpus oracle suites),
  not re-proven here.
- **Installed-binary crossing** (the console-script entry points over a built
  wheel) is the scope of task 6.2.4, not this in-process matrix.
"""

# This module is the single home for the whole ``command x output-mode x phase``
# matrix (ExecPlan Decision Log): the cross-product view and the carried-gap
# documentation belong together, so the matrix is kept in one module rather than
# split across files. The combined snapshot, human-mode, and per-command semantic
# coverage pushes it past the 400-line module cap; the cap is relaxed here for the
# same reason ``tests/test_working_corpus.py`` and
# ``tests/test_validate_state_property.py`` relax it.
# pylint: disable=too-many-lines

from __future__ import annotations

import json
import re
import typing as typ

import pytest
import working_corpus as wc

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
    from syrupy.assertion import SnapshotAssertion


class _ReadCommand(typ.NamedTuple):
    """One read surface: its console name, ``build_app`` factory, and argv.

    Bundling the three identity fields keeps the drive helper's and tests'
    parameter lists within the project's argument-count gate (Pylint
    ``too-many-arguments``) while still naming each field at the call site.
    """

    name: str
    build_app: cabc.Callable[[], cyclopts.App]
    argv: list[str]


# The five read surfaces. ``novel-state`` is keyed on its ``check`` query;
# ``novel-compile`` on ``--check`` (the read-only checker, never the write path —
# see the module docstring trap note).
_READ_REGISTRY: tuple[_ReadCommand, ...] = (
    _ReadCommand("novel-state", novel_state.build_app, ["check"]),
    _ReadCommand("novel-done", _novel_done.build_app, []),
    _ReadCommand("wordcount", _wordcount.build_app, []),
    _ReadCommand("novel-compile", _compile.build_app, ["--check"]),
    _ReadCommand("desloppify", _desloppify.build_app, []),
)

# The verified ``ok`` sign per ``(command, phase)`` cell. ``novel-state check``,
# ``wordcount``, and ``desloppify`` are ``ok=True`` for every phase; ``novel-done``
# is ``ok=False`` for every phase (the corpus never satisfies the full done
# predicate); ``novel-compile --check`` is ``ok=False`` for the eight pre-drafting
# phases and ``drafting``, and ``ok=True`` only for ``final-pass`` and ``done``.
# Captured in-process over the real corpus trees (see the ExecPlan Surprises).
_COMPILE_OK_PHASES: frozenset[str] = frozenset({"final-pass", "done"})

# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path, an ISO-8601 date, or a clock time. Mirrors the desloppify/novel-done guard
# in ``tests/test_novel_done_snapshots.py``.
_VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"
    r"|/[^/\"\s]+/"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}:\d{2}:\d{2}"
)

# The one deterministic working-relative path token the compile checker emits
# (``checked``/its message). It is a fixed contract constant by construction
# (``tests/test_compile_check_snapshots.py`` line 8, ExecPlan D-RESULT), not a
# volatile per-run path, so the volatile guard exempts it rather than flagging it
# as multi-segment-path churn. The snapshot still pins it verbatim.
_DETERMINISTIC_PATH_TOKEN = "working/manuscript/compiled.md"  # noqa: S105  # a path, not a secret

_BY_NAME: dict[str, _ReadCommand] = {
    command.name: command for command in _READ_REGISTRY
}

# The drafting-era phases carry a populated three-chapter manifest; the eight
# pre-drafting phases (premise…chapter-planning) carry an empty manifest. Several
# Work item 3/4 branch assertions key on this manifest split.
_DRAFTING_ERA_PHASES: frozenset[str] = frozenset({"drafting", "final-pass", "done"})

_CELL_IDS: tuple[str, ...] = tuple(
    f"{command.name}-{phase}" for command in _READ_REGISTRY for phase in wc.PHASE_ORDER
)
_CELLS: tuple[tuple[_ReadCommand, str], ...] = tuple(
    (command, phase) for command in _READ_REGISTRY for phase in wc.PHASE_ORDER
)


class _ErrorArm(typ.NamedTuple):
    """One command-agnostic diagnostic arm of the shared ``run`` wrapper.

    The two arms (``_USAGE_ARM`` and ``_STATE_ARM``) are the envelopes ``run``
    stamps *before or instead of* a command body returning a value (§3.2 lines
    203-230; ``runner.py`` lines 225-239). Both are command-agnostic: driven
    through ``run``, every read command yields the same exit code, the same
    ``ok: false`` skeleton, an empty ``result``, and a message whose stable
    prefix is identical across all five commands (ExecPlan Surprises). The only
    field that varies is ``messages`` — the exit-3 errno text and the exit-2
    suggestion suffix (``novel-compile --check`` appends "Did you mean
    --no-check?") — so the snapshot redacts it and the message is asserted by
    its command-body-owned prefix instead.

    Bundling the arm into a single parametrize cell with its command (see
    ``_ERROR_CELLS``) keeps the drive helper's and tests' parameter lists within
    the project's argument-count gate (Pylint ``too-many-arguments``).
    """

    label: str
    extra_argv: list[str]
    build_working: bool
    expected_code: ExitCode
    message_prefix: str


# Usage (exit 2): an unknown option appended to the read argv faults at parse
# before the body runs, so a real ``working/`` tree leaves only the argv at fault.
_USAGE_ARM = _ErrorArm(
    label="usage",
    extra_argv=["--nope"],
    build_working=True,
    expected_code=ExitCode.USAGE_ERROR,
    message_prefix="Unknown option:",
)
# State (exit 3): a cwd with no ``working/`` makes every body raise
# ``StateInputError`` when it tries to load ``working/state.toml``.
_STATE_ARM = _ErrorArm(
    label="state",
    extra_argv=[],
    build_working=False,
    expected_code=ExitCode.STATE_ERROR,
    message_prefix="cannot load working/state.toml",
)

_ErrorCell = tuple[_ReadCommand, _ErrorArm]

_ERROR_ARMS: tuple[_ErrorArm, ...] = (_USAGE_ARM, _STATE_ARM)
_ERROR_CELLS: tuple[_ErrorCell, ...] = tuple(
    (command, arm) for command in _READ_REGISTRY for arm in _ERROR_ARMS
)
_ERROR_CELL_IDS: tuple[str, ...] = tuple(
    f"{command.name}-{arm.label}" for command in _READ_REGISTRY for arm in _ERROR_ARMS
)


def _build_phase_tree(phase: str, tmp_path: Path) -> Path:
    """Build the coherent ``working/`` tree for ``phase`` under ``tmp_path``.

    Mirrors the ``phase_state_tree`` factory pattern
    (``tests/corpus_fixtures.py`` lines 195-201): a per-phase subdirectory keeps
    repeated builds within one test from inheriting a previous phase's tree.

    Parameters
    ----------
    phase : str
        The phase enum member name to build.
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Path
        The materialised ``working/`` path.
    """
    dest = tmp_path / phase
    dest.mkdir(exist_ok=True)
    return wc.build_working_tree(wc.PHASE_STATES[phase], dest)


class _Driver(typ.Protocol):
    """An in-process command driver bundling the chdir and capture mechanics."""

    def __call__(
        self, command: _ReadCommand, working: Path, *, human: bool
    ) -> tuple[int, str]:
        """Drive ``command`` from ``working.parent``; return ``(code, out)``."""


@pytest.fixture
def drive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> _Driver:
    """Return an in-process driver for a read command over a phase tree.

    Bundling ``monkeypatch`` and ``capsys`` into one fixture keeps each test's
    parameter list within the project's argument-count gate (Pylint
    ``too-many-arguments``) while still delivering the capture mechanics by
    fixture name. The returned callable is modelled on
    ``tests/test_novel_done_snapshots.py::_run_capture`` (lines 56-71): it changes
    directory with ``monkeypatch.chdir`` (auto-reverted, xdist-safe — never a bare
    ``os.chdir``) and captures stdout via the ``capsys`` fixture. The caller
    ``json.loads`` the text for machine mode and keeps it raw for human mode.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Supplies the auto-reverted ``chdir``.
    capsys : pytest.CaptureFixture[str]
        Captures the rendered stdout.

    Returns
    -------
    _Driver
        A callable ``(command, working, *, human) -> (code, out)``.
    """

    def _drive(command: _ReadCommand, working: Path, *, human: bool) -> tuple[int, str]:
        """Drive ``command`` from ``working.parent``; return ``(code, out)``."""
        monkeypatch.chdir(working.parent)
        with pytest.raises(SystemExit) as excinfo:
            run(
                command.build_app(),
                command.argv,
                RunContext(command=command.name, working_dir="working", human=human),
            )
        return int(typ.cast("int", excinfo.value.code)), capsys.readouterr().out

    return _drive


def _assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path.

    Reuses the volatile-field guard pattern from
    ``tests/test_novel_done_snapshots.py`` (lines 74-84) so a churn-prone field
    cannot silently slip into the snapshot.

    Parameters
    ----------
    envelope : dict[str, object]
        The parsed machine-mode envelope.
    """
    rendered = json.dumps(envelope).replace(_DETERMINISTIC_PATH_TOKEN, "<compiled>")
    match = _VOLATILE_PATTERN.search(rendered)
    assert match is None, (
        f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        if match is not None
        else ""
    )
    for key in ("timestamp", "created_at", "now", "time"):
        assert key not in rendered, f"unexpected volatile key {key!r} in envelope"


@pytest.mark.parametrize("cell", _CELLS, ids=_CELL_IDS)
def test_machine_envelope_matrix(
    cell: tuple[_ReadCommand, str],
    tmp_path: Path,
    drive: _Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot the machine-mode envelope for every ``command x phase`` cell.

    Pins the rendered machine-mode JSON envelope per read command across the
    eleven coherent phase states (§9 lines 811-813; §2.3 lines 125-129). Each
    snapshot is paired with semantic assertions — the envelope names the right
    command and carries the verified ``ok`` sign for the cell — so no behaviour is
    snapshot-only (AGENTS.md "pair them with semantic assertions").
    """
    command, phase = cell
    working = _build_phase_tree(phase, tmp_path)
    code, raw = drive(command, working, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert envelope["command"] == command.name
    expected_ok = _expected_ok(command.name, phase)
    assert envelope["ok"] is expected_ok
    assert (code == ExitCode.SUCCESS) is expected_ok
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


@pytest.mark.parametrize("cell", _CELLS, ids=_CELL_IDS)
def test_human_mode_presence_matrix(
    cell: tuple[_ReadCommand, str],
    tmp_path: Path,
    drive: _Driver,
) -> None:
    """Assert ``--human`` renders a non-empty body for every ``command x phase``.

    The design asserts human mode for *presence* — it renders without error and
    is non-empty — not byte-for-byte (§2.3 lines 127-129; §9 lines 817-819), so
    this is not snapshotted. The drive catches the command's ``SystemExit`` and
    returns its body, so even the compile exit-3 pre-drafting cells (which render
    the error envelope in human mode and exit 3) assert presence, not exit 0. A
    targeted assertion that the rendering names the command makes "presence"
    meaningful rather than a bare truthiness check (mirroring the human-mode
    assertion in ``tests/test_novel_done_snapshots.py``).
    """
    command, phase = cell
    working = _build_phase_tree(phase, tmp_path)
    _code, rendered = drive(command, working, human=True)
    assert rendered.strip(), "human mode must render a non-empty report"
    assert command.name in rendered


def _drive_error_cell(
    cell: _ErrorCell, tmp_path: Path, drive: _Driver, *, human: bool
) -> tuple[int, str]:
    """Drive an ``(command, arm)`` error cell; return ``(code, out)``.

    For ``build_working=False`` the cell needs a cwd with no ``working/``: it
    builds a bare per-arm directory and passes a synthetic ``working`` path under
    it that is **not** materialised, so ``working.parent`` is that empty cwd. The
    ``drive`` fixture only reads ``working.parent`` and never stats ``working``
    itself, so it is reused unchanged. Bundling ``cell`` keeps this helper at four
    parameters (three positional plus one keyword-only), within the Pylint
    ``too-many-arguments``/``too-many-positional-arguments`` gate.

    Parameters
    ----------
    cell : _ErrorCell
        The ``(command, arm)`` pair to drive.
    tmp_path : Path
        The per-test temporary directory.
    drive : _Driver
        The in-process driver fixture.
    human : bool
        Whether to render the human rather than the machine envelope.

    Returns
    -------
    tuple[int, str]
        The exit code and the rendered stdout.
    """
    command, arm = cell
    root = tmp_path / arm.label
    root.mkdir(exist_ok=True)
    if arm.build_working:
        working = wc.build_working_tree(wc.PHASE_STATES["drafting"], root)
    else:
        working = root / "working"  # deliberately NOT created
    argv = [*command.argv, *arm.extra_argv]
    return drive(command._replace(argv=argv), working, human=human)


@pytest.mark.parametrize("cell", _ERROR_CELLS, ids=_ERROR_CELL_IDS)
def test_error_arm_machine_envelope(
    cell: _ErrorCell,
    tmp_path: Path,
    drive: _Driver,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot the machine-mode envelope for both diagnostic arms per command.

    Crosses the two command-agnostic arms ``run`` stamps before the body returns
    — usage (exit 2) and state (exit 3) — with every read command (§3.2 lines
    203-230; §9 lines 822-826). Each snapshot redacts ``messages`` (the only
    platform/command-variable field — exit-3 errno text, exit-2 suggestion
    suffix) and is **paired** with semantic assertions on the envelope skeleton
    and the command-body-owned message prefix, so no behaviour is snapshot-only
    (AGENTS.md). The ``len(messages) == 1`` assertion restores the count signal
    the redaction would otherwise collapse.
    """
    command, arm = cell
    code, raw = _drive_error_cell(cell, tmp_path, drive, human=False)
    envelope = typ.cast("dict[str, object]", json.loads(raw))
    assert code == arm.expected_code
    assert envelope["command"] == command.name
    assert envelope["ok"] is False
    assert envelope["working_dir"] == "working"
    assert envelope["result"] == {}
    messages = typ.cast("list[str]", envelope["messages"])
    assert len(messages) == 1
    assert messages[0].startswith(arm.message_prefix)
    redacted = {**envelope, "messages": ["<redacted>"]}
    _assert_no_volatile_fields(redacted)
    assert redacted == snapshot


@pytest.mark.parametrize("cell", _ERROR_CELLS, ids=_ERROR_CELL_IDS)
def test_error_arm_human_presence(
    cell: _ErrorCell,
    tmp_path: Path,
    drive: _Driver,
) -> None:
    """Assert ``--human`` renders a non-empty body for both diagnostic arms.

    Proves the ``--human`` stamp reaches the body-less arms (§3.2 lines 203-230;
    ADR-003 §3.1): the same presence contract ``test_human_mode_presence_matrix``
    uses, now over the exit-2/exit-3 envelopes ``run`` produces when the body
    never returns a ``result``.
    """
    command, _arm = cell
    _code, rendered = _drive_error_cell(cell, tmp_path, drive, human=True)
    assert rendered.strip(), "human mode must render a non-empty report"
    assert command.name in rendered


def _expected_ok(name: str, phase: str) -> bool:
    """Return the verified ``ok`` sign for the ``(name, phase)`` cell.

    Captured in-process over the real corpus phase trees (ExecPlan Surprises):
    ``novel-done`` is ``ok=False`` for every phase; ``novel-compile --check`` is
    ``ok=True`` only for ``final-pass`` and ``done``; the other three are
    ``ok=True`` for every phase.

    Parameters
    ----------
    name : str
        The console name of the command.
    phase : str
        The phase enum member name.

    Returns
    -------
    bool
        The expected ``ok`` value for the cell.
    """
    if name == "novel-done":
        return False
    if name == "novel-compile":
        return phase in _COMPILE_OK_PHASES
    return True


def _drive_machine_envelope(
    command: _ReadCommand, phase: str, tmp_path: Path, drive: _Driver
) -> tuple[int, dict[str, object]]:
    """Drive ``command`` over ``phase`` in machine mode; return ``(code, env)``.

    Parameters
    ----------
    command : _ReadCommand
        The read command to drive.
    phase : str
        The phase enum member name to build and drive over.
    tmp_path : Path
        The per-test temporary directory.
    drive : _Driver
        The in-process driver fixture.

    Returns
    -------
    tuple[int, dict[str, object]]
        The exit code and the parsed machine-mode envelope.
    """
    working = _build_phase_tree(phase, tmp_path)
    code, raw = drive(command, working, human=False)
    return code, typ.cast("dict[str, object]", json.loads(raw))


def _drive_machine_result(
    command: _ReadCommand, phase: str, tmp_path: Path, drive: _Driver
) -> tuple[int, dict[str, object]]:
    """Drive ``command`` over ``phase`` in machine mode; return ``(code, result)``.

    Folds the build-tree, drive, and ``result`` extraction the Work item 3/4
    branch assertions repeat per phase, so each test body stays declarative.

    Parameters
    ----------
    command : _ReadCommand
        The read command to drive.
    phase : str
        The phase enum member name to build and drive over.
    tmp_path : Path
        The per-test temporary directory.
    drive : _Driver
        The in-process driver fixture.

    Returns
    -------
    tuple[int, dict[str, object]]
        The exit code and the envelope's ``result`` mapping.
    """
    code, envelope = _drive_machine_envelope(command, phase, tmp_path, drive)
    return code, typ.cast("dict[str, object]", envelope["result"])


def test_done_phase_clause_across_phases(tmp_path: Path, drive: _Driver) -> None:
    """``phase_is_done`` is true only on the ``done`` tree; false on the other ten.

    Drives ``novel-done`` across all eleven phases and asserts the phase-keyed
    ``phase_is_done`` clause (§4.2 done predicate; ``phase.py`` enum order). The
    aggregate envelope ``ok``/exit is a *constant* ``False``/``1`` across every
    phase because the corpus never satisfies the full done predicate, so this test
    asserts the ``phase_is_done`` clause — the phase-keyed datum — not the
    aggregate ``ok``.

    The real failing-clause set differs by band and is pinned **in code** per band
    (not by docstring alone, so the B4/B5 attribution error class cannot recur):

    - the eight pre-drafting phases (empty manifest) fail on ``phase_is_done``,
      ``final_pass_complete``, ``knitting_gates_passed``, and ``compile_consistent``
      (compiled.md missing). ``all_chapters_flagged`` is **True** here — it holds
      vacuously over the empty manifest (``done_predicate.py`` line 182), so it is
      **not** a failing clause (the round-4 B5 fix);
    - ``drafting`` is the one tree where ``all_chapters_flagged`` genuinely fails
      (its last chapter is unflagged);
    - the ``done`` tree's sole failing clause is ``knitting_gates_passed`` (its
      ``state.toml`` gate booleans are all true, but the
      ``reviews/knitting-NN.md`` files are absent — ExecPlan Surprise);
      ``compile_consistent`` is **True** on ``done`` (the round-2 B4 fix).
    """
    command = _BY_NAME["novel-done"]
    for phase in wc.PHASE_ORDER:
        code, result = _drive_machine_result(command, phase, tmp_path, drive)
        assert code == ExitCode.BENIGN_NEGATIVE
        assert result["phase_is_done"] is (phase == "done")

    # Pin the failing-clause attribution in code, one representative cell per band.
    _, pre = _drive_machine_result(command, "premise", tmp_path, drive)
    assert pre["all_chapters_flagged"] is True
    assert pre["compile_consistent"] is False

    _, drafting = _drive_machine_result(command, "drafting", tmp_path, drive)
    assert drafting["all_chapters_flagged"] is False

    _, done = _drive_machine_result(command, "done", tmp_path, drive)
    assert done["knitting_gates_passed"] is False
    assert done["compile_consistent"] is True


def test_check_coherent_across_phases(tmp_path: Path, drive: _Driver) -> None:
    """``novel-state check`` is coherent (exit 0, no violations) for every phase.

    Drives ``novel-state check`` across all eleven phases and asserts exit 0,
    ``ok`` true, and an empty ``violations`` list (§5.2; the corpus phase states
    are coherent by construction). This drives the **command envelope**, not the
    structural oracle, so it is not a duplicate of
    ``tests/test_validate_state_corpus.py`` (which asserts the oracle directly):
    its assertion is on the envelope ``ok``/``violations``.
    """
    command = _BY_NAME["novel-state"]
    for phase in wc.PHASE_ORDER:
        code, result = _drive_machine_result(command, phase, tmp_path, drive)
        assert code == ExitCode.SUCCESS
        assert result["violations"] == []


def test_wordcount_branch_across_phases(tmp_path: Path, drive: _Driver) -> None:
    """``wordcount`` emits the zero-progress branch pre-drafting, populated after.

    Drives ``wordcount`` across all eleven phases and asserts the two verified
    branches (§4.5; the gate geometry's totality guard at
    ``_wordcount_report._gate_geometry`` and ``validate.py:261``):

    - the eight pre-drafting phases plus ``chapter-planning`` (empty manifest)
      emit ``chapters == []`` and the zero-progress cumulative block (current 0,
      no gates triggered, ``next_gate_threshold`` 0.3, ``next_gate_distance``
      24000);
    - the three drafting-era phases emit three chapter rows, ``current`` 68800,
      all three gates triggered, and ``next_gate_threshold`` ``None`` (past the
      final gate; D-NOGATE).
    """
    command = _BY_NAME["wordcount"]
    for phase in wc.PHASE_ORDER:
        code, result = _drive_machine_result(command, phase, tmp_path, drive)
        assert code == ExitCode.SUCCESS
        cumulative = typ.cast("dict[str, object]", result["cumulative"])
        if phase in _DRAFTING_ERA_PHASES:
            assert len(typ.cast("list[object]", result["chapters"])) == 3
            assert cumulative["current"] == 68800
            assert cumulative["gate_triggered_30"] is True
            assert cumulative["gate_triggered_50"] is True
            assert cumulative["gate_triggered_80"] is True
            assert cumulative["next_gate_threshold"] is None
        else:
            assert result["chapters"] == []
            assert cumulative == {
                "current": 0,
                "target": 80000,
                "percent_of_target": 0.0,
                "gate_triggered_30": False,
                "gate_triggered_50": False,
                "gate_triggered_80": False,
                "next_gate_threshold": 0.3,
                "next_gate_distance": 24000,
            }


def test_compile_check_branches_across_phases(tmp_path: Path, drive: _Driver) -> None:
    """``novel-compile --check`` splits into exit 3 / 4 / 0 along the phase axis.

    Drives ``novel-compile --check`` across all eleven phases and asserts the
    three verified branches (§10 lines 811-815;
    ``_compile._require_chapter_manifest`` and ``check_compiled``):

    - the eight pre-drafting phases (empty manifest) refuse with exit 3,
      ``ok`` false, ``result == {}``, and a message naming the empty-manifest
      refusal;
    - ``drafting`` (compiled.md absent → ABSENT projects to the actionable
      finding) diverges with exit 4, ``ok`` false, and ``diverged`` true;
    - ``final-pass`` and ``done`` (compiled.md present and matching) pass with
      exit 0, ``ok`` true, and ``diverged`` false.

    This is the **phase-axis** proof — the exit-3/4/0 split is keyed on the
    manifest+compiled state — distinct from
    ``tests/test_compile_check_snapshots.py``, which pins the MATCHES/DIVERGES
    envelopes on one hand-built tree.
    """
    command = _BY_NAME["novel-compile"]
    for phase in wc.PHASE_ORDER:
        code, envelope = _drive_machine_envelope(command, phase, tmp_path, drive)
        result = typ.cast("dict[str, object]", envelope["result"])
        if phase not in _DRAFTING_ERA_PHASES:
            assert code == ExitCode.STATE_ERROR
            assert envelope["ok"] is False
            assert result == {}
            messages = typ.cast("list[str]", envelope["messages"])
            assert any("manifest" in message for message in messages)
        elif phase == "drafting":
            assert code == ExitCode.ACTIONABLE_FINDING
            assert envelope["ok"] is False
            assert result == {
                "checked": _DETERMINISTIC_PATH_TOKEN,
                "chapters": 3,
                "diverged": True,
            }
        else:
            assert code == ExitCode.SUCCESS
            assert envelope["ok"] is True
            assert result["diverged"] is False


def test_desloppify_shape_across_phases(tmp_path: Path, drive: _Driver) -> None:
    """``desloppify`` is shape-stable across phases; only ``total_words`` varies.

    Drives ``desloppify`` across all eleven phases and asserts exit 0, ``ok``
    true, the stable ``result`` key set, an empty ``violations`` list, and an
    empty slimmed ``findings`` trail on every phase. Each phase is a clean pass,
    so the clean-pass findings contract (roadmap 7.1.3) slims the trail to the
    over-threshold rules — none here — even though the detection core still
    aggregates the full 24-rule shipped pack (§4.4; §3.3 checker read shape). The
    ``findings`` key stays present; only its contents collapse to ``[]``. The one
    phase-varying datum is ``total_words``: 0 for the eight empty-manifest
    pre-drafting phases and 68800 for the three drafting-era phases. So desloppify
    is shape-invariant but **not** value-invariant across phases.
    """
    command = _BY_NAME["desloppify"]
    for phase in wc.PHASE_ORDER:
        code, result = _drive_machine_result(command, phase, tmp_path, drive)
        assert code == ExitCode.SUCCESS
        assert set(result) == {"pack", "total_words", "violations", "findings"}
        assert result["violations"] == []
        assert result["findings"] == []
        expected_words = 68800 if phase in _DRAFTING_ERA_PHASES else 0
        assert result["total_words"] == expected_words
