# Prove the command-boundary ROLLBACK disposition for an unrecoverable `done.flag`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.2.7 proved one half of the `ROLLBACK` torn-turn disposition at
the `novel-state` command boundary: a turn that declared an unrecoverable
`draft.md` which never landed is detected by `check` (exit 4,
`rollback-pending-turn`) and rolled back by `reconcile` (exit 0). The
production classifier `_classify_pending_turn`
(`novel_ralph_skill/state/reconcile.py:177-216`) treats **two** missing-artefact
basenames as unrecoverable `ROLLBACK` triggers — a `draft.md` body **and** a
`done.flag` (module docstring `reconcile.py:22-24`; rationale comment
`reconcile.py:85-89`). Task 6.2.7 exercised only the `draft.md` trigger
end-to-end through the runner; the `done.flag` trigger is covered solely by the
pure classifier test, an in-process-only proof. The post-merge audit recorded
this asymmetry as `docs/issues/audit-6.2.7.md` Finding 3.

After this change, the behavioural suite proves **both** unrecoverable
`ROLLBACK` triggers end-to-end through the same command entry path an operator
uses. Running the new behavioural scenario observes success: a torn turn
declaring an unrecoverable `done.flag` that never lands is reported by
`check` at exit 4 with a `rollback-pending-turn` reconciliation and rolled back
by `reconcile` at exit 0 — the record cleared, a `rollback-pending-turn` receipt
appended to `log.md`, a follow-up `check` clean, the author-owned drafts intact,
and no `working/` file removed. The `draft.md` trigger 6.2.7 already proved runs
alongside it from the same step module via a single `Scenario Outline`, so both
branches of the `_RECOMPUTABLE_BASENAMES`-exclusion rule carry a command-boundary
proof.

This is a **test-only** change. No production code changes; the production
behaviour already exists and is correct. The work closes a coverage gap, exactly
as 6.2.7 did for `draft.md`.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No production code changes.** This task closes a test-coverage asymmetry. The
  `done.flag` trigger is already implemented and correct in
  `novel_ralph_skill/state/reconcile.py`. If implementing the scenario appears to
  require a production edit, stop and escalate — that signals the mechanism was
  mis-analysed.
