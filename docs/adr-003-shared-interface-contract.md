# Architectural decision record (ADR) 003: shared interface contract

## Status

Accepted, 2026-06-21. The five deterministic commands share one JSON envelope,
one `--human` rendering switch, and one exit-code table whose codes 1 and 4 are
disambiguated: code 1 is a benign negative the loop continues on, code 4 is an
actionable finding the agent must adjudicate or repair.

## Date

2026-06-21.

## Context and problem statement

The harness invokes the deterministic commands every turn and gates on their
output. If each command invents its own output shape and exit-code meaning, the
harness has to special-case every command, and a contract change in one ripples
unpredictably. The commands need one contract.

A design review surfaced a specific defect in the first draft of that contract.
Exit code 1 was overloaded: it meant both "the predicate is not yet satisfied"
— a benign state the loop expects every turn and acts on by continuing — and "a
detector found something to fix", such as a stale compile or a slop violation.
The harness cannot tell "keep drafting" from "stop and regenerate the compile"
by an exit code that means both. The review also asked that machine-actionable
data live in a parseable field rather than in prose, and that the several
`schema_version` numbers in the system be related explicitly.

This ADR fixes the contract and resolves open question Q2 in the terms of
reference.

## Decision drivers

- The harness must branch on command results without bespoke per-command logic.
- "Not yet done" and "found something to fix" must be distinguishable by exit
  code alone.
- The harness must read structured data, never parse human prose.
- The system's three `schema_version` fields must have a stated relationship.

## Requirements

### Functional requirements

- Every command emits a common JSON envelope: `command`, `schema_version`,
  `ok`, `working_dir`, `result`, `messages`.
- A `--human` flag switches stdout to a human rendering; diagnostics go to
  stderr in both modes.
- `result` holds all machine-actionable data; `messages` holds only human prose
  the harness never parses.
- Exit codes distinguish success, benign negative, usage error, state error,
  and actionable finding.

### Technical requirements

- `ok` mirrors the exit code: true only on 0.
- The envelope `schema_version`, the `state.toml` `schema_version`, and each
  rule pack's `schema_version` are independent and separately versioned.

## Options considered

### Option A: One envelope with a disambiguated five-code table

Codes: 0 success; 1 benign negative (predicate not yet satisfied, loop
continues); 2 usage error; 3 state or input error; 4 actionable finding
(desloppify violations, compile divergence, reconciliation conflict).
Structured data in `result`, prose in `messages`.

### Option B: One envelope, four codes, harness parses `result`

Keep codes 0–3, leave code 1 overloaded, and require the harness to read
`result` to tell a benign negative from an actionable finding.

| Topic                        | Option A: five codes | Option B: four codes, parse result |
| ---------------------------- | -------------------- | ---------------------------------- |
| Benign-vs-actionable by code | Yes                  | No; requires JSON parsing          |
| Harness branching cost       | Branch on exit code  | Branch on exit code plus `result`  |
| Risk of mis-looping          | Low                  | Higher; easy to mishandle          |
| Codes used                   | Five                 | Four                               |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A. The exit-code table is:

| Code | Meaning                                          | Harness response                  |
| ---- | ------------------------------------------------ | --------------------------------- |
| 0    | Success; checker satisfied, mutator applied      | proceed                           |
| 1    | Benign negative; predicate not yet satisfied     | continue the loop, no fix needed  |
| 2    | Usage error                                      | stop; the invocation is wrong     |
| 3    | State or input error                             | stop; recover state               |
| 4    | Actionable findings requiring agent intervention | adjudicate or repair, then re-run |

_Table 2: The disambiguated exit-code table._

`result` carries every machine-actionable datum — failed clause names, rule ids
and hit counts, divergent chapters, reconciliation discrepancies — and
`messages` carries only human prose. The three `schema_version` fields evolve
independently: the envelope version tracks this contract, the state version
tracks the on-disk schema, and a pack version tracks its own rule vocabulary,
so revising a rule pack never forces a state migration. The contract is
recorded in novel-ralph-harness-design.md §3.

### The four-flag Cyclopts contract

The exit-code table above is policy; this subsection records the construction
contract that makes the policy enforceable. Every command runs its Cyclopts app
through the shared `run` wrapper rather than calling the app directly, and
`run` requires the app to have been built with four specific flags. Each flag
exists so that `run` — not Cyclopts — owns every `sys.exit` and every envelope
emission:

| Flag                           | Rationale                                                                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `result_action="return_value"` | Returns the body's value to `run` instead of Cyclopts calling `sys.exit` on it, so `run` can emit the success-path envelope.    |
| `exit_on_error=False`          | Makes a usage fault raise a `CycloptsError` rather than exit 1, so `run` can translate it into the contract's exit 2 (Table 2). |
| `print_error=False`            | Suppresses Cyclopts's Rich error panel so the diagnostic channel is the envelope `run` owns, never a second rendering.          |
| `help_on_error=False`          | Suppresses the auto-printed help on a usage fault for the same single-owner reason.                                             |

_Table 3: The four-flag construction contract every command's app must carry._

This four-flag requirement is load-bearing contract machinery, so it has a
single enforcement point: the `make_contract_app(name)` factory in
`novel_ralph_skill/contract/runner.py`. Every command's `build_app()` calls the
factory rather than constructing a bare `cyclopts.App`, so a future sixth
command adopts all four flags by calling `make_contract_app` instead of
re-spelling — or silently dropping — them. Table 2 is the exit-code policy the
flags serve, not the flag specification itself; this table is the
specification. A structural tripwire
(`tests/test_contract_app_centralisation.py`) pins that the four production
constructors and their four entry points consume the factory and the shared
`run` seam.

## Goals and non-goals

- Goals:
  - One contract the five commands share without renegotiation.
  - A code-1-versus-code-4 split the harness can branch on directly.
  - Resolve open question Q2.
- Non-goals:
  - The per-command `result` shapes (novel-ralph-harness-design.md §4).
  - The command-surface shape — five scripts versus a multiplexer (ADR 005).

## Migration plan

Not applicable; greenfield. The shared envelope and exit-code helpers are built
once in roadmap task 1.3.1 and reused by every slice.

## Known risks and limitations

- Adding code 4 means a command author must classify each non-zero outcome as
  benign (1) or actionable (4). The design fixes the classification per command
  (novel-ralph-harness-design.md §4) so it is not re-decided ad hoc.
- A future command might need a sixth code; the table is extensible, but any
  addition is an ADR amendment, not a silent change.

## Outstanding decisions

None. The contract is fixed; conformance is verified by the envelope property
test and snapshots in roadmap task 1.3.1.
