# Architectural decision record (ADR) 004: distribution as installed console-scripts

## Status

Accepted, 2026-06-21. The deterministic commands ship as installed
console-scripts in the existing `novel_ralph_skill` package, built as a
hatchling wheel, rather than as self-contained `uv` scripts or any other
distribution form.

## Date

2026-06-21.

## Context and problem statement

The deterministic spine must reach the harness as commands it can invoke on
`PATH` every turn. The project already has a Python package skeleton —
`novel_ralph_skill`, a hatchling wheel build — that is on the critical path:
the package's build and console-script wiring must be in place before any
command can be installed and invoked.

A plausible alternative exists. Self-contained `uv` scripts with inline
dependency metadata are increasingly idiomatic for small tools and would avoid
a package install step. Because a future contributor might reach for that
pattern, the rationale for staying with installed console-scripts is worth
recording so the choice is not silently re-litigated. This records
terms-of-reference decision C3.

## Decision drivers

- An existing `novel_ralph_skill` package skeleton already targets a wheel
  build.
- The harness needs commands invocable on `PATH`.
- A credible alternative (`uv` scripts) exists and should be weighed explicitly.

## Requirements

### Functional requirements

- Each command is invocable by name on `PATH` after a single install step.
- The commands share one installable package and one dependency set (including
  `tomlkit`, ADR 002).

### Technical requirements

- The distribution integrates with the project's existing hatchling build and
  the `make`-driven quality gates in `AGENTS.md`.

## Options considered

### Option A: Installed console-scripts in `novel_ralph_skill`

Register the commands as `[project.scripts]` entry points against the existing
package. A wheel build installs them all; they share one dependency resolution
and one version.

### Option B: Self-contained `uv` scripts

Ship each command as a standalone script with inline dependency metadata, run
via `uv`. No package install, but each script resolves dependencies
independently and lives outside the existing package's build and test gates.

| Topic                    | Option A: console-scripts | Option B: `uv` scripts          |
| ------------------------ | ------------------------- | ------------------------------- |
| Fits existing package    | Yes                       | No; sits beside it              |
| Dependency resolution    | Once, shared              | Per script                      |
| Quality-gate integration | Inside `make` gates       | Separate handling               |
| Install step             | One wheel install         | None, but per-run resolution    |
| Shared code reuse        | Direct imports            | Awkward across standalone files |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A. Installed console-scripts in `novel_ralph_skill` reuse the
existing build, share one dependency set, and let the commands import shared
code (the envelope module, the compile-and-hash routine) directly rather than
duplicating it across standalone files. The decision is recorded in
novel-ralph-harness-design.md §2.2 and §4.

## Goals and non-goals

- Goals:
  - Commands invocable on `PATH` from the existing package.
  - Shared dependencies and shared code without duplication.
  - Record C3 with its rationale.
- Non-goals:
  - Whether the commands are five entry points or one multiplexer (ADR 005).

## Migration plan

Not applicable; the package skeleton already exists. Entry points are wired in
roadmap task 1.2.1 and the dependency set is confirmed in task 1.2.2.

## Known risks and limitations

- Console-scripts require an install step the harness environment must perform;
  this is accepted as the cost of shared code and shared dependencies.
- If the project ever wanted zero-install distribution, this decision would be
  revisited; no such requirement exists.

## Outstanding decisions

None. The distribution form is fixed; the command-surface shape is settled
separately in ADR 005.
