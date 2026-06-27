"""The ``novel-done`` command body and its Cyclopts app (design §4.2).

``novel-done`` is the read-only done predicate as a console-script: it loads the
fixed ``working/state.toml``, evaluates the six §4.2 clauses against disk through
:func:`novel_ralph_skill.state.done_predicate.evaluate_done`, and projects the
per-clause result into the shared envelope. It writes nothing on any path
(ADR-001; design §3.3 puts ``novel-done`` in the read-only checker column) and
takes no positional or keyword arguments.

The exit-code contract (design §3.2): exit ``0`` when every clause holds, exit
``1`` (the benign "not yet done" the harness loops on) when a drafting clause is
unmet (alone or alongside a stale compile), exit ``3`` when ``state.toml`` is
missing/unparseable or a chapter artefact is unreadable, and exit ``2`` (the
runner's ``CycloptsError`` arm) on a usage error.

Roadmap task 3.1.2 adds the exit-``4`` (``ACTIONABLE_FINDING``) carve-out: when
``compile_consistent`` is the *sole* false clause **and** ``compiled.md`` is
present — a stale-present compile the harness can regenerate — ``novel-done``
exits ``4`` (matching ``novel-compile --check``; design §4.2 lines 318-327). The
carve-out is conservative (ExecPlan D-CARVE): an *absent* sole-failure compile
stays exit ``1``, because an absent compile must not be reported as a regenerable
stale one (preserving the 3.1.1 B1 soundness fix). The
``compiled_path.exists()`` stat is the read-only mechanism distinguishing a
stale-present compile from an absent one, since :class:`DoneClauses` carries only
the six booleans and cannot say *why* ``compile_consistent`` is false.

The body mirrors ``desloppify`` exactly: it reuses ``novel-state``'s boundary
helpers (``working_dir``, ``state_path``, ``_load_or_state_error``,
``STATE_INPUT_ERRORS``) so it resolves the same fixed ``working/`` tree and maps
load faults to the same exit-``3`` channel, and the app is built with the same
four flags so the shared :func:`novel_ralph_skill.contract.runner.run` wrapper
owns every exit and envelope.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands.novel_state import (
    STATE_INPUT_ERRORS,
    _draft_read_error,
    _load_or_state_error,
    state_path,
    working_dir,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import (
    CommandOutcome,
    make_contract_app,
)
from novel_ralph_skill.state import compiled_manuscript_path
from novel_ralph_skill.state.done_predicate import DoneClauses, evaluate_done

if typ.TYPE_CHECKING:
    from pathlib import Path

    import cyclopts


def _novel_done() -> CommandOutcome:
    """Evaluate the done predicate and return its :class:`CommandOutcome`.

    Resolves the fixed cwd-relative ``working/`` tree, loads ``state.toml`` (exit
    ``3`` on a bad state), evaluates the six §4.2 clauses against disk, and maps
    the verdict to one of three exit codes: ``ExitCode.SUCCESS`` (every clause
    holds), ``ExitCode.ACTIONABLE_FINDING`` (the sole unmet clause is a
    stale-*present* ``compiled.md`` — the 3.1.2 carve-out, regenerable by the
    harness), else ``ExitCode.BENIGN_NEGATIVE`` (a drafting clause is unmet, or the
    sole failure is an *absent* compile). ``result`` is the six per-clause booleans
    in design order; ``messages`` names the failed clause(s), distinguishing a
    *stale* compile from a *missing* one (A-4). This is a checker: it writes
    nothing on any path.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` when the novel is done; ``ExitCode.ACTIONABLE_FINDING``
        when the only obstacle is a stale-present compile; otherwise
        ``ExitCode.BENIGN_NEGATIVE`` naming the unmet clauses.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable, or a chapter
        artefact (including ``compiled.md`` or a ``draft.md``) is unreadable (the
        exit-``3`` state-error channel).
    """
    root = working_dir()
    state = _load_or_state_error(state_path())
    try:
        clauses = evaluate_done(state, root)
    except STATE_INPUT_ERRORS as exc:
        # The draft/compiled read fault routes through the shared
        # ``_draft_read_error`` formatter so the six draft-read boundaries emit
        # one actionable message naming the ``working/`` tree (roadmap §6.3.5).
        raise _draft_read_error(root) from exc
    if clauses.all_hold:
        return CommandOutcome(
            code=ExitCode.SUCCESS,
            result=clauses.as_result(),
            messages=["novel is done"],
        )
    if _sole_stale_compile(clauses, root):
        return CommandOutcome(
            code=ExitCode.ACTIONABLE_FINDING,
            result=clauses.as_result(),
            messages=["compile_consistent is false (stale compile; regenerate)"],
        )
    return CommandOutcome(
        code=ExitCode.BENIGN_NEGATIVE,
        result=clauses.as_result(),
        messages=[
            _failed_clause_message(name, root) for name in clauses.failed_clause_names
        ],
    )


def _failed_clause_message(name: str, root: Path) -> str:
    """Return the human ``messages`` line for one failed clause name.

    For ``compile_consistent`` the line distinguishes a *missing* ``compiled.md``
    (the absent sole-failure case that stays exit ``1``) from any other cause, so
    human-mode output is not misleading at the carve-out boundary (A-4); every
    other clause renders the plain ``"<name> is false"`` line. The harness never
    parses ``messages`` (ADR-003).
    """
    if name == "compile_consistent" and not compiled_manuscript_path(root).exists():
        return "compile_consistent is false (compiled.md missing)"
    return f"{name} is false"


def build_app() -> cyclopts.App:
    """Build the ``novel-done`` Cyclopts app (design §4.2).

    Built via :func:`novel_ralph_skill.contract.runner.make_contract_app`, which
    owns the four-flag contract so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope,
    exactly like ``novel-state`` and ``desloppify``. The single default body
    takes no arguments and returns a
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome`.

    Returns
    -------
    cyclopts.App
        The configured ``novel-done`` app.
    """
    app = make_contract_app("novel-done")

    @app.default
    def _check() -> CommandOutcome:
        """Evaluate the done predicate; exit 0/1 per the §4.2 clauses."""
        return _novel_done()

    return app


def _sole_stale_compile(clauses: DoneClauses, root: Path) -> bool:
    """Return whether the sole unmet clause is a stale-*present* ``compiled.md``.

    The conservative exit-``4`` carve-out predicate (ExecPlan D-CARVE): ``True``
    iff ``compile_consistent`` is the *only* false clause **and**
    ``manuscript/compiled.md`` exists. An *absent* sole-failure compile is
    excluded, so it stays exit ``1`` (an absent compile is not a regenerable stale
    one; this preserves the 3.1.1 B1 soundness fix). The ``exists`` stat is a
    read-only ``pathlib`` call and is the only way the command body can tell a
    stale-present compile from an absent one, since :class:`DoneClauses` carries
    only the six booleans.
    """
    if clauses.failed_clause_names != ("compile_consistent",):
        return False
    return compiled_manuscript_path(root).exists()
