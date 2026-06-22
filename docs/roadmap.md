# novel-ralph harness roadmap

This roadmap translates the deterministic-spine design into an outcome-oriented
delivery sequence. It does not promise dates. Each phase carries one testable
idea at the GIST level: the steps underneath a phase work toward validating or
falsifying that idea, and the tasks are concrete, review-sized execution units.
The primary design document is `docs/novel-ralph-harness-design.md`; the
problem statement is `docs/terms-of-reference.md`. Architectural decisions are
recorded as ADRs in `docs/`, named `adr-NNN-short-description.md` per the
documentation style guide, as the foundational phase ratifies them.

The slices are ordered by the controlling decision in the design (§1): the
deterministic spine ships first as five installed, tested commands, then the
judgemental architecture (the device ledger, the configurable AI-isms packs,
the line editor, and the clean-context sub-agents) follows in the
deferred-extensions phase. Within the spine, `novel-state` leads because it
exercises the most architecture — the validated schema, the lossless TOML
round-trip, atomic writes, and disk-authoritative reconciliation — that every
later slice reuses.

## 1. Foundational contracts and command spine

Idea: if the rebuild settles its packaging boundary, its TOML round-trip
mechanism, and its shared command contract before any command is built, the
five slices can converge on one coherent v1 spine instead of each reworking the
envelope, the exit-code policy, and the serialisation strategy.

This phase produces no narrative-facing capability. It ratifies the
hard-to-reverse decisions the design names, stands up the console-script
packaging in `novel_ralph_skill`, and builds the shared contract scaffolding
and test corpus that the slices depend on.

### 1.1. Ratify the decisions that would otherwise force rework

This step answers which architectural choices are fixed before code lands. Its
outcome informs every command's interface and the serialisation all mutators
share. See novel-ralph-harness-design.md §1, §3, and §5.3.

- [x] 1.1.1. Record the deterministic-and-judgemental boundary as an ADR.
  - Capture the controlling rule: scripts detect and report; the model
    adjudicates. No command makes a narrative judgement.
  - See novel-ralph-harness-design.md §1.
  - Success: one accepted ADR states the boundary and the legal crossings,
    and is cited by every later slice.
- [x] 1.1.2. Record the TOML round-trip decision as an ADR.
  - Requires 1.1.1.
  - Select `tomlkit` over an owned comment-preserving serialiser, with the
    reasoning from the design.
  - See novel-ralph-harness-design.md §5.3.
  - Success: the ADR resolves open question Q1 and fixes the dependency every
    mutator builds on.
- [x] 1.1.3. Record the shared interface contract as an ADR.
  - Requires 1.1.1.
  - Fix the JSON envelope, the `--human` flag, the checker-and-mutator
    segregation, and the disambiguated exit-code table: 0 success, 1 benign
    negative (predicate not yet satisfied; the loop continues), 2 usage error,
    3 state or input error, 4 actionable finding requiring agent intervention
    (desloppify violations, compile divergence, reconciliation conflict).
  - Settle the structured-error shape: machine-actionable data lives in
    `result`; `messages` is human prose the harness never parses. Record the
    relation between the three `schema_version` fields (envelope, state, rule
    pack) and that they evolve independently.
  - See novel-ralph-harness-design.md §3.1, §3.2, and §3.3.
  - Success: the ADR resolves open question Q2; the five slices implement the
    same contract — including the code-1-versus-code-4 split — without
    renegotiating it.
- [x] 1.1.4. Record distribution as installed console-scripts as an ADR.
  - Requires 1.1.1.
  - Capture why the commands ship as console-scripts in `novel_ralph_skill`
    (terms-of-reference C3) rather than as self-contained `uv` scripts.
  - See novel-ralph-harness-design.md §2.2 and §4.
  - Success: an accepted ADR records the distribution decision and its
    rationale for future contributors.
- [x] 1.1.5. Record the command-surface shape as an ADR.
  - Requires 1.1.4.
  - Weigh five separate console-scripts against a single `novel` multiplexer,
    and record the decision to ship five named commands — each mapping 1:1 onto
    a deterministic operation, with the shared envelope enforced by the §1.3
    scaffolding rather than by a single entry point — together with the
    multiplexer trade-offs considered.
  - See novel-ralph-harness-design.md §4.
  - Success: the trade is recorded before 1.2.1 wires the entry points, so the
    five-script choice is deliberate rather than defaulted.

### 1.2. Stand up the console-script packaging boundary

