"""Materialise a :class:`WorkingTreeSpec` as an on-disk ``working/`` tree.

The builder writes the manuscript, the chapter outline, and ``state.toml``
through ``tomlkit`` (ADR-002; design §5.3), carrying every table the §5.1 schema
names so the phase-2 schema task parses each state file without loss. Layout
follows ``state-layout.md`` and design §5.1 exactly: manuscript under
``working/manuscript/``, chapters ``chapter-NN/`` zero-padded to two digits,
``compiled.md`` at ``working/manuscript/compiled.md``, the outline at
``working/plan/chapter-outline.md``, and ``state.toml`` at the ``working/`` root.
"""

from __future__ import annotations

import typing as typ

import tomlkit

from ._specs import (
    _CREATED_AT,
    _resolve_compiled,
    chapter_dir_name,
    derive_by_chapter,
    derive_current,
    draft_body,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

    import tomlkit.items as tomlitems

    from ._specs import ChapterSpec, WorkingTreeSpec


def _inline(pairs: dict[str, object]) -> tomlitems.InlineTable:
    """Return a ``tomlkit`` inline table populated from ``pairs``."""
    table = tomlkit.inline_table()
    table.update(pairs)
    return table


def _novel_table(spec: WorkingTreeSpec) -> tomlitems.Table:
    """Return the ``[novel]`` table with the fixed ``created_at`` literal."""
    table = tomlkit.table()
    table["title"] = "Working Title"
    table["slug"] = "working-title"
    table["target_word_count"] = spec.target_words
    table["created_at"] = _CREATED_AT
    return table


def _phase_table(spec: WorkingTreeSpec) -> tomlitems.Table:
    """Return the ``[phase]`` table (current phase and completed prefix)."""
    table = tomlkit.table()
    table["current"] = spec.phase_current
    table["completed"] = list(spec.phase_completed)
    return table


def _drafting_table(spec: WorkingTreeSpec) -> tomlitems.Table:
    """Return the ``[drafting]`` table with its critic and fangirl sub-tables."""
    table = tomlkit.table()
    table["current_chapter"] = spec.current_chapter
    table["current_scene"] = spec.current_scene
    table["current_beat"] = spec.current_beat
    critic = tomlkit.table()
    critic["pass"] = 1
    critic["consecutive_clean"] = spec.consecutive_clean
    critic["convergence_target"] = spec.convergence_target
    critic["last_finding_counts"] = _inline({
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


def _gates_table(spec: WorkingTreeSpec) -> tomlitems.Table:
    """Return the ``[gates]`` table (knitting booleans and the final gate)."""
    table = tomlkit.table()
    knitting = tomlkit.table()
    knitting["done_30"] = spec.done_30
    knitting["done_50"] = spec.done_50
    knitting["done_80"] = spec.done_80
    table["knitting"] = knitting
    final = tomlkit.table()
    final["final_pass_complete"] = spec.final_pass_complete
    table["final"] = final
    return table


def _word_counts_table(spec: WorkingTreeSpec) -> tomlitems.Table:
    """Return the ``[word_counts]`` table with the string-keyed ``by_chapter``."""
    table = tomlkit.table()
    table["target"] = spec.target_words
    by_chapter = derive_by_chapter(spec)
    table["current"] = derive_current(spec)
    table["by_chapter"] = _inline(dict(by_chapter))
    return table


def _chapters_array(spec: WorkingTreeSpec) -> tomlitems.Array:
    """Return the ``[chapters]`` manifest array in zero-padded chapter order.

    The manifest holds one entry per planned chapter: every in-manifest chapter
    plus every ``manifest_only_numbers`` entry (a manifest entry with no on-disk
    directory, for the bijection-violation variant), ordered by number.
    """
    numbers = sorted(
        {chapter.number for chapter in spec.chapters if chapter.in_manifest}
        | set(spec.manifest_only_numbers)
    )
    by_number = {chapter.number: chapter for chapter in spec.chapters}
    array = tomlkit.array()
    array.multiline(multiline=True)
    for number in numbers:
        chapter = by_number.get(number)
        array.append(
            _inline({
                "number": number,
                "slug": chapter.slug if chapter else f"chapter-{number:02d}",
                "title": chapter.title if chapter else f"Chapter {number}",
                "target_words": chapter.target_words if chapter else 0,
            })
        )
    return array


def _build_state_document(spec: WorkingTreeSpec) -> tomlkit.TOMLDocument:
    """Return the full ``state.toml`` document for ``spec``.

    Carries every table the §5.1 schema names (``schema_version``, ``[novel]``,
    ``[phase]``, ``[drafting]`` with its critic/fangirl sub-tables, ``[gates]``,
    ``[word_counts]``, and ``[chapters]``), plus ``[pending_turn]`` only when the
    spec provides one.
    """
    doc = tomlkit.document()
    doc["schema_version"] = 1
    doc["novel"] = _novel_table(spec)
    doc["phase"] = _phase_table(spec)
    doc["drafting"] = _drafting_table(spec)
    doc["gates"] = _gates_table(spec)
    doc["word_counts"] = _word_counts_table(spec)
    doc["chapters"] = _chapters_array(spec)
    if spec.pending_turn is not None:
        pending = tomlkit.table()
        pending.update(dict(spec.pending_turn))
        doc["pending_turn"] = pending
    return doc


def _write_chapter(chapter: ChapterSpec, manuscript: Path) -> None:
    """Write one chapter directory: draft, plan files, and ``done.flag``.

    ``draft.md`` is suppressed entirely when ``write_draft`` is ``False`` so the
    directory has no draft at all (the design §5.4 ``done.flag``-beside-absent-
    ``draft.md`` case); otherwise it is written, empty when ``draft_words`` is 0.
    ``scenes.md`` and ``beats.md`` (the scene/beat plan files, ``state-layout.md``
    lines 38-39) are written only when ``has_scene_plan`` / ``has_beat_plan`` are
    set, each with a fixed deterministic body so snapshot suites do not churn.
    """
    chapter_dir = manuscript / chapter_dir_name(chapter.number)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    if chapter.write_draft:
        (chapter_dir / "draft.md").write_text(
            draft_body(chapter.draft_words), encoding="utf-8"
        )
    if chapter.has_scene_plan:
        (chapter_dir / "scenes.md").write_text("# Scenes\n", encoding="utf-8")
    if chapter.has_beat_plan:
        (chapter_dir / "beats.md").write_text("# Beats\n", encoding="utf-8")
    if chapter.has_done_flag:
        (chapter_dir / "done.flag").touch()


def build_working_tree(spec: WorkingTreeSpec, dest: Path) -> Path:
    """Materialise ``spec`` as a ``working/`` tree under ``dest``.

    Parameters
    ----------
    spec : WorkingTreeSpec
        The declarative tree specification to render.
    dest : Path
        The destination directory (a test's ``tmp_path``); ``working/`` is
        created beneath it.

    Returns
    -------
    Path
        The path to the materialised ``working/`` directory.
    """
    working = dest / "working"
    manuscript = working / "manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (working / "plan").mkdir(parents=True, exist_ok=True)
    (working / "log.md").write_text("", encoding="utf-8")
    (working / "plan" / "chapter-outline.md").write_text("", encoding="utf-8")
    for chapter in spec.chapters:
        _write_chapter(chapter, manuscript)
    compiled = _resolve_compiled(spec)
    if compiled is not None:
        (manuscript / "compiled.md").write_text(compiled, encoding="utf-8")
    (working / "state.toml").write_text(
        tomlkit.dumps(_build_state_document(spec)), encoding="utf-8"
    )
    return working
