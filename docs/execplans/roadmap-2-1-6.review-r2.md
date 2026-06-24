# Adversarial Logisphere design review — roadmap 2.1.6 — Round 2

Verdict: REVISE (one residual blocking wording defect; the central design is
sound and was re-verified against live code).

Reviewed against the real source in the worktree:
`tests/working_corpus/_variants.py`, `_oracle.py`, `_live_draft.py`,
`corpus_divergent_fixtures.py`, `tests/test_working_corpus.py`,
`tests/test_validate_state_live_draft.py`, `tests/test_validate_state_corpus.py`,
`docs/developers-guide.md`, `docs/roadmap.md`, `pyproject.toml`, `Makefile`. The
under-counting tree, both oracle verdicts, the validator's owned verdict, and the
`min`-mutant kill/survive behaviour were executed against the live corpus under
`uv run python` during this review.

## Empirical verification (live code, this review)

Built the plan's exact under-counting spec (three chapters `draft_words=30000`/
`target_words=30000`, target 80000, `by_chapter_override={"01":4000,"02":4000}`,
`current_words_override=8000`, all gates `False`, `consecutive_clean=2`,
`convergence_target=3`, `current_chapter=3`) and the existing over-counting
variant, then ran the real oracle, validator, and a `min(live, table)` mutant:

    UNDER: live_draft_counts=(90000, 3)  corpus_check=('gate-ratio-consistent',)
           live_draft_owned={'gate-ratio-consistent'}  validator_owned=set()
           min-mutant owned {gate-ratio} -> set()      => mutant KILLED
    OVER:  live_draft_counts=(8000, 2)
           live_draft_owned={'gate-ratio-consistent','consecutive-clean-within-drafted'}
           min-mutant owned unchanged                  => mutant SURVIVES
           validator_owned=set()

The plan's central thesis (D1, D2) holds exactly. The under-counting tree fires
exactly `gate-ratio-consistent`; `consecutive-clean-within-drafted`,
`by-chapter-sum`, and `cursor-coherent` stay silent; the validator is silent; the
`min`-mutant survives over-counting and dies on under-counting. The single-proxy
asymmetry (D2) is real and forced, not a choice.

## Verified structural claims

- `tests/test_working_corpus.py` is 599 lines; `_variants.py` 300;
  `corpus_divergent_fixtures.py` 84; `test_validate_state_live_draft.py` 208 — all
  as the plan states (`wc -l`).
- `validator_verdict` and `PURE_STATE_INVARIANT_NAMES` in `test_working_corpus.py`
  are used ONLY at line 599 inside the moved `TestCorpusDivergentTable` class
  (imports at lines 28, 30). B2's unconditional-delete instruction is correct.
- The moved block (`_DIVERGENT_KEY` + class, lines 540-599) is 60 lines; removing
  it plus the two imports leaves ~537 lines, still over the 400 cap. The exemption
  must stay. The arithmetic in D5 is sound.
- `divergent_table_variant_names` returns `tuple(wc.DIVERGENT_TABLE_VARIANTS)` —
  the whole mapping by name; the new key is exposed with no fixture change.
- `test_validate_state_live_draft.py` line 173 hard-codes
  `(variant_name,) = divergent_table_variant_names`; the existing discrimination
  test asserts over-counting owned = `{GATE_RATIO_CONSISTENT,
  CONSECUTIVE_CLEAN_WITHIN_DRAFTED}` and live `(8000, 2)` (line 178) — matching
  the plan's Work item 4 expected mapping.
- The corpus and live-draft agreement suites iterate only `coherent_oracle_cases`
  and `incoherent_variant_names`; the new `DIVERGENT_TABLE_VARIANTS` key never
  reaches them.
- `_live_draft.py` lines 171-172 carry the "A future `by_chapter_override`
  variant" framing the plan de-futures; developers-guide line 350 names
  `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]`.
- `make all = build check-fmt lint typecheck test`; `max-module-lines=400` with
  `too-many-lines` re-enabled; interrogate `fail-under=100`; `markdownlint` and
  `nixie` targets exist.

Round-1's B2 is resolved (Work item 1 step 3 now deletes both imports
unconditionally; D5 records it). The bulk of round-1's B1 is resolved (Work item
1 step 4 and D5 state plainly the exemption is kept and explain why removal is
infeasible).

## Blocking defect

B1-residual. The Work item 1 header still reintroduces the exact false framing
round-1's B1 was raised to eliminate. Lines 475-476:

