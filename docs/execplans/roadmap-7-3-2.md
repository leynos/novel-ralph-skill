# Collapse the multiplexer mount lines onto a registry-driven construction table

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

The `novel` multiplexer's builder,
`novel_ralph_skill.commands.novel.build_multiplexer`, mounts its five operations
with five hand-copied lines, each pairing a leaf module's `build_app()` with a
literal mount-verb string:

```python
# novel_ralph_skill/commands/novel.py, build_multiplexer() today
app = make_contract_app(MULTIPLEXER_NAME)
app.command(novel_state.build_app(), name="state")
app.command(_novel_done.build_app(), name="done")
app.command(_compile.build_app(), name="compile")
app.command(_desloppify.build_app(), name="desloppify")
app.command(_wordcount.build_app(), name="wordcount")
```

The mount verbs (`"state"`, `"done"`, …) are already derived once, as data, from
the `SUBCOMMAND_NAMES` registry through `_VERB_FOR_SUBCOMMAND`
(`novel.py` lines 46–48), yet these five mount lines re-spell each verb inline
and re-list each leaf builder by hand. A sixth operation, a re-order, or a verb
rename must touch five copied lines, and nothing pins the mount set against the
registry: the verbs the dispatcher *names* (`SUBCOMMAND_NAMES`) and the verbs the
dispatcher *mounts* can silently drift apart.

After this change, the five mount lines collapse onto a single registry-driven
construction table: a verb-keyed mapping of mount verb to its leaf `build_app`
factory, consumed by one loop that mounts each leaf under the verb the registry
names. The five verbs come from `SUBCOMMAND_NAMES` (via the existing
`_VERB_FOR_SUBCOMMAND` derivation), so the names the dispatcher mounts and the
names it stamps cannot drift; a new structural test pins the mount set against
the registry so a future divergence fails a test rather than shipping. The
public entry-point function name (`novel.main`), the single `[project.scripts]`
target (`novel = "novel_ralph_skill.commands.novel:main"`), and the per-command
deferred-import laziness are preserved exactly.

Success is observable four ways. First, `build_multiplexer()` builds the parent
app by iterating a single verb→`build_app` table rather than five hand-copied
`app.command(...)` lines, and the table's verb set is the registry's verb set by
construction (no inline verb literals survive in the mount path). Second, the
existing multiplexer shape suite (`tests/test_multiplexer_dispatch.py`) and
behavioural parity suite (`tests/test_multiplexer_behaviour.py`) pass unchanged:
`build_multiplexer()` still registers exactly the five mount names, still carries
the four-flag contract, and still produces byte-for-byte-equal envelopes against
each leaf driven directly. Third, a new structural test
(`tests/test_multiplexer_mount_table.py`) asserts the construction table's verbs
equal the registry's bare-verb set (`set(_SUBCOMMAND_FOR_VERB)`, equivalently
`set(_VERB_FOR_SUBCOMMAND.values())`) and that every table entry's
`build_app` is the leaf module's own `build_app`, so a drifted or dropped mount
fails here. Fourth, the console-scripts end-to-end suite
(`tests/test_console_scripts_e2e.py`), which builds and installs the real wheel
and runs the installed `novel` script by absolute path for every subcommand,
stays green, proving the installed-binary behaviour is unchanged.

This is a pure-Python, internal dispatch-layer refactor. It changes no
command-line surface, no envelope wire format, no exit-code policy, and no
external-library behaviour. It serves the step-7.3 command-facade single-home
hypothesis — one registry-driven home for the multiplexer's entry-point
construction — per roadmap task 7.3.2 (`docs/roadmap.md` lines 2849–2871). It
cites design §4 (`docs/novel-ralph-harness-design.md` lines 274–289), ADR 007
(`docs/adr-007-command-surface-novel-multiplexer.md`, superseding ADR 005
`docs/adr-005-command-surface-five-scripts.md`), and the names registry
(`novel_ralph_skill/commands/names.py`, `SUBCOMMAND_NAMES`).

### A load-bearing reinterpretation of the roadmap text (read before starting)

The roadmap's task-7.3.2 prose and success criterion were written against the
**pre-ADR-007 surface** and are now partly stale. They say the change collapses
"the four real entry points (`novel_state`, `novel_done`, `novel_compile`,
`desloppify`) … one-liners differing only by name and `build_app` source" onto a
table "keyed off `COMMAND_ENTRY_POINTS`" (`docs/roadmap.md` lines 2851–2871).
Two facts make the literal reading impossible and reshape the task:

1. **There are no longer four entry-point functions.** ADR 007 (task 1.2.15)
   retired the five-script surface and `stub.py`; the package now ships a
   **single** `novel` multiplexer with one entry-point function, `novel.main`,
   bound once in `[project.scripts]`
   (`pyproject.toml` line 11: `novel = "novel_ralph_skill.commands.novel:main"`).
   There is exactly one entry-point body to preserve, not four to collapse.

2. **`COMMAND_ENTRY_POINTS` no longer exists.** Task 1.2.15 removed it, and
   `tests/test_legacy_surface_retired.py` line 66 actively asserts
   `not hasattr(names, "COMMAND_ENTRY_POINTS")`. The surviving registry is
   `SUBCOMMAND_NAMES` (`novel_ralph_skill/commands/names.py` lines 40–46), which
   the developers guide names as the single source for the dispatcher's verbs
   (`docs/developers-guide.md` lines 420–430).

The faithful, design-aligned interpretation — and the one this plan
implements — is that the *surviving* repetition the 7.3.2 reroute targets is the
**five hand-copied mount lines in `build_multiplexer()`**, and the
registry it keys off is `SUBCOMMAND_NAMES` (through the existing
`_VERB_FOR_SUBCOMMAND` derivation), not the retired `COMMAND_ENTRY_POINTS`. This
preserves the design's intent (one data-driven home for the dispatcher's verbs;
`docs/developers-guide.md` line 420: "spaced subcommand names live once, as
data, in a single registry") while honouring task 7.3.2's definition of done
(the duplication is removed, one canonical construction survives, it is
documented as the single source, and a test pins it). This reinterpretation is
recorded as Decision D1 below; if a reviewer holds that the task instead requires
re-introducing a `COMMAND_ENTRY_POINTS`-style symbol, that is a tolerance breach
(Ambiguity) — stop and escalate rather than reviving a symbol a green test
forbids.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** This is a pure dispatch-layer refactor. The
  multiplexer's exit codes, envelope shapes, command-name stamping, and
  actionable-message strings must be byte-for-byte identical before and after.
  `tests/test_multiplexer_behaviour.py` pins the legacy-vs-direct envelope parity
  across the corpus and every exit arm; it must pass unchanged (no edits to its
  assertions).

