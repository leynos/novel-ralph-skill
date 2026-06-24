"""Unit and property tests for the shared ``derive_reconciliation`` function.

These pin :func:`novel_ralph_skill.state.derive_reconciliation` (roadmap task
2.3.2) — the one pure function ``check`` renders and ``reconcile`` enacts:

- a table-driven unit test maps each corpus variant to its expected
  :class:`~novel_ralph_skill.state.ReconcileAction` (refuse-class → ``REFUSE``,
  the §5.4 under-count → ``RECOUNT``, the stale pending-turn marker →
  ``COMPLETE_PENDING_TURN``, an inline unrecoverable torn turn →
  ``ROLLBACK_PENDING_TURN``, pure-state-only and coherent trees → ``NONE``);
- a Hypothesis property pins the two invariants example-based tests cannot
  exhaust: the derivation is **total** (never raises over a generated space of
  pending-turn path declarations), and the precedence is exhaustive — **no**
  disk-evidence violation ever yields ``NONE`` (the round-2 blocking-point-4
  invariant), so ``check``'s exit-4 finding always carries an actionable action.

Per ``python-verification``, example-based tests cannot cover the open space of
declared-path sets a torn turn may carry (recoverable vs unrecoverable, present
vs absent), so the totality/precedence invariant is the property test's subject.
The corpus is taken by the sanctioned ``working_corpus as wc`` value import the
other corpus suites use.
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import pytest
import working_corpus as wc
from hypothesis import given
from hypothesis import strategies as st

from novel_ralph_skill.state import (
    ReconcileAction,
    check_disk_evidence,
    derive_reconciliation,
    load_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

# The expected action for each corpus variant that materialises (the
# ``phase-not-in-enum`` variant is parse-rejected, so it is excluded). Pure-state
# variants fire no disk-evidence invariant and so reconcile to ``NONE``.
_VARIANT_ACTIONS: dict[str, ReconcileAction] = {
    "completed-prefix-gap": ReconcileAction.NONE,
    "by-chapter-sum-mismatch": ReconcileAction.NONE,
    "consecutive-clean-over-target": ReconcileAction.NONE,
    "convergence-target-below-one": ReconcileAction.NONE,
    "consecutive-clean-over-chapters-drafted": ReconcileAction.NONE,
    "cursor-past-current-chapter": ReconcileAction.NONE,
    "scene-cursor-past-current-chapter": ReconcileAction.NONE,
    "beat-cursor-past-current-chapter": ReconcileAction.NONE,
    "gate-true-below-threshold": ReconcileAction.NONE,
    "manifest-extra-entry": ReconcileAction.REFUSE,
    "draft-without-manifest-entry": ReconcileAction.REFUSE,
    "done-flag-empty-draft": ReconcileAction.REFUSE,
    "done-flag-absent-draft": ReconcileAction.REFUSE,
    "compiled-not-concatenation-of-drafts": ReconcileAction.REFUSE,
    "scene-cursor-without-plan": ReconcileAction.REFUSE,
    "beat-cursor-without-plan": ReconcileAction.REFUSE,
    "uncleared-pending-turn": ReconcileAction.COMPLETE_PENDING_TURN,
    "done-flag-real-draft-undercount": ReconcileAction.RECOUNT,
    "done-claim-stale-word-counts": ReconcileAction.RECOUNT,
    "pending-turn-complete-recomputable": ReconcileAction.COMPLETE_PENDING_TURN,
    "pending-turn-rollback-unrecoverable": ReconcileAction.ROLLBACK_PENDING_TURN,
}


def _derive_for_variant(name: str, tmp_path: Path) -> ReconcileAction:
    """Build the named corpus variant and return its derived action."""
    spec, _expected = wc.INCOHERENT_VARIANTS[name]
    working = wc.build_working_tree(spec, tmp_path / name)
    state = load_state(working / "state.toml")
    return derive_reconciliation(state, working).action


@pytest.mark.parametrize(("name", "expected"), list(_VARIANT_ACTIONS.items()))
def test_variant_maps_to_expected_action(
    name: str,
    expected: ReconcileAction,
    tmp_path: Path,
) -> None:
    """Each materialising corpus variant derives its expected reconcile action."""
    (tmp_path / name).mkdir()
    assert _derive_for_variant(name, tmp_path) == expected, name


def test_coherent_baseline_reconciles_to_none(tmp_path: Path) -> None:
    """A coherent baseline tree reconciles to ``NONE`` (nothing to do)."""
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action == ReconcileAction.NONE
    assert not reconciliation.discrepancies


def test_unrecoverable_torn_turn_rolls_back(tmp_path: Path) -> None:
    """A torn turn whose missing declared path is a ``draft.md`` rolls back.

    The declared ``chapter-99/draft.md`` never materialises (the baseline has three
    chapters), so it is a *missing unrecoverable* artefact: the derivation chooses
    ``ROLLBACK_PENDING_TURN`` and carries the missing path (D-COMPLETE).
    """
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        pending_turn={
            "operation": "write-draft",
            "paths": ["working/manuscript/chapter-99/draft.md"],
        },
    )
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action == ReconcileAction.ROLLBACK_PENDING_TURN
    assert reconciliation.operation == "write-draft"
    assert reconciliation.missing_paths == ("working/manuscript/chapter-99/draft.md",)


def test_recount_carries_disk_derived_counts(tmp_path: Path) -> None:
    """A ``RECOUNT`` reconciliation carries the disk-derived word-count payload."""
    spec, _expected = wc.INCOHERENT_VARIANTS["done-flag-real-draft-undercount"]
    working = wc.build_working_tree(spec, tmp_path)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    assert reconciliation.action == ReconcileAction.RECOUNT
    assert reconciliation.recounted_current == 68800
    assert reconciliation.recounted_by_chapter == {
        "01": 24000,
        "02": 24000,
        "03": 20800,
    }


# A path-segment alphabet for the property strategy: directory and file names a
# torn turn might declare, mixing recomputable (``state.toml``/``log.md``) and
# unrecoverable (``draft.md``/``done.flag``) basenames with present and absent
# chapter directories, so the generated declared-path sets exercise every
# COMPLETE/ROLLBACK branch.
_DECLARED_BASENAMES = st.sampled_from([
    "state.toml",
    "log.md",
    "manuscript/chapter-01/draft.md",
    "manuscript/chapter-99/draft.md",
    "manuscript/chapter-02/done.flag",
    "plan/chapter-outline.md",
])


@given(
    declared=st.lists(
        _DECLARED_BASENAMES.map(lambda rest: f"working/{rest}"),
        min_size=1,
        max_size=4,
        unique=True,
    )
)
def test_derivation_is_total_and_never_yields_none_on_a_violation(
    declared: list[str],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """``derive_reconciliation`` is total and never reconciles a violation to ``NONE``.

    Over a generated space of torn-turn declared-path sets on an otherwise coherent
    baseline, the derivation (a) returns a ``Reconciliation`` without raising
    (totality) and (b) yields ``NONE`` only when *no* disk-evidence violation fired
    — the round-2 blocking-point-4 invariant that ``check``'s exit-4 finding always
    carries an actionable action.
    """
    dest = tmp_path_factory.mktemp("torn")
    spec = dc.replace(
        wc.COHERENT_BASELINE,
        pending_turn={"operation": "write-draft", "paths": declared},
    )
    working = wc.build_working_tree(spec, dest)
    state = load_state(working / "state.toml")
    reconciliation = derive_reconciliation(state, working)
    fired = check_disk_evidence(state, working)
    if fired:
        assert reconciliation.action != ReconcileAction.NONE
    else:
        assert reconciliation.action == ReconcileAction.NONE
