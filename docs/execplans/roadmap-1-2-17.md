# Sweep the skill reference files to the `novel` multiplexer surface

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 1.2.15 retired the five legacy console-scripts (`novel-state`,
`novel-done`, `novel-compile`, `desloppify`, `wordcount`) and the package now
ships **exactly one** `[project.scripts]` entry — `novel` — dispatching into a
`state` subgroup and four leaf verbs (`novel done`, `novel compile`,
`novel desloppify`, `novel wordcount`). Verified in the worktree:
`novel_ralph_skill/commands/names.py` defines `SUBCOMMAND_NAMES` as
`("novel state", "novel done", "novel compile", "novel desloppify",
"novel wordcount")` and `project_scripts_table()` returns `{"novel": …}`.

Tasks 1.2.14 (design document and `SKILL.md`) and 1.2.16 (users' and developers'
guides) swept the prose that those success criteria named. The three skill
**reference** files under `skill/novel-ralph/references/` fell outside both
criteria, so they still invoke the retired hyphenated console-scripts directly:

1. `state-layout.md` — 15 `novel-state` invocations across 14 lines (line 230
   carries two `novel-state` tokens) plus one `novel-compile` reference
   (line 239). That makes 16 convertible tokens in this file. Line 239 is a
   two-token line carrying both `novel-state set-chapters` and `novel-compile`.
   These name commands the harness types — `novel-state set-critic-pass
   --pass N`, `novel-state check`, `novel-state recount`, `novel-state set-gate
   --knitting-30`, `novel-state set-chapters`, `novel-state init`,
   `novel-state reconcile`, `novel-state complete-final-pass`, and the
   `novel-compile` index follower.
2. `done-conditions.md` — 5 `novel-done` references (lines 17, 18, 141, 144,
   145), all naming the done-predicate command the agent runs each turn.
3. `critic-personas.md` — 2 `novel-done` references (lines 131, 133) naming the
   blocker-checker command in the "Resolving a BLOCKER" convention.

After this change a reader of any of the three references sees the single
`novel <sub>` surface the package actually ships, with no surviving
`novel-state` / `novel-done` / `novel-compile` console-script invocation.

**The load-bearing distinction this task names explicitly.** The roadmap warns
against mis-sweeping the noun-form `desloppify`. There are two different things
spelled `desloppify` in these files:

- The retired **console-script** `desloppify` (the one that polluted `PATH`),
  which became the subcommand `novel desloppify` (ADR 007 §90-96; design §4.4).
- The **noun / operation** "desloppify" — the desloppification pass the agent
  runs — used in running prose: "run desloppify", "If desloppify is run", "One
  full-novel desloppify pass logged", "run desloppify on the edited passages".
  This names the *operation*, not the command a user types, and **stays
  verbatim**. The design document itself uses this noun form (design §4.4 line
  414 "`desloppify` runs the checklist", line 423 "`desloppify` detects").

Verified by enumeration (Work item 1 records the live transcript): every
`desloppify` occurrence in all three files is the **noun form** in running prose
(`state-layout.md` lines 167-168; `done-conditions.md` lines 110, 191;
`critic-personas.md` line 162). **No `desloppify` console-script invocation and
no `wordcount` reference exists in any of the three files at all.** So the
roadmap's "no retired `desloppify`/`wordcount` console-script reference
survives" criterion is satisfied by leaving every `desloppify` noun form
untouched; there is nothing to flip there, and flipping a noun form to
`novel desloppify` would *introduce* the error the task warns against. This plan
converts only `novel-state`, `novel-compile`, and `novel-done`.

The work is a **documentation-only** sweep of three Markdown files. It touches
no Python, no test, and no command behaviour. `make all` stays green because no
test asserts on the *command spelling* inside these reference bodies: the body
guards in `tests/test_state_layout_reference.py` and
`tests/test_state_layout_schema_guard.py` scan for forbidden `state.toml`-write
**recipes** and parse the **phase-enum text block**, neither of which involves a
command name (see `Surprises & Discoveries`). Success is observable by grep (no
`novel-state`/`novel-done`/`novel-compile` survives; the `desloppify` noun-form
count is unchanged) and by the Markdown gates (`make markdownlint` and
`make nixie` pass).

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- Edit only `skill/novel-ralph/references/state-layout.md`,
  `skill/novel-ralph/references/done-conditions.md`, and
  `skill/novel-ralph/references/critic-personas.md`. Do not modify any other
  file: not the roadmap, not the design document, not the ADRs, not `SKILL.md`,
  not the guides, not any code or test. The roadmap success criterion names
  exactly these three reference files.
- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-17`. Never
  read-modify-write any file in the root/control worktree.
- **Convert only retired console-script invocations.** Flip `novel-state <verb>`
  → `novel state <verb>`, `novel-compile` → `novel compile`, and `novel-done` →
  `novel done`. The surface vocabulary is fixed by
  [ADR 007](../adr-007-command-surface-novel-multiplexer.md) and
  `novel_ralph_skill/commands/names.py` `SUBCOMMAND_NAMES`; use exactly these
  spaced forms. Do **not** invent `novel-desloppify`-style hyphenated namespacing
  (Option A, which ADR 007 rejected).
- **Preserve every `desloppify` noun form verbatim.** Each occurrence in the
  three files is the operation noun in running prose, not the retired
  console-script (see the enumeration in `Purpose`). Do NOT rewrite "run
  desloppify" → "run `novel desloppify`"; that mis-sweeps the noun form and
  introduces the exact error the task warns against. There is no `wordcount`
  reference and no `desloppify`/`novel-desloppify` console-script invocation in
  any of the three files; do not add one.
- Do **not** alter the negative-test fixture
  `novel-state set-cursor --chapter 7` or any `novel-state`/`novel-done` literal
  that lives in **test code** (`tests/test_state_layout_reference.py:252`,
  `tests/test_state_layout_schema_guard.py`, the `tests/working_corpus/`
  docstrings, etc.). Those are owned by sibling roadmap task **1.2.8.5**, whose
  addendum explicitly places them "outside the `skill/novel-ralph/references/`
  scope of 1.2.17". This task's scope is the three reference files only.
- Do not change the substance of any sentence — the `state.toml`-write
  discipline, the ADR-001/ADR-008/ADR-010 cross-references, the exit-code
  contracts, the gate-ratio binding, the blocker-resolution convention. The
  only change is the command-name literal and any minimal re-flow needed to keep
  the surrounding sentence reading truthfully and within 80 columns.
- Do not introduce a copy-pasteable `state.toml`-write recipe. The body guard
  `tests/test_state_layout_reference.py::TestSkillReferenceGuard` scans these
  files; a converted sentence that still points at `novel state` (not a raw
  write) stays clean by construction, but never add a `tomlkit`/`tomllib`/shell
  hand-edit fence.
- All prose must be en-GB Oxford spelling (`-ize`/`-yse`/`-our`), matching the
  surrounding references.

## Tolerances (exception triggers)

- Scope: this plan edits exactly three files. If a truthfulness fix appears to
  require editing a fourth file, stop and escalate (it likely belongs to a
  sibling task such as 1.2.8.5).
- Noun-form boundary: if you find yourself about to change a `desloppify`
  occurrence, stop and re-confirm it is a retired console-script invocation
  (it is not — every occurrence in these three files is the noun form). Do not
  convert it.
- Ambiguity: if a sentence cannot be made truthful by a mechanical literal swap
  — for example if it asserts a behaviour the spaced surface does not actually
  have — stop and record the conflict in the `Decision Log` before guessing.
- Gate iterations: if `make markdownlint` still fails after 3 fix attempts on a
  single work item, stop and escalate.
- Test breakage: if `make all` goes red after a sweep, stop and escalate — that
  would mean a test does assert on a command spelling in a reference body, which
  contradicts the Work-item-0 finding and must be reconciled, not worked around.

## Risks

    - Risk: Mis-sweeping a `desloppify` noun form to `novel desloppify`,
      introducing the exact error the task explicitly warns against.
      Severity: high
      Likelihood: medium
      Mitigation: The conversion alternation is restricted to
      `novel-state|novel-compile|novel-done` — `desloppify` is NOT in it.
      Work item 1 records the enumerated noun-form occurrences as a preserve
      list; Work item 5's acceptance gate counts `desloppify` occurrences before
      and after and asserts the count is unchanged (no noun form was touched and
      none was added).

    - Risk: A converted sentence introduces a `markdownlint` line-length
      (80-column prose) regression, since `novel-state check` → `novel state
      check` is the same length but a few lines that wrap tightly may shift.
      Severity: low
      Likelihood: low
      Mitigation: Run `make markdownlint` per work item and hand-wrap at 80
      columns (AGENTS.md Markdown guidance, line 173). AGENTS.md line 170 also
      asks for `make fmt` after documentation changes, but the **tree-wide**
      target is unsafe here: in this worktree `mdformat-all` re-flows all 267
      Markdown files (verified live) and would churn ~250 files unrelated to this
      task, some of which (`docs/issues/*.md`) carry pre-existing line-length
      errors that predate it (recorded as a Decision in the 1.2.16 execplan, the
      immediately prior sibling sweep). The permitted substitute is a **scoped**
      format of only the edited reference files
      (`mdtablefix … --in-place <file>` then `markdownlint-cli2 --fix <file>`,
      the two commands `mdformat-all` invokes), which stays inside this task's
      scope. Hyphenated and spaced forms are the same character count, so the
      literal swap alone is already `make markdownlint`-clean; the scoped format
      is available if a re-wrap is needed.

    - Risk: Editing a `novel-state` literal that is actually part of a
      `state.toml`-write-recipe illustration, tripping the body guard.
      Severity: low
      Likelihood: low
      Mitigation: None of the 15 `novel-state` occurrences sit inside a fenced
      write recipe — they are running-prose references to the validated command
      that *replaces* hand-edits (the guard's whole point). Converting
      `novel-state` → `novel state` keeps the sentence pointing at the validated
      command, so the guard stays green. Work item 5 runs `make all` to confirm.

    - Risk: A test in `tests/` carries a `novel-state`/`novel-done` literal that
      a careless tree-wide `sed` would also rewrite, breaching the scope
      Constraint and colliding with sibling task 1.2.8.5.
      Severity: medium
      Likelihood: medium
      Mitigation: Never run a blind tree-wide `sed`. Restrict every edit to the
      three named files (Work items 2-4 each `grep`/edit one file). The
      acceptance gate (Work item 5) greps only the three reference files, not
      `tests/`.

## Progress

    - [x] (2026-06-26) Work item 0 — Orientation and reference grep (no edits).
    - [x] (2026-06-26) Work item 1 — Record the per-file convert/preserve
      enumeration.
    - [x] (2026-06-26) Work item 2 — Sweep `state-layout.md` to the `novel`
      surface.
    - [x] (2026-06-26) Work item 3 — Sweep `done-conditions.md` to the `novel`
      surface.
    - [x] (2026-06-26) Work item 4 — Sweep `critic-personas.md` to the `novel`
      surface.
    - [x] (2026-06-26) Work item 5 — Gate the sweep and prove the end-state
      (markdownlint + nixie + the noun-form-preserved acceptance grep +
      `make all`).

## Surprises & discoveries

    - Observation: Unlike the 1.2.16 guide sweep, several tests DO read the
      bodies of these three reference files — but none asserts on a *command
      name*. `tests/test_state_layout_reference.py` scans every
      `skill/novel-ralph/**/*.md` file for forbidden `state.toml`-write recipes
      (`find_direct_state_write_recipes_in_files`); its `novel-state` mentions
      are in docstrings and a self-contained synthetic fixture
      (`test_novel_state_example_not_flagged`, line 252), not assertions against
      the live reference text. `tests/test_state_layout_schema_guard.py` parses
      the emitted `state.toml` schema, not commands.
      `tests/test_working_corpus.py` parses the `### Phase enum` text block from
      `state-layout.md` (lines 137-149), which carries no command name.
      Evidence: `grep -rnE 'novel-state|novel-done|novel-compile' tests/` returns
      only docstrings and fixtures; the scanners key on write primitives and the
      phase-enum block, never on a command spelling.
      Impact: Converting `novel-state`/`novel-compile`/`novel-done` in the
      reference bodies cannot turn `make all` red. The mandated gates reduce to
      `make markdownlint` and `make nixie` on the edited Markdown, with `make
      all` run once at the end to confirm no incidental breakage. (To be
      re-confirmed live in Work item 0.)

    - Observation: Every `desloppify` occurrence in the three files is the
      operation noun in running prose, never the retired console-script. There
      is no `wordcount` reference and no `desloppify`/`novel-desloppify`
      console-script invocation anywhere in the three files.
      Evidence (live, planning run 2026-06-26):
      `grep -nE 'desloppify' state-layout.md` → lines 167, 168 ("run
      desloppify", "If desloppify is run"); `done-conditions.md` → lines 110
      ("One full-novel desloppify pass logged"), 191 ("each step (desloppify,
      …)"); `critic-personas.md` → line 162 ("run desloppify on the edited
      passages"). `grep -nE 'wordcount|novel-desloppify|desloppify ' ` over all
      three returns nothing matching a console-script invocation.
      Impact: The conversion alternation is exactly
      `novel-state|novel-compile|novel-done`. The "no retired
      `desloppify`/`wordcount` console-script reference survives" criterion is
      already satisfied; the work is to keep it satisfied by NOT touching the
      noun forms.

    - Observation (live re-confirmation, Work items 0-1, 2026-06-26): The
      planning enumeration holds exactly against the live worktree. The convert
      bucket is `state-layout.md` `novel-state` ×15 (lines 118, 181, 190, 201,
      211, 214, 217, 223, 230 ×2, 237, 239, 256, 257, 260) + `novel-compile` ×1
      (239); `done-conditions.md` `novel-done` ×5 (17, 18, 141, 144, 145);
      `critic-personas.md` `novel-done` ×2 (131, 133).
      `grep -oE 'novel-state' state-layout.md | wc -l` returns 15. The preserve
      bucket is the five `desloppify` noun forms (state-layout 167-168,
      done-conditions 110/191, critic-personas 162). The third grep
      (`wordcount|novel-desloppify`) over the three files is empty.
      Evidence: `grep -rnE 'novel-state|novel-done|novel-compile' tests/`
      returns only docstrings and fixtures (e.g.
      `tests/test_state_layout_reference.py:252` synthetic fence,
      `tests/corpus_done_predicate_fixtures.py` docstrings,
      `tests/test_gate_drafting_mutators_e2e.py:93` `"novel-state-run"` catalogue
      name); none reads a reference body and asserts its command spelling.
      Impact: The sweep cannot turn `make all` red; the operative gates are
      `make markdownlint` and `make nixie` per item, with `make all` once at the
      end.

    - Observation (Work item 3, 2026-06-26): The Work item 5 mis-sweep gate
      `grep -nE 'novel desloppify' $REFS` yields a **false positive** on
      `done-conditions.md:110` ("One full-novel desloppify pass logged") because
      the substring "novel desloppify" also appears inside the hyphenated
      adjective phrase "full-novel desloppify". This is NOT a mis-swept command.
      Evidence: `git diff` shows no `desloppify` line changed (the five noun
      forms are byte-for-byte preserved). The trustworthy mis-sweep check is the
      backtick-anchored form `grep -nE '`novel desloppify`' $REFS` (a command is
      always code-spanned) or inspecting the diff; both return empty.
      Impact: When running the Work item 5 gate, read the `novel desloppify` hit
      against the diff; the line-110 match is benign prose, not a regression.

## Decision log

    - Decision: Treat 1.2.17 as a three-file, documentation-only sweep with
      `make markdownlint` + `make nixie` as the operative gates, plus `make all`
      run once at the end to confirm no code/test breakage, rather than
      re-running the whole suite per item.
      Rationale: The roadmap success criterion names exactly the three reference
      files; no code, test, or behaviour changes; no test asserts on a command
      spelling in these bodies (Work item 0 re-confirms live).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Convert only `novel-state`, `novel-compile`, and `novel-done`;
      preserve every `desloppify` noun form verbatim and add no `wordcount`
      reference.
      Rationale: The roadmap explicitly distinguishes the retired console-script
      from the operation noun and warns against mis-sweeping the latter. The live
      enumeration shows every `desloppify` in these files is the noun form, and
      no `wordcount`/`desloppify` console-script invocation exists to flip. The
      design document itself uses the `desloppify` noun form (§4.4).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Exclude all `tests/` literals (the
      `novel-state set-cursor --chapter 7` fixture and the working-corpus
      docstrings) from this sweep.
      Rationale: Roadmap sub-task 1.2.8.5 explicitly owns those stale test
      literals and places them "outside the `skill/novel-ralph/references/` scope
      of 1.2.17". Touching them here would duplicate or collide with that
      addendum.
      Date/Author: 2026-06-26, planning agent.

    - Decision: No cuprum API and no other locked external-library behaviour is
      load-bearing for this task, so there is no cuprum forking decision and no
      external-library behaviour to verify by web research.
      Rationale: This is a Markdown prose sweep. It exercises no
      `cuprum.catalogue`/`Program`/`run` surface (verified: the only cuprum use
      in the repo is the test scaffolding `single_program_catalogue` fixture,
      untouched here), no Cyclopts `--help`/`--version` path, no pytest-timeout
      or pytest-xdist behaviour, and no `uv run` resolution semantics. The
      operative gates are `make markdownlint`, `make nixie`, and `make all`.
      For completeness, the locked cuprum is **0.1.0** (`uv.lock` lines 113-114).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Correct the preserved `desloppify` noun-form count from "six" to
      "five" throughout the plan (Work item 1 enumeration, Work item 5 gate
      comment, and the acceptance text).
      Rationale: The live count is five tokens across five lines (state-layout
      167-168, done-conditions 110/191, critic-personas 162):
      `grep -ohE 'desloppify' <three refs> | wc -l` returns 5. The earlier "six"
      was an off-by-one. CodeRabbit (Work item 2 review, minor) flagged the
      inconsistency. The convert/preserve buckets and the swept literals are
      unaffected; only the count word changes.
      Date/Author: 2026-06-26, implementing agent.

    - Decision: Soften the `make fmt` prohibition: keep the tree-wide target out
      of scope (it re-flows all 267 Markdown files, churning ~250 unrelated to
      this task) but permit a **scoped** format of only the edited reference
      files (`mdtablefix … --in-place <file>` then `markdownlint-cli2 --fix
      <file>`). For this sweep the literal swap alone is already
      `make markdownlint`-clean (hyphenated and spaced forms share a character
      count), so no scoped re-wrap was needed; the edited references keep the
      minimal literal-swap diff. Note `make all`'s `check-fmt` checks only Python
      (ruff), not Markdown, so Markdown formatting is gated solely by
      `make markdownlint`.
      Rationale: AGENTS.md line 170 asks for `make fmt` after documentation
      changes; CodeRabbit (Work item 2 review, major) flagged that a flat ban
      conflicts with that rule. Scoping the format to the edited files honours
      both the repo rule and this task's edit-only-three-files constraint.
      Date/Author: 2026-06-26, implementing agent.

## Outcomes & retrospective

Completed 2026-06-26. The sweep met every success criterion. Final transcript
from the worktree root:

    # SURFACE gate — no retired console-script invocation survives:
    $ grep -nE 'novel-state|novel-compile|novel-done' <three refs>
    (empty)

    # Noun-form preservation — five desloppify lines, count unchanged:
    $ grep -nE 'desloppify' <three refs>
    state-layout.md:167  - If the chapter's beats are complete, run desloppify.
    state-layout.md:168  - If desloppify is run, advance to the spiteful …
    done-conditions.md:110  - One full-novel desloppify pass logged.
    done-conditions.md:191  … each step (desloppify, spiteful, image …
    critic-personas.md:162  … After addressing, run desloppify on the edited …
    $ grep -ohE 'desloppify' <three refs> | wc -l
    5

    # No mis-swept command and no reintroduced retired script:
    $ grep -nE '`novel desloppify`' <three refs>       (empty)
    $ grep -nE 'wordcount|novel-desloppify' <three refs> (empty)

    # Gates:
    $ make markdownlint   → Summary: 0 error(s)
    $ make nixie          → All diagrams validated successfully!
    $ make all            → 1171 passed, 1 skipped

Each criterion held: no `novel-state`/`novel-compile`/`novel-done`
console-script invocation survives the three reference files; the five
`desloppify` noun forms are byte-for-byte preserved; `make markdownlint`,
`make nixie`, and `make all` are all green.

Lessons learned:

- The planning enumeration was accurate apart from a single off-by-one count
  word ("six" preserved noun forms where the live count is five). The token
  count, not the line count, is the trustworthy figure
  (`grep -ohE 'desloppify' | wc -l`). CodeRabbit caught this on the first review.
- The literal swap is genuinely length-preserving, so the file-level diffs are
  minimal (14 / 5 / 2 changed lines) and `make markdownlint` stayed clean
  without any re-wrap. The pre-existing over-80 lines in the references were left
  untouched, in keeping with the substance-preservation constraint; they are
  within markdownlint's MD013 inline-code tolerance.
- The `grep 'novel desloppify'` mis-sweep gate has a benign false positive on
  "full-novel desloppify"; anchor the check on backticks (a real command is
  always code-spanned) or read it against the diff.
- The repo's `check-fmt` gate covers only Python (ruff), so Markdown formatting
  is enforced solely by `make markdownlint` plus the optional `make fmt`. The
  tree-wide `make fmt` is unsafe here (it would churn ~250 unrelated files); the
  scoped substitute is the right tool when a re-wrap is genuinely needed.

## Context and orientation

A novice should read these before touching anything:

- [docs/roadmap.md](../roadmap.md), task 1.2.17 (the step-task paragraph and its
  success criterion) and its parent step 1.2 — the source of truth for scope and
  acceptance. Read also task 1.2.8.5 (the test-literal sweep that owns the
  `tests/` `novel-state` literals this task must NOT touch) and tasks 1.2.14 /
  1.2.16 (the design/`SKILL.md` and guide sweeps this task extends).
- [docs/adr-007-command-surface-novel-multiplexer.md](../adr-007-command-surface-novel-multiplexer.md)
  — fixes the surface as a single `novel` multiplexer (supersedes ADR 005). Its
  "Decision outcome" section (lines 90-96) lists the exact subcommand structure:
  `novel state init | set-cursor | advance-phase | recount | check | reconcile`,
  `novel done`, `novel compile [--check]`, `novel desloppify [...]`,
  `novel wordcount`. Its "Decision drivers" (line 40, "avoid generic global
  names (`wordcount`, `desloppify`)") is why the *console-script* was namespaced
  under `novel` — but the operation *noun* is unaffected.
- [docs/novel-ralph-harness-design.md](../novel-ralph-harness-design.md) §4
  ("The deterministic commands") and §4.1-§4.5 — the authoritative description
  of each operation's behaviour. **Caveat:** §4's *command literals* in body
  prose are largely written in the retired hyphenated form (recorded in the
  1.2.16 execplan), so quote §4 only for *behaviour*, and take every command
  spelling from `names.py` `SUBCOMMAND_NAMES` / ADR 007, not from §4's body.
  Note §4.4 uses the `desloppify` **noun** form (lines 414, 423) — confirmation
  that the noun stays.
- [AGENTS.md](../../AGENTS.md) — quality gates ("Validate Markdown files using
  `make markdownlint`"; "Validate Mermaid diagrams … `make nixie`", lines
  169-172), the 400-line module cap (not relevant; no code touched), the en-GB
  Oxford spelling rule (line 18), and the commit-message convention (imperative
  subject ≤50 chars, lines 103-106).
- [docs/scripting-standards.md](../scripting-standards.md) and
  [docs/documentation-style-guide.md](../documentation-style-guide.md) — house
  style the references already follow.
- [docs/execplans/roadmap-1-2-16.md](roadmap-1-2-16.md) — the immediately prior
  sibling sweep (the two guides). Its Decision Log records the `make fmt`
  tree-wide-churn finding and the spaced-surface vocabulary discipline this plan
  reuses.

The single, authoritative source of the surface vocabulary is
[`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
together with ADR 007: `SUBCOMMAND_NAMES` is exactly
`("novel state", "novel done", "novel compile", "novel desloppify",
"novel wordcount")` and `project_scripts_table()` returns `{"novel": …}`. Every
command form written into a reference must match this file.

Terms used in this plan:

- **Console-script invocation**: a token naming the command the harness or a
  user types on the shell — `novel-state check`, `novel-compile`, `novel-done`.
  These are converted to `novel state check`, `novel compile`, `novel done`.
- **Operation noun (`desloppify`)**: the desloppification pass named as a verb
  or noun in running prose ("run desloppify", "a full-novel desloppify pass").
  This is NOT a command the user types; it is preserved verbatim.
- **Test literal**: a `novel-state`/`novel-done` token inside `tests/` (a
  fixture or docstring). Owned by task 1.2.8.5; out of scope here.

Library-API note (verification, not a change): no cuprum API and no other locked
external library is exercised by this task; it is a Markdown sweep. See the
Decision Log entry. Locked cuprum is 0.1.0 (`uv.lock` lines 113-114).

## Plan of work

The sweep proceeds file by file, each behind its own Markdown gate, so a
stopping point never leaves a half-converted reference. Stage A (Work items 0-1)
understands and enumerates without editing; Stage B (Work items 2-4) sweeps each
reference; Stage C (Work item 5) proves the whole end-state and runs `make all`.

### Work item 0 — Orientation and reference grep (no edits)

Implements: roadmap 1.2.17 scope; ADR 007 surface vocabulary; the
test-body-safety finding.

Read, in order: roadmap 1.2.17 (and 1.2.8.5, 1.2.14, 1.2.16 for scope
boundaries), ADR 007 (Decision outcome + Decision drivers), design §4-§4.5,
AGENTS.md Markdown sections, and the three reference files end to end. No file is
edited in this item.

Re-confirm live that no test asserts on a command spelling in these reference
bodies, so `make all` cannot break:

    grep -rnE 'novel-state|novel-done|novel-compile' tests/

Expect: only docstrings and fixtures (notably
`tests/test_state_layout_reference.py:252`'s synthetic fence and the
`tests/working_corpus/` docstrings); confirm none reads a reference body and
asserts its command spelling. Record the confirmation in
`Surprises & Discoveries`.

Docs to read: roadmap.md (1.2.17, 1.2.8.5, 1.2.14, 1.2.16), adr-007, design §4,
AGENTS.md, scripting-standards.md, documentation-style-guide.md,
docs/execplans/roadmap-1-2-16.md.

Skills to load: `execplans` (this plan's format), `en-gb-oxendict` (spelling
convention for every edited sentence). Use `leta` (`leta show`, `leta files`)
and `grepai search` for navigation rather than ad-hoc reads.

Tests: none (no behaviour change). Validation: confirm the spaced forms in ADR
007 / design §4 headings match `SUBCOMMAND_NAMES` in
`novel_ralph_skill/commands/names.py`, and confirm the live `tests/` grep matches
the Work-item-0 expectation.

### Work item 1 — Record the per-file convert/preserve enumeration

Implements: the Constraints' noun-form boundary; Risk 1 mitigation.

Run the enumerating greps below and record, in `Surprises & Discoveries`, the
per-file list split into two buckets: **convert** (console-script invocations)
and **preserve** (the `desloppify` noun form). This enumeration is the contract
the three sweep items execute against, so a later edit cannot silently flip a
noun form.

Commands (run from the worktree root):

    REFS='skill/novel-ralph/references'
    # Convert bucket — console-script invocations:
    grep -nE 'novel-state|novel-compile|novel-done' \
      "$REFS/state-layout.md" "$REFS/done-conditions.md" \
      "$REFS/critic-personas.md"
    # Preserve bucket — the desloppify operation noun (must NOT be converted):
    grep -nE 'desloppify' \
      "$REFS/state-layout.md" "$REFS/done-conditions.md" \
      "$REFS/critic-personas.md"
    # Confirm there is no retired desloppify/wordcount console-script to flip:
    grep -nE 'wordcount|novel-desloppify|`desloppify`|desloppify (--|init|run )' \
      "$REFS/state-layout.md" "$REFS/done-conditions.md" \
      "$REFS/critic-personas.md"

Expected (from the planning run; re-confirm live):

- `state-layout.md` convert: 15 `novel-state` hits across 14 lines — 118, 181,
  190, 201, 211, 214, 217, 223, 230 (×2: `complete-final-pass` + `set-gate
  --final`), 237, 239, 256, 257, 260 — plus one `novel-compile` at line 239.
  That is 16 convertible tokens. Line 239 is a two-token line carrying BOTH
  `novel-state set-chapters` AND `novel-compile`. Verify the count live:
  `grep -oE 'novel-state' state-layout.md | wc -l` returns 15.
- `done-conditions.md` convert: `novel-done` at lines 17, 18, 141, 144, 145.
- `critic-personas.md` convert: `novel-done` at lines 131, 133.
- preserve: `desloppify` noun at `state-layout.md` 167-168, `done-conditions.md`
  110, 191, `critic-personas.md` 162.
- third grep: empty (no console-script `desloppify`/`wordcount` to convert).

Docs to read: this plan's Constraints and Risks.

Skills to load: `leta` (resolve any ambiguous token with `leta show` to confirm
it is a doc reference, not a code symbol, before bucketing).

Tests: none. Validation: the enumeration is recorded in this plan and every grep
hit appears in exactly one bucket.

### Work item 2 — Sweep `state-layout.md` to the `novel` surface

Implements: roadmap 1.2.17 success criterion (state-layout half); ADR 007
Decision outcome; design §4.1, §4.3.

Independently committable. Edit only
`skill/novel-ralph/references/state-layout.md`. Apply the Work-item-1 convert
bucket: flip every `novel-state <verb>` → `novel state <verb>` and the one
`novel-compile` → `novel compile`, preserving each surrounding sentence verbatim
apart from the command literal. Specifically:

- `novel-state set-chapters` → `novel state set-chapters` (lines 118, 239).
- `novel-state set-critic-pass --pass N` → `novel state set-critic-pass --pass N`
  (line 181).
- `novel-state check` → `novel state check` (lines 190, 214, 237, 256, 257).
- `novel-state set-fangirl --last-chapter N` → `novel state set-fangirl
  --last-chapter N` (line 201).
- `novel-state set-gate --knitting-30` (and `--knitting-NN`/`--final`) →
  `novel state set-gate …` (lines 211, 223, 230).
- `novel-state recount` → `novel state recount` (line 217).
- `novel-state complete-final-pass` → `novel state complete-final-pass`
  (line 230, the second hit on that line).
- `novel-compile` → `novel compile` (line 239).
- `novel-state reconcile` → `novel state reconcile` (line 257).
- `novel-state init` → `novel state init` (lines 257-ish, 260).

**Preserve verbatim**: the `desloppify` noun form at lines 167-168 ("run
desloppify", "If desloppify is run"). Do not touch them. Do not alter the
`state.toml`-write discipline prose, the ADR-001/ADR-008/ADR-010 references, the
exit-code-3 contracts, the gate-ratio binding wording, or the `[pending_turn]`
reconciliation paragraph — only the command literal changes.

Docs to read: design §4.1 (`novel state` behaviour) and §4.3 (`novel compile`
index follower) — behaviour only; take the spaced spelling from `names.py`
`SUBCOMMAND_NAMES`. ADR 007 (subcommand structure). AGENTS.md Markdown guidance
(80-column prose).

Skills to load: `en-gb-oxendict` (every reworded clause stays en-GB Oxford
spelling), `leta`/`grepai` for navigation.

Tests: none — documentation. Per the AGENTS.md testing rules, a
documentation-only change that alters no externally observable behaviour adds no
unit, behavioural, property, snapshot, or e2e test; the Markdown gates plus the
existing body guards (`test_state_layout_reference.py`, unchanged and still
green because the command-name flip does not introduce a write recipe) are the
verification.

Validation: run `make markdownlint` (expect clean) and confirm
`grep -nE 'novel-state|novel-compile' state-layout.md` returns nothing, then
commit with an imperative subject (for example, "Sweep state-layout reference to
the novel surface"). Final whole-tree proof is Work item 5.

### Work item 3 — Sweep `done-conditions.md` to the `novel` surface

Implements: roadmap 1.2.17 success criterion (done-conditions half); ADR 007;
design §4.2.

Independently committable. Edit only
`skill/novel-ralph/references/done-conditions.md`. Flip every `novel-done` →
`novel done` (lines 17, 18, 141, 144, 145), preserving each sentence — the
"single source of truth for the novel-level predicate" framing, the
six-clauses/`done_predicate.py` cross-reference, and the
`contains_unresolved_blocker` convention — verbatim apart from the command
literal.

**Preserve verbatim**: the `desloppify` noun form at line 110 ("One full-novel
desloppify pass logged") and line 191 ("each step (desloppify, spiteful, image
verification)"). Do not touch them.

Docs to read: design §4.2 (`novel done` predicate) — behaviour only; ADR 007.
AGENTS.md Markdown guidance.

Skills to load: `en-gb-oxendict`, `leta`/`grepai`.

Tests: none — documentation (same rationale as Work item 2).

Validation: `make markdownlint` (expect clean) and
`grep -nE 'novel-done' done-conditions.md` returns nothing; commit with an
imperative subject. Final proof is Work item 5.

### Work item 4 — Sweep `critic-personas.md` to the `novel` surface

Implements: roadmap 1.2.17 success criterion (critic-personas half); ADR 007;
design §4.2.

Independently committable. Edit only
`skill/novel-ralph/references/critic-personas.md`. Flip both `novel-done` →
`novel done` (lines 131, 133) in the "Resolving a BLOCKER" subsection,
preserving the producer/consumer convention prose verbatim apart from the
command literal.

**Preserve verbatim**: the `desloppify` noun form at line 162 ("run desloppify
on the edited passages"). Do not touch it. Do not alter any persona system
prompt, the BLOCKER/`[resolved]` token convention, or the format examples.

Docs to read: design §4.2 (`novel done` reads `critic-notes.md`) — behaviour
only; ADR 007. AGENTS.md Markdown guidance.

Skills to load: `en-gb-oxendict`, `leta`/`grepai`.

Tests: none — documentation (same rationale as Work item 2).

Validation: `make markdownlint` (expect clean) and
`grep -nE 'novel-done' critic-personas.md` returns nothing; commit with an
imperative subject. Final proof is Work item 5.

### Work item 5 — Gate the sweep and prove the end-state

Implements: AGENTS.md Markdown gates; roadmap 1.2.17 success criterion (final
proof).

Run, from the worktree root:

    REFS='skill/novel-ralph/references/state-layout.md'
    REFS="$REFS skill/novel-ralph/references/done-conditions.md"
    REFS="$REFS skill/novel-ralph/references/critic-personas.md"

    # Markdown gates (avoid tree-wide `make fmt`; scoped format or hand-wrap at
    # 80 cols on the edited references only — Decision Log / Risk 2).
    make markdownlint   # expect: clean
    make nixie          # expect: clean (no reference carries Mermaid)

    # Surface gate: no retired console-script invocation survives. Expect: empty.
    grep -nE 'novel-state|novel-compile|novel-done' $REFS

    # Noun-form preservation gate: the desloppify count is unchanged AND no
    # token became `novel desloppify`. Expect: the same five noun-form lines as
    # Work item 1 (state-layout 167-168, done-conditions 110/191,
    # critic-personas 162), and the second grep empty (no noun form mis-swept).
    grep -nE 'desloppify' $REFS
    grep -nE 'novel desloppify' $REFS    # expect: empty

    # No retired desloppify/wordcount console-script reference was introduced.
    grep -nE 'wordcount|novel-desloppify' $REFS   # expect: empty

    make all            # expect: green; confirms no code/test breakage

Acceptance: `make markdownlint` and `make nixie` exit 0; the surface grep
returns nothing (no `novel-state`/`novel-compile`/`novel-done` survives); the
`desloppify` grep returns exactly the five preserved noun-form lines from Work
item 1 (count unchanged); the `novel desloppify` and `wordcount|novel-desloppify`
greps return nothing (no noun form mis-swept, no console-script reference
introduced); and `make all` is green.

If any gate fails, fix within tolerance (Risk 2 mitigation: scoped format or
re-wrap at 80 columns on the edited references; avoid tree-wide `make fmt`) and
re-run before the final commit. Record the
final transcript in `Outcomes & Retrospective` and flip the plan Status to
COMPLETE.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` is green (1100+ passed; no test asserts on a command
  spelling in these reference bodies, so the suite is unaffected by the sweep).
- Lint/typecheck: `make markdownlint` and `make nixie` exit 0 on the three
  edited references.
- Surface: `grep -nE 'novel-state|novel-compile|novel-done'` over the three
  references returns nothing.
- Noun-form preservation: the `desloppify` occurrence count over the three
  references is unchanged from before the sweep, and `grep 'novel desloppify'`
  over them returns nothing.

Quality method (how we check): the Work-item-5 gate block above, run from the
worktree root.

## Idempotence and recovery

Each work item is a single-file edit followed by a Markdown gate and an atomic
commit, so the sweep is resumable from the `Progress` checklist. Re-running a
gate is safe and side-effect-free. If a commit must be undone, `git revert` the
single-file commit; no state is shared between items. The conversion is a pure
literal flip with a noun-form preserve list, so re-applying it to an
already-swept file is a no-op (the surface grep returns empty).

## Artefacts and notes

The authoritative convert/preserve enumeration (from the planning run, to be
re-confirmed live in Work item 1):

    state-layout.md    convert: novel-state ×15 (118,181,190,201,211,214,217,
                                223,230×2,237,239,256,257,260);
                                novel-compile ×1 (239)
                                = 16 convertible tokens. Line 230 is a
                                two-token novel-state line (complete-final-pass
                                + set-gate --final). Line 239 is a two-token
                                cross-type line (novel-state set-chapters +
                                novel-compile).
                       preserve: desloppify noun (167,168)
    done-conditions.md convert: novel-done ×5 (17,18,141,144,145)
                       preserve: desloppify noun (110,191)
    critic-personas.md convert: novel-done ×2 (131,133)
                       preserve: desloppify noun (162)

## Interfaces and dependencies

No code interface changes. The only external contract this plan depends on is
the surface vocabulary in
[`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
`SUBCOMMAND_NAMES` and ADR 007's subcommand structure: the spaced command forms
`novel state <verb>`, `novel done`, and `novel compile` are exactly the forms
written into the three references. No new dependency is introduced.

## Revision note

- 2026-06-26 (planning round 2): Corrected the `state-layout.md` convert-bucket
  count from `novel-state ×17` to the verified `novel-state ×15` (across 14
  lines, line 230 carrying two `novel-state` tokens) plus `novel-compile ×1`,
  for 16 convertible tokens total. Annotated line 239 as a two-token cross-type
  line carrying BOTH `novel-state set-chapters` AND `novel-compile`. The fix was
  applied in all three places the enumeration appears — the Purpose paragraph,
  Work item 1's expected output (now with a live `grep -oE 'novel-state' … | wc
  -l` → 15 check), and the Artefacts enumeration — and in Risk 3's "15
  occurrences" phrasing. This resolves design-review blocking points B1
  (off-by-two count) and B2 (line-239 under-count) so Work item 1's contract and
  Work item 5's count audit reconcile against the live file. No edit
  instruction, gate command, scope boundary, or noun-form preserve list changed;
  Work item 2's per-edit list already converted both tokens on line 239
  correctly. The per-file convert/preserve sweep is otherwise unchanged.
- 2026-06-26 (review fix round 1): Rebased the branch onto `origin/main` to
  resolve the dual review's sole blocking item. After this branch forked at
  `b89373c`, sibling task 1.2.8.5 landed as `d2932f0`, sweeping the residual
  `novel-state` literals in `tests/test_state_layout_reference.py` to `novel
  state` and ticking roadmap 1.2.8.5 to `[x]`. Because the branch lacked
  `d2932f0`, `git diff origin/main..HEAD` falsely showed it reverting that
  landed work (the test file flipping `novel state` back to `novel-state`, and
  `docs/roadmap.md` plus `docs/execplans/roadmap-1-2-8.md` flipping 1.2.8.5 from
  `[x]` to `[ ]`); none of the four 1.2.17 commits touch those files, so the
  apparent reversion was pure staleness. The rebase was pre-verified
  conflict-free (`git merge-tree --write-tree origin/main HEAD` exited 0 with no
  conflict marker) and replayed the four sweep commits cleanly onto `d2932f0`.
  The diff now reduces to the three reference-file sweeps plus the two execplan
  files, with the test-file and 1.2.8.5 reversions gone. Deterministic gates
  (`make all`, `make markdownlint`, `make nixie`) re-run green after the rebase.
  No sweep edit, gate command, or scope boundary changed.

## Addenda

- [x] 1.2.17.1 (from review:1.2.17 and audit:1.2.17; medium; two near-identical
  proposals merged). Sweep the residual flag-bearing `desloppify --pack` and
  `desloppify --ledger` console-script invocations in
  `skill/novel-ralph/references/desloppify-checklist.md` (around lines 294 and
  302) to the `novel desloppify --pack` / `novel desloppify --ledger` surface.
  This sibling reference file shares the same directory 1.2.17 swept but sits
  outside this plans three-file success criterion (`state-layout.md`,
  `done-conditions.md`, `critic-personas.md`), so its retired flag-bearing
  surface survived untracked. The flags distinguish these from the preserved
  noun-form `desloppify` mentions that name the desloppification operation
  rather than the retired console-script; preserve every noun-form mention.
  Lightweight addendum pass: no plan or design-review cycle, just the two
  invocation flips, the gates (`make markdownlint`, `make nixie`), and a merge.
