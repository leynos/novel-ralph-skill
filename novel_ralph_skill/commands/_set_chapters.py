"""The ``set-chapters`` mutator body (roadmap task 2.2.3; design §4.1, §5.1).

``set-chapters`` populates the ``[chapters]`` manifest from the agent's plan, the
one piece of harness state that previously had no sanctioned command to write it
(design §5.1; ADR 001). It is the multi-file mutator that, in one turn, persists
the populated manifest, materialises the on-disk ``working/manuscript/chapter-NN/``
directories, and appends a ``log.md`` receipt, so ``novel-state check`` finds the
manifest and disk in bijection (design §5.2) immediately afterwards.

The manifest is the agent's *judgement* (slug/title/target_words) and is **not**
recomputable from disk, so — unlike ``reconcile``, whose recount payload persists
last — the populated ``[chapters]`` is written into the document and persisted
**together with** the ``[pending_turn]`` intent record in the *first* atomic write,
before any directory is created (ADR 008, design §5.4; ExecPlan Decision Log D10).
Every torn state from that write onward therefore carries the full manifest on disk
with only deterministically-derivable empty directories outstanding, which
``reconcile`` completes (ExecPlan Decision Log D8).

It lives in its own module rather than in
:mod:`novel_ralph_skill.commands._state_mutators` so that module stays within the
400-line cap (AGENTS.md "Keep file size manageable"); it reuses that module's
shared load/refuse helpers rather than duplicating the mutator contract.
"""

from __future__ import annotations

import datetime as dt
import typing as typ

import tomlkit
import tomlkit.items

