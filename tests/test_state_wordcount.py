"""Unit and property tests for the word-count aggregation helper (roadmap 2.3.1).

These pin :func:`novel_ralph_skill.state.recount_words` — the one counting rule
the harness re-derives ``[word_counts]`` from — against the corpus oracle and its
fault boundary:

- an example-based unit test builds a tree with two non-empty drafts, one empty
  draft, and one chapter whose ``draft.md`` is *absent*, and pins the exact
  ``current``/``by_chapter`` table the helper returns (the per-chapter *mapping*
  is pinned here, not by the oracle — see the property test docstring);
- the fault boundary: an absent ``draft.md`` contributes ``0`` and does **not**
  raise, while an *undecodable* ``draft.md`` raises ``UnicodeDecodeError`` *out of*
  ``recount_words`` (the helper does not swallow it; the command layer translates
  it to exit ``3``, Work item 2);
- a Hypothesis property pins the helper's **total** equal to the oracle
  ``tests/working_corpus/_live_draft.py:live_draft_counts`` over generated
  manifests, so production and corpus cannot drift on the counting rule.

The counting rule itself (``len(draft_text.split())``) is fixed and shared with
the oracle (design §4.1; ExecPlan Constraint "Word-count algorithm is fixed").
"""

from __future__ import annotations

import typing as typ
import uuid

import pytest
import working_corpus as wc
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state import ChapterEntry, recount_words

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path


def _manifest(numbers: cabc.Iterable[int]) -> tuple[ChapterEntry, ...]:
    """Return a minimal manifest of :class:`ChapterEntry` for ``numbers``.

    Only ``number`` drives :func:`recount_words`; the other fields carry fixed,
    coherent placeholders so the manifest parses as a real chapter list.
    """
    return tuple(
        ChapterEntry(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
        )
        for number in numbers
    )


def _write_draft(working: Path, number: int, body: str) -> None:
    """Write ``body`` to ``working/manuscript/chapter-NN/draft.md``."""
    chapter_dir = working / "manuscript" / wc.chapter_dir_name(number)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "draft.md").write_text(body, encoding="utf-8")


def test_recount_words_sums_and_keys_by_manifest(tmp_path: Path) -> None:
    """Two filled drafts, one empty, and one absent yield the exact table.

    The empty and absent chapters both contribute ``0``; the total is the sum and
    the keys are the zero-padded two-digit strings keyed by the manifest (Decision
    Log D-KEY). An absent ``draft.md`` does **not** raise (Round-1 blocking 3).
    """
    working = tmp_path / "working"
    (working / "manuscript").mkdir(parents=True)
    _write_draft(working, 1, wc.draft_body(3))
    _write_draft(working, 2, wc.draft_body(5))
    _write_draft(working, 3, wc.draft_body(0))  # empty draft -> 0
    # Chapter 4 is in the manifest but has no ``draft.md`` directory at all.
    manifest = _manifest((1, 2, 3, 4))

    current, by_chapter = recount_words(working, manifest)

    assert current == 8, f"expected the summed total 8, got {current}"
    assert dict(by_chapter) == {"01": 3, "02": 5, "03": 0, "04": 0}, (
        f"empty and absent chapters should contribute 0, got {dict(by_chapter)}"
    )
    # The key order is ascending so a second run is byte-stable (Risk
    # "non-idempotent write").
    assert list(by_chapter) == ["01", "02", "03", "04"], (
        f"by_chapter keys should be ascending, got {list(by_chapter)}"
    )


def test_recount_words_orders_by_chapter_number(tmp_path: Path) -> None:
    """An out-of-order manifest still yields ascending ``by_chapter`` keys."""
    working = tmp_path / "working"
    (working / "manuscript").mkdir(parents=True)
    _write_draft(working, 2, wc.draft_body(5))
    _write_draft(working, 1, wc.draft_body(3))
    manifest = _manifest((2, 1))

    _current, by_chapter = recount_words(working, manifest)

    assert list(by_chapter) == ["01", "02"], (
        f"an out-of-order manifest should still key ascending, got {list(by_chapter)}"
    )


