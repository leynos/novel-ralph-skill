# Add a command-boundary partial-landed ROLLBACK scenario for an unrecoverable `done.flag`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.2.14 closes the last open cell of the torn-turn ROLLBACK
disposition matrix at the command boundary. The matrix has two axes: the
unrecoverable trigger (`draft.md` body versus `done.flag`) and whether a partial
artefact landed before the crash (never-landed versus partial-landed). Three of
the four cells are already proven end-to-end through the command entry points:

- never-landed `draft.md` (task 6.2.7),
- partial-landed `draft.md` (task 6.2.12,
  `tests/features/torn_turn_rollback_partial.feature`),
- never-landed `done.flag` (task 6.2.13, the second `Examples` row of
  `tests/features/torn_turn_rollback.feature`).

The fourth cell — a torn `mark-done` turn declaring an unrecoverable `done.flag`
that never lands, *after a partial `done.flag` residue did land* — is exercised
only by the pure in-process classifier; it has never been driven through the
`check`/`reconcile` command boundary. This plan adds that proof.

After this change a developer can run `make test` and see a new behavioural
scenario,
`tests/features/torn_turn_rollback_partial_done_flag.feature`, in which:

1. a real design §3.4 `pending_turn` bracket raises mid-turn over the coherent
   baseline, declaring an unrecoverable `working/manuscript/chapter-99/done.flag`
   via `operation="mark-done"`, after landing a partial `done.flag` residue
   inside an existing manifest chapter directory;
2. `novel state check` reports the torn turn at exit 4 with a
   `rollback-pending-turn` reconciliation naming the `pending-turn-cleared`
   discrepancy;
3. `novel state reconcile` rolls it back in a single pass (exit 0), clearing the
   record and appending a `rollback-pending-turn` receipt to `log.md`;
4. a follow-up `check` exits 0;
5. the partial `done.flag` residue is preserved byte-for-byte on disk,
   unreferenced by state, with no `working/` file removed and no file fabricated
   beyond `state.toml` and `log.md`.

The developer can also read the developers' guide torn-turn scenario-family note
and see all four ROLLBACK cells enumerated, with the partial-landed half now
covering both triggers.

