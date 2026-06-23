# Adversarial Logisphere design review — roadmap 2.1.5 — Round 2

Verdict: REVISE (one blocking defect; proceed once fixed).

Reviewed against the real worktree source: `tests/working_corpus/_oracle.py`,
`_live_draft.py`, `_specs.py`, `_variants.py`, `_library.py`, `__init__.py`,
`tests/corpus_fixtures.py`, `tests/test_validate_state_live_draft.py`,
`tests/test_working_corpus.py`, `novel_ralph_skill/state/validate.py` (by
reference), `docs/developers-guide.md`, `docs/roadmap.md`, `AGENTS.md`,
`pyproject.toml`. Round-1 BLOCKING B1 (tuple order) is confirmed fixed.

## Round-1 carry-over status

- B1 (reversed `corpus_check` tuple order) — FIXED. Plan lines 149 and 597 now
  assert `("consecutive-clean-within-drafted", "gate-ratio-consistent")`, which
  matches `corpus_check`'s `CORPUS_INVARIANT_NAMES`-ordered return
  (`_oracle.py` line 312; index 5 precedes index 9). The set-valued
  `live_draft_owned`/`check_live_draft` assertions (plan lines 128, 593) are
  order-insensitive and correct.
- A1 (cuprum consumer miscount) — NOT addressed. Re-confirmed below; still
  advisory.
- A2 (over-count vs roadmap's "under-count" parenthetical) — acceptable; the
  over-count reproduces the exact 2.1.3 fixture the surviving mutant needed.
- A3 (tense rewrite of the landmine clause) — NOT explicitly folded; still
  advisory.

## What holds up

Re-tracing the divergent tree against the real predicates confirms the core:

- `corpus_check` fires exactly `consecutive-clean-within-drafted` (drafted=2,
  `3 <= 2` false) and `gate-ratio-consistent` (live ratio 0.10 vs all-True
  gates). `by-chapter-sum` is silent (`90000 == 90000`, override sum equals
  `current_words_override`), `cursor-coherent` silent (`0 <= 2 <= 2`),
  `consecutive-clean-within-target` silent (`3 <= 3`), `cursor-plan-present`
  silent (scene/beat 0). D3's isolation holds.
- `live_draft_owned` returns `{gate-ratio-consistent,
  consecutive-clean-within-drafted}` (words_total 8000, chapters_count 2 from
  the on-disk globbed drafts).
- The validator stays silent on the table: numerator `sum(by_chapter)=90000`,
  ratio 1.125 consistent with all-True gates; ceiling = count of `by_chapter`
  entries `> 0` = 3 >= 3. Owned verdict empty. The disagreement is real.
- `derive_by_chapter` writes the 3-entry override verbatim even though only two
  chapter directories exist on disk (`_specs.py` 256-257), so the table/draft
  divergence survives materialisation. `derive_current` writes 90000 verbatim,
  keeping `by-chapter-sum` silent.
- The new `DIVERGENT_TABLE_VARIANTS` category is correctly invisible to every
  agreement loop: `test_live_draft_agreement_over_whole_corpus`,
  `test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling`, and the
  `test_validate_state_corpus.py` suite all iterate only `coherent_oracle_cases`
  and `incoherent_variant_names`. D1's separate-category model is right;
  `DONE_FLAG_PERMUTATIONS` is a real precedent.
- Work item 3's deletion is contained: `divergent_table_tree` and
  `corpus_builders` are referenced only inside `test_validate_state_live_draft.py`
  (the latter solely by the former); `phase_names` survives (used elsewhere).
  The two existing assertions migrate verbatim.

## BLOCKING

B2. Work item 2 breaches the 400-line module cap on `tests/corpus_fixtures.py`,
   which the pylint gate enforces. `corpus_fixtures.py` is currently **393
   lines**. Work item 2 adds two NumPy-docstringed fixtures
   (`divergent_table_variant_names` and the `divergent_table_tree` factory)
   modelled on the `done_flag_permutation_names` / `done_flag_tree` pair, which
   itself spans 44 lines (`corpus_fixtures.py` 309-352). Even a terse rendering
   adds ~40 lines, pushing the file to ~433-440 lines.

   This is not merely the AGENTS.md prose convention: `pyproject.toml` disables
   `all` pylint messages (line 187) then re-enables a specific list, and
   `too-many-lines` (C0302) is in the enable list (line 300) with
   `max-module-lines = 400` (line 177). So `make all` will **fail** the pylint
   pass on `corpus_fixtures.py` once the fixtures land.

   The plan's Constraints (lines 79-82) and Tolerances (lines 99-102) anticipate
   the cap only for `tests/working_corpus/_variants.py`, and provide an
   extraction escape hatch only for that file. `corpus_fixtures.py` — the file
   Work item 2 actually grows — is unguarded. Work item 3 deletes lines from a
   *different* module (`test_validate_state_live_draft.py`), so it does not
   offset the growth.

   Fix: before Work item 2 lands, the plan must (a) verify the post-addition line
   count of `corpus_fixtures.py` against the 400 cap, and (b) specify the
   remedy if it breaches — either trim the new fixtures' docstrings to fit
   within budget (risky, ~7-line margin), or extract the divergent-table
   fixtures (and ideally the symmetric `done_flag_*` pair) into a sibling
   fixture plugin module registered through `pytest_plugins` (mirroring how
   `corpus_fixtures.py` itself was split out of `conftest.py` for the same
   reason — see its module docstring lines 9-14). Add the corresponding
   Tolerance and a self-check step to Work item 2. As written, Work item 2's
   gate run will fail and the plan gives the implementer no sanctioned path.

## ADVISORY

A1 (carried). Decision Log D4 (plan lines 225-232), the Constraints note (lines
   163-168), and Risks still claim "the only cuprum consumer is
   `tests/test_console_scripts_e2e.py`". A grep of `tests/` for `cuprum` returns
   five files: `conftest.py`, `test_conftest_helpers.py`,
   `test_console_scripts_e2e.py`, `test_novel_state_check.py`,
   `test_venv_scripts_dir.py`. The operative conclusion (this task touches no
   cuprum consumer and adds no cuprum behaviour claim) is correct and does not
   block, but the rationale is factually wrong. Reword D4 to "this task touches
   no cuprum consumer" rather than asserting a single one. (Note: round 1 named
   a slightly different file set; the authoritative list is the grep above.)

