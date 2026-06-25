# Add a torn-turn recovery scenario driven through a real command

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.2.5 closes a coverage gap in the torn-multi-file-turn recovery
story. The harness records a torn turn as an uncleared `[pending_turn]` record
in `working/state.toml`: `novel-state check` detects it and `novel-state
reconcile` either completes or rolls it back, depending on which artefacts
landed (design §3.4, §5.4). Today this recovery is proven two ways, neither of
which crosses the *command* boundary with a torn record produced by a real
command:

- `tests/test_torn_turn_bdd.py` drives the `pending_turn()` context-manager
  primitive directly against a literal `state.toml` and asserts only the
  *producer* signature (the record is left populated). It never runs `check` or
  `reconcile`.
- `tests/test_reconcile_integration.py::test_interrupted_reconcile_leaves_recoverable_record`
  interrupts a `reconcile` mid-bracket but does so by calling the body function
  `_reconcile.reconcile()` *directly* and monkeypatching a private helper. It
  proves recovery converges but bypasses the `novel-state` command entry path
  (Cyclopts app, the shared `run` wrapper, exit-code translation).

After this change a reader can see a torn `[pending_turn]` *produced by a real
`novel-state reconcile` invocation that crashes mid-write*, then watch `novel-state
check` report the torn turn (exit 4 with a `complete-pending-turn` reconciliation)
and `novel-state reconcile` recover it (exit 0, converging to a coherent tree) —
every command driven through the same entry path an operator uses, asserted at the
command boundary. The observable proof is a new behavioural (`pytest-bdd`) scenario
plus a guard that pins the recovery against the real Cyclopts command surface.

You can see it working by running, from the worktree root:

```bash
make test
```

and observing the new behavioural test
`tests/test_torn_turn_recovery_bdd.py::test_*` pass (it fails before the change
because the scenario, feature, and steps do not yet exist).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No production code changes.** This is a test-only task: it adds behavioural
  and integration test coverage. Do not modify any module under
  `novel_ralph_skill/`. If the gap can only be closed by changing production
  code, stop and escalate (it cannot — the mechanism is already present, see
  `Decision Log D-MECH`).
- **Drive through the command boundary, not the bracket primitive.** The new
  recovery scenario must run `check` and `reconcile` through the `novel-state`
  command entry path — the shared
  `novel_ralph_skill.contract.runner.run(build_app(), [...], RunContext(...))`
  wrapper, exactly as `tests/steps/reconcile_steps.py` does — and must *not*
  assert recovery by calling `_reconcile.reconcile()` directly or by driving the
  `pending_turn()` context manager. The roadmap clause is explicit: "driven
  through the command entry points, not the bracket primitive."
- **The torn record must be produced by a real mutator invocation.** The
  populated `[pending_turn]` the scenario recovers must be the residue of an
  interrupted `reconcile` *command*, not a record hand-planted into a fixture
  `state.toml`. (The hand-planted `uncleared-pending-turn` corpus variant has
  command-boundary coverage of the *checker* half only — `check` exits `4`
  with a `complete-pending-turn` reconciliation, asserted at
  `tests/test_novel_state_check_disk.py:85` via the
  `test_disk_evidence_tree_exits_four_with_reconciliation` parametrize case.
  Verified against source: no test drives `reconcile` over a hand-planted
  pending-turn through the command boundary, and `tests/test_reconcile_e2e.py`
  has *no* pending-turn coverage at all — its cases cover `recount`, the two
  `word-counts-cover-drafts` cover-gap directions, and `recreate-log` only.
  This task therefore adds two things the suite lacks: the *real-crash* origin
  and the `reconcile`-boundary recovery of any pending-turn.)
- **No file in `working/` is ever deleted by recovery** (design §5.4). The
  scenario must assert that the author-owned `draft.md` bytes survive the crash
  and the recovery byte-for-byte, mirroring `tests/steps/reconcile_steps.py`'s
  `_assert_drafts_unchanged`.
