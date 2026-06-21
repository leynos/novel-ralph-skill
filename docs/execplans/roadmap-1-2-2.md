# Add `tomlkit` to the package dependencies and confirm the build

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

This is roadmap task 1.2.2 (`docs/roadmap.md`, step 1.2). It closes the
packaging boundary that step 1.2 stands up by confirming that `tomlkit` — the
TOML round-trip mechanism fixed in ADR 002
(`docs/adr-002-toml-round-trip-tomlkit.md`) and design §5.3 — is a declared,
resolved, installed, and importable dependency of `novel_ralph_skill`, and that
the full quality-gate set still passes against it. It depends on roadmap tasks
1.1.2 (the TOML round-trip ADR, accepted) and 1.2.1 (the wired console-scripts,
already merged).

The task name reads "Add `tomlkit` to the package dependencies and confirm the
build", but the empirical starting state is that **`tomlkit` is already
declared and already locked**. `pyproject.toml` `[project.dependencies]` reads
`["cyclopts", "tomlkit"]`; `uv.lock` pins `tomlkit` to **0.15.0** (verified, see
the Decision Log entry "tomlkit is already declared and locked at 0.15.0"). The
declaration landed in commit `916313c` ("Establish novel-ralph design suite"),
before task 1.2.1 ran, so the literal "add the dependency" half of the task is
satisfied at the declaration level. The substantive, load-bearing half is
therefore "**confirm the build**": prove the declared dependency actually
resolves, installs, imports, and round-trips, against the locked version, and
prove the AGENTS.md quality gates stay green.

That confirmation is not hollow ceremony. The repository has **no
unused-dependency gate** — there is no `deptry` and `pip-audit` checks only for
vulnerabilities, not for usage (verified: `make audit` is `uv run pip-audit`,
Makefile line 104–105; no `deptry` anywhere). A dependency that is declared but
never imported would pass `make all` silently and could be dropped by a future
contributor with no test going red. This task adds the one thing that makes the
"confirm the build" criterion meaningful and durable: a small confirmation test
that imports `tomlkit` and pins the **locked** round-trip capability ADR 002
relies on, so the dependency is provably load-bearing from this commit forward.

A hard scope boundary governs this task. Design §9 and roadmap task **2.2.1**
own the real `tomlkit` round-trip-and-atomic-write *helper*
(`tomllib`-then-`Path.replace`, the `[pending_turn]` intent record) and the
*property-based* round-trip test over generated states. This task must **not**
implement that helper, must **not** touch `state.toml` mutation, and must
**not** add a Hypothesis property suite — doing so would poach 2.2.1's scope and
build on commands that do not yet exist. The confirmation test here is a thin,
example-based capability check (parse → mutate → dump round-trips and preserves
a comment, on a tiny in-test TOML string), not the state round-trip. The full
property guard against a `tomlkit` major-version regression is task 2.2.1's job,
as ADR 002 "Known risks" and design §9 both state.

The research surfaced a related documentation defect that this task does **not**
fix and must **not** pretend to own. ADR 002 ("Decision outcome", line 77) and
design §5.3 (line 465) both assert, in the past tense, that "the failed
`tomli_w` snippet … **is removed**". That is **not true at HEAD**: the snippet
is still present in `skill/novel-ralph/references/state-layout.md` lines 226–238
(verified). It would be tempting to "correct" those two sentences here, but the
removal of that snippet is **not assigned to any roadmap task**. Design §8
(lines 644–664) enumerates exactly three reference-file defects owned by roadmap
task 6.2.3 — the `SKILL.md:107` phase mislabel, the two-source done predicate,
and the dead `state-layout.md:38` `plan.md` spec — and the `tomli_w` snippet
removal is **not** among them (`grep -rn tomli_w docs/` confirms: every hit
outside this execplan is the defect itself, never an ownership assignment). Its
ownership is therefore currently a gap in the roadmap. Editing design §5.3 or
ADR 002 to forward-reference 6.2.3 would inject a **false** cross-reference into
the very documents this task is meant to keep truthful, so this plan
deliberately leaves those sentences untouched and instead **escalates the
unassigned-ownership gap to the roadmap owner** (see Decision Log and
Surprises). This keeps the task
inside roadmap 1.2.2's narrow success criterion (line 102: "`make test` and the
quality gates in AGENTS.md pass against the extended dependency set") and keeps
docs/ free of manufactured references.

To verify the implementation: `tomlkit` imports in the synced environment and
reports version `0.15.0`; a no-op `tomlkit.parse` → `tomlkit.dumps` round-trips
a comment-bearing TOML string byte-for-byte; a targeted value edit re-serialises
with the comment intact and the value changed; and `make all` is green.

