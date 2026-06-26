# Cross the installed-binary command-agnostic error arms (exit 2 and exit 3) over a built wheel

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (round 3 — B1 and B2 resolved)

## Purpose / big picture

The harness gates on the five console-scripts by exit code, so each
load-bearing exit-code behaviour must be proven against a *real installed
binary*, not merely the in-process entry-point body. Task 6.2.8 closed the
in-process half of one gap: it crossed the two **command-agnostic diagnostic
arms** the shared runner stamps *before any command body runs* — the usage
error (exit 2, `CycloptsError`) and the state-or-input error (exit 3,
`StateInputError`) — for all five read commands, asserting the `--human` stamp
and the envelope skeleton. Those arms live in
[`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
(the `except CycloptsError` and `except StateInputError` blocks in `run`), and
they are the arms the §3.2 exit-code table the harness branches on.

The **installed-binary** half of that same gap is open. Today the installed
e2es prove exit 0 (`check`, `recount`), exit 4 (`desloppify`, `novel-done`),
exit 1/4 (`novel-done`), and the exit-3 state-error path for the installed
`novel-state recount`
([`tests/test_recount_e2e.py`](../../tests/test_recount_e2e.py)) and for all
five installed scripts' bare exit-3
([`tests/test_console_scripts_e2e.py`](../../tests/test_console_scripts_e2e.py)).
But no installed binary is ever observed taking the **usage (exit 2)** arm, and
no installed exit-3 proof asserts the **envelope shape** or the **`--human`
stamp** that 6.2.8 pinned in-process. The in-process-versus-binary symmetry the
step-6.2 hypothesis demands is therefore broken for exactly the two
command-agnostic diagnostic arms the harness gates on.

After this change, a developer can run the slow installed-binary e2e suite and
observe two new proofs against a real console-script over a built wheel: the
installed `novel-state` exits **2** with an `ok: false` usage envelope on a
malformed invocation (an unknown option), and exits **3** with an `ok: false`
state envelope on an absent `working/` — each asserted in **both** output modes,
with the `--human` stamp present (the command name in the human rendering) and
the machine envelope skeleton (`command`, `ok: false`, `working_dir`,
`result: {}`, exactly one message) pinned. The §3.2 / ADR-003 §3.1 contract is
then anchored at the subprocess boundary for the two diagnostic arms exactly as
6.2.8 anchored it in-process.

Observable success, runnable verbatim from the worktree root:

```plaintext
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10
uv run pytest -v tests/test_console_scripts_error_arms_e2e.py -m slow
```

Expect the new installed-binary exit-2 and exit-3 error-arm e2es to pass (each
parametrised over machine and human mode), and:

```plaintext
make all
make markdownlint
make nixie
```

passing over the new test module and the updated design §9 / developers' guide
prose.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. Work exclusively inside the worktree at
   `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10`. Never
   read-modify-write any file in the root/control worktree.
2. This is a **test-and-docs** task. Do not modify any production module under
   `novel_ralph_skill/`. The runner's two diagnostic arms, the envelope
   builder, the `--human` pre-parse (`parse_global_flags`), and every command
   body must remain byte-for-byte unchanged. If a production change is needed to
   make a test pass, stop and escalate — that means the behaviour this task
   assumes is not what the runner does.
3. The installed-binary e2es run every external program through a local cuprum
   `ProgramCatalogue` allowlist: `uv` (a bare name) for build/venv/install and
   the installed console-script (run by **absolute path**). No raw `subprocess`,
   and no `uv run` resolution of the project environment (the wheel under test
   must be the freshly built one). This is the discipline ADR-006 "Decision
   outcome", `docs/scripting-standards.md`, and the existing installed e2es
   already use ([`tests/test_console_scripts_e2e.py`](../../tests/test_console_scripts_e2e.py)
   lines 105-118; [`tests/test_recount_e2e.py`](../../tests/test_recount_e2e.py)
   lines 128-134).
4. The installed-binary e2es are **POSIX-only** (ADR-006). The new module
   carries a module-level `pytestmark = pytest.mark.skipif(os.name != "posix",
   reason="… ADR 006")`, mirroring
   [`tests/test_console_scripts_e2e.py`](../../tests/test_console_scripts_e2e.py)
   lines 76-79 and `test_recount_e2e.py`'s per-test guard.
5. Slow installed-binary e2es carry `@pytest.mark.slow` and an explicit
   `@pytest.mark.timeout(180)` that supersedes the 30 s project default
   (`pyproject.toml` line 326 `timeout = 30`; the `slow` marker is declared line
   328), exactly as the existing installed e2es do. The 180 s per-test timeout
   is a per-test override that wins over the global default under
   `pytest-timeout` and is unaffected by `pytest-xdist` `-n auto` (verified: see
   `Surprises & Discoveries`).
6. The exit-code semantics are fixed policy (design §3.2 table; ADR-003 Table
   2): 2 = usage error (unknown subcommand or bad arguments); 3 =
   state-or-input error (missing/unparseable `state.toml`, absent working dir).
   The plan asserts exactly these codes; it must not relabel them.
7. The shared-test-scaffolding rule (developers' guide "Shared test
   scaffolding"): test modules consume helpers by **fixture name**, never by
   importing a helper *value* from another test module or from `conftest`. The
   new module consumes the built-and-installed script through the existing
   module-scoped `installed_novel_state` fixture
   ([`tests/installed_binary_fixtures.py`](../../tests/installed_binary_fixtures.py),
   roadmap 6.2.4) and the one-program catalogue through the
   `single_program_catalogue` fixture (`tests/conftest.py`); it builds no wheel
   of its own.
8. Snapshot discipline (AGENTS.md "Python verification and testing"): if a
   syrupy snapshot is used, pair it with semantic assertions and redact every
   platform/locale-variable field (the OS errno string in the exit-3 message;
   the Cyclopts wording of the exit-2 message). This plan asserts the envelope
   **in code** (the skeleton plus a message *prefix*), not via syrupy, because
   the matrix already owns the redacted machine-envelope snapshot in-process and
   re-snapshotting it at the subprocess boundary would only re-pin a skeleton
   the in-code assertions already pin (see Decision D-NOSNAP); if a reviewer
   requires a snapshot, the message field must be redacted exactly as 6.2.8's
   matrix snapshot does.
9. Keep every code file at or under the 400-line module cap (AGENTS.md). The new
   module is small (one helper plus two parametrised tests); it must not breach
   the cap, and folding the new arms into `test_console_scripts_e2e.py` (181
   lines today) is rejected because that module owns the all-five-scripts
   install-and-run guard and re-paying a wheel build there is unnecessary when
   the module-scoped `installed_novel_state` fixture already caches one (Decision
   D-MODULE).
10. AGENTS.md quality gates (`make all`, plus `make markdownlint` and
    `make nixie` for any Markdown change) must pass before each commit. en-GB
    Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and commit
    messages; Markdown paragraphs wrap at 80 columns, code blocks at 120.

## Tolerances (exception triggers)

Stop and escalate (document in `Decision Log`, then await direction) when:

- Scope: implementation requires changes to more than 3 files (the new test
  module, design §9, the developers' guide) or more than ~180 net new lines of
  code. A fourth touched file means the change has grown beyond what was
  planned.
- Production code: any change under `novel_ralph_skill/` is required to make a
  test pass — the arms this task crosses are a frozen contract; a forced change
  means the contract is wrong, not the test.
- Behaviour fork: the installed binary's observed exit code for either arm does
  not match the design §3.2 expectation (e.g. the usage arm exits 1 rather than
  2, or either arm prints a traceback rather than an envelope). That is a real
  contract defect; surface it rather than rewriting the assertion to match.
- Human-stamp fork: the installed binary's human-mode rendering does **not**
  carry the command name on a body-less arm (i.e. the `--human` selection is
  lost across the subprocess boundary). Stop and escalate — that would mean the
  console-script entry point drops the global flag the §3.2 arms must stamp.
- Dependencies: any new runtime or dev dependency, or a change to the
  `cuprum==0.1.0` floor, is required.
- Iterations: the slow e2e still fails after 3 focused fix attempts (e.g. a
  wheel-build, venv, or cwd-resolution surprise that is not a test-logic bug).
- Ambiguity: the representative-command choice (drive one command, since 6.2.8
  verified the arms are command-agnostic across all five) proves wrong — i.e.
  the installed `novel-state` arm behaves differently from another installed
  script. Stop and reconsider whether to cross all five rather than silently
  switching commands.

## Risks

- Risk: the exit-3 message embeds the OS `strerror` text (`[Errno 2] No such
  file or directory: 'working/state.toml'`), which is locale- and
  platform-dependent.
  Severity: medium
  Likelihood: high (off the development locale/OS)
  Mitigation: drive the **absent-`working/`** variant (the §3.2 first-class
  exit-3 trigger) and assert the message by its command-body-owned constant
  *prefix* (`"cannot load working/state.toml"`), not the full errno string —
  exactly the redaction 6.2.8 settled on for the matrix snapshot.

- Risk: the exit-2 message wording is Cyclopts's (`"Unknown option: --nope."`,
  optionally with a `" Did you mean …"` suffix on `novel-compile --check`), so a
  future Cyclopts upgrade could churn a full-string assertion.
  Severity: low
  Likelihood: low (locked at `cyclopts 4.18.0` in `uv.lock`)
  Mitigation: assert the exit *code* (2) and the redacted envelope skeleton as
  the primary contract; assert the message only by its stable prefix
  (`"Unknown option:"`). The chosen command (`novel-state check`) emits the
  bare `"Unknown option: --nope."` with no suffix (verified), so the prefix
  assertion is exact for this command.

- Risk: the slow e2e adds wheel-build + venv + install + script-run cost under
  `-n auto`; a too-tight timeout could flake.
  Severity: low
  Likelihood: low
  Mitigation: the wheel/venv/install is paid **once** by the module-scoped
  `installed_novel_state` fixture and reused by every parametrised case in the
  new module (Decision D-FIXTURE); each case is a single fast script run. Reuse
  the proven `@pytest.mark.timeout(180)` per-test override (Constraint 5).

- Risk: the `--human` selection is lost across the subprocess boundary, so the
  human-mode case asserts a machine envelope.
  Severity: medium
  Likelihood: low (the console-script `_drive` pre-parses `--human` from
  `sys.argv[1:]` before `run`, so passing `--human` on the installed binary's
  argv does stamp the human envelope — verified in-process; see `Surprises &
  Discoveries`)
  Mitigation: the human-mode assertion is the §3.2 / ADR-003 §3.1 contract this
  task exists to anchor at the boundary; if it fails, that is a Tolerance breach
  (human-stamp fork), not an assertion to soften.

## Progress

- [x] Work item 1: Add the installed-binary error-arm e2e module
  (`tests/test_console_scripts_error_arms_e2e.py`) — a module-local
  `run_installed` driver fixture plus a four-parameter helper and two
  three-parameter parametrised tests — crossing the exit-2 usage arm and the
  exit-3 state arm over the installed `novel-state`, each in machine and human
  mode, asserting the envelope skeleton, the message prefix, and the `--human`
  stamp; `make all` green (including the four-parameter Pylint gate). DONE: the
  four cells pass (2 machine + 2 human), `make all` reports 980 passed / 1
  skipped. CodeRabbit minor finding (self-describing assert messages) applied;
  its major "group into a test class" finding was declined (see Decision
  D-NOCLASS).
- [x] Work item 2: Reconcile the living documentation — extend design §9's
  "Installed-binary e2es" bullet and the developers' guide so the prose records
  that the two command-agnostic diagnostic arms (usage exit 2, state exit 3) are
  now proven at the installed boundary with the `--human` stamp and envelope
  shape pinned; `make markdownlint`, `make nixie`, `make all` green. DONE: design
  §9 bullet and the developers' guide "Shared test scaffolding" section both
  name the new boundary coverage; `make markdownlint`, `make nixie`, `make all`
  all pass. A pre-existing MD012 double-blank in `docs/developers-guide.md`
  (introduced by the 7.1.2 ledger merge) was fixed in passing since the file was
  already being edited. The leftover planning artifact
  `docs/execplans/roadmap-6-2-10.review-r1.md` (never tracked) was removed so the
  global `make markdownlint` gate passes.

## Surprises & discoveries

- Observation: the locked, **installed** cuprum 0.1.0 and the local development
  checkout at `/data/leynos/Projects/cuprum` have **divergent** `SafeCmd`
  run-API signatures. The plan must pin against the installed 0.1.0, not the
  local checkout.
  Evidence: `uv run python -c "import inspect; from cuprum import sh;
  print(inspect.signature(sh.SafeCmd.run_sync))"` in the worktree prints
  `(self, *, capture: bool = True, echo: bool = False, context:
  ExecutionContext | None = None) -> CommandResult` for the installed 0.1.0,
  whereas `/data/leynos/Projects/cuprum/cuprum/sh.py` line 441 defines
  `run_sync(self, *, output: RunOutputOptions | None = None, timeout=None,
  context=None, stdin=None)` (no `capture` kwarg). The installed `uv.lock` pin
  (`cuprum==0.1.0`, lines 113-118) is canonical.
  Impact: the existing installed e2es' call shape
  `sh.make(prog, catalogue=cat)(*argv).run_sync(context=ExecutionContext(
  cwd=run_dir), capture=True)` is the correct, supported shape for the locked
  version and is what the new module reuses verbatim. The `ExecutionContext`
  has a `cwd` field on the installed 0.1.0 (verified). An absolute-path
  `Program` runs correctly through a one-project `ProgramCatalogue` allowlist
  (verified: a `/usr/bin/env echo hi` run returned exit 0, stdout `"hi\n"`).

- Observation: both diagnostic arms fire over the real entry-point body with the
  `--human` stamp present, and emit the envelope to **stdout**.
  Evidence: driving `novel_ralph_skill.commands.stub.novel_state()` in-process
  (which is the exact body the installed console-script executes) over a cwd
  with no `working/`: `["check"]` → exit 3, stdout envelope `{"command":
  "novel-state", "ok": false, "working_dir": "working", "result": {},
  "messages": ["cannot load working/state.toml: [Errno 2] No such file or
  directory: 'working/state.toml'"]}`; `["--human", "check"]` → exit 3, stdout
  begins `command: novel-state\nok: False\nworking_dir: working\nmessages:\n  -
  cannot load working/state.toml: …`. With an unknown option: `["check",
  "--nope"]` → exit 2, stdout envelope with `messages: ["Unknown option:
  --nope."]`; `["--human", "check", "--nope"]` → exit 2, human rendering
  beginning `command: novel-state`.
  Impact: the human stamp reaches the body-less arms across the `--human`
  pre-parse; the machine envelope is on stdout, not stderr; the message field is
  the only command-/platform-variable part (so it is asserted by prefix). The
  arms are command-agnostic (6.2.8 verified this across all five read commands
  in-process), so crossing one representative installed command — `novel-state`,
  whose installed fixture already exists — is sufficient (Decision D-ONECMD).

- Observation: the project's Pylint argument-count gate is `max-args = 4` and
  **counts keyword-only parameters**, so the round-1 five-parameter helper would
  have failed `make all`.
  Evidence: `pyproject.toml` line 171 and line 180 both set `max-args = 4`;
  `too-many-arguments` (R0913) is enabled at line 297 and
  `too-many-positional-arguments` at line 303. The Makefile runs the PyPy-backed
  Pylint over `tests/` (`Makefile` line 97 `$(PYLINT) $(PYLINT_TARGETS)` with
  `PYLINT_TARGETS ?= $(PYTHON_TARGETS)` resolving to `novel_ralph_skill tests`,
  lines 17 and the `PYTHON_TARGETS` default). Pylint's R0913 counts every
  parameter including keyword-only ones, so `(arm, run_dir,
  installed_novel_state, build_catalogue, *, human)` = 5 trips it. The
  conformant in-process precedent `_drive_error_cell(cell, tmp_path, drive, *,
  human)` (matrix lines 380-417) stops at 4 total and passes.
  Impact: the helper and both tests are pinned at four total parameters via the
  `run_installed` driver fixture (Decision D-RUNNER); no per-file ignore is used.

- Observation: the new module's `wc.build_working_tree`/`wc.PHASE_STATES` calls
  require a top-level `import working_corpus as wc`; the established precedent
  places it in the third-party/first-party import group, after `pytest` and
  before the cuprum imports.
  Evidence: `tests/test_recount_e2e.py` line 30 imports `import working_corpus
  as wc` immediately after `import pytest` (line 29) and before `from cuprum
  import sh` (line 31); `tests/test_command_surface_matrix.py` line 88 imports
  `import working_corpus as wc` immediately after `import pytest` (line 87).
  `tests/working_corpus/__init__.py` exports `build_working_tree` (line 28, via
  `._builder`) and `PHASE_STATES` (line 53, via `._library`), both listed in
  `__all__` (lines 106, 114).
  Impact: the step-2 import list pins `import working_corpus as wc` in that
  group (resolving review B2); omitting it would raise `NameError: name 'wc' is
  not defined` at module import, failing collection and the `make all` gate
  before any test runs.

- Observation: `pytest-timeout`'s per-test `@pytest.mark.timeout(180)` marker
  overrides the global `timeout = 30` and is honoured under `pytest-xdist`.
  Evidence: pytest-timeout documents that the `@pytest.mark.timeout(N)` marker
  overrides the `timeout` ini value per test, and that under `pytest-xdist` the
  timeout applies per test in each worker; the existing installed e2es
  (`test_recount_e2e.py`, `test_console_scripts_e2e.py`,
  `test_per_chapter_loop_installed_bdd.py`) already rely on exactly this
  override and pass under the suite's `-n auto`. (Confirm against the
  pytest-timeout docs during implementation per the research rule.)
  Impact: the new module reuses the proven `@pytest.mark.slow` /
  `@pytest.mark.timeout(180)` pair without inventing new timeout handling.