- **The four-flag contract is exact and unchanged.** `build_multiplexer()` must
  continue to build the parent through `make_contract_app(MULTIPLEXER_NAME)` so
  the parent carries `result_action="return_value"`, `exit_on_error=False`,
  `print_error=False`, `help_on_error=False`
  (runner contract; design §3.2; ADR 003). Mounting a child via
  `parent.command(child, name=…)` copies only the child's group and version
  defaults, never its contract flags (verified against the locked Cyclopts
  4.18.0 — see Interfaces and dependencies); each mounted leaf keeps its own
  four-flag contract. The construction table must change *how* the five leaves
  are mounted, never *what* `make_contract_app`/`app.command` do.

- **The five mount names and their order are preserved.** The parent must
  register exactly `state`, `done`, `compile`, `desloppify`, `wordcount` (ADR
  007; design §4 lines 276–279), in `SUBCOMMAND_NAMES` order. Cyclopts mount
  order has no observable effect on dispatch, but the registry order is the
  canonical surface order, so the table iterates the registry in registry order.

- **Per-command deferred-import laziness is preserved.** The five leaf modules
  (`novel_state`, `_novel_done`, `_compile`, `_desloppify`, `_wordcount`) are
  imported **inside** `build_multiplexer()` today (`novel.py` lines 79–85) so the
  dispatcher pulls each leaf's state/predicate machinery in only when the
  multiplexer is actually built, mirroring the retired `stub.py`'s laziness
  (module docstring lines 63–66; design intent recorded in the 1.3.6 ExecPlan).
  The construction table must build its `build_app` references **inside**
  `build_multiplexer()`, after the deferred imports, so the import-laziness
  profile is unchanged: importing `novel_ralph_skill.commands.novel` must **not**
  import the five leaf modules at module load. (Decision D2 records why the table
  is local to the function rather than a module-level constant.)

- **The public entry point and `[project.scripts]` target are stable.** The
  `novel.main` function name, its signature (`() -> None`), and the single
  `[project.scripts]` binding `novel = "novel_ralph_skill.commands.novel:main"`
  (`pyproject.toml` line 11) must not change. `tests/test_pyproject_scripts.py`
  and `tests/test_command_names_registry.py` guard the entry-point table; they
  must pass unchanged.

- **`COMMAND_ENTRY_POINTS` stays retired.** Do not re-introduce a
  `COMMAND_ENTRY_POINTS` symbol; `tests/test_legacy_surface_retired.py` line 66
  asserts its absence and must pass unchanged. The construction table keys off
  `SUBCOMMAND_NAMES`/`_VERB_FOR_SUBCOMMAND`.

- **Module-size and docstring gates.** `novel.py` and every test module stay
  within the 400-line cap (AGENTS.md lines 24–26) and carry 100% `interrogate`
  docstring coverage on every module, function, and fixture
  (AGENTS.md lines 85–87). New test scaffolding obeys the developers-guide
  "Shared test scaffolding" rule (`docs/developers-guide.md` lines 20–95): no new
  copies of existing scaffolding, no cross-module value imports — consume the
  registry by name.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached. These bound autonomous action;
they are not quality criteria.

- Scope: if the implementation touches more than 4 source/test files or more than
  ~140 net lines, stop and escalate — this is a localized refactor of one
  function plus one new test module.
- Interface: if any public signature must change (`novel.main`,
  `build_multiplexer`'s return type, `make_contract_app`, or any leaf
  `build_app`), stop and escalate.
- Dependencies: if a new external dependency is required, stop and escalate (none
  is expected — this is in-process Python over the locked Cyclopts 4.18.0).
- Laziness: if preserving the deferred-import profile proves impossible
  without a module-level leaf import, stop and escalate (Decision D2 must be
  revisited).
- Ambiguity: if a reviewer requires reviving `COMMAND_ENTRY_POINTS` or a separate
  per-verb entry-point function, stop and present the conflict with
  `tests/test_legacy_surface_retired.py` (Decision D1).
- Iterations: if `make all` still fails after 3 fix attempts on the same root
  cause, stop and escalate.

## Risks

- Risk: the construction table is hoisted to a module-level constant, eagerly
  importing the five leaf modules at `novel` import and breaking the
  import-laziness invariant.
  Severity: medium
  Likelihood: medium
  Mitigation: keep the five leaf imports inside the `_build_mount_table` helper
  (Decision D2). Work item 3 adds an in-process textual laziness guard that
  asserts, via `inspect.getsource`, that the leaf imports live inside the helper
  body and not at module scope — a deterministic check that fails if a future
  edit hoists the table (and its leaf imports) to module level. A `sys.modules`
  check is deliberately *not* used: the guard module imports the leaves at module
  scope for the identity tests, so the leaves are already resident before any
  test runs, making an in-process absence check structurally impossible (see
  Work item 3 for the full rationale and the self-proof step).

- Risk: a refactor of the mount loop silently changes the mounted verb set
  (drops a leaf, mis-keys a verb), passing the existing shape test if it happens
  to match by accident.
  Severity: medium
  Likelihood: low
  Mitigation: the new structural test (Work item 1) asserts the table's verb keys
  equal `set(_SUBCOMMAND_FOR_VERB)` (the registry's bare-verb set, equivalently
  `set(_VERB_FOR_SUBCOMMAND.values())`) and that each table value is the leaf
  module's own `build_app` object identity, not just a callable — a dropped or
  swapped leaf fails by identity.

- Risk: iterating a dict over `build_app()` *return values* (eagerly building all
  five apps to fill the table) changes the per-call build cost or import timing.
  Severity: low
  Likelihood: low
  Mitigation: the table maps verb → `build_app` **factory** (the bound function),
  and the loop calls each factory exactly once at mount time, exactly as the
  hand-copied lines do today; no app is built before it is mounted.

- Risk: Cyclopts 4.18.0 mount semantics differ from what the constraint assumes
  (e.g. mounting copies contract flags), so the registry-driven loop changes leaf
  behaviour.
  Severity: low
  Likelihood: low
  Mitigation: the loop calls the identical `app.command(build_app(), name=verb)`
  API the hand-copied lines call; the only change is the source of `name` and the
  iteration. `tests/test_multiplexer_dispatch.py` (four-flag tripwire) and
  `tests/test_multiplexer_behaviour.py` (full envelope parity) pin the
  unchanged-behaviour claim against the locked Cyclopts.

## Progress

