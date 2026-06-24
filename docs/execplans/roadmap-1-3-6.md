# Add a shared contract-app factory for the runner's required four-flag `cyclopts.App`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (all four work items implemented, gated, and committed)

## Purpose / big picture

The shared `run` wrapper in `novel_ralph_skill/contract/runner.py` has a hard,
load-bearing requirement: every Cyclopts app it drives MUST be constructed with
`result_action="return_value"`, `exit_on_error=False`, `print_error=False`, and
`help_on_error=False` (runner docstring lines 166-170). The first flag returns
the command body's value to the wrapper instead of `App.__call__` calling
`sys.exit`; the other three make Cyclopts raise a `CycloptsError` on a usage
fault (so the wrapper maps it to exit `2`) and suppress the Rich error panel (so
the wrapper owns the diagnostic channel). Those four flags are currently
re-spelled verbatim in four `build_app()` constructors — `novel_state.py:328`,
`_novel_done.py:98`, `_compile.py:139`, `_desloppify.py:305` — so a fifth
command, or any change to the required flag set, must touch every site, and a
mismatch is caught only at runtime (`audit-3.1.1.md` Finding 5). In parallel,
the four real entry-point bodies in `novel_ralph_skill/commands/stub.py`
(`novel_state`, `novel_done`, `novel_compile`, `desloppify`, lines 72-165)
differ only in the command name, the `build_app` source, and the `_NAME_FOR[…]`
key; the `parse_global_flags → run(build_app(), residual, RunContext(...))`
skeleton is copied four times.

After this change, a single `make_contract_app(name)` factory in the contract
layer owns the four-flag construction, co-located with the `run` wrapper that
demands those flags. Each `build_app()` calls the factory, then registers its
`@app.command`/`@app.default` bodies exactly as it does today. An optional
`_drive(name, build_app)` helper in `stub.py` collapses the four near-identical
entry-point bodies into one-liners, putting the `parse_global_flags`/`run`
plumbing in one place. The runner's required-flags contract then has one home,
and a future command inherits it rather than re-deriving it.

Success is observable four ways. First, a new unit test asserts the factory
returns a `cyclopts.App` whose `result_action`, `exit_on_error`, `print_error`,
and `help_on_error` attributes carry the four required values and whose `name`
carries the argument passed. Note that cyclopts 4.18.0 tuple-normalises two of
these on construction — `name="novel-state"` is stored as `("novel-state",)` and
`result_action="return_value"` as `("return_value",)` — while the three booleans
are stored plain (`exit_on_error == False`, `print_error == False`,
`help_on_error == False`); the test asserts the normalised forms, not the raw
arguments (see Work item 1). Second, the existing contract-runner suite
(`tests/test_contract_runner.py`), the cyclopts tripwire
(`tests/test_cyclopts_contract.py`), and every per-command suite (`novel-state`
check/mutators, `novel-done`, `novel-compile`, `desloppify`) continue to pass
unchanged in behaviour, proving the construction refactor is behaviour-
preserving. Third, the console-scripts end-to-end suite
(`tests/test_console_scripts_e2e.py`) — which builds, installs, and runs the
five console-scripts by absolute path through a cuprum catalogue — stays green,
proving the entry-point `_drive` refactor preserves the installed-binary
behaviour. Fourth, `make all` passes (build, format check, lint including the
N-family naming rules and 100% `interrogate` docstring coverage, type check via
`ty`, and the full pytest suite under xdist).

This is a pure-Python, internal refactor. It changes no command-line surface, no
envelope wire format, no exit-code policy, and no external-library behaviour. It
serves the step-1.3 shared-contract-scaffolding hypothesis — one envelope,
output-mode switch, and exit-code helper serving all five commands — by
co-locating the four-flag contract with the runner that enforces it, per roadmap
task 1.3.6 and `docs/issues/audit-3.1.1.md` Finding 5. It cites design §3.1 and
§4 and `docs/adr-003-shared-interface-contract.md`.

## Constraints

Hard invariants that must hold throughout implementation.

- **The four-flag contract is exact and unchanged (runner.py:166-170 is the
  prose home; the flags serve the design §3.2 / ADR-003 Table 2 exit-code
  policy).** `make_contract_app` must construct the app with exactly
  `result_action="return_value"`, `exit_on_error=False`, `print_error=False`,
  `help_on_error=False`. The contract's documented home is the `run` docstring
  (`runner.py:166-170`): `result_action="return_value"` returns the body value
  to `run`; `exit_on_error=False` makes a usage fault raise `CycloptsError`
  instead of Cyclopts exiting `1`; `print_error=False, help_on_error=False`
  suppress the Rich panel so `run` owns the diagnostic channel. The exit-code
  table those behaviours feed (codes 0-4) lives in design §3.2 and ADR-003
  Table 2, but neither documents the four constructor flags — do not cite §3.2 /
  Table 2 as the flag specification. These are the four behaviours pinned by
  `tests/test_cyclopts_contract.py` (the version-and-behaviour tripwire). The
  refactor centralises the spelling; it must not change a single flag value.
- **No behavioural drift in any command.** Every `build_app()` must still return
  an app exposing the same subcommands/default body it does today, so every
  per-command suite passes unchanged. `novel-state` exposes `check`, `init`,
  `set-cursor`, `advance-phase`, `recount`, `reconcile`; `novel-done`,
  `novel-compile`, and `desloppify` each register their existing default body.
- **No public-surface drift.** The names and import paths of the four
  `build_app` functions, the five `stub.py` entry-point functions
  (`novel_state`, `novel_done`, `novel_compile`, `desloppify`, `wordcount`), and
  the `make_stub_app` factory must remain exactly as they are today.
  `pyproject.toml` `[project.scripts]` targets (`module:function`) and the
  `COMMAND_ENTRY_POINTS` registry must not change, so
  `tests/test_pyproject_scripts.py` and `tests/test_command_names_registry.py`
  stay green.
- **Layering direction (design §3.1; roadmap 1.3.6).** The factory lives in the
  `contract` layer (beside the `run` wrapper that demands the flags); command
  modules and `stub.py` depend on `contract`, never the reverse.
  `novel_ralph_skill/contract` must not import any command module.
