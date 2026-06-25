"""Frozen, typed dataclasses mirroring the ``state.toml`` tables (design §5.1).

This module is the typed shape of the harness's primary on-disk memory. Each
dataclass mirrors one table of ``state.toml`` as documented in design §5.1 and
``skill/novel-ralph/references/state-layout.md`` "state.toml schema", and pinned
to the exact key set the §1.3.2 corpus builder emits
(``tests/working_corpus/_builder.py``; see the ExecPlan
``docs/execplans/roadmap-2-1-1.md`` "Pinned corpus key shape"). The schema omits
the dead per-chapter ``plan.md`` reference (design §8).

The objects are frozen, slotted, keyword-only domain shapes (python-data-shapes:
"domain objects belong in immutable, slotted containers"), following the
``novel_ralph_skill/contract/envelope.py`` house style. The boundary constructor
that builds them from a decoded mapping lives in
:mod:`novel_ralph_skill.state.parse`; this module carries the shapes only and
performs no parsing, writing, or validation. The §5.2 invariants are enforced by
``novel-state check`` (roadmap task 2.1.2), not here.
"""

from __future__ import annotations

import dataclasses
import typing as typ

from novel_ralph_skill._freeze import freeze_mapping

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state.phase import Phase


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class NovelMeta:
    """The ``[novel]`` table: provisional identity and target length.

    Attributes
    ----------
    title : str
        The novel's working title (``[novel].title``).
    slug : str
        The identifier (``[novel].slug``), stored verbatim. The schema treats
        it as an opaque string; slug validation is not a §5.2 invariant.
    target_word_count : int
        The target length in words (``[novel].target_word_count``).
    created_at : str
        The RFC 3339 creation timestamp, kept verbatim as a string rather than
        parsed to a ``datetime`` (``[novel].created_at``; see the ExecPlan
        Decision Log).
    """

    title: str
    slug: str
    target_word_count: int
    created_at: str


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class PhaseState:
    """The ``[phase]`` table: the active phase and the completed prefix.

    Attributes
    ----------
    current : Phase
        The active lifecycle phase (``[phase].current``).
    completed : tuple[Phase, ...]
        The ordered prefix of completed phases (``[phase].completed``).
    """

    current: Phase
    completed: tuple[Phase, ...]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterEntry:
    """One ``[chapters]`` manifest entry: a single planned chapter.

    Attributes
    ----------
    number : int
        The one-based chapter number; the manifest is ordered ascending by it.
    slug : str
        The chapter identifier, stored verbatim. The schema treats it as an
        opaque string; slug shape is the agent's responsibility, as for
        ``[novel].slug``.
    title : str
        The chapter title.
    target_words : int
        The planned word count for the chapter.
    """

    number: int
    slug: str
    title: str
    target_words: int


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class CriticState:
    """The ``[drafting.critic]`` table: the spiteful critic's loop state.

    Attributes
    ----------
    pass_number : int
        The current critic pass number for the current chapter
        (``[drafting.critic].pass``; ``pass`` is a Python keyword, so the
        attribute is ``pass_number``).
    consecutive_clean : int
        The count of consecutive passes with no blocker or major finding.
    convergence_target : int
        The configured ceiling for ``consecutive_clean`` (default 1).
    last_finding_counts : FindingCounts
        The most recent pass's finding tally by severity.
    """

    pass_number: int
    consecutive_clean: int
    convergence_target: int
    last_finding_counts: FindingCounts


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class FindingCounts:
    """The ``last_finding_counts`` inline table: a tally by severity.

    Attributes
    ----------
    blocker : int
        The count of blocker findings in the most recent critic pass.
    major : int
        The count of major findings.
    minor : int
        The count of minor findings.
    taste : int
        The count of taste findings.
    """

    blocker: int
    major: int
    minor: int
    taste: int


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class FangirlState:
    """The ``[drafting.fangirl]`` table: the forward-projecting reader's state.

    Attributes
    ----------
    last_chapter_passed : int
        The last chapter number the fangirl pass ran on
        (``[drafting.fangirl].last_chapter_passed``).
    """

    last_chapter_passed: int


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Drafting:
    """The ``[drafting]`` table: the drafting cursor and its sub-states.

    Attributes
    ----------
    current_chapter : int
        The cursor's chapter component (``[drafting].current_chapter``).
    current_scene : int
        The cursor's scene component; ``0`` if no scene plan exists yet.
    current_beat : int
        The cursor's beat component; ``0`` if no beats exist yet.
    critic : CriticState
        The spiteful critic's loop sub-state (``[drafting.critic]``).
    fangirl : FangirlState
        The fangirl reader's sub-state (``[drafting.fangirl]``).
    """

    current_chapter: int
    current_scene: int
    current_beat: int
    critic: CriticState
    fangirl: FangirlState


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class KnittingGates:
    """The ``[gates.knitting]`` table: the three knitting-circle gate flags.

    Attributes
    ----------
    done_30 : bool
        Whether the 30% knitting gate has passed and been integrated.
    done_50 : bool
        Whether the 50% knitting gate has passed and been integrated.
    done_80 : bool
        Whether the 80% knitting gate has passed and been integrated.
    """

    done_30: bool
    done_50: bool
    done_80: bool


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class FinalGate:
    """The ``[gates.final]`` table: the final-pass completion flag.

    Attributes
    ----------
    final_pass_complete : bool
        Whether the final pass over the compiled manuscript is complete.
    """

    final_pass_complete: bool


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Gates:
    """The ``[gates]`` table: the knitting gates and the final gate.

    Attributes
    ----------
    knitting : KnittingGates
        The three knitting-circle gate flags (``[gates.knitting]``).
    final : FinalGate
        The final-pass gate (``[gates.final]``).
    """

    knitting: KnittingGates
    final: FinalGate


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class WordCounts:
    """The ``[word_counts]`` table: the target, current, and per-chapter counts.

    Attributes
    ----------
    target : int
        The target word count (``[word_counts].target``).
    current : int
        The current word count: the drafted sum ``sum(by_chapter.values())``
        (``[word_counts].current``). A bytes-divergent ``compiled.md`` is the
        ``compiled-matches-drafts`` finding, not a ``current`` source.
    by_chapter : collections.abc.Mapping[str, int]
        The per-chapter word counts keyed by the zero-padded two-digit chapter
        string (``[word_counts].by_chapter``; e.g. ``{"01": 3200}``). Typed as a
        read-only ``Mapping`` and normalised to a ``types.MappingProxyType`` in
        :meth:`__post_init__` (via
        :func:`novel_ralph_skill._freeze.freeze_mapping`), so the frozen/slotted
        read-only immutability guarantee holds for every construction path, not
        just the parse boundary (``contract/envelope.py`` house style). The
        guarantee is immutability, not hashability: a
        ``MappingProxyType`` is unhashable, so :class:`WordCounts` and
        :class:`State` are unhashable too, exactly as the cited ``Envelope``
        (whose ``cabc.Mapping`` field is likewise unhashable). Do not use a
        :class:`State` as a dict key or set member.
    """

    target: int
    current: int
    by_chapter: cabc.Mapping[str, int]

    def __post_init__(self) -> None:
        """Freeze ``by_chapter`` so the immutability guarantee holds however built."""
        object.__setattr__(self, "by_chapter", freeze_mapping(self.by_chapter))


