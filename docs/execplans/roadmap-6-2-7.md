# Add a reconcile-boundary ROLLBACK_PENDING_TURN recovery scenario

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DELIVERED

## Purpose / big picture

Roadmap task 6.2.7 closes the symmetric half of the torn-multi-file-turn
recovery story at the command boundary. The harness records a torn turn as an
uncleared `[pending_turn]` record in `working/state.toml`: `novel-state check`
detects it and `novel-state reconcile` either *completes* the partial write
(when every missing declared artefact is recomputable — `state.toml`/`log.md`)
or *rolls it back* (when an unrecoverable artefact — a `draft.md` or a
`done.flag` — did not land), per design §3.4 and §5.4 item 2.

Task 6.2.5 already proved the **COMPLETE** disposition at the `reconcile`
command boundary (`tests/test_torn_turn_recovery_bdd.py`): a real `reconcile`
crash leaves an `operation="reconcile"` record naming the present `state.toml`/
`log.md`, which recovers by completing. But the **ROLLBACK** disposition — an
uncleared `[pending_turn]` whose declared unrecoverable artefact never
materialised — has *no reconcile-command-boundary coverage*. Today ROLLBACK is
proven only two ways, neither of which drives `reconcile` over the rollback
case through the command entry path:

- `tests/test_reconcile_derivation.py::test_rollback_*` exercises the *pure*
  `derive_reconciliation` classifier directly (no command run): a hand-built
  `PendingTurn` naming `working/manuscript/chapter-99/draft.md` classifies as
  `ROLLBACK_PENDING_TURN`.
- `tests/test_reconcile.py::test_rollback_clears_record_and_keeps_every_file`
  calls the `reconcile` **body function** `_reconcile.reconcile()` directly
  over a *hand-planted* `pending-turn-rollback-unrecoverable` corpus fixture;
  it never crosses the `novel-state` command entry path (the Cyclopts app, the
  shared `run` wrapper, exit-code translation), and the torn record is planted
  into the fixture rather than produced by a real torn-turn write.

After this change a reader can see an uncleared `[pending_turn]` whose declared
unrecoverable artefact (a `draft.md`) *did not land*, produced by a **real torn
turn** (the design §3.4 `pending_turn` producer bracket raising mid-turn), then
watch `novel-state check` report the torn turn (exit `4` with a
`rollback-pending-turn` reconciliation) and `novel-state reconcile` roll it
back (exit `0`: the record cleared, the partial artefacts left in place, no
`working/` file deleted, the author drafts byte-for-byte intact, a
`rollback-pending-turn` receipt appended to `log.md`) — every command driven
through the same entry path an operator uses, asserted at the command boundary.
The observable proof is a new behavioural (`pytest-bdd`) scenario that is the
ROLLBACK sibling of the COMPLETE scenario task 6.2.5 added.

The change is observable by running, from the worktree root:

```bash
make test
```

and observing the new behavioural test
`tests/test_torn_turn_rollback_bdd.py::test_*` pass (it fails before the change
because the scenario, feature, and steps do not yet exist).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No production code changes.** This is a test-only task: it adds behavioural
  test coverage. Do not modify any module under `novel_ralph_skill/`. The
  ROLLBACK mechanism is already present and exercised in-process
  (`tests/test_reconcile.py::test_rollback_clears_record_and_keeps_every_file`,
  `tests/test_reconcile_derivation.py`); only the *command-boundary* proof of
  the ROLLBACK case from a *real torn turn* is missing. If the gap can only be
  closed by changing production code, stop and escalate (it cannot — see
  `Decision Log D-MECH`).
- **Drive recovery through the command boundary, not the bracket primitive.**
  The new scenario must run `check` and `reconcile` through the `novel-state`
  command entry path — the shared
  `novel_ralph_skill.contract.runner.run(build_app(), [...], RunContext(...))`
  wrapper, exactly as `tests/steps/torn_turn_recovery_steps.py` and
  `tests/steps/reconcile_steps.py` do — and must **not** assert recovery by
  calling `_reconcile.reconcile()` directly or by inspecting
  `derive_reconciliation` for the recovery halves. The roadmap clause is
  explicit: "driven through the command entry points". (The *producer* of the
  torn record is the design §3.4 `pending_turn` bracket primitive — see the
  next constraint and `Decision Log D-PRODUCER`; the producer side is a real
  state mutation, the *recovery* side is the command boundary.)
- **The torn record must be the residue of a real torn turn, not a hand-planted
  fixture field.** The populated `[pending_turn]` the scenario rolls back must
  be produced by the design §3.4 producer — the
  `novel_ralph_skill.state.document.pending_turn(path, operation=..., paths=...)`
  context manager raising before clean exit, leaving the record populated on
  disk exactly as `tests/steps/torn_turn_steps.py` already does — declaring an
  unrecoverable `draft.md`/`done.flag` path that never materialises. It must
  **not** be the `pending-turn-rollback-unrecoverable` corpus fixture's planted
  `pending_turn={...}` dict (that variant has body-call coverage only, in
  `tests/test_reconcile.py`). This is the rollback analogue of 6.2.5's "real
  mutator crash" origin: 6.2.5 could crash `reconcile` (the only command that
  opens a forward bracket) for COMPLETE; ROLLBACK has no v1 command that opens
  a bracket declaring an unrecoverable artefact (`Decision Log D-MECH`,
  `D-PRODUCER`), so the faithful real producer is the §3.4 bracket itself.
