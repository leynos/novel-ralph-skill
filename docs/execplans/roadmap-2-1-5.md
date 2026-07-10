# Promote a `by_chapter_override` divergent-table variant into the §1.3.2 corpus

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Roadmap task 2.1.3 proved the §5.2 validator enforces its two table-based
proxies — `gate-ratio-consistent` (whose numerator is `sum(by_chapter.values())`)
and `consecutive-clean-within-drafted` (whose ceiling is the count of
`by_chapter` entries greater than zero) — against a *live* draft count read from
the on-disk `chapter-NN/draft.md` bodies. That cross-check is genuinely live in
its code, but no §1.3.2 corpus tree currently sets `by_chapter_override`. On
every existing corpus tree the `[word_counts].by_chapter` table is numerically
equal to the on-disk drafts, so a *table*-reading mutant of the live reader
passes the whole-corpus agreement loop undetected. The 2.1.3 fix round had to
plug that hole with a one-off, module-local `divergent_table_tree` fixture built
inside `tests/test_validate_state_live_draft.py`, and a surviving mutant (live
reader rewritten to read the table) confirmed the gap was real.

After this change, the §1.3.2 corpus itself owns a first-class divergent-table
variant: a tree whose `[word_counts].by_chapter` table deliberately belies the
real `draft.md` bodies (the table over-counts both the drafted-words total and
the drafted-chapters count). The whole-corpus live-draft discrimination test
consumes that variant by fixture name through the standard corpus loop, the
live-reader-to-table-reader mutant is killed without any bespoke per-test
fixture, and the module-local `divergent_table_tree` fixture is removed. Success
is observable by running the test suite: the discrimination test passes while
sourcing its tree from the corpus, every existing corpus-agreement and
self-test suite stays green, and (optionally) a focused mutmut run shows the
live-reader mutant is killed.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the git worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-5`. Never edit
  the root/control worktree.
- Do **not** change the production validator
  `novel_ralph_skill/state/validate.py` or any `novel_ralph_skill/` source. This
  task is test-corpus and oracle data only. The validator's two table-based
  proxies are correct by design (developers-guide "Invariant validation"); the
  divergent tree exists to *exercise* the documented validator-versus-live
  disagreement, not to remove it.
- Keep the corpus's public surface contract stable: `CORPUS_INVARIANT_NAMES`
  (the thirteen-name vocabulary in `tests/working_corpus/_oracle.py`),
  `corpus_check`, and `novel_ralph_skill.state.PURE_STATE_INVARIANT_NAMES` must
  not change. The new variant must not add or rename any invariant name.
- The new variant must **not** be a member of `INCOHERENT_VARIANTS`. Each
  `INCOHERENT_VARIANTS` member must break exactly one named invariant under
  `corpus_check` (pinned by
  `tests/test_working_corpus.py::CorpusSplit::test_each_variant_breaks_exactly_its_invariant`),
  and the validator-versus-oracle agreement suites assert the validator's owned
  verdict equals the oracle's on every variant. The divergent tree breaks two
  owned names under the spec-draft `corpus_check`
  (`consecutive-clean-within-drafted`, `gate-ratio-consistent`, in
  `CORPUS_INVARIANT_NAMES` vocabulary order) while the
  table-reading validator breaks none — a deliberate disagreement that both of
  those contracts forbid for an `INCOHERENT_VARIANTS` entry (see Decision Log
  D1).
- The new variant must **not** be a member of `coherent_oracle_cases` /
  `PHASE_STATES`: under `corpus_check` it is not coherent.
- Every existing test must stay green:
  `tests/test_working_corpus.py`, `tests/test_validate_state_corpus.py`,
  `tests/test_validate_state_live_draft.py`,
  `tests/test_working_corpus_done_flags.py`.
- The corpus is consumed by **fixture name only**, never by a runtime value
  import of the `working_corpus` mappings, in every test module outside the
  registered fixture plugins (`tests/corpus_fixtures.py`,
  `tests/corpus_live_draft_fixtures.py`, and the new
  `tests/corpus_divergent_fixtures.py` this task adds) and `tests/conftest.py`
  (developers-guide "Shared test scaffolding" rule;
  `docs/execplans/roadmap-1-3-2.md` Decision Log).
- No single code file exceeds 400 lines, enforced (not merely conventional) by
  the Pylint `too-many-lines` (C0302) check with `max-module-lines = 400`
  (`pyproject.toml` line 177; `[tool.pylint."messages control"]` disables `all`
  at line 187 then re-enables `too-many-lines` at line 300), so `make all`
  **fails** on any module over the cap. The fixture file Work item 2 touches,
  `tests/corpus_fixtures.py`, is **393 lines** (verified), leaving only a 7-line
  margin — adding the divergent-table fixtures inline would breach the cap.
  Work item 2 therefore lands the new fixtures in a *new* sibling plugin module
  rather than growing `corpus_fixtures.py` (Decision Log D5). The existing
  `tests/test_working_corpus.py` already exceeds the default module-line ceiling
  by design and is exempted with an inline note; Work item 1 adds only the three
  small self-test methods there and must not worsen it materially — if those
  additions push it materially further past its current exemption, extract the
  divergent-table self-tests to a focused sibling test module rather than
  escalating the exemption.
- 100% docstring coverage (`interrogate`, `fail-under = 100` in
  `pyproject.toml`): every new module-level function, fixture, and test method
  carries a docstring.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages.
- Keep tests in the top-level `tests/` tree; do not place them in package module
  directories (AGENTS.md).

## Tolerances (exception triggers)

- Scope: if implementation requires touching more than 8 files or more than ~250
  net lines, stop and escalate.
- Production source: if any change to `novel_ralph_skill/` appears necessary,
  stop and escalate (this contradicts the Constraints).
- Interface: if `CORPUS_INVARIANT_NAMES`, `corpus_check`, or
  `PURE_STATE_INVARIANT_NAMES` must change, stop and escalate.
- Module cap (`_variants.py`): if `tests/working_corpus/_variants.py` would
  exceed 400 lines after the addition, stop and escalate (extract the
  divergent-table category to a new sibling module
  `tests/working_corpus/_divergent.py` only after escalation). It is currently
  233 lines, so the ~40-line addition leaves ample margin; this trigger is a
  safety net, not an expected branch.
- Module cap (fixtures): `tests/corpus_fixtures.py` is 393 lines (verified), so
  the new divergent-table fixtures cannot land there without breaching the
  enforced 400-line `too-many-lines` cap. Work item 2 lands them in a *new*
  sibling plugin module `tests/corpus_divergent_fixtures.py` registered through
  `pytest_plugins` in `tests/conftest.py`, mirroring how
  `corpus_live_draft_fixtures.py` was split out for the same reason (Decision
  Log D5; `tests/conftest.py` lines 33-42). This is the sanctioned path, not an
  escalation. Inline `# pylint: disable=too-many-lines` on `corpus_fixtures.py`
  is **forbidden** — it would defeat the AGENTS.md cap and the gate. If, against
  expectation, the new plugin module itself were to approach 400 lines (it will
  not — two fixtures plus a module docstring is well under 60 lines), trim the
  docstrings to NumPy-minimal first, and only then escalate.
