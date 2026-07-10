# Logisphere design review — roadmap 6.2.4 ExecPlan, Round 3

Verdict: PROCEED. The plan is implementable and design-conformant as written.
Every load-bearing claim was re-verified against real source this round; the
round-1 and round-2 blocking defects are genuinely closed.

## What was re-verified this round (all true)

- **D-IMPORTS gap is real and the fix is correct.** `tests/conftest.py` imports
  `Program` only under `if typ.TYPE_CHECKING:` (line 60) and never imports
  `sh`; the runtime block (line 28) carries only
  `ProgramCatalogue, ProjectSettings`. The new module-scoped fixture body calls
  `sh.make(...)`, `Program("uv")`, `.run_sync(...)` at runtime, so the plan's
  step-1 runtime-import additions are necessary and accurately specified.
  Precedent `test_ai_isms_e2e.py` lines 31-32 imports all three at runtime,
  confirming the shape.
- **D-SCOPE is mechanically sound.** `single_program_catalogue` and
  `venv_scripts_dir` are function-scoped (`conftest.py` lines 238, 270); a
  module-scoped fixture cannot request them. `installed_desloppify`
  (`test_ai_isms_e2e.py` lines 49-83, 152-164) is the verbatim precedent:
  `scope="module"`, takes `tmp_path_factory`, inlines `_one_program_catalogue` /
  `_scripts_dir`. The plan mirrors it exactly.
- **Cross-module import is real and the reroute count is correct.**
  `test_reconcile_e2e.py` line 32 imports `_build_and_install_novel_state` and
  calls it at lines 212 and 260 (two installed e2es). The plan's "two installed
  e2es, now sharing 1 build" is accurate.
- **Exit-3 channel.** `runner.run` emits an `ok: false` envelope to stdout then
  `sys.exit(ExitCode.STATE_ERROR)` on `StateInputError` (lines 233-239);
  `STATE_ERROR == 3` (`exit_codes.py` line 29). Asserting both `exit_code == 3`
  and stdout JSON `ok is False` is correct.
- **recount exit-3 paths.** `_load_document_or_state_error` (missing/unparseable
  state) and `_recount_or_state_error` (read faults) both raise
  `StateInputError`. In-process `test_recount_missing_state_refuses` proves a
  `working/`-present, `state.toml`-absent cwd exits 3 — exactly the WI3
  "missing-state" shape; `test_recount_undecodable_draft_refuses` and the
  unparseable channel cover the rest. WI3 mirrors these at the installed
  boundary.
- **recount oracle.** The in-process e2e uses the identical spec WI2 specifies
  (drafting 3 and 5 words, `by_chapter_override={"01":999,"02":999}`,
  `current_words_override=1998`) and asserts
  `result == {"current": 8, "by_chapter": {"01": 3, "02": 5}}` (lines 67-69).
- **cuprum 0.1.0 surface (read-only sibling).** `Program` re-exported at
  `__init__.py` line 62; `sh` via `from . import builders, sh` and `__all__`;
  `sh.make` at `sh.py` line 528; `CommandResult.exit_code: int` (line 115),
  `.stdout: str | None` / `.stderr: str | None` (lines 117-118);
  `ExecutionContext.cwd` (line 196); `run_sync(capture=True)` captures both
  streams. All citations accurate.
- **pytest config.** `timeout = 30` default, `slow` marker registered,
  `pytest-timeout` and `pytest-xdist` present. Existing installed e2es combine
  `@pytest.mark.slow` + `@pytest.mark.timeout(180)` in-tree, proving Constraint
  7.
- **Doc anchors.** Design §9 "CLI error-path tests" bullet (lines 822-834) and
  the developers-guide shared-scaffolding rule (lines 31-64) exist where WI4
  points.

## Adversarial probes that did not yield defects

- **Unused fixture parameter after reroute.** Rerouting drops
  `venv_scripts_dir` from the three test signatures. Neither Ruff (`ARG` family
  not selected) nor Pylint (`unused-argument` not in the curated `enable` list)
  flags an unused fixture parameter, so this is not a gate trap. The plan's
  "behaviourally identical / pure refactor" framing holds.
- **Module-scoped install mutated by mutator tests.** Every run materializes its
  own per-test `run_dir = tmp_path / "run"` and mutates `state.toml` there,
  never the shared install under `tmp_path_factory`. The subtrees never overlap
  (Decision D-CWD). Confirmed against the existing check/reconcile e2e bodies,
  which already isolate the run tree this way.
- **Deterministic/judgemental boundary.** All three new tests assert exit codes
  and `ok`/`result` only — pure deterministic observation, no narrative
  judgement. Conformant.

## Notes (non-blocking)

- The dev-guide installed-console-script anchor WI4 cites ("near line 926") is
  rulepack-adjacent prose, not a dedicated convention section; WI4 hedges with
  "any installed-console-script note near line 926," so the implementer is
  directed to record the convention wherever the shared-fixture rule lives
  (lines 31-64) rather than at a precise line. Acceptable.

Docs/skills relied on: docs/novel-ralph-harness-design.md §3.2/§4.1/§9/§10,
docs/adr-003 and adr-006, docs/developers-guide.md (shared scaffolding, lines
31-64), AGENTS.md (gates, markers), /data/leynos/Projects/cuprum source
(`__init__.py`, `sh.py`, `program.py`), and the logisphere-design-review skill
(Pandalump structural integrity, Wafflecat alternatives, Buzzy Bee
scaling/cost, Telefono contracts, Doggylump failure modes, Dinolump viability).