- [x] Work item 1: Add the failing structural mount-table test (red).
  Committed `f0d6f36`. `make test` showed exactly the new module's 7 tests
  failing on the undefined `novel._build_mount_table`, the rest green
  (1464 passed). The leaf modules are imported at module scope (needed for the
  identity tests and Work item 3's guard), so the missing symbol surfaces as
  test failures rather than a collection error. Used `ModuleType` for the
  parametrized `module` annotation so the only typecheck error is the intended
  missing-symbol one.
- [x] Work item 2: Collapse `build_multiplexer()` onto the registry-driven table
  (green) and document it. Committed `0e26a80`. Added `_build_mount_table()`
  (deferred leaf imports inside its body) and rewrote `build_multiplexer()` to
  mount by iterating `_SUBCOMMAND_FOR_VERB`. `make all` green (1471 passed);
  the mount-table tests pass, the shape/behaviour/e2e suites unchanged.
  coderabbit run 1 returned two minor markdown findings: the
  `roadmap-7-3-2.md` reflow finding was stale (markdownlint reports zero errors
  there, so skipped with that reason); the fenced-code-language finding pointed
  at the sibling `roadmap-7-3-2.logisphere-review-r2.md`, which had three real
  markdownlint errors (line-length, blanks-around-headings, fenced-language) —
  all fixed so `make markdownlint` and `make nixie` pass.
- [x] Work item 3: Add the in-process textual import-laziness guard test and
  update the developers guide. Added the parametrized `inspect.getsource` guard
  to `tests/test_multiplexer_mount_table.py` (each leaf name must appear in the
  helper source and must be absent from the module source with the helper slice
  removed). Self-proof done: temporarily hoisting `novel_state` to module scope
  turned exactly the `[novel_state]` case red, the other four green; reverted.
  Added the registry-driven construction-table note to `docs/developers-guide.md`
  (quoting the "live once, as data, in a single registry" rule verbatim).
  `make all` (1476 passed), `make markdownlint` (0 errors), and `make nixie` all
  green. coderabbit run 2 returned three findings, all on ExecPlan/review-artefact
  markdown (none on the code):
  - `roadmap-7-3-2.md` 531-533 (minor): claimed the plan alternates between
    registry symbols. Skipped — the round-3 revision deliberately names both
    `_SUBCOMMAND_FOR_VERB` (the symbol the loop and tests use) and
    `_VERB_FOR_SUBCOMMAND` (the trap it warns against) to explain the
    keys-vs-values distinction; the implementation uses one symbol
    (`_SUBCOMMAND_FOR_VERB`) consistently.
  - `roadmap-7-3-2.md` 646-650 (minor): validation checklist omitted the
    formatting step. Actioned — added a `ruff format`/`make fmt` bullet, since
    both Work items 2 and 3 needed a format pass.
  - `roadmap-7-3-2.logisphere-review-r1.md` 100-106 (major): a stale laziness-
    guard rationale. Skipped — this is the round-1 review artefact, a
    historical record; rounds 2-3 superseded it by adopting the
    `inspect.getsource` guard, which the implementation uses. Editing a past
    review to match the current decision would rewrite history; the live plan
    (Decision D2) already records the correct mechanism.

## Surprises & discoveries

```plaintext
- Observation: the roadmap's 7.3.2 success criterion ("keyed off
  COMMAND_ENTRY_POINTS", "four real entry points") is stale relative to
  ADR 007 / task 1.2.15, which retired both the four scripts and the symbol.
  Evidence: tests/test_legacy_surface_retired.py line 66 asserts
  not hasattr(names, "COMMAND_ENTRY_POINTS"); pyproject.toml line 11 binds
  a single `novel` script; novel.py has exactly one entry-point function (main).
  Impact: the task is reinterpreted as collapsing the five mount lines onto a
  SUBCOMMAND_NAMES-keyed table (Decision D1). No revival of the retired symbol.
```

## Decision log

```plaintext
- Decision D1: Interpret task 7.3.2 as collapsing the five hand-copied mount
  lines in build_multiplexer() onto one SUBCOMMAND_NAMES-keyed construction
  table, not as reviving COMMAND_ENTRY_POINTS or four entry-point functions.
  Rationale: ADR 007 / task 1.2.15 retired the four-script surface and the
  COMMAND_ENTRY_POINTS symbol; a green test forbids the symbol's return. The
  surviving repetition the reroute targets is the five mount lines, and the
  surviving registry is SUBCOMMAND_NAMES. This honours the task's definition of
  done (duplication removed, one canonical home, documented, test-pinned) and
  the design's "names live once as data" rule (docs/developers-guide.md line
  420).
  Date/Author: 2026-06-27, planning agent.

- Decision D2: Build the construction table inside the _build_mount_table
  helper (with the five leaf imports inside it), not as a module-level constant.
  Rationale: a module-level table referencing novel_state.build_app etc. would
  force the five leaf imports at `novel` import time, breaking the per-command
  import-laziness invariant the module docstring (lines 63-66) and the 1.3.6
  ExecPlan establish. The table is cheap to build per call and is built once per
  main() invocation, so locality costs nothing observable.
  The laziness invariant is pinned by an in-process *textual* guard
  (inspect.getsource on _build_mount_table and the module), NOT a sys.modules
  fresh-import check. Reason: the guard test module imports the five leaves at
  module scope for the identity tests, so the leaves are already resident in
  sys.modules before any test runs, making an in-process absence assertion
  structurally impossible; and the repo has no reusable clean-interpreter
  import-probe idiom (zero sys.modules matches across tests/; find_spec checks
  importability, not prior import). Authoring a bespoke subprocess probe would
  duplicate scaffolding and add a slow test to re-prove what the textual guard
  pins deterministically. The textual guard is the primary mechanism (round 1
  treated it as a fallback; this revision promotes it). See Work item 3.
  Date/Author: 2026-06-27, planning agent.

- Decision D3: The table maps mount verb -> build_app factory (the bound
  function), and the mount loop calls each factory once at mount time.
  Rationale: preserves the exact "build then mount" sequencing of the
  hand-copied lines; no leaf app is constructed before it is mounted, so build
  cost and timing are unchanged.
  Date/Author: 2026-06-27, planning agent.
```

## Outcomes & retrospective

All three work items landed as planned, no tolerance breached. The five
hand-copied mount lines in `build_multiplexer()` are gone, replaced by one
registry-driven construction table (`_build_mount_table`) and a registry-ordered
mount loop over `_SUBCOMMAND_FOR_VERB`. No inline verb literal survives in the
mount path; the verbs come solely from the registry. The public entry point
(`novel.main`), the `[project.scripts]` target, and the import-laziness profile
are unchanged — the leaf imports live inside the helper, pinned by the
`inspect.getsource` guard (proved load-bearing via the self-proof). The shape,
behavioural-parity, and console-scripts e2e suites all pass unchanged, so the
"no behaviour change" constraint holds. The construction table is documented as
the single source in the developers guide.

What went smoothly: the round-3 plan's keys-vs-values guidance
(`_SUBCOMMAND_FOR_VERB`, not `_VERB_FOR_SUBCOMMAND`) was exact, so the loop and
the verb-set test went green first try once `_build_mount_table` existed. Minor
friction: `ruff format` reflowed the new parametrise/annotation lines (caught by
`check-fmt`, fixed by re-running the formatter) — now noted in the validation
checklist. Pre-existing markdownlint violations in the round-2 review artefact
were fixed in passing to keep `make markdownlint` green.

## Context and orientation

This repository is the `novel-ralph-skill` Python package: a deterministic
command spine driving a long-form-fiction harness. The command surface is a
single `novel` multiplexer (ADR 007), one console-script that mounts five
operations as Cyclopts sub-apps.

The files this plan touches or reads:

- `novel_ralph_skill/commands/novel.py` — the multiplexer dispatcher. The
  function `build_multiplexer()` (lines 56–91) builds the parent contract app and
  mounts the five leaves; `_VERB_FOR_SUBCOMMAND` (lines 46–48) already derives the
  verb-per-spaced-name map from the registry; `main()` (lines 137–end) is the
  console-script entry point. This is the only source file the plan edits.

- `novel_ralph_skill/commands/names.py` — the names registry. `SUBCOMMAND_NAMES`
  (lines 40–46) is the spaced `novel <verb>` names in surface order; the
  multiplexer derives `_VERB_FOR_SUBCOMMAND` from it. The plan consumes this
  registry; it does not edit it.

- `novel_ralph_skill/contract/runner.py` — hosts `make_contract_app(name)`, the
  factory that builds the four-flag contract app. Unchanged by this plan; named
  so the implementer understands the contract the parent carries.

- `tests/test_multiplexer_dispatch.py` — the multiplexer *shape* unit suite:
  asserts the five mount names, the four-flag tripwire, and that
  `_command_name_for` is registry-driven. Must pass unchanged.

- `tests/test_multiplexer_behaviour.py` — the in-process *behavioural* parity
  suite: drives every operation through the multiplexer and directly through its
  own `build_app`, asserting fully-equal envelopes and exit codes over the corpus
  and every exit arm. Must pass unchanged.

- `tests/multiplexer_support.py` — the shared `driver` fixture (a registered
  pytest plugin) the two suites above consume by name.

- `tests/test_console_scripts_e2e.py` — the build-install-run e2e proof,
  parametrized off `SUBCOMMAND_NAMES`. Unchanged and unaffected (it never
  references `build_multiplexer`'s internals).

- `tests/test_legacy_surface_retired.py` — asserts the retired registry symbols
  (including `COMMAND_ENTRY_POINTS`) stay gone. Must pass unchanged.

Terms of art: a *Cyclopts App* is the parser object; `app.command(child,
name=…)` mounts `child` as a named sub-app. The *four-flag contract* is the four
constructor flags every app the shared `run` wrapper drives must carry
(`result_action="return_value"`, `exit_on_error=False`, `print_error=False`,
`help_on_error=False`). The *construction table* this plan introduces is an
ordered mapping of mount verb (`"state"`, …) to the leaf module's `build_app`
factory.

## Plan of work

The work is three ordered, independently committable items, each gate-passable.

### Work item 1 — Add the failing structural mount-table test (red)

Adds the structural test that the refactor must satisfy, before the refactor
exists, so it fails red first. The test lives in a new module
`tests/test_multiplexer_mount_table.py`.

Documentation to read first:

- `docs/developers-guide.md` lines 20–95 (Shared test scaffolding — no new copies
  of scaffolding, consume the registry by name) and lines 415–445 (the names
  registry and the multiplexer description).
- `novel_ralph_skill/commands/novel.py` lines 35–91 (the imports,
  `_VERB_FOR_SUBCOMMAND`, and `build_multiplexer`).
- `tests/test_multiplexer_dispatch.py` (the existing shape suite this complements
  — assert the same five mount names, but now against the registry).

Skills to load: `python-router` → `python-testing` (for the `parametrize`
guidance the identity tests use).

Use bare `assert` — this is the house style of the suite this module sits beside
and explicitly mirrors. `pyproject.toml` line 93 sets the per-file ignore
`"**/test_*.py" = ["S101", "PLR0913", "PLR0917", "PLR2004", "PLR6301"]`, so the
S101 "no bare assert" rule is **ignored** for every `test_*.py` module, including
this new one. The existing `tests/test_multiplexer_dispatch.py` (e.g. lines 47,
58, 69) and `tests/test_legacy_surface_retired.py` (line 66) use bare `assert`
and pass lint. Do **not** write `AssertionError`-raising helpers: they diverge
from the house style and risk tripping the very PLR rules the per-file ignore
already silences for plain assertions.

What to add: a module `tests/test_multiplexer_mount_table.py` with:

1. A test asserting the construction table the refactor introduces exposes its
   verbs as a public, registry-derived view. The refactor (Work item 2) exposes
   the table-building seam as a module-level helper
   `novel._build_mount_table()` returning `dict[str, Callable[[], cyclopts.App]]`
   (named in
   Interfaces and dependencies). This test asserts
   `set(novel._build_mount_table()) == set(novel._SUBCOMMAND_FOR_VERB)` so the
   mounted verb set equals the registry's **bare-verb** set by construction.
   Compare against `set(novel._SUBCOMMAND_FOR_VERB)` (whose keys are the bare
   verbs `{"state", "done", …}`) — **not** `set(novel._VERB_FOR_SUBCOMMAND)`,
   whose keys are the **spaced** names `{"novel state", "novel done", …}`. The
   table is keyed by bare verb, so comparing it against the spaced-name set is
   always `False` (the two sets are disjoint; confirmed in the project venv), an
   assertion that can never go green. `set(novel._VERB_FOR_SUBCOMMAND.values())`
   is the equivalent correct comparand if `_SUBCOMMAND_FOR_VERB` is unavailable.

2. A test asserting each table value **is** the corresponding leaf module's own
   `build_app` (object identity), so a swapped or wrapped builder fails:
   `novel._build_mount_table()["state"] is novel_state.build_app`, and likewise
   for `done`/`_novel_done`, `compile`/`_compile`, `desloppify`/`_desloppify`,
   `wordcount`/`_wordcount`. Parametrize over the five `(verb, module)` pairs.

3. A test asserting `build_multiplexer()` still registers exactly the five mount
   names (mirroring the existing shape test) **and** that the registered names
   equal `set(novel._build_mount_table())`, tying the built app back to the
   table. The registered sub-app names are the bare verbs (`name="state"`, …),
   so the assertion compares the built app's registered names against
   `set(novel._build_mount_table())` (bare-verb keys), which in turn equals
   `set(novel._SUBCOMMAND_FOR_VERB)` by test 1 — never against
   `set(novel._VERB_FOR_SUBCOMMAND)` (spaced names), which would be disjoint and
   always fail.

Because `_build_mount_table` does not yet exist, this module fails to import /
collect — that is the intended red. (Do not stub the helper in this item;
Work item 2 introduces it.)

Tests this item adds: the three unit tests above (`tests/test_multiplexer_mount_table.py`).
No behavioural, property, snapshot, or e2e tests are added here — the
behaviour is already pinned by `tests/test_multiplexer_behaviour.py` (Work item
2 proves it stays green).

Validation: `make test` — confirm `tests/test_multiplexer_mount_table.py` fails
(red) because `novel._build_mount_table` is undefined. Under `pytest -n auto` an
`AttributeError`/`ImportError` in one module surfaces as a collection error for
that module; explicitly confirm the **rest** of the suite still runs green and is
not escalated by the one collection error (a collection error in a single module
does not abort the others under this repo's pytest config). Commit the red test
with a message noting it is the expected-failing structural test for 7.3.2.

### Work item 2 — Collapse `build_multiplexer()` onto the registry-driven table (green)

Replaces the five hand-copied mount lines with the construction table and the
mount loop, turning Work item 1's test green and keeping every existing suite
green.

Documentation to read first:

- `docs/novel-ralph-harness-design.md` lines 274–289 (design §4 — the single
  multiplexer mounting five operations) and ADR 007
  (`docs/adr-007-command-surface-novel-multiplexer.md`).
- `novel_ralph_skill/commands/novel.py` lines 56–91 (the current
  `build_multiplexer` and its deferred imports) and the module docstring lines
  56–66 (the laziness rationale to preserve and re-state).
- The 7.3.1 ExecPlan (`docs/execplans/roadmap-7-3-1.md`) for the house style of
  these single-home refactors and the "no behaviour change" framing.

Skills to load: `python-router` → `python-types-and-apis` (the table type and
the `_build_mount_table` signature) and, if the iteration shape needs care,
`python-iterators-and-generators` (the mount loop).

What to change in `novel_ralph_skill/commands/novel.py`:

1. Add a module-level helper `_build_mount_table() -> dict[str, Callable[[],
   cyclopts.App]]` that performs the five **deferred** leaf imports (moved from
   inside `build_multiplexer`) and returns the ordered mapping
   `{"state": novel_state.build_app, "done": _novel_done.build_app, "compile":
   _compile.build_app, "desloppify": _desloppify.build_app, "wordcount":
   _wordcount.build_app}`. Keeping the leaf imports inside this helper preserves
   the import-laziness invariant (Decision D2): importing `novel` does not import
   the leaves; calling `_build_mount_table()` does. Annotate the return type
   (import `cyclopts` under `TYPE_CHECKING` as today; add `collections.abc` for
   `Callable` under `TYPE_CHECKING`). The table's **keys are the bare verbs**
   (`"state"`, …) — the same values `_VERB_FOR_SUBCOMMAND` maps each spaced name
   to, and the same keys `_SUBCOMMAND_FOR_VERB` carries — in registry/surface
   order; add an assertion-free docstring stating the table keys are the
   registry's bare verbs and the order is surface order.

2. Rewrite `build_multiplexer()` to:
   - build the parent via `make_contract_app(MULTIPLEXER_NAME)` (unchanged),
   - obtain `table = _build_mount_table()`,
   - mount in registry order:
     `for verb in _SUBCOMMAND_FOR_VERB: app.command(table[verb](), name=verb)`,
     which iterates the registry-derived **bare-verb** sequence so a verb the
     registry names but the table omits raises `KeyError` (a loud, test-caught
     failure) rather than silently dropping a mount,
   - return `app`.

   Iterate `_SUBCOMMAND_FOR_VERB`, **not** `_VERB_FOR_SUBCOMMAND`: the table is
   keyed by the bare verb (`"state"`), and `_SUBCOMMAND_FOR_VERB`'s **keys are
   exactly those bare verbs** (`novel.py` lines 51–53), in registry order
   (it is built from `_VERB_FOR_SUBCOMMAND.items()`, itself ordered by
   `SUBCOMMAND_NAMES`). `_VERB_FOR_SUBCOMMAND`'s keys are the **spaced** names
   (`"novel state"`), so `for verb in _VERB_FOR_SUBCOMMAND` would bind
   `verb="novel state"` and `table["novel state"]` would raise
   `KeyError: 'novel state'` (confirmed in the project venv) — and even if it
   resolved, `name="novel state"` would mis-register the mount and break
   `tests/test_multiplexer_dispatch.py`. Iterating `_SUBCOMMAND_FOR_VERB`
   (equivalently `_VERB_FOR_SUBCOMMAND.values()`) keeps `name=verb` equal to the
   bare verb the surface expects while tying the mount sequence to the registry,
   so the registry remains the single source of the verb set and its order
   (Decision D1).

3. Update the `build_multiplexer` docstring to describe the registry-driven
   table: the five mount lines are now one loop over the `SUBCOMMAND_NAMES`-keyed
   table, the verbs come from the registry (no inline verb literals), and the
   deferred imports now live in `_build_mount_table` so the laziness profile is
   unchanged. Re-state that mounting copies only group/version defaults, never the
   contract flags (verified against locked Cyclopts 4.18.0), so each leaf keeps
   its four-flag contract.

Constraint check before committing: confirm no inline verb literal
(`name="state"` etc.) survives in `build_multiplexer`; the only verb source is
`_VERB_FOR_SUBCOMMAND`/the table keys.

Tests this item updates/relies on (no new tests added here; it turns Work item
1's tests green and must keep these unchanged):

- `tests/test_multiplexer_mount_table.py` (Work item 1) — now collects and
  passes.
- `tests/test_multiplexer_dispatch.py` — the five-mount-names shape test and the
  four-flag tripwire pass unchanged.
- `tests/test_multiplexer_behaviour.py` — the full legacy-vs-direct envelope
  parity over the corpus and every exit arm passes unchanged (this is the
  behaviour-preservation proof; do not edit its assertions).
- `tests/test_console_scripts_e2e.py` — the installed-binary e2e (slow, POSIX)
  passes unchanged.

Validation: `make all` (build, check-fmt, lint including the N-family naming
rules and 100% `interrogate` coverage, `ty` typecheck, and the full pytest suite
under `-n auto`). The new mount-table tests pass; every existing suite is green.
Commit with a message describing the registry-driven collapse and citing roadmap
7.3.2, ADR 007, and design §4.

### Work item 3 — Add the import-laziness guard and document the single home

Pins the import-laziness invariant with a test (so a future hoist of the table to
module scope fails) and records the registry-driven construction table as the
documented single source in the developers guide.

Documentation to read first:

- `novel_ralph_skill/commands/novel.py` module docstring (the laziness rationale
  to guard).
- `docs/developers-guide.md` lines 415–460 (the names-registry and `novel`
  multiplexer sections — this is where the documented single-home note lands).
- `docs/execplans/roadmap-7-3-1.md` for the structural-guard test style.

Skills to load: `python-router` → `python-testing` (for the in-process
`inspect.getsource` guard) and the `en-gb-oxendict` skill for the
developers-guide prose (en-GB Oxford spelling). Use bare `assert` here too (S101
is per-file-ignored for `test_*.py`; see Work item 1).

Why no `sys.modules` / fresh-interpreter check (mechanism decision, not a
fallback): a `sys.modules`-absence check is **structurally impossible** in this
module. `tests/test_multiplexer_mount_table.py` imports the five leaf modules at
module scope for the Work-item-1 identity tests
(`novel._build_mount_table()["state"] is novel_state.build_app`), so by the time
any test in the module runs, the five leaves are already in the running
interpreter's `sys.modules`; an in-process absence assertion would be a no-op
(or pass trivially regardless of laziness) — false confidence, the exact trap
the pre-mortem flags. The repository **has no reusable fresh-interpreter
import-probe idiom** to lean on either: `grep -rn "sys.modules" tests/` returns
zero matches across the whole test tree, and
`tests/test_legacy_surface_retired.py` line 72 uses
`importlib.util.find_spec`, which only checks *importability*, not whether a
module was already imported. The subprocess-using suites
(`tests/test_console_scripts_e2e.py` and the other e2e modules) shell out to the
installed `novel` binary; none does a clean-interpreter `sys.modules` probe that
could be reused per the Shared-test-scaffolding rule. Authoring a bespoke
clean-interpreter subprocess probe would (a) duplicate scaffolding the rule
forbids inventing without need, (b) push the slow-test count up under `-n auto`,
and (c) re-prove the very import-time invariant the in-process textual guard
already pins deterministically. The textual guard is therefore the **primary and
sole** mechanism for this item — it is promoted from the round-1 fallback, not
hedged behind an unimplementable preferred path.

What to add:

1. A laziness guard test in `tests/test_multiplexer_mount_table.py` (same
   module) that pins Decision D2 — the leaf imports live *inside*
   `_build_mount_table`, never at module scope — by **static textual
   inspection** of the helper's source, an in-process, deterministic check:
   - `source = inspect.getsource(novel._build_mount_table)`;
   - assert each leaf name (`novel_state`, `_novel_done`, `_compile`,
     `_desloppify`, `_wordcount`) appears in `source` (the deferred import block
     is inside the helper body), and
   - assert the module-level source of `novel` *outside* `build_multiplexer`/
     `_build_mount_table` carries no top-level `from novel_ralph_skill.commands
     import (... leaf ...)` line — i.e. the leaves are not imported at module
     scope. Drive this from `inspect.getsource(novel)` (the whole module) by
     checking the leaf-import statement text occurs only within the helper's
     `getsource` slice, not at column 0. Parametrize over the five leaf names so
     a single leaf hoisted to module scope fails its own case.

   This guard *proves itself*: during authoring, the implementer must confirm it
   **fails** against a deliberately module-hoisted leaf import (temporarily move
   one leaf import to module scope, watch the test go red, then revert), so the
   guard is demonstrably load-bearing and not a tautology. Record that
   self-proof step in the commit message.

   (Rationale: this is the in-process guard the round-1 review identified as the
   correct mechanism given the module-scope leaf imports; Decision D2 is updated
   below to record that the textual guard is primary, with the structural reason
   it cannot be a `sys.modules` check.)

2. A short addition to `docs/developers-guide.md` in the `novel` multiplexer
   section (after line ~445): state that `build_multiplexer` mounts the five
   leaves by iterating a single registry-driven construction table keyed off
   `SUBCOMMAND_NAMES` (via `_VERB_FOR_SUBCOMMAND`), that the verbs live once as
   data in the registry (not inline in the mount lines), and that
   `tests/test_multiplexer_mount_table.py` pins the table against the registry so
   a dropped or drifted mount fails a test. Wrap prose at 80 columns; use en-GB
   Oxford spelling. When echoing the registry rule, quote the guide verbatim —
   the source reads "The spaced subcommand names live once, as data, in a single
   registry" (`docs/developers-guide.md` line 420); do not paraphrase it into a
   near-quote.

Tests this item adds: the in-process textual laziness guard (parametrized over
the five leaf names, in the existing new module). No property, snapshot, or e2e
additions — the behaviour surface is unchanged and already covered, and a
clean-interpreter subprocess probe is deliberately avoided (see the rationale
above).

Validation:

- `ruff format` the new test additions before gating — `make all`'s `check-fmt`
  arm rejects an unformatted file, so run the formatter (or `make fmt`) on any
  edited Python so the long parametrise/annotation lines wrap to house style.
- `make all` — full build/lint/typecheck/test green, including the new laziness
  guard.
- `make markdownlint` and `make nixie` — required because this item edits
  Markdown (`docs/developers-guide.md` and this ExecPlan). `make nixie` validates
  any Mermaid diagrams (none added; the run must still pass).

Commit with a message citing roadmap 7.3.2 and the developers-guide single-home
note.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-2`.

1. Work item 1 — author `tests/test_multiplexer_mount_table.py`; then run
   `make test`. Expect collection failure on the new module
   (`AttributeError`/`ImportError` for `novel._build_mount_table`), the rest
   green. Commit the red test.

2. Work item 2 — edit `novel_ralph_skill/commands/novel.py`
   (`_build_mount_table` + rewritten `build_multiplexer`); then run `make all`.
   Expect: build ok; `ruff`/naming/`interrogate` clean; `ty` clean; pytest green
   including `tests/test_multiplexer_mount_table.py`,
   `tests/test_multiplexer_dispatch.py`, `tests/test_multiplexer_behaviour.py`,
   and `tests/test_console_scripts_e2e.py`. Commit.

3. Work item 3 — add the laziness guard test and the developers-guide note; then
   run `make all`, `make markdownlint`, and `make nixie`. Expect all three
   green. Commit.

## Validation and acceptance

Acceptance is behavioural and structural:

- Quality method: `make all` passes (build, `check-fmt`, `lint`, `typecheck`,
  `test` under `-n auto`); for the Markdown-touching item, `make markdownlint`
  and `make nixie` also pass.
- Tests:
  - `tests/test_multiplexer_mount_table.py::*` fail before Work item 2 and pass
    after (red→green), proving the registry-driven table exists and matches the
    registry.
  - `tests/test_multiplexer_dispatch.py` and `tests/test_multiplexer_behaviour.py`
    pass unchanged before and after, proving no behaviour change.
  - `tests/test_console_scripts_e2e.py` passes, proving the installed `novel`
    binary still runs every subcommand to its real path.
  - `tests/test_legacy_surface_retired.py` passes, proving `COMMAND_ENTRY_POINTS`
    stays retired.
- Structural acceptance: `build_multiplexer` contains no inline mount-verb literal
  (`name="state"`, etc.); the verbs come solely from `_VERB_FOR_SUBCOMMAND`/the
  table keys. The leaf imports live inside `_build_mount_table`, pinned by the
  in-process textual laziness guard (`inspect.getsource`), which the implementer
  proves load-bearing by watching it fail against a temporarily module-hoisted
  leaf import before reverting.

Done means: the five hand-copied mount lines are gone, replaced by one
registry-driven table and a registry-ordered mount loop; the public entry point,
`[project.scripts]` target, and import-laziness profile are unchanged; the
construction table is documented as the single source in the developers guide;
and a test pins it so it cannot silently re-fork (roadmap task 7.3.2 definition
of done).

## Idempotence and recovery

Every step is a pure source edit under version control; re-running `make all`,
`make markdownlint`, and `make nixie` is safe and side-effect-free. If Work
item 2
breaks behaviour parity, revert `novel.py` to the hand-copied lines (the red test
from Work item 1 stays committed as the target) and retry the refactor. No
destructive or stateful operations are involved.

## Interfaces and dependencies

Prescriptive end-state in `novel_ralph_skill/commands/novel.py`:

```python
# Built inside the function-scoped helper so importing `novel` imports no leaf
# module (Decision D2). The keys are the registry verbs; the order is surface
# order.
def _build_mount_table() -> dict[str, cabc.Callable[[], cyclopts.App]]:
    from novel_ralph_skill.commands import (
        _compile,
        _desloppify,
        _novel_done,
        _wordcount,
        novel_state,
    )

    return {
        "state": novel_state.build_app,
        "done": _novel_done.build_app,
        "compile": _compile.build_app,
        "desloppify": _desloppify.build_app,
        "wordcount": _wordcount.build_app,
    }


def build_multiplexer() -> cyclopts.App:
    app = make_contract_app(MULTIPLEXER_NAME)
    table = _build_mount_table()
    for verb in _SUBCOMMAND_FOR_VERB:
        app.command(table[verb](), name=verb)
    return app
```

The mount loop iterates `_SUBCOMMAND_FOR_VERB`, whose **keys are the bare
mount verbs** (`"state"`, `"done"`, …) in registry order, because the table is
keyed by bare verb. It must **not** iterate `_VERB_FOR_SUBCOMMAND` directly:
that dict is keyed by the **spaced** registry name (`"novel state"` → `"state"`),
so `for verb in _VERB_FOR_SUBCOMMAND` binds `verb="novel state"` and
`table["novel state"]` raises `KeyError` (the construction table holds no spaced
key). Verified in the project venv: iterating `_VERB_FOR_SUBCOMMAND`'s keys
raises `KeyError: 'novel state'` on the first lookup; iterating
`_SUBCOMMAND_FOR_VERB` (or, equivalently, `_VERB_FOR_SUBCOMMAND.values()`)
yields the bare verbs and every lookup succeeds. `_SUBCOMMAND_FOR_VERB`
(`novel.py` lines 51–53) is derived from `_VERB_FOR_SUBCOMMAND.items()`, so its
key order is the registry/surface order; iterating it preserves the canonical
mount order while keeping `name=verb` equal to the bare verb the surface
expects.

`cabc` is `collections.abc`, imported under `TYPE_CHECKING`. `cyclopts` is
already imported under `TYPE_CHECKING` (novel.py line 41). No runtime imports are
added at module scope.

External library facts this plan relies on, pinned to the locked versions:

- **Cyclopts 4.18.0** (`uv.lock` lines 137–148). `cyclopts.App.command(child, *,
  name=…)` mounts `child` as a named sub-app; mounting copies only the child's
  group and version defaults, never its contract flags, so each mounted leaf keeps
  its own `result_action`/`exit_on_error`/`print_error`/`help_on_error`. This is
  the same `app.command(build_app(), name=…)` call the five hand-copied lines use
  today; the plan changes only the *source* of `name` and the iteration, not the
  Cyclopts API or its semantics. The unchanged-behaviour claim is pinned by
  `tests/test_multiplexer_dispatch.py` (four-flag tripwire) and
  `tests/test_multiplexer_behaviour.py` (full envelope parity), not asserted from
  memory.
- **cuprum 0.1.0** (`uv.lock` lines 113–118) is **not** load-bearing for this
  change: it appears only in `tests/test_console_scripts_e2e.py` and
  `tests/installed_binary_fixtures.py`, which build/install the wheel and run the
  installed `novel` script by absolute path through a `ProgramCatalogue`
  allowlist (verified against the locked cuprum's
  `cuprum/catalogue.py::ProgramCatalogue` — `projects=`-constructed,
  `is_allowed`/`allowlist` of `Program` strings including absolute paths). Those
  fixtures are parametrized off `SUBCOMMAND_NAMES` and never reference
  `build_multiplexer`'s internals, so the construction-table refactor leaves them
  untouched; they serve only as the green-throughout installed-binary proof.
- **pytest-timeout / pytest-xdist** (`pyproject.toml` lines 21–22, 322–324):
  the suite runs under `-n auto` with a 30s default per-test timeout; the slow
  e2e carries its own explicit override. This plan adds only fast in-process unit
  tests (no new slow/e2e), so no timeout override is needed.

## Revision note

Initial draft (2026-06-27). Establishes the three-item plan to collapse the five
multiplexer mount lines onto a `SUBCOMMAND_NAMES`-keyed construction table,
records the load-bearing reinterpretation of the stale roadmap text
(`COMMAND_ENTRY_POINTS` retired; single entry point; Decision D1), and pins the
import-laziness invariant (Decision D2) with a guard test. No implementation has
begun.

Round 2 revision (2026-06-27), resolving the round-1 Logisphere review
(`docs/execplans/roadmap-7-3-2.logisphere-review-r1.md`):

- B1 — corrected the false Work-item-1 premise that test modules "may not use
  bare `assert`". `pyproject.toml` line 93 per-file-ignores S101 (and the PLR
  rules) for `**/test_*.py`, so the new module uses bare `assert`, mirroring
  `tests/test_multiplexer_dispatch.py`. Removed the `AssertionError`-helper
  instruction.
- B2 — replaced the unimplementable "reuse the sanctioned fresh-import idiom"
  laziness-guard path with an in-process `inspect.getsource` textual guard as the
  **primary** mechanism. Spelled out why a `sys.modules` check is structurally
  impossible in this module (the leaves are imported at module scope for the
  identity tests) and why no reusable clean-interpreter idiom exists (zero
  `sys.modules` matches in `tests/`; `find_spec` only checks importability).
  Added a self-proof step (the guard must fail against a temporarily
  module-hoisted leaf import). Updated the Risk entry, Decision D2, and the
  acceptance criteria to match.
- Advisories A2 (collection-error check) and A3 (verbatim developers-guide quote)
  folded into Work items 1 and 3.

No design constraint was relaxed; both fixes correct the plan's description of
the test harness, not the design. No implementation has begun.

Round 3 revision (2026-06-27), resolving the round-2 Logisphere review
(`docs/execplans/roadmap-7-3-2.logisphere-review-r2.md`). Both blocking points
share one root cause: the plan confused the registry dict's **keys** with its
**values**. `_VERB_FOR_SUBCOMMAND` is `{spaced_name: bare_verb}` — its keys are
the spaced names (`"novel state"`), its values the bare verbs (`"state"`) — and
the construction table is keyed by **bare verb**. The sibling map
`_SUBCOMMAND_FOR_VERB` (`novel.py` lines 51–53), whose **keys are the bare
verbs** in registry order, is the correct symbol; `_VERB_FOR_SUBCOMMAND.values()`
is the equivalent fallback. Verified in the project venv: iterating
`_VERB_FOR_SUBCOMMAND`'s keys to index the table raises `KeyError: 'novel state'`
on the first lookup, and `set(table) == set(_VERB_FOR_SUBCOMMAND)` is always
`False` (disjoint sets).

- B3 (mount loop) — changed the prescriptive mount loop in both sites
  (Interfaces and dependencies; Work item 2 step 2) from
  `for verb in _VERB_FOR_SUBCOMMAND` to `for verb in _SUBCOMMAND_FOR_VERB`, so
  `verb` binds the bare verb (`"state"`), `table[verb]` resolves, and
  `name=verb` registers the bare mount name `tests/test_multiplexer_dispatch.py`
  expects. Spelled out the KeyError and the command-surface drift the old loop
  would have caused, with the venv evidence.
- B3 (acceptance tests) — changed the Work item 1 verb-set test (step 1) and the
  registered-names test (step 3) to compare against
  `set(novel._SUBCOMMAND_FOR_VERB)` (bare verbs), not
  `set(novel._VERB_FOR_SUBCOMMAND)` (spaced names), so the red→green transition
  is reachable. Propagated the same correction to the Purpose section's
  "observable four ways" summary and the Risks mitigation (both previously cited
  `_VERB_FOR_SUBCOMMAND` keys as the comparand), and tightened the
  `_build_mount_table` docstring instruction to name the table keys as the bare
  verbs.

No design constraint was relaxed; the fixes correct which registry symbol the
loop and tests consume, not the design. The cuprum non-load-bearing claim was
re-verified against `/data/leynos/Projects/cuprum/cuprum/catalogue.py`
(`ProgramCatalogue`, `projects=`-constructed, `is_allowed`/`allowlist`,
lines 59–77) and the locked versions re-confirmed (cuprum 0.1.0 `uv.lock`
line 114; Cyclopts 4.18.0 `uv.lock` line 138). No implementation has begun.

## Addenda

Post-merge corrections folded back onto this completed task. Each is a
lightweight, no-plan addendum pass; they do not reopen the design.

- [x] **Addendum 7.3.2.1 — `ast` import-laziness guard** (from audit:7.3.2
  Finding 4 / review:7.3.2; low). The laziness guard
  `test_leaf_import_lives_inside_the_mount_table_helper`
  (`tests/test_multiplexer_mount_table.py`) asserts each leaf name is absent from
  the module source outside `_build_mount_table` by a raw substring scan over
  `inspect.getsource(...).replace(...)`. That property is wider than the real
  invariant (no module-scope leaf *import*): it false-fails the day a docstring
  or comment legitimately mentions a leaf module by name, and cannot distinguish
  an
  import from a comment. Re-pin the invariant with an `ast` walk over module-scope
  (`col_offset == 0`) `Import`/`ImportFrom` nodes — asserting no leaf is imported
  at module scope and each leaf *is* imported inside the `_build_mount_table`
  `FunctionDef` body — following the in-repo `ast` scanner pattern in
  `tests/_state_layout_scanner.py`. The guard must still prove itself load-bearing
  (fail against a temporarily module-hoisted leaf import, then revert). This
  honours Decision D2 (the leaf imports stay inside the helper) while pinning
  import location rather than string presence, so the guard survives reformatting
  and prose mentions.

- [x] **Addendum 7.3.2.2 — registry-tied test verb-sets** (from audit:7.3.2
  Findings 2 and 3; medium). The bare-verb set is hand-spelled as an inline
  literal in `tests/test_multiplexer_dispatch.py:47` — a fourth copy untied to the
  registry — and `test_build_multiplexer_registers_the_five_subcommands` there
  duplicates the stronger, registry-tied
  `test_build_multiplexer_registers_exactly_the_table_verbs` in
  `tests/test_multiplexer_mount_table.py`. Drive the dispatch test's expected set
  from `set(novel._SUBCOMMAND_FOR_VERB)` (or repoint it at
  `set(novel._build_mount_table())`), retire or repoint the redundant
  registered-mounts test (updating the dispatch module docstring if its assertion
  moves), and add a single guard that the `_VERB_MODULE_PAIRS`/`_OPERATIONS`
  fixture verb keys equal the registry's bare-verb set so no test surface silently
  drifts from the single registry. This completes the refactor's "no inline verb
  literals drift" framing on the test side without over-de-duplicating the
  verb→module/argv fixtures.

- [x] **Addendum 7.3.2.3 — mount-map prose and observable order** (from audit:7.3.2
  Findings 1 and 5; low). The developers' guide
  (`docs/developers-guide.md:451-453`) names `_VERB_FOR_SUBCOMMAND` as the mount
  driver, but `build_multiplexer` iterates `_SUBCOMMAND_FOR_VERB`; iterating
  `_VERB_FOR_SUBCOMMAND` would yield the spaced names and `KeyError` against the
  bare-verb-keyed table, so the named map is doubly misleading. Separately, the
  "ordered mapping in surface order" claim across the `_build_mount_table`
  docstring, the guide, and the tests is asserted only by set-equality, leaving
  the one behaviourally observable order (the `--help` listing order) untested.
  Correct
  the guide to name the map the loop actually reads (or describe the order as
  `SUBCOMMAND_NAMES`/ADR 007 surface order without over-committing to an
  intermediate map), add one ordered assertion that the registered mount order
  equals `list(novel._SUBCOMMAND_FOR_VERB)`, and soften the `_build_mount_table`
  docstring so it does not imply the table's own iteration order is load-bearing
  (the mount loop, not the table, fixes the surface order).
