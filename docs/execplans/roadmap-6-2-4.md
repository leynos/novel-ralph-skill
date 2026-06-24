# Broaden installed-binary e2e coverage to `recount` and the exit-3 state-error paths

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (all four work items landed and gated; 2026-06-25)

## Purpose / big picture

The harness gates on the five console-scripts by exit code, so the project must
prove those exit codes hold for a *real installed binary*, not merely for the
in-process entry-point body. Today exactly one happy path crosses the real
wheel/venv subprocess boundary for `novel-state` (`check`, exit 0, in
`tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero`),
plus `desloppify`'s exit 4 and `novel-done`'s 0/1/4. Two contractually
load-bearing behaviours of `novel-state` are *not* proven against an installed
binary:

1. `recount` (a mutator) is proven only through `stub.novel_state()` in-process
   (`tests/test_recount_e2e.py`); no test runs the installed
   `novel-state recount` over a built wheel.
2. The exit-3 *state-or-input-error* path (missing or unparseable `state.toml`)
   is proven only in-process (`tests/test_novel_state_check.py`,
   `tests/test_recount_unit.py`); no installed binary is ever observed exiting
   3.

After this change, a developer can run the slow installed-binary e2e suite and
observe two new proofs against a real console-script: the installed
`novel-state recount` corrects wrong counts and exits 0 with a recounted
`{current, by_chapter}` envelope, and the installed `novel-state recount`
(and/or `check`) exits 3 with an `ok: false` state-error envelope over a
missing or unparseable `state.toml`. The exit-code contract the harness
branches on (design §3.2; ADR-003) is then anchored at the subprocess boundary
for the recount and state-error cases exactly as it already is for the
exit-0/1/4 cases.

Observable success, runnable verbatim:

```bash
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-4
uv run pytest -v tests/test_recount_e2e.py -m slow
# expect: the new installed-binary recount and exit-3 e2es pass (others may be
# deselected by the -m slow filter).
```

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. Do not edit anything outside the worktree
   `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-4`. The
   root/control worktree is off-limits.
2. Locked dependency floor: `cuprum==0.1.0` (`uv.lock` line 113-118). Every
   external program — `uv` (a bare name) and the installed console-scripts (run
   by **absolute path**) — runs through a local `cuprum` `ProgramCatalogue`; no
   raw `subprocess` and no `uv run` resolution of the project environment (the
   wheel must be the freshly built one). This is exactly the discipline the
   existing installed-binary e2es already use
   (`tests/test_novel_state_check.py` lines 304-371; ADR-006 "Decision outcome";
   `docs/scripting-standards.md`).
3. The installed-binary e2es are POSIX-only (ADR-006). Each new test keeps the
   `@pytest.mark.skipif(os.name != "posix", …)` guard (or inherits the
   module-level `pytestmark`) whose reason names ADR-006, and resolves the
   venv-scripts directory through the `venv_scripts_dir` fixture
   (`tests/conftest.py` lines 270-294), never a hand-rolled platform branch.
4. The exit-code semantics are fixed policy (design §3.2 table; ADR-003 Table
   2):
   0 success / mutator applied; 3 state-or-input error (missing/unparseable
   `state.toml`, absent working dir). A mutator that refuses an invalid request
   exits 3, never 1 (design §3.2 "A mutator that refuses an invalid request").
   The plan must assert exactly these codes; it must not relabel them.
5. Do not weaken or alter the existing in-process recount/check coverage. The
   new e2es are *additive* installed-binary proofs; the in-process tests
   (`tests/test_recount_e2e.py`, `tests/test_recount_unit.py`,
   `tests/test_novel_state_check.py`) remain.
