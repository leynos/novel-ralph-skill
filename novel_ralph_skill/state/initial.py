"""Build a fresh, schema-coherent ``state.toml`` document for ``init``.

This module is the *create* half of the ``init`` mutator (roadmap task 2.2.2;
design §4.1 ``init`` row, §5.1 schema). :func:`build_initial_document` emits the
**full** required table set the strict :func:`~novel_ralph_skill.state.parse.
parse_state` boundary reads by subscription — every key, with no defaults — so a
freshly initialised tree parses cleanly and ``novel-state check`` accepts it
(design §5.2; ExecPlan Decision Log D5, Risk "init builds an unreadable
document").

The schema *shape* mirrors the corpus reference builder
(``tests/working_corpus/_builder.py`` ``_build_state_document``) field for
field, re-derived from ``state/parse.py`` rather than importing test code. The
inline-table *materialisation* idiom is no longer hand-copied: both modules now
build their inline tables through the shared
:func:`~novel_ralph_skill.state.document.build_inline_table` helper (roadmap
task 7.2.1), so only the schema field set is mirrored here, not the builder
plumbing. The mirrored fields are: ``schema_version``; ``[novel]`` (with
``created_at``); ``[phase]``
(``current = "premise"``, an empty ``completed``); ``[drafting]`` with its
``[drafting.critic]`` and ``[drafting.fangirl]`` sub-tables; ``[gates.knitting]``
and ``[gates.final]`` all-false; ``[word_counts]`` with a present empty
``by_chapter``; and an empty ``[[chapters]]`` array. The result carries no
``[pending_turn]`` — the initial state has no in-flight turn.

The document is written back through
:func:`~novel_ralph_skill.state.document.write_document_atomically`, the single
sanctioned writer (ADR-002; design §5.3); this module never serialises directly.
"""

from __future__ import annotations

import typing as typ

import tomlkit

from novel_ralph_skill.state.document import build_inline_table
from novel_ralph_skill.state.phase import Phase

if typ.TYPE_CHECKING:
    import tomlkit.items as tomlitems
    from tomlkit import TOMLDocument

# The §5.1 default convergence ceiling: a single clean critic pass converges a
# chapter (design §5.1; the corpus ``_pre_drafting_spec`` uses the same value).
_DEFAULT_CONVERGENCE_TARGET = 1


def _novel_table(
    *, title: str, slug: str, target_word_count: int, created_at: str
) -> tomlitems.Table:
    """Return the ``[novel]`` table from the supplied metadata.

    ``title`` and ``slug`` are stored verbatim (the schema treats them as opaque
    strings; slug validation is not a §5.2 invariant). ``created_at`` is the
    generated RFC 3339 timestamp the parser reads at ``raw["created_at"]``.
    """
    table = tomlkit.table()
    table["title"] = title
    table["slug"] = slug
    table["target_word_count"] = target_word_count
    table["created_at"] = created_at
    return table


def _phase_table() -> tomlitems.Table:
    """Return the initial ``[phase]`` table: ``premise`` with no completed phases."""
    table = tomlkit.table()
    table["current"] = Phase.PREMISE.value
    table["completed"] = tomlkit.array()
    return table


def _drafting_table() -> tomlitems.Table:
    """Return the initial ``[drafting]`` table with critic and fangirl sub-tables.

    The cursor is zeroed (no chapter, scene, or beat yet); the critic carries the
    keyword ``pass`` key the parser reads at ``raw["pass"]`` and the four-key
    ``last_finding_counts`` inline table; the fangirl records its
    ``last_chapter_passed`` baseline.
    """
    table = tomlkit.table()
    table["current_chapter"] = 0
    table["current_scene"] = 0
    table["current_beat"] = 0
    critic = tomlkit.table()
    # ``pass`` seeds at 1: passes are numbered from 1, so the first pass is
    # numbered 1 and pending (not run), matching the corpus builder and the
    # reference (audit:2.1.8 Findings 1 and 2; state-layout.md "Critic
    # sub-state").
    critic["pass"] = 1
    critic["consecutive_clean"] = 0
    critic["convergence_target"] = _DEFAULT_CONVERGENCE_TARGET
    critic["last_finding_counts"] = build_inline_table({
        "blocker": 0,
        "major": 0,
        "minor": 0,
        "taste": 0,
    })
    table["critic"] = critic
    fangirl = tomlkit.table()
    fangirl["last_chapter_passed"] = 0
    table["fangirl"] = fangirl
    return table


def _gates_table() -> tomlitems.Table:
    """Return the initial ``[gates]`` table: every knitting and final gate false."""
    table = tomlkit.table()
    knitting = tomlkit.table()
    knitting["done_30"] = False
    knitting["done_50"] = False
    knitting["done_80"] = False
    table["knitting"] = knitting
    final = tomlkit.table()
    final["final_pass_complete"] = False
    table["final"] = final
    return table


def _word_counts_table(target_word_count: int) -> tomlitems.Table:
    """Return the initial ``[word_counts]`` table with a present empty ``by_chapter``.

    ``current`` is zero (no drafted words yet) and ``by_chapter`` is a present but
    empty inline table — the parser subscripts ``raw["by_chapter"]``, so it must
    exist even when empty.
    """
    table = tomlkit.table()
    table["target"] = target_word_count
    table["current"] = 0
    table["by_chapter"] = build_inline_table({})
    return table


def build_initial_document(
    *, title: str, slug: str, target_word_count: int, created_at: str
) -> TOMLDocument:
    """Build a fresh, schema-coherent ``state.toml`` document for ``init``.

    Carries every required §5.1 table the strict ``parse_state`` boundary reads
    by subscription: ``schema_version``, ``[novel]`` (with ``created_at``),
    ``[phase]`` (``current = "premise"``, an empty ``completed``), ``[drafting]``
    with its ``[drafting.critic]`` (``pass``, ``consecutive_clean``,
    ``convergence_target = 1``, ``last_finding_counts`` inline with
    ``blocker``/``major``/``minor``/``taste``) and ``[drafting.fangirl]``
    (``last_chapter_passed``) sub-tables, ``[gates.knitting]`` and
    ``[gates.final]`` all-false, ``[word_counts]`` (``target``, ``current = 0``,
    a present empty ``by_chapter`` inline table), and an empty ``[[chapters]]``
    array. There is no ``[pending_turn]`` (no in-flight turn).
    ``parse_state(build_initial_document(...))`` succeeds and ``validate_state``
    of the result is an empty tuple.

    Parameters
    ----------
    title : str
        The novel title, stored verbatim in ``[novel].title``.
    slug : str
        The filesystem-safe project slug, stored verbatim in ``[novel].slug``.
    target_word_count : int
        The novel target, written to both ``[novel].target_word_count`` and
        ``[word_counts].target``.
    created_at : str
        The RFC 3339 creation timestamp, written to ``[novel].created_at``.

    Returns
    -------
    tomlkit.TOMLDocument
        The fresh, schema-coherent ``state.toml`` document.
    """
    document = tomlkit.document()
    document["schema_version"] = 1
    document["novel"] = _novel_table(
        title=title,
        slug=slug,
        target_word_count=target_word_count,
        created_at=created_at,
    )
    document["phase"] = _phase_table()
    document["drafting"] = _drafting_table()
    document["gates"] = _gates_table()
    document["word_counts"] = _word_counts_table(target_word_count)
    document["chapters"] = tomlkit.array()
    return document
