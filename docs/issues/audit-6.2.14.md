# Post-merge audit — roadmap task 6.2.14

Audit of the codebase after roadmap task 6.2.14 ("Add a command-boundary
partial-landed ROLLBACK scenario for an unrecoverable `done.flag`") merged to
`main` at commit `9973644`.

The merged change is docs-and-tests only: it adds a BDD feature, a step module,
and a binder for the partial-landed `done.flag` ROLLBACK scenario, plus a
developers'-guide refresh. No production code changed; the behaviour it exercises
(`_classify_pending_turn` treating a missing `done.flag` as an unrecoverable
ROLLBACK trigger) was already in `novel_ralph_skill/state/reconcile.py`.

The work is high quality: the scenario is driven through the real command
boundary, the residue-placement reasoning (a non-`done.flag` `.tmp` sibling inside
an existing manifest chapter directory keeps both the `manifest-disk-bijection`
and `done-flag-without-draft` refuse-class detectors quiet so the disposition
stays ROLLBACK rather than REFUSE) is sound and matches the production detectors,
and the developers'-guide edit also corrects a prior mis-attribution (the
`draft.md` partial scenario was labelled task 6.2.13 but is task 6.2.12).

Findings below are minor; the dominant one is a deferral-tracking gap rather than
a defect.

## Finding 1 — New step module extends the deferred reconcile-family duplication beyond what step 7.23.3 enumerates

- **Category**: duplication
- **Severity**: low
- **Location**: `tests/steps/torn_turn_rollback_partial_done_flag_steps.py`
  (lines 108-171, 233-401) versus
  `tests/steps/torn_turn_rollback_partial_steps.py`; deferral recorded at
  `docs/roadmap.md` lines 3945-3975 (task 7.23.3).

The new step module is near byte-identical to its 6.2.12 sibling
`torn_turn_rollback_partial_steps.py`. The entire helper scaffold — `_TornError`,
the `_Outcome` dataclass, `_draft_bytes`, `_present_files`, `_run`,
`_run_capturing` — and all eight `given`/`when`/`then` bodies differ only in the
declared operation (`mark-done` versus `write-draft`), the declared path, the
residue path, and prose. A diff of lines 107-401 between the two files shows the
divergence is confined to those literals and docstrings.

The module docstring acknowledges this explicitly (Decision D-DUP) and defers the
fold-out to roadmap step 7.23.3 ("Consolidate the reconcile-family command-driving
scaffolding into one single registered plugin"). That deferral is legitimate.

The gap is that **task 7.23.3's own success clause does not name this new file**.
The roadmap text (lines 3952-3954, 3969-3975) enumerates the modules to collapse
and stops at the 6.2.12 sibling
(`torn_turn_rollback_steps.py`, `torn_turn_rollback_partial_steps.py`), calling
out a "four-way copy of `_run_capturing`". After 6.2.14 there is now a
**fifth** copy of `_run_capturing` (and of `_run`, `_draft_bytes`,
`_present_files`, `_Outcome`, `_TornError`), but 7.23.3 will not retire it unless
its enumeration is updated. Left as-is, the consolidation step risks leaving one
copy behind.

- **Proposed fix**: Update task 7.23.3 in `docs/roadmap.md` to add
  `tests/steps/torn_turn_rollback_partial_done_flag_steps.py` to both the
  duplication inventory ("now a five-way copy of `_run_capturing`") and the
  Success clause's list of modules that must delegate to the shared plugin. This
  is a roadmap edit reserved to the root agent and is proposed as a roadmap item
  below, not applied here.

## Finding 2 — Asymmetric feature-file naming between the two partial-residue siblings

- **Category**: inconsistency
- **Severity**: low
- **Location**: `tests/features/torn_turn_rollback_partial.feature` versus
  `tests/features/torn_turn_rollback_partial_done_flag.feature` (and the matching
  step/binder basenames).

The two partial-residue ROLLBACK scenarios now form a pair: a `draft.md` variant
and a `done.flag` variant. The `done.flag` sibling carries a `_done_flag`
discriminator in its filename, but the `draft.md` sibling retains the generic
`torn_turn_rollback_partial` name from when it was the only partial scenario. A
reader scanning `tests/features/` cannot tell from the filename that
`torn_turn_rollback_partial.feature` is specifically the `draft.md` cell; the name
reads as the parent of both.

- **Proposed fix**: When task 7.23.3 (or a dedicated rename) touches these files,
  rename the 6.2.12 trio to a `..._partial_draft` basename so the two siblings are
  named symmetrically (`..._partial_draft` / `..._partial_done_flag`). Defer to
  that step rather than renaming now, since a standalone rename would churn the
  binder, the developers'-guide cross-reference (line 1030), and the roadmap
  references for no behavioural gain; flag it here so the rename is bundled into
  the consolidation rather than forgotten.

## Items confirmed sound (no action)

- The ROLLBACK-not-REFUSE premise is correct against production:
  `novel_ralph_skill/state/disk_evidence.py:162-186`
  (`_check_done_flag_without_draft`) stats only the literal
  `chapter_dir / "done.flag"` for each *manifest* chapter, and
  `novel_ralph_skill/state/_disk_paths.py:170` (`_on_disk_chapter_numbers`) keys
  the bijection on `chapter-NN/` directory presence only. A `.tmp` residue inside
  an existing chapter directory, for a chapter the manifest never declares, is
  invisible to both — so the scenario genuinely lands on the ROLLBACK arm of
  `_classify_pending_turn` rather than a misconstructed REFUSE.
- The developers'-guide refresh
  (`docs/developers-guide.md`, "partial-landed ROLLBACK" bullet) is accurate and
  corrects the prior task-number mis-attribution.
- The scenario is driven through `novel_ralph_skill.contract.runner.run` (the
  operator entry path), not the `pending_turn` bracket primitive, matching the
  command-boundary requirement the roadmap clause states.
- No central feature registry or coverage manifest needs updating; binders are
  per-feature and the new binder
  (`tests/test_torn_turn_rollback_partial_done_flag_bdd.py`) is present and wired.
