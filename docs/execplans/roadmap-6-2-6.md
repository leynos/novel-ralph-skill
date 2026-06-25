# Extend the installed-binary exit-3 coverage to `reconcile` and `wordcount`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

Today only `novel-state recount` proves its exit-3 (state or input error) path
against a real installed console-script over a built wheel. Roadmap task 6.2.4
added that proof but left `novel-state reconcile` and the `wordcount`
console-script with only happy-path installed proofs, even though both share the
same `./working/state.toml` input boundary and the same exit-3 contract
(`docs/novel-ralph-harness-design.md` §3.2; `docs/adr-003-shared-interface-contract.md`
Table 2). The harness branches on the *installed* exit code for every command,
so this asymmetry is a real gap in the packaging boundary the unattended gate
trusts (`docs/issues/audit-6.2.4.md` Finding 6).

After this change a developer can run the test suite and observe two new
`@slow` installed-binary e2e proofs:

- the installed `novel-state reconcile`, run over a freshly built wheel against
  a `working/` directory with a missing or unparseable `state.toml`, exits `3`
  with
  an `ok: false` JSON envelope and no traceback on stderr; and
- the installed `wordcount` console-script, run the same way, exits `3` with an
  `ok: false` envelope and no traceback.

Both mirror the existing
`test_installed_novel_state_recount_state_error_exits_three`
(`tests/test_recount_e2e.py:150`). Success is the disappearance of the installed
exit-3 asymmetry: each of `recount`, `reconcile`, and `wordcount` now asserts
exit `3` on a bad `state.toml` against a real installed console-script, not only
in-process.

This is purely additive test work. No production code changes, no public
interface changes, and no changes to any source-of-truth document.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No production-code change.** This task adds installed-binary e2e tests only.
  The package under `novel_ralph_skill/` and the `skill/` tree must not be
  modified. If a test cannot pass without a production change, the in-process
  behaviour it depends on is already proven (`tests/test_wordcount_command.py`
  exit-3 cases; the in-process reconcile suite), so a failure means the test is
  wrong, not the product — stop and escalate rather than editing the product.
- **No new dependencies.** Use only the locked toolchain: `cuprum==0.1.0`
  (verified in `uv.lock:113-118`), `pytest`, `pytest-timeout`, `working_corpus`
  (the in-tree `tests/working_corpus/` helper), and the existing fixtures.
- **Locked cuprum API only.** Every cuprum call must be one the locked
  `cuprum==0.1.0` genuinely supports (see "Interfaces and dependencies"). All
  signatures below were re-derived against the locked 0.1.0 wheel itself
  (`uv.lock:113-118`, sha256 `b03e813…c984c3e72`; unpacked sources verified at
  `cuprum/program.py`, `cuprum/catalogue.py`, `cuprum/sh.py` of that wheel — NOT
  the post-0.1.0 sibling checkout at `/data/leynos/Projects/cuprum`, whose run
  API has diverged): `Program` is `typ.NewType("Program", str)`
  (`cuprum/program.py:15`), so `Program(str(absolute_path))` is the supported
  way to name an absolute-path executable; `ProgramCatalogue(projects=(...,))`
  built from `ProjectSettings(name, programs, documentation_locations,
  noise_rules)` is the allowlist (`cuprum/catalogue.py:56` and `:30`);
  `sh.make(program, catalogue=...)` raises `UnknownProgramError` on an
  unregistered program via `catalogue.lookup` (`cuprum/catalogue.py:76`,
  `raise` at `:82`); `run_sync(*, capture=True, echo=False,
  context=ExecutionContext(cwd=...)) -> CommandResult` (`cuprum/sh.py:450`)
  returns a `CommandResult` (`cuprum/sh.py:89`) whose `exit_code`, `stdout`, and
  `stderr` fields are the only ones read. `ExecutionContext` (with its `cwd`
  field) is at `cuprum/sh.py:165`.
- **POSIX-only e2e policy.** Console-script e2es are skipped off POSIX with
  `@pytest.mark.skipif(os.name != "posix", reason="console-script e2e is
  POSIX-only; see ADR 006")`, exactly as every existing installed e2e does
  (`docs/adr-006-console-scripts-e2e-posix-policy.md`).
- **`@slow` and explicit timeout.** Each installed e2e carries
  `@pytest.mark.slow` and `@pytest.mark.timeout(180)`; the 180-second per-test
  timeout supersedes the 30-second project default because the wheel build is the
  slow part (`docs/novel-ralph-harness-design.md` §9).
