# Logisphere design review — ExecPlan roadmap-2-3-3 (round 1)

Verdict: REVISE. The reroute itself (Work item 1) is sound and well-anchored, but
Work item 2's divergence-proof tests are specified against an acceptance
criterion ("verdict equals the singleton `{name}`") that is provably infeasible
for two of the three cases, because the corpus already has a sixth disk-evidence
predicate — `word-counts-match-drafts` — that co-fires on exactly the mutations
the plan proposes. The plan equivocates between "singleton" and "exact set
including co-fires" without resolving which, leaving the load-bearing test design
undetermined.

## Blocking

1. **Case 1 (`rmtree` a chapter directory) co-fires `word-counts-match-drafts`.**
   `_check_word_counts_match_drafts` (`_oracle.py` lines 273-294) reads the
   manifest from `state.toml` (entry still present after `rmtree`), then reads
   `manuscript/chapter-NN/draft.md` via `_disk_by_chapter` — directory gone, so
   the count is 0 while the `[word_counts].by_chapter` table still holds the
   chapter's non-zero count. Disk (0) ≠ table (N) ⇒ `word-counts-match-drafts`
   fires alongside `manifest-disk-bijection`. The plan's parenthetical defence —
   "a chapter whose table entry is non-zero, making the bijection the sole break"
   — is backwards: a non-zero table entry *guarantees* the word-count co-fire. The
   singleton assertion in Work item 2 case 1 cannot hold on `COHERENT_BASELINE`
   (chapters 24000/24000/20800, all non-zero). Specify the exact expected set
   (`manifest-disk-bijection`, `word-counts-match-drafts`) or construct the case
   on a chapter with a zero table entry — but a zero entry contradicts the plan's
   own "non-zero" requirement, so the planner must pick a concrete, verified
   construction and state it, not hedge.

2. **Case 2 (empty a draft beside `done.flag`) co-fires `word-counts-match-drafts`
   and possibly `compiled-matches-drafts`.** Emptying `chapter-NN/draft.md`
   (24000 → 0 tokens) makes disk 0 vs table 24000 ⇒ `word-counts-match-drafts`
   fires with the targeted `done-flag-without-draft`. If a `compiled.md` is
   present and included that draft body, `compiled-matches-drafts` also fires.
   The singleton assertion is infeasible. The plan must specify the exact
   multi-name expected set, confirmed against a concrete tree, and justify it
   as a Decision — not promise a singleton it cannot deliver.
   (`COHERENT_BASELINE` has no `compiled.md`, so the compiled co-fire is
   avoidable, but the word-count co-fire is not.)

3. **Acceptance criterion is internally contradictory.** Work item 2's "Tests to
   add" says each test "asserts the verdict equals the singleton `{name}`", while
   the same section's tail and the Risks section say "where a mutation unavoidably
   co-fires a second invariant, assert the exact expected set." Given (1) and (2),
   the co-fire is unavoidable for two of three cases, so the singleton form is the
   wrong default and the plan never commits to the actual expected tuples. An
   implementer cannot write these tests deterministically from the plan as
   written. Resolve by stating, per case, the exact expected `corpus_check` tuple
   (in `CORPUS_INVARIANT_NAMES` vocabulary order) verified against a concrete
   built-and-mutated tree, and recording each co-fire as a Decision.

## Advisory

- **Work item 3 dev-guide edit targets text that does not assert the
  asymmetry.** The plan says to edit "the sentence describing the deliberate
  twins (`docs/developers-guide.md` lines 426-434) so it no longer implies three
  oracle predicates read the spec while production reads disk." Lines 426-434
  describe the **six pure-state §5.2 twins** in `validate.py`; they say nothing
  about the disk-evidence predicates' spec/disk asymmetry. The asymmetry
  statement lives only in `disk_evidence.py` lines 29-33 (the module docstring).
  No dev-guide sentence currently "implies three oracle predicates read the
  spec", so the planned dev-guide edit either is unnecessary or risks
  inventing a claim. Re-scope Work item 3 to the `disk_evidence.py` comment
  only, or point at the actual dev-guide text (lines 336-348 describe the six
  disk-evidence invariants neutrally and need no change).

- **Compiled-reroute helper is unnamed.** The plan says the expected
  concatenation is "computed from the present on-disk `draft.md` bodies ... via
  `concatenate_drafts`", but the oracle has no disk-reading draft-body helper;
  `_specs._present_draft_bodies` reads the spec. The implementer must add a
  disk-reading helper mirroring production `_present_draft_bodies(state,
  working_dir)` (`disk_evidence.py` lines 156-168) and decide its order source
  (manifest from `state.toml`, as `_disk_by_chapter` already does). Name it and
  fix the order source to avoid a second on-disk convention.

- **Case 3 needs a count-preserving edit to stay a clean singleton.** Editing a
  draft so `compiled.md` goes stale will also co-fire `word-counts-match-drafts`
  unless the edit preserves the whitespace token count (e.g. replace tokens with
  same-count different tokens). The plan does not state this. With a
  count-preserving edit, case 3 *can* be a clean `compiled-matches-drafts`
  singleton; specify the edit precisely.

## Confirmed sound

- Line anchors for the three predicates (`_oracle.py` 158-171, 212-221, 234-248)
  and the "Twin asymmetry" comment (`disk_evidence.py` 29-33) are accurate.
- The three predicates are referenced externally only via the name constants
  (`oracle.MANIFEST_DISK_BIJECTION`, etc.) in `_variants.py`; no external caller
  invokes the predicate functions, so the `(spec)` → `(working_dir)` signature
  change is contained within `_oracle.py`, as claimed.
- The `cuprum` non-use claim holds: no `cuprum` reference under
  `tests/working_corpus/`, `tests/test_working_corpus*.py`,
  `tests/test_disk_evidence.py`, or `tests/test_novel_state_check_disk.py`. The
  oracle reads disk with `pathlib`/`tomllib` only; no locked-library behaviour is
  load-bearing, so no firecrawl research is required.
- The deterministic/judgemental boundary is respected: the change is test/oracle
  only, invokes no external process, and the production §5.4 detector already
  reads disk for all six invariants.
- The fix-round-1 precedent (`_check_by_chapter_sum` now reads `working_dir`,
  `_oracle.py` lines 114-125) is real and is the correct template for the reroute.
- File caps: `_oracle.py` is 366 lines; the reroute is roughly net-neutral. The
  new self-test correctly lands in a sibling module, mirroring
  `tests/test_working_corpus_divergent.py` (138 lines).
