# Logisphere design review — roadmap 2.3.8, round 1

Adversarial pre-implementation review of `docs/execplans/roadmap-2-3-8.md`
(re-key `word-counts-cover-drafts` off the on-disk drafted subset). Source
claims were verified against the real tree, not the planner's summary.

## Verdict

Revise. The plan is unusually rigorous and almost all of its load-bearing
source claims check out against the real code. Two precedence/gating defects in
Work item 3 (Decision D3) are genuine ADR 008 risks and must be closed before
implementation.

## What was verified true (so it is not re-litigated)

- `_check_word_counts_cover_drafts` defers on `manifest != on_disk`
  (`_disk_word_counts.py` lines 128-130); recompute is manifest-keyed via
  `disk_word_counts`/`recount_words`. Plan's mechanism is accurate.
- `derive_reconciliation` reads the **strict** bijection (`reconcile.py` line
  352, default flag), the refuse arm (365-367) precedes the recount arm
  (372-378); `MANIFEST_DISK_BIJECTION ∈ _REFUSE_CLASS` (101-106). Risk 1 is
  real.
- `recount_words` keys `by_chapter` off the full manifest, `0` for absent draft
  (`wordcount.py` D-KEY, 129-133). The D2 convergence argument holds: after a
  manifest-keyed RECOUNT `drafted_keys ⊆ table_keys`, so the missing-only
  detector cannot re-fire.
- `_classify_bijection.coherent_subset = not orphans and contiguous`
  (`_disk_paths.py` 99-109). Plan's extra `on_disk < manifest` gate is sound.
- The behavioural pin
  `test_cover_drafts_silent_on_relaxed_subset_with_drifted_table`
  exists (line 196) and pins the old deferral; it uses an **extra** key (`04`)
  drift, not a missing-drafted-key drift. WI2's replacement uses a different
  tree (omit `02`); the planner must not claim the identical tree flips — under
  D2 the original extra-key tree stays silent even after 2.3.8 (extra
  suppressed on a relaxed subset). WI2 wording is consistent with this.
- Oracle twin `_check_word_counts_cover_drafts(working_dir)` takes only
  `working_dir` and inlines the bijection rule; `_disk_by_chapter` is
  manifest-keyed. The required end signature (add kw-only `relax_drafting`) is
  implementable; the oracle must compute the drafted subset itself (no shared
  `_classify_bijection` — deliberate-twin discipline). Plan acknowledges this.
- Corpus variants and twin-agreement tests exist at the cited locations
  (`_variants.py` 212-219; `test_disk_evidence.py` 241).
- WI5 cuprum APIs (Decision D5) are **already in active use** in
  `tests/test_reconcile_e2e.py` (lines 49, 221-240): `ProgramCatalogue`,
  `Program`, `sh.make(...).run_sync`, `ExecutionContext(cwd=...)`,
  `CommandResult.exit_code/.stdout/.stderr`. Proven by existence — no firecrawl
  needed. The fast entry-point e2e drives `novel.main()` via argv (no cuprum).
- No existing installed-binary cover-gap test exists, so WI5's conditional
  ("only if one already exercises the cover-gap at bijection") resolves to *not
  adding* the slow variant — defensible under AGENTS.md atomicity.
- ADR 009 deferral language (line 171, "deferred to a later roadmap task") and
  developers-guide "not enforced" prose (784-792) exist as WI6 describes. Phase
  is imported in `disk_evidence.py` but not yet in `_disk_word_counts.py`
  (WI1's import is required and correct).

## Blocking defects

### B1 — D3 pre-arm position relative to the set-chapters COMPLETE arm is unpinned

`derive_reconciliation` has the set-chapters COMPLETE exception and the refuse
arm both around line 361-367. D3 says the new cover-drafts pre-arm runs "BEFORE
the strict refuse-class arm" but never states its position relative to the
**set-chapters COMPLETE arm**. A torn `set-chapters` turn that is a coherent
drafting subset (manifest `{1,2,3}`, on-disk `{1}`, the
`test_partial_directory_torn_turn_completes` shape) with a hand-edited cover
gap (table omits a drafted key) would, if the pre-arm runs first, RECOUNT
instead of COMPLETE — silently abandoning the pending-turn completion and
violating ADR 008. The existing set-chapters tests do not catch this because
their `by_chapter` always covers the manifest (no cover gap), so the regression
is latent.

Fix: pin the pre-arm to run **after** the set-chapters COMPLETE arm and
**before** the refuse arm, and add a regression test (torn set-chapters turn at
drafting, coherent subset, table omitting a drafted key) asserting
COMPLETE_PENDING_TURN still wins, not RECOUNT.

### B2 — D3 pre-arm is under-gated against uncleared pending turns and second refuse-class members

The D3 gate is only (a) phase drafting, (b) coherent subset, (c) cover
missing-direction. It does not exclude trees carrying an uncleared
`[pending_turn]` (whose `pending-turn-cleared` would drive COMPLETE/ROLLBACK at
arm #3) or a **second** refuse-class violation. Because the pre-arm sits ahead
of both the refuse arm and the pending-turn arm, a torn write-draft turn (or
any non-set-chapters torn turn) on a coherent drafting subset with a cover gap
would be pre-empted into a RECOUNT, masking the COMPLETE/ROLLBACK/REFUSE the
tree needs. `_set_chapters_turn_explains_bijection` already guards this with
`fired_refuse == {MANIFEST_DISK_BIJECTION}`; the new pre-arm needs the
analogous guard.

Fix: gate the pre-arm so it fires only when the fired refuse-class set is
exactly `{manifest-disk-bijection}` AND no uncleared `[pending_turn]` is
present (or prove that co-occurrence is unreachable). Add a regression test for
a torn non-set-chapters pending turn on a coherent drafting subset that also
carries a cover gap, asserting the pending-turn action wins (not RECOUNT).

## Advisory (non-blocking)

- WI1 must compute `missing = drafted_keys - table_keys` over the **on-disk
  drafted subset**, never the manifest-keyed recount key set; otherwise
  undrafted manifest keys over-fire. The plan says this; make it explicit in
  the predicate body and the convergence property test so an implementer cannot
  reach for the manifest set by reflex.
- A chapter directory may exist with an absent/empty `draft.md` (count 0). It is
  still "on disk" (`_on_disk_chapter_numbers` keys on the directory).
  Convergence still holds, but the WI1 docstring should state that "drafted"
  means directory-present, not non-empty, to avoid an implementer adding a
  non-empty filter that would break convergence.
- WI6 ADR 009 line citations drift slightly ("154-163"/"165-172" vs actual
  154-160/165-171). Cosmetic; fix when editing.
- WI2's relaxed verdict must be taken from
  `check_disk_evidence(..., relax_drafting_bijection=True)`, not the
  bijection-only `_bijection_verdict`
  helper (which only runs `_check_manifest_disk_bijection`). The module already
  imports `check_disk_evidence`; state this in WI2 so the new test wires the
  full detector.