## Decision log

- Decision (D-MODULE): host the new arms in a new module
  `tests/test_console_scripts_error_arms_e2e.py` consuming the module-scoped
  `installed_novel_state` fixture, rather than folding them into
  `test_console_scripts_e2e.py`.
  Rationale: `test_console_scripts_e2e.py` owns the all-five-scripts
  install-and-run guard and builds its own wheel in-body; the new arms only need
  one installed command and the `installed_novel_state` fixture already caches a
  built-and-installed `novel-state` at module scope. A focused new module keeps
  each module's intent coherent (AGENTS.md "structure logically"), avoids a
  second wheel build, and mirrors `test_recount_e2e.py`'s installed exit-3 shape
  exactly.
  Date/Author: 2026-06-25, planning agent.

- Decision (D-ONECMD): cross one representative installed command
  (`novel-state`), not all five.
  Rationale: 6.2.8 empirically verified both diagnostic arms are
  command-agnostic and uniform across all five read commands in-process
  (`docs/execplans/roadmap-6-2-8.md` Surprises). The arms are stamped by the
  shared `run` wrapper, not by any command body, so the subprocess boundary
  adds no per-command variance. `novel-state` is chosen because its installed
  fixture (`installed_novel_state`) already exists, so no new wheel-build
  scaffolding is needed. The all-five installed exit-3 bare path is already
  covered by `test_console_scripts_e2e.py`.
  Date/Author: 2026-06-25, planning agent.

