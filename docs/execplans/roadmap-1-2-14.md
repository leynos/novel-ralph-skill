# Sweep the design document and `SKILL.md` to the `novel` multiplexer surface

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 1.2.15 retired the five legacy console-scripts (`novel-state`,
`novel-done`, `novel-compile`, `desloppify`, `wordcount`) and deleted the
`stub.py` factory, so the package now ships **exactly one** `[project.scripts]`
entry — `novel` — dispatching into a `state` subgroup and four leaf verbs
(`novel state …`, `novel done`, `novel compile`, `novel desloppify`,
`novel wordcount`). This is verified in the worktree: `pyproject.toml` lists
only `novel = "novel_ralph_skill.commands.novel:main"`, and
`novel_ralph_skill/commands/names.py` holds the spaced surface vocabulary as the
single source of truth.

Two repository documents still describe the retired per-command scripts, because
this task (1.2.14) was specified but never executed (its body was orphaned under
roadmap sub-task 1.2.15.1 with no checkbox until promoted):

1. `docs/novel-ralph-harness-design.md` carries **44 lines** that name the
   retired hyphenated console-scripts (`grep -cE
   'novel-state|novel-done|novel-compile' …` returns 44; the count rises to 65
   if the bare `desloppify`/`wordcount` operation-noun hits are also counted).
   The §4 *intro* (lines 267-274) and the §4.1-§4.5 subsection *headings* were
   already updated to the spaced form, but the **§2.3 Verification scope** prose
   (lines 112 `novel-state` validator, 115 `novel-done` returns, 121
   `novel-compile --check`, 123 `novel-done` compile clause), the **§3.1 Output
   modes** envelope example (line 148 `"command": "novel-done"`), the §3 tables,
   the two Mermaid diagrams (Figure 1 at lines 53-73, Figure 3 at lines
   798-810), and the §4 body (including the §4.2 envelope example at line 358
   `"command": "novel-done"`), §5, §9, and §10 prose still carry hyphenated
   literals. The design is therefore in a **mixed** state, which is itself a
   defect: a reader sees both forms.
2. `skill/novel-ralph/SKILL.md` carries **33 hyphenated occurrences** across 26
   lines, presents the harness in its Setup section as "five console-scripts",
   and verifies the install with `novel-state --version` — a command that **no
   longer exists** (only `novel` is on `PATH`). Anyone following the Setup
   section verbatim would hit "command not found" and conclude the package is
   broken.

After this change a reader of either file sees the single `novel <sub>` surface
the package actually ships, with no surviving console-script reference and a
Setup install check (`novel --version`) that resolves against the installed
binary. The work is a **documentation-only** sweep: it edits two Markdown files
and touches no Python, no tests, and no command behaviour, so `make all` stays
green by construction (verified: no test asserts on the *content* of either file
— see `Surprises & Discoveries`). Success is observable by grep (no
command-surface literal survives, the noun-form operation references and the
`desloppify-checklist.md` filename are preserved) and by the Markdown gates
(`make markdownlint` and `make nixie` pass; `make nixie` is load-bearing here
because the design doc contains two Mermaid diagrams whose nodes are swept).

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- Edit only `docs/novel-ralph-harness-design.md` and
  `skill/novel-ralph/SKILL.md`. Do not modify any other file: not the roadmap,
  not the ADRs, not the users'/developers' guides (owned by completed task
  1.2.16), not the reference files under `skill/novel-ralph/references/` (owned
  by task 1.2.17), not any code or test. The roadmap 1.2.14 success criterion
  names exactly the design document and `SKILL.md`.
- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-14`. Never
  read-modify-write any file in the root/control worktree.
- The surface vocabulary is fixed by
  [ADR 007](../adr-007-command-surface-novel-multiplexer.md). The subcommands
  are
  `novel state init | set-cursor | advance-phase | recount | check | reconcile`
  (plus `set-chapters`, `set-gate`, `complete-final-pass`, `set-fangirl`,
  `set-critic-pass` under `novel state`); `novel done`;
  `novel compile [--check]`;
  `novel desloppify [--pack … | --ledger …] [--chapter …]`; `novel wordcount`.
  Use exactly these spaced forms; do not invent `novel-desloppify`-style
  hyphenated namespacing (Option A, which ADR 007 rejected). Confirm every
  command form written into either file against
  `novel_ralph_skill/commands/names.py` `SUBCOMMAND_NAMES`, **never** against
  design §4's body prose, whose command literals are still hyphenated until this
  sweep flips them.
- **Convert the JSON envelope `command` field exactly.** The two JSON envelope
  examples at design line 148 (§3.1 Output modes) and line 358 (§4.2 `novel
  done`) carry `"command": "novel-done"`. The multiplexer stamps the **spaced**
  form into this field: `names.py` `ENVELOPE_COMMAND_NAMES` (line 53) is derived
  from `SUBCOMMAND_NAMES` (line 40), whose entry is exactly `"novel done"`
  (line 42). Both envelope lines must become `"command": "novel done"`,
  confirmed character-for-character against `names.py` `SUBCOMMAND_NAMES` —
  **not** a `novel-done` → `novel done` text reflex. This is the most
  contract-sensitive convert target in the file: the envelope `command` string
  is part of the harness's machine-read output contract, so an off-by-one
  spacing or a stray hyphen is a contract defect, not a prose nit. Verify both
  with `grep -n '"command":' "$DESIGN"` returning exactly `"novel done"` after
  the sweep.
- **Preserve the `desloppify-checklist.md` filename verbatim.** It is a
  reference-document filename (`skill/novel-ralph/references/`), not a
  console-script reference. It appears 3 times in `SKILL.md` and once in the
  design (line 938). A blind `desloppify` → `novel desloppify` substitution
  would corrupt it to `novel desloppify-checklist.md`. This is the
  code-identifier-equivalent preserve case for this task.
- **Preserve the ADR-005 supersession history.** The design doc references
  `adr-005-command-surface-five-scripts.md` only as explicit superseded history
  (line 18, a references-list filename; line 274, "superseding ADR 005"). These
  are legitimate historical record, not present-tense surface claims, and are
  left verbatim (1.2.16 precedent, Decision Log).
- **Preserve `console-script` distribution prose that is true of the single
  surface.** The design's distribution prose (lines 103, 268, 279, 881, 890)
  describes the package being installed as a console-script — still true of the
  single `novel` entry point (ADR 004 distribution is unchanged per ADR 007).
  These are not "five separate scripts" claims and stay. Only convert prose that
  frames the surface as *multiple* separate scripts (e.g. `SKILL.md` line 28).
- All prose must be en-GB Oxford spelling (`-ize`/`-yse`/`-our`), matching the
  surrounding documents.

## Tolerances (exception triggers)

- Scope: this plan edits exactly two files. If a truthfulness fix appears to
  require editing a third file, stop and escalate (it likely belongs to sibling
  task 1.2.16 or 1.2.17).
- Noun-vs-script ambiguity: if a bare `` `desloppify` `` or `` `wordcount` ``
  cannot be confidently classified as either an *operation noun* (preserve) or a
  *command invocation* (convert to `novel desloppify` / `novel wordcount`) by
  the rule in the Decision Log, stop and record the specific line in the
  `Decision Log` before guessing. Do **not** mass-substitute bare
  `desloppify`/`wordcount`.
- Mermaid: if `make nixie` fails after a diagram-node edit, stop and inspect —
  a swept node label with a space (e.g. `ST[novel state]`) is valid Mermaid, but
  a stray bracket or arrow corruption is not. Fix within 3 attempts or escalate.
- Gate iterations: if `make markdownlint` still fails after 3 fix attempts on a
  single work item, stop and escalate.

## Risks

    - Risk: A blind `desloppify` → `novel desloppify` substitution corrupts the
      `desloppify-checklist.md` filename to `novel desloppify-checklist.md`,
      breaking a documentation cross-reference.
      Severity: high
      Likelihood: high
      Mitigation: Never run a blind `sed`. Work item 1 enumerates and classifies
      every `desloppify`/`wordcount` hit into convert (command invocation),
      preserve-noun (operation name), and preserve-filename
      (`desloppify-checklist.md`) buckets before any edit. The work item 5 gate
      asserts `desloppify-checklist.md` survives at its original count
      (SKILL.md 3, design 1).

    - Risk: Over-sweeping bare `` `desloppify` `` / `` `wordcount` `` that name
      the *operation* (e.g. "`desloppify` detects; it never edits", "`wordcount`
      reports, per chapter …", "the desloppify command reads versioned
      configuration") into `novel desloppify` / `novel wordcount`, making the
      prose read as though every mention is a shell invocation. Conversely,
      UNDER-sweeping a genuine invocation (e.g. the Figure 3 node `novel-state
      recount / novel-done / wordcount`, which lists commands run in the
      pipeline) leaves a console-script reference alive.
      Severity: medium
      Likelihood: high
      Mitigation: Work item 1 applies the explicit classification rule (Decision
      Log, mirrored from roadmap task 1.2.17's stated distinction): convert a
      bare token to `novel <verb>` only where the surrounding clause names the
      command being *run/invoked* (a shell-style invocation, a pipeline node, a
      flag-bearing form like `desloppify --ledger`, or a table row enumerating
      the *checker commands*); preserve the bare token where the clause uses it
      as the operation/pass *noun* ("the desloppify pass", "what `desloppify`
      detects"). Each ambiguous hit is recorded with its classification in
      `Surprises & Discoveries`; the Tolerances forbid guessing.

    - Risk: `make nixie` fails because a Mermaid node label was edited
      incorrectly (Figure 1 nodes `ST[novel-state]` … and the Figure 3 node
      `G[novel-state recount / novel-done / wordcount]`).
      Severity: medium
      Likelihood: medium
      Mitigation: Mermaid permits spaces inside `[]` node labels, so
      `ST[novel state]` and `G[novel state recount / novel done / novel
      wordcount]` are valid. Edit only the label text inside the brackets, never
      the node id or the arrows. Work item 3 runs `make nixie` immediately after
      the design-doc diagram edits, before committing.

    - Risk: `markdownlint` line-length (80-column prose) regressions after
      rewriting sentences, since `novel state check` is two characters longer
      than `novel-state check` (a space replaces a hyphen, but adding the
      `novel ` prefix to a bare `desloppify`/`wordcount` lengthens the line).
      Severity: low
      Likelihood: medium
      Mitigation: Run `make markdownlint` per work item and hand-wrap at 80
      columns (AGENTS.md Markdown guidance: 80-column prose, 120-column code).
      Do **not** run `make fmt` — in this worktree it re-flows ~250 unrelated
      Markdown files tree-wide and fails on pre-existing `docs/issues/*.md`
      line-length errors, violating the two-file scope (1.2.16 Decision Log,
      verified).

    - Risk: A swept §3 table cell or §9 proof reference pushes a Markdown table
      row over the column budget or breaks table alignment.
      Severity: low
      Likelihood: low
      Mitigation: `markdownlint`'s default table rules tolerate long cells;
      re-align pipes by hand after editing and re-run `make markdownlint`. The
      segregation table (line 242) lists the checker commands and is a convert
      target; the §9 "exit-code proofs" prose (line 884) is too.

## Progress

    - [x] (2026-06-26) Work item 0 — Orientation and reference grep (no edits).
    - [x] (2026-06-26) Work item 1 — Build and record the hit classification for
      both files (convert / preserve-noun / preserve-filename buckets), including
      the noun-vs-script disposition of every bare `desloppify`/`wordcount`. Live
      worktree greps confirmed the planning baseline exactly (DESIGN 14 bare
      `desloppify` / 1 `desloppify-checklist` / 2 `novel desloppify`, 7 bare
      `wordcount` / 2 `novel wordcount`; SKILL 1 bare each / 3
      `desloppify-checklist`; envelope lines 148 and 358 both `"novel-done"`).
    - [x] (2026-06-26) Work item 2 — Swept `docs/novel-ralph-harness-design.md`
      (Figure 1 nodes, §2.3, §3.1 including both JSON envelope `command` fields,
      §3 tables, §3.4, §4 body, §5, §8 Figure 3 node, §9, §10) to the `novel`
      surface; preserve-noun mentions, `desloppify-checklist.md`, ADR-005 history,
      and single-surface console-script distribution prose left verbatim.
    - [x] (2026-06-26) Work item 3 — Gated work item 2: `make markdownlint`
      (re-aligned the §3.3 checker table for MD060) and `make nixie` clean; the
      surface grep's survivors are exactly the 11 `desloppify` / 4 `wordcount`
      preserve-noun mentions; the count gate shows DESIGN 11/1/5 `desloppify` and
      4/5 `wordcount`; both envelope fields read `"command": "novel done"`.
    - [x] (2026-06-26) Work item 4 — Swept `skill/novel-ralph/SKILL.md`: rewrote
      the Setup section to describe the single `novel` multiplexer (a `state`
      subgroup plus four leaf verbs), replaced the `novel-state --version`
      install check with `novel --version`, re-cast the bare-name invocation
      guidance to `novel <sub>`, and converted every body command literal
      (`novel-state`/`novel-done`/`novel-compile` → spaced forms) while
      preserving the three `desloppify-checklist.md` filename references.
    - [x] (2026-06-26) Work item 5 — Gated work item 4: `make markdownlint`,
      `make nixie`, and `make all` (1165 passed, 1 skipped) green. The surface
      grep's survivors over both files are exactly the recorded operation-noun
      mentions plus the preserve-filename references; the count gate shows DESIGN
      11/1/5 `desloppify` and 4/5 `wordcount`, SKILL 0 bare / 3
      `desloppify-checklist` (plus 1 `novel desloppify` / 1 `novel wordcount`
      named in the rewritten Setup); both envelope fields read `"novel done"`;
      `novel-state --version` is gone and `novel --version` is the Setup check;
      `desloppify-checklist` counts are 3 (SKILL) / 1 (design).

## Surprises & discoveries

    - Observation: Neither target file contains a Python code identifier that
      merely *contains* a legacy substring (no `installed_novel_state`,
      `_novel_done.py`, `novel_state.py`, `stub.py`, `make_stub_app`,
      `installed_desloppify`). This task is therefore SIMPLER than 1.2.16 on the
      code-identifier axis: the only preserve cases are the `desloppify-checklist`
      filename and the bare operation-noun mentions of `desloppify`/`wordcount`.
      Evidence: `grep -nE
      'installed_novel_state|_novel_done|novel_state\.py|stub\.py|make_stub_app|installed_desloppify'`
      over both files returns nothing (exit 1).
      Impact: The work item 5 surface gate does not need the token-level
      preserve-subtraction the 1.2.16 plan required for fixtures; it needs only
      to subtract the `desloppify-checklist` filename and the correctly-converted
      `novel desloppify`/`novel wordcount` forms.

    - Observation: The design §4 *intro* (lines 267-274) and §4.1-§4.5
      *headings* already use the spaced `novel <verb>` form; the §4 *body*, §3
      tables, §5, §9, §10 prose, and both Mermaid diagrams do not. The design is
      in a MIXED state.
      Evidence: line 412 heading `### 4.4 \`novel desloppify\`` vs line 414 body
      `` `desloppify` runs the checklist's §6 … ``; line 56 Mermaid node
      `ST[novel-state]`.
      Impact: An implementer cannot mirror §4 as a spaced-surface reference. The
      surface vocabulary source is `names.py` `SUBCOMMAND_NAMES` + ADR 007;
      design §4 supplies per-operation BEHAVIOUR wording only, with every
      command literal re-spaced (the §4 caveat from the 1.2.16 plan applies).

    - Observation: `SKILL.md` Setup (lines 28-45) frames the harness as "five
      console-scripts" in the present tense and runs `novel-state --version` as
      the install check. `novel --version` exists and returns exit 0 with no
      envelope.
      Evidence: `novel_ralph_skill/commands/novel.py` module docstring (lines
      18-20): "`--help`/`--version` and a bare `novel` return `None`, which `run`
      treats as the help/version path (exit `0`, no envelope)";
      `tests/test_multiplexer_dispatch.py` lines 81-82 pin `["--version"]` →
      `"novel"`. `pyproject.toml` line 11 ships only `novel`.
      Impact: Work item 4 reconciles the "five console-scripts" framing to the
      single multiplexer AND replaces `novel-state --version` with
      `novel --version`, satisfying the roadmap criterion's explicit install-check
      clause.

    - Observation: The bare operation-noun preserve baseline is now pinned, so
      work items 3 and 5 can gate over-sweep mechanically (B3). In the design
      doc, the leftmost-longest extraction `grep -oE '(novel
      )?desloppify(-checklist)?'` currently yields `14 desloppify`, `1
      desloppify-checklist`, `2 novel desloppify`; `grep -oE '(novel
      )?wordcount'` yields `7 wordcount`, `2 novel wordcount`. The convert
      anchors are 3 bare `desloppify` (Figure 1 node line 59, §3.3 checker table
      line 242, §9 proofs line 884) and 3 bare `wordcount` (Figure 1 node line
      60, §3.3 checker table line 242, Figure 3 node line 805). Therefore the
      POST-sweep design baseline is exactly: bare `desloppify` = 14 − 3 = **11**
      (preserve-noun), bare `wordcount` = 7 − 3 = **4** (preserve-noun), `novel
      desloppify` = 2 + 3 = **5**, `novel wordcount` = 2 + 3 = **5**,
      `desloppify-checklist` = **1**.
      Evidence: live worktree greps (planning round 2), enumerated per line in
      work item 1. Per-line classification: design preserve-noun `desloppify`
      lines 218, 414, 423, 668, 711, 776, 800 (Figure 3 `B[desloppify: detect]`
      op-label), 812 (caption), 844, 870, 924 (= 11); preserve-noun `wordcount`
      lines 432, 812 (caption), 843, 874 (= 4).
      Impact: An over-swept operation noun raises `novel desloppify`/`novel
      wordcount` above 5/5 and drops the bare count below 11/4, so the
      preserve-noun count gate added to work items 3 and 5 catches it before the
      commit merges green. Without the count assertion the surface gate alone
      could not see over-sweep, because the converted forms are subtracted first.

    - Observation: In `SKILL.md` the only bare `desloppify`/`wordcount` (1 each,
      both on line 29) are inside the "five console-scripts" framing sentence and
      are rewritten away by the Setup-section rewrite (work item 4 step 1); they
      are NOT operation nouns. `desloppify-checklist` appears 3 times (lines 87,
      105, 372, all `references/desloppify-checklist.md`) and is preserved.
      Evidence: live greps `grep -oE '(novel )?desloppify(-checklist)?'` →
      `1 desloppify`, `3 desloppify-checklist`; `grep -oE '(novel )?wordcount'` →
      `1 wordcount`. Line 29 reads "five console-scripts — `novel-state`,
      `novel-done`, `novel-compile`, `desloppify`, and `wordcount`".
      Impact: The POST-sweep `SKILL.md` baseline is exactly: bare `desloppify` =
      **0**, bare `wordcount` = **0**, `desloppify-checklist` = **3**, and any
      `novel desloppify`/`novel wordcount` only if the rewritten Setup prose
      names those subcommands. The work-item-5 preserve-noun gate pins SKILL bare
      nouns at 0/0 and `desloppify-checklist` at 3.

    - Observation: (work item 1 — line-number re-confirmation) The enumerating
      greps must be re-run live in the worktree at the start of the sweep and the
      line numbers re-confirmed on disk, since an earlier edit may shift them.
      The classification buckets and counts above are the contract; the line
      numbers are navigation aids.

## Decision log

    - Decision: Treat 1.2.14 as a two-file, documentation-only sweep with
      `make markdownlint` + `make nixie` as the operative gates, asserting
      `make all` is unaffected rather than re-running the whole suite per item.
      Rationale: The roadmap 1.2.14 success criterion names exactly the design
      document and `SKILL.md`; no code, test, or behaviour changes; no test reads
      either file's body. `make nixie` is included (unlike a pure prose task)
      because the design doc carries two Mermaid diagrams whose nodes are swept.
      `make all` is run once at the end to confirm no incidental breakage.
      Date/Author: 2026-06-26, planning agent.

    - Decision: The noun-vs-script rule for bare `desloppify`/`wordcount`.
      Convert a bare `` `desloppify` ``/`` `wordcount` `` to `novel desloppify`/
      `novel wordcount` ONLY where the clause names the command being *run or
      invoked* — a shell-style invocation, a Mermaid pipeline node that lists
      commands executed in the pipeline (Figure 3 node `G`), a flag-bearing form
      (`desloppify --ledger`, `desloppify --chapter`), or a table row that
      enumerates the *checker commands* (the §3.3 segregation table, line 242)
      or the §9 exit-code *proofs* (line 884). PRESERVE the bare token where the
      clause uses it as the operation/pass *noun* — "the desloppify command/pass",
      "what `desloppify` detects", "`wordcount` reports, per chapter …", "running
      after `desloppify`", "`desloppify` and `wordcount` are pure aggregations".
      Rationale: This is exactly the distinction roadmap task 1.2.17 states for
      the reference files ("Distinguish retired command invocations … from the
      noun-form `desloppify` pass, which names the desloppification operation
      rather than the retired console-script"). The design doc uses bare
      `desloppify`/`wordcount` predominantly as operation nouns, the same way it
      uses bare `check`, `compile`, `recount`. Applying the same discipline here
      keeps the prose truthful and avoids the `desloppify-checklist.md`
      corruption. The roadmap 1.2.14 criterion forbids a console-script
      *reference* surviving; an operation noun is not a console-script reference.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Preserve the `desloppify-checklist.md` filename and the ADR-005
      supersession history verbatim.
      Rationale: The filename names a reference document, not a command; the
      ADR-005 mentions are legitimate superseded history (line 274 "superseding
      ADR 005") and a references-list filename (line 18), not present-tense
      surface claims (1.2.16 precedent).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Do NOT run `make fmt`.
      Rationale: In this worktree `make fmt` re-flows ~250 unrelated Markdown
      files tree-wide and fails on pre-existing `docs/issues/*.md` line-length
      errors, which would violate the two-file scope Constraint (1.2.16
      implementation Decision Log, verified). Hand-wrap edited lines at 80
      columns instead.
      Date/Author: 2026-06-26, planning agent.

    - Decision (round 2): Convert both JSON envelope `command` fields (design
      lines 148, 358) to the spaced `"command": "novel done"`, verified against
      `names.py` `SUBCOMMAND_NAMES`/`ENVELOPE_COMMAND_NAMES`, and add a dedicated
      Constraint plus a work-item-2 step (3a) and gate (work items 3/5) for it.
      Rationale: design-review B2. The envelope `command` field is the harness's
      machine-read output contract; the multiplexer stamps the spaced form, so
      the doc must match it character-for-character. Verified live: `grep -n
      '"command":'` returns lines 148 and 358, both `"novel-done"`; `names.py`
      line 42 is `"novel done"`, line 53 derives `ENVELOPE_COMMAND_NAMES` from it.
      Date/Author: 2026-06-26, planning agent (round 2).

    - Decision (round 2): Add a preserve-noun count gate (over-sweep oracle) to
      work items 3 and 5, pinning the post-sweep bare-noun and converted-form
      counts per file, and add §2.3 and §3.1 to work item 2's explicit convert
      scope.
      Rationale: design-review B3 (over-sweep was defended only by human
      classification, invisible to the subtract-then-print surface grep) and B1
      (§2.3 lines 112/115/121/123 and §3.1 line 148 carried hyphenated
      references the section list omitted). The count baselines (DESIGN 11
      `desloppify` / 4 `wordcount` preserve-noun after subtracting 3 + 3 convert
      anchors; 5 / 5 converted; SKILL 0 / 0 bare, 3 `desloppify-checklist`) were
      derived from live worktree greps and recorded in `Surprises &
      Discoveries`. The line-924 `desloppify exits 2` anchor is a knowingly close
      call (review A3): it is classified preserve-noun (it names the operation
      that exits, not a shell invocation), and is flagged in work item 1 so the
      implementer does not silently flip it.
      Date/Author: 2026-06-26, planning agent (round 2).

    - Decision: No cuprum (or other locked-library) API is exercised by this
      task.
      Rationale: This is a documentation-only sweep of Markdown prose and Mermaid
      diagrams. No Python is added or changed, so there is no cuprum catalogue,
      allowlist, or run/output decision to pin. For completeness, the locked
      version is **cuprum 0.1.0** (`uv.lock` lines 113-114); 1.2.14 introduces no
      new cuprum usage, so there is no cuprum forking decision to resolve. The
      same holds for Cyclopts, pytest-timeout, pytest-xdist, and `uv run`: none
      is newly relied upon by this task.
      Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

Completed 2026-06-26. Both files were swept to the single `novel` multiplexer
surface across two atomic commits (design doc, then `SKILL.md`). The final-state
gates all hold: `make markdownlint`, `make nixie`, and `make all` are green; the
surface grep's survivors over both files are exactly the recorded
operation-noun and `desloppify-checklist` filename references; the count gate
shows DESIGN `11 desloppify` / `1 desloppify-checklist` / `5 novel desloppify`
and `4 wordcount` / `5 novel wordcount`, SKILL `0` bare `desloppify` / `3
desloppify-checklist` / `0` bare `wordcount`; both JSON envelope `command`
fields read `"novel done"`; the `SKILL.md` Setup install check is `novel
--version`. `coderabbit review` returned **No findings** on both commits.

Lessons: (1) `markdownlint`'s MD060 table-column-style rule is strict — the §3.3
checker table needed re-alignment after the longer `novel <verb>` cells, so
table edits must re-pad pipes (MD013 line-length is disabled in this repo, so
80-column prose wrapping is courtesy, not gate-enforced). (2) The hyphenated
command prefixes (`novel-state`/`novel-done`/`novel-compile`) never appear
fused to a hyphenated suffix in `SKILL.md`, so a prefix-only token replacement
was safe and left the subcommand hyphens (`set-chapters`, `set-cursor`) intact.
(3) The two-file scope held with no third-file edit required.

The plan succeeded as specified. The plan succeeds when: no
`novel-state`/`novel-done`/`novel-compile` console-script reference (including
the §2.3 validator/returns/compile prose and both §3.1/§4.2 JSON envelope
`command` fields) and no hyphenated-or-invoked `desloppify`/`wordcount`
console-script reference survives in either file; both JSON envelope `command`
fields read `"command": "novel done"`, character-for-character matching
`names.py` `SUBCOMMAND_NAMES`; the `desloppify-checklist.md` filename and the
operation-noun mentions are intact at their pinned counts (the preserve-noun
count gate shows DESIGN `11 desloppify` / `1 desloppify-checklist` /
`5 novel desloppify` and `4 wordcount` / `5 novel wordcount`, and SKILL `0` bare
`desloppify` / `3 desloppify-checklist` / `0` bare `wordcount`), so neither an
over-swept nor an under-swept noun escapes; the SKILL.md Setup section describes
the single `novel` multiplexer and its install check is `novel --version`; and
`make markdownlint`, `make nixie`, and `make all` are green.

## Context and orientation

A novice should read these before touching anything:

- [docs/roadmap.md](../roadmap.md), task 1.2.14 (the step-task paragraph, the
  update instruction, and its success criterion) and the sibling tasks 1.2.16
  (completed — the users'/developers' guides, the precedent for this sweep's
  mechanics) and 1.2.17 (the reference-file sweep, which states the noun-vs-script
  distinction this plan adopts). Task 1.2.14's parent is step 1.2.
- [docs/adr-007-command-surface-novel-multiplexer.md](../adr-007-command-surface-novel-multiplexer.md)
  — fixes the surface as a single `novel` multiplexer (supersedes ADR 005). Its
  "Decision outcome" section lists the exact subcommand structure (lines 90-96);
  its "Migration plan" section (lines 113-123) explicitly names "sweeps the
  design prose and diagrams and `SKILL.md` (including its Setup section and
  every bare-command reference) from `novel-x` to `novel x`" as part of the
  migration — this task executes that clause.
- [docs/novel-ralph-harness-design.md](../novel-ralph-harness-design.md) — the
  file being swept. §4 ("The deterministic commands") and §4.1-§4.5 are the
  authoritative description of each operation's **behaviour**. **Caveat
  (verified):** §4's *body* command literals are still hyphenated (the spaced
  forms are confined to the §4 intro and the subsection headings). So §4 is
  **not** a spaced-surface reference: any command literal quoted from it must be
  re-spaced. The surface vocabulary source is `names.py` `SUBCOMMAND_NAMES` plus
  ADR 007, not §4's body.
- The previously-completed
  [docs/execplans/roadmap-1-2-16.md](roadmap-1-2-16.md) — the sibling sweep of
  the two guides. Its mechanics (per-file gating, bare-alternation surface gate
  with token-level preserve subtraction, no `make fmt`, hand-wrap at 80 columns)
  are the template this plan follows. 1.2.14 differs in two ways: (a) it sweeps
  two Mermaid diagrams, so `make nixie` is load-bearing; (b) its only preserve
  cases are the `desloppify-checklist` filename and the operation-noun mentions,
  not Python fixtures.
- [AGENTS.md](../../AGENTS.md) — quality gates ("Markdown files (`.md` only)":
  `make markdownlint` line 169, `make nixie` line 172) and the Markdown guidance
  (80-column prose line 173, 120-column code line 174, dash bullets, en-GB Oxford
  spelling).
- [docs/documentation-style-guide.md](../documentation-style-guide.md) — house
  style the documents already follow.

The single, authoritative source of the surface vocabulary is
[`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
together with ADR 007: `SUBCOMMAND_NAMES` is exactly
`("novel state", "novel done", "novel compile", "novel desloppify", "novel wordcount")`,
and `project_scripts_table()` returns exactly `{"novel": …}`. **Every** command
form written into either file must be confirmed against this file (and ADR 007's
subcommand structure), never against design §4's body prose.

Terms used in this plan:

- **Command-surface reference**: a token naming the command a user or the
  harness invokes on the shell — `novel-state`, `novel-done`, `novel-compile`,
  and their subcommand/flag forms (`novel-state check`, `novel-compile --check`),
  plus a bare `desloppify`/`wordcount` used as an *invocation* (a pipeline node,
  a flag-bearing form, a checker-command table row). These are converted to the
  spaced `novel <verb>` form.
- **Operation noun**: a bare `` `desloppify` `` / `` `wordcount` `` (or "the
  desloppify command/pass") naming the *operation* in running prose rather than
  an invocation. These are preserved (see the Decision Log rule).
- **Preserve filename**: `desloppify-checklist.md`, a reference-document
  filename. Preserved verbatim.

Library-API note (verification, not a change): this task adds no Python and
exercises no external-library API. The locked external libraries the wider
codebase leans on (cuprum 0.1.0, Cyclopts, pytest-timeout, pytest-xdist,
`uv run`) are not newly relied upon here; there is no library-behaviour fork to
resolve. See the Decision Log entry "No cuprum … API is exercised".

## Plan of work

The sweep proceeds file by file, each behind its own Markdown gate, so a
stopping point never leaves a half-converted document. Stage A (work items 0-1)
understands and classifies without editing; Stage B (items 2-3) sweeps and gates
the design document (prose, tables, and the two Mermaid diagrams); Stage C
(items 4-5) sweeps and gates `SKILL.md` (including the Setup section and the
install check) and proves the whole-file end-state.

### Work item 0 — Orientation and reference grep (no edits)

Implements: roadmap 1.2.14 scope; ADR 007 surface vocabulary and Migration plan.

Read, in order: roadmap 1.2.14 (and the 1.2.16/1.2.17 siblings for the
noun-vs-script distinction), ADR 007 (Decision outcome + Migration plan), the
completed `roadmap-1-2-16.md` execplan (for the gate mechanics), design §3-§5
and §9-§10, AGENTS.md Markdown sections, and both target files end to end. No
file is edited in this item; it exists so the implementer holds the target
vocabulary, the noun-vs-script rule, and the truthful end-state in mind before
classifying hits.

Docs to read: `docs/roadmap.md` (1.2.14, 1.2.16, 1.2.17),
`docs/adr-007-command-surface-novel-multiplexer.md`,
`docs/execplans/roadmap-1-2-16.md`, `docs/novel-ralph-harness-design.md`
§3-§5/§9-§10, `AGENTS.md`, `docs/documentation-style-guide.md`.

Skills to load: `execplans` (this plan's format), `en-gb-oxendict` (spelling
convention for every edited sentence). Use `leta` (`leta show`, `leta files`)
and `grepai search` for navigation rather than ad-hoc reads.

Tests: none (no behaviour change). Validation: confirm by reading that the
spaced forms in design §4 headings match `SUBCOMMAND_NAMES` in
`novel_ralph_skill/commands/names.py`.

### Work item 1 — Build and record the hit classification for both files

Implements: the Constraints' preserve boundary; the noun-vs-script Decision Log
rule; Risks 1 and 2 mitigation.

Run the enumerating greps below and record, in the `Surprises & Discoveries`
section of this plan, the per-file list of hits split into three buckets:
**convert** (command-surface references, including invoked
`desloppify`/`wordcount`), **preserve-noun** (operation-noun
`desloppify`/`wordcount`), and **preserve-filename** (`desloppify-checklist.md`).
This classification is the contract the two sweep items execute against, so a
later edit cannot silently corrupt the checklist filename or over-sweep an
operation noun.

Commands (run from the worktree root):

    DESIGN=docs/novel-ralph-harness-design.md
    SKILL=skill/novel-ralph/SKILL.md
    # All hyphenated + bare-generic surface literals, per file:
    LEGACY='novel-state|novel-done|novel-compile|desloppify|wordcount'
    grep -nE "$LEGACY" "$DESIGN"
    grep -nE "$LEGACY" "$SKILL"
    # The preserve-filename term (must be classified out of the desloppify hits):
    grep -nE 'desloppify-checklist' "$DESIGN" "$SKILL"
    # Stale present-tense "five console-scripts" framing (SKILL.md line 28):
    grep -niE 'five[ -]?(separate )?console-?scripts?' "$DESIGN" "$SKILL"
    # ADR-005 references (classify as preserved superseded history):
    grep -niE 'adr-005|ADR 005' "$DESIGN" "$SKILL"
    # The two JSON envelope command fields (contract-sensitive convert, B2):
    grep -n '"command":' "$DESIGN"   # expect lines 148 (§3.1) and 358 (§4.2)
    # Preserve-noun count baseline (over-sweep oracle source, B3):
    grep -oE '(novel )?desloppify(-checklist)?' "$DESIGN" | sort | uniq -c
    grep -oE '(novel )?wordcount' "$DESIGN"               | sort | uniq -c
    grep -oE '(novel )?desloppify(-checklist)?' "$SKILL"  | sort | uniq -c
    grep -oE '(novel )?wordcount' "$SKILL"                | sort | uniq -c

For every bare `` `desloppify` ``/`` `wordcount` `` hit, classify it by the
Decision Log noun-vs-script rule and record the disposition. Confirmed anchors
from the planning pass (re-verify line numbers on disk, the file may shift):

- **Convert** (invocation): the §3.3 segregation table row (design line 242,
  which enumerates the checker commands `novel-done`, `novel-state check`,
  `wordcount`, `desloppify` (detect), `novel-compile --check`); the §9
  exit-code proofs (design line 884, `check` / `desloppify` / `novel-done`
  proofs); the device-ledger flag prose where it bears a flag; and the **Figure
  3 node** `G[novel-state recount / novel-done / wordcount]` (design line 805).
- **Preserve-noun** (operation): design lines 218 ("desloppify finds
  violations"), 414/423 ("`desloppify` runs …", "`desloppify` detects"), 432
  ("`wordcount` reports, per chapter …"), 668 ("The desloppify command reads
  …"), 711 ("`desloppify` enforces"), 776 ("running after `desloppify`"), 800
  (Figure 3 node `B[desloppify: detect]` — the operation label, not an
  invocation list), 812 (caption "Detection (`desloppify`, `wordcount`)"),
  843-844 ("`wordcount` and `desloppify` are pure aggregations"), 870/874
  ("`desloppify`, whose rule-pack loader …", "`wordcount`"), 924 ("`desloppify`
  exits 2" — **knowingly close call** (review A3): it reads as a runtime-contract
  statement but names the operation that exits, not a shell invocation, so it is
  preserve-noun; do not silently flip it, and if the implementer judges it an
  invocation, stop and record per Tolerances before converting).
- **Preserve-filename**: design line 938 and SKILL.md (3 occurrences) —
  `desloppify-checklist.md`.

Note the Figure 1 diagram nodes (design lines 56-60: `ST[novel-state]`,
`DN[novel-done]`, `CO[novel-compile]`, `DS[desloppify]`, `WC[wordcount]`) name
the deterministic *commands* as the spine; these are command identities and
**convert** to the spaced labels `ST[novel state]`, `DN[novel done]`,
`CO[novel compile]`, `DS[novel desloppify]`, `WC[novel wordcount]`.

If any bare hit resists classification, record it in the `Decision Log` and
escalate per Tolerances rather than guessing.

Docs to read: this plan's Constraints, Risks, and Decision Log.

Skills to load: `leta`, `grepai` for navigation.

Tests: none. Validation: the classification is recorded in this plan and every
hit from the greps above appears in exactly one bucket.

### Work item 2 — Sweep `docs/novel-ralph-harness-design.md` to the `novel` surface

Implements: roadmap 1.2.14 success criterion (design half); ADR 007 Decision
outcome and Migration plan; design §2.3 Verification scope, §3.1 Output modes
(including the JSON envelope `command` field), §3 tables, §4.1-§4.5 (behaviour
wording, re-spaced), §4.2 envelope example, §5, §9, §10.

Independently committable. Edit only `docs/novel-ralph-harness-design.md`. Four
kinds of change, in order:

1. **Figure 1 (lines 53-73).** Re-space the five deterministic-spine node labels:
   `ST[novel-state]` → `ST[novel state]`, `DN[novel-done]` → `DN[novel done]`,
   `CO[novel-compile]` → `CO[novel compile]`, `DS[desloppify]` →
   `DS[novel desloppify]`, `WC[wordcount]` → `WC[novel wordcount]`. Edit only the
   label text inside `[]`; leave node ids (`ST`, `DN`, …) and the arrows
   untouched. The caption (Figure 1) names no command literal and stays.

2. **Figure 3 (lines 798-810) and its caption (812-814).** Re-space the
   invocation node `G[novel-state recount / novel-done / wordcount]` →
   `G[novel state recount / novel done / novel wordcount]`. The node
   `B[desloppify: detect]` and the caption "Detection (`desloppify`,
   `wordcount`)" are operation nouns (preserve-noun bucket) — leave them.

3. **§2.3 Verification scope, §3 tables and prose, §3.1 Output modes, §4 body,
   §5, §9, §10 (the convert bucket from work item 1).** Convert every
   command-surface literal to its spaced form: `novel-state` → `novel state`
   (and its verb forms `novel-state check` → `novel state check`, `novel-state
   recount` → `novel state recount`, etc.), `novel-done` → `novel done`,
   `novel-compile` → `novel compile`, `novel-compile --check` → `novel compile
   --check`. §2.3 (lines 112, 115, 121, 123) and §3.1 are NOT optional: line 112
   (`novel-state` validator), line 115 (`novel-done` returns), line 121
   (`novel-compile --check`), and line 123 (`novel-done` compile clause) are all
   convert targets. In the §3.3 segregation table (line 242) and the §9
   exit-code proofs (line 884), the invoked `desloppify`/`wordcount` become
   `novel desloppify`/`novel wordcount`. Reconcile any surrounding prose so each
   sentence reads truthfully (a clause that introduced a separate script now
   names a subcommand of `novel`). Take the per-operation *behaviour* wording
   from §4.1-§4.5 where needed, re-spacing any command literal it quotes (the §4
   caveat).

   **3a. The two JSON envelope `command` fields (contract-sensitive).** §3.1's
   Output-modes example at design line 148 and §4.2's example at line 358 both
   carry `"command": "novel-done"`. Convert both to `"command": "novel done"`,
   verified character-for-character against `names.py` `SUBCOMMAND_NAMES`
   (`"novel done"`, line 42) — this is the spaced form the multiplexer actually
   stamps via `ENVELOPE_COMMAND_NAMES` (line 53). Do not apply a reflexive
   `novel-done` → `novel done` text edit here without that confirmation: the
   envelope `command` string is part of the harness's machine-read output
   contract (Constraints, "Convert the JSON envelope `command` field exactly"),
   so it is the one place exactness is contractually load-bearing rather than
   cosmetic. After the edit, `grep -n '"command":' "$DESIGN"` must return both
   lines as `"command": "novel done"`.

4. **Preserve** the operation-noun `desloppify`/`wordcount` mentions
   (preserve-noun bucket), the `desloppify-checklist.md` filename (line 938), the
   ADR-005 supersession history (lines 18, 274), and the single-surface
   `console-script` distribution prose (lines 103, 268, 279, 881, 890) verbatim.

Do not touch any section that carries no command-surface reference (e.g. §1's
problem statement beyond its command mentions, §6's rule-pack schema beyond its
operation-noun mentions, §11 references beyond the preserved ADR filenames).

Docs to read: design §4.1-§4.5 (per-operation *behaviour* wording only; re-space
any hyphenated command literal it quotes), ADR 007 (subcommand structure),
`names.py` `SUBCOMMAND_NAMES` (the authoritative spaced forms), AGENTS.md
Markdown guidance.

Skills to load: `en-gb-oxendict` (every reworded sentence), `leta`/`grepai` for
navigation.

Tests: none — this is documentation. Per the AGENTS.md testing rules, a
documentation-only change that alters no externally observable behaviour adds no
unit, behavioural, property, snapshot, or e2e test; the Markdown gates
(`make markdownlint`, `make nixie`) are the verification. (Verified: no test
reads the design body — see `Surprises & Discoveries`.)

Validation for this item is performed by work item 3.

### Work item 3 — Gate work item 2 (markdownlint + nixie + surface grep)

Implements: AGENTS.md "Markdown files (`.md` only)" gates; roadmap 1.2.14
success criterion (design-half proof).

Run, from the worktree root:

    DESIGN=docs/novel-ralph-harness-design.md
    # Hand-wrap edited lines at 80 columns; do NOT run `make fmt` (Decision Log).
    make markdownlint  # expect: clean exit, no findings
    make nixie         # expect: clean — both Mermaid diagrams still parse with
                       # the spaced node labels
    # Surface gate: no un-converted command-surface reference survives. Subtract
    # the preserve-filename and the correctly-converted `novel <verb>` forms at
    # TOKEN level (the converted forms contain desloppify/wordcount as
    # substrings, so the leftmost-longest `novel <verb>` is extracted first).
    SURFACE='novel-state|novel-done|novel-compile|desloppify|wordcount'
    CONVERTED='novel (state|done|compile|desloppify|wordcount)'
    PRESERVE='desloppify-checklist'
    grep -onE "$PRESERVE|$CONVERTED|$SURFACE" "$DESIGN" \
      | grep -vE ":($PRESERVE)\$" \
      | grep -vE ':(novel (state|done|compile|desloppify|wordcount))$'

The surface grep prints `line:token` for every alternation hit, then drops any
token that is the preserve filename or a correctly-converted `novel <verb>`
form. What survives is the set of un-converted command-surface references **plus
the operation-noun `desloppify`/`wordcount` mentions** (which legitimately
remain). The implementer reviews the survivors against the work-item-1
preserve-noun bucket: every survivor must be a bucket entry. If a hit appears
that is NOT a recorded operation noun, it is an un-converted reference — fix it
and re-run.

This surface grep catches UNDER-sweep (a hyphenated literal that escaped
conversion). It cannot by itself catch OVER-sweep, because the
`novel (desloppify|wordcount)` forms are subtracted before survivors print, so a
noun wrongly promoted to `novel desloppify` is invisible to it (B3, Risk 2).
Add the **preserve-noun count gate**, which pins the exact post-sweep
operation-noun and converted-form counts derived in `Surprises & Discoveries`:

    # Over-sweep / under-sweep count gate (leftmost-longest extraction):
    # Expected after the design sweep:
    #   11 desloppify   1 desloppify-checklist   5 novel desloppify
    #    4 wordcount                              5 novel wordcount
    grep -oE '(novel )?desloppify(-checklist)?' "$DESIGN" | sort | uniq -c
    grep -oE '(novel )?wordcount' "$DESIGN"               | sort | uniq -c
    # The two JSON envelope command fields must be the spaced form:
    grep -n '"command":' "$DESIGN"   # expect both: "command": "novel done"

If bare `desloppify` is below 11 (or `novel desloppify` above 5), an operation
noun was over-swept — revert that specific hit to the bare noun. If bare
`desloppify` is above 11 (or `novel desloppify` below 5), a checker-command
invocation was under-swept — convert it. The `wordcount` counts work the same
way against 4 / 5. These exact numbers are the over-sweep oracle the surface
grep lacks.

Acceptance: `make markdownlint` and `make nixie` exit 0; the surface grep's
survivors are exactly the recorded operation-noun mentions; the preserve-noun
count gate shows exactly `11 desloppify` / `1 desloppify-checklist` /
`5 novel desloppify` and `4 wordcount` / `5 novel wordcount`; both
`"command":` envelope fields read `"command": "novel done"`; the
`desloppify-checklist.md` filename count is unchanged (1). Commit the design-doc
sweep as one atomic commit with an imperative subject (for example, "Sweep
harness design to the novel multiplexer surface"). If a gate fails, fix within
tolerance (re-wrap at 80 columns; repair the Mermaid node) and re-run before
committing.

### Work item 4 — Sweep `skill/novel-ralph/SKILL.md` to the `novel` surface

Implements: roadmap 1.2.14 success criterion (`SKILL.md` half, including "the
Setup section and every bare `novel-x` reference" and "Replace the
`novel-state --version` install check"); ADR 007 Migration plan.

Independently committable. Edit only `skill/novel-ralph/SKILL.md`. Three kinds
of change, in order:

1. **The Setup section (lines 26-45).** Rewrite the opening framing: the harness
   is no longer "five console-scripts — `novel-state`, `novel-done`,
   `novel-compile`, `desloppify`, and `wordcount`". It is a single `novel`
   multiplexer (one `[project.scripts]` entry; `project_scripts_table()` returns
   `{"novel": …}`) with a `state` subgroup and four leaf verbs. Take the
   vocabulary from `names.py` `SUBCOMMAND_NAMES` and ADR 007. Replace the install
   check `novel-state --version` (line 37) with **`novel --version`** — verified
   to exist and exit 0 (`novel.py` docstring lines 18-20;
   `tests/test_multiplexer_dispatch.py` lines 81-82). Re-space the "Invoke the
   commands by **bare name**" guidance (line 40, `novel-state init …`,
   `novel-done`, `novel-compile`) to `novel state init …`, `novel done`,
   `novel compile`, and reconcile the "bare name" phrasing (the surface is now
   invoked as `novel <sub>`, not as five bare scripts).

2. **Body command references throughout (the convert bucket from work item 1).**
   Convert every command-surface literal: `novel-state` → `novel state` (and its
   verb forms), `novel-done` → `novel done`, `novel-compile` → `novel compile`.
   In `SKILL.md` the only bare `desloppify`/`wordcount` (1 each, both on line 29)
   live inside the "five console-scripts" framing sentence rewritten in step 1;
   they are NOT operation nouns. The other `desloppify` hits (lines 87, 105, 372)
   are all the `references/desloppify-checklist.md` filename and are preserved.
   So the post-sweep SKILL baseline is **0** bare `desloppify`, **0** bare
   `wordcount`, **3** `desloppify-checklist` — pinned by the work-item-5
   preserve-noun count gate.

3. **Preserve** the `desloppify-checklist.md` filename (3 occurrences) verbatim.

Reconcile the harness-contract clause at line 63 ("the `novel-done` command exits
0") and the other body mentions so each reads truthfully against the single
surface.

Docs to read: ADR 007 (Migration plan, for the Setup-section truthful framing),
`names.py` `SUBCOMMAND_NAMES`, `novel_ralph_skill/commands/novel.py` (to confirm
`novel --version` is the correct install check), AGENTS.md Markdown guidance.

Skills to load: `en-gb-oxendict` (each reworded sentence), `leta` (`leta show`
on `SUBCOMMAND_NAMES`, `project_scripts_table` to confirm they exist before
describing them), `grepai` for navigation.

Tests: none — documentation-only (same rationale as work item 2; no test reads
the `SKILL.md` body). The Markdown gates are the verification.

Validation for this item is performed by work item 5.

### Work item 5 — Gate work item 4 and prove the whole-file end-state

Implements: AGENTS.md Markdown gates; roadmap 1.2.14 success criterion (final
proof).

Run, from the worktree root:

    SKILL=skill/novel-ralph/SKILL.md
    DESIGN=docs/novel-ralph-harness-design.md
    # Do NOT run `make fmt` (Decision Log): hand-wrap edited lines at 80 columns.
    make markdownlint  # expect: clean
    make nixie         # expect: clean (SKILL.md has no Mermaid; design re-checked)
    # Surface gate over BOTH files (same token-subtraction shape as work item 3):
    SURFACE='novel-state|novel-done|novel-compile|desloppify|wordcount'
    CONVERTED='novel (state|done|compile|desloppify|wordcount)'
    PRESERVE='desloppify-checklist'
    grep -onE "$PRESERVE|$CONVERTED|$SURFACE" "$SKILL" "$DESIGN" \
      | grep -vE ':($PRESERVE)$' \
      | grep -vE ':(novel (state|done|compile|desloppify|wordcount))$'
    # Preserve-noun count gate (over-sweep oracle, per file). Expected:
    #   DESIGN: 11 desloppify / 1 desloppify-checklist / 5 novel desloppify
    #           4 wordcount                              / 5 novel wordcount
    #   SKILL:   0 bare desloppify / 3 desloppify-checklist / 0 novel desloppify
    #            0 bare wordcount                            / 0 novel wordcount
    grep -oE '(novel )?desloppify(-checklist)?' "$DESIGN" | sort | uniq -c
    grep -oE '(novel )?wordcount' "$DESIGN"               | sort | uniq -c
    grep -oE '(novel )?desloppify(-checklist)?' "$SKILL"  | sort | uniq -c
    grep -oE '(novel )?wordcount' "$SKILL"                | sort | uniq -c
    # The two JSON envelope command fields in the design must be spaced:
    grep -n '"command":' "$DESIGN"   # expect both: "command": "novel done"
    # Stale present-tense "five console-scripts" framing must be gone:
    grep -niE 'five[ -]?(separate )?console-?scripts?' "$SKILL" "$DESIGN"
    # The install check must name a command that exists:
    grep -n 'novel-state --version' "$SKILL"   # expect: empty
    grep -n 'novel --version' "$SKILL"         # expect: the Setup install check
    # Preserve-filename intact at original counts:
    grep -c 'desloppify-checklist' "$SKILL"    # expect: 3
    grep -c 'desloppify-checklist' "$DESIGN"   # expect: 1
    make all           # expect: green; confirms no code/test breakage

Acceptance: `make markdownlint` and `make nixie` exit 0; the surface grep's
survivors over both files are exactly the recorded operation-noun mentions (no
un-converted hyphenated reference, no invoked bare `desloppify`/`wordcount`); the
preserve-noun count gate shows DESIGN `11 desloppify` / `1 desloppify-checklist`
/ `5 novel desloppify` and `4 wordcount` / `5 novel wordcount`, and SKILL `0`
bare `desloppify` / `3 desloppify-checklist` / `0` bare `wordcount` (so no SKILL
operation noun was over-swept); both design `"command":` envelope fields read
`"command": "novel done"`; the "five console-scripts" framing grep is empty;
`novel-state --version` is gone and `novel --version` is the Setup install check;
the `desloppify-checklist.md` counts are 3 (SKILL) and 1 (design); `make all` is
green. Commit the `SKILL.md`
sweep as one atomic commit with an imperative subject (for example, "Sweep
novel-ralph SKILL.md to the novel multiplexer surface"). If a gate fails, fix
within tolerance and re-run before committing.

## Idempotence and recovery

Every work item is a self-contained Markdown edit gated by `make markdownlint`,
`make nixie`, and the surface grep; re-running a gate is safe. If a sweep is
interrupted mid-file, re-run the work-item-1 greps to see which literals remain
and resume. No step is destructive; `git checkout -- <file>` restores either
file to HEAD. The two sweeps are independent commits, so the design-doc sweep can
land and be verified before the `SKILL.md` sweep begins.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` green (no test reads either file's body; the suite must be
  unaffected). No new test is added — a documentation-only change adds none per
  AGENTS.md testing rules.
- Lint/format: `make markdownlint` clean on both files.
- Mermaid: `make nixie` clean — both design-doc diagrams parse with spaced node
  labels.
- Surface: the work-item-5 surface grep's survivors are exactly the recorded
  operation-noun mentions; no console-script reference survives (under-sweep
  oracle).
- Preserve-noun counts (over-sweep oracle): DESIGN `11 desloppify` /
  `1 desloppify-checklist` / `5 novel desloppify` and `4 wordcount` /
  `5 novel wordcount`; SKILL `0` bare `desloppify` / `3 desloppify-checklist` /
  `0` bare `wordcount`. No noun is promoted to a `novel <verb>` invocation.
- Envelope contract: both design JSON envelope `command` fields read
  `"command": "novel done"`, matching `names.py` `SUBCOMMAND_NAMES`.
- Install check: `SKILL.md` Setup runs `novel --version`, a command that exists.

Quality method (how we check): run the work-item-3 and work-item-5 command
blocks verbatim from the worktree root and compare against the stated expected
outputs.

## Interfaces and dependencies

None. This task adds no code, no module, no public interface, and no dependency.
It edits two Markdown files. The surface vocabulary it writes is governed by the
existing `novel_ralph_skill/commands/names.py` `SUBCOMMAND_NAMES` and ADR 007;
this plan changes neither.

## Revision note

Round 2 (2026-06-26, planning agent) resolves the three round-1 Logisphere
blocking points and the actionable advisories:

- **B1 (incomplete convert scope).** Added §2.3 Verification scope (design lines
  112, 115, 121, 123) and §3.1 Output modes (line 148) to the Purpose, to work
  item 2 step 3 (explicitly named, "NOT optional"), and to work item 2's
  "Implements" line. Verified live: those four §2.3 lines and the §3.1 envelope
  carry the hyphenated forms.
- **B2 (envelope `command` field).** Added a dedicated Constraint, a work-item-2
  step 3a, and a gate line (work items 1/3/5) converting both `"command":
  "novel-done"` envelopes (design lines 148, 358) to `"command": "novel done"`,
  tied character-for-character to `names.py` `SUBCOMMAND_NAMES` (line 42) /
  `ENVELOPE_COMMAND_NAMES` (line 53). Verified live: `grep -n '"command":'`
  returns lines 148 and 358.
- **B3 (over-sweep blind spot).** Added a preserve-noun count gate (over-sweep
  oracle) to work items 3 and 5, pinning the post-sweep bare-noun and
  converted-form counts per file (DESIGN 11/4 bare, 5/5 converted,
  1 `desloppify-checklist`; SKILL 0/0 bare, 3 `desloppify-checklist`). Baselines
  derived from live worktree greps and recorded in `Surprises & Discoveries`.
- Advisories: corrected the 44-vs-65 grep parenthetical (A1), the SKILL hit-line
  count to 26 (A2), and flagged line 924 (`desloppify exits 2`) as a knowingly
  close preserve-noun call in work item 1 (A3).

These changes affect no remaining work: the plan is still a two-file,
documentation-only sweep with the same two atomic commits; the gates are
strictly stronger (they now catch over-sweep and pin the envelope contract).

Implementation (2026-06-26, implementing agent). Executed the plan as written.
The design-doc sweep (Figure 1 nodes, §2.3, §3.1/§4.2 envelopes, §3 tables,
§3.4, §4 body, §5, §8 Figure 3 node, §9, §10) and the `SKILL.md` sweep (Setup
rewrite, install check, body literals) landed as two atomic commits; the
execplan checkboxes, `Surprises & Discoveries` evidence, and the `Outcomes`
section were updated alongside. All deterministic gates (`make markdownlint`,
`make nixie`, `make all`) and `coderabbit review` (No findings) pass. The only
in-flight correction was re-aligning the §3.3 checker table for MD060 after the
longer `novel <verb>` cells — recorded in `Outcomes`. No tolerance was breached;
no third file was touched.
