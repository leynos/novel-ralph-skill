# Introduce a single source of truth for the five command names

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

This is roadmap task 1.2.4 (`docs/roadmap.md` lines 112-117, step 1.2). It
closes a medium-severity remediation raised by the audit of task 1.2.1: the
list of the five console-script command names is duplicated across the package
and the test suite, so a rename or a dropped entry point can drift between
sources without a single gate catching it. The duplication exists today in:

- `novel_ralph_skill/commands/stub.py` — five entry-point functions
  (`novel_state`, `novel_done`, `novel_compile`, `desloppify`, `wordcount`),
  each calling `make_stub_app("<name>")()` with the console-script name spelt
  out inline.
- `pyproject.toml` `[project.scripts]` (lines 10-15) — five `name = "module:func"`
  entries.
- `tests/test_command_stubs.py` — a `COMMAND_NAMES` tuple (lines 23-29) and an
  `ENTRY_POINTS` tuple (lines 31-37).
- `tests/test_console_scripts_e2e.py` — a second `COMMAND_NAMES` tuple
  (lines 60-66).
- `tests/test_pyproject_scripts.py` — an `EXPECTED_SCRIPTS` mapping (lines
  17-23).

The five names are fixed by `docs/adr-005-command-surface-five-scripts.md`
(`novel-state`, `novel-done`, `novel-compile`, `desloppify`, `wordcount`),
distributed as installed console-scripts by
`docs/adr-004-distribution-console-scripts.md`, and described as the v1 spine in
`docs/novel-ralph-harness-design.md` §4. The audit's prescription is precise:
"a package registry consumed by the entry points and tests, asserted against
`[project.scripts]`, removes the drift risk while the surface is still five thin
stubs."

The deliverable is therefore a **single package-level registry** —
`novel_ralph_skill/commands/names.py` — that records, once, the ordered mapping
from each console-script name to its entry-point function name. `stub.py`
generates its five entry-point functions from that registry; the three test
modules import their name and entry-point data from it; and a new fast test
parses `pyproject.toml` `[project.scripts]` and asserts the registry and the
TOML table agree exactly. After this task there is exactly one place a name is
written as data (the registry) and one place each name is bound to runtime
behaviour (`pyproject.toml`, gated against the registry); every other reference
is derived.

This task is **pure Python plus packaging**: it adds no command behaviour, emits
no new program output, shells out to nothing, and adds no runtime or test
dependency. cuprum is touched only incidentally —
`tests/test_console_scripts_e2e.py` imports the shared `COMMAND_NAMES` instead of
re-declaring it; the cuprum run-loop it added in task 1.2.3 is unchanged.

To verify the implementation: `make test` proves the five entry points still
build, install, and exit `2` (the e2e is unchanged in behaviour, only its name
source moves); a new `tests/test_command_names_registry.py` asserts the registry
matches `pyproject.toml [project.scripts]` exactly (same names, same
entry-point targets, same order) and that each registry name resolves to a
callable on the stub module; the existing stub unit tests still pass, now
parametrized off the shared registry; and `make all`, `make markdownlint`, and
`make nixie` are all green. Success is observable as: a single edit to a command
name in `names.py` would force `pyproject.toml` and every test to agree or fail
the new gate, so the names can no longer silently drift.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- All work must stay exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-4`. Files in the
  root/control worktree must not be edited.
- The five command names and their entry-point targets are fixed by ADR 005 and
  the existing `[project.scripts]` table and must not change. The registry
  records exactly: `novel-state` → `novel_state`, `novel-done` → `novel_done`,
  `novel-compile` → `novel_compile`, `desloppify` → `desloppify`,
  `wordcount` → `wordcount`, all bound to module
  `novel_ralph_skill.commands.stub`. This task introduces a single source of
  truth; it does **not** rename, add, or remove a command.
- The externally observable contract is unchanged. After this task a wheel build
  still installs all five console-scripts, each still resolves on `PATH` and
  still exits `2` with "`<name>` is not yet implemented" on stderr, and the
  stub factory `make_stub_app` and its `STUB_EXIT_CODE = 2` are unchanged in
  behaviour. The e2e assertions (exit `2`, no `Traceback`, name echoed in
  stderr) must not be weakened.
- This task does **not** change any command body, the `make_stub_app` factory's
  logic, the cuprum run-loop in `tests/test_console_scripts_e2e.py`, the venv
  resolver, or the `slow`/`timeout(180)` markers. It does not introduce the
  shared JSON envelope or the `--human` switch — those are roadmap step 1.3.
- The registry is the **only** new place a name is written as data. The five
  entry-point functions in `stub.py` must be derived from the registry (not
  re-spelt inline), and all three existing tests must import their name and
  entry-point data from the registry rather than re-declaring it. A name written
  in two data sources after **all three work items complete** is a defect; this
  is an end-state invariant, not a per-commit one. At work item 1's commit the
  triple duplication (registry, `stub.py` inline, `pyproject.toml`) is expected
  and legitimate — work items 2 and 3 collapse it onto the registry.
- `pyproject.toml [project.scripts]` remains authoritative for the runtime
  binding (the build backend reads it; a Python constant cannot drive entry-point
  installation). The registry does not replace it; the new test makes the two
  agree by gate. (Verified: hatchling — the build backend, `pyproject.toml`
  `[build-system]` — installs console-scripts from `[project.scripts]` only; no
  build backend reads a Python constant for entry points. The registry therefore
  cannot be the runtime source; it is the asserted-against source of truth.)
- No new runtime or test dependency. `tomllib` is in the standard library on
  Python 3.14 (`requires-python = ">=3.14"`, `pyproject.toml` line 6) and is
  already used by `tests/test_pyproject_scripts.py`. syrupy and hypothesis are
  **not** locked (`uv.lock`); this task must not add them — see Decision Log for
  why no snapshot or property suite belongs here.
- Prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` convention.
- Every public module, class, and function carries a docstring; `interrogate`
  enforces 100% coverage (AGENTS.md; Makefile `lint-python`). No file exceeds
  400 lines (AGENTS.md).
