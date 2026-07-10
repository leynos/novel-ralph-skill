# Extend the cross-command identity proof to the installed-wheel boundary

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT

## Purpose / big picture

The harness drives the five `novel` subcommands unattended and gates on their
exit code and JSON envelope. Roadmap task 6.3.2 pinned that every command
presents the *same* contract — the six-field envelope skeleton in the same
order, the same field types, and the same `ok`-to-exit-code mapping — but it did
so *in-process*, driving each command's `build_app()` factory through the shared
`novel_ralph_skill.contract.runner.run` seam (see
`tests/cross_command_contract/`). The binary the harness actually executes is the
*installed* `novel` console-script unpacked from a built wheel, not the
in-process entry-point body.

An installed-boundary exit-0 proof for `novel state check` **already exists**:
`tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
(lines 307-344) is a `@pytest.mark.slow`, `@pytest.mark.timeout(180)`,
POSIX-`skipif` e2e that builds and installs the wheel through
`installed_novel_state`, materializes a coherent `working/` tree from
`baseline_tree`, drives `novel state check` through the installed script with
`sh.make(prog, catalogue=...)("state", "check").run_sync(context=ExecutionContext(cwd=dest),
capture=True)`, and asserts `result.exit_code == 0` and `envelope["ok"] is True`.
The design document confirms this: §9 line 893 lists "the existing `check`
(exit 0) … proofs" among the installed-binary e2es. The installed error arms —
the usage error (exit 2) and the state error (exit 3) — are likewise pinned by
`tests/test_console_scripts_error_arms_e2e.py`.

The genuine residual gap is therefore *not* "the installed exit-0 arm is unproven";
it is that the existing installed exit-0 proof pins **only** `exit_code == 0` and
`envelope["ok"] is True`. It does **not** pin the rest of the envelope *skeleton
identity* over the wheel: the six-key order against `ENVELOPE_KEY_ORDER`,
`schema_version == 1`, `command == "novel state"` (a member of
`ENVELOPE_COMMAND_NAMES`), the resolved-absolute `working_dir`,
`result["violations"] == []`, and that every `messages` element is a `str`. The
in-process cross-command suite (6.3.2) pins all of these in-process; none of them
is observed crossing the wheel/venv packaging boundary. That skeleton identity
over the wheel is the residual delta this task closes.

After this change, the existing installed exit-0 test is *extended* in place with
the missing skeleton-identity assertions (no new module, no second wheel build),
asserting the same six contract keys in `ENVELOPE_KEY_ORDER`, `schema_version`,
`command`, `ok`-iff-exit-0, the resolved-absolute `working_dir`,
`result["violations"] == []`, and `str`-typed `messages`, against the same
constants the in-process suite uses. This closes the residual gap between the
in-process identity proof and the executed surface, reusing the existing
`installed_novel_state` and `single_program_catalogue` cuprum fixtures rather than
rebuilding the `command × channel` matrix.

Success is observable by running the extended test: it builds the wheel,
installs it, drives `novel state check` over a coherent `working/` tree through
the installed script by absolute path, parses the emitted machine envelope, and
asserts the same six contract keys in the same order with the same field types,
`schema_version == 1`, `command == "novel state"`, `ok: true`, the resolved
`working_dir`, and the `result` mapping a checker produces. Concretely, after this
change `make test` (and `make all`) passes, and a deliberately introduced
divergence — re-ordering the envelope fields, bumping `schema_version`, or
flipping the expected `ok` off the exit code — turns the extended tripwire red
while the rest of the suite is untouched. The test retains the same
`slow` / `timeout(180)` / POSIX-`skipif` marks it already carries.

## Constraints

Hard invariants that must hold throughout implementation.

- Work exclusively in the git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-6`. Never
  read-modify-write any file in the root/control worktree.
- This is a *verification* task. It extends one existing test (plus, in Work
  item 3, one documentation paragraph). No file under `novel_ralph_skill/`
  (production source) may change. The envelope
  (`novel_ralph_skill/contract/envelope.py`), the runner
  (`novel_ralph_skill/contract/runner.py`), the exit-code vocabulary
  (`novel_ralph_skill/contract/exit_codes.py`), and the five command
  `build_app()` factories must remain behaviourally unchanged. If the installed
  command genuinely *diverges* from the contract, that is a defect for a separate
  task — stop and escalate; do not "fix" production code under cover of this test
  task.
- Reuse the existing installed-binary scaffolding by fixture *name*. Do **not**
  introduce a new catalogue, a new wheel-build helper, or a new installed-binary
  fixture. The change extends the *existing* installed exit-0 test
  (`test_novel_state_check.py::test_installed_novel_state_check_exits_zero`),
  which already consumes `installed_novel_state` (module-scoped, builds the wheel
  and installs once per module; `tests/installed_binary_fixtures.py`),
  `single_program_catalogue` (`tests/conftest.py`), and `baseline_tree`
  (`tests/corpus_fixtures.py`) by name. Because the new assertions live in the
  same module that already builds the wheel, they add **zero** extra wheel-build
  cost. The developers-guide "Shared test scaffolding" rule forbids new copies of
  existing scaffolding and forbids cross-module fixture/value imports; fixtures
  are bound by parameter name (`docs/developers-guide.md` lines 20-105).
- The shared envelope field set and order are fixed by ADR-003 and design §3.1:
  `command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`. The
  exit-code table is fixed by ADR-003 Table 2 and design §3.2. `ok` is `True` if
  and only if the code is 0 (design §3.1). The tripwire asserts these against the
  installed surface; it does not redefine them. The cross-command suite already
  expresses these as `ENVELOPE_KEY_ORDER` and
  `assert_envelope_skeleton` in `tests/cross_command_contract/`.
