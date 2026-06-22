# Implement the typed `state.toml` schema and the phase enum

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

This plan delivers the typed in-memory representation of `state.toml` — the
harness's primary on-disk memory — together with the eleven-member phase enum
that orders the novel's lifecycle. After this change, a developer (and every
later command in vertical slice 1: `novel-state check`, the `tomlkit`
round-trip, the done predicate, the recount logic) can parse any coherent
`state.toml` produced by the test corpus into a frozen, fully typed Python
object without loss, and can name the phases through a single closed enum rather
than bare strings scattered across the codebase.

The observable outcome has two complementary tests, because the corpus surface
makes exactly one of them possible at exact-value resolution and the other
possible only coarsely (see the Decision Log entry "without-loss test is split
in two", and the corpus-surface constraint below):

1. A **coverage pass** over every coherent tree the §1.3.2 corpus materialises —
   all eleven phase states plus the mid-drafting baseline, delivered by the
   `coherent_oracle_cases` fixture — asserting each `state.toml` parses into a
   `State` *without raising*, that `phase.current` and every `phase.completed`
   entry resolve to `Phase` members, that the `[chapters]` manifest is present
   and in ascending `number` order, and that `pending_turn is None` on these
   settled trees. This is the breadth guarantee: all eleven phases + baseline
   decode.
2. An **exact without-loss pass** over **specs the test authors itself** through
   the `make_working_tree_spec` / `make_chapter_spec` constructors and the
   `build_tree` fixture (the established pattern in
   `tests/test_working_corpus.py::test_state_decodes_to_declared_values`,
   lines 103-122). Because the test hand-builds the spec, it knows every
   expected value — including `word_counts.current`, the `by_chapter` mapping,
   `convergence_target`, distinct non-zero `last_finding_counts`, and the
   `[chapters]` manifest — and asserts each field on the parsed `State` equals
   the value it declared. This is the depth guarantee: every field is parsed
   into the right attribute, with no transposition.

The phase enum's membership and order are asserted against the corpus's
`phase_names` fixture. No CLI, no validation, and no writing are in scope here:
this task produces the *shape* the validator (2.1.2) and the round-trip helper
(2.2.1) will consume.

This split is forced by the corpus contract, not a convenience: `word_counts.`
`current` and `by_chapter` are **derived** values (`derive_current` /
`derive_by_chapter`, `tests/working_corpus/_specs.py:228-253`), not fields on
`WorkingTreeSpec`. The functions that compute them are **not** among the fifteen
sanctioned corpus fixtures (developers-guide lines 103-107), and the
developers-guide bars consuming the corpus by runtime value import (lines 31-32,
96-97). So the exact value of `current`/`by_chapter` for a *library* tree cannot
be named in a test without breaching the corpus contract; only a tree the test
authored itself carries values the test knows. The coverage pass therefore
asserts a coarse, derivation-free property over the library trees, and the
exact pass asserts the full without-loss criterion over test-authored trees.
Wanting exact-value coverage over the *library* trees would require exposing
`derive_*` as fixtures — a corpus-fixture surface change, which is an escalation
under the Tolerances below, not something this task does.

You can see it working by running, from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-1`:

```bash
make test
```

and observing the new tests `tests/test_state_schema.py` pass. Before the
implementation lands they fail at import (the module does not exist); after, they
pass.

## Context and orientation

You are working inside the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-1`, on branch
`roadmap-2-1-1`. Do every edit here; never touch the control worktree at
`/data/leynos/Projects/novel-ralph-skill`.

Read these before starting, in order:

1. `docs/novel-ralph-harness-design.md` §5.1 (schema and phase enum) — the
   authoritative definition of what this task models. Note the three added
   fields and the eleven-member enum.
2. `docs/novel-ralph-harness-design.md` §8 — the defects the rebuild corrects;
   specifically the dead per-chapter `plan.md` reference this schema must omit.
3. `skill/novel-ralph/references/state-layout.md` — the authoritative on-disk
   layout and the concrete `state.toml` example the schema mirrors. The §5.1
   schema *follows this file exactly* except for the three added fields and the
   omitted `plan.md`.
4. `docs/adr-002-toml-round-trip-tomlkit.md` — why writes go through `tomlkit`
   (relevant to 2.2.1, not this task; this task only *reads*).
5. `docs/developers-guide.md` "State and on-disk layout" and "Shared test
   scaffolding" sections.
6. `AGENTS.md` — code style, the 400-line file cap, en-GB Oxford spelling, the
   testing rules, and the quality gates.

Key existing files you will mirror or consume:

- `novel_ralph_skill/contract/exit_codes.py` — the house style for an enum:
  `import enum`, `class ExitCode(enum.IntEnum)`, a class docstring, and a
  docstring on every member. Your phase enum follows this exactly, as a
  `enum.StrEnum`.
- `novel_ralph_skill/contract/envelope.py` — the house style for an immutable
  domain object: `dataclasses.dataclass(frozen=True, kw_only=True)` with a numpy
  docstring enumerating every attribute. Your schema dataclasses follow this.
- `tests/working_corpus/_specs.py`, `_library.py`, `_variants.py`,
  `_builder.py`, `_oracle.py` — the §1.3.2 corpus. `_specs.py` documents every
  field the builder writes into `state.toml`; this is your field inventory. The
  corpus is "expressed as plain `tomlkit` data so the typed schema (roadmap task
  2.1.1) … can wrap it unchanged" (`_specs.py` module docstring) — i.e. this
  task is exactly the wrapper the corpus was built to be consumed by.
- `tests/corpus_fixtures.py` — the pytest plugin exposing the corpus by fixture
  name. Your test consumes these fixtures: `phase_names`, `phase_state_tree`,
  `baseline_tree`, `coherent_oracle_cases`, `make_working_tree_spec`,
  `make_chapter_spec`, `build_tree`, `incoherent_variant_names`,
  `incoherent_tree` (the last two reach the `uncleared-pending-turn` variant,
  the only coherent-schema carrier of a populated `[pending_turn]`).
