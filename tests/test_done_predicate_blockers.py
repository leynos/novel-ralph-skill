"""Unit and property tests for the ``no_unresolved_blockers`` BLOCKER grammar.

These pin the heading-based BLOCKER recogniser (roadmap 3.1.5): the spiteful
critic's strict output format is a ``## BLOCKER`` section with ``### Bn — <label>``
findings, a finding is resolved by a trailing space-then-``[resolved]`` token, the
``No BLOCKER. No MAJOR.`` sentinel is clean by construction, and the section
scoping, positional marker, trailing-text, and case rules are each asserted. The
positional invariant is a Hypothesis property over generated finding headings,
asserted directly on the extracted pure helper
:func:`~novel_ralph_skill.state._blocker_notes._line_is_unresolved_blocker_finding`
so no filesystem round-trips per example (audit-3.1.4 Finding 4).

These cases live beside ``test_done_predicate.py`` rather than inside it so that
module stays under the AGENTS.md 400-line cap once the eight BLOCKER cases plus
the rewritten property land. The all-hold tree helper is re-spelled here (it is a
two-line corpus build) to keep the module self-contained.
"""

from __future__ import annotations

import typing as typ

import pytest
import working_corpus as wc
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state import load_state
from novel_ralph_skill.state._blocker_notes import (
    _line_is_unresolved_blocker_finding,
)
from novel_ralph_skill.state.done_predicate import no_unresolved_blockers

if typ.TYPE_CHECKING:
    from pathlib import Path

    from novel_ralph_skill.state.schema import State

# A critic-personas-shaped ``## BLOCKER`` section carrying one live ``### B1``
# finding (quoted passage, ``What's wrong:``, ``Suggested action:`` lines), the
# real producer format (``critic-personas.md``; roadmap 3.1.5). The label is a
# template field so a test can flip a single finding heading to resolved.
_LIVE_BLOCKER_NOTE = (
    "## BLOCKER\n"
    "\n"
    "### B1 — {label}\n"
    "> the climax contradicts chapter 2\n"
    "\n"
    "What's wrong: the protagonist already knows the secret.\n"
    "Suggested action: cut the reveal or rewrite chapter 2.\n"
)


def _blocker_note(label: str = "the climax contradicts chapter 2") -> str:
    """Return a critic-personas-shaped ``## BLOCKER`` body with one finding."""
    return _LIVE_BLOCKER_NOTE.format(label=label)


def _write_reviews(working: Path, percentages: tuple[int, ...]) -> None:
    """Write ``reviews/knitting-NN.md`` for each named percentage under ``working``."""
    reviews = working / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    for percentage in percentages:
        (reviews / f"knitting-{percentage}.md").write_text(
            f"# Knitting {percentage}\n", encoding="utf-8"
        )


def _all_hold_tree(tmp_path: Path) -> tuple[State, Path]:
    """Build an all-six-clauses-hold tree and return its parsed state and path."""
    working = wc.build_working_tree(wc.PHASE_STATES["done"], tmp_path)
    _write_reviews(working, (30, 50, 80))
    return load_state(working / "state.toml"), working


def test_no_unresolved_blockers_clean_and_blocking(tmp_path: Path) -> None:
    """The clause holds when clean; a live ``### B1`` finding fails it.

    The blocking body is the spiteful critic's strict output format — a
    ``## BLOCKER`` section with a live ``### B1 — …`` finding (``critic-personas.md``;
    roadmap 3.1.5). This is the headline exit-code flip: genuine critic output is
    now caught, where the old ``startswith("BLOCKER")`` grammar matched zero lines
    (audit-3.1.4 Finding 1).
    """
    state, working = _all_hold_tree(tmp_path)
    assert no_unresolved_blockers(state, working) is True
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text(_blocker_note(), encoding="utf-8")
    assert no_unresolved_blockers(state, working) is False


def test_resolved_blocker_is_clean(tmp_path: Path) -> None:
    """A ``### B1`` finding bearing a trailing ``[resolved]`` token holds."""
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text(
        _blocker_note("the climax contradicts chapter 2 [resolved]"),
        encoding="utf-8",
    )
    assert no_unresolved_blockers(state, working) is True


def test_convergence_sentinel_is_clean(tmp_path: Path) -> None:
    """The ``No BLOCKER. No MAJOR.`` sentinel writes no section and is clean.

    D-BLOCKER-SENTINEL: the critic writes the sentinel *instead of* a
    ``## BLOCKER`` section, so the recogniser finds no findings and the clause
    holds by construction (``critic-personas.md``).
    """
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text("No BLOCKER. No MAJOR.\n", encoding="utf-8")
    assert no_unresolved_blockers(state, working) is True


