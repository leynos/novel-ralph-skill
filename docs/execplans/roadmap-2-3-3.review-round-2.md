# Logisphere design review — ExecPlan roadmap-2-3-3 (round 2)

Verdict: REVISE. Revision 2 resolves the round-1 co-fire blocking points
correctly — the two co-firing tests now assert the exact, empirically-correct
two-name tuples, and all four expected tuples were reproduced against concrete
built-and-mutated trees (see Evidence below). But one of the two new
clean-singleton tests is built on a construction that cannot prove what the test
claims to prove, and in fact fails the plan's own red-first guarantee and the
roadmap's success criterion. That is a single, precise, addressable defect.

## Blocking

1. **Clean-singleton bijection test (Work item 2, test 2) uses a construction
   that does not diverge spec-from-disk, so it proves nothing about disk
   reading.** The plan specifies
   `test_manifest_bijection_caught_from_disk_for_structural_mismatch` as
   "reuse the `manifest-extra-entry` construction (a `manifest_only_numbers`
   entry with no on-disk directory) built directly through the spec fixtures …
   assert the verdict is exactly `(manifest-disk-bijection,)` … This proves the
   disk-reading bijection check fires in isolation" (execplan lines 658-666;
   D-CLEAN).

   It does not. The `manifest-extra-entry` spec
   (`_variants.py` lines 135-138: `dc.replace(_BASE, manifest_only_numbers=(4,))`)
   declares a non-bijective manifest *in the spec*: `manifest = {1,2,3,4}`,
   `on_disk = {1,2,3}`. The **current spec-reading** oracle already returns
   `('manifest-disk-bijection',)` for it — confirmed by a probe run:

   ```plaintext
   manifest-extra-entry SPEC-reading corpus_check: ('manifest-disk-bijection',)
   ```

   So the assertion `corpus_check(spec, working) == ('manifest-disk-bijection',)`
   passes **identically** against the spec-reading and the disk-reading oracle.
   The test therefore:
   - violates the plan's own red-first guarantee (execplan lines 631-641: "a
     spec-reading predicate would miss the divergence and the test would fail
     against the pre-reroute oracle"). This test would *pass* against the
     pre-reroute oracle.
   - misses the roadmap's success criterion (roadmap lines 674-677: "a tree
     whose `state.toml` claims agree with disk but whose disk evidence diverges
     is flagged by the oracle from disk alone"). In `manifest-extra-entry` the
     `state.toml` manifest does **not** agree with disk — the divergence is
     baked into the spec, not introduced by a post-build disk mutation.

   The good news: a genuine clean bijection divergence singleton **is**
   constructible, so this is a fix, not a dead end. Build `COHERENT_BASELINE`
   (spec bijection holds), assert `()` on the unmutated tree, then post-build
   `(working/"manuscript"/"chapter-04").mkdir()` — add an on-disk chapter
   directory that is **absent from the manifest** and carries no `draft.md`.
   Verified:

   ```plaintext
   baseline bijection_ok: True wordcounts_ok: True
   after mkdir chapter-04: bijection_ok: False wordcounts_ok: True
   ```

   This breaks the disk bijection (`manifest-disk-bijection` fires), keeps
   `word-counts-match-drafts` silent (the extra directory is not in
   `state["chapters"]`, so `_disk_by_chapter` never reads it), keeps
   `done-flag-without-draft` silent (the done-flag loop iterates only manifest
   chapters), and keeps `compiled-matches-drafts` silent
   (`COHERENT_BASELINE` writes no `compiled.md`). The spec is unchanged and
   coherent between the two `corpus_check` calls, so the spec-reading oracle
   returns `()` after the mutation — red-first holds, and it is a true
   state-agrees/disk-diverges singleton, exactly the roadmap criterion. Re-specify
   test 2 around this `mkdir` mutation (or another genuine post-build disk
   mutation), drop the `manifest-extra-entry` reuse, and record the corrected
   construction as a Decision. Re-confirm the tuple with a probe as the plan does
   for the others.

## Advisory