- **Do not edit the root/control worktree.** Work exclusively inside
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-13`.
- **Module-size cap.** No code file may exceed 400 lines (AGENTS.md, "Keep file
  size manageable"). The step module `tests/steps/torn_turn_rollback_steps.py`
  is currently 291 lines; the parametrization must keep it under 400.
- **Drive every command through the command entry path.** Both `check` and
  `reconcile` must be driven through
  `novel_ralph_skill.contract.runner.run` with a real `build_app()`, never by
  calling the body functions directly — the roadmap clause demands an end-to-end
  command-boundary proof (mirroring the existing 6.2.7 steps). The producer
  remains the real design §3.4 `pending_turn` bracket, not a hand-planted
  fixture field.
- **Semantic assertions, not snapshot-only.** Every behavioural claim is
  asserted directly (exit code, reconciliation action, discrepancy name, cleared
  record, log receipt, draft-byte integrity, no-file-removal). No new `.ambr`
  snapshot is introduced; this scenario family has none and must not gain one
  (AGENTS.md testing rules: no snapshot-only coverage for logic assertable
  directly).
- **en-GB Oxford spelling** (`-ize`/`-yse`/`-our`) in all prose, docstrings,
  comments, feature narrative, and the commit message (AGENTS.md).
- **Keep the existing `draft.md` proof passing.** The parametrization must not
  weaken or remove the `draft.md` trigger coverage; it runs as the first example
  row.

## Tolerances (exception triggers)

- **Scope:** if the change touches more than 3 files or adds more than ~120 net
  lines of test code, stop and escalate — this is a tight parametrization, not a
  rewrite.
- **Production drift:** if any file under `novel_ralph_skill/` must change, stop
  and escalate (violates the no-production-code constraint).
- **Mechanism surprise:** if the `done.flag` trigger does **not** classify as
  `ROLLBACK_PENDING_TURN` at the command boundary (e.g. it instead trips a
  refuse-class `done-flag-without-draft` contradiction, exit 4 with `REFUSE`, or
  any other disposition), stop and escalate with the observed envelope — the
  analysis in Decision D-DONEFLAG-CLEAN would be wrong.
- **Module-size:** if the parametrized step module would exceed ~380 lines, stop
  and escalate (the 400-line cap is near; an extraction may be warranted, but
  that is out of this task's scope and is tracked separately under step 7.23).
- **Iterations:** if `make all` still fails after 3 fix attempts, stop and
  escalate.
- **Ambiguity:** if `Scenario Outline` substitution into a `target_fixture`
  Given step behaves differently from the existing `tests/features/novel_done.feature`
  precedent, stop and present the two implementation options (Scenario Outline
  versus `pytest.mark.parametrize` on a single-row binder) with trade-offs.

## Risks

    - Risk: the unrecoverable `done.flag` declared path trips the refuse-class
      `done-flag-without-draft` contradiction instead of the ROLLBACK pending-turn
      path, changing the expected envelope.
      Severity: medium
      Likelihood: low
      Mitigation: verified — `_check_done_flag_without_draft`
      (novel_ralph_skill/state/disk_evidence.py:136-156) iterates the *manifest*
      chapters from state.toml and only fires when a `done.flag` file actually
      exists on disk beside an empty/absent draft. The declared chapter-99 is not
      in the COHERENT_BASELINE manifest and nothing lands, so no `done.flag` file
      exists and the contradiction cannot fire. The classifier keys ROLLBACK
      purely on the missing declared path's basename being outside
      {state.toml, log.md} (reconcile.py:190-206). Pinned by the scenario itself.

    - Risk: `Scenario Outline` placeholder substitution does not reach the
      `target_fixture` Given step's argument under pytest-bdd 8.1.
      Severity: low
      Likelihood: low
      Mitigation: the repo already uses this exact pattern —
      `tests/features/novel_done.feature:14-29` is a `Scenario Outline` whose
      `<clause>` placeholder is consumed by a Given step. pytest-bdd>=8.1.0 is the
      locked version (pyproject.toml). If substitution into the producer Given
      proves awkward, fall back to `pytest.mark.parametrize` on the scenario
      binder (Decision D-SHAPE records the fallback).

    - Risk: the parametrized step module breaches the 400-line cap.
      Severity: low
      Likelihood: low
      Mitigation: current size is 291 lines; the parametrization replaces hard-coded
      `_UNRECOVERABLE_DRAFT` references with a per-row value threaded through the
      `_Outcome` dataclass and the feature `Examples` table, adding well under 90
      lines. Measured in Stage D against `make all`.

## Progress

    - [x] Stage A: confirm the mechanism and the chosen scenario shape (no code).
      Verified `reconcile.py:89,190-206` keys ROLLBACK on basename outside
      `{state.toml, log.md}`; `disk_evidence.py:136-156` iterates manifest chapters
      and needs an on-disk `done.flag`, so the absent chapter-99 cannot pre-empt the
      ROLLBACK; `novel_done` steps bind their Outline placeholder via
      `parsers.parse('... "{clause}" ...')`, confirming the Scenario Outline idiom
      (D-SHAPE) reaches a step argument. Go on D-DONEFLAG-CLEAN and D-SHAPE.
    - [x] Stage B: add the failing `done.flag` example row (red). The feature is a
      `Scenario Outline` over `(trigger, declared_path, operation)`. Red proof
      captured: with the leftover-record assertion temporarily hard-coded to the
      draft path, the `done.flag` row failed at `torn_leaves_record`; restoring the
      per-row assertion turned both rows green.
    - [x] Stage C: generalize the step module to thread the declared path and
      operation per row (green). Both rows pass with distinct, readable test ids.
    - [x] Stage D: harden — module-size check (322 lines, under the 380/400 caps),
      docstring/narrative en-GB pass, `make all` green (981 passed, 1 skipped),
      `make markdownlint`, `make nixie`; committed.

## Surprises & discoveries

    - The `done.flag` row classified `rollback-pending-turn` at the command
      boundary exactly like the `draft.md` row, confirming D-DONEFLAG-CLEAN with no
      refuse-class pre-emption — no mechanism surprise, no escalation needed.
    - The parametrized step phrasings (placeholders now in the producer Given and
      the leftover-record Then) push the step text past the line-length limit; Ruff
      reformatted `torn_leaves_record`'s signature onto one line. The format pass is
      part of `make all` and dropped the module from 324 to 322 lines, still well
      under the 380/400 caps.
    - CodeRabbit round 1 raised two minor docs-style notes (first/second-person
      narration in the plan's Purpose and orientation prose and in the logisphere
      review file); both were rewritten in impersonal voice. The plan's Markdown
      also had to drop its indented-list/fenced-block mix to a single MD046 style:
      the five Bash command blocks were converted from fenced to indented to match
      the indented administrative lists markdownlint sees first.
    - CodeRabbit round 2 suggested adding `make fmt` to and removing `make nixie`
      from the Stage D gate list. Skipped as non-actionable: `make all` already
      runs `check-fmt` (the formatting gate; `fmt` only mutates), and the standing
      workflow rules explicitly require `make nixie` for any Markdown change, run
      repo-wide regardless of whether a given file carries a Mermaid diagram.
      Weakening the documented gate would contradict those rules.

## Decision log

    - Decision: Use a pytest-bdd `Scenario Outline` with an `Examples` table over
      `(declared_path, expected_basename, trigger_label)` as the primary shape,
      rather than `pytest.mark.parametrize` on the binder.
      Rationale: the audit's proposed fix names a `parametrize over
      (declared_path, expected_basename)`, but the repo already expresses
      table-driven behavioural cases as `Scenario Outline` in
      tests/features/novel_done.feature, keeping the behavioural narrative in the
      feature file where a reviewer reads it. Both are valid; the Scenario Outline
      is the house idiom for this suite. Tag: D-SHAPE. Fallback to binder-level
      `parametrize` is retained if Outline substitution into the producer Given is
      awkward (see Risks).
      Date/Author: 2026-06-25, planning agent.

    - Decision: The `done.flag` trigger classifies a clean ROLLBACK at the command
      boundary, not a refuse-class contradiction.
      Rationale: `_classify_pending_turn` (reconcile.py:190-206) keys ROLLBACK on
      the missing declared path's basename being outside {state.toml, log.md}; a
      declared `working/manuscript/chapter-99/done.flag` that never lands has
      basename `done.flag`, so it is unrecoverable → ROLLBACK, symmetric with the
      `draft.md` case. The refuse-class `done-flag-without-draft` check
      (disk_evidence.py:136-156) needs an actual on-disk `done.flag` beside an
      empty/absent draft *for a manifest chapter*; chapter-99 is absent from the
      COHERENT_BASELINE manifest and nothing lands, so it cannot fire. Tag:
      D-DONEFLAG-CLEAN.
      Date/Author: 2026-06-25, planning agent.

    - Decision: Keep the step helpers self-contained in the rollback step module
      (do not consolidate with torn_turn_recovery_steps.py here).
      Rationale: the shared-scaffolding consolidation is owned by roadmap task
      7.23.3 (audit-6.2.7.md Finding 1 widened its scope to name this module).
      Pre-empting it here would expand scope and conflict with the tracked
      consolidation. Tag: D-DUP (inherited from the 6.2.7 ExecPlan).
      Date/Author: 2026-06-25, planning agent.

    - Decision: Hand-pick the unrecoverable `done.flag` declared path rather than
      import a corpus constant.
      Rationale: the corpus does not yet expose the ROLLBACK-triggering
      unrecoverable basenames; that exposure is owned by roadmap task 7.23.4
      (audit-6.2.7.md Finding 4). The existing scenario hand-picks
      `chapter-99/draft.md`; the `done.flag` row mirrors it with
      `chapter-99/done.flag`. Tag: D-LITERAL (inherited).
      Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

    - **Delivered:** `tests/features/torn_turn_rollback.feature` is now a
      `Scenario Outline` with two `Examples` rows (`draft.md`/`write-draft`,
      `done.flag`/`mark-done`); `tests/steps/torn_turn_rollback_steps.py` threads
      the per-row declared path and operation through the producer Given, the
      `_Outcome` dataclass, and the leftover-record Then; the binder docstring names
      both triggers. Both rows drive `check` (exit 4, `rollback-pending-turn`,
      `pending-turn-cleared`) and `reconcile` (exit 0, record cleared,
      `rollback-pending-turn:` receipt) through
      `novel_ralph_skill.contract.runner.run`, with a clean follow-up `check`,
      byte-identical drafts, and no `working/` file removed.
    - **Scope honoured:** only `tests/` and `docs/execplans/` changed; no production
      code under `novel_ralph_skill/` was touched. Net test-code growth and file
      count stayed inside the Tolerances. The disposition/integrity Then steps were
      left unchanged — both triggers share the identical envelope, which is the
      symmetry the task pins.
    - **Gates:** `make all` green (981 passed, 1 skipped); `make markdownlint` and
      `make nixie` green for the ExecPlan change. Module size 322 lines.

## Context and orientation

This section orients a complete newcomer to the repository.

The repository implements a deterministic harness for the novel-ralph skill. A
`working/` directory holds a `state.toml` (the manifest and per-chapter record),
a `log.md` audit trail, and a `manuscript/chapter-NN/` tree of `draft.md`,
`done.flag`, and plan artefacts. Five console-script commands operate on this
tree; the two relevant here are:

- `check` — read-only; reports drift and exits 4 (`ACTIONABLE_FINDING`) when it
  finds an actionable discrepancy.
- `reconcile` — the mutator that enacts the reconciliation `check` reports.

A **torn turn** is a multi-file mutation that died mid-write. The design §3.4
`pending_turn` context manager
(`novel_ralph_skill/state/document.py:223-267`) brackets such a mutation: it
writes a `[pending_turn]` intent record to `state.toml` *before* yielding, and
clears it only on clean exit. If the body raises, the populated record is left on
disk — the signature of a torn turn. The record names the `operation` in flight
and the `paths` it intended to write.

The **reconciliation derivation** `derive_reconciliation`
(`novel_ralph_skill/state/reconcile.py`) is the one pure function both `check`
and `reconcile` call. For an uncleared `[pending_turn]`, the private
`_classify_pending_turn` (`reconcile.py:177-216`) decides the disposition:

- Every *missing* declared path is recomputable (basename in `{state.toml,
  log.md}`, the frozenset `_RECOMPUTABLE_BASENAMES` at `reconcile.py:89`) →
  `COMPLETE_PENDING_TURN` (the dispatch re-derives the artefacts and clears the
  record).
- Any missing declared path is unrecoverable (basename **not** in that set — a
  `draft.md` body or a `done.flag`) → `ROLLBACK_PENDING_TURN`: the record is
  cleared, the partial artefacts that did land are left in place, nothing is
  fabricated (design §5.4 item 2).

The **existing 6.2.7 behavioural proof** (the work this task extends) lives in
three files:

- `tests/features/torn_turn_rollback.feature` — a single `Scenario` whose
  narrative declares an unrecoverable `draft.md` that never lands.
- `tests/steps/torn_turn_rollback_steps.py` — the step definitions; the producer
  Given `torn_rollback_tree` enters a real `pending_turn` bracket over
  `wc.COHERENT_BASELINE` declaring `_UNRECOVERABLE_DRAFT =
  "working/manuscript/chapter-99/draft.md"` (line 69) and raises a `_TornError`,
  leaving the populated record. Subsequent steps drive `check` and `reconcile`
  through `novel_ralph_skill.contract.runner.run` and assert the disposition,
  the cleared record, the log receipt, draft-byte integrity, and no file
  removal.
- `tests/test_torn_turn_rollback_bdd.py` — the binder; star-imports the step
  module and calls `scenarios("features/torn_turn_rollback.feature")`.

The **gap this task closes** is `docs/issues/audit-6.2.7.md` Finding 3: the
command-boundary ROLLBACK proof exercises only the `draft.md` trigger; the
`done.flag` trigger remains in-process-only. The audit's proposed fix (lines
125-131) is a parametrization over `(declared_path, expected_basename)` covering
both triggers with one step module.

The **corpus** (`tests/working_corpus/`) provides `COHERENT_BASELINE` (a
canonical mid-drafting coherent tree) and `build_working_tree(spec, dest)`.
`COHERENT_BASELINE` materializes chapters 1..N; chapter-99 is deliberately
outside its manifest so the declared artefact never lands and carries no manifest
entry — the precondition that keeps the disposition a clean ROLLBACK
(Decision D-DONEFLAG-CLEAN).

## Plan of work

The work is a single behavioural extension expressed as one `Scenario Outline`
with two example rows. It is one atomic, committable, gate-passable change — the
task is small and the three files are tightly coupled (feature narrative, steps,
binder), so splitting them across commits would leave intermediate red states
with no independent value. The Stages below are go/no-go checkpoints within the
single commit, not separate commits.

### Stage A: confirm the mechanism (no code changes)

Read and confirm against source before touching anything:

- `novel_ralph_skill/state/reconcile.py:85-89` and `:177-216` — confirm
  `done.flag` is an unrecoverable trigger keyed on basename.
- `novel_ralph_skill/state/disk_evidence.py:136-156` — confirm
  `_check_done_flag_without_draft` cannot fire for an absent chapter (no on-disk
  flag), so no refuse-class pre-emption.
- `tests/features/novel_done.feature:14-29` — confirm the repo's `Scenario
  Outline` / `Examples` idiom and placeholder substitution into a Given step.

Go/no-go: if any of these contradicts D-DONEFLAG-CLEAN or D-SHAPE, stop and
escalate before writing tests.

### Stage B: add the failing `done.flag` row (red)

1. Convert the single `Scenario` in
   `tests/features/torn_turn_rollback.feature` into a
   `Scenario Outline`. Generalize the narrative to "an unrecoverable artefact (a
   `draft.md` or a `done.flag`) that never lands", parametrize the producer Given
   and the leftover-record Then on a `<declared_path>` placeholder and the
   leftover-operation step on an `<operation>` placeholder, and add an `Examples:`
   table with two rows: the existing `draft.md`/`write-draft` row first, then the
   new `done.flag`/`mark-done` (or the operation the design uses for flag-writing;
   confirm against the producer — `operation` is a free string the classifier
   does not branch on, so any honest verb is fine, but keep it faithful to a
   real flag-writing turn). Keep one column for a human-readable `<trigger>`
   label used only in the scenario title for a readable test id.
2. Run only the new row and confirm it **fails** before the step generalization
   lands (the steps still hard-code `_UNRECOVERABLE_DRAFT`, so the `done.flag`
   row's leftover-path assertion at `torn_leaves_record` will mismatch). This is
   the red proof that the new row exercises new ground, per the execplans
   red-green-refactor rule.

Command (run from the worktree root):

    make build && uv run pytest tests/test_torn_turn_rollback_bdd.py -k "done" -x

Expect: a failure in `torn_leaves_record` (declared-path assertion) for the
`done.flag` row, while the `draft.md` row still passes.

### Stage C: generalize the step module (green)

In `tests/steps/torn_turn_rollback_steps.py`:

1. Thread the declared path through the producer Given. Replace the module-level
   `_UNRECOVERABLE_DRAFT` constant usage inside `torn_rollback_tree` with the
   `<declared_path>` value pytest-bdd injects from the `Examples` row (an
   Outline placeholder is available to the step as a string argument; bind it via
   the step's parsed argument, mirroring `novel_done` steps). Store the declared
   path (and its expected basename) on the `_Outcome` dataclass so later Then
   steps assert against the per-row value, not a constant.
2. Generalize `torn_leaves_record` (currently asserts `== (_UNRECOVERABLE_DRAFT,)`
   at line 196) to assert the leftover record's `paths` equals the per-row
   declared path, and assert the leftover record's `operation` equals the per-row
   `<operation>`.
3. Leave the disposition assertions (`check_reports_rollback`,
   `reconcile_clears_and_logs`, `follow_up_check_clean`,
   `rollback_preserves_files`) unchanged — both triggers share the identical
   `rollback-pending-turn` envelope, cleared record, receipt, and integrity
   guarantees, which is precisely the symmetry the task proves. Add no new
   assertions to `rollback_preserves_files` (the landed-partial-preservation half
   is roadmap task 6.2.12's job, not this one).
4. Update the module docstring and the binder docstring to describe both triggers
   (en-GB Oxford spelling), and keep the D-DUP self-contained-helpers rationale.

Command:

    make build && uv run pytest tests/test_torn_turn_rollback_bdd.py -v

Expect: both example rows pass; the test ids name the `draft.md` and `done.flag`
triggers distinctly.

### Stage D: harden, document, gate

1. Confirm `tests/steps/torn_turn_rollback_steps.py` stays under 400 lines
   (`wc -l`). If it approaches ~380, stop and escalate per Tolerances.
2. en-GB Oxford-spelling pass over the feature narrative, step docstrings, and
   binder docstring.
3. Run the full gate (below). Commit once green.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-13`.

