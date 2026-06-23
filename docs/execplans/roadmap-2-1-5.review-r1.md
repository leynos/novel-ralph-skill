# Adversarial Logisphere design review — roadmap 2.1.5 — Round 1

Verdict: REVISE (proceed once the blocking defect below is fixed).

Reviewed against the real source in the worktree: `tests/working_corpus/_oracle.py`,
`_live_draft.py`, `_specs.py`, `_variants.py`, `__init__.py`,
`tests/corpus_fixtures.py`, `tests/test_working_corpus.py`,
`tests/test_validate_state_corpus.py`, `tests/test_validate_state_live_draft.py`,
`novel_ralph_skill/state/validate.py`, `docs/developers-guide.md`,
`docs/roadmap.md`, `AGENTS.md`. cuprum claims checked against the read-only
sibling checkout references in-tree.

## What holds up (the plan's core is sound)

Tracing the divergent tree (two `draft_words=4000` chapters, target 80000,
`by_chapter_override={"01":30000,"02":30000,"03":30000}`,
`current_words_override=90000`, all gates `True`, `consecutive_clean=3`,
`convergence_target=3`, `current_chapter=2`) through the real predicates:

- `corpus_check` breaks exactly `consecutive-clean-within-drafted` (drafted=2 <
  3) and `gate-ratio-consistent` (live ratio 0.10 vs all-True gates).
  `by-chapter-sum` stays silent (sum 90000 == current 90000).
  `consecutive-clean-within-target` silent (3 <= target 3). `cursor-coherent`
  silent (2 <= 2). D3's isolation claim is correct.
- `live_draft_owned` returns `{gate-ratio-consistent,
  consecutive-clean-within-drafted}` (words_total 8000, chapters_count 2).
- The validator (`validate.py`) stays silent on the table: gate numerator
  `sum(by_chapter)=90000` -> ratio 1.125 consistent with all-True gates;
  `consecutive-clean` ceiling = count of `by_chapter > 0` = 3 >= 3. Owned
  verdict empty. The disagreement is real and is the discriminator.
- Builder writes `[word_counts].target = spec.target_words` (80000), so the
  validator's 1.125 ratio is correct.
- The category is correctly invisible to every agreement loop: all of them
  iterate only `coherent_oracle_cases` and `incoherent_variant_names`
  (verified in both `test_validate_state_corpus.py` and
  `test_validate_state_live_draft.py`). A separate `DIVERGENT_TABLE_VARIANTS`
  category (D1) is the right model; `DONE_FLAG_PERMUTATIONS` is a real precedent.
- The `done_flag_tree` fixture is the correct template; the proposed corpus
  `divergent_table_tree` takes only `tmp_path`, so dropping the `corpus_builders`
  bundle is justified. Deletion is contained: `divergent_table_tree` /
  `corpus_builders` are referenced only inside
  `test_validate_state_live_draft.py`; `phase_names` survives (used by three
  other modules).
- The developers-guide landmine paragraph exists at lines ~348-351 exactly as
  described; the Work item 4 edit is coherent and additive.
- Gates (`make all`, interrogate 100%, markdownlint, nixie) match AGENTS.md. No
  cuprum/Cyclopts/xdist/timeout behaviour is relied on; firecrawl is correctly
  declared unnecessary.

## BLOCKING

B1. Self-test tuple order is reversed from `corpus_check`'s actual output.
   Work item 1's `test_divergent_table_breaks_both_proxies` (plan line ~365) and
   the Validation/acceptance section (plan line ~589) assert
   `check_corpus(...) == ("gate-ratio-consistent",
   "consecutive-clean-within-drafted")` and label it "(vocabulary order)".
   `corpus_check` returns names in `CORPUS_INVARIANT_NAMES` order, in which
   `consecutive-clean-within-drafted` (index 5) precedes `gate-ratio-consistent`
   (index 9). The actual return is `("consecutive-clean-within-drafted",
   "gate-ratio-consistent")` — the reverse. As written, the red-first self-test
   would stay red after a correct implementation, inviting a spurious "fix".
   Correct both occurrences to `("consecutive-clean-within-drafted",
   "gate-ratio-consistent")`. (The `live_draft_owned` assertions use a set, so
   they are unaffected; only the tuple-returning `corpus_check` assertion bites.)

## ADVISORY

A1. Decision Log D4 overstates the cuprum facts. It claims "the only cuprum
   consumer is `tests/test_console_scripts_e2e.py`". cuprum is in fact imported
   and used by `tests/test_venv_scripts_dir.py`,
   `tests/test_conftest_helpers.py`, `tests/test_novel_state_check.py`, and
   `tests/conftest.py` (`single_program_catalogue`). The operative conclusion
   (this task introduces no cuprum usage and touches none of those files) is
   correct, so this does not block — but the rationale is factually wrong and
   should be corrected to "this task touches no cuprum consumer" rather than
   "there is only one".

A2. Direction mismatch versus the roadmap's illustrative example. Roadmap 2.1.5
   suggests "a `by_chapter_override` that under-counts or omits a drafted
   chapter". The plan implements an over-count (table 90000/3 entries vs drafts
   8000/2). Both satisfy the controlling requirement ("the table mislabels the
   real drafts"), and the over-count reproduces the exact 2.1.3 fixture the
   surviving mutant required, so this is acceptable — but note the inversion in
   the Decision Log so a later reader is not surprised the plan diverges from the
   roadmap's parenthetical.

A3. Minor wording in Work item 4: the landmine paragraph currently says "a
   future `by_chapter_override` variant". After this task the variant is no
   longer future; ensure the edit rewrites that clause (the plan implies but does
   not explicitly call out the tense change).

## Pre-mortem (Doggylump)

- Most likely failure: an implementer writes B1's assertion verbatim, the
  self-test stays red, and they reorder `CORPUS_INVARIANT_NAMES` or the oracle
  loop to "make it pass" — perturbing the frozen vocabulary contract and the
  agreement suites. Prevention: fix B1 in the plan now.
- Second: D3 drift. If a future edit sets the divergent spec's draft words to
  match the table, `corpus_check` returns the empty tuple and the variant goes
  coherent, silently defeating the discriminator. The plan's
  `test_divergent_table_breaks_both_proxies` pin (once B1-corrected) catches
  this; keep it.

## Alternatives checkpoint (Wafflecat)

The strongest alternative is to leave the divergent tree as the module-local
2.1.3 fixture and simply add a self-test asserting it is not in any agreement
loop. It trades away corpus ownership and reuse (the roadmap's explicit goal)
for a smaller diff. Rejected: the roadmap requires first-class §1.3.2 ownership
and retirement of the bespoke fixture, and the plan's four-step landing
(category + exclusion self-tests, then fixtures, then consumer migration, then
docs) is the correct ordering to keep every agreement suite green throughout.
