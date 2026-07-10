# Pin cross-command exit-code and envelope-schema consistency

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: IMPLEMENTED (all six work items committed; fix round 1 made the commit
gate deterministic; `make all` green at HEAD)

## Purpose / big picture

After this change a single cross-command behavioural suite proves that every
one of the harness's commands presents the *same* output contract: the
exit-code to `ok` mapping, the envelope field set and order (`command`,
`schema_version`, `ok`, `working_dir`, `result`, `messages`), each field's
type, and the shape of each error channel (usage to exit 2, state/input to exit
3, actionable finding to exit 4). The harness drives these commands unattended
every turn and gates on their output (`docs/novel-ralph-harness-design.md` §3;
ADR-003). Today that identity is asserted only obliquely: the §1.3.1 contract
tests pin the envelope *helper* in isolation, and the §6.2.1 command-surface
matrix (`tests/test_command_surface_matrix.py`) pins the five **read** commands
across phases but explicitly excludes the **mutators** and asserts each
command's own shape rather than asserting that the shapes are *identical across
commands*. If a sixth command — or a future edit to one of the existing
commands or to a mutator — drifted from the shared envelope or exit-code table,
no single test would fail on the divergence. This task closes that gap.

You can observe success by running the new suite: a single parametrized
pytest-bdd scenario set plus syrupy snapshots that, for every command and every
contract channel, asserts the shared envelope skeleton and exit-code mapping.
The suite must fail if any command drifts. Concretely, after this change
`make test` passes, and a deliberately introduced divergence (for example,
re-ordering the envelope fields for one command, or mapping its usage fault to
exit 1 instead of 2) makes the new suite go red while the rest of the suite is
untouched.

## Constraints

Hard invariants that must hold throughout implementation.

- Do not modify any file in the root/control worktree. Work exclusively in the
  git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-2`.
- Do not change the production contract surface. This is a *verification* task:
  it adds tests (and at most shared test scaffolding and documentation). The
  envelope (`novel_ralph_skill/contract/envelope.py`), the runner
  (`novel_ralph_skill/contract/runner.py`), the exit-code vocabulary
  (`novel_ralph_skill/contract/exit_codes.py`), and the five command
  `build_app()` factories must remain behaviourally unchanged. If a command
  genuinely *diverges* from the contract, that is a defect for a separate task
  — stop and escalate; do not "fix" production code under cover of this test
  task.
- The shared envelope field set and order are fixed by ADR-003 and design §3.1:
  `command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`. The
  exit-code table is fixed by ADR-003 Table 2 and design §3.2: 0 success, 1
  benign negative, 2 usage error, 3 state/input error, 4 actionable finding.
  `ok` is `True` if and only if the code is 0 (design §3.1; `is_ok`). The suite
  asserts these; it does not redefine them.
- The "command" surface under test is the single shipping `novel` multiplexer
  (ADR-007; `novel_ralph_skill/commands/names.py`). The "five commands" the
  roadmap names are its five spaced subcommands: `novel state`, `novel done`,
  `novel compile`, `novel desloppify`, `novel wordcount`. `novel state` is a
  command-group sub-app whose verbs include the read `check` query *and* the
  mutators (`init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`,
  `set-chapters`, and the four gate/drafting mutators); this task's
  contribution over §6.2.1 is to bring the mutator success and refusal
  envelopes into the cross-command identity proof.
- Tests live in the top-level `tests/` tree (AGENTS.md "Python verification and
  testing"); never under package directories or `unittests/`.
- Behavioural tests use `pytest-bdd`; feature files live under `tests/features/`
  and step modules under `tests/steps/` (the established layout). Snapshot
  tests use `syrupy` and must be paired with semantic assertions, never
  snapshot-only (AGENTS.md). Redact every nondeterministic field (timestamps,
  absolute paths) before snapshotting.
- No single code file exceeds 400 lines (AGENTS.md). If a test module would
  exceed it, split by concern or relax the cap only with the same justification
  the existing matrix module records (`tests/test_command_surface_matrix.py`
  lines 74-81).
- All prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` skill.
  External API names (Cyclopts, syrupy, `schema_version`) are quoted verbatim.
- Every `tests/`-tree Python module under `PYTHON_TARGETS` carries a module
  docstring and a docstring on every fixture, helper, and test function (100%
  `interrogate` coverage; AGENTS.md), and raises `AssertionError` directly
  rather than a bare `assert` inside fixture/helper bodies that are not test
  functions, mirroring `tests/installed_binary_fixtures.py`.

## Tolerances (exception triggers)

- Scope: if the change requires touching more than 8 files net, or editing any
  file under `novel_ralph_skill/` (production source), stop and escalate.
- Production divergence: if any command is found to genuinely violate the shared
  contract (a real field-order, field-set, type, or exit-code divergence), stop
  and escalate — that is a defect fix for a separate roadmap task, not part of
  pinning the contract.
- Dependencies: if a new external dependency is required, stop and escalate. The
  suite must use only the already-locked `pytest`, `pytest-bdd` (`>=8.1.0`),
  `hypothesis`, `syrupy`, and `cuprum` (`0.1.0`).
- Iterations: if the new suite still fails after 4 focused attempts to align it
  with the real contract (and the failure is *not* a genuine production
  divergence), stop and escalate.
- Ambiguity: if the cross-command identity assertion cannot be expressed without
  encoding per-command special cases that defeat the "identical contract"
  intent, stop and present the options.

## Risks

    - Risk: Duplicating the §6.2.1 command-surface matrix rather than adding the
      distinct cross-command-identity axis, producing redundant tests that churn
      together.
      Severity: medium
      Likelihood: medium
      Mitigation: Frame this suite around the *identity-across-commands* claim
      (every command yields the same envelope skeleton and the same exit-code to
      ok mapping) and the *mutator* surface §6.2.1 excluded, not around
      per-command per-phase behaviour. Cite the §6.2.1 carried-gap notes
      (`tests/test_command_surface_matrix.py` lines 54-71) in the new module's
      docstring to record the boundary.

    - Risk: A mutator's success `result` is command-specific (design §3.1: a
      mutator names what it changed), so a naive "identical result" assertion is
      wrong. The contract that is identical is the *envelope skeleton and field
      types*, not the `result` contents.
      Severity: medium
      Likelihood: high
      Mitigation: Assert the envelope field set, order, and the *type* of each
      field (`command: str`, `schema_version: int`, `ok: bool`,
      `working_dir: str`, `result: mapping`, `messages: sequence of str`) and the
      exit-code to ok mapping. Snapshot the per-command `result` separately where
      a stable shape exists, paired with semantic assertions. Do not assert that
      two different commands produce the same `result`.

    - Risk: Nondeterministic fields (the `created_at` timestamp `init` stamps,
      any absolute path) churn the snapshots.
      Severity: low
      Likelihood: medium
      Mitigation: Reuse the volatile-field redaction patterns already proven in
      `tests/test_command_surface_matrix.py` (lines 147-159, 310-330) and
      `tests/test_novel_state_mutator_snapshots.py` (lines 35-59).

    - Risk: Driving a mutator changes state on disk, so a parametrized body that
      reuses one tree across commands corrupts later cells.
      Severity: medium
      Likelihood: medium
      Mitigation: Build a fresh `working/` tree per cell under a per-cell
      subdirectory of `tmp_path`, exactly as the matrix `_build_phase_tree`
      helper does (`tests/test_command_surface_matrix.py` lines 234-255), and
      drive in-process through `run` with `monkeypatch.chdir` (auto-reverted,
      xdist-safe).