- Tests live in the top-level `tests/` tree, never inside the package (AGENTS.md,
  "Python verification and testing"; the `novel_ralph_skill` package contains no
  tests so xdist-backed SlipCover coverage stays correct).
- Markdown prose wraps at 80 columns; code blocks at 120; tables and headings are
  not wrapped; list bullets use `-`; Mermaid is validated by nixie (AGENTS.md
  "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 7 files or more than
  200 net lines, stop and escalate. Expected files: this plan;
  `novel_ralph_skill/commands/names.py` (new registry); `stub.py` (entry-point
  functions derived from the registry); `tests/test_command_stubs.py`,
  `tests/test_console_scripts_e2e.py`, `tests/test_pyproject_scripts.py` (import
  the shared data); `tests/test_command_names_registry.py` (new gate); and a
  one-line cross-reference in `docs/developers-guide.md`. If any **command body**,
  the `make_stub_app` factory logic, the cuprum run-loop, or the
  `[project.scripts]` targets must change, stop and escalate — that is outside
  1.2.4.
- Dependencies: this task adds **no** new runtime or dev dependency. If the
  registry-versus-`[project.scripts]` assertion appears to need syrupy,
  hypothesis, or any new package, stop and escalate (it does not: `tomllib`
  already parses the table, and the comparison is a direct equality on a small
  fixed mapping).
- Registry shape: this plan commits to a single immutable, ordered mapping
  (`name -> entry-point function name`) in `names.py`, plus a derived
  `COMMAND_NAMES` tuple for callers needing only the names. If review prefers a
  different container (for example a `tuple` of `dataclass`/`NamedTuple` records,
  or deriving names by importing `[project.scripts]` at runtime), that is a
  **materially different** design; do not switch mid-implementation. Stop and
  escalate so the module and its consumers are rewritten coherently.
- Direction of truth: this plan makes the Python registry the source of truth and
  asserts `[project.scripts]` against it. The build backend still reads the TOML
  table at install time (it must). If review prefers `[project.scripts]` to be
  the sole source and the registry to be *derived from* it at runtime (parsing
  TOML inside the package), stop and escalate — that inverts the dependency
  direction, adds an import-time TOML read to the package, and changes the test's
  meaning.
- Iterations: if `make all` (or `make markdownlint` / `make nixie`) still fails
  after 3 focused fix attempts on the same gate, stop and escalate.

## Risks

- Risk: a future contributor adds a sixth command to `[project.scripts]` (or
  renames one) but forgets the registry, reintroducing exactly the drift this
  task removes.
  - Severity: medium. Likelihood: medium.
  - Mitigation: the new `tests/test_command_names_registry.py` parses
    `[project.scripts]` and asserts it equals the registry's derived table (names,
    targets, and order). Any divergence fails `make test`, so the gate catches the
    omission rather than letting it ship. The developers' guide one-liner points
    contributors at the registry as the place to edit.
- Risk: the registry and `[project.scripts]` disagree on entry-point *order*,
  and an order-insensitive comparison hides a real reordering.
  - Severity: low. Likelihood: low.
  - Mitigation: the gate compares an ordered structure (a `list` of `(name,
    target)` pairs derived from both the registry's insertion order and the TOML
    table's parse order) **and** the set of names, so both a missing/extra name
    and a reordering are caught. `tomllib` preserves table key order (Python dict
    insertion order), and the registry mapping is constructed in a fixed order.
- Risk: deriving the `stub.py` entry-point functions from the registry obscures
  them from static analysis (Ruff/Pylint/`ty`), or breaks the `module:func`
  resolution the build backend performs.
  - Severity: medium. Likelihood: low.
  - Mitigation: the five entry-point functions stay as **named module-level
    `def`s** (so `module:func` resolution and `ty`/Pylint see real symbols); only
    the console-script *name* each one passes to `make_stub_app` is read from the
    registry, removing the inline string duplication without hiding the functions.
    The new gate asserts each `[project.scripts]` target (`...:novel_state`, …)
    resolves to a callable on the stub module, so a broken binding fails loudly.
- Risk: importing the registry at module top of `tests/test_console_scripts_e2e.py`
  perturbs that POSIX-only, slow test.
  - Severity: low. Likelihood: very low.
  - Mitigation: the import is a pure-Python constant import with no side effects
    and no cuprum/subprocess interaction; the test's `pytestmark` skip guard, the
    `slow`/`timeout(180)` markers, and the cuprum run-loop are untouched. Only the
    inline `COMMAND_NAMES` tuple is replaced by the shared import.

## Progress

- [x] Work item 1: Add the registry module
  `novel_ralph_skill/commands/names.py` (the single source of truth) and the new
  gate `tests/test_command_names_registry.py` asserting it matches
  `pyproject.toml [project.scripts]` and resolves to callables. (done — registry
  is a frozen `MappingProxyType` over an ordered dict plus a derived
  `COMMAND_NAMES` and `project_scripts_table()`; four gate tests pass; `make all`,
  `make markdownlint`, `make nixie` green; CodeRabbit run 1 actioned.)
- [x] Work item 2: Derive the five `stub.py` entry-point functions and the stub
  unit tests' `COMMAND_NAMES`/`ENTRY_POINTS` from the registry. (done — stub.py
  builds a pre-computed `_NAME_FOR` reverse map from the registry and each
  entry-point reads its name from it; the functions stay named module-level
  `def`s. `test_command_stubs.py` imports `COMMAND_NAMES` and derives
  `ENTRY_POINTS` via `getattr(stub, func)`. `make all` green; CodeRabbit run 2
  returned 0 findings.)
