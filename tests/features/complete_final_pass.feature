Feature: complete-final-pass marks the final pass complete and stays coherent
  The complete-final-pass mutator is the named, argument-free idiom the agent
  runs at the end of the final-pass phase to flip gates.final.final_pass_complete
  true. The final gate carries no section 5.2 binding, so the flip is accepted on
  any coherent tree, must exit 0, and must leave the state coherent so a follow-up
  novel-state check exits 0 (the roadmap 2.2.4 success criterion; design section
  4.1).

  Scenario: complete-final-pass flips the final gate and leaves the tree coherent
    Given a coherent final-pass tree with the final gate off
    When complete-final-pass runs against that tree
    Then complete-final-pass exits 0
    And gates.final.final_pass_complete is true
    And novel-state check exits 0