def test_finding_outside_blocker_section_is_clean(tmp_path: Path) -> None:
    """A ``### B1`` line under ``## MAJOR`` (not ``## BLOCKER``) does not fail.

    The section scoping is load-bearing: only findings *inside* the ``## BLOCKER``
    section count, so a ``### B1`` heading under a different ``##``-level section
    is clean (roadmap 3.1.5).
    """
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text(
        "## MAJOR\n\n### B1 — a label that happens to start with B\n",
        encoding="utf-8",
    )
    assert no_unresolved_blockers(state, working) is True


def test_incidental_resolved_mention_stays_unresolved(tmp_path: Path) -> None:
    """A live finding whose label quotes ``[resolved]`` mid-line stays unresolved.

    The resolution marker is positional (D-BLOCKER-POSITIONAL): a ``[resolved]``
    token that is not the trailing marker — here, prose in the heading label that
    incidentally quotes it — does not clear the finding. The 3.1.4 false-clean
    edge, re-expressed on the ``### B1`` finding heading.
    """
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text(
        _blocker_note("the ending still depends on the [resolved] issue"),
        encoding="utf-8",
    )
    assert no_unresolved_blockers(state, working) is False


def test_trailing_text_after_token_stays_unresolved(tmp_path: Path) -> None:
    """A finding with text after ``[resolved]`` stays unresolved by design.

    D-BLOCKER-TRAILING (audit-3.1.4 Finding 2): the convention forbids trailing
    text after the marker, so ``### B1 — label [resolved] (see log)`` is treated
    as unresolved. The recogniser needs no tolerance because the producer owns
    the shape.
    """
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_text(
        _blocker_note("a label [resolved] (see log 42)"),
        encoding="utf-8",
    )
    assert no_unresolved_blockers(state, working) is False


def test_case_variant_token_stays_unresolved(tmp_path: Path) -> None:
    """Case and spelling variants of the token stay unresolved today.

    D-BLOCKER-CASE (audit-3.1.4 Finding 3): the recogniser is case-sensitive on
    the ``[resolved]`` token, so ``[RESOLVED]`` and ``(resolved)`` do not clear
    the finding. This pins the documented out-of-scope behaviour so a future
    ``.casefold()`` "fix" cannot silently flip it.
    """
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    for label in ("a label [RESOLVED]", "a label (resolved)"):
        (first / "critic-notes.md").write_text(_blocker_note(label), encoding="utf-8")
        assert no_unresolved_blockers(state, working) is False


@settings(max_examples=200, deadline=None)
@given(
    label=st.text(
        alphabet=st.characters(
            min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="[]\n"
        ),
        max_size=40,
    ),
    suffix=st.text(
        alphabet=st.characters(
            min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="[]\n"
        ),
        max_size=40,
    ),
)
def test_blocker_resolution_is_positional(label: str, suffix: str) -> None:
    """The token's *trailing position* decides resolution; its presence does not.

    Hypothesis is the right adversary (``python-verification``): a positional
    invariant over generated ``### B1`` finding headings (D-BLOCKER-POSITIONAL),
    asserted directly on the extracted pure helper
    :func:`_line_is_unresolved_blocker_finding` so no filesystem round-trips per
    example (audit-3.1.4 Finding 4). The alphabet excludes ``[``, ``]`` and
    newlines so neither field can introduce a spurious ``[resolved]`` token; the
    mid-line case ends in a fixed non-space sentinel ``X`` so, even when
    ``suffix`` is empty or whitespace, the token is provably not the trailing
    marker (round-1 advisory A1).
    """
    prefix = "### B1 — "
    # Token strictly mid-line, fixed non-space sentinel after it: unresolved.
    mid = f"{prefix}{label} [resolved] {suffix}X"
    assert _line_is_unresolved_blocker_finding(mid) is True
    # Token trailing with the required separating space: resolved.
    resolved = f"{prefix}{label} [resolved]"
    assert _line_is_unresolved_blocker_finding(resolved) is False


def test_undecodable_critic_notes_propagates(tmp_path: Path) -> None:
    """An undecodable ``critic-notes.md`` propagates rather than reading as clean."""
    state, working = _all_hold_tree(tmp_path)
    first = min((working / "manuscript").glob("chapter-*"))
    (first / "critic-notes.md").write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(UnicodeDecodeError):
        no_unresolved_blockers(state, working)