- [x] Work item 3: Replace the duplicated name lists in
  `tests/test_console_scripts_e2e.py` and `tests/test_pyproject_scripts.py` with
  the shared registry, and add the developers'-guide cross-reference. (done — the
  e2e imports `COMMAND_NAMES`; `test_pyproject_scripts.py` derives its expectation
  from `names.project_scripts_table()`; the developers' guide points contributors
  at `names.py` as the single edit point. `make all`, `make markdownlint`,
  `make nixie` green; CodeRabbit run 3 returned 0 findings.)

## Surprises & discoveries

- Observation: the build backend cannot consume a Python constant for
  console-script installation, so `[project.scripts]` must remain in
  `pyproject.toml`; the registry is the asserted-against source of truth, not a
  replacement for the TOML table.
  - Evidence: `pyproject.toml` `[build-system]` uses hatchling (the wheel build
    in task 1.2.1/1.2.2); PEP 621 `[project.scripts]` is the standard,
    backend-read location for console-script entry points, and hatchling reads it
    verbatim. No supported backend imports a Python module to discover entry
    points at build time.
  - Impact: Work item 1 keeps `[project.scripts]` and adds a gate
    (`test_command_names_registry.py`) that parses it with `tomllib` and asserts
    equality with the registry. The registry drives `stub.py` and the tests; the
    gate keeps the TOML table honest.
- Observation: no snapshot or property-based suite is warranted for this task.
  - Evidence: the deliverable emits no command output and adds no invariant
    over a range of generated inputs; it is a fixed five-entry mapping checked
    by direct equality. syrupy and hypothesis are not locked (`uv.lock`), and
    AGENTS.md gates snapshots to "multivariant output format consistency" and
    property tests to "an invariant over a range of inputs, states, orderings, or
    transitions" — neither applies. `python-verification` confirms example-based
    pytest is the right (and only needed) adversary here.
  - Impact: the plan uses only example-based pytest with `tomllib`; it adds no
    test dependency.

## Decision log

- Decision: make the Python registry (`novel_ralph_skill/commands/names.py`) the
  single source of truth, and assert `pyproject.toml [project.scripts]` against
  it, rather than deriving names from the TOML at runtime.
  - Rationale: the audit prescribes "a package registry consumed by the entry
    points and tests, asserted against `[project.scripts]`". A package-level
    constant is import-cheap, statically analysable, and has no side effects;
    parsing TOML inside the package at import time would add an I/O read and a
    file-location dependency to every command's import path for no benefit. The
    build backend already reads `[project.scripts]`; the gate keeps the two in
    lockstep without inverting the dependency.
  - Date/Author: 2026-06-22, planning agent.
- Decision: model the registry as a single immutable, ordered mapping
  (`Mapping[str, str]`: console-script name → entry-point function name) plus a
  derived `COMMAND_NAMES: tuple[str, ...]`.
  - Rationale: the data is a small fixed name→target mapping; a plain
    `types.MappingProxyType` over an ordered dict captures it with no dependency
    and is the smallest container that records both the names and their bindings
    (`python-data-shapes`: prefer the simplest container that names the
    relationship; a frozen mapping over a dataclass list when the only fields are
    a key and one value). The `module:func` *module* part is a single shared
    constant (`STUB_MODULE = "novel_ralph_skill.commands.stub"`) so the full
    `[project.scripts]` target is derived, not duplicated.
  - Date/Author: 2026-06-22, planning agent.
- Decision: keep the five entry-point functions as named module-level `def`s in
  `stub.py`; only their console-script *name* argument is read from the registry.
  - Rationale: the build backend resolves `module:func`, so the functions must be
    real, importable symbols; generating them dynamically (for example via
    `setattr` in a loop) would hide them from `ty`/Pylint and from `module:func`
    resolution. Reading only the name string from the registry removes the
    duplication the audit flagged while keeping the functions statically visible.
  - Date/Author: 2026-06-22, planning agent.
- Decision: add **no** snapshot (syrupy) or property (hypothesis/CrossHair) suite.
  - Rationale: per `python-verification`, the change is example-based — a fixed
    mapping asserted by equality and a callable-resolution check — with no
    generated-input invariant and no multivariant output format. Adding syrupy or
    hypothesis would be an unjustified dependency. The mutation-survival concern
    (mutmut) is out of scope for a five-entry constant.
  - Date/Author: 2026-06-22, planning agent.
- Decision: do **not** touch the cuprum run-loop, the venv resolver, or the
  `slow`/`timeout` markers in `tests/test_console_scripts_e2e.py`.
  - Rationale: those are task 1.2.3's settled contract (ADR 006); 1.2.4 only
    replaces the inline `COMMAND_NAMES` tuple with the shared import. The cuprum
    0.1.0 API (`ProgramCatalogue`, `ProjectSettings`, `Program`, `sh.make(...)
    .run_sync(capture=True)`) is unchanged and re-verified against the `v0.1.0`
    tag of `/data/leynos/Projects/cuprum` (`cuprum/program.py`,
    `cuprum/catalogue.py`, `cuprum/sh.py`).
  - Date/Author: 2026-06-22, planning agent.

## Outcomes & retrospective

To be completed at the end of implementation. Record: the registry's final
shape; the exact files changed and net line count; whether the
registry-versus-`[project.scripts]` gate caught any pre-existing mismatch; any
CodeRabbit findings and their disposition; and confirmation that `make all`,
`make markdownlint`, and `make nixie` are green at each commit's HEAD.

### Work item 1 (registry + gate)