1. Stage A reading (no commands beyond `leta show`/`leta refs` for navigation).
2. Stage B: edit the feature file; run the red check:

        make build && uv run pytest tests/test_torn_turn_rollback_bdd.py -k "done" -x

   Expect a single failing assertion in the leftover-record step.
3. Stage C: edit the step module and binder; run:

        make build && uv run pytest tests/test_torn_turn_rollback_bdd.py -v

   Expect both rows green.
4. Stage D: size check and full gate:

        wc -l tests/steps/torn_turn_rollback_steps.py
        make all
        make markdownlint
        make nixie

   `make all` runs `build check-fmt lint typecheck test` (Makefile line 28).
   `make markdownlint` and `make nixie` cover the Markdown change to this
   ExecPlan and any feature-file prose review (the feature file is not Markdown,
   but the ExecPlan is — markdownlint/nixie are required because this plan file
   is added/edited under `docs/`).
5. Commit with an en-GB Oxford-spelling message referencing roadmap task 6.2.13
   and `docs/issues/audit-6.2.7.md` Finding 3.

## Validation and acceptance

Acceptance is behavioural:

- **New coverage:** `uv run pytest tests/test_torn_turn_rollback_bdd.py -v`
  reports **two** passing scenario rows — one for the `draft.md` trigger, one for
  the `done.flag` trigger — each driving `check` (exit 4,
  `rollback-pending-turn`, `pending-turn-cleared` discrepancy) and `reconcile`
  (exit 0, record cleared, `rollback-pending-turn:` receipt in `log.md`) through
  `novel_ralph_skill.contract.runner.run`, with a follow-up `check` clean (exit
  0), the author-owned drafts byte-for-byte identical, and no `working/` file
  removed.
