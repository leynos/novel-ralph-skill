# Developer guide

This guide explains the contributor workflow for the generated project.

## Local workflow

The public entrypoint for formatting, linting, typechecking, and tests is
`make all`. Narrower Make targets may be invoked when investigating a specific
failure, and changes should be reconciled with the aggregate gate before being
considered complete.

`make lint` runs Ruff, `interrogate` over `$(PYTHON_TARGETS)` to enforce 100%
docstring coverage (the threshold is pinned in `[tool.interrogate]` in
`pyproject.toml`, and `tests/test_interrogate_gate.py` guards it), and Pylint.

Run `make audit` as the dependency vulnerability gate. It runs `pip-audit` for
Python dependencies, and Rust-enabled projects also run `cargo audit` from the
`rust_extension` crate directory.

## Shared test scaffolding

[`tests/conftest.py`](../tests/conftest.py) is the single home for scaffolding
shared across the test suite. It exposes the project-root path (`project_root`),
the parsed `pyproject.toml` (`pyproject`), a repo-relative UTF-8 reader
(`read_repo_text`), a TOML-table accessor (`toml_table`), the one-program cuprum
catalogue builder (`single_program_catalogue`), and the POSIX venv
scripts-directory resolver (`venv_scripts_dir`).

Test modules consume these by fixture name — list the fixture as a test or
helper parameter — and never by importing from another test module or from
`conftest` itself. Importing helpers from `conftest` is fragile across pytest
import modes, and reaching into another test module's private symbols couples
modules through hidden dependencies; both are forbidden here. New shared
scaffolding belongs in `tests/conftest.py` as another fixture rather than a
fresh copy in each module.

`tests/conftest.py` is inside `$(PYTHON_TARGETS)`, so it is subject to the full
Ruff lint and format, 100% `interrogate` docstring coverage, Pylint, and `ty`
typecheck gates — unlike `test_*.py`, it gains no `per-file-ignores` relief, so
it carries a module docstring, a docstring on every fixture, and no bare
`assert` (guards raise `AssertionError` directly). This consolidation discharges
the duplication and cross-module-import findings recorded in
[`audit-1.2.1.md`](issues/audit-1.2.1.md),
[`audit-1.2.3.md`](issues/audit-1.2.3.md),
[`audit-1.2.4.md`](issues/audit-1.2.4.md),
[`audit-1.2.5.md`](issues/audit-1.2.5.md), and
[`audit-1.2.6.md`](issues/audit-1.2.6.md).

## Automation scripts

The [Scripting standards](scripting-standards.md) document provides guidance
for adding or updating helper scripts. New and updated scripts are expected to
use `Cyclopts` for command-line interfaces, `cuprum` for typed and
catalogue-bound external command execution, `pathlib` for filesystem paths, and
`cmd-mox` for tests that mock external executables.

Script changes should update the scripting guide when they introduce a new
convention, command catalogue, testing pattern, or operational expectation that
future contributors need to follow.

## Novel-ralph harness architecture

The novel-ralph skill drives novel authoring through a Ralph Loop: an agent is
re-entered each turn with no memory beyond what is on disk, so progress lives in
`working/` and `state.toml`, and every command is idempotent and resumable.
The deterministic spine is five console-scripts; the model supplies judgement.
The authoritative design is
[novel-ralph-harness-design.md](novel-ralph-harness-design.md); the decisions
behind it are recorded in the ADRs referenced below. This section is the
orientation a contributor needs before reading either.

### The deterministic/judgemental boundary

Scripts detect and report; the model adjudicates. A command never makes a
creative or editorial decision, and the model never hand-edits state or
hand-counts words. This split is the load-bearing invariant of the system and
is recorded in
[adr-001-deterministic-judgemental-boundary.md](adr-001-deterministic-judgemental-boundary.md).
When adding behaviour, decide which side of the boundary it sits on before
writing code: anything requiring taste belongs to the model, anything
mechanically checkable belongs to a command.

### The five commands

The v1 spine is five separate console-scripts in `novel_ralph_skill`, not a
single multiplexer (the rationale is in
[adr-005-command-surface-five-scripts.md](adr-005-command-surface-five-scripts.md),
with distribution in
[adr-004-distribution-console-scripts.md](adr-004-distribution-console-scripts.md)):

- `novel-state` — the only path that mutates `state.toml`. Subcommands
  `init`, `set-cursor`, `advance-phase`, and `recount` are mutators; `check` is
  a read-only checker that reports divergence from disk and exits 4;
  `reconcile` is the mutator that writes the disk-authoritative reconciliation
  `check` reports. See design §4.1 and §5.4.
