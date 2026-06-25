# Stand up the `novel` multiplexer dispatcher and entry point (ADR 007)

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Today the deterministic spine installs five separate console-scripts —
`novel-state`, `novel-done`, `novel-compile`, `desloppify`, and `wordcount` —
each wired in `pyproject.toml [project.scripts]` to its own entry-point
function in `novel_ralph_skill/commands/stub.py`. ADR 007 (superseding ADR 005)
fixes the final surface as a single `novel` multiplexer: `novel state …`,
`novel done`, `novel compile`, `novel desloppify`, `novel wordcount`.

This task delivers the multiplexer dispatcher and its `novel` entry point, and
nothing more. After this change a developer can run, in-process and (once
installed) on `PATH`:

- `novel state init --title X --slug x`, `novel state check`, and the other five
  `state` mutators — dispatching into the existing `novel-state` app;
- `novel done`, `novel compile [--check]`, `novel desloppify …`, and
  `novel wordcount` — dispatching into the four existing leaf apps;

each emitting the **unchanged** JSON (or `--human`) envelope and the
**unchanged** exit codes (0 success, 1 benign negative, 2 usage error, 3
state/input error, 4 actionable finding) that the five separate scripts already
produce.

Crucially, this task is **independently landable**: the five legacy
`[project.scripts]` entries stay registered and keep working. Migrating the e2e
and contract suites onto `novel <sub>`, removing the legacy entry points, and
sweeping the design and `SKILL.md` prose are explicitly **out of scope** here —
they are roadmap tasks 1.2.13 and 1.2.14. You can observe success without
touching any of those.

Observable acceptance (full detail in `Validation and acceptance`):

- A new in-process behavioural test drives `novel state check`, `novel done`,
  `novel compile --check`, `novel desloppify`, and `novel wordcount` through
  the multiplexer entry point and asserts each produces the same envelope and
  exit code as its legacy entry point over the corpus, including the exit-2
  (usage), exit-3 (state), and exit-0 (`--help`/`--version`) arms.
- `make all` is green, and the five legacy console-scripts still pass their
  existing suites unchanged.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change to the five operations.** The envelope schema, field
  order, exit-code policy (design §3.2; ADR 003 Table 2), and `--human`
  semantics (ADR 003 §3.1) are unchanged. The multiplexer is a pure dispatch
  layer; it adds no new command logic.
- **The five legacy entry points stay registered and working.** Do not remove or
  rename `novel-state`, `novel-done`, `novel-compile`, `desloppify`, or
  `wordcount` from `[project.scripts]` or `stub.py`. (Their removal is task
  1.2.13.) This keeps the task independently landable per the roadmap.
- **Do not migrate the e2e/contract suites or sweep docs here.** Do not edit
  `tests/test_console_scripts_e2e.py`,
  `tests/test_console_scripts_error_arms_e2e.py`, the installed-binary
  fixtures, or the design/`SKILL.md` prose to the spaced form (tasks
  1.2.13/1.2.14). The one permitted exception is *additive* registry/guard
  tests for the new spaced names.
- **Locked dependencies.** Cyclopts is pinned at `4.18.0` and tomlkit per
  `uv.lock`; introduce no new runtime dependency. The dispatcher must use only
  Cyclopts sub-app mounting that 4.18.0 supports (verified below).
- **Single source of truth preserved.** The command-name registry
  (`novel_ralph_skill/commands/names.py`) remains the one place command names
  live; the spaced subcommand names are added there additively, not re-spelled
  inline in the entry point or the envelope guard.
- **Quality gates (AGENTS.md).** Every commit passes `make all` (build,
  check-fmt, lint, typecheck, test); en-GB Oxford spelling ("-ize"/"-yse"/
  "-our") in all prose, comments, and commit messages; files ≤ 400 lines; tests
  live under the top-level `tests/` tree; 100% docstring coverage (interrogate).
- **No markdown changes expected.** This task touches no `.md` under normal
  scope. If you do edit any markdown, run `make markdownlint` and `make nixie`
  on it (and only commit markdown that passes both).

## Tolerances (exception triggers)

Stop and escalate when any of these is breached; do not work around it.

- **Scope.** If implementation requires net changes to more than 8 files or more
  than ~350 lines (excluding tests), stop and escalate.
- **Interface.** If you must change the public signature of any existing
  `build_app()`, of `make_contract_app`, of `run`, of `parse_global_flags`, of
  `RunContext`, or of `build_envelope`, stop and escalate. (The plan expects
  these to remain stable; the multiplexer is additive.)
- **Dependencies.** If a new external dependency seems required, stop and
  escalate — Cyclopts 4.18.0 sub-app mounting is verified sufficient below.
