# Add a symmetric under-counting divergent-table corpus variant

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Roadmap task 2.1.5 promoted a single *over-counting* divergent-table tree into
the §1.3.2 corpus: a `working/` tree whose `[word_counts].by_chapter` table
claims more drafted words and more drafted chapters than the real `draft.md`
bodies on disk. The whole-corpus live-draft agreement loop uses it to prove the
live oracle (`working_corpus.live_draft_owned`) reads the drafts, not the table,
so a table-reading mutant of `live_draft_counts` is caught.

That single tree only exercises divergence in *one* direction (table greater than
drafts). A subtler mutant survives it: a live reader that returns
`min(live, table)` — element-wise — "mishandles only over-counts". On the
over-counting tree (`live (8000, 2)`, `table (90000, 3)`) the minimum is the live
read, so the mutant is indistinguishable from the honest reader and the
discrimination test passes it. This was verified against the real corpus code
(see Decision Log D1, the `min`-mutant transcript): on the over-counting tree
the mutant leaves the live-draft owned verdict unchanged.

After this change the §1.3.2 corpus owns a first-class *under-counting* sibling
variant: a tree whose `[word_counts].by_chapter` table claims **fewer** drafted
words and **fewer** drafted chapters than the real drafts (`live (90000, 3)`,
`table (8000, 2)`). On this tree the `min`-mutant returns the table read and
collapses the live oracle's verdict, so the mutant is killed. Success is
observable by running the test suite: a new corpus self-test pins the variant's
shape and exclusion, the whole-corpus live-draft discrimination test exercises
**both** divergent trees and asserts the live/table disagreement on each, every
existing corpus-agreement and self-test suite stays green, and (verified by hand,
recorded in Decision Log D1) the `min`-style mutant of `live_draft_counts` that
survives the over-counting tree is killed by the under-counting tree.

A key asymmetry, proved against the live code (Decision Log D2), shapes the
variant: when the table *under*-counts the drafted-chapters count it becomes a
*more* restrictive `consecutive-clean-within-drafted` ceiling than the live
count, so that proxy cannot fire on the live side while the validator stays
silent. The under-counting variant therefore drives its divergence through the
`gate-ratio-consistent` proxy only (the live drafted-words ratio is high while
the table ratio is low), which is the exact mirror of the over-counting tree's
two-proxy break. The roadmap's success clause requires the live/table
disagreement on the new tree and the death of the over-count-only mutant — both
of which the single-proxy under-counting tree delivers; it does not require the
under-counting tree to fire both proxies (Decision Log D2 records why it cannot).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the git worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-6`. Never edit
  the root/control worktree.
- Do **not** change the production validator
  `novel_ralph_skill/state/validate.py` or any `novel_ralph_skill/` source. This
  task is test-corpus, oracle data, and documentation only. The validator's two
  table-based proxies are correct by design (developers-guide "Invariant
  validation"); the divergent tree exercises the documented
  validator-versus-live disagreement, it does not remove it.
- Keep the corpus's public surface contract stable: `CORPUS_INVARIANT_NAMES`
  (the thirteen-name vocabulary in `tests/working_corpus/_oracle.py`),
  `corpus_check`, `live_draft_counts`, `live_draft_owned`, and
  `novel_ralph_skill.state.PURE_STATE_INVARIANT_NAMES` must not change. The new
  variant must not add or rename any invariant name.
- The new variant must **not** be a member of `INCOHERENT_VARIANTS`. Each
  `INCOHERENT_VARIANTS` member must break exactly one named invariant under
  `corpus_check` (pinned by
  `tests/test_working_corpus.py::CorpusSplit::test_each_variant_breaks_exactly_its_invariant`),
  and the validator-versus-oracle agreement suites
  (`test_incoherent_agreement_restricted_to_owned`,
  `test_live_draft_agreement_over_whole_corpus`) assert the validator's owned
  verdict equals the oracle's on every variant. The under-counting tree breaks one
  owned name under `corpus_check` (`gate-ratio-consistent`) while the
  table-reading validator breaks none — a deliberate disagreement both contracts
  forbid for an `INCOHERENT_VARIANTS` entry. It therefore joins the existing
  first-class `DIVERGENT_TABLE_VARIANTS` category (Decision Log D1 of
  `docs/execplans/roadmap-2-1-5.md`), never `INCOHERENT_VARIANTS`.
- The new variant must **not** be a member of `coherent_oracle_cases` /
  `PHASE_STATES`: under `corpus_check` it is not coherent.
- Every existing test must stay green: `tests/test_working_corpus.py`,
  `tests/test_validate_state_corpus.py`,
  `tests/test_validate_state_live_draft.py`,
  `tests/test_working_corpus_done_flags.py`.
- The corpus is consumed by **fixture name only**, never by a runtime value
  import of the `working_corpus` mappings, in every test module outside the
  registered fixture plugins (`tests/corpus_fixtures.py`,
  `tests/corpus_live_draft_fixtures.py`, `tests/corpus_divergent_fixtures.py`)
  and `tests/conftest.py` (developers-guide "Shared test scaffolding" rule;
  `docs/execplans/roadmap-1-3-2.md` Decision Log).
- No single code file exceeds 400 lines, enforced (not merely conventional) by
  the Pylint `too-many-lines` (C0302) check with `max-module-lines = 400`
  (`pyproject.toml`; `[tool.pylint."messages control"]` disables `all` then
  re-enables `too-many-lines`), so `make all` **fails** on any module over the
  cap. `tests/test_working_corpus.py` is **599 lines** (verified) under an inline
  `# pylint: disable=too-many-lines` exemption; adding the new divergent
  self-test method there would widen an already-stretched exemption. Work item 1
  therefore *first* extracts the existing `TestCorpusDivergentTable` class to a
  focused sibling module `tests/test_working_corpus_divergent.py` (folding in
  roadmap addendum 2.1.5.1, the sanctioned escalation path named in
  `docs/execplans/roadmap-2-1-5.md` Tolerances and Decision Log D5), so the NEW
  under-counting self-test lands in a sibling module that is itself under the cap
  and carries no exemption. The extraction does **not** bring
  `tests/test_working_corpus.py` under the cap: at 599 lines, removing the ~62-line
  divergent block leaves it at ~537 lines, still far over 400, so that module
  **keeps its inline `# pylint: disable=too-many-lines` exemption** (Decision Log
  D5; design-review B1). `tests/corpus_divergent_fixtures.py` is **84 lines** and
  `tests/working_corpus/_variants.py` is **300 lines** (verified), both with ample
  margin for this task's additions.
- 100% docstring coverage (`interrogate`, `fail-under = 100` in
  `pyproject.toml`): every new module-level function, fixture, and test method
  carries a docstring.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages.
- Keep tests in the top-level `tests/` tree; do not place them in package module
  directories (AGENTS.md).

## Tolerances (exception triggers)

- Scope: if implementation requires touching more than 8 files or more than ~300
  net lines, stop and escalate. (Work item 1's extraction moves an existing
  ~60-line class between modules; that move is net-neutral and does not count
  against the line budget, but the file count does.)
- Production source: if any change to `novel_ralph_skill/` appears necessary,
  stop and escalate (this contradicts the Constraints).
- Interface: if `CORPUS_INVARIANT_NAMES`, `corpus_check`, `live_draft_counts`,
  `live_draft_owned`, or `PURE_STATE_INVARIANT_NAMES` must change, stop and
  escalate.
- Module cap (`_variants.py`): currently 300 lines. The under-counting factory
  plus its mapping entry adds ~45 lines, leaving ample margin. If it would exceed
  400 lines after the addition, stop and escalate (extract the divergent-table
  category to a new sibling module `tests/working_corpus/_divergent.py` only
  after escalation).