- Registry shape landed as planned: `STUB_MODULE: str`, a private ordered
  `dict`, a frozen `COMMAND_ENTRY_POINTS` (`MappingProxyType`), a derived
  `COMMAND_NAMES` tuple, and `project_scripts_table()` returning a fresh dict.
- Gate (`tests/test_command_names_registry.py`) has four tests: TOML equality,
  order equality, callable resolution, and the five-name pin. They pass against
  the unchanged `[project.scripts]`; no pre-existing mismatch was found.
- CodeRabbit run 1 returned 8 findings (4 minor on the new code, 4 trivial on
  this plan). Disposition: added `: str` to `STUB_MODULE` (minor). Skipped the
  `_PROJECT_ROOT: Path` annotation and the bare-assert "add a message" findings
  to stay consistent with the established repo test style (`tests/`
  `test_pyproject_scripts.py` and `test_command_stubs.py` use bare asserts and
  leave `_PROJECT_ROOT`/`STUB_EXIT_CODE` unannotated; `ty` passes). Actioned all
  four trivial plan findings: clarified the "two data sources" constraint as an
  end-state (not per-commit) invariant; recommended the pre-computed reverse-map
  shape for work item 2; and added docstring caveats to the illustrative code
  blocks.
- `make all`, `make markdownlint`, and `make nixie` green at HEAD.

### Work item 2 (stub + stub tests)

- `stub.py` gained the pre-computed `_NAME_FOR` reverse map (the recommended
  shape from the plan); each of the five entry points reads its console-script
  name from it. The functions remain named module-level `def`s so `module:func`
  resolution and static analysis still see them; `make_stub_app` and
  `STUB_EXIT_CODE` are unchanged.
- `test_command_stubs.py` now imports `COMMAND_NAMES` and `COMMAND_ENTRY_POINTS`
  and derives `ENTRY_POINTS` by pairing each name with `getattr(stub, func)`.
  Every prior parametrized assertion is preserved.
- CodeRabbit run 2 returned 0 findings. `make all` green at HEAD.

### Work item 3 (e2e/pyproject tests + developers' guide)

- `test_console_scripts_e2e.py` dropped its inline `COMMAND_NAMES` tuple and
  imports the shared one; the cuprum run-loop, the POSIX skip guard, and the
  `slow`/`timeout(180)` markers are untouched.
- `test_pyproject_scripts.py` dropped its hand-written `EXPECTED_SCRIPTS` mapping
  and now asserts the parsed `[project.scripts]` equals
  `names.project_scripts_table()`. It stays complementary to the dedicated
  registry gate (which additionally pins order, callable resolution, and the
  five-name invariant); both are kept per the audit's "a … registry … tests".
- `docs/developers-guide.md` "The five commands" section gained a cross-reference
  naming `names.py` as the single edit point.
- CodeRabbit run 3 returned 0 findings. `make all`, `make markdownlint`, and
  `make nixie` green at HEAD.

### Summary

- Three commits, one per work item. Files changed: new
  `novel_ralph_skill/commands/names.py` and
  `tests/test_command_names_registry.py`; edits to
  `novel_ralph_skill/commands/stub.py`, `tests/test_command_stubs.py`,
  `tests/test_console_scripts_e2e.py`, `tests/test_pyproject_scripts.py`, and
  `docs/developers-guide.md`; this execplan and its review note. Net effect: the
  five names are written as data in exactly one place; every other reference is
  derived or gated. The registry-versus-`[project.scripts]` gate found no
  pre-existing mismatch. Three CodeRabbit runs (8 findings on run 1, 0 on runs 2
  and 3); all actionable findings actioned, the rest skipped with the rationale
  recorded above. `make all`, `make markdownlint`, and `make nixie` green at
  every commit's HEAD.

## Context and orientation