This step answers whether the intended packaging — installed console-scripts in
the existing `novel_ralph_skill` package — supports local development and the
harness's invocation model. See novel-ralph-harness-design.md §2.2 and §4, and
docs/scripting-standards.md.

- [x] 1.2.1. Wire the five console-script entry points in `pyproject.toml`.
  - Requires 1.1.3 and 1.1.5.
  - Register `novel-state`, `novel-done`, `novel-compile`, `desloppify`, and
    `wordcount` against stub Cyclopts applications that exit 2 until
    implemented.
  - See novel-ralph-harness-design.md §4.
  - Success: a wheel build installs all five commands; each is invocable on
    `PATH` and reports a usage error rather than crashing.
- [x] 1.2.2. Add `tomlkit` to the package dependencies and confirm the build.
  - Requires 1.1.2 and 1.2.1.
  - Success: `make test` and the quality gates in AGENTS.md pass against the
    extended dependency set.
- [x] 1.2.3. Decide and enforce a cross-platform policy for the console-scripts
  e2e test.
  - Remediation (source: review:1.2.1; severity: low). `test_console_scripts_e2e.py`
    is only half-portable on Windows: the win32 branch resolves scripts via the
    `nt_user` sysconfig scheme (a roaming user path, not the venv `Scripts/` dir
    uv creates) and looks up `scripts_dir / command_name` without the `.exe`
    suffix, so either commit to Linux-only execution or make the lookup truly
    portable.
  - [ ] 1.2.3.1. Index ADR 006 and the `docs/issues/` and `docs/execplans/`
    sets in `docs/contents.md`.
    - Addendum (from audit:1.2.6; severity: low). The documentation map omits
      the POSIX console-scripts ADR and the growing audit-trail and per-task
      plan sets, leaving them undiscoverable. Execute as a lightweight addendum
      pass against the 1.2.3 execplan: no plan or design-review cycle, just the
      change, the gates, and a merge.
- [x] 1.2.4. Introduce a single source of truth for the five command names.
  - Remediation (source: audit:1.2.1; severity: medium). The command-name list is
    duplicated across `stub.py`, `pyproject.toml`, and three test modules; a
    package registry consumed by the entry points and tests, asserted against
    `[project.scripts]`, removes the drift risk while the surface is still five
    thin stubs.
- [x] 1.2.5. Establish a docstring-coverage gate (interrogate) for the Python
  package.
  - Remediation (source: audit:1.2.1; severity: low). `interrogate` is a dev
    dependency with no configuration or Makefile/CI invocation, so docstring
    coverage is unenforced; locking the standard in now, while the modules are
    well documented, is cheapest before the command bodies expand the surface.
- [x] 1.2.6. Remove the dead `tomli_w` snippet from `state-layout.md` and
  reconcile the premature "is removed" claims.
  - Remediation (source: review:1.2.2; severity: medium). The failed `tomli_w`
    snippet still survives at `skill/novel-ralph/references/state-layout.md:229`
    and `:235`, yet ADR-002 line 77 and design §5.3 already assert it "is removed"
    while ADR-002 line 22 says it "even carries" it; delete the snippet (or
    rewrite it to `tomlkit`) and reconcile the ADR-002 and design wording, as no
    existing task owns this removal.
- [x] 1.2.7. Introduce `tests/conftest.py` to consolidate the shared test
  scaffolding.
  - Remediation (source: audit:1.2.6; severity: medium). The same project-root,
    `pyproject` parse, repo-file reader, single-program catalogue,
    `_venv_scripts_dir`, and TOML-table accessor are duplicated across the six
    test modules and re-flagged in audit-1.2.1, 1.2.3, 1.2.4, 1.2.5, and 1.2.6;
    a shared `conftest` removes the drift and cross-module private imports in one
    move while the surface is still small.