Success is observable as: a `pytest` test that imports `tomlkit`, asserts its
version is the locked `0.15.0`, and asserts the parse/dump round-trip preserves
comments and applies a value edit; `make build` resolving the dependency set
cleanly with `tomlkit` present in `uv.lock`; `make audit` clearing `tomlkit`;
and `make all` green.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-2`. Never edit
  files in the root/control worktree.
- `tomlkit` is the only TOML write mechanism (ADR 002, design §5.3). Do not add
  `tomli_w`, `tomli`, `toml`, or any other TOML library; do not build an owned
  serialiser. Reading may use the standard-library `tomllib` (the confirmation
  test does not need it).
- This task does **not** implement the state round-trip helper, the
  `[pending_turn]` intent record, the atomic temp-file-and-`Path.replace` write,
  or any `state.toml` mutation — those are roadmap task 2.2.1 (design §3.4, §9).
  The confirmation test operates on an in-test TOML string only and writes
  nothing to `working/`.
- This task does **not** add a Hypothesis/CrossHair property suite. The
  round-trip *property* test over generated states is task 2.2.1 (design §9).
  The confirmation here is example-based.
- This task does **not** delete the `tomli_w` snippet from
  `skill/novel-ralph/references/state-layout.md`, and does **not** edit design
  §5.3 or ADR 002 to "fix" their premature "is removed" claim. The snippet's
  removal is currently unassigned in the roadmap (design §8 owns only the three
  defects listed in roadmap task 6.2.3, none of which is this snippet).
  Asserting a 6.2.3 owner here would inject a false cross-reference; the gap is
  escalated to the roadmap owner instead (Decision Log).
- No command implements any narrative judgement or any real deterministic
  behaviour in this task (ADR 001, design §1, §2.2). No new console-script, no
  command body change.
- Prose, comments, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` convention.
- Every public module, class, and function carries a docstring; `interrogate`
  enforces 100% coverage (AGENTS.md, Makefile `lint-python`). No file exceeds
  400 lines (AGENTS.md).
- Tests live in the top-level `tests/` tree, never inside the package
  (AGENTS.md, "Python verification and testing").