A3 (carried). Work item 4 (plan lines 504-510) should explicitly instruct
   rewriting the landmine clause's tense. The developers-guide paragraph reads
   "a **future** `by_chapter_override` variant" (line 348-349); after this task
   the variant is no longer future. The plan implies the edit but does not call
   out the tense change; state it so the implementer does not leave a stale
   "future" in place.

A4. Work item 1's self-test build path is under-specified but recoverable. The
   plan says to build the divergent spec "via the existing
   `make_working_tree_spec`/`build_tree` fixtures" or "reuse the `_with_chapters`
   helper pattern where it fits". Note for the implementer: `_with_chapters`
   inherits `COHERENT_BASELINE`'s `phase_completed` (the correct `drafting`
   prefix) but also its `current_chapter`, `consecutive_clean`,
   `convergence_target`, and leaves `by_chapter_override`/`current_words_override`
   unset — all of which the divergent tree must override explicitly in
   `changes`, and the gates must be passed explicitly (not honest). This matches
   the plan's prose (line 354) but the `_divergent_table_spec()` factory must set
   `current_chapter=2` explicitly (baseline is 3 = `len(chapters)`), or
   `cursor-coherent` would still pass at 2 but the intent should be pinned. The
   Work-item-1 self-test `test_divergent_table_breaks_both_proxies` catches any
   slip, so this is advisory, not blocking.

## Pre-mortem (Doggylump)

- Most likely failure now: the implementer follows Work item 2 verbatim, the
  `make all` pylint pass fails on `corpus_fixtures.py` for `too-many-lines`,
  and — with no sanctioned remedy in the plan — they either inline-`# pylint:
  disable` the check (defeating the AGENTS.md cap and the gate) or thrash within
  the 4-attempt tolerance before escalating. Prevention: fix B2 in the plan now
  with an explicit extraction path and a line-budget check.
- Second: D3 drift. If a later edit aligns the divergent spec's draft words with
  the table, `corpus_check` returns the empty tuple and the variant silently goes
  coherent. The Work-item-1 pin
  (`check_corpus(...) == ("consecutive-clean-within-drafted",
  "gate-ratio-consistent")`) catches this; keep it.
- Third: a maintainer "fixes" the intentional validator-versus-oracle
  disagreement. Work item 4's guide edit plus the variant docstring are the
  documented mitigation; ensure they land.

## Alternatives checkpoint (Wafflecat)

The strongest alternative to B2's extraction is to trim the two new fixtures'
docstrings hard enough to fit under 400 lines. Rejected as the primary remedy:
the margin is ~7 lines, interrogate demands 100% docstrings, and the file is
already a split-out-for-size module — a second split for the divergent-table
(and symmetric done-flag) fixtures is the durable move that the next corpus
variant (2.3.3 adds disk-authoritative oracle checks) will also need. The
extraction is the right call; the plan must name it.

## Telefono (contracts) / Dinolump (longevity)

No public contract changes: `CORPUS_INVARIANT_NAMES`, `corpus_check`,
`PURE_STATE_INVARIANT_NAMES` are untouched; the new name is a test-only category
key. The deterministic/judgemental boundary is respected — no
`novel_ralph_skill/` source changes, and the variant *exercises* the documented
validator-versus-live disagreement rather than removing it. The four-item
ordering (data + exclusion self-tests, fixtures, consumer migration, docs) keeps
every agreement suite green throughout, which is the correct longevity-preserving
sequence.
