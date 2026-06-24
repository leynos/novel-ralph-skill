"""The ``recount`` mutator body (roadmap task 2.3.1; design §4.1).

``recount`` re-derives ``[word_counts].current`` and ``[word_counts].by_chapter``
from the on-disk chapter drafts, so a human never types a word count again
(design §4.1 lines 275-282). It is a *single-file* mutator: it rewrites only
``working/state.toml``, already atomic via ``Path.replace``, exactly like
``set-cursor`` and ``advance-phase``, so it opens **no** ``[pending_turn]``
bracket (design §4.1 line 271; §3.4 lines 240-241; ExecPlan Decision Log D-PT).

It lives beside :mod:`novel_ralph_skill.commands._state_mutators` rather than in
it so that module stays within the 400-line cap (AGENTS.md "clear file
boundaries"); it reuses that module's shared load/refuse helpers
(:func:`_state_path`, :func:`_working_dir`, :func:`_load_document_or_state_error`,
:func:`_state_view_or_state_error`, :func:`_refuse_if_incoherent`) rather than
duplicating the mutator contract.
"""

from __future__ import annotations

import typing as typ

import tomlkit

from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _refuse_if_incoherent,
    _state_path,
    _state_view_or_state_error,
    _working_dir,
)
from novel_ralph_skill.commands.novel_state import STATE_INPUT_ERRORS
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import recount_words, write_document_atomically

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state import ChapterEntry


def _recount_or_state_error(
    manifest: cabc.Sequence[ChapterEntry],
) -> tuple[int, cabc.Mapping[str, int]]:
    """Recount the drafts, mapping any read fault to exit ``3``.

    :func:`~novel_ralph_skill.state.recount_words` has already absorbed the one
    benign read fault — an absent ``draft.md`` returns ``0`` (it catches
    ``FileNotFoundError`` narrowly per chapter). Every *other* read fault —
    ``UnicodeDecodeError`` (an undecodable body, a ``ValueError`` subclass),
    ``PermissionError``, ``IsADirectoryError``, and any other non-
    ``FileNotFoundError`` ``OSError`` — propagates out of ``recount_words``, and
    this wrapper re-raises it as :class:`StateInputError` under the existing
    ``STATE_INPUT_ERRORS`` tuple (whose members include ``OSError`` and
    ``ValueError``), so it reaches the exit-``3`` channel and cannot escape to the
    benign exit ``1`` (ExecPlan Round-1 blocking point 3; design §3.2). This
    mirrors ``_load_document_or_state_error`` in the mutator module.

    Parameters
    ----------
    manifest : collections.abc.Sequence[ChapterEntry]
        The chapter manifest from the prior typed view (``prior.chapters``).

    Returns
    -------
    tuple[int, collections.abc.Mapping[str, int]]
        The recounted total and the ordered per-chapter mapping.

    Raises
    ------
    StateInputError
        When a chapter's ``draft.md`` is unreadable or undecodable (the exit-``3``
        channel).
    """
    try:
        return recount_words(_working_dir(), manifest)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot recount chapter drafts: {exc}"
        raise StateInputError(msg) from exc


def _inline_by_chapter(by_chapter: cabc.Mapping[str, int]) -> tomlkit.items.InlineTable:
    """Return a fresh ``tomlkit`` inline table for ``by_chapter``.

    Rebuilding ``[word_counts].by_chapter`` as a fresh inline table in the
    mapping's (ascending) key order keeps the write deterministic, so a second
    ``recount`` over unchanged drafts yields a byte-for-byte identical
    ``state.toml`` (ExecPlan Risk "non-idempotent write"; Decision Log D-KEY).

    Parameters
    ----------
    by_chapter : collections.abc.Mapping[str, int]
        The recounted per-chapter mapping, already in ascending key order.

    Returns
    -------
    tomlkit.items.InlineTable
        The populated inline table to assign to ``document["word_counts"]``.
    """
    table = tomlkit.inline_table()
    table.update(dict(by_chapter))
    return table


def recount() -> CommandOutcome:
    """Re-derive ``[word_counts]`` from the chapter drafts; refuse with exit ``3``.

    Loads ``working/state.toml`` through the ``tomlkit`` document path, derives the
    typed view to prove structural completeness and obtain the chapter manifest,
    recounts each chapter's ``draft.md`` token count via the shared
    :func:`~novel_ralph_skill.state.recount_words` helper, and rewrites
    ``[word_counts].current`` and ``[word_counts].by_chapter`` in place. It writes
    a *single* file (``state.toml``), already atomic via ``Path.replace``, so it
    opens no ``[pending_turn]`` bracket — exactly like ``set-cursor`` and
    ``advance-phase`` (design §4.1 line 271; §3.4 lines 240-241; Decision Log
    D-PT). ``current`` is the drafted sum ``sum(by_chapter.values())`` (design §5.2
    invariant 3 holds by construction; Decision Log D-CURRENT). The proposed state
    is validated before the write, so a recount that would breach a §5.2 invariant
    refuses with exit ``3`` and leaves the prior ``state.toml`` byte-for-byte
    intact (Constraints "Validate before persist").

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the recounted counts are written, carrying the
        written counts in ``result`` — ``{"current", "by_chapter"}``. This is the
        write-shaped success vocabulary: a mutator names what it changed and never
        echoes the ``check`` query's ``violations`` read shape (design §3.3;
        audit-2.2.2 Finding 2).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, a chapter's ``draft.md``
        is unreadable or undecodable, or the recounted state is incoherent (each
        the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    # Derive the typed view first to prove structural completeness and obtain the
    # manifest; a missing ``[word_counts]``/``[chapters]`` table would otherwise
    # make the edit below raise ``NonExistentKey`` uncaught -> exit 1 (BR2-1).
    prior = _state_view_or_state_error(document)
    current, by_chapter = _recount_or_state_error(prior.chapters)
    document["word_counts"]["current"] = current
    document["word_counts"]["by_chapter"] = _inline_by_chapter(by_chapter)
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="recount")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"current": current, "by_chapter": dict(by_chapter)},
        messages=[f"recounted {current} words across {len(by_chapter)} chapters"],
    )
