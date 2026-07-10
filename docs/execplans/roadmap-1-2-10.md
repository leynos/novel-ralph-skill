# Replace the bare sh.make expression statement with an explicit assertion

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises and discoveries`,
`Decision log`, and `Outcomes and retrospective` must be kept up to date as
work proceeds.

Status: DONE

## Purpose / big picture

The test
`tests/test_conftest_helpers.py::test_single_program_catalogue_builds_usable_allowlist`
proves that the shared `single_program_catalogue` fixture yields a cuprum
allowlist usable by `cuprum.sh.make`. Its final line (line 90 today) is a *bare
expression statement*:

```python
sh.make(program, catalogue=catalogue)
```

The statement constructs a value and then discards it, asserting nothing. To a
maintainer it reads as dead code: nothing tells the reader that the intent is
"this call must not raise `UnknownProgramError`". Roadmap task 1.2.10
(`docs/roadmap.md` lines 155-160; source review:1.2.7, severity low) requires
replacing that statement with an explicit assertion so the "does not raise"
guarantee is self-evident.

After this change, a reader of `test_single_program_catalogue_builds_usable_allowlist`
sees an assertion that names what `sh.make` must return — a usable
`SafeCmdBuilder` — rather than a result-discarding call. The test's behavioural
contract is unchanged: it still proves the fixture allowlists the program and
that resolving it through the catalogue does not raise. `make test` passes
before and after; the change strengthens *clarity*, not coverage breadth.

This is a readability/intent fix, **not** a lint-failure fix. The bare
`sh.make(...)` statement is **not** currently flagged by any enabled linter: it
is a function call, and ruff's `B018` (useless-expression) explicitly "ignores
expression types that are commonly used for their side effects, such as function
calls" (verified at <https://docs.astral.sh/ruff/rules/useless-expression/>,
"Known problems"). Pylint's `pointless-statement` (W0104) likewise exempts
calls. The roadmap wording "may be flagged by a linter" is forward-looking; the
plan does not assume a current failure, and the acceptance criterion is the
explicit assertion plus a still-green gate, not a lint diff.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Edit only inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-10`. Never
  touch the root/control worktree.
- The behavioural contract of
  `test_single_program_catalogue_builds_usable_allowlist` must not change. It
  must still assert (a) the program is in `catalogue.allowlist`, and (b) that
  resolving the program through the catalogue via `sh.make` does not raise
  `UnknownProgramError`. The new assertion replaces the discard; it must not
  weaken either guarantee, nor convert the test into an execution test (no
  `.run`/`.run_sync` is added — the docstring's promise is to avoid the slow
  wheel-build-and-install e2e cost).
- Pin to the cuprum 0.1.0 API the test already uses, verified from the locked
  wheel (uv.lock line 113-118, `cuprum==0.1.0`). The `sh.make` signature is:

  ```python
  def make(
      program: Program, *, catalogue: ProgramCatalogue = DEFAULT_CATALOGUE
  ) -> SafeCmdBuilder: ...
  ```

  - `sh.make` calls `catalogue.lookup(program)` eagerly and raises
    `UnknownProgramError` when the program is not allowlisted; otherwise it
    returns a `builder` closure of type
    `SafeCmdBuilder = cabc.Callable[..., SafeCmd]`. Verified in the installed
    wheel `cuprum/sh.py` `def make` (lines 529-545) and the `SafeCmdBuilder`
    type alias (line 47).
  - `SafeCmd` is a frozen dataclass exposing `program: Program`,
    `argv: tuple[str, ...]`, `project: ProjectSettings`, and the property
    `argv_with_program -> tuple[str, ...]` (installed `cuprum/sh.py`, lines
    355-374). Both `SafeCmd` and `SafeCmdBuilder` are re-exported from the
    `cuprum.sh` module `__all__` and from the top-level `cuprum` package
    `__init__` (`__init__.py` exports at lines 48-57, 87-88).
  - `UnknownProgramError(LookupError)` is raised by `ProgramCatalogue.lookup`
    when the program is absent (installed `cuprum/catalogue.py`, class at line
    25, raised at line 82); it is re-exported from `cuprum.sh`
    (`cuprum/sh.py` `__all__`).
  Do **not** rely on the illustrative `Catalogue.from_programs(...)` /
  `sh.scoped(...)` forms shown in `docs/scripting-standards.md` lines 166-177:
  those are documentation-level sketches; the locked 0.1.0 surface the test
  actually uses is `ProgramCatalogue`/`ProjectSettings` + `sh.make(program,
  catalogue=...)`, exactly as the `single_program_catalogue` fixture
  (`tests/conftest.py` lines 112-141) and the e2e module
  (`tests/test_console_scripts_e2e.py` lines 73, 93-96) construct it.
