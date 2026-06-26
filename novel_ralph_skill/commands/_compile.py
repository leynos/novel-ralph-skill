"""The ``novel-compile`` write body (roadmap task 4.1.1; design §4.3).

``novel-compile`` regenerates the whole-novel manuscript by concatenating the
chapter drafts in zero-padded chapter-index order and writing
``working/manuscript/compiled.md`` atomically. It is a deterministic *mutator*:
identical drafts and manifest always produce a byte-identical ``compiled.md``
regardless of directory-listing order, because the order *is* the ascending
``[chapters]`` manifest chapter number (design §4.3; ExecPlan Constraints
"Ordering is the zero-padded chapter index").

The write path reuses the one production join rule
(:func:`~novel_ralph_skill.state.concatenate_drafts` / ``DRAFT_SEPARATOR``) and
the one draft-body read rule
(:func:`~novel_ralph_skill.state.present_draft_bodies`) that the §5.4
``compiled-matches-drafts`` disk-evidence invariant recomputes, so a freshly
compiled tree is coherent under ``novel-state check`` by construction (ExecPlan
Risk "output diverges from compiled-matches-drafts"; D-READ).

It writes exactly one file, already atomic via ``Path.replace``, so it opens no
``[pending_turn]`` bracket — exactly like ``recount``/``set-cursor``/
``advance-phase`` (design §3.4; ExecPlan D-PT). An absent or empty ``[chapters]``
manifest has no authoritative ordering, so the command refuses with exit ``3``
and writes nothing (design §10 lines 811-815; ExecPlan D-EMPTY); a missing or
unparseable ``state.toml``, an absent ``working/`` tree, or an unreadable/
undecodable ``draft.md`` is likewise exit ``3``.

The module also hosts the ``--check`` read-only divergence checker
(:func:`check_compiled`; roadmap task 4.1.2; design §4.3). With ``--check``,
``novel-compile`` is a *checker*: it reads ``state.toml`` and the manuscript
tree, reports whether ``compiled.md`` is the ordered concatenation of the present
drafts, **writes nothing on any path**, and exits ``4`` (an actionable finding)
when the compile is stale or absent so the agent knows to regenerate (design
§3.3 checker/mutator table; ADR-001). The two modes share the verdict site
:func:`~novel_ralph_skill.state.compiled_matches_drafts` with the ``novel-done``
``compile_consistent`` clause, so the command-line surface and the done clause
cannot disagree about whether ``compiled.md`` is current (ExecPlan
D-POLARITY/D-BYTE-COMPARE).
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
    StateInputError,
    make_contract_app,
)
from novel_ralph_skill.state import (
    COMPILED_REL,
    compile_is_current,
    compiled_manuscript_path,
    compiled_matches_drafts,
    concatenate_drafts,
    present_draft_bodies,
    write_text_atomically,
)

if typ.TYPE_CHECKING:
    import cyclopts

    from novel_ralph_skill.state.schema import State


def _require_chapter_manifest(state: State) -> None:
    """Refuse an absent or empty ``[chapters]`` manifest with exit ``3``.

    An absent or empty manifest has no authoritative ordering, so neither the
    write path nor the ``--check`` checker can act on it; both refuse with the
    identical exit-``3`` :class:`StateInputError` *before* any read, so the two
    modes' state-error boundary cannot drift (design §10; ExecPlan D-EMPTY).

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` carrying the ``[chapters]`` manifest.

    Raises
    ------
    StateInputError
        When ``state.chapters`` is empty (the exit-``3`` channel).
    """
    if not state.chapters:
        msg = "cannot compile: chapter manifest is absent or empty"
        raise StateInputError(msg)


def compile_manuscript() -> CommandOutcome:
    """Concatenate the chapter drafts into ``compiled.md``; refuse with exit ``3``.

    Loads ``working/state.toml`` through ``novel-state``'s shared exit-``3``
    boundary, refuses an absent/empty ``[chapters]`` manifest (no authoritative
    ordering; design §10, ExecPlan D-EMPTY), reads each manifest chapter's
    ``draft.md`` in ascending chapter order via the shared
    :func:`~novel_ralph_skill.state.present_draft_bodies` rule, joins them with
    the production ``DRAFT_SEPARATOR`` via
    :func:`~novel_ralph_skill.state.concatenate_drafts`, and writes
    ``working/manuscript/compiled.md`` atomically. An absent ``draft.md``
    contributes the empty string; every other read fault (an undecodable body, a
    permission error, an absent ``manuscript/``) is re-raised as
    :class:`~novel_ralph_skill.contract.runner.StateInputError` under the shared
    ``STATE_INPUT_ERRORS`` tuple, so it reaches exit ``3`` and cannot escape to
    the benign exit ``1`` — mirroring ``_recount._recount_or_state_error``.

    The success ``result`` names what the mutator changed — the written path, the
    chapter count, and the byte length — and carries no ``violations`` read shape
    (design §3.3; ExecPlan D-RESULT). The write reuses the production join and
    read rules the ``compiled-matches-drafts`` invariant recomputes, so a freshly
    compiled tree is coherent under ``novel-state check`` (ExecPlan D-READ).

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once ``compiled.md`` is written, carrying
        ``{"compiled", "chapters", "bytes"}`` in ``result``.

    Raises
    ------
    StateInputError
        When ``state.toml`` is missing/unparseable, the ``[chapters]`` manifest
        is absent or empty, a chapter's ``draft.md`` is unreadable or undecodable,
        or ``working/manuscript/`` is absent (each the exit-``3`` channel).
    """
    state = _load_or_state_error(state_path())
    _require_chapter_manifest(state)
    root = working_dir()
    try:
        bodies = present_draft_bodies(state, root)
    except STATE_INPUT_ERRORS as exc:
        # The draft read fault routes through the shared ``_draft_read_error``
        # formatter so the six draft-read boundaries emit one actionable message
        # naming the ``working/`` tree (roadmap §6.3.5).
        raise _draft_read_error(root, exc) from exc
    rendered = concatenate_drafts(bodies)
    compiled_path = compiled_manuscript_path(root)
    try:
        write_text_atomically(rendered, compiled_path)
    except STATE_INPUT_ERRORS as exc:
        # An absent manuscript/ directory raises FileNotFoundError (an OSError),
        # routed to exit 3 rather than escaping to the benign exit 1. This is a
        # *write* fault, deliberately kept out of the draft-read formatter's scope
        # (ExecPlan Decision D6): it wants a write-shaped remedy, not the
        # inspect-the-draft remedy ``_draft_read_error`` emits.
        msg = f"cannot write {COMPILED_REL}: {exc}"
        raise StateInputError(msg) from exc
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={
            "compiled": COMPILED_REL,
            "chapters": len(state.chapters),
            "bytes": len(rendered.encode("utf-8")),
        },
        messages=[f"compiled {len(state.chapters)} chapters into {COMPILED_REL}"],
    )


def check_compiled() -> CommandOutcome:
    """Report whether ``compiled.md`` matches the drafts; write nothing.

    The read-only half of ``novel-compile`` (roadmap task 4.1.2; design §4.3).
    It loads ``state.toml`` through ``novel-state``'s shared exit-``3`` boundary,
    refuses an absent/empty ``[chapters]`` manifest with the identical exit-``3``
    :class:`StateInputError` the write path uses (via the shared
    :func:`_require_chapter_manifest` guard), then reads the divergence verdict
    from the single production site
    :func:`~novel_ralph_skill.state.compiled_matches_drafts` — the same routine
    the ``novel-done`` ``compile_consistent`` clause consumes, so the two cannot
    disagree on whether ``compiled.md`` is current (ExecPlan Constraints "share
    one comparison routine"; D-BYTE-COMPARE).

    The verdict is projected to the ``compile_consistent`` polarity: only
    :attr:`~novel_ralph_skill.state.CompiledComparison.MATCHES` is satisfied
    (exit ``0``); both :attr:`~CompiledComparison.ABSENT` and
    :attr:`~CompiledComparison.DIVERGES` are actionable findings (exit ``4``),
    because an absent ``compiled.md`` is equally "not current — regenerate it"
    (ExecPlan D-POLARITY). This is the **opposite** polarity to the §5.4
    ``novel-state check`` disk-evidence detector (absent = vacuously satisfied);
    both are reconciled inside the one shared helper.

    The body never calls ``write_text_atomically`` and never reaches the write
    branch, so it writes nothing on any path (ADR-001; ExecPlan R-NOWRITE). The
    success ``result`` carries the checker-shaped keys ``checked``/``chapters``/
    ``diverged`` and no write keys; ``diverged`` is the bounded boolean datum, not
    a per-chapter enumeration (design §3.3; ExecPlan D-RESULT).

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with ``diverged=False`` when the verdict is
        ``MATCHES``; ``ExitCode.ACTIONABLE_FINDING`` with ``diverged=True`` when
        the verdict is ``ABSENT`` or ``DIVERGES``.

    Raises
    ------
    StateInputError
        When ``state.toml`` is missing/unparseable, the ``[chapters]`` manifest
        is absent or empty, or a chapter's ``draft.md``/``compiled.md`` is
        unreadable or undecodable (each the exit-``3`` channel).
    """
    state = _load_or_state_error(state_path())
    _require_chapter_manifest(state)
    try:
        verdict = compiled_matches_drafts(state, working_dir())
    except STATE_INPUT_ERRORS as exc:
        # ``check_compiled`` has no ``root`` local; pass ``working_dir()`` so the
        # shared ``_draft_read_error`` formatter names the same ``working/`` tree
        # the read targeted (roadmap §6.3.5).
        raise _draft_read_error(working_dir(), exc) from exc
    if compile_is_current(verdict):
        return CommandOutcome(
            code=ExitCode.SUCCESS,
            result={
                "checked": COMPILED_REL,
                "chapters": len(state.chapters),
                "diverged": False,
            },
            messages=[f"{COMPILED_REL} matches the chapter drafts"],
        )
    return CommandOutcome(
        code=ExitCode.ACTIONABLE_FINDING,
        result={
            "checked": COMPILED_REL,
            "chapters": len(state.chapters),
            "diverged": True,
        },
        messages=[
            (
                f"{COMPILED_REL} diverges from the chapter drafts; "
                "regenerate it with novel-compile"
            )
        ],
    )


def build_app() -> cyclopts.App:
    """Build the ``novel-compile`` Cyclopts app (design §4.3; ADR-005).

    ``novel-compile`` maps 1:1 onto one operation with two modes, so the app
    exposes a single default callback carrying a kw-only ``--check`` boolean
    rather than a subcommand multiplexer (design §4.3; ADR-005; ExecPlan D-FLAG).
    Built via :func:`novel_ralph_skill.contract.runner.make_contract_app`, which
    owns the four-flag contract so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope,
    exactly like ``desloppify``. Without ``--check`` the body writes
    ``compiled.md`` and exits ``0``; with ``--check`` it is the read-only
    divergence checker (:func:`check_compiled`), which writes nothing and exits
    ``4`` on a stale or absent compile.

    Returns
    -------
    cyclopts.App
        The configured ``novel-compile`` app.
    """
    app = make_contract_app("novel-compile")

    @app.default
    def _compile(*, check: bool = False) -> CommandOutcome:
        """Check or compile the chapter drafts; ``--check`` writes nothing."""
        return check_compiled() if check else compile_manuscript()

    return app
