# Align `no_unresolved_blockers` to the real `critic-personas.md` format and define the resolution producer contract

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT

## Purpose / big picture

The `novel-done` checker is the harness terminator: every turn it reads
`state.toml` and the `working/` tree and exits `0` only when all six §4.2 done
clauses hold (`skill/novel-ralph/references/done-conditions.md`, "Novel-level
predicate"). One clause, `no_unresolved_blockers`, is supposed to keep the loop
running while any chapter's spiteful-critic notes still carry an unaddressed
BLOCKER finding.

Today that clause is unsound against real input. The recogniser
(`novel_ralph_skill/state/done_predicate.py:276-296`) treats a
`critic-notes.md` line as an unresolved BLOCKER only when its *stripped text
starts with* the bare word `BLOCKER` and does *not end with* a trailing
`[resolved]` token. But the producer — the spiteful critic, whose strict output
format is fixed in `skill/novel-ralph/references/critic-personas.md:81-104` —
never writes such a line. It writes a `## BLOCKER` **section heading** followed
by `### B1 — <label>` **finding headings**, each with a quoted passage, a
`What's wrong:` line and a `Suggested action:` line. No emitted line's stripped
text starts with `BLOCKER` (the heading stripped is `## BLOCKER`, which starts
with `##`; the findings start with `### B`). The clause therefore matches **zero
lines** and reads `True` — clean — against genuine unresolved critic output.
This is the exact exit-`0` lie the clause exists to prevent, and it is *strictly
larger* than the mid-line false-clean edge roadmap 3.1.4 closed, because it
fires on **every** real unresolved blocker, not a near-miss. Worse, no reference
anywhere tells the loop how to *mark* a blocker resolved: the `[resolved]`
trailing token is invented by the predicate and its corpus, never by the
producer's spec (audit-3.1.4 Finding 1, severity high).

After this change a reader can drop a real critic-personas-shaped
`critic-notes.md` — a `## BLOCKER` section with a live `### B1 — …` finding —
into a chapter directory, run `novel-done`, and see it exit `1` with
`no_unresolved_blockers` reported false; mark that finding resolved using the
**documented** convention and see `novel-done` exit `0`. The convention is
written once, in `critic-personas.md` and `done-conditions.md`, so the side that
*writes* notes and the side that *reads* them share one contract.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. `novel-done` is a read-only checker. `evaluate_done` and every clause helper
   must write nothing to disk on any path (ADR-001;
   `docs/novel-ralph-harness-design.md` §3.3 puts `novel-done` in the read-only
   column). The change is in-memory line classification only.
2. The fault boundary (ExecPlan term **D-FAULT**, established by roadmap 3.1.1
   and documented in `done_predicate.py:26-39`) is preserved: an *absent*
   `critic-notes.md` is a benign clean clause (`FileNotFoundError` absorbed);
   every other read fault (`PermissionError`, `UnicodeDecodeError`) propagates
   unchanged for the command layer to route to exit `3`. The new grammar must
   not swallow or introduce a fault.
3. The six clause names and their design §4.2 JSON order
   (`done_predicate.py:104-109`) are fixed. This task changes only *how*
   `no_unresolved_blockers` is computed, never the clause set, its order, or the
   envelope shape.
4. The chapter set is the manifest (`state.chapters`), not an outline parse —
   the deliberate design §4.3-justified divergence recorded as D-CLAUSES. This
   task does not touch chapter iteration.
5. The corpus oracle twin
   (`tests/working_corpus/_done_predicate_oracle.py`) must **not** import the
   production recogniser; it re-spells the rule independently and a corpus test
   pins the two equal on every `novel-done` tree (the invariant-validation twin
   policy, developers-guide "Shared test scaffolding"). When the production rule
   changes, the twin changes in the same commit.
6. en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
   commit messages (AGENTS.md). Markdown obeys
   `docs/documentation-style-guide.md`.
7. No code file exceeds 400 lines (AGENTS.md). `done_predicate.py` is currently
   351 lines; the parser additions must stay within budget or move helper logic
   to a small sibling module (see Risk R-FILESIZE).

## Tolerances (exception triggers)

Stop and escalate, recording the trigger in the Decision Log, when any holds:

- Scope: implementation touches more than 8 files or exceeds ~400 net changed
  lines across production and tests.
- Interface: any change to the `DoneClauses` shape, the clause set/order, the
  `novel-done` envelope JSON, or any public function signature outside
  `done_predicate.py`'s private helpers.
- Dependencies: any new third-party dependency is required (none is expected;
  the recogniser is pure `str`/`pathlib`).
- Producer-contract ambiguity: if, while drafting the resolution convention, two
  materially different conventions are equally defensible *and* the choice
  changes the recogniser grammar, stop and present both with trade-offs rather
  than picking silently. (The plan pins one convention in the Decision Log as
  D-BLOCKER-FORMAT; this tolerance covers a discovery that contradicts it.)
- Iterations: tests still red after 3 focused attempts on one work item.
- File size: `done_predicate.py` would exceed 400 lines and the logic cannot be
  cleanly relocated (R-FILESIZE).

## Risks

- Risk: the recogniser must distinguish a *live* `### Bn` finding from a
  *resolved* one and from the literal convergence sentinel
  `No BLOCKER. No MAJOR.` (critic-personas.md:116-118). A naive "any `### B`
  line under `## BLOCKER`" rule could misread the sentinel or a heading-only
  section.
  Severity: high · Likelihood: medium
  Mitigation: pin the grammar in W1 with explicit unit + property tests for the
  sentinel, an empty `## BLOCKER` section, and a live finding; the convergence
  case never writes a `## BLOCKER` heading at all (the critic writes the
  sentinel *instead*), so it is clean by construction.

- Risk: silent scope creep into case-insensitive / alternative-spelling variants
  (`RESOLVED`, `(resolved)`), which D-BLOCKER-SCOPE (roadmap 3.1.4) left out of
  scope in both directions.
  Severity: medium · Likelihood: medium
  Mitigation: the roadmap entry *folds in* that deferred decision — W1 records
  the explicit case/variant decision in the Decision Log and pins it with an
  asserting-current-behaviour test (audit-3.1.4 Finding 3), rather than silently
  widening the grammar.

- Risk: the producer convention I document is one the loop cannot actually emit
  or honour, leaving the contract decorative.
  Severity: medium · Likelihood: low
  Mitigation: W0 verifies the convention against how SKILL.md drives the critic
  loop (`SKILL.md:341-367`) — notes are overwritten each pass and convergence is
  the sentinel — before any code changes; the resolution token is chosen to sit
  on the existing `### Bn` heading line the producer already writes.

- Risk (R-FILESIZE): the heading-aware parser pushes `done_predicate.py` past the
  400-line ceiling.
  Severity: low · Likelihood: medium
  Mitigation: keep the parser to two small pure helpers; if the ceiling is
  threatened, relocate the line/section classification into a new
  `novel_ralph_skill/state/_blocker_notes.py` and re-export, mirroring the
  `_disk_paths` split. Decide in W1, record as D-BLOCKER-MODULE.

- Risk (R-TWIN-DRIFT): the oracle twin and production rule drift if updated in
  separate commits.
  Severity: low · Likelihood: low
  Mitigation: W3 updates both in the same commit; `test_blocker_oracle_twin_agrees`
  gates it.

## Progress

- [x] W0 — Verify the producer loop and pin the resolution convention (no code).
  All three facts confirmed; no contradiction with D-BLOCKER-FORMAT. The critic
  writes `## BLOCKER` then `### B1 — …` and the literal `No BLOCKER. No MAJOR.`
  on convergence (`critic-personas.md:83-92,116-118`). `critic-notes.md` is
  overwritten each pass (`SKILL.md:362` "The critic's findings reset each
  pass."). Nothing instructs the loop to mark a finding resolved today, so the
  convention is additive (audit-3.1.4 Finding 1).
- [x] W1 — Define the BLOCKER resolution convention in `critic-personas.md` and
  `done-conditions.md`; record the format and case/variant decisions. Added a
  "Resolving a BLOCKER" subsection to `critic-personas.md` (heading-based
  format, trailing `[resolved]` token with no trailing text, sentinel clean by
  construction, case/variant out of scope) and rewrote the `done-conditions.md`
  consumer note to match. `make markdownlint`, `make nixie`, and `make all`
  green; coderabbit 0 findings. Commit `0cb41e9`.
- [x] W2 — Realign the recogniser in `done_predicate.py` to the heading-based
  format plus the documented resolution token; update unit + property tests.
  See Decision Log D-BLOCKER-MODULE (relocated) and Surprises (W2/W3 folded).
- [x] W3 — Update the corpus specs, the oracle twin, and the corpus/BDD/snapshot
  trees to drive the clause clean and dirty from real critic-personas-shaped
  output. Folded into the W2 commit (see Surprises & discoveries) because the
  recogniser cannot land `make all`-green without the corpus realignment.
- [x] W4 — Update `developers-guide.md` (and §4.2 status note) to the new
  grammar; run the markdown gates. Rewrote "The BLOCKER format" to the
  heading-based grammar, naming all three documented edges (case/variant out of
  scope per D-BLOCKER-CASE, trailing text forbidden per D-BLOCKER-TRAILING — the
  third edge audit-3.1.4 Finding 2 asked for, the false-dirty near-miss). Added
  a roadmap-3.1.5 note to the design §4.2 status block superseding the 3.1.4
  prefix description. Verified no stale "starts with `BLOCKER`" grammar survives
  outside historical audit records and the roadmap's own task description.
  `make markdownlint`, `make nixie`, and `make all` green.

## Surprises & discoveries

- Deviation: W2 and W3 were committed **together** as one atomic commit rather
  than as two. The recogniser realignment (W2) makes every existing corpus note
  body (the old `BLOCKER …` strings) read clean under the new grammar, so the
  W2-only tree would leave `test_failers_each_break_exactly_one_clause`,
  `test_blocker_edges`, `test_blocker_oracle_twin_agrees`, and two BDD scenarios
  red — i.e. `make all` could not be green at a W2-only commit. The per-work-item
  deterministic-gate rule (each commit `make all`-green) therefore requires the
  corpus + oracle twin + BDD to change in the same commit, which also satisfies
  R-TWIN-DRIFT (twin and production never drift across commits). Recorded here
  rather than silently merging the work items.

- Surprise: `make fmt` runs `mdformat` across **all** Markdown and is not
  idempotent against the repo's existing prose, reflowing ~135 unrelated files.
  The Markdown gate is `make markdownlint` (+ `make nixie`), not `make fmt`; the
  `make all` formatting check is `ruff format --check` (Python only). Action: do
  not run `make fmt`; the unwanted churn was stashed off. This matches a long
  trail of prior "spurious make-fmt mdformat churn" stashes on earlier branches.

- Observation: `ChapterSpec.critic_notes` already writes a verbatim
  `critic-notes.md`, so the corpus can carry full critic-personas-shaped bodies
  with no builder change.
  Evidence: `tests/working_corpus/_specs.py:99-119`;
  `tests/working_corpus/_builder.py:166-182`.
  Impact: W3 changes only the note *strings* and their oracle, not the builder.

- Observation: this clause is a pure `str`/`pathlib` predicate with no cuprum,
  subprocess, or external-library dependency; the command layer's only external
  import is `cyclopts` for CLI dispatch, untouched here.
  Evidence: `grep` of `done_predicate.py`/`compile_model.py` finds no
  `cuprum`/`subprocess`; `_novel_done.py:56` imports `cyclopts` solely for the
  app object.
  Impact: the locked-library research the task brief asks for (cuprum catalogue
  APIs, Cyclopts `--help`/`--version`, pytest-timeout under xdist, `uv run`
  resolution) is **not load-bearing** for any work item here. No external library
  behaviour is relied upon; the plan pins every behavioural claim with a test
  instead. This is recorded so the implementer does not chase a non-existent
  cuprum surface.

## Decision log

- Decision (D-BLOCKER-FORMAT): an *unresolved* BLOCKER is a `### Bn` **finding
  heading** that appears under a `## BLOCKER` **section heading** and is not
  marked resolved. "Under" means: at or after a line whose stripped text equals
  `## BLOCKER`, and before the next `##`-level section heading. A finding heading
  is a line whose stripped text matches `### B<digits>` (the critic's strict
  format uses `B1`, `B2`, …; `critic-personas.md:83-92`). Resolution is marked by
  appending the documented `[resolved]` token to the *finding heading line*
  (`### B1 — <label> [resolved]`). The token stays a *trailing* marker so the
  3.1.4 positional soundness (an incidental mid-line mention does not clear the
  finding) carries over verbatim.
  Rationale: this matches the format the producer is actually specified to emit
  (`critic-personas.md:81-104`), keeps resolution an explicit, greppable,
  positional marker (so the cap-reached "log unresolved findings" case,
  `done-conditions.md:134-138`, and the corpus can mark a finding closed without
  deleting it), and reuses the trailing-token discipline 3.1.4 already proved
  sound. The bare-`BLOCKER`-prefix grammar 3.1.4 hardened a format the producer
  never writes (audit-3.1.4 Finding 1) and is removed.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-SENTINEL): the convergence sentinel `No BLOCKER. No
  MAJOR.` (critic-personas.md:116-118) is clean by construction — the critic
  writes it *instead of* a `## BLOCKER` section, so there is no `## BLOCKER`
  heading and the recogniser finds no findings. A pinned test asserts this.
  Rationale: avoids a special-case in the parser; the absence of the section is
  the resolution signal for the convergence path.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-CASE): case- and alternative-spelling variants of the
  resolution token (`[RESOLVED]`, `(resolved)`) and of the headings remain *out
  of scope*, matching D-BLOCKER-SCOPE (roadmap 3.1.4). The recogniser stays
  case-sensitive on `## BLOCKER`, `### B<n>`, and `[resolved]`. W1 records this
  and W2 pins it with an asserting-current-behaviour test (audit-3.1.4 Finding
  3) so a future "fix" cannot silently flip it.
  Rationale: the roadmap entry asks to *fold in* the deferred case/variant
  decision, not to widen the grammar; a documented, test-pinned limitation is
  the honest discharge.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-TRAILING): trailing text after the marker on a finding
  heading (`### B1 — label [resolved] (see log 42)`) is *forbidden* by the
  convention and therefore treated as **unresolved** by design, closing
  audit-3.1.4 Finding 2's false-dirty direction by ruling it out at the producer
  rather than relaxing the recogniser. W1 states this in the convention; W2 pins
  it with a test.
  Rationale: the convention owns the producer; a forbidden shape needs no
  recogniser tolerance. Keeps the positional rule simple and the contract
  single-sided.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-MODULE): keep the parser in `done_predicate.py` if it
  stays under 400 lines after W2; otherwise relocate the line/section
  classification to `novel_ralph_skill/state/_blocker_notes.py`. Decide during
  W2 against the actual line count and record the outcome here.
  Rationale: AGENTS.md 400-line ceiling (Constraint 7).
  Date/Author: 2026-06-24, planning agent.
  Outcome (2026-06-24, implementing agent): **relocated.** With both pure
  helpers inline, `done_predicate.py` reached 407 lines, over the ceiling. The
  two helpers (`_line_is_unresolved_blocker_finding`, `_body_has_unresolved_blocker`)
  and the four heading/token constants moved to the new
  `novel_ralph_skill/state/_blocker_notes.py` (91 lines), mirroring the
  `_disk_paths` split; `done_predicate.py` imports `_body_has_unresolved_blocker`
  and is now 336 lines. The unit/property tests import
  `_line_is_unresolved_blocker_finding` from the sibling module, and the oracle
  twin re-spells the grammar independently (it imports nothing from production).

