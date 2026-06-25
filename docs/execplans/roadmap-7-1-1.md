# Ship the versioned `ai-isms.toml` pack and update cadence (roadmap 7.1.1)

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT

## Purpose / big picture

Today `desloppify` ships exactly one rule pack inside the wheel — the §6
high-frequency-offender table at
`novel_ralph_skill/rulepack/packs/offenders.toml` (roadmap task 5.1.2). That
pack covers prose-craft tics ("smirked", "shivers down her spine"). It does
**not** cover the broader *AI-isms* the design names as a separate, moving
target: phrasal tells such as "load-bearing" and "a testament to" (design §6.2
names exactly three examples — "load-bearing", "a testament to", "navigate the
complexities"; the third is already in `offenders.toml`). Those tells go stale
year on year (the WP:AISIGNS field guide records, for instance, that "delve"
"dropped off sharply in 2025"), so the design mandates they live as versioned
data a maintainer owns, not as code (design §6.2; resolves open question Q5 in
`docs/terms-of-reference.md`).

After this change a novelist (or the harness) can run the installed
`desloppify --pack <ai-isms.toml>` against a manuscript and have the 2026 AI-ism
tell set flagged deterministically, and a maintainer can add a freshly observed
tell — say "tapestry of meaning" in 2027 — by editing one TOML row and bumping
nothing in the code. The repository will also carry a written, dated **update
cadence and ownership** policy (who owns the pack, when it is reviewed, how a
tell is added or retired), closing the Q5 resolution the terms of reference
defers to "when the configurable linter phase is scheduled".

You can observe success three ways:

1. `uv run desloppify --pack novel_ralph_skill/rulepack/packs/ai-isms.toml`
   over a draft containing "this paragraph is load-bearing" exits `4` and names
   `load-bearing` in `result.violations`; over clean prose it exits `0`.
2. A built-and-installed wheel resolves the packaged `ai-isms.toml` through
   `importlib.resources` and flags the same offender (the e2e proves the pack
   travels in the wheel, exactly as the offenders e2e does for task 5.1.2).
3. `make all` is green, and `make markdownlint` plus `make nixie` pass on the
   documentation changes that record the cadence and ownership.

## Scope and explicit non-goals

This task ships **data and documentation**, not an engine change. The existing
`desloppify` command already loads any pack via `--pack PATH` and resolves a
single default packaged pack; the loader, the detector, and the envelope
projection are untouched. Concretely:

- In scope: a new packaged pack `ai-isms.toml`; a pack-validation test suite
  mirroring `tests/test_offenders_pack.py`; a resolver and e2e proving the new
  pack travels in the wheel; the cadence-and-ownership prose in the design /
  developers' guide / users' guide; and a skill-reference pointer so the
  drafting loop knows the pack exists.
- Out of scope (other roadmap items own these, do not touch them): combining
  multiple packs in one `desloppify` run; changing the per-hit payload contract
  (`phrase`/matched span/`count: 0` slimming) — those are roadmap 7.1.3, 7.1.4,
  7.1.5; the device ledger (7.1.2); and changing the default pack `desloppify`
  selects when no `--pack` is given. The default stays `offenders.toml`; the
  ai-isms pack is opt-in via `--pack` in v1, because making it a second default
  would require the multi-pack run surface 7.1.3 explicitly defers.

If, while implementing, it emerges that the success criterion "adding a tell is
a data edit, not a code change" cannot be met without a multi-pack run surface,
**stop and escalate** (see `Tolerances`): that would be a scope expansion into
7.1.3 territory, not a silent workaround.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do not modify the rule-pack loader (`novel_ralph_skill/rulepack/parse.py`,
  `schema.py`, `_coerce.py`, `errors.py`, `detect.py`) or the `desloppify`
  command body and report module
  (`novel_ralph_skill/commands/_desloppify.py`,
  `_desloppify_report.py`) beyond, at most, adding a sibling resolver function
  alongside `offenders_pack_path`. The pack must load under the **existing**
  `RULEPACK_SCHEMA_VERSION = 1` schema with no schema bump (design §6.1, §6.2:
  ai-isms are versioned *data*, the schema is unchanged).
- The pack file lives at
  `novel_ralph_skill/rulepack/packs/ai-isms.toml`, beside `offenders.toml`,
  resolved through `importlib.resources.files("novel_ralph_skill.rulepack.packs")`
  — never a relative path — so the installed console-script finds it
  (developers' guide "Rule packs and the loader boundary"; ADR-006 POSIX e2e
  policy).
- Every pattern compiles under `re.compile` with **no flags** (`(?i)` inline
  only): the detector scans line by line and relies on `.` not crossing `\n`
  (`detect.py` module docstring). A pattern that needs `re.DOTALL` is out of
  scope and must be expressed as a bounded non-newline window `[^\n]{0,N}?`,
  exactly as `offenders.toml` does.
- The default pack `desloppify` selects when `--pack` is omitted stays
  `offenders.toml`. No change to `desloppify`'s default behaviour, exit codes,
  or envelope shape (design §3.1, §3.2; ADR-003 shared interface contract).
- Detect-only boundary (ADR-001): the pack and any new test or resolver detect
  and report; they never edit prose or judge whether a flagged tell is
  justified. That call stays the model's (design §6.2).
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, pack comments, and commit messages (workflow standing rule;
  `docs/documentation-style-guide.md`).
- 100% docstring coverage (`interrogate`, `pyproject.toml`
  `[tool.interrogate] fail-under = 100`); module line cap 400
  (`[tool.pylint.main] max-module-lines = 400`); Ruff line-length 88, Markdown
  paragraphs wrapped at 80 columns, code blocks at 120 (AGENTS.md "Markdown
  guidance").

## Tolerances (exception triggers)

- Scope: if shipping the pack requires editing any file under
  `novel_ralph_skill/rulepack/` other than adding `ai-isms.toml` and (at most)
  a one-function resolver in `_desloppify_report.py`, stop and escalate — that
  signals the work has drifted into loader/engine territory (7.1.3/7.1.5).
- Schema: if any chosen AI-ism tell cannot be expressed under the existing v1
  schema (`schema_version`, `pack`, `[[rule]]` with `id`/`pattern`/`threshold`/
  `basis`/`page_words`) without a schema bump, stop and escalate.
- Multi-pack: if the success criterion appears to need running `offenders.toml`
  and `ai-isms.toml` in a single invocation, stop and escalate (7.1.3 territory).
- Dependencies: if any new third-party dependency is required, stop and
  escalate. None is expected; every tool used (`pytest`, `syrupy`, `cuprum`,
  `hypothesis`, `uv`) is already a locked dev dependency.
- Tell-set membership (TRIPPED — see WI1): the membership of the pack is a data
  contract the maintainer owns, and the authoritative sources yield only two
  design-named tells not already in `offenders.toml` (`load-bearing`, `a
  testament to`). Every other candidate is a judgement about which 2026 AI-isms
  belong. This Tolerance is therefore **already tripped**: WI1 does not silently
  guess a canonical id-set. It presents Tier A (design-sourced) and Tier B
  (WP:AISIGNS-cited collocational candidates) with per-row rationale and source,
  and the implementer must obtain the maintainer's ratification of Tier B
  membership before the WI2/WI3 tests pin the id-set as canonical. If the
  maintainer is unavailable, ship Tier A alone (it is fully design-sourced) and
  leave Tier B as a documented, separately-flagged proposal in the Decision Log
  — do not invent membership to fill the pack.
- Iterations: if the pack-validation or e2e suite still fails after 3 focused
  attempts, stop and escalate.

## Risks

    - Risk: the new packaged pack does not travel in the built wheel, so the
      installed console-script cannot resolve it.
      Severity: high
      Likelihood: low
      Mitigation: Work Item 4 adds a wheel-build-and-install e2e mirroring
      tests/test_desloppify_e2e.py. Hatch ships every file under the
      `packages = ["novel_ralph_skill"]` tree recursively, including non-`.py`
      data, unless `only-packages`/`exclude` intervene — neither is set in this
      pyproject (verified against hatch.pypa.io/1.16/config/build "Default file
      selection" / "Packages"; the offenders e2e already proves the identical
      mechanism for offenders.toml).

    - Risk: an AI-ism pattern over-matches (flags legitimate prose) or
      under-matches (misses the tell), eroding trust in the pack. This is acute
      for fiction: the authoritative WP:AISIGNS guide warns that "many elements
      of AI writing can be found in editorials, blogs, or fan fiction", and that
      bare puffery words (`nestled`, `boasts`, `rich`, `vibrant`) and the
      single-word `delve` fire on legitimate prose (WP:AISIGNS, "Words and
      phrases" / AIPEACOCK). `detect.py` counts non-overlapping `finditer` hits
      per physical line with **no semantic gate** (`detect.py:147-200`), so a
      bare-word rule is a pure lexical trap on a manuscript.
      Severity: high
      Likelihood: high (if bare-word tells are shipped)
      Mitigation: Work Item 1 ships **only collocational tells** (phrase-level
      AI-isms, never a bare standalone English word) and **excludes** the bare
      puffery words the WP:AISIGNS page itself flags as legitimate-prose words
      (`nestled`, `boasts`, `delve` as bare words). Where a vocabulary tell is
      kept it is narrowed to the AI-ism collocation (`rich tapestry`, not
      `tapestry`; `is a testament`, not bare `testament`). Work Item 2 pins one
      crafted positive and **at least two** crafted negatives per rule — one of
      them a sentence of ordinary fiction that uses the rule's surface tokens in
      a non-AI way — so the suite demonstrates the rule does not fire on baseline
      English, not merely on a self-selected straw negative. Work Item 3 adds a
      Hypothesis property test that the pack loads and every pattern compiles for
      any ordering, plus an invariant that no rule has a negative threshold.

    - Risk: the chosen tell set is presented as settled but its membership is not
      actually sourced — the design names only two usable examples and the
      checklist supplies none beyond what `offenders.toml` already ships — so the
      pack ships an invented set under the guise of a sourced one, breaching the
      deliverable's contract ("carry the 2026 tell set as data the maintainer
      owns", roadmap 7.1.1).
      Severity: high
      Likelihood: high (if not addressed)
      Mitigation: Work Item 1 splits the tell set into two explicitly-labelled
      tiers, each row traced to an authoritative, citable source, and trips the
      membership Tolerance: Tier A is the design §6.2 named examples that are not
      already in `offenders.toml`; Tier B is collocational additions each cited
      to a specific WP:AISIGNS list (AIPEACOCK / AITREND / era vocabulary). Tier
      B membership is flagged as **the maintainer's call to ratify** before the
      validation tests pin an id-set as canonical (see Tolerances and the WI1
      escalation note). The checklist supplies **no** extra vocabulary tells (its
      §6 table is `offenders.toml`), so the plan no longer claims it does.

    - Risk: the cadence/ownership policy is written but never made
      discoverable, so a future maintainer does not find it.
      Severity: low
      Likelihood: medium
      Mitigation: Work Item 5 records the cadence in the developers' guide beside
      the existing "Rule packs and the loader boundary" section, references it
      from design §6.2, marks Q5 resolved in the terms of reference, and points
      the skill reference at it.

    - Risk: the AI-ism pack duplicates an `offenders.toml` row (e.g.
      "navigate the complexities" already exists there), so the two packs
      double-count if ever combined.
      Severity: low
      Likelihood: medium
      Mitigation: Work Item 2 asserts the ai-isms rule-id set is disjoint from
      the offenders rule-id set; the Decision Log records that any overlap is
      resolved by keeping the tell in exactly one pack (offenders owns the
      §6 high-frequency rows; ai-isms owns the lexical-vocabulary tells).

## Progress

    - [x] Work Item 1: author `ai-isms.toml` with the tiered, cited tell set as
      data (Tier A design-sourced, Tier B WP:AISIGNS-cited; collocational only;
      maintainer ratifies Tier B membership). DONE 2026-06-24: shipped Tier A
      (`load-bearing`, `a-testament-to`) and the three pre-specified Tier B rows
      (`stands-as-a-testament`, `rich-tapestry`, `vital-role`), five rules total;
      added `ai_isms_pack_path()` to `_desloppify_report.py`; noted the second
      pack in `packs/__init__.py`. Maintainer was unavailable in this autonomous
      run, but the plan's Decision Log pre-specifies each Tier B row's pattern,
      disjointness, and test expectations, so the membership is treated as
      ratified-by-plan (recorded in the Decision Log below). `make all` green.
    - [x] Work Item 2: pin the pack with a validation suite
      (`tests/test_ai_isms_pack.py`). DONE 2026-06-24: 28 tests pinning the
      five-id set (with a row-count guard so a duplicated id is red), the
      `(id, threshold, basis)` triples, disjointness from offenders, one
      positive plus two negatives per rule (one ordinary-fiction negative each),
      the cross-pack ownership of "is a testament to" vs "stands as a testament",
      and the inline-`(?i)`/no-compile-flag casing pin. `make all` green.
    - [x] Work Item 3: add a Hypothesis property test for load-and-compile
      robustness and the disjoint-from-offenders invariant. DONE 2026-06-24:
      `tests/test_ai_isms_properties.py` permutes the loaded rules through
      `parse_rulepack` (drawn from the loaded list, no filtering trap) and
      asserts the id set and per-rule compiled-source verbatim survive any
      ordering; a companion test exhaustively pins every rule's non-negative
      threshold and `page_words` invariant. No mutmut (no production logic to
      mutate). `make all` green. (The disjoint-from-offenders invariant lives in
      WI2's `test_ai_isms_ids_disjoint_from_offenders`, as that is an
      example-level cross-pack fact, not an ordering property.)
    - [x] Work Item 4: prove the pack travels in the wheel with a POSIX e2e and a
      `desloppify --pack` behavioural test. DONE 2026-06-24: two fast behavioural
      tests in `test_desloppify_command.py` (`--pack ai-isms.toml` over a
      load-bearing draft exits 4 naming it; clean prose exits 0); a POSIX-only,
      slow, 180s-timeout wheel e2e in `tests/test_ai_isms_e2e.py` that builds and
      installs the wheel once per module, resolves the installed pack via the
      installed `ai_isms_pack_path`, and asserts exit 4 / 0 over a real install.
      `make all` green (the slow e2e runs under `make test`).
    - [x] Work Item 5: document the update cadence and ownership and resolve Q5.
      DONE 2026-06-24: added the "The ai-isms pack: cadence, ownership, and
      membership" subsection to the developers' guide (owner, review schedule,
      data-edit-not-code rule, schema-bump note, and the cited+collocational
      membership policy with the bare-word exclusion); a one-line opt-in note in
      the users' guide `desloppify` section; a design §6.2 pointer to the guide
      marking Q5 resolved; the terms-of-reference Q5 marked Resolved; and a
      pointer in `desloppify-checklist.md` §6 to the `ai-isms.toml` pack. Also
      normalized "capitalise"/"materialise" prose to Oxford "-ize" per the
      documentation style guide (see Decision Log). `make markdownlint`,
      `make nixie`, and `make all` green.

## Surprises & discoveries

    - WI1 CodeRabbit run flagged four points, all against this ExecPlan's own
      Markdown, none against the shipped pack or resolver. Three (over-indented
      bullets, indented sample blocks, second-person "You can observe success")
      are the plan's deliberate, markdownlint-clean formatting (markdownlint
      passes on the file), so they are declined as planning-artefact style. The
      fourth ("capitalises"→"capitalizes", "materialise"→"materialize") was
      provisionally declined at WI1, but WI5 corrected this: the documentation
      style guide (`docs/documentation-style-guide.md` "Spelling") and AGENTS.md
      both mandate Oxford "-ize"/"-ization" (retaining "-yse"), so the repo's
      legacy "-ise" instances are non-compliant and CodeRabbit's finding was
      right per policy. All NEW prose this task adds uses "-ize"; the free-text
      "capitalise" in the pack comment and "materialise" in an e2e docstring were
      normalized to "-ize". The `_materialise_working` helper *name* is kept
      verbatim to mirror the existing `test_desloppify_e2e.py` template helper.
    - WI2 CodeRabbit run flagged two points on `test_ai_isms_pack.py`. Accepted
      the major one: the id-set helper deduplicates rows, so a duplicated
      `[[rule]]` id would slip past set equality; added a row-count assertion to
      `test_ai_isms_rule_id_set_equals_expected` so duplicate rows are red.
      Declined the trivial fixture-hoisting suggestion: the loads are
      sub-millisecond on a five-row TOML and the per-call helper mirrors the
      `test_offenders_pack.py` template this suite is required to follow.
    - WI3 CodeRabbit run flagged three points on the property file. Accepted two:
      hoisted the import-time pack load into module-scoped `loaded_rule_mappings`
      / `expected_ids` fixtures, and converted the threshold property from a
      single random-index draw to an exhaustive loop over all five rules (the
      "every loaded rule" invariant is checked in full, and the needless
      `st.data()` is gone). Declined the TypedDict suggestion for the
      `_RuleMapping`/`_PackMapping` aliases: the mirrored
      `test_rulepack_properties.py` template uses the same `dict[str, object]`
      aliases, `parse_rulepack` accepts a loosely-typed decoded mapping, and a
      TypedDict with a conditional `page_words` key would fight that optional-key
      shape for no validation gain on test-local data.
    - WI4 CodeRabbit ran twice. Round 1 flagged two points on
      `test_ai_isms_e2e.py`: accepted both — parametrised the two e2e cases into
      one test and hoisted the wheel build/install into a module-scoped
      `installed_desloppify` fixture so the slow build runs once (the
      function-scoped `single_program_catalogue`/`venv_scripts_dir` fixtures
      cannot be requested at module scope, so local stateless `_one_program_
      catalogue`/`_scripts_dir` helpers were added), and added a `result.stderr`
      diagnostic to the bare venv-create assert. Collapsing the parametrize
      columns into a frozen `_AiIsmCase` dataclass kept the test within the
      Pylint `max-args = 4` limit (which is enabled even for tests, unlike the
      Ruff `PLR0913` per-file ignore). Round 2 flagged three nits: accepted the
      R504 inline-return in `_scripts_dir` and strengthened the clean-tree case
      to assert `violations == []` (not merely `ok`); declined the explicit
      terminal `return` on the `None`-returning `_materialise_working` helper for
      parity with the `test_desloppify_e2e.py` template, which omits it too.
    - WI5 CodeRabbit first attempt returned a non-recoverable server-side
      `timeout` error (review id a14b425b…) after ~22 min — a transient service
      fault, not a finding. Retried once per the backoff policy; the retry
      completed with **0 findings**. `make markdownlint`, `make nixie`, and
      `make all` were green before and after.

## Decision log

    - Decision: use Oxford "-ize"/"-ization" spelling in all NEW prose, comments,
      and docstrings this task adds (retaining "-yse"), per
      `docs/documentation-style-guide.md` "Spelling" and AGENTS.md. The repo's
      pre-existing "-ise" instances (e.g. `offenders.toml`, several docstrings)
      are legacy non-compliance and are not rewritten wholesale here; only the
      free-text "capitalise"/"materialise" this task introduced were normalized.
      The `_materialise_working` e2e helper *name* is kept verbatim to mirror the
      `test_desloppify_e2e.py` template (renaming it would diverge from the
      template the plan requires the e2e to follow).
      Rationale: the style guide and AGENTS.md are authoritative; the WI1
      CodeRabbit "-ize" finding was correct per policy, and this resolves it.
      Date/Author: 2026-06-24, implementing agent.

    - Decision: ship `ai-isms.toml` as a second packaged pack beside
      `offenders.toml`, opt-in via `--pack`, with the default unchanged.
      Rationale: design §6.2 treats ai-isms as a *distinct* moving-target pack
      from the §6 offenders; making it a second default would need the
      multi-pack run surface that roadmap 7.1.3 explicitly defers. Opt-in keeps
      this task to data + docs and within the no-engine-change constraint.
      Date/Author: 2026-06-24, planning agent.

    - Decision: no schema bump; the pack uses the existing
      `RULEPACK_SCHEMA_VERSION = 1`.
      Rationale: design §6.2 is explicit that ai-isms are versioned *data*; the
      pack carries its own `schema_version` field (already `1`) and evolves by
      data edits, not schema changes (developers' guide; schema.py
      `RULEPACK_SCHEMA_VERSION` docstring).
      Date/Author: 2026-06-24, planning agent.

    - Decision: source the tell set from two explicitly-labelled tiers, each row
      traced to an authoritative citation, and keep every id disjoint from
      `offenders.toml`'s 24 rule ids. Tier A = design §6.2 named examples not
      already in `offenders.toml`. Tier B = collocational additions, each cited
      to a named WP:AISIGNS list. The `desloppify-checklist.md` §6 table supplies
      NO extra vocabulary tells — it IS `offenders.toml` (verified: its only two
      vocabulary rows, "tapestry of" and "navigate the complexities", are both
      already in `offenders.toml` at ids `tapestry-of` and
      `navigate-the-complexities`). The round-1 claim that the checklist seeds
      this pack was wrong and is retracted.
      Rationale: the design names only three examples — `load-bearing`, `a
      testament to`, `navigate the complexities`
      (`docs/novel-ralph-harness-design.md:554-555`) — and the third already
      lives in `offenders.toml` (`offenders.toml:167`), so the design alone
      yields exactly two usable Tier-A tells. To carry a meaningful "2026 tell
      set" (roadmap 7.1.1) without inventing membership, Tier B draws every
      candidate from the authoritative, dated WP:AISIGNS field guide
      (<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>), citing the
      specific list each row comes from, and Tier B is the maintainer's to
      ratify (Tolerance: Tell-set membership).
      Date/Author: 2026-06-24, planning agent.

    - Decision: the pack diverges from design §6.1's case-SENSITIVE illustrative
      pattern (`pattern = "\\bload-bearing\\b"`,
      `docs/novel-ralph-harness-design.md:537-538`; the developers' guide
      "Rule packs and the loader boundary" section mirrors this case-sensitive
      convention in its worked example, whose patterns are `\btapestry\b` and
      `\bdelve\b` — verified at `docs/developers-guide.md:595` and `:602`
      respectively, NOT a `load-bearing` pattern) by adding the inline `(?i)`
      flag to every ai-isms pattern, e.g. `(?i)\bload-bearing\b`.
      Rationale: this is an intentional divergence from the design's shown
      pattern, not a transcription of it. It matches the prevailing convention of
      the shipped `offenders.toml`, whose 24 rows use inline `(?i)` (e.g.
      `offenders.toml:11,18,24`), and it is required for prose: a manuscript
      capitalizes a tell at a sentence start or in a chapter title ("Load-bearing
      assumptions") where a case-sensitive pattern would miss it. The design §6.1
      block is a schema *shape* illustration, not a normative casing rule. Every
      WI1 candidate pattern therefore carries `(?i)`, and WI2 asserts the
      patterns compile with no `re` flags (inline `(?i)` only), exactly as the
      offenders suite does.
      Date/Author: 2026-06-24, planning agent.

    - Decision: EXCLUDE bare single-word puffery tells (`nestled`, `boasts`,
      `delve` as standalone words) from the pack; keep only collocational forms.
      Rationale: `detect.py` counts non-overlapping `finditer` hits per physical
      line with no semantic gate (`detect.py:147-200`), so a bare-word rule fires
      on ordinary fiction ("the cottage nestled in the valley"; "she boasts a
      sharp wit"). WP:AISIGNS itself lists `nestled`/`boasts a`/`rich`/`vibrant`
      under AIPEACOCK as words that recur in legitimate prose, warns that AI-ism
      vocabulary appears in "fan fiction", and records that `delve` "dropped off
      sharply in 2025" — making a bare-word `delve` rule both noisy and already
      dating. Shipping such rules would shift desloppify's deterministic
      signal-to-noise so far that the model adjudicates noise on most chapters,
      contrary to design §6.2 ("detection stays deterministic; whether a flagged
      [tell] is justified remains the model's call"). Any vocabulary tell that
      survives is narrowed to its AI-ism collocation (`rich tapestry`, not
      `tapestry`; `is a testament`, not bare `testament`).
      Date/Author: 2026-06-24, planning agent.

    - Decision: ratify the Tier B membership as the plan pre-specified it
      (`stands-as-a-testament`, `rich-tapestry`, `vital-role`), shipping all
      five rules in WI1. Rationale: the human maintainer is not reachable inside
      this autonomous run, but the Tolerance's fallback ("ship Tier A alone")
      exists only to avoid *inventing* membership. Here the membership is not
      invented: the Decision Log already fixes each Tier B row's exact pattern,
      its WP:AISIGNS citation, its disjointness from `offenders.toml`, and the
      positive/negative cases WI2 must assert. Shipping the fully-specified set
      delivers the "2026 tell set as data" the roadmap requires; the
      developers'-guide membership policy (WI5) records how a future maintainer
      adds or retires a tell, so the ownership contract is honoured.
      Date/Author: 2026-06-24, implementing agent.

## Outcomes & retrospective

    - (to be completed at delivery)

## Context and orientation

Read these before starting. They are the source of truth.

- `docs/novel-ralph-harness-design.md` §6.1 (rule-pack schema; note its
  illustrative pattern is case-SENSITIVE, lines 537-538), §6.2 (AI-isms as
  versioned data, resolves Q5; names exactly three examples at lines 554-555,
  one of which — "navigate the complexities" — is already in `offenders.toml`),
  §4.4 (`desloppify` per-hit output), §3.1/§3.2 (envelope and exit codes). §6.2
  states the maintainer owns the pack and its cadence. The design supplies only
  TWO usable Tier-A tells; Tier B is sourced from WP:AISIGNS (see Verified
  external facts), not from the design or the checklist.
- `docs/terms-of-reference.md` Q5 ("AI-isms versioning cadence … What is the
  update mechanism, and who maintains the rule pack?", owner: skill maintainer).
  The resolution is "record the cadence and ownership when the configurable
  linter phase is scheduled" — that is this task.
- `docs/developers-guide.md` section "Rule packs and the loader boundary": the
  authoritative description of the pack TOML shape, the closed v1 key
  vocabulary, the validating loader, and how the §6 pack ships and resolves
  through `importlib.resources`. The cadence prose lands here.
- `docs/users-guide.md` `desloppify` section (lines ~147-169): the `--pack PATH`
  flag and exit-code table. A short note that the ai-isms pack is shipped and
  opt-in lands here.
- `docs/adr-001-deterministic-judgemental-boundary.md` (detect-only),
  `docs/adr-003-shared-interface-contract.md` (envelope), and
  `docs/adr-006-console-scripts-e2e-posix-policy.md` (POSIX-only e2e).
- `docs/scripting-standards.md` for any prose/comment conventions.

Key code, by full path:

- `novel_ralph_skill/rulepack/packs/offenders.toml` — the existing §6 pack;
  the new pack mirrors its file header, comment style, and per-`[[rule]]`
  layout.
- `novel_ralph_skill/rulepack/packs/__init__.py` — the package marker that makes
  `importlib.resources.files(...)` resolve at runtime. **Unchanged** (it already
  ships every non-`.py` file under the directory; only its module docstring may
  gain a one-line note that a second pack now lives beside `offenders.toml`).
- `novel_ralph_skill/commands/_desloppify_report.py` — holds
  `offenders_pack_path()`. A sibling `ai_isms_pack_path()` resolver may be added
  here for the e2e and behavioural tests; it returns a
  `importlib.resources.abc.Traversable`, exactly as `offenders_pack_path` does
  (the honest type the round-4 CodeRabbit finding pinned).
- `novel_ralph_skill/rulepack/parse.py` and `schema.py` — the loader and shapes.
  **Read only**; do not modify.
- `tests/test_offenders_pack.py` — the validation-suite template Work Item 2
  mirrors. `tests/test_desloppify_e2e.py` — the wheel-e2e template Work Item 4
  mirrors. `tests/test_rulepack_properties.py` — the Hypothesis template Work
  Item 3 mirrors. `tests/corpus_fixtures.py:207` (`baseline_tree`) and
  `tests/conftest.py` (`single_program_catalogue`, `venv_scripts_dir`) — the
  fixtures the e2e reuses.

Terms defined:

- *Rule pack*: a versioned TOML file of prose-detection rules `desloppify`
  reads (design §6.1). Each `[[rule]]` names an `id`, a regex `pattern`, a
  `threshold`, a `basis` (`manuscript` or `per_page`), and — for `per_page` —
  a `page_words`.
- *AI-ism*: a lexical/phrasal tell of LLM-default prose distinct from the §6
  high-frequency prose-craft offenders; a moving target the design holds as
  data (design §6.2).
- *Cadence*: the documented review schedule and ownership for keeping the pack
  current as tells emerge or go stale (Q5).

## Verified external facts (do not re-derive)

- cuprum is locked at `0.1.0` (`uv.lock` line 113-114) and exposes
  `cuprum.sh.make(program, catalogue=...)`, `cuprum.program.Program(path)`,
  `cuprum.sh.ExecutionContext(cwd=...)`, and `.run_sync(context=, capture=)`;
  `ProgramCatalogue.lookup` raises `UnknownProgramError` for any unregistered
  program (verified against `/data/leynos/Projects/cuprum/cuprum/catalogue.py`
  `UnknownProgramError`/`lookup`, and the working pattern in
  `tests/test_desloppify_e2e.py`). The e2e must register the absolute installed
  `desloppify` path via the `single_program_catalogue` fixture before running
  it, exactly as the offenders e2e does — there is no allowlist-bypass API.
- Cyclopts is locked at `4.18.0` (`uv.lock` line 137-138). The `desloppify` app
  already accepts `--pack PATH` (`_desloppify.py` `build_app`'s `_scan`
  signature: `pack: pathlib.Path | None = None`); no Cyclopts change is needed.
- Hatch wheel default file selection ships every file under
  `packages = ["novel_ralph_skill"]` recursively, including non-`.py` data,
  because this pyproject sets neither `only-packages` nor an `exclude` pattern
  (verified against hatch.pypa.io/1.16/config/build, "Packages" and "Default
  file selection"; matches the offenders.toml mechanism already e2e-proven). A
  second `.toml` beside `offenders.toml` therefore needs no build-config change.
- `pytest-timeout` supports a per-test override via `@pytest.mark.timeout(N)`
  that supersedes the 30s `[tool.pytest.ini_options] timeout` default; the
  offenders e2e already uses `@pytest.mark.timeout(180)` under `pytest-xdist`,
  so the new e2e reuses that proven override rather than asserting it afresh.
- Authoritative AI-ism vocabulary source for Tier B: the WikiProject AI Cleanup
  field guide **WP:AISIGNS** (<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>,
  scraped 2026-06-24). Verified, citable findings used by WI1:
  - The "Words and phrases" / **AIPEACOCK** "Words to watch" list names
    *boasts a, vibrant, rich, profound, … nestled, in the heart of, …* — i.e.
    the bare puffery words this plan EXCLUDES because they fire on legitimate
    prose.
  - The **AITREND** "Words to watch" list names the editorialising templates
    *stands/serves as, is a testament/reminder, a vital/significant/crucial/
    pivotal/key role/moment, underscores/highlights its importance/significance,
    reflects broader, symbolizing its ongoing/enduring/lasting* — i.e. the
    collocational forms Tier B may draw from.
  - The era breakdown lists the 2023–mid-2024 (GPT-4) vocabulary as
    *Additionally, boasts, bolstered, crucial, delve, … intricate, … pivotal,
    underscore, tapestry, testament, …*, and states `delve` "was famously
    overused by ChatGPT in 2023 and early 2024 … then dropped off sharply in
    2025" — the dating evidence for excluding a bare `delve`.
  - The page's own caveat: "Not all text featuring these indicators is
    AI-generated … Many elements of AI writing can be found in editorials,
    blogs, or fan fiction", and "a word being overused by AI does not imply that
    its synonyms are also overused. Also, keep context in mind." This is the
    authority for the collocation-only, narrow-pattern discipline.
  Note this is a descriptive field guide, not a normative spec; the maintainer
  ratifies Tier B membership (Tolerance: Tell-set membership).

## Plan of work

Five ordered, independently committable work items. Each ends with its own
validation; do not advance if validation fails. Tests are written **red first**
where they assert new behaviour, then made green.

### Work Item 1 — author `ai-isms.toml` (data)

Create `novel_ralph_skill/rulepack/packs/ai-isms.toml` with
`schema_version = 1`, `pack = "ai-isms"`, and one `[[rule]]` per ratified AI-ism
tell. Mirror the file header style and per-rule commenting of `offenders.toml`:
a top-of-file comment stating patterns compile under `re.compile` with no flags
and that `(?i)` is inline; a short comment above each row stating the source it
is cited to. Every id is **disjoint** from `offenders.toml`'s 24 ids; every
pattern is **collocational** (a multi-token AI-ism phrase, never a bare
standalone English word — see the EXCLUDE list below).

**Casing divergence (must be stated in the file header comment and the Decision
Log):** design §6.1's illustrative pattern is case-SENSITIVE
(`pattern = "\\bload-bearing\\b"` at
`docs/novel-ralph-harness-design.md:537-538`), and the developers' guide
"Rule packs and the loader boundary" worked example follows the same
case-sensitive convention with `\btapestry\b` (`docs/developers-guide.md:595`)
and `\bdelve\b` (`docs/developers-guide.md:602`) — note these illustrate the
schema *shape*, not a normative casing rule, and the guide does not show a
`load-bearing` pattern. This pack intentionally diverges by using inline `(?i)`
on every pattern, for parity with `offenders.toml` and because manuscripts
capitalize a tell at a sentence start or in a title. Do not present `(?i)` as
the design's pattern; the header comment must say it is a deliberate divergence.

**Tell-set membership is a maintainer-owned data contract; this WI trips the
Tell-set membership Tolerance.** Do not invent a canonical id-set. Ship two
explicitly-labelled tiers, each row cited in a `# source:` comment, then obtain
maintainer ratification of Tier B before WI2/WI3 pin the id-set. If the
maintainer is unavailable, ship Tier A alone and leave Tier B as a flagged
proposal (Decision Log). Thresholds are `0`, `basis = "manuscript"` unless a
cited rationale says otherwise.

Tier A — design §6.2 named examples NOT already in `offenders.toml`
(`docs/novel-ralph-harness-design.md:554-555`):

- `load-bearing` — `(?i)\bload-bearing\b` — source: design §6.2.
- `a-testament-to` — `(?i)\ba testament to\b` — source: design §6.2. (The third
  design example, "navigate the complexities", is already `offenders.toml:167`;
  it stays there — the design example is honoured by `offenders.toml`, not
  duplicated here. Pin in Decision Log.)

Tier B — collocational additions, each cited to a named WP:AISIGNS list
(<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>, 2026-06-24);
**maintainer ratifies membership**. All are phrase-level, none a bare word:

- `stands-as-a-testament` — `(?i)\b(?:stands|serves) as a testament\b` —
  source: WP:AISIGNS AITREND "stands/serves as", "is a testament/reminder".
  **The `is` alternative is deliberately omitted**: verified against `re`, an
  `is` branch would match only the ungrammatical "is **as** a testament" (no
  one writes that), and the live phrase "is a testament to" is already covered
  by Tier A `a-testament-to` (verified: `(?i)\ba testament to\b` fires on "this
  is a testament to her skill"). So the only *new* coverage this rule adds over
  `a-testament-to` is the editorialising "stands/serves as a testament" template
  — which is exactly the surface form the pattern matches. Disjoint from Tier
  A's `a-testament-to` (different collocation, no token overlap on "to"); WI2
  asserts this rule fires on "stands/serves as a testament …" and does NOT fire
  on "is a testament to …" (which `a-testament-to` owns), and that
  `a-testament-to` does NOT fire on a "stands as a testament" sentence that has
  no "to" continuation.
- `rich-tapestry` — `(?i)\brich tapestry\b` — source: WP:AISIGNS era list
  ("tapestry") plus the page's "rich tapestry of" worked example. Narrowed to
  the collocation; **distinct** from `offenders.toml:149` `tapestry-of` (pin the
  disjointness in the Decision Log; WI2 asserts the `rich tapestry` rule does
  NOT fire on the bare "tapestry of light" that `tapestry-of` owns).
- `vital-role` — `(?i)\b(?:plays?|played) a (?:vital|pivotal|crucial|key)
  role\b` — source: WP:AISIGNS AITREND "a vital/significant/crucial/pivotal/key
  role/moment". Collocational template, safe for fiction.

EXCLUDE (do NOT ship as rules; record the exclusion in the Decision Log): bare
`delve`, bare `nestled`, bare `boasts`. WP:AISIGNS lists `nestled`/`boasts a`
under AIPEACOCK as words recurring in legitimate prose, and records `delve`
"dropped off sharply in 2025". `detect.py` has no semantic gate
(`detect.py:147-200`), so these fire on ordinary fiction. If the maintainer
later wants `boasts`, it must be the AI-ism collocation with a non-zero
threshold and a stated false-positive rationale — not the bare word.

If a candidate cannot be expressed under the v1 schema without a schema bump,
drop it and record why — do not bump the schema.

Validation:

- `uv run python -c "from novel_ralph_skill.rulepack import load_rulepack; from
  novel_ralph_skill.commands._desloppify_report import ai_isms_pack_path;
  print(load_rulepack(ai_isms_pack_path()).pack)"` prints `ai-isms`. (The
  resolver `ai_isms_pack_path` is added in this work item alongside the pack,
  in `_desloppify_report.py`, returning the `Traversable` for the packaged file.)
- `make all` green.

Docs to read: design §6.1, §6.2; developers' guide "Rule packs and the loader
boundary"; `offenders.toml` as the structural template.
Skills to load: `python-router` (then `python-data-shapes` for the frozen-pack
shape it loads into; `python-types-and-apis` for the `Traversable` resolver
signature).

### Work Item 2 — pin the pack with a validation suite

Add `tests/test_ai_isms_pack.py`, mirroring `tests/test_offenders_pack.py`. It
must:

- Assert the pack loads with name `ai-isms` and `schema_version == 1`.
- Pin the exact rule-id set (so a dropped or added row is red), and the
  `(id, threshold, basis)` triple per row transcribed from the pack.
- Assert the ai-isms rule-id set is **disjoint** from the offenders rule-id set
  (`frozenset(ai_isms_ids).isdisjoint(offenders_ids)`), guarding against
  double-counting (Risk row "duplicates an offenders row").
- Provide, per rule, one crafted positive (`>= 1` match) and **at least two**
  crafted negatives (0 matches): (a) the deliberate out-of-scope negative the
  narrowing implies, and (b) a sentence of **ordinary fiction** that uses the
  rule's surface tokens in a non-AI way, demonstrating the rule does not fire on
  baseline English (the BP2 acceptance evidence — a self-selected straw negative
  is insufficient). Concretely: `rich-tapestry` negative on the bare
  "tapestry of light" that `offenders.toml:149` `tapestry-of` owns AND on a
  fiction sentence using "tapestry" alone ("a tapestry hung on the wall");
  `stands-as-a-testament` positive on "the bridge stands as a testament to the
  city" (matches "stands as a testament"), negative (a) on "this is a testament
  to her skill" — the `is`-led phrase the dropped branch would have wrongly
  claimed, which this rule must NOT fire on (it is `a-testament-to`'s, and WI2
  asserts `a-testament-to` DOES fire on it), and negative (b) on a sentence
  where "testament" is the legal/literal noun ("the will was his last
  testament"); `vital-role` negative on a fiction sentence with "role" not in
  the collocation ("she rehearsed her role"). These are unit/example tests over
  the compiled patterns, not over `desloppify`.
- Assert every pattern compiles under `re.compile` with no flags — inline `(?i)`
  only (loader parity), as the offenders suite does. This pins the deliberate
  casing divergence (Decision Log): the divergence is in the inline `(?i)`, not
  in any compile flag.
- Do NOT pin the Tier B id-set as canonical until the maintainer has ratified
  membership (Tolerance). If only Tier A ships, the id-set assertion pins Tier A;
  Tier B rows are added with their tests when ratified.

Validation:

- `uv run pytest tests/test_ai_isms_pack.py -q` passes; each new positive fails
  before the corresponding row exists and passes after (write the test row,
  watch it fail against an empty pack, then add the row).
- `make all` green.

Docs to read: AGENTS.md "Python verification and testing" (unit + example
discipline; snapshots only for stable boundaries); `test_offenders_pack.py`.
Skills to load: `python-router` → `python-testing` (parametrization, ids).

### Work Item 3 — Hypothesis property test for robustness

Add property coverage in `tests/test_ai_isms_pack.py` (or a sibling
`tests/test_ai_isms_properties.py` if the first nears its file boundary),
mirroring `tests/test_rulepack_properties.py`. The properties:

- For any permutation of the pack's rules fed through `parse_rulepack`, the pack
  still loads and every pattern compiles — a structural-robustness invariant
  over orderings (AGENTS.md: property tests where an invariant ranges over
  orderings).
- No rule has a negative threshold and every `per_page` rule (if any) carries a
  positive `page_words` — an invariant the loader already enforces, restated as
  a property so a future hand-edit that violates it is caught at the pack level.

Use the `hypothesis` skill to keep strategies inside the data the pack actually
contains (avoid the filtering trap; draw from the loaded rule list rather than
synthesising arbitrary regexes). This is example-plus-property; do **not** add
mutation testing (mutmut) — there is no new production logic to mutate, only
data and a one-line resolver.

Validation:

- `uv run pytest tests/test_ai_isms_pack.py tests/test_ai_isms_properties.py -q`
  (whichever holds the properties) passes.
- `make all` green.

Docs to read: `test_rulepack_properties.py`; AGENTS.md property-test rule.
Skills to load: `python-router` → `python-verification` (to confirm Hypothesis
is the right adversary here and mutmut/CrossHair are not), then `hypothesis`.

### Work Item 4 — prove the pack travels in the wheel (e2e + behavioural)

Two additions:

1. A behavioural test (fast, no wheel) asserting `desloppify --pack
   <ai_isms_pack_path>` over an in-tree `working/` fixture exits `4` and names
   an ai-ism (e.g. `load-bearing`) in `result.violations`, and exits `0` over
   clean prose. Drive it through the `desloppify` app the way
   `tests/test_desloppify_command.py` does, passing the packaged pack path. This
   proves the pack is usable through the documented `--pack` flag.
2. A POSIX-only, `slow`-marked wheel e2e in `tests/test_desloppify_e2e.py` (or a
   sibling `tests/test_ai_isms_e2e.py`), mirroring
   `test_installed_desloppify_flags_offender`: build the wheel, install into a
   throwaway venv, materialize a `working/` tree via `baseline_tree`, write an
   ai-ism-bearing draft, and run the installed `desloppify --pack
   <installed-site-packages>/novel_ralph_skill/rulepack/packs/ai-isms.toml` —
   resolved by importing the installed package's resolver inside the subprocess,
   or by passing the resolved path — through a `single_program_catalogue` that
   registers the absolute script path. Assert exit `4` and the ai-ism in
   `violations`. Skip off POSIX (ADR-006); `@pytest.mark.timeout(180)` overrides
   the 30s default (verified `pytest-timeout` behaviour).

This is the defence of the high-severity "pack not in wheel" risk: it proves
the packaged `ai-isms.toml` resolves through `importlib.resources` after a real
install, exactly as the offenders e2e proves for `offenders.toml`.

Validation:

- `uv run pytest tests/test_desloppify_command.py -q` (or the new behavioural
  test file) passes — fast path.
- `uv run pytest -m slow -q` runs the wheel e2e on POSIX and passes; off POSIX
  it is skipped with the ADR-006 reason.
- `make all` green (the slow e2e runs under `make test`).

Docs to read: `tests/test_desloppify_e2e.py`; ADR-006; `tests/conftest.py` and
`tests/corpus_fixtures.py` for the fixtures.
Skills to load: `python-router` → `python-testing` (e2e/marks), and
`domain-cli-and-daemons` for the subprocess/console-script lifecycle framing.

### Work Item 5 — document cadence and ownership; resolve Q5

Prose-only, the Q5 resolution. Edits:

- `docs/developers-guide.md`: extend "Rule packs and the loader boundary" with a
  subsection naming the shipped `ai-isms.toml`, stating it is opt-in via
  `--pack` (default stays `offenders.toml`), and recording the **update
  cadence and ownership**: the skill maintainer owns the pack; it is reviewed on
  a stated schedule (e.g. each release, or at least annually) as tells emerge or
  go stale; adding or retiring a tell is a data edit plus its positive/negative
  test row, never a code change; a schema change (not expected) would bump
  `RULEPACK_SCHEMA_VERSION`. The subsection MUST also record the **membership
  policy** so the next maintainer does not invent tells: each new tell must be
  cited to an authoritative source (the design's named examples, or a dated AI-
  ism field guide such as WP:AISIGNS,
  <https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>), and MUST be
  **collocational** — a bare standalone English word (e.g. `delve`, `nestled`,
  `boasts`) is rejected because `detect.py` applies no semantic gate and such a
  rule fires on legitimate prose. Cite design §6.2 and §6.1 (the casing
  divergence: the pack uses inline `(?i)` for manuscript capitalization, unlike
  the case-sensitive §6.1 illustration).
- `docs/users-guide.md`: a one-line note in the `desloppify` section that an
  ai-isms pack ships and is selected with `--pack`.
- `docs/novel-ralph-harness-design.md` §6.2: a sentence pointing at the
  developers' guide for the concrete cadence/ownership, so the design records
  that Q5 is resolved.
- `docs/terms-of-reference.md` Q5: mark resolved, citing the developers' guide
  section.
- `skill/novel-ralph/references/desloppify-checklist.md`: a pointer note that
  the lexical AI-isms are now enforceable via the `ai-isms.toml` pack and where
  it lives, so the drafting loop can invoke it. (Keep the prose checklist; the
  pack mechanizes the lexical subset.)

Validation:

- `make markdownlint` passes on every edited Markdown file.
- `make nixie` passes (no Mermaid is added, but run it per the workflow rule for
  Markdown changes).
- `make fmt` reflows the prose to 80 columns; re-run `make markdownlint` after.
- `make all` green.

Docs to read: AGENTS.md "Markdown guidance" and "Project documentation";
`docs/documentation-style-guide.md`; `docs/terms-of-reference.md` Q5.
Skills to load: `en-gb-oxendict` (Oxford spelling enforcement on the new prose).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-1`.

1. Confirm the branch and clean tree:

        $ git branch --show
        roadmap-7-1-1
        $ git status --porcelain   # expect empty before starting

2. Work Item 1: author the pack and add `ai_isms_pack_path`. Verify it loads:

        $ uv run python -c "$(printf '%s\n' \
            'from novel_ralph_skill.commands._desloppify_report import ai_isms_pack_path' \
            'from novel_ralph_skill.rulepack import load_rulepack' \
            'p = load_rulepack(ai_isms_pack_path())' \
            'print(p.pack, len(p.rules))')"
        ai-isms <N>

   Then `make all`; commit (gate first).

3. Work Item 2: add `tests/test_ai_isms_pack.py`. Run it red against the
   smallest pack, fill rows, run green:

        $ uv run pytest tests/test_ai_isms_pack.py -q
        ... passed

   Then `make all`; commit.

4. Work Item 3: add the property test(s); run:

        $ uv run pytest tests/test_ai_isms_pack.py tests/test_ai_isms_properties.py -q
        ... passed

   Then `make all`; commit.

5. Work Item 4: add the behavioural test and the wheel e2e:

        $ uv run pytest tests/test_desloppify_command.py -q     # fast
        ... passed
        $ uv run pytest -m slow -q                              # POSIX e2e
        ... passed   (or skipped off POSIX)

   Then `make all`; commit.

6. Work Item 5: edit the docs and skill reference. Then:

        $ make markdownlint && make nixie && make all
        # all three gates exit 0

   Commit.

Each commit is gated by `make all` per the workflow standing rule; commit only
when the user has approved the plan and asked to proceed.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `tests/test_ai_isms_pack.py` (and the property file) pass; the
  `desloppify --pack` behavioural test exits 4 on an ai-ism and 0 on clean
  prose; the POSIX wheel e2e proves the packaged pack travels and exits 4.
  Before each new test exists it fails (red); after the pack/row lands it passes
  (green).
- Lint/typecheck: `make all` (build, check-fmt, lint, typecheck, test) is green
  — Ruff, `interrogate` 100%, Pylint, `pyright`/`ty`.
- Docs: `make markdownlint` and `make nixie` pass on every edited Markdown file.
- en-GB Oxford spelling throughout new prose, comments, and pack comments.

Quality method (how we check):

- Local: `make all`; for the doc work items also `make markdownlint` and
  `make nixie`. The same gates run in CI (`.github/workflows/ci.yml`).
- Behavioural acceptance: `uv run desloppify --pack
  novel_ralph_skill/rulepack/packs/ai-isms.toml` in a tree whose draft contains
  "this load-bearing paragraph" exits 4 and lists `load-bearing` in
  `result.violations`; the same over clean prose exits 0.

## Idempotence and recovery

- Authoring the pack and adding tests is additive; re-running any work item is
  safe. The pack file is overwritten wholesale on re-edit; no migration.
- The wheel e2e builds into a `tmp_path` venv and wheel dir that pytest discards;
  re-running rebuilds cleanly. If a wheel build fails mid-run, delete the
  `tmp_path` (pytest does this between runs) and re-run.
- No `working/` tree or `state.toml` is mutated by any step (detect-only,
  ADR-001); the e2e materializes throwaway trees under `tmp_path`.
- If a commit's gate fails, fix forward on the same work item; do not advance.

## Interfaces and dependencies

- New data file: `novel_ralph_skill/rulepack/packs/ai-isms.toml`, a v1 rule pack
  (`schema_version = 1`, `pack = "ai-isms"`, `[[rule]]` array) consumed by the
  existing `novel_ralph_skill.rulepack.load_rulepack`.
- New resolver (if added): in
  `novel_ralph_skill/commands/_desloppify_report.py`:

        def ai_isms_pack_path() -> Traversable:
            """Return the packaged ``ai-isms.toml`` resource (design §6.2)."""
            return importlib.resources.files(
                "novel_ralph_skill.rulepack.packs"
            ).joinpath("ai-isms.toml")

  Returns `importlib.resources.abc.Traversable` (the honest type
  `load_rulepack` accepts), mirroring `offenders_pack_path`.
- Reused, unchanged: `novel_ralph_skill.rulepack.{load_rulepack, RulePack, Rule,
  RuleBasis}`; `novel_ralph_skill.rulepack.detect.detect`; the `desloppify`
  Cyclopts app and its `--pack` flag; the test fixtures `baseline_tree`,
  `single_program_catalogue`, `venv_scripts_dir`.
- Dependencies: no new third-party dependency. `pytest`, `syrupy`, `cuprum`
  (0.1.0), `hypothesis`, `uv` are already locked dev dependencies.

## Revision note

- 2026-06-24: initial DRAFT. Decomposed roadmap 7.1.1 into five ordered work
  items (pack data, validation suite, property test, wheel e2e, cadence docs),
  pinned every external behaviour (cuprum 0.1.0 catalogue/run APIs against the
  cuprum source; Hatch default wheel inclusion against hatch.pypa.io;
  Cyclopts `--pack` and `pytest-timeout` per-test override against in-repo
  proof), and scoped the task to data + documentation with no loader/engine
  change.
- 2026-06-24 (round 2, design-review fixes). Three blocking points resolved:
  (1) Tell-set sourcing was uncited and falsely attributed to the checklist.
  Verified against source that the design names only two usable tells
  (`load-bearing`, `a testament to`; the third, "navigate the complexities", is
  already `offenders.toml:167`) and the checklist §6 table IS `offenders.toml`,
  supplying no extra vocabulary. Retracted the checklist claim and the "no
  undecided forks" assertion; reframed WI1 into Tier A (design-sourced) and
  Tier B (each row cited to a named WP:AISIGNS list,
  <https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>, scraped
  2026-06-24); explicitly tripped the Tell-set membership Tolerance and made
  Tier B membership the maintainer's to ratify before the tests pin a canonical
  id-set. (2) Over-matching bare words: dropped bare `nestled`, `boasts`,
  `delve` (WP:AISIGNS lists them as legitimate-prose / AIPEACOCK words, and
  `delve` "dropped off sharply in 2025"); kept only collocational tells; WI2 now
  requires a second negative drawn from ordinary fiction per rule as
  false-positive evidence. (3) Casing divergence: stated explicitly that the
  pack diverges from design §6.1's case-sensitive `\bload-bearing\b` by adding
  inline `(?i)` (offenders parity + manuscript capitalization), pinned in the
  Decision Log and the pack file header, with WI2 asserting no `re` compile
  flags (inline `(?i)` only). One open authoring choice remains and is honestly
  flagged: Tier B membership, owned by the maintainer per Tolerance.
- 2026-06-24 (round 3, design-review fixes). Two blocking points resolved:
  (1) `is-a-testament` pattern was self-contradictory. The shipped
  `(?i)\b(?:is|stands|serves) as a testament\b` has a dead `is` branch:
  verified against `re`, the `is` alternative matches only the ungrammatical
  "is **as** a testament" and never "is a testament to" (which is already
  covered by Tier A `a-testament-to`, also verified). The WI2 assertion that
  "both surface forms fire on their own positive" was therefore unsatisfiable
  for an `is`-led positive. Dropped the `is` branch
  (`(?i)\b(?:stands|serves) as a testament\b`), renamed the rule
  `stands-as-a-testament`, and restated WI1/WI2 so the only positive is
  "stands/serves as a testament" (the genuinely new coverage over
  `a-testament-to`) and the negatives assert this rule does NOT fire on "is a
  testament to …" while `a-testament-to` DOES. (2) Decision Log and WI1
  mis-cited `docs/developers-guide.md:595` as mirroring §6.1's case-sensitive
  `\bload-bearing\b`. Verified: the guide's "Rule packs and the loader
  boundary" worked example shows `\btapestry\b` at line 595 and `\bdelve\b` at
  line 602 (both case-sensitive), not a `load-bearing` pattern. Corrected both
  citations to the actual `tapestry`/`delve` example lines and named the
  section.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
review and audit of step 7.1. Execute each as a small addendum pass — no plan or
design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial
follow-ups — wiring the shipped pack to a symbolic `--pack ai-isms` selector
(roadmap 7.1.6) and the multi-pack invocation surface (roadmap 7.1.7) — warrant
their own plans and are filed as full step-7.1 tasks; these two are the small
data-contract and documentation fixes only.

- [x] 7.1.1.1 — Capture the maintainer's explicit ratification of the Tier B
  ai-isms membership (from review:7.1.1, low). Tier B
  (`stands-as-a-testament`, `rich-tapestry`, `vital-role`) shipped as
  "ratified-by-plan" because the maintainer was unreachable in the autonomous
  run (Decision Log, 2026-06-24). Obtain and record the human maintainer's
  explicit ratification of the shipped tell set in the developers' guide
  membership policy (or this Decision Log), closing the maintainer-owned
  data-contract loop the plan opened. Prose-only; gate with `make markdownlint`
  and `make nixie`.
- [x] 7.1.1.2 — Note the one-pack-per-run limit in the users' guide and resolve
  the developers' guide combine-packs cross-reference (from audit:7.1.1, low).
  `docs/developers-guide.md` says combining both packs in one invocation "is a
  separate roadmap item and is not yet supported" but the item was unfiled;
  point that cross-reference at the multi-pack task (roadmap 7.1.7) and add a
  one-line note to the `desloppify` users' guide section that a run scans a
  single pack. Prose-only; gate with `make markdownlint` and `make nixie`.