- **The two co-fire tests' red-first rationale is imprecise (not wrong, but the
  stated explanation does not hold).** D-COFIRE1 (`rmtree` chapter-NN) and
  D-COFIRE2 (empty a flagged `draft.md`) assert the correct two-name tuples —
  both were reproduced. But the plan's blanket claim that "a spec-reading predicate
  would miss the divergence" (execplan lines 640-641) is not the reason these
  tests are red against the pre-reroute oracle. The already-disk-reading
  `word-counts-match-drafts` predicate (rerouted in task 2.3.2) fires on both
  mutations even on the *spec-reading* oracle:

  ```plaintext
  D-COFIRE1 rmtree ch3:  disk-reading ('manifest-disk-bijection', 'word-counts-match-drafts')
                         spec-reading ('word-counts-match-drafts',)
  D-COFIRE2 empty ch1:   disk-reading ('done-flag-without-draft', 'word-counts-match-drafts')
                         spec-reading ('word-counts-match-drafts',)
  ```

  The tests are still discriminating — the pre-reroute tuple is one name, the
  asserted tuple is two, so exact-equality fails red against the pre-reroute
  oracle — but it is the **added** name (`manifest-disk-bijection` /
  `done-flag-without-draft`) that proves the reroute, not the whole tuple.
  Tighten the plan's prose so the implementer understands *which* name carries
  the red-first signal for each co-fire test; otherwise a "local revert" check
  (execplan lines 697-702) done against the wrong predicate could mislead. The
  test assertions themselves need no change.

- **`_oracle.py` is 366 lines, not 367** (execplan lines 167, 174 say 367).
  Cosmetic; the net-neutral reroute keeps it under the 400-line cap regardless.

## Confirmed sound (do not relitigate)

- **Round-1 blocking points 1-3 are resolved.** The co-fire tuples are now
  exact, in `CORPUS_INVARIANT_NAMES` vocabulary order, and empirically correct:
  `manifest-disk-bijection` (index 6) precedes `word-counts-match-drafts`
  (index 13); `done-flag-without-draft` (index 10) precedes
  `word-counts-match-drafts` (index 13). Both reproduced against concrete trees.
- **Clean-singleton test 1 (count-preserving compiled edit) is sound.** With
  `compiled=COMPILED_AUTO` and a count-preserving draft edit, the spec-reading
  oracle returns `()` after the edit (red-first holds — the spec's
  `draft_words` is unchanged, so a spec-recomputed concatenation still matches
  the stale `compiled.md`) while the disk read fires `(compiled-matches-drafts,)`
  alone. Verified, including token-count preservation.
- **Work item 1 is sound.** Line anchors (`_oracle.py` 158-171, 212-221,
  234-248) accurate. The reroute mirrors the production twin exactly; the
  builder materializes the spec faithfully, so every existing corpus verdict is
  preserved and the three named agreement suites
  (`test_union_detector_agrees_with_corpus_oracle`,
  `test_word_counts_twin_equals_corpus_oracle`,
  `test_incoherent_agreement_restricted_to_owned`) stay green — all three exist
  exactly as cited. `_disk_present_draft_bodies` (D-COMPILED-HELPER) correctly
  mirrors production `_present_draft_bodies(state, working_dir)`.
- **D-DEVGUIDE is correctly re-scoped.** developers-guide lines 426-434 describe
  the six pure-state §5.2 twins in `validate.py` (verified) and make no
  disk-evidence asymmetry claim; lines 336-348 describe the disk-evidence
  invariants neutrally. Editing only the `disk_evidence.py` lines 29-33 comment
  is the honest scope.
- **Deterministic/judgemental boundary respected.** Test/oracle-only; invokes no
  external process; production §5.4 detector already reads disk for all six
  invariants. No production behaviour or design-document change.
- **`cuprum` non-use holds and no locked-library behaviour is load-bearing.** No
  `cuprum` reference anywhere under `tests/working_corpus/`,
  `tests/test_working_corpus*.py`, `tests/test_disk_evidence.py`, or
  `tests/test_novel_state_check_disk.py`. The oracle uses `pathlib`/`tomllib`/
  stdlib only; no Cyclopts, pytest-timeout, or `uv` behaviour is exercised, so
  no firecrawl citation is required (verified against the real cuprum source at
  /data/leynos/Projects/cuprum and by grep).

## Pre-mortem (Doggylump)

Six months on, the corpus suite goes green but the bijection reroute silently
regresses to a spec read in a later refactor, and nobody notices — because the
one test meant to guard the disk path (clean-singleton test 2) was built on
`manifest-extra-entry`, whose spec already breaks the bijection, so it passes
whether the predicate reads disk or spec. The fix designed in now: re-specify
test 2 around a post-build disk-only mutation (`mkdir chapter-04`) so the test
is red against any spec-reading bijection predicate.

## Alternatives checkpoint (Wafflecat)

The plan's four-test design (two clean singletons + two co-fires) is the right
shape and matches the roadmap criterion once test 2 is corrected. The only
credible alternative — assert membership (`name in verdict`) instead of exact
tuple equality to sidestep the co-fire bookkeeping — is strictly worse: it was
the round-1 failure mode, hides regressions that add a spurious name, and the
plan rightly rejects it. No better alternative exists; exact-tuple equality on a
genuine post-build divergence is correct.
