# Migrate the e2e and contract suites to invoke `novel <sub>`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (round 3 — design-review B1/B2/B3 resolved)

## Purpose / big picture

Roadmap task 1.2.12 stood up the single `novel` multiplexer
(`novel state …`, `novel done`, `novel compile`, `novel desloppify`,
`novel wordcount`) alongside the five legacy console-scripts
(`novel-state`, `novel-done`, `novel-compile`, `desloppify`, `wordcount`).
Both surfaces are currently installed and exercised. This task re-points the
**installed-binary end-to-end (e2e)** test suites — the ones that build a wheel,
install it into a throwaway virtual environment, and run a console-script by
absolute path — so they invoke the new `novel <sub>` surface instead of the
legacy per-command scripts. The migration is **additive**: the five legacy
`[project.scripts]` entries and the `COMMAND_NAMES` /
`COMMAND_ENTRY_POINTS` / `SUBCOMMAND_NAMES` registry symbols stay exactly as
they are (they are removed later, in roadmap task 1.2.15), so the legacy
oracle the parity tests need is untouched and this change is low-risk and
independently landable.

After this change, a reader can observe success by:

1. Running `make all` (which runs `make test`, building the wheel once per
   installed-e2e module and running the installed binary). Every installed e2e
   now resolves and runs the single `novel` console-script with a subcommand
   argv (for example `novel state check`, `novel desloppify --pack …`), and
   each asserts the envelope `command` field carries the **spaced** name
   (`"novel state"`, `"novel desloppify"`, …) rather than the legacy hyphenated
   name (`"novel-state"`, `"desloppify"`, …).
2. Confirming the legacy registry is untouched: `tests/test_pyproject_scripts.py`
   and `tests/test_command_names_registry.py` still pass unchanged, proving the
   six `[project.scripts]` entries (legacy five plus `novel`) and the
   `COMMAND_NAMES` tuple are intact.

The user-visible behaviour enabled: the installed-binary safety net now proves
the *shipping* command surface (the single `novel` multiplexer that 1.2.15
makes the sole entry point), so removing the legacy scripts in 1.2.15 cannot
silently break the real install-and-run path.

A note on the roadmap's literal "every e2e and contract test invokes
`novel <sub>`" success line. The same roadmap entry qualifies it: "This is an
ADDITIVE migration: the five legacy `[project.scripts]` entries and the
`COMMAND_NAMES`/`COMMAND_ENTRY_POINTS` symbols stay in place (removed in 1.2.15),
**so the legacy-vs-multiplexer parity tests still have their oracle**". The
in-process legacy-stub and `RunContext`-driven suites (and their snapshots) *are*
that oracle, so they keep stamping legacy names until 1.2.15; migrating them now
would destroy the parity oracle one task early. This plan therefore reads the
success line as scoped to the **installed-binary** e2e suites plus the installed
BDD step module (the surfaces that run a real console-script), and treats the
contract/command-name registry suites (`test_command_names_registry.py`,
`test_pyproject_scripts.py`) as verify-unchanged gates that already assert the
additive 1.2.12 registry. See Decision Log D1/D5.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Additive only.** Do not delete, rename, or re-target any
  `[project.scripts]` entry. Do not delete or weaken any symbol in
  `novel_ralph_skill/commands/names.py` (`STUB_MODULE`, `NOVEL_MODULE`,
  `COMMAND_ENTRY_POINTS`, `COMMAND_NAMES`, `MULTIPLEXER_NAME`,
  `SUBCOMMAND_NAMES`, `ENVELOPE_COMMAND_NAMES`, `project_scripts_table`). These
  belong to task 1.2.15.
- **No production-code change.** The dispatcher
  (`novel_ralph_skill/commands/novel.py`), the runner
  (`novel_ralph_skill/contract/runner.py`), and every command body are frozen.
  This task touches `tests/` only. If a test cannot pass without a production
  change, stop and escalate (the production change is out of scope; it belongs
  to whichever task owns that module).
- **Leave the in-process legacy-stub suites alone.** The in-process tests that
  drive the *legacy* entry points by monkeypatching `sys.argv` to
  `[_COMMAND, …]` against `novel_ralph_skill.commands.stub`, or that build a
  `RunContext(command="novel-state", …)` directly, are the legacy oracle for
  the parity tests and must keep stamping the legacy names until 1.2.15. They
  are out of scope for this task. The in-scope set is exactly the
  **installed-binary** e2e tests (those that build a wheel and run a
  console-script by absolute path) enumerated in *Context and orientation*.
- **Do not modify any `.ambr` snapshot.** Every syrupy snapshot under
  `tests/__snapshots__/` that carries a legacy `command` name belongs to an
  in-process suite (`test_contract_envelope*`, `test_compile*_snapshots`,
  `test_novel_state_mutator_snapshots`, `test_command_surface_matrix`, …) that
  stays on the legacy names until 1.2.15. The installed e2e tests assert
  envelope fields directly in Python and use no snapshots, so no snapshot
  changes are expected. If a snapshot would change, you have touched an
  out-of-scope suite — stop and revert.
- **Locked external versions.** cuprum `0.1.0`, Cyclopts `4.18.0`,
  pytest-timeout `2.4.0`, pytest-xdist `3.8.0` (pinned in `uv.lock`). Do not
  introduce, upgrade, or pin a new dependency.
- **ADR-006 POSIX policy.** Installed-binary e2e tests are POSIX-only; keep the
  existing `pytestmark` / `@pytest.mark.skipif(os.name != "posix", …)` guards.
- **Quality gates (AGENTS.md lines 63-98).** Every commit passes `make all`
  (format, lint, interrogate docstring coverage, Pylint, `ty` typecheck,
  `pytest -n auto`, audit). Any commit that adds or edits a Markdown file also
  passes `make markdownlint` and `make nixie`.
- **en-GB Oxford spelling** (`-ize`, `-yse`, `-our`) in all prose, comments,
  docstrings, and commit messages.

## Tolerances (exception triggers)

- **Scope:** if the migration requires editing more than the in-scope test
  modules enumerated in *Context and orientation* (one fixture module, the
  installed-e2e test modules, the installed BDD step module, and the one new
  in-process registry-pin module `tests/test_installed_command_names.py` added by
  WI1), or requires touching any file under `novel_ralph_skill/`, stop and
  escalate.
- **Production change:** if any installed e2e cannot be made green without a
  change to `novel.py`, `runner.py`, `names.py`, or a command body, stop and
  escalate.
- **Snapshot churn:** if any `tests/__snapshots__/*.ambr` file changes, stop
  and revert — it means an out-of-scope suite was touched.
- **Iterations:** if `make test` still fails for the same module after 3 fix
  attempts, stop and escalate with the failing transcript.
- **Ambiguity:** if a test asserts the envelope `command` against a value that
  is neither a clean legacy-to-spaced rename nor explained by the dispatcher's
  name derivation, stop and present the options.

## Risks

- Risk: the **one** installed module that asserts the envelope `command`
  field — `test_console_scripts_error_arms_e2e.py` (lines 194, 234-236) — is
  missed, so it still expects a legacy name (`"novel-state"`) while invoking the
  spaced surface, and fails confusingly.
  Severity: medium. Likelihood: low.
  Mitigation: an audit of the in-scope modules (recorded in WI3/WI4) establishes
  that this is the *only* installed module carrying a `command`-field assertion;
  the four `installed_novel_state` state consumers carry **none** (they assert
  only `.exit_code`, `env["ok"]`, and `env["result"][…]`; see Decision Log D7).
  WI4 flips that one module's `_COMMAND` constant to the spaced name; the WI8
  grep gate then confirms no migrated installed-e2e module still references a
  legacy command literal in an *invocation* argv or a `command`-field assertion.
  Rather than a shared test-module mapping (forbidden as a cross-module value
  import; see WI1 and Decision Log D8), each consumer derives the spaced name and
  the mount verb **inline from production code** — `SUBCOMMAND_NAMES` (and, where
  it needs the legacy->spaced pairing, `zip(COMMAND_NAMES, SUBCOMMAND_NAMES)`) in
  `novel_ralph_skill.commands.names` — so no assertion re-spells a literal and no
  test imports a value from another test module.
- Risk: the `novel-state`-specific subcommand routing (`novel-state check`
  vs `novel state check`) is forgotten when rewriting the `state` arms, sending
  a bare `novel state` (which prints help and exits 0) instead of
  `novel state check` (which reaches the real exit-3 path).
  Severity: medium. Likelihood: low.
  Mitigation: the existing `_REAL_PATH_ARGV` / `_READ_SUBCOMMAND` constants
  already encode this; WI3/WI4 prepend the `state` mount verb to those argv
  tuples rather than discarding them. Verified in-process (Decision Log D2).
- Risk: the `installed_novel_state` fixture is renamed/retargeted in a way that
  breaks the five consumer modules that import it by name.
  Severity: medium. Likelihood: low.
  Mitigation: WI2 keeps the fixture *name* (`installed_novel_state`) and its
  return *type* (`Path`) stable, changing only the resolved script basename
  from `novel-state` to `novel`; consumers receive the `novel` path by the same
  parameter name. The five consumers are migrated in WI3 in the same series.
