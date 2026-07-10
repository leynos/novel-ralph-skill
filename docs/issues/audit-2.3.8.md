# Post-merge audit — roadmap task 2.3.8

Audit of the codebase after task 2.3.8 ("Re-key `word-counts-cover-drafts` off
the on-disk drafted subset") merged to `main` at commit `5b9902c`. The task
re-keyed `_check_word_counts_cover_drafts` so the gate stays enforced mid-draft:
under the ADR 009 `relax_drafting` flag, during a coherent disk-subset-of-manifest
break in `drafting`, the detector keys off the on-disk drafted subset and fires
the *missing* direction only (a drafted chapter the `by_chapter` table omits). It
introduced a `reconcile` precedence helper (`_reconcile_precedence.py`) with a
scoped, drafting-gated `RECOUNT` pre-arm (`_drafting_subset_cover_gap`) that runs
after the torn `set-chapters` COMPLETE arm and before the refuse arm, so strict
`reconcile` agrees with the relaxed verdict the user-facing `check` reports for
the same tree. ADR 009, the harness design doc, and the developers' guide were
updated to record the re-key.

Trail followed: `docs/novel-ralph-harness-design.md` §5.4,
`docs/adr-009-drafting-bijection-relaxation.md` (drafting bijection relaxation,
"Known risks"), `docs/developers-guide.md` §"Invariant validation"/bijection
relaxation section, `docs/roadmap.md` task 2.3.8,
`docs/execplans/roadmap-2-3-8.md` and its Logisphere review round (design-review
blocking points B1, B2), `docs/adr-008-chapter-manifest-mutator.md` (D8, the
sibling `set-chapters` COMPLETE precedence), and `AGENTS.md` (quality gates, the
400-line cap, CQS, the deliberate-twin discipline). Navigation and history were
traced with `leta` and `sem`; fallback `grep` was used to enumerate the
`relax_drafting` call sites across production and the corpus oracle. The
`python-router` skill routed the Python review (data-shapes for the proposed
classification value, types-and-apis for the proposed shared predicate). Files
inspected: `novel_ralph_skill/state/_reconcile_precedence.py`,
`novel_ralph_skill/state/_disk_word_counts.py`,
`novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/_disk_paths.py`,
`tests/working_corpus/_oracle_disk.py`,
`tests/test_cover_drafts_relaxation.py`,
`tests/test_relaxed_subset_reconcile.py`, `tests/test_relaxed_subset_e2e.py`,
`tests/test_drafting_bijection_relaxation.py`, `tests/features/reconcile.feature`.

The merged change is high quality and tightly scoped. The strict/relaxed split
between `check` and `reconcile` is preserved (only the user-facing `check` passes
the relaxation flag; `derive_reconciliation` reads the strict bijection and gates
the pre-arm itself), the precedence ordering is pinned with explicit B1/B2
rationale, the missing-only direction is justified for convergence, and the
production detector and corpus oracle twin gained matching relaxed branches under
the deliberate-twin discipline. The findings below are refinements; none is a
defect in the merged behaviour.

## Finding 1 — `_drafting_subset_cover_gap` re-derives the relaxed-subset shape its own detector already gates on (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/state/_reconcile_precedence.py`
`_drafting_subset_cover_gap` lines 152-169, against
`novel_ralph_skill/state/_disk_word_counts.py`
`_check_word_counts_cover_drafts` lines 173-195.

**Description:** The reconcile pre-arm predicate independently recomputes the same
relaxed-subset shape the detector it then calls already recomputes internally.
`_drafting_subset_cover_gap` reads `state.phase.current == Phase.DRAFTING`
(line 154), globs the disk via `_on_disk_chapter_numbers` (line 157), and
computes `on_disk < manifest and _classify_bijection(...).coherent_subset`
(lines 156-159) — then calls `_check_word_counts_cover_drafts(..., relax_drafting=
True)` (line 167), which immediately recomputes `manifest`, re-globs disk via its
own `_on_disk_chapter_numbers` (line 174), re-checks the drafting phase
(line 189), and re-computes the identical subset predicate (lines 190-192) before
delegating to `_drafted_subset_cover_violation`. The two sites encode the same
gate in two places: a future change to "what counts as a relaxed subset" must be
made in both or they silently disagree. On the relaxed-reconcile path this also
re-reads the manuscript directory at least three times for one verdict
(`check_disk_evidence`'s bijection + cover-drafts predicates, then this pre-arm,
then `_recount` → `disk_word_counts` → `recount_words`), so the redundancy is a
cost as well as a divergence risk.

**Proposed fix:** Have `_drafting_subset_cover_gap` perform only the guards the
detector does *not* already own — `state.pending_turn is None` and
`fired_refuse == {MANIFEST_DISK_BIJECTION}` — and let the
`_check_word_counts_cover_drafts(..., relax_drafting=True) is not None` call be
the sole owner of the phase/subset shape (it already returns `None` outside that
shape, so the gap predicate stays correct). This removes the duplicated
phase/subset computation from the pre-arm. If the extra disk globbing is a
measurable concern, thread the already-computed `on_disk` set (and optionally the
`_BijectionBreak`) from `derive_reconciliation` down through the pre-arm and the
detector so the manuscript directory is globbed once per `reconcile`.

## Finding 2 — the `fired_refuse == {MANIFEST_DISK_BIJECTION}` "sole refuse-class" guard is duplicated across the two scoped pre-arms (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/_reconcile_precedence.py`
`_set_chapters_turn_explains_bijection` lines 105-107 and
`_drafting_subset_cover_gap` lines 163-164.

**Description:** Both scoped precedence exceptions express the identical "the
fired refuse-class set is exactly `{manifest-disk-bijection}`" guard — the B2
safeguard that stops either arm masking a co-occurring second contradiction — by
hand: `fired_refuse = {name for name in fired if name in _REFUSE_CLASS}` followed
by `if fired_refuse != {MANIFEST_DISK_BIJECTION}: return False`. The two
docstrings even cross-reference each other as "the analogue" of this guard. The
literal is load-bearing (it is the single line that keeps the precedence from
swallowing a second refuse-class member), so duplicating it invites the two arms
to drift apart under a future edit.

**Proposed fix:** Extract a single private predicate in
`_reconcile_precedence.py`, e.g.
`_sole_refuse_is_bijection(fired: cabc.Sequence[str]) -> bool` returning
`{name for name in fired if name in _REFUSE_CLASS} == {MANIFEST_DISK_BIJECTION}`,
and call it from both arms. The shared name documents the B2 invariant in one
place and pins both arms to the same notion of "lone bijection break".

## Finding 3 — the "strict coherent subset" idiom is recomputed inline at three production sites (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/_disk_word_counts.py` lines 190-192;
`novel_ralph_skill/state/_reconcile_precedence.py` lines 158-159; and the
corpus oracle twin `tests/working_corpus/_oracle_disk.py` lines 238-240 (the
fourth, deliberately independent, copy).

**Description:** The notion "the on-disk set is a strict, coherent subset of the
manifest" is spelled as `on_disk < manifest and _classify_bijection(manifest,
on_disk).coherent_subset` in `_check_word_counts_cover_drafts` and again in
`_drafting_subset_cover_gap`. `_BijectionBreak.coherent_subset` already centralizes
the "no orphan, contiguous" half (audit:2.1.7 Findings 1 and 2), but the strict
`on_disk < manifest` half is left dangling beside it at each site, so the full
"strict coherent subset" predicate is not single-homed. `coherent_subset` is
documented as "the only possible break is missing-direction" — which already
implies a non-empty `missing` when `on_disk != manifest` — so the extra
`on_disk < manifest` clause is subtly redundant with `not is_bijection`, and
spelling it twice obscures that.

**Proposed fix:** Add a `strict_coherent_subset` property to `_BijectionBreak`
(in `_disk_paths.py`) returning `self.coherent_subset and bool(self.missing)`
(equivalently `self.coherent_subset and not self.is_bijection`), and replace the
two production inline expressions with `_classify_bijection(...).strict_coherent_subset`.
This collapses the strict-subset notion to one definition beside `coherent_subset`
and `is_bijection`. The oracle twin stays an independent reimplementation by the
deliberate-twin discipline (it must not import the thing it checks), so it is left
as-is; the finding only addresses the two production copies.

## Finding 4 — the mid-draft relaxed-subset RECOUNT has no behavioural (`.feature`) scenario (severity: low)

**Category:** test-gap

**Location:** `tests/features/reconcile.feature` (scenarios cover the stale
done-claim recount and the partial-init recreate-log, but not the relaxed
drafting-subset cover-gap recount); the new path is covered only at unit
(`tests/test_relaxed_subset_reconcile.py`) and installed-binary e2e
(`tests/test_relaxed_subset_e2e.py`) levels.

**Description:** The other `reconcile` recovery behaviours each have a
black-box BDD scenario in `reconcile.feature` that pins the operator-visible
contract (exit code, the recount recovery log entry, no working file removed).
The 2.3.8 mid-draft RECOUNT — `check` exits 4 reporting a `word-counts-cover-drafts`
recount on a relaxed subset, and `reconcile` carries it out — is exercised by an
e2e test but is absent from the behavioural feature suite, so the operator-facing
contract for the new headline behaviour is not asserted at the same level as its
siblings. This is a coverage-symmetry gap, not a correctness gap (the e2e test
exists).

**Proposed fix:** Add a `Scenario` to `tests/features/reconcile.feature`
asserting that a relaxed drafting subset whose `by_chapter` table omits a drafted
chapter's key is detected by `check` (exit 4, `word-counts-cover-drafts`
reconciliation) and repaired by `reconcile` (exit 0, a recount recovery log entry,
no working file removed), mirroring the existing stale-done-claim scenario. Wire
it through the existing `reconcile` step definitions.

## Finding 5 — the relaxed-subset cover-drafts contract is documented across four prose sites with no single canonical statement (severity: low)

**Category:** docs-gap

**Location:** `novel_ralph_skill/state/_disk_word_counts.py`
`_check_word_counts_cover_drafts` docstring lines 162-171 and
`_drafted_subset_cover_violation` lines 108-137;
`novel_ralph_skill/state/_reconcile_precedence.py` `_drafting_subset_cover_gap`
lines 125-151; `docs/adr-009-drafting-bijection-relaxation.md` "Known risks";
`docs/developers-guide.md` bijection-relaxation section.

**Description:** The "missing direction only, keyed off the on-disk drafted
subset, gated on drafting + coherent subset, repaired by a scoped RECOUNT"
contract is restated, accurately, in four places. The restatements agree today,
but the Decision references (D2, D3, D6, D7, B1, B2) are spread across the
docstrings and the ExecPlan rather than collected in one developer-facing
location, so a reader must assemble the contract from fragments and a future
edit must keep four prose copies in step.

**Proposed fix:** Make the developers' guide bijection-relaxation section the
single canonical statement of the relaxed cover-drafts contract (the missing-only
direction, the convergence argument for why the manifest-keyed `0`-write never
re-fires, and the `check`-relaxed / `reconcile`-strict agreement), and have the
three code docstrings reference it by section name rather than re-deriving the
rationale inline. The docstrings keep their local "what this function does" lead
but defer the cross-cutting "why" to the one guide section.