from novel_ralph_skill.commands._chapter_plan_entry import ChapterPlanEntry
from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _refuse_if_incoherent,
    _state_path,
    _state_view_or_state_error,
    _working_dir,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import (
    SET_CHAPTERS_OPERATION,
    build_inline_table,
    chapter_dir_name,
    clear_pending_turn,
    open_pending_turn,
    write_document_atomically,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import pathlib

    from tomlkit import TOMLDocument

# Re-exported so existing importers (`from _set_chapters import ChapterPlanEntry`)
# and ``manifest_coherence_violations`` callers keep one name; the class itself
# lives in the dependency-free leaf module to break the circular import.
__all__ = ["ChapterPlanEntry", "manifest_coherence_violations", "set_chapters"]

# The manifest-coherence rule names, each spelled as a distinct kebab string so a
# refusal pins exactly the rule broken (mirroring ``validate.py``'s
# one-predicate-per-invariant style). These are write-time preconditions the §5.2
# ``validate_state`` set does not own (ExecPlan Decision Log D4), so they live here
# beside ``set-chapters`` rather than in the pure-state validator.
CHAPTERS_NON_EMPTY: typ.Final = "chapters-non-empty"
NUMBERS_UNIQUE: typ.Final = "numbers-unique"
NUMBERS_CONTIGUOUS_FROM_1: typ.Final = "numbers-contiguous-from-1"
SLUGS_UNIQUE: typ.Final = "slugs-unique"
TARGET_WORDS_POSITIVE: typ.Final = "target-words-positive"

# The owned rule names, in the deterministic order
# :func:`manifest_coherence_violations` evaluates them, so a multi-rule verdict is
# stable for the tests and the refusal message.
MANIFEST_COHERENCE_RULE_NAMES: tuple[str, ...] = (
    CHAPTERS_NON_EMPTY,
    NUMBERS_UNIQUE,
    NUMBERS_CONTIGUOUS_FROM_1,
    SLUGS_UNIQUE,
    TARGET_WORDS_POSITIVE,
)


def manifest_coherence_violations(
    entries: cabc.Sequence[ChapterPlanEntry],
) -> tuple[str, ...]:
    """Return the manifest-coherence rules ``entries`` breaks (empty == coherent).

    A pure, total predicate the ``set-chapters`` body calls *before* the §5.2
    validate-before-persist pass: it owns the write-time preconditions the §5.2
    ``validate_state`` set does not (ExecPlan Decision Log D4). The rules, in the
    fixed :data:`MANIFEST_COHERENCE_RULE_NAMES` order:

    - :data:`CHAPTERS_NON_EMPTY` — an empty plan is refused (nothing to populate);
    - :data:`NUMBERS_UNIQUE` — no chapter number repeats;
    - :data:`NUMBERS_CONTIGUOUS_FROM_1` — the sorted numbers are ``1..n`` with no
      gaps (the §5.2 bijection's "contiguous from 1" wording the manifest must
      satisfy);
    - :data:`SLUGS_UNIQUE` — no chapter slug repeats (D5, a manifest-quality guard);
    - :data:`TARGET_WORDS_POSITIVE` — every ``target_words`` is at least 1.

    Parameters
    ----------
    entries : collections.abc.Sequence[ChapterPlanEntry]
        The proposed chapter plan, in the order the agent supplied it.

    Returns
    -------
    tuple[str, ...]
        The breached rule names in evaluation order; empty when ``entries`` is a
        coherent manifest.

    Examples
    --------
    >>> manifest_coherence_violations([])
    ('chapters-non-empty',)
    >>> coherent = [
    ...     ChapterPlanEntry(number=1, slug="a", title="A", target_words=10),
    ...     ChapterPlanEntry(number=2, slug="b", title="B", target_words=20),
    ... ]
    >>> manifest_coherence_violations(coherent)
    ()
    >>> manifest_coherence_violations(coherent[1:])
    ('numbers-contiguous-from-1',)
    """
    if not entries:
        return (CHAPTERS_NON_EMPTY,)
    numbers = [entry.number for entry in entries]
    slugs = [entry.slug for entry in entries]
    violations: list[str] = []
    if len(set(numbers)) != len(numbers):
        violations.append(NUMBERS_UNIQUE)
    if sorted(numbers) != list(range(1, len(numbers) + 1)):
        violations.append(NUMBERS_CONTIGUOUS_FROM_1)
    if len(set(slugs)) != len(slugs):
        violations.append(SLUGS_UNIQUE)
    if any(entry.target_words < 1 for entry in entries):
        violations.append(TARGET_WORDS_POSITIVE)
    return tuple(violations)


def _ordered_chapters(
    chapters: cabc.Sequence[ChapterPlanEntry],
) -> list[ChapterPlanEntry]:
    """Return ``chapters`` sorted ascending by number (the manifest's order)."""
    return sorted(chapters, key=lambda entry: entry.number)


def _chapter_array(ordered: cabc.Sequence[ChapterPlanEntry]) -> tomlkit.items.Array:
    """Return a fresh multiline ``[[chapters]]`` array of inline tables.

    Each entry carries the four manifest keys (``number``, ``slug``, ``title``,
    ``target_words``) in the on-disk schema order; the array is multiline so the
    written ``[chapters]`` reads one inline table per line, matching the corpus
    builder's layout (``tests/working_corpus/_builder.py``).
    """
    array = tomlkit.array()
    array.multiline(multiline=True)
    for entry in ordered:
        array.append(
            build_inline_table({
                "number": entry.number,
                "slug": entry.slug,
                "title": entry.title,
                "target_words": entry.target_words,
            })
        )
    return array


def _zero_word_counts(
    ordered: cabc.Sequence[ChapterPlanEntry],
) -> tomlkit.items.InlineTable:
    """Return a fresh ``by_chapter`` inline table with a zero entry per chapter.

    Keys are the zero-padded two-digit chapter strings (``"01"``, ``"02"``, …) the
    ``[word_counts].by_chapter`` schema uses (design §5.1). A freshly-planned
    chapter is undrafted, so ``0`` is the honest word count; seeding the keys keeps
    the §5.4 ``word-counts-cover-drafts`` coverage satisfied so ``check`` exits 0
    immediately after ``set-chapters`` (Decision D13).
    """
    return build_inline_table({f"{entry.number:02d}": 0 for entry in ordered})


def _declared_paths(ordered: cabc.Sequence[ChapterPlanEntry]) -> list[str]:
    """Return the ``[pending_turn].paths`` the turn will write, ``working/``-rooted.

    The paths are ``working/state.toml`` plus each
    ``working/manuscript/chapter-NN/`` directory, in the ``working/…`` form
    :func:`novel_ralph_skill.state.reconcile._missing_declared_paths` expects (it
    strips the ``working/`` prefix). Work item 3a's recovery parses the chapter
    numbers back out of these paths, so they are the contract between the writer and
    ``reconcile``.
    """
    paths = ["working/state.toml"]
    paths.extend(
        f"working/manuscript/{chapter_dir_name(entry.number)}" for entry in ordered
    )
    return paths


def _append_receipt(working_dir: pathlib.Path, line: str) -> None:
    """Append one timestamped ``set-chapters`` receipt to ``working/log.md``.

    Mirrors ``_reconcile._append_recovery_entry``: the receipt is appended (UTF-8,
    append mode) so the existing turn log is preserved, carrying an RFC 3339 UTC
    timestamp and the operation detail. It lands **before** the bracket's clear so a
    crash after the receipt still leaves a recoverable torn turn (design §3.4).
    """
    timestamp = dt.datetime.now(dt.UTC).isoformat()
    with (working_dir / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp} set-chapters: {line}\n")


def _refuse_incoherent_plan(chapters: cabc.Sequence[ChapterPlanEntry]) -> None:
    """Raise :class:`StateInputError` (exit 3) when the plan breaks a coherence rule.

    The exit-3 ``run`` arm emits only ``messages``, so the breached rule names ride
    first, then a human detail (mirroring ``_refuse_if_incoherent``).
    """
    breaches = manifest_coherence_violations(chapters)
    if breaches:
        names = ", ".join(breaches)
        summary = f"set-chapters refuses an incoherent plan: {names}"
        raise StateInputError(summary, f"the chapter plan breaks: {names}")


def set_chapters(*, chapters: list[ChapterPlanEntry]) -> CommandOutcome:
    """Populate ``[chapters]`` from the agent's plan; refuse an incoherent plan.

    The multi-file mutator for roadmap task 2.2.3. In the fixed order Decision D10
    fixes — which deliberately differs from ``reconcile``'s, because the manifest is
    the agent's *non-recomputable* judgement and must persist first:

    1. load ``working/state.toml`` (exit 3 on missing/unparseable);
    2. derive the typed view to prove structural completeness and read the prior
       manifest;
    3. refuse with exit 3 if the prior ``[chapters]`` is non-empty (Decision D3 —
       ``set-chapters`` is a one-shot populate, not an editor) — *memory only*;
    4. refuse with exit 3 on any manifest-coherence breach (Work item 2) — *memory
       only*;
    5. edit ``document["chapters"]`` to the ascending inline-table array, seed
       ``[word_counts].by_chapter`` with a zero entry per chapter (so the §5.4
       coverage holds and ``check`` exits 0 afterwards; Decision D13), and run the
       §5.2 validate-before-persist pass on the proposed document (defence in depth)
       — *memory only, so a crash so far leaves the prior file byte-for-byte intact*;
    6. ``open_pending_turn`` naming ``state.toml`` plus each chapter directory;
    7. **one** atomic write — the populated manifest and the ``[pending_turn]``
       intent land together (Decision D10/B2), so from here the manifest is on disk
       and any torn turn is recoverable by ``reconcile``;
    8. ``mkdir`` each ``working/manuscript/chapter-NN/`` directory (idempotent);
    9. append the ``log.md`` receipt (before the clear);
    10. ``clear_pending_turn`` and a final atomic write.

    Parameters
    ----------
    chapters : list[ChapterPlanEntry]
        The planned chapters, as parsed from the ``--chapters`` JSON array.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` with a write-shaped ``result`` naming the written
        chapters — ``{"chapters": [{number, slug, title, target_words}, ...]}`` in
        ascending number order. It never echoes ``check``'s ``violations`` read
        shape (developers' guide; audit-2.2.2 Finding 2).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, the prior manifest is
        already populated (D3), or the proposed plan is incoherent (each the
        exit-3 channel).
    """
    path = _state_path()
    working_dir = _working_dir()
    document = _load_document_or_state_error(path)
    prior = _state_view_or_state_error(document)
    if prior.chapters:
        msg = (
            "set-chapters refuses to overwrite a populated [chapters] manifest; "
            "re-planning is a separate, later concern"
        )
        raise StateInputError(msg)
    _refuse_incoherent_plan(chapters)

    ordered = _ordered_chapters(chapters)
    document["chapters"] = _chapter_array(ordered)
    # Seed [word_counts].by_chapter with a zero entry per freshly-planned chapter so
    # the §5.4 ``word-counts-cover-drafts`` coverage holds the instant the command
    # returns (the chapters are planned but undrafted, so 0 is the honest count).
    # Without this, the populated manifest would out-key the empty table and a
    # follow-up ``check`` would exit 4 — failing the success criterion that ``check``
    # exits 0 after ``set-chapters`` (Surprise S7, Decision D13). ``current`` was 0
    # for the empty-manifest precondition and stays 0 = sum(by_chapter), so §5.2
    # invariant 3 holds.
    document["word_counts"]["by_chapter"] = _zero_word_counts(ordered)
    # Defence in depth against the §5.2 set: the proposed document must still be
    # self-consistent before any write (the manifest plus zeroed counts breach no
    # §5.2 invariant, but the pass keeps every mutator on the same "validate before
    # persist" contract).
    _refuse_if_incoherent(_state_view_or_state_error(document), context="set-chapters")

    _write_manifest_turn(document, path, working_dir, ordered)
    written = [
        {
            "number": entry.number,
            "slug": entry.slug,
            "title": entry.title,
            "target_words": entry.target_words,
        }
        for entry in ordered
    ]
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"chapters": written},
        messages=[f"populated [chapters] with {len(ordered)} chapters"],
    )