- Risk: the wheel build/install machinery differs subtly between the
  `installed_novel_state` fixture and the per-module `_build_and_install_*`
  helpers (`desloppify`, `novel-done`, `wordcount`), so a half-migration leaves
  one module installing the wrong script name.
  Severity: low. Likelihood: low.
  Mitigation: each per-module helper resolves its script by basename
  (`scripts_dir / "desloppify"`); WI5/WI6 change exactly that basename to
  `"novel"` and prepend the mount verb to the run argv. The script-exists
  assertion (`assert script_path.exists()`) catches a wrong basename
  immediately.
- Risk: a Markdown doc edit (none currently planned) trips `make markdownlint`
  or `make nixie`. Severity: low. Likelihood: low.
  Mitigation: this task edits no Markdown; the design/skill prose sweep is the
  separate task 1.2.14. If a doc note becomes necessary, run both gates.

## Progress

- [x] WI1: Establish the registry-sourced legacy-name -> spaced-name / mount-verb
  derivation for the installed e2e suites (a production import, not a shared
  test-module value). Done: added `tests/test_installed_command_names.py` (3
  tests, in-process, no slow/timeout marks) importing only production `names`.
  Ruff flagged a literal `str.split` (split-static-string); reworked the mount-verb
  assertion to derive from `SUBCOMMAND_NAMES` rather than a string literal.
- [x] WI2: Re-point the `installed_novel_state` fixture to the `novel` script.
  Done in the WI2+WI3 commit (Decision Log D6). Flipped the resolved basename to
  `"novel"`, updated the not-found message and the module/fixture docstrings.
- [x] WI3: Migrate the `installed_novel_state` consumer modules to
  `novel state …`. Done: argv mount-verb prefix only across
  `test_novel_state_check.py`, `test_recount_e2e.py`, `test_reconcile_e2e.py`,
  `test_set_chapters_e2e.py`, `test_drafting_bijection_e2e.py`. No `command`
  assertion edited; line 143 of `test_novel_state_check.py` left untouched.
- [x] WI4: Migrate `test_console_scripts_e2e.py` and
  `test_console_scripts_error_arms_e2e.py`. **Deviation (Decision Log D9):**
  `test_console_scripts_error_arms_e2e.py` also consumes the shared
  `installed_novel_state` fixture, so flipping the fixture basename in WI2 breaks
  it too. To keep every commit gate-passable (the D6 atomicity rule), the
  error-arm module's migration was folded into the WI2+WI3 commit. The remaining
  WI4 module, `test_console_scripts_e2e.py` (its own builder, not the fixture),
  migrated here as a separate commit: the loop now resolves `scripts_dir /
  "novel"` once and iterates `SUBCOMMAND_NAMES`, deriving the mount verb and the
  extra argv (`{"state": ("check",), "compile": ("--check",)}`); both module
  guards re-anchored on `SUBCOMMAND_NAMES`; the unused `COMMAND_NAMES` import
  dropped.
- [x] WI5: Migrate the `desloppify` installed e2e modules
  (`test_desloppify_e2e.py`, `test_ai_isms_e2e.py`). Done: renamed the
  build/install helper to `_build_and_install_novel`, flipped the basename to
  `novel`, and prepended the `desloppify` mount verb to every run argv. No
  `command` assertion existed in either module. Two docstrings re-wrapped to keep
  under the 88-col line cap.
- [x] WI6: Migrate `test_novel_done_e2e.py` and `test_wordcount_e2e.py`. Done:
  renamed both build helpers to `_build_and_install_novel`, flipped the basename,
  prepended the `done`/`wordcount` mount verbs. No `command` assertions. Prose
  updated to the spaced surface; the one intentional legacy reference (the
  helper-docstring note that the legacy script still ships) retained.
- [x] WI7: Migrate the installed per-chapter-loop BDD
  (`tests/steps/per_chapter_loop_installed_steps.py`). Done: `_run_installed`
  now always resolves the single `novel` script; `_LOOP_ARGV` values carry the
  mount-verb argv while the keys stay the legacy operation labels (capture keys,
  unchanged); the `advance-phase` `When` step drives `("state", "advance-phase")`
  against `novel`. No `Then`-step literal touched; the feature file untouched.
- [x] WI8: Add the closing grep gate and full-suite validation. Done: the grep
  over the in-scope modules returns only the three benign categories — the
  `_COMMAND = "novel-state"` in-process oracle constants, the `_LOOP_ARGV`
  capture keys, and the mount-verb literals (`"wordcount"`, `"desloppify"`) that
  coincide with legacy names but are correct spaced-surface verbs. No legacy
  literal appears in a `sh.make(...)(...)` invocation as a *script name* nor in
  any `envelope["command"] ==` comparison. `make all` green at HEAD.

## Surprises & discoveries

- Observation: the local working checkout at `/data/leynos/Projects/cuprum` is a
  **newer, divergent** source than the locked `cuprum 0.1.0` wheel this project
  installs. Its `SafeCmd.run_sync` signature
  (`output: RunOutputOptions | None`) differs from the installed wheel's.
  Evidence: `uv run python -c "from cuprum import sh; import inspect;
  print(inspect.signature(sh.SafeCmd.run_sync))"` against the project venv
  prints `(self, *, capture: bool = True, echo: bool = False,
  context: ExecutionContext | None = None)`, matching the existing tests'
  `.run_sync(context=…, capture=True)` calls; the local checkout's `sh.py`
  does not.
  Impact: every cuprum claim in this plan is pinned against the **installed
  wheel** surface (verified in the project venv), never the local checkout. Do
  not consult `/data/leynos/Projects/cuprum/cuprum/sh.py` as the API of record.

## Decision log

- Decision: scope is exactly the installed-binary e2e suites plus the installed
  BDD step module; the in-process legacy-stub and `RunContext`-driven suites are
  out of scope.
  Rationale: the roadmap 1.2.13 entry says "Re-point the installed-binary e2e
  tests and the contract/command-name suites" and is "ADDITIVE … the five
  legacy `[project.scripts]` entries and the `COMMAND_NAMES` /
  `COMMAND_ENTRY_POINTS` symbols stay in place … so the legacy-vs-multiplexer
  parity tests still have their oracle". The in-process legacy-stub tests *are*
  that oracle; migrating them would destroy it before 1.2.15. The
  "contract/command-name suites" (`test_command_names_registry.py`,
  `test_pyproject_scripts.py`) already assert the additive registry that 1.2.12
  produced and therefore need **no change** here — they are listed as
  "verify-unchanged" gates, not migration targets (Decision Log D5).
  Date/Author: 2026-06-25, planning agent.
- Decision: D2 — `novel state check` (not bare `novel state`) is the routing
  that reaches the real exit-3 state-error path; `novel desloppify`,
  `novel wordcount`, `novel compile --check`, and `novel done` reach it bare.
  Rationale: verified in-process against the locked dispatcher:
  `novel._command_name_for(["state","check"])` returns `"novel state"` and
  `run(build_multiplexer(), ["state","check"], …)` exits `3` under an empty
  cwd; the four leaf verbs exit `3` bare. `state` is a command-group sub-app, so
  a bare `novel state` prints help and exits 0 — the same reason the legacy
  `novel-state` suites carry `_REAL_PATH_ARGV = {"novel-state": ("check",)}`.
  Date/Author: 2026-06-25, planning agent.
- Decision: D3 — the migrated envelope `command` assertions expect the spaced
  name (`"novel state"`, `"novel desloppify"`, …).
  Rationale: the multiplexer entry point derives the name through
  `novel._command_name_for(residual)`, which maps the leading non-flag token to
  its `SUBCOMMAND_NAMES` entry; `run` stamps that into every envelope including
  the body-less exit-2/exit-3 arms (`novel.py` docstring, Decision Log D4 of
  1.2.12). Verified in-process: the resolved names are `"novel state"`,
  `"novel done"`, `"novel compile"`, `"novel desloppify"`, `"novel wordcount"`.
  Date/Author: 2026-06-25, planning agent.
- Decision: D4 — `novel` is run by absolute path through the existing one-program
  cuprum catalogue; only the program basename and the prepended subcommand argv
  change.
  Rationale: cuprum `0.1.0` `Program` is a `NewType[str]` (any string, including
  an absolute path, is a valid program); the `ProgramCatalogue` allowlist, not
  the `Program` type, is the execution gate; `sh.make(prog, catalogue=…)(*argv)`
  builds the argv and `run_sync(context=ExecutionContext(cwd=…), capture=True)`
  executes it. Verified in the project venv: an absolute-path `Program`
  (`/usr/bin/true`) registered in a one-`ProjectSettings` catalogue runs and
  returns `exit_code == 0`. So `Program(str(scripts_dir / "novel"))` with argv
  `("state", "check")` is a drop-in for the legacy `Program(str(scripts_dir /
  "novel-state"))` with argv `("check",)`.
  Date/Author: 2026-06-25, planning agent.
- Decision: D5 — `test_command_names_registry.py` and `test_pyproject_scripts.py`
  are not edited.
  Rationale: both already assert the additive 1.2.12 registry (six
  `[project.scripts]` entries; `COMMAND_NAMES` = the five; `SUBCOMMAND_NAMES` =
  the five spaced names). The migration changes no registry symbol, so these
  files must remain green untouched; they are validation gates, not targets.
  Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

