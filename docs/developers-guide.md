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
shared across the test suite. It exposes the project-root path
(`project_root`), the parsed `pyproject.toml` (`pyproject`), a repo-relative
UTF-8 reader (`read_repo_text`), a TOML-table accessor (`toml_table`), the PEP
508 dependency-name normaliser (`dist_name`, a `(spec) -> str | None` callable
that reduces a requirement string to its bare distribution name), the
one-program cuprum catalogue builder (`single_program_catalogue`), and the
POSIX venv scripts-directory resolver (`venv_scripts_dir`).

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
not reintroduce the fragility the rule guards against: a `TYPE_CHECKING` import
is `False` at runtime, so it creates no runtime cross-module import and cannot
fail under any pytest import mode. It conveys a type only, never a fixture or
helper *value*; fixtures are still consumed by parameter name. The prohibition
on importing fixture or helper values, and on reaching into another module's
private symbols, is unchanged. The variadic fixture's return type is expressed
as a named `typing.Protocol` defined inside the `TYPE_CHECKING` block of
`tests/conftest.py`, rather than as `Callable[..., str]`, because the `...`
wildcard disables per-call argument-shape checking.

`tests/conftest.py` is inside `$(PYTHON_TARGETS)`, so it is subject to the full
Ruff lint and format, 100% `interrogate` docstring coverage, Pylint, and `ty`
typecheck gates — unlike `test_*.py`, it gains no `per-file-ignores` relief, so
it carries a module docstring, a docstring on every fixture, and no bare
`assert` (guards raise `AssertionError` directly). This consolidation
discharges the duplication and cross-module-import findings recorded in
[`audit-1.2.1.md`](issues/audit-1.2.1.md),
[`audit-1.2.3.md`](issues/audit-1.2.3.md),
[`audit-1.2.4.md`](issues/audit-1.2.4.md),
[`audit-1.2.5.md`](issues/audit-1.2.5.md),
[`audit-1.2.6.md`](issues/audit-1.2.6.md), and
[`audit-1.2.7.md`](issues/audit-1.2.7.md) (Findings 1-2: the seventh
`pyproject` parse and the divergent dependency-name normaliser, both now folded
onto the shared fixtures).

### The `working/` fixture corpus

The [`working_corpus`](../tests/working_corpus) package (roadmap task 1.3.2) is
the shared on-disk test corpus the slice suites in phases 2-6 consume. It
builds a `working/` directory tree under a test's `tmp_path` for each of the
eleven phase states, for coherent and deliberately incoherent `state.toml`
variants, and for `done.flag` permutations. The corpus is anchored to the
design's authoritative artefacts —
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §5.1 (schema and
phase enum) and §5.2 (invariants), and
[`state-layout.md`](../skill/novel-ralph/references/state-layout.md) (the
on-disk layout) — not to the typed schema (roadmap task 2.1.1) or the §5.2
validator (task 2.1.2), which consume it. It is consumed **unchanged** by
phases 2-6 (the roadmap 1.3.2 success criterion).

The package's public surface is `WorkingTreeSpec` and `ChapterSpec` (the
specification dataclasses), `build_working_tree` (the tree builder),
`concatenate_drafts` with `CORPUS_SEPARATOR` and `GATE_THRESHOLDS` (the §4.3/§9
compile model and the knitting thresholds), `PHASE_STATES` with
`COHERENT_BASELINE` (the eleven coherent phase states and the mid-drafting
baseline), `INCOHERENT_VARIANTS` (one deliberately incoherent variant per §5.2
invariant plus the §5.4 disk and §3.4 torn-turn cases),
`DONE_FLAG_PERMUTATIONS` (coherent `done.flag` patterns), and `corpus_check`
with `CORPUS_INVARIANT_NAMES` (the corpus-local structural oracle and its
stable invariant-name vocabulary).

How the corpus is consumed:

- **By fixture name only.** Later slices consume the corpus through pytest
  fixtures, never by a runtime value import. The fixtures live in the
  registered plugin module
  [`tests/corpus_fixtures.py`](../tests/corpus_fixtures.py) (registered via
  `pytest_plugins` in `conftest`), which is the single runtime importer of
  `working_corpus`. The plugin sits beside `conftest` rather than inside it
  only because the corpus fixture surface would push `conftest` past the
  400-line module cap; for fixture resolution a registered plugin is
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
console-scripts (`pyproject.toml`). `novel-state` (task 2.1.2) and `desloppify`
(task 5.1.2) now drive their real apps; the remaining three are still **stubs**:
each stub is a minimal Cyclopts application defined by the shared `make_stub_app`
factory in
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
asserts the registry and `[project.scripts]` agree, so a rename or dropped
entry point cannot silently drift. Edit a command name there, not in five
places. The JSON envelope, the `--human` switch, and the shared exit-code
helper are deferred to roadmap step 1.3.

### Checker/mutator segregation

Read-only checkers (`novel-done`, `novel-state check`, `wordcount`,
`desloppify`, `novel-compile --check`) write nothing, so the harness can call
them freely. Mutators (`novel-state init`/`set-cursor`/`advance-phase`/
`recount`/`reconcile` and `novel-compile`) are the only commands that touch
`state.toml` or `compiled.md`, and every write is atomic via a temporary file
plus `Path.replace`. Only the *genuinely multi-file* writers (`reconcile` and
`novel-compile`) bracket their writes with a `[pending_turn]` intent record so
a torn multi-file turn is recoverable. The single-file mutators (`init`/
`set-cursor`/`advance-phase`/`recount`) write one file per `Path.replace` and
open **no** `[pending_turn]` bracket — `recount` re-derives only
`[word_counts]` in `state.toml` (design §4.1 line 271), and a recount is named
in design §3.4 lines 240-241 as *one write among several in a turn*, not the
command writing several files; `init` writes `state.toml` *and* `log.md` yet
still uses no bracket because each is a single `Path.replace` write. Keep this
segregation honest: a command that detects a finding must not also repair it.
See design §3.3 and §3.4.

