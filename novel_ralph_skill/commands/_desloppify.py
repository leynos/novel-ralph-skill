"""The ``desloppify`` command body (roadmap task 5.1.2; design §4.4).

``desloppify`` is the detect-only slop checker (ADR-001): it reads the chapter
drafts under the fixed ``working/`` tree, scans them against a versioned rule
pack — the §6 high-frequency-offender table by default (design §6.1) — and
reports a per-rule finding without editing, judging, or mutating any state. It
writes nothing to disk.

This module owns two concerns, mirroring ``_recount.py``'s placement beside the
mutator module: sourcing chapter text from the ``working/`` tree (manifest-driven,
with the exit-2 vs exit-3 fault split); and wiring the Cyclopts app and the
:class:`~novel_ralph_skill.contract.runner.CommandOutcome` that the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper renders. The envelope
projection and the shipped-pack resolver (:func:`offenders_pack_path`) live in the
sibling :mod:`novel_ralph_skill.commands._desloppify_report` so this module stays
within the 400-line cap.

Fault routing follows the contract (design §3.2): a malformed pack
(:class:`~novel_ralph_skill.rulepack.RulePackError`) is a usage error (exit 2);
an unreadable/undecodable pack file or an unreadable draft or an absent/unparseable
``state.toml`` (:class:`~novel_ralph_skill.rulepack.RulePackFileError` /
:class:`~novel_ralph_skill.contract.runner.StateInputError`) is a state/input
error (exit 3); and a ``--chapter`` outside the manifest is a body-detected usage
fault (exit 2) raised as :class:`DesloppifyUsageError`. The text-sourcing helper
reuses ``recount``'s two conventions — the ``chapter-{number:02d}`` path
derivation and the ``len(text.split())`` token rule — so the density word count
cannot drift from ``recount`` (ExecPlan round-1 advisory).
"""

from __future__ import annotations

import pathlib
import typing as typ

import cyclopts

from novel_ralph_skill.commands._desloppify_report import (
    offenders_pack_path,
    report_outcome,
)
from novel_ralph_skill.commands.novel_state import (
    STATE_INPUT_ERRORS,
    WORKING_DIR_NAME,
    _load_or_state_error,
)
from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.rulepack import RulePackError, RulePackFileError, load_rulepack
from novel_ralph_skill.rulepack.detect import ScannedChapter, detect

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state import ChapterEntry


class DesloppifyUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit ``2`` (design §3.2).

    Raised when the invocation is wrong in a way the Cyclopts parser cannot
    catch — specifically ``--chapter N`` naming a chapter absent from the
    ``[chapters]`` manifest. The command body converts it to a
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome` carrying
    :data:`~novel_ralph_skill.contract.exit_codes.ExitCode.USAGE_ERROR`, never the
    exit-``3`` state channel, because a bad ``--chapter`` is a caller error, not a
    corrupt ``working/`` tree. The optional ``messages`` payload (recorded once by
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError`) carries the
    human prose for the emitted envelope.
    """


def _chapter_text(working_dir: pathlib.Path, number: int) -> str:
    """Return one chapter's ``draft.md`` text (``""`` when absent).

    Reads ``working_dir/manuscript/chapter-NN/draft.md`` as UTF-8, mirroring
    :func:`novel_ralph_skill.state.wordcount._chapter_word_count`'s fault
    boundary: an absent ``draft.md`` is an undrafted chapter and contributes
    empty text (an undrafted chapter has no tics), while every other read fault
    propagates for the caller to route to exit ``3``. The path derivation is the
    same ``chapter-{number:02d}`` convention ``recount`` uses, so the two cannot
    disagree on which file a chapter maps to.

    Parameters
    ----------
    working_dir : pathlib.Path
        The ``working/`` directory holding ``manuscript/``.
    number : int
        The one-based chapter number; the directory is ``chapter-NN`` zero-padded
        to two digits.

    Returns
    -------
    str
        The chapter's UTF-8 draft body, or ``""`` when its ``draft.md`` is absent.

    Raises
    ------
    OSError
        Any read fault other than a missing file (e.g. ``PermissionError``,
        ``IsADirectoryError``) propagates for the caller to translate.
    UnicodeDecodeError
        When the body is not valid UTF-8 (a ``ValueError`` subclass), likewise
        propagated for exit-``3`` translation.
    """
    draft = working_dir / "manuscript" / f"chapter-{number:02d}" / "draft.md"
    try:
        return draft.read_text(encoding="utf-8")
    except FileNotFoundError:
        # An undrafted chapter contributes no text; this is the only benign read
        # fault, mirroring ``wordcount._chapter_word_count``. A broad
        # ``except OSError`` would swallow a ``PermissionError`` as empty text.
        return ""


def _select_chapters(
    manifest: cabc.Sequence[ChapterEntry], chapter: int | None
) -> tuple[ChapterEntry, ...]:
    """Select the manifest chapters to scan, in ascending order.

    Whole-manuscript scope (``chapter is None``) scans every manifest chapter in
    ascending ``number`` order — the same authoritative ``[chapters]`` source
    ``recount`` uses (design §5.1). ``--chapter N`` scans only that chapter; a
    ``--chapter N`` absent from the manifest is a caller error, not a corrupt
    tree, so it raises :class:`DesloppifyUsageError` for the exit-``2`` channel.

    Parameters
    ----------
    manifest : collections.abc.Sequence[ChapterEntry]
        The ``[chapters]`` manifest (``state.chapters``).
    chapter : int | None
        The ``--chapter N`` selection, or ``None`` for the whole manuscript.

    Returns
    -------
    tuple[ChapterEntry, ...]
        The selected chapters, ascending by ``number``.

    Raises
    ------
    DesloppifyUsageError
        When ``chapter`` names a chapter absent from the manifest (exit ``2``).
    """
    ordered = tuple(sorted(manifest, key=lambda entry: entry.number))
    if chapter is None:
        return ordered
    selected = tuple(entry for entry in ordered if entry.number == chapter)
    if not selected:
        available = ", ".join(str(entry.number) for entry in ordered) or "none"
        msg = f"no chapter {chapter} in the manifest (available: {available})"
        raise DesloppifyUsageError(msg)
    return selected


def source_chapters(chapter: int | None) -> tuple[ScannedChapter, ...]:
    """Source the scanned chapters from the ``working/`` tree (design §5.1).

    Loads the typed ``working/state.toml`` through ``novel-state``'s shared
    :func:`~novel_ralph_skill.commands.novel_state._load_or_state_error` (so a
    missing or unparseable state is exit ``3``), selects the manifest chapters per
    ``chapter`` (a bad ``--chapter`` is the exit-``2`` usage fault), and reads each
    chapter's ``draft.md``. An absent draft yields empty text; every other read
    fault is re-raised as :class:`~novel_ralph_skill.contract.runner.StateInputError`
    under the shared ``STATE_INPUT_ERRORS`` tuple, exactly as
    ``_recount._recount_or_state_error`` does, so it reaches exit ``3`` and cannot
    escape to the benign exit ``1``.

    Parameters
    ----------
    chapter : int | None
        The ``--chapter N`` selection, or ``None`` for the whole manuscript.

    Returns
    -------
    tuple[ScannedChapter, ...]
        One :class:`~novel_ralph_skill.rulepack.detect.ScannedChapter` per
        selected chapter, in ascending ``number`` order.

    Raises
    ------
    StateInputError
        When ``working/state.toml`` is missing or unparseable, or a chapter's
        ``draft.md`` is unreadable or undecodable (the exit-``3`` channel).
    DesloppifyUsageError
        When ``--chapter N`` names a chapter absent from the manifest (exit ``2``).
    """
    working_dir = pathlib.Path(WORKING_DIR_NAME)
    state = _load_or_state_error(working_dir / "state.toml")
    selected = _select_chapters(state.chapters, chapter)
    try:
        return tuple(
            ScannedChapter(
                number=entry.number,
                text=_chapter_text(working_dir, entry.number),
            )
            for entry in selected
        )
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot read chapter drafts: {exc}"
        raise StateInputError(msg) from exc


def _desloppify(*, chapter: int | None, pack: pathlib.Path | None) -> CommandOutcome:
    """Run the slop scan and return its :class:`CommandOutcome` (design §4.4).

    Loads the rule pack (the shipped §6 ``offenders.toml`` by default, or an
    explicit ``--pack``), sources the scanned chapters from the ``working/`` tree,
    detects the offenders, and projects the report into the envelope outcome.
    Fault routing is the contract's (design §3.2): a malformed pack
    (:class:`~novel_ralph_skill.rulepack.RulePackError`) is a usage error (exit
    ``2``); an unreadable/undecodable pack file
    (:class:`~novel_ralph_skill.rulepack.RulePackFileError`) is a state/input error
    (exit ``3``); and a ``--chapter`` outside the manifest is the exit-``2``
    :class:`DesloppifyUsageError`. The two loader errors are caught here and mapped
    locally rather than in the shared ``run`` wrapper, keeping the runner untouched
    and the rulepack→contract coupling out of the shared seam (ExecPlan WI4
    Decision Log).

    Parameters
    ----------
    chapter : int | None
        The ``--chapter N`` selection, or ``None`` for the whole manuscript.
    pack : pathlib.Path | None
        An explicit ``--pack`` path, or ``None`` for the shipped §6 pack.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS``/``ExitCode.ACTIONABLE_FINDING`` on a completed scan,
        or ``ExitCode.USAGE_ERROR`` when the pack content is malformed.

    Raises
    ------
    StateInputError
        When the pack file or a draft is unreadable, or ``state.toml`` is
        missing/unparseable (the exit-``3`` channel).
    DesloppifyUsageError
        When ``--chapter N`` names a chapter absent from the manifest (exit
        ``2``).
    """
    try:
        rulepack = load_rulepack(pack or offenders_pack_path())
    except RulePackError as exc:
        # Malformed pack *content* is a usage error (exit 2); map it locally to a
        # CommandOutcome rather than coupling the shared runner to rulepack.
        return CommandOutcome(
            code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
        )
    except RulePackFileError as exc:
        # An absent/unreadable/undecodable pack *file* is the exit-3 state channel,
        # which the shared runner already maps from StateInputError.
        msg = f"cannot read rule pack: {exc}"
        raise StateInputError(msg) from exc
    chapters = source_chapters(chapter)
    return report_outcome(detect(rulepack, chapters))


def _scan_or_usage(*, chapter: int | None, pack: pathlib.Path | None) -> CommandOutcome:
    """Run :func:`_desloppify`, mapping the body usage fault to exit ``2``.

    A ``--chapter`` outside the manifest is detected in the body (not the Cyclopts
    parser), so it cannot reach the runner's ``CycloptsError`` arm; this thin
    adapter catches :class:`DesloppifyUsageError` and returns the exit-``2``
    :class:`CommandOutcome` directly, keeping the runner untouched (ExecPlan WI4).

    Parameters
    ----------
    chapter : int | None
        The ``--chapter N`` selection, or ``None`` for the whole manuscript.
    pack : pathlib.Path | None
        An explicit ``--pack`` path, or ``None`` for the shipped §6 pack.

    Returns
    -------
    CommandOutcome
        The scan outcome, or an ``ExitCode.USAGE_ERROR`` outcome for a bad
        ``--chapter``.
    """
    try:
        return _desloppify(chapter=chapter, pack=pack)
    except DesloppifyUsageError as exc:
        return CommandOutcome(
            code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
        )


def build_app() -> cyclopts.App:
    """Build the ``desloppify`` Cyclopts app (design §4.4).

    Wired with ``result_action="return_value", exit_on_error=False,
    print_error=False, help_on_error=False`` so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope,
    exactly like ``novel-state``. The single default body takes the optional
    ``--chapter`` and ``--pack`` keywords and returns a
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome`.

    Returns
    -------
    cyclopts.App
        The configured ``desloppify`` app.
    """
    app = cyclopts.App(
        name="desloppify",
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )

    @app.default
    def _scan(
        *, chapter: int | None = None, pack: pathlib.Path | None = None
    ) -> CommandOutcome:
        """Scan the manuscript for §6 offenders; exit 0/4 per the finding."""
        return _scan_or_usage(chapter=chapter, pack=pack)

    return app