def test_recount_words_undecodable_draft_propagates(tmp_path: Path) -> None:
    """An undecodable ``draft.md`` raises ``UnicodeDecodeError`` out of the helper.

    The helper catches only ``FileNotFoundError``; a non-UTF-8 body must escape so
    the command layer can route it to exit ``3`` (Round-1 blocking 3).
    """
    working = tmp_path / "working"
    chapter_dir = working / "manuscript" / wc.chapter_dir_name(1)
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "draft.md").write_bytes(b"\xff\xfe")
    manifest = _manifest((1,))

    with pytest.raises(UnicodeDecodeError):
        recount_words(working, manifest)


def test_recount_words_empty_manifest_returns_zero(tmp_path: Path) -> None:
    """An empty manifest yields ``0`` and an empty ``by_chapter`` mapping."""
    working = tmp_path / "working"
    (working / "manuscript").mkdir(parents=True)

    current, by_chapter = recount_words(working, _manifest(()))

    assert current == 0, f"an empty manifest should total 0, got {current}"
    assert not by_chapter, (
        f"an empty manifest should yield no entries, got {by_chapter}"
    )


# A manifest of distinct chapter numbers paired with a per-chapter word count;
# building values directly (rather than drawing-then-filtering) keeps shrinking
# clean (the filtering trap).
@st.composite
def _manifest_with_counts(draw: st.DrawFn) -> dict[int, int]:
    """Draw a ``{chapter_number: word_count}`` mapping over distinct chapters."""
    numbers = draw(
        st.lists(
            st.integers(min_value=1, max_value=99),
            min_size=0,
            max_size=8,
            unique=True,
        )
    )
    return {number: draw(st.integers(min_value=0, max_value=40)) for number in numbers}


# The tree is rebuilt into a fresh subdirectory per example, so the
# function-scoped ``tmp_path`` not resetting between generated inputs is harmless
# — each example materialises its own drafts before counting. This mirrors the
# ``test_state_mutators_unit.py`` health-check suppression.
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(counts=_manifest_with_counts())
def test_recount_words_total_agrees_with_live_oracle(
    tmp_path: Path,
    counts: dict[int, int],
) -> None:
    """``recount_words``' total equals ``live_draft_counts`` over any manifest.

    ``live_draft_counts`` is a **total-only** oracle: it globs the *present*
    ``draft.md`` files and exposes no per-chapter map, whereas ``recount_words``
    iterates the manifest (an absent draft → ``0``). The two therefore agree on
    the **total** (an absent draft contributes ``0`` in both), which is what this
    property pins; the per-chapter ``by_chapter`` *mapping* is pinned by the
    example-based unit test above, not by the oracle (Round-2 advisory). The
    property also pins ``sum(by_chapter.values()) == current`` (design §5.2
    invariant 3 holds by construction).
    """
    # A globally unique subdirectory per example so drafts from one case cannot
    # leak into the next under the shared function-scoped ``tmp_path`` — the
    # oracle globs *every* present draft, so a name collision would mix cases.
    working = tmp_path / f"case-{uuid.uuid4().hex}"
    (working / "manuscript").mkdir(parents=True, exist_ok=True)
    for number, word_count in counts.items():
        _write_draft(working, number, wc.draft_body(word_count))
    manifest = _manifest(counts)

    current, by_chapter = recount_words(working, manifest)
    oracle_total, _oracle_chapters = wc.live_draft_counts(working)

    assert current == oracle_total, (
        f"helper total {current} diverged from oracle total {oracle_total}"
    )
    assert sum(by_chapter.values()) == current, (
        f"sum(by_chapter) {sum(by_chapter.values())} != current {current}"
    )
