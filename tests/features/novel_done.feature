Feature: novel-done evaluates the six done clauses against disk
  The novel-done checker is the harness's terminator: it reads state.toml and the
  working/ tree, evaluates each of the six §4.2 done clauses, and exits 0 only
  when every clause holds. While any clause is false it exits 1, the benign
  "not yet done" the harness loops on. It writes nothing on any path (design
  §4.2, §3.2; ADR-001).

  Scenario: a tree where every clause holds is declared done
    Given a working tree where all six done clauses hold
    When novel-done runs against that tree
    Then novel-done exits 0
    And every clause in the result is true

  Scenario Outline: a single failed clause keeps the predicate not done
    Given a working tree that fails only the "<clause>" clause
    When novel-done runs against that tree
    Then novel-done exits 1
    And the result reports "<clause>" false

    Examples:
      | clause                  |
      | phase_is_done           |
      | final_pass_complete     |
      | all_chapters_flagged    |
      | knitting_review_missing |
      | knitting_gate_false     |
      | compile_consistent      |
      | no_unresolved_blockers  |
