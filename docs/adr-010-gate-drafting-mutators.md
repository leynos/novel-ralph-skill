# Architectural decision record (ADR) 010: the gate and drafting sub-state mutators

## Status

Accepted, 2026-06-26. The four gate and drafting sub-state fields that previously
had no validated mutator — the three knitting-circle gates
(`gates.knitting.done_30/done_50/done_80`), the final-pass gate
(`gates.final.final_pass_complete`), the critic sub-state (`drafting.critic.pass`),
and the fangirl sub-state (`drafting.fangirl.last_chapter_passed`) — are each set
through a validated `novel-state` subcommand: `set-gate`, `complete-final-pass`,
`set-critic-pass`, and `set-fangirl`. This realises roadmap task 2.2.4 under
ADR 001 (scripts detect and report; the model adjudicates) and design §4.1, §5.1,
and §5.2.

## Date

2026-06-26.

## Context and problem statement

Four fields reached `working/state.toml` with no sanctioned command to write
them. Beta testing therefore forced direct edits of `state.toml` to record a
gate flip, a completed final pass, or a critic/fangirl pass — a direct violation
of ADR 001 (all state mutation goes through validated commands) and of the
skill's "always exercise the installed contract" rule.

The hardest case is the knitting gates. The §5.2 `gate-ratio-consistent`
invariant binds all three at once: a state is coherent only when each of
`done_30`/`done_50`/`done_80` equals `drafted_ratio >= threshold` (thresholds
0.30/0.50/0.80). The harness's primary gate transition — the drafted ratio
crossing a threshold — is performed by the word-count mutators (`recount` /
`set-cursor` move `by_chapter`, which moves the ratio). The gate booleans,
however, had no mutator that asserted the value the ratio now mandates, so a
state whose ratio had crossed 0.30 while `done_30` was still `false` was
incoherent **and unrepairable through a command**. That is the precise hand-edit
hole task 2.2.4 closes.

## Decision drivers

- ADR 001: each field reaches `state.toml` only through a validated command.
- Validate before persist (§3.2, §3.4): a refusal leaves `state.toml`
  byte-for-byte intact.
- The §5.2 invariant set is unchanged; write-time preconditions the validator
  does not own live in the mutator bodies (the ADR 008 precedent).
- The exit-code contract (ADR 003): a state-semantics fault is exit 3, a
  shape/usage fault is exit 2, never the benign exit 1 the harness loops on.
- The AGENTS.md 400-line file cap, which both the body site and the registration
  site press against.

## Decision outcome

### Command names and input shapes

The four single-file mutators are:

- `set-gate` — optional `--knitting-30/--no-knitting-30`,
  `--knitting-50/--no-knitting-50`, `--knitting-80/--no-knitting-80`, and
  `--final/--no-final` flags (one `bool | None` per gate; an omitted flag leaves
  its gate untouched). A single mutator covers all four gate booleans.
- `complete-final-pass` — zero-argument; the named convenience verb for the
  common final-pass flip (`set-gate --final` is the general form). Idempotent.
- `set-fangirl` — `--last-chapter k` (`int`), sets
  `drafting.fangirl.last_chapter_passed`.
- `set-critic-pass` — `--pass p` (`int`), sets the on-disk `drafting.critic.pass`
  key. The body parameter is `pass_number` (the schema renames `pass` because it
  is a Python keyword); the CLI flag is exposed as `--pass` end to end through an
  explicit `cyclopts.Parameter(name="--pass")`, with no name translation between
  wrapper and body.

Each body follows the `set-cursor` skeleton: load the `tomlkit` document, derive
the typed view once to prove structural completeness, edit the on-disk key(s),
derive the proposed view, run the §5.2 validate-before-persist pass, and write
atomically only when the proposed state is coherent.

### `set-gate` is the repair mutator for a gate that lags its ratio

`set-gate` follows the `set-cursor` skeleton, which — unlike `advance-phase` —
does **not** refuse an incoherent prior; it validates only the *proposed* state.
Because `gate-ratio-consistent` binds the gates to the ratio, any *coherent* prior
already has each gate at its ratio-mandated value, so from a coherent prior a flag
set is an idempotent no-op. The validator-permitted *observable* transition is
therefore the **repair** of an *incoherent* prior where the ratio has crossed but
the gate boolean still lags (for example, `recount` moved the ratio past 0.30 but
`done_30` is still `false`). This answers "why can't `set-gate` just flip the flag
from any state": it can only assert the value the ratio mandates. Asserting a gate
true below its threshold, or false once crossed, makes the proposed state
incoherent and is refused with exit 3. `final_pass_complete` has no §5.2 binding,
so `--final` is accepted on any structurally complete prior.

### Exit-code split (exit 2 vs exit 3)

A state-semantics fault — a missing/unparseable/structurally-incomplete
`state.toml`, or a ratio-contradicting `set-gate`, or a write-time precondition
breach — is exit 3 (`STATE_ERROR`), routed through `StateInputError`.

