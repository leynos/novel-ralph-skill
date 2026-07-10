# Post-merge audit: roadmap task 6.2.4

Audit of the codebase after roadmap task 6.2.4 ("broaden installed-binary e2e
coverage", commit `9c63253`) merged to `main`. The task extended the
installed-binary end-to-end suite to cover `novel-state recount` (exit 0) and
its exit-3 state-error paths, and extracted a module-scoped
`installed_novel_state` fixture into the new plugin module
`tests/installed_binary_fixtures.py`.

The change is sound and well-documented. The findings below are pre-existing
duplication that task 6.2.4 partially addressed for one binary and inadvertently
extended, plus a few smaller consistency and coverage gaps. None block the merge.

Sources relied on: `docs/developers-guide.md` ("Shared test scaffolding"),
`docs/novel-ralph-harness-design.md` (§9 installed-binary criteria),
`docs/adr-006-console-scripts-e2e-posix-policy.md`, `AGENTS.md` (module and
local-variable caps, bare-`assert` policy), and the `python-router` /
`python-testing` skills. Code navigated with `leta`; history traced with `git
show` over commit `9c63253`.

## Finding 1: Wheel-build/venv-install logic duplicated across six e2e sites

- **Category:** duplication
- **Severity:** high
- **Location:** `tests/installed_binary_fixtures.py:92` (`installed_novel_state`);
  `tests/test_ai_isms_e2e.py:118` (`_build_and_install`);
  `tests/test_desloppify_e2e.py:58` (`_build_and_install_desloppify`);
  `tests/test_novel_done_e2e.py:58` (`_build_and_install_novel_done`);
  `tests/test_wordcount_e2e.py:42` (`_build_and_install_wordcount`).

The body that (1) builds a wheel with `uv build --wheel <project> --out-dir`,
(2) asserts exactly one `*.whl`, (3) creates a fresh `uv venv`, (4) resolves the
scripts directory, (5) `uv pip install`s the wheel, and (6) asserts the named
console-script exists, is copy-pasted across at least five modules. The five
copies differ only in the console-script name string (`novel-state`,
`desloppify`, `novel-done`, `wordcount`) and the catalogue project label. Task
6.2.4 correctly recognized this as scaffolding and extracted it into
`installed_novel_state`, but only for the `novel-state` binary, leaving the four
other copies in place and adding a sixth instance of the build/install body.

The `docs/developers-guide.md` "Shared test scaffolding" rule states plainly:
"New shared scaffolding belongs in `tests/conftest.py` as another fixture rather
than a fresh copy in each module." A per-binary build/install fixture is exactly
such scaffolding.

- **Proposed fix:** Promote the build/install body to a single
  binary-parametrized helper in the `installed_binary_fixtures` plugin — e.g. a
  module-scoped fixture factory `installed_console_script(script_name: str) ->
  Path`, or a plain `_build_and_install(tmp_path, script_name) -> Path` helper
  the per-binary fixtures call. Replace the `installed_novel_state`,
  `installed_desloppify`, `_build_and_install_desloppify`,
  `_build_and_install_novel_done`, and `_build_and_install_wordcount` bodies with
  one-line delegations naming their binary. This collapses five near-identical
  bodies to one and makes `installed_novel_state` a thin alias.

## Finding 2: New plugin re-inlines two existing conftest fixtures

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/installed_binary_fixtures.py:43` (`_one_program_catalogue`,
  a copy of `single_program_catalogue` in `tests/conftest.py:246`) and
  `tests/installed_binary_fixtures.py:76` (`_venv_scripts_dir`, a copy of
  `venv_scripts_dir` in `tests/conftest.py:278`). `tests/test_ai_isms_e2e.py`
  carries the same two copies (`_one_program_catalogue`, `_scripts_dir`).

The new plugin's docstring (lines 21-25) acknowledges the duplication and
justifies it on a real `ScopeMismatch` constraint: a module-scoped fixture
cannot request a function-scoped one. The justification is correct, but the
remedy chosen — copy the body — re-creates exactly the duplication the
"Shared test scaffolding" rule was written to prevent, and now in three places
(both conftest fixtures, the `installed_binary_fixtures` copies, and the
`test_ai_isms_e2e` copies).

- **Proposed fix:** Extract the two pure builders to module-level functions
  (e.g. `build_one_program_catalogue(name, program)` and
  `resolve_venv_scripts_dir(venv_dir)`) in a small shared helper module that both
  `conftest` fixtures and the module-scoped fixtures import. The function-scoped
  `single_program_catalogue` / `venv_scripts_dir` fixtures then become one-line
  wrappers returning the shared function, and the module-scoped fixtures call the
  same function directly — no `ScopeMismatch`, no copied body. (Importing a pure
  *function* from a shared helper module is distinct from the forbidden
  cross-module *fixture-value* import; the rule targets the latter.)

## Finding 3: "Run installed script under a cwd" pattern repeated verbatim

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/test_recount_e2e.py:128-132` and `178-182`;
  `tests/test_reconcile_e2e.py:215-220` and `261-266`;
  `tests/test_novel_state_check.py:331-335`;
  `tests/test_wordcount_e2e.py:98-102`;
  `tests/test_desloppify_e2e.py:116` and `147`;
  `tests/test_novel_done_e2e.py:88` (`_run_in`).

The four-line incantation `prog = Program(str(script)); catalogue =
single_program_catalogue(label, prog); result = sh.make(prog,
catalogue=catalogue)(*args).run_sync(context=ExecutionContext(cwd=dir),
capture=True)` recurs roughly a dozen times across the installed-binary suite.
`test_novel_done_e2e.py` already extracted it as `_run_in`; the `recount` and
`reconcile` modules added in 6.2.4 spell it out inline twice each instead of
reusing that shape.

- **Proposed fix:** Add one shared helper to the `installed_binary_fixtures`
  plugin — e.g. `run_installed(script: Path, catalogue_builder, *args, cwd: Path)
  -> CommandResult` — and have the recount, reconcile, check, wordcount,
  desloppify, and novel-done e2es call it. This also centralizes the
  `capture=True` / `ExecutionContext` choice so a future change to the run
  convention touches one site.

## Finding 4: Inconsistent fixture scope between the new and existing e2e builds

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `tests/installed_binary_fixtures.py:92` (module-scoped) and
  `tests/test_ai_isms_e2e.py:152` (`installed_desloppify`, module-scoped) versus
  `tests/test_wordcount_e2e.py:91`, `tests/test_novel_done_e2e.py:110`,
  `tests/test_desloppify_e2e.py:106` (function-scoped `_build_and_install_*`
  called once per test).

Task 6.2.4 and the `ai-isms` suite build the wheel once per module
(module-scoped fixture); `wordcount`, `novel-done`, and the flag-offender
`desloppify` e2es rebuild the wheel for every test function. With multiple cases
per module, the function-scoped modules pay the slow wheel build several times
over. The harness design (§9) and the new `installed_novel_state` docstring both
state the build "is the slow part", so the per-test rebuild is a measurable cost
the module-scoped approach already avoids.

- **Proposed fix:** Once Finding 1 lands, route all installed-binary e2es through
  one module-scoped fixture factory so every module builds the wheel exactly
  once. This converges the scope convention and removes the redundant rebuilds.

## Finding 5: Bare-`assert` versus `AssertionError` split between plugin and test helpers

- **Category:** inconsistency
- **Severity:** low
- **Location:** `tests/installed_binary_fixtures.py:64-73` (`_run_ok` raises
  `AssertionError`) versus the `_build_and_install_*` helpers in
  `tests/test_wordcount_e2e.py:56-68`, `tests/test_novel_done_e2e.py:72-84`,
  etc. (bare `assert`).

`tests/installed_binary_fixtures.py` is inside `PYTHON_TARGETS`, so it must raise
`AssertionError` directly (no bare `assert`, per `AGENTS.md` and `conftest`'s own
docstring); the `test_*.py` build/install helpers get `per-file-ignores` relief
and use bare `assert`. This is the intended policy split, but it means the
otherwise-identical build/install bodies cannot be literally shared without the
guard style diverging. The fix for Finding 1 should standardize on raising
`AssertionError` (the stricter form) so the single shared body lives correctly in
the plugin regardless of which module consumes it.

- **Proposed fix:** When consolidating per Finding 1, write the shared helper to
  raise `AssertionError` (as `_run_ok` already does) rather than bare `assert`,
  so it satisfies the `PYTHON_TARGETS` gate from its plugin home, and the
  policy split becomes a non-issue.

## Finding 6: Installed-binary failure-mode coverage is asymmetric across mutators

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_recount_e2e.py:150`
  (`test_installed_novel_state_recount_state_error_exits_three`) versus
  `tests/test_reconcile_e2e.py` (no installed exit-3 case) and
  `tests/test_wordcount_e2e.py` (no installed exit-3 case).

Task 6.2.4 added a welcome installed exit-3 (missing / unparseable `state.toml`)
proof for `recount`, but `reconcile` and `wordcount` — which share the same
state-input boundary and exit-3 contract (design §3.2, ADR-003 Table 2) — still
have only happy-path installed proofs. The in-process suites cover the exit-3
path for these commands, so the installed gap is narrow, but it is an asymmetry
worth recording: the harness branches on the *installed* exit code for every
command, not just `recount`.

- **Proposed fix:** Add a parametrized installed exit-3 case (missing and
  unparseable `state.toml`) to `test_reconcile_e2e.py` and `test_wordcount_e2e.py`,
  mirroring `test_installed_novel_state_recount_state_error_exits_three`. Once
  Finding 3's `run_installed` helper exists, each addition is a few lines.

## Finding 7: `installed_binary_fixtures` naming undersells its single-binary scope

- **Category:** ergonomics
- **Severity:** low
- **Location:** `tests/installed_binary_fixtures.py` (module name) and the
  `pytest_plugins` registration in `tests/conftest.py:55-61`.

The plugin module is named `installed_binary_fixtures` (plural, generic), but it
currently exposes exactly one fixture for one binary (`installed_novel_state`).
The generic name is the right destination for the Finding 1 consolidation, but
until then it overstates the module's reach and risks a reader expecting the
other binaries' fixtures to live there too.

- **Proposed fix:** Land Finding 1 so the module genuinely hosts the shared
  installed-binary scaffolding for all four console-scripts, fulfilling the name.
  If Finding 1 is deferred, add a one-line module-docstring note that the plugin
  is the intended future home for the other binaries' installed fixtures.