- **Red-before-green evidence:** the `done.flag` row fails at the leftover-record
  step before the step generalization lands (Stage B) and passes after (Stage C).

Quality criteria (what "done" means):

- Tests: `make test` passes (includes the two new rows). No production test
  regresses.
- Lint/typecheck: `make all` passes (`build check-fmt lint typecheck test`).
- Markdown: `make markdownlint` and `make nixie` pass for the ExecPlan change.
- Module size: `tests/steps/torn_turn_rollback_steps.py` < 400 lines.
- No production code under `novel_ralph_skill/` changed (`git diff --stat`
  shows only `tests/` and `docs/execplans/`).

Quality method:

- Run `make all`, then `make markdownlint`, then `make nixie` sequentially (never
  in parallel — the environment relies on build caching; AGENTS.md / global
  instructions).

## Idempotence and recovery

The change is purely additive test code plus this ExecPlan; re-running the gate
is safe and side-effect-free. If a step fails, the worktree is unchanged outside
`tests/` and `docs/execplans/`; revert the working tree with `git restore` and
retry. No destructive operations are involved.

## Artefacts and notes

The load-bearing production behaviour, pinned by reading source (not from
memory):

- `novel_ralph_skill/state/reconcile.py:89` —
  `_RECOMPUTABLE_BASENAMES = frozenset({"state.toml", "log.md"})`; any other
  missing basename (a `draft.md` body, a `done.flag`) is unrecoverable.
