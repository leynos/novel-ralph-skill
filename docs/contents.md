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

## Project guides

- [User guide](users-guide.md) explains how to use the generated project and
  its public build and test commands.
- [Developer guide](developers-guide.md) explains the contributor workflow and
  points maintainers to script automation standards.
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