A shape/usage fault is exit 2 (`USAGE_ERROR`). Two arise here: a non-integer
`--last-chapter`/`--pass` (the Cyclopts parser's `CoercionError`, handled by the
shared runner), and a **no-flag `set-gate`** (the operator named no field to
change). The Cyclopts parser cannot catch the latter — a no-flag `set-gate`
parses cleanly to `{}` — so it is detected in the body and routed to exit 2 by a
domain `GateDraftingUsageError(EnvelopeMessagesError)` raised in the registrar
wrapper and caught by a thin `_set_gate_or_usage` adapter that returns a
`CommandOutcome(code=ExitCode.USAGE_ERROR, ...)` **directly**. This copies the
proven `_desloppify.DesloppifyUsageError` + `_scan_or_usage` precedent. It does
**not** raise `cyclopts.ValidationError(msg=...)`: a bare hand-raised
`ValidationError(msg=...)` has `argument`/`group`/`command_chain` all `None`, so
`str(exc)` raises `NotImplementedError` inside the runner's `CycloptsError` arm,
crashing the command with an uncaught traceback rather than a clean exit-2
envelope (verified live driving the real `runner.run`).

### Write-time preconditions for the §5.2-unconstrained fields

`final_pass_complete`, `drafting.critic.pass`, and
`drafting.fangirl.last_chapter_passed` are not bound by the §5.2 invariant set,
so two carry write-time preconditions in their own bodies (the ADR 008
`manifest_coherence_violations` precedent — a pure predicate in the mutator, not
a new validator rule):

- `set-fangirl` requires `0 <= last_chapter <= len(chapters)` — a fangirl pass
  cannot have run on a chapter the manifest does not contain; `0` means no pass
  yet. A breach refuses with exit 3 naming `fangirl-chapter-in-manifest`.
- `set-critic-pass` requires `pass >= 1` (passes are numbered from 1). A breach
  refuses with exit 3 naming `critic-pass-at-least-one`.

Each precondition is checked *before* the §5.2 validate-before-persist pass, which
still runs for defence in depth.

### General `set-gate`, not per-gate verbs

A per-gate alternative (four zero-argument `complete-knitting-30/50/80` verbs plus
`complete-final-pass`) was considered and rejected: the roadmap names `set-gate`
explicitly, and a single multi-flag mutator covers all four gate booleans with one
body and one registration, staying closer to the established
`set-cursor`/`set-chapters` family. The false direction the `bool | None` flags
expose (`--no-knitting-NN`) can never legitimately *write* false above threshold
(the validator refuses it) and is already false below threshold, so on the happy
path it is only ever a refusal or a no-op. It is retained for symmetry and tested
for its refusal arm only; it is **not** a supported "turn a gate off" operation.

### Single-file mutators: no `[pending_turn]` bracket, no `log.md` receipt

Each mutator writes exactly one file (`state.toml`) via one `Path.replace`,
exactly like `set-cursor`/`advance-phase`/`recount`. None is a multi-file writer,
so none opens a `[pending_turn]` record, and none appends a `log.md` receipt —
the existing single-file mutators do not. The roadmap 2.2.4 "log-receipt
discipline" wording binds the *multi-file* mutators (`reconcile`/`set-chapters`),
per the developers' guide "Checker/mutator segregation" (single-file mutators
write one `Path.replace` and open no bracket). Note that `init` is the one
single-file-style mutator that *does* append a `log.md` receipt; the four new
mutators follow the `set-cursor`/`advance-phase`/`recount` no-receipt sub-family,
not `init`, so a reader applying the roadmap wording literally against `init` does
not mistake the absence of a receipt here for an omission.

### The registrar pattern keeps `novel_state.py` under the 400-line cap

The four bodies live in a new sibling module
`novel_ralph_skill/commands/_gate_drafting_mutators.py` (reusing the shared
load/refuse helpers from `_state_mutators.py`), not appended to `_state_mutators.py`
or to `novel_state.py:build_app`, both of which are at or near the cap. The four
`@app.command` wrappers live in a registrar function
`register_gate_drafting_commands(app)` in that same module; `build_app` invokes
it with one deferred-import line plus one call line (the deferred import avoids
the
`_gate_drafting_mutators -> _state_mutators -> novel_state` cycle). A
`@app.command` registers a decorated function onto any `cyclopts.App` regardless
of the defining module, so the wrappers may be defined in the sibling and applied
to the app `build_app` passes in. This is the established way to add subcommands
without growing `novel_state.py` past the cap, and a future subcommand-adding task
should follow the same trail.

## Goals and non-goals

Goals: every gate and drafting sub-state field settable through a validated
command; no hand-edit of `state.toml` required; `check` coherent after each
mutation; refusals exit 3 with the file unchanged; usage/shape faults exit 2.

Non-goals: changing `validate_state` or the §5.2 invariant set (a design change,
out of scope); a "turn a gate off" operation (the false direction is symmetry
only); reconciling the stale design prose that describes the gate ratio as
`current / target` (the validator deliberately uses `sum(by_chapter) / target`;
the doc is stale on this one point and reconciling it is out of scope).

## Known risks and limitations

- The gate-ratio repair semantics are non-obvious; the observable use of
  `set-gate` is the incoherent→coherent repair, pinned by tests rather than
  prose. A reader who expects to flip a gate from any state will find the
  command refuses a ratio-contradicting flip.
- The no-flag `set-gate` exit-2 mechanism depends on the domain-error + adapter
  pattern, not on `cyclopts.ValidationError`; the installed-binary e2e proves the
  clean exit-2 envelope at the boundary.

## Outstanding decisions

None. The command surface, the gate-ratio binding, the exit-code split, the
write-time preconditions, and the registrar pattern are all settled and pinned by
tests.
