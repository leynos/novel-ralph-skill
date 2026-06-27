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

The installed-binary e2es obtain a built-and-installed `novel`
console-script through the module-scoped `installed_novel_state` fixture, the
sanctioned replacement for the former cross-module
`_build_and_install_novel_state` helper that one e2e module imported from
another (an instance of the value-import the rule below forbids). The fixture
builds a wheel with `uv build --wheel`, installs it into a fresh `uv venv`, and
returns the installed script's absolute path; it is **module-scoped** so the
slow build runs once per consuming module and every test reuses the one
install. It lives in the registered plugin module
[`tests/installed_binary_fixtures.py`](../tests/installed_binary_fixtures.py)
(registered via `pytest_plugins` in `conftest`) rather than in `conftest`
itself, for the same reason the corpus plugin does: hosting it inline would push
`conftest` past the 400-line module cap, and for fixture resolution a
registered plugin is `conftest`-equivalent. Because a module-scoped fixture
cannot request the function-scoped `single_program_catalogue` /
`venv_scripts_dir` (pytest raises `ScopeMismatch`), the plugin inlines their
logic as two private helpers, mirroring `test_ai_isms_e2e.py`'s
`installed_desloppify`. The fixture is POSIX-only per ADR-006; consuming
modules keep their own POSIX skip guard.

[`tests/test_console_scripts_error_arms_e2e.py`](../tests/test_console_scripts_error_arms_e2e.py)
is the home for the installed command-agnostic error-arm proofs: it consumes
the `installed_novel_state` and `single_program_catalogue` fixtures by name to
cross the usage error (exit 2) and the state-or-input error (exit 3) over the
installed `novel` in both output modes, and carries the same `slow` /
`timeout(180)` / POSIX-`skipif` marks as the other installed e2es.

[`tests/test_novel_state_check.py`](../tests/test_novel_state_check.py)'s
`test_installed_novel_state_check_exits_zero` is the installed-boundary
*success*-arm counterpart (roadmap task 6.3.6). It consumes the same
`installed_novel_state`, `single_program_catalogue`, and `baseline_tree`
fixtures by name and pins the full installed exit-0 envelope-skeleton identity
over the wheel for `novel state check`: the six contract keys in
`ENVELOPE_KEY_ORDER`, `schema_version`, `command == "novel state"`, the
`ok`-iff-exit-0 mapping, the resolved-absolute `working_dir`,
`result["violations"] == []`, and `str`-typed `messages` — not merely
`exit_code == 0` and `ok`. It asserts against the same constants the in-process
`tests/cross_command_contract/` identity proof uses, so it is that proof's
installed mirror: deliberately a single tripwire over one representative
command, not a re-run of the command × channel matrix. It was extended in place
rather than split into a new module to avoid a second module-scoped wheel build,
and it carries the same `slow` / `timeout(180)` / POSIX-`skipif` marks as the
other installed e2es. The boundary between the three proofs is therefore: this
test covers the *success* arm, `test_console_scripts_error_arms_e2e.py` covers
the *error* arms (exit 2/3), and `tests/cross_command_contract/` pins the same
skeleton identity *in-process* across all five commands.

The in-process command-drive seam shared by the command-surface matrix and the
cross-command contract suite lives in the registered plugin module
[`tests/contract_drive_support.py`](../tests/contract_drive_support.py) (roadmap
task 6.3.2), again co-located beside `conftest` rather than inside it to keep
`conftest` under the 400-line cap. It owns the `drive` fixture (which drives a
command in-process through the shared `run` seam and captures its exit code and
rendered stdout), the `CommandSpec` identity tuple, the per-cell phase-tree
builder, and the volatile-field redaction guard. Both the matrix module and the
`tests/cross_command_contract/` package consume the `drive` fixture by name and
the pure helpers by importing this plugin module, the sanctioned form for a
`conftest`-equivalent scaffolding module.

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

### The combinatorial command-surface matrix

[`tests/test_command_surface_matrix.py`](../tests/test_command_surface_matrix.py)
(roadmap task 6.2.1) is the single home for the
`command x output-mode x phase` matrix described in
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §2.3. It drives
each of the five **read** surfaces — `novel state check`, `novel done`,
`novel wordcount`, `novel compile --check`, and `novel desloppify` — in-process
through the
shared `run` seam across the eleven coherent `working_corpus` phase states, in
both machine and human output modes. It snapshots the machine-mode envelope per
cell, asserts the `--human` rendering is present (non-empty, names the
command), and carries semantic branch assertions pinned to the verified
per-phase envelopes: the phase-keyed `phase_is_done` clause, the coherent
`novel state check` result, the `novel wordcount` zero-progress versus populated
branches, the `novel compile --check` exit-3/4/0 split, and the
shape-stable-but-value-varying `novel desloppify` report.

Beyond the body-produced envelopes (exit 0/1/4), the matrix also crosses the
two command-agnostic diagnostic arms the shared `run` wrapper stamps before the
body returns a value (design §3.2 and §9): the usage-error arm (exit 2, an
unknown option) and the state-error arm (exit 3, an absent `working/`). Both
are crossed with every read command in both output modes, so the `--human`
selection is proven to reach these body-less envelopes too. The machine-mode
snapshot redacts the `messages` field — the platform- and command-variable datum
— and pins the envelope skeleton (`command`, `ok: false`, `working_dir`, empty
`result`) while the message is asserted by its stable prefix. The state-error
arm's message is now an actionable string that names the current directory and
the `novel state init` remedy (roadmap §6.3.1), so only its cwd tail is volatile;
the usage-error arm still carries a command-variable suggestion suffix.

The matrix deliberately bounds its surface and documents the combinatorial gaps
it carries rather than omitting them silently (design §9): the module
docstring's `Carried gaps` section enumerates the mutator-by-phase
cross-products (covered by their own suites and by tasks 6.2.2/6.2.5), the
exhaustive eleven-phase cross-product for the manifest-sensitive commands
(which collapse to their manifest branches), the incoherent-variant-by-phase
cross-products (covered by the validator suites), and the installed-binary
crossing (the scope of task 6.2.4). Read that docstring before extending the
matrix, so a new cell lands in the covered surface rather than re-proving a gap
another suite owns.

### The cross-command envelope-and-exit-code identity proof

The [`tests/cross_command_contract/`](../tests/cross_command_contract/) package
and its companion feature file
[`tests/features/cross_command_contract.feature`](../tests/features/cross_command_contract.feature)
(roadmap task 6.3.2) are the single home for the cross-command identity proof:
that every one of the five spaced commands — `novel state`, `novel done`,
`novel compile`, `novel desloppify`, and `novel wordcount` — presents the *same*
output contract. The package pins three identity claims. First, the shared
six-field envelope skeleton (`command`, `schema_version`, `ok`, `working_dir`,
`result`, `messages`, in that order) with the contract field types and the
`working_dir` label. These synthetic-`RunContext` suites inject the fixed
`working_dir="working"` constant to pin envelope *shape*; the *production* entry
point (`novel.main`) and the installed-binary e2e instead stamp and assert the
**absolute resolved** `working/` path via the `resolved_working_dir()` accessor,
so a misresolution is visible in the field the harness reads (roadmap §6.3.4).
Second, the `ok`-to-exit-code mapping: `ok` is `true` if
and only if the exit code is 0 — a Hypothesis property over the pure
synthetic-outcome → `run` → envelope surface plus plain parametrised driven-cell
examples. Third, the error-channel shapes: the usage (exit 2) and state (exit 3)
arms share one redacted skeleton across all five commands, and the
actionable-finding (exit 4) skeleton is shared across the three commands that can
reach it. Crucially, the package extends the identity proof to the `novel state`
**mutators** — `init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`,
`set-chapters`, `set-gate`, `complete-final-pass`, `set-fangirl`, and
`set-critic-pass` — whose success and refusal envelopes the matrix above
explicitly carried as a gap. A mutator's success `result` names what it changed,
so its contents are command-specific and snapshotted separately, never asserted
equal across commands; only the *skeleton* and the success/refusal exit-code-to-
`ok` mapping are asserted identical.

This proof is the cross-command *identity* axis, distinct from the matrix's
read-command-by-phase surface: do not duplicate either. Where the matrix asserts
each read command's own shape across the eleven phases, this package asserts the
shapes are *equal across commands* and adds the mutator surface. Like the matrix,
it carries its combinatorial gaps knowingly rather than silently (design §9). The
corpus does not let every command reach every channel: the actionable-finding
(exit 4) channel is constructible only for `novel state check` (an incoherent
tree), `novel compile --check` (a `drafting` tree), and `novel desloppify` (an
em-dash-flood draft), so the `novel done` and `novel wordcount` exit-4 cells are
carried as documented gaps; and the benign-negative (exit 1) channel is
constructible only for `novel done` (the corpus never satisfies its done
predicate), so every other command's exit-1 cell is a carried gap too. The
constructible-cell table lives in `tests/cross_command_contract/_cells.py`; read
the package docstring before extending the suite so a new cell lands on a
reachable channel rather than asserting an unreachable one.

### The per-chapter deterministic-loop scenario