- Module cap (self-tests): if Work item 1's three self-test methods push
  `tests/test_working_corpus.py` materially past its existing inline exemption,
  extract the divergent-table self-tests to a focused sibling test module rather
  than widening the exemption; do not add a fresh inline cap-disable.
- Iterations: if the suite still fails after 4 fix attempts on any one work
  item, stop and escalate.
- Ambiguity: if the divergent variant cannot be made to fail under `corpus_check`
  on exactly the two intended owned names without also perturbing a third, stop
  and present options.

## Risks

- Risk: Adding the variant to the wrong corpus category (`INCOHERENT_VARIANTS`
  or `coherent_oracle_cases`) breaks the single-invariant self-test or the
  whole-corpus agreement suites.
  Severity: high Likelihood: medium
  Mitigation: The variant lives in its own first-class category
  `DIVERGENT_TABLE_VARIANTS` (Decision Log D1), exposed by dedicated fixtures and
  consumed only by the discrimination test. Work item 1 lands the category and a
  self-test that pins it is *excluded* from `INCOHERENT_VARIANTS` and from
  `coherent_oracle_cases` before any consumer rewires.

- Risk: The corpus self-test
  `test_every_invariant_name_is_exercised` asserts the set of single-named
  `INCOHERENT_VARIANTS` targets equals `CORPUS_INVARIANT_NAMES`. A divergent
  variant that named two invariants would violate this if mis-filed.
  Severity: medium Likelihood: medium
  Mitigation: The divergent variant is not in `INCOHERENT_VARIANTS`, so it never
  participates in `test_every_invariant_name_is_exercised`. Its self-test
  asserts the *pair* `{gate-ratio-consistent, consecutive-clean-within-drafted}`
  under `corpus_check`, separately.