- **Cyclopts behaviour.** If any verified Cyclopts behaviour in the Decision Log
  fails to reproduce (sub-app mounting, leaf `@app.default` dispatch under a
  parent, `CycloptsError` on unknown command/option, `--help`/`--version`
  returning a non-`CommandOutcome`), stop and escalate with the failing probe.
- **Iterations.** If the multiplexer behavioural test still fails after 4
  focused attempts, stop and escalate.
- **Ambiguity.** If the envelope `command` field for a subcommand is contested
  (see Decision Log D1: spaced `"novel state"` vs legacy `"novel-state"`), and
  the choice materially affects 1.2.13/1.2.14, stop and present options.

## Risks

- Risk: A mounted leaf app whose body is registered with `@app.default` might
  not
  fire when invoked as `novel <verb>` under the parent. Severity: high
  Likelihood: low Mitigation: Verified empirically against Cyclopts 4.18.0
  (Decision Log D2); pinned by the multiplexer behavioural test in Work item 4.
- Risk: Mounting a sub-app could clobber its `result_action="return_value"`
  (which `make_contract_app` sets), making the parent `sys.exit` on the body
  value before `run` emits the envelope. Severity: high Likelihood: low
  Mitigation: Source-verified that `_apply_parent_defaults_to_app` copies only
  group defaults and `version`, never `result_action` (Decision Log D3). The
  parent is itself built via `make_contract_app`, so its own `result_action` is
  `return_value` and it returns the leaf body value to `run` unchanged. Pinned
  by the contract-app tripwire (Work item 4).
- Risk: Re-pointing the envelope command-name guard onto a superset that
  includes
  the spaced names while keeping `[project.scripts]` at the legacy five could
  desynchronise the two registry consumers, breaking the existing
  `test_command_names_registry.py` / `test_pyproject_scripts.py` gates.
  Severity: medium Likelihood: medium Mitigation: Work item 2 decouples the two
  roles explicitly — a `SCRIPT_NAMES` / `project_scripts_table` view for
  `[project.scripts]` (legacy five plus the new `novel`) and an
  `ENVELOPE_COMMAND_NAMES` superset for the guard — and updates the coupled
  tests to assert each view against its own source.
- Risk: The envelope `command` value the multiplexer stamps (`"novel state"`)
  differs from what the design §4.2 example still shows (`"novel-done"`),
  pre-empting the 1.2.14 prose sweep. Severity: low Likelihood: medium
  Mitigation: The design example is prose swept in 1.2.14; the envelope guard
  is a superset, so both forms validate during the transition (Decision Log D1).
- Risk: Bare `novel` with no subcommand behaves differently from a leaf verb
  (prints help, exits 0) rather than running a default body. Severity: low
  Likelihood: high (this is expected Cyclopts behaviour) Mitigation: Documented
  and pinned by an explicit test arm (Work item 4); this is the desired
  multiplexer behaviour, not a defect.

## Progress

- [x] Work item 1: Read-only orientation and red-test harness scaffold (no
  production code). Cyclopts 4.18.0 probe re-confirmed D2/D3 in this venv;
  `tests/test_multiplexer_dispatch.py` fails at import on the missing `novel`
  module and `SUBCOMMAND_NAMES`, the intended red state.
- [x] Work item 2: Decouple the command-name registry — `[project.scripts]`
  view (`project_scripts_table()` now legacy five + `novel`) vs envelope-guard
  superset (`ENVELOPE_COMMAND_NAMES` = legacy five + `SUBCOMMAND_NAMES` +
  `"novel"`). `envelope.py` re-pointed onto the superset; the coupled gates
  (`test_command_names_registry.py`, `test_pyproject_scripts.py`,
  `test_contract_envelope.py`) updated to the decoupled views.
- [x] Work item 3: Added `novel_ralph_skill/commands/novel.py`
  (`build_multiplexer`, `_command_name_for`, `main`) and registered
  `novel = "novel_ralph_skill.commands.novel:main"` in `[project.scripts]`.
  Leaf imports deferred inside the builder to preserve per-command laziness.
- [x] Work item 4: Multiplexer dispatch tests split across
  `tests/test_multiplexer_dispatch.py` (unit shape/contract/name-mapping) and
  `tests/test_multiplexer_behaviour.py` (in-process legacy-vs-multiplexer
  equality over the corpus, exit 0/1/2/3/4 + help/version + bare-`novel`), with
  the shared `driver` fixture in the registered plugin
  `tests/multiplexer_support.py`. The split keeps each module under the
  400-line cap.
- [x] Work item 5: `make all` green at HEAD (1074 passed, 1 skipped);
  coderabbit `review` reported **no findings** (run 1). Added a "The `novel`
  multiplexer" subsection to `docs/developers-guide.md` documenting the new
  internal dispatch interface; markdownlint and nixie pass on it.

