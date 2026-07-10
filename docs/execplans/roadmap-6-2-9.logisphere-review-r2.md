# Logisphere design review — roadmap 6.2.9, round 2

Verdict: **Proceed** (✅). The round-1 blocking points are genuinely resolved and
every load-bearing factual claim verifies against the real source. Findings below
are advisory; none block implementation.

## What was verified against real source (not the planner's summary)

- **Gate runs slow tests inline (S3).** `Makefile` `test` target is
  `... pytest -v -n $(PYTEST_XDIST_WORKERS)` with no `-m 'not slow'`;
  `pyproject.toml` `[tool.pytest.ini_options]` has `timeout = 30`,
  `markers = ["slow: ..."]`, and **no** `addopts`; `tests/conftest.py` has no
  `pytest_collection_modifyitems` deselection; CI runs on `ubuntu-latest`
  (POSIX) via `make test`. The plan's "no slow deselection anywhere; WI-1 must be
  green in one commit" conclusion is correct. The round-1 "make all may deselect
  the slow item" hedge is genuinely removed. (Minor: the plan cites `Makefile:116`
  and `ci.yml:10`; the substantive lines are off by a line or two but the content
  is exactly as claimed.)
- **cuprum 0.1.0 surface.** The *installed* artefact's `SafeCmd.run_sync` is
  `(*, capture=True, echo=False, context=None) -> CommandResult` — exactly the
  chain the existing `_run_installed` uses and the plan reuses. Confirmed by
  introspecting the installed package. NOTE: the read-only sibling checkout at
  `/data/leynos/Projects/cuprum` has **drifted** to a newer API
  (`run_sync(*, output: RunOutputOptions, ..., stdin)`, no `capture`) while still
  labelled 0.1.0, so the plan's sibling-source line citations (`sh.py:441`,
  `:528`) now point at drifted code. The behaviour the plan depends on is pinned
  by the existing green installed test and re-verified here; the surface is sound.
- **Helper conflation (S2).** Real `_run_installed(installed, command_name)` uses
  `command_name` as script filename (`scripts_dir / command_name`), argv key
  (`_LOOP_ARGV[command_name]`), and the catalogue label
  (`per-chapter-loop-{command_name}`); callers write
  `installed.captures[command_name] = _run_installed(...)` at 3 sites
  (lines 167, 237, 238). The refused advance needs script `novel-state`,
  argv `("advance-phase",)`, capture key `advance-phase` — three values one
  argument cannot carry. The `_run_installed_argv(script_name, argv, *,
  capture_key)` split is genuinely required, and the delegation keeps the
  clean-pass/stale paths byte-identical (capture_key == command_name there).
- **state.toml path.** `build_working_tree(spec, dest)` creates `dest/working/`
  and writes `dest/working/state.toml`. `_build_installed` builds at
  `run_dir = tmp_path/"run"`, and the script runs with `cwd=run_dir`. So the
  plan's `(run_dir / "working" / "state.toml")` read in the new Given/Then is
  correct (it mirrors the in-process `(working / "state.toml")` where
  `working == tmp_path/"working"`).
- **Crossed gate already installed-proven (S1).** The existing scenario's
  `Then the installed wordcount reports all three knitting gates crossed` binds
  `installed_wordcount_gates`, which asserts `gate_triggered_30/50/80 is True` at
  `cumulative["current"] == 68800`. Adding a crossed-gate scenario would be
  redundant; documenting it (WI-3) is the right call. Faithful to audit-6.2.2
  Finding 7, which offers add-or-document and names refused-advance the
  highest-value addition.
- **Mark guard.** `_REQUIRED_MARKS = frozenset({"slow", "timeout", "skipif"})`
  and the existing `test_installed_scenario_carries_marks` read
  `getattr(test_installed_per_chapter_loop, "pytestmark", ())`. WI-2 mirrors this
  exactly for `test_installed_advance_phase_refused`. Wheel-free, green on
  landing.
- **Fixture scope.** `installed_novel_state` is `scope="module"`, so both
  scenarios in the binder share one wheel build/venv — the plan's double-build
  mitigation holds.
- **Module-size / tolerances.** Installed steps module is 262 lines today;
  +~45 stays well under the 400 cap. Edits touch 5 files (feature, steps, binder,
  dev guide, plan) — at the tolerance ceiling, not over.
- **Design anchors.** §§3.2, 4.1, 4.5, 5.4, 9, 10 all exist at the cited
  headings. The dev-guide sentence WI-3 rewrites ("re-driving the clean pass and
  the stale-compile catch") is present and correctly located.

## Advisory (non-blocking)

- A1 (Telefono): `_run_installed_argv` becomes a command/query hybrid — it both
  returns the `(exit, env, stderr)` tuple AND writes `installed.captures`. The
  plan turns the 3 existing call sites into bare calls to avoid a double-write.
  This is fine under the `tests/steps/` exemption, but the module docstring must
  state the side-effect contract clearly so a future reader does not re-add the
  `captures[...] =` assignment and double-write. The plan already says to record
  this — keep that promise.
- A2 (Pandalump): the binder imports steps via `from steps.<module> import *`
  (import root `steps`, not `tests.steps`). The new steps land in the same module
  so `import *` picks them up automatically — but the plan never names this root.
  No action required; just do not introduce a new steps module.
- A3 (citation hygiene): refresh the cuprum `sh.py` line citations in
  "Interfaces and dependencies" to note they describe the *pinned installed
  0.1.0* surface, since the sibling checkout has drifted. Memory of the surface
  is fine here only because the existing green test pins it; future readers
  should not be sent to the drifted sibling lines.
- A4 (Doggylump): the transient red→green demonstration (point the new Given at
  a coherent tree, confirm exit-3 assertion fails, revert) is the behaviour pin
  in lieu of a committed red state. Sound given the inline-slow gate. Ensure the
  "coherent tree" chosen for the red demo genuinely *advances* (exits 0/non-3) —
  use a clean `drafting` spec whose `phase.completed` is an in-order prefix, not
  another incoherent variant.

## Pre-mortem (no blocker emerged)

Most-likely six-months-out failure: a maintainer adds a third installed scenario,
copies the new `When` step, reuses capture key `advance-phase`, and the two
scenarios' captures appear to collide. Mitigated already: each `@scenario`
function is an independent test item with its own `_Installed`, so captures never
share a dict; WI-2's mark guard catches the other likely regression (a dropped
mark). No durability/blast-radius concern — this is test-and-docs only, no
production code touched.

## Strongest alternative (Wafflecat)

Document-only (Finding 7's second option): name the in-process-only bound in the
dev guide and add a `Carried gaps` entry, skipping the new scenario. Trades away
real installed proof of the runner-stamped exit-3 arm — exactly the POSIX
exit-code translation the installed boundary exists to prove — for ~45 fewer test
lines and one fewer slow item. The plan correctly rejects it: Finding 7 itself
calls the refused-advance re-drive "the highest-value addition." Proceed as
planned.
