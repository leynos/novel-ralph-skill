# Logisphere design review — roadmap 6.2.14, round 1

Verdict: **Proceed** (no blocking defects). Adversarial review against real
project source, the ADRs/design doc, the developers' guide, and AGENTS.md.

## What was verified against real source (not the planner's summary)

- ROLLBACK classification: `reconcile.py::_classify_pending_turn`
  (lines 178-194) keys ROLLBACK on any missing declared path whose basename is
  outside
  `_RECOMPUTABLE_BASENAMES` (`{state.toml, log.md}`). `done.flag` qualifies.
  Verified.
- Path resolution: `_reconcile_precedence.py::_missing_declared_paths`
  (lines 64-80) strips the `working/` prefix and checks existence, so
  `working/manuscript/chapter-99/done.flag` resolves under `working_dir` and is
  absent (chapter-99 not in the baseline manifest) → missing → unrecoverable.
  Verified.
- Refuse-class precedence runs *before* the pending-turn arm
  (`derive_reconciliation` lines 308-323), gated on `PENDING_TURN_CLEARED`
  firing (line 320). Verified.
- `_check_done_flag_without_draft` (disk_evidence.py lines 162-190) stats only
  the literal `chapter_dir / "done.flag"` per manifest chapter; a
  `done.flag.partial.tmp` sibling fires nothing. Verified.
- Bijection (`_check_manifest_disk_bijection`, lines 124-159) keys on
  `chapter-NN/` directory presence via `_on_disk_chapter_numbers`; a `.tmp` file
  inside an existing chapter dir adds no on-disk chapter number. Verified.
- Every other disk-evidence detector reviewed (`_check_compiled_matches_drafts`,
  `_check_pending_turn_cleared`, `_check_cursor_plan_present`, the word-count
  detectors, `_check_log_present`): none scans for stray `.tmp` files. The
  residue is invisible to the full detector suite, so the disposition is exactly
  `ROLLBACK_PENDING_TURN`. Verified.
- Producer: `document.py::pending_turn(path, *, operation, paths)` accepts a
  free-form `operation` and `paths`; the never-landed `done.flag` `Examples` row
  of `torn_turn_rollback.feature` already drives `operation="mark-done"`,
  `paths=["working/manuscript/chapter-99/done.flag"]` through it successfully.
  Producer proven.
- Baseline (`tests/working_corpus/_library.py`): three drafted chapters, each
  with a non-empty `draft.md`; chapter-03 (the residue host) carries no
  `done.flag`. Verified — so a literal `done.flag` there would be coherent,
  which is why D-RESIDUE's `.tmp` choice is correct.
- Lint exemption: `pyproject.toml:94` exempts `tests/steps/*.py` from
  S101/PLR0913/PLR0917/PLR2004/PLR6301. Verified.
- Red state: the new binder will star-import a not-yet-existing step module,
  producing a `ModuleNotFoundError` collection error after Work item 1 — a real
  red, per AGENTS.md. Verified against the predecessor binder.
- "No external-library research load-bearing" section: the runner path is fully
  in-process; neither predecessor step module imports any `cuprum` symbol. No
  Cyclopts help/version, pytest-timeout, or uv behaviour is exercised. The
  plan's
  memory-free framing is correct — there is nothing to firecrawl-cite because
  nothing external is on the path. Verified.

## Design-doc / roadmap conformance

- §5.4 item 2 ("Rolling back removes nothing — the partial artefacts stay on
  disk, unreferenced by state") at design lines 566-567, and the
  `done.flag`-beside-empty-draft REFUSE clause at lines 572-ff and 916, both
  verified at the cited locations.
- The devguide misattribution the plan targets in Work item 4 is real: the
  partial-landed bullet (developers-guide.md ~lines 1026-1029) labels the family
  "(task 6.2.13)", but roadmap 6.2.12 is the partial-landed `draft.md` cell and
  6.2.13 is the never-landed `done.flag` cell. The plan's correction (6.2.12 for
  `draft.md`, 6.2.14 for `done.flag`) is accurate.

## Findings (all advisory — none blocking)

- A1 (Doggylump). Work item 3 is conditionally a no-op ("folds into Work item 2
  if no hardening edit is needed"). This is fine, but the plan should make the
  commit-or-fold decision explicit in the Progress log when reached, so the
  audit
  trail is unambiguous about why there may be three commits or four.
- A2 (Telefono). The predecessor `torn_turn_rollback_partial_steps.py` and its
  binder already say "roadmap 6.2.12" in their docstrings, while the devguide
  said 6.2.13 — the inconsistency the plan fixes. Recommend the new artefacts'
  docstrings explicitly note they are the 6.2.14 `done.flag` sibling of the
  6.2.12 `draft.md` proof (the plan already requires this in Work item 2;
  restating here for the record).
- A3 (Buzzy Bee / Wafflecat). D-SINGLEFEATURE adds a fourth near-identical
  feature/step pair. This is the right call now (the roadmap defers
  parametrisation/scaffolding extraction to 7.23), but the duplication debt is
  real and accumulating across 6.2.7/6.2.12/6.2.13/6.2.14. The plan correctly
  declines to pre-extract; flagging only so 7.23 inherits a clear mandate.
- A4 (Pandalump). The `_RESIDUE_BODY` should be a non-empty, distinctive marker
  so the byte-for-byte preservation assertion is meaningful (an empty body would
  still pass but prove less). The plan says "a short residue marker string" —
  acceptable; just ensure it is non-empty.

## Pre-mortem (Doggylump)

The most plausible failure is not a runtime one — the disposition is fully
pinned by source — but a *documentation* regression: Work item 4 corrects one
mislabel while introducing another, or the cross-referenced feature filename
drifts. Mitigation is already in the plan (`make markdownlint`/`make nixie`
gate, explicit filename citation). Second most plausible: the `.tmp` residue is
accidentally written outside an existing chapter dir, creating a stray
`chapter-NN/` and flipping to REFUSE; the Disposition tolerance and the exit-4
ROLLBACK-action assertion catch this loudly. Both are designed in.

## Strongest alternative (Wafflecat)

Add a third `Examples` row to a parametrized `torn_turn_rollback_partial`
outline instead of a new feature. Rejected correctly by D-SINGLEFEATURE: the
existing partial feature is a concrete `Scenario` with `draft.md`-specific
helper phrasing, and parametrizing residue *filename* + *declared operation*
together is exactly the scaffolding consolidation the roadmap parks at 7.23.
The sibling-feature approach matches how 6.2.12/6.2.13 are kept separate. No
credible better alternative for this task in isolation.
