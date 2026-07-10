# Sweep the users' and developers' guides to the `novel` multiplexer surface

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 1.2.15 retired the five legacy console-scripts (`novel-state`,
`novel-done`, `novel-compile`, `desloppify`, `wordcount`) and deleted the
`stub.py` factory and the legacy name-registry symbols, so the package now
ships **exactly one** `[project.scripts]` entry — `novel` — dispatching into a
`state` subgroup and four leaf verbs (`novel done`, `novel compile`,
`novel desloppify`, `novel wordcount`). This is verified in the worktree:
`pyproject.toml` lists only `novel = "novel_ralph_skill.commands.novel:main"`,
there is no `novel_ralph_skill/commands/stub.py`, and
`novel_ralph_skill/commands/names.py` describes only the single `novel`
multiplexer (its module docstring states "task 1.2.15 retired the legacy
surface").

Two repository documents were left behind by that retirement, because task
1.2.14's wording and success criterion covered only the design document and
`SKILL.md`:

1. `docs/users-guide.md` still presents the legacy five console-scripts as the
   user-facing surface. Its "Installed Commands" section says installing the
   wheel "puts five console-scripts onto `PATH`" and lists `novel-state`,
   `novel-done`, `novel-compile`, `desloppify`, and `wordcount`; the body then
   refers to those bare names throughout (for example `novel-state check`,
   `novel-compile --check`, `desloppify --ledger`). There is zero mention of the
   `novel` multiplexer.
2. `docs/developers-guide.md` carries a "The five commands" subsection that
   asserts in the present tense "The v1 spine is five separate console-scripts
   … not a single multiplexer", cites the **superseded** ADR 005, and describes
   three commands as "stubs" defined by the now-deleted `stub.py`. Its "The
   `novel` multiplexer" subsection then describes that surface being stood up
   "additively" with the legacy five "stay[ing] registered and working", and
   names "their removal and the prose sweep … roadmap tasks 1.2.13 and 1.2.14"
   as still-future work. All of that additive-transition framing is now false.

After this change a reader of either guide sees the single `novel <sub>`
surface the package actually ships, with no surviving reference to the retired
separate scripts and no prose that treats them as present. The work is a
**documentation-only** sweep: it edits two Markdown files and touches no
Python, no tests, and no command behaviour, so `make all` stays green by
construction (verified: no test asserts on the *content* of either guide — see
`Surprises & Discoveries`). Success is observable by grep (no legacy literal
and no additive/present-tense legacy prose survives) and by the Markdown gates
(`make markdownlint` and `make nixie` pass on the edited files).

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- Edit only `docs/users-guide.md` and `docs/developers-guide.md`. Do not modify
  any other file: not the roadmap, not the design document, not the ADRs, not
  `SKILL.md`, not any code or test. The roadmap success criterion names exactly
  these two guides.
- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-16`. Never
  read-modify-write any file in the root/control worktree.
- Do **not** rename Python code symbols that merely *contain* a legacy-form
  substring. The fixture `installed_novel_state`, the module path
  `novel_ralph_skill/commands/_novel_done.py`, the module `novel_state.py`, the
  fixture `installed_desloppify`, and the helper
  `_build_and_install_novel_state` are real (or, for the last, historically
  named) code identifiers, not command-surface references. They are governed by
  the codebase, not by this doc sweep; leaving them as written keeps the prose
  truthful about the code. Convert only references that name the *command a
  user or the harness types*.
- Do not edit `tests/features/per_chapter_loop.feature` step text or the
  `tests/test_contract_app_centralisation.py` /
  `tests/test_pyproject_scripts.py` prose. Those stale literals are owned by
  sibling roadmap task 1.2.15.1 (a separate addendum pass), not by 1.2.16,
  whose scope is the two guides.
- The surface vocabulary is fixed by
  [ADR 007](../adr-007-command-surface-novel-multiplexer.md). The subcommands
  are
  `novel state init | set-cursor | advance-phase | recount | check | reconcile`,
  plus `set-chapters`, `set-gate`, `complete-final-pass`, `set-fangirl`,
  `set-critic-pass` under `novel state`; `novel done`;
  `novel compile [--check]`;
  `novel desloppify [--pack … | --ledger …] [--chapter …]`; `novel wordcount`.
  Use exactly these spaced forms; do not invent `novel-desloppify`-style
  hyphenated namespacing (Option A, which ADR 007 rejected).
- All prose must be en-GB Oxford spelling (`-ize`/`-yse`/`-our`), matching the
  surrounding guides.

## Tolerances (exception triggers)

- Scope: this plan edits exactly two files. If a truthfulness fix appears to
  require editing a third file, stop and escalate (it likely belongs to a
  sibling task).
- Ambiguity: if a sentence cannot be made truthful by a mechanical literal swap
  *and* a reconciliation of transition language — for example if it asserts a
  behaviour that the spaced surface does not actually have — stop and record
  the conflict in the `Decision Log` before guessing.
- Gate iterations: if `make markdownlint` still fails after 3 fix attempts on a
  single work item, stop and escalate.
- Code-symbol boundary: if you find yourself about to change a token that is
  also
  an importable Python name (a fixture, module, or function that exists in
  `novel_ralph_skill/` or `tests/`), stop and re-confirm it is a
  command-surface reference, not a code identifier, before editing.

## Risks

    - Risk: Over-eager substitution rewrites a code identifier (e.g.
      `installed_novel_state`, `_novel_done.py`) that merely contains a
      legacy substring, making the prose lie about the code.
      Severity: medium
      Likelihood: medium
      Mitigation: Never run a blind `sed` over the whole file. Work from the
      enumerated grep hit list, classifying each hit as command-surface
      reference (convert) or code identifier (leave). Work item 1 builds and
      records that classification before any edit.

    - Risk: A line carries a present-tense / additive legacy framing that
      survives a literal-only swap. The framing may carry NO hyphenated
      command literal AND no curated tripwire phrase — for example a section
      heading ("The five commands"), a present-tense count claim ("these five
      names are wired as `[project.scripts]` console-scripts"), a
      success-criterion-forbidden verbatim phrase ("exit codes the legacy
      scripts produce"), or a contrastive count ("five-script command surface").
      A curated denylist that enumerates known phrases inherently lags the prose
      and lets such lines pass the gate — this is the failure mode the round-1
      and round-2 reviews raised (B2, then BR2-1: a one-phrase patch fixed the
      named instance, not the class).
      Severity: high
      Likelihood: high
      Mitigation: The stale-prose gate is no longer a curated phrase denylist.
      It is a **two-pattern class gate** (work item 5) that fires on the
      STRUCTURE of legacy framing, not on enumerated wordings:
      (a) the digit-word "five" adjacent to a surface noun —
      `five[ -]?(separate )?(console-?script|command|name|script)` — which
      catches 256, 273, 275, 310, 322, 337, 489, 492, 1354 and the two
      users'-guide lines (78, 104) in one shot; and (b) the "legacy" framing of
      the retired scripts —
      `legacy[ -](five|scripts?|entry[ -]points?)|the legacy scripts produce|legacy-(versus|vs)-multiplexer`
      — which catches 345, 356, 358, 360, 368. The two patterns together are
      verified (work item 1 records the live transcript) to catch every line
      BR2-1 enumerated, including the three the round-2 plan left to "illustrative"
      ranges (273, 345, 1354). The residual additive/stub phrases that carry
      neither "five" nor "legacy" ("stands up that multiplexer additively",
      "stay registered and working", "still **stubs**", "stub.py") are kept as a
      third belt-and-braces literal term. Work items 2 and 4 reconcile *meaning*,
      not just literals; the class gate is what proves the reconcile was
      complete. The "five" gate can fire on a legitimate "five operations"
      sentence — that is the intended forcing function: phrase any surviving
      count without the legacy-surface noun (say "the five state operations" or
      drop the count), so the gate cannot be satisfied by a literal-only swap.

    - Risk: `markdownlint` line-length (80-column prose) regressions after
      rewriting sentences, since spaced command names are longer than hyphenated
      ones (e.g. `novel-state check` → `novel state check` is the same length,
      but inserted clauses can push lines over).
      Severity: low
      Likelihood: medium
      Mitigation: Run `make markdownlint` per work item and hand-wrap at 80
      columns (AGENTS.md Markdown guidance). `make fmt` is NOT used here — it
      re-flows ~250 unrelated Markdown files tree-wide (see the Decision Log).

    - Risk: A code block that runs a command (e.g. the
      `novel-state set-chapters --chapters '[…]'` example in the users' guide)
      is converted to a form that would not actually run.
      Severity: low
      Likelihood: low
      Mitigation: The spaced surface is exactly how the installed `novel`
      multiplexer is invoked (`novel state set-chapters --chapters '…'`),
      verified against `novel_ralph_skill/commands/names.py`'s `SUBCOMMAND_NAMES`
      and ADR 007's subcommand structure. Convert fenced examples to the spaced
      form verbatim; do not paraphrase flags.

## Progress

    - [x] Work item 0 — Orientation and reference grep (no edits).
    - [x] Work item 1 — Build and record the hit classification for both guides.
    - [x] Work item 2 — Sweep `docs/users-guide.md` to the `novel` surface.
    - [x] Work item 3 — Gate work item 2 (markdownlint + nixie).
    - [x] Work item 4 — Sweep `docs/developers-guide.md` to the `novel` surface
      (including the orientation section at line ~256 and the enumerated
      literal-free legacy-framing lines 273, 277, 345, 356, 489/492, 1354 and
      the 337-368 transition block, ahead of the named subsection ranges).
    - [x] Work item 5 — Gate work item 4 (markdownlint + nixie) and final
      whole-repo grep proof: bare-alternation surface gate with token-level
      preserve subtraction, plus the two-pattern stale-prose CLASS gate that
      fires on "five"-adjacent and "legacy"-framed structure (not a curated
      phrase denylist).

## Surprises & discoveries

    - Observation: No test asserts on the *content* of either guide. The only
      test references to the guides are comments/docstrings that cite them as
      the source of a convention (`tests/conftest.py` line 74,
      `tests/test_interrogate_gate.py` lines 3-4,
      `tests/multiplexer_support.py` lines 9 and 60).
      Evidence: `grep -rnE "users-guide|developers-guide" tests/` returns only
      comment/docstring mentions; none read or parse the guide bodies.
      Impact: This sweep cannot break `make test`; `make all` stays green by
      construction. The mandated gates reduce to `make markdownlint` and
      `make nixie` for the edited Markdown, with `make all` confirmed unaffected.

    - Observation: `docs/developers-guide.md` references several Python code
      identifiers that contain a legacy-form substring but are NOT command-surface
      references: the `installed_novel_state` fixture (lines 31-55), the
      `installed_desloppify` fixture (line 47), the deleted helper
      `_build_and_install_novel_state` (line 34, named only as the thing the
      fixture replaced).
      Evidence: `grep -rln "installed_novel_state\|installed_desloppify"
      tests/` resolves the fixtures to live test modules and
      `tests/installed_binary_fixtures.py` / `tests/conftest.py`.
      Impact: These must be preserved verbatim (Constraints, Risk 1). Only the
      *command* a user types is converted.

    - Observation: (round 3, BR2-1) At least eight present-tense / additive
      legacy framings in `docs/developers-guide.md` carry NEITHER a hyphenated
      command literal NOR a round-2 tripwire phrase, so the round-2 surface gate
      and one-phrase tripwire both reported PASS while they survived. Verified
      live: line 256 "The deterministic spine is five console-scripts"; line 273
      "### The five commands" (heading); line 275 "five separate console-scripts";
      line 310 "these five names are wired as `[project.scripts]`
      console-scripts"; line 322 "The five names live once"; line 337 "rather
      than five separate scripts"; line 345 "exit codes the legacy scripts
      produce" (verbatim a roadmap-forbidden example); line 356
      "`ENVELOPE_COMMAND_NAMES` superset (the legacy five, …)" (also factually
      false — `names.py` defines
      `ENVELOPE_COMMAND_NAMES = SUBCOMMAND_NAMES + ("novel",)`, no "legacy five");
      lines 358/360 "legacy entry points (which stamp `\"novel-state\"` etc.) …
      legacy five `[project.scripts]` entries stay registered and working"; line
      368 "in-process legacy-versus-multiplexer envelope equality"; line 489 "the
      five command names as data"; line 492 "five names live once"; line 1354
      "five-script command surface".
      Evidence: the two-pattern class gate run live against both guides —
      `grep -niE 'five[ -]?(separate )?(console-?script|command|name|script)'`
      returns users'-guide 78, 104 and developers-guide 256, 273, 275, 310, 322,
      337, 489, 492, 1354; and
      `grep -niE 'legacy[ -](five|scripts?|entry[ -]points?)|the legacy scripts produce|legacy-(versus|vs)-multiplexer'`
      returns developers-guide 345, 356, 358, 360, 368. Together they catch every
      line BR2-1 named, including the three the round-2 plan left to "illustrative"
      ranges (273, 345, 1354).
      Impact: Work item 5's stale-prose gate is now these two structural patterns
      (plus a residual additive/stub literal term), and work item 4 enumerates the
      literal-free lines as required reconciles. A literal-only swap can no longer
      report PASS.

    - Observation: `docs/developers-guide.md` lines 310-330 and 350 describe the
      deleted `stub.py` / `make_stub_app` factory in the present tense as the
      mechanism behind three commands. `stub.py` no longer exists in the worktree.
      Evidence: `ls novel_ralph_skill/commands/stub.py` →
      "No such file or directory".
      Impact: This is dead, false prose, not a literal swap. Work item 4
      reconciles it (the three commands are no longer stubs; the dispatcher's
      `main` no longer "generalizes the `stub.py` `_drive` shape").

    - Observation: (work item 1, implementation run 2026-06-26) The enumerating
      greps were re-run live in the worktree and the per-file classification is
      recorded below. Line numbers match the on-disk guides at the start of the
      sweep.
      CONVERT bucket — command-surface references (users' guide): lines 81-85
      (the five-bullet list), 87, 97, 100, 106, 114, 119, 124, 125, 128, 133,
      136, 144, 192, 199, 206, 218, 228, 234, 241, 255, 257, 263 (fenced
      `set-chapters`), 272, 279, 283, 291 (fenced `set-gate`), 296, 305, 309,
      312 (fenced `complete-final-pass`), 315, 320 (fenced `set-fangirl`), 328,
      332 (fenced `set-critic-pass`), 339, 340, 380, 391, 403, 404, 420, 452,
      474, 486, 492.
      CONVERT bucket — command-surface references (developers' guide): lines
      100-101, 106-109, 139, 145-146, 162-164, 281, 298, 300, 302, 305, 307,
      311, 374-378, 383, 388, 512, 523, 529, 533, 538-539, 543, 546, 560, 565,
      568, 647, 811, 827, 829, 837 (only the `` `novel-state` ``'s reference,
      NOT `_novel_done.py`), 866, 869, 925, 928, 938, 951-952, 993, 1050, 1054,
      1090, 1099, 1101, 1132, 1165, 1222, 1231, 1238, 1240, 1273, 1287, 1290,
      1345, 1354.
      PRESERVE bucket — code identifiers (developers' guide, leave verbatim):
      `installed_novel_state` (32, 52), `_build_and_install_novel_state` (34),
      `installed_desloppify` (47), `novel_state.py` (292, 995),
      `_novel_done.py` / `_novel_done` (837, 929).
      RECONCILE bucket — dead-code / additive / present-tense legacy framing
      (developers' guide): `stub.py` / `make_stub_app` (313, 315, 350, 839);
      ADR 005 live citation (277, 335, 338); the FIVE-pattern lines 256, 273,
      275, 310, 322, 337, 489, 492, 1354; the LEGACY-framing lines 345, 356,
      358, 360, 368; users' guide FIVE lines 78, 104; additive line 338.
      Evidence: the three class greps from work item 1 returned exactly the line
      sets enumerated in the round-3 Surprises transcript above.

## Decision log

    - Decision: Treat 1.2.16 as a two-file, documentation-only sweep with
      `make markdownlint` + `make nixie` as the operative gates, asserting
      `make all` is unaffected rather than re-running the whole suite per item.
      Rationale: The roadmap success criterion names exactly the two guides; no
      code, test, or behaviour changes; no test reads the guide bodies. Running
      `make all` once at the end confirms no incidental breakage.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Convert only command-surface references; preserve Python code
      identifiers that share a legacy substring (fixtures, module paths, deleted
      helpers).
      Rationale: Renaming a live fixture or module name in prose would make the
      developers' guide describe code that does not exist — the opposite of the
      task's truthfulness goal. The task targets "console-script reference[s]",
      i.e. the command the harness/user invokes.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Keep ADR 005 mentions only where they are explicitly historical
      ("superseding ADR 005"), and remove/rewrite any that frame five scripts as
      the *current* surface.
      Rationale: ADR 007 supersedes ADR 005 but the supersession is legitimate
      history; the falsehood is present-tense "the v1 spine **is** five separate
      console-scripts", not the historical record.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Exclude `per_chapter_loop.feature`, `test_pyproject_scripts.py`,
      and `test_contract_app_centralisation.py` from this sweep.
      Rationale: Roadmap sub-task 1.2.15.1 explicitly owns those stale literals.
      Touching them here would duplicate or collide with that addendum.
      Date/Author: 2026-06-26, planning agent.

    - Decision: (round 2, B1) The work item 5 surface gate uses the BARE
      alternation `novel-state|novel-done|novel-compile|desloppify|wordcount`
      with the five preserve identifiers subtracted at TOKEN level
      (`grep -onE … | grep -vE ':(…)$'`), not the round-1
      space/anchor-narrowed pattern.
      Rationale: The narrowed pattern reported PASS while ~30 genuine references
      survived (backtick, comma, apostrophe boundaries). Totality must come from
      enumerated subtraction, never from narrowing the surface. Token-level
      (not line-level) subtraction is required because line 837 carries a
      preserve identifier (`_novel_done.py`) and a convert reference
      (`` `novel-state` ``) on the SAME line; a line-level `-vE` would suppress
      the whole line and hide the surviving surface token. (Round-3 correction,
      A2: the round-2 text also claimed line 47 mixes preserve+convert. It does
      NOT — `grep -oE` matches `installed_desloppify` as one leftmost-longest
      token there and `desloppify` appears only as its substring, so line 47
      yields no separate convert token. Line 837 alone justifies token-level
      subtraction. The gate mechanism is unaffected; only the rationale text is
      corrected.)
      Date/Author: 2026-06-26, planning agent.

    - Decision: (round 3, BR2-1) Replace the curated stale-prose phrase denylist
      with a two-pattern CLASS gate that fires on the structure of legacy
      framing, and enumerate the literal-free legacy-framing lines explicitly in
      work item 4 as required reconciles. The class gate is the Wafflecat
      alternative the round-2 review recommended:
      `grep -niE 'five[ -]?(separate )?(console-?script|command|name|script)'`
      (catches 256, 273, 275, 310, 322, 337, 489, 492, 1354 and users'-guide 78,
      104) plus a `legacy`-framing pattern
      (`legacy[ -](five|scripts?|entry[ -]points?)|the legacy scripts produce|legacy-(versus|vs)-multiplexer`,
      catching 345, 356, 358, 360, 368).
      Rationale: Round 2 patched ONE instance of the B2 class (added the single
      phrase "five console-scripts" for line 256) but at least six further
      present-tense / additive framings carry NO surface literal and NO tripwire
      phrase, so the round-2 acceptance gate would report PASS while lines 273
      ("### The five commands" heading), 345 ("exit codes the legacy scripts
      produce" — verbatim a roadmap-forbidden example), 356 ("the legacy five")
      and 1354 ("five-script command surface") survive. A curated denylist
      inherently lags the prose; a structural class gate cannot be under-fixed by
      a literal-only swap. Verified against the live developers-guide: the two
      patterns together catch every line BR2-1 enumerated (transcript recorded in
      Surprises & Discoveries). Lines 273/277/345/356/489/492/1354 and the
      337-368 transition block are now ALSO enumerated in work item 4 change-kinds
      so they are not left to the "illustrative" ranges. The accepted trade-off
      (the "five" gate may fire on a legitimate "five operations" count) is the
      intended forcing function — surviving counts must be phrased without the
      legacy-surface noun.
      Date/Author: 2026-06-26, planning agent.

    - Decision: (round 2, B3) Drop the claim that design §4 is "already written
      in the spaced form"; make `names.py` `SUBCOMMAND_NAMES` + ADR 007 the sole
      surface-vocabulary source and use §4 only for per-operation BEHAVIOUR, with
      an explicit caveat that §4's command literals are hyphenated and must be
      re-spaced when quoted.
      Rationale: Verified that §4's body prose contains 51 hyphenated command
      references against only 9 spaced (the spaced forms are confined to
      subsection headings). An implementer faithfully mirroring §4 would
      reproduce exactly the hyphenated forms task 1.2.16 must eliminate.
      Date/Author: 2026-06-26, planning agent.

    - Decision: (implementation, 2026-06-26) Do NOT run `make fmt`. In this
      worktree `make fmt` re-flows ~250 unrelated Markdown files across the
      whole tree (the spurious-churn pattern recorded in dozens of repo
      stashes) and also fails on pre-existing line-length errors in
      `docs/issues/*.md` that predate this task. Running it would violate the
      two-file scope Constraint by mutating files outside the sweep. The
      operative gate for this documentation-only task is `make markdownlint`
      (run per guide and tree-wide) plus `make nixie`; `make all` is run once
      at the end to confirm no code/test breakage. The two edited guides are
      hand-wrapped at 80 columns so they pass `markdownlint` without `make fmt`.
      Rationale: Constraint (edit only the two guides) overrides the plan's
      `make fmt` step, which the planning agent included before the
      whole-tree churn behaviour was observed in this worktree.
      Date/Author: 2026-06-26, implementation agent.

    - Decision: (implementation, 2026-06-26) Refine the work item 5 surface
      gate to also subtract the correctly-converted `novel desloppify` and
      `novel wordcount` forms, because the bare alternation
      `…|desloppify|wordcount` matches `desloppify`/`wordcount` as SUBSTRINGS of
      the converted `novel desloppify`/`novel wordcount` and so false-positives
      on the target end-state. The refined gate extracts every alternation hit,
      then drops any token that is a preserve identifier OR is immediately
      preceded by `novel ` (the converted spaced form). What survives is a
      genuinely un-converted hyphenated or bare-generic reference, which must be
      empty. Verified: in the users' guide every `desloppify`/`wordcount` is now
      preceded by `novel `; no bare or hyphenated surface reference survives.
      Rationale: the plan's literal gate would report a false failure on the
      correct output; the surface vocabulary (`names.py` `SUBCOMMAND_NAMES`)
      makes `novel desloppify`/`novel wordcount` the required forms, so they
      must be excluded from the "un-converted" set.
      Date/Author: 2026-06-26, implementation agent.

## Outcomes & retrospective

Completed 2026-06-26. Both guides were swept to the single `novel <sub>`
surface; the final acceptance gates all pass.

- Surface gate (refined token subtraction, see Decision Log): prints nothing —
  no `novel-state` / `novel-done` / `novel-compile` / hyphenated or bare-generic
  `desloppify` / `wordcount` command-surface reference survives in either guide.
  The five preserve identifiers (`installed_novel_state`, `installed_desloppify`,
  `_build_and_install_novel_state`, `_novel_done.py`, `novel_state.py`) are
  intact at their original counts.
- Stale-prose CLASS gate (three patterns): the "five"-adjacency, "legacy"-framing,
  and additive/stub-literal greps each print nothing. The heading became
  `### The deterministic commands`; the orientation spine line, the "five names
  live once" registry prose, the additive "stands up that multiplexer
  additively" framing, the "legacy five" superset claim, the "the legacy scripts
  produce" verbatim forbidden example, and the "five-script command surface"
  line are all reconciled. The stale `COMMAND_NAMES` symbol (retired; a test
  asserts `not hasattr(names, "COMMAND_NAMES")`) was corrected to
  `ENVELOPE_COMMAND_NAMES`, and the `test_multiplexer_behaviour.py` description
  was corrected from "legacy-versus-multiplexer" to the truthful
  multiplexer-versus-direct-`build_app` envelope equality.
- `make markdownlint` and `make nixie` exit 0 on both guides and this plan.
- `make all` is green at HEAD (1151 passed, 1 skipped). One Hypothesis
  `DeadlineExceeded` flake in `test_reconcile_derivation.py` (timing, not
  content) cleared on re-run; the change touches no Python.
- ADR 005 survives only as explicit superseded history ("supersedes ADR 005");
  the `adr-004-…console-scripts` / `adr-006-…console-scripts` ADR *filenames*
  are link targets, not present-tense surface claims, and are left verbatim.

Deviations from the plan (all recorded in the Decision Log): `make fmt` was not
run (whole-tree reflow churn would violate the two-file scope); the work item 5
surface gate was refined to subtract the correctly-converted `novel desloppify`
/ `novel wordcount` forms (the plan's bare gate false-positives on them). The
developers' guide picked up incidental 80-column reflow churn from an earlier
exploratory `make fmt`; it is content-equivalent (token counts verified against
HEAD) and the edited lines were hand-wrapped, so `make markdownlint` is clean.

## Context and orientation

A novice should read these before touching anything:

- [docs/roadmap.md](../roadmap.md), task 1.2.16 (the remediation paragraph and
  its success criterion) and its parent step 1.2 — the source of truth for
  scope and acceptance.
- [docs/adr-007-command-surface-novel-multiplexer.md](../adr-007-command-surface-novel-multiplexer.md)
  — fixes the surface as a single `novel` multiplexer (supersedes ADR 005). Its
  "Decision outcome" section lists the exact subcommand structure; its
  "Migration plan" section is the template for the truthful end-state prose.
- [docs/novel-ralph-harness-design.md](../novel-ralph-harness-design.md) §4
  ("The deterministic commands") and §4.1-§4.5 — the authoritative description
  of each operation's **behaviour** (what `compile` checks, what `desloppify`
  rewrites, what the `state` verbs mutate). Use §4 only for per-operation
  behaviour wording. **Caveat (verified):** §4's *command literals* are still
  written in the retired hyphenated form — its body prose contains 51 hyphenated
  `novel-state`/`novel-compile`/`novel-done` references against only 9 spaced
  (the spaced forms are confined to the subsection *headings*). So §4 is
  **not** a spaced-surface reference: any command literal quoted from §4 must
  be re-spaced to the `novel state` / `novel done` / `novel compile` /
  `novel desloppify` / `novel wordcount` form before it enters a guide. The
  single source of the surface vocabulary is `names.py` `SUBCOMMAND_NAMES` plus
  ADR 007 (below), not §4.
- [AGENTS.md](../../AGENTS.md) — quality gates ("Markdown files (`.md` only)":
  `make markdownlint`, `make nixie`) and the Markdown guidance (80-column
  prose, 120-column code, dash bullets, en-GB Oxford spelling).
- [docs/documentation-style-guide.md](../documentation-style-guide.md) — house
  style the guides already follow.

The single, authoritative source of the surface vocabulary is
[`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
together with ADR 007: `SUBCOMMAND_NAMES` is exactly
`("novel state", "novel done", "novel compile", "novel desloppify", "novel wordcount")`,
`ENVELOPE_COMMAND_NAMES` is those five plus the bare `"novel"`, and
`project_scripts_table()` returns exactly `{"novel": …}`. **Every** command
form written into a guide must be confirmed against this file (and ADR 007's
subcommand structure) — never against design §4's body prose, whose command
literals are still hyphenated (see the §4 caveat above).

Terms used in this plan:

- **Command-surface reference**: a token naming the command a user or the
  harness invokes on the shell — `novel-state`, `novel-done`, `novel-compile`,
  `desloppify`, `wordcount`, and their subcommand/flag forms
  (`novel-state check`, `novel-compile --check`, `desloppify --ledger`). These
  are converted.
- **Code identifier**: an importable Python name (fixture, module, function)
  that happens to contain a legacy substring (`installed_novel_state`,
  `_novel_done.py`, `novel_state.py`, `installed_desloppify`,
  `_build_and_install_novel_state`). These are preserved.
- **Additive-transition prose**: sentences describing the multiplexer being
  added *beside* the legacy scripts, or the legacy scripts being still present
  / scheduled for later removal ("additively", "stay registered", "their
  removal … are roadmap tasks", "still **stubs**"). These are reconciled to the
  current single-surface state.

Library-API note (verification, not a change): the developers' guide's cuprum
prose (the `single_program_catalogue` fixture, lines 28-29 and the e2e
fixtures) describes test scaffolding, not the command surface, and is untouched
by this sweep. For completeness it was verified against the locked **cuprum
0.1.0** (`uv.lock` line 113): `cuprum.catalogue.ProgramCatalogue(projects=…)`
is keyword-only,
`cuprum.catalogue.ProjectSettings(name, programs, documentation_locations, noise_rules)`
is its frozen project record, and
`cuprum.program.Program = NewType("Program", str)` allowlists any string
including an absolute path (`cuprum/catalogue.py` lines 33-122,
`cuprum/program.py` line 16). No cuprum API is newly exercised by 1.2.16, so
there is no cuprum forking decision to resolve.

## Plan of work

The sweep proceeds file by file, each behind its own Markdown gate, so a
stopping point never leaves a half-converted guide. Stage A (work items 0-1)
understands and classifies without editing; Stage B (items 2-3) sweeps and
gates the users' guide; Stage C (items 4-5) sweeps and gates the developers'
guide and proves the whole-repo end-state.

### Work item 0 — Orientation and reference grep (no edits)

Implements: roadmap 1.2.16 scope; ADR 007 surface vocabulary.

Read, in order: roadmap 1.2.16, ADR 007 (Decision outcome + Migration plan),
design §4-§4.5, AGENTS.md Markdown sections, and both guides end to end. No
file is edited in this item; it exists so the implementer holds the target
vocabulary and the truthful end-state in mind before classifying hits.

Docs to read: roadmap.md (1.2.16), adr-007, design §4, AGENTS.md,
documentation-style-guide.md.

Skills to load: `execplans` (this plan's format), `en-gb-oxendict` (spelling
convention for every edited sentence). Use `leta` (`leta show`, `leta files`)
and `grepai search` for navigation rather than ad-hoc reads.

Tests: none (no behaviour change). Validation: confirm by reading that the
spaced forms in design §4 match `SUBCOMMAND_NAMES` in
`novel_ralph_skill/commands/names.py`.

### Work item 1 — Build and record the hit classification for both guides

Implements: the Constraints' code-identifier boundary; Risk 1 mitigation.

Run the enumerating greps below and record, in the `Surprises & Discoveries`
section of this plan, the per-file list of hits split into two buckets:
**convert** (command-surface references) and **preserve** (code identifiers).
This classification is the contract the two sweep items execute against, so a
later edit cannot silently rename a fixture.

Commands (run from the worktree root). The first two enumerate command-surface
literals per guide; the third enumerates the developers' guide's code
identifiers and stale-prose tripwires:

    LEGACY='novel-state|novel-done|novel-compile|desloppify|wordcount'
    grep -nE "$LEGACY" docs/users-guide.md
    grep -nE "$LEGACY" docs/developers-guide.md

    IDENTS='installed_novel_state|installed_desloppify'
    IDENTS="$IDENTS|_build_and_install_novel_state|_novel_done"
    IDENTS="$IDENTS|novel_state\.py|stub\.py|make_stub_app"
    grep -nE "$IDENTS" docs/developers-guide.md

    # Stale-prose CLASS gate (two structural patterns + a residual literal term).
    # Pattern 1 — "five" adjacent to a surface noun (catches headings and counts
    # with no hyphenated literal):
    FIVE='five[ -]?(separate )?(console-?script|command|name|script)'
    grep -niE "$FIVE" docs/users-guide.md docs/developers-guide.md
    # Pattern 2 — "legacy" framing of the retired scripts:
    LEG='legacy[ -](five|scripts?|entry[ -]points?)'
    LEG="$LEG|the legacy scripts produce|legacy-(versus|vs)-multiplexer"
    grep -niE "$LEG" docs/users-guide.md docs/developers-guide.md
    # Residual additive/stub literals (carry neither "five" nor "legacy"):
    RESID='stands up that multiplexer additively|stay(s)? registered'
    RESID="$RESID|still \*\*stubs\*\*|stub\.py|adr-005|ADR 005"
    grep -niE "$RESID" docs/developers-guide.md

The known preserve-bucket identifiers (do not convert) are
`installed_novel_state`, `installed_desloppify`,
`_build_and_install_novel_state`, `_novel_done` (module
`novel_ralph_skill/commands/_novel_done.py`), and `novel_state.py` (module
`novel_ralph_skill/commands/novel_state.py`). The `stub.py` / `make_stub_app`
hits are dead-code references (the file was deleted) and belong to the
**reconcile** bucket handled by work item 4, not a literal swap.

Docs to read: this plan's Constraints and Risks.

Skills to load: `leta` (resolve each ambiguous identifier with `leta show` to
confirm whether it is a live code symbol before bucketing it).

Tests: none. Validation: the classification is recorded in this plan and every
hit from the greps above appears in exactly one bucket.

### Work item 2 — Sweep `docs/users-guide.md` to the `novel` surface

Implements: roadmap 1.2.16 success criterion (users' guide half); ADR 007
Decision outcome; design §4-§4.5.

Independently committable. Edit only `docs/users-guide.md`. Two kinds of change:

1. **The "Installed Commands" section (around lines 76-104).** Rewrite the
   opening claim — installing the wheel no longer "puts five console-scripts
   onto `PATH`"; it puts a single `novel` command on `PATH` (ADR 007;
   `project_scripts_table()` returns `{"novel": …}`). Replace the five-bullet
   list of separate scripts with a description of the single `novel`
   multiplexer and its `state` subgroup plus four leaf verbs, taking the
   command vocabulary from `names.py` `SUBCOMMAND_NAMES` and ADR 007's
   subcommand structure (not from design §4's hyphenated body literals). Design
   §4's opening paragraph may supply the *behaviour* framing, with any command
   literal it quotes re-spaced. Remove the now-false sentence "All
   five console-scripts now drive their real checkers." (the scripts no longer
   exist; the operations do).

2. **Body command references throughout (lines ~87-492).** Convert every
   command-surface literal to its spaced form, using the bucket-1 list from
   work item 1: `novel-state check` → `novel state check`,
   `novel-state --human check` → `novel state --human check`,
   `novel-state set-chapters …` → `novel state set-chapters …` (including the
   fenced `--chapters '[…]'` example), `novel-state set-gate` →
   `novel state set-gate`, `novel-state reconcile` → `novel state reconcile`,
   `novel-compile` → `novel compile`, `novel-compile --check` →
   `novel compile --check`, `desloppify` → `novel desloppify` (including
   `desloppify --ledger`, `desloppify --chapter`, and the
   `--pack novel_ralph_skill/rulepack/packs/ai-isms.toml` example), `wordcount`
   → `novel wordcount`, and `novel-done` → `novel done`. Reconcile any
   surrounding prose so the sentence reads truthfully (for example, a clause
   that introduced a script as a separate binary now introduces a subcommand of
   `novel`).

Do not touch the "Quality Gates", "Dependency Auditing", "Rust Test Behaviour",
"Local GitHub Actions Validation", or "Cleaning Local State" sections — they
carry no command-surface reference and are out of scope.

Docs to read: design §4.1-§4.5 (per-operation *behaviour* wording only;
re-space any hyphenated command literal it quotes — see the §4 caveat in
Context), ADR 007 (subcommand structure), `names.py` `SUBCOMMAND_NAMES` (the
authoritative spaced command forms), AGENTS.md Markdown guidance (80-column
prose, 120-column code).

Skills to load: `en-gb-oxendict` (every reworded sentence stays en-GB Oxford
spelling), `leta`/`grepai` for navigation.

Tests: none — this is documentation. Per the AGENTS.md testing rules, a
documentation-only change that alters no externally observable behaviour adds
no unit, behavioural, property, snapshot, or e2e test; the Markdown gates are
the verification. (Verified: no test reads the guide body — see
`Surprises & Discoveries`.)

Validation for this item is performed by work item 3.

### Work item 3 — Gate work item 2 (markdownlint + nixie)

Implements: AGENTS.md "Markdown files (`.md` only)" gates.

Run, from the worktree root:

    # Hand-wrap edited lines at 80 columns; do NOT run `make fmt` (it re-flows
    # ~250 unrelated Markdown files tree-wide — see the Decision Log).
    make markdownlint  # expect: clean exit, no findings
    make nixie         # expect: clean exit (the users' guide has no Mermaid)
    # expect: no command-surface hits remain
    grep -nE 'novel-state|novel-done|novel-compile|desloppify|wordcount' \
      docs/users-guide.md

Acceptance: `make markdownlint` and `make nixie` exit 0; the grep returns no
*command-surface* hit (the users' guide carries no preserve-bucket code
identifiers, so a clean grep is total). Commit the users'-guide sweep as one
atomic commit with an imperative subject (for example, "Sweep users' guide to
the novel multiplexer surface"). If the gate fails, fix within tolerance (Risk
3 mitigation: re-wrap at 80 columns) and re-run before committing.

### Work item 4 — Sweep `docs/developers-guide.md` to the `novel` surface

Implements: roadmap 1.2.16 success criterion (developers' guide half, including
the "developers' guide multiplexer subsection" the task names explicitly); ADR
007; design §4.

Independently committable. Edit only `docs/developers-guide.md`. The named line
ranges below are **illustrative anchors, not the authoritative worklist**. The
authoritative worklist is the **union of two enumerations**: (a) the bare-grep
surface-token list from work item 1 (every hyphenated surface token, minus the
enumerated preserve identifiers), and (b) the **literal-free legacy-framing
lines** the two stale-prose class patterns flag — every line returned by the
"five"-adjacency and "legacy"-framing greps in work item 1. The class-gate hits
are NOT optional clean-up left to care: each is a required reconcile listed
explicitly below. Several surface hits also fall *outside* the emphasized
subsections (for example lines 311, 837, 925, 1354); convert every one. Five
kinds of change, in order:

0. **Reconcile the "Novel-ralph harness architecture" orientation section
   (heading at line ~251, body around line ~256), which sits BEFORE "The five
   commands" subsection.** Line 256 reads, in the present tense, "The
   deterministic spine is **five console-scripts**; the model supplies
   judgement." This frames the retired five scripts as the current spine and so
   violates the "no prose treats the retired scripts as present" criterion even
   though it carries no hyphenated literal. Rewrite it to name the single
   `novel` multiplexer as the deterministic spine — e.g. "The deterministic
   spine is the single `novel` multiplexer (a `state` subgroup and four leaf
   verbs); the model supplies judgement." (ADR 007; `names.py`
   `SUBCOMMAND_NAMES`.) The orientation section is in scope.

1. **Reconcile the "The five commands" subsection (around lines 273-330).** This
   subsection is the core falsehood: it states "The v1 spine **is** five
   separate console-scripts … not a single multiplexer", cites the superseded
   ADR 005 as the live rationale, and describes three commands as "still
   **stubs**" defined by the deleted `stub.py` / `make_stub_app`. Rewrite it to
   describe the single `novel` multiplexer as the spine (ADR 007), with the
   five operations as a `state` subgroup and four leaf verbs. Drop the stub
   paragraph entirely (the operations all drive real apps; `stub.py` no longer
   exists). Re-point the rationale citation from ADR 005 to ADR 007; keep ADR
   005 only if referenced as superseded history. The per-operation bullets
   (`novel-state`, `novel-done`, …) become `novel state`, `novel done`, … with
   their behaviour text preserved and their design cross-references (§4.1-§4.5)
   intact.

2. **Reconcile the "The `novel` multiplexer" subsection (around lines
   332-370).**
   Remove the additive-transition framing: the multiplexer is no longer being
   "stood up additively"; the "legacy five `[project.scripts]` entries" do not
   "stay registered and working"; "their removal and the prose sweep … roadmap
   tasks 1.2.13 and 1.2.14" is completed history, not future work. Rewrite to
   the present single-surface state: `novel` is the sole entry point; the
   dispatcher in `novel_ralph_skill/commands/novel.py` builds a parent contract
   app via `make_contract_app("novel")` and mounts each operation's `build_app`
   (these symbols still exist — verified: `make_contract_app` at
   `novel_ralph_skill/contract/runner.py` and the five
   `app.command(<leaf>.build_app(), name=…)` mounts at
   `novel_ralph_skill/commands/novel.py` lines 84-89). Remove the sentence that
   says `main` "generalizes the `stub.py` `_drive` shape" (stub.py is gone).
   **Advisory A1 — do NOT replace it by quoting the live dispatcher docstring**:
   `novel.py` line 139 itself still says "Generalizes the `_drive` shape
   `stub.py` uses" (that code-docstring fix is owned by roadmap task 1.2.15.1,
   out of scope here), so quoting it would re-introduce a `stub.py` reference.
   The truthful current wiring to describe is `make_contract_app("novel")` plus
   the five `app.command(<leaf>.build_app(), name=…)` mounts (novel.py lines
   84-89). Either describe that, or simply drop the implementation-archaeology
   detail; do not reach for `stub.py` framing in either direction. Update the
   name-registry prose so it matches the current `names.py`: `SUBCOMMAND_NAMES`
   is the five spaced `novel <verb>` names and
   `ENVELOPE_COMMAND_NAMES = SUBCOMMAND_NAMES + ("novel",)` — there is NO
   "legacy five" in the superset and no legacy-vs-spaced transition (line 356's
   "the legacy five, the spaced names" framing is factually false against the
   current `names.py` and must be rewritten, not merely re-spaced). Consider
   folding the two subsections into one single-surface section if that reads
   more truthfully, but a minimal reconcile that leaves the heading structure
   intact is acceptable.

3. **Convert remaining body command references (the matrix, loop, segregation,
   and command-specific subsections, lines ~94-1354).** Apply the bucket-1
   conversions from work item 1: `novel-state check` → `novel state check`,
   `novel-compile --check` → `novel compile --check`, `novel-done` →
   `novel done`, `desloppify` → `novel desloppify`, `wordcount` →
   `novel wordcount`, and `novel-state <verb>` → `novel state <verb>`
   everywhere they name a command the harness invokes. Reconcile any
   present-tense legacy claim (for example a sentence asserting "the legacy
   entry points (which stamp `\"novel-state\"` etc.)") into history or the
   current single surface. This bucket also includes the **present-tense
   dead-code prose at line ~839** in the done-predicate section (~827): "the
   `stub.py` `novel_done()` entry point drives it through the shared `run`
   wrapper exactly as `desloppify()` does" — `stub.py` is deleted, so rewrite
   this to describe the current dispatcher path (the `novel done` leaf's
   `build_app`/`run` wiring) or drop the implementation archaeology; do not
   leave `stub.py` framed as a live mechanism. Note line 837 carries **both** a
   preserve identifier (`_novel_done.py`, keep verbatim) and a convert reference
   (`` `novel-state` ``'s, re-space to `` `novel state` ``'s): change only the
   latter on that line.

4. **Reconcile the literal-free legacy-framing lines explicitly (BR2-1).** These
   lines carry a present-tense or additive legacy framing but NO hyphenated
   command literal, so the surface gate never sees them; the round-2 plan left
   several to the "illustrative" ranges and the round-2 review (BR2-1) showed
   three would survive the gate (273, 345, 1354). Each is now a REQUIRED
   reconcile — the work-item-5 class gate (work item 5) enforces them. Treat
   the line numbers as anchors and re-locate by phrase if the file has shifted:
   - **Line ~256** — orientation spine line; handled by change-kind 0 above.
   - **Line ~273** — the `### The five commands` **heading**. Rename it so it
     does not assert five separate commands as the current surface — e.g.
     `### The novel multiplexer commands` or `### The deterministic commands`.
     A literal-only swap of the bullets below it leaves this heading false.
   - **Line ~275** — "The v1 spine **is** five separate console-scripts … not a
     single multiplexer"; handled by change-kind 1. Eliminate the contrastive
     "five separate … not a multiplexer" framing entirely (do not merely reword
     the count), or the `five separate` class term stays red.
   - **Line ~277** — the inline link to
     `adr-005-command-surface-five-scripts.md`. Re-point to ADR 007, keeping
     ADR 005 only if cited explicitly as superseded history (per the Decision
     Log). The bare ADR-005 link as a *live* rationale must go.
   - **Lines ~310 / ~322** — "these **five names** are wired as
     `[project.scripts]` console-scripts" and "The **five names** live once, as
     data, in a single registry". Rewrite to the single-`novel` reality: one
     `[project.scripts]` entry (`novel`), with the five spaced subcommand names
     held as data in `names.py` `SUBCOMMAND_NAMES`. Phrase any surviving count
     without the legacy-surface noun (e.g. "the five state operations" or drop
     the count) so the class gate cannot fire.
   - **Lines ~337 / ~338** — "rather than **five separate scripts**" and
     "Roadmap task 1.2.12 **stands up that multiplexer additively**". Handled by
     change-kind 2; eliminate the contrastive and additive framing, not just the
     literal.
   - **Line ~345** — "exit codes **the legacy scripts produce**". This is
     *verbatim* one of the roadmap success criterion's own forbidden examples.
     Rewrite to the present single surface — the multiplexer emits the same
     envelope and exit codes each mounted leaf produces (there are no separate
     legacy scripts to "produce" anything).
   - **Lines ~356 / ~358 / ~360 / ~368** — the `ENVELOPE_COMMAND_NAMES`
     "**legacy five**" claim (factually false per change-kind 2), the "legacy
     entry points (which stamp `\"novel-state\"` etc.)", the "legacy five
     `[project.scripts]` entries **stay registered and working**", and the
     "in-process **legacy-versus-multiplexer** envelope equality" test
     description. All describe a retired transition as live; rewrite to the
     current single-surface state or to explicit completed history.
   - **Lines ~489 / ~492** — "source-of-truth module that holds only the **five
     command names** as data" and "**five names** live once and neither layer
     re-spells them". Reconcile to the current `names.py` (`SUBCOMMAND_NAMES` +
     `ENVELOPE_COMMAND_NAMES`, no legacy-vs-spaced superset); phrase any count
     without the legacy-surface noun.
   - **Line ~1354** — "**five-script command surface** — the ledger is a flag on
     `desloppify`". This line carries `desloppify` (caught by the surface gate)
     AND the literal-free "five-script command surface" framing; a literal-only
     swap of `desloppify` → `novel desloppify` leaves "five-script command
     surface" intact. Rewrite to "the single `novel` surface — the ledger is a
     flag on `novel desloppify`, never a …", eliminating "five-script".

**Preserve verbatim** (bucket 2, work item 1): `installed_novel_state`,
`installed_desloppify`, `_build_and_install_novel_state`, the module path
`novel_ralph_skill/commands/_novel_done.py`, and the module `novel_state.py`.
These are code identifiers, not command-surface references.

Docs to read: design §4-§4.5 (per-operation *behaviour* wording only; its
command literals are hyphenated and must be re-spaced — see the §4 caveat in
Context), ADR 007 (Decision outcome + Migration plan, for the truthful
end-state framing), the current `novel_ralph_skill/commands/names.py` (the
authoritative spaced surface vocabulary) and `novel.py` (to keep symbol prose
accurate), AGENTS.md Markdown guidance.

Skills to load: `en-gb-oxendict` (each reworded sentence), `leta` (`leta show`
on `make_contract_app`, `build_app`, `SUBCOMMAND_NAMES` to confirm they still
exist before describing them), `grepai` for navigation.

Tests: none — documentation-only (same rationale as work item 2; no test reads
the guide body). The Markdown gates are the verification.

Validation for this item is performed by work item 5.

### Work item 5 — Gate work item 4 and prove the whole-repo end-state

Implements: AGENTS.md Markdown gates; roadmap 1.2.16 success criterion (final
proof).

Run, from the worktree root.

The **surface gate** must achieve totality by subtracting the ENUMERATED
preserve-bucket identifiers from the *bare* alternation — **never** by
narrowing the surface pattern with space/anchor boundaries (the round-1 spaced
pattern `` `novel-state |novel-done|... | wordcount ` `` produced ~30 false
negatives, e.g. line 281 `` `novel-state` `` at a backtick boundary, line 305
`desloppify,` before a comma, line 837 `` `novel-state` ``'s before an
apostrophe, and lines 993, 1165, 1231, 1240, 1273, 1287, 1290, 1345; B1).
Subtraction is done at **token** level with `grep -oE` (not line level with
`grep -vE`), because line 837 carries a preserve identifier (`_novel_done.py`)
*and* a genuine convert reference (`` `novel-state` ``) on the SAME line — a
line-level `-vE` would wrongly suppress the whole line and hide the surviving
surface token. (Round-3 correction, A2: line 47 does NOT mix preserve and
convert — `grep -oE` matches `installed_desloppify` as one leftmost-longest
token there and `desloppify` appears only as its substring, so line 47 yields
no separate convert token. Line 837 alone justifies token-level subtraction;
the gate is unaffected.) The five preserve tokens are exactly
`installed_novel_state`, `installed_desloppify`,
`_build_and_install_novel_state`, `_novel_done.py`, and `novel_state.py` (note:
`installed_novel_state` / `novel_state.py` use an underscore and so never match
the hyphenated `novel-state` alternation anyway; they are subtracted
defensively and to cover any future underscore-form alternation):

    # Do NOT run `make fmt` (Decision Log): hand-wrap edited lines at 80 columns.
    make markdownlint  # expect: clean
    make nixie         # expect: clean (neither guide has Mermaid)
    GUIDES='docs/users-guide.md docs/developers-guide.md'
    # Bare surface alternation; subtract the enumerated preserve tokens AND the
    # correctly-converted `novel <verb>` forms at TOKEN level. Expect: empty (no
    # surviving command-surface reference). The converted `novel desloppify` /
    # `novel wordcount` forms contain `desloppify` / `wordcount` as substrings,
    # so the leftmost-longest `novel <verb>` token is extracted FIRST and
    # subtracted; what survives is a genuinely un-converted hyphenated or
    # bare-generic reference (implementation Decision Log, gate refinement).
    SURFACE='novel-state|novel-done|novel-compile|desloppify|wordcount'
    CONVERTED='novel (desloppify|wordcount)'
    PRESERVE='installed_novel_state|installed_desloppify'
    PRESERVE="$PRESERVE|_build_and_install_novel_state|_novel_done\.py"
    PRESERVE="$PRESERVE|novel_state\.py"
    grep -onE "$PRESERVE|$CONVERTED|$SURFACE" $GUIDES \
      | grep -vE ":($PRESERVE)\$" | grep -vE ':(novel desloppify|novel wordcount)$'
    # Stale-prose CLASS gate (BR2-1): structural patterns, not a phrase denylist.
    # Pattern 1 — "five" adjacent to a surface noun. Expect: empty.
    FIVE='five[ -]?(separate )?(console-?script|command|name|script)'
    grep -niE "$FIVE" $GUIDES
    # Pattern 2 — "legacy" framing of the retired scripts. Expect: empty.
    LEG='legacy[ -](five|scripts?|entry[ -]points?)'
    LEG="$LEG|the legacy scripts produce|legacy-(versus|vs)-multiplexer"
    grep -niE "$LEG" $GUIDES
    # Residual additive/stub literals (neither "five" nor "legacy"). Expect: empty.
    RESID='stands up that multiplexer additively|stay(s)? registered'
    RESID="$RESID|still \*\*stubs\*\*|stub\.py"
    grep -niE "$RESID" $GUIDES
    make all           # expect: green; confirms no code/test breakage

The surface grep prints `path:line:token` for every alternation hit, then drops
any line whose extracted token is exactly a preserve identifier; what survives
is the set of un-converted command-surface references, which must be **empty**.

The **stale-prose gate is a structural CLASS gate, not a curated phrase
denylist** (BR2-1). A denylist enumerates known wordings and inherently lags
the prose — round 2 added the single phrase "five console-scripts" for line 256
and still let at least six further literal-free framings pass. The two class
patterns fire on the *structure* of legacy framing. Pattern 1 (the digit-word
"five" adjacent to a surface noun) catches lines 256, 273 (the
`### The five commands` heading), 275, 310, 322, 337, 489, 492, 1354 in the
developers' guide and lines 78, 104 in the users' guide — including the three
the round-2 plan left to "illustrative" ranges (273, 1354 here; 345 is caught
by pattern 2). Pattern 2 (the "legacy" framing of the retired scripts) catches
345 ("the legacy scripts produce" — verbatim a roadmap-forbidden example), 356
("the legacy five"), 358, 360, and 368 ("legacy-versus-multiplexer"). Pattern 1
may also fire on a legitimate "five operations" sentence — that is the intended
forcing function: phrase any surviving count without the legacy-surface noun
(`console-script`, `command`, `name`, `script`), e.g. "the five state
operations", or drop the count. The residual literal term catches the
additive/stub framings that carry neither "five" nor "legacy" ("stands up that
multiplexer additively", "stay(s) registered", "still **stubs**", "stub.py").
All three greps must print nothing.

Acceptance: `make markdownlint` and `make nixie` exit 0; the surface grep
prints **nothing** (totality is by enumerated token subtraction, not pattern
narrowing); all three stale-prose class greps print **nothing** in either guide;
`make all` is green. Commit the developers'-guide sweep as one atomic commit.
Then update this plan's `Progress`, `Outcomes & retrospective`, and Status to
COMPLETE.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-16`.

1. Work item 0-1: run the enumerating greps (above) and record the bucketed
   classification in this plan. No edits.
2. Work item 2: edit `docs/users-guide.md` per the two change kinds. Use `Edit`
   for targeted replacements; convert fenced command examples verbatim to the
   spaced form.
3. Work item 3: `make markdownlint && make nixie` (no `make fmt`), then the
   users'-guide grep; commit.

   Expected markdownlint transcript on success (illustrative):

       $ make markdownlint
       … markdownlint-cli2 …
       Finding: **/*.md
       … (no error lines) …

4. Work item 4: edit `docs/developers-guide.md` per the five change kinds
   (including change-kind 4's enumerated literal-free legacy-framing lines),
   preserving the bucket-2 code identifiers.
5. Work item 5: `make markdownlint && make nixie` (no `make fmt`), the surface
   grep and the three stale-prose class greps, then `make all`; commit; finalize
   the plan.

## Validation and acceptance

Quality criteria (what "done" means):

- Behaviour: unchanged. No console-script, subcommand, flag, exit code, or
  envelope is altered; this is prose only.
- Truthfulness: no `novel-state` / `novel-done` / `novel-compile` / `desloppify`
  / `wordcount` *command-surface* reference survives in either guide, and no
  prose in either guide describes the retired separate scripts as present (no
  present-tense or additive-transition reference). Each guide reads truthfully
  against the single `novel <sub>` surface. Code identifiers that contain a
  legacy substring are preserved.
- Lint/format: `make markdownlint` exits 0 on the two edited guides, which are
  hand-wrapped at 80 columns (`make fmt` is not run — see the Decision Log).
- Mermaid: `make nixie` exits 0 (neither guide contains a Mermaid block;
  verified — `grep -c '```mermaid'` returns 0 for both).
- No incidental breakage: `make all` is green (no Python or test file changed;
  no test reads the guide bodies).

Quality method (how we check):

- The end-state greps in work item 5. The surface grep proves command-surface
  absence by **token-level subtraction** of the enumerated preserve identifiers
  from the *bare* alternation
  `novel-state|novel-done|novel-compile|desloppify|wordcount` (not by a
  space/anchor-narrowed pattern, which produced ~30 false negatives in round
  1); it must print nothing. The **stale-prose CLASS gate** — two structural
  patterns (the digit-word "five" adjacent to a surface noun; the "legacy"
  framing of the retired scripts) plus a residual additive/stub literal term,
  NOT a curated phrase denylist — proves the present-tense / additive framing
  is gone, including the literal-free lines (273 heading, 345 "the legacy
  scripts produce", 356 "the legacy five", 1354 "five-script command surface")
  the round-2 phrase tripwire missed (BR2-1). All three class greps must print
  nothing.
- `make markdownlint`, `make nixie`, and a confirming `make all`.

## Idempotence and recovery

Every step is a Markdown edit; re-running a gate or a grep is safe and
side-effect-free. Each work item is a separate atomic commit, so a failed gate
can be fixed and re-committed (or amended before the commit lands) without
touching the other guide. If a sweep edit is found to have changed a code
identifier (Risk 1), revert that single hunk and re-classify before re-editing
— no global state is involved. Re-running `make markdownlint` is idempotent and
side-effect-free.

## Artefacts and notes

Key transcripts to capture as evidence in `Outcomes & retrospective`:

- The "before" grep counts (the users' guide and developers' guide legacy-hit
  lists from work item 1) and the "after" greps returning empty for
  command-surface references and additive prose.
- The passing `make markdownlint` / `make nixie` / `make all` exit lines.

## Interfaces and dependencies

This task defines no code interfaces. It depends only on:

- The fixed surface vocabulary in
  `novel_ralph_skill.commands.names.SUBCOMMAND_NAMES` (the five spaced names)
  and `project_scripts_table()` (`{"novel": …}`), used as the source of truth
  for every command form written into the guides.
- ADR 007's subcommand structure and design §4's per-operation wording, used as
  the authoritative prose the guides are reconciled against.

No new dependency is introduced; cuprum/Cyclopts/pytest behaviour is not
exercised by this documentation-only sweep.

## Revision note

Round 2 (2026-06-26) — resolved the three blocking defects from the round-1
design review:

- B1: Rewrote the work item 5 surface gate to use the bare alternation
  `novel-state|novel-done|novel-compile|desloppify|wordcount` with the five
  enumerated preserve identifiers subtracted at TOKEN level (`grep -onE …` then
  `grep -vE ':(…)$'`), replacing the round-1 space/anchor-narrowed pattern that
  reported PASS while ~30 genuine references survived. Token-level (not
  line-level) subtraction is mandated because lines 47 and 837 mix a preserve
  identifier with a convert reference. Updated the Risk 1/2 mitigations, the
  quality method, and the Decision Log accordingly.
- B2: Extended work item 4 with a new "change kind 0" covering the
  "Novel-ralph harness architecture" orientation section (line ~256, "The
  deterministic spine is **five console-scripts**"), which sits before the
  named subsection ranges, and added "five console-scripts" to both tripwires
  (work item 1 and work item 5). Marked the named line ranges as illustrative
  anchors, with the work-item-1 bare-grep token list as the authoritative
  worklist.
- B3: Dropped the false "design §4 is already written in the spaced form" claim.
  Context now records the verified count (51 hyphenated vs 9 spaced in §4,
  spaced only in headings), names `names.py` `SUBCOMMAND_NAMES` + ADR 007 as
  the sole surface-vocabulary source, and caveats that §4 supplies
  per-operation behaviour wording only with its command literals re-spaced.
  Updated the four reinforcing spots (Context orientation bullet, the names.py
  source-of-truth paragraph, and the docs-to-read lists of work items 2 and 4).

Also actioned the two advisories: folded the line-839 `stub.py` `novel_done()`
dead-code prose into work item 4's reconcile list, and noted line 837's mixed
preserve+convert content explicitly.

These changes are confined to the plan document; the file-scope, behaviour, and
gate structure are unchanged. No remaining work is affected beyond the sharper
acceptance gate and the wider work-item-4 scope.

Round 3 (2026-06-26) — resolved the round-2 blocking defect BR2-1 (the round-2
B2 fix patched one instance, not the class) and actioned the two round-2
advisories:

- BR2-1: Replaced the curated stale-prose phrase denylist with a two-pattern
  structural CLASS gate (the Wafflecat alternative the round-2 review
  recommended). Work item 5 now runs (1)
  `five[ -]?(separate )?(console-?script|command|name|script)` — catching the
  literal-free lines 256, 273 (`### The five commands` heading), 275, 310, 322,
  337, 489, 492, 1354 and users'-guide 78/104 in one shot — and (2) the
  `legacy`-framing pattern (`legacy[ -](five|scripts?|entry[ -]points?)`, the
  `the legacy scripts produce` literal, and `legacy-(versus|vs)-multiplexer`) —
  catching 345 ("the legacy scripts produce", verbatim a roadmap-forbidden
  example), 356 ("the legacy five"), 358, 360, 368 — plus a residual
  additive/stub literal term. Verified live: the two patterns together catch
  every line BR2-1 enumerated, including the three the round-2 plan left to
  "illustrative" ranges (273, 345, 1354). Added work item 4 change-kind 4,
  which enumerates 273, 277, 310/322, 337/338, 345, 356/358/360/368, 489/492
  and 1354 as REQUIRED reconciles (no longer left to "illustrative" ranges),
  and made the work-item-4 authoritative worklist the union of the
  surface-token list AND the class-gate hit list. Updated Risk 2 (now severity
  high), the Progress and Decision Log entries, the Surprises transcript, work
  item 1's recorded greps, and the Quality method.
- A1 (advisory): work item 4 change-kind 2 now explicitly forbids satisfying
  "describe the dispatcher's actual current shape" by quoting the live
  `novel.py` line-139 docstring (which still says `stub.py`, a fix owned by
  1.2.15.1). The truthful wiring to describe is `make_contract_app("novel")` +
  the five `app.command(<leaf>.build_app(), name=…)` mounts (novel.py 84-89).
- A2 (advisory): corrected the false "line 47 mixes preserve+convert" claim in
  the Decision Log (B1) and the work item 5 narrative; only line 837 does, and
  it alone justifies token-level subtraction. The gate mechanism is unchanged.

These changes are confined to the plan document. The file-scope, behaviour, and
the surface-gate mechanism are unchanged; only the stale-prose gate (now a
class gate) and the work-item-4 enumeration are strengthened. No remaining work
is affected beyond the harder-to-under-fix acceptance gate.