## Outcomes & retrospective

To be completed at the close of each work item and at task completion. Compare
against the Purpose: a real critic-personas-shaped unresolved blocker must drive
`novel-done` to exit `1`, and the documented resolution convention must drive it
to exit `0`, with the contract written once and shared by producer and consumer.

Outcome (2026-06-24, implementing agent): Purpose met. The recogniser now parses
the real `## BLOCKER`/`### Bn` structure (`_blocker_notes.py`); a live `### B1`
finding under `## BLOCKER` drives `no_unresolved_blockers` false (the headline
exit-code flip pinned by `test_no_unresolved_blockers_clean_and_blocking` and the
new `a live B1 finding …` BDD scenario, exit `1`), and a trailing
space-then-`[resolved]` token clears it (exit `0`). The convention is written
once in `critic-personas.md` ("Resolving a BLOCKER") and `done-conditions.md`,
shared by producer and consumer. Two atomic commits: `0cb41e9` (W0/W1
references), `c004265` (W2/W3 recogniser + corpus + oracle twin + BDD); W4 docs
follow. `make all` green throughout; coderabbit `0` findings on each run.
Deviations: W2/W3 folded into one commit (deterministic-gate coupling, also
satisfying R-TWIN-DRIFT); D-BLOCKER-MODULE relocated the parser to a sibling
module (407-line ceiling breach); the BLOCKER unit/property cases moved to
`test_done_predicate_blockers.py` (module-line cap). All recorded above.

