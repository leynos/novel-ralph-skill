Feature: An out-of-order advance-phase is refused and leaves the prior state
  The advance-phase mutator marches phase.current to the next enum member and
  appends the just-left phase to phase.completed, but it refuses any transition
  that would leave the state incoherent. Because it takes no argument it can only
  ever move to the immediate successor, so the one out-of-order refusal it can
  make is against a prior state whose phase.completed is already not the in-order
  prefix. Such a refusal must exit 3 (state error), never the benign exit 1, and
  must leave state.toml byte-for-byte intact (the roadmap success criterion;
  design §3.2, §4.1, §9).

  Scenario: An out-of-order advance-phase is refused with exit 3 and leaves the prior state intact
    Given a working tree whose phase.completed is not the in-order prefix
    When advance-phase runs against that tree
    Then advance-phase exits 3
    And the prior state.toml is byte-for-byte unchanged
