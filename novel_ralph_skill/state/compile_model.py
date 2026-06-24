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

import enum
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


class CompiledComparison(enum.Enum):
    """Three-valued verdict for ``compiled.md`` against the present drafts.

    The "is ``compiled.md`` the ordered concatenation of the present drafts?"
    comparison has three outcomes the two production callers must tell apart,
    not two: an *absent* ``compiled.md`` is distinct from a *present-but-stale*
    one. A plain :class:`bool` ("present and matching") would collapse absent
    and diverging into one ``False``, which neither caller can use. Hence this
    closed three-state result, with each caller projecting it to its own
    absent-file polarity (design §4.3/§5.4; ``docs/issues/audit-3.1.1.md``
    Finding 2).
    """

    ABSENT = "absent"
    MATCHES = "matches"
    DIVERGES = "diverges"


def compiled_matches_drafts(state: State, working_dir: Path) -> CompiledComparison:
    """Return how ``compiled.md`` compares to the ordered draft concatenation.

    This is the **single production site** that decides whether
    ``working/manuscript/compiled.md`` equals the ordered concatenation of the
    present chapter drafts (design §4.3/§5.4; ``docs/issues/audit-3.1.1.md``
    Finding 2). Both
    :func:`~novel_ralph_skill.state.disk_evidence._check_compiled_matches_drafts`
    (the §5.4 detector) and the
    :func:`~novel_ralph_skill.state.done_predicate.compile_consistent` done-clause
    consume it, each projecting the three-valued result to its own absent-file
    polarity — the detector treats absent as satisfied, the content clause treats
    both absent and divergent as not-done (only ``MATCHES`` holds) — so the two
    cannot disagree on the same tree.

    The existence check precedes any draft read: an absent ``compiled.md``
    returns :attr:`CompiledComparison.ABSENT` without touching the drafts.
    Otherwise the expected text is recomputed through the one join rule
    (:func:`concatenate_drafts` of :func:`present_draft_bodies`) and compared
    byte-for-byte. A *missing* ``draft.md`` contributes ``""`` (benign); every
    other read fault — ``PermissionError``, ``IsADirectoryError``,
    ``UnicodeDecodeError`` — propagates unchanged for the command layer to route
    to the exit-``3`` channel. The helper neither catches nor reshapes those
    faults.

    Parameters
    ----------
    state : State
        The parsed, typed ``state.toml`` carrying the ``[chapters]`` manifest.
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/compiled.md``.

    Returns
    -------
    CompiledComparison
        :attr:`~CompiledComparison.ABSENT` when ``compiled.md`` is absent;
        :attr:`~CompiledComparison.MATCHES` when its bytes equal the ordered
        draft concatenation; :attr:`~CompiledComparison.DIVERGES` otherwise.

    Raises
    ------
    OSError
        Any read fault other than a missing ``compiled.md`` or ``draft.md``
        (e.g. ``PermissionError``, ``IsADirectoryError``) propagates.
    UnicodeDecodeError
        When ``compiled.md`` or a present ``draft.md`` is not valid UTF-8 (a
        ``ValueError`` subclass), likewise propagated.
    """
    compiled = working_dir / "manuscript" / "compiled.md"
    if not compiled.exists():
        return CompiledComparison.ABSENT
    expected = concatenate_drafts(present_draft_bodies(state, working_dir))
    if compiled.read_text(encoding="utf-8") == expected:
        return CompiledComparison.MATCHES
    return CompiledComparison.DIVERGES


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
