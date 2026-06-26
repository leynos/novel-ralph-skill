Feature: every command presents the same envelope and exit-code contract
  The harness drives the five spaced commands unattended every turn and gates on
  their output, so each must present the same six-field envelope skeleton, the
  same ok-to-exit-code mapping, and the same error-channel shapes (design §3.1,
  §3.2; ADR-003 Table 2). This is the human-readable face of the cross-command
  identity proof; the heavy assertions live in the shared helpers the steps call,
  so a divergence in any command fails the same single suite.

  Scenario Outline: every command emits the shared envelope skeleton
    Given a coherent working tree for "<command>"
    When "<command>" is driven in machine mode
    Then the envelope carries the six contract fields in order with the contract types
    And working_dir is "working"
    And ok mirrors the exit code

    Examples:
      | command          |
      | novel state      |
      | novel done       |
      | novel wordcount  |
      | novel compile    |
      | novel desloppify |

  Scenario Outline: the state channel has the same shape across commands
    Given a cwd with no working tree for "<command>"
    When "<command>" is driven in machine mode
    Then the command exits 3 with the ok-false skeleton and an empty result
    And the envelope carries a non-blank message

    Examples:
      | command          |
      | novel state      |
      | novel done       |
      | novel wordcount  |
      | novel compile    |
      | novel desloppify |

  Scenario Outline: the usage channel has the same shape across commands
    Given a coherent working tree for "<command>"
    When "<command>" is driven with an unknown option in machine mode
    Then the command exits 2 with the ok-false skeleton and an empty result
    And the envelope carries a non-blank message

    Examples:
      | command          |
      | novel state      |
      | novel done       |
      | novel wordcount  |
      | novel compile    |
      | novel desloppify |