This is the success clause of roadmap 6.2.14
(`docs/roadmap.md`): "a torn turn whose declared `done.flag` partially landed is
detected by `check` and rolled back by `reconcile` at the command boundary, with
the partial artefact preserved on disk and unreferenced by state, closing the
partial-landed `done.flag` cell of the §5.4 rollback surface left after 6.2.12
and 6.2.13."

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-14`. Never edit
  the root/control worktree.
- Do not modify production code under `novel_ralph_skill/`. This task is a
  test-and-docs addition only; the classifier
  (`novel_ralph_skill/state/reconcile.py::_classify_pending_turn`) and the
  disk-evidence detectors
  (`novel_ralph_skill/state/disk_evidence.py`) already treat `done.flag` as an
  unrecoverable ROLLBACK trigger and must remain unchanged. If the scenario
  cannot be expressed without touching production code, stop and escalate — the
  predecessor cells (6.2.7/6.2.12/6.2.13) all closed with test-only diffs and a
  production change would signal a misread of the disposition rules.
- The torn `[pending_turn]` record must be produced by the *real* design §3.4
  `pending_turn` context manager
  (`novel_ralph_skill/state/document.py::pending_turn`) raising mid-turn, not by
  a hand-planted `state.toml` fixture field. This mirrors the predecessor
  ROLLBACK suites and is the producer-side faithfulness the roadmap clause and
  design §3.4 demand.
- Recovery must be driven through the shared runner
  `novel_ralph_skill.contract.runner.run` over `build_app()` (the command entry
  path an operator uses), not by calling the bracket primitive or the
  `derive_reconciliation` classifier directly.
- The partial `done.flag` residue must be placed so the disposition stays
  `ROLLBACK_PENDING_TURN` and does **not** short-circuit to REFUSE. Design §5.4
  (and `disk_evidence.py::_check_done_flag_without_draft`) make a real
  `done.flag` beside an empty or absent `draft.md` a refuse-class
  `done-flag-without-draft` violation; the residue must therefore avoid being a
  literal `done.flag` in a manifest chapter lacking a non-empty draft (see
  Decision D-RESIDUE).
- En-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, feature
  text, and commit messages (AGENTS.md; `docs/scripting-standards.md`;
  en-gb-oxendict skill).
- Markdown wraps at 80 columns for prose/bullets, 120 for code blocks; tables
  and headings unwrapped; dash bullets; GitHub-flavoured footnotes (AGENTS.md
  "Markdown guidance").
- All AGENTS.md quality gates must pass before each commit: `make check-fmt`,
  `make lint`, `make typecheck`, `make test`, `make audit`; plus
  `make markdownlint` and `make nixie` for the Markdown change.

## Tolerances (exception triggers)

- Scope: if implementation requires touching more than the three new test
  artefacts (feature, steps, binder) plus the one developers'-guide note — for
  example any edit under `novel_ralph_skill/` — stop and escalate.
- Production code: if any production module under `novel_ralph_skill/` must
  change for the scenario to classify ROLLBACK and recover, stop and escalate
  (the disposition is meant to already hold).
- Disposition: if the constructed residue placement yields REFUSE or COMPLETE
  rather than `ROLLBACK_PENDING_TURN` at `check`, stop and escalate before
  weakening any assertion; re-derive the placement from
  `disk_evidence.py`/`reconcile.py` rather than relaxing the expected exit code.
- Iterations: if `make test` still fails for the new scenario after 3 focused
  attempts, stop and escalate with the failing transcript.
- Dependencies: if any new external dependency appears necessary, stop and
  escalate (none is expected; the suite reuses `pytest-bdd`, `working_corpus`,
  and the existing contract runner).
- Ambiguity: if the residue-placement decision (D-RESIDUE) proves materially
  contestable against the disk-evidence detectors, stop and present the options
  with trade-offs.

## Risks

- Risk: a literal `done.flag` residue trips `done-flag-without-draft` (a
  refuse-class violation) and the disposition becomes REFUSE, not ROLLBACK.
  Severity: high. Likelihood: medium.
  Mitigation: Decision D-RESIDUE places the residue as a `.tmp` sibling inside a
  manifest chapter directory that already carries a non-empty `draft.md`. A
  non-`done.flag` filename is never inspected by
  `disk_evidence.py::_check_done_flag_without_draft` (which `stat`s only the
  literal `chapter-dir / "done.flag"`), so it fires nothing. Work item 1 records
  the option set; Work item 3 asserts the exit-4 ROLLBACK action so a REFUSE
  regression fails loudly.
- Risk: the residue accidentally creates a new `chapter-NN/` directory and trips
  the refuse-class `manifest-disk-bijection` (orphan direction). Severity:
  medium. Likelihood: low.
  Mitigation: place the residue inside an *existing* manifest chapter directory
  (chapter-03 in the baseline). The bijection keys on `chapter-NN/` directory
  presence only (`_disk_paths.py::_on_disk_chapter_numbers`), not on stray files
  within a chapter dir, so a `.tmp` file adds no on-disk chapter number. This is
  the exact mechanism the partial-`draft.md` sibling (6.2.12) already relies on.
- Risk: the new suite drifts from the predecessor partial-landed suite, leaving
  two near-identical step modules whose helpers diverge. Severity: low.
  Likelihood: medium.
  Mitigation: Decision D-DUP keeps the step helpers self-contained per the
  predecessor convention (the two suites assert different residue facts and the
  helpers are a handful of lines), and the docstrings cross-reference each
  other. If a third partial-landed boundary appears, the roadmap already defers
  shared scaffolding extraction to step 7.23, so do not pre-extract here.
- Risk: the developers'-guide note bullet currently mislabels the partial-landed
  family as "(task 6.2.13)" and mentions only `draft.md`. Severity: low.
  Likelihood: high (observed). Mitigation: Work item 4 corrects the label and
  enumerates both partial-landed triggers; `make markdownlint`/`make nixie` gate
  the prose.

## Progress

- [x] Work item 1 — Add the failing partial-landed `done.flag` feature and
  binder (red). Done: the binder star-imports a not-yet-existing step module, so
  the gate suite goes red at `make typecheck` (`unresolved-import`) before `make
  test` — the intended pre-fix red. Committed together with Work item 2's step
  module so each commit's gates stay green per the workflow's deterministic-gate
  rule (the red was captured and recorded, not committed).
- [x] Work item 2 — Add the step module driving the scenario through the command
  boundary. Done: the new scenario passes (PASSED) and `make all` is green
  (1179 passed, 1 skipped). Disposition held at ROLLBACK (`check` exit 4,
  `rollback-pending-turn`, `pending-turn-cleared`) with no production change.
- [x] Work item 3 — Confirm green and pin the residue-preservation and
  ROLLBACK-action assertions; run full gates. Done: no hardening edit was
  required — Work item 2 already pinned every assertion the bar demands (check
  exit 4 + `rollback-pending-turn` action + `pending-turn-cleared` discrepancy;
  reconcile exit 0 + cleared record + `rollback-pending-turn:` receipt; follow-up
  check exit 0; residue byte-for-byte preserved, `files_before <= after`,
  `fabricated <= {state.toml, log.md}`, drafts identical, residue unreferenced).
  Per the plan this item folds into Work item 2's commit (no separate commit).
  `python-verification` confirms an example-based behavioural assertion suffices:
  the scenario pins a single concrete torn-turn shape, not an input-range
  invariant, so neither Hypothesis, CrossHair, nor mutmut is in scope (and mutmut
  would target production code this task must not change). Full suite incl.
  `make audit` green.
- [x] Work item 4 — Extend the developers' guide torn-turn scenario-family note
  to enumerate both partial-landed triggers and correct the task label. Done:
  the partial-landed bullet now corrects the attribution (partial-landed
  `draft.md` is task 6.2.12, partial-landed `done.flag` is task 6.2.14), and
  enumerates both
  triggers, cites `torn_turn_rollback_partial_done_flag.feature`, and records the
  ROLLBACK-not-REFUSE rationale (residue inside an existing chapter dir; the
  `done.flag` residue's non-`done.flag` filename). `make markdownlint`/`make
  nixie` clean and the suite green.

## Surprises & discoveries

- Observation: the disposition this scenario proves already holds in production
  code; `_classify_pending_turn` keys ROLLBACK on any missing declared path
  whose basename is outside `_RECOMPUTABLE_BASENAMES` (`{state.toml, log.md}`),
  which a declared `done.flag` satisfies.
  Evidence: `novel_ralph_skill/state/reconcile.py` lines 178-194; the
  `_RECOMPUTABLE_BASENAMES` set in
  `novel_ralph_skill/state/_reconcile_precedence.py`.
  Impact: this task is test-and-docs only; no production change is in scope.
- Observation: `done-flag-without-draft` only inspects the literal
  `chapter-dir / "done.flag"` path for each *manifest* chapter, so a `.tmp`
  residue is invisible to it.
  Evidence: `novel_ralph_skill/state/disk_evidence.py`
  `_check_done_flag_without_draft` lines 162-190 (`(chapter_dir /
  "done.flag").exists()`).
  Impact: confirms Decision D-RESIDUE keeps the disposition ROLLBACK, not REFUSE.
- Observation: the Work item 1 red surfaces at `make typecheck`
  (`ty` raises `unresolved-import` for the missing step module) rather than at
  `make test` (collection error), because `typecheck` runs before `test` in
  `make all`. Same red, earlier gate.
  Impact: the documented red-check command (`! make test`) still holds when run
  in isolation; under `make all` the red is observed one gate earlier.
- Observation: the new step module's expanded docstring pushed it to 405 lines,
  tripping pylint's `too-many-lines` (cap 400); the §3.4/§5.4 docstring was
  tightened to land at exactly 400 lines while keeping the D-RESIDUE/D-DECLARED/
  D-DUP citations and both refuse-class-invariant rationales.
  Impact: no behavioural change; the assertions and decisions are unchanged.

## Decision log

- Decision (D-RESIDUE): land the partial `done.flag` residue as a `.tmp` sibling
  named `done.flag.partial.tmp` inside an existing manifest chapter directory
  (chapter-03 of `COHERENT_BASELINE`, which carries a non-empty `draft.md`).
  Rationale: this is the faithful §3.4/§5.4 analogue of the partial-`draft.md`
  residue (the temp file a never-completed atomic write left behind), and the
  non-`done.flag` filename guarantees `done-flag-without-draft` never fires, so
  the disposition stays `ROLLBACK_PENDING_TURN`. A literal `done.flag` residue
  was rejected: in a manifest chapter without a non-empty draft it trips
  refuse-class `done-flag-without-draft` (design §5.4; the `done.flag`-beside-
  empty-draft clause), and chapter-03 already carries a non-empty draft so a
  literal flag there would be *coherent* (`word-counts-match-drafts`) rather than
  a residue, defeating the "unreferenced partial artefact" point of the proof.
  Date/Author: 2026-06-26, planning agent.
- Decision (D-DECLARED): the unrecoverable artefact the bracket declares is
  `working/manuscript/chapter-99/done.flag` via `operation="mark-done"`,
  matching the never-landed `done.flag` `Examples` row of 6.2.13 so the two
  `done.flag` cells differ only in residue presence. chapter-99 is absent from
  the baseline manifest, so the declared basename `done.flag` is outside
  `{state.toml, log.md}` and never lands → ROLLBACK.
  Rationale: keeps the four-cell matrix orthogonal and reuses the verified
  trigger.
  Date/Author: 2026-06-26, planning agent.
- Decision (D-DUP): keep the new step helpers self-contained rather than sharing
  with `tests/steps/torn_turn_rollback_partial_steps.py`.
  Rationale: the predecessor partial-landed suite made the same call
  (its module docstring records D-DUP); the two suites assert different
  residue-preservation facts (a `.tmp` `draft.md` residue versus a `.tmp`
  `done.flag` residue) and the helpers are a handful of lines. The roadmap defers
  shared command-driving scaffolding to step 7.23, so no premature extraction.
  Date/Author: 2026-06-26, planning agent.
- Decision (D-COMMITORDER): commit the failing feature + binder (Work item 1)
  together with the green step module (Work item 2) in a single atomic commit
  rather than committing the red state on its own.
  Rationale: the df12-build workflow gates every commit on a green `make all`,
  which is incompatible with committing a deliberately-red state. The pre-fix red
  AGENTS.md requires was still produced and recorded (the binder's
  `unresolved-import` red at `make typecheck`); folding the two items keeps every
  committed HEAD green while preserving the red-before/green-after evidence in the
  Progress and Surprises logs. Work items 1 and 2 are additive and inseparable in
  practice (the binder is dead without the steps), so a single commit loses no
  audit value.
  Date/Author: 2026-06-26, implementation agent.
- Decision (D-SINGLEFEATURE): add a *new* dedicated feature file rather than
  adding a third `Examples` row to `torn_turn_rollback_partial.feature`.
  Rationale: the existing partial feature is a single concrete `Scenario` (not a
  `Scenario Outline`) whose step phrasing and residue helpers are `draft.md`-
  specific; a `done.flag` residue asserts a different filename and a different
  declared operation. A sibling feature mirrors how 6.2.12 and 6.2.13 are kept in
  separate features and keeps each scenario's prose self-describing. If a future
  reviewer prefers parametrisation, that is a follow-up refactor, not a blocker.
  Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

Completed. All four torn-turn ROLLBACK cells are now proven end-to-end through
the command boundary: never-landed `draft.md` (6.2.7), never-landed `done.flag`
(6.2.13), partial-landed `draft.md` (6.2.12), and — added here — partial-landed
`done.flag` (6.2.14). The new scenario was red before its step module existed
(the binder's `unresolved-import` at `make typecheck`) and passes after
(`test_a_torn_markdone_turn_that_left_a_partial_doneflag_residue...` PASSED;
`make all` 1179 passed, 1 skipped). No
divergence between the predicted residue placement and the actual disposition:
the `.tmp` residue (`manuscript/chapter-03/done.flag.partial.tmp`) kept the
disposition at `ROLLBACK_PENDING_TURN` exactly as Decision D-RESIDUE predicted —
`check` reported exit 4 with `rollback-pending-turn`/`pending-turn-cleared` on the
first attempt, with no REFUSE short-circuit. No production code under
`novel_ralph_skill/` was touched (test-and-docs only, as the constraints
required). The developers' guide now enumerates the full family with correct task
attributions and cites the new feature.

Deviations from the plan, with rationale:

- Commit structure: Work items 1 and 2 were committed together rather than as a
  standalone red commit, because the df12-build workflow gates every commit on a
  green `make all` (Decision D-COMMITORDER). The pre-fix red AGENTS.md requires
  was still produced and recorded.
- Work item 3 folded into the verification record (no separate code change), as
  the plan explicitly permitted; it was committed as a small ExecPlan tick so the
  audit trail stays explicit.
- The Work item 1 red surfaced at `make typecheck`, not `make test`, because
  `typecheck` precedes `test` in `make all` (Surprises log). Same red, earlier
  gate.

## Context and orientation

The repository is a Python 3.13 package, `novel_ralph_skill`, implementing the
"novel-ralph" harness: a set of `novel state` subcommands (`check`,
`reconcile`, and others) that read and reconcile a `working/state.toml` against
on-disk evidence. Tests live under the top-level `tests/` tree (AGENTS.md forbids
unit tests inside package directories because xdist-backed coverage relies on
that layout). Behavioural tests use `pytest-bdd`: a `.feature` file under
`tests/features/`, a step module under `tests/steps/`, and a thin binder module
`tests/test_*_bdd.py` that star-imports the steps and calls `scenarios(...)`.

Key files for this task:

- `novel_ralph_skill/state/document.py` — defines the design §3.4 `pending_turn`
  context manager. It persists a `[pending_turn]` intent record *before*
  yielding and clears it on clean exit; an exception inside the `with` body
  leaves the populated record on disk. This is the production producer of torn
  turns.
- `novel_ralph_skill/state/reconcile.py` — `derive_reconciliation` and
  `_classify_pending_turn`. The latter (lines 165-204) computes the declared
  paths still missing from disk and chooses ROLLBACK when any missing basename is
  outside `_RECOMPUTABLE_BASENAMES` (`{state.toml, log.md}`); a missing
  `done.flag` qualifies. The precedence in `derive_reconciliation` (lines
  283-341) runs the refuse-class arm *before* the pending-turn arm, which is why
  the residue must not trip a refuse-class violation.
- `novel_ralph_skill/state/disk_evidence.py` — the disk-evidence detectors.
  `_check_manifest_disk_bijection` (lines 124-159) keys on `chapter-NN/`
  directory presence; `_check_done_flag_without_draft` (lines 162-190) `stat`s
  only the literal `chapter-dir / "done.flag"` for each manifest chapter and
  fires `done-flag-without-draft` (refuse-class) when a flag sits beside an empty
  or absent draft. A `.tmp` residue is invisible to both.
- `novel_ralph_skill/state/_reconcile_precedence.py` — defines `_REFUSE_CLASS`
  (`{manifest-disk-bijection, done-flag-without-draft}`) and the
  `_RECOMPUTABLE_BASENAMES` set.
- `novel_ralph_skill/contract/runner.py` — the shared `run(app, args, ctx)`
  wrapper and `RunContext`; commands are driven through it as an operator would,
  raising `SystemExit` carrying the exit code, and printing the JSON envelope to
  stdout.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode` (SUCCESS = 0,
  ACTIONABLE_FINDING = 4, etc.).