## Context and orientation

A novice should be able to navigate from these paths alone.

Production:

- `novel_ralph_skill/state/done_predicate.py` — the pure six-clause predicate
  engine. The relevant symbols: module constants `_BLOCKER_PREFIX`,
  `_RESOLVED_TOKEN` (lines 71-74); the private `_contains_unresolved_blocker`
  (276-296) that reads one `critic-notes.md` and applies the line rule; and the
  public `no_unresolved_blockers(state, working_dir)` (299-312) that scans every
  manifest chapter. `evaluate_done` (315-350) assembles the six clauses.
- `novel_ralph_skill/commands/_novel_done.py` — the command layer that maps
  `DoneClauses` to exit codes and the envelope. Untouched by this task (the
  clause set and exit semantics are unchanged); only the *meaning* of the
  `no_unresolved_blockers` boolean changes.

References (source of truth — must be edited):

- `skill/novel-ralph/references/critic-personas.md` — the spiteful critic's
  system prompt and strict output format. Lines 81-127 fix the `## BLOCKER` /
  `### Bn` format and the `No BLOCKER. No MAJOR.` convergence sentinel. This file
  defines the *producer*; W1 adds the resolution convention here.
- `skill/novel-ralph/references/done-conditions.md` — the done predicate at
  three scales. Lines 111, 134-138 (the cap-reached "log unresolved findings"
  case) and 191-195 (the current `[resolved]` trailing-token note) describe the
  *consumer*; W1 rewrites lines 191-195 to the new contract and cross-links the
  convention.