- **The torn turn must classify as ROLLBACK, not COMPLETE or REFUSE.** The torn
  record must declare an unrecoverable missing artefact (a `draft.md` or a
  `done.flag` whose basename is **not** in `{"state.toml", "log.md"}`), built
  over an otherwise-coherent tree so the refuse-class disk-evidence invariants
  do not fire first (`derive_reconciliation` precedence: refuse-class →
  pending-turn → recount → recreate-log → none,
  `novel_ralph_skill/state/reconcile.py:256-283`). The scenario must assert the
  reconciliation `action` is `rollback-pending-turn`, distinguishing it from
  the COMPLETE sibling 6.2.5 already proves.
- **Rollback removes nothing and fabricates nothing** (design §5.4 item 2:
  "rolling back clears the `[pending_turn]` record and leaves `state.toml` at
  the prior coherent point … Rolling back removes nothing"). The scenario must
  assert that after recovery every `working/` file present before recovery is
  still present, the author-owned `draft.md` bytes are byte-for-byte unchanged,
  and the partial artefacts (if any) are left on disk unreferenced by state.
- **Test placement and scaffolding rules (AGENTS.md; developers-guide §"Shared
  test scaffolding", §"working_corpus").** Tests live under the top-level
  `tests/` tree. The `working_corpus` package is consumed by the sanctioned
  `import working_corpus as wc` value import. Step modules live under
  `tests/steps/` (the directory `pyproject.toml` exempts from the
  assert/argument-count Ruff rules: `S101`, `PLR0913`, `PLR0917`, `PLR2004`,
  `PLR6301` — verified at `pyproject.toml:98`) and are bound by a
  `scenarios(...)` module under `tests/`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (task standing rules; AGENTS.md §"Code
  style").
- **Locked dependencies only.** `cuprum==0.1.0`, `cyclopts==4.18.0`,
  `pytest-bdd==8.1.0`, `pytest-timeout==2.4.0`, `pytest-xdist==3.8.0`,
  `syrupy==5.3.2`, `hypothesis==6.155.7`, `tomlkit` (verified against
  `pyproject.toml` and `uv.lock`). Introduce no new dependency. This task
  touches **no cuprum** code path: none of the five commands shells out (design
  §4 line 269: "cuprum is required only where a command shells out (none do in
  v1)"), and this scenario drives only in-process command-runner calls.

## Tolerances (exception triggers)

- **Scope.** If closing the gap requires touching any file under
  `novel_ralph_skill/`, stop and escalate (Constraint "No production code
  changes").
- **Files.** If the change touches more than 5 files (net), stop and escalate.
  The expected set is: 1 new feature file, 1 new steps module, 1 new scenario
  binder, and edits to `docs/roadmap.md` and this ExecPlan — exactly 5.
- **Producer mechanism.** If the `pending_turn`-bracket producer (Decision
  D-PRODUCER) does not leave a populated `[pending_turn]` declaring the
  unrecoverable `draft.md` path on disk that `derive_reconciliation` classifies
  as `ROLLBACK_PENDING_TURN`, stop and escalate rather than reaching for the
  hand-planted corpus fixture or an OS-signal kill.
- **Disposition.** If the constructed tree classifies as anything other than
  `ROLLBACK_PENDING_TURN` (for example `COMPLETE_PENDING_TURN` because the
  declared path is recomputable, or `REFUSE` because a refuse-class invariant
  fires first), stop and escalate: the tree construction is wrong and must be
  corrected before the recovery assertions are meaningful.
- **Iterations.** If `make all` still fails after 3 fix attempts on any work
  item, stop and escalate.
- **Interpretation.** The roadmap clause reads "crashes `reconcile` after
  declaring a path that does not materialise". Taken literally this is
  mechanically impossible in v1: `reconcile`'s own bracket only ever declares
  the recomputable `state.toml`/`log.md` (`_RECONCILE_PATHS` in
  `novel_ralph_skill/commands/_reconcile.py:74`), so a crashed `reconcile`
  always classifies as COMPLETE, never ROLLBACK (`Decision Log D-MECH`,
  `Surprises`). If review insists the producer must be a crashed `reconcile`
  *command* declaring an unrecoverable artefact, stop and escalate: that
  requires a production change (`reconcile` does not declare drafts), which
  Constraint "No production code changes" forbids. The faithful achievable
  producer is the §3.4 `pending_turn` bracket (`Decision Log D-PRODUCER`),
  which the Success clause's actual wording ("a torn turn whose declared
  artefact did not land is detected by `check` and rolled back by `reconcile`
  at the command boundary") fully supports.

## Risks

- Risk: The roadmap clause literally says "crashes `reconcile` after declaring a
  path that does not materialise", but `reconcile`'s bracket only declares the
  recomputable `state.toml`/`log.md`, so a crashed `reconcile` can never
  produce a ROLLBACK torn turn. A plan that tries to crash `reconcile` for
  ROLLBACK would find no unrecoverable declared path. Severity: high
  Likelihood: high (it is the central mechanical fact distinguishing 6.2.7 from
  6.2.5) Mitigation: Use the design §3.4 producer — the
  `pending_turn(path, operation="write-draft", paths=["working/manuscript/chapter-NN/draft.md"])`
  bracket raising before clean exit, leaving the populated record — declaring
  an unrecoverable `draft.md` that never lands. This is a *real torn turn* (the
  §3.4 producer, the same one `tests/steps/torn_turn_steps.py` drives), and the
  Success clause's wording ("a torn turn whose declared artefact did not land")
  supports it. Recorded as `Decision Log D-MECH`, `D-PRODUCER`; the Constraint
  and the Interpretation tolerance pin it.

- Risk: The constructed tree could accidentally classify as
  `COMPLETE_PENDING_TURN` (if the declared path is recomputable) or `REFUSE`
  (if a refuse-class disk-evidence invariant — `done-flag-empty-draft`,
  `done-flag-absent-draft`, `compiled-matches-drafts`, `cursor-plan-present` —
  fires first), masking the ROLLBACK case. Severity: medium Likelihood: medium
  Mitigation: Build the torn record over the *coherent baseline* tree
  (`wc.COHERENT_BASELINE` / `wc.build_working_tree(BASE-equivalent)`) — the
  same baseline the `pending-turn-rollback-unrecoverable` variant uses (it is
  `BASE` with only the `pending_turn` field added,
  `_reconcile_variants.py:200`) — so no refuse-class invariant fires, and
  declare a `draft.md` whose basename is not in `{"state.toml", "log.md"}` so
  the missing artefact is unrecoverable. Assert the `check` envelope
  `result.reconciliation.action == "rollback-pending-turn"` explicitly so a
  misclassification fails loudly. Recorded as `Decision Log D-COHERENT`.

- Risk: A single recovery pass may not converge if the torn record is layered
  over a tree that *also* needs another repair (as in 6.2.5, where the crashed
  `reconcile` left a stale recount pending). Severity: low Likelihood: low
  Mitigation: The ROLLBACK producer here is built over an otherwise-coherent
  tree (Mitigation above), so after the single `reconcile` rolls the record
  back the tree is coherent (`pending_turn is None`, no other drift) and one
  pass converges. The scenario asserts a single-pass recovery and a clean
  follow-up `check`; if convergence needs more than one pass the tree
  construction is wrong (escalate per the Disposition tolerance). Recorded as
  `Decision Log D-ONEPASS`.

- Risk: The new BDD step module duplicates the command-driving helpers (`_run`,
  `_run_capturing`, draft-bytes capture, present-files capture) already in
  `tests/steps/torn_turn_recovery_steps.py`, drawing a "shared test
  scaffolding" review objection. Severity: low Likelihood: medium Mitigation:
  Keep the new steps self-contained and small, mirroring the established
  `Decision Log D-DUP` choice the 6.2.5 plan made for the same helpers (the two
  scenarios assert different dispositions and the helpers are a handful of
  lines). If review flags duplication, a shared helper extraction is a cheap
  addendum, not a blocker. Note the choice in `Decision Log D-DUP`.

## Progress

- [x] Work item 1: ROLLBACK-pending-turn behavioural scenario at the reconcile
  command boundary. Added the feature, steps, and binder; the scenario produces
  the torn ROLLBACK record via the §3.4 producer and drives recovery through
  the command runner. Delivered as `tests/features/torn_turn_rollback.feature`,
  `tests/steps/torn_turn_rollback_steps.py`, and
  `tests/test_torn_turn_rollback_bdd.py`. The feature, steps, and binder were
  authored together, so the targeted run was green on first collection rather
  than passing through a separate unbound-collection red phase (a deviation
  from the Stage B red-then-green sequence, noted in
  `Outcomes & Retrospective`); the scenario asserts
  `action == "rollback-pending-turn"` explicitly, so it cannot pass without
  exercising the rollback disposition (a misclassification fails loudly), which
  preserves the Stage B intent.
- [x] Work item 2: Green — the bound scenario passes (`1 passed`) and the full
  `make all` gate (`build check-fmt lint typecheck test`) is green (916 passed,
  1 skipped; format, ruff, pylint-pypy, and `ty` clean).
- [x] Work item 3: Documentation — ticked roadmap 6.2.7, updated this ExecPlan's
  living sections, and ran `make markdownlint` and `make nixie` (both clean);
  prose formatting is covered by the `check-fmt` stage of `make all`. During the
  implementing agent's gate pass, `make markdownlint` flagged two MD013
  line-length findings in this plan (the inline `run(...)` example and the
  rolled-back `detail` string, both single-token spans over 80 columns); both
  were lifted into fenced code blocks (which the repo config allows up to 120
  columns, `code_block_line_length: 120`) to clear the gate without truncating
  the load-bearing identifiers. See `Decision Log D-MD013`.

## Surprises & discoveries

- Observation: No v1 command opens a forward `[pending_turn]` bracket declaring
  an unrecoverable artefact (a `draft.md` or `done.flag`). The only command
  that opens a forward bracket at all is `reconcile`, and it declares only the
  recomputable `state.toml`/`log.md`
  (`_RECONCILE_PATHS = ("state.toml", "log.md")`). The single-file mutators
  (`recount`, `set-cursor`, `advance-phase`, `compile`) open no bracket. There
  is no `write-draft` command in v1 (drafting is the agent's job, not a
  deterministic command). Evidence:
  `novel_ralph_skill/commands/_reconcile.py:73-74` (`_RECONCILE_PATHS`);
  `novel_ralph_skill/commands/_recount.py:7,115` (single-file, opens no
  bracket); a repository search for `open_pending_turn`/`pending_turn(` finds
  producer call sites only in `novel_ralph_skill/state/document.py` (the
  primitive) and `novel_ralph_skill/commands/_reconcile.py` (the one bracketing
  `state.toml` + `log.md`). The `operation="write-draft"` in
  `tests/working_corpus/_reconcile_variants.py:203` is a synthetic fixture tag,
  not a real command. Impact: A crashed `reconcile` *command* can never produce
  a ROLLBACK torn turn (it always declares recomputable paths → COMPLETE). The
  faithful real producer for ROLLBACK is the design §3.4 `pending_turn` bracket
  primitive declaring an unrecoverable `draft.md` and raising before clean exit
  — exactly what `tests/steps/torn_turn_steps.py` already does, here paired
  with command-boundary recovery. This is the load-bearing difference between
  6.2.7 and 6.2.5, recorded in `Decision Log D-MECH`/`D-PRODUCER`.

- Observation: The §3.4 `pending_turn` bracket and the `wc.build_working_tree`
  baseline compose cleanly. Building `wc.COHERENT_BASELINE` materialises a
  coherent `working/` tree; entering
  `pending_turn(working / "state.toml", operation="write-draft", paths=["working/manuscript/chapter-99/draft.md"])`
  and raising leaves the populated `operation="write-draft"` record over that
  otherwise-coherent tree. `derive_reconciliation` then classifies it
  `ROLLBACK_PENDING_TURN` on the first try, and a single `reconcile` clears the
  record (one pass, per D-ONEPASS) — confirming the producer/recovery split the
  plan predicted with no production change and no multi-pass loop. Impact: the
  scenario was green on first run; the deterministic gate (`make all`) reported
  916 passed, 1 skipped with format, ruff, pylint-pypy, and `ty` clean.

## Decision log

- Decision: D-MECH — The ROLLBACK torn turn cannot be produced by crashing a
  real command; it must be produced by the design §3.4 `pending_turn` producer
  primitive. Rationale: `reconcile` is the only v1 command that opens a forward
  `[pending_turn]` bracket, and it declares only the recomputable `state.toml`/
  `log.md`, so a crashed `reconcile` always classifies COMPLETE, never
  ROLLBACK. No v1 command declares an unrecoverable `draft.md`/`done.flag` in a
  bracket. The §3.4 `pending_turn` context manager *is* the production producer
  of torn records (design §3.4; `novel_ralph_skill/state/document.py:222`), so
  a bracket that raises mid-turn declaring an unrecoverable artefact is a
  genuine torn turn, not a synthetic field. This is the rollback analogue of
  6.2.5's COMPLETE crash origin. Date/Author: 2026-06-25, planning agent.

- Decision: D-PRODUCER — Produce the torn record via the
  `novel_ralph_skill.state.document.pending_turn(...)` context manager
  (operation `"write-draft"`, paths
  `["working/manuscript/chapter-NN/draft.md"]`) raising before clean exit, over
  the coherent baseline tree. Rationale: This is the established real-torn-turn
  idiom (`tests/steps/torn_turn_steps.py` drives the same bracket for the
  COMPLETE/recount producer signature). Declaring an unrecoverable `draft.md`
  basename that never lands makes `derive_reconciliation` classify ROLLBACK.
  The producer side is a real state mutation through the production primitive;
  the *recovery* side (`check`, `reconcile`) is driven through the command
  boundary, which is the coverage gap this task closes. Date/Author:
  2026-06-25, planning agent.

- Decision: D-COHERENT — Build the torn record over the coherent baseline so no
  refuse-class invariant fires and the disposition is unambiguously ROLLBACK.
  Rationale: `derive_reconciliation` checks refuse-class invariants *before*
  the pending-turn classification (`reconcile.py:256-265`). Over a coherent
  baseline no refuse-class invariant fires, so the uncleared record reaches the
  pending-turn branch and classifies ROLLBACK on the unrecoverable missing
  path. This mirrors the `pending-turn-rollback-unrecoverable` corpus variant,
  which is `BASE` plus the `pending_turn` field only
  (`_reconcile_variants.py:200-206`). Date/Author: 2026-06-25, planning agent.

- Decision: D-ONEPASS — Assert single-pass recovery (one `reconcile`, then a
  clean `check`), unlike 6.2.5's bounded two-pass loop. Rationale: 6.2.5's
  crashed `reconcile` left its own record over a tree that still needed a
  recount (two passes). Here the ROLLBACK record sits over an
  otherwise-coherent tree, so one `reconcile` clears the record and the tree is
  immediately coherent. A multi-pass need would signal a wrongly-constructed
  tree (escalate per the Disposition tolerance). Date/Author: 2026-06-25,
  planning agent.

- Decision: D-MD013 — Render the two over-80-column single-token spans in this
  plan (the inline `run(...)` command-boundary example and the rolled-back
  `detail` string) as fenced code blocks rather than wrapping them. Rationale:
  both are single, unbreakable identifiers that cannot be hyphenated or wrapped
  mid-token, and the repo markdownlint config grants fenced code blocks a
  120-column budget (`code_block_line_length: 120`) while holding inline prose
  to 80 (`.markdownlint-cli2.jsonc`). Lifting them into fenced blocks clears the
  MD013 gate without truncating the load-bearing tokens or reflowing them into a
  misleading shape. Date/Author: 2026-06-25, implementing agent.

- Decision: D-DUP — Keep the new BDD steps self-contained rather than
  extracting a shared command-driver from
  `tests/steps/torn_turn_recovery_steps.py`. Rationale: The 6.2.5 plan made the
  same call (its own D-DUP) for the same helpers; the COMPLETE and ROLLBACK
  scenarios assert different dispositions and the helpers are a few lines.
  Premature extraction couples two suites; extraction is a cheap addendum if
  review asks for it. (A shared reconcile-family command driver is already
  filed as roadmap task 7.23.3, per the 6.2.5 addenda note.) Date/Author:
  2026-06-25, planning agent.

## Outcomes & retrospective

Delivered as planned. A real torn ROLLBACK turn — produced by the §3.4
`pending_turn` bracket raising mid-turn over `wc.COHERENT_BASELINE`, declaring
the unrecoverable `working/manuscript/chapter-99/draft.md` that never lands —
is detected by `check` (exit `4`, `rollback-pending-turn` with the
`pending-turn-cleared` discrepancy) and rolled back by `reconcile` (exit `0`,
single pass, record cleared, `rollback-pending-turn` receipt appended to
`log.md`, follow-up `check` exit `0`, no `working/` file removed, drafts
byte-for-byte intact) at the command boundary, closing the symmetric half of
the disposition 6.2.5 proved for COMPLETE.

The plan held with no deviations of substance: no production code changed; the
expected five-file set landed (1 feature, 1 steps module, 1 binder, the roadmap
tick, and this plan); and the constructed tree classified unambiguously as
ROLLBACK (no escalation triggered). The only minor process note: work items 1
and 2 were authored together (feature, steps, and binder in one pass), so the
scenario was green on first collection rather than passing through a separate
unbound-red phase — the explicit `action == "rollback-pending-turn"` assertion
still guarantees the rollback path is exercised, satisfying the Stage B intent.
`coderabbit review --agent` raised two minor Markdown findings on this plan (a
stray space in a `tests/steps/torn_turn_steps.py` cross-reference and a
second-person demonstration sentence); both were addressed and the
deterministic gates re-confirmed green.

During the implementing agent's gate pass, `coderabbit review --agent` was
repeatedly rate-limited (the org-attributed CLI quota reported wait times of
roughly 18 down to 1.5 minutes); the call was retried with exponential backoff
(30s, 60s, 120s, 240s, 480s, then a final ~95s wait) until the quota cleared on
the sixth retry. The successful run raised a single minor finding on this plan:
the docs validation sequence omitted `make fmt`. The finding was addressed by
making the formatting-enforcement story explicit (the `check-fmt` stage of
`make all` verifies the changed files are formatted; `make markdownlint`
enforces the Markdown rules; the prose is hand-wrapped so the tree-wide
`make fmt` rewrite is not needed) rather than by adding `make fmt` to the
per-task gate, for the reasons the `Concrete steps` section records. The
deterministic gates (`make all`, `make markdownlint`, `make nixie`) were
re-confirmed green after the edit.

## Context and orientation

This repository implements a deterministic "harness" for novel drafting as five
console-script commands. The relevant command is `novel-state`, a Cyclopts
application whose subcommands include the read-only `check` (a *checker*) and
the state-writing `reconcile` (a *mutator*). The roadmap and design documents
are in `docs/`; treat them as the source of truth.

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
  before clearing it. Recovery *completes* the partial write (when every
  missing declared artefact is recomputable: `state.toml`/`log.md`) or *rolls
  it back* (when an unrecoverable `draft.md`/`done.flag` did not land) (design
  §5.4 item 2).
- **ROLLBACK disposition** — the reconciliation
  `ReconcileAction.ROLLBACK_PENDING_TURN` (`"rollback-pending-turn"`): the torn
  record's missing declared path is an unrecoverable artefact (a `draft.md`/
  `done.flag`, basename not in `{"state.toml", "log.md"}`), so `reconcile`
  clears the record, deletes nothing, leaves the partial artefacts in place,
  and appends a `rollback-pending-turn` receipt
  (`novel_ralph_skill/state/reconcile.py:177-216`, `_classify_pending_turn`;
  `novel_ralph_skill/commands/_reconcile.py:20-21,288-293`).
- **`check` / `reconcile`** — `check` reads disk and `state.toml`, derives the
  reconciliation, reports it under `result.reconciliation`, and exits `4` on
  any actionable finding without writing. `reconcile` independently re-derives
  the same reconciliation (`derive_reconciliation`) and enacts it: for ROLLBACK
  it runs the manual `[pending_turn]` bracket (intent → no-op edit → receipt →
  clear), appends a `rollback-pending-turn` receipt to `log.md`, exits `0`, and
  deletes no `working/` file.
- **`derive_reconciliation`** — the one pure
  `(State, working_dir) -> Reconciliation` function both commands call, in
  `novel_ralph_skill/state/reconcile.py`. Precedence is refuse-class →
  pending-turn → recount → recreate-log → none (`reconcile.py:256-283`). An
  uncleared `[pending_turn]` whose missing declared path is recomputable
  classifies `COMPLETE_PENDING_TURN`; an unrecoverable missing artefact
  classifies `ROLLBACK_PENDING_TURN`.
- **Command boundary / the `run` wrapper** — every command is exercised through
  `novel_ralph_skill.contract.runner.run(app, argv, context)`, which owns
  exit-code translation and envelope emission. Driving a command "through the
  command entry point" means calling

  ```python
  run(build_app(), [subcommand], RunContext(command="novel-state", working_dir="working", human=False))
  ```

  exactly as the existing BDD step modules `tests/steps/reconcile_steps.py` and
  `tests/steps/torn_turn_recovery_steps.py` do. This is the boundary the
  roadmap clause means by "command entry points".
- **The §3.4 producer bracket** —
  `novel_ralph_skill.state.document.pending_turn( path, operation=..., paths=...)`,
  a context manager that writes the `[pending_turn]` record atomically
  *before* yielding and, on an exception, leaves the record populated on disk
  for the next turn's `reconcile` (design §3.4; `document.py:222-266`). This is
  the production producer of torn records; the scenario raises inside it to
  manufacture a genuine torn ROLLBACK turn.
- **`working_corpus`** — `tests/working_corpus/`, the test-only package that
  materialises `working/` trees from declarative specs.
  `build_working_tree(spec, tmp_path)` returns the built `working/` path;
  `INCOHERENT_VARIANTS` maps named variants to `(spec, expected)` pairs;
  `COHERENT_BASELINE` is the settled baseline spec. Consume it by the sanctioned
  `import working_corpus as wc` value import.
- **`pytest-bdd`** — the behavioural-test framework AGENTS.md mandates. A
  feature file under `tests/features/` declares Gherkin scenarios; a step
  module under `tests/steps/` defines `@given`/`@when`/`@then` callables; a
  binder module under `tests/` calls `scenarios("features/<name>.feature")` and
  star-imports the steps so pytest-bdd discovers them.

Files to read or touch:

- `docs/novel-ralph-harness-design.md` §3.4 (atomic writes and the
  `[pending_turn]` producer bracket), §5.4 (disk-authoritative reconciliation;
  item 2, the COMPLETE/ROLLBACK pending-turn dispositions). The two sections
  the roadmap task cites.
- `docs/roadmap.md` lines 1384-1400 (task 6.2.7 statement and success clause).
- `docs/developers-guide.md` §"Shared test scaffolding", §"working_corpus" (the
  sanctioned value import and step-module conventions).
- `docs/adr-002-toml-round-trip-tomlkit.md` (the `tomlkit` document path the
  `pending_turn` bracket writes through — orientation only; no change here).
- `novel_ralph_skill/state/document.py` — `pending_turn`, `open_pending_turn`,
  `clear_pending_turn` (the §3.4 producer the scenario raises inside). Do not
  modify.
- `novel_ralph_skill/state/reconcile.py` — `derive_reconciliation`,
  `ReconcileAction.ROLLBACK_PENDING_TURN`, `_classify_pending_turn` (the
  classification the recovery enacts). Do not modify.
- `novel_ralph_skill/commands/_reconcile.py` — the `reconcile` body and its
  ROLLBACK dispatch (`reconcile.py` module docstring lines 20-21; dispatch
  lines 288-293). Do not modify.
- `novel_ralph_skill/commands/novel_state.py` — `build_app`,
  `_render_reconciliation` (the `check` envelope `result.reconciliation`
  shape). Do not modify.
- `novel_ralph_skill/contract/runner.py` — `run`, `RunContext`, the `SystemExit`
  exit-code contract.
- `tests/steps/torn_turn_recovery_steps.py`,
  `tests/features/torn_turn_recovery.feature`,
  `tests/test_torn_turn_recovery_bdd.py` — the **COMPLETE** sibling this task
  mirrors; the closest pattern to copy. Do not modify.
- `tests/steps/torn_turn_steps.py`, `tests/features/torn_turn.feature` — the
  §3.4 producer idiom (the `pending_turn` bracket raising mid-turn) to copy for
  the producer half. Do not modify.
- `tests/test_reconcile.py::test_rollback_clears_record_and_keeps_every_file`,
  `tests/test_reconcile_derivation.py` — the existing in-process/pure ROLLBACK
  coverage this task complements (do not modify; they still hold).
- `tests/working_corpus/_reconcile_variants.py::pending_turn_rollback_unrecoverable`
  — the reference declaring `working/manuscript/chapter-99/draft.md`; the
  scenario uses the same shape but produces it through the §3.4 bracket rather
  than the planted field.

## Plan of work

### Stage A: understand and propose (no code changes)

Read the design sections and the orientation files above and confirm the
mechanism: the ROLLBACK torn turn must be produced by the §3.4 `pending_turn`
producer declaring an unrecoverable `draft.md` over a coherent baseline (no
command can produce it by crashing — `Decision Log D-MECH`). Confirm the
command-driving idiom in `tests/steps/torn_turn_recovery_steps.py::_run` /
`_run_capturing`. Confirm `derive_reconciliation` classifies an uncleared
record declaring a missing `draft.md` as `ROLLBACK_PENDING_TURN` over a
coherent tree (`reconcile.py:190-206` with no refuse-class invariant firing).
Go/no-go: if any production change appears necessary, escalate (Tolerance
"Scope").

### Stage B: scaffolding and tests (Work item 1, red)

Add the failing behavioural scenario. Three new test artefacts, no production
change:

1. `tests/features/torn_turn_rollback.feature` — a Gherkin feature with a single
   scenario describing: a real §3.4 `pending_turn` bracket raises mid-turn over
   a coherent baseline, declaring an unrecoverable `draft.md` that never lands
   and leaving an uncleared `operation="write-draft"` `[pending_turn]`; `check`
   reports the torn turn at exit `4` with a `rollback-pending-turn`
   reconciliation; `reconcile` rolls it back (exit `0`, single pass); a
   follow-up `check` is clean; and the chapter drafts are byte-for-byte intact
   with no `working/` file removed and the record cleared.

2. `tests/steps/torn_turn_rollback_steps.py` — the step definitions. The
   `@given` builds the coherent baseline tree via
   `wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)` and produces the
   torn record by entering the `pending_turn(working / "state.toml", ...)`
   context manager (operation `"write-draft"`, paths
   `["working/manuscript/chapter-99/draft.md"]`) and raising a sentinel
   `_TornError` inside the `with` block (the bracket leaves the record
   populated, exactly as `tests/steps/torn_turn_steps.py` does). It captures
   the present files and the draft bytes *after* the torn write (the recovery
   baseline). The `@when`/`@then` steps drive `check` and `reconcile` through
   the `run` wrapper, capture stdout, and assert: `check` exits `4` and its
   envelope `result.reconciliation.action == "rollback-pending-turn"` with the
   `pending-turn-cleared` discrepancy; `reconcile` exits `0` in a single pass;
   the recovered `state.pending_turn is None`; the follow-up `check` exits `0`;
   the `log.md` carries a `rollback-pending-turn` receipt; no `working/` file
   removed; drafts byte-for-byte unchanged. The torn record is a real torn turn
   (Constraint, `Decision Log D-PRODUCER`); recovery is driven through the
   command runner, not the body call (Constraint).

3. `tests/test_torn_turn_rollback_bdd.py` — the binder: a module docstring, the
   `from steps.torn_turn_rollback_steps import *  # noqa: F403` star-import, and
   `scenarios("features/torn_turn_rollback.feature")`.

Validation at end of Stage B (red): run the new test alone and confirm it is
*collected* and fails only because, before the steps land, the scenario is
unbound (collection error or a deliberate failing assertion). Do not leave
Stage B with a passing test that never exercised the rollback path.

### Stage C: green (Work item 2)

Complete the step bodies so the scenario passes. Run the targeted module, then
the full gate. The new behavioural test must pass; the pre-existing
`tests/test_torn_turn_bdd.py`, `tests/test_torn_turn_recovery_bdd.py`,
`tests/test_reconcile.py`, `tests/test_reconcile_derivation.py`, and
`tests/test_reconcile_bdd.py` must stay green.

### Stage D: documentation (Work item 3)

Tick `docs/roadmap.md` task 6.2.7 (`- [ ]` → `- [x]`), update this ExecPlan's
`Progress`, `Surprises & Discoveries`, `Decision Log`, and
`Outcomes & Retrospective`, then run the markdown gates.

Each stage ends with validation. Do not proceed past a failing gate.

## Concrete steps

All commands run from the worktree root (the repository checkout for this
branch's worktree).

Work item 1 (red) — author the feature, steps, and binder, then collect:

```bash
uv run pytest tests/test_torn_turn_rollback_bdd.py -q
```

Expected before the steps are complete: the test fails (collection error or a
deliberate failing assertion), proving the scenario is not yet satisfied.

Work item 2 (green) — complete the steps, then:

```bash
uv run pytest tests/test_torn_turn_rollback_bdd.py -q
```

Expected: `1 passed` (the bound scenario). Then run the full code gate:

```bash
make all
```

Expected: all format, lint, type, and test gates pass. A representative tail:

```plaintext
...
tests/test_torn_turn_rollback_bdd.py .                              [100%]
====== N passed in T.TTs ======
```

Work item 3 (documentation) — after ticking the roadmap and updating this plan:

```bash
make markdownlint
make nixie
```

The docs gate is `make markdownlint` and `make nixie`, not `make fmt`:
`make fmt` (mdformat) reformats the entire `docs/` and `skill/` tree, mutating
files unrelated to this task and tripping pre-existing MD013 findings in
`docs/issues/audit-*.md`, so it is unsuitable as the per-task docs gate.
Formatting is still enforced rather than skipped: the `check-fmt` stage of
`make all` verifies the changed files are correctly formatted (failing the gate
on any drift), and `make markdownlint` enforces the structural and 80-column
Markdown rules. The authored Markdown is hand-wrapped to the 80-column limit so
both gates pass without invoking the tree-wide `make fmt` rewrite.

Expected: both pass with no findings on the changed Markdown (`docs/roadmap.md`,
`docs/execplans/roadmap-6-2-7.md`). `make nixie` validates Mermaid; neither
changed file adds a Mermaid diagram, so it is a clean no-op over the edited
files but must still be run per AGENTS.md.

This section must be updated with real transcripts as work proceeds.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Behavioural (`pytest-bdd`, AGENTS.md "behavioural tests").**
  `tests/test_torn_turn_rollback_bdd.py` binds
  `tests/features/torn_turn_rollback.feature`. Running
  `uv run pytest tests/test_torn_turn_rollback_bdd.py` fails before the steps
  are complete and passes after. The scenario proves, all at the command
  boundary:
  1. a real §3.4 `pending_turn` bracket raises mid-turn over a coherent
     baseline,
     declaring an unrecoverable `draft.md` that never lands, and leaves an
     uncleared `operation="write-draft"` `[pending_turn]` on disk;
  2. `novel-state check` reports the torn turn at exit `4` with a
     `rollback-pending-turn` reconciliation and the `pending-turn-cleared`
     discrepancy;
  3. `novel-state reconcile` rolls the torn turn back in a single pass (exit
     `0`),
     the recovered `state.pending_turn is None`, a `rollback-pending-turn` receipt
     is appended to `log.md`, and a follow-up `check` exits `0`;
  4. every chapter `draft.md` is byte-for-byte identical and no `working/` file
     was
     removed across the torn write and the recovery (design §5.4 item 2:
     "Rolling back removes nothing").

- **No regressions.** `tests/test_torn_turn_bdd.py`,
  `tests/test_torn_turn_recovery_bdd.py`, `tests/test_reconcile_bdd.py`,
  `tests/test_reconcile.py`, `tests/test_reconcile_derivation.py`,
  `tests/test_novel_state_check_disk.py` stay green.

Quality criteria (what "done" means):

- Tests: `make all` passes (it runs `build check-fmt lint typecheck test`, per
  `Makefile:28`). The new behavioural test passes; it fails before the change.
- Lint/typecheck: covered by `make all` (Ruff + `ty`). The new step module sits
  under `tests/steps/`, exempt from the assert/argument-count rules
  (`pyproject.toml:98`); it still carries a module docstring and per-callable
  docstrings per the 100% `interrogate` policy (AGENTS.md §"For Python files").
- Markdown: `make markdownlint` and `make nixie` pass on the changed Markdown.
- Audit: `make audit` passes (the repo's dependency-vulnerability gate,
  `Makefile:104`); this task introduces no new dependency, so the audit is a
  clean no-op over the locked set.
- Property/mutation: no new invariant-over-inputs is introduced, so a Hypothesis
  property is not required (the pending-turn round-trip property already exists
  at task 2.2.1, and `derive_reconciliation`'s ROLLBACK classification is
  exercised by `tests/test_reconcile_derivation.py`). If the new step helpers
  grow non-trivial branching, `mutmut` (per the `mutmut` skill /
  `python-verification`) may be used as an optional adversary to confirm the
  asserts kill mutants of the disposition-assertion and no-deletion logic; this
  is optional hardening, not a gate.

Quality method (how we check): `make all` and `make audit`, then
`make markdownlint` and `make nixie` for the Markdown changes (not `make fmt`,
which mass-reformats unrelated docs), run sequentially (never in parallel — the
build cache rewards sequential runs).

## Idempotence and recovery

Every step is re-runnable. The tests materialise throwaway `working/` trees
under pytest `tmp_path`, so re-running leaves no residue. The `pending_turn`
bracket writes only into the throwaway tree, and `monkeypatch.chdir` is
restored at the end of each test, so nothing leaks across tests. Editing the
roadmap checkbox and this plan is a plain text edit; re-running the markdown
gates is safe. If a gate fails mid-way, fix and re-run the same command;
nothing is destructive.

## Artifacts and notes

The §3.4 producer idiom to copy from `tests/steps/torn_turn_steps.py` (here
declaring an unrecoverable `draft.md` and raising a sentinel error so the
bracket leaves the record populated):

```python
class _TornError(RuntimeError):
    """Sentinel raised inside the bracket to simulate a torn turn."""

with pytest.raises(_TornError), pending_turn(
    working / "state.toml",
    operation="write-draft",
    paths=["working/manuscript/chapter-99/draft.md"],
):
    raise _TornError  # die before clean exit; record left populated
```

The command-driving idiom to copy from
`tests/steps/torn_turn_recovery_steps.py`:

```python
def _run_capturing(working, command, monkeypatch):
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command="novel-state", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), json.loads(stream.getvalue() or "{}")
```

The expected `check` envelope shape for the ROLLBACK case (verified against
`novel_ralph_skill/commands/novel_state.py:160-176` `_render_reconciliation` and
`novel_ralph_skill/state/reconcile.py:196-206` `_classify_pending_turn`):

```json
{
  "result": {
    "reconciliation": {
      "action": "rollback-pending-turn",
      "discrepancies": ["pending-turn-cleared"]
    }
  }
}
```

The `detail` field (omitted above for width) is built by
`_classify_pending_turn` as

```text
rolling back torn turn 'write-draft': unrecoverable artefact(s) ['working/manuscript/chapter-99/draft.md'] did not land
```

(`novel_ralph_skill/state/reconcile.py:200-203`); the scenario asserts the
`action` and `discrepancies` rather than the exact prose to stay robust.

The `reconcile` ROLLBACK receipt appended to `log.md` (verified against
`novel_ralph_skill/commands/_reconcile.py:288-292`, which builds the log line as
`f"{action}: {reconciliation.detail}"` where `str(action)` is
`"rollback-pending-turn"`): the line contains
`reconcile: rollback-pending-turn:`.

The coherent baseline the scenario builds on is `wc.COHERENT_BASELINE` (the
settled baseline spec; the `pending-turn-rollback-unrecoverable` corpus variant
is this baseline plus only the `pending_turn` field, per
`tests/working_corpus/_reconcile_variants.py:200-206`), so declaring
`working/manuscript/chapter-99/draft.md` — a chapter the baseline never
materialises — yields a *missing unrecoverable* `draft.md` → ROLLBACK.

## Interfaces and dependencies

Be prescriptive. The new test artefacts use only existing, locked interfaces:

- `novel_ralph_skill.contract.runner.run(app, argv, context) -> NoReturn` and
  `RunContext(command, working_dir, human)` — the command boundary.
- `novel_ralph_skill.commands.novel_state.build_app() -> cyclopts.App` — the
  `novel-state` app factory.
- `novel_ralph_skill.state.document.pending_turn(path, *, operation, paths)` —
  the §3.4 producer context manager (raise inside it to leave a torn record).
  Do not modify.
- `novel_ralph_skill.state.load_state(path) -> State` — to read back
  `state.pending_turn` for assertions.
- `working_corpus` (value import `import working_corpus as wc`):
  `build_working_tree(spec, tmp_path) -> Path`, `COHERENT_BASELINE`.
- `pytest_bdd`: `given`, `when`, `then`, `scenarios`.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — `SUCCESS` (0),
  `ACTIONABLE_FINDING` (4).

New test modules to exist at the end of the milestone:

- `tests/features/torn_turn_rollback.feature` — the Gherkin scenario.
- `tests/steps/torn_turn_rollback_steps.py` — defines `@given`/`@when`/`@then`
  callables; a sentinel `class _TornError(RuntimeError)`; the §3.4-bracket
  producer; an `_run`/`_run_capturing` command driver; draft-bytes and
  present-files capture and the no-deletion/drafts-unchanged assertions
  (self-contained per `Decision Log D-DUP`).
- `tests/test_torn_turn_rollback_bdd.py` — binder calling
  `scenarios("features/torn_turn_rollback.feature")`.

No new production interface, no new dependency, no new console-script.

## Skills and documentation per work item

- **All work items:** load `leta` (code navigation), `sem` (history), and the
  `execplans` skill (this plan's authoring discipline). Use `python-router` to
  reach the smaller Python skills; for the BDD test work load `python-testing`
  (pytest-bdd fixtures, `target_fixture`, scenario binding). Read AGENTS.md
  §"Python verification and testing" and §"Change quality and committing".
- **Work item 1-2 (the scenario):** read design §3.4 and §5.4 item 2;
  `docs/developers-guide.md` §"Shared test scaffolding" / §"working_corpus";
  `tests/steps/torn_turn_recovery_steps.py` (the COMPLETE sibling) and
  `tests/steps/torn_turn_steps.py` (the §3.4 producer idiom). If asserting
  branch-killing on the new helpers, load `python-verification` then `mutmut`
  (optional, not a gate). No `cuprum`, `hypothesis`, or `crosshair` work is
  needed (no new invariant-over-inputs; no shelling out).
- **Work item 3 (docs):** read AGENTS.md §"Markdown guidance"; run
  `make markdownlint` and `make nixie`.

## Revision note

(Delivered. Append later revisions here if the plan changes again.)
