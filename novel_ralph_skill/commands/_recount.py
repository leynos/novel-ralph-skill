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

from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _refuse_if_incoherent,
    _state_path,
    _state_view_or_state_error,
    _working_dir,
)
from novel_ralph_skill.commands.state_sourcing import draft_read_guard
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome
from novel_ralph_skill.state import (
    GATE_THRESHOLDS,
    build_inline_table,
    recount_words,
    write_document_atomically,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state import ChapterEntry, State

# The three knitting-gate flag names paired with their ``set-gate`` flags, in
# ``GATE_THRESHOLDS`` order, so the recount remedy can point each disagreeing
# gate at the exact ``novel-state set-gate --knitting-NN`` verb that repairs it
# (verified ``_gate_drafting_mutators.py`` lines 71-73).
_KNITTING_GATE_REPAIRS: tuple[tuple[str, str], ...] = (
    ("done_30", "--knitting-30"),
    ("done_50", "--knitting-50"),
    ("done_80", "--knitting-80"),
)


def _recount_or_state_error(
    manifest: cabc.Sequence[ChapterEntry],
) -> tuple[int, cabc.Mapping[str, int]]:
    """Recount the drafts, mapping any read fault to exit ``3``.

    :func:`~novel_ralph_skill.state.recount_words` has already absorbed the one
    benign read fault — an absent ``draft.md`` returns ``0`` (it catches
    ``FileNotFoundError`` narrowly per chapter). Every *other* read fault —
    ``UnicodeDecodeError`` (an undecodable body, a ``ValueError`` subclass),
    ``PermissionError``, ``IsADirectoryError``, and any other non-
    ``FileNotFoundError`` ``OSError`` — propagates out of ``recount_words``. It
    delegates the fault translation to the shared
    :func:`~novel_ralph_skill.commands.state_sourcing.draft_read_guard` context
    manager (the single home for the
    ``try/except STATE_INPUT_ERRORS → _draft_read_error`` shell, roadmap §7.3.3),
    which re-raises the fault as :class:`StateInputError` so it reaches the
    exit-``3`` channel and cannot escape to the benign exit ``1`` (design §3.2),
    naming the ``working/`` tree via the shared formatter. The working directory is
    resolved once and passed to both the reader and the guard.

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
    working_dir = _working_dir()
    with draft_read_guard(working_dir):
        return recount_words(working_dir, manifest)


def _gate_ratio_remedy(state: State) -> list[str]:
    """Return per-gate actionable advice when a recount breaches a knitting gate.

    Pure text: reads ``state`` and returns one operator-advice line per knitting
    gate whose recorded flag disagrees with ``drafted_ratio >= threshold``,
    choosing the line by direction. It enumerates the gates directly rather than
    recomputing "which threshold was crossed", so the advice is built only from
    facts the validator already knows: each gate's recorded flag, its threshold
    (``GATE_THRESHOLDS``), and the recounted drafted ratio. The empty list is
    returned when no knitting gate disagrees — so the helper is a harmless no-op
    when some *other* invariant is the sole breach (design §4.1, §5.4 recovery
    rule 1; the remedy points at a verb, never a hand-edit — ADR-001/ADR-010).

    The **upward** line (flag ``false`` but the recount moved drafting at or past
    the threshold) prescribes the repair: integrate the pending knitting pass,
    then run ``novel-state set-gate --knitting-NN``. The **downward** line (flag
    ``true`` but the recount left drafting below the threshold) deliberately omits
    that verb — nothing was crossed upward, so prescribing the repair would
    corrupt the gate-integration record; it asks the operator to adjudicate.

    Parameters
    ----------
    state : State
        The proposed (recounted) state being refused.

    Returns
    -------
    list[str]
        One advice line per disagreeing knitting gate, empty when none disagree.
    """
    target = state.word_counts.target
    if target <= 0:
        return []
    drafted_total = sum(state.word_counts.by_chapter.values())
    ratio = drafted_total / target
    knitting = state.gates.knitting
    flags = (knitting.done_30, knitting.done_50, knitting.done_80)
    # Render the drafted ratio with one decimal so a near-boundary ratio (e.g.
    # 0.298) reads as "29.8%" rather than rounding to "30%" inside a "below the
    # 30% threshold" sentence, which would read as a self-contradiction for an
    # operator sitting on a gate boundary.
    percent = f"{ratio * 100:.1f}"
    lines: list[str] = []
    for (name, flag_name), flag, threshold in zip(
        _KNITTING_GATE_REPAIRS, flags, GATE_THRESHOLDS, strict=True
    ):
        crossed = ratio >= threshold
        if flag == crossed:
            continue
        gate_percent = int(threshold * 100)
        if crossed:
            lines.append(
                f"recount crossed the {gate_percent}% knitting threshold (drafts "
                f"now at {percent}% of target) but gate {name} is still false: "
                f"integrate the pending knitting pass and log it, then run "
                f"`novel-state set-gate {flag_name}`. Do not hand-edit [gates]."
            )
        else:
            lines.append(
                f"recount left drafting below the {gate_percent}% knitting "
                f"threshold (drafts now at {percent}% of target) but gate {name} "
                f"is recorded true: the recorded gate no longer matches the "
                f"drafts. Adjudicate — restore the drafts or clear the gate — and "
                f"re-derive. Do not hand-edit [gates] to silence this."
            )
    return lines


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
    document["word_counts"]["by_chapter"] = build_inline_table(by_chapter)
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="recount", remedy=_gate_ratio_remedy)
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"current": current, "by_chapter": dict(by_chapter)},
        messages=[f"recounted {current} words across {len(by_chapter)} chapters"],
    )