`reconcile` (roadmap task 2.3.2) is the project's **first genuinely multi-file
mutator**: a state-writing repair touches `state.toml` *and* appends a recovery
receipt to `log.md`, so it brackets the pair with a `[pending_turn]` of its
own. It does **not** use the `pending_turn` context manager
(`novel_ralph_skill/state/document.py`), because that manager clears the record
on `__exit__` with no hook to land the `log.md` receipt *before* the clear.
Instead `novel_ralph_skill/commands/_reconcile.py::_run_reconcile_bracket`
drives the lower-level seam manually in a fixed order: (1) `open_pending_turn` +
`write_document_atomically` lands the intent record first; (2) the state edit
(the recount, or the torn-turn clear); (3) the `log.md` receipt is appended; (4)
`clear_pending_turn` + `write_document_atomically` clears the bracket last,
after both the state edit and the receipt are on disk. This is a **deliberate
ordering note against design §3.4 line 237** ("the log entry is appended last
as the receipt"): the receipt is written before the final
bracket-clear-and-`state.toml` write rather than strictly after every artefact,
because §3.4 lines 243-245 also require the record to be cleared *only after*
every artefact is written and verified — and a receipt appended after the clear
would reopen a crash window with state settled, the record gone, and no
receipt. Ordering the receipt as step 3 (before the clear) closes that window:
a crash at any step leaves a populated `operation="reconcile"` record a
subsequent `reconcile` re-derives and finishes, and a completed run leaves a
coherent tree with the receipt on disk. `reconcile` deletes no `working/` file
on any path; a rollback clears the record and leaves the partial artefacts in
place, unreferenced.

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
types, the command-agnostic `parse_global_flags` splitter, and the `run`
wrapper. A new command builds a Cyclopts app, returns a `CommandOutcome` from
its body, and calls `run` rather than calling the app directly. Two
consequences of `run` are load-bearing. First, `run` requires the caller to
build the app with `result_action="return_value"` (plus
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
incoherent `set-cursor` or an out-of-order `advance-phase` — is never exit 1;
it is always exit 3. A command body signals this exit-3 channel by raising
`StateInputError`, which `run` maps to the state-error envelope and exit code;
a missing or unparseable `state.toml` or an absent working directory uses the
same channel.

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
`tomlkit` round-trip writer (task 2.2.1) is the matching mutator seam,
described next.

### Invariant validation (`novel-state check`)

`novel_ralph_skill.state.validate_state` is the §5.2 **pure-state** validator
behind `novel-state check` (task 2.1.2). It is a pure
`State -> tuple[Violation, ...]`: it decides whether a parsed `State`
contradicts *itself*, reading nothing from disk beyond the `state.toml` that
produced the `State`. It owns eight invariant names — `phase-in-enum`,
`completed-prefix`, `by-chapter-sum`, `consecutive-clean-within-target`,
`convergence-target-at-least-one`, `consecutive-clean-within-drafted`,
`cursor-coherent`, and `gate-ratio-consistent` — spelled exactly as the corpus
oracle's `CORPUS_INVARIANT_NAMES`, so task 2.1.3's cross-check keys on one
vocabulary; the constants live in the production module and a test pins their
equality to the oracle. Design §5.2 invariant 4 is split into three named
sub-rules (`consecutive-clean-within-target`,
`convergence-target-at-least-one`, and `consecutive-clean-within-drafted`) so a
verdict pins exactly the sub-rule it breaks. Six **disk-evidence** invariants —
the four §5.4 ones (`manifest-disk-bijection`, `done-flag-without-draft`,
`compiled-matches-drafts`, `pending-turn-cleared`), `cursor-plan-present` (the
scene/beat-plan-presence sub-clause of invariant 6, "zero until plans exist",
added by task 2.1.4), and `word-counts-match-drafts` (the disk-vs-table
per-chapter word-count divergence added by task 2.3.2) — need `working/`
contents beyond `state.toml`. `validate_state` never emits any of them (a
scope-boundary test pins that); task 2.3.2's `check_disk_evidence`
(`novel_ralph_skill/state/disk_evidence.py`) **implements** all six, the §5.4
twin of `validate_state`, and disk-aware `check` unions the two verdicts. The
production `DISK_EVIDENCE_INVARIANT_NAMES` tuple is pinned equal to the corpus
oracle's disk-evidence subset by `test_owned_names_equal_corpus_vocabulary`,
the same shared-vocabulary discipline the pure-state names follow.

The eight owned names map onto the design's seven §5.2 invariants (numbered by
their order in the bullet list) as follows; invariant 4 splits into three
sub-rules and invariant 5 is deferred, which is why the validator owns eight
names but covers seven design invariants:

| §5.2 invariant                     | Owned name(s) / status                                                                                   |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1 (phase in enum)                  | `phase-in-enum`                                                                                          |
| 2 (completed is enum prefix)       | `completed-prefix`                                                                                       |
| 3 (`by_chapter` sums to `current`) | `by-chapter-sum`                                                                                         |
| 4 (`consecutive_clean` bounds)     | `consecutive-clean-within-target`, `convergence-target-at-least-one`, `consecutive-clean-within-drafted` |
| 5 (manifest-disk bijection)        | `manifest-disk-bijection` — deferred to task 2.3.2 (disk evidence)                                       |
| 6 (cursor coherent)                | `cursor-coherent`                                                                                        |
| 7 (gate ratio consistent)          | `gate-ratio-consistent`                                                                                  |

Two readings are deliberate pure-state approximations, recorded so a later
reader does not mistake them for bugs. The `gate-ratio-consistent` numerator is
the **drafted total** `sum(word_counts.by_chapter.values())`, not `current`,
matching the oracle and decoupling gate consistency (invariant 7) from the
by-chapter sum (invariant 3); the predicate also short-circuits when
`word_counts.target <= 0` rather than dividing, so `validate_state` is total
over every constructible `State`. The `consecutive-clean-within-drafted`
ceiling counts the `word_counts.by_chapter` entries with a positive drafted
total as the pure-state proxy for the design's "chapters drafted" disk quantity
(mirroring the oracle, which counts chapters whose `draft_words > 0`); the two
agree on every corpus tree.

Task 2.1.3 reconciles **both** proxies against a live draft count in
`tests/test_validate_state_live_draft.py::test_live_draft_agreement_over_whole_corpus`.
The live-draft oracle (`working_corpus.live_draft_owned`) recomputes both live
quantities from the on-disk `chapter-NN/draft.md` bodies — the drafted-words
total (the whitespace-split token count of each present draft, summed) and the
drafted-chapters count (the present drafts with a positive token count), both
independent of the `[word_counts]` table — and reconciles `gate-ratio-consistent`
against the live drafted-words ratio and the `consecutive-clean-within-drafted`
ceiling against the live drafted-chapters count. The agreement test asserts that,
restricted to the eight owned names, `validate_state` (reading the table) and the
live-draft oracle (reading the drafts) return the same verdict on every coherent
tree and every incoherent variant — a full-vocabulary cross-check keyed on
`CORPUS_INVARIANT_NAMES`. Both live readings are the design's **honest-draft**
bases (the invariant-7 numerator and the invariant-4c ceiling), so the two
`by_chapter_override` variants that separate the table basis from the draft basis
— `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]` (roadmap
2.1.5) and `["by-chapter-override-under-counts-drafts"]` (roadmap 2.1.6) — are
findings to investigate, not drifts to paper over.
`test_live_draft_discriminates_table_from_drafts` iterates both members from
corpus data through the standard fixture loop (the `divergent_table_tree`
factory), having retired the module-local fixture the 2.1.3 fix round used, and
a `test_live_draft_counts_equal_honest_draft_bases` self-test pins both live
numbers to those bases on every coherent tree. The two members diverge in
opposite directions and so carry asymmetric expected verdicts. The over-counting
tree makes the table over-state both quantities, so the live oracle names
**both** proxies (`gate-ratio-consistent` and `consecutive-clean-within-drafted`)
while the validator names neither. The under-counting tree makes the table
under-state them, and there the live oracle names **only**
`gate-ratio-consistent`: `consecutive-clean-within-drafted` cannot fire on the
live side because an under-counted table chapter count is a *smaller* ceiling than
the live count, so keeping the validator silent forces the `consecutive_clean`
counter within the live count too. The under-counting tree exists specifically to
kill a table-reading mutant of `live_draft_counts` that "mishandles only
over-counts" — a `min(live, table)`-style mutant that returns the element-wise
minimum of the live read and the table read. On the over-counting tree that
minimum is the live read, so the mutant survives; on the under-counting tree it
returns the table read, collapsing the oracle's verdict from
`{gate-ratio-consistent}` to empty and failing the discrimination test. The
over-counting tree alone cannot catch it. The cross-check does **not** "live-
reconcile" `by-chapter-sum` (invariant 3 is table-internal, with no live
analogue, so it reads `sum(by_chapter) == current` from the table) and it does
**not** re-run `validate_state` as the oracle — the other five owned invariants
come from the spec-keyed `corpus_check`. The disk-vs-table per-chapter divergence
`by-chapter-sum` cannot see — a table internally consistent but stale against
the drafts — is exactly what task 2.3.2's disk-evidence
`word-counts-match-drafts` detects, comparing the per-chapter `by_chapter`
mapping (over the shared chapter keys, never `current`, so it stays orthogonal
to `by-chapter-sum`) against the recount of the on-disk drafts.

