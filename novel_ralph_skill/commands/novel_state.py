"""The ``novel-state`` subcommand app and its working directory.

This module hosts the ``novel-state`` Cyclopts app (design §4.1) and its
``WORKING_DIR_NAME`` default. It is the first command on the real ``run`` path,
so the conventions it sets — reading state from the fixed cwd-relative
``working/`` directory (design line 151) — are the ones the four later commands
inherit. The command-agnostic ``--human`` pre-parse the entry point performs
before :func:`novel_ralph_skill.contract.runner.run` is reached no longer lives
here; it is the shared
:func:`novel_ralph_skill.contract.parse_global_flags` splitter (ADR-003 §3.1),
which every command imports from the contract package rather than from a sibling
command module.

The read-only ``check`` subcommand is **disk-aware** (roadmap task 2.3.2): it
validates the §5.2 pure-state invariants (task 2.1.2) **and** the §5.4
disk-evidence invariants (this task) without writing (the checker half of the
§5.4 checker/mutator split). It loads ``./working/state.toml`` relative to the
process cwd, applies :func:`novel_ralph_skill.state.validate_state` and
:func:`novel_ralph_skill.state.check_disk_evidence`, and returns a
:class:`~novel_ralph_skill.contract.runner.CommandOutcome`: exit ``0`` with an
empty ``result.violations`` when the state is coherent, or exit ``4``
(``ACTIONABLE_FINDING``) naming the violated invariants when it is not. When disk
evidence fired it attaches the implied
:func:`~novel_ralph_skill.state.derive_reconciliation` to
``result.reconciliation`` (reported, never enacted — ``check`` writes nothing). A
missing or unparseable ``state.toml`` — or an unreadable chapter ``draft.md`` —
raises :class:`~novel_ralph_skill.contract.runner.StateInputError` for the
exit-``3`` state-error channel.

The ``init`` mutator (roadmap task 2.2.2) is the *create* command: it bootstraps
``working/`` and a coherent initial ``state.toml`` (refusing to overwrite an
existing one). The load-edit-rewrite mutators live in sibling modules and are
registered here: ``set-cursor``/``advance-phase``
(:mod:`~novel_ralph_skill.commands._state_mutators`), ``recount``
(:mod:`~novel_ralph_skill.commands._recount`), ``reconcile``
(:mod:`~novel_ralph_skill.commands._reconcile`), ``set-chapters``
(:mod:`~novel_ralph_skill.commands._set_chapters`), and the four gate/drafting
mutators (:mod:`~novel_ralph_skill.commands._gate_drafting_mutators`, task 2.2.4).
"""

from __future__ import annotations

import datetime as dt
import typing as typ

# ``ChapterPlanEntry`` is imported as a *runtime* module global (not under
# ``TYPE_CHECKING``) because Cyclopts resolves the ``list[ChapterPlanEntry]``
# annotation of the ``set-chapters`` subcommand against this function's module
# ``__globals__`` (``get_type_hints``). It lives in a dependency-free leaf module,
# so this import does not create the ``_set_chapters`` -> ``_state_mutators`` ->
# ``novel_state`` cycle a direct ``_set_chapters`` import would.
from novel_ralph_skill.commands._chapter_plan_entry import (
    ChapterPlanEntry,  # noqa: TC001 - runtime global for Cyclopts annotation resolution
)

# The ``working/state.toml`` load boundary lives in a dependency-free leaf module
# (``_state_load``) so this command module stays within the 400-line cap. These
# symbols are re-exported here so every command — and ``_state_mutators`` — keeps
# importing them from ``novel_state``; ``__all__`` marks the re-export so the
# unused-import lint does not fire on the ones this module does not call directly.
from novel_ralph_skill.commands._state_load import (
    STATE_INPUT_ERRORS,
    WORKING_DIR_NAME,
    _load_or_state_error,
    _state_input_error,
    resolved_working_dir,
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
    build_initial_document,
    check_disk_evidence,
    derive_reconciliation,
    validate_state,
    write_document_atomically,
)

__all__ = [
    "STATE_INPUT_ERRORS",
    "WORKING_DIR_NAME",
    "_load_or_state_error",
    "_state_input_error",
    "build_app",
    "resolved_working_dir",
    "state_path",
    "working_dir",
]

if typ.TYPE_CHECKING:
    import pathlib

    import cyclopts

    from novel_ralph_skill.state import Reconciliation, State, Violation

# The Initialisation directory skeleton ``init`` creates beside ``state.toml``,
# sourced verbatim from state-layout.md "Initialisation" step 1
# (``mkdir -p working/{characters,world,reader,plan,manuscript,reviews}``); the
# later prose-writing phases land their artefacts here (ExecPlan Decision Log;
# round-2 blocking point BR2-2).
_INIT_SUBDIRECTORIES: tuple[str, ...] = (
    "characters",
    "world",
    "reader",
    "plan",
    "manuscript",
    "reviews",
)