- `tests/conftest.py` — re-exports the corpus spec *types* under its
  `TYPE_CHECKING` guard, so a test annotation uses
  `from conftest import WorkingTreeSpec` (developers-guide "Shared test
  scaffolding").

Definitions of terms used below:

- **Phase enum**: the closed, ordered set of eleven lifecycle phases
  (`premise` … `done`).
- **Schema**: the set of frozen dataclasses that mirror the `state.toml` tables.
- **Parse / decode at the boundary**: read the TOML into a plain mapping with the
  standard-library `tomllib`, then construct the typed objects from that mapping
  in one place, so no raw `dict[str, object]` leaks inward (python-data-shapes
  "parse to a schema type at the boundary").
- **Without loss**: every value present in the materialised `state.toml`
  reappears, equal, on the typed object.

### The schema, field by field (from §5.1 and `state-layout.md`)

The §5.1 schema is `state-layout.md`'s structure, minus the dead per-chapter
`plan.md`, plus three fields. Concretely the tables are:

- top-level `schema_version` (int, currently `1`).
- `[novel]`: `title` (str), `slug` (str), `target_word_count` (int),
  `created_at` (str, an RFC 3339 timestamp kept as a string — the schema does
  not parse it to a `datetime`, matching the corpus which writes the fixed
  literal `"2026-05-23T14:00:00Z"`; see Decision Log).
- `[phase]`: `current` (a **phase enum** member) and `completed` (an ordered
  sequence of phase enum members).
- `[chapters]` — **added field**: the chapter manifest, an ordered record of
  each planned chapter, each carrying `number` (int), `slug` (str), `title`
  (str), and `target_words` (int). The corpus writes this from `ChapterSpec`;
  see `_builder.py` for the exact on-disk table shape, which Work item 2 pins.
- `[drafting]`: `current_chapter`, `current_scene`, `current_beat` (ints — the
  cursor).
- `[drafting.critic]`: `pass` (int), `consecutive_clean` (int),
  `convergence_target` (int — **added field**, default 1), and
  `last_finding_counts` (a record of `blocker`/`major`/`minor`/`taste` ints).
- `[drafting.fangirl]`: `last_chapter_passed` (int).
- `[gates.knitting]`: `done_30`, `done_50`, `done_80` (bools).
- `[gates.final]`: `final_pass_complete` (bool).
- `[word_counts]`: `target` (int), `current` (int), `by_chapter` (a mapping from
  the zero-padded two-digit chapter-string to an int word count).
- `[pending_turn]` — **added field**: present only mid-write, an intent record
  carrying `operation` (str) and `paths` (a sequence of str). Optional; absent on
  a settled state.

The dead per-chapter `plan.md` reference (`state-layout.md:38`, §8) is **not** a
schema field and must not appear.

The exact on-disk key names and table nesting the corpus emits are the ground
truth: Work item 2 reads `tests/working_corpus/_builder.py` and pins the schema's
keys to exactly what the builder writes, so the parser and the fixtures cannot
drift. Where the design prose and the builder disagree on a key name, the builder
wins for this task (it is what the fixtures actually materialise) and the
discrepancy is recorded in `Surprises & Discoveries` and raised — the design is
the longer-term source of truth and a mismatch is a real finding, not something
to paper over.

## Constraints

- Work exclusively in the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-1`. Never edit
  the control worktree.
- All prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`) per AGENTS.md and the `en-gb-oxendict` skill, except
  references to external APIs.
- No single code file exceeds 400 lines (AGENTS.md). The schema and the enum are
  split across small modules if needed; the schema dataclasses live in their own
  module under `novel_ralph_skill/state/`.
- The schema is **read-only** here. This task introduces no writing, no
  `tomlkit` mutation, no CLI, and no validation logic. Writing is 2.2.1;
  validation is 2.1.2; the CLI is 2.2.2. Do not pre-build them.
- Do **not** add a new runtime dependency. `msgspec` is referenced only as an
  import-convention alias in `pyproject.toml` and is **not** in `uv.lock`; using
  it would be a new dependency (a Tolerance breach). The schema uses
  standard-library `dataclasses` and `enum`, and reads with standard-library
  `tomllib` (already used in `tests/conftest.py` and `tests/test_working_corpus.py`).
- The phase enum members and their order are exactly the eleven in §5.1
  (`premise`, `treatment`, `characters`, `conflict-analysis`, `setting`,
  `reader-fit`, `stc`, `chapter-planning`, `drafting`, `final-pass`, `done`),
  with the kebab-case *values* the corpus writes and `state-layout.md` documents.
- The schema must omit the dead per-chapter `plan.md` field (§8).
- **Corpus surface is fixture-only.** Tests consume the corpus through the
  fifteen sanctioned fixtures named in the developers-guide (lines 103-107):
  `make_chapter_spec`, `make_working_tree_spec`, `build_tree`, `concatenate`,
  `compile_probe`, `phase_names`, `phase_state_tree`, `baseline_tree`,
  `coherent_oracle_cases`, `incoherent_variant_names`, `incoherent_tree`,
  `done_flag_permutation_names`, `done_flag_tree`, `check_corpus`,
  `corpus_invariant_names`. A test must **not** import any corpus value at
  runtime — in particular it must not import `derive_current` /
  `derive_by_chapter` or any other `working_corpus` symbol to source an expected
  value (developers-guide lines 31-32, 96-97). Spec *types* may be imported only
  under the `TYPE_CHECKING` carve-out (`from conftest import WorkingTreeSpec`).
- Member documentation form: each `Phase` and `ExitCode`-style enum member
  carries a **string-literal docstring on the line after the member**
  (`PREMISE = "premise"` then `"""Premise capture; …"""`), exactly as
  `novel_ralph_skill/contract/exit_codes.py` does. A `#` comment does **not**
  satisfy interrogate's per-member coverage at `fail-under = 100` and must not
  be used in its place.
- Public schema and enum names are stable once introduced; `novel-state check`
  (2.1.2), the round-trip (2.2.1), and the done predicate all import them.
