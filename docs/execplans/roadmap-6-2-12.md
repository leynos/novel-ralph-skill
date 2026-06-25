# Add a command-boundary ROLLBACK scenario where the partial artefact landed

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

Roadmap task 6.2.12 closes the second half of the `ROLLBACK` operational
surface at the command boundary. The harness records a torn multi-file turn as
an uncleared `[pending_turn]` record in `working/state.toml`: `novel-state
check` detects it and `novel-state reconcile` either *completes* the partial
write (every missing declared artefact recomputable — `state.toml`/`log.md`) or
*rolls it back* (an unrecoverable artefact — a `draft.md` or a `done.flag` — did
not land), per design §3.4 and §5.4 item 2.

Task 6.2.7 already proved the `ROLLBACK` disposition at the `reconcile` command
boundary for the case where the declared unrecoverable `draft.md` **never
materialised** (`tests/test_torn_turn_rollback_bdd.py`): a real §3.4
`pending_turn` bracket raises mid-turn declaring `working/manuscript/
chapter-99/draft.md`, the chapter never lands, `check` reports
`rollback-pending-turn`, and `reconcile` clears the record. But design §5.4's
clause that rolling back **"leaves the partial artefacts in place — the partial
artefacts stay on disk, unreferenced by state"** (design §5.4 item 2, lines
551-555) is *unexercised at the command boundary*: 6.2.7's torn turn left
nothing partial on disk, so the "preserve the partial residue" guarantee has no
command-boundary proof. Today it is covered only in-process: `tests/
test_reconcile.py::test_rollback_clears_record_and_keeps_every_file` calls the
`reconcile` body function directly over a *hand-planted* corpus fixture, never
crossing the `novel-state` command entry path.

After this change a reader can see an uncleared `[pending_turn]` whose declared
unrecoverable `draft.md` (the next chapter's draft) **did not land as a complete
draft**, while a *partial residue of that draft did land on disk* — the on-disk
remnant of a turn that died mid-write, exactly the §3.4 temp-file-then-`Path.
replace` discipline leaves when the rename never happened — and then watch
`novel-state check` report the torn turn (exit `4` with a `rollback-pending-turn`
reconciliation) and `novel-state reconcile` roll it back (exit `0`: the record
cleared, the partial residue **preserved byte-for-byte on disk and unreferenced
by state**, no `working/` file deleted, the author drafts byte-for-byte intact,
a `rollback-pending-turn` receipt appended to `log.md`) — every command driven
through the same entry path an operator uses, asserted at the command boundary.
The observable proof is a new behavioural (`pytest-bdd`) scenario that is the
*partial-landed* sibling of the *never-landed* ROLLBACK scenario task 6.2.7
added.

The change is observable by running, from the worktree root:

```bash
make test
```

and observing the new behavioural test
`tests/test_torn_turn_rollback_partial_bdd.py::test_*` pass (it fails before the
change because the scenario, feature, and steps do not yet exist).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No production code changes.** This is a test-only task: it adds behavioural
  test coverage. Do not modify any module under `novel_ralph_skill/`. The
  ROLLBACK mechanism — including the "leaves the partial artefacts in place"
  guarantee — is already present in production (`novel_ralph_skill/state/
  reconcile.py` `_classify_pending_turn` and the `_reconcile.py` ROLLBACK
  dispatch, which deletes nothing) and exercised in-process (`tests/
  test_reconcile.py::test_rollback_clears_record_and_keeps_every_file`); only
  the *command-boundary* proof of the **partial-landed** ROLLBACK case is
  missing. If the gap can only be closed by changing production code, stop and
  escalate (it cannot — see `Decision Log D-MECH`, `D-PARTIAL`).
- **Drive recovery through the command boundary, not the bracket primitive.**
  The new scenario must run `check` and `reconcile` through the `novel-state`
  command entry path — the shared
  `novel_ralph_skill.contract.runner.run(build_app(), [...], RunContext(...))`
  wrapper, exactly as `tests/steps/torn_turn_rollback_steps.py` (6.2.7) and
  `tests/steps/reconcile_steps.py` do — and must **not** assert recovery by
  calling `_reconcile.reconcile()` directly or by inspecting
  `derive_reconciliation` for the recovery halves. The roadmap clause is
  explicit: "driven through the command entry points".
- **The torn record must be the residue of a real torn turn, not a hand-planted
  fixture field.** The populated `[pending_turn]` the scenario rolls back must
  be produced by the design §3.4 producer —
  `novel_ralph_skill.state.document.pending_turn(path, operation=..., paths=...)`
  — raising before clean exit, leaving the record populated on disk exactly as
  `tests/steps/torn_turn_steps.py` and `tests/steps/torn_turn_rollback_steps.py`
  already do, declaring an unrecoverable `draft.md` path that never lands *as a
  complete draft*. It must **not** be the `pending-turn-rollback-unrecoverable`
  corpus fixture's planted `pending_turn={...}` dict (that variant has body-call
  coverage only, in `tests/test_reconcile.py`).
- **A partial residue of the declared draft must land on disk inside the torn
  turn, and survive the recovery byte-for-byte.** The defining feature of this
  task (versus 6.2.7) is that *something partial landed*. Inside the §3.4
  bracket — before the raise — the step must write a partial draft residue to
  disk (the temp-file remnant of the mid-write that the `Path.replace` never
  promoted to `draft.md`), then capture its exact bytes. After `reconcile`, the
  scenario must assert that residue is **still present and byte-for-byte
  unchanged**, that no `working/` file was deleted, and that no unexpected file
  was fabricated (only `state.toml` and `log.md` may change) — design §5.4 item
  2: "Rolling back removes nothing — the partial artefacts stay on disk,
  unreferenced by state". The residue's path must **not** be referenced by
  `state` after recovery (the manifest never declared its chapter; the cleared
  `pending_turn` no longer names it).
