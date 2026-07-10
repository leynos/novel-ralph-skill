# Logisphere Design Review — ExecPlan roadmap-2-2-3 (Round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-3.md`
(implement the validated chapter-manifest mutator `set-chapters`).

Verdict: **Proceed with conditions.** The plan is structurally sound, its
load-bearing claims verified against real source, and its design-boundary
conformance is strong. A small number of advisory fixes and one near-blocking
documentation/gate inaccuracy remain. No structural rework is required.

## What was verified against real source (not the planner's summary)

- **Multi-file mutator precedent (reconcile).**
  `_reconcile.py::_run_reconcile_bracket`
  drives the exact `open_pending_turn` + write → edit → `log.md` append →
  `clear_pending_turn` + write order the plan copies (WI3). The plan's claim
  that the receipt lands *before* the clear, and that the context-manager
  `pending_turn` is unsuitable (it clears on `__exit__` with no receipt hook),
  is correct — `document.py::pending_turn` confirms it.
- **Validate-before-persist seam.** `_state_mutators.py` exposes
  `_load_document_or_state_error`, `_state_view_or_state_error`,
  `_refuse_if_incoherent` exactly as the plan describes; the exit-3 routing of
  structural-incompleteness faults is real and load-bearing.
- **No contiguity/uniqueness predicate in `validate.py` (D4).** Confirmed:
  `validate_state` owns eight §5.2 invariant names; none is manifest
  contiguity/uniqueness. The plan's decision to add a *separate write-time*
  predicate rather than extend `validate_state` is justified and matches the
  `advance-phase` empty-manifest precedent (a §4.1 precondition the §5.2 set
  does not own).
- **Bijection (D2).** `disk_evidence._check_manifest_disk_bijection` requires
  `manifest == on_disk` (exact set equality) **and** contiguity from 1, counting
  `chapter-NN/` directories via `entry.is_dir()`. So an empty-directory
  manifest makes `check` exit 0 and a manifest with no directories exits 4 —
  the plan's D2 directory-creation rationale is correct.
- **Exit-code contract.** `runner.run` maps `CycloptsError → 2`,
  `StateInputError → 3` exactly as claimed.
- **`[chapters]` document shape.** The corpus builder writes `[[chapters]]` as
  `tomlkit.array().multiline(True)` of inline tables; `parse.py::_chapters`
  reads "array of inline tables". The plan's "build a fresh `[[chapters]]`
  array of inline tables and assign `document["chapters"]`" matches the
  parser's accepted shape.
- **cuprum API (S4, WI6).** Verified against the read-only sibling checkout:
  `cuprum/sh.py::make(program, *, catalogue=...)`,
  `SafeCmd.run_sync(*, context, capture=True)`, `ExecutionContext`,
  `cuprum/catalogue.py::ProgramCatalogue(*, projects=[...])`, `ProjectSettings`.
  `grep cuprum novel_ralph_skill/` is empty — set-chapters shells out to
  nothing, so the cuprum-tests-only boundary holds.
- **pytest-timeout / pytest-xdist / slow markers.** `test_recount_e2e.py` uses
  `@pytest.mark.slow` + `@pytest.mark.timeout(180)`; both plugins are locked in
  `pyproject.toml`. The plan mirrors a real, working pattern.
- **cyclopts locked 4.18.0.** Confirmed in `uv.lock`.
- **Downstream behaviour on empty dirs.** `wordcount.recount_words` reads
  `draft.md` and absorbs `FileNotFoundError` as 0; `_compile` treats an absent
  `draft.md` as the empty string. So after `set-chapters` creates empty dirs,
  `recount` returns a non-empty by-chapter map *of zeros* and `novel-compile`
  exits 0 (no longer 3). Neither requires the directory to pre-exist — only
  `check`'s bijection does.

## Findings

### Near-blocking

1. **`make all` does not run `audit`; the plan claims it does.** Makefile:
   `all: build check-fmt lint typecheck test`. `audit` is a *separate* target
   (`make audit` → `pip-audit`), and AGENTS.md "Quality gates" lists auditing
   as a distinct gate that must pass before commit. The plan's "Concrete steps"
   run only `make all` and its prose states `make all` "chains format-check,
   lint, typecheck, test, and audit" — this is false. Fix: correct the gate
   description and add `make audit` (and the docstring/interrogate gate
   AGENTS.md names) to the per-work-item gate sequence, or state explicitly why
   audit is omitted. Low practical risk (no new dependency) but the plan
   misstates the commit gate, which a novice implementer would follow verbatim.

### Advisory

1. **`list[dataclass]` cyclopts parsing is a novel pattern for this codebase and
   is not firecrawl-cited.** No existing command uses `list[<dataclass>]` as a
   cyclopts parameter; the entire input mechanism rests on S1/S2. The planner
   *did* run an in-process probe against locked 4.18.0 (S1 documents the exact
   invocation and output) and the plan pins it with WI1 unit + WI6 installed
   e2e, which meets the "pin with a test" bar. But the cited doc URL
   (`cyclopts.readthedocs.io/en/v4.18.0/user_classes.html`) is referenced from
   memory, not verified. Recommend: firecrawl-confirm the "JSON List Parsing"
   section for 4.18.0 during WI1, or treat the WI1 probe as the canonical pin
   and drop the unverified URL claim. The exit-2-for-missing-field claim (S2)
   is the weakest memory claim; ensure WI6's installed exit-2 proof covers a
   *missing required field* (not only malformed JSON), since the plan asserts
   both route to exit 2.