- `novel-done` — the done predicate as code, evaluated per clause against
  disk. See design §4.2.
- `novel-compile` — regenerates `working/manuscript/compiled.md`
  deterministically in chapter-index order; `--check` is a read-only divergence
  checker. See design §4.3.
- `desloppify` — detects and reports prose tics from a versioned rule pack,
  never editing. See design §4.4 and §6.
- `wordcount` — a read-only checker reporting per-chapter and cumulative
  counts and the next gate distance. See design §4.5.

As of roadmap task 1.2.1 these five names are wired as `[project.scripts]`
console-scripts (`pyproject.toml`) but are still **stubs**: each is a minimal
Cyclopts application defined by the shared `make_stub_app` factory in
[`novel_ralph_skill/commands/stub.py`](../novel_ralph_skill/commands/stub.py)
that prints "`<name>` is not yet implemented" to stderr and exits `2` until its
real behaviour lands in a later slice. The build-and-install proof lives in
[`tests/test_console_scripts_e2e.py`](../tests/test_console_scripts_e2e.py),
which runs on POSIX only (see
[adr-006-console-scripts-e2e-posix-policy.md](adr-006-console-scripts-e2e-posix-policy.md)),
and [`tests/test_pyproject_scripts.py`](../tests/test_pyproject_scripts.py)
guards the entry-point table. The five names live once, as data, in a single
registry,
[`novel_ralph_skill/commands/names.py`](../novel_ralph_skill/commands/names.py);
the entry-point functions and every test derive their names from it, and
[`tests/test_command_names_registry.py`](../tests/test_command_names_registry.py)
asserts the registry and `[project.scripts]` agree, so a rename or dropped entry
point cannot silently drift. Edit a command name there, not in five places. The
JSON envelope, the `--human` switch, and the shared exit-code helper are deferred
to roadmap step 1.3.

### Checker/mutator segregation

Read-only checkers (`novel-done`, `novel-state check`, `wordcount`,
`desloppify`, `novel-compile --check`) write nothing, so the harness can call
them freely. Mutators (`novel-state init`/`set-cursor`/`advance-phase`/`recount`
/`reconcile` and `novel-compile`) are the only commands that touch `state.toml`
or `compiled.md`, and they write atomically via a temporary file plus
`Path.replace`, bracketed by a `[pending_turn]` intent record so a torn
multi-file turn is recoverable. Keep this segregation honest: a command that
detects a finding must not also repair it. See design §3.3 and §3.4.

### The shared JSON envelope

Every command emits the same machine-mode JSON envelope —
`{command, schema_version, ok, working_dir, result, messages}` — with a
`--human` flag for readable output. The contract, and the single shared
implementation both checkers and mutators reuse, is recorded in
[adr-003-shared-interface-contract.md](adr-003-shared-interface-contract.md)
and design §2. New commands adopt the envelope rather than inventing their own
output shape.

The shared implementation lives in `novel_ralph_skill/contract/`. Its public
surface is the frozen `Envelope` dataclass and the `build_envelope` constructor
(which derives `ok` from the exit code and validates `command` against the
single source of truth), the `render_machine` and `render_human` renderers, the
`ENVELOPE_SCHEMA_VERSION` constant, the `ExitCode` enum and its `is_ok` helper,
the `StateInputError` channel, the `CommandOutcome` and `RunContext` value
types, and the `run` wrapper. A new command builds a Cyclopts app, returns a
`CommandOutcome` from its body, and calls `run` rather than calling the app
directly. Two consequences of `run` are load-bearing. First, `run` requires the
caller to build the app with `result_action="return_value"` (plus
`exit_on_error=False, print_error=False, help_on_error=False`) so that `run` —
not Cyclopts — owns every `sys.exit` and envelope emission; without it
Cyclopts's default `result_action` would exit on the body's return value and
pre-empt the success-path envelope. Second, `run` translates Cyclopts's native
exit-`1` usage errors into the contract's exit `2`.

### Disambiguated exit codes

The exit code is a first-class part of the contract because the harness
branches on it (design §3.2):

| Code | Meaning                                                  |
| ---- | -------------------------------------------------------- |
| 0    | Success; checker satisfied or mutator applied            |
| 1    | Benign negative; a predicate is not yet satisfied        |
| 2    | Usage error; the invocation is wrong                     |
| 3    | State or input error; recover state before retrying      |
| 4    | Actionable finding a deterministic detector has surfaced |

