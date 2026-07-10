# Post-merge audit: roadmap task 6.2.12

Audit of the codebase after roadmap task 6.2.12 ("Add a command-boundary
ROLLBACK scenario where the unrecoverable artefact partially landed", commit
`4969177`) merged to `main`. The task is test-and-docs only: it adds a
behavioural (`pytest-bdd`) scenario proving the *partial-landed* half of the
design §5.4 rollback surface — a torn `write-draft` turn that left a partial
`.tmp` residue on disk is detected by `check` (exit `4`,
`rollback-pending-turn`) and rolled back by `reconcile` (exit `0`), with the
residue preserved byte-for-byte and unreferenced by state. The diff adds
`tests/features/torn_turn_rollback_partial.feature`,
`tests/steps/torn_turn_rollback_partial_steps.py`, the binder
`tests/test_torn_turn_rollback_partial_bdd.py`, and ticks the roadmap plus its
ExecPlan.

The change is correct and faithful to its plan. The constraint "no production
code changes" held — verified: the commit touches no file under
`novel_ralph_skill/`. The new scenario mirrors the established never-landed
ROLLBACK sibling (6.2.7), drives recovery through the shared command runner
rather than the bracket primitive, and produces the torn record through the
real §3.4 `pending_turn` producer. The feature's `Given`/`Then`/`When`
ordering (asserting the producer precondition before driving `check`) matches
the sibling `tests/features/torn_turn_rollback.feature`, so it is a deliberate
house pattern, not a Gherkin regression. No finding below is a defect in
6.2.12's diff; the findings are pre-existing hygiene observations that 6.2.12
extends or surfaces while reading the torn-turn behavioural-test family.

Sources relied on: `docs/execplans/roadmap-6-2-12.md` (the task's plan, its
`Decision Log D-DUP` deferring helper extraction, and `D-MECH`/`D-PARTIAL`);
`docs/roadmap.md` (task 6.2.12 statement at lines 1578-1596, and the deferred
shared-scaffolding tasks 7.23 / 7.23.3 at lines 1533, 3085, 3123, 3171);
`docs/issues/audit-6.2.10.md` and `docs/issues/audit-6.1.1.md` (the prior
duplication-by-copy-paste theme); `docs/developers-guide.md` (§"Shared test
scaffolding"; the torn-turn behavioural-scenario note at lines 824-827);
`docs/novel-ralph-harness-design.md` (§3.4 atomic writes and the `[pending_turn]`
producer, §5.4 item 2 the leaves-partial-artefacts-in-place guarantee);
`docs/scripting-standards.md` (§"Reading / writing files and atomic updates");
and `AGENTS.md` (en-GB Oxford spelling, the single-source-of-truth stance).
Code navigated with `leta`; history traced with `sem` / `git show` over commit
`4969177`. Skills consulted: `leta`, `sem`, `python-router` (routing the BDD
step-module review).

## Finding 1: Torn-turn BDD command-driver helpers are now duplicated four ways

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/torn_turn_rollback_partial_steps.py:106-150`
  (`_draft_bytes`, `_present_files`, `_run`, `_run_capturing`), duplicating
  `tests/steps/torn_turn_rollback_steps.py:89-133`,
  `tests/steps/torn_turn_recovery_steps.py:89-133`, and (for the runner
  helpers) `tests/steps/per_chapter_loop_steps.py`.

Task 6.2.12 adds a third byte-identical copy of the reconcile-family
command-driving helpers. Verified by hashing the helper bodies (comments and
docstrings stripped):

- `_run` and `_run_capturing` are **byte-identical** across
  `torn_turn_rollback_partial_steps.py`, `torn_turn_recovery_steps.py`, and
  `torn_turn_rollback_steps.py` (a fourth, slightly divergent copy of
  `_run_capturing` lives in `per_chapter_loop_steps.py`).
- `_present_files` is **byte-identical** across the same three torn-turn
  modules.
- `_draft_bytes` differs only in its docstring across the three torn-turn
  modules; the bodies are the same `rglob("draft.md")` map.

Each helper is a few lines, but the duplication is now load-bearing: a change
to the command-boundary driving idiom (the `monkeypatch.chdir`,
`redirect_stdout`, `pytest.raises(SystemExit)` envelope-parsing dance) must be
applied in three or four places to stay consistent, and a divergence between
copies would silently weaken one suite's command-boundary proof. This is the
same copy-paste theme `docs/issues/audit-6.1.1.md` and `audit-6.2.10.md`
already record for the command and state layers.

The 6.2.12 plan acknowledges this (Decision `D-DUP`): it keeps the new steps
self-contained because "the 6.2.5 and 6.2.7 plans made the same call", the
helpers are small, and a shared reconcile-family command driver is "already
filed as roadmap task 7.23.3". That is a defensible per-task choice — premature
extraction couples the suites — but the deferral is now exercised a third time,
so the consolidation is overdue rather than speculative.

- **Proposed fix:** Land roadmap task 7.23.3 (and the parent 7.23): extract the
  shared reconcile-family command driver — `_run`, `_run_capturing`,
  `_present_files`, `_draft_bytes` — into a single test-support module under
  `tests/` (e.g. `tests/_reconcile_bdd_support.py`), imported by all three
  torn-turn step modules and, where the runner helper matches, the per-chapter
  loop steps. Keep each module's scenario-specific assertions and residue
  capture local. This removes the four-way `_run_capturing` and three-way
  `_present_files` / `_draft_bytes` duplication without coupling the distinct
  residue-preservation facts each suite proves. No production change is
  involved; this is test-support consolidation only.

## Finding 2: Developers' guide does not name the rollback torn-turn scenarios

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/developers-guide.md:824-827` (the torn-turn
  behavioural-scenario note).

The developers' guide describes the torn-turn behavioural coverage generically:
"The torn-turn recovery flow is covered by the suite's first `pytest-bdd`
behavioural scenario (`tests/features/torn_turn.feature` with steps under
`tests/steps/`)". The suite now carries a *family* of torn-turn scenarios —
the COMPLETE recovery (`torn_turn_recovery`), the never-landed ROLLBACK
(`torn_turn_rollback`, task 6.2.7), and now the partial-landed ROLLBACK
(`torn_turn_rollback_partial`, task 6.2.12) — each pinning a distinct half of
the design §5.4 reconciliation surface (COMPLETE vs ROLLBACK; never-landed vs
partial-landed residue preservation). A reader following the guide to the
command-boundary torn-turn coverage finds only the first scenario named and
would not discover that the partial-residue preservation guarantee (§5.4 item
2) is now proven at the command boundary.

This is not a defect in 6.2.12's diff — the task's ExecPlan documents the new
scenario thoroughly, and the guide's generic note remains true — but the
guide's torn-turn map has fallen behind the scenario family it summarizes.

- **Proposed fix:** Extend the `docs/developers-guide.md:824-827` note to name
  the torn-turn scenario family and the distinct guarantee each pins: the
  COMPLETE recovery, the never-landed ROLLBACK (6.2.7), and the partial-landed
  ROLLBACK (6.2.12) that proves the §5.4 item 2 "leaves the partial artefacts
  in place, unreferenced by state" guarantee at the command boundary. A
  one-sentence enumeration with the feature-file names suffices; no behavioural
  change. This fits naturally alongside the consolidation in Finding 1 (when
  the shared driver lands, document it and the scenario family it serves
  together).
