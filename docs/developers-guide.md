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
(`read_repo_text`), a TOML-table accessor (`toml_table`), the PEP 508
dependency-name normaliser (`dist_name`, a `(spec) -> str | None` callable that
reduces a requirement string to its bare distribution name), the one-program
cuprum catalogue builder (`single_program_catalogue`), and the POSIX venv
scripts-directory resolver (`venv_scripts_dir`).

Test modules consume these by fixture name — list the fixture as a test or
helper parameter — and never by importing from another test module or from
`conftest` itself. Importing helpers from `conftest` is fragile across pytest
import modes, and reaching into another test module's private symbols couples
modules through hidden dependencies; both are forbidden here. New shared
scaffolding belongs in `tests/conftest.py` as another fixture rather than a
fresh copy in each module.

One narrow exception applies to shared *types*. A type that describes a
fixture's value — such as the `RepoTextReader` `Protocol` that types the
`read_repo_text` fixture's return — may be imported from `conftest` under an
`if TYPE_CHECKING:` guard (`from conftest import RepoTextReader`). This does
not reintroduce the fragility the rule guards against: a `TYPE_CHECKING`
import is `False` at runtime, so it creates no runtime cross-module import and
cannot fail under any pytest import mode. It conveys a type only, never a
fixture or helper *value*; fixtures are still consumed by parameter name. The
prohibition on importing fixture or helper values, and on reaching into
another module's private symbols, is unchanged. The variadic fixture's return
type is expressed as a named `typing.Protocol` defined inside the
`TYPE_CHECKING` block of `tests/conftest.py`, rather than as
`Callable[..., str]`, because the `...` wildcard disables per-call
argument-shape checking.

`tests/conftest.py` is inside `$(PYTHON_TARGETS)`, so it is subject to the full
Ruff lint and format, 100% `interrogate` docstring coverage, Pylint, and `ty`
typecheck gates — unlike `test_*.py`, it gains no `per-file-ignores` relief, so
it carries a module docstring, a docstring on every fixture, and no bare
`assert` (guards raise `AssertionError` directly). This consolidation discharges
the duplication and cross-module-import findings recorded in
[`audit-1.2.1.md`](issues/audit-1.2.1.md),
[`audit-1.2.3.md`](issues/audit-1.2.3.md),
[`audit-1.2.4.md`](issues/audit-1.2.4.md),
[`audit-1.2.5.md`](issues/audit-1.2.5.md),
[`audit-1.2.6.md`](issues/audit-1.2.6.md), and
[`audit-1.2.7.md`](issues/audit-1.2.7.md) (Findings 1-2: the seventh
`pyproject` parse and the divergent dependency-name normaliser, both now
folded onto the shared fixtures).

### The `working/` fixture corpus

The [`working_corpus`](../tests/working_corpus) package (roadmap task 1.3.2) is
the shared on-disk test corpus the slice suites in phases 2-6 consume. It builds
a `working/` directory tree under a test's `tmp_path` for each of the eleven
phase states, for coherent and deliberately incoherent `state.toml` variants,
and for `done.flag` permutations. The corpus is anchored to the design's
authoritative artefacts —
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §5.1 (schema and
phase enum) and §5.2 (invariants), and
[`state-layout.md`](../skill/novel-ralph/references/state-layout.md) (the
on-disk layout) — not to the typed schema (roadmap task 2.1.1) or the §5.2
validator (task 2.1.2), which consume it. It is consumed **unchanged** by phases
2-6 (the roadmap 1.3.2 success criterion).

The package's public surface is `WorkingTreeSpec` and `ChapterSpec` (the
specification dataclasses), `build_working_tree` (the tree builder),
`concatenate_drafts` with `CORPUS_SEPARATOR` and `GATE_THRESHOLDS` (the §4.3/§9
compile model and the knitting thresholds), `PHASE_STATES` with
`COHERENT_BASELINE` (the eleven coherent phase states and the mid-drafting
baseline), `INCOHERENT_VARIANTS` (one deliberately incoherent variant per §5.2
invariant plus the §5.4 disk and §3.4 torn-turn cases), `DONE_FLAG_PERMUTATIONS`
(coherent `done.flag` patterns), and `corpus_check` with `CORPUS_INVARIANT_NAMES`
(the corpus-local structural oracle and its stable invariant-name vocabulary).

How the corpus is consumed:

- **By fixture name only.** Later slices consume the corpus through pytest
  fixtures, never by a runtime value import. The fixtures live in the registered
  plugin module [`tests/corpus_fixtures.py`](../tests/corpus_fixtures.py)
  (registered via `pytest_plugins` in `conftest`), which is the single runtime
  importer of `working_corpus`. The plugin sits beside `conftest` rather than
  inside it only because the corpus fixture surface would push `conftest` past
  the 400-line module cap; for fixture resolution a registered plugin is
  `conftest`-equivalent. The exposed fixtures are `make_chapter_spec`,
  `make_working_tree_spec`, `build_tree`, `concatenate`, `compile_probe`,
  `phase_names`, `phase_state_tree`, `baseline_tree`, `coherent_oracle_cases`,
  `incoherent_variant_names`, `incoherent_tree`, `done_flag_permutation_names`,
  `done_flag_tree`, `check_corpus`, and `corpus_invariant_names`.
