# Post-merge audit — roadmap task 2.3.6

Audit of the codebase after task 2.3.6 ("Detect `by_chapter` key-set divergence
from manifest and drafts") merged to `main` at commit `9995523`. The task added
the `word-counts-cover-drafts` §5.4 disk-evidence invariant so disk-aware
`check` catches a `[word_counts].by_chapter` table that omits a drafted manifest
chapter or carries a key the manifest never declared — the key-set coverage
divergence orthogonal to the existing shared-key `word-counts-match-drafts`
value divergence. It split the production word-count twins into
`_disk_word_counts.py` (with shared path helpers in `_disk_paths.py`) and the
divergent-table corpus specs into `_divergent_variants.py` to keep
`disk_evidence.py` and the corpus `_variants.py` under the 400-line cap, routed
both `word-count` divergences through one `RECOUNT` reconciliation, and
documented the invariant across the developers' guide, design §5.4, and the
users' guide.

Trail followed: `docs/novel-ralph-harness-design.md` §§4.1/5.2/5.4,
`docs/developers-guide.md` §"Invariant validation",
`docs/users-guide.md`, `docs/roadmap.md` task 2.3.6,
`docs/execplans/roadmap-2-3-6.md` (Decision Log D-WORDCOUNT, D-NAMES, D-KEY),
`docs/adr-001`, `AGENTS.md` (quality gates, the 400-line cap, CQS), the
`python-router` skill (Python work, routing to data-shapes/iterators), and
`leta`/`sem` for navigation and history. Files inspected:
`novel_ralph_skill/state/_disk_word_counts.py`,
`novel_ralph_skill/state/_disk_paths.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/wordcount.py`,
`novel_ralph_skill/state/__init__.py`,
`tests/test_disk_evidence.py`, `tests/working_corpus/_oracle.py`,
`tests/working_corpus/_oracle_disk.py`,
`tests/working_corpus/_reconcile_variants.py`,
`tests/working_corpus/_divergent_variants.py`.

The merged change is high quality and tightly scoped: the new predicate is a
deliberate twin of a corpus oracle predicate pinned to agree on every corpus
tree, the orthogonality boundary against the value-divergence predicate is
covered by a dedicated silence test (`test_cover_predicate_silent_on_value_only_divergence`),
the bijection deferral that prevents double-firing is reasoned out in both the
production and oracle docstrings, and the design/dev-guide/users-guide prose all
describe the new invariant consistently. The findings below are refinements to
the predicate split this task introduced; none is a defect in the merged
behaviour.

## Finding 1 — the cover predicate recounts every draft only to discard the counts (severity: medium)

**Category:** complexity

**Location:** `novel_ralph_skill/state/_disk_word_counts.py`
`_check_word_counts_cover_drafts` lines 128-136 (the `disk_word_counts(...)`
call at line 131 and the `set(by_chapter)` derivation at lines 133-134).

**Description:** `_check_word_counts_cover_drafts` needs only the *key set* of
the manifest-keyed recount, yet it calls `disk_word_counts(state, working_dir)`,
which opens and `str.split()`-counts every chapter's `draft.md` off disk via
`recount_words`, then throws away every value and keeps only `set(by_chapter)`.
By the contract of `recount_words` (it "keys `by_chapter` by the chapter
manifest, one entry per manifest chapter"; `wordcount.py` lines 11-18, 129-132)
that key set is exactly `{f"{chapter.number:02d}" for chapter in state.chapters}`
— a pure function of the in-memory manifest that needs no disk read at all. The
predicate has already, two lines earlier, computed `manifest = {chapter.number
for chapter in state.chapters}` and confirmed via the bijection guard that the
manifest matches the on-disk directories, so every draft read the recount
performs is redundant work whose result is discarded. In `check_disk_evidence`
both word-count predicates run, so the tree's drafts are read and counted
**twice** per `check` (once for `match`, once for `cover`), and a third time when
`derive_reconciliation` calls `_recount`; the cover read is the one that buys
nothing.

**Proposed fix:** Derive the recount key set directly from the manifest instead
of reading disk: replace the `disk_word_counts(...)` call with `recount_keys = {
f"{chapter.number:02d}" for chapter in state.chapters}` and compare that against
`set(table)`. This keeps the predicate's verdict byte-for-byte identical (the
bijection guard already established the manifest is the authority for the key
set), removes one full draft-tree read from every `check`, and makes the
predicate honestly "key-set only" — matching its own docstring, which frames the
check as a key-set comparison, not a value computation. The twin-equality test
`test_word_counts_cover_twin_equals_corpus_oracle` continues to pin the
production predicate against the oracle, so the simplification is guarded.

## Finding 2 — the manifest/disk bijection guard is open-coded in three predicates (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/disk_evidence.py`
`_check_manifest_disk_bijection` lines 119-122 and
`novel_ralph_skill/state/_disk_word_counts.py`
`_check_word_counts_cover_drafts` lines 128-129; the oracle twins repeat it in
`tests/working_corpus/_oracle_disk.py` `_check_manifest_disk_bijection`
lines 81-85 and `_check_word_counts_cover_drafts` lines 206-208.

**Description:** Whether the manifest is in bijection with the on-disk chapter
directories — `{chapter.number for chapter in state.chapters} ==
_on_disk_chapter_numbers(working_dir)` — is computed independently inside
`_check_manifest_disk_bijection` (which owns the verdict) and inside
`_check_word_counts_cover_drafts` (which *defers* to that verdict). The cover
predicate's correctness depends on agreeing exactly with the bijection
predicate's set-equality clause: the design intent (production docstring lines
118-126; ExecPlan D-KEY) is "fire the cover gap only when the bijection holds, so
the two never double-fire". But the deferral is enforced by a hand-copied
`manifest != _on_disk_chapter_numbers(...)` expression rather than by reusing the
bijection predicate, so a future change to what "bijection" means (for example
the contiguity clause `_check_manifest_disk_bijection` adds at line 121, which
the cover guard does **not** replicate) silently desynchronises the two: the
cover guard tests only set-equality, not contiguity, so a non-contiguous manifest
that is nonetheless set-equal to disk would pass the cover guard while
`manifest-disk-bijection` fires — re-opening the double-fire the deferral exists
to prevent.