- `novel_ralph_skill/state/reconcile.py:190-206` — `_classify_pending_turn`
  selects `ROLLBACK_PENDING_TURN` when any missing declared path's
  `PurePosixPath(path).name` is outside `_RECOMPUTABLE_BASENAMES`.
- `novel_ralph_skill/state/disk_evidence.py:136-156` —
  `_check_done_flag_without_draft` fires only for a *manifest* chapter with an
  on-disk `done.flag` beside an empty/absent draft; an absent chapter-99 cannot
  trip it.
- `novel_ralph_skill/state/document.py:223-267` — the §3.4 `pending_turn`
  producer that leaves a populated record on an in-bracket raise.

## Interfaces and dependencies

No new production symbols, no new dependencies, no external-library behaviour is
relied upon beyond the already-locked test stack:

- `pytest-bdd>=8.1.0` (pyproject.toml) — `Scenario Outline` with an `Examples`
  table and `<placeholder>` substitution into step arguments, already used in
  `tests/features/novel_done.feature:14-29`.
- `pytest` parametrization — the binder-level fallback if Outline substitution
  into the producer Given proves awkward (Decision D-SHAPE).

No `cuprum` API is used anywhere in this task: the commands are driven through
`novel_ralph_skill.contract.runner.run(build_app(), argv, RunContext(...))`, the
in-process command boundary, exactly as the existing 6.2.7 steps do. The
installed-binary boundary (which is where cuprum's catalogue/allowlist surface
would matter) is out of scope here — this task proves the in-process command
boundary, matching its 6.2.7 sibling.

