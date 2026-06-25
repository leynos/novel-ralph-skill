# Logisphere design review — roadmap 2.2.3, round 3

Verdict: **Proceed.** The three round-2 blocking points (B1 precedence, B2
write ordering, B3 recomputable-set amendment) are resolved, and every
load-bearing claim the resolution rests on is verified against real source in
this worktree (and the read-only cuprum sibling). The plan is implementable and
design-conformant as written. Residual findings are advisory only.

## What was re-verified against real source (not the planner's summary)

- **Reconcile precedence (S5 corrected; the B1 fix is genuinely necessary).**
  `state/reconcile.py::derive_reconciliation` lines 256-265 evaluate
  `refuse = [name for name in fired if name in _REFUSE_CLASS]` then
  `if refuse: return _refuse(refuse)`
  **before** the
  `state.pending_turn is not None and PENDING_TURN_CLEARED in fired` branch.
  `_REFUSE_CLASS` (lines 78-83) contains `MANIFEST_DISK_BIJECTION`. So a
  partial-directory torn `set-chapters` turn REFUSEs before
  `_classify_pending_turn` runs. The round-2 B1 finding and the plan's S5
  correction are both correct; WI3a's guarded-branch-ahead-of-refuse is the
  honest fix, not a classifier tweak.
- **D10 single-write seam.** `state/document.py::open_pending_turn` (lines
  179-204) only sets `document[_PENDING_TURN_KEY] = record`; it does not touch
  `[chapters]`. So one `write_document_atomically` carries both the in-memory
  `[chapters]` edit and the `[pending_turn]` record, exactly as D10/WI3 step
  6-7 claim. The B2 ordering fix is mechanically sound on the real seam.
- **Bijection check.** `disk_evidence.py::_check_manifest_disk_bijection`
  (lines 112-133): fires unless `manifest == on_disk and contiguous`, no
  pending-turn exemption — matching the plan's D2/D9 rationale and confirming
  the manifest-only alternative would leave `check` at exit 4 the instant the
  command returns.
- **`_pending_turn_edit` needs the mkdir branch (WI3a extension point is
  real).**
  `commands/_reconcile.py::_pending_turn_edit` (lines 150-183) only re-derives
  `[word_counts]` when `state.toml` is a missing declared path; the
  COMPLETE/ROLLBACK dispatch (lines 288-292) funnels both through it. For a
  `set-chapters` COMPLETE, `state.toml` is present (not missing), so
  `writes_state` is False and no word-count re-derive runs — the branch must add
  `mkdir`, exactly as WI3a specifies. The `Reconciliation` dataclass already
  carries `operation` and `missing_paths` (lines 130-145), so no shape change
  is needed.
- **§5.4 recomputable enumeration is `state.toml`/`log.md` (B3 is a genuine
  amendment).** Design §5.4 bullet 2 enumerates the recomputable torn-turn
  artefacts as exactly `state.toml`/`log.md`. Adding `chapter-NN/` is a real
  design-invariant change; WI8 records it in ADR 008 and amends §5.4 (both the
  enumeration and the precedence statement), as B3 requires.
- **Validate-before-persist does not spuriously fire.** `validate_state`'s eight
  §5.2 invariants (`PURE_STATE_INVARIANT_NAMES`) include `by-chapter-sum`
  (`sum(by_chapter) == current`) but none ties `[chapters]` membership to
  `[word_counts]` coverage. Populating `[chapters]` over an init'd tree's empty
  `[word_counts]` (`{}`/0) keeps `sum({}) == 0` true, so WI3 step 5's
  defence-in-depth `_refuse_if_incoherent` pass is green on a freshly populated
  manifest. The manifest-disk bijection is §5.4, not §5.2, so it is correctly
  absent from the write-time pure-state pass (the directories do not yet exist
  at step 5).
- **Predicate scope holds in the realistic torn state.** With manifest `{1,2,3}`
  and on-disk `{1}`, the only refuse-class invariant that fires is
  `manifest-disk-bijection`: `done-flag-without-draft` skips missing dirs (no
  `done.flag`), `compiled-matches-drafts` is ABSENT-polarity,
  `cursor-plan-present` is guarded by `0 < current_chapter`.
  `pending-turn-cleared` fires but is not refuse-class. So WI3a's "fired
  refuse-class is exactly `{manifest-disk-bijection}`" predicate is satisfiable
  in the case it must cover. Verified against `disk_evidence.py` predicate
  bodies.
- **Gate description.** Makefile `all: build check-fmt lint typecheck test`
  (no audit); `lint-python` runs `ruff check`, `interrogate`, then Pylint;
  `audit`, `markdownlint`, `nixie` are separate targets. The plan's
  per-work-item `make all` then `make audit` sequence and the WI8 markdown
  gates are accurate (round-1 finding 1 closed).