Completed (2026-06-25, implementing agent). Every installed-binary e2e and the
installed per-chapter-loop BDD now invoke the single `novel` multiplexer with the
mount-verb argv; the one module that asserts the envelope `command`
(`test_console_scripts_error_arms_e2e.py`) asserts the spaced `"novel state"`. The
legacy registry and entry points are untouched: `test_pyproject_scripts.py` and
`test_command_names_registry.py` pass unchanged, and the in-process legacy-stub
and `RunContext` oracle suites keep stamping the legacy names for the 1.2.15
parity oracle. No `.ambr` snapshot changed; no file under `novel_ralph_skill/` was
touched. `make all` is green at HEAD (1127 passed, 1 skipped).

Deviation from the eight-WI structure: `test_console_scripts_error_arms_e2e.py`
(planned for WI4) shares the `installed_novel_state` fixture, so its migration was
folded into the WI2+WI3 commit to keep every commit gate-passable (Decision Log
D9). The remaining WI4 module, `test_console_scripts_e2e.py`, landed as its own
commit. WI8 was a developer-run grep check folded into the WI7 validation rather
than a committed test (the WI1 unit test already pins the registry mapping).

## Context and orientation

Read these before starting (paths relative to the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-13`):

- `docs/roadmap.md` lines 237-249 (task 1.2.13) and lines 202-236 (task 1.2.12,
  which built the multiplexer this task migrates onto).
- `docs/adr-007-command-surface-novel-multiplexer.md` (the single-`novel`
  surface; §"Migration plan" names the installed-binary e2e migration).
- `docs/adr-006-console-scripts-e2e-posix-policy.md` (installed-binary e2e is
  POSIX-only).
- `docs/adr-003-shared-interface-contract.md` §3.1 (the envelope and exit-code
  policy the `command` field belongs to).
- `docs/novel-ralph-harness-design.md` §4 (lines 265-280) — the deterministic
  spine is a single `novel` multiplexer; §4.1-4.5 name the five operations;
  §3.2 (the two command-agnostic diagnostic arms).
- `docs/developers-guide.md` §"Shared test scaffolding" (lines 20-72) — fixtures
  are consumed *by name*; the `installed_novel_state` fixture lives in
  `tests/installed_binary_fixtures.py` (registered via `pytest_plugins`); only a
  *type* may be imported, never a fixture/helper value; the 400-line module cap.
- `docs/scripting-standards.md` §"cuprum: typed command execution" — note that
  its illustrative `Catalogue.from_programs` / `sh.scoped` API is **not** the
  locked-0.1.0 surface; the installed wheel exposes
  `ProgramCatalogue(projects=…)` + `sh.make(prog, catalogue=…)`, which the
  existing tests already use and which this plan pins against.
- `AGENTS.md` lines 63-98 (quality gates) and lines 141-172 (Python and
  Markdown testing rules).

Key production modules (frozen; read-only context):

- `novel_ralph_skill/commands/names.py` — the registry. `SUBCOMMAND_NAMES` =
  `("novel state", "novel done", "novel compile", "novel desloppify",
  "novel wordcount")`. `MULTIPLEXER_NAME` = `"novel"`. `COMMAND_NAMES` = the
  legacy five. `project_scripts_table()` returns the six-entry table.
- `novel_ralph_skill/commands/novel.py` — the dispatcher. `build_multiplexer()`
  mounts `state`/`done`/`compile`/`desloppify`/`wordcount`; `main()` derives the
  spaced name via `_command_name_for(residual)` and drives `run`.

The verified mapping (legacy invocation -> migrated invocation; spaced envelope
`command`):

- `novel-state check` -> `novel state check`; command `"novel state"`.
- `novel-state recount` -> `novel state recount`; command `"novel state"`.
- `novel-state reconcile` -> `novel state reconcile`; command `"novel state"`.
- `novel-state set-chapters …` -> `novel state set-chapters …`;
  command `"novel state"`.
- `desloppify [--pack|--ledger …]` -> `novel desloppify [--pack|--ledger …]`;
  command `"novel desloppify"`.
- `novel-done` -> `novel done`; command `"novel done"`.
- `wordcount` -> `novel wordcount`; command `"novel wordcount"`.
- `novel-compile --check` -> `novel compile --check`; command `"novel compile"`.

In-scope test files (installed-binary e2e — they build a wheel and run a
console-script by absolute path; plus the one new in-process registry-pin module
WI1 adds):

0. `tests/test_installed_command_names.py` — **new** in WI1, a fast in-process
   unit module (no wheel, no `slow`/`timeout` marks) that pins the
   registry-sourced legacy-to-spaced / mount-verb derivation the installed e2e
   rely on. It imports only production `names`; it is in scope as the WI1 home.
1. `tests/installed_binary_fixtures.py` — the `installed_novel_state` fixture
   (currently returns the `novel-state` script path).
2. `tests/test_console_scripts_e2e.py` — loops over all five legacy script
   names.
3. `tests/test_console_scripts_error_arms_e2e.py` — asserts envelope
   `command == "novel-state"` for the usage/state arms over the installed
   binary; also asserts the `--human` header `command: novel-state`.
4. `tests/test_novel_state_check.py` — only the installed-binary test
   `test_installed_novel_state_check_exits_zero` (the rest of the module is the
   in-process legacy oracle and stays).
5. `tests/test_recount_e2e.py`, `tests/test_reconcile_e2e.py`,
   `tests/test_set_chapters_e2e.py`, `tests/test_drafting_bijection_e2e.py` —
   consumers of `installed_novel_state`. **Audited (Decision Log D7): none of
   these four modules asserts `envelope["command"]` on the installed run** — they
   assert only `result.exit_code`, `env["ok"]`, and `env["result"][…]`. Each
   carries a `_COMMAND = "novel-state"` module constant used *only* by the
   in-process `monkeypatch.setattr(sys, "argv", [_COMMAND, …])` legacy-oracle
   arms, which must stay `"novel-state"`. The installed migration for these four
   is therefore a pure argv mount-verb prepend with no `command`-assertion edit.
6. `tests/test_desloppify_e2e.py`, `tests/test_ai_isms_e2e.py` — build/install
   `desloppify`.
7. `tests/test_novel_done_e2e.py`, `tests/test_wordcount_e2e.py` —
   build/install `novel-done` / `wordcount`.
8. `tests/steps/per_chapter_loop_installed_steps.py` (driven by
   `tests/test_per_chapter_loop_installed_bdd.py`) — drives four installed
   scripts by basename.

Explicitly out of scope (do not edit): `test_compile_e2e.py` (in-process,
monkeypatches `sys.argv` against the legacy `novel_compile` stub),
`test_command_names_registry.py`, `test_pyproject_scripts.py`,
`test_venv_scripts_dir.py`, every `*_snapshots.py`, `test_contract_*`,
`test_command_surface_matrix.py`, and every in-process unit/BDD module that
builds a `RunContext(command="novel-…", …)` or monkeypatches `sys.argv` to a
legacy entry point.

## Plan of work

The work proceeds bottom-up: first the registry-sourced derivation convention and
its unit test (WI1), then the shared fixture (WI2), then each cluster of consumer
modules. Each work item is independently committable and `make all`-green because
the migration is a per-module argv-and-assertion rewrite with no cross-module
coupling: the only shared dependency is the WI2 fixture, and the spaced-name /
mount-verb derivation each consumer needs is taken **inline from production code**
(`novel_ralph_skill.commands.names`), not from a shared test-module value.

### Stage A — shared scaffolding (WI1, WI2)

Establish the registry-sourced derivation convention (WI1) and land the one
fixture every downstream module depends on (WI2), so each later module derives the
spaced name and mount verb from `names.SUBCOMMAND_NAMES`/`COMMAND_NAMES` by
reference rather than re-spelling a literal — and without any cross-module test
value import.

### Stage B — consumer migration (WI3-WI7)

Migrate each cluster of installed e2e modules to invoke `novel <sub>` and assert
the spaced `command`. Each cluster is one commit.

### Stage C — gate and validate (WI8)

Add the closing grep gate that proves no migrated installed-e2e module still
references a legacy command literal in an invocation or `command` assertion,
then run the full `make all` (which builds the wheels and runs the installed
binaries).

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-13`. Confirm the
branch first:

```bash
git branch --show
```

Expected:

```plaintext
roadmap-1-2-13
```

Run the in-scope subset fast during development with:

```bash
uv run pytest -q tests/test_console_scripts_e2e.py \
  tests/test_console_scripts_error_arms_e2e.py
```

The installed e2e tests are marked `slow` with a 180s per-test timeout; they
run under `make test` (`pytest -n auto`). Per pytest-timeout 2.4.0, the
`@pytest.mark.timeout(180)` marker is the highest-priority per-item override and
supersedes the 30s project default for that one test (verified against the
official docs; the marker priority is ini < env < CLI < per-item marker).

---

### WI1 — Establish the registry-sourced spaced-name / mount-verb derivation

Documentation to read: `docs/developers-guide.md` §"Shared test scaffolding"
(lines 57-75) — test modules consume scaffolding *by fixture name* and **never by
importing from another test module or from `conftest` itself**; only a
`TYPE_CHECKING`-guarded *type* may be imported, never a *value*. ADR-007 (the
spaced surface). `novel_ralph_skill/commands/names.py` (`SUBCOMMAND_NAMES`,
`COMMAND_NAMES`, both production constants).

Skills to load: `python-router` -> `python-testing` (fixture design, the
"shared by fixture name, never by value import" rule), `python-types-and-apis`
(the derivation helper's public shape, if WI1 chooses the conftest-fixture home).
Load `leta` for navigation and `sem` for history.

What to do: the installed e2e modules need two derivations, identically, in
several places — the spaced envelope name for a legacy command
(`"novel-state"` -> `"novel state"`) and the multiplexer mount verb to prepend
to the run argv (`"novel-state"` -> `"state"`). Both derive **purely from
production code**: `novel_ralph_skill.commands.names` exports `COMMAND_NAMES`
(the legacy five, in registration order) and `SUBCOMMAND_NAMES` (the five spaced
names, in the *same* surface order; verified — `names.py` lines 39-45, 68-74,
the i-th `COMMAND_NAMES` entry pairs with the i-th `SUBCOMMAND_NAMES` entry). So:

- legacy -> spaced is `dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))`;
- the mount verb for a spaced name `s` is `s.split(" ", 1)[1]` (`"novel state"`
  -> `"state"`, `"novel desloppify"` -> `"desloppify"`).

**Do not introduce any shared test-module value** (`SPACED_COMMAND`,
`MOUNT_VERB`, or similar module-level dict in `tests/installed_binary_fixtures.py`
or any plugin module). A `test_*.py` reading such a dict would have to `import`
it from another test/plugin module — the cross-module **value** import the
developers-guide forbids, and which `pytest_plugins` does **not** rescue (that
mechanism shares *fixtures* by name, not module-level constants). This is the
round-2 B3 defect; Decision Log D8 records the resolution.

Pick one of these two sanctioned homes for the derivation (planner mandates
option A unless a consumer genuinely needs the helper injected; both are
design-conformant):

- **Option A (default) — derive inline, per consumer, from the production
  import.** Each in-scope module already (or now) carries
  `from novel_ralph_skill.commands.names import COMMAND_NAMES, SUBCOMMAND_NAMES`
  (`test_console_scripts_e2e.py` already imports `COMMAND_NAMES`). Where a
  module needs the mount verb for its operation it derives it locally, e.g. a
  module-level `_MOUNT = SUBCOMMAND_NAMES[i].split(" ", 1)[1]` for its own
  operation index, or, in the all-operations loop (WI4), iterates
  `SUBCOMMAND_NAMES` directly. There is **zero** cross-module test import: the
  only import is from production `names`.
- **Option B (only if injection is wanted) — a `conftest.py` fixture.** Add to
  `tests/conftest.py` (the sanctioned shared home) a function-scoped fixture
  returning the legacy->spaced mapping
  (`dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))`), consumed **by
  parameter name** (e.g. `def test_…(spaced_command): …`). Never expose it as an
  importable module-level dict. This keeps the derivation in one place while
  obeying the "shared by fixture name" rule.

Whichever home, the derivation must be **pinned to the registry order** so a
future registry reordering fails loudly rather than silently mis-mapping. This
pin lives in the WI1 unit test (below), which asserts the positional pairing and
the surface order — there is no separate module-level guard to add, because there
is no shared module-level value to guard.

Tests this work item must add/update: add a focused, fast in-process unit test
(new module `tests/test_installed_command_names.py`, no wheel, no
`slow`/`timeout` marks) that pins the production-sourced derivation the consumers
rely on. It imports **only** `novel_ralph_skill.commands.names` (no test-module
import) and asserts:

1. `dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))["novel-state"] ==
   "novel state"`, and the four other pairings
   (`"novel-done"`->`"novel done"`, `"novel-compile"`->`"novel compile"`,
   `"desloppify"`->`"novel desloppify"`, `"wordcount"`->`"novel wordcount"`).
2. The mount verb derivation: `SUBCOMMAND_NAMES[0].split(" ", 1)[1] == "state"`
   and `"novel desloppify".split(" ", 1)[1] == "desloppify"`; more generally
   every spaced name has exactly two whitespace-separated tokens whose first is
   `"novel"` (so `split(" ", 1)[1]` is always the bare verb).
3. `COMMAND_NAMES` and `SUBCOMMAND_NAMES` are the **same length** and pair
   positionally (the registry-order coupling that makes `zip(strict=True)`
   safe) — this is the loud-failure guard for a future registry reordering.

Because the module is inside `PYTHON_TARGETS`, use explicit `raise AssertionError`
in any non-test helper per the file convention; the `test_*` functions
themselves use plain `assert` (pytest rewrites them).

Validation:

```bash
uv run pytest -q tests/test_installed_command_names.py
make all
```

Acceptance: the new unit test passes and imports only production `names`; no
shared test-module dict (`SPACED_COMMAND`/`MOUNT_VERB`) is introduced; `make all`
green. Commit:
"Pin installed-e2e legacy-to-spaced derivation against the registry".

---

### WI2 — Re-point the `installed_novel_state` fixture to the `novel` script

Documentation to read: `docs/developers-guide.md` lines 30-56 (the
`installed_novel_state` fixture contract — module-scoped, returns the installed
script path by name; consumers receive it by parameter name). ADR-006 (POSIX).
`docs/scripting-standards.md` §cuprum (the catalogue is the gate).

Skills to load: `python-router` -> `python-testing` (module-scoped fixtures,
`tmp_path_factory`). `leta` for navigation.

What to do: in `tests/installed_binary_fixtures.py`, the fixture currently
builds the wheel, installs it, then resolves and returns
`scripts_dir / "novel-state"`. Change the resolved basename to `"novel"` and
update the not-found message; the wheel still ships the single `novel` script
(per the six-entry `project_scripts_table()`). Keep the fixture *name*
(`installed_novel_state`) and return *type* (`Path`) unchanged so the five
consumers bind it by the same parameter name with no signature churn. Update the
fixture docstring and the module docstring to say it returns the installed
`novel` multiplexer script (note the legacy scripts still ship until 1.2.15, but
the e2e drives the `novel` surface).

Concrete edit (the resolution block):

```python
# tests/installed_binary_fixtures.py (installed_novel_state body)
script_path = scripts_dir / "novel"
if not script_path.exists():
    msg = f"novel not installed at {script_path}"
    raise AssertionError(msg)
return script_path
```

Tests this work item must update: the fixture has no direct unit test; its
correctness is proven by its consumers (WI3) building and running the binary.
Do not add a standalone slow test here — it would duplicate the WI3 coverage and
the wheel build.

Validation: this fixture is only exercised through its consumers, so validate
WI2 together with the first consumer module (it is acceptable to land WI2 and the
WI3 `state` migration in one commit if `make test` would otherwise fail on a
half-migrated consumer; see WI3). Run:

```bash
uv run pytest -q tests/test_novel_state_check.py::test_installed_novel_state_check_exits_zero
```

after WI3 lands. Commit WI2+WI3 together if needed for green; otherwise commit
WI2 as "Point installed_novel_state fixture at the novel script".

Note on commit atomicity: because the fixture's consumers all assert the legacy
behaviour, flipping the fixture basename **without** migrating the consumers'
argv would make them invoke `novel` with a bare `check` argv (wrong — `novel`
expects `state check`). Therefore **WI2 and WI3 must land in the same commit**
(or WI3 immediately after, with WI2 not committed alone). Recorded as Decision
Log D6 below.

---

### WI3 — Migrate the `installed_novel_state` consumer modules

Documentation to read: `docs/novel-ralph-harness-design.md` §4.1
(`novel state` subcommands). ADR-003 §3.1 (envelope `command`). The WI1 mapping.

Skills to load: `python-router` -> `python-testing`. `leta` for refs:
`leta refs installed_novel_state` to enumerate consumers.

**Audit result (verified against real source; Decision Log D7).** None of these
five modules asserts `envelope["command"]` on its *installed-binary* run. The
installed tests assert `result.exit_code`, `env["ok"]`, and `env["result"][…]`
(for `test_novel_state_check.py`: `test_installed_novel_state_check_exits_zero`
asserts only the exit code). The sole `command` assertion among the state
modules is `test_novel_state_check.py` line 143
(`assert envelope["command"] == _COMMAND`) inside `test_check_envelope_shape` —
and that is an **in-process** legacy-oracle test (`_run_check(["check"])` +
`_capture_envelope(capsys)`), not an installed run. It must stay
`"novel-state"`. Therefore **the only installed-run edit in WI3 is the argv
mount-verb prefix; there is no `command`-assertion to migrate in any of these
five modules.** Do **not** invent a `command` assertion, and do **not** touch
line 143 of `test_novel_state_check.py` (editing it destroys the parity oracle
one task early — pre-mortem failure path 2).

Per module, the exact installed-run argv edits:

- `tests/test_novel_state_check.py` — only
  `test_installed_novel_state_check_exits_zero`. Its installed run currently
  calls `sh.make(prog, catalogue=…)("check")`; change the builder argv to
  `("state", "check")`. It asserts only the exit code — leave that. Every
  in-process test above it (including line 143's `_COMMAND = "novel-state"`
  oracle and the `RunContext`/`monkeypatch` tests) is untouched.
- `tests/test_recount_e2e.py` — two installed tests. Builder argv
  `("recount",)` -> `("state", "recount")` at both run sites
  (`test_installed_novel_state_recount_exits_zero` and
  `test_installed_novel_state_recount_state_error_exits_three`). They assert
  `.exit_code`, `env["ok"]`, and the recounted `env["result"]`; no `command`
  assertion. The module's `_COMMAND = "novel-state"` constant is used **only**
  by the in-process `monkeypatch.setattr(sys, "argv", [_COMMAND, "recount"])`
  arm — leave it `"novel-state"`.
- `tests/test_reconcile_e2e.py` — every installed builder argv:
  `("reconcile",)` -> `("state", "reconcile")` and `("check",)` ->
  `("state", "check")` (the installed tests run both verbs). They assert
  `.exit_code`, `env["ok"]`, and `env["result"]["action"]`; no `command`
  assertion. `_COMMAND` stays `"novel-state"` (in-process arms only).
- `tests/test_set_chapters_e2e.py` — every installed builder argv:
  `("set-chapters", "--chapters", …)` -> `("state", "set-chapters",
  "--chapters", …)` (the success, shape-fault exit-2, and incoherent exit-3
  installed runs). They assert `.exit_code`/`env["ok"]`/`env["result"]`; no
  `command` assertion. `_COMMAND` stays `"novel-state"`.
- `tests/test_drafting_bijection_e2e.py` — `_run_check` calls
  `sh.make(prog, catalogue=…)("check")`; change to `("state", "check")`. The
  two consumers (`_run_check(dest, installed_novel_state, …)`) assert exit
  codes only; no `command` assertion; no module `_COMMAND` constant.

There is therefore **no `_INSTALLED_COMMAND` constant to add in WI3** — that
guidance applies only to the one module that genuinely asserts an installed
`command` field, `test_console_scripts_error_arms_e2e.py`, handled in WI4. (The
WI1 registry-sourced derivation is needed by WI4, not WI3: WI3 prepends the mount
verb as a literal second token — `("state", "check")` etc. — which the WI8 grep
gate confirms are spaced-surface verbs, not legacy command literals.)

Tests this work item must update: the listed installed e2e tests are *updated in
place* (argv prefix only). No new test files. The behavioural guarantee (exit
code, `ok`, `result` per arm) is unchanged; only the invocation surface changes.

Validation (each is `slow`; run the migrated tests):

```bash
uv run pytest -q tests/test_recount_e2e.py tests/test_reconcile_e2e.py \
  tests/test_set_chapters_e2e.py tests/test_drafting_bijection_e2e.py \
  tests/test_novel_state_check.py
make all
```

Acceptance: each migrated installed test invokes `novel state <verb>` (builder
argv prefixed with `state`) and keeps its existing exit-code / `ok` / `result`
assertions; no `command` assertion is added or changed in any of the five
modules; the in-process legacy tests in the same modules still pass with
`"novel-state"` (including line 143 of `test_novel_state_check.py`); `make all`
green. Commit (with WI2): "Drive novel-state installed e2e through novel state".

---

### WI4 — Migrate the all-scripts and error-arm installed e2e

Documentation to read: `docs/novel-ralph-harness-design.md` §3.2 (the two
command-agnostic diagnostic arms — usage exit 2, state exit 3). ADR-003 §3.1.
The WI1 derivation (`SUBCOMMAND_NAMES` from production `names`).

Skills to load: `python-router` -> `python-testing`. `leta`.

`tests/test_console_scripts_e2e.py`:

- Today it loops over `COMMAND_NAMES` (the legacy five), resolving
  `scripts_dir / command_name` and running each by absolute path, with
  `_REAL_PATH_ARGV = {"novel-state": ("check",)}`, asserting each exits `3`. The
  migration target is to run the single `novel` script once per operation with
  the mount-verb argv: `("state", "check")`, `("desloppify",)`, `("wordcount",)`,
  `("compile", "--check")`, `("done",)`. Rewrite `_assert_scripts_real_state_error`
  to resolve `scripts_dir / "novel"` once and iterate over the five operations
  taken from the production `SUBCOMMAND_NAMES` (imported directly from
  `novel_ralph_skill.commands.names`; **no** shared test-module mapping). For
  each spaced name `s`, the mount verb is `s.split(" ", 1)[1]`; build the run argv
  from it: the `state` operation runs `("state", "check")` (the routing special
  case, Decision Log D2), `compile` runs `("compile", "--check")`, and the three
  leaf verbs run `(verb,)`. Assert each still exits `ExitCode.STATE_ERROR` (3)
  with no traceback and no `"not yet implemented"` greeting.
- **Fate of the two module-level guards and the argv map (advisory A5).**
  `_REAL_PATH_ARGV = {"novel-state": ("check",)}` and the
  `assert set(COMMAND_NAMES) <= _REAL_COMMANDS, …` guard are keyed on legacy
  names. Re-key both onto the spaced operations: replace `_REAL_PATH_ARGV` with
  a map from the mount verb to the *extra* argv tokens after it — `{"state":
  ("check",), "compile": ("--check",)}`, the two operations that need a second
  token; the other three contribute none. Re-anchor the second guard on
  `SUBCOMMAND_NAMES` (e.g. `assert set(_REAL_PATH_ARGV) <=
  {s.split(" ", 1)[1] for s in SUBCOMMAND_NAMES}`), so a typo'd verb fails loudly.
  Keep the non-empty guard but anchor it on `SUBCOMMAND_NAMES`
  (`assert SUBCOMMAND_NAMES, …`).
- Note `novel compile --check`: use `("compile", "--check")` (the read-only
  divergence checker), not bare `("compile",)`. Both exit 3 under the e2e's
  no-`working/` cwd (verified in-process: `run(build_multiplexer(),
  ["compile","--check"], …)` and `run(build_multiplexer(), ["compile"], …)`
  both exit 3 on an absent tree, so the empty-cwd guard does not by itself
  distinguish them). The reason to keep `--check` is *path selection*, not the
  guard's exit code: bare `novel compile` is the *write* surface (it writes
  `compiled.md` when a tree is present), whereas `--check` is the read-only
  checker the other installed suites (`test_console_scripts_error_arms_e2e.py`,
  the BDD loop) rely on; the all-operations loop must stay on the read path so
  it never mutates the throwaway cwd. (Corrects the round-1 rationale, which
  wrongly stated bare `compile` "exits 0 after writing" under the empty cwd.)
- After the A5 re-keying the loop iterates `SUBCOMMAND_NAMES`, so `COMMAND_NAMES`
  may no longer be referenced. Drop it from the `from
  novel_ralph_skill.commands.names import …` line if unused, keeping
  `SUBCOMMAND_NAMES` (this is a test-only import change, not a registry change).
  The import remains a **production** import — at no point does this module import
  a value from another test module.

`tests/test_console_scripts_error_arms_e2e.py`:

- `_COMMAND = "novel-state"` -> the installed run now drives
  `novel state check …`, so set `_COMMAND = "novel state"` and prepend the
  `state` mount verb to `_READ_SUBCOMMAND` usage (it already carries
  `("check",)`; the run argv becomes `("state", "check", …)`).
- The machine-envelope test asserts `envelope["command"] == _COMMAND`; with
  `_COMMAND = "novel state"` this now pins the spaced name on the body-less
  exit-2/exit-3 arms (the dispatcher derives `"novel state"` from the leading
  `state` token before the parser rejects `--nope`; Decision Log D3).
- The `--human` test asserts the header `command: novel-state`; change the
  expected header to `command: novel state` and the `_COMMAND in rendered`
  check accordingly.

Tests this work item must update: both modules in place. No new test files. The
exit-code and envelope-shape guarantees are unchanged; only the surface and the
stamped name change.

Validation:

```bash
uv run pytest -q tests/test_console_scripts_e2e.py \
  tests/test_console_scripts_error_arms_e2e.py
make all
```

Acceptance: the all-operations loop drives `novel <verb>` and each exits 3; the
error-arm envelope and `--human` header carry `"novel state"`; `make all` green.
Commit: "Drive console-scripts and error-arm e2e through novel multiplexer".

---

### WI5 — Migrate the `desloppify` installed e2e modules

Documentation to read: `docs/novel-ralph-harness-design.md` §4.4
(`novel desloppify [--pack | --ledger] [--chapter]`). ADR-003 §3.1. The WI1
mapping. `docs/scripting-standards.md` §cuprum.

Skills to load: `python-router` -> `python-testing`. `leta`.

`tests/test_desloppify_e2e.py`:

- `_build_and_install_desloppify` resolves `scripts_dir / "desloppify"`. Change
  the basename to `"novel"` (rename the helper to `_build_and_install_novel` if
  the name now misleads; keep it a private module helper). The not-found
  assertion message updates accordingly.
- Every run site (`sh.make(prog, catalogue=catalogue)(...)`) prepends the
  `desloppify` mount verb: the bare offender/clean runs become
  `("desloppify",)`; `--ledger` becomes `("desloppify", "--ledger", …)`. The
  envelope `command`, where asserted, becomes `"novel desloppify"`; the
  exit-code and `violations` assertions are unchanged.

`tests/test_ai_isms_e2e.py`:

- The `installed_desloppify` fixture resolves `scripts_dir / "desloppify"` and a
  `pack_path`. Change the script basename to `"novel"`; the pack-path resolution
  (via `_resolve_installed_pack`) is unaffected (it reads
  `importlib.resources`, not the script name). The run prepends the
  `desloppify` mount verb: `("desloppify", "--pack", str(pack_path))`. The
  exit-code and `violations` assertions are unchanged; if any `command`
  assertion exists, set it to `"novel desloppify"`.

Tests this work item must update: both modules in place; the parametrized
ai-isms cases and the ledger cases keep their data, only the invocation surface
changes.

Validation:

```bash
uv run pytest -q tests/test_desloppify_e2e.py tests/test_ai_isms_e2e.py
make all
```

Acceptance: both modules install the `novel` script and run
`novel desloppify …`; offender trees exit 4, clean trees exit 0, packs and the
ledger still travel in the wheel; `make all` green. Commit:
"Drive desloppify installed e2e through novel desloppify".

---

### WI6 — Migrate `test_novel_done_e2e.py` and `test_wordcount_e2e.py`

Documentation to read: `docs/novel-ralph-harness-design.md` §4.2 (`novel done`)
and §4.5 (`novel wordcount`). ADR-003 §3.1. The WI1 mapping.

Skills to load: `python-router` -> `python-testing`. `leta`.

`tests/test_novel_done_e2e.py`:

- `_build_and_install_novel_done` resolves `scripts_dir / "novel-done"`. Change
  the basename to `"novel"`. The run argv prepends the `done` mount verb: the
  bare `novel-done` run becomes `("done",)`; any extra argv keeps its position
  after `done`. The four behavioural cases (all-hold exit 0, absent-compile exit
  1, sole-stale exit 4, mid-draft-stale exit 1) keep their exit-code assertions;
  any envelope `command` assertion becomes `"novel done"`.

`tests/test_wordcount_e2e.py`:

- `_build_and_install_wordcount` resolves `scripts_dir / "wordcount"`. Change
  the basename to `"novel"`. The run argv prepends the `wordcount` mount verb:
  `("wordcount",)`. The gate-trigger and state-error (exit 3) cases keep their
  exit-code assertions; any envelope `command` assertion becomes
  `"novel wordcount"`.

Tests this work item must update: both modules in place.

Validation:

```bash
uv run pytest -q tests/test_novel_done_e2e.py tests/test_wordcount_e2e.py
make all
```

Acceptance: both install the `novel` script and run `novel done` /
`novel wordcount`; exit codes unchanged; `make all` green. Commit:
"Drive novel-done and wordcount installed e2e through novel multiplexer".

---

### WI7 — Migrate the installed per-chapter-loop BDD

Documentation to read: `docs/novel-ralph-harness-design.md` §4 and the
per-chapter loop diagram (line ~799: `novel-state recount / novel-done /
wordcount`). ADR-006. `AGENTS.md` lines 143-147 (`pytest-bdd` for behavioural
tests). The WI1 mapping.

Skills to load: `python-router` -> `python-testing` (pytest-bdd step modules,
fixtures by name). `leta` to read the step bindings; `grepai` if locating the
feature file by intent.

**This is the highest-blast-radius work item; treat the capture key and the
script basename as two *separate* things.** The module conflates three roles
today, and the migration must split them carefully or the suite fails with
`KeyError`.

Current shape (verified against real source). `_LOOP_ARGV` is keyed on the
*legacy script filename*, and that key plays **three** roles at once: (a) the
script basename resolved as `installed.scripts_dir / script_name`
(`_run_installed_argv` line 116); (b) the argv source (`_LOOP_ARGV[command_name]`
in `_run_installed` line 144); and (c) the **capture key**
(`capture_key=command_name`, line 145). `_run_installed_argv` already accepts
`script_name` and `capture_key` as *separate* parameters (lines 99-102), so the
machinery to decouple them is present:

```python
_LOOP_ARGV = {
    "novel-state": ("recount",),
    "novel-done": (),
    "wordcount": (),
    "desloppify": (),
    "novel-compile": ("--check",),
}
```

The `When`/`Then` steps look up captures by **literal** strings that must stay in
lockstep with whatever key `_run_installed`/`_run_installed_argv` writes:

- `run_installed_clean_spine` (line 210) iterates `for command_name in
  _LOOP_ARGV` and calls `_run_installed(installed, command_name)` — so every
  `_LOOP_ARGV` key becomes a capture key.
- `installed_clean_exit_zero` (line 223-224) iterates `_LOOP_ARGV` again and
  reads `installed.captures[command_name]` for each.
- `installed_wordcount_gates` reads `_result(installed, "wordcount")` (line 235).
- `installed_compile_clean` reads `_result(installed, "novel-compile")` (246).
- `run_installed_stale` (281-282) calls `_run_installed(installed, "novel-done")`
  and `_run_installed(installed, "novel-compile")`.
- `installed_stale_caught` reads `installed.captures["novel-done"]` (294),
  `_result(installed, "novel-done")` (298), `installed.captures["novel-compile"]`
  (301), and `_result(installed, "novel-compile")` (305).
- the refused-advance `When` (`run_installed_advance_phase`, 346-360) already
  calls `_run_installed_argv(installed, "novel-state", ("advance-phase",),
  capture_key="advance-phase")`, and `installed_advance_phase_refused` reads
  `installed.captures["advance-phase"]` (375).

**Migration directive — keep every capture key (and therefore every `Then`-step
literal) byte-identical; change only the script basename and the argv.**
Concretely:

1. **Script basename:** pass `"novel"` as the `script_name` to
   `_run_installed_argv` for **every** command, including `advance-phase`. The
   simplest, lowest-risk edit is to make `_run_installed` resolve `"novel"`
   regardless of the loop key, and to change the `advance-phase` `When` step's
   first positional from `"novel-state"` to `"novel"`. After WI2 the
   `installed_novel_state` fixture already returns the `novel` path, so
   `installed.scripts_dir = installed_novel_state.parent` still points at the
   venv `bin/` containing `novel`.
2. **Argv — prepend the mount verb to each `_LOOP_ARGV` value:**

   ```python
   _LOOP_ARGV = {
       "novel-state": ("state", "recount"),
       "novel-done": ("done",),
       "wordcount": ("wordcount",),
       "desloppify": ("desloppify",),
       "novel-compile": ("compile", "--check"),
   }
   ```

   and change the `advance-phase` `When` step argv from `("advance-phase",)` to
   `("state", "advance-phase")`.
3. **Capture keys — leave them exactly as today.** Keep the `_LOOP_ARGV` keys
   as the legacy strings (`"novel-state"`, `"novel-done"`, `"wordcount"`,
   `"desloppify"`, `"novel-compile"`) **only** in their role as capture keys, so
   that every `Then`-step literal above (`installed.captures["novel-done"]`,
   `_result(installed, "novel-compile")`, `_result(installed, "wordcount")`, the
   loop over `_LOOP_ARGV`, and the distinct `"advance-phase"`) continues to
   resolve with **no edit**. Do **not** re-key `_LOOP_ARGV` to mount verbs or
   spaced names; doing so would require touching every `Then` literal and is the
   exact failure path the reviewer flagged (pre-mortem path 1, `KeyError`).

   Because the dict keys now serve only as argv source + capture key (no longer
   as script basename), update the `_run_installed` docstring and the module
   docstring lines 23-32 to say each command resolves the single `novel` script
   with the mount-verb argv, the capture key staying the legacy operation label
   for continuity with the `Then` assertions. Adjust the `_run_installed`
   helper so it passes `script_name="novel"` and `capture_key=command_name` (the
   `command_name` continues to index `_LOOP_ARGV` for the argv). `_result` and
   `_assert_no_traceback` index `installed.captures[command_name]`/`[…]` and need
   **no** change since the capture keys are unchanged.

This module asserts **no** `envelope["command"]` field anywhere (it asserts
exit codes, `result["cumulative"]`, `result["diverged"]`,
`result["compile_consistent"]`, no-traceback, and `state.toml` byte-equality), so
there is **no** `command` assertion to migrate here — only the script basename
and argv change. Verified against real source (Decision Log D7).

Tests this work item must update: the step module in place. **Do not edit the
feature file** `tests/features/per_chapter_loop_installed.feature` or the
`@given`/`@when`/`@then` decorator strings: the legacy words
(`novel-done`, `wordcount`, `advance-phase`, `compile`) there are *descriptive
English* in the scenario prose, not invocation literals, and the migration is
internal argv only (advisory A2). pytest-bdd matches step text against decorator
strings **verbatim**, so if the prose were ever touched, the `.feature` text and
the matching decorator string must change in lockstep or step resolution fails
with "step definition not found". Default: leave both untouched.

Validation:

```bash
uv run pytest -q tests/test_per_chapter_loop_installed_bdd.py
make all
```

Acceptance: the installed per-chapter loop drives the single `novel` script for
all five clean-pass operations plus the refused `advance-phase`, each with the
mount-verb argv; every capture key and `Then`-step lookup string is unchanged, so
the clean pass still exits 0 with no traceback, the stale-compile arms exit 4, and
the refused advance exits 3 with `state.toml` intact; no `KeyError`; `make all`
green. Commit: "Drive installed per-chapter-loop BDD through novel multiplexer".

---

### WI8 — Closing grep gate and full validation

Documentation to read: `AGENTS.md` lines 63-98 (gates). ADR-007 (success
criterion). The roadmap 1.2.13 success line.

Skills to load: `python-router` -> `python-testing`. `leta`/`grepai` for the
sweep.

What to do: prove the migration is complete-by-construction. Run a grep over the
in-scope installed-e2e modules that must return **no** match for a legacy
command literal used in an *invocation* or a `command`-field assertion:

```bash
grep -rn '"novel-state"\|"novel-done"\|"novel-compile"\|"desloppify"\|"wordcount"' \
  tests/test_console_scripts_e2e.py \
  tests/test_console_scripts_error_arms_e2e.py \
  tests/test_recount_e2e.py tests/test_reconcile_e2e.py \
  tests/test_set_chapters_e2e.py tests/test_drafting_bijection_e2e.py \
  tests/test_desloppify_e2e.py tests/test_ai_isms_e2e.py \
  tests/test_novel_done_e2e.py tests/test_wordcount_e2e.py \
  tests/steps/per_chapter_loop_installed_steps.py
```

Expected residual matches (all benign; enumerate them in the commit body so a
reviewer can confirm nothing leaked):

1. The not-found *diagnostic message* string in
   `tests/installed_binary_fixtures.py` and the per-module `_build_and_install_*`
   helpers (these reference `"novel"`, not a legacy literal, after WI2/WI5/WI6).
2. The legacy `_COMMAND = "novel-state"` constants intentionally retained in
   `test_recount_e2e.py`, `test_reconcile_e2e.py`, `test_set_chapters_e2e.py`,
   and `test_novel_state_check.py` — each used **only** by an in-process
   `monkeypatch.setattr(sys, "argv", [_COMMAND, …])` legacy-oracle arm (and line
   143's `_capture_envelope` shape oracle in `test_novel_state_check.py`), never
   by an installed invocation or installed `command` assertion.
3. The legacy strings retained as **capture keys** in
   `tests/steps/per_chapter_loop_installed_steps.py` `_LOOP_ARGV` and its
   `Then`-step lookups (`"novel-done"`, `"novel-compile"`, `"wordcount"`,
   `"novel-state"`) — these are dictionary keys / capture labels, deliberately
   kept identical (WI7) to keep the `Then` literals in lockstep; they are **not**
   invocation argv (the argv values are now `("state","recount")`,
   `("compile","--check")`, …) and **not** `command`-field assertions.

Confirm each match falls into one of these three categories; any other match
(a legacy literal inside a `sh.make(...)(...)` argv tuple, or an
`envelope["command"] == "novel-…"` comparison) is a real leak — fix it before
committing. Document the residual set in the commit body.

This grep is a developer-run completeness check, not a committed test, unless a
lightweight registry-coupling unit test already covers it (the WI1 unit test
pins the mapping; the grep pins the call sites). If you choose to encode it, add
it as a fast in-process test that reads the in-scope module sources and asserts
no legacy literal appears in a `sh.make(...)(...)` argv or an
`envelope["command"] ==` comparison — but a source-scanning test is brittle;
prefer the manual grep recorded in the commit body plus the green installed
suite as the real proof.

Then run the full gate:

```bash
make all
```

If any Markdown changed in this task (the plan itself is under `docs/`, but it is
the execplan, not a shipped doc — still lint it):

```bash
make markdownlint
make nixie
```

Acceptance (the roadmap 1.2.13 success criterion): every e2e test invokes
`novel <sub>`; the legacy entry points and registry symbols are untouched and
still pass (`test_pyproject_scripts.py`, `test_command_names_registry.py` green
unchanged); `make all` (including the installed-binary e2e) is green. Commit:
"Verify novel-multiplexer e2e migration is complete" (if the gate adds a test or
doc note; otherwise fold WI8 validation into WI7's commit).

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` (`pytest -n auto`) passes. Each migrated installed e2e
  builds the wheel, installs it, resolves `scripts_dir / "novel"`, runs
  `novel <verb> …` by absolute path through the one-program cuprum catalogue,
  and asserts the same exit code as before plus (where it asserts `command`) the
  spaced name. The in-process legacy-oracle tests and the registry gates remain
  green unchanged.
- Lint/typecheck: `make lint` (Ruff, interrogate 100% docstring coverage,
  Pylint) and `make typecheck` (`ty`) pass. New helpers/mappings carry
  docstrings; the installed-e2e modules are inside `PYTHON_TARGETS`, so use
  explicit `raise AssertionError` over bare `assert` where the file convention
  requires it.
- Format: `make check-fmt` passes.
- Audit: `make audit` (`pip-audit`) passes (no dependency change expected).
- Markdown (this plan only, plus any doc note): `make markdownlint` and
  `make nixie` pass.

Quality method (how we check): `make all` runs the full gate locally. The
installed e2e is the behaviour-level acceptance: a green `make test` over the
`slow`-marked installed modules proves the `novel` console-script ships in the
wheel and runs every subcommand to its documented exit code.

Behavioural acceptance, phrased as observable behaviour:

- Running `make test` and inspecting `tests/test_console_scripts_e2e.py`'s run:
  the single installed `novel` script, run as `novel state check`,
  `novel desloppify`, `novel wordcount`, `novel compile --check`, and
  `novel done` under a cwd with no `working/`, each exits `3` with no traceback.
- Running `tests/test_console_scripts_error_arms_e2e.py`: the installed
  `novel state check --nope` exits `2` and `novel state check` (absent tree)
  exits `3`, each stamping `envelope["command"] == "novel state"` in machine
  mode and `command: novel state` in `--human` mode.
- Running `tests/test_pyproject_scripts.py` and
  `tests/test_command_names_registry.py`: both pass unchanged, proving the six
  `[project.scripts]` entries and the five `COMMAND_NAMES` are intact.

## Idempotence and recovery

Every step is a re-runnable test-source edit; re-running `make all` is safe and
drift-free. The wheel build/install happens in throwaway `tmp_path` /
`tmp_path_factory` directories the tests own, so reruns leave no residue. If a
migrated module fails, revert that one module's edit (it is one commit) and
re-apply; no other module depends on it beyond the WI1 mapping and the WI2
fixture, both landed first. No destructive operations; no schema or data
migration.

## Artifacts and notes

Verified facts captured during planning (pin these; do not re-derive from the
local cuprum checkout):

- cuprum `0.1.0` installed surface (from the project venv):
  `ProgramCatalogue(projects=Iterable[ProjectSettings])`;
  `ProjectSettings(name, programs, documentation_locations, noise_rules)`;
  `sh.make(program, *, catalogue) -> SafeCmdBuilder`;
  `SafeCmd.run_sync(*, capture=True, echo=False, context=None) -> CommandResult`;
  `CommandResult` fields `program, argv, exit_code, pid, stdout, stderr`;
  `ExecutionContext(cwd=…)`. `Program = NewType("Program", str)`, so an
  absolute-path program is allowlistable. An absolute-path `Program`
  (`/usr/bin/true`) in a one-`ProjectSettings` catalogue runs and returns
  `exit_code == 0` (verified in the venv).
- Multiplexer routing (in-process, locked dispatcher):
  `novel._command_name_for(["state","check"]) == "novel state"`;
  `run(build_multiplexer(), ["state","check"], …)` exits `3` under an empty cwd;
  `["desloppify"]`, `["wordcount"]`, `["compile","--check"]`, `["done"]` each
  resolve to their spaced name and exit `3` bare.
- pytest-timeout `2.4.0`: the `@pytest.mark.timeout(180)` marker is the
  highest-priority per-item override (ini < env < CLI < per-item marker) and
  supersedes the project's 30s default for that one test (official PyPI docs).
- Cyclopts `4.18.0`: a bare `novel` and `--help` / `--version` return the
  body-less help/version path (`run` exit 0, no envelope); a usage fault raises
  a `CycloptsError` subclass mapped to exit 2 (`novel.py` docstring, 1.2.12
  Decision Log D2/D3).

## Interfaces and dependencies

Be prescriptive about the test-only surface this task introduces:

- The spaced-name and mount-verb derivations are taken **inline from production
  code** in each consumer — `SUBCOMMAND_NAMES` (and, where the legacy->spaced
  pairing is needed, `dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))`)
  from `novel_ralph_skill.commands.names`, with the mount verb computed as
  `spaced.split(" ", 1)[1]`. **No** shared test-module value
  (`SPACED_COMMAND`/`MOUNT_VERB` module-level dict) is introduced in
  `tests/installed_binary_fixtures.py` or any plugin module — that would be a
  cross-module test value import the developers-guide forbids (Decision Log D8).
  If a shared, injected form is wanted, the only sanctioned home is a
  `tests/conftest.py` fixture consumed **by parameter name**, never an importable
  module-level dict.

- A new fast in-process unit test `tests/test_installed_command_names.py` pins the
  registry-order coupling (`zip(strict=True)` safety, the five legacy->spaced
  pairings, the two-token spaced-name shape); it imports **only** production
  `names`, no test module.

- The `installed_novel_state` fixture keeps its signature
  `installed_novel_state(tmp_path_factory: pytest.TempPathFactory) -> Path` and
  its name; only the resolved script basename changes from `"novel-state"` to
  `"novel"`.

- No change to any `novel_ralph_skill` module, any `[project.scripts]` entry, or
  any `names.py` symbol. No new third-party dependency.

## Decision log (continued)

- Decision: D6 — WI2 (fixture basename flip) and WI3 (consumer argv migration)
  land in a single commit (or WI3 immediately follows with WI2 uncommitted
  alone). Rationale: flipping the fixture to return `novel` while consumers still
  pass a bare `check` argv would invoke `novel check` (unrouted; not
  `novel state check`), breaking `make test` mid-series and violating the
  "each commit gate-passable" rule. Date/Author: 2026-06-25, planning agent.
- Decision: D7 — exactly **one** installed module asserts the envelope `command`
  field: `test_console_scripts_error_arms_e2e.py` (lines 194, 234-236, against
  `_COMMAND = "novel-state"`). Migrated in WI4 by flipping `_COMMAND` to the
  spaced `"novel state"`. The four `installed_novel_state` state consumers
  (`test_recount_e2e.py`, `test_reconcile_e2e.py`, `test_set_chapters_e2e.py`,
  `test_drafting_bijection_e2e.py`) and the installed BDD step module assert
  **no** `command` field on the installed run; their WI3/WI7 migration is a pure
  argv mount-verb prepend. The only `command` assertion in the state cluster is
  `test_novel_state_check.py` line 143 — an *in-process* legacy oracle
  (`_capture_envelope`/`monkeypatch`) that must stay `"novel-state"` and must not
  be edited. Rationale: verified against the real test source by grepping each
  module for `envelope["command"]`/`["command"]`/`command ==` and reading the
  matching tests; round-1 WI3 wrongly directed `command`-assertion edits in the
  four state consumers that have none, risking invented assertions or destruction
  of the line-143 parity oracle (review B1). Date/Author: 2026-06-25, planning
  agent.
- Decision: D8 — the legacy->spaced and spaced->mount-verb derivations are taken
  **inline from production `novel_ralph_skill.commands.names`**
  (`SUBCOMMAND_NAMES`, `COMMAND_NAMES`, paired positionally), **not** from a
  shared test-module dict (`SPACED_COMMAND`/`MOUNT_VERB`). Rationale: a
  module-level dict in `tests/installed_binary_fixtures.py` (or a `pytest_plugins`
  module) can only be reached from a `test_*.py` by a cross-module **value**
  import, which the developers-guide §"Shared test scaffolding" (lines 57-75)
  forbids ("never by importing from another test module or from `conftest`
  itself"; only a `TYPE_CHECKING`-guarded *type* is exempt). `pytest_plugins`
  shares *fixtures* by name, not constants, so it does not rescue the pattern. The
  derivation is unnecessary as a test value: `SUBCOMMAND_NAMES` is importable from
  production code with no test coupling, and `test_console_scripts_e2e.py` already
  imports `COMMAND_NAMES` from `names`. The registry-order coupling
  (`COMMAND_NAMES`/`SUBCOMMAND_NAMES` pair positionally, names.py lines 39-45 and
  68-74) makes `dict(zip(…, strict=True))` exact; the WI1 unit test pins it. This
  resolves round-2 review B3. Verified against real source: the only sanctioned
  runtime cross-module value imports in the suite are the documented `conftest`
  carve-outs (`STATE_FAULT_MESSAGE`, `WorkingTreeSpec`); there is no precedent for
  importing a value from a non-`conftest` plugin module. Date/Author: 2026-06-25,
  planning agent.

- Decision: D9 — `test_console_scripts_error_arms_e2e.py` migrates in the WI2+WI3
  commit, not in a later WI4 commit. Rationale: it is the one module besides the
  five state consumers that binds the shared `installed_novel_state` fixture, so
  the WI2 basename flip (which D6 requires landing with WI3) makes it invoke the
  `novel` script with a bare `("check", …)` argv — exit 0 help instead of the real
  exit-2/exit-3 arms — and `make test` fails mid-series. Folding its argv-and-name
  migration (the only installed `command` assertion in the suite, D7) into the
  WI2+WI3 commit keeps each commit gate-passable. `test_console_scripts_e2e.py`,
  the other half of WI4, has its own wheel builder and does not bind the fixture,
  so it stays a separate commit. Date/Author: 2026-06-25, implementing agent.

## Revision note

Initial draft (2026-06-25). Decomposes roadmap task 1.2.13 into eight atomic,
gate-passable work items that migrate only the installed-binary e2e suites (plus
the installed BDD step module) to invoke `novel <sub>`, derive the spaced
envelope `command` from the registry-sourced mapping, and leave the legacy
entry points, registry symbols, in-process legacy-oracle tests, and snapshots
untouched for task 1.2.15. All load-bearing cuprum, Cyclopts, and pytest-timeout
behaviours are pinned to the locked installed versions and verified
(in-process drive, venv API introspection, official docs) rather than asserted
from memory.

Round 2 revision (2026-06-25), resolving Logisphere review-r1 blocking points.

- B1 (WI3 phantom `command` assertions). Audited all four `installed_novel_state`
  state consumers plus `test_novel_state_check.py` against real source: none of
  their *installed* tests assert `envelope["command"]` (they assert
  `.exit_code`/`env["ok"]`/`env["result"]`). The lone `command` assertion is
  `test_novel_state_check.py` line 143 — an in-process oracle that must stay
  `"novel-state"`. WI3 is re-scoped to an **argv-prefix-only** migration with no
  `command`-assertion edit and an explicit "do not touch line 143" instruction;
  the `_INSTALLED_COMMAND`/spaced-command guidance is restricted to the one
  module that genuinely asserts an installed `command` field,
  `test_console_scripts_error_arms_e2e.py` (WI4). Risk 1, the in-scope file list,
  WI3 acceptance, and new Decision Log D7 are updated to match.
- B2 (WI7 BDD capture-key coupling). WI7 now enumerates every capture key and
  every `Then`-step literal lookup in
  `tests/steps/per_chapter_loop_installed_steps.py`, and directs the implementer
  to (1) pass script basename `"novel"` to `_run_installed_argv` for every
  command including `advance-phase`, (2) prepend the mount verb to each argv
  (`("state","recount")`, `("compile","--check")`, `("state","advance-phase")`,
  …), and (3) keep every capture key and `Then`-step lookup string byte-identical
  by leaving `_LOOP_ARGV` keyed on the legacy operation labels (decoupling capture
  key from script basename, which `_run_installed_argv` already supports). WI8's
  expected-residual set now explicitly whitelists those retained capture keys.
- Advisories applied: A1 (corrected the bare-`compile`-exits-0 rationale; both
  bare and `--check` exit 3 under the empty cwd, `--check` chosen for read-path
  selection), A2 (explicit "leave the feature/decorator prose untouched; change
  in lockstep if ever touched"), and A3 (quoted the roadmap's ADDITIVE
  parity-oracle clause in Purpose to pre-empt the literal-reading gap).

Round 3 revision (2026-06-25), resolving Logisphere review-r2 blocking point B3
and advisory A5.

- B3 (WI1 forbidden cross-module test value import). The round-2 WI1 added
  `SPACED_COMMAND`/`MOUNT_VERB` as module-level dicts in
  `tests/installed_binary_fixtures.py` and directed WI4 to consume them — a
  cross-module **value** import a `test_*.py` can only satisfy by `import`ing from
  another test/plugin module, which the developers-guide §"Shared test
  scaffolding" forbids and the plan itself quoted the rule against. WI1 is
  rewritten to **drop the shared test-module dicts entirely** and derive the
  spaced name and mount verb **inline from production
  `novel_ralph_skill.commands.names`** (`SUBCOMMAND_NAMES`/`COMMAND_NAMES`,
  positionally paired; mount verb = `spaced.split(" ", 1)[1]`). The fix is exact
  because the two registry tuples pair positionally (names.py lines 39-45, 68-74).
  WI4's "iterate over the five tuples derived from `MOUNT_VERB`" instruction is
  re-worded to iterate `SUBCOMMAND_NAMES` directly; the Interfaces-and-dependencies
  block, the Risk-1 mitigation, the Purpose paragraph, the WI3 cross-reference,
  Stage A, and the Progress line are all re-worded to drop the shared-mapping
  language; new Decision Log D8 records the resolution and the verified
  no-precedent finding. The WI1 unit test now imports **only** production `names`
  and pins the positional pairing (`zip(strict=True)` safety), removing the
  module-level guard that no longer has a shared value to guard.
- A5 (WI4 `_REAL_COMMANDS`/`_REAL_PATH_ARGV` underspecified). WI4 now spells out
  the fate of both module-level constants: re-key `_REAL_PATH_ARGV` onto the mount
  verb -> extra-argv map (`{"state": ("check",), "compile": ("--check",)}`), and
  re-anchor the membership guard and the non-empty guard on `SUBCOMMAND_NAMES`.