- No new runtime or dev dependency. The change uses only what
  `tests/test_conftest_helpers.py` already imports (`cuprum.sh`,
  `cuprum.program.Program`) plus, if the chosen assertion needs the type at
  runtime, a runtime import of `SafeCmd`/`SafeCmdBuilder` from `cuprum` (already
  an installed, locked symbol; no dependency change). `make audit` must stay
  clean.
- `tests/test_conftest_helpers.py` is inside `PYTHON_TARGETS` (`Makefile` line
  15: `PYTHON_TARGETS ?= novel_ralph_skill tests`), so it is subject to the
  full ruff lint + format, 100% `interrogate` docstring coverage, Pylint, and
  `ty` typecheck gates. The `**/test_*.py` per-file-ignores
  (`pyproject.toml` line 96) exempt `S101` (bare `assert`), `PLR2004` (magic
  values), `PLR0913`, `PLR0917`, and `PLR6301`, so a bare `assert` is the
  idiomatic form in this module — match the existing assertions in the file
  (e.g. lines 85-87).
- All prose, comments, docstrings, and commit messages use en-GB Oxford
  spelling ("-ize"/"-yse"/"-our"), per AGENTS.md "Code style and structure".
- Target Python 3.14 (`requires-python = ">=3.14"`), keep
  `from __future__ import annotations` at the top of the module (already
  present, line 11).

## Tolerances (exception triggers)

- Scope: this task touches exactly two files —
  `tests/test_conftest_helpers.py` (the assertion) and `docs/roadmap.md` (the
  task tick). If the implementation needs to touch more than these two files, or
  more than ~25 net lines, stop and escalate. (No developers-guide note is
  warranted: this is a one-test clarity fix, not a new project convention; see
  Decision Log.)
- Interface: this task adds no public API and changes no production code under
  `novel_ralph_skill/`. If satisfying it appears to require changing the
  `single_program_catalogue` fixture or any production module, stop and
  escalate.
- Dependencies: if any work item appears to need a new dependency, stop and
  escalate; the standard plan needs none.
- Iterations: if the gate (`make all`) fails for a reason attributable to this
  change after 3 fix attempts, stop and escalate.
- Ambiguity: if review concludes the assertion should also exercise the builder
  by *calling* it (constructing a `SafeCmd`) rather than only asserting the
  builder is returned, that is a design choice with a clear default below
  (assert the builder is callable, then call it once and assert the resulting
  `SafeCmd.program` round-trips); if a reviewer instead wants the call removed
  entirely or wants `.run_sync()` added, stop and escalate — adding execution
  contradicts the module's stated "without paying the slow … e2e cost" intent.

## Risks

- Risk: over-reaching the assertion into an *execution* test (adding
  `.run_sync()` / `.run`), which would contradict the test's documented intent
  to avoid the slow wheel-build-and-install e2e and could fail in sandboxed CI
  where `uv` may not be runnable.
  - Severity: medium. Likelihood: low.
  - Mitigation: the assertion only *constructs* — it calls `sh.make` (the
    resolution that can raise `UnknownProgramError`) and at most invokes the
    returned builder to produce a `SafeCmd`; it never runs a subprocess. The
    builder call is pure: `builder(*args, **kwargs)` only coerces argv and
    constructs a frozen `SafeCmd` (installed `cuprum/sh.py` lines 540-543), with
    no I/O.