- The installed binary stamps the **absolute resolved** `working_dir`, not the
  literal `"working"` token the in-process suite asserts. This is the deliberate
  6.3.4 behaviour: the in-process `assert_envelope_skeleton` checks
  `working_dir == "working"` (`tests/cross_command_contract/__init__.py`
  `WORKING_DIR_CONSTANT`), whereas the installed boundary stamps
  `str((<run-dir> / "working").resolve())`
  (`tests/test_console_scripts_error_arms_e2e.py` lines 301-307, where that
  module's run dir is `run_dir`). The extended test must therefore assert the five
  contract-fixed fields (`command`, `schema_version`, `ok`, `result`, `messages`)
  plus the *resolved absolute* `working_dir`, computed from *its* run dir `dest`
  as `str((dest / "working").resolve())` — the same way the production code
  resolves it — so symlink normalization cannot desynchronize them. Do not assert
  the installed
  `working_dir` equals `"working"`.
- The installed e2e is POSIX-only (ADR-006): every external program runs by
  absolute path through a one-project cuprum `ProgramCatalogue` allowlist, with
  no raw `subprocess` and no `uv run` resolution of the project environment. The
  extended test already carries its per-test POSIX `skipif` guard
  (`test_novel_state_check.py` lines 310-313); no new guard is added.
- cuprum is pinned to `0.1.0` (`uv.lock` line 113-118). The locked wheel's
  `SafeCmd.run_sync` takes a `capture: bool = True` keyword, **not** the local
  working-tree's `output: RunOutputOptions` parameter (verified below). Pin every
  cuprum call to the locked 0.1.0 API the existing fixtures use; do not follow
  the unreleased local source signature.
- Tests live in the top-level `tests/` tree (AGENTS.md "Python verification and
  testing"). Snapshot tests use `syrupy` and must be paired with semantic
  assertions, never snapshot-only; redact nondeterministic fields (the absolute
  `working_dir`, `messages`) before snapshotting (AGENTS.md lines 148-158).
- No single code file exceeds 400 lines (AGENTS.md). `test_novel_state_check.py`
  is 344 lines; the added skeleton assertions (and three import lines) must not
  push it past the 400-line cap. If they would, stop and escalate (see
  Tolerances) — splitting the installed test into its own module is a separate
  decision that reintroduces a second wheel build and must be weighed explicitly.
- Every `tests/`-tree module under `$(PYTHON_TARGETS)` carries a module docstring
  and a docstring on every fixture, helper, and test function (100% `interrogate`
  coverage), and raises `AssertionError` directly rather than a bare `assert`
  inside non-`test_*` helper/fixture bodies. The extended test is a `test_*`
  function, so it may keep plain `assert` (as it and
  `tests/test_console_scripts_error_arms_e2e.py` already do); no new helper or
  fixture is introduced.
- All prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` skill. External
  API names (Cyclopts, syrupy, cuprum, `schema_version`) are quoted verbatim.

## Tolerances (exception triggers)

- Scope: if the change requires touching more than 2 files net (the existing
  `tests/test_novel_state_check.py` and the developers-guide paragraph), or
  editing any file under `novel_ralph_skill/` (production source), stop and
  escalate.
- Line cap: if extending `test_novel_state_check.py` in place would push it past
  the 400-line cap (AGENTS.md), stop and escalate. Splitting the installed test
  into a separate module reintroduces a second module-scoped wheel build, a
  decision for escalation, not an in-flight workaround.
- Production divergence: if the installed command is found to genuinely violate
  the shared contract (a real field-order, field-set, type, `schema_version`, or
  `ok`/exit-code divergence at the wheel boundary), stop and escalate — that
  is a defect fix for a separate roadmap task, not part of pinning the contract.
- Scaffolding: if the skeleton assertions cannot be expressed inside the
  existing `test_installed_novel_state_check_exits_zero` (which already consumes
  `installed_novel_state`, `single_program_catalogue`, and `baseline_tree` by
  name) and a new fixture or wheel-build helper seems necessary, stop and
  escalate rather than duplicating scaffolding or paying a second wheel build.
- Dependencies: if a new external dependency is required, stop and escalate. The
  tripwire uses only the already-locked `pytest`, `syrupy`, `cuprum` (`0.1.0`),
  and the existing `working_corpus` plugin.
- Iterations: if the tripwire still fails after 4 focused attempts to align it
  with the real installed contract (and the failure is *not* a genuine
  production divergence), stop and escalate.
- Matrix creep: if pinning the success arm tempts a full `command × channel`
  re-run over the wheel, stop — the roadmap scopes this to *one* tripwire for a
  *representative* command "without duplicating the full command × channel
  matrix" (roadmap §6.3.6). Widening belongs to a separate addendum.

## Risks

    - Risk: Re-building the wheel a second time by adding a *new* installed
      module for `novel state check`, when an installed exit-0 test for that
      exact command/arm already exists
      (`test_novel_state_check.py::test_installed_novel_state_check_exits_zero`).
      The module-scoped wheel build runs once *per consuming module*, so a new
      module pays a full second build for a command already installed-tested.
      Severity: medium
      Likelihood: high
      Mitigation: Do not add a new module. *Extend the existing exit-0 test in
      place* with the missing skeleton-identity assertions (key order against
      `ENVELOPE_KEY_ORDER`, `schema_version`, `command`, resolved `working_dir`,
      `result["violations"] == []`, `str`-typed `messages`). The wheel is already
      built in that module, so the assertions add zero build cost. The existing
      test pins only `exit_code == 0` and `ok is True`; the extension is purely
      additive over the same `result`.

    - Risk: Redundancy against the installed *error*-arm e2e
      (`tests/test_console_scripts_error_arms_e2e.py`), which already crosses the
      wheel for the diagnostic arms.
      Severity: low
      Likelihood: low
      Mitigation: The error-arm module pins only exit 2 (usage) and exit 3
      (state); it does not touch the exit-0 body skeleton. The extension targets
      the success arm exclusively, so there is no overlap. Record the boundary in
      Work item 3 so the developers-guide names which module pins which arm.

    - Risk: The installed `working_dir` is the absolute resolved path, not the
      `"working"` token the in-process `assert_envelope_skeleton` asserts, so a
      naive reuse of that helper fails on `working_dir`.
      Severity: medium
      Likelihood: high
      Mitigation: Assert the five contract-fixed fields plus the resolved
      absolute `working_dir`, computing the expected value as
      `str((run_dir / "working").resolve())` exactly as
      `test_console_scripts_error_arms_e2e.py` lines 301-307 do (so symlink
      normalization under `tmp_path` cannot desynchronize them). Pin the key
      order and types against `ENVELOPE_KEY_ORDER` from the cross-command
      package. Do not call the in-process `assert_envelope_skeleton` verbatim —
      its `working_dir == "working"` check is in-process-only.

    - Risk: Importing the cross-command constants (`ENVELOPE_KEY_ORDER`,
      `BODY_PHASE`) into `test_novel_state_check.py` trips the developers-guide
      cross-module rule, or the constants drift from the values the existing test
      already relies on.
      Severity: low
      Likelihood: low
      Mitigation: `ENVELOPE_KEY_ORDER` and `BODY_PHASE` are plain-value
      `typ.Final` constants in `tests/cross_command_contract/__init__.py`, not
      fixtures, so importing them is permitted (the developers-guide rule bars
      cross-module *fixture/value-via-fixture* imports, not shared constants).
      `ENVELOPE_SCHEMA_VERSION`, `ExitCode`, and `ENVELOPE_COMMAND_NAMES` come
      from production modules. The existing test does not currently materialize
      via `BODY_PHASE`; it uses `baseline_tree`, which is the coherent tree. Keep
      `baseline_tree` (it is the established coherent corpus the test already
      copies) and assert against the *constants*, so the installed assertion
      mirrors the in-process key order rather than re-spelling it. Do not swap the
      tree source.

    - Risk: The slow wheel build crosses the project's default 30s pytest
      timeout, failing under `pytest-timeout`.
      Severity: medium
      Likelihood: high
      Mitigation: Carry `@pytest.mark.slow` and `@pytest.mark.timeout(180)` on
      the tripwire, exactly as every installed e2e does
      (`test_console_scripts_error_arms_e2e.py` lines 252-253). Per-test
      `timeout` marks override the project default under `pytest-timeout` even
      with `pytest-xdist` (verified below).

    - Risk: cuprum 0.1.0's `run_sync` signature differs from the local
      working-tree source, so a call copied from the unreleased source breaks.
      Severity: low
      Likelihood: low
      Mitigation: Reuse the established 0.1.0 call shape
      `sh.make(prog, catalogue=...)(*argv).run_sync(context=ExecutionContext(cwd=...),
      capture=True)`, verified against the installed wheel below. The `run_dir`
      fixture pattern already encapsulates this.

## Progress

    - [x] Work item 1: Extend
      `test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
      with the installed-boundary envelope-skeleton identity assertions (key
      order, `schema_version`, `command`, resolved `working_dir`,
      `result["violations"] == []`, `str`-typed `messages`). Done: the test
      gained the eight skeleton-identity assertions over the parsed envelope; the
      file is 380 lines (under the 400 cap); the three constant imports were
      added; `make all` green (1310 passed, 1 skipped).
    - [x] Work item 2: Teeth check — perturb one extended assertion and confirm
      the test goes red on the asserted field (not on a build error), then revert
      (no commit of the perturbation); record in the Decision Log. Done: see the
      Decision Log entry "Teeth check (Work item 2)".
    - [x] Work item 3: Developers-guide note recording what the extended installed
      test now pins and its boundary against the installed error-arm e2e and the
      in-process cross-command suite. Done: a paragraph in the "Shared test
      scaffolding" section, beside the error-arm e2e note, records the success-arm
      scope, the three-proof boundary, the in-place extension rationale, and the
      reused fixtures. `make all` / `make markdownlint` / `make nixie` green;
      coderabbit reported zero findings.

## Surprises & discoveries

    - Observation: The locked cuprum 0.1.0 wheel's `SafeCmd.run_sync` accepts a
      `capture` keyword, whereas the local `/data/leynos/Projects/cuprum` working
      tree (a newer, unreleased revision) replaced it with an
      `output: RunOutputOptions` parameter.
      Evidence: `uv run python -c "import inspect; from cuprum.sh import SafeCmd;
      print(inspect.signature(SafeCmd.run_sync))"` against this repo's `.venv`
      prints `(self, *, capture: bool = True, echo: bool = False, context:
      ExecutionContext | None = None) -> CommandResult`; the same module in
      `/data/leynos/Projects/cuprum/cuprum/sh.py` line 441 shows
      `output: RunOutputOptions | None`. `uv.lock` line 113-118 pins cuprum to
      `0.1.0`.
      Impact: This plan pins every cuprum call against the *locked* 0.1.0 API
      (the wheel actually installed), matching the existing e2e modules
      (`.run_sync(context=ExecutionContext(cwd=...), capture=True)`,
      `CommandResult.{exit_code,stdout,stderr}`). It does not follow the local
      working-tree signature.

    - Observation: An installed exit-0 proof for `novel state check` already
      exists — `test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
      — but it pins only `exit_code == 0` and `envelope["ok"] is True`, nothing
      else of the envelope skeleton. The residual gap is the *unpinned skeleton
      identity* over the wheel, not an absent exit-0 proof.
      Evidence: `test_novel_state_check.py` lines 307-344: the test is
      `@pytest.mark.slow`/`@pytest.mark.timeout(180)`/POSIX-`skipif`, builds and
      installs via `installed_novel_state`, copies `baseline_tree()` into
      `dest/working`, drives `("state", "check").run_sync(...)`, and ends with
      `assert result.exit_code == 0` and `assert envelope["ok"] is True`. It does
      NOT assert key order against `ENVELOPE_KEY_ORDER`, `schema_version`,
      `command == "novel state"`, the resolved-absolute `working_dir`,
      `result["violations"] == []`, or `messages` element types. Design §9 line
      893 lists "the existing `check` (exit 0) … proofs", confirming the exit-0
      proof's existence. `test_console_scripts_error_arms_e2e.py` separately
      covers the exit-2 (usage) and exit-3 (state) arms.
      Impact: The task is re-scoped from "add a new success-arm tripwire module"
      to "extend the existing installed exit-0 test in place with the missing
      skeleton-identity assertions". This avoids a second module-scoped wheel
      build (the existing module already pays one) and pins the genuine residual:
      the full envelope-skeleton identity crossing the wheel for the exit-0 arm.

## Decision log

    - Decision: Scope this task as a single success-arm (exit 0) envelope-
      *skeleton-identity* tripwire over one representative command
      (`novel state check`), reusing the installed fixtures, rather than
      re-crossing the full command × channel matrix over the wheel.
      Rationale: Roadmap §6.3.6 requires "one installed-binary identity tripwire"
      that "drives a representative command through the installed wheel and
      asserts its envelope skeleton and exit-code mapping match the in-process
      contract pinned by 6.3.2 … without duplicating the full command × channel
      matrix". An installed exit-0 *liveness* proof already exists
      (`test_installed_novel_state_check_exits_zero`, pinning only `exit_code == 0`
      and `ok is True`); the unpinned residual is the *rest of the envelope
      skeleton* (key order, `schema_version`, `command`, resolved `working_dir`,
      `result` payload, message types) over the wheel. The tripwire targets
      exactly that residual.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Extend the existing installed exit-0 test
      (`test_novel_state_check.py::test_installed_novel_state_check_exits_zero`)
      in place with the skeleton-identity assertions, rather than adding a new
      `test_installed_identity_tripwire_e2e.py` module.
      Rationale: Two paths are defensible. (a) *Extend in place*: the existing
      test already builds and installs the wheel through the module-scoped
      `installed_novel_state`, materializes the coherent `baseline_tree`, and
      drives `("state", "check")` through the installed script; the missing
      skeleton assertions are additive over the same `result`, so they cost zero
      extra wheel build. (b) *New module*: a separate
      `test_installed_identity_tripwire_e2e.py` would carry its own module-scoped
      `installed_novel_state`, which builds, venvs, and installs the wheel a
      *second* time for the same command/arm — a real, repeated cost in `make all`
      (`installed_novel_state` runs once per consuming module;
      `tests/installed_binary_fixtures.py`), buying only module isolation the
      existing test already provides. Path (a) is chosen: same command, same arm,
      same fixtures, no duplicate build, and the assertions sit beside the exit-0
      assertion they reinforce. The only cost is a slightly longer test body and
      three new imports, well within the 400-line cap (the module is 344 lines).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Representative command is `novel state check`; keep the existing
      test's coherent `baseline_tree`, not a `BODY_PHASE`-materialized tree.
      Rationale: `novel state check` is the canonical read surface, and the
      existing installed test already drives it through the `state` sub-app with
      the argv shape `("state", "check")`. That test materializes its coherent
      tree by copying `baseline_tree()` into `dest/working`
      (`test_novel_state_check.py` lines 332-335); `baseline_tree` is the
      established coherent corpus tree and a coherent tree exits 0 with
      `result["violations"] == []`. The cross-command in-process suite uses
      `BODY_PHASE = "final-pass"` for *its* body cell, but both are coherent and
      both exit 0; keeping `baseline_tree` avoids a gratuitous tree-source swap in
      a test that already passes, while the *assertions* still mirror the
      cross-command key order via the imported `ENVELOPE_KEY_ORDER` constant. Only
      the constants are imported, never a tree fixture, so no in-process success
      cell is re-spelled.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Reuse `installed_novel_state`, `single_program_catalogue`, and
      `baseline_tree` by fixture name; no new runner fixture is introduced — the
      extended test already wires the cuprum call inline (lines 337-341).
      Rationale: The developers-guide "Shared test scaffolding" rule forbids new
      copies of existing scaffolding and cross-module value imports; consumers
      bind fixtures by name, which the existing test already does. The locked
      cuprum 0.1.0 API that test uses is verified
      (`ProgramCatalogue(projects=(ProjectSettings(name, programs,
      documentation_locations, noise_rules),))` via `single_program_catalogue`,
      `Program(str(absolute_path))` allowlisted by exact value,
      `sh.make(program, catalogue=)`,
      `.run_sync(context=ExecutionContext(cwd=...), capture=True)`,
      `CommandResult.{exit_code,stdout,stderr}`). The extension adds only
      assertions and the three constant imports, no new fixture body.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Teeth check (Work item 2) — the new assertions bite on the
      asserted field, not on a build error.
      Evidence: perturbing the `command` assertion to
      `assert envelope["command"] == "novel-wrong"` turned the single test red
      with `AssertionError: assert 'novel state' == 'novel-wrong'` — the installed
      run built the wheel, exited 0, and produced a real `'novel state'` envelope,
      so the red landed on the perturbed comparison rather than a wheel-build or
      parse failure. Reverting the perturbation returned the test to green
      (`1 passed`). The perturbation was kept local and uncommitted.
      Date/Author: 2026-06-26, implementing agent.

    - Decision: `result.stderr` is `str | None` under the locked cuprum 0.1.0
      `CommandResult`, so the traceback assertion guards `None`.
      Rationale: `ty` rejected `assert "Traceback" not in result.stderr`
      (unsupported `not in` against `str | None`). The fix matches the established
      `test_console_scripts_error_arms_e2e.py` pattern
      `assert "Traceback" not in (result.stderr or "")` (line 281). No production
      code changed.
      Date/Author: 2026-06-26, implementing agent.

    - Decision: Keep the 4-space-indented list style in Risks / Progress /
      Surprises / Decision Log despite a coderabbit nit that they render as code
      blocks, and rephrase the success paragraph into impersonal voice.
      Rationale: the deep-indent list style is the established execplan house
      style (`docs/execplans/roadmap-6-3-2.md` uses identical indentation in its
      Progress and Decision Log) and passes `make markdownlint`; diverging for one
      document would break corpus consistency. The impersonal-voice nit on the
      success paragraph (lines 55-61) was a cheap prose improvement and was
      applied. The two logisphere review artefacts' trailing-punctuation headings
      and one over-length line were corrected to keep `make markdownlint` green;
      the machine-path nit in the r2 artefact was left as-is (the artefact is a
      transient review record, not a tracked deliverable, and deleting it was
      denied by the sandbox).
      Date/Author: 2026-06-26, implementing agent.

    - Decision: Assert the resolved-absolute `working_dir`, not the `"working"`
      token, and do not call the in-process `assert_envelope_skeleton` verbatim.
      Rationale: After 6.3.4 the binary stamps the absolute resolved working
      directory (`test_console_scripts_error_arms_e2e.py` lines 301-307), whereas
      the in-process `assert_envelope_skeleton`
      (`tests/cross_command_contract/_identity_assertions.py`) asserts
      `working_dir == "working"`. The extended test pins the key order against
      `ENVELOPE_KEY_ORDER` and the contract-fixed fields, computing the expected
      `working_dir` as `str((dest / "working").resolve())` — `dest` is the
      existing test's run directory (`test_novel_state_check.py` line 330), the
      same directory passed as `ExecutionContext(cwd=dest)` — so the divergence is
      asserted *as the intended 6.3.4 behaviour*, not papered over, and symlink
      normalization under `tmp_path` cannot desynchronize the two sides.
      Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

Delivered as planned. The existing installed exit-0 test was extended in place
into an installed-boundary success-arm *skeleton-identity* tripwire (no second
wheel build), reusing the existing cuprum fixtures; it now fails on any
divergence of the installed exit-0 envelope skeleton (key order,
`schema_version`, `command`, resolved `working_dir`, `result` payload, message
types) from the in-process contract. The teeth check confirmed the new
assertions bite on the asserted field. The developers-guide records the
extended test's success-arm scope and its boundary against the installed
error-arm e2e and the in-process cross-command proof. No production source under
`novel_ralph_skill/` changed; no new module, fixture, or second wheel build was
introduced; `test_novel_state_check.py` stayed at 380 lines, under the 400-line
cap. `make all` green (1310 passed, 1 pre-existing skip); `make markdownlint` and
`make nixie` green on the edited Markdown. Two coderabbit runs: the first
surfaced three minor doc nits (one prose-voice fix applied, two artefact lint
fixes applied, one house-style nit declined with rationale); the second reported
zero findings.

## Context and orientation

The harness is a Python package, `novel_ralph_skill`, that ships a single
`novel` console-script multiplexer (ADR-007). Each invocation emits one JSON
"envelope" on stdout (or a human rendering under `--human`) and exits with a
contract code. Read the following before starting; they are the source of truth.

- `docs/adr-003-shared-interface-contract.md` — the shared six-field envelope,
  the four-flag Cyclopts construction contract (Table 3), and the disambiguated
  five-code exit table (Table 2). This is the contract the tripwire pins at the
  installed boundary.
- `docs/novel-ralph-harness-design.md` §3 (lines 131-264) — the same contract in
  narrative form: §3.1 the envelope and `ok`-iff-exit-0 rule, §3.2 the exit
  codes, §3.3 command/query segregation (why a checker's `result` carries
  `violations`). §9 (the verification strategy; lines 847-908) — the
  "Installed-binary e2es prove the exit-code contract at the real wheel/venv
  packaging boundary" rule, the wheel-build-and-install discipline, the cuprum
  catalogue allowlist, and the POSIX-only constraint. §10 (failure modes) — a
  fault yields a message, not a stack trace.
- `docs/adr-006-console-scripts-e2e-posix-policy.md` — the POSIX-only,
  absolute-path-through-catalogue policy the installed e2es follow.
- `docs/developers-guide.md` "Shared test scaffolding" (lines 20-105) — the
  fixture-by-name rule, the module-scoped `installed_novel_state` fixture, the
  `single_program_catalogue` builder, the `slow`/`timeout(180)`/POSIX-`skipif`
  convention the installed error-arm module carries, and the 400-line cap
  rationale.
- `docs/execplans/roadmap-6-3-2.md` — the in-process cross-command identity
  proof this tripwire extends. Its Decision Log (the entry beginning "Do not
  introduce a new shared catalogue or installed-binary fixture", lines 329-342)
  sketches exactly this tripwire: reuse `installed_novel_state` /
  `single_program_catalogue`, do not rebuild the matrix. Its Interfaces /
  Constructible-cell table (lines 548-600) records which commands reach which
  channels.
- `AGENTS.md` — the quality gates, the testing rules (pytest, snapshots paired
  with semantic assertions, redact nondeterministic fields, e2e for externally
  observable workflows), and the Oxford-spelling convention.

Key production files (read-only for this task):

- `novel_ralph_skill/contract/envelope.py` — `build_envelope` (derives `ok` from
  the code), `render_machine` (the fixed `result`-before-`messages` field order),
  and `ENVELOPE_SCHEMA_VERSION = 1`.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode` (`SUCCESS 0`,
  `BENIGN_NEGATIVE 1`, `USAGE_ERROR 2`, `STATE_ERROR 3`, `ACTIONABLE_FINDING 4`)
  and `is_ok`.
- `novel_ralph_skill/commands/names.py` — `ENVELOPE_COMMAND_NAMES`.

Key existing tests (read before editing):

- `tests/test_novel_state_check.py` — **the file this task edits.** Its installed
  e2e `test_installed_novel_state_check_exits_zero` (lines 307-344) builds and
  installs the wheel via `installed_novel_state`, copies `baseline_tree()` into
  `dest/working` (lines 332-335), drives `("state", "check").run_sync(
  context=ExecutionContext(cwd=dest), capture=True)` (lines 337-341), and asserts
  only `result.exit_code == 0` (line 342) and `envelope["ok"] is True` (line 344).
  It already imports `json`, `os`, `pytest`, `cuprum.sh`, `Program`,
  `ExecutionContext`, and `ExitCode` (lines 26-40). The task extends this test
  with the missing skeleton-identity assertions; it is the installed mirror of the
  module's own in-process exit-0 case `test_check_coherent_tree_exits_zero`
  (lines 76-89), a coherent tree that exits 0 with `result.violations == []`.
- `tests/test_console_scripts_error_arms_e2e.py` — the installed error-arm e2e
  (exit 2/3 only). Read its resolved-`working_dir` computation (lines 301-307) as
  the model for asserting the absolute `working_dir`. The extended test reuses
  the same `slow`/`timeout(180)`/POSIX-`skipif` discipline this module also
  carries; the existing exit-0 test already has all three marks.
- `tests/installed_binary_fixtures.py` — the module-scoped `installed_novel_state`
  fixture (lines 111-166) and the locked cuprum 0.1.0 call shape (lines 203-209).
- `tests/conftest.py` — `single_program_catalogue` (lines 255-284); the
  `pytest_plugins` tuple (lines 54-72) that registers `installed_binary_fixtures`,
  `corpus_fixtures` (the `baseline_tree` source), and `working_corpus`.
- `tests/corpus_fixtures.py` — `baseline_tree` (line 207), the coherent corpus
  tree the existing installed test copies into `dest/working`.
- `tests/cross_command_contract/__init__.py` — `ENVELOPE_KEY_ORDER`,
  `WORKING_DIR_CONSTANT`, `BODY_PHASE`, and `COMMANDS`. The extended test imports
  `ENVELOPE_KEY_ORDER` from this package (a sibling test package; import the
  *constant*, a plain `typ.Final` value, not a fixture) so the installed assertion
  mirrors the in-process key order rather than re-spelling it. `BODY_PHASE` is the
  in-process body cell's phase; the extended test keeps `baseline_tree` (also
  coherent) rather than swapping trees, so it imports only `ENVELOPE_KEY_ORDER`.
- `tests/cross_command_contract/_identity_assertions.py` —
  `assert_envelope_skeleton` (the in-process skeleton helper, which asserts
  `working_dir == "working"`; the extended test deliberately does NOT call it
  verbatim for the `working_dir` field — see the Decision Log).

Terms:

- "Envelope" — the six-field JSON object every command emits (design §3.1).
- "Envelope skeleton" — the envelope reduced to its contract-fixed fields, set,
  order, and types, with the command-specific `result`/`messages` set aside.
- "Identity tripwire" — a single fast-to-author, slow-to-run test that fails if
  the installed surface drifts from the in-process contract; it does not
  re-enumerate the matrix.
- "Installed boundary" — the built-and-installed `novel` console-script run by
  absolute path through a cuprum catalogue allowlist, as opposed to the
  in-process `run` seam.

## Plan of work

The work proceeds in three small, independently committable items. Work item 1
extends the existing installed exit-0 test with the skeleton-identity assertions;
Work item 2 proves their teeth (no commit of the perturbation); Work item 3 adds
a documentation paragraph. Each ends with the project gate.

Establish a failing-first discipline per AGENTS.md. Because the test is a
*tripwire* — it should already pass because the installed contract holds — prove
its teeth (Work item 2) by temporarily perturbing one new assertion locally and
confirming the test goes red on the asserted field, then revert. Record the
perturbation result in the Decision Log; do not commit it.

### Work item 1: Extend the installed exit-0 test with skeleton-identity assertions

Implements design §9 (installed-binary e2es prove the contract at the wheel/venv
boundary), §3.1 (the six-field envelope and `ok`-iff-exit-0), ADR-003 (envelope
field set and order; Table 2), ADR-006 (POSIX absolute-path-through-catalogue
policy), and roadmap §6.3.6.

Edit `tests/test_novel_state_check.py`. Do **not** add a new module (see the
Decision Log: a new module pays a second module-scoped wheel build for the same
command/arm). The edit:

- adds three imports near the existing import block (lines 26-41):
  `from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION`,
  `from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES`, and
  `from cross_command_contract import ENVELOPE_KEY_ORDER`. (`json`, `os`,
  `cuprum.sh`, `Program`, `ExecutionContext`, and `ExitCode` are already imported.)
  `cross_command_contract` is a sibling test package and `ENVELOPE_KEY_ORDER` is
  a plain `typ.Final` constant, so this is not a cross-module fixture/value-import
  breach (developers-guide "Shared test scaffolding");
- extends the docstring of `test_installed_novel_state_check_exits_zero` to record
  that the test now pins the full exit-0 envelope-skeleton identity over the wheel
  (key order, `schema_version`, `command`, resolved `working_dir`, `result`
  payload, message types), not only `exit_code == 0` and `ok`;
- after the existing `envelope = json.loads(result.stdout or "{}")` (line 343),
  keeps `assert envelope["ok"] is True` and **adds** the following assertions over
  the same parsed `envelope` (the test keeps its `slow`/`timeout(180)`/POSIX-`skipif`
  marks and its `dest`/`baseline_tree` setup unchanged):
  1. assert no `"Traceback"` in `result.stderr` (design §10 — a fault yields a
     message, not a stack trace; here there is no fault, so stderr carries no
     traceback). Use the existing `result.stderr`;
  2. assert the parsed key order equals `ENVELOPE_KEY_ORDER`, e.g.
     `assert tuple(envelope) == ENVELOPE_KEY_ORDER` — the cross-command key-order
     identity, now observed over the wheel;
  3. assert `envelope["command"] == "novel state"` and
     `envelope["command"] in ENVELOPE_COMMAND_NAMES` (the dispatcher stamps the
     spaced sub-app name `novel state`, *not* the subcommand `check`; this is
     the existing `_COMMAND` constant at line 50);
  4. assert `envelope["schema_version"] == ENVELOPE_SCHEMA_VERSION`;
  5. assert `envelope["ok"] is (result.exit_code == ExitCode.SUCCESS)` — the
     `ok`-iff-exit-0 mapping over the installed surface (the existing
     `assert envelope["ok"] is True` already pins the value; this pins the
     mapping);
  6. assert `envelope["working_dir"] == str((dest / "working").resolve())`
      — the resolved-absolute `working_dir` the binary stamps post-6.3.4
      (computed the production way from `dest`, the test's run directory, so
      symlink normalization under `tmp_path` cannot desynchronize the two sides),
      NOT the `"working"` token;
  7. assert `isinstance(envelope["result"], dict)` and
      `envelope["result"]["violations"] == []` — the checker's coherent-tree body
      payload (the installed mirror of the module's own in-process
      `test_check_coherent_tree_exits_zero`);
  8. assert `isinstance(envelope["messages"], list)` and every element is a
      `str` (e.g. `all(isinstance(m, str) for m in envelope["messages"])`).

Do **not** add a snapshot. The in-process cross-command suite already snapshots
the redacted skeleton; an installed `.ambr` would only re-pin the same fixed
fields the semantic assertions above already cover, while adding a snapshot file
that redacts the absolute `working_dir` and `messages` down to the very fields
the assertions check. The semantic assertions are the complete and primary guard
(this choice is recorded in the Decision Log).

The extended test asserts `command`/`schema_version`/key-order against the same
constants the in-process suite uses (`ENVELOPE_KEY_ORDER`,
`ENVELOPE_SCHEMA_VERSION`, `ENVELOPE_COMMAND_NAMES`), so a drift in the installed
surface that the in-process suite would catch is also caught here — the installed
tripwire and the in-process proof cannot silently diverge.

Docs to read for this item: design §9, §3.1, §3.2, §10; ADR-003 (Table 2);
ADR-006; `docs/execplans/roadmap-6-3-2.md` Decision Log (the installed-fixture
reuse entry, lines 329-342); `tests/test_console_scripts_error_arms_e2e.py`
(the resolved-`working_dir` computation, lines 301-307); the existing
`test_installed_novel_state_check_exits_zero` (lines 307-344, the test being
extended); the `cross_command_contract` package `__init__.py` constants. Skills
to load: `python-router` then `python-testing` (marks, the `slow`/`timeout`
convention) and `en-gb-oxendict` for prose. No verification adversary
(Hypothesis/CrossHair/mutmut) is warranted: this is a single example tripwire over
one constructible cell, not an invariant over a range of inputs.

Tests changed: `test_installed_novel_state_check_exits_zero` gains the
skeleton-identity assertions (still slow, POSIX-only). Validation: `make all`.

### Work item 2: Teeth check (perturb-and-revert)

Implements the AGENTS.md failing-first discipline for a tripwire. Because the
installed contract already holds, the extended test passes on first authoring.
Prove the new assertions bite: temporarily perturb one *new* assertion in
`test_installed_novel_state_check_exits_zero` — for example assert
`tuple(envelope) == ENVELOPE_KEY_ORDER[::-1]`, assert
`envelope["schema_version"] == ENVELOPE_SCHEMA_VERSION + 1`, or assert
`envelope["command"] == "novel-wrong"` — then run the single test:

        uv run pytest \
          "tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero" \
          -m slow

Confirm it goes red **on the asserted field** (read the assertion-error message
to confirm it is the perturbed assertion, not a wheel-build error), then revert
the perturbation and confirm green. Record the observed red/green transition, and
the confirmation that the red landed on the asserted field, in the Decision Log.
Do **not** commit the perturbation.

This is a verification task, so do not perturb production source — perturb only
the test's expected values. Keep the perturbation local and uncommitted.

Docs to read: AGENTS.md "Python verification and testing" (failing-first); the
6.3.2 execplan "Plan of work" preamble (the tripwire teeth-check convention).
Skills to load: `python-testing`.

Validation: the single-test red run followed by the green `make all`. No new
commit beyond Work item 1 (the teeth check is recorded in the Decision Log, not
in code).

### Work item 3: Developers-guide note recording the extended test's scope

Implements the AGENTS.md "Documentation maintenance" rule and the developers-guide
"Shared test scaffolding" convention of recording each installed e2e module's
scope. Add a short paragraph to `docs/developers-guide.md` (in or beside the
"Shared test scaffolding" section, near the existing
`test_console_scripts_error_arms_e2e.py` note at lines 51-56) recording that
`tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero` now
pins the full installed exit-0 envelope-skeleton identity (key order,
`schema_version`, `command`, `ok`-iff-exit-0, the resolved `working_dir`,
`result["violations"] == []`, and `str`-typed `messages`) over the wheel for
`novel state check`, not merely `exit_code == 0` and `ok`. Record its boundary
against the two neighbouring installed/in-process proofs: it covers the *success*
arm, whereas `test_console_scripts_error_arms_e2e.py` covers the *error* arms
(exit 2/3); and it is the installed mirror of the in-process
`tests/cross_command_contract/` identity proof — deliberately a single tripwire
over one representative command, not a re-run of the command × channel matrix
(roadmap §6.3.6). State that it was extended in place rather than split into a new
module to avoid a second module-scoped wheel build, and that it reuses
`installed_novel_state`, `single_program_catalogue`, and `baseline_tree` by name.
Note it carries the same `slow`/`timeout(180)`/POSIX-`skipif` marks as the other
installed e2es. Wrap prose at 80 columns; use en-GB Oxford spelling.

Docs to read: `docs/developers-guide.md` "Shared test scaffolding";
`docs/documentation-style-guide.md`. Skills to load: `en-gb-oxendict`.

Validation: `make all`, then `make markdownlint` and `make nixie` (Markdown
changed).

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-6`.

1. Confirm the branch and a clean tree:

        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-6 \
          branch --show-current

   Expect `roadmap-6-3-6`.

2. Re-verify the locked cuprum `run_sync` signature before relying on it:

        uv run python -c "import inspect; from cuprum.sh import SafeCmd; \
        print(inspect.signature(SafeCmd.run_sync))"

   Expect `(self, *, capture: bool = True, echo: bool = False, context:
   ExecutionContext | None = None) -> CommandResult`.

3. Extend `test_installed_novel_state_check_exits_zero` in
   `tests/test_novel_state_check.py` per Work item 1 (three new imports plus the
   skeleton-identity assertions after the existing `envelope = json.loads(...)`).

4. Confirm the extended test still collects as one id:

        uv run pytest \
          "tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero" \
          --collect-only -q

   Expect the single id
   `test_novel_state_check.py::test_installed_novel_state_check_exits_zero`.

5. Run the extended test (it builds the wheel; allow time):

        uv run pytest \
          "tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero" \
          -m slow -q

   Expect `1 passed` (or `1 skipped` on a non-POSIX host).

6. Teeth check (Work item 2): perturb one new assertion, re-run step 5, observe
   `1 failed` with the assertion error on the perturbed field (not a build
   error), then revert and re-run, observe `1 passed`. Record in the Decision Log.
   Commit only the reverted (green) file.

7. Run the full gate before committing Work item 1:

        make all

   Expect a green run (all passed; one pre-existing skip permitted).

8. Add the developers-guide paragraph (Work item 3), then:

        make all && make markdownlint && make nixie

   Expect all three green.

## Validation and acceptance

Acceptance is behavioural:

- Running `uv run pytest
  "tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero"
  -m slow` builds and installs the wheel, drives the installed `novel state check`
  over a coherent `working/` tree, and the extended tripwire passes: exit 0, the
  six contract keys in `ENVELOPE_KEY_ORDER`, `command == "novel state"`,
  `schema_version == 1`, `ok: true` mirroring the exit code, the resolved-absolute
  `working_dir`, `result["violations"] == []`, and `str`-typed `messages`.
- A deliberately introduced divergence in one of the new assertions (a wrong
  `command`, a bumped `schema_version`, a reversed key order, or an `ok: false`
  expectation) turns the test red on that assertion, while the rest of the suite
  is untouched (Work item 2 teeth check).
- `make all` is green (all passed; at most the one pre-existing skip).
- `make markdownlint` and `make nixie` are green on the edited
  `docs/developers-guide.md` and this execplan.

Quality criteria (what "done" means):

- Tests: the extended `test_installed_novel_state_check_exits_zero` passes; the
  existing installed e2e and cross-command suites stay green (roadmap §6.3.6
  success criterion).
- Lint/typecheck: `make all` (Ruff, Pylint, `ty`, `interrogate`) green; the
  extended test keeps its module and function docstrings (the docstring is
  broadened to record the new skeleton-identity pins); no helper or fixture is
  added.
- No production source under `novel_ralph_skill/` changed; no new module added;
  no second wheel build introduced.
- Markdown: `make markdownlint` and `make nixie` green.

Quality method (how we check): run `make all`, then `make markdownlint` and
`make nixie`, from the worktree root. The dual review and audit run downstream of
this plan.

## Idempotence and recovery

The extended test is re-runnable without drift: each run copies a throwaway
`working/` tree under a fresh `tmp_path`, and the module-scoped
`installed_novel_state` fixture builds the wheel into a `tmp_path_factory`
directory per module. No state outside `tmp_path` is touched. If the wheel build
fails (e.g. a transient `uv` error), re-run the test; the build is hermetic.
Reverting the branch to `origin/main` discards all changes cleanly, as the task
edits only one existing test and one documentation file.

## Artefacts and notes

Expected machine envelope for the success cell the extended test now pins
(illustrative; `working_dir` is the run's absolute resolved path, redacted here):

    {
      "command": "novel state",
      "schema_version": 1,
      "ok": true,
      "working_dir": "<abs>/working",
      "result": {"violations": []},
      "messages": ["..."]
    }

## Interfaces and dependencies

No new module, fixture, or runner is added. The edit lives entirely inside the
existing `tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
(which keeps its `@pytest.mark.slow`, `@pytest.mark.timeout(180)`, and
POSIX-`skipif` marks and its
`(tmp_path, baseline_tree, single_program_catalogue, installed_novel_state)`
signature). The edit:

- adds three imports to the module's existing import block:
  - `from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION`;
  - `from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES`;
  - `from cross_command_contract import ENVELOPE_KEY_ORDER` (the cross-command
    package's plain-value `typ.Final` constant — not a fixture, so this is not a
    cross-module fixture/value-import breach; it mirrors the in-process key order
    rather than re-spelling it);
- adds skeleton-identity assertions over the already-parsed `envelope`.

`json`, `os`, `pytest`, `from cuprum import sh`, `from cuprum.program import
Program`, `from cuprum.sh import ExecutionContext`, and
`from novel_ralph_skill.contract.exit_codes import ExitCode` are **already**
imported by the module (lines 26-40). The test already consumes
`installed_novel_state` (`tests/installed_binary_fixtures.py`, module-scoped),
`single_program_catalogue` (`tests/conftest.py`), `baseline_tree`
(`tests/corpus_fixtures.py`), and the function-scoped pytest `tmp_path` by name.
No new external dependency is introduced; no production interface changes; no
second wheel build.

## Revision note

Initial draft (2026-06-26, planning agent). Scoped roadmap 6.3.6 as a *new*
installed-boundary success-arm tripwire module.

Round 2 revision (2026-06-26, planning agent), addressing logisphere review r1
(B1). The round-1 draft's central premise — that the installed exit-0 arm "has
never been observed crossing the wheel/venv packaging boundary" — was false:
`tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero`
(lines 307-344) already drives the installed `novel state check` over a coherent
tree and asserts `exit_code == 0` and `ok is True` (design §9 line 893 confirms
"the existing `check` (exit 0) … proofs"). This revision: (1) corrected the
Purpose and Surprises to acknowledge that test; (2) restated the residual gap as
the *unpinned envelope-skeleton identity* over the wheel (key order vs
`ENVELOPE_KEY_ORDER`, `schema_version == 1`, `command == "novel state"`, resolved
absolute `working_dir`, `result["violations"] == []`, `str`-typed `messages` —
none pinned by the existing test); (3) added a Decision Log entry choosing to
*extend the existing exit-0 test in place* over a new module, because a
new module's module-scoped `installed_novel_state` would pay a second full wheel
build for the same command/arm; (4) rewired Risk-1 and the Scaffolding/line-cap
tolerances to measure duplication against `test_installed_novel_state_check_exits_zero`
(the test that actually overlaps), not only the error-arm e2e; and (5) extended
Work item 3 to demarcate the extended test's boundary against both the installed
error-arm e2e (exit 2/3) and the in-process cross-command suite. The locked cuprum
0.1.0 `run_sync(capture=...)` signature remains verified against the installed
wheel; the `working_dir` reconciliation against the in-process `"working"` token
is pinned as the deliberate 6.3.4 behaviour. The optional snapshot is dropped
(advisory A3). No remaining work beyond the three work items.

## Addenda

Lightweight, no-plan corrections folded onto this completed task after the
review and audit of step 6.3 settled. Each runs as a no-review lightweight pass.

- [x] **6.3.6.1 (from review:6.3.6; low).** Make the tautological
  `envelope["ok"] is (result.exit_code == ExitCode.SUCCESS)` assertion in
  `test_installed_novel_state_check_exits_zero` load-bearing or document it as
  intent-only. Once `exit_code == 0` and `ok is True` are already asserted, this
  mapping check cannot fail independently, so it carries documentation value but
  no distinct failure mode. Either add a clarifying comment that it is a
  redundant mapping guard, or cross-arm parameterize it so the mapping can fail
  independently. Scope: one assertion/comment in one test.
- [x] **6.3.6.2 (from audit:6.3.6; medium).** Parameterize the canonical
  `assert_envelope_skeleton` helper with an optional `working_dir` override
  (default `WORKING_DIR_CONSTANT`) and collapse the inline envelope-skeleton
  block re-spelled at `tests/test_novel_state_check.py` lines 363-380 onto a
  single helper call, keeping only the command-specific
  `result["violations"] == []` assertion. The installed identity mirror today
  re-spells the in-process proof's canonical helper inline, so the two halves
  can drift independently — the exact divergence the installed mirror exists to
  catch. Scope: one optional parameter on the shared helper; collapse one inline
  block onto it.