The repository is the Python package skeleton becoming the deterministic spine of
the novel-ralph harness. Orient with these files; all paths are relative to the
worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-4`:

- `novel_ralph_skill/commands/stub.py` — the shared `make_stub_app(name)` factory
  (`STUB_EXIT_CODE = 2`) and the five entry-point functions `novel_state`,
  `novel_done`, `novel_compile`, `desloppify`, `wordcount`, each calling
  `make_stub_app("<name>")()` with the console-script name spelt inline (the
  duplication this task removes from the package side).
- `novel_ralph_skill/commands/__init__.py` — the `commands` subpackage docstring;
  the new `names.py` lives beside it.
- `pyproject.toml` — `[project.scripts]` (lines 10-15) maps the five names to
  `novel_ralph_skill.commands.stub:<func>`; `requires-python = ">=3.14"`
  (line 6); `[tool.pytest.ini_options]` sets `timeout = 30`,
  `testpaths = ["tests"]`, and the `slow` marker (lines 305-309).
- `tests/test_command_stubs.py` — `COMMAND_NAMES` (lines 23-29) and `ENTRY_POINTS`
  (lines 31-37) tuples driving the parametrized stub unit tests.
- `tests/test_console_scripts_e2e.py` — a second `COMMAND_NAMES` tuple (lines
  60-66); POSIX-only (`pytestmark` skip), `slow`, `timeout(180)`; runs the
  installed scripts through a cuprum catalogue keyed on their absolute paths.
- `tests/test_pyproject_scripts.py` — the fast gate that parses
  `[project.scripts]` with `tomllib` and asserts it equals `EXPECTED_SCRIPTS`
  (lines 17-23): the natural home/sibling for the new registry gate.
- `uv.lock` — pins `cuprum 0.1.0`, `cyclopts 4.18.0`; does **not** contain syrupy
  or hypothesis.
- `Makefile` — `make all` is `build check-fmt lint typecheck test` (line 28);
  `make test` is `uv run pytest -v -n auto`; `make lint` runs Ruff,
  `interrogate --fail-under 100`, and PyPy-backed Pylint over
  `PYTHON_TARGETS = novel_ralph_skill tests`; `make markdownlint` and `make nixie`
  gate Markdown and Mermaid.
- `docs/roadmap.md` lines 112-117 — this task; lines 104-111 — the adjacent 1.2.3
  (the e2e POSIX policy, already done).
- `docs/adr-005-command-surface-five-scripts.md` — fixes the five names and the
  five-script (not multiplexer) shape.
- `docs/adr-004-distribution-console-scripts.md` — fixes installed
  console-scripts in `novel_ralph_skill` as the distribution form.
- `docs/novel-ralph-harness-design.md` §4 (lines 237-368) — the five commands as
  the v1 spine.
- `docs/developers-guide.md` lines 53-87 — "The five commands" section, the
  cross-reference target for the registry.
- `docs/scripting-standards.md` — the cuprum-over-subprocess and Cyclopts
  conventions (unchanged here; the registry shells out to nothing).
- The locked cuprum sources, pinned at the `v0.1.0` tag of
  `/data/leynos/Projects/cuprum`: `cuprum/program.py` (`Program` newtype),
  `cuprum/catalogue.py` (`ProgramCatalogue`, `ProjectSettings`),
  `cuprum/sh.py` (`make`, `SafeCmd.run_sync`, `CommandResult`) — relevant only
  because the e2e consuming the registry runs through them; this task makes no
  new cuprum call.

Terms of art, defined so the plan is self-contained:

- **Console-script.** A command installed onto `PATH` from a package's
  `[project.scripts]` entry points. On POSIX it is a launcher in the venv `bin/`.
- **Entry-point target.** The `"module:function"` string a `[project.scripts]`
  value holds; the build backend imports `module` and binds `function` as the
  command. Here, `"novel_ralph_skill.commands.stub:novel_state"` and so on.
- **Single source of truth (registry).** One package-level data structure that
  records each command name once; every other reference (entry-point functions,
  tests) derives from it, and the runtime `[project.scripts]` table is asserted
  against it by a gate.

Skills to load before touching code (per the global agent instructions and the
worktree standing rules):

- `python-router` first, to route to the smaller skills below.
- `python-data-shapes` for the registry container choice (a frozen, ordered
  `Mapping[str, str]` via `types.MappingProxyType`, plus a derived
  `COMMAND_NAMES` tuple; the entry-point *module* as one shared constant so the
  full target is derived not duplicated).
- `python-testing` for the test shape (a fast `tomllib`-driven gate; parametrized
  stub tests fed from the shared registry; preserving the e2e's `slow`/`timeout`
  markers and skip guard).
- `python-verification` only to confirm that **no** Hypothesis/CrossHair/mutmut
  suite belongs here (example-based fixed-mapping assertion, not a generative
  contract); `hypothesis`, `crosshair`, and `mutmut` are not loaded or used.
- `leta` for navigating the package and test tree; `sem` for history.
- `en-gb-oxendict` for the docstring and developers'-guide prose.

Authoritative sources to read before editing:

- `docs/roadmap.md` lines 104-117 — task 1.2.4 and the adjacent 1.2.3 boundary.
- `docs/adr-005-command-surface-five-scripts.md` and
  `docs/adr-004-distribution-console-scripts.md` — the five fixed names and the
  console-script distribution form.
- `docs/novel-ralph-harness-design.md` §4 — the five commands.
- `docs/developers-guide.md` lines 53-87 — the cross-reference target.
- `docs/scripting-standards.md` — Cyclopts/cuprum conventions (context only).
- `AGENTS.md` — quality gates, en-GB Oxford spelling, 400-line limit, 100%
  docstring coverage, tests under `tests/`, snapshot discipline, Markdown
  guidance.
- `.rules/python-00.md`, `.rules/python-typing.md`, `.rules/python-return.md`,
  `.rules/python-pyproject.md` — house Python style, typing, return, and
  packaging conventions.

## Plan of work

Three atomic, independently-committable work items, each ending with its own
validation; `make all` must be green before each code commit, and the
Markdown-touching work item also runs `make markdownlint` and `make nixie`. The
items are ordered so the source of truth and its gate land first (1), then the
package side derives from it (2), then the remaining tests and the doc converge
on it (3). Each commit leaves the suite green.

### Work item 1 — Add the registry module and its gate

Implements: roadmap task 1.2.4 ("a package registry consumed by the entry points
and tests, asserted against `[project.scripts]`");
`docs/adr-005-command-surface-five-scripts.md` (the five fixed names);
`docs/adr-004-distribution-console-scripts.md` (the entry-point targets bind to
`novel_ralph_skill.commands.stub`).

Add `novel_ralph_skill/commands/names.py`, the single source of truth:

- A module-level constant `STUB_MODULE = "novel_ralph_skill.commands.stub"` (the
  one place the entry-point module is named).
- A frozen, ordered registry mapping console-script name to its entry-point
  function name, for example (illustrative; add module and per-function
  docstrings before committing — Ruff D, interrogate 100%):

  ```python
  from __future__ import annotations

  import types

  STUB_MODULE = "novel_ralph_skill.commands.stub"

  _COMMAND_ENTRY_POINTS: dict[str, str] = {
      "novel-state": "novel_state",
      "novel-done": "novel_done",
      "novel-compile": "novel_compile",
      "desloppify": "desloppify",
      "wordcount": "wordcount",
  }

  COMMAND_ENTRY_POINTS: types.MappingProxyType[str, str] = types.MappingProxyType(
      _COMMAND_ENTRY_POINTS
  )
  """Ordered map of console-script name to its stub entry-point function name."""

  COMMAND_NAMES: tuple[str, ...] = tuple(COMMAND_ENTRY_POINTS)
  """The five console-script names, in registration order."""


  def project_scripts_table() -> dict[str, str]:
      """Return the expected ``[project.scripts]`` table derived from the registry."""
      return {
          name: f"{STUB_MODULE}:{func}"
          for name, func in COMMAND_ENTRY_POINTS.items()
      }
  ```

  (Exact form pinned by the implementer against `.rules/python-typing.md` and
  `.rules/python-return.md`; `MappingProxyType` gives an immutable, ordered view
  with no dependency.)

Add `tests/test_command_names_registry.py`, the gate that ties the registry to
the runtime table:

1. Parse `pyproject.toml` `[project.scripts]` with `tomllib` (as
   `tests/test_pyproject_scripts.py` already does) and assert it **equals**
   `names.project_scripts_table()` — same names, same `module:func` targets.
2. Assert the table's key order matches `names.COMMAND_NAMES` order (parse order
   versus registration order), so a reordering is caught, not just a
   missing/extra name. Compare `list(parsed)` to `list(names.COMMAND_NAMES)`.
3. Assert each registry entry-point function name resolves to a callable on the
   imported stub module (`getattr(stub, func)` is callable), proving the
   `module:func` binding the build backend will perform is satisfiable.
4. Assert `len(names.COMMAND_NAMES) == 5` and that the names are exactly the ADR
   005 set, so the source of truth itself is pinned (a stray sixth entry fails
   here, not only at the TOML gate).

Read first: `docs/roadmap.md` lines 112-117; `docs/adr-005-command-surface-five-scripts.md`;
`docs/adr-004-distribution-console-scripts.md`; `.rules/python-typing.md`,
`.rules/python-return.md`, `.rules/python-00.md`; `tests/test_pyproject_scripts.py`
(the `tomllib` pattern to mirror).

Skills: `python-router`, then `python-data-shapes` (the frozen ordered mapping),
then `python-testing` (the `tomllib` gate). `python-verification` only to
reconfirm no property/snapshot suite belongs here.

Tests added/updated:

- `tests/test_command_names_registry.py` (new) — the registry-versus-
  `[project.scripts]` equality gate, the order check, the callable-resolution
  check, and the five-name pin. This is the load-bearing new gate that makes the
  single source of truth enforceable.

Validation: `make test` passes (the new gate is green against the unchanged
`[project.scripts]`); `make lint` (Ruff, `interrogate --fail-under 100`, Pylint),
`make check-fmt`, `make typecheck` pass over the new module and test; `make all`
is green.

### Work item 2 — Derive the stub entry points and stub unit tests from the registry

Implements: roadmap task 1.2.4 ("a package registry consumed by the entry
points"); removes the package-side and stub-test name duplication.

In `novel_ralph_skill/commands/stub.py`:

- Import the registry: `from novel_ralph_skill.commands.names import COMMAND_ENTRY_POINTS`
  (or the names tuple, as needed).
- Keep the five entry-point functions as **named module-level `def`s** (so
  `module:func` resolution and static analysis still see them), but have each one
  read its console-script name from the registry rather than spelling it inline,
  for example:

  ```python
  def novel_state() -> None:
      """Console-script entry point for ``novel-state`` (stub; exits ``2``)."""
      make_stub_app(_name_for("novel_state"))()
  ```

  The default, path-of-least-resistance shape is a pre-computed module-level
  reverse map built once from the registry — for example
  `_NAME_FOR = {func: name for name, func in COMMAND_ENTRY_POINTS.items()}` —
  read by each function as `make_stub_app(_NAME_FOR["novel_state"])()`, so the
  literal `"novel-state"` string is no longer duplicated in the body. A per-call
  `_name_for()` helper that scans the registry on every invocation is an
  acceptable alternative but is a materially different shape; prefer the
  pre-computed map and escalate for design review before adopting the per-call
  form. The only hard constraint is that the console-script name string is
  **not** re-spelt inline. `make_stub_app` and `STUB_EXIT_CODE` are unchanged.

In `tests/test_command_stubs.py`:

- Replace the inline `COMMAND_NAMES` tuple with
  `from novel_ralph_skill.commands.names import COMMAND_NAMES`.
- Derive `ENTRY_POINTS` from the registry by pairing each name with
  `getattr(stub, COMMAND_ENTRY_POINTS[name])`, so the `(name, callable)` pairs
  are no longer hand-listed. All parametrized cases (`test_command_result_exits_two`,
  `test_unknown_option_exits_one`, `test_meta_flags_exit_zero`,
  `test_entry_point_callable_exits_two`) keep their current assertions.

Read first: `novel_ralph_skill/commands/stub.py`; `tests/test_command_stubs.py`;
`.rules/python-00.md`, `.rules/python-return.md`; the new
`novel_ralph_skill/commands/names.py` from work item 1.

Skills: `python-router`, then `python-data-shapes` (consuming the registry) and
`python-testing` (parametrizing off the shared data).

Tests added/updated:

- `tests/test_command_stubs.py` (updated) — `COMMAND_NAMES` and `ENTRY_POINTS`
  now derive from the registry; every existing assertion is preserved. No new
  test file; the four parametrized tests still pin the no-arg/positional exit-2
  path, the unknown-option exit-1 carve-out, the `--help`/`--version` exit-0
  carve-outs, and the entry-point callables.

Validation: `make test` passes (the stub tests are green off the shared
registry, and the work-item-1 gate still passes since the `[project.scripts]`
targets and the registry agree); `make lint` reports no unused import; `make all`
is green.

### Work item 3 — Converge the e2e and pyproject tests on the registry, and document it

Implements: roadmap task 1.2.4 ("consumed by … tests"); AGENTS.md ("Document
internally facing conventions in `docs/developers-guide.md`").

In `tests/test_console_scripts_e2e.py`:

- Replace the inline `COMMAND_NAMES` tuple (lines 60-66) with
  `from novel_ralph_skill.commands.names import COMMAND_NAMES`. The cuprum
  run-loop, the `pytestmark` POSIX skip guard, the `slow`/`timeout(180)` markers,
  the venv resolver, and every assertion (exit `2`, no `Traceback`, name in
  stderr) are unchanged.

In `tests/test_pyproject_scripts.py`:

- Replace the hand-written `EXPECTED_SCRIPTS` mapping (lines 17-23) with
  `names.project_scripts_table()` so this gate, too, derives its expectation from
  the registry rather than re-declaring it. The test's behaviour (assert the
  parsed `[project.scripts]` equals the expected table) is preserved; its
  expectation now comes from the single source of truth. (This makes
  `test_pyproject_scripts.py` and the new `test_command_names_registry.py`
  complementary: the former proves the TOML matches the registry by the existing
  fast path; the latter additionally pins order, callable resolution, and the
  five-name invariant. If review judges the two redundant, fold the order/callable
  checks into `test_pyproject_scripts.py` and drop the new file — but default to
  keeping the dedicated registry gate, as the audit names "a … registry … tests"
  explicitly.)

In `docs/developers-guide.md`:

- Add a one-line cross-reference in the "The five commands" section (lines
  53-87) noting that the five names live in a single registry,
  `novel_ralph_skill/commands/names.py`, consumed by the entry points and the
  tests and asserted against `[project.scripts]`, so the names cannot drift.

Read first: `tests/test_console_scripts_e2e.py`; `tests/test_pyproject_scripts.py`;
`docs/developers-guide.md` lines 53-87; `docs/documentation-style-guide.md`;
AGENTS.md "Markdown guidance".

Skills: `python-router`, then `python-testing` (the import swaps); `en-gb-oxendict`
for the developers'-guide prose.

Tests added/updated:

- `tests/test_console_scripts_e2e.py` (updated) — imports the shared
  `COMMAND_NAMES`; behaviour unchanged.
- `tests/test_pyproject_scripts.py` (updated) — derives `EXPECTED_SCRIPTS` from
  `names.project_scripts_table()`; behaviour unchanged.

Validation: `make test` passes (all suites green off the single registry);
`make lint`/`make check-fmt`/`make typecheck` pass; `make markdownlint` and
`make nixie` pass over the edited developers' guide; `make all` is green.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-4`.

