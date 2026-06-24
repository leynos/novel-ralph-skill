"""The §4.3/§9 draft-concatenation model the disk-evidence detector shares.

The ``compiled-matches-drafts`` disk-evidence invariant (roadmap task 2.3.2)
decides whether ``working/manuscript/compiled.md`` is the ordered concatenation
of the present chapter drafts. It needs only the *divergence verdict*: the full
compile-and-hash command is roadmap task 4.1.1's. This module owns the one join
rule that verdict recomputes — the ordered draft bodies joined by a single fixed
separator (design §4.3 "consistent separators"; §9 lines 705-711).

:func:`concatenate_drafts` is the production twin of the corpus helper
``tests/working_corpus/_specs.py::concatenate_drafts``. The two are deliberate
twins (developers' guide twin policy): production must agree with the corpus
byte-for-byte, pinned by a test (``test_disk_evidence.py``), but neither imports
the other. The separator constant is the single source of truth on the
production side; the corpus keeps its own copy on purpose so a drift is a
finding, not a silent alignment.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state._disk_paths import _chapter_dir_name

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# The single separator the ordered draft bodies are joined with when recomputing
# the expected ``compiled.md``. The design names "consistent separators" (§4.3)
# but pins no exact bytes, so this module owns the production copy; the corpus's
# ``CORPUS_SEPARATOR`` is its independent twin (pinned equal by test).
DRAFT_SEPARATOR = "\n\n"


def present_draft_bodies(state: State, working_dir: Path) -> list[str]:
    """Return the present chapters' draft bodies in ascending chapter order.

    Reads each manifest chapter's ``draft.md`` as UTF-8 (an absent draft
    contributes the empty string), ordered by chapter number, so a caller that
    concatenates the result reproduces the same ordered body sequence the
    ``compiled-matches-drafts`` disk-evidence invariant recomputes (design §4.3;
    §9 lines 705-711). This is the single read rule both the ``novel-compile``
    write path (roadmap task 4.1.1) and
    :func:`~novel_ralph_skill.state.disk_evidence._check_compiled_matches_drafts`
    share, so a freshly compiled tree is coherent under the detector by
    construction (ExecPlan Constraints "Draft-body read rule matches the
    disk-evidence detector exactly"; D-READ).

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` carrying the ``[chapters]`` manifest.
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.

    Returns
    -------
    list[str]
        The present chapters' draft bodies, ascending by chapter number; an
        absent ``draft.md`` contributes ``""``.

    Raises
    ------
    OSError
        Any read fault other than a missing ``draft.md`` (e.g.
        ``PermissionError``, ``IsADirectoryError``) propagates for the caller to
        route to the exit-``3`` channel.
    UnicodeDecodeError
        When a body is not valid UTF-8 (a ``ValueError`` subclass), likewise
        propagated.
    """
    manuscript = working_dir / "manuscript"
    bodies: list[str] = []
    for chapter in sorted(state.chapters, key=lambda chapter: chapter.number):
        draft = manuscript / _chapter_dir_name(chapter.number) / "draft.md"
        bodies.append(draft.read_text(encoding="utf-8") if draft.exists() else "")
    return bodies


def concatenate_drafts(drafts: cabc.Sequence[str]) -> str:
    """Return the ordered concatenation of ``drafts`` joined by the separator.

    This is the production stand-in for the §4.3 compile routine (the ordered
    concatenation of the present drafts with consistent separators) that roadmap
    task 4.1.1 implements in full. The disk-evidence detector uses it to recompute
    the expected ``compiled.md`` for the content-divergence verdict, comparing the
    result byte-for-byte against the on-disk ``compiled.md`` (§4.3 lines 320-344;
    §9 lines 705-711).

    Parameters
    ----------
    drafts : collections.abc.Sequence[str]
        The present chapter draft bodies, already in ascending chapter order.

    Returns
    -------
    str
        The ordered concatenation joined by :data:`DRAFT_SEPARATOR`.
    """
    return DRAFT_SEPARATOR.join(drafts)
