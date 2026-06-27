"""Unit tests pinning the ``reconciliation_payload`` projection.

These pin :func:`novel_ralph_skill.state.reconciliation_payload` (roadmap task
7.1.3) — the single source of the ``{action, discrepancies, detail}`` payload
dict the four reconciliation arms (``check``'s read shape, ``reconcile``'s
``_write_outcome`` / ``_refuse_outcome`` / ``NONE`` write shapes) route through.

The projection is a fixed-shape, total function over the closed
:class:`~novel_ralph_skill.state.Reconciliation` dataclass, so example-based
tests over the two structural cases (recount-bearing and recount-absent)
suffice; no Hypothesis/CrossHair/mutmut adversary is required
(``python-verification``: there is no generated input space).

The recount-absent ``list(payload.items())`` order assertion is the **named
primary order pin** for the write-side ``REFUSE``/``NONE`` ``result`` envelope:
it is the only check that fails on a write-side key reorder, because the
``test_reconcile_refuse`` snapshot is ``sort_keys=True`` (it pins the field set,
not the order) and the ``test_novel_state_check_disk`` snapshot pins insertion
order only for the READ (``check``) path. Do not weaken or remove it.
"""

from __future__ import annotations

from novel_ralph_skill.state import (
    ReconcileAction,
    Reconciliation,
    reconciliation_payload,
)


def test_payload_base_shape_and_key_order() -> None:
    """A recount-absent reconciliation projects to the base three keys, in order."""
    reconciliation = Reconciliation(
        action=ReconcileAction.REFUSE,
        discrepancies=("log-present", "word-counts-match-drafts"),
        detail="disk evidence refuses repair",
    )

    payload = reconciliation_payload(reconciliation)

    # Compare ``items()`` (ordered), not ``==`` (which ignores order), so a
    # reordered projection is red here. This is the primary write-side order pin.
    assert list(payload.items()) == [
        ("action", "refuse"),
        ("discrepancies", ["log-present", "word-counts-match-drafts"]),
        ("detail", "disk evidence refuses repair"),
    ], "base payload shape or key order drifted from action/discrepancies/detail"


def test_payload_omits_recount_pair_when_absent() -> None:
    """No ``current``/``by_chapter`` keys when ``recounted_by_chapter`` is ``None``."""
    reconciliation = Reconciliation(
        action=ReconcileAction.NONE,
        discrepancies=(),
        detail="state is coherent against disk; nothing to reconcile",
    )

    payload = reconciliation_payload(reconciliation)

    assert set(payload) == {"action", "discrepancies", "detail"}, (
        "recount-absent payload must carry only the base three keys"
    )
    assert "current" not in payload, "recount-absent payload leaked a current key"
    assert "by_chapter" not in payload, "recount-absent payload leaked a by_chapter key"


def test_payload_includes_recount_pair_after_detail() -> None:
    """A RECOUNT projects the recount pair, in order, after ``detail``."""
    reconciliation = Reconciliation(
        action=ReconcileAction.RECOUNT,
        discrepancies=("word-counts-match-drafts",),
        detail="recounting from disk",
        recounted_current=1234,
        recounted_by_chapter={"chapter-01": 600, "chapter-02": 634},
    )

    payload = reconciliation_payload(reconciliation)

    assert list(payload.items()) == [
        ("action", "recount"),
        ("discrepancies", ["word-counts-match-drafts"]),
        ("detail", "recounting from disk"),
        ("current", 1234),
        ("by_chapter", {"chapter-01": 600, "chapter-02": 634}),
    ], "recount payload shape or key order (pair after detail) drifted"


def test_payload_copies_discrepancies_and_by_chapter() -> None:
    """``discrepancies`` and ``by_chapter`` are independent copies of the dataclass."""
    by_chapter = {"chapter-01": 600}
    reconciliation = Reconciliation(
        action=ReconcileAction.RECOUNT,
        discrepancies=("word-counts-match-drafts",),
        detail="recounting from disk",
        recounted_current=600,
        recounted_by_chapter=by_chapter,
    )

    payload = reconciliation_payload(reconciliation)

    # The projection uses ``list(...)`` / ``dict(...)``, so the payload values
    # are independent copies, not aliases of the frozen dataclass's tuple and
    # the caller's mapping. ``list`` is never the source ``tuple``; the
    # ``by_chapter`` dict must be a distinct object from the input mapping.
    assert payload["discrepancies"] == ["word-counts-match-drafts"], (
        "discrepancies value drifted from the source tuple contents"
    )
    assert isinstance(payload["discrepancies"], list), (
        "discrepancies must be projected as a fresh list, not the source tuple"
    )
    assert payload["by_chapter"] == {"chapter-01": 600}, (
        "by_chapter value drifted from the source mapping contents"
    )
    assert payload["by_chapter"] is not by_chapter, (
        "by_chapter must be an independent copy, not the source mapping"
    )
