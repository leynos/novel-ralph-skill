Feature: recount re-derives the word counts from the chapter drafts
  The recount mutator re-derives [word_counts].current and [word_counts].by_chapter
  by a pure aggregation over the on-disk chapter drafts, so a human never types a
  word count by hand. It writes only state.toml (no [pending_turn] bracket), the
  per-chapter values sum to the total, and a second run over unchanged drafts
  yields a byte-for-byte identical state.toml (idempotence). These are the roadmap
  success criteria (design §4.1, §5.2 invariant 3, §9).

  Scenario: recount corrects hand-wrong counts and is idempotent on a second run
    Given a working tree with two drafted chapters whose hand-typed counts are wrong
    When recount runs against that tree
    Then recount exits 0
    And state.toml records the summed counts derived from the drafts
    And a second recount leaves state.toml byte-for-byte unchanged

  Scenario: recount refuses with an actionable upward message when it crosses a gate
    Given a working tree whose drafts have grown past the 30% knitting threshold while done_30 is still false
    When recount runs against that tree
    Then recount exits 3
    And the recount message contains "crossed the 30% knitting threshold"
    And the recount message contains "set-gate --knitting-30"
    And the recount message contains "Do not hand-edit [gates]"
    And state.toml is left byte-for-byte unchanged

  Scenario: recount refuses with a non-prescriptive downward message when the gate no longer matches the drafts
    Given a working tree whose recorded done_80 gate no longer matches its shrunken drafts
    When recount runs against that tree
    Then recount exits 3
    And the recount message contains "left drafting below the 80% knitting threshold"
    And the recount message contains "gate done_80 is recorded true"
    And the recount message contains "Adjudicate"
    And the recount message does not contain "set-gate --knitting-80"
    And state.toml is left byte-for-byte unchanged
