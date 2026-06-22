"""Boundary constructors that build a typed :class:`State` from ``state.toml``.

This module is the single place a decoded ``state.toml`` mapping becomes the
typed :class:`~novel_ralph_skill.state.schema.State` object, so no raw
``dict[str, object]`` leaks inward (python-data-shapes: "parse to a schema type
at the boundary and never let the raw ``dict`` leak inward").

:func:`parse_state` is pure — mapping in, :class:`State` out — so the §5.2
validator (roadmap task 2.1.2) and the ``tomlkit`` round-trip (task 2.2.1) can
reuse it without a filesystem. :func:`load_state` is a thin convenience that
reads bytes with the standard-library ``tomllib`` and delegates.

Parsing is **structural** only: it builds the typed object and resolves phase
strings to :class:`~novel_ralph_skill.state.phase.Phase` members. It does not
enforce the §5.2 invariants (that is task 2.1.2). ``tomllib`` decodes every TOML
array to a Python ``list``; this module explicitly coerces each such field to a
``tuple`` so no decoded ``list`` is left on a ``tuple``-typed field.
"""

from __future__ import annotations

import tomllib
import typing as typ

from novel_ralph_skill.state.phase import Phase
from novel_ralph_skill.state.schema import (
    ChapterEntry,
    CriticState,
    Drafting,
    FangirlState,
    FinalGate,
    FindingCounts,
    Gates,
    KnittingGates,
    NovelMeta,
    PendingTurn,
    PhaseState,
    State,
    WordCounts,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

# The ``state.toml`` decoded by ``tomllib`` is a nested mapping; every table this
# parser reads is itself a mapping, so a single alias documents that shape.
type _Table = cabc.Mapping[str, object]


def _table(raw: _Table, key: str) -> _Table:
    """Return ``raw[key]`` typed as a nested table mapping.

    ``tomllib`` returns ``dict`` for every TOML table, so this narrows the
    ``object`` value to the mapping shape the sub-constructors expect. The cast
    is a structural promise the corpus trees keep; a malformed table surfaces as
    a ``KeyError`` or ``TypeError`` at construction, which task 2.2.x maps to an
    exit code.
    """
    return typ.cast("_Table", raw[key])


def _novel(raw: _Table) -> NovelMeta:
    """Construct :class:`NovelMeta` from the ``[novel]`` table."""
    return NovelMeta(
        title=typ.cast("str", raw["title"]),
        slug=typ.cast("str", raw["slug"]),
        target_word_count=typ.cast("int", raw["target_word_count"]),
        created_at=typ.cast("str", raw["created_at"]),
    )


def _phase(raw: _Table) -> PhaseState:
    """Construct :class:`PhaseState`, resolving each phase string to a member.

    The ``[phase].completed`` array is decoded by ``tomllib`` as a ``list``;
    each element is resolved through :class:`Phase` and the result is built as a
    ``tuple`` so no ``list`` is left on the ``tuple``-typed field.
    """
    completed = typ.cast("cabc.Sequence[str]", raw["completed"])
    return PhaseState(
        current=Phase(typ.cast("str", raw["current"])),
        completed=tuple(Phase(value) for value in completed),
    )


def _chapters(raw_entries: object) -> tuple[ChapterEntry, ...]:
    """Construct the ``[chapters]`` manifest tuple from the decoded array.

    ``tomllib`` decodes the array of inline tables to a ``list[dict]``; each
    entry is built into a :class:`ChapterEntry` and the result is a ``tuple`` in
    the array's order.
    """
    entries = typ.cast("cabc.Sequence[_Table]", raw_entries)
    return tuple(
        ChapterEntry(
            number=typ.cast("int", entry["number"]),
            slug=typ.cast("str", entry["slug"]),
            title=typ.cast("str", entry["title"]),
            target_words=typ.cast("int", entry["target_words"]),
        )
        for entry in entries
    )


def _finding_counts(raw: _Table) -> FindingCounts:
    """Construct :class:`FindingCounts` from the ``last_finding_counts`` table."""
    return FindingCounts(
        blocker=typ.cast("int", raw["blocker"]),
        major=typ.cast("int", raw["major"]),
        minor=typ.cast("int", raw["minor"]),
        taste=typ.cast("int", raw["taste"]),
    )


def _critic(raw: _Table) -> CriticState:
    """Construct :class:`CriticState` from the ``[drafting.critic]`` table.

    The ``pass`` key is a Python keyword on disk, so it is read by subscription
    and stored on the ``pass_number`` attribute.
    """
    return CriticState(
        pass_number=typ.cast("int", raw["pass"]),
        consecutive_clean=typ.cast("int", raw["consecutive_clean"]),
        convergence_target=typ.cast("int", raw["convergence_target"]),
        last_finding_counts=_finding_counts(_table(raw, "last_finding_counts")),
    )


def _drafting(raw: _Table) -> Drafting:
    """Construct :class:`Drafting` from the ``[drafting]`` table and sub-tables."""
    return Drafting(
        current_chapter=typ.cast("int", raw["current_chapter"]),
        current_scene=typ.cast("int", raw["current_scene"]),
        current_beat=typ.cast("int", raw["current_beat"]),
        critic=_critic(_table(raw, "critic")),
        fangirl=FangirlState(
            last_chapter_passed=typ.cast(
                "int", _table(raw, "fangirl")["last_chapter_passed"]
            )
        ),
    )


def _gates(raw: _Table) -> Gates:
    """Construct :class:`Gates` from the ``[gates]`` knitting and final tables."""
    knitting = _table(raw, "knitting")
    final = _table(raw, "final")
    return Gates(
        knitting=KnittingGates(
            done_30=typ.cast("bool", knitting["done_30"]),
            done_50=typ.cast("bool", knitting["done_50"]),
            done_80=typ.cast("bool", knitting["done_80"]),
        ),
        final=FinalGate(
            final_pass_complete=typ.cast("bool", final["final_pass_complete"])
        ),
    )


def _word_counts(raw: _Table) -> WordCounts:
    """Construct :class:`WordCounts` from the raw ``[word_counts]`` table.

    ``by_chapter`` is copied and wrapped read-only by
    :meth:`WordCounts.__post_init__`, so the boundary passes it straight through;
    the typed object never aliases the decoded mapping the caller still holds.
    """
    return WordCounts(
        target=typ.cast("int", raw["target"]),
        current=typ.cast("int", raw["current"]),
        by_chapter=typ.cast("cabc.Mapping[str, int]", raw["by_chapter"]),
    )


def _pending_turn(raw: object) -> PendingTurn:
    """Construct :class:`PendingTurn`, coercing ``paths`` to a tuple.

    ``tomllib`` decodes the ``paths`` array to a ``list``; it is rebuilt as a
    ``tuple`` so no ``list`` is left on the ``tuple``-typed field.
    """
    table = typ.cast("_Table", raw)
    paths = typ.cast("cabc.Sequence[str]", table["paths"])
    return PendingTurn(
        operation=typ.cast("str", table["operation"]),
        paths=tuple(paths),
    )


def parse_state(raw: cabc.Mapping[str, object]) -> State:
    """Construct a :class:`State` from a decoded ``state.toml`` mapping.

    Builds the typed object table by table and resolves every phase string to a
    :class:`Phase` member. Every TOML array is coerced to a ``tuple`` at this
    boundary, so the returned object holds no decoded ``list`` on a
    ``tuple``-typed field. This is a structural parse only; the §5.2 invariants
    are not checked here (roadmap task 2.1.2).

    Parameters
    ----------
    raw : collections.abc.Mapping[str, object]
        The decoded ``state.toml`` mapping, as ``tomllib.load`` returns.

    Returns
    -------
    State
        The fully typed, frozen state object.

    Raises
    ------
    KeyError
        If a required table or key is absent from ``raw``.
    ValueError
        If a phase string is not a :class:`Phase` member.
    """
    raw_pending = raw.get("pending_turn")
    return State(
        schema_version=typ.cast("int", raw["schema_version"]),
        novel=_novel(_table(raw, "novel")),
        phase=_phase(_table(raw, "phase")),
        chapters=_chapters(raw["chapters"]),
        drafting=_drafting(_table(raw, "drafting")),
        gates=_gates(_table(raw, "gates")),
        word_counts=_word_counts(_table(raw, "word_counts")),
        pending_turn=(None if raw_pending is None else _pending_turn(raw_pending)),
    )


def load_state(path: Path) -> State:
    """Read and parse ``state.toml`` from ``path`` with ``tomllib``.

    A thin convenience over :func:`parse_state`: it opens ``path`` in binary
    mode, decodes it with the standard-library ``tomllib``, and delegates the
    typed construction. Keeping :func:`parse_state` pure lets the validator and
    the round-trip reuse it without a filesystem.

    Parameters
    ----------
    path : pathlib.Path
        The path to a ``state.toml`` file.

    Returns
    -------
    State
        The fully typed, frozen state object parsed from ``path``.
    """
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_state(raw)
