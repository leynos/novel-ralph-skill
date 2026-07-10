# Introduce `tests/conftest.py` to consolidate the shared test scaffolding

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises and discoveries`, `Decision log`,
and `Outcomes and retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Today the `tests/` tree repeats the same scaffolding in module after module:
the project-root path, the `pyproject.toml` parse, a repo-relative file reader,
a TOML-table accessor, a single-program cuprum catalogue, and the venv
scripts-directory resolver. The resolver is even reached across modules through
a private import
(`from tests.test_console_scripts_e2e import _venv_scripts_dir`). Six
post-merge audits (`docs/issues/audit-1.2.1.md` Finding 3, `audit-1.2.3.md`
Findings 1-2, `audit-1.2.4.md` Finding 2, `audit-1.2.5.md` Findings 1-3 and 5,
`audit-1.2.6.md` Findings 1-2) have flagged this growing duplication and named
the fix every time: a single `tests/conftest.py` that owns the shared helpers,
consumed by every module.

After this change a reader can run `make test` and see the same suite pass, but
each test module imports its scaffolding from one place. The observable wins:

- No test module re-derives `Path(__file__).resolve().parent.parent`.
- No test module re-implements the `pyproject.toml` parse or the
  repo-relative file read.
- The venv scripts-directory resolver and the single-program cuprum catalogue
  live in `tests/conftest.py`; the cross-module private import disappears.
- Adding a seventh test module costs no new copy of any of these helpers.

Success is behaviour-preserving: the test count and outcomes are unchanged; the
diff removes duplication and the private cross-module import, and `make all`
stays green.

## Constraints

Hard invariants that must hold throughout implementation.

