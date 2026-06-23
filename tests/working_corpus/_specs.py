"""On-disk ``working/`` fixture corpus for the test suite.

This module is the corpus data and builder for roadmap task 1.3.2. It declares
the specification dataclasses (:class:`ChapterSpec`, :class:`WorkingTreeSpec`),
the :func:`build_working_tree` factory that materialises a ``working/`` tree on
disk, the ``compiled.md`` concatenation helper, and the named specification
library consumed by the slice suites in roadmap phases 2-6.

The corpus is anchored to the design's authoritative artefacts rather than to
any not-yet-existent schema type: ``docs/novel-ralph-harness-design.md`` §5.1
(schema and phase enum) and §5.2 (invariants), and
``skill/novel-ralph/references/state-layout.md`` (the authoritative on-disk
layout). It is expressed as plain ``tomlkit`` data so the typed schema (roadmap
task 2.1.1) and the §5.2 validator (task 2.1.2) can wrap it unchanged; this
module deliberately invents neither (Decision Log, ``docs/execplans/roadmap-1-3-2.md``).

``tests/conftest.py`` is the single runtime importer of this module: it
re-exposes every datum as a pytest fixture so test modules consume the corpus by
fixture parameter name and never by a runtime value import (the developers-guide
"Shared test scaffolding" rule). The spec *types* are re-exported from
``conftest`` under its ``TYPE_CHECKING`` guard so a test annotation uses the
sanctioned ``from conftest import WorkingTreeSpec`` carve-out.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# The single separator the corpus joins ordered draft bodies with when writing a
# coherent ``compiled.md``; the design names "consistent separators" (§4.3) but
# pins no exact bytes, so the corpus owns this one constant (Decision Log). The
# oracle recomputes the concatenation with the same helper, so it stays
# internally consistent regardless of the eventual production separator.
CORPUS_SEPARATOR = "\n\n"

# The knitting-gate thresholds, the single source of truth ``0.30 / 0.50 / 0.80``
# (``state-layout.md`` lines 174-177; design §5.2 invariant 7). Pinned once and
# shared by the coherent gate booleans, the ``gate-true-below-threshold``
# variant, and the oracle's invariant-7 branch so the three cannot drift.
GATE_THRESHOLDS: tuple[float, float, float] = (0.30, 0.50, 0.80)

# The fixed ``novel.created_at`` literal every corpus state file carries, so no
# timestamp varies between trees and snapshot suites in later phases stay stable.
_CREATED_AT = "2026-05-23T14:00:00Z"

# The sentinel ``compiled`` value asking the builder to write the hash-equal
# ordered concatenation of the present drafts (the coherent compile). Any other
# string writes those exact bytes (a stale or contradictory compile).
COMPILED_AUTO = "AUTO"


@dc.dataclass(frozen=True, kw_only=True)
class ChapterSpec:
    """A single chapter's on-disk shape within a ``working/`` tree.

    Parameters
    ----------
    number : int
        The chapter number, one-based; the directory is ``chapter-NN`` with
        ``NN`` zero-padded to two digits.
    slug : str
        The filesystem-safe chapter identifier carried in the ``[chapters]``
        manifest.
    title : str
        The chapter title carried in the ``[chapters]`` manifest.
    target_words : int
        The planned word count carried in the ``[chapters]`` manifest.
    draft_words : int
        The number of deterministic words the builder writes into ``draft.md``;
        ``0`` writes an empty ``draft.md``.
    has_done_flag : bool
        When true, the builder ``touch``es ``done.flag`` beside the draft.
    in_manifest : bool
        When true (the default), the chapter has a matching ``[chapters]``
        manifest entry; ``False`` models a ``chapter-NN/`` directory with no
        manifest entry, for the bijection-violation variant.
    write_draft : bool
        When true (the default), the builder writes ``draft.md`` (empty when
        ``draft_words`` is ``0``); ``False`` suppresses the write entirely so
        the chapter directory has *no* ``draft.md`` — modelling the design §5.4
        ``done.flag`` beside an *absent* ``draft.md`` contradiction (which the
        always-written empty case alone cannot reach).
    has_scene_plan : bool
        When true, the builder writes ``scenes.md`` beside the draft — the
        on-disk scene plan (``state-layout.md`` line 38). Defaulting ``False``
        keeps every existing spec byte-identical; a non-zero ``current_scene``
        without this file is the "zero until plans exist" sub-clause of design
        §5.2 invariant 6.
    has_beat_plan : bool
        When true, the builder writes ``beats.md`` beside the draft — the
        on-disk beat plan (``state-layout.md`` line 39). Defaulting ``False``
        keeps every existing spec byte-identical; a non-zero ``current_beat``
        without this file is the "zero until plans exist" sub-clause of design
        §5.2 invariant 6.
    """

    number: int
    slug: str
    title: str
    target_words: int
    draft_words: int
    has_done_flag: bool
    in_manifest: bool = True
    write_draft: bool = True
    has_scene_plan: bool = False
    has_beat_plan: bool = False


@dc.dataclass(frozen=True, kw_only=True)
class WorkingTreeSpec:
    """A declarative specification of a whole ``working/`` tree.

    The builder renders this to disk under a test's ``tmp_path``. Fields the
    design names but a variant does not vary carry fixed builder defaults so the
    phase-2 schema task parses every state file without loss.

    Parameters
    ----------
    phase_current : str
        The active phase (``[phase].current``); a member of the phase enum for a
        coherent tree.
    phase_completed : tuple[str, ...]
        The ordered completed-phase prefix (``[phase].completed``).
    chapters : tuple[ChapterSpec, ...]
        The on-disk chapters, in order.
    target_words : int
        The novel target word count (``[novel].target_word_count`` and
        ``[word_counts].target``).
    consecutive_clean : int
        The critic's ``consecutive_clean`` counter.
    convergence_target : int
        The critic's configured ``convergence_target`` ceiling (default 1).
    manifest_only_numbers : tuple[int, ...]
        Manifest entries with no on-disk directory, for the other direction of
        the bijection-violation variant.
    by_chapter_override : Mapping[str, int] | None
        When ``None``, ``[word_counts].by_chapter`` is derived from each
        chapter's ``draft_words``; a value sets the per-chapter breakdown
        explicitly (still keyed by the zero-padded two-digit string).
    current_words_override : int | None
        When ``None``, ``[word_counts].current`` is the sum of the
        ``by_chapter`` values (design §5.2 invariant 3 holds on disk); an
        integer writes that value to ``[word_counts].current`` verbatim while
        ``by_chapter`` still derives from the drafts, so the on-disk state has
        ``sum(by_chapter) != current`` — the genuine invariant-3 violation the
        ``by-chapter-sum-mismatch`` variant needs.
    done_30, done_50, done_80 : bool
        The knitting-gate booleans (``[gates.knitting]``).
    final_pass_complete : bool
        The final-pass gate (``[gates.final]``).
    current_chapter, current_scene, current_beat : int
        The drafting cursor (``[drafting]``).
    compiled : str | None
        ``None`` writes no ``compiled.md``; :data:`COMPILED_AUTO` writes the
        hash-equal concatenation of the present drafts; any other string writes
        exactly those bytes (the stale/contradictory compile).
    pending_turn : Mapping[str, object] | None
        When set, the two-key ``operation``/``paths`` ``[pending_turn]`` marker
        for the torn-turn variant.
    """

    phase_current: str
    phase_completed: tuple[str, ...]
    chapters: tuple[ChapterSpec, ...]
    target_words: int
    consecutive_clean: int
    convergence_target: int
    manifest_only_numbers: tuple[int, ...] = ()
    by_chapter_override: cabc.Mapping[str, int] | None = None
    current_words_override: int | None = None
    done_30: bool = False
    done_50: bool = False
    done_80: bool = False
    final_pass_complete: bool = False
    current_chapter: int = 0
    current_scene: int = 0
    current_beat: int = 0
    compiled: str | None = None
    pending_turn: cabc.Mapping[str, object] | None = None


def chapter_dir_name(number: int) -> str:
    """Return the ``chapter-NN`` directory name for a one-based chapter number.

    Names are zero-padded to two digits up to 99 chapters (``state-layout.md``
    lines 54-56); the corpus never exceeds that range.
    """
    return f"chapter-{number:02d}"


def by_chapter_key(number: int) -> str:
    """Return the zero-padded two-digit string ``by_chapter`` key for a chapter.

    ``state-layout.md`` line 115 keys ``[word_counts].by_chapter`` by a
    zero-padded two-digit *string* (``"01"``, ``"02"``, …); the corpus, the
    invariant-3 sum check, and the oracle all use this exact key form.
    """
    return f"{number:02d}"


def draft_body(word_count: int) -> str:
    """Return a deterministic ``draft.md`` body with exactly ``word_count`` words.

    The body is fixed minimal text whose whitespace-split token count is exactly
    ``word_count`` (``0`` yields an empty string), so later word-count suites
    have exact expected totals and snapshot suites do not churn.
    """
    if word_count <= 0:
        return ""
    return " ".join("word" for _ in range(word_count))


def concatenate_drafts(drafts: cabc.Sequence[str]) -> str:
    """Return the ordered concatenation of ``drafts`` joined by the separator.

    This is the corpus's local stand-in for the §4.3 compile routine (the
    ordered concatenation of the present drafts with consistent separators) that
    roadmap task 4.1.1 implements. The builder uses it to write a coherent
    ``compiled.md``; the oracle uses it to recompute the expected concatenation
    for the content-hash compile check (§4.3 lines 320-344; §9 lines 705-711).
    """
    return CORPUS_SEPARATOR.join(drafts)


def _present_draft_bodies(spec: WorkingTreeSpec) -> list[str]:
    """Return the present chapters' draft bodies in zero-padded chapter order."""
    ordered = sorted(spec.chapters, key=lambda chapter: chapter.number)
    return [draft_body(chapter.draft_words) for chapter in ordered]