- `tests/working_corpus/` — the corpus builder. `working_corpus.build_working_tree`
  materialises a `WorkingTreeSpec` into a real `working/` tree.
  `working_corpus.COHERENT_BASELINE` is the canonical mid-drafting coherent tree:
  three chapters, each with a non-empty `draft.md`; chapter-01 and chapter-02
  carry a `done.flag`, chapter-03 does not. The chapter the torn turn declares
  (chapter-99) is absent from this manifest.

The artefacts this task mirrors:

- `tests/features/torn_turn_rollback_partial.feature` and
  `tests/steps/torn_turn_rollback_partial_steps.py` and
  `tests/test_torn_turn_rollback_partial_bdd.py` — the partial-landed `draft.md`
  cell (task 6.2.12). The new artefacts are the `done.flag` siblings of these.
- `tests/features/torn_turn_rollback.feature` and
  `tests/steps/torn_turn_rollback_steps.py` — the never-landed `Scenario
  Outline` whose `done.flag` row (`operation="mark-done"`,
  `working/manuscript/chapter-99/done.flag`) the new scenario reuses as its
  declared-but-never-landed artefact.

Terms used in this plan:

- "Torn turn": a multi-file operation that crashed after persisting its
  `[pending_turn]` intent record but before clearing it (design §3.4), leaving
  the record uncleared on disk.
