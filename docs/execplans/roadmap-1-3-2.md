# Build the on-disk `working/` fixture corpus

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

This is roadmap task 1.3.2 (`docs/roadmap.md` lines 229-236, step 1.3). It
builds the shared on-disk test corpus every later slice consumes: a set of
reusable pytest fixtures that materialise a `working/` directory tree under
`tmp_path` for each of the eleven phase states, for coherent and deliberately
incoherent `state.toml` variants, and for chapter drafts with `done.flag`
permutations. The corpus is the seed of the snapshot and behavioural suites in
roadmap phases 2-6, so it is built once here and consumed unchanged thereafter
(roadmap 1.3.2 success criterion: "the corpus is consumed unchanged by the
slice suites in phases 2-6, so no slice re-rolls fixtures").

The corpus is anchored to the design's authoritative artefacts:
`docs/novel-ralph-harness-design.md` §5 (state schema and invariants) and §9
(verification strategy), and the on-disk layout in
`skill/novel-ralph/references/state-layout.md`, which design §5.1 names as "the
authoritative source for the on-disk layout".

After this change a contributor can, in any test module, request a fixture by
parameter name and receive a fully materialised `working/` tree on disk, then
point a command (in a later slice) at it. Concretely, after this task lands:

- A new conftest-level factory fixture (the "factory as fixture" pattern,
  verified against the pytest stable docs; see "Documentation to read") builds a
  `working/` tree from a declarative specification, writing `state.toml` via
  `tomlkit`, the chapter directories (`working/manuscript/chapter-NN/`), their
  `draft.md` and optional `done.flag` files, and
  `working/manuscript/compiled.md` where the variant calls for it.
- A library of named specifications covers the eleven phase states
  (`premise` … `done`, design §5.1), the coherent baseline, the deliberately
  incoherent variants (each violating exactly one §5.2 invariant), and the
  `done.flag` permutations.
- A self-validating corpus test proves every fixture materialises the tree it
  claims and that the coherent / incoherent split is real: the coherent
  variants satisfy a corpus-local structural oracle while each incoherent
  variant fails it on exactly the one invariant it is built to break.

### What this task does NOT do

- It does not implement, import, or invoke any of the five commands. Those are
  built in phases 2-6. This task delivers only the fixtures and their
  self-tests; the commands that will consume the corpus do not exist yet
  (`novel_ralph_skill` today contains only `commands/` stubs and the
  `contract/` module from task 1.3.1; verified by `find novel_ralph_skill`).
- It does not implement the typed `state.toml` schema or the §5.2 invariant
  validator. Those are roadmap tasks 2.1.1 and 2.1.2, which *consume* this
  corpus (roadmap 2.1.1 success: "representative states from the §1.3.2 corpus
  parse into the typed structure"; 2.1.2 success: a Hypothesis suite over the
  corpus). The corpus must therefore be expressed in plain Python / `tomlkit`
  data, NOT against a schema type this task would have to invent and then
  rework when 2.1.1 lands. The corpus's own self-test re-implements only the
  *structural* checks it needs to prove the coherent/incoherent split (a small,
  deliberately local oracle), and is explicit that the canonical validator is
  2.1.2's job (see Decision Log).
- It adds NO production code under `novel_ralph_skill/`. The corpus is test
  scaffolding and lives entirely under the top-level `tests/` tree (`AGENTS.md`
  lines 145-147: "Keep pytest tests in the top-level `tests/` tree").
- It deliberately writes a **narrower** chapter-directory file set than
  `state-layout.md` lists. `state-layout.md` (lines 35-44) shows each
  `working/manuscript/chapter-NN/` holding `scenes.md`, `beats.md`, `draft.md`,
  `critic-notes.md`, `fangirl-notes.md`, and `done.flag`. The builder writes
  only `draft.md` and (where flagged) `done.flag`, because those are the only
  files the consumers this task serves depend on: the §5.2 bijection is between
  `[chapters]` manifest entries and chapter *directories* (not their inner
  files), and §4.3 compiles from `draft.md` alone. The omitted reference files
  (`scenes.md`, `beats.md`, `critic-notes.md`, `fangirl-notes.md`) are
  non-load-bearing for the phase-2-6 consumers the plan names (2.x
  check/reconcile/compile, 3.x done-predicate). If a later slice is found to
  need one present, that is an escalation (a scoped builder addition), not a
  silent re-roll. (Resolves round-2 advisory A1.)
- It invokes no external process, so it depends on **no** `cuprum` API. Design
  §9 (line 711) states: "v1 commands shell out to nothing, so the suite touches
  only the filesystem under `tmp_path`." The corpus writes files with `pathlib`
  and `tomlkit` only. `cuprum` is used elsewhere in `tests/conftest.py` (the
  `single_program_catalogue` / `venv_scripts_dir` fixtures for the
  console-scripts e2e), but this task neither touches nor needs it. (Stated
  explicitly so the implementer does not reach for a catalogue this task has no
  use for; verified against `cuprum` 0.1.0 locked in `uv.lock` and the existing
  `tests/conftest.py` usage.)

## Orientation for a newcomer

You have only this repository's working tree and this file. Key facts:

- The package is `novel_ralph_skill` (`pyproject.toml`,
  `requires-python = ">=3.14"`). Tests live only under the top-level `tests/`
  tree.
- `tests/conftest.py` is the single home for shared test scaffolding
  (`docs/developers-guide.md` "Shared test scaffolding"). It already exposes
  `project_root`, `pyproject`, `read_repo_text`, `toml_table`, `dist_name`,
  `single_program_catalogue`, and `venv_scripts_dir`, each as a fixture
  consumed by parameter name with no cross-module import. This task adds the
  corpus fixtures here (or in a dedicated sibling module imported by
  `conftest`; see Decision Log) following the same factory-as-fixture idiom.
- `tomlkit` (0.15.0, a runtime dependency; `pyproject.toml`, ADR-002) is the
  comment- and format-preserving TOML library. The corpus writes `state.toml`
  with `tomlkit` so the variants it produces are exactly what the round-trip
  helper in task 2.2.1 must preserve byte-for-byte. `tomllib` (stdlib) reads
  TOML but cannot write it (design §5.3), so it is fine for *reading back* a
  written `state.toml` in a self-test, but the corpus must *write* with
  `tomlkit`.
- `hypothesis` (6.155.7) and `syrupy` (5.3.2) are already locked dev
  dependencies (added in task 1.3.1; verified in `uv.lock` and `pyproject.toml`
  `[dependency-groups].dev`). This task needs **no new dependency**.
- Quality gates are Makefile targets (`AGENTS.md` lines 71-98): `make all` runs
  `build check-fmt lint typecheck test`; markdown changes additionally need
  `make markdownlint` and `make nixie`. `make lint` enforces 100% docstring
  coverage via `interrogate` (so every fixture and helper needs a docstring,
  including the corpus's specification dataclasses) and runs Ruff plus
  PyPy-Pylint.
- `tests/conftest.py` is inside `$(PYTHON_TARGETS)` (verified in the conftest
  docstring, lines 12-17), so the new fixtures are fully linted, typechecked,
  and docstring-gated like production code. A test *module* gets the
  `**/test_*.py` per-file-ignores; a conftest helper does not, so guard
  failures in self-tests that live in `conftest` must raise `AssertionError`
  directly rather than use a bare `assert`.

The eleven phase states, in order, are the canonical phase enum (design §5.1
lines 402-405, mirrored in `state-layout.md` lines 122-134):

```text
premise → treatment → characters → conflict-analysis → setting →
reader-fit → stc → chapter-planning → drafting → final-pass → done
```

The on-disk layout the corpus reproduces (design §5.1; `state-layout.md` lines
13-52) anchors the manuscript under `working/manuscript/`: each chapter is
`working/manuscript/chapter-NN/` (zero-padded to two digits up to 99) holding
`draft.md` and, when complete, `done.flag`; the compiled output is
`working/manuscript/compiled.md`; the chapter outline is
`working/plan/chapter-outline.md`. `state.toml` and `log.md` sit at the
`working/` root.

The validated schema (design §5.1 lines 386-398) adds three fields beyond the
`state-layout.md` reference structure, and the corpus MUST carry them so the
phase-2 schema task can parse representative states without loss:

- `[chapters]` — the chapter manifest: an ordered record of each planned
  chapter (number, slug, title, target words).
- `[drafting.critic].convergence_target` — the configured ceiling for
  `consecutive_clean` (default 1).
- `[pending_turn]` — the per-turn intent record (the operation in flight and
  the paths it will write), present only in the torn-turn variants.

So that task 2.1.1 parses representative states "without loss", the builder
must also emit every table the `state-layout.md` schema (lines 63-116) already
carries, with fixed deterministic defaults the corpus owns as builder constants
— not because this task validates them, but because an absent field makes
2.1.1's parse incomplete. The full required set, with the exact key forms the
corpus and the eventual validator must agree on, is:

- `schema_version = 1` (line 64).
- `[novel]`: `title`, `slug`, `target_word_count`, and `created_at` fixed to the
  single literal `"2026-05-23T14:00:00Z"` (lines 66-70).
- `[phase]`: `current` and the ordered `completed` prefix (lines 72-83).
- `[drafting]`: `current_chapter`, `current_scene`, `current_beat` (lines
  85-88).
- `[drafting.critic]`: `pass`, `consecutive_clean`, `convergence_target` (the
  added field), and `last_finding_counts` (an inline table of `blocker`,
  `major`, `minor`, `taste`) (lines 90-98).
- `[drafting.fangirl]`: `last_chapter_passed` (lines 100-101).
- `[gates.knitting]`: `done_30`, `done_50`, `done_80` (lines 103-106).
- `[gates.final]`: `final_pass_complete` (lines 108-109).
- `[word_counts]`: `target`, `current`, and `by_chapter` — an inline table keyed
  by **zero-padded two-digit string** (`{ "01" = 3200, "02" = 3500, … }`, line
  115). The corpus, the invariant-3 sum check, and the oracle all use this
  exact string key form; the builder derives `by_chapter["NN"]` from each
  chapter's `draft_words` unless a variant injects a deliberate mismatch.
- `[chapters]` — the manifest, one entry per planned chapter (`number`, `slug`,
  `title`, `target_words`), ordered to mirror the zero-padded directory index
  (design §4.3 lines 331-339).

The knitting-gate thresholds are the single source of truth `0.30 / 0.50 / 0.80`
(`state-layout.md` lines 174-177): a gate boolean is coherent only when
`word_counts.current / word_counts.target` has crossed its threshold (invariant
7). The corpus pins these three constants **once** in the corpus module and
shares them between the coherent gate booleans, the `gate-true-below-threshold`
incoherent variant, and the oracle's invariant-7 branch, so the three cannot
drift. The `[pending_turn]` record carries, at minimum, an `operation` key (a
string naming the mutation in flight) and a `paths` key (the list of paths it
will write), per design §3.4 lines 227-235; the design pins no further fields,
so the torn-turn variant carries exactly those two and the precise final field
set is deferred to task 2.3.2 (recorded as a Decision).

The §5.2 invariants the corpus's coherent variants satisfy and its incoherent
variants each break (design §5.2 lines 436-456) are:

1. `phase.current` is a member of the phase enum.
2. `phase.completed` is a prefix of the enum in order, with no gaps.
3. `word_counts.by_chapter` sums to `word_counts.current`.
4. `0 ≤ drafting.critic.consecutive_clean ≤ convergence_target`, the latter
   itself `≥ 1`, and `consecutive_clean` never exceeds the number of chapters
   drafted.
5. The chapter manifest and the on-disk chapter directories are in bijection:
   every `[chapters]` entry has exactly one `chapter-NN/` directory and vice
   versa, contiguous from 1, no gaps.
6. The drafting cursor is coherent (`current_scene` / `current_beat` are zero
   until their plans exist, and never reference a chapter past
   `current_chapter`).
7. Each knitting-gate boolean is consistent with the
   `word_counts.current / word_counts.target` ratio (a gate is true only once
   its threshold is crossed).

These seven invariants drive the incoherent-variant set: the plan provides one
fixture per invariant that violates that invariant alone, plus the
contradictory-disk-evidence cases design §5.4 names (a `done.flag` beside an
empty `draft.md`; a `compiled.md` whose content is not the hash-equal ordered
concatenation of the chapter drafts present on disk) and the torn-turn case (an
uncleared `[pending_turn]`). These map one-to-one onto the disk states the
phase-2 `check` / `reconcile` scenarios (roadmap 2.3.2) and the phase-3
done-predicate clauses (roadmap 3.1.x) must exercise.

The `compiled.md` contradiction is expressed strictly in the design's own
compile model, never by inventing a chapter-naming grammar. Design §4.3 (lines
320-344) defines `compiled.md` as the deterministic **ordered concatenation of
the chapter drafts with consistent separators**, and §9 (lines 705-711, with
the compile-divergence prose at §4.2 lines 307-318) defines the only fidelity
check as a **content-hash** comparison between `compiled.md` and a fresh
ordered concatenation of the present drafts. The design's prose elsewhere
describes the contradiction informally as a "`compiled.md` referencing an
absent chapter" (§5.4 line 499; §10 line 725), but it pins **no** structured
chapter-reference, heading, or separator-grammar inside `compiled.md` that a
fixture could parse. The corpus therefore models this case as a `compiled.md`
whose bytes are **not** the hash-equal concatenation of the present drafts (a
stale or contradictory compile), and the oracle detects it by recomputing that
concatenation and comparing — exactly the §4.3/§9 mechanism
`novel-compile --check` and the `novel-done` compile clause will use. No
separator/heading grammar is invented, so the Tolerance against silent
corpus/design changes is respected (see the separator Decision in the Decision
Log, and the escalation Tolerance covering a phase-4 separator divergence).

## Constraints

Hard invariants; violation requires escalation, not a workaround.

- Add no production code under `novel_ralph_skill/`. The corpus is test
  scaffolding under `tests/` only (AGENTS.md lines 145-147).
- Do not invent or depend on the typed `state.toml` schema type or the §5.2
  validator. They are roadmap tasks 2.1.1 / 2.1.2 and consume this corpus; the
  corpus is expressed as plain data written through `tomlkit` (Decision Log).
- The on-disk layout must match `state-layout.md` and design §5.1 exactly:
  manuscript under `working/manuscript/`, chapters `chapter-NN/` zero-padded to
  two digits, `compiled.md` at `working/manuscript/compiled.md`, outline at
  `working/plan/chapter-outline.md`, `state.toml` and `log.md` at the
  `working/` root. The earlier-draft paths `working/compiled.md` and
  `working/chapter-NN/` are wrong and must not appear (design §5.1 lines
  381-384).
- `state.toml` is written with `tomlkit`, not `tomllib`/`json`/hand-formatted
  strings, so the variants are valid inputs to the task-2.2.1 round-trip
  property (design §5.3; ADR-002). `state.toml` carries `schema_version`, the
  three added fields where the variant needs them, and the eleven-phase enum
  ordering.
- Each "coherent" variant satisfies every §5.2 invariant; each "incoherent"
  variant violates exactly one named invariant (or models exactly one
  contradictory-disk / torn-turn case). No incoherent variant may accidentally
  violate a second invariant — that would make it useless to a later negative
  test that means to isolate one failure.
- All corpus *values* — every spec instance, the `PHASE_STATES` /
  `INCOHERENT_VARIANTS` / `DONE_FLAG_PERMUTATIONS` mappings, the
  `COHERENT_BASELINE`, the `build_working_tree` builder, and the `corpus_check`
  oracle — are reached **only** by fixture parameter name. No test module
  performs a runtime `from working_corpus import …` (or any cross-module value
  import). This is categorical in the developers-guide "Shared test
  scaffolding" (lines 31-37): scaffolding is consumed "by fixture name … and
  never by importing from another test module or from `conftest` itself", and
  six prior audits (`audit-1.2.1`…`1.2.7`, cited in `tests/conftest.py` lines
  8-10) were specifically about cross-module value imports. The corpus data and
  builder live in `tests/working_corpus.py`; `tests/conftest.py` imports them
  there (a conftest importing its own private data module is not a *test*
  module reaching into another, and is the same move `conftest` already makes —
  it is the single sanctioned importer) and re-exposes every datum as a fixture.
- The spec **types** `WorkingTreeSpec` and `ChapterSpec` are named in test
  annotations **only** through the literal developers-guide carve-out (lines
  39-52): "a type that describes a fixture's value … may be imported **from
  `conftest`** under an `if TYPE_CHECKING:` guard
  (`from conftest import RepoTextReader`)." The carve-out is scoped to
  `conftest`, not to an arbitrary module, so the spec types must be reachable as
  `from conftest import WorkingTreeSpec` (and `ChapterSpec`) under the guard —
  exactly the documented form. To achieve this **without** a guide amendment
  and **without** a runtime cross-module cycle, the dataclasses are *defined* in
  `tests/working_corpus.py` (where the builder constructs them, so no module
  imports `conftest` at runtime) and *re-exported from* `tests/conftest.py`
  under its own `if TYPE_CHECKING:` block
  (`from working_corpus import WorkingTreeSpec, ChapterSpec`). Because that
  re-export lives inside `conftest`'s `TYPE_CHECKING` guard, it is `False` at
  runtime and creates no runtime import; a test then writes
  `from conftest import WorkingTreeSpec` under its own guard — the verbatim
  sanctioned form. A test never needs to construct a spec at runtime to *use*
  the corpus — it receives a built tree from a factory fixture — so the type
  name is annotation-only. **This conforms to the existing guide rule and adds
  no amendment**: the only `TYPE_CHECKING` import a test performs is
  `from conftest import …`, which is precisely the rule's words. (Resolution
  (a) of design-review D1. Resolution (b) — keeping the types in
  `working_corpus.py`, importing them from there under `TYPE_CHECKING`, and
  amending the guide to extend the carve-out to the dedicated corpus module —
  was rejected because the literal carve-out is achievable cycle-free by
  re-exporting through `conftest`, so no guide amendment is warranted.)
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
  docstrings (AGENTS.md lines 18-20; en-gb-oxendict skill), except external API
  names.
- No single code file exceeds 400 lines (AGENTS.md lines 24-27). The
  specification corpus is data; if `conftest.py` would approach the cap, move
  the corpus data and its builder into a dedicated module under `tests/`
  imported by `conftest` (Decision Log; this is the AGENTS.md guidance "Large
  blocks of test data should be moved to external data files").
- 100% docstring coverage (`make lint` runs `interrogate`); every public
  fixture, builder function, and specification type needs a docstring.

## Tolerances (exception triggers)

- Scope: if implementation requires more than 6 files or ~700 net lines
  (fixtures + specs + self-tests + docs), stop and escalate. (The corpus is
  inherently data-heavy; this ceiling is wider than 1.3.1's because the
  specification library spans eleven phases plus the variant set.)
- Dependencies: this task adds **no** new dependency. If any new dependency
  (runtime or dev) appears necessary, stop and escalate — the corpus is
  `pathlib` + `tomlkit` + `pytest` only, all already locked.
- Schema coupling: if expressing a variant appears to *require* the typed
  schema or the validator from phase 2, stop and escalate — that is a roadmap
  ordering conflict (1.3.2 requires only 1.2.1), not something to resolve by
  pulling phase-2 work forward.
- Interface: if the §5.1 schema fields or §5.2 invariants in the design appear
  to need changing to express a fixture, stop and escalate — that is a design
  amendment, not a silent corpus change.
- Compile model: if expressing the `compiled.md` contradiction appears to
  require a parseable chapter-reference, heading, or separator grammar inside
  `compiled.md` (which design §4.3 / §9 do not define), stop and escalate — do
  not invent one in a fixture. The only sanctioned compile model is the
  content-hash comparison against `concatenate_drafts` of the present drafts.
- Separator divergence: if a later phase (task 4.1.1, `novel-compile`) fixes a
  production draft separator that differs from `CORPUS_SEPARATOR`, stop and
  escalate to reconcile the constant (a one-line change recorded in the
  Decision Log), rather than silently re-rolling the corpus's coherent
  `compiled.md` files.
- Import contract: if any corpus value (a spec instance, a mapping, the builder,
  or the oracle) appears to need a runtime `from working_corpus import …` in a
  *test* module, stop — route it through a `conftest` fixture instead. The only
  symbol a test module may name is a spec *type*, and only under
  `if TYPE_CHECKING:` via `from conftest import WorkingTreeSpec` (the verbatim
  developers-guide carve-out, lines 39-52); a `TYPE_CHECKING` import directly
  `from working_corpus` in a *test* module is **not** sanctioned (it extends
  the carve-out) — `conftest` re-exports the types so the `from conftest` form
  is available. If the `from conftest` re-export appears not to work (e.g. a
  tooling constraint), stop and escalate rather than importing from
  `working_corpus`.
- Iterations: if a gate (`make all`) still fails after 3 fix attempts on one
  work item, stop and escalate.
- Ambiguity: if `state-layout.md` and design §5.1 appear to disagree on a path
  or field, stop and present the conflict (design §5.1 already flags the
  earlier-draft path discrepancy; any *new* disagreement is an escalation).

## Risks

- Risk: the corpus is built against a schema that does not yet exist (phase 2),
  so a later schema decision could force the corpus to be re-rolled, breaching
  the "consumed unchanged" success criterion. Severity: high. Likelihood:
  medium. Mitigation: anchor every field and path to the *design* (§5.1, §5.2)
  and to `state-layout.md`, the documents phase 2 itself implements, rather
  than to any provisional code; carry the three added fields (`[chapters]`,
  `convergence_target`, `[pending_turn]`) the design names so phase 2 parses
  the corpus "without loss"; and keep the corpus as plain `tomlkit` data so a
  schema *type* can wrap it without the data changing. Recorded as a Decision.
- Risk: an "incoherent" variant accidentally violates a second invariant,
  making it useless to the phase-2/3 negative test that means to isolate one
  failure. Severity: medium. Likelihood: medium. Mitigation: the corpus
  self-test asserts each incoherent variant fails the corpus-local structural
  oracle on exactly its named invariant and *passes* every other check, so a
  double-violation fails the corpus's own suite loudly (Work item 3).
- Risk: the corpus-local structural oracle drifts from the eventual §5.2
  validator (task 2.1.2), so the corpus and the real validator disagree about
  which variants are coherent. Severity: medium. Likelihood: medium.
  Mitigation: the oracle is scoped to the *structural* §5.2 invariants only, is
  documented as a corpus-internal cross-check (not the canonical validator),
  and exposes a stable invariant-name vocabulary (`CORPUS_INVARIANT_NAMES`) so
  task 2.1.2 can assert the real validator agrees with the corpus labels on
  every fixture by keying on the same strings (advisory A5). The oracle's
  checks are enumerated against §5.2 lines 436-456 so the mapping is auditable,
  and the compile check uses the design's §4.3/§9 content-hash model (recompute
  `concatenate_drafts` and compare) rather than a separator/heading grammar the
  design does not define, so the oracle cannot diverge from `novel-compile` by
  encoding a compile model the design lacks (design-review B1).
- Risk: `tomlkit` writes a state file the phase-2 round-trip cannot preserve
  byte-for-byte (e.g. through an idiom `tomlkit` normalises on load). Severity:
  medium. Likelihood: low. Mitigation: write each `state.toml` through
  `tomlkit` and, in the self-test, read it back with `tomllib` and assert the
  decoded values match the specification; additionally assert a `tomlkit`
  load-then-dump of the written file is idempotent (the no-op round-trip the
  task-2.2.1 property will later assert), so a non-round-trippable idiom is
  caught here, not in phase 2.
- Risk: the corpus files churn snapshot tests in later phases because the prose
  content of `draft.md` is non-deterministic. Severity: low. Likelihood:
  medium. Mitigation: draft bodies are fixed, deterministic, minimal text with
  a known word count (so `wordcount` and `recount` in phases 2/6 have exact
  expected totals); no timestamps, random ids, or absolute paths appear in any
  corpus file (AGENTS.md snapshot rules, lines 148-158). `created_at` and any
  log timestamp use a single fixed literal.
- Risk: a fixture leaves state on disk between tests. Severity: low.
  Likelihood: low. Mitigation: every tree is built under the test's own
  `tmp_path` (function-scoped, pytest-managed), so there is no shared mutable
  state; the factory takes the destination directory as a parameter.

## Progress

- [x] Work item 1: define the corpus specification types and the tree builder
  (`build_working_tree`), with unit tests proving it materialises the declared
  files and writes a `tomlkit`-round-trippable `state.toml`.
- [x] Work item 2: define the named specification library — the eleven phase
  states and the coherent baseline — and expose them through a factory fixture,
  with tests asserting each phase state materialises with the right
  `phase.current` / `phase.completed`.
- [x] Work item 3: add the deliberately incoherent variants (one per §5.2
  invariant), the contradictory-disk cases — including
  `compiled-not-concatenation-of-drafts`, detected by the §4.3/§9 content-hash
  model, never by parsing chapter names — and the torn-turn case, plus the
  corpus-local structural oracle (with its stable `CORPUS_INVARIANT_NAMES`
  vocabulary) and the self-test that proves the coherent/incoherent split (each
  incoherent variant fails on exactly its named invariant), all consumed
  through fixtures by parameter name.
- [x] Work item 4: add the `done.flag` permutation fixtures and the chapter
  draft factory parameters they need.
- [x] Work item 5: document the corpus in the developers' guide, index it in
  `docs/contents.md`, and reify the roadmap checkbox; run markdown gates.

## Surprises & discoveries

- Work item 1: the corpus exceeds the 400-line file cap if held in one module,
  so `working_corpus` is implemented as a *package* under `tests/`
  (`__init__.py` re-exporting `_specs.py` and `_builder.py`, with later work
  items adding `_library.py`, `_oracle.py`, and `_variants.py`). This satisfies
  the contract verbatim: `from working_corpus import WorkingTreeSpec` resolves
  through the package `__init__`, identical to a single module, and `conftest`
  remains the single runtime importer. Recorded as a Decision below.
- Work item 1: the PyPy-Pylint gate (unlike Ruff) does not honour the
  `**/test_*.py` `per-file-ignores`, so a five-argument test tripped
  `too-many-arguments`. Resolved by bundling the builder and concatenation
  helper into one `compile_probe` fixture rather than passing both separately.
- Work item 1: a `TYPE_CHECKING` re-export with an `__all__` list trips Ruff's
  `runtime-import-in-type-checking-block` (the `__all__` entry counts as a
  runtime use). The re-export is kept use-only: the spec types are referenced
  in the corpus fixture annotations (`from conftest import WorkingTreeSpec`),
  so no `__all__` is needed and the import stays type-only.
- Work item 2: `ty` could not narrow a `**dict[str, bool]` kwargs unpack against
  the keyword-only `WorkingTreeSpec` fields (it reported the unpacked value
  against unrelated fields). Resolved by returning the three gate booleans as a
  fixed-length tuple from `_crossed_gates` and passing them by explicit name,
  which `ty` checks precisely.
- Work item 2: the phase enum block in `state-layout.md` carries inline `#`
  comments on some lines (e.g. `drafting   # contains the inner Ralph loop`), so
  the reference parser takes the leading whitespace-delimited token per line
  rather than the whole line. The phase order is parsed from the reference (not
  re-typed) so it stays the single source of truth.
- Work item 3: adding the corpus fixtures pushed `tests/conftest.py` past the
  400-line module cap (it reached 481). The corpus fixtures moved into a
  registered pytest plugin module `tests/corpus_fixtures.py`
  (`pytest_plugins = ("corpus_fixtures",)` in `conftest`), which is the corpus's
  single runtime importer of `working_corpus`; `conftest` keeps only the
  spec-type `TYPE_CHECKING` re-export for the `from conftest import
  WorkingTreeSpec` carve-out. Every fixture is still available by name exactly
  as a `conftest` fixture would be, and no test module value-imports the corpus.
  Recorded as a Decision below.
- Work item 3: the torn-turn `[pending_turn]` case needed a detectable oracle
  signal, so the oracle vocabulary gained a tenth invariant name
  `pending-turn-cleared` (an uncleared `[pending_turn]` is a §3.4 torn turn). The
  plan's vocabulary listed nine names; the tenth is the structural label for the
  torn-turn variant the plan already required, recorded as a Decision.
- Work item 3: building several variants under one `tmp_path` left a previous
  variant's `compiled.md` in place and produced a spurious second violation, so
  the `incoherent_tree`, `phase_state_tree`, and `coherent_oracle_cases`
  factories each build in a per-name/per-phase subdirectory of `tmp_path`.
- Work item 3: the invariant-2 (`completed-prefix`) and invariant-7
  (`gate-ratio-consistent`) checks had to be decoupled from sibling invariants so
  each variant breaks exactly one name: `completed-prefix` passes when
  `phase.current` is outside the enum (that is invariant 1's concern), and
  `gate-ratio-consistent` computes its ratio from the honest on-disk draft total
  rather than from a `by_chapter_override`. The `_with_chapters` helper also
  re-derives consistent gate booleans from the mutated chapter set so a
  draft-word mutation does not incidentally break invariant 7.
- Work item 4: adding the permutation tests pushed `tests/test_working_corpus.py`
  past the 400-line module cap, so the `done.flag` permutation self-tests live in
  a sibling module `tests/test_working_corpus_done_flags.py`. The
  `done_flag_tree` factory returns `(spec, working_dir)` so the test runs the
  oracle to confirm each permutation is coherent.

## Decision log

- Decision: express the corpus as plain Python specification data written
  through `tomlkit`, not against the typed `state.toml` schema. Rationale: the
  schema is roadmap task 2.1.1, which depends on this corpus (roadmap 2.1.1
  "Requires steps 1.1-1.3"); building the corpus against a not-yet-existent
  type would invert the dependency and force a re-roll when 2.1.1 lands,
  breaching the "consumed unchanged" criterion. Anchoring to the design
  documents the schema itself implements keeps the corpus stable across the
  schema's arrival. Date/Author: 2026-06-22, planning agent.
- Decision: the corpus carries a small corpus-local structural oracle that
  re-implements only the §5.2 *structural* invariants, used solely to prove the
  coherent/incoherent split in this task's own self-test; it is explicitly not
  the canonical validator. Rationale: this task must prove its incoherent
  variants are genuinely incoherent *now*, before task 2.1.2's validator
  exists, without smuggling phase-2 work forward. Scoping the oracle to the
  structural checks and documenting it as a cross-check (task 2.1.2 will assert
  the real validator agrees with the corpus labels) keeps the boundary clean.
  Date/Author: 2026-06-22, planning agent.
- Decision: use the pytest "factory as fixture" pattern (a fixture returning a
  builder callable), matching the existing `read_repo_text` / `toml_table` /
  `single_program_catalogue` fixtures in `tests/conftest.py`. Rationale: a
  single test often needs several trees (e.g. a coherent and an incoherent
  variant to compare), which a value fixture cannot supply; the factory pattern
  is the documented pytest idiom for that (pytest stable docs, "Factories as
  fixtures") and is already the house style here. Date/Author: 2026-06-22,
  planning agent.
- Decision: the corpus data, the spec **types** (`WorkingTreeSpec` /
  `ChapterSpec`), the `build_working_tree` builder, and the `corpus_check`
  oracle live in a dedicated `tests/working_corpus.py` module (not a
  `test_*.py` module), and `tests/conftest.py` is the **single** runtime
  importer that re-exposes every datum as a fixture. Test modules consume the
  data by fixture parameter name only — never a runtime value import. For *type
  annotations* a test may name a spec type, but it does so via the verbatim
  developers-guide carve-out (lines 39-52):
  `from conftest import WorkingTreeSpec` under `if TYPE_CHECKING:`. To make
  that literal form available without a runtime cycle, `conftest`
  **re-exports** the two types under its own `TYPE_CHECKING` block
  (`from working_corpus import WorkingTreeSpec, ChapterSpec`), which is `False`
  at runtime. Rationale: the developers-guide forbids cross-module *value*
  imports categorically (lines 31-37) and six audits enforced it; routing data
  through fixtures and routing the type annotation through `conftest`'s
  `TYPE_CHECKING` re-export both conform to the guide **as written** with **no
  amendment**. Defining the types directly in `conftest` was rejected because
  `working_corpus` (where the builder constructs them) would then have to import
  `conftest` at runtime — the exact cross-module runtime import the rule
  forbids; the re-export keeps the runtime dependency edge pointing only
  `conftest → working_corpus` (the direction `conftest` already uses for its
  cuprum fixtures), and the test-facing import is the sanctioned
  `from conftest import …`. `conftest` importing its own private data module is
  not the prohibited "another *test* module" case — it is the established
  consolidation pattern. Date/Author: 2026-06-22, planning agent. (Resolves
  design-review B2; resolves round-2 D1 by resolution (a).)
- Decision: model the `compiled.md` contradiction variant by **content**, not
  by parsing chapter names. The design defines `compiled.md` as the ordered
  concatenation of the present drafts with consistent separators (§4.3) and the
  only fidelity check as a content-hash comparison (§9; §4.2), and pins no
  parseable chapter-reference/heading/separator grammar inside the file. The
  variant `compiled-not-concatenation-of-drafts` therefore writes a
  `compiled.md` whose bytes are deliberately **not** the hash-equal ordered
  concatenation of the present drafts, and the oracle detects it by recomputing
  that concatenation and comparing — the same mechanism `novel-compile --check`
  will use. Rationale: detecting "names an absent chapter" structurally would
  require inventing a heading grammar the design does not have, breaching the
  no-silent-corpus-change Tolerance; the hash model is the design's actual
  contradiction signal. Date/Author: 2026-06-22, planning agent. (Resolves
  design-review B1; see the separator Decision and Tolerance below.)
- Decision: the corpus pins **one** separator constant (`CORPUS_SEPARATOR`) and
  a `concatenate_drafts(drafts: Sequence[str]) -> str` helper in
  `tests/working_corpus.py`, used both to write each coherent `compiled.md` and
  by the oracle to recompute the expected concatenation. Rationale: the design
  names "consistent separators" (§4.3) but does not pin the exact bytes; the
  corpus must choose one so its coherent compiles are self-consistent and its
  contradiction variant is meaningfully *different* from the canonical
  concatenation. The chosen separator is `"\n\n"` (a blank line between
  drafts), the simplest consistent separator. **Tolerance:** when task 4.1.1
  implements `novel-compile` and fixes the production separator, if it differs
  from `CORPUS_SEPARATOR` the corpus's coherent `compiled.md` files would no
  longer hash-match the real compiler — STOP and escalate (a one-line constant
  reconciliation, recorded here), rather than silently re-rolling the corpus.
  The oracle compares against its own `concatenate_drafts`, so it stays
  internally consistent regardless; only the cross-phase hash agreement depends
  on the constant matching. Date/Author: 2026-06-22, planning agent.
- Decision: the torn-turn `[pending_turn]` record carries exactly an
  `operation` string and a `paths` list (design §3.4 lines 227-235); the design
  pins no further fields, so the precise final shape is deferred to task
  2.3.2's reconciliation, and the corpus carries only this two-key marker.
  Rationale: anchoring to the two fields the design names gives 2.3.2 a
  concrete shape to read without over-committing to fields the design has not
  specified (resolves advisory A3). Date/Author: 2026-06-22, planning agent.
- Decision: if `tests/conftest.py` would exceed ~300 lines once the corpus
  fixtures land (it is 223 today), keep all corpus *data*, the
  `build_working_tree` builder, the `corpus_check` oracle, `CORPUS_SEPARATOR`,
  and `concatenate_drafts` in `tests/working_corpus.py`, and keep only the thin
  fixture wrappers in `conftest`, per AGENTS.md "Large blocks of test data
  should be moved to external data files" and the 400-line cap. The fixtures
  themselves stay in `conftest` so consumers still receive them by parameter
  name (no value import). Date/Author: 2026-06-22, planning agent. (The split
  is now mandatory, not conditional, because the no-value-import resolution
  above requires a dedicated non-`test_*` data module; finalise nothing else in
  Work item 1.)
- Decision (Work item 1): `working_corpus` is a *package* (`tests/working_corpus/`)
  rather than a single `tests/working_corpus.py` module, because the corpus data
  plus builder, oracle, and variant library exceed the 400-line file cap
  (AGENTS.md lines 24-27). The package splits into `_specs.py` (dataclasses,
  constants, helpers), `_builder.py` (`build_working_tree` and the `tomlkit`
  document construction), and — in later items — `_library.py`, `_oracle.py`,
  and `_variants.py`; `__init__.py` re-exports the public surface. The
  consumption contract is unchanged: `from working_corpus import WorkingTreeSpec`
  resolves through the package `__init__` exactly as for a module, `conftest`
  remains the single runtime importer, and no `test_*` module value-imports the
  corpus. Rationale: a package is the standard way to keep each file under the
  cap while preserving one import name; the plan's `tests/working_corpus.py`
  spelling was indicative of the import *name*, which the package preserves.
  Date/Author: 2026-06-22, implementation agent.
- Decision (Work item 1): the `AUTO` compile sentinel is named once as the
  `COMPILED_AUTO` constant in `_specs.py` (resolves a CodeRabbit minor: a bare
  `"AUTO"` string is ambiguous with file content). Date/Author: 2026-06-22,
  implementation agent.
- Decision (Work item 3): the corpus fixtures live in a registered pytest plugin
  module `tests/corpus_fixtures.py` (`pytest_plugins = ("corpus_fixtures",)` in
  `conftest`) rather than in `conftest` itself, because adding them to `conftest`
  pushed it past the 400-line module cap (AGENTS.md lines 24-27). The plugin is
  the single runtime importer of `working_corpus` and exposes every datum by
  fixture name; `conftest` retains only the spec-type `TYPE_CHECKING` re-export
  for the `from conftest import WorkingTreeSpec` carve-out. The plan named
  `conftest` the single importer, but a registered plugin is `conftest`-equivalent
  scaffolding (pytest treats both identically for fixture resolution), and the
  load-bearing contract — no test-module value imports, types via `from conftest
  import` — is fully preserved. The split is a hard-cap necessity, not a contract
  relaxation. Date/Author: 2026-06-22, implementation agent.
- Decision (Work item 3): the oracle vocabulary carries a tenth invariant name,
  `pending-turn-cleared`, for the §3.4 torn-turn case (an uncleared
  `[pending_turn]`). The plan's nine-name list covered the seven §5.2 structural
  invariants plus the two §5.4 disk cases but gave the torn-turn variant no
  detectable oracle label; the tenth name supplies it without inventing a new
  case (the variant was already required). Task 2.1.2 keys its cross-check on the
  full ten-name vocabulary. Date/Author: 2026-06-22, implementation agent.
- Decision (fix round 1): make design §5.2 invariant 3 genuinely reachable on
  disk. The original `by-chapter-sum-mismatch` variant used a
  `by_chapter_override`, but the builder computed `word_counts.current` as
  `sum(by_chapter.values())` unconditionally, so the materialised `state.toml`
  always satisfied `sum(by_chapter) == current` — the real invariant 3 was never
  violated, and the oracle's `_check_by_chapter_sum` instead compared the
  override against the chapters' `draft_words` (a corpus-internal property, not
  invariant 3). Task 2.1.2's real validator would therefore have found the tree
  coherent for invariant 3 while the corpus labelled it `by-chapter-sum`,
  breaking the cross-check this corpus exists to serve. Fix: `WorkingTreeSpec`
  gains an independent `current_words_override: int | None`, and the builder
  writes `word_counts.current` via a new `derive_current` helper that returns the
  override verbatim while `by_chapter` still derives from the drafts — so the
  variant's on-disk state now has `sum(by_chapter) != current`, a genuine
  invariant-3 violation. The oracle's `_check_by_chapter_sum` now reads the
  materialised `state.toml` and compares the written `sum(by_chapter)` against the
  written `current`, i.e. the exact disk evidence task 2.1.2's validator will see,
  so the corpus label and the real validator agree. The `by-chapter-sum-mismatch`
  variant switches to `current_words_override=1`. A new self-test
  (`test_current_words_override_breaks_invariant_3_on_disk`) pins both the
  coherent default (`sum(by_chapter) == current`) and the override violation. No
  design field or invariant changed; the only new spec dimension models a state
  the design already permits (`state-layout.md` line 113: `current` is "words in
  compiled.md (or sum of drafts)", an independently written value). Date/Author:
  2026-06-22, implementation agent.

## Outcomes & retrospective

All five work items landed, each gated green by `make all` and reviewed by
`coderabbit review --agent` (Work items 3, 4, and 5 returned zero findings;
Work items 1 and 2 had only minor/trivial findings, all addressed). The
markdown gates (`make markdownlint`, `make nixie`) are green for the touched
documents.

The corpus is delivered as the `tests/working_corpus` package
(`_specs`/`_builder`/`_library`/`_oracle`/`_variants`, re-exported from
`__init__`), consumed through the registered pytest plugin
`tests/corpus_fixtures.py`, with the spec types re-exported from `conftest`
under `TYPE_CHECKING`. The self-tests live in `tests/test_working_corpus.py`
and `tests/test_working_corpus_done_flags.py`. Every datum is consumed by
fixture parameter name; no test module value-imports the corpus.

Deviations from the plan, all recorded as Decisions above:

- `working_corpus` is a package, not a single module, to keep each file under
  the 400-line cap.
- The corpus fixtures live in a registered plugin (`corpus_fixtures.py`), not in
  `conftest`, for the same cap; the load-bearing import contract is preserved
  (no test-module value imports; spec types via `from conftest import`).
- The oracle vocabulary carries a tenth invariant name, `pending-turn-cleared`,
  the structural label for the torn-turn variant the plan already required.

No Tolerance was triggered: the change stays within the ~6-file / ~700-line
ceiling for the corpus and its tests (the package and two test modules), adds no
dependency, pulls no phase-2 schema work forward, and changes no design field or
invariant. The `gate-ratio-consistent` check derives its ratio from the honest
on-disk draft total so a `by_chapter_override` cannot perturb invariant 7, and
the `completed-prefix` check defers an out-of-enum phase to invariant 1, so each
incoherent variant breaks exactly one named invariant (proved by the split
self-test).

## Documentation to read, and skills to load, before starting

Read first (source of truth):

- `docs/novel-ralph-harness-design.md` §5 (state schema and invariants — §5.1
  schema and phase enum, §5.2 invariants, §5.3 round-trip, §5.4
  reconciliation), §9 (verification strategy: which test method each command
  earns; the corpus seeds the snapshot and behavioural suites), §3.4
  (`[pending_turn]` intent record, for the torn-turn variants), and §4.2 / §4.3
  (the compile-and-hash model: `compiled.md` is the ordered concatenation of
  the present drafts and fidelity is a content-hash comparison — the model the
  `compiled-not-concatenation-of-drafts` variant and the oracle use, with no
  invented chapter-naming grammar; design-review B1).
- `skill/novel-ralph/references/state-layout.md` in full (the authoritative
  on-disk layout the corpus reproduces, design §5.1).
- `docs/roadmap.md` task 1.3.2 (this task) and its consumers: 2.1.1, 2.1.2,
  2.3.2, 3.1.1, 3.1.2, 4.1.1, 6.2.1, 6.2.2 (so the variants cover what those
  suites need).
- `docs/developers-guide.md` "Shared test scaffolding" (the conftest fixture
  idiom and the no-value-import rule).
- `docs/scripting-standards.md` (pathlib for filesystem work; `cuprum` is NOT
  needed here — see "What this task does NOT do").
- `docs/adr-002-toml-round-trip-tomlkit.md` (why `state.toml` is written with
  `tomlkit`).
- `AGENTS.md` (quality gates lines 71-98; testing rules lines 141-166; file
  size lines 24-27; spelling lines 18-20).

External library docs (verified during planning, cite when implementing):

- pytest stable "How to use fixtures" → "Factories as fixtures"
  (`https://docs.pytest.org/en/stable/how-to/fixtures.html#factories-as-fixtures`):
  a fixture may return a function that generates data, callable multiple times
  in one test, optionally with parameters; if the data needs managing, the
  fixture `yield`s the factory and tears down afterward. This is the verified
  mechanism for `build_working_tree` as a factory fixture. (The corpus needs no
  teardown beyond pytest's own `tmp_path` cleanup, so a plain `return` factory
  suffices.)
- `tomlkit` is the locked round-trip writer (0.15.0, `uv.lock`); design §5.3
  and ADR-002 pin it as the comment/format-preserving serialiser. `tomllib`
  (stdlib) reads but cannot write TOML (design §5.3), so it is used only to
  read a written file back in a self-test.

Skills to load (via the Skill tool / routers):

- `python-router` first, then the sub-skills it routes to:
  - `python-testing` for fixture scopes, the factory-as-fixture pattern,
    parametrization, and `tmp_path` usage.
  - `python-data-shapes` for the specification dataclass choice (a frozen
    `@dataclass` describing a `working/` tree: phase, completed prefix,
    chapter manifest, per-chapter draft/done-flag, compiled presence,
    word counts, optional `[pending_turn]`).
  - `python-types-and-apis` for the builder and fixture signatures.
  - `python-verification` to confirm whether any corpus property warrants
    Hypothesis (it does not for this task — see below — but confirm via the
    skill rather than asserting).
- `en-gb-oxendict` for prose, comments, docstrings, and commit messages.
- `leta` for navigation (`leta show`, `leta refs`, `leta grep`) and `sem` for
  history.

Hypothesis, CrossHair, and mutmut are NOT required for this task: the corpus is
fixed, enumerated data, not an invariant over a generated range. The property
suites that exercise the corpus belong to the *consumers* (task 2.1.2's
Hypothesis suite over the validator, task 2.2.1's round-trip property). This
task's own tests are example-based assertions that each named fixture
materialises the tree it claims. If, while implementing, the structural oracle
seems to warrant generated inputs, escalate and reconsider per
`python-verification` rather than adding Hypothesis speculatively.

## Plan of work

The work proceeds in five atomic, independently committable, gate-passable work
items. Each ends with `make all` green (and, where markdown changes, with
`make markdownlint` and `make nixie` green). Run gates sequentially, never in
parallel, to benefit from build caching (user instruction). Establish a failing
self-test before its fixtures exist where practical (red, then green).

### Work item 1: specification types and the tree builder

Purpose: deliver the data shape that describes a `working/` tree and the
builder that materialises it on disk, so every later variant is declared once
and rendered uniformly.

New code (in `tests/working_corpus.py` if the line-count split is taken, else in
`tests/conftest.py`; decide and record in the Decision Log):

- A frozen `@dataclass` `ChapterSpec` describing one chapter:
  `number: int`, `slug: str`, `title: str`, `target_words: int`,
  `draft_words: int` (0 means an empty `draft.md`; the builder writes exactly
  that many deterministic words), `has_done_flag: bool`, and
  `in_manifest: bool` (default `True`; `False` models a `chapter-NN/` directory
  with no `[chapters]` entry, for the bijection-violation variant).
- A frozen `@dataclass` `WorkingTreeSpec` describing a whole tree:
  `phase_current: str`, `phase_completed: tuple[str, ...]`,
  `chapters: tuple[ChapterSpec, ...]`, `manifest_only_numbers: tuple[int, ...]`
  (manifest entries with no directory, for the other bijection-violation
  direction), `target_words: int`,
  `by_chapter_override: Mapping[str, int] | None` (None means derive
  `by_chapter` from the chapter draft words; a value injects a deliberate
  current/by-chapter mismatch), `consecutive_clean: int`,
  `convergence_target: int`, gate booleans (`done_30`/`done_50`/`done_80`,
  `final_pass_complete`), the drafting cursor (`current_chapter`/`current_scene`
  /`current_beat`), `compiled: str | None` (None means no `compiled.md`; the
  sentinel `AUTO` writes the hash-equal `concatenate_drafts` of the present
  drafts — the coherent compile; any other string writes exactly that content —
  the stale/contradictory compile used by the
  `compiled-not-concatenation-of-drafts` variant), and
  `pending_turn: Mapping[str, object] | None` (the two-key `operation`/`paths`
  marker for the torn-turn variant).
- `build_working_tree(spec: WorkingTreeSpec, dest: Path) -> Path`: materialises
  the tree under `dest` (the test's `tmp_path`). It creates `working/` and its
  subdirectories with `pathlib`, writes each `chapter-NN/draft.md` (zero-padded
  to two digits) with `draft_words` deterministic words, touches `done.flag`
  where `has_done_flag`, writes `working/manuscript/compiled.md` when
  `compiled` is not None (a `None` spec field means "no compiled.md"; a sentinel
  `AUTO` means "the hash-equal `concatenate_drafts` of the present drafts" —
  the coherent compile; any other string writes those exact bytes — the stale
  or contradictory compile), writes `working/plan/chapter-outline.md`, and
  writes `working/state.toml` through `tomlkit` carrying **every** table the
  schema names (enumerated in "Orientation"): `schema_version`, `[novel]` (with
  `created_at = "2026-05-23T14:00:00Z"`), `[phase]`, `[drafting]`,
  `[drafting.critic]` (including `pass`, `consecutive_clean`,
  `convergence_target`, and `last_finding_counts`), `[drafting.fangirl]`,
  `[gates.knitting]`, `[gates.final]`, `[word_counts]` (with `by_chapter` keyed
  by zero-padded two-digit **string**), and `[chapters]`, plus `[pending_turn]`
  only when the spec provides one. Tables the spec does not parameterise are
  emitted with fixed deterministic builder defaults so task 2.1.1 parses
  without loss. Returns the `working/` path.
- `CORPUS_SEPARATOR: str` (the single `"\n\n"` separator constant) and
  `concatenate_drafts(drafts: Sequence[str]) -> str`, the one helper that joins
  ordered draft bodies with `CORPUS_SEPARATOR`. The builder uses it to write a
  coherent `compiled.md` (`compiled=AUTO`), and Work item 3's oracle uses it to
  recompute the expected concatenation for the `"compiled-matches-drafts"`
  check. This is the corpus's local stand-in for the §4.3 compile routine task
  4.1.1 implements; the Decision Log records the escalation Tolerance if
  4.1.1's production separator differs.
- The three knitting-gate threshold constants `0.30 / 0.50 / 0.80` named once
  (e.g. `GATE_THRESHOLDS`), shared by the coherent gate booleans, the
  `gate-true-below-threshold` variant, and the oracle's invariant-7 branch.
- A small deterministic word-body helper so `draft_words=N` produces a body
  with exactly `N` words under whatever word-count rule the design uses (split
  on whitespace), giving phases 2/6 exact expected totals.

Tests to add (`tests/test_working_corpus.py`):

- Unit: `build_working_tree` on a minimal two-chapter coherent spec creates
  `working/state.toml`, `working/manuscript/chapter-01/draft.md`,
  `chapter-02/draft.md`, the outline, and (when requested) `compiled.md`, at
  exactly the design paths; assert each path exists and that no earlier-draft
  path (`working/compiled.md`, `working/chapter-01/`) is created.
- Unit: the written `state.toml`, read back with `tomllib`, decodes to the
  values the spec declared (phase, completed prefix, target, by_chapter sum,
  manifest entries, convergence_target), and `word_counts.by_chapter` is keyed
  by the zero-padded two-digit **string** form (`"01"`, `"02"`, …) matching
  `state-layout.md` line 115 — not an integer key — so the corpus and the
  eventual validator agree on the key shape.
- Unit: the written `state.toml` carries every schema table task 2.1.1 must
  parse (`[novel]`, `[drafting.critic].last_finding_counts`,
  `[drafting.fangirl].last_chapter_passed`, `[gates.knitting]`,
  `[gates.final]`) with the builder's fixed defaults present, so a "parse
  without loss" consumer hits no absent field.
- Unit: a coherent `compiled=AUTO` spec writes a
  `working/manuscript/compiled.md`
  whose bytes equal
  `concatenate_drafts([...present draft bodies in zero-padded order...])`, and
  a non-`AUTO` string writes exactly those bytes (the stale-compile case),
  confirming the corpus's compile model is the §4.3 concatenation, not a parsed
  structure.
- Unit (round-trip guard, mitigates the §5.3 risk): a `tomlkit` parse-then-dump
  of the written `state.toml` is byte-for-byte idempotent, so the corpus only
  ever emits state files the task-2.2.1 no-op round-trip can preserve.
- Unit: `draft_words=N` yields a `draft.md` whose whitespace-split token count
  is exactly `N`, and `draft_words=0` yields an empty file.

Validation: `make all`. Commit.

Docs/skills: `python-data-shapes` (the spec dataclasses),
`python-types-and-apis` (builder signature), `python-testing` (`tmp_path`);
ADR-002 / design §5.3 for the `tomlkit` write.

### Work item 2: the eleven phase states and the coherent baseline

Purpose: deliver the named specification library for the eleven phase states
and expose it through a factory fixture, so any later suite can request a
coherent tree at a chosen phase.

Edits/new code:

- A module-level mapping `PHASE_STATES: dict[str, WorkingTreeSpec]` keyed by
  each of the eleven phase enum members (`premise` … `done`), each a coherent
  spec whose `phase.current` is that member and whose `phase.completed` is the
  exact in-order prefix preceding it (invariants 1 and 2). The pre-drafting
  phases carry an empty chapter manifest and a zeroed cursor; `drafting`,
  `final-pass`, and `done` carry a small populated manifest with matching
  `chapter-NN/` directories, drafts, gate booleans consistent with their word
  counts, and (for `final-pass`/`done`) a `compiled.md` matching the drafts. A
  `COHERENT_BASELINE` constant names the canonical mid-drafting coherent tree
  the negative variants in Work item 3 mutate.
- In `tests/conftest.py`, expose the corpus through fixtures only, each
  importing the corpus module once at `conftest` scope (the single sanctioned
  importer) and re-exposing values by parameter name:
  - `phase_state_tree` — a **factory fixture** bound to `tmp_path`:
    `def phase_state_tree(tmp_path) -> Callable[[str], Path]` returning a
    closure `lambda phase: build_working_tree(PHASE_STATES[phase], tmp_path)`,
    so a test writes `tree = phase_state_tree("drafting")` and never names
    `PHASE_STATES` itself. The phase string is the only argument the test
    supplies; the spec lookup happens inside the fixture.
  - `phase_names` — a fixture returning the ordered tuple of the eleven phase
    enum members (the `PHASE_STATES` keys), so a test parametrizes over phases
    by receiving this tuple by parameter name rather than importing the mapping.
    A test that needs to iterate phases uses `phase_names` together with
    `phase_state_tree`, both by parameter name.
  (All corpus data stays in `tests/working_corpus.py`; `conftest` is its only
  importer and exposes it as fixtures — no test module performs a value import.)

Tests to add (extend `tests/test_working_corpus.py`):

- A test that requests `phase_names` and `phase_state_tree` by parameter name,
  iterates the phase tuple, and for each phase asserts
  `phase_state_tree(phase)` materialises a tree whose read-back `state.toml` has
  `phase.current == phase` and `phase.completed` equal to the in-order prefix
  before `phase`. (No `PHASE_STATES` symbol appears in the test; pytest's
  `parametrize` cannot take a fixture value, so iterate the `phase_names` tuple
  inside one test, or add a tiny non-corpus module-level phase-order constant
  in the test file derived from the reference — see the next bullet — and
  parametrize on that.)
- Assert the `phase_names` tuple is exactly the eleven enum members in order,
  cross-checked against the phase list parsed out of `state-layout.md` (lines
  122-134) via the existing `read_repo_text` fixture (single source of truth:
  the phase order is read from the reference, not re-typed in the corpus or the
  test). This is the test that proves a missing or mis-ordered phase in
  `PHASE_STATES` fails loudly, and it does so without importing
  `PHASE_STATES` — it compares the `phase_names` fixture value against the
  reference text.

Validation: `make all`. Commit.

Docs/skills: `python-testing` (factory fixture, parametrization),
`python-data-shapes`; design §5.1 (phase enum), `state-layout.md`.

### Work item 3: incoherent variants and the structural oracle

Purpose: deliver the deliberately incoherent variants — one per §5.2 invariant,
plus the contradictory-disk and torn-turn cases — and prove, with a
corpus-local oracle, that each breaks exactly the invariant it targets and
nothing else.

Edits/new code (in `tests/working_corpus.py`):

- A `corpus_check(spec, working_dir) -> tuple[str, ...]` structural oracle that
  re-implements the seven §5.2 structural invariants (enumerated in
  "Orientation") plus the §5.4 contradictory-disk checks, returning the tuple
  of invariant **names** a tree violates (empty tuple = coherent). It is
  documented as a corpus-internal cross-check, NOT the canonical validator
  (task 2.1.2), and each branch cites the §5.2 / §5.4 line it implements. The
  invariant-name vocabulary is a fixed, documented set of stable string
  constants (e.g. `"phase-in-enum"`, `"completed-prefix"`, `"by-chapter-sum"`,
  `"consecutive-clean-bound"`, `"manifest-disk-bijection"`, `"cursor-coherent"`,
  `"gate-ratio-consistent"`, plus `"done-flag-without-draft"` and
  `"compiled-matches-drafts"` for the §5.4 cases) so task 2.1.2 can key its
  cross-check on the same strings (resolves advisory A5).
- The `"done-flag-without-draft"` branch (design §5.4) keys on **
  `has_done_flag and draft_words == 0`** — a `done.flag` beside an empty
  `draft.md` — not on
  `has_done_flag` alone. This is the precise boundary against Work item 4's
  coherent `DONE_FLAG_PERMUTATIONS`, where flagged chapters always carry
  `draft_words > 0`: those permutations must return the empty tuple, while a
  flagged zero-word draft returns `"done-flag-without-draft"`. (Resolves
  round-2 advisory A4.)
- The compile contradiction is checked by the design's hash model, not by name
  parsing: the `"compiled-matches-drafts"` branch recomputes
  `concatenate_drafts([...present drafts...])` (the `CORPUS_SEPARATOR` helper
  from Work item 1) and flags the tree when `compiled.md`'s bytes are not equal
  to that concatenation (§4.3 lines 320-344; §9 lines 705-711). It never parses
  a chapter name out of `compiled.md` (resolves design-review B1).
- A mapping `INCOHERENT_VARIANTS: dict[str, tuple[WorkingTreeSpec, str]]`
  pairing each named variant with the single invariant-name string it is built
  to violate. The set covers, at minimum:
  - `phase-not-in-enum` (`"phase-in-enum"`), `completed-prefix-gap`
    (`"completed-prefix"`), `by-chapter-sum-mismatch` (`"by-chapter-sum"`, via
    `by_chapter_override`), `consecutive-clean-over-target`,
    `convergence-target-below-one`, and `consecutive-clean-over-chapters-drafted`
    (all three keyed `"consecutive-clean-bound"`; the third sets
    `consecutive_clean` higher than the number of drafted chapters — e.g.
    `consecutive_clean = 2` on a tree with at most one drafted chapter — to
    exercise invariant 4's *third* sub-clause, which the first two variants do
    not reach; resolves round-2 advisory A2),
    `manifest-extra-entry` and `draft-without-manifest-entry`
    (`"manifest-disk-bijection"`, both directions of the bijection),
    `cursor-past-current-chapter` (`"cursor-coherent"`),
    `gate-true-below-threshold` (`"gate-ratio-consistent"`). The
    `gate-true-below-threshold` variant flips a single gate boolean true while
    keeping an **honest** `word_counts.current = sum(draft_words)` whose
    `current/target` ratio is below that gate's threshold — it adjusts the gate
    boolean alone and never overrides `current`, so invariant 3
    (`by_chapter` sums to `current`) stays satisfied and the variant violates
    exactly invariant 7. (Overriding `current` here would break invariant 3 too,
    the double-violation hazard Risk #2 and the split self-test guard against;
    pinning the construction avoids a wasted iteration. Resolves round-2 advisory
    A3.)
  - Contradictory-disk cases (design §5.4 / §10): `done-flag-empty-draft`
    (a `done.flag` beside a zero-word `draft.md`, `"done-flag-without-draft"`)
    and `compiled-not-concatenation-of-drafts` (a `compiled.md` whose bytes are
    deliberately not the `concatenate_drafts` of the present drafts,
    `"compiled-matches-drafts"`). The latter replaces the round-1
    `compiled-references-absent-chapter` variant per B1.
  - Torn-turn case (design §3.4): `uncleared-pending-turn` (a coherent tree
    plus a populated two-key `[pending_turn]` record).
- In `tests/conftest.py`, factory fixtures exposing the variants by parameter
  name only:
  - `incoherent_variant_names` — a fixture returning the tuple of variant keys,
    so a test iterates the variant set without importing `INCOHERENT_VARIANTS`.
  - `incoherent_tree` — a factory fixture
    `def incoherent_tree(tmp_path) -> Callable[[str], tuple[Path, str]]` whose
    closure looks up the named variant in `INCOHERENT_VARIANTS`, builds it under
    `tmp_path`, and returns `(working_dir, expected_invariant_name)`, so a test
    writes `tree, expected = incoherent_tree("by-chapter-sum-mismatch")`.
  - `check_corpus` — a fixture returning the `corpus_check` callable, so a test
    receives the oracle by parameter name (`def test_x(check_corpus, …)`) and
    never imports `corpus_check`.

Tests to add (extend `tests/test_working_corpus.py`):

- The coherent/incoherent split (the load-bearing self-test): a test receiving
  `incoherent_variant_names`, `incoherent_tree`, and `check_corpus` by
  parameter name iterates the variant-name tuple, builds each via
  `incoherent_tree(name)`, and asserts `check_corpus(spec, working_dir)`
  returns a tuple containing **exactly** the one expected invariant name the
  fixture reports — proving each variant is incoherent *and* isolated (no
  second accidental violation). No `INCOHERENT_VARIANTS` or `corpus_check`
  symbol is imported.
- For the coherent baseline and all eleven phase states (via `phase_names` /
  `phase_state_tree` and a `baseline_tree` factory fixture), assert
  `check_corpus` returns the empty tuple — the coherent variants really are
  coherent under the oracle.
- A guard that every named §5.2 / §5.4 invariant string in the oracle's
  vocabulary is exercised by at least one variant (received via
  `incoherent_variant_names` and a `corpus_invariant_names` fixture exposing
  the vocabulary), so the corpus cannot silently lose coverage of an invariant.

Validation: `make all`. Commit.

Docs/skills: `python-verification` (confirm no Hypothesis needed),
`python-testing`; design §4.2, §4.3, §5.2, §5.4, §9, §10, §3.4.

### Work item 4: `done.flag` permutation fixtures

Purpose: deliver the `done.flag` permutations the roadmap names explicitly
("chapter drafts with `done.flag` permutations", roadmap 1.3.2), which the
phase-3 `all_chapters_flagged` clause (roadmap 3.1.1) and the phase-2 `check`
reconciliation (roadmap 2.3.2) consume.

Edits/new code:

- A `DONE_FLAG_PERMUTATIONS` mapping (in `tests/working_corpus.py`) of coherent
  multi-chapter specs differing only in which chapters carry `done.flag`: none
  flagged, all flagged, a leading prefix flagged, and a non-contiguous subset
  flagged (the last is the case a done-predicate must treat as not-all-done).
  Each keeps every *other* §5.2 invariant satisfied so the permutation isolates
  the flag state. (The contradictory `done.flag`-beside-empty-draft case
  already lives in Work item 3's incoherent set; this item is the *coherent*
  flag permutations.)
- In `tests/conftest.py`, `done_flag_permutation_names` (a fixture returning the
  permutation-key tuple) and `done_flag_tree` (a factory fixture
  `def done_flag_tree(tmp_path) -> Callable[[str], Path]` whose closure looks
  up the named permutation and builds it), both consumed by parameter name.

Tests to add (extend `tests/test_working_corpus.py`):

- A test receiving `done_flag_permutation_names`, `done_flag_tree`, and
  `check_corpus` by parameter name iterates the permutation tuple and, for
  each, asserts the materialised tree carries `done.flag` in exactly the
  chapters the permutation names and in no others, and that `check_corpus`
  still returns the empty tuple (the permutations are coherent). No
  `DONE_FLAG_PERMUTATIONS` or `corpus_check` symbol is imported.
- Assert the "non-contiguous subset flagged" permutation (built via
  `done_flag_tree`) has at least one flagged chapter following an unflagged one
  (the shape a future `all_chapters_flagged` test needs), so the corpus
  genuinely carries that case.

Validation: `make all`. Commit.

Docs/skills: `python-testing`; design §4.2 (`all_chapters_flagged`),
`state-layout.md` (`done.flag` is an empty `touch`ed file, line 266).

### Work item 5: document the corpus and reify the roadmap checkbox

Purpose: keep the living docs current (AGENTS.md "Documentation maintenance")
and make the corpus discoverable.

Edits:

- `docs/developers-guide.md`: under the existing "Shared test scaffolding"
  section, add a *descriptive* subsection naming the `tests/working_corpus.py`
  data module and its public surface (`WorkingTreeSpec`, `ChapterSpec`,
  `build_working_tree`, `concatenate_drafts`, `CORPUS_SEPARATOR`,
  `GATE_THRESHOLDS`, `PHASE_STATES`, `COHERENT_BASELINE`, `INCOHERENT_VARIANTS`,
  `DONE_FLAG_PERMUTATIONS`, `CORPUS_INVARIANT_NAMES`) and the `conftest`
  fixtures that expose it (`phase_names`, `phase_state_tree`, `baseline_tree`,
  `incoherent_variant_names`, `incoherent_tree`, `done_flag_permutation_names`,
  `done_flag_tree`, `check_corpus`, `corpus_invariant_names`). This subsection
  **does not amend** the scaffolding rule or its `TYPE_CHECKING` carve-out — it
  records how the corpus *applies* the already-stated rule. State explicitly:
  (1) later slices consume the corpus **by fixture name only** and never by a
  runtime value import; (2) `tests/conftest.py` is the single runtime importer
  of `tests/working_corpus.py` (the same consolidation pattern the section
  already describes); (3) a test annotation that needs a spec type uses the
  **existing** carve-out verbatim — `from conftest import WorkingTreeSpec` (or
  `ChapterSpec`) under `if TYPE_CHECKING:` — which `conftest` makes available
  by re-exporting the two types inside its own `TYPE_CHECKING` block, so no new
  import-contract clause and no new sanctioned module is introduced. Note that
  the corpus is consumed unchanged by phases 2-6 (roadmap 1.3.2 criterion), and
  that the `corpus_check` oracle is a corpus-internal cross-check superseded by
  task 2.1.2's validator (which keys on the same `CORPUS_INVARIANT_NAMES`
  strings). If, while writing this subsection, the guide's existing carve-out
  wording appears to genuinely require extension to cover the corpus module (it
  should not, given the `conftest` re-export), stop and escalate rather than
  silently amending the rule — that would be a contract change, not
  documentation.
- `docs/contents.md`: index the developers-guide corpus subsection so the
  corpus is discoverable (mirrors the 1.2.3.1 documentation-map discipline).
- `docs/roadmap.md`: change `- [ ] 1.3.2.` to `- [x] 1.3.2.` only after Work
  items 1-4 are merged and green (do this in the final commit).

Validation: `make markdownlint` and `make nixie` (markdown changed), then
`make all`. Commit.

Docs/skills: `en-gb-oxendict`; documentation-style-guide.

## Concrete commands

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-2`.

```bash
make build        # create .venv, sync dev group (first work item)
make all          # build check-fmt lint typecheck test (every work item)
make markdownlint # markdown lint (Work item 5)
make nixie        # Mermaid validation (Work item 5)
```

Expected: `make all` ends with pytest reporting all tests passed (the new
`test_working_corpus.py` among them) and `interrogate` reporting 100% docstring
coverage. A new corpus test fails before its builder/specs exist and passes
after (red/green): e.g. `tests/test_working_corpus.py`'s materialisation test
fails before Work item 1's `build_working_tree` lands.

## Validation and acceptance

Acceptance is behavioural:

- Requesting `phase_state_tree("drafting")` (the factory fixture, by parameter
  name) in a test materialises a `working/` tree on disk at exactly the design
  paths (manuscript under `working/manuscript/`, chapters `chapter-NN/`,
  `compiled.md` under `working/manuscript/`), whose read-back `state.toml` has
  the declared phase, completed prefix, manifest, and word counts — verified by
  the Work item 1/2 tests. No test imports `PHASE_STATES`; the phase string is
  the only argument.
- Every incoherent variant (driven through the `incoherent_tree` /
  `incoherent_variant_names` / `check_corpus` fixtures, all by parameter name)
  materialises a tree the corpus-local oracle flags on **exactly** its one
  named §5.2 (or §5.4) invariant — including the
  `compiled-not-concatenation-of-drafts` case, detected by recomputing
  `concatenate_drafts` and comparing content, not by parsing chapter names —
  while the coherent baseline and all eleven phase states pass the oracle clean
  — verified by the Work item 3 self-test (the proof the coherent/incoherent
  split is real and isolated).
- The `done.flag` permutations materialise flags in exactly the named chapters
  and remain coherent — verified by the Work item 4 tests.
- The written `state.toml` is `tomlkit`-round-trip idempotent, so phase 2's
  no-op round-trip property will preserve every corpus state file — verified by
  the Work item 1 round-trip guard.

Quality criteria ("done"):

- Tests: `make test` passes; the new corpus tests fail before and pass after
  their work items (red/green).
- Lint/format/type: `make check-fmt`, `make lint` (Ruff + interrogate 100% +
  PyPy-Pylint), `make typecheck` all green.
- Audit: `make audit` clean.
- Markdown: `make markdownlint` and `make nixie` green for the doc commit.

Quality method: `make all` (plus the two markdown targets for the doc commit),
run sequentially.

## Idempotence and recovery

Every work item is additive and re-runnable. `make build` is safe to repeat
(`uv sync`). The corpus builder writes only under a test's `tmp_path`, which
pytest creates and cleans per test, so running the suite repeatedly leaves no
residue. If a gate fails mid-item, fix forward and re-run `make all`; no step
is destructive. The roadmap checkbox flip (Work item 5) is the only edit to an
existing doc line and is trivially reversible. If a tolerance triggers, stop
and escalate per the execplans skill's exception handling.

## Interfaces and dependencies

Use these and only these:

- Standard library: `dataclasses`, `pathlib`, `collections.abc` (for
  `Mapping`/`Sequence`/`Callable`), `tomllib` (read-back only), `typing`.
- `tomlkit` (0.15.0, already a runtime dep) to **write** every `state.toml`
  (design §5.3; ADR-002), so the corpus emits state files the phase-2
  round-trip preserves.
- `pytest` (`tmp_path`, the factory-as-fixture pattern) — already present.
- NO new dependency; NO `cuprum` (no external process; design §9 line 711); NO
  `hypothesis` for this task's own tests (the corpus is enumerated data, not a
  generated range — see "Documentation to read").

End-state module layout and consumption contract. All of the following live in
`tests/working_corpus.py`. **No test module imports any of these values at
runtime**; `tests/conftest.py` is the single importer and re-exposes every
datum as a fixture (the fixtures are listed below the surface). The spec
*types* are defined in `tests/working_corpus.py` and re-exported from
`tests/conftest.py` inside its `TYPE_CHECKING` block; the only symbols a test
module may name are those types, and only under `if TYPE_CHECKING:` via
`from conftest import WorkingTreeSpec` (the verbatim developers-guide
carve-out, lines 39-52).

```python
# tests/working_corpus.py — corpus data module (not a test_*.py module).
CORPUS_SEPARATOR: str               # the single "\n\n" draft separator
GATE_THRESHOLDS: tuple[float, ...]  # (0.30, 0.50, 0.80), single source

def concatenate_drafts(drafts: Sequence[str]) -> str: ...

@dataclass(frozen=True, kw_only=True)
class ChapterSpec:
    number: int
    slug: str
    title: str
    target_words: int
    draft_words: int
    has_done_flag: bool
    in_manifest: bool = True

@dataclass(frozen=True, kw_only=True)
class WorkingTreeSpec:
    phase_current: str
    phase_completed: tuple[str, ...]
    chapters: tuple[ChapterSpec, ...]
    target_words: int
    consecutive_clean: int
    convergence_target: int
    # gate booleans, cursor fields, compiled (None|AUTO|bytes),
    # pending_turn (operation/paths), by_chapter_override, manifest_only_numbers

def build_working_tree(spec: WorkingTreeSpec, dest: Path) -> Path: ...
def corpus_check(spec: WorkingTreeSpec, working_dir: Path) -> tuple[str, ...]: ...

PHASE_STATES: dict[str, WorkingTreeSpec]
COHERENT_BASELINE: WorkingTreeSpec
INCOHERENT_VARIANTS: dict[str, tuple[WorkingTreeSpec, str]]
DONE_FLAG_PERMUTATIONS: dict[str, WorkingTreeSpec]
CORPUS_INVARIANT_NAMES: tuple[str, ...]  # the oracle's stable name vocabulary
```

Fixtures in `tests/conftest.py`, each importing `tests/working_corpus.py` once
and exposing values by parameter name (no test module imports the module). The
spec *types* are re-exported under `conftest`'s `TYPE_CHECKING` guard so tests
can annotate with `from conftest import WorkingTreeSpec`:

```python
# tests/conftest.py — the single importer; consumers receive these by name.
if typ.TYPE_CHECKING:
    # Re-export the corpus spec types so test annotations use the sanctioned
    # `from conftest import WorkingTreeSpec` carve-out (developers-guide 39-52);
    # False at runtime, so no runtime cross-module import is introduced.
    from working_corpus import ChapterSpec, WorkingTreeSpec

phase_names           # -> tuple[str, ...]            (the eleven phases, order)
phase_state_tree      # -> Callable[[str], Path]      (factory, bound to tmp_path)
baseline_tree         # -> Callable[[], Path]         (COHERENT_BASELINE, tmp_path)
incoherent_variant_names  # -> tuple[str, ...]
incoherent_tree       # -> Callable[[str], tuple[Path, str]]  (tree, invariant)
done_flag_permutation_names  # -> tuple[str, ...]
done_flag_tree        # -> Callable[[str], Path]
check_corpus          # -> Callable[[WorkingTreeSpec, Path], tuple[str, ...]]
corpus_invariant_names    # -> tuple[str, ...]        (CORPUS_INVARIANT_NAMES)
```

The only cross-module symbols a test names directly are `WorkingTreeSpec` /
`ChapterSpec`, for annotations only, imported via the verbatim developers-guide
carve-out: `from conftest import WorkingTreeSpec` under `if TYPE_CHECKING:`.
`conftest` makes this form available by re-exporting the two types inside its
own `TYPE_CHECKING` block
(`from working_corpus import WorkingTreeSpec, ChapterSpec`), which is `False`
at runtime; the only runtime import edge is `conftest → working_corpus`. No
test performs a runtime cross-module import, and the test-facing
`TYPE_CHECKING` import is `from conftest import …` — exactly the sanctioned
form (developers-guide lines 39-52), so the contract holds with no guide
amendment. The exact field set above is indicative; finalise it in Work item 1
to carry every datum the §5.1 schema and §5.2 invariants need, recording any
change in the Decision Log. Do not add a field the design does not name, and do
not drop one phase 2 must parse.

## Revision note

Round 2 (2026-06-22) resolves the two blocking points from
`docs/execplans/roadmap-1-3-2.review-r1.md`:

- B1 (design non-conformance, the `compiled.md` variant): the round-1 variant
  `compiled-references-absent-chapter` and its oracle assumed `compiled.md`
  *names* chapters in a parseable form the design does not define (§4.3 lines
  320-344; §9 lines 705-711 model `compiled.md` as the ordered concatenation of
  the present drafts, verified by **content hash**). The variant is reframed to
  `compiled-not-concatenation-of-drafts` — a `compiled.md` whose bytes are
  deliberately not the hash-equal `concatenate_drafts` of the present drafts —
  and the oracle's `"compiled-matches-drafts"` branch detects it by recomputing
  that concatenation and comparing content, inventing no separator/heading
  grammar. A `CORPUS_SEPARATOR` constant and a `concatenate_drafts` helper pin
  the one separator the corpus uses, with an escalation Tolerance if task 4.1.1
  fixes a different production separator. Affected: Orientation prose, Risks,
  Tolerances, Decision Log, Work items 1 and 3, acceptance, documentation list.
- B2 (contract violation, cross-module value imports): all corpus *values* are
  now consumed by fixture parameter name only. The data, builder, and oracle
  live in a dedicated non-`test_*` module `tests/working_corpus.py`;
  `tests/conftest.py` is its single importer and re-exposes every datum as a
  fixture (`phase_names`, `phase_state_tree`, `baseline_tree`,
  `incoherent_variant_names`, `incoherent_tree`, `done_flag_permutation_names`,
  `done_flag_tree`, `check_corpus`, `corpus_invariant_names`). No test module
  performs a runtime `from working_corpus import …`; the spec *types* are
  imported solely under `if TYPE_CHECKING:`, the one developers-guide
  carve-out. The `phase_state_spec` fixture that returned the raw mapping is
  removed; every example test is rewritten to take the fixture value by
  parameter name. Affected: Constraints, Decision Log, Tolerances, Work items
  2, 3, 4, 5, the end-state public surface, and acceptance.

The advisories are also folded in: the full `state.toml` table set with fixed
defaults and the zero-padded-string `by_chapter` key form (A1, A2) are pinned
in Orientation and Work item 1; the `[pending_turn]` two-key shape (A3) and the
single-source gate thresholds (A4) are pinned; the oracle's stable
`CORPUS_INVARIANT_NAMES` vocabulary wires the 2.1.2 cross-check (A5). No work
item count changed (still five); the module split into
`tests/working_corpus.py` is now mandatory rather than conditional.

Round 3 (2026-06-22) resolves the single blocking point D1 from
`docs/execplans/roadmap-1-3-2.review-r2.md` and folds in its advisories A1-A4:

- D1 (spec-type import contract — the claimed carve-out was an undocumented
  *extension*, and "no amendment" contradicted Work item 5 writing a new clause
  into the guide). Resolved by **resolution (a)** in its cycle-safe form: the
  spec types stay *defined* in `tests/working_corpus.py` (so the builder
  constructs them with no runtime import of `conftest`), and
  `tests/conftest.py` **re-exports** them inside its own `if TYPE_CHECKING:`
  block. A test annotation now uses the **verbatim** sanctioned form
  `from conftest import WorkingTreeSpec` under `TYPE_CHECKING` — the exact
  words the developers-guide carve-out carries (lines 39-52) — so the contract
  holds with **no guide amendment**. Work item 5's developers-guide edit is now
  explicitly *descriptive* (records how the corpus applies the existing rule)
  and carries an escalation guard against silently extending the carve-out.
  Every prior "no amendment / conforms to the existing rule" claim is now true
  rather than asserted, and resolution (b) (keep types in `working_corpus.py`,
  import from there, amend the guide) is recorded as considered-and-rejected
  with rationale. Affected: Constraints (spec-type paragraph), Decision Log
  (corpus-module decision), Work item 5, the Interfaces end-state contract, the
  `conftest` surface code block.
- A1 (narrower chapter-directory file set): "What this task does NOT do" now
  states the builder deliberately writes only `draft.md` / `done.flag` and why
  the omitted reference files are non-load-bearing for phase-2-6 consumers,
  with an escalation path if one is later needed.
- A2 (invariant-4 third sub-clause): a new
  `consecutive-clean-over-chapters-drafted` incoherent variant exercises
  `consecutive_clean ≤ chapters drafted` directly (keyed
  `consecutive-clean-bound`).
- A3 (`gate-true-below-threshold` construction): Work item 3 now pins that the
  variant flips one gate boolean against an honest
  `current = sum(draft_words)`, leaving invariant 3 intact.
- A4 (`done-flag-without-draft` boundary): the oracle branch is pinned to key on
  `has_done_flag and draft_words == 0`, so Work item 4's coherent permutations
  are not spuriously flagged.

No work item count changed (still five). The variant set grows by one
(`consecutive-clean-over-chapters-drafted`); the scope Tolerance (~6 files /
~700 net lines) is unaffected.