- Markdown prose wraps at 80 columns; code blocks at 120; tables and headings
  are not wrapped; list bullets use `-` (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 2 files or more than
  80 net lines, stop and escalate. Expected files:
  `tests/test_tomlkit_dependency.py` (new) and this plan — two at most. No
  `docs/`, `skill/`, or `pyproject.toml`
  edits are in scope (the documentation reconciliation was dropped in round 2;
  see Decision Log). If editing any design doc, ADR, or reference file feels
  necessary, stop and escalate — that work is not owned here.
- Dependencies: this task adds **no** new runtime or dev dependency. `tomlkit`
  is already declared and locked. If resolution reveals `tomlkit` is somehow
  absent or must be re-pinned, stop and escalate rather than silently changing
  the lock floor.
- Lock churn: `make build` must not change the resolved `tomlkit` version away
  from `0.15.0` without cause. If `uv.lock` re-resolves `tomlkit` to a different
  version, stop and reconcile the confirmation test's pinned version (and ADR
  002's "Known risks") rather than asserting a stale version.
- Scope creep into 2.2.1: if the confirmation test starts needing `state.toml`,
  `Path.replace`, a `[pending_turn]` record, or generated-state strategies, stop
  — that is 2.2.1, not this task.
- Iterations: if `make all` still fails after 3 focused fix attempts on the same
  gate, stop and escalate.

## Risks

- Risk: the confirmation test pins `tomlkit.__version__ == "0.15.0"`, and a
  later `uv lock` re-resolution bumps the version, turning the pin into a
  spurious failure.
  - Severity: low. Likelihood: low (the lock pins it; bumps are deliberate).
  - Mitigation: assert the version that `uv.lock` actually records, and add a
    `# why:` comment stating the pin tracks the lock and must be updated in
    lockstep with a deliberate bump. The pin is a *tripwire* for an
    unannounced `tomlkit` change (the regression ADR 002 "Known risks" names),
    not an arbitrary constraint. If a maintainer bumps `tomlkit` on purpose,
    updating this one assertion is the intended, visible cost. (Alternative
    considered and rejected: asserting only `>= 0.13`. That would not trip on a
    silent major-version round-trip regression, defeating the test's purpose.)
- Risk: the confirmation test is mistaken by a reviewer for the 2.2.1 state
  round-trip, inviting scope creep or a duplicate property suite.
  - Severity: low. Likelihood: medium.
  - Mitigation: the test module docstring and a `# why:` comment state
    explicitly that this is the dependency-confirmation capability check for
    task 1.2.2, that it operates on an in-test string (not `state.toml`), and
    that the full property round-trip over generated states is task 2.2.1
    (design §9). Cross-reference 2.2.1 by number.
- Risk: the implementer is tempted to "fix" the premature "is removed" claim in
  design §5.3 / ADR 002 as a tidy-up, injecting a false 6.2.3 cross-reference
  (or any owner) for a removal the roadmap has not assigned.
  - Severity: medium. Likelihood: medium (the overstatement is conspicuous and
    looks like low-hanging fruit).
  - Mitigation: this plan deliberately drops all design/ADR edits and escalates
    the unassigned-ownership gap to the roadmap owner (Decision Log, Surprises).
    Constraints forbid touching design §5.3, ADR 002, and `state-layout.md`. The
    correct sentence cannot be written until a roadmap task owns the removal, so
    no such edit is attempted here.
- Risk: dropping the documentation work item leaves the design/ADR
  overstatement unaddressed indefinitely if the escalation is lost.
  - Severity: low. Likelihood: low.
  - Mitigation: the gap is recorded as a first-class Surprise with the precise
    locations (design §5.3 line 465; ADR 002 lines 22 and 77) and the verified
    finding that 6.2.3 does not own it, so the roadmap owner has everything
    needed to schedule it. This task's return value surfaces the escalation.

## Progress

- [x] (2026-06-21) Work item 1: Add the `tomlkit` dependency-confirmation test
  (import, version pin, parse/dump round-trip with comment preservation and a
  value edit). Confirmed `make build` (no lock churn; `tomlkit` stays at
  `0.15.0`), `make audit` (no known vulnerability), and `make all` (36 tests
  pass, including the three new ones) against the locked dependency set. Added
  `tests/test_tomlkit_dependency.py`. No `pyproject.toml`, `docs/`, or `skill/`
  source edited.
- [x] (2026-06-21) Escalation (no code change): the premature "is removed"
  claim in design §5.3 / ADR 002 cannot be corrected here because the `tomli_w`
  snippet removal is unassigned in the roadmap (design §8 / task 6.2.3 own only
  three other defects). Recorded in Surprises and Decision Log and surfaced in
  this task's return value to the roadmap owner. No documentation edited.

## Surprises & discoveries

- Observation: `tomlkit` is already declared in `[project.dependencies]` and
  already in `uv.lock` at version `0.15.0`. The literal "add the dependency"
  half of task 1.2.2 is pre-satisfied; the work is the "confirm the build" half.
  - Evidence: `pyproject.toml` `dependencies = ["cyclopts", "tomlkit"]`;
    `uv.lock` `name = "tomlkit" / version = "0.15.0"`; `git log -S tomlkit`
    shows the declaration entering in commit `916313c`.
- Observation: the design (§5.3, line 465) and ADR 002 ("Decision outcome",
  line 77) both assert the failed `tomli_w` snippet "is removed", but it is
  still present in `skill/novel-ralph/references/state-layout.md` lines 226–238.
  The removal is **unassigned** in the roadmap. Design §8 (lines 644–664) and
  roadmap task 6.2.3 (lines 424–432) own only three other reference-file defects
  (the `SKILL.md:107` phase mislabel, the two-source done predicate, and the
  dead `state-layout.md:38` `plan.md` spec), and the `tomli_w` snippet is none
  of them.
  - Evidence: `grep -rn tomli_w skill/` finds the snippet at
    `state-layout.md:229` and `:235`; `grep -rn tomli_w docs/` shows every hit
    outside this execplan is the defect text itself (design §5.3 line 464, ADR
    002 lines 22 and 77, terms of reference line 39), never an ownership
    assignment; design §8 lists three defects, none of which is this snippet.
  - Impact: this task does **not** correct the overstated design/ADR claim,
    because writing a correct sentence requires a roadmap owner for the removal,
    which does not yet exist. Inventing a 6.2.3 reference would inject a false
    cross-reference. The gap is **escalated to the roadmap owner** (Decision
    Log) and surfaced in this task's return value; it is out of scope for 1.2.2.
- Observation: ADR 002 is internally inconsistent independent of the roadmap
  gap: line 22 (Context) says the reference "even carries" the snippet (present
  tense), while line 77 (Decision outcome) says it "is removed" (past tense).
  - Evidence: `docs/adr-002-toml-round-trip-tomlkit.md:22` and `:77`.
  - Impact: noted for the roadmap owner so that whichever task is assigned the
    removal reconciles both sentences, not just line 77. Not edited here.
- Observation: there is no unused-dependency gate (`deptry` absent; `pip-audit`
  checks vulnerabilities only). A declared-but-unimported `tomlkit` would pass
  `make all` silently.
  - Evidence: no `deptry` in `Makefile`/`pyproject.toml`; `make audit` is
    `uv run pip-audit`.
  - Impact: the confirmation test is what makes the dependency provably load-
    bearing; without it "confirm the build" is hollow.

## Decision log

- Decision: tomlkit is already declared and locked at 0.15.0; this task is a
  confirmation task, not a declaration task.
  - Rationale: `pyproject.toml` already lists `tomlkit`; `uv.lock` already pins
    `0.15.0`. Re-adding it is a no-op. The roadmap's "and confirm the build"
    clause is the real deliverable, made meaningful by a confirmation test
    (there is no unused-dependency gate to otherwise catch a dangling
    dependency).
  - Date/Author: 2026-06-21, planning agent.
- Decision: the confirmation test pins the locked round-trip *capability*
  example-based; the round-trip *property* over generated states is deferred to
  task 2.2.1.
  - Rationale: design §9 assigns the property-based round-trip ("a no-op
    `recount` preserves formatting and comments") to the state validator work,
    and roadmap 2.2.1 owns the `tomlkit` helper. Building it here would poach
    2.2.1 and depend on commands that do not exist. ADR 002 "Migration plan"
    says `tomlkit` "is added in roadmap task 1.2.2 and exercised by the
    round-trip helper in task 2.2.1" — exactly this split. The 1.2.2 test pins
    the locked behaviour (parse/dump round-trips and preserves a comment) so the
    dependency is load-bearing now; 2.2.1 adds the generated-state guard.
  - Date/Author: 2026-06-21, planning agent.
- Decision: the confirmation test asserts the exact locked version `0.15.0`.
  - Rationale: ADR 002 "Known risks" names a `tomlkit` major-version change as
    the regression to guard against. An exact pin against `uv.lock` is a
    tripwire: a silent re-resolution trips it, a deliberate bump updates it
    visibly. A floor (`>= 0.13`) would not trip on a major-version round-trip
    change and so would not serve the ADR's stated risk. Verified locally:
    `tomlkit.__version__ == "0.15.0"` in the synced env.
  - Date/Author: 2026-06-21, planning agent.
- Decision: drop the planned documentation work item entirely; do not edit
  design §5.3 or ADR 002, do not delete the `tomli_w` snippet, and escalate the
  unassigned-ownership gap to the roadmap owner.
  - Rationale: round-1 design review (B1) and direct verification establish that
    the `tomli_w` snippet removal is **not** owned by roadmap task 6.2.3 or any
    other task. Design §8 (lines 644–664) and roadmap 6.2.3 (lines 424–432)
    enumerate exactly three reference-file defects — the `SKILL.md:107` phase
    mislabel, the two-source done predicate, and the dead `state-layout.md:38`
    `plan.md` spec — and the snippet is none of them; `grep -rn tomli_w docs/`
    finds no ownership assignment anywhere. The round-1 plan's edit would have
    rewritten design §5.3 and ADR 002 to forward-reference 6.2.3 as the owner
    of work 6.2.3 does not own, injecting a false cross-reference into the
    documents the task is meant to keep truthful — the inverse of intent.
    Path (a) of
    the review (drop the item, escalate the gap) is chosen over path (b)
    (assign-then-correct) because assigning roadmap ownership is the roadmap
    owner's prerogative, not a side effect of a dependency-confirm task, and
    folding it in would also breach roadmap 1.2.2's narrow success criterion
    (line 102). The gap is recorded in Surprises with exact locations and
    surfaced in this task's return value so the roadmap owner can schedule it
    (and, when they do, reconcile ADR 002 lines 22 and 77 together — advisory
    A2).
  - Date/Author: 2026-06-21, planning agent (revised round 2 after review).
- Decision: prefer a direct semantic assertion over a `syrupy` snapshot for the
  round-trip confirmation.
  - Rationale: AGENTS.md requires snapshots to capture a meaningful, reviewer-
    useful boundary and to avoid brittle dumps. The round-trip capability is a
    one-line equality (`dumps(parse(src)) == src`) plus two membership checks;
    a snapshot would add churn without a clearer contract. The machine-mode JSON
    envelope snapshots belong to the command tasks (design §9), not here.
  - Date/Author: 2026-06-21, planning agent.

## Outcomes & retrospective

- Outcome: `tests/test_tomlkit_dependency.py` added, making the declared
  `tomlkit` dependency provably load-bearing. Three example-based tests pass:
  the version pin (`tomlkit.__version__ == "0.15.0"`), the lossless no-op
  round-trip (`dumps(parse(SRC)) == SRC`), and the comment-preserving value
  edit. `make all` is green (36 tests). No production code, `pyproject.toml`,
  `docs/`, or `skill/` source was changed, as planned.
- Deviation (minor, non-code): the worktree carried two untracked planning
  artefacts — `docs/execplans/roadmap-1-2-2.md` (this plan) and
  `docs/execplans/roadmap-1-2-2.review-r1.md` (the round-1 review). The
  repo-wide `make markdownlint` lints all tracked and untracked Markdown, and
  `review-r1.md` tripped MD022 (four `###` advisory headings lacked a trailing
  blank line). Inserted the required blank lines so the worktree's repo-wide
  Markdown gate is green; this is a formatting-only fix to a review artefact and
  touches no design doc, ADR, or reference file. The escalation about the
  unassigned `tomli_w` snippet removal is unchanged.
- Escalation reaffirmed: the unassigned `tomli_w` snippet removal (design §5.3
  line 465; ADR 002 lines 22 and 77; snippet at `state-layout.md:229,235`)
  remains out of scope and is surfaced in this task's return value to the
  roadmap owner. Nothing in `docs/` or `skill/` was edited.

## Context and orientation

The repository is the Python package skeleton becoming the deterministic spine
of the novel-ralph harness. Orient with these files, all paths relative to the
worktree root `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-2`:

- `pyproject.toml` — `[project.dependencies] = ["cyclopts", "tomlkit"]`;
  `[project.scripts]` already wires the five console-scripts (task 1.2.1);
  `[tool.pytest.ini_options]` sets `timeout = 30`, `testpaths = ["tests"]`, and
  registers the `slow` marker; `requires-python = ">=3.14"`.
- `uv.lock` — pins `tomlkit` to `0.15.0` (and `cyclopts`, `cuprum`, the dev
  tools).
- `novel_ralph_skill/commands/stub.py` — the five exit-2 stubs from task 1.2.1.
  Untouched here.
- `tests/` — `test_stub.py`, `test_command_stubs.py`, `test_pyproject_scripts.py`,
  `test_console_scripts_e2e.py`. No `conftest.py`. New test lives alongside.
- `Makefile` — `make all` runs `build check-fmt lint typecheck test`. `make
  build` is `uv sync --group dev`. `make audit` is `uv run pip-audit`. `make
  test` is `uv run pytest -v -n auto`. `PYTHON_TARGETS = novel_ralph_skill
  tests`, so the new test is linted and type-checked. `make markdownlint` and
  `make nixie` gate Markdown and Mermaid.
- `docs/adr-002-toml-round-trip-tomlkit.md` — the dependency decision this task
  confirms; its "Migration plan" splits 1.2.2 (add) from 2.2.1 (exercise).
- `docs/novel-ralph-harness-design.md` §5.3 (TOML round-trip; line 465 carries
  the premature "is removed" claim, left untouched here), §3.4 (atomic writes —
  2.2.1 territory, named here only to mark the boundary), §8 (the three
  reference-file defects owned by 6.2.3 — which do **not** include the `tomli_w`
  snippet), §9 (verification strategy; the property round-trip is 2.2.1).
- `docs/roadmap.md` step 1.2 and task 1.2.2 (this task; narrow success criterion
  at line 102), task 2.2.1 (the round-trip helper, out of scope here), and task
  6.2.3 (lines 424–432 — the three reference-file defects, none being the
  `tomli_w` snippet).
- `skill/novel-ralph/references/state-layout.md` lines 226–238 — the stale
  `tomli_w` snippet; left in place. Its removal is **unassigned** in the roadmap
  and escalated to the roadmap owner (Decision Log), not edited here.

Terms of art, defined so the plan is self-contained:

- **Round-trip.** Reading a TOML document into a model and re-serialising it.
  A *lossless* round-trip reproduces the input byte-for-byte, including comments
  and whitespace. `tomlkit` provides this; `tomllib` (read-only) and `tomli_w`
  (no comment preservation) do not. This is the property ADR 002 buys.
- **Confirmation test.** A test whose purpose is to prove a dependency resolves,
  imports, and behaves as the design assumes — here, that the *locked* `tomlkit`
  round-trips comments. It is example-based, distinct from the property-based
  state round-trip (task 2.2.1).
- **Dependency confirmation vs. exercise.** ADR 002 splits "add the dependency"
  (task 1.2.2, here) from "exercise it in the state helper" (task 2.2.1). This
  plan stays on the 1.2.2 side of that line.

Authoritative sources to read before editing:

- `docs/roadmap.md` step 1.2, tasks 1.2.2 and 2.2.1 — the task and its boundary.
- `docs/adr-002-toml-round-trip-tomlkit.md` — the decision, its "Migration
  plan" (1.2.2 adds, 2.2.1 exercises), and its "Known risks" (the major-version
  regression the version pin tripwires).
- `docs/novel-ralph-harness-design.md` §5.3, §8, §9 — the round-trip decision,
  the prose-defect ownership, and the verification split.
- `AGENTS.md` — quality gates, en-GB Oxford spelling, 400-line limit, 100%
  docstring coverage, tests under `tests/`, Markdown guidance.

Skills to load before touching code (per the global agent instructions and the
worktree standing rules):

- `python-router` first, to route to the smaller skills below.
- `python-testing` for the confirmation test shape (a focused unit test, direct
  semantic assertions, no snapshot, no property suite here).
- `python-verification` is consulted only to confirm that the property-based
  round-trip is **not** in scope for this task (it is task 2.2.1); `hypothesis`,
  `crosshair`, and `mutmut` are not loaded or used here.
- `leta` for navigating the package; `sem` for history.

## Plan of work

One atomic, independently-committable work item, followed by a non-code
escalation note. The work item ends with its own validation, and `make all` must
be green before it is committed. The round-1 plan carried a second work item
(reconciling the design/ADR "is removed" overstatement); design review B1 and
direct verification showed it would inject a false 6.2.3 cross-reference for a
removal the roadmap does not assign to any task, so it is **dropped** and the
ownership gap is **escalated** instead (Decision Log).

### Work item 1 — Add the `tomlkit` dependency-confirmation test

Implements: roadmap task 1.2.2 ("confirm the build" against the extended
dependency set), ADR 002 ("Migration plan": `tomlkit` is added in 1.2.2), design
§5.3 (the lossless round-trip `tomlkit` provides).

Confirm the declared dependency first, without editing `pyproject.toml`
(`tomlkit` is already present; do not re-add or re-pin it — Tolerances):

- `make build` resolves the dependency set; confirm `uv.lock` still pins
  `tomlkit` at `0.15.0` (it does at planning time). If the version moved, follow
  the Lock-churn tolerance.
- `make audit` clears `tomlkit` (no known vulnerability).

Add a focused unit test, `tests/test_tomlkit_dependency.py`, that makes the
declared dependency provably load-bearing. The test module carries a docstring
stating it is the task-1.2.2 dependency-confirmation check, that it exercises an
in-test TOML string (not `state.toml`), and that the property-based state
round-trip is task 2.2.1 (design §9). The test:

1. imports `tomlkit` and asserts `tomlkit.__version__ == "0.15.0"` — the locked
   version (Decision Log; this is the tripwire for ADR 002's named major-version
   regression risk, carrying a `# why:` comment that the pin tracks `uv.lock`
   and is updated in lockstep with a deliberate bump);
2. asserts a no-op round-trip is lossless:
   `tomlkit.dumps(tomlkit.parse(SRC)) == SRC`, where `SRC` is a small in-test
   TOML string containing a standalone comment, an inline comment, and a table
   (verified locally to round-trip byte-for-byte);
3. asserts a targeted value edit preserves comments and changes only the target:
   parse `SRC`, mutate one value via the document model, `dumps`, and assert the
   standalone and inline comment text both survive in the output and the new
   value is present (verified locally: comment-preserved and value-changed).

Do **not** read or write `state.toml`, do **not** use `Path.replace`, and do
**not** add a Hypothesis strategy — those belong to task 2.2.1 (Constraints).
Keep the assertions direct and semantic; do not snapshot (Decision Log).

Read first: `docs/adr-002-toml-round-trip-tomlkit.md` (the decision and its
1.2.2/2.2.1 split), `docs/novel-ralph-harness-design.md` §5.3 and §9,
`.rules/python-00.md`, `.rules/python-return.md`.

Skills: `python-router`, then `python-testing` (focused unit test, direct
assertions). `python-verification` only to reconfirm no property suite belongs
here (that is 2.2.1).

Tests added/updated:

- `tests/test_tomlkit_dependency.py` — new unit test: imports `tomlkit`, pins
  the locked version, and asserts the parse/dump round-trip preserves comments
  and applies a value edit. This is the externally meaningful "confirm the
  build" evidence the roadmap criterion requires, and the load-bearing pin that
  keeps `tomlkit` from being silently droppable (no unused-dependency gate
  exists). No property test (deferred to 2.2.1); no snapshot (Decision Log); no
  behavioural or e2e test (a library-import confirmation has no workflow surface
  of its own — the install of `tomlkit` is already proven transitively by the
  task-1.2.1 wheel-build e2e in `tests/test_console_scripts_e2e.py`, which
  installs the whole dependency set into a fresh venv).

Validation:

- The new test fails if `tomlkit` is absent or its round-trip regresses, and
  passes against the locked `0.15.0`.
- `make build` succeeds and `uv.lock` still pins `tomlkit 0.15.0`.
- `make audit` passes (no known vulnerability in `tomlkit`).
- `make lint` (Ruff, `interrogate --fail-under 100`, Pylint), `make check-fmt`,
  `make typecheck` (`ty`), and `make test` pass.
- `make all` is green.

### Escalation (no code change) — unassigned `tomli_w` snippet removal

This is **not** a work item; it produces no commit. It records why the round-1
documentation work item was dropped and hands the gap to the roadmap owner.

Finding (verified): design §5.3 (line 465) and ADR 002 ("Decision outcome",
line 77) assert the failed `tomli_w` snippet "is removed", but the snippet is
still present at `skill/novel-ralph/references/state-layout.md:229,235`. ADR 002
is internally inconsistent on this too — line 22 (Context) says the reference
"even carries" it (present), line 77 says it "is removed" (past). The removal is
**not owned by any roadmap task**: design §8 (lines 644–664) and roadmap task
6.2.3 (lines 424–432) own exactly three other reference-file defects (the
`SKILL.md:107` phase mislabel, the two-source done predicate, and the dead
`state-layout.md:38` `plan.md` spec), and `grep -rn tomli_w docs/` shows no
ownership assignment anywhere.

Action for the roadmap owner (outside this task): assign the `tomli_w` snippet
removal to a roadmap task (most naturally folded into 6.2.3, which already owns
the other `state-layout.md` reference-file corrections, but that is the roadmap
owner's call). Once a task owns it, that task — not this one — should both
delete the snippet from `state-layout.md` and reconcile the design §5.3 / ADR
002
"is removed" claim (and ADR 002 line 22 vs line 77) so the documents become
truthful. Until then this plan leaves all of that prose untouched rather than
inventing an owner.

Why not fix it here: writing a *correct* sentence requires naming the real
owner, which does not yet exist; any sentence written now would either invent a
false 6.2.3 reference (design review B1) or assert an ownerless "pending"
removal, and either way folds an out-of-scope documentation concern into a task
whose roadmap success criterion (line 102) is purely "`make test` and the
quality gates pass against the extended dependency set". The escalation is the
correct disposition.

No files are edited and no tests are added for this escalation. It is surfaced
in this task's return value to the roadmap owner.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-2`.

Confirm the branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-2 branch --show-current
```

Expect `roadmap-1-2-2`.

The validation commands for the single work item are:

```bash
make build      # refresh lock, install deps
make audit      # dependency vulnerability gate
make all        # build check-fmt lint typecheck test
```

This task edits no Markdown and no Mermaid, so `make markdownlint` and
`make nixie` are **not** required for the work item itself. (This execplan is
itself Markdown; if the worktree's repo-wide gates lint `docs/execplans/`,
running `make markdownlint` over the plan is harmless and the plan is wrapped to
satisfy it. No design doc, ADR, or reference file is touched.)

Re-confirm the locked round-trip before relying on the test's pins (verified at
planning time; re-confirm on the target machine):

```bash
uv run python -c "import tomlkit; print(tomlkit.__version__)"   # expect 0.15.0
```

Expected high-level transcript (illustrative), after work item 1:

```plaintext
$ make test
... tests/test_tomlkit_dependency.py::test_tomlkit_import_and_version PASSED
... tests/test_tomlkit_dependency.py::test_tomlkit_roundtrip_preserves_comments PASSED
===== N passed in Xs =====
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- The declared `tomlkit` dependency resolves and installs: `make build` pins it
  in `uv.lock` (at `0.15.0`) and `make audit` clears it.
- `tomlkit` imports in the synced environment and the new test asserts its
  locked version and a lossless, comment-preserving parse/dump round-trip with a
  value edit — so the dependency is provably load-bearing and cannot be silently
  dropped (no unused-dependency gate exists).
- No design doc, ADR, or reference file is edited. The premature "is removed"
  claim in design §5.3 / ADR 002 and the still-present `tomli_w` snippet are
  left untouched; the unassigned-ownership gap is escalated to the roadmap owner
  (Decision Log, Surprises) rather than "fixed" with an invented owner.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `tests/test_tomlkit_dependency.py` is
  present and green; the pre-existing tests still pass.
- Lint/typecheck: `make lint` (Ruff, `interrogate --fail-under 100`, Pylint),
  `make check-fmt` (`ruff format --check`), and `make typecheck` (`ty check`)
  all pass.
- Audit: `make audit` (`pip-audit`) passes against the locked dependency set
  including `tomlkit`.
- Markdown/Mermaid: no source Markdown or Mermaid is changed by this task, so
  `make markdownlint` and `make nixie` are not gating criteria for the work
  item. (If repo-wide gates lint this execplan, it is wrapped to satisfy them.)
- Aggregate: `make all` is green at the work item's commit.

Quality method (how we check): run `make all` before and after the work item;
run `make audit` after it. There is no documentation work item to gate with
`make markdownlint` / `make nixie`.

## Idempotence and recovery

- The confirmation test is pure and re-runnable; it touches no tracked file
  beyond its own creation and writes nothing to `working/`.
- `make build` reconciles `uv.lock` deterministically; `tomlkit` is already
  present, so the build is a no-op on the dependency set.
- No documentation, ADR, or reference file is edited, so there is nothing to
  revert there; the escalation is record-only.
- If `make build` leaves a partial environment, `make clean` then `make build`
  restores a known state (the Makefile `clean` target removes `.venv`,
  `.uv-cache`, and build artefacts).
- No step is destructive to tracked files beyond the intended new test
  (`tests/test_tomlkit_dependency.py`) and updates to this execplan.

## Artifacts and notes

- The locked `tomlkit` version, verified: `0.15.0` (`uv.lock`; `import tomlkit;
  tomlkit.__version__`).
- The round-trip capability, verified locally against the locked `tomlkit`:
  `tomlkit.dumps(tomlkit.parse(src)) == src` for a comment-bearing string
  (byte-for-byte), and a value edit through the document model preserves the
  standalone and inline comments while changing the target value.
- Scope fence, restated: the `tomlkit` round-trip-and-atomic-write *helper*, the
  `[pending_turn]` intent record, and the property-based round-trip over
  generated states are roadmap task **2.2.1** (design §3.4, §9), not this task.
  The removal of the `tomli_w` snippet from
  `skill/novel-ralph/references/state-layout.md` — and the matching correction
  of the design §5.3 / ADR 002 "is removed" claim — is **unassigned** in the
  roadmap and escalated to the roadmap owner; it is not done here and must not
  be faked with an invented 6.2.3 (or any) owner.

## Interfaces and dependencies

Dependencies: **no change** to `pyproject.toml` dependency tables. `tomlkit` is
already in `[project.dependencies]` and `uv.lock`. This task adds no runtime and
no dev dependency.

New test surface, `tests/test_tomlkit_dependency.py` (illustrative shape; the
implementer pins the exact assertions against the locked `tomlkit`):

```python
"""Confirm the locked tomlkit dependency for roadmap task 1.2.2.

This is the dependency-confirmation check: it proves tomlkit resolves,
imports, and round-trips comments at the locked version. It operates on an
in-test TOML string, not ``state.toml``. The property-based round-trip over
generated states is roadmap task 2.2.1 (design §9); it is intentionally not
here.
"""

from __future__ import annotations

import tomlkit

# why: tracks uv.lock; bump in lockstep with a deliberate tomlkit upgrade.
LOCKED_TOMLKIT_VERSION = "0.15.0"

SRC = '# standalone comment\nkey = "value"  # inline comment\n\n[table]\na = 1\n'


def test_tomlkit_import_and_version() -> None:
    """tomlkit imports and resolves to the locked version."""
    assert tomlkit.__version__ == LOCKED_TOMLKIT_VERSION


def test_tomlkit_roundtrip_is_lossless() -> None:
    """A no-op parse/dump round-trips the source byte-for-byte."""
    assert tomlkit.dumps(tomlkit.parse(SRC)) == SRC


def test_tomlkit_edit_preserves_comments() -> None:
    """A value edit changes only the target and keeps the comments."""
    doc = tomlkit.parse(SRC)
    doc["table"]["a"] = 2
    out = tomlkit.dumps(doc)
    assert "# standalone comment" in out
    assert "# inline comment" in out
    assert "a = 2" in out
```

Out of scope (do not build here): the `tomlkit` round-trip helper, the atomic
temp-file-and-`Path.replace` write, and the `[pending_turn]` intent record (task
2.2.1, design §3.4); the property-based round-trip over generated states (task
2.2.1, design §9); deleting the `tomli_w` snippet from
`skill/novel-ralph/references/state-layout.md` and correcting the design §5.3 /
ADR 002 "is removed" claim (currently **unassigned** in the roadmap — escalated,
not done here, and not to be attributed to a manufactured owner); any real
command behaviour (design §4.1–§4.5).

## Revision note

- 2026-06-21 (planning round 1): Authored the self-contained plan against the
  locked toolchain. Verified empirically that `tomlkit` is already declared in
  `[project.dependencies]` and pinned to `0.15.0` in `uv.lock` (so the task's
  real deliverable is "confirm the build", not "add the dependency"); that the
  locked `tomlkit` round-trips a comment-bearing TOML string byte-for-byte and
  preserves comments across a value edit; that no unused-dependency gate exists,
  making the confirmation test the thing that keeps `tomlkit` load-bearing; and
  that the failed `tomli_w` snippet the design/ADR claim is "removed" is in fact
  still present in `state-layout.md`. (Round 1 wrongly assumed design §8
  assigned that snippet's removal to task 6.2.3; round 2 corrects this — see
  below.) Scoped the plan to stay on the 1.2.2 side of the 2.2.1 boundary (no
  state helper, no property suite). The plan remained in DRAFT pending review.
- 2026-06-21 (planning round 2, after design review B1): The design reviewer
  verified, and I re-verified, that the `tomli_w` snippet removal is **not**
  owned by roadmap task 6.2.3 or any other task — design §8 (lines 644–664) and
  roadmap 6.2.3 (lines 424–432) own only three other reference-file defects, and
  `grep -rn tomli_w docs/` finds no ownership assignment. The round-1 plan would
  have rewritten design §5.3 and ADR 002 to forward-reference 6.2.3, injecting
  a **false** cross-reference into documents the task must keep truthful.
  Resolution (review path (a)): **dropped** the documentation work item
  entirely; removed every claim that 6.2.3 (or any task) owns the removal from
  Purpose, Constraints, Tolerances, Risks, Progress, Surprises, Decision Log,
  Plan of work, Validation, Idempotence, Artifacts, and Interfaces; replaced
  Work Item 2 with a record-only escalation that hands the unassigned-ownership
  gap (and ADR 002's internal line-22-vs-line-77 inconsistency, advisory A2) to
  the roadmap owner with exact locations. The plan now has one work item (the
  confirmation test) plus the escalation, and edits no `docs/`, `skill/`, or
  `pyproject.toml` source. This also resolves advisory A1 (the doc fix was
  scope creep against roadmap 1.2.2's narrow success criterion). Advisory A3
  (the exact version pin is an eyes-open tripwire) is retained by design; A4
  (one three-behaviour test module) is unchanged. Still DRAFT; none begun.