# The default novel target word count when ``init`` is given none, matching
# state-layout.md "Initialisation" ("default 80000").
_DEFAULT_TARGET_WORD_COUNT = 80000


def _render_reconciliation(reconciliation: Reconciliation) -> dict[str, object]:
    """Render a :class:`Reconciliation` as the read-only ``check`` payload.

    ``check`` reports the reconciliation a stale ``state.toml`` *implies* without
    enacting it (design §3.3, §5.4): the action name, the discrepancy names that
    drove it, and the human detail, plus the disk-derived counts for a ``recount``
    so an operator can see exactly what ``reconcile`` would write. It carries no
    write-shaped success vocabulary — ``check`` writes nothing.
    """
    payload: dict[str, object] = {
        "action": str(reconciliation.action),
        "discrepancies": list(reconciliation.discrepancies),
        "detail": reconciliation.detail,
    }
    if reconciliation.recounted_by_chapter is not None:
        payload["current"] = reconciliation.recounted_current
        payload["by_chapter"] = dict(reconciliation.recounted_by_chapter)
    return payload


def _disk_evidence_or_state_error(
    state: State, working_dir: pathlib.Path
) -> tuple[Violation, ...]:
    """Run the §5.4 disk-evidence detector, mapping read faults to exit ``3``.

    :func:`~novel_ralph_skill.state.check_disk_evidence` reads each chapter's
    ``draft.md``; an absent draft is benign (counted ``0``), but every other read
    fault — an undecodable body (``UnicodeDecodeError``), a ``PermissionError`` —
    propagates. Wrapping it under ``STATE_INPUT_ERRORS`` routes those to the
    exit-``3`` state-error channel rather than letting them escape to exit ``1``,
    exactly as the ``recount`` mutator wraps the same reader. It passes
    ``relax_drafting_bijection=True`` so the user-facing checker relaxes the
    manifest-disk bijection during drafting (ADR 009; see :func:`_check`).
    """
    try:
        return check_disk_evidence(state, working_dir, relax_drafting_bijection=True)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot read disk evidence under {working_dir}: {exc}"
        raise StateInputError(msg) from exc


def _check() -> CommandOutcome:
    """Validate ``./working/state.toml`` against the §5.2 and §5.4 invariants.

    Reads the fixed cwd-relative ``working/state.toml`` (design line 151), parses
    it, applies :func:`novel_ralph_skill.state.validate_state` (the §5.2 pure-state
    invariants) **and** :func:`novel_ralph_skill.state.check_disk_evidence` (the
    §5.4 disk-evidence invariants), and unions the verdicts into
    ``result.violations``. When any disk-evidence violation fired, it attaches the
    :func:`~novel_ralph_skill.state.derive_reconciliation` result to
    ``result.reconciliation`` so an operator sees the repair a stale tree implies.
    A coherent state returns exit ``0``; any violation returns exit ``4``. This is
    a checker: it writes nothing on any path (design §3.3).

    During drafting the disk-evidence pass relaxes the manifest-disk bijection to
    disk-subset-of-manifest (ADR 009): a mid-draft tree whose on-disk chapters lag
    the manifest exits ``0``, but an orphan directory or a manifest gap still
    exits ``4``.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with an empty ``violations`` list when coherent, or
        ``ExitCode.ACTIONABLE_FINDING`` naming the violated invariants (and a
        ``reconciliation`` payload when disk evidence fired).

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable, or a chapter
        ``draft.md`` is unreadable (the exit-``3`` state-error channel).
    """
    root = working_dir()
    state = _load_or_state_error(state_path())
    pure_state = validate_state(state)
    disk_evidence = _disk_evidence_or_state_error(state, root)
    verdict = (*pure_state, *disk_evidence)
    result: dict[str, object] = {
        "violations": [violation.invariant for violation in verdict]
    }
    if disk_evidence:
        result["reconciliation"] = _render_reconciliation(
            derive_reconciliation(state, root)
        )
    # One verdict-driven constructor: an empty verdict is success, any violation
    # is an actionable finding (audit:2.1.2 finding 5).
    code = ExitCode.SUCCESS if not verdict else ExitCode.ACTIONABLE_FINDING
    return CommandOutcome(
        code=code,
        result=result,
        messages=[violation.detail for violation in verdict] or ["state is coherent"],
    )