The 1-versus-4 distinction is load-bearing: code 1 is the steady-state "not
finished yet" the loop expects every turn, while code 4 signals something only
the model can resolve (desloppify violations, compile divergence, a
reconciliation conflict, a `check` discrepancy). A refused mutator request — an
incoherent `set-cursor` or an out-of-order `advance-phase` — is exit 3, never 1.
A command body signals this exit-3 channel by raising `StateInputError`, which
`run` maps to the state-error envelope and exit code; a missing or unparseable
`state.toml` or an absent working directory uses the same channel.

### State and on-disk layout

`state.toml` is the single source of truth for cursor, phase, gates, word
counts, and the chapter manifest; it is mutated only through `novel-state` and
round-trips losslessly with `tomlkit` to preserve comments and formatting
(rationale in
[adr-002-toml-round-trip-tomlkit.md](adr-002-toml-round-trip-tomlkit.md)).
Manuscript content lives under `working/manuscript/` (`compiled.md` and
per-chapter `chapter-NN/{draft.md,done.flag}`), with planning artefacts under
`working/plan/`. `novel-done` and `novel-compile --check` call the same
compile-and-hash routine, so they cannot disagree about whether `compiled.md`
is stale.

### The state-layout direct-edit guard

Because direct editing of `state.toml` is eliminated (design §4.1; ADR-002
selects `tomlkit` as the only sanctioned writer), the state-layout skill
reference [`skill/novel-ralph/references/state-layout.md`](../skill/novel-ralph/references/state-layout.md)
must not carry any copy-pasteable recipe that writes `state.toml` outside
`novel-state`. The guard
[`tests/test_state_layout_reference.py`](../tests/test_state_layout_reference.py)
enforces this: it scans the reference's executable code fences
(`python`/`py`/`sh`/`bash`/`shell`/`console`) for a write primitive — a known
TOML writer (`tomlkit.dump`, `tomli_w`, `.write_text`), an `open(` paired with a
write-mode literal, a redirect or heredoc targeting the path, or a backstop
`.write(` on the path — and fails `make test` if one names the state file. It
leaves the atomic-write *prose* (design §3.4 and §5.3) and any `novel-state`
invocation example untouched, so it never flags a read-only `open(…, "rb")`, an
unrelated redirect, or the schema fence. Rewriting the reference prose to point
at the `novel-state` commands remains roadmap task 6.2.3's job; the guard only
keeps a hand-edit recipe from re-entering.

## GitHub Actions

The generated repository includes GitHub Actions workflows and local composite
actions under `.github/`.

- `.github/workflows/ci.yml` runs on pushes to `main` and on pull requests. It
  sets up Python 3.13, installs `uv`, validates the generated `Makefile` with
  `mbake`, runs `make build`, `make check-fmt`, `make lint` (Ruff +
  `interrogate` over `$(PYTHON_TARGETS)` + Pylint), `make typecheck`,
  and `make audit`, then delegates coverage generation to the shared coverage
  action. When the Rust extension is enabled, it also sets up Rust, installs
  Rust lint and test tools, and passes `rust_extension/Cargo.toml` to coverage.
- `.github/workflows/act-validation.yml` runs rendered workflow validation in a
  separate workflow. It installs `act`, checks Docker availability, and runs
  `make test WITH_ACT=1` outside the coverage path.
- `.github/workflows/release.yml` publishes wheels when a `v*.*.*` tag is
  pushed. It builds a pure Python wheel, creates a GitHub release with
  generated release notes, downloads wheel artifacts, and uploads them to the
  tag release.
- `.github/workflows/build-wheels.yml` is a reusable workflow for extension
  builds. It accepts a Python version and builds wheels across Linux, Windows,
  and macOS architectures via `.github/actions/build-wheels`.
- `.github/workflows/get-codescene-sha.yml` is manually dispatched. It fetches
  the CodeScene coverage CLI installer, computes its SHA-256 digest, and writes
  the result to the `CODESCENE_CLI_SHA256` repository variable.
- `.github/actions/build-wheels` wraps `cibuildwheel` with `uvx` and uploads
  architecture-specific wheel artifacts.
- `.github/actions/pure-python-wheel` builds a pure Python wheel with
  `uv build --wheel` and uploads the resulting artifact.
- `.github/dependabot.yml` enables dependency update pull requests for GitHub
  Actions and Python packages. Rust-enabled projects also receive Cargo updates.

The `CS_ACCESS_TOKEN` secret must be configured when CodeScene coverage upload
is required. The `CODESCENE_CLI_SHA256` variable should be populated using the
refresh workflow, so CI can verify the downloaded CodeScene installer before
upload.