- **Module and bare-`assert` policy.** Files under `PYTHON_TARGETS` (the package
  and `conftest.py` / `tests/installed_binary_fixtures.py`) must raise
  `AssertionError` directly and stay under the 400-line module cap (`AGENTS.md`
  lines 24-27, 132-148 of `docs/issues/audit-6.2.4.md`). The `tests/test_*.py`
  e2e modules carry `per-file-ignores` relief and may use bare `assert`, as the
  existing recount/reconcile/wordcount e2es do. New test bodies live in
  `tests/test_*.py`, so bare `assert` is permitted and consistent with their
  neighbours.
- **British English, Oxford spelling.** All prose, docstrings, comments, and the
  commit message follow en-GB Oxford spelling (`-ize`, `-yse`, `-our`), per the
  `en-gb-oxendict` skill and `AGENTS.md`.

## Tolerances (exception triggers)

- **Scope.** If the change requires touching more than 3 files or more than
  roughly 120 net lines, stop and escalate. The expected footprint is two test
  files (`tests/test_reconcile_e2e.py`, `tests/test_wordcount_e2e.py`) plus this
  execplan.
- **Production code.** If any file under `novel_ralph_skill/` or `skill/` must
  change for a test to pass, stop and escalate (it would mean an undiscovered
  product defect, not a test gap).
- **Interface.** If a public API signature (a console-script entry point, an
  envelope field, an exit code) must change, stop and escalate.
- **Dependencies.** If a new external dependency or a cuprum API absent from
  `cuprum==0.1.0` is required, stop and escalate.
- **Iterations.** If `make test` still fails for the new tests after 3 focused
  fix attempts, stop and escalate with the captured output.
- **Fixture-scope clash.** If reusing the module-scoped `installed_novel_state`
  fixture or the function-scoped `wordcount` build helper raises a pytest
  `ScopeMismatch`, stop and escalate rather than copying fixture bodies across
  modules (the developers-guide "Shared test scaffolding" rule forbids that).

## Risks

- Risk: the `wordcount` e2e module uses a *function-scoped* build helper
  (`_build_and_install_wordcount`, `tests/test_wordcount_e2e.py:42`) rather than
  the module-scoped `installed_novel_state` fixture, so a naive
  copy of the recount proof (which depends on `installed_novel_state`) would not
  apply to `wordcount`.
  Severity: medium
  Likelihood: medium
  Mitigation: Work Item 2 reuses the module's own `_build_and_install_wordcount`
  helper, building the wheel once and parametrising the exit-3 cases off that one
  install, mirroring how `test_installed_wordcount_reports_gate_triggers` already
  calls the helper. No cross-module fixture import.

- Risk: a `working/` directory containing a `state.toml` but no `manuscript/`
  tree might exit on a code other than 3 (for example a different state fault),
  weakening the proof.
  Severity: low
  Likelihood: low
  Mitigation: the two fault shapes are exactly those the recount proof and the
  in-process `wordcount` exit-3 tests already use and that exit 3:
  `working/` present with no `state.toml` (`missing-state`), and `working/state.toml`
  holding invalid TOML (`unparseable-state`). The in-process
  `test_unparseable_state_exits_three` and `test_absent_working_dir_exits_three`
  (`tests/test_wordcount_command.py:98,110`) confirm both shapes reach exit 3, so
  the installed proof asserts the same boundary the in-process suite pins.

- Risk: building the wheel twice (once per new test module run) makes the suite
  noticeably slower.
  Severity: low
  Likelihood: high
  Mitigation: `reconcile` reuses the existing module-scoped `installed_novel_state`
  fixture, so its module builds the wheel exactly once regardless of how many
  cases run; `wordcount`'s function-scoped helper already rebuilds per test, so
  Work Item 2 keeps that module's existing scope convention rather than widening
  scope here (the scope consolidation is audit Finding 1/4 work, out of scope for
  6.2.6). The 180s timeout accommodates the build.

- Risk: a future reader cannot tell why `reconcile` uses a fixture but
  `wordcount` uses a helper.
  Severity: low
  Likelihood: medium
  Mitigation: each new test's docstring names the build mechanism it reuses and
  why (the `novel-state` fixture vs. the `wordcount` helper), and the Decision Log
  records the asymmetry as a deliberate match to each module's existing
  convention.

## Progress

