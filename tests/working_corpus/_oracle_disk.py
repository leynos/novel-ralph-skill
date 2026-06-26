"""The physically-disk-reading half of the corpus structural oracle.

This module holds the oracle predicates that take a ``working_dir`` parameter and
read the materialised ``working/`` tree (``state.toml`` and the manuscript files),
split out from :mod:`._oracle` purely for file size (AGENTS.md 400-line cap). Each
moved predicate keeps the role it had in ``_oracle.py`` and is imported back there
so :func:`._oracle.corpus_check` and every existing caller are unchanged.

The §5.4 disk-evidence twins — :func:`_check_manifest_disk_bijection`,
:func:`_check_done_flag_without_draft`, :func:`_check_compiled_matches_drafts`,
:func:`_check_word_counts_match_drafts`, :func:`_check_word_counts_cover_drafts`,
:func:`_check_log_present`, and :func:`_check_cursor_plan_present` — remain the
disk-reading twins of the same-named production predicates in
:mod:`novel_ralph_skill.state.disk_evidence`. :func:`_check_by_chapter_sum` is
**not** a disk-evidence twin: it is the on-disk reader of the *pure-state*
``by-chapter-sum`` name, owned by ``validate_state`` and absent from
``DISK_EVIDENCE_INVARIANT_NAMES``. The disk-evidence-owned ``pending-turn-cleared``
twin (``_check_pending_turn_cleared``) does **not** live here: it reads the spec,
not disk, so it stays in ``_oracle.py``'s ``_SPEC_CHECKS``.
"""

from __future__ import annotations

import tomllib
import typing as typ

from ._specs import (
    chapter_dir_name,
    concatenate_drafts,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

    from ._specs import WorkingTreeSpec

# Disk-evidence (roadmap task 2.3.6): the ``by_chapter`` key-set coverage
# divergence from the manifest-keyed recount, orthogonal to the shared-key value
# match ``WORD_COUNTS_MATCH_DRAFTS`` owns. Defined here beside the predicate that
# owns it and re-exported through ``_oracle`` so the vocabulary stays single-homed.
WORD_COUNTS_COVER_DRAFTS = "word-counts-cover-drafts"


def _check_by_chapter_sum(working_dir: Path) -> bool:
    """Return True when ``by_chapter`` sums to ``current`` on disk (invariant 3).

    Reads the materialised ``state.toml`` and compares the sum of the written
    ``[word_counts].by_chapter`` values against the written
    ``[word_counts].current``. This is the genuine design §5.2 invariant 3 as it
    appears on disk — exactly what task 2.1.2's validator will see — so a spec
    with ``current_words_override`` set produces a real on-disk violation here.
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    word_counts = state["word_counts"]
    return sum(word_counts["by_chapter"].values()) == word_counts["current"]


def _on_disk_chapter_numbers(working_dir: Path) -> set[int]:
    """Return the chapter numbers materialised under ``manuscript/``.

    Globs ``manuscript/chapter-*`` directories and parses the two-digit suffix,
    ignoring any entry whose suffix is not a valid integer. Mirrors production
    ``_on_disk_chapter_numbers`` (``disk_evidence.py``).
    """
    numbers: set[int] = set()
    for entry in (working_dir / "manuscript").glob("chapter-*"):
        suffix = entry.name.removeprefix("chapter-")
        if entry.is_dir() and suffix.isdigit():
            numbers.add(int(suffix))
    return numbers


def _check_manifest_disk_bijection(
    working_dir: Path, *, relax_drafting: bool = False
) -> bool:
    """Return True when manifest entries and chapter dirs are in bijection (inv 5).

    Reads the manifest from the materialised ``state.toml`` ``[chapters]`` array
    and the on-disk side from a ``manuscript/chapter-*`` glob, then classifies the
    break into its two directions (``orphans = on_disk - manifest``,
    ``missing = manifest - on_disk``) plus the contiguity-from-1 check, mirroring
    production ``_check_manifest_disk_bijection``.

    When ``relax_drafting`` is set and the materialised ``[phase].current`` is
    ``drafting``, a break whose only broken direction is ``missing`` (no orphan,
    contiguous manifest) is treated as coherent — the disk-subset-of-manifest
    relaxation (ADR 009). The default (``relax_drafting=False``) is strict, so
    ``corpus_check`` and the strict agreement suite read the unchanged bijection.
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    manifest = {chapter["number"] for chapter in state["chapters"]}
    on_disk = _on_disk_chapter_numbers(working_dir)
    # Deliberate independent twin of production ``_classify_bijection``
    # (``novel_ralph_skill.state._disk_paths``); kept un-shared so the oracle never
    # imports the thing it checks (the deliberate-twin discipline).
    orphans = on_disk - manifest
    missing = manifest - on_disk
    contiguous = sorted(manifest) == list(range(1, len(manifest) + 1))
    coherent_subset = not orphans and contiguous
    if coherent_subset and not missing:
        return True
    drafting = relax_drafting and state["phase"]["current"] == "drafting"
    return drafting and coherent_subset


def _check_done_flag_without_draft(working_dir: Path) -> bool:
    """Return True when no ``done.flag`` sits beside an empty draft (§5.4).

    For each manifest chapter (read from the materialised ``state.toml``), a
    ``done.flag`` beside a ``draft.md`` whose whitespace-split token count is zero
    — or beside no ``draft.md`` at all — is a contradiction. Disk-reading twin of
    production ``_check_done_flag_without_draft`` (``disk_evidence.py``).
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    manuscript = working_dir / "manuscript"
    for chapter in state["chapters"]:
        chapter_dir = manuscript / chapter_dir_name(chapter["number"])
        if not (chapter_dir / "done.flag").exists():
            continue
        draft = chapter_dir / "draft.md"
        text = draft.read_text(encoding="utf-8") if draft.exists() else ""
        if not text.split():
            return False
    return True


def _disk_drafts(working_dir: Path) -> list[tuple[int, str]]:
    """Return ``(number, draft_text)`` per manifest chapter, in ascending order.

    Reads the manifest from the materialised ``state.toml`` ``[chapters]`` array,
    then each chapter's ``draft.md`` as UTF-8 (an absent draft contributing the
    empty string). The shared read behind :func:`_disk_present_draft_bodies` and
    :func:`_disk_by_chapter`, mirroring production ``recount_words``.
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    manuscript = working_dir / "manuscript"
    drafts: list[tuple[int, str]] = []
    for number in sorted(chapter["number"] for chapter in state["chapters"]):
        draft = manuscript / chapter_dir_name(number) / "draft.md"
        drafts.append((
            number,
            draft.read_text(encoding="utf-8") if draft.exists() else "",
        ))
    return drafts


