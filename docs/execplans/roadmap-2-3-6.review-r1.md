# Logisphere adversarial design review — roadmap 2.3.6, round 1

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Verdict: **Proceed with conditions** — the core mechanic is verified sound
against real source, but two plan-as-written defects must be fixed before
implementation.

## What was verified against real source (not the planner's summary)

- The recount keys `by_chapter` strictly by the **manifest**
  (`novel_ralph_skill/state/wordcount.py:recount_words`), so the symmetric
  difference between the recount key set and the table key set is exactly the
  coverage signal the plan targets. Verified.
- `_check_word_counts_match_drafts` compares **shared** keys only
  (`disk_evidence.py` line ~300: `shared = set(by_chapter) & set(table)`), so
  the omit/extra variants leave it silent. Verified.
- `manifest-disk-bijection` reads on-disk `chapter-NN/` dirs vs the manifest,
  never the `by_chapter` table (`disk_evidence.py:_check_manifest_disk_bijection`),
  so a table-only orphan key does not trip it. Verified.
- The reconcile mutator replaces `[word_counts].by_chapter` with a **fresh**
  inline table (`commands/_recount.py:_inline_by_chapter` →
  `commands/_reconcile.py:140`), so a RECOUNT drops an orphan key and supplies a
  missing key by re-keying off the manifest. The plan's "repaired by RECOUNT"
  claim is verified.
- The pure-state validator imposes no manifest/`by_chapter` key bijection; the
  schema parse (`parse.py`) does not reject a `by_chapter` key absent from the
  manifest. Both variants are buildable and parseable. Verified.
- Exit 4 is automatic for any disk-evidence violation
  (`commands/novel_state.py`), and all referenced test modules/functions exist
  (`test_disk_evidence.py`, `test_reconcile_derivation.py::_VARIANT_ACTIONS`,
  `test_novel_state_check_disk.py`, e2e/bdd). Verified.
- No `cuprum` import on the touched path; no Cyclopts / pytest-timeout / uv
  behaviour is load-bearing. The plan correctly scopes external-library
  behaviour out; no firecrawl citation is required. Verified.

## Blocking defects (return to planner)

### B1 — The vocabulary-test instruction will mislead the implementer into breaking a test

Work item 2 says: "extend the pure-state complement set in
`test_owned_disk_evidence_names_equal_corpus_subset` so the disk-evidence subset
still equals the oracle's complement (the new name lands on the disk-evidence
side)."

`test_owned_disk_evidence_names_equal_corpus_subset`
(`tests/test_disk_evidence.py` lines 62-87) computes
`expected = set(corpus_invariant_names) - pure_state`, where `pure_state` is a
hardcoded eight-name set. `word-counts-cover-drafts` is a **disk-evidence** name,
so it must **not** be added to `pure_state`. Once the name is appended to both
`CORPUS_INVARIANT_NAMES` and `DISK_EVIDENCE_INVARIANT_NAMES`, this test passes
with **no edit**. The plan's instruction to "extend the pure-state complement
set" reads as an instruction to add the new name to `pure_state`, which would
make `expected` exclude it and **fail** the assertion. Reword to: "no edit to
the `pure_state` set; confirm the test passes automatically because the new name
lands on the disk-evidence side." (Telefono / Pandalump.)

### B2 — Risk #2's gate-ratio failure mechanism is factually wrong, and the stated mitigation is therefore unverifiable as written

Risk #2 claims that omitting a chapter's count from `by_chapter` "makes the
omitted chapter's contribution vanish from `current`, dropping the ratio enough
to flip a knitting gate and tripping `gate-ratio-consistent`," and mitigates by
keeping the table total in-band.

Both the oracle and the validator compute the gate ratio from the **honest draft
total** (`sum(chapter.draft_words)`), never from `by_chapter`, `current`, or the
table sum: oracle `_check_gate_ratio_consistent` line 219
(`drafted = sum(chapter.draft_words for chapter in spec.chapters)`), validator
identically. Omitting a `by_chapter` key (or pinning `current`) does **not**
change the gate-ratio input, so `gate-ratio-consistent` cannot flip on either
variant for that reason. The stated risk mechanism is impossible and the
"keep the table total in the same gate band" mitigation guards against nothing.