- [x] 1.2.8. Broaden the state-layout direct-edit guard to reject any
  hand-edit recipe, not just `tomli_w`.
  - Remediation (source: review:1.2.6; severity: low). The 1.2.6 guard pins only
    the literal `tomli_w` substrings, so a future `tomlkit`- or `tomllib`-based
    hand-edit of `state.toml` would pass green while re-opening the design §4.1
    "direct editing eliminated" violation; widen the guard to forbid any direct
    `state.toml`-write recipe, coordinated with task 6.2.3 which rewrites the
    reference prose to point at the `novel-state` commands.
  - [ ] 1.2.8.1. Enforce a single code-fence style (MD048) in the markdownlint
    configuration.
    - Addendum (from review:1.2.8; severity: low). markdownlint accepts tilde
      fences, which made the guard bypass reachable; pinning backtick-only
      fences repo-wide is defence-in-depth. Lightweight addendum pass against
      the 1.2.8 execplan.
  - [ ] 1.2.8.2. Split `tests/test_state_layout_reference.py` before it breaches
    the 400-line module cap.
    - Addendum (from review:1.2.8; severity: low). At 400 of 400 lines the next
      planted row or negative test breaks the AGENTS.md module-size gate;
      extract the recipe corpus or scanner helpers into a small support module
      (coordinate with the 1.2.7 shared conftest). Lightweight addendum pass.
  - [ ] 1.2.8.3. Distinguish the live `state.toml` from its atomic `.new`
    sibling in the state-layout guard.
    - Addendum (from review:1.2.8; severity: medium). `_STATE_FILE` matches as a
      bare substring, so a fenced write-then-rename illustration (design §3.4,
      §5.3) is false-flagged because `state.toml` is a substring of
      `state.toml.new`; anchor the live-file match on a word, quote, or
      end-of-line boundary and add a negative test. Lightweight addendum pass.
  - [ ] 1.2.8.4. Reconcile the developers' guide state-layout guard section with
    the merged 1.2.8 code.
    - Addendum (from audit:1.2.8; severity: medium). The guide's write-token
      list omits `.write_bytes`/`.writelines` and the executable info-string
      list omits `python3`/`py3`/`pycon`, all of which the code scans; a
      one-paragraph edit keeps the prose truthful. Lightweight addendum pass.
- [x] 1.2.9. Tighten the `read_repo_text` fixture signature from
  `Callable[..., str]` to a precise `(*parts: str) -> str` form.
  - Remediation (source: review:1.2.7; severity: low). The ellipsis in
    `cabc.Callable[..., str]` disables argument-count and type checking at every
    call site; a documented variadic callable signature restores the static
    arg-shape guarantee the plan's Interfaces section preferred without changing
    behaviour.
- [x] 1.2.10. Replace the bare `sh.make(...)` expression statement in
  `test_conftest_helpers` with an explicit assertion.
  - Remediation (source: review:1.2.7; severity: low). A statement that discards
    its result and asserts nothing reads as dead code and may be flagged by a
    linter; making the "does not raise" intent explicit keeps the test's
    guarantee self-evident to maintainers.
- [x] 1.2.11. Migrate `test_contract_test_deps` onto the shared conftest
  fixtures and centralise dependency-name normalisation.
  - Remediation (source: audit:1.2.7; severity: medium). The 1.2.7 consolidation
    left `test_contract_test_deps.py` re-parsing `pyproject` itself and carrying
    a second, weaker copy of the PEP 508 distribution-name normaliser; lifting a
    `dist_name` fixture into `conftest` and migrating the module onto the
    `pyproject`/`toml_table` fixtures removes both duplications in one move.

### 1.3. Build the shared contract scaffolding and test corpus

This step answers whether one envelope, output-mode switch, and exit-code
helper can serve all five commands. Its outcome removes per-command contract
drift and seeds the snapshot suite. See novel-ralph-harness-design.md §3 and §9.

- [x] 1.3.1. Implement the shared JSON-envelope and output-mode module.
  - Requires 1.1.3 and 1.2.1.
  - Provide the `command`, `schema_version`, `ok`, `working_dir`, `result`,
    and `messages` envelope, the `--human` rendering hook, and the exit-code
    mapping (0/1/2/3/4) as reusable helpers, with `result` carrying all
    machine-actionable data and `messages` carrying only human prose.
  - See novel-ralph-harness-design.md §3.1 and §3.2.
  - Success: a property-based test confirms `ok` is true only on exit 0; that
    each of the four non-zero codes is reported as `ok: false`; and that all
    five codes (0 success, 1 benign negative, 2 usage error, 3 state or input
    error, 4 actionable finding) map to the expected envelope semantics — a
    malformed invocation yields code 2, an unparseable or missing `state.toml`
    yields code 3, and codes 1 and 4 carry distinct, non-interchangeable
    meanings. A snapshot pins the envelope shape for each code.
  - [ ] 1.3.1.1. Extract a shared wrapper-app builder fixture for the contract
    run-driver tests and fold the residual conftest table accessors.
    - Addendum (from audit:1.2.8; severity: low). The four-flag Cyclopts
      `_build_app` is duplicated across `test_contract_runner` and
      `test_contract_properties`, and `_parse_scripts` duplicates an inline
      `toml_table` access; a `wrapper_app` fixture plus a `project_scripts`
      walker in `conftest` makes both live once. Lightweight addendum pass
      against the 1.3.1 execplan.