- Module cap (self-tests): the new sibling test module
  `tests/test_working_corpus_divergent.py` must stay under 400 lines. The moved
  class is ~60 lines and the one new self-test ~25 lines, so the module lands
  near ~120 lines including imports and a module docstring — well under. If it
  would approach 400, trim docstrings to NumPy-minimal first, then escalate. An
  inline `# pylint: disable=too-many-lines` on any module is **forbidden**.
- Proxy attribution: the under-counting tree must fire exactly
  `gate-ratio-consistent` under `corpus_check` and `live_draft_owned` and nothing
  else (no `by-chapter-sum`, no `consecutive-clean-within-*`, no
  `cursor-coherent`), with the table-reading validator silent on all owned names.
  If the tree cannot be made to fire exactly that one name without perturbing a
  second, stop and present options.
- Iterations: if the suite still fails after 4 fix attempts on any one work item,
  stop and escalate.
- Ambiguity: if the `min`-style mutant cannot be shown to survive the
  over-counting tree and die on the under-counting tree (the task's reason to
  exist), stop and escalate rather than landing a redundant variant.

## Risks

- Risk: Adding the under-counting tree to the wrong corpus category
  (`INCOHERENT_VARIANTS` or `coherent_oracle_cases`) breaks the single-invariant
  self-test or the whole-corpus agreement suites.
  Severity: high Likelihood: low
  Mitigation: The variant joins the existing first-class
  `DIVERGENT_TABLE_VARIANTS` mapping (Work item 2), exposed by the existing
  `divergent_table_tree` factory and `divergent_table_variant_names` fixtures,
  consumed only by the discrimination test and the divergent self-tests. Work
  item 3's self-test pins it absent from `incoherent_variant_names`. The
  agreement suites iterate only `coherent_oracle_cases` and
  `incoherent_variant_names` (verified in `tests/test_validate_state_corpus.py`
  lines 119, 136 and `tests/test_validate_state_live_draft.py` lines 93, 127), so
  the new key never reaches them.

- Risk: The discrimination test
  `test_live_draft_discriminates_table_from_drafts` hard-codes
  `(variant_name,) = divergent_table_variant_names`
  (`tests/test_validate_state_live_draft.py` line 173), so adding a second
  variant breaks it with an opaque `ValueError: too many values to unpack`.
  Severity: high Likelihood: high (certain if unaddressed)
  Mitigation: Work item 4 rewrites that test to *iterate*
  `divergent_table_variant_names` with a per-variant expected-owned-verdict
  table, folding in roadmap addendum 2.1.5.3 (which named exactly this fix). The
  expected verdict differs by variant (over-count fires two proxies; under-count
  fires one), so the test carries a small name-to-expected mapping rather than a
  single shared assertion.

- Risk: The under-counting tree's owned verdict is asymmetric with the
  over-counting tree's (one proxy versus two), so a naive "assert both proxies
  fire" rewrite of the discrimination test would fail on the new tree.
  Severity: medium Likelihood: medium
  Mitigation: Decision Log D2 records and the verification transcript proves that
  the under-counting tree fires only `gate-ratio-consistent`; Work item 4's
  per-variant expected table encodes each tree's true owned verdict, and Work
  item 3's self-test pins `corpus_check` on the under-counting tree to exactly
  `("gate-ratio-consistent",)`.

- Risk: A future reader mistakes the under-counting variant's intentional
  validator-versus-oracle disagreement for a bug and "fixes" it by aligning the
  oracles.
  Severity: medium Likelihood: low
  Mitigation: This is the documented landmine the developers-guide already names.
  Work item 5 extends that guide paragraph to name the under-counting variant and
  the `min`-style mutant it kills. The variant's docstring restates it.

- Risk: The corpus oracle `_check_gate_ratio_consistent` reads `spec.chapters`
  (the honest drafts), so `corpus_check` on the under-counting spec returns
  `gate-ratio-consistent` — but if the spec's gates were set consistent with the
  *live* ratio the tree would be coherent under the oracle and useless.
  Severity: medium Likelihood: low
  Mitigation: Work item 3's self-test pins `corpus_check` on the under-counting
  tree to exactly `("gate-ratio-consistent",)`, so a drift in the gates or the
  drafts is caught immediately. The verified design sets all three gates `False`
  against a live ratio of 1.125 (every gate should be `True`), an unambiguous
  break.

- Risk: This task uses no `cuprum` and no external executable; asserting a cuprum
  API the plan does not exercise would be noise.
  Severity: low Likelihood: low
  Mitigation: Decision Log D3 records, with citation, that this task touches *no*
  cuprum consumer. A grep of `tests/` for `cuprum` returns five files
  (`conftest.py`, `test_conftest_helpers.py`, `test_console_scripts_e2e.py`,
  `test_novel_state_check.py`, `test_venv_scripts_dir.py`), none of which this
  task edits; the corpus, the oracle, and the discrimination test execute
  in-process over `tmp_path`.

## Progress

- [x] Work item 1 — fold in addendum 2.1.5.1: extract the existing
  `TestCorpusDivergentTable` class from `tests/test_working_corpus.py` into a new
  sibling module `tests/test_working_corpus_divergent.py` so the new under-counting
  self-test has a home in a module under the 400-line cap. Unconditionally delete
  the two orphaned imports (`validator_verdict`, `PURE_STATE_INVARIANT_NAMES`)
  from `test_working_corpus.py`, and **keep** that module's inline
  `too-many-lines` exemption (it stays at ~537 lines, over the cap). DONE
  (commit `5ee6622`): post-move `test_working_corpus.py` is **534 lines** (`wc -l`,
  vs the planned ~537 — within tolerance) and keeps its exemption; the new sibling
  module is **95 lines** (under cap, no exemption). The module-local key was
  renamed `_OVER_COUNTING_KEY` while moving (the rename Work item 3 anticipated),
  so the three moved tests carry it verbatim. `make all` green (342 passed);
  coderabbit 0 findings.
- [x] Work item 2 — add the under-counting variant to `DIVERGENT_TABLE_VARIANTS`
  in `tests/working_corpus/_variants.py`. DONE. Renamed `_divergent_table_spec`
  to `_over_counting_table_spec` for symmetry, added `_under_counting_table_spec`
  (three 30000-word drafts, `by_chapter_override={"01":4000,"02":4000}`,
  `current_words_override=8000`, all gates `False`, `consecutive_clean=2`,
  `convergence_target=3`, `current_chapter=3`), and the second mapping entry
  `"by-chapter-override-under-counts-drafts"`. Refreshed the module docstring and
  mapping comment to name both members. `_variants.py` is **368 lines** (under the
  400 cap). `make all` green (342 passed); the discrimination test now exercises
  both keys.
- [x] Work item 3 — add the under-counting self-test to
  `tests/test_working_corpus_divergent.py` (shape, exclusion, validator-silent),
  parametrized over both divergent variants where it adds signal. DONE (commit
  `c244e84`). Added `test_under_counting_table_breaks_only_gate_ratio` pinning
  `corpus_check == ("gate-ratio-consistent",)`; extended the
  not-in-incoherent test to assert both keys present; parametrized the
  validator-stays-silent test over both keys. Module at **125 lines** (under cap).
  `make all` green (343 passed); coderabbit 0 findings.
- [x] Work item 4 — rewrite `test_live_draft_discriminates_table_from_drafts` to
  iterate both variants with a per-variant expected-owned table, folding in
  addendum 2.1.5.3 (the single-unpack fix). DONE (commit `0178971`, executed
  before Work item 2 per the 1,4,2,3,5 order). Added a module-level
  `_DIVERGENT_EXPECTATIONS` mapping (key -> `(live_counts, expected_owned)`) and
  an iteration that asserts each iterated key is pinned (fails loudly otherwise).
  At this commit the fixture returns one key, so the rewrite is behaviour-
  preserving. `make all` green (342 passed); coderabbit 0 findings.
