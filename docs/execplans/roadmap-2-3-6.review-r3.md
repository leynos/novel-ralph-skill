# Logisphere adversarial design review — roadmap 2.3.6, round 3

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.

Verdict: **Proceed** — no blocking defects. The round-1 blockers (B1 vocabulary
test, B2 gate-ratio misanalysis) and the round-3 file-cap breach are all
resolved and verified sound against real source. Four non-blocking advisories
remain (all comment/doc drift, none gate `make all`).

## Verified against real source (not the planner's summary)

- `_oracle.py` is **399 lines** (`wc -l`), one below the AGENTS.md 400 cap.
  Work item 0's extraction is genuinely necessary, not theatre. Verified.
- The word-count twin cluster the move targets occupies `_oracle.py` lines
  256-323 (`_disk_drafts`, `_disk_present_draft_bodies`,
  `_check_compiled_matches_drafts`, `_disk_by_chapter`,
  `_check_word_counts_match_drafts`). Verified.
- **No circular import** in the move. The moved functions depend only on
  `chapter_dir_name` / `concatenate_drafts` (from `._specs`), stdlib, and a
  `State` alias (`dict[str, typ.Any]`). `_oracle_wordcounts` need not import
  from `._oracle`; `_oracle` imports the twins back. Direction is acyclic.
  Verified.
- The private `_disk_*` symbols are not imported by name from `._oracle`
  anywhere external; only `corpus_check`, `WORD_COUNTS_MATCH_DRAFTS`, and
  `CORPUS_INVARIANT_NAMES` cross the package seam (`__init__.py`,
  `_variants.py`, `_live_draft.py`, `corpus_fixtures.py:365` `wc.corpus_check`,
  `test_disk_evidence.py` `wc.corpus_check`). The plan's re-export list is a
  superset of what callers need — harmless. Verified.
- `disk_word_counts` keys `by_chapter` strictly by `state.chapters` (the
  manifest) via `recount_words`. The symmetric difference between recount keys
  and table keys is exactly the coverage signal. Verified.
- `_check_manifest_disk_bijection` compares `state.chapters` against on-disk
  `chapter-NN/` dirs (`_on_disk_chapter_numbers`), never the `by_chapter`
  table. A table-only orphan key does not trip it. Verified.
- `_check_word_counts_match_drafts` (both production and oracle) compares
  **shared** keys only (`shared = set(by_chapter) & set(table)`). The
  symmetric-difference keys are an uncovered gap. Verified.
- Reconcile precedence at `reconcile.py` lines 234-242 is refuse-class →
  pending-turn → recount(`WORD_COUNTS_MATCH_DRAFTS`) → none. Adding
  `WORD_COUNTS_COVER_DRAFTS` to the recount trigger *after* the earlier branches
  preserves precedence. Verified.
- `gate-ratio-consistent` reads the honest `draft_words` total
  (`_oracle.py:_check_gate_ratio_consistent`, `drafted = sum(chapter.draft_words
  …)` — actual line **220**, plan cites 219; trivial drift). A `by_chapter` /
  `current` override cannot flip a gate. Risk #2 and the B2 correction are
  factually right. Verified.
- The vocabulary test `test_owned_disk_evidence_names_equal_corpus_subset`
  (`test_disk_evidence.py` lines 62-87) uses **set algebra**
  (`corpus_names - pure_state`), not a hardcoded count, so it passes with **no**
  edit to `pure_state` once the name is appended to both name tuples. B1's
  correction stands. The sibling assertion in `test_validate_state_corpus.py`
  lines 80-87 is also pure set algebra and passes unedited. Verified.
- `_VARIANT_ACTIONS` (`test_reconcile_derivation.py:47`) is an explicit dict
  parametrized over its own items — a manual enrolment point, silent if a
  variant is omitted (advisory A2 correctly captured). The disk-aware
  `test_disk_evidence_tree_exits_four_with_reconciliation` is parametrized over
  `(name, invariant, action)` tuples (line 74), so the plan's proposed
  `("…", "word-counts-cover-drafts", "recount")` case fits. Verified.
- No `cuprum` / Cyclopts / pytest-timeout / uv behaviour is load-bearing on the
  touched path (pure `state` package + `tests/working_corpus`). No firecrawl
  citation required. Verified.
- Design conformance: the new check is a **§5.4 disk-evidence** invariant, not a
  §5.2 pure-state invariant; §5.4 is its correct home and §5.2's bijection
  invariant stays unchanged in scope. The "sub-threshold only" reconcile
  constraint (design §5.4 scope item 1) is satisfied by construction: the
  recount rewrites `[word_counts]` only and never `[gates]`, and the honest
  `draft_words` total (hence the gate flags) is untouched by a `by_chapter`
  coverage gap. No gate can move during the repair. Verified.