- `skill/novel-ralph/SKILL.md:341-367` — how the loop drives the critic
  (overwrites notes each pass; converges on the sentinel). Read-only context for
  W0; confirms the convention is emittable.

Design / docs:

- `docs/novel-ralph-harness-design.md` §4.2 (lines 308-368) — the `novel-done`
  spec and the implementation-status block (lines 310-322) whose 3.1.4 note W4
  extends.
- `docs/developers-guide.md` lines 571-583 ("The BLOCKER format") — the internal
  description W4 rewrites.
- `docs/issues/audit-3.1.4.md` — Findings 1 (the headline this task closes), 2
  (false-dirty trailing text, closed by D-BLOCKER-TRAILING), 3 (case/variant
  test gap, closed by D-BLOCKER-CASE).
- `docs/scripting-standards.md`, `AGENTS.md` — quality gates and prose rules.

Tests (the `tests/` tree; AGENTS.md keeps all pytest tests here):

- `tests/test_done_predicate.py:241-330` — the unit + Hypothesis tests for the
  clause: clean/blocking, resolved, incidental-mid-line, the positional property
  `test_blocker_resolution_is_positional`, and the undecodable-propagates fault
  test.
- `tests/working_corpus/_done_predicate_specs.py:60-177` — the note-body string
  constants and the trees that exercise the clause (`RESOLVED_BLOCKER_NOTE`,
  `UNRESOLVED_BLOCKER_NOTE`, `NEAR_MISS_BLOCKER_NOTE`,
  `INCIDENTAL_RESOLVED_BLOCKER_NOTE`, and the `DONE_PREDICATE_*` specs).