Six of `validate_state`'s structural predicates are **deliberate twins** of the
corpus oracle's same-named predicates in `tests/working_corpus/_oracle.py`.
This duplication is intentional, not an oversight: the oracle is an independent
cross-check and must never import the validator it checks, so each side carries
its own copy of the rule. The two are pinned to agree on every corpus tree by
`tests/test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`;
editing either predicate keeps that contract test as the safety net, and each
module carries a reciprocal cross-reference comment pointing at its twin. Do
not de-duplicate the twins — collapsing them would defeat the cross-check.

`novel-state check` is the first command to drive the shared `run` path: its
entry point pre-parses the single `--human` flag off argv before `run` (so the
flag is honoured even on the body-less usage and state-error paths) using the
shared `parse_global_flags` splitter from the contract package, so every
command pre-parses `--human` through one seam rather than re-implementing it.
It reads its state from the fixed cwd-relative `working/` directory — there is
no `--working-dir` flag. A §5.2 violation returns exit `4` (an actionable
finding the agent adjudicates), naming the breached invariants in
`result.violations`; a missing or unparseable `state.toml` is the separate
exit-`3` state-error channel, and `check` writes nothing (it is a checker).
Note that `phase-in-enum` is enforced one layer *earlier* than the validator:
`parse_state` raises constructing `Phase(current)` on an out-of-enum phase, so
such a `state.toml` is rejected at load (exit `3`) and the validator's
`phase-in-enum` predicate only fires for a `State` constructed directly (as in
the property suite), never for one loaded from disk.

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
  the producer side. The clean-exit write re-dumps the *yielded,
  caller-mutated* document, so an in-bracket value edit survives.
  `open_pending_turn` and `clear_pending_turn` are the in-place primitives the
  context manager composes.

