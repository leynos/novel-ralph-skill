# Decide and enforce a cross-platform policy for the console-scripts e2e test

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

This is roadmap task 1.2.3 (`docs/roadmap.md` lines 104-111, step 1.2). It
closes a low-severity remediation raised against task 1.2.1: the wheel-build
end-to-end test `tests/test_console_scripts_e2e.py` is only half-portable on
Windows. Its `_venv_scripts_dir` helper resolves the venv scripts directory
through the `nt_user` sysconfig scheme on `win32` (a roaming per-user path,
**not** the venv `Scripts/` directory `uv venv` creates) and then looks up
`scripts_dir / command_name` with **no `.exe` suffix**, so the test would not
find the installed console-scripts on Windows even though it pretends to support
that platform. The roadmap directs the work to "either commit to Linux-only
execution or make the lookup truly portable".

The deliverable is a **decision, enforced in code and recorded in an ADR**, not
a menu. After research (see Decision Log and Surprises) this plan commits to
**POSIX-only execution of this single e2e test**, made explicit by a guard that
skips the test on non-POSIX platforms, and corrects the venv-path lookup to the
canonical `venv` sysconfig scheme so the resolution is correct on the platform
the test does run on. The policy matches reality: the only environment that runs
`make test` — and therefore this test — is `ubuntu-latest`
(`.github/workflows/ci.yml` line 10; the Windows and macOS entries in
`.github/workflows/build-wheels.yml` only build wheels with `cibuildwheel` and
never invoke `pytest`). A test that branches on `win32` but is never executed on
Windows is dead, untested, and — as verified — wrong; committing to POSIX-only
makes the contract honest.

A second, independently valuable correction rides on the same research. The
test's module docstring asserts that the installed scripts must be run by a raw
`subprocess.run` because "cuprum's catalogue allowlists bare program names only
and exposes no API to execute an absolute path". **That claim is false against
the locked cuprum 0.1.0** (verified empirically — see Surprises). cuprum 0.1.0
allowlists *any* `Program` string, including an absolute path, and executes it
verbatim as `argv[0]` through `asyncio.create_subprocess_exec`. The raw
`subprocess.run` (with its `# noqa: S404` and `# noqa: S603` security
suppressions) is therefore avoidable: the installed console-scripts can be run
through cuprum by absolute path, bringing the test into line with the scripting
standards (`docs/scripting-standards.md`, "Cyclopts + cuprum + pathlib"), which
require external programs to run through a curated cuprum catalogue rather than
through `subprocess`. This removes two `noqa` suppressions and a `subprocess`
import from the suite.

To verify the implementation: `make test` (Linux) still proves all five
console-scripts build into a wheel, install into a fresh `uv venv`, resolve on
disk, and exit `2`; the test runs the installed scripts through a cuprum
catalogue keyed on their absolute paths, with no `subprocess` import and no
`# noqa: S404/S603`; the venv scripts directory is resolved through the `venv`
sysconfig scheme; and the test is skipped with a clear reason on any non-POSIX
platform. A new accepted ADR records the POSIX-only policy and its rationale so
the choice is not silently re-litigated when a future contributor re-adds a
Windows branch.

Success is observable as: `make test` green on Linux with the e2e test passing
through cuprum (no `subprocess`); `os.name != "posix"` causing the test to
report `SKIPPED` rather than executing a broken Windows path; a focused unit
test that proves the venv-scripts resolver returns the `uv venv` bin directory
(and that the resolver is POSIX-shaped); a new `docs/adr-006-*.md` accepted and
linked from the design doc and developers' guide; and `make all`,
`make markdownlint`, and `make nixie` all green.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- All work must stay exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-3`. Files in the
  root/control worktree must not be edited.
- The locked cuprum version is **0.1.0** (`uv.lock`). The plan must use only the
  cuprum 0.1.0 public API: `ProgramCatalogue(projects=...)`, `ProjectSettings`,
  `cuprum.program.Program`, `sh.make(program, catalogue=...)`, and
  `SafeCmd.run_sync(capture=..., context=ExecutionContext(...))` returning a
  `CommandResult` with `.exit_code`, `.stdout`, `.stderr` (verified against the
  `v0.1.0` tag of `/data/leynos/Projects/cuprum`:
  `cuprum/catalogue.py`, `cuprum/program.py`, `cuprum/sh.py`). Do **not** use
  `Catalogue.from_programs`, `sh.scoped`, or any helper shown only in the
  scripting-standards reference snippet — those names do not exist in 0.1.0
  (verified: `cuprum/__init__.py` `__all__` at the `v0.1.0` tag).
- External programs run through a curated cuprum catalogue, never through
  `subprocess` (`docs/scripting-standards.md`). This task **removes** the raw
  `subprocess.run`, its `import subprocess`, and the `# noqa: S404`/`# noqa: S603`
  suppressions; it must not add any new `subprocess` use or new `noqa`.
- The test's externally observable contract is unchanged: a wheel is built,
  installed into a fresh `uv venv`, and each of the five console-scripts
  (`novel-state`, `novel-done`, `novel-compile`, `desloppify`, `wordcount`) is
  resolved on disk and run with no arguments, asserting exit `2`, no `Traceback`
  in stderr, and the command name echoed in stderr. These assertions must not be
  weakened.
- This task does **not** change any command body, the stub factory
  (`novel_ralph_skill/commands/stub.py`), the entry-point table
  (`pyproject.toml [project.scripts]`), or any other test's behaviour. It does
  **not** add a single source of truth for the command names — that is roadmap
  task 1.2.4 (`docs/roadmap.md` lines 112-117); the `COMMAND_NAMES` tuple in this
  test stays as-is.