- `tests/working_corpus/_done_predicate_oracle.py:36-85` — the independent
  oracle twin (`_BLOCKER_PREFIX`/`_RESOLVED_TOKEN`, `_notes_has_unresolved_blocker`,
  `no_unresolved_blockers`).
- `tests/test_working_corpus_done_predicate.py:90-145` — `test_blocker_edges`
  and `test_blocker_oracle_twin_agrees`.
- `tests/features/novel_done.feature:30-34` and
  `tests/steps/novel_done_steps.py:100-122` — the BDD incidental-resolved
  scenario.
- `tests/test_novel_done_snapshots.py` — the machine-mode envelope snapshot
  (clause keys at 37-44); no BLOCKER-specific snapshot today.

Term definitions:

- **§1.3.2 corpus tree**: house shorthand for a `WorkingTreeSpec` added to
  `tests/working_corpus/_done_predicate_specs.py`, materialised by the corpus
  builder, cross-checked by an independent oracle twin, and asserted in
  `tests/test_working_corpus_done_predicate.py` (used the same way by roadmap
  3.1.4, see `docs/execplans/roadmap-3-1-4.md`).
- **Recogniser**: the pure predicate that classifies a `critic-notes.md` body as
  carrying an unresolved BLOCKER or not.

## Plan of work

Stages map to the work items. Each ends with validation and is independently
committable and gate-passable.

### W0 — Verify the producer loop and pin the convention (Stage A: understand, no code)

Read, do not edit: `skill/novel-ralph/SKILL.md:341-367`,
`skill/novel-ralph/references/critic-personas.md:81-145`, and
`skill/novel-ralph/references/done-conditions.md:111,134-145,191-195`. Confirm
the three facts the convention depends on and record them in the Decision Log if
any contradicts D-BLOCKER-FORMAT:

1. The critic writes `## BLOCKER` then `### B1 — …` findings, and writes the
   literal `No BLOCKER. No MAJOR.` when there are none
   (critic-personas.md:83-92, 116-118).
2. `critic-notes.md` is overwritten each pass (SKILL.md:366-367), so a resolved
   blocker normally *vanishes*; an explicit in-place `[resolved]` marker is only
   needed for the cap-reached "log unresolved findings" path
   (done-conditions.md:134-138) and for the corpus to mark a finding closed.
3. Nothing currently instructs the loop to mark a finding resolved (audit-3.1.4
   Finding 1) — so the convention is additive, not a redefinition.

Docs to read: SKILL.md, critic-personas.md, done-conditions.md, audit-3.1.4.md.
Skills to load: `python-router` (to route the later code work),
`logisphere-design-review` is *not* required at plan time.
Tests: none (no code). Validation: none beyond confirming the Decision Log is
consistent.

### W1 — Define the resolution convention in the references (Stage B: contract first)

Edit `skill/novel-ralph/references/critic-personas.md`: under the spiteful
critic's "Output format, strict" block (after line 104) or its "Rules" list, add
a short **"Resolving a BLOCKER"** subsection stating the convention from
D-BLOCKER-FORMAT, D-BLOCKER-TRAILING, and D-BLOCKER-CASE in prose:

- A blocker is identified by a `### Bn — <label>` finding under the `## BLOCKER`
  section.
- A finding is marked resolved by appending a space and then exactly
  `[resolved]` to its `### Bn — <label>` heading line, with **no trailing text
  after the token**.
- When the critic re-runs and the chapter has no blockers, it writes
  `No BLOCKER. No MAJOR.` and emits no `## BLOCKER` section (the normal
  resolution path; the in-place token is for the cap-reached logged case).
- Case and spelling variants of the token are not recognised (out of scope).

Edit `skill/novel-ralph/references/done-conditions.md` lines 191-195: replace the
current trailing-`[resolved]`-on-a-`BLOCKER`-prefixed-line note with the new
heading-based contract, cross-referencing critic-personas.md and naming this as
roadmap 3.1.5 / design §4.2. Keep the "absent notes file is clean" sentence.

Docs to read: critic-personas.md, done-conditions.md,
`docs/documentation-style-guide.md`. Skills to load: none (prose only); apply
`en-gb-oxendict` conventions by hand.
Tests: none — these are reference Markdown. The behavioural pinning lands in W2
and W3, which consume the convention.
Validation: `make markdownlint` and `make nixie` (Constraint 6; both pass).
Commit: reference-only change defining the producer contract.

### W2 — Realign the recogniser and its unit/property tests (Stage C: implementation)

Edit `novel_ralph_skill/state/done_predicate.py`:

- Replace the line-level rule. Introduce two small **pure** helpers (extracting
  the rule per audit-3.1.4 Finding 4 so the property test asserts over strings,
  not the filesystem):
  - `def _line_is_unresolved_blocker_finding(stripped: str) -> bool` — true when
    `stripped` matches a `### B<digits>` finding heading and does **not** end
    with a space-then-`[resolved]` token (trailing-only; D-BLOCKER-TRAILING).
    Pure `str -> bool`.
  - `def _body_has_unresolved_blocker(body: str) -> bool` — walks the lines,
    tracks whether the cursor is inside a `## BLOCKER` section (entered on a line
    whose stripped text equals `## BLOCKER`, left on the next `##`-level
    heading), and returns true when a finding line inside that section is
    unresolved.
  - `_contains_unresolved_blocker(notes_path)` keeps **only** the file-fault
    boundary (`FileNotFoundError` → `False`; everything else propagates;
    Constraint 2) and delegates to `_body_has_unresolved_blocker`.