## Progress

    - [x] Work item 1: Cross-command envelope-shape contract pin (in-process).
      Committed `b6829a0`. Promoted the `drive` seam, `CommandSpec`,
      `build_phase_tree`, and the volatile guard into the registered plugin
      `tests/contract_drive_support.py`; the §6.2.1 matrix consumes them by name
      and its regression run stayed green (135 passed).
    - [x] Work item 2: Cross-command exit-code to ok mapping pin — a Hypothesis
      property over the **pure** synthetic-outcome → `run` → envelope surface,
      plus parametrized example tests over the named constructible (command,
      channel) cells. Committed `04838b1`. Cell table in
      `tests/cross_command_contract/_cells.py`.
    - [x] Work item 3: pytest-bdd cross-command contract scenario suite.
      Committed `38660fe`. Three `Scenario Outline`s over the five-command
      `Examples` table (body skeleton, state arm, usage arm); steps call the
      shared identity helpers.
    - [x] Work item 4: Cross-command error-channel shape pin (usage/state/finding,
      each bound to its concrete constructible cell). Committed `7acd6ef`. Adds
      the nine state-reaching mutators to the state and usage arms.
    - [x] Work item 5: Mutator success/refusal envelope identity pin + snapshots.
      Committed `723a9a8`.
    - [x] Work item 6: Developers-guide note recording the suite's scope and the
      boundary against §6.2.1. Committed `7b5f67e`.

## Surprises & discoveries

    - Observation: Empirically pinned, in-process over the corpus, which exit code
      each command reaches over which tree — the constructible-cell matrix that
      Work items 2 and 4 enumerate. Not every command can be driven into every
      channel.
      Evidence: Driving each `build_app()` through `run` with
      `monkeypatch`-style `chdir` (a throwaway probe script, run from the worktree
      with `PYTHONPATH=tests`) over `working_corpus.PHASE_STATES` and the
      `INCOHERENT_VARIANTS`/em-dash-flood fixtures printed:
      `novel state check` → 0 over every coherent phase, 4 over an
      `incoherent_tree` (e.g. `consecutive-clean-over-target`), 2 on `--nope`,
      3 with no `working/`, and **no** code-1 cell;
      `novel done` → **1** over every coherent phase (the corpus never satisfies
      the done predicate, so **no** code-0 and **no** code-4 cell), 2 on `--nope`,
      3 with no `working/`;
      `novel wordcount` → 0 over every coherent phase only (**no** 1 and **no** 4),
      2 on `--nope`, 3 with no `working/`;
      `novel compile --check` → 0 over `final-pass`/`done`, **3** over the eight
      pre-drafting phases, **4** over `drafting`, 2 on `--nope`, 3 with no
      `working/` (**no** code-1 cell);
      `novel desloppify` → 0 over every coherent phase, **4** over a `drafting`
      tree with an em-dash-flood draft (the `tests/test_desloppify_command.py`
      lines 84-106 construction), 2 on `--nope`, 3 with no `working/` (**no**
      code-1 cell).
      Impact: Work item 2's Hypothesis property runs only on the *pure* surface
      (no disk); the driven channels are asserted as parametrized example tests
      over exactly these named cells, and the unconstructible (command, channel)
      pairs are carried as documented gaps (see the constructible-cell table in
      Context and orientation). This removes the B1/B2 defects the Round 1 review
      raised.

    - Observation: A mutator only reaches the state arm (exit 3) when its argv is
      otherwise *valid*; a missing required keyword-only argument faults at parse
      (exit 2) and masks the state channel.
      Evidence: Probed in-process with no `working/`. `novel state recount`,
      `reconcile`, and `advance-phase` exit 3; but `novel state set-cursor` (its
      `chapter` parameter is keyword-only and required) exits 2 unless invoked as
      `set-cursor --chapter 1`, and `novel state set-chapters` (its `chapters`
      list parameter is required, `novel_state.py` lines 366, 389-390) exits 2
      unless invoked with a valid `--chapters` value. With `set-cursor --chapter 1`
      and no `working/`, the exit is 3 with the shared `ok: false` skeleton.
      Impact: Work item 4 (the mutator state arm) and Work item 5 (refusal arms)
      must drive each mutator with a *complete, valid* argv so the body reaches the
      `working/state.toml` load; otherwise the exit-2 usage fault hides the exit-3
      state channel. Bind each mutator's state-arm argv to a minimal valid form
      (e.g. `["set-cursor", "--chapter", "1"]`), reusing the argvs the existing
      per-mutator suites already construct (`tests/test_novel_state_mutators.py`).

    - Observation: The locked `cuprum` 0.1.0 wheel's `SafeCmd.run_sync` accepts a
      `capture` keyword, whereas the local `/data/leynos/Projects/cuprum` working
      tree (a newer, unreleased revision) replaced it with an
      `output: RunOutputOptions` parameter.
      Evidence: `uv run python -c "import inspect; from cuprum.sh import SafeCmd;
      print(inspect.signature(SafeCmd.run_sync))"` against this repo's `.venv`
      prints `(self, *, capture: bool = True, echo: bool = False, context:
      ExecutionContext | None = None)`; the same module in
      `/data/leynos/Projects/cuprum/cuprum/sh.py` line 441 shows `output:
      RunOutputOptions | None`. `uv.lock` pins `cuprum` to `0.1.0`.
      Impact: This plan pins every cuprum call against the *locked* 0.1.0 API
      (the wheel actually installed), matching the existing e2e modules
      (`.run_sync(context=ExecutionContext(cwd=...), capture=True)`). It does not
      follow the local working-tree signature. This task's primary suite is
      in-process and consumes no cuprum; cuprum is referenced only for the
      optional installed-binary widening discussed under Decision Log, and even
      there it reuses the established fixtures rather than introducing new API.