Confirm the branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-4 \
  branch --show-current
```

Expect `roadmap-1-2-4`.

Re-verify the load-bearing facts on the target machine before relying on them
(verified at planning time):

```bash
uv run python -c "import tomllib; print('tomllib stdlib ok')"
uv run python - <<'PY'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
print("scripts:", list(data["project"]["scripts"]))
PY
# expect: ['novel-state', 'novel-done', 'novel-compile', 'desloppify', 'wordcount']
```

Per-work-item validation:

```bash
make all          # build check-fmt lint typecheck test (every code work item)
make markdownlint # developers'-guide edit (work item 3)
make nixie        # Mermaid validation (work item 3; no diagrams expected)
```

Expected high-level transcript after work item 1 (illustrative):

```plaintext
$ make test
... tests/test_command_names_registry.py::test_registry_matches_project_scripts PASSED
... tests/test_command_names_registry.py::test_registry_order_matches_table PASSED
... tests/test_command_names_registry.py::test_entry_points_resolve_to_callables PASSED
... tests/test_command_names_registry.py::test_registry_has_exactly_five_names PASSED
===== N passed in Xs =====
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- A single registry, `novel_ralph_skill/commands/names.py`, records each of the
  five console-script names exactly once, with its entry-point function name and
  the shared stub module.
