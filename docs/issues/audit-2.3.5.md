# Post-merge audit — roadmap task 2.3.5

Audit of the codebase after task 2.3.5 ("Settle authoritative `current`
definition for divergent compiled.md") merged to `main` at commit `a9bf7a1`. The
task pinned `[word_counts].current` to the drafted sum `sum(by_chapter.values())`
as the single authoritative on-disk quantity, retiring the legacy "in
`compiled.md` or the sum of drafts" wording, and aligned `recount` and the
`reconcile` RECOUNT path on that rule. It updated design §4.1/§5.4,
`state-layout.md`, the `WordCounts.current` schema docstring, and added
`tests/test_current_definition.py` covering the divergence and agreement cases.

Trail followed: `docs/novel-ralph-harness-design.md` §§4.1/5.2/5.4,
`docs/developers-guide.md` §"Invariant validation", `docs/roadmap.md` task 2.3.5,
`docs/execplans/roadmap-2-3-5.md` (Decision Log D-CURRENT, D-TOKEN-EQUALITY),
`docs/adr-001`, `AGENTS.md` (quality gates, the 400-line cap, CQS), the
`python-router` skill (Python work, routing to data-shapes/errors), and
`leta`/`sem` for navigation and history. Files inspected:
`novel_ralph_skill/state/schema.py`, `novel_ralph_skill/state/wordcount.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/compile_model.py`,
`novel_ralph_skill/state/validate.py`,
`novel_ralph_skill/commands/_recount.py`,
`novel_ralph_skill/commands/_reconcile.py`,
`novel_ralph_skill/commands/_state_mutators.py`,
`tests/test_current_definition.py`, `tests/test_reconcile_refuse.py`,
`tests/working_corpus/`.

The merged change is high quality and tightly scoped: the new test pins the
drafted-sum `current` as a cross-command regression (recount, reconcile RECOUNT,
and the `check` REFUSE-on-divergent-compiled path), the `by-chapter-sum`
validator already enforces `current == sum(by_chapter)` so the new authoritative
definition is consistent end-to-end, and the design/dev-guide/state-layout prose
all now state one rule. The findings below are refinements to the surrounding
mutator code the task touched and consolidated; none is a defect in the merged
behaviour.

## Finding 1 — the `[word_counts]` write block is open-coded three times (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/commands/_recount.py` lines 145-146;
`novel_ralph_skill/commands/_reconcile.py` lines 139-140 (`_recount_edit`) and
lines 173-174 (`_pending_turn_edit`).

**Description:** The exact two-line pair that rewrites the word-counts table —

```python
document["word_counts"]["current"] = current
document["word_counts"]["by_chapter"] = _inline_by_chapter(by_chapter)
```

appears verbatim at three sites, and at two of them (`_recount_edit`, the
`recount` body) it is immediately followed by the same
`_state_view_or_state_error(document)` + `_refuse_if_incoherent(...)`
validate-before-persist step. Task 2.3.5 is precisely the task that pins these
three writes to one authoritative `current` rule, yet the rule is enacted by
three copies of the write. A future change to the table layout (e.g. a third
`[word_counts]` field, a different `current` derivation, or a change to the
validate-before-persist convention) must be made in three places and is easy to
skew — which is the exact failure mode this task exists to prevent. The
`reconcile` module already imports `_inline_by_chapter` from `_recount` to avoid
duplicating the inline-table builder, so the precedent for sharing across the two
modules is established.

**Proposed fix:** Promote a single private helper — e.g.
`_apply_word_counts(document, current, by_chapter)` in `_recount.py`, re-exported
to `_reconcile.py` exactly as `_inline_by_chapter` already is — that performs the
two assignments, and have all three sites call it. Optionally fold the shared
`_state_view_or_state_error` + `_refuse_if_incoherent(context=...)` tail into a
`_write_word_counts_validated(document, current, by_chapter, *, context)` helper
that the `recount` body and `_recount_edit` both call (the `_pending_turn_edit`
path already constructs its own view, so it can call the inner two-line helper).
This makes the single authoritative `current` rule have a single enactment site.

## Finding 2 — `_recount_edit` and `_pending_turn_edit` are near-identical recount closures (severity: low)

**Category:** similarity

**Location:** `novel_ralph_skill/commands/_reconcile.py` `_recount_edit`
(lines 119-144) and `_pending_turn_edit` (lines 147-180).

**Description:** Both closures end by writing `[word_counts]` from a disk-derived
`(current, by_chapter)` and refusing an incoherent proposed state; they differ
only in where the counts come from. `_recount_edit` takes them pre-computed off
the `Reconciliation` (`recounted_current`/`recounted_by_chapter`, themselves
`disk_word_counts(...)` results carried by `_recount` in `reconcile.py`'s
derivation), while `_pending_turn_edit` recomputes them via `disk_word_counts`
inside the closure. Both ultimately write `disk_word_counts(state, working_dir)`
output, so the two closures encode the same write with two provenance paths for
the same numbers. This compounds Finding 1: collapsing the write block leaves the
two closures differing only in the count source, making the remaining asymmetry
(carried payload vs in-closure recompute) visible and easy to reconcile.

**Proposed fix:** Once Finding 1's `_apply_word_counts`/`_write_word_counts_validated`
helper exists, both closures reduce to "obtain `(current, by_chapter)`, then call
the shared writer". Consider also carrying the RECOUNT payload through the
COMPLETE-pending-turn `Reconciliation` so `_pending_turn_edit` reads the counts
the same way `_recount_edit` does, removing the second `disk_word_counts` call
site and the divergent provenance.

## Finding 3 — function-local import of `disk_word_counts` is inconsistent with module style (severity: low)

**Category:** inconsistency

**Location:** `novel_ralph_skill/commands/_reconcile.py` line 169
(`from novel_ralph_skill.state import disk_word_counts` inside
`_pending_turn_edit._edit`).

**Description:** `_reconcile.py` imports `ReconcileAction`, `Reconciliation`,
`derive_reconciliation`, `clear_pending_turn`, `open_pending_turn`, and
`write_document_atomically` from `novel_ralph_skill.state` at module level
(lines 52-59), but pulls `disk_word_counts` in with a function-local import inside
the COMPLETE-pending-turn edit closure. `disk_word_counts` is already exported
from `novel_ralph_skill.state` (`novel_ralph_skill/state/__init__.py` lines 35,
126) alongside the symbols already imported at the top, so there is no import
cycle to dodge: the local import is a gratuitous inconsistency that hides a real
dependency from the module header and risks tripping a lint (e.g. PLC0415,
import-outside-toplevel) on a future quality-gate tightening.

**Proposed fix:** Move `disk_word_counts` into the existing module-level
`from novel_ralph_skill.state import (...)` block and delete the function-local
import. If the local import was placed to avoid an import cycle, add a one-line
comment saying so; on inspection no cycle exists (the other `state` symbols are
already imported at module scope), so plain promotion is correct.

## Finding 4 — the `len(text.split())` token rule remains open-coded across disk-evidence predicates (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/wordcount.py` line 83
(`_chapter_word_count`); `novel_ralph_skill/state/disk_evidence.py` line 145
(`_check_done_flag_without_draft` inlines
`len(draft.read_text(encoding="utf-8").split())`); the `tests/working_corpus`
oracle and `_live_draft.py` keep their own deliberate twins.

**Description:** Task 2.3.5's central claim is that there is *one* counting
rule — `len(text.split())` — that defines `current` and makes a `compiled.md`
byte divergence the only way the compiled token count can differ from the
drafted sum (D-TOKEN-EQUALITY). Yet inside the production package that rule is
enacted both by `wordcount._chapter_word_count` (the named home, used by
`recount_words`) and open-coded again in
`disk_evidence._check_done_flag_without_draft`, which reads a
chapter `draft.md` and re-derives `len(...split())` rather than reusing the
single-chapter helper. The two are equivalent today, but the whole task rests on
the rule being singular; a second open-coded copy inside the same production
package is the seam where a future drift (e.g. someone normalising whitespace in
one site) would silently break the "compiled divergence is the only divergence"
guarantee. (The audit-2.3.3 Finding 5 flagged the related `chapter-NN` path
open-coding; this is the sibling token-rule spread and is worth tracking with it.)

**Proposed fix:** Have `_check_done_flag_without_draft` reuse
`wordcount._chapter_word_count(chapter_dir.parent.parent, chapter.number)` (or a
small `_drafted_token_count(draft_path)` extracted from it) so the production side
has exactly one whitespace-token counter, matching the module docstring's "no
second counter exists" claim for the word-count predicate. Keep the corpus and
`_live_draft` twins independent (the deliberate-twin policy forbids importing
production into the cross-check).

## Finding 5 — the D-TOKEN-EQUALITY rationale lives only in the ExecPlan and a test docstring (severity: low)

**Category:** docs-gap

**Location:** the rationale appears in `docs/execplans/roadmap-2-3-5.md`
(D-TOKEN-EQUALITY) and `tests/test_current_definition.py` lines 16-20, 96-97, but
not in the durable design doc. `docs/novel-ralph-harness-design.md` §4.1
(lines 288-291) and §5.4 (lines 558-559) state *that* `current` is the drafted
sum and never the compiled token count, but not *why* a compiled token count can
diverge from the drafted sum only through non-whitespace content.

**Description:** The load-bearing fact behind 2.3.5 is that `str.split()` token
counts are invariant under the blank-line separator and any whitespace, so the
*only* tree whose compiled token count can differ from the drafted sum is one
whose `compiled.md` carries non-whitespace content not in the drafts — which is
exactly the `compiled-matches-drafts` REFUSE finding. This is why pinning
`current` to the drafted sum loses no information. That reasoning is captured in
the ExecPlan (a historical record) and the new test's docstring, but the design
doc — the stated source of truth — only asserts the conclusion. A maintainer
revisiting "why isn't `compiled.md` ever a `current` source?" must reconstruct the
token-equality argument from the ExecPlan rather than the design.

**Proposed fix:** Add one sentence to design §4.1 or §5.4 recording the
token-equality rationale: because `current` is a whitespace-split token count, the
separator and trailing whitespace never change it, so a divergence between the
compiled token count and the drafted sum can only arise from non-whitespace
content — which is precisely the `compiled-matches-drafts` finding, not a
`current` source. This moves the load-bearing rationale into the durable doc.
