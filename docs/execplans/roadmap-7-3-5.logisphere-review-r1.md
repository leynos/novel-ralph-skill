# Logisphere design review — ExecPlan roadmap-7-3-5, round 1

Adversarial pre-implementation review of
`docs/execplans/roadmap-7-3-5.md` (DRAFT). Verdict: **REVISE** — the
constructive design is sound and the library/source claims verify, but the
plan's test-impact analysis is wrong in a way that guarantees a red gate and
duplicates an existing guard.

Trail followed: `logisphere-design-review` skill; design §4
(`docs/novel-ralph-harness-design.md`); ADR 003, ADR 007; AGENTS.md (400-line
cap, docstring/example rule, `interrogate` 100%); the real source for
`novel.py`, `contract/runner.py`, `contract/__init__.py`; the test scaffolding
(`tests/test_multiplexer_behaviour.py`, `tests/test_novel_main_working_dir.py`,
`tests/test_contract_app_centralisation.py`, `tests/test_legacy_surface_retired.py`,
`tests/conftest.py`, `tests/_state_layout_scanner.py`,
`tests/test_multiplexer_mount_table.py`); read-only cuprum checkout at
`/data/leynos/Projects/cuprum`; `docs/roadmap.md` lines 3040-3065.

## What verifies (the plan's strong half)

- S1/D1 reframing is correct. `stub.py`/`_drive`/`COMMAND_ENTRY_POINTS` were
  retired by ADR 007 (1.2.15); the only `_drive` left is the test fixture in
  `tests/contract_drive_support.py`. The constructive single-home seam is the
  right reading of the roadmap success criterion.
- D2 signature matches reality. `run` is `typ.NoReturn`; `RunContext` is a
  `frozen, kw_only` dataclass with exactly `command`/`working_dir`/`human`. The
  seam body in "Interfaces and dependencies" type-checks against the real
  symbols.
- D3 fallback is moot in practice: `runner.py` is 250 lines; +~35 stays well
  under 400. Harmless to keep as a recorded contingency.
- cuprum claims verify against source: `ProgramCatalogue.__init__(*, projects)`
  at catalogue.py:62, `.allowlist` at :70, `sh.make` at sh.py:528. The seam
  shells out to nothing, so "no new cuprum surface" is accurate.
- `runner.py` imports no `commands` module today; the WI4 layering guard pins a
  real, currently-true invariant.

## Blocking defects (back to the planner)

### B1 — WI2 breaks `tests/test_contract_app_centralisation.py`; the plan never mentions it

`tests/test_contract_app_centralisation.py:122` does
`monkeypatch.setattr(novel, "run", _capture_run)` then calls `novel.main()` and
asserts `"app" in captured` ("novel did not route through the shared run
seam"). It is an existing structural tripwire for roadmap 1.3.6 / audit:1.3.6
Finding 3.

After WI2 repoints `main` onto `drive(...)` and drops `run` from novel.py's
imports (as WI2 step 1 instructs), `main` no longer calls the module-level
`run` symbol. The monkeypatch then patches a symbol `main` never invokes (or a
removed attribute), `captured` stays empty, and the assertion fails. WI2's
claim "Expect green with no behavioural test changes" is false. The plan must
enumerate this test and specify its migration (patch `novel.drive`, or assert
the seam routes through `run` at the `runner` layer) so the 1.3.6 invariant is
preserved transitively.

### B2 — WI3 guard contradicts B1's existing test; the conflict is unreconciled

WI3 guard 3b asserts `novel.main`'s body contains **no** `Call` to `run`.
`test_contract_app_centralisation.py` currently asserts `main` **does** invoke
`run`. These two guards cannot both pass against the same surface. The plan
must resolve the contradiction explicitly: re-home the 1.3.6 "routes through the
shared seam" check onto `drive` (and have the seam prove it forwards to `run`),
not silently leave two guards asserting opposite structural facts about `main`.

### B3 — WI2 caller enumeration is factually wrong

WI2 says to "confirm every `novel.main` caller (only the console-script
declaration and the two behaviour tests)". `grep -rln "novel\.main()" tests/`
returns **12** files (test_compile_e2e, test_compile_check_integration,
test_contract_app_centralization, test_novel_main_working_dir,
test_gate_drafting_mutators_e2e, test_reconcile_e2e, test_multiplexer_behaviour,
test_set_chapters_e2e, test_recount_e2e, test_legacy_surface_retired,
test_novel_state_check, test_relaxed_subset_e2e). The plan must re-run the
enumeration and confirm which of these assert on `main`'s internal plumbing
(at minimum B1's test does) versus pure behaviour, before claiming parity.

### B4 — WI3 guard 3a duplicates an existing guard and ignores existing scaffolding

`tests/test_legacy_surface_retired.py` already has
`test_pyproject_scripts_is_novel_only` and `test_script_table_is_novel_only`,
both asserting `[project.scripts]` is exactly `novel`, using the `pyproject` and
`project_scripts` fixtures in `tests/conftest.py:136,201`. WI3 step 1a proposes
a fresh `tests/test_entry_point_single_home.py` that re-parses pyproject with
stdlib `tomllib` — re-copying scaffolding the developers-guide "Shared test
scaffolding" rule (which the plan itself cites) forbids. Guard 3a must extend
or reference the existing test/fixtures; only guard 3b (the ast "no inline
`RunContext` in `main`") is net-new.

## Advisory (non-blocking)

- A1 — `make all` is `build check-fmt lint typecheck test` (Makefile:37); it
  does **not** run `audit`. The plan states `make all` runs `audit` (lines ~351,
  ~579) and lists `make audit` as an acceptance gate. Either invoke `make audit`
  separately or drop the claim.
- A2 — The `drive` docstring "usage example" (WI1 step 3): the seam is
  `typ.NoReturn`, so a runnable doctest would terminate the process.
  `interrogate` only checks docstring presence, and `run`'s own docstring is
  prose-only (no example). Specify a *prose* example, not a doctest, to satisfy
  AGENTS.md without a hazard.
- A3 — WI2's "drop `RunContext`/`run` from that import line" is correct: after
  the edit `main` uses only `parse_global_flags`, `build_multiplexer`, and
  `drive`. State explicitly that the import becomes
  `from novel_ralph_skill.contract import drive, parse_global_flags` so the
  implementer does not leave an unused-import lint failure.

## Pre-mortem (Doggylump)

Six months on, the most likely incident: WI2 lands, CI goes red on
`test_contract_app_centralisation`, the implementer "fixes" it by deleting the
monkeypatch assertion rather than migrating it — quietly retiring the 1.3.6
routing guarantee. Blast radius: a future re-inlined entry point that bypasses
the shared seam ships undetected. Prevention designed in now: B1+B2 force the
1.3.6 guard to be migrated, not removed, and reconciled with the new WI3 guard.

## Alternatives checkpoint (Wafflecat)

The strongest alternative: instead of a separate `drive` seam wrapping `run`,
fold the `RunContext` construction into `run` itself by overloading it to accept
keyword scalars. Trade-off: fewer indirections and no new public symbol, but it
widens `run`'s signature (a Tolerances escalation trigger) and muddies the
"`run` owns exit/emit; the entry point owns resolution" boundary. The plan's
thin-wrapper seam is the better call. No change recommended to the mechanism —
the defects are in the test-impact analysis, not the architecture.