- Decision (D-FIXTURE): reuse the module-scoped `installed_novel_state` fixture
  rather than building a wheel in the new module.
  Rationale: Constraint 7 (consume scaffolding by fixture name) and the
  module-scoped fixture pays the slow build once and shares it across all
  parametrised cases, exactly as `test_recount_e2e.py` does.
  Date/Author: 2026-06-25, planning agent.

- Decision (D-USAGE): trigger the exit-2 usage arm with an unknown option
  (`novel-state check --nope`), and the exit-3 state arm with an absent
  `working/` (`novel-state check` under a cwd with no tree).
  Rationale: an unknown option raises `CycloptsError` uniformly (6.2.8 verified
  this across all five; the design §9 names "unknown subcommand or bad arguments
  → exit 2"). The absent-`working/` variant is the §3.2 first-class exit-3
  trigger and yields a command-identical, line/column-free message
  (6.2.8 preferred it over the unparseable variant for the same reason). The
  `check` subcommand is needed because `novel-state` is a command-group app: a
  bare `novel-state` prints help and exits 0, so a read subcommand routes the
  invocation onto the real path (the same `_REAL_PATH_ARGV` reason
  `test_console_scripts_e2e.py` records, line 45).
  Date/Author: 2026-06-25, planning agent.

- Decision (D-RUNNER): supply the installed binary through a module-local
  `run_installed` **driver fixture** that closes over `single_program_catalogue`
  and `installed_novel_state`, so the helper signature is
  `_run_installed_arm(arm, tmp_path, run_installed, *, human)` — three positional
  plus one keyword-only = **four total**, the exact `max-args = 4` ceiling.
  Rationale: this resolves review blocking point B1. The round-1 helper at five
  total parameters (`arm, run_dir, installed_novel_state, build_catalogue, *,
  human`) trips Pylint `too-many-arguments` (R0913) and
  `too-many-positional-arguments`, both explicitly enabled with `max-args = 4`
  (`pyproject.toml` lines 171, 180, 297, 303); R0913 counts keyword-only
  parameters, so five total fails the mandatory `make all` -> `make lint` gate
  (the PyPy-backed Pylint pass over `tests/`, `Makefile` line 97 with
  `PYLINT_TARGETS = tests`). The fix is structural, not a suppression: it mirrors
  the in-process precedent `_drive_error_cell(cell, tmp_path, drive, *, human)`
  (matrix lines 380-417), which carries the `drive` *fixture* rather than the two
  values that fixture closes over, and computes its `run_dir` from `tmp_path`
  internally (matrix line 410). Folding the two fixtures into one driver fixture
  sheds two parameters; deriving `run_dir` from `tmp_path` sheds a third. The
  presented code blocks are therefore landable verbatim with no per-file ignore.
  Rejected alternatives: passing the cell/context as an opaque bundle (less
  readable than the named precedent) and disabling R0913 per-file (forbidden —
  the precedent passes the gate cleanly, so a suppression would diverge from the
  matrix's clean keyword-only pattern, exactly the pre-mortem failure path the
  review named).
  Date/Author: 2026-06-25, planning agent (round 2, resolving B1).

- Decision (D-SCOPE-A1): the matrix docstring's "task 6.2.4" attribution
  (`tests/test_command_surface_matrix.py` lines 42, 68-69) and
  `docs/developers-guide.md` line 121 are **knowingly left unchanged**; this task
  does not touch them.
  Rationale: review A1 flagged these as defensible-but-arguable. They are
  accurate as written: 6.2.4 owned the installed *body-produced* crossing, and
  the matrix note concerns the *in-process* matrix gap — neither claims to own
  the installed *error-arm* crossing this task adds. Touching the matrix module
  (a fourth file) would also breach the 3-file scope Tolerance and pull a code
  module into a docs reconciliation for no behavioural gain. The new coverage is
  recorded truthfully in design §9 and the developers' guide installed-e2e
  section (Work item 2), which is where a reader looks for the
  installed-boundary surface; the developers' guide line-121 sentence is about
  the matrix's in-process scope and remains correct. This is carried knowingly
  per design §9, not silently.
  Date/Author: 2026-06-25, planning agent (round 2, resolving advisory A1).

- Decision (D-NOCLASS): keep the two parametrised tests as module-level
  functions rather than grouping them under a `TestInstalledErrorArms` class.
  Rationale: CodeRabbit raised a major "group related tests into a class"
  finding, but every sibling installed-e2e module the plan mirrors —
  `tests/test_recount_e2e.py`, `tests/test_console_scripts_e2e.py`, and the
  in-process precedent `tests/test_command_surface_matrix.py` — uses plain
  module-level test functions, and no repo rule (AGENTS.md, developers' guide,
  or a `.coderabbit` config) mandates test classes. Adopting a class here would
  diverge from the established convention this module is required to mirror
  (Constraints 7, D-MODULE, D-RUNNER). The finding's companion minor point —
  self-describing assert messages — was applied in full, since it improves CI
  diagnosability without conflicting with any convention.
  Date/Author: 2026-06-25, implementation agent.

- Decision (D-NOSNAP): assert the machine envelope **in code** (skeleton +
  message prefix), not via a syrupy snapshot.
  Rationale: 6.2.8's matrix already owns the redacted machine-envelope snapshot
  for both arms in-process; the contract worth pinning at the subprocess
  boundary is that the *same* skeleton and code survive packaging, which the
  in-code assertions pin directly. A subprocess-boundary snapshot would re-pin a
  skeleton with no added signal (and audit-6.2.8 already flagged the in-process
  error-arm snapshots as near-degenerate, sub-task 6.2.8.1). If a reviewer
  requires a snapshot, redact the message field exactly as the matrix does.
  Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

To be completed at task close. Compare the result against the Purpose: the
installed binary should be observed exiting 2 (usage) and 3 (state) with the
`--human` stamp and envelope shape pinned in both modes, closing the
in-process-versus-binary asymmetry the §3.2 diagnostic arms carried after 6.2.8.

## Context and orientation

You are a novice to this repository. Here is what you need.

The harness ships five **console-scripts** (`novel-state`, `novel-done`,
`novel-compile`, `desloppify`, `wordcount`). Each is a
[Cyclopts](https://cyclopts.readthedocs.io/) app (locked at `cyclopts 4.18.0` in
[`uv.lock`](../../uv.lock)) wired in
[`novel_ralph_skill/commands/stub.py`](../../novel_ralph_skill/commands/stub.py)
and driven through a single shared wrapper, `run`, in
[`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py).
The entry-point body `_drive` (stub.py) first calls
`parse_global_flags(sys.argv[1:])` to split off the `--human` global flag
(ADR-003 §3.1), then calls `run(build_app(), residual, RunContext(command,
working_dir="working", human=…))`. Because `--human` is pre-parsed from
`sys.argv`, passing it on the installed binary's command line stamps the human
envelope even on the body-less arms.

`run` owns every `sys.exit` and every envelope emission. Two `except` arms fire
*before or instead of* a command body returning a value:

- `except CycloptsError` → emits an `ok: false` envelope with
  `ExitCode.USAGE_ERROR` (2) and exits 2 — the "unknown subcommand or bad
  arguments" arm.
- `except StateInputError` → emits an `ok: false` envelope with
  `ExitCode.STATE_ERROR` (3) and exits 3 — fired when `working/state.toml` is
  missing/unparseable or the working dir is absent.

Both arms call the same `_emit`, which renders machine (JSON) or human
(line-oriented) per `RunContext.human` and prints to **stdout**. The exit codes
live in
[`novel_ralph_skill/contract/exit_codes.py`](../../novel_ralph_skill/contract/exit_codes.py)
(`USAGE_ERROR = 2`, `STATE_ERROR = 3`). This is the §3.2 contract the harness
branches on (design table) and the §9 "CLI error-path tests" strategy.

The **installed-binary e2e** pattern you will reuse:

- The module-scoped fixture `installed_novel_state` in
  [`tests/installed_binary_fixtures.py`](../../tests/installed_binary_fixtures.py)
  (roadmap 6.2.4) builds the wheel (`uv build --wheel`), creates a fresh
  `uv venv`, installs the wheel, and returns the **absolute path** of the
  installed `novel-state` script. It is module-scoped (fed by
  `tmp_path_factory`) so the slow build runs once per consuming module and every
  test reuses the one install. It is registered as a pytest plugin through
  `pytest_plugins` in `tests/conftest.py`.
- The `single_program_catalogue` fixture in `tests/conftest.py` returns a
  builder `(name, program) -> ProgramCatalogue` for a one-project cuprum
  catalogue allowlisting exactly `program`. cuprum 0.1.0 allowlists any
  `Program` string, including an absolute path.
- The canonical installed-run shape, as
  [`tests/test_recount_e2e.py`](../../tests/test_recount_e2e.py) lines 126-134
  uses it:

  ```python
  prog = Program(str(installed_novel_state))
  catalogue = single_program_catalogue("novel-state-run", prog)
  result = sh.make(prog, catalogue=catalogue)(*argv).run_sync(
      context=ExecutionContext(cwd=run_dir), capture=True
  )
  # result.exit_code, result.stdout, result.stderr
  ```

  `run_sync(capture=True, context=ExecutionContext(cwd=…))` is the supported
  signature on the **locked installed cuprum 0.1.0** (Surprises & Discoveries —
  this differs from the local cuprum checkout; pin to the installed version).

The closest precedent for both arms together is **in-process**:
[`tests/test_command_surface_matrix.py`](../../tests/test_command_surface_matrix.py)
(task 6.2.8) crosses the exit-2 and exit-3 arms for all five read commands in
both modes, asserting the envelope skeleton (`command`, `ok: false`,
`working_dir`, `result == {}`, exactly one message) and the message prefix, with
`messages` redacted in its snapshot. This task takes the same assertions to the
**subprocess boundary** for one representative command.

Key terms: an **envelope** is the JSON object every command prints (`command`,
`schema_version`, `ok`, `working_dir`, `result`, `messages`). **Machine mode**
prints it as JSON; **human mode** prints a line-oriented rendering that begins
`command: <name>`. A **diagnostic arm** is a runner `except` block that emits an
envelope and exits before the command body returns.

## Plan of work

Two atomic, independently committable work items. Item 1 adds the test module
(self-contained: code + green gate). Item 2 reconciles the prose to match
(self-contained: docs + markdown gates). Item 1 must land first so the prose in
item 2 describes behaviour that already has a passing proof.

### Work item 1 — Add the installed-binary error-arm e2e

Implements: design §3.2 (the exit-2 and exit-3 rows of the code table); design
§9 (the "CLI error-path tests" strategy — "unknown subcommand or bad arguments →
exit 2" and "missing or unparseable `state.toml`, absent working dir → exit 3" —
and the "Installed-binary e2es" bullet that proves the exit-code contract at the
wheel/venv boundary); design §2.3 (the `command × output-mode × phase` surface
and its machine-envelope / human-presence strategy, here taken to the installed
boundary for the two diagnostic arms); ADR-003 §3.1 (the command-agnostic
`--human` splitter the arms stamp); ADR-006 (the POSIX-only installed-e2e
policy). Closes the installed half of the 6.2.8 gap (roadmap 6.2.10 success
clause; source review:6.2.8).

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §2.3, §3.2, §9 (the "CLI error-path
  tests" and "Installed-binary e2es" bullets), and §10 (a state fault yields a
  message, not a stack trace).
- `docs/adr-003-shared-interface-contract.md` (the `--human` global flag and the
  exit-code translation `run` owns).
- `docs/adr-006-console-scripts-e2e-posix-policy.md` (the POSIX-only,
  run-by-absolute-path-through-cuprum policy).
- `docs/scripting-standards.md` (every external program runs through a cuprum
  catalogue; no raw `subprocess`, no `uv run`).
- `docs/developers-guide.md` "Shared test scaffolding" (consume the installed
  fixture by name).
- `docs/execplans/roadmap-6-2-8.md` (the in-process arms this mirrors) and
  `docs/execplans/roadmap-6-2-4.md` (the `installed_novel_state` fixture).
- `tests/test_recount_e2e.py` (the installed exit-3 run shape) and
  `tests/test_console_scripts_e2e.py` (the all-five installed exit-3 guard and
  the `_REAL_PATH_ARGV` command-group reason).
- `AGENTS.md` "Python verification and testing" (snapshot discipline; unhappy
  paths; slow/timeout marks).

Skills to load:

- `python-router`, then `python-testing` (pytest parametrization, marks
  `slow`/`timeout`/`skipif`, fixtures, the boundary between unit, behavioural,
  and e2e tests).
- No property, symbolic, or mutation verification is warranted: the two arms are
  finite, enumerable, and exact (no invariant-over-a-range to fuzz, so neither
  `hypothesis` nor `crosshair`; no surviving-mutant hunt in scope, so not
  `mutmut`). Semantic assertions over a four-cell parametrize (2 arms × 2 modes)
  pin the contract directly. If `python-verification` is consulted, it confirms
  example-based assertions are the right adversary here.
- `leta` for navigation within the runner, the stub, and the existing e2e
  modules; `sem` for the history of the installed-e2e modules if needed.
- `en-gb-oxendict` for the module docstring and comments.

Concrete edits — create
[`tests/test_console_scripts_error_arms_e2e.py`](../../tests/test_console_scripts_error_arms_e2e.py):

1. Module docstring (en-GB): state that this proves the two command-agnostic
   diagnostic arms — usage (exit 2) and state (exit 3) — over a built wheel for
   the installed `novel-state`, in both output modes, asserting the `--human`
   stamp and the envelope shape, closing the installed half of the 6.2.8 gap.
   Cite design §3.2, §9, ADR-003 §3.1, ADR-006. Note POSIX-only and that the
   wheel is supplied by the module-scoped `installed_novel_state` fixture.

2. Module-level POSIX skip guard and imports:

   ```python
   pytestmark = pytest.mark.skipif(
       os.name != "posix",
       reason="installed-binary e2e is POSIX-only; see ADR 006",
   )
   ```

   Import `json`, `os`, `typing as typ`; then `pytest`, `import working_corpus
   as wc`, `from cuprum import sh`, `from cuprum.program import Program`, `from
   cuprum.sh import ExecutionContext`; then `from
   novel_ralph_skill.contract.exit_codes import ExitCode`. Under `TYPE_CHECKING`
   import `collections.abc as cabc`, `Path`, and `ProgramCatalogue` (mirroring
   `test_recount_e2e.py` lines 39-43). The `working_corpus as wc` import is
   load-bearing: steps 3 and 5 call `wc.build_working_tree(
   wc.PHASE_STATES["drafting"], run_dir)` to materialise the usage arm's real
   tree, so omitting it raises `NameError: name 'wc' is not defined` at import
   time and fails collection. Place it in the third-party/first-party group,
   after `pytest` and before the three cuprum imports, exactly as
   `tests/test_recount_e2e.py` line 30 and `tests/test_command_surface_matrix.py`
   line 88 both do (`working_corpus` is the package under `tests/` exporting
   `build_working_tree` and `PHASE_STATES`).

3. A small frozen descriptor naming the two arms, so the parametrize stays
   declarative and within the four-parameter Pylint gate the project enforces
   over `tests/` (see `docs/execplans/roadmap-6-2-8.md` Constraints — bundle
   related values into one cell rather than passing many parameters):

   ```python
   class _ErrorArm(typ.NamedTuple):
       """One command-agnostic diagnostic arm of the installed console-script."""

       label: str               # "usage" | "state"
       extra_argv: tuple[str, ...]  # appended after the read subcommand
       build_working: bool      # whether to materialise an (empty) working/ tree
       expected_code: ExitCode
       message_prefix: str

   _READ_SUBCOMMAND: tuple[str, ...] = ("check",)  # novel-state is a group app
   _USAGE_ARM = _ErrorArm(
       label="usage",
       extra_argv=("--nope",),
       build_working=True,   # a real tree so only the argv is at fault
       expected_code=ExitCode.USAGE_ERROR,
       message_prefix="Unknown option:",
   )
   _STATE_ARM = _ErrorArm(
       label="state",
       extra_argv=(),
       build_working=False,  # no working/ → exit-3 state arm
       expected_code=ExitCode.STATE_ERROR,
       message_prefix="cannot load working/state.toml",
   )
   _ARMS: tuple[_ErrorArm, ...] = (_USAGE_ARM, _STATE_ARM)
   ```

   For the usage arm, `build_working=True` materialises a real `working/` tree.
   This is for **parity, not necessity** (review A2): the usage error (exit 2)
   fires at Cyclopts parse time *before* any state load, so it would fire exit 2
   even with no tree — but building the tree isolates the fault to the argv and
   matches the 6.2.8 matrix convention exactly (matrix `_drive_error_cell`,
   `build_working` field). Build it with `wc.build_working_tree(
   wc.PHASE_STATES["drafting"], run_dir)` (the same corpus the matrix uses for
   its usage cell). The state arm builds **no** tree.

4. A **fixture-supplied installed-runner callable** `run_installed`, mirroring
   the in-process matrix's `drive` fixture exactly. This is the load-bearing
   structural decision that keeps every helper and test within the project's
   four-parameter Pylint gate (Decision D-RUNNER below; see B1). The
   `single_program_catalogue` and `installed_novel_state` fixtures are consumed
   **once** by this driver fixture, which closes over them and returns a callable
   that takes only the per-call argv; downstream the helper and tests no longer
   carry those two as parameters, exactly as `_drive_error_cell(cell, tmp_path,
   drive, *, human)` (matrix lines 380-417) carries `drive` rather than
   `monkeypatch`/`capsys`.

   Add this fixture to the new module (it is module-local, like the matrix's
   `drive` fixture):

   ```python
   @pytest.fixture
   def run_installed(
       single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
       installed_novel_state: Path,
   ) -> cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult]:
       """Return a runner for the installed ``novel-state`` over a built wheel.

       Closes over the module-scoped install and the one-program catalogue
       builder so callers pass only ``(run_dir, argv)`` — keeping every consumer
       within the four-parameter Pylint gate, mirroring the matrix ``drive``
       fixture (``tests/test_command_surface_matrix.py`` lines 380-417).
       """
       prog = Program(str(installed_novel_state))
       catalogue = single_program_catalogue("novel-state-error-arm", prog)
       builder = sh.make(prog, catalogue=catalogue)

       def _run(run_dir: Path, argv: tuple[str, ...]) -> sh.CommandResult:
           """Run ``argv`` against the installed script with ``cwd=run_dir``."""
           return builder(*argv).run_sync(
               context=ExecutionContext(cwd=run_dir), capture=True
           )

       return _run
   ```

   The catalogue and `sh.make` builder are constructed once per test (a
   one-program allowlist; cheap), and the cached install is reused. cuprum 0.1.0
   allowlists any `Program` string including an absolute path
   (`single_program_catalogue` docstring; verified Surprises & Discoveries), and
   `run_sync(*, capture, ..., context)` is the locked installed-0.1.0 signature.

5. A helper that runs one arm in one mode through the fixture-supplied runner.
   Its signature is **pinned at four total parameters** — three positional
   (`arm`, `tmp_path`, `run_installed`) plus one keyword-only (`human`) — exactly
   matching the conformant precedent `_drive_error_cell(cell, tmp_path, drive, *,
   human)`. This is verified-landable: `max-args = 4` in `pyproject.toml` (lines
   171, 180) and Pylint's `too-many-arguments` (R0913, line 297) and
   `too-many-positional-arguments` (line 303) count keyword-only parameters, so
   four total is the ceiling and this hits it exactly:

   ```python
   def _run_installed_arm(
       arm: _ErrorArm,
       tmp_path: Path,
       run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
       *,
       human: bool,
   ) -> sh.CommandResult:
       """Drive one diagnostic arm in one output mode over the installed binary.

       Derives ``run_dir`` from ``tmp_path`` internally (dropping it as a
       parameter), so the signature lands at four total — three positional plus
       one keyword-only — within the Pylint argument-count gate.
       """
       run_dir = tmp_path / arm.label
       run_dir.mkdir(exist_ok=True)
       if arm.build_working:
           wc.build_working_tree(wc.PHASE_STATES["drafting"], run_dir)
       human_prefix = ("--human",) if human else ()
       argv = (*human_prefix, *_READ_SUBCOMMAND, *arm.extra_argv)
       return run_installed(run_dir, argv)
   ```

   Deriving `run_dir` from `tmp_path` inside the helper (rather than passing it)
   is the param-shedding move B1 asked for; it mirrors `_drive_error_cell`, which
   computes `root = tmp_path / arm.label` internally (matrix line 410). No Ruff
   per-file ignore or Pylint disable is needed or permitted; re-verify with
   `make lint` (the PyPy-backed Pylint pass over `tests/`), not merely Ruff,
   because the Ruff config does not silence the separate Pylint pass.

6. The machine-mode test, parametrised over `_ARMS` with
   `ids=[arm.label for arm in _ARMS]`. It consumes the `run_installed` driver
   fixture (and `tmp_path`), so it carries exactly three parameters — well within
   the four-parameter gate:

   ```python
   @pytest.mark.slow
   @pytest.mark.timeout(180)
   @pytest.mark.parametrize("arm", _ARMS, ids=[a.label for a in _ARMS])
   def test_installed_error_arm_machine_envelope(
       arm: _ErrorArm,
       tmp_path: Path,
       run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
   ) -> None:
       ...
   ```

   Run the arm via `_run_installed_arm(arm, tmp_path, run_installed,
   human=False)`; assert
   `result.exit_code == arm.expected_code` (with `result.stderr` in the message
   so a fault surfaces); `"Traceback" not in (result.stderr or "")` (design §10
   — a fault yields a message, not a stack trace); `envelope =
   json.loads(result.stdout or "{}")`; then the skeleton: `envelope["command"]
   == "novel-state"`, `envelope["ok"] is False`, `envelope["working_dir"] ==
   "working"`, `envelope["result"] == {}`; `messages = envelope["messages"]`
   with `len(messages) == 1` (pin the count, mirroring 6.2.8 advisory A1) and
   `messages[0].startswith(arm.message_prefix)`.

7. The human-mode presence test, parametrised over `_ARMS`, likewise consuming
   the `run_installed` driver fixture (three parameters):

   ```python
   @pytest.mark.slow
   @pytest.mark.timeout(180)
   @pytest.mark.parametrize("arm", _ARMS, ids=[a.label for a in _ARMS])
   def test_installed_error_arm_human_stamp(
       arm: _ErrorArm,
       tmp_path: Path,
       run_installed: cabc.Callable[[Path, tuple[str, ...]], sh.CommandResult],
   ) -> None:
       ...
   ```

   Run via `_run_installed_arm(arm, tmp_path, run_installed, human=True)`; assert
   `result.exit_code == arm.expected_code`; `rendered = (result.stdout or
   "").strip()`; assert `rendered` is non-empty and `"novel-state" in rendered`
   and `rendered.startswith("command: novel-state")` — the `--human` stamp
   reaches the body-less arm across the subprocess boundary (the §3.2 / ADR-003
   §3.1 point this task anchors). Then **assert (mandatory)
   `arm.message_prefix in rendered`** so the human rendering carries the
   diagnostic, not merely the header — both arms' human output carries the
   message (verified in-process; review A3 promoted this from optional to
   required because it is the only assertion distinguishing this test from a bare
   header check).

Tests this work item adds (per AGENTS.md testing rules):

- End-to-end (`@pytest.mark.slow`) installed-binary tests: a four-cell matrix (2
  arms × 2 output modes) over a real console-script built into a throwaway venv.
  The machine cells pin the envelope skeleton, the message count, the message
  prefix, and the exit code; the human cells pin the `--human` stamp, the
  message prefix in the rendering (review A3, mandatory), and the exit code.
  These are the "unhappy path" and "externally observable
  command-line behaviour" coverage AGENTS.md requires.
- No syrupy snapshot is added (Decision D-NOSNAP): the in-process matrix already
  owns the redacted error-arm snapshot, and the in-code assertions pin the
  boundary contract directly.
- No property, behavioural (`pytest-bdd`), or unit test is added: the arms are
  finite and exact (no range invariant → no `hypothesis`/`crosshair`); the
  behavioural per-chapter-loop installed scenarios are task 6.2.9's scope; this
  is e2e by design.

Validation:

```plaintext
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10
uv run pytest -v tests/test_console_scripts_error_arms_e2e.py -m slow
make all
```

Expected: the four installed-binary cells pass (2 machine + 2 human); the wheel
is built once for the module and reused across all cells; `make all` (build,
check-fmt, lint, typecheck, test) is green. The new tests fail before the module
exists and pass after. Commit message (file-based, en-GB): "Cross the installed
exit-2/exit-3 error arms over a built wheel".

Acceptance: `make all` passes; `uv run pytest
tests/test_console_scripts_error_arms_e2e.py -m slow` reports 4 passed; the
installed `novel-state` is observed exiting 2 on an unknown option and 3 on an
absent `working/`, each with `ok: false`, the named command, `result: {}`, one
message, and (in human mode) a `command: novel-state` header.

### Work item 2 — Reconcile design §9 and the developers' guide

Implements: design §9 (the "Installed-binary e2es" bullet and the
"carried knowingly rather than silently" principle — the prose must describe the
new boundary coverage so the surface description matches reality); ADR-003 (the
`--human` stamp now proven at the boundary); the project docs-as-source-of-truth
rule. Keeps living documentation truthful.

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §9 "Installed-binary e2es" bullet (lines
  ~834-848) — the bullet that lists the installed proofs (`check`, `desloppify`,
  `novel-done`, `recount`) and must now record the two command-agnostic
  diagnostic arms at the boundary.
- `docs/developers-guide.md` "Shared test scaffolding" / installed-e2e
  conventions (the section describing `installed_novel_state` and the installed
  e2es) — add a sentence naming the new error-arm module and its coverage.
- `docs/execplans/roadmap-6-2-8.md` (the in-process arms' description, to keep
  the in-process/installed wording symmetric).

Skills to load:

- `en-gb-oxendict` (Oxford spelling).
- `leta` to locate the prose sites; no router skill is needed for a docs-only
  change.

Concrete edits:

1. In `docs/novel-ralph-harness-design.md` §9 "Installed-binary e2es" bullet:
   add a sentence stating that the two command-agnostic diagnostic arms — the
   usage error (exit 2) and the state-or-input error (exit 3) the runner stamps
   before any command body runs — are now also proven at the installed boundary:
   the installed `novel-state` exits 2 on a malformed invocation and 3 on an
   absent `working/`, each in machine and human mode, with the `--human` stamp
   and the `ok: false` envelope shape pinned, closing the in-process-versus-
   binary asymmetry left after the matrix slice (6.2.8). Wrap at 80 columns.

2. In `docs/developers-guide.md` (the installed-e2e conventions section): add a
   sentence naming `tests/test_console_scripts_error_arms_e2e.py` as the home
   for the installed command-agnostic error-arm proofs, consuming the
   `installed_novel_state` and `single_program_catalogue` fixtures and carrying
   the `slow` / `timeout(180)` / POSIX-`skipif` marks like the other installed
   e2es. Wrap at 80 columns.

Tests this work item adds: none (docs-only). The behaviour the prose describes
is already pinned by Work item 1's tests.

Validation:

```plaintext
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10
make markdownlint
make nixie
make all
```

Expected: `make markdownlint` and `make nixie` pass over the updated design and
guide; `make all` stays green (docs-only change). Commit message (file-based,
en-GB): "Record the installed error-arm coverage in design §9 and the guide".

Acceptance: design §9 and the developers' guide both describe the installed
exit-2/exit-3 command-agnostic arm coverage with the `--human` stamp and
envelope shape; neither understates it as a carried gap; `make markdownlint`,
`make nixie`, and `make all` all pass.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10`.

1. Confirm the branch and a clean tree:

   ```plaintext
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10 branch --show-current
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-10 status
   ```

   Expect branch `roadmap-6-2-10` and a clean working tree (this plan aside).

2. Work item 1: create `tests/test_console_scripts_error_arms_e2e.py` per the
   plan, then:

   ```plaintext
   uv run pytest -v tests/test_console_scripts_error_arms_e2e.py -m slow
   make all
   ```

   Commit (gate first; file-based message).

3. Work item 2: edit design §9 and `docs/developers-guide.md`, then:

   ```plaintext
   make markdownlint
   make nixie
   make all
   ```

   Commit (gate first; file-based message).

4. Tick roadmap task 6.2.10 in `docs/roadmap.md` only if the workflow's
   merge/audit step expects the implementer to do so; otherwise leave the
   roadmap to the orchestration.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `uv run pytest tests/test_console_scripts_error_arms_e2e.py -m slow`
  reports 4 passed (2 machine + 2 human); the tests fail before the module
  exists and pass after. The full `make test` suite stays green.
- Lint/typecheck/format/test: `make all` is green (including the PyPy-backed
  Pylint argument-count gate over `tests/` — re-verify the helper/test
  signatures stay within four parameters).
- Markdown: `make markdownlint` and `make nixie` pass over the updated design §9
  and developers' guide.
- No production code under `novel_ralph_skill/` is touched.

Quality method (how we check):

- Run `make all` after Work item 1 and again after Work item 2.
- Run `make markdownlint` and `make nixie` after Work item 2.
- Inspect the test output to confirm the installed binary exited 2 (usage) and 3
  (state), each in both modes, with the asserted envelope skeleton and `--human`
  stamp.

Behavioural acceptance a human can verify: build the wheel, install it into a
fresh venv, and run the installed `novel-state` by absolute path. From a
directory with a real `working/` tree, `novel-state check --nope` exits 2 and
prints an `ok: false` envelope naming the command with message beginning
`Unknown option:`. From a directory with no `working/`, `novel-state check`
exits 3 and prints an `ok: false` envelope with message beginning
`cannot load working/state.toml`. Prepending `--human` to either renders a
line-oriented report beginning `command: novel-state`. The new module asserts
exactly this.

## Idempotence and recovery

- All steps are re-runnable. The module-scoped `installed_novel_state` fixture
  rebuilds the wheel per session under a fresh `tmp_path_factory` directory, so
  reruns do not drift.
- No production code or persistent state is touched, so there is nothing to roll
  back beyond `git checkout` of the new test module and the two edited docs.
- If a slow e2e flakes on timeout, confirm `@pytest.mark.timeout(180)` is on the
  test (it overrides the global 30 s under `-n auto`) before assuming a real
  failure; re-run the single module with `-m slow`.

## Interfaces and dependencies

- Test framework: `pytest` with the `slow`/`timeout`/`skipif` marks, the
  module-scoped `installed_novel_state` fixture
  ([`tests/installed_binary_fixtures.py`](../../tests/installed_binary_fixtures.py)),
  and the `single_program_catalogue` fixture (`tests/conftest.py`).
- New module-local driver fixture `run_installed(single_program_catalogue,
  installed_novel_state) -> Callable[[Path, tuple[str, ...]], sh.CommandResult]`
  (Decision D-RUNNER): closes over the two consumed fixtures so the helper and
  tests carry at most four parameters, mirroring the matrix's `drive` fixture.
  Its returned callable takes `(run_dir, argv)`.
- Helper `_run_installed_arm(arm: _ErrorArm, tmp_path: Path, run_installed:
  Callable[[Path, tuple[str, ...]], sh.CommandResult], *, human: bool) ->
  sh.CommandResult` — pinned at four total parameters (three positional + one
  keyword-only); derives `run_dir` from `tmp_path` internally.
- cuprum (locked `cuprum==0.1.0`, `uv.lock` lines 113-118), pinned against the
  **installed** version (not the local checkout — Surprises & Discoveries):
  - `cuprum.program.Program(str(path))` — an absolute-path program, allowlisted
    by a one-project `ProgramCatalogue`/`ProjectSettings` (verified: an
    absolute-path program runs through the allowlist).
  - `cuprum.sh.make(program, *, catalogue) -> builder`; `builder(*argv) ->
    SafeCmd`.
  - `SafeCmd.run_sync(*, capture: bool = True, echo: bool = False, context:
    ExecutionContext | None = None) -> CommandResult` — this is the locked
    0.1.0 signature (verified by `inspect.signature` in the worktree venv); the
    plan uses `run_sync(context=ExecutionContext(cwd=run_dir), capture=True)`.
  - `cuprum.sh.ExecutionContext(cwd=run_dir)` — the `cwd` field exists on the
    installed 0.1.0 (verified).
  - `CommandResult.exit_code: int`, `.stdout: str | None`, `.stderr: str | None`
    (verified fields).
- Runner under test (unchanged): `novel_ralph_skill.contract.runner.run` and its
  `except CycloptsError` / `except StateInputError` arms;
  `novel_ralph_skill.contract.exit_codes.ExitCode` (`USAGE_ERROR == 2`,
  `STATE_ERROR == 3`).
- Cyclopts (locked `cyclopts 4.18.0`): raises `CycloptsError` on an unknown
  option (the runner's `except CycloptsError` arm maps it to exit 2; the message
  wording is Cyclopts's, hence asserted by prefix only). Confirm the
  `--help`/`--version` and unknown-option behaviour against the Cyclopts docs
  during implementation per the research rule, but the load-bearing claim —
  unknown option → `CycloptsError` → exit 2 — is already pinned by the
  in-process matrix (6.2.8) and re-pinned here at the boundary.
- Corpus: `working_corpus.build_working_tree` / `PHASE_STATES["drafting"]` for
  the usage arm's real tree; no tree for the state arm.

No new module under `novel_ralph_skill/`, no new public API, no new dependency
is introduced. The only new file is the test module; the only edited files are
design §9 and the developers' guide.

## Revision note

Round 3 (2026-06-25), resolving the design review (round 2):

- What changed: step 2 of Work item 1 (the new module's import list) now
  includes `import working_corpus as wc`, placed in the third-party/first-party
  group after `pytest` and before the three cuprum imports, exactly as
  `tests/test_recount_e2e.py` line 30 and `tests/test_command_surface_matrix.py`
  line 88 place it. A new Surprises entry pins the verified precedent and the
  `working_corpus` exports (`build_working_tree`, `PHASE_STATES`).
- Why it changed: round 1 (round-2 numbering) blocking point B2 — the round-2
  import list omitted `working_corpus`, yet step 3 (`_USAGE_ARM` tree build) and
  step 5 (`_run_installed_arm` body) both call `wc.build_working_tree(
  wc.PHASE_STATES["drafting"], run_dir)`. A novice following the import list
  verbatim would hit `NameError: name 'wc' is not defined` at import, failing
  collection and the plan's own `make all` gate before any test ran.
- How it affects remaining work: none structurally — Work item 1's code blocks
  are now importable verbatim, and Work item 2 (docs) is unchanged. The 3-file
  Tolerance and all other constraints stand. The Interfaces section already
  named the `working_corpus.build_working_tree`/`PHASE_STATES` dependency; the
  fix makes the import explicit in the construction steps.

Round 2 (2026-06-25), resolving the design review (round 1):

- What changed: the primary helper signature was restructured to be
  gate-conformant. Round 1 presented `_run_installed_arm(arm, run_dir,
  installed_novel_state, build_catalogue, *, human)` (five total parameters) with
  only a vague menu of ways to shrink it. Round 2 pins one concrete shape:
  a module-local `run_installed` **driver fixture** that closes over
  `single_program_catalogue` and `installed_novel_state`, plus a helper
  `_run_installed_arm(arm, tmp_path, run_installed, *, human)` (three
  positional + one keyword-only = four total) that derives `run_dir` from
  `tmp_path` internally. Both parametrised tests now consume `run_installed`
  (three parameters each). New Decision D-RUNNER, a new Surprises entry pinning
  the verified `max-args = 4` / R0913 keyword-only-counting fact, and Interfaces
  signatures were added. The advisory points were also folded in: A2 (the usage
  arm's tree is for parity, not necessity — stated plainly in step 3), A3 (the
  human-mode `message_prefix in rendered` assertion promoted from optional to
  mandatory), and A1 (the stale 6.2.4-attribution prose consciously left out of
  scope via Decision D-SCOPE-A1, keeping the 3-file Tolerance).
- Why it changed: the round-1 helper would have failed `make all` -> `make lint`
  (the PyPy-backed Pylint pass over `tests/`, which enables `too-many-arguments`
  and `too-many-positional-arguments` with `max-args = 4` and counts keyword-only
  parameters), so the presented code was not landable verbatim — the review's
  blocking point B1.
- How it affects remaining work: Work item 1's code blocks are now landable
  verbatim with no per-file ignore or Pylint disable, mirroring the conformant
  in-process precedent `_drive_error_cell`. Work item 2 (docs) is unchanged in
  scope. The 3-file Tolerance and all other constraints stand.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge review of step 6.2 (`review:6.2.10`). Execute each as a small
addendum pass — no plan or design-review cycle: make the change, run `make all`
(plus `make markdownlint`/`make nixie` for Markdown), `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge. Both are small
extensions to this task's installed error-arm proof; the substantial,
cross-cutting follow-ups raised against step 6.2 were re-routed off this task
(the reconciliation payload projection to new roadmap step 7.26, the
ROLLBACK-trigger basename corpus constants to roadmap task 7.23.8).

- [x] 6.2.10.1 — Cross the installed error arms over a second installed command
  as a command-sensitivity tripwire (from review:6.2.10, low). Decision D-ONECMD
  crosses only `novel-state` on the empirical 6.2.8 finding that the arms are
  command-agnostic (stamped by the shared run wrapper, not command bodies);
  extend the installed error-arm matrix to a second installed command (e.g.
  `desloppify`, which already has an installed fixture) so a future change making
  the runner's arms command-sensitive — a command overriding `--human` pre-parse
  or the `working_dir` default — is caught rather than silently uncovered. Gate
  with `make all`.
- [x] 6.2.10.2 — Pin `schema_version` (and field order) at the installed-binary
  boundary for the diagnostic arms (from review:6.2.10, low). The in-process
  matrix pins the full envelope including `schema_version` via snapshot, but the
  installed-boundary error-arm proofs assert only the
  command/ok/working_dir/result/messages skeleton; add a `schema_version`
  assertion (or a redacted boundary snapshot) so the boundary proof is a complete
  mirror of the in-process contract and a schema-version bump or field-order
  regression cannot survive packaging unobserved at the subprocess boundary. Gate
  with `make all`.