def _resolve_compiled(spec: WorkingTreeSpec) -> str | None:
    """Return the ``compiled.md`` bytes to write, or ``None`` for no file.

    :data:`COMPILED_AUTO` resolves to the hash-equal concatenation of the
    present drafts (the coherent compile); any other string is written verbatim
    (the stale or contradictory compile).
    """
    if spec.compiled is None:
        return None
    if spec.compiled == COMPILED_AUTO:
        return concatenate_drafts(_present_draft_bodies(spec))
    return spec.compiled


def derive_by_chapter(spec: WorkingTreeSpec) -> dict[str, int]:
    """Return the ``[word_counts].by_chapter`` mapping for ``spec``.

    When ``by_chapter_override`` is set, that mapping is returned verbatim;
    otherwise the mapping is derived from each chapter's ``draft_words`` keyed by
    the zero-padded two-digit string.
    """
    if spec.by_chapter_override is not None:
        return dict(spec.by_chapter_override)
    return {
        by_chapter_key(chapter.number): chapter.draft_words
        for chapter in sorted(spec.chapters, key=lambda chapter: chapter.number)
    }


def derive_current(spec: WorkingTreeSpec) -> int:
    """Return the ``[word_counts].current`` value the builder writes for ``spec``.

    When ``current_words_override`` is set, that integer is returned verbatim so
    the on-disk ``current`` diverges from ``sum(by_chapter)`` — the genuine
    design §5.2 invariant-3 violation (``by-chapter-sum-mismatch``). Otherwise
    ``current`` is the sum of the ``by_chapter`` values, so invariant 3 holds.
    """
    if spec.current_words_override is not None:
        return spec.current_words_override
    return sum(derive_by_chapter(spec).values())
