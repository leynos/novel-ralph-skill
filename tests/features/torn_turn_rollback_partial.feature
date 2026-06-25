Feature: a torn turn whose partial artefact landed is rolled back at the command boundary
  When a real §3.4 pending_turn bracket raises mid-turn over a coherent
  baseline — after it has written its own [pending_turn] intent record but
  before it clears it — declaring an unrecoverable next-chapter draft.md that
  never lands, it leaves an uncleared operation="write-draft" record on disk.
  Unlike the never-landed sibling (6.2.7), a partial draft residue did land:
  the §3.4 temp-file remnant of a mid-write whose Path.replace never promoted
  it, written inside an existing manifest chapter directory so the manifest-disk
  bijection still holds and the disposition stays ROLLBACK. novel-state check
  reports the torn turn (exit 4 with a rollback-pending-turn reconciliation),
  and novel-state reconcile rolls it back in a single pass (exit 0): the record
  is cleared, a rollback-pending-turn receipt is appended to log.md, and a
  follow-up check is coherent (exit 0). Every command is driven through the same
  entry path an operator uses; the partial residue is preserved byte-for-byte on
  disk and unreferenced by state, the author-owned drafts survive byte-for-byte,
  no working/ file is removed, and no unexpected file is fabricated — only
  state.toml and log.md change (design §3.4, §5.4 item 2: "Rolling back removes
  nothing — the partial artefacts stay on disk, unreferenced by state").

  Scenario: a torn write-draft turn that left a partial residue is reported by check and rolled back by reconcile
    Given a real pending_turn bracket raises mid-turn after a partial draft residue landed
    Then the torn turn leaves an uncleared write-draft pending_turn on disk
    And the partial residue is present on disk and unreferenced by state
    When check runs against that torn tree
    Then check exits 4 reporting a rollback-pending-turn reconciliation
    When reconcile rolls the torn turn back in a single pass
    Then reconcile clears the record and appends a rollback-pending-turn receipt
    And a follow-up check exits 0
    And the rollback preserves the partial residue byte-for-byte and fabricates no file