At the end of this task the following test artefacts exist:

- `tests/features/torn_turn_rollback.feature` — one `Scenario Outline` with two
  `Examples` rows (`draft.md`, `done.flag`).
- `tests/steps/torn_turn_rollback_steps.py` — the producer Given and
  leftover-record Then parametrized on the per-row declared path and operation;
  the disposition/integrity Then steps unchanged.
- `tests/test_torn_turn_rollback_bdd.py` — binder docstring updated to name both
  triggers.

## Documentation and skills signposting (per work item)

Stage A (mechanism confirmation):

- Read: `docs/novel-ralph-harness-design.md` §3.4 (the `pending_turn` bracket and
  torn-turn recovery) and §5.4 (the COMPLETE/ROLLBACK dispositions, item 2
  "rolling back removes nothing, fabricates nothing"); `docs/issues/audit-6.2.7.md`
  (Findings 3 and 4); `novel_ralph_skill/state/reconcile.py`,
  `disk_evidence.py`, `document.py` (cited line ranges above).
- Skills: load `leta` for navigation (`leta show`/`leta refs` over
  `_classify_pending_turn`, `_check_done_flag_without_draft`, `pending_turn`).
  Load `python-router`; it routes to `python-testing` for pytest-bdd step and
  fixture discipline.

Stage B–C (scenario + steps):

