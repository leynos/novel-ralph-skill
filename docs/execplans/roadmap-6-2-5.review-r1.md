# Logisphere design review — roadmap 6.2.5, round 1

Adversarial pre-implementation review of
`docs/execplans/roadmap-6-2-5.md`. Verdict: **Proceed with conditions**. The
mechanism is sound and verified against real source; one factual coverage claim
in the Constraints block is false and must be corrected, and two small
clarifications are advisable.

## Trail (docs and source relied on)

- `logisphere-design-review` skill (full crew + pre-mortem + alternatives).
- `docs/roadmap.md:1342-1354` (task 6.2.5 statement and success clause).
- `docs/novel-ralph-harness-design.md` §3.4 (lines 250-263, the
  `[pending_turn]` bracket) and §5.4 (lines 547-607, COMPLETE/ROLLBACK).
- Source verified: `novel_ralph_skill/commands/_reconcile.py`
  (`_append_recovery_entry`, `_run_reconcile_bracket`, `reconcile`),
  `novel_ralph_skill/commands/novel_state.py` (`_check`,
  `_render_reconciliation`), `novel_ralph_skill/state/reconcile.py`
  (`derive_reconciliation`, `_classify_pending_turn`, precedence),
  `novel_ralph_skill/contract/runner.py` (`run` exception handling).
- Tests verified: `tests/steps/reconcile_steps.py`,
  `tests/test_reconcile_integration.py`, `tests/test_reconcile_e2e.py`,
  `tests/test_novel_state_check_disk.py`, `tests/test_torn_turn_bdd.py`,
  `tests/steps/torn_turn_steps.py`, `tests/test_reconcile_bdd.py`.
- Corpus verified: `tests/working_corpus/_reconcile_variants.py`
  (`done_claim_stale_word_counts`), `tests/working_corpus/_variants.py`.
- `pyproject.toml` (`tests/steps/*` Ruff exemption, `timeout=30`, `-n` xdist),
  `Makefile` (`all`, `test`, `markdownlint`, `nixie`).

## What was verified true

- Crash seam, bracket order, and the `_run` command-driver idiom match real
  source exactly. `run` (`runner.py:223-239`) catches only `CycloptsError` and
  `StateInputError`; an injected `_CrashError(RuntimeError)` propagates out, so
  the plan's instruction to wrap the crashing `reconcile` in
  `pytest.raises(_CrashError)` is correct.
- Convergence trace confirmed against `derive_reconciliation` precedence
  (`reconcile.py:262-272`): after the crash, `state.toml` carries the stale
  `[word_counts]` (`01:10000`) plus an `operation="reconcile"` `[pending_turn]`
  naming `("state.toml","log.md")`, both present on disk. Pass A classifies
  `COMPLETE_PENDING_TURN` with an empty missing set, so `_pending_turn_edit`
  writes no `[word_counts]` change and the bracket just clears the record; pass
  B then derives `RECOUNT` and rewrites the table to the disk-derived values.
  Two recovery passes, matching `test_reconcile_integration.py`'s documented
  two-pass convergence. The plan's D-CONVERGE bounded loop is correct.
- `check`'s envelope exposes `result.reconciliation.action` =
  `"complete-pending-turn"` for the post-crash tree
  (`novel_state.py:160-176, 233-236`); the plan's assertion path is valid.
- Post-recount target `{"01": 0, "02": 24000, "03": 20800}` → 44800 matches
  the `done_claim_stale_word_counts` variant (stale table sum 54800, honest
  draft total 44800).
- Design §3.4/§4.1 interpretation is conformant: the bracket is for
  *multi-file* turns; the single-file mutators open none, so `reconcile` is the
  only v1 bracket-opening command. The plan's Risk/Tolerance pin this correctly.
- No new dependency; no uncited locked-library behaviour claim — the mechanism
  uses only the in-process runner, `monkeypatch`, and the corpus. The bounded
  loop is plain Python and fits comfortably inside the 30s xdist timeout.
- The new `torn_turn_recovery.feature` name does not collide with the existing
  `torn_turn.feature`; the primitive test is producer-signature only and is not
  modified.

## Blocking