## Decision log

    - Decision: Scope this task as the *cross-command identity* axis plus the
      *mutator* surface, in-process, distinct from §6.2.1's read-command ×
      phase matrix.
      Rationale: §6.2.1 (`tests/test_command_surface_matrix.py`) already pins the
      five read surfaces across eleven phases and explicitly carries the
      "mutator × phase" and cross-command-identity gaps as documented omissions
      (lines 54-71). The roadmap's 6.3.2 success criterion is a single
      cross-command suite that "fails on any per-command divergence" from the
      shared envelope and exit-code table — an identity claim, not a per-phase
      claim. Adding the mutator success/refusal envelopes to the identity proof
      is the missing coverage.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Primary suite is in-process through
      `novel_ralph_skill.contract.runner.run`, not over a built wheel.
      Rationale: The contract identity (field set/order/types, exit-code mapping,
      error-channel shape) is a property of the shared `run` wrapper and the
      command `build_app()` factories, fully observable in-process. The installed
      boundary is already covered for the error arms by §6.2.10
      (`tests/test_console_scripts_error_arms_e2e.py`), which pins the *complete*
      envelope over the wheel. The in-process suite is fast (no `slow`/`timeout`
      marks, no cuprum), matching the §6.2.1 matrix's drive seam
      (`tests/test_command_surface_matrix.py` lines 39-44).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Express the cross-command suite as one parametrized pytest-bdd
      scenario set plus syrupy snapshots, as the roadmap text requires.
      Rationale: The roadmap names "one parametrized pytest-bdd suite plus syrupy
      snapshots". pytest-bdd 8.1.0 supports a single feature whose scenarios are
      driven over a parametrized command fixture; the repo already uses
      `pytest-bdd` scenarios extensively (`tests/features/`, `tests/steps/`). The
      snapshots pin the redacted per-command envelope skeletons; the scenarios
      assert the identity invariants in steps. The in-code Hypothesis property
      (Work item 2) backs the exit-code mapping over the full code range, as the
      existing `tests/test_contract_properties.py` does.
      Date/Author: 2026-06-26, planning agent.

    - Decision: The only `@given` Hypothesis property in this suite runs on the
      *pure* outcome → `run` → envelope path (a synthetic `CommandOutcome` driven
      through `run` over the shared `wrapper_app` builder, no `tmp_path`, no
      `chdir`); the *driven* (command, channel) cells are asserted as plain,
      table-driven parametrized pytest cases, not under `@given`.
      Rationale: Driving a real command into a real channel needs an on-disk
      `working/` tree (`tmp_path`) and `monkeypatch.chdir`, both function-scoped
      fixtures, which `@given` forbids via `HealthCheck.function_scoped_fixture`.
      The repo's precedent makes this exact split: `tests/test_contract_properties.py`
      lines 49-110 run `@given` on the pure `build_envelope`, while the *driven*
      cases (`test_malformed_invocation_maps_to_two`, `test_state_fault_maps_to_three`,
      lines 130-202) are plain pytest over the synthetic `wrapper_app`, never
      `@given`. The pure property still ranges over every `ExitCode` and every
      `SUBCOMMAND_NAMES` member, so the ok/exit biconditional is proven over the
      full code × command space; the example cells then prove each *real* command
      actually reaches its constructible channels. This resolves Round 1 B1.
      Date/Author: 2026-06-26, planning agent (Round 2).

    - Decision: Enumerate the constructible (command, channel) cells explicitly
      from the empirical probe, bind each to a concrete corpus tree, and mark the
      unconstructible pairs as carried gaps in the suite module docstring exactly
      as `tests/test_command_surface_matrix.py` lines 54-71 and roadmap 6.2.1 do.
      Rationale: The corpus does not let every command reach every channel
      (Surprises): `novel done` never reaches 0 or 4; `novel wordcount` never
      reaches 1 or 4; `novel state check`/`compile`/`desloppify` never reach 1;
      exit 4 is constructible only for `compile --check` (drafting tree),
      `state check` (`incoherent_tree`), and `desloppify` (em-dash-flood draft).
      Driving "each command into each code" blindly would either silently skip
      channels or assert false premises. A named cell table makes the identity
      claim mechanical and the gaps auditable. This resolves Round 1 B2.
      Date/Author: 2026-06-26, planning agent (Round 2).

    - Decision: Commit up front to a test *package* `tests/cross_command_contract/`
      (the suite module split by concern) rather than leaving the split
      conditional. Promote the shared `drive` seam, `_build_phase_tree`,
      `_VOLATILE_PATTERN`, and `_assert_no_volatile_fields` from the matrix module
      into `tests/conftest.py` (the fixture) plus a small shared helper module (the
      pure functions), and re-run the §6.2.1 matrix as an explicit regression gate
      after the promotion, not only `make all`.
      Rationale: Work item 1 (5 commands × 2 modes), Work item 4 (5 × 3 arms), and
      Work item 5 (~10 mutators × success/refusal × snapshots) together exceed the
      400-line module cap; a pre-committed package split avoids a mid-task scramble
      (Round 1 A4). Editing the passing 729-line `test_command_surface_matrix.py`
      to consume the promoted helpers by name is a real change to a passing module,
      so it warrants an explicit `uv run pytest tests/test_command_surface_matrix.py`
      regression run before the work-item commit (Round 1 A5).
      Date/Author: 2026-06-26, planning agent (Round 2).

    - Decision: Do not introduce a new shared catalogue or installed-binary
      fixture. If a single installed-binary identity tripwire is added, reuse the
      module-scoped `installed_novel_state` fixture and the `single_program_-
      catalogue` builder already registered in `tests/conftest.py` and
      `tests/installed_binary_fixtures.py`.
      Rationale: The developers-guide "Shared test scaffolding" rule forbids new
      copies of existing scaffolding and forbids cross-module value imports;
      consumers bind fixtures by name. The locked cuprum 0.1.0 API those fixtures
      use is verified (`ProgramCatalogue(projects=(ProjectSettings(name,
      programs, documentation_locations, noise_rules),))`, `sh.make(program,
      catalogue=)`, `Program(str(absolute_path))`,
      `.run_sync(context=ExecutionContext(cwd=...), capture=True)`,
      `CommandResult.{exit_code,stdout,stderr}`).
      Date/Author: 2026-06-26, planning agent.

    - Decision: Route the envelope-skeleton type checks in
      `tests/cross_command_contract/_identity_assertions.py` through one
      `_require(condition, message)` helper that raises `AssertionError`, rather
      than inline `isinstance(...)`-then-`raise`.
      Rationale: AGENTS.md requires non-`test_*` helper bodies to raise
      `AssertionError` directly (not a bare `assert`). An inline
      `isinstance(...)`-then-`raise AssertionError` trips Ruff `TRY004`, which
      would prefer `TypeError`; but a skeleton breach is a contract violation, not
      a type error, so `AssertionError` is correct. Computing the boolean first and
      passing it to `_require` keeps the call sites free of the flagged shape while
      preserving the contract-assertion intent.
      Date/Author: 2026-06-26, implementing agent.

    - Decision: Share the package-internal identity helpers and cell tables across
      the cross-command modules by a sibling-module runtime import within the
      `tests/cross_command_contract/` package (`from ._identity_assertions import
      …`, `from ._cells import …`), and the `drive` seam by the registered
      `contract_drive_support` plugin.
      Rationale: The developers-guide "Shared test scaffolding" rule forbids
      cross-module *fixture/value* imports between top-level test modules; it does
      not forbid a test *package* sharing its own private assertion helpers by
      runtime import, the package being one cohesive suite. Fixtures are still
      consumed by name (`drive`, `tmp_path`, `snapshot`). This keeps the four
      cross-command modules asserting one identity contract rather than re-spelling
      it, while honouring the fixture-by-name rule.
      Date/Author: 2026-06-26, implementing agent.

## Outcomes & retrospective

Delivered. The `tests/cross_command_contract/` package plus
`tests/features/cross_command_contract.feature` form a single cross-command
suite that fails on any per-command divergence from the shared envelope and
exit-code table, including for the mutators §6.2.1 excluded. `make all` is green
at HEAD (1296 passed, 1 skipped); `make markdownlint`/`make nixie` pass on the
edited `developers-guide.md`. The Work item 1 teeth check confirmed the suite's
bite: reordering `result`/`messages` in `render_machine` turned 10 cells red and
reverting restored green (perturbation not committed).

Findings recorded during implementation:

- `Ruff TRY004` (`type-check-without-type-error`) flags the
  `isinstance(...)`-then-`raise AssertionError` shape in the non-`test_*` helper
  `_identity_assertions.py`. The constraint requires `AssertionError` (not a bare
  `assert`, and not `TypeError`, since an envelope skeleton breach is a contract
  violation, not a type error), so the type checks are routed through one
  `_require(condition, message)` helper that breaks the flagged shape while
  keeping the contract-assertion intent. Decision recorded below.
- `init` with no `working/` exits **0** (it *creates* `working/`), so it is not
  a state-arm cell; the mutator state-arm set is the other nine mutators. `init`'s
  refusal is instead a pre-existing `state.toml` (exit 3).
- `reconcile` is exit 0/4 by design (§3.1): it never refuses an incoherent tree
  with exit 3, so its identity refusal is the shared no-`working/` load fault, not
  a content breach. Recorded in `_mutator_cases.py`.
- `INCOHERENT_VARIANTS` maps each key to a `(spec, violation_name)` pair (the
  `incoherent_tree` fixture unpacks the same shape); the cell builders take the
  first element.
- Pre-existing spurious `mdformat`/`make fmt` reflow churn was present in the
  worktree's tracked `docs/` files (a known recurring issue; the stash list is
  full of "spurious make-fmt mdformat churn" entries). The Work item 6 commit was
  scrubbed to carry **only** the two `developers-guide.md` additions (restored the
  file to HEAD and re-applied the edits), so no unrelated reflow churn was
  committed.

Open issue (resolved in fix round 1) — coderabbit review obtained. The original
`coderabbit review --agent` run stalled in its "summarizing" phase across
several attempts during the implementation session (a parallel `coderabbit`
review in the sibling `roadmap-6-3-1` worktree was contending, and the service
appeared rate-limited/queued). In fix round 1 the review completed
(`coderabbit review --plain`, ~5.5 min in the summarizing phase) and returned
**No findings** over all local changes (committed plus uncommitted) against
`main`.

## Fix round 1 — deterministic commit gate

