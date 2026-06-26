"""Actionable-refusal unit tests for the ``recount`` mutator (roadmap 2.3.7).

When a recount would move the drafted ratio across a 30/50/80% knitting-gate
threshold while the matching gate flag still lags, the refusal must be
*actionable*: the exit-``3`` envelope's ``messages`` carry one advice line per
disagreeing gate, naming the crossed threshold, the recounted percentage, and
the direction-correct remedy (design §4.1, §5.4 recovery rule 1). This module
pins that behaviour in both directions, at the body level:

- the **upward** case (a recount crosses a threshold while the gate is false)
  prescribes ``novel-state set-gate --knitting-NN`` once the pending knitting
  pass is integrated, and forbids a hand-edit;
- the **downward** case (a recount leaves drafting below a threshold while the
  gate is recorded true) asks the operator to adjudicate and deliberately omits
  the ``set-gate --knitting-NN`` verb, because nothing was crossed upward —
  prescribing the repair there would corrupt the gate-integration record
  (resolves design-review B2 at the unit level);
- the **multi-gate fan-out** (a recount crosses two thresholds at once) emits one
  line per disagreeing gate.

Verification choice (cite ``python-verification``): the message is a fixed
template over an enumerable trigger (three thresholds by two directions, plus the
multi-gate fan-out), so parametrized example-based unit tests are the right
adversary — there is no new range-of-inputs invariant, only a finite message
matrix, so this is *not* a Hypothesis target.

The corpus spec/builder is used by direct value import (``working_corpus as
wc``), the carve-out the BDD step modules already use, so each test stays within
pylint's argument budget. This module is kept separate from
``tests/test_recount_unit.py`` so neither exceeds the 400-line module cap
(AGENTS.md "clear file boundaries"); the shared self-contained helpers below are
intentionally not imported across test modules (the developers-guide "Shared test
scaffolding" rule).
"""

from __future__ import annotations

import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._recount import recount
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import (
    GATE_RATIO_CONSISTENT,
    document_to_state,
    load_document,
    validate_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

_TARGET_WORDS = 80000
# The completed prefix for a coherent ``drafting``-phase tree (``premise`` … ``stc``).
_DRAFTING_PREFIX = wc.PHASE_ORDER[:8]


def _chapter(number: int, draft_words: int) -> wc.ChapterSpec:
    """Return a minimal coherent :class:`ChapterSpec` drafting ``draft_words``."""
    return wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=_TARGET_WORDS,
        draft_words=draft_words,
        has_done_flag=False,
        write_draft=True,
    )


def _spec(
    chapters: tuple[wc.ChapterSpec, ...],
    *,
    by_chapter_override: dict[str, int],
    current_words_override: int,
    gates: tuple[bool, bool, bool],
) -> wc.WorkingTreeSpec:
    """Return a coherent ``drafting``-phase spec with the given count overrides."""
    done_30, done_50, done_80 = gates
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=_DRAFTING_PREFIX,
        chapters=chapters,
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        by_chapter_override=by_chapter_override,
        current_words_override=current_words_override,
        done_30=done_30,
        done_50=done_50,
        done_80=done_80,
    )


def _refuses_leaving_file_intact(working: Path) -> StateInputError:
    """Run ``recount`` expecting a refusal; assert ``state.toml`` is intact.

    Returns the raised :class:`StateInputError` so the caller can inspect its
    ``messages`` (the refusal reason and the actionable remedy lines).
    """
    state_path = working / "state.toml"
    before = state_path.read_bytes()
    with pytest.raises(StateInputError) as excinfo:
        recount()
    assert state_path.read_bytes() == before, (
        "a refused recount must leave state.toml byte-for-byte intact"
    )
    return excinfo.value


def _message_for(error: StateInputError, needle: str) -> str:
    """Return the single ``messages`` line of ``error`` containing ``needle``.

    Asserts exactly one line matches so a test pins the precise advice line and
    does not accidentally match a sibling gate's line.
    """
    matches = [line for line in error.messages if needle in line]
    assert len(matches) == 1, (
        f"expected exactly one message containing {needle!r}, got {error.messages!r}"
    )
    return matches[0]


def _upward_gate_breach_tree(tmp_path: Path, *, draft_words: int) -> Path:
    """Build a coherent tree whose recount lifts the drafted ratio past a gate.

    A single chapter drafts ``draft_words`` on disk, but the hand-typed
    ``[word_counts]`` records a tiny ratio so the prior state passes the
    pure-state checker with all knitting gates ``false``. A recount then re-derives
    the larger on-disk total, crossing a knitting-gate threshold while the gate
    flag still lags — the roadmap's upward headline case.
    """
    spec = _spec(
        (_chapter(1, draft_words),),
        by_chapter_override={"01": 100},
        current_words_override=100,
        gates=(False, False, False),
    )
    working = wc.build_working_tree(spec, tmp_path)
    prior = document_to_state(load_document(working / "state.toml"))
    assert not validate_state(prior), (
        "the hand-typed prior state must pass validate_state before recount"
    )
    return working


