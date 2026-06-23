# Adversarial Logisphere design review — roadmap 2.1.5 — Round 3

Verdict: PROCEED. No blocking defects. The plan is implementable and
design-conformant as written.

Reviewed against the real worktree source: `tests/working_corpus/_oracle.py`,
`_variants.py`, `_library.py`, `_specs.py` (by reference), `__init__.py`,
`tests/corpus_fixtures.py`, `tests/corpus_live_draft_fixtures.py`,
`tests/conftest.py`, `tests/test_validate_state_live_draft.py`,
`tests/test_working_corpus.py`, `novel_ralph_skill/state/validate.py` (by
reference), `pyproject.toml`, `docs/developers-guide.md`, `docs/roadmap.md`,
`AGENTS.md`. Live line counts and the cuprum consumer set were re-measured, not
trusted from the plan's prose.

## Round-1 / Round-2 carry-over status — all closed

- **B1** (round 1; reversed `corpus_check` tuple order) — FIXED and re-verified.
  `CORPUS_INVARIANT_NAMES` (`_oracle.py` 60-74) places
  `CONSECUTIVE_CLEAN_WITHIN_DRAFTED` at index 5 and `GATE_RATIO_CONSISTENT` at
  index 9; `corpus_check` returns `tuple(name for name in CORPUS_INVARIANT_NAMES
  if not passed[name])` (line 312), so the order-preserving filter yields
  `("consecutive-clean-within-drafted", "gate-ratio-consistent")`. Plan lines
  453-454 and 738-739 assert exactly that. Correct.

- **B2** (round 2; 400-line cap on `corpus_fixtures.py`) — FIXED and re-verified.
  `wc -l` confirms `corpus_fixtures.py` is **393** lines; `pyproject.toml`
  disables `all` (line 186) then re-enables `too-many-lines` in the `enable` list
  (line 300) with `max-module-lines = 400` (line 177), so the cap is
  gate-enforced. The plan no longer grows `corpus_fixtures.py`: Decision Log D5
  (lines 278-302), Constraints (lines 80-94, 117-128), Tolerances, Work item 2
  (lines 480-561), and the Interfaces section all route the two new fixtures into
  a *new* sibling plugin `tests/corpus_divergent_fixtures.py`, registered by
  appending `"corpus_divergent_fixtures"` to the `pytest_plugins` tuple in
  `tests/conftest.py` (currently `("corpus_fixtures",
  "corpus_live_draft_fixtures")`, line 42). This mirrors the documented precedent:
  `corpus_live_draft_fixtures.py` (61 lines, verified) was split out of
  `corpus_fixtures.py` for the same reason, with the rationale recorded in the
  conftest comment (lines 33-42). A mandatory line-budget self-check is now a
  numbered step in Work item 2 (lines 539-548) and step 3 of Concrete steps.
  Inline `# pylint: disable=too-many-lines` on `corpus_fixtures.py` is explicitly
  forbidden. The sanctioned path now exists.

- **A1** (cuprum consumer miscount) — ADDRESSED. Decision Log D4 (lines 259-276)
  now reads "this task touches no cuprum consumer" and lists the five real
  consumers — `conftest.py`, `test_conftest_helpers.py`,
  `test_console_scripts_e2e.py`, `test_novel_state_check.py`,
  `test_venv_scripts_dir.py`. A fresh `grep -rln cuprum tests/` returns exactly
  those five, and none is in this task's edit set. Round-2 advisory A1 is
  explicitly retired in the D4 text (lines 273-275). Correct.

- **A3** (tense rewrite of the landmine clause) — ADDRESSED. Work item 4 (lines
  629-642) now explicitly instructs rewriting the developers-guide clause from
  "a **future** `by_chapter_override` variant" to present tense naming the
  now-existing variant, and to "Leave no stale 'future' in the clause". The real
  paragraph is at `docs/developers-guide.md` 347-350, matching the plan's cite.

- **A4** (Work item 1 build-path / baseline inheritance) — ADDRESSED. Work item
  1 (lines 429-438) now spells out that `_with_chapters` inherits
  `COHERENT_BASELINE`'s `current_chapter`, `consecutive_clean`,
  `convergence_target` and leaves the override fields unset, so the factory must
  set every divergent field explicitly. Verified against source:
  `COHERENT_BASELINE = PHASE_STATES["drafting"]` (`_library.py` 118) sets
  `consecutive_clean=1`, `convergence_target=1`, `current_chapter=len(chapters)`
  (lines 89-91); `_with_chapters` (`_variants.py` 35-45) merges
  `_consistent_gates(chapters)` with explicit `changes`, and explicit gate
  booleans override the honest defaults. The plan's instruction to set the three
  gates `True`, `consecutive_clean=3`, `convergence_target=3`, `current_chapter=2`
  in `changes` is therefore both necessary and sufficient.

## Independent re-trace of the divergent tree (real predicates)