- [ ] 1.3.2. Build the on-disk `working/` fixture corpus.
  - Requires 1.2.1.
  - Provide reusable `tmp_path` fixtures spanning all eleven phase states,
    coherent and deliberately incoherent `state.toml` variants, and chapter
    drafts with `done.flag` permutations.
  - See novel-ralph-harness-design.md §5 and §9.
  - Success: the corpus is consumed unchanged by the slice suites in
    phases 2-6, so no slice re-rolls fixtures.

## 2. Vertical slice 1: trustworthy state through validated mutators

Idea: if all state mutation hides behind validated subcommands that refuse to
write an incoherent `state.toml` and can reconstruct state from disk, the
silent phase drift and hand-typed counts in the field report become impossible,
and every later slice can trust the schema as the single source of truth.

This slice delivers `novel-state` end-to-end: the validated schema, the five
subcommands, the lossless TOML round-trip, atomic writes, and
disk-authoritative reconciliation. It is sequenced first because its artefacts
— the schema, the validator, and the round-trip — underpin `novel-done`,
`novel-compile`, and `wordcount`.

### 2.1. Establish the validated schema and its invariants

This step answers whether the `state.toml` schema can be expressed as a typed
structure whose invariants a validator enforces. Its outcome is the single
source of truth the done predicate and the recount logic read. See
novel-ralph-harness-design.md §5.1 and §5.2.

- [ ] 2.1.1. Implement the typed `state.toml` schema and the phase enum.
  - Requires steps 1.1-1.3.
  - Model the schema from `state-layout.md` with the dead per-chapter
    `plan.md` reference removed, encode the eleven-member phase enum in order,
    and add the three new fields: the `[chapters]` manifest (number, slug,
    title, target words), `[drafting.critic].convergence_target`, and the
    `[pending_turn]` intent record. Anchor all manuscript paths under
    `working/manuscript/`.
  - See novel-ralph-harness-design.md §5.1 and §8.
  - Success: representative states from the §1.3.2 corpus parse into the typed
    structure without loss, including the manifest and the pending-turn record.
- [ ] 2.1.2. Implement the invariant validator behind `novel-state check`.
  - Requires 2.1.1.
  - Enforce phase membership, the completed-prefix ordering, the
    by-chapter-sum-to-current rule, cursor coherence, and
    gate-boolean-versus-ratio consistency. Bound `consecutive_clean` by the
    configured `convergence_target` ceiling (default 1, rejecting a target
    below 1) rather than a hard-coded 0–1 literal, so the convergence bar is a
    state-field change.
  - See novel-ralph-harness-design.md §5.2 and §2.3.
  - Success: a `hypothesis` suite over generated states shows `check` accepts
    exactly the states satisfying §5.2 and rejects the rest (the
    state-coherence property), and a state with `consecutive_clean` above its
    `convergence_target` is rejected while one within a raised target is
    accepted.

### 2.2. Deliver lossless, atomic state mutation

This step answers whether mutators can write validated state without losing
formatting or leaving a torn file on a crash. Its outcome is the write
discipline every mutator in the spine inherits. See
novel-ralph-harness-design.md §3.4, §4.1, and §5.3.

- [ ] 2.2.1. Implement the `tomlkit` round-trip and atomic write helper.
  - Requires 1.1.2 and 2.1.1.
  - Read, mutate, and re-serialise `state.toml` through `tomlkit`, writing via
    a temporary file in the target directory followed by `Path.replace`. Open a
    `[pending_turn]` intent record naming the operation and the paths it will
    write before touching any other file, and clear it only once every artefact
    is written and verified.
  - See novel-ralph-harness-design.md §5.3 and §3.4.
  - Success: a property-based test confirms a no-op mutate-and-write preserves
    on-disk formatting and comments byte-for-byte (the round-trip property), and
    a write interrupted before completion leaves a populated `[pending_turn]`
    record for the next turn to reconcile.