The dual review returned two blocking findings: `make all` was not reliably
green. Both root causes were pre-existing on `main` (the
`test_reconcile_derivation.py` property is unchanged on this branch), but per
AGENTS.md the commit gate must pass deterministically before merge. Both are now
resolved in commit `733cf33` (two `tests/`/build-tooling files; no production
source touched, preserving the verification-only constraint).

Finding 1 — flaky Hypothesis property
`test_derivation_is_total_and_never_yields_none_on_a_violation` (~1 in 8 under
`pytest -n auto`). Root cause: the property materializes a full corpus working
tree via `build_working_tree` and parses `state.toml` per generated example, so
under xdist I/O contention an example sporadically breaches Hypothesis's default
200ms deadline and raises `DeadlineExceeded`. It carried no `@settings`, unlike
every other filesystem-heavy property in the suite (for example
`tests/test_done_predicate.py:236-240` documents this exact convention).
Confirmed by profiling (≈16ms/example uncontended, but the single-process run is
already ~45ms/example including Hypothesis overhead, so contention easily
crosses 200ms) and by reproducing `DeadlineExceeded` under a tightened deadline
plus simulated contention. Fix: add
`@settings(max_examples=100, deadline=None)`, matching the suite convention; the
strategy space (unique lists of 1-4 of six basenames) is small, so 100 examples
retains the search strength. Verified by 40 consecutive `-n auto` runs of the
single test (0 failures) and a full green `make all`.

Finding 2 — wide first-run envelope field-order failure (101 tests, `messages`
before `result`) despite a statically `result`-then-`messages` `render_machine`.
Root cause confirmed and reproduced deterministically: a stale,
timestamp-validated `__pycache__/envelope.cpython-314.pyc` in the tracked tree
whose embedded source mtime matches the current source (the exact condition git
worktree/checkout/rebase creates, since git does not preserve content-correlated
mtimes) makes CPython trust the old bytecode under the editable install. Staging
such a stale `envelope.pyc` and stamping the restored good source to its
embedded mtime reproduced the `messages`-before-`result` order on import;
purging the cache restored the correct order. Fix: the `build` target now purges
tracked-tree bytecode caches after `uv sync` (scoped to `$(PYTHON_TARGETS)`,
never `.venv` or the uv cache) via the `PURGE_TREE_BYTECODE` macro, so `test`
(which depends on `build`) always imports the editable source as written.
Verified by re-staging the stale-pyc condition, running the purge, and
confirming the import order is correct.

Gate at fix-round-1 HEAD: `make all` green (1296 passed, 1 skipped);
`coderabbit review` returned No findings. The edited Markdown (this execplan) is
re-checked with `make markdownlint`/`make nixie` before the documentation
commit.

## Context and orientation

The harness is a Python package, `novel_ralph_skill`, that ships a single
`novel` console-script multiplexer (ADR-007). Each invocation emits one JSON
"envelope" on stdout (or a human rendering under `--human`) and exits with a
contract code. Read the following before starting; they are the source of truth.

- `docs/adr-003-shared-interface-contract.md` — the shared envelope, the
  four-flag Cyclopts construction contract (Table 3), and the disambiguated
  five-code exit table (Table 2). This is the contract this task pins.
