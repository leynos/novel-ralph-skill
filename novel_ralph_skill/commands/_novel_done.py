"""The ``novel-done`` command body and its Cyclopts app (design §4.2).

``novel-done`` is the read-only done predicate as a console-script: it loads the
fixed ``working/state.toml``, evaluates the six §4.2 clauses against disk through
:func:`novel_ralph_skill.state.done_predicate.evaluate_done`, and projects the
per-clause result into the shared envelope. It writes nothing on any path
(ADR-001; design §3.3 puts ``novel-done`` in the read-only checker column) and
takes no positional or keyword arguments.

The exit-code contract (design §3.2): exit ``0`` when every clause holds, exit
``1`` (the benign "not yet done" the harness loops on) when any clause is false,
exit ``3`` when ``state.toml`` is missing/unparseable or a chapter artefact is
unreadable, and exit ``2`` (the runner's ``CycloptsError`` arm) on a usage error.
No 3.1.1 path produces exit ``4``: the ``compile_consistent`` clause reports
existence only (ExecPlan D-COMPILE-EXISTENCE) and the exit-``4`` compile-divergence
carve-out lands with roadmap task 3.1.2.

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
    _load_or_state_error,
    state_path,
    working_dir,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import (
    CommandOutcome,
    StateInputError,
    make_contract_app,
)
from novel_ralph_skill.state.done_predicate import evaluate_done

if typ.TYPE_CHECKING:
    import cyclopts


def _novel_done() -> CommandOutcome:
    """Evaluate the done predicate and return its :class:`CommandOutcome`.

    Resolves the fixed cwd-relative ``working/`` tree, loads ``state.toml`` (exit
    ``3`` on a bad state), evaluates the six §4.2 clauses against disk, and builds
    the outcome: ``result`` is the per-clause booleans in design order; ``code``
    is ``ExitCode.SUCCESS`` when every clause holds, else
    ``ExitCode.BENIGN_NEGATIVE``; ``messages`` names the failed clauses or reports
    the novel is done. This is a checker: it writes nothing on any path.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with the all-true ``result`` when the novel is done,
        or ``ExitCode.BENIGN_NEGATIVE`` naming the unmet clauses.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable, or a chapter
        artefact is unreadable (the exit-``3`` state-error channel).
    """
    root = working_dir()
    state = _load_or_state_error(state_path())
    try:
        clauses = evaluate_done(state, root)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot evaluate the done predicate under {root}: {exc}"
        raise StateInputError(msg) from exc
    if clauses.all_hold:
        return CommandOutcome(
            code=ExitCode.SUCCESS,
            result=clauses.as_result(),
            messages=["novel is done"],
        )
    return CommandOutcome(
        code=ExitCode.BENIGN_NEGATIVE,
        result=clauses.as_result(),
        messages=[f"{name} is false" for name in clauses.failed_clause_names],
    )


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