- "ROLLBACK disposition": the reconciliation `derive_reconciliation` returns when
  a torn turn's declared artefact is unrecoverable from disk; `reconcile` clears
  the record and leaves any partial artefacts in place (design §5.4 item 2).
- "Partial-landed residue": a partial artefact (here a `.tmp` temp file) that
  *did* materialise before the crash and must be preserved byte-for-byte,
  unreferenced by state.
- "Command boundary": invocation through `novel_ralph_skill.contract.runner.run`
  over `build_app()`, the same entry path an operator drives.

### Why no external-library research is load-bearing here

This task adds an *in-process* `pytest-bdd` scenario that drives `check` and
`reconcile` through `contract.runner.run` in the same process. It launches no
subprocess, builds no wheel, and invokes no installed console-script. Therefore
none of the externally-documented behaviours sometimes pinned in this codebase
are load-bearing for 6.2.14:

- `cuprum` (secure command execution / catalogue allowlisting,
  `/data/leynos/Projects/cuprum`): not used — there is no external command to
  run. The predecessor partial-landed suite
  (`tests/steps/torn_turn_rollback_partial_steps.py`) imports no `cuprum`
  symbol, confirming the boundary is in-process.
- `Cyclopts` `--help`/`--version` handling: not exercised; the scenario invokes
  the `check`/`reconcile` subcommands, not the CLI's help/version arms.