- [x] Work item 5 — fold in addendum 2.1.5.2 and document: de-future the
  `live_draft_owned` docstring landmine, extend the developers-guide "Invariant
  validation" paragraph to name the under-counting variant and the `min`-mutant,
  refresh the package docstrings, and confirm the mutant kill. DONE. De-futured
  the `live_draft_owned` docstring (now names both members plus the `min`-mutant),
  refreshed the `__init__.py` package docstring and the
  `corpus_divergent_fixtures.py` plugin docstring, and extended the
  developers-guide landmine paragraph with both per-variant verdicts and the
  `min`-mutant rationale. Confirmed the mutant kill by hand (see Outcomes). `make
  markdownlint`, `make nixie`, and `make all` green.

## Surprises & discoveries

    - Observation: <none yet>
      Evidence:
      Impact:

## Decision log

    - Decision: D1 — add the under-counting tree as a second entry in the existing
      first-class `DIVERGENT_TABLE_VARIANTS` mapping, keyed
      `"by-chapter-override-under-counts-drafts"`, NOT as a new category and NOT as
      an `INCOHERENT_VARIANTS` member.
      Rationale: The category already exists (roadmap 2.1.5, Decision Log D1 of
      `docs/execplans/roadmap-2-1-5.md`) precisely to hold table-versus-draft
      divergent trees that break owned proxies under `corpus_check` while the
      table-reading validator breaks none — a disagreement the single-invariant
      self-test and the agreement suites forbid for `INCOHERENT_VARIANTS`. The
      under-counting tree is the same shape of disagreement in the opposite
      direction, so it is the category's second member, not a new structure. The
      fixtures (`divergent_table_variant_names`, the `divergent_table_tree`
      factory) already return the whole mapping by name, so no fixture change is
      needed. Verified against the live corpus code: with `by_chapter_override={
      "01": 4000, "02": 4000}`, `current_words_override=8000`, three drafted
      chapters of 30000 words, target 80000, all gates `False`,
      `consecutive_clean=2`, `convergence_target=3`, `current_chapter=3`,
      `live_draft_counts` returns `(90000, 3)`, `corpus_check` returns
      `('gate-ratio-consistent',)`, `live_draft_owned` returns
      `{'gate-ratio-consistent'}`, and the table-reading validator's owned verdict
      is empty. A `min(live, table)` mutant of `live_draft_counts` survives the
      over-counting tree (its minimum is the live read `(8000, 2)`) but on the
      under-counting tree returns the table read `(8000, 2)` and collapses the
      oracle verdict from `{'gate-ratio-consistent'}` to `set()`, killing the
      mutant. (Both transcripts captured during planning against
      `working_corpus` under `uv run python`.)
      Date/Author: 2026-06-24, planning agent

    - Decision: D2 — drive the under-counting tree's divergence through the
      `gate-ratio-consistent` proxy only, NOT both proxies (the over-counting tree
      breaks both).
      Rationale: A proved asymmetry. `consecutive-clean-within-drafted` fires when
      `consecutive_clean` exceeds the drafted-chapters count. When the table
      *under*-counts the chapter count it is a *smaller* ceiling than the live
      count, so for the table-reading validator to stay silent
      (`consecutive_clean <= table_entries`) the counter must be no larger than
      the table's entry count, which is itself smaller than the live count — so
      the live ceiling is never exceeded and the live oracle cannot fire that
      proxy. Firing it on the live side while keeping the validator silent would
      require the table to *over*-count chapters, which is the over-counting
      tree's job. The roadmap success clause requires the live/table disagreement
      and the death of the over-count-only mutant; it does not require both
      proxies, and the words-total proxy (`gate-ratio-consistent`) carries the
      under-counting divergence cleanly. The verification transcript (D1) confirms
      exactly one owned name fires.
      Date/Author: 2026-06-24, planning agent

    - Decision: D3 — record that this task introduces no cuprum usage.
      Rationale: The roadmap requires pinning every cuprum API the plan relies on.
      This plan relies on none, and it touches no cuprum consumer. A grep of
      `tests/` for `cuprum` returns five files — `conftest.py`,
      `test_conftest_helpers.py`, `test_console_scripts_e2e.py`,
      `test_novel_state_check.py`, `test_venv_scripts_dir.py` — none of which this
      task modifies. The files this task edits —
      `tests/working_corpus/_variants.py`,
      `tests/working_corpus/_live_draft.py` (docstring only),
      `tests/working_corpus/__init__.py` (docstring only),
      `tests/test_working_corpus.py` (extraction), the new
      `tests/test_working_corpus_divergent.py`,
      `tests/test_validate_state_live_draft.py`, and
      `docs/developers-guide.md` — import no cuprum symbol; the corpus, the
      oracle, and the discrimination test execute in-process over `tmp_path`. The
      mutant kill is confirmed in-process, not via any external program. Cuprum's
      catalogue/allowlist/absolute-path-executable surface (verified to exist in
      `/data/leynos/Projects/cuprum/src/cuprum/catalogue.py`, `program.py`, `sh.py`)
      is therefore out of scope for this task and is not exercised.
      Date/Author: 2026-06-24, planning agent

    - Decision: D4 — fold the three pending roadmap addenda 2.1.5.1, 2.1.5.2, and
      2.1.5.3 into this task rather than leaving them for a separate pass.
      Rationale: All three are direct prerequisites or natural companions of the
      under-counting variant. 2.1.5.1 (extract the divergent self-tests to a
      sibling module) is a hard prerequisite: `tests/test_working_corpus.py` is at
      599 lines under an inline `too-many-lines` exemption, and the variant adds a
      self-test there; the 2.1.5 plan named extraction as the sanctioned path
      rather than widening the exemption (`docs/execplans/roadmap-2-1-5.md`
      Tolerances). 2.1.5.3 (iterate the variant set instead of single-unpack) is a
      hard prerequisite: the second variant makes the existing
      `(variant_name,) = divergent_table_variant_names` unpack raise. 2.1.5.2
      (de-future the `live_draft_owned` docstring) is a natural companion: the
      docstring still frames "a future `by_chapter_override` variant" as
      hypothetical, and this task adds the second such variant, so the present-tense
      rewrite belongs with it. Completing each ticks the matching roadmap sub-task.
      Date/Author: 2026-06-24, planning agent

    - Decision: D5 — Work item 1's extraction does NOT remove
      `tests/test_working_corpus.py`'s inline `# pylint: disable=too-many-lines`
      exemption, and the orphaned-import deletion is unconditional. (Resolves
      design-review round-1 blocking points B1 and B2.)
      Rationale (B1): `tests/test_working_corpus.py` is 599 lines (verified
      `wc -l`). The moved block — `_DIVERGENT_KEY` plus the
      `TestCorpusDivergentTable` class, lines 540-599 (~60 lines), plus the two
      orphaned imports (~2 lines) — totals ~62 lines, leaving the module at ~537
      lines, still far above the 400-line cap (`599 - 62 = 537 > 400`). The
      exemption therefore CANNOT be removed; the round-1 draft's "remove the
      exemption / enforced honestly" instruction was infeasible and is deleted.
      The extraction's purpose is solely to give the NEW under-counting self-test a
      home in a sibling module under the cap, so this task does not widen an
      existing exemption; `test_working_corpus.py` stays over-cap and keeps its
      exemption verbatim.
      Rationale (B2): the imports at lines 28 (`validator_verdict`) and 30
      (`PURE_STATE_INVARIANT_NAMES`) are used ONLY by the moved class — the sole
      remaining use of either is at line 599 inside that class (verified by
      `grep -n`). They WILL be orphaned by the extraction and MUST be deleted, or
      `ruff` fails `make all` (F401). The deletion is therefore an unconditional
      step, not a conditional "confirm with `leta refs` before deleting"; the
      `leta refs` check is optional belt-and-braces only.
      Date/Author: 2026-06-24, planning agent

