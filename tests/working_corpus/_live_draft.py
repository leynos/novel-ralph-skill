"""The live-draft cross-check oracle for roadmap task 2.1.3.

The §5.2 validator reads only the ``[word_counts]`` table for its two pure-state
proxies: the ``gate-ratio-consistent`` numerator ``sum(by_chapter.values())`` and
the ``consecutive-clean-within-drafted`` ceiling, the count of ``by_chapter``
entries ``> 0``. The developers' guide ("Invariant validation", lines 323-334)
names both as proxies for a real disk quantity and promises task 2.1.3 reconciles
them "against a live draft count".

:func:`live_draft_owned` is that reconciliation. It recomputes **both** live
quantities — the drafted-words total and the drafted-chapters count — from the
on-disk ``draft.md`` bodies via :func:`live_draft_counts`, then reconciles the
``[gates.knitting]`` booleans against the live drafted-words ratio and the
``[drafting.critic].consecutive_clean`` counter against the live drafted-chapters
count. Both are genuinely independent of the ``[word_counts]`` table the validator
trusts, so the cross-check catches a table-versus-real-drafts mislabel of either
quantity. The table-internal ``by-chapter-sum`` coherence (``sum(by_chapter) ==
current``) has no live analogue, so the live oracle does not reconcile it: it
takes the verdict :func:`corpus_check` already returns. The other five owned
invariants are pure-state and reused from the same spec-keyed
:func:`corpus_check`.

This module lives beside :mod:`._oracle` rather than inside it solely because the
combined oracle would breach the 400-line module cap (AGENTS.md). The two
live-draft reconciliations parse the materialised ``state.toml`` once in
:func:`live_draft_owned` and operate on the already-decoded ``[gates]`` and
``[drafting]`` tables, so each predicate is a pure function over decoded data.
"""

from __future__ import annotations

import tomllib
import typing as typ

from ._oracle import (
    BY_CHAPTER_SUM,
    COMPLETED_PREFIX,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
    PHASE_IN_ENUM,
    corpus_check,
)
from ._specs import GATE_THRESHOLDS

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from ._specs import WorkingTreeSpec

# The eight pure-state invariant names the §5.2 validator owns (it never emits
# the five disk-evidence names). The live-draft oracle restricts its verdict to
# these so it can be compared with the validator directly. The set mirrors
# ``novel_ralph_skill.state.PURE_STATE_INVARIANT_NAMES``; the production constant
# is the source of truth and ``test_owned_names_equal_corpus_vocabulary`` pins
# them equal, so this local copy cannot silently drift.
_LIVE_DRAFT_OWNED_NAMES: frozenset[str] = frozenset({
    PHASE_IN_ENUM,
    COMPLETED_PREFIX,
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_WITHIN_TARGET,
    CONVERGENCE_TARGET_AT_LEAST_ONE,
    CONSECUTIVE_CLEAN_WITHIN_DRAFTED,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
})


def live_draft_counts(working_dir: Path) -> tuple[int, int]:
    """Return ``(drafted_words_total, drafted_chapters_count)`` from disk.

    Globs ``working_dir/manuscript/chapter-*/draft.md``, reads each present file
    as UTF-8, and takes its whitespace-split token count. The first element sums
    those counts (the honest-draft numerator ``sum(chapter.draft_words)``
    recovered from disk); the second counts the bodies whose token count is
    ``> 0`` (the honest-draft ceiling
    ``sum(1 for c in chapters if c.draft_words > 0)``). Both are independent of
    the ``[word_counts]`` table, so they cross-check that table and the
    gate/consecutive-clean fields, not restate them.

    A chapter with no ``draft.md`` (the ``write_draft=False`` case) and a chapter
    with an empty ``draft.md`` (``draft_words=0``, zero tokens) both contribute
    nothing to either quantity, mirroring the builder and matching the validator's
    ``> 0`` filter exactly.
    """
    draft_paths = sorted((working_dir / "manuscript").glob("chapter-*/draft.md"))
    token_counts = [
        len(path.read_text(encoding="utf-8").split()) for path in draft_paths
    ]
    words_total = sum(token_counts)
    chapters_count = sum(1 for count in token_counts if count > 0)
    return words_total, chapters_count