- `pytest-timeout` per-test overrides and `uv run` resolution semantics: not
  load-bearing; the scenario adds no timeout marker and runs under the existing
  `make test` invocation.

Every load-bearing behavioural claim in this plan (ROLLBACK classification of a
missing `done.flag`; the residue's invisibility to the refuse-class detectors;
the bijection keying on directory presence) is pinned by reading the cited
project source and by the assertions Work item 3 adds. No undecided fork remains.
If implementation reveals that the runner unexpectedly shells out, stop and
escalate (it would contradict the cited source).

## Plan of work

Red-green-refactor across four atomic, independently committable work items.
Each ends with the full AGENTS.md gate suite. The first three items together
form the behavioural proof; the fourth is the documentation addendum.

### Work item 1 — Add the failing feature and binder (red)

Implements roadmap 6.2.14 (design §3.4, §5.4 item 2). Mirrors
`tests/features/torn_turn_rollback_partial.feature` and
`tests/test_torn_turn_rollback_partial_bdd.py`.

Read before starting:

- `docs/roadmap.md` task 6.2.14 (success clause and the four-cell framing).
- `docs/novel-ralph-harness-design.md` §3.4 (torn turn / `pending_turn`) and
  §5.4 (disk-authoritative reconciliation, item 2: "Rolling back removes nothing
  — the partial artefacts stay on disk, unreferenced by state", lines 566-567;
  and the `done.flag`-beside-empty-draft REFUSE clause, lines 572 and 916).
- `tests/features/torn_turn_rollback_partial.feature` (the `draft.md` sibling to
  mirror) and `tests/features/torn_turn_rollback.feature` (the `mark-done`
  declared-artefact row to reuse).

Skills to load:

- `python-router` → `python-testing` (pytest-bdd feature/step/binder structure,
  the `tests/`-tree placement rule).
- `en-gb-oxendict` (Oxford spelling in the feature narrative).

Add `tests/features/torn_turn_rollback_partial_done_flag.feature`: a single
`Scenario` mirroring the `draft.md` partial feature but for the `done.flag`
trigger. The feature narrative must state that the bracket declares an
unrecoverable `done.flag` (operation `mark-done`) that never lands, after a
partial `done.flag` residue landed as a `.tmp` sibling inside an existing
manifest chapter directory, and that the disposition stays ROLLBACK (not REFUSE)
because the `.tmp` residue is invisible to `done-flag-without-draft`. Use step
phrasing parallel to the `draft.md` feature, e.g.:

```gherkin
Given a real pending_turn bracket raises mid-turn after a partial done.flag residue landed
Then the torn turn leaves an uncleared mark-done pending_turn on disk
And the partial residue is present on disk and unreferenced by state
When check runs against that torn tree
Then check exits 4 reporting a rollback-pending-turn reconciliation
When reconcile rolls the torn turn back in a single pass
Then reconcile clears the record and appends a rollback-pending-turn receipt
And a follow-up check exits 0
And the rollback preserves the partial residue byte-for-byte and fabricates no file
```

Add the binder `tests/test_torn_turn_rollback_partial_done_flag_bdd.py`: a thin
module with a docstring citing roadmap 6.2.14, a star-import from the new step
module, and `scenarios("features/torn_turn_rollback_partial_done_flag.feature")`.
At this point the step module does not yet exist, so the binder import fails.

Validation: `make test` must error on the missing step module (collection
error), demonstrating the scenario is wired and red. Then run the full gate
suite for the Markdown-free Python diff:

```bash
make check-fmt && make lint && make typecheck && ! make test  # expected: test red (missing steps)
```

Commit the failing feature + binder (the red state is the intended pre-fix
failing test AGENTS.md requires).

Tests added by this item: the feature file and binder (the scenario itself; no
separate unit/property/snapshot/e2e tests — this is a behavioural proof and the
runner is the system under test).

### Work item 2 — Add the step module driving the command boundary

Implements roadmap 6.2.14 (design §3.4 producer; §5.4 item 2 disposition).
Mirrors `tests/steps/torn_turn_rollback_partial_steps.py`.

Read before starting:

- `tests/steps/torn_turn_rollback_partial_steps.py` (the `draft.md` step module
  to mirror, including its `_Outcome` dataclass, `_run`/`_run_capturing`
  helpers, and residue-capture pattern).
- `novel_ralph_skill/state/document.py::pending_turn` (the producer bracket).
- `novel_ralph_skill/contract/runner.py` (`run`, `RunContext`).
- `novel_ralph_skill/state/disk_evidence.py::_check_done_flag_without_draft`
  (to confirm the `.tmp` residue fires nothing).

Skills to load:

- `python-router` → `python-testing` (step definitions, fixtures, `target_fixture`).
- `python-router` → `python-errors-and-logging` (the `_TornError` sentinel and
  `pytest.raises` discipline) if any exception-raising idiom needs review.
- `en-gb-oxendict`.

Add `tests/steps/torn_turn_rollback_partial_done_flag_steps.py` mirroring the
`draft.md` partial step module, with these concrete differences (Decisions
D-RESIDUE, D-DECLARED):

- `_UNRECOVERABLE_FLAG = "working/manuscript/chapter-99/done.flag"` (the declared
  artefact that never lands; chapter-99 is absent from the baseline manifest).
- `_RESIDUE_RELPATH = "manuscript/chapter-03/done.flag.partial.tmp"` — a `.tmp`
  sibling inside the existing chapter-03 directory (which carries a non-empty
  draft), so it creates no new `chapter-NN/` directory and is not a literal
  `done.flag`; the bijection and `done-flag-without-draft` both stay clean and
  the disposition stays ROLLBACK.
- `_RESIDUE_BODY` — a short residue marker string.
- The `given` step enters `pending_turn(working / "state.toml",
  operation="mark-done", paths=[_UNRECOVERABLE_FLAG])`, writes the residue inside
  the bracket body, then raises `_TornError` (use the `# noqa: PT012` the sibling
  uses for the multi-statement `pytest.raises` body).
- The "leaves an uncleared mark-done pending_turn" step asserts
  `interrupted.pending_turn.operation == "mark-done"` and
  `tuple(interrupted.pending_turn.paths) == (_UNRECOVERABLE_FLAG,)`.
- The residue helpers capture the `.tmp` residue bytes separately from any
  `draft.md` (reuse the `_draft_bytes` / `_present_files` helpers verbatim; the
  `.tmp` residue is not a `draft.md` so it never enters the draft map).
- The `check`/`reconcile`/follow-up steps are identical in structure to the
  sibling: `check` exits 4 with `rollback-pending-turn` and `pending-turn-cleared`;
  `reconcile` exits 0, clears the record, and appends `rollback-pending-turn:` to
  `log.md`; follow-up `check` exits 0.
- The final preservation step asserts the residue is present and byte-for-byte
  unchanged, `files_before <= after`, `fabricated <= {"state.toml", "log.md"}`,
  every `draft.md` byte-for-byte identical, and the residue path is referenced by
  neither the chapter manifest nor any cleared `pending_turn`.

Place the module under `tests/steps/` (the directory `pyproject.toml` exempts
from the assert/argument-count lint rules, as the sibling docstring notes). The
docstring must cite roadmap 6.2.14, design §3.4/§5.4, Decisions D-RESIDUE,
D-DECLARED, and D-DUP, and cross-reference the `draft.md` partial module.

Validation:

```bash
make check-fmt && make lint && make typecheck && make test
```

The new scenario must now pass (green). If `check` returns exit 2 or 3 rather
than 4, or the reconciliation action is REFUSE, stop and escalate — re-derive the
residue placement from `disk_evidence.py` before weakening any assertion
(tolerance: Disposition).

Commit the green step module.