- Read: `tests/features/novel_done.feature` (the `Scenario Outline` idiom),
  `tests/steps/torn_turn_rollback_steps.py` and
  `tests/steps/torn_turn_recovery_steps.py` (the sibling COMPLETE proof's shape),
  `docs/developers-guide.md` ("Shared test scaffolding" — why the helpers stay
  self-contained pending task 7.23.3), `docs/scripting-standards.md` (test prose
  and en-GB conventions), AGENTS.md (snapshot-pairing rule, 400-line cap, en-GB
  Oxford spelling).
- Skills: `python-router` → `python-testing`. `en-gb-oxendict` for the prose and
  docstrings.

Verification adversaries (Hypothesis / CrossHair / mutmut):

- **Not applicable and not added.** This task adds one behavioural scenario over
  a fixed, deterministic torn-turn producer; there is no new production logic, no
  numeric/algebraic surface, and no example-poverty to attack. Per AGENTS.md,
  property and mutation tools are warranted when a change *introduces non-trivial
  logic*; this change introduces none. If, contrary to the no-production-code
  constraint, the implementer is forced to touch `_classify_pending_turn`, that
  is a tolerance breach — stop and escalate; only then would `python-verification`
  routing to `hypothesis`/`crosshair`/`mutmut` come into play.

## Tests this task adds or updates (per AGENTS.md testing rules)

- **Behavioural (pytest-bdd):** the `done.flag` example row in the
  `Scenario Outline` of `tests/features/torn_turn_rollback.feature`, bound through
  `tests/test_torn_turn_rollback_bdd.py`. This is the sole new test; it is a
  behavioural proof, not a unit test, because it drives real commands end-to-end
  through the runner.
- **Updated:** the existing `draft.md` scenario becomes the first row of the
  Outline (behaviour preserved, now parametrized).
- **Unit / property / snapshot / e2e:** none added. The pure classifier already
  has its in-process test (the coverage this task lifts to the command boundary);
  no snapshot is introduced (semantic assertions only); no installed-binary e2e
  is in scope (the in-process command boundary is the target, matching 6.2.7).

## Revision note

Initial draft (2026-06-25). First planning round for roadmap task 6.2.13.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge audit of step 6.2 (`audit:6.2.12`). Execute each as a small addendum
pass — no plan or design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial
follow-up raised alongside this — the partial-landed `done.flag` ROLLBACK
scenario, which advances the step-6.2 surface hypothesis — was re-routed to a new
roadmap task 6.2.14 (it warrants its own plan and review); the one below is the
small docs gap.

- [x] 6.2.13.1 — Refresh the developers' guide torn-turn behavioural-scenario note
  to enumerate the complete scenario family (from audit:6.2.12, low). The guide
  names only the first torn-turn scenario, but after 6.2.7, 6.2.12, and 6.2.13
  the suite covers the COMPLETE, never-landed-ROLLBACK, and
  partial-landed-ROLLBACK halves of the §5.4 reconciliation surface; enumerate
  the full scenario family so the developer documentation map stays current.
  Gate with `make markdownlint` and `make nixie`.