## Outcomes & retrospective

Delivered as planned, execution order 1, 4, 2, 3, 5. The under-counting variant
`"by-chapter-override-under-counts-drafts"` exists as a first-class
`DIVERGENT_TABLE_VARIANTS` member; the discrimination test iterates both divergent
trees with a per-variant expected verdict; every prior suite stays green (343
tests pass, up from 342); no `novel_ralph_skill/` source or corpus public surface
changed (`CORPUS_INVARIANT_NAMES`, `corpus_check`, `live_draft_counts`,
`live_draft_owned`, `PURE_STATE_INVARIANT_NAMES` all stable). Final line counts:
`tests/test_working_corpus.py` 534, `tests/test_working_corpus_divergent.py` 125,
`tests/working_corpus/_variants.py` 368 — all the divergent self-test modules and
the variants module under or at their planned caps.

Mutant-kill confirmation (hand-applied `min(live, table)` monkeypatch of
`live_draft_counts`, run in-process against both variants, then reverted; never
committed):

    OVER-counting tree:  real_live=(8000, 2)  mutant=(8000, 2)
                         owned unchanged {consecutive-clean, gate-ratio} -> SURVIVES
    UNDER-counting tree: real_live=(90000, 3) mutant=(8000, 2)
                         owned {gate-ratio} -> set() -> KILLED

So `test_live_draft_discriminates_table_from_drafts` (asserting the under-counting
oracle verdict is `{gate-ratio-consistent}`) fails under the mutant on the
under-counting tree while passing on the over-counting tree alone — exactly the
discrimination the second tree was added to provide. A full `mutmut` run is out
of scope (roadmap task 7.6.1 owns the standing gate over `_live_draft.py`).

Deviations: none material. The module-local divergent key was renamed
`_OVER_COUNTING_KEY` during Work item 1's extraction (the rename Work item 3
anticipated), so Work item 3 only added `_UNDER_COUNTING_KEY`. The
`corpus_divergent_fixtures.py` plugin docstring — listed "unchanged" in the
plan — was refreshed to name both members, since leaving it describing only the
over-counting direction would have been inaccurate after Work item 2.

Coderabbit: the Work item 2 review hit a rate limit twice (reported waits ~13 min
then ~4.5 min) and succeeded on the third attempt after exponential backoff; all
five work-item reviews ultimately returned 0 findings.

## Context and orientation

This repository packages the `novel-ralph` skill plus a Python package
`novel_ralph_skill` and a substantial test corpus. The layers this task touches,
all under `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-6`:

1. The production §5.2 validator,
   `novel_ralph_skill/state/validate.py` — `validate_state(state)` returns the
   tuple of `Violation`s a parsed `State` breaks. It is **pure** and reads only
   the `[word_counts]` table: its `gate-ratio-consistent` numerator is
   `sum(state.word_counts.by_chapter.values())` and its
   `consecutive-clean-within-drafted` ceiling is the count of `by_chapter`
   entries greater than zero. Do not modify this file. (Context only; this task
   does not touch it.)

2. The §1.3.2 corpus package, `tests/working_corpus/`:
   - `_specs.py` — `ChapterSpec`, `WorkingTreeSpec` (carrying
     `by_chapter_override` and `current_words_override`), the builder helpers
     `derive_by_chapter`/`derive_current`, and `GATE_THRESHOLDS` (`0.30 / 0.50 /
     0.80`). The builder writes `by_chapter` and `current` verbatim from the
     overrides (`derive_by_chapter` returns the override mapping unchanged;
     `derive_current` returns `current_words_override`), so a two-entry override
     against three on-disk drafts is exactly the under-counting shape.
   - `_library.py` — `PHASE_ORDER`, `PHASE_STATES`, and `COHERENT_BASELINE` (the
     mid-drafting tree the variants mutate via `dataclasses.replace`).
   - `_variants.py` — `INCOHERENT_VARIANTS`, `DONE_FLAG_PERMUTATIONS`, and the
     `DIVERGENT_TABLE_VARIANTS` mapping with its `_divergent_table_spec()`
     factory. **This is where the under-counting variant lands** (Work item 2).
   - `_oracle.py` — `corpus_check` (the spec-draft structural oracle) and the
     `CORPUS_INVARIANT_NAMES` vocabulary. `_check_gate_ratio_consistent` reads
     the honest `spec.chapters` draft total; `_check_consecutive_clean_within_drafted`
     counts chapters whose `draft_words > 0`.
   - `_live_draft.py` — `live_draft_counts` (globs `manuscript/chapter-*/draft.md`,
     reads each as UTF-8, takes whitespace-split token counts; returns
     `(drafted_words_total, drafted_chapters_count)`) and `live_draft_owned` (the
     owned-invariant oracle reconciling the two proxies against the live drafts).
     Its docstring still names "a future `by_chapter_override` variant" — Work
     item 5 de-futures it (addendum 2.1.5.2).
   - `__init__.py` — re-exports the package's public surface and `__all__`. No
     new public name is added by this task (the under-counting tree is a new
     *value* under the existing `DIVERGENT_TABLE_VARIANTS` key, not a new symbol).