- Risk: A future reader mistakes the divergent variant's intentional
  validator-versus-oracle disagreement for a bug and "fixes" it by aligning the
  oracles.
  Severity: medium Likelihood: low
  Mitigation: This is the documented landmine the developers-guide already
  names ("a future `by_chapter_override` variant ... is a finding to
  investigate, not a drift to paper over"). Work item 4 extends that guide
  paragraph to point at the new corpus variant and the discrimination test by
  name. The variant's docstring restates it.

- Risk: The corpus oracle `_check_gate_ratio_consistent` /
  `_check_consecutive_clean_within_drafted` read `spec.chapters` (the honest
  drafts), so `corpus_check` on the divergent spec returns the two proxy names —
  but if the spec's `draft_words` were set to match the table, `corpus_check`
  would instead return the empty tuple and the variant would be coherent under
  the oracle, defeating its purpose.
  Severity: medium Likelihood: low
  Mitigation: Work item 1's self-test pins `corpus_check` on the divergent tree
  to exactly `("consecutive-clean-within-drafted", "gate-ratio-consistent")`
  (the `CORPUS_INVARIANT_NAMES` vocabulary order), so a drift in the spec's draft
  words is caught immediately.

- Risk: Removing the module-local `divergent_table_tree` fixture orphans the
  `corpus_builders` bundle fixture (added in 2.1.3 only to keep that fixture's
  argument count within gate) and leaves a dead helper.
  Severity: low Likelihood: high
  Mitigation: Work item 3 removes `corpus_builders` together with
  `divergent_table_tree` once the discrimination test sources its tree from the
  corpus fixture; a `ruff`/`pylint`/`ty` pass plus the suite confirms nothing
  else references either.

- Risk: This task uses no `cuprum` and no external executable; asserting a
  cuprum API the plan does not exercise would be noise.
  Severity: low Likelihood: low
  Mitigation: Decision Log D4 records, with citation, that this task touches
  *no* cuprum consumer. A grep of `tests/` for `cuprum` returns five files
  (`conftest.py`, `test_conftest_helpers.py`, `test_console_scripts_e2e.py`,
  `test_novel_state_check.py`, `test_venv_scripts_dir.py`), none of which this
  task edits; the corpus and oracle layers run purely in-process against
  `tmp_path`.

## Progress

- [x] Work item 1 — add the `DIVERGENT_TABLE_VARIANTS` corpus category and its
  exclusion/shape self-tests. Committed `36e72db`. `make all` green (336
  passed). coderabbit raised only two minor markdown-line-length findings on the
  pre-existing `*.review-r1/-r2.md` planning artefacts (untracked, outside this
  task's code scope) — not actioned. Note: the three self-tests share a local
  `divergent_builders` bundle fixture so each stays within the argument-count
  gate (mirroring `compile_probe`); this is transient and is collapsed in Work
  item 2 when the tests re-point onto the corpus `divergent_table_tree` fixture.
- [x] Work item 2 — expose the category through a new sibling fixture plugin
  `tests/corpus_divergent_fixtures.py` (keeps `corpus_fixtures.py` under the
  enforced 400-line cap — Decision Log D5). Committed `dd7009c`. `make all` green
  (336 passed). Line budget: `corpus_fixtures.py` unchanged at 393, new module 84
  lines, `conftest.py` 332 — all under cap. The WI1 self-tests now consume
  `divergent_table_tree` / `divergent_table_variant_names`; the transient local
  bundle is gone. coderabbit raised one trivial finding (use
  `from typing import TYPE_CHECKING` instead of `import typing as typ`) — declined
  for consistency with the repo-wide idiom: `corpus_live_draft_fixtures.py`,
  `conftest.py`, and `_state_corpus_support.py` all use `import typing as typ`,
  and ruff passes; changing only the new module would make it inconsistent with
  its three siblings. The other two findings target pre-existing planning prose
  in `*.review-r3.md` / the plan's Purpose and Decision Log sections (not authored
  in this work item).
- [x] Work item 3 — rewire the discrimination test onto the corpus fixture and
  delete the module-local `divergent_table_tree` and `corpus_builders` fixtures.
  Committed (this commit). `make all` green (336 passed); the rewritten
  `test_live_draft_discriminates_table_from_drafts` and the three sibling
  live-draft agreement tests all pass. Deleting the two module-local fixtures
  orphaned the `pytest` and `ChapterSpec` imports, both removed. coderabbit raised
  two major findings on second-person "you" in the plan's pre-existing Purpose and
  Context prose; both rephrased to impersonal voice. A one-character markdownlint
  overflow in the untracked `roadmap-2-1-5.review-r3.md` planning artefact was
  wrapped so `make markdownlint` and `make nixie` pass.
- [x] Work item 4 — update the developers-guide and the corpus package
  docstrings, and (optional) confirm the mutant kill. Committed (this commit).
  `make all`, `make markdownlint`, and `make nixie` all green. The
  developers-guide "Invariant validation" landmine paragraph is rewritten to
  present tense, naming
  `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]` and
  `test_live_draft_discriminates_table_from_drafts` and noting the module-local
  fixture's retirement. The `_variants.py` and `__init__.py` package docstrings
  name the new category (landed in Work item 1). Mutant kill confirmed by hand:
  a table-reading rewrite of `live_draft_counts` makes the corpus-sourced
  discrimination test fail `(90000, 3) != (8000, 2)`; reverted, not committed.
  coderabbit returned zero findings on this work item.

### Fix round 1

- [x] Blocking dual-review finding: the `tests/test_validate_state_live_draft.py`
  module docstring contradicted itself within one paragraph. Lines 18-20 still
  framed the `by_chapter_override` variant as a hypothetical "future" tree that
  "would surface as a disagreement to investigate", whereas lines 26-32 already
  described it as a first-class corpus variant in use. Work item 3 step 3 had
  updated the function docstring but missed this earlier module-level paragraph.
  Rewrote lines 18-22 to present tense: the variant exists as
  `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]` and the
  discrimination is driven from corpus data, removing the stale "future" framing
  so the docstring is internally consistent. Committed `4304241`. `make all`
  green (336 passed); the change is docstring-only (no markdown, so markdownlint
  and nixie are not triggered by it). coderabbit returned zero findings.

## Surprises & discoveries

    - Observation: <none yet>
      Evidence:
      Impact:

## Decision log

    - Decision: D1 — model the divergent tree as a new first-class corpus
      category `DIVERGENT_TABLE_VARIANTS` in
      `tests/working_corpus/_variants.py`, NOT as an `INCOHERENT_VARIANTS`
      member.
      Rationale: Under the spec-draft corpus oracle `corpus_check`, the divergent
      tree breaks TWO owned invariants (`consecutive-clean-within-drafted`,
      `gate-ratio-consistent`, in vocabulary order), while the table-reading §5.2
      validator
      breaks NONE. `INCOHERENT_VARIANTS` membership is incompatible with both the
      single-invariant self-test
      (`test_each_variant_breaks_exactly_its_invariant`) and the
      validator-versus-oracle agreement suites
      (`test_incoherent_agreement_restricted_to_owned`,
      `test_live_draft_agreement_over_whole_corpus`), which require
      validator-owned == oracle-owned on every variant. A `DONE_FLAG_PERMUTATIONS`
      precedent already exists for a coherent-but-separate category; this is the
      divergent-but-separate analogue. The roadmap's "keep ... every current
      agreement suite green" clause requires it.
      Date/Author: 2026-06-23, planning agent

    - Decision: D2 — reuse the existing `WorkingTreeSpec.by_chapter_override` and
      `current_words_override` fields rather than add new spec fields.
      Rationale: `_specs.py` already supports both (lines 140-151), the builder
      already materializes them via `derive_by_chapter`/`derive_current`, and the
      2.1.3 module-local fixture already proved the shape. No schema change is
      needed.
      Date/Author: 2026-06-23, planning agent

    - Decision: D3 — keep the divergent variant's `current` equal to the
      override table sum (`current_words_override` = `sum(by_chapter_override)`)
      so `by-chapter-sum` stays silent and the only owned disagreements are the
      two proxies.
      Rationale: The discrimination must isolate the two proxy reads. If
      `by-chapter-sum` also fired, the test could not attribute the disagreement
      to the live/table proxy split. This mirrors the 2.1.3 fixture exactly.
      Date/Author: 2026-06-23, planning agent

    - Decision: D4 — record that this task introduces no cuprum usage.
      Rationale: The roadmap requires pinning every cuprum API the plan relies
      on. This plan relies on none, and it touches no cuprum consumer. A grep of
      `tests/` for `cuprum` returns five files — `conftest.py`,
      `test_conftest_helpers.py`, `test_console_scripts_e2e.py`,
      `test_novel_state_check.py`, `test_venv_scripts_dir.py` — none of which
      this task modifies. (`conftest.py` imports `ProgramCatalogue` /
      `ProjectSettings`; the e2e suite drives installed console scripts by
      absolute path via cuprum 0.1.0 `cuprum.sh` / `cuprum.program.Program`.)
      The files this task does edit — `tests/working_corpus/_variants.py`,
      `tests/working_corpus/__init__.py`, the new
      `tests/corpus_divergent_fixtures.py`, `tests/test_working_corpus.py`,
      `tests/test_validate_state_live_draft.py`, and `docs/developers-guide.md` —
      import no cuprum symbol; the corpus, the oracle, and the discrimination
      test execute in-process over `tmp_path`. (Round-2 advisory A1: earlier
      drafts mis-stated cuprum as having a single consumer; the operative
      conclusion — this task touches none — is unchanged.)
      Date/Author: 2026-06-23, planning agent

    - Decision: D5 — land the divergent-table fixtures in a new sibling pytest
      plugin module `tests/corpus_divergent_fixtures.py` registered through
      `pytest_plugins`, NOT inline in `tests/corpus_fixtures.py`.
      Rationale: `tests/corpus_fixtures.py` is 393 lines (verified), 7 below the
      enforced 400-line `too-many-lines` cap (`pyproject.toml` line 177/300).
      The two new fixtures (`divergent_table_variant_names` plus the
      `divergent_table_tree` factory), modelled on the 44-line
      `done_flag_permutation_names` / `done_flag_tree` pair
      (`corpus_fixtures.py` 309-352) with mandatory 100% NumPy docstrings
      (`interrogate`), add ~40 lines and would push the file to ~433-440 lines,
      failing `make all`'s Pylint pass with no sanctioned remedy. The repository
      already uses exactly this split-for-size idiom: `corpus_live_draft_fixtures.py`
      (61 lines) was carved out of `corpus_fixtures.py` for the same cap reason
      (`tests/conftest.py` lines 33-42), and `corpus_fixtures.py` itself was
      carved out of `conftest.py` (its module docstring lines 9-14). A second
      sibling plugin keeps the new fixtures available by name exactly as a
      `conftest` fixture would be, with zero risk of the cap, and gives the next
      corpus variant (roadmap 2.3.3's disk-authoritative oracle checks) a home.
      The rejected alternative — trimming the new docstrings to fit the ~7-line
      margin — is fragile (interrogate demands 100%) and would re-breach on the
      next addition. Adding the fixtures to `corpus_live_draft_fixtures.py`
      instead was also considered but rejected: the divergent-table fixtures are
      structural-corpus fixtures, not live-draft-oracle fixtures, so a
      named-by-purpose module reads truer and keeps each plugin small.
      Date/Author: 2026-06-23, planning agent

## Outcomes & retrospective

Delivered across four atomic commits, all gates green at HEAD.

- The discrimination test `test_live_draft_discriminates_table_from_drafts`
  sources its tree from the corpus `divergent_table_tree` factory fixture, keyed
  by `divergent_table_variant_names`; it no longer constructs the tree in-module.
- The module-local `divergent_table_tree` and `corpus_builders` fixtures, and the
  orphaned `pytest` and `ChapterSpec` imports, are removed from
  `tests/test_validate_state_live_draft.py`.
- The live-reader-to-table-reader mutant is killed: a hand-applied table read of
  `live_draft_counts` makes the corpus-sourced discrimination test fail
  `(90000, 3) != (8000, 2)`; the mutant was reverted, not committed.
- `make all` passes (336 tests, ruff, interrogate at 100%, pylint via the PyPy
  shim, ty); `make markdownlint` and `make nixie` pass for the Markdown changes.
- The new category `DIVERGENT_TABLE_VARIANTS` is excluded from
  `INCOHERENT_VARIANTS` and `coherent_oracle_cases`, so every prior agreement and
  self-test suite stays green untouched. `CORPUS_INVARIANT_NAMES`, `corpus_check`,
  and `PURE_STATE_INVARIANT_NAMES` are unchanged, and no `novel_ralph_skill/`
  source was touched.

Deviations from the plan:

- Work item 1 added a transient module-local `divergent_builders` bundle fixture
  (mirroring `compile_probe`) so the three self-tests stayed within the
  argument-count gate while building the tree via the constructor fixtures. Work
  item 2 re-pointed the self-tests onto the corpus `divergent_table_tree` factory
  and removed that transient fixture, exactly as the plan anticipated.
- The `import typing as typ` idiom was retained in the new
  `corpus_divergent_fixtures.py` against one trivial coderabbit suggestion, for
  consistency with the repo-wide convention in `corpus_live_draft_fixtures.py`,
  `conftest.py`, and `_state_corpus_support.py`.
- Two coderabbit findings on second-person pronouns in this plan's own
  pre-existing Purpose and Context prose were actioned (rephrased to impersonal
  voice), and a one-character markdownlint overflow in
  `roadmap-2-1-5.review-r3.md` was wrapped, to keep the global Markdown gate
  green.

## Context and orientation

This repository packages the `novel-ralph` skill plus a Python package
`novel_ralph_skill` and a substantial test corpus. Three layers require
understanding, all under
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-5`:

1. The production §5.2 validator,
   `novel_ralph_skill/state/validate.py`. `validate_state(state)` returns the
   tuple of `Violation`s a parsed `State` breaks. It is **pure** and reads only
   the `[word_counts]` table. Its `gate-ratio-consistent` numerator is
   `sum(state.word_counts.by_chapter.values())` and its
   `consecutive-clean-within-drafted` ceiling is the count of `by_chapter`
   entries greater than zero (lines 195-275). It owns eight pure-state names in
   `PURE_STATE_INVARIANT_NAMES`. Do not modify this file.

2. The §1.3.2 corpus package, `tests/working_corpus/`. It declares the spec
   dataclasses and builder, the named tree library, the incoherent variants, the
   structural oracle, and the live-draft oracle:
   - `_specs.py` — `ChapterSpec`, `WorkingTreeSpec` (already carrying
     `by_chapter_override` and `current_words_override`), the builder helpers
     `derive_by_chapter`/`derive_current`, and the `GATE_THRESHOLDS` constant.
   - `_library.py` — `PHASE_ORDER`, `PHASE_STATES` (the eleven coherent phase
     trees), and `COHERENT_BASELINE` (the mid-drafting tree the variants mutate).
   - `_variants.py` — `INCOHERENT_VARIANTS` (each a `(spec, single-invariant-name)`
     pair) and `DONE_FLAG_PERMUTATIONS` (coherent multi-chapter trees). **This is
     where the new `DIVERGENT_TABLE_VARIANTS` category lands.**
   - `_oracle.py` — `corpus_check` (the spec-draft structural oracle) and the
     `CORPUS_INVARIANT_NAMES` vocabulary, plus the named-constant exports
     (`GATE_RATIO_CONSISTENT`, `CONSECUTIVE_CLEAN_WITHIN_DRAFTED`, etc.).
   - `_live_draft.py` — `live_draft_counts` (reads `draft.md` token counts) and
     `live_draft_owned` (the owned-invariant oracle reconciling the two proxies
     against the live drafts).
   - `__init__.py` — re-exports the package's public surface; new public names
     are added here and to `__all__`.

3. The fixture plugins and the consuming tests:
   - `tests/corpus_fixtures.py` — the registered plugin exposing the corpus by
     fixture name (`incoherent_variant_names`, `incoherent_tree`,
     `coherent_oracle_cases`, `done_flag_permutation_names`, `done_flag_tree`,
     `check_corpus`, `corpus_invariant_names`, the `make_*`/`build_tree`
     constructors). At 393 lines it is 7 below the enforced 400-line cap, so the
     new divergent-table fixtures do **not** land here (Decision Log D5).
   - `tests/corpus_live_draft_fixtures.py` — the registered plugin exposing
     `check_live_draft` and `live_draft_counts` (a 61-line module carved out of
     `corpus_fixtures.py` for the size cap; the new plugin mirrors its shape).
   - `tests/corpus_divergent_fixtures.py` — **the new registered plugin this
     task adds**, exposing `divergent_table_variant_names` and the
     `divergent_table_tree` factory. Registered via `pytest_plugins` in
     `tests/conftest.py`.
   - `tests/_state_corpus_support.py` — shared parse/verdict helpers
     (`validator_verdict`, `load_succeeds`, `PARSE_ERRORS`,
     `PARSE_ENFORCED_INVARIANTS`).
   - `tests/test_working_corpus.py` — the corpus self-tests (the
     coherent/incoherent split, the single-invariant pin, the
     every-name-exercised pin). The module already exceeds the default line
     ceiling with an inline exemption note.
   - `tests/test_validate_state_corpus.py` — the validator-versus-oracle
     agreement suite (owned-name equality on every coherent tree and every
     variant).
   - `tests/test_validate_state_live_draft.py` — the whole-corpus *live-draft*
     agreement suite and **the module-local `divergent_table_tree` and
     `corpus_builders` fixtures plus `test_live_draft_discriminates_table_from_drafts`**
     this task migrates onto the corpus.

Key term: a "divergent-table tree" is a `working/` tree whose
`[word_counts].by_chapter` table is numerically NOT equal to the real
`draft.md` bodies on disk. Reading the table yields one answer; reading the
drafts yields another. The §5.2 validator reads the table; the live oracle reads
the drafts; on such a tree they disagree on the two proxy invariants. That
disagreement is by design and is the discriminator this task makes first-class.

The exact tree to model (from the 2.1.3 fix-round fixture,
`tests/test_validate_state_live_draft.py` lines 95-160): phase `drafting` with
the in-order completed prefix; two chapters each with `draft_words=4000`
(live: 8000 words, two drafted chapters) against an 80000 target;
`by_chapter_override={"01": 30000, "02": 30000, "03": 30000}` and
`current_words_override=90000` (table: 90000 words, three entries greater than
zero, and `sum(by_chapter) == current` so `by-chapter-sum` stays silent); all
three knitting gates `True`; `consecutive_clean=3` with
`convergence_target=3`; `current_chapter=2`. Under the live read the 0.10 ratio
contradicts the all-`True` gates and the counter 3 exceeds the two drafted
chapters; under the table read the 1.125 ratio matches the gates and three
drafted entries cover the counter.

## Plan of work

Four ordered, independently committable work items. Each ends with a gate run.
The sequence lands the corpus data and its self-tests first (so the new category
is proven excluded from the agreement loops before any consumer changes), then
exposes it through fixtures, then migrates the consumer and deletes the
module-local fixtures, then documents.

### Work item 1 — add the `DIVERGENT_TABLE_VARIANTS` category to the corpus

Implements: roadmap 2.1.5 (the first-class corpus variant under §1.3.2
ownership); design §5.2 (the two table-based proxies) and §9 (the corpus is the
shared fixture source); `docs/execplans/roadmap-1-3-2.md` (corpus-ownership
constraints — express as plain `tomlkit` data, never invent a schema type);
`docs/execplans/roadmap-2-1-3.md` Fix round 1 (the divergent-table tree shape).

Docs to read first: `docs/novel-ralph-harness-design.md` §5.2 and §9;
`docs/developers-guide.md` "Invariant validation" (the proxy/landmine
paragraph); `docs/execplans/roadmap-2-1-3.md` Risks (the documented landmine)
and Fix round 1; `docs/execplans/roadmap-1-3-2.md` Decision Log and Constraints;
AGENTS.md "Keep file size manageable" and the testing rules.

Skills to load: `python-router` (route to `python-data-shapes` for the frozen
dataclass spec usage and `python-testing` for the self-test idioms);
`en-gb-oxendict` for the prose.

Changes:

1. In `tests/working_corpus/_variants.py`, add a `_divergent_table_spec()`
   factory and a `DIVERGENT_TABLE_VARIANTS: dict[str, WorkingTreeSpec]` mapping
   keyed (initially) `{"by-chapter-override-over-counts-drafts":
   _divergent_table_spec()}`. The factory builds the tree described in Context
   above by mutating from a two-chapter drafting spec (reuse the `_with_chapters`
   helper pattern where it fits). Note that `_with_chapters` inherits
   `COHERENT_BASELINE`'s `phase_completed` (the correct in-order `drafting`
   prefix) but also its `current_chapter`, `consecutive_clean`, and
   `convergence_target`, and leaves `by_chapter_override` /
   `current_words_override` unset — so the factory must set **every** divergent
   field explicitly in its `changes`, not rely on inheritance (round-2 advisory
   A4): the three knitting gates to `True` (not honest), `consecutive_clean=3`,
   `convergence_target=3`, `current_chapter=2` (the baseline is `3` =
   `len(chapters)`; pin `2` so `cursor-coherent` stays silent under the live
   read and the intent is explicit), `by_chapter_override={"01": 30000,
   "02": 30000, "03": 30000}`, and `current_words_override=90000`. Carry a
   module-level docstring update describing the new category beside the existing
   `INCOHERENT_VARIANTS`/`DONE_FLAG_PERMUTATIONS` docs. Every new function
   carries a docstring (interrogate 100%).
2. In `tests/working_corpus/__init__.py`, re-export `DIVERGENT_TABLE_VARIANTS`
   from `._variants` and add it to `__all__` in sorted position.

Tests to add (in `tests/test_working_corpus.py`, the corpus self-test home):

- A new `CorpusDivergentTable` test class (or a focused group) with:
  - `test_divergent_table_breaks_both_proxies`: for the one variant, build it
    through the `incoherent_tree`-style builder (a new `divergent_table_tree`
    fixture from Work item 2 — but for Work item 1 you may build via the existing
    `make_working_tree_spec`/`build_tree` fixtures already present, mirroring how
    the 2.1.3 fixture did) and assert
    `check_corpus(spec, working) == ("consecutive-clean-within-drafted",
    "gate-ratio-consistent")` (vocabulary order: `corpus_check` filters through
    `CORPUS_INVARIANT_NAMES`, where `consecutive-clean-within-drafted` is
    index 5 and `gate-ratio-consistent` is index 9, so the former precedes —
    verified against `tests/working_corpus/_oracle.py` lines 60-74 and the
    `tuple(name for name in CORPUS_INVARIANT_NAMES ...)` return at line 312). This
    pins D3 (only the two proxies fire, `by-chapter-sum` stays silent).
  - `test_divergent_table_not_in_incoherent_variants`: assert the
    divergent-table key is absent from `incoherent_variant_names` (delivered by
    fixture). This pins the Constraint that the variant is a separate category
    and the single-invariant / agreement self-tests never see it.
  - `test_divergent_table_validator_stays_silent`: load the built tree's
    `state.toml` through `validator_verdict` (from `_state_corpus_support`) and
    assert the table-reading validator's owned verdict is empty — the
    disagreement's table side.

These tests must be written red-first where practical: add them, watch them fail
because `DIVERGENT_TABLE_VARIANTS` does not yet exist (collection/import error or
assertion), then implement the category to turn them green (AGENTS.md / execplans
red-green discipline).

Validation: `make all` (build, check-fmt, lint, typecheck, test) passes; the new
self-tests pass; no existing test regresses; `interrogate` reports 100%.

Commit: one commit, message body referencing roadmap 2.1.5 and Work item 1, in
en-GB Oxford spelling.

### Work item 2 — expose the divergent-table category through a new fixture plugin

Implements: roadmap 2.1.5 (the corpus must be consumed by fixture name);
developers-guide "Shared test scaffolding"; `docs/execplans/roadmap-1-3-2.md`
(the fixture-plugin idiom); AGENTS.md "Keep file size manageable" and the
enforced Pylint `too-many-lines` cap (`pyproject.toml` 177/300) — Decision Log
D5.

Why a new module, not `corpus_fixtures.py`: that file is **393 lines** (verified
`wc -l tests/corpus_fixtures.py`), 7 below the enforced 400-line cap. The two new
fixtures (mirroring the 44-line `done_flag_permutation_names` / `done_flag_tree`
pair at `corpus_fixtures.py` 309-352, with mandatory 100% docstrings) add ~40
lines and would push it to ~433-440 — a guaranteed `make all` Pylint failure with
no sanctioned remedy. The repository's own precedent is to split:
`corpus_live_draft_fixtures.py` (61 lines) was carved out of `corpus_fixtures.py`
for exactly this reason (`tests/conftest.py` 33-42). This work item follows that
precedent. An inline `# pylint: disable=too-many-lines` on `corpus_fixtures.py`
is forbidden (it defeats the cap and the AGENTS.md rule).

Docs to read first: `tests/corpus_fixtures.py` (the existing
`incoherent_tree`/`done_flag_tree` factory-as-fixture idiom and its size-split
module docstring lines 9-14); `tests/corpus_live_draft_fixtures.py` (the
already-split sibling plugin this new module mirrors in shape and registration);
`tests/conftest.py` lines 33-42 (the `pytest_plugins` registration and the
size-split rationale comment); developers-guide "Shared test scaffolding".

Skills to load: `python-router` -> `python-testing` (fixture design and plugin
registration); `leta` for navigating the fixture call sites; `en-gb-oxendict`.

Changes:

1. Add a new fixture-plugin module `tests/corpus_divergent_fixtures.py`,
   structurally identical to `tests/corpus_live_draft_fixtures.py`: a module
   docstring (in en-GB Oxford spelling) explaining it is a `pytest_plugins`-
   registered plugin that re-exposes the `DIVERGENT_TABLE_VARIANTS` corpus
   category by fixture name (and noting it lives apart from `corpus_fixtures.py`
   to keep that module under the 400-line cap, mirroring
   `corpus_live_draft_fixtures.py`), `from __future__ import annotations`, the
   `import working_corpus as wc` runtime import, and the `TYPE_CHECKING`-guarded
   `collections.abc` / `pathlib.Path` / `working_corpus.WorkingTreeSpec`
   imports. It contains two fixtures mirroring the existing done-flag pattern:
   - `divergent_table_variant_names() -> tuple[str, ...]` returning
     `tuple(wc.DIVERGENT_TABLE_VARIANTS)`.
   - `divergent_table_tree(tmp_path) -> Callable[[str], tuple[WorkingTreeSpec, Path]]`
     a factory `(name) -> (spec, working_dir)` that builds the named
     divergent-table variant in its own `tmp_path` subdirectory via
     `wc.build_working_tree`, byte-for-byte the `done_flag_tree` idiom. (Provide
     the factory even though there is one variant today, for symmetry and the
     next variant; the discrimination test calls it with the one key.)
   - Each fixture carries a NumPy-style docstring (interrogate 100%).
2. Register the new plugin in `tests/conftest.py` by appending
   `"corpus_divergent_fixtures"` to the `pytest_plugins` tuple (line 42:
   `pytest_plugins = ("corpus_fixtures", "corpus_live_draft_fixtures")`), and
   extend the adjacent rationale comment (lines 33-39) to name the third plugin
   and its size-split reason in one clause, in en-GB Oxford spelling.
3. Re-point the Work item 1 self-tests (if they used `make_working_tree_spec`
   directly) onto these fixtures so the corpus is consumed by fixture name, not
   value. Keep the assertions identical.

Line-budget self-check (mandatory, before committing this work item):

    wc -l tests/corpus_fixtures.py tests/corpus_divergent_fixtures.py tests/conftest.py

   Expect `corpus_fixtures.py` **unchanged at 393** (Work item 2 must not touch
   it), the new `corpus_divergent_fixtures.py` well under 400 (≈ 55-70 lines),
   and `conftest.py` (currently 325) to gain only the one tuple entry plus the
   comment extension — comfortably under 400. If any of the three is at or over
   400, do not commit: trim NumPy docstrings to minimal-complete first, and only
   then escalate.

Tests to update: the Work item 1 self-tests now consume
`divergent_table_variant_names` / `divergent_table_tree`. Add a
`test_divergent_table_variant_names_match_mapping`-style pin only if it adds
signal beyond Work item 1 (optional; do not duplicate coverage). The fixtures
become available to every test module automatically via `pytest_plugins`, exactly
like the existing corpus fixtures — no per-module import.

Validation: `make all` passes (the Pylint pass clears `corpus_fixtures.py`,
`corpus_divergent_fixtures.py`, and `conftest.py` against the 400-line cap; the
self-tests still pass sourcing from the new fixtures; `interrogate` reports 100%).

Commit: one commit, Work item 2.

### Work item 3 — migrate the discrimination test and delete the module-local fixtures

Implements: roadmap 2.1.5 Success clause ("the module-local `divergent_table_tree`
fixture is removed"; "discriminates ... directly through the standard corpus
loop"); `docs/execplans/roadmap-2-1-3.md` Fix round 1 (the fixture this retires).

Docs to read first: `tests/test_validate_state_live_draft.py` in full (the
module-local `divergent_table_tree`, the `corpus_builders` bundle, and
`test_live_draft_discriminates_table_from_drafts` lines 75-260).

Skills to load: `python-router` -> `python-testing`; `leta` (`leta refs
divergent_table_tree`, `leta refs corpus_builders`) to confirm no other
references before deletion; `en-gb-oxendict`; and `mutmut` (via
`python-verification`) for the optional mutant-kill confirmation in Work item 4.

Changes in `tests/test_validate_state_live_draft.py`:

1. Delete the module-local `divergent_table_tree` fixture (lines ~95-160) and the
   `corpus_builders` bundle fixture (lines ~75-93) it depended on. Confirm with
   `leta refs` that nothing else in the module or suite references either name.
2. Rewrite `test_live_draft_discriminates_table_from_drafts` to take the corpus
   `divergent_table_tree` factory fixture (from Work item 2) and the
   `divergent_table_variant_names` fixture, build the one variant by name through
   the factory, and keep the two existing assertions verbatim:
   - `live_draft_counts(working_dir) == (8000, 2)` (the live reader returns the
     draft-derived numbers, not the table's `(90000, 3)`).
   - `check_live_draft(spec, working_dir) == {GATE_RATIO_CONSISTENT,
     CONSECUTIVE_CLEAN_WITHIN_DRAFTED}` while the validator's owned verdict is
     empty, so the two disagree.
   The test now consumes the corpus through the standard fixture loop; its
   docstring is updated to say the divergent tree is now a first-class §1.3.2
   corpus variant (no longer constructed in-module).
3. Update the module docstring's paragraph that currently says
   "`test_live_draft_discriminates_table_from_drafts` closes that gap by
   constructing the one tree ..." to reflect that the tree is now sourced from
   the corpus.

Tests: the rewritten `test_live_draft_discriminates_table_from_drafts` is the
behaviour under test; it must pass after the rewrite and (by construction)
exercise the corpus variant. The whole-corpus agreement tests in the same module
(`test_live_draft_agreement_over_whole_corpus`,
`test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling`,
`test_live_draft_counts_equal_honest_draft_bases`) must stay green untouched —
they iterate `coherent_oracle_cases` and `incoherent_variant_names`, which the
divergent variant is deliberately absent from, so they are unaffected.

Validation: `make all` passes; `ruff`/`pylint`/`ty` report no unused fixture or
import left behind by the deletion.

Commit: one commit, Work item 3.

### Work item 4 — documentation and the optional mutant-kill confirmation

Implements: roadmap 2.1.5 (record the variant once so later readers follow it);
developers-guide "Invariant validation" (the landmine paragraph).

Docs to read first: `docs/developers-guide.md` "Invariant validation" (lines
~335-356, the proxy/landmine paragraph); the corpus package docstrings in
`tests/working_corpus/__init__.py` and `_variants.py`.

Skills to load: `en-gb-oxendict`; `python-verification` -> `mutmut` for the
optional kill check; `firecrawl` is **not** required (no external-library
behaviour is asserted by this task — see Decision Log D4).

Changes:

1. In `docs/developers-guide.md`, extend the "Invariant validation" paragraph
   that names the `by_chapter_override` landmine (lines 347-350: "so a **future**
   `by_chapter_override` variant that separated the table basis from the draft
   basis ... is a finding to investigate, not a drift to paper over"). The
   variant is no longer future, so **rewrite the tense** (round-2 advisory A3):
   change "a future `by_chapter_override` variant that separated ..." to present
   tense naming the now-existing variant — e.g. "the `by_chapter_override`
   variant `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]`,
   which separates the table basis from the draft basis on both proxies, is a
   finding to investigate, not a drift to paper over". Point the paragraph at the
   `test_live_draft_discriminates_table_from_drafts` test by name, noting that
   the discrimination is now driven from corpus data through the standard fixture
   loop and the module-local fixture has been retired. Leave no stale "future"
   in the clause. Keep en-GB Oxford spelling.
2. Ensure the `_variants.py` module docstring and the `__init__.py` package
   docstring mention the new category alongside `INCOHERENT_VARIANTS` and
   `DONE_FLAG_PERMUTATIONS` (the categories the package owns).
3. Optional verification (record the result in Outcomes & Retrospective): run a
   focused mutmut session over `tests/working_corpus/_live_draft.py`'s
   `live_draft_counts` to confirm the live-reader-to-table-reader mutant the
   2.1.3 fix round identified is now killed by the corpus-sourced discrimination
   test. If mutmut is impractical to scope here, instead apply the mutant by
   hand (temporarily make `live_draft_counts` read `by_chapter` from the table)
   and confirm `test_live_draft_discriminates_table_from_drafts` fails, then
   revert. Do not commit the mutant.

Tests: no new test logic beyond Work items 1-3; this item is documentation
plus a verification spot-check.

Validation: `make all` passes; for the Markdown change run `make markdownlint`
and `make nixie` (the developers-guide edit is prose with no new Mermaid, but
`nixie` is required by the standing rule for any Markdown change).

Commit: one commit, Work item 4.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-5`.

1. Confirm the branch and a clean tree:

       git branch --show-current
       git status --short

   Run both from the worktree root. Expect `roadmap-2-1-5` and a clean status.

2. Work item 1: edit `tests/working_corpus/_variants.py` and
   `tests/working_corpus/__init__.py`; add the self-tests to
   `tests/test_working_corpus.py`. Run the targeted suite first, then the full
   gate:

       make test 2>&1 | tail -40
       make all 2>&1 | tail -40

   Expect the new `test_divergent_table_*` cases to pass and the whole suite to
   pass. Commit.

3. Work item 2: create the new plugin `tests/corpus_divergent_fixtures.py` with
   the two fixtures (do **not** edit `tests/corpus_fixtures.py`); register it by
   appending `"corpus_divergent_fixtures"` to `pytest_plugins` in
   `tests/conftest.py` (line 42) and extend the adjacent rationale comment;
   re-point the self-tests onto the new fixtures. Run the line-budget self-check,
   then the gate:

       wc -l tests/corpus_fixtures.py tests/corpus_divergent_fixtures.py tests/conftest.py
       make all 2>&1 | tail -40

   Expect `corpus_fixtures.py` unchanged at 393, the new module well under 400,
   and the Pylint pass green. Commit.

4. Work item 3: delete the module-local fixtures and rewrite the discrimination
   test in `tests/test_validate_state_live_draft.py`. Before deleting, confirm no
   stray references:

       leta refs divergent_table_tree
       leta refs corpus_builders

   Then run `make all`. Expect the rewritten discrimination test to pass and the
   three sibling live-draft agreement tests to stay green. Commit.

5. Work item 4: edit `docs/developers-guide.md` and the two package docstrings;
   run the Markdown gates and the optional mutant check:

       make markdownlint
       make nixie
       make all 2>&1 | tail -40

   Commit.

A short expected transcript of the gate's tail on success:

    ===== N passed in T s =====

(where N is the post-change total). Treat any `failed`, `error`, lint, or
interrogate-below-100 line as a stop-and-fix signal.

## Validation and acceptance

Acceptance is observable behaviour:

- Running `make test` (or `make all`) passes with the suite green. The new
  `test_live_draft_discriminates_table_from_drafts` sources its tree from the
  corpus fixture `divergent_table_tree` and asserts:
  `live_draft_counts(working_dir) == (8000, 2)` (the live reader returns the
  draft-derived numbers, not the table's `(90000, 3)`), and the live oracle's
  owned verdict is `{gate-ratio-consistent, consecutive-clean-within-drafted}`
  while the validator's owned verdict is empty — the two disagree.
- The corpus self-test `test_divergent_table_breaks_both_proxies` asserts
  `corpus_check` on the divergent tree returns exactly
  `("consecutive-clean-within-drafted", "gate-ratio-consistent")` (the
  `CORPUS_INVARIANT_NAMES` vocabulary order — `consecutive-clean-within-drafted`
  at index 5 precedes `gate-ratio-consistent` at index 9, per
  `tests/working_corpus/_oracle.py` lines 60-74 and the order-preserving return
  at line 312), and `test_divergent_table_not_in_incoherent_variants` asserts the
  variant is not in `INCOHERENT_VARIANTS`.
- The module-local `divergent_table_tree` and `corpus_builders` fixtures no
  longer exist in `tests/test_validate_state_live_draft.py`
  (`leta refs divergent_table_tree` finds only the corpus fixture; a `grep` of
  that module finds the fixture name only as a parameter, defined in
  `tests/corpus_fixtures.py`).
- The existing agreement suites are unchanged in behaviour:
  `tests/test_validate_state_corpus.py` and the three sibling live-draft
  agreement tests stay green.

Quality criteria ("done"):

- Tests: `make test` passes; the new discrimination test sources from the corpus;
  the new self-tests pass.
- Lint/typecheck: `make all` passes (`ruff`, `interrogate` at 100%, `pylint`
  via the PyPy shim, `ty`).
- Markdown: `make markdownlint` and `make nixie` pass for the
  developers-guide edit.
- Mutation (optional but recommended): the live-reader-to-table-reader mutant of
  `live_draft_counts` is killed by the corpus-sourced discrimination test
  (confirmed via mutmut or a hand-applied-then-reverted mutant).

Quality method: run `make all` from the worktree root; for the Markdown change
additionally run `make markdownlint` and `make nixie`. Do not run gates in
parallel (shared build cache).

## Idempotence and recovery

Every edit is additive corpus data, a fixture, a test, or a docstring/prose
change; re-running `make all` is safe and the tree builders write only under
`tmp_path`. If a work item's gate fails, fix forward within the iteration
tolerance (4 attempts) before escalating. The four commits are independent: if
Work item 3's deletion proves entangled (an unexpected reference), revert that
commit alone — Work items 1 and 2 leave the corpus category and fixtures in
place harmlessly, and the module-local fixture can remain until the entanglement
is resolved.

## Artefacts and notes

The exact divergent tree (from `tests/test_validate_state_live_draft.py` lines
95-160, the fixture being retired) is the canonical shape the corpus factory
reproduces: two `draft_words=4000` chapters against an 80000 target, with
`by_chapter_override={"01": 30000, "02": 30000, "03": 30000}`,
`current_words_override=90000`, all three knitting gates `True`,
`consecutive_clean=3`, `convergence_target=3`, `current_chapter=2`, phase
`drafting` with the in-order completed prefix.

## Interfaces and dependencies

New public corpus surface (test-only; no production dependency added):

- In `tests/working_corpus/_variants.py`:

      DIVERGENT_TABLE_VARIANTS: dict[str, WorkingTreeSpec]

  keyed by `"by-chapter-override-over-counts-drafts"`, each value a
  `WorkingTreeSpec` whose `by_chapter_override`/`current_words_override` make the
  `[word_counts]` table over-count both proxy quantities relative to the on-disk
  drafts.

- In `tests/working_corpus/__init__.py`: `DIVERGENT_TABLE_VARIANTS` added to the
  re-exports and `__all__`.

- In a **new** module `tests/corpus_divergent_fixtures.py` (registered through
  `pytest_plugins` in `tests/conftest.py`, not added to `corpus_fixtures.py` —
  Decision Log D5, to keep that 393-line module under the enforced 400-line cap):

      @pytest.fixture
      def divergent_table_variant_names() -> tuple[str, ...]: ...

      @pytest.fixture
      def divergent_table_tree(
          tmp_path: Path,
      ) -> cabc.Callable[[str], tuple[WorkingTreeSpec, Path]]: ...

  mirroring the existing `done_flag_permutation_names` / `done_flag_tree`
  signatures.

- In `tests/conftest.py`: `pytest_plugins` gains `"corpus_divergent_fixtures"`
  (line 42), with the adjacent size-split rationale comment extended to name it.

No change to `novel_ralph_skill/` source, to `CORPUS_INVARIANT_NAMES`, to
`corpus_check`, or to `PURE_STATE_INVARIANT_NAMES`. No new external dependency.
`cuprum` is not used by this task (Decision Log D4).

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge review and audit of step 2.1 (`review:2.1.5`, `audit:2.1.5`).
Execute each as a small addendum pass — no plan or design-review cycle: make the
change, run `make all` (plus `make markdownlint`/`make nixie` for Markdown),
`coderabbit review --agent`, commit, and tick the matching roadmap sub-task on
merge. The substantial, cross-cutting follow-ups were re-routed off this task:
the symmetric under-counting `by_chapter_override` corpus variant (review:2.1.5
and audit:2.1.5, two near-identical proposals merged) to roadmap step 2.1
(task 2.1.6, because it adds §1.3.2 corpus data and hardens the
validator-versus-live-oracle cross-check that proves the step-2.1 hypothesis);
the corpus tree-factory-closure consolidation and plugin-split convention
(audit:2.1.5 and review:2.1.5) to a new roadmap step 7.7 (deferred
test-maintainability hardening); and the scoped `mutmut` gate over
`tests/working_corpus/_live_draft.py` (review:2.1.5) is already owned by roadmap
task 7.6.1, which names that module among its mutation targets, so it is not
re-filed here. The three below are the small, localized fixes.

- [x] 2.1.5.1 — Extract the divergent-table self-tests into a focused sibling
  test module (from review:2.1.5, low). `tests/test_working_corpus.py` is 599
  lines under an inline `# pylint: disable=too-many-lines` exemption; this
  task's own Tolerances and Decision Log D5 named extraction to a focused
  sibling test module as the sanctioned escalation path. Lift the
  divergent-table self-test class into a new sibling module before the next
  variant lands so the inline exemption can be relieved. Test-only. Gate with
  `make all`.
  Addendum verification (2026-06-24): already delivered by the later roadmap
  2.1.6 merge, which landed the under-counting variant. The
  `TestCorpusDivergentTable` class now lives in
  `tests/test_working_corpus_divergent.py`, and `tests/test_working_corpus.py`
  carries no divergent-table self-test. `make all` is green at HEAD; no further
  change is required for this sub-task.
- [x] 2.1.5.2 — De-future the live-draft oracle docstring's `by_chapter_override`
  landmine framing (from review:2.1.5, low). `live_draft_owned`'s docstring in
  `tests/working_corpus/_live_draft.py` still frames a `by_chapter_override`
  variant as a "future" landmine ("A future `by_chapter_override` variant … is
  therefore a finding to investigate"), but this task landed that variant.
  Reword the stale "future" framing (and sweep any sibling occurrences) so the
  documentation trail describes the variant that now exists. Docs/comment-only.
  Gate with `make all`.
  Addendum verification (2026-06-24): already delivered by the later roadmap
  2.1.6 merge. The `live_draft_owned` docstring now names both
  `DIVERGENT_TABLE_VARIANTS` members in the present tense as findings to
  investigate, and the `docs/developers-guide.md` "Invariant validation"
  landmine paragraph likewise. A repository-wide sweep finds no remaining
  "future" framing of a `by_chapter_override` variant. No further change is
  required for this sub-task.
- [x] 2.1.5.3 — Make the divergent-table consumer iterate rather than
  single-unpack the variant set (from review:2.1.5, low).
  `tests/test_validate_state_live_draft.py` hard-codes
  `(variant_name,) = divergent_table_variant_names`, so once task 2.1.6 adds the
  second variant the unpack fails with an opaque `ValueError`. Iterate the
  variant set (or pin an explicit single variant by name) to localize that
  future failure ahead of 2.1.6. Test-only. Gate with `make all`.
  Addendum verification (2026-06-24): already delivered by the later roadmap
  2.1.6 merge. `test_live_draft_discriminates_table_from_drafts` iterates
  `for variant_name in divergent_table_variant_names:`, keying each variant's
  expected verdict from `_DIVERGENT_EXPECTATIONS` and asserting any unpinned
  variant announces itself, so there is no single-unpack to break. No further
  change is required for this sub-task.