- [ ] 2.2.2. Implement `init`, `set-cursor`, and `advance-phase`.
  - Requires 2.1.2 and 2.2.1.
  - `init` creates `working/` and an initial state; `set-cursor` refuses
    incoherent cursors; `advance-phase` refuses skips and out-of-order
    completion. A refused mutator request returns exit 3 (state or input error,
    per ADR 003 and §3.2), not the benign-negative exit 1 the loop continues
    on, so the harness cannot mistake a rejected transition for progress.
  - See novel-ralph-harness-design.md §4.1 and §3.2.
  - Success: a behavioural scenario shows an out-of-order `advance-phase` is
    refused with exit 3 and leaves the prior state intact.

### 2.3. Deliver recount and disk-authoritative reconciliation

This step answers whether state can be re-derived from disk so it can never
drift from the manuscript. Its outcome retires hand-typed word counts and the
agent-improvised recovery routine. See novel-ralph-harness-design.md §4.1 and
§5.4.

- [ ] 2.3.1. Implement `recount` as a pure aggregation over chapter drafts.
  - Requires 2.2.1.
  - Re-derive `word_counts.current` and `by_chapter` from `draft.md` files and
    write the validated result.
  - See novel-ralph-harness-design.md §4.1.
  - Success: `recount` is idempotent — a second run on unchanged drafts writes
    an identical file — and the by-chapter values sum to the current total.
- [ ] 2.3.2. Implement read-only reconciliation detection in `check` and the
  disk-authoritative write in `reconcile`.
  - Requires 2.1.2 and 2.3.1.
  - In `check` (read-only), reconstruct intended state from on-disk evidence
    (`done.flag` presence, `compiled.md` contents) where disk is internally
    consistent, report the discrepancy and the reconciliation it implies in the
    payload, and exit 4 without writing. In `reconcile` (mutator), recompute the
    same reconciliation and write the reconciled state, appending a recovery
    entry to the log and deleting no file in `working/`. Assert the
    chapter-manifest-to-disk bijection in `check` — every `chapter-NN/draft.md`
    maps to exactly one manifest entry and vice versa, contiguous from 1. Handle
    an uncleared `[pending_turn]` by having `check` report whether the partial
    write should be completed or discarded according to what landed and
    `reconcile` carry it out. Refuse to auto-repair contradictory disk evidence
    (a `done.flag` beside an empty `draft.md`; a `compiled.md` referencing an
    absent chapter): both `check` and `reconcile` report, log, and exit 4.
  - See novel-ralph-harness-design.md §3.3, §5.2, and §5.4.
  - Success: a scenario where state claims a chapter is done but no `done.flag`
    exists is detected by `check` with exit 4 and repaired by `reconcile`, while
    `check` itself writes nothing; a non-bijective manifest and a
    contradictory-evidence tree are each reported with exit 4 rather than
    silently repaired (the loud-reconciliation requirement).

## 3. Vertical slice 2: a single-source done predicate

Idea: if the done predicate is the same code path the harness gates on, the
two-source divergence between the short-form and long-form predicates
disappears, and "check done every turn" becomes one trustworthy call.

This slice delivers `novel-done`: a per-clause predicate evaluated against
disk, including the hash-based compile-divergence check that a coincidentally
matching header count and word total cannot fool. It reuses the schema and
validator from phase 2.

### 3.1. Deliver the per-clause done predicate

This step answers whether every done clause can be evaluated deterministically
against disk and reported individually. Its outcome makes the predicate
auditable rather than a single opaque boolean. See
novel-ralph-harness-design.md §4.2 and §2.3.

- [ ] 3.1.1. Implement the per-clause predicate and its structured result.
  - Requires phase 2.
  - Evaluate `phase_is_done`, `final_pass_complete`, `all_chapters_flagged`,
    `knitting_gates_passed`, `compile_consistent`, and
    `no_unresolved_blockers`, reporting which clauses failed.
  - See novel-ralph-harness-design.md §4.2.
  - Success: each clause can be independently driven true and false from the
    §1.3.2 corpus, and the exit code is 0 only when every clause holds.
- [ ] 3.1.2. Implement the shared compile-and-hash routine and the
  compile-divergence clause.
  - Requires 3.1.1.
  - Build one compile-and-hash function that concatenates the chapter drafts in
    zero-padded chapter-index order and hashes the result, and call it from the
    `compile_consistent` clause to compare against `working/manuscript/compiled.md`
    rather than comparing header counts or word totals. `novel-compile` reuses
    this same function in phase 4 so the two cannot disagree. Report only the
    `compile_consistent` boolean, never per-chapter hashes, so the payload stays
    bounded as the chapter count grows. Drive the exit-code carve-out: when
    `compile_consistent` is the sole unmet clause, exit 4 (an actionable stale
    compile, matching `novel-compile --check`); while any drafting clause is
    still unmet, stay at exit 1.
  - See novel-ralph-harness-design.md §3.2, §4.2, and §2.3.
  - Success: a stale `compiled.md` whose header count and word total
    coincidentally match the drafts is still reported as divergent (the
    predicate-truthfulness property); the `novel-done` result size is
    independent of the chapter count; and an otherwise-complete tree with only a
    stale `compiled.md` exits 4 while a mid-draft tree exits 1.

