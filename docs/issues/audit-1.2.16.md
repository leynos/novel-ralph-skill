# Post-merge audit — roadmap task 1.2.16

Task 1.2.16 swept `docs/users-guide.md` and `docs/developers-guide.md` to the
single `novel` multiplexer surface, closing the user- and developer-guide gap
that audit `audit:1.2.13` flagged and that task 1.2.14's narrower wording had
left untracked. The sweep is gated behind 1.2.15 (which actually retired the
legacy five console-scripts), so the prose flips only once the scripts were
gone.

This audit reviews the merged state at `origin/main` (commit `5191087`) for
refactoring opportunities, duplication, inconsistencies, separation-of-concerns
and CQS issues, and gaps in documentation and tests. Each finding records a
location and a concrete proposed fix.

The most material finding is that 1.2.16's **sibling** task — the equivalent
sweep of `docs/novel-ralph-harness-design.md` and `skill/novel-ralph/SKILL.md`
— was never performed, and the roadmap item that should track it is both
unchecked and structurally orphaned. The two guides 1.2.16 itself owns are
clean; the gap is wholly in the untouched siblings.

## 1. Design doc and SKILL.md still present the retired hyphenated surface

- **Category:** docs-gap
- **Severity:** high
- **Location:** `docs/novel-ralph-harness-design.md` (44 occurrences, e.g.
  lines 56-58 Mermaid nodes, 112, 115, 121-123, 242-243, 340, 388, 506, 805,
  884-921); `skill/novel-ralph/SKILL.md` (23 occurrences, e.g. lines 28-31, 40,
  63, 100, 118, 327, 345, 351, 460-462, 487, 491, 523-529, 606)

Task 1.2.15 retired the five standalone console-scripts (`novel-state`,
`novel-done`, `novel-compile`, `desloppify`, `wordcount`); only the `novel`
multiplexer ships on `PATH`. Yet the design document and `SKILL.md` still
describe and *invoke* the retired hyphenated surface throughout their live
prose. The harm is concrete, not cosmetic:

- `SKILL.md` §Setup (lines 28-39) tells the operator "The deterministic harness
  is five console-scripts — `novel-state`, `novel-done`, `novel-compile`,
  `desloppify`, and `wordcount`" and then runs `novel-state --version` to
  "confirm the install resolves". That command no longer exists; following the
  Setup section verbatim fails at the first verification step. `SKILL.md` is the
  authoritative entry point an agent loads to drive the harness, so this is a
  functional defect, not a stale aside.
- The design document's command table (§ lines 242-243), the envelope examples
  (`"command": "novel-done"`, lines 148, 358), and the test-anchor prose
  (884-921) all name commands the package no longer binds.