SET_CHAPTERS_OPERATION: typ.Final = "set-chapters"
"""The ``[pending_turn].operation`` tag the ``set-chapters`` mutator brackets with.

Named once here, beside :class:`PendingTurn`, so the writer
(:mod:`novel_ralph_skill.commands._set_chapters`) and the reconcile derivation
(:mod:`novel_ralph_skill.state.reconcile`) key the torn-turn recovery on one
literal rather than repeating the string (roadmap task 2.2.3; ExecPlan Decision
Log D8).
"""


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class PendingTurn:
    """The ``[pending_turn]`` table: an in-flight multi-file write intent.

    Present only while a multi-file mutation is mid-write (design §3.4); a
    settled state carries no ``[pending_turn]`` and :attr:`State.pending_turn` is
    ``None``.

    Attributes
    ----------
    operation : str
        The operation in flight (``[pending_turn].operation``).
    paths : tuple[str, ...]
        The paths the operation will write (``[pending_turn].paths``).
    """

    operation: str
    paths: tuple[str, ...]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class State:
    """The whole typed ``state.toml`` document (design §5.1).

    Attributes
    ----------
    schema_version : int
        The ``state.toml`` schema version (currently ``1``).
    novel : NovelMeta
        The ``[novel]`` identity and target length.
    phase : PhaseState
        The ``[phase]`` active phase and completed prefix.
    chapters : tuple[ChapterEntry, ...]
        The ``[chapters]`` manifest, ordered ascending by ``number``.
    drafting : Drafting
        The ``[drafting]`` cursor with its critic and fangirl sub-states.
    gates : Gates
        The ``[gates]`` knitting and final gate flags.
    word_counts : WordCounts
        The ``[word_counts]`` target, current, and per-chapter counts.
    pending_turn : PendingTurn | None
        The ``[pending_turn]`` in-flight write intent, or ``None`` on a settled
        state.
    """

    schema_version: int
    novel: NovelMeta
    phase: PhaseState
    chapters: tuple[ChapterEntry, ...]
    drafting: Drafting
    gates: Gates
    word_counts: WordCounts
    pending_turn: PendingTurn | None = None
