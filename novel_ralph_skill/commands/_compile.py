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
undecodable ``draft.md`` is likewise exit ``3``. This is the write path only;
the ``--check`` divergence checker and the compile-and-hash routine are roadmap
tasks 4.1.2 and 3.1.2 (ExecPlan D-SCOPE).
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
from novel_ralph_skill.state import (
    concatenate_drafts,
    present_draft_bodies,
    write_text_atomically,
)

if typ.TYPE_CHECKING:
    import cyclopts

# The working-relative ``compiled.md`` path, named once so the written file, the
# success ``result``, and the human message cannot drift (design §4.3). It is the
# working-relative token rather than an absolute path so the envelope is
# deterministic for snapshotting (ExecPlan D-RESULT; AGENTS.md snapshot rule).
_COMPILED_REL = "working/manuscript/compiled.md"


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
    if not state.chapters:
        # An absent or empty manifest has no authoritative ordering, so there is
        # nothing to compile; refuse rather than write an empty compiled.md.
        msg = "cannot compile: chapter manifest is absent or empty"
        raise StateInputError(msg)
    root = working_dir()
    try:
        bodies = present_draft_bodies(state, root)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot read chapter drafts: {exc}"
        raise StateInputError(msg) from exc
    rendered = concatenate_drafts(bodies)
    compiled_path = root / "manuscript" / "compiled.md"
    try:
        write_text_atomically(rendered, compiled_path)
    except STATE_INPUT_ERRORS as exc:
        # An absent manuscript/ directory raises FileNotFoundError (an OSError),
        # routed to exit 3 rather than escaping to the benign exit 1.
        msg = f"cannot write {_COMPILED_REL}: {exc}"
        raise StateInputError(msg) from exc
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={
            "compiled": _COMPILED_REL,
            "chapters": len(state.chapters),
            "bytes": len(rendered.encode("utf-8")),
        },
        messages=[f"compiled {len(state.chapters)} chapters into {_COMPILED_REL}"],
    )


def build_app() -> cyclopts.App:
    """Build the ``novel-compile`` Cyclopts app (design §4.3; ADR-005).

    ``novel-compile`` maps 1:1 onto one deterministic operation, so the app
    exposes a single default callback (the write) rather than a subcommand
    multiplexer (the ``--check`` flag is roadmap task 4.1.2; ExecPlan D-SCOPE).
    Built via :func:`novel_ralph_skill.contract.runner.make_contract_app`, which
    owns the four-flag contract so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope,
    exactly like ``desloppify``.

    Returns
    -------
    cyclopts.App
        The configured ``novel-compile`` app.
    """
    app = make_contract_app("novel-compile")

    @app.default
    def _compile() -> CommandOutcome:
        """Concatenate the chapter drafts into ``compiled.md``; exit 0/3."""
        return compile_manuscript()

    return app