def test_recount_upward_gate_breach_is_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recount crossing 30% with done_30 false emits the upward actionable line.

    A single chapter drafts 27200 words on disk (0.34 of the 80000 target) while
    the hand-typed counts record a tiny ratio, so the prior state is coherent with
    done_30 false. The recount lifts the ratio past 0.30, so done_30 false now
    breaches gate-ratio-consistent and the refusal carries the upward remedy
    naming the crossed threshold, the recounted percentage, and the set-gate verb.
    """
    working = _upward_gate_breach_tree(tmp_path, draft_words=27200)
    monkeypatch.chdir(working.parent)

    error = _refuses_leaving_file_intact(working)

    assert GATE_RATIO_CONSISTENT in str(error), (
        f"the refusal must name {GATE_RATIO_CONSISTENT!r}, got {error}"
    )
    upward = _message_for(error, "crossed the 30% knitting threshold")
    assert "drafts now at 34% of target" in upward, upward
    assert "gate done_30 is still false" in upward, upward
    assert "set-gate --knitting-30" in upward, upward
    assert "Do not hand-edit [gates]" in upward, upward


def test_recount_downward_gate_breach_does_not_prescribe_set_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recount leaving drafting below 80% with done_80 true adjudicates, not repairs.

    The hand-typed counts cross 0.80 (68800/80000 = 0.86) so the prior state is
    coherent with all three gates true, but the drafts recount to 44000 words
    (0.55 of target). That keeps done_30 and done_50 consistent (0.55 is above
    both 0.30 and 0.50) and isolates the **single** downward breach: done_80 is
    recorded true while the ratio sits below 0.80. The downward message must
    adjudicate and must *not* prescribe the upward repair verb for any gate
    (resolves design-review B2 at the unit level).
    """
    spec = _spec(
        (_chapter(1, 44000),),
        by_chapter_override={"01": 68800},
        current_words_override=68800,
        gates=(True, True, True),
    )
    working = wc.build_working_tree(spec, tmp_path)
    prior = document_to_state(load_document(working / "state.toml"))
    assert not validate_state(prior), (
        "the hand-typed prior state must pass validate_state before recount"
    )
    monkeypatch.chdir(working.parent)

    error = _refuses_leaving_file_intact(working)

    assert GATE_RATIO_CONSISTENT in str(error), (
        f"the refusal must name {GATE_RATIO_CONSISTENT!r}, got {error}"
    )
    downward = _message_for(error, "left drafting below the 80% knitting threshold")
    assert "drafts now at 55% of target" in downward, downward
    assert "gate done_80 is recorded true" in downward, downward
    assert "Adjudicate" in downward, downward
    # No gate's advice may prescribe the upward repair verb on the downward path
    # — done_80 is the only disagreeing gate, but assert globally so a future
    # leak from a sibling gate is also caught.
    assert all("set-gate" not in line for line in error.messages), (
        f"the downward remedy must not prescribe set-gate, got {error.messages!r}"
    )


def test_recount_multi_gate_breach_enumerates_each_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recount crossing 30% and 50% with both gates false emits both upward lines.

    Drafts of 44000 words (0.55 of target) cross both the 30% and 50% thresholds
    while done_30 and done_50 are both false, so the remedy enumerates each
    disagreeing gate on its **own** line: a distinct upward line for the 30% gate
    and another for the 50% gate, and no line for the uncrossed 80% gate (the
    multi-gate fan-out).
    """
    working = _upward_gate_breach_tree(tmp_path, draft_words=44000)
    monkeypatch.chdir(working.parent)

    error = _refuses_leaving_file_intact(working)

    # ``_message_for`` asserts exactly one line per needle, so the 30% and 50%
    # verbs each ride a distinct advice line (not one combined or duplicated line).
    line_30 = _message_for(error, "set-gate --knitting-30")
    line_50 = _message_for(error, "set-gate --knitting-50")
    assert line_30 != line_50, (
        f"each disagreeing gate must get its own line, got {error.messages!r}"
    )
    assert "crossed the 30% knitting threshold" in line_30, line_30
    assert "crossed the 50% knitting threshold" in line_50, line_50
    assert all("--knitting-80" not in line for line in error.messages), (
        f"the uncrossed 80% gate must emit no line, got {error.messages!r}"
    )