## 4. Vertical slice 3: deterministic, outline-ordered compilation

Idea: if `compiled.md` is regenerated deterministically in outline order with
consistent separators, the ordering ambiguity of a directory glob disappears
and the compile-consistency clause has an authoritative artefact to check
against.

This slice delivers `novel-compile` as both a mutator and, under `--check`, a
read-only checker. It shares the hashing approach with the phase 3 divergence
clause so the two never disagree.

### 4.1. Deliver outline-ordered compilation and its checker

This step answers whether compilation can be made deterministic and verifiable
without writing. Its outcome resolves assumption A5 — ordering is the
zero-padded chapter index, validated against the manifest — and gives
`novel-done` a stable artefact. See novel-ralph-harness-design.md §4.3 and §2.3.

- [ ] 4.1.1. Implement `novel-compile` ordered by the zero-padded chapter index.
  - Requires phase 2.
  - Concatenate chapter drafts in zero-padded chapter-index order with
    consistent separators, writing `working/manuscript/compiled.md` atomically,
    and exit 3 when the chapter manifest is absent or empty (no authoritative
    ordering). No outline prose is parsed.
  - See novel-ralph-harness-design.md §4.3 and §10.
  - Success: compilation is deterministic — identical drafts and manifest
    produce a byte-identical `compiled.md` — regardless of directory listing
    order.
- [ ] 4.1.2. Implement the `--check` read-only divergence checker.
  - Requires 4.1.1 and 3.1.2.
  - Report divergence by calling the shared compile-and-hash routine from
    3.1.2 — the same code path the `novel-done` compile clause uses — writing
    nothing and exiting 4 on divergence.
  - See novel-ralph-harness-design.md §3.3 and §4.3.
  - Success: `novel-compile --check` and the `novel-done` compile clause agree
    on every corpus fixture because they share one routine (the compile-fidelity
    property).

## 5. Vertical slice 4: deterministic slop detection

Idea: if the desloppify checklist runs as a versioned rule pack that emits
structured per-hit output, the improvised `grep` the field report blames — with
its spurious whole-file output, non-zero-on-zero-match breakage, and mid-scan
glob expansion — is replaced by a command the model can adjudicate against.

This slice delivers `desloppify` over the §6 high-frequency-offender table as
the first rule pack. It detects and reports only; it never edits and never
judges. The rule-pack schema it establishes is reused by the AI-isms and
device-ledger packs in the deferred phase.

### 5.1. Deliver the rule-pack engine and the first pack

This step answers whether detection rules can be expressed as versioned data
and applied uniformly across a chapter or the whole manuscript. Its outcome is
the rule-pack contract the later packs extend. See
novel-ralph-harness-design.md §4.4, §6.1, and §1.

- [ ] 5.1.1. Implement the versioned rule-pack loader and schema.
  - Requires steps 1.1-1.3.
  - Load a TOML pack of `pattern`, `threshold`, and `basis` rules, validating
    `schema_version` and rejecting malformed patterns with exit 2 naming the
    offending rule id.
  - See novel-ralph-harness-design.md §6.1 and §10.
  - Success: a pack with an invalid regular expression fails loudly, naming the
    rule, rather than silently skipping it.
- [ ] 5.1.2. Implement `desloppify` detection over the §6 offender table.
  - Requires 5.1.1.
  - Emit structured output per hit — phrase, count, density per N words,
    threshold, pass or fail, and line numbers — for a chapter or the whole
    manuscript, making zero edits. Exit 0 on a clean pass, 4 when violations are
    found (an actionable finding), and 2 on a usage error, so the three are
    distinguishable by exit code alone.
  - Verify with snapshot coverage of the envelope plus boundary examples (a hit
    exactly at threshold, a clean pass), not a full property-based or
    behavioural suite — the command is a pure aggregation (§9).
  - See novel-ralph-harness-design.md §4.4 and §9.
  - Success: clean prose exits 0, a manuscript with violations exits 4, and a
    malformed invocation exits 2 — each distinguishable without parsing JSON.