2. **Registration style diverges from the established pattern.** Every sibling
   uses bare `@app.command` and lets cyclopts kebab-derive the name
   (`set_cursor` → `set-cursor`). WI4 uses `@app.command(name="set-chapters")`.
   Both work; prefer the bare form for consistency, or note the deliberate
   choice. Not a defect.

3. **Success-clause wording on recount risks overclaiming.** Validation step 4
   says recount "returns a non-empty by-chapter map" after `set-chapters`.
   True, but the values are all zero (no drafts yet). The Purpose contrasts
   this with the blocked state's "empty map". Keep the distinction explicit in
   the test assertion (assert the *keys* exist, not non-zero counts) so the e2e
   does not accidentally assert a stronger, false property.

4. **Bijection set-equality edge: pre-existing stray `chapter-NN/` dirs.** D2
   creates dirs for the manifest, but the bijection is `manifest == on_disk`.
   If a stray `chapter-NN/` directory exists on disk that the manifest does not
   name (e.g. a leftover from an aborted run), `check` will exit 4 even after a
   successful `set-chapters`. The plan's non-empty-prior refusal (D3) does not
   cover this — the *manifest* may be empty while *disk* has stray dirs. This
   is an edge but worth a one-line note in WI3/Risks: `set-chapters` creates
   the manifest's dirs but does not prune unexpected ones; reconcile/check
   surface the mismatch. Acceptable to defer, but record it.

## Pre-mortem (Doggylump)

- **Scenario A — torn turn mid-directory-creation.** A crash after the state
  write but before all `chapter-NN/` dirs are created leaves a populated
  manifest with a partial directory set. Bijection fails → `check` exits 4. The
  plan handles this: the `[pending_turn]` intent lands first (operation
  `set-chapters`), directory creation is idempotent (`exist_ok=True`), and a
  subsequent re-run/reconcile completes it. Mitigation present. **However**,
  the plan must confirm that reconcile's `COMPLETE_PENDING_TURN` path knows how
  to *create the chapter directories* for a `set-chapters`-tagged torn turn —
  the existing reconcile only re-derives `[word_counts]` and `log.md`, not
  chapter dirs (`_pending_turn_edit` only touches `word_counts`). If reconcile
  cannot finish a torn `set-chapters`, the recovery story is "re-run
  set-chapters", but D3 *refuses* a non-empty prior manifest — so the torn-turn
  re-run would be refused with exit 3 and the tree stays non-bijective. **This
  is the sharpest open question and should be answered before implementation**
  (see blocking list).

- **Scenario B — agent emits a 35-chapter JSON array via shell.** Buzzy Bee:
  one command, one JSON arg, ~35 inline-table writes plus 35 `mkdir`s. No
  fan-out, no scaling wall. Shell-quoting a large JSON array is the only
  ergonomic risk; the SKILL.md Phase 7 bridge (WI8) should show the exact
  quoting.

## Strongest alternative (Wafflecat)

**Do not create directories in `set-chapters`; let the bijection be satisfied
lazily by the first drafting turn.** Phase 8 step (a) already writes
`chapter-NN/scenes.md`, which creates the directory. The manifest would then be
populated at end of Phase 7, and `check` would exit 4 until drafting of chapter
01 begins — which is *arguably the honest state* (no chapter is materialized
yet).

Trade-off: this alternative makes `set-chapters` a pure state write (simpler,
single-file, no multi-file `[pending_turn]` bracket, no torn-directory recovery
problem — Scenario A evaporates). It *loses* the success-clause property that
`check` exits 0 immediately after `set-chapters`, which the roadmap explicitly
requires ("check … then operate correctly on the real chapter directories").
The plan's Tolerances already flag this as an escalation trigger (D2). Verdict:
the plan's choice is defensible and roadmap-aligned, but the alternative is
*materially simpler* and removes the recovery hazard in Scenario A. Worth a
sentence in the Decision Log explaining why the immediate-bijection requirement
outweighs the simpler single-file design — currently D2 asserts the requirement
without weighing the simpler option it forecloses.

## Conditions to clear before implementation (back to the planner)

1. Resolve Scenario A: specify how a torn `set-chapters` turn is recovered given
   D3 refuses a non-empty-prior re-run. Either (a) reconcile must learn to
   create the manifest's missing chapter dirs for a `set-chapters` pending
   turn, or (b) D3 must allow a re-run when the manifest is present *but the
   dirs are missing* (i.e. the refusal keys off "manifest present AND
   bijective", not "manifest non-empty"), or (c) document that recovery is
   manual `mkdir` + `reconcile`. Pick one and pin it with a test.
2. Correct the `make all` gate description and add `make audit` (and the
   AGENTS.md docstring/interrogate gate) to the per-work-item gate sequence.
3. Ensure WI6's installed exit-2 proof exercises a *missing required field*, not
   only malformed JSON, to pin the S2 split end-to-end.
