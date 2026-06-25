Feature: a torn turn whose declared artefact did not land is rolled back at the command boundary
  When a real §3.4 pending_turn bracket raises mid-turn over a coherent
  baseline — after it has written its own [pending_turn] intent record but
  before it clears it — declaring an unrecoverable artefact (a draft.md body or a
  done.flag) that never lands, it leaves an uncleared pending_turn record on disk:
  the on-disk signature of a torn turn whose missing artefact is unrecoverable.
  novel-state check then reports the torn turn (exit 4 with a rollback-pending-turn
  reconciliation), and novel-state reconcile rolls it back in a single pass
  (exit 0): the record is cleared, a rollback-pending-turn receipt is appended to
  log.md, and a follow-up check is coherent (exit 0). Every command is driven
  through the same entry path an operator uses, the author-owned drafts survive
  byte-for-byte, and no working/ file is removed (design §3.4, §5.4 item 2).

  Both unrecoverable triggers — a missing draft.md body and a missing done.flag —
  carry the basename outside {state.toml, log.md} that the classifier keys
  ROLLBACK on, so both run end-to-end through the command boundary as example rows.

  Scenario Outline: a torn <trigger> turn that left no artefact is reported by check and rolled back by reconcile
    Given a real pending_turn bracket raises mid-turn declaring an unrecoverable "<declared_path>" via "<operation>"
    Then the torn turn leaves an uncleared "<operation>" pending_turn declaring "<declared_path>"
    When check runs against that torn tree
    Then check exits 4 reporting a rollback-pending-turn reconciliation
    When reconcile rolls the torn turn back in a single pass
    Then reconcile clears the record and appends a rollback-pending-turn receipt
    And a follow-up check exits 0
    And the rollback removes no working file and the drafts are unchanged

    Examples:
      | trigger    | declared_path                              | operation   |
      | draft.md   | working/manuscript/chapter-99/draft.md     | write-draft |
      | done.flag  | working/manuscript/chapter-99/done.flag    | mark-done   |