def _disk_present_draft_bodies(working_dir: Path) -> list[str]:
    """Return present chapters' draft bodies via :func:`_disk_drafts`.

    Disk-reading twin of production ``_present_draft_bodies``.
    """
    return [text for _number, text in _disk_drafts(working_dir)]


def _check_compiled_matches_drafts(working_dir: Path) -> bool:
    """Return True when ``compiled.md`` is the concatenation of drafts (§4.3/§9).

    Recomputes the ordered :func:`concatenate_drafts` of the present drafts read
    from disk via :func:`_disk_present_draft_bodies` and compares ``compiled.md``'s
    bytes against it; a tree with no ``compiled.md`` trivially satisfies the check.
    Disk-reading twin of production ``_check_compiled_matches_drafts``.
    """
    compiled_path = working_dir / "manuscript" / "compiled.md"
    if not compiled_path.exists():
        return True
    expected = concatenate_drafts(_disk_present_draft_bodies(working_dir))
    return compiled_path.read_text(encoding="utf-8") == expected


def _disk_by_chapter(working_dir: Path) -> dict[str, int]:
    """Return the per-chapter token counts read straight from the on-disk drafts.

    Reads each manifest chapter's ``draft.md`` from disk via :func:`_disk_drafts`
    (an absent draft counts ``0``) and takes its whitespace-split token count,
    keyed by the zero-padded two-digit string (production ``recount_words``).
    """
    return {
        f"{number:02d}": len(text.split()) for number, text in _disk_drafts(working_dir)
    }


