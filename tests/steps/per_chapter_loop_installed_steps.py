"""Installed-binary step definitions for the per-chapter loop (roadmap 6.2.2).

These re-drive the headline clean pass and the stale-compile catch of the
in-process scenarios through the **installed** console-scripts over a built
wheel, the real wheel/venv packaging boundary design §9 lines 835-847 names as
the end-to-end loop scope. Where the in-process steps cross the Cyclopts app and
the shared ``run`` wrapper, these cross the installed entry points an operator
and the harness actually invoke, so the harness-trusted exit codes are proven at
the packaging boundary, not only in-process (ExecPlan Decision Log; ADR-003).

The wheel/venv build is supplied by the module-scoped ``installed_novel_state``
fixture (``tests/installed_binary_fixtures.py``); the four sibling scripts
(``novel-done``, ``wordcount``, ``desloppify``, ``novel-compile``) resolve from
the same ``bin/`` directory (``installed_novel_state.parent``), so one venv
install yields all five scripts with no second wheel build (Surprises). Each
script is run by absolute path through a single-program cuprum catalogue with
``ExecutionContext(cwd=run_dir)`` so it resolves ``./working/state.toml``,
mirroring ``tests/test_recount_e2e.py`` and ``tests/test_console_scripts_e2e.py``.
``novel-compile`` is always driven with ``--check`` — its bare invocation writes
``compiled.md`` (ExecPlan D-CHECK-ARGV).

This module is kept separate from the in-process step module so the cuprum
imports and the installed fixtures do not load on every in-process run. It lives
under ``tests/steps/`` (the directory ``pyproject.toml`` exempts from the
assert/argument-count rules) and is imported into
``tests/test_per_chapter_loop_installed_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

import working_corpus as wc
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext
from pytest_bdd import given, then, when

from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

# The drafted totals every installed assertion pins, matching the in-process pins.
_DRAFTED_TOTAL: typ.Final = 68800

# Each loop command maps to the extra argv the installed script needs: ``recount``
# selects the ``novel-state`` subcommand, ``--check`` selects the read-only compile
# surface, and the other three run bare.
_LOOP_ARGV: typ.Final[dict[str, tuple[str, ...]]] = {
    "novel-state": ("recount",),
    "novel-done": (),
    "wordcount": (),
    "desloppify": (),
    "novel-compile": ("--check",),
}


@dc.dataclass(slots=True)
class _Installed:
    """The installed scripts directory, a run dir, and the per-command captures.

    ``scripts_dir`` is the venv ``bin/`` holding all five console-scripts;
    ``run_dir`` is the per-test cwd whose ``working/`` tree each script resolves.
    The captures accumulate across the ``When`` steps for the ``Then`` assertions.
    """

    scripts_dir: Path
    run_dir: Path
    catalogue: cabc.Callable[[str, Program], ProgramCatalogue]
    captures: dict[str, tuple[int, dict[str, object], str]] = dc.field(
        default_factory=dict
    )


def _run_installed(
    installed: _Installed, command_name: str
) -> tuple[int, dict[str, object], str]:
    """Run an installed script by absolute path; return ``(exit_code, env, stderr)``.

    Resolves the sibling script from the shared ``bin/`` directory, runs it through
    a single-program cuprum catalogue with ``ExecutionContext(cwd=run_dir)`` so it
    resolves ``./working/state.toml``, and parses its machine-mode stdout as the
    JSON envelope, exactly as the existing installed e2es do.
    """
    script_path = installed.scripts_dir / command_name
    prog = Program(str(script_path))
    catalogue = installed.catalogue(f"per-chapter-loop-{command_name}", prog)
    result = sh.make(prog, catalogue=catalogue)(*_LOOP_ARGV[command_name]).run_sync(
        context=ExecutionContext(cwd=installed.run_dir), capture=True
    )
    envelope = json.loads(result.stdout or "{}")
    return (
        result.exit_code,
        typ.cast("dict[str, object]", envelope),
        result.stderr or "",
    )


def _result(installed: _Installed, command_name: str) -> dict[str, object]:
    """Return the parsed ``result`` block from ``command_name``'s captured envelope."""
    _code, envelope, _stderr = installed.captures[command_name]
    return typ.cast("dict[str, object]", envelope["result"])


def _assert_no_traceback(installed: _Installed, command_name: str) -> None:
    """Assert ``command_name``'s installed run emitted no traceback on stderr.

    Design §10: a finding or state fault yields a structured message, never a
    stack trace, so a ``Traceback`` on stderr is a real defect at the boundary.
    """
    _code, _envelope, stderr = installed.captures[command_name]
    assert "Traceback" not in stderr, f"{command_name} emitted a traceback: {stderr}"