def _init(*, title: str, slug: str, target_word_count: int) -> CommandOutcome:
    """Create ``working/`` and a fresh, coherent ``state.toml`` (design §4.1).

    Refuses with exit ``3`` when ``working/state.toml`` already exists rather
    than overwriting a live project (ExecPlan Decision Log D1; state-layout.md
    "Working directory hygiene"). Otherwise it creates ``working/`` and the
    Initialisation directory skeleton, writes a fresh document built by
    :func:`~novel_ralph_skill.state.build_initial_document` through the sanctioned
    atomic writer, and creates an empty ``log.md``. Directory creation is
    idempotent, so a partially-present ``working/`` does not crash.

    Parameters
    ----------
    title : str
        The novel title, stored verbatim in ``[novel].title``.
    slug : str
        The project slug, stored verbatim in ``[novel].slug``.
    target_word_count : int
        The novel target word count for ``[novel]`` and ``[word_counts]``.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the tree is bootstrapped.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` already exists (the exit-``3`` refusal).
    """
    working = working_dir()
    path = state_path()
    if path.exists():
        msg = f"refusing to overwrite existing {path}"
        raise StateInputError(msg)
    working.mkdir(parents=True, exist_ok=True)
    for name in _INIT_SUBDIRECTORIES:
        (working / name).mkdir(parents=True, exist_ok=True)
    created_at = dt.datetime.now(dt.UTC).isoformat()
    document = build_initial_document(
        title=title,
        slug=slug,
        target_word_count=target_word_count,
        created_at=created_at,
    )
    write_document_atomically(document, path)
    # ``log.md`` is the turn log (state-layout.md "Initialisation" step 3); it is
    # not ``state.toml``, so the direct-edit guard does not apply to it.
    (working / "log.md").write_text("", encoding="utf-8")
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        # The body names the absolute, resolved path where ``init`` created the
        # tree, not the bare ``"working"`` token, so an agent gating on the body
        # sees a misresolution rather than a silent constant (roadmap §6.3.4;
        # Decision Log D6).
        result={"working_dir": str(resolved_working_dir()), "slug": slug},
        messages=[f"initialised {path}"],
    )


def build_app() -> cyclopts.App:
    """Build the ``novel-state`` Cyclopts app with its subcommands.

    Built via :func:`novel_ralph_skill.contract.runner.make_contract_app`, which
    owns the four-flag contract so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope.
    Exposes the read-only ``check`` subcommand, the ``init`` builder-mutator (task
    2.2.2), the ``set-cursor``/``advance-phase`` mutators (task 2.2.2), ``recount``
    (task 2.3.1), ``reconcile`` (task 2.3.2), the ``set-chapters`` chapter-manifest
    mutator (task 2.2.3), and the gate/drafting mutators ``set-gate``,
    ``complete-final-pass``, ``set-fangirl``, and ``set-critic-pass`` (task 2.2.4),
    the last four registered via
    :func:`novel_ralph_skill.commands._gate_drafting_mutators.register_gate_drafting_commands`.

    The signature is deliberately zero-argument and stable (later tasks import
    it): each body resolves its working directory from the fixed ``working/``
    constant (Decision Log B4/B5), so the builder exposes no working-dir option.

    Returns
    -------
    cyclopts.App
        The app exposing the read ``check`` query and every mutator named above.
    """
    # Imported inside the builder, not at module top: the mutator modules import
    # from this module, so a top-level import would be circular (the builder runs
    # after both are defined). The task-2.2.4 registrar call below is deferred too.
    from novel_ralph_skill.commands import _state_mutators as mutators

    app = make_contract_app("novel-state")

    @app.command
    def check() -> CommandOutcome:
        """Validate the §5.2 pure-state invariants without writing (design §4.1)."""
        return _check()

    @app.command
    def init(
        *,
        title: str,
        slug: str,
        target_word_count: int = _DEFAULT_TARGET_WORD_COUNT,
    ) -> CommandOutcome:
        """Create ``working/`` and an initial ``state.toml`` (design §4.1)."""
        return _init(title=title, slug=slug, target_word_count=target_word_count)

    @app.command
    def set_cursor(*, chapter: int, scene: int = 0, beat: int = 0) -> CommandOutcome:
        """Set the drafting cursor; refuse an incoherent cursor with exit 3."""
        return mutators.set_cursor(chapter=chapter, scene=scene, beat=beat)

    @app.command
    def advance_phase() -> CommandOutcome:
        """Advance ``phase.current`` to the next member; refuse skips with exit 3."""
        return mutators.advance_phase()

    @app.command
    def recount() -> CommandOutcome:
        """Re-derive ``[word_counts]`` from the chapter drafts; refuse with exit 3."""
        from novel_ralph_skill.commands import _recount

        return _recount.recount()

    @app.command
    def reconcile() -> CommandOutcome:
        """Write the disk-authoritative reconciliation; log it; exit 0/4."""
        from novel_ralph_skill.commands import _reconcile

        return _reconcile.reconcile()

    @app.command(name="set-chapters")
    def set_chapters(*, chapters: list[ChapterPlanEntry]) -> CommandOutcome:
        """Populate [chapters] from the agent's plan; refuse an incoherent plan."""
        from novel_ralph_skill.commands import _set_chapters

        return _set_chapters.set_chapters(chapters=chapters)

    from novel_ralph_skill.commands import _gate_drafting_mutators

    _gate_drafting_mutators.register_gate_drafting_commands(app)
    return app
