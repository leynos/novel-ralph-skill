"""Run/build helpers for the installed per-chapter loop steps (roadmap 6.2.9.1).

This support module holds the run/build seam the installed step definitions in
``per_chapter_loop_installed_steps`` drive — the ``_Installed`` capture record,
the ``_run_installed_argv``/``_run_installed`` run helpers, the ``_build_installed``
tree builder, and their ``_result``/``_assert_no_traceback`` capture accessors,
plus the drafted-total and ``_LOOP_ARGV`` constants they read. It is split out of
the step module (roadmap 6.2.9.1, from review:6.2.9) so the step definitions stay
well under the AGENTS.md 400-line module cap as future installed arms land; the
behaviour is unchanged from the pre-split single module.

Running an installed script is centralised in ``_run_installed_argv``, which
separates the script filename, the argv, and the capture key — three values the
single ``command_name`` argument of the older ``_run_installed`` conflated. The
helper writes its own ``installed.captures[capture_key]`` entry, so the ``When``
steps call it for its side effect and never assign the capture by hand;
``_run_installed`` delegates to it, keeping the clean-pass and stale-compile loops
byte-identical (ExecPlan Decision Log, roadmap 6.2.9).

The wheel/venv build is supplied by the module-scoped ``installed_novel_state``
fixture (``tests/installed_binary_fixtures.py``), which returns the single
``novel`` multiplexer script (roadmap task 1.2.13). Every loop operation resolves
that one ``novel`` script from the venv ``bin/`` directory
(``installed_novel_state.parent``) and drives it with the operation's mount-verb
argv (``state recount``, ``done``, ``wordcount``, ``desloppify``, ``compile
--check``), so one venv install drives all five subcommands with no second wheel
build. Each run goes by absolute path through a single-program cuprum catalogue
with ``ExecutionContext(cwd=run_dir)`` so it resolves ``./working/state.toml``,
mirroring ``tests/test_recount_e2e.py`` and ``tests/test_console_scripts_e2e.py``.
``compile`` is always driven with ``--check`` — its bare invocation writes
``compiled.md`` (ExecPlan D-CHECK-ARGV). The ``_LOOP_ARGV`` dict keys stay the
legacy operation labels purely as argv source and capture key, so the
``Then``-step capture lookups remain byte-identical.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported by
``per_chapter_loop_installed_steps``.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

import working_corpus as wc
from cuprum import sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

# The drafted totals every installed assertion pins, matching the in-process pins.
# ``_DRAFTED_BY_CHAPTER`` is the per-chapter table the all-hold tree drafts (the
# three drafted chapters sum to ``_DRAFTED_TOTAL``); a no-op ``recount`` over that
# tree must report exactly these ``{current, by_chapter}`` values, so the clean-pass
# assertion proves the no-op property at the installed wheel boundary rather than
# inferring it from the in-process suite (review:6.2.2 addendum 6.2.2.3).
_DRAFTED_BY_CHAPTER: typ.Final[dict[str, int]] = {"01": 24000, "02": 24000, "03": 20800}
_DRAFTED_TOTAL: typ.Final = 68800

# Each loop command maps to the full argv the single ``novel`` multiplexer needs:
# the mount verb that selects the operation, plus any extra tokens. ``state
# recount`` selects the recount subcommand of the ``state`` sub-app, ``compile
# --check`` selects the read-only divergence checker, and the other three run with
# their mount verb alone (roadmap task 1.2.13). The dict **keys** stay the legacy
# operation labels: they serve only as the argv source and the capture key here
# (the script basename is now the single ``novel`` script for every command), so
# the ``Then``-step capture lookups remain byte-identical (ExecPlan WI7).
_LOOP_ARGV: typ.Final[dict[str, tuple[str, ...]]] = {
    "novel-state": ("state", "recount"),
    "novel-done": ("done",),
    "wordcount": ("wordcount",),
    "desloppify": ("desloppify",),
    "novel-compile": ("compile", "--check"),
}


@dc.dataclass(slots=True)
class _Installed:
    """The installed scripts directory, a run dir, and the per-command captures.

    ``scripts_dir`` is the venv ``bin/`` holding all five console-scripts;
    ``run_dir`` is the per-test cwd whose ``working/`` tree each script resolves.
    The captures accumulate across the ``When`` steps for the ``Then`` assertions.
    ``state_before`` records the prior ``state.toml`` bytes for the refused-advance
    scenario so a ``Then`` step can prove the refused mutator left the file intact
    (design §5.4); the clean-pass and stale-compile givens leave it ``None``.
    """

    scripts_dir: Path
    run_dir: Path
    catalogue: cabc.Callable[[str, Program], ProgramCatalogue]
    captures: dict[str, tuple[int, dict[str, object], str]] = dc.field(
        default_factory=dict
    )
    state_before: bytes | None = None


def _run_installed_argv(
    installed: _Installed,
    script_name: str,
    argv: tuple[str, ...],
    *,
    capture_key: str,
) -> tuple[int, dict[str, object], str]:
    """Run ``script_name`` with ``argv``; store the capture under ``capture_key``.

    Resolves the sibling script from the shared ``bin/`` directory, runs it through
    a single-program cuprum catalogue with ``ExecutionContext(cwd=run_dir)`` so it
    resolves ``./working/state.toml``, and parses its machine-mode stdout as the
    JSON envelope, exactly as the existing installed e2es do. The script filename,
    the argv, and the capture key are separated so the single ``novel`` script can
    be driven with different subcommand argv (``state recount`` vs ``state
    advance-phase``) under distinct capture keys. The ``(exit_code, envelope,
    stderr)`` tuple is written into ``installed.captures[capture_key]`` and also
    returned, so callers may use the helper for its side effect alone.

    The single-write contract — each ``capture_key`` is written exactly once per
    ``_Installed`` — is enforced here rather than only documented (roadmap 6.2.9.3,
    from review:6.2.9), so a future ``When`` step that re-ran the helper under a key
    already captured (or re-added a manual ``captures[...] =`` assignment) fails
    loudly instead of silently overwriting the prior capture.
    """
    assert capture_key not in installed.captures, (
        f"capture key {capture_key!r} already written; "
        "_run_installed_argv writes each capture key exactly once"
    )
    script_path = installed.scripts_dir / script_name
    prog = Program(str(script_path))
    catalogue = installed.catalogue(f"per-chapter-loop-{capture_key}", prog)
    result = sh.make(prog, catalogue=catalogue)(*argv).run_sync(
        context=ExecutionContext(cwd=installed.run_dir), capture=True
    )
    envelope = json.loads(result.stdout or "{}")
    capture = (
        result.exit_code,
        typ.cast("dict[str, object]", envelope),
        result.stderr or "",
    )
    installed.captures[capture_key] = capture
    return capture


def _run_installed(
    installed: _Installed, command_name: str
) -> tuple[int, dict[str, object], str]:
    """Run a loop command by name; return ``(exit_code, env, stderr)``.

    Delegates to :func:`_run_installed_argv`, always resolving the single ``novel``
    multiplexer script (roadmap task 1.2.13) and using ``command_name`` as both the
    ``_LOOP_ARGV`` key (which now carries the mount-verb argv) and the capture key.
    The capture key stays the legacy operation label so every ``Then``-step lookup
    resolves unchanged.
    """
    return _run_installed_argv(
        installed,
        "novel",
        _LOOP_ARGV[command_name],
        capture_key=command_name,
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
