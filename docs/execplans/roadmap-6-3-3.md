# Document the unified contract and command-invocation discipline in the skill

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT

## Purpose / big picture

After this change, a dogfooding agent reading `skill/novel-ralph/SKILL.md` can
learn the harness's command contract and the discipline for invoking it
**once**, in one authoritative place, without consulting the design document or
the developers' guide and without any per-command prose copy that can drift.
Concretely, three things become true of `SKILL.md`:

1. It states the exit-code table (0 success, 1 benign negative, 2 usage error,
   3 state/input error, 4 actionable finding) and the JSON envelope schema
   (`command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`)
   once, as the single description an agent needs — either inline or behind a
   single pointer at the developers' guide, mirroring how the existing "Done
   predicate (short form)" section points at the developers' guide clause table
   rather than re-listing the clauses.
2. It records the command-invocation discipline a harness-driven agent depends
   on: run every command from the novel root; after each invocation read the
   **process exit code** as the authoritative gating signal, because only the
   exit code carries the load-bearing 1-versus-4 distinction (benign negative,
   loop continues, versus actionable finding, stop-and-fix). The envelope `ok`
   field collapses the five codes to a single success(0)-versus-not-success
   (1/2/3/4) bit — `ok` is `true` if and only if the exit code is 0 — so `ok`
   alone cannot distinguish a benign exit 1 from a stop-and-fix exit 4 and must
   not be used as the sole gate. A non-zero exit is a stop-and-fix **except**
   exit 1 (benign negative), on which the loop continues; the one further
   documented carve-out is that `--help` and `--version` exit 0 with no
   envelope.
3. It records the install-currency note: a `uv tool`-installed `novel` binary
   does not auto-update, so before a dogfood session the agent must reinstall
   with `uv tool install --force …` (or pin a version) to be sure the on-`PATH`
   binary matches the contract this skill documents.

You can observe success by reading the edited `SKILL.md` and by running the two
Markdown gates the roadmap names: `make markdownlint` and `make nixie` both pass
on the edited skill, and `make all` stays green (no Python changed, so the
Python suite is unaffected; the gate proves the edit broke nothing). The
roadmap's success criterion is met when `SKILL.md` documents the exit-code
table, the envelope schema, and the run-from-root / check-exit-code discipline
once, and both Markdown gates pass.

