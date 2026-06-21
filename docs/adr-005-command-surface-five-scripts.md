# Architectural decision record (ADR) 005: command surface — five scripts, not one multiplexer

## Status

Accepted, 2026-06-21. The deterministic spine ships as five separately named
console-scripts — `novel-state`, `novel-done`, `novel-compile`, `desloppify`,
`wordcount` — rather than as a single `novel` multiplexer with subcommands.

## Date

2026-06-21.

## Context and problem statement

The design anchors on five deterministic commands, each mapping onto one
deterministic operation. A design review observed that a single `novel`
multiplexer (`novel state`, `novel done`, …) is a close and credible
alternative, and that the design had chosen five without recording the trade.
The review asked for a short ADR settling it before roadmap task 1.2.1 wires
the entry points, so the five-script choice is deliberate rather than defaulted.

The multiplexer's headline appeal is that one entry point emits one envelope by
construction, removing any chance of per-command contract drift, and that
`novel --help` gives a single discoverable surface. The package has no existing
`[project.scripts]` convention to preserve, so neither shape inherits an
advantage from history.

## Decision drivers

- The design's 1:1 mapping of command to deterministic operation.
- The review's request to weigh the multiplexer explicitly.
- The risk of per-command envelope drift, and how each shape mitigates it.
- Discoverability for the harness and for a human maintainer.

## Requirements

### Functional requirements

- Each deterministic operation is invocable as a command.
- All commands emit the shared envelope and exit-code table (ADR 003).

### Technical requirements

- The shape integrates with installed console-scripts (ADR 004).

## Options considered

### Option A: Five separate console-scripts

Each operation is its own entry point. The shared envelope and exit-code policy
are enforced by the shared scaffolding module (roadmap step 1.3), which every
command imports, not by the entry-point shape. Command names map 1:1 onto the
deterministic operations the design and the field report already discuss by
name.

### Option B: One `novel` multiplexer

A single entry point dispatches to subcommands. One process emits one envelope
by construction. `novel --help` lists everything. The trade-aways are
independent per-command versioning and subset installation — neither of which
the project wants — and a slightly heavier single entry point.

| Topic                             | Option A: five scripts           | Option B: `novel` multiplexer        |
| --------------------------------- | -------------------------------- | ------------------------------------ |
| Envelope consistency              | Enforced by shared module (§1.3) | Enforced by single entry point       |
| 1:1 map to operations             | Direct                           | Indirect (one binary, many verbs)    |
| Discoverability                   | Five names on `PATH`             | `novel --help`                       |
| Naming churn across docs          | Matches existing prose           | Renames every `novel-x` to `novel x` |
| Drift risk if scaffolding skipped | Higher in principle              | Lower in principle                   |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A: five separate console-scripts. The multiplexer's main advantage
— one envelope by construction — is already secured by the shared scaffolding
module in roadmap step 1.3, which every command imports, so the envelope
consistency does not depend on a single entry point. Against that, five named
commands map 1:1 onto the deterministic operations the design, the roadmap, and
the field report all refer to by name, and avoid renaming every reference. The
multiplexer's remaining advantages — independent versioning and subset install
— are capabilities the project does not want. The decision is recorded in
novel-ralph-harness-design.md §4.

## Goals and non-goals

- Goals:
  - Record the five-versus-multiplexer trade so the choice is deliberate.
  - Keep the 1:1 command-to-operation mapping.
- Non-goals:
  - The shared contract itself (ADR 003) or the distribution form (ADR 004).

## Migration plan

Not applicable; greenfield wiring. The five entry points are registered in
roadmap task 1.2.1, which depends on this ADR (1.1.5).

## Known risks and limitations

- The envelope consistency the multiplexer would guarantee structurally is, with
  five scripts, guaranteed only if every command uses the shared scaffolding.
  Roadmap step 1.3 and the snapshot suite enforce that; skipping the
  scaffolding would reintroduce drift risk.
- If the spine ever grew to many more commands, a multiplexer might become more
  attractive for discoverability; revisiting this ADR is cheap if that happens.

## Outstanding decisions

None. The command surface is fixed at five scripts; the entry points are wired
in roadmap task 1.2.1.