- **Test placement and scaffolding rules (AGENTS.md; developers-guide §"Shared
  test scaffolding", §"working_corpus").** Tests live under the top-level
  `tests/` tree. The `working_corpus` package is consumed by the sanctioned
  `import working_corpus as wc` value import; installed-binary scaffolding is
  obtained through the `installed_novel_state` fixture, never a cross-module
  import. Step modules live under `tests/steps/` (the directory `pyproject.toml`
  exempts from the assert/argument-count Ruff rules) and are bound by a
  `scenarios(...)` module under `tests/`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (task standing rules).
- **Locked dependencies only.** `cuprum==0.1.0`, `cyclopts==4.18.0`,
  `pytest-bdd==8.1.0`, `pytest-timeout==2.4.0`, `pytest-xdist==3.8.0`,
  `syrupy==5.3.2`, `hypothesis==6.155.7` (verified against `uv.lock`). Introduce
  no new dependency.

## Tolerances (exception triggers)

- **Scope.** If closing the gap requires touching any file under
  `novel_ralph_skill/`, stop and escalate (Constraint "No production code
  changes").
- **Files.** If the change touches more than 6 files (net), stop and escalate.
  The expected set is: 1 new feature file, 1 new steps module, 1 new scenario
  binder, optionally 1 new integration module, and edits to
  `docs/roadmap.md` and this ExecPlan — at most 6.
- **Mechanism.** If the in-process command-runner crash-injection mechanism
  (`Decision Log D-MECH`) does not produce a populated `operation="reconcile"`
  `[pending_turn]` on disk within the runner path, stop and escalate rather than
  reaching for an OS-signal kill or a separate crash entry point.
- **Iterations.** If `make all` still fails after 3 fix attempts on any work
  item, stop and escalate.
- **Interpretation.** If review reads the roadmap clause "interrupts a mutator
  mid-write" as *requiring* a single-file mutator (`recount`/`set-cursor`/
  `advance-phase`) to leave a `[pending_turn]` — which the v1 implementation
  deliberately does not do (those are single-file writers and open no bracket;
  `_recount.py` Decision Log D-PT) — stop and escalate: the only v1 command that
  opens a `[pending_turn]` bracket is `reconcile` (`Decision Log D-MECH`).

## Risks

- Risk: The roadmap premise ("interrupt a mutator mid-write leaving a
  populated [pending_turn] and partial artefacts") implies any mutator opens
  a [pending_turn] bracket, but in v1 only `reconcile` does; `recount`,
  `set-cursor`, `advance-phase`, and `compile` are single-file writers that
  deliberately open no bracket (design §4.1 line 271; `_recount.py` Decision
  Log D-PT). A plan that tries to torn-interrupt `recount` would find no
  bracket to leave a record.
  Severity: high
  Likelihood: high (it is the central design fact of this task)
  Mitigation: The scenario interrupts the *one* real bracket-opening
  command — `reconcile` — mid-write, which is exactly "a torn write produced
  by an actual mutator invocation" (`reconcile` is a mutator, design §3.3
  table). Recorded as `Decision Log D-MECH`; the Constraint and the
  Interpretation tolerance pin it.

- Risk: A subprocess installed-binary e2e cannot inject a deterministic
  mid-write crash, because the crash point is inside the wheel's own
  `_reconcile` module and monkeypatch does not cross the process boundary.
  Severity: medium
  Likelihood: high
  Mitigation: Produce the torn record *in-process* through the command
  runner (`run(build_app(), ["reconcile"], ...)`) with the crash injected by
  monkeypatching `_reconcile._append_recovery_entry` to append-then-raise —
  the same crash seam `test_reconcile_integration.py` already validates,
  but reached through the command entry path rather than the body call. The
  installed-binary subprocess layer already has torn-turn-free reconcile
  coverage in `test_reconcile_e2e.py`; this task does not need a new
  subprocess crash. Recorded as `Decision Log D-INPROC`.

- Risk: After the crashed `reconcile` writes `operation="reconcile"`
  `[pending_turn]` naming `("state.toml", "log.md")` — both of which exist —
  the next `reconcile` classifies it `COMPLETE_PENDING_TURN` with an empty
  missing set and simply clears it, but the *original* stale word-counts
  drift the first run was repairing is still pending, so one recovery pass
  may not converge.
  Severity: medium
  Likelihood: medium
  Mitigation: The scenario drives `reconcile` under the harness re-entry
  model (re-run until `check` is clean, bounded), exactly as
  `test_reconcile_integration.py` documents ("an interrupted RECOUNT
  converges in two passes"). Assert convergence within a bounded loop, not a
  single pass. Recorded as `Decision Log D-CONVERGE`.

- Risk: The new BDD step module duplicates the command-driving helper
  (`_run`, draft-bytes capture) already in `tests/steps/reconcile_steps.py`,
  drawing a "shared test scaffolding" review objection.
  Severity: low
  Likelihood: medium
  Mitigation: Keep the new steps self-contained and small (the helpers are a
  handful of lines and the two scenarios assert different things); if review
  flags duplication, the shared helper extraction is an addendum, not a
  blocker. Note the choice in `Decision Log D-DUP`.

## Progress

- [x] (done) Work item 1: Red — failing torn-turn-recovery behavioural
  scenario at the command boundary. Added the feature, steps, and binder; the
  scenario drives the real-crash origin through the command runner.
- [x] (done) Work item 2: Green — the bound scenario passes (`1 passed`) and the
  full `make all` gate is green (794 passed, 1 skipped).
- [N/A] Work item 3: Optional hardening folded into Work item 1. The producer
  half (the crashed `reconcile` command leaves a populated
  `operation="reconcile"` `[pending_turn]` on disk) is asserted directly by the
  scenario's first `@then` (`crash_leaves_torn_record`), so a standalone
  parametrized integration guard adds no coverage; marked N/A per the plan.
- [x] (done) Work item 4: Documentation — ticked roadmap 6.2.5, updated this
  ExecPlan's living sections, and ran `make markdownlint` and `make nixie`
  (both clean on the changed Markdown).

## Surprises & discoveries

- Observation: No v1 production mutator opens a forward-write `[pending_turn]`
  bracket except `reconcile`. `recount`, `set-cursor`, `advance-phase`, and
  `compile` are single-file `state.toml`/`compiled.md` writers and skip the
  bracket by design.
  Evidence: `novel_ralph_skill/commands/_recount.py` docstring and Decision
  Log D-PT ("It is a *single-file* mutator … so it opens **no**
  `[pending_turn]` bracket"); a repository-wide search for `pending_turn(`
  and `open_pending_turn` finds the producer call sites only in
  `state/document.py` (the primitive) and `commands/_reconcile.py` (the one
  command that brackets `state.toml` + `log.md`).
  Impact: The scenario must interrupt `reconcile`, the sole bracket-opening
  command. This is consistent with the roadmap success clause ("a torn write
  produced by an actual mutator invocation") because `reconcile` is a mutator.

- Observation: The runner-path crash leaves an `operation="reconcile"` record
  naming the two present files `("state.toml", "log.md")`, so the first recovery
  `reconcile` classifies it `COMPLETE_PENDING_TURN` with an empty missing set and
  merely clears it; the original stale word-counts drift is repaired on the
  second pass. The bounded re-entry loop converges in exactly the two passes
  D-CONVERGE predicted, confirmed by the green scenario.
  Evidence: `tests/steps/torn_turn_recovery_steps.py::reconcile_re_runs` loops
  `reconcile` then `check` until `check` exits `0`; the recovered tree settles to
  `pending_turn is None` and `by_chapter == {"01": 0, "02": 24000, "03": 20800}`.
  Impact: A single recovery pass would have left the recount unapplied; the
  bounded loop is load-bearing, not defensive padding.

- Observation: The existing reconcile e2e already drives the installed
  `novel-state` binary through cuprum with an absolute-path program and a
  single-program allowlisted catalogue, and it works.
  Evidence: `tests/test_reconcile_e2e.py` uses `Program(str(installed))`,
  `single_program_catalogue(...)`, `sh.make(prog, catalogue=...)("reconcile")
  .run_sync(context=ExecutionContext(cwd=dest), capture=True)` and asserts
  `.exit_code`/`.stdout`. Verified against `cuprum==0.1.0` source:
  `cuprum/program.py` (`Program = typ.NewType("Program", str)`),
  `cuprum/sh.py:make` and `SafeCmd.argv_with_program` (runs `argv[0]` =
  the absolute path), `cuprum/catalogue.py` (`ProjectSettings`,
  `ProgramCatalogue`).
  Impact: No new cuprum capability is required; the installed-binary layer is
  out of scope for this task (it cannot host a deterministic mid-write crash).

## Decision log

- Decision: D-MECH — Interrupt the `reconcile` command mid-write to produce
  the torn `[pending_turn]`.
  Rationale: `reconcile` is the only v1 command that opens a `[pending_turn]`
  bracket (it brackets the `state.toml` + `log.md` pair in
  `_run_reconcile_bracket`). It is a mutator (design §3.3), so interrupting it
  satisfies "a torn write produced by an actual mutator invocation". The
  single-file mutators open no bracket and cannot leave a `[pending_turn]`.
  Date/Author: 2026-06-25, planning agent.

- Decision: D-INPROC — Produce the torn record in-process through the command
  runner, not through a subprocess.
  Rationale: The crash seam is `_reconcile._append_recovery_entry`; a
  subprocess crash cannot be injected deterministically without a dedicated
  crash entry point (out of scope). Driving `run(build_app(), ["reconcile"],
  RunContext(...))` with that helper monkeypatched to append-then-raise
  crosses the Cyclopts app and the shared `run` wrapper — the command entry
  path — while keeping the crash deterministic. This is strictly stronger
  than the existing `test_reconcile_integration.py`, which calls the body
  function directly.
  Date/Author: 2026-06-25, planning agent.

- Decision: D-CONVERGE — Assert recovery convergence under bounded harness
  re-entry, not a single pass.
  Rationale: A crashed `reconcile` that was repairing stale word-counts
  leaves its own `operation="reconcile"` record over a tree that still needs
  the recount; the first recovery clears the leftover record and the second
  re-applies the recount, mirroring the harness's idempotent re-entry. The
  existing integration test documents and relies on exactly this two-pass
  convergence.
  Date/Author: 2026-06-25, planning agent.

- Decision: D-DUP — Keep the new BDD steps self-contained rather than
  pre-emptively extracting a shared command-driver.
  Rationale: The reconcile and torn-turn-recovery scenarios assert different
  things and the shared helper is a few lines; premature extraction couples
  two suites. Extraction is a cheap addendum if review asks for it.
  Date/Author: 2026-06-25, planning agent.

- Decision: D-FOLD — Fold Work item 3 (the optional integration guard) into the
  BDD scenario rather than adding a separate module.
  Rationale: The plan permits folding the producer-half assertion into Work item
  1 if the BDD coverage is judged sufficient (Stage D). The scenario's first
  `@then` (`crash_leaves_torn_record`) reads the on-disk record straight after
  the runner-path crash and asserts the populated `operation="reconcile"`
  `[pending_turn]` — the producer half the standalone guard would have proven —
  and the `@when`/`@then` chain proves convergence. A separate
  `test_torn_turn_recovery_runner.py` would re-assert the same producer/converge
  facts over the same single stale-word-counts origin, so it is N/A. This keeps
  the change to 5 files (1 feature, 1 steps, 1 binder, roadmap, ExecPlan), within
  the 6-file tolerance.
  Date/Author: 2026-06-25, implementing agent.

- Decision: D-REVIEW — Skip the four coderabbit findings with documented
  reasons; no code change resulted.
  Rationale: (1) the `files_before`/`drafts_before` baseline is captured
  *before* the crash deliberately — asserting the author drafts survive both the
  crash and the recovery byte-for-byte is strictly stronger than a post-crash
  baseline and matches the Constraint wording ("draft.md bytes survive the crash
  and the recovery"); (2) the request to add NumPy `Parameters` sections to every
  public step would diverge from the sibling `tests/steps/reconcile_steps.py`,
  whose step callables carry summary+`Returns` only and which passes the Ruff
  pydocstyle gate — consistency with the established pattern is preferred and the
  gate does not require it; (3) the execplan second-person voice is the sanctioned
  ExecPlan idiom (the execplans skill uses "You can see it working"); (4) the
  flagged `review-r1.md` is a historical review artefact superseded by D-COVERAGE
  in this plan, not a file the change touches.
  Date/Author: 2026-06-25, implementing agent.

- Decision: D-COVERAGE — Correct the round-1 Constraints coverage claim after
  the design reviewer flagged it as false.
  Rationale: Round 1 asserted the hand-planted `uncleared-pending-turn` variant
  "already has command-boundary coverage in
  `tests/test_novel_state_check_disk.py` AND `tests/test_reconcile_e2e.py`".
  Verified against source this is false: `tests/test_reconcile_e2e.py` has no
  pending-turn coverage at all (recount, the two `word-counts-cover-drafts`
  directions, and `recreate-log` only). The hand-planted variant has
  *checker*-only boundary coverage at `tests/test_novel_state_check_disk.py:85`;
  no test reconciles a hand-planted pending-turn through the command boundary.
  The claim is load-bearing for scope, so it is restated accurately: this task
  is the first to reconcile a pending-turn at the command boundary, and it does
  so from the real-crash origin. The scope and the no-regressions list are
  unchanged because they never depended on a reconcile pending-turn e2e existing.
  Date/Author: 2026-06-25, planning agent (round 2).

## Outcomes & retrospective

Delivered as planned. The new behavioural scenario
`tests/test_torn_turn_recovery_bdd.py` binds
`tests/features/torn_turn_recovery.feature` to
`tests/steps/torn_turn_recovery_steps.py` and proves the full Purpose at the
command boundary:

- a real `novel-state reconcile` invocation crashes mid-write (the crash
  injected at the `_reconcile._append_recovery_entry` seam but driven through
  `run(build_app(), ["reconcile"], RunContext(...))`) and leaves a populated
  `operation="reconcile"` `[pending_turn]` on disk;
- `novel-state check` reports the torn turn at exit `4` with a
  `complete-pending-turn` reconciliation and the `pending-turn-cleared`
  discrepancy;
- `novel-state reconcile`, re-run under a bounded re-entry loop, converges (each
  run exits `0`) — the leftover record is cleared and the still-pending recount
  re-applied — and a follow-up `check` exits `0`;
- the recovered `state.pending_turn is None`, the word counts are repaired to the
  disk-derived `{"01": 0, "02": 24000, "03": 20800}`, every chapter `draft.md` is
  byte-for-byte intact across both the crash and the recovery, and no `working/`
  file is removed.

No production code changed (the recovery mechanism was already present, per
D-MECH). The change touched 5 files, within the 6-file tolerance. The full
`make all` gate is green (794 passed, 1 skipped); `make markdownlint` and `make
nixie` are clean on the changed Markdown.

Retrospective: the producer-half assertion folded cleanly into the first `@then`
(D-FOLD), which is why Work item 3 is N/A. The two-pass convergence (D-CONVERGE)
held exactly as the sibling integration test documents: the first recovery pass
clears the leftover `operation="reconcile"` record, the second re-applies the
recount the original stale word-counts still needed.

## Context and orientation

This repository implements a deterministic "harness" for novel drafting as five
console-script commands. The relevant command is `novel-state`, a Cyclopts
application whose subcommands include the read-only `check` (a *checker*) and the
state-writing `reconcile` (a *mutator*). The roadmap and design documents are in
`docs/`; treat them as the source of truth.

Key terms (defined for a first-time reader):

- **`state.toml`** — `working/state.toml`, the harness's single state file. It
  records phase, cursor, gates, word counts, the chapter manifest, and — when a
  multi-file turn is in flight — a `[pending_turn]` record.
- **`[pending_turn]`** — an *intent record* written into `state.toml` before a
  multi-file turn touches any other file, naming the `operation` in flight and
  the `paths` it will write, and cleared only after every artefact is written
  (design §3.4). An *uncleared* `[pending_turn]` after a turn is the on-disk
  signature of a torn (crashed) turn.
- **Torn turn** — a turn that died after writing its `[pending_turn]` intent but
  before clearing it. Recovery completes the partial write (when every missing
  declared artefact is recomputable: `state.toml`/`log.md`) or rolls it back
  (when an unrecoverable `draft.md`/`done.flag` did not land) (design §5.4).
- **`check` / `reconcile`** — `check` reads disk and `state.toml`, derives the
  reconciliation, reports it, and exits `4` on any actionable finding without
  writing. `reconcile` independently re-derives the same reconciliation
  (`derive_reconciliation`) and enacts it: writes the repair, appends a recovery
  receipt to `log.md`, exits `0` (or exits `4`, refusing, on a contradiction).
- **`derive_reconciliation`** — the one pure `(State, working_dir) ->
  Reconciliation` function both commands call, in
  `novel_ralph_skill/state/reconcile.py`. An uncleared `[pending_turn]` whose
  missing declared paths are all recomputable classifies as
  `COMPLETE_PENDING_TURN`; an unrecoverable missing artefact classifies as
  `ROLLBACK_PENDING_TURN`.
- **Command boundary / the `run` wrapper** — every command is exercised through
  `novel_ralph_skill.contract.runner.run(app, argv, context)`, which owns
  exit-code translation and envelope emission. Driving a command "through the
  command entry point" means calling `run(build_app(), [subcommand], RunContext(
  command="novel-state", working_dir="working", human=False))`, exactly as the
  existing BDD step module `tests/steps/reconcile_steps.py` does. This is the
  boundary the roadmap clause means by "command entry points, not the bracket
  primitive".
- **`working_corpus`** — `tests/working_corpus/`, the test-only package that
  materialises `working/` trees from declarative specs. `build_working_tree(spec,
  tmp_path)` returns the built `working/` path; `INCOHERENT_VARIANTS` maps named
  variants to `(spec, expected)` pairs; `COHERENT_BASELINE` is the settled
  baseline spec. Consume it by the sanctioned `import working_corpus as wc` value
  import.
- **`pytest-bdd`** — the behavioural-test framework AGENTS.md mandates. A feature
  file under `tests/features/` declares Gherkin scenarios; a step module under
  `tests/steps/` defines `@given`/`@when`/`@then` callables; a binder module
  under `tests/` calls `scenarios("features/<name>.feature")` and star-imports
  the steps so pytest-bdd discovers them.

Files you will read or touch:

- `docs/novel-ralph-harness-design.md` §3.4 (atomic writes and the
  `[pending_turn]` bracket), §5.4 (disk-authoritative reconciliation; the
  COMPLETE/ROLLBACK pending-turn dispositions). The two sections the roadmap
  task cites.
- `docs/roadmap.md` lines 1342-1354 (task 6.2.5 statement and success clause).
- `docs/developers-guide.md` §"Shared test scaffolding", §"working_corpus",
  §"The five entry points" (the `stub.py` boundary).
- `docs/adr-006-console-scripts-e2e-posix-policy.md` (the installed-binary e2e
  POSIX policy — referenced only for orientation; this task adds no new
  installed-binary e2e).
- `novel_ralph_skill/commands/_reconcile.py` — the `reconcile` body,
  `_run_reconcile_bracket` (the manual intent → edit → receipt → clear bracket),
  and `_append_recovery_entry` (the crash seam).
- `novel_ralph_skill/commands/novel_state.py` — `build_app` (builds the
  `novel-state` Cyclopts app).
- `novel_ralph_skill/contract/runner.py` — `run`, `RunContext`, the `SystemExit`
  exit-code contract.
- `novel_ralph_skill/state/reconcile.py` — `derive_reconciliation`,
  `ReconcileAction`, the COMPLETE/ROLLBACK classification.
- `tests/steps/reconcile_steps.py`, `tests/test_reconcile_bdd.py`,
  `tests/features/reconcile.feature` — the closest existing BDD pattern to copy.
- `tests/test_reconcile_integration.py` — the in-process crash-injection seam
  (`monkeypatch.setattr(_reconcile, "_append_recovery_entry", ...)`), reached via
  the body call rather than the command runner.
- `tests/test_torn_turn_bdd.py`, `tests/features/torn_turn.feature`,
  `tests/steps/torn_turn_steps.py` — the *primitive-level* torn-turn scenario
  this task complements (do not modify; it still proves the producer signature).

## Plan of work

### Stage A: understand and propose (no code changes)

Read the design sections and the orientation files above and confirm the
mechanism: only `reconcile` opens a `[pending_turn]` bracket, and the crash seam
is `_reconcile._append_recovery_entry`. Confirm the command-driving idiom in
`tests/steps/reconcile_steps.py::_run`. Confirm `derive_reconciliation`
classifies the leftover `operation="reconcile"` record naming present
`state.toml`/`log.md` as `COMPLETE_PENDING_TURN`. Go/no-go: if any production
change appears necessary, escalate (Tolerance "Scope").

### Stage B: scaffolding and tests (Work item 1, red)

Add the failing behavioural scenario. Three new test artefacts, no production
change:

1. `tests/features/torn_turn_recovery.feature` — a Gherkin feature with a single
   scenario describing: a real `reconcile` command crashes mid-write over a
   stale tree, leaving an uncleared `operation="reconcile"` `[pending_turn]`;
   `check` reports the torn turn at exit `4`; repeated `reconcile` recovers it;
   a follow-up `check` is clean; and the chapter drafts are byte-for-byte intact
   with no `working/` file removed.

2. `tests/steps/torn_turn_recovery_steps.py` — the step definitions. The `@given`
   builds the `done-claim-stale-word-counts` tree via `wc.build_working_tree`
   and crashes a real `reconcile` command through the runner: it
   `monkeypatch.setattr(_reconcile, "_append_recovery_entry", _append_then_raise)`
   and drives `run(build_app(), ["reconcile"], RunContext(command="novel-state",
   working_dir="working", human=False))` from `working.parent` under
   `pytest.raises` of the sentinel crash error. The `@when`/`@then` steps drive
   `check` and `reconcile` through the same `run` wrapper (production
   `_append_recovery_entry` restored), capture stdout, and assert: `check` exits
   `4` and its envelope `result.reconciliation.action == "complete-pending-turn"`
   with `state record(s) an uncleared pending_turn`-class discrepancy; `reconcile`
   converges within a bounded re-entry loop (Decision D-CONVERGE); the recovered
   `state.pending_turn is None`; drafts unchanged; no file removed. The crashed
   `reconcile` is the "real mutator invocation" that produces the torn write
   (Constraint, Decision D-MECH); it is reached through the command runner, not
   the body call (Constraint, Decision D-INPROC).

3. `tests/test_torn_turn_recovery_bdd.py` — the binder: a module docstring, the
   `from steps.torn_turn_recovery_steps import *  # noqa: F403` star-import, and
   `scenarios("features/torn_turn_recovery.feature")`.

Validation at end of Stage B (red): run the new test alone and confirm it is
*collected* and fails only because, before the steps land, the scenario is
unbound. The accepted red signal is the assembled scenario asserting recovery
fails when (transiently) the convergence loop or the crash-origin assertion is
stubbed out; once the steps are complete it must go green in Stage C. Do not
leave Stage B with a passing test that never exercised the crash path.

### Stage C: green (Work item 2)

Complete the step bodies so the scenario passes. Run the targeted module, then
the full gate. The new behavioural test must pass; the pre-existing
`tests/test_torn_turn_bdd.py` (primitive level) and the reconcile suites must
stay green.

### Stage D: optional hardening (Work item 3) and documentation (Work item 4)

Work item 3 (optional): if review judges the single BDD scenario insufficient
for the "real command origin" claim, add a small parametrized integration guard
`tests/test_torn_turn_recovery_runner.py` that asserts the runner-path crash
leaves the `operation="reconcile"` record on disk (the producer half) for both a
stale-word-counts origin and a coherent-baseline origin, then converges. If the
BDD scenario already covers this, fold the assertion into Work item 1 and mark
Work item 3 N/A in `Progress`.

Work item 4: tick `docs/roadmap.md` task 6.2.5 (`- [ ]` → `- [x]`), update this
ExecPlan's `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes
& Retrospective`, then run the markdown gates.

Each stage ends with validation. Do not proceed past a failing gate.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-5`.

Work item 1 (red) — author the feature, steps, and binder, then collect:

```bash
uv run pytest tests/test_torn_turn_recovery_bdd.py -q
```

Expected before the steps are complete: the test fails (collection error or a
deliberate failing assertion), proving the scenario is not yet satisfied.

Work item 2 (green) — complete the steps, then:

```bash
uv run pytest tests/test_torn_turn_recovery_bdd.py -q
```

Expected: `1 passed` (the bound scenario). Then run the full code gate:

```bash
make all
```

Expected: all format, lint, type, and test gates pass. A representative tail:

```plaintext
...
tests/test_torn_turn_recovery_bdd.py .                              [100%]
====== N passed in T.TTs ======
```

Work item 3 (optional) — if added:

```bash
uv run pytest tests/test_torn_turn_recovery_runner.py -q
make all
```

Work item 4 (documentation) — after ticking the roadmap and updating this plan:

```bash
make markdownlint
make nixie
```

Expected: both pass with no findings on the changed Markdown
(`docs/roadmap.md`, `docs/execplans/roadmap-6-2-5.md`). `make nixie` validates
Mermaid; neither changed file adds a Mermaid diagram, so it is a clean no-op
over the edited files but must still be run per AGENTS.md.

This section must be updated with real transcripts as work proceeds.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Behavioural (`pytest-bdd`, AGENTS.md "behavioural tests").**
  `tests/test_torn_turn_recovery_bdd.py` binds
  `tests/features/torn_turn_recovery.feature`. Running
  `uv run pytest tests/test_torn_turn_recovery_bdd.py` fails before the steps are
  complete and passes after. The scenario proves, all at the command boundary:
  1. a real `novel-state reconcile` invocation crashes mid-write and leaves an
     uncleared `operation="reconcile"` `[pending_turn]` on disk;
  2. `novel-state check` reports the torn turn at exit `4` with a
     `complete-pending-turn` reconciliation;
  3. `novel-state reconcile`, re-run under bounded harness re-entry, recovers the
     torn turn (each run exits `0`) and a follow-up `check` exits `0`;
  4. every chapter `draft.md` is byte-for-byte identical and no `working/` file
     was removed across the crash and the recovery.

- **Integration guard (optional, Work item 3).** If added,
  `tests/test_torn_turn_recovery_runner.py` parametrizes the runner-path crash
  origin and asserts the producer half (the leftover `operation="reconcile"`
  record) and convergence.

- **No regressions.** `tests/test_torn_turn_bdd.py`,
  `tests/test_reconcile_bdd.py`, `tests/test_reconcile_integration.py`,
  `tests/test_reconcile_e2e.py`, `tests/test_novel_state_check_disk.py` stay
  green.

Quality criteria (what "done" means):

- Tests: `make all` passes (it runs format, lint, type-check, and the unit +
  behavioural test suites). The new behavioural test passes; it fails before the
  change.
- Lint/typecheck: covered by `make all` (Ruff + the project type-checker). The
  new step module sits under `tests/steps/`, exempt from the assert/argument-count
  rules; it still carries a module docstring and per-callable docstrings per the
  project's docstring policy.
- Markdown: `make markdownlint` and `make nixie` pass on the changed Markdown.
- Property/mutation: no new invariant-over-inputs is introduced, so a Hypothesis
  property is not required here (the pending-turn round-trip property already
  exists at task 2.2.1). If the new step helpers grow non-trivial branching,
  `mutmut` may be used as the adversary to confirm the asserts kill mutants of
  the convergence-loop and crash-origin logic (per `python-verification`); this
  is optional hardening, not a gate.

Quality method (how we check): `make all`, then `make markdownlint` and `make
nixie` for the Markdown changes, run sequentially (never in parallel — the build
cache rewards sequential runs).

## Idempotence and recovery

Every step is re-runnable. The tests materialise throwaway `working/` trees under
pytest `tmp_path`, so re-running leaves no residue. `monkeypatch` automatically
restores `_reconcile._append_recovery_entry` at the end of each test, so the
crash injection cannot leak across tests. Editing the roadmap checkbox and this
plan is a plain text edit; re-running the markdown gates is safe. If a gate fails
mid-way, fix and re-run the same command; nothing is destructive.

## Artifacts and notes

The crash-injection seam, verified in
`tests/test_reconcile_integration.py::test_interrupted_reconcile_leaves_recoverable_record`
(to be reached through the command runner rather than the body call in this
task):

```python
real_append = _reconcile._append_recovery_entry

def _append_then_crash(working_dir, line):
    real_append(working_dir, line)
    raise _CrashError

monkeypatch.setattr(_reconcile, "_append_recovery_entry", _append_then_crash)
```

The command-driving idiom to copy from `tests/steps/reconcile_steps.py`:

```python
def _run(working, command, monkeypatch):
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command="novel-state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)
```

For the crashed `reconcile` step, wrap that `run(...)` call in
`pytest.raises(_CrashError)` instead of `pytest.raises(SystemExit)`, because the
injected crash propagates out of the body before `run` reaches its `sys.exit`.

The `done-claim-stale-word-counts` variant the scenario builds on (the roadmap
headline stale tree) is defined in
`tests/working_corpus/_reconcile_variants.py::done_claim_stale_word_counts`; its
post-recount drafts hold `{"01": 0, "02": 24000, "03": 20800}` → 44800 across 3
chapters (the convergence target).

## Interfaces and dependencies

Be prescriptive. The new test artefacts use only existing, locked interfaces:

- `novel_ralph_skill.contract.runner.run(app, argv, context) -> NoReturn` and
  `RunContext(command, working_dir, human)` — the command boundary.
- `novel_ralph_skill.commands.novel_state.build_app() -> cyclopts.App` — the
  `novel-state` app factory.
- `novel_ralph_skill.commands._reconcile` — the module whose
  `_append_recovery_entry(working_dir, line)` helper is monkeypatched to inject
  the deterministic mid-write crash. Do not modify it.
- `novel_ralph_skill.state.load_state(path) -> State` — to read back
  `state.pending_turn` and `state.word_counts` for assertions.
- `working_corpus` (value import `import working_corpus as wc`):
  `build_working_tree(spec, tmp_path) -> Path`, `INCOHERENT_VARIANTS[...]`,
  `COHERENT_BASELINE`.
- `pytest_bdd`: `given`, `when`, `then`, `parsers`, `scenarios`.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — `SUCCESS` (0),
  `ACTIONABLE_FINDING` (4).

New test modules to exist at the end of the milestone:

- `tests/features/torn_turn_recovery.feature` — the Gherkin scenario.
- `tests/steps/torn_turn_recovery_steps.py` — defines `@given`/`@when`/`@then`
  callables; a sentinel `class _CrashError(RuntimeError)`; an
  `_append_then_crash` injector; an `_run` command driver; a draft-bytes capture
  and `_assert_drafts_unchanged` (self-contained per Decision D-DUP).
- `tests/test_torn_turn_recovery_bdd.py` — binder calling
  `scenarios("features/torn_turn_recovery.feature")`.
- Optionally `tests/test_torn_turn_recovery_runner.py` — the parametrized
  integration guard (Work item 3).

No new production interface, no new dependency, no new console-script.

## Revision note

- 2026-06-25 (round 2): Corrected the false coverage claim in `Constraints`
  flagged by the design reviewer. The plan previously asserted the hand-planted
  `uncleared-pending-turn` variant had command-boundary coverage in both
  `tests/test_novel_state_check_disk.py` and `tests/test_reconcile_e2e.py`;
  verified against source, the latter has no pending-turn coverage at all and
  the former covers only the `check` half. The Constraints bullet now states the
  coverage accurately and notes this task is the first to reconcile a
  pending-turn at the command boundary. Added `Decision Log` entry D-COVERAGE.
  No work item, scope, tolerance, or test changed — only the justifying claim
  was made truthful; the existing scope already implied the corrected reality.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
review of step 6.2. Execute each as a small addendum pass — no plan or
design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial
follow-ups surfaced alongside these — the reconcile-boundary `ROLLBACK`
recovery scenario (roadmap 6.2.7), the reconcile-family command-driver plugin
(roadmap 7.23.3), and making the corpus the source of truth for the expected
repaired counts (roadmap 7.23.4) — warrant their own plans and are filed as full
tasks; this is the small assertion-tightening only.

- [ ] 6.2.5.1 — Pin the two-pass convergence count in the torn-turn recovery
  tests (from review:6.2.5, low). `test_reconcile_integration.py` and the new
  torn-turn BDD steps document and rely on exactly two-pass convergence (clear
  the leftover record, then re-apply recount) but only assert convergence within
  a bound (`range(3)`); tighten both assertions to the exact pass count so a
  regression that silently raises the number of re-entry passes the harness needs
  to converge fails loudly rather than passing green. Gate with `make all`.