## Surprises & discoveries

    - Observation: The Cyclopts 4.18.0 probe reproduced the planned transcript
      exactly in this worktree's venv.
      Evidence: `parent(["done"]) -> "DONE"`, `parent(["state","check"]) ->
      "CHECK"`, `state bogus -> UnknownCommandError`, `done extra ->
      UnusedCliTokensError`, `done --bogus -> UnknownOptionError`, `--help`/bare
      `novel` print help and return `None`.
      Impact: D2/D3 hold; the multiplexer can mount the leaf/state apps and rely
      on the shared `run` wrapper unchanged.

    - Observation: A single combined dispatch test module reached ~450 lines,
      breaching the 400-line cap, and the developers-guide "Shared test
      scaffolding" rule forbids importing helper *values* (registries, helpers)
      between test modules — only fixtures (by name) and shared *types* (under
      `TYPE_CHECKING`) may cross modules.
      Evidence: `docs/developers-guide.md` lines 58-78; Pylint
      `too-many-lines (450/400)`.
      Impact: Split into `tests/test_multiplexer_dispatch.py` (unit) and
      `tests/test_multiplexer_behaviour.py` (behavioural). The shared `driver`
      fixture lives in the registered plugin `tests/multiplexer_support.py`
      (consumed by name); the `Driver` type crosses under `TYPE_CHECKING`; the
      five-operation parametrize registry is defined locally in the behavioural
      module (a value, so not imported across modules). The `driver`'s two arms
      are closures in a frozen dataclass, not methods, to avoid Pylint
      `no-self-use`.

    - Observation: Cyclopts stores `result_action` tuple-wrapped
      (`("return_value",)`) and reports a leading parent-level `--bad-option` as
      an *unknown command*, not an unknown option.
      Evidence: probe in the venv; `test_contract_app_factory.py` asserts
      `result_action == ("return_value",)`.
      Impact: The contract tripwire asserts `result_action == ("return_value",)`
      and the boolean flags via `is False` (mirroring the existing factory
      tripwire); the usage-fault arm expects "Unknown command" for the
      parent-level bad option and adds a leaf-level `done --bad-option` arm for
      the genuine `UnknownOptionError` path.

