# Post-merge audit — roadmap task 1.2.3

Audit of the codebase after roadmap task 1.2.3 ("Decide and enforce a
cross-platform policy for the console-scripts e2e test") merged to `main` at
commit `a7e1dec`. Primary scope is the code and documentation introduced or
touched by that task: the rewritten `tests/test_console_scripts_e2e.py`, the new
`tests/test_venv_scripts_dir.py`, ADR-006
(`docs/adr-006-console-scripts-e2e-posix-policy.md`), and the developer-guide and
design references that point at the new POSIX-only policy. The audit also
re-checks whether the findings carried in `docs/issues/audit-1.2.1.md` and
`docs/issues/audit-1.2.2.md` have been actioned, since the surface is still small
enough that carrying them forward is cheap.

Each finding records a category, a location, a description, a concrete proposed
fix, and a severity. None is a blocking defect; the merged slice is correct (the
broken `win32` branch is removed, the resolver now points at the venv `bin/`
directory, and the skip guard makes the contract honest), well tested, and well
documented. They are tidy-up opportunities, plus several prior-audit items that
remain open and now have explicit roadmap homes (1.2.4, 1.2.5).

## Finding 1 — Cuprum catalogue boilerplate is now built three times across two test modules

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_console_scripts_e2e.py:48` (module-level
  `_CATALOGUE`), `tests/test_console_scripts_e2e.py:128` (per-command catalogue
  inside the loop), `tests/test_venv_scripts_dir.py:37` (resolver-test
  catalogue)

This slice introduced a second copy of the same six-line `ProgramCatalogue` /
`ProjectSettings` construction shape and left a third in place. All three wrap a
single `Program` in a `ProjectSettings` with empty `documentation_locations` and
`noise_rules` and a one-off project `name`, differing only in that name and the
program. The pattern is the scripting-standards-mandated cuprum allowlisting
idiom, so it will recur every time a test needs to run a program; building it by
hand each time invites drift (an inconsistent `name`, a forgotten empty tuple)
and obscures the one line that actually varies. The new resolver-test module
(`test_venv_scripts_dir.py`) only needs a catalogue to run `uv venv`, yet it
re-derives the whole structure rather than reusing the e2e module's `_CATALOGUE`.

**Proposed fix:** add a small helper — naturally in the `tests/conftest.py` that
audit-1.2.1 Finding 3 already proposes — for example
`def single_program_catalogue(program: Program, name: str) -> ProgramCatalogue`
that fills the empty `documentation_locations`/`noise_rules` tuples, and have all
three sites call it. This keeps the cuprum allowlisting discipline in one place
and reduces each call site to the program and a name. Fold this into the
`tests/conftest.py` work when task 1.2.4 or 1.2.5 first touches the test surface.

## Finding 2 — The venv-scripts resolver lives in a test module and is imported across test files

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `tests/test_console_scripts_e2e.py:76` (`_venv_scripts_dir`
  defined as a private function), `tests/test_venv_scripts_dir.py:18`
  (`from tests.test_console_scripts_e2e import _venv_scripts_dir`)

`_venv_scripts_dir` is reusable, behaviour-bearing logic — it resolves the venv
`bin/` directory through the canonical `venv` sysconfig scheme — yet it lives as
a leading-underscore private function inside one test module, and a second test
module reaches across the package boundary to import that private name. ADR-006's
technical requirement ("the venv-scripts directory resolves through the canonical
sysconfig scheme") describes a contract worth owning in one place, but the
current home makes the function look like test-local scaffolding while
`test_venv_scripts_dir.py` treats it as a shared API. Importing a `_`-prefixed
symbol from a sibling test module is fragile: it couples the two files, defeats
the privacy the underscore signals, and breaks silently if either module is
renamed or the resolver is moved. This coupling is new with this slice (the
resolver test did not exist before 1.2.3).

**Proposed fix:** move `_venv_scripts_dir` to a shared, non-private home and
import it from there in both modules. The lightest option is a public
`venv_scripts_dir` helper in `tests/conftest.py` (or a `tests/_helpers.py`
module) so neither test reaches into the other. If the resolver is judged to be
production-adjacent rather than test-only, a follow-up could host it in the
package proper; for now a shared test helper removes the cross-module private
import while keeping the change test-scoped. Pair this with Finding 1 so the
catalogue helper and the resolver land in the same shared module.

## Finding 3 — `test_resolver_is_posix_shaped` asserts a value the skip guard already fixes

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_venv_scripts_dir.py:65`
  (`test_resolver_is_posix_shaped`), with the module-level
  `pytestmark = pytest.mark.skipif(os.name != "posix", …)` at `:25`

The module is skipped outwith POSIX, and the `venv` sysconfig scheme returns
`bin` on every POSIX platform by construction, so `test_resolver_is_posix_shaped`
asserts `scripts_dir.name == "bin"` only on platforms where it cannot be anything
else. The test therefore re-states the skip-guard precondition rather than
catching a regression: the realistic failure modes it should guard against — a
future edit that re-introduces a `win32`/`Scripts` branch, or that drops the
explicit `venv` scheme and falls back to the running interpreter's scheme — are
exactly the cases the skip guard hides from this assertion. The companion test
`test_resolver_points_at_venv_bin` is stronger because it asserts the resolved
directory lives inside the venv and contains a `python` launcher, which a wrong
scheme would break.

**Proposed fix:** either fold the `bin` check into
`test_resolver_points_at_venv_bin` (one POSIX-shape assertion alongside the
inside-the-venv assertions) and drop the near-tautological standalone test, or
strengthen it to pin the resolver's intent directly — for example assert that the
resolved path equals the `venv`-scheme `scripts` path and is *not* the running
interpreter's default scheme — so it would fail if the explicit `venv` scheme
argument were removed. The aim is a test that catches the re-introduction of the
defect ADR-006 was written to prevent, not one that restates `os.name`.

## Finding 4 — Five command names now duplicated across a fourth test surface; prior-audit items still open

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/test_command_stubs.py:23` and
  `tests/test_console_scripts_e2e.py:60` (two hand-written `COMMAND_NAMES`
  tuples), `tests/test_pyproject_scripts.py:17` (`EXPECTED_SCRIPTS` keys),
  `novel_ralph_skill/commands/stub.py` (five `def` entry points plus name
  literals), `pyproject.toml` `[project.scripts]`; no `tests/conftest.py`

The five command names — `novel-state`, `novel-done`, `novel-compile`,
`desloppify`, `wordcount` — remain hand-written across the stub module,
`pyproject.toml`, and three test modules, exactly as audit-1.2.1 Finding 1 and
audit-1.2.2 Finding 4 recorded. This slice did not add a copy (the rewritten e2e
module kept its existing `COMMAND_NAMES`), but it confirms the drift surface is
unchanged while a fourth module (`test_venv_scripts_dir.py`) was added without a
shared fixture home, and there is still no `tests/conftest.py`. Roadmap task
1.2.4 ("a single source of truth for the five command names") now owns the
registry, and audit-1.2.1 Finding 3 owns the shared project-root/command-name
fixture; both remain unactioned at this commit. The cheapest moment to land the
registry is still while the surface is five thin stubs.

**Proposed fix:** action roadmap task 1.2.4: introduce a single command-name
registry in `novel_ralph_skill.commands.stub`, derive the `[project.scripts]`
assertion and the test `COMMAND_NAMES` from it via a new `tests/conftest.py`, and
host the shared `_PROJECT_ROOT` value (audit-1.2.1 Finding 3) in the same
conftest. No new work is required of this audit beyond confirming the items are
still open and live in the roadmap.

## Finding 5 — `interrogate` remains installed but unconfigured and ungated

- **Category:** test-gap
- **Severity:** low
- **Location:** `pyproject.toml` (`interrogate` under `[dependency-groups].dev`;
  no `[tool.interrogate]` block, no Makefile target, no CI step in
  `.github/workflows/ci.yml`)

`interrogate` is still a dev dependency with no `[tool.interrogate]`
configuration, no Makefile target, and no CI invocation, so docstring coverage is
unenforced — as audit-1.2.1 Finding 4 and audit-1.2.2 Finding 4 both recorded.
The new modules this slice added (`test_venv_scripts_dir.py`) and the rewritten
e2e module are in fact well documented with module and function docstrings, which
is precisely why locking the gate in now is cheap. Roadmap task 1.2.5
("docstring-coverage gate (interrogate)") owns this and is unactioned at this
commit.

**Proposed fix:** action roadmap task 1.2.5: add a `[tool.interrogate]` block
with an explicit `fail-under` threshold and wire an `interrogate` invocation into
the lint gate (a Makefile target plus a CI step), or remove `interrogate` from
the dev group if the gate is intentionally deferred. Either resolves the
ambiguity of a tool that is installed but does nothing.

## Finding 6 — ADR-006 cross-reference to design §4 is correct but the design only names the policy, not the resolver scheme

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/adr-006-console-scripts-e2e-posix-policy.md:88`
  ("recorded in novel-ralph-harness-design.md §4"),
  `docs/novel-ralph-harness-design.md:243`

ADR-006 states the decision is "recorded in
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §4 and the
[developers' guide](developers-guide.md)". Design §4 (line 243) does record that
the e2e test "runs on POSIX only, per
`docs/adr-006-console-scripts-e2e-posix-policy.md`", which is accurate. The minor
gap is that the design and developer-guide references capture the *skip* half of
the policy but not the resolver half — that the venv-scripts directory resolves
through the canonical `venv` sysconfig scheme, which is the technical requirement
ADR-006 leans on and the one a future contributor is most likely to break by
swapping the scheme. The ADR carries this detail; the referencing documents do
not, so a reader following the design's §4 pointer learns the platform policy but
not why `_venv_scripts_dir` passes `"venv"` explicitly.

**Proposed fix:** add one clause to the design §4 sentence (and optionally the
developer-guide note at `docs/developers-guide.md:83`) recording that the
resolver uses the canonical `venv` sysconfig scheme, so the two halves of the
policy — skip outwith POSIX, resolve through the `venv` scheme — are documented
together where ADR-006 says they are recorded. This is a one-line clarification,
not a restructuring.

## Notes on what was checked and found sound

- **The fix is correct and honest.** The dead, wrong `win32` branch (the
  `nt_user` roaming scheme with no `.exe` suffix) is gone; the resolver now uses
  the `venv` scheme bound to the venv directory and returns the venv `bin/`
  directory; the module-level `skipif` guard names ADR-006 as its reason. The
  contract now matches the `ubuntu-latest`-only CI lane.
- **Command/query separation.** `_venv_scripts_dir` is a pure query (it computes
  a path from inputs, no side effects); `_require_success` is a pure assertion
  helper; the e2e test's side effects (build, venv, install, run) are confined to
  the test body. No CQS concern.
- **Scripting standards.** Both the build `uv` and each installed console-script
  run through a cuprum `ProgramCatalogue` keyed on an allowlisted `Program`
  (including absolute paths), so no raw `subprocess` is used, consistent with
  `docs/scripting-standards.md` and ADR-006's decision outcome.
- **Documentation.** ADR-006 is complete (context, drivers, options table,
  decision, goals/non-goals, risks), and the developer guide and design §4 both
  point at it. The new and rewritten test modules carry accurate module and
  function docstrings, and the load-bearing reasons (the POSIX-only rationale,
  the cuprum absolute-path allowlisting) are recorded inline with `why:` comments.
- **Prose conventions.** The slice's prose follows en-GB Oxford spelling
  ("outwith", "-ise") and the quality gates in `AGENTS.md` (`make all`) pass on
  the merged change.