- `tests/test_command_names_registry.py` parses `pyproject.toml [project.scripts]`
  and asserts it equals the registry-derived table (names, targets, order), that
  each entry-point function resolves to a callable on the stub module, and that
  there are exactly the five ADR-005 names.
- `novel_ralph_skill/commands/stub.py`'s five entry-point functions no longer
  spell their console-script names inline; they read them from the registry, and
  remain named module-level `def`s for `module:func` resolution.
- `tests/test_command_stubs.py`, `tests/test_console_scripts_e2e.py`, and
  `tests/test_pyproject_scripts.py` all derive their command-name (and
  entry-point) data from the registry; none re-declares the list.
- The externally observable contract is unchanged: a wheel build installs all
  five console-scripts, each resolves on `PATH` and exits `2` with the
  "not yet implemented" message (proved by the unchanged e2e on POSIX).
- `docs/developers-guide.md` points contributors at the registry as the single
  place to edit a command name.

Quality criteria (what "done" means):

- Tests: `make test` passes; `tests/test_command_names_registry.py` is present and
  green; the stub, e2e, and pyproject tests pass off the shared registry; all
  pre-existing assertions still hold.
- Lint/typecheck: `make lint` (Ruff, `interrogate --fail-under 100`, Pylint),
  `make check-fmt` (`ruff format --check`), and `make typecheck` (`ty check`) all
  pass; no unused import; the new module and test carry full docstrings.
- Markdown/Mermaid: `make markdownlint` and `make nixie` pass over the edited
  developers' guide.
- Aggregate: `make all` is green at each code work item's commit.

Quality method (how it is checked): run `make all` before and after each code
work item; run `make markdownlint` and `make nixie` after the documentation
edit in work item 3.

## Idempotence and recovery

- The registry module is a pure constant with no side effects; importing it is
  re-runnable and deterministic.
- The new gate and the updated tests are pure and re-runnable; the e2e still
  writes only into its own `tmp_path` and touches no tracked file or `working/`
  state.