**Proposed fix:** Extract the bijection test into one named predicate the cover
guard can consult — e.g. a `_manifest_disk_in_bijection(state, working_dir) ->
bool` in `_disk_paths.py` (beside `_on_disk_chapter_numbers`) that both
`_check_manifest_disk_bijection` and `_check_word_counts_cover_drafts` call — so
the deferral guard is the *same* test the owning invariant uses, contiguity
clause included. The oracle twins should keep their own independent copy (the
deliberate-twin policy forbids importing production into the cross-check), but the
production side should have a single bijection definition. Add a test that a
set-equal-but-non-contiguous manifest does not double-fire `cover` and
`manifest-disk-bijection`, pinning the boundary the extraction protects.

## Finding 3 — `_on_disk_chapter_numbers` twins guard `is_dir()`/`isdigit()` in a different order (severity: low)

**Category:** inconsistency

**Location:** `novel_ralph_skill/state/_disk_paths.py` `_on_disk_chapter_numbers`
lines 31-38 versus `tests/working_corpus/_oracle_disk.py`
`_on_disk_chapter_numbers` lines 65-70.

**Description:** The production and oracle copies of `_on_disk_chapter_numbers`
are deliberate twins (the oracle's docstring at line 63 says "Mirrors production
`_on_disk_chapter_numbers`"), but they apply the two filters in a different
shape. Production does an early `continue` on `not entry.is_dir()` and *then*
tests `suffix.isdigit()`; the oracle computes `suffix` first and tests
`entry.is_dir() and suffix.isdigit()` in one boolean. The two are equivalent for
the inputs the corpus builds, but a deliberate twin pair is supposed to be
trivially diffable so a reviewer can confirm by eye they encode the same rule;
the reordered guards force a reviewer to mentally normalise the control flow
before trusting the equivalence, and there is no twin-equality test for this
helper pair the way there is for the word-count predicates (the helper is
exercised only transitively through the predicates that call it).

**Proposed fix:** Align the two copies to the same guard order — preferably the
production early-`continue` shape, which avoids parsing the suffix of a
non-directory entry — so the twins diff cleanly. This is a readability and
twin-discipline fix only; the behaviour is already identical. No new test is
needed beyond the existing predicate-level agreement suites, though a one-line
comment on each copy cross-referencing the other would make the twin relationship
explicit at the call site.

## Finding 4 — the `len(text.split())` token rule remains open-coded in `_check_done_flag_without_draft` (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/disk_evidence.py`
`_check_done_flag_without_draft` lines 149-152
(`len(draft.read_text(encoding="utf-8").split())`).

**Description:** This is a continuation of audit-2.3.5 Finding 4, unchanged by
task 2.3.6 (which split the word-count twins into `_disk_word_counts.py` but left
`_check_done_flag_without_draft` in `disk_evidence.py`). The module docstring of
`_disk_word_counts.py` (lines 13-17) reasserts the single-counter claim — "The
recount reuses the shared `recount_words`, the one counting rule
(`len(text.split())`), so no second counter exists" — yet the sibling
`disk_evidence.py` predicate still open-codes that very rule to decide whether a
`done.flag` sits beside an empty draft, rather than reusing
`wordcount._chapter_word_count`. The split this task performed makes the claim
more prominent without closing the seam it describes: there are still two
production sites that compute a whitespace-split token count.

**Proposed fix:** As proposed in audit-2.3.5 Finding 4, have
`_check_done_flag_without_draft` reuse `wordcount._chapter_word_count` (or a small
`_drafted_token_count(draft_path)` extracted from it) so the production side has
exactly one whitespace-token counter. Recorded here for continuity so the item
is visible against the module that now most loudly claims single-counter status.

## Finding 5 — the design doc states the deferral but not the contiguity gap behind it (severity: low)

**Category:** docs-gap

**Location:** the deferral rationale lives in
`novel_ralph_skill/state/_disk_word_counts.py` lines 118-126 and
`tests/working_corpus/_oracle_disk.py` lines 194-204; the design doc
`docs/novel-ralph-harness-design.md` §5.4 records *that* `word-counts-cover-drafts`
defers to `manifest-disk-bijection` but not the precise predicate-shape reason
(the recount keys off the untrustworthy manifest) the deferral guards against.

**Description:** The load-bearing subtlety behind the cover predicate is that it
keys its comparison off the manifest, so on a non-bijective tree the manifest is
not trustworthy and the comparison would double-fire on every structural
mismatch; the deferral exists precisely to suppress that. This reasoning is fully
captured in the two predicate docstrings, but the durable design doc — the stated
source of truth — states the conclusion ("the two invariants never double-fire")
without the mechanism. A maintainer revisiting "why does `cover` test bijection
before comparing key sets?" must reconstruct the manifest-as-untrustworthy-key
argument from the code rather than the design. This is closely related to
Finding 2: if the contiguity clause is folded into a shared bijection predicate,
the design doc should state both the deferral and *which* bijection (set-equality
plus contiguity) is being deferred to.

**Proposed fix:** Add one sentence to design §5.4 recording the mechanism:
because the cover predicate keys its recount off the manifest, a non-bijective
manifest is untrustworthy as a key source, so the predicate defers wholly to
`manifest-disk-bijection` (set-equality and contiguity) and fires only once the
manifest and disk agree — leaving the hand-edited-table key-set divergence as the
sole surviving signal. This moves the load-bearing rationale into the durable
doc.