- Work only inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-7`. Never edit
  files in the root/control worktree.
- Do not change any test's observable behaviour: the same tests must pass, with
  the same exit-code, skip, timeout, and warning-filter semantics, before and
  after. This is a refactor (AGENTS.md "Separate atomic refactors"), not a
  behaviour change.
- Do not modify production code under `novel_ralph_skill/`. The single source of
  truth for command names stays `novel_ralph_skill/commands/names.py` (roadmap
  1.2.4; `docs/developers-guide.md` "Edit a command name there").
- Keep all pytest tests in the top-level `tests/` tree (AGENTS.md "Python
  verification and testing"). `conftest.py` lives at `tests/conftest.py`.
- `tests/conftest.py` is inside `PYTHON_TARGETS` (`Makefile:15`,
  `PYTHON_TARGETS ?= novel_ralph_skill tests`), so it must pass Ruff lint and
  format, 100% `interrogate` docstring coverage (`pyproject.toml`
  `[tool.interrogate] fail-under = 100` with every `ignore-*` set to its
  non-relaxing default), the PyPy-backed Pylint runner, and `ty` typecheck. The
  module needs a module docstring and a docstring on every fixture and helper.
- The Ruff `per-file-ignores` for `**/test_*.py` (`pyproject.toml:94`:
  `S101`, `PLR0913`, `PLR0917`, `PLR2004`, `PLR6301`) do **not** match
  `conftest.py`. Either keep `conftest.py` free of those triggers (no bare
  `assert`, no six-positional helpers) or add a `"tests/conftest.py"` entry to
  `per-file-ignores`. Prefer keeping the file clean; raise via `AssertionError`
  only where a guard genuinely belongs.
- Imports obey the repo conventions: `from __future__ import annotations`,
  `import typing as typ`, `import collections.abc as cabc`, no banned `from`
  imports (`pyproject.toml` `[tool.ruff.lint.flake8-import-conventions]`),
  numpy-style docstrings (`pyproject.toml` `[tool.ruff.lint.pydocstyle]`).
- All external commands run through a cuprum catalogue allowlist; no raw
  `subprocess` (`docs/scripting-standards.md` "Command execution with cuprum";
  AGENTS.md "Scripting standards"). The shared catalogue helper preserves this.
- Prose, comments, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our") except where naming an external API (AGENTS.md "Code
  style and structure").
- Mermaid/Markdown gates apply to any `.md` edit: `make markdownlint` and
  `make nixie` (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if the consolidation requires net changes to more than 9 files or more
  than ~250 net lines, stop and escalate.
- Behaviour: if any test changes its pass/fail/skip outcome, its exit-code
  assertion, its timeout, or its warning filter, stop and escalate — that is no
  longer a pure refactor.
- Interface: if making the helpers importable forces adding `tests/__init__.py`
  (turning `tests` into a regular package) or changing pytest import mode in
  `pyproject.toml`, stop and escalate; this changes collection semantics for
  the whole suite. (See Risks and the Decision Log entry below for the planned
  fixture-first approach that avoids this.)
- Dependencies: if any new external dependency is required, stop and escalate.
  This work adds none.
- Iterations: if `make all` still fails after 3 fix attempts on a single work
  item, stop and escalate.
- Ambiguity: if the audits' named helper set cannot be expressed without
  changing behaviour, present the conflict with options.

## Risks

    - Risk: conftest helpers consumed as importable functions. pytest auto-loads
      `tests/conftest.py`, but importing module-level helpers via
      `from tests.conftest import ...` is fragile across import modes and is a
      recognized anti-pattern. Reaching for `tests/_helpers.py` instead would
      add a second shared module the audits did not ask for.
      Severity: medium
      Likelihood: medium
      Mitigation: expose the run-time scaffolding (project root, single-program
      catalogue, venv resolver) as pytest *fixtures*, which conftest injects by
      name with no import. Expose the pure, side-effect-free parse/transform
      helpers (`pyproject()`, `read_repo_text`, `toml_table`) as fixtures too,
      or as a fixture returning a small callable, so no module imports from
      conftest. Confirm by collection: `from tests.test_console_scripts_e2e
      import _venv_scripts_dir` must be gone and no `from tests.conftest import`
      appears anywhere.
    - Risk: removing `_venv_scripts_dir` from `test_console_scripts_e2e.py`
      breaks `test_venv_scripts_dir.py`, which imports it cross-module.
      Severity: medium
      Likelihood: high (intended change)
      Mitigation: migrate both modules in the same work item; convert the
      resolver into a fixture, delete the private import, and run `make test`
      to prove both still pass/skip identically.
    - Risk: interrogate 100% coverage fails the new module because a fixture or
      helper lacks a docstring.
      Severity: low
      Likelihood: medium
      Mitigation: every fixture and helper carries a numpy-style docstring; run
      `make lint` (which runs interrogate) per work item.
    - Risk: a bare `assert` in a conftest helper trips Ruff `S101` because the
      `test_*.py` ignore does not cover `conftest.py`.
      Severity: low
      Likelihood: medium
      Mitigation: conftest helpers do not assert; guards that must raise use
      `raise AssertionError(...)` (the pattern already used by `toml_table`'s
      source `_table` in `tests/test_interrogate_gate.py`).
    - Risk: the POSIX-only skip semantics (ADR-006) drift when the catalogue and
      resolver move.
      Severity: medium
      Likelihood: low
      Mitigation: leave the `pytestmark = pytest.mark.skipif(os.name != "posix",
      …)` guards in the two console-scripts modules; the fixtures hold no
      skip logic. Verify the skip count is unchanged on this POSIX host.

## Progress

    - [x] WI-1: Add `tests/conftest.py` with `project_root`, `pyproject`,
      `read_repo_text`, and `toml_table` scaffolding; migrate the four
      static-parse modules. Done 2026-06-22; `make all` green at 52 passed.
    - [x] WI-2: Move the single-program cuprum catalogue and the
      `venv_scripts_dir` resolver into `tests/conftest.py`; migrate the two
      console-scripts modules and delete the cross-module private import. Done
      2026-06-22; cross-module import gone, `make all` green at 54 passed.
    - [x] WI-3: Record the shared test-scaffolding convention in
      `docs/developers-guide.md`; update `docs/contents.md` if touched. Done
      2026-06-22; added a "Shared test scaffolding" subsection.
      `docs/contents.md` not touched (out of scope).

## Surprises and discoveries

    - Observation: `tests/` has no `__init__.py`, yet
      `tests/test_venv_scripts_dir.py:18` does
      `from tests.test_console_scripts_e2e import _venv_scripts_dir`.
      Evidence: `ls tests/__init__.py` -> absent; the import works under
      pytest's default `prepend` import mode because the rootdir is inserted on
      `sys.path`.
      Impact: the fixture-first approach removes this import entirely rather
      than legitimizing it, avoiding any `tests/__init__.py` / import-mode
      change (see Tolerances).
    - Observation: `Program` is `typing.NewType("Program", str)` with no
      validation.
      Evidence: `.venv/.../cuprum/program.py` defines
      `Program = typ.NewType("Program", str)`.
      Impact: `Program(str(absolute_path))` is a plain string; the catalogue
      allowlist — not `Program` — is the gate, so the shared
      `single_program_catalogue` fixture/helper can wrap any program string,
      including an absolute path, exactly as the e2e does today.
    - Observation (WI-2): consuming both new fixtures plus a local `uv` builder
      pushed `test_console_scripts_install_and_exit_two` over Ruff `PLR0914`
      (too-many-locals, limit 10), which the `**/test_*.py` `per-file-ignores`
      do not relax.
      Evidence: `ruff check` reported "Too many local variables (12 > 10)".
      Impact: the per-script run-and-assert loop was extracted into a
      module-level `_assert_scripts_exit_two` helper (behaviour identical),
      restoring the local count under the limit while keeping the e2e markers
      and skip semantics intact.

## Decision log

    - Decision: expose run-time scaffolding as pytest fixtures, not importable
      module functions, and avoid creating `tests/__init__.py` or changing
      pytest import mode.
      Rationale: conftest fixtures are injected by name with zero import,
      eliminating the cross-module private import the audits flag without
      altering collection semantics for the whole suite. Importing helpers from
      conftest is a known anti-pattern; a second `tests/_helpers.py` module is
      more surface than the audits asked for.
      Date/Author: 2026-06-22, planning agent
    - Decision: keep the pure parse/transform helpers (`pyproject`,
      `read_repo_text`, `toml_table`) available as fixtures (some returning a
      small callable) so no test module needs to import from conftest.
      Rationale: uniform consumption pattern (all-fixtures) keeps the
      cross-module import count at zero and sidesteps the import-mode fragility.
      Date/Author: 2026-06-22, planning agent
    - Decision: pin cuprum usage to the locked 0.1.0 public API
      (`ProgramCatalogue(*, projects=...)`, `ProjectSettings(name, programs,
      documentation_locations, noise_rules)`, `sh.make(program, *,
      catalogue=…)`, `run_sync(*, capture=True)` returning `CommandResult`
      with `.exit_code`/`.stderr`), not the `Catalogue.from_programs` /
      `sh.scoped` idiom shown in `docs/scripting-standards.md`.
      Rationale: the installed locked cuprum 0.1.0 exposes the former (verified
      below); the standards' `Catalogue.from_programs`/`sh.scoped` shorthand is
      not what the existing tests use, and the shared helper must match what the
      pinned library actually ships so the refactor stays behaviour-preserving.
      Date/Author: 2026-06-22, planning agent

## Outcomes and retrospective

Yes on both counts. `tests/conftest.py` now owns the six shared helpers
(`project_root`, `pyproject`, `read_repo_text`, `toml_table`,
`single_program_catalogue`, `venv_scripts_dir`); the four static-parse modules
and the two console-scripts modules consume them by fixture name, and the
cross-module private import `from tests.test_console_scripts_e2e import
_venv_scripts_dir` is gone. No `from tests.conftest import` was introduced, and
no `tests/__init__.py` or import-mode change was needed — the fixture-first
approach in the Decision log held.

The suite stayed green throughout: 52 passed before the conftest-helper tests,
54 passed after (the two added `single_program_catalogue` assertions), with the
POSIX-only skip semantics unchanged on this POSIX host. `make all`,
`make markdownlint`, and `make nixie` all pass at HEAD.

One deviation from the plan: the e2e test tripped Ruff `PLR0914` after gaining
two fixture parameters, resolved by extracting the per-script run-and-assert
loop into the module-level `_assert_scripts_exit_two` helper (recorded under
Surprises and discoveries). No tolerance was breached: net changes stayed within
budget, no test changed outcome, no dependency was added.

## Context and orientation

This repository packages the novel-ralph harness. The Python package lives under
`novel_ralph_skill/`; tests live under `tests/`. The five console-script
command names live once, as data, in `novel_ralph_skill/commands/names.py`
(`COMMAND_NAMES`, `COMMAND_ENTRY_POINTS`, `project_scripts_table()`); the stub
command surface is `novel_ralph_skill/commands/stub.py` (`make_stub_app`,
`STUB_EXIT_CODE`). See `docs/developers-guide.md` "The five commands".

Key terms:

- **cuprum** — a typed command-execution library. A `ProgramCatalogue` is an
  allowlist of `Program` strings grouped under `ProjectSettings`. `sh.make`
  builds a callable for an allowlisted program; `.run_sync()` runs it and
  returns a `CommandResult` (`.exit_code`, `.stdout`, `.stderr`). See
  `docs/scripting-standards.md` and the verified API below.
- **conftest.py** — a pytest file auto-discovered for a directory; its fixtures
  are available to every test under that directory by parameter name, with no
  import statement.
- **fixture** — a pytest-managed setup function a test receives by naming it as
  a parameter.

The duplicated scaffolding, by current location:

- `_PROJECT_ROOT = Path(__file__).resolve().parent.parent` in
  `tests/test_console_scripts_e2e.py:39`, `tests/test_venv_scripts_dir.py` (via
  the import), `tests/test_command_names_registry.py:18`,
  `tests/test_pyproject_scripts.py:17`, `tests/test_interrogate_gate.py:21`,
  `tests/test_state_layout_reference.py:23` (audit-1.2.6 Finding 1).
- `pyproject.toml` parse: `_parse_scripts()` in
  `tests/test_command_names_registry.py:21`, inline `tomllib.loads(...)` in
  `tests/test_pyproject_scripts.py:22`, `_pyproject()` in
  `tests/test_interrogate_gate.py:27` (audit-1.2.5 Finding 2).
- repo-relative file reader: `_state_layout_text()` in
  `tests/test_state_layout_reference.py:26` plus the three pyproject readers
  (audit-1.2.6 Finding 2).
- TOML-table accessor `_table()` in `tests/test_interrogate_gate.py:32`
  (audit-1.2.5 Finding 3).
- single-program cuprum catalogue: `_CATALOGUE` and the per-command loop
  catalogue in `tests/test_console_scripts_e2e.py:50,122`, and the
  resolver-test catalogue in `tests/test_venv_scripts_dir.py:37` (audit-1.2.3
  Finding 1).
- `_venv_scripts_dir()` defined in `tests/test_console_scripts_e2e.py:70` and
  imported across modules by `tests/test_venv_scripts_dir.py:18` (audit-1.2.3
  Finding 2).

`tests/test_stub.py` and `tests/test_command_stubs.py` need none of these
helpers (they import from the package), and `tests/test_tomlkit_dependency.py`
operates on an in-test TOML string; leave those modules untouched except where
a trivial unused import would otherwise remain.

### Verified locked-library facts (do not re-derive from memory)

cuprum is locked at 0.1.0 (`uv.lock:113-115`). Verified against the installed
package at `.venv/lib64/python3.14/site-packages/cuprum/`:

- `cuprum/__init__.py` re-exports `ProgramCatalogue`, `ProjectSettings`,
  `Program`, `sh`, `CommandResult`.
- `cuprum/catalogue.py:59` —
  `ProgramCatalogue.__init__(self, *, projects: Iterable[ProjectSettings])`
  (keyword-only `projects`).
- `cuprum/catalogue.py:29-36` — `ProjectSettings` is a frozen dataclass with
  fields `name: str`, `programs: tuple[Program, ...]`,
  `documentation_locations: tuple[str, ...]`, `noise_rules: tuple[str, ...]`.
- `cuprum/program.py` — `Program = typing.NewType("Program", str)`; any string
  (including an absolute path) is a valid `Program`. The allowlist is the gate.
- `cuprum/sh.py:529` — the signature below; the builder is called with args to
  produce a `SafeCmd`.

      sh.make(
          program: Program,
          *,
          catalogue: ProgramCatalogue = DEFAULT_CATALOGUE,
      ) -> SafeCmdBuilder
- `cuprum/sh.py:450` — `SafeCmd.run_sync(self, *, capture: bool = True, echo:
  bool = False, context: ExecutionContext | None = None) -> CommandResult`
  (all keyword-only). `cuprum/sh.py:89-114` — `CommandResult` carries
  `exit_code: int`, `stdout: str | None`, `stderr: str | None`.

Conclusion: the shared `single_program_catalogue(name, program)` helper is
fully expressible on the locked cuprum 0.1.0 with the exact constructor calls
the existing tests already make. No cuprum gap; no alternative needed.

pytest-timeout is locked at 2.4.0 (`uv.lock:494-496`). Verified against the
pytest-timeout 2.4.0 PyPI page (`https://pypi.org/project/pytest-timeout/`,
"Usage"): the timeout precedence is, lowest to highest, ini `timeout` option ->
`PYTEST_TIMEOUT` env -> `--timeout` CLI -> the `@pytest.mark.timeout(...)`
marker. This project sets `timeout = 30` in `[tool.pytest.ini_options]`
(`pyproject.toml:323`) and passes no `--timeout` on the command line
(`make test` runs `pytest -v -n $(PYTEST_XDIST_WORKERS)`, `Makefile:115`), so
`@pytest.mark.timeout(180)` on the e2e supersedes the 30s default. This
refactor must leave that marker on `test_console_scripts_install_and_exit_two`
so the slow build/install test keeps its 180s budget under `-n auto`.