1. **False coverage claim in the Constraints block (lines 70-71).** The plan
   asserts the hand-planted `uncleared-pending-turn` corpus variant "already has
   command-boundary coverage in `tests/test_novel_state_check_disk.py` *and
   `tests/test_reconcile_e2e.py`*." Verified false: `test_reconcile_e2e.py`
   contains no pending-turn coverage at all (it covers `recount`,
   `cover`-gap, and `recreate-log` only). The hand-planted variant has
   `check`-boundary coverage in `test_novel_state_check_disk.py:85` only; no
   test reconciles a hand-planted COMPLETE/ROLLBACK pending-turn through the
   command boundary. Correct the citation (drop `test_reconcile_e2e.py`) and
   restate the actual coverage. This claim is load-bearing for the plan's
   scope/completeness argument, so it cannot stand uncorrected.

## Advisory

- **Near-duplication of the existing integration test.** `test_reconcile_
  integration.py::test_interrupted_reconcile_leaves_recoverable_record` already
  crashes a real `reconcile` and drives recovery `reconcile`/`check` through the
  runner (`_drive` → `run(build_app(), ...)`); its only non-command-boundary
  step is the *crash-producing* call (`_reconcile.reconcile()` direct, line
  158). The plan's genuine delta is narrow: drive the *crashing* reconcile
  through `run(...)` too, and express it as a BDD scenario. This is exactly the
  roadmap gap, so the work is justified — but the plan should state the delta
  crisply (it is "move the crash-producing call onto the command path", not a
  whole new recovery proof) so the implementer does not re-derive coverage that
  exists. Tighten the Purpose section to say so.

- **Stage B "red" is contrived.** The plan concedes the red signal requires
  transiently stubbing the convergence loop or the crash-origin assertion
  (lines 386-391). A scenario that "fails because it is unbound" is a collection
  error, not a behavioural red. The plan's guard ("do not leave Stage B with a
  passing test that never exercised the crash path") is the right mitigation;
  keep it explicit and prefer a genuine red where the crash path is asserted but
  the convergence step is the last to land.

- **ROLLBACK branch is out of scope and uncovered at the reconcile boundary.**
  The scenario only exercises COMPLETE (both declared paths present). The
  roadmap clause says "completes or rolls it back per what landed"; the COMPLETE
  branch alone satisfies the success clause ("recovered by reconcile"), so this
  is acceptable for 6.2.5 — but the plan should not imply the ROLLBACK branch is
  already covered at the reconcile command boundary (it is not). Note it as a
  known gap rather than asserting coverage.

## Pre-mortem (most likely failure paths)

1. Implementer asserts `check`'s `result.violations` contains only
   `pending-turn-cleared`. In fact `word-counts-match-drafts` also still fires
   on the stale table, so `violations` carries both. Mitigation: assert the
   *reconciliation action* (`complete-pending-turn`) and membership of
   `pending-turn-cleared`, not the exact violation set. The plan's step text
   already leans this way; make it explicit.
2. Implementer asserts single-pass convergence. The first recovery `reconcile`
   clears the record but leaves the stale counts; a single-pass assertion would
   fail. Mitigation: the D-CONVERGE bounded loop is mandatory, not optional;
   reuse the `range(3)` loop shape from the integration test.
3. Implementer wraps the crashing `reconcile` in `pytest.raises(SystemExit)`.
   The crash propagates as `_CrashError`, never reaching `sys.exit`. Mitigation:
   the plan's Artefacts note already specifies `pytest.raises(_CrashError)`;
   keep it prominent in the step skeleton.

## Strongest alternative (Wafflecat)

Rather than a third BDD suite that largely overlaps the integration test,
*promote the existing integration test's crash-producing call onto the command
path* and add a thin BDD binder over it. Concretely: change
`test_interrupted_reconcile_leaves_recoverable_record` to drive the crashing
`reconcile` through `run(build_app(), ["reconcile"], ...)` (wrapped in
`pytest.raises(_CrashError)`) instead of `_reconcile.reconcile()`, then add the
Gherkin scenario as the human-readable acceptance face. Trades away: a fully
independent BDD module (slightly less isolation). Gains: one canonical crash
fixture, no duplicated `_run`/draft-bytes helpers (defusing the D-DUP review
risk entirely), and a smaller net diff. The plan's choice (a self-contained BDD
module per D-DUP) is defensible, but the alternative is genuinely viable and
would shrink the change; the planner should at least record why it was not
taken.