- Update the module constants: keep `_RESOLVED_TOKEN = "[resolved]"` (still the
  trailing marker, now on the finding heading); replace `_BLOCKER_PREFIX` with
  the section/finding heading constants the new grammar needs
  (`_BLOCKER_SECTION = "## BLOCKER"`, plus the `### B<n>` finding match). Keep the
  `# noqa: S105` why-comment on the token.
- Refresh the module/`_contains_unresolved_blocker`/`no_unresolved_blockers`
  docstrings to describe the heading-based grammar and cite roadmap 3.1.5 and
  `critic-personas.md`.
- Decide D-BLOCKER-MODULE against the final line count; if relocating, create
  `novel_ralph_skill/state/_blocker_notes.py` with the two pure helpers and
  import them.

Edit `tests/test_done_predicate.py:241-330`. Replace the bare-`BLOCKER`-line
fixtures with critic-personas-shaped bodies and add the new edges:

- `test_no_unresolved_blockers_clean_and_blocking`: clean tree holds; a body with
  a `## BLOCKER` section and a live `### B1 — …` finding fails the clause.
- `test_resolved_blocker_is_clean`: a `### B1 — … [resolved]` finding under
  `## BLOCKER` holds.
- `test_convergence_sentinel_is_clean` (new): a body of exactly
  `No BLOCKER. No MAJOR.` holds (D-BLOCKER-SENTINEL).
- `test_finding_outside_blocker_section_is_clean` (new): a `### B1` line under a
  `## MAJOR` section (not `## BLOCKER`) does not fail the clause — the section
  scoping is load-bearing.
- `test_incidental_resolved_mention_stays_unresolved`: a live finding whose label
  quotes `[resolved]` mid-line stays unresolved (the 3.1.4 false-clean edge,
  re-expressed on the finding heading).
- `test_trailing_text_after_token_stays_unresolved` (new): `### B1 — label
  [resolved] (see log)` stays unresolved by design (D-BLOCKER-TRAILING;
  audit-3.1.4 Finding 2).
- `test_case_variant_token_stays_unresolved` (new): `### B1 — label [RESOLVED]`
  and `(resolved)` stay unresolved today (D-BLOCKER-CASE; audit-3.1.4 Finding 3),
  docstring citing the out-of-scope decision.
- Rewrite the Hypothesis property `test_blocker_resolution_is_positional` to call
  the extracted pure helper `_line_is_unresolved_blocker_finding` directly over
  generated finding-heading strings (no `TemporaryDirectory` per example),
  constructing valid inputs (a fixed `### B1 —` finding-heading prefix, an
  alphabet excluding `[`,
  `]`, and newlines, a fixed non-space sentinel after a mid-line token) so the
  property does not filter (the filtering trap; round-1 advisory A1 carried
  over). The invariant: the token's *trailing position* decides resolution; its
  mere presence does not.
- Keep `test_undecodable_critic_notes_propagates` green (the fault boundary is
  unchanged).

Docs to read: audit-3.1.4.md (Findings 1-4), critic-personas.md (the format),
the W1 convention. Skills to load: `python-router` → `python-testing` (pytest
fixtures/parametrize), `python-verification` then `hypothesis` (the positional
property is a genuine invariant over generated inputs, so Hypothesis is the
right adversary; CrossHair/mutmut are not needed — the rule is a small total
function, but the implementer may run `crosshair cover` on
`_line_is_unresolved_blocker_finding` as a coverage check if the property leaves
a branch unexercised).
Tests added/updated: the eight unit cases above plus the rewritten property, all
in `tests/test_done_predicate.py`. Each new behavioural case fails against the
pre-change recogniser (red) and passes after (green) — note in the Progress log
which cases were confirmed red first.
Validation: `make all` (build, check-fmt, lint, typecheck, test) green.
Commit: recogniser realignment plus its unit/property suite.

### W3 — Corpus, oracle twin, BDD, and snapshot from real critic output (Stage C cont.)

Edit `tests/working_corpus/_done_predicate_specs.py:60-177`: replace the four
note-body constants with critic-personas-shaped bodies —

- `RESOLVED_BLOCKER_NOTE`: a `## BLOCKER` section with `### B1 — … [resolved]`.
- `UNRESOLVED_BLOCKER_NOTE`: a `## BLOCKER` section with a live `### B1 — …`
  finding (quoted passage, `What's wrong:`, `Suggested action:` lines, matching
  the strict format so the corpus exercises the *real* shape).
- `NEAR_MISS_BLOCKER_NOTE`: a body that mentions resolution only in prose
  (`What's wrong: the author says this was resolved later`) under a live finding
  — stays unresolved (the false-dirty edge).
- `INCIDENTAL_RESOLVED_BLOCKER_NOTE`: a live finding whose label quotes
  `[resolved]` mid-line — stays unresolved (the false-clean edge,
  D-BLOCKER-POSITIONAL carried over).