## Plan of work

Three ordered, independently committable work items. Each ends green under
`make all` (and `make markdownlint`/`make nixie` for the docs item).

### WI-1 — Static-parse scaffolding into `tests/conftest.py`

Implements audit-1.2.1 Finding 3, audit-1.2.4 Finding 2, audit-1.2.5 Findings
1-3, audit-1.2.6 Findings 1-2. Cite these in the commit body.

Documentation to read first: `docs/issues/audit-1.2.5.md` Findings 1-3,
`docs/issues/audit-1.2.6.md` Findings 1-2, AGENTS.md "Python verification and
testing" and "Refactoring heuristics and workflow", `docs/developers-guide.md`
"Local workflow". Skills to load: `python-router` then `python-testing`
(fixture-scope and conftest decisions); `python-types-and-apis` for the helper
signatures; `leta` for navigation and `sem` for history.

Create `tests/conftest.py` with a module docstring and these fixtures (all
docstring'd, numpy-style):

- `project_root() -> Path` (session-scope): returns
  `Path(__file__).resolve().parent.parent`. Replaces every `_PROJECT_ROOT`.
- `read_repo_text(project_root)` returning a callable `(*parts: str) -> str`
  that joins `parts` under `project_root` and returns
  `path.read_text(encoding="utf-8")`. Replaces `_state_layout_text` and the
  inline reads.
- `pyproject(project_root) -> dict[str, object]` (session-scope, parsed once):
  `tomllib.loads((project_root / "pyproject.toml").read_text("utf-8"))`.
  Replaces `_parse_scripts`/`_pyproject`/the inline parse.
- `toml_table` returning a callable
  `(parent: Mapping, key: str) -> dict[str, object]` narrowing a value to a
  table or raising `AssertionError`
  (the `_table` logic from `tests/test_interrogate_gate.py:32`).

Then migrate the four static-parse modules to consume the fixtures and delete
their local copies:

- `tests/test_command_names_registry.py`: drop `_PROJECT_ROOT` and
  `_parse_scripts`; have the tests take `pyproject` (or a small
  `project_scripts` fixture derived from it) and assert against
  `names.project_scripts_table()` / `names.COMMAND_NAMES`.
- `tests/test_pyproject_scripts.py`: drop `_PROJECT_ROOT` and the inline parse;
  consume `pyproject`.
- `tests/test_interrogate_gate.py`: drop `_PROJECT_ROOT`, `_pyproject`, and
  `_table`; consume `pyproject`, `toml_table`, and `read_repo_text` (the
  Makefile read). Keep `_dist_name` and the `_DIST_NAME` regex local — they are
  specific to this guard (audit-1.2.5 Finding 3 only asked to share `_table`).
- `tests/test_state_layout_reference.py`: drop `_PROJECT_ROOT` and
  `_state_layout_text`; consume
  `read_repo_text("skill", "novel-ralph", "references", "state-layout.md")`.

Do not touch `tests/test_console_scripts_e2e.py` or
`tests/test_venv_scripts_dir.py` in this work item (their cuprum/resolver
helpers move in WI-2); leaving `_PROJECT_ROOT` in the e2e module until WI-2 is
acceptable because WI-2 removes it.

Tests this work item must add/update (AGENTS.md testing rules):

- This is a behaviour-preserving refactor, so the *existing* tests are the
  regression net: they must pass identically before and after. The mechanism of
  proof is the unchanged assertion bodies now fed by fixtures.
- Add one focused unit test in a new `tests/test_conftest_helpers.py` per shared
  helper that has logic worth pinning: `toml_table` returns the sub-table for a
  table value and raises `AssertionError` for a non-table value (happy +
  unhappy path); `read_repo_text` reads a known repo file (e.g.
  `pyproject.toml`) and returns text containing a known marker; `pyproject`
  returns a dict whose `["project"]["name"]` is the package name.
  `project_root` is trivial (path join) and is exercised transitively; a direct
  assertion that it ends in the repo directory name is sufficient and cheap.
  These tests consume the fixtures the same way production test modules do,
  proving the conftest wiring.
- No property, snapshot, or e2e test is warranted here: there is no new
  invariant over a range of inputs, no multivariant output format, and no new
  externally observable workflow (AGENTS.md "Use property tests …", "Snapshot
  tests …", "Add end-to-end tests …"). State this explicitly in the commit body
  so a reviewer sees the test-tier choice was deliberate.

Validation: `make all` (build, check-fmt, lint, typecheck, test). Expect the
same passed/skipped counts as before plus the new `test_conftest_helpers.py`
cases. Spot-check `make lint` covers interrogate 100% on the new file.

Go/no-go: if any pre-existing test changes outcome, stop (Tolerances).

### WI-2 — Cuprum catalogue and venv resolver into `tests/conftest.py`

Implements audit-1.2.3 Findings 1-2 and audit-1.2.5 Finding 5. Cite these.

Documentation to read first: `docs/issues/audit-1.2.3.md` Findings 1-2,
`docs/scripting-standards.md` "Command execution with cuprum" and "Catalogue
and allowlisting", `docs/adr-006-console-scripts-e2e-posix-policy.md` (the
POSIX-only skip policy), the "Verified locked-library facts" section above.
Skills: `python-testing` (fixtures returning factories),
`python-types-and-apis` (the catalogue/resolver signatures), `leta`/`sem`.

Add to `tests/conftest.py`:

- `single_program_catalogue` fixture returning a callable
  `(name: str, program: Program) -> ProgramCatalogue` that builds a
  one-`ProjectSettings`, one-`Program` catalogue with empty
  `documentation_locations` and `noise_rules`. This is the exact shape the e2e
  builds three times today (audit-1.2.3 Finding 1). Type it precisely; no
  `Any`. Pin the constructor calls to the verified cuprum 0.1.0 API above.
- `venv_scripts_dir` fixture returning the resolver callable
  `(venv_dir: Path) -> Path` — the body of the current `_venv_scripts_dir`
  (`sysconfig.get_path("scripts", "venv", vars=...)`), POSIX `venv` scheme. The
  resolver is behaviour-bearing logic that lives in a non-private home
  (audit-1.2.3 Finding 2). Keep its docstring noting ADR-006 POSIX scope.

Then migrate:

- `tests/test_console_scripts_e2e.py`: remove the module-level `_CATALOGUE`,
  the per-command loop catalogue, and `_venv_scripts_dir`; have
  `test_console_scripts_install_and_exit_two` take `single_program_catalogue`
  and `venv_scripts_dir`. Build the `uv` catalogue and each per-script
  catalogue through the fixture. **Keep** the module `pytestmark` POSIX skip,
  the `@pytest.mark.slow` and `@pytest.mark.timeout(180)` markers, and the
  `_require_success` helper (it is e2e-specific). Drop the now-unused
  `_PROJECT_ROOT` if nothing else uses it (the wheel-build path uses it — keep
  it only if still referenced).
- `tests/test_venv_scripts_dir.py`: delete
  `from tests.test_console_scripts_e2e import _venv_scripts_dir`; have the
  `TestVenvScriptsDir` methods take `venv_scripts_dir` and
  `single_program_catalogue`. Keep the module POSIX `pytestmark`.

Tests this work item must add/update:

- The existing e2e (`test_console_scripts_install_and_exit_two`, marked `slow`)
  and the resolver unit suite (`tests/test_venv_scripts_dir.py`) are the
  regression net; they must pass/skip identically. On this POSIX host the
  resolver suite runs; the `slow` e2e runs under `make test` unless deselected.
- Add a focused unit test (in `tests/test_conftest_helpers.py`) that
  `single_program_catalogue("x", Program("uv"))` returns a `ProgramCatalogue`
  whose `.allowlist` contains `Program("uv")` and that
  `sh.make(Program("uv"), catalogue=...)` resolves without raising
  `UnknownProgramError` — proving the factory builds a usable allowlist without
  paying the slow e2e cost. This mirrors the lightweight-resolver rationale of
  `tests/test_venv_scripts_dir.py`.
- Add an assertion that `single_program_catalogue` accepts an absolute-path
  program string (e.g. `Program("/usr/bin/true")`) and allowlists it, pinning
  the verified "`Program` is a bare `str`, the catalogue is the gate" fact so a
  future cuprum bump that adds path validation fails loudly here.
- No new property/snapshot test: the catalogue construction is deterministic and
  has no multivariant rendered output. The e2e remains the externally
  observable workflow test (AGENTS.md "Add end-to-end tests …"); it is
  preserved, not added to.

Validation: `make all`. Confirm `from tests.test_console_scripts_e2e import` no
longer appears anywhere (`leta grep` / ripgrep for it) and no
`from tests.conftest import` was introduced. Expect unchanged passed/skipped
counts plus the new conftest-helper cases.

Go/no-go: if the e2e or resolver suite changes outcome, or the skip count on
this POSIX host shifts, stop (Tolerances, Risks).

### WI-3 — Document the shared test-scaffolding convention

Implements AGENTS.md "Abstraction / port / helper policy" (record a new shared
abstraction's scope and re-use policy in the docs) and "Documentation
maintenance". Cite these.

Documentation to read first: `docs/developers-guide.md` (the testing/quality
sections), `docs/documentation-style-guide.md`, AGENTS.md "Markdown guidance".
Skills: `en-gb-oxendict` for the prose; `leta`/`sem` if cross-referencing.

Add a short subsection to `docs/developers-guide.md` recording that
`tests/conftest.py` is the single home for shared test scaffolding — the
`project_root`/`pyproject`/`read_repo_text`/`toml_table` parse helpers and the
`single_program_catalogue`/`venv_scripts_dir` cuprum/venv helpers — that test
modules consume these by fixture name (never by importing from another test
module or from conftest), and that new shared scaffolding belongs there. Note
the rule that conftest is inside `PYTHON_TARGETS` and therefore subject to the
full lint/typecheck/docstring gate. Reference the audits that drove it.

If `docs/contents.md` is edited in passing, keep it consistent with its
existing structure; do not expand scope into the unrelated
ADR-006/issues/execplans index gaps (those belong to their own follow-ups,
audit-1.2.5 Finding 6 / audit-1.2.6 Finding 3).

Tests: documentation-only; no code tests. The guard that the *convention* holds
is structural — the absence of the cross-module import (proven in WI-2) and the
absence of duplicated helpers (proven in WI-1).

Validation: `make markdownlint` and `make nixie` (AGENTS.md "Markdown
guidance"); then `make all` to confirm nothing else regressed. Paragraphs
wrapped at 80 columns, dashes for bullets, en-GB Oxford spelling.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-7`.

1. Confirm the branch and a clean tree:

        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-7 \
            branch --show-current
        # expect: roadmap-1-2-7

2. WI-1: create `tests/conftest.py` and `tests/test_conftest_helpers.py`, then
   migrate the four static-parse modules. Validate:

        make all

   Expect a passed line at least equal to the prior count plus the new
   conftest-helper cases, and `0 failed`. Commit (gated) citing the audits.

3. WI-2: extend `tests/conftest.py` with the cuprum catalogue and venv resolver
   fixtures; migrate `test_console_scripts_e2e.py` and
   `test_venv_scripts_dir.py`; delete the cross-module import. Validate:

        make all
        rg -n "from tests.test_console_scripts_e2e import" tests || echo "import gone"
        rg -n "from tests.conftest import" tests || echo "no conftest import"

   Expect "import gone" and "no conftest import". Commit (gated).

4. WI-3: edit `docs/developers-guide.md`. Validate:

        make markdownlint
        make nixie
        make all

   Commit (gated).

Expected `make test` transcript shape (counts illustrative; the real numbers
are whatever the suite reports — the point is no failures and no lost skips):

        tests/test_command_names_registry.py ….            [  ..%]
        tests/test_console_scripts_e2e.py s                  [  ..%]
        tests/test_conftest_helpers.py ….                  [  ..%]
        …
        ==== N passed, M skipped in T s ====

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes with no failures and the same skip set as before
  (the POSIX-only modules skip identically off POSIX; on this POSIX host they
  run). The new `tests/test_conftest_helpers.py` cases pass.
- Lint/typecheck: `make check-fmt`, `make lint` (Ruff + interrogate 100% +
  Pylint), and `make typecheck` (`ty`) pass over `novel_ralph_skill tests`,
  including the new `tests/conftest.py`.
- Audit: `make audit` (pip-audit) passes — no dependency change, so unchanged.
- Markdown (WI-3): `make markdownlint` and `make nixie` pass.
- Structural acceptance: `rg "from tests.test_console_scripts_e2e import"`
  returns nothing; `rg "from tests.conftest import"` returns nothing;
  `rg "_PROJECT_ROOT ="` returns nothing under `tests/` (every copy folded into
  the `project_root` fixture); `git diff --stat` shows net line reduction
  across the migrated modules.

Quality method (how we check): run `make all` after each work item; run the two
`rg` structural checks after WI-2; run `make markdownlint`/`make nixie` after
WI-3.

Behaviour to observe: before the change, `tests/test_venv_scripts_dir.py`
reaches into another test module's private symbol; after, it receives the
resolver as a fixture and the import is gone, with the suite still green.

## Idempotence and recovery

Each work item is a single commit and is independently revertible with
`git revert`. The changes are pure refactors plus additive tests and docs; no
data migration, no destructive step. Re-running `make all` is safe and
repeatable. If a migration breaks a module, restore that module from
`git checkout -- tests/<module>.py` and re-apply the fixture consumption
incrementally.

## Artefacts and notes

The cross-module private import to be removed
(`tests/test_venv_scripts_dir.py:18`):

        from tests.test_console_scripts_e2e import _venv_scripts_dir

The single-program catalogue shape to factor (from
`tests/test_console_scripts_e2e.py:50-59`):

        ProgramCatalogue(
            projects=(
                ProjectSettings(
                    name=…,
                    programs=(Program(…),),
                    documentation_locations=(),
                    noise_rules=(),
                ),
            )
        )

## Interfaces and dependencies

Add no dependencies. In `tests/conftest.py`, define these fixtures (numpy-style
docstrings; precise types; no `Any`):

        # tests/conftest.py
        import collections.abc as cabc
        from pathlib import Path

        import pytest
        from cuprum import Program, ProgramCatalogue

        @pytest.fixture(scope="session")
        def project_root() -> Path: …

        @pytest.fixture(scope="session")
        def pyproject(project_root: Path) -> dict[str, object]: …

        @pytest.fixture
        def read_repo_text(project_root: Path) -> cabc.Callable[…, str]: …

        @pytest.fixture
        def toml_table() -> cabc.Callable[
            [cabc.Mapping[str, object], str], dict[str, object]
        ]: …

        @pytest.fixture
        def single_program_catalogue() -> cabc.Callable[
            [str, Program], ProgramCatalogue
        ]: …

        @pytest.fixture
        def venv_scripts_dir() -> cabc.Callable[[Path], Path]: …

The exact return-callable signatures may be tightened during implementation
(for example `read_repo_text` as `Callable[[str], str]` with `*parts`), but the
fixtures must remain consumable by name with no inter-module imports, and the
cuprum calls must match the verified locked 0.1.0 API in "Verified
locked-library facts".

## Revision note

Initial draft (2026-06-22). Decomposes roadmap task 1.2.7 into three atomic
work items: static-parse scaffolding (WI-1), cuprum catalogue + venv resolver
(WI-2), and the developers-guide convention note (WI-3). Pins the cuprum 0.1.0
and pytest-timeout 2.4.0 behaviour the plan relies on against verified sources.