- **`make_stub_app` stays distinct.** The exit-`2` stub factory in `stub.py` for
  the one remaining `wordcount` stub does **not** drive through `run` and does
  **not** take the four flags (it owns its own `sys.exit`). It must remain a
  separate factory; `make_contract_app` must not subsume it.
- **The cyclopts tripwire keeps building a raw `cyclopts.App`.**
  `tests/test_cyclopts_contract.py::_make_app` must continue to construct the
  app directly with the four literal flags. It is the genuine version tripwire
  that fails loudly on a silent `uv` re-resolution; routing it through the
  factory would hide a default change behind the factory and defeat its purpose.
- **No new dependency.** Use only the standard library, `cyclopts` (already a
  dependency), and the existing package. Do not add anything to
  `pyproject.toml`'s dependency lists.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all docstrings, comments,
  and commit messages (AGENTS.md house style).
- **Docstring coverage stays at 100%.** Every new public function carries a
  NumPy-style docstring; `interrogate` is pinned in `make lint`.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- **Scope.** If the change touches more than 9 source/test files or more than
  ~220 net lines of code, stop and escalate; this is a focused extraction.
- **Interface.** If any `build_app`, entry-point, or `make_stub_app` name,
  import path, or `[project.scripts]` target must change to make the refactor
  work, stop and escalate — that contradicts a Constraint.
- **Flags.** If centralising the four flags appears to require changing any flag
  value, or if `cyclopts.App` rejects passing them via the factory, stop and
  escalate — that contradicts a Constraint and the verified cyclopts API.
- **Dependencies.** If a new external dependency seems required, stop and
  escalate (none should be).
- **Iterations.** If `make all` still fails after 3 fix attempts on any work
  item, stop and escalate with the failing output.
- **Ambiguity.** If the `_drive` helper cannot accommodate one entry point's
  `build_app` import shape (top-level for `novel_state`, deferred in-body for the
  other three) without changing import semantics, stop and present the options
  before coding.

## Risks

- Risk: the four `build_app` functions register their bodies on the app
  returned by the factory; if the factory returned a frozen or
  already-finalised app, decorator registration could fail. Severity: medium.
  Likelihood: low. Mitigation: the factory returns a freshly constructed,
  empty `cyclopts.App`; `@app.command`/`@app.default` registration after
  construction is exactly how every command already works today (verified
  against `cyclopts` 4.18.0 `core.py` — the four flags are `kw_only` attrs
  `field`s with `default=None`, set at construction, independent of later
  command registration). Pin with the existing per-command suites.
- Risk: `novel_state.build_app` performs a deferred in-builder import of
  `_state_mutators` to avoid a circular import, and the four entry points import
  `build_app` differently (`novel_state` at module top; the other three deferred
  in-body). A `_drive` helper that imports eagerly could reintroduce a cycle.
  Severity: medium. Likelihood: medium. Mitigation: `_drive(name, build_app)`
  takes the already-resolved `build_app` *callable* as a parameter; each entry
  point resolves its own `build_app` (keeping its current import site and
  laziness) and passes it in, so `_drive` adds no import of its own. The
  deferred-import laziness rationale (`audit-3.1.1.md` Finding 4) is preserved
  and gets the one-line comment that audit asked for.
- Risk: the `wrapper_app` conftest fixture and the `_make_app` tripwire helper
  also re-spell the four flags; a reviewer may expect them routed through the
  factory too. Severity: low. Likelihood: medium. Mitigation: route the
  `wrapper_app` fixture through the factory (it is test scaffolding that should
  track the production contract), but leave `_make_app` building the raw app (a
  Constraint: it is the version tripwire). Document this split in the Decision
  Log.
- Risk: `make fmt` reformats unrelated Markdown under `docs/` via
  `mdformat-all` (a known repo nuisance). Severity: low. Likelihood: high.
  Mitigation: `make all` does not run `mdformat`; stage only intended files with
  explicit `git add` pathspecs and leave the churn unstaged (the Safety Net
  blocks `git restore`).

## Progress

- [x] Work item 1: add `make_contract_app(name)` to
  `novel_ralph_skill/contract/runner.py`, re-export it from
  `novel_ralph_skill/contract/__init__.py`, and add a failing-first unit test in
  a new `tests/test_contract_app_factory.py` asserting the cyclopts-normalised
  attribute forms (`name == ("novel-state",)`,
  `result_action == ("return_value",)`, the three booleans `is False`). Done:
  `cyclopts` is now imported at module top in `runner.py` (the redundant
  `TYPE_CHECKING` import was dropped); the test went red (ImportError) then green
  after the factory and re-export landed. `make all` green; coderabbit's trivial
  fixture/parametrize suggestion applied (the three boolean flags are now one
  parametrized test reusing a `contract_app` fixture).
- [x] Work item 2: route the four `build_app()` constructors
  (`novel_state.py`, `_novel_done.py`, `_compile.py`, `_desloppify.py`) through
  `make_contract_app`, deleting the inline four-flag construction. Done: each
  imports `make_contract_app` from `novel_ralph_skill.contract.runner` (the
  existing per-module convention, beside `CommandOutcome`/`StateInputError`) and
  the docstrings now cite the factory rather than re-listing the flags. Because
  the modules no longer *call* `cyclopts.App`, Ruff TC003 required `cyclopts`
  to move into a `TYPE_CHECKING` block (added to `_novel_done.py` and
  `_compile.py`, which previously had none). `make all` green; all per-command
  suites and `test_contract_runner.py` pass unchanged.
- [x] Work item 3: add the `_drive(name, build_app)` helper to `stub.py`,
  collapse the four real entry-point bodies to one-liners, and add the
  deferred-import rationale comment (`audit-3.1.1.md` Finding 4). Done: `_drive`
  takes the resolved `build_app` callable as a parameter (no new import in
  `stub.py`), so each entry point keeps its own import site/laziness; the
  B3/B4/Finding-4 rationale now lives once in the `_drive` docstring. The
  one-line entry-point docstrings were trimmed to fit the 88-col Ruff limit
  (dropped a `(drives the real app)` clause for `(drives via :func:`_drive`)`).
  `collections.abc as cabc` is imported under `TYPE_CHECKING` for the callable
  annotation; `cyclopts` is already a module-top runtime import (`make_stub_app`
  uses it). `make all` green; `wordcount` left untouched.