This is roadmap task 6.3.3 (`docs/roadmap.md` lines 2164-2178). It is the
documentation capstone of step 6.3 ("Make the command contract uniform,
actionable, and self-documenting"): tasks 6.3.1 and 6.3.2 made the contract
actionable and pinned its cross-command identity in tests; 6.3.3 makes it
**self-documenting** in the skill the agent actually reads. It implements design
§3 (the shared interface contract) and §8 (the skill defects the rebuild
corrects), and ADR-003 (the shared envelope and disambiguated exit-code table).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively in the git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-3`. Never
  read-modify-write any file in the root/control worktree; it is off-limits for
  edits.
- This is a **documentation-only** task. The files this plan edits are
  `skill/novel-ralph/SKILL.md` (Work items 1-3), a single-line lint precondition
  in `docs/developers-guide.md` (Work item 0 — see below), and, if and only if a
  new internal convention warrants it, a one-paragraph note in
  `docs/developers-guide.md` (Work item 4 is conditional — see its note). Do
  **not** touch any file under `novel_ralph_skill/` (production source) or
  `tests/`. If documenting the contract surfaces a genuine production or test
  defect, stop and escalate; it is a separate roadmap task, not part of
  documenting the contract.
- **Lint-baseline precondition (Work item 0).** `make markdownlint` is RED on
  the worktree baseline *before this task edits anything*: the tree fails with
  `docs/developers-guide.md:149 error MD012/no-multiple-blanks` — two
  consecutive blank lines at lines 148-149, immediately before the heading
  `### The cross-command envelope-and-exit-code identity proof`. This
  double-blank is committed at HEAD (introduced by the 6.3.2 commit; confirmed
  via `git show HEAD:docs/developers-guide.md` and a live `make markdownlint`
  run on 2026-06-26 reporting exactly one error). The only untracked file is
  this execplan. Because every later Work item's validation and the acceptance
  criterion rest on `make markdownlint` passing on `**/*.md`, the gate cannot go
  green until this pre-existing violation is fixed. Work item 0 therefore
  removes exactly **one** of the two consecutive blank lines, leaving a single
  blank line before the heading, as a scoped precondition. The edit is bounded
  to that one blank line in
  `docs/developers-guide.md`; it changes no prose, no heading text, and no other
  line. Do not "fix" any other markdownlint finding under cover of this item —
  the baseline reports exactly one error, and that is the entire scope of Work
  item 0.
- The exit-code table and envelope schema documented in `SKILL.md` must match,
  verbatim in meaning, the authoritative sources and must not introduce a
  fourth, drifting copy:
  - The five-code table fixed by ADR-003 Table 2
    (`docs/adr-003-shared-interface-contract.md` lines 85-95) and design §3.2
    (`docs/novel-ralph-harness-design.md` lines 203-233): 0 success; 1 benign
    negative (predicate not yet satisfied, loop continues); 2 usage error; 3
    state or input error; 4 actionable finding.
  - The six-field envelope fixed by ADR-003 (lines 45-46) and design §3.1
    (lines 137-201): `command`, `schema_version`, `ok`, `working_dir`,
    `result`, `messages`, in that order; `ok` is `true` if and only if the exit
    code is 0; `result` holds machine-actionable data, `messages` holds
    human-only prose the harness never parses.
  - **The gating signal is the exit code, not `ok`.** Verified in source:
    `is_ok` returns `code is ExitCode.SUCCESS`
    (`novel_ralph_skill/contract/exit_codes.py` line 55), and the envelope sets
    `ok=is_ok(code)` (`novel_ralph_skill/contract/envelope.py` line 119). So a
    benign exit 1 emits `ok: false` exactly like exits 2/3/4. The `ok` boolean
    therefore does **not** carry the 1-versus-4 distinction that ADR-003,
    design §3.2 (lines 222-225), and the developers' guide
    ("Disambiguated exit codes", "The 1-versus-4 distinction is load-bearing")
    all call the contract's load-bearing distinction. SKILL.md must document the
    **exit code** as the authoritative signal for the continue-versus-stop-and-
    fix decision; `ok` is only a coarse success(0)-versus-not-success(1/2/3/4)
    bit and must never be presented as a substitute for branching on the code.
    An agent that gated on `ok` alone would read every benign "not yet done"
    (`novel done` exit 1, `ok: false`) as a stop-and-fix and halt the Ralph
    loop every turn — the exact failure the loop exists to avoid.
  - The same contract is already restated for developers in
    `docs/developers-guide.md` "The shared JSON envelope" (lines 522-570) and
    "Disambiguated exit codes" (lines 572-593). To avoid a fourth drifting copy,
    prefer the established single-source discipline: `SKILL.md` documents the
    agent-facing contract concisely and links the developers' guide as the
    canonical reference, exactly as the existing "Done predicate (short form)"
    section (lines 590-600) points at the developers' guide clause table instead
    of re-listing clauses. See the Decision Log for the inline-versus-pointer
    decision.
- The install-currency note must be accurate against the locked tooling. The
  verified `uv` semantics (see Surprises & Discoveries) are: `uv tool install`
  installs the latest at install time but does **not** auto-update an
  already-installed tool; the on-`PATH` executable stays at the installed
  version until the operator acts; `--force` overrides/overwrites the existing
  executable so a reinstall takes effect; a version may be pinned with the
  `package==version` or `package@version` specifier. State the remedy as
  `uv tool install --force --from . novel-ralph-skill` (the local-checkout form
  the Setup section already uses) or a pinned version, and cite the uv tools
  documentation.
- The `--help`/`--version` carve-out is load-bearing and verified in source:
  `novel_ralph_skill/contract/runner.py` lines 16-18 ("`--help`/`--version` are
  handled by Cyclopts … it exits `0` with no envelope") and
  `novel_ralph_skill/commands/novel.py` lines 18-20 ("`--help`/`--version` and a
  bare `novel` return `None`, which `run` treats as the help/version path (exit
  `0`, no envelope)"). The check-exit/check-`ok` discipline must name this carve-
  out so the agent does not parse a non-existent envelope on the help/version
  arms; the discipline applies to body-producing invocations and the
  diagnostic (usage/state) arms.
- All prose uses en-GB Oxford spelling ("-ize"/"-yse"/"-our"), per AGENTS.md and
  the `en-gb-oxendict` skill. External API names (`uv tool`, `--force`,
  Cyclopts, `schema_version`) are quoted verbatim. Follow
  `docs/documentation-style-guide.md`: sentence-case headings, ordered heading
  levels, a language identifier on every fenced block (`plaintext` for text), a
  delimiter line under every table header, blank lines around lists and fences,
  and **a caption on every table** (style guide lines 35-65).
- `SKILL.md` is matched by the `make markdownlint` glob (`**/*.md`,
  `Makefile` line 119) and must pass it. The active rules
  (`.markdownlint-cli2.jsonc`) set MD013 `line_length: 80` with `tables: false`
  and `headings: false`, so **prose must wrap at 80 columns** while table rows
  and headings are exempt; MD004 dash bullets; MD048 backtick fences; MD029
  ordered list style. `make nixie` validates Mermaid; `SKILL.md` adds no Mermaid,
  so nixie is a no-op pass to be confirmed, not a content target.
- `SKILL.md` carries YAML front matter (lines 1-17: `name`, `description`). Do
  not disturb the front matter; the skill loader depends on it. Add the new
  content as ordinary body sections.

## Tolerances (exception triggers)

- Scope: the permitted edit surface is `SKILL.md` plus `docs/developers-guide.md`
  (the single-blank-line lint precondition of Work item 0, and at most the
  conditional one-paragraph note of Work item 4). If delivering the
  documentation requires editing any *other* file, or editing any file under
  `novel_ralph_skill/` or `tests/`, stop and escalate.
- Lint precondition: Work item 0 must change exactly one blank line in
  `docs/developers-guide.md` and nothing else. If, before any edit, a live
  `make markdownlint` reports anything other than the single expected
  `docs/developers-guide.md:149 MD012/no-multiple-blanks` error (for example,
  additional pre-existing violations the implementer did not introduce), stop
  and escalate — the baseline has drifted from what this plan analysed, and the
  acceptance criterion's "fix exactly this pre-existing MD012" assumption no
  longer holds.
- Contract divergence: if the authoritative sources disagree with each other on
  the exit-code table or the envelope schema (so there is no single correct
  thing to document), stop and escalate — a contract that documents itself
  inconsistently is a defect for a separate task.
- Production behaviour: if reading the source to document the `--help`/
  `--version` carve-out or the exit codes reveals that the code does **not**
  behave as design §3 / ADR-003 states, stop and escalate; do not "document
  around" a real divergence.
- Install semantics: if the verified `uv tool` behaviour contradicts the
  roadmap's stated remedy (reinstall with `--force`, or pin a version) such that
  the note cannot be written truthfully, stop and present the corrected remedy
  before writing it.
- Iterations: if `make markdownlint` or `make nixie` still fails after 4 focused
  attempts to satisfy the rule it reports (line length, table delimiter,
  caption, fence language) on the content **this task adds or edits**, stop and
  escalate. This trigger does *not* apply to the pre-existing
  `docs/developers-guide.md:149 MD012` baseline failure, which Work item 0
  removes deterministically in a single edit; if that one edit does not clear
  the MD012, the baseline differs from this plan's analysis — escalate per the
  Lint-precondition tolerance above rather than iterating.
- Ambiguity: if the inline-versus-pointer choice for the contract description
  materially changes the skill's structure and both readings of the roadmap are
  defensible, present the two options with trade-offs rather than guessing.

## Risks

    - Risk: A fourth copy of the exit-code table / envelope schema is introduced
      in SKILL.md and immediately begins to drift from ADR-003, design §3, and
      the developers' guide — the very per-command/per-document drift task 6.3
      exists to close.
      Severity: high
      Likelihood: medium
      Mitigation: Apply the established single-source discipline. SKILL.md gives
      the agent the concise operational table and schema it needs to gate, and
      names the developers' guide ("The shared JSON envelope", "Disambiguated
      exit codes") and ADR-003 as the canonical sources, exactly as the existing
      "Done predicate (short form)" section points at the developers' guide
      clause table. If an inline table is included for agent convenience, mark it
      explicitly as a convenience restatement of the cited canonical source so a
      future editor knows where the source of truth lives. Decision recorded in
      the Decision Log.

    - Risk: The check-exit/check-ok discipline is written as an absolute ("every
      invocation emits the six-field envelope; always parse ok"), which is false
      for the --help/--version arms (exit 0, no envelope), so an agent following
      it would try to parse a non-existent envelope and mis-handle help/version.
      Severity: medium
      Likelihood: medium
      Mitigation: State the carve-out explicitly and cite it: the discipline
      applies to body-producing invocations and the diagnostic (usage/state)
      arms; --help/--version exit 0 with no envelope by design
      (novel_ralph_skill/contract/runner.py lines 16-18;
      novel_ralph_skill/commands/novel.py lines 18-20). This is the same carve-
      out the 6.3.2 cross-command suite scopes around (developers' guide
      "The cross-command envelope-and-exit-code identity proof").

    - Risk: SKILL.md tells the agent it "may gate on either" the exit code or
      the envelope `ok`, treating them as interchangeable. They are NOT
      interchangeable for the load-bearing 1-versus-4 decision: `ok` is `true`
      iff the exit code is 0 (is_ok returns `code is ExitCode.SUCCESS`,
      exit_codes.py line 55; envelope.py line 119 sets `ok=is_ok(code)`), so a
      benign exit 1 emits `ok: false` exactly like exits 2/3/4. An agent gating
      on `ok` alone would read every benign "not yet done" (`novel done` exit 1)
      as a stop-and-fix and halt the Ralph loop on every turn — the precise
      failure the loop is built to avoid.
      Severity: high
      Likelihood: high (if "gate on either" survives into SKILL.md)
      Mitigation: SKILL.md must state that the **exit code is the authoritative
      gating signal** for the continue-versus-stop-and-fix (1-versus-4)
      decision; `ok` collapses only to success(0)-versus-not-success(1/2/3/4)
      and must never be presented as a substitute for branching on the code.
      Remove any "may gate on either" wording. Verified against source and
      against the developers' guide "Disambiguated exit codes" ("The 1-versus-4
      distinction is load-bearing"). See Work item 2 and the Decision Log.

    - Risk: `make markdownlint` is RED on the worktree baseline before this task
      edits anything (`docs/developers-guide.md:149 MD012/no-multiple-blanks`,
      committed at HEAD by the 6.3.2 commit), so every later Work item's
      validation and the acceptance criterion — both of which rest on
      markdownlint passing on `**/*.md` — cannot go green, and the Tolerances
      iteration trigger could fire on a violation the implementer did not cause.
      Severity: high
      Likelihood: high (it is the live baseline, confirmed 2026-06-26)
      Mitigation: Work item 0 removes the spurious blank line (one of the two
      consecutive blanks before the `### The cross-command...` heading) as a
      scoped precondition before any other edit, and the acceptance criterion is
      restated as "make markdownlint passes on the whole tree, including this
      pre-existing fix". The Tolerances iteration trigger is scoped to exclude
      this baseline failure. If a live markdownlint reports anything other than
      this single expected error, escalate (Lint-precondition tolerance).

    - Risk: The install-currency note states an inaccurate uv remedy (for
      example, claiming a plain re-run of `uv tool install` upgrades an already-
      installed tool, which it does not), sending a dogfooding agent into a
      session against a stale binary.
      Severity: medium
      Likelihood: low
      Mitigation: Pin the note to the verified uv semantics and cite the uv
      tools documentation (https://docs.astral.sh/uv/concepts/tools/, sections
      "Tool versions" and "Upgrading tools", and "Overwriting executables" for
      --force). The remedy is `uv tool install --force …` or a pinned version;
      `uv tool upgrade` is the constraint-respecting alternative. Evidence in
      Surprises & Discoveries.

    - Risk: Prose exceeds the 80-column MD013 limit (tables and headings are
      exempt, but body paragraphs are not), or a new table lacks the style
      guide's required caption or a delimiter row, failing the gate late.
      Severity: low
      Likelihood: medium
      Mitigation: Wrap prose at 80 columns as the rest of SKILL.md does; caption
      every table; include the header delimiter row; give every fence a language
      identifier. Run `make markdownlint` before committing (Work items 1-3) and
      `make nixie` once Markdown is touched.

    - Risk: An unrelated `mdformat`/`make fmt` reflow rewrites large parts of the
      tracked docs tree and gets swept into the documentation commit (a known
      recurring churn noted in the 6.3.2 retrospective).
      Severity: low
      Likelihood: medium
      Mitigation: Before committing, diff the working tree and stage only the
      intended SKILL.md (and, if applicable, developers-guide.md) hunks; if
      spurious reflow churn appears in other docs, restore those files to HEAD
      and re-apply only the intended edits, as the 6.3.2 Work item 6 commit did.

## Progress

    - [x] Work item 0 (precondition): Remove the pre-existing
      `docs/developers-guide.md:149 MD012/no-multiple-blanks` baseline failure
      by deleting one of the two consecutive blank lines before the
      `### The cross-command envelope-and-exit-code identity proof` heading, so
      `make markdownlint` can go green. Validation: `make markdownlint` (now
      passes on `**/*.md`), `make nixie`, `make all`. DONE 2026-06-26: live
      baseline confirmed exactly one MD012 error at developers-guide:149;
      removed one of the two blank lines; `make markdownlint` now reports
      0 errors over 278 files, `make nixie` and `make all` green
      (1301 passed, 1 skipped).
    - [x] Work item 1: Add the unified contract section to SKILL.md (exit-code
      table + envelope schema, single-sourced against ADR-003 / design §3 /
      developers' guide). Validation: `make markdownlint`, `make nixie`,
      `make all`. DONE 2026-06-26: added a "Command contract" section after
      "Harness contract" with the five-code table (captioned, restated from
      ADR-003 Table 2), the six-field envelope JSON skeleton with one sentence
      per field, the `ok`-iff-exit-0 framing pointing at the discipline
      section, and a single canonical pointer at ADR-003 and the developers'
      guide. Caption emphasis uses asterisk to match SKILL.md's prevailing
      emphasis style (MD049 infers the document style from the first marker);
      table columns widened to satisfy MD060. All gates green.
    - [x] Work item 2: Add the command-invocation discipline (run-from-root;
      the **exit code** is the authoritative gating signal because only it
      carries the 1-versus-4 distinction; `ok` is only success(0)-vs-not(1/2/3/4)
      and must not be the sole gate; exit 1 continues, 2/3/4 stop-and-fix; the
      --help/--version exit-0-no-envelope carve-out). Validation:
      `make markdownlint`, `make nixie`, `make all`. DONE 2026-06-26: added an
      "Invocation discipline" subsection to the Command contract section,
      framed as the complement to the "Harness contract" four requirements,
      with the four numbered rules (run-from-root; gate on the exit code, not
      `ok` alone; branch per the table with exit 1 continuing and 2/3/4
      stop-and-fix; the help/version exit-0-no-envelope carve-out). No "gate on
      either" wording. All gates green.
    - [x] Work item 3: Add the install-currency note (uv tool does not auto-
      update; reinstall with --force or pin a version before a dogfood session),
      pinned to verified uv semantics. Validation: `make markdownlint`,
      `make nixie`, `make all`. DONE 2026-06-26: augmented the Setup section
      with the note and a fenced `bash` block showing `uv tool install --force
      --from . novel-ralph-skill`, the `==<version>` pin, and the
      `uv tool upgrade` constraint-respecting alternative; cited the uv tools
      docs (Tool versions / Upgrading tools / Overwriting executables); tied
      `novel --version`'s exit-0-no-envelope back to the help/version carve-out.
      All gates green.
    - [x] Work item 4 (conditional): SKIPPED 2026-06-26. The contract section
      introduces no *new* cross-document convention: the single-source pointer
      pattern it follows already exists (the "Done predicate (short form)"
      pointer at the developers' guide clause table). No new developers'-guide
      note is warranted; recorded in the Decision Log.

## Surprises & discoveries

    - Observation: The `uv tool`-installed executable does not auto-update, and
      a plain `uv tool install` re-run is not the documented upgrade path; the
      verified remedies are `uv tool upgrade` (respects original constraints),
      reinstall via `uv tool install` (replaces constraints / re-creates the
      env), and `--force` to overwrite an existing executable.
      Evidence: uv official docs, https://docs.astral.sh/uv/concepts/tools/,
      scraped 2026-06-26. "Tool versions": "Unless a specific version is
      requested, `uv tool install` will install the latest available … Once a
      tool is installed with `uv tool install`, `uvx` will use the installed
      version by default." "Upgrading tools": "Tool environments may be upgraded
      via `uv tool upgrade`, or re-created entirely via subsequent `uv tool
      install` operations." "Overwriting executables": "Installation of tools
      will not overwrite executables … The `--force` flag can be used to override
      this behavior."
      Impact: Work item 3's note is written as: the installed `novel` binary does
      not auto-update, so before a dogfood session reinstall with `uv tool
      install --force --from . novel-ralph-skill` (or pin a version with a
      `==version`/`@version` specifier) to guarantee the on-`PATH` binary matches
      the documented contract. Cites the uv docs above.

    - Observation: `--help`/`--version` (and a bare `novel`) exit 0 with **no**
      JSON envelope; only body-producing invocations and the usage/state
      diagnostic arms emit the six-field envelope.
      Evidence: `novel_ralph_skill/contract/runner.py` lines 16-18 and 242
      ("A --help/--version invocation: under exit_on_error=False Cyclopts …");
      `novel_ralph_skill/commands/novel.py` lines 18-20 ("`--help`/`--version`
      and a bare `novel` return `None`, which `run` treats as the help/version
      path (exit `0`, no envelope)").
      Impact: Work item 2's discipline names this carve-out so the agent does not
      parse a non-existent envelope on help/version.

    - Observation: `make markdownlint` is RED on the worktree baseline before
      this task edits anything: it reports exactly one error,
      `docs/developers-guide.md:149 error MD012/no-multiple-blanks Multiple
      consecutive blank lines [Expected: 1; Actual: 2]`. The two consecutive
      blank lines sit at developers-guide lines 148-149, immediately before the
      heading `### The cross-command envelope-and-exit-code identity proof`, and
      are committed at HEAD (introduced by the 6.3.2 commit). The only untracked
      file is this execplan.
      Evidence: live `make markdownlint` run on 2026-06-26 (output
      "Summary: 1 error(s)" naming developers-guide:149) and
      `git show HEAD:docs/developers-guide.md | sed -n '144,152p'` showing two
      blank lines before the heading.
      Impact: Adds Work item 0 (a one-line lint precondition) ahead of the
      content items, scoped in Constraints and Tolerances, and restates the
      acceptance criterion as "make markdownlint passes on the whole tree,
      including this pre-existing fix". Without this, the markdownlint-based
      validation is not executable.

    - Observation: `ok` is `true` if and only if the exit code is 0; it does NOT
      distinguish a benign exit 1 from a stop-and-fix exit 4. `is_ok` returns
      `code is ExitCode.SUCCESS`, and the envelope sets `ok=is_ok(code)`, so
      exit 1 (benign negative) emits `ok: false` exactly like exits 2/3/4. The
      load-bearing 1-versus-4 distinction (developers' guide "Disambiguated exit
      codes": "The 1-versus-4 distinction is load-bearing") is carried by the
      exit code alone.
      Evidence: `novel_ralph_skill/contract/exit_codes.py` line 55
      (`return code is ExitCode.SUCCESS`); `novel_ralph_skill/contract/
      envelope.py` line 119 (`ok=is_ok(code)`); developers' guide "Disambiguated
      exit codes" section. Verified by source read 2026-06-26.
      Impact: Work item 2 documents the **exit code** as the authoritative
      gating signal and frames `ok` only as the coarse success(0)-vs-not-success
      bit; the round-1 "the agent may gate on either" wording is removed as
      false for the benign-negative case.

    - Observation: SKILL.md currently documents none of the exit-code table, the
      envelope schema, the run-from-root/check-exit discipline, or the install-
      currency note, so this task is purely additive prose; no existing
      contradictory prose must be reconciled.
      Evidence: `grep -in "exit code|envelope|schema_version|run from|check the
      exit|stop and fix"` over `skill/novel-ralph/SKILL.md` returns nothing.
      Impact: The work items add new sections rather than rewriting existing
      ones, lowering the drift and merge-conflict risk.

    - Observation: The developers' guide already restates the contract for
      developers in "The shared JSON envelope" (lines 522-570) and "Disambiguated
      exit codes" (lines 572-593), and SKILL.md already single-sources the *done
      predicate* by pointing at the developers' guide clause table rather than
      re-listing clauses (lines 590-600).
      Evidence: Read of `docs/developers-guide.md` and `skill/novel-ralph/
      SKILL.md`.
      Impact: This is the precedent Work item 1 follows for the contract
      description, keeping a single source of truth and avoiding a fourth copy.

## Decision log

    - Decision: Scope task 6.3.3 as documentation-only, editing
      `skill/novel-ralph/SKILL.md` (and at most a one-paragraph developers'-guide
      note), and adding no tests or production changes.
      Rationale: The roadmap success criterion is "`SKILL.md` documents the exit-
      code table, the envelope schema, and the run-from-root / check-exit-code
      discipline once; `make markdownlint` and `make nixie` pass on the edited
      skill" (roadmap lines 2176-2178). The contract itself is already built and
      pinned by tasks 1.3.1, 6.3.1, and 6.3.2; 6.3.3 only documents it. AGENTS.md
      "Quality gates" require tests for behaviour changes, but there is no
      behaviour change here — the gate is the Markdown lint/validation pass over
      a prose edit.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Add Work item 0, a scoped one-line lint precondition, to remove
      the pre-existing `docs/developers-guide.md:149 MD012/no-multiple-blanks`
      baseline failure before any content edit, and restate the acceptance
      criterion as "make markdownlint passes on the whole tree, including this
      pre-existing fix".
      Rationale: `make markdownlint` is RED on the baseline (confirmed
      2026-06-26), so every Work item's validation and the acceptance criterion
      — both of which require markdownlint to pass on `**/*.md` — are not
      executable until the spurious blank line is removed. The defect sits in the
      exact developers-guide region (148-190) SKILL.md points at and that Work
      item 4 may edit, so fixing it here is in-scope and low-risk. Scope is
      bounded to one blank line; the Tolerances iteration trigger is amended to
      exclude this pre-existing failure; if the baseline shows any other
      markdownlint error, the implementer escalates rather than expanding scope.
      Resolves design-review round-1 blocking point 1.
      Date/Author: 2026-06-26, planning agent (round 2).

    - Decision: The **exit code** is the authoritative gating signal SKILL.md
      documents for the continue-versus-stop-and-fix (1-versus-4) decision;
      `ok` is documented only as the coarse success(0)-versus-not-success
      (1/2/3/4) bit, and the round-1 "the agent may gate on either" wording is
      removed.
      Rationale: Verified against source — `is_ok` returns `code is
      ExitCode.SUCCESS` (exit_codes.py line 55) and the envelope sets
      `ok=is_ok(code)` (envelope.py line 119) — so a benign exit 1 emits
      `ok: false` exactly like exits 2/3/4. `ok` therefore cannot carry the
      load-bearing 1-versus-4 distinction (ADR-003, design §3.2, developers'
      guide "Disambiguated exit codes"). An agent gating on `ok` alone would
      halt the Ralph loop on every benign "not yet done" turn — the failure the
      loop exists to avoid. "May gate on either" is false for the benign-negative
      case and must not appear in the very contract SKILL.md documents. Resolves
      design-review round-1 blocking point 2.
      Date/Author: 2026-06-26, planning agent (round 2).

    - Decision (to confirm during implementation): Document the contract in
      SKILL.md with a concise agent-facing exit-code table and envelope schema,
      each marked as a convenience restatement of the canonical source, with a
      single pointer at the developers' guide ("The shared JSON envelope",
      "Disambiguated exit codes") and ADR-003 as the source of truth — mirroring
      the existing "Done predicate (short form)" pointer pattern.
      Rationale: The roadmap text offers the explicit choice "to `SKILL.md` (or a
      reference it links once)" and the governing intent is "so no per-command
      prose copy can drift". A concise table plus a single canonical pointer
      gives the dogfooding agent what it needs to gate at the point of use while
      keeping one source of truth, satisfying both halves of the requirement.
      Alternative considered: a pure pointer with no inline table; rejected as a
      weaker fit for "self-documenting in the skill the agent reads" because the
      agent would have to leave SKILL.md to learn how to gate. The implementer
      may adopt the pure-pointer form only if the inline table cannot be written
      without drifting from the canonical source; record the final choice here.
      Date/Author: 2026-06-26, planning agent.

    - Decision (confirmed during implementation): Adopted the concise inline
      restatement plus a single canonical pointer (not the pure-pointer
      fallback). The inline exit-code table and envelope skeleton were written
      without drifting from ADR-003 Table 2 and design §3.1, so the
      stronger-fit inline form stands, each marked a convenience restatement
      with a single pointer at ADR-003 and the developers' guide.
      Date/Author: 2026-06-26, implementation agent.

    - Decision: Skip Work item 4 (conditional developers'-guide note). The
      contract section introduces no *new* cross-document convention worth
      recording: the single-source pointer pattern it follows already exists
      and is documented (the "Done predicate (short form)" pointer at the
      developers' guide clause table). Adding a note would restate an existing
      convention, so the item is skipped per its own conditional.
      Date/Author: 2026-06-26, implementation agent.

    - Decision: Apply coderabbit's still-valid factual findings against the
      execplan (the 278-file Markdown count and the line-number ambiguity in
      the Work item 0 description) and defer the remaining execplan-only
      stylistic findings (second-person voice in the Purpose narrative; 4-space
      list indentation in the Risks/Progress/Surprises/Decision-log sections;
      prose wrap in the Purpose and the untracked logisphere review note).
      Rationale: the SKILL.md and developers-guide deliverables drew zero
      coderabbit findings across all runs. The deferred items concern
      planning-artefact prose authored by the planning agent; the execplan
      passes `make markdownlint` (the 4-space indentation and long Purpose
      lines do not trip the active rules), and wholesale reformatting the
      structured planning sections is outside this implementation task's scope
      and risks corrupting them. The logisphere review note is not a deliverable
      of this task.
      Date/Author: 2026-06-26, implementation agent.

## Outcomes & retrospective

Delivered 2026-06-26. Against the Purpose: the
`docs/developers-guide.md:149 MD012` baseline failure is cleared (Work item 0);
`skill/novel-ralph/SKILL.md` now documents, once, the exit-code table and the
six-field envelope schema (Work item 1, a captioned table plus a JSON skeleton,
marked a convenience restatement with a single canonical pointer at ADR-003 and
the developers' guide), the run-from-root / check-exit-code discipline with the
**exit code** as the authoritative gating signal and `ok` framed only as
success(0)-versus-not-success (Work item 2, "Invocation discipline"), the
help/version exit-0-no-envelope carve-out, and the install-currency note pinned
to the verified `uv tool` semantics (Work item 3). No drifting fourth copy was
introduced. Work item 4 was skipped as no new cross-document convention arose.
`make markdownlint` passes on the whole tree (278 files, 0 errors, including the
Work item 0 fix), `make nixie` passes (no Mermaid added), and `make all` stays
green (1301 passed, 1 skipped; the Python suite is unaffected by the prose-only
change). coderabbit returned zero findings on the SKILL.md and developers-guide
deliverables; its execplan-only findings were triaged in the Decision Log.

## Context and orientation

The harness is a Python package, `novel_ralph_skill`, that ships a single
`novel` console-script multiplexer (ADR-007). Each body-producing invocation
emits one JSON "envelope" on stdout (or a human rendering under `--human`) and
exits with a contract exit code. The skill that an agent loads to drive this
harness is `skill/novel-ralph/SKILL.md`. This task adds the contract and the
invocation discipline to that skill.

Read the following before editing; they are the source of truth this task
documents and must not contradict.

- `docs/roadmap.md` lines 2116-2178 — step 6.3 and tasks 6.3.1-6.3.3. Task
  6.3.3 (lines 2164-2178) is this plan; its predecessors 6.3.1 (actionable exit-
  3 messages) and 6.3.2 (cross-command contract suite) are complete.
- `docs/adr-003-shared-interface-contract.md` — the shared envelope (lines
  45-46), the disambiguated five-code exit table (Table 2, lines 85-95), and the
  four-flag Cyclopts construction contract (Table 3). This is the contract this
  task documents.
- `docs/novel-ralph-harness-design.md` §3 (lines 131-264) — the same contract in
  narrative form: §3.1 the envelope and output modes (lines 137-201), §3.2 the
  exit codes (lines 203-233), §3.3 command/query segregation (lines 235-243),
  §3.4 atomic writes (lines 245-264). §8 (lines 816-836) — the skill defects the
  rebuild corrects, including the single-source done-predicate discipline this
  task extends to the contract.
- `docs/developers-guide.md` "The shared JSON envelope" (lines 522-570) and
  "Disambiguated exit codes" (lines 572-593) — the developer-facing restatement
  of the contract and the canonical reference SKILL.md will point at. "The
  cross-command envelope-and-exit-code identity proof" (lines 150-190) — the
  6.3.2 suite that pins exactly the identity SKILL.md now describes in prose,
  including the help/version carve-out the discipline must name.
- `docs/documentation-style-guide.md` — sentence-case headings, ordered heading
  levels, fenced-block language identifiers, table delimiter rows, caption every
  table (lines 35-65), the en-GB Oxford spelling rules.
- `AGENTS.md` — the quality gates and the Markdown rules: `make markdownlint`
  (lines 96-98, 169), `make nixie` (line 172), and the Documentation-maintenance
  rule that user-facing and skill prose stay current (lines 37-57).

Key source files (read-only for this task; cited so the documented carve-out and
exit codes are pinned to real behaviour, not memory):

- `novel_ralph_skill/contract/runner.py` lines 16-18, 242 — `run` owns every
  `sys.exit` and envelope emission; `--help`/`--version` exit 0 with no envelope.
- `novel_ralph_skill/commands/novel.py` lines 18-20 — the multiplexer's
  help/version/bare-`novel` arm returns `None` (exit 0, no envelope).
- `novel_ralph_skill/contract/exit_codes.py` line 55 — `is_ok` returns
  `code is ExitCode.SUCCESS`; the source proof that `ok` is `true` iff the exit
  code is 0, so `ok` does **not** carry the load-bearing 1-versus-4 distinction.
- `novel_ralph_skill/contract/envelope.py` line 119 — the envelope sets
  `ok=is_ok(code)`, binding the envelope `ok` field to the exit-0 condition.

Key file to edit:

- `skill/novel-ralph/SKILL.md` — the skill. Existing sections relevant here:
  "Setup" (lines 26-46, the `uv tool install` instructions Work item 3 augments),
  "Harness contract" (lines 48-65, the four turn requirements the invocation
  discipline complements), and "Done predicate (short form)" (lines 590-600, the
  single-source pointer pattern Work item 1 mirrors). The YAML front matter
  (lines 1-17) must not be disturbed.

Terms (defined here so the skill's new prose can use them precisely):

- "Envelope" — the six-field JSON object every body-producing command emits:
  `{command, schema_version, ok, working_dir, result, messages}` (design §3.1).
- "Exit code" — the process exit status the harness branches on without parsing
  JSON; the five-code table (design §3.2, ADR-003 Table 2).
- "Body-producing invocation" — a command run that executes its body and emits
  an envelope, as distinct from the `--help`/`--version` arm, which exits 0 with
  no envelope.
- "Stop-and-fix" — the agent's required response to exit code 2, 3, or 4: halt
  the loop, adjudicate or repair, and re-run, never treat it as success. The
  agent decides this on the **exit code**, not on `ok`: exits 1, 2, 3, and 4 all
  carry `ok: false` (because `ok` is `true` iff the exit code is 0), so `ok`
  cannot distinguish the benign exit 1 — on which the loop **continues** without
  a fix — from a stop-and-fix exit 2/3/4. The help/version arm (exit 0, no
  envelope) is the further carve-out.
- "Install currency" — the property that the on-`PATH` `novel` binary matches the
  contract version this skill documents; not guaranteed automatically because
  `uv tool` does not auto-update an installed tool.

## Plan of work

The work proceeds in a one-line lint precondition (Work item 0) followed by
three small, independently committable documentation items (Work item 4 is
conditional). Work item 0 and Work item 4 edit `docs/developers-guide.md`; Work
items 1-3 edit `skill/novel-ralph/SKILL.md` only. Each ends with the Markdown
gates plus `make all`. The items are ordered so the lint baseline is green
first, then the contract section (the reference the discipline leans on), then
the discipline.

Because there is no failing test to establish (no behaviour changes), the red/
green discipline here is: before each commit, confirm the new prose is present
and correct by re-reading the edited section, then prove the gates pass. The
"teeth" of this task are the Markdown gates and the human-readable correctness
of the contract against its cited sources — verify every documented code,
field, and remedy against the cited line ranges, not from memory.

### Work item 0 (precondition): Clear the markdownlint baseline failure

Implements the AGENTS.md `make markdownlint` quality gate (lines 96-98, 169) as
a precondition for every later Work item. `make markdownlint` is RED on the
worktree baseline before this task edits anything; a live run on 2026-06-26
reports exactly one error:

    docs/developers-guide.md:149 error MD012/no-multiple-blanks Multiple
    consecutive blank lines [Expected: 1; Actual: 2]

The two consecutive blank lines are at `docs/developers-guide.md` lines 148-149,
immediately before the heading `### The cross-command envelope-and-exit-code
identity proof`, and are committed at HEAD (introduced by the 6.3.2 commit;
confirmed with `git show HEAD:docs/developers-guide.md`). Remove **one** of the
two blanks so a single blank line separates the preceding paragraph from the
heading, satisfying MD012. Change nothing else: no prose, no heading text, no
other line.

Before editing, run `make markdownlint` and confirm it reports *only* the single
`docs/developers-guide.md:149 MD012` error. If it reports anything else, the
baseline has drifted from this plan's analysis — stop and escalate
(Lint-precondition tolerance). After the one-line edit, `make markdownlint` must
pass on `**/*.md`.

Docs to read for this item: AGENTS.md "Quality gates" (the `make markdownlint`
rule); `.markdownlint-cli2.jsonc` (the active rules, to confirm MD012 is the
default and is not relaxed). Skills to load: none beyond a careful read; this is
a whitespace deletion, not a prose change.

Tests added: none (whitespace-only lint fix; no behaviour change). Validation:
`make markdownlint` (now green), `make nixie`, `make all`. Commit this item
first and separately so the green baseline is captured before any content edit.

### Work item 1: Unified contract section in SKILL.md

Implements ADR-003 (envelope and Table 2), design §3.1-§3.2, and §8 (single-
source discipline). Add a new top-level section to `skill/novel-ralph/SKILL.md`
— place it after "Harness contract" (the natural home for the contract an agent
gates on) — titled, in sentence case, e.g. "Command contract". The section
documents two things once:

1. The exit-code table: 0 success (proceed); 1 benign negative — predicate not
   yet satisfied, loop continues without a fix; 2 usage error — the invocation
   is wrong, stop; 3 state or input error — recover state, stop; 4 actionable
   finding — a deterministic detector surfaced something only the model can
   resolve, adjudicate or repair then re-run. Render it as a Markdown table with
   a header delimiter row and a caption (style guide lines 51, 65). State the
   load-bearing 1-versus-4 distinction in one sentence, matching design §3.2
   lines 222-225 and developers' guide lines 585-588.
2. The envelope schema: the six fields `command`, `schema_version`, `ok`,
   `working_dir`, `result`, `messages`, in that order; `ok` is `true` if and
   only if the exit code is 0; `result` carries machine-actionable data the
   harness reads; `messages` carries human-only prose the harness never parses.
   A short fenced `json` block showing the skeleton (mirroring design §3.1 lines
   146-155) plus one sentence per field is sufficient. State, alongside `ok`,
   that because `ok` is `true` iff the exit code is 0, `ok` only reports
   success(0)-versus-not-success(1/2/3/4) and the **exit code** remains the
   signal that carries the 1-versus-4 distinction — so the gating discipline
   (Work item 2) branches on the exit code, not on `ok`. This keeps the contract
   section and the discipline section internally consistent.

Mark both the table and the schema explicitly as the agent-facing restatement of
the canonical sources, and add a single pointer: "The canonical contract is
`docs/adr-003-shared-interface-contract.md` and the developers' guide sections
'The shared JSON envelope' and 'Disambiguated exit codes'; this skill restates
it for the agent at the point of use." This mirrors the existing "Done predicate
(short form)" pointer (SKILL.md lines 590-600) and is the §8 single-source
discipline applied to the contract, so no per-command prose copy can drift.

Do not restate the four-flag Cyclopts construction contract (ADR-003 Table 3) or
the command/query segregation table — those are developer-internal, not the
agent-facing gating contract; a pointer at ADR-003 covers them.

Docs to read for this item: ADR-003 (Decision outcome, Table 2; envelope fields);
design §3.1, §3.2, §8; developers' guide "The shared JSON envelope" and
"Disambiguated exit codes"; `docs/documentation-style-guide.md` (headings,
tables, captions, fences). Skills to load: `en-gb-oxendict` for the prose
(Oxford spelling, sentence-case headings).

Tests added: none (documentation-only; no behaviour change — AGENTS.md "Quality
gates" require tests for behaviour changes, of which there are none). Validation:
`make markdownlint` and `make nixie` (Markdown changed), then `make all` to prove
the edit broke nothing.

### Work item 2: Command-invocation discipline in SKILL.md

Implements design §3 (the contract the harness gates on) and the roadmap's
explicit invocation-discipline requirement (lines 2168-2172). Add the discipline
to `skill/novel-ralph/SKILL.md`, either as a subsection of the Work item 1
"Command contract" section or as a short adjacent section (e.g. "Invocation
discipline"). It states, in plain prose:

1. Run every command from the novel root — the directory whose `working/`
   subtree holds the state — because the commands resolve `working/` relative to
   the current directory (SKILL.md "Setup" already says "run them from the
   novel's root"; this section makes the *why* — wrong-directory invocation is
   the dogfooding failure 6.3 was surfaced by, roadmap lines 2122-2125).
2. After each invocation, gate on the **process exit code** — it is the
   authoritative signal. The exit code is the only signal that carries the
   load-bearing 1-versus-4 distinction (benign negative versus actionable
   finding). The envelope `ok` field is `true` if and only if the exit code is
   0 (verified: `is_ok` returns `code is ExitCode.SUCCESS`,
   `novel_ralph_skill/contract/exit_codes.py` line 55; the envelope sets
   `ok=is_ok(code)`, `envelope.py` line 119), so `ok` collapses the five codes
   to a single success(0)-versus-not-success(1/2/3/4) bit. `ok` is a useful
   sanity cross-check that the envelope agrees with the exit status, but it must
   **not** be used as the sole gate: it cannot tell a benign exit 1 apart from a
   stop-and-fix exit 4. Do **not** write "gate on either"; the agent must branch
   on the exit code.
3. Branch on the exit code per the Work item 1 table: exit 0 is success
   (proceed); exit 1 is the benign negative on which the loop **continues**
   without a fix (e.g. `novel done` reporting "not finished yet", which emits
   `ok: false`); exits 2, 3, and 4 are stop-and-fix — halt, adjudicate or repair
   per the table, and re-run; never assume success. Make explicit that exit 1
   and exits 2/3/4 all share `ok: false`, which is precisely why gating on `ok`
   alone would halt the loop on every benign turn — the failure the Ralph loop
   exists to avoid. Tie this back to the Work item 1 table so the agent reads
   one contract, not two.
4. The carve-out: `--help` and `--version` (and a bare `novel`) exit 0 with **no
   envelope**, so the "parse the envelope `ok`" step applies to body-producing
   invocations and the usage/state diagnostic arms, not to the help/version arm.
   Cite that this is by design (runner and multiplexer behaviour). This prevents
   an agent from trying to parse a non-existent envelope on help/version.

Frame this as the complement to the existing "Harness contract" four
requirements (SKILL.md lines 48-65): those govern how the agent *persists* work
across turns; this governs how the agent *reads the result* of each command it
runs.

Docs to read: design §3.2 (the harness-response column); developers' guide
"Disambiguated exit codes" ("The 1-versus-4 distinction is load-bearing");
roadmap lines 2122-2125 and 2168-2172 (the dogfooding origin and the discipline
text); `novel_ralph_skill/contract/exit_codes.py` line 55
(`is_ok` returns `code is ExitCode.SUCCESS`) and
`novel_ralph_skill/contract/envelope.py` line 119 (`ok=is_ok(code)`) — the
source proof that `ok` is `true` iff exit 0 and so does not carry the 1-versus-4
distinction; `novel_ralph_skill/contract/runner.py` lines 16-18 and
`novel_ralph_skill/commands/novel.py` lines 18-20 (the help/version carve-out);
developers' guide "The cross-command envelope-and-exit-code identity proof"
(the suite that pins this contract). Skills to load: `en-gb-oxendict`.

Tests added: none (documentation-only). Validation: `make markdownlint`,
`make nixie`, `make all`.

### Work item 3: Install-currency note in SKILL.md

Implements the roadmap's install-currency requirement (lines 2172-2174) and
design §8 (skill-currency discipline). Augment the existing "Setup" section of
`skill/novel-ralph/SKILL.md` (lines 26-46) with a short note: the `uv tool`-
installed `novel` binary does **not** auto-update, so the on-`PATH` binary can
lag the contract this skill documents. Before a dogfood session, guarantee
currency by reinstalling with `uv tool install --force --from . novel-ralph-skill`
(the local-checkout form Setup already uses, with `--force` to overwrite the
existing executable) or by pinning a version (`novel-ralph-skill==<version>` or
the `@<version>` specifier). Optionally mention `uv tool upgrade novel-ralph-skill`
as the constraint-respecting alternative. Confirm the install resolves with
`novel --version` (already shown in Setup) — and note that `novel --version`
itself exits 0 with no envelope, consistent with the Work item 2 carve-out.

Pin every claim to the verified uv semantics (Surprises & Discoveries) and cite
the uv tools documentation (<https://docs.astral.sh/uv/concepts/tools/>,
sections "Tool versions", "Upgrading tools", "Overwriting executables"). Do not
claim a plain `uv tool install` re-run upgrades an already-installed tool — it
does not; `--force` (overwrite) or `uv tool upgrade` (within constraints) is
required.

Docs to read: roadmap lines 2172-2174; the uv tools docs above; SKILL.md "Setup"
(lines 26-46). Skills to load: `en-gb-oxendict`.

Tests added: none. Validation: `make markdownlint`, `make nixie`, `make all`.

### Work item 4 (conditional): Developers'-guide cross-reference note

Implements the AGENTS.md "Documentation maintenance" rule (record internal
conventions in the developers' guide, lines 53-55). This item is **conditional**:
only undertake it if Work item 1 establishes a *new* cross-document convention
worth recording for developers — for example, a note that SKILL.md now single-
sources the contract from the developers' guide, so future contract edits must
update the developers' guide (the canonical copy) and not SKILL.md's
restatement. If no such new convention arises (the more likely case, since the
done-predicate pointer pattern already exists), **skip this item** and record the
skip in the Decision Log. If undertaken, add at most one paragraph to
`docs/developers-guide.md` beside "The shared JSON envelope" or "Disambiguated
exit codes" naming SKILL.md as the agent-facing restatement and the developers'
guide as canonical. Do not duplicate the table or schema.

Docs to read: `docs/developers-guide.md` ("The shared JSON envelope",
"Disambiguated exit codes"); `docs/documentation-style-guide.md` (developer's-
guide conventions). Skills to load: `en-gb-oxendict`.

Tests added: none. Validation: `make markdownlint`, `make nixie`, `make all`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-3`.

1. Confirm the branch and a clean tree (run from the worktree root):

       git branch --show-current
       git status

   Expect branch `roadmap-6-3-3` and a clean (or only-this-execplan) tree.

2. Establish the baseline state of the lint gate before any content edit:

       make markdownlint

   Expect exactly one error,
   `docs/developers-guide.md:149 MD012/no-multiple-blanks`. If markdownlint
   reports anything else, stop and escalate (Lint-precondition tolerance) — the
   baseline differs from this plan's analysis. Then perform **Work item 0**:
   delete one of the two consecutive blank lines at
   `docs/developers-guide.md` lines 148-149 (delete line 148), re-run
   `make markdownlint`, and expect it to pass on `**/*.md`. Commit Work item 0
   first and separately.

3. For each remaining Work item, edit `skill/novel-ralph/SKILL.md` (Work item 4
   edits `docs/developers-guide.md`), wrapping prose at 80 columns, captioning
   any table, and giving every fence a language identifier.

4. After each Work item's edit, run the Markdown gates and the full gate:

       make markdownlint
       make nixie
       make all

   Expect `markdownlint` to report no violations on `**/*.md` (the Work item 0
   fix having cleared the only baseline error), `nixie` to pass (no Mermaid
   added), and `make all` to stay green (the Python suite is unaffected by a
   prose-only change). A representative `markdownlint` success is silent or a
   clean summary; any MD013/MD058/caption failure names the file and line — fix
   at source.

5. Before committing each Work item, diff the working tree and stage **only** the
   intended hunks, guarding against spurious `make fmt`/`mdformat` reflow in
   other docs (Risks):

       git diff -- skill/novel-ralph/SKILL.md docs/developers-guide.md

   If unrelated docs show reflow churn, restore them to HEAD and re-apply only
   the intended edits before staging.

6. Commit each Work item separately with an en-GB Oxford-spelling message in the
   imperative mood, using the `commit-message` skill (file-based message, never
   `-m`). Keep `docs/execplans/roadmap-6-3-3.md` updated (Progress, Decision Log)
   as each item lands.

## Validation and acceptance

Acceptance is behaviour a reader can verify in the edited skill plus the two
Markdown gates the roadmap names.

Quality criteria (what "done" means):

- Documentation: `skill/novel-ralph/SKILL.md` documents, once, the exit-code
  table, the envelope schema, the run-from-root / check-exit-code discipline
  (with the `--help`/`--version` exit-0-no-envelope carve-out), and the install-
  currency note, each consistent with and pointing at the canonical sources
  (ADR-003, design §3, developers' guide), introducing no drifting fourth copy.
- Gating discipline: SKILL.md states that the **exit code** is the authoritative
  gating signal and that `ok` only reports success(0)-versus-not-success
  (1/2/3/4); it never tells the agent it "may gate on either", because `ok`
  cannot tell a benign exit 1 from a stop-and-fix exit 4 (verified:
  `exit_codes.py` line 55, `envelope.py` line 119). The benign exit-1 carve-out
  is honoured by branching on the exit code, not on `ok`.
- Lint: `make markdownlint` passes on the whole tree (`**/*.md`), **including the
  Work item 0 fix of the pre-existing `docs/developers-guide.md:149 MD012`
  baseline failure**. The gate cannot go green without that precondition fix, so
  acceptance includes it; a clean run reports zero errors over all 278 Markdown
  files.
- Mermaid: `make nixie` passes (no Mermaid added; a clean no-op pass).
- Full gate: `make all` stays green (no Python changed; the gate proves the edit
  broke nothing).
- Prose: en-GB Oxford spelling throughout; sentence-case headings; every table
  captioned with a delimiter row; every fence carries a language identifier;
  prose wrapped at 80 columns.

Quality method (how we check):

- Re-read each edited section against its cited source line ranges to confirm
  the documented codes, fields, and remedies are correct (not from memory).
- Run `make markdownlint`, `make nixie`, and `make all` from the worktree root
  after each Work item, and once more at the end.

## Idempotence and recovery

Every step is a re-runnable Markdown edit; re-running an edit or a gate is safe
and non-destructive. If a gate fails, fix the named file/line and re-run the
gate; no state is mutated outside the edited Markdown. If spurious reflow churn
is staged, `git restore` the affected docs to HEAD and re-apply only the intended
hunks. No production source, tests, or on-disk novel state are touched, so there
is nothing to roll back beyond the Markdown edits themselves.

## Artifacts and notes

The canonical contract sources this task documents, for the implementer's quick
reference:

- ADR-003 Table 2 (`docs/adr-003-shared-interface-contract.md` lines 85-95) —
  the five-code exit table.
- Design §3.1 (`docs/novel-ralph-harness-design.md` lines 146-201) — the
  envelope skeleton and field semantics.
- Developers' guide lines 522-593 — the developer-facing restatement SKILL.md
  points at as canonical.
- uv tools docs (<https://docs.astral.sh/uv/concepts/tools/>) — "Tool versions",
  "Upgrading tools", "Overwriting executables" — the install-currency semantics.

## Interfaces and dependencies

No code interfaces change. The only "interface" this task touches is the prose
contract of `skill/novel-ralph/SKILL.md`. The documented contract must match,
verbatim in meaning, the symbols already defined in
`novel_ralph_skill/contract/` (the `ExitCode` enum values 0-4, the six-field
`Envelope`, and the `ok`-iff-0 invariant) as restated in ADR-003 and the
developers' guide; this task adds no new symbols and depends on no new library.

## Revision note

Initial draft (2026-06-26). Decomposes roadmap task 6.3.3 into three atomic
documentation Work items (plus one conditional developers'-guide note),
single-sourcing the exit-code table and envelope schema in SKILL.md against
ADR-003 / design §3 / the developers' guide, adding the run-from-root /
check-exit-code discipline with the verified `--help`/`--version` exit-0-no-
envelope carve-out, and adding the install-currency note pinned to the verified
`uv tool` semantics (no auto-update; reinstall with `--force` or pin a version).
Every load-bearing behavioural claim is cited to a source line range or the uv
docs; no undecided forks remain (the inline-versus-pointer contract-description
choice is decided in favour of a concise inline restatement plus a single
canonical pointer, with the pure-pointer fallback bounded in the Decision Log).

Round 2 (2026-06-26). Revised to resolve the two design-review round-1 blocking
points; what changed and why:

1. Blocking point 1 (markdownlint baseline RED). A live `make markdownlint` on
   the worktree confirmed exactly one pre-existing error,
   `docs/developers-guide.md:149 MD012/no-multiple-blanks` (two consecutive
   blank lines at lines 148-149 before the `### The cross-command...` heading),
   committed at HEAD by the 6.3.2 commit. Because every Work item's validation
   and the acceptance criterion rest on markdownlint passing on `**/*.md`, the
   gate could not go green. Added **Work item 0**, a scoped one-line precondition
   that deletes one of the two blanks, ahead of the content items; scoped it in
   Constraints (Lint-baseline precondition) and Tolerances (Lint precondition;
   iteration trigger amended to exclude this baseline failure); restated the
   acceptance criterion as "make markdownlint passes on the whole tree,
   including this pre-existing fix"; and added a Risk, a Surprises entry, a
   Decision Log entry, a Progress line, and an explicit baseline-check Concrete
   step. If the live baseline shows any other error, the implementer escalates
   rather than expanding scope.

2. Blocking point 2 (gate-on-`ok` contradiction). Verified against source that
   `is_ok` returns `code is ExitCode.SUCCESS` (`exit_codes.py` line 55) and the
   envelope sets `ok=is_ok(code)` (`envelope.py` line 119), so a benign exit 1
   emits `ok: false` exactly like exits 2/3/4 and `ok` does NOT carry the
   load-bearing 1-versus-4 distinction. Removed the round-1 "the agent may gate
   on either" wording. Work item 2, the Purpose, the Constraints, the Terms
   "Stop-and-fix" definition, the Work item 1 envelope-schema instruction, the
   acceptance criteria, and a new Risk and Decision Log entry now all state that
   the **exit code** is the authoritative gating signal for the
   continue-versus-stop-and-fix decision, with `ok` framed only as the coarse
   success(0)-versus-not-success(1/2/3/4) bit and explicitly not a substitute
   for branching on the code. Work item 2's docs-to-read now cites the
   `exit_codes.py`/`envelope.py` source lines and the developers' guide
   "Disambiguated exit codes" load-bearing statement.