### Work item 3 — Confirm green, pin residue-preservation and ROLLBACK-action assertions, full gates

Implements roadmap 6.2.14 success clause (the distinguishing residue-preservation
half of §5.4 item 2).

This item is a verification-and-hardening pass over the assertions added in Work
item 2; if Work items 1-2 already produced a fully-asserting green scenario, this
item is the confirmation commit (or folds into Work item 2's commit if no
hardening edit is needed — keep it separate only if an assertion is strengthened).

Read before starting:

- `tests/steps/torn_turn_rollback_partial_steps.py` final preservation step (the
  bar the `done.flag` proof must match).

Skills to load:

- `python-router` → `python-testing`.
- `python-router` → `python-verification` to confirm whether a property/mutation
  adversary is warranted. Expected conclusion: example-based behavioural
  assertions suffice here — the scenario pins a single concrete torn-turn shape,
  not an invariant over a range of inputs, so neither Hypothesis nor mutmut is in
  scope (record this in the Decision Log if the verification skill agrees). Do not
  add a property test unless the verification skill identifies an input-range
  invariant the example test cannot pin.

Confirm the following assertions are present and meaningful (strengthen if any is
missing):

- `check` exit == `ExitCode.ACTIONABLE_FINDING` (4) and
  `reconciliation["action"] == "rollback-pending-turn"` with `pending-turn-cleared`
  in `discrepancies` — this is the ROLLBACK-action pin that fails loudly on a
  REFUSE/COMPLETE regression.
- `reconcile` exit == `ExitCode.SUCCESS` (0), record cleared, `rollback-pending-turn:`
  receipt in `log.md`.
- Follow-up `check` exit 0.
- Residue present and byte-for-byte unchanged; no `working/` file removed; no
  file fabricated beyond `state.toml`/`log.md`; drafts byte-for-byte identical;
  residue unreferenced by manifest or pending_turn after recovery.

Validation — full AGENTS.md suite (no Markdown changed in this item, but run the
Python gates):

```bash
make check-fmt && make lint && make typecheck && make test && make audit
```

Expect the new scenario green and the full suite passing. Capture the scenario's
PASSED line as evidence. Commit any hardening edit; otherwise this verification
folds into Work item 2.

### Work item 4 — Extend the developers' guide torn-turn scenario-family note