6. The shared-test-scaffolding rule (developers-guide "Shared test
   scaffolding", lines 31-51): test modules consume helpers by **fixture
   name**, never by importing a helper *value* from another test module or from
   `conftest`. The one carve-out is a `TYPE_CHECKING`-only type import. New
   shared scaffolding belongs in `tests/conftest.py` as a fixture.
7. Slow installed-binary e2es carry `@pytest.mark.slow` and an explicit
   `@pytest.mark.timeout(180)` that supersedes the 30 s project default
   (`pyproject.toml` line 326 `timeout = 30`; marker declared line 328),
   exactly as the existing installed e2es do.
8. AGENTS.md quality gates (`make all`, plus `make markdownlint` and
   `make nixie` for any Markdown change) must pass before each commit. en-GB
   Oxford
   spelling ("-ize"/"-yse"/"-our") in all prose, comments, and commit messages.

## Tolerances (exception triggers)

Stop and escalate (document in `Decision Log`, then await direction) when:

- Scope: implementation requires changes to more than 8 files or more than 250
  net lines of code. (The plan's own footprint is seven files:
  `tests/conftest.py`, the three test modules, and three docs; a *ninth*
  touched file means the change has grown beyond what was planned.)
- Interface: any change to a public `novel_ralph_skill` API signature, the
  envelope shape, or an exit-code value is required to make a test pass — these
  are frozen contracts; a forced change means the contract is wrong, not the
  test.
- Dependencies: any new runtime or dev dependency, or a change to the `cuprum`
  floor, is required.
- Iterations: the slow e2e still fails after 3 focused fix attempts (e.g. a
  wheel-build, venv, or cwd-resolution surprise that is not a test-logic bug).
- Behaviour fork: the installed binary's observed exit code for a state-error
  case does not match the design §3.2 expectation (e.g. it exits 1 or crashes
  with a traceback rather than exiting 3). That is a real contract defect; stop
  and surface it rather than rewriting the assertion to match.
- Helper-promotion blast radius: promoting `_build_and_install_novel_state` to a
  shared fixture forces touching more than the two consuming modules
  (`test_novel_state_check.py`, `test_reconcile_e2e.py`) plus the new test
  module — i.e. an unexpected third consumer or a Pylint/`ty` gate fights the
  fixture shape.

## Risks

- Risk: the installed `recount`, being a mutator, writes `state.toml` under the
  subprocess cwd; if the test materialises its tree under the wheel/venv
  `tmp_path` subtree, the build and the mutation could interfere. Severity:
  low. Likelihood: low. Mitigation: materialise the run tree under a per-test
  `run_dir = tmp_path / "run"` and pass it as `ExecutionContext(cwd=run_dir)`,
  exactly as `test_installed_novel_state_check_exits_zero` does (lines
  353-367). With the module-scoped fixture the wheel and venv live under
  `tmp_path_factory`'s install directory (`build_root`), an entirely separate
  tree from each test's function-scoped `tmp_path`, so the mutation cannot
  touch the install; the subtrees never overlap.
- Risk: the wheel-build/install helper `_build_and_install_novel_state` is
  currently imported cross-module by `test_reconcile_e2e.py` (line 32), which
  violates the developers-guide shared-scaffolding rule (Constraint 6). Adding
  a third such import for the new module would deepen a flagged anti-pattern.
  Severity: medium. Likelihood: high (the obvious copy-paste path reintroduces
  it). Mitigation: Work item 1 promotes the helper to a shared `conftest.py`
  fixture `installed_novel_state` and reroutes both existing consumers, so the
  new tests consume it by fixture name (Constraint 6) and the existing rule
  violation is retired in the same pass (Decision D-FIXTURE).
- Risk: an unparseable-`state.toml` e2e could accidentally assert the wrong
  surface — e.g. `recount` might reach a different exit code than `check` for a
  missing working dir because `recount` is a mutator. Severity: low.
  Likelihood: low. Mitigation: both `check` and `recount` route
  missing/unparseable state through the same `StateInputError` → exit-3 channel
  (`_recount.py` lines 43-81 and `recount()` lines 139-149;
  `_state_mutators._load_document_or_state_error`; `runner.run` lines 233-239
  emits an `ok: false` envelope and exits 3). The in-process tests already pin
  this (`test_novel_state_check.py` lines 89-114; `test_recount_unit.py` lines
  198-234). The e2e asserts `exit_code == 3` and `ok is False`, the two facts
  the harness branches on, not the message text.
- Risk: the slow e2es add wheel-build + venv + install + run cost under
  `-n auto`; a too-tight timeout could flake.
  Severity: low. Likelihood: low. Mitigation: reuse the proven
  `@pytest.mark.timeout(180)` (Constraint 7). The `installed_novel_state`
  fixture is **module-scoped** (`scope="module"`, fed by `tmp_path_factory`),
  so it builds the wheel and venv **once per consuming test module** and every
  test in that module — including the two parametrised cases of Work item 3's
  exit-3 test — reuses the one install. This is the exact shape the proven
  `installed_desloppify` fixture uses (`test_ai_isms_e2e.py` lines 152-164:
  `scope="module"`, `tmp_path_factory`, "the wheel build, venv create, and
  install … run once and every parametrised case reuses the installed script").
  Each test still materialises its own throwaway `working/` tree under a
  per-test `tmp_path`, so the cases stay independent (Decision D-CWD). Net
  wheel-build count for the whole suite becomes **three** — one per module that
  owns installed e2es: `test_novel_state_check.py` (1 installed test),
  `test_reconcile_e2e.py` (2 installed tests, now sharing 1 build), and
  `test_recount_e2e.py` (3 new installed cases — WI2's one plus WI3's two —
  sharing 1 build). Today the in-body helper builds the wheel **once per
  installed test**, so the two existing modules already pay 1 + 2 = three
  builds; the module-scoped fixture holds that flat (the reconcile module drops
  from 2 builds to 1) and the new recount module adds exactly **one**. Total is
  three, against the **six** a function-scoped fixture would cost (1 + 2 + 3).
  The saving is genuine, not framing.

## Progress

- [x] Work item 1: Promote the wheel-build/install helper to a shared fixture
      and reroute existing consumers. Landed as a registered pytest plugin
      (`tests/installed_binary_fixtures.py`) rather than directly in
      `conftest.py`: hosting the fixture in `conftest.py` pushed it to 432 lines,
      breaching the 400-line cap (AGENTS.md lines 24-27). The codebase's own
      registered-plugin pattern (the four `corpus_*_fixtures` plugins) is the
      sanctioned way to keep `conftest` under the cap while exposing a fixture by
      name to every consuming module, so the fixture lives in the new plugin and
      `conftest.py` registers it via `pytest_plugins`. See Decision D-PLUGIN.
- [x] Work item 2: Add the installed-binary `novel-state recount` exit-0 e2e.
      Added `test_installed_novel_state_recount_exits_zero` plus a shared
      `_stale_two_chapter_spec` builder and `_RECOUNTED_RESULT` oracle, and
      rerouted the existing in-process recount test onto the shared builder (the
      spec values are byte-identical, so the in-process coverage is unchanged per
      Constraint 5). CodeRabbit: 0 findings.
- [x] Work item 3: Add the installed-binary `novel-state` exit-3 state-error
      e2e. Added `test_installed_novel_state_recount_state_error_exits_three`,
      parametrised over `missing-state` and `unparseable-state`. The installed
      binary exits 3 with an `ok: false` envelope and no traceback for both
      faults — the design §3.2 contract holds (no behaviour fork). CodeRabbit: 0
      findings.
- [x] Work item 4: Documentation reconciliation (design §9 / developers-guide /
      roadmap tick). Added an "Installed-binary e2es" bullet to design §9
      recording the wheel/venv boundary coverage for `recount` and the exit-3
      path; documented the `installed_novel_state` fixture and its registered
      plugin in the developers-guide "Shared test scaffolding" section; ticked
      roadmap 6.2.4. `make markdownlint`, `make nixie`, and `make all` all green;
      CodeRabbit: 0 findings.

## Surprises & discoveries

- Observation: `tests/test_reconcile_e2e.py` line 32 already imports
  `_build_and_install_novel_state` from `test_novel_state_check.py`. Evidence:
  `grep -n "_build_and_install_novel_state" tests/test_reconcile_e2e.py`.
  Impact: the obvious "copy the helper" path is a flagged cross-module import
  (developers-guide lines 31-37). Work item 1 promotes it to a fixture, which
  both serves the new tests and retires the existing violation.
- Observation: adding the `installed_novel_state` fixture and its two helpers to
  `conftest.py` took the module from 339 to 432 lines, breaching the 400-line cap
  (AGENTS.md lines 24-27) and failing Ruff.
  Evidence: `make all` PLE/format gate; `wc -l tests/conftest.py` == 432 with the
  fixture inline.
  Impact: the fixture moved to a new registered plugin
  `tests/installed_binary_fixtures.py`, mirroring the four existing
  `corpus_*_fixtures` plugins (Decision D-PLUGIN). No behaviour change; the
  fixture is still consumed by name across all three modules.
- Observation: the fixture body initially tripped Ruff PLR0914 (too many local
  variables, 11 > 10).
  Evidence: `make all` lint gate on `tests/installed_binary_fixtures.py`.
  Impact: a `_run_ok(command)` helper folds the build/venv/install exit-code
  guards, dropping the named-result locals back under the cap.
- Observation: `runner.run` emits an `ok: false` envelope *and* exits 3 on
  `StateInputError`, so an installed-binary exit-3 run still prints a parseable
  JSON envelope on stdout. Evidence: `novel_ralph_skill/contract/runner.py`
  lines 233-239; `ok` mirrors exit 0 only (ADR-003 "ok mirrors the exit code").
  Impact: the exit-3 e2e can assert both `exit_code == 3` and the captured
  stdout JSON `ok is False`, not just the exit code.

## Decision log

- Decision: D-PLUGIN — host the `installed_novel_state` fixture in a new
  registered pytest plugin (`tests/installed_binary_fixtures.py`) rather than in
  `conftest.py` directly.
  Rationale: the plan assumed `conftest.py` could absorb the fixture, but adding
  the fixture plus its two inlined helpers took `conftest.py` from 339 to 432
  lines, breaching the 400-line module cap (AGENTS.md lines 24-27) and tripping
  Ruff. The codebase already solves exactly this tension: the corpus, live-draft,
  divergent, and done-predicate fixtures all live in registered-plugin modules
  (`tests/corpus_fixtures.py` etc.) "because the … fixture surface would push
  ``conftest.py`` past the 400-line module cap … registering it as a plugin keeps
  every fixture available by name exactly as a ``conftest`` fixture would be."
  The new plugin follows that precedent verbatim; `conftest.py` registers it in
  `pytest_plugins`. The fixture is consumed by name across all three installed-e2e
  modules, satisfying Constraint 6 identically to the conftest plan. The runtime
  cuprum imports (`sh`, `Program`) D-IMPORTS specified for `conftest.py` move to
  the plugin module instead (`conftest.py`'s function-scoped fixtures keep
  `Program` under `TYPE_CHECKING` as before). A `_run_ok` helper folds the three
  uv-step exit-code guards so the fixture body stays under the Ruff PLR0914
  local-variable cap.
  Date/Author: 2026-06-24, implementation agent.
- Decision: D-FIXTURE — promote `_build_and_install_novel_state` to a shared
  fixture `installed_novel_state` rather than adding a third cross-module import
  (hosted per D-PLUGIN in `tests/installed_binary_fixtures.py`, not
  `conftest.py`). Rationale: the developers-guide shared-scaffolding rule
  (lines 31-37) forbids importing helper *values* across test modules; a
  fixture is the sanctioned shape and retires the existing
  `test_reconcile_e2e.py` violation in the same pass. Alternative (copy the
  helper into the new module) was rejected as duplication the post-merge audits
  repeatedly flag (`conftest.py` lines 5-10). Date/Author: 2026-06-24, planning
  agent.
- Decision: D-SCOPE — `installed_novel_state` is `scope="module"`, takes
  `tmp_path_factory`, and inlines the catalogue/scripts-dir logic as two
  `conftest`-private helpers (`_one_program_catalogue`, `_venv_scripts_dir`)
  rather than requesting the function-scoped `single_program_catalogue` /
  `venv_scripts_dir` fixtures. Rationale: design-review round 1 (blocking 1)
  correctly observed that a module/session-scoped fixture that *requests* a
  function-scoped fixture raises `ScopeMismatch` at collection, so the earlier
  "function scope, widen later if a gate flags cost" escape hatch was
  mechanically impossible. The codebase already settles this exact tension:
  `test_ai_isms_e2e.py`'s module-scoped `installed_desloppify` takes
  `tmp_path_factory` and copies the catalogue and scripts-dir builders into
  module-private `_one_program_catalogue` / `_scripts_dir` functions, with a
  docstring stating "the module-scoped install fixture cannot request the
  function-scoped fixture, and the catalogue is a stateless value, so building
  it directly keeps the wheel install at module scope … without a scope clash"
  (lines 49-83). `installed_novel_state` follows that precedent verbatim, only
  it lives in `conftest.py` (so three modules share it) instead of a single
  test module. Module scope is chosen over session scope because each consuming
  module then owns an independent install (no cross-module install state) while
  still building the wheel once per module; it is the minimum scope that
  delivers the WI3 two-case reuse the Risks section claims. The function-scoped
  alternative was rejected: it would build the wheel six times across the suite
  (1 + 2 + 3) and break the reuse claim outright (blocking 2). Date/Author:
  2026-06-24, planning agent.
- Decision: D-IMPORTS — Work item 1 adds the runtime cuprum imports
  (`from cuprum import sh`; `from cuprum.program import Program` moved out of
  the `TYPE_CHECKING` block) to `conftest.py` as an explicit step before the
  fixture body, and Work item 2 adds the matching runtime imports to
  `test_recount_e2e.py`. Rationale: design-review round 2 (blocking 1) observed
  that `conftest.py` imports `Program` only under `if typ.TYPE_CHECKING:` (line
  60) and never imports `sh`; the existing function-scoped
  `single_program_catalogue` / `venv_scripts_dir` fixtures only build
  `ProgramCatalogue` / `ProjectSettings` values (runtime-imported at line 28)
  and never call `sh.make` or instantiate `Program` at runtime, so the gap is
  real and the `_one_program_catalogue(name, program: Program)` parameter
  annotation masks it (a lazy annotation string under
  `from __future__ import annotations` never forces a runtime import). The new
  fixture body calls `sh.make(...)`, `Program("uv")`, and `.run_sync(...)` at
  runtime, so without the imports an implementer following the plan verbatim
  hits `NameError: name 'Program'` / `name 'sh'` at fixture execution, or a `ty`
  /Ruff undefined-name failure under `make all`. The same class of gap exists in
  `test_recount_e2e.py`, which imports no cuprum symbol today, so WI2 lists
  the matching runtime imports for that module too. Both fixes mirror the
  proven precedent `test_ai_isms_e2e.py` (runtime imports at lines 31-32). The
  imports resolve against locked `cuprum==0.1.0` (`cuprum/__init__.py`
  re-exports `sh` at line 134 and `Program` at line 62; `sh.make` at
  `cuprum/sh.py` line 528), so no new dependency is introduced. Alternative
  (relying on the annotation or a TYPE_CHECKING import) was rejected as
  mechanically broken at runtime. Date/Author: 2026-06-24, planning agent.
- Decision: D-EXIT3-SUBJECT — drive the installed exit-3 e2e through
  `novel-state recount` (the mutator this task names) over a
  missing-or-unparseable
  `state.toml`, asserting exit 3 and `ok: false`. Rationale: the roadmap text
  names "a missing or unparseable `state.toml` through the installed binary"
  and pairs it with `recount`; `recount` routes missing/unparseable state
  through the same exit-3 channel as `check` (`_recount.py` lines 139-149).
  Driving the named mutator keeps the proof on the task's subject. The success
  criterion ("at least one exit-3 state-error path … asserted against a real
  installed console-script") is met by one such case; the plan adds the
  missing-`state.toml` case and, budget permitting, the unparseable case as a
  parametrised second. Date/Author: 2026-06-24, planning agent.
- Decision: D-CWD — every installed run uses `ExecutionContext(cwd=run_dir)`
  with a dedicated per-test `run_dir = tmp_path / "run"` holding a
  `working_dir = run_dir / "working"` tree, never the build/venv subtree (which
  lives under the module fixture's `tmp_path_factory` install directory).
  Rationale: `recount` resolves a cwd-relative `working/state.toml` and writes
  it; isolating the run tree per test mirrors the proven `check` e2e (lines
  353-367) and avoids the mutator interfering with the shared install. The names
  `run_dir`/`working_dir` are used consistently across Work items 2 and 3 and
  the Artifacts snippet so the template is copy-correct for both. Date/Author:
  2026-06-24, planning agent.

## Outcomes & retrospective

Milestone closed (2026-06-25). Against the Purpose:

- The installed `novel-state recount` is now proven at the wheel/venv boundary:
  `test_installed_novel_state_recount_exits_zero` corrects wrong counts and exits
  0 with the recounted `{current, by_chapter}` envelope, and
  `test_installed_novel_state_recount_state_error_exits_three` (parametrised over
  `missing-state` and `unparseable-state`) exits 3 with an `ok: false` envelope
  and no traceback. All three new cases pass under `make all`.
- The cross-module `_build_and_install_novel_state` import is retired; the helper
  is now the module-scoped `installed_novel_state` fixture, consumed by name by
  all three installed-e2e modules. The reconcile module dropped from two wheel
  builds to one.
- Design §9 gained an "Installed-binary e2es" bullet and the developers' guide
  documents the fixture and its plugin.

Deviations from the plan (each with rationale, recorded in the Decision Log):

- D-PLUGIN: the fixture landed in a registered plugin
  (`tests/installed_binary_fixtures.py`), not `conftest.py`, because the inline
  version breached the 400-line module cap. This is the codebase's own pattern
  for fixture surfaces that would overflow `conftest`; behaviour is identical.
- A `_run_ok` helper folds the uv-step exit-code guards to satisfy Ruff PLR0914.
- The execplan and its review artifacts were caught by an inadvertent `make fmt`
  mdformat reflow early in WI1; the spurious churn to unrelated tracked docs was
  stashed (matching the long-standing "spurious make-fmt mdformat churn" pattern
  in this repo), and the execplan's two over-width inline-code lines were
  rewrapped by hand so `make markdownlint` passes. Lesson for the next agent:
  format Python with `ruff format` directly; do **not** run `make fmt`, which
  rewrites every Markdown file in the tree.

CodeRabbit raised two findings across the run, both against the ExecPlan or its
`review-r1.md` artifact (Markdown width in the plan, and a citation nuance in the
review note). The plan's over-width lines were fixed; the `review-r1.md` citation
is a pre-existing design-review artifact left verbatim as the historical record,
not live code, so it was not rewritten. No finding touched the implementation.

## Context and orientation

The repository is a Python package, `novel_ralph_skill`, exposing five console
scripts via `[project.scripts]` (ADR-005). `novel-state` is the
multi-subcommand script; its subcommands are `init`, `check`, `set-cursor`,
`advance-phase`, `recount`, and `reconcile` (design §3.3; ADR-003). Each
command runs its Cyclopts app through the shared `run` wrapper, which owns every
`sys.exit` and envelope emission (`novel_ralph_skill/contract/runner.py`;
ADR-003 "four-flag contract").

Key terms, defined for a newcomer:

- **Installed-binary e2e**: a test that builds a wheel with `uv build --wheel`,
  installs it into a fresh `uv venv`, and runs the resulting console-script *by
  its absolute path on disk* in a subprocess, so the proof crosses the real
  packaging boundary rather than importing the entry-point function. The
  canonical example is
  `tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
  (lines 341-371).
- **Exit-3 state-or-input error**: the harness contract code for "the state is
  missing, unparseable, or otherwise unusable; stop and recover state" (design
  §3.2; ADR-003 Table 2). A mutator that refuses an incoherent request also
  exits 3, never 1 (design §3.2).
- **`recount`**: the mutator that re-derives `[word_counts].current` and
  `[word_counts].by_chapter` from the on-disk chapter drafts; it writes only
  `state.toml`, opens no `[pending_turn]` bracket, and is idempotent over
  unchanged drafts (`novel_ralph_skill/commands/_recount.py`; design §4.1).
- **`working_corpus`** (aliased `wc` in tests): the in-repo builder that
  materialises a coherent `working/` tree from a `WorkingTreeSpec` /
  `ChapterSpec` under a `tmp_path` (`tests/working_corpus/`). Tests consume it
  by direct value import (`import working_corpus as wc`), the sanctioned
  carve-out the BDD step modules use.
- **`single_program_catalogue` / `venv_scripts_dir`**: the two
  **function**-scoped
  `conftest` fixtures that build a one-program `cuprum` catalogue and resolve a
  venv's scripts directory (`tests/conftest.py` lines 238-294). Because they
  are function-scoped, a module-scoped fixture cannot request them (pytest
  raises `ScopeMismatch` at collection); the module-scoped
  `installed_novel_state` added by Work item 1 therefore inlines their *logic*
  as `conftest`-private helpers, exactly as `test_ai_isms_e2e.py`'s
  module-scoped `installed_desloppify` already does (Decision D-SCOPE).
- **`tmp_path_factory`**: pytest's built-in **session**-scoped
  temporary-directory
  factory. A module/session-scoped fixture must use it (via
  `tmp_path_factory.mktemp(...)`) rather than the function-scoped `tmp_path`,
  because `tmp_path` is always function-scoped and would raise `ScopeMismatch`.
  `installed_desloppify` uses exactly this (`test_ai_isms_e2e.py` lines
  152-164).

Files this plan touches:

- `tests/conftest.py` — add the runtime cuprum imports the new fixture needs
  (`sh`, and `Program` moved out of the `TYPE_CHECKING` block to runtime) and
  add the `installed_novel_state` fixture plus its two inlined helpers (Work
  item 1).
- `tests/test_novel_state_check.py` — reroute its
  `_build_and_install_novel_state`
  use to the fixture; keep the existing `check` e2e behaviourally identical
  (Work item 1).
- `tests/test_reconcile_e2e.py` — drop the cross-module import; consume the
  fixture (Work item 1).
- `tests/test_recount_e2e.py` — add the installed-binary recount exit-0 e2e
  (Work item 2) and the installed-binary exit-3 state-error e2e (Work item 3).
- `docs/novel-ralph-harness-design.md` §9, `docs/developers-guide.md`,
  `docs/roadmap.md` — documentation reconciliation and the roadmap tick (Work
  item 4).

Verified external-library facts the plan relies on (each pinned to source or an
existing passing test, per the research mandate):

- `cuprum==0.1.0`
  `sh.make(program, catalogue=…)(*argv).run_sync(context=…, capture=True)`
  returns a `CommandResult` with `.exit_code: int`, `.stdout: str | None`,
  `.stderr: str | None`. Verified at
  `/data/leynos/Projects/cuprum/cuprum/sh.py` `class CommandResult` (lines
  93-118) and `class ExecutionContext` with a `cwd` field (lines 168-203). The
  `cwd`-scoped installed run is already exercised by
  `test_installed_novel_state_check_exits_zero` (lines 363-368), so the surface
  is pinned by a passing test, not memory.
- `cuprum` 0.1.0 allowlists any `Program` string, including an absolute path,
  and executes it via `asyncio.create_subprocess_exec`; the catalogue
  allowlist, not the `Program` type, is the execution gate (`tests/conftest.py`
  lines 244-246; ADR-006 "Decision outcome"). No `uv run`; `uv` is a bare name
  run through its own one-program catalogue.
- `runner.run` emits an `ok: false` envelope and
  `sys.exit(ExitCode.STATE_ERROR)`
  (3) on `StateInputError` (`novel_ralph_skill/contract/runner.py` lines
  233-239); `ExitCode.STATE_ERROR == 3` (`contract/exit_codes.py` line 29). The
  in-process exit-3 paths for both `check` and `recount` are already pinned
  (`test_novel_state_check.py` lines 89-114; `test_recount_unit.py` lines
  198-234), so the e2e only has to prove the *installed binary* reproduces them.

- The runtime imports Work item 1 adds to `conftest.py` resolve against locked
  `cuprum==0.1.0`: `from cuprum import sh` is valid because
  `cuprum/__init__.py` does `from . import builders, sh` (line 77) and lists
  `"sh"` in `__all__` (line 134); `sh.make` is the public command builder
  (`cuprum/sh.py` line 528, in `sh.py`'s `__all__` line 548);
  `from cuprum.program import Program` resolves to the `Program` class
  (`cuprum/program.py`, also re-exported at `cuprum/__init__.py` line 62). The
  precedent module `test_ai_isms_e2e.py` already imports all three at runtime
  (lines 31-32), so these are pinned by an existing passing module, not by
  memory.

Because every mechanism above is either read from locked-version source or
exercised by an existing passing installed-binary test, no work item depends on
an unverified external-library behaviour; there are no undecided forks. The one
new mechanism — the module-scoped `installed_novel_state` fixture — has its
runtime import prerequisites spelled out explicitly in Work item 1 so a novice
following the plan verbatim does not hit a `NameError` at fixture execution.

## Plan of work

The work proceeds in four atomic, independently committable, gate-passable work
items, red-before-green where a new behavioural proof is added.

### Work item 1 — Promote the wheel-build/install helper to a shared fixture

Implements: developers-guide "Shared test scaffolding" (lines 31-51);
Constraint 6; Decision D-FIXTURE. Retires the `test_reconcile_e2e.py`→
`test_novel_state_check.py` cross-module import.

Docs to read first: `docs/developers-guide.md` lines 31-64 (the shared-fixture
rule and its audit lineage); `tests/conftest.py` lines 238-294 (the existing
`single_program_catalogue` and `venv_scripts_dir` fixtures this one sits
beside); `tests/test_ai_isms_e2e.py` lines 31-32 (the runtime cuprum imports
the precedent module uses —
`from cuprum import ProgramCatalogue, ProjectSettings, sh` and
`from cuprum.program import Program`), and lines 49-83 and 152-164 (the proven
module-scoped installed-binary fixture this work item mirrors, including its
two inlined catalogue/scripts-dir helpers and the docstring explaining why they
are inlined). Note `tests/conftest.py` line 28 (the current runtime
`from cuprum import ProgramCatalogue, ProjectSettings`) and line 60 (the
`TYPE_CHECKING`-only `from cuprum.program import Program`) — the gap step 1
closes.

Skills to load: `python-router` → `python-testing` (fixture **scope** rules —
in particular that a higher-scoped fixture may not request a lower-scoped one,
and the `tmp_path_factory`-versus-`tmp_path` distinction — and the
parameter-name consumption idiom).

Change: add a **module-scoped** fixture `installed_novel_state` to
`tests/conftest.py`. It must be `scope="module"` and take **only**
`tmp_path_factory: pytest.TempPathFactory` (pytest's session-scoped temp
factory) — it must **not** request `tmp_path`, `single_program_catalogue`, or
`venv_scripts_dir`, all of which are function-scoped and would raise pytest
`ScopeMismatch` at collection against a module-scoped fixture (design-review
round 1, blocking 1). This is exactly the constraint `test_ai_isms_e2e.py`'s
module-scoped `installed_desloppify` already solved (lines 152-164): it takes
`tmp_path_factory`, calls `tmp_path_factory.mktemp("…")` for its build root,
and copies the catalogue/scripts-dir builders into module-private helper
functions (`_one_program_catalogue`, `_scripts_dir`, lines 49-83) precisely
"because the module-scoped install fixture cannot request the function-scoped
fixture".

Mirror that shape in `conftest.py`:

1. **Add the runtime cuprum imports the fixture body needs.** Today
   `tests/conftest.py` imports `ProgramCatalogue, ProjectSettings` at runtime
   (line 28) but imports `Program` **only** under the `TYPE_CHECKING` guard
   (line 60) and does **not** import `sh` at all (the existing function-scoped
   `single_program_catalogue` / `venv_scripts_dir` fixtures never call
   `sh.make` or instantiate `Program` at runtime — they only build
   `ProgramCatalogue` / `ProjectSettings` values). The new
   `installed_novel_state` fixture body calls `sh.make(...)`, `Program("uv")`,
   and `.run_sync(...)` at **runtime**, so two runtime imports must be added or
   the fixture raises `NameError: name 'Program'` / `name 'sh'` at execution
   (and fails the `ty` / Ruff undefined-name gate under `make all`):
   - add `from cuprum import sh` to the runtime import block (extend the
     existing
     `from cuprum import ProgramCatalogue, ProjectSettings` on line 28 to
     `from cuprum import ProgramCatalogue, ProjectSettings, sh`, or add a
     dedicated `from cuprum import sh` line — match the precedent's
     `from cuprum import ProgramCatalogue, ProjectSettings, sh` at
     `test_ai_isms_e2e.py` line 31);
   - add a runtime `from cuprum.program import Program` (move the import out of
     the `if typ.TYPE_CHECKING:` block on line 60 so it is imported at runtime,
     mirroring `test_ai_isms_e2e.py` line 32). The `_one_program_catalogue(name,
     program: Program)` helper annotation alone is **not** sufficient: a
     parameter annotation under `from __future__ import annotations` is a lazy
     string and never forces a runtime import, which is exactly what masks the
     gap — the runtime *call* `Program("uv")` inside the fixture body is what
     needs the name bound at runtime.
   The fixture does **not** need `ExecutionContext` (it only builds and
   installs; the cwd-scoped `run_sync` with `ExecutionContext` lives in the
   WI2/WI3 test bodies, not in `conftest`), so do not add that import here.
   These are re-exports of the same locked `cuprum==0.1.0` surface the
   precedent module already imports at runtime (`from cuprum import sh` is
   valid — `cuprum/__init__.py` re-exports `sh`; `Program` lives at
   `cuprum/program.py`), so no new dependency is introduced.
2. Add two `conftest`-private module-level helper functions —
   `_one_program_catalogue(name, program)` (a verbatim copy of the
   `single_program_catalogue` fixture's inner `_build`, returning a one-project
   `ProgramCatalogue`) and `_venv_scripts_dir(venv_dir)` (a verbatim copy of the
   `venv_scripts_dir` fixture's inner `_resolve`, using the `sysconfig` "venv"
   scheme). Each carries a docstring (conftest enforces 100% `interrogate`
   coverage) noting it exists so the module-scoped fixture avoids the
   function-scoped fixture, citing the same reason `test_ai_isms_e2e.py`
   records. The function-scoped `single_program_catalogue` and
   `venv_scripts_dir` fixtures remain unchanged for their existing
   function-scoped consumers; only their *logic* is shared with the new
   helpers. (Do not refactor the existing fixtures to delegate to the helpers
   in this work item — that widens the blast radius beyond the tolerance; a
   follow-up may fold them, but it is out of scope here.)
3. Add `installed_novel_state(tmp_path_factory)` with `scope="module"`. Its body
   wraps what `_build_and_install_novel_state` does today
   (`tests/test_novel_state_check.py` lines 304-332): resolve the project root
   from `__file__`, call
   `build_root = tmp_path_factory.mktemp("novel-state-install")`, build a wheel
   with `uv build --wheel … --out-dir build_root/"wheels"` (via
   `sh.make(Program("uv"), catalogue=_one_program_catalogue("novel-state-e2e", Program("uv")))`),
   assert exactly one wheel, create a fresh `uv venv build_root/"venv"`,
   resolve its scripts dir with `_venv_scripts_dir`,
   `uv pip install --python <scripts>/python <wheel>`, assert the `novel-state`
   script exists, and **return its absolute `Path`**. Each `uv` step asserts
   `exit_code == 0` by raising `AssertionError` directly (conftest carries no
   bare-`assert` relief; developers-guide lines 53-57).

Then reroute the consumers:

- In `tests/test_novel_state_check.py`, delete `_build_and_install_novel_state`
  and rewrite `test_installed_novel_state_check_exits_zero` to take the
  `installed_novel_state` fixture (the `novel-state` script `Path`) in place of
  the local helper call; it keeps its own function-scoped
  `single_program_catalogue` for building the *run* catalogue against the
  resolved script. The observable behaviour (build → install → run `check` →
  exit 0, `ok: true`) is unchanged; this is a pure refactor.
- In `tests/test_reconcile_e2e.py`, delete the
  `from test_novel_state_check import _build_and_install_novel_state` line
  (line 32) and rewrite its **two**
  installed e2es to take the `installed_novel_state` fixture. Both now share
  the one module-scoped install (the reconcile module drops from 2 wheel builds
  to 1), and each still materialises its own throwaway `working/` tree per test.

The fixture lives in `conftest.py` (not a test module) so all three consuming
modules see it by name without a value import (Constraint 6). Module scope —
not function and not session — is deliberate: each module owns an independent
install (no cross-module install coupling) while the wheel is built once per
module, which is the minimum scope that lets WI3's two parametrised exit-3
cases share a single build (Decision D-SCOPE).

Tests added/updated: no new assertions — this work item is a refactor proven by
the *existing* installed e2es continuing to pass (`make test -m slow` for the
three affected installed tests). The structural-tripwire suite
(`tests/test_contract_app_centralisation.py`) and the fixture-name discipline
are unaffected.

Validation: `make all` (the Ruff/`ty` undefined-name gate confirms the new
runtime `sh` / `Program` imports are present — a missing import surfaces here
as an undefined-name error rather than only at fixture execution). The three
rerouted installed e2es (`test_installed_novel_state_check_exits_zero`, the two
reconcile installed e2es) still pass;
`grep -rn "_build_and_install_novel_state" tests/` returns no match (the helper
name is gone). `make markdownlint` and `make nixie` are not required (no
Markdown change in this item).

### Work item 2 — Installed-binary `novel-state recount` exit-0 e2e

Implements: roadmap 6.2.4 ("an installed-binary e2e that runs
`novel-state recount` over a built wheel and asserts the JSON envelope");
design §9 ("externally observable … command-line behaviour"); design §4.1
(`recount` semantics); ADR-003 (the envelope `result` shape); ADR-006
(POSIX-only).

Docs to read first: design §4.1 (`recount` re-derives `[word_counts]`); design
§9 (verification strategy, the installed-binary e2e expectation); the existing
in-process recount proof `tests/test_recount_e2e.py` (the
`{current, by_chapter}` envelope assertion at lines 67-69) and the
installed-`check` template `test_novel_state_check.py` lines 341-371.

Skills to load: `python-router` → `python-testing` (slow/timeout marks,
`tmp_path` isolation).

Imports to add to `tests/test_recount_e2e.py` first: the module today imports
**no** cuprum symbols (it drives `recount` in-process through
`novel_ralph_skill.commands.stub`, lines 24-25), so the new installed-binary
test needs runtime imports for the run surface, mirroring
`test_novel_state_check.py` lines 31-33: `from cuprum import sh`,
`from cuprum.program import Program`, and
`from cuprum.sh import ExecutionContext` (all runtime — the `sh.make(...)`,
`Program(...)`, and `ExecutionContext(cwd=...)` calls run at execution). Add
`from cuprum import ProgramCatalogue` under the existing
`if typ.TYPE_CHECKING:` block for the run-catalogue *annotation* only (the
value comes from the function-scoped `single_program_catalogue` fixture, so no
runtime `ProgramCatalogue` construction happens in this module — match
`test_novel_state_check.py` line 45, which imports `ProgramCatalogue` under
`TYPE_CHECKING`). Also add `import os` (for the `skipif(os.name != "posix", …)`
guard) if not already present.

Change: add `test_installed_novel_state_recount_exits_zero` to
`tests/test_recount_e2e.py`, marked
`@pytest.mark.skipif(os.name != "posix", …)` (ADR-006), `@pytest.mark.slow`,
`@pytest.mark.timeout(180)`. The test takes the function-scoped `tmp_path` (for
its own run tree), the function-scoped `single_program_catalogue` (for the
*run* catalogue against the resolved script), and the module-scoped
`installed_novel_state` fixture (the `novel-state` script `Path`). Use the
proven `check` template's directory shape verbatim so the names match the
shared Artifacts snippet (`run_dir` is the cwd; it contains `working/`):

1. `run_dir = tmp_path / "run"`; materialise the two-chapter `drafting` tree
   *under* `run_dir / "working"` with deliberately *wrong* hand-typed
   `[word_counts]` via `working_corpus`. Build the tree by pointing the
   `working_corpus` builder at `run_dir` (it creates the `working/` child),
   then the cwd is `run_dir`. Reuse the `wc.WorkingTreeSpec` shape already in
   `test_recount_e2e.py` lines 39-61: chapters drafting 3 and 5 words,
   `by_chapter_override={"01": 999, "02": 999}`, `current_words_override=1998`.
2. Build the run catalogue: `prog = Program(str(installed_novel_state))`;
   `catalogue = single_program_catalogue("novel-state-run", prog)`.
3. Run the installed script — `sh.make(prog, catalogue=catalogue)("recount")`
   with `.run_sync(context=ExecutionContext(cwd=run_dir), capture=True)` — so it
   resolves `./working/state.toml` (the cwd is `run_dir`, which holds
   `working/`).
4. Assert `result.exit_code == 0` (with `result.stderr` in the failure
   message), parse `result.stdout` as JSON, and assert the envelope `result`
   equals `{"current": 8, "by_chapter": {"01": 3, "02": 5}}` (the recounted
   counts; same oracle as the in-process test, lines 67-69) and `ok is True`.

This is a behavioural addition (red before green is satisfied by writing the
test first: it fails until the assertions are correct against the real binary;
the binary already implements `recount`, so the proof is that the *installed*
path reproduces the in-process verdict). The test asserts the JSON envelope
exactly as the roadmap success criterion requires.

Tests added: one slow installed-binary e2e (above). No snapshot is added: the
recounted-counts oracle is small and exactly asserted, which AGENTS.md prefers
over snapshot-only coverage for directly assertable logic (AGENTS.md lines
148-158). The existing in-process recount snapshot/unit/property coverage is
untouched.

Validation: `make all`. Then, to observe the new proof directly:

```bash
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-4
uv run pytest -v -m slow \
  tests/test_recount_e2e.py::test_installed_novel_state_recount_exits_zero
# expect: 1 passed
```

`make markdownlint` / `make nixie` not required (no Markdown change).

### Work item 3 — Installed-binary `novel-state` exit-3 state-error e2e

Implements: roadmap 6.2.4 ("one that drives a missing or unparseable
`state.toml` through the installed binary and asserts exit 3"); design §3.2
(exit-3 state-or-input error); design §10 ("`state.toml` unparseable … exit 3
with a message rather than a stack trace"); ADR-003 (`ok` mirrors exit 0 only);
ADR-006 (POSIX-only). Decision D-EXIT3-SUBJECT.

Docs to read first: design §3.2 (the exit-code table and the
mutator-refusal-is-3 rule); design §10 (failure modes, "`state.toml`
unparseable"); the in-process exit-3 templates `test_novel_state_check.py`
lines 89-114 (missing working dir → 3; unparseable `state.toml` → 3) and
`test_recount_unit.py` lines 198-234 (recount missing/incomplete/undecodable →
3).

Skills to load: `python-router` → `python-testing`; and `python-verification`
to confirm whether a property/parametrised matrix is warranted here — the
state-error surface is a small, enumerable boundary (missing vs unparseable),
so a `pytest.mark.parametrize` over the two fault shapes is the right tool, not
Hypothesis (the in-process property coverage already exists). Record that
verification decision in the test docstring.

Imports: this test lands in the same module as Work item 2, which already added
`from cuprum import sh`, `from cuprum.program import Program`,
`from cuprum.sh import ExecutionContext`, the `TYPE_CHECKING`
`ProgramCatalogue` annotation import, and `import os`. No further import is
needed here (WI3 commits after WI2 on the same module). If WI3 is somehow
implemented before WI2, add the same imports listed in Work item 2.

Change: add `test_installed_novel_state_recount_state_error_exits_three` to
`tests/test_recount_e2e.py`, with the same three marks (skipif-POSIX, slow,
timeout 180), parametrised over two fault shapes. As in Work item 2, the cwd is
`run_dir = tmp_path / "run"` and the state tree lives under
`working_dir = run_dir / "working"`:

- `"missing-state"`: `working_dir` is created
  (`working_dir.mkdir(parents=True)`)
  but contains **no** `state.toml`.
- `"unparseable-state"`: `working_dir` is created and
  `working_dir / "state.toml"`
  is written with invalid TOML (`b"not = toml ="`, mirroring
  `test_novel_state_check.py` line 109).

For each case the test takes the function-scoped `tmp_path` and
`single_program_catalogue`, plus the module-scoped `installed_novel_state`
fixture; builds the run catalogue (`prog = Program(str(installed_novel_state))`;
`catalogue = single_program_catalogue("novel-state-run", prog)`); runs the
installed `novel-state recount` via
`sh.make(prog, catalogue=catalogue)("recount")` with
`.run_sync(context=ExecutionContext(cwd=run_dir), capture=True)`; and asserts:

- `result.exit_code == 3` (the design §3.2 / ADR-003 state-error code; assert
  the
  integer 3, with `result.stderr` in the failure message);
- `result.stdout` parses as JSON with `ok is False` (the `runner.run`
  state-error envelope, lines 233-239);
- `"Traceback" not in (result.stderr or "")` — the design §10 promise that a
  state fault yields a message, not a stack trace.

Driving `recount` (the named mutator) over a missing/unparseable state proves
the mutator-refusal-is-3 rule at the installed boundary (Constraint 4). This
satisfies the roadmap success criterion ("at least one exit-3 state-error path
… asserted against a real installed console-script") with two cases for safety.

Tests added: one parametrised slow installed-binary e2e (two cases). No
snapshot (the asserted facts are `exit_code` and `ok`, directly assertable).

Validation: `make all`. Direct observation:

```bash
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-4
uv run pytest -v -m slow \
  "tests/test_recount_e2e.py::test_installed_novel_state_recount_state_error_exits_three"
# expect: 2 passed (missing-state, unparseable-state)
```

### Work item 4 — Documentation reconciliation and roadmap tick

Implements: AGENTS.md "Project documentation" (record behaviour-affecting and
internal-convention changes); keeps docs the source of truth.

Docs to read/update:

- `docs/novel-ralph-harness-design.md` §9: the verification-strategy prose lists
  the methods but does not yet name the installed-binary e2e coverage for
  `recount` and the exit-3 path. Add a sentence (or extend the "CLI error-path
  tests" bullet, lines 822-834) recording that `recount` and at least one
  exit-3 state-error path are now asserted against a real installed
  console-script, not only in-process — mirroring how the existing `check`
  installed e2e is treated. Keep en-GB Oxford spelling.
- `docs/developers-guide.md`: where the installed-binary e2e convention and the
  shared-fixture rule live (the section around lines 31-64 and any
  installed-console-script note near line 926), record the new
  `installed_novel_state` fixture as the sanctioned way to obtain a built-and-
  installed `novel-state` script, replacing the former cross-module helper
  import. This is the internal-convention update AGENTS.md requires.
- `docs/roadmap.md`: tick `6.2.4` to `[x]` once the e2es and docs land, leaving
  the success-criterion text intact (the criterion is now met).

Skills to load: `en-gb-oxendict` (spelling and comma discipline for the prose
edits).

Tests added: none (documentation only).

Validation: `make markdownlint` and `make nixie` (both required for Markdown
changes, per the standing rules and AGENTS.md lines 169-172), then `make all`
to confirm nothing regressed. Confirm the roadmap line 1330 checkbox reads
`[x]`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-4`.

1. Confirm the branch and a clean tree:

   ```bash
   git branch --show-current   # expect: roadmap-6-2-4
   git status --short          # expect: empty
   ```

2. Work item 1 (fixture promotion). Edit `tests/conftest.py`,
   `tests/test_novel_state_check.py`, `tests/test_reconcile_e2e.py`. Then:

   ```bash
   make all
   grep -rn "_build_and_install_novel_state" tests/   # expect: no match
   ```

   Commit (gated): `test: promote installed novel-state helper to a fixture`.

3. Work item 2 (recount exit-0 e2e). Add the test to
   `tests/test_recount_e2e.py`. Then:

   ```bash
   uv run pytest -v -m slow \
     tests/test_recount_e2e.py::test_installed_novel_state_recount_exits_zero
   make all
   ```

   Commit (gated): `test: assert installed novel-state recount exits 0`.

4. Work item 3 (exit-3 state-error e2e). Add the parametrised test to
   `tests/test_recount_e2e.py`. Then:

   ```bash
   uv run pytest -v -m slow \
     "tests/test_recount_e2e.py::test_installed_novel_state_recount_state_error_exits_three"
   make all
   ```

   Commit (gated):
   `test: assert installed novel-state recount exits 3 on bad state`.

5. Work item 4 (docs + roadmap). Edit the three docs. Then:

   ```bash
   make markdownlint
   make nixie
   make all
   ```

   Commit (gated): `docs: record installed recount and exit-3 e2e coverage`.

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- Running the new installed-binary recount e2e exits 0 and the captured JSON
  envelope's `result` is `{"current": 8, "by_chapter": {"01": 3, "02": 5}}` with
  `ok: true` — proving the *installed* `novel-state recount` reproduces the
  in-process verdict.
- Running the new installed-binary state-error e2e exits 3 with an `ok: false`
  envelope and no traceback on stderr, for both a missing and an unparseable
  `state.toml` — proving the installed binary honours the design §3.2 exit-3
  contract.
- The former cross-module helper import is gone
  (`grep -rn "_build_and_install_novel_state" tests/` is empty); both prior
  installed e2es
  for `novel-state` still pass through the shared fixture.

Quality criteria (what "done" means):

- Tests: `make test` passes, including the three new slow cases under the
  installed-binary boundary. The three rerouted installed e2es still pass.
- Lint/typecheck: `make all` passes (Ruff, Pylint, `ty`, `interrogate`, etc.).
- Docs: `make markdownlint` and `make nixie` pass after the Work item 4 edits.

Quality method (how we check): `make all` (the AGENTS.md aggregate gate), plus
`make markdownlint` and `make nixie` for the Markdown changes, run sequentially
(never in parallel — shared build cache; AGENTS.md / global instructions).

## Idempotence and recovery

Every step is re-runnable: the e2es build the wheel and venv under a fresh
`tmp_path` each run and leave no repo-tracked artefact. If a slow e2e fails on
a wheel-build or venv surprise (not a test-logic bug), re-run the single test
by node id; the `tmp_path` is rebuilt clean each time. The doc edits are plain
text and re-applying them is harmless. No destructive step exists; no rollback
plan is needed beyond `git restore` on an unstaged edit.

## Artifacts and notes

Reference template for the installed-binary run (from the proven `check` e2e,
`tests/test_novel_state_check.py` lines 363-368), the shape both new tests
follow. `installed_novel_state` is the module-scoped fixture's returned script
`Path`; `run_dir` is the per-test cwd (a function-scoped `tmp_path / "run"`
that holds the `working/` tree):

```python
prog = Program(str(installed_novel_state))
catalogue = single_program_catalogue("novel-state-run", prog)
result = sh.make(prog, catalogue=catalogue)("recount").run_sync(
    context=ExecutionContext(cwd=run_dir), capture=True
)
assert result.exit_code == 0, result.stderr
envelope = json.loads(result.stdout or "{}")
```

Reference template for the module-scoped install fixture (mirroring
`tests/test_ai_isms_e2e.py` lines 49-83 and 152-164), the shape Work item 1
adds to `tests/conftest.py`:

```python
# Runtime imports this template requires in conftest.py (Work item 1, step 1):
#   from cuprum import ProgramCatalogue, ProjectSettings, sh  # extend line 28
#   from cuprum.program import Program                        # move out of TYPE_CHECKING
# `Program` must be a *runtime* import (not TYPE_CHECKING-only) because the
# fixture body calls `Program("uv")`; the parameter annotation below does not
# force a runtime import under `from __future__ import annotations`.


def _one_program_catalogue(name: str, program: Program) -> ProgramCatalogue:
    """One-project cuprum catalogue; inlined so the module-scoped fixture
    avoids the function-scoped ``single_program_catalogue``."""
    return ProgramCatalogue(projects=(ProjectSettings(
        name=name, programs=(program,),
        documentation_locations=(), noise_rules=()),))


def _venv_scripts_dir(venv_dir: Path) -> Path:
    """Venv scripts dir; inlined for the same scope reason (POSIX, ADR-006)."""
    return Path(sysconfig.get_path(
        "scripts", "venv",
        vars={"base": str(venv_dir), "platbase": str(venv_dir)}))


@pytest.fixture(scope="module")
def installed_novel_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel, install it into a fresh venv once per module, and return
    the installed ``novel-state`` script path."""
    build_root = tmp_path_factory.mktemp("novel-state-install")
    # build wheel, uv venv, uv pip install via _one_program_catalogue / _venv_scripts_dir;
    # assert each uv step exits 0 (raise AssertionError directly); return the script Path.
```

## Interfaces and dependencies

- `tests/conftest.py` runtime import changes (Work item 1, step 1) — required so
  the fixture body's `sh.make(...)`, `Program("uv")` and `.run_sync(...)` calls
  resolve at runtime rather than raising `NameError` / failing the `ty`/Ruff
  undefined-name gate:

  ```python
  # before: from cuprum import ProgramCatalogue, ProjectSettings   (line 28)
  #         + Program only under `if typ.TYPE_CHECKING:`            (line 60)
  # after (runtime):
  from cuprum import ProgramCatalogue, ProjectSettings, sh
  from cuprum.program import Program  # moved out of the TYPE_CHECKING block
  ```

  `ExecutionContext` is **not** added to `conftest.py` (the fixture only builds
  and installs); the cwd-scoped `run_sync` lives in the WI2/WI3 test bodies.

- New `tests/conftest.py` **module-scoped** fixture and its two inlined helpers:

  ```python
  def _one_program_catalogue(name: str, program: Program) -> ProgramCatalogue: ...
  def _venv_scripts_dir(venv_dir: Path) -> Path: ...

  @pytest.fixture(scope="module")
  def installed_novel_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
      """Build a wheel, install it into a fresh venv once per module, return
      the installed novel-state script path."""
  ```

  The fixture is `scope="module"` and depends **only** on the session-scoped
  `tmp_path_factory`; it must not request the function-scoped `tmp_path`,
  `single_program_catalogue`, or `venv_scripts_dir` (that would raise pytest
  `ScopeMismatch`). The two helpers inline the catalogue and scripts-dir logic
  so the fixture needs neither function-scoped fixture, exactly as
  `test_ai_isms_e2e.py`'s `installed_desloppify` does (Decision D-SCOPE).
  Consumers: `tests/test_novel_state_check.py`, `tests/test_reconcile_e2e.py`,
  `tests/test_recount_e2e.py` — all by parameter name, never by value import.
  The existing function-scoped `single_program_catalogue` / `venv_scripts_dir`
  fixtures are unchanged; the new tests still take `single_program_catalogue`
  function-scoped to build their *run* catalogue against the resolved script.

- `cuprum==0.1.0` (locked): `sh.make`, `Program`, `ProgramCatalogue`,
  `ProjectSettings`, `ExecutionContext`, `CommandResult` — all already used by
  the existing e2es; no new dependency, no version change.

- `tests/test_recount_e2e.py` runtime import changes (Work item 2) — the module
  imports no cuprum symbols today (it drives `recount` in-process via
  `novel_ralph_skill.commands.stub`), so the installed-binary tests add,
  mirroring `test_novel_state_check.py` lines 31-33 and 45: runtime
  `from cuprum import sh`, `from cuprum.program import Program`,
  `from cuprum.sh import ExecutionContext`, `import os`; and a
  `TYPE_CHECKING`-only `from cuprum import ProgramCatalogue` (annotation only —
  the value comes from the `single_program_catalogue` fixture).

- `working_corpus` (in-repo test builder): `WorkingTreeSpec`, `ChapterSpec`,
  `PHASE_ORDER`, `build_working_tree` — consumed by direct value import as the
  BDD step modules already do.

## Revision note

Initial draft (2026-06-24). Decomposes roadmap 6.2.4 into four atomic work
items: (1) promote the wheel-build/install helper to a shared `conftest`
fixture and retire the existing cross-module import; (2) add the
installed-binary `novel-state recount` exit-0 e2e asserting the recounted
envelope; (3) add the installed-binary exit-3 state-error e2e (parametrised
over missing and unparseable `state.toml`); (4) reconcile design §9, the
developers' guide, and the roadmap tick. Every external mechanism is pinned to
locked `cuprum==0.1.0` source or to an existing passing installed-binary test,
so no work item rests on an unverified library behaviour. Status remains DRAFT
pending approval.

Revision 2 (2026-06-24) — design-review round 1 response. What changed:

1. **Fixture scope fixed (blocking 1).** `installed_novel_state` is now declared
   **`scope="module"`** and depends **only** on the session-scoped
   `tmp_path_factory`. The earlier draft made it depend on the function-scoped
   `tmp_path`, `single_program_catalogue`, and `venv_scripts_dir`, then offered
   a "widen to session later" escape hatch that is mechanically impossible (a
   higher-scoped fixture requesting a function-scoped one raises pytest
   `ScopeMismatch` at collection). The catalogue and scripts-dir logic are now
   inlined as two `conftest`-private helpers (`_one_program_catalogue`,
   `_venv_scripts_dir`), exactly as the codebase's own module-scoped
   `installed_desloppify` already does (`test_ai_isms_e2e.py` lines 49-83,
   152-164). New Decision D-SCOPE records this. Updated: Work item 1, the
   Interfaces signature, the Context fixture notes, and the new Artifacts
   fixture template.
2. **Reuse claim made true (blocking 2).** The Risks mitigation no longer
   promises wheel reuse a function-scoped fixture could not deliver. Module
   scope builds the wheel once per consuming module, so Work item 3's two
   parametrised exit-3 cases now genuinely share one install. The corrected
   net-cost arithmetic (three wheel builds total, versus six for a
   function-scoped fixture, and the reconcile module dropping from two builds
   to one) is stated with the per-module test counts verified against the
   source.
3. **cwd-naming normalised (advisory).** Work items 2 and 3 and the Artifacts
   run-snippet now use one consistent shape — `run_dir = tmp_path / "run"` as
   the cwd, `working_dir = run_dir / "working"` for the state tree — matching
   the proven `check` template, so the shared snippet is copy-correct for both
   work items (the previous draft used `dest` for two different directory
   levels).
4. **Tolerance file-count widened** from 6 to 8 to fit the plan's own seven-file
   footprint without a spurious immediate breach.

Status remains DRAFT pending approval.

Revision 3 (2026-06-24) — design-review round 2 response. What changed:

1. **Runtime cuprum imports for the new fixture made explicit (blocking 1).**
   Round 2 correctly observed that `tests/conftest.py` imports `Program` only
   under `if typ.TYPE_CHECKING:` (line 60) and never imports `sh`; the existing
   function-scoped fixtures only build `ProgramCatalogue` / `ProjectSettings`
   values (runtime-imported at line 28) and never call `sh.make` or instantiate
   `Program` at runtime, while the
   `_one_program_catalogue(name, program: Program)` annotation masks the gap (a
   lazy annotation under `from __future__ import annotations` never forces a
   runtime import). The new `installed_novel_state` fixture body calls
   `sh.make(...)`, `Program("uv")`, and `.run_sync(...)` at runtime, so
   following the plan verbatim would raise `NameError` at fixture execution or
   fail the `ty`/Ruff undefined-name gate. Work item 1 now opens with an
   explicit step 1 (renumbering the helpers to step 2 and the fixture to step
   3) that adds `from cuprum import sh` to the runtime block and moves
   `from cuprum.program import Program` out of the `TYPE_CHECKING` guard,
   citing the precedent `test_ai_isms_e2e.py` lines 31-32. The Context "Files
   this plan touches" bullet, the verified-external-facts block (now pinning
   `from cuprum import sh` and `Program` against `cuprum/__init__.py` lines
   62/77/134 and `cuprum/sh.py` line 528), the Artifacts fixture template (a
   leading import comment), and the Interfaces section (a new conftest-import
   sub-bullet) all list this import change. New Decision D-IMPORTS records it.
2. **Same gap closed for the test module (completeness).** `test_recount_e2e.py`
   imports no cuprum symbol today (it drives `recount` in-process via `stub`),
   so Work item 2 now lists the runtime imports its installed-binary test needs
   (`from cuprum import sh`, `from cuprum.program import Program`,
   `from cuprum.sh import ExecutionContext`, `import os`, and a `TYPE_CHECKING`
   `ProgramCatalogue` annotation import), mirroring `test_novel_state_check.py`
   lines 31-33 and 45; Work item 3 notes it reuses WI2's imports on the same
   module. A matching Interfaces sub-bullet records it.

Status remains DRAFT pending approval.
