"""Pure word-count aggregation over the on-disk chapter drafts (roadmap 2.3.1).

This module owns the one counting rule the harness re-derives ``[word_counts]``
from: a chapter's word count is ``len(draft_text.split())`` — the whitespace-split
token count over the UTF-8 body of
``working/manuscript/chapter-NN/draft.md`` (design §4.1; ExecPlan Constraint
"Word-count algorithm is fixed"). The rule is pinned equal to the test oracle
``tests/working_corpus/_live_draft.py:live_draft_counts`` by a property test, so
production and corpus cannot drift apart.

:func:`recount_words` is a *pure I/O* function: it reads each manifest chapter's
``draft.md`` and returns the recounted total plus the per-chapter mapping. It
keys ``by_chapter`` by the **chapter manifest** (one entry per manifest chapter,
``0`` for a chapter whose ``draft.md`` is absent or empty), so the recounted
table stays in bijection with ``[chapters]`` (ExecPlan Decision Log D-KEY;
design §5.2 invariant 5). The helper lives in the ``state`` package, beside the
schema it serves, because the later ``wordcount`` command (roadmap §4.5) and
task 2.3.2's reconciliation will both want it (ExecPlan Decision Log D-LOC).

Fault boundary: the per-chapter read catches **only** :class:`FileNotFoundError`
and treats it as ``0`` (an undrafted chapter contributes nothing — D-KEY). Every
other :class:`OSError` (:class:`PermissionError`, :class:`IsADirectoryError`) and
any :class:`UnicodeDecodeError` propagates unchanged, so the command layer can
route them to the exit-``3`` state-error channel rather than the helper swallowing
them as ``0`` (ExecPlan Risk "undecodable draft"; Round-1 blocking point 3). The
helper itself raises no ``StateInputError``; the exit-code translation belongs to
the command layer.
"""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import ChapterEntry


def _chapter_word_count(working_dir: Path, number: int) -> int:
    """Return the token count of one chapter's ``draft.md`` (``0`` when absent).

    Reads ``working_dir/manuscript/chapter-NN/draft.md`` as UTF-8 and returns its
    whitespace-split token count, the single counting rule the oracle pins. An
    absent ``draft.md`` (an undrafted chapter) contributes ``0`` (ExecPlan
    Decision Log D-KEY); every other read fault — a permission error, a directory
    where the file is expected, or an undecodable body — propagates unchanged so
    the command layer can route it to exit ``3``.

    Parameters
    ----------
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.
    number : int
        The one-based chapter number; the directory is ``chapter-NN`` zero-padded
        to two digits and the path is built solely from this integer (no
        directory-name parsing).

    Returns
    -------
    int
        The chapter's whitespace-split token count, or ``0`` when its ``draft.md``
        is absent.

    Raises
    ------
    OSError
        Any read fault other than a missing file (e.g. ``PermissionError``,
        ``IsADirectoryError``) propagates for the command layer to translate.
    UnicodeDecodeError
        When the body is not valid UTF-8 (a ``ValueError`` subclass), likewise
        propagated for exit-``3`` translation.
    """
    draft = working_dir / "manuscript" / f"chapter-{number:02d}" / "draft.md"
    try:
        text = draft.read_text(encoding="utf-8")
    except FileNotFoundError:
        # An undrafted chapter contributes nothing; this is the only benign read
        # fault. A broad ``except OSError`` here would both misclassify an absent
        # draft and silently swallow a ``PermissionError`` as ``0`` (D-KEY).
        return 0
    return len(text.split())


def recount_words(
    working_dir: Path,
    manifest: cabc.Sequence[ChapterEntry],
) -> tuple[int, cabc.Mapping[str, int]]:
    """Re-derive ``(current, by_chapter)`` from the on-disk chapter drafts.

    For each chapter in ``manifest`` it reads
    ``working_dir/manuscript/chapter-NN/draft.md`` and counts its whitespace-split
    tokens, then returns the total (``current``) and an ordered ``by_chapter``
    mapping keyed by the zero-padded two-digit chapter string. The mapping is
    keyed by the manifest (one entry per manifest chapter, ``0`` for an absent or
    empty draft), and the key order is ascending chapter number, so a second run
    over unchanged drafts yields a byte-for-byte identical write (ExecPlan Risk
    "non-idempotent write"; Decision Log D-KEY). ``current`` equals
    ``sum(by_chapter.values())`` by construction, satisfying design §5.2
    invariant 3.

    This is a pure I/O function: it reads only ``draft.md`` and raises no
    ``StateInputError``. Only an absent ``draft.md`` is absorbed (as ``0``); every
    other read fault propagates for the command layer to translate to exit ``3``.

    Parameters
    ----------
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.
    manifest : collections.abc.Sequence[ChapterEntry]
        The chapter manifest (``state.chapters``); each entry's ``number`` drives
        both the ``chapter-NN`` directory name and the ``by_chapter`` key.

    Returns
    -------
    tuple[int, collections.abc.Mapping[str, int]]
        The recounted total and the ordered per-chapter mapping.

    Examples
    --------
    A two-chapter manifest whose drafts hold three and five words returns the
    summed total and the per-chapter table::

        total, by_chapter = recount_words(working_dir, manifest)
        assert total == 8
        assert dict(by_chapter) == {"01": 3, "02": 5}
    """
    by_chapter = {
        f"{chapter.number:02d}": _chapter_word_count(working_dir, chapter.number)
        for chapter in sorted(manifest, key=lambda chapter: chapter.number)
    }
    return sum(by_chapter.values()), by_chapter
