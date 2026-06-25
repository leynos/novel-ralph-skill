# Logisphere adversarial design review — roadmap 6.2.2, round 2

Reviewed: `docs/execplans/roadmap-6-2-2.md` (read from disk, round-2 revision).
Verdict: **Proceed** — round-1 blocking defect B1 is resolved by a mechanism
verified empirically, not on trust. No blocking defects remain. Two minor
advisories below are non-blocking polish.

## Method / trail followed

- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- Docs of record: `docs/roadmap.md` (6.2.2 entry, lines 1293-1300, success
  criteria exact); `docs/novel-ralph-harness-design.md` §7.2 (Figure 3
  per-chapter pipeline), §9 lines 835-847 (installed-binary e2e mandate), §4.5,
  §4.2/§4.3, §10; ADR-003, ADR-006; `AGENTS.md` gates; `pyproject.toml`.
- Source verified: the five `build_app` factories
  (`novel_ralph_skill/commands/{novel_state,_novel_done,_wordcount,_desloppify,_compile}.py`);
  `tests/working_corpus/_done_predicate_specs.py` (specs + exports);
  `tests/steps/advance_phase_steps.py` (the `INCOHERENT_VARIANTS["completed-prefix-gap"]`
  tuple-unpack + byte-identity model); `tests/steps/torn_turn_recovery_steps.py`
  (the single-command `_run_capturing` the new helper must NOT copy verbatim);
  `tests/test_compile_check_snapshots.py` (the D-CHECK-ARGV `--check` trap);
  `tests/test_console_scripts_e2e.py`, `tests/test_recount_e2e.py`,
  `tests/installed_binary_fixtures.py` (module-scoped wheel, plain-pytest marks);
  every `tests/test_*_bdd.py` binder (all bare `scenarios(...)`, no per-scenario
  marks — confirming round-1's "no repo idiom" finding).
- cuprum (read-only sibling `/data/leynos/Projects/cuprum`):
  `cuprum/sh.py` — `ExecutionContext.cwd` is a real documented field;
  `make`/`run_sync`/`.exit_code`/`.stdout`/`.stderr` real.
- Locked versions confirmed in `uv.lock`: pytest-bdd **8.1.0** (resolved, not
  just the `>=8.1.0` floor), pytest-timeout **2.4.0**, pytest 9.1.1, cuprum,
  cyclopts.

## The round-2 fix (B1) — verified empirically, not on trust

The plan's central round-2 claim is that an `@scenario`-decorated binder
function can carry `@pytest.mark.slow`, `@pytest.mark.timeout(180)`, and the
POSIX `@pytest.mark.skipif`, and that a guard test can assert those marks via
`func.pytestmark`. The doc scrape was not taken on trust; a throwaway feature +
`@scenario`-decorated binder with the three marks stacked above `@scenario` (the
exact order the plan specifies) was built and run:

- The decorated function **collects as a test** and passes.
- `test_probe.pytestmark` exposes `{"skipif", "slow", "timeout"}` — the
  marker-guard mechanism in Work item 3 works exactly as written.
- `@pytest.mark.skipif(True, ...)` on the `@scenario` function **actually skips**
  the scenario (1 skipped), so the POSIX gate fires.
- `@pytest.mark.timeout(1)` on the `@scenario` function **actually aborts** a 3s
  step ("Failed: Timeout (>1.0s) from pytest-timeout"), so the 180s override is
  real per-item, not cosmetic.
- `inspect.signature(pytest_bdd.scenario)` →
  `(feature_name, scenario_name, encoding='utf-8', features_base_dir=None) ->
  Callable[[Callable[P, T]], Callable[P, T]]` — a decorator factory, so the marks
  stack above it.

This is the strongest possible resolution of B1: the mechanism is the
repo-idiomatic plain-pytest mark surface, it is documented, AND it is
demonstrated to behave correctly under this exact pytest/pytest-bdd/pytest-timeout
lock. The feature split (own feature + own binder) means the POSIX skip cannot
leak onto the cross-platform in-process scenarios, which is structurally clean.
The round-1 pre-mortem mitigation (a guard test asserting the marks are present)
is folded in and is itself verified to work.

## Round-1 advisories — all folded in correctly

- **A2** (import root): the plan now specifies `from steps.<module> import *`,
  not `from tests.steps.<module>`. Confirmed correct: `pyproject.toml`
  `testpaths = ["tests"]` with no `tests` package root; every existing binder
  uses `from steps.<module>`.
- **A3** (`_run_capturing` shape): the plan now states explicitly that the helper
  selects the matching `build_app` factory and `RunContext(command=...)` per
  `command_name` across all five commands, rather than copying the single-command
  `torn_turn_recovery_steps._run_capturing` (whose `build_app`/`_COMMAND` are
  module-fixed). Verified against the cited helper — the warning is apt.
- **A4** (per-commit cost): the plan now states the gate runs the slow installed
  scenario unconditionally on every commit (no `-m "not slow"` deselection),
  matching the existing slow e2es. Correct framing.
- **A5** (ini vs flag): the Decision Log now cites the **ini** `timeout = 30`
  (`pyproject.toml` line 326) being overridden by the per-item marker, not a
  `--timeout` flag. Confirmed: line 326 is the ini value; line 328 registers
  `slow`.

## Crew pass (this round)

- **Pandalump** (structure): boundaries are clean. Two features, two step
  modules, two binders, one doc — the split is drawn exactly where the platform
  contract changes (cross-platform in-process vs POSIX-only installed). No
  marker leak path remains. Deterministic/judgemental boundary respected: the
  plan drives only the scripted half of Figure 3, never the judgemental reads.
- **Wafflecat** (alternatives): round-1's recommended alternative (split the
  installed scenario into its own feature+binder) was adopted. No stronger
  alternative remains; the `pytest_bdd_apply_tag` hook is correctly rejected as
  more surface for no benefit.
