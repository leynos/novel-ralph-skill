# Post-merge audit — roadmap task 2.3.4

Audit of the codebase after task 2.3.4 ("Cover the partial-init bootstrap in
disk-authoritative reconciliation") merged to `main` at commit `209c3ed`. The
task added a `log-present` disk-evidence invariant (`log.md` absent beside a
present `state.toml` — the torn `init` bootstrap), a `RECREATE_LOG` reconcile
action that recreates the absent receipt without fabricating an agent judgement,
behavioural (BDD) and end-to-end coverage, and matching prose in the developers'
guide, users' guide, and harness design. The disk-reading oracle predicates were
extracted into a `tests/working_corpus/_oracle_disk.py` sibling to stay under the
AGENTS.md 400-line cap.

Trail followed: `docs/novel-ralph-harness-design.md` §§3.4/5.2/5.4,
`docs/developers-guide.md` §"Invariant validation",
`docs/users-guide.md` (`reconcile` behaviour), `docs/roadmap.md` task 2.3.4,
`docs/execplans/roadmap-2-3-4.md` (Decision Log D-SELF, D-LOG, D-COMPLETE,
D-NAMES), `docs/adr-001` (deterministic/judgemental boundary), `AGENTS.md`
(quality gates, the 400-line cap, CQS), the `python-router` skill (routing Python
work, errors-and-logging for the exit-code channels), and `leta`/`sem` for
navigation and history. Files inspected:
`novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/__init__.py`,
`novel_ralph_skill/commands/_reconcile.py`,
`novel_ralph_skill/commands/_recount.py`,
`novel_ralph_skill/commands/_state_mutators.py`,
`novel_ralph_skill/commands/novel_state.py`,
`tests/test_reconcile.py`, `tests/test_reconcile_derivation.py`,
`tests/test_reconcile_e2e.py`, `tests/test_disk_evidence.py`,
`tests/test_novel_state_check_disk.py`, `tests/steps/reconcile_steps.py`,
`tests/working_corpus/`.

The merged change is high quality and tightly scoped. The new `RECREATE_LOG`
path is covered at every level — pure derivation (`test_reconcile_derivation.py`),
detector (`test_disk_evidence.py`), command (`test_reconcile.py`, including an
idempotence test), behaviour (`tests/features/reconcile.feature` plus steps),
end-to-end against the installed console script (`test_reconcile_e2e.py`), and
the production/oracle twin-agreement suite (`test_novel_state_check_disk.py`).
Precedence is property-tested: `log-present` is lowest-precedence and a parametric
corpus test (`test_log_present_never_overrides_higher_precedence`) proves it never
masks a refuse / pending-turn / recount action. The new detector reads disk on
both production and oracle sides, so the cross-check is genuinely disk-vs-disk,
and the `RECREATE_LOG` path correctly skips the D-SELF `[pending_turn]` bracket
(no `state.toml` change, and a crash simply re-derives `RECREATE_LOG`).

The findings below are refinements to the surrounding mutator code the task
touched. Findings 1–3 are carry-overs from `audit-2.3.5.md` that remain unaddressed
and that task 2.3.4 lightly perturbed (it added the `RECREATE_LOG` arm beside the
`RECOUNT`/pending-turn arms without consolidating the shared writes); Finding 4
is specific to a docstring 2.3.4 left stale. None is a defect in the merged
behaviour.

## Finding 1 — stale `build_app` docstring claims `reconcile` "lands in a later task" (severity: medium)

**Category:** docs-gap

**Location:** `novel_ralph_skill/commands/novel_state.py` lines 306-309 (the
`build_app` docstring).

**Description:** The `build_app` docstring lists the exposed subcommands and ends
"the remaining `reconcile` mutator lands in a later task." That is no longer true:
`reconcile` has been registered as a subcommand since task 2.3.2 and is wired in
the same `build_app` body at lines 369-373, with its `RECREATE_LOG` arm extended
by this very task. The module-level docstring (lines 36-37) and the `build_app`
`Returns` section (lines 318-321, which list `reconcile` among the exposed
commands) are both correct, so the body docstring contradicts the function it
documents and the rest of the same module. A reader trusting the docstring would
believe `reconcile` is unimplemented. The `recount` clause in the same sentence
was likewise updated when 2.3.1 landed but the `reconcile` clause was missed.

**Proposed fix:** Replace "the remaining `reconcile` mutator lands in a later
task" with a clause matching the others, e.g. "and the `reconcile` mutator (task
2.3.2, extended for the partial-`init` `RECREATE_LOG` repair by task 2.3.4) lives
in `novel_ralph_skill.commands._reconcile` and is registered here." Then audit the
remaining command docstrings for the same "later task" pattern (a repo grep shows
this is the only surviving instance).

## Finding 2 — the `[word_counts]` write block is open-coded three times (severity: medium, carry-over)

**Category:** duplication

**Location:** `novel_ralph_skill/commands/_recount.py` lines 145-146;
`novel_ralph_skill/commands/_reconcile.py` lines 142-143 (`_recount_edit`) and
lines 176-177 (`_pending_turn_edit`).

**Description:** The exact two-line pair that rewrites the word-counts table —

```python
document["word_counts"]["current"] = current
document["word_counts"]["by_chapter"] = _inline_by_chapter(by_chapter)
```

appears verbatim at three sites across two modules, twice followed by the same
`_state_view_or_state_error(document)` + `_refuse_if_incoherent(...)`
validate-before-persist tail. This was raised as Finding 1 of `audit-2.3.5.md` and
remains open; task 2.3.4 added the `RECREATE_LOG` arm immediately above these
sites without consolidating them. A change to the `[word_counts]` layout, the
`current` derivation, or the validate-before-persist convention must be made in
three places and is easy to skew. The `reconcile` module already imports
`_inline_by_chapter` from `_recount`, so cross-module sharing of a small write
helper is established precedent.

**Proposed fix:** Promote a single private helper in `_recount.py` — e.g.
`_apply_word_counts(document, current, by_chapter)` (the two assignments) and a
`_write_word_counts_validated(document, current, by_chapter, *, context)` that
adds the shared view-derive + refuse tail — re-exported to `_reconcile.py` exactly
as `_inline_by_chapter` already is, and call it from all three sites. This gives
the single authoritative `current` rule a single enactment site.

## Finding 3 — `_recount_edit` and `_pending_turn_edit` are near-identical recount closures (severity: low, carry-over)

**Category:** similarity

**Location:** `novel_ralph_skill/commands/_reconcile.py` `_recount_edit`
(lines 122-147) and `_pending_turn_edit` (lines 150-183).

**Description:** Both closures end by writing `[word_counts]` from a disk-derived
`(current, by_chapter)` and refusing an incoherent proposed state; they differ
only in provenance. `_recount_edit` reads the counts pre-computed off the
`Reconciliation` (`recounted_current`/`recounted_by_chapter`), while
`_pending_turn_edit` recomputes them via `disk_word_counts` inside the closure.
Both ultimately persist `disk_word_counts(state, working_dir)` output, so the two
closures encode the same write with two count-provenance paths. Raised as Finding
2 of `audit-2.3.5.md`; still open.

**Proposed fix:** Once Finding 2's shared writer exists, both closures reduce to
"obtain `(current, by_chapter)`, then call the shared writer". Consider carrying
the RECOUNT payload through the COMPLETE-pending-turn `Reconciliation` so
`_pending_turn_edit` reads the counts the same way `_recount_edit` does, removing
the second `disk_word_counts` call site and the divergent provenance.

## Finding 4 — function-local import of `disk_word_counts` is inconsistent with module style (severity: low, carry-over)

**Category:** inconsistency

**Location:** `novel_ralph_skill/commands/_reconcile.py` line 172
(`from novel_ralph_skill.state import disk_word_counts` inside
`_pending_turn_edit._edit`).

**Description:** `_reconcile.py` imports `ReconcileAction`, `Reconciliation`,
`derive_reconciliation`, `clear_pending_turn`, `open_pending_turn`, and
`write_document_atomically` from `novel_ralph_skill.state` at module level
(lines 55-62), but pulls `disk_word_counts` in with a function-local import inside
the COMPLETE-pending-turn edit closure. `disk_word_counts` is already exported from
`novel_ralph_skill.state` (`novel_ralph_skill/state/__init__.py` lines 36, 128)
alongside the symbols already imported at the top, and the `state` package never
imports `commands`, so there is no import cycle to dodge: the local import is a
gratuitous inconsistency that hides a real dependency from the module header and
risks tripping a future `PLC0415` (import-outside-top-level) gate. Raised as
Finding 3 of `audit-2.3.5.md`; still open.

**Proposed fix:** Move `disk_word_counts` into the existing module-level
`from novel_ralph_skill.state import (...)` block (lines 55-62) and delete the
function-local import. On inspection no cycle exists, so plain promotion is correct.

## Finding 5 — COMPLETE-pending-turn-with-absent-`log.md` interaction is untested (severity: low)

**Category:** test-gap

**Location:** `novel_ralph_skill/commands/_reconcile.py`
`_run_reconcile_bracket` (lines 90-119) and the `COMPLETE_PENDING_TURN` dispatch
(lines 285-292); coverage in `tests/test_reconcile.py` and
`tests/test_reconcile_derivation.py`.

**Description:** Task 2.3.4 establishes `log.md` as a recomputable artefact and
adds `RECREATE_LOG` for the standalone "torn `init`" tree. Independently,
`_classify_pending_turn` already treats a missing `log.md` declared in a torn
turn's `paths` as recomputable (`_RECOMPUTABLE_BASENAMES`), and the D-SELF bracket
recreates `log.md` as a side effect of `_append_recovery_entry` (the append-mode
open creates the file). These two `log.md`-recreating paths now coexist, but no
test exercises a `COMPLETE_PENDING_TURN` tree whose `log.md` is *itself*
absent on disk (the bracket's step-1 `state.toml` write and step-3 receipt-append
both then
run against a tree with no prior `log.md`). The derivation precedence test proves
`log-present` never overrides a pending turn, but does not assert that a
COMPLETE-pending-turn run over a log-absent tree leaves a coherent tree with both
`state.toml` cleared and `log.md` present. The behaviour is almost certainly
correct (the bracket recreates `log.md` regardless), but it is the one
interaction the two new/adjacent `log.md` recovery paths share and it is unpinned.

**Proposed fix:** Add a command-level test: build a torn-turn tree
(`operation`-bearing `[pending_turn]` with only `state.toml`/`log.md` missing),
remove `log.md`, run `reconcile`, and assert exit `0`, the cleared
`[pending_turn]`, a recreated `log.md` carrying the `complete-pending-turn`
receipt, and a follow-up `check` exit `0`. This pins the interaction between the
`RECREATE_LOG` recomputability rule and the pending-turn bracket's receipt write.