- The `slow` marker and the per-test `@pytest.mark.timeout(180)` override stay.
  pytest-timeout 2.4.0 documents that a per-test `@pytest.mark.timeout`
  overrides the project-wide `timeout = 30` (`pyproject.toml` line 307), and the
  override is applied per item in each xdist worker (verified against the
  official pytest-timeout 2.4.0 documentation — see Decision Log).
- Prose, comments, ADR, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` convention.
- Every public module, class, and function carries a docstring; `interrogate`
  enforces 100% coverage (AGENTS.md; Makefile `lint-python`). No file exceeds
  400 lines (AGENTS.md).
- Tests live in the top-level `tests/` tree, never inside the package
  (AGENTS.md, "Python verification and testing").
- Markdown prose wraps at 80 columns; code blocks at 120; tables and headings are
  not wrapped; list bullets use `-`; Mermaid is validated by nixie (AGENTS.md
  "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 5 files or more than
  220 net lines, stop and escalate. Expected files: this plan,
  `tests/test_console_scripts_e2e.py` (rewrite of the run loop and the scheme),
  a new `tests/test_venv_scripts_dir.py` (focused unit test for the resolver),
  `docs/adr-006-console-scripts-e2e-posix-policy.md` (new ADR), and one or two
  one-line cross-reference additions to `docs/novel-ralph-harness-design.md` and
  `docs/developers-guide.md`. If any **command body**, `pyproject.toml`, or the
  stub factory must change, stop and escalate — that is outside 1.2.3.
- Dependencies: this task adds **no** new runtime or dev dependency. cuprum,
  cyclopts, pytest-timeout, and pytest-xdist are already locked. If running the
  installed scripts through cuprum appears to require a new dependency or a
  cuprum API absent from 0.1.0, stop and escalate (the empirical check in
  Surprises says it does not).
- Policy ambiguity: this plan commits to POSIX-only. If review prefers
  "make the lookup truly portable on Windows" instead, that is a **materially
  different** implementation (a real Windows `Scripts/` + `.exe` lookup that
  cannot be tested in this Linux-only CI, plus an ADR recording the opposite
  decision). Policies must not switch mid-implementation; stop and escalate so
  the ADR and the guard are rewritten coherently.
- cuprum behaviour: if, on the target machine, cuprum 0.1.0 fails to execute an
  allowlisted absolute-path program (contradicting the verified check in
  Surprises), stop and escalate rather than silently restoring `subprocess.run`.
- Iterations: if `make all` (or `make markdownlint` / `make nixie`) still fails
  after 3 focused fix attempts on the same gate, stop and escalate.

## Risks

- Risk: a future contributor re-introduces a `win32` branch, recreating the
  exact dead, wrong code this task removes.
  - Severity: low. Likelihood: medium.
  - Mitigation: the new ADR (`adr-006`) records the POSIX-only decision and its
    rationale (CI runs the suite only on Linux); the test's skip guard carries a
    `# why:` comment pointing at the ADR; the design doc and developers' guide
    link the ADR. The decision is therefore discoverable before re-litigation.
- Risk: the cuprum-by-absolute-path rewrite changes the captured stderr text or
  exit code semantics versus `subprocess.run`, weakening the assertions.
  - Severity: low. Likelihood: low.
  - Mitigation: cuprum 0.1.0 `run_sync(capture=True)` returns
    `CommandResult.exit_code` and `.stderr` from the same
    `asyncio.create_subprocess_exec` primitive `subprocess` wraps; the existing
    assertions (`exit_code == 2`, `"Traceback" not in stderr`, `name in stderr`)
    map one-to-one onto `result.exit_code` and `result.stderr`. Verified locally
    that an allowlisted absolute-path program runs and captures stdout/stderr
    (Surprises). The assertions are preserved verbatim in meaning.
- Risk: the `venv` sysconfig scheme is unavailable on an older interpreter,
  breaking the resolver.
  - Severity: low. Likelihood: very low.
  - Mitigation: `requires-python = ">=3.14"` (`pyproject.toml` line 6); the
    `venv` scheme has existed since Python 3.11 and is the **default** scheme on
    3.14 (verified locally: `sysconfig.get_default_scheme() == "venv"`). The new
    unit test asserts the resolver returns the `uv venv` bin directory, tripping
    immediately if the scheme regresses.
- Risk: removing the `subprocess` import and its `noqa` leaves a stale lint
  suppression or an unused import elsewhere.
  - Severity: low. Likelihood: low.
  - Mitigation: `make lint` (Ruff) flags unused imports and redundant `noqa`;
    the work-item validation runs it. The module docstring is rewritten to drop
    the now-false cuprum claim and the `subprocess` rationale.

## Progress

- [x] Work item 1: Add a focused, POSIX-shaped unit test for the venv-scripts
  resolver (`tests/test_venv_scripts_dir.py`) that fails against the current
  `nt_user`/`posix_prefix` helper and the missing skip guard, then correct
  `_venv_scripts_dir` to the `venv` scheme and add the non-POSIX skip guard to
  the e2e test. (completed: resolver switched to the `venv` scheme; module-level
  `pytestmark` skip guard added to both `test_console_scripts_e2e.py` and the
  new `test_venv_scripts_dir.py`; the `win32` `python.exe` conditional dropped;
  `make all` green at 38 passed. remaining: none.)
- [x] Work item 2: Replace the raw `subprocess.run` loop with a cuprum catalogue
  keyed on the installed scripts' absolute paths; remove `import subprocess` and
  the `# noqa: S404`/`# noqa: S603` suppressions; rewrite the module docstring to
  drop the false cuprum claim and state the POSIX-only policy. (completed: each
  installed script now runs through a per-script `ProgramCatalogue` keyed on its
  absolute path via `sh.make(prog, catalogue=...)().run_sync(capture=True)`;
  `import subprocess` and both `noqa` suppressions removed; the docstring no
  longer claims cuprum "exposes no API to execute an absolute path" and now
  states the POSIX-only policy and the `uv run` rationale. Assertions preserved
  one-to-one on `result.exit_code`/`result.stderr`. `make all` green at 38
  passed; CodeRabbit clean (0 findings). remaining: none.)
