# Remove the dead `tomli_w` snippet from `state-layout.md` and reconcile the premature "is removed" claims

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

This is roadmap task 1.2.6 (`docs/roadmap.md` lines 124-131, step 1.2). It
closes a medium-severity documentation-accuracy defect raised by the post-merge
audit of task 1.2.2 (`docs/issues/audit-1.2.2.md`, Finding 1).

Three documents currently disagree about the same fact:

1. `skill/novel-ralph/references/state-layout.md` lines 226-238 contain a live
   Bash code block whose Python heredoc still imports `tomli_w` and calls
   `tomli_w.dump(...)` to hand-edit `state.toml`. The exact `import` line is at
   line 229 and the `dump` call at line 235.
2. `docs/adr-002-toml-round-trip-tomlkit.md` line 77 already asserts, in the
   present tense, that "the failed `tomli_w` snippet **is removed** from the
   reference material", and `docs/novel-ralph-harness-design.md` §5.3 (line
   466) makes the same present-tense claim ("The failed `tomli_w` snippet in
   the current reference **is removed**.").
3. The same ADR-002, at line 22, says the reference material "even **carries** a
   failed `tomli_w` snippet" (present tense), which is true *now* but becomes
   false the moment the snippet is removed.

So the tree, the ADR, and the design contradict one another, and the ADR even
contradicts itself across lines 22 and 77. The terms of reference
(`docs/terms-of-reference.md` line 39) correctly describe `tomli_w` as an
undeclared dependency that does not run, confirming the design and ADR are the
documents out of step.

The risk the audit names: a reader trusting the design or ADR believes the
reference is clean and may copy the `tomli_w` pattern that ADR-002 exists to
reject — a pattern that is doubly wrong, because ADR-002 selects `tomlkit` over
`tomli_w`, and design §4.1 (lines 248-249) eliminates **direct editing of
`state.toml`** altogether ("All state mutation hides behind validated
subcommands. Direct editing of `state.toml` is eliminated.").

The deliverable is a single, coherent state of the documentation:

- the dead `tomli_w` snippet is gone from `state-layout.md`, replaced by
  library-neutral prose that describes the temp-file-then-`Path.replace` atomic
  discipline (design §3.4, `docs/scripting-standards.md` "Reading / writing
  files and atomic updates") without demonstrating a forbidden direct edit;
- ADR-002 and design §5.3 read truthfully (the present-tense "is removed" is now
  correct), and ADR-002 line 22's "even carries" is corrected to the past tense
  so the ADR no longer contradicts itself; and
- a fast guard test (mirroring `tests/test_interrogate_gate.py`) pins the
  absence of `tomli_w`/`tomli_w.dump` from the reference, so a regression fails
  `make test` rather than shipping silently.

Success is observable in two parts, because the word `tomli_w` legitimately
**survives** in the design and ADR after the work — WI2 deliberately keeps the
two truthful "is removed" sentences (`docs/adr-002-toml-round-trip-tomlkit.md`
line 77 and `docs/novel-ralph-harness-design.md` line 466), and ADR-002 line 22
keeps the word while only its tense changes (present "carries" → past
"carried"). A whole-tree `grep` for the bare token therefore *must not* be the
acceptance gate; scrubbing those surviving sentences to make such a grep silent
would re-open the very inaccuracy this task closes. The two-part gate is:

1. **Absence in the skill reference.**
   `grep -rn 'tomli_w' skill/` returns **nothing** — the dead snippet is gone
   from `state-layout.md`, the only file under `skill/` that ever held it.
2. **Truthful references elsewhere.**
   `grep -rn 'tomli_w' docs/adr-002-toml-round-trip-tomlkit.md docs/novel-ralph-harness-design.md`
   still matches, but every surviving line is a *truthful* mention: the
   present tense "even carries" at ADR-002 line 22 is gone (now past tense),
   and the only remaining present-tense uses are the "is removed" sentences at
   ADR-002 line 77 and design line 466, which WI1's removal has made correct.

This two-part formulation is identical to the final cross-document check in
`Concrete steps` ("expect: no output from `skill/`; design and ADR show only
truthful references"). The new test `tests/test_state_layout_reference.py`
fails on the unmodified tree and passes after; and `make all`,
`make markdownlint`, and `make nixie` all pass.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation (see `Decision Log`), not a workaround.

- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-6`. Never edit
  any file in the root/control worktree.
- **Scope is exactly Finding 1 of `docs/issues/audit-1.2.2.md`.** This task owns
  only the `tomli_w` snippet removal and the design §5.3 / ADR-002 wording
  reconciliation. It must **not** touch:
  - the dead `state-layout.md:38` per-chapter `plan.md` spec — that defect is
    owned by roadmap task 6.2.3 (`docs/roadmap.md` line 457; design §8
    lines 663-666);
  - the `SKILL.md:107` phase mislabel or the duplicated done-predicate prose —
    also owned by 6.2.3 (design §8 lines 655-662);
  - Findings 2, 3, and 4 of `docs/issues/audit-1.2.2.md` (the `tomlkit` pin
    comment, the 2.2.1 round-trip cross-reference, and the carried-forward
    audit-1.2.1 duplication) — each is owned by another roadmap item.
- The replacement prose must **not** introduce a `tomllib`, `tomli_w`,
  `tomli`, `toml`, or `tomlkit` code block that demonstrates an agent
  hand-editing `state.toml`. Design §4.1 (lines 248-249) eliminates direct
  editing; the atomic write is owned by the `novel-state` mutators (§3.4, §4.1
  table). Those mutators do **not** exist yet at this point in the roadmap
  (they land in slice 1, tasks 2.x), so the prose must **not**
  forward-reference a `novel-state` invocation either — "point the prose at the
  commands" is the distinct work owned by task 6.2.3 (`docs/roadmap.md` lines
  452-457). The prose must therefore be **library-neutral and
  command-neutral**: it describes the write *discipline* (work first; verify;
  write `state.toml` via temp file then atomic rename; append to the log last),
  not a concrete code recipe.
- The `state.toml.new`-then-rename prose at `state-layout.md` line 61
  ("write to `state.toml.new`, fsync, rename") is correct and must be preserved
  verbatim. The "Atomic writes" narrative (lines 212-241) keeps its meaning,
  but the fenced code block at lines 226-238 is removed and the two list items
  it sat between are edited: line 224's colon lead-in is rewritten into a
  self-contained step-3 sentence and the line-240 step is renumbered to `4.` so
  the ordered list stays contiguous (see WI1). Lines 224 and 240 carry **no**
  `state.toml.new` token, so "preserve them unchanged" would be both wrong and
  impossible once the block they frame is gone.
- All prose, comments, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md (lines 18-19) and the `en-gb-oxendict`
  convention.
- Each work item is independently committable and must pass the AGENTS.md gates
  before commit (`make all`; plus `make markdownlint` and `make nixie` for any
  Markdown change).

## Tolerances (exception triggers)

- Scope: if the change requires editing more than the three files named below
  (`skill/novel-ralph/references/state-layout.md`,
  `docs/adr-002-toml-round-trip-tomlkit.md`,
  `docs/novel-ralph-harness-design.md`) plus the one new test file
  (`tests/test_state_layout_reference.py`), stop and escalate.
- Net size: if the diff exceeds roughly 80 net lines, stop and escalate — this
  is a surgical doc-accuracy fix, not a rewrite of the state-layout reference.
- Dependencies: if any work item appears to need a new runtime or test
  dependency, stop and escalate. It must not: the guard test uses only
  standard-library `pathlib` (the `tests/test_interrogate_gate.py` pattern).
- Boundary breach: if closing Finding 1 appears to require editing
  `SKILL.md`, the `state-layout.md:38` `plan.md` line, or any file owned by
  task 6.2.3, stop and escalate — that is a scope collision the roadmap owner
  must resolve.
- Ambiguity: the delete-versus-rewrite fork offered by the roadmap ("delete the
  snippet (or rewrite it to `tomlkit`)") is **resolved to delete** by the
  Constraints above and the Decision Log; if new evidence contradicts that
  resolution, stop and escalate rather than improvising a `tomlkit` rewrite.
- Iterations: if a gate (`make all`, `make markdownlint`, `make nixie`) still
  fails after 3 fix attempts on a single work item, stop and escalate.

## Risks

- Risk: a wider rewrite of the "Atomic writes" section is tempting, but the
  "point the prose at the novel-state commands" work belongs to task 6.2.3,
  which runs after the commands exist (Requires phase 3). Over-reaching here
  pre-empts 6.2.3 and may conflict with it.
  - Severity: medium. Likelihood: medium.
  - Mitigation: keep the edit surgical — remove only the code fence and replace
    it with library-neutral, command-neutral prose; the Constraints and
    Tolerances forbid touching 6.2.3's defects.
- Risk: a future edit reintroduces a `tomli_w` (or other direct-edit) snippet,
  silently re-opening Finding 1.
  - Severity: medium. Likelihood: low.
  - Mitigation: WI3 adds a guard test that fails `make test` if `tomli_w`
    reappears in the reference, mirroring the `tests/test_interrogate_gate.py`
    precedent.
- Risk (residual, accepted by design): WI3's guard pins only the literal
  `tomli_w` / `import tomli_w` / `tomli_w.dump(` substrings. A *different*
  direct-edit recipe (e.g. a `tomlkit`-based hand-edit of `state.toml`) added
  to the same "Atomic writes" section later would pass the guard green while
  re-opening the design §4.1 "direct editing eliminated" violation this task
  forecloses.
  - Severity: medium. Likelihood: low.
  - Mitigation/justification: broadening the guard to reject *any* direct-edit
    code fence would exceed this task's surgical scope (Finding 1 is specifically
    the `tomli_w` snippet) and would collide with task 6.2.3, which owns pointing
    the reference prose at the `novel-state` commands. The guard is therefore
    substring-specific **by design**; the broader "no direct-edit recipe in any
    reference" invariant is left to 6.2.3 (or a follow-up roadmap item) rather
    than smuggled into 1.2.6. The next reader should know the guard does not
    catch a `tomlkit` recipe.
- Risk: markdownlint or mdformat reflows or rejects the edited prose (line
  length, list numbering, fenced-block spacing).
  - Severity: low. Likelihood: medium.
  - Mitigation: run `make markdownlint` and `make fmt` (mdformat-all) on the
    edited files within each work item before committing; the
    `.markdownlint-cli2.jsonc` config is authoritative.
- Risk: the present-tense "is removed" in design §5.3 / ADR-002 line 77 is
  corrected in the wrong direction (softened to "will be removed") when it
  should now read as simple past/perfect, because the removal lands in the same
  change set.
  - Severity: low. Likelihood: low.
  - Mitigation: WI2 sequences the wording edit after WI1's removal, so the
    present-tense claim is already true; only ADR-002 line 22 ("carries")
    changes tense.

## Progress

- [x] WI1: Remove the dead `tomli_w` code block from `state-layout.md`, rewrite
  line 224's colon lead-in into a self-contained library-neutral step-3
  sentence, and renumber line 240's step to `4.` so the four-item ordered list
  stays contiguous. Done 2026-06-22: fenced block and its blank lead-in removed,
  step 3 folded into a library-neutral temp-file-then-atomic-rename sentence,
  step 4 renumbered; the list renders `1. 2. 3. 4.`. `grep tomli_w` on the
  reference is empty; `make all`, `make markdownlint`, `make nixie` green.
  Note: `make fmt` (`mdformat-all`) reflowed many *unrelated* tracked docs and
  introduced two pre-existing markdownlint defects in files outwith scope
  (`roadmap-1-2-1.md`, `audit-1.2.4.md`); those spurious mutations were reverted
  so the commit stays surgical. The authoritative gate `make markdownlint`
  (over `**/*.md`) is clean.
- [x] WI2: Reconcile the design §5.3 and ADR-002 wording (lines 22 and 77).
  Done 2026-06-22: ADR-002 line 22 changed from present "even carries … does not
  round-trip" to past "even carried … did not round-trip"; line 77's "is removed"
  left as-is (now true). Design §5.3 line 466 tightened "in the current reference
  is removed" to "in the reference is removed", dropping the now-stale "current"
  framing. All three surviving `tomli_w` mentions are truthful; gates green;
  coderabbit returned no findings.
- [x] WI3: Add a guard test pinning the absence of `tomli_w` from the reference.
  Done 2026-06-22: added `tests/test_state_layout_reference.py` mirroring
  `tests/test_interrogate_gate.py` (stdlib `pathlib`, no shelling out, numpy-ish
  docstrings, 100% interrogate coverage). Two tests: the bare `tomli_w` token is
  absent, and neither the comma-form import sentinel (`tomllib, tomli_w`) nor the
  `tomli_w.dump(` call site reappears. `make all` rose from 45 to 47 passing
  tests. Coderabbit returned no findings.

## Surprises & discoveries

- Observation: the roadmap (line 129) offers a "delete OR rewrite to tomlkit"
  fork, but the design forecloses the rewrite.
  - Evidence: design §4.1 lines 248-249 ("Direct editing of `state.toml` is
    eliminated.") and the §3.4 mutator-owned atomic-write discipline. A
    `tomlkit` rewrite of a hand-edit heredoc would re-demonstrate the very
    direct-edit pattern §4.1 forbids.
  - Impact: the fork is resolved to *delete* (see Decision Log); the plan
    carries no undecided menu.
- Observation: Finding 1's proposed fix names task 6.2.3 as the "natural home",
  but the roadmap owner created a dedicated task 1.2.6 instead.
  - Evidence: `docs/roadmap.md` line 124 defines 1.2.6 as this exact removal;
    6.2.3 (lines 452-457) enumerates three *different* skill defects and does
    not list the snippet.
  - Impact: 1.2.6 owns the removal; the §38 `plan.md` line and SKILL.md defects
    stay with 6.2.3 (see Constraints).

## Decision log

- Decision: delete the snippet rather than rewrite it to `tomlkit`.
  - Rationale: design §4.1 (lines 248-249) eliminates direct editing of
    `state.toml`; the snippet demonstrates exactly that. A `tomlkit` rewrite
    would reintroduce the forbidden pattern, and pointing the prose at the
    not-yet-built `novel-state` mutators is task 6.2.3's job, not 1.2.6's.
    Resolving the roadmap's delete-or-rewrite fork to *delete* is the only
    option consistent with the design and the task scope.
  - Date/Author: 2026-06-22, planning agent (roadmap-1-2-6).
- Decision: reconcile by making the documents truthful after the removal — keep
  design §5.3 / ADR-002 line 77 as present-tense "is removed" (now true) and
  change ADR-002 line 22 from "even carries" to the past tense.
  - Rationale: the audit's interim suggestion to soften "is removed" to "is
    removed in roadmap task 6.2.3" applied only "until that [removal] lands"
    (`docs/issues/audit-1.2.2.md` lines 52-54). Since this task lands the
    removal, the truthful state is the present-tense claim, so the softening is
    unnecessary and the only remaining contradiction is line 22's tense.
  - Date/Author: 2026-06-22, planning agent (roadmap-1-2-6).
- Decision: add a static guard test rather than relying on review alone.
  - Rationale: `tests/test_interrogate_gate.py` establishes the project
    precedent of pinning a documentation/config invariant by static parse so a
    regression fails `make test`. Finding 1's risk (a reader copying the dead
    pattern) is best foreclosed by making its absence a tested contract.
  - Date/Author: 2026-06-22, planning agent (roadmap-1-2-6).
- Decision: no cuprum API is exercised by this task.
  - Rationale: the task changes documentation and adds a pure file-reading guard
    test (`pathlib`, stdlib). Design §4 (lines 240-241) confirms cuprum is
    required only where a command shells out, and no v1 command does. The guard
    test mirrors `tests/test_interrogate_gate.py`, which uses `pathlib` and
    `tomllib` and never shells out. There is therefore no cuprum catalogue,
    allowlist, or run/output option to pin for this work.
  - Date/Author: 2026-06-22, planning agent (roadmap-1-2-6).
- Decision: edit lines 224 and 240 of `state-layout.md` (rewrite line 224's
  colon lead-in into a self-contained step-3 sentence and renumber line 240 to
  `4.`); do not "preserve them unchanged".
  - Rationale: round-1 design review established that neither line carries a
    `state.toml.new` token (that token is only inside the deleted block and at
    line 61), and that "preserve line 224 unchanged" would leave a dangling
    "via temp file + rename:" colon introducing nothing once the block is gone.
    The only way to leave a coherent four-item ordered list with no dangling
    colon is to rewrite line 224 and renumber line 240. The `state.toml.new`
    prose genuinely preserved is line 61 alone.
  - Date/Author: 2026-06-22, planning agent (roadmap-1-2-6, round 2).

## Outcomes & retrospective

Completed 2026-06-22. Compared against Purpose: the three documents now agree.

- The dead `tomli_w` snippet is gone from `state-layout.md`; `grep tomli_w` on
  the skill reference is empty. The "Atomic writes" discipline is a contiguous
  four-item ordered list whose step 3 is a library-neutral, command-neutral
  temp-file-then-atomic-rename sentence (no `tomllib`/`tomli_w`/`tomlkit` code,
  no `novel-state` forward reference — both owned by task 6.2.3).
- ADR-002 line 22 is past tense ("even carried … did not round-trip"); line 77
  and design §5.3 keep "is removed", now truthful. The three surviving `tomli_w`
  mentions are all truthful references, exactly as the two-part Purpose gate
  predicted (skill empty; design/ADR truthful).
- `tests/test_state_layout_reference.py` guards the absence; it was shown RED
  against the original snippet fixture and is GREEN on the final tree
  (`make all`: 45 → 47 tests).
- Gates: `make all`, `make markdownlint`, and `make nixie` green at every commit.

Deviation worth noting for the next agent: `make fmt` (`mdformat-all`) reflows
*all* tracked Markdown and, on this tree, introduces two pre-existing
markdownlint defects in files outwith scope (`docs/execplans/roadmap-1-2-1.md`,
`docs/issues/audit-1.2.4.md`). The authoritative gate is `make markdownlint`
(over `**/*.md`), which is clean; the spurious `make fmt` mutations to unrelated
docs were reverted to keep each commit surgical. Run `make markdownlint`, not
`make fmt`, when validating an isolated doc edit here.

## Context and orientation

The repository is a Python package (`novel_ralph_skill`,
`requires-python = ">=3.14"`) that ships a writing-harness *skill* under
`skill/novel-ralph/`. The skill's reference files
(`skill/novel-ralph/references/*.md`) are prose the harness agent reads; they
are the "prose layer the commands replace" (design §8, line 648).
`state-layout.md` is the reference that defines the working directory, the
`state.toml` schema, the log conventions, and the atomic-write discipline (its
own opening, lines 1-5).

Key files for this task, by full repository-relative path:

- `skill/novel-ralph/references/state-layout.md` — the reference carrying the
  dead snippet. The relevant region is the "## Atomic writes" section (lines
  212-241). The snippet itself is a fenced ```` ```bash ```` block at lines
  226-238 whose body is a `python3 - <<'EOF'` heredoc importing
  `tomllib, tomli_w, os` (line 229), mutating two values, writing
  `working/state.toml.new` with `tomli_w.dump(...)` (line 235), and
  `os.replace`-ing it into place (line 236). The numbered prose around it
  frames the write discipline as an ordered list: steps `1.`/`2.` at lines
  220-223, the `3.` lead-in at line 224 (which ends in a colon and introduces
  only the deleted block — it carries no `state.toml.new` token and must be
  rewritten, not preserved), and a restarted `1.` at line 240 that Markdown
  renders as item 4 via list continuation (also rewritten, to `4.`). Neither
  line 224 nor line 240 contains a `state.toml.new` narrative; that token
  appears only inside the deleted block (lines 234, 236) and at the untouched
  line 61.
- `docs/adr-002-toml-round-trip-tomlkit.md` — ADR-002. Line 22 ("even carries"),
  line 77 ("is removed").
- `docs/novel-ralph-harness-design.md` — the design. §5.3 is lines 458-467; the
  claim is line 466 ("is removed"). §4.1 (lines 246-249) and §3.4 (lines
  217-235) define the mutator-owned atomic-write discipline. §8 (lines 646-666)
  records which reference defects belong to task 6.2.3.
- `docs/issues/audit-1.2.2.md` — the audit; Finding 1 (lines 19-54) is the
  authoritative specification for this task.
- `docs/roadmap.md` — task 1.2.6 (lines 124-131); task 6.2.3 (lines 452-460).
- `docs/scripting-standards.md` — the atomic-write convention (lines 397-415:
  "Atomic write pattern (tmp → replace)",
  `tmp_path.replace(f)  # atomic on POSIX`).
- `tests/test_interrogate_gate.py` — the precedent for a static guard test that
  reads a project file with `pathlib` and asserts an invariant.
- `Makefile` — gates: `make all` (= `build check-fmt lint typecheck test`),
  `make markdownlint` (markdownlint-cli2 over `**/*.md`), `make nixie` (Mermaid
  validation), `make test` (`pytest -v -n auto`).

Terms of art, defined immediately:

- **Direct editing of `state.toml`**: an agent reading, mutating, and rewriting
  `state.toml` by hand (e.g. the dead heredoc), as opposed to going through a
  validated `novel-state` subcommand. Design §4.1 eliminates this.
- **Atomic write (tmp → replace)**: write the new content to a temporary file in
  the same directory, then `Path.replace` it over the target; the rename is
  atomic on POSIX, so a crash never leaves a half-written file
  (`docs/scripting-standards.md` lines 409-414; design §3.4 lines 219-220).
- **Guard test**: a fast, pure test that statically reads a project file and
  asserts an invariant, so a regression fails `make test` rather than shipping
  silently (`tests/test_interrogate_gate.py` module docstring).

## Plan of work

Three ordered, independently committable work items. WI1 removes the defect,
WI2 makes the dependent documents truthful, WI3 locks the invariant. Each ends
with its own validation; do not proceed past a failing gate.

### WI1 — Remove the dead `tomli_w` snippet and replace it with library-neutral prose

Implements: `docs/issues/audit-1.2.2.md` Finding 1 (the removal half);
`docs/roadmap.md` lines 124-131; design §4.1 (lines 248-249, direct editing
eliminated) and §3.4 (lines 217-235, mutator-owned atomic write);
`docs/scripting-standards.md` lines 397-415.

Edit only `skill/novel-ralph/references/state-layout.md`. The exact "## Atomic
writes" region as it stands today is (shown inside a four-backtick fence so the
inner triple-backtick fences are inert):

```text
218 Discipline:
219
220 1. Write the actual work first (draft.md, critic-notes.md,
221    etc.).
222 2. After the work is on disk and verified (file exists, size is
223    non-zero), update state.toml.
224 3. Write state.toml via temp file + rename:
225
226 ```bash
227 # Example pattern for state mutation
228 python3 - <<'EOF'
229 import tomllib, tomli_w, os
230 with open("working/state.toml", "rb") as f:
231     state = tomllib.load(f)
232 state["drafting"]["current_beat"] = 6
233 state["word_counts"]["current"] = 24820
234 with open("working/state.toml.new", "wb") as f:
235     tomli_w.dump(state, f)
236 os.replace("working/state.toml.new", "working/state.toml")
237 EOF
238 ```
239
240 1. Append to log.md last. The log entry is the receipt that the
241    state transition happened.
```

Two facts to read off this region before editing, because the round-1 review
corrected an earlier mis-statement of them:

- Line 224 is **not** a `state.toml.new` narrative. It reads
  `3. Write state.toml via temp file + rename:` — a colon-terminated *lead-in*
  that introduces nothing except the fenced code block being deleted. Line 240
  reads `1. Append to log.md last.` and likewise carries no `state.toml.new`
  token. The only `state.toml.new` tokens in the file are inside the deleted
  block (lines 234 and 236) and at the untouched line 61 ("write to
  `state.toml.new`, fsync, rename"). So lines 224 and 240 must be **edited**,
  not "preserved": line 224's dangling colon must be rewritten and line 240
  must be renumbered (see below). Only line 61 is genuinely preserved.
- Markdown currently renders this as a four-item ordered list: the `1.` at
  line 240 restarts numbering but, because the fenced block sits inside the
  list as item 3's content, mdformat renders it as item 4 via list
  continuation. Once the interrupting fence is gone, a literal `3.` then `1.`
  sequence would let mdformat renumber unexpectedly. The edit must therefore
  emit an explicit, contiguous four-item ordered list (`1. 2. 3. 4.`).

Perform the edit in two parts:

1. Delete the entire fenced ```` ```bash ```` code block at lines 226-238 (from
   the ```` ```bash ```` opener through the closing ```` ``` ```` fence,
   inclusive), together with the blank line 225 that separated the lead-in from
   the fence.
2. Rewrite line 224 so its trailing colon no longer dangles: fold the
   temp-file-then-atomic-rename example *into* step 3 as one self-contained,
   library-neutral sentence, and renumber the former line-240 step to `4.` so
   the list reads as a contiguous four-item ordered list. The intended
   post-edit list, verbatim in shape, is:

```text
Discipline:

1. Write the actual work first (draft.md, critic-notes.md,
   etc.).
2. After the work is on disk and verified (file exists, size is
   non-zero), update state.toml.
3. Write state.toml via a temporary file in working/, then atomically
   rename it over working/state.toml, so a crash mid-write never leaves a
   torn file.
4. Append to log.md last. The log entry is the receipt that the
   state transition happened.
```

The step-3 sentence above is the single library-neutral replacement for the
deleted worked example. Do **not** name `tomllib`, `tomli_w`, `tomli`, `toml`,
or `tomlkit`, and do **not** name a `novel-state` subcommand (those belong to
task 6.2.3). Preserve only the existing "write to `state.toml.new`, fsync,
rename" phrasing at line 61 unchanged; lines 224 and 240 are edited as above.
After editing, run `make fmt` (mdformat-all) and confirm mdformat leaves the
four items numbered `1. 2. 3. 4.` (it must not have collapsed or restarted the
sequence). The exact wording of step 3 may be adjusted for voice and line
length so long as it stays library-neutral, command-neutral, and names no
direct-edit recipe; the `4.` renumber and the no-dangling-colon outcome are not
negotiable.

This work item reads, before editing: `docs/issues/audit-1.2.2.md` Finding 1;
design §3.4 and §4.1; `docs/scripting-standards.md` "Reading / writing files
and atomic updates"; `docs/documentation-style-guide.md` for code-fence and
prose conventions. Skills to load: `en-gb-oxendict` (Oxford spelling of the new
prose); the `df12-copy` and `documentation-style-guide` conventions are
honoured through the existing reference's voice.

Tests for WI1: none of its own beyond the gates — this is a prose deletion. The
regression contract is added in WI3 (sequenced after the wording edit so the
test asserts the final state of the tree). Per AGENTS.md, a docs-only change
adds no unit, property, snapshot, or e2e test; markdownlint and nixie are the
applicable gates.

Validation for WI1:

1. `grep -n 'tomli_w' skill/novel-ralph/references/state-layout.md` returns
   nothing.
2. `make markdownlint` passes.
3. `make nixie` passes (no Mermaid touched; expected no-op pass).
4. `make all` passes.

Commit WI1 with an en-GB Oxford-spelled message scoped to the snippet removal.

### WI2 — Reconcile the design §5.3 and ADR-002 wording

Implements: `docs/issues/audit-1.2.2.md` Finding 1 (the reconciliation half);
design §5.3 (lines 458-467); ADR-002 (lines 22 and 77).

Sequenced after WI1 so the present-tense "is removed" is already true. Edit two
files:

1. `docs/adr-002-toml-round-trip-tomlkit.md` line 22: change the present-tense
   "The current reference material even **carries** a failed `tomli_w` snippet
   that does not round-trip comments." to the past tense (e.g. "even
   **carried** a failed `tomli_w` snippet…"), so the ADR no longer claims the
   reference currently holds a snippet that WI1 deleted. Leave line 77 ("the
   failed `tomli_w` snippet is removed from the reference material") as-is:
   after WI1 it is true. Confirm the surrounding "Context and problem
   statement" and "Decision outcome" prose still reads coherently with the
   tense change. The audit (`docs/issues/audit-1.2.2.md`) cites this design
   sentence as `§5.3:464`; this plan uses the more precise `466-467`. Both
   point at the same "is removed" sentence — the figure differs only because
   line counting drifts by a line or two; this is not a mis-citation of the
   audit.
2. `docs/novel-ralph-harness-design.md` §5.3 line 466-467: the present-tense
   "The failed `tomli_w` snippet in the current reference is removed." is now
   true after WI1; leave it, or tighten "in the current reference" to remove
   the now-stale "current" framing if markdownlint/prose review prefers
   (optional, within tolerance). Do not alter the `tomlkit` decision substance.

Do **not** touch design §8 (it correctly records 6.2.3's defects), and do
**not** touch any `state-layout.md:38` `plan.md` wording.

This work item reads, before editing: `docs/issues/audit-1.2.2.md` Finding 1
(esp. lines 52-54 on the softening's "until that lands" condition); ADR-002 in
full; design §5.3. Skills to load: `en-gb-oxendict`.

Tests for WI2: none of its own beyond the gates (prose edit). The
cross-document consistency is asserted by WI3's guard test (it checks both the
absence in the reference and, optionally, the truthfulness predicate — see WI3).

Validation for WI2:

1. `grep -rn 'tomli_w' docs/adr-002-toml-round-trip-tomlkit.md docs/novel-ralph-harness-design.md`
   shows only truthful, past-or-removed references (no present-tense "carries").
2. `make markdownlint` passes.
3. `make nixie` passes.
4. `make all` passes.

Commit WI2 separately.

### WI3 — Guard the invariant with a static test

Implements: `docs/issues/audit-1.2.2.md` Finding 1's stated risk (a reader
copying the dead pattern); the `tests/test_interrogate_gate.py` guard-test
precedent; AGENTS.md "Python verification and testing" (lines 141-172,
unit-test placement in top-level `tests/`).

Add `tests/test_state_layout_reference.py`: a fast, pure guard test that reads
`skill/novel-ralph/references/state-layout.md` via `pathlib` (resolving the
path from `Path(__file__).resolve().parent.parent`, exactly as
`tests/test_interrogate_gate.py` resolves `_PROJECT_ROOT`) and asserts:

1. the literal substring `tomli_w` does not appear anywhere in the reference;
   and
2. a regression sentinel — the reference contains no `import tomli_w` and no
   `tomli_w.dump(` call (asserting both the import and the call site named in
   Finding 1, lines 26-27, are gone).

Optionally, add a second test asserting cross-document truthfulness: that
`docs/adr-002-toml-round-trip-tomlkit.md` does not contain the present-tense
phrase "even carries a failed `tomli_w`" (the line-22 defect WI2 fixes). Keep
this assertion substring-based and tolerant of surrounding wording so it is not
brittle; if it proves brittle under markdownlint reflow, drop it and rely on
the reference-only assertion plus review (note the choice in the Decision Log).

The module must carry a module docstring and each test a numpy-style docstring
with the project's conventions (mirror `tests/test_interrogate_gate.py`: class
or function form, `from __future__ import annotations`, `pathlib`-only, no
shelling out). It must pass `interrogate` (100% docstring coverage), `ruff`,
`pylint`, and `ty` — i.e. the full `make all` Python gate, not only `make test`.

This work item reads, before writing: `tests/test_interrogate_gate.py` (the
exact precedent); AGENTS.md lines 141-172; `docs/developers-guide.md` test
conventions. Skills to load: `python-router`, then `python-testing` (fast pure
guard-test shape, pytest collection, top-level `tests/` placement). Consult
`python-verification` only to confirm — and it does — that a static
absence-assertion needs **no** Hypothesis property, CrossHair, or mutmut
adversary: there is no input space to generate over and no branching logic to
mutate; the test is a single deterministic file read with fixed assertions.
Therefore the plan adds **no** `hypothesis`/`crosshair`/`mutmut` work for this
task.

Red/green evidence (AGENTS.md mandates running the suite before and after each
change so a regression is observable; it does not name a red-green-refactor
cycle, so the discipline here is "demonstrate the test discriminates", not a
formal TDD ritual): write the test first and confirm it **fails** on the
pre-WI1 tree (where `tomli_w` is present), then confirm it **passes** after
WI1+WI2. Because WI3 is committed after WI1, capture the red evidence by
temporarily checking the assertion against a stashed copy of the original
snippet (or by asserting the test's logic against a fixture string containing
`tomli_w`), and record the transcript in `Artifacts and notes`. The committed
state is green.

Validation for WI3:

1. `make test` — the new test `tests/test_state_layout_reference.py` passes;
   total pass count increases by the number of new tests.
2. `make lint` and `make typecheck` — the new module passes `ruff`, `pylint`,
   `interrogate` (100% docstrings), and `ty`.
3. `make all` passes.

Commit WI3 separately.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-6`. Confirm the
branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-6 branch --show-current
```

Expected: `roadmap-1-2-6`.

WI1 — remove the snippet, then gate:

```bash
# after editing state-layout.md
grep -n 'tomli_w' skill/novel-ralph/references/state-layout.md   # expect: no output
make markdownlint
make nixie
make all
```

WI2 — reconcile wording, then gate:

```bash
grep -rn 'tomli_w' docs/adr-002-toml-round-trip-tomlkit.md docs/novel-ralph-harness-design.md
make markdownlint
make nixie
make all
```

WI3 — add and run the guard test:

```bash
# red first (against the original snippet, via stash or fixture string), then:
make test        # expect the new test in the pass count
make all
```

Final cross-document check (all three documents agree):

```bash
grep -rn 'tomli_w' skill/ docs/adr-002-toml-round-trip-tomlkit.md \
  docs/novel-ralph-harness-design.md
# expect: no output from skill/; design and ADR show only truthful references
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- Running `grep -rn 'tomli_w' skill/novel-ralph/references/state-layout.md`
  returns nothing: the dead snippet is gone.
- `docs/adr-002-toml-round-trip-tomlkit.md` no longer contains the present-tense
  "even carries a failed `tomli_w` snippet"; line 77's "is removed" and design
  §5.3's "is removed" are now truthful.
- The new test `tests/test_state_layout_reference.py` fails on the unmodified
  tree (where `tomli_w` is present) and passes after WI1+WI2.
- `make all` passes (build, check-fmt, lint, typecheck, test).
- `make markdownlint` passes on the edited Markdown.
- `make nixie` passes (no Mermaid changed; expected no-op pass).

Quality criteria ("done"):

- Tests: `make test` green, including the new guard test; pass count increased.
- Lint/typecheck: `make lint` and `make typecheck` green; the new module
  satisfies `ruff`, `pylint`, `interrogate` (100% docstrings), and `ty`.
- Docs: `make markdownlint` and `make nixie` green; all prose in en-GB Oxford
  spelling.

Quality method: run `make all`, `make markdownlint`, and `make nixie` per work
item before committing; do not commit on a failing gate.

## Idempotence and recovery

Every step is a Markdown or test-file edit and is safely re-runnable. If a gate
fails, fix the edited file and re-run the gate; nothing is destructive. The
three work items are independent commits, so any one can be amended or reverted
without disturbing the others. The guard test's red evidence is captured
against a stashed or fixture copy of the snippet, so the working tree is never
left in a broken state.

## Artefacts and notes

WI1: the fenced `bash`/`python3` heredoc at the old lines 226-238 (importing
`tomllib, tomli_w, os`, mutating two values, writing `working/state.toml.new`
with `tomli_w.dump`, and `os.replace`-ing it) plus its blank lead-in were
deleted; step 3 was folded into a self-contained library-neutral sentence and
the trailing step renumbered to `4.`.

WI2: ADR-002 line 22 "even **carries** … **does not** round-trip" →
"even **carried** … **did not** round-trip"; design §5.3 "in the current
reference is removed" → "in the reference is removed".

WI3 red→green transcript — the guard's three assertions evaluated against the
original snippet text (RED) and against the post-removal tree (GREEN):

```text
RED (fail): "tomli_w" not in text
RED (fail): "tomllib, tomli_w" not in text
RED (fail): "tomli_w.dump(" not in text
RED confirmed: every guard assertion fails on the original snippet text.

# after WI1+WI2, on the committed tree:
make all → 47 passed (was 45); the two new guard tests pass.
```

## Interfaces and dependencies

No new runtime or test dependency. The guard test uses only standard-library
`pathlib` (and, if the optional cross-document assertion is kept, plain string
matching), mirroring `tests/test_interrogate_gate.py`. No cuprum API is used:
this task ships no command and shells out nowhere (design §4 lines 240-241
confirm cuprum is required only where a v1 command shells out, and none do).
The new test module to exist at end of WI3:

```python
# tests/test_state_layout_reference.py
from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _state_layout_text() -> str:
    """Return the state-layout skill reference as text."""
    return (
        _PROJECT_ROOT / "skill" / "novel-ralph" / "references" / "state-layout.md"
    ).read_text(encoding="utf-8")
```

with one or more test functions asserting
`"tomli_w" not in _state_layout_text()` and the absence of `import tomli_w` /
`tomli_w.dump(`.

## Revision note

- Round 2 (2026-06-22): resolved the round-1 BLOCKING contradiction in WI1.
  Earlier, WI1 told the implementer to "preserve lines 224 and 240 unchanged"
  as a `state.toml.new`/rename narrative while also rewriting step 3's worked
  example — instructions that are mutually exclusive and factually wrong, since
  lines 224 (`Write state.toml via temp file + rename:`) and 240
  (`Append to log.md last…`) carry no `state.toml.new` token and line 224's
  colon would dangle once the block is deleted. WI1 now (a) prints the exact
  pre-edit region with line numbers, (b) states that lines 224/240 must be
  *edited* not preserved, (c) gives the explicit four-item post-edit ordered
  list with line 224 folded into a self-contained step-3 sentence and line 240
  renumbered to `4.`, and (d) mandates a post-edit `make fmt` check that the
  list stays numbered `1. 2. 3. 4.`. The Context, Constraints, Progress, and
  Decision Log sections were corrected to match.
- Round 2 also folded in the three round-1 advisories: WI1 states the intended
  contiguous four-item list (mdformat-renumber advisory); the "red, green,
  refactor" citation in WI3 is re-attributed to AGENTS.md's actual
  "run-before-and-after" mandate; WI2 reconciles the audit's `§5.3:464` against
  the plan's `466-467`; and Risks records the residual, by-design gap that the
  substring guard does not catch a future `tomlkit` direct-edit recipe (owned
  by 6.2.3). No work-item count, file scope, or tolerance changed; the plan
  stays three work items over the same four files.
- Round 3 (2026-06-22): resolved the round-2 BLOCKING self-contradiction in the
  Purpose acceptance criterion. Previously the Purpose claimed success was
  observable when
  `grep -rn 'tomli_w' skill/ docs/adr-002* docs/novel-ralph-harness-design.md`
  "returns nothing". That gate is unsatisfiable by design: WI2 deliberately
  keeps the truthful "is removed" sentences at ADR-002 line 77 and design line
  466, and retains the word at ADR-002 line 22 (only its tense changes), so all
  three contain the bare token `tomli_w` after the work (verified against the
  live files: ADR-002:22, ADR-002:77, design:466). An implementer treating the
  whole-tree grep as the gate would have scrubbed the truthful sentences and
  re-opened the very inaccuracy this task closes. The Purpose now states a
  two-part gate — (1) `grep -rn 'tomli_w' skill/` returns nothing; (2) the
  design/ADR matches are all *truthful* references (line-22 present tense gone;
  only the "is removed" sentences remain) — identical in wording to the
  existing final cross-document check in `Concrete steps` (lines now ~607-610)
  and to the already-correctly-scoped `Validation and acceptance` grep (skill
  file only). No work-item count, file scope, tolerance, or test changed; the
  plan stays three work items over the same four files.
