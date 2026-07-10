# Hoist `parse_global_flags` and `_HUMAN_FLAG` into the shared contract seam

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises and discoveries`,
`Decision Log`, and `Outcomes and retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose and big picture

Today the command-agnostic `--human` global-flag splitter (`parse_global_flags`
and the `_HUMAN_FLAG` constant) lives inside the `novel-state` *command* module,
`novel_ralph_skill/commands/novel_state.py`. Only one command imports it so far
(`novel_ralph_skill/commands/stub.py`, which wires the real `novel_state` entry
point). The four still-stubbed commands (`novel-done`, `novel-compile`,
`desloppify`, `wordcount`) will each need the same splitter when their real
entry points land. If the splitter stays where it is, those four commands must
either import it from a *sibling command module* — coupling, for example,
`novel-done` to `novel-state` for no domain reason — or re-implement it and
drift.

After this change, the splitter lives in a neutral, command-agnostic home in the
shared interface-contract package (`novel_ralph_skill/contract/`), every command
imports the one splitter, and no command depends on a sibling command module.
The `--human` switch is part of the shared contract (design §3.1, Architecture
Decision Record (ADR-003) §3.1),
and `RunContext.human` — the field the splitter ultimately feeds — already lives
in `novel_ralph_skill/contract/runner.py`, so the contract package is the
splitter's rightful seam.

You can observe success three ways. First, `grep -rn "parse_global_flags" \
novel_ralph_skill/commands/` returns only *import* lines, never a *definition*.
Second, `novel_ralph_skill/commands/stub.py` imports the splitter from
`novel_ralph_skill.contract` rather than from
`novel_ralph_skill.commands.novel_state`. Third, the full quality gate — `make
all` — passes, including the existing `parse_global_flags` unit suite and the
`novel-state check` behavioural and end-to-end tests, which continue to exercise
the moved splitter through its new import path.

