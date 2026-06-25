# Logisphere adversarial design review — roadmap 6.2.2, round 1

Reviewed: `docs/execplans/roadmap-6-2-2.md` (read from disk).
Verdict: **Revise** — one blocking structural defect; the plan is otherwise
exceptionally well-grounded (nearly every behavioural claim verified against real
source).

## Method / trail followed

- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- Docs of record: `docs/roadmap.md` (6.2.2 entry, lines ~1293-1300);
  `docs/novel-ralph-harness-design.md` §7.2, §9, §4.5, §4.2/§4.3, §10;
  `docs/developers-guide.md` (installed-binary + matrix subsections);
  ADR-003, ADR-006; `AGENTS.md` gates.
- Source verified: `novel_ralph_skill/commands/_wordcount_report.py`,
  `_wordcount.py`, `_compile.py`, `_novel_done.py`, `novel_state.py`;
  `tests/working_corpus/_done_predicate_specs.py` (lines 51-272);
  `tests/steps/torn_turn_recovery_steps.py`, `tests/steps/advance_phase_steps.py`;
  `tests/installed_binary_fixtures.py`, `tests/test_console_scripts_e2e.py`,
  `tests/test_recount_e2e.py`, `tests/conftest.py`, `pyproject.toml`, `Makefile`,
  every `tests/test_*_bdd.py` binder.
- cuprum (read-only sibling `/data/leynos/Projects/cuprum`): `cuprum/sh.py`
  (`ExecutionContext.cwd`, `run_sync`, `.exit_code/.stdout/.stderr`).
- Locked-library docs firecrawled: pytest-timeout 2.4.0 (PyPI),
  pytest-bdd 8.1.0 (readthedocs).

## What is solid (verified, not taken on trust)

- Corpus claims hold exactly: `DONE_PREDICATE_ALL_HOLD` is phase `done`, all three
  gates crossed, `compiled=COMPILED_AUTO`; `_DRAFTED_WORDS=(24000,24000,20800)`
  sum 68800; `_TARGET_WORDS=80000`; ratio 0.86 ≥ 0.80 so all gates trigger and
  `next_gate_threshold` is `None`. `DONE_PREDICATE_SOLE_STALE_COMPILE` is the
  count-coincident byte-divergent carve-out. `INCOHERENT_VARIANTS["completed-prefix-gap"]`
  is the out-of-order tree, asserted byte-identical by the existing step module.
- Envelope key paths verified: `wordcount` result nests
  `result["cumulative"]["gate_triggered_30/50/80"]` and `result["chapters"]`;
  `novel-compile --check` carries `result["diverged"]`; `novel-done` exposes
  `compile_consistent`; `recount` carries `result["current"]` and
  `result["by_chapter"]`.
- `wordcount` has **no** phase gating (it always populates from disk), so the
  plan's "drafting-era" provenance phrasing is harmless — the populated branch
  holds at phase `done`.
- cuprum API the installed scenario uses is real and proven in-repo.
- pytest-timeout 2.4.0 marker-override claim is correct per official docs (the
  per-item `@pytest.mark.timeout` overrides the ini `timeout = 30`).
- No production or corpus change is required; all four scenarios are expressible
  over existing corpus trees through the command boundary.

## BLOCKING

### B1 — Per-scenario marker mechanism for the installed scenario is unspecified, and no repo idiom supports it (Pandalump / Doggylump / Telefono)

The plan puts the in-process scenarios (run on every platform, governed by the
global 30s timeout) **and** the `@slow`, POSIX-only, `timeout(180)` installed
scenario in the *same* feature file bound by a *single* bare
`scenarios("features/per_chapter_loop.feature")` binder (Work item 1 spec;
Interfaces). It then defers the marker question to "carried via the binder or
per-step markers as the repo idiom requires" (Work item 3) — but:

- Every BDD binder in this repo uses bare `scenarios(...)` and applies **no**
  per-scenario marks. There is **no** `@scenario`-decorated binder and **no**
  `pytest_bdd_apply_tag` hook anywhere in `tests/`. The "repo idiom" the plan
  appeals to does not exist.
- pytest-bdd 8.1 auto-converts Gherkin tags to markers, so a `@slow` tag does
  become `@pytest.mark.slow`. But `@pytest.mark.timeout(180)` and the POSIX
  `skipif(os.name != "posix", ...)` **take arguments** and cannot be expressed
  as bare Gherkin tags. A bare `@timeout`/`@posix` tag yields an argument-less,
  unregistered marker — useless for the 180s budget and the skip condition (and
  a `PytestUnknownMarkWarning`, since only `slow` is registered).