- **cuprum API, ADR numbering, SKILL Phase 7, compile exit-3.** cuprum
  `sh.make`, `ProgramCatalogue`, `ProjectSettings`, `ExecutionContext`,
  `run_sync` confirmed in the read-only sibling. ADRs 001-007 exist; 008 is
  free. SKILL.md Phase 7 "Chapter planning" with an Exit step exists.
  `_compile.py` refuses an empty manifest with exit 3. All as claimed.

## Crew lenses (residual)

- **Pandalump (structure):** WI ordering 3 → 3a → 5 is correct (3a needs the
  `set-chapters` pending-turn shape; 5's recovery scenario needs 3a). Module
  boundaries respected; the pure validator is separable from the I/O body.
- **Telefono (contracts):** exit-0/2/3 split and the `reconcile` precedence
  change are documented (ADR 008, §5.4, docstrings). No public signature change.
- **Buzzy Bee (scaling):** a 35-chapter array is one command, ~35 inline-table
  writes plus 35 idempotent `mkdir`s; shell-quoting is addressed in the WI8
  SKILL.md bridge.
- **Doggylump (pre-mortem):** the partial-directory 03:00 crash (round-2 A2) is
  now the *decisive* test in WI3a and WI5, with three negative "still-REFUSE"
  tests guarding over-broad recovery. D10 guarantees the manifest is on disk
  before any crash-able artefact. The recovery is a single sanctioned command
  (`reconcile`). Well covered.
- **Wafflecat (alternatives):** the manifest-only alternative (round-2 A1) is
  explicitly rejected in D9 on roadmap-mandate (lines 715-719) plus
  firm-bijection (§5.1/§5.2) grounds — both verified.
- **Dinolump (viability):** the precedence change is scoped and ADR-recorded;
  the
  escalation trigger in Tolerances is narrowed to shape/signature changes.

## Advisory (non-blocking; do not block on these)

1. **Wrong test filename in WI3a and WI5.** The plan says "mirror
   `tests/test_reconcile_unit.py`". No such file exists; the reconcile unit
   surface is `tests/test_reconcile.py` (plus `test_reconcile_derivation.py`,
   `test_reconcile_refuse.py`, `test_reconcile_integration.py`,
   `test_reconcile_scaffold.py`). The implementer should mirror the actual
   files; the intent is unambiguous.
2. **Named-constant sweep confirmed empty.** WI3a says "sweep for an existing
   operation constant first." Confirmed: there is no `set-chapters` operation
   constant in `novel_ralph_skill/`; the only sibling is the module-local
   `_RECONCILE_OPERATION = "reconcile"` in `commands/_reconcile.py`. The
   implementer will introduce a new named constant (e.g. in `_set_chapters.py`)
   and import it where `reconcile.py` needs to compare `operation`; ensure the
   two sides key on one literal (cross-module), mirroring how the
   `[pending_turn]` key is single-homed in `document.py`. Worth a one-line note
   so the constant is not duplicated as a string literal across
   `_set_chapters.py` and `reconcile.py`.
3. **WI3a helper placement.** The plan's fallback (place
   `_set_chapters_turn_explains_bijection` in `state/_disk_paths.py` if
   `reconcile.py` would exceed 400 lines) is sound, but note `_disk_paths.py`
   is docstring-scoped to "path helpers". A predicate that reads
   `state.pending_turn` and `fired` is not a path helper; prefer a small new
   `state/_reconcile_predicates.py` (or keep it in `reconcile.py` if it fits)
   over stretching `_disk_paths.py`'s stated remit. Minor.
4. **Registration style (carried from round 1).** WI4 uses
   `@app.command(name="set-chapters")`; every sibling lets cyclopts
   kebab-derive the name. Both work; the plan already records this as a
   deliberate choice. No action required.

## Trail

Source verified in the worktree: `state/reconcile.py`, `state/disk_evidence.py`,
`state/document.py`, `state/_disk_paths.py`, `state/validate.py`,
`state/schema.py`, `commands/_reconcile.py`, `commands/_state_mutators.py`,
`commands/_compile.py`; `docs/roadmap.md` task 2.2.3 (lines 702-727);
`docs/novel-ralph-harness-design.md` §5.1/§5.2/§5.4; `Makefile`;
`skill/novel-ralph/SKILL.md` Phase 7; ADR directory listing. Read-only sibling:
`/data/leynos/Projects/cuprum` (`cuprum/sh.py`, `cuprum/catalogue.py`). Prior
reviews: round-1 (`*.review-r1.md`), round-2 (`*.review-round2.md`). Skill:
logisphere-design-review.
