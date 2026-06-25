# Architectural decision record (ADR) 007: command surface — a single `novel` multiplexer

## Status

Accepted, 2026-06-25. The deterministic spine ships as a single `novel`
multiplexer with subcommands — `novel state …`, `novel done`, `novel compile`,
`novel desloppify`, `novel wordcount` — rather than as five separately named
console-scripts. This **supersedes ADR 005**, which chose five scripts.

## Date

2026-06-25.

## Context and problem statement

ADR 005 weighed a single `novel` multiplexer against five separate
console-scripts and chose five, but explicitly noted that revisiting was cheap
"if the spine ever grew to many more commands" or if discoverability and naming
came to matter. Two things have since changed the balance, both surfaced while
preparing to dogfood the harness:

1. **The surface already grew into a partial multiplexer.** `novel-state` alone
   exposes six subcommands (`init`, `set-cursor`, `advance-phase`, `recount`,
   `check`, `reconcile`). The real surface is therefore one multiplexer plus
   four flat verbs — the inconsistent worst of both shapes.
2. **Two of the five names pollute `PATH`.** `desloppify` and especially
   `wordcount` are generic global names liable to collide with unrelated tools.
   Installing the package (`uv tool install`) drops both onto `PATH`
   unprefixed, which the maintainer flagged on first install.

The maintainer's stated preference is the single-command shape; namespaced
separate scripts (`novel-desloppify`, `novel-wordcount`) were noted as an
acceptable fallback. This ADR settles the surface before the
chapter-manifest work (roadmap 2.2.3) and before dogfooding, so the first real
use exercises the final shape.

## Decision drivers

- Consistency: one namespace and one structural model for the whole surface.
- `PATH` hygiene: avoid generic global names (`wordcount`, `desloppify`).
- Discoverability: a single `novel --help` surface for the harness and humans.
- The cost of renaming, which is at its lowest now (pre-dogfood, no external
  users, full test coverage as a safety net) and only grows.
- The maintainer's stated preference.

## Options considered

### Option A: Namespace the two unprefixed scripts

Rename `desloppify` → `novel-desloppify` and `wordcount` → `novel-wordcount`,
keeping five separate console-scripts. Smallest change; fixes `PATH` hygiene.
Leaves the structural asymmetry (one script, `novel-state`, carries subcommands;
the other four do not) and keeps five binaries on `PATH`.

### Option B: A single `novel` multiplexer

One entry point dispatches to a `state` subgroup and four leaf verbs. One
process emits one envelope by construction; `novel --help` lists everything;
only `novel` reaches `PATH`. Costs a one-time rename of every `novel-x` reference
to `novel x` across code, tests, the design, and the skill.

| Topic                 | A: namespace two scripts   | B: `novel` multiplexer     |
| --------------------- | -------------------------- | -------------------------- |
| `PATH` names          | Five `novel-*` scripts     | One (`novel`)              |
| Structural uniformity | Asymmetric (state nests)   | Uniform (state + verbs)    |
| Envelope consistency  | Convention (shared module) | Structural + shared module |
| Discoverability       | Five names on PATH         | `novel --help`             |
| One-time rename cost  | Two entry points           | Whole surface              |

_Table 1: Comparison of options._

## Decision outcome

Adopt **Option B: a single `novel` multiplexer**. ADR 005's pro-five reasons have
weakened: its headline argument was "avoid renaming every reference", but the two
generic names must be renamed regardless, the surface has already become a
partial multiplexer, and the rename churn is cheapest now. The multiplexer's
"trade-aways" that ADR 005 cited against it — independent per-command versioning
and subset installation — are equally unwanted under five scripts, so they no
longer favour five. Against a residual cost (a mechanical, test-covered rename),
the multiplexer delivers a uniform structure, a clean single-name `PATH`
footprint, a discoverable `novel --help`, and matches the maintainer's
preference.

This is an honest close call: Option A would also resolve the maintainer's
literal `PATH` concern at lower cost. Option B is chosen for the better
end-state and because the moment to pay the rename is now, before dogfooding
hardens the old names into use.

The subcommand structure:

- `novel state init | set-cursor | advance-phase | recount | check | reconcile`
- `novel done`
- `novel compile [--check]`
- `novel desloppify [--pack … | --ledger …] [--chapter …]`
- `novel wordcount`

The shared envelope and exit-code policy (ADR 003) continue to be enforced by
the shared scaffolding module (roadmap step 1.3); the single entry point makes
that consistency structural as well. The distribution form (installed
console-script, ADR 004) is unchanged — there is now one `[project.scripts]`
entry, `novel`, instead of five.

## Goals and non-goals

- Goals:
  - One uniform, discoverable command surface under a single `novel` namespace.
  - Remove generic unprefixed names from `PATH`.
- Non-goals:
  - The shared contract itself (ADR 003) or the distribution mechanism (ADR 004).
  - Independent per-command versioning or subset installation (not wanted).

## Migration plan

Implemented by roadmap task 1.2.12. It collapses the five `[project.scripts]`
entries to a single `novel` entry dispatching into the existing Cyclopts apps
(the `state` subgroup plus four leaf verbs), updates the command-name single
source of truth (`novel_ralph_skill/commands/names.py`), migrates the
installed-binary e2e tests and the contract suite to invoke `novel <sub>`,
sweeps the design prose and diagrams and `SKILL.md` (including its Setup section
and every bare-command reference) from `novel-x` to `novel x`, and removes the
four generic entry points. The shared scaffolding, exit-code policy, and
envelope are unchanged.

## Known risks and limitations

- The rename touches a broad surface (entry points, the name source of truth,
  the installed-binary e2e tests, the design, and the skill). The existing
  snapshot and e2e suite is the safety net; the migration task gates on it.
- A nested Cyclopts command group adds one indirection over a flat script; this
  is negligible and the `state` group already demonstrates the pattern.

## Outstanding decisions

None. The surface is fixed at a single `novel` multiplexer; the migration is
roadmap task 1.2.12.
