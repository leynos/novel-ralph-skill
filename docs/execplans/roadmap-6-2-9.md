# Extend the installed per-chapter loop re-drive to the refused-advance and crossed-gate decisions

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT

## Purpose / big picture

Roadmap task 6.2.9 closes a documented test-gap at the **installed packaging
boundary** of the per-chapter deterministic loop. The in-process feature
([`tests/features/per_chapter_loop.feature`](../../tests/features/per_chapter_loop.feature))
pins four deterministic decisions over real `working/` trees: a clean pass, a
caught stale compile, a crossed knitting gate, and a refused out-of-order
`advance-phase`. The installed re-drive
([`tests/features/per_chapter_loop_installed.feature`](../../tests/features/per_chapter_loop_installed.feature),
roadmap 6.2.2) crosses those decisions over a **built wheel installed into a
throwaway venv** — the real boundary an operator and the harness invoke — but
today it re-drives only the clean pass and the stale-compile catch.

Post-merge audit
[`docs/issues/audit-6.2.2.md`](../../docs/issues/audit-6.2.2.md) Finding 7
records the omission: the **crossed knitting gate** (design §4.5) and the
**refused out-of-order `advance-phase`** (design §3.2, §4.1; exit 3) are proven
only in-process. The exit-3 state-error arm is the high-value half. The shared
runner [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
owns the exit-3 channel two distinct ways, and the `completed-prefix-gap` case
exercises the second: it does **not** pre-parse a usage error before the body
(that path stamps exit 2 from a `CycloptsError`); instead the `advance-phase`
body raises a domain `StateInputError` from `_refuse_if_incoherent(prior)` in
[`novel_ralph_skill/commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py),
which the runner catches in its `try` block and translates to a stamped
exit-3 envelope (`runner.py:233-239`). The installed boundary is therefore exactly
where a packaging regression (a wrong `sys.exit` translation, a swallowed
traceback) would first surface. Finding 7 offers the
design §9 "carried knowingly rather than silently" choice: add the installed
re-drive of both decisions, **or** name the in-process-only bound in the
developers' guide / a `Carried gaps` entry.

This plan takes the **add-the-re-drive** option, because verification (see
`Surprises & Discoveries`, item S1) confirms the refused-advance decision needs
a genuine new installed scenario, while the crossed-gate decision is **already
proven at the installed boundary today** by the existing clean-pass scenario's
`Then the installed wordcount reports all three knitting gates crossed` step
(installed steps, `installed_wordcount_gates`, asserting
`gate_triggered_30/50/80 is True` at the 68800-word drafted total). The plan
therefore adds one new installed scenario for the refused advance and makes the
existing crossed-gate coverage explicit in the developers' guide, so both
decisions of the roadmap success clause are demonstrably proven over the real
installed console-script.

After this change, a maintainer can run the installed loop suite on a POSIX host
and see a second `@slow` scenario drive the **installed** `novel-state
advance-phase` over the `completed-prefix-gap` corpus tree, observe it exit 3
(`STATE_ERROR`), leave `working/state.toml` byte-for-byte intact, and emit no
traceback on stderr — proving the runner-stamped exit-3 mutator-refusal contract
(§3.2) at the real wheel/venv boundary, not merely in-process.

Observable acceptance:

- Running `make all` passes; the new installed scenario
  `the installed loop refuses an out-of-order advance-phase` is collected and
  run inline (the gate does **not** deselect slow items — see S3), marked
  `@slow`/`@timeout(180)`/POSIX-skip, and passes on a POSIX host.
- The exit-3 assertion in the new `Then` step is the behaviour pin: it fails
  (red) if pointed at a coherent tree and passes (green) against
  `completed-prefix-gap`, demonstrable transiently per `Concrete steps`.
- The mark-retention guard `test_installed_advance_refused_carries_marks` fails
  if any of the three marks is dropped from the new scenario's bound function.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work happens **only** in the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-9`. The
  root/control worktree is off-limits for edits.
- Do **not** modify production code under `novel_ralph_skill/`. This is a
  test-and-docs-only task; the commands' behaviour is already correct and
  in-process-proven. If any production change appears necessary, stop and
  escalate.
- Do **not** weaken or alter the existing in-process feature
  (`per_chapter_loop.feature`) or its steps; the in-process refused-advance
  scenario remains the cross-platform proof.
- **Every committed work item must leave `make all` green.** The repo gate runs
  slow tests inline — `make test` is `pytest -v -n auto` with **no**
  `-m 'not slow'` deselection (`Makefile:116`); `pyproject.toml` defines only
  `markers = ["slow: …"]` (line 328) with no `addopts`; `conftest.py` has no
  `collect_modifyitems` deselection; and CI runs `make test` on `ubuntu-latest`
  (POSIX; `.github/workflows/ci.yml`). The new `@slow` POSIX scenario is
  therefore **collected and executed** by `make all` and by CI. Consequently the
  feature, the binder, and **all three** step definitions must land together in
  **one** gated commit (WI-1); no commit may leave a scenario whose steps are
  undefined (AGENTS.md lines 100, 108; ExecPlan "Commit only after `make all` is
  green").
- The new installed scenario must carry **all three** marks the existing
  installed scenario carries — `@pytest.mark.slow`,
  `@pytest.mark.timeout(180)`, and the POSIX `@pytest.mark.skipif` — so it never
  runs the wheel build on a non-POSIX leg or under the global 30s timeout
  (ADR-006; design §9). No marker may leak onto the cross-platform in-process
  scenarios (Decision D-INSTALLED-SPLIT, already established by 6.2.2).
- Reuse the locked external surface as-is. cuprum is pinned at **0.1.0**
  (`uv.lock` lines 113-118); only the APIs the existing installed module already
  uses may be relied on (see `Interfaces and dependencies`). No new external
  dependency.
- Prose, comments, and commit messages use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`), per AGENTS.md and the `en-gb-oxendict` skill.
- Obey AGENTS.md module/file boundaries (the 400-line module cap) and the
  `tests/steps/` assert/argument-count exemption. The installed steps module is
  currently **262 lines**; the WI-1 additions must keep it under 400.

## Tolerances (exception triggers)

- Scope: if the implementation requires touching more than **5 files** or more
  than **~120 net lines**, stop and escalate. (Expected: the installed feature,
  the installed steps module, the installed binder, the developers' guide, and
  this plan.)
- Production code: if **any** file under `novel_ralph_skill/` must change, stop
  and escalate — this contradicts the test-and-docs-only constraint.
- Interface: if a new public corpus accessor or a new cuprum API is needed, stop
  and escalate; the plan is predicated on reusing
  `INCOHERENT_VARIANTS["completed-prefix-gap"]` and the
  `_run_installed_argv` helper specified below.
- Dependencies: if a new external dependency is required, stop and escalate.
- Iterations: if the new installed scenario still fails after **3** focused fix
  attempts, stop and escalate.
- Wheel-build time: if the installed scenario's wheel build pushes the bound
  test past the 180s timeout budget, stop and escalate rather than raising the
  budget silently.
- Module size: if wiring the new steps would push
  `tests/steps/per_chapter_loop_installed_steps.py` over the 400-line cap, stop
  and escalate (the planned refactor in WI-1 is expected to keep it well under).
- Ambiguity: if `make all` surfaces a snapshot or contract change in an unrelated
  module, stop and escalate rather than refreshing snapshots.

## Risks

- Risk: the new installed scenario silently loses one of its three marks
  (slow / timeout / POSIX skip), running the wheel build on a non-POSIX leg or
  under the 30s global timeout.
  Severity: medium.
  Likelihood: low.
  Mitigation: WI-2 adds a wheel-free mark-retention guard
  `test_installed_advance_refused_carries_marks` mirroring the existing
  `test_installed_scenario_carries_marks`, reading the bound function's
  `pytestmark`. The Constraints forbid dropping a mark.

- Risk: a second `@scenario`-decorated function in the same binder shares step
  fixtures with the first and causes step-collision or target-fixture bleed
  between scenarios.
  Severity: low.
  Likelihood: low.
  Mitigation: the new scenario uses its own `Given`/`When`/`Then` phrases and
  its own `target_fixture="installed"` given (the installed `_Installed`
  dataclass already supports per-test independence via per-test `run_dir`).
  pytest-bdd binds each `@scenario` function as an independent test item.

- Risk: the wheel build runs twice (once per installed scenario) inflating
  suite time.
  Severity: low.
  Likelihood: medium.
  Mitigation: the `installed_novel_state` fixture is **module-scoped**
  (`tests/installed_binary_fixtures.py`, Decision D-SCOPE), so both scenarios in
  the same binder module reuse one wheel build and one venv install.

- Risk: the capture-key collision — the refused-advance run writes under the
  same `novel-state` key the clean-pass loop uses, so the `Then` step reads the
  wrong capture.
  Severity: medium.
  Likelihood: low (the two scenarios run as independent test items with
  independent `_Installed` instances, so captures do not actually share a dict).
  Mitigation: the new `When` step writes under the **distinct** capture key
  `"advance-phase"` (not `"novel-state"`) via the `_run_installed_argv` helper's
  `capture_key` parameter, mirroring the in-process step's
  `outcome.captures["advance-phase"]` key (`per_chapter_loop_steps.py:316`).

- Risk: the developers' guide edit drifts from the feature's actual coverage
  (claims a decision is proven that is not, or vice versa).
  Severity: low.
  Likelihood: low.
  Mitigation: word the guide to match exactly what the feature asserts — clean
  pass, stale-compile catch, crossed gate (folded into the clean pass), and
  refused advance — and run `make markdownlint` and `make nixie`.

## Progress

- [x] WI-1: Add the installed refused-advance scenario, binder function, the
  `_run_installed_argv` helper, and all three step definitions in one gated
  commit (the scenario passes green; no intermediate red commit). Done in commit
  "Re-drive refused advance-phase at installed boundary". The behaviour pin was
  demonstrated transiently (see Artifacts); `make all` green (941 passed, 1
  skipped); coderabbit `--agent` returned 0 findings.
- [x] WI-2: Add the mark-retention guard for the new scenario. Done:
  `test_installed_advance_refused_carries_marks` mirrors the existing guard,
  reads the bound function's `pytestmark`, and asserts the set `>= _REQUIRED_MARKS`.
  Both `*_carries_marks` guards pass wheel-free; `make all` green (942 passed).
- [x] WI-3: Make the existing crossed-gate installed coverage explicit in the
  developers' guide; record the decision. Done: the "per-chapter deterministic-loop
  scenario" section now states the full installed coverage (clean pass, crossed
  knitting gate folded into the clean pass, stale-compile catch, refused
  out-of-order advance) and names both mark-retention guards. `make markdownlint`,
  `make nixie`, and `make all` all green.

## Surprises & discoveries

- Observation (S1): the crossed knitting gate is *already* proven at the
  installed boundary; only the refused advance is a genuine gap.
  Evidence: `tests/steps/per_chapter_loop_installed_steps.py`
  `installed_wordcount_gates` asserts `cumulative["gate_triggered_30/50/80"] is
  True` at `_DRAFTED_TOTAL == 68800` over the clean tree, bound by the existing
  scenario's `Then the installed wordcount reports all three knitting gates
  crossed`. The in-process feature folds the crossed gate into the clean pass
  identically (`per_chapter_loop_steps.wordcount_gates_crossed`).
  Impact: the plan adds **one** new installed scenario (refused advance) and
  documents the crossed-gate coverage rather than adding a redundant
  crossed-gate scenario.

- Observation (S2): the installed step driver `_run_installed(installed,
  command_name)` is hardwired against reuse for the refused advance in **two**
  ways. (a) It looks up argv via `_LOOP_ARGV[command_name]`, and
  `_LOOP_ARGV["novel-state"]` is `("recount",)`, not `("advance-phase",)`. (b)
  It uses the single `command_name` argument simultaneously as the **script
  filename** (`scripts_dir / command_name`), the **argv key**
  (`_LOOP_ARGV[command_name]`), and the **capture key** (callers store under
  `installed.captures[command_name]`). For the refused advance the script file
  is `novel-state` but the capture key must be `advance-phase` (distinct from the
  clean-pass `novel-state`/recount capture) and the argv must be
  `("advance-phase",)`. A helper that separates `(script_name, argv,
  capture_key)` is genuinely required.
  Evidence: `per_chapter_loop_installed_steps.py:81-102` (`_run_installed`);
  `:55-61` (`_LOOP_ARGV`); the in-process refused step keys on `"advance-phase"`
  (`per_chapter_loop_steps.py:316`).
  Impact: WI-1 introduces `_run_installed_argv(installed, script_name, argv, *,
  capture_key)` (signature pinned in `Interfaces and dependencies`) and
  refactors `_run_installed` to delegate to it, keeping the clean-pass loop
  byte-identical while giving the refused advance an explicit argv and a distinct
  capture key.

- Observation (S3): the repo gate **does not deselect slow tests**, so a slow
  scenario with undefined steps fails `make all` and CI.
  Evidence: `Makefile:116` is `… pytest -v -n $(PYTEST_XDIST_WORKERS)` (no
  `-m 'not slow'`); `pyproject.toml:326-328` sets `timeout = 30`,
  `testpaths = ["tests"]`, `markers = ["slow: …"]` and **no** `addopts`;
  `tests/conftest.py` has no `pytest_collection_modifyitems` deselection;
  `.github/workflows/ci.yml:10` runs on `ubuntu-latest` and invokes `make test`.
  Impact: corrects the round-1 plan's false "the binder carries `@slow`, so
  `make all` may deselect the slow item" hedge. There is no slow deselection
  anywhere; the slow scenario runs inline. The feature, binder, helper, and all
  three steps therefore land in one green commit (WI-1) — no separate red commit
  is permissible.

## Decision log

- Decision: add the refused-advance installed scenario; document (do not
  re-prove) the crossed-gate decision.
  Rationale: audit-6.2.2 Finding 7 offers add-or-document. The crossed gate is
  already installed-proven (S1), so adding a crossed-gate scenario would be
  redundant; the refused-advance exit-3 arm is runner-stamped and is the
  decision the installed boundary most exists to prove (Finding 7's own
  "highest-value addition").
  Date/Author: 2026-06-25, planning agent.

- Decision: land the feature, binder, `_run_installed_argv` helper, and all
  three steps in **one** gated commit (WI-1), not a red→green split.
  Rationale: the gate runs slow tests inline (S3). A commit that adds the
  scenario and binder but leaves steps undefined would make `make all` and CI
  fail on the undefined-step error, violating AGENTS.md lines 100/108 and the
  ExecPlan "commit only after `make all` is green" rule. Atomicity is preserved:
  WI-1 is a single self-contained, gate-passable unit. The red→green discipline
  is still satisfied **within** WI-1 by the transient coherent-tree
  demonstration in `Concrete steps` (the exit-3 assertion fails when pointed
  at a coherent tree, passes against `completed-prefix-gap`), which is the
  behaviour
  pin without committing a failing state.
  Date/Author: 2026-06-25, planning agent.

- Decision: drive the installed `novel-state advance-phase` through a new
  `_run_installed_argv(installed, script_name, argv, *, capture_key)` helper, and
  refactor `_run_installed` to delegate to it.
  Rationale: `_run_installed` conflates script filename, argv key, and capture
  key into one `command_name` (S2). The refused advance needs a `novel-state`
  script, `("advance-phase",)` argv, and an `"advance-phase"` capture key — three
  values the single argument cannot express. `_run_installed_argv` separates
  them; `_run_installed(installed, command_name)` becomes a one-line delegation
  `_run_installed_argv(installed, command_name, _LOOP_ARGV[command_name],
  capture_key=command_name)` that returns the same tuple, so the clean-pass and
  stale-compile loops are byte-identical in behaviour. The capture write is
  centralised in the helper so the `When` steps no longer assign
  `installed.captures[...]` by hand (see signature below).
  Date/Author: 2026-06-25, planning agent.

- Decision: keep the new scenario in the **same** installed feature and binder
  as the clean-pass scenario, each bound by its own `@scenario`-decorated
  function carrying the three marks.
  Rationale: the binder already houses the installed loop and its mark-retention
  guard; a `@scenario`-decorated function "behaves like a normal test function"
  (pytest-bdd 8.1.0), so stacked `@pytest.mark.*` attach per function and do not
  leak between scenarios or onto the in-process scenarios (Decision
  D-INSTALLED-SPLIT). A second feature file would duplicate the slow/POSIX
  scaffolding for no gain.
  Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

Delivered 2026-06-25 across three gated commits. Against the roadmap 6.2.9
success clause — "the refused out-of-order `advance-phase` (exit 3) and the
crossed-gate report are each proven over the real installed console-script
boundary, or the in-process-only bound is named in the Carried gaps section":

- Refused out-of-order `advance-phase` (exit 3): **proven** at the installed
  boundary by the new `the installed loop refuses an out-of-order advance-phase`
  scenario (WI-1), which drives the installed `novel-state advance-phase` over the
  `completed-prefix-gap` corpus tree and asserts exit 3, `state.toml`
  byte-for-byte intact, and no traceback. The behaviour pin was demonstrated
  transiently (red against `COHERENT_BASELINE`, green against
  `completed-prefix-gap`).
- Crossed-gate report: **proven** at the installed boundary (pre-existing, S1) by
  the clean-pass scenario's `the installed wordcount reports all three knitting
  gates crossed` step. WI-3 makes this explicit in the developers' guide so no
  reader expects a standalone crossed-gate installed scenario.

Both halves of the success clause are therefore proven at the real
wheel/venv console-script boundary; no Carried-gaps entry is required.

Deviations: none of substance. A `ruff format` reflow of the `state_before`
assignment was applied during WI-1's gate (recorded in Artifacts). Pre-existing
markdownlint MD013 violations in the untracked planning artefact
`roadmap-6-2-9.logisphere-review-r2.md` were wrapped during WI-3 so the
whole-tree markdownlint gate passed. No production code under
`novel_ralph_skill/` was touched; the change stayed within the 5-file / ~120-line
tolerance (3 test files, 1 doc file, plus this plan and its review artefact).

Coderabbit: WI-1 reviewed with 0 findings. The WI-2/WI-3 review cycle was
initially rate-limited (Pro account; successive `rate_limit` responses through
the policy's exponential backoff, the reported wait time decaying from ~6m41s to
~1m16s on each fresh call) and finally cleared on the closing attempt, returning
0 findings over the full HEAD diff (all three commits). No actionable feedback
was raised. The deterministic gates (`make all`, `make markdownlint`,
`make nixie`) are green at HEAD for all three commits.

## Context and orientation

This repository packages the novel-ralph harness skill plus a Python package
`novel_ralph_skill` exposing five deterministic console-scripts (`novel-state`
with its `recount`/`advance-phase`/… subcommands, `novel-done`, `wordcount`,
`desloppify`, `novel-compile`). Each command emits a JSON envelope on stdout and
signals outcome through a POSIX exit code defined in
[`novel_ralph_skill/contract/exit_codes.py`](../../novel_ralph_skill/contract/exit_codes.py):
`SUCCESS = 0`, `STATE_ERROR = 3`, `ACTIONABLE_FINDING = 4`. The shared runner
[`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
runs the command body inside a `try` and translates the exception it raises into
the contract code: a Cyclopts usage fault becomes exit 2, and a domain
`StateInputError` becomes the stamped exit-3 state-error envelope
(`runner.py:233-239`; design §3.2; ADR-003). Two exit-3 surfaces therefore exist
and must not be conflated: a *pre-body* fault the runner detects before the body
returns (a missing-argument or unparsed-flag case stamped from the parse layer),
and an *in-body* domain refusal the body raises explicitly. The
`completed-prefix-gap` refused advance is the in-body kind — the `advance-phase`
body raises `StateInputError` from `_refuse_if_incoherent(prior)` (design §4.1),
not a pre-parse global-flag error.

The per-chapter deterministic loop is the ordered drive of the five read
surfaces over one chapter's `working/` tree (design §7.2, Figure 3; §9 lines
814-847). It is proven two ways:

- **In-process** —
  [`tests/features/per_chapter_loop.feature`](../../tests/features/per_chapter_loop.feature),
  steps
  [`tests/steps/per_chapter_loop_steps.py`](../../tests/steps/per_chapter_loop_steps.py),
  bound by the mark-free
  [`tests/test_per_chapter_loop_bdd.py`](../../tests/test_per_chapter_loop_bdd.py).
  It drives the commands through the shared `run` wrapper in-process and includes
  the refused-advance scenario (`advance-phase` exits 3, `state.toml`
  byte-for-byte intact; steps at `per_chapter_loop_steps.py:293-327`).
- **Installed** —
  [`tests/features/per_chapter_loop_installed.feature`](../../tests/features/per_chapter_loop_installed.feature),
  steps
  [`tests/steps/per_chapter_loop_installed_steps.py`](../../tests/steps/per_chapter_loop_installed_steps.py),
  bound by
  [`tests/test_per_chapter_loop_installed_bdd.py`](../../tests/test_per_chapter_loop_installed_bdd.py).
  It builds a wheel, installs every console-script into a throwaway venv, and
  runs each script by absolute path through a cuprum catalogue allowlist
  (POSIX-only; ADR-006). Today it re-drives only the clean pass and the
  stale-compile catch.

Key reusable machinery (all already present, all to be reused):

- The module-scoped `installed_novel_state` fixture
  ([`tests/installed_binary_fixtures.py`](../../tests/installed_binary_fixtures.py))
  builds the wheel and venv once per module and returns the absolute path of the
  installed `novel-state` script; its sibling scripts resolve from
  `installed_novel_state.parent` (the venv `bin/`).
- The `single_program_catalogue` fixture
  ([`tests/conftest.py`](../../tests/conftest.py) line 245-274) returns a builder
  `(name, program) -> ProgramCatalogue` allowlisting exactly one absolute-path
  `Program`.
- `_run_installed(installed, command_name)`
  ([`tests/steps/per_chapter_loop_installed_steps.py`](../../tests/steps/per_chapter_loop_installed_steps.py)
  lines 81-102) runs an installed script by absolute path through a
  single-program cuprum catalogue with `ExecutionContext(cwd=run_dir)` and
  returns `(exit_code, envelope, stderr)`. It is the helper WI-1 generalises.
  `_assert_no_traceback(installed, command_name)` (lines 111-118) asserts no
  `Traceback` on stderr (design §10). `_build_installed(...)` (lines 121-139)
  materialises a `working/` tree under a per-test `run_dir` and returns an
  `_Installed`.
- The corpus spec `INCOHERENT_VARIANTS["completed-prefix-gap"]`
  ([`tests/working_corpus/__init__.py`](../../tests/working_corpus/__init__.py),
  exported public name) is the `drafting` tree whose
  `phase.completed = ("premise", "characters")` skips the in-order prefix, so
  `advance-phase` must refuse it. The in-process refused-advance scenario already
  builds exactly this tree (`per_chapter_loop_steps.py:308`).

Terms used:

- **Refused out-of-order advance** — `novel-state advance-phase` invoked on a
  tree whose `phase.completed` skips an in-order prefix; the mutator refuses the
  write and exits 3, leaving `state.toml` unchanged (design §3.2, §4.1).
- **Crossed knitting gate** — `wordcount` reporting
  `gate_triggered_30/50/80 == True` once the cumulative drafted total passes each
  threshold (design §4.5).
- **Installed boundary** — the wheel/venv console-script an operator runs, as
  opposed to the in-process Cyclopts app (ADR-006).

## Plan of work

Stage A (understand) is complete: this plan. Stages B-D are the three work items
below, each independently committable and gate-passable. Each work item ends with
`make all` (and, for the doc work item, `make markdownlint` and `make nixie`).

The round-1 four-item split (scenario+binder red, then steps green) is
**abandoned**: the gate runs slow tests inline (S3), so a red commit would fail
`make all` and CI, violating AGENTS.md lines 100/108. WI-1 below is the merged,
green-in-one-commit unit.

### WI-1 — Add the installed refused-advance scenario, helper, binder, and steps (one green commit)

Implements: roadmap 6.2.9 (success clause, refused-advance half); audit-6.2.2
Finding 7; design §3.2, §4.1 (refused mutator → exit 3), §5.4 (refused mutator
leaves `state.toml` intact), §9 (installed boundary proves exit codes), §10 (no
traceback); ADR-003 (shared envelope), ADR-006 (POSIX-only installed e2e).

Docs to read first: design §3.2 (exit codes), §4.1 (`advance-phase`), §5.4
(disk evidence — refused mutator must not touch `state.toml`), §9 lines 814-847
(loop scope at the installed boundary), §10 (structured message, never a stack
trace); ADR-003; ADR-006; audit-6.2.2.md Finding 7; the in-process
refused-advance steps (`per_chapter_loop_steps.py:293-327`) as the behavioural
oracle to mirror at the installed boundary.

Skills to load: `python-router` → `python-testing` (pytest-bdd scenario
decorator, marks, fixtures, step phrasing); `leta` for navigation;
`en-gb-oxendict` for prose in the feature header comment and docstrings.

Edits:

1. In
   [`tests/features/per_chapter_loop_installed.feature`](../../tests/features/per_chapter_loop_installed.feature),
   add a second scenario after the existing one:

   ```gherkin
   Scenario: the installed loop refuses an out-of-order advance-phase
     Given an installed loop tree whose phase.completed skips the in-order prefix
     When the installed advance-phase runs over the out-of-order tree
     Then the installed advance-phase exits 3 with state.toml byte-for-byte intact and no traceback
   ```

   Extend the feature's header comment to name the new decision and cite
   audit-6.2.2 Finding 7, design §3.2/§4.1/§5.4.

2. In
   [`tests/steps/per_chapter_loop_installed_steps.py`](../../tests/steps/per_chapter_loop_installed_steps.py),
   make these changes (all under the `tests/steps/` exemption; keep the module
   under 400 lines — it is 262 today and these edits add roughly 45 lines):

   - **Generalise the run helper.** Replace the body of `_run_installed` with a
     delegation to a new `_run_installed_argv`. The new helper has the exact
     signature

     ```python
     def _run_installed_argv(
         installed: _Installed,
         script_name: str,
         argv: tuple[str, ...],
         *,
         capture_key: str,
     ) -> tuple[int, dict[str, object], str]:
     ```

     It resolves `installed.scripts_dir / script_name`, builds the
     single-program catalogue keyed `f"per-chapter-loop-{capture_key}"`, runs
     `sh.make(prog, catalogue=catalogue)(*argv)` with
     `ExecutionContext(cwd=installed.run_dir)`, parses the JSON envelope, writes
     the `(exit_code, envelope, stderr)` tuple into
     `installed.captures[capture_key]`, and returns it. `_run_installed` becomes:

     ```python
     def _run_installed(
         installed: _Installed, command_name: str
     ) -> tuple[int, dict[str, object], str]:
         return _run_installed_argv(
             installed,
             command_name,
             _LOOP_ARGV[command_name],
             capture_key=command_name,
         )
     ```

     This keeps the clean-pass and stale-compile loops byte-identical (same
     script filename, same argv, same capture key) while centralising the
     capture write. (The two existing `When` steps `run_installed_clean_spine`
     and `run_installed_stale` already assign `installed.captures[...] =
     _run_installed(...)`; since `_run_installed_argv` now writes the capture
     itself, change those assignments to bare calls — e.g.
     `_run_installed(installed, command_name)` — so the capture is not written
     twice. This is a behaviour-preserving simplification; record it in the
     module docstring.)

   - **Record the prior `state.toml`.** Add an optional
     `state_before: bytes | None = None` field to the `_Installed` dataclass
     (mirroring the in-process `_Outcome.state_before` at
     `per_chapter_loop_steps.py:84`). Existing givens leave it `None`.

   - **Add the `Given` step** `"an installed loop tree whose phase.completed
     skips the in-order prefix"` with `target_fixture="installed"`. It calls
     `_build_installed(installed_novel_state, tmp_path, single_program_catalogue,
     INCOHERENT_VARIANTS["completed-prefix-gap"][0])`, then captures
     `(run_dir / "working" / "state.toml").read_bytes()` into the returned
     `_Installed.state_before`, and returns it. Reuse `_build_installed`; do not
     duplicate the tree-build.

   - **Add the `When` step** `"the installed advance-phase runs over the
     out-of-order tree"` that calls
     `_run_installed_argv(installed, "novel-state", ("advance-phase",),
     capture_key="advance-phase")`. The script file is `novel-state`; the argv
     selects the `advance-phase` subcommand; the capture key is the distinct
     `"advance-phase"` (mirroring the in-process key at
     `per_chapter_loop_steps.py:316`), so it never collides with the clean-pass
     `novel-state`/recount capture.

   - **Add the `Then` step** `"the installed advance-phase exits 3 with
     state.toml byte-for-byte intact and no traceback"` asserting:
     - `installed.captures["advance-phase"][0] == ExitCode.STATE_ERROR` (3);
     - `(installed.run_dir / "working" / "state.toml").read_bytes() ==
       installed.state_before` (the refused mutator left the file untouched —
       design §5.4);
     - `_assert_no_traceback(installed, "advance-phase")` (design §10).

3. In
   [`tests/test_per_chapter_loop_installed_bdd.py`](../../tests/test_per_chapter_loop_installed_bdd.py),
   add a second `@scenario`-decorated function, stacking the same three marks as
   the existing one, binding the new scenario name:

   ```python
   @pytest.mark.slow
   @pytest.mark.timeout(180)
   @pytest.mark.skipif(
       os.name != "posix",
       reason="installed loop e2e is POSIX-only; see ADR 006",
   )
   @scenario(
       "features/per_chapter_loop_installed.feature",
       "the installed loop refuses an out-of-order advance-phase",
   )
   def test_installed_advance_phase_refused() -> None:
       """Bind the installed refused-advance scenario, carrying the marks."""
   ```

Tests added/updated by WI-1: the new Gherkin scenario, its three step
definitions, the generalised `_run_installed_argv` helper (with `_run_installed`
delegating), the `_Installed.state_before` field, and the binder function. **No
production code.** The whole installed suite (clean pass + stale compile +
refused advance) passes under one module-scoped wheel build.

Validation: `make all` on a POSIX host — all of `build`, `check-fmt`, `lint`,
`typecheck`, `test` must pass with the new scenario **green** (the slow item runs
inline; there is no deselection). Before committing, demonstrate the behaviour
pin transiently: point the new `Given` at a coherent tree
(`INCOHERENT_VARIANTS` → a coherent spec, e.g. a `drafting` clean spec) and
confirm the exit-3 assertion **fails** (red), then revert to
`completed-prefix-gap` and confirm it **passes** (green). Record both transcripts
in `Concrete steps`. **Commit only after `make all` is green.**

### WI-2 — Add the mark-retention guard for the new scenario

Implements: design §9 (carried-knowingly / boundary integrity); ADR-006
(POSIX-only); mirrors the existing `test_installed_scenario_carries_marks` guard.

Docs to read first: the existing `test_installed_scenario_carries_marks` in the
installed binder
(`tests/test_per_chapter_loop_installed_bdd.py`); pytest-timeout 2.4.0 marker
precedence (verified — see `Interfaces and dependencies`).

Skills to load: `python-router` → `python-testing`.

Edits in
[`tests/test_per_chapter_loop_installed_bdd.py`](../../tests/test_per_chapter_loop_installed_bdd.py):

1. Add `test_installed_advance_refused_carries_marks`, mirroring the existing
   guard exactly: read
   `getattr(test_installed_advance_phase_refused, "pytestmark", ())`, collect the
   mark names, and assert the set `>= _REQUIRED_MARKS` (the already-defined
   `frozenset({"slow", "timeout", "skipif"})`). This wheel-free guard fails if a
   future edit drops any mark, preventing the slow wheel build from running on a
   non-POSIX leg or under the 30s global timeout (Risk 1).

This guard introduces **no failing test** at any point: the marks are present
from WI-1, so the guard is green the moment it lands, and it is wheel-free
(runs on every platform).

Tests added/updated by WI-2: one new wheel-free guard test. No production code.

Validation: `make all`. Expect the guard to pass; it runs on every platform
(no wheel build). Optionally demonstrate red by transiently dropping a mark from
the bound function and confirming the guard fails, then revert. Commit only after
`make all` is green.

### WI-3 — Make the installed crossed-gate coverage explicit in the developers' guide

Implements: design §9 ("carried knowingly rather than silently"); audit-6.2.2
Finding 7 (the developers' guide prose must say which decisions the installed
re-drive carries and why the rest are bounded); roadmap 6.2.9 success clause
(both decisions proven, or the bound named).

Docs to read first: the developers' guide "per-chapter deterministic-loop
scenario" section (lines ~125-168), specifically the sentence at lines 151-153
stating the installed re-drive carries "the clean pass and the stale-compile
catch"; design §4.5 (crossed gate), §9.

Skills to load: `en-gb-oxendict`; `python-router` only if cross-checking step
names.

Edits in
[`docs/developers-guide.md`](../../docs/developers-guide.md), the
"per-chapter deterministic-loop scenario" section:

1. Update the sentence that currently says the installed re-drive carries "the
   clean pass and the stale-compile catch" to state the full installed coverage
   accurately: the clean pass, the stale-compile catch, the **crossed knitting
   gate** (folded into the clean pass via the installed `wordcount`
   gates-crossed assertion, mirroring the in-process clean pass), and the
   **refused out-of-order `advance-phase`** (exit 3, `state.toml` byte-for-byte
   intact, no traceback). Cite roadmap 6.2.9 and design §3.2/§4.1/§4.5.

2. Ensure the prose makes clear the crossed gate is proven *as part of* the clean
   pass (not a separate scenario) so a reader is not led to expect a standalone
   crossed-gate installed scenario.

Tests added/updated by WI-3: none (documentation). Markdown/prose only.

Validation: `make markdownlint` and `make nixie` (markdown changed), then
`make all`. Expect all to pass. Commit only after the gates are green.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-9`.

1. Confirm the branch and clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-9 branch --show-current
   ```

   Expect `roadmap-6-2-9`.

2. WI-1: add the feature scenario, the `_run_installed_argv` helper (with
   `_run_installed` delegating), the `state_before` field, the three steps, and
   the binder function. First demonstrate the behaviour pin by transiently
   pointing the new `Given` at a coherent tree and running:

   ```bash
   uv run pytest tests/test_per_chapter_loop_installed_bdd.py \
     -k advance_phase_refused -m slow -p no:cacheprovider
   ```

   Expect the exit-3 assertion to **fail** (the coherent tree advances, exiting
   0). Revert the `Given` to `completed-prefix-gap` and re-run; expect it to
   **pass**. Record both transcripts here. Then run the full installed binder to
   confirm one wheel build serves both scenarios:

   ```bash
   uv run pytest tests/test_per_chapter_loop_installed_bdd.py -m slow
   ```

   Expect both installed scenarios (and, after WI-2, both mark guards) to pass.

3. WI-1 gate (note: no `-m 'not slow'` — the gate runs the slow scenario
   inline, so it must already be green):

   ```bash
   make all
   ```

   Expect `build`, `check-fmt`, `lint`, `typecheck`, and `test` all green, with
   the new installed scenario executed and passing. Commit WI-1.

4. WI-2: add the new guard; confirm it runs wheel-free on any platform:

   ```bash
   uv run pytest tests/test_per_chapter_loop_installed_bdd.py \
     -k carries_marks
   ```

   Expect both `*_carries_marks` guards to pass. Then `make all`; commit WI-2.

5. WI-3: edit the developers' guide, then:

   ```bash
   make markdownlint
   make nixie
   make all
   ```

   Expect all to pass with no findings on the changed file. Commit WI-3.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: the new installed scenario
  `the installed loop refuses an out-of-order advance-phase` passes on a POSIX
  host under one module-scoped wheel build; it exits 3, leaves `state.toml`
  byte-for-byte intact, and emits no traceback. The new
  `test_installed_advance_refused_carries_marks` guard passes on every platform.
  The existing installed scenario and the in-process scenarios are unchanged and
  still pass.
- Behaviour pin: the new `Then` exit-3 assertion fails when (transiently) pointed
  at a coherent tree and passes against `completed-prefix-gap` — demonstrated in
  `Concrete steps` without committing a failing state.
- Lint/typecheck/format: `make all` passes (`check-fmt`, `lint`, `typecheck`,
  `test`). `make markdownlint` and `make nixie` pass for the developers' guide
  change.
- Behaviour observable by a human: on a POSIX host, running the installed loop
  binder shows the installed `novel-state advance-phase` console-script refusing
  the out-of-order tree with exit 3 over a real built wheel.

Quality method (how we check):

- Run `make all` after every work item; run `make markdownlint` and `make nixie`
  after the doc work item. Commit each work item separately, **each gated on a
  green `make all`** — no work item may leave a failing or undefined-step test
  (the gate runs slow tests inline; S3).

Testing-rule conformance (AGENTS.md "Python verification and testing"):

- The change is a **behavioural** (`pytest-bdd`) and **end-to-end** addition —
  exactly the externally observable, command-line, packaging-boundary behaviour
  AGENTS.md requires e2e coverage for. No new snapshot is warranted (the envelope
  contract is already snapshotted per command elsewhere; this scenario asserts
  the exit code, disk-intactness, and no-traceback semantics directly, which
  AGENTS.md says to prefer over snapshot-only coverage). No property test is
  warranted: there is no new invariant over a range of inputs — the refusal is a
  single fixed corpus tree (`completed-prefix-gap`). Hypothesis/CrossHair/mutmut
  are not engaged: there is no new production logic to mutate or symbolically
  explore; the behaviour under test is already covered in-process and the new
  work crosses the *packaging* boundary, where e2e is the correct adversary.
  Unit tests are not applicable (no production logic changes).

## Idempotence and recovery

All steps are re-runnable. The wheel build and venv install happen in throwaway
`tmp_path_factory` directories the fixture owns; re-running rebuilds cleanly. No
step mutates tracked source beyond the four edited files (feature, installed
steps, binder, developers' guide) plus this plan. If a work item's `make all`
fails, fix forward or `git restore` the edited test/doc files and retry; nothing
is destructive. The installed scenario itself builds each `working/` tree under
a per-test `run_dir`, so cases stay independent and re-runs do not leak state.

## Artifacts and notes

Transcripts captured during implementation:

- WI-1 behaviour pin (red): pointing the new `Given` transiently at the coherent
  `wc.COHERENT_BASELINE` tree (in-order prefix complete) made the installed
  `advance-phase` exit 0, so the exit-3 assertion failed as designed:
  `AssertionError: installed advance-phase exited 0, expected 3`
  (`per_chapter_loop_installed_steps.py` Then step). Reverted to
  `INCOHERENT_VARIANTS["completed-prefix-gap"][0]`.
- WI-1 green: `uv run pytest tests/test_per_chapter_loop_installed_bdd.py -m slow`
  reported `2 passed, 1 deselected` under one module-scoped wheel build (both
  installed scenarios share the build).
- WI-1 gate: `make all` green — `941 passed, 1 skipped`, with the slow scenario
  executed inline (no slow deselection; S3). A transient `ruff format` reflow of
  the `state_before` assignment was applied before the gate passed.
- WI-2: both `*_carries_marks` guards passing wheel-free (see WI-2 progress).

## Interfaces and dependencies

All relied-upon APIs are present in the locked dependency set; **no new
dependency is introduced**.

cuprum (locked **0.1.0**, `uv.lock` lines 113-118). Verified against
`/data/leynos/Projects/cuprum/cuprum/sh.py`:

- `cuprum.program.Program(str)` — the program value; cuprum 0.1.0 allowlists any
  `Program` string including an absolute path (verified by the existing
  `single_program_catalogue` fixture and `tests/test_conftest_helpers.py`).
- `cuprum.ProgramCatalogue(projects=(ProjectSettings(...),))` — the one-program
  allowlist built by `single_program_catalogue` (`tests/conftest.py:261-272`).
- `cuprum.sh.make(program, *, catalogue) -> builder` (`sh.py:528`): looks up
  `program` in the catalogue (raising `UnknownProgramError` otherwise) and
  returns a builder that coerces argv into a `SafeCmd`.
- `SafeCmd.run_sync(*, capture=True, context=ExecutionContext(cwd=...)) ->
  CommandResult` (`sh.py:441`). `ExecutionContext` carries `cwd` (`sh.py:169`).
  `CommandResult` exposes `exit_code: int` (`sh.py:115`), `stdout: str | None`,
  `stderr: str | None`. These are exactly the surfaces `_run_installed` already
  uses; `_run_installed_argv` calls the **same** `sh.make(prog,
  catalogue=catalogue)(*argv).run_sync(context=ExecutionContext(cwd=run_dir),
  capture=True)` chain with `argv` parameterised, so **no new cuprum API is
  introduced**.

If a work item appears to need a cuprum capability beyond the above (it should
not), stop and escalate per Tolerances rather than inventing a workaround.

The new helper (the only genuinely new code, all in `tests/steps/`):

```python
def _run_installed_argv(
    installed: _Installed,
    script_name: str,
    argv: tuple[str, ...],
    *,
    capture_key: str,
) -> tuple[int, dict[str, object], str]:
    """Run ``script_name`` with ``argv`` and store the capture under ``capture_key``."""
```

It centralises the capture write (`installed.captures[capture_key] = …`), so the
`When` steps call it for its side effect; `_run_installed` delegates to it
preserving the existing `(exit_code, envelope, stderr)` return.

pytest-bdd (locked **8.1.0**, `uv.lock` lines 585-587). A function decorated with
`@scenario(...)` "behaves like a normal test function", so stacked
`@pytest.mark.*` decorators attach to the produced test item exactly as on a
plain pytest function — the mechanism the existing installed binder and
`tests/test_console_scripts_e2e.py` / `tests/test_recount_e2e.py` rely on
(documented in the existing binder's module docstring, citing pytest-bdd 8.1.0).
The new scenario follows the same per-function `@scenario` + stacked-marks shape.

pytest-timeout (locked **2.4.0**, `uv.lock` lines 603-605). Verified against the
official PyPI documentation
(<https://pypi.org/project/pytest-timeout/>, 2.4.0): the timeout is resolved
"from low to high priority" as (1) ini `timeout`, (2) `PYTEST_TIMEOUT` env, (3)
`--timeout` CLI, (4) the per-item `@pytest.mark.timeout(...)` marker; the docs
state the marker "specif[ies] timeouts on a per-item basis" and "If combined with
the --timeout flag this will override the timeout for this individual test." The
project's ini sets `timeout = 30` (`pyproject.toml:326`); the new scenario's
`@pytest.mark.timeout(180)` therefore supersedes it for that item only — the same
guarantee the existing installed scenario relies on, now re-asserted by the new
mark-retention guard. pytest-xdist (`-n auto`) does not change per-item timeout
resolution: the timeout marker is applied within each worker's runtest protocol,
independent of distribution.

Gate behaviour (verified against the repo, correcting the round-1 false claim):
`make test` (`Makefile:116`) is `… pytest -v -n $(PYTEST_XDIST_WORKERS)` with
**no** `-m 'not slow'`; `pyproject.toml:326-328` defines `timeout = 30`,
`testpaths = ["tests"]`, `markers = ["slow: …"]` and **no** `addopts`;
`tests/conftest.py` defines no `pytest_collection_modifyitems` deselection; and
`.github/workflows/ci.yml:10` runs on `ubuntu-latest` invoking `make test`.
There is therefore **no slow deselection anywhere**; the `@slow` POSIX scenario
is collected and executed by `make all` and CI, which is why WI-1 must be green
in one commit (S3; Constraints).

Corpus and fixtures (in-repo, reused as-is):

- `working_corpus.INCOHERENT_VARIANTS["completed-prefix-gap"]` — public export
  (`tests/working_corpus/__init__.py`). Returns `(WorkingTreeSpec,
  invariant_name)`; the spec is a `drafting` tree with `phase.completed =
  ("premise", "characters")`. WI-1 passes the spec (`[0]`) to `_build_installed`.
- `working_corpus.build_working_tree(spec, dest)` — materialises the tree (called
  inside `_build_installed`).
- `installed_novel_state` (module-scoped) and `single_program_catalogue`
  fixtures — reused unchanged.
- Existing installed-step helpers `_run_installed` (now delegating),
  `_assert_no_traceback`, `_build_installed`, and the `_Installed` dataclass
  (extended with `state_before`) — reused.

End-state signatures (informal):

- New helper: `_run_installed_argv(installed, script_name, argv, *,
  capture_key) -> tuple[int, dict[str, object], str]`.
- New given (installed steps):
  `installed_out_of_order_tree(installed_novel_state, tmp_path,
  single_program_catalogue) -> _Installed` with `target_fixture="installed"`,
  setting `state_before`.
- New when: `run_installed_advance_phase(installed: _Installed) -> None`
  (calls `_run_installed_argv(installed, "novel-state", ("advance-phase",),
  capture_key="advance-phase")`).
- New then: `installed_advance_phase_refused(installed: _Installed) -> None`.
- New binder function: `test_installed_advance_phase_refused() -> None` with the
  three stacked marks; guard `test_installed_advance_refused_carries_marks() ->
  None`.

## Revision note

Revision 2 (2026-06-25) — resolves the round-1 design-review blocking points.

- What changed: the round-1 red→green-across-two-commits split (old WI-1 added
  the scenario+binder as a committed *red* state; old WI-2 wired the steps) is
  abandoned and merged into a single green-in-one-commit **WI-1** that lands the
  feature, the `_run_installed_argv` helper, the binder, and all three steps
  together. The plan now has three work items (WI-1 implement; WI-2 mark guard;
  WI-3 developers' guide). The false "`make all` may deselect the slow item under
  the default marker config" hedge is removed and replaced with the verified S3
  finding that there is **no** slow deselection (`Makefile:116`,
  `pyproject.toml:326-328`, `conftest.py`, `ci.yml:10`). The
  `_run_installed_argv(installed, script_name, argv, *, capture_key)` helper is
  now pinned exactly — signature, the `installed.captures["advance-phase"]`
  capture key it writes, and the `_run_installed` delegation that keeps the
  clean-pass loop byte-identical and the module under the 400-line cap.
- Why it changed: the design reviewer established that (1) the gate runs slow
  tests inline so a committed red state fails `make all`/CI and violates AGENTS.md
  lines 100/108, and (2) `_run_installed` conflates script name, argv key, and
  capture key, so the refused advance needs a separately-specified helper rather
  than a mid-implementation TODO.
- How it affects remaining work: WI-1 is now a single atomic, gate-passable unit;
  WI-2 and WI-3 each add only green-from-landing tests/docs. The behavioural
  red→green discipline is preserved *within* WI-1 by the transient coherent-tree
  demonstration, not by a committed failing state.

Revision 1 (2026-06-25). Initial draft: established the work-item decomposition,
recorded the S1 discovery that the crossed gate is already installed-proven, and
pinned the locked external surfaces.

## Addenda

Post-merge remediation items filed against this completed task. Each is a
lightweight addendum pass: no plan or design-review cycle, just the change, the
gates, and a merge. The roadmap carries the matching nested sub-task.

- [x] **6.2.9.1 — Split `tests/steps/per_chapter_loop_installed_steps.py` before
  it breaches the 400-line module cap** (from review:6.2.9; severity: low). At 383
  of 400 lines the next installed arm risks breaching the AGENTS.md module-size
  gate mid-task. Extract the run/build helpers (the `_run_installed_argv`/
  `_run_installed`/`_build_installed` seam) from the step definitions into a
  small support module so future installed work stays within bounds.
- [x] **6.2.9.2 — Correct the execplan framing of where the refused-advance
  exit-3 is stamped** (from review:6.2.9; severity: low). The framing above
  (Context and orientation; the WI-1 prose) describes the refused-advance exit-3
  as runner-stamped "before the command body runs (the global-flag pre-parse)".
  For the `completed-prefix-gap` case the exit-3 actually originates from a domain
  `StateInputError` raised inside `advance_phase` (`_refuse_if_incoherent(prior)`)
  and is translated by the runner. Reword the prose to distinguish the two
  distinct exit-3 paths — pre-parse global-flag (usage/`--human`) errors versus
  in-body domain refusals — so a later reader does not draw the wrong conclusion
  about the contract surface.
- [x] **6.2.9.3 — Enforce the installed step helper's capture-key single-write
  contract structurally** (from review:6.2.9; severity: low).
  `_run_installed_argv` is a command/query hybrid: it writes
  `installed.captures[capture_key]` and returns the tuple, with the single-write
  contract guarded only by the module docstring. A future maintainer copying a
  `When` step could re-add `captures[...] =` and double-write silently. Add a
  small assertion that `capture_key` is not already present in
  `installed.captures` for this run, so the contract is enforced rather than only
  documented.
- [x] **6.2.9.4 — Parametrise the two duplicated installed-scenario mark-guard
  tests** (from audit:6.2.9 Finding 3; severity: low). The two `*_carries_marks`
  tests in `tests/test_per_chapter_loop_installed_bdd.py` are near-identical
  clones differing only in the bound function and message noun, and the
  developers' guide instructs contributors to add a guard per installed scenario,
  so the clone pattern grows one copy per future scenario. Collapse them to one
  `@pytest.mark.parametrize`d test over `(function, label)` pairs so adding a
  scenario is a one-line append, keeping each scenario named in the test id.
- [x] **6.2.9.5 — Document the installed crossed-gate folding and step-harness
  conventions adjacent to the code** (from audit:6.2.9 Findings 2, 4, 5; severity:
  low). Three consistency notes share a root cause — rationale that lives only in
  the developers' guide, not next to the code: (1) add a one-line feature-header
  comment in `per_chapter_loop_installed.feature` recording that the installed
  feature folds the crossed-gate into the clean-pass scenario rather than a
  standalone scenario (asymmetric with the in-process feature), and (2) sanction
  the `_run_installed_argv` command/query hybrid as a deliberate test-helper
  exception in the developers' guide's test-helper conventions. The audit's
  third, conditional note — optionally extracting a shared capture-contract
  helper "if a third loop boundary appears" — is deferred to step 7.23 (shared
  command-driving test scaffolding), whose hypothesis it serves, and is not
  folded here.