- A module-level `pytestmark = skipif(os.name != "posix")` on the binder (the
  pattern `test_console_scripts_e2e.py` uses) would wrongly skip the in-process
  scenarios that must run everywhere, because they share the binder module.

The repo's installed e2es achieve POSIX-skip + slow + timeout(180) only because
they are **plain pytest functions** (`test_recount_e2e.py`,
`test_console_scripts_e2e.py`), not `scenarios()`-bound BDD tests. The plan
inherits none of that wiring automatically.

This contradicts the plan's own Tolerances claim that it "carries **no**
undecided step." The implementer cannot proceed without inventing an
unvalidated pattern. Resolve by specifying one concrete, working mechanism, e.g.:

  (a) put the installed scenario in its **own** feature file and its **own**
      binder module, bound with `@scenario(...)` on a function decorated with
      `@pytest.mark.slow`, `@pytest.mark.timeout(180)`, and the POSIX
      `@pytest.mark.skipif`, leaving the in-process scenarios in the unmarked
      binder; or
  (b) keep one feature but add a `pytest_bdd_apply_tag` hook (in `conftest.py`
      or the binder) translating, say, `@slow` to the slow+timeout+POSIX-skip
      marker bundle, and register every tag used. Either way name the hook,
      show where it lives, register the markers in `pyproject.toml`, and confirm
      it under `pytest -n auto`.

Until B1 is pinned to a real mechanism the plan is not implementable as written.

## ADVISORY (fix, but not on their own blocking)

- A2 (Telefono). Work item 1's binder spec (plan line ~494) writes
  `from tests.steps.per_chapter_loop_steps import *`. The repo convention is
  `from steps.<module> import *` (every existing `*_bdd.py`; `pyproject.toml`
  `testpaths = ["tests"]`, no `tests` package import root). `tests.steps...`
  will `ModuleNotFoundError`. Correct the import to `from steps.per_chapter_loop_steps`.
- A3 (Pandalump). `_run_capturing` in `torn_turn_recovery_steps.py` (the cited
  model) takes a single `command` string and a module-fixed `build_app()` /
  `_COMMAND`. The clean-pass scenario must drive **five different** `build_app`
  factories with different argv (`["recount"]`, `[]`, `["--check"]`,
  `["check"]`/`advance-phase`). The plan's proposed signature
  `_run_capturing(working, argv, monkeypatch)` is the right shape but is **not**
  a copy of the cited helper — it must also select the matching `build_app` and
  pass the matching `RunContext(command=...)`. State this explicitly so the
  implementer does not mirror the single-command helper verbatim.
- A4 (Doggylump). `make all` → `make test` runs `pytest -n auto` with **no**
  `-m "not slow"` deselection, so the installed scenario builds a wheel on
  **every** commit gate, not only when run with `-m slow`. The plan's Concrete
  Steps imply the slow path is a separate `-m slow` run; clarify that the gate
  runs it unconditionally (this matches the existing slow e2es and is fine, but
  the framing misleads on per-commit cost — relevant to the 500-line/iteration
  tolerances and gate wall-clock).
- A5 (Telefono). Decision-log pytest-timeout citation says the marker overrides
  "the --timeout flag"; the repo's global is the **ini** `timeout = 30`, not a
  `--timeout` flag. The override still holds (marker is highest per-item
  priority, ini is lowest), but quote the ini-vs-marker priority, not the flag.

## Pre-mortem (Doggylump)

Most likely six-months-out failure: the installed BDD scenario silently lost its
180s timeout and/or POSIX skip because the marker bundle was wired by a fragile
ad-hoc mechanism (B1 unaddressed), so on a CI runner the wheel build either ran
on a non-POSIX leg (hard error) or tripped the global 30s timeout and was
quarantined/`xfail`-ed, eroding the very installed-boundary confidence §9
demands — the loss invisible because no test asserts the marker is present.
Mitigation: pin B1's mechanism now and add a guard (e.g. assert the scenario
carries the timeout/skip via `item.iter_markers`) or keep the installed scenario
in a dedicated, plainly-decorated binder where the marks are visually obvious.

## Alternatives checkpoint (Wafflecat)

Strongest alternative: **split the installed scenario into its own
feature+binder file** rather than co-housing all five in one feature. Trades
away the "one scripted pass reads as one file" narrative the roadmap success line
evokes; gains a clean, repo-idiomatic marker surface (plain `@scenario` +
function decorators, exactly as the existing installed e2es), eliminating B1
entirely and most of A3/A4's ambiguity. Given that the installed scenario is
already a *separate* drive (different runner, different fixtures, different
platform contract), the monolithic-feature framing buys little and costs the
marker headache. Recommend the planner adopt this unless it can specify a
concrete single-file mechanism for B1.