## 6. Vertical slice 5: derived word counts and gate triggers

Idea: if word counts and knitting-gate triggers are derived from disk on every
run, the repeated hand computation in the field report disappears and the 80%
gate can never fire late at 85%.

This slice delivers `wordcount` as a read-only checker reporting per-chapter
and cumulative figures alongside the next gate distance. It completes the
deterministic spine and feeds the knitting gate into the per-chapter pipeline.

### 6.1. Deliver word reporting and gate-distance computation

This step answers whether progress and gate proximity can be derived purely
from disk. Its outcome retires the last hand-computed determinism in the field
report. See novel-ralph-harness-design.md §4.5.

- [ ] 6.1.1. Implement `wordcount` reporting and gate-trigger derivation.
  - Requires phase 2.
  - Report per chapter and cumulatively: words, percentage of target, distance
    to the next knitting gate, and delta against the chapter target, deriving
    the 30%, 50%, and 80% gate triggers rather than noticing them late.
  - Verify with snapshot coverage of the envelope plus boundary examples (a
    manuscript exactly on each gate), not a full property-based or behavioural
    suite — the command is a pure aggregation (§9).
  - See novel-ralph-harness-design.md §4.5 and §9.
  - Success: at a manuscript exactly on a gate threshold the corresponding gate
    is reported as just reached, and the next-gate distance is non-negative.

### 6.2. Prove the spine end-to-end across the combinatorial surface

This step answers whether the five commands behave correctly across the full
`command × output-mode × phase` surface, not just in isolation. Its outcome is
the confidence the harness needs to gate on the spine unattended. See
novel-ralph-harness-design.md §2.3 and §9.

- [ ] 6.2.1. Build the combinatorial command-surface test suite.
  - Requires phase 5 and 6.1.1.
  - Snapshot the machine-mode JSON envelope per command, assert the `--human`
    mode for presence, and carry semantic assertions over the
    phase-dependent branches across the eleven phase states.
  - See novel-ralph-harness-design.md §9 and §2.3.
  - Success: the `command × output-mode × phase` matrix is covered, with the
    knowingly carried gaps (exhaustive phase cross-products) documented rather
    than silently omitted.
- [ ] 6.2.2. Build the end-to-end per-chapter deterministic-loop scenario.
  - Requires 6.2.1.
  - Drive a chapter from `recount` through `novel-done`, `wordcount`,
    `desloppify`, and `novel-compile --check` on a real `working/` tree,
    asserting the harness-facing flows from the design.
  - See novel-ralph-harness-design.md §7.2 and §9.
  - Success: a stale compile is caught, a crossed gate is reported, and an
    out-of-order phase advance is refused, all in one scripted pass.
- [ ] 6.2.3. Correct the documented skill defects and point the prose at the
  commands.
  - Requires phase 3.
  - Fix the `SKILL.md:107` phase mislabel (drafting is Phase 8, not Phase 7),
    reduce both prose copies of the done predicate to a pointer at `novel-done`,
    and remove the dead `state-layout.md:38` `plan.md` reference.
  - See novel-ralph-harness-design.md §8.
  - Success: `make markdownlint` passes on the edited skill files and no prose
    copy of the predicate survives to diverge.

## 7. Deferred extensions after the deterministic spine

Idea: if the deterministic spine is already trustworthy and boring to operate,
the project can evaluate the judgemental architecture — the device ledger, the
configurable AI-isms packs, the line editor, and the clean-context sub-agents —
on its craft value instead of letting it destabilise the spine.

These items are designed in the technical document but explicitly deferred from
v1, which delivers determinism parity only. Each is a lightweight step here,
built once the spine is in place.

### 7.1. Configurable detection packs

This step extends the phase 5 rule-pack engine with the moving-target and
per-novel packs the design defers. See novel-ralph-harness-design.md §6.2 and
§6.3.

- [ ] 7.1.1. Ship the versioned `ai-isms.toml` pack and update cadence.
  - Requires phase 5.
  - Carry the 2026 tell set as data the maintainer owns, with `schema_version`
    versioning, so new tells land without touching the command.
  - See novel-ralph-harness-design.md §6.2.
  - Success: resolves open question Q5; adding a tell is a data edit, not a
    code change.