def _write_manifest_turn(
    document: TOMLDocument,
    path: pathlib.Path,
    working_dir: pathlib.Path,
    ordered: cabc.Sequence[ChapterPlanEntry],
) -> None:
    """Drive the D10 bracket: intent+manifest write → dirs → receipt → clear.

    ``document`` already carries the populated ``[chapters]`` edit (step 5).
    ``open_pending_turn`` only appends the ``[pending_turn]`` table, so the single
    :func:`write_document_atomically` carries **both** the manifest and the intent
    record (Decision D10): every torn state from that write onward has the full
    manifest on disk with only the empty, manifest-derivable directories
    outstanding, which ``reconcile`` completes (Decision D8). The directories are
    created idempotently, the receipt lands before the clear, and the clear writes
    last.
    """
    open_pending_turn(
        document,
        operation=SET_CHAPTERS_OPERATION,
        paths=_declared_paths(ordered),
    )
    write_document_atomically(document, path)
    manuscript = working_dir / "manuscript"
    for entry in ordered:
        (manuscript / chapter_dir_name(entry.number)).mkdir(parents=True, exist_ok=True)
    _append_receipt(
        working_dir,
        f"populated [chapters] with {len(ordered)} chapters",
    )
    clear_pending_turn(document)
    write_document_atomically(document, path)