The torn-turn recovery flow is covered by the suite's first `pytest-bdd`
behavioural scenario (`tests/features/torn_turn.feature` with steps under
`tests/steps/`); the round-trip and surgical-mutation guarantees are pinned by
Hypothesis properties over a hand-authored, comment-and-layout-bearing fixture.

### State mutators (`init`, `set-cursor`, `advance-phase`)

The three state-mutating subcommands of `novel-state` (task 2.2.2; design §4.1)
are the first commands that *write* `state.toml`. `init` lives in
`commands/novel_state.py` beside `check`; `set-cursor` and `advance-phase` live
in the sibling `commands/_state_mutators.py` so the command module stays within
the 400-line cap once all three bodies land. Three disciplines bind every
mutator:

- **Validate before persist.** Each mutator edits the live `tomlkit` document,
  derives the typed `State` *read* view through `document_to_state`, applies
  the §5.2 `validate_state`, and writes atomically only when the proposed state
  is coherent. A refused request performs **no write**, so the prior
  `state.toml` is byte-for-byte unchanged (design §3.4).
- **Refusal is exit `3`, never exit `1`.** An incoherent cursor, a phase skip or
  out-of-order completion, a terminal advance, an empty-manifest advance into
  `drafting`, or a missing/unparseable/structurally-incomplete `state.toml` is
  the contract's exit `3` (state error), routed through `StateInputError` —
  never the benign exit `1` the loop continues on (design §3.2). Because the
  exit-`3` `run` arm emits only `messages` (no `result`), a refusal names the
  breached invariant(s) in `messages`.
- **Success `result` is write-shaped, never `check`'s read shape.** A mutator's
  success `result` names *what it changed* and never echoes the `check` query's
  `violations` key (design §3.3; `docs/issues/audit-2.2.2.md` Finding 2).
  `set-cursor` returns `{current_chapter, current_scene, current_beat}` — the
  cursor it set, read back to the on-disk drafting fields without translation;
  `advance-phase` returns `{from, to}` — the transition it made, as the
  `Phase.value` strings. The `from`/`to` keys are *transition labels*, not
  on-disk schema keys: `state.toml` persists `phase.current` plus
  `phase.completed`, never a `[from]`/`[to]` table. `recount` and `reconcile`
  must follow the same write-shaped discipline (the counts or discrepancies
  they wrote), so a later mutator does not copy the checker's vocabulary by
  accident; a cross-subcommand test pins `violations` to `check` alone.
- **The two-helper document load path.** The mutators load through
  `_load_document_or_state_error` → `load_document` (`tomlkit`), **not**
  `_load_or_state_error` → `load_state` (`tomllib`), because they edit the live
  document in place. The typed-view derivation goes through a *second* helper,
  `_state_view_or_state_error` → `document_to_state`. Both route faults to exit
  `3` under the existing `STATE_INPUT_ERRORS` tuple. The second wrap is
  load-bearing: a `state.toml` that is valid TOML but structurally incomplete
  (e.g. `schema_version = 1` alone) passes `load_document` and fails only inside
  `document_to_state`; left unwrapped that fault would exit `1`. The mutators
  never call bare `document_to_state`.