## Decision log

    - Decision: D1 — The multiplexer entry point stamps the *spaced* subcommand
      name into the envelope `command` field (e.g. "novel state", "novel done"),
      and the envelope guard (ENVELOPE_COMMAND_NAMES) is a superset of the legacy
      five plus the five spaced names.
      Rationale: The roadmap entry for 1.2.12 directs exactly this — "Make the
      command-name single source of truth carry the new spaced subcommand names
      additively, and re-point the envelope command-name guard onto the
      superset." Keeping the guard a superset lets the legacy entry points
      (which still stamp "novel-state" etc.) and the new multiplexer (which
      stamps "novel state" etc.) both validate during the 1.2.12→1.2.13
      transition. The design §4.2 example still shows the legacy form; that prose
      is swept in 1.2.14, not here.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D2 — Mount the four leaf apps and the state app on a parent
      `novel` app built by make_contract_app, via parent.command(subapp,
      name="state"|"done"|"compile"|"desloppify"|"wordcount").
      Rationale: Verified empirically against the locked Cyclopts 4.18.0 (probe
      run in this worktree's venv). Findings: (a) a leaf app whose body is a
      bare @app.default fires when invoked as `novel done` under the parent;
      (b) the state app's @app.command subgroup nests correctly as
      `novel state check` / `novel state init …`; (c) an unknown subcommand or
      verb raises UnknownCommandError; an extra positional raises
      UnusedCliTokensError; an unknown option raises UnknownOptionError — all
      subclasses of cyclopts.exceptions.CycloptsError, which the shared `run`
      wrapper already catches and maps to exit 2; (d) `--help`/`--version` (at
      the parent or any sub level) print and return None (a non-CommandOutcome),
      which `run` treats as the help/version path → exit 0, no envelope; (e) bare
      `novel` with no subcommand prints the parent help and returns None → exit
      0.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D3 — Reuse the leaf apps' existing build_app() functions
      unchanged; do not rebuild their bodies in the dispatcher.
      Rationale: Source-verified (cyclopts/core.py 4.18.0) that
      App.command(subapp) calls _apply_parent_defaults_to_app, which copies only
      _group_commands/_group_parameters/_group_arguments and `version` — never
      result_action, exit_on_error, print_error, or help_on_error. So each
      mounted leaf keeps its four-flag contract from make_contract_app, and the
      parent (also make_contract_app) returns the leaf body's CommandOutcome to
      `run` unchanged. Rebuilding bodies would duplicate logic and risk drift.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D4 — The entry point resolves the subcommand name from argv
      (after stripping --human) to build the RunContext.command, then drives the
      whole parent app through the shared `run` wrapper exactly once.
      Rationale: `run` stamps RunContext.command into every envelope, including
      the body-less exit-2/exit-3 arms (Decision Log B3 in runner.py). The
      multiplexer must therefore decide the command name before `run` is called.
      The name is derived from the leading non-flag token(s) of the residual
      argv via the command-name registry, defaulting to the bare "novel" surface
      name when no subcommand is present (so bare `novel`/`novel --help` stamp a
      registry-valid name even though they emit no envelope).
      Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

Task complete. The `novel` multiplexer dispatches all five operations with
unchanged envelopes and exit codes, proven in-process by the
legacy-versus-multiplexer equality suite across every exit arm (0/1/2/3/4 plus
help/version/bare). The legacy five entry points stay registered and their
existing suites pass unchanged; `make all` is green at HEAD (1074 passed, 1
skipped) and coderabbit reported no findings.

The scope boundary held: the e2e/contract suites and the design/`SKILL.md` prose
were not migrated (tasks 1.2.13/1.2.14); the only test edits outside the new
dispatch suite were the additive registry/guard updates Work item 2 mandates.

Deviations from the plan, with rationale:

- The plan placed all dispatch tests in one module
  (`tests/test_multiplexer_dispatch.py`). The combined module reached ~450
  lines, breaching the 400-line cap, and the developers-guide forbids importing
  helper *values* across test modules. Resolution: split into a unit module and
  a behavioural module, with the shared `driver` fixture in a registered plugin
  (`tests/multiplexer_support.py`, consumed by name) and the `Driver` type
  crossing under `TYPE_CHECKING`. The five-operation parametrize registry is a
  value, so each module defines its own rather than importing it. This is fully
  within the additive-test exception and the AGENTS.md cap.
- The contract tripwire asserts `result_action == ("return_value",)` (cyclopts
  stores it tuple-wrapped) and the boolean flags via `is False`, mirroring the
  existing `tests/test_contract_app_factory.py` tripwire. A parent-level
  `--bad-option` surfaces as "Unknown command" (the parent routes commands and
  has no default body), so the usage-fault arm expects that string and adds a
  leaf-level `done --bad-option` arm for the genuine `UnknownOptionError` path.
  All three remain exit-2 usage faults.

No constraint or tolerance was breached: no public signature changed, no new
dependency was introduced, and the net production change is four files
(`names.py`, `envelope.py`, the new `novel.py`, and `pyproject.toml`).

## Context and orientation

You have only this repository's working tree and this file. No prior plan is
assumed. Work **exclusively** inside the worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-12`.

Key terms:

- **Envelope.** The single JSON object (or `--human` rendering) every command
  prints, carrying `command`, `schema_version`, `ok`, `working_dir`, `result`,
  `messages` in a fixed order (design §3;
  `novel_ralph_skill/contract/ envelope.py`).
- **Exit-code contract.** 0 success, 1 benign negative, 2 usage error, 3 state/
  input error, 4 actionable finding (design §3.2; ADR 003 Table 2). Enforced by
  the shared `run` wrapper.
- **Contract app.** A Cyclopts `App` built by
  `novel_ralph_skill.contract.runner.make_contract_app(name)` with the four
  flags
  `result_action="return_value", exit_on_error=False, print_error=False, help_on_error=False`,
  so the shared `run` wrapper owns every `sys.exit` and every envelope
  emission.
- **Leaf verb.** One of `done`, `compile`, `desloppify`, `wordcount`, each a
  contract app with a single `@app.default` body returning a `CommandOutcome`.
- **`state` subgroup.** The `novel-state` contract app
  (`novel_ralph_skill/commands/novel_state.py`, `build_app()`), exposing seven
  `@app.command` subcommands (`init`, `set-cursor`, `advance-phase`, `recount`,
  `set-chapters`, `check`, `reconcile`).
- **Multiplexer.** The new parent `novel` contract app that mounts the `state`
  app and the four leaf apps as sub-apps, dispatching `novel <sub> …` to them.

Files you will read and touch:

- `novel_ralph_skill/commands/stub.py` — the five legacy entry points and the
  shared `_drive(name, build_app)` body (the pattern the multiplexer entry
  point generalises). Read it; do not remove its entries.
- `novel_ralph_skill/commands/names.py` — the command-name registry. Today
  `COMMAND_NAMES` is exactly the legacy five and double-serves both the
  `[project.scripts]` table and the envelope guard. Work item 2 decouples these.
- `novel_ralph_skill/commands/novel_state.py` — `build_app()` for the `state`
  subgroup (the nesting pattern to mirror) and `WORKING_DIR_NAME`.
- `novel_ralph_skill/commands/_novel_done.py`, `_compile.py`, `_desloppify.py`,
  `_wordcount.py` — each exposes a zero-argument `build_app() -> cyclopts.App`
  built via `make_contract_app`. Reused unchanged.
- `novel_ralph_skill/contract/runner.py` — `make_contract_app`,
  `parse_global_flags`, `RunContext`, `run`, `CommandOutcome`,
  `StateInputError`. Reused unchanged.
- `novel_ralph_skill/contract/envelope.py` — `build_envelope`, which validates
  `command` against `COMMAND_NAMES`. Work item 2 re-points this onto the
  envelope-guard superset.
- `pyproject.toml [project.scripts]` — add one `novel` entry; keep the five.
- `tests/` — add the new dispatch tests; update only the registry/guard gates
  that Work item 2 decouples (`test_command_names_registry.py`,
  `test_pyproject_scripts.py`, `test_contract_envelope.py`). Do **not** touch
  the e2e suites.

Verified Cyclopts mechanism (locked 4.18.0; see Decision Log D2/D3). A parent
`App` mounts a child via `parent.command(child_app, name="state")`. When tokens
`state init --title X` are parsed, the parent walks the command chain into the
child, resolves the leaf function, runs it once, and the **parent's**
`__call__` applies the **parent's** `result_action` to the returned value.
Since the parent is built with `result_action="return_value"`, it returns the
leaf's `CommandOutcome` to `run` unchanged. Mounting copies only group/version
defaults, never the child's contract flags. This makes the parent app
behaviourally transparent to the existing `run` wrapper: from `run`'s
perspective the multiplexer is just another contract app.

## Plan of work

Work item 1 (Stage A — orient, no production code). Re-run the Cyclopts probe
to re-confirm D2/D3 in the current venv, then scaffold the failing behavioural
test so red/green is observable. The probe and the new test file are the
go/no-go for the mechanism.

Work item 2 (Stage B — decouple the registry). In
`novel_ralph_skill/commands/names.py`, separate the two roles the registry
currently conflates:

- Keep `COMMAND_ENTRY_POINTS` (legacy five) and add the single `novel` entry so
  `project_scripts_table()` derives
  `{novel-state, novel-done, novel-compile, desloppify, wordcount, novel}` —
  the legacy five (still live for 1.2.12) plus the new `novel`. Name the new
  entry-point target explicitly (the multiplexer entry function, Work item 3).
- Add an ordered tuple of **spaced subcommand names** — `SUBCOMMAND_NAMES`,
  carrying `"novel state"`, `"novel done"`, `"novel compile"`,
  `"novel desloppify"`, and `"novel wordcount"` — plus the bare surface name
  `"novel"` (for the body-less help/version arms, Decision Log D4) — and an
  `ENVELOPE_COMMAND_NAMES` superset tuple = legacy
  `COMMAND_NAMES` + `SUBCOMMAND_NAMES` (+ `"novel"`). Keep order deterministic
  and de-duplicated.
- Re-point the envelope guard: `novel_ralph_skill/contract/envelope.py` imports
  `ENVELOPE_COMMAND_NAMES` (renamed import or new name) instead of
  `COMMAND_NAMES`, and validates `command` membership against the superset.
  Keep the legacy `COMMAND_NAMES` name available (still the five) so the legacy
  entry points and their existing tests are untouched.

Update the coupled gates so each asserts against the correct view:
`test_pyproject_scripts.py` and `test_command_names_registry.py` must allow the
new `novel` script entry; `test_contract_envelope.py`'s
`test_build_envelope_rejects_unknown_command` must still reject a genuinely
unknown name and now accept the spaced names. End the stage with `make test`
green on these modules.

Work item 3 (Stage C — the dispatcher). Add a new module
`novel_ralph_skill/commands/novel.py` (the multiplexer):

- `build_multiplexer() -> cyclopts.App` builds a parent contract app named
  `"novel"` via `make_contract_app("novel")`, imports the five `build_app`
  builders (the four leaf modules plus `novel_state`), and mounts each:
  `app.command(novel_state.build_app(), name="state")`,
  `app.command(_novel_done.build_app(), name="done")`,
  `app.command(_compile.build_app(), name="compile")`,
  `app.command(_desloppify.build_app(), name="desloppify")`,
  `app.command(_wordcount.build_app(), name="wordcount")`. Defer the leaf
  imports inside the builder to preserve the existing per-command import
  laziness (mirroring `stub.py`).
- `_command_name_for(residual: list[str]) -> str` maps the leading non-flag
  token(s) of the residual argv to the spaced registry name (`"novel state"`
  etc.), returning the bare `"novel"` surface name when no subcommand token is
  present. It consults the registry (Work item 2), not inline string literals.
- `main() -> None` is the entry point:
  `human, residual = parse_global_flags(sys.argv[1:])`;
  `name = _command_name_for(residual)`; then `run` is called with
  `build_multiplexer()`, `residual`, and a `RunContext` carrying `command=name`,
  `working_dir=WORKING_DIR_NAME`, and `human=human`. This reuses the exact
  `_drive`-style shape `stub.py` already uses, generalised to compute the
  subcommand name.

Register the entry point: add `novel = "novel_ralph_skill.commands.novel:main"`
to `[project.scripts]` in `pyproject.toml`, matching the new registry entry
from Work item 2.

Work item 4 (Stage C — tests). See `Validation and acceptance` for the exact
test set. End the stage with the new tests passing and the legacy suites
unchanged.

Work item 5 (Stage D — hardening). Run the full `make all`; fix any
lint/format/typecheck/docstring findings; if the multiplexer constitutes a new
internal interface, add a short note to `docs/developers-guide.md` (and only
then run `make markdownlint` + `make nixie` on it). Update the living sections.

Each stage ends with validation; do not proceed past a failing stage.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-12`.

Work item 1 — orient and scaffold the red test:

Re-confirm the Cyclopts mounting mechanism in the locked venv (D2/D3) by
running, via `uv run python -`, a heredoc that builds a `novel-done` leaf app
(`@app.default` body) and a `novel-state` app (`@app.command check`), mounts
both on a `novel` parent via `parent.command(child, name=...)`, then invokes
`parent(["done"])`, `parent(["state", "check"])`, `parent(["state", "bogus"])`,
and `parent(["done", "extra"])`, printing each result or the caught
`CycloptsError` subclass name. The script body to run:

    import cyclopts
    from cyclopts.exceptions import CycloptsError
    def make(n):
        return cyclopts.App(name=n, result_action="return_value",
                            exit_on_error=False, print_error=False,
                            help_on_error=False)
    leaf = make("novel-done")
    @leaf.default
    def _d():
        return "DONE"
    state = make("novel-state")
    @state.command
    def check():
        return "CHECK"
    parent = make("novel")
    parent.command(leaf, name="done")
    parent.command(state, name="state")
    print(parent(["done"]), parent(["state", "check"]))
    for a in (["state", "bogus"], ["done", "extra"]):
        try:
            parent(a)
        except CycloptsError as e:
            print(a, type(e).__name__)

Expected transcript:

    DONE CHECK
    ['state', 'bogus'] UnknownCommandError
    ['done', 'extra'] UnusedCliTokensError

Then create the new test module (Work item 4 content) so it fails for the right
reason — `ModuleNotFoundError: novel_ralph_skill.commands.novel` — before any
production code exists:

Run `uv run pytest -q tests/test_multiplexer_dispatch.py 2>&1 | tail -5`.

Expected (red): a collection/import error naming the missing
`novel_ralph_skill.commands.novel` module.

Work item 2 — decouple the registry, then:

Run pytest over the decoupled gates:

    uv run pytest -q tests/test_command_names_registry.py \
      tests/test_pyproject_scripts.py tests/test_contract_envelope.py \
      tests/test_contract_envelope_snapshots.py

Expected: all pass (after the gates are updated to the decoupled views).

Work item 3 — add the dispatcher and the `novel` script entry, then re-run the
red test from Work item 1; it should now progress past the import error.

Work item 4 — run the new dispatch suite to green with
`uv run pytest -q tests/test_multiplexer_dispatch.py`.

Work item 5 — full gate with `make all`.

Expected tail: build succeeds; `ruff format --check`, `ruff check`,
`interrogate`, Pylint, and `ty check` clean; pytest reports all passed with no
new failures.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `tests/test_multiplexer_dispatch.py` fails
  before Work item 3 and passes after. The existing legacy suites
  (`test_console_scripts_e2e.py`, `test_command_surface_matrix.py`,
  `test_novel_done_*`, `test_compile_*`, `test_desloppify_*`,
  `test_wordcount_*`, `test_novel_state_*`) pass unchanged.
- Lint/format/typecheck: `make lint`, `make check-fmt`, `make typecheck` clean.
- Audit: `make audit` clean (no new dependency).

Tests this task must add or update (per AGENTS.md testing rules):

- **Unit (new) — `tests/test_multiplexer_dispatch.py`:**
  - `build_multiplexer()` returns a Cyclopts app whose registered command names
    are exactly `{state, done, compile, desloppify, wordcount}`.
  - The contract-app tripwire: the multiplexer app carries
    `result_action="return_value", exit_on_error=False, print_error=False,
    help_on_error=False` (mirror the assertion style of
    `tests/test_contract_app_factory.py` /
    `tests/test_contract_app_centralisation.py`), so a future edit that drops a
    flag fails here rather than silently changing exit behaviour.
  - `_command_name_for(...)` maps residual argv to the spaced registry name:
    `["state","check"] → "novel state"`, `["done"] → "novel done"`,
    `["compile","--check"] → "novel compile"`, `[] → "novel"`,
    `["--help"] → "novel"`. Driven from the registry, not inline literals.
- **Behavioural / in-process (new) — same module, parametrized over the five
  operations:** drive `main()` (patching `sys.argv`) or, preferably, drive the
  multiplexer app through `run(...)` over the `working_corpus` trees the
  existing snapshot/matrix tests use (`tests/test_command_surface_matrix.py`,
  `tests/test_novel_done_snapshots.py`), and assert the captured stdout
  envelope and the `SystemExit` code **equal** those produced by the
  corresponding legacy entry point on the same tree. Cover every exit arm:
  - exit 0 success (`novel state check` on a coherent corpus tree; `novel done`
    on a satisfied tree);
  - exit 1 benign negative (`novel done` on an unsatisfied tree);
  - exit 4 actionable finding (`novel compile --check` on a diverged tree;
    `novel state check` on a violating tree);
  - exit 2 usage error (`novel state bogus`, `novel done extra`,
    `novel --bad-option`) — assert `UnknownCommandError`/`UnusedCliTokensError`/
    `UnknownOptionError` is mapped to exit 2 with the usage envelope;
  - exit 3 state/input error (`novel state check` with no `working/` present);
  - exit 0 help/version with **no** envelope (`novel --help`, `novel --version`,
    `novel state --help`, `novel done --help`, and bare `novel`).
- **Snapshot (optional, syrupy) — if and only if** a reviewer-useful machine/
  human envelope boundary is not already pinned by the per-command snapshot
  suites: a focused snapshot of one dispatched envelope (e.g. `novel done` on a
  fixed corpus tree) proving the multiplexer emits a byte-identical envelope to
  the legacy path. Prefer a semantic equality assertion against the legacy
  envelope over a fresh snapshot to avoid snapshot churn (AGENTS.md snapshot
  rule); add a snapshot only if it captures a contract the equality assertion
  cannot.
- **Registry/guard gates (update) —**
  `tests/test_command_names_registry.py`, `tests/test_pyproject_scripts.py`,
  `tests/test_contract_envelope.py`: update to the decoupled views (Work item
  2) — `[project.scripts]` is the legacy five plus `novel`; the envelope guard
  accepts the superset (legacy five + spaced names + `"novel"`) and still
  rejects a genuinely unknown name. `test_registry_has_exactly_five_names` is
  updated to assert the *script* view (now six entries: five legacy + `novel`)
  or split so the "five operations" intent is asserted against
  `SUBCOMMAND_NAMES`.

Property tests are **not** required: this task adds dispatch routing, not a new
invariant over a range of inputs. (If you find the `_command_name_for` argv
mapping warrants it, a small Hypothesis test over "first non-flag token →
registry name" is acceptable; load `python-verification` then `hypothesis` —
otherwise skip.)

Quality method (how we check):

- Run the new suite red (pre-implementation) then green (post-implementation),
  then `make all`. The behavioural test's legacy-vs-multiplexer equality
  assertions are the core proof that the dispatcher changes no behaviour.

## Idempotence and recovery

- All steps are re-runnable. Editing `names.py`, `envelope.py`,
  `pyproject.toml`,
  and adding `commands/novel.py` are pure source edits; re-running `make all`
  is safe and cache-friendly. Do not run format/lint/test in parallel (build
  cache).
- If a stage fails, revert only that stage's edits (`git restore <file>`) and
  retry; do not advance past a red gate.
- No destructive operations. The legacy entry points remain a working fallback
  throughout, so a half-applied change never leaves the package unrunnable.

## Artifacts and notes

Verified Cyclopts 4.18.0 probe (run in this worktree's venv during planning):

    ['done'] -> ('DONE', [])
    ['state', 'check'] -> ('CHECK',)
    ['state', 'init', '--title', 'X'] -> ('INIT', 'X')
    ['state', 'bogus'] RAISED UnknownCommandError
    ['bogus'] RAISED UnknownCommandError
    --help / --version / state --help / done --help -> None  (→ run exits 0, no envelope)
    ['done', 'extra'] RAISED UnusedCliTokensError
    ['done', '--bogus'] RAISED UnknownOptionError
    UnknownCommandError is CycloptsError: True

This proves: leaf `@app.default` bodies dispatch under the parent; the `state`
subgroup nests; all usage faults raise `CycloptsError` subclasses (→ exit 2 via
`run`); help/version return `None` (→ exit 0, no envelope); bare `novel` returns
`None` (→ exit 0, prints help).

## Interfaces and dependencies

Use Cyclopts `4.18.0` (locked) and the existing contract package; add no
dependency. At the end of this task the following must exist:

In `novel_ralph_skill/commands/novel.py`:

    import cyclopts

    def build_multiplexer() -> cyclopts.App:
        """Build the `novel` parent app mounting state + the four leaf verbs."""

    def main() -> None:
        """`novel` console-script entry point: parse --human, drive via run()."""

In `novel_ralph_skill/commands/names.py` (additive; legacy `COMMAND_NAMES`
unchanged):

    SUBCOMMAND_NAMES: tuple[str, …]        # ("novel state", "novel done", …)
    ENVELOPE_COMMAND_NAMES: tuple[str, …]  # legacy five + spaced names + "novel"
    # project_scripts_table() now includes the "novel" entry beside the five.

In `novel_ralph_skill/contract/envelope.py`: `build_envelope` validates
`command` against `ENVELOPE_COMMAND_NAMES` (superset), not the legacy five.

In `pyproject.toml [project.scripts]`: the five legacy entries unchanged, plus
`novel = "novel_ralph_skill.commands.novel:main"`.

Reused unchanged (escalate before altering any signature): `make_contract_app`,
`parse_global_flags`, `RunContext`, `run`, `CommandOutcome`, `StateInputError`
(`novel_ralph_skill/contract/runner.py`); every leaf/state `build_app()`;
`WORKING_DIR_NAME` (`novel_ralph_skill/commands/novel_state.py`).

## Documentation and skills signposting

Documents the implementer must read (source of truth):

- `docs/adr-007-command-surface-novel-multiplexer.md` — the decision, the exact
  subcommand structure (§"The subcommand structure"), and the migration plan
  naming 1.2.12's scope.
- `docs/novel-ralph-harness-design.md` §3 (envelope + exit-code contract), §3.2,
  §4 (the command surface; §4.1 `novel state`, §4.2 `novel done`, §4.3
  `novel compile`), and the per-command sections for desloppify/wordcount.
- `docs/adr-003-shared-interface-contract.md` — the envelope, exit-code policy
  (Table 2), and the `--human` global flag (§3.1).
- `docs/adr-004-distribution-console-scripts.md` — the console-script
  distribution form (now one `novel` entry).
- `docs/roadmap.md` task 1.2.12 (scope boundary), 1.2.13 and 1.2.14 (what is
  explicitly **out** of scope here).
- `docs/developers-guide.md` and `docs/scripting-standards.md` — conventions for
  the package and command modules.
- `AGENTS.md` — quality gates, testing rules, en-GB Oxford spelling.

Skills to load:

- `python-router` first, then `python-abstractions` (the multiplexer is a small
  behaviour-shaped dispatch layer) and/or `python-types-and-apis` (for the
  `build_multiplexer`/`main` signatures and the registry tuples).
- `python-testing` for the parametrized behavioural suite, fixtures, and the
  legacy-vs-multiplexer equality assertions; `python-verification` then
  `hypothesis` **only if** the `_command_name_for` argv mapping warrants a
  property test.
- `leta` for navigation (`leta show build_app`, `leta refs COMMAND_NAMES`,
  `leta refs build_envelope`) and `sem` for history; `grepai` for semantic
  search.
- `commit-message` for file-based commit messages at each gate.

## Revision note

Initial draft (2026-06-25). Establishes the five ordered work items, pins the
Cyclopts 4.18.0 sub-app mounting mechanism by an empirical probe and a
source-read of `_apply_parent_defaults_to_app`/`__call__`/`parse_args`, and
fixes the registry-decoupling and envelope-guard-superset approach the roadmap
directs. No implementation performed; awaiting design review / approval.

## Addenda

Lightweight, post-merge corrections folded onto this completed task. Each runs
as a no-plan, no-review pass: make the change, run the gates, merge.

- Roadmap 1.2.12.1 — guard `_command_name_for` against future multi-token
  global flags (from review:1.2.12; low). `_command_name_for` treats every
  dash-prefixed token as a value-less global flag, true today because
  `--human` is the only global flag and carries no separate value. Should a
  later global flag carry its own value token, that value could be misread as
  the subcommand verb. Add a small guard (or an explicit comment pinning the
  single-value-less-flag assumption) so the latent regression cannot land
  silently when the global-flag surface grows. Scope: `commands/novel.py`
  `_command_name_for`, plus a focused unit assertion; one focused commit.
- Roadmap 1.2.12.2 — pin a bare unknown top-level verb arm (from review:1.2.12;
  low). The behavioural usage-fault suite covers sub-verb and option faults
  (`novel state bogus`, `novel done extra`, `novel --bad-option`) but not a
  leading unknown verb (`novel bogus`). The path works (the probe shows
  `['bogus'] RAISED UnknownCommandError`; it stamps `novel` and exits 2) yet is
  unpinned, so a regression in `_command_name_for`'s default branch or the
  parent's command routing could go uncaught. Add a `novel bogus` arm to the
  multiplexer behavioural suite asserting exit 2 with the `novel` command name.
  Scope: `tests/test_multiplexer_behaviour.py`; one focused commit.