This matters because the plan instructs the implementer to engineer variant
draft-word totals around a non-existent constraint (Work item 1 bullet 1:
"the omitted chapter chosen so the table total stays within the same gate
band"). Correct the analysis: the gate predicate reads `draft_words`, which the
omit/extra variants leave untouched, so `gate-ratio-consistent` is silent by
construction. The real constraint the variants must satisfy is `by-chapter-sum`
(pin `current_words_override = sum(by_chapter_override)`), which the plan does
also state. Remove or rewrite Risk #2 and the corresponding Work-item-1
in-band-selection instruction so the implementer does not waste cycles tuning
draft totals against a phantom constraint. (Buzzy Bee / Doggylump.)

## Advisory (non-blocking) findings

### A1 — Confirm the omit variant's omitted chapter is non-empty *and* document why `done.flag` does not interfere

The baseline's chapter 1 carries `done.flag` over a non-empty 24000-word draft.
The omit variant must omit a **drafted** chapter (so the recount key exists and
the cover predicate fires). `done-flag-without-draft` reads disk drafts, not the
table, so omitting a table key does not perturb it — but the plan should state
this explicitly so the implementer does not accidentally choose an
empty/absent-draft chapter (which would make the recount value `0`, still a key,
still a valid cover divergence, but muddies the worked example in Purpose).
(Pandalump.)

### A2 — `_VARIANT_ACTIONS` is exhaustive; name that contract

`tests/test_reconcile_derivation.py::_VARIANT_ACTIONS` is an explicit
variant→action map parametrized over its own items. It is **not** auto-derived
from `INCOHERENT_VARIANTS`, so a new variant that is not added here is simply not
exercised (silent gap) rather than a hard failure. Work item 3 does add both
variants, but should note that this map is the manual enrolment point and that
omission is silent, so the implementer treats it as mandatory. (Doggylump.)

### A3 — Twin-equality must explicitly include the value-only divergence variants in the silent set

Work item 2 says the new predicate "must stay silent on the *value*-only
divergences." Confirm the twin-equality / agreement assertions actually include
`done-flag-real-draft-undercount`, `done-claim-stale-word-counts`, and the two
`DIVERGENT_TABLE_VARIANTS` so a regression where the cover predicate fires on a
shared-key value gap is caught. The whole-corpus agreement loop covers
`INCOHERENT_VARIANTS` automatically, but `DIVERGENT_TABLE_VARIANTS` are **not**
`INCOHERENT_VARIANTS` members (see `_variants.py` docstring), so verify they are
in whichever coherent/agreement loop the new predicate is asserted silent over.
(Telefono.)

### A4 — Pre-mortem scenario

Six months out, the most likely incident is a **double-fire** regression: a
future variant or a refactor causes `word-counts-cover-drafts` and
`word-counts-match-drafts` to both fire on one tree, and reconcile's
discrepancy list carries two names where downstream log-receipt parsing expects
one. Mitigation already latent in the design: the single-invariant isolation
self-test forbids double-fire per variant; ensure the new variants are added to
it (they are, Work item 1) and that the `discrepancies` assembly in
`derive_reconciliation` is verified to carry **all** fired recount-trigger names
deterministically (the plan's `recount_names` list comprehension does this —
confirm the existing single-name receipt format tolerates a list, or keep the
list ordered by `DISK_EVIDENCE_INVARIANT_NAMES`). (Doggylump / Buzzy Bee.)

## Alternatives checkpoint (Wafflecat)

The strongest alternative is to **fold coverage into the existing
`word-counts-match-drafts` predicate** (compare full key sets and values in one
check) rather than adding a sibling invariant. It trades away orthogonality and
the clean single-invariant isolation property — a corpus variant could no longer
pin "coverage only" vs "value only" — and it would change the existing
predicate's contract and its REFUSE/RECOUNT mapping surface. The proposed
two-predicate design is the better choice precisely because the roadmap and the
existing twin/isolation discipline demand one-invariant-per-variant; fold-in
would break that. No credible reason to prefer the alternative; the proposed
decomposition is on solid ground.

## Scaling / long-term (Buzzy Bee / Dinolump)

Pure set comparison over a manifest-sized key set; trivially cheap. The design
matches the established twin/isolation pattern the team already operates, so
long-term maintenance cost is the marginal cost of one more twinned predicate —
acceptable and consistent. No new dependency, no interface shape change.

## Bottom line

Fix B1 (the vocabulary-test instruction) and B2 (the gate-ratio risk
misanalysis and the dependent variant-selection instruction). With those two
corrections the plan is implementable and design-conformant. The advisories
strengthen the test net but do not block.