3. The fixture plugins and the consuming tests:
   - `tests/corpus_divergent_fixtures.py` — the registered plugin exposing the
     `DIVERGENT_TABLE_VARIANTS` category by fixture name:
     `divergent_table_variant_names() -> tuple[str, ...]` (returns the whole
     mapping's keys) and the `divergent_table_tree(tmp_path)` factory `(name) ->
     (spec, working_dir)`. **Unchanged by this task** — it already returns every
     mapping entry, so the new variant is exposed automatically.
   - `tests/conftest.py` — registers the three corpus fixture plugins via
     `pytest_plugins`. **Unchanged by this task.**
   - `tests/_state_corpus_support.py` — shared parse/verdict helpers
     (`validator_verdict`, `load_succeeds`, `PARSE_ERRORS`,
     `PARSE_ENFORCED_INVARIANTS`).
   - `tests/test_working_corpus.py` — the corpus self-tests, **599 lines** under
     an inline `# pylint: disable=too-many-lines` exemption. Its
     `TestCorpusDivergentTable` class (lines ~543-599) is extracted to a sibling
     module by Work item 1.
   - `tests/test_working_corpus_divergent.py` — **the new sibling self-test
     module** this task adds (Work item 1), home to the divergent-table
     self-tests and the new under-counting self-test (Work item 3).
   - `tests/test_validate_state_corpus.py` — the validator-versus-oracle agreement
     suite (owned-name equality on every coherent tree and every incoherent
     variant). **Unchanged**; it iterates only `coherent_oracle_cases` and
     `incoherent_variant_names`.
   - `tests/test_validate_state_live_draft.py` — the whole-corpus live-draft
     agreement suite and `test_live_draft_discriminates_table_from_drafts`, which
     Work item 4 rewrites to iterate both divergent variants.

Key term: a "divergent-table tree" is a `working/` tree whose
`[word_counts].by_chapter` table is numerically NOT equal to the real `draft.md`
bodies on disk. The §5.2 validator reads the table; the live oracle reads the
drafts; on such a tree they disagree on a proxy invariant. The over-counting tree
makes the table greater than the drafts; the under-counting tree (this task)
makes the table smaller.

The exact under-counting tree to model (verified against the live corpus during
planning): phase `drafting` with the in-order completed prefix (inherited from
`COHERENT_BASELINE`); three chapters each with `draft_words=30000`,
`target_words=30000` (live: 90000 words, three drafted chapters) against an 80000
novel target; `by_chapter_override={"01": 4000, "02": 4000}` and
`current_words_override=8000` (table: 8000 words, two entries greater than zero,
and `sum(by_chapter) == current` so `by-chapter-sum` stays silent); all three
knitting gates `False`; `consecutive_clean=2` with `convergence_target=3`;
`current_chapter=3`. Under the live read the 1.125 ratio (every gate should be
`True`) contradicts the all-`False` gates, so `gate-ratio-consistent` fires;
`consecutive_clean=2` is within both the live (3) and the table (2)
drafted-chapter counts, so `consecutive-clean-within-drafted` stays silent on
both sides; `cursor-coherent` stays silent (`current_chapter=3 <= 3` chapters).
Under the table read the 0.10 ratio matches the all-`False` gates, so the
validator names neither proxy.

## Plan of work

Five ordered, independently committable work items. Each ends with a gate run.
The sequence first carves out a sibling self-test module that sits under the
line cap so the new under-counting self-test has an under-cap home (Work item 1;
this does NOT remove `test_working_corpus.py`'s existing `too-many-lines`
exemption, which stays), then lands the corpus data (Work item 2), then its
self-test (Work item 3), then migrates the discrimination consumer
(Work item 4), then documents and confirms the mutant kill (Work item 5).

### Work item 1 — extract the divergent self-tests to a sibling module (addendum 2.1.5.1)

Implements: roadmap addendum 2.1.5.1 (extract the divergent-table self-tests to
a focused sibling test module). This extraction gives the NEW under-counting
self-test (Work item 3) a home in a sibling module that is *under* the 400-line
cap; it does NOT relieve, lift, or remove the inline `too-many-lines` exemption
in `tests/test_working_corpus.py`. That module stays ~537 lines after the move
(still over the cap) and keeps its exemption verbatim — see step 4 and
Decision Log D5.
Design §5.2 and §9 (the corpus is the shared fixture source); AGENTS.md
"Keep file size manageable".

Docs to read first: `docs/execplans/roadmap-2-1-5.md` Tolerances and Decision Log
D5 (the sanctioned extraction path); AGENTS.md "Keep file size manageable" and
the testing rules; `docs/developers-guide.md` "Shared test scaffolding".

Skills to load: `python-router` -> `python-testing` (test-module structure,
fixture consumption by name); `leta` (`leta refs TestCorpusDivergentTable`,
`leta grep _DIVERGENT_KEY`) to confirm nothing imports the class or the
module-local key from `tests/test_working_corpus.py`; `en-gb-oxendict`.

Changes:

1. Create `tests/test_working_corpus_divergent.py` with a module docstring (en-GB
   Oxford spelling) explaining it is the focused home for the divergent-table
   corpus self-tests, carved out of `tests/test_working_corpus.py` to keep that
   module under the line cap (mirroring the corpus fixture-plugin split idiom).
   It needs `from __future__ import annotations`, the `TYPE_CHECKING`-guarded
   imports (`collections.abc`, `pathlib.Path`, and `from conftest import
   WorkingTreeSpec`), the `from _state_corpus_support import validator_verdict`
   import, and `from novel_ralph_skill.state import PURE_STATE_INVARIANT_NAMES`,
   matching the symbols the moved class uses.
2. Move the `_DIVERGENT_KEY` constant and the `TestCorpusDivergentTable` class
   (the three methods `test_divergent_table_breaks_both_proxies`,
   `test_divergent_table_not_in_incoherent_variants`,
   `test_divergent_table_validator_stays_silent`) verbatim from
   `tests/test_working_corpus.py` into the new module. Do not change their logic.
3. Delete the moved constant and class from `tests/test_working_corpus.py`, and
   **unconditionally delete the two imports the moved class orphans**: line 28
   `from _state_corpus_support import validator_verdict` and line 30
   `from novel_ralph_skill.state import PURE_STATE_INVARIANT_NAMES`. This review
   confirmed both imports are used **only** by the moved `TestCorpusDivergentTable`
   class — the sole remaining use of either is at line 599, inside that class
   (`assert validator_verdict(working) & set(PURE_STATE_INVARIANT_NAMES) ==
   set()`), verified by `grep -n` over the module. They **will** be orphaned by
   the extraction and **must** be removed, or `ruff` fails `make all` on the
   unused imports (F401). This is not a conditional "confirm before deleting"
   step. (You may re-run `leta refs validator_verdict` / `leta refs
   PURE_STATE_INVARIANT_NAMES` as a belt-and-braces confirmation, but the deletion
   is unconditional regardless.)
4. **Leave `tests/test_working_corpus.py`'s inline
   `# pylint: disable=too-many-lines` exemption (and its explanatory comment,
   lines 14-17) in place — do NOT remove it.** The extraction cannot bring the
   module under the 400-line cap and is not intended to: the module is 599 lines
   (verified `wc -l`), and the moved block — `_DIVERGENT_KEY` plus the
   `TestCorpusDivergentTable` class (lines 540-599, ~60 lines) plus the two
   orphaned imports (~2 lines) — totals ~62 lines, leaving the module at ~537
   lines, still far over the cap (`599 - 62 = 537 > 400`). The extraction's sole
   purpose is to give the NEW under-counting self-test (Work item 3) a home in a
   sibling module that is *under* the cap, so this task does not widen an existing
   exemption; `test_working_corpus.py` stays over-cap and keeps its exemption
   verbatim. Removing the exemption would fail `make all`'s Pylint pass. (Verify
   the post-move line count with `wc -l` and record it in Progress; expect ~537.)
   This resolves design-review round-1 blocking points B1 and B2 (Decision Log
   D5).

Tests: no new test logic — the three moved tests must pass unchanged from the new
module. The whole suite stays green (same tests, new home).

Validation: `make all` passes; the three moved tests run from
`tests/test_working_corpus_divergent.py`; `ruff`/`pylint`/`ty` report no orphaned
import in either module; `interrogate` reports 100%.

Commit: one commit, message body referencing roadmap addendum 2.1.5.1 and Work
item 1, en-GB Oxford spelling.

### Work item 2 — add the under-counting variant to `DIVERGENT_TABLE_VARIANTS`

Implements: roadmap 2.1.6 (the symmetric under-counting first-class corpus
variant under §1.3.2 ownership); design §5.2 (the two table-based proxies) and §9
(the corpus is the shared fixture source); `docs/execplans/roadmap-2-1-5.md`
Decision Log D1 (the `DIVERGENT_TABLE_VARIANTS` category contract) and D3 (keep
`current == sum(by_chapter)` so `by-chapter-sum` stays silent).

Docs to read first: `docs/novel-ralph-harness-design.md` §5.2 and §9;
`docs/developers-guide.md` "Invariant validation" (the proxy/landmine paragraph);
`docs/execplans/roadmap-2-1-5.md` (the over-counting variant and its constraints);
`tests/working_corpus/_variants.py` (the `_divergent_table_spec` factory this
mirrors) and `_specs.py` (the `by_chapter_override`/`current_words_override`
semantics); AGENTS.md "Keep file size manageable".

Skills to load: `python-router` -> `python-data-shapes` (the frozen-dataclass
spec usage via `dataclasses.replace`); `en-gb-oxendict`.

Changes:

