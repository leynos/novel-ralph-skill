Feature: set-gate repairs a lagging knitting gate, refuses below threshold, and faults on no flag
  The set-gate mutator flips the named knitting gate true under the section 5.2
  gate-ratio-consistent invariant: it repairs a lagging gate whose drafted ratio
  has crossed the threshold (exit 0), refuses a gate the ratio has not yet earned
  (exit 3, state.toml byte-for-byte intact), and faults with a usage envelope when
  no gate flag is supplied (exit 2, no traceback) rather than silently doing
  nothing. These three arms are the headline mutator's repair, refusal, and usage
  channels (the roadmap 2.2.4 success criterion; design sections 4.1, 5.2, 9).

  Scenario: set-gate repairs a lagging knitting gate and leaves the tree coherent
    Given a drafting tree whose drafted ratio has crossed 0.30 with done_30 false
    When set-gate --knitting-30 runs against that tree
    Then set-gate exits 0
    And gates.knitting.done_30 is true
    And novel-state check exits 0

  Scenario: set-gate refuses a gate the drafted ratio has not earned
    Given a drafting tree whose drafted ratio is below every threshold with done_30 false
    When set-gate --knitting-30 runs against that tree
    Then set-gate exits 3
    And the prior state.toml is byte-for-byte unchanged

  Scenario: set-gate with no gate flag faults with a usage envelope
    Given a drafting tree whose drafted ratio has crossed 0.30 with done_30 false
    When set-gate runs against that tree with no gate flag
    Then set-gate exits 2
    And the prior state.toml is byte-for-byte unchanged
