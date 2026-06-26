Feature: a missing working/ yields one actionable exit-3 message for every command
  When any novel command runs from a directory with no working/ tree, the exit-3
  envelope must carry an actionable message that names where the command looked and
  how to recover — not a raw Errno or a path-as-noise. The message must be identical
  across a mutator, a checker, and a reader, because both load boundaries route
  through one shared helper (roadmap §6.3.1; design §3.2).

  Scenario: every command class emits the same cwd-naming, init-suggesting message
    Given a directory with no novel working/ tree
    When the mutator, the checker, and the reader each run from that directory
    Then each command exits 3
    And each message names the current directory and the 'novel state init' remedy
    And no message contains a raw Errno or a traceback
    And the message is identical across the mutator, the checker, and the reader