def _check_gate_ratio_live(
    word_counts: cabc.Mapping[str, typ.Any],
    gates: cabc.Mapping[str, typ.Any],
    drafted_words_total: int,
) -> bool:
    """Return True when each knitting gate matches the live drafted-words ratio.

    Reads ``[word_counts].target`` and the ``[gates.knitting]`` booleans from the
    already-decoded ``state.toml`` tables, then compares each boolean against
    ``(drafted_words_total / target) >= threshold`` for its threshold in
    :data:`GATE_THRESHOLDS`. The numerator is the **live** drafted-words total
    recovered from the ``draft.md`` bodies, never ``sum(by_chapter.values())``.
    Short-circuits to consistent when ``target <= 0``, mirroring the validator's
    totality guard.
    """
    target = word_counts["target"]
    if target <= 0:
        return True
    knitting = gates["knitting"]
    ratio = drafted_words_total / target
    low, mid, high = GATE_THRESHOLDS
    knitting_gates = (
        (knitting["done_30"], low),
        (knitting["done_50"], mid),
        (knitting["done_80"], high),
    )
    return all(flag == (ratio >= threshold) for flag, threshold in knitting_gates)


def _check_consecutive_clean_live(
    drafting: cabc.Mapping[str, typ.Any],
    drafted_chapters_count: int,
) -> bool:
    """Return True when ``consecutive_clean`` is within the live drafted chapters.

    Reads ``[drafting.critic].consecutive_clean`` from the already-decoded
    ``state.toml`` ``[drafting]`` table (the field the builder writes and the
    validator reads; it is part of the state under test, not a proxy) and compares
    it against the **live** drafted-chapters count recovered from the ``draft.md``
    bodies, never against the count of ``by_chapter`` entries ``> 0``. This is the
    second proxy the developers' guide names, reconciled against the live drafts.
    """
    clean = drafting["critic"]["consecutive_clean"]
    return clean <= drafted_chapters_count


def live_draft_owned(spec: WorkingTreeSpec, working_dir: Path) -> set[str]:
    """Return the owned invariant names a tree violates under the live-draft read.

    Overrides the two disk-reconcilable owned invariants ``gate-ratio-consistent``
    (gate booleans vs ``drafted_words_total / target`` against
    :data:`GATE_THRESHOLDS`) and ``consecutive-clean-within-drafted``
    (``[drafting.critic].consecutive_clean`` vs ``drafted_chapters_count``) with
    the live-draft reads. It reuses the spec-keyed :func:`corpus_check`
    (restricted to the owned set) for the other six owned invariants — the five
    pure-state ones (``phase-in-enum``, ``completed-prefix``,
    ``consecutive-clean-within-target``, ``convergence-target-at-least-one``,
    ``cursor-coherent``) and ``by-chapter-sum`` (table ``sum(by_chapter) ==
    current`` — table-internal, with no live analogue, so the verdict
    :func:`corpus_check` already returns is taken as is rather than recomputed).

    The invariant-7 numerator and the invariant-4c ceiling are BOTH honest-draft
    live quantities (the live drafted-words total ``sum(chapter.draft_words)`` and
    the live drafted-chapters count
    ``sum(1 for c in chapters if c.draft_words > 0)`` recovered from disk), NOT
    their ``[word_counts].by_chapter`` table equivalents. The two
    ``by_chapter_override`` variants that separate the table basis from the draft
    basis — ``DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]``
    and ``["by-chapter-override-under-counts-drafts"]`` — therefore exercise this
    landmine: the disagreement they surface is a finding to investigate, not a
    drift to align. The under-counting variant in particular kills a
    ``min(live, table)``-style mutant of :func:`live_draft_counts` that mishandles
    only over-counts and survives the over-counting variant alone.

    The ``spec`` argument feeds only the :func:`corpus_check` reuse; the two
    live-draft proxy reconciliations (``gate-ratio-consistent``,
    ``consecutive-clean-within-drafted``) read disk and never the spec.
    ``by-chapter-sum`` is independent of the spec but table-internal, not live, so
    its verdict comes straight from :func:`corpus_check`; the other five owned
    invariants are derived from the spec via :func:`corpus_check` and are
    deliberately not spec-independent.
    """
    words_total, chapters_count = live_draft_counts(working_dir)
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    spec_owned = set(corpus_check(spec, working_dir)) & _LIVE_DRAFT_OWNED_NAMES
    # Override the two live-reconcilable owned invariants with the live reads;
    # ``by-chapter-sum`` keeps the table-internal verdict ``corpus_check`` returns.
    spec_owned.discard(GATE_RATIO_CONSISTENT)
    spec_owned.discard(CONSECUTIVE_CLEAN_WITHIN_DRAFTED)
    if not _check_gate_ratio_live(state["word_counts"], state["gates"], words_total):
        spec_owned.add(GATE_RATIO_CONSISTENT)
    if not _check_consecutive_clean_live(state["drafting"], chapters_count):
        spec_owned.add(CONSECUTIVE_CLEAN_WITHIN_DRAFTED)
    return spec_owned