[`tests/features/per_chapter_loop.feature`](../tests/features/per_chapter_loop.feature)
(roadmap task 6.2.2) is the end-to-end home for the per-chapter pipeline of
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §7.2 (Figure 3).
Where the command-surface matrix proves each command's envelope per phase in
isolation, this feature proves the deterministic commands **compose**: it drives
`recount`, `novel done`, `novel wordcount`, `novel desloppify`, and
`novel compile --check` as one ordered drive over a real `working_corpus` tree
through the shared command boundary (`run`), exactly as the existing
command-boundary BDD suites do. A clean-pass scenario drives all five read
surfaces over the fully-drafted all-hold tree, and three focused scenarios pin
the §9 deterministic decisions that gate the loop, each over the corpus tree
that exhibits exactly it: a stale compile is caught (`novel done` and
`novel compile --check` both exit 4; §4.2, §4.3, §10); a crossed knitting gate
is reported (`novel wordcount` carries `gate_triggered_30/50/80`; §4.5); and an
out-of-order phase advance is refused (`advance-phase` exits 3 with
`state.toml` byte-for-byte intact; §3.2, §4.1). The steps live under
[`tests/steps/per_chapter_loop_steps.py`](../tests/steps/per_chapter_loop_steps.py)
and bind through the bare, mark-free
[`tests/test_per_chapter_loop_bdd.py`](../tests/test_per_chapter_loop_bdd.py),
so the in-process scenarios run on every platform under the global 30s timeout.

The installed re-drive crosses the real wheel/venv packaging boundary §9 names
as the end-to-end loop scope. It lives in its **own** feature,
[`tests/features/per_chapter_loop_installed.feature`](../tests/features/per_chapter_loop_installed.feature),
re-driving three of the four in-process deterministic decisions through the
installed `novel` console-script over a built wheel (roadmap tasks 6.2.2 and
6.2.9): the clean pass; the **crossed knitting gate**, proven *as part of* the
clean pass via the installed `novel wordcount` gates-crossed assertion
(`gate_triggered_30/ 50/80`; §4.5), not as a standalone scenario; the
stale-compile catch (`novel done` and `novel compile --check` exit 4; §4.2,
§4.3); and — closing the audit-6.2.2 Finding 7 gap — the **refused out-of-order
`advance-phase`** (exit 3 with `state.toml` byte-for-byte intact and no
traceback; §3.2, §4.1, §5.4). This split exists to carry the per-scenario
marks: an installed BDD scenario that needs `@pytest.mark.slow`,
`@pytest.mark.timeout(180)`, and a POSIX `@pytest.mark.skipif` must live in its
own feature and `@scenario`-decorated binder
([`tests/test_per_chapter_loop_installed_bdd.py`](../tests/test_per_chapter_loop_installed_bdd.py)),
because the repo has no per-scenario Gherkin-tag marking idiom and a co-housed
module-level `pytestmark` POSIX skip would wrongly skip the cross-platform
in-process scenarios. A `@scenario`-decorated function "behaves like a normal
test function" (pytest-bdd 8.1.0), so the stacked marks attach as on a plain
pytest test — the same mechanism the installed e2es
([`tests/test_console_scripts_e2e.py`](../tests/test_console_scripts_e2e.py), [`tests/test_recount_e2e.py`](../tests/test_recount_e2e.py))
use. A single wheel-free, parametrized `test_installed_scenario_carries_marks`
guard covers every installed scenario — one `pytest.param` per bound function,
each keeping the scenario named in the test id — and asserts the bound item
keeps those three marks, so a future edit that drops one fails a named test
rather than silently weakening the installed boundary. Adding an installed BDD
scenario is therefore a one-line `pytest.param` append to that guard, not a new
cloned guard; follow this convention.

The installed step definitions
([`tests/steps/per_chapter_loop_installed_steps.py`](../tests/steps/per_chapter_loop_installed_steps.py))
keep only the `@given`/`@when`/`@then` bodies; the run/build seam they drive —
the `_Installed` capture record, the `_run_installed_argv`/`_run_installed` run
helpers, `_build_installed`, and the `_result`/`_assert_no_traceback`
accessors — lives in the sibling support module
[`tests/steps/per_chapter_loop_installed_support.py`](../tests/steps/per_chapter_loop_installed_support.py),
split out so the step module stays under the 400-line cap as installed arms land.
`_run_installed_argv` is a **sanctioned command/query hybrid**: it both writes
`installed.captures[capture_key]` (the command) and returns the
`(exit_code, envelope, stderr)` tuple (the query). The hybrid is a deliberate
test-helper exception to the usual command-query separation, because the `When`
steps want only the capture side effect while `_run_installed` wants the return;
the single-write contract is enforced structurally by an assertion that the
`capture_key` is not already present, so a copied `When` step that re-added a
manual `captures[...] =` assignment fails loudly rather than double-writing. A
`When` step should call it for its side effect alone and never re-assign the
capture by hand.

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
The deterministic spine is the single `novel` multiplexer — a `state` subgroup
and four leaf verbs; the model supplies judgement.
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

### The deterministic commands

The spine is the single `novel` multiplexer in `novel_ralph_skill`: a `state`
subgroup plus four leaf verbs (the rationale is in
[adr-007-command-surface-novel-multiplexer.md](adr-007-command-surface-novel-multiplexer.md),
which supersedes ADR 005, with distribution in
[adr-004-distribution-console-scripts.md](adr-004-distribution-console-scripts.md)):

- `novel state` — the only path that mutates `state.toml`. Subcommands
  `init`, `set-cursor`, `advance-phase`, `recount`, `set-chapters`, `set-gate`,
  `complete-final-pass`, `set-fangirl`, and `set-critic-pass` are mutators;
  `check` is a read-only checker that reports divergence from disk and exits 4;
  `reconcile` is the mutator that writes the disk-authoritative reconciliation
  `check` reports. `set-chapters` populates the `[chapters]` manifest from the
  agent's plan and creates the chapter directories (roadmap 2.2.3; ADR 008).
  The four gate/drafting mutators set the knitting and final-pass gate flags,
  the critic pass, and the fangirl last-chapter-passed (roadmap 2.2.4; ADR
  010): they live in `_gate_drafting_mutators.py` and are wired on by its
  `register_gate_drafting_commands(app)` registrar, the established way to add
  subcommands without growing `novel_state.py` past the 400-line cap.
  `set-gate` is the repair mutator for a knitting gate that lags its drafted
  ratio — it can only assert the ratio-mandated value, refusing a contradicting
  flip with exit 3; `set-fangirl` and `set-critic-pass` carry write-time
  preconditions the §5.2 validator does not own (ADR 010). See design §4.1,
  §5.1, and §5.4.
- `novel done` — the done predicate as code, evaluated per clause against
  disk. See design §4.2.
- `novel compile` — regenerates `working/manuscript/compiled.md`
  deterministically in chapter-index order (the write path, roadmap task 4.1.1);
  `novel compile --check` is the read-only divergence checker (roadmap task
  4.1.2), which writes nothing and exits `4` when `compiled.md` is stale or
  absent. See design §4.3.
- `novel desloppify` — detects and reports prose tics from a versioned rule
  pack, never editing. See design §4.4 and §6.
- `novel wordcount` — a read-only checker reporting per-chapter and cumulative
  counts and the next gate distance. See design §4.5.

The package ships a single `[project.scripts]` entry — `novel` — that
dispatches to the `state` subgroup and the four leaf verbs (`pyproject.toml`;
ADR 007). Each operation drives its real app. The build-and-install proof lives
in [`tests/test_console_scripts_e2e.py`](../tests/test_console_scripts_e2e.py),
which runs on POSIX only (see
[adr-006-console-scripts-e2e-posix-policy.md](adr-006-console-scripts-e2e-posix-policy.md)),
and [`tests/test_pyproject_scripts.py`](../tests/test_pyproject_scripts.py)
guards the entry-point table. The spaced subcommand names live once, as data, in
a single registry,
[`novel_ralph_skill/commands/names.py`](../novel_ralph_skill/commands/names.py):
`SUBCOMMAND_NAMES` is the spaced `novel <verb>` names and `project_scripts_table`
derives the single `novel` entry from it. The dispatcher and every test derive
their names from this registry, and
[`tests/test_command_names_registry.py`](../tests/test_command_names_registry.py)
asserts the registry and `[project.scripts]` agree, so a rename or dropped entry
point cannot silently drift. Edit a command name there, not inline. The JSON
envelope, the `--human` switch, and the shared exit-code helper are owned by the
shared contract scaffolding (roadmap step 1.3).

### The `novel` multiplexer

[adr-007-command-surface-novel-multiplexer.md](adr-007-command-surface-novel-multiplexer.md)
(superseding ADR 005) fixes the command surface as a single `novel`
multiplexer — `novel state …`, `novel done`, `novel compile`,
`novel desloppify`, and `novel wordcount`.
[`novel_ralph_skill/commands/novel.py`](../novel_ralph_skill/commands/novel.py)
builds a parent contract app via `make_contract_app("novel")` and mounts each
operation's existing `build_app` as a sub-app
(`app.command(novel_state.build_app(), name="state")`, and likewise for the
four leaf verbs). The multiplexer is a **pure dispatch layer**: it adds no
command logic, reuses each `build_app` unchanged, and emits the same envelope
and exit codes each mounted leaf produces. Mounting copies only the child's
group and version defaults — never its contract flags — so each mounted leaf
keeps its four-flag contract and the parent returns the leaf body's
`CommandOutcome` to the shared `run` wrapper unchanged (verified against the
locked Cyclopts 4.18.0).

