# Tighten the `read_repo_text` fixture to a precise `(*parts: str) -> str` type

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises and discoveries`, `Decision log`,
and `Outcomes and retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

The shared `read_repo_text` fixture in `tests/conftest.py` (introduced by
roadmap task 1.2.7) returns a callable typed as `cabc.Callable[..., str]`. The
ellipsis (`...`) in that annotation is a deliberate "any arguments" escape
hatch: it tells the typechecker to skip argument-count and argument-type
checking at every call site. So today a call such as `read_repo_text(123)` or
`read_repo_text("Makefile", mode="rb")` typechecks clean even though the
underlying reader only accepts positional `str` parts. The reviewer of 1.2.7
flagged this (roadmap remediation, source `review:1.2.7`, severity low): the
fixture's real shape is the variadic `(*parts: str) -> str` form, and the
1.2.7 "Interfaces" section explicitly anticipated tightening it
(`docs/execplans/roadmap-1-2-7.md` lines 652-654: "The exact return-callable
signatures may be tightened during implementation (for example `read_repo_text`
as `Callable[[str], str]` with `*parts`)").

After this change, the fixture's return type is a named, variadic-aware
`Protocol` named `RepoTextReader`, defined entirely inside an
`if typ.TYPE_CHECKING:` block in `tests/conftest.py`, and every call site
annotates the fixture parameter with that type. The observable wins, all
confirmed against the locked typechecker `ty` 0.0.51 (`uv.lock`):

- `read_repo_text(123)` becomes a typecheck error
  (`invalid-argument-type`: "Expected `str`, found `Literal[123]`"), where it
  was previously accepted. This is the restored static arg-shape guarantee.
- The fixture's documented signature (`(*parts: str) -> str`) is now expressed
  in the type system, not only in prose.
- No runtime behaviour changes: the same tests pass, with the same counts,
  before and after, and the `RepoTextReader` name is never constructed or
  imported at runtime. This is a typing refactor (AGENTS.md "Separate atomic
  refactors"), not a behaviour change.

Success is behaviour-preserving and demonstrable: `make all` stays green, the
test count and outcomes are unchanged, and a temporary `read_repo_text(123)`
probe fails `make typecheck` after the change but would have passed before.

## Constraints

Hard invariants that must hold throughout implementation.

- Work only inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-9`. Never
  read-modify-write any file in the root/control worktree at
  `/data/leynos/Projects/novel-ralph-skill`.
- Do not change any test's observable behaviour. The same tests must pass with
  the same exit-code, skip, timeout, and warning-filter semantics before and
  after. The reader closure `_read(*parts: str) -> str` in `tests/conftest.py`
  keeps its body and behaviour unchanged; only its *return-type annotation* and
  the *call-site annotations* change.
- Do not modify production code under `novel_ralph_skill/`. The new `Protocol`
  is a test-only type and must live in the `tests/` tree, not in the shipped
  package (placing a test type in `novel_ralph_skill/` would pollute the
  distribution — wrong altitude).
- Add no new dependencies. `typing.Protocol` is standard library.
- Keep all pytest tests in the top-level `tests/` tree (AGENTS.md "Python
  verification and testing"). The type lives in `tests/conftest.py` alongside
  the fixture it describes.
- No runtime cross-module test import is created, ever. The developers' guide
  (`docs/developers-guide.md`, "Shared test scaffolding", lines 29-35) forbids
  consuming shared scaffolding "by importing from another test module or from
  `conftest` itself", and as that section reads on `origin/main` it states no
  exception. This plan therefore (a) first amends that guide in WI-1 to carve
  out an explicit, narrow exception for a **type-only** `if TYPE_CHECKING:`
  import of a shared *type* (never a fixture/helper value), and only then
  (b) introduces any `from conftest import RepoTextReader` consumer. Every
  consumer import sits inside an `if typ.TYPE_CHECKING:` guard, which is `False`
  at runtime, so no runtime import is created (verified: pytest collects and
  runs the suite with this guarded import; see "Verified facts"). Because every
  touched file carries `from __future__ import annotations`, the fixture's own
  `-> RepoTextReader` return annotation is a lazy string and the name is never
  needed at runtime either — so the `Protocol` lives wholly inside the
  `TYPE_CHECKING` block (verified).
- `tests/conftest.py` is inside `PYTHON_TARGETS`
  (`Makefile`, `PYTHON_TARGETS ?= novel_ralph_skill tests`), so it must pass
  Ruff lint and format, 100% `interrogate` docstring coverage
  (`pyproject.toml` `[tool.interrogate] fail-under = 100`), the PyPy-backed
  Pylint runner, and `ty` typecheck. interrogate scans inside `TYPE_CHECKING`
  blocks, so the new `Protocol` class needs a class docstring and its `__call__`
  method needs a method docstring even though both sit inside the guard
  (verified: removing the `__call__` docstring drops coverage to 92.3% and fails
  the gate).
- `tests/test_state_layout_reference.py` is at exactly 400 lines, the AGENTS.md
  per-file cap ("No single code file should be longer than 400 lines"). The
  three annotation changes in that file must be line-neutral: replace
  `cabc.Callable[..., str]` with the `Protocol` name on the same line. Do not
  add or remove a line in that file beyond the single net-neutral import swap
  described in WI-4. If the import or annotation work would push it past 400
  lines, stop and escalate (see Tolerances) rather than splitting it here —
  splitting that module is roadmap task 1.2.18's job.
- All prose, comments, docstrings, and the commit message use en-GB Oxford
  spelling ("-ize"/"-yse"/"-our") per AGENTS.md.

## Tolerances (exception triggers)

- Scope: this change touches four files
  (`tests/conftest.py`, `tests/test_conftest_helpers.py`,
  `tests/test_interrogate_gate.py`, `tests/test_state_layout_reference.py`) plus
  the developers' guide. If implementation requires editing more than five
  files, or more than roughly 70 net lines, stop and escalate.
- Interface: the fixture's *return value* (a callable accepting `*parts: str`)
  must not change. If making the type precise forces a change to the runtime
  callable's parameters, stop and escalate.
- File size: if any edit pushes `tests/test_state_layout_reference.py` above
  400 lines, stop and escalate (1.2.18 owns the split).
- Dependencies: if any work item appears to need a new dependency, stop and
  escalate — none should.
- Iterations: if `make all` still fails after three fix attempts on a work
  item, stop and escalate with the failing output.
- Typechecker behaviour: if `ty` rejects the `Protocol`-based variadic callable
  form, or rejects it when defined inside the `TYPE_CHECKING` block (contrary to
  the verification below), stop and escalate rather than reaching for `Any`,
  `# type: ignore`, or a runtime-level class definition.

## Risks

    - Risk: `ty` 0.0.51 does not honour a variadic `Protocol.__call__` and
      either errors or silently keeps the old "any args" looseness.
      Severity: high
      Likelihood: low
      Mitigation: verified before drafting against the locked `ty` 0.0.51 — the
      Protocol form is accepted and a non-`str` argument is flagged
      (`invalid-argument-type`). WI-2 adds a red-then-green typecheck probe so
      the guarantee is pinned, not assumed.

    - Risk: defining `RepoTextReader` wholly inside the `if typ.TYPE_CHECKING:`
      block breaks `ty` resolution or pytest collection (because the class does
      not exist at runtime).
      Severity: medium
      Likelihood: low
      Mitigation: empirically disproved in this exact worktree (see "Verified
      facts"). A `RepoTextReader` defined entirely inside conftest's
      `if typ.TYPE_CHECKING:` block, with the fixture annotated
      `-> RepoTextReader` and consumers importing it under their own
      `TYPE_CHECKING` guard, (a) passes `uv run ty check` ("All checks passed!"),
      (b) is collected and run by `uv run pytest` ("1 passed"), and (c) still
      flags `read_repo_text(123)` with `error[invalid-argument-type]`. The
      `from __future__ import annotations` line present in all four files makes
      the fixture's `-> RepoTextReader` return annotation a lazy string, so the
      name is never resolved at runtime.

    - Risk: importing the Protocol from `conftest` breaks pytest collection or
      `ty` module resolution under the repo's default (prepend) import mode with
      no `tests/__init__.py`.
      Severity: medium
      Likelihood: low
      Mitigation: verified that `from conftest import RepoTextReader` under
      `if typ.TYPE_CHECKING:` resolves for both `ty` check and pytest
      collection in this exact tree (see "Verified facts"). The import is
      type-only, so no runtime import is created and the developers'-guide
      no-runtime-cross-import rule — as amended in WI-1 — is respected.

    - Risk: introducing the `from conftest import RepoTextReader` import in a
      commit before the developers' guide permits it would land a commit that
      contradicts the source-of-truth guide.
      Severity: medium
      Likelihood: low
      Mitigation: WI-1 amends the guide's "Shared test scaffolding" section to
      carve out the type-only `TYPE_CHECKING` exception **before** any consumer
      import is introduced (WI-3 and WI-4 are the first commits to add such an
      import). Work-item ordering is the mitigation; see "Decision log".

    - Risk: the edit pushes `tests/test_state_layout_reference.py` over the
      400-line cap, breaching the AGENTS.md module-size gate.
      Severity: medium
      Likelihood: low
      Mitigation: the three changes there are in-place substitutions on existing
      annotation lines (line-neutral), plus a single import swap that replaces
      one `import collections.abc as cabc` line with one
      `from conftest import RepoTextReader` line (net zero) or drops `cabc`
      entirely (net negative). WI-4 checks `wc -l` stays at or below 400 and
      escalates otherwise.

    - Risk: interrogate fails because the nested `__call__` method (or the
      `Protocol` class) lacks a docstring, even though both sit inside the
      `TYPE_CHECKING` block.
      Severity: low
      Likelihood: medium
      Mitigation: WI-2 gives the `Protocol` class and its `__call__` method
      explicit numpy-style docstrings; `make lint` (which runs interrogate) is
      the per-work-item gate. interrogate is verified to scan inside the
      `TYPE_CHECKING` block.

## Progress

    - [x] WI-1: Amend the developers' guide "Shared test scaffolding" section to
          carve out the type-only `TYPE_CHECKING`-import exception, before any
          consumer import exists. Done: added a "narrow exception" paragraph;
          `make markdownlint`, `make nixie`, and `make all` (121 passed) all
          green.
    - [x] WI-2: Define the `RepoTextReader` Protocol inside the
          `TYPE_CHECKING` block in `tests/conftest.py` and return it from the
          `read_repo_text` fixture. Done: red probe confirmed
          `read_repo_text(123)` now errors `invalid-argument-type`; probe
          removed; `make all` green (121 passed); coderabbit 0 findings.
    - [x] WI-3: Tighten the call-site annotation in
          `tests/test_conftest_helpers.py` and add a regression test that pins
          the variadic signature. Done: added `from conftest import
          RepoTextReader` under `TYPE_CHECKING`, retyped the call site, and added
          `test_read_repo_text_joins_multiple_parts`; `make all` green (122
          passed, +1); coderabbit 0 findings.
    - [x] WI-4: Tighten the remaining call-site annotations in
          `tests/test_interrogate_gate.py` and
          `tests/test_state_layout_reference.py`. Done: added `RepoTextReader`
          imports under `TYPE_CHECKING`, retyped all four call sites,
          `test_state_layout_reference.py` stayed at 400 lines; `make all` green
          (122 passed).

## Surprises and discoveries

    - WI-1: coderabbit (major) flagged several prose lines in this execplan over
      80 columns. `make markdownlint` already passed because the affected lines
      sit inside 4-space-indented blocks (treated as code blocks under
      `code_block_line_length: 120`) or are unbreakable under MD013's non-strict
      default. The genuinely-prose continuation lines were reflowed to under 80
      columns to address the feedback; indented-code-block lines were left as-is
      (within the 120 cap).
    - WI-2: the plan snippet placed a trailing `...` in the Protocol's
      `__call__` body, but Pylint's PyPy runner flagged it as
      `W2301 unnecessary-ellipsis`. A docstring-only body is a valid statement
      for a Protocol method, so the `...` was dropped; `make all` then passed.
    - WI-4: in `tests/test_state_layout_reference.py`, `cabc` was used *only* by
      the three `read_repo_text` annotations, so the plan's net-neutral path
      applied: the `import collections.abc as cabc` line was replaced in place by
      `from conftest import RepoTextReader`. The file stayed at exactly 400 lines
      (`wc -l`), within the AGENTS.md cap. In `tests/test_interrogate_gate.py`,
      `cabc` is still used by the `toml_table` annotation, so its import was kept
      and the `RepoTextReader` import added alongside.
    - WI-4: coderabbit was rate-limited across four attempts (initial plus
      backoffs of 30s, 200s, and 480s; advised wait times oscillated 3-5 min and
      did not clear). Per the workflow's rate-limit policy, this is recorded as
      an open issue and WI-4 proceeded: the deterministic gates (`make all`) are
      green, and WI-4 applies the identical in-place annotation pattern that
      coderabbit reviewed with 0 findings in WI-2 and WI-3. The WI-4 review
      should be re-run when the limit clears (e.g. at PR time).

## Decision log

    - Decision: Express the variadic `(*parts: str) -> str` shape with a
      `typing.Protocol` whose `__call__` is `def __call__(self, *parts: str)
      -> str`, rather than `cabc.Callable[..., str]` or `cabc.Callable[[str],
      str]`.
      Rationale: `cabc.Callable[...]` cannot express `*args` — its argument
      position is either a fixed positional list or the `...` wildcard. A
      `Callable[[str], str]` would wrongly forbid the multi-part calls the
      fixture is used for (e.g.
      `read_repo_text("skill", "novel-ralph", "references",
      "state-layout.md")`). A `Protocol` with a variadic `__call__` is the
      standard, typed way to express a variadic callable and is the form the
      Python typing skill `python-types-and-apis` prescribes for callbacks whose
      `Callable[...]` form is insufficient. Verified accepted by `ty` 0.0.51.
      Date/Author: 2026-06-22, planning agent.

    - Decision: Define `RepoTextReader` **entirely inside** the
      `if typ.TYPE_CHECKING:` block of `tests/conftest.py`, not at module level.
      Rationale: the design's stated goal is no runtime cross-module test import
      and no needless runtime machinery. Because all four touched files carry
      `from __future__ import annotations`, the fixture's `-> RepoTextReader`
      return annotation is a lazy string never evaluated at runtime, and every
      consumer imports the name under its own `TYPE_CHECKING` guard. A
      `TYPE_CHECKING`-only definition therefore (a) resolves cleanly for `ty`,
      (b) is collected and run by pytest, and (c) still flags
      `read_repo_text(123)` — full static teeth with zero runtime class
      construction. This is strictly more design-conformant than the
      module-level placement considered in round 1 (which the round-1 plan
      wrongly justified as "must exist at runtime"); that justification was
      empirically false and is dropped. Verified in this worktree (see "Verified
      facts").
      Date/Author: 2026-06-22, planning agent (round 2).

    - Decision: Amend the developers' guide ("Shared test scaffolding") to
      permit a type-only `TYPE_CHECKING` import of a shared *type* in WI-1,
      before any consumer import is introduced (WI-3/WI-4), rather than relaxing
      the rule after the fact.
      Rationale: the guide as it reads on `origin/main` (lines 29-35) forbids
      importing from `conftest` outright and states no `TYPE_CHECKING`
      exception. Every commit in this repo is gate-passing and individually
      reviewable, so an interim commit that adds `from conftest import
      RepoTextReader` while the guide still forbids it would be a real defect,
      not cosmetic. Landing the carve-out first means no commit ever contradicts
      the source-of-truth guide. This directly resolves round-1 blocking point 1.
      Date/Author: 2026-06-22, planning agent (round 2).

## Outcomes and retrospective

    - All four work items landed as atomic, individually gate-passing commits.
      The `read_repo_text` fixture now returns a named `RepoTextReader`
      `Protocol` (`(*parts: str) -> str`) defined wholly inside conftest's
      `TYPE_CHECKING` block, and all four call sites annotate the fixture with it
      under their own `TYPE_CHECKING`-guarded `from conftest import
      RepoTextReader`. A red probe confirmed `read_repo_text(123)` is now a
      `ty` `invalid-argument-type` error where it previously typechecked clean;
      the probe was removed before committing.
    - Behaviour is preserved: the suite rose by exactly one test (the new
      multi-part regression `test_read_repo_text_joins_multiple_parts`), from
      121 to 122 passing, with no other count or outcome change.
      `test_state_layout_reference.py` stayed at exactly 400 lines, within the
      AGENTS.md per-file cap, and no production code under `novel_ralph_skill/`
      was touched. No dependencies were added.
    - `make all` is green at HEAD (build, check-fmt, lint incl. interrogate 100%
      and PyPy Pylint, `ty` typecheck, 122 tests). `make markdownlint` and
      `make nixie` pass for the documentation changes.
    - Process note: coderabbit reviewed WI-1 (one self-referential execplan
      line-length finding, addressed by reflowing genuine prose), WI-2, and WI-3
      with 0 actionable code findings. The WI-4 review could not run: coderabbit
      returned recoverable account-level rate limits across four attempts
      (initial plus 30s/200s/480s backoffs). This is the one open issue; the WI-4
      diff is the same in-place annotation substitution that passed review in
      WI-2 and WI-3, and the deterministic gates are green.

## Context and orientation

The repository generates the novel-ralph harness skill. The relevant code is
entirely in the `tests/` tree; no production code under `novel_ralph_skill/` is
touched.

`tests/conftest.py` is the single home for shared test scaffolding (roadmap
1.2.7; `docs/developers-guide.md`, "Shared test scaffolding"). It exposes
fixtures consumed by name across the suite, with no inter-module imports. The
fixture this plan changes is `read_repo_text`
(`tests/conftest.py` lines 64-84):

    @pytest.fixture
    def read_repo_text(project_root: Path) -> cabc.Callable[..., str]:
        """Return a reader for a repo-relative UTF-8 text file."""

        def _read(*parts: str) -> str:
            """Return the UTF-8 text of the repo-relative file named by ``parts``."""
            return project_root.joinpath(*parts).read_text(encoding="utf-8")

        return _read

The inner closure `_read` is already `(*parts: str) -> str`. The looseness is
only in the *fixture's return annotation* (`cabc.Callable[..., str]`) and the
*call-site parameter annotations*. Every touched file begins with
`from __future__ import annotations` (verified by reading lines 1-30 of each),
so all annotations are strings the typechecker reads and the runtime ignores.

The developers' guide rule this plan amends and then relies on
(`docs/developers-guide.md` lines 29-35) currently reads:

> Test modules consume these by fixture name — list the fixture as a test or
> helper parameter — and never by importing from another test module or from
> `conftest` itself. Importing helpers from `conftest` is fragile across pytest
> import modes, and reaching into another test module's private symbols couples
> modules through hidden dependencies; both are forbidden here.

WI-1 amends this to carve out the narrow type-only exception (see WI-1) before
any consumer adds such an import.

The call sites (found via `read_repo_text` text search; each annotates the
fixture parameter under an `if typ.TYPE_CHECKING:` block):

- `tests/test_conftest_helpers.py` line 48 —
  `read_repo_text: cabc.Callable[..., str]` in
  `test_read_repo_text_reads_a_known_marker`. Calls
  `read_repo_text("pyproject.toml")`.
- `tests/test_interrogate_gate.py` line 51 —
  `read_repo_text: cabc.Callable[..., str]` in
  `test_makefile_invokes_interrogate`. Calls `read_repo_text("Makefile")`.
- `tests/test_state_layout_reference.py` lines 264, 276, 291 —
  `read_repo_text: cabc.Callable[..., str]` in three methods. Calls
  `read_repo_text(*_STATE_LAYOUT_PARTS)` (a multi-part call: `("skill",
  "novel-ralph", "references", "state-layout.md")`).

Term definitions:

- *Variadic callable*: a callable taking a variable number of positional
  arguments, written `def f(*parts: str) -> str`. `collections.abc.Callable`
  cannot type this directly; a `typing.Protocol` with a `__call__` method can.
- *`Protocol`*: a `typing.Protocol` subclass declares a structural
  ("duck-typed") interface. Any object whose shape matches — here, any callable
  accepting `*parts: str` and returning `str` — satisfies it without
  inheritance.
- *`TYPE_CHECKING` guard*: `if typ.TYPE_CHECKING:` is `False` at runtime and
  `True` only to the typechecker, so definitions and imports inside it cost
  nothing at runtime and cannot cause import-mode collection failures. With
  `from __future__ import annotations`, a name referenced only in annotations
  need never exist at runtime.

## Verified facts (locked libraries)

These were confirmed in this worktree before drafting; the implementer should
re-run the probes in WI-2 to keep them pinned. The conftest and scratch test
files used for verification were created, checked, and then removed, leaving the
working tree clean.

- Locked versions (`uv.lock`): `ty` 0.0.51, `cuprum` 0.1.0, CPython 3.14.
  This task does not call any cuprum API — the changed fixture reads a file with
  `pathlib.Path.joinpath(...).read_text(...)` and touches no external command —
  so no cuprum catalogue, allowlist, or run/output option is in scope (confirmed
  by reading `tests/conftest.py`: `read_repo_text` uses only `pathlib`; cuprum's
  `ProgramCatalogue`/`ProjectSettings` are used only by the unrelated
  `single_program_catalogue` fixture, which is out of scope). The only
  load-bearing external behaviour is the `ty` typechecker's handling of a
  variadic `Protocol` defined inside a `TYPE_CHECKING` block.

- `ty` 0.0.51 accepts a `typing.Protocol` whose `__call__` is
  `def __call__(self, *parts: str) -> str`, treats an object of that type as
  callable with `*str` arguments, and reports a non-`str` argument as
  `error[invalid-argument-type]`. Verified by patching the real
  `tests/conftest.py` so the Protocol sat entirely inside its
  `if typ.TYPE_CHECKING:` block and annotating `read_repo_text` as
  `-> RepoTextReader`, then running `uv run ty check tests` ("All checks
  passed!") and, with a scratch `read_repo_text(123)` call, capturing:

      error[invalid-argument-type]: Argument to bound method
        `RepoTextReader.__call__` is incorrect
        --> tests/test_scratch_red.py:13:20
         |
      13 |     read_repo_text(123)
         |                    ^^^ Expected `str`, found `Literal[123]`
      Found 1 diagnostic

- A `RepoTextReader` Protocol defined **wholly inside** conftest's
  `if typ.TYPE_CHECKING:` block, imported by a scratch `tests/test_*.py` module
  via `from conftest import RepoTextReader` under that module's own
  `TYPE_CHECKING` guard, is collected and run by `uv run pytest` ("1 passed",
  prepend import mode, no `tests/__init__.py`) and resolves for `uv run ty
  check` ("All checks passed!"). This disproves the round-1 claim that the
  Protocol "must exist at runtime"; it does not.

- interrogate scans inside the `TYPE_CHECKING` block. Verified by removing the
  `__call__` docstring from the `TYPE_CHECKING`-only Protocol and running
  `uv run interrogate -c pyproject.toml tests/conftest.py`, which reported
  `RESULT: FAILED (minimum: 100.0%, actual: 92.3%)`. So the class-plus-`__call__`
  docstring burden is identical whether the Protocol is at module level or
  inside the guard; the docstrings are required either way.

- The pytest config (`pyproject.toml` `[tool.pytest.ini_options]`) sets no
  `import-mode` and the tree has no `tests/__init__.py`, so `conftest.py` is
  importable as the top-level module `conftest` — hence the import path
  `from conftest import RepoTextReader` rather than `from tests.conftest import
  ...` (the latter does not resolve in this layout).

## Plan of work

Four atomic, independently committable, gate-passable work items, in dependency
order. WI-1 is markdown-only and runs `make markdownlint` and `make nixie` in
addition to `make all`. WI-2 through WI-4 each end with the full `make all`
gate. The ordering is load-bearing: WI-1 lands the developers'-guide carve-out
**before** any commit introduces a `from conftest import RepoTextReader` import,
so no interim commit ever contradicts the source-of-truth guide (round-1
blocking point 1).

### WI-1: Carve out the type-only `TYPE_CHECKING`-import exception in the guide

Documentation to read first: `docs/developers-guide.md` "Shared test
scaffolding" (lines 20-47, especially the prohibition at lines 29-35); AGENTS.md
"Markdown guidance" (80-column prose wrap, 120-column code wrap, dash bullets);
`docs/documentation-style-guide.md`. Skills to load: none code-specific; honour
`en-gb-oxendict` Oxford spelling.

Implements: AGENTS.md "Documentation maintenance" / "Internal interfaces"
(record internally facing conventions in the developers' guide); roadmap task
1.2.9 (`docs/roadmap.md` lines 148-154), as the enabling precondition for the
typed fixture.

Why first: the guide as it reads on `origin/main` forbids importing from
`conftest` outright and states no `TYPE_CHECKING` exception
(`docs/developers-guide.md` lines 29-35). The plan's central move —
`from conftest import RepoTextReader` under a `TYPE_CHECKING` guard — would
contradict that rule if landed before the guide permits it. Landing the
carve-out in its own first commit means every later commit is consistent with
the guide.

Edit `docs/developers-guide.md`, "Shared test scaffolding" section. After the
existing paragraph that forbids importing helpers from `conftest` (lines 29-35),
add a short paragraph that:

1. States the narrow exception: a shared *type* (such as the `RepoTextReader`
   `Protocol` that types the `read_repo_text` fixture's return value) may be
   imported from `conftest` **only** under an `if TYPE_CHECKING:` guard
   (`from conftest import RepoTextReader`).
2. Explains why this does not reintroduce the fragility the rule guards against:
   a `TYPE_CHECKING` import is `False` at runtime, so it creates no runtime
   cross-module import and cannot fail under any pytest import mode; it conveys
   a type only, never a fixture or helper *value* (fixtures are still consumed
   by parameter name).
3. Notes that the variadic fixture's return type is expressed as a named
   `typing.Protocol` defined inside the `TYPE_CHECKING` block of
   `tests/conftest.py` (rather than `Callable[..., str]`), because the `...`
   wildcard disables per-call argument-shape checking.

Keep prose wrapped at 80 columns and any code span short. Do not weaken the
existing prohibition on importing fixture/helper *values* or reaching into
another module's private symbols — those remain forbidden.

Tests: none (documentation only).

Validation: `make markdownlint` and `make nixie` (no Mermaid is added, so nixie
validates nothing new but must still pass), plus `make all` to keep the
aggregate gate green. Commit, e.g. "Permit type-only TYPE_CHECKING conftest
imports in dev guide".

### WI-2: Define the `RepoTextReader` Protocol and return it from the fixture

Documentation to read first: `docs/developers-guide.md` "Shared test
scaffolding" (now including the WI-1 carve-out);
`docs/execplans/roadmap-1-2-7.md` "Interfaces and dependencies" (lines 618-656);
`.rules/python-typing.md` (standard aliases `typ`, `cabc`; `TYPE_CHECKING` guard
guidance). Skills to load: `python-router`, then `python-types-and-apis`
(Protocols, variadic callables, public-callback typing).

Implements: roadmap task 1.2.9 (`docs/roadmap.md` lines 148-154); the 1.2.7
"Interfaces" tightening note; AGENTS.md "Typechecking" and the `.rules`
python-typing conventions.

Edit `tests/conftest.py`:

1. Inside the existing `if typ.TYPE_CHECKING:` block (which already imports
   `collections.abc as cabc` and `cuprum.program.Program`), add the
   `RepoTextReader` Protocol. It is defined **wholly inside** the guard: with
   `from __future__ import annotations` already present (line 19), the fixture's
   `-> RepoTextReader` return annotation is a lazy string never evaluated at
   runtime, so the class need not exist at runtime (verified — see "Verified
   facts"). interrogate scans inside the guard, so the class needs a class
   docstring and `__call__` needs a method docstring (verified). Use numpy-style
   docstrings to match the file:

       if typ.TYPE_CHECKING:
           import collections.abc as cabc

           from cuprum.program import Program

           class RepoTextReader(typ.Protocol):
               """A reader for a repo-relative UTF-8 text file.

               The reader joins its positional ``parts`` under the repository
               root and returns the named file's UTF-8 text. Expressing the
               variadic shape as a ``Protocol`` (rather than
               ``Callable[..., str]``) restores per-call argument-shape checking
               that the ``...`` wildcard disabled.
               """

               def __call__(self, *parts: str) -> str:
                   """Return the UTF-8 text of the file named by ``parts``."""
                   ...

2. Change the `read_repo_text` fixture's return annotation from
   `cabc.Callable[..., str]` to `RepoTextReader`, and update its numpy-style
   "Returns" section to name `RepoTextReader` (keep the `(*parts: str) -> str`
   gloss). The inner `_read` closure body is unchanged. `cabc` is still imported
   in the guard because the other fixtures (`toml_table`,
   `single_program_catalogue`, `venv_scripts_dir`) still annotate with it, so do
   not remove the `cabc` import.

Tests for this work item (per AGENTS.md "Python verification and testing"): this
is a typing-only refactor, so the primary verification is the typechecker plus a
red/green probe rather than a new behavioural test in this WI (the behavioural
regression test is added in WI-3, which owns `test_conftest_helpers.py`). To
prove the tightening has teeth, run a **temporary red probe**: in a scratch
file (not committed), add a `RepoTextReader`-annotated parameter calling
`read_repo_text(123)` and confirm `ty` flags it (`invalid-argument-type`); then
delete the probe before committing. Record the transcript in `Artifacts and
notes`.

Validation: `make all` (Ruff format-check and lint, interrogate 100%, Pylint,
`ty`, pytest). Expect the full suite to pass with the same counts as before.
Commit with an imperative subject, e.g. "Type read_repo_text fixture with a
RepoTextReader Protocol".

### WI-3: Tighten `test_conftest_helpers.py` and pin the variadic signature

Documentation to read first: `docs/developers-guide.md` "Shared test
scaffolding" (now permitting the type-only import); AGENTS.md "Python
verification and testing" (happy/unhappy/edge coverage; snapshot/property
guidance). Skills to load: `python-router`, then `python-types-and-apis` and
`python-testing`.

Implements: roadmap 1.2.9; AGENTS.md testing rules (the changed contract gets a
regression test).

Edit `tests/test_conftest_helpers.py` (the first module to add the consumer
import — permitted because WI-1 has landed the carve-out):

1. In its `if typ.TYPE_CHECKING:` block, add `from conftest import
   RepoTextReader` (the `cabc` import there stays — `toml_table` annotations
   still use it).
2. Change the parameter annotation in `test_read_repo_text_reads_a_known_marker`
   (line 48) from `cabc.Callable[..., str]` to `RepoTextReader`.
3. Add a regression test that pins the *multi-part* call — the behaviour the
   precise signature must keep accepting — so a future over-tightening to
   `Callable[[str], str]` (single-arg) would fail here:

       def test_read_repo_text_joins_multiple_parts(
           read_repo_text: RepoTextReader,
       ) -> None:
           """``read_repo_text`` joins several path parts under the repo root."""
           text = read_repo_text("docs", "roadmap.md")
           assert "1.2.9" in text, "multi-part read did not reach docs/roadmap.md"

   This test documents and locks the variadic contract at runtime (the
   typechecker locks it statically). Its docstring states the behaviour, not the
   mechanics (AGENTS.md "Test documentation should omit examples that only
   restate the test logic").

Property/snapshot/e2e: none warranted. There is no invariant over a range of
inputs that a property test would add value to (the reader is a thin
`joinpath().read_text()`), and no multivariant output format, so neither
Hypothesis/CrossHair nor syrupy applies here (AGENTS.md). The two example-based
tests (single-part existing, multi-part new) cover the happy path and the shape
the type change is about.

Validation: `make all`. Expect one additional passing test
(`test_read_repo_text_joins_multiple_parts`) and no regressions. Commit, e.g.
"Pin read_repo_text variadic contract in conftest-helper tests".

### WI-4: Tighten the remaining call-site annotations

Documentation to read first: AGENTS.md "Keep file size manageable" (400-line
cap); the roadmap note on 1.2.18 (`docs/roadmap.md` lines 210-216) explaining
that `test_state_layout_reference.py` sits at the cap. Skills to load:
`python-router`, then `python-types-and-apis`.

Implements: roadmap 1.2.9.

Edit `tests/test_interrogate_gate.py`:

1. In its `if typ.TYPE_CHECKING:` block, add `from conftest import
   RepoTextReader` (keep `cabc` — other annotations in the file still use it).
2. Change the parameter annotation in `test_makefile_invokes_interrogate`
   (line 51) from `cabc.Callable[..., str]` to `RepoTextReader`.

Edit `tests/test_state_layout_reference.py` (at the 400-line cap — every edit
here must keep the file at or below 400 lines):

1. In its `if typ.TYPE_CHECKING:` block, add `from conftest import
   RepoTextReader`. If `cabc` becomes unused after step 2 below, drop the
   `import collections.abc as cabc` line and verify Ruff is clean (a removed
   unused import keeps the file at or under 400 lines — acceptable, net
   negative). If `cabc` is still used elsewhere in the file, replace its import
   line in place with the new import or add the new import on a net-neutral
   line. Either way the net line delta must be zero or negative; confirm with
   `wc -l`.
2. Change the three parameter annotations at lines 264, 276, 291 from
   `cabc.Callable[..., str]` to `RepoTextReader`, each on its existing line.

Before committing this file, run
`wc -l tests/test_state_layout_reference.py` and confirm the count is `<= 400`.
If it exceeds 400, stop and escalate per Tolerances (do not split the module —
that is 1.2.18).

Tests: no new tests; the existing guard tests in
`test_state_layout_reference.py` and the interrogate-gate tests already exercise
these call sites and must keep passing unchanged. The static guarantee is
verified by `make typecheck` inside `make all`.

Validation: `make all`. Expect unchanged test counts and a clean `ty` pass.
Commit, e.g. "Type remaining read_repo_text call sites with RepoTextReader".

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-9`.

1. Confirm the branch and a clean tree before starting. Running
   `git branch --show-current` reports `roadmap-1-2-9`, and `git status
   --short` reports nothing (beyond this plan).

2. WI-1 — edit `docs/developers-guide.md`, then run the markdown gates and the
   aggregate gate: `make markdownlint`, `make nixie`, and `make all` each pass.
   Commit.

3. WI-2 — edit `tests/conftest.py`, then run the temporary red probe and the
   gate. `uv run ty check tests` reports the clean state, and `make all` runs
   the full suite green with unchanged counts:

       $ uv run ty check tests
       All checks passed!

   For the red probe, create a throwaway `tests/test_scratch_red.py` with a
   `RepoTextReader`-annotated parameter calling `read_repo_text(123)`, run
   `uv run ty check tests`, and confirm it fails, then delete the file before
   committing:

       $ uv run ty check tests
       error[invalid-argument-type]: Argument to bound method
         `RepoTextReader.__call__` is incorrect
         ... Expected `str`, found `Literal[123]`
       Found 1 diagnostic

   Then run `make all` and expect the full suite green. Commit.

4. WI-3 — edit `tests/test_conftest_helpers.py` and add the multi-part test.
   `uv run pytest tests/test_conftest_helpers.py -q` reports the module passing
   with one extra test, then `make all` is run for the aggregate gate:

       $ uv run pytest tests/test_conftest_helpers.py -q
       ........ [100%]
       8 passed

   Commit.

5. WI-4 — edit `tests/test_interrogate_gate.py` and
   `tests/test_state_layout_reference.py`. Confirm the cap is respected, then
   run the gate:

       $ wc -l tests/test_state_layout_reference.py
       400 tests/test_state_layout_reference.py

   Then run `make all` and expect unchanged test counts and a clean `ty` pass.
   Commit.

Commit after each work item once its gate is green (AGENTS.md "Committing":
file-based commit message, imperative subject ~50 chars, wrapped body).

## Validation and acceptance

Quality criteria (what "done" means):

- Documentation: `docs/developers-guide.md` permits the type-only
  `TYPE_CHECKING` `conftest` import before any consumer adds it, so no commit
  contradicts the guide.
- Tests: `make test` passes with one net-new test
  (`test_read_repo_text_joins_multiple_parts`) and otherwise unchanged counts
  and outcomes. The new test fails if the fixture's variadic contract is broken
  (e.g. narrowed to a single argument).
- Typecheck: `make typecheck` (`ty check novel_ralph_skill tests`) passes. The
  acceptance proof of the tightening: a temporary `read_repo_text(123)` call
  annotated as `RepoTextReader` makes `ty` report
  `error[invalid-argument-type]` — it would have passed under the old
  `Callable[..., str]`. This probe is run during WI-2 and then removed.
- Lint/format/docstrings: `make lint` (Ruff, interrogate 100%, Pylint) and
  `make check-fmt` pass; the new `Protocol` class and `__call__` carry
  docstrings (interrogate scans inside the `TYPE_CHECKING` block).
- Markdown: `make markdownlint` and `make nixie` pass after the WI-1 edit.
- File size: `tests/test_state_layout_reference.py` is `<= 400` lines.

Quality method: `make all` after every work item, plus `make markdownlint` and
`make nixie` for WI-1.

## Idempotence and recovery

Every code edit is an in-place annotation/type change and is re-runnable safely;
no filesystem state, network, or external command is involved. If a work item's
gate fails, revert the working-tree changes for that file
(`git checkout -- <file>`) and reapply. The temporary `ty` red probe is a
throwaway file deleted before commit; if forgotten, `make lint`/`ty` will flag
it, and removing it restores green. No backups or rollback of committed history
are needed because each commit is independently gate-passing.

## Artifacts and notes

Pre-draft verification transcript (locked `ty` 0.0.51), with the Protocol
defined inside conftest's `TYPE_CHECKING` block, to be reproduced in WI-2:

    error[invalid-argument-type]: Argument to bound method
      `RepoTextReader.__call__` is incorrect
      --> tests/test_scratch_red.py:13:20
       |
    13 |     read_repo_text(123)
       |                    ^^^ Expected `str`, found `Literal[123]`
    info: Method defined here
      --> tests/conftest.py:37:13
    Found 1 diagnostic

`from conftest import RepoTextReader` under `TYPE_CHECKING` in a scratch test
module, with `RepoTextReader` defined wholly inside conftest's `TYPE_CHECKING`
block: `uv run ty check tests` reported "All checks passed!" and
`uv run pytest tests/test_scratch_probe.py -q` reported "1 passed".

interrogate scanning inside the `TYPE_CHECKING` block: removing the `__call__`
docstring dropped `uv run interrogate -c pyproject.toml tests/conftest.py` to
`RESULT: FAILED (minimum: 100.0%, actual: 92.3%)`.

## Interfaces and dependencies

Add no dependencies. In `tests/conftest.py`, define the type **inside** the
existing `TYPE_CHECKING` guard (not at module level):

    # tests/conftest.py
    from __future__ import annotations

    import typing as typ

    if typ.TYPE_CHECKING:
        import collections.abc as cabc

        from cuprum.program import Program

        class RepoTextReader(typ.Protocol):
            """A reader for a repo-relative UTF-8 text file."""

            def __call__(self, *parts: str) -> str:
                """Return the UTF-8 text of the file named by ``parts``."""
                ...

    @pytest.fixture
    def read_repo_text(project_root: Path) -> RepoTextReader: ...

Consuming modules (`tests/test_conftest_helpers.py`,
`tests/test_interrogate_gate.py`, `tests/test_state_layout_reference.py`) import
the type under their `if typ.TYPE_CHECKING:` block:

    if typ.TYPE_CHECKING:
        from conftest import RepoTextReader

and annotate the fixture parameter as `read_repo_text: RepoTextReader`. No other
fixture signature changes; `cabc.Callable[...]` remains correct for the
non-variadic fixtures (`toml_table`, `single_program_catalogue`,
`venv_scripts_dir`) and is out of scope for this task.

## Revision note

Round 2 (2026-06-22). Resolved both design-review blocking points.

- Blocking point 1 (dev-guide ordering): the developers'-guide carve-out for a
  type-only `TYPE_CHECKING` `conftest` import is now WI-1, landing **before**
  any commit introduces `from conftest import RepoTextReader` (the first such
  imports are now in WI-3 and WI-4). No interim commit contradicts the
  source-of-truth guide. The Constraints, Risks, and Decision log sections now
  state the guide is amended first rather than asserting the rule is already
  respected.
- Blocking point 2 (Protocol placement): the `RepoTextReader` Protocol is now
  defined **wholly inside** conftest's `if typ.TYPE_CHECKING:` block, not at
  module level. The round-1 "must exist at runtime" justification was
  empirically disproved in this worktree (TYPE_CHECKING-only resolves for `ty`,
  is collected and run by pytest, and still flags `read_repo_text(123)`), and is
  removed. The lazy-annotation rationale (`from __future__ import annotations`)
  and the interrogate-scans-the-guard fact (docstrings still required) are
  documented in Verified facts and the Decision log.

Work-item count is unchanged at four, but reordered: WI-1 is now the
markdown-only carve-out; WI-2 defines the Protocol and retypes the fixture; WI-3
takes the conftest-helper consumer plus the variadic regression test; WI-4 takes
the remaining consumers under the 400-line cap. No cuprum API is in scope (the
fixture touches no external command).