- [x] (done) Work Item 1: add the installed `reconcile` exit-3 e2e to
  `tests/test_reconcile_e2e.py`. Added
  `test_installed_novel_state_reconcile_state_error_exits_three`, parametrised
  over `missing-state`/`unparseable-state`, mirroring the recount proof. Both
  cases pass; flipping the asserted exit code to `0` makes both fail, proving the
  assertion is load-bearing. `make all` green at this point.
- [x] (done) Work Item 2: add the installed `wordcount` exit-3 e2e to
  `tests/test_wordcount_e2e.py`. Added
  `test_installed_wordcount_state_error_exits_three`, parametrised over
  `missing-state`/`unparseable-state`, invoking the installed `wordcount` with
  the empty call `()` (no subcommand) and reusing the module's function-scoped
  `_build_and_install_wordcount` helper. Both cases pass; flipping the asserted
  exit code to `0` makes both fail, proving the assertion is load-bearing. `make
  all` green (913 passed, 1 skipped).
- [x] (done) Final validation: `make all` green at both work-item commits; each
  new test fails when its asserted exit code is flipped from `3` and passes when
  restored. The installed exit-3 asymmetry audit Finding 6 named is closed:
  `recount`, `reconcile`, and `wordcount` now each assert installed exit-3 on a
  bad `state.toml`.

## Surprises & discoveries

- Observation: `wordcount` is its own top-level console-script invoked with no
  subcommand (`sh.make(prog, catalogue=catalogue)()`), whereas `reconcile` is a
  `novel-state` subcommand (`...("reconcile")`).
  Evidence: `tests/test_wordcount_e2e.py:100` calls the program with no arguments;
  `tests/test_reconcile_e2e.py:218` calls `("reconcile")`.
  Impact: the two work items differ in the invocation shape and the build
  mechanism (function-scoped helper for `wordcount`, module-scoped fixture for
  `reconcile`). Captured upfront so the implementer does not conflate them.

## Decision log

- Decision: mirror `test_installed_novel_state_recount_state_error_exits_three`
  (`tests/test_recount_e2e.py:150`) rather than invent a new e2e shape.
  Rationale: the roadmap task and audit Finding 6 both say "mirroring the
  `recount` proof 6.2.4 added"; reusing the proven shape (two parametrised fault
  cases, assert exit 3 + `ok: false` + no traceback) keeps the surface uniform and
  the diff minimal.
  Date/Author: 2026-06-25, planning agent.