The `novel` `main` entry point splits `--human` off `sys.argv` first (so `run`
stamps the human selection even on the body-less usage and state-error arms),
then derives the spaced command name from the residual argv through
`_command_name_for` before driving the parent through `run` once. The name
derivation consults the registry, not inline literals: `names.py` carries
`SUBCOMMAND_NAMES` (the spaced `novel <verb>` names) and the
`ENVELOPE_COMMAND_NAMES` superset (those spaced names plus the bare `"novel"`
the body-less help and version arms stamp); `build_envelope` validates `command`
against that superset, so every name the multiplexer stamps validates. The
dispatch proof lives in
[`tests/test_multiplexer_dispatch.py`](../tests/test_multiplexer_dispatch.py)
(the multiplexer shape, the four-flag contract tripwire, and the name mapping)
and
[`tests/test_multiplexer_behaviour.py`](../tests/test_multiplexer_behaviour.py)
(in-process envelope equality between the multiplexer arm and each operation's
direct `build_app` over the corpus, across every exit arm), sharing the `driver`
fixture from the registered plugin
[`tests/multiplexer_support.py`](../tests/multiplexer_support.py).

### Checker/mutator segregation

Read-only checkers (`novel done`, `novel state check`, `novel wordcount`,
`novel desloppify`, `novel compile --check`) write nothing, so the harness can
call them freely. Mutators (`novel state` `init`/`set-cursor`/`advance-phase`/
`recount`/`reconcile`/`set-chapters`/`set-gate`/`complete-final-pass`/
`set-fangirl`/`set-critic-pass` and `novel compile`) are the only commands that
touch `state.toml` or `compiled.md`, and every write is atomic via a temporary
file plus `Path.replace`. The *genuinely multi-file* writers — `reconcile` and
`set-chapters` — bracket their writes with a `[pending_turn]` intent record so
a torn multi-file turn is recoverable. The single-file mutators (`init`/
`set-cursor`/ `advance-phase`/`recount`/`set-gate`/`complete-final-pass`/
`set-fangirl`/`set-critic-pass`/`novel compile`) write one file per
`Path.replace` and open **no** `[pending_turn]` bracket — `recount` re-derives
only `[word_counts]` in `state.toml` (design §4.1 line 271), and a recount is
named in design §3.4 lines 240-241 as *one write among several in a turn*, not
the command writing several files; `novel compile` writes only
`working/manuscript/compiled.md`, one `Path.replace` (design §4.3, §3.4);
`init` writes `state.toml` *and* `log.md` yet still uses no bracket because
each is a single `Path.replace` write. Keep this segregation honest: a command
that detects a finding must not also repair it. See design §3.3 and §3.4.

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

`set-chapters` (roadmap task 2.2.3; ADR 008) is the second genuinely multi-file
mutator: it writes `state.toml`, creates the `working/manuscript/chapter-NN/`
directories, and appends a `log.md` receipt under its own `[pending_turn]`
bracket. Its ordering **deliberately differs** from `reconcile`'s.
`reconcile`'s payload (the recount) is recomputable from disk, so it persists
last; a crash in the window loses nothing the next `reconcile` cannot re-derive.
`set-chapters`'s payload (slug, title, target words) is the agent's
*judgement*, recoverable from nowhere else, so the populated `[chapters]`
manifest is edited into the document and persisted **together with** the
`[pending_turn]` record in the *first* atomic write, before any directory is
created — then the directories are created, the receipt is appended, and the
bracket clears last. Every torn state from the first write onward therefore
carries the full manifest on disk with only empty, manifest-derived directories
outstanding. Those empty directories are recomputable *given the persisted
manifest* — they carry no agent judgement and are wholly derivable from it,
exactly like `log.md` — so `reconcile` COMPLETEs a torn `set-chapters` turn by
creating them. This is the scoped precedence branch in `derive_reconciliation`:
a `set-chapters` `[pending_turn]` whose only fired refuse-class violation is a
`manifest-disk-bijection` fully explained by its missing chapter directories is
classified ahead of the bijection REFUSE; any unexplained break still REFUSEs
(design §5.4; ADR 008).

The chapter `slug` is an **opaque string**: it is stored verbatim and never
seeds a path, because the `chapter-NN/` directory name derives from the chapter
*number*, not the slug. Manifest coherence enforces slug *uniqueness* only;
slug *shape* is the agent's responsibility, mirroring the `[novel].slug` stance
for `init`. The schema docstrings therefore describe the slug as an opaque,
stored-verbatim identifier rather than a "filesystem-safe" one, since nothing
validates that claim (ADR 008).

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
types, the command-agnostic `parse_global_flags` splitter, the
`make_contract_app` factory, and the `run` wrapper. A new command builds its
Cyclopts app with `make_contract_app(name)`, returns a `CommandOutcome` from
its body, and calls `run` rather than calling the app directly. Two
consequences of `run` are load-bearing. First, `run` requires the app to carry
four flags — `result_action="return_value"` plus
`exit_on_error=False, print_error=False, help_on_error=False` — so that `run` —
not Cyclopts — owns every `sys.exit` and envelope emission; without them
Cyclopts's default `result_action` would exit on the body's return value and
pre-empt the success-path envelope. Because this four-flag requirement is
load-bearing, `make_contract_app` is its single enforcement point: every
`build_app()` calls the factory rather than a bare `cyclopts.App`, so a future
sixth command adopts all four flags by calling the factory instead of
re-spelling them, and the structural tripwire
`tests/test_contract_app_centralisation.py` pins that the constructors and
entry points consume it. The per-flag rationale and the construction contract
live in
[adr-003-shared-interface-contract.md](adr-003-shared-interface-contract.md)
Table 3. Second, `run` translates Cyclopts's native exit-`1` usage errors into
the contract's exit `2`.

`build_envelope` validates its `command` argument against
`ENVELOPE_COMMAND_NAMES`, so
`novel_ralph_skill/contract/` imports the registry from
[`novel_ralph_skill/commands/names.py`](../novel_ralph_skill/commands/names.py).
This edge is deliberate, not a layering leak: `names.py` is a leaf
source-of-truth module that holds only the command names as data and
carries no command logic. The shared name registry is therefore a leaf that
both the `contract` layer and the `commands` layer may depend on, exactly so
the names live once and neither layer re-spells them. The contract and command
suites import the registry symbols for the same reason. Keep the
dependency pointed this way: nothing in `commands/names.py` may import from
`contract/`, or the edge would become a genuine cycle.

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
the model can resolve (`novel desloppify` violations, compile divergence, a
reconciliation conflict, a `check` discrepancy). A refused mutator request — an
incoherent `set-cursor` or an out-of-order `advance-phase` — is never exit 1;
it is always exit 3. A command body signals this exit-3 channel by raising
`StateInputError`, which `run` maps to the state-error envelope and exit code;
a missing or unparseable `state.toml` or an absent working directory uses the
same channel.