- [x] Work item 3: Author and accept
  `docs/adr-006-console-scripts-e2e-posix-policy.md`; add a one-line
  cross-reference from
  `docs/novel-ralph-harness-design.md` (§4) and from `docs/developers-guide.md`
  (the e2e paragraph). Gate Markdown with `make markdownlint` and `make nixie`.
  (completed: ADR 006 authored following the ADR-004/005 template, marked
  Accepted, recording the POSIX-only-vs-truly-portable trade and the `venv`
  scheme / cuprum-by-absolute-path enforcement; cross-referenced from design §4
  and the developers' guide e2e paragraph. `make markdownlint`, `make nixie`,
  and `make all` green; CodeRabbit clean (0 findings). remaining: none.)

CodeRabbit notes (work item 1): applied — reworded the Constraints and
Tolerances imperatives and the first-person prose to impersonal phrasing;
repaired two inline code spans (`.github/workflows/ci.yml`, the ADR-006 file
name) and the `pytestmark`/`get_path` snippets that had been split across line
breaks; grouped the resolver tests under a `TestVenvScriptsDir` class; reworded
the skip-guard comment; and dropped the dead `or scripts_dir == venv_dir`
clause (the `venv` scheme never returns the venv root on POSIX). Declined, with
reason: keeping `import typing as typ` (repo-wide convention); leaving
`_venv_scripts_dir` in the e2e module (the plan scopes the resolver there, and
the unit test exercises that helper) rather than extracting a `tests/utils.py`;
not extracting a single-use `uv_catalogue` conftest fixture; and retaining the
worktree absolute path in the plan (mandated verbatim by the workflow standing
rules — it is the canonical worktree, not portable example text).

## Surprises & discoveries

- Observation: cuprum 0.1.0 **can** allowlist and execute an absolute-path
  program, directly contradicting the e2e test's docstring claim that cuprum
  "exposes no API to execute an absolute path".
  - Evidence: at the `v0.1.0` tag of `/data/leynos/Projects/cuprum`,
    `cuprum/program.py` defines `Program = typ.NewType("Program", str)` (any
    string is a valid `Program`); `cuprum/catalogue.py`
    `ProgramCatalogue._index_programs` allowlists whatever `Program` strings are
    supplied (no bare-name restriction); `cuprum/sh.py` `SafeCmd.argv_with_program`
    is `(str(self.program), *self.argv)` and `_spawn_subprocess` calls
    `asyncio.create_subprocess_exec(*execution.cmd.argv_with_program, ...)`,
    which accepts an absolute path as `argv[0]`. Verified empirically in the
    synced environment: a `ProgramCatalogue` keyed on `Program("/usr/sbin/echo")`
    reported `is_allowed == True`, and `sh.make(prog, catalogue=...)("hello")
    .run_sync()` returned `exit_code == 0` with `stdout == "hello-from-abs\n"`.
  - Impact: the raw `subprocess.run` (and its `# noqa: S404`/`# noqa: S603`) is
    unnecessary; Work item 2 runs the installed scripts through cuprum by
    absolute path, satisfying the scripting standards. The cuprum local checkout
    is 47 commits ahead of `v0.1.0` and changes `catalogue.py`/`program.py`/
    `sh.py`, so the plan was pinned against the **tag**, not `HEAD`.
- Observation: the test's Windows branch is dead code that CI never executes,
  and it is wrong where it would execute.
  - Evidence: `.github/workflows/ci.yml` line 10 runs the whole gate
    (`make build/lint/typecheck/test` via the coverage action) on
    `ubuntu-latest`; `.github/workflows/build-wheels.yml` runs a Windows/macOS
    matrix but only invokes the local `build-wheels` action (cibuildwheel),
    never `pytest`. Locally, `sysconfig.get_path("scripts", "nt_user",
    vars={"base": "/tmp/myvenv"})` resolves to `~/.local/Python/Scripts` (a
    roaming user path), not the venv `Scripts/`, and console-scripts on Windows
    carry a `.exe` suffix the lookup omits.
  - Impact: committing to POSIX-only (skip on non-POSIX) is the honest policy;
    the ADR records it. "Truly portable" was considered and rejected because no
    CI lane would ever exercise the Windows path (Decision Log).
- Observation: Python 3.14 provides a dedicated `venv` sysconfig scheme and uses
  it by default; the current helper's `posix_prefix` happens to work but is not
  the canonical scheme, and its `nt_user` Windows arm is simply the wrong scheme.
  - Evidence: locally, `sysconfig.get_scheme_names()` includes `venv`,
    `nt_venv`, `posix_venv`; `sysconfig.get_default_scheme() == "venv"`;
    `sysconfig.get_path("scripts", "venv", vars={"base": <uv venv>})` returns the
    venv `bin/` directory and `Path(...).is_dir()` is `True` for a real
    `uv venv`.
  - Impact: Work item 1 switches the resolver to the `venv` scheme, which is
    correct on the POSIX platform the test runs on and is the canonical choice.

## Decision log

- Decision: commit to **POSIX-only execution** of the console-scripts e2e test
  (skip on `os.name != "posix"`) rather than making the Windows lookup truly
  portable.
  - Rationale: the only CI lane that runs `make test` is `ubuntu-latest`
    (`ci.yml` line 10); the Windows/macOS matrix builds wheels only
    (`build-wheels.yml`), never running pytest. A "truly portable" Windows path
    (`Scripts/` + `.exe` resolution) would be untested in every CI lane and so
    could rot exactly as the current branch did. POSIX-only is the honest,
    enforceable contract; the roadmap explicitly offers this option
    ("commit to Linux-only execution"). Recorded in `adr-006`.
  - Date/Author: 2026-06-21, planning agent.