- [x] Work item 4: route the `wrapper_app` conftest fixture through
  `make_contract_app`; run the full gate including the console-scripts e2e suite.
  Done: the fixture's `_build` now calls `make_contract_app(COMMAND_NAMES[0])`
  (where it was previously an anonymous four-flag `cyclopts.App`), `cyclopts`
  moved into the conftest `TYPE_CHECKING` block (now typing-only), and a comment
  records that the added name is behaviourally inert. The
  `--help`/`--version` -> `None`/exit-0 assertion already existed at
  `test_contract_runner.py:237` (asserts `excinfo.value.code ==
  ExitCode.SUCCESS` and that stdout does not parse as the contract JSON), so no
  new assertion was needed — the named app's help/version path is proven inert.
  `tests/test_cyclopts_contract.py::_make_app` left as the raw four-flag tripwire
  (a Constraint). `make all` green; the console-scripts e2e suite and the
  cyclopts tripwire both pass. CodeRabbit: clean on the code; one finding on the
  sibling `.review-r1.md` planning artefact (not a work-item file, left
  untouched).

## Surprises & discoveries

- Work item 2: once `build_app()` stopped calling `cyclopts.App(...)` directly,
  `cyclopts` became a typing-only import in all four command modules, so Ruff
  TC003 (`typing-only-third-party-import`) failed `make lint` until `import
  cyclopts` moved into each module's `TYPE_CHECKING` block. `novel_state.py` and
  `_desloppify.py` already had such a block; `_novel_done.py` and `_compile.py`
  did not, so a `import typing as typ` plus an `if typ.TYPE_CHECKING:` guard was
  added to each. Impact: import-time cost of `cyclopts` in those two modules is
  now deferred to the entry-point `build_app` call (which still imports it
  transitively via the runner), matching the lazy-import intent the entry points
  already follow. No behavioural change; the runtime `cyclopts` import now lives
  solely in `contract/runner.py` (the factory) and `stub.py` (`make_stub_app`).

- Work items 2-4: `coderabbit review --agent` was heavily rate-limited
  throughout this task because a parallel df12-build agent in a sibling worktree
  (`roadmap-2-3-2`, `roadmap-3-1-1-addendum`) was consuming the same shared
  CodeRabbit org quota. Each time this worktree's wait window cleared, the
  contending agent reclaimed the quota and the reported wait reset (observed
  bouncing between ~1s and ~16m). Exponential backoff was applied per the
  workflow rule (30s→900s, repeated). One early background retry's piped output
  even captured the *other* worktree's review (`currentBranch:"roadmap-2-3-2"`),
  confirming the contention; subsequent retries were run in the foreground from
  this worktree and verified to report `currentBranch:"roadmap-1-3-6"`. The
  deterministic gate (`make all`) is green at each commit, which is the
  authoritative quality bar. Despite the contention, a foreground review run from
  this worktree eventually cleared the rate limit and completed with `findings:0`
  for the Work item 3 diff (branch `roadmap-1-3-6`); Work items 1 and 2 likewise
  had only test-fixture (applied) or sibling planning-artefact findings.

## Decision log