The exit-3 messages are actionable, never raw OS text. Two sibling formatters in
the dependency-free leaf module `_state_load` own the prose. `_state_input_error`
serves the *state.toml-load* fault (roadmap §6.3.1): a missing `working/` names
the current directory and the `novel state init` remedy, while a
present-but-corrupt `state.toml` names the path and asks for inspection or repair.
`_draft_read_error` serves the six *draft-read* boundaries (roadmap §6.3.5) —
`novel state check`'s disk-evidence read, `novel state recount`, `novel
wordcount`, `novel done`, `novel desloppify`, and both of `novel compile`'s
draft-read tails — when a present `working/` tree holds a corrupt or unreadable
`draft.md`/`compiled.md`; it names the `working/` tree and asks for inspection or
repair, never advising `init` (the tree exists). Routing every boundary through
one formatter keeps the message from drifting and leaks no raw `Errno`, `{exc}`
repr, or traceback. The mutator view-derivation boundary
(`_state_view_or_state_error`) is a *state-document* fault, not a draft fault, so
it reuses `_state_input_error`'s present-but-corrupt arm — naming the `state.toml`
path — rather than the draft-read formatter, keeping the two faults distinct
(roadmap §6.3.5). The `novel compile` atomic-*write* tail and the desloppify
rule-pack/device-ledger faults keep their own write- and file-shaped messages.

### State and on-disk layout

`state.toml` is the single source of truth for cursor, phase, gates, word
counts, and the chapter manifest; it is mutated only through `novel state` and
round-trips losslessly with `tomlkit` to preserve comments and formatting
(rationale in
[adr-002-toml-round-trip-tomlkit.md](adr-002-toml-round-trip-tomlkit.md)).
Manuscript content lives under `working/manuscript/` (`compiled.md` and
per-chapter `chapter-NN/{draft.md,done.flag}`), with planning artefacts under
`working/plan/`. The `novel compile` **write** path (roadmap task 4.1.1)
regenerates `compiled.md` by reusing the single production join rule —
`compile_model.concatenate_drafts` over `present_draft_bodies`, the same read
rule the `compiled-matches-drafts` disk-evidence invariant recomputes — so a
freshly compiled tree is coherent under `novel state check` by construction.
The *comparison* against that join rule is shared too, not just the join:
roadmap task 3.1.3 factored "does `compiled.md` equal the ordered draft
concatenation?" into the one helper `compile_model.compiled_matches_drafts`
(see the done predicate section below), so the detector and the
`compile_consistent` clause recompute the verdict at a single site. Both the
`novel compile --check` divergence flag (roadmap task 4.1.2) and the
`novel done` `compile_consistent` clause now call that one routine,
`compile_model.compiled_matches_drafts` — a direct byte comparison, not a
digest, so no `hashlib` is involved despite the historical "compile-and-hash"
naming. They cannot disagree about whether `compiled.md` is stale.
`novel compile --check` projects the verdict to the same polarity the
`compile_consistent` clause uses: only `MATCHES` is satisfied (exit `0`), so an
absent or stale `compiled.md` is exit `4`. This is the **opposite** absent-file
polarity to the §5.4 `novel state check` detector
(`_check_compiled_matches_drafts`), which treats an absent `compiled.md` as
vacuously satisfied; the two polarities are correct for their different jobs
and are reconciled inside the one shared helper.

The typed, read-only model of `state.toml` lives in the
`novel_ralph_skill.state` package (design §5.1). `Phase` is the closed,
eleven-member lifecycle enum (`premise` … `done`); `State` and its sub-shapes
(`NovelMeta`, `PhaseState`, `ChapterEntry`, `Drafting`, `Gates`, `WordCounts`,
`PendingTurn`, and friends) are frozen, slotted dataclasses mirroring the
`state.toml` tables. `parse_state(mapping)` constructs a `State` from a decoded
mapping at the boundary, and `load_state(path)` is the thin `tomllib`-backed
file convenience; both are pure structural parses that resolve phase strings to
`Phase` members and coerce TOML arrays to tuples without enforcing the §5.2
invariants. Later slice-1 commands import this package: the `novel state check`
validator (task 2.1.2) layers the invariants over `parse_state`, and the
`tomlkit` round-trip writer (task 2.2.1) is the matching mutator seam,
described next.

### Invariant validation (`novel state check`)

`novel_ralph_skill.state.validate_state` is the §5.2 **pure-state** validator
behind `novel state check` (task 2.1.2). It is a pure
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
verdict pins exactly the sub-rule it breaks. Eight **disk-evidence** invariants
— the four §5.4 ones (`manifest-disk-bijection`, `done-flag-without-draft`,
`compiled-matches-drafts`, `pending-turn-cleared`), `cursor-plan-present` (the
scene/beat-plan-presence sub-clause of invariant 6, "zero until plans exist",
added by task 2.1.4), `word-counts-match-drafts` (the disk-vs-table per-chapter
word-count *value* divergence added by task 2.3.2), `log-present` (the
partial-`init` bootstrap detector — `log.md` absent while `state.toml` is
present — added by task 2.3.4), and `word-counts-cover-drafts` (the
`[word_counts].by_chapter` *key-set* coverage divergence added by task 2.3.6) —
need `working/` contents beyond `state.toml`. `validate_state` never emits any
of them (a scope-boundary test pins that); task 2.3.2's `check_disk_evidence`
(`novel_ralph_skill/state/disk_evidence.py`) **implements** all eight, the §5.4
twin of `validate_state`, and disk-aware `check` unions the two verdicts. The
production `DISK_EVIDENCE_INVARIANT_NAMES` tuple is pinned equal to the corpus
oracle's disk-evidence subset by
`test_owned_disk_evidence_names_equal_corpus_subset`, the same
shared-vocabulary discipline the pure-state names follow.

The eight owned names map onto the design's seven §5.2 invariants (numbered by
their order in the bullet list) as follows; invariant 4 splits into three
sub-rules and invariant 5 is disk-evidence (owned by `check_disk_evidence`, not
the pure-state validator), which is why the validator owns eight names but
covers seven design invariants:

| §5.2 invariant                     | Owned name(s) / status                                                                                   |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1 (phase in enum)                  | `phase-in-enum`                                                                                          |
| 2 (completed is enum prefix)       | `completed-prefix`                                                                                       |
| 3 (`by_chapter` sums to `current`) | `by-chapter-sum`                                                                                         |
| 4 (`consecutive_clean` bounds)     | `consecutive-clean-within-target`, `convergence-target-at-least-one`, `consecutive-clean-within-drafted` |
| 5 (manifest-disk bijection)        | `manifest-disk-bijection` — disk-evidence (`check_disk_evidence`); **relaxed during drafting** (ADR 009) |
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

#### The recount-gate coupling

`recount` re-derives `[word_counts]` from the on-disk chapter drafts and writes
*only* that table — it never writes `[gates]`. This is deliberate: disk does
not store the "knitting pass integrated" fact, so the harness cannot synthesise
it. A `recount` that would move the drafted ratio across a 30/50/80%
knitting-gate threshold while the matching gate flag still lags would therefore
make the recounted state breach `gate-ratio-consistent`, and the
validate-before-persist guard (`_refuse_if_incoherent`) refuses the write with
exit `3`, leaving `state.toml` byte-for-byte intact (design §4.1, §5.4 recovery
rule 1: "a done-claim large enough to move a gate is reported and escalated,
not silently re-projected").

The refusal is **actionable**. The pure validator's `Violation.detail` stays a
CLI-agnostic *description* of the breach (which gate, which threshold, which
direction — the checker/mutator split, design §3.3), while the command layer
adds the operator remedy through `_refuse_if_incoherent`'s `remedy` keyword:
`recount` passes `_gate_ratio_remedy`, a pure function that emits one advice
line per disagreeing gate. The **upward** line (a recount crosses a threshold
while the gate is `false`) names the crossed threshold and points at
`novel state set-gate --knitting-NN` as the repair once the pending knitting
pass is integrated and logged. The **downward** line (a recount leaves drafting
below a threshold while the gate is recorded `true`) deliberately omits that
verb — nothing was crossed upward, so prescribing the repair would corrupt the
gate-integration record; instead it asks the operator to adjudicate (restore
the drafts or clear the gate) and re-derive. Both directions forbid a hand-edit
of `[gates]`, consistent with `set-gate` being the only repair mutator for a
knitting gate that lags its ratio (see the `set-gate` "repair mutator" note
above). Two pytest-bdd scenarios and two installed-binary e2e tests prove the
dual-direction message at the user-visible level (roadmap 2.3.7).

Task 2.1.3 reconciles **both** proxies against a live draft count in
`tests/test_validate_state_live_draft.py::test_live_draft_agreement_over_whole_corpus`.
The live-draft oracle (`working_corpus.live_draft_owned`) recomputes both live
quantities from the on-disk `chapter-NN/draft.md` bodies — the drafted-words
total (the whitespace-split token count of each present draft, summed) and the
drafted-chapters count (the present drafts with a positive token count), both
independent of the `[word_counts]` table — and reconciles
`gate-ratio-consistent` against the live drafted-words ratio and the
`consecutive-clean-within-drafted` ceiling against the live drafted-chapters
count. The agreement test asserts that, restricted to the eight owned names,
`validate_state` (reading the table) and the live-draft oracle (reading the
drafts) return the same verdict on every coherent tree and every incoherent
variant — a full-vocabulary cross-check keyed on `CORPUS_INVARIANT_NAMES`. Both
live readings are the design's **honest-draft** bases (the invariant-7
numerator and the invariant-4c ceiling), so the two `by_chapter_override`
variants that separate the table basis from the draft basis —
`DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]` (roadmap
2.1.5) and `["by-chapter-override-under-counts-drafts"]` (roadmap 2.1.6) — are
findings to investigate, not drifts to paper over.
`test_live_draft_discriminates_table_from_drafts` iterates both members from
corpus data through the standard fixture loop (the `divergent_table_tree`
factory), having retired the module-local fixture the 2.1.3 fix round used, and
a `test_live_draft_counts_equal_honest_draft_bases` self-test pins both live
numbers to those bases on every coherent tree. The two members diverge in
opposite directions and so carry asymmetric expected verdicts. The
over-counting tree makes the table over-state both quantities, so the live
oracle names **both** proxies (`gate-ratio-consistent` and
`consecutive-clean-within-drafted`) while the validator names neither. The
under-counting tree makes the table under-state them, and there the live oracle
names **only** `gate-ratio-consistent`: `consecutive-clean-within-drafted`
cannot fire on the live side because an under-counted table chapter count is a
*smaller* ceiling than the live count, so keeping the validator silent forces
the `consecutive_clean` counter within the live count too. The under-counting
tree exists specifically to kill a table-reading mutant of `live_draft_counts`
that "mishandles only over-counts" — a `min(live, table)`-style mutant that
returns the element-wise minimum of the live read and the table read. On the
over-counting tree that minimum is the live read, so the mutant survives; on
the under-counting tree it returns the table read, collapsing the oracle's
verdict from `{gate-ratio-consistent}` to empty and failing the discrimination
test. The over-counting tree alone cannot catch it. The cross-check does
**not** "live- reconcile" `by-chapter-sum` (invariant 3 is table-internal, with
no live analogue, so it reads `sum(by_chapter) == current` from the table) and
it does **not** re-run `validate_state` as the oracle — the other five owned
invariants come from the spec-keyed `corpus_check`. The disk-vs-table
per-chapter divergence `by-chapter-sum` cannot see — a table internally
consistent but stale against the drafts — is exactly what task 2.3.2's
disk-evidence `word-counts-match-drafts` detects, comparing the per-chapter
`by_chapter` mapping (over the shared chapter keys, never `current`, so it
stays orthogonal to `by-chapter-sum`) against the recount of the on-disk drafts.

Task 2.3.6 adds `word-counts-cover-drafts`, the orthogonal **key-set coverage**
companion to that **shared-key value** check. The recount keys `by_chapter` by
the manifest (one entry per manifest chapter), so the only way the table's key
set can diverge from the recount — once the manifest and the on-disk chapter
directories agree — is a hand-edited `[word_counts]` table that omits a drafted
manifest chapter's key or carries a key the manifest never declared. The
predicate compares the two key sets (the symmetric difference) and fires on
either direction; `word-counts-match-drafts` owns the shared keys' values and
`word-counts-cover-drafts` owns the symmetric-difference keys, so the two
partition the recount-versus-table comparison. The cover predicate **defers** to
`manifest-disk-bijection` when the manifest and the chapter directories are
not in bijection: the recount keys off the then-untrustworthy manifest, so
without the guard it would double-fire on every structural mismatch. Both
divergence directions are repaired by the same `RECOUNT` that repairs the value
divergence, because a recount re-keys `by_chapter` off the manifest — supplying
any missing key and dropping any orphan key. Two first-class
`INCOHERENT_VARIANTS` exercise the directions
(`word-counts-cover-drafts-omits-drafted-chapter` and
`word-counts-cover-drafts-extra-table-key`); the over- and under-counting
`DIVERGENT_TABLE_VARIANTS` carry both a value gap and a key-count gap, so the
two word-count predicates legitimately co-fire there.

Roadmap task 2.3.8 refines that deferral: it is unconditional only **outside**
a relaxed drafting subset. When the user-facing `check` passes
`relax_drafting_bijection=True`, the phase is drafting, and the break is a
coherent disk-subset-of-manifest, cover-drafts instead re-keys off the on-disk
drafted subset and fires the *missing* direction only (a drafted chapter the
table omits), repaired by a scoped `RECOUNT` pre-arm in `reconcile`. See the
bijection relaxation section below and ADR 009 "Known risks".

Six of `validate_state`'s structural predicates are **deliberate twins** of the
corpus oracle's same-named predicates in `tests/working_corpus/_oracle.py`.
This duplication is intentional, not an oversight: the oracle is an independent
cross-check and must never import the validator it checks, so each side carries
its own copy of the rule. The two are pinned to agree on every corpus tree by
`tests/test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`;
editing either predicate keeps that contract test as the safety net, and each
module carries a reciprocal cross-reference comment pointing at its twin. Do
not de-duplicate the twins — collapsing them would defeat the cross-check.

The corpus oracle's **disk-evidence** predicates follow the same twin
discipline, but against a different production module. After tasks 2.3.2/2.3.3
the oracle reads the materialised `working/` tree for all eight §5.4
disk-evidence invariants (`manifest-disk-bijection`, `done-flag-without-draft`,
`compiled-matches-drafts`, `pending-turn-cleared`, `cursor-plan-present`,
`word-counts-match-drafts`, `log-present`, and `word-counts-cover-drafts`), so
these checks are **disk-vs-disk** twins of production `check_disk_evidence`
(`novel_ralph_skill/state/disk_evidence.py`) — the manuscript-comparing twins
glob `manuscript/chapter-*` and read each `draft.md` from disk, and the
`log-present` twin (added by task 2.3.4 — the partial-`init` bootstrap where
`state.toml` is present but `log.md` is absent) reads `log.md`'s presence on
disk; in every case the cross-check is disk-vs-disk, not against the pure-state
`validate_state` the section above describes. The two disk-reading sides are
pinned to agree on every corpus tree by
`tests/test_novel_state_check_disk.py::test_union_detector_agrees_with_corpus_oracle`,
`tests/test_disk_evidence.py::test_word_counts_twin_equals_corpus_oracle`, and
`::test_word_counts_cover_twin_equals_corpus_oracle`, and the production tuple
`DISK_EVIDENCE_INVARIANT_NAMES` is pinned equal to the oracle's disk-evidence
subset (above). The independence rule is identical: the oracle reimplements the
disk read rather than importing the production detector, so the cross-check
stays genuine. The disk-reading twins live in
`tests/working_corpus/_oracle_disk.py` (split out of `_oracle.py` for the
400-line cap and re-exported through it), colocating the manifest, word-count
value, coverage, and `log.md` checks by feature.

**The drafting bijection relaxation (ADR 009, task 2.1.7).** During drafting
the manifest leads the on-disk directory set — the manifest holds every planned
chapter the instant chapter planning finishes, but only the drafted-so-far
`chapter-NN/` directories need exist — so the exact §5.2 invariant-5 bijection
makes `check` exit `4` for the whole drafting phase. `check_disk_evidence`
takes a keyword-only, default-strict `relax_drafting_bijection` flag: when it
is set and `state.phase.current == drafting`, `manifest-disk-bijection` relaxes
to disk-subset-of-manifest. The predicate splits the break into its two
directions (`orphans = on_disk - manifest`, `missing = manifest - on_disk`)
plus the manifest-contiguity check, and the relaxation suppresses **only** the
`missing`-direction break; an orphan directory or a manifest gap still fires in
every phase, and the exact bijection re-tightens at `final-pass`/`done` where
the §4.3 compile-ordering guarantee requires every planned chapter on disk.
Only the user-facing `check` passes the flag (`_disk_evidence_or_state_error`);
`derive_reconciliation` keeps the strict default, so the torn `set-chapters`
COMPLETE precedence (ADR 008) — whose decisive tree carries `phase=drafting` —
reads the unchanged bijection. The oracle twin
`_oracle_disk._check_manifest_disk_bijection` mirrors the split and the flag,
and a relaxed agreement test pins the relaxed production path to the relaxed
twin alongside the unchanged strict agreement suite.

The relaxation's blast radius is exactly two disk-evidence invariants:
`manifest-disk-bijection` itself, and `word-counts-cover-drafts`. The latter
**re-keys** off the on-disk drafted subset during a relaxed drafting subset
(roadmap task 2.3.8): the same `relax_drafting` flag threads to the
cover-drafts predicate, which — when the phase is drafting and the break is a
coherent subset (`on_disk < manifest`) — fires the *missing* direction only,
flagging a drafted chapter the `by_chapter` table omits. (Originally
cover-drafts simply **deferred** on `manifest != on_disk`, so a subset-tree key
gap went unenforced until the tree returned to bijection; task 2.3.8 closed
that gap — see ADR 009 "Known risks".) `reconcile` repairs it via a scoped,
drafting-gated `RECOUNT` pre-arm that re-keys `by_chapter` off the manifest.
Convergence holds because the manifest-keyed recount writes a `0` key for every
undrafted manifest chapter, so the missing-only detector never re-fires on its
own repair; the symmetric *extra* direction is deliberately not checked on a
relaxed subset for that reason. Outside the relaxed subset (at bijection,
`final-pass`, or `done`) cover-drafts runs the full symmetric-difference
key-set check exactly as before. The remaining six disk-evidence predicates do
not read the manifest⇄disk equality and are unchanged.

`novel state check` is the first command to drive the shared `run` path: its
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

### Done predicate (`novel done`)

`novel done` (roadmap task 3.1.1) is the read-only done predicate as a
subcommand (design §4.2). Its pure engine lives in
`novel_ralph_skill/state/done_predicate.py`, beside `disk_evidence.py` and
parallel to it: a `(State, working_dir) -> DoneClauses` reader with one
predicate per clause, a `chapter-NN` path derivation shared through
`_chapter_dir_name` (imported from `_disk_paths.py`, not from `disk_evidence`),
and the same benign-absent / propagate-everything-else fault boundary — but it
inverts the polarity, returning `True` when a clause *holds*. The command body
and its app live in `novel_ralph_skill/commands/_novel_done.py`, reusing
`novel state`'s `working_dir`, `state_path`, `_load_or_state_error`, and
`STATE_INPUT_ERRORS` seams; its `build_app` is mounted as the `done` leaf of the
`novel` multiplexer and driven through the shared `run` wrapper exactly as the
other leaves are.

**The six clauses and their disk sources.** This table is the authoritative
statement of the clause truth conditions: the clause names are fixed by design
§4.2 and the conditions are implemented in
`novel_ralph_skill/state/done_predicate.py`. The skill prose
(`skill/novel-ralph/references/done-conditions.md` "Novel-level predicate") now
points here rather than restating the clauses.

- `phase_is_done` := `state.phase.current is Phase.DONE`;
- `final_pass_complete` := `state.gates.final.final_pass_complete`;
- `all_chapters_flagged` := every manifest chapter has an on-disk
  `manuscript/chapter-NN/done.flag`;
- `knitting_gates_passed` := the three `state.gates.knitting.done_30/50/80`
  booleans are all true *and* `reviews/knitting-{30,50,80}.md` all exist (the
  `(30, 50, 80)` percentages are taken from one `KNITTING_PERCENTAGES` constant
  shared between the booleans and the file names so they cannot drift);
- `compile_consistent` := `manuscript/compiled.md` is present *and* byte-equal
  to
  the ordered concatenation of the present drafts (the content comparison; see
  below);
- `no_unresolved_blockers` := no manifest chapter's `critic-notes.md` carries an
  unresolved BLOCKER.

**Manifest, not outline.** The chapter set the predicate iterates is the
**manifest** (`state.chapters`), not outline prose. This is design
§4.3-conformant: the manifest is the authoritative chapter set and order, there
is no `parse_chapter_outline` in the codebase, and `novel state check` already
asserts the manifest⇄directory bijection. The skill reference
(`done-conditions.md`) was reconciled to the manifest source by roadmap task
3.1.1.1 and now points at `novel done` for the predicate, so there is no second
chapter-source statement left to diverge.

**The BLOCKER format.** An unresolved BLOCKER is a live `### Bn` finding
heading under the `## BLOCKER` section of a `critic-notes.md` body — the
spiteful critic's strict output format (`critic-personas.md`, "Resolving a
BLOCKER"; roadmap 3.1.5). The recogniser enters the section on a line whose
stripped text equals `## BLOCKER`, leaves it on the next `##`-level heading,
and treats a `### B<digit>` heading inside it as unresolved unless that heading
ends with a single space then the `[resolved]` token. The token is a trailing
marker, so its *position* carries the meaning: an incidental mid-line quotation
(for example a finding label
`### B1 — the ending still depends on the [resolved] issue`) does not clear the
blocker. The convergence sentinel `No BLOCKER. No MAJOR.` writes no
`## BLOCKER` section and is clean by construction, as is an absent
`critic-notes.md`. The rule has documented limitations in *both* directions: a
prose mention without the token stays unresolved (the false-dirty near-miss the
corpus pins); trailing text after the token (for example
`### B1 — label [resolved] (see log)`) is treated as unresolved by design,
because the producer convention forbids it (D-BLOCKER-TRAILING; audit-3.1.4
Finding 2); and case or alternative-spelling variants (`RESOLVED`,
`(resolved)`) are out of scope and stay mis-classified (D-BLOCKER-CASE;
audit-3.1.4 Finding 3). The corpus pins the resolved, near-miss, incidental,
and convergence-sentinel edges, and a BDD scenario drives a live `### B1`
finding to exit 1.