`init` *creates*, it does not overwrite: it refuses with exit `3` when
`working/state.toml` already exists rather than clobbering a live project, then
builds the full required table set (`build_initial_document`), creates the
Initialisation directory skeleton plus an empty `log.md`, and writes
atomically. Each of these mutators writes a single file (`state.toml`, plus
`init`'s `log.md`), already atomic via `Path.replace`, so none opens a
`[pending_turn]` bracket — that belongs to the genuinely multi-file mutators
(`reconcile` and `novel-compile`). `recount` is a single-file mutator too: it
re-derives only `[word_counts]` in `state.toml` (design §4.1 line 271), and
design §3.4 lines 240-241 name a recount as *one write among several in a
turn*, not the command writing several files, so it writes one `Path.replace`
and opens no bracket, exactly like `set-cursor` and `advance-phase`.

`advance-phase` takes no argument and always moves to the immediate successor,
so a phase *skip* cannot be requested. "Refuses out-of-order completion" is
therefore realised **solely** as a prior-state coherence guard: a prior whose
`completed` is not the in-order prefix is refused (a future reader should not
hunt for skip-rejection logic that cannot exist). The behavioural proof is the
`pytest-bdd` scenario `tests/features/advance_phase_refusal.feature`, which
advances the `completed-prefix-gap` corpus tree and asserts exit `3` with the
prior state intact.

`recount` re-derives `[word_counts]` from the chapter drafts so a human never
types a word count by hand (design §4.1). It reads each manifest chapter's
`working/manuscript/chapter-NN/draft.md`, takes the whitespace-split token count
(`len(text.split())`) through the shared `recount_words` helper in the `state`
package, and rewrites `[word_counts].current` and `[word_counts].by_chapter` in
place. `by_chapter` is keyed by the chapter *manifest* (one entry per manifest
chapter, `0` for an absent or empty `draft.md`), written in ascending key order
so a second recount over unchanged drafts is byte-for-byte identical
(idempotence); `current` is the drafted sum `sum(by_chapter.values())`, so §5.2
invariant 3 holds by construction. The success `result` is write-shaped —
`{current, by_chapter}`, the counts it wrote — never the checker's
`violations`. An absent `draft.md` counts as `0`, but an unreadable or
undecodable draft, a missing or structurally-incomplete `state.toml`, or a
recount that would breach a §5.2 invariant each refuses with exit `3` (the
state-error channel) and leaves the prior `state.toml` byte-for-byte intact.
The behavioural proof is the `pytest-bdd` scenario
`tests/features/recount.feature`.

### The state-layout direct-edit guard

Because direct editing of `state.toml` is eliminated (design §4.1; ADR-002
selects `tomlkit` as the only sanctioned writer), no skill markdown file may
carry a copy-pasteable recipe that writes `state.toml` outside `novel-state`.
The guard
[`tests/test_state_layout_reference.py`](../tests/test_state_layout_reference.py)
enforces this: it scans each file's executable code fences (`python`/`python3`/
`py`/`py3`/`pycon`/`sh`/`bash`/`shell`/`console`) for a write primitive — a
known TOML writer (`tomlkit.dump`, `tomli_w`, `.write_text`, `.write_bytes`,
`.writelines`), an `open(` paired with a write-mode literal, a redirect or
heredoc targeting the path, or a backstop `.write(` on the path — and fails
`make test` if one names the state file. It leaves the atomic-write *prose*
(design §3.4 and §5.3) and any `novel-state` invocation example untouched, so
it never flags a read-only `open(…, "rb")`, an unrelated redirect, or the
schema fence. Rewriting the reference prose to point at the `novel-state`
commands remains roadmap task 6.2.3's job; the guard only keeps a hand-edit
recipe from re-entering.

Roadmap task 1.2.8 scoped the guard to `state-layout.md` alone, but other
references such as `done-conditions.md` carry executable fences too and could
grow a hand-edit recipe no single-file guard would catch. Roadmap task 7.3.3
widened it: a shared multi-file driver,
`find_direct_state_write_recipes_in_files` in
[`tests/_state_layout_scanner.py`](../tests/_state_layout_scanner.py), applies
the same per-file detector to every skill markdown file under
`skill/novel-ralph/` (the seven references and `SKILL.md`), with no per-file
duplication. The acceptance-bearing guard
`test_no_skill_reference_carries_direct_write_recipe` discovers the file set by
globbing `skill/novel-ralph/**/*.md`, so adding a new reference needs no change
to the guard.

The `.md` extension is a **gate assumption**, not a passing remark: the
`**/*.md` discovery glob only catches files ending `.md`, so a reference added
with a `.markdown` or `.mdx` extension would slip past the guard silently. All
skill references use `.md` by convention; a non-`.md` skill document is a
review smell until property and extension hardening lands in roadmap task
7.3.4. The companion tripwire `test_discovery_covers_known_skill_files` pins
the known inventory of skill markdown files, so adding or removing a reference
fails that test and forces a human to inspect the new file and confirm the glob
caught it.

