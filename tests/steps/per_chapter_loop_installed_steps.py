"""Installed-binary step definitions for the per-chapter loop (roadmap 6.2.2, 6.2.9).

These re-drive the deterministic decisions of the in-process scenarios through
the **installed** console-scripts over a built wheel, the real wheel/venv
packaging boundary design §9 lines 835-847 names as the end-to-end loop scope.
Where the in-process steps cross the Cyclopts app and the shared ``run`` wrapper,
these cross the installed entry points an operator and the harness actually
invoke, so the harness-trusted exit codes are proven at the packaging boundary,
not only in-process (ExecPlan Decision Log; ADR-003). They cover the headline
clean pass (folding in the crossed knitting gate via the wordcount gates-crossed
assertion), the stale-compile catch, and the refused out-of-order ``advance-phase``
(exit 3, ``state.toml`` byte-for-byte intact; design §3.2, §4.1, §5.4) that closes
audit-6.2.2 Finding 7.

The run/build seam these steps drive — the ``_Installed`` capture record, the
``_run_installed_argv``/``_run_installed`` run helpers, ``_build_installed``, and
the ``_result``/``_assert_no_traceback`` accessors plus the ``_LOOP_ARGV`` and
drafted-total constants — lives in the sibling support module
``per_chapter_loop_installed_support`` (roadmap 6.2.9.1), split out so this step
module stays under the AGENTS.md 400-line cap as future installed arms land.

This module is kept separate from the in-process step module so the cuprum
imports and the installed fixtures do not load on every in-process run. It lives
under ``tests/steps/`` (the directory ``pyproject.toml`` exempts from the
assert/argument-count rules) and is imported into
``tests/test_per_chapter_loop_installed_bdd.py``.
"""

from __future__ import annotations

import typing as typ

import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.contract.exit_codes import ExitCode
from steps.per_chapter_loop_installed_support import (
    _DRAFTED_BY_CHAPTER,
    _DRAFTED_TOTAL,
    _LOOP_ARGV,
    _assert_no_traceback,
    _build_installed,
    _Installed,
    _result,
    _run_installed,
    _run_installed_argv,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue
    from cuprum.program import Program


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
        _run_installed(installed, command_name)


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


@then("the installed recount reports the drafted by-chapter counts")
def installed_recount_drafted_counts(installed: _Installed) -> None:
    """Assert the installed ``recount`` reports the drafted ``{current, by_chapter}``.

    The clean pass drives ``recount`` (a mutator) first, relying on it being a no-op
    over the all-hold tree (ExecPlan Risk 2). This proves that no-op at the real
    wheel boundary rather than inferring it from the in-process suite (review:6.2.2
    addendum 6.2.2.3); the recount capture lives under the ``"novel-state"`` key.
    """
    result = _result(installed, "novel-state")
    assert result["current"] == _DRAFTED_TOTAL
    assert result["by_chapter"] == _DRAFTED_BY_CHAPTER


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
    _run_installed(installed, "novel-done")
    _run_installed(installed, "novel-compile")


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


# --- gated decision: the installed advance-phase refuses out-of-order (§3.2) ---


@given(
    "an installed loop tree whose phase.completed skips the in-order prefix",
    target_fixture="installed",
)
def installed_out_of_order_tree(
    installed_novel_state: Path,
    tmp_path: Path,
    single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
) -> _Installed:
    """Build the ``completed-prefix-gap`` tree and record its prior ``state.toml``.

    ``INCOHERENT_VARIANTS["completed-prefix-gap"]`` is a ``drafting`` tree whose
    ``phase.completed = ("premise", "characters")`` skips the in-order prefix, so
    the installed ``advance-phase`` must refuse it. The prior ``state.toml`` bytes
    are captured into ``state_before`` so a later step can prove the refused mutator
    left the file byte-for-byte intact (design §5.4), mirroring the in-process
    refused-advance given.

    Returns
    -------
    _Installed
        The installed scripts dir, the per-test run dir, the catalogue builder, and
        the captured prior ``state.toml`` bytes.
    """
    installed = _build_installed(
        installed_novel_state,
        tmp_path,
        single_program_catalogue,
        wc.INCOHERENT_VARIANTS["completed-prefix-gap"][0],
    )
    installed.state_before = (installed.run_dir / "working" / "state.toml").read_bytes()
    return installed


@when("the installed advance-phase runs over the out-of-order tree")
def run_installed_advance_phase(installed: _Installed) -> None:
    """Drive the installed ``novel state advance-phase`` over the out-of-order tree.

    The script file is the single ``novel`` multiplexer; the ``("state",
    "advance-phase")`` argv mounts the ``state`` sub-app and selects the mutator
    subcommand; the capture key is the distinct ``"advance-phase"`` (the in-process
    refused step keys identically) so it never collides with the clean-pass
    recount capture.
    """
    _run_installed_argv(
        installed,
        "novel",
        ("state", "advance-phase"),
        capture_key="advance-phase",
    )


@then(
    "the installed advance-phase exits 3 with state.toml byte-for-byte intact "
    "and no traceback"
)
def installed_advance_phase_refused(installed: _Installed) -> None:
    """Assert the installed out-of-order advance refused: exit 3, intact, no trace.

    Design §3.2/§4.1: the runner stamps the exit-3 state error before the mutator
    body runs; §5.4: the refused mutator must not touch ``state.toml``; §10: a state
    fault yields a structured message, never a stack trace. This pins all three at
    the real wheel/venv boundary.
    """
    code, _envelope, _stderr = installed.captures["advance-phase"]
    assert code == ExitCode.STATE_ERROR, (
        f"installed advance-phase exited {code}, expected 3"
    )
    after = (installed.run_dir / "working" / "state.toml").read_bytes()
    assert after == installed.state_before, (
        "the refused installed advance mutated state.toml"
    )
    _assert_no_traceback(installed, "advance-phase")