- [ ] 7.1.2. Implement the per-novel `device-ledger.toml` enforcement.
  - Requires phase 5.
  - Enforce rationing — `max_count`, `allowed_chapters`,
    `retired_after_chapter`, `reserved_for_chapter` — recomputing current
    counts from disk every run so the ledger cannot drift.
  - See novel-ralph-harness-design.md §6.3.
  - Success: resolves open question Q3; a device spent beyond its ration is
    reported deterministically while the spend decision stays with the model.

### 7.2. Clean-context judgemental passes

This step builds the sub-agent architecture the design defers, sequenced after
the spine because adjudication depends on the deterministic detectors feeding
it. See novel-ralph-harness-design.md §7.

- [ ] 7.2.1. Implement the line-editor pass and its boundary.
  - Requires phase 5.
  - Run a clean-context copy-editor persona after `desloppify` and before the
    critic, scoped by the sentence-versus-scene boundary test, adjudicating
    passive-voice hits, filtering words, and micro show-don't-tell.
  - See novel-ralph-harness-design.md §7.1.
  - Success: resolves open question Q4; sentence-level fixes route to the line
    editor and scene-level fixes route to the critic, with separate prompts
    and outputs.
- [ ] 7.2.2. Wire the clean-context critic, knitting circle, and resumable
  fangirl into the per-chapter pipeline.
  - Requires 7.2.1 and phase 6.
  - Run the spiteful critic and knitting circle as clean-context sub-agents at
    peer capability, the fangirl as a resumable persistent agent, with the
    knitting circle gated by the `wordcount` triggers, and all adjudication
    returning to the orchestrator.
  - See novel-ralph-harness-design.md §7 and §7.2.
  - Success: each pass runs in the context the design assigns it, no sub-agent
    mutates state or manuscript directly, and the persona-degradation guards
    re-issue the prompt on praise drift.

### 7.3. Harden the state-layout reference guard

This step answers whether the state-layout direct-edit guard can be widened to
every executable recipe form and skill reference without false positives, once
the reference prose has been pointed at the `novel-state` commands. Its outcome
is a guard that cannot be bypassed by an alternative fence grammar or writer
idiom. These are deferred hardening extensions surfaced by the audits of step
1.2; they do not gate the deterministic spine and coordinate with task 6.2.3,
which rewrites the reference prose.

- [ ] 7.3.1. Extend the state-layout guard fence grammar to all CommonMark
  fence forms (tilde, four-or-more backticks, indented).
  - Requires 1.2.8 and 6.2.3.
  - The `re`-based fence matcher cannot see tilde, longer-backtick, or
    list-indented fences, a structural blind spot that could silently drop a
    recipe once the reference gains list-embedded examples; a stdlib dedent
    pre-pass or vetted lightweight fence parser hardens it without breaching the
    no-AST-dependency spirit.
  - Success: planted recipes in tilde, four-backtick, and indented fences are
    all caught; the no-AST-dependency constraint holds.
- [ ] 7.3.2. Extend the state-layout write-recipe guard to rename, move, and
  in-place writers across Python and shell.
  - Requires 1.2.8 and 6.2.3.
  - `os.rename`/`os.replace`, `shutil.move`/`shutil.copy`, `sed -i`, `dd of=`,
    `sponge`, and `cp`/`mv ... working/state.toml` all currently pass the guard
    clean even though they write the state file outside `novel-state`; a
    path-anchored write-verb heuristic closes the disclosed residual hole.
  - Success: each enumerated writer idiom against `working/state.toml` is
    rejected; legitimate non-state writes are not.
- [ ] 7.3.3. Extend the direct-edit guard to every skill reference that can
  carry executable recipes.
  - Requires 1.2.8.
  - 1.2.8 scoped the guard to `state-layout.md`; other references such as
    `done-conditions.md` contain executable fences and could grow a hand-edit
    recipe no guard would catch. A shared multi-file fence scanner closes that
    gap without per-file duplication.
  - Success: a planted hand-edit recipe in any executable-carrying reference is
    caught by a single shared scanner, with no per-file duplication.
- [ ] 7.3.4. Add a fuzz or property check that the guard's planted-recipe forms
  survive whitespace, quoting, and flag-order variation.
  - Requires 1.2.8.
  - The parametrized matrix encodes one concrete spelling per form, sharing the
    regex's own assumptions; a property test that mutates whitespace, quoting,
    and flag ordering around each planted recipe would catch anchor-too-tight
    regressions like the no-space redirect automatically.
  - Success: a property test over whitespace, quoting, and flag-order mutations
    of each planted recipe passes, demonstrating the matcher is not
    anchor-too-tight.