### Rule packs and the loader boundary

A *rule pack* is a versioned TOML file of prose-detection rules that
`desloppify` reads to flag slop without baking the rules into code (design §4.4
and §6.1). Each rule names a regular-expression `pattern`, a `threshold` (the
allowed number of hits), and a counting `basis`; a `per_page` rule additionally
carries a `page_words` page size. The typed, read-only model and its validating
loader live in the `novel_ralph_skill.rulepack` package.

A v1 pack is a TOML file carrying a top-level `schema_version` and `pack` name,
followed by one or more `[[rule]]` tables. Each rule names an `id`, a
regular-expression `pattern`, a non-negative `threshold`, and a `basis`; a
`per_page` rule additionally carries a positive `page_words` page size. For
example:

```toml
schema_version = 1
pack = "ai-isms"

# A manuscript-basis rule: zero hits tolerated across the whole manuscript.
[[rule]]
id = "tapestry"
pattern = "\\btapestry\\b"
threshold = 0
basis = "manuscript"

# A per-page-basis rule: up to five hits per 300-word page.
[[rule]]
id = "delve"
pattern = "\\bdelve\\b"
threshold = 5
basis = "per_page"
page_words = 300
```

The v1 key vocabulary is closed. The pack table accepts only `schema_version`,
`pack`, and the `rule` array; each `[[rule]]` accepts only `id`, `pattern`,
`threshold`, `basis`, and `page_words`. The loader enforces these rules
strictly: `schema_version` must equal `1`; `page_words` is required for a
`per_page` rule and rejected on any other basis; rule `id`s must be unique;
`pattern` must compile; and any unknown key — a misspelled `thresold`, say —
is rejected, naming the offending rule (or the pack level), rather than being
silently ignored.

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
(roadmap task 5.1.2) surfaces. Malformed *pack content* — a bad
`schema_version`, a missing or wrong-typed field, an unknown `basis`, a
non-positive `page_words`, a negative `threshold`, or an uncompilable
`pattern` — raises `RulePackError`, which carries the offending `rule_id` (or
`None` for a pack-level fault) and maps to exit 2, naming the rule. An absent,
unreadable, or undecodable pack *file* raises `RulePackFileError`, which maps
to exit 3. The loader itself emits no envelope and never calls `sys.exit`;
exit-code translation is the command body's job, exactly as for `parse_state`.
Task 5.1.2 wires the `desloppify` command on top of `load_rulepack` and is
responsible for catching these two errors (or extending the runner's `except`
chain) to map each to its `ExitCode`.

Task 5.1.2 ships the first rule pack:
[`novel_ralph_skill/rulepack/packs/offenders.toml`](../novel_ralph_skill/rulepack/packs/offenders.toml),
the §6 high-frequency-offender table transcribed one `[[rule]]` per row. It lives
inside the package tree so it travels in the built wheel, and `desloppify`
resolves it through `importlib.resources.files` rather than a relative path, so
the installed console-script finds it. `desloppify` is the detect-only checker
built on `load_rulepack` and the pure `detect(pack, chapters)` aggregation in
[`novel_ralph_skill/rulepack/detect.py`](../novel_ralph_skill/rulepack/detect.py):
it scans each chapter draft line by line (the loader compiles patterns with no
flags, so `.` cannot cross a newline), counts each rule's non-overlapping hits,
and reports a per-rule finding — count, threshold, per-page density, and the
`{chapter, line}` of each match — in the shared envelope's `result`. It maps the
two loader errors to their exit codes in the command body (`RulePackError` → exit
2; `RulePackFileError` → exit 3) rather than extending the shared runner, keeping
the `rulepack` → `contract` coupling out of the shared seam.

## GitHub Actions

The generated repository includes GitHub Actions workflows and local composite
actions under `.github/`.

- `.github/workflows/ci.yml` runs on pushes to `main` and on pull requests. It
  sets up Python 3.13, installs `uv`, validates the generated `Makefile` with
  `mbake`, runs `make build`, `make check-fmt`, `make lint` (Ruff +
  `interrogate` over `$(PYTHON_TARGETS)` + Pylint), `make typecheck`, and
  `make audit`, then delegates coverage generation to the shared coverage
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