- **Buzzy Bee** (scaling/cost): one module-scoped wheel build per gate; per-test
  `run_dir` keeps the mutator `recount` isolated per scenario. 180s budget
  matches the existing installed e2es. No unbounded cost.
- **Telefono** (contracts): every pinned envelope key path
  (`result["cumulative"]["gate_triggered_30/50/80"]`, `result["diverged"]`,
  `compile_consistent`, recount `{current, by_chapter}`) was already verified in
  round 1 against real source; nothing changed. Exit-code contract (0/3/4) is the
  externally visible harness contract and is asserted at both boundaries.
- **Doggylump** (failure modes): the round-1 pre-mortem failure (silent loss of
  the timeout/skip marks) is now guarded by `test_installed_scenario_carries_marks`,
  confirmed to work via the `.pytestmark` probe. The corpus-drift risk has
  a re-capture-then-escalate mitigation.
- **Dinolump** (viability): the mechanism is plain pytest marks the team already
  uses; no novel repo machinery. The developers-guide cross-reference records the
  "installed BDD scenario lives in its own feature + `@scenario` binder so it can
  carry argument-bearing marks" convention for the next author.

## ADVISORY (non-blocking polish)

- **A6** (Telefono, minor). The marker-guard test asserts
  `{"slow", "timeout", "skipif"} <= marks`. The POSIX `skipif` mark is the one
  the guard most needs to protect (a dropped `skipif` makes the wheel build run
  on a non-POSIX CI leg — a hard error, not a quiet quarantine). The plan already
  includes `skipif` in the asserted set, which is correct; just ensure the
  implementer does not trim the guard to `{"slow", "timeout"}` (the round-2 prose
  mostly says "slow + timeout" and only once names `skipif`). Keep all three in
  the assertion. Non-blocking because the plan's concrete guard line already lists
  all three.
- **A7** (Dinolump, minor). The clean-pass installed scenario re-drives `recount`
  (a mutator) before the read commands. Because `recount` over
  `DONE_PREDICATE_ALL_HOLD` is a no-op on the counts (Risk 2, verified in
  round 1: drafts already match the table), the downstream installed reads see an
  unchanged tree. Worth a one-line assertion in the installed steps that the
  installed `recount` exits 0 and leaves the by-chapter counts at the drafted
  totals (mirroring the in-process Risk-2 mitigation), so an installed-only
  mutator regression cannot mask a later read. Non-blocking; the in-process
  scenario already pins this and the installed envelope assertion would catch a
  divergence anyway.

## Pre-mortem (Doggylump, refreshed)

The round-1 most-likely failure (marks silently lost) is now closed by both the
feature/binder split and the guard test, each independently verified here. The
residual six-months-out scenario is a corpus refactor (phases 2-6 are supposed to
consume the corpus unchanged, developers-guide lines 80-81) silently repairing
the stale `compiled.md` or filling the out-of-order `phase.completed`, flipping
a pinned exit code. Mitigation is already in the plan: every pin is reproducible
from the Surprises ground-truth capture, and a divergence escalates under the
Iterations tolerance rather than being re-pinned. Adequate.

## Alternatives checkpoint (Wafflecat)

No credible alternative remains. The one structural fork (own feature+binder vs
co-housed with a tag hook) was resolved in favour of the split, which is both
repo-idiomatic and the lower-surface option. That the only fork is settled is a
strong signal the design is on solid ground.

## Verdict

✅ **Proceed.** B1 is resolved by an empirically verified, repo-idiomatic,
documented mechanism. All four round-1 advisories are folded in correctly. Every
load-bearing behavioural claim (corpus specs, envelope key paths, cuprum API,
build_app factories, the `--check` argv trap, the marker mechanism, the
ini-vs-marker timeout override) is verified against real source or demonstrated
empirically. A6/A7 are optional polish the implementer may apply inline. This
plan is implementable and design-conformant as written.