- Decision: run the installed console-scripts through a cuprum catalogue keyed on
  their **absolute paths**, removing the raw `subprocess.run`.
  - Rationale: cuprum 0.1.0 supports allowlisting and executing an absolute-path
    `Program` (verified — Surprises), and the scripting standards require
    external programs to run through a curated cuprum catalogue, not
    `subprocess`. This removes two security `noqa` suppressions and a
    `subprocess` import, and corrects the test's false docstring claim. The
    `uv build`/`uv venv`/`uv pip install` steps already run through cuprum; this
    brings the run-loop into line.
  - Date/Author: 2026-06-21, planning agent.
- Decision: resolve the venv scripts directory through the `venv` sysconfig
  scheme.
  - Rationale: `venv` is the canonical, default scheme on Python 3.14 (verified)
    and resolves the `uv venv` bin directory correctly on POSIX. `posix_prefix`
    coincidentally works but is not the venv-specific scheme; `nt_user` is simply
    wrong (roaming user path). With the POSIX-only policy, the resolver needs
    only the POSIX answer, but using `venv` keeps it semantically correct and
    self-documenting.
  - Date/Author: 2026-06-21, planning agent.
- Decision: keep the `slow` marker and the per-test `@pytest.mark.timeout(180)`.
  - Rationale: the official pytest-timeout 2.4.0 documentation states a per-test
    `@pytest.mark.timeout` "If combined with the --timeout flag this will
    override the timeout for this individual test"; the same precedence applies
    over the ini `timeout = 30`, and the marker is evaluated per item in each
    xdist worker. The build-plus-install-plus-five-runs test needs the longer
    bound; no change is warranted.
  - Date/Author: 2026-06-21, planning agent.
- Decision: do **not** introduce a single source of truth for the command names
  here; keep the in-test `COMMAND_NAMES` tuple.
  - Rationale: deduplicating the command-name list is roadmap task 1.2.4 (a
    separate medium-severity remediation). Folding it in would poach 1.2.4's
    scope and exceed this task's narrow remit.
  - Date/Author: 2026-06-21, planning agent.

## Outcomes & retrospective

All three work items landed as planned, in three atomic commits, with `make all`
green at each commit's HEAD. Measured against the purpose:

- The e2e test remains a true wheel-build-and-install proof on Linux: it builds
  the wheel, creates a fresh `uv venv`, installs the wheel, and asserts all five
  console-scripts resolve on disk and exit `2`. The five-script contract is
  unchanged.
- The installed scripts now run through a cuprum `ProgramCatalogue` keyed on
  their absolute paths, with no `import subprocess` and no `# noqa: S404/S603`.
  The false docstring claim that cuprum "exposes no API to execute an absolute
  path" is removed.
- The venv-scripts directory resolves through the canonical `venv` sysconfig
  scheme; the new `tests/test_venv_scripts_dir.py` proves the resolver returns
  the `uv venv` bin directory and is POSIX-shaped.
- A module-level `pytestmark` skip guard makes the test SKIPPED on
  `os.name != "posix"`, naming ADR 006; the `win32`/`nt_user` branch and the
  `python.exe` conditional are gone.
- `docs/adr-006-console-scripts-e2e-posix-policy.md` is Accepted and
  cross-referenced from the design (§4) and the developers' guide.

Deviations from the plan: none material. The plan's stated "no Linux red on the
scheme name alone" held — the resolver change is proven by the new unit tests'
positive assertions and by CodeRabbit review rather than by a Linux-only red.
Scope, dependency, and tolerance fences were all respected: no command body,
`pyproject.toml`, or stub-factory change; no new dependency; no policy switch.

CodeRabbit cost: work item 1 took four review rounds (it cycled through prose
and Markdown nits on the planning document — imperative voice, first-person
pronouns, two genuinely broken inline code spans, a class grouping, and a dead
assertion clause; all genuine defects fixed, subjective/scope-bound suggestions
declined with reason in the Progress note). Work items 2 and 3 were clean on the
first review (0 findings each).

Gates at HEAD: `make all`, `make markdownlint`, and `make nixie` all green.

## Context and orientation

The repository is the Python package skeleton becoming the deterministic spine
of the novel-ralph harness. Orient with these files; all paths are relative to
the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-3`:

- `tests/test_console_scripts_e2e.py` — the subject of this task. Builds a wheel
  with `uv build --wheel`, creates a `uv venv`, `uv pip install`s the wheel, then
  resolves each of the five console-scripts on disk and runs it. The `uv` steps
  go through a local cuprum `ProgramCatalogue` allowlisting `Program("uv")`; the
  installed scripts are (currently) run by a raw `subprocess.run` with
  `# noqa: S404`/`# noqa: S603`. `_venv_scripts_dir` (lines 63-67) picks the
  sysconfig scheme `nt_user` on `win32` and `posix_prefix` otherwise — the bug.
- `pyproject.toml` — `requires-python = ">=3.14"` (line 6);
  `[project.dependencies] = ["cyclopts", "tomlkit"]`; dev group includes
  `pytest-timeout`, `pytest-xdist`, `cuprum`; `[tool.pytest.ini_options]` sets
  `timeout = 30` (line 307), `testpaths = ["tests"]`, and registers the `slow`
  marker (line 309).
- `uv.lock` — pins `cuprum 0.1.0` (line 114), `cyclopts 4.18.0`,
  `pytest-timeout 2.4.0`.