**`compile_consistent` is the full content comparison (roadmap 3.1.2).** The
clause is the single function `compile_consistent(state, working_dir)`: an
absent `compiled.md` is `False`, a present one is `True` iff its bytes equal
the ordered draft concatenation. The verdict is read from the shared production
helper `compile_model.compiled_matches_drafts` (see below), which the §5.4
detector `_check_compiled_matches_drafts` also consumes, so the clause and the
detector cannot disagree on what "compiled matches drafts" means. The
comparison is a direct byte comparison, not a digest (D-BYTE-COMPARE). This
closes the 3.1.1 stale-but-present unsoundness window: a present-but-stale
compile whose header count and word total coincide with the drafts is still
caught, because the comparison is over bytes, not counts.

The clause carries the **opposite** absent-file polarity to that §5.4 detector,
which treats an absent `compiled.md` as *vacuously satisfied* ("nothing to
diverge from"); here an absent compile is *not consistent*. The two polarities
are correct for their different jobs, and both are projections of the one
shared helper.

**One owner for "compiled.md equals the ordered draft concatenation" (roadmap
task 3.1.3).** That comparison lives in a single production helper,
`compile_model.compiled_matches_drafts(state, working_dir) -> CompiledComparison`,
returning the three-valued `ABSENT`/`MATCHES`/`DIVERGES` (audit-3.1.1 Finding
2). Both production callers consume it, each projecting the verdict to its own
absent-file polarity: the §5.4 detector `_check_compiled_matches_drafts` maps
`DIVERGES` to a `Violation` and `ABSENT`/`MATCHES` to none, while the
`compile_consistent` done-clause maps `MATCHES` to `True` and both `ABSENT` and
`DIVERGES` to `False`. A `bool` helper could not serve both, since the detector
must tell an *absent* compile (no violation) from a *present-but-stale* one (a
violation), which a single "present and matching" boolean collapses. The
test-side corpus oracle deliberately keeps its own copy of the comparison (see
the invariant-validation twin policy) and does not import the helper, so a
production bug cannot mask itself.

**The exit-`4` carve-out (the conservative reading).** `novel done` exits `4`
(`ACTIONABLE_FINDING`) **iff** `compile_consistent` is the *sole* false clause
**and** `compiled.md` is present — a stale-present compile the harness can
regenerate (matching `novel compile --check`). The decision lives in the
command body (`_novel_done._sole_stale_compile`), not the pure engine, because
exit codes are the command/contract layer's concern. It is conservative
(D-CARVE): an *absent* sole-failure compile stays exit `1`, because an absent
compile is not a regenerable stale one (this preserves the 3.1.1 B1 soundness
fix). The `compiled.md` `exists()` stat is the read-only mechanism that
distinguishes a stale-present compile from an absent one, since `DoneClauses`
carries only the six booleans and cannot say *why* `compile_consistent` is
false. The human `messages` line names a *stale* compile at exit `4` and a
*missing* one at exit `1` (A-4).

**The fault boundary.** Mirroring `novel wordcount`/`disk_evidence`, an *absent*
on-disk artefact is a benign false clause, but every other read fault
(`PermissionError`, an undecodable `critic-notes.md` or `compiled.md`)
propagates; the command body wraps `evaluate_done` under `STATE_INPUT_ERRORS`
and re-raises `StateInputError`, so a corrupt tree reaches the exit-`3` channel
rather than being swallowed as exit `1` or `4`.

**Oracle twins for the two new disk clauses.** The `knitting_gates_passed`
review-existence read and the `no_unresolved_blockers` BLOCKER scan are
disk-evidence reads, so each gets an independent corpus-side twin in
`tests/working_corpus/_done_predicate_oracle.py` (`reviews_all_present`,
`no_unresolved_blockers`) that re-implements the read without importing the
production predicate; a cross-check test pins each equal to its production
counterpart on every `novel done` corpus tree, exactly as the `_oracle_disk.py`
twins pin `disk_evidence`. The `novel done` corpus specs (the
all-six-clauses-hold tree, the per-clause failers, the `[resolved]`/near-miss
BLOCKER trees) live in `tests/working_corpus/_done_predicate_specs.py`, added
beside `PHASE_STATES`/`COHERENT_BASELINE` without mutating them so every
existing fixture and snapshot stays byte-identical.

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

The torn-turn flow is covered by a family of `pytest-bdd` behavioural scenarios
(features under `tests/features/`, steps under `tests/steps/`) that together span
both halves of the §5.4 reconciliation surface. `torn_turn.feature` pins the
producer side: a bracket that raises mid-turn leaves the `[pending_turn]` intent
record populated on disk. The recovery and rollback dispositions are then
exercised end-to-end through the real command boundary:

- **COMPLETE** — `torn_turn_recovery.feature`: a crashed `reconcile` leaves a
  recoverable torn turn that `check` reports (exit 4) and `reconcile` re-derives
  and finishes under bounded harness re-entry (each run exits 0).
- **never-landed ROLLBACK** — `torn_turn_rollback.feature` (task 6.2.7): a torn
  turn whose declared artefact (a missing `draft.md` body or a missing
  `done.flag`) never landed is reported by `check` and rolled back by `reconcile`
  in a single pass, with a rollback-pending-turn receipt appended to `log.md`.
- **partial-landed ROLLBACK** — a torn turn that left a partial `.tmp` residue,
  unpromoted by `Path.replace` and unreferenced by state, is likewise reported
  by `check` and rolled back by `reconcile`, with the residue preserved
  byte-for-byte on disk. Both unrecoverable triggers are covered: a torn
  `write-draft` turn that left a partial `draft.md` residue
  (`torn_turn_rollback_partial.feature`, task 6.2.12) and a torn `mark-done`
  turn that left a partial `done.flag` residue
  (`torn_turn_rollback_partial_done_flag.feature`, task 6.2.14). Each residue
  lands inside an existing manifest chapter directory so the manifest-disk
  bijection still holds, and the `done.flag` residue uses a non-`done.flag`
  filename so the `done-flag-without-draft` detector never fires — both keep the
  disposition ROLLBACK rather than REFUSE.

The round-trip and surgical-mutation guarantees are pinned by Hypothesis
properties over a hand-authored, comment-and-layout-bearing fixture.

### State mutators (`init`, `set-cursor`, `advance-phase`)

The three state-mutating subcommands of `novel state` (task 2.2.2; design §4.1)
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
  cursor it set, read back to the on-disk drafting fields without translation.
  That `result` echoes the validated *input* arguments rather than re-reading
  the written document; this is a deliberate coupling, not a latent assumption.
  Validation precedes the write (§3.4 above), so the echoed scalars equal the
  persisted `[drafting]` cursor on every success and a diverging write is
  refused before it lands; the cursor is plain scalars the mutator neither
  derives nor normalises, so re-reading the document would add no guarantee. A
  future mutator that *computes* or *normalises* a value before persisting it
  must report the written value, not its input echo. `advance-phase` returns
  `{from, to}` — the transition it made, as the `Phase.value` strings. The
  `from`/`to` keys are *transition labels*, not on-disk schema keys:
  `state.toml` persists `phase.current` plus `phase.completed`, never a `[from]`
  /`[to]` table. `recount` and `reconcile` must follow the same write-shaped
  discipline (the counts or discrepancies they wrote), so a later mutator does
  not copy the checker's vocabulary by accident; a cross-subcommand test pins
  `violations` to `check` alone.
- **The two-helper document load path.** The mutators load through
  `_load_document_or_state_error` → `load_document` (`tomlkit`), **not**
  `_load_or_state_error` → `load_state` (`tomllib`), because they edit the live
  document in place. The typed-view derivation goes through a *second* helper,
  `_state_view_or_state_error` → `document_to_state`. Both route faults to exit
  `3` under the existing `STATE_INPUT_ERRORS` tuple. The second wrap is
  load-bearing: a `state.toml` that is valid TOML but structurally incomplete
  (e.g. `schema_version = 1` alone) passes `load_document` and fails only inside
  `document_to_state`; left unwrapped that fault would exit `1`. The mutators
  never call bare `document_to_state`. The structurally-incomplete fault's exit-3
  message is actionable: `_state_view_or_state_error` routes it through
  `_state_input_error`'s present-but-corrupt arm (roadmap §6.3.5), which names the
  `state.toml` path and advises inspect/repair — the state-document remedy, kept
  distinct from the draft-read formatter because the document, not a draft, is at
  fault.

`init` *creates*, it does not overwrite: it refuses with exit `3` when
`working/state.toml` already exists rather than clobbering a live project, then
builds the full required table set (`build_initial_document`), creates the
Initialisation directory skeleton plus an empty `log.md`, and writes
atomically. Each of these mutators writes a single file (`state.toml`, plus
`init`'s `log.md`), already atomic via `Path.replace`, so none opens a
`[pending_turn]` bracket — that belongs to the genuinely multi-file mutator
`reconcile`. `recount` and `novel compile` are single-file mutators too:
`recount` re-derives only `[word_counts]` in `state.toml` (design §4.1 line
271), and design §3.4 lines 240-241 name a recount as *one write among several
in a turn*, not the command writing several files, so it writes one
`Path.replace` and opens no bracket; `novel compile` (roadmap task 4.1.1)
writes only `working/manuscript/compiled.md` (design §4.3), one `Path.replace`,
likewise with no bracket. Both behave exactly like `set-cursor` and
`advance-phase`.

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
carry a copy-pasteable recipe that writes `state.toml` outside `novel state`.
The guard
[`tests/test_state_layout_reference.py`](../tests/test_state_layout_reference.py)
enforces this: it scans each file's executable code fences (`python`/`python3`/
`py`/`py3`/`pycon`/`sh`/`bash`/`shell`/`console`) for a write primitive — a
known TOML writer (`tomlkit.dump`, `tomli_w`, `.write_text`, `.write_bytes`,
`.writelines`), an `open(` paired with a write-mode literal, a redirect or
heredoc targeting the path, or a backstop `.write(` on the path — and fails
`make test` if one names the state file. It leaves the atomic-write *prose*
(design §3.4 and §5.3) and any `novel state` invocation example untouched, so
it never flags a read-only `open(…, "rb")`, an unrelated redirect, or the
schema fence. Rewriting the reference prose to point at the `novel state`
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

### The state-layout schema-drift guard

The direct-edit guard keeps hand-edit recipes out of the references; a sibling
guard keeps the `## state.toml schema` fence in `state-layout.md` honest about
what `novel state init` actually emits. Beta testing of roadmap task 2.1.8
found the emitted document carrying fields the reference never described, so
[`tests/test_state_layout_schema_guard.py`](../tests/test_state_layout_schema_guard.py)
locks the two together. It derives the required leaf-name and table-header
nets from the **serialised** `build_initial_document(...)` dump
(`tomlkit.dumps(...)`) — the exact textual shape the fence must mirror — and
asserts each emitted leaf appears as a `name =` line and each emitted table
header as a `[header]` line inside the extracted fence. Adding an emitted field
to `init` therefore obliges a matching line in the fence, or the guard fails
`make test`.

Two emitted-versus-fence shape mismatches are deliberate exclusions, both
justified by the design's chosen rendering:

- **`gates`** is a parent-only table carrying no scalar leaf, so `tomlkit.dumps`
  emits no bare `[gates]` line — only `[gates.knitting]` and `[gates.final]`
  (design §5.1). Deriving the header net from the dump excludes `gates` (and
  any future parent-only table) automatically, with no special-case.
- **`chapters`** serialises as the empty leaf line `chapters = []`, but the
  reference documents the *populated* manifest as a `[[chapters]]` block, so
  `chapters` is the one emitted leaf the guard drops from the required-leaf
  set; its sub-fields are checked separately against `ChapterEntry`.

The transient `[pending_turn]` table is **not** covered: `init` never emits it,
so the dump-derived nets structurally cannot require it (the reference
documents it by hand instead — see `state-layout.md` "Pending turn"). The
table-aware, per-occurrence hardening of this guard is deferred to roadmap task
7.30. See design §5.1 and roadmap task 2.1.8.

### Rule packs and the loader boundary

A *rule pack* is a versioned TOML file of prose-detection rules that
`novel desloppify` reads to flag slop without baking the rules into code
(design §4.4 and §6.1). Each rule names a regular-expression `pattern`, a
`threshold` (the allowed number of hits), and a counting `basis`; a `per_page`
rule additionally carries a `page_words` page size. The typed, read-only model
and its validating loader live in the `novel_ralph_skill.rulepack` package.

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
`pattern` must compile; and any unknown key — a misspelled `thresold`, say — is
rejected, naming the offending rule (or the pack level), rather than being
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

The loader splits its failures into the two exit-code channels `novel desloppify`
(roadmap task 5.1.2) surfaces. Malformed *pack content* — a bad
`schema_version`, a missing or wrong-typed field, an unknown `basis`, a
non-positive `page_words`, a negative `threshold`, or an uncompilable
`pattern` — raises `RulePackError`, which carries the offending `rule_id` (or
`None` for a pack-level fault) and maps to exit 2, naming the rule. An absent,
unreadable, or undecodable pack *file* raises `RulePackFileError`, which maps
to exit 3. The loader itself emits no envelope and never calls `sys.exit`;
exit-code translation is the command body's job, exactly as for `parse_state`.
Task 5.1.2 wires the `novel desloppify` command on top of `load_rulepack` and is
responsible for catching these two errors (or extending the runner's `except`
chain) to map each to its `ExitCode`.

Task 5.1.2 ships the first rule pack:
[`novel_ralph_skill/rulepack/packs/offenders.toml`](../novel_ralph_skill/rulepack/packs/offenders.toml),
the §6 high-frequency-offender table transcribed one `[[rule]]` per row. It
lives inside the package tree so it travels in the built wheel, and
`novel desloppify` resolves it through `importlib.resources.files` rather than a
relative path, so the installed console-script finds it. `novel desloppify` is the
detect-only checker built on `load_rulepack` and the pure
`detect(pack, chapters)` aggregation in
[`novel_ralph_skill/rulepack/detect.py`](../novel_ralph_skill/rulepack/detect.py):
it scans each chapter draft line by line (the loader compiles patterns with no
flags, so `.` cannot cross a newline), counts each rule's non-overlapping hits,
and reports a per-rule finding — count, threshold, per-page density, and the
`{chapter, line}` of each match — for every rule. The envelope's
`result.findings` carries only the over-threshold subset of those findings (see
[the clean-pass findings contract](#the-clean-pass-findings-contract-roadmap-task-713)
below). It maps the two loader errors to their exit codes in the command body
(`RulePackError` → exit 2; `RulePackFileError` → exit 3) rather than extending
the shared runner, keeping the `rulepack` → `contract` coupling out of the
shared seam.

#### The clean-pass findings contract (roadmap task 7.1.3)

`result.findings` carries **only the over-threshold findings**. A clean pass
emits `findings: []` and `violations: []` at exit `0`; the detection core still
aggregates a finding for *every* rule, but the envelope projection slims the
trail to the rules that actually breached. This is the authoritative contract:
the design (§3.1, §4.4) and the ledger section below merely reference it.

The rationale is that `result` carries only **machine-actionable** data (design
§3.1): the harness gates on `ok` and reads `result.violations` (§3.3), so a
rule within threshold — by construction `count: 0` or below its limit — is
never read. The full audit trail of passing rules is **recoverable** from data
the operator already owns: the rule pack is versioned, and any non-clean
envelope still lists every offending rule in full. Carrying every passing rule
would also make the payload grow linearly with pack size and pack count, so a
clean multi-pack scan would serialise dozens of `count: 0` rows no consumer
reads; slimming keeps a clean scan at `findings: []` regardless of how many
rules ship.

The decision applies **uniformly** to both the rule-pack path and the
`novel desloppify --ledger` path (see
[the device ledger](#the-device-ledger-and-per-novel-rationing) below), so the
§7.1 packs — `ai-isms.toml`, `device-ledger.toml`, and the future multi-pack
run — all inherit one shape. The multi-pack surface (roadmap tasks 7.1.6 and
7.1.7) inherits this contract; it is settled here once and is not re-litigated
there.

The uniformity is enforced by a single shared helper, not by keeping two
projections in lockstep by hand. `build_finding_outcome`
([`novel_ralph_skill/contract/finding_outcome.py`](../novel_ralph_skill/contract/finding_outcome.py),
roadmap task 7.1.4) is the **single finding-outcome envelope skeleton**: it
filters a report's findings to the failed ones, derives the exit code from that
same `failed` list, and assembles `result` (any path-specific extra keys first,
then `violations`, then the slimmed `findings`) and `messages` (one human line
per failed finding, or a clean-pass note). It lives in the lowest-layer
`contract` package and is generic over an opaque finding type with injected
callables, so it imports neither `rulepack` nor `ledger` and creates no import
cycle. Both `report_outcome`
([`commands/_desloppify_report.py`](../novel_ralph_skill/commands/_desloppify_report.py))
and `ledger_report_outcome`
([`ledger/report.py`](../novel_ralph_skill/ledger/report.py)) route through it,
injecting only their per-hit payload, id accessor, clean-pass message and — for
the rule-pack path — the `pack`/`total_words` extra keys; the per-hit payload
projections stay distinct and are injected unchanged (the per-hit field shape is
8.1.4/8.1.5 territory, not this builder's). Its **scope and re-use policy**: the
builder owns only the shared *skeleton*, so a change to the
violations-versus-findings relationship is made once here, while anything
genuinely per-path (a finding's projected fields, the prose of a message) stays
in the call site. Deriving the exit code from the `failed` filter rather than a
separate `passed` flag (design §3.2; ADR-003) closes the latent
self-contradictory-envelope path: a report whose `passed` flag disagreed with
its findings can no longer emit `ok: true` alongside a non-empty `violations`
list.

#### The ai-isms pack: cadence, ownership, and membership

Roadmap task 7.1.1 ships a second packaged pack beside `offenders.toml`:
[`novel_ralph_skill/rulepack/packs/ai-isms.toml`](../novel_ralph_skill/rulepack/packs/ai-isms.toml),
the *AI-ism* tell pack (design §6.2). Where `offenders.toml` carries the §6
prose-craft offenders, `ai-isms.toml` carries the lexical and phrasal tells of
LLM-default prose — "load-bearing", "a testament to", and similar. It ships by
the same default hatchling mechanism, travels in the wheel, and resolves through
`importlib.resources.files`. It is **opt-in**: `novel desloppify` selects it only
when given `--pack ai-isms.toml`, and the default pack stays `offenders.toml`.
Combining both packs in one invocation is roadmap task 7.1.7 (the multi-pack
`novel desloppify` surface) and is not yet supported: a single run scans
exactly one pack.

The AI-ism tell set is a *moving target* the maintainer owns as versioned data,
not code (design §6.2). The cadence is:

- **Owner.** The skill maintainer owns the pack and this policy.
- **Review schedule.** The pack is reviewed at least once per release, and no
  less than annually, as tells emerge or go stale. (AI-ism vocabulary dates:
  the WP:AISIGNS field guide records, for instance, that "delve" was overused
  in 2023–2024 and then dropped off sharply in 2025.)
- **Adding or retiring a tell** is a *data edit* — one TOML `[[rule]]` row plus
  its positive and negative test rows in
  [`tests/test_ai_isms_pack.py`](../tests/test_ai_isms_pack.py) — never a code
  change. The loader, detector, and envelope are untouched.
- **A schema change** (not expected) would bump `RULEPACK_SCHEMA_VERSION`; the
  tell set evolves under the existing v1 schema by data edits alone.

The **membership policy** keeps the next maintainer from inventing tells:

- Every new tell must be cited to an authoritative source — the design's named
  examples (§6.2), or a dated AI-ism field guide such as WP:AISIGNS
  (<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>) — recorded in
  a `# source:` comment above the row.
- Every tell must be **collocational**: a multi-token phrase, never a bare
  standalone English word. A bare word such as `delve`, `nestled`, or `boasts`
  is rejected, because `detect.py` applies no semantic gate and such a rule
  fires on legitimate fiction (WP:AISIGNS lists those words as recurring in
  ordinary prose). A vocabulary tell is narrowed to its AI-ism collocation —
  `rich tapestry`, not bare `tapestry`; `is a testament`, not bare `testament`.
- Every id is disjoint from `offenders.toml`'s ids, so the two packs never
  double-count; the validation suite asserts the disjointness.

The shipped Tier B tell set — `stands-as-a-testament`, `rich-tapestry`, and
`vital-role` — was **ratified by the skill maintainer** on 2026-06-25, closing
the maintainer-owned data contract the original task opened. (Task 7.1.1 first
shipped Tier B as "ratified-by-plan" because the maintainer was unreachable in
the autonomous run; this records the explicit human ratification.) Future
additions follow the membership policy above and are ratified the same way.

The ai-isms patterns diverge deliberately from design §6.1's case-sensitive
illustration (and from the case-sensitive `\btapestry\b`/`\bdelve\b` worked
example above): every ai-isms pattern carries the inline `(?i)` flag, for
parity with `offenders.toml` and because a manuscript capitalizes a tell at a
sentence start or in a chapter title. The inline `(?i)` is never a compile
flag; the loader still compiles every pattern with no flags.

### The device ledger and per-novel rationing

Roadmap task 7.1.2 adds a parallel detection family: the *device ledger*, a
per-novel `device-ledger.toml` that rations a book's signature devices — a
recurring image, a key phrase, a bookend line — each of which is meant to land
a fixed number of times, in a fixed set of chapters, and nowhere else (design
§6.3, resolving open question Q3). Unlike the shipped rule packs, the ledger is
**per-novel user data**: it is not packaged in the wheel and has no
`importlib.resources` resolver. It is selected with `novel desloppify --ledger PATH`,
where `PATH` is a filesystem path the novelist (or the harness) writes into
`working/`. A run with no `--ledger` is the unchanged rule-pack scan.

The ledger lives in a new package,
[`novel_ralph_skill/ledger/`](../novel_ralph_skill/ledger/), modelled on the
rule-pack package (schema → parse → detect → report) but carrying its own
chapter-aware vocabulary that the closed v1 rule-pack schema cannot express
(ADR-001/003/007 still hold: detect-only, the shared envelope contract, and the
single `novel` command surface — the ledger is a flag on `novel desloppify`,
never a separate subcommand). The TOML shape is `schema_version` plus one or
more `[[device]]`
tables, each with an `id`, a regex `pattern`, and a ration:

```toml
schema_version = 1

[[device]]
id = "sternum"
pattern = "(?i)pressure[^\n]{0,20}?sternum"
max_count = 3
allowed_chapters = [1, 3, 8]
```

The **closed key vocabulary** is `id`, `pattern`, and the four rationing fields
`max_count`, `allowed_chapters`, `retired_after_chapter`, and
`reserved_for_chapter`. The **constraint-combination semantics** are:

- a device must carry **at least one** of the four rationing fields — a
  ration-less device is a no-op the author did not intend, so the loader
  rejects it;
- a device may carry **at most one** of the three *window* constraints
  (`allowed_chapters`, `retired_after_chapter`, `reserved_for_chapter`);
  `max_count` may pair with any one window. A device combining two window
  constraints is rejected;
- `max_count` — total hits across the manuscript must be `<= max_count`;
  `allowed_chapters = [..]` — every hit's chapter must be in the set;
  `retired_after_chapter = N` — no hit in any chapter `> N`;
  `reserved_for_chapter = N` — every hit must be in chapter `N`.

Like the rule-pack loader, malformed *content* fails loudly through a
`LedgerError` the command maps to **exit 2**, naming the offending device; an
absent, unreadable, or undecodable ledger *file* fails through a
`LedgerFileError` mapped to **exit 3**. An over-ration device exits **4**,
naming the device in `result.violations`; a within-ration manuscript exits
**0**.

The ledger path obeys the same
[clean-pass findings contract](#the-clean-pass-findings-contract-roadmap-task-713)
as the rule-pack path: `result.findings` carries only the over-ration devices,
so a within-ration manuscript emits `findings: []` and `violations: []` at exit
`0`.

Detection follows the same **line-by-line, no-flags, no-semantic-gate** model
as the rule-pack detector. A *spend* is one literal `finditer` hit of the
device's pattern, counted line by line so `.` cannot cross a newline and each
hit's `{chapter, line}` is exact; a multi-token device must use a bounded
non-newline window `[^\n]{0,N}?`, never greedy `.*`. There is **no semantic
gate**: a bare word such as `\bsternum\b` fires on every literal use of the
word, not only the motif use, so an author narrows the pattern to the motif's
collocation knowingly. The current spend is **recomputed from the chapter
drafts on disk on every run** (design §6.3), so the ledger cannot drift from
the manuscript: editing a draft to remove a spend and re-running drops the
finding with no ledger edit. Whether a device *should* have been spent stays
the model's call (ADR-001).

The ledger is a **whole-manuscript** concern — it rations *across* the book — so
`--ledger` is **mutually exclusive with `--chapter`**: a single-chapter scan
cannot total `max_count` or evaluate a chapter window faithfully, so the
combination is an exit-2 usage fault rather than a silently wrong count. Each
window constraint is read **negatively** (a hit outside the window is a
violation); there is no "must appear" floor, so a `reserved_for_chapter`
bookend the author forgot entirely passes silently. That is design-conformant
(§6.3 specifies no floor); a "must appear" floor is the highest-value future
enhancement, recorded here so the limitation is explicit, not accidental.

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
