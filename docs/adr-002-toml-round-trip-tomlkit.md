# Architectural decision record (ADR) 002: TOML round-trip via tomlkit

## Status

Accepted, 2026-06-21. State mutation reads, edits, and re-writes `state.toml`
through `tomlkit`, which preserves on-disk formatting and comments, rather than
through an owned serializer over `tomllib`.

## Date

2026-06-21.

## Context and problem statement

The harness's primary memory is `state.toml`. It is read at the start of every
turn and written at the end. The file carries hand-authored comments and a
deliberate layout that a human maintainer reads during recovery. State mutation
must preserve that formatting and those comments, or each turn degrades the
file until it is unreadable.

The standard-library `tomllib` reads TOML but cannot write it. The reference
material even carried a failed `tomli_w` snippet that did not round-trip
comments. The rebuild must choose a write mechanism. This decision
is hard to reverse once every mutator depends on it, so it is settled before
the state slice is built. It resolves open question Q1 in the terms of
reference.

## Decision drivers

- `state.toml` carries comments and formatting that must survive mutation.
- `tomllib` cannot write; a writer must be chosen or built.
- The choice is load-bearing for every mutator and hard to reverse.

## Requirements

### Functional requirements

- A no-op read-mutate-write preserves the file byte-for-byte, including comments
  and whitespace.
- A real mutation changes only the targeted values, leaving surrounding
  formatting and comments intact.

### Technical requirements

- The mechanism integrates with the atomic temp-file-and-`Path.replace` write
  discipline (novel-ralph-harness-design.md §3.4).
- It is an installable dependency of `novel_ralph_skill`.

## Options considered

### Option A: tomlkit

`tomlkit` is a style-preserving TOML library that round-trips comments and
formatting. Mutators read into its document model, edit values, and
re-serialize with formatting intact. The cost is a third-party dependency.

### Option B: an owned serializer over tomllib

Read with `tomllib`, hold formatting and comments in a side structure, and
write with a hand-built serializer that reapplies them. This owns the full
problem and adds a comment-preserving TOML writer to the project's maintenance
surface for no capability `tomlkit` does not already provide.

| Topic                   | Option A: tomlkit             | Option B: owned serializer   |
| ----------------------- | ----------------------------- | ---------------------------- |
| Comment preservation    | Built in                      | Must be built and maintained |
| Maintenance surface     | One dependency                | A bespoke TOML writer        |
| Risk of round-trip bugs | Borne by a maintained library | Borne by this project        |
| Dependency footprint    | One added dependency          | None added                   |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A: `tomlkit`. Owning a comment-preserving TOML writer is avoidable
complexity for no benefit. `tomlkit` is added to the package dependencies, and
the failed `tomli_w` snippet is removed from the reference material. The
decision is recorded in novel-ralph-harness-design.md §5.3.

## Goals and non-goals

- Goals:
  - Preserve `state.toml` formatting and comments across every mutation.
  - Resolve open question Q1.
- Non-goals:
  - Choosing the schema or the invariants (ADR-adjacent; see
    novel-ralph-harness-design.md §5.1 and §5.2).

## Migration plan

Not applicable; this is a greenfield dependency choice. `tomlkit` is added in
roadmap task 1.2.2 and exercised by the round-trip helper in task 2.2.1.

## Known risks and limitations

- A `tomlkit` major-version change could alter round-trip behaviour; the
  round-trip property test (roadmap 2.2.1) guards against silent regressions.
- `tomlkit` is slower than `tomllib` for reads; state files are small, so the
  cost is immaterial.

## Outstanding decisions

None. The dependency is fixed; the round-trip property is verified in roadmap
2.2.1.
