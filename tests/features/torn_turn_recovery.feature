Feature: a torn reconcile turn is recovered through the real command boundary
  When a real novel-state reconcile command crashes mid-write — after it has
  written its own [pending_turn] intent record but before it clears it — it
  leaves an uncleared operation="reconcile" record on disk: the on-disk
  signature of a torn turn. novel-state check then reports the torn turn (exit 4
  with a complete-pending-turn reconciliation), and novel-state reconcile,
  re-run under the harness re-entry model, recovers it (each run exits 0) until a
  follow-up check is coherent (exit 0). Every command is driven through the same
  entry path an operator uses, the author-owned drafts survive byte-for-byte, and
  no working/ file is removed (design §3.4, §5.4).

  Scenario: a crashed reconcile leaves a torn turn that check reports and reconcile recovers
    Given a real reconcile command crashes mid-write over a stale tree
    Then the crashed reconcile leaves an uncleared reconcile pending_turn on disk
    When check runs against that torn tree
    Then check exits 4 reporting a complete-pending-turn reconciliation
    When reconcile re-runs under bounded harness re-entry
    Then reconcile recovers the torn turn and the pending_turn is cleared
    And a follow-up check exits 0
    And the recovery removes no working file and the drafts are unchanged