- **The partial residue must not break the manifest-disk bijection.** This is
  the load-bearing mechanical constraint that distinguishes 6.2.12 from 6.2.7
  and is **verified by experiment** (see `Surprises & Discoveries` S-BIJECTION).
  `derive_reconciliation`'s precedence is refuse-class → pending-turn → recount
  → recreate-log → none (`novel_ralph_skill/state/reconcile.py:256-283`), and
  `manifest-disk-bijection` is a **refuse-class** invariant
  (`reconcile.py:78-83`) that fires *before* the pending-turn branch. The
  bijection check globs `manuscript/chapter-*` directories
  (`novel_ralph_skill/state/_disk_paths.py:24-40`), so a partial residue that
  **creates a new `chapter-NN/` directory** (e.g. `chapter-99/draft.md.tmp`)
  breaks the bijection and the tree classifies `REFUSE`, **not** `ROLLBACK`
  (verified: probe G yielded `action=refuse
  discrepancies=('manifest-disk-bijection',)`). The residue must therefore land
  **inside an existing manifest chapter directory** (a `.tmp` sibling of that
  chapter's real `draft.md`), which preserves the bijection while still being a
  genuine partial-write remnant (verified: probe H yielded `action=
  rollback-pending-turn` over the coherent baseline declaring the missing
  `chapter-99/draft.md`). The scenario asserts `check`'s
  `reconciliation.action == "rollback-pending-turn"` explicitly so a
  misclassification fails loudly.
- **The torn turn must classify as ROLLBACK, not COMPLETE or REFUSE.** The
  declared missing artefact must be an unrecoverable `draft.md`/`done.flag`
  (basename not in `{"state.toml", "log.md"}`,
  `reconcile.py:89` `_RECOMPUTABLE_BASENAMES`), built over an
  otherwise-coherent tree so no refuse-class disk-evidence invariant
  (`manifest-disk-bijection`, `done-flag-without-draft`, `compiled-matches-
  drafts`, `cursor-plan-present`) fires first
  (`reconcile.py:256-265`). The scenario asserts the reconciliation `action` is
  `rollback-pending-turn`, distinguishing it from both the COMPLETE sibling
  6.2.5 proves and a misconstructed REFUSE.
- **Test placement and scaffolding rules** (AGENTS.md; developers-guide
  §"Shared test scaffolding", lines 20+, and the `working_corpus` package, lines
  181+). Tests live under the top-level `tests/` tree. The `working_corpus`
  package is consumed by the sanctioned `import working_corpus as wc` value
  import. Step modules live under `tests/steps/` (the directory `pyproject.toml`
  exempts from the assert/argument-count Ruff rules `S101`, `PLR0913`,
  `PLR0917`, `PLR2004`, `PLR6301` — verified at `pyproject.toml:98`) and are
  bound by a `scenarios(...)` binder module under `tests/`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (task standing rules; AGENTS.md §"Code
  style").
- **Locked dependencies only.** `cuprum==0.1.0`, `cyclopts==4.18.0`,
  `pytest-bdd==8.1.0`, `pytest-timeout==2.4.0`, `pytest-xdist==3.8.0`,
  `syrupy==5.3.2`, `hypothesis==6.155.7`, `tomlkit` (verified against
  `pyproject.toml` and `uv.lock`). Introduce no new dependency. This task
  touches **no cuprum** code path: none of the five commands shells out (design
  §4 line 269: "cuprum is required only where a command shells out (none do in
  v1)"), and this scenario drives only in-process command-runner calls, exactly
  as the proven 6.2.7 sibling does.

## Tolerances (exception triggers)

- **Scope.** If closing the gap requires touching any file under
  `novel_ralph_skill/`, stop and escalate (Constraint "No production code
  changes").
- **Files.** If the change touches more than 5 files (net), stop and escalate.
  The expected set is: 1 new feature file, 1 new steps module, 1 new scenario
  binder, and edits to `docs/roadmap.md` and this ExecPlan — exactly 5.
- **Bijection / disposition.** If the partial residue, as placed, makes the tree
  classify as anything other than `ROLLBACK_PENDING_TURN` — for example `REFUSE`
  because the residue created a new `chapter-NN/` directory and broke the
  manifest-disk bijection (probe G), or `COMPLETE_PENDING_TURN` because the
  declared missing path is recomputable — stop and escalate: the tree
  construction is wrong and must be corrected before the recovery assertions are
  meaningful (`Decision Log D-PARTIAL`, `Surprises` S-BIJECTION).
- **Producer mechanism.** If the §3.4 `pending_turn` bracket producer does not
  leave a populated `[pending_turn]` declaring the unrecoverable `draft.md` path
  on disk that `derive_reconciliation` classifies as `ROLLBACK_PENDING_TURN`,
  stop and escalate rather than reaching for the hand-planted corpus fixture or
  an OS-signal kill.
- **Residue preservation.** If `reconcile` removes or mutates the partial
  residue (rather than leaving it byte-for-byte on disk), do **not** weaken the
  assertion to make the test pass — that would be a genuine §5.4 regression.
  Stop and escalate (the production ROLLBACK dispatch deletes nothing, so this
  must not occur over the locked tree; if it does, the constraint or the tree is
  wrong).
- **Iterations.** If `make all` still fails after 3 fix attempts on any work
  item, stop and escalate.
- **Interpretation.** The roadmap clause reads "a partial `draft.md` materialised
  before the crash". Taken literally as *a new chapter's `draft.md` landed
  partially*, this is mechanically impossible to classify as ROLLBACK in v1: a
  new `chapter-NN/draft.md` creates a new chapter directory that breaks the
  refuse-class `manifest-disk-bijection`, short-circuiting to REFUSE before the
  pending-turn branch (verified, probe G). The faithful achievable realisation
  is the atomic-write **partial residue** (`draft.md.<rand>.tmp`) that the §3.4
  temp-then-`Path.replace` discipline leaves when the rename never happens,
  landed **inside an existing manifest chapter directory** so the bijection
  holds (verified, probe H), with the *declared* missing artefact being the next
  chapter's `draft.md` that never lands. The Success clause's wording ("the
  partial artefact preserved on disk and unreferenced by state") fully supports
  this. If review insists the partial artefact must itself be a complete new
  `chapter-NN/draft.md`, stop and escalate: that requires either a production
  change to the bijection precedence or it cannot classify ROLLBACK
  (`Decision Log D-PARTIAL`).

## Risks

- Risk: The partial residue, if landed as a new `chapter-NN/draft.md` (the most
  literal reading of "a partial `draft.md` materialised"), creates a new chapter
  directory that trips the refuse-class `manifest-disk-bijection` invariant,
  short-circuiting `derive_reconciliation` to `REFUSE` *before* the pending-turn
  branch — so the scenario would prove a REFUSE, not the intended ROLLBACK.
  Severity: high Likelihood: high (it is the central mechanical fact
  distinguishing 6.2.12 from 6.2.7) Mitigation: Land the partial residue as a
  `.tmp` sibling **inside an existing manifest chapter directory** (e.g.
  `working/manuscript/chapter-03/<draft.md residue>.tmp`), which leaves the
  `manuscript/chapter-*` directory set — and thus the bijection — unchanged,
  while still being a genuine §3.4 mid-write remnant. **Verified by experiment**
  (probe G → REFUSE; probe H → ROLLBACK; see `Surprises` S-BIJECTION). The
  declared *missing* unrecoverable artefact is the next chapter's
  `working/manuscript/chapter-99/draft.md`, which never lands. Recorded as
  `Decision Log D-PARTIAL`; the Constraint and the Interpretation tolerance pin
  it. Assert `check`'s `reconciliation.action == "rollback-pending-turn"`
  explicitly so a misclassification fails loudly.

- Risk: A future maintainer (or reviewer) reads "partial `draft.md`" and expects
  the residue file to be literally named `draft.md`, and objects that a `.tmp`
  sibling is not "a partial `draft.md`". Severity: low Likelihood: medium
  Mitigation: The feature/step prose and this plan make the §3.4 mapping
  explicit — the temp-file-then-`Path.replace` discipline (design §3.4 lines
  247-251; `novel_ralph_skill/state/document.py:145-151`,
  `docs/scripting-standards.md` §"Reading / writing files and atomic updates",
  lines 397-414) means a turn that dies mid-write leaves the *partial draft body
  in a temp file*, never a half-written `draft.md` (the `replace` is atomic). So
  the temp residue **is** the on-disk partial artefact §5.4 promises to
  preserve; a literal half-written `draft.md` is the one thing the atomic
  discipline guarantees never exists. Recorded as `Decision Log D-PARTIAL`.

- Risk: The constructed tree could accidentally classify as `REFUSE` for a
  *different* reason (a refuse-class disk-evidence invariant —
  `done-flag-without-draft`, `compiled-matches-drafts`, `cursor-plan-present` —
  fires) or as `COMPLETE_PENDING_TURN` (the declared path is recomputable),
  masking the ROLLBACK case. Severity: medium Likelihood: low Mitigation: Build
  over the coherent baseline `wc.COHERENT_BASELINE` (the settled mid-drafting
  tree; `compiled is None`, so `compiled-matches-drafts` is ABSENT and never
  fires), land the residue as a `.tmp` sibling (non-zero body, so no
  `done-flag-without-draft` interaction even if a flag were near it), and declare
  a `chapter-99/draft.md` whose basename is not recomputable. Probe H confirmed
  ROLLBACK over exactly this construction. Recorded as `Decision Log
  D-COHERENT`.

- Risk: A single recovery pass may not converge if the torn record is layered
  over a tree that also needs another repair. Severity: low Likelihood: low
  Mitigation: The ROLLBACK producer here is built over an otherwise-coherent
  tree, and the residue is a `.tmp` sibling the disk-evidence invariants ignore
  (it is neither a `draft.md`, a `done.flag`, a `compiled.md`, nor a chapter
  directory), so after the single `reconcile` rolls the record back the tree is
  coherent (`pending_turn is None`, no other drift) and one pass converges
  (probe H: a follow-up `derive_reconciliation` over the rolled-back tree is
  `none`). The scenario asserts a single-pass recovery and a clean follow-up
  `check`; if convergence needs more than one pass the tree construction is
  wrong (escalate per the Bijection/disposition tolerance). Recorded as
  `Decision Log D-ONEPASS`.

- Risk: The new BDD step module duplicates the command-driving helpers (`_run`,
  `_run_capturing`, draft-bytes capture, present-files capture) already in
  `tests/steps/torn_turn_rollback_steps.py` (6.2.7) and
  `tests/steps/torn_turn_recovery_steps.py` (6.2.5), drawing a "shared test
  scaffolding" review objection. Severity: low Likelihood: medium Mitigation:
  Keep the new steps self-contained and small, mirroring the established
  `Decision Log D-DUP` choice the 6.2.5 and 6.2.7 plans made for the same
  helpers (the scenarios assert different residue-preservation facts and the
  helpers are a handful of lines). A shared reconcile-family command driver is
  already filed as roadmap task 7.23.3; premature extraction couples three
  suites. If review flags duplication, a shared helper extraction is a cheap
  addendum, not a blocker. Note the choice in `Decision Log D-DUP`.

## Progress

- [x] Work item 1 (red): added the partial-landed ROLLBACK behavioural
  scenario — the feature, steps, and binder — producing the torn ROLLBACK record
  via the §3.4 producer with a partial residue landed inside an existing
  manifest chapter, and driving recovery through the command runner. New:
  `tests/features/torn_turn_rollback_partial.feature`,
  `tests/steps/torn_turn_rollback_partial_steps.py`,
  `tests/test_torn_turn_rollback_partial_bdd.py`. The residue is landed inside
  `manuscript/chapter-03` (an existing baseline chapter) and the declared
  unrecoverable artefact is `chapter-99/draft.md`, confirmed by a fresh probe H
  during implementation (`action=rollback-pending-turn`,
  `discrepancies=('pending-turn-cleared',)`).
- [x] Work item 2 (green): the bound scenario passes (`1 passed`) and the full
  `make all` gate (`build check-fmt lint typecheck test`) is green —
  `977 passed, 1 skipped` — with no regression to the existing torn-turn /
  reconcile suites.
- [x] Work item 3 (docs): ticked roadmap 6.2.12, updated this ExecPlan's living
  sections, and ran `make markdownlint` and `make nixie` (both clean over the
  changed Markdown).

## Surprises & discoveries

- Observation: S-BIJECTION — A partial draft residue that **creates a new
  `chapter-NN/` directory** breaks the refuse-class `manifest-disk-bijection`
  invariant and the tree classifies `REFUSE`, **not** `ROLLBACK`; a residue
  landed **inside an existing manifest chapter directory** preserves the
  bijection and the tree classifies `ROLLBACK_PENDING_TURN`. Evidence: a probe
  built `wc.COHERENT_BASELINE`, raised inside the §3.4 `pending_turn` bracket,
  and ran `derive_reconciliation`:
  - probe G (residue at `manuscript/chapter-04/draft.md.a1b2.tmp`, a *new*
    chapter dir; declared `chapter-04/draft.md` + `chapter-04/done.flag`
    missing) →
    `action=refuse discrepancies=('manifest-disk-bijection',)`.
  - probe H (residue at `manuscript/chapter-03/.draft.md.x9.tmp`, an *existing*
    manifest chapter; declared `chapter-99/draft.md` missing) →
    `action=rollback-pending-turn discrepancies=('pending-turn-cleared',)`.
  Impact: the residue must land inside an existing manifest chapter directory
  (or otherwise not under a `chapter-NN/` path), and the declared *missing*
  unrecoverable artefact is the next chapter's `draft.md`. This is the
  load-bearing difference between 6.2.12 and 6.2.7 (which left nothing on disk),
  recorded in `Decision Log D-PARTIAL`. (Date/Author: 2026-06-25, planning
  agent.)

- Observation: S-ATOMIC — The §3.4 atomic-write discipline guarantees a torn
  mid-write never leaves a *half-written* `draft.md`; it leaves a partial body
  in a temp file (`suffix=".tmp"`) that the `Path.replace` never promoted.
  Evidence: `novel_ralph_skill/state/document.py:145-151` writes to a
  `NamedTemporaryFile(suffix=".tmp", ...)` in the target directory and only then
  `temp_path.replace(path)`; design §3.4 lines 247-251 and
  `docs/scripting-standards.md` lines 397-414 state the temp-then-replace rule.
  Impact: the faithful "partial artefact that landed" is the `.tmp` residue, not
  a half-written `draft.md` — which justifies the residue mechanism in
  `Decision Log D-PARTIAL` rather than hedging on a literal half-file.
  (Date/Author: 2026-06-25, planning agent.)

- Observation: S-SLUG — The chapter manifest entry exposes its on-disk directory
  name as `ChapterEntry.slug` (e.g. `"chapter-03"`), with companion `number`,
  `title`, and `target_words` fields — there is no `id` attribute. The
  "residue unreferenced by state" assertion therefore reconstructs each declared
  chapter draft path as `working/manuscript/{chapter.slug}/draft.md` and asserts
  the residue's `working/manuscript/chapter-03/draft.md.partial.tmp` path is in
  neither the manifest set nor `pending_turn.paths`. Evidence: a probe over
  `wc.COHERENT_BASELINE` printed `ChapterEntry(number=1, slug='chapter-01',
  title='Chapter 1', target_words=24000)`. Impact: confirmed the residue is a
  genuine `.tmp` sibling the manifest never names, so "unreferenced by state" is
  asserted positively rather than merely by the residue's basename. Probe H was
  re-run during implementation and reconfirmed `action=rollback-pending-turn`,
  `discrepancies=('pending-turn-cleared',)` over chapter-03. (Date/Author:
  2026-06-25, implementing agent.)

## Decision log

- Decision: D-MECH — The ROLLBACK torn turn cannot be produced by crashing a
  real command; it must be produced by the design §3.4 `pending_turn` producer
  primitive. Rationale: inherited unchanged from the 6.2.7 plan — `reconcile`
  is the only v1 command that opens a forward `[pending_turn]` bracket, and it
  declares only the recomputable `state.toml`/`log.md`, so a crashed command
  always classifies COMPLETE, never ROLLBACK; no v1 command declares an
  unrecoverable `draft.md`/`done.flag` in a bracket
  (`novel_ralph_skill/commands/_reconcile.py:73-74` `_RECONCILE_PATHS`;
  6.2.7 plan Surprises). The §3.4 `pending_turn` context manager is the
  production producer of torn records (design §3.4;
  `novel_ralph_skill/state/document.py:222`). Date/Author: 2026-06-25, planning
  agent.

- Decision: D-PARTIAL — Model the "partial `draft.md` that landed" as the §3.4
  atomic-write **temp-file residue** (`draft.md.<rand>.tmp`), written inside the
  bracket before the raise, landed **inside an existing manifest chapter
  directory** so the manifest-disk bijection is preserved; the *declared
  missing* unrecoverable artefact is the next chapter's
  `working/manuscript/chapter-99/draft.md`, which never lands. Rationale: a new
  `chapter-NN/` directory breaks the refuse-class `manifest-disk-bijection` and
  forces REFUSE (verified probe G); a residue inside an existing chapter
  preserves the bijection and yields ROLLBACK (verified probe H). The §3.4
  atomic discipline (temp-then-`Path.replace`) means a torn mid-write leaves the
  partial body *in a temp file*, never a half-written `draft.md` (S-ATOMIC), so
  the residue is the faithful on-disk partial artefact §5.4 promises to
  preserve. Date/Author: 2026-06-25, planning agent.

- Decision: D-COHERENT — Build the torn record over `wc.COHERENT_BASELINE` so no
  refuse-class invariant fires and the disposition is unambiguously ROLLBACK.
  Rationale: `derive_reconciliation` checks refuse-class invariants before the
  pending-turn classification (`reconcile.py:256-265`); the baseline is
  mid-drafting with `compiled is None` (no `compiled-matches-drafts`), so the
  uncleared record reaches the pending-turn branch and classifies ROLLBACK on
  the unrecoverable missing path. Verified by probe H. Date/Author: 2026-06-25,
  planning agent.

- Decision: D-ONEPASS — Assert single-pass recovery (one `reconcile`, then a
  clean `check`). Rationale: the ROLLBACK record sits over an
  otherwise-coherent tree and the residue is a `.tmp` sibling the disk-evidence
  invariants ignore, so one `reconcile` clears the record and the tree is
  immediately coherent. A multi-pass need would signal a wrongly-constructed
  tree (escalate per the Bijection/disposition tolerance). Date/Author:
  2026-06-25, planning agent.

- Decision: D-DUP — Keep the new BDD steps self-contained rather than extracting
  a shared command-driver from `tests/steps/torn_turn_rollback_steps.py`.
  Rationale: the 6.2.5 and 6.2.7 plans made the same call for the same helpers;
  the scenarios assert different residue-preservation facts and the helpers are
  a few lines. A shared reconcile-family command driver is already filed as
  roadmap task 7.23.3; premature extraction couples three suites. Date/Author:
  2026-06-25, planning agent.

## Outcomes & retrospective

Delivered as planned, no deviations from the approved mechanism. The Purpose is
met: a real §3.4 `pending_turn` bracket raises mid-turn over `COHERENT_BASELINE`,
having landed a partial `.tmp` residue inside the existing `chapter-03`
directory, declaring an unrecoverable `chapter-99/draft.md` that never lands;
`check` reports the torn turn at exit `4` with a `rollback-pending-turn`
reconciliation and the `pending-turn-cleared` discrepancy; `reconcile` rolls it
back in a single pass (exit `0`), clears the record, appends a
`rollback-pending-turn` receipt to `log.md`, and a follow-up `check` exits `0`.
The distinguishing 6.2.12 proof holds: the residue is preserved byte-for-byte on
disk and unreferenced by state, no `working/` file is removed, and the only files
that appear are `state.toml` and `log.md` — no fabrication. Every command is
driven through the shared command runner, not the bracket primitive.

No production code was touched (Constraint "No production code changes" held).
The change is exactly four files: the feature, the self-contained step module,
the binder, and this ExecPlan, plus the `docs/roadmap.md` tick — within the
five-file tolerance. The bijection-preserving residue placement (probe H,
re-verified) kept the disposition ROLLBACK throughout; no escalation was needed.
The only implementation discovery was the `ChapterEntry.slug` field name
(S-SLUG), which let the "unreferenced by state" assertion be positive rather than
basename-only. `make all` is green at HEAD; `coderabbit review --agent` returned
zero findings.

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
- **Atomic write (§3.4)** — every mutator writes via a temporary file
  (`suffix=".tmp"`) in the target directory followed by `Path.replace`, which is
  atomic on POSIX (design §3.4 lines 247-251;
  `docs/scripting-standards.md` lines 397-414;
  `novel_ralph_skill/state/document.py:145-151`). A crash *after* the temp write
  but *before* the rename leaves the partial body in the `.tmp` file — the
  partial artefact on disk this task preserves. The atomic discipline guarantees
  a half-written *final* `draft.md` never exists.
- **Torn turn** — a turn that died after writing its `[pending_turn]` intent but
  before clearing it. Recovery *completes* the partial write (when every missing
  declared artefact is recomputable: `state.toml`/`log.md`) or *rolls it back*
  (when an unrecoverable `draft.md`/`done.flag` did not land) (design §5.4 item
  2).
- **ROLLBACK disposition** — the reconciliation
  `ReconcileAction.ROLLBACK_PENDING_TURN` (`"rollback-pending-turn"`): the torn
  record's missing declared path is an unrecoverable artefact (a `draft.md`/
  `done.flag`, basename not in `{"state.toml", "log.md"}`), so `reconcile`
  clears the record, deletes nothing, **leaves the partial artefacts in place**,
  and appends a `rollback-pending-turn` receipt
  (`novel_ralph_skill/state/reconcile.py:177-216`, `_classify_pending_turn`;
  `novel_ralph_skill/commands/_reconcile.py:20-21,288-293`).
- **Manifest-disk bijection (refuse-class)** — `manifest-disk-bijection`
  requires every `state.chapters` entry to have its on-disk `chapter-NN/`
  directory and vice versa, contiguous from 1
  (`novel_ralph_skill/state/disk_evidence.py:112-133`). It is **refuse-class**
  (`reconcile.py:78-83`) and fires *before* the pending-turn branch
  (`reconcile.py:256-265`). The check globs `manuscript/chapter-*` directories
  (`novel_ralph_skill/state/_disk_paths.py:24-40`), so any new numeric
  `chapter-NN/` directory breaks it. This is why the partial residue must land
  inside an existing manifest chapter directory (`Surprises` S-BIJECTION).
- **`check` / `reconcile`** — `check` reads disk and `state.toml`, derives the
  reconciliation, reports it under `result.reconciliation`, and exits `4` on any
  actionable finding without writing. `reconcile` independently re-derives the
  same reconciliation and enacts it: for ROLLBACK it runs the manual
  `[pending_turn]` bracket (intent → no-op edit → receipt → clear), appends a
  `rollback-pending-turn` receipt to `log.md`, exits `0`, and deletes no
  `working/` file.
- **`derive_reconciliation`** — the one pure
  `(State, working_dir) -> Reconciliation` function both commands call, in
  `novel_ralph_skill/state/reconcile.py`. Precedence is refuse-class →
  pending-turn → recount → recreate-log → none (`reconcile.py:256-283`).
- **Command boundary / the `run` wrapper** — every command is exercised through
  `novel_ralph_skill.contract.runner.run(app, argv, context)`, which owns
  exit-code translation and envelope emission. Driving a command "through the
  command entry point" means calling

  ```python
  run(build_app(), [subcommand], RunContext(command="novel-state", working_dir="working", human=False))
  ```

  exactly as the existing BDD step modules `tests/steps/reconcile_steps.py`,
  `tests/steps/torn_turn_recovery_steps.py`, and
  `tests/steps/torn_turn_rollback_steps.py` do.
- **The §3.4 producer bracket** —
  `novel_ralph_skill.state.document.pending_turn(path, operation=..., paths=...)`,
  a context manager that writes the `[pending_turn]` record atomically *before*
  yielding and, on an exception, leaves the record populated on disk for the
  next turn's `reconcile` (design §3.4; `document.py:222-267`). The scenario
  writes a partial residue and then raises inside it to manufacture a genuine
  torn ROLLBACK turn with a partial artefact on disk.
- **`working_corpus`** — `tests/working_corpus/`, the test-only package that
  materialises `working/` trees from declarative specs. `build_working_tree(spec,
  tmp_path)` returns the built `working/` path; `COHERENT_BASELINE` is the
  settled mid-drafting baseline spec (3 chapters, `compiled is None`). Consume it
  by the sanctioned `import working_corpus as wc` value import.
- **`pytest-bdd`** — the behavioural-test framework AGENTS.md mandates. A feature
  file under `tests/features/` declares Gherkin scenarios; a step module under
  `tests/steps/` defines `@given`/`@when`/`@then` callables; a binder module
  under `tests/` calls `scenarios("features/<name>.feature")` and star-imports
  the steps so pytest-bdd discovers them.

Files to read or touch:

- `docs/novel-ralph-harness-design.md` §3.4 (lines 245-263, atomic writes and
  the `[pending_turn]` producer bracket — including the temp-file-then-`Path.
  replace` discipline) and §5.4 (lines 529-555, disk-authoritative
  reconciliation; item 2 lines 551-555, the "leaves the partial artefacts in
  place — the partial artefacts stay on disk, unreferenced by state" guarantee
  this task proves). The two sections the roadmap task cites.
- `docs/roadmap.md` lines 1578-1596 (task 6.2.12 statement and success clause).
- `docs/scripting-standards.md` §"Reading / writing files and atomic updates"
  (lines 397-414, the temp-then-`Path.replace` atomic rule — orientation for the
  residue mechanism).
- `docs/developers-guide.md` §"Shared test scaffolding" (lines 20+) and the
  `working_corpus` package (lines 181+) — the sanctioned value import and
  step-module conventions; lines 817+ describe the torn-turn behavioural-scenario
  precedent.
- `docs/adr-002-toml-round-trip-tomlkit.md` (the `tomlkit` document path the
  `pending_turn` bracket writes through — orientation only; no change here).
- `docs/adr-003-shared-interface-contract.md` (the shared command-runner
  interface contract the scenario drives through — orientation only).
- `novel_ralph_skill/state/document.py` — `pending_turn`, `write_text_atomically`
  (the `.tmp` discipline at lines 145-151), `open_pending_turn`,
  `clear_pending_turn`. Do not modify.
- `novel_ralph_skill/state/reconcile.py` — `derive_reconciliation` (precedence,
  lines 256-283), `_classify_pending_turn` (lines 177-216),
  `_REFUSE_CLASS`/`_RECOMPUTABLE_BASENAMES` (lines 78-89),
  `ReconcileAction.ROLLBACK_PENDING_TURN`. Do not modify.
- `novel_ralph_skill/state/disk_evidence.py` — `_check_manifest_disk_bijection`
  (lines 112-133) and the `_PREDICATES`/precedence assembly. Do not modify.
- `novel_ralph_skill/state/_disk_paths.py` — `_on_disk_chapter_numbers`
  (lines 24-40, why a new `chapter-NN/` dir breaks the bijection). Do not modify.
- `novel_ralph_skill/commands/_reconcile.py` — the `reconcile` body and its
  ROLLBACK dispatch (module docstring lines 20-21; dispatch lines 288-293,
  the receipt build). Do not modify.
- `novel_ralph_skill/commands/novel_state.py` — `build_app`,
  `_render_reconciliation` (the `check` envelope `result.reconciliation` shape).
  Do not modify.
- `novel_ralph_skill/contract/runner.py` — `run`, `RunContext`, the `SystemExit`
  exit-code contract.
- `tests/steps/torn_turn_rollback_steps.py`,
  `tests/features/torn_turn_rollback.feature`,
  `tests/test_torn_turn_rollback_bdd.py` — the **never-landed** ROLLBACK sibling
  (6.2.7) this task mirrors; the closest pattern to copy. Do not modify.
- `tests/steps/torn_turn_steps.py`, `tests/features/torn_turn.feature` — the
  §3.4 producer idiom (the `pending_turn` bracket raising mid-turn) to copy for
  the producer half. Do not modify.
- `tests/test_reconcile.py::test_rollback_clears_record_and_keeps_every_file`,
  `tests/test_reconcile_derivation.py` — the existing in-process/pure ROLLBACK
  coverage this task complements (do not modify; they still hold).
- `tests/working_corpus/_reconcile_variants.py::pending_turn_rollback_unrecoverable`
  (lines 191-206) — the reference declaring `chapter-99/draft.md`; the scenario
  uses the same declared-missing shape but produces it through the §3.4 bracket
  *and* lands a partial residue, the distinguishing feature of 6.2.12.

## Plan of work

### Stage A: understand and propose (no code changes)

Read the design sections and the orientation files above and confirm the
mechanism: the partial-landed ROLLBACK torn turn must be produced by the §3.4
`pending_turn` producer declaring an unrecoverable `chapter-99/draft.md` over a
coherent baseline, with a partial `.tmp` residue landed *inside an existing
manifest chapter directory* (so the bijection holds and the disposition is
ROLLBACK, verified probes G/H in `Surprises` S-BIJECTION). Confirm the
command-driving idiom in `tests/steps/torn_turn_rollback_steps.py::_run` /
`_run_capturing`. Go/no-go: if any production change appears necessary, escalate
(Tolerance "Scope"); if a literal new `chapter-NN/draft.md` is demanded, escalate
(Tolerance "Interpretation").

### Stage B: scaffolding and tests (Work item 1, red)

Add the failing behavioural scenario. Three new test artefacts, no production
change:

1. `tests/features/torn_turn_rollback_partial.feature` — a Gherkin feature with
   a single scenario describing: a real §3.4 `pending_turn` bracket raises
   mid-turn
   over a coherent baseline, *after landing a partial draft residue inside an
   existing manifest chapter directory*, declaring an unrecoverable next-chapter
   `draft.md` that never lands, and leaving an uncleared `operation="write-draft"`
   `[pending_turn]`; `check` reports the torn turn at exit `4` with a
   `rollback-pending-turn` reconciliation; `reconcile` rolls it back (exit `0`,
   single pass); a follow-up `check` is clean; **the partial residue is preserved
   byte-for-byte on disk and unreferenced by state**, the chapter drafts are
   byte-for-byte intact, no `working/` file is removed, and no unexpected file is
   fabricated (only `state.toml`/`log.md` change), and the record is cleared.

2. `tests/steps/torn_turn_rollback_partial_steps.py` — the step definitions. The
   `@given` builds the coherent baseline tree via
   `wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)`, then **inside** the
   `pending_turn(working / "state.toml", operation="write-draft",
   paths=["working/manuscript/chapter-99/draft.md"])` bracket — before the raise
   — writes a partial draft residue to an existing manifest chapter directory
   (e.g. `working/manuscript/chapter-03/<draft.md residue>.tmp`) and captures its
   exact bytes and relative path, then raises a sentinel `_TornError` (the bracket
   leaves the record populated). It captures the present files and the draft bytes
   *after* the torn write (the recovery baseline). The `@when`/`@then` steps drive
   `check` and `reconcile` through the `run` wrapper, capture stdout, and assert:
   `check` exits `4` and its envelope `result.reconciliation.action ==
   "rollback-pending-turn"` with the `pending-turn-cleared` discrepancy;
   `reconcile` exits `0` in a single pass; the recovered `state.pending_turn is
   None`; the follow-up `check` exits `0`; the `log.md` carries a
   `rollback-pending-turn` receipt; **the partial residue is still present and
   byte-for-byte unchanged**; no `working/` file removed; the after-set difference
   limited to `{state.toml, log.md}` (no fabrication); drafts byte-for-byte
   unchanged. The torn record is a real torn turn (Constraint, `Decision Log
   D-MECH`); the partial residue is a real §3.4 mid-write remnant (`D-PARTIAL`);
   recovery is driven through the command runner, not the body call (Constraint).

3. `tests/test_torn_turn_rollback_partial_bdd.py` — the binder: a module
   docstring, the `from steps.torn_turn_rollback_partial_steps import *  #
   noqa: F403` star-import, and
   `scenarios("features/torn_turn_rollback_partial.feature")`.

Validation at end of Stage B (red): run the new test alone and confirm it is
*collected* and fails only because, before the steps land, the scenario is
unbound (collection error or a deliberate failing assertion). Do not leave Stage
B with a passing test that never exercised the partial-residue-preserved
rollback path.

### Stage C: green (Work item 2)

Complete the step bodies so the scenario passes. Run the targeted module, then
the full gate. The new behavioural test must pass; the pre-existing
`tests/test_torn_turn_bdd.py`, `tests/test_torn_turn_recovery_bdd.py`,
`tests/test_torn_turn_rollback_bdd.py`, `tests/test_reconcile.py`,
`tests/test_reconcile_derivation.py`, and `tests/test_reconcile_bdd.py` must stay
green.

### Stage D: documentation (Work item 3)

Tick `docs/roadmap.md` task 6.2.12 (`- [ ]` → `- [x]`), update this ExecPlan's
`Progress`, `Surprises & Discoveries`, `Decision Log`, and
`Outcomes & Retrospective`, then run the markdown gates.

Each stage ends with validation. Do not proceed past a failing gate.

## Concrete steps

All commands run from the worktree root (the repository checkout for this
branch's worktree).

Work item 1 (red) — author the feature, steps, and binder, then collect:

```bash
uv run pytest tests/test_torn_turn_rollback_partial_bdd.py -q
```

Expected before the steps are complete: the test fails (collection error or a
deliberate failing assertion), proving the scenario is not yet satisfied.

Work item 2 (green) — complete the steps, then:

```bash
uv run pytest tests/test_torn_turn_rollback_partial_bdd.py -q
```

Expected: `1 passed` (the bound scenario). Then run the full code gate:

```bash
make all
```

Expected: all format, lint, type, and test gates pass. A representative tail:

```plaintext
...
tests/test_torn_turn_rollback_partial_bdd.py .                     [100%]
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
both gates pass without invoking the tree-wide `make fmt` rewrite. Single,
unbreakable identifiers that exceed 80 columns are placed in fenced code blocks
(which the repo config grants a 120-column budget) rather than truncated.

Expected: both pass with no findings on the changed Markdown (`docs/roadmap.md`,
`docs/execplans/roadmap-6-2-12.md`). `make nixie` validates Mermaid; neither
changed file adds a Mermaid diagram, so it is a clean no-op over the edited files
but must still be run per AGENTS.md.

Real transcripts (implementing agent, 2026-06-25):

- Probe H, re-run during implementation over the actual baseline (residue at
  `manuscript/chapter-03/draft.md.partial.tmp`, declaring `chapter-99/draft.md`
  missing), yielded `PROBE_H_ACTION rollback-pending-turn` and
  `PROBE_H_DISCREP ['pending-turn-cleared']`; the baseline materialised
  `chapter-01`, `chapter-02`, `chapter-03`, confirming chapter-03 is an existing
  manifest chapter and chapter-99 never lands.
- `uv run pytest tests/test_torn_turn_rollback_partial_bdd.py -q` →
  `1 passed, 2 warnings` (the warnings are the pre-existing pytest-bdd
  `PytestRemovedIn10Warning`, unrelated to this change).
- `make all` → `977 passed, 1 skipped, 68 warnings`; the `build`, `check-fmt`,
  `lint`, and `typecheck` stages all passed with no findings on the new files.
- `coderabbit review --agent` → `findings: 0`.
- `make markdownlint` and `make nixie` → both clean over the changed Markdown
  (`docs/roadmap.md`, `docs/execplans/roadmap-6-2-12.md`).

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Behavioural (`pytest-bdd`, AGENTS.md "behavioural tests").**
  `tests/test_torn_turn_rollback_partial_bdd.py` binds
  `tests/features/torn_turn_rollback_partial.feature`. Running
  `uv run pytest tests/test_torn_turn_rollback_partial_bdd.py` fails before the
  steps are complete and passes after. The scenario proves, all at the command
  boundary:
  1. a real §3.4 `pending_turn` bracket raises mid-turn over a coherent baseline,
     having landed a *partial draft residue* inside an existing manifest chapter
     directory, declaring an unrecoverable next-chapter `draft.md` that never
     lands, and leaves an uncleared `operation="write-draft"` `[pending_turn]` on
     disk;
  2. `novel-state check` reports the torn turn at exit `4` with a
     `rollback-pending-turn` reconciliation and the `pending-turn-cleared`
     discrepancy;
  3. `novel-state reconcile` rolls the torn turn back in a single pass (exit
     `0`), the recovered `state.pending_turn is None`, a `rollback-pending-turn`
     receipt is appended to `log.md`, and a follow-up `check` exits `0`;
  4. the **partial residue is preserved byte-for-byte on disk and unreferenced by
     state**, every chapter `draft.md` is byte-for-byte identical, no `working/`
     file was removed, and no unexpected file was fabricated — only `state.toml`
     and `log.md` change (design §5.4 item 2: "Rolling back removes nothing — the
     partial artefacts stay on disk, unreferenced by state").

- **No regressions.** `tests/test_torn_turn_bdd.py`,
  `tests/test_torn_turn_recovery_bdd.py`, `tests/test_torn_turn_rollback_bdd.py`,
  `tests/test_reconcile_bdd.py`, `tests/test_reconcile.py`,
  `tests/test_reconcile_derivation.py`, `tests/test_novel_state_check_disk.py`
  stay green.

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
  exercised by `tests/test_reconcile_derivation.py`). If the new step helpers grow
  non-trivial branching, `mutmut` (per the `mutmut` skill / `python-verification`)
  may be used as an optional adversary to confirm the asserts kill mutants of the
  disposition-assertion, residue-preservation, and no-fabrication logic; this is
  optional hardening, not a gate.

Quality method (how we check): `make all` and `make audit`, then `make
markdownlint` and `make nixie` for the Markdown changes (not `make fmt`, which
mass-reformats unrelated docs), run sequentially (never in parallel — the build
cache rewards sequential runs).

## Idempotence and recovery

Every step is re-runnable. The tests materialise throwaway `working/` trees under
pytest `tmp_path`, so re-running leaves no residue. The `pending_turn` bracket
and the partial-residue write touch only the throwaway tree, and
`monkeypatch.chdir` is restored at the end of each test, so nothing leaks across
tests. Editing the roadmap checkbox and this plan is a plain text edit;
re-running the markdown gates is safe. If a gate fails mid-way, fix and re-run
the same command; nothing is destructive.

## Artifacts and notes

The verified mechanism (probes G and H, `Surprises` S-BIJECTION): a partial
residue inside an existing manifest chapter directory keeps the disposition
ROLLBACK; a new `chapter-NN/` directory forces REFUSE. The producer/residue
idiom to author (declaring an unrecoverable next-chapter `draft.md`, landing a
partial residue inside chapter-03, then raising):

```python
class _TornError(RuntimeError):
    """Sentinel raised inside the bracket to simulate a torn turn."""

# A partial draft residue the mid-write left inside an existing manifest
# chapter directory (the §3.4 temp-file the Path.replace never promoted). It
# does NOT create a new chapter-NN/ directory, so the manifest-disk bijection
# holds and the disposition stays ROLLBACK (probe H).
residue = working / "manuscript" / "chapter-03" / "draft.md.partial.tmp"

with pytest.raises(_TornError), pending_turn(  # noqa: PT012
    working / "state.toml",
    operation="write-draft",
    paths=["working/manuscript/chapter-99/draft.md"],
):
    residue.write_text("partial draft body that landed mid-turn", encoding="utf-8")
    raise _TornError  # die before clean exit; record left populated, residue on disk
```

The command-driving idiom to copy from
`tests/steps/torn_turn_rollback_steps.py`:

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
`novel_ralph_skill/commands/novel_state.py` `_render_reconciliation` and
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

The residue-preservation and no-fabrication assertions (the distinguishing proof
of 6.2.12, strengthening the 6.2.7.1 addendum's "forbid fabrication" tightening
to the *partial-landed* case): after `reconcile`,

```python
assert residue.read_bytes() == residue_bytes_before  # preserved byte-for-byte
assert (after_files - before_files) <= {"state.toml", "log.md"}  # no fabrication
assert before_files <= after_files  # no deletion
```

## Interfaces and dependencies

The new test artefacts use only existing, locked interfaces:

- `novel_ralph_skill.contract.runner.run(app, argv, context) -> NoReturn` and
  `RunContext(command, working_dir, human)` — the command boundary.
- `novel_ralph_skill.commands.novel_state.build_app() -> cyclopts.App` — the
  `novel-state` app factory.
- `novel_ralph_skill.state.document.pending_turn(path, *, operation, paths)` —
  the §3.4 producer context manager (raise inside it, after landing the residue,
  to leave a torn record over a partial artefact). Do not modify.
- `novel_ralph_skill.state.load_state(path) -> State` — to read back
  `state.pending_turn` for assertions.
- `working_corpus` (value import `import working_corpus as wc`):
  `build_working_tree(spec, tmp_path) -> Path`, `COHERENT_BASELINE`.
- `pytest_bdd`: `given`, `when`, `then`, `scenarios`.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — `SUCCESS` (0),
  `ACTIONABLE_FINDING` (4).

New test modules to exist at the end of the milestone:

- `tests/features/torn_turn_rollback_partial.feature` — the Gherkin scenario.
- `tests/steps/torn_turn_rollback_partial_steps.py` — defines
  `@given`/`@when`/`@then` callables; a sentinel `class _TornError(RuntimeError)`;
  the §3.4-bracket producer that lands a partial residue inside an existing
  manifest chapter before raising; an `_run`/`_run_capturing` command driver;
  residue-bytes, draft-bytes, and present-files capture; and the
  preservation/no-deletion/no-fabrication assertions (self-contained per
  `Decision Log D-DUP`).
- `tests/test_torn_turn_rollback_partial_bdd.py` — binder calling
  `scenarios("features/torn_turn_rollback_partial.feature")`.

No new production interface, no new dependency, no new console-script. This task
touches no cuprum code path (design §4 line 269: no v1 command shells out), so no
cuprum API (catalogue, allowlisting, run/output options) is relied upon.

## Skills and documentation per work item

- **All work items:** load `leta` (code navigation), `sem` (history), and the
  `execplans` skill (this plan's authoring discipline). Use `python-router` to
  reach the smaller Python skills; for the BDD test work load `python-testing`
  (pytest-bdd fixtures, `target_fixture`, scenario binding). Read AGENTS.md
  §"Change quality and committing" and §"For Python files".
- **Work item 1-2 (the scenario):** read design §3.4 (atomic writes, the
  temp-then-`Path.replace` discipline) and §5.4 item 2 (the
  leaves-partial-artefacts-in-place guarantee); `docs/scripting-standards.md`
  §"Reading / writing files and atomic updates"; `docs/developers-guide.md`
  §"Shared test scaffolding" / `working_corpus`;
  `tests/steps/torn_turn_rollback_steps.py` (the never-landed ROLLBACK sibling)
  and `tests/steps/torn_turn_steps.py` (the §3.4 producer idiom). If asserting
  branch-killing on the new helpers, load `python-verification` then `mutmut`
  (optional, not a gate). No `cuprum`, `hypothesis`, or `crosshair` work is
  needed (no new invariant-over-inputs; no shelling out).
- **Work item 3 (docs):** read AGENTS.md §"Markdown guidance"; run
  `make markdownlint` and `make nixie`.

## Revision note

(Draft. Append later revisions here as the plan changes.)