- Decision: `reconcile` uses the existing module-scoped `installed_novel_state`
  fixture; `wordcount` uses its own function-scoped `_build_and_install_wordcount`
  helper.
  Rationale: each module already adopts that mechanism for its happy-path
  installed proof; matching it keeps each module internally consistent and avoids
  a cross-module fixture import (forbidden by the developers-guide "Shared test
  scaffolding" rule). Consolidating the two mechanisms is audit Finding 1/4 work,
  explicitly out of scope for 6.2.6.
  Date/Author: 2026-06-25, planning agent.

- Decision: assert exit `3`, `ok: false`, and absence of `"Traceback"` on stderr;
  do not assert a specific message string.
  Rationale: design §10 requires a message rather than a stack trace, and the
  recount proof pins exactly this triple; pinning a message string would couple
  the test to wording the contract does not fix.
  Date/Author: 2026-06-25, planning agent.

- Decision: action the two minor coderabbit findings raised on the Work Item 1
  commit before committing — convert the execplan's prose verb/adjective forms
  `parametrized`/`parametrizes` to en-GB `parametrised`/`parametrises` (the
  literal `@pytest.mark.parametrize` decorator name stays unchanged), and rewrite
  the first-person narration in `roadmap-6-2-6.review-r2.md` into impersonal
  form.
  Rationale: both are en-GB / docs-style requirements under `AGENTS.md` and the
  `en-gb-oxendict` skill; the review artefacts are tracked and committed with the
  task, so the style rule applies to them too. No test code changed.
  Date/Author: 2026-06-25, implementation agent.

## Outcomes & retrospective

Done. Both work items landed as atomic commits, each gated on `make all`:

- Work Item 1 added
  `test_installed_novel_state_reconcile_state_error_exits_three`
  (`tests/test_reconcile_e2e.py`), and Work Item 2 added
  `test_installed_wordcount_state_error_exits_three`
  (`tests/test_wordcount_e2e.py`), each parametrised over the `missing-state`
  and `unparseable-state` fault shapes.
- The purpose is met: each of `recount`, `reconcile`, and `wordcount` now
  asserts installed exit-3 on a bad `state.toml` against a real wheel/venv, not
  only in-process, closing the asymmetry audit Finding 6 named.
- Footprint stayed within tolerance: two test files plus this execplan and its
  review notes; no production-code, interface, or dependency change.
- `reconcile` reused the module-scoped `installed_novel_state` fixture (one wheel
  build per module); `wordcount` reused its function-scoped
  `_build_and_install_wordcount` helper and the empty-call `()` invocation, as
  each module's existing convention dictated.
- Coderabbit raised two minor en-GB / docs-style findings on the Work Item 1
  pass (US `parametrized`/`parametrizes` prose forms in this execplan; first-
  person narration in `roadmap-6-2-6.review-r2.md`); both were actioned before
  the commit landed.

## Context and orientation

The repository is a Python skill harness. The package lives in
`novel_ralph_skill/`; tests live in the top-level `tests/` tree (`AGENTS.md` line
145). Five console-scripts are distributed in the wheel: `novel-state` (with
subcommands `check`, `recount`, `reconcile`, `set-cursor`, `advance-phase`,
`init`), `novel-compile`, `novel-done`, `wordcount`, and `desloppify`
(`docs/adr-005-command-surface-five-scripts.md`).

Key terms:

- **Installed-binary e2e.** A test that builds a wheel with
  `uv build --wheel`, installs it into a throwaway `uv venv`, and runs the
  resulting console-script *by its absolute path* through a cuprum catalogue that
  allowlists that exact path. This proves the exit-code contract at the real
  packaging boundary, not merely against the in-process entry-point body, because
  the harness branches on the exit code of the *installed* script
  (`docs/novel-ralph-harness-design.md` §9;
  `docs/adr-006-console-scripts-e2e-posix-policy.md`).
- **Exit-3 (state or input error).** The contract code for "state or input
  error; stop and recover state" — a missing or unparseable `state.toml`, or an
  absent working directory (`docs/novel-ralph-harness-design.md` §3.2 Table;
  `docs/adr-003-shared-interface-contract.md` Table 2, row 3). A mutator that
  refuses an incoherent request exits 3, never 1 (design §3.2).
- **Envelope.** The single JSON object every command emits in machine mode, with
  an `ok` field mirroring the exit code (`ok` is true only on exit 0) and a
  `result` payload (`docs/adr-003-shared-interface-contract.md` §"Decision",
  `ok` row).
- **`working_corpus` (alias `wc`).** The in-tree test helper
  (`tests/working_corpus/`) that materialises a `working/` tree from a
  `WorkingTreeSpec`; `wc.build_working_tree(spec, dest)` returns the `working/`
  path. `wc.COHERENT_BASELINE` and `wc.INCOHERENT_VARIANTS` are reusable specs.

Files this plan touches:

- `tests/test_reconcile_e2e.py` — the `novel-state reconcile` e2es. It already
  imports `cuprum.sh`, `cuprum.program.Program`, `cuprum.sh.ExecutionContext`,
  `working_corpus as wc`, and the `os`/`json`/`typ` stdlib, and reuses the
  module-scoped `installed_novel_state` fixture and the function-scoped
  `single_program_catalogue` fixture (its two existing installed e2es,
  `tests/test_reconcile_e2e.py:194,243`). Work Item 1 adds one parametrised
  test here.
- `tests/test_wordcount_e2e.py` — the `wordcount` e2e. It builds the wheel with
  its own `_build_and_install_wordcount` helper (`:42`) and reuses
  `single_program_catalogue` and `venv_scripts_dir`. Work Item 2 adds one
  parametrised test here.

Reference model (do not modify, only mirror):
`tests/test_recount_e2e.py:139-186`
(`test_installed_novel_state_recount_state_error_exits_three`) — the canonical
two-case installed exit-3 proof. It parametrises
`state_bytes` over `[None, b"not = toml ="]` with ids `["missing-state",
"unparseable-state"]`, creates `run_dir/working/`, writes the bad bytes when not
`None`, runs the installed program with `ExecutionContext(cwd=run_dir)`, and
asserts `exit_code == 3`, `json.loads(stdout)["ok"] is False`, and `"Traceback"
not in stderr`.

In-process proofs already in place (so the installed proofs only re-assert the
boundary at the packaging layer, never establishing new product behaviour):
`tests/test_wordcount_command.py:98-122` (absent `working/` and unparseable
`state.toml` each exit 3); the in-process reconcile suite drives the same input
boundary.

## Plan of work

Two stages, each one atomic, independently committable, and gate-passable.

- Stage A (Work Item 1): add the installed `reconcile` exit-3 e2e.
- Stage B (Work Item 2): add the installed `wordcount` exit-3 e2e.

Each stage ends with `make all` green. Do not proceed to Stage B if Stage A's
validation fails.

### Work Item 1: installed `reconcile` exit-3 e2e

Implements: `docs/novel-ralph-harness-design.md` §9 (installed-binary e2es prove
the exit-code contract at the packaging boundary) and §3.2 (mutator-refusal-is-3;
state-or-input-error exits 3); `docs/adr-003-shared-interface-contract.md` Table
2 row 3; `docs/issues/audit-6.2.4.md` Finding 6; roadmap task 6.2.6.

Docs to read first: `docs/novel-ralph-harness-design.md` §3.2 and §9; §10
(failure modes — a state fault yields a message, not a stack trace);
`docs/adr-003-shared-interface-contract.md` (envelope `ok` row, Table 2);
`docs/adr-006-console-scripts-e2e-posix-policy.md` (POSIX-only e2e policy);
`docs/developers-guide.md` "Shared test scaffolding" (no cross-module fixture
copies); `AGENTS.md` "Python verification and testing".

Skills to load: `python-router` (route to the smaller skills), then
`python-testing` (parametrize, marks, fixture scope, e2e boundary). No
property/symbolic adversary is warranted — see "Tests this work item adds".

Edit `tests/test_reconcile_e2e.py`. Add one new test function,
`test_installed_novel_state_reconcile_state_error_exits_three`, after the two
existing installed e2es. Decorate it with the same four markers the existing
installed reconcile tests carry: `@pytest.mark.skipif(os.name != "posix",
reason="console-script e2e is POSIX-only; see ADR 006")`, `@pytest.mark.slow`,
`@pytest.mark.timeout(180)`, and a
`@pytest.mark.parametrize("state_bytes", [None, b"not = toml ="],
ids=["missing-state", "unparseable-state"])`. The test takes `state_bytes: bytes
| None`, `tmp_path: Path`, `single_program_catalogue`, and `installed_novel_state`
(the module-scoped fixture the module already uses). Its body, mirroring
`tests/test_recount_e2e.py:172-185`:

1. Create `run_dir = tmp_path / "run"` and `working_dir = run_dir / "working"`;
   `working_dir.mkdir(parents=True)`.
2. When `state_bytes is not None`, write it to `working_dir / "state.toml"` with
   `write_bytes`.
3. `prog = Program(str(installed_novel_state))`;
   `catalogue = single_program_catalogue("novel-state-run", prog)` (the same
   project label the module's other installed tests use).
4. `result = sh.make(prog, catalogue=catalogue)("reconcile").run_sync(
   context=ExecutionContext(cwd=run_dir), capture=True)`.
5. Assert `result.exit_code == 3, result.stderr`;
   `json.loads(result.stdout or "{}")["ok"] is False`;
   `"Traceback" not in (result.stderr or "")`.

Give the function a docstring that: names the two fault shapes and ties them to
design §3.2 and ADR-003 Table 2; states the verification choice (a small
enumerable pair → two-case `parametrize`, not Hypothesis, since the in-process
reconcile exit-3 coverage already exists); notes the `installed_novel_state`
fixture supplies the script path (built once per module); and notes the 180s
timeout supersedes the 30s default. Use en-GB Oxford spelling.

Update the module docstring's bullet list (`tests/test_reconcile_e2e.py:1-20`) to
mention the new exit-3 installed proof alongside the existing exit-0 ones, and add
roadmap `6.2.6` to the docstring's roadmap reference line.

This stage ends with validation (see "Concrete steps").

### Work Item 2: installed `wordcount` exit-3 e2e

Implements: the same design and ADR sections as Work Item 1; roadmap task 6.2.6;
`docs/issues/audit-6.2.4.md` Finding 6. Note design §9 records that `wordcount`
"covers its own gate-boundary envelope" but the installed exit-3 path was not
yet anchored — this work item anchors it.

Docs to read first: same set as Work Item 1, plus `docs/roadmap.md` task 6.1.1
(the existing `wordcount` installed proof this sits beside).

Skills to load: `python-router`, then `python-testing`.

Edit `tests/test_wordcount_e2e.py`. Add one new test function,
`test_installed_wordcount_state_error_exits_three`, after
`test_installed_wordcount_reports_gate_triggers`. Decorate it with
`@pytest.mark.skipif(os.name != "posix", ...)`, `@pytest.mark.slow`,
`@pytest.mark.timeout(180)`, and the same `@pytest.mark.parametrize("state_bytes",
[None, b"not = toml ="], ids=["missing-state", "unparseable-state"])`. The test
takes `state_bytes: bytes | None`, `tmp_path: Path`, `single_program_catalogue`,
and `venv_scripts_dir` (the two function-scoped fixtures the module already
uses). Its body:

1. `script_path = _build_and_install_wordcount(tmp_path,
   single_program_catalogue, venv_scripts_dir)` — reuse the module's existing
   function-scoped build helper, exactly as
   `test_installed_wordcount_reports_gate_triggers` does (`:91`).
2. Create `run_dir = tmp_path / "run-state-error"` and
   `working_dir = run_dir / "working"`; `working_dir.mkdir(parents=True)`.
3. When `state_bytes is not None`, write it to `working_dir / "state.toml"`.
4. `prog = Program(str(script_path))`;
   `catalogue = single_program_catalogue("wordcount-run", prog)` (the same label
   the happy-path test uses).
5. `result = sh.make(prog, catalogue=catalogue)().run_sync(
   context=ExecutionContext(cwd=run_dir), capture=True)` — note the empty call
   `()`, because `wordcount` takes no subcommand (unlike `reconcile`).
6. Assert `result.exit_code == 3, result.stderr`;
   `json.loads(result.stdout or "{}")["ok"] is False`;
   `"Traceback" not in (result.stderr or "")`.

Docstring requirements as in Work Item 1, adapted: name the build helper (not a
fixture) and why (this module's existing convention), and state that `wordcount`
is invoked with no subcommand. Use en-GB Oxford spelling.

Update the module docstring (`tests/test_wordcount_e2e.py:1-19`) to mention the
new exit-3 installed proof and add roadmap `6.2.6` to its reference line.

This stage ends with validation.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-6`. Use the
shared Cargo/uv caches; do not create an isolated cache.

For each work item, follow red-green-refactor:

1. (Red) Before adding the test body, confirm the new test name does not yet
   exist and the suite is green. After writing the test, run the focused module
   to see it pass (the product behaviour it asserts already exists, so there is
   no pre-existing red from a missing product feature; the "red" here is the
   absence of the test, which the audit recorded). To demonstrate the test is
   load-bearing, temporarily flip the asserted exit code (for example assert
   `== 0`) and observe a failure, then restore `== 3`:

   ```bash
   # cuprum-allowlisted; runs the focused module on POSIX
   make test PYTEST_ARGS='tests/test_reconcile_e2e.py -k state_error_exits_three'
   ```

   Expected after the body is correct: `2 passed` for the two parametrised ids
   (`missing-state`, `unparseable-state`); `0 failed`.

2. (Green) Run the full gate:

   ```bash
   make all
   ```

   Expected: `build`, `check-fmt`, `lint`, `typecheck`, and `test` all succeed.
   The `test` target builds first (`Makefile:115`). On a non-POSIX host the new
   installed tests report `skipped`, not `failed`.

3. Commit the work item with a file-based commit message (never `-m`), gating on
   `make all`. Use the `commit-message` skill conventions.

Because the only markdown changed by this task is this execplan
(`docs/execplans/roadmap-6-2-6.md`) and the docstring/roadmap touch-ups are
inside `.py` files, also run the markdown gates once when this plan file or any
markdown changes (it does for the execplan itself):

```bash
make markdownlint
make nixie
```

Expected: both succeed. `make nixie` validates Mermaid diagrams only; this
execplan adds no Mermaid, so `nixie` has nothing to validate here and passes.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. On POSIX the two new tests each contribute two
  passing parametrised cases:
  `tests/test_reconcile_e2e.py::test_installed_novel_state_reconcile_state_error_exits_three[missing-state]`
  and `[unparseable-state]`, and the `wordcount` equivalents. Each fails if the
  asserted exit code is changed from `3`, proving it is load-bearing.
- Lint/typecheck: `make lint` and `make typecheck` pass; the new test bodies
  satisfy `ruff` and `ty` (`make typecheck` runs `ty check $(PYTHON_TARGETS)`,
  `Makefile:100`, `AGENTS.md:89`) under the existing `tests/` `per-file-ignores`.
- Markdown: `make markdownlint` and `make nixie` pass over this execplan.
- Performance: each installed test stays within the 180s per-test timeout. No
  new wheel build beyond the one the existing module mechanism already performs
  (module-scoped fixture for `reconcile`; per-test helper for `wordcount`, as
  before).
- Security: no new dependency; cuprum's catalogue allowlist still gates every
  subprocess (the program is run only because the catalogue registers its exact
  absolute path).

Quality method (how we check):

- `make all` from the worktree root; the new tests fail before their bodies exist
  (or when the asserted exit code is flipped) and pass after.
- Acceptance, phrased as behaviour: running the installed `novel-state reconcile`
  over a `working/` directory whose `state.toml` is missing or unparseable exits
  `3` and emits `{"ok": false, ...}` on stdout with no `Traceback` on stderr; the
  installed `wordcount` console-script does the same. Each is observed against a
  real wheel installed into a fresh venv, not only in-process.

## Idempotence and recovery

The work is additive and re-runnable. Each test materialises its own throwaway
`working/` tree under a per-test `tmp_path`, so cases are independent and leave
no state behind. `tmp_path` and the `uv venv` are cleaned by pytest. If a
stage's
`make all` fails, fix the new test in place and re-run; nothing is destructive.
Re-running the suite rebuilds the wheel cleanly. There is no migration, no schema
change, and no rollback path needed.

## Artifacts and notes

Reference proof shape mirrored, from `tests/test_recount_e2e.py:172-185`:

```python
# cuprum 0.1.0; the canonical installed exit-3 proof shape
run_dir = tmp_path / "run"
working_dir = run_dir / "working"
working_dir.mkdir(parents=True)
if state_bytes is not None:
    (working_dir / "state.toml").write_bytes(state_bytes)

prog = Program(str(installed_novel_state))
catalogue = single_program_catalogue("novel-state-run", prog)
result = sh.make(prog, catalogue=catalogue)("recount").run_sync(
    context=ExecutionContext(cwd=run_dir), capture=True
)
assert result.exit_code == 3, result.stderr
assert json.loads(result.stdout or "{}")["ok"] is False
assert "Traceback" not in (result.stderr or "")
```

Work Item 1 changes `("recount")` to `("reconcile")`; Work Item 2 changes it to
`()` (no subcommand) and substitutes the function-scoped
`_build_and_install_wordcount` helper for the `installed_novel_state` fixture.

## Interfaces and dependencies

All cuprum calls were verified against the locked `cuprum==0.1.0` wheel itself
— `uv.lock:113-118`, registry wheel sha256
`b03e813bb56afe75f6cc38ec742091a0b1dc183480630abbaf8f205c984c3e72` — whose
sources were unpacked and read directly. They were NOT verified against the
sibling working tree at `/data/leynos/Projects/cuprum`: that checkout is at a
post-0.1.0 revision ("Collapse `_IOBehaviour` into the canonical
`RunOutputOptions`") whose `SafeCmd.run_sync` has been refactored to take
`output: RunOutputOptions | None` and has NO `capture` keyword, so its line
numbers and signatures do not describe the wheel the tests run against. Every
citation below resolves against the 0.1.0 wheel; an implementer who opens those
files in the wheel will find exactly these signatures.

- `cuprum.program.Program` — `typ.NewType("Program", str)`
  (`cuprum/program.py:15`). `Program(str(absolute_path))` is the supported way to
  name an absolute-path executable; equality is string equality, so the
  catalogue allowlist matches the exact path.
- `cuprum.ProjectSettings(name, programs, documentation_locations, noise_rules)`
  (`cuprum/catalogue.py:30`) and `cuprum.ProgramCatalogue(projects=(...,))`
  (`cuprum/catalogue.py:56`). The `single_program_catalogue` conftest fixture
  already wraps this (`tests/conftest.py:246`); the new tests reuse the fixture,
  not the raw constructors.
- `cuprum.sh.make(program, catalogue=...)` (`cuprum/sh.py:529`) — builds a
  `SafeCmd`; `ProgramCatalogue.lookup` (`cuprum/catalogue.py:76`) raises
  `UnknownProgramError` for any unregistered program (`raise` at
  `cuprum/catalogue.py:82`), which is the execution gate that makes the
  catalogue allowlist load-bearing.
- `SafeCmd.run_sync(*, capture: bool = True, echo: bool = False, context:
  ExecutionContext | None = None) -> CommandResult` — `cuprum/sh.py:450`. In the
  locked 0.1.0 wheel `capture` is a **first-class keyword on `run_sync`** with
  default `True`; there is no `RunOutputOptions` routing on `run_sync` in 0.1.0
  (that routing is a post-0.1.0 sibling refactor). The tests pass `capture=True`
  explicitly to match the existing green installed e2es and to read the captured
  envelope. `ExecutionContext` (`cuprum/sh.py:165`) carries the `cwd` field that
  sets the subprocess working directory so the installed script resolves
  `./working/state.toml`.
- `CommandResult` (`cuprum/sh.py:89`) has fields `program, argv, exit_code, pid,
  stdout, stderr`; the new tests read only `exit_code: int`, `stdout: str |
  None`, and `stderr: str | None`. (`CommandResult.ok` is a derived property
  `exit_code == 0`, `cuprum/sh.py:116`; the tests assert the JSON envelope's
  `ok` field rather than this property, matching the recount proof.)

No cuprum API absent from `0.1.0` is required; the entire surface is the same one
the existing installed e2es already exercise (those tests are green against the
0.1.0 wheel, which independently pins the `capture=True` keyword). The plan
therefore does not need any external-library research beyond cuprum:
`pytest-timeout`'s per-test
`@pytest.mark.timeout(180)` override and the `@pytest.mark.parametrize` /
`@pytest.mark.skipif` / `@pytest.mark.slow` marks are already in use unchanged
across `tests/test_recount_e2e.py`, so their behaviour is pinned by the existing
green suite rather than asserted from memory.

Fixtures depended upon (all pre-existing, no new fixtures):

- `installed_novel_state` (module-scoped) —
  `tests/installed_binary_fixtures.py:92`, registered via `pytest_plugins` in
  `tests/conftest.py:55-60`. Used by Work Item 1.
- `single_program_catalogue` (function-scoped) — `tests/conftest.py:246`. Used by
  both work items.
- `venv_scripts_dir` (function-scoped) — `tests/conftest.py:278`. Used by Work
  Item 2 via `_build_and_install_wordcount`.
- `_build_and_install_wordcount` (module-local helper) —
  `tests/test_wordcount_e2e.py:42`. Used by Work Item 2.

## Revision note

Initial draft (2026-06-25). Decomposes roadmap task 6.2.6 into two atomic,
independently committable installed-binary exit-3 e2e additions — one for
`novel-state reconcile`, one for `wordcount` — each mirroring the `recount` proof
6.2.4 added. No production code or source-of-truth doc changes.

Round-2 revision (2026-06-25), in response to the round-1 Logisphere review
(`docs/execplans/roadmap-6-2-6.review-r1.md`):

- What changed: every cuprum citation was re-derived against the locked
  `cuprum==0.1.0` wheel (registry sha256 `b03e813…c984c3e72`, `uv.lock:113-118`)
  rather than the post-0.1.0 sibling checkout at `/data/leynos/Projects/cuprum`.
  The Constraints and "Interfaces and dependencies" sections now cite the wheel's
  line numbers (`CommandResult` `sh.py:89`, `ExecutionContext` `sh.py:165`,
  `SafeCmd.run_sync` `sh.py:450`, `make` `sh.py:529`; `ProjectSettings`
  `catalogue.py:30`, `ProgramCatalogue` `catalogue.py:56`, `lookup` `:76` /
  `raise` `:82`; `Program` `program.py:15`). The false `RunOutputOptions`
  sentence was corrected: in 0.1.0 `run_sync` takes `capture` as a first-class
  keyword (default `True`) with no `RunOutputOptions` routing; that routing is a
  post-0.1.0 sibling refactor. The two non-blocking advisories were also actioned
  — the typecheck gate is named as `ty` (`make typecheck` → `ty check`,
  `AGENTS.md:89`/`Makefile:100`), not `pyright`, and the `nixie` framing now
  states it validates Mermaid only.
- Why it changed: the standing rule requires locked-library behaviour to be
  verified and cited against the locked artefact. The round-1 trail pointed at a
  diverged tree and carried one claim that was false for the wheel.
- Effect on remaining work: none to the prescribed test code, which already
  matched the green existing tests and the wheel. Only the verification trail an
  implementer follows was corrected, so following the citations now lands on the
  exact `capture=True` API the tests use.