> "the prerequisite that relieves `tests/test_working_corpus.py`'s inline
> `too-many-lines` exemption before the new self-test lands."

"Relieves the exemption" reads as "removes/lifts the exemption" — but Work item
1 step 4 and Decision Log D5 explicitly KEEP the exemption (the module stays at
~537 lines, over the 400 cap). The header therefore contradicts the step it
heads. An
implementer who reads the Work item header first (the normal reading order) is
told the extraction relieves the exemption, then told three paragraphs later to
keep it. This is the same self-contradiction round-1 flagged as blocking, and it
reintroduces the round-1 pre-mortem landmine ("someone deletes the kept exemption
because the framing suggested it was removable").

Fix (one line, no design change): reword line 475-476 to state the truth — the
extraction gives the NEW under-counting self-test a home in a sibling module under
the cap; it does NOT relieve `test_working_corpus.py`'s exemption, which stays.
Likewise tighten the Plan-of-work sentence at line 467 ("first relieves the
self-test module's line pressure") so "relieve" does not read as "remove the
exemption" — speak of "reducing the over-cap module's size while keeping its
exemption", or drop the word.

## Advisory (non-blocking)

A1 (carried from round 1, unaddressed). Work item 2's prose (lines ~589-618) still
contains the ~25-line internal monologue that argues itself into "That violates
the per-commit gate" before reversing to the correct 1,4,2,3,5 order. The
conclusion and the Concrete steps are correct; the dithering should be cut to the
conclusion to spare the implementer a false trail. Round 2 did not touch it.

A2 (carried from round 1). `_specs.py`'s module docstring wrongly claims it
declares the `build_working_tree` factory; that factory lives in `_builder.py`
(verified: `__init__.py` imports `build_working_tree` from `._builder`). Pre-
existing and out of scope, but Work item 2 cites `_specs.py` as a reference — note
it so the implementer locates the builder correctly.

A3 (carried). `_variants.py` margin: 300 + a symmetric ~45-60-line factory lands
~345-360, under 400 but not "ample". Keep the under-counting docstring tight.

A4 (round-1 A4 was actioned in the over-counting factory — its docstring now sets
every divergent field explicitly, lines 259-261). Carry the same explicitness and
the same before/after mutant transcript discipline into the under-counting factory
and Outcomes.

## Pre-mortem (Doggylump)

Most likely six-months-later failure unchanged from round 1: a later
`DIVERGENT_TABLE_VARIANTS` member added without a Work item 4 expected-mapping
entry. The plan's loud-`KeyError` guard (assert each iterated key has an expected
entry) is the single most valuable defensive line; keep it. Second scenario:
someone deletes the kept `too-many-lines` exemption because the Work item 1 header
(B1-residual) still says the extraction "relieves" it. Fixing B1-residual removes
that landmine — which is precisely why it remains blocking rather than advisory.

## Alternatives checkpoint (Wafflecat)

Re-confirmed: driving the under-counting divergence through
`consecutive-clean-within-drafted` instead of `gate-ratio-consistent` is
IMPOSSIBLE for an under-counting table (the table chapter count is a smaller
ceiling than the live count, so the live proxy cannot fire while the validator
stays silent — proved in D2 and re-verified here). The single-proxy choice is
forced. No credible structural alternative exists; the design space is genuinely
narrow, a strong signal the approach is correct.

## Conformance

- Deterministic/judgemental boundary: untouched. Test-corpus, oracle data, and
  docs only; no `novel_ralph_skill/` source change.
- Contracts: `CORPUS_INVARIANT_NAMES`, `corpus_check`, `live_draft_counts`,
  `live_draft_owned`, `PURE_STATE_INVARIANT_NAMES` all stable; the new variant is
  a value under the existing `DIVERGENT_TABLE_VARIANTS` key, no new symbol.
- Category placement: correctly `DIVERGENT_TABLE_VARIANTS`, not
  `INCOHERENT_VARIANTS` and not `coherent_oracle_cases`/`PHASE_STATES` (verified
  against the agreement-suite iteration sets).
- Cuprum: D3 correct — no cuprum consumer touched; oracle and corpus run in-process
  over `tmp_path`. No uncited cuprum claim. No Cyclopts/pytest-timeout/uv behaviour
  asserted. Nothing requires firecrawl.
- Roadmap 2.1.6 success criteria and addenda 2.1.5.1/.2/.3 (folded via D4) are all
  covered.

Fix B1-residual (one-line wording correction) and the plan is implementable and
design-conformant as written. Every load-bearing technical claim is verified true
against live code.