- Quality gates (AGENTS.md): `make check-fmt`, `make lint` (ruff + interrogate
  100% docstring coverage + pylint-pypy), `make typecheck` (`ty`), `make test`,
  `make audit` must all pass before each commit. `make all` runs the build,
  format check, lint, typecheck, and test in sequence. This task touches no
  Markdown except this plan, so `make markdownlint` and `make nixie` are run only
  on commits that touch Markdown (this plan's commits).

## Tolerances (exception triggers)

- Scope: if implementation requires changing more than 6 files or more than ~450
  net lines of code, stop and escalate.
- Interface: if a public API beyond the new `novel_ralph_skill/state/` surface
  must change (e.g. the envelope, the contract package, the corpus modules),
  stop and escalate.
- Dependencies: if any new external dependency (notably `msgspec`) appears
  necessary, stop and escalate — do not add it.
- Corpus: if delivering the parse requires editing any
  `tests/working_corpus/*` module or `tests/corpus_fixtures.py` (rather than
  consuming them unchanged), stop and escalate; the corpus is a frozen contract
  this task wraps, not modifies.
- Schema/builder mismatch: if the schema cannot parse a corpus tree because the
  builder emits a key the design did not name (or vice versa), stop, record it in
  `Surprises & Discoveries`, and escalate rather than silently reshaping either
  side.
- Iterations: if the gated test suite still fails after 3 fix attempts on a work
  item, stop and escalate.
- Ambiguity: if the design and the builder disagree on a field's name, type, or
  nesting in a way that materially changes the schema, present both and escalate.

## Risks

- Risk (severity medium, likelihood medium): the design prose (§5.1) and the
  corpus builder (`tests/working_corpus/_builder.py`) disagree on an exact TOML
  key name or table nesting for an added field (`[chapters]`,
  `convergence_target`, `[pending_turn]`). Mitigation: Work item 1 reads the
  builder first and pins the schema keys to what it actually writes; the parse
  test then exercises every corpus tree, so any mismatch fails loudly rather than
  silently. Record the authoritative key set in the schema module's docstring
  with the builder line cited.
- Risk (severity medium, likelihood medium): the `[chapters]` manifest shape is
  under-specified — the design calls it "an ordered record of each planned
  chapter" without pinning whether the builder emits an array of tables, a
  table-of-tables keyed by chapter, or a single table. Mitigation: Work item 1
  reads `_builder.py` to pin the exact shape before the dataclass is written;
  the schema mirrors whatever the builder emits, and the parse test asserts the
  order is preserved.
- Risk (severity low, likelihood low): a `tomllib`-decoded value's Python type
  (for example an inline table, or `by_chapter` keys) does not match the
  dataclass field type, so the parse either raises or silently coerces.
  Mitigation: the boundary parser constructs each field explicitly with the
  expected type; the parse test asserts equality against the corpus's source
  values, catching any coercion.
- Risk (severity high, likelihood high): the without-loss test is written to
  assert exact `word_counts.current`/`by_chapter` values over the *library*
  trees (`coherent_oracle_cases`), which forces a forbidden runtime import of the
  `derive_current`/`derive_by_chapter` helpers (they are not sanctioned fixtures;
  developers-guide lines 103-107, 31-32). Mitigation: Work item 3 splits the
  tests — a coverage pass over the library trees asserts only derivation-free
  properties (parses, phases resolve, manifest ascending, `pending_turn is
  None`), while the exact without-loss assertions run over test-authored specs
  built through `make_working_tree_spec`/`make_chapter_spec`/`build_tree`, whose
  values the test owns. No corpus value is imported at runtime; the corpus
  surface stays fixture-only.
- Risk (severity medium, likelihood medium): a field-transposition bug
  (`target_words` ↔ `number`, or one `last_finding_counts` count onto another)
  parses without error and passes a test that uses indistinguishable values.
  Mitigation: the 3b spec uses distinct `slug`/`title`/`number`/`target_words`
  per chapter, and 3c asserts distinct non-zero `last_finding_counts`
  (`0/2/4/7`) through a direct `parse_state` unit test, so any transposition
  changes an observed value and fails.
- Risk (severity low, likelihood medium): `parse_state` assigns a `tomllib`
  decoded `list` straight onto a `tuple[...]` field, leaving a runtime type
  mismatch the frozen dataclass does not police. Mitigation: `parse_state`
  builds every sequence field as an explicit `tuple` at the boundary, and the
  tests assert against tuples (`paths == ("…",)`), so a missed coercion fails.
- Risk (severity medium, likelihood medium): the schema in a single
  `schema.py` plus the boundary parser, both with numpy docstrings and 100%
  interrogate, approaches or exceeds the 400-line cap mid-implementation,
  forcing a late, unplanned split that risks the >6-file Tolerance. Mitigation:
  Interfaces commits to the `schema.py` + `parse.py` split up front, so the cap
  is respected by construction rather than discovered late.
- Risk (severity low, likelihood low): the phase enum's kebab-case values
  (`conflict-analysis`, `reader-fit`, `final-pass`) collide with
  `enum.StrEnum`'s member-name rules if members are named carelessly.
  Mitigation: name members in `UPPER_SNAKE` (`CONFLICT_ANALYSIS`) with the
  kebab-case string as the explicit value; assert `Phase("conflict-analysis")`
  resolves and `list(Phase)` order equals the `phase_names` fixture.

## Interfaces and dependencies

Create the package `novel_ralph_skill/state/` with these modules and public
surfaces. (Splitting the enum from the schema keeps each module well under the
400-line cap and lets the validator (2.1.2) import the enum without the whole
schema.)

In `novel_ralph_skill/state/phase.py`, define the closed phase enum:

```python
import enum


class Phase(enum.StrEnum):
    """The eleven ordered lifecycle phases of the novel (design §5.1)."""

    PREMISE = "premise"
    """Premise capture; the first phase."""

    TREATMENT = "treatment"
    """Treatment of the premise into a narrative shape."""

    # … one string-literal docstring on the line after every member, exactly as
    # contract/exit_codes.py does for ExitCode. A `#` comment will NOT satisfy
    # interrogate at fail-under = 100; the literal-string form is mandatory.

    DONE = "done"
    """Terminal phase; the novel is complete."""
```

`list(Phase)` is the canonical order; export a `PHASE_ORDER: tuple[Phase, ...]`
if a tuple form is convenient for callers. Each member carries a **string-literal
docstring on the line after the member**, mirroring `ExitCode` exactly (a `#`
comment does not satisfy interrogate's per-member coverage; see Constraints).

Split the schema across two modules **up front** rather than discovering the
400-line cap mid-implementation (the Tolerance escalates at >6 files / ~450 net
lines, so the split must not be improvised late). Put the frozen dataclasses in
`novel_ralph_skill/state/schema.py` and the boundary constructors
(`parse_state` / `load_state`) in `novel_ralph_skill/state/parse.py`. With
roughly eight sub-dataclasses each carrying a numpy docstring on every attribute
(the `envelope.py` house style) plus 100% interrogate coverage, a single file
would plausibly approach the cap; the split keeps each module comfortably under
400 lines and lets the 2.1.2 validator import `parse_state` without pulling in
filesystem code. The four files this task adds are therefore `state/__init__.py`,
`state/phase.py`, `state/schema.py`, and `state/parse.py` — four of the
six-file Tolerance budget, leaving headroom for the enum test and schema test
modules.

In `novel_ralph_skill/state/schema.py` define the frozen, keyword-only
dataclasses mirroring the §5.1 tables, for example:

```python
import dataclasses
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterEntry:
    number: int
    slug: str
    title: str
    target_words: int


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class PendingTurn:
    operation: str
    paths: tuple[str, ...]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class State:
    schema_version: int
    novel: NovelMeta
    phase: PhaseState           # current: Phase; completed: tuple[Phase, ...]
    chapters: tuple[ChapterEntry, ...]
    drafting: Drafting          # cursor + critic + fangirl sub-state
    gates: Gates                # knitting + final
    word_counts: WordCounts     # target, current, by_chapter mapping
    pending_turn: PendingTurn | None = None
```

The exact sub-dataclass set (`NovelMeta`, `PhaseState`, `Drafting`,
`CriticState`, `FangirlState`, `Gates`, `WordCounts`) is settled in Work item 3
against the field inventory above. Use `slots=True` per python-data-shapes for
immutable domain objects.

Provide one public boundary constructor:

```python
def parse_state(raw: cabc.Mapping[str, object]) -> State:
    """Construct a :class:`State` from a decoded ``state.toml`` mapping."""
```

and a thin convenience that reads a file:

```python
def load_state(path: Path) -> State:
    """Read and parse ``state.toml`` from ``path`` with ``tomllib``."""
```

`load_state` reads bytes and calls `tomllib.load`, then `parse_state`. Keep
`parse_state` pure (mapping in, `State` out) so the validator and round-trip can
reuse it without a filesystem.

**List→tuple coercion at the boundary.** `tomllib` decodes every TOML array to a
Python `list`: `phase.completed`, the `[chapters]` array, and
`pending_turn.paths` all arrive as lists. The schema's sequence fields are
tuples (`tuple[Phase, ...]`, `tuple[ChapterEntry, ...]`, `tuple[str, ...]`), so
`parse_state` must explicitly build a `tuple` (and, for `completed`, resolve
each element through `Phase(...)`) when constructing each field — it must not
assign the decoded `list` straight onto a tuple-typed field. Correspondingly the
tests assert against tuples (e.g. `state.pending_turn.paths == ("…",)`), never
against a `list`, so a missed coercion fails loudly rather than passing on a
type mismatch the dataclass does not police.

`parse_state` performs **structural** construction
only — it builds the typed object and resolves phase strings to `Phase`. It does
**not** enforce the §5.2 invariants (that is 2.1.2). If a phase string is not a
member, `Phase(value)` raises `ValueError`; for this task that is acceptable
boundary behaviour, since every corpus coherent tree carries valid phases. The
exit-code mapping of parse failures is 2.2.x's concern, not this task's.

Re-export the public names from `novel_ralph_skill/state/__init__.py`:
`Phase`, `PHASE_ORDER`, `State`, the sub-dataclasses, `parse_state`,
`load_state`.

Dependencies: standard-library `enum`, `dataclasses`, `tomllib`, `pathlib`
only. No third-party runtime dependency. No `cuprum`, no `cyclopts` — this task
runs no subprocess and exposes no CLI. (`cuprum` is the subprocess-catalogue
boundary used only when a command shells out; design §9 confirms "v1 commands
shell out to nothing", so it is genuinely out of scope here. `cyclopts` is the
CLI framework wired in 2.2.2.)

## Plan of work

Stage A is understand-and-pin (no production code). Stage B writes the failing
tests. Stage C implements the enum and schema to green. Stage D hardens and
documents. Each work item below is independently committable and gate-passable.

### Work item 1 — Pin the field inventory and the corpus key shape (no code)

Implements: design §5.1 (schema), §8 (omit `plan.md`); `state-layout.md` (on-disk
layout). Verifies the schema against the §1.3.2 corpus it must wrap.

Read `tests/working_corpus/_builder.py` end to end and record, in this plan's
`Decision Log` and (later) the schema module docstring, the **exact** TOML key
names, types, and table nesting the builder writes for every field — especially
the three added fields (`[chapters]` manifest shape, `[drafting.critic].`
`convergence_target`, `[pending_turn]`). Confirm the builder writes no
per-chapter `plan.md` key. Cross-check against `state-layout.md` and §5.1.
Resolve the `[chapters]` shape question (array-of-tables vs table-of-tables)
from the builder, not from prose.

Documentation to read: design §5.1, §8; `state-layout.md`; `_builder.py`,
`_specs.py`. Skills to load: `leta` (navigate `_builder.py` and the corpus),
`python-data-shapes` (boundary-parse stance), `en-gb-oxendict` (prose).

Tests: none (analysis only). Output is the pinned inventory recorded in this
plan.

Validation: no code, so no gate. Commit this plan update with
`make markdownlint` and `make nixie` passing (this plan is the only changed
Markdown).

### Work item 2 — Add the `Phase` enum and a failing membership/order test

Implements: design §5.1 phase enum (the eleven-member ordered lifecycle).

Add `novel_ralph_skill/state/__init__.py`, `novel_ralph_skill/state/phase.py`
with the `Phase` `enum.StrEnum` and `PHASE_ORDER`, mirroring the `ExitCode`
house style exactly: a class docstring and a **string-literal docstring on the
line after every member** (not a `#` comment — see Constraints; a comment fails
interrogate at `fail-under = 100`). Add
`tests/test_state_schema.py` (or `tests/test_phase_enum.py`) with a test that
asserts: every member's value is the kebab-case string; `list(Phase)` order
equals the `phase_names` fixture exactly (the corpus's `PHASE_ORDER`);
`Phase("conflict-analysis")` resolves; and an unknown string raises `ValueError`.

Documentation to read: design §5.1; `state-layout.md` "Phase enum";
`novel_ralph_skill/contract/exit_codes.py` (house style); AGENTS.md testing
rules. Skills: `leta`, `python-data-shapes` (StrEnum for a closed set),
`python-testing` (parametrization), `en-gb-oxendict`.

Tests to add: a unit test module covering phase membership, order against
`phase_names`, value form, and the unknown-string `ValueError`. This is the
red→green pair for the enum: the order assertion fails before the enum exists
(import error) and passes after.

Validation: from the worktree root, `make test` (expect the new enum tests
pass; everything else still green), then `make check-fmt lint typecheck`. Run
`make all` before committing. Commit.

### Work item 3 — Add the schema dataclasses and the boundary parser, failing tests first

Implements: design §5.1 schema (all tables and the three added fields), §8 (no
`plan.md`); python-data-shapes boundary-parse discipline.

The tests are deliberately **split into a coverage pass and an exact pass**,
because the corpus surface (see the "Corpus surface is fixture-only" Constraint
and the Purpose) makes exact word-count values nameable only for trees the test
authors itself. Write both as failing tests first (red), then implement the
schema to green.

**3a — coverage pass over the library trees (`coherent_oracle_cases`).**
Parametrize over the `coherent_oracle_cases` fixture (baseline + eleven phase
states). For each `(spec, working)` pair, assert that
`load_state(working / "state.toml")` returns a `State` **without raising**; that
`state.phase.current` is a `Phase` member and every entry of
`state.phase.completed` is a `Phase` member; that
`tuple(str(p) for p in state.phase.completed) == spec.phase_completed` and
`str(state.phase.current) == spec.phase_current` (these two `WorkingTreeSpec`
fields *are* directly available, so the phase round-trip is checked exactly even
on the library trees); that `state.chapters` is a tuple whose `number` values
are strictly ascending; and that `state.pending_turn is None` (every coherent
library tree leaves `pending_turn` unset — the `WorkingTreeSpec` default, never
overridden in `_library.py`). This proves all eleven phases + baseline decode
and that phases resolve, **without** naming any derived `current`/`by_chapter`
value. It deliberately does **not** assert exact word counts, because those are
not on the spec and `derive_*` is not a sanctioned fixture (B1).

**3b — exact without-loss pass over test-authored specs.** Build one or more
specs in the test itself via the `make_chapter_spec` and `make_working_tree_spec`
constructors and the `build_tree` fixture — the identical pattern
`tests/test_working_corpus.py::test_state_decodes_to_declared_values`
(lines 103-122) uses. Because the test declares every value, assert the parsed
`State` reproduces, exactly: `schema_version == 1`; the novel metadata; the
drafting cursor; `phase.current`/`phase.completed` as `Phase` members;
`drafting.critic.convergence_target` (set the spec's `convergence_target` to a
non-default value such as `2` so a hard-coded default would fail);
`word_counts.target`, `word_counts.current`, and the `by_chapter` mapping keyed
by the zero-padded two-digit string (with chapters whose `draft_words` give an
unambiguous per-chapter breakdown and a `current` equal to their sum, mirroring
the `{"01": 4, "02": 6}` / `10` self-test); and the `[chapters]` manifest as an
ordered tuple of `ChapterEntry` with the declared `number`/`slug`/`title`/
`target_words`. Use distinct `slug`/`title`/`target_words`/`number` across
chapters so a transposition bug (e.g. `target_words` ↔ `number`) fails (the
pre-mortem's latent-transposition class, A3-aligned).

**3c — `last_finding_counts` transposition guard (A3).** The builder hard-codes
`blocker/major/minor/taste = 0` for every library tree
(`_builder.py:70-75`), so the library trees never prove the four counts land in
the right fields. The builder writes `last_finding_counts` from a fixed inline
table, not from a `WorkingTreeSpec` field, so a test-authored spec cannot vary
it through the corpus. Therefore cover the four counts with a **direct
`parse_state` unit test**: hand-build a minimal decoded mapping (a plain `dict`,
the shape `tomllib.load` returns) with **distinct non-zero** counts — for
example `blocker=0, major=2, minor=4, taste=7`, the `state-layout.md` example —
and assert each lands on its own `CriticState` attribute. This exercises
`parse_state` directly (mapping in, `State` out — the pure boundary), needs no
corpus fixture, and catches a count transposition the corpus cannot.

**3d — pending-turn presence and list→tuple coercion (A1).** Parse the
`uncleared-pending-turn` incoherent variant via the `incoherent_tree` fixture
and assert `state.pending_turn` is a populated `PendingTurn` whose `operation`
equals `"write-draft"` and whose `paths` equals the **tuple**
`("working/manuscript/chapter-03/draft.md",)` — the variant writes `paths` as a
TOML array (`_variants.py:148`), `tomllib` decodes it to a `list`, and the
assertion against a tuple proves `parse_state` coerced it (it must not leave a
`list` on the `tuple[str, ...]` field). The settled `pending_turn is None` case
is already covered by 3a. Parsing this variant exercises only the *structural*
presence of `[pending_turn]`; the schema does not judge whether it should be
cleared (that is the §5.2 validator's job in 2.1.2).

All four tests fail at import before the schema exists. Then implement
`novel_ralph_skill/state/schema.py` (the dataclasses) and
`novel_ralph_skill/state/parse.py` (`parse_state` / `load_state`) — the split
committed to in Interfaces — pinned to the Work item 1 inventory, with the
list→tuple coercion at the boundary. Re-export from `state/__init__.py`. Make all
four tests green.

Documentation to read: design §5.1; `state-layout.md` schema block; `_specs.py`
(field inventory) and `_builder.py` (the `last_finding_counts` and `paths`
shapes); `envelope.py` (frozen-dataclass house style); developers-guide
"Shared test scaffolding" and "The `working/` fixture corpus"; the existing
`tests/test_working_corpus.py::test_state_decodes_to_declared_values` as the
template for the 3b pattern. Skills: `leta`, `python-data-shapes` (slotted frozen
domain objects, parse-at-boundary, list→tuple coercion), `python-types-and-apis`
(public signatures, `Mapping` parameter typing), `python-testing` (fixture-driven
parametrization, the `from conftest import` type carve-out), `en-gb-oxendict`.

Tests to add: the 3a coverage pass over `coherent_oracle_cases`; the 3b exact
without-loss pass over test-authored specs; the 3c direct `parse_state`
`last_finding_counts` unit test; the 3d pending-turn presence/coercion test.
These are example-based — exhaustive over the corpus for breadth and
hand-specified for depth — which is the right method for "representative states
parse without loss"; property-based generation belongs to the 2.1.2 validator,
not here.

Validation: `make test` (the four new schema tests pass; corpus self-tests still
pass), then `make check-fmt lint typecheck audit`. Run `make all` before
committing. Commit.

### Work item 4 — Harden, document, and remove any temporary suppressions

Implements: AGENTS.md documentation-maintenance and quality rules.

Add module docstrings to every new file citing the design sections and the
`state-layout.md` lines they implement, and a one-line note that the schema is
read-only and validation lives in 2.1.2. Add the public schema surface to
`docs/developers-guide.md` "State and on-disk layout" (a short paragraph naming
`novel_ralph_skill.state.Phase`, `State`, and `parse_state`/`load_state` as the
typed entry point later commands import) if and only if the developers-guide does
not already describe an equivalent. Ensure interrogate reports 100% docstring
coverage and that no lint suppression was introduced without a linked follow-up.

Documentation to read: AGENTS.md "Documentation maintenance"; developers-guide;
documentation-style-guide. Skills: `en-gb-oxendict`, `leta`.

Tests: no new behaviour; the existing schema tests remain the guard. If the
developers-guide is edited, run `make markdownlint` and `make nixie`.

Validation: `make all` (build, check-fmt, lint, typecheck, test) plus `make
audit`; if Markdown changed, `make markdownlint` and `make nixie`. Commit.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-1`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-1 \
     branch --show-current
   ```

   Expect `roadmap-2-1-1`.

2. Work item 1: read the builder and record the inventory. No commands beyond
   reading; update this plan's `Decision Log`. Commit the plan with the Markdown
   gates:

   ```bash
   make markdownlint
   make nixie
   ```

3. Work item 2: add `phase.py` and the enum test, then:

   ```bash
   make all
   ```

   Expect the build, format check, lint, typecheck, and test stages to pass, with
   the new enum tests among the passes. Commit.

4. Work item 3: add the failing schema tests, then the schema module, then:

   ```bash
   make all
   make audit
   ```

   Expect all green. Commit.

5. Work item 4: docstrings, optional developers-guide paragraph, then:

   ```bash
   make all
   make audit
   make markdownlint   # only if Markdown changed
   make nixie          # only if Markdown changed
   ```

   Commit.

## Validation and acceptance

Acceptance is behavioural and observable:

- Running `make test` from the worktree root passes. The new test module
  `tests/test_state_schema.py` (and/or `tests/test_phase_enum.py`) is present;
  its parse tests fail before Work item 3's schema module exists (import error)
  and pass after.
- For every coherent corpus tree — the mid-drafting baseline and all eleven
  phase states delivered by the `coherent_oracle_cases` fixture —
  `load_state(working / "state.toml")` returns a `State` without raising, with
  `phase.current`/`phase.completed` resolving to `Phase` members that round-trip
  to the spec's `phase_current`/`phase_completed`, the `[chapters]` manifest
  present and ascending by `number`, and `pending_turn is None` (the 3a coverage
  pass). This is the breadth half of the §2.1.1 success criterion ("representative
  states from the §1.3.2 corpus parse into the typed structure without loss").
- For test-authored specs built via `make_working_tree_spec`/`make_chapter_spec`/
  `build_tree`, the parsed `State` reproduces *every* field exactly — including
  `word_counts.current`, the `by_chapter` mapping, a non-default
  `convergence_target`, distinct non-zero `last_finding_counts` (via a direct
  `parse_state` unit test), and the `[chapters]` manifest order (the 3b/3c depth
  passes). This is the without-loss depth half of the criterion, sourced from
  values the test owns rather than from corpus-internal derived helpers (which
  are not a sanctioned fixture surface — see Constraints).
- `list(Phase)` equals the `phase_names` fixture (the eleven members in §5.1
  order); `Phase("conflict-analysis")` resolves; an unknown phase string raises
  `ValueError`.
- The `uncleared-pending-turn` variant parses into a `State` with a populated
  `PendingTurn` whose `paths` is a `tuple` (list→tuple coercion verified); a
  settled coherent tree has `pending_turn is None`.
- The schema carries no per-chapter `plan.md` field (§8).

Quality criteria (what "done" means):

- Tests: `make test` passes; new tests fail before and pass after the
  implementation.
- Lint/typecheck: `make check-fmt`, `make lint` (ruff + interrogate 100% +
  pylint-pypy), and `make typecheck` (`ty`) pass with no new suppressions.
- Security: `make audit` (pip-audit) passes; no new dependency added.
- Markdown (this plan and any guide edit): `make markdownlint` and `make nixie`
  pass.

Quality method (how we check):

- `make all` (build, check-fmt, lint, typecheck, test) run sequentially per
  AGENTS.md, plus `make audit`, before each commit. Markdown gates on Markdown
  commits.

## Idempotence and recovery

Every step is additive and re-runnable. The new package
`novel_ralph_skill/state/` and the new test module do not exist yet, so creating
them is safe; re-running `make all` after a partial edit simply re-checks. No
step deletes or mutates existing files except the optional developers-guide
paragraph in Work item 4, which is a pure addition. If a gate fails, fix forward
and re-run `make all`; nothing is left in a torn state because no writes touch
`working/` or any runtime artefact. To abandon, `git restore` the new files;
they are isolated under `novel_ralph_skill/state/` and `tests/test_state_*`.

## Progress

- [x] Work item 1: pin the field inventory and corpus key shape (analysis).
  Inventory recorded under "Pinned corpus key shape"; design and builder agree,
  no mismatch escalation needed.
- [x] Work item 2: add the `Phase` enum and its membership/order test.
  `novel_ralph_skill/state/phase.py` defines the eleven-member `Phase`
  `StrEnum` with `PHASE_ORDER`; `tests/test_phase_enum.py` asserts order against
  the `phase_names` fixture, value form, resolution, and the unknown-string
  `ValueError`. See Surprises for the S105 false positive on `FINAL_PASS`.
- [x] Work item 3: add the schema dataclasses, the boundary parser, and the
  parse tests — the 3a coverage pass over `coherent_oracle_cases`, the 3b exact
  without-loss pass over test-authored specs, the 3c direct `parse_state`
  `last_finding_counts` unit test, and the 3d pending-turn presence/coercion
  test. `schema.py` (twelve frozen, slotted dataclasses) and `parse.py`
  (`parse_state`/`load_state`) deliver the split committed to in Interfaces; the
  public surface is re-exported from `state/__init__.py`. All 159 tests pass;
  `make all` and `make audit` are green. See Surprises for the TC001 and
  `itertools.pairwise` lint adjustments.
- [x] Work item 4: harden, document, and clear any suppressions. Every new
  module already carries a docstring citing its design sections and the
  read-only/validation-lives-in-2.1.2 note; `docs/developers-guide.md` "State
  and on-disk layout" gains a paragraph naming the typed
  `novel_ralph_skill.state` entry point (`Phase`, `State`, `parse_state`,
  `load_state`). interrogate reports 100%; the only suppression is the permanent
  `# noqa: S105` on `FINAL_PASS` (documented above), with no follow-up needed.

## Surprises & discoveries

- Work item 1 (2026-06-22, implementing agent): the design prose (§5.1) and the
  corpus builder (`tests/working_corpus/_builder.py`) **agree** on every key
  name, type, and table nesting for the three added fields. No
  design-versus-disk drift was found, so the schema/builder-mismatch Tolerance
  did not fire. The pinned inventory below is therefore the single ground truth
  the schema mirrors.

### Pinned corpus key shape (Work item 1)

Read end to end from `tests/working_corpus/_builder.py` and cross-checked
against `skill/novel-ralph/references/state-layout.md` and design §5.1:

- `schema_version` — top-level `int`, fixed `1` (`_builder.py:143`).
- `[novel]` — `title` (str), `slug` (str), `target_word_count` (int),
  `created_at` (str literal `"2026-05-23T14:00:00Z"`) (`_builder.py:42-49`).
- `[phase]` — `current` (str), `completed` (TOML array of str)
  (`_builder.py:52-57`). `tomllib` decodes `completed` to a `list`.
- `[drafting]` — `current_chapter`, `current_scene`, `current_beat` (ints)
  (`_builder.py:60-65`).
- `[drafting.critic]` — `pass` (int, fixed `1`), `consecutive_clean` (int),
  `convergence_target` (int, the **added field**), and `last_finding_counts`
  (an **inline table** with `blocker`/`major`/`minor`/`taste` ints, hard-coded
  `0/0/0/0` for every library tree) (`_builder.py:66-76`).
- `[drafting.fangirl]` — `last_chapter_passed` (int, fixed `0`)
  (`_builder.py:77-79`).
- `[gates.knitting]` — `done_30`, `done_50`, `done_80` (bools)
  (`_builder.py:83-90`).
- `[gates.final]` — `final_pass_complete` (bool) (`_builder.py:91-93`).
- `[word_counts]` — `target` (int), `current` (int), `by_chapter` (an **inline
  table** keyed by the zero-padded two-digit string, values int)
  (`_builder.py:97-104`).
- `[chapters]` — the **added field**: a TOML **array of inline tables**
  (array-of-tables resolved here, not table-of-tables), ascending by `number`,
  each carrying `number` (int), `slug` (str), `title` (str), `target_words`
  (int) (`_builder.py:107-131`). `tomllib` decodes this to a `list[dict]`.
- `[pending_turn]` — the **added field**: present only when the spec sets it,
  a table with `operation` (str) and `paths` (TOML array of str)
  (`_builder.py:150-153`). The `uncleared-pending-turn` variant sets
  `operation="write-draft"`, `paths=["working/manuscript/chapter-03/draft.md"]`
  (`tests/working_corpus/_variants.py`).
- **No per-chapter `plan.md` key** is written anywhere in the builder
  (confirmed by full read), so the §8 dead reference is correctly absent.

- Work item 2 (2026-06-22, implementing agent): ruff's
  `hardcoded-password-string` (S105) heuristic flags `FINAL_PASS = "final-pass"`
  because the assignment target name contains the substring "PASS". This is a
  false positive — the value is a lifecycle phase string, not a secret. A single
  inline `# noqa: S105` with an explanatory comment suppresses it on the enum
  member; the enum test sidesteps it by comparing through a member→value `dict`
  rather than a bare `member == "final-pass"` line, and the order test was
  written `tuple(Phase) == PHASE_ORDER` to satisfy ruff's `SIM300` (no Yoda
  conditions). This suppression is permanent (the member name is fixed by the
  design), not a temporary one needing a follow-up link.

- Work item 3 (2026-06-22, implementing agent): two ruff findings on first green
  were resolved without suppressions. (1) `schema.py` imported `Phase` only for
  annotations, so ruff's `TC001` (typing-only-first-party-import) asked for it
  under the `TYPE_CHECKING` guard; with `from __future__ import annotations` the
  string annotation resolves lazily, so the import moved there. (2) The 3a
  manifest-ascending check used `zip(numbers, numbers[1:])`, which ruff's
  `zip-instead-of-pairwise` rule flagged; it became `itertools.pairwise`.
  Neither is a suppression — both are the idiomatic form the gate prefers.

- Work item 3 (2026-06-22, implementing agent): `CriticState` annotates
  `last_finding_counts: FindingCounts` before `FindingCounts` is defined later
  in the module. With `from __future__ import annotations` the annotation is a
  string and resolves lazily, so the forward reference is sound and `ty` accepts
  it; the readers' order (critic before its finding-count sub-table) is kept for
  narrative clarity.

- Fix round 1 (2026-06-22, dual review B1): `WordCounts.by_chapter` shipped as a
  plain mutable `dict` on a dataclass the package documents as "frozen, fully
  typed". The `frozen=True`/`slots=True` guarantee was leaky —
  `state.word_counts.by_chapter['01'] = 999` mutated the supposedly immutable
  object in place — diverging from the house style the ExecPlan cites
  (`contract/envelope.py` types its mapping field as the read-only
  `cabc.Mapping[str, object]`). Resolved by typing the field
  `cabc.Mapping[str, int]` and wrapping the already-copied dict in a
  `types.MappingProxyType` at the boundary in `_word_counts` (`parse.py` already
  copied into a fresh dict to avoid aliasing; the proxy completes the isolation).
  `MappingProxyType` still satisfies `==` against a `dict`, so the existing parse
  tests pass unchanged. Note: this restores the immutability guarantee but not
  per-se hashability — a `MappingProxyType` is read-only yet unhashable, exactly
  as the cited house-style `Envelope` (whose `cabc.Mapping` field is likewise
  unhashable) is. Making `State` hashable would require a hashable frozen-mapping
  type, which would diverge from the cited house style and exceed the blocking
  item; the leaky-immutability defect — the verifiable, in-scope half — is fixed.
- Fix round 2 (2026-06-22, dual review B1): the round-1 fix was correct in code
  but the shipped `WordCounts.by_chapter` docstring still asserted the wrapping
  kept `State` "hashable" — the opposite of the truth recorded in this Surprises
  log. `MappingProxyType` is unhashable, so `WordCounts` and `State` are
  unhashable too (`hash(WordCounts(...))` raises `TypeError: unhashable type:
  'dict'`). Because `State`/`WordCounts` are the stable public surface that
  2.1.2 (`novel-state check`) and 2.2.1 (round-trip) import, a docstring lying
  about hashability would mislead a consumer into using a `State` as a dict key
  or set member. Resolved by rewriting the `by_chapter` docstring in
  `schema.py` to state the actual guarantee — read-only immutability, not
  hashability — explicitly noting `MappingProxyType` is unhashable (mirroring
  the cited `Envelope`, whose `cabc.Mapping` field is likewise unhashable) and
  directing consumers not to use a `State` as a dict key or set member.
  Docstring-only change; all 159 tests, `make all`, markdownlint, and nixie
  stay green.

## Decision log

- Decision: use standard-library `dataclasses` (frozen, slotted, `kw_only`) plus
  `enum.StrEnum`, read with standard-library `tomllib`, rather than
  `msgspec.Struct`. Rationale: `msgspec` is referenced only as an
  import-convention alias in `pyproject.toml` and is absent from `uv.lock`;
  adopting it is a new runtime dependency and a Tolerance breach. The established
  house style (`contract/envelope.py`, `contract/exit_codes.py`) is frozen
  dataclasses and stdlib enums, and `tomllib` is already used in the test suite
  (`tests/conftest.py:117`, `tests/test_working_corpus.py:19`). This keeps the
  schema dependency-free and consistent. python-data-shapes endorses dataclasses
  for "in-process domain shapes that do not need a serde codec"; `state.toml` is
  read with `tomllib` and the writer is `tomlkit` (ADR-002), so no decode codec
  is needed in the schema itself. Date/author: 2026-06-22, planning agent.
- Decision: `created_at` is carried as a `str`, not parsed to a `datetime`.
  Rationale: the corpus writes the fixed literal `"2026-05-23T14:00:00Z"`
  (`_specs.py` `_CREATED_AT`) and the round-trip (2.2.1) must preserve the file
  byte-for-byte through `tomlkit`; keeping the timestamp as the on-disk string
  avoids a parse/format asymmetry and a timezone dependency. The schema models
  the field, not a calendar. Date/author: 2026-06-22, planning agent.
- Decision: `parse_state` performs structural construction only; it does not
  enforce the §5.2 invariants. Rationale: §5.2 enforcement is roadmap task 2.1.2
  (`novel-state check`). 2.1.1's success criterion is parse-without-loss, not
  validation. Keeping the boundary parser free of invariant logic preserves the
  checker/mutator separation (design §3.3) and lets 2.1.2 layer the validator
  over the schema. Date/author: 2026-06-22, planning agent.
- Decision: `cuprum` and `cyclopts` are out of scope for this task. Rationale:
  design §9 confirms v1 commands shell out to nothing, so the `cuprum` catalogue
  boundary is unused here; `cyclopts` is the CLI framework wired in 2.2.2. This
  task is a pure, in-process schema parse with no subprocess and no CLI, so
  neither library is load-bearing. Verified against `cuprum` docs
  (`/data/leynos/Projects/cuprum/docs/users-guide.md`:
  `DEFAULT_CATALOGUE`/`ProgramCatalogue` are an executable allowlist for shelling
  out) and the locked `cuprum` 0.1.0 in `uv.lock`. Date/author: 2026-06-22,
  planning agent.
- Decision: when the design prose and the corpus builder disagree on a key name
  or table shape, the builder wins for this task and the mismatch is escalated.
  Rationale: the fixtures are what the parser must consume; a parser that
  disagrees with the corpus is useless. But a real design-versus-disk drift is a
  finding (the kind the by-chapter-sum fix-round-1 surfaced for 1.3.2), so it is
  recorded and raised rather than silently absorbed. Date/author: 2026-06-22,
  planning agent.

- Decision: the without-loss test is split in two — a coverage pass over the
  library trees (`coherent_oracle_cases`) asserting only derivation-free
  properties, and an exact pass over test-authored specs. Rationale:
  `word_counts.current` and `by_chapter` are *derived* by `derive_current` /
  `derive_by_chapter` (`_specs.py:228-253`), not carried on `WorkingTreeSpec`,
  and those helpers are not among the fifteen sanctioned corpus fixtures
  (developers-guide lines 103-107). Asserting their exact values over a library
  tree would require a forbidden runtime value import (lines 31-32, 96-97) or a
  corpus-fixture surface change barred by this plan's Tolerances. The existing
  self-test proves the only available patterns: exact `by_chapter`/`current`
  only for self-authored specs (`test_working_corpus.py:118-119`) and a coarse
  property over `coherent_oracle_cases` (`:357-360`). The split keeps breadth
  (all eleven phases + baseline decode) and depth (every field exact) without
  breaching the corpus contract, and makes the §2.1.1 "without loss" wording
  true by construction. Date/author: 2026-06-22, planning agent (resolves
  design-review B1, round 1).
- Decision: `last_finding_counts` is covered by a direct `parse_state` unit test
  with distinct non-zero counts (`0/2/4/7`), not through a corpus tree.
  Rationale: the builder hard-codes all four counts to `0`
  (`_builder.py:70-75`) and sources them from a fixed inline table, not a
  `WorkingTreeSpec` field, so neither the library trees nor a test-authored spec
  can vary them; a transposition bug would pass unseen. A direct mapping-in /
  `State`-out unit test exercises the pure boundary and pins each count to its
  attribute. Date/author: 2026-06-22, planning agent (resolves design-review A3).
- Decision: `parse_state` coerces every `tomllib`-decoded `list` to a `tuple` at
  the boundary, and the tests assert against tuples. Rationale: TOML arrays
  decode to `list`, the schema's sequence fields are tuples, and a frozen
  dataclass does not enforce element-container type at construction; an explicit
  coercion plus tuple-valued assertions catch a missed conversion.
  Date/author: 2026-06-22, planning agent (resolves design-review A1).
- Decision: enum members carry a string-literal docstring on the following line,
  not a `#` comment. Rationale: only the literal-string form satisfies
  interrogate's per-member coverage at `fail-under = 100`, as
  `contract/exit_codes.py` already does; a comment fails the first `make lint`.
  Date/author: 2026-06-22, planning agent (resolves design-review A2).
- Decision: the schema is split into `schema.py` (dataclasses) and `parse.py`
  (`parse_state`/`load_state`) up front. Rationale: with ~8 sub-dataclasses,
  numpy docstrings on every attribute, and 100% interrogate, a single file
  plausibly approaches the 400-line cap; committing to the split avoids a late,
  unplanned restructure that could brush the >6-file Tolerance, and lets 2.1.2
  import `parse_state` without filesystem code. Date/author: 2026-06-22,
  planning agent (resolves design-review A4).

## Outcomes & retrospective

- Delivered (2026-06-22): the typed, read-only `novel_ralph_skill.state` package
  — the closed eleven-member `Phase` `StrEnum`, twelve frozen/slotted schema
  dataclasses mirroring the §5.1 `state.toml` tables, and the pure `parse_state`
  / `load_state` boundary constructors — wraps every coherent §1.3.2 corpus tree
  without loss. The four-part parse suite (breadth coverage, exact without-loss,
  the direct `last_finding_counts` transposition guard, and the pending-turn
  presence/coercion test) passes alongside the enum suite; `make all` (159
  tests) and `make audit` are green at HEAD.
- All within tolerance: four new source files (`state/__init__.py`, `phase.py`,
  `schema.py`, `parse.py`) plus two test modules and the developers-guide
  paragraph — no corpus, contract, or envelope surface was touched, no new
  dependency added, and no file approaches the 400-line cap (`schema.py` is the
  largest at 297 lines).
- Design and corpus agreed throughout (no schema/builder-mismatch escalation),
  so the parser is pinned to exactly what the fixtures materialise. The only
  permanent suppression is the documented `# noqa: S105` false positive on
  `FINAL_PASS`; the TC001 and `itertools.pairwise` findings were resolved by
  adopting the idiomatic form rather than suppressing.
- Hand-off: the `novel-state check` validator (2.1.2) layers the §5.2 invariants
  over `parse_state`, and the `tomlkit` round-trip (2.2.1) is the matching
  writer; both import the stable public surface re-exported from
  `state/__init__.py`.

## Revision note

Initial draft (2026-06-22). Establishes the four-work-item plan to deliver the
typed `state.toml` schema and the `Phase` enum as a read-only, dependency-free
wrapper over the §1.3.2 corpus, pinned to the design §5.1 schema and the corpus
builder's on-disk key shape. No remaining-work split yet; implementation has not
started.

Revision 2 (2026-06-22). Resolves the round-1 Logisphere design review.

- B1 (blocking): the without-loss parse test was not constructible — it required
  asserting exact `word_counts.current`/`by_chapter` over the library trees, but
  those are derived by `derive_current`/`derive_by_chapter`, which are not
  sanctioned corpus fixtures, so naming their values forces a forbidden runtime
  import or a Tolerance-breaching fixture edit. Work item 3 is now split: a 3a
  coverage pass over `coherent_oracle_cases` asserts only derivation-free
  properties (parses, phases resolve and round-trip to the spec, manifest
  ascending, `pending_turn is None`), and a 3b exact without-loss pass runs over
  test-authored specs built via `make_working_tree_spec`/`make_chapter_spec`/
  `build_tree` (the established `test_state_decodes_to_declared_values`
  pattern), whose values the test owns. Purpose, Validation, a new "Corpus
  surface is fixture-only" Constraint, a high/high Risk, and a Decision Log entry
  were amended to match. Exact-value coverage over the library trees is named as
  an escalation, not buried.
- A1: list→tuple coercion at the boundary is now stated in Interfaces, Work item
  3d, the acceptance criteria, and the Decision Log; tests assert `paths` as a
  tuple.
- A2: the enum member-doc form is pinned to a string-literal docstring (not a
  `#` comment) in Constraints, the Interfaces enum sketch, Work item 2, and the
  Decision Log, to satisfy interrogate at `fail-under = 100`.
- A3: a direct `parse_state` unit test (3c) covers `last_finding_counts` with
  distinct non-zero counts (`0/2/4/7`), since the builder hard-codes all four to
  zero and they are not spec-varied.
- A4: the schema is committed to a `schema.py` + `parse.py` split up front,
  naming the four added source files within the six-file Tolerance budget.

These changes affect the test design and documentation only; the schema/enum
interfaces, the dependency stance, and the cuprum/cyclopts scope are unchanged.
Implementation has not started.

Revision 3 (2026-06-22). Resolves the round-1 dual-review blocking finding B1
on the delivered implementation.

- B1 (blocking): `WordCounts.by_chapter` was a plain mutable `dict`, making the
  package's "frozen, fully typed" guarantee leaky (in-place mutation of the
  supposedly immutable object succeeded). The field is now typed
  `cabc.Mapping[str, int]` and built as a `types.MappingProxyType` at the parse
  boundary in `_word_counts`, matching the read-only `cabc.Mapping` house style
  of `contract/envelope.py` and completing the fresh-dict isolation `parse.py`
  already performed. No test change was needed (a `MappingProxyType` still
  satisfies `==` against a `dict`). See the Surprises & discoveries entry for
  the hashability caveat. `make all` (159 tests) and `make audit` are green;
  CodeRabbit returned zero findings.

Revision 4 (2026-06-22). Resolves the round-2 dual-review blocking finding B1
on the delivered implementation.

- B1 (blocking): the round-1 code fix was sound, but the `WordCounts.by_chapter`
  docstring still claimed the `MappingProxyType` wrapping kept `State`
  "hashable" — directly contradicting the truthful hashability caveat in this
  ExecPlan's Surprises & discoveries log. `MappingProxyType` is unhashable, so
  `WordCounts` and `State` are unhashable; `hash(WordCounts(...))` raises
  `TypeError`. Since `State`/`WordCounts` are the public surface imported by
  2.1.2 and 2.2.1, the false contract risked misleading a consumer into keying a
  dict or set on a `State`. The docstring now states the real guarantee —
  read-only immutability, not hashability — and notes the proxy is unhashable
  exactly like the cited `Envelope` mapping field, with an explicit instruction
  not to use a `State` as a dict key or set member. Docstring-only change; no
  code or test behaviour changed. `make all` (159 tests), `make markdownlint`,
  and `make nixie` are green.
