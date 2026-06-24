# Post-merge audit — roadmap task 2.3.2

Audit of the codebase after roadmap task 2.3.2 ("Implement read-only
reconciliation detection and disk-authoritative reconcile") merged to `main` at
commit `cf1ee2d`. The slice lands the §5.4 checker/mutator split: a disk-evidence
detector
([`state/disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py)), the
shared pure derivation
([`state/reconcile.py`](../../novel_ralph_skill/state/reconcile.py)), a
draft-concatenation model
([`state/compile_model.py`](../../novel_ralph_skill/state/compile_model.py)), a
disk-aware `check`
([`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)),
and the project's first genuinely multi-file mutator, `reconcile`
([`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)).

The slice is sound, thoroughly documented, and well covered: a cross-check test
pins that `check` and `reconcile` re-derive an identical `Reconciliation`
(D-SHARED), twin-equality tests pin the detector against the corpus oracle, and
a self-recovery test proves an interrupted `reconcile` leaves a recoverable
`operation="reconcile"` record that repeated runs converge. None of the findings
below is a blocking defect. The dominant theme is *minor structural duplication
and a stale command docstring*: the read/write reconciliation payload `{action,
discrepancies, detail}` is rebuilt by hand in four places, and the registered
`check` command's help text still claims it validates only the §5.2 pure-state
invariants although the slice made it disk-aware.

Trail followed: explored with `leta`/targeted reads over
`commands/_reconcile.py`, `commands/_recount.py`, `commands/_state_mutators.py`,
`commands/novel_state.py`, `state/reconcile.py`, `state/disk_evidence.py`,
`state/compile_model.py`, `state/wordcount.py`, `state/document.py`, and the
2.3.2 test modules (`test_reconcile*.py`, `test_disk_evidence.py`,
`test_novel_state_check_disk.py`); traced the merge with
`git diff --stat c09a946~1 cf1ee2d`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.3/§3.4/§4.1/§5.2/§5.4,
`docs/users-guide.md` (the disk-evidence and `reconcile` sections),
`docs/developers-guide.md` (the multi-file-writer section), the prior
`docs/issues/audit-2.2.2.md` and `audit-2.1.6.md`, and `AGENTS.md`. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity.

## Finding 1 — The registered `check` command docstring still claims "§5.2 pure-state invariants" although `check` is now disk-aware

- Category: docs-gap
- Severity: medium
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  line 315 (the `@app.command def check()` body docstring).

Task 2.3.2 made `check` disk-aware: it now unions the §5.2 pure-state verdict
with the §5.4 disk-evidence verdict and attaches a `reconciliation` payload. The
module docstring (lines 14–28) and the `_check` helper docstring (lines 172–197)
were both updated to say so, but the *registered* subcommand's body docstring at
line 315 still reads `"""Validate the §5.2 pure-state invariants without writing
(design §4.1)."""`. Because Cyclopts surfaces a command's docstring as its
`--help` summary, this is the user-visible description of `novel-state check`,
and it now understates what the command does: it omits the §5.4 disk-evidence
half and the reconciliation report entirely. A user reading `novel-state check
--help` would not learn that `check` compares `state.toml` against the `working/`
tree or that it reports the repair a stale tree implies.

Proposed fix: update the line-315 docstring to match the slice — e.g.
`"""Validate the §5.2 pure-state and §5.4 disk-evidence invariants; report the
implied reconciliation; write nothing (design §4.1)."""`. While there, confirm
the sibling command docstrings (lines 325, 331, 335, 340, 347) remain accurate;
they were spot-checked and read correctly.

## Finding 2 — The reconciliation `{action, discrepancies, detail}` payload is hand-built in four places

- Category: duplication
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  lines 142–150 (`_render_reconciliation`);
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  lines 192–199 (`_write_outcome`), lines 218–223 (`_refuse_outcome`), and lines
  264–268 (the `NONE` branch of `reconcile`).

Four sites independently construct the same dictionary from a `Reconciliation`:
`{"action": str(...), "discrepancies": list(...), "detail": ...}`, three of them
adding the `current`/`by_chapter` pair guarded by `recounted_by_chapter is not
None`. `_render_reconciliation` (the `check` read shape) and `_write_outcome`
(the `reconcile` write shape) are byte-for-byte identical in their body; the
`NONE` branch inlines the same base dict with an empty discrepancy list; and
`_refuse_outcome` repeats the three-key base. The slice is careful to keep the
read shape and the write shape *vocabulary* distinct (audit-2.2.2 Finding 2), but
the *serialisation* of a `Reconciliation` into the base dict is one concern
duplicated across two modules. A future field added to the reported
reconciliation (or a rename of `discrepancies`) is shotgun surgery across four
call sites, and a partial edit would silently let `check` and `reconcile` report
different shapes for the same derivation — the very divergence D-SHARED exists to
prevent.

Proposed fix: give `Reconciliation` (or a small free function beside it in
`state/reconcile.py`) a single `to_payload()` method that returns the base
`{action, discrepancies, detail}` dict plus the optional recount pair, and route
all four sites through it. The read/write *envelope code* and *exit codes* stay
where they are (those genuinely differ); only the `Reconciliation`-to-dict
serialisation is centralised, so `check` and `reconcile` cannot drift on payload
shape.

## Finding 3 — `reconcile`'s own `[pending_turn]` records bare paths, inconsistent with the `working/`-prefixed convention its recovery logic expects

- Category: inconsistency
- Severity: low
- Location:
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  line 71 (`_RECONCILE_PATHS = ("state.toml", "log.md")`);
  [`state/reconcile.py`](../../novel_ralph_skill/state/reconcile.py) lines
  133–149 (`_missing_declared_paths`, which `removeprefix("working/")`).

Every other producer of a `[pending_turn]` record declares
project-root-relative, `working/`-prefixed paths: the corpus reconcile variants
write `["working/state.toml", "working/log.md"]` and
`["working/manuscript/chapter-99/draft.md"]`
([`tests/working_corpus/_reconcile_variants.py`](../../tests/working_corpus/_reconcile_variants.py)
lines 111, 129), and `_missing_declared_paths` is written to that convention —
it strips a leading `working/` before resolving against `working_dir`. But
`reconcile`'s *own* self-bracket declares bare `("state.toml", "log.md")` with no
`working/` prefix. The self-recovery still works today only by coincidence:
`removeprefix("working/")` is a no-op on a bare path, and `state.toml`/`log.md`
sit directly under `working/`, so `working_dir / "state.toml"` resolves
correctly, and `PurePosixPath("state.toml").name` is still a recomputable
basename. The convention is nonetheless violated: a reader comparing
`reconcile`'s declared paths against the corpus producers sees two different
spellings of the same concept, and any future `reconcile` artefact declared
*deeper* than the `working/` root (or a `_missing_declared_paths` change that
stopped tolerating the missing prefix) would break self-recovery silently.

Proposed fix: declare `_RECONCILE_PATHS = ("working/state.toml",
"working/log.md")` so `reconcile`'s self-bracket matches the project-root-relative
convention every other producer and the `_missing_declared_paths` consumer use.
Add a one-line assertion or comment in `_run_reconcile_bracket` documenting that
the declared paths are project-root-relative, and (Finding 6) a test that pins
the self-recovery against the prefixed form.

## Finding 4 — `_pending_turn_edit` imports `disk_word_counts` at call time inside the closure

- Category: ergonomics
- Severity: low
- Location:
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  lines 168–169 (`from novel_ralph_skill.state import disk_word_counts` inside the
  `_edit` closure).

`_pending_turn_edit` performs a function-body `from novel_ralph_skill.state
import disk_word_counts` inside the returned `_edit` closure, where the module
already imports a cluster of names from `novel_ralph_skill.state` at the top
(lines 52–59: `ReconcileAction`, `Reconciliation`, `clear_pending_turn`,
`derive_reconciliation`, `open_pending_turn`, `write_document_atomically`).
Unlike the deliberate circular-import-avoidance late imports elsewhere in the
package (`novel_state.build_app` imports `_state_mutators`, and `_recount`/
`_reconcile` are imported inside the command bodies), there is no import cycle
here: `state/reconcile.py` and `state/disk_evidence.py` do not import the
`commands` package, so `disk_word_counts` is freely importable at module top.
The inline import re-runs the import machinery (cached, but still a lookup) on
every `COMPLETE_PENDING_TURN` that writes `state.toml`, and it hides a real
dependency from anyone reading the module's import block.

Proposed fix: hoist `disk_word_counts` into the existing top-level
`from novel_ralph_skill.state import (...)` block at lines 52–59 and delete the
in-closure import. If the late import was a deliberate guard, document *why* with
a comment (as the genuine circular-import late imports do); otherwise lift it so
the dependency is visible.

## Finding 5 — `_run_reconcile_bracket`'s `edit` callback both mutates the document and refuses incoherent state, blending command and query

- Category: cqs
- Severity: low
- Location:
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  lines 137–144 (`_recount_edit`'s `_edit`) and lines 165–178
  (`_pending_turn_edit`'s `_edit`), driven by `_run_reconcile_bracket` line 113.

The `edit` closures handed to `_run_reconcile_bracket` do two things: they mutate
the live `TOMLDocument` *and* derive a typed view and call
`_refuse_if_incoherent`, which raises `StateInputError` (exit 3) when the proposed
state would breach a §5.2 invariant. The bracket invokes `edit(document)` at line
113 *after* it has already written reconcile's intent record to disk (line 112).
So a refusal raised from inside `edit` happens with the intent record already
persisted — the self-recovery path is designed to tolerate this (a leftover
`operation="reconcile"` record is recoverable), but it means the validate-or-
refuse decision is buried inside a callback named purely for its *mutation* role,
and the refusal's exit-3 side effect is invisible at the `_run_reconcile_bracket`
call site. A reader auditing "where can `reconcile` refuse with exit 3?" must
trace into two closures to find it. The recount and pending-turn validations are
also a near-duplicate three-line `_state_view_or_state_error` →
`document["word_counts"]` rewrite → `_refuse_if_incoherent` shape across the two
closures.

Proposed fix: keep the closures pure mutators (rewrite `[word_counts]` only) and
move the `_refuse_if_incoherent` gate out into `_run_reconcile_bracket` as an
explicit post-edit `validate` step the bracket runs once, after `edit` and before
the receipt. This makes the exit-3 refusal a first-class, single-site step in the
bracket sequence (intent → edit → *validate* → receipt → clear) rather than a
side effect hidden in a callback, and collapses the duplicated
view-rewrite-refuse shape into one place. Alternatively, factor the shared
`document["word_counts"]` rewrite (used by both closures and by `recount`) into
a single helper beside `_inline_by_chapter`.

## Finding 6 — `reconcile`'s self-bracket path convention has no direct test; self-recovery is proven only on the `RECOUNT` action

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_reconcile_integration.py`](../../tests/test_reconcile_integration.py)
  lines 127–182 (`test_interrupted_reconcile_leaves_recoverable_record`);
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py) line
  71 (`_RECONCILE_PATHS`).

The self-recovery test (D-SELF) is valuable but exercises a single action: it
crashes an interrupted `RECOUNT` and asserts repeated `reconcile` runs converge.
It asserts the leftover record's `operation == "reconcile"` but never asserts the
*declared paths* of that record, so the bare-vs-`working/`-prefixed inconsistency
of Finding 3 is invisible to the suite — a regression that changed
`_RECONCILE_PATHS` (in either direction) would not be caught. The two
pending-turn recovery actions (`COMPLETE_PENDING_TURN`, `ROLLBACK_PENDING_TURN`)
are covered by
the derivation and integration suites at the `derive_reconciliation` level, but
the *interrupted-`reconcile`* self-recovery seam is proven only over `RECOUNT`.

Proposed fix: extend `test_interrupted_reconcile_leaves_recoverable_record` (or
add a sibling) to assert the leftover record's `pending_turn.paths` equal the
declared `_RECONCILE_PATHS` (pinning the convention chosen for Finding 3), and add
an interrupted-self-recovery case driven by a `COMPLETE_PENDING_TURN` tree so the
manual bracket is proven recoverable on a torn-turn action, not only on a recount.

## Summary

The 2.3.2 reconciliation slice is correct, keeps `check` read-only and
`reconcile` disk-authoritative, shares one pure derivation so the two cannot
disagree, and is proven recoverable when interrupted. The actionable items are
documentation and minor structure, not defects: the registered `check` command's
help text must catch up with its new disk-awareness (Finding 1, highest value);
the `Reconciliation`-to-payload serialisation should have one home rather than
four (Finding 2); `reconcile`'s self-bracket should declare paths in the same
`working/`-prefixed convention every other producer uses (Finding 3); the
call-time `disk_word_counts` import should be hoisted (Finding 4); the
validate-or-refuse gate should be a visible step in the bracket rather than a
side effect in a mutation callback (Finding 5); and the self-recovery suite should
pin the declared-path convention and cover a torn pending-turn action (Finding 6).
