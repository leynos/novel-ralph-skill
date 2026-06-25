Feature: set-chapters populates the chapter manifest from the agent's plan
  The set-chapters mutator is the one sanctioned path a planned chapter takes into
  [chapters]: it writes the manifest, creates the on-disk chapter-NN/ directories,
  and appends a log.md receipt under a [pending_turn] bracket, so novel-state check
  finds the manifest and disk in bijection. An incoherent or duplicate plan is
  refused with exit 3 and writes nothing; re-running against a populated manifest is
  refused (set-chapters is a one-shot populate). A turn torn mid-write is completed
  by reconcile, never by a re-run or a hand edit (design 4.1, 5.1, 5.2, 5.4; ADR 008).

  Scenario: a coherent plan reaches the manifest and check then exits 0
    Given an initialised tree with an empty chapter manifest
    When set-chapters runs with a coherent two-chapter plan
    Then set-chapters exits 0
    And state.toml records the two planned chapters in ascending order
    And the chapter directories chapter-01 and chapter-02 exist
    And a follow-up check exits 0

  Scenario: a non-contiguous plan is refused and writes nothing
    Given an initialised tree with an empty chapter manifest
    When set-chapters runs with a non-contiguous plan
    Then set-chapters exits 3
    And state.toml is byte-for-byte unchanged

  Scenario: a duplicate-number plan is refused
    Given an initialised tree with an empty chapter manifest
    When set-chapters runs with a duplicate-number plan
    Then set-chapters exits 3
    And state.toml is byte-for-byte unchanged

  Scenario: re-running against a populated manifest is refused
    Given a tree whose chapter manifest is already populated
    When set-chapters runs with a coherent two-chapter plan
    Then set-chapters exits 3
    And state.toml is byte-for-byte unchanged

  Scenario: a partial-directory torn turn is recovered by reconcile
    Given a torn set-chapters turn with three planned chapters and only chapter-01 on disk
    When check runs against the torn tree
    Then check exits 4
    When reconcile runs against the torn tree
    Then reconcile exits 0
    And the chapter directories chapter-02 and chapter-03 exist
    And a follow-up check exits 0
