Feature: a torn turn whose declared artefact did not land is rolled back at the command boundary
  When a real §3.4 pending_turn bracket raises mid-turn over a coherent
  baseline — after it has written its own [pending_turn] intent record but
  before it clears it — declaring an unrecoverable draft.md that never lands, it
  leaves an uncleared operation="write-draft" record on disk: the on-disk
  signature of a torn turn whose missing artefact is unrecoverable. novel-state
  check then reports the torn turn (exit 4 with a rollback-pending-turn
  reconciliation), and novel-state reconcile rolls it back in a single pass
  (exit 0): the record is cleared, a rollback-pending-turn receipt is appended to
  log.md, and a follow-up check is coherent (exit 0). Every command is driven
  through the same entry path an operator uses, the author-owned drafts survive
  byte-for-byte, and no working/ file is removed (design §3.4, §5.4 item 2).

  Scenario: a torn write-draft turn that left no draft is reported by check and rolled back by reconcile
    Given a real pending_turn bracket raises mid-turn declaring an unrecoverable draft
    Then the torn turn leaves an uncleared write-draft pending_turn on disk
    When check runs against that torn tree
    Then check exits 4 reporting a rollback-pending-turn reconciliation
    When reconcile rolls the torn turn back in a single pass
    Then reconcile clears the record and appends a rollback-pending-turn receipt
    And a follow-up check exits 0
    And the rollback removes no working file and the drafts are unchanged