- `Makefile` — `make all` is `build check-fmt lint typecheck test` (line 28);
  `make test` is `uv run pytest -v -n auto` (`PYTEST_XDIST_WORKERS ?= auto`);
  `make lint` runs Ruff and `interrogate --fail-under 100` over
  `PYTHON_TARGETS = novel_ralph_skill tests`; `make markdownlint` and
  `make nixie` gate Markdown and Mermaid.
- `.github/workflows/ci.yml` (line 10, `runs-on: ubuntu-latest`) — the only lane
  that runs the test suite. `.github/workflows/build-wheels.yml` — a
  Windows/macOS/Linux matrix that builds wheels only.
- `docs/roadmap.md` lines 104-111 — this task; lines 112-117 — task 1.2.4 (the
  command-name single-source-of-truth, out of scope here).
- `docs/novel-ralph-harness-design.md` §4 — the five-console-script command
  surface (the ADR cross-reference target).
- `docs/developers-guide.md` lines 76-86 — the paragraph describing the stubs and
  pointing at `tests/test_console_scripts_e2e.py` (the second ADR
  cross-reference target).
- `docs/scripting-standards.md` "Cyclopts + cuprum + pathlib together" and
  "Notes and gotchas" — the requirement that external programs run through a
  curated cuprum catalogue rather than `subprocess`, and that `run_sync()`
  returns a `CommandResult` whose `exit_code` is checked explicitly.
- `docs/adr-004-distribution-console-scripts.md` and
  `docs/adr-005-command-surface-five-scripts.md` — the distribution and command
  surface decisions whose e2e proof this test is; the new ADR follows their
  template.
- The locked cuprum sources, pinned at the `v0.1.0` tag of
  `/data/leynos/Projects/cuprum`: `cuprum/program.py` (`Program` newtype),
  `cuprum/catalogue.py` (`ProgramCatalogue`, `ProjectSettings`, allowlisting),
  `cuprum/sh.py` (`make`, `SafeCmd.run_sync`, `ExecutionContext`,
  `CommandResult`).

Terms of art, defined so the plan is self-contained:

- **Console-script.** A command installed onto `PATH` from a Python package's
  `[project.scripts]` entry points. On POSIX it is a small executable launcher in
  the venv `bin/`; on Windows it is a `<name>.exe` in the venv `Scripts/`.
- **sysconfig scheme.** A named set of installation paths Python uses to locate
  things like the scripts directory. `venv` (and its `posix_venv`/`nt_venv`
  aliases) is the scheme describing a virtual environment's layout; `nt_user`
  describes a Windows per-user (roaming) install, which is **not** a venv.
- **cuprum catalogue / allowlist.** `cuprum` only executes programs registered in
  a `ProgramCatalogue`; an unregistered program raises `UnknownProgramError`. A
  `Program` is any string, so an absolute path is a valid, allowlistable program.
- **POSIX-only policy.** The decision that this e2e test runs only where
  `os.name == "posix"`, skipping elsewhere with a recorded reason. It matches the
  Linux-only CI test lane.

Skills to load before touching code (per the global agent instructions and the
worktree standing rules):

- `python-router` first, to route to the smaller skills below.
- `python-testing` for the test rewrite shape (a focused unit test for the
  resolver; a skip-marked, cuprum-driven e2e; direct semantic assertions; no new
  snapshot; the existing `slow`/`timeout` markers preserved).
- `python-verification` only to confirm that **no** property/Hypothesis/CrossHair
  suite belongs here (this is an example-based portability fix, not a generative
  contract); `hypothesis`, `crosshair`, and `mutmut` are not loaded or used.
- `leta` for navigating the package and test tree; `sem` for history.

Authoritative sources to read before editing:

- `docs/roadmap.md` lines 104-117 — task 1.2.3 and the adjacent 1.2.4 boundary.
- `docs/scripting-standards.md` — the cuprum-over-subprocess rule and the
  `run_sync()` result contract.
- `docs/adr-004-distribution-console-scripts.md` and
  `docs/adr-005-command-surface-five-scripts.md` — the ADR template and the
  decisions this test proves.
- `docs/novel-ralph-harness-design.md` §4 and `docs/developers-guide.md`
  lines 76-86 — the ADR cross-reference targets.
- `AGENTS.md` — quality gates, en-GB Oxford spelling, 400-line limit, 100%
  docstring coverage, tests under `tests/`, snapshot discipline, Markdown
  guidance.
- The cuprum `v0.1.0`-tagged sources named above, to keep every API call pinned
  to the locked version.

## Plan of work

