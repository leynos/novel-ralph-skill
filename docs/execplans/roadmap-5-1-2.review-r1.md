# Logisphere design review — roadmap 5.1.2 — round 1

Adversarial pre-implementation review of `docs/execplans/roadmap-5-1-2.md`
(`desloppify` detection over the §6 offender table). Verdict: **Revise** — the
plan is structurally close but carries blocking gaps in rule-pack completeness,
the detection model for multi-token offenders, and one mis-stated
locked-library claim.

Trail followed: design §3.1-§3.2, §4.4, §6.1, §9; developers-guide "Rule packs
and the loader boundary", "Disambiguated exit codes"; scripting-standards
(cuprum/Cyclopts); AGENTS.md (400-line cap, snapshot/e2e rules, en-GB);
`skill/novel-ralph/references/desloppify-checklist.md` §6; real source —
`rulepack/{parse,schema}.py`, `contract/runner.py`,
`commands/{novel_state,_recount,stub}.py`, `state/wordcount.py`,
`contract/envelope.py`; cuprum sibling (`cuprum/{catalogue,sh}.py`).

## Blocking defects (back to the planner)

1. **Rule pack is under-specified and incomplete (Pandalump / Telefono).**
   The §6 table has **24 rows**; Work item 2 says "one `[[rule]]` per row" but
   enumerates only 6 example regexes and a per-rule test matrix that "asserts
   each rule matches a crafted positive and misses a crafted negative". A
   novice implementer cannot derive the other 18 rows' regexes, thresholds, or
   bases from the plan — they must improvise the heart of the deliverable. The
   plan must pin every row's `id`, `pattern`, `threshold`, and `basis`
   (verbatim thresholds from the §6 table), or the work item is neither atomic
   nor testable as written.

2. **Two placeholder rows are unpinned, and one obvious reading contradicts the
   checklist's own example (Doggylump / ambiguity tolerance).** The plan pins
   "found [herself]" and "capitalised abstract noun" but is silent on the other
   two placeholder rows the Risk register itself flags:
   - "shivers down [her] spine" — the `[her]` possessive-pronoun placeholder is
     unpinned.
   - "[verb]-ed sadly/quietly/softly" — the natural regex `\b\w+ed
     (?:sadly|quietly|softly)\b` **misses** the checklist's own canonical
     example, `she said sadly` (§4 "X said with adverbs"), because "said" does
     not end in "ed". A rule whose positive-case test would pass while missing
     the documented offender is a silent false-negative baked into v1. The plan
     must pin a defensible interpretation per the Tolerances ("pin the chosen
     interpretation in the Decision Log; if two readings materially change which
     prose is flagged, stop and present them").

3. **The detection model does not support multi-token span offenders (Pandalump
   / Buzzy Bee).** Work item 1 scans each chapter as one string and recovers
   line numbers from `match.start()`. Risk row 5 asserts "the offender patterns
   are anchored to word boundaries", but at least two §6 offenders are
   inherently multi-token spans: "It's not just… it's…" and "Some things…
   (sententious)". The plan's own example, `(?i)it'?s not just\b.*\bit'?s\b`,
   has two verified failure modes when run over whole-chapter text:
   - **Greedy over-match across sentence/paragraph boundaries:** `.*` matches
     from the first "it's not just" to a *distant, unrelated* "it's" later in
     the chapter (verified: a 47-char span across a full sentence boundary),
     inflating or mis-locating hits.
   - **Newline blindness:** with default flags `.` does not cross `\n`, so a
     genuine "It's not just X,\nit's Y" split across a line break is **missed**
     entirely (verified).
   The plan must either (a) constrain these patterns to a bounded,
   non-newline-spanning window (e.g. `[^\n]{0,N}` and document N), (b) scan
   line-by-line where the offender is single-line, or (c) explicitly scope the
   v1 pattern to the single-line case and record the limitation. As written,
   the "two hits on one line / count non-overlapping matches" test (Work item 1
   / Risk row 5) will not exercise the failure mode the example pattern
   actually exhibits.

4. **The cuprum claim in the Decision Log is mis-stated (Telefono).**
   The Decision Log asserts "`ProgramCatalogue.allowlist` admits any `Program`
   string". This is **false** against the real source: `cuprum/sh.py:make` calls
   `catalogue.lookup(program)`, which raises `UnknownProgramError` for any
   program not registered in the catalogue (`cuprum/catalogue.py`). The e2e
   works only because the existing test builds a *single-program* catalogue
   (`single_program_catalogue` in `tests/conftest.py`) containing that exact
   absolute-path program. The plan's cited pattern (mirror
   `test_console_scripts_e2e.py` via `single_program_catalogue`) is correct,
   but the stated rationale is wrong and, per the task brief, an uncited
   memory-based claim about a locked library is a blocking defect. Fix the
   Decision Log to describe the allowlist-registration mechanism the real code
   enforces (cite `cuprum/sh.py:make` → `catalogue.lookup`).