- Add `CONVERGENCE_SENTINEL_NOTE = "No BLOCKER. No MAJOR.\n"` and a tree that
  carries it, asserting the clause holds (the convergence path is clean).

Update the docstrings on these constants to cite the heading-based contract and
roadmap 3.1.5. The `DONE_PREDICATE_*` tree wiring (`_note_on_first_chapter`,
the failer map) is unchanged — only the strings change.

Edit `tests/working_corpus/_done_predicate_oracle.py:36-85`: re-spell the new
heading-based rule independently (its own section/finding parsing, not a copy of
the production constants), keeping it a genuine cross-check. The twin must not
import production (Constraint 5).

Edit `tests/test_working_corpus_done_predicate.py`: extend `test_blocker_edges`
to cover the resolved/near-miss/incidental/sentinel trees and keep
`test_blocker_oracle_twin_agrees` covering every tree (it already iterates the
edge set). Confirm `test_existing_specs_have_no_new_artefacts` stays green (only
strings changed; no new artefacts).

Edit `tests/features/novel_done.feature` and `tests/steps/novel_done_steps.py`:
update the incidental-`[resolved]` scenario wording to the finding-heading shape,
and add a scenario `a live ### B1 finding under ## BLOCKER keeps the predicate not
done` driven from `UNRESOLVED_BLOCKER_NOTE`, asserting exit `1` and
`no_unresolved_blockers` false — the externally observable proof that genuine
critic output is now caught (AGENTS.md "add end-to-end tests where a change
affects command-line behaviour").

Snapshot (`tests/test_novel_done_snapshots.py`): the envelope JSON shape does not
change (same six clause keys, same exit codes), so existing snapshots should not
churn. Add a focused machine-mode snapshot **only if** a reviewer-useful contract
is exposed that the semantic assertions do not already cover; otherwise rely on
the existing exit-1 snapshot plus the new BDD scenario (AGENTS.md: avoid
snapshot-only coverage; do not add churny snapshots). Record the decision in the
Progress log.

Docs to read: the W1 convention, `tests/working_corpus/_builder.py:166-182` (how
`critic_notes` is written), AGENTS.md testing rules. Skills to load:
`python-router` → `python-testing` (corpus fixtures, pytest-bdd), and confirm the
oracle-twin policy from the developers-guide.
Tests added/updated: corpus edge trees + sentinel tree, the rewritten oracle
twin, the extended `test_blocker_edges`, the new BDD scenario, optional snapshot.
Validation: `make all` green; the new BDD scenario fails red against the
pre-change recogniser and passes after.
Commit: corpus + oracle twin + BDD (+ optional snapshot), updated together so the
twin and production never drift in a single commit (R-TWIN-DRIFT).

### W4 — Documentation and design-status (Stage D: hardening/docs)

Edit `docs/developers-guide.md:571-583` ("The BLOCKER format"): rewrite to the
heading-based grammar — an unresolved BLOCKER is a live `### Bn` finding under a
`## BLOCKER` section; resolution is the trailing space-then-`[resolved]` token on
the finding heading; the convergence sentinel and the absent file are clean; name
the
two documented limitations in both directions (case/spelling variants out of
scope per D-BLOCKER-CASE; trailing text forbidden and treated unresolved per
D-BLOCKER-TRAILING — this *names* the third edge audit-3.1.4 Finding 2 asked for).
Cross-link critic-personas.md and roadmap 3.1.5.

Edit `docs/novel-ralph-harness-design.md` §4.2 status block (lines 310-322): add
a roadmap-3.1.5 note that `no_unresolved_blockers` now parses the real
`## BLOCKER`/`### Bn` structure and the documented resolution token, superseding
the 3.1.4 `BLOCKER`-prefix description.

Verify no stale reference to the old "stripped text starts with `BLOCKER`"
grammar survives anywhere in `docs/` or `skill/` (grep for `startswith` /
`BLOCKER` prose).

Docs to read: developers-guide.md, design §4.2, the documentation style guide.
Skills to load: none (prose); apply `en-gb-oxendict`.
Tests: none (docs). Validation: `make markdownlint` and `make nixie` pass;
`make all` still green (no code change). Commit: documentation alignment.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-5`.

Establish the failing state first (red) before W2/W3 implementation, per the
red-green discipline:

```bash
# After writing the new unit cases in W2, before changing the recogniser,
# confirm the genuine-critic-output case fails against today's predicate:
make test  # expect the new unresolved-### B1 case(s) to FAIL (red)
```

Then implement the recogniser and re-run:

```bash
make all
# expect: build OK; ruff format --check clean; ruff/interrogate/pylint clean;
# ty check clean; pytest all green, including the new BLOCKER cases.
```

For the reference and docs commits (W1, W4):

```bash
make markdownlint   # markdownlint-cli2 over the Markdown; expect no findings
make nixie          # Mermaid validation; expect no findings (no diagrams added)
```

Expected `make test` tail after W2/W3 (illustrative):

```plaintext
tests/test_done_predicate.py ......... [ xx%]
tests/test_working_corpus_done_predicate.py ..... [ xx%]
tests/test_novel_done_command.py ... [ xx%]
=== NN passed in N.NNs ===
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. The new behavioural cases — a live `### B1` finding
  under `## BLOCKER` driving `no_unresolved_blockers` false, and the documented
  documented space-then-`[resolved]` token clearing it — fail before W2's
  recogniser change and pass
  after. The new BDD scenario in `novel_done.feature` exits `1` against genuine
  critic output. The Hypothesis positional property holds over generated finding
  headings. The oracle twin agrees with production on every corpus tree.
- Lint/typecheck/format: `make lint`, `make typecheck`, `make check-fmt` clean
  (rolled into `make all`).
- Markdown: `make markdownlint` and `make nixie` clean for the reference/docs
  commits.
- Behaviour to observe: place a real critic-personas-shaped `critic-notes.md`
  (a `## BLOCKER` section with `### B1 — …`) in a chapter dir of an
  otherwise-done tree and run `novel-done --human`; it exits `1` and the messages
  name `no_unresolved_blockers`. Append a space and `[resolved]` to the `### B1`
  heading and it exits `0`.

Quality method (how we check): `make all` then, for markdown-bearing commits,
`make markdownlint` and `make nixie`; the CI mirrors these. The red-before-green
evidence is captured in the Progress log per work item.

Acceptance against the roadmap 3.1.5 success criteria: the resolution convention
is defined once in `critic-personas.md` and `done-conditions.md` (W1); the
recogniser parses the real `## BLOCKER`/`### Bn` structure and the documented
token, with the case/variant decision recorded (W2, D-BLOCKER-CASE); a §1.3.2
corpus tree built from critic-personas-shaped output drives the clause both clean
and dirty (W3); an unresolved blocker in genuine critic output is reported (W2
unit + W3 BDD); and the done-predicate suite stays green (`make all`).

## Idempotence and recovery

Every step is a re-runnable edit; `make all` / `make markdownlint` / `make nixie`
are idempotent. No destructive or stateful operation is involved (the predicate
writes nothing; Constraint 1). If a commit's gate fails, fix forward and re-run
the gate; nothing to roll back beyond `git restore` of the working tree. Commit
per work item so a failed later item never strands an earlier green one.

## Artifacts and notes

The headline evidence is the exit-code flip: a genuine critic-personas-shaped
unresolved blocker, which exits `0` (falsely clean) today, must exit `1` after
W2. Capture that transcript in the Progress log when W2 lands.

## Interfaces and dependencies

In `novel_ralph_skill/state/done_predicate.py` (or, per D-BLOCKER-MODULE, a new
`novel_ralph_skill/state/_blocker_notes.py`), the recogniser ends as two pure
helpers plus the file-boundary wrapper:

```python
# novel_ralph_skill/state/done_predicate.py (or _blocker_notes.py)
def _line_is_unresolved_blocker_finding(stripped: str) -> bool: ...
def _body_has_unresolved_blocker(body: str) -> bool: ...
def _contains_unresolved_blocker(notes_path: Path) -> bool: ...  # file-fault boundary only
```

The public `no_unresolved_blockers(state: State, working_dir: Path) -> bool` and
the `DoneClauses` shape are unchanged. No new third-party dependency; the
recogniser uses only `str`, `re` (optional, for the `### B<digits>` match), and
`pathlib`. The corpus oracle twin in
`tests/working_corpus/_done_predicate_oracle.py` re-implements the same
heading-based rule independently and must not import the production helpers.

## Addenda

Lightweight post-merge corrections folded onto this completed task. Each runs as
a no-plan, no-review addendum pass (roadmap sub-task under the `[x]` 3.1.5
parent).

- [x] **Roadmap 3.1.5.1 — pin the decorated `## BLOCKER` heading false-clean
  direction** (from review:3.1.5; severity low). The recogniser enters a section
  only on a line whose stripped text equals `## BLOCKER` (D-BLOCKER-FORMAT), so
  a decorated heading such as `## BLOCKER (chapter 3)` reads clean by design and
  matches the producer contract — but no test pins this single-sided behaviour,
  so a future critic-prompt change emitting a decorated heading could silently
  re-open the exit-0 lie this task closed. Add an asserting-current-behaviour test
  (a body whose only `## BLOCKER`-like line is decorated holds the clause clean),
  mirroring how D-BLOCKER-CASE pins the case/variant limitation, so the limitation
  is explicit and tamper-evident. Test-only; no production change.

- [x] **Roadmap 3.1.5.2 — add an end-to-end novel-done scenario for the
  cap-reached `[resolved]` exit-0 path** (from audit:3.1.5; severity low). The
  `[resolved]` token's purpose is the cap-reached resolution path
  (`done-conditions.md:134-138`), yet only a unit test
  (`test_resolved_blocker_is_clean`) covers it; the exit-0 direction is the one
  the harness loop terminates on, so it is the more consequential to pin
  behaviourally. Add a BDD scenario to `tests/features/novel_done.feature` (with
  its `tests/steps/novel_done_steps.py` wiring) using the existing all-hold tree
  builder and a `### B1 — … [resolved]` finding, asserting exit `0` and
  `no_unresolved_blockers` true. Closes audit-3.1.5 Finding 2. Test-only; no
  production change.