## Advisory (non-blocking) findings

### A1 — Stale "six disk-evidence" comments/docstrings the plan does not name

Adding `word-counts-cover-drafts` makes the disk-evidence family **seven**.
Live (non-execplan) sites that hardcode "six" in prose will become stale:

- `tests/working_corpus/_oracle.py:15` — "The six §5.4 disk-evidence predicates".
- `tests/test_disk_evidence.py:8` and `:65` — "the six owned name constants".
- `tests/test_validate_state_corpus.py:83` — "owns exactly the six deferred
  names" (the *assertion* still passes; the comment goes stale).
- `docs/developers-guide.md:439` — "all six §5.4 disk-evidence invariants
  (manifest-disk-bijection, …, word-counts-match-drafts)" — this enumerates the
  six by name and must become seven, adding the new name. The plan's work item 4
  says "add … to the disk-evidence invariant enumeration", which *should* catch
  this, but the plan does not flag that the **count word** also changes.
- `docs/novel-ralph-harness-design.md` §5.4 enumeration (per the 2.3.3 execplan,
  lines 336-348 describe the disk-evidence invariants) may also count them.

None of these gate `make all` (comments/markdown prose). Treat as a cleanup
checklist for work items 0/2/4. `tests/working_corpus/_live_draft.py:152`'s
"other six owned invariants" refers to **pure-state** owned names and stays
correct — do not touch it.

### A2 — Misleading existing production docstring should be corrected in work item 2

`novel_ralph_skill/state/disk_evidence.py`, in
`_check_word_counts_match_drafts`'s docstring (≈ lines 294-298):

> "A key present in the recount but absent from the table (or the reverse) is a
> manifest-to-disk structural mismatch the `manifest-disk-bijection`
> contradiction owns, so this value-divergence predicate stays silent on it —
> the two invariants do not double-fire on one tree."

This is **factually wrong** and is precisely the gap this task closes:
`manifest-disk-bijection` reads on-disk dirs, never the `by_chapter` table, so
it does **not** own a table key-coverage gap. After this change the owner is
`word-counts-cover-drafts`. Work item 2 must correct this docstring (point the
"reverse / absent key" sentence at the new sibling predicate), or the codebase
ships a comment asserting a false ownership. Not a behavioural blocker, but a
correctness-of-record defect the plan currently omits. (Telefono / Pandalump.)

### A3 — "State alias travels with the twins" is imprecise

Work item 0 says the `State` alias "travels with the twins". `State` is still
used by predicates that **stay** in `_oracle.py` (`_check_by_chapter_sum`,
`_check_manifest_disk_bijection`, `_check_done_flag_without_draft`) and by
`corpus_check` itself (line 389). The alias must therefore be **defined in both
modules** (or re-exported), not moved. The correct mechanic — each module
defines its own `type State = dict[str, typ.Any]` — is trivial and acyclic;
just don't let "travels with" be read as "moves out of `_oracle.py`". (Pandalump.)

### A4 — Line-citation drift

The plan cites `_oracle.py:_check_gate_ratio_consistent` "line 219"; the
`drafted = sum(...)` line is actually **220**, and the reconcile recount branch
is at **241-242** (plan says 241-242 — correct). Harmless, but if the
implementer greps by line number it will mismatch; cite by symbol name.

## Pre-mortem (Doggylump)

Six months out, the most plausible incident is **silent staleness**, not a
runtime failure: a future reader trusts the un-corrected
`_check_word_counts_match_drafts` docstring (A2) and the "six disk-evidence"
prose (A1), and either re-derives a wrong ownership map or adds a redundant
check. Blast radius: documentation/onboarding, not production. Signal missed:
the comment drift is invisible to `make all`. Prevention designed-in: fold A1
and A2 into work items 2 and 4 as explicit edits rather than leaving them to the
implementer's discretion. The second-most-plausible failure — a double-fire
receipt — is already neutralized by the single-invariant isolation self-test and
the `DISK_EVIDENCE_INVARIANT_NAMES`-ordered `recount_names` filter (advisory A4
from round 1, folded in).

## Alternatives checkpoint (Wafflecat)

Unchanged from round 1: the only credible alternative — folding coverage into
`word-counts-match-drafts` — trades away the one-invariant-per-variant isolation
the roadmap and twin discipline demand, and mutates an existing predicate's
contract. The two-predicate decomposition remains the right call. No reason to
prefer the alternative.

## Bottom line

The plan is implementable and design-conformant as written. The four advisories
are comment/doc-record hygiene (A1, A2) and citation precision (A3, A4); none
block implementation or violate the deterministic/judgemental boundary or any
established contract. Folding A1 and A2 into the relevant work items before
implementation is recommended so the merged tree carries no stale ownership
claims, but their omission would not produce a broken or non-conformant build.