- Decision: place `make_contract_app` in
  `novel_ralph_skill/contract/runner.py` rather than a new module. Rationale: the
  runner module *defines* the four-flag requirement (its docstring is the
  contract's prose home and `run` is the consumer), so the factory belongs beside
  the wrapper that demands the flags — the roadmap's "co-locating the four-flag
  contract with the runner that enforces it" success criterion.
  `contract/__init__.py` already re-exports `run`, `RunContext`,
  `parse_global_flags` from `runner`, so adding one more re-export keeps the
  contract surface coherent. Date/Author: 2026-06-24, planning agent.
- Decision: keep `tests/test_cyclopts_contract.py::_make_app` building a raw
  `cyclopts.App` with the four literal flags, but route the `wrapper_app`
  conftest fixture through `make_contract_app`. Rationale: `_make_app` is the
  version-and-behaviour tripwire; it must construct the app independently of the
  factory so a silent cyclopts re-resolution that changes a default is caught at
  the source. `wrapper_app` is ordinary run-path scaffolding that should track
  the production contract, so routing it through the factory is a genuine
  consolidation. Date/Author: 2026-06-24, planning agent.
- Decision: `_drive(name, build_app)` takes the `build_app` callable as a
  parameter rather than importing it. Rationale: preserves each entry point's
  existing import site and laziness (top-level for `novel_state`; deferred
  in-body for the other three) and adds no new import to `stub.py`, so the
  circular-import avoidance and the lazy-import-cost intent (`audit-3.1.1.md`
  Finding 4) both hold. Date/Author: 2026-06-24, planning agent.
- Decision (round 2): the Work item 1 factory test asserts the cyclopts 4.18.0
  *normalised* attribute forms, not the raw constructor arguments. Rationale: a
  live probe in this worktree's venv shows `cyclopts.App(name="novel-state")`
  stores `name == ("novel-state",)` and `result_action="return_value"` stores
  `("return_value",)`, while the three booleans stay plain `False`. A literal
  `app.name == "novel-state"` assertion fails, so the plan pins the tuple forms
  explicitly; this keeps the failing-first test genuinely red→green and
  un-weakenable. Resolves design-review round-1 blocking point 1. Date/Author:
  2026-06-24, planning agent.
- Decision (round 2): the four-flag contract's documented home is the `run`
  docstring (`runner.py:166-170`); design §3.2 and ADR-003 Table 2 are cited
  only as the exit-code policy the flags serve, never as the flag
  specification. Rationale: §3.2 is "Exit codes" and ADR-003 Table 2 is the
  disambiguated exit-code table (codes 0-4); neither documents the four
  `cyclopts.App` constructor flags. Citing them as the flag home would seed a
  false citation into newly written production docstrings. Resolves
  design-review round-1 blocking point 2. Date/Author: 2026-06-24, planning
  agent.
- Decision (round 2): route the `wrapper_app` fixture through the factory
  (gaining a `name=`) but prove the added name is behaviourally inert by
  confirming/adding the `--help`/`--version` → `None` (exit `0`) assertion in
  `test_contract_runner.py`. Rationale: addresses the round-1 advisory that the
  named app now drives the help/version path; the assertion proves the change
  inert rather than assumed. Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

All four work items landed as planned, one atomic commit each, with `make all`
green at every commit and at HEAD. The four-flag contract now has a single home,
`make_contract_app(name)` in `contract/runner.py`, re-exported from the contract
package; the four `build_app()` constructors and the `wrapper_app` test fixture
call it instead of re-spelling the flags, and the four real entry-point bodies in
`stub.py` collapse onto one `_drive(name, build_app)` helper. The cyclopts
tripwire (`test_cyclopts_contract.py::_make_app`) stays a raw four-flag app, as
a Constraint required.

Result versus Purpose: the success criteria hold. The new
`tests/test_contract_app_factory.py` pins the factory's normalised attribute
forms; the existing contract-runner, cyclopts-tripwire, per-command, and
console-scripts e2e suites pass unchanged in behaviour; and `make all` is green.

Lessons and small deviations:

- The plan said to import `make_contract_app` "from `novel_ralph_skill.contract`"
  in the command modules. The existing per-module convention imports
  `CommandOutcome`/`StateInputError` from `novel_ralph_skill.contract.runner`, so
  the factory was added to that same import for local consistency (the symbol
  lives in `runner`; the package re-export exists and is exercised by the factory
  test). No layering or public-surface impact.
- Centralising the construction turned `cyclopts` into a typing-only import in
  all four command modules and in `tests/conftest.py`, tripping Ruff TC003. The
  fix was mechanical (move `import cyclopts` into each `TYPE_CHECKING` block,
  adding the block to the two command modules that lacked one). Recorded under
  Surprises.
- CodeRabbit was heavily rate-limited by a parallel df12-build agent sharing the
  org quota; foreground reruns from this worktree eventually completed cleanly
  (Work item 3: `findings:0`; Work item 4: the only finding was on a sibling
  planning artefact, left untouched). Recorded under Surprises and the openIssues
  of the workflow return.

## Context and orientation

This repository is the `novel-ralph` harness: a set of deterministic Python
commands that read and mutate a novel's `working/` directory and emit a shared
JSON envelope. The relevant package is `novel_ralph_skill`. Only the following
files are load-bearing for this task.

- `novel_ralph_skill/contract/runner.py` — the shared `run` wrapper. Its
  docstring (lines 159-191) states the four-flag requirement; `run` catches
  `CycloptsError` → exit `2`, `StateInputError` → exit `3`, treats a
  non-`CommandOutcome` return as the `--help`/`--version` path → exit `0`, and
  emits the envelope on a `CommandOutcome` return. This module also hosts
  `parse_global_flags` (the `--human` splitter), `CommandOutcome`, `RunContext`,
  and `StateInputError`. The new `make_contract_app` lands here.
- `novel_ralph_skill/contract/__init__.py` — re-exports the contract surface
  (`run`, `RunContext`, `parse_global_flags`, `CommandOutcome`,
  `StateInputError`, …) via an import block and a sorted `__all__`. The new
  factory is added to both.
- `novel_ralph_skill/commands/novel_state.py` (lines 299-334) — `build_app()`
  constructs `cyclopts.App(name="novel-state", result_action="return_value",
  exit_on_error=False, print_error=False, help_on_error=False)` then registers
  `check`, `init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`. It
  also defines `WORKING_DIR_NAME = "working"` (line 85) and performs a deferred
  in-builder import of `_state_mutators` to avoid a circular import.
- `novel_ralph_skill/commands/_novel_done.py` (lines 83-111),
  `novel_ralph_skill/commands/_compile.py` (lines 123-…), and
  `novel_ralph_skill/commands/_desloppify.py` (lines 290-…) — each `build_app()`
  opens with the identical four-flag construction then registers a default body.
- `novel_ralph_skill/commands/stub.py` — the entry-point module. `novel_state`
  (lines 72-93), `novel_done` (96-117), `novel_compile` (120-142), and
  `desloppify` (145-165) are near-identical `parse_global_flags →
  run(build_app(), residual, RunContext(command=_NAME_FOR[…],
  working_dir=WORKING_DIR_NAME, human=human))` bodies; `wordcount` (168-170) is
  the one remaining stub via `make_stub_app`. `_NAME_FOR` (line 26) is the
  reverse map from entry-point function name to console-script name, built from
  `COMMAND_ENTRY_POINTS`.
- `novel_ralph_skill/commands/names.py` — `COMMAND_ENTRY_POINTS`,
  `COMMAND_NAMES`, `project_scripts_table()`; the single source of truth for the
  five names. Not edited by this task.
- Tests that pin current behaviour and must keep passing:
  - `tests/test_cyclopts_contract.py` — the four-behaviour cyclopts 4.18.0
    tripwire (`_make_app` builds the raw four-flag app; **stays raw**).
  - `tests/test_contract_runner.py` — the run-wrapper exit-code translation
    tests; uses the `wrapper_app` fixture.
  - `tests/conftest.py` (lines 293-322) — the `wrapper_app` fixture that
    re-spells the four flags (routed through the factory in Work item 4).
  - `tests/test_command_stubs.py`, `tests/test_stub.py` — the `make_stub_app`
    and entry-point exit-`2` behaviour (must stay green; `make_stub_app`
    untouched).
  - `tests/test_command_names_registry.py`, `tests/test_pyproject_scripts.py` —
    the registry/`[project.scripts]` agreement.
  - Per-command suites: `tests/test_novel_state_check.py`,
    `tests/test_novel_state_mutators.py`, `tests/test_novel_done_command.py`,
    `tests/test_compile_unit.py`, `tests/test_desloppify_command.py`, and their
    BDD/snapshot/e2e siblings.
  - `tests/test_console_scripts_e2e.py` — builds, installs, and runs the five
    console-scripts by absolute path through a cuprum catalogue (POSIX only, per
    ADR-006); the end-to-end proof the `_drive` refactor preserves installed-
    binary behaviour.

Term definitions:

- **Four-flag contract** — the four `cyclopts.App` constructor arguments
  (`result_action="return_value"`, `exit_on_error=False`, `print_error=False`,
  `help_on_error=False`) the `run` wrapper requires. Its documented home is the
  `run` docstring (`novel_ralph_skill/contract/runner.py:166-170`).
  `result_action="return_value"` returns the body value to `run`;
  `exit_on_error=False` makes a usage fault raise `CycloptsError`;
  `print_error=False, help_on_error=False` suppress the Rich panel. These flags
  serve the design §3.2 / ADR-003 Table 2 exit-code policy (codes 0-4) but are
  not specified there.
- **`CommandOutcome`** — the frozen dataclass a command body returns carrying its
  `ExitCode` and the envelope `result`/`messages` (runner.py:95-116).
- **`make all`** — the project gate: `build check-fmt lint typecheck test`
  (Makefile `.DEFAULT_GOAL`, line 26: `all: build check-fmt lint typecheck
  test`). `make lint` includes Ruff (N-family/N818, TRY, D, ANN, …) and 100%
  `interrogate` docstring coverage; `make test` runs `pytest` under xdist.

### Verified external facts

- **cyclopts is locked at 4.18.0** (`uv.lock` line 137; pinned by
  `tests/test_cyclopts_contract.py::LOCKED_CYCLOPTS_VERSION`). Verified against
  the installed source
  (`…/novel-ralph-skill/.venv/lib/python3.14/site-packages/cyclopts/core.py`):
  `result_action` (line 458), `exit_on_error` (442), `print_error` (440), and
  `help_on_error` (387) are all `kw_only=True` attrs `field`s on `App` with
  `default=None`, plus `name`. So a factory that constructs
  `cyclopts.App(name=name, result_action="return_value", exit_on_error=False,
  print_error=False, help_on_error=False)` is the faithful single home for the
  contract, and registering `@app.command`/`@app.default` after construction is
  the same post-construction registration every command already performs. The
  four behaviours these flags produce are independently pinned by
  `tests/test_cyclopts_contract.py` (usage-error raises `CycloptsError`; panel
  suppressed; `return_value` returns the body; `--help`/`--version` return
  `None`) — verified-and-cited, not asserted from memory.
- **cuprum is locked at 0.1.0** and is **not** on this refactor's logic path. A
  search of `novel_ralph_skill` for `cuprum` returns nothing; cuprum appears
  only in the e2e/console-scripts harness. The single cuprum surface that
  exercises the refactored entry points is in `tests/test_console_scripts_e2e.py`
  (lines 30, 55, 88-90): `cuprum.program.Program(str(script_path))`,
  `cuprum.ProgramCatalogue`, and `cuprum.sh.make(prog,
  catalogue=…)().run_sync(capture=True)` returning a `cuprum.sh.CommandResult`.
  Each is confirmed present in the locked cuprum source
  (`/data/leynos/Projects/cuprum/cuprum/sh.py:528` `make`, `:93` `CommandResult`,
  `:441/:509` `run_sync`; `catalogue.py:59` `ProgramCatalogue`; `pyproject.toml`
  version `0.1.0`). cuprum 0.1.0 allowlists any `Program` string, including an
  absolute path (the e2e harness comment at lines 8-9, 85). This task adds no
  cuprum call and changes no cuprum-driven step; the existing e2e harness simply
  re-runs the installed entry points after the `_drive` refactor, which is the
  intended end-to-end proof. No cuprum capability is missing for this task.
- **N-family exception/naming rules.** The `python-errors-and-logging` skill's
  stance aligns with the repo's Ruff `N` selection; this task adds no new
  exception type, so N818 is not engaged. The factory is a plain function whose
  name (`make_contract_app`) follows the existing `make_stub_app` convention.

## Plan of work

Four ordered, independently committable, gate-passable work items. Each ends
with `make all` passing. Stages map to the skill's red/green/refactor envelope:
Work item 1 is scaffolding-and-test (B/C); items 2-4 are the minimal refactor and
hardening (C/D).

### Stage B/C: Work item 1 — add the `make_contract_app` factory (red, then green)

In `novel_ralph_skill/contract/runner.py`, add a public factory:

```python
# novel_ralph_skill/contract/runner.py
def make_contract_app(name: str) -> cyclopts.App:
    """Build a Cyclopts app wired to the four-flag contract :func:`run` requires.

    The app is constructed with ``result_action="return_value",
    exit_on_error=False, print_error=False, help_on_error=False`` so the shared
    :func:`run` wrapper owns every exit and envelope. The four-flag contract is
    specified in the :func:`run` docstring (runner.py:166-170); the flags serve
    the exit-code policy in design §3.2 / ADR-003 Table 2 but are not documented
    there. Callers register their ``@app.command``/``@app.default`` bodies on
    the returned app exactly as before; this factory owns only the four-flag
    construction, co-located with the wrapper that demands it.
    """
    return cyclopts.App(
        name=name,
        result_action="return_value",
        exit_on_error=False,
        print_error=False,
        help_on_error=False,
    )
```

`cyclopts` is imported lazily inside `run` today only for typing; the factory
needs the runtime module, so import `cyclopts` at module top (it is already a
hard dependency and is imported at runtime by every command module, so this adds
no new cost). Re-export `make_contract_app` from
`novel_ralph_skill/contract/__init__.py` (add to the import block from
`.runner` and to the sorted `__all__`).

Add a failing-first unit test. Prefer a new module
`tests/test_contract_app_factory.py` (keeps the factory's contract pinned in one
obvious place) asserting:

- `make_contract_app("novel-state")` returns a `cyclopts.App`.
- The returned app's five attributes carry the cyclopts-normalised forms,
  **verified live against cyclopts 4.18.0 in this worktree's venv**
  (`.venv/bin/python -c "import cyclopts; …"`):

  - `app.name == ("novel-state",)` — cyclopts tuple-wraps the `name`
    argument; a literal `app.name == "novel-state"` assertion **fails**. Assert
    the tuple form. (Equivalently, `app.name[0] == "novel-state"` or
    `"novel-state" in app.name`; prefer the full-tuple equality so the test
    pins the exact normalised representation.)
  - `app.result_action == ("return_value",)` — cyclopts tuple-wraps
    `result_action` the same way; assert the tuple, not the raw string.
  - `app.exit_on_error is False`, `app.print_error is False`,
    `app.help_on_error is False` — the three booleans are stored plain (no
    normalisation); assert with `is False`.

  Do **not** hedge these forms: they are confirmed by live probe (cyclopts
  4.18.0, version-pinned by `tests/test_cyclopts_contract.py`). No existing test
  reads `App.name`/`App.result_action` back, so there is no in-repo convention
  to crib — the normalised forms above are the convention this test establishes.
- `make_contract_app` is importable from both
  `novel_ralph_skill.contract.runner` and `novel_ralph_skill.contract`.

Run the new test first to confirm it fails (factory absent → AttributeError /
ImportError), then add the factory to make it pass. Because the asserted forms
are the verified normalised values, the test is genuinely red→green: it cannot
be silently weakened to pass against a wrong literal.

**Docs to read:** design §3.1 (output modes / envelope) and §3.2 (exit-code
table); `docs/adr-003-shared-interface-contract.md` (Decision outcome, Table 2);
AGENTS.md §"Quality gates" and §"Python verification and testing".

**Skills to load:** `python-router` → `python-types-and-apis` (public function
signature shape) and `python-testing` (unit-test placement); `leta` (navigate
`contract/__init__.py` exports and confirm the cyclopts attrs names); `sem` (if
checking how `wrapper_app` arrived at its four flags); `commit-message`.

**Tests to add/update:** new `tests/test_contract_app_factory.py` (unit) — the
assertions above. No property, snapshot, behavioural, or e2e test is warranted
for a construction factory; its behavioural consequences are already pinned by
`tests/test_cyclopts_contract.py` and `tests/test_contract_runner.py`.

**Validation:** `make all`. The new test fails before the factory exists and
passes after.

### Work item 2 — route the four `build_app()` constructors through the factory

Edit each `build_app()` to call `make_contract_app(<name>)` instead of spelling
the four flags inline, keeping every subsequent `@app.command`/`@app.default`
registration verbatim:

- `novel_ralph_skill/commands/novel_state.py` (lines 328-334): replace the
  `cyclopts.App(name="novel-state", result_action=…, …)` block with
  `app = make_contract_app("novel-state")`. Keep the deferred `_state_mutators`
  import and all six subcommand registrations unchanged. Import
  `make_contract_app` from `novel_ralph_skill.contract`.
- `novel_ralph_skill/commands/_novel_done.py` (lines 98-104): replace with
  `app = make_contract_app("novel-done")`; keep the `@app.default` body.
- `novel_ralph_skill/commands/_compile.py` (lines 139-…): replace with
  `app = make_contract_app("novel-compile")`; keep the compile default body.
- `novel_ralph_skill/commands/_desloppify.py` (lines 305-…): replace with
  `app = make_contract_app("desloppify")`; keep the desloppify default body.

Trim each `build_app` docstring's "Wired with `result_action=…`" sentence to
cite the factory ("built via `make_contract_app`, which owns the four-flag
contract") rather than re-listing the flags, so the prose no longer duplicates
the contract either. Do **not** reintroduce a "design §3.2 / ADR-003 Table 2"
citation as the flag home in these trimmed docstrings: that table is the
exit-code policy, not the flag specification (see Constraints). If the trimmed
docstring points anywhere for the contract, point at `make_contract_app` (and,
transitively, the `run` docstring at runner.py:166-170).

Do not change any subcommand body, any import other than adding the factory
import, or any `name=` string (the names must stay the console-script names).

**Docs to read:** design §4.1 (`novel-state` subcommands), §4.2 (`novel-done`),
§4.3 (`novel-compile`); `docs/adr-003-shared-interface-contract.md`.

**Skills to load:** `python-router` → `python-types-and-apis`; `leta`
(find each `build_app` and its references to confirm the call sites are
unaffected); `commit-message`.

**Tests to add/update:** none new. The per-command suites
(`tests/test_novel_state_check.py`, `tests/test_novel_state_mutators.py`,
`tests/test_novel_done_command.py`, `tests/test_compile_unit.py`,
`tests/test_desloppify_command.py`, plus their BDD/snapshot siblings) and
`tests/test_contract_runner.py` must all pass unchanged — they are the proof the
factory builds an identical app.

**Validation:** `make all`. Behaviour is preserved; no test changes its expected
outcome.

### Work item 3 — collapse the four entry-point bodies with `_drive`

In `novel_ralph_skill/commands/stub.py`, add a private helper:

```python
# novel_ralph_skill/commands/stub.py
def _drive(name: str, build_app: cabc.Callable[[], cyclopts.App]) -> None:
    """Pre-parse ``--human`` and drive ``build_app()`` through :func:`run`.

    The shared entry-point body: split the ``--human`` global flag off
    ``sys.argv`` (it must be resolved before :func:`run`, which stamps the
    selection into the usage and state-error envelopes; Decision Log B3), then
    drive the app over the residual argv with the fixed ``working/`` working
    directory (B4).
    """
    human, residual = parse_global_flags(sys.argv[1:])
    run(
        build_app(),
        residual,
        RunContext(command=name, working_dir=WORKING_DIR_NAME, human=human),
    )
```

Rewrite the four real entry points as one-liners that each resolve their own
`build_app` (preserving the current import site/laziness) and call `_drive`:

```python
def novel_state() -> None:
    """Console-script entry point for ``novel-state`` (drives the real app)."""
    _drive(_NAME_FOR["novel_state"], build_app)  # build_app imported at top


def novel_done() -> None:
    """Console-script entry point for ``novel-done`` (drives the real app)."""
    # Deferred import: keeps entry-point import cost lazy (audit-3.1.1 Finding 4).
    from novel_ralph_skill.commands import _novel_done

    _drive(_NAME_FOR["novel_done"], _novel_done.build_app)
```

…and the same shape for `novel_compile` (deferred `_compile.build_app`) and
`desloppify` (deferred `_desloppify.build_app`). Add the one-line deferred-import
rationale comment `audit-3.1.1.md` Finding 4 asked for, at the first deferred
import. Leave `wordcount` untouched (it uses `make_stub_app`, not `run`). Import
`collections.abc as cabc` under `TYPE_CHECKING` for the callable annotation, and
`cyclopts` is already imported at module top.

Each per-entry-point docstring keeps its design-cited prose (the `--human`
pre-parse and B3/B4 rationale now live once in `_drive`; the entry-point
docstring can shrink to a one-line "drives the real app" referencing `_drive`).

**Docs to read:** design §3.1 (the `--human` switch) and §4 (the five commands);
`docs/adr-003-shared-interface-contract.md`; `docs/issues/audit-3.1.1.md`
(Findings 4 and 5). The Decision Log B3/B4 references are the established
shorthand in the existing docstrings; preserve them.

**Skills to load:** `python-router` → `python-abstractions` (the right level to
hide the shared plumbing) and `python-types-and-apis` (the `_drive` callable
signature); `leta` (confirm `_NAME_FOR`, `WORKING_DIR_NAME`, `parse_global_flags`
imports); `commit-message`.

**Tests to add/update:** none new. `tests/test_command_stubs.py` and
`tests/test_stub.py` (entry-point exit behaviour), and any in-process entry-point
test must pass unchanged. The behavioural proof is Work item 4's e2e run.

**Validation:** `make all`.

### Stage D: Work item 4 — route the `wrapper_app` fixture and run the full gate

In `tests/conftest.py`, change the `wrapper_app` fixture's `_build` to call
`make_contract_app(...)` (from `novel_ralph_skill.contract`) and then register
its `@app.command` body, instead of re-spelling the four flags. The fixture
builds its app today with **no** `name=` argument (conftest.py:316-321);
`make_contract_app(name: str)` forces one, so pick `COMMAND_NAMES[0]` for the
name. The fixture's behaviour — building a run-configured app whose body returns
the supplied `CommandOutcome` or raises the state fault — must be identical, so
`tests/test_contract_runner.py` and `tests/test_contract_properties.py` pass
unchanged.

Because the fixture's app is now *named* where it was anonymous, prove the name
change is behaviourally inert for the one path that could plausibly notice it:
the `--help`/`--version` case at `tests/test_contract_runner.py:212` now runs
against a named app. Confirm that test still asserts the body returns `None`
(the `run` wrapper's `--help`/`--version` path → exit `0`); the cyclopts probe
implies a named app returns `None` there exactly as an anonymous one does, but
the existing assertion is the proof. If that test does not already pin the
`None`/exit-`0` outcome for the help and version probes, add the explicit
assertion so the fixture's added name is proven inert rather than assumed. This
is the only assertion this work item may add; everything else is refactor-only.

Do **not** touch `tests/test_cyclopts_contract.py::_make_app`: it stays a raw
four-flag `cyclopts.App` (the version tripwire — a Constraint).

Then run the full gate, **explicitly including the console-scripts e2e suite** on
POSIX (it is the end-to-end proof the `_drive` refactor preserves installed-
binary behaviour):

```bash
make all
# and confirm the e2e suite ran (POSIX, per ADR-006):
make test 2>&1 | grep -E "test_console_scripts_e2e"
```

**Docs to read:** AGENTS.md §"Quality gates" (the full gate) and §"Python
verification and testing" (test placement); `docs/adr-006-console-scripts-e2e-posix-policy.md`
(the e2e suite's POSIX scope).

**Skills to load:** `python-testing` (fixture refactor), `code-review`
(self-review the diff for behaviour preservation), `commit-message`.

**Tests to add/update:** the `wrapper_app` fixture body (refactor only, no new
assertion). The whole suite — unit, BDD, snapshot, property, and e2e — must pass
unchanged.

**Validation:** `make all`, with the e2e grep above confirming the console-script
end-to-end suite ran.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-6`.

1. Confirm the branch and tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-6 \
     branch --show-current   # expect: roadmap-1-3-6
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-6 \
     status --short          # expect: only docs/execplans/roadmap-1-3-6.md
   ```

2. Work item 1: create `tests/test_contract_app_factory.py` (failing), run it,
   add `make_contract_app` to `contract/runner.py`, wire the re-export, then:

   ```bash
   make test     # new factory test passes
   make all      # full gate green
   ```

   Commit (file-based message via the `commit-message` skill; never `-m`).

3. Work item 2: edit the four `build_app()` constructors; `make all`; commit.

4. Work item 3: add `_drive` and collapse the four entry points in `stub.py`;
   `make all`; commit.

5. Work item 4: refactor the `wrapper_app` fixture; `make all` (confirm the e2e
   suite ran); commit.

Each commit message follows the `commit-message` skill, uses en-GB Oxford
spelling, and references roadmap task 1.3.6.

Expected `make all` tail on success (illustrative):

```plaintext
... passed in N.NNs
```

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests:** `make test` passes the full suite under xdist. The new
  `tests/test_contract_app_factory.py` fails before Work item 1's factory exists
  and passes after. `tests/test_cyclopts_contract.py` (raw tripwire),
  `tests/test_contract_runner.py`, every per-command suite, and
  `tests/test_console_scripts_e2e.py` pass unchanged in behaviour.
- **Lint/typecheck:** `make lint` (Ruff including N-family, TRY, D, ANN;
  `interrogate` at 100%) and `make typecheck` (`ty check`) pass.
- **Format:** `make check-fmt` passes.
- **Gate:** `make all` is green after every work item.
- **Markdown (this execplan only):** because this ExecPlan is a Markdown file,
  run `make markdownlint` and `make nixie` before committing the plan document;
  expect both to pass. (`make nixie` validates Mermaid; this plan has no Mermaid,
  so it is a no-op pass.)

Quality method (verification): run the commands above in the worktree; compare
output to the expected transcripts.

Behavioural acceptance: the four-flag contract still holds and the installed
scripts still behave. After Work item 4:

```bash
make test 2>&1 | grep -E "test_cyclopts_contract|test_console_scripts_e2e"
# both report PASSED (the e2e suite runs on POSIX per ADR-006)
```

## Idempotence and recovery

Every step is re-runnable. Adding the factory and the test is additive; routing
each `build_app()` and the entry points through the factory/`_drive` is a
localised edit. If a `make all` run fails, fix forward (do not delete the
factory) and re-run `make all`; the build cache makes re-runs cheap. To abandon
a half-finished work item, `git restore` the touched source files and re-apply
from this plan. No step is destructive; no backups are required.

## Artifacts and notes

The load-bearing current code, for reference during implementation.

The four-flag block repeated in every `build_app()` (e.g. `novel_state.py:328`):

```python
app = cyclopts.App(
    name="novel-state",
    result_action="return_value",
    exit_on_error=False,
    print_error=False,
    help_on_error=False,
)
```

One of the four near-identical entry-point bodies (`stub.py:96-117`,
`novel_done`):

```python
def novel_done() -> None:
    human, residual = parse_global_flags(sys.argv[1:])
    from novel_ralph_skill.commands import _novel_done

    run(
        _novel_done.build_app(),
        residual,
        RunContext(
            command=_NAME_FOR["novel_done"],
            working_dir=WORKING_DIR_NAME,
            human=human,
        ),
    )
```

## Interfaces and dependencies

At the end of this plan the following must exist.

In `novel_ralph_skill/contract/runner.py`:

```python
def make_contract_app(name: str) -> cyclopts.App: ...
```

constructing `cyclopts.App(name=name, result_action="return_value",
exit_on_error=False, print_error=False, help_on_error=False)`.

Re-exported from `novel_ralph_skill.contract` (`__init__.py` import block and
sorted `__all__`).

In `novel_ralph_skill/commands/stub.py`:

```python
def _drive(name: str, build_app: cabc.Callable[[], cyclopts.App]) -> None: ...
```

The four `build_app()` functions (`novel_state.build_app`,
`_novel_done.build_app`, `_compile.build_app`, `_desloppify.build_app`) keep
their names and zero-argument signatures but build their app via
`make_contract_app(<name>)`. The five entry points (`novel_state`, `novel_done`,
`novel_compile`, `desloppify`, `wordcount`) and `make_stub_app` keep their names
and import paths; `[project.scripts]` is unchanged. Dependency direction:
command modules and `stub.py` → `novel_ralph_skill.contract`; never the reverse.
No new external dependency.

## Revision note (required when editing an ExecPlan)

Initial draft (2026-06-24): first planning round for roadmap task 1.3.6. No
prior design-review blocking points to address.

Revision (2026-06-24, round 2): resolved both design-review round-1 blocking
points and the round-1 advisory. (1) Blocking point 1 — the Work item 1 factory
test now asserts the cyclopts 4.18.0 *normalised* attribute forms, verified live
in this worktree's venv: `name == ("novel-state",)`,
`result_action == ("return_value",)`, and the three booleans `is False`. The
Purpose, the Work item 1 test bullets, the Progress entry, and a new Decision
Log entry all state the normalised forms explicitly, so the failing-first test
is genuinely red→green and cannot be silently weakened against a wrong literal.
(2) Blocking point 2 — the four-flag contract's documented home is now correctly
attributed to the `run` docstring (`runner.py:166-170`) throughout: the
Constraints "four-flag contract" bullet, the term definition, the
`make_contract_app` docstring template, and the Work item 2 docstring-trim
instruction. Design §3.2 / ADR-003 Table 2 are cited only as the exit-code
policy (codes 0-4) the flags serve, never as the flag specification, and Work
item 2 is explicitly warned not to reintroduce that misattribution. (3) Advisory
— Work item 4 now requires confirming (or adding) the `--help`/`--version` →
`None` assertion in `test_contract_runner.py`, proving the `wrapper_app`
fixture's newly added `name=` is behaviourally inert. No work items were added,
removed, or reordered; the change is documentation/test-specification precision
only.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task. Execute
each as a small addendum pass — no plan or design-review cycle: make the change,
run `make all`, `coderabbit review --agent`, commit, and tick the roadmap
sub-task on merge.

- [x] 1.3.6.1 — Add a structural tripwire pinning that the four `build_app()`
  constructors and the four real entry points consume the centralisation (merges
  review:1.3.6 and audit:1.3.6 Finding 3, low and medium). The behavioural proof
  that `make_contract_app`/`_drive` are on the path is currently indirect
  (console-scripts e2e plus per-command suites), so a future edit re-inlining a
  bare `cyclopts.App` in one `build_app()`, or re-inlining the
  `parse_global_flags`/`run` plumbing in one entry point, would still pass every
  existing suite. Add a lightweight in-process test that (a) parametrises over
  the four production `build_app` callables and asserts each returned app carries
  the four-flag contract (`result_action`, `exit_on_error`, `print_error`,
  `help_on_error`), and (b) asserts each of the four real entry points routes
  through `_drive`/`make_contract_app` (e.g. by monkeypatching the shared seam
  and confirming each entry point invokes it). This is the cheap structural
  tripwire the factory makes possible, guarding the "constructors consume the
  factory" half of the 1.3.6 success criterion. Behaviour-preserving;
  test-only; gate with `make all`.
- [x] 1.3.6.2 — Document the four-flag cyclopts contract and `make_contract_app`
  in ADR-003 and the developers' guide (from audit:1.3.6 Findings 1 and 6, low).
  The four-flag requirement is now load-bearing contract machinery with a
  dedicated factory but is undocumented in prose — the `runner.py` docstring
  itself notes the flags "are not documented there". Record in ADR-003 (the
  shared-interface-contract ADR) the four-flag requirement, the per-flag
  rationale, and that `make_contract_app` is its single enforcement point, so a
  future sixth command calls the factory rather than `cyclopts.App` directly; add
  the matching note to the developers' guide. Keep the existing attribution that
  design §3.2 / ADR-003 Table 2 is the exit-code policy the flags serve, not the
  flag specification. Documentation-only; gate with `make all`.