def _build_installed(
    installed_novel_state: Path,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
    spec: wc.WorkingTreeSpec,
) -> _Installed:
    """Materialise a per-test ``working/`` tree beside the installed scripts.

    Resolves the shared ``bin/`` from the module-scoped installed ``novel-state``
    path and builds ``spec`` under a per-test ``run_dir`` so the cases stay
    independent while reusing the one wheel install (Surprises).
    """
    run_dir = tmp_path / "run"
    wc.build_working_tree(spec, run_dir)
    return _Installed(
        scripts_dir=installed_novel_state.parent,
        run_dir=run_dir,
        catalogue=single_program_catalogue,
    )


@given("an installed loop tree that passes clean", target_fixture="installed")
def installed_clean_tree(
    installed_novel_state: Path,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> _Installed:
    """Build the all-hold tree beside the installed scripts for the clean pass.

    Returns
    -------
    _Installed
        The installed scripts dir, the per-test run dir, and the catalogue builder.
    """
    return _build_installed(
        installed_novel_state,
        tmp_path,
        single_program_catalogue,
        wc.DONE_PREDICATE_ALL_HOLD,
    )


@when("the installed spine runs over the clean tree")
def run_installed_clean_spine(installed: _Installed) -> None:
    """Drive all five installed scripts over the clean tree, capturing each result."""
    for command_name in _LOOP_ARGV:
        installed.captures[command_name] = _run_installed(installed, command_name)


@then("every installed loop command exits 0 with no traceback")
def installed_clean_exit_zero(installed: _Installed) -> None:
    """Assert every installed script exits 0 with no traceback on the clean tree.

    This is the composed clean pass at the installed boundary: ``recount``,
    ``novel-done``, ``wordcount``, ``desloppify``, and ``novel-compile --check``
    each resolve the real ``working/`` tree and exit 0, the same envelope the
    in-process clean pass pins.
    """
    for command_name in _LOOP_ARGV:
        code, _envelope, _stderr = installed.captures[command_name]
        assert code == ExitCode.SUCCESS, (
            f"installed {command_name} exited {code}, expected 0"
        )
        _assert_no_traceback(installed, command_name)


@then("the installed wordcount reports all three knitting gates crossed")
def installed_wordcount_gates(installed: _Installed) -> None:
    """Assert the installed ``wordcount`` reports all three crossed gates (§4.5)."""
    cumulative = typ.cast(
        "dict[str, object]", _result(installed, "wordcount")["cumulative"]
    )
    assert cumulative["current"] == _DRAFTED_TOTAL
    assert cumulative["gate_triggered_30"] is True
    assert cumulative["gate_triggered_50"] is True
    assert cumulative["gate_triggered_80"] is True


@then("the installed compile reports the compile is not diverged")
def installed_compile_clean(installed: _Installed) -> None:
    """Assert the installed ``novel-compile --check`` finds the compile matching."""
    assert _result(installed, "novel-compile")["diverged"] is False


@given(
    "an installed loop tree whose compiled.md is byte-divergent",
    target_fixture="installed",
)
def installed_stale_tree(
    installed_novel_state: Path,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> _Installed:
    """Build the sole-stale-compile tree beside the installed scripts.

    Returns
    -------
    _Installed
        The installed scripts dir, the per-test run dir, and the catalogue builder.
    """
    return _build_installed(
        installed_novel_state,
        tmp_path,
        single_program_catalogue,
        wc.DONE_PREDICATE_SOLE_STALE_COMPILE,
    )


@when("the installed novel-done and compile run over the stale tree")
def run_installed_stale(installed: _Installed) -> None:
    """Drive the installed ``novel-done`` and ``novel-compile`` over the stale tree.

    ``novel-compile`` runs with ``--check`` (the read surface). Both commands
    surface the stale ``compiled.md`` as an actionable finding; their captures
    feed the exit-4 assertions in the following step.
    """
    installed.captures["novel-done"] = _run_installed(installed, "novel-done")
    installed.captures["novel-compile"] = _run_installed(installed, "novel-compile")


@then("the installed novel-done exits 4 and the compile exits 4 diverged")
def installed_stale_caught(installed: _Installed) -> None:
    """Assert the installed boundary catches the stale compile at exit 4, no traceback.

    Both the installed ``novel-done`` (the otherwise-complete carve-out) and the
    installed ``novel-compile --check`` (the divergence checker) exit 4 with a
    structured finding and no stack trace, proving §10's stale-compile failure
    mode at the real packaging boundary.
    """
    done_code, _done_env, _done_err = installed.captures["novel-done"]
    assert done_code == ExitCode.ACTIONABLE_FINDING, (
        f"installed novel-done exited {done_code}, expected 4"
    )
    assert _result(installed, "novel-done")["compile_consistent"] is False
    _assert_no_traceback(installed, "novel-done")

    compile_code, _compile_env, _compile_err = installed.captures["novel-compile"]
    assert compile_code == ExitCode.ACTIONABLE_FINDING, (
        f"installed novel-compile --check exited {compile_code}, expected 4"
    )
    assert _result(installed, "novel-compile")["diverged"] is True
    _assert_no_traceback(installed, "novel-compile")