Tree: phase `drafting` with in-order completed prefix; two `draft_words=4000`
chapters (live 8000 words / 2 drafted) against `target_words=80000`;
`by_chapter_override={"01":30000,"02":30000,"03":30000}`,
`current_words_override=90000`; all three knitting gates `True`;
`consecutive_clean=3`, `convergence_target=3`, `current_chapter=2`. This is a
byte-faithful reproduction of the retired 2.1.3 module-local fixture
(`tests/test_validate_state_live_draft.py` 95-160, read this round).

- `corpus_check` (spec-draft oracle) fires exactly
  `consecutive-clean-within-drafted` (drafted=2, `3 <= 2` false) and
  `gate-ratio-consistent` (live ratio 0.10 vs all-`True` gates). `by-chapter-sum`
  silent (override sum 90000 == `current_words_override` 90000),
  `cursor-coherent` silent (`current_chapter` 2 <= 2),
  `consecutive-clean-within-target` silent (`3 <= 3`). D3's isolation holds.
- The §5.2 validator stays silent on the table: numerator
  `sum(by_chapter)=90000`, ratio 1.125 consistent with all-`True` gates; ceiling
  = count of `by_chapter` entries `> 0` = 3 >= counter 3. Owned verdict empty.
- The disagreement on both proxies is real and is the discriminator. `target` is
  written from `spec.target_words=80000`, so 1.125 is the validator's honest
  arithmetic, not an artefact.

## Structural / contract / longevity checks (full crew)

- **Pandalump (structure):** The new `DIVERGENT_TABLE_VARIANTS` category is
  correctly invisible to every agreement loop — all of them iterate only
  `coherent_oracle_cases` and `incoherent_variant_names`. `DONE_FLAG_PERMUTATIONS`
  is a real coherent-but-separate precedent; this is the divergent-but-separate
  analogue. The four-item ordering (data + exclusion self-tests, then fixtures,
  then consumer migration, then docs) keeps every suite green at each commit.
- **Telefono (contracts):** No public contract changes. `CORPUS_INVARIANT_NAMES`,
  `corpus_check`, `PURE_STATE_INVARIANT_NAMES` are untouched; the new name is a
  test-only category key. The deterministic/judgemental boundary is respected —
  no `novel_ralph_skill/` source change; the variant exercises the documented
  validator-versus-live disagreement rather than removing it.
- **Buzzy Bee (scaling):** N/A in the runtime sense; the only "scale" concern is
  module-line budget, now correctly hedged by the split-plugin design and the
  mandatory `wc -l` self-check.
- **Doggylump (failure modes):** see pre-mortem below.
- **Wafflecat (alternatives):** see checkpoint below.
- **Dinolump (longevity):** The new plugin gives the next corpus variant
  (roadmap 2.3.3's disk-authoritative oracle checks) a home, and the landmine
  doc-rewrite keeps a future maintainer from "fixing" the intentional
  disagreement.

## Pre-mortem (Doggylump)

The two failure paths flagged in rounds 1-2 are now defused in the plan:

1. *Self-test stays red and someone reorders the frozen vocabulary.* Closed by
   B1's fix — the tuple assertion matches `corpus_check`'s real order.
2. *Work item 2's gate fails on `too-many-lines` with no sanctioned remedy, and
   the implementer inline-disables the cap.* Closed by B2's fix — the new sibling
   plugin plus the line-budget self-check.

Residual (low) risk, already mitigated in-plan, not blocking:

- *D3 drift:* a later edit that aligns the divergent spec's draft words to the
  table would make `corpus_check` return the empty tuple and silently convert the
  variant to coherent. `test_divergent_table_breaks_both_proxies` pins the exact
  pair and catches this. Keep that pin.
- *test_working_corpus.py line creep:* the module is 534 lines with an inline
  `# pylint: disable=too-many-lines` at line 17. Work item 1 adds only three small
  methods; Constraints (91-94) and Tolerances (129-132) direct extraction rather
  than widening the exemption if they bite. Acceptable.

## Alternatives checkpoint (Wafflecat)

Two alternatives were weighed in prior rounds and remain correctly rejected:
(a) leave the tree as the 2.1.3 module-local fixture — trades away the roadmap's
explicit first-class-ownership goal; (b) trim docstrings to fit the ~7-line
margin in `corpus_fixtures.py` — fragile against `interrogate`'s 100% demand and
re-breaches on the next addition. The chosen split-plugin approach is the durable
move and matches established repo precedent. No new credible alternative emerges;
that is itself a signal the design is on solid ground.

## Conclusion

Every blocking defect from rounds 1 and 2 is fixed and independently re-verified
against real source; both advisories are folded in. The divergent-tree semantics,
the vocabulary order, the cap arithmetic, the cuprum consumer set, the fixture
template, and the baseline-inheritance subtlety all check out. I would stake my
name on this plan being implementable and design-conformant as written.