This task is roadmap item 1.3.3 ("Hoist `parse_global_flags` and `_HUMAN_FLAG`
into a shared seam before the second command imports them cross-command"). It
advances the step-1.3 hypothesis — one envelope, output-mode switch, and
exit-code helper serving all five commands — by giving the splitter its neutral
home *before* the import direction sets when the second real command lands.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. The dependency direction is `commands → contract`, never the reverse.
   `novel_ralph_skill/contract/` must not import anything from
   `novel_ralph_skill/commands/`. Moving the splitter *into* `contract` is only
   safe because `contract.runner` already imports solely from
   `novel_ralph_skill._freeze`, `novel_ralph_skill.contract.envelope`, and
   `novel_ralph_skill.contract.exit_codes` — none of which touch `commands`. Do
   not introduce a `commands` import into `contract` to make this work.
2. The splitter's *public behaviour* is frozen and must not change: it
   recognizes a `--human` boolean token in any position, removes *every*
   occurrence, and returns `(human: bool, residual: list[str])` with the
   remaining tokens in original order, parsing no working-directory token
   (design line 151 fixes `working/` as a constant, not a flag; ADR-003 §3.1).
   The six parametrized cases in `tests/test_novel_state_check.py`
   (`test_parse_global_flags`: `leading`, `trailing`, `between`, `absent`,
   `multiple`, `other-flag-untouched`) must continue to pass unchanged in
   assertion content.
3. The exit-code contract (design §3.2, ADR-003 Table 2) and the JSON-envelope
   shape (design §3.1) are untouched. This is an import-seam move, not a
   behaviour change. No envelope field, no exit code, and no `RunContext` field
   changes.
4. `WORKING_DIR_NAME` stays in `novel_ralph_skill/commands/novel_state.py`. It
   is a `novel-state`-specific constant (the default state location that command
   reads), not a command-agnostic global-flag concern, and it is part of
   `build_app`'s documented orientation. Do not move it in this task. Only
   `parse_global_flags` and `_HUMAN_FLAG` move.
5. The end-to-end installed-script test
   (`test_installed_novel_state_check_exits_zero` in
   `tests/test_novel_state_check.py`) drives the *installed console script*, not
   the splitter symbol, so it must remain green without edits to its body. Treat
   any need to edit it as a signal that the move broke the entry-point wiring.
6. No new external dependency. The splitter is pure standard library; keep it
   so. `uv.lock` must not change.

## Tolerances (exception triggers)

Thresholds that trigger escalation rather than autonomous action.

1. Scope: this is a small, mechanical move. If the implementation touches more
   than five files or exceeds roughly 80 net changed lines (excluding
   documentation prose), stop and escalate — the scope has been
   misunderstood.
2. Interface: the public signature of `parse_global_flags` must not change. If
   making the move clean appears to require changing its signature or return
   type, stop and escalate.
3. Dependencies: if a new third-party dependency seems required, stop and
   escalate (it should not be).
4. Iterations: if `make all` still fails after three focused fix attempts on the
   same gate, stop and escalate with the failing transcript.
5. Ambiguity: the seam home is decided below (the `contract` package). If
   evidence emerges that the `contract` package is the wrong home — for example
   a circular import that cannot be resolved without violating Constraint 1 —
   stop, record it in the Decision Log, and escalate with the
   `commands/_global_flags.py` fallback the roadmap names.

## Risks

    - Risk: Re-export wiring forgets a `__all__` entry, so a downstream
      `from novel_ralph_skill.contract import parse_global_flags` type-checks at
      runtime but is flagged by linters or omitted from the documented public
      surface.
      Severity: low
      Likelihood: medium
      Mitigation: Work item 2 adds both `parse_global_flags` and (deliberately
      *not* the private `_HUMAN_FLAG`) consideration to `contract/__init__.py`'s
      `__all__`, and Work item 3's test asserts the import resolves from
      `novel_ralph_skill.contract`. `make lint` (ruff + interrogate + pylint)
      catches an unused or missing re-export.

    - Risk: A circular import appears because `contract.runner` is imported very
      early and the move adds a new import edge somewhere.
      Severity: low
      Likelihood: low
      Mitigation: The splitter has *no* imports of its own beyond the standard
      library, so moving it into `contract.runner` adds no new import edge into
      `contract`. `commands/stub.py` already imports `RunContext` and `run` from
      `contract.runner`, so the seam is already on its import graph. Constraint 1
      forbids the reverse edge. A smoke import (`uv run python -c "import
      novel_ralph_skill.commands.stub"`) in the concrete steps confirms no cycle.

    - Risk: `_HUMAN_FLAG` is a private (underscore-prefixed) constant; moving it
      while keeping it private could leave a test that reached into the old
      private name.
      Severity: low
      Likelihood: low
      Mitigation: `grep -rn "_HUMAN_FLAG"` confirms only the splitter body
      references it (no test imports the private constant). The constant moves
      with the function and stays private to its new module.

    - Risk: Documentation drifts — the developers' guide and the moved module's
      docstrings still say the splitter lives in the command module.
      Severity: medium
      Likelihood: high
      Mitigation: Work item 4 updates the module docstrings, the developers'
      guide §"`novel-state check` is the first command…" passage (around line
      318), and runs `make markdownlint` and `make nixie` on the changed
      Markdown. AGENTS.md "Documentation maintenance" requires this.

## Progress

    - [x] Work item 1: Move the splitter and constant into `contract.runner`,
      keeping behaviour identical. (Commit A.)
    - [x] Work item 2: Re-export `parse_global_flags` from the `contract`
      package and reroute the `stub.py` importer. (Commit A.) The test importer
      reroute (the first half of Work item 3's import change) was folded into
      Commit A so the commit gate (`make all`, including `ty check`) stays green;
      `ty` resolves the test's import at type-check time, so a commit that moved
      the splitter without rerouting the test import would have failed the gate.
    - [x] Work item 3: Add the import-seam guard tests (the test importer reroute
      already landed in Commit A). (Commit B.) Added
      `test_parse_global_flags_is_a_contract_seam` and
      `test_novel_state_command_does_not_own_the_splitter` to
      `tests/test_contract_runner.py`, beside the seam they protect.
    - [x] Work item 4: Update module docstrings and the developers' guide;
      validate Markdown. (Commit C.) Reworded the `novel_state` and
      `contract.runner` module docstrings, added `parse_global_flags` to the
      `contract/__init__.py` surface (the `__all__` and `__init__` docstring
      landed in Commit A), and extended the developers' guide contract-surface
      and `novel-state check` passages. The users' guide is deliberately
      untouched (see Decision Log).

## Surprises and discoveries

    - `ty check` resolves the test module's `from ...novel_state import
      parse_global_flags` at type-check time, so Commit A could not be green
      while the test still imported the splitter from the old path. The test
      import reroute (planned for Work item 3) was therefore folded into
      Commit A. Work item 3 retains only the new seam-guard tests.
    - CodeRabbit's first pass flagged only the execplan Markdown: ampersand-to-
      "and" in three headings and an ADR first-mention expansion. Both applied.
      Its "RFC first mention" finding was a false positive — the execplan
      contains no `RFC` token — and was skipped.

## Decision log

    - Decision: Hoist the splitter into `novel_ralph_skill/contract/runner.py`
      (re-exported through `novel_ralph_skill/contract/__init__.py`), rather than
      into a new `novel_ralph_skill/commands/_global_flags.py`.
      Rationale: The roadmap (item 1.3.3 "Success") names both options as
      acceptable ("e.g. `contract.runner` or `commands/_global_flags.py`"). The
      `contract` package wins because `--human` is, by design §3.1 and ADR-003
      §3.1, part of the *shared interface contract*, and the splitter's product —
      the `human: bool` — is consumed by `RunContext.human`, which already lives
      in `contract.runner`. Co-locating the splitter with the `RunContext` field
      it feeds keeps the contract's output-mode machinery in one package and
      avoids creating a fifth `commands/` module whose only job is to hold one
      function. `commands/_global_flags.py` would still satisfy the neutrality
      requirement, but it adds a module and leaves the `--human` contract split
      across two packages. The `contract` package also already re-exports its
      public surface through `__init__.py`, giving the splitter a documented
      front door at `novel_ralph_skill.contract.parse_global_flags`.
      Date/Author: 2026-06-23, planning agent.

    - Decision: `WORKING_DIR_NAME` does not move.
      Rationale: It is the `novel-state` default state location (a per-command
      constant), not a command-agnostic global-flag concern. Constraint 4.
      Date/Author: 2026-06-23, planning agent.

    - Decision: `_HUMAN_FLAG` stays private to its new home and is not added to
      the `contract` package `__all__`.
      Rationale: It is an implementation detail of the splitter; only
      `parse_global_flags` is the public seam. Keeping it private avoids widening
      the contract's public surface unnecessarily.
      Date/Author: 2026-06-23, planning agent.

    - Decision: `docs/users-guide.md` is deliberately left untouched.
      Rationale: This is an internal seam move with no user-visible behaviour
      change — the `--human` flag works identically (Work item 4 step 3).
      Date/Author: 2026-06-23, implementing agent.

    - Decision: No property or mutation testing (`hypothesis`, `crosshair`,
      `mutmut`) is added for this task.
      Rationale: This is a pure import-seam move with no new invariant over a
      range of inputs. The existing six parametrized `test_parse_global_flags`
      cases (`leading`, `trailing`, `between`, `absent`, `multiple`,
      `other-flag-untouched`) already pin the splitter's behaviour exhaustively
      over flag positions, and the two new structural guards pin the seam. The
      `python-verification` router confirms an adversary is unwarranted here.
      Date/Author: 2026-06-23, implementing agent.

    - Decision: `stub.py` imports `RunContext`, `parse_global_flags`, and `run`
      from the package front door `novel_ralph_skill.contract`, not from the
      `contract.runner` submodule.
      Rationale: Work item 2 step 2 prefers the public-seam front door so
      consumers depend on the curated re-export. Rather than split the import
      across the front door (`parse_global_flags`) and the submodule
      (`RunContext, run`), the existing `RunContext, run` import was moved up to
      the front door too, so `stub.py` depends on the one documented public
      surface. All three symbols are in `contract.__all__`.
      Date/Author: 2026-06-23, implementing agent.

## Outcomes and retrospective

    - All four work items landed across three atomic commits (A: move +
      re-export + reroute; B: seam guards; C: documentation), each gated with a
      green `make all`. The acceptance checks hold: `grep -rn "def
      parse_global_flags" novel_ralph_skill/` returns the single definition in
      `contract/runner.py`; `grep -rn "parse_global_flags"
      novel_ralph_skill/commands/` returns only the `stub.py` import line; and
      the two new guard tests pass beside the seam.
    - Scope stayed within tolerance: five source/test/doc files plus the
      execplan, a small mechanical move with no signature, exit-code, or
      envelope change, and `uv.lock` untouched.
    - One deviation from the planned commit grouping: the `novel-state` test
      import reroute was folded into Commit A (not Commit B), because `ty check`
      resolves the import at type-check time and the commit gate would otherwise
      have failed. Recorded in Surprises and the Progress notes.

## Context and orientation

This is a small Python package, `novel_ralph_skill`, that ships five console
scripts forming the deterministic spine of a novel-writing harness. The reader
needs to know only four files and one package.

1. `novel_ralph_skill/contract/` — the shared interface-contract package. It
   owns the JSON envelope (`envelope.py`), the exit-code table (`exit_codes.py`),
   and the `run` wrapper plus its value types (`runner.py`). Its `__init__.py`
   re-exports a curated public surface and lists it in `__all__`. The `run`
   wrapper in `runner.py` drives a Cyclopts app and owns every `sys.exit` and
   every envelope emission; `RunContext` (also in `runner.py`) is the frozen
   per-invocation record carrying `command`, `working_dir`, and `human`. The
   package imports only from `novel_ralph_skill._freeze` and its own
   submodules — it never imports from `novel_ralph_skill/commands/`.

2. `novel_ralph_skill/commands/novel_state.py` — the `novel-state` command
   module. It currently *defines* the splitter at module scope:

       _HUMAN_FLAG = "--human"

       def parse_global_flags(argv: list[str]) -> tuple[bool, list[str]]:
           ...
           residual = [token for token in argv if token != _HUMAN_FLAG]
           human = len(residual) != len(argv)
           return human, residual

   It also defines `WORKING_DIR_NAME = "working"` (which stays here), the private
   `_check()` body, and `build_app()`.

3. `novel_ralph_skill/commands/stub.py` — wires the five console-script entry
   points. The `novel_state()` entry point imports `WORKING_DIR_NAME`,
   `build_app`, and `parse_global_flags` from
   `novel_ralph_skill.commands.novel_state` (lines 17–21) and already imports
   `RunContext` and `run` from `novel_ralph_skill.contract.runner` (line 22). It
   pre-parses `--human` off `sys.argv[1:]` *before* calling `run`, because `run`
   stamps the human selection into the envelope even on the body-less usage
   (exit 2) and state-error (exit 3) paths (Decision Log B3 in the module
   docstring).

4. `tests/test_novel_state_check.py` — the behavioural, unit, and end-to-end
   tests for `novel-state check`. It imports `build_app` and
   `parse_global_flags` from `novel_ralph_skill.commands.novel_state` (lines
   36–39). It contains the parametrized `test_parse_global_flags` unit suite
   (lines 276–300) and the POSIX-only installed-script e2e
   `test_installed_novel_state_check_exits_zero` (lines 343–372), which drives
   the installed console script via `cuprum` and is unaffected by an import-seam
   move.

The term *seam* means the single, neutral place a shared helper lives so every
consumer imports it from one home rather than from each other. The term *global
flag* means a flag (here only `--human`) that applies to every command,
independent of the subcommand, and so is pre-parsed off `argv` before the
command's Cyclopts app runs.

Authoritative references for this task:

- `docs/novel-ralph-harness-design.md` §3.1 (output modes; the `--human`
  switch is the shared contract's responsibility).
- `docs/adr-003-shared-interface-contract.md` §3.1 (the `--human` rendering
  switch is a functional requirement of the one shared contract).
- `docs/developers-guide.md`, the "The shared JSON envelope" section (the
  contract package's public surface) and the `novel-state check` passage near
  line 318 (the pre-parse-before-`run` convention).
- `AGENTS.md` — quality gates (`make check-fmt`, `make lint`, `make typecheck`,
  `make test`, `make audit`; for Markdown `make markdownlint` and `make
  nixie`), the en-GB Oxford-spelling convention, atomic-commit discipline, and
  the abstraction/helper sweep policy (sweep before adding a helper — here we
  are *moving* an existing one, and the sweep confirms there is no rival).
- `docs/scripting-standards.md` — no new cuprum/Cyclopts surface is introduced
  by this task, so its conventions are satisfied by leaving the existing
  splitter behaviour and the e2e's cuprum usage untouched.

### Pinned external-library facts (verified, not recalled)

- Cyclopts is locked at `4.18.0` (`uv.lock`). This task introduces no new
  Cyclopts surface: the splitter is a standard-library `argv` filter that runs
  *before* the Cyclopts app, exactly as it does today. No Cyclopts behaviour is
  relied on by the move itself. The existing `stub.make_stub_app` note that
  `--help`/`--version` exit `0` and an unknown `--option` exits `1` (verified
  against cyclopts 4.18.0 in the module docstring) is unchanged.
- cuprum is locked at `0.1.0` (`uv.lock`). The e2e test
  (`test_installed_novel_state_check_exits_zero`) uses `cuprum.sh.make`,
  `cuprum.program.Program`, a single-program `ProgramCatalogue` (via the
  `single_program_catalogue` conftest fixture), and
  `cuprum.sh.ExecutionContext(cwd=...)` with `.run_sync(capture=True)`. This
  task does not change that test, so no new cuprum API is depended upon; the
  pinned APIs the suite already relies on (`sh.make`, `Program`,
  `ProgramCatalogue` allowlisting, `ExecutionContext` cwd, `run_sync` capture)
  are exercised unchanged. Verified by reading
  `tests/test_novel_state_check.py` lines 306–372 and confirming the symbols
  resolve against the locked cuprum in `uv.lock`.
- `pytest-timeout` per-test override: the e2e is marked
  `@pytest.mark.timeout(180)`, which overrides the project default
  (`timeout = 30` in `pyproject.toml`) for that one test under `pytest-xdist`.
  This task does not alter timeouts; no per-test override is added or removed.
- `uv run` resolution: `make` targets invoke tools through
  `$(UV_ENV) $(UV) run …` (see `Makefile`), which resolves against the project
  virtual environment built by `make build` (the `.venv` prerequisite). This
  task adds no dependency, so `uv`'s resolution set is unchanged and `make all`
  rebuilds nothing new.

## Plan of work

The work proceeds in four atomic, independently committable, gate-passable work
items. Each ends with the relevant `make` gate. Do not proceed to the next item
if the current item's gate fails.

### Work item 1: Move the splitter into `contract.runner`

Documentation to read first: `docs/novel-ralph-harness-design.md` §3.1;
`docs/adr-003-shared-interface-contract.md` §3.1; `AGENTS.md`
"Abstraction / port / helper policy" (confirm by sweep that no rival splitter
exists — `grep -rn "--human"` across `novel_ralph_skill/` shows only the one
definition).

Skills to load: `python-router` (it routes to the smaller skills below);
`leta` for navigation; from the router, `python-data-shapes` is not needed (no
new data type), but `python-types-and-apis` is relevant because the moved
function keeps its `tuple[bool, list[str]]` signature.

Implements: ADR-003 §3.1 (the `--human` switch belongs to the shared contract);
design §3.1.

Steps:

1. In `novel_ralph_skill/contract/runner.py`, add the constant and function. A
   natural home is just after the module imports and before `StateInputError`,
   so the global-flag pre-parse reads as the first thing `run`'s callers reach.
   Move the *exact* body and docstring from `novel_state.py` (the docstring
   already cites ADR-003 §3.1 and Decision Log B3/B4 — keep those citations).
   Adjust the docstring's first line only if needed so it reads naturally in its
   new home; do not change the documented behaviour.

       _HUMAN_FLAG = "--human"


       def parse_global_flags(argv: list[str]) -> tuple[bool, list[str]]:
           """Split the ``--human`` global flag off ``argv`` (ADR-003 §3.1)."""
           residual = [token for token in argv if token != _HUMAN_FLAG]
           human = len(residual) != len(argv)
           return human, residual

2. In `novel_ralph_skill/commands/novel_state.py`, delete the `_HUMAN_FLAG`
   constant and the `parse_global_flags` function (lines 41–71). Leave
   `WORKING_DIR_NAME` and everything below the splitter intact.

At the end of this item, `novel_state.py` no longer defines the splitter and
`runner.py` does. `stub.py` and the test still import from the old path, so the
package is momentarily broken — that is acceptable *within* item 1 because items
1 and 2 are designed to be committed together if a single green commit is
preferred. To keep each commit independently gate-passable, prefer to fold the
`stub.py` reroute (the first half of Work item 2) into the *same* commit as this
move, so no commit leaves an unresolved import. The Progress section records the
chosen grouping.

Tests for this item: none new yet (the move is covered by the existing suite
once the importers are rerouted in item 2/3). The guard test is added in item 3.

Validation: defer the full gate to the end of the combined item-1+stub-reroute
commit (see Work item 2), because the package does not import cleanly until the
`stub.py` consumer is rerouted.

### Work item 2: Re-export from `contract` and reroute `stub.py`

Documentation to read first: `docs/developers-guide.md` "The shared JSON
envelope" section (the `contract` package public surface and its `__all__`);
`docs/novel-ralph-harness-design.md` §3.1.

Skills to load: `python-router` → `python-types-and-apis` (public surface and
`__all__` discipline); `leta` (`leta refs parse_global_flags` to confirm every
importer is found and rerouted).

Implements: roadmap 1.3.3 Success criterion ("every command imports the one
splitter, and no command depends on a sibling command module"); design §3.1.

Steps:

1. In `novel_ralph_skill/contract/__init__.py`, import `parse_global_flags` from
   `novel_ralph_skill.contract.runner` alongside the existing `runner` imports,
   and add `"parse_global_flags"` to `__all__` (keep `__all__` alphabetically
   ordered as the file already is). Update the module docstring's "public
   surface re-exported here is …" sentence to include `parse_global_flags`.

2. In `novel_ralph_skill/commands/stub.py`, change the import block (lines
   17–22). Import `WORKING_DIR_NAME` and `build_app` from
   `novel_ralph_skill.commands.novel_state` (these stay there), and import
   `parse_global_flags` together with `RunContext` and `run` from
   `novel_ralph_skill.contract` (the package front door) — or from
   `novel_ralph_skill.contract.runner` to match the existing `RunContext, run`
   import on line 22. Prefer the package front door
   (`novel_ralph_skill.contract`) for the public seam so consumers depend on the
   re-export, not the submodule; if you keep `RunContext, run` on the submodule
   import for minimal churn, import `parse_global_flags` from the same submodule
   for consistency and record the choice in the Decision Log. Either way, the
   result is that `stub.py` no longer imports `parse_global_flags` from the
   `novel_state` command module.

3. Smoke-check the import graph (no cycle):

       uv run python -c "import novel_ralph_skill.commands.stub; \
       from novel_ralph_skill.contract import parse_global_flags; \
       print(parse_global_flags(['--human','check']))"

   Expect: `(True, ['check'])`.

Tests for this item: no new test file yet; the reroute is covered by the
existing `novel-state check` behavioural suite once item 3 reroutes the test
import. (If items 1 and 2 are committed together, the existing suite already
exercises the moved splitter through `stub.novel_state()`.)

Validation (this is the first fully green commit): from the worktree root, run
`make all`. Expect `make check-fmt`, `make lint`, `make typecheck`, and `make
test` to pass. The `novel-state check` behavioural tests and the
`test_parse_global_flags` unit suite must pass because they drive the splitter
through `stub.novel_state()` and (after item 3) the rerouted import.

### Work item 3: Reroute the test importer and add an import-seam guard

Documentation to read first: `AGENTS.md` "Python verification and testing"
(keep tests in `tests/`; unit + behavioural coverage); `docs/developers-guide.md`
the `novel-state check` passage.

Skills to load: `python-router` → `python-testing` (pytest import discipline and
parametrization). Property testing (`hypothesis`/`crosshair`) is **not**
warranted here: this is a pure import-seam move with no new invariant over a
range of inputs, and the existing six parametrized cases already pin the
splitter's behaviour exhaustively over flag positions. Record this verification
decision in the Decision Log. Do **not** add a Hypothesis or CrossHair suite for
this task; `mutmut` mutation testing is likewise out of scope for a move.

Implements: roadmap 1.3.3 Success criterion (the *one* splitter; no
sibling-command dependency); Constraint 2 (frozen behaviour).

Steps:

1. In `tests/test_novel_state_check.py`, change the import (lines 36–39): import
   `build_app` from `novel_ralph_skill.commands.novel_state` and
   `parse_global_flags` from `novel_ralph_skill.contract` (the public seam). The
   existing `test_parse_global_flags` parametrized suite (lines 276–300) now
   exercises the moved splitter through its new home without any change to its
   assertions — its six cases (`leading`, `trailing`, `between`, `absent`,
   `multiple`, `other-flag-untouched`) are the behavioural pins for Constraint 2.

2. Add a small **import-seam guard** test. It belongs with the splitter's
   contract, so add it to `tests/test_contract_runner.py` (the contract-package
   test module) — or, if that module's scope feels wrong, to a focused new
   assertion near the `test_parse_global_flags` block. Prefer
   `tests/test_contract_runner.py` so the guard lives beside the seam it
   protects. The guard asserts two things:

   - `parse_global_flags` is importable from the contract package front door
     and is the *same object* as the one on `contract.runner`:

         from novel_ralph_skill import contract
         from novel_ralph_skill.contract import runner

         def test_parse_global_flags_is_a_contract_seam() -> None:
             """The splitter is the contract package's public seam, not a
             command's."""
             assert contract.parse_global_flags is runner.parse_global_flags
             assert "parse_global_flags" in contract.__all__

   - The `novel_state` *command* module no longer defines the splitter, proving
     no command can be a sibling source for it:

         import novel_ralph_skill.commands.novel_state as novel_state

         def test_novel_state_command_does_not_own_the_splitter() -> None:
             """The command module no longer defines the global-flag splitter."""
             assert not hasattr(novel_state, "parse_global_flags")
             assert not hasattr(novel_state, "_HUMAN_FLAG")

   Give each test a docstring that states the contract it guards (per AGENTS.md
   "Illustrate with clear examples" — but omit examples that merely restate the
   test logic). These two tests *fail before* the move (the splitter is defined
   on `novel_state` and absent from `contract`) and *pass after*, satisfying the
   red-green discipline in the `execplans` skill and AGENTS.md.

Tests added/updated by this item:

- Updated: the import in `tests/test_novel_state_check.py`; the existing
  `test_parse_global_flags` suite now runs against the new home (behavioural
  pin, no assertion change).
- New unit/structural guard: `test_parse_global_flags_is_a_contract_seam` and
  `test_novel_state_command_does_not_own_the_splitter` in
  `tests/test_contract_runner.py`. These are the seam regression guard.
- Unchanged: the e2e `test_installed_novel_state_check_exits_zero` (Constraint
  5) — confirm it stays green without edits.

Validation: from the worktree root, run `make all`. Expect the two new guard
tests to appear in the `pytest` output and pass, the `test_parse_global_flags`
suite to pass, and the full gate (`check-fmt`, `lint`, `typecheck`, `test`) to
be green. To prove the red-green discipline, before applying the move you may
temporarily run only the two guard tests and observe them fail; after the move
they pass.

### Work item 4: Update documentation

Documentation to read first: `docs/developers-guide.md` (the passage near line
318 describing the pre-parse-before-`run` convention and the contract package
surface); `AGENTS.md` "Documentation maintenance" and "Markdown guidance";
`docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` (enforce en-GB Oxford spelling in all prose);
`leta` only if cross-referencing symbols.

Implements: AGENTS.md "Documentation maintenance" (update the developers' guide
when an internal interface/seam moves); design §3.1 (the contract owns
`--human`).

Steps:

1. Update the moved-from and moved-to module docstrings so they describe reality:

   - `novel_ralph_skill/commands/novel_state.py` module docstring currently says
     the module hosts "the standard-library `--human` pre-parse the entry point
     performs". Reword so it no longer claims to *own* the splitter; instead note
     that the `--human` pre-parse now lives in the shared contract package and
     this module hosts the read-only `novel-state` app and its `WORKING_DIR_NAME`
     default. Keep the ADR-003 §3.1 and design-line-151 citations.
   - `novel_ralph_skill/contract/runner.py` module docstring should mention that
     it now also hosts the command-agnostic `--human` global-flag splitter
     (`parse_global_flags`), the pre-parse every command performs before `run`.
   - `novel_ralph_skill/contract/__init__.py` docstring: add
     `parse_global_flags` to the "public surface re-exported here is …" list.

2. Update `docs/developers-guide.md`: in the contract-package public-surface
   paragraph ("The shared implementation lives in `novel_ralph_skill/contract/`.
   Its public surface is …"), add `parse_global_flags` to the enumerated surface.
   In the `novel-state check` passage near line 318 ("its entry point pre-parses
   the single `--human` flag off argv before `run`"), add a clause noting the
   splitter is the *shared* `parse_global_flags` from the contract package, so
   every command pre-parses `--human` through one seam rather than re-implementing
   it. Wrap prose at 80 columns (AGENTS.md "Markdown guidance").

3. Consider whether `docs/users-guide.md` needs a change: it does **not** — this
   is an internal seam move with no user-visible behaviour change (the `--human`
   flag works identically). Record this in the Decision Log so the next agent
   knows the users' guide was deliberately left untouched.

Tests for this item: none (documentation only).

Validation: from the worktree root, run `make markdownlint` and `make nixie`
(the developers' guide is Markdown; `nixie` validates any Mermaid, of which this
change adds none, but AGENTS.md requires running it on Markdown changes). Then
run `make all` once more to confirm the whole gate is green after the docstring
edits (docstrings are linted by `interrogate` and `ruff`).

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-3`.

1. Confirm the starting state — the splitter is defined exactly once, in the
   command module:

       grep -rn "def parse_global_flags\|_HUMAN_FLAG = " novel_ralph_skill/

   Expect a single definition in `novel_ralph_skill/commands/novel_state.py`.

2. Apply Work item 1 (move) and the `stub.py` reroute from Work item 2 in one
   change, then re-export from the contract package (Work item 2). Re-run the
   sweep:

       grep -rn "def parse_global_flags" novel_ralph_skill/

   Expect the single definition now in
   `novel_ralph_skill/contract/runner.py`. Then:

       grep -rn "parse_global_flags" novel_ralph_skill/commands/

   Expect only an *import* line in `stub.py`, no definition.

3. Smoke-import (no cycle):

       uv run python -c "import novel_ralph_skill.commands.stub; \
       from novel_ralph_skill.contract import parse_global_flags; \
       print(parse_global_flags(['check','--human','x']))"

   Expect:

       (True, ['check', 'x'])

4. Apply Work item 3 (test reroute + guard tests). Optionally observe the guards
   fail on an un-moved tree first (red), then pass after the move (green):

       uv run pytest tests/test_contract_runner.py -k "seam or does_not_own" -v

   Expect both guard tests to pass after the move.

5. Run the full gate:

       make all

   Expect a clean run: `check-fmt` OK, `lint` OK (ruff + interrogate 100% +
   pylint), `typecheck` OK (`ty check`), `test` all-passed.

6. Apply Work item 4 (documentation). Then:

       make markdownlint
       make nixie
       make all

   Expect `markdownlint` and `nixie` clean and `make all` green.

Commit grouping (each commit gate-passable):

- Commit A: Work items 1 + 2 (move + re-export + `stub.py` reroute). Gate: `make
  all`. This is the first point the package imports cleanly.
- Commit B: Work item 3 (test reroute + seam guard tests). Gate: `make all`.
- Commit C: Work item 4 (documentation). Gate: `make markdownlint`, `make
  nixie`, then `make all`.

Each commit message uses the imperative mood, ≤ ~50-char subject, with a body
explaining *what* and *why* (AGENTS.md "Committing"). Use the `commit-message`
skill (file-based message; never `-m`).

## Validation and acceptance

Acceptance is behaviour a reviewer can verify:

- Running `grep -rn "def parse_global_flags" novel_ralph_skill/` prints exactly
  one line, in `novel_ralph_skill/contract/runner.py`.
- Running `grep -rn "parse_global_flags" novel_ralph_skill/commands/` prints
  only import lines (in `stub.py`), never a definition, and no `commands/`
  module imports it from a *sibling command* module.
- `uv run python -c "from novel_ralph_skill.contract import \
  parse_global_flags; print(parse_global_flags(['--human']))"` prints
  `(True, [])`.
- The two new guard tests in `tests/test_contract_runner.py` fail on a tree
  where the splitter still lives in `novel_state` and pass after the move.
- The existing `test_parse_global_flags` parametrized suite passes unchanged in
  assertion content.
- The e2e `test_installed_novel_state_check_exits_zero` passes without edits.

Quality criteria (what "done" means), per AGENTS.md:

- Tests: `make test` passes (`pytest -v -n <workers>`), including the two new
  guard tests, the `test_parse_global_flags` suite, the `novel-state check`
  behavioural tests, and the POSIX e2e.
- Lint: `make lint` passes — `ruff check`, `interrogate` at the
  `[tool.interrogate]` threshold (the new tests and the moved/edited docstrings
  must keep 100% docstring coverage), and the PyPy-backed Pylint runner.
- Format: `make check-fmt` passes (`ruff format --check`).
- Typecheck: `make typecheck` passes (`ty check`).
- Audit: `make audit` passes (`pip-audit`) — unchanged, since no dependency is
  added.
- Markdown (Work item 4): `make markdownlint` and `make nixie` pass.

Quality method (how we check): run `make all` from the worktree root after each
commit, plus `make markdownlint` and `make nixie` after the documentation
commit.

## Idempotence and recovery

Every step is re-runnable. The move is a pure relocation of code with no state or
filesystem side effects. If `make all` fails after the move, the most likely
causes are: a stale import path in `stub.py` or the test (fix the import line and
re-run); a missing `__all__` entry (`ruff`/`pylint` flags the unused import or
the docstring surface mismatch — add `"parse_global_flags"` to
`contract/__init__.py`'s `__all__`); or `interrogate` failing because a new guard
test lacks a docstring (add one). To roll back entirely, `git checkout -- \
novel_ralph_skill/ tests/ docs/` from the worktree restores the pre-change tree;
no external resource is touched.

## Artefacts and notes

The seam decision rests on three verified facts from the current tree:

1. The splitter is defined exactly once, in
   `novel_ralph_skill/commands/novel_state.py` (lines 41–71), and referenced by
   exactly three files (`novel_state.py`, `stub.py`, `tests/
   test_novel_state_check.py`) — confirmed by
   `grep -rln "parse_global_flags\|_HUMAN_FLAG"`.

2. `novel_ralph_skill/contract/runner.py` already imports only
   `novel_ralph_skill._freeze`, `novel_ralph_skill.contract.envelope`, and
   `novel_ralph_skill.contract.exit_codes` (plus `cyclopts` under
   `TYPE_CHECKING`). It does not import `commands`, so moving the splitter in
   adds no reverse edge (Constraint 1 holds).

3. `novel_ralph_skill/commands/stub.py` already imports `RunContext` and `run`
   from `novel_ralph_skill.contract.runner` (line 22), so the contract package is
   already on `stub.py`'s import graph — the reroute adds no new dependency, only
   moves one symbol's source from a sibling command to the shared contract.

## Interfaces and dependencies

At the end of this task, these must exist with these exact names and shapes:

- In `novel_ralph_skill/contract/runner.py`:

      _HUMAN_FLAG: str  # module-private constant, value "--human"

      def parse_global_flags(argv: list[str]) -> tuple[bool, list[str]]:
          """Split the ``--human`` global flag off ``argv`` (ADR-003 §3.1)."""

- In `novel_ralph_skill/contract/__init__.py`: `parse_global_flags` re-exported
  and present in `__all__`, so
  `from novel_ralph_skill.contract import parse_global_flags` resolves.

- In `novel_ralph_skill/commands/novel_state.py`: `WORKING_DIR_NAME`,
  `build_app`, and the private `_check` remain; the splitter and `_HUMAN_FLAG`
  are gone.

- In `novel_ralph_skill/commands/stub.py`: `parse_global_flags` imported from
  `novel_ralph_skill.contract` (or `novel_ralph_skill.contract.runner`), never
  from `novel_ralph_skill.commands.novel_state`.

No new third-party dependency. `uv.lock` unchanged. Standard library only for the
splitter.

## Revision note

Initial draft (2026-06-23). Decomposes roadmap 1.3.3 into four atomic work
items: move the splitter into `contract.runner` (Work item 1), re-export it and
reroute `stub.py` (Work item 2), reroute the test import and add a seam guard
(Work item 3), and update documentation (Work item 4). The seam home is decided
as the `contract` package (not a new `commands/_global_flags.py`); see the
Decision Log. No remaining forks: the mechanism is a pure standard-library
relocation, every cited library fact is pinned to the locked versions in
`uv.lock`, and the behavioural contract is held by the existing
`test_parse_global_flags` suite plus the new seam-guard tests.