- **Spec types via the existing carve-out.** A test annotation that needs a
  spec type uses the **existing** `TYPE_CHECKING` carve-out described above
  verbatim — `from conftest import WorkingTreeSpec` (or `ChapterSpec`) under
  `if TYPE_CHECKING:`. `conftest` makes this form available by re-exporting the
  two types inside its own `TYPE_CHECKING` block, so no new import-contract
  clause and no new sanctioned module is introduced.

The `corpus_check` oracle is a corpus-internal cross-check, not the canonical
validator: roadmap task 2.1.2 implements the real §5.2 validator and asserts it
agrees with the corpus labels by keying on the same `CORPUS_INVARIANT_NAMES`
strings.

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

The typed, read-only model of `state.toml` lives in the
`novel_ralph_skill.state` package (design §5.1). `Phase` is the closed,
eleven-member lifecycle enum (`premise` … `done`); `State` and its sub-shapes
(`NovelMeta`, `PhaseState`, `ChapterEntry`, `Drafting`, `Gates`, `WordCounts`,
`PendingTurn`, and friends) are frozen, slotted dataclasses mirroring the
`state.toml` tables. `parse_state(mapping)` constructs a `State` from a decoded
mapping at the boundary, and `load_state(path)` is the thin `tomllib`-backed
file convenience; both are pure structural parses that resolve phase strings to
`Phase` members and coerce TOML arrays to tuples without enforcing the §5.2
invariants. Later slice-1 commands import this package: the `novel-state check`
validator (task 2.1.2) layers the invariants over `parse_state`, and the
`tomlkit` round-trip writer (task 2.2.1) is the matching mutator seam, described
next.

### Invariant validation (`novel-state check`)

`novel_ralph_skill.state.validate_state` is the §5.2 **pure-state** validator
behind `novel-state check` (task 2.1.2). It is a pure
`State -> tuple[Violation, ...]`: it decides whether a parsed `State` contradicts
*itself*, reading nothing from disk beyond the `state.toml` that produced the
`State`. It owns eight invariant names — `phase-in-enum`, `completed-prefix`,
`by-chapter-sum`, `consecutive-clean-within-target`,
`convergence-target-at-least-one`, `consecutive-clean-within-drafted`,
`cursor-coherent`, and `gate-ratio-consistent` — spelled exactly as the corpus
oracle's `CORPUS_INVARIANT_NAMES`, so task 2.1.3's cross-check keys on one
vocabulary; the constants live in the production module and a test pins their
equality to the oracle. Design §5.2 invariant 4 is split into three named
sub-rules (`consecutive-clean-within-target`, `convergence-target-at-least-one`,
and `consecutive-clean-within-drafted`) so a verdict pins exactly the sub-rule it
breaks. The four §5.4 **disk-evidence** invariants (`manifest-disk-bijection`,
`done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`)
need `working/` contents beyond `state.toml` and are task 2.3.2's; `validate_state`
never emits them, and a scope-boundary test pins that.

Two readings are deliberate pure-state approximations, recorded so a later reader
does not mistake them for bugs. The `gate-ratio-consistent` numerator is the
**drafted total** `sum(word_counts.by_chapter.values())`, not `current`, matching
the oracle and decoupling gate consistency (invariant 7) from the by-chapter sum
(invariant 3); the predicate also short-circuits when `word_counts.target <= 0`
rather than dividing, so `validate_state` is total over every constructible
`State`. The `consecutive-clean-within-drafted` ceiling counts the
`word_counts.by_chapter` entries with a positive drafted total as the pure-state
proxy for the design's "chapters drafted" disk quantity (mirroring the oracle,
which counts chapters whose `draft_words > 0`); the two agree on every corpus
tree, and reconciling the proxy against a live draft count is task 2.1.3's
on-disk cross-check.

`novel-state check` is the first command to drive the shared `run` path: its
entry point pre-parses the single `--human` flag off argv before `run` (so the
flag is honoured even on the body-less usage and state-error paths), and it reads
its state from the fixed cwd-relative `working/` directory — there is no
`--working-dir` flag. A §5.2 violation returns exit `4` (an actionable finding
the agent adjudicates), naming the breached invariants in `result.violations`; a
missing or unparseable `state.toml` is the separate exit-`3` state-error channel,
and `check` writes nothing (it is a checker). Note that `phase-in-enum` is
enforced one layer *earlier* than the validator: `parse_state` raises constructing
`Phase(current)` on an out-of-enum phase, so such a `state.toml` is rejected at
load (exit `3`) and the validator's `phase-in-enum` predicate only fires for a
`State` constructed directly (as in the property suite), never for one loaded
from disk.

### The `document.py` round-trip writer

The write half of the `state` package lives in
`novel_ralph_skill/state/document.py` (task 2.2.1) and is the seam every later
mutator (`init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`) calls;
it has no CLI of its own. It supplies three disciplines:

- **Lossless round-trip.** `load_document(path)` reads `state.toml` into a
  style-preserving `tomlkit.TOMLDocument`, and `write_document_atomically`
  re-dumps it, so a no-op write is byte-for-byte stable and a surgical value
  edit rewrites only the touched bytes — comments and layout survive (ADR-002).
  `document_to_state(document)` exposes the typed `State` as a *read* view (via
  `parse_state`); the document, never the lossy typed model, is the write
  source.
- **Atomic write.** `write_document_atomically(document, path)` writes a
  temporary file in the target's directory then `Path.replace`s it over the
  target, so a crash before the rename leaves the prior coherent `state.toml`
  intact and no stray temp file (design §3.4).
- **`[pending_turn]` bracket.** The `pending_turn(path, operation=…, paths=…)`
  context manager writes a `[pending_turn]` intent record atomically before
  yielding the document for the caller's artefact work, then clears the record
  and re-writes on a clean exit. On an exception it leaves the populated record
  on disk for the next turn's `reconcile` (design §3.4); this helper owns only
  the producer side. The clean-exit write re-dumps the *yielded, caller-mutated*
  document, so an in-bracket value edit survives. `open_pending_turn` and
  `clear_pending_turn` are the in-place primitives the context manager composes.

The torn-turn recovery flow is covered by the suite's first `pytest-bdd`
behavioural scenario (`tests/features/torn_turn.feature` with steps under
`tests/steps/`); the round-trip and surgical-mutation guarantees are pinned by
Hypothesis properties over a hand-authored, comment-and-layout-bearing fixture.

### The state-layout direct-edit guard

Because direct editing of `state.toml` is eliminated (design §4.1; ADR-002
selects `tomlkit` as the only sanctioned writer), the state-layout skill
reference [`skill/novel-ralph/references/state-layout.md`](../skill/novel-ralph/references/state-layout.md)
must not carry any copy-pasteable recipe that writes `state.toml` outside
`novel-state`. The guard
[`tests/test_state_layout_reference.py`](../tests/test_state_layout_reference.py)
enforces this: it scans the reference's executable code fences
(`python`/`python3`/`py`/`py3`/`pycon`/`sh`/`bash`/`shell`/`console`) for a write
primitive — a known TOML writer (`tomlkit.dump`, `tomli_w`, `.write_text`,
`.write_bytes`, `.writelines`), an `open(` paired with a write-mode literal, a
redirect or heredoc targeting the path, or a backstop `.write(` on the path — and
fails `make test` if one names the state file. It
leaves the atomic-write *prose* (design §3.4 and §5.3) and any `novel-state`
invocation example untouched, so it never flags a read-only `open(…, "rb")`, an
unrelated redirect, or the schema fence. Rewriting the reference prose to point
at the `novel-state` commands remains roadmap task 6.2.3's job; the guard only
keeps a hand-edit recipe from re-entering.

### Rule packs and the loader boundary

A *rule pack* is a versioned TOML file of prose-detection rules that
`desloppify` reads to flag slop without baking the rules into code (design §4.4
and §6.1). Each rule names a regular-expression `pattern`, a `threshold` (the
allowed number of hits), and a counting `basis`; a `per_page` rule additionally
carries a `page_words` page size. The typed, read-only model and its validating
loader live in the `novel_ralph_skill.rulepack` package.

`RuleBasis` is the closed two-member set of counting bases (`manuscript`,
`per_page`); `Rule` and `RulePack` are frozen, slotted dataclasses, with each
`Rule` carrying both the verbatim `pattern` (for reporting) and its compiled
form (so detection never recompiles). The rule pack's `schema_version` is its
own number, independent of the envelope's and `state.toml`'s (design §3.1); the
current version is `RULEPACK_SCHEMA_VERSION` (`1`).

`parse_rulepack(mapping)` is the pure boundary that builds a validated
`RulePack` from a decoded mapping, and `load_rulepack(path)` is the thin
`tomllib`-backed file convenience over it — the same parse-boundary split as
`parse_state`/`load_state`. Unlike `parse_state`, which is a structural-only
parse, the rule-pack loader is a *validating* boundary: it runtime-checks every
field and compiles every pattern at load time, so a malformed pack fails loudly
rather than silently skipping a bad rule. The loader is detect-only (ADR-001):
it validates structure and compiles patterns but never judges prose.

The loader splits its failures into the two exit-code channels `desloppify`
(roadmap task 5.1.2) surfaces. Malformed *pack content* — a bad `schema_version`,
a missing or wrong-typed field, an unknown `basis`, a non-positive `page_words`,
a negative `threshold`, or an uncompilable `pattern` — raises `RulePackError`,
which carries the offending `rule_id` (or `None` for a pack-level fault) and maps
to exit 2, naming the rule. An absent, unreadable, or undecodable pack *file*
raises `RulePackFileError`, which maps to exit 3. The loader itself emits no
envelope and never calls `sys.exit`; exit-code translation is the command body's
job, exactly as for `parse_state`. Task 5.1.2 wires the `desloppify` command on
top of `load_rulepack` and is responsible for catching these two errors (or
extending the runner's `except` chain) to map each to its `ExitCode`.

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