def _check_word_counts_match_drafts(working_dir: Path) -> bool:
    """Return True when the ``[word_counts]`` table matches the on-disk drafts (§5.4).

    Recomputes the per-chapter token counts from disk via :func:`_disk_by_chapter`
    and compares the recomputed ``by_chapter`` mapping against the
    ``[word_counts].by_chapter`` table read from the materialised ``state.toml``.
    The comparison is over ``by_chapter`` **only**, never ``current`` —
    ``current`` versus ``sum(by_chapter)`` is the orthogonal table-internal
    ``by-chapter-sum`` check's concern (D-WORDCOUNT). Only the **shared** chapter
    keys are compared, so a manifest-to-disk key mismatch (the
    ``manifest-disk-bijection`` contradiction's concern) does not double-fire here.
    Disk-reading twin of production ``_check_word_counts_match_drafts``.
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    table = dict(state["word_counts"]["by_chapter"])
    disk = _disk_by_chapter(working_dir)
    shared = set(disk) & set(table)
    return all(disk[key] == table[key] for key in shared)


def _check_word_counts_cover_drafts(
    working_dir: Path, *, relax_drafting: bool = False
) -> bool:
    """Return True when the ``by_chapter`` key set covers the drafts (§5.4).

    Recomputes the manifest-keyed disk ``by_chapter`` via :func:`_disk_by_chapter`
    (one entry per manifest chapter) and, at bijection (``manifest == on_disk``),
    returns True iff its key set equals the ``[word_counts].by_chapter`` table key
    set. A recount key absent from the table is a drafted chapter omitted from the
    table; a table key absent from the recount is a key the manifest never
    declared. Both are pure key-coverage signals (roadmap task 2.3.6).

    When ``relax_drafting`` is set and the materialised ``[phase].current`` is
    ``drafting`` and the manifest/disk break is a coherent subset (no orphan,
    contiguous manifest, ``on_disk < manifest``), it re-keys off the **on-disk
    drafted subset** (the directory-present chapters) and returns True iff every
    drafted chapter has a table key — the *missing* direction only (roadmap task
    2.3.8; Decisions D2, D6). The symmetric extra direction is deliberately not
    checked, so the manifest-keyed recount (which writes a ``0`` key per undrafted
    manifest chapter) never re-trips the twin on its own repair.

    Outside that exact shape — a non-subset break, a non-drafting phase, or the
    strict default — it **defers** (returns True): a non-bijective manifest is the
    ``manifest-disk-bijection`` invariant's signal, and the recount keys off the
    (untrustworthy) manifest, so the key-set comparison would otherwise
    double-fire on every structural mismatch. Deliberate independent twin of
    production ``_check_word_counts_cover_drafts``; kept un-shared (the
    deliberate-twin discipline).
    """
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    manifest = {chapter["number"] for chapter in state["chapters"]}
    on_disk = _on_disk_chapter_numbers(working_dir)
    table = dict(state["word_counts"]["by_chapter"])
    if manifest == on_disk:
        disk = _disk_by_chapter(working_dir)
        return set(disk) == set(table)
    drafting = relax_drafting and state["phase"]["current"] == "drafting"
    # ``coherent_subset``: a strict subset (``on_disk < manifest``) with no orphan
    # and a contiguous manifest from 1.
    contiguous = sorted(manifest) == list(range(1, len(manifest) + 1))
    is_subset = on_disk < manifest and not (on_disk - manifest) and contiguous
    if drafting and is_subset:
        drafted_keys = {f"{number:02d}" for number in on_disk}
        return drafted_keys <= set(table)
    return True


def _check_log_present(working_dir: Path) -> bool:
    """Return True when ``log.md`` is present (§5.4).

    Disk-reading twin of production ``_check_log_present``.
    """
    return (working_dir / "log.md").exists()


def _check_cursor_plan_present(spec: WorkingTreeSpec, working_dir: Path) -> bool:
    """Return True when a non-zero scene/beat cursor has its on-disk plan (inv 6).

    The "zero until their plans exist" sub-clause of design §5.2 invariant 6: a
    non-zero ``current_scene`` requires the current chapter's ``scenes.md``, and
    a non-zero ``current_beat`` requires its ``beats.md`` (``state-layout.md``
    lines 38-39, 86-88). This is disk-evidence — it reads the built tree — so
    the pure-state validator cannot decide it (deferred to task 2.3.2).

    ``working_dir`` is the materialised ``working/`` directory, so the plan files
    live under ``working_dir / "manuscript" / chapter_dir_name(n)/`` — the same
    ``manuscript/`` base :func:`_check_compiled_matches_drafts` joins. The
    predicate is guarded by ``0 < current_chapter <= len(chapters)`` so it never
    raises on a malformed cursor and leaves the degenerate ``current_chapter ==
    0`` case to the pure-state :func:`._oracle._check_cursor_coherent` clause; an
    out-of-range cursor returns True (the predicate does not fire).
    """
    if not 0 < spec.current_chapter <= len(spec.chapters):
        return True
    chapter_dir = working_dir / "manuscript" / chapter_dir_name(spec.current_chapter)
    if spec.current_scene > 0 and not (chapter_dir / "scenes.md").exists():
        return False
    return not (spec.current_beat > 0 and not (chapter_dir / "beats.md").exists())
