# Implement the invariant validator behind `novel-state check`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

This plan delivers the §5.2 **invariant validator** — the pure function that
decides whether a parsed `state.toml` is internally coherent — and wires it
behind the read-only `novel-state check` console-script subcommand. After this
change, a developer (and the harness) can run `novel-state check` in a working
directory and get a contract-conformant JSON envelope: exit `0` with `ok: true`
when every §5.2 invariant holds, and exit `4` (an actionable finding the agent
adjudicates) with the violated invariant names in `result` when one or more do
not. A missing or unparseable `state.toml`, or an absent working directory, is
the state-error channel (exit `3`).

You can see it working, from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-2`:

```bash
make build
# A coherent corpus tree validates clean:
cd "$(mktemp -d)" && novel-state check ; echo "exit=$?"
```

against a `working/` directory holding a coherent `state.toml`, the command
prints a one-line JSON envelope with `"ok": true` and exits `0`; against a
state whose `consecutive_clean` exceeds its `convergence_target`, it prints an
envelope naming `consecutive-clean-bound` in `result.violations` and exits `4`.

The observable outcome has three complementary tests, mirroring the design's
verification scope (§2.3 "state coherence … demonstrated by property-based
tests over generated states") and the corpus oracle agreement the developers
guide names:

1. A **Hypothesis property suite** over generated `State` objects asserting the
   validator accepts exactly the states satisfying the §5.2 pure-state
   invariants and rejects the rest (the state-coherence property), with a
   targeted case proving a `consecutive_clean` above its `convergence_target` is
   rejected while one within a raised target is accepted.
2. A **corpus-oracle agreement suite** asserting that for every §1.3.2 corpus
   tree the validator's verdict (the set of violated invariant names) matches
   the corpus oracle's `CORPUS_INVARIANT_NAMES` labels, restricted to the
   pure-state invariants this task owns (see the scope split below). This is the
   anti-drift guarantee the developers guide and roadmap task 2.1.3 build on.
3. A **behavioural / end-to-end suite** over `novel-state check` asserting the
   exit codes and envelope shape: `0`/`ok: true` on a coherent tree, `4` with
   the violated invariant names on an incoherent one, and `3` on a missing or
   unparseable `state.toml`.

### Scope: this task owns the pure-state §5.2 invariants only

The design splits `novel-state check` into two responsibilities along the
checker/mutator boundary (§5.4): the §5.2 **invariant validation** (does the
parsed state contradict *itself*?) and the §5.4 **disk-authoritative
reconciliation** (is the state merely *behind* or *contradicted by* disk?).
**This task (2.1.2) implements only the first.** The roadmap assigns the
disk-evidence half — reconstructing intended state from `done.flag`/`compiled.md`
evidence, the chapter-manifest-to-disk bijection, the contradictory-disk refusal,
and `[pending_turn]` reconciliation — explicitly to task 2.3.2 (roadmap.md
lines 377-401), which `check` and `reconcile` share.

Concretely, of the design §5.2 invariants and the corpus oracle's ten
`CORPUS_INVARIANT_NAMES`, this task validates the ones computable from a parsed
`State` alone, with no filesystem read beyond loading `state.toml` itself:

- `phase-in-enum` — `phase.current` is a `Phase` member (§5.2 bullet 1).
- `completed-prefix` — `phase.completed` is an in-order enum prefix, no gaps
  (§5.2 bullet 2).
- `by-chapter-sum` — `word_counts.by_chapter` sums to `word_counts.current`
  (§5.2 bullet 3).
- `consecutive-clean-bound` — `0 <= consecutive_clean <= convergence_target`,
  `convergence_target >= 1`, and `consecutive_clean` never exceeds the number of
  manifest chapters (§5.2 bullet 4). This is the roadmap's named focus: the
  bound is the configured `convergence_target` ceiling, not a hard-coded 0-1
  literal, and a `convergence_target` below 1 is itself rejected.
- `gate-ratio-consistent` — each knitting gate boolean matches the **drafted
  total** ratio (`sum(word_counts.by_chapter) / word_counts.target`) against its
  threshold (§5.2 bullet 7). The drafted total, not `current`, is the gate
  numerator; the Decision Log (B1) records why this is the faithful reading of
  the design literal and how it agrees with the oracle.
- The **state-only** part of `cursor-coherent` (§5.2 bullet 6): `current_scene`
  and `current_beat` are non-negative, and `current_chapter`/scene/beat never
  reference a chapter past the manifest length. The "zero until plans exist"
  sub-clause that needs on-disk scene/beat-plan evidence is the corpus task
  2.1.4's and reconciliation task 2.3.2's concern, not validated here from disk.

The four invariants that require disk evidence are **explicitly out of scope**
for this task and are deferred to 2.3.2: `manifest-disk-bijection` (needs the
on-disk `chapter-NN/` set), `done-flag-without-draft` (needs `done.flag` and
`draft.md`), `compiled-matches-drafts` (needs `compiled.md`), and
`pending-turn-cleared` (a §3.4 torn-turn marker that reconciliation, not
validation, resolves). The validator surface this task ships is shaped so 2.3.2
layers the disk checks on top without rework: the validator is a pure
`State -> tuple[Violation, ...]`, and `check`'s command body composes it with the
(future) disk-evidence pass.

This scope split is not a convenience; it is the design's checker/mutator
boundary (§3.3, §5.4) and the roadmap's task decomposition (2.1.2 vs 2.3.2). A
single test in this plan pins the boundary so a future reader cannot mistake a
deferred invariant for a missing one (Work item 4's "deferred invariants are not
asserted from disk" test).

## Context and orientation

You are working inside the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-2`, on branch
`roadmap-2-1-2`. Do every edit here; never touch the control worktree at
`/data/leynos/Projects/novel-ralph-skill`.

Read these before starting, in order:

1. `docs/novel-ralph-harness-design.md` §5.2 — the authoritative list of
   invariants this task validates. Note which need disk evidence (deferred to
   2.3.2) versus which are pure-state (this task).
2. `docs/novel-ralph-harness-design.md` §5.4 — the checker/mutator split of
   `check` versus `reconcile` and the disk-authoritative half this task does
   **not** implement.
3. `docs/novel-ralph-harness-design.md` §2.3 — verification scope: "state
   coherence … demonstrated by property-based tests over generated states". This
   is why Work item 3 is a Hypothesis suite.
4. `docs/novel-ralph-harness-design.md` §3.1, §3.2, §3.3, §3.4 — the envelope,
   the exit-code table (the `4` actionable-finding code this checker returns
   on a violation), the checker/mutator segregation (`check` writes nothing),
   and the `[pending_turn]` model.
5. `docs/novel-ralph-harness-design.md` §4.1 — the `novel-state` subcommand
   table; `check` is "Validate every invariant (§5.2) … without writing".
6. `docs/adr-003-shared-interface-contract.md` §3.1 — the JSON envelope, the
   `--human` flag, the `working_dir` envelope **field** (not a flag), and the
   disambiguated exit-code table (0/1/2/3/4). Note: ADR-003 mandates only the
   `--human` flag and the `working_dir` envelope field; the design fixes
   `working_dir` to the cwd-relative constant `"working"` (design line 151) and
   defines exit `3` as "working dir absent" (design line 189). There is **no**
   `--working-dir` CLI flag anywhere in the design, the ADRs, or the
   users-guide; the validator reads `./working/state.toml` relative to the
   process cwd (see B4).
7. `docs/developers-guide.md` "The `working/` fixture corpus" (the
   `corpus_check` oracle and `CORPUS_INVARIANT_NAMES`), "Checker/mutator
   segregation", "The shared JSON envelope", and "State and on-disk layout".
8. `docs/execplans/roadmap-2-1-1.md` — the just-landed typed schema and parser
   this validator layers over; its Decision Log records the corpus key shape,
   the `created_at`-as-string and `cuprum`/`cyclopts` scope decisions, and the
   list→tuple coercion convention.
9. `AGENTS.md` — code style, the 400-line file cap, en-GB Oxford spelling, the
   testing rules (pytest unit + behavioural, Hypothesis for invariants, syrupy
   snapshots where multivariant output matters), and the quality gates.
10. `docs/scripting-standards.md` — the `Cyclopts` conventions for the
    subcommand surface (no `cuprum`/`cmd-mox` here; see the Decision Log on why
    this command shells out to nothing).

Key existing files you will consume or mirror:

- `novel_ralph_skill/state/schema.py` — the frozen `State` dataclass and its
  sub-tables (`PhaseState`, `Drafting`, `CriticState`, `WordCounts`, `Gates`,
  `KnittingGates`, `ChapterEntry`, …). The validator reads these fields; it
  imports the stable public surface from `novel_ralph_skill.state`. Confirmed
  field paths: `state.phase.current` / `state.phase.completed`;
  `state.word_counts.current` / `.target` / `.by_chapter` (a
  `Mapping[str, int]`); `state.drafting.critic.consecutive_clean` /
  `.convergence_target`; `state.drafting.current_chapter` / `.current_scene` /
  `.current_beat`; `state.gates.knitting.done_30` / `.done_50` / `.done_80`;
  `state.chapters` (a `tuple[ChapterEntry, ...]`).
- `novel_ralph_skill/state/phase.py` — `Phase` (`enum.StrEnum`) and
  `PHASE_ORDER`. The `phase-in-enum` and `completed-prefix` checks use these.
