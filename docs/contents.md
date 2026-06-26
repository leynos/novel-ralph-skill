# Documentation contents

[Documentation contents](contents.md) is the index for novel-ralph-skill's
documentation set.

## Problem, design, and planning

- [Terms of reference](terms-of-reference.md) settles the problem space
  for the novel-ralph skill rebuild: why the deterministic spine was never
  built, who the harnessed agent is, and the scope boundaries.
- [novel-ralph harness design](novel-ralph-harness-design.md) is the
  technical design for the deterministic spine and the clean-context sub-agent
  architecture.
- [Development roadmap](roadmap.md) sequences the rebuild into phases,
  steps, and tasks.
- [Execution plans](execplans/) hold the self-contained per-task plans
  (`roadmap-<step>-<task>.md`) and their review rounds that drive each
  roadmap task to completion.
- [Post-merge audits](issues/) hold the per-task audit notes
  (`audit-<step>.<task>.md`) recording the codebase review after each task
  merged to `main`.

## Architecture decision records

- [ADR 001: deterministic and judgemental boundary](adr-001-deterministic-judgemental-boundary.md)
  fixes the controlling decision: scripts detect and report; the model
  adjudicates.
- [ADR 002: TOML round-trip via tomlkit](adr-002-toml-round-trip-tomlkit.md)
  selects `tomlkit` for comment-preserving state mutation (resolves Q1).
- [ADR 003: shared interface contract](adr-003-shared-interface-contract.md)
  fixes the JSON envelope and the disambiguated exit-code table (resolves Q2).
- [ADR 004: distribution as installed console-scripts](adr-004-distribution-console-scripts.md)
  records why the commands ship as console-scripts (decision C3).
- [ADR 005: command surface — five scripts, not one multiplexer](adr-005-command-surface-five-scripts.md)
  weighs the multiplexer and settles on five named commands.
- [ADR 006: console-scripts e2e is POSIX-only](adr-006-console-scripts-e2e-posix-policy.md)
  records why the wheel-build end-to-end test runs only where
  `os.name == "posix"`.
- [ADR 007: command surface — a single `novel` multiplexer](adr-007-command-surface-novel-multiplexer.md)
  supersedes ADR 005 and folds the surface into one `novel` multiplexer.
- [ADR 008: the validated chapter-manifest mutator](adr-008-chapter-manifest-mutator.md)
  records `novel-state set-chapters`: its input shape, the exit-2/exit-3 split,
  directory creation, the manifest-at-intent-write ordering, and the torn-turn
  recovery precedence.
- [ADR 009: the phase-gated drafting bijection relaxation](adr-009-drafting-bijection-relaxation.md)
  records that during drafting `novel-state check` relaxes the manifest-to-disk
  bijection to disk-subset-of-manifest behind a default-strict flag, leaving the
  orphan and contiguity directions firing, `reconcile` strict, and the exact
  bijection re-tightening at `final-pass` and `done`.
- [ADR 010: the gate and drafting sub-state mutators](adr-010-gate-drafting-mutators.md)
  records `novel-state set-gate`, `complete-final-pass`, `set-fangirl`, and
  `set-critic-pass`: their input shapes, the exit-2/exit-3 split, the gate-ratio
  binding that makes `set-gate` the repair mutator for a gate that lags its ratio,
  the write-time preconditions for the §5.2-unconstrained fields, and the
  registrar pattern that keeps `novel_state.py` under the 400-line cap.

## Project guides

- [User guide](users-guide.md) explains how to use the generated project and
  its public build and test commands.
- [Developer guide](developers-guide.md) explains the contributor workflow and
  points maintainers to script automation standards. Its "Shared test
  scaffolding" section documents the `working/` fixture corpus
  ([`working_corpus`](../tests/working_corpus)) the slice suites consume.
- [Documentation style guide](documentation-style-guide.md) defines the
  spelling, structure, Markdown, Architecture Decision Record (ADR), Request
  for Comments (RFC), and roadmap conventions used by this documentation set.

## Engineering practice

- [Complexity antipatterns and refactoring strategies](complexity-antipatterns-and-refactoring-strategies.md)
  explains cognitive complexity, the bumpy-road antipattern, and refactoring
  approaches for maintainable code.
- [Local validation of GitHub Actions with act and pytest](local-validation-of-github-actions-with-act-and-pytest.md)
  explains how to validate workflow behaviour locally before relying on remote
  Continuous Integration (CI) runs.
- [Scripting standards](scripting-standards.md) explains the preferred Python
  scripting stack, command execution patterns, and test expectations for helper
  scripts.
