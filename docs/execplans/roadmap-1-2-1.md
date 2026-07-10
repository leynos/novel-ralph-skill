# Wire the five console-script entry points in pyproject.toml

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

After this change the `novel_ralph_skill` package exposes five named
console-scripts — `novel-state`, `novel-done`, `novel-compile`, `desloppify`,
and `wordcount` — that a freshly built wheel installs onto `PATH`. Each command
is a minimal Cyclopts application that, until its real logic lands in a later
roadmap slice, deliberately reports "not yet implemented" and exits with code
`2` (usage error) on every invocation that asks it to do work.

The precise stub contract — settled here and **verified empirically against the
locked Cyclopts** (`cyclopts` resolves to 4.18.0 under `requires-python
>=3.14`; see the Decision Log entry "Cyclopts argument-path exit codes,
verified") — is:

- The stub's own command path is reached on a bare, no-argument invocation, and
  on any invocation that supplies only positional tokens. To make positional
  tokens route to the stub body (rather than raising a parser error), the
  registered default callback takes `*tokens: str` and ignores them. That path
  writes a short "`<name>` is not yet implemented" line to stderr and exits `2`.
  This is the path the roadmap success criterion exercises: "each is invocable
  on `PATH` and reports a usage error rather than crashing".
- Three argument classes never reach the stub body; the Cyclopts argument parser
  handles them *before* dispatch, so they are not command results and are exempt
  from the exit-code contract (design §3.2 governs command results, not the
  framework's own argument validation):
  - `--help` (and `-h`) prints usage to stdout and exits `0` (verified).
  - `--version` prints the version string to stdout and exits `0` (verified).
  - An unknown option (a token beginning with `--` that the stub does not
    declare, e.g. `--nope`) is rejected by the Cyclopts parser, which prints an
    error panel to stderr and, with Cyclopts' default `exit_on_error=True`,
    exits `1` (verified). The stub does not, and cannot without re-implementing
    Cyclopts' parser, force this to `2`. Wiring "bad arguments → 2" into a shared
    exit-code helper is roadmap task 1.3.1, explicitly out of scope here.

This is the honest reconciliation of "the stubs exit 2 until implemented"
(roadmap task 1.2.1 text) with the framework's real behaviour: the headline and
the roadmap's literal success criterion is that the **bare PATH invocation exits
2 without crashing**. The two conventional meta-flags exit 0, and the parser's
own unknown-option rejection exits 1; both are facts of the locked framework,
pinned by tests, not choices this task makes.

This is roadmap task 1.2.1 (`docs/roadmap.md`, step 1.2). It stands up the
packaging boundary the design fixes in ADR 004 (installed console-scripts) and
ADR 005 (five separate scripts, not one multiplexer), without implementing any
command behaviour, so the five later slices converge on one coherent spine. It
depends on roadmap tasks 1.1.3 (shared interface contract,
`docs/adr-003-shared-interface-contract.md`) and 1.1.5 (command surface,
`docs/adr-005-command-surface-five-scripts.md`), both already accepted.

To verify the implementation, build a wheel, install it into a throwaway
virtual environment, and run each of the five commands: every one is found
on `PATH`, prints a short usage message to stderr, and exits `2`. No command
crashes with a traceback.

Success is observable as: a `pytest` suite that invokes each stub application
with no arguments and with a positional token and asserts exit code `2`, pins
the three parser carve-outs (`--help` → `0`, `--version` → `0`, unknown
`--option` → `1`), and asserts the `[project.scripts]` table lists exactly the
five expected names; an end-to-end test that builds and installs the wheel and
confirms all five commands resolve on `PATH` and exit `2` on a bare invocation;
and `make all` green.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-1`. Never edit
  files in the root/control worktree.
- The five command names are fixed by ADR 005 and must be spelled exactly:
  `novel-state`, `novel-done`, `novel-compile`, `desloppify`, `wordcount`. Do
  not rename, add, or drop a command.
- No command may implement any narrative judgement or any of its real
  deterministic behaviour in this task (ADR 001, design §1, §2.2). The stubs
  detect nothing and write nothing to the working tree; they only report "not
  implemented" and exit `2`.
- Exit code `2` means "usage error" per the shared contract
  (`docs/adr-003-shared-interface-contract.md`, design §3.2). The stub's
  *command result* — the bare no-argument invocation and any positional-token
  invocation that reaches the default callback — exits `2`. Do not use code `0`,
  `1`, `3`, or `4` for that command result.
- The stub contract is scoped to command results, not to Cyclopts' argument
  parser. Three argument classes are handled by the parser before the command
  body runs and are exempt from the exit-code contract (verified against
  cyclopts 4.18.0; see the Decision Log): `--help`/`-h` exits `0`, `--version`
  exits `0`, and an unknown `--option` exits `1` (Cyclopts' own default
  `exit_on_error` path). Do not attempt to force these to `2`.
- Distribution is installed console-scripts in the existing `novel_ralph_skill`
  hatchling package only (ADR 004, design §2.2). Do not introduce `uv` scripts,
  a `novel` multiplexer, a second package, or a different build backend.
- The CLI framework is Cyclopts (`docs/scripting-standards.md`). Do not use
  `argparse`, `click`, or `typer`.
- Filesystem work, if any, uses `pathlib` (scripting standards). The *command
  code* (the stubs) shells out to nothing — design §4 states "cuprum is required
  only where a command shells out (none do in v1)" — so **no production cuprum
  catalogue is introduced into `novel_ralph_skill`**. The *end-to-end test*
  shells out, and its shell-out discipline is fixed in the Decision Log entry
  "End-to-end shell-out: cuprum for `uv`, scoped subprocess for the installed
  scripts".
- Prose, comments, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our").
- Every public module, class, and function carries a docstring; `interrogate`
  enforces 100% coverage (`AGENTS.md`, Makefile `lint-python`). No file exceeds
  400 lines (`AGENTS.md`).
- Tests live in the top-level `tests/` tree, never inside the package
  (`AGENTS.md`, "Python verification and testing").

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 9 files or more than
  300 net lines, stop and escalate. (Expected files: `pyproject.toml`,
  `novel_ralph_skill/commands/__init__.py`,
  `novel_ralph_skill/commands/stub.py`, `tests/test_command_stubs.py`,
  `tests/test_console_scripts_e2e.py`, `tests/test_pyproject_scripts.py`,
  `docs/developers-guide.md`, `docs/users-guide.md`, and this plan — nine at
  most.)
- Interface: the only public-surface change intended is adding five
  `[project.scripts]` entries and the `cyclopts` runtime dependency. If any
  other public interface must change, stop and escalate.
- Dependencies: this plan adds exactly one *runtime* dependency, `cyclopts`, and
  exactly one *dev* dependency, `cuprum` (used only by the e2e test to shell out
  to `uv` per the scripting standards; added to `[dependency-groups] dev`, not
  to `[project.dependencies]`). If a second new runtime dependency, or a dev
  dependency beyond `cuprum`, proves necessary, stop and escalate. (`tomlkit` is
  already present; adding or confirming it is task 1.2.2, not this task.)
- Iterations: if `make all` still fails after 3 focused fix attempts on the same
  gate, stop and escalate.
- Entry-point mechanism: if a wheel build cannot register the console-scripts
  via `[project.scripts]` under the hatchling backend, stop and escalate rather
  than switching build backend.
- Ambiguity: if the stub exit code requirement appears to conflict with the
  shared-envelope expectation (a stub that also prints the JSON envelope), stop
  and present the trade-off rather than guessing.

## Risks

- Risk: Cyclopts' default for an empty invocation, with no `@app.default`
  registered, is to print help and exit `0`, so a `sys.exit(2)` buried in an
  unreached command body would never fire on the no-argument path.
  - Severity: high. Likelihood: high (this is the framework default, not an edge
    case).
  - Mitigation: resolved structurally and **verified**. `make_stub_app`
    registers an `@app.default` callback that takes `*tokens: str` (so positional
    tokens route to it rather than erroring) whose body is the stub's only code
    path; it writes the message to stderr and calls `sys.exit(STUB_EXIT_CODE)`.
    Verified against cyclopts 4.18.0: the no-argument path and any
    positional-token path both reach the default and exit `2`; `--help` and
    `--version` exit `0`; an unknown `--option` exits `1` via the parser (it does
    *not* reach the default). The unit-test matrix asserts each path so the
    boundary is pinned, not assumed. See the Decision Log entries "Stub exit
    mechanism" and "Cyclopts argument-path exit codes, verified", and the
    Interfaces section for the exact construction.
- Risk: `cyclopts` is not yet in `uv.lock`; `make build` (`uv sync`) must
  resolve it, and `make audit` (`pip-audit`) must pass against it.
  - Severity: low. Likelihood: low.
  - Mitigation: add `cyclopts` to `[project.dependencies]`, run `make build` to
    refresh the lock, then `make audit`. If `pip-audit` flags a known
    vulnerability, escalate with the advisory rather than pinning blindly.
    (Empirically, the resolution at planning time was cyclopts 4.18.0 with
    transitive `docstring-parser` and `rich-rst`.)
- Risk: the end-to-end "build wheel, create venv, install, run five commands"
  check runs **under pytest-xdist** (`make test` is `uv run pytest -v -n auto`,
  Makefile line 116; default `PYTEST_XDIST_WORKERS = auto`, line 14), so the slow
  e2e test executes on a worker process concurrently with every fast test, and it
  must beat the project-wide 30s pytest timeout on a cold cache
  (`pyproject.toml` `[tool.pytest.ini_options]` sets `timeout = 30`).
  - Severity: medium. Likelihood: high (build + venv + install + five subprocess
    runs is realistically 30–90s cold).
  - Mitigation (decided and **verified**, single mechanism, no fallback): the
    e2e test is marked `@pytest.mark.slow` and given an explicit per-test override
    `@pytest.mark.timeout(180)`. This override supersedes the 30s project default
    for that one test and does so **under `-n auto`** — verified empirically
    against the locked plugin set (pytest-timeout 2.x, pytest-xdist 3.x): a
    sleeping test carrying `@pytest.mark.timeout(N)` passes on an xdist worker
    under a smaller project default, while a sibling without the marker is killed
    by the project default on another worker. pytest-timeout applies its marker
    per test inside each worker process, so the override and the project default
    coexist correctly across `-n auto`. The implementer must re-confirm this with
    a quick probe before relying on it (see Concrete steps). The `slow` mark is
    registered in `pyproject.toml` `[tool.pytest.ini_options] markers` so a
    `--strict-markers` run does not error. If a 180s budget were ever genuinely
    insufficient on the target machine, that is a tolerance breach to escalate,
    not a mechanism to swap.
- Risk: the locked cuprum's public catalogue API differs from the example in
  `docs/scripting-standards.md`. The standards show `Catalogue.from_programs("uv")`
  and `sh.scoped(CATALOGUE)`, but the locked cuprum source exposes neither
  `Catalogue` nor `from_programs`.
  - Severity: medium. Likelihood: high (confirmed by reading the source).
  - Mitigation: the e2e test uses the **real** locked cuprum API, pinned against
    the source: `cuprum.ProgramCatalogue(projects=...)` built from
    `ProjectSettings` and `Program`, with `cuprum.sh.make(Program("uv"),
    catalogue=...)`. See the Decision Log entry "Locked cuprum catalogue API,
    verified against source" for the exact symbols and file references. The
    scripting-standards example is treated as illustrative, not as the API of
    record.
- Risk: duplicating five near-identical stub apps invites drift and risks the
  400-line limit or `interrogate` gaps.
  - Severity: low. Likelihood: low.
  - Mitigation: factor a single `make_stub_app(name)` helper so the five apps
    share one definition; each entry-point callable is a thin call into it. Keep
    each module small and docstringed.

## Progress

- [x] Work item 1: Add the `cyclopts` runtime dependency and refresh the lock.
  Done 2026-06-21. `cyclopts` added alphabetically to `[project.dependencies]`;
  `make build` resolved it to 4.18.0 (as predicted), `make audit` reported no
  known vulnerabilities, and `make all` stayed green. coderabbit flagged one
  minor second-person-pronoun issue in this plan's "Purpose" section, fixed.
- [x] Work item 2: Add the stub command surface (a `commands` subpackage with a
  documented `__init__.py`, one shared `make_stub_app` factory registering an
  `@app.default(*tokens: str)` exit, and five named entry-point callables) with
  unit tests asserting exit `2` on no-arg/positional-token, exit `0` on `--help`
  and `--version`, and exit `1` on an unknown `--option`. Done 2026-06-21. The
  verified construction from the Interfaces section was used verbatim; the four
  argument-path exit codes were re-confirmed against cyclopts 4.18.0 before
  writing the tests (no-arg/positional -> 2, `--help`/`--version` -> 0, unknown
  `--option` -> 1). The unknown-option assertion carries a "provisional until
  1.3.1" docstring note (review-round1 advisory 2). Two deviations from the
  letter of the plan, both forced by the locked toolchain: (a) the entry-point
  callable test `monkeypatch`es `sys.argv` to `[name]`, because the callable
  runs `app()` which parses `sys.argv` and would otherwise inherit pytest's
  own argv; (b) that same test filters cyclopts' `UserWarning` ("Cyclopts
  application invoked without tokens under unit-test framework pytest"), which
  fires on the bare `app()` path and is benign. `interrogate` reports 100%,
  Pylint 10.00/10, `ty` clean, all 31 tests pass; coderabbit returned zero
  findings.
- [x] Work item 3: Add `cuprum` (dev), register the `slow` marker and the five
  `[project.scripts]` entry points, add a fast `[project.scripts]`-table unit
  test, and add the build-and-install end-to-end test (slow, 180s per-test
  timeout; `uv` via the locked cuprum catalogue, the five installed scripts
  invoked by absolute path via one scoped `subprocess.run`). Done 2026-06-21.
  cuprum resolved from PyPI as 0.1.0 and its installed API matches the
  source-verified plan exactly (`ProgramCatalogue(projects=...)`,
  `ProjectSettings(name, programs, documentation_locations, noise_rules)`,
  `sh.make(Program("uv"), catalogue=...)`, `CommandResult.exit_code/.stdout/
  .stderr`); `uv --version` through the catalogue reported `uv 0.9.21` as
  predicted. The e2e build, venv, and install run through the scoped cuprum
  catalogue and the five scripts run by absolute path via one
  `subprocess.run`. Three small hardenings/deviations: (a) advisory 1 from the
  round-one review is addressed by passing the project directory explicitly to
  `uv build --wheel <project_root> --out-dir <tmp>` rather than relying on the
  xdist worker's inherited cwd, plus an assertion that exactly one wheel is
  produced; (b) the venv scripts directory and Python interpreter are resolved
  via `sysconfig` so the test is not POSIX-hardcoded; (c) the `subprocess`
  import carries `# noqa: S404` (the call already carries `S603`) since it runs
  installed scripts by absolute path only. The e2e passed under `-n auto` (the
  180s per-test timeout coexists with the 30s project default on a worker), and
  full `make all` is green. coderabbit returned zero findings.
- [x] Work item 4: Document the wired commands in the developers' guide and
  users' guide. Done 2026-06-21. `docs/developers-guide.md` "The five commands"
  section now notes the entry points are wired as exit-2 stubs, pointing at
  `novel_ralph_skill/commands/stub.py`, the e2e test, and the pyproject-scripts
  test. `docs/users-guide.md` gains an "Installed Commands" section listing the
  five names and their current "not yet implemented; exits 2" status.
  `make markdownlint` and `make nixie` pass; `make all` stays green; coderabbit
  returned zero findings.

## Surprises & discoveries

- Observation: `cyclopts.testing.invoke`, shown in `docs/scripting-standards.md`,
  does **not** exist in the locked cyclopts (4.18.0); `import cyclopts.testing`
  raises `ModuleNotFoundError`.
  - Evidence: `python -c "from cyclopts.testing import invoke"` fails on the
    resolved 4.18.0 in the worktree venv.
  - Impact: the unit tests must not import it. They drive each app in-process via
    `app([...], exit_on_error=False)` inside a `pytest.raises(SystemExit)` guard
    (or catch `CycloptsError` for the unknown-option path). The plan's work
    item 2 specifies this verified pattern instead.
- Observation: the locked cuprum exposes `ProgramCatalogue(projects=...)`,
  `ProjectSettings`, and `Program` (a `NewType(str)`), not the
  `Catalogue.from_programs("uv")` the scripting standards illustrate.
  - Evidence: `cuprum/catalogue.py` defines `class ProgramCatalogue` and
    `ProjectSettings`; `cuprum/program.py` defines `Program = NewType("Program",
    str)`; `cuprum/sh.py` `make(program, *, catalogue=DEFAULT_CATALOGUE)`. No
    `from_programs` symbol exists anywhere in `cuprum/`.
  - Impact: the e2e test builds the catalogue with the real constructor; see
    work item 3 and the Decision Log.

## Decision log

- Decision: the stub command result exits `2`; the Cyclopts parser carve-outs are
  `--help` → `0`, `--version` → `0`, unknown `--option` → `1`.
  - Rationale: the roadmap success criterion for 1.2.1 says each command
    "reports a usage error rather than crashing", and the task text says the
    stubs "exit 2 until implemented"; ADR 003 / design §3.2 maps usage error to
    code `2`. The
    bare no-argument PATH invocation is the command result the roadmap exercises,
    and it exits `2`. Cyclopts' parser handles three argument classes before the
    command body runs; these are not command results, so design §3.2 does not
    govern them. Their exit codes are facts of the locked framework, verified
    below.
  - Date/Author: 2026-06-21, planning agent.
- Decision: Cyclopts argument-path exit codes, verified against the locked
  cyclopts (4.18.0).
  - Rationale: checked empirically with an `App(name=..., version="0.1.0")`
    carrying an `@app.default` callback. With Cyclopts' default
    `exit_on_error=True`: no arguments → reaches the default, exits `2`; a
    positional token → reaches the default and exits `2` **only if** the default
    accepts `*tokens: str` (a no-arg default raises `UnusedCliTokensError` and
    exits `1`); an unknown `--option` → parser rejects it, prints an error panel
    to stderr, exits `1` (it never reaches the default); `--help`/`-h` → prints
    usage to stdout, exits `0`; `--version` → prints the version to stdout, exits
    `0`. The official docs corroborate the mechanism: `App.exit_on_error` (default
    `True`) calls `sys.exit(1)` on a `CycloptsError` (`CoercionError`,
    `ValidationError`, `UnknownOptionError`, `UnusedCliTokensError`, …); `App.console`
    is stdout (help/version) and `App.error_console` is stderr (errors)
    (cyclopts.readthedocs.io "App Calling & Return Values"). All parser errors
    subclass `cyclopts.CycloptsError`, verified by introspection of
    `cyclopts.exceptions`. The `*tokens: str` signature is therefore mandated so
    positional tokens exit `2`; the unit-test matrix pins all five paths.
  - Date/Author: 2026-06-21, planning agent.
- Decision: stub exit mechanism — register `@app.default`, exit inside it.
  - Rationale: a bare `cyclopts.App` with no registered default prints help and
    exits `0` on no-args, so a `sys.exit(2)` placed in an unreached command body
    would never fire on the no-arg path. `make_stub_app` therefore registers an
    `@app.default` callback that is the stub's only code path; the callback writes
    the stderr message and calls `sys.exit(STUB_EXIT_CODE)`. The entry-point
    callable runs `app()`, which dispatches the no-arg and positional-token paths
    to that default, so the exit is produced by running the app (the no-args test
    exercises the exact code that exits `2`). `make_stub_app` returning an `App`
    is load-bearing, not dead scaffolding.
  - Date/Author: 2026-06-21, planning agent.
- Decision: unit tests drive the app in-process; they do **not** use
  `cyclopts.testing.invoke`.
  - Rationale: `cyclopts.testing` does not exist in the locked cyclopts 4.18.0
    (Surprises). The verified in-process pattern is `pytest.raises(SystemExit)`
    around `app([...], exit_on_error=False)`, asserting `excinfo.value.code`:
    `2` for the no-arg and positional-token paths, `0` for `--help`/`--version`.
    For the unknown-option path, either assert the same `SystemExit(1)` with
    Cyclopts' default `exit_on_error=True` (the e2e and PATH behaviour), or call
    with `exit_on_error=False` inside `pytest.raises(cyclopts.CycloptsError)` to
    assert the parser rejects it. The plan standardizes on the `SystemExit` form
    so the in-process assertions match the real PATH exit codes exactly.
  - Date/Author: 2026-06-21, planning agent.
- Decision: command module path is `novel_ralph_skill/commands/stub.py` with a
  `commands` subpackage; a flat `cli.py` is rejected.
  - Rationale: the `commands` subpackage colocates the five entry points and
    leaves room for the real per-command implementations (design §4.1–§4.5)
    without a later move. The new `novel_ralph_skill/commands/__init__.py` carries
    a module docstring (next entry).
  - Date/Author: 2026-06-21, planning agent.
- Decision: `commands/__init__.py` carries a module docstring.
  - Rationale: `make lint` runs `interrogate --fail-under 100` over the whole
    `novel_ralph_skill` package and Ruff's `D` rules apply to every module. The
    only per-file ignore for `__init__.py` in `pyproject.toml` is `RUF067`, not
    the `D` rules or interrogate, so a new `commands/__init__.py` without a module
    docstring fails the lint gate.
  - Date/Author: 2026-06-21, planning agent.
- Decision: share one stub factory rather than five hand-written apps.
  - Rationale: AGENTS.md DRY and refactoring heuristics; avoids drift across five
    identical bodies and keeps each module docstringed and under 400 lines.
  - Date/Author: 2026-06-21, planning agent.
- Decision: prefer a direct semantic assertion over a `syrupy` snapshot for the
  stub stderr message.
  - Rationale: `AGENTS.md` requires snapshots to capture a meaningful,
    reviewer-useful boundary and to avoid brittle dumps. The stub message is one
    short line that disappears when the command is implemented, so it is not a
    long-lived contract worth a snapshot; assert "the message contains the command
    name and no traceback" directly.
  - Date/Author: 2026-06-21, planning agent.
- Decision: no production cuprum, and no property test, in this task.
  - Rationale: the stubs shell out to nothing (design §4: "cuprum is required
    only where a command shells out (none do in v1)"), so cuprum is not a runtime
    dependency. A stub has a single behaviour, so there is no invariant over a
    range of inputs (design §9: the simpler commands need only snapshot plus
    boundary examples); Hypothesis/CrossHair are out of scope here.
  - Date/Author: 2026-06-21, planning agent.
- Decision: end-to-end shell-out — cuprum for `uv`, scoped subprocess for the
  installed scripts.
  - Rationale: the scripting standards mandate cuprum's allowlist-based execution
    for external processes. The e2e build/venv/install steps run `uv`, a bare
    program name, so they go through a local cuprum catalogue scoped to the test
    file. The final step invokes each of the five installed console-scripts **by
    absolute path** inside the disposable venv's `bin/`. Cuprum cannot do this:
    the catalogue allowlists *bare program names* only (`Program` is a
    `NewType(str)`; `ProgramCatalogue.lookup` resolves a name and raises
    `UnknownProgramError` otherwise — `cuprum/catalogue.py`), and exposes no API
    to allowlist or execute an executable given by absolute path. `uv run
    <command>` is **not** a substitute: `uv run` resolves the command against the
    *project* environment (the worktree's own editable install, whose scripts
    exist after this task), not the freshly built wheel in the disposable venv —
    verified against uv 0.9.21, whose `--no-project` flag exists precisely to
    "avoid discovering the project or workspace", so the default discovers it. The
    decided, verifiable mechanism is a single narrowly-scoped
    `subprocess.run([str(script_path)], capture_output=True, text=True,
    check=False)` per script, where `script_path` is the absolute path under
    `venv/bin/`. This is the only raw-subprocess use in the task; it is taken
    under the plan's Ambiguity tolerance and is justified here, not left for the
    implementer to discover.
  - Date/Author: 2026-06-21, planning agent.
- Decision: locked cuprum catalogue API, verified against source.
  - Rationale: `docs/scripting-standards.md` shows `Catalogue.from_programs("uv")`
    and `sh.scoped(CATALOGUE)`, but the locked cuprum source exposes neither
    `Catalogue` nor `from_programs`. The real public API, read from the source,
    is: `from cuprum import ProgramCatalogue, ProjectSettings` and
    `from cuprum.program import Program`; build
    `catalogue = ProgramCatalogue(projects=(ProjectSettings(
    name="novel-ralph-e2e", programs=(Program("uv"),), documentation_locations=(),
    noise_rules=()),))`; then `from cuprum import sh` and `uv = sh.make(Program("uv"),
    catalogue=catalogue)`, calling `uv("build", "--wheel", …).run_sync()`.
    `cuprum.context.scoped` exists if an ambient context is wanted, but `sh.make`
    accepts `catalogue=` directly, which is the simpler, source-verified path.
    `CommandResult` carries `.exit_code`, `.stdout`, `.stderr`; `RunOutputOptions(
    capture=True)` governs capture (`cuprum/sh.py`). The implementer must re-read
    `cuprum/catalogue.py`, `cuprum/program.py`, and `cuprum/sh.py` against the
    actually-installed cuprum and adjust symbol names if the locked version moved,
    but the invariant is fixed: allowlist exactly `uv`, run it through cuprum, and
    run the installed scripts by absolute path via subprocess.
  - Date/Author: 2026-06-21, planning agent.
- Decision: defer `tomlkit` confirmation to task 1.2.2.
  - Rationale: the roadmap splits dependency confirmation (1.2.2) from
    entry-point wiring (1.2.1). `tomlkit` is already declared; this task leaves
    it in place.
  - Date/Author: 2026-06-21, planning agent.

## Outcomes & retrospective

- All four work items landed as four atomic commits, each gated green by
  `make all` (plus `make markdownlint`/`make nixie` where Markdown changed) and
  reviewed by `coderabbit --agent`. The headline criterion holds: a wheel built
  from this package installs `novel-state`, `novel-done`, `novel-compile`,
  `desloppify`, and `wordcount` onto `PATH`, and each exits `2` with a short
  stderr message and no traceback on a bare invocation, proven end to end by
  `tests/test_console_scripts_e2e.py`.
- Every load-bearing claim the plan verified held on the target machine:
  cyclopts resolved to 4.18.0 and produced the four argument-path exit codes
  (no-arg/positional -> 2, `--help`/`--version` -> 0, unknown `--option` -> 1);
  cuprum resolved to 0.1.0 with the source-verified `ProgramCatalogue` /
  `ProjectSettings` / `sh.make` API and ran `uv 0.9.21`; the
  `@pytest.mark.timeout(180)` override coexisted with the 30s project default
  under `-n auto`.
- Deviations from the plan letter, all minor and forced by the toolchain, were:
  (1) the entry-point callable test pins `sys.argv` and filters cyclopts'
  "invoked without tokens under pytest" `UserWarning`; (2) the e2e test passes
  the project directory explicitly to `uv build` and asserts exactly one wheel
  (round-one review advisory 1), and resolves the venv scripts directory via
  `sysconfig` rather than hardcoding `bin/`; (3) the `subprocess` import in the
  e2e test carries `# noqa: S404` alongside the existing `S603` on the call.
  None changes the public surface or the exit-code contract.
- Tolerances were respected: the change touched eight files (the nine expected
  minus a separate stub-test split was unnecessary) and stayed well within the
  300-net-line and one-runtime-plus-one-dev-dependency budgets. No escalation
  was required; `make all` never needed more than one fix attempt on any gate
  (one `S404` import lint on work item 3).
- coderabbit returned findings only once across the four runs: a single minor
  second-person-pronoun fix in this plan's Purpose section on work item 1. Work
  items 2, 3, and 4 each returned zero findings.

## Context and orientation

The repository is a Python package skeleton that will become the deterministic
spine of the novel-ralph harness. Orient yourself with these files, all paths
relative to the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-1`:

- `pyproject.toml` — project metadata, dependencies, Ruff/Pylint/pytest config,
  and the hatchling build. `[project.dependencies]` currently lists `tomlkit`.
  `[tool.hatch.build.targets.wheel]` packages `novel_ralph_skill`. There is no
  `[project.scripts]` table yet. `requires-python = ">=3.14"`.
- `novel_ralph_skill/__init__.py` — package entrypoint. Currently exports a
  placeholder `hello()` with an optional Rust-extension fallback.
- `novel_ralph_skill/pure.py` — the pure-Python `hello()` placeholder.
- `tests/test_stub.py` — the single existing test, asserting `hello()` returns
  its greeting. New tests live alongside it under `tests/`. There is no
  `conftest.py` yet.
- `Makefile` — `make all` runs `build check-fmt lint typecheck test`. `make
  build` is `uv sync --group dev`. `make build-release` builds the sdist and
  wheel via `python -m build`. `make test` runs `uv run pytest -v -n auto`. `make
  markdownlint` and `make nixie` gate Markdown and Mermaid.

Terms of art, defined here so the plan is self-contained:

- **Console-script entry point.** A `name = "module:function"` line under
  `[project.scripts]` in `pyproject.toml`. Installing the package writes an
  executable `name` onto `PATH` that calls `function`. This is the distribution
  mechanism ADR 004 fixes.
- **Cyclopts application.** An instance of `cyclopts.App`. Calling `app()` runs
  the CLI: it parses arguments and dispatches to a registered command function.
  Cyclopts is the project's CLI framework per `docs/scripting-standards.md`.
- **Stub.** A placeholder implementation that satisfies the interface (a command
  exists, is invocable, returns a defined exit code) but performs none of the
  real work. Here every stub reports "not implemented" and exits `2`.
- **Exit-code contract.** The shared interface contract
  (`docs/adr-003-shared-interface-contract.md`, design §3.2) reserves: `0`
  success, `1` benign negative, `2` usage error, `3` state/input error, `4`
  actionable finding. Stubs use `2` for their command result.

Authoritative sources to read before editing:

- `docs/roadmap.md` step 1.2 and task 1.2.1 — the task's success criteria.
- `docs/adr-004-distribution-console-scripts.md` — why console-scripts.
- `docs/adr-005-command-surface-five-scripts.md` — why five names, not a
  multiplexer.
- `docs/adr-003-shared-interface-contract.md` and design §3.2 — the exit-code
  table the stub exit must honour.
- `docs/novel-ralph-harness-design.md` §4 — the five commands and that "Each is
  a Cyclopts application exposed as a console-script in `novel_ralph_skill`", and
  that cuprum is required only where a command shells out (none do in v1).
- `docs/scripting-standards.md` — the Cyclopts pattern (`App`, `@app.default` /
  command functions, `def main(): app()` entrypoint) and the cuprum section.
  Note: its `cyclopts.testing.invoke` and `Catalogue.from_programs` examples do
  not match the locked versions (see Surprises); use the verified patterns this
  plan pins instead.
- `AGENTS.md` — quality gates, en-GB Oxford spelling, 400-line limit, 100%
  docstring coverage, tests under `tests/`.

Skills to load before touching code (per the global agent instructions and the
worktree standing rules):

- `python-router` first, to route to the smaller skills below.
- `python-types-and-apis` for the public signatures of the stub factory and
  entry-point callables.
- `python-errors-and-logging` for the "not implemented" exit path (narrow
  failure, no bare `except`, no traceback leak).
- `python-testing` for fixtures, marks, the `SystemExit` boundary, and the
  slow-e2e/xdist interaction.
- `python-verification` is consulted only to confirm that no property test is
  warranted here (a stub has a single behaviour); `hypothesis`/`crosshair`/
  `mutmut` are out of scope for this task.
- `leta` for navigating the package; `sem` for history.

## Plan of work

The work proceeds in four atomic, independently-committable work items. Each
ends with its own validation, and `make all` must be green before the work item
is committed. Stage ordering is deliberate: the dependency lands first so the
import resolves, then the stub surface with red-then-green unit tests, then the
entry-point registration with the build-install proof, then the docs.

### Work item 1 — Add the `cyclopts` runtime dependency

Implements: ADR 004 (one shared dependency set), design §4 (each command is a
Cyclopts application), `docs/scripting-standards.md` (Cyclopts is the default CLI
framework).

Edit `pyproject.toml` `[project.dependencies]`, changing
`dependencies = ["tomlkit"]` to add `cyclopts`, kept alphabetical:
`dependencies = ["cyclopts", "tomlkit"]`. Leave `tomlkit` in place; its
confirmation is task 1.2.2. Leave `cyclopts` unpinned (or floor it only if a
constraint is warranted) so it takes the locked resolution; at planning time that
resolved to cyclopts 4.18.0.

Run `make build` to refresh `uv.lock`, then `make audit`.

Read first: `docs/scripting-standards.md` (Cyclopts rationale and version note),
`.rules/python-pyproject.md`.

Skills: `python-router`.

Tests: no new unit test for this item alone — adding a dependency has no
behaviour to assert until work item 2 imports it. The validation is that
`make build` resolves `cyclopts` into `uv.lock` and `make audit` passes. Commit
this item only once both succeed.

Validation:

- `make build` succeeds and `uv.lock` now contains a `cyclopts` entry.
- `make audit` passes (no known vulnerability in `cyclopts`).
- `make all` passes (the existing `tests/test_stub.py` still passes; nothing else
  changed).

### Work item 2 — Add the stub command surface with unit tests

Implements: design §4 (five Cyclopts applications), ADR 005 (five distinct
commands), ADR 003 / design §3.2 (exit code `2` = usage error), ADR 001 / design
§2.2 (no real behaviour, no judgement).

Create a `commands` subpackage (path fixed by the Decision Log, no alternative):
`novel_ralph_skill/commands/__init__.py` and
`novel_ralph_skill/commands/stub.py`.

`novel_ralph_skill/commands/__init__.py` **must carry a module docstring** (a
single line such as `"""Console-script entry points for the deterministic
spine."""`). This is not optional: `make lint` runs `interrogate --fail-under
100` over `novel_ralph_skill` and Ruff's `D` rules apply to every module; the
only `__init__.py` per-file ignore in `pyproject.toml` is `RUF067`, not the `D`
rules or interrogate, so an undocumented `__init__.py` fails the lint gate.

In `stub.py`, define one factory and the five entry-point callables (exact
construction in Interfaces). The factory `make_stub_app(name)`:

1. constructs `app = cyclopts.App(name=name)`;
2. registers an `@app.default` callback — the stub's only code path — that takes
   `*tokens: str` (so positional tokens route to it and exit `2` rather than
   raising `UnusedCliTokensError`; verified against cyclopts 4.18.0) and whose
   body writes a short "`<name>` is not yet implemented" line to stderr and calls
   `sys.exit(STUB_EXIT_CODE)` (module constant `STUB_EXIT_CODE = 2`, the single
   call site); and
3. returns `app`.

Each of the five callables is the console-script target: it calls
`make_stub_app("<command-name>")` and then runs `app()`, mirroring the
`def main(): app()` pattern in `docs/scripting-standards.md`. The exit is
produced by *running the app*, not by the callable calling `sys.exit` directly,
so `make_stub_app` returning an `App` is load-bearing. Each callable and the
factory carries a numpy-style docstring (Ruff `D` and `interrogate --fail-under
100` require it).

Keep the message human prose on stderr; do **not** emit the JSON envelope. The
envelope and `--human` switch are roadmap step 1.3 (the shared scaffolding
module), explicitly out of scope here. Note this boundary in a `# why:` comment
so a later reader does not mistake the stub for a contract violation.

Add unit tests under `tests/test_command_stubs.py`. These are the red-green
tests: write them to assert exit `2` and the per-command message before the stubs
are complete (they fail), then make them pass. Drive each app **in-process** —
do not import `cyclopts.testing.invoke`, which does not exist in the locked
cyclopts (Surprises). Use a `pytest.raises(SystemExit)` guard around
`app([...], exit_on_error=False)` and assert `excinfo.value.code`. Parametrize
over the five command/callable pairs so the five are asserted uniformly without
copied bodies. Cover:

- No arguments → exits `2` (exercises the registered `@app.default` callback, the
  code path that produces the exit).
- A positional token (e.g. `["foo"]`) → exits `2` (routes to the `*tokens`
  default; verified).
- An unknown `--option` (e.g. `["--nope"]`) → exits `1`. Assert with Cyclopts'
  default `exit_on_error=True` inside `pytest.raises(SystemExit)` and
  `excinfo.value.code == 1`, matching the real PATH behaviour. This pins the
  carve-out so a later reader cannot mistake the parser's exit `1` for a stub
  bug.
- `--help` → exits `0`, and `--version` → exits `0` (parser carve-outs; both
  pinned, the `--version` assertion required not optional).
- The stderr message names the command and contains no `"Traceback"` (assert on
  the no-arg/positional paths, where the stub body runs). Capture stderr via
  `capsys`.

Prefer a direct semantic assertion over a `syrupy` snapshot for the stderr
message (Decision Log).

Read first: `docs/scripting-standards.md` (Cyclopts `App` pattern, `main()`
entrypoint), `docs/novel-ralph-harness-design.md` §3.2 and §4,
`.rules/python-typing.md`, `.rules/python-return.md`,
`.rules/python-exception-design-raising-handling-and-logging.md`.

Skills: `python-router`, then `python-types-and-apis` (factory/callable
signatures), `python-errors-and-logging` (the exit path; narrow, no bare
`except`, no leaked traceback), `python-testing` (parametrization and the
`SystemExit` boundary).

Tests added/updated:

- `tests/test_command_stubs.py` — unit tests, parametrized over the five
  commands, asserting exit `2` for no-arg and positional-token invocations, that
  stderr names the command without a traceback, that `--help` and `--version`
  each exit `0`, and that an unknown `--option` exits `1`. These are CLI
  error-path tests per design §9.
- No property test (no range invariant; Decision Log).

Validation:

- The new tests fail before `stub.py` is complete and pass after (red → green).
- `make test` passes; `make lint` (Ruff + `interrogate --fail-under 100` +
  Pylint), `make check-fmt`, and `make typecheck` (`ty`) pass.
- `make all` is green.

### Work item 3 — Register the five entry points and prove install

Implements: roadmap task 1.2.1 success criterion ("a wheel build installs all
five commands; each is invocable on `PATH` and reports a usage error rather than
crashing"), ADR 004 (`[project.scripts]` registration), ADR 005 (five names).

Add a `[project.scripts]` table to `pyproject.toml` mapping each command name to
its callable in the module from work item 2:

```toml
[project.scripts]
novel-state = "novel_ralph_skill.commands.stub:novel_state"
novel-done = "novel_ralph_skill.commands.stub:novel_done"
novel-compile = "novel_ralph_skill.commands.stub:novel_compile"
desloppify = "novel_ralph_skill.commands.stub:desloppify"
wordcount = "novel_ralph_skill.commands.stub:wordcount"
```

Add `cuprum` to `[dependency-groups] dev` in `pyproject.toml` (test-only; it must
not enter `[project.dependencies]`), then `make build` to refresh `uv.lock` and
`make audit` to clear it.

Register the `slow` marker so the e2e test's mark is declared. Add to
`pyproject.toml` `[tool.pytest.ini_options]`:

```toml
markers = ["slow: end-to-end tests that build and install a wheel"]
```

Add a **fast** unit test, `tests/test_pyproject_scripts.py`, that parses
`pyproject.toml` with the standard-library `tomllib` and asserts the
`[project.scripts]` table lists exactly the five expected names mapping to
`novel_ralph_skill.commands.stub:<callable>`. This guards against a typo'd or
dropped entry point and runs in-process (no slow mark).

Add an **end-to-end** test, `tests/test_console_scripts_e2e.py`, decorated
`@pytest.mark.slow` and `@pytest.mark.timeout(180)`. The 180s per-test override
supersedes the 30s project default for this single test and does so under
`-n auto` (xdist) — see Risk 3 and the Concrete-steps probe. The test:

1. builds the wheel into `tmp_path` with `uv build --wheel --out-dir <tmp>`;
2. creates a throwaway virtual environment under `tmp_path` with
   `uv venv <tmp/venv>`;
3. installs the built wheel into it with
   `uv pip install --python <tmp/venv/bin/python> <wheel>`; and
4. runs each of the five console-scripts from that venv's `bin/` (by absolute
   path) with no arguments and asserts exit `2` and no `"Traceback"` on stderr.

Steps 1–3 run `uv` — a bare program name — through a **local cuprum catalogue**
scoped to the test file, built with the **source-verified locked cuprum API**
(Decision Log "Locked cuprum catalogue API, verified against source"):

```python
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program

_CATALOGUE = ProgramCatalogue(
    projects=(
        ProjectSettings(
            name="novel-ralph-e2e",
            programs=(Program("uv"),),
            documentation_locations=(),
            noise_rules=(),
        ),
    )
)
_uv = sh.make(Program("uv"), catalogue=_CATALOGUE)
# _uv("build", "--wheel", "--out-dir", str(out_dir)).run_sync()
```

Before relying on these symbols, re-read `cuprum/catalogue.py`,
`cuprum/program.py`, and `cuprum/sh.py` against the actually-installed cuprum and
adjust if the locked version moved; the invariant is fixed (allowlist exactly
`uv`). Read `CommandResult.exit_code`/`.stdout`/`.stderr` (`cuprum/sh.py`) to
assert each `uv` step succeeded.

Step 4 is the **single justified raw-subprocess exception** (Decision Log
"End-to-end shell-out"). Cuprum allowlists *bare program names* only and exposes
no API to allowlist or execute an absolute path (`cuprum/catalogue.py`;
`Program` is `NewType(str)`), so it cannot run `<tmp/venv/bin/novel-state>`. Run
each installed script directly by absolute path:

```python
import subprocess

result = subprocess.run(  # noqa: S603 - path is a known tmp_path Path, not user input
    [str(script_path)],            # absolute path under venv/bin, no PATH lookup
    capture_output=True,
    text=True,
    check=False,                   # we assert returncode ourselves
)
assert result.returncode == 2
assert "Traceback" not in result.stderr
assert command_name in result.stderr
```

Do **not** invoke the scripts via `uv run <command>`: `uv run` resolves the
command against the *project* environment (the worktree's own editable install,
whose scripts exist after this task), not the freshly built wheel in the
disposable venv (verified against uv 0.9.21; its `--no-project` flag exists to
avoid project discovery, so the default discovers it). That would yield a green
test that never exercises the installed wheel.

Read first: `docs/adr-004-distribution-console-scripts.md`,
`docs/adr-005-command-surface-five-scripts.md`, `.rules/python-pyproject.md`,
`docs/scripting-standards.md` (the cuprum section — illustrative only; pin the
real API per the Decision Log), the Makefile `build-release` target,
`/data/leynos/Projects/cuprum/cuprum/catalogue.py`, `.../program.py`, `.../sh.py`.

Skills: `python-router`, `python-testing` (slow marks, timeouts, the
build-install e2e boundary, the xdist interaction). `cmd-mox` is not used — the
test runs the real `uv` and the real installed scripts to prove the install;
mocking would defeat its purpose.

Tests added/updated:

- `tests/test_pyproject_scripts.py` — fast unit test asserting the five
  `[project.scripts]` entries map to the expected callables.
- `tests/test_console_scripts_e2e.py` — end-to-end: build the wheel with `uv`
  (via the cuprum catalogue), install into a fresh `uv venv`, then run each of the
  five console-scripts by absolute path from the venv `bin/` (one scoped
  `subprocess.run`), asserting exit `2` and no traceback. Marked
  `@pytest.mark.slow` and `@pytest.mark.timeout(180)`. This is the
  externally-observable command-line behaviour `AGENTS.md` requires an e2e test
  for, and the roadmap's explicit success criterion.

Validation:

- `make build-release` (or the e2e test's own build step) produces a wheel whose
  `entry_points` register all five commands.
- The fast `test_pyproject_scripts.py` passes; the e2e test passes (each
  console-script resolves and exits `2`).
- `make all` is green.

### Work item 4 — Document the wired command surface

Implements: `AGENTS.md` "Documentation maintenance" (update users' and
developers' guides for behaviour and interface changes), ADR 004/005 (record the
realized wiring).

Update `docs/developers-guide.md` (it already has a "The five commands" section
referencing ADR 004/005) to note that the entry points are now wired as stubs
that exit `2` until each slice implements its command, and to point at the stub
module and the e2e test. Update `docs/users-guide.md` to list the five installed
command names and the current "not yet implemented; exits 2" status, so a user
who installs the wheel today understands what they will see.

If a Mermaid diagram is added or changed, run `make nixie`. All Markdown changes
run through `make markdownlint`. Wrap prose at 80 columns and use en-GB Oxford
spelling per `AGENTS.md`.

Read first: `docs/developers-guide.md`, `docs/users-guide.md`,
`docs/documentation-style-guide.md`, `AGENTS.md` "Markdown guidance".

Skills: `python-router` is not needed (docs only). Follow `AGENTS.md` Markdown
rules and the `en-gb-oxendict` convention.

Tests: none (documentation only).

Validation:

- `make markdownlint` passes on the changed Markdown.
- `make nixie` passes if any Mermaid diagram was touched (run it regardless if a
  diagram exists in a changed file).
- `make all` remains green (re-run to confirm no accidental code edit slipped
  in).

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-1`.

Confirm the branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-1 branch --show-current
```

Expect `roadmap-1-2-1`.

Per work item, the validation commands are:

```bash
make build      # refresh lock, install deps (work items 1 and 3)
make audit      # dependency vulnerability gate (work items 1 and 3)
make all        # build check-fmt lint typecheck test (every work item)
```

For the Markdown work item:

```bash
make markdownlint
make nixie       # only required if a Mermaid diagram is present/changed
```

Before relying on the per-test timeout override under xdist (work item 3),
confirm it empirically with a throwaway probe (delete it afterwards): a test
sleeping a few seconds, marked `@pytest.mark.timeout(<large>)`, must pass under
`uv run pytest -n auto` while the project `timeout = 30` is temporarily lowered.
This was verified at planning time; re-confirm on the target machine.

Expected high-level transcripts (illustrative):

After work item 2, running the unit suite:

```plaintext
$ make test
... tests/test_command_stubs.py::test_stub_exits_two[novel-state] PASSED
... tests/test_command_stubs.py::test_stub_exits_two[novel-done] PASSED
... (five commands) ...
===== N passed in Xs =====
```

After work item 3, the e2e proof (illustrative):

```plaintext
$ novel-state            # from the installed venv
novel-state is not yet implemented
$ echo $?
2
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- Building and installing a wheel from this package puts five executables —
  `novel-state`, `novel-done`, `novel-compile`, `desloppify`, `wordcount` — on
  `PATH`. Running any of them with no arguments prints a short "not yet
  implemented" message to stderr and exits `2`. None prints a Python traceback.
- The new unit test `tests/test_command_stubs.py` fails before the stub module
  exists and passes after; for each of the five commands it asserts exit `2` on
  the no-arg and positional-token paths, exit `0` for `--help` and `--version`,
  and exit `1` for an unknown `--option`.
- The fast unit test `tests/test_pyproject_scripts.py` asserts the
  `[project.scripts]` table lists exactly the five names mapping to the stub
  callables.
- The end-to-end test `tests/test_console_scripts_e2e.py` builds the wheel with
  `uv` (through a local cuprum catalogue), installs it into a fresh `uv venv`,
  and confirms all five console-scripts resolve in the venv `bin/` and exit `2`
  when run **by absolute path** (one scoped `subprocess.run`, never via
  `uv run`). It is marked `@pytest.mark.slow` and `@pytest.mark.timeout(180)`.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new unit and e2e tests are present and green;
  the pre-existing `tests/test_stub.py` still passes.
- Lint/typecheck: `make lint` (Ruff, `interrogate --fail-under 100`, Pylint),
  `make check-fmt` (`ruff format --check`), and `make typecheck` (`ty check`) all
  pass.
- Audit: `make audit` (`pip-audit`) passes against the added `cyclopts` (and dev
  `cuprum`).
- Markdown: `make markdownlint` passes; `make nixie` passes if any Mermaid
  diagram was changed.
- Aggregate: `make all` is green at each commit.

Quality method (how we check): run `make all` before and after each work item;
run `make audit` after work items 1 and 3; run `make markdownlint` (and `make
nixie` when a diagram is touched) after the documentation work item.

## Idempotence and recovery

- Editing `pyproject.toml` is idempotent; re-running `make build` reconciles
  `uv.lock` deterministically.
- The unit tests are pure and re-runnable.
- The e2e test builds and installs into a `tmp_path`-scoped throwaway
  environment, so repeated runs neither pollute nor depend on the developer's
  environment; pytest's `tmp_path` cleans it up.
- If `make build` leaves a partial or inconsistent environment, `make clean`
  then `make build` restores a known state (the Makefile `clean` target removes
  `.venv`, `.uv-cache`, and build artefacts).
- No step is destructive to tracked files beyond the intended edits to
  `pyproject.toml`, the new modules, the new tests, and the two docs.

## Artefacts and notes

- The five command names, verbatim, from ADR 005: `novel-state`, `novel-done`,
  `novel-compile`, `desloppify`, `wordcount`.
- The exit-code table the stub honours (design §3.2): `0` success, `1` benign
  negative, `2` usage error, `3` state/input error, `4` actionable finding. The
  stub uses `2` for its command result.
- Supplementary manual e2e transcript (documentation of the automated flow; the
  automated `tests/test_console_scripts_e2e.py` is the proof of record). Run from
  the worktree root:

```plaintext
$ uv build --wheel --out-dir /tmp/nrs-e2e
$ uv venv /tmp/nrs-e2e/venv
$ uv pip install --python /tmp/nrs-e2e/venv/bin/python /tmp/nrs-e2e/*.whl
$ /tmp/nrs-e2e/venv/bin/novel-state ; echo $?
novel-state is not yet implemented
2
$ /tmp/nrs-e2e/venv/bin/wordcount ; echo $?
wordcount is not yet implemented
2
```

  Each of the five scripts behaves identically.

## Interfaces and dependencies

Dependencies (work items 1 and 3), in `pyproject.toml`:

- `cyclopts` as a runtime dependency in `[project.dependencies]` (the CLI
  framework, per `docs/scripting-standards.md`). One new runtime dependency only.
- `cuprum` as a *dev* dependency in `[dependency-groups] dev` (work item 3): the
  e2e test shells out to `uv` (build/venv/install) through a local cuprum
  catalogue. The five installed scripts are then run by absolute path via one
  scoped `subprocess.run` (cuprum cannot allowlist an absolute path — verified;
  Decision Log). `cuprum` is test-only and must not enter `[project.dependencies]`.

Public interface at the end of the task, in `novel_ralph_skill.commands.stub`
(module path fixed; there is no `cli.py` alternative). The new
`novel_ralph_skill/commands/__init__.py` carries a one-line module docstring (to
satisfy `interrogate --fail-under 100` and Ruff `D`).

The construction is shown so the no-arg path provably reaches the exit:

```python
"""Stub console-script entry points for the deterministic spine."""

from __future__ import annotations

import sys

import cyclopts

STUB_EXIT_CODE = 2


def make_stub_app(name: str) -> cyclopts.App:
    """Build a Cyclopts app whose command-result invocation exits 2.

    A default callback taking ``*tokens`` is registered so the no-argument path
    and any positional-token path both reach user code and exit with
    :data:`STUB_EXIT_CODE`. The ``*tokens`` parameter is load-bearing: without it
    a positional token raises ``UnusedCliTokensError`` and exits ``1`` instead of
    reaching the body (verified against cyclopts 4.18.0). The Cyclopts parser
    handles three classes before the default runs and they are exempt from the
    exit-code contract (design §3.2 governs results): ``--help``/``-h`` and
    ``--version`` exit ``0``, and an unknown ``--option`` exits ``1``.
    """
    app = cyclopts.App(name=name)

    @app.default
    def _not_implemented(*tokens: str) -> None:
        """Report that ``name`` is not yet implemented and exit 2."""
        del tokens  # accepted so positional tokens route here, not to an error
        # why: stubs emit human prose only; the JSON envelope is task 1.3.1.
        print(f"{name} is not yet implemented", file=sys.stderr)
        sys.exit(STUB_EXIT_CODE)

    return app


def novel_state() -> None:
    """Console-script entry point for ``novel-state`` (stub; exits 2)."""
    make_stub_app("novel-state")()


def novel_done() -> None:
    """Console-script entry point for ``novel-done`` (stub; exits 2)."""
    make_stub_app("novel-done")()


def novel_compile() -> None:
    """Console-script entry point for ``novel-compile`` (stub; exits 2)."""
    make_stub_app("novel-compile")()


def desloppify() -> None:
    """Console-script entry point for ``desloppify`` (stub; exits 2)."""
    make_stub_app("desloppify")()


def wordcount() -> None:
    """Console-script entry point for ``wordcount`` (stub; exits 2)."""
    make_stub_app("wordcount")()
```

Each callable delegates to ``app()``; the exit is produced by running the app,
not by the callable calling ``sys.exit`` directly, so ``make_stub_app`` returning
an ``App`` is load-bearing. The ``@app.default`` decorator, the ``name=``
argument, and the four argument-path exit codes (no-arg/positional → 2,
``--help`` → 0, ``--version`` → 0, unknown ``--option`` → 1) are verified for
cyclopts 4.18.0 (Decision Log). Re-confirm them against the locked version
when implementing; if a helper name differs, adjust the call but keep the
invariants —
the no-arg and positional-token paths must reach the exit and produce ``2``, and
the carve-out codes must be the ones the unit test asserts.

Entry-point registration at the end of the task, in `pyproject.toml`:

```toml
[project.scripts]
novel-state = "novel_ralph_skill.commands.stub:novel_state"
novel-done = "novel_ralph_skill.commands.stub:novel_done"
novel-compile = "novel_ralph_skill.commands.stub:novel_compile"
desloppify = "novel_ralph_skill.commands.stub:desloppify"
wordcount = "novel_ralph_skill.commands.stub:wordcount"
```

Out of scope (later roadmap tasks, do not build here): the shared JSON envelope,
the `--human` switch, and the exit-code helper (task 1.3.1, design §3.1–§3.2);
the `tomlkit` confirmation (task 1.2.2); any real command behaviour
(`novel-state` subcommands, the compile-and-hash routine, the desloppify rule
pack, the wordcount gates) — design §4.1–§4.5.

## Revision note

- 2026-06-21 (planning round 1): Authored the self-contained plan against the
  locked toolchain, verifying every load-bearing claim empirically rather than
  from memory. Verified that `cyclopts` resolves to 4.18.0 under the
  `requires-python >=3.14` floor; that with the default `exit_on_error=True` a
  stub default callback taking `*tokens` exits `2` on no-arg and positional
  paths, `--help` and `--version` exit `0`, and an unknown `--option` exits `1`
  (the parser path, corroborated by the official "App Calling & Return Values"
  docs). Discovered and worked around two doc/reality gaps. First,
  `cyclopts.testing.invoke` does not exist in 4.18.0, so the tests use the
  in-process `pytest.raises(SystemExit)` pattern around
  `app([...], exit_on_error=False)`. Second, the locked cuprum exposes
  `ProgramCatalogue(projects=...)` with `ProjectSettings` and `Program`, not
  `Catalogue.from_programs`, so the e2e `uv` catalogue is pinned to the real
  source-verified API. Pinned the e2e shell-out discipline (cuprum for
  `uv`; one justified absolute-path `subprocess.run` for the installed scripts,
  because cuprum cannot allowlist an absolute path and `uv run` resolves against
  the project env — verified against uv 0.9.21). The plan remains in DRAFT pending
  approval; no implementation has begun.
- 2026-06-21 (implementation): Executed all four work items in order as four
  atomic, separately-gated commits. Status moved DRAFT -> IN PROGRESS -> DONE.
  Progress ticks, the Outcomes & retrospective section, and the per-item
  deviation notes record the results; every predicted toolchain fact held.