- `novel_ralph_skill/state/parse.py` — `parse_state` (pure, mapping→`State`)
  and `load_state` (reads a `state.toml` path with `tomllib`, line 228).
  `check`'s body calls `load_state`; a `tomllib.TOMLDecodeError`, `OSError`,
  `KeyError`, or `ValueError` from a malformed file maps to the exit-`3`
  `StateInputError`.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode` (`SUCCESS=0`,
  `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`) and `is_ok`. A §5.2 violation returns
  `ACTIONABLE_FINDING`.
- `novel_ralph_skill/contract/runner.py` — `run`, `CommandOutcome`,
  `RunContext`, `StateInputError`. `run(app, argv, context)` takes a
  **pre-built** `RunContext(command, working_dir, human)` and stamps
  `context.working_dir`/`context.human` into the envelope on every path,
  including the usage (`CycloptsError` → exit `2`, runner.py lines 163-170) and
  state-error (`StateInputError` → exit `3`, lines 171-177) paths where the
  command body never runs. Because `human` is needed on those body-less paths,
  it must be resolved from argv *by the entry point* before `run` is called (see
  B3). `working_dir`, by contrast, is **not** parsed from argv at all: it is the
  fixed constant `"working"` the design records (B4), so the entry point passes
  `RunContext(command="novel-state", working_dir="working", human=...)`
  unconditionally and the residual argv (with `--human` removed) goes to `run`.
  The `check` body returns a `CommandOutcome` carrying `ExitCode.SUCCESS` or
  `ExitCode.ACTIONABLE_FINDING` and the machine-actionable `result`; it raises
  `StateInputError` for the exit-`3` channel. `run` owns every `sys.exit` and
  envelope emission.
- `novel_ralph_skill/contract/envelope.py` — `build_envelope`/`render_machine`/
  `render_human`. The validator does not call these; `run` does. The `result`
  payload shape this task defines flows through `render_machine` unchanged.
- `novel_ralph_skill/commands/stub.py` — hosts the five console-script entry
  points (`novel_state`, `novel_done`, `novel_compile`, `desloppify`,
  `wordcount`). **This task evolves `stub.py::novel_state()` in place** from a
  not-implemented stub into the real entry point that pre-parses the `--human`
  flag, builds the `RunContext` (with the fixed `working_dir="working"`), and
  drives the new `commands/novel_state.py` app through `run`. The other four
  `*()` functions stay untouched stubs. Keeping the entry point on `stub`
  (rather than repointing the console-script) is the decisive B2 resolution
  below. Note the behavioural consequence (B6): once `novel_state()` runs `run`
  against `./working/`, invoking it with no `working/` present in cwd exits `3`
  (state error), not the stub's `2`; the two gate tests that exercise the real
  `novel_state()` callable must be narrowed accordingly (see Work item 2).
- `novel_ralph_skill/commands/names.py` — the single source of truth for the
  five command names. `STUB_MODULE = "novel_ralph_skill.commands.stub"` binds
  **all five** entry points to the `stub` module, and
  `project_scripts_table()` derives `[project.scripts]` from it. **No change**:
  the entry point stays on `stub`, so the registry, `pyproject.toml`, and the
  three registry gates (see B2) remain valid.
- `tests/working_corpus/_oracle.py` — `corpus_check`, the corpus-local
  structural oracle, and `CORPUS_INVARIANT_NAMES` (ten stable strings). The
  agreement suite keys on these. The validator must use the **same** invariant
  name strings for the pure-state invariants it owns, so the two vocabularies
  align (developers-guide lines 115-118). `_check_gate_ratio_consistent` (line
  137) computes the ratio from `sum(chapter.draft_words)` (the drafted total),
  **not** from `current`; the validator must match this (B1).
- `tests/working_corpus/_variants.py` — `INCOHERENT_VARIANTS` (line 156), the
  thirteen single-invariant variants the agreement suite drives. The
  `by-chapter-sum-mismatch` variant (line 95) sets `current_words_override=1`
  while leaving the drafts and the baseline gate booleans intact — the variant
  that falsified the round-1 plan's gate-ratio quantity (B1).
- `tests/working_corpus/_specs.py` — `derive_by_chapter` (line 228) and
  `derive_current` (line 243): `by_chapter` is derived from each chapter's
  `draft_words` (so `sum(by_chapter) == sum(draft_words)` whenever
  `by_chapter_override` is unset, which no current variant sets), while
  `current` honours `current_words_override`. This is why
  `sum(by_chapter) / target` equals the oracle's `drafted / target` on every
  corpus tree.
- `tests/corpus_fixtures.py` / `tests/conftest.py` — the fixture surface. The
  agreement suite consumes `coherent_oracle_cases`, `incoherent_variant_names`,
  `incoherent_tree`, `check_corpus`, and `corpus_invariant_names`; the
  behavioural suite consumes `baseline_tree`, `incoherent_tree`, and the
  spec-building constructors (`make_working_tree_spec`, `build_tree`). Consume
  by fixture name only; never import a corpus value. `incoherent_tree(name)`
  returns `(spec, working_dir, expected_invariant_name)` and materialises
  `state.toml` directly under `working_dir` (so the validator loads
  `working_dir / "state.toml"`).
- `tests/test_contract_runner.py` and the `wrapper_app` conftest fixture (line
  283) — the established pattern for building and driving a `run`-configured
  Cyclopts app in tests. The behavioural suite mirrors it.
- `tests/test_cyclopts_contract.py`, `tests/test_command_names_registry.py`,
  `tests/test_pyproject_scripts.py`, `tests/test_command_stubs.py`,
  `tests/test_console_scripts_e2e.py` — the registry/stub gates Work item 2
  must respect (see B2 and the WI2 escalation note).

Definitions of terms used below:

- **§5.2 invariant**: one of the coherence rules the design lists in §5.2 that
  `novel-state check` enforces.
- **Pure-state invariant**: an invariant decidable from the parsed `State`
  alone, with no filesystem evidence beyond the `state.toml` that produced it.
  This task's scope.
- **Disk-evidence invariant**: an invariant needing `working/` contents
  (`done.flag`, `compiled.md`, the `chapter-NN/` set). Deferred to task 2.3.2.
- **Drafted total**: the sum of the per-chapter draft word counts. In a parsed
  `State` this is `sum(state.word_counts.by_chapter.values())` (the corpus
  derives `by_chapter` from each chapter's `draft_words`). In the oracle it is
  `sum(chapter.draft_words)`. On every corpus tree the two coincide.
- **Violation**: a named §5.2 failure the validator reports, keyed by a string
  drawn from the same vocabulary as `CORPUS_INVARIANT_NAMES`.
- **Verdict**: the (possibly empty) ordered tuple of violation names the
  validator returns for a `State`; an empty verdict means the state is coherent.
- **Global flag**: `--human`, the single ADR-003 §3.1 invocation-level option
  the entry point parses off argv before delegating to the subcommand app (the
  B3 convention). The working directory is **not** a flag; it is the design's
  fixed cwd-relative constant `working/` (design line 151), resolved by the
  `check` body from the process cwd, never from a CLI override (see B4).

## Constraints

- Work exclusively in the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-2`. Never edit
  the control worktree.
