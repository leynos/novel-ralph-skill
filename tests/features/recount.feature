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
