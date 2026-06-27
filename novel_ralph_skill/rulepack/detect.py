r"""The pure ``desloppify`` detection core (roadmap task 5.1.2; design §4.4, §6).

This module is the pure aggregation at the heart of ``desloppify``: given a
loaded :class:`~novel_ralph_skill.rulepack.RulePack` and the in-memory text of
the scanned chapters, it counts each rule's hits and reports per-rule findings.
It performs no filesystem access, calls no :func:`sys.exit`, and builds no
envelope, so it is trivially unit-testable and reusable by the later ai-isms /
device-ledger packs (roadmap 7.1). Exit-code translation and text sourcing are
the command body's job (:mod:`novel_ralph_skill.commands._desloppify`).

Detection scans **line by line**, not over whole-chapter text, via the shared
:func:`~novel_ralph_skill.loaderkit.scan.scan_pattern` primitive (see its
docstring for why the no-flags compilation makes a per-line scan the exact
line-numbering discipline). A multi-token offender hard-wrapped across a line
break is therefore **not** detected in v1, a documented limitation: the writer's
drafts wrap at sentence or paragraph granularity, so single-line coverage catches
the common case, and multi-token rows express their span as a bounded lazy
non-newline window ``[^\n]{0,N}?`` rather than greedy ``.*``.

The result shapes follow the package's frozen, slotted, keyword-only house style
(``novel_ralph_skill/rulepack/schema.py``).
"""

from __future__ import annotations

import dataclasses
import typing as typ

from novel_ralph_skill.loaderkit.scan import LineHit, scan_pattern
from novel_ralph_skill.rulepack.schema import RuleBasis

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.loaderkit.scan import ScannedChapter
    from novel_ralph_skill.rulepack.schema import Rule, RulePack

__all__ = [
    "DetectionReport",
    "RuleFinding",
    "detect",
]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class RuleFinding:
    """One rule's aggregated detection result (design §3.1, §6.1).

    Attributes
    ----------
    rule_id : str
        The rule's stable identifier, named in the report and any message.
    pattern : str
        The authored pattern source, echoed for reporting.
    count : int
        The total number of non-overlapping matches across every scanned line of
        every chapter.
    threshold : int
        The rule's allowed hit count (``manuscript``) or per-page density
        (``per_page``).
    basis : RuleBasis
        How the rule is tallied: across the whole manuscript or per notional
        page.
    page_words : int | None
        The notional page size for a ``per_page`` rule, ``None`` otherwise.
    density : float | None
        The hits-per-page density for a ``per_page`` rule, ``None`` for a
        ``manuscript`` rule.
    passed : bool
        Whether the rule is within threshold (``count``/``density`` ``<=``
        ``threshold``).
    lines : tuple[LineHit, ...]
        The ``(chapter, line)`` of every match, in scan order (ascending
        chapter, then ascending line, then left-to-right within a line).
    """

    rule_id: str
    pattern: str
    count: int
    threshold: int
    basis: RuleBasis
    page_words: int | None
    density: float | None
    passed: bool
    lines: tuple[LineHit, ...]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DetectionReport:
    """The whole-pack detection result over the scanned chapters.

    Attributes
    ----------
    pack : str
        The scanned pack's name, echoed for reporting.
    total_words : int
        The whitespace-split token count summed across every *scanned* chapter,
        the denominator the ``per_page`` density divides into pages. The token
        rule is ``len(text.split())``, the same rule
        :func:`novel_ralph_skill.state.recount_words` uses, so the per-token
        counting cannot drift (ExecPlan Risk "density computed inconsistently").
        The *scope* differs by invocation, though: a whole-manuscript scan sums
        every chapter and so matches ``recount_words``'s manuscript total, while
        ``--chapter N`` scans one chapter and so divides density into *that
        chapter's* word count, not the manuscript total.
    findings : tuple[RuleFinding, ...]
        One finding per rule, in the pack's authoring order.
    passed : bool
        ``True`` if and only if every finding passed.
    """

    pack: str
    total_words: int
    findings: tuple[RuleFinding, ...]
    passed: bool


def _finding(
    rule: Rule,
    *,
    count: int,
    lines: tuple[LineHit, ...],
    total_words: int,
) -> RuleFinding:
    """Build one :class:`RuleFinding`, computing pass/fail and density.

    A ``manuscript`` rule passes when ``count <= threshold`` and has no density.
    A ``per_page`` rule divides ``total_words`` into ``page_words``-token pages
    (a float — a partial page still counts) and passes when the per-page density
    is within threshold. An empty manuscript (zero pages) cannot divide, so it
    falls back to ``count <= 0`` with a ``0.0`` density and never raises
    :class:`ZeroDivisionError` (ExecPlan Work item 1).

    Parameters
    ----------
    rule : Rule
        The scanned rule supplying ``threshold``, ``basis``, and ``page_words``.
    count : int
        The rule's total non-overlapping match count.
    lines : tuple[LineHit, ...]
        The per-match ``LineHit`` tuple.
    total_words : int
        The whole-manuscript token count, the ``per_page`` page denominator.

    Returns
    -------
    RuleFinding
        The aggregated finding for ``rule``.
    """
    if rule.basis is RuleBasis.PER_PAGE:
        # ``page_words`` is a positive int for every ``per_page`` rule (the loader
        # validates this), so the only zero-division risk is an empty manuscript.
        page_words = rule.page_words or 0
        pages = total_words / page_words if page_words else 0.0
        density = count / pages if pages > 0 else 0.0
        passed = density <= rule.threshold if pages > 0 else count <= 0
    else:
        density = None
        passed = count <= rule.threshold
    return RuleFinding(
        rule_id=rule.id,
        pattern=rule.pattern,
        count=count,
        threshold=rule.threshold,
        basis=rule.basis,
        page_words=rule.page_words,
        density=density,
        passed=passed,
        lines=lines,
    )


def detect(
    pack: RulePack,
    chapters: cabc.Sequence[ScannedChapter],
) -> DetectionReport:
    """Aggregate ``pack``'s rules over ``chapters`` into a report.

    Pure — a pack and in-memory chapter text in, a :class:`DetectionReport` out —
    so any caller can reuse it without a filesystem. Each rule is scanned line by
    line across every passed chapter (see the module docstring); the per-page
    density uses ``total_words = sum(len(ch.text.split()) for ch in chapters)``,
    the same token rule :func:`novel_ralph_skill.state.recount_words` applies, so
    the per-token counting cannot drift. The denominator covers exactly the
    chapters passed in: a whole-manuscript scan matches ``recount_words``'s
    manuscript total, while a ``--chapter N`` scan passes one chapter and so
    divides density into that chapter's words, not the manuscript total.

    Parameters
    ----------
    pack : RulePack
        The loaded, validated rule pack to scan with.
    chapters : collections.abc.Sequence[ScannedChapter]
        The chapters to scan, in the order their findings' lines should appear.

    Returns
    -------
    DetectionReport
        The per-rule findings, the total word count, and the overall pass flag.
    """
    total_words = sum(len(chapter.text.split()) for chapter in chapters)
    findings: list[RuleFinding] = []
    for rule in pack.rules:
        count, lines = scan_pattern(
            rule.compiled,
            chapters,
            line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line),
        )
        findings.append(
            _finding(rule, count=count, lines=lines, total_words=total_words)
        )
    return DetectionReport(
        pack=pack.pack,
        total_words=total_words,
        findings=tuple(findings),
        passed=all(finding.passed for finding in findings),
    )