1. In `tests/working_corpus/_variants.py`, add a `_under_counting_table_spec()`
   factory beside the existing `_divergent_table_spec()` (which becomes the
   "over-counting" factory; optionally rename it `_over_counting_table_spec()` for
   symmetry, updating the one call site in the mapping — a clarity-only rename,
   no behaviour change; if renamed, also update any docstring reference). The new
   factory builds the tree described in Context above: three chapters of
   `draft_words=30000` / `target_words=30000` against the baseline's 80000 target,
   with `by_chapter_override={"01": 4000, "02": 4000}`,
   `current_words_override=8000`, all three knitting gates `False`,
   `consecutive_clean=2`, `convergence_target=3`, `current_chapter=3`. Build via
   the `_with_chapters` helper, then set every divergent field explicitly in the
   `changes` (gates `False` must be set explicitly because `_with_chapters`
   computes honest gates from the drafts — the live 1.125 ratio would make
   `_consistent_gates` return all-`True`, the opposite of what the divergence
   needs; pass `done_30=False, done_50=False, done_80=False` to override). Carry
   a NumPy-style docstring (interrogate 100%) explaining the under-counting shape,
   the single fired proxy (`gate-ratio-consistent`), why `consecutive-clean-within-drafted`
   cannot fire on the live side (Decision Log D2), and that the table-reading
   validator stays silent.
2. Add the mapping entry
   `"by-chapter-override-under-counts-drafts": _under_counting_table_spec()` to
   `DIVERGENT_TABLE_VARIANTS`, and update the mapping's leading comment and the
   module docstring's `DIVERGENT_TABLE_VARIANTS` paragraph to describe both the
   over-counting and under-counting members.

Tests to add: none in this work item (the self-test lands in Work item 3 so the
data and its proof are separately committable; the existing divergent self-tests
and the discrimination test still pass because the existing `_DIVERGENT_KEY`
self-tests pin the over-counting tree by name and the discrimination test still
single-unpacks — so this work item must keep the mapping's *first* key as the
over-counting one, or Work item 4 lands in the same commit). To keep work items
atomic and gate-passable: confirm the existing
`test_live_draft_discriminates_table_from_drafts` single-unpack still works after
adding a second key — it will **not** (two keys break the unpack), so Work
item 2 and Work item 4 must be ordered so the suite is green at each commit.
**Resolution (Decision Log D4 dependency):** land Work item 4's iterate-rewrite
*before* adding the second mapping entry, or fold the second mapping entry and the
discrimination rewrite into a single commit. This plan adopts the latter only if
the line budget forces it; the preferred order is **Work item 4 before Work item
2's mapping entry is observable to the discrimination test**. To keep five clean
commits, Work item 2 adds the factory **and** the mapping entry, and Work item 4
(the discrimination rewrite) is reordered to run *immediately after* Work item 2
in the same push but as its own commit — meaning Work item 2's commit will leave
`test_live_draft_discriminates_table_from_drafts` failing. That violates the
per-commit gate.

   **Therefore this plan reorders:** Work item 2 is split so the gate stays green
   at every commit — see the Concrete steps. Specifically, Work item 4's
   iterate-rewrite of the discrimination test is performed **first** (against the
   single existing variant, a no-op behavioural change that still passes), then
   Work item 2 adds the under-counting mapping entry. The Progress list and
   Concrete steps below encode this corrected order: 1 (extract), then 4
   (iterate-rewrite, still one variant), then 2 (add variant), then 3 (self-test),
   then 5 (docs). The Work item numbers are retained for traceability; the
   *execution order* is 1, 4, 2, 3, 5.

