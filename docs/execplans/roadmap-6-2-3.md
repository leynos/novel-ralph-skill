# Correct the documented skill defects and point the predicate prose at `novel-done`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

Roadmap task 6.2.3 (`docs/roadmap.md:1301-1309`) closes the last documentation
defects the field report flagged in the prose layer the commands now replace.
The design records the three defects in `docs/novel-ralph-harness-design.md` §8
"Skill defects the rebuild corrects"
(`docs/novel-ralph-harness-design.md:772-792`):

1. a **phase mislabel** — drafting prose calling itself "Phase 7" when drafting
   is Phase 8;
2. a **two-source done predicate** — the short-form predicate in
   `skill/novel-ralph/SKILL.md` and the long-form `novel_predicate` pseudocode
   in `skill/novel-ralph/references/done-conditions.md` are two hand-maintained
   copies that have already drifted apart; and
3. a **dead `plan.md` spec** — a per-chapter `plan.md` listed in the
   `state-layout.md` directory tree that the workflow never writes and nothing
   checks.

The on-disk reality is subtle and was verified during planning (see
`Surprises & discoveries`):

- Defect (1), the phase mislabel, is **already corrected in the skill file**.
  `skill/novel-ralph/SKILL.md:107` now reads "The drafting phase (Phase 8)…",
  and the `### Phase 7 — Chapter planning` / `### Phase 8 — Drafting` headings
  (lines 279, 304) are correct. The correction landed in commit `916313c`
  ("Establish novel-ralph design suite and action Logisphere review (#6)"),
  proven by `git log -L 106,107:skill/novel-ralph/SKILL.md` (it flips "Phase 7"
  → "Phase 8"). It did **not** land in `8d4a07c`, which exists only on
  `origin/skill-turn-around` and is **not** an ancestor of this branch
  (`git merge-base --is-ancestor 8d4a07c HEAD` returns non-zero).
- Defect (3), the dead `plan.md` entry, is **already corrected in the skill
  file**. `grep -n "plan\.md" skill/novel-ralph/references/state-layout.md`
  returns nothing; the chapter directory tree (lines 37-43) lists `scenes.md`,
  `beats.md`, `draft.md`, `critic-notes.md`, `fangirl-notes.md`, and
  `done.flag`, with no `plan.md`. This too landed in `916313c`.
- **But design §8 still describes (1) and (3) as open.** §8 was deliberately
  framed by `916313c` to say "The reference files still carry these defects…
  the corrections to `SKILL.md` and `state-layout.md` are owned by roadmap task
  6.2.3" and cites the now-stale line numbers `SKILL.md:107`, `SKILL.md:304`,
  `state-layout.md:38`. That framing is now contradicted by the very files it
  describes: the skill files no longer carry defects (1) and (3). So the §8
  record is the stale artefact, not the skill files.

The live work is therefore:

- **The done-predicate defect (the real change).** Reduce both prose copies of
  the *novel-level* done predicate to a pointer at the `novel-done`
  console-script, making `novel-done` (its code plus the clause table already in
  `docs/developers-guide.md` §"Done predicate (`novel-done`)") the single
  source of truth, exactly as design §332-333 mandates ("`novel-done` is the
  done predicate as code, replacing the pseudocode in `done-conditions.md`").
- **The §8 record reconciliation.** Update design §8 so it records the
  phase-mislabel and `plan.md` defects as *already corrected in the skill
  files* (with the actual provenance commit, `916313c`) and the two-source
  predicate as *now consolidated by this task*, and so it drops the stale
  `SKILL.md:107` / `SKILL.md:304` / `state-layout.md:38` line references.
  Update the roadmap 6.2.3 item to match what actually remains.
- **The dev-guide cross-reference repoint.** Repoint the one cross-reference in
  `docs/developers-guide.md` (§562-564) that currently treats the
  `done-conditions.md` pseudocode as the authoritative clause spec, so it does
  not dangle once that pseudocode becomes a pointer.

After this change, a reader looking for "what makes the novel done" finds a
single authoritative answer — the `novel-done` command and the developers'
guide clause table — reached by a short pointer from both `SKILL.md` and
`done-conditions.md`, with no second hand-maintained copy left to diverge.

This is a documentation-only task. No Python source, test code, build wiring,
or runtime behaviour changes. Per AGENTS.md §"Quality gates" the validation for
a Markdown-only change is `make markdownlint` plus `make nixie`
(AGENTS.md:96-98, 167-173); there is no new unit, behavioural, property,
snapshot, or e2e test to write, because no executable behaviour changes.
`make all` is run **once** at the end purely as a regression check that the
docs edits did not perturb the build; it is **not** the gate that validates the
Markdown (see the toolchain note below).

## Toolchain note — what each gate actually runs

Pinned to `Makefile` on this branch so the implementer does not assume gate
coverage that does not exist:

- `make all` (`Makefile:28`) expands to `build check-fmt lint typecheck test`.
  It does **not** run `markdownlint`, `nixie`, or `audit`. Those are separate
  targets (`Makefile:104` audit, `Makefile:108` markdownlint, `Makefile:111`
  nixie). So `make all` passing does **not** prove the Markdown change passes
  its own gates.
- For a `.md`-only change, AGENTS.md scopes validation to `make markdownlint`
  (AGENTS.md:97, 169) and `make nixie` (AGENTS.md:98, 172). These are the gates
  that decide whether this task's edits are acceptable.
- `make fmt` (`Makefile:81`) formats Markdown and fixes table markup; run it
  after edits per AGENTS.md:170.
- The Markdown tools (`markdownlint-cli2` and `nixie`) are invoked through the
  existing `make markdownlint` and `make nixie` targets above; the plan does not
  rely on any machine-local tool path.

## Why no external-library research is load-bearing here

The standing planning rules require pinning every external-library API the plan
leans on (cuprum catalogue/allowlisting/absolute-path execution; Cyclopts
`--help`/`--version`; pytest-timeout under xdist; `uv run` semantics) to the
locked versions, verified and cited. This plan leans on **none** of them: it
edits Markdown prose only and runs no new code path. No cuprum catalogue is
constructed, no command is invoked by the change, no test exercises a library.
The only tooling the plan invokes is `markdownlint-cli2` and `nixie` through
the existing `Makefile` targets. Recording this explicitly so the implementer
does not go looking for a library contract that does not exist for this task.
If implementation reveals that a prose edit forces a behavioural assertion (it
should not), stop and escalate per Tolerances rather than inventing a test.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. **Documentation-only.** No file under `novel_ralph_skill/`, `tests/`,
   `pyproject.toml`, `Makefile`, or `.github/` is edited. The change set is
   confined to Markdown under `skill/` and `docs/`.
2. **`novel-done` is the single source of truth for the done predicate**
   (design §3.3 read-only checker column; design §332-333; ADR-001
   deterministic/judgemental boundary). The prose must point at the command and
   the developers' guide clause table, never re-state the clause logic in a
   form that can drift.
3. **No new second copy.** The fix must not introduce a third prose statement of
   the predicate. After the change, the *only* normative statement of the
   novel-level clauses lives in `docs/developers-guide.md` §"Done predicate
   (`novel-done`)" (the six-clause table) and in the code it documents; every
   other mention is a pointer to it.
4. **Preserve the non-predicate content of `done-conditions.md`.** Only the
   *novel-level* predicate (the `## Novel-level predicate` section's
   `novel_predicate` pseudocode and the `## How to evaluate` novel-level
   pseudocode) is reduced to a pointer. The **phase-level exit criteria** and
   **chapter-level done conditions** sections are distinct artefacts the
   harness still needs (no command checks per-phase or per-chapter exit), and
   the **BLOCKER resolution convention** prose (the `## Novel-level predicate`
   trailing paragraphs about `contains_unresolved_blocker` and the `### Bn`
   format) is a producer/consumer contract shared with `critic-personas.md`
   (design §330; roadmap 3.1.4/3.1.5); these must survive. Removing them would
   regress roadmap 3.1.4/3.1.5 and the §8 producer-contract guarantee.
5. **Do not gut completed-work records.** `novel_predicate` also appears in
   `docs/roadmap.md:929,937` (the closed 3.1.1.1/3.1.1.2 addenda) and in
   `docs/execplans/roadmap-3-1-1.md` and `roadmap-3-1-1.review-r1.md`. These
   are historical records of finished work and are **out of scope**: this task
   does not edit them. The success grep is therefore scoped to `skill/` (see
   Constraint 6), never the whole repo.
6. **Scoped success grep.** The "no surviving prose copy" gate is
   `grep -rn "novel_predicate" skill/` returning no match — the two skill files
   are the only place this task removes the pseudocode. The dev-guide reference
   to the term is repointed (Work Item 3) to a description, not a code symbol,
   so it too clears; but the canonical gate is the `skill/`-scoped grep. The
   repo addenda and prior execplans are excluded by design (Constraint 5).
7. **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all edited prose and
   commit messages (AGENTS.md; `docs/scripting-standards.md` prose convention),
   except verbatim external API names.
8. **Markdown style** holds on every edited file: paragraphs and bullets wrapped
   at 80 columns, code blocks at 120, dashes for bullets, tables and headings
   unwrapped (AGENTS.md §"Markdown guidance", lines 167-177;
   `docs/documentation-style-guide.md`). `make markdownlint` and `make nixie`
   must pass.

## Tolerances (exception triggers)

Thresholds that trigger escalation rather than autonomous workaround.

- **Scope.** If the change touches more than the five Markdown files named in
  "Plan of work" (`skill/novel-ralph/SKILL.md`,
  `skill/novel-ralph/references/done-conditions.md`,
  `docs/novel-ralph-harness-design.md`, `docs/developers-guide.md`,
  `docs/roadmap.md`), or net more than ~120 changed lines, stop and escalate.
- **Behaviour.** If any edit appears to require a Python, test, or `Makefile`
  change to keep a gate green, stop and escalate — a docs task must not.
- **Predicate semantics.** If reducing the `done-conditions.md` pseudocode to a
  pointer would lose a clause or edge the developers' guide table does *not*
  already capture (so the pointer would point at something less precise than
  what is removed), stop and escalate: the consolidation target must be at
  least as complete as the text it replaces.
- **Cross-reference breakage.** If repointing the developers' guide §562-564
  reference reveals further references into the removed pseudocode elsewhere in
  `docs/developers-guide.md`, `skill/`, `docs/users-guide.md`, or the design
  doc (beyond the completed-work records in Constraint 5, which are out of
  scope), stop and list them before proceeding.
- **Record reconciliation.** If updating design §8 to record defects (1) and (3)
  as already-corrected appears to require changing the *substance* of any other
  design section (not just §8's defect bullets), stop and escalate — the §8
  edit is a record correction, not a redesign.
- **Ambiguity.** If the maintainer's intent for "reduce to a pointer" is read by
  review as "delete the pseudocode entirely" versus "replace with a short
  pointer paragraph", and the choice materially changes the result, present
  both and ask. (This plan chooses "replace with a short pointer paragraph that
  names `novel-done` and links the developers' guide clause table", per design
  §332-333 and Constraint 3.)
- **Iterations.** If `make markdownlint` or `make nixie` still fails after 3
  fix attempts on a file, stop and escalate with the tool output.

## Risks

- Risk: An implementer trusts the roadmap/design line numbers (`SKILL.md:107`,
  `SKILL.md:304`, `state-layout.md:38`) and either "re-fixes" already-correct
  skill prose or edits the wrong line, instead of recognising that the skill
  files are already corrected and only §8's *record* is stale. Severity:
  medium. Likelihood: medium. Mitigation: Work Item 1 verifies the current
  on-disk state of defects (1) and (3) by content (grep on text), not line
  number, before any edit, and records the finding in `Decision Log`. The §8
  edit corrects the record; it does not touch the skill prose for defects (1)
  and (3).

- Risk: An implementer cites `8d4a07c` (the round-1 plan's mistaken provenance)
  in the §8 edit, writing a dangling reference into the canonical design doc —
  `8d4a07c` is not on this branch's history. Severity: high. Likelihood: medium
  (the round-1 plan explicitly instructed it). Mitigation: Work Item 1 cites
  the *verified* provenance commit `916313c` (or drops the commit citation and
  states the correction by content). The plan records the
  `git merge-base --is-ancestor 8d4a07c HEAD` non-zero result so the
  implementer does not reintroduce the wrong SHA.

- Risk: The "no surviving copy" success grep is run unscoped
  (`grep -rn "novel_predicate" skill/ docs/`) and can never pass because the
  term legitimately survives in `docs/roadmap.md` addenda and prior execplans,
  which this task must not touch. Severity: high. Likelihood: high (the round-1
  plan used the unscoped grep). Mitigation: Constraints 5 and 6 fix the
  canonical gate to `grep -rn "novel_predicate" skill/` (the two edited skill
  files). The completed-work records are explicitly out of scope.

- Risk: Reducing the `done-conditions.md` pseudocode to a pointer orphans the
  developers' guide cross-reference at §562-564, which currently asserts the
  clause truth conditions *are* that pseudocode body, producing a dangling
  pointer. Severity: medium. Likelihood: high (a certainty unless handled).
  Mitigation: Work Item 3 repoints that reference at design §4.2 plus the
  `novel-done` code (`novel_ralph_skill/state/done_predicate.py`) — the actual
  authority — in the same change.

- Risk: The BLOCKER resolution convention lives inside the same
  `## Novel-level predicate` section being trimmed, so a blunt deletion drops a
  producer/consumer contract (regressing roadmap 3.1.4/3.1.5). Severity: high.
  Likelihood: medium. Mitigation: Constraint 4 enumerates exactly what
  survives; Work Item 2 keeps the resolution-convention prose, removing only the
  `novel_predicate` pseudocode body and the duplicated clause enumeration, and
  re-homes any surviving normative text under a "see `novel-done`" pointer.

- Risk: Markdown reflow after editing changes table or fence formatting and
  trips
  `markdownlint` rules unrelated to the intended edit. Severity: low.
  Likelihood: medium. Mitigation: Run `make fmt` then `make markdownlint` after
  each file edit (not only at the end) per AGENTS.md:170.

- Risk: `make all` (the end-of-task regression check) fails on a non-Markdown
  gate for reasons unrelated to this docs change. Severity: low. Likelihood:
  low. Mitigation: `make all` does not gate this docs change (Toolchain note);
  the Markdown gates do. If `make all` fails on a non-Markdown gate, confirm
  against a clean checkout that the failure pre-exists this change before
  escalating.

## Progress

- [x] Work Item 1: Reconcile the design §8 record (and the roadmap 6.2.3 item) to
  the on-disk reality — defects (1) and (3) already corrected in the skill files
  by `916313c`; defect (2) the live work. Done: verified on-disk by content; §8
  and the roadmap item rewritten; `make all`, `make markdownlint`, `make nixie`
  green.
- [x] Work Item 2: Reduce both prose copies of the novel-level done predicate to
  a pointer at `novel-done`. Done: removed the `novel_predicate`/`novel_is_done`
  pseudocode from `done-conditions.md` and the five-item short-form list from
  `SKILL.md`; repointed the four in-text mentions (truthful-done principle,
  entry-routine step 5, Phase 9 exit, "almost done" anti-pattern) at
  `novel-done`; kept the BLOCKER resolution convention, final-log template,
  failure modes, and anti-patterns. `grep -rn "novel_predicate" skill/` clean;
  `make all`, `make markdownlint`, `make nixie` green; coderabbit 0 findings.
- [x] Work Item 3: Repoint the developers' guide cross-reference off the removed
  pseudocode. Done: §562-564 now presents the clause table as authoritative,
  sourcing the conditions from design §4.2 and `done_predicate.py`, not the
  removed `novel_predicate` body; the "Manifest, not outline" note records the
  manifest reconciliation as 3.1.1.1's work (never 6.2.3's) and that the skill
  prose now points at `novel-done`. `grep -n "novel_predicate"
  docs/developers-guide.md` clean; remaining `done-conditions.md` references
  point only at surviving content; `make all`, `make markdownlint`, `make nixie`
  green; coderabbit 0 findings.

## Surprises & discoveries

- Observation: Two of the three §8 defects (phase mislabel, dead `plan.md`) are
  already corrected **in the skill files**, but design §8 still records them as
  open. Evidence: `skill/novel-ralph/SKILL.md:107` reads "(Phase 8)";
  `git log -L 106,107:skill/novel-ralph/SKILL.md` shows commit `916313c`
  flipped "Phase 7" → "Phase 8".
  `grep -n "plan\.md" skill/novel-ralph/references/state-layout.md` returns
  nothing (the entry is gone; `916313c` removed it). Yet
  `docs/novel-ralph-harness-design.md:774-792` still says "The reference files
  still carry these defects" and cites stale line numbers. Impact: Work Item 1
  corrects the §8 *record* (it is the stale artefact), not the skill prose for
  defects (1) and (3). The substantive edit is the done-predicate consolidation
  in Work Item 2.

- Observation: The round-1 plan cited commit `8d4a07c` as the fix for defects
  (1)
  and (3). That commit is not on this branch. Evidence:
  `git merge-base --is-ancestor 8d4a07c HEAD` returns non-zero;
  `git branch -a --contains 8d4a07c` lists only `skill-turn-around` /
  `origin/skill-turn-around`. The real provenance is `916313c` ("Establish
  novel-ralph design suite and action Logisphere review (#6)"). Impact: The §8
  record must cite `916313c` (or no commit), never `8d4a07c`.

- Observation: The `done-conditions.md` `novel_predicate` already iterates the
  **manifest**, not the outline. Evidence:
  `skill/novel-ralph/references/done-conditions.md:157-160` iterates
  `state["chapters"]` ("The manifest … is the authoritative chapter set; design
  §4.3 pins the chapter source to the manifest, not to outline prose"); clause
  5 (lines 173-175) iterates the same set. Roadmap 3.1.1.1
  (`docs/roadmap.md:925-934`, marked `[x]`) performed this manifest
  reconciliation. Impact: The dev-guide §580-586 "recorded so a later docs pass
  can reconcile `done-conditions.md` to the manifest source" note is **already
  stale, independent of this task** — 3.1.1.1 did that reconciliation, not
  6.2.3. This plan does **not** claim to perform the manifest reconciliation;
  it only repoints the §562-564 clause-source reference (Work Item 3).

## Decision log

- Decision: Treat the done-predicate consolidation as the single substantive
  change, and the phase/`plan.md` defects as already-corrected in the skill
  files whose §8 *record* must be reconciled. Rationale: Verified on disk and
  in git history that `916313c` already corrected the skill files for (1) and
  (3); design §332-333 and §8 make `novel-done` the source of truth, so the
  remaining drift is the two predicate copies. Date/Author: 2026-06-24,
  planning agent.

- Decision: Cite `916313c` (not `8d4a07c`) as the provenance of the
  already-landed phase/`plan.md` corrections, or state the correction by
  content with no commit SHA. Rationale:
  `git merge-base --is-ancestor 8d4a07c HEAD` is non-zero; `8d4a07c` is on
  `skill-turn-around` only. Citing it would write a dangling provenance
  reference into the canonical design doc. `git log -L 106,107:...SKILL.md`
  pins the change to `916313c`. Date/Author: 2026-06-24, planning agent.

- Decision: Scope the "no surviving copy" success gate to
  `grep -rn "novel_predicate" skill/`, not the whole repo. Rationale:
  `novel_predicate` legitimately survives in `docs/roadmap.md:929,937` (closed
  3.1.1.1/3.1.1.2 addenda) and in `docs/execplans/roadmap-3-1-1*.md`, which are
  completed-work records this task must not gut. The two skill files are the
  only place this task removes the pseudocode. Date/Author: 2026-06-24,
  planning agent.

- Decision: In Work Item 3, repoint §562-564 off the pseudocode, and treat the
  §580-586 "later docs pass can reconcile" note as describing reconciliation
  that 3.1.1.1 already performed — do not record 6.2.3 as having performed it.
  Rationale: `done-conditions.md:157-160` already iterates the manifest; the
  note is stale because of 3.1.1.1, not 6.2.3. Misattributing it would write a
  false provenance narrative. Date/Author: 2026-06-24, planning agent.

- Decision: "Reduce to a pointer" means replace the `novel_predicate` pseudocode
  body and the SKILL.md short-form clause list with a short pointer paragraph
  that names `novel-done` and links the developers' guide clause table, not a
  bare deletion. Rationale: Design §332-333 says `novel-done` *replaces* the
  pseudocode; a pointer keeps the navigation a reader needs while removing the
  divergent copy (Constraint 3). Date/Author: 2026-06-24, planning agent.

- Decision: Keep the phase-level exit criteria, chapter-level done conditions,
  and the BLOCKER resolution convention in `done-conditions.md`. Rationale:
  They are not the novel-level predicate; no command supersedes them, and the
  resolution convention is a producer/consumer contract shared with
  `critic-personas.md` (design §330; roadmap 3.1.4/3.1.5). Date/Author:
  2026-06-24, planning agent.

## Outcomes & retrospective

Delivered as planned, in three atomic commits.

- **Purpose met.** A reader looking for "when is the novel done" is now pointed
  at `novel-done` and the developers' guide six-clause table from both
  `SKILL.md` and `done-conditions.md`; no second hand-maintained predicate copy
  survives (`grep -rn "novel_predicate" skill/` is clean). Design §8 records the
  phase-mislabel and `plan.md` defects as already corrected in the skill files
  (provenance `916313c`, never `8d4a07c`) and the two-source predicate as
  consolidated here; the roadmap 6.2.3 item matches. The dev-guide §562-564
  reference is repointed at design §4.2 and `done_predicate.py`, and the
  "Manifest, not outline" note attributes the manifest reconciliation to 3.1.1.1.
- **Gates.** `make markdownlint` and `make nixie` pass repo-wide on every commit;
  `make all` (`build check-fmt lint typecheck test`) stays green at 761 passed,
  1 skipped. Coderabbit: three runs (one per work item); the first surfaced three
  minor portability nits on the execplan text (two fixed, one skipped — the
  frozen round-1 review record), the latter two returned zero findings.
- **Deviation (recorded).** `make fmt`/`mdtablefix` reflows the entire
  repository's Markdown — a known recurring nuisance on this repo (see the long
  run of "spurious make-fmt mdformat churn" stashes). Running it would have
  produced a ~140-file diff far outside this task's scope (Tolerances: Scope).
  Instead, edited files were hand-wrapped to 80 columns and validated with
  `markdownlint-cli2` directly; the committed diffs are confined to the five
  planned files plus the execplan. The Markdown gates (`make markdownlint`,
  `make nixie`) — the gates AGENTS.md scopes a `.md`-only change to — pass
  repo-wide.

## Context and orientation

The repository is a Python package (`novel_ralph_skill/`) that ships a set of
deterministic console-scripts plus an authored Claude skill under `skill/`. The
skill's prose (read by the model at runtime) lives in
`skill/novel-ralph/SKILL.md` and its reference files under
`skill/novel-ralph/references/`. The design of record is
`docs/novel-ralph-harness-design.md`; supporting decisions are the ADRs
(`docs/adr-00*.md`); developer-facing internals are in
`docs/developers-guide.md`; user-facing behaviour in `docs/users-guide.md`; and
the build order in `docs/roadmap.md`.

Key terms:

- **Done predicate.** The boolean condition under which the Ralph Loop
  terminates: the novel is finished. Design §4.2 fixes it as six clauses.
- **`novel-done`.** The read-only console-script that evaluates the done
  predicate per clause and returns a structured result plus an exit code
  (design §4.2; `docs/developers-guide.md` §"Done predicate (`novel-done`)";
  pure engine `novel_ralph_skill/state/done_predicate.py`; command body
  `novel_ralph_skill/commands/_novel_done.py`).
- **Short-form predicate.** The five-item list under
  `## Done predicate (short form)` in `skill/novel-ralph/SKILL.md` (currently
  lines 455-468). It omits `final_pass_complete` as a named clause (folding it
  loosely into item 5, "Phase 9's final pass is logged as complete") and omits
  the knitting gate booleans — the drift the design flags.
- **Long-form predicate.** The `novel_predicate(working_dir, state)` Python
  pseudocode under `## Novel-level predicate` in
  `skill/novel-ralph/references/done-conditions.md` (currently lines 150-189).
- **Clause table.** The authoritative six-clause enumeration with disk sources
  in `docs/developers-guide.md` §"Done predicate (`novel-done`)" (currently
  lines 562-578). This is the consolidation target.

The files this plan edits, with the content (not line number) each edit targets:

- `skill/novel-ralph/SKILL.md` — the `## Done predicate (short form)` section
  and its in-text pointers to "the done predicate in
  `references/done-conditions.md`" (the entry routine bullet near line 42, the
  Phase 9 `**Exit:**` line near 424-425, the anti-patterns "Run the predicate"
  line near 543). The phase-label prose (line 107) is **already correct** and
  is not edited.
- `skill/novel-ralph/references/done-conditions.md` — the
  `## Novel-level predicate` section's `novel_predicate` pseudocode and the
  novel-level
  `## How to evaluate` pseudocode (the `return novel_predicate(...)` call near
  line 26).
- `docs/novel-ralph-harness-design.md` — §8 "Skill defects the rebuild
  corrects" (lines 772-792).
- `docs/developers-guide.md` — the §"Done predicate (`novel-done`)" cross
  reference that points back into the pseudocode (the §562-564 "their truth
  conditions are the `novel_predicate` body" sentence). The §580-586 "Manifest,
  not outline" note is touched only if its premise can be made truthful without
  claiming 6.2.3 did the reconciliation (see Work Item 3).
- `docs/roadmap.md` — the 6.2.3 item text, updated to match what landed.

## Plan of work

Three atomic, independently committable work items, ordered so that the
substantive predicate consolidation (Work Item 2) lands between the record
correction (Work Item 1) and the cross-reference repoint (Work Item 3). Each
ends with the Markdown gates green on the edited files.

### Work Item 1 — Reconcile the §8 record and the roadmap item to on-disk reality

Implements: design §8 (the record of defects); roadmap 6.2.3 first and third
sub-bullets (`docs/roadmap.md:1304-1306`). Read first: design §8
(`docs/novel-ralph-harness-design.md:772-792`);
`docs/documentation-style-guide.md` (single-source-of-truth and cross-reference
guidance). Load skill: none beyond the Markdown gates; this is prose. Use `leta`
/`sem` only if navigation is needed — this item is a pure prose edit.

Verify on disk first (do not trust the cited line numbers): grep
`skill/novel-ralph/SKILL.md` for the drafting-phase sentence and confirm it
reads "(Phase 8)"; confirm `### Phase 7 — Chapter planning` and
`### Phase 8 — Drafting` headings; grep
`skill/novel-ralph/references/state-layout.md` for `plan.md` and confirm no
per-chapter entry. Record the no-op finding (already seeded in
`Surprises & discoveries`).

Then edit `docs/novel-ralph-harness-design.md` §8 so it reads as the true
record:

- The **phase-mislabel** bullet: state it is **already corrected in
  `SKILL.md`** (drafting reads "Phase 8"), landed in commit `916313c`. Remove
  the stale `SKILL.md:107` / `SKILL.md:304` references. Do **not** cite
  `8d4a07c`.
- The **dead `plan.md`** bullet: state it is **already removed from
  `state-layout.md`**, landed in commit `916313c`. Remove the stale
  `state-layout.md:38` reference.
- The **two-source done predicate** bullet: keep as the live defect, and state
  that roadmap 6.2.3 consolidates both prose copies to a pointer at
  `novel-done` (Work Item 2 performs this).
- The §8 preamble (lines 774-779) that says "The reference files still carry
  these defects … the corrections … are owned by roadmap task 6.2.3": reframe
  so it no longer claims the skill files are unfixed; instead, it records that
  the phase/`plan.md` corrections already landed and the predicate
  consolidation is the remaining 6.2.3 work.

Then edit the `docs/roadmap.md` 6.2.3 item (lines 1301-1309) so its sub-bullets
and success criterion describe the actual remaining work — note that the phase
mislabel and `plan.md` entry are already corrected in the skill files, and that
the substantive work is the predicate consolidation — without changing the item
number or its `Requires phase 3` dependency. Replace the success criterion with
the scoped one (Constraint 6).

Tests: none (documentation-only; AGENTS.md scopes Markdown changes to the
Markdown gates). Validation: run `make fmt`, then `make markdownlint` and
`make nixie`; expect each to exit 0 with no findings on the two edited files.
Commit message (en-GB, imperative, ~50-col subject): e.g. "Reconcile §8
skill-defect record to on-disk reality".

### Work Item 2 — Reduce both done-predicate copies to a pointer at `novel-done`

Implements: design §8 second bullet and §332-333 (`novel-done` replaces the
pseudocode); roadmap 6.2.3 second sub-bullet and the (now scoped) success
criterion. This is the substantive change. Read first: design §3.3 (read-only
checker column), §4.2 (the six clauses), §332-344 (`novel-done` behaviour and
exit codes); `docs/developers-guide.md` §"Done predicate (`novel-done`)" (the
clause table, the consolidation target); ADR-001
(`docs/adr-001-deterministic-judgemental-boundary.md`). Load skill: none beyond
the Markdown gates.

In `skill/novel-ralph/SKILL.md`, replace the body of the
`## Done predicate (short form)` section (lines 455-468) with a short pointer
paragraph: the novel is done when `novel-done` exits 0; the authoritative
clauses and their disk sources are owned by `novel-done` and tabulated in the
developers' guide; truthful "done" means running the command, not re-asserting
a hand-kept list. Keep the section heading (so existing links survive) but drop
the five-item clause list that omits `final_pass_complete`. Update the in-text
mentions that point at "the done predicate in `references/done-conditions.md`"
(the idempotent-entry bullet near line 42, the Phase 9 `**Exit:**` line near
424-425, and the anti-patterns "Run the predicate" line near 543) so they point
at `novel-done` as the evaluator and at `done-conditions.md` only for the
*phase-level and chapter-level* conditions that genuinely live there.

In `skill/novel-ralph/references/done-conditions.md`, replace the
`## Novel-level predicate` `novel_predicate(...)` pseudocode (lines 150-189)
and the novel-level `## How to evaluate` pseudocode (the
`return novel_predicate(...)` call near line 26) with a pointer paragraph naming
`novel-done` and linking the developers' guide clause table, while **keeping**
(per Constraint 4): the phase-level exit criteria section, the chapter-level
done conditions section, and the BLOCKER resolution convention prose (the
trailing paragraphs about `contains_unresolved_blocker` and the `### Bn` format
— re-homed under the pointer if needed). The final-log-entry template and the
predicate failure-modes/anti-patterns prose may stay as operator guidance, but
must not re-enumerate the clause logic in a way that can drift — trim any
clause restatement to a reference.

After the edits, `grep -rn "novel_predicate" skill/` returns no surviving prose
copy of the clause body (the scoped success criterion, Constraint 6), and the
only normative clause enumeration is the developers' guide table.

Tests: none (documentation-only). The behavioural truth of the clauses is
already pinned by the existing `novel-done` suite
(`tests/test_done_predicate*.py`, `tests/test_novel_done_*.py`); this change
does not alter that code, so no test is added or modified. Validation:
`make fmt`, then `make markdownlint` and `make nixie` pass on the two edited
files; `grep -rn "novel_predicate" skill/` returns no match. Commit message:
e.g. "Point done-predicate prose at the novel-done command".

### Work Item 3 — Repoint the developers' guide reference off the removed pseudocode

Implements: Constraint 2/3 (single source of truth, no dangling pointer). Read
first: `docs/developers-guide.md` §"Done predicate (`novel-done`)" (lines
547-590), specifically the §562-564 "their truth conditions are the
`novel_predicate` body in `done-conditions.md`" sentence and the §580-586
"Manifest, not outline" note. Load skill: none beyond the Markdown gates.

Edit `docs/developers-guide.md` so the clause table is presented as the
authoritative statement of the clause truth conditions, sourcing them from the
`novel-done` code and design §4.2 rather than from the `done-conditions.md`
pseudocode that Work Item 2 removes. Concretely, repoint the §562-564 sentence
away from "their truth conditions are the `novel_predicate` body in
`skill/novel-ralph/references/done-conditions.md`" to "their truth conditions
are fixed by design §4.2 and implemented in
`novel_ralph_skill/state/done_predicate.py`".

For the §580-586 "Manifest, not outline" note: its premise ("The reference
predicate iterates planned chapters parsed from `plan/chapter-outline.md`") is
**already false** — `done-conditions.md:157-160` iterates the manifest
(`state["chapters"]`), reconciled by roadmap **3.1.1.1** (a closed addendum),
not by this task. So either (a) leave the note untouched if it is not orphaned
by Work Item 2's edit, or (b) if Work Item 2's removal of the pseudocode leaves
the note pointing at deleted text, update it to record that the reference prose
now points at `novel-done` and that the manifest reconciliation was already
performed by 3.1.1.1. **Do not** write any narrative attributing the manifest
reconciliation to this task (6.2.3); that work was 3.1.1.1's.

Tests: none (documentation-only). Validation: `make fmt`, then
`make markdownlint` and `make nixie` pass on the edited file;
`grep -n "done-conditions.md" docs/developers-guide.md` shows the remaining
references point only at the phase-level / chapter-level / resolution content
that survives, not at the removed pseudocode. Commit message: e.g. "Repoint
dev-guide done-predicate reference at the command".

## Concrete steps

Run everything from the worktree root for this branch (the directory the
`roadmap-6-2-3` worktree is checked out in). Confirm the branch first:

```bash
git branch --show-current
# expect: roadmap-6-2-3
```

Work Item 1 — verify the already-fixed defects by content, confirm provenance,
then correct the records:

```bash
grep -n "drafting phase\|Phase 8\|Phase 7" skill/novel-ralph/SKILL.md
# expect line ~107 to read "The drafting phase" + "(Phase 8)"; headings 279/304
grep -n "plan\.md" skill/novel-ralph/references/state-layout.md
# expect: no output (no per-chapter plan.md entry)
git merge-base --is-ancestor 8d4a07c HEAD; echo "ancestor? $?"
# expect: non-zero exit (8d4a07c is NOT on this branch — do not cite it)
git log -L 106,107:skill/novel-ralph/SKILL.md --oneline | head -3
# expect: 916313c shown flipping "Phase 7" -> "Phase 8" (the real provenance)
```

Edit `docs/novel-ralph-harness-design.md` §8 and `docs/roadmap.md` 6.2.3, then:

```bash
make fmt
make markdownlint
make nixie
```

Expect `markdownlint` and `nixie` to exit 0 with no findings.

Work Item 2 — edit `skill/novel-ralph/SKILL.md` and
`skill/novel-ralph/references/done-conditions.md`, then prove the copy is gone
(scoped to `skill/`):

```bash
grep -rn "novel_predicate" skill/
# expect: no match (the prose pseudocode copy is removed from the skill files)
make fmt
make markdownlint
make nixie
```

Note: an unscoped `grep -rn "novel_predicate" skill/ docs/` will still match
`docs/roadmap.md:929,937` and `docs/execplans/roadmap-3-1-1*.md` — those are
closed-work records this task must not edit (Constraint 5). The canonical gate
is the `skill/`-scoped grep above.

Work Item 3 — edit `docs/developers-guide.md`, then:

```bash
grep -n "done-conditions.md" docs/developers-guide.md
# expect: remaining references point at phase/chapter/resolution content only
grep -n "novel_predicate" docs/developers-guide.md
# expect: no match (the §562-564 sentence is repointed off the symbol)
make fmt
make markdownlint
make nixie
```

After all three work items, run the full build gate once as a regression check
(it does NOT validate the Markdown — the Markdown gates above do):

```bash
make all
# Makefile:28 -> build check-fmt lint typecheck test (no markdownlint/nixie/audit)
```

Expect `build check-fmt lint typecheck test` to pass. If a non-Markdown gate
fails, confirm it pre-exists this docs change before escalating (see Risks).

## Validation and acceptance

Acceptance is behavioural for the documentation:

- A reader who opens `skill/novel-ralph/SKILL.md` and looks for "when is the
  novel done" is pointed at `novel-done` (and the developers' guide clause
  table), not at a five-item list that omits `final_pass_complete`.
- A reader who opens `skill/novel-ralph/references/done-conditions.md` finds the
  novel-level predicate expressed as a pointer at `novel-done`, with the
  phase-level and chapter-level conditions and the BLOCKER resolution
  convention still present.
- `grep -rn "novel_predicate" skill/` returns no match: no prose copy of the
  predicate body survives in the skill files to diverge (the scoped roadmap
  success criterion; Constraints 5-6). The term legitimately remains in the
  out-of-scope closed-work records (`docs/roadmap.md`, `docs/execplans/`).
- `docs/novel-ralph-harness-design.md` §8 records the phase-mislabel and
  `plan.md` defects as already corrected in the skill files (provenance
  `916313c`, never `8d4a07c`) and the two-source predicate as consolidated by
  this task; no stale `SKILL.md:107` / `SKILL.md:304` / `state-layout.md:38`
  line reference remains.
- `docs/developers-guide.md` §"Done predicate (`novel-done`)" presents the
  clause table as authoritative and contains no pointer into the removed
  pseudocode; the §580-586 note attributes the manifest reconciliation to
  3.1.1.1 (or stays silent on attribution), never to 6.2.3.

Quality criteria (what "done" means):

- Tests: no new or changed tests (documentation-only). The existing `novel-done`
  suites continue to pass under `make all`.
- Markdown gates (the gates that decide this task): `make markdownlint` and
  `make nixie` pass on every edited file (AGENTS.md:97-98, 169-172).
- Regression: `make all` (`build check-fmt lint typecheck test`,
  `Makefile:28`) passes. This is a regression check, not the Markdown gate.

Quality method (how we check): run `make fmt` then the targeted Markdown gates
after each file edit, the scoped `grep` assertions above, and `make all` once
at the end as a regression check.

## Idempotence and recovery

Every step is a Markdown edit and is safely re-runnable. If a `markdownlint` or
`nixie` failure appears, re-edit the offending file and re-run the gate;
nothing is destructive and no state is written outside the working tree. If
`make all` surfaces an unrelated pre-existing failure, leave the docs commits
in place and escalate with the gate output rather than working around it.

## Artifacts and notes

Evidence captured during planning:

- `git merge-base --is-ancestor 8d4a07c HEAD` returns non-zero;
  `git branch -a --contains 8d4a07c` lists only `skill-turn-around` — `8d4a07c`
  is **not** on this branch. Do not cite it.
- `git log -L 106,107:skill/novel-ralph/SKILL.md` shows commit `916313c`
  changed `SKILL.md` drafting prose "Phase 7" → "Phase 8" — the real provenance
  of the already-landed phase-mislabel correction.
- `grep -n "plan\.md" skill/novel-ralph/references/state-layout.md` returns
  nothing; the per-chapter `plan.md` entry is already gone (also `916313c`).
- `docs/novel-ralph-harness-design.md:774-792` still records all three defects
  as open and cites stale line numbers — this is the §8 record Work Item 1
  reconciles.
- `skill/novel-ralph/references/done-conditions.md:157-160` already iterates the
  manifest (`state["chapters"]`); roadmap 3.1.1.1 (`docs/roadmap.md:925-934`,
  `[x]`) performed that reconciliation. The dev-guide §580-586 note is
  therefore already stale independent of this task.
- `docs/developers-guide.md:562-564` ties the clause truth conditions to the
  `done-conditions.md` `novel_predicate` body — the reference Work Item 3
  repoints when Work Item 2 removes the pseudocode.
- `docs/novel-ralph-harness-design.md:332-333`: "`novel-done` is the done
  predicate as code, replacing the pseudocode in `done-conditions.md`" — the
  mandate for the consolidation.
- `Makefile:28`: `all: build check-fmt lint typecheck test` — `make all` does
  not run markdownlint, nixie, or audit (`Makefile:104,108,111`).

## Interfaces and dependencies

No code interfaces change. The documentation contract after this plan is:

- `novel-done` (console-script; `novel_ralph_skill/commands/_novel_done.py`,
  engine `novel_ralph_skill/state/done_predicate.py`) is the sole evaluator of
  the novel-level done predicate.
- `docs/developers-guide.md` §"Done predicate (`novel-done`)" holds the
  authoritative six-clause table with disk sources.
- `skill/novel-ralph/SKILL.md` and
  `skill/novel-ralph/references/done-conditions.md` carry pointers to the
  above, no clause logic of their own at the novel level.

## Revision note

Revised in planning round 2 to resolve the design reviewer's four blocking
points:

1. **Wrong provenance / false chronology.** All references to commit `8d4a07c`
   are removed. The phase-mislabel and `plan.md` corrections are now attributed
   to the verified provenance commit `916313c` (proven by
   `git log -L 106,107:...SKILL.md` and
   `git merge-base --is-ancestor 8d4a07c HEAD` returning non-zero). Work Item 1
   and the §8 edit cite `916313c` (or no SHA), never `8d4a07c`. Purpose,
   Surprises, Decision Log, Risks, and Artifacts updated accordingly.
2. **Unachievable success grep.** The success criterion is scoped to
   `grep -rn "novel_predicate" skill/` (Constraints 5-6). The closed-work
   records in `docs/roadmap.md:929,937` and `docs/execplans/roadmap-3-1-1*.md`
   are declared out of scope and explicitly must not be edited. Concrete steps
   and Validation use the scoped grep.
3. **`make all` gate description.** A new "Toolchain note" pins `make all` to
   `Makefile:28` (`build check-fmt lint typecheck test`) and states it does
   **not** run markdownlint/nixie/audit. The Markdown gates
   (`make markdownlint`, `make nixie`) are the gates that decide a `.md`-only
   change per AGENTS.md:97-98,169-172; `make all` is a regression check only.
   Purpose, Risks, Concrete steps, and Validation corrected.
4. **Manifest-reconciliation rationale.** Work Item 3 and the Decision
   Log/Surprises now state the manifest reconciliation was performed by roadmap
   **3.1.1.1** (closed), not 6.2.3; `done-conditions.md:157-160` already
   iterates the manifest. The §580-586 dev-guide note is recorded as already
   stale independent of this task, and the implementer is forbidden from
   writing a narrative attributing that reconciliation to 6.2.3.