- `docs/novel-ralph-harness-design.md` §3 (lines 131-264) — the same contract
  in narrative form: §3.1 the envelope and output modes, §3.2 the exit codes,
  §3.3 command/query segregation (why a mutator's `result` differs from a
  checker's), §3.4 atomic writes. §2.3 (lines 106-129) — the verification scope
  and the `command × output-mode × phase` surface. §9 (the verification
  strategy) — "snapshot tests pin the machine-mode JSON contract per command,
  semantic assertions cover the phase-dependent branches, and the human mode is
  asserted for presence rather than pinned".
- `docs/developers-guide.md` "Shared test scaffolding" (lines 20-70) — the
  fixture-by-name rule, the `installed_novel_state` and
  `single_program_catalogue` fixtures, and the 400-line cap rationale.
- `docs/scripting-standards.md` — the atomic-write and POSIX conventions the
  mutators follow.
- `AGENTS.md` — the quality gates, the testing rules (pytest + pytest-bdd,
  snapshots paired with semantic assertions, redact nondeterministic fields,
  property tests for invariants), and the Oxford-spelling convention.

Key production files (read-only for this task):

- `novel_ralph_skill/contract/envelope.py` — `Envelope`, `build_envelope`
  (derives `ok` from the code; validates `command` against
  `ENVELOPE_COMMAND_NAMES`), `render_machine` (the fixed field order),
  `render_human`, and `ENVELOPE_SCHEMA_VERSION = 1`.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode` (IntEnum: SUCCESS 0,
  BENIGN_NEGATIVE 1, USAGE_ERROR 2, STATE_ERROR 3, ACTIONABLE_FINDING 4) and
  `is_ok`.
- `novel_ralph_skill/contract/runner.py` — `run` (the shared seam owning every
  `sys.exit` and envelope emission), `RunContext`, `CommandOutcome`,
  `StateInputError`, `make_contract_app`, `parse_global_flags`.
- `novel_ralph_skill/commands/names.py` — `SUBCOMMAND_NAMES` (the five spaced
  names), `ENVELOPE_COMMAND_NAMES`, `MULTIPLEXER_NAME`.
- `novel_ralph_skill/commands/novel_state.py`,
  `novel_ralph_skill/commands/_novel_done.py`,
  `novel_ralph_skill/commands/_compile.py`,
  `novel_ralph_skill/commands/_desloppify.py`,
  `novel_ralph_skill/commands/_wordcount.py` — the five `build_app()` factories.
  `novel_state.build_app()` registers `check` plus all mutators.

Key existing tests to model on (read before writing new ones):

- `tests/test_command_surface_matrix.py` — the §6.2.1 read-command × phase
  matrix. Reuse its `_build_phase_tree`, `drive` fixture,
  `_assert_no_volatile- _fields`, and `_VOLATILE_PATTERN`; do not duplicate
  them — extract into `tests/conftest.py` if shared (see Work item 1). Its
  carried-gap section (lines 54-71) names exactly what this task adds.
- `tests/test_contract_properties.py` — the §1.3.1 ok/exit-code Hypothesis
  properties over the envelope *helper*. Work item 2 lifts the same
  biconditional to the *driven command* surface.
- `tests/test_contract_envelope_snapshots.py` — per-code envelope-helper
  snapshots. Work item 1's snapshots are the per-command analogue.
- `tests/test_novel_state_mutator_snapshots.py` — the per-mutator
  success/refusal
  envelope snapshots and the `_normalise` timestamp redaction. Work item 5
  reuses this redaction.
- `tests/test_console_scripts_error_arms_e2e.py` and
  `tests/installed_binary_fixtures.py` — the installed error-arm boundary proof
  and the cuprum fixtures, for the optional installed tripwire only.
- `working_corpus` (`tests/working_corpus/`) — `PHASE_ORDER`, `PHASE_STATES`,
  `build_working_tree`; the in-process trees every cell is built over.

Terms:

- "Envelope" — the six-field JSON object every command emits (design §3.1).
- "Envelope skeleton" — the envelope with its command-specific `result` and
  `messages` redacted, leaving only the contract-fixed fields, set, order, and
  types.
- "Contract channel" / "error channel" — one of the five exit-code outcomes:
  success (0), benign negative (1), usage error (2), state/input error (3),
  actionable finding (4) (design §3.2).
- "Checker" / "mutator" — read-only query versus state-writing command (design
  §3.3). A checker reports `result.violations`; a mutator reports what it
  changed and never echoes the checker read shape.
- "Drive in-process" — call `run(build_app(), argv, RunContext(...))` and catch
  its `SystemExit`, capturing stdout, rather than spawning a subprocess.

### Constructible (command, channel) cell table

This table is the spine of Work items 2, 4, and 5. It records, per command and
per exit-code channel, the concrete tree that constructs that cell, and marks
the channels the corpus cannot reach for that command as **carried gaps** (the
roadmap 6.2.1 and `tests/test_command_surface_matrix.py` discipline of carrying
combinatorial gaps "knowingly rather than silently", design §9 lines 819-821).
The cells are empirically verified (see Surprises & discoveries); the suite
must assert exactly these cells and must *not* default to a coherent
`PHASE_STATES` tree for the exit-4 channel, where most commands cannot reach it.

Channel legend: 0 success, 1 benign negative, 2 usage, 3 state/input, 4
actionable finding (design §3.2; ADR-003 Table 2).

    command            | 0 (success)        | 1 (benign)  | 2 (usage)  | 3 (state)     | 4 (finding)
    -------------------|--------------------|-------------|------------|---------------|------------------------
    novel state check  | any coherent phase | GAP         | --nope     | no working/   | incoherent_tree
    novel done         | GAP                | any phase   | --nope     | no working/   | GAP
    novel wordcount    | any coherent phase | GAP         | --nope     | no working/   | GAP
    novel compile      | final-pass / done  | GAP         | --nope     | pre-drafting* | drafting tree
    novel desloppify   | any coherent phase | GAP         | --nope     | no working/   | em-dash-flood draft

Notes on the cells:

- `novel state check` exit 4: build an `incoherent_tree` variant (the
  `incoherent_tree` fixture, e.g. `"consecutive-clean-over-target"`,
  `tests/test_novel_state_check.py` lines 165-179), not a coherent
  `PHASE_STATES` tree (which exits 0).
- `novel done` reaches **only** exit 1 over every coherent phase (the corpus
  never satisfies the full done predicate, confirmed by the §6.2.1 matrix
  docstring and the probe). Its 0 and 4 channels are **carried gaps** for this
  in-process suite; only `novel done` exercises the benign-negative (1) channel
  here, so it is the suite's sole code-1 witness.
- `novel wordcount` reaches **only** exit 0 over coherent phases plus the two
  shared diagnostic arms (2, 3). Its 1 and 4 channels are **carried gaps**.
- `novel compile --check` exit 3 is the *body-produced* state arm over the eight
  pre-drafting phases (a real exit-3 cell distinct from the shared "no
  `working/`" state arm marked `*`); exit 4 is the `drafting` tree; exits 0 are
  `final-pass`/`done`. Its benign-negative (1) channel is a **carried gap**.
- `novel desloppify` exit 4: build a `drafting` tree, then overwrite the
  lowest-numbered chapter's `draft.md` with an em-dash flood and clear the
  other drafts, exactly the `tests/test_desloppify_command.py` lines 84-106
  construction. A coherent `PHASE_STATES` tree exits 0. Its 1 channel is a
  **carried gap**.
- The usage (2) and state (3) arms are command-agnostic: the `--nope` unknown
  option faults at parse (exit 2) and an absent `working/` faults at load (exit
  3) identically for all five commands (verified by the probe), so they are the
  cross-command-*identity* arms Work item 4 pins.

The exit-4 channel is therefore constructible for exactly three commands; the
suite carries the `done`/`wordcount` exit-4 cells and every command's exit-1
cell (other than `done`'s) as documented gaps, recorded in the suite module
docstring.

## Plan of work

The work proceeds in six small, independently committable items. Each adds
tests only (Work item 6 adds a documentation paragraph). Each ends with the
project gate.

Establish a failing-first discipline per AGENTS.md: where a work item adds a
genuinely new assertion, first run the new test to confirm it is collected and
exercises the real path, then confirm it passes against the real contract.
Where an item is a *tripwire* (it should already pass because the contract
holds), prove its teeth by temporarily perturbing the contract assertion
locally and confirming the test goes red, then revert the perturbation — record
this in the Decision Log, do not commit the perturbation.

### Work item 1: Cross-command envelope-shape contract pin (in-process)

Implements ADR-003 (envelope field set and order) and design §3.1, §9. Create
the test *package* `tests/cross_command_contract/` (committed up front, not
conditionally — see the Decision Log; the combined WI1/WI4/WI5 surface exceeds
the 400-line module cap). In this item add
`tests/cross_command_contract/test_envelope_shape.py`, which drives each of the
five spaced commands in-process through `run` over a representative coherent
`working/` tree and, for each, asserts the envelope:

- carries exactly the six keys `command`, `schema_version`, `ok`, `working_dir`,
  `result`, `messages` and in that order — `render_machine` emits `result`
  **before** `messages` (`novel_ralph_skill/contract/envelope.py`; ADR-003) —
  asserting the ordered key list from the parsed machine JSON, which preserves
  `render_machine`'s insertion order;
- `command` equals the command's spaced name and is a member of
  `ENVELOPE_COMMAND_NAMES`;
- `schema_version == ENVELOPE_SCHEMA_VERSION` (1);
- `ok` is a `bool` and equals `(code == ExitCode.SUCCESS)`;
- `working_dir == "working"` (the fixed constant);
- `result` is a mapping; `messages` is a sequence whose every element is a
  `str`.

Cross each command with both output modes over a *body-producing* invocation:
machine mode parses and asserts the key order and types; human mode asserts
presence (non-empty, names the command) per design §9 — never byte-pinned. Do
**not** drive `--help`/`--version`: `runner.run` exits 0 with **no envelope**
on those arms (`novel_ralph_skill/contract/runner.py`; review A2), so the
"every invocation emits the six-field envelope" assertion is deliberately
scoped to the body-producing and the two diagnostic (usage/state) arms, never
the help/version carve-out.

Snapshot the redacted machine envelope per command (one `.ambr` block per
command), paired with the semantic assertions above so the snapshot is not the
only guard (AGENTS.md). Redact `result` and `messages` to fixed tokens before
snapshotting so the snapshot pins only the contract-fixed skeleton and cannot
churn on a command's payload wording; the per-command `result` is pinned
separately in Work items 4/5 where its shape is stable.

Refactoring: the matrix's `_build_phase_tree`, the `drive` fixture, the
`_VOLATILE_PATTERN`, and `_assert_no_volatile_fields` are reused here. Per the
AGENTS.md abstraction policy and the developers-guide "Shared test scaffolding"
rule, first sweep for the existing helper; promote the `drive` seam to
`tests/conftest.py` as a fixture and the pure functions (`_build_phase_tree`,
`_VOLATILE_PATTERN`, `_assert_no_volatile_fields`) to a small shared helper
module (e.g. `tests/contract_drive_support.py`, registered via `pytest_plugins`
if it carries fixtures, exactly as `installed_binary_fixtures.py` is
registered). Update `tests/test_command_surface_matrix.py` to consume the
promoted versions by name, and record the promotion in the Decision Log. After
the promotion, re-run the §6.2.1 matrix as an explicit regression gate —
`uv run pytest tests/test_command_surface_matrix.py` — before the work-item
commit, in addition to `make all` (review A5). If promotion would push
`conftest.py` past 400 lines, keep the fixture in the registered plugin module
rather than in `conftest.py`.

Docs to read for this item: ADR-003 (Decision outcome, Table 2); design §3.1,
§9; `tests/test_command_surface_matrix.py` (drive seam, redaction);
`tests/test_contract_envelope_snapshots.py` (snapshot pairing). Skills to load:
`python-router` then `python-testing` (fixture scopes, parametrization,
snapshot/approval tests) and `en-gb-oxendict` for prose.

Tests added: per-command machine-envelope skeleton assertions + snapshots
(syrupy), per-command human-mode presence assertions. Validation: `make all`.

### Work item 2: Cross-command exit-code to ok mapping pin

Implements ADR-003 Table 2 and design §3.2 ("`ok` mirrors the exit code"). This
item has **two distinct parts** with different mechanisms; do not conflate them.

**Part A — the pure Hypothesis property (no disk).** Add
`tests/cross_command_contract/test_ok_exit_property.py` with one `@given`
property that drives a *synthetic* `CommandOutcome` through `run` and parses
the emitted envelope, asserting `ok` is `True` if and only if the exit code is
0, sampling `code` over `st.sampled_from(list(ExitCode))` and `command` over
`st.sampled_from(list(SUBCOMMAND_NAMES))`. This runs entirely in-process with
**no** `tmp_path` and **no** `monkeypatch.chdir`: the synthetic outcome is
returned by a builder modelled on the existing `wrapper_app` conftest fixture
(`tests/conftest.py` lines 309-350), which constructs a run-configured app via
`make_contract_app` and whose `act` body returns the supplied `CommandOutcome`
or raises `StateInputError`. Because the only inputs are strategy-drawn values
and no function-scoped fixture is taken, the property obeys
`HealthCheck.function_scoped_fixture` exactly as `test_contract_properties.py`
lines 49-110 do. This proves the ok/exit biconditional over the *full* code ×
command space on the real `run` seam (a strict superset of the §1.3.1 property,
which used `build_envelope` directly rather than driving `run`).

> The roadmap groups codes as "0/1 → benign, 2/3/4 → ok:false"; that grouping is
> the harness *response* class (loop versus stop), **not** the `ok` field. The
> contract is `ok` true **iff** the code is 0, so benign-negative (code 1) is
> `ok: false`. Assert the iff, and add a one-line comment so a future reader
> does
> not "correct" the suite to make code 1 `ok: true` (review A6).

**Part B — the driven example cells (plain pytest, disk allowed).** Add
table-driven parametrized tests (plain `@pytest.mark.parametrize`, **not**
`@given`, so function-scoped `tmp_path` and the `drive` fixture are permitted)
that drive each *real* command into each of its **constructible** channels from
the cell table in Context and orientation, and assert the (code, ok) pair: for
each named cell, the captured exit code equals the channel's code and the
parsed envelope `ok` is `(code == 0)`. The parametrize list enumerates exactly
the constructible cells — `state check` {0, 2, 3, 4}, `done` {1, 2, 3},
`wordcount` {0, 2, 3}, `compile --check` {0, 3, 4}, `desloppify` {0, 2, 3, 4} —
and the test ids name the carried gaps so a reviewer sees which (command,
channel) pairs are *deliberately* absent (per the cell table). A small in-test
mapping binds each cell to its tree-builder (coherent phase, `incoherent_tree`,
em-dash flood, `--nope`, no-`working/`), reusing the promoted `drive` fixture
and `_build_phase_tree`.

This split is the Round 1 B1/B2 resolution: the property stays on the pure
surface (B1), and the driven assertions are enumerated, constructible cells
with the gaps marked (B2), rather than a `@given` that tries and fails to take
function-scoped fixtures, or a blind "each command into each code" that asserts
unreachable channels.

Docs to read: design §3.2; ADR-003 ("Technical requirements", Table 2);
`tests/test_contract_properties.py` (the pure-property vs driven-example split,
lines 49-110 and 130-202); `tests/conftest.py` `wrapper_app` (lines 309-350).
Skills to load: `python-router` then `python-verification` to confirm
Hypothesis is the right adversary for Part A (an invariant over a range of
codes/commands on the pure surface), then `hypothesis` for the strategy design
and the function-scoped-fixture trap.

Tests added: the pure ok/exit `@given` property (Part A); the parametrized
driven (command, channel) cell tests over the constructible cells (Part B).
Validation: `make all`.

### Work item 3: pytest-bdd cross-command contract scenario suite

Implements the roadmap's literal requirement ("one parametrized pytest-bdd
suite") and design §9. Add a feature file
`tests/features/cross_command_contract.feature` and a step module
`tests/steps/cross_command_contract_steps.py`. Write a small set of scenarios,
each parametrized over the command surface via a `Scenario Outline` with an
`Examples` table of the five spaced command names (and, where a scenario covers
a channel, the channel):

- "every command emits the shared envelope skeleton" — given a coherent
  `working/` tree, when the command is driven, then the envelope carries the
  six contract fields in order with the correct types and
  `working_dir == "working"`.
- "ok mirrors the exit code for every command" — then `ok` is true iff the exit
  code is 0.
- "each error channel has the same shape across commands" — given the cwd has no
  `working/`, when the command is driven, then it exits 3 with the `ok: false`
  skeleton and an empty `result` and a non-blank message (the state channel);
  and given an unknown option, then it exits 2 with the same skeleton (the
  usage channel). Use **only** the two command-agnostic arms (usage, state)
  here: the cell table shows both are constructible for all five commands, so
  the `Examples` table is the full five-command list. Do **not** add an exit-4
  row to this cross-command outline — exit 4 is constructible for only three of
  the five commands (cell table), so an exit-4 assertion belongs in Work item
  4's per-command-bound tests, not a five-row outline that would assert an
  unreachable channel for `done`/`wordcount`.

The step module reuses the in-process `drive` seam (promoted in Work item 1)
and the redaction helpers. Keep step text declarative and the bindings thin:
the heavy assertions are the shared helpers, so the scenarios read as the
contract in prose. Confirm `pytest-bdd` `Scenario Outline` parametrization
collects one test per command (the repo pins `pytest-bdd>=8.1.0`; the existing
scenarios under `tests/features/` are the model). The new scenarios are the
human-readable face of Work items 1, 2, and 4; they must not silently diverge
from those assertions, so the steps call the same helpers.

Docs to read: design §9; `docs/developers-guide.md` (pytest-bdd usage, lines
177-180); existing `tests/features/*.feature` and `tests/steps/*_steps.py` for
the `scenarios(...)`/`@given`/`@when`/`@then` layout. Skills to load:
`python-router` then `python-testing` (the pytest-bdd plugin section).

Tests added: the parametrized scenario suite (one feature, several outlines).
Validation: `make all`.

### Work item 4: Cross-command error-channel shape pin

Implements design §3.2 and ADR-003 Table 2 (the usage/state/finding channels)
and ADR-003 §3.1 (the `--human` stamp reaches the body-less arms). Add
`tests/cross_command_contract/test_error_channels.py`.

For each of the five commands, drive the **two command-agnostic diagnostic
arms** in-process — the usage arm (an unknown `--nope` option, exit 2,
`CycloptsError`) and the state arm (no `working/`, exit 3, `StateInputError`) —
and assert that, with the variable `messages` field redacted, the envelope
skeleton is *identical* across all five commands for each arm: `ok: false`,
empty `result`, the six fields in order (`result` before `messages`),
`schema_version == 1`, `working_dir == "working"`. The probe confirms all five
commands reach exit 2 on `--nope` and exit 3 with no `working/`, so these arms
are fully cross-command (the only varying datum is the redacted `command`
string and `messages`). These are body-less diagnostic arms, **not** the
help/version carve-out, which `run` exits 0 with no envelope (review A2); the
suite never drives help/version.

For the **actionable-finding arm (exit 4)**, bind each *constructible* command
to its concrete tree from the cell table; do **not** default to a coherent
`PHASE_STATES` tree (where only `compile` reaches 4, over `drafting`):

- `novel compile --check` → a `drafting` tree (`_build_phase_tree("drafting")`),
  which diverges with exit 4;
- `novel state check` → an `incoherent_tree` variant (e.g.
  `"consecutive-clean-over-target"`), which finds violations with exit 4;
- `novel desloppify` → a `drafting` tree with the lowest-numbered chapter's
  `draft.md` overwritten with an em-dash flood and the other drafts cleared (the
  `tests/test_desloppify_command.py` lines 84-106 construction), exit 4;
- `novel done` and `novel wordcount` have **no** exit-4 arm — mark these as
  carried gaps in the test ids and the module docstring, matching the cell
  table.

For the exit-4 cells the `result` is command-specific and **not** empty (it
carries `violations`), so assert the *skeleton and field types* identity (six
fields in order, `schema_version`, `working_dir`, `ok: false`) across the three
constructible commands, and snapshot each command's `result` separately (paired
with semantic assertions), never asserting two commands' `result` equal. Assert
the message is non-blank for every arm (a fault yields a message, not a
traceback — design §10). Cross both output modes (machine equality on the
skeleton; human presence).

This is the cross-command *identity* form of the §6.2.8 per-read-command error
arms: §6.2.8 crosses the arms with the five *read* surfaces and asserts each
command's skeleton; this item asserts the skeletons are *equal across commands*
(the per-command difference reduces to the redacted `command` string), and adds
the mutator subcommands to the state and usage arms.

When driving a mutator's **state arm** (no `working/`, exit 3), use a
*complete, valid* argv so the body reaches the `working/state.toml` load: a
mutator with a missing required keyword-only argument faults at parse (exit 2)
and masks the state channel (Surprises & discoveries). Bind each mutator's
state-arm argv to a minimal valid form (e.g. `["set-cursor", "--chapter", "1"]`,
`["set-chapters", "--chapters", "<valid>"]`), taking the argvs from the
existing per-mutator suites (`tests/test_novel_state_mutators.py`). The **usage
arm** for the mutators appends `--nope` to a valid argv, exactly as for the
read commands.

Reuse the matrix `_ErrorArm`/`_ErrorCell` shapes
(`tests/test_command_surface_matrix.py` lines 178-231) and its
`_drive_error_cell` precedent (lines 384-421) rather than re-inventing them; if
shared, promote them with Work item 1's helpers.

Docs to read: design §3.2, §10; ADR-003 §3.1, Table 2;
`tests/test_command_surface_matrix.py` (error-arm cells);
`tests/test_console_scripts_error_arms_e2e.py` (the installed analogue's
full-envelope equality). Skills to load: `python-router` then `python-testing`.

Tests added: per-command × per-arm machine skeleton-equality assertions and
human-presence assertions; the actionable-finding arm where constructible.
Validation: `make all`.

### Work item 5: Mutator success/refusal envelope identity pin + snapshots

Implements design §3.1 (a mutator's success `result` names what it changed; a
refusal carries no `result`) and §3.3 (command/query segregation). This is the
coverage §6.2.1 explicitly carried as a gap (its module docstring, lines
54-61). Add `tests/cross_command_contract/test_mutator_identity.py`.

For each `novel state` mutator (`init`, `set-cursor`, `advance-phase`,
`recount`, `reconcile`, `set-chapters`, and the four gate/drafting mutators
registered by `_gate_drafting_mutators.register_gate_drafting_commands`), drive
its success path and at least one refusal path in-process over a fresh per-cell
tree and assert:

- the *envelope skeleton* (six fields, order, types, `working_dir`,
  `schema_version`) is identical to every other command's — the cross-command
  identity claim;
- the success path exits 0 with `ok: true` and a `result` mapping (its contents
  are command-specific and snapshotted, not asserted equal across commands);
- the refusal path (an incoherent cursor, a skipped phase, a pre-existing
  `state.toml` for `init`) exits 3 with `ok: false`, an empty `result`, and a
  non-blank message — the same state-channel shape every command shares.

Snapshot the redacted success and refusal envelopes per mutator (reusing the
`_normalise` timestamp redaction from
`tests/test_novel_state_mutator_snapshots.py`), paired with the semantic
exit-code/`ok` assertions. Build each mutator's input tree from
`working_corpus` phase states (`PHASE_STATES`) at a phase where the mutator is
coherent; for `advance-phase` refusal and `set-cursor` refusal, reuse the
refusal scenarios the existing per-mutator suites already construct
(`tests/features/advance_phase_refusal.feature`,
`tests/test_novel_state_mutators.py`) so the tree shapes are the proven ones.

Do not assert two different mutators produce the same `result`; that would
contradict §3.1/§3.3. Assert only that the *skeleton and field types* are
identical and that the success/refusal *exit-code-to-ok mapping* is identical.

Docs to read: design §3.1 (mutator vs checker result), §3.3, §3.4; ADR-003
Table 2; `tests/test_novel_state_mutator_snapshots.py`;
`tests/test_novel_state_mutators.py`. Skills to load: `python-router` then
`python-testing`; consult `crosshair`/`mutmut` only if asked to harden a
specific mutator's refusal predicate (out of scope here unless escalated).

Tests added: per-mutator success/refusal envelope skeleton-identity assertions
plus snapshots. Validation: `make all`.

### Work item 6: Developers-guide note recording the suite's scope

Implements the AGENTS.md "Documentation maintenance" rule (record internal
conventions in the developers' guide) and the abstraction-policy requirement to
document a new shared abstraction's scope. Add a short paragraph to
`docs/developers-guide.md` (in or beside the "Shared test scaffolding" section)
naming the `tests/cross_command_contract/` package and
`tests/features/cross_command_contract.feature` as the single home for the
cross-command envelope-and-exit-code identity proof, stating what it pins (the
shared skeleton, the ok/exit mapping, and the error-channel shapes across all
five commands including the mutators), and recording the boundary against
§6.2.1's read-command × phase matrix so a future contributor does not duplicate
either. Record the constructible-cell discipline too: exit 4 is constructible
for only `state check`, `compile --check`, and `desloppify`, so the `done`/
`wordcount` exit-4 cells and every command's benign-negative (1) cell except
`done`'s are carried as documented gaps rather than asserted. If Work item 1
promoted any helper to `conftest.py`/a plugin, record it in the same "Shared
test scaffolding" list.

Docs to read: `docs/developers-guide.md` "Shared test scaffolding";
`docs/documentation-style-guide.md`. Skills to load: `en-gb-oxendict`.

Validation: `make all`, then `make markdownlint` and `make nixie` (Markdown
changed).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-2`.

1. Confirm you are on the task branch:

        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-2 \
          branch --show-current

   Expect `roadmap-6-3-2`.

2. For each work item, write the test(s), then run the focused module first to
   see it collected and exercising the real path. For example, after Work item
   1:

        uv run pytest -v tests/cross_command_contract/test_envelope_shape.py

   Expect the new cells to pass against the real contract. When a snapshot is
   first written, generate it with
   `uv run pytest --snapshot-update tests/cross_command_contract/`, then review
   the `.ambr` diff and re-run without the flag to confirm it is stable.

   After Work item 1 promotes the shared `drive`/tree helpers and edits
   `tests/test_command_surface_matrix.py` to consume them by name, run the
   §6.2.1 matrix as an explicit regression gate before that commit:

        uv run pytest tests/test_command_surface_matrix.py

   Expect it to stay green (the promotion is behaviour-preserving).

3. Run the full gate before each commit:

        make all

   Expect formatting, lint (`ruff`, `interrogate` 100%, Pylint), typecheck
   (`ty`), and the full `pytest -n` run to pass.

4. For the documentation commit (Work item 6) additionally run:

        make markdownlint
        make nixie

   Expect both to pass on the edited Markdown.

5. Commit each work item separately with an imperative en-GB subject (for
   example, "Pin cross-command envelope skeleton across all five commands"),
   only after its gate passes. Branch is already a task branch; do not push or
   open a PR unless asked.

## Validation and acceptance

Acceptance is behaviour a reviewer can verify:

- Running `make test` (or `make all`) passes with the new suite collected.
- The new suite asserts, for every one of the five spaced commands, that the
  machine envelope carries exactly `command`, `schema_version`, `ok`,
  `working_dir`, `result`, `messages` in that order, with the contract types,
  and that `ok` is true iff the exit code is 0.
- The new suite asserts the usage (2) and state (3) channels share one envelope
  skeleton across all five commands, with a non-blank message and no traceback,
  and asserts the actionable-finding (4) skeleton across the three commands
  that can reach it (`state check`, `compile --check`, `desloppify`), with the
  `done`/`wordcount` exit-4 cells and the non-`done` exit-1 cells carried as
  documented gaps in the cell table — not silently skipped.
- The exit-code property runs `@given` only on the pure synthetic-outcome →
  `run` → envelope surface (no disk, no `chdir`), and the *driven* (command,
  channel) cells are asserted as plain parametrized pytest over the named
  constructible cells; a reviewer can confirm no `@given` test takes a
  function-scoped fixture.
- The new suite asserts the `novel state` mutators' success and refusal
  envelopes share that same skeleton (with command-specific `result` contents
  snapshotted separately).
- Divergence proof: temporarily editing `render_machine`
  (`novel_ralph_skill/contract/envelope.py`) to reorder two envelope fields, or
  editing one command's `build_app` outcome to map a usage fault to a different
  code, makes the new suite fail; reverting restores green. (This is a manual
  teeth check; do not commit the perturbation.)

Quality criteria (what "done" means):

- Tests: `make test` passes; the new cross-command suite fails before the
  identity assertions exist and passes after; the divergence teeth check goes
  red under a perturbation.
- Lint/typecheck: `make check-fmt`, `make lint`, `make typecheck` pass
  (`ruff format --check`, `ruff check`, `interrogate` at 100%, the Pylint
  runner, `ty check`).
- Markdown (Work item 6): `make markdownlint` and `make nixie` pass.
- Security: `make audit` (`pip-audit`) passes; no new dependency is added.

Quality method (how we check): run `make all` (and `make markdownlint` /
`make nixie` for the docs commit) before each commit; only commit on green.

## Idempotence and recovery

Every step adds test files and at most promotes a shared fixture; nothing is
destructive. The in-process driver uses `monkeypatch.chdir` (auto-reverted) and
builds each tree under a per-cell `tmp_path` subdirectory, so re-running the
suite is safe and order-independent. If a snapshot churns, re-review the diff:
a real contract change is a finding to escalate (per the production-divergence
tolerance), not a snapshot to bless. To recover from a half-written work item,
discard the uncommitted test file and re-run `make all` to confirm the tree is
green before retrying.

## Artefacts and notes

The shared contract under test, for reference (design §3.1; ADR-003):

        {
          "command": "novel done",
          "schema_version": 1,
          "ok": false,
          "working_dir": "working",
          "result": { "…": "command-specific" },
          "messages": ["compiled.md diverges from chapter drafts"]
        }

The exit-code table under test (ADR-003 Table 2; design §3.2): 0 success, 1
benign negative, 2 usage error, 3 state/input error, 4 actionable finding; `ok`
true iff 0.

## Interfaces and dependencies

The suite consumes, by stable name and unchanged:

- `novel_ralph_skill.contract.runner.run`, `RunContext`, `CommandOutcome`,
  `StateInputError` — the in-process drive seam.
- `novel_ralph_skill.contract.exit_codes.ExitCode`, `is_ok`.
- `novel_ralph_skill.contract.envelope.ENVELOPE_SCHEMA_VERSION`,
  `render_machine`/`render_human` (indirectly via `run`).
- `novel_ralph_skill.commands.names.SUBCOMMAND_NAMES`,
  `ENVELOPE_COMMAND_NAMES`.
- Each command's `build_app` under `novel_ralph_skill.commands`
  (`novel_state`, `_novel_done`, `_compile`, `_desloppify`, `_wordcount`).
- `working_corpus.{PHASE_ORDER, PHASE_STATES, build_working_tree}`.
- `pytest`, `pytest-bdd` (`>=8.1.0`), `hypothesis`, `syrupy` — all already
  locked.

If (and only if) an installed-binary identity tripwire is added, it consumes
the already-registered `installed_novel_state` (module-scoped) and
`single_program_catalogue` fixtures, and the locked cuprum 0.1.0 API verified
above: `cuprum.ProgramCatalogue`,
`cuprum.ProjectSettings(name, programs, documentation_locations, noise_rules)`,
`cuprum.program.Program` (a `NewType` over `str`, so `Program(str(path))`),
`cuprum.sh.make(program, catalogue=)`, `cuprum.sh.ExecutionContext(cwd=...)`,
`SafeCmd.run_sync(context=..., capture= True)`, and
`CommandResult.{exit_code, stdout, stderr}`. No new cuprum API is introduced.

## Revision note

Initial draft (2026-06-26). Decomposes roadmap task 6.3.2 into six atomic,
gate-passable work items: a cross-command envelope-skeleton pin, an ok/exit
mapping property pin, a parametrized pytest-bdd scenario suite, an
error-channel-shape identity pin, a mutator success/refusal identity pin with
snapshots, and a developers-guide scope note. Pins the suite's mechanism to the
in-process `run` seam and the §6.2.1 matrix precedents, scoping it as the
cross-command *identity* axis plus the *mutator* surface §6.2.1 excluded.
Verified the locked cuprum 0.1.0 API (used only for an optional installed
tripwire) against the installed wheel, noting the divergence from the local
cuprum working tree. No production source changes; verification only.

Round 2 revision (2026-06-26), resolving the Logisphere Round 1 review
(`roadmap-6-3-2.review-r1.md`):

- **B1 (Work item 2 Hypothesis feasibility).** Split Work item 2 into Part A —
  one `@given` property on the *pure* synthetic-outcome → `run` → envelope
  surface (no `tmp_path`, no `monkeypatch.chdir`, reusing the `wrapper_app`
  builder, so no function-scoped fixture is taken under `@given`) — and Part B
  — plain parametrized pytest over the driven cells, where function-scoped
  `tmp_path`/`drive` are permitted. This mirrors
  `tests/test_contract_properties.py` (pure `@given` at lines 49-110; driven
  plain-pytest cases at 130-202). The property no longer attempts to drive real
  commands under `@given`, so it collects and passes.
- **B2 (unconstructible (command, channel) pairs).** Added an empirically
  verified constructible-cell table to Context and orientation, binding every
  driven cell to a concrete tree (coherent phase, `incoherent_tree`, drafting
  tree, em-dash-flood draft, `--nope`, no-`working/`) and marking the
  unconstructible pairs (`done` 0/4, `wordcount` 1/4, every non-`done` code-1)
  as carried gaps in the suite docstring, the roadmap-6.2.1 way. Work items 2
  and 4 now enumerate exactly these cells instead of defaulting to a coherent
  `PHASE_STATES` tree for exit 4.
- Folded the advisory points: fixed the Work item 1 key-order typo to
  `result, messages` (A1); excluded the `--help`/`--version` no-envelope arm
  from the "every invocation emits the envelope" assertions (A2); bound each
  exit-4 command to its fixture in Work item 4 (A3); committed up front to the
  `tests/cross_command_contract/` package split (A4); added the §6.2.1 matrix
  regression-gate run after the helper promotion (A5); and noted that the
  roadmap's "benign" grouping is the harness *response* class, not the `ok`
  field, so code 1 stays `ok: false` (A6).

## Addenda

- [x] 6.3.2.1 (from review:6.3.2; low). Add a completeness tripwire for the
  actionable-finding (exit 4) arm in the cross-command suite, mirroring the
  existing `test_diagnostic_arms_cover_all_five_commands` guard on the
  usage/state arms. Because `make test` runs under xdist where syrupy does not
  reliably fail on orphaned snapshots, a future deletion of a finding cell from
  `_BODY_CELLS` would silently reduce coverage. Assert the finding cells cover
  exactly `{novel state, novel compile, novel desloppify}`. Lightweight
  addendum pass.
- [x] 6.3.2.2 (from review:6.3.2; low). Strip the two redundant `typing.cast`
  wrappers over `ChannelCell.build_app` in the cross-command suite (already
  typed `Callable[[], App]` on the `ChannelCell` NamedTuple), which `ty check`
  flags as redundant-cast warnings, and remove the now-unused `cabc`/`cyclopts`
  `TYPE_CHECKING` references those casts justified, keeping the just-landed test
  code free of dead annotations. Lightweight addendum pass.
- 6.3.2.3 (from review:6.3.2; low). Correct the roadmap §6.3.2 entry wording so
  the exit-code-to-`ok` mapping no longer reads `0/1 → benign, 2/3/4 →
  ok:false`, which conflates the harness response class (loop vs stop) with the
  envelope `ok` field. ADR-003 and design §3.1 fix `ok` as true iff code 0, so
  benign-negative code 1 is `ok: false`; the shipped suite already pins the real
  contract. A small editorial fix to the roadmap §6.3.2 prose removes the trap
  at source. Lightweight addendum pass.
