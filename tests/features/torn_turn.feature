Feature: Torn multi-file turn leaves a pending_turn record
  The pending_turn bracket makes a multi-file mutation recoverable. A turn
  that dies after the intent record is written but before the bracket exits
  cleanly must leave a populated [pending_turn] naming the operation and the
  paths it intended to write, with the prior tables otherwise intact, so the
  next turn's reconcile can read it (design §3.4).

  Scenario: A bracket that raises mid-turn leaves the intent record populated
    Given a settled state.toml with no pending_turn
    When a pending_turn bracket for "recount" raises before clean exit
    Then state.toml carries a pending_turn for "recount" naming the declared paths
    And the prior word_counts table is intact