- Risk: a runtime import of `SafeCmd`/`SafeCmdBuilder` trips ruff `TC` (the
  typing-import-convention rule set, selected at `pyproject.toml` line 51) which
  pushes type-only imports under `TYPE_CHECKING`. If the symbol is used only in
  an annotation, `TC` will demand it move to the `TYPE_CHECKING` block; if it is
  used at runtime (e.g. in `isinstance`), it must stay a runtime import.
  - Severity: low. Likelihood: medium.
  - Mitigation: choose an assertion form whose import placement is consistent
    with its use. The default form (assert the builder is `callable(...)`, then
    call it and assert on the resulting `SafeCmd.program`) needs **no** new
    import at all — `callable` is a builtin and `SafeCmd.program` is accessed by
    attribute, not by name — so no `TC` interaction arises. Only if a reviewer
    prefers an explicit `isinstance(result, SafeCmd)` is a runtime import of
    `SafeCmd` from `cuprum` required; in that case keep it a runtime import
    (it is used at runtime) and let `ty`/ruff confirm. The plan's default
    avoids the question.
- Risk: the new assertion message or comment drifts from en-GB Oxford spelling
  or restates the test logic (AGENTS.md: "Test documentation should omit
  examples that only restate the test logic").
  - Severity: low. Likelihood: low.
  - Mitigation: keep the assertion message factual and outcome-named ("sh.make
    must return a usable SafeCmdBuilder for an allowlisted program"); do not add
    a redundant comment that merely re-narrates the call.

## Progress

- [x] (done) Work item 1: replaced the bare `sh.make(...)` statement in
      `test_single_program_catalogue_builds_usable_allowlist` with an explicit
      assertion (bind `builder`, assert `callable`, construct one `SafeCmd`, and
      assert `command.program == program`), in a single gate-passing commit.
      `make all` green (121 passed); `make audit` clean. The formatter joined the
      round-trip assertion message onto one line (no behaviour change).
- [x] (done) Work item 2: ticked roadmap task 1.2.10 and ran the Markdown
      gates. `make markdownlint` clean (0 errors, 63 files), `make nixie` clean
      (all diagrams validated), `make all` green (121 passed), `make audit`
      clean.

## Surprises and discoveries

- Observation: the bare `sh.make(...)` statement is not flagged by any enabled
  linter today; ruff `B018` exempts function-call expression statements.
  - Evidence: ruff rule docs for `useless-expression (B018)`, "Known problems":
    "This rule ignores expression types that are commonly used for their side
    effects, such as function calls." (<https://docs.astral.sh/ruff/rules/useless-expression/>).
    `B` is selected (`pyproject.toml` line 61) but does not fire here.
  - Impact: the task is framed as a clarity fix with a still-green gate, not as
    fixing a current lint failure. The acceptance criterion is the explicit
    assertion, not a change in lint output.
- Observation: `cuprum.sh.make` resolves the program eagerly (it calls
  `catalogue.lookup(program)` *before* returning the builder), so the
  "does not raise `UnknownProgramError`" guarantee is exercised by the
  `sh.make(...)` call itself, not by invoking the returned builder.
  - Evidence: installed wheel `cuprum/sh.py`, `def make` (lines 529-545):
    `entry = catalogue.lookup(program)` runs at call time; the inner `builder`
    closure is what defers argv construction.
  - Impact: an assertion that merely binds and inspects the *builder* (without
    calling it) already proves the no-raise guarantee. Calling the builder once
    is an optional strengthening that also pins the `SafeCmd.program`
    round-trip; both are valid and neither runs a subprocess.

## Decision log

- Decision: replace the discard with an explicit assertion that binds the
  `sh.make` result and asserts it is a usable builder, using the default form
  `builder = sh.make(program, catalogue=catalogue); assert callable(builder)`
  followed by constructing one `SafeCmd` and asserting its `program` round-trips
  (`cmd = builder(); assert cmd.program == program`).
  - Rationale: the roadmap asks to make the "does not raise" intent explicit.
    Binding the result and asserting it is callable names the contract
    (`sh.make` yields a usable `SafeCmdBuilder`) and removes the dead-code read.
    Constructing one `SafeCmd` and asserting `cmd.program == program` pins the
    program round-trip through the catalogue entry (`builder` builds the
    `SafeCmd` from `entry.program`, installed `cuprum/sh.py` line 542) without
    running anything, honouring the test's documented "no slow e2e cost" intent.
    `callable(...)` is a builtin and `SafeCmd` is reached by attribute, so no new
    import and no `TYPE_CHECKING`/`TC` interaction is introduced.
  - Date/Author: 2026-06-22, planning agent.
- Decision: do **not** add `.run_sync()` / `.run` to the assertion.
  - Rationale: the test docstring (`tests/test_conftest_helpers.py` lines 77-81)
    explicitly avoids "paying the slow wheel-build-and-install e2e cost", and
    ADR-006 (`docs/adr-006-console-scripts-e2e-posix-policy.md`) scopes actual
    console-script execution to the POSIX-guarded slow e2e in
    `tests/test_console_scripts_e2e.py`. Executing here would duplicate that and
    risk sandbox flakiness. The no-raise guarantee is already exercised by the
    eager `sh.make` resolution.
  - Date/Author: 2026-06-22, planning agent.
- Decision: do not add a developers-guide note for this change.
  - Rationale: AGENTS.md "Documentation maintenance" asks to record *new
    conventions, decisions, or behaviour changes*. This is a localized
    test-clarity edit that introduces no new convention and changes no
    user-facing or internal interface, so a guide note would be noise. (Contrast
    1.2.8, which introduced a guard *convention* worth recording.) If a reviewer
    judges otherwise, that is an ambiguity tolerance trigger — stop and escalate
    rather than expand scope silently.
  - Date/Author: 2026-06-22, planning agent.
- Decision: pin the assertion to the real cuprum 0.1.0 API
  (`ProgramCatalogue`/`sh.make(program, catalogue=...)` returning a
  `SafeCmdBuilder`), not the illustrative `Catalogue.from_programs`/`sh.scoped`
  forms in `docs/scripting-standards.md`.
  - Rationale: the locked wheel exposes `ProgramCatalogue`, `ProjectSettings`,
    and `sh.make(program, *, catalogue=...)`; the fixture and e2e modules
    already use exactly this surface. The scripting-standards snippets are
    documentation sketches and do not reflect the 0.1.0 symbol names. Verified
    directly against the installed wheel `cuprum/sh.py` and `cuprum/__init__.py`.
  - Date/Author: 2026-06-22, planning agent.

## Outcomes and retrospective

Delivered as planned. The test
`test_single_program_catalogue_builds_usable_allowlist` now ends with an
explicit, self-documenting assertion: the `sh.make` result is bound to
`builder`, `assert callable(builder)` names the "yields a usable builder"
contract, and `assert command.program == program` pins the program round-trip.
`make all` stayed green (121 passed) and the behavioural contract is unchanged —
no subprocess runs and no execution test was added. The program round-trip
assertion caught nothing beyond the no-raise guarantee (as expected) but
documents intent cheaply. The only deviation from the draft was a formatter-led
single-lining of the round-trip assertion message; the no-new-import default
form held with no `TYPE_CHECKING`/`TC` interaction.

## Context and orientation

The reader needs no prior plans. Key facts and paths (all relative to the
worktree `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-10`):

- The test under change:
  `tests/test_conftest_helpers.py::test_single_program_catalogue_builds_usable_allowlist`
  (lines 74-90). It receives the `single_program_catalogue` fixture, builds a
  one-program catalogue for `Program("uv")`, asserts `program in
  catalogue.allowlist` (lines 85-87), and then — the target — discards the
  result of `sh.make(program, catalogue=catalogue)` (line 90) under a comment
  explaining the intent (lines 88-89).
- The fixture it exercises: `single_program_catalogue` in `tests/conftest.py`
  (lines 112-141). It returns a builder `(name, program) -> ProgramCatalogue`
  that wraps one `ProjectSettings` allowlisting exactly `program`. The fixture
  docstring (lines 114-126) records that cuprum 0.1.0 allowlists any `Program`
  string and that the catalogue allowlist is the execution gate.
- The cuprum surface, verified against the locked wheel `cuprum==0.1.0`
  (uv.lock lines 113-118). The repository checkout at
  `/data/leynos/Projects/cuprum` is *not* the source of truth for the locked
  version; the assertions in this plan were read from the installed wheel
  `cuprum/sh.py`:
  - `def make(program, *, catalogue=DEFAULT_CATALOGUE) -> SafeCmdBuilder`
    (lines 529-545). It runs `entry = catalogue.lookup(program)` eagerly
    (raising `UnknownProgramError` for an unlisted program) and returns a
    `builder(*args, **kwargs) -> SafeCmd` closure.
  - `type SafeCmdBuilder = cabc.Callable[..., SafeCmd]` (line 47).
  - `class SafeCmd` (lines 355-374): frozen dataclass with `program`, `argv`,
    `project`, and `argv_with_program` property.
  - `cuprum/catalogue.py`: `UnknownProgramError(LookupError)` (line 25),
    raised by `ProgramCatalogue.lookup` (line 82).
  - `cuprum/__init__.py`: re-exports `SafeCmd`, `SafeCmdBuilder` (lines 48-57,
    87-88), so a runtime import — should a reviewer want one — is
    `from cuprum import SafeCmd`.
- Source-of-truth docs the change must respect:
  - `docs/roadmap.md` lines 155-160 — task 1.2.10 (the remediation text).
  - `docs/adr-006-console-scripts-e2e-posix-policy.md` — execution of console
    scripts is the slow, POSIX-guarded e2e's job, not this unit test's; line 86
    confirms "cuprum 0.1.0 allowlists any `Program` string, including an
    absolute path", matching the fixture docstring.
  - `docs/scripting-standards.md` — describes the `sh.make` builder pattern
    (the `git = sh.make("git"); git(...).run_sync()` shape, lines 173-176). Used
    here for *concept* only; the locked symbol names come from the wheel.
  - AGENTS.md — "Python verification and testing" (cover happy paths; keep tests
    in `tests/`), "Code style and structure" (comment *why*, omit test
    documentation that only restates logic), and "Change quality and committing"
    (commit only when all gates pass).
- Quality gates (AGENTS.md "Change quality and committing", Makefile the
  canonical entry point): `make check-fmt`, `make lint`, `make typecheck`,
  `make test`, `make audit`; `make all` is `build check-fmt lint typecheck test`
  (Makefile line 28) and does **not** run `audit`, `markdownlint`, or `nixie`,
  so those run explicitly. For the Markdown work item, AGENTS.md requires
  `make markdownlint` and `make nixie`.

Definitions:

- "Bare expression statement": a Python statement consisting only of an
  expression whose value is neither assigned nor returned nor asserted — here,
  `sh.make(program, catalogue=catalogue)` on its own line.
- "SafeCmdBuilder": cuprum's `Callable[..., SafeCmd]` returned by `sh.make`; a
  closure that, when called with argv, produces a `SafeCmd` ready to run.
- "Allowlist": the set of `Program` values a `ProgramCatalogue` permits;
  `sh.make` raises `UnknownProgramError` for any program outside it.

## Plan of work

Two ordered, independently committable work items, each gate-passable at commit
time. No commit is made in a gate-failing state (AGENTS.md "Change quality and
committing", lines 99-100 and 108).

### Work item 1 — Replace the discard with an explicit assertion

Implements: `docs/roadmap.md` task 1.2.10 (lines 155-160, make the "does not
raise" intent explicit); AGENTS.md "Code style and structure" (clarity over
cleverness; comment *why*, not *what*; small single-responsibility tests) and
"Python verification and testing" (cover the happy path, keep tests in
`tests/`); AGENTS.md "Change quality and committing" (commit only when all gates
pass). Honours ADR-006's boundary by keeping this a construction-only unit test,
not an execution test.

Docs to read first: `docs/roadmap.md` lines 155-160; the existing
`tests/test_conftest_helpers.py` (the whole file, ~108 lines) and
`tests/conftest.py` `single_program_catalogue` (lines 112-141);
`docs/adr-006-console-scripts-e2e-posix-policy.md` (why execution stays in the
slow e2e); `docs/scripting-standards.md` lines 160-199 (the `sh.make` builder
concept); AGENTS.md "Code style and structure", "Python verification and
testing", and "Change quality and committing"; `.rules/python-00.md`,
`.rules/python-typing.md`, `.rules/python-return.md` (style, annotation, return
conventions).

Skills to load: `python-router` → `python-testing` (assertion style, the
fixture boundary, why this stays a unit test rather than an e2e),
`python-types-and-apis` (the `SafeCmdBuilder`/`SafeCmd` shape and whether any
import is type-only or runtime). `en-gb-oxendict` for the assertion message and
any comment. Verification adversaries (`python-verification` →
`hypothesis`/`crosshair`/`mutmut`) are **not** warranted: this is a single
deterministic assertion over a fixed input (`Program("uv")` in a one-program
catalogue), not an invariant over an input space, and it adds no production
branch a mutation could survive. Do not pull in `hypothesis`.

What to change, precisely, in `tests/test_conftest_helpers.py`,
`test_single_program_catalogue_builds_usable_allowlist` (lines 74-90):

1. Replace the bare statement on line 90 and its preceding two-line comment
   (lines 88-89) with an explicit assertion that binds the `sh.make` result and
   asserts the contract. The default form (no new import):

   ```python
   # cuprum.sh.make resolves the program through the catalogue eagerly; for an
   # allowlisted program it must return a usable SafeCmdBuilder rather than
   # raising UnknownProgramError. Asserting on the returned builder (and the
   # SafeCmd it constructs) makes that "does not raise" guarantee explicit.
   builder = sh.make(program, catalogue=catalogue)
   assert callable(builder), (
       f"sh.make returned a non-callable {builder!r} for allowlisted {program}"
   )
   command = builder()
   assert command.program == program, (
       f"builder produced SafeCmd.program {command.program!r}, "
       f"expected {program!r}"
   )
   ```

   The bound `builder` and the constructed `command` replace the discarded
   value; `callable(...)` is a builtin and `command.program` is reached by
   attribute, so no new import (and no `TYPE_CHECKING`/`TC` interaction) is
   introduced. The `builder()` call is pure — it only coerces an empty argv and
   constructs a frozen `SafeCmd` — so no subprocess runs and the test stays a
   fast construction-only unit test.

2. Keep the docstring (lines 77-81) intact; it already states the intent
   ("resolving the program proves the factory yields a usable allowlist without
   paying the slow … e2e cost"), which the new assertion now makes concrete in
   code. Do not add a redundant comment that merely re-narrates the call
   (AGENTS.md: omit test documentation that only restates the test logic) — the
   *why* comment above is retained because it explains the eager-resolution
   rationale, which is not obvious from the call.

3. Do not alter the other tests, the imports for `sh`/`Program`, or the
   `__future__` import.

Keep the module well under the 400-line AGENTS.md cap (it is ~108 lines today
and grows by a handful). Maintain 100% docstring coverage — `interrogate` runs
under `make lint`; no new function/class is added, so the existing docstrings
suffice, but verify `make lint` still reports 100%.

Validation (run sequentially from the worktree root, never in parallel per the
build-cache note in the global instructions): `make check-fmt`, then
`make lint`, then `make typecheck`, then `make test`, then `make audit`, then
`make all`. Expect all green: the edited test passes (it asserted `callable`
and the `program` round-trip), the rest of the suite is unaffected,
`interrogate` reports 100%, ruff/`ruff format`/`ty` clean, `pip-audit` clean.
Capture the `make test` summary line (N passed) in `Artifacts and notes`. Only
when every gate is green is the commit made.

Commit (single, gate-passing): "Assert sh.make builder in conftest helper test".

### Work item 2 — Tick the roadmap and run the Markdown gates

Implements: AGENTS.md "Documentation maintenance" and "Markdown files" gates;
the `docs/roadmap.md` task-completion convention (`- [ ]` -> `- [x]`).

Docs to read first: `docs/roadmap.md` task 1.2.10 (lines 155-160);
`docs/documentation-style-guide.md` (wrap prose at 80 columns, en-GB Oxford
spelling). Skills to load: `en-gb-oxendict`.

What to do:

1. Tick task 1.2.10 in `docs/roadmap.md` (`- [ ]` -> `- [x]` on line 155). Do
   not alter any other roadmap entry.
2. This ExecPlan file (`docs/execplans/roadmap-1-2-10.md`) is itself a tracked
   Markdown file; if it is committed as part of the planning round it must also
   pass the Markdown gates. Treat both `.md` files together for the gate run.

Validation (run sequentially from the worktree root, never in parallel):
because Markdown files changed, run `make markdownlint` and `make nixie` (the
edited Markdown has no Mermaid, so `nixie` passes trivially, but AGENTS.md
requires running it for any Markdown change). Then run the full code suite as a
final end-to-end check: `make all`, then `make audit`. (`make all` is
`build check-fmt lint typecheck test` per Makefile line 28; it does **not** run
`audit`, `markdownlint`, or `nixie`, so those run explicitly.) Expect
`make markdownlint` clean, `make nixie` clean, `make all` green, `make audit`
clean. Capture each summary in `Artifacts and notes`.

Commit: "Tick roadmap task 1.2.10".

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-10`.

1. Confirm the branch and tree state. Run `git branch --show-current` (expect
   `roadmap-1-2-10`) and `git status --short` (expect clean or plan-only).

2. Work item 1 — edit
   `test_single_program_catalogue_builds_usable_allowlist` to replace the bare
   `sh.make(...)` statement with the bound-and-asserted form above. Then gate by
   running, sequentially from the worktree root: `make check-fmt`, `make lint`,
   `make typecheck`, `make test`, `make audit`, `make all`. Expect all green;
   `make test` reports all tests passed. Commit once, gate-passing, with a
   file-based message (never `-m`, per the `commit-message` skill).

3. Work item 2 — tick `docs/roadmap.md` task 1.2.10, then run, sequentially:
   `make markdownlint`, `make nixie`, then `make all`, then `make audit`. Expect
   `markdownlint` and `nixie` clean and `make all` green. Commit once,
   gate-passing.

4. Two commits total — no commit is made while any gate is red.

## Validation and acceptance

Acceptance is behavioural and observable:

- The final lines of `test_single_program_catalogue_builds_usable_allowlist` are
  an explicit assertion, not a bare expression statement: the `sh.make` result
  is bound to `builder`, `assert callable(builder)` names the "yields a usable
  builder" contract, and `assert command.program == program` pins the program
  round-trip. A reader can see the "does not raise / usable builder" intent
  without inferring it.
- The test's behavioural contract is unchanged: it still asserts the program is
  in `catalogue.allowlist` and that `sh.make` resolves the allowlisted program
  without raising `UnknownProgramError`. No subprocess is run; the test remains
  a fast construction-only unit test, consistent with its docstring and ADR-006.
- `make test` passes before and after the change (the change does not introduce
  a red-then-green test; it rewrites an existing assertion-free statement into an
  assertion that holds on the current fixture).

Quality criteria ("done"):

- Tests: every test in `tests/test_conftest_helpers.py` passes under
  `make test`, and the full suite stays green.
- Lint/typecheck: `make lint` (ruff + `interrogate` 100% docstring coverage +
  Pylint) and `make typecheck` (`ty`) clean; `make check-fmt` clean.
- Audit: `make audit` (`pip-audit`) clean — no new dependency is introduced.
- Markdown: `make markdownlint` and `make nixie` clean on the edited docs
  (`docs/roadmap.md` and this ExecPlan).

Quality method: run the Makefile targets sequentially (per the build-cache note,
never in parallel) from the worktree root. `make all` is
`build check-fmt lint typecheck test` (Makefile line 28) and does **not** run
`audit`, `markdownlint`, or `nixie`; the final end-to-end check is therefore
`make all` followed by `make audit`, then (for the Markdown work item)
`make markdownlint` and `make nixie`, each run on its own so no gate is skipped.

## Idempotence and recovery

- Both steps are re-runnable. The test edit is a single deterministic
  replacement; the roadmap edit is a one-character checkbox flip.
- If `make test` reports a failure outside `tests/test_conftest_helpers.py`,
  stop: this change touches only that one test and no production code, so an
  unrelated failure is not caused by it. Re-examine before proceeding.
- If `make typecheck` or `make lint` flags the assertion (e.g. an unexpected
  `TC` import demand because a reviewer chose the `isinstance(..., SafeCmd)`
  variant), prefer the default no-import form documented in Work item 1; if the
  reviewer's variant is required, keep `SafeCmd` a runtime import and re-run.
- No destructive operations. Recovery is `git checkout -- <file>` on any edited
  file within the worktree.

## Artefacts and notes

- Work item 1: `make all` reported `121 passed in 4.70s`; `make audit` reported
  `No known vulnerabilities found`. The `ruff format` check required joining the
  `command.program` round-trip assertion message onto a single line (the only
  formatter-driven deviation from the plan's draft snippet; no behaviour change).
- Work item 2: `make markdownlint` reported `Summary: 0 error(s)` over 63 files;
  `make nixie` reported `All diagrams validated successfully`; `make all`
  reported `121 passed`; `make audit` reported `No known vulnerabilities found`.
- Coderabbit review (`coderabbit review --agent`) ran twice. The first run, after
  Work item 1, flagged two execplan-only style issues (a first-person "asks us
  to" on the Purpose paragraph and two ampersand headings); both were corrected
  to passive/third-person phrasing and "and"-spelled headings. The second run,
  after Work item 2, reported 0 findings.
- Verified cuprum-API references (from the installed locked wheel
  `cuprum==0.1.0`, not the `/data/leynos/Projects/cuprum` checkout):
  `cuprum/sh.py` `def make` lines 529-545 (eager `catalogue.lookup`, returns
  `SafeCmdBuilder`); `type SafeCmdBuilder` line 47; `class SafeCmd` lines
  355-374; `cuprum/catalogue.py` `UnknownProgramError` line 25, raised line 82;
  `cuprum/__init__.py` re-exports `SafeCmd`/`SafeCmdBuilder` lines 48-57, 87-88.
- Verified linter behaviour: ruff `B018` (useless-expression) "ignores
  expression types that are commonly used for their side effects, such as
  function calls" — <https://docs.astral.sh/ruff/rules/useless-expression/>,
  "Known problems". Confirms the bare statement is not a current lint failure.

## Interfaces and dependencies

No production interface changes; `novel_ralph_skill` is untouched. No new test
helper, fixture, or cross-module import is added. The change is confined to the
body of one test, `test_single_program_catalogue_builds_usable_allowlist`, in
`tests/test_conftest_helpers.py`. The cuprum symbols it relies on are already
imported in that module (`cuprum.sh`, `cuprum.program.Program`); the default
assertion form needs no further import. The locked dependency set is unchanged;
`make audit` must stay clean.