This work *was* scoped: task 1.2.14's success criterion (roadmap lines 296-298)
reads "no `novel-state`/`novel-done`/`novel-compile`/`desloppify`/`wordcount`
console-script reference survives in the design or `SKILL.md`". The
`audit:1.2.15` issue file (`docs/issues/audit-1.2.15.md`, lines 15-19)
explicitly held these references out of scope as "tracked by roadmap tasks
1.2.14 and 1.2.16, which are gated behind 1.2.15 and not yet done". 1.2.16 has
now landed; 1.2.14's targets remain untouched. `git log -- docs/novel-ralph-
harness-design.md skill/novel-ralph/SKILL.md` confirms no commit has ever swept
either file from the `novel-x` form to the `novel x` form.

- **Proposed fix:** execute the 1.2.14 sweep. Rewrite every command-invocation
  reference in `docs/novel-ralph-harness-design.md` and
  `skill/novel-ralph/SKILL.md` from the hyphenated `novel-x` form to the spaced
  `novel x` form (`novel-state check` -> `novel state check`, `novel-done` ->
  `novel done`, `novel-compile` -> `novel compile`, the bare `desloppify`/
  `wordcount` script names -> `novel desloppify`/`novel wordcount`), including
  the Mermaid nodes (lines 56-58), the envelope `"command"` example values, and
  the `SKILL.md` Setup section's `uv tool install` verification (use
  `novel --version`). Reconcile the surrounding prose for truthfulness, exactly
  as 1.2.16 did for the guides — the present-tense "the harness is five
  console-scripts" framing must go. Re-run `make markdownlint` and `make nixie`
  on the edited docs.

## 2. Reference files under `skill/novel-ralph/references/` carry stale command names

- **Category:** docs-gap
- **Severity:** medium
- **Location:** `skill/novel-ralph/references/state-layout.md` (14 occurrences,
  e.g. lines 118, 190, 214, 217, 237, 239, 256-260);
  `skill/novel-ralph/references/done-conditions.md` (lines 17-18, 141, 144-145);
  `skill/novel-ralph/references/critic-personas.md` (lines 131, 133)

The `references/` files the skill loads on demand share the same defect as
finding 1 but are not named by *any* roadmap success criterion: 1.2.14 lists
only "the design and `SKILL.md`", and 1.2.16 lists only the two guides. These
files invoke retired commands directly — `state-layout.md` line 118 "written
only by `novel-state set-chapters`", line 190 "`novel-state check` requires",
line 239 "`novel-compile` follows"; `done-conditions.md` line 17 "running the
`novel-done` command. If it exits 0"; `critic-personas.md` line 131 "The
`novel-done` checker reads `critic-notes.md`". An agent that follows a reference
to its cited command will reach for a binary that is no longer installed.

These are distinct from the legitimate generic-verb uses of "desloppify" as a
noun for the pass (e.g. `state-layout.md` line 167 "run desloppify",
`SKILL.md` line 87), which are not command invocations and need no change.

- **Proposed fix:** fold these reference files into the same hyphenated-to-
  spaced sweep as finding 1, so the whole `skill/novel-ralph/` tree — not just
  `SKILL.md` — describes the shipped `novel <sub>` surface. Distinguish the
  command-invocation references (rewrite) from the noun-form "desloppify" pass
  references (leave). If the sweep is scoped per-roadmap-task, the
  remediation item must name `skill/novel-ralph/references/` explicitly, because
  no existing success criterion reaches them.

## 3. The 1.2.14 roadmap item is unchecked and structurally orphaned

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `docs/roadmap.md:291-298`

The roadmap text that defines the 1.2.14 work — "Update the design prose and
diagrams and `SKILL.md` … from the `novel-x` form to the `novel x` form" with
its own `Requires 1.2.15`, `See …`, and `Success:` sub-bullets — sits at lines
291-298 as a continuation of task **1.2.15.1**'s bullet list, not as a numbered,
checkboxed task of its own. There is no `- [ ] 1.2.14.` (or `- [x] 1.2.14.`)
line anywhere in the roadmap, yet two other places reference "task 1.2.14" as a
real tracked item (line 281 "the production-module-name scope that tasks
1.2.14/1.2.16 cover"; line 301 "Task 1.2.14's wording and success criterion").
Because the block has no checkbox, the build workflow can neither select it as
unblocked work nor mark it done; its completion state is invisible. This is how
finding 1 escaped — the work was specified but never given a trackable home, so
1.2.16 (its sibling) was completed while 1.2.14 silently lapsed.

- **Proposed fix:** promote lines 291-298 to a first-class, unchecked roadmap
  task `- [ ] 1.2.14. Sweep the design document and SKILL.md to the novel
  multiplexer surface.` at the correct sibling indentation (peer of 1.2.13,
  1.2.15, 1.2.16), with the existing `Requires`/`See`/`Success` bullets nested
  under it, and extend its scope and success criterion to cover
  `skill/novel-ralph/references/` (finding 2). Adding the item to the roadmap is
  the root agent's prerogative; this audit proposes it only.

## 4. The success criterion that should have caught finding 1 is unenforced

- **Category:** test-gap
- **Severity:** medium
- **Location:** `tests/` (no doc-prose guard); cf.
  `tests/test_legacy_surface_retired.py` (which scans only source and test
  files, not docs)

`test_legacy_surface_retired.py` is the durable guard that the retired
hyphenated *literals* do not creep back into `tests/` and
`novel_ralph_skill/`, but it deliberately does not scan `docs/` or `skill/`.
Nothing in the suite enforces the 1.2.14/1.2.16 success criterion — "no
`novel-state`/… console-script reference survives" — against the documentation
tree. The result is finding 1: 44 + 23 stale references sit on `main` with the
spawning task marked structurally complete and no test failing. Documentation
correctness here is load-bearing (the agent reads `SKILL.md` to drive the
harness), so it deserves the same regression discipline as the code surface.

- **Proposed fix:** add a documentation-prose guard — either extend
  `test_legacy_surface_retired.py` with a doc-tree scan, or add a sibling test —
  that asserts no hyphenated console-script *invocation* (`novel-state`,
  `novel-done`, `novel-compile`, and the bare-name `desloppify`/`wordcount` used
  as commands) survives in `docs/**/*.md` and `skill/**/*.md`. Allow the
  documented historical-provenance and noun-form exceptions narrowly (e.g. ADR
  transition notes, the "desloppify pass" noun) via an explicit allowlist so the
  guard reflects intent rather than blanket-banning the substring. This converts
  the 1.2.14/1.2.16 success criteria from prose aspirations into enforced
  invariants.

## 5. Project-wide `-ise`/`-isation` spelling diverges from the stated Oxford `-ize` convention

- **Category:** inconsistency
- **Severity:** low
- **Location:** repository-wide; e.g. `docs/adr-002-toml-round-trip-tomlkit.md`
  (`serialiser`, `serialise`), `docs/adr-008-chapter-manifest-mutator.md:117`
  (`materialise`), `skill/novel-ralph/SKILL.md:114,122,261,367` (`initialise`,
  `summarising`, `recognise`, `realisation`),
  `skill/novel-ralph/references/critic-personas.md:9` (`maximise`, `minimise`),
  `docs/users-guide.md:228` (`initialised`)

The harness build instructions stipulate en-GB Oxford spelling — `-ize`/`-yse`/
`-our`. The documentation and skill corpus instead uses the `-ise`/`-isation`
British variant uniformly (serializer, materialize, initialize, summarize,
recognize, realization, maximize, minimize, capitalization, and so on). The
corpus is internally consistent in the `-ise` form, so this is a single
convention mismatch rather than scattered typos, and it predates 1.2.16 — the
1.2.16 sweep correctly matched the surrounding `-ise` house style rather than
introducing a third variant. Recording it so the convention is settled
deliberately rather than by drift.

- **Proposed fix:** decide the convention once and apply it tree-wide. If the
  Oxford `-ize` rule stands, run a controlled sweep converting the `-ize`-class
  words (serialize, materialize, initialize, summarize, recognize, realization,
  maximize, minimize, capitalization, …) while leaving the always-`-ise` words
  (advise, comprise, exercise, premise, supervise, revise, …) and `-yse`/`-our`
  forms untouched, then add a lint or spell-check rule to hold the line. If the
  project intends `-ise`, update the build instruction so the stated convention
  matches the corpus. Either way, remove the latent ambiguity; do not leave it
  to each task's author to guess.