Validation: `make all` passes after the rewrite-then-add sequence; the under-
counting tree builds and `corpus_check` on it returns `("gate-ratio-consistent",)`
(spot-checked in Work item 3's self-test); `interrogate` reports 100%.

Commit: one commit for the variant addition (after the discrimination rewrite),
Work item 2.

### Work item 3 — add the under-counting self-test

Implements: roadmap 2.1.6 (pin the under-counting variant's shape and exclusion);
design §5.2; `docs/execplans/roadmap-2-1-5.md` Risks (the shape self-test that
guards the proxy attribution).

Docs to read first: `tests/test_working_corpus_divergent.py` (the moved
`TestCorpusDivergentTable` class from Work item 1); `tests/working_corpus/_oracle.py`
lines 60-74 (the `CORPUS_INVARIANT_NAMES` vocabulary order) and 288-312
(`corpus_check`); AGENTS.md testing rules.

Skills to load: `python-router` -> `python-testing` (parametrized self-tests,
fixture consumption by name); `en-gb-oxendict`.

Changes in `tests/test_working_corpus_divergent.py`:

1. Add `_UNDER_COUNTING_KEY = "by-chapter-override-under-counts-drafts"` and
   `_OVER_COUNTING_KEY` (rename `_DIVERGENT_KEY` for symmetry, updating its uses
   in the moved class).
2. Add a focused test method (or extend the moved class) pinning the
   under-counting tree:
   - `test_under_counting_table_breaks_only_gate_ratio`: build the under-counting
     tree through the `divergent_table_tree` factory fixture and assert
     `check_corpus(spec, working) == ("gate-ratio-consistent",)` — exactly the one
     proxy, with `by-chapter-sum`, `consecutive-clean-within-drafted`, and
     `cursor-coherent` all silent (Decision Log D2). This pins the verified shape.
   - `test_under_counting_table_validator_stays_silent`: load the built tree's
     `state.toml` through `validator_verdict` and assert the table-reading
     validator's owned verdict is empty — the disagreement's table side.
   Where it removes duplication without obscuring intent, parametrize the
   "validator stays silent" and "not in incoherent variants" assertions over both
   divergent keys via `divergent_table_variant_names` (the over-counting tree
   already has its own `test_divergent_table_*` methods; do not duplicate the
   over-counting proxy-pair assertion — that one is over-count-specific).
3. Ensure `test_divergent_table_not_in_incoherent_variants` (moved in Work
   item 1) covers *both* keys: assert
   `set(divergent_table_variant_names).isdisjoint(incoherent_variant_names)` and
   that both keys are present in `divergent_table_variant_names`.

These tests must be written red-first where practical: add the under-counting
assertions, watch them fail (collection or assertion) until Work item 2's variant
exists, then green. Because Work item 2 (the variant) lands before Work item 3 in
the execution order, write the self-test to assert the verified verdict and watch
it pass; if it fails, the variant shape has drifted from the design — fix the
variant, not the test.

Validation: `make all` passes; the new under-counting self-tests pass; the moved
over-counting self-tests stay green; `interrogate` reports 100%.

Commit: one commit, Work item 3.

### Work item 4 — iterate the discrimination test over both variants (addendum 2.1.5.3)

Implements: roadmap 2.1.6 Success ("the whole-corpus live-draft agreement test
discriminates the live read from a table read on this tree too"); roadmap addendum
2.1.5.3 (iterate the variant set rather than single-unpack);
`docs/execplans/roadmap-2-1-5.md` Success clause (the discrimination is driven
from corpus data through the standard loop).

Note on order: per Decision Log D4 and the Work item 2 resolution, the
iterate-rewrite is executed **before** the under-counting variant is added to the
mapping, so this work item's commit lands while `divergent_table_variant_names`
still has one key — the rewrite is a behaviour-preserving refactor at that point
(iterating a one-element tuple), and the suite stays green. The under-counting
variant (Work item 2) then exercises the new iteration without further test edits.

Docs to read first: `tests/test_validate_state_live_draft.py` in full (the
`test_live_draft_discriminates_table_from_drafts` test, lines 143-180, and the
module docstring lines 18-39); `tests/working_corpus/_live_draft.py`
(`live_draft_counts`, `live_draft_owned`); `docs/developers-guide.md` "Invariant
validation".

Skills to load: `python-router` -> `python-testing` (parametrization, per-case
expected tables); `leta` (`leta refs divergent_table_variant_names`) to confirm
the consumer set; `en-gb-oxendict`.

Changes in `tests/test_validate_state_live_draft.py`:

1. Replace the line-173 single-unpack
   `(variant_name,) = divergent_table_variant_names` with an iteration over
   `divergent_table_variant_names`. Carry a module-level mapping of each variant
   key to its expected `(live_counts, expected_owned)` pair:
   - `"by-chapter-override-over-counts-drafts"` -> `((8000, 2),
     {GATE_RATIO_CONSISTENT, CONSECUTIVE_CLEAN_WITHIN_DRAFTED})`.
   - `"by-chapter-override-under-counts-drafts"` -> `((90000, 3),
     {GATE_RATIO_CONSISTENT})`.
   At the point this work item commits, only the first key exists, so the mapping
   may list both but the loop only iterates the keys the fixture returns; assert
   each iterated key has an entry in the expected mapping (a `KeyError` would
   signal a new, unpinned variant — fail loudly with the key name). This keeps the
   test honest when Work item 2 adds the second key.
2. For each iterated variant: build it via `divergent_table_tree(name)`, assert
   `live_draft_counts(working_dir) == expected_live_counts[name]`, compute
   `oracle_owned = check_live_draft(spec, working_dir)` and
   `validator_owned = validator_verdict(working_dir) & set(PURE_STATE_INVARIANT_NAMES)`,
   then assert `oracle_owned == expected_owned[name]`, `validator_owned == set()`,
   and `oracle_owned != validator_owned` (the disagreement is the discriminator
   on every divergent tree). Annotate each assertion with `name` for a legible
   failure message.
3. Update the test's docstring and the module docstring to describe *both*
   divergent trees (the table over-counts on one, under-counts on the other) and
   the per-variant expected verdicts, and to note the discrimination is driven
   from corpus data through the standard fixture loop for every divergent variant.

Tests: the rewritten `test_live_draft_discriminates_table_from_drafts` is the
behaviour under test; it must pass with one variant (this commit) and, after Work
item 2, with both. The three sibling agreement tests
(`test_live_draft_agreement_over_whole_corpus`,
`test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling`,
`test_live_draft_counts_equal_honest_draft_bases`) stay green untouched.

Validation: `make all` passes; the iterated discrimination test passes;
`ruff`/`pylint`/`ty` clean.

Commit: one commit, Work item 4 (executed before Work item 2's variant entry).

### Work item 5 — de-future the docstring, document, and confirm the mutant kill

Implements: roadmap 2.1.6 (record the under-counting variant once so later readers
follow it); roadmap addendum 2.1.5.2 (de-future the `live_draft_owned` docstring);
developers-guide "Invariant validation" (the landmine paragraph).

Docs to read first: `tests/working_corpus/_live_draft.py` (the `live_draft_owned`
docstring's "A future `by_chapter_override` variant ..." sentence, lines ~171-174);
`docs/developers-guide.md` "Invariant validation" (lines ~347-356, the
proxy/landmine paragraph naming `DIVERGENT_TABLE_VARIANTS[
"by-chapter-override-over-counts-drafts"]`); the corpus package docstrings in
`tests/working_corpus/__init__.py` and `_variants.py`.

Skills to load: `en-gb-oxendict`; `python-verification` -> `mutmut` for the
mutant-kill confirmation (or the hand-applied-then-reverted mutant); `firecrawl`
is **not** required (no external-library behaviour is asserted — Decision Log D3).

Changes:

1. In `tests/working_corpus/_live_draft.py`, rewrite the `live_draft_owned`
   docstring sentence that frames "A future `by_chapter_override` variant that
   separates the table basis from the draft basis on either proxy is therefore a
   finding to investigate" to present tense, naming both existing
   `DIVERGENT_TABLE_VARIANTS` members (over-counts and under-counts) as the
   variants that now exercise the landmine (addendum 2.1.5.2). Sweep for any
   sibling "future" framing of the same variant in the module and in
   `tests/test_validate_state_live_draft.py`'s docstrings.
2. In `docs/developers-guide.md`, extend the "Invariant validation" landmine
   paragraph to name both divergent members and the discrimination test's
   per-variant verdicts, and add one sentence recording that the under-counting
   tree exists specifically to kill a table-reading mutant of `live_draft_counts`
   that "mishandles only over-counts" (a `min(live, table)`-style mutant), which
   the over-counting tree alone cannot catch. Keep en-GB Oxford spelling.
3. Refresh the `_variants.py` module docstring and the `__init__.py` package
   docstring so the `DIVERGENT_TABLE_VARIANTS` description names both the
   over-counting and under-counting members.
4. Mutant-kill confirmation (record the result in Outcomes & Retrospective):
   apply the `min`-style mutant by hand — temporarily make `live_draft_counts`
   return the element-wise minimum of the live read and the table read — and
   confirm that `test_live_draft_discriminates_table_from_drafts` now **fails on
   the under-counting variant** (the oracle verdict collapses from
   `{gate-ratio-consistent}` to empty) while it would have **passed on the
   over-counting variant alone**. Revert the mutant; do not commit it. If `mutmut`
   is practical to scope over `tests/working_corpus/_live_draft.py`, prefer it and
   record the surviving/killed mutant ids (note: roadmap task 7.6.1 owns the
   standing `mutmut` gate over this module, so a full run is out of scope here —
   a focused spot-check suffices).

Tests: no new test logic beyond Work items 1-4; this item is documentation plus
a verification spot-check.

Validation: `make all` passes; for the Markdown change run `make markdownlint` and
`make nixie` (the developers-guide edit is prose with no new Mermaid, but `nixie`
is required by the standing rule for any Markdown change).

Commit: one commit, Work item 5.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-6`. The execution
order is **1, 4, 2, 3, 5** (the discrimination rewrite precedes the variant
addition so the gate stays green at every commit — Decision Log D4).

1. Confirm the branch and a clean tree:

       git branch --show-current
       git status --short

   Expect `roadmap-2-1-6` and a clean status.

2. Work item 1 (extract): create `tests/test_working_corpus_divergent.py`, move
   `_DIVERGENT_KEY` and `TestCorpusDivergentTable` into it, remove them and any
   orphaned imports from `tests/test_working_corpus.py`. Confirm references and
   line counts, then gate:

       leta refs TestCorpusDivergentTable
       wc -l tests/test_working_corpus.py tests/test_working_corpus_divergent.py
       make all 2>&1 | tail -40

   Expect the three divergent self-tests to run from the new module and the suite
   to pass. Commit.

3. Work item 4 (iterate-rewrite, still one variant): rewrite
   `test_live_draft_discriminates_table_from_drafts` in
   `tests/test_validate_state_live_draft.py` to iterate
   `divergent_table_variant_names` with the per-variant expected table. Gate:

       make all 2>&1 | tail -40

   Expect the iterated test to pass over the single existing key. Commit.

4. Work item 2 (add variant): add `_under_counting_table_spec()` and the
   `"by-chapter-override-under-counts-drafts"` mapping entry to
   `tests/working_corpus/_variants.py` (optionally rename the over-counting
   factory for symmetry). Confirm the build and the verdicts, then gate:

       wc -l tests/working_corpus/_variants.py
       make all 2>&1 | tail -40

   Expect `_variants.py` under 400 lines and the discrimination test now passing
   over **both** keys. Commit.

5. Work item 3 (self-test): add the under-counting self-tests to
   `tests/test_working_corpus_divergent.py`. Gate:

       make all 2>&1 | tail -40

   Expect `corpus_check` on the under-counting tree pinned to
   `("gate-ratio-consistent",)` and the validator silent. Commit.

6. Work item 5 (docs and mutant check): de-future the `_live_draft.py` docstring,
   extend `docs/developers-guide.md`, refresh the package docstrings, and run the
   mutant spot-check. Gate the Markdown and the suite:

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

- Running `make test` (or `make all`) passes with the suite green.
- `test_live_draft_discriminates_table_from_drafts` iterates both divergent
  variants and asserts, for the under-counting tree: `live_draft_counts(working_dir)
  == (90000, 3)` (the live reader returns the draft-derived numbers, not the
  table's `(8000, 2)`), the live oracle's owned verdict is `{gate-ratio-consistent}`,
  the validator's owned verdict is empty, and the two disagree; and, for the
  over-counting tree: the verified `(8000, 2)` and the two-proxy verdict, unchanged.
- The corpus self-test `test_under_counting_table_breaks_only_gate_ratio` asserts
  `corpus_check` on the under-counting tree returns exactly
  `("gate-ratio-consistent",)`, and `test_divergent_table_not_in_incoherent_variants`
  asserts both divergent keys are absent from `INCOHERENT_VARIANTS`.
- The existing agreement suites are unchanged in behaviour:
  `tests/test_validate_state_corpus.py` and the three sibling live-draft agreement
  tests stay green; the moved over-counting self-tests pass from their new module.
- The `min`-style over-count-only mutant of `live_draft_counts` is killed by the
  under-counting tree (confirmed via the hand-applied-then-reverted mutant or a
  focused `mutmut` spot-check; recorded in Outcomes & Retrospective).

Quality criteria ("done"):

- Tests: `make test` passes; the discrimination test iterates both variants; the
  new and moved self-tests pass.
- Lint/typecheck: `make all` passes (`ruff`, `interrogate` at 100%, `pylint` via
  the PyPy shim, `ty`).
- Markdown: `make markdownlint` and `make nixie` pass for the developers-guide
  edit.
- Mutation: the over-count-only mutant of `live_draft_counts` is killed by the
  under-counting variant.

Quality method: run `make all` from the worktree root; for the Markdown change
additionally run `make markdownlint` and `make nixie`. Do not run gates in
parallel (shared build cache).

## Idempotence and recovery

Every edit is additive corpus data, a moved test, a rewritten test, or a
docstring/prose change; re-running `make all` is safe and the tree builders write
only under `tmp_path`. If a work item's gate fails, fix forward within the
iteration tolerance (4 attempts) before escalating. The commits are ordered so the
gate is green at each: the discrimination rewrite (Work item 4) precedes the
variant addition (Work item 2). If the variant addition proves entangled, revert
that commit alone — the iterate-rewrite handles a one-key fixture set harmlessly,
and the corpus keeps only the over-counting member.

## Artifacts and notes

The verified under-counting tree (pinned against the live `working_corpus` code
during planning): three `draft_words=30000` / `target_words=30000` chapters
against the baseline's 80000 novel target, with
`by_chapter_override={"01": 4000, "02": 4000}`, `current_words_override=8000`,
all three knitting gates `False`, `consecutive_clean=2`, `convergence_target=3`,
`current_chapter=3`, phase `drafting` with the in-order completed prefix.

The verification transcripts captured during planning (reproducible with `uv run
python` against `tests/working_corpus`):

    live_draft_counts:                 (90000, 3)
    corpus_check (spec-draft oracle):  ('gate-ratio-consistent',)
    live_draft_owned:                  {'gate-ratio-consistent'}
    validator_verdict & owned:         set()

    min-mutant of live_draft_counts:
      OVER-counting tree:  real_live=(8000, 2)  mutant=(8000, 2)  -> owned unchanged -> SURVIVES
      UNDER-counting tree: real_live=(90000, 3) mutant=(8000, 2)  -> owned {gate-ratio} -> {} -> KILLED

## Interfaces and dependencies

New corpus surface (test-only; no production dependency added):

- In `tests/working_corpus/_variants.py`: a new `_under_counting_table_spec()`
  factory and a second entry in the existing mapping —

      DIVERGENT_TABLE_VARIANTS: dict[str, WorkingTreeSpec] = {
          "by-chapter-override-over-counts-drafts": _over_counting_table_spec(),
          "by-chapter-override-under-counts-drafts": _under_counting_table_spec(),
      }

  whose under-counting value's `by_chapter_override`/`current_words_override` make
  the `[word_counts]` table *under*-count both proxy quantities relative to the
  on-disk drafts.

- No change to `tests/working_corpus/__init__.py`'s `__all__` (no new symbol; the
  mapping object is unchanged in identity, only its contents grow), beyond a
  docstring refresh.

- No change to `tests/corpus_divergent_fixtures.py` or `tests/conftest.py`: the
  `divergent_table_variant_names` fixture returns `tuple(wc.DIVERGENT_TABLE_VARIANTS)`
  and the `divergent_table_tree` factory looks the variant up by name, so both
  expose the new entry automatically.

- A new self-test module `tests/test_working_corpus_divergent.py` (the
  divergent-table self-tests, moved from `tests/test_working_corpus.py` plus the
  under-counting cases).

No change to `novel_ralph_skill/` source, to `CORPUS_INVARIANT_NAMES`, to
`corpus_check`, to `live_draft_counts`/`live_draft_owned`, or to
`PURE_STATE_INVARIANT_NAMES`. No new external dependency. `cuprum` is not used by
this task (Decision Log D3).

## Revision note

Initial draft (2026-06-24, planning agent). Establishes the under-counting
variant's verified shape (proved against the live corpus, Decision Log D1), the
single-proxy asymmetry (Decision Log D2), the no-cuprum scope (Decision Log D3),
and the decision to fold roadmap addenda 2.1.5.1, 2.1.5.2, and 2.1.5.3 into this
task as prerequisites and companions (Decision Log D4). The execution order is
1, 4, 2, 3, 5 so the per-commit gate stays green across the discrimination
rewrite and the variant addition.

Round-2 revision (2026-06-24, planning agent), resolving the design reviewer's
two blocking points on Work item 1.

- B1 (self-contradictory exemption removal): the round-1 draft's Work item 1
  step 4 instructed removing `tests/test_working_corpus.py`'s inline
  `# pylint: disable=too-many-lines` exemption "so the cap is enforced honestly".
  That is impossible: the module is 599 lines and the moved block (~62 lines)
  leaves it at ~537 lines, still far over the 400-line cap. Step 4 is rewritten
  to state plainly that the exemption stays in place and that the extraction's only
  purpose is to give the NEW under-counting self-test a home in a sibling module
  under the cap (not to relieve the existing exemption). The "remove the
  exemption / enforced honestly" instruction is deleted. The Purpose-adjacent
  Constraints bullet and the Work item 1 Progress entry are reworded to match.
- B2 (conditional orphaned-import deletion): the round-1 draft's Work item 1
  step 3 told the implementer to run `ruff` and "confirm with `leta refs` before
  deleting" the `validator_verdict` and `PURE_STATE_INVARIANT_NAMES` imports. This
  review confirmed both imports (lines 28 and 30) are used only by the moved class
  (sole remaining use at line 599). Step 3 now deletes both unconditionally; the
  `leta refs` check is downgraded to optional belt-and-braces.
- Decision Log D5 records both resolutions with the verifying arithmetic and the
  grep finding.
- The load-bearing D1/D2 numbers (`live_draft_counts == (90000, 3)`,
  `corpus_check == ('gate-ratio-consistent',)`, validator owned verdict empty, and
  the min-mutant returning the table read on the under-counting tree while
  surviving the over-counting tree) were re-verified against the live
  `working_corpus` code under `uv run python` during this revision.
