# Post-merge audit: roadmap task 6.2.13

Audit of the codebase after roadmap task 6.2.13 ("Add a command-boundary
ROLLBACK scenario for an unrecoverable `done.flag`", commit `694f2e5`) merged to
`main`. The task is test-and-docs only: it generalizes the existing
`tests/features/torn_turn_rollback.feature` into a `Scenario Outline` over
`(trigger, declared_path, operation)` with two `Examples` rows — the pre-existing
`draft.md`/`write-draft` row and a new `done.flag`/`mark-done` row — and threads
the declared path and operation per row through the producer `Given`, the
`_Outcome` dataclass, and the leftover-record `Then`. The disposition and
integrity steps are unchanged because both triggers share the identical
`rollback-pending-turn` envelope, cleared record, receipt, and draft-byte
integrity. The diff touches `tests/features/torn_turn_rollback.feature`,
`tests/steps/torn_turn_rollback_steps.py`, `tests/test_torn_turn_rollback_bdd.py`,
the ExecPlan, its Logisphere review, and ticks `docs/roadmap.md`.

The change is correct and faithful to its plan. It directly closes
`docs/issues/audit-6.2.7.md` Finding 3, which recorded the `done.flag` ROLLBACK
trigger as covered only by the in-process classifier test, never end-to-end
through the command boundary. The constraint "no production code changes" held —
verified: the commit touches no file under `novel_ralph_skill/`, because the
`done.flag` trigger already existed in `_classify_pending_turn` and was correct.
The new `Examples` row is a faithful sibling of the `draft.md` row: both declare
a `chapter-99` artefact the coherent baseline never materializes, both carry a
basename outside `{state.toml, log.md}`, and both therefore classify
`ROLLBACK_PENDING_TURN` through the production `_RECOMPUTABLE_BASENAMES` rule. The
feature narrative, step docstrings, and binder docstring all check out against
the design (§3.4 the `pending_turn` bracket, §5.4 item 2 "Rolling back removes
nothing"), the scenario pairs every assertion with semantic checks (no
snapshot-only coverage, per AGENTS.md), and the prose is en-GB Oxford-spelling
clean.

No finding below is a defect in 6.2.13's diff. The findings are pre-existing
hygiene observations in the reconcile-family code and test territory the change
extends or surfaces while reading the torn-turn behavioural-test family. Two of
them (Findings 1 and 2) are carried duplication themes already filed under
roadmap tasks 7.23.3 and the audit record; the third (Finding 3) is a known
finding (audit-2.3.2 Finding 2) whose proposed `to_payload()` consolidation was
never promoted to a roadmap task and remains untracked.

Sources relied on: `docs/issues/audit-6.2.7.md` (Finding 3, the `done.flag`
command-boundary gap this task closes; Finding 1, the reconcile-family driver
duplication theme); `docs/issues/audit-6.2.12.md` (the partial-landed ROLLBACK
sibling and audit format); `docs/issues/audit-2.3.2.md` (Finding 2, the
`{action, discrepancies, detail}` payload duplication); `docs/roadmap.md` (task
6.2.13 statement; tasks 7.14.1, 7.23.3, 7.23.4 tracking the carried themes);
`docs/developers-guide.md` ("Shared test scaffolding"); `docs/adr-001-...md` (the
detect/adjudicate boundary the read/write split serves);
`docs/novel-ralph-harness-design.md` (§3.4 the `pending_turn` bracket, §5.4 item
2 the rollback-removes-nothing rule); and `AGENTS.md` (snapshot-pairing, the
400-line module cap, command/query segregation, en-GB Oxford spelling). Code
navigated with `leta`; the 6.2.13 change set traced with `git show` over commit
`694f2e5`. Skills consulted: `python-router`, which routed to `python-testing`
(pytest-bdd `Scenario Outline` discipline) for the test-scaffolding findings;
`leta` and `sem` for navigation and history.

## Finding 1: The torn-turn ROLLBACK step module still carries the four-way reconcile-family driver duplication

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/torn_turn_rollback_steps.py:100-143` (`_draft_bytes`,
  `_present_files`, `_run`, `_run_capturing`), duplicating the byte-identical
  helpers in `tests/steps/torn_turn_recovery_steps.py`,
  `tests/steps/torn_turn_rollback_partial_steps.py`, and (for the runner helpers)
  `tests/steps/per_chapter_loop_steps.py`.

Task 6.2.13 extends the module that already carries the third copy of the
reconcile-family command-driving helpers rather than adding a fourth file, so it
does **not** widen the copy count — a deliberate and correct choice. But the
helpers it now leans on more heavily (`_run`, `_run_capturing`, `_present_files`,
`_draft_bytes`) remain duplicated across the torn-turn family. The module
docstring (lines 41-43) cites "ExecPlan Decision D-DUP" to justify keeping them
self-contained, while `docs/developers-guide.md` ("Shared test scaffolding") is
explicit that new shared scaffolding belongs in a registered plugin or
`conftest.py` rather than a fresh copy in each module. This is the same theme
`docs/issues/audit-6.2.7.md` Finding 1 and `docs/issues/audit-6.2.12.md`
Finding 1 already record.

Roadmap task 7.23.3 owns this consolidation, but its named Requires/Success scope
(roadmap lines 3085-3108) still lists only `torn_turn_recovery_steps.py`,
`reconcile_steps.py`, and `test_reconcile_integration.py` — it names neither
`torn_turn_rollback_steps.py` (now a load-bearing consumer after 6.2.13) nor
`torn_turn_rollback_partial_steps.py`. So the tracked consolidation's site list
has drifted two modules behind the duplication it is meant to collapse, exactly
as audit-6.2.7 Finding 1 first observed for the rollback module.

- **Proposed fix:** No new consolidation work — task 7.23.3 owns the
  `drive()` / `present_files` / `draft_bytes` registered-plugin home. Widen
  7.23.3's Requires/Success scope to name `tests/steps/torn_turn_rollback_steps.py`
  and `tests/steps/torn_turn_rollback_partial_steps.py` as further delegating
  sites (both share the `_run`/`_run_capturing`/`_present_files`/`_draft_bytes`
  helpers, though not the `crash_after_recovery_receipt()` seam — their producer
  is the §3.4 `pending_turn` bracket, not the `_append_recovery_entry`
  monkeypatch). Recording this so the root agent can extend 7.23.3 rather than
  letting the copy count and the task's site list drift further apart.

## Finding 2: The reconciliation `{action, discrepancies, detail}` payload is still hand-built in four places, untracked by the roadmap

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel_state.py:169-177`
  (`_render_reconciliation`, the `check` read shape);
  `novel_ralph_skill/commands/_reconcile.py:195-202` (`_write_outcome`, the
  write shape), `:221-226` (`_refuse_outcome`), and `:267-272` (the `NONE` branch
  of `reconcile`).

Four sites independently serialize a `Reconciliation` into the same base dict —
`{"action": str(...), "discrepancies": list(...), "detail": ...}` — three of them
appending the `current`/`by_chapter` pair guarded by `recounted_by_chapter is not
None`. `_render_reconciliation` and `_write_outcome` are body-identical;
`_refuse_outcome` repeats the three-key base; the `NONE` arm inlines it with an
empty discrepancy list. The slice deliberately keeps the read-shape and
write-shape *vocabulary* distinct (audit-2.2.2 Finding 2, the command/query
segregation guard), but the *serialization* of a `Reconciliation` into the base
dict is one concern duplicated across two modules. A future field on the reported
reconciliation, or a rename of `discrepancies`, is shotgun surgery across four
sites, and a partial edit would let `check` and `reconcile` report different
shapes for the same derivation — the very divergence the shared
`derive_reconciliation` (D-SHARED) exists to prevent.

This was recorded as `docs/issues/audit-2.3.2.md` Finding 2 but, unlike the
sibling `[word_counts]`-write theme (roadmap task 7.14.1) and the compile
projection theme (task 7.19), it was never promoted to a roadmap task. A
`grep` of `docs/roadmap.md` finds no item owning the reconciliation-payload
projection, so this remains an open, untracked duplication. The 6.2.13 scenario
exercises the `check` read-shape arm (`reconciliation["action"]`,
`["discrepancies"]`) directly, which is what surfaced it on this read.

- **Proposed fix:** Give `Reconciliation` a single payload projection beside its
  data shape in `novel_ralph_skill/state/reconcile.py` (e.g. a `to_payload()`
  method or a free `reconciliation_payload(reconciliation)` function) returning
  the base `{action, discrepancies, detail}` dict plus the optional recount pair,
  and route all four sites through it. The read/write *envelope code* and *exit
  codes* stay where they are (those genuinely differ; the CQS read/write
  vocabulary split is preserved); only the `Reconciliation`-to-dict serialization
  is centralized, so `check` and `reconcile` cannot drift on payload shape. This
  mirrors the canonical-projection pattern roadmap task 7.1.5 establishes for
  `RuleFinding`/`LineHit` and task 7.19 for the compile projection. Worth a new
  roadmap item under step 7 (the consolidation hypothesis) so the audit-2.3.2
  finding stops being orphaned.

## Finding 3: The developers' guide torn-turn scenario map does not name the `done.flag` ROLLBACK row

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/developers-guide.md` (the torn-turn behavioural-scenario
  note that `docs/issues/audit-6.2.12.md` Finding 2 already flagged as trailing
  the scenario family).

`docs/issues/audit-6.2.12.md` Finding 2 proposed extending the developers' guide
torn-turn note to name the scenario family and the distinct guarantee each pins
(COMPLETE recovery, never-landed ROLLBACK, partial-landed ROLLBACK). Task 6.2.13
adds a further dimension to that map: the never-landed ROLLBACK scenario now
proves **both** unrecoverable triggers — a missing `draft.md` body and a missing
`done.flag` — at the command boundary, where before only `draft.md` was proven
end-to-end. A reader following the guide to the command-boundary torn-turn
coverage would not discover that the `done.flag` half of the
`_RECOMPUTABLE_BASENAMES`-exclusion rule (`reconcile.py:88-89`) now has a
behavioural proof. This is not a defect in 6.2.13's diff — the feature file and
ExecPlan document the new row thoroughly — but the guide's torn-turn map (already
behind per audit-6.2.12) has fallen one example row further behind.

- **Proposed fix:** Fold into the audit-6.2.12 Finding 2 documentation update:
  when the developers' guide torn-turn note is extended to name the scenario
  family, also record that the never-landed ROLLBACK scenario is a `Scenario
  Outline` proving both unrecoverable triggers (`draft.md` and `done.flag`) at the
  command boundary, so the guide reflects that both branches of the
  `{state.toml, log.md}`-exclusion rule are behaviourally covered. A short clause
  with the two `Examples` rows suffices; no behavioural change.
