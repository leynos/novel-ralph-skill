Feature: a faulted draft yields one actionable exit-3 message for every boundary
  When a chapter draft.md (or compiled.md) under a present working/ tree is corrupt
  or unreadable, every draft-read command must surface an actionable exit-3 message
  that names the working/ tree it read and how to recover — not a raw Errno, a {exc}
  repr, or a path-as-noise. The message must route through one shared formatter so
  the six draft-read boundaries cannot drift apart (roadmap §6.3.5; design §3.2).

  The mutator view-derivation boundary is not a draft-read fault: a
  parseable-but-structurally-incomplete state.toml reuses the state-document
  present-but-corrupt remedy (naming the state.toml path), kept distinct from the
  draft-read prose (ExecPlan Decision D7).

  Scenario: every draft-read command emits the shared working/-naming repair message
    Given a coherent working/ tree whose first chapter draft is corrupt
    When each draft-read command runs against the corrupt tree
    Then each draft-read command exits 3
    And each draft-read message names the working/ tree and an inspect/repair remedy
    And no draft-read message leaks raw noise or an init suggestion

  Scenario: a structurally incomplete state.toml reuses the state-document remedy
    Given a working/ tree whose state.toml is structurally incomplete
    When a mutator runs against the structurally incomplete state
    Then the mutator exits 3
    And the mutator message names the state.toml path and an inspect/repair remedy
    And the mutator message leaks no raw structurally-incomplete text