- The edits are in-place and additive (one new module, one new test, import swaps
  in three tests, a one-line stub-body change per function, a one-line doc
  cross-reference); re-running `make all` rebuilds the venv and re-runs the suite
  from a clean state.
- If a Markdown gate fails, re-wrap the developers'-guide line to 80 columns and
  re-run `make markdownlint`.
- If `make build` leaves a partial environment, `make clean` then `make build`
  restores a known state.
- No step is destructive to tracked files beyond the intended edits and updates
  to this execplan.

## Artifacts and notes

- Locked versions, verified: `cuprum 0.1.0`, `cyclopts 4.18.0` (`uv.lock`);
  syrupy and hypothesis are **not** locked, so no snapshot or property suite is
  added.
- `tomllib` is standard-library on Python 3.14 (`requires-python = ">=3.14"`) and
  is already used by `tests/test_pyproject_scripts.py`; the new gate reuses that
  pattern with no new dependency.
- The build backend is hatchling (`pyproject.toml [build-system]`); it installs
  console-scripts from `[project.scripts]` only, so the registry is the
  asserted-against source of truth, not a runtime replacement for the TOML table.
- cuprum 0.1.0 API re-confirmed at the `v0.1.0` tag of
  `/data/leynos/Projects/cuprum`: `cuprum/program.py`
  (`Program = typ.NewType("Program", str)`), `cuprum/catalogue.py`
  (`ProgramCatalogue`, `ProjectSettings`), `cuprum/sh.py` (`make`,
  `SafeCmd.run_sync(capture=True)` → `CommandResult`). This task makes **no** new
  cuprum call; the e2e's existing run-loop is untouched.
- Scope fences restated: this task does **not** change any command body, the
  `make_stub_app` factory logic, the cuprum run-loop, the venv resolver, the
  `slow`/`timeout` markers, or the `[project.scripts]` targets; it does **not**
  rename, add, or remove a command; it does **not** introduce the JSON envelope
  (step 1.3) or any new dependency.

## Interfaces and dependencies

Dependencies: **no change** to `pyproject.toml` dependency tables or `uv.lock`.
This task adds no runtime and no test dependency.

New module shape (illustrative; the implementer pins the exact form against
`.rules/python-typing.md` and `.rules/python-return.md`, and adds module and
per-function docstrings before committing — Ruff D, interrogate 100%):

```python
# novel_ralph_skill/commands/names.py
from __future__ import annotations

import types

STUB_MODULE = "novel_ralph_skill.commands.stub"

_COMMAND_ENTRY_POINTS: dict[str, str] = {
    "novel-state": "novel_state",
    "novel-done": "novel_done",
    "novel-compile": "novel_compile",
    "desloppify": "desloppify",
    "wordcount": "wordcount",
}

COMMAND_ENTRY_POINTS: types.MappingProxyType[str, str] = types.MappingProxyType(
    _COMMAND_ENTRY_POINTS
)
COMMAND_NAMES: tuple[str, ...] = tuple(COMMAND_ENTRY_POINTS)


def project_scripts_table() -> dict[str, str]:
    """Return the expected ``[project.scripts]`` table derived from the registry."""
    return {
        name: f"{STUB_MODULE}:{func}"
        for name, func in COMMAND_ENTRY_POINTS.items()
    }
```

Gate shape (illustrative; assertions pinned by the implementer):

```python
# tests/test_command_names_registry.py
import tomllib
from pathlib import Path

from novel_ralph_skill.commands import names, stub

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_scripts() -> dict[str, str]:
    data = tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text("utf-8"))
    return data["project"]["scripts"]


def test_registry_matches_project_scripts() -> None:
    assert _parse_scripts() == names.project_scripts_table()


def test_registry_order_matches_table() -> None:
    assert list(_parse_scripts()) == list(names.COMMAND_NAMES)


def test_entry_points_resolve_to_callables() -> None:
    for func in names.COMMAND_ENTRY_POINTS.values():
        assert callable(getattr(stub, func))


def test_registry_has_exactly_five_names() -> None:
    assert names.COMMAND_NAMES == (
        "novel-state", "novel-done", "novel-compile", "desloppify", "wordcount",
    )
```

Out of scope (do not build here): any command body or `make_stub_app` change; any
`[project.scripts]` target change; a rename/add/remove of a command; the JSON
envelope or `--human` switch (step 1.3); any cuprum, venv-resolver, or marker
change in the e2e; any snapshot (syrupy) or property (hypothesis/CrossHair) suite.

## Revision note

- 2026-06-22 (planning round 1): Authored the self-contained plan against the
  locked toolchain. Catalogued the five-place duplication (`stub.py`,
  `pyproject.toml`, and three test modules) the task 1.2.1 audit flagged. Pinned
  the design to a single package registry (`names.py`: a frozen, ordered
  `MappingProxyType` of name → entry-point function, plus a derived
  `COMMAND_NAMES` and a `project_scripts_table()` helper) consumed by the entry
  points and tests and asserted against `[project.scripts]` via a new
  `tomllib`-driven gate. Verified that the build backend (hatchling) reads
  `[project.scripts]` and cannot consume a Python constant, so the registry is the
  asserted-against source of truth rather than a runtime replacement. Confirmed
  `tomllib` is stdlib on Python 3.14 and already used by
  `tests/test_pyproject_scripts.py`, so no dependency is added. Confirmed via
  `python-verification` that no snapshot or property suite is warranted (a fixed
  five-entry mapping asserted by equality; syrupy/hypothesis unlocked). Re-pinned
  the cuprum 0.1.0 API at the `v0.1.0` tag and confirmed the e2e's run-loop is
  untouched. Decomposed into three atomic work items (registry+gate; stub +
  stub-tests; e2e/pyproject tests + developers' guide) and fenced out the JSON
  envelope, command bodies, and any rename. The plan remains DRAFT pending review.