Implements the documentation-maintenance duty (AGENTS.md "Documentation
maintenance"; design §3.4/§5.4) — the analogue of addendum 6.2.13.1 which
refreshed this same note for the never-landed family.

Read before starting:

- `docs/developers-guide.md` lines 1012-1029 (the torn-turn scenario-family
  note). The partial-landed bullet (lines 1026-1029) currently labels the family
  "(task 6.2.13)" — a misattribution, since partial-landed `draft.md` was 6.2.12
  — and mentions only the `write-draft`/`draft.md` residue.
- `docs/documentation-style-guide.md` (wrap and style rules).

Skills to load:

- `en-gb-oxendict` (Oxford spelling).
- `python-router` is not needed; this is a Markdown-only edit.

Edit the partial-landed ROLLBACK bullet so it:

- corrects the task attribution (partial-landed `draft.md` is task 6.2.12; the
  partial-landed `done.flag` cell this plan adds is task 6.2.14), and
- enumerates both partial-landed triggers: a torn `write-draft` turn that left a
  partial `draft.md` `.tmp` residue (6.2.12) and a torn `mark-done` turn that
  left a partial `done.flag` `.tmp` residue (6.2.14), each unpromoted by
  `Path.replace`, unreferenced by state, reported by `check` and rolled back by
  `reconcile`, with the residue preserved byte-for-byte on disk.

Keep prose wrapped at 80 columns; dash bullets; do not reflow surrounding
paragraphs unnecessarily. Cite the new feature file
`tests/features/torn_turn_rollback_partial_done_flag.feature` in the bullet so
the documentation map points at the proof.

Validation — Markdown gates plus the standard suite:

```bash
make markdownlint && make nixie && make check-fmt && make lint && make typecheck && make test
```

Expect markdownlint and nixie clean and the suite green. Commit the guide update.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-14` (the
`Makefile` resolves targets relative to it). The shell resets cwd between
invocations in this environment, so prefer single compound commands.

1. Branch check (already on `roadmap-6-2-14`):

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-14 branch --show-current
   ```

   Expect `roadmap-6-2-14`.

2. Work item 1: create the feature and binder, then:

   ```bash
   make check-fmt && make lint && make typecheck && make test
   ```

   Expect a collection error on the missing step module (red). Commit.

3. Work item 2: create the step module, then:

   ```bash
   make check-fmt && make lint && make typecheck && make test
   ```

   Expect the new scenario PASSED (green). A short expected transcript line:

   ```plaintext
   tests/test_torn_turn_rollback_partial_done_flag_bdd.py::test_a_torn_mark-done_turn... PASSED
   ```

   Commit.

4. Work item 3: confirm/strengthen assertions, then:

   ```bash
   make check-fmt && make lint && make typecheck && make test && make audit
   ```

   Expect all green. Commit any hardening edit.

5. Work item 4: edit `docs/developers-guide.md`, then:

   ```bash
   make markdownlint && make nixie && make check-fmt && make lint && make typecheck && make test
   ```

   Expect markdownlint/nixie clean and suite green. Commit.

## Validation and acceptance

Acceptance is behavioural:

- Before Work item 2, `make test` fails (collection error) for
  `tests/test_torn_turn_rollback_partial_done_flag_bdd.py`. After Work item 2 it
  passes. This is the red-before/green-after AGENTS.md requires.
- The new scenario drives a *real* §3.4 `pending_turn` bracket raising mid-turn,
  not a planted fixture, and recovers through `contract.runner.run` — the command
  boundary, not the classifier.
- `check` reports the torn turn at exit 4 with a `rollback-pending-turn`
  reconciliation and the `pending-turn-cleared` discrepancy.
- `reconcile` exits 0, clears the record, appends a `rollback-pending-turn`
  receipt to `log.md`; a follow-up `check` exits 0.
- The partial `done.flag` residue is present and byte-for-byte unchanged after
  recovery, no `working/` file is removed, no file is fabricated beyond
  `state.toml`/`log.md`, the author-owned drafts are byte-for-byte identical, and
  the residue is referenced by neither the manifest nor any `pending_turn`.
- The developers' guide enumerates all four ROLLBACK cells with correct task
  attributions and cites the new feature.

Quality criteria ("done"):

- Tests: `make test` passes; the new scenario fails before its step module and
  passes after.
- Lint/typecheck/format: `make lint`, `make typecheck`, `make check-fmt` all
  clean (the step module lives under `tests/steps/`, exempt from the
  assert/argument-count rules per `pyproject.toml`).
- Audit: `make audit` clean (no dependency change).
- Markdown (Work item 4): `make markdownlint` and `make nixie` clean.

Quality method: run the gate suite listed per work item before each commit; do
not commit a work item whose gates fail.

## Idempotence and recovery

Every step is a test/docs addition over a coherent tree; re-running the gate
suite is safe and side-effect-free. The behavioural scenario builds its tree in
a pytest `tmp_path`, so repeated `make test` runs never accumulate state. If a
commit's gates fail, amend the work item's diff and re-run the suite before
committing — no rollback of prior commits is needed because the items are
independent and additive. No destructive operation is involved.

## Artifacts and notes

Load-bearing source evidence (verified during planning, worktree
`roadmap-6-2-14`):

- ROLLBACK classification of a missing `done.flag`:
  `novel_ralph_skill/state/reconcile.py::_classify_pending_turn` (lines 178-194)
  — `unrecoverable` is any missing path whose `PurePosixPath(path).name` is not
  in `_RECOMPUTABLE_BASENAMES`; `done.flag` qualifies.
- Refuse-class precedence runs before the pending-turn arm:
  `novel_ralph_skill/state/reconcile.py::derive_reconciliation` (lines 308-323).
- `done-flag-without-draft` inspects only the literal `done.flag` per manifest
  chapter: `novel_ralph_skill/state/disk_evidence.py::_check_done_flag_without_draft`
  (lines 162-190) — so a `.tmp` residue fires nothing.
- Bijection keys on `chapter-NN/` directory presence only:
  `novel_ralph_skill/state/_disk_paths.py::_on_disk_chapter_numbers` and
  `_check_manifest_disk_bijection` (disk_evidence.py lines 124-159).
- Baseline shape (three chapters, each with a non-empty draft; chapter-03 carries
  no `done.flag`): `tests/working_corpus/_library.py` lines 41-118.
- Design §5.4 item 2 ("Rolling back removes nothing — the partial artefacts stay
  on disk, unreferenced by state"): `docs/novel-ralph-harness-design.md` lines
  566-567; the `done.flag`-beside-empty-draft REFUSE clause: lines 572 and 916.

## Interfaces and dependencies

No new modules or dependencies. The new test artefacts use the existing
interfaces:

- `novel_ralph_skill.state.document.pending_turn(state_path, *, operation, paths)`
  — the producer bracket.
- `novel_ralph_skill.contract.runner.run(app, args, RunContext(...))` with
  `RunContext(command="novel state", working_dir="working", human=False)` — the
  command boundary.
- `novel_ralph_skill.commands.novel_state.build_app()` — the Cyclopts app under
  test.
- `novel_ralph_skill.state.load_state(path)` — to read back the recovered state.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — `SUCCESS` (0),
  `ACTIONABLE_FINDING` (4).
- `working_corpus.build_working_tree(COHERENT_BASELINE, tmp_path)` — to
  materialise the baseline tree.
- `pytest_bdd` `given`/`when`/`then`/`scenarios` — the behavioural harness.

New test artefacts created at the end of this plan:

- `tests/features/torn_turn_rollback_partial_done_flag.feature`
- `tests/steps/torn_turn_rollback_partial_done_flag_steps.py`
- `tests/test_torn_turn_rollback_partial_done_flag_bdd.py`

Docs updated:

- `docs/developers-guide.md` (torn-turn scenario-family note).
