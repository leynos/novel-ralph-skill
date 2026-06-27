"""The ``wordcount`` reporting command body (roadmap task 6.1.1; design §4.5).

``wordcount`` is a read-only checker (ADR-001): it reads the chapter drafts under
the fixed ``working/`` tree and the typed ``state.toml``, derives a per-chapter
and cumulative word-count report — words, percentage of target, distance to the
next knitting gate, the delta against the chapter target, and the 30/50/80%
gate triggers — and reports the finding without editing, judging, or mutating any
state. It writes nothing to disk.

This module owns two concerns, mirroring ``_desloppify.py`` and ``_recount.py``:
sourcing the novel target, the chapter manifest, and the on-disk drafted counts
from the ``working/`` tree (with the exit-``3`` state-fault routing); and wiring
the Cyclopts app and the
:class:`~novel_ralph_skill.contract.runner.CommandOutcome` that the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper renders. The pure report
derivation and its envelope projection live in the sibling
:mod:`novel_ralph_skill.commands._wordcount_report` so this module stays within
the 400-line cap (AGENTS.md "clear file boundaries").

The counting rule is the single one the corpus oracle is pinned to:
``wordcount`` recounts the drafts via
:func:`novel_ralph_skill.state.recount_words` rather than reading
``[word_counts].current`` blindly, because disk is authoritative (design §5.4;
ExecPlan Decision Log D-NUM). It introduces no second counter and no second
gate-threshold constant.

Fault routing follows the contract (design §3.2): a missing or unparseable
``state.toml``, an absent ``working/``, or an unreadable/undecodable ``draft.md``
is the exit-``3`` state channel (:class:`StateInputError`), exactly as
``_recount._recount_or_state_error`` and ``_desloppify.source_chapters`` route it.
``wordcount`` takes no command-specific argument in v1 (ExecPlan Decision Log
D-SCOPE), so the only usage fault is the shared Cyclopts unknown-option route to
exit ``2``, which the framework owns without a command-level error class.
"""

from __future__ import annotations

import pathlib
import typing as typ

from novel_ralph_skill.commands._wordcount_report import build_report, report_outcome
from novel_ralph_skill.commands.state_sourcing import (
    WORKING_DIR_NAME,
    draft_read_guard,
    load_or_state_error,
)
from novel_ralph_skill.contract.runner import (
    CommandOutcome,
    make_contract_app,
)
from novel_ralph_skill.state import recount_words

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    import cyclopts

    from novel_ralph_skill.state import ChapterEntry


def _recount_or_state_error(
    working_dir: pathlib.Path,
    manifest: cabc.Sequence[ChapterEntry],
) -> cabc.Mapping[str, int]:
    """Recount the drafts, mapping any read fault to the exit-``3`` channel.

    :func:`~novel_ralph_skill.state.recount_words` has already absorbed the one
    benign read fault — an absent ``draft.md`` returns ``0`` — and propagates
    every other read fault (``UnicodeDecodeError``, ``PermissionError``,
    ``IsADirectoryError`` and any other non-``FileNotFoundError`` ``OSError``). It
    delegates the fault translation to the shared
    :func:`~novel_ralph_skill.commands.state_sourcing.draft_read_guard` context
    manager (the single home for the
    ``try/except STATE_INPUT_ERRORS → _draft_read_error`` shell, roadmap §7.3.3),
    which re-raises the fault as
    :class:`~novel_ralph_skill.contract.runner.StateInputError` so an undecodable
    draft reaches exit ``3`` and cannot escape to the benign exit ``1`` (design
    §3.2), naming the ``working/`` tree via the shared formatter. The ``by_chapter``
    return sits outside the guard so the guarded body is just the reader call.

    Parameters
    ----------
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.
    manifest : collections.abc.Sequence[ChapterEntry]
        The chapter manifest from the loaded ``State`` (``state.chapters``).

    Returns
    -------
    collections.abc.Mapping[str, int]
        The per-chapter drafted-word mapping keyed by the zero-padded two-digit
        chapter string. The drafted total is ``sum(by_chapter.values())``.

    Raises
    ------
    StateInputError
        When a chapter's ``draft.md`` is unreadable or undecodable (exit ``3``).
    """
    with draft_read_guard(working_dir):
        _current, by_chapter = recount_words(working_dir, manifest)
    return by_chapter


def source_state_and_drafts() -> tuple[
    int, tuple[ChapterEntry, ...], cabc.Mapping[str, int]
]:
    """Source the novel target, the manifest, and the drafted counts from disk.

    Loads the typed ``working/state.toml`` through the shared
    :func:`~novel_ralph_skill.commands.state_sourcing.load_or_state_error` (so a
    missing or unparseable state is exit ``3``), takes the novel target from
    ``[word_counts].target`` (configured, not derived from disk) and the chapter
    manifest from the loaded ``State``, and recounts each chapter's ``draft.md``
    from disk (the disk-authoritative numerator, ExecPlan Decision Log D-NUM). An
    absent ``working/`` makes ``load_or_state_error`` fail on the missing
    ``state.toml``, the same exit-``3`` route ``desloppify`` and the mutators take.

    Returns
    -------
    tuple[int, tuple[ChapterEntry, ...], collections.abc.Mapping[str, int]]
        The novel target word count, the manifest chapters in their recorded
        order, and the per-chapter drafted-word mapping.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable, or a chapter's
        ``draft.md`` is unreadable or undecodable (the exit-``3`` channel).
    """
    working_dir = pathlib.Path(WORKING_DIR_NAME)
    state = load_or_state_error(working_dir / "state.toml")
    by_chapter = _recount_or_state_error(working_dir, state.chapters)
    return state.word_counts.target, state.chapters, by_chapter


def _wordcount() -> CommandOutcome:
    """Derive the word-count report and project it into a :class:`CommandOutcome`.

    Sources the target, manifest, and drafted counts from the ``working/`` tree
    (the exit-``3`` faults are raised by :func:`source_state_and_drafts`), derives
    the pure §4.5 report via
    :func:`~novel_ralph_skill.commands._wordcount_report.build_report`, and projects
    it into the success envelope via
    :func:`~novel_ralph_skill.commands._wordcount_report.report_outcome`. A
    successful report exits ``0`` (ExecPlan Decision Log D-EXIT): ``wordcount`` is
    a report, not a detector that surfaces an actionable finding.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` carrying the per-chapter and cumulative report.

    Raises
    ------
    StateInputError
        When the ``working/`` tree is missing or unreadable (the exit-``3``
        channel), propagated from :func:`source_state_and_drafts`.
    """
    target, manifest, by_chapter = source_state_and_drafts()
    report = build_report(target=target, manifest=manifest, by_chapter=by_chapter)
    return report_outcome(report)


def build_app() -> cyclopts.App:
    """Build the ``wordcount`` Cyclopts app (design §4.5).

    Built via :func:`novel_ralph_skill.contract.runner.make_contract_app`, which
    owns the four-flag contract so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope,
    exactly like ``desloppify`` and ``novel-compile``. The single default body
    takes no arguments beyond the four shared contract flags (no ``--chapter``;
    ExecPlan Decision Log D-SCOPE) and returns a
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome`.

    Returns
    -------
    cyclopts.App
        The configured ``wordcount`` app.
    """
    app = make_contract_app("wordcount")

    @app.default
    def _report() -> CommandOutcome:
        """Report per-chapter and cumulative word counts; exit 0 (design §4.5)."""
        return _wordcount()

    return app