## Advisory (non-blocking, strengthen before/at implementation)

- **`recount_words` returns counts, not text (Wafflecat).** Work item 3 cannot
  reuse `state/wordcount.py:recount_words` to source draft *text*; it returns
  only the per-chapter token counts. The plan already reads `draft.md` itself,
  but should say explicitly that it reuses only the `chapter-{number:02d}`
  path-derivation convention and the `len(text.split())` token rule, not the
  function, so the density `total_words` cannot drift from `recount`.

- **`RuleBasis` JSON serialization (Telefono).** `render_machine` calls
  `json.dumps(ordered)` with no `default=` handler. `RuleBasis` is a `StrEnum`
  (a `str` subclass), so a raw member serialises as its bare string value — the
  envelope example `"basis":"per_page"` holds. Make the body emit the string
  explicitly (`basis.value` or `str(basis)`) so a future change of `RuleBasis`
  to a non-`str` Enum cannot silently break the contract, and add a snapshot
  assertion that `result.findings[].basis` is a string.

- **Exit-3 scope vs the roadmap success line (Dinolump).** The roadmap 5.1.2
  success criterion names only exits 0/4/2. The plan adds exit 3 (absent
  `working/`, unreadable pack file). This is *correct* and design-conformant
  (design §9 explicitly lists "unreadable or absent pack file → exit 3" and the
  absent-working-dir state-error channel), but the plan should cite design §9
  for the exit-3 cases rather than only §3.2, so a reviewer does not read it as
  scope creep beyond the roadmap line.

- **df12 spaced-en-dash note (Doggylump).** §1 of the checklist notes the df12
  register uses spaced en dashes ( – ), distinct from the em dash (—) the §6
  row counts. The em-dash rule's literal `—` pattern is correct for the §6 row;
  the plan should record that the spaced-en-dash variant is deliberately **out
  of scope** for v1 (it belongs to a register-specific pack), so a future
  reader does not treat the omission as a miss.

- **Snapshot determinism (AGENTS.md).** Work item 1 records `(chapter, line)`
  per hit and the envelope embeds a `lines` list. Confirm hit ordering is
  deterministic (it is, via `finditer` left-to-right and ascending chapter
  order) and assert that ordering invariant in the snapshot test, per the
  AGENTS.md snapshot rule against ordering-dependent churn.

## Pre-mortem (Doggylump)

- *Six months on, the agent's desloppify pass silently misses the most common
  AI tell.* Most likely trigger: the multi-token "it's not just… it's…" pattern
  (defect 3) misses every newline-split instance and mis-locates the rest, so
  the model adjudicates phantom or absent hits. Signal missed: the per-rule
  positive test used a single-line crafted string and never a newline-split or
  cross-sentence corpus. Prevention designable now: a multi-line and a
  cross-sentence negative in the Work item 1 matrix, plus a bounded
  non-newline-spanning window in the pattern.

- *The packaged pack ships incomplete.* Trigger: 18 unspecified rows (defect 1)
  get filled in ad hoc during implementation, half omitted under time pressure;
  the table-driven test only checks the rows that were authored. Prevention:
  pin all 24 rows in the plan and make the table-driven test assert the rule-id
  set equals the §6 row set, so a missing row fails.

## Strongest alternative (Wafflecat)

Author the offender pack as the deliverable's *specification* inside the
ExecPlan (all 24 rows, as a TOML block with per-row `# why`), and make Work
item 2 purely "transcribe the pinned pack and add the table-driven id-set
test". This trades a longer plan for an atomic, novice-followable, fully
testable work item, and removes the improvisation surface that defects 1-3 all
live in. It is meaningfully different (spec-first vs sketch-then-derive) and
strictly reduces implementation ambiguity. Recommended.

## What the plan gets right (credit where due)

- The detect-only / no-shell-out boundary (ADR-001, design §9) is correctly
  held; cuprum is correctly confined to the e2e.
- The exit-code mapping (`RulePackError`→2, `RulePackFileError`→3, clean→0,
  finding→4) matches developers-guide and design §3.2/§9 exactly.
- The runner-extension approach is mechanically viable: body exceptions
  propagate through `app(...)` under `exit_on_error=False` (proven by
  `novel-state`'s `StateInputError` path), and the body-returned `USAGE_ERROR`
  `CommandOutcome` flows cleanly through `run`.
- The pack-in-wheel risk and the `importlib.resources` resolution are sound;
  hatchling ships non-`.py` files under the package tree, and the e2e proves it.
- The per-source-file line-number decision (not a global buffer) is correct.