Three atomic, independently-committable work items, each ending with its own
validation; `make all` must be green before each code commit, and the
Markdown-touching work item also runs `make markdownlint` and `make nixie`.
Work item 1 fixes the resolver and adds the platform guard (the "decide and
enforce" core); work item 2 removes the `subprocess` dependency by routing
through cuprum (the scripting-standards alignment the research unlocked); work
item 3 records the decision as an ADR and links it. The items are ordered so the
test is correct and green (1), then idiomatic (2), then documented (3).

### Work item 1 — Fix the venv-scripts resolver and enforce the POSIX-only guard

Implements: roadmap task 1.2.3 ("commit to Linux-only execution … make the
lookup truly portable"); `docs/scripting-standards.md` (pathlib path handling);
the design's five-console-script surface (§4) that the e2e proves.

Add a new focused unit test `tests/test_venv_scripts_dir.py` **first** (red),
exercising the resolver directly so the fix is proven without paying the slow
build/install cost:

1. A test that creates a real `uv venv` in `tmp_path` (through the same cuprum
   `Program("uv")` catalogue the e2e uses, or a minimal local catalogue) and
   asserts the resolver returns a directory that exists and contains the venv
   `python` launcher — proving the resolver points at the venv's bin directory,
   not a roaming user path.
2. A test asserting the resolver is POSIX-shaped: on the running (POSIX)
   platform the resolved path ends in `bin` (not `Scripts`). This pins the
   `venv` scheme's POSIX answer and trips if a future edit reintroduces
   `posix_prefix`/`nt_user` divergence.

Then make the e2e test changes (green):

- In `tests/test_console_scripts_e2e.py`, rewrite `_venv_scripts_dir` to resolve
  the scripts directory through the `venv` sysconfig scheme:

  ```python
  sysconfig.get_path(
      "scripts", "venv",
      vars={"base": str(venv_dir), "platbase": str(venv_dir)},
  )
  ```

  Drop the `win32`/`nt_user` branch entirely.
- Add a module- or test-level skip guard:

  ```python
  pytestmark = pytest.mark.skipif(
      os.name != "posix",
      reason="console-scripts e2e is POSIX-only; see ADR 006",
  )
  ```

  (or an equivalent decorator on the test), with a `# why:` comment pointing at
  the ADR. Keep the existing `slow` and `timeout(180)` markers.
- Update `venv_python` to drop the `"python.exe" if sys.platform == "win32"`
  conditional (POSIX-only), using `scripts_dir / "python"`.

Read first: `docs/roadmap.md` lines 104-111; `docs/scripting-standards.md`
(pathlib section); `.rules/python-00.md`; `.rules/python-return.md`.

Skills: `python-router`, then `python-testing` (focused unit test; skip marker;
direct assertions). `python-verification` only to reconfirm no property suite
belongs here.

Tests added/updated:

- `tests/test_venv_scripts_dir.py` (new) — two unit tests proving the resolver
  returns the `uv venv` bin directory and is POSIX-shaped. These fail against the
  current `nt_user`/`posix_prefix` helper only on Windows, so to make the red
  state observable on Linux the resolver test asserts the **`venv`-scheme**
  behaviour the new helper must provide (it exercises the helper after the fix;
  before the fix the second test still passes on Linux because `posix_prefix`
  also yields `bin`, so the load-bearing red signal is the Windows-path removal
  and is captured by the e2e skip behaviour and code review rather than a
  Linux-only assertion — documented here so the implementer does not expect a
  Linux red on the scheme name alone).
- `tests/test_console_scripts_e2e.py` (updated) — `_venv_scripts_dir` uses the
  `venv` scheme; the non-POSIX skip guard is added; the `win32` `python.exe`
  conditional is removed. The five-script build/install/exit-2 assertions are
  unchanged.

Validation: `make test` passes on Linux (the e2e runs, not skipped, since
`os.name == "posix"`); the new unit tests pass; `make lint`, `make check-fmt`,
`make typecheck` pass; `make all` is green.

### Work item 2 — Run the installed scripts through cuprum by absolute path

Implements: `docs/scripting-standards.md` (external programs run through a
curated cuprum catalogue, not `subprocess`; `run_sync()` returns a
`CommandResult` whose `exit_code` is checked); roadmap task 1.2.3 (the run-loop
half of the e2e). Built on the verified cuprum 0.1.0 absolute-path capability
(Surprises).

In `tests/test_console_scripts_e2e.py`:

- Replace the `subprocess.run` loop with a cuprum run. For each installed
  console-script absolute path `script_path` (resolved via the `venv`-scheme
  scripts dir), build a `Program(str(script_path))`, register it in a
  `ProgramCatalogue` (a single catalogue allowlisting all five absolute paths,
  built after install, or one catalogue per script), and run it via
  `sh.make(prog, catalogue=cat)().run_sync(capture=True)`. Assert
  `result.exit_code == 2`, `"Traceback" not in (result.stderr or "")`, and
  `command_name in (result.stderr or "")`, preserving the existing contract.
- Remove `import subprocess` and the `# noqa: S404`/`# noqa: S603` comments.
- Rewrite the module docstring: drop the false claim that cuprum "exposes no API
  to execute an absolute path"; state instead that the installed scripts are run
  through a cuprum catalogue keyed on their absolute paths (cuprum 0.1.0
  allowlists any `Program`, including a path), and that the test is POSIX-only
  per ADR 006. Keep the explanation that `uv run` is avoided because it would
  resolve against the project environment rather than the freshly built wheel.

Read first: the cuprum `v0.1.0` sources (`cuprum/sh.py` `make`,
`SafeCmd.run_sync`, `ExecutionContext`, `CommandResult`; `cuprum/catalogue.py`
`ProgramCatalogue`, `ProjectSettings`); `docs/scripting-standards.md` "Notes and
gotchas"; `.rules/python-00.md`.

Skills: `python-router`, then `python-testing`.

Tests added/updated:

- `tests/test_console_scripts_e2e.py` (updated) — same five-script assertions,
  now driven through cuprum with no `subprocess` import and no `noqa`. No new
  test file; this is a faithful refactor of the existing assertions onto the
  cuprum `CommandResult` surface.

Validation: `make test` passes on Linux with the e2e green through cuprum;
`make lint` reports no unused import and no stale `noqa`; `make all` is green.

### Work item 3 — Record the POSIX-only policy as an ADR and link it

Implements: AGENTS.md ("Record substantive decisions in the relevant design
document; for major decisions, capture an ADR"); roadmap task 1.2.3 ("decide and
enforce" — the ADR is the durable record of the decision).

- Create `docs/adr-006-console-scripts-e2e-posix-policy.md` following the
  template of `docs/adr-004-distribution-console-scripts.md` (Status, Date,
  Context, Decision drivers, Options considered, Decision outcome, Goals and
  non-goals, Known risks, Outstanding decisions). Record: the two options
  (commit to POSIX-only vs. make the lookup truly portable on Windows); the
  decision to go POSIX-only because the test suite runs only on `ubuntu-latest`
  (`ci.yml`) while the Windows/macOS matrix builds wheels only
  (`build-wheels.yml`); the enforcement (the non-POSIX skip guard and the `venv`
  scheme); and the note that cuprum 0.1.0 runs the installed scripts by absolute
  path. Mark it Accepted, dated 2026-06-21.
- Add a one-line cross-reference to the ADR from
  `docs/novel-ralph-harness-design.md` §4 (the command-surface section) and from
  the `docs/developers-guide.md` e2e paragraph (lines 76-86), so the policy is
  discoverable from both the design and the contributor docs.

Read first: `docs/adr-004-distribution-console-scripts.md` and
`docs/adr-005-command-surface-five-scripts.md` (template and tone);
`docs/documentation-style-guide.md`; AGENTS.md "Markdown guidance".

Skills: `en-gb-oxendict` for the prose; `python-router` is not needed (no code).

Tests added/updated: none (documentation only). The policy's *behaviour* is
already gated by the skip guard and the resolver unit tests from work items 1-2.

Validation: `make markdownlint` and `make nixie` pass over the new ADR and the
edited docs; `make all` stays green (no code change in this item).

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-3`.

Confirm the branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-3 \
  branch --show-current
```

Expect `roadmap-1-2-3`.

Re-verify the load-bearing cuprum and sysconfig facts on the target machine
before relying on them (verified at planning time):

```bash
uv run python -c "import importlib.metadata as m; print(m.version('cuprum'))"
# expect 0.1.0
uv run python - <<'PY'
import shutil, sysconfig
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program
p = Program(shutil.which("echo") or "/bin/echo")
cat = ProgramCatalogue(projects=(ProjectSettings(
    name="t", programs=(p,), documentation_locations=(), noise_rules=()),))
print("allowed:", cat.is_allowed(p))
print("exit:", sh.make(p, catalogue=cat)("hi").run_sync().exit_code)
print("venv-scheme:", sysconfig.get_path("scripts", "venv",
      vars={"base": "/tmp/x", "platbase": "/tmp/x"}))
PY
# expect: allowed: True / exit: 0 / venv-scheme: /tmp/x/bin
```

Per-work-item validation:

```bash
make all          # build check-fmt lint typecheck test (every code work item)
make markdownlint # ADR + doc edits (work item 3)
make nixie        # Mermaid validation (work item 3; no diagrams expected)
```

Expected high-level transcript after work items 1-2 (illustrative):

```plaintext
$ make test
... tests/test_venv_scripts_dir.py::test_resolver_points_at_venv_bin PASSED
... tests/test_venv_scripts_dir.py::test_resolver_is_posix_shaped PASSED
... tests/test_console_scripts_e2e.py::test_console_scripts_install_and_exit_two PASSED
===== N passed in Xs =====
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- On Linux, `make test` builds a wheel, installs it into a fresh `uv venv`,
  resolves all five console-scripts on disk, and runs each through a cuprum
  catalogue keyed on its absolute path, asserting exit `2`, no `Traceback` in
  stderr, and the command name echoed in stderr.
- The e2e test imports no `subprocess` and carries no `# noqa: S404`/`S603`
  suppression; `make lint` is clean.
- `_venv_scripts_dir` resolves through the `venv` sysconfig scheme; the new
  `tests/test_venv_scripts_dir.py` proves it returns the `uv venv` bin directory.
- On a non-POSIX platform the e2e test reports `SKIPPED` with a reason naming
  ADR 006, instead of executing a broken Windows path.
- `docs/adr-006-console-scripts-e2e-posix-policy.md` exists, is Accepted, and is
  cross-referenced from `docs/novel-ralph-harness-design.md` §4 and the
  `docs/developers-guide.md` e2e paragraph.

Quality criteria (what "done" means):

- Tests: `make test` passes; `tests/test_venv_scripts_dir.py` is present and
  green; the e2e test passes through cuprum; all pre-existing tests still pass.
- Lint/typecheck: `make lint` (Ruff, `interrogate --fail-under 100`, Pylint),
  `make check-fmt` (`ruff format --check`), and `make typecheck` (`ty check`)
  all pass; no unused import and no stale `noqa`.
- Markdown/Mermaid: `make markdownlint` and `make nixie` pass over the new ADR
  and the edited design and developers' guide.
- Aggregate: `make all` is green at each code work item's commit.

Quality method (how it is checked): run `make all` before and after each code
work item; run `make markdownlint` and `make nixie` after the documentation
work item.

## Idempotence and recovery

- The new unit test and the e2e test are pure and re-runnable; each writes only
  into its own `tmp_path` (wheel dir, venv, installed scripts) and touches no
  tracked file or `working/` state.
- The resolver and run-loop edits are in-place and deterministic; re-running
  `make test` rebuilds the wheel and venv from scratch each time.
- The ADR and the two one-line cross-references are additive Markdown; if a
  Markdown gate fails, re-wrap to 80 columns and re-run `make markdownlint`.
- If `make build` leaves a partial environment, `make clean` then `make build`
  restores a known state (the Makefile `clean` target removes `.venv`,
  `.uv-cache`, caches, and build artefacts).
- No step is destructive to tracked files beyond the intended edits
  (`tests/test_console_scripts_e2e.py`, the new `tests/test_venv_scripts_dir.py`,
  the new ADR, and the two doc cross-references) and updates to this execplan.

## Artifacts and notes

- Locked versions, verified: `cuprum 0.1.0`, `cyclopts 4.18.0`,
  `pytest-timeout 2.4.0` (`uv.lock`; `importlib.metadata`).
- cuprum 0.1.0 API pinned against the `v0.1.0` tag of
  `/data/leynos/Projects/cuprum` (the local checkout is 47 commits ahead and
  changed these files, so `HEAD` was **not** used):
  - `cuprum/program.py`: `Program = typ.NewType("Program", str)` — any string,
    including an absolute path, is a `Program`.
  - `cuprum/catalogue.py`: `ProgramCatalogue(projects=...)`, `ProjectSettings`,
    `is_allowed`, `lookup` — allowlists whatever `Program` strings are supplied,
    with no bare-name restriction.
  - `cuprum/sh.py`: `make(program, *, catalogue=DEFAULT_CATALOGUE)` →
    `SafeCmdBuilder`; `SafeCmd.run_sync(*, capture=True, echo=False,
    context=None)` → `CommandResult(exit_code, stdout, stderr, ...)`;
    `SafeCmd.argv_with_program` is `(str(program), *argv)` and
    `_spawn_subprocess` calls `asyncio.create_subprocess_exec`, accepting an
    absolute path as `argv[0]`.
- Verified empirically (synced env): allowlisting `Program("/usr/sbin/echo")`
  and running it via cuprum returned `exit_code == 0`, `stdout ==
  "hello-from-abs\n"`; the `venv` sysconfig scheme resolves a real `uv venv`'s
  `bin/` directory containing the `python` launcher.
- pytest-timeout 2.4.0 (official docs): a per-test `@pytest.mark.timeout`
  overrides the `--timeout`/ini global; the per-item marker is applied in each
  xdist worker. The e2e's `@pytest.mark.timeout(180)` over `timeout = 30` is
  documented behaviour and is retained.
- Scope fences restated: this task does **not** add a command-name single source
  of truth (task 1.2.4), does **not** touch any command body or the stub factory,
  and does **not** add a Hypothesis/CrossHair property suite.

## Interfaces and dependencies

Dependencies: **no change** to `pyproject.toml` dependency tables or `uv.lock`.
This task adds no runtime and no dev dependency.

Resolver shape after work item 1 (illustrative; the implementer pins the exact
form against the locked `sysconfig`):

```python
import sysconfig
from pathlib import Path


def _venv_scripts_dir(venv_dir: Path) -> Path:
    """Return the venv's executable-scripts directory (POSIX, ``venv`` scheme)."""
    scripts = sysconfig.get_path(
        "scripts",
        "venv",
        vars={"base": str(venv_dir), "platbase": str(venv_dir)},
    )
    return Path(scripts)
```

Run-loop shape after work item 2 (illustrative; assertions preserved):

```python
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program

# why: cuprum 0.1.0 allowlists any Program string, including an absolute path,
# and runs it through asyncio.create_subprocess_exec; no subprocess needed.
for command_name in COMMAND_NAMES:
    script_path = scripts_dir / command_name
    assert script_path.exists(), f"{command_name} not installed at {script_path}"
    prog = Program(str(script_path))
    catalogue = ProgramCatalogue(projects=(ProjectSettings(
        name="novel-ralph-e2e-scripts", programs=(prog,),
        documentation_locations=(), noise_rules=()),))
    result = sh.make(prog, catalogue=catalogue)().run_sync(capture=True)
    assert result.exit_code == 2, (
        f"{command_name} exited {result.exit_code}, expected 2"
    )
    stderr = result.stderr or ""
    assert "Traceback" not in stderr
    assert command_name in stderr
```

Out of scope (do not build here): a single source of truth for the command names
(task 1.2.4); any command body or stub-factory change; any `pyproject.toml`
entry-point change; a real Windows `Scripts/` + `.exe` lookup (explicitly
rejected by ADR 006); any property/Hypothesis/CrossHair suite.

## Revision note

- 2026-06-21 (planning round 1): Authored the self-contained plan against the
  locked toolchain. Pinned cuprum to the `v0.1.0` tag (the local checkout is 47
  commits ahead and modifies the relevant files) and verified empirically that
  cuprum 0.1.0 allowlists and executes an absolute-path `Program`, refuting the
  e2e test's docstring claim and unlocking the `subprocess`-removal work item.
  Verified that CI runs the test suite only on `ubuntu-latest`
  (`ci.yml`), with the Windows/macOS matrix building wheels only
  (`build-wheels.yml`), grounding the POSIX-only decision. Verified that the
  current `nt_user`/missing-`.exe` Windows branch is both dead and wrong, and
  that the canonical `venv` sysconfig scheme resolves the `uv venv` bin directory
  on POSIX. Confirmed against the official pytest-timeout 2.4.0 documentation
  that the per-test `@pytest.mark.timeout(180)` overrides the ini `timeout = 30`
  and is honoured per item under xdist. Decomposed into three atomic work items
  (resolver+guard, cuprum run-loop, ADR) and kept the command-name dedup out of
  scope (task 1.2.4). The plan remains DRAFT pending review.
- 2026-06-22 (implementation): Executed all three work items in order, each an
  atomic commit gated by `make all` (and `make markdownlint`/`make nixie` for
  Markdown). Re-verified the load-bearing cuprum-absolute-path and `venv`-scheme
  facts on the target machine before relying on them. Reworded the Constraints,
  Tolerances, and prose to impersonal phrasing and repaired broken inline code
  spans in response to CodeRabbit. Status moved DRAFT → DONE; Outcomes filled in.

## Addenda (post-merge follow-ups)

Lightweight addendum work items surfaced by later audits and folded back onto
this completed task. Execute each as a small addendum pass — no plan or
design-review cycle: make the change, run `make all` (plus `make markdownlint`
and `make nixie` for Markdown), `coderabbit review --agent`, commit, and tick
the matching roadmap sub-task on merge.

- [x] 1.2.3.1 — Index ADR 006 and the `docs/issues/` and `docs/execplans/` sets
  in `docs/contents.md` (from audit:1.2.6, low). The documentation map omits the
  POSIX console-scripts ADR and the growing audit-trail and per-task plan sets,
  leaving them undiscoverable. Docs-only change; gate with `make markdownlint`
  and `make nixie`.