- All prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`) per AGENTS.md and the `en-gb-oxendict` skill, except
  references to external APIs.
- No single code file exceeds 400 lines (AGENTS.md). The validator lives in its
  own module under `novel_ralph_skill/state/`; the `novel-state` subcommand app
  lives in its own module under `novel_ralph_skill/commands/`. If either nears
  the cap, split by invariant family (phase checks, count checks, cursor checks)
  rather than by layer.
- The validator is **pure and read-only**: `State` in, verdict out. It performs
  no filesystem access, no writing, no `tomlkit` mutation. `check` is a checker
  (design §3.3); it must write nothing. The only filesystem read is
  `load_state` decoding `state.toml`.
- **The console-script entry point stays on the `stub` module.** The
  `novel-state` console-script remains bound to
  `novel_ralph_skill.commands.stub:novel_state` via `names.py`/`pyproject.toml`.
  This task evolves `stub.py::novel_state()` in place to build the
  `RunContext` and drive the new app; it does **not** repoint the
  console-script or restructure `names.py`. Repointing would break three
  registry gates and trip the interface Tolerance (B2).
- **Scope boundary (load-bearing):** this task validates the pure-state §5.2
  invariants only (`phase-in-enum`, `completed-prefix`, `by-chapter-sum`,
  `consecutive-clean-bound`, `gate-ratio-consistent`, and the state-only part of
  `cursor-coherent`). The disk-evidence invariants
  (`manifest-disk-bijection`, `done-flag-without-draft`,
  `compiled-matches-drafts`, `pending-turn-cleared`) are task 2.3.2's and must
  **not** be implemented here. If a work item appears to require reading
  `working/` contents beyond `state.toml`, stop and escalate.
- **Invariant-name vocabulary is shared, not reinvented.** The validator's
  violation names for the invariants it owns must equal the corresponding
  `CORPUS_INVARIANT_NAMES` strings (`phase-in-enum`, `completed-prefix`,
  `by-chapter-sum`, `consecutive-clean-bound`, `gate-ratio-consistent`,
  `cursor-coherent`). The single source of truth for these strings is the design
  §5.2 wording; the corpus oracle and this validator both spell them the same so
  task 2.1.3's cross-check is keyed on one vocabulary. Define the validator's own
  name constants in the production module (the validator must not import from
  `tests/`), and pin their equality to the oracle's via a test.
- **The gate-ratio numerator is the drafted total, not `current`.** The
  validator computes invariant 7 from
  `sum(state.word_counts.by_chapter.values()) / state.word_counts.target` —
  the drafted total — exactly as the oracle's `_check_gate_ratio_consistent`
  does (`sum(chapter.draft_words) / target`). This keeps invariant 7 (gate
  consistency) decoupled from invariant 3 (by-chapter sum) so corrupting
  `current` trips only invariant 3, matching the oracle on the
  `by-chapter-sum-mismatch` variant (B1). Invariant 3 independently compares
  `sum(by_chapter)` against `current`.
- **The gate-ratio predicate guards its division: `target <= 0` is not a
  gate violation.** Before dividing by `state.word_counts.target` the predicate
  short-circuits when `target <= 0`, returning no `gate-ratio-consistent`
  violation — exactly mirroring the oracle's
  `_check_gate_ratio_consistent` first line `if spec.target_words <= 0: return
  True` (`_oracle.py` lines 144-145). `WordCounts.target` is a plain `int` with
  no positivity enforcement (`schema.py` line 254; `__post_init__` only freezes
  `by_chapter`), so a `State` with `target == 0` or negative is structurally
  constructible and parseable; without this guard the predicate would raise
  `ZeroDivisionError` rather than return a verdict, crashing both the property
  suite and the public `validate_state` surface and diverging from the oracle by
  exception (B7). `validate_state` is therefore **total**: every predicate
  returns a `Violation | None` for every constructible `State`, with no
  unguarded arithmetic.
- A §5.2 violation is the contract's **exit `4`** (`ACTIONABLE_FINDING`), not
  exit `1` or exit `3`: an invariant breach is a finding the agent adjudicates,
  per design §3.2 and §5.4 (`check` "exits 4 to signal an actionable finding").
  A missing/unparseable `state.toml` or absent working directory is exit `3`
  (`STATE_ERROR`).
- The `novel-state` command adopts the shared contract: it builds a Cyclopts app
  with `result_action="return_value", exit_on_error=False, print_error=False,
  help_on_error=False` and is driven through
  `novel_ralph_skill.contract.runner.run`, exactly as the `wrapper_app` fixture
  and `test_contract_runner.py` establish. It does not invent its own output
  shape or exit logic.
- Do **not** add a new runtime or dev dependency. The validator uses only
  `novel_ralph_skill.state` and the standard library; the command uses the
  already-present `cyclopts`. Tests use the already-present `hypothesis` and
  (if a snapshot is warranted) `syrupy`. `cuprum`/`cmd-mox`/`pytest-bdd`/
  `crosshair`/`mutmut` are not used (see Decision Log; `pytest-bdd` is not in
  `uv.lock`, so behavioural tests are plain pytest).
- Public schema and command names are stable; later tasks (2.1.3 the oracle
  cross-check, 2.2.2 the mutators, 2.3.2 the reconciliation half of `check`)
  import this validator's public surface.
- Quality gates (AGENTS.md): `make check-fmt`, `make lint` (ruff + interrogate
  100% docstring coverage + pylint-pypy), `make typecheck` (`ty`), `make test`,
  and `make audit` must all pass before each commit. `make all` runs build,
  format check, lint, typecheck, and test in sequence. For commits that touch
  Markdown (this plan, and any guide edit), also run `make markdownlint` and
  `make nixie`.

## Tolerances (exception triggers)

- Scope: if implementation requires changing more than 8 files or more than ~600
  net lines of code, stop and escalate.
- Disk evidence: if delivering any in-scope invariant appears to require reading
  `working/` contents beyond `state.toml` (a `done.flag`, `compiled.md`, or the
  `chapter-NN/` directory set), stop and escalate — that work is task 2.3.2's,
  and crossing into it breaches the checker scope split.
- Interface: if a public API beyond the new validator module, the new
  `commands/novel_state.py` app module, and the `stub.py::novel_state()` body
  must change (the envelope, the contract package, the schema, the corpus
  modules, **`names.py`/`pyproject.toml`**), stop and escalate. The registry is
  deliberately untouched (B2); needing to touch it means the entry-point
  decision must be revisited.
- Dependencies: if any new external dependency appears necessary, stop and
  escalate — do not add it.
- Corpus: if delivering the agreement suite requires editing any
  `tests/working_corpus/*` module or `tests/corpus_fixtures.py` (rather than
  consuming them unchanged), stop and escalate; the corpus is a frozen contract.
- Oracle disagreement: if the validator and the corpus oracle disagree on a
  pure-state invariant for a corpus fixture, stop, record it in
  `Surprises & Discoveries`, and escalate — a disagreement is a real finding
  (either the validator or the oracle is wrong), not something to paper over by
  loosening the assertion. (B1 pre-empts the one known disagreement; any *new*
  one escalates.)
- Iterations: if the gated suite still fails after 3 fix attempts on a work
  item, stop and escalate.
- Ambiguity: if the design §5.2 wording and the corpus oracle's structural
  re-implementation disagree on what a pure-state invariant means in a way that
  materially changes the verdict beyond the one resolved in B1, present both and
  escalate.
- Global-flag convention: if the `--human` argv pre-parse the entry point
  performs (B3) cannot be expressed without a new dependency or a change to
  `run`'s signature, stop and escalate — the convention must be expressible with
  the standard library and the existing `run` seam. The working directory is
  not parsed (it is the fixed `"working"` constant, B4); if any in-scope test
  appears to need a per-invocation working-directory override, stop and
  escalate — introducing one is a design/ADR amendment, not this task's work.

## Risks

- Risk (severity high, likelihood high): the corpus oracle includes four
  disk-evidence invariant names this task does not own; an agreement suite that
  asserts full verdict equality against the oracle would fail because the
  validator never emits the deferred names. Mitigation: the agreement suite
  restricts both sides to the six pure-state invariant names this task owns
  (intersecting the oracle's verdict and the validator's verdict with the owned
  set) before comparing. Work item 4 states this restriction explicitly and a
  test pins that the four deferred names are never emitted by the validator.
- Risk (severity high, likelihood high — RESOLVED by B1): the gate-ratio
  invariant must read the **drafted total**, not `current`. The corpus
  `by-chapter-sum-mismatch` variant sets `current = 1` while the drafts
  (68 800 words) and the all-true baseline gate booleans are unchanged; the
  oracle computes the gate ratio from the drafted total (68 800 / 80 000 = 0.86,
  gates consistent) and reports only `by-chapter-sum`. A validator that read
  `current` (1 / 80 000 ≈ 0) would mark every gate inconsistent and over-report
  `gate-ratio-consistent`, so the restricted-set equality in Work item 4 would
  fail. Mitigation: the validator computes the gate ratio from
  `sum(state.word_counts.by_chapter.values()) / target`, which equals the
  oracle's `sum(draft_words) / target` on every corpus tree (the corpus derives
  `by_chapter` from `draft_words`; no variant sets `by_chapter_override`). This
  decouples invariant 7 from invariant 3: corrupting `current` now trips only
  invariant 3. Work item 1 records the design-versus-oracle nuance; Work item 3
  drives a property-level perturbation that breaks the gate boolean *only* (not
  `by_chapter`) and one that breaks `by_chapter` *only* (not the gate booleans),
  proving the decoupling; Work item 4 keeps strict restricted-set equality and
  exercises the `by-chapter-sum-mismatch` variant explicitly.
- Risk (severity medium, likelihood medium): the §5.2 "by-chapter sum to
  current" and "gate ratio" invariants depend on values (`current`,
  `by_chapter`, `target`, the drafted total) whose corpus derivation is subtle.
  Mitigation: Work item 1 reads the oracle (`_oracle.py`
  `_check_by_chapter_sum` at line 80, `_check_gate_ratio_consistent` at line
  137) and `_specs.py` (`derive_by_chapter` at line 228, `derive_current` at
  line 243) and §5.2 line by line, pinning which quantity each invariant reads
  in the Decision Log. The agreement suite (Work item 4) then fails loudly on
  any residual divergence.
- Risk (severity medium, likelihood medium): a Hypothesis strategy that
  generates `State` objects naively produces mostly-invalid states (e.g. random
  phases rarely form a valid prefix), so the "accepts valid" half of the property
  is never exercised (the filtering trap). Mitigation: Work item 3 builds a
  `@composite` strategy that constructs coherent states by construction (a valid
  phase with its exact prefix, a `by_chapter` whose sum is assigned to `current`,
  gate booleans derived from the drafted-total ratio, `consecutive_clean` drawn
  within `[0, min(convergence_target, len(chapters))]`) and a parallel strategy
  that perturbs exactly one invariant, so both halves of the biconditional are
  driven without `assume`-heavy filtering. The `hypothesis` skill's "filtering
  trap" guidance is followed.
- Risk (severity medium, likelihood low): the `consecutive_clean <= chapters
  drafted` clause references "the number of chapters drafted", which on disk is
  the count of non-empty `draft.md` files — a disk quantity. The oracle's
  `_check_consecutive_clean_bound` (line 94) computes `drafted = sum(1 for c if
  c.draft_words > 0)` (non-empty drafts), while this task's pure-state proxy is
  `len(state.chapters)` (the manifest length). These agree on every current
  corpus variant (the single divergent variant,
  `consecutive-clean-over-chapters-drafted`, has one chapter, drafted), but they
  are **semantically different**: a manifest with planned-but-undrafted chapters
  would diverge. Mitigation: the Decision Log records the manifest-length proxy
  as a deliberate pure-state approximation, names exactly where it could diverge
  from the design's disk-quantity intent, and notes that task 2.1.3's on-disk
  cross-check runs the validator against materialised trees where the two could
  surface a disagreement — so 2.1.3 (not this task) owns reconciling the proxy
  with a live draft count. Work item 1 confirms agreement on the corpus.
- Risk (severity high, likelihood high — RESOLVED by B2): replacing or
  repointing the `novel-state` console-script breaks three registry gates
  (`test_pyproject_scripts.py::test_project_scripts_table_lists_the_five_commands`,
  `test_command_names_registry.py::test_registry_matches_project_scripts`, and
  `::test_entry_points_resolve_to_callables`, the last asserting every entry
  point resolves to a callable **on the `stub` module**). Mitigation: the entry
  point stays on `stub.py::novel_state()`, evolved in place; `names.py`,
  `pyproject.toml`, and all three gates are untouched. Work item 2 reads the
  three gates first and confirms they still pass unchanged.
- Risk (severity high, likelihood high — RESOLVED by B3): `run` stamps `human`
  and `working_dir` into the envelope on the usage (exit `2`) and state-error
  (exit `3`) paths where the command body never executes, so the `--human`
  selection must be parsed *before* `run` is called. No existing command does
  this; only test harnesses build `RunContext` directly. Mitigation: the
  Decision Log fixes the convention — `stub.py::novel_state()` pre-parses the
  `--human` boolean off `sys.argv[1:]` with a tiny standard-library splitter
  (`parse_global_flags`), builds `RunContext(command="novel-state",
  working_dir="working", human=...)` with `working_dir` the fixed design
  constant (B4, not a flag), and passes the residual argv (`--human` removed) to
  `run`. Work item 2 implements and pins this with a behavioural test that
  drives `--human` and a usage error through the *entry point* (not just `run`)
  and asserts the human rendering and the exit `2` envelope both carry
  `working_dir == "working"`.
- Risk (severity low, likelihood low): `cyclopts` 4.18.0's `--help`/`--version`
  handling on the `novel-state` app returns a non-`CommandOutcome`, which `run`
  treats as exit `0` with no envelope; a behavioural test that expects an
  envelope on `--help` would fail. Mitigation: the behavioural suite asserts
  `--help`/`--version` exit `0` with no envelope (the documented `run` contract,
  runner.py lines 179-183; pinned in `test_cyclopts_contract.py`), matching the
  stub's existing exemption; it does not expect an envelope there.
- Risk (severity medium, likelihood medium): a coherent state whose
  `convergence_target` is the default `1` and `consecutive_clean` is `1` sits
  exactly on the ceiling; an off-by-one in the bound (`<` versus `<=`) would
  reject a legitimately converged state. Mitigation: the §5.2 bullet 4 wording is
  inclusive (`<= convergence_target`); Work item 3 includes explicit boundary
  cases (`consecutive_clean == convergence_target` accepted;
  `consecutive_clean == convergence_target + 1` rejected) and the roadmap-named
  raised-target case (a target lifted to `2` accepts `consecutive_clean == 2`).
- Risk (severity high, likelihood medium — RESOLVED by B7): the gate-ratio
  predicate divides by `state.word_counts.target`, which carries no positivity
  enforcement (`schema.py` line 254 is a plain `int`; `__post_init__` only
  freezes `by_chapter`), so a `State` with `target == 0` is structurally
  constructible and parseable. The corpus always has a positive `target`, so the
  agreement suite would not surface this, but the WI3 Hypothesis strategies draw
  `target` and a `target == 0` draw would raise `ZeroDivisionError` mid-property
  (a flake, not a verdict), and task 2.1.3 cross-checks `validate_state` against
  arbitrary materialised states where a `target == 0` state would crash the
  validator while the oracle returns gates-consistent — a validator-vs-oracle
  divergence by exception. Mitigation: the gate predicate mirrors the oracle's
  `if spec.target_words <= 0: return True` (`_oracle.py` lines 144-145) and
  returns no `gate-ratio-consistent` violation when `target <= 0`; the
  `coherent_states`/`one_perturbation` strategies draw `target >= 1` so the live
  ratio path is exercised without tripping the guard; and a targeted example pins
  the `target <= 0` verdict directly (`target == 0` and one negative `target`
  yield no gate violation). This makes `validate_state` total over every
  constructible `State`.
- Risk (severity low, likelihood low — RESOLVED by A5): the `coherent_states`
  strategy derives each gate boolean from the drafted-total ratio; if it used a
  different float comparison (`>` versus the validator's `>=`) a state landing
  `ratio` exactly on a `0.30/0.50/0.80` threshold would self-falsify. Mitigation:
  the strategy derives the gate booleans with the identical `ratio >= threshold`
  comparison the validator uses (WI3), so boundary-tie states cannot drift.
- Risk (severity low, likelihood medium): the WI2 `xfail` on the violation case
  could mask a WI3 regression where `validate_state` returns empty for a genuine
  violation. Mitigation: Work item 3's boundary and property tests assert the
  exact verdict directly (not via the behavioural `xfail`), so a silent
  empty-verdict bug fails an independent assertion even if the `xfail` removal
  alone would have passed.

## Interfaces and dependencies

Create the validator module `novel_ralph_skill/state/validate.py` with this
public surface (names stable; later tasks import them):

```python
import dataclasses
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state.schema import State


# The pure-state §5.2 invariant names this task owns. Each string equals the
# corresponding design §5.2 wording and the corpus oracle's
# CORPUS_INVARIANT_NAMES entry (the equality is pinned by a test).
PHASE_IN_ENUM: typ.Final = "phase-in-enum"
COMPLETED_PREFIX: typ.Final = "completed-prefix"
BY_CHAPTER_SUM: typ.Final = "by-chapter-sum"
CONSECUTIVE_CLEAN_BOUND: typ.Final = "consecutive-clean-bound"
CURSOR_COHERENT: typ.Final = "cursor-coherent"
GATE_RATIO_CONSISTENT: typ.Final = "gate-ratio-consistent"

# The owned set, in design §5.2 order, for callers (and task 2.3.2) that need to
# distinguish a pure-state verdict from the disk-evidence verdict.
PURE_STATE_INVARIANT_NAMES: tuple[str, ...] = (
    PHASE_IN_ENUM,
    COMPLETED_PREFIX,
    BY_CHAPTER_SUM,
    CONSECUTIVE_CLEAN_BOUND,
    CURSOR_COHERENT,
    GATE_RATIO_CONSISTENT,
)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Violation:
    """One named §5.2 invariant breach with a human-readable detail."""

    invariant: str
    detail: str


def validate_state(state: State) -> tuple[Violation, ...]:
    """Return the pure-state §5.2 invariants ``state`` violates (design §5.2).

    An empty tuple means the state is coherent under the pure-state invariants
    this validator owns. Disk-evidence invariants (§5.4) are not checked here.
    """
```

`validate_state` is pure: `State` in, ordered `tuple[Violation, ...]` out, no
filesystem, no writing. It composes one small predicate per invariant family
(phase, counts, cursor, gates), each returning a `Violation | None`, assembled
in `PURE_STATE_INVARIANT_NAMES` order so the verdict order is deterministic
(stable for snapshotting and for the agreement suite). The gate predicate reads
`sum(state.word_counts.by_chapter.values())` as the numerator (the drafted
total), per the gate-ratio Constraint and B1, and **guards the division**: when
`state.word_counts.target <= 0` it returns no `gate-ratio-consistent` violation
(it does not divide), mirroring the oracle's
`_check_gate_ratio_consistent`'s `if spec.target_words <= 0: return True` first
line (`_oracle.py` lines 144-145, B7). This makes `validate_state` **total** —
every predicate returns a `Violation | None` for every constructible `State`,
with no unguarded division — which is what task 2.1.3's arbitrary-state
cross-check needs.

Create the `novel-state` subcommand app module
`novel_ralph_skill/commands/novel_state.py` exposing:

```python
import cyclopts


def build_app() -> cyclopts.App:
    """Build the ``novel-state`` Cyclopts app with its subcommands.

    Wired with ``result_action="return_value", exit_on_error=False,
    print_error=False, help_on_error=False`` so the shared
    :func:`novel_ralph_skill.contract.runner.run` owns every exit and envelope.
    Exposes the read-only ``check`` subcommand; the mutators
    (``init``/``set-cursor``/``advance-phase``/``recount``/``reconcile``) are
    later tasks and are not registered here.

    The signature is deliberately zero-argument and stable (later tasks import
    it): the ``check`` body resolves its working directory from the process cwd
    (the fixed ``working/`` constant, B4/B5), so the builder needs no
    per-invocation value to close over. There is no working-directory parameter
    and no Cyclopts working-dir option — adding either would be a B4 defect.
    """
```

The `check` subcommand body resolves the working directory **itself** from the
process cwd — there is no injected path and no global working-dir token (B4,
B5). This keeps `build_app()` legitimately zero-argument: the body needs nothing
from the builder beyond the design's fixed constant. The body:

1. forms the `state.toml` path as `pathlib.Path("working") / "state.toml"`
   (the design's cwd-relative `working_dir="working"` constant, design line
   151), resolved against the process cwd. This is the single source of truth
   for the file `check` reads; the envelope's `working_dir` field is the same
   constant string `"working"` the entry point stamps into the `RunContext`, so
   the file read and the envelope value can never drift;
2. calls `load_state(path)`; on `FileNotFoundError`/`OSError`/
   `tomllib.TOMLDecodeError`/`KeyError`/`ValueError`/`TypeError` raises
   `StateInputError(...)` (the exit-`3` channel; `TypeError` is included because
   `parse_state` raises it at construction on a structurally wrong table, see
   parse.py line 57, advisory A2);
3. calls `validate_state(state)`; if the verdict is empty, returns
   `CommandOutcome(code=ExitCode.SUCCESS, result={"violations": []}, messages=
   ["state is coherent"])`; otherwise returns
   `CommandOutcome(code=ExitCode.ACTIONABLE_FINDING, result={"violations":
   [v.invariant for v in verdict]}, messages=[v.detail for v in verdict])`.

The entry point `novel_ralph_skill/commands/stub.py::novel_state()` is evolved
in place (per B2) to:

```python
def novel_state() -> None:
    """Console-script entry point for ``novel-state`` (drives the real app)."""
    # Pre-parse --human off argv BEFORE run, because run never reaches the
    # command body on the usage/state-error paths yet still stamps the envelope
    # from context (B3). working_dir is NOT parsed: it is the design's fixed
    # cwd-relative "working" constant (design line 151, B4).
    human, residual = parse_global_flags(sys.argv[1:])
    app = build_app()
    run(
        app,
        residual,
        RunContext(command="novel-state", working_dir="working", human=human),
    )
```

where `parse_global_flags(argv) -> tuple[bool, list[str]]` is a small,
standard-library splitter (no new dependency) that recognises a `--human`
boolean flag in **any** position, removes every occurrence of it from the
vector, and returns `(human, residual)`. It does **not** parse a working-dir
option (there is none — B4). It lives in `commands/novel_state.py` (so `stub.py`
only imports and calls it, keeping `stub.py`'s other four functions untouched)
and is unit-tested directly. The working directory the `check` body reads
(`Path("working")`, resolved against cwd) and the `working_dir` the envelope
records (the constant `"working"` stamped into `RunContext`) are the **same
fixed string**, so there is exactly one source of truth and they cannot drift
(this closes B5: the body never needs a value injected by the builder).

This is the **first command on the real `run` path**, so the `--human`
pre-parse via `parse_global_flags` is the convention all four later commands
inherit; the working-directory resolution (cwd-relative `working/`) is likewise
the shared convention. The Decision Log records both (B3/B4).

Re-export the validator's public names (`validate_state`, `Violation`,
`PURE_STATE_INVARIANT_NAMES`, and the six name constants) from
`novel_ralph_skill/state/__init__.py`, alongside the existing schema exports
(append to the existing `__all__`).

Dependencies: the validator uses standard-library `dataclasses`/`enum` and the
`novel_ralph_skill.state` schema only. The command uses `cyclopts` (locked
4.18.0) and the `novel_ralph_skill.contract` package. Tests use `hypothesis`
(locked 6.155.7) and, if a snapshot proves warranted for the envelope, `syrupy`
(locked 5.3.2). No `cuprum`/`cyclopts`-subprocess, because this command shells
out to nothing (design §9 line 710: "v1 commands shell out to nothing"; verified
against `cuprum` 0.1.0 `DEFAULT_CATALOGUE`/`ProgramCatalogue` in
`/data/leynos/Projects/cuprum/cuprum/catalogue.py`, an executable allowlist for
shelling out, which is not exercised here).

## Plan of work

Stage A is understand-and-pin (no production code). Stage B writes the failing
tests. Stage C implements the validator and the command to green. Stage D
hardens, documents, and pins the scope boundary. Each work item below is
independently committable and gate-passable.

### Work item 1 — Pin each pure-state invariant's exact quantity (no code)

Implements: design §5.2 (the invariant definitions), §5.4 (the scope split).

Read `docs/novel-ralph-harness-design.md` §5.2 and §5.4 and
`tests/working_corpus/_oracle.py`, `_variants.py`, and `_specs.py` end to end.
For each of the six pure-state invariants this task owns, record in this plan's
`Decision Log` the **exact** `State` quantity the check reads and the precise
comparison, cross-checked against the oracle's structural re-implementation:

- `phase-in-enum`: `state.phase.current in PHASE_ORDER`.
- `completed-prefix`: `state.phase.completed == PHASE_ORDER[:index(current)]`
  (and how an out-of-enum `current` is handled — the oracle treats it as
  invariant 1's concern and passes the prefix check, line 74; mirror that so a
  bad phase reports exactly `phase-in-enum`, not two violations).
- `by-chapter-sum`: `sum(state.word_counts.by_chapter.values()) ==
  state.word_counts.current` (matches the oracle's `_check_by_chapter_sum`,
  line 80, which reads the materialised `state.toml`).
- `consecutive-clean-bound`: `convergence_target >= 1`,
  `0 <= consecutive_clean <= convergence_target`, and
  `consecutive_clean <= len(state.chapters)` (the manifest-length proxy for
  "chapters drafted"). Record (per the consecutive-clean Risk) that the oracle's
  `_check_consecutive_clean_bound` (line 94) uses `drafted = count of non-empty
  drafts`, that the two agree on every current corpus variant, and that the
  proxy is a deliberate pure-state approximation whose divergence (a planned but
  undrafted chapter) is task 2.1.3's to reconcile against disk.
- `cursor-coherent` (state-only part): `current_scene >= 0`,
  `current_beat >= 0`, `current_chapter >= 0`, and
  `current_chapter <= len(state.chapters)` (mirror the oracle's
  `_check_cursor_coherent`, line 124, which also enforces
  `0 <= current_chapter`; advisory A1). Record that this follows the
  oracle's structural reading (bound `current_chapter` against the manifest
  length, check scene/beat non-negativity) over the design's literal
  "never reference a chapter past `current_chapter`" scene-vs-`current_chapter`
  clause, and that the "zero until plans exist" disk sub-clause is task
  2.1.4/2.3.2's. Confirm the two bijection variants (`manifest-extra-entry`,
  `draft-without-manifest-entry`) do not perturb the cursor, so the manifest
  length still bounds it correctly there.
- `gate-ratio-consistent`: when `target <= 0` there is **no** violation (the
  predicate short-circuits before dividing, mirroring the oracle's
  `if spec.target_words <= 0: return True` at `_oracle.py` line 144); otherwise
  each knitting gate boolean equals
  `(drafted_total / target) >= threshold` for the §5.2 thresholds
  `0.30/0.50/0.80`, where `drafted_total = sum(by_chapter.values())`. Record the
  B7 guard alongside the full B1 nuance: the design literal is `current /
  target`, but the design also
  asserts invariant 3 (`current == sum(by_chapter)`), so on any invariant-3-
  coherent state the two readings coincide; the corpus deliberately breaks
  invariant 3 in `by-chapter-sum-mismatch` while keeping the drafts and gate
  booleans honest, and the oracle computes the gate ratio from the drafted total
  precisely to keep invariant 7 independent of invariant 3. The validator
  follows the oracle (drafted total) so the two agree on every corpus tree and
  the invariants stay decoupled; when invariant 3 holds the validator's reading
  equals the design literal. Note that no corpus variant sets
  `by_chapter_override`, so `sum(by_chapter) == sum(draft_words)` everywhere.

Confirm the four disk-evidence names (`manifest-disk-bijection`,
`done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`)
are out of scope and record that this task does not implement them.

Documentation to read: design §5.2, §5.4, §2.3; `_oracle.py`; `_variants.py`;
`_specs.py` (the quantities the corpus writes); `docs/execplans/roadmap-2-1-1.md`
(the schema field names). Skills to load: `leta` (navigate the oracle and
schema), `python-router` → `python-data-shapes` (reading frozen domain objects),
`en-gb-oxendict` (prose).

Tests: none (analysis only). Output is the pinned per-invariant quantity table
recorded in this plan's Decision Log.

Validation: no code, so no code gate. Commit this plan update with
`make markdownlint` and `make nixie` passing (this plan is the only changed
Markdown).

### Work item 2 — Stand up the `novel-state` app, the global-flag parse, and the `check` skeleton, failing tests first

Implements: design §4.1 (`check` subcommand), §3.1/§3.2/§3.3 (envelope, exit
codes, checker segregation); ADR-003 §3.1 (the `--human` flag and the
`working_dir` envelope field — not a CLI flag; B4).

Add `novel_ralph_skill/commands/novel_state.py` with `build_app()` (zero-arg,
per Interfaces and B5), a `check` subcommand whose body resolves
`Path("working") / "state.toml"` from cwd, calls `load_state`, and applies a
**stand-in** `validate_state` that returns an empty verdict (so the skeleton
compiles before Work item 3 lands the real checks), and
`parse_global_flags(argv) -> tuple[bool, list[str]]` (per Interfaces; `--human`
only, no working-dir). Evolve `novel_ralph_skill/commands/stub.py::novel_state()`
in place (per B2) to call `parse_global_flags`, build
`RunContext(command="novel-state", working_dir="working", human=...)`, and drive
the app through `run`; leave the other four stub functions and `names.py`/
`pyproject.toml` untouched.

Read `tests/test_command_stubs.py`, `tests/test_stub.py`,
`tests/test_console_scripts_e2e.py`, `tests/test_cyclopts_contract.py`,
`tests/test_command_names_registry.py`, and `tests/test_pyproject_scripts.py`
first. Confirm the three registry gates still pass unchanged (they must, because
the entry point stays on `stub`): `test_pyproject_scripts.py::
test_project_scripts_table_lists_the_five_commands`, `test_command_names_registry
.py::test_registry_matches_project_scripts`, and `::test_entry_points_resolve_to_
callables` (the last only asserts `callable(getattr(stub, func))`).

**Exactly which assertions break, and their new exit codes (B6).** Verified
against the gates, evolving `novel_state()` to drive `run` against `./working/`
changes the exit code of the two tests that invoke or run the *real*
`novel_state` callable with no `working/` present — they move from `2` to
**`3`** (state error: `load_state` cannot find `working/state.toml`), not `2`:

- `tests/test_command_stubs.py::test_entry_point_callable_exits_two`
  (parametrized over `ENTRY_POINTS`, calls `novel_state()` with a clean
  `[name]` argv via `monkeypatch.setattr(sys, "argv", ...)`). For the
  `novel-state` parameter it now exits `3`. Narrow it: drop `novel-state` from
  the parametrization (or `xfail`/skip that one id) and assert the four remaining
  entry points still exit `2`; move the `novel-state` exit-`3`-with-no-`working/`
  expectation into the new behavioural module.
- `tests/test_console_scripts_e2e.py::_assert_scripts_exit_two` (helper looping
  over `COMMAND_NAMES`, run by `test_console_scripts_install_and_exit_two`). The
  installed `novel-state` run with no args in a cwd lacking `working/` now exits
  `3`. Narrow `_assert_scripts_exit_two` to the four still-stubbed names; add a
  dedicated `novel-state` e2e (below) that materialises a `working/` tree and
  asserts exit `0`.

The three `make_stub_app`-based tests are **unaffected** and must NOT be touched
(the factory is untouched): `test_command_stubs.py::test_command_result_exits_two`,
`::test_unknown_option_exits_one`, and `::test_meta_flags_exit_zero` all build
`stub.make_stub_app(name)` directly, which `novel_state()`'s evolution does not
change. If any stub suite asserts all five uniformly in a way that cannot be
narrowed without touching the registry or `names.py`, stop and escalate (the
entry-point decision would need revisiting).

**Cwd isolation for the real `novel_state` callable (A6).** The narrowed
`test_entry_point_callable_exits_two` runs the four still-stubbed entry points in
pytest's ambient cwd. Confirm no stray `working/` directory exists at the pytest
invocation root that would perturb a future real entry point's exit code; the new
behavioural module is the **only** place the real `novel-state` callable is
driven, and it does so under an explicit `monkeypatch.chdir(dest)` into a fixture
parent, so it never depends on (or is perturbed by) the ambient cwd. A test in
the behavioural module asserts the real callable's exit code is governed solely
by the chdir'd `working/`, not by the invocation root.

Write the failing **behavioural / e2e suite** `tests/test_novel_state_check.py`
(red before the command body is complete):

All these cases select a fixture working directory by `monkeypatch.chdir(dest)`
into the materialised parent (the corpus fixtures build `dest/working/` and
return the `working/` path; `chdir(dest.parent of working)` — i.e. the `dest`
passed to `build_tree`/`build_working_tree` — makes the default `./working/`
resolve to the fixture). The `check` body and the envelope both use the fixed
`working/` constant, so no flag is involved (B4).

- `novel-state check` from a cwd whose `./working/` is a `baseline_tree`
  (chdir into its parent) exits `0` with an envelope whose `ok` is `true` and
  `result.violations == []`.
- `novel-state check` from a cwd with no `./working/` (an empty `tmp_path`)
  exits `3` (state error) with `ok: false`.
- `novel-state check` from a cwd whose `./working/state.toml` is unparseable
  (build a coherent tree, then overwrite `working/state.toml` with a line such
  as `not = toml =` that `tomllib` rejects) exits `3`.
- `novel-state --help` and `novel-state --version` exit `0` with no envelope
  (the `run` exemption).
- the JSON envelope shape matches the contract field set
  (`command/schema_version/ok/working_dir/result/messages`), `command ==
  "novel-state"`, and `working_dir == "working"`.
- **the global-flag convention (B3):** driving the *entry point* (not just
  `run`) with `--human` switches stdout to the human rendering at the same exit
  code; a usage error (e.g. `novel-state bogus`) still exits `2` with an
  envelope whose `working_dir == "working"` (proving the entry point built the
  `RunContext` before `run` reached the usage path); and the residual argv after
  the `--human` strip still drives the subcommand correctly (`--human check`
  reaches the `check` body).
- **`parse_global_flags` unit tests:** `--human` recognised and removed from any
  position (leading, between tokens, trailing); absence of `--human` yields
  `human is False`; the residual argv preserves the subcommand tokens in order;
  multiple `--human` occurrences all removed. No working-dir token is parsed
  (B4): an arbitrary `--foo` token is left untouched in the residual.
- **checker segregation (design §3.3):** capture the `working/` tree before and
  after a `check` invocation and assert it is byte-for-byte unchanged.

Drive the command the way `test_contract_runner.py` and the `wrapper_app`
fixture do (build the app, call `run`), and exercise the *entry point* directly
for the global-flag cases (`monkeypatch.chdir` into the fixture parent,
`monkeypatch.setattr(sys, "argv", [...])`, catch `SystemExit`).

Add **one subprocess e2e through the installed console-script** for the genuine
end-to-end path, mirroring `test_console_scripts_e2e.py` but for `novel-state`:
materialise a coherent `working/` tree under a `tmp_path` directory (build a
`baseline_tree`-equivalent spec via `make_working_tree_spec`/`build_tree` so the
tree lands at `dest/working/`), install (or reuse the installed) `novel-state`,
and run it with cuprum setting the subprocess cwd to `dest` so the script
resolves `./working/state.toml`. Cuprum 0.1.0 supports this directly:
`sh.make(prog, catalogue=...)().run_sync(context=ExecutionContext(cwd=dest),
capture=True)` (verified against `/data/leynos/Projects/cuprum/cuprum/sh.py`
lines 168-198 `ExecutionContext.cwd` and `run_sync(context=...)` at line 441).
Assert exit `0` and `ok: true`. Because the global pytest config sets
`timeout = 30` (pyproject line 325), and a build-install-run e2e can exceed it,
mark this e2e `@pytest.mark.slow` and `@pytest.mark.timeout(180)` to supersede
the 30s default, exactly as `test_console_scripts_install_and_exit_two` does
(its module docstring documents the 180s supersession). If the e2e reuses an
already-installed script rather than rebuilding the wheel, the lighter per-test
`@pytest.mark.timeout` may be lowered, but it MUST carry an explicit marker
because the 30s default is otherwise in force.

Documentation to read: design §4.1, §3.1-§3.4; ADR-003 §3.1;
`docs/developers-guide.md` "The shared JSON envelope" and "Checker/mutator
segregation"; `runner.py`, `envelope.py`, `exit_codes.py`;
`tests/test_contract_runner.py`; the `wrapper_app` fixture;
`tests/test_cyclopts_contract.py`. Skills: `leta`, `python-router` →
`domain-cli-and-daemons` (CLI lifecycle, global flags, exit codes),
`python-testing` (fixtures, subprocess e2e, monkeypatching argv),
`en-gb-oxendict`.

Tests to add: `tests/test_novel_state_check.py` (the behavioural suite, the
subprocess e2e with the `working/` tree and the `@pytest.mark.timeout(180)`
marker, the global-flag cases, and the `parse_global_flags` unit tests). Tests
to update: narrow `test_command_stubs.py::test_entry_point_callable_exits_two`
and `test_console_scripts_e2e.py::_assert_scripts_exit_two` to the four
still-stubbed commands (B6), leaving the three `make_stub_app`-based tests
untouched. The new suite's coherent-tree, state-error, and global-flag cases
fail before the command body is wired and pass after; the invariant-violation
exit-`4` case stays red until Work item 3.

Validation: `make all` (expect the envelope/state-error/global-flag cases green,
the violation case still red until WI3). Commit once the WI2 cases are green by
marking the violation case `xfail(reason="validate_state lands in WI3")` and
removing the marker in WI3. Run `make check-fmt lint typecheck test`. Commit.

### Work item 3 — Implement `validate_state` and its Hypothesis property suite, failing tests first

Implements: design §5.2 (the six pure-state invariants), §2.3 (property-based
verification of state coherence).

Write the failing **Hypothesis property suite**
`tests/test_validate_state_property.py` (red before `validate_state` exists):

- a `@composite` `coherent_states` strategy that constructs a `State` satisfying
  every pure-state invariant by construction: a phase drawn from `PHASE_ORDER`
  with its exact prefix as `completed`; a `by_chapter` mapping whose values sum
  to the chosen `current`; `target >= 1` (the strategy pins a strictly positive
  target so the live-ratio path is exercised without tripping the `target <= 0`
  guard — B7) such that the gate booleans are set to match
  the **drafted-total** ratio (`sum(by_chapter)/target`) against
  `0.30/0.50/0.80`; `convergence_target >= 1` and `consecutive_clean` drawn in
  `[0, min(convergence_target, len(chapters))]`; a cursor with non-negative
  scene/beat and `current_chapter <= len(chapters)`. **The strategy derives each
  gate boolean with the identical `ratio >= threshold` comparison the validator
  uses (not `>`)** (A5), so a state that lands `ratio` exactly on a threshold
  (e.g. `drafted/target == 0.30`) cannot self-falsify on a tie. Property:
  `validate_state(state) == ()` for every coherent state (the "accepts valid"
  half).
- a `@composite` `one_perturbation` strategy that takes a coherent state and
  breaks exactly one named invariant. Property: the verdict is exactly the
  singleton of the perturbed invariant's name (the "rejects invalid" half, with
  the name correct). Include explicit decoupling perturbations proving B1: one
  that forces a single gate boolean against the drafted-total ratio while leaving
  `by_chapter` and `current` consistent (verdict == `{gate-ratio-consistent}`
  only), and one that sets `current` off the `by_chapter` sum while leaving the
  gate booleans honest against the drafted total (verdict == `{by-chapter-sum}`
  only). Use the `hypothesis` skill's filtering-trap guidance: construct rather
  than `assume`-filter. **No perturbation zeroes or negates `target`** (each
  draws `target >= 1`), so the `one_perturbation` strategy likewise never trips
  the `target <= 0` guard mid-property (B7); the guard's verdict is pinned by a
  dedicated example below, not by the property.
- targeted boundary tests (example-based, not property): `consecutive_clean ==
  convergence_target` accepted; `consecutive_clean == convergence_target + 1`
  rejected on `consecutive-clean-bound`; a `convergence_target` of `0` rejected;
  the roadmap-named raised-target case — a state with `convergence_target ==
  2` accepts `consecutive_clean == 2`, while the same `consecutive_clean == 2`
  under the default `convergence_target == 1` is rejected; and the **`target <=
  0` guard case (B7)** — a state constructed with `target == 0` (otherwise
  coherent) produces **no** `gate-ratio-consistent` violation (the predicate
  short-circuits instead of dividing, matching the oracle's
  `if spec.target_words <= 0: return True`), pinned directly so a future
  un-guarded division surfaces as a failing assertion rather than a
  `ZeroDivisionError` flake; assert the same for one negative `target`. These
  assert the exact verdict directly, independent of the WI2 behavioural `xfail`,
  so a silent empty-verdict bug fails here regardless.

Then implement `novel_ralph_skill/state/validate.py` with `validate_state`, the
`Violation` dataclass, the six name constants, and `PURE_STATE_INVARIANT_NAMES`
(per Interfaces), each invariant as a small `State -> Violation | None`
predicate assembled in design order; the gate predicate reads
`sum(state.word_counts.by_chapter.values())` as the numerator (B1) and
**short-circuits to `None` when `target <= 0`** before dividing (B7), so it is
total over every constructible `State`. Re-export
from `state/__init__.py`. Replace the WI2 stand-in `validate_state` in the
`check` body with the real import and remove the `xfail` on the violation case
in `tests/test_novel_state_check.py`.

Documentation to read: design §5.2, §2.3; the WI1 pinned quantity table; the
`hypothesis` skill (composite strategies, the filtering trap, example
databases); `python-verification` (why Hypothesis is the right adversary for an
invariant over generated states). Skills: `leta`, `python-router`, then
`python-verification` → `hypothesis`; `python-data-shapes` (constructing frozen
`State` objects in the strategy); `python-testing`; `en-gb-oxendict`.

Tests to add: `tests/test_validate_state_property.py` (the two properties, the
B1 decoupling perturbations, the boundary/raised-target cases, and the B7
`target <= 0` guard examples — `target == 0` and one negative `target` each yield
no `gate-ratio-consistent` violation). These exercise the §2.3 state-coherence
property and the roadmap's `consecutive_clean`/`convergence_target` success
clause directly, and pin the validator as total over every constructible
`State`.

Validation: `make all` (the property suite and the now-unblocked exit-`4`
behavioural case pass), then `make audit`. Commit.

### Work item 4 — Corpus-oracle agreement suite and the scope-boundary pin

Implements: design §5.2 / §9 (the validator agrees with the corpus oracle on the
invariants it owns); the §5.4 scope split (deferred invariants are not emitted).
This is the foundation roadmap task 2.1.3 extends to full on-disk agreement.

Add `tests/test_validate_state_corpus.py`:

- **Owned-name equality constant.** A test asserting the validator's six name
  constants equal the corpus oracle's `corpus_invariant_names` entries for the
  same invariants (consume `corpus_invariant_names` by fixture; the validator's
  constants come from the production module). This pins the shared vocabulary
  (developers-guide lines 115-118) so the two cannot drift.
- **Coherent agreement.** Parametrized over `coherent_oracle_cases`: for each
  `(spec, working)` pair, `validate_state(load_state(working / "state.toml"))`
  is empty (every coherent tree passes the pure-state invariants).
- **Incoherent agreement, restricted to owned invariants.** Parametrized over
  `incoherent_variant_names` via `incoherent_tree`: for each variant, intersect
  both the corpus oracle's verdict (`check_corpus(spec, working)`, the labels)
  and the validator's verdict (`{v.invariant for v in validate_state(state)}`)
  with `PURE_STATE_INVARIANT_NAMES`, and assert the two restricted sets are
  **equal** (strict; not papered over — B1 makes this hold). The
  `by-chapter-sum-mismatch` variant is the load-bearing case: the validator must
  name exactly `{by-chapter-sum}` (not also `gate-ratio-consistent`), proving
  the drafted-total gate numerator decoupled invariant 7 from invariant 3. For a
  variant whose label is a disk-evidence invariant, both restricted sets are
  empty (the validator correctly stays silent, because that invariant is task
  2.3.2's).
- **Deferred invariants are never emitted.** A test asserting that for every
  corpus tree (coherent and incoherent) the validator's verdict contains none of
  the four disk-evidence names (`manifest-disk-bijection`,
  `done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`).
  This pins the scope boundary so a future reader cannot mistake a deferred
  invariant for a missing one, and protects 2.3.2's surface.

Optionally add a **syrupy snapshot** of the `check` machine-mode envelope for
one coherent and one incoherent tree if the envelope `result` shape benefits
from a pinned contract (AGENTS.md snapshot rules: redact `working_dir`; keep the
snapshot to the stable `command/ok/result.violations` boundary, paired with the
semantic assertions above). Skip the snapshot if the semantic assertions already
pin the contract without churn.

Harden and document: add module docstrings to `validate.py` and
`novel_state.py` citing design §5.2/§5.4/§4.1 and ADR-003; add a paragraph to
`docs/developers-guide.md` ("State and on-disk layout" or a new "Validation"
note) naming `validate_state` as the §5.2 pure-state validator, stating the
scope split (disk-evidence invariants are task 2.3.2's), recording the
drafted-total gate numerator and the manifest-length `consecutive_clean` proxy
as deliberate pure-state readings, and noting `check` returns exit `4` on a
violation and that `novel-state` is the first command to set the `--human`
pre-parse convention and to read its state from the fixed cwd-relative
`working/` directory. Update `docs/users-guide.md` if `novel-state check`'s
behaviour is user-facing enough to document (the exit-code meanings, the
`--human` flag, the cwd-relative `working/` resolution, and the
`result.violations` payload). Do **not** document a `--working-dir` flag — there
is none (B4). Ensure interrogate reports 100% and no suppression lacks a linked
follow-up.

Documentation to read: design §5.2, §5.4, §9; developers-guide "The `working/`
fixture corpus" and "State and on-disk layout"; AGENTS.md snapshot and
documentation-maintenance rules. Skills: `leta`, `python-testing`
(parametrization, syrupy snapshot discipline), `en-gb-oxendict`.

Tests to add: `tests/test_validate_state_corpus.py` (the four agreement/scope
tests, plus the optional snapshot). These are the anti-drift guarantee task
2.1.3 builds on.

Validation: `make all` plus `make audit`; because Markdown changed
(developers-guide, possibly users-guide, and this plan), also `make markdownlint`
and `make nixie`. Commit.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-2`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-2 \
     branch --show-current
   ```

   Expect `roadmap-2-1-2`.

2. Work item 1: read §5.2/§5.4, `_oracle.py`, `_variants.py`, and `_specs.py`;
   record the pinned quantity table in this plan's Decision Log. Commit the plan
   with the Markdown gates:

   ```bash
   make markdownlint
   make nixie
   ```

3. Work item 2: add `commands/novel_state.py` (zero-arg `build_app`, the cwd-
   relative `check` skeleton, `--human`-only `parse_global_flags`), evolve
   `stub.py::novel_state()` in place, confirm the three registry gates still
   pass, narrow `test_entry_point_callable_exits_two` and
   `_assert_scripts_exit_two` to the four still-stubbed commands (B6), add the
   failing behavioural suite (including the `working/`-tree subprocess e2e with
   `@pytest.mark.timeout(180)`), then:

   ```bash
   make all
   ```

   Expect the envelope/state-error/global-flag cases green (the violation case
   `xfail`ed until WI3). Commit.

4. Work item 3: add the failing Hypothesis property suite (including the B1
   decoupling perturbations), then `state/validate.py`, re-export, drop the WI2
   `xfail`, then:

   ```bash
   make all
   make audit
   ```

   Expect all green. Commit.

5. Work item 4: add the corpus-agreement and scope-boundary suite (and the
   optional snapshot), the docstrings, and the guide paragraph, then:

   ```bash
   make all
   make audit
   make markdownlint
   make nixie
   ```

   Commit.

## Validation and acceptance

Acceptance is behavioural and observable:

- Running `make test` from the worktree root passes. The new suites
  `tests/test_novel_state_check.py`, `tests/test_validate_state_property.py`, and
  `tests/test_validate_state_corpus.py` are present; each new assertion fails
  before its work item's implementation lands and passes after.
- `novel-state check` against a coherent `working/` (the `baseline_tree` and
  every `coherent_oracle_cases` tree) exits `0` with an envelope whose `ok` is
  `true` and `result.violations == []` — the §2.3 "state coherence" property as
  an externally observable behaviour.
- `novel-state check` against an incoherent state whose single broken invariant
  is one this task owns exits `4` with that invariant named in
  `result.violations`; in particular a `consecutive_clean` above its
  `convergence_target` is rejected, and the same `consecutive_clean` within a
  raised `convergence_target` is accepted (the roadmap's named success clause);
  and the `by-chapter-sum-mismatch` variant names exactly `by-chapter-sum`,
  never also `gate-ratio-consistent` (B1).
- `novel-state check` against a missing or unparseable `state.toml` exits `3`
  (the state-error channel), writing nothing.
- `novel-state --human check` renders the human envelope at the same exit code,
  and a usage error or state error still carries `working_dir == "working"` in
  its envelope — proving the entry point pre-parses `--human` and builds the
  `RunContext` (with the fixed working-dir constant) before `run` reaches the
  body-less paths (B3/B4).
- The Hypothesis property suite shows `validate_state` returns the empty verdict
  for every constructed coherent state and the exact singleton for every
  single-perturbation state (the §5.2 state-coherence biconditional), including
  the gate-only and by-chapter-only decoupling perturbations. A targeted example
  shows a `target == 0` (and one negative-`target`) state yields **no**
  `gate-ratio-consistent` violation rather than raising `ZeroDivisionError`,
  proving `validate_state` is total and agrees with the oracle's `target <= 0`
  guard on every constructible state (B7).
- For every §1.3.2 corpus tree, the validator's verdict restricted to the six
  pure-state invariants equals the corpus oracle's labels restricted the same
  way; the validator never emits any of the four deferred disk-evidence names
  (the scope-boundary pin, and the foundation task 2.1.3 extends).
- `check` writes nothing under `working/` (the checker/mutator segregation,
  design §3.3) — asserted by comparing the `working/` tree before and after a
  `check` invocation in the behavioural suite.

Quality criteria (what "done" means):

- Tests: `make test` passes; new tests fail before and pass after each work
  item's implementation. The Hypothesis suite runs deterministically under
  `pytest-xdist` (no shared mutable state; `@composite` strategies only).
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

Every step is additive and re-runnable. The new modules
(`novel_ralph_skill/state/validate.py`,
`novel_ralph_skill/commands/novel_state.py`) and the new test modules do not
exist yet, so creating them is safe. The one mutation of existing code —
evolving `stub.py::novel_state()` from the not-implemented stub into the real
entry point — is reversible by restoring the `make_stub_app(...)` one-liner; the
other four stub functions, `names.py`, and `pyproject.toml` are untouched, so
the registry stays valid throughout. The validator and `check` write nothing
under `working/`, so no runtime artefact is ever left torn. If a gate fails, fix
forward and re-run `make all`. To abandon, `git restore` the new files and the
`stub.py::novel_state()` body; the surface is isolated under
`state/validate.py`, `commands/novel_state.py`, the `stub.py::novel_state()`
function, and `tests/test_validate_state_*` / `tests/test_novel_state_check.py`.

## Progress

- [x] Work item 1: pin each pure-state invariant's exact quantity against §5.2
  and the corpus oracle (analysis; recorded in the Decision Log).
- [x] Work item 2: stand up the `novel-state` app, the `parse_global_flags`
  global-flag parse, and the `check` skeleton (entry point evolved in `stub.py`,
  registry untouched); narrow the stub suites; add the failing
  behavioural/global-flag suite.
- [x] Work item 3: implement `validate_state` (drafted-total gate numerator) and
  its Hypothesis property suite (with the B1 decoupling perturbations); unblock
  the exit-`4` behavioural case.
- [x] Work item 4: corpus-oracle agreement suite (strict restricted-set
  equality), the scope-boundary pin, the parse-boundary discovery, and the
  documentation (snapshot skipped — the semantic assertions pin the contract
  without churn).

## Surprises & discoveries

- Work item 4 (2026-06-23): CodeRabbit raised one `critical` finding — the corpus
  suite's `except ValueError, KeyError, TypeError:` "is Python 2 syntax". It is
  actually valid py3.14 (PEP 758 parentheses-free multi-type `except`), which the
  project targets (`requires-python >= 3.14`, `target-version = "py314"`), so
  ruff's formatter *produces* the unparenthesized form and re-strips any
  parentheses added back — `ast.parse` under 3.14.3 accepts it and `make all`
  runs it. To stop the recurring false flag and the ruff tug-of-war, the
  exception set was lifted to a named module constant `_PARSE_ERRORS` and the
  clause now reads `except _PARSE_ERRORS:`, which is unambiguous on any Python and
  ruff-stable. A re-review then raised one `trivial` finding (a comment said
  "must be exactly the parse-enforced set" while the code asserts a non-empty
  subset) — fixed by rewording the comment to "non-empty subset" — and five
  `minor` bare-`assert`-message findings, declined for the same convention reason
  as WI2/WI3. All gates stay green.
- Work item 4 (2026-06-23): **`phase-in-enum` is enforced by the parser, not the
  validator.** `parse_state` constructs `Phase(current)` (`parse.py` line 82),
  which raises `ValueError` on an out-of-enum phase, so a parsed `State` can never
  carry a `phase-in-enum` violation; the validator's `_check_phase_in_enum`
  predicate only fires for a `State` constructed directly (the property suite),
  never for one loaded from disk. The corpus's `phase-not-in-enum` variant
  therefore makes `load_state` raise (the production exit-`3` state-error channel)
  rather than yielding a validator verdict, so the agreement suite cannot intersect
  a validator verdict against the oracle's `{phase-in-enum}` label for that tree.
  This is **not** a validator-vs-oracle logic disagreement (the Tolerance trigger):
  both layers reject the same incoherent state, just at different points — the
  parser at load, the oracle as a structural label. Resolution (recorded, not
  papered over): the agreement suite detects a parse-rejected tree, asserts the
  oracle's owned label is exactly the parse-enforced `{phase-in-enum}`, and skips
  the validator comparison for it; a dedicated test
  (`test_phase_in_enum_is_parser_enforced`) pins the boundary, and the
  developers-guide records it. The `_check_phase_in_enum` predicate is retained
  as it is still correct and necessary for directly-constructed `State` objects
  (and for task 2.1.3's arbitrary-state cross-check).
- Work item 3 (2026-06-22): `pylint-pypy` enforces `max-args = 4` and
  `too-many-boolean-expressions` (max 2) regardless of the global disable list,
  so two production predicates (`_check_consecutive_clean_bound`,
  `_check_cursor_coherent`) were refactored from chained `and` conditions into an
  `all((...))` over a tuple of booleans, and the property suite's `_build_state`
  was given a single frozen `_StateParams` argument instead of ten keyword
  parameters. `C1803` also required the property suite's empty-verdict assertions
  to read `not validate_state(state)` rather than `== ()`.
- Work item 3 (2026-06-22): CodeRabbit raised seven `major` findings — one asking
  the four private `_check_*` predicate docstrings be reduced to single-line
  summaries, and six repeating the WI2 bare-`assert`-message request on the
  property suite. All seven are **not actionable**: `.rules/python-00.md` mandates
  NumPy-format docstrings and 100% coverage but no single-line-summary rule for
  private functions, and the multi-paragraph predicate docstrings deliberately
  mirror the corpus oracle's own multi-paragraph `_check_*` docstrings
  (`tests/working_corpus/_oracle.py`) they cross-check; the bare-assert convention
  is sanctioned by the `S101` per-file-ignore and used throughout `tests/`. All
  deterministic gates (`make all`, `make audit`) are green without the changes,
  so the findings are recorded and declined.
- Work item 2 (2026-06-22): the `check` body needs a verdict-item type before
  the real `Violation` lands in Work item 3. Rather than typing the stand-in
  `validate_state` as `tuple[object, ...]` (which fails `ty` on `.invariant`/
  `.detail`), the skeleton defines a private `_Violation` Protocol with
  `invariant`/`detail` properties; Work item 3 replaces both the stand-in and the
  Protocol with the concrete `novel_ralph_skill.state.Violation` import. The
  stand-in returns `()`, so no `_Violation` is ever constructed.
- Work item 2 (2026-06-22): `make fmt` runs `mdformat-all`, which reflows every
  Markdown file in the repository (49 files churned), not just the ones this task
  touches. As the prior tasks' stash list shows, this is recurring spurious
  churn. The churn was stashed (`spurious make-fmt mdformat churn roadmap-2-1-2`)
  rather than committed; only `ruff format` Python output is kept. The
  deterministic `make check-fmt` gate checks Python only (the Makefile notes
  "mdformat-all doesn't currently do checking"), so the stash does not affect the
  gate.
- Work item 2 (2026-06-22): CodeRabbit raised three `major` findings on
  `tests/test_novel_state_check.py` — add explicit trailing `return` to `-> None`
  test/helper functions, and add messages to bare `assert`s. These are **not
  actionable**: every existing test module in `tests/` uses bare `assert`
  (sanctioned by the `S101` per-file-ignore) and no trailing `return` on void
  test functions, and `make lint` (ruff, including the `flake8-return`/RET rules)
  passes without them — so the trailing `return` is not required by `.rules/
  python-return.md` (R501 forbids a redundant `return None`; a bare trailing
  `return` as the sole statement is not mandated). Applying the findings would
  make the new module inconsistent with the entire suite for no gate benefit, so
  they are recorded and declined.
- Work item 1 (2026-06-22): re-reading `tests/working_corpus/_oracle.py` end to
  end confirmed the plan's pins exactly, with no new disagreement. The oracle's
  `_check_consecutive_clean_bound` (lines 100-105) computes `drafted = sum(1 for
  chapter in spec.chapters if chapter.draft_words > 0)`, a disk-quantity count of
  non-empty drafts, whereas this task's pure-state proxy is `len(state.chapters)`
  (the manifest length). On the corpus they agree because every divergent
  variant drafts every manifest chapter; the one variant that lowers the count
  (`consecutive-clean-over-chapters-drafted`) keeps a single drafted chapter, so
  `drafted == len(chapters) == 1`. The divergence is a deliberate approximation
  (Decision Log entry on the manifest-length proxy) and 2.1.3 reconciles it
  against disk. No oracle disagreement triggers an escalation.
- Work item 1 (2026-06-22): the oracle's `_check_cursor_coherent` (lines
  130-134) enforces `0 <= current_chapter <= len(spec.chapters)` and
  `current_scene >= 0`, `current_beat >= 0` — exactly advisory A1's reading. The
  two bijection variants (`manifest-extra-entry`, `draft-without-manifest-entry`)
  leave `current_chapter` at the baseline (`len(_BASE_CHAPTERS)`), so the
  manifest-length bound still passes there and the validator names only
  `manifest-disk-bijection` (a deferred invariant the validator stays silent on).

## Decision log

- Decision (WI4 parse boundary): the corpus agreement suite treats a tree the
  parser rejects (`load_state` raising) as the parser enforcing the owned
  invariant the oracle labels, asserting the oracle's owned label is the
  parse-enforced `{phase-in-enum}` and skipping the (impossible) validator
  comparison for it. Rationale: `parse_state` constructs `Phase(current)`
  (`parse.py` line 82) and raises `ValueError` on an out-of-enum phase, so a
  `phase-in-enum` violation is unreachable from a parsed `State`; the corpus's
  `phase-not-in-enum` variant is therefore a load rejection (exit-`3` in
  production), not a validator verdict. This is not the Tolerance's
  oracle-disagreement trigger — the two layers agree the state is incoherent, the
  parser rejecting it before the validator runs — so it is resolved in the suite
  and pinned by `test_phase_in_enum_is_parser_enforced` rather than escalated. The
  `_check_phase_in_enum` predicate is retained for directly-constructed `State`
  objects and task 2.1.3's arbitrary-state cross-check. Date/author: 2026-06-23,
  implementing agent.
- Decision (WI4 snapshot): the optional syrupy snapshot of the `check` envelope
  is skipped. Rationale: the semantic assertions in
  `tests/test_validate_state_corpus.py` and `tests/test_novel_state_check.py`
  already pin the `command`/`ok`/`result.violations` contract directly, so a
  snapshot would add churn without additional coverage (the plan's WI4 "skip the
  snapshot if the semantic assertions already pin the contract" clause). Date/
  author: 2026-06-23, implementing agent.
- Decision (WI1 quantity table): the six pure-state invariants this task owns
  read exactly the following `State` quantities, each cross-checked against the
  oracle's structural re-implementation (`tests/working_corpus/_oracle.py`):

  | Invariant | `State` quantity and comparison | Oracle parity |
  | --- | --- | --- |
  | `phase-in-enum` | `state.phase.current in PHASE_ORDER` | `_check_phase_in_enum` (line 62) |
  | `completed-prefix` | if `current in PHASE_ORDER`: `state.phase.completed == PHASE_ORDER[: PHASE_ORDER.index(current)]`; else pass (invariant 1's concern) | `_check_completed_prefix` (line 67) |
  | `by-chapter-sum` | `sum(state.word_counts.by_chapter.values()) == state.word_counts.current` | `_check_by_chapter_sum` (line 80) |
  | `consecutive-clean-bound` | `convergence_target >= 1` and `0 <= consecutive_clean <= convergence_target` and `consecutive_clean <= len(state.chapters)` (manifest-length proxy) | `_check_consecutive_clean_bound` (line 94; oracle uses non-empty-draft count, agrees on corpus) |
  | `cursor-coherent` | `0 <= current_chapter <= len(state.chapters)` and `current_scene >= 0` and `current_beat >= 0` | `_check_cursor_coherent` (line 124) |
  | `gate-ratio-consistent` | if `target <= 0`: pass (no division); else each of `done_30/done_50/done_80` equals `(sum(by_chapter.values()) / target) >= 0.30/0.50/0.80` | `_check_gate_ratio_consistent` (line 137; drafted-total numerator, `target <= 0` guard) |

  The four disk-evidence names (`manifest-disk-bijection`,
  `done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`)
  are confirmed out of scope and are not implemented here (deferred to 2.3.2).
  Date/author: 2026-06-22, implementing agent.
- Decision (B1): the gate-ratio invariant reads the **drafted total**
  (`sum(state.word_counts.by_chapter.values()) / state.word_counts.target`), not
  `current / target`. Rationale: the design §5.2 bullet 7 literal is
  `current / target`, but the design simultaneously asserts invariant 3
  (`current == sum(by_chapter)`), so on any invariant-3-coherent state the two
  readings are identical. The corpus's `by-chapter-sum-mismatch` variant
  deliberately violates invariant 3 (`current_words_override=1`) while leaving
  the drafts and the all-true baseline gate booleans honest, and the corpus
  oracle's `_check_gate_ratio_consistent` (line 137) computes the ratio from the
  drafted total precisely so corrupting `current` (invariant 3) does not also
  trip invariant 7. A validator reading `current` would report both
  `by-chapter-sum` and `gate-ratio-consistent` on that variant while the oracle
  reports only `by-chapter-sum`, so the Work item 4 restricted-set equality
  would fail. Reading the drafted total keeps invariant 7 independent of
  invariant 3 (the design's evident intent — they are two distinct invariants),
  matches the oracle on every corpus tree (the corpus derives `by_chapter` from
  `draft_words`, so `sum(by_chapter) == sum(draft_words)`, and no variant sets
  `by_chapter_override`), and coincides with the design literal whenever
  invariant 3 holds. This resolves the round-1 B1 blocker without loosening the
  Work item 4 assertion. Date/author: 2026-06-22, planning agent.
- Decision (B2): the `novel-state` console-script entry point stays on
  `novel_ralph_skill.commands.stub:novel_state`; this task evolves that function
  in place rather than adding a separately-registered module. Rationale:
  `names.py` binds all five entry points to a single `STUB_MODULE`, and three
  gates pin it —
  `test_pyproject_scripts.py::test_project_scripts_table_lists_the_five_commands`,
  `test_command_names_registry.py::test_registry_matches_project_scripts`, and
  `::test_entry_points_resolve_to_callables` (which asserts every entry-point
  function resolves to a callable on the `stub` module). Repointing `novel-state`
  to a new module would fail all three and would require restructuring `names.py`
  to per-entry module targets, breaching the interface Tolerance and the file
  budget. Keeping the entry point on `stub` (delegating to the new
  `commands/novel_state.py` app builder) costs zero registry churn, leaves the
  three gates green, and isolates the change to one existing function plus two
  new modules. This is the Wafflecat alternative the round-1 review proposed,
  adopted. The cleaner per-command module boundary is sacrificed deliberately;
  the real app logic still lives in `commands/novel_state.py`, only the
  thin entry-point shim stays in `stub.py`. Date/author: 2026-06-22, planning
  agent.
- Decision (B3): the global `--human` flag is parsed off `sys.argv[1:]` by the
  entry point (`stub.py::novel_state()`, via a standard-library
  `parse_global_flags` helper in `commands/novel_state.py`) **before** `run` is
  called; the residual argv (`--human` removed) is passed to the app. Rationale:
  `run` (runner.py lines 161-188) stamps `context.human` into every envelope,
  including the usage (exit `2`, lines 163-170) and state-error (exit `3`, lines
  171-177) paths where the command body never executes, so `run` cannot recover
  the human selection from the body's return value — it must be resolved before
  `run`. No existing command does this (only `test_contract_runner.py::_run`
  builds `RunContext` directly), so this task sets the convention.
  `novel-state` is the first command on the real `run` path, so all four later
  commands (2.2.2, 2.3.x) inherit this `parse_global_flags` `--human` convention.
  A behavioural test pins it by driving the entry point with `--human` and with
  a usage error and asserting both render correctly and carry the fixed
  `working_dir`. Date/author: 2026-06-22, planning agent.
- Decision (B4): the working directory is the design's **fixed cwd-relative
  constant `"working"`**, not a CLI flag. The entry point passes
  `RunContext(command="novel-state", working_dir="working", human=...)`
  unconditionally; the `check` body reads `Path("working") / "state.toml"`
  relative to the process cwd. Rationale: a repository-wide search of
  `docs/novel-ralph-harness-design.md`, `docs/users-guide.md`, and every
  `docs/adr-*.md` finds **no** `--working-dir` flag, `--working` option, or any
  per-invocation working-directory override. ADR-003 §3.1 mandates only the
  `--human` flag and the `working_dir` *envelope field*; the design fixes
  `working_dir` to `"working"` (design line 151) and defines exit `3` as
  "working dir absent" (design line 189). The round-2 plan invented a
  `--working-dir VALUE` flag and mis-attributed it to ADR-003 §3.1; this is
  dropped. It is also unnecessary: the corpus fixtures materialise `dest/working/`
  and tests select a fixture by `monkeypatch.chdir(dest)`, relying on the default
  `working/`. Eliminating the flag yields a single source of truth for the
  working directory (the envelope value and the file path are the same constant),
  removing the cross-command drift the round-2 pre-mortem warned of. Should a
  working-directory override ever be wanted, it is a design/ADR amendment, not a
  side effect of this command's plan. Date/author: 2026-06-22, planning agent.
- Decision (B5): `build_app()` is zero-argument and the `check` body resolves
  its own working directory from cwd; no value is injected by the builder or
  carried in the residual argv. Rationale: with B4's fixed `"working"` constant,
  the body needs nothing per-invocation to close over, so the
  `conftest.py::wrapper_app` closure pattern is unnecessary here and the pinned
  zero-arg `build_app()` signature (which later tasks import) is consistent with
  the data flow. The round-2 plan's "via a closure or a Cyclopts default" escape
  hatch — which a zero-arg builder cannot satisfy and which a stripped argv
  defeats — is removed. Date/author: 2026-06-22, planning agent.
- Decision (B6): evolving `novel_state()` to drive `run` against `./working/`
  changes two gate assertions from exit `2` to exit `3` (state error, no
  `working/` present), and they are narrowed accordingly:
  `test_command_stubs.py::test_entry_point_callable_exits_two` (drop/skip the
  `novel-state` parameter; the four other entry points still exit `2`) and
  `test_console_scripts_e2e.py::_assert_scripts_exit_two` (narrow the loop to the
  four still-stubbed names). The three `make_stub_app`-based tests
  (`test_command_result_exits_two`, `test_unknown_option_exits_one`,
  `test_meta_flags_exit_zero`) are **unaffected** (the factory is untouched) and
  must not be edited. The new `novel-state` subprocess e2e materialises a coherent
  `working/` tree under a tmp dir and runs the installed script with cuprum's
  `ExecutionContext(cwd=dest)` (verified against `cuprum/sh.py` lines 168-198 and
  the `run_sync(context=...)` seam at line 441) so it resolves `./working/` and
  exits `0`; it carries `@pytest.mark.slow` and `@pytest.mark.timeout(180)` to
  supersede the global `timeout = 30` (pyproject line 325). Date/author:
  2026-06-22, planning agent.
- Decision (B7): the gate-ratio predicate guards its division — when
  `state.word_counts.target <= 0` it returns no `gate-ratio-consistent`
  violation (it does not divide), exactly mirroring the corpus oracle's
  `_check_gate_ratio_consistent` first line `if spec.target_words <= 0: return
  True` (`_oracle.py` lines 144-145). Rationale: B1 pinned the gate numerator to
  the drafted total and claimed structural agreement with the oracle, but omitted
  the oracle's `target <= 0` guard. `WordCounts.target` is a plain `int` with no
  positivity enforcement (`schema.py` line 254; `__post_init__` only freezes
  `by_chapter`), so a `State` with `target == 0` or negative is structurally
  constructible and parseable; without the guard the predicate divides by zero
  and raises `ZeroDivisionError` rather than returning a verdict. That would (a)
  flake the WI3 Hypothesis suite whenever the `target` draw is `0`, and (b) crash
  the public `validate_state` surface when task 2.1.3 cross-checks it against an
  arbitrary materialised `target == 0` state, where the oracle returns
  gates-consistent — a silent validator-vs-oracle divergence by exception, the
  same drift class the round-1 pre-mortem flagged for B1, one task deeper. The
  corpus always has a positive `target`, so WI4's agreement suite would not catch
  this; it must be fixed in the plan. The guard makes `validate_state` **total**:
  every predicate returns a `Violation | None` for every constructible `State`,
  with no unguarded arithmetic — which is what task 2.1.3's arbitrary-state
  cross-check needs. Correspondingly, the WI3 `coherent_states` and
  `one_perturbation` strategies draw `target >= 1` (so the live ratio path is
  exercised without tripping the guard), and a targeted example pins the
  `target <= 0` verdict directly (`target == 0` and one negative `target` each
  yield no gate violation). The guard is pinned in the Interfaces gate-predicate
  description, the Constraints, WI1's gate pin, and WI3's strategy and
  implementation note. Date/author: 2026-06-22, planning agent.
- Decision (A5): the WI3 `coherent_states` strategy derives each gate boolean
  with the identical `ratio >= threshold` comparison the validator uses (not
  `>`), so a state landing `ratio` exactly on a `0.30/0.50/0.80` threshold cannot
  self-falsify on a floating-point tie. Rationale: the validator and the oracle
  both compare `ratio >= threshold`; the coherent-by-construction strategy must
  reuse the same comparison or a boundary-tie state would be generated as
  "coherent" yet rejected by the validator. Date/author: 2026-06-22, planning
  agent.
- Decision: this task implements only the pure-state §5.2 invariants; the four
  disk-evidence invariants are deferred to task 2.3.2.
  Rationale: the design splits `check` along the checker/mutator boundary (§5.4)
  into §5.2 invariant validation and §5.4 disk reconciliation, and the roadmap
  assigns the disk-evidence half (done.flag/compiled.md reconstruction,
  manifest-disk bijection, contradictory-disk refusal, pending-turn
  reconciliation) explicitly to 2.3.2 (roadmap.md 377-401). Implementing them
  here would breach the scope split and the Tolerances.
  Date/author: 2026-06-22, planning agent.
- Decision: a §5.2 invariant violation returns exit `4` (ACTIONABLE_FINDING),
  not `1` or `3`. Rationale: design §3.2 and §5.4 — `check` "exits 4 to signal
  an actionable finding" the agent adjudicates; a missing/unparseable
  `state.toml` is the separate exit-`3` state-error channel. ADR-003 Table 2
  fixes the same split. Date/author: 2026-06-22, planning agent.
- Decision: the validator's invariant-name vocabulary equals the corpus oracle's
  `CORPUS_INVARIANT_NAMES` for the six owned invariants, but the constants are
  defined in the production module (not imported from `tests/`); a test pins the
  equality. Rationale: developers-guide lines 115-118 require task 2.1.2's
  validator to "agree with the corpus labels by keying on the same
  `CORPUS_INVARIANT_NAMES` strings", but production code must not depend on test
  code. Date/author: 2026-06-22, planning agent.
- Decision: `consecutive_clean`'s "chapters drafted" ceiling is the manifest
  length (`len(state.chapters)`), the pure-state proxy, not a live disk walk of
  non-empty `draft.md` files. Rationale: keeps the check pure (no filesystem),
  matches the design §5.1 authoritative planned set, and agrees with the corpus
  oracle's `_check_consecutive_clean_bound` (line 94) on every current corpus
  variant (the one divergent variant has a single drafted chapter). The proxy is
  a **deliberate pure-state approximation**: it diverges from the design's
  disk-quantity intent only when the manifest holds a planned-but-undrafted
  chapter, and reconciling that against a live draft count is task 2.1.3's
  on-disk cross-check, not this task's. Re-confirmed against `_oracle.py` in Work
  item 1. Date/author: 2026-06-22, planning agent.
- Decision: `cursor-coherent` follows the oracle's structural reading — bound
  `current_chapter <= len(state.chapters)` and require `current_scene >= 0`,
  `current_beat >= 0` — over the design's literal "never reference a chapter past
  `current_chapter`" scene-vs-`current_chapter` clause, and defers the "zero
  until plans exist" disk sub-clause to task 2.1.4/2.3.2. Rationale: the oracle's
  `_check_cursor_coherent` (line 124) is the corpus's authoritative structural
  reading, the agreement suite keys on it, and the scene/beat-against-
  `current_chapter` and zero-until-plans clauses both need on-disk scene/beat
  plans this task cannot read. Date/author: 2026-06-22, planning agent.
- Decision: `cuprum`/`cmd-mox`/`pytest-bdd`/`crosshair`/`mutmut` are out of
  scope. Rationale: this command shells out to nothing (design §9 line 710,
  verified against `cuprum` 0.1.0's executable-allowlist `ProgramCatalogue` in
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`), so no subprocess boundary
  or command mock is needed; `pytest-bdd`, `crosshair`, and `mutmut` are not in
  `uv.lock`, so behavioural tests are plain pytest and the invariant
  verification uses the locked `hypothesis` 6.155.7. Adding any of these is a
  Tolerance breach. Date/author: 2026-06-22, planning agent.
- Decision: state-coherence verification uses Hypothesis (locked 6.155.7), not
  CrossHair or mutmut. Rationale: §2.3 names "property-based tests over generated
  states", and the property is an invariant over a generated state space —
  Hypothesis's home ground (`python-verification` routing). CrossHair and mutmut
  are not in `uv.lock`. Date/author: 2026-06-22, planning agent.

## Outcomes & retrospective

All four work items landed as planned, each an atomic gated commit:

1. Work item 1 pinned the six pure-state invariant quantities against §5.2 and
   the corpus oracle (analysis only), with the consolidated table in the Decision
   Log.
2. Work item 2 stood up the `novel-state` app, the `parse_global_flags` `--human`
   pre-parse, and the `check` skeleton (a stand-in validator behind a `_Violation`
   Protocol), evolved `stub.py::novel_state()` in place, and narrowed the two
   stub suites — the registry stayed untouched and its three gates stayed green.
3. Work item 3 implemented `validate_state` (drafted-total gate numerator, the
   `target <= 0` guard, total over every constructible `State`) and its
   Hypothesis property suite, then wired the real validator into `check` and
   dropped the exit-`4` xfail.
4. Work item 4 added the corpus-oracle agreement suite (strict restricted-set
   equality, the load-bearing `by-chapter-sum-mismatch` case), the
   deferred-name scope-boundary pin, and the documentation.

The one substantive discovery was the **parse boundary for `phase-in-enum`**: the
parser, not the validator, enforces a valid `phase.current`, so the corpus
`phase-not-in-enum` tree is a load rejection rather than a validator verdict. It
was resolved in the agreement suite and pinned by a dedicated test rather than
escalated, because the two layers agree the state is incoherent — they just reject
it at different points. The `make fmt` `mdformat-all` markdown churn (recurring
across prior tasks) was stashed, not committed; only `ruff format` output was
kept. CodeRabbit's bare-`assert`-message and single-line-docstring findings were
declined as contradicting the established `tests/` conventions (the `S101`
per-file-ignore, multi-paragraph private docstrings mirroring the oracle) with no
backing project rule and all deterministic gates green.

`make all` and `make audit` are green at HEAD; `make markdownlint` and `make
nixie` pass for the touched Markdown. Task 2.1.3 (the on-disk cross-check) and
2.3.2 (the disk-evidence half of `check`) build on the stable validator surface
and the manifest-length/drafted-total readings recorded here.

## Revision note

Round-2 revision (2026-06-22). Resolves the three round-1 Logisphere blockers in
the plan rather than deferring them:

- **B1 (gate-ratio quantity):** the validator's gate numerator is now pinned to
  the **drafted total** (`sum(by_chapter.values())`), matching the corpus
  oracle's `_check_gate_ratio_consistent` and decoupling invariant 7 from
  invariant 3, so the Work item 4 restricted-set equality holds strictly on the
  `by-chapter-sum-mismatch` variant. Constraints, Risks, the Interfaces gate
  predicate, Work item 1's pin, Work item 3's decoupling perturbations, and Work
  item 4's load-bearing case were all updated; the prior "current/target isolates
  7 from 3" reasoning (which was backwards) is removed.
- **B2 (entry-point rewiring):** the console-script entry point stays on
  `stub.py::novel_state()`, evolved in place; `names.py`, `pyproject.toml`, and
  the three registry gates are untouched. The "separate registered module"
  interface is dropped in favour of a thin `stub` shim delegating to the new
  `commands/novel_state.py` app builder. Context, Constraints, Tolerances, the
  Risks (now RESOLVED), Work item 2, and the recovery section reflect this.
- **B3 (`--human`/`--working-dir` parsing):** the plan now fixes the convention
  — the entry point pre-parses the global flags off argv via a standard-library
  `parse_global_flags` helper before calling `run`, defaulting `working_dir` to
  `"working"`, and threads them into `RunContext`. Work item 2 implements and
  pins it with behavioural and unit tests; the Decision Log records it as the
  project convention all four later commands inherit.

Advisory items A1 (consecutive-clean proxy), A2 (cursor bijection variants), A3
(cursor structural reading), and A4 (WI2 `xfail` independence) are folded into
the Decision Log, Risks, and Work item 3. Library versions remain pinned to
`uv.lock` (`cyclopts` 4.18.0, `hypothesis` 6.155.7, `syrupy` 5.3.2, `cuprum`
0.1.0 — the last unused).

Round-3 revision (2026-06-22). Resolves the three round-2 Logisphere blockers,
adopting the reviewer's Wafflecat alternative (cwd-relative `working/`,
`--human`-only pre-parse):

- **B4 (`--working-dir` is an uncited, unneeded, mis-attributed flag):** the
  invented `--working-dir VALUE` flag is dropped entirely. Verified against
  source: no `--working-dir` flag exists in the design, the ADRs, or the
  users-guide; ADR-003 §3.1 mandates only `--human` and the `working_dir`
  *envelope field*; the design fixes `working_dir` to `"working"` (line 151) and
  defines exit `3` as "working dir absent" (line 189). The entry point now stamps
  the fixed `working_dir="working"` into the `RunContext` and the `check` body
  reads `Path("working") / "state.toml"` from cwd. The "convention all four later
  commands inherit" framing for the flag is removed; only the `--human` pre-parse
  is inherited. Updated: the Global-flag definition, Context item 6, the runner.py
  and stub.py consumer notes, the Constraints/Tolerances, the B3 Risk, the
  Interfaces entry-point block and `parse_global_flags` signature
  (`-> tuple[bool, list[str]]`), Work items 2 and 4, the Validation section, and
  a new Decision-Log entry B4.
- **B5 (`build_app()` zero-arg cannot deliver the working dir):** with B4's fixed
  constant, the `check` body resolves `./working/` itself, so `build_app()`
  stays legitimately zero-argument and the data flow is single-sourced (the
  envelope value and the file path are the same constant). The round-2 "via a
  closure or a Cyclopts default" non-working escape hatch is removed; the
  Interfaces `check`-body and `build_app()` docstring now pin the cwd resolution.
  New Decision-Log entry B5.
- **B6 (stub/e2e narrowing under-specified):** Work item 2 now enumerates the
  exact breaking assertions and their new exit code `3` (not `2`):
  `test_entry_point_callable_exits_two` and `_assert_scripts_exit_two` move to
  exit `3` for `novel-state` with no `working/` and are narrowed to the four
  still-stubbed commands; the three `make_stub_app`-based tests are untouched.
  The new `novel-state` subprocess e2e materialises a coherent `working/` tree
  and sets the subprocess cwd via cuprum `ExecutionContext(cwd=dest)` (verified
  against `cuprum/sh.py`), asserting exit `0`, and carries
  `@pytest.mark.timeout(180)` to supersede the global `timeout = 30` (pyproject
  line 325). New Decision-Log entry B6.

Advisory A1 (assert `current_chapter >= 0` to match the oracle) is folded into
Work item 1's cursor pin and the Interfaces predicate; advisory A2 (`TypeError`
in the exit-3 set) is added to the `check` body's exception mapping. Library
versions remain pinned to `uv.lock`. Implementation has not started.

Round-4 revision (2026-06-22). Resolves the single round-3 Logisphere blocker
(B7) and folds in advisories A5 and A6:

- **B7 (unguarded `target` division in the gate-ratio predicate):** the plan
  pinned the gate numerator to the drafted total and claimed structural agreement
  with the oracle's `_check_gate_ratio_consistent`, but omitted that oracle's
  first line — `if spec.target_words <= 0: return True` (`_oracle.py` lines
  144-145, verified against source). `WordCounts.target` is a plain `int` with no
  positivity enforcement (`schema.py` line 254, verified; `__post_init__` only
  freezes `by_chapter`), so a `target == 0` `State` is constructible and would
  raise `ZeroDivisionError` in the predicate — flaking the WI3 Hypothesis suite
  and crashing the public `validate_state` surface against an arbitrary
  `target == 0` state that task 2.1.3 cross-checks (where the oracle returns
  gates-consistent, a divergence by exception). Resolution: (1) the gate
  predicate now short-circuits to no `gate-ratio-consistent` violation when
  `target <= 0`, mirroring the oracle exactly, making `validate_state` total over
  every constructible `State`; and (2) the WI3 `coherent_states`/`one_perturbation`
  strategies draw `target >= 1` (exercising the live ratio path without tripping
  the guard) plus a targeted example pinning the `target <= 0` verdict directly
  (`target == 0` and one negative `target` yield no gate violation). The guard is
  pinned in the Interfaces gate-predicate description, the Constraints, WI1's gate
  pin, and WI3's strategy and implementation note; new Risk and Decision-Log (B7)
  entries record it, and the Validation/acceptance section adds the corresponding
  observable.
- **A5 (float threshold-tie parity):** WI3's `coherent_states` strategy now
  derives each gate boolean with the identical `ratio >= threshold` comparison
  the validator uses (not `>`), pinned in WI3 and a new Decision-Log (A5) entry
  and Risk, so a state landing `ratio` exactly on a `0.30/0.50/0.80` threshold
  cannot self-falsify.
- **A6 (cwd isolation for the real callable):** WI2 now records that the new
  behavioural module is the only place the real `novel-state` callable is driven,
  always under an explicit `monkeypatch.chdir(dest)`, and confirms the narrowed
  still-stubbed entry-point tests are not perturbed by a stray `working/` at the
  pytest invocation root.

Library versions remain pinned to `uv.lock` (`cyclopts` 4.18.0, `hypothesis`
6.155.7, `syrupy` 5.3.2, `cuprum` 0.1.0 — the last unused). Implementation has
not started.
