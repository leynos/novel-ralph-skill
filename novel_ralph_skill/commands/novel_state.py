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

The read-only ``check`` subcommand validates the §5.2 pure-state invariants
(roadmap task 2.1.2) without writing (the checker half of the §5.4
checker/mutator split). It loads ``./working/state.toml`` relative to the process
cwd, applies :func:`novel_ralph_skill.state.validate_state`, and returns a
:class:`~novel_ralph_skill.contract.runner.CommandOutcome`: exit ``0`` with an
empty ``result.violations`` when the state is coherent, or exit ``4``
(``ACTIONABLE_FINDING``) naming the violated invariants when it is not. A
missing or unparseable ``state.toml`` raises
:class:`~novel_ralph_skill.contract.runner.StateInputError` for the exit-``3``
state-error channel. The disk-evidence invariants (§5.4) are task 2.3.2's and
are not checked here.

The ``init`` mutator (roadmap task 2.2.2) is the *create* command: it bootstraps
``working/`` and a coherent initial ``state.toml`` (refusing to overwrite an
existing one). Its ``set-cursor`` and ``advance-phase`` siblings — the two
mutators that load, edit, and re-write an existing ``state.toml`` — live in
:mod:`novel_ralph_skill.commands._state_mutators` and are registered here; the
remaining mutators (``recount``/``reconcile``) are later tasks.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import tomllib
import typing as typ

import cyclopts

from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import (
    build_initial_document,
    load_state,
    validate_state,
    write_document_atomically,
)

if typ.TYPE_CHECKING:
    from novel_ralph_skill.state import State

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

# The fixed cwd-relative working directory the design records (design line 151);
# the same constant the entry point stamps into the ``RunContext.working_dir``,
# so the file ``check`` reads and the envelope's ``working_dir`` field cannot
# drift (Decision Log B4/B5). There is no ``--working-dir`` flag.
WORKING_DIR_NAME = "working"

# The exceptions a missing or malformed ``state.toml`` raises through
# ``load_state``; each is translated to ``StateInputError`` (the exit-``3``
# state-error channel). Named once here so the "what counts as a state-input
# error" vocabulary has a single home the four later mutators reuse, and so the
# corpus test can pin its own parse-error list against this set rather than
# hand-listing it independently (audit:2.1.2 finding 4).
STATE_INPUT_ERRORS: tuple[type[Exception], ...] = (
    OSError,
    tomllib.TOMLDecodeError,
    KeyError,
    ValueError,
    TypeError,
)


def _load_or_state_error(path: pathlib.Path) -> State:
    """Load ``path`` into a ``State``, translating load faults to ``StateInputError``.

    Owns the load-and-translate boundary so callers read as "load → validate →
    build outcome": it maps every member of :data:`STATE_INPUT_ERRORS` to a
    :class:`~novel_ralph_skill.contract.runner.StateInputError` (the exit-``3``
    state-error channel) and lets a coherent load return the parsed ``State``
    unchanged. Reusable by the four later mutators that hit the same boundary.

    Parameters
    ----------
    path : pathlib.Path
        The ``state.toml`` to load.

    Returns
    -------
    State
        The parsed, typed state.

    Raises
    ------
    StateInputError
        When ``path`` is missing or unparseable.
    """
    try:
        return load_state(path)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot load {path}: {exc}"
        raise StateInputError(msg) from exc


def _check() -> CommandOutcome:
    """Validate ``./working/state.toml`` against the §5.2 pure-state invariants.

    Reads the fixed cwd-relative ``working/state.toml`` (design line 151),
    parses it, and applies :func:`novel_ralph_skill.state.validate_state`. A
    coherent state returns exit ``0``; a violation returns exit ``4`` naming the
    breached invariants in ``result.violations``. This is a checker: it writes
    nothing (design §3.3).

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with an empty ``violations`` list when coherent, or
        ``ExitCode.ACTIONABLE_FINDING`` naming the violated invariants.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable (the exit-``3``
        state-error channel).
    """
    path = pathlib.Path(WORKING_DIR_NAME) / "state.toml"
    state = _load_or_state_error(path)
    verdict = validate_state(state)
    # One verdict-driven constructor: an empty verdict is success, any violation
    # is an actionable finding. Computing the verdict once and projecting it into
    # a single outcome makes "empty verdict means success" a single expression
    # rather than two parallel constructors (audit:2.1.2 finding 5).
    code = ExitCode.SUCCESS if not verdict else ExitCode.ACTIONABLE_FINDING
    return CommandOutcome(
        code=code,
        result={"violations": [violation.invariant for violation in verdict]},
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
    working = pathlib.Path(WORKING_DIR_NAME)
    state_path = working / "state.toml"
    if state_path.exists():
        msg = f"refusing to overwrite existing {state_path}"
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
    write_document_atomically(document, state_path)
    # ``log.md`` is the turn log (state-layout.md "Initialisation" step 3); it is
    # not ``state.toml``, so the direct-edit guard does not apply to it.
    (working / "log.md").write_text("", encoding="utf-8")
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"working_dir": WORKING_DIR_NAME, "slug": slug},
        messages=[f"initialised {state_path}"],
    )


def build_app() -> cyclopts.App:
    """Build the ``novel-state`` Cyclopts app with its subcommands.

    Wired with ``result_action="return_value", exit_on_error=False,
    print_error=False, help_on_error=False`` so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope
    (the ``wrapper_app`` fixture's contract). Exposes the read-only ``check``
    subcommand, the ``init`` builder-mutator (roadmap task 2.2.2), the
    ``set-cursor`` and ``advance-phase`` mutators (task 2.2.2), and the
    ``recount`` mutator (task 2.3.1); the remaining ``reconcile`` mutator lands in
    a later task.

    The signature is deliberately zero-argument and stable (later tasks import
    it): each body resolves its working directory from the process cwd (the fixed
    ``working/`` constant, Decision Log B4/B5), so the builder needs no
    per-invocation value to close over. There is no working-directory parameter
    and no Cyclopts working-dir option.

    Returns
    -------
    cyclopts.App
        The configured ``novel-state`` app exposing ``check``, ``init``,
        ``set-cursor``, ``advance-phase``, and ``recount``.
    """
    # Imported inside the builder, not at module top: the mutator module imports
    # ``STATE_INPUT_ERRORS``/``WORKING_DIR_NAME`` from this module, so a top-level
    # import would be circular. The builder runs after both modules are defined.
    from novel_ralph_skill.commands import _state_mutators as mutators

    app = cyclopts.App(
        name="novel-state",
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )

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

    return app
