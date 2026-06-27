# Collapse the entry-point drive plumbing into one shared `drive` seam

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Roadmap task 7.3.5 was raised to collapse a byte-identical
parse-`--human`/resolve-command-name/drive-via-`run` body that lived in two
production sites: `novel.main` (the multiplexer entry point) and `stub._drive`
(the legacy per-script driver). The step-7.3 hypothesis it serves is the
*command-facade single-home* hypothesis: near-identical entry-point plumbing
must collapse into one explicit home so a refactor of one site cannot silently
break the other.

A load-bearing discovery changes the shape of this task (see Decision Log D1
and Surprises S1): **the second copy no longer exists.** ADR 007 (delivered by
roadmap task 1.2.15, commit `9e95c49`) retired `stub.py`, its `_drive` body, the
four legacy `novel-x` console-scripts, and the `COMMAND_ENTRY_POINTS` registry
symbol. The production surface is now a single `novel` multiplexer with exactly
one console entry point (`pyproject.toml`:
`novel = "novel_ralph_skill.commands.novel:main"`). The
parse-`--human`/resolve-name/drive-via-`run` plumbing therefore survives at
**one** site only: `novel.main` in
`novel_ralph_skill/commands/novel.py`. There is no `stub._drive` to collapse,
and the only remaining `_drive` symbol in the tree is an unrelated *test*
fixture in `tests/contract_drive_support.py` (the in-process command driver),
which this task does not touch.

The task statement offers two mechanisms — "generalise `_drive` to take a name
resolver, or lift the shared body into a contract-level `drive()` helper". The
first is moot (`_drive` is gone). This plan commits, without a fork, to the
second: lift the entry-point drive plumbing out of `novel.main` into a single,
tested, contract-level `drive()` seam, and repoint `novel.main` onto it. This
discharges the constructive arm of the task — the shared body lives in one
explicit home parametrised by the command-name resolver — and installs a
regression guard so the single-home invariant the task asserts is enforced going
forward, rather than relying on the historical accident that only one entry
point happens to remain.

After this change a developer can observe:

- `novel_ralph_skill/contract/runner.py` exposes a public `drive(app, argv, *,
  command, working_dir, human)` (the signature in Decision Log D2) that owns the
  build-`RunContext`-then-`run` plumbing once.
- `novel.main` is a thin entry point: parse `--human`, resolve the name, call
  the seam. It re-spells no `RunContext`/`run` plumbing inline.
- The existing roadmap-1.3.6 routing tripwire
  (`tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`)
  still passes, having been **migrated** to patch the seam (`novel.drive`) that
  `main` now invokes, with the seam itself proven (by a new unit test) to
  forward to `run`. The "routes through the shared seam" invariant is preserved
  transitively (`main` → `drive` → `run`), not silently dropped.
- A net-new structural guard asserts `novel.main` constructs no inline
  `RunContext` and calls neither `RunContext` nor `run` directly, so a future
  entry point that re-inlines the plumbing fails CI.
- `make all` passes; the multiplexer, console-scripts, and entry-point suites
  stay green; the import-laziness profile is unchanged (verified, Work item 4).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do not edit any file outside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-5`. The
  root/control worktree is off-limits for edits.
- The observable behaviour of `novel <sub>` must not change: the same envelope,
  the same exit codes (0/1/2/3/4), the same `working_dir` stamp (the
  absolute, resolved `working/` path from `resolved_working_dir()`), and the
  same `--human` handling. This is a pure internal seam extraction.
- `run` retains its contract: it is `typ.NoReturn` and owns every `sys.exit`
  and every envelope emission (`novel_ralph_skill/contract/runner.py`). The new
  seam wraps `run`; it does not duplicate or bypass `run`'s exit/emit ownership.
- The roadmap-1.3.6 / audit:1.3.6 Finding 3 invariant — "the real `novel` entry
  point routes the multiplexer through the shared `run` seam carrying the
  four-flag-contract app" — must be **preserved**, not deleted. Because `main`
  now calls `run` indirectly through `drive`, the invariant is re-homed: the
  entry-point half is checked at the `drive` boundary (`main` forwards the
  four-flag-contract app to `drive`), and a complementary unit test proves
  `drive` forwards that app to `run`. Deleting the assertion rather than
  migrating it is a Constraint violation (escalate).
- The import-laziness profile must be preserved: importing
  `novel_ralph_skill.commands.novel` must still pull in no leaf command module
  (the deferred imports stay inside `_build_mount_table`), and importing
  `novel_ralph_skill.contract.runner` must not pull in any `commands` module
  (no `contract`→`commands` layering inversion may be introduced by the new
  seam). The seam therefore takes the resolved name and resolved working_dir as
  *arguments*; it does not import `commands.names` or `state_sourcing`.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (AGENTS.md; en-gb-oxendict).
- No single code file may exceed 400 lines (AGENTS.md). `runner.py` is 250 lines
  today; the ~35-line seam keeps it under 400 (Decision Log D3 fallback is
  retained but moot).
- 100% docstring coverage (`interrogate`) over `PYTHON_TARGETS`: every new
  function and module carries a docstring; AGENTS.md's example requirement is
  satisfied by a **prose** usage note, not a runnable doctest (the seam is
  `typ.NoReturn`; a doctest would terminate the interpreter — Decision Log D4,
  matching `run`'s own prose-only docstring).

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 8 files or more than
  250 net lines of code, stop and escalate.
- Interface: the only new public interface is the `drive` seam (and its
  re-export from `novel_ralph_skill.contract.__init__`). If any *existing*
  public signature (`run`, `parse_global_flags`, `RunContext`, `make_contract_app`,
  `novel.main`, `novel.build_multiplexer`) must change its signature, stop and
  escalate.
- Dependencies: if any new external dependency is required, stop and escalate.
  (None is expected: the seam is pure stdlib plus the existing `run`.)
- File size: if adding the seam pushes `novel_ralph_skill/contract/runner.py`
  over 400 lines, stop and escalate (the fallback is a dedicated
  `contract/drive.py` module — Decision Log D3, pre-recorded).
- Iterations: if `make all` still fails after 3 fix attempts on any work item,
  stop and escalate.
- Ambiguity: if migrating the 1.3.6 routing tripwire onto `drive` cannot be
  expressed without weakening the four-flag-contract assertion it already makes,
  stop and present the options rather than dropping the assertion.

## Risks

    - Risk: the seam's argument shape forces a future value-carrying global flag
      to thread an extra parameter, re-opening the `_command_name_for`
      assumption documented in novel.py:148-155.
      Severity: low
      Likelihood: low
      Mitigation: keep the seam command-agnostic — it takes the already-resolved
      name and working_dir as arguments and never re-parses argv. The
      `--human`/name resolution stays in `novel.main`, exactly where the
      existing guard for that assumption lives. The seam is therefore
      orthogonal to that concern.

    - Risk: the 1.3.6 routing tripwire is migrated incorrectly — the implementer
      deletes the monkeypatch assertion instead of re-homing it onto `drive`,
      silently retiring the "routes through the shared seam" guarantee (the
      Doggylump pre-mortem, review round 1).
      Severity: high
      Likelihood: medium
      Mitigation: Work item 2 specifies the exact migration (patch `novel.drive`,
      keep the four-flag-contract assertion on the captured app) and Work item 1
      adds the complementary seam-forwards-to-`run` unit test, so the transitive
      invariant `main → drive → run` is pinned at both joints. Work item 3's
      structural guard then asserts `main` constructs no inline `RunContext`,
      closing the re-inline path. The Constraints forbid deletion.

    - Risk: adding the seam to runner.py breaches the 400-line cap.
      Severity: low
      Likelihood: low
      Mitigation: runner.py is 250 lines (measured, review round 1 confirmed);
      +~35 stays well under 400. Decision Log D3 keeps the dedicated
      `contract/drive.py` fallback recorded if a later edit changes the maths.

    - Risk: a `contract`→`commands` import inversion is accidentally introduced
      if the seam reaches for `commands.names` or `state_sourcing` to resolve
      the name/working_dir itself.
      Severity: medium
      Likelihood: low
      Mitigation: the Constraints forbid it; the seam takes resolved values as
      arguments. Work item 4 adds a layering guard asserting
      contract/runner.py imports no commands module.

    - Risk: the structural guard test is brittle (false-fails on a benign
      docstring edit or a refactor that renames a local).
      Severity: medium
      Likelihood: medium
      Mitigation: assert the invariant with an `ast` walk over `novel.main`'s
      body (no `RunContext(...)` and no `run(...)` Call node inside `main`),
      mirroring the in-repo `ast` scanner pattern in
      `tests/_state_layout_scanner.py` and the multiplexer laziness guard
      (`tests/test_multiplexer_mount_table.py`), rather than a raw substring
      scan.

## Progress

    - [x] Work item 1: measure runner.py, add the `drive` seam with a
      failing-first unit test that also proves the seam forwards to `run`.
      Done: runner.py measured at 250 lines; the ~50-line `drive` seam lands at
      ~300, well under 400, so the seam stays in `runner.py` (Decision D3
      fallback unused). The seam needed a `# noqa: PLR0913  # pylint:
      disable=too-many-arguments` suppression to keep its Decision-D2 five-scalar
      signature, mirroring the established `build_envelope`/`build_finding_outcome`
      pattern (`max-args = 4` in pyproject.toml). The red-first test
      `tests/test_contract_drive_seam.py` failed on import (no `drive` symbol),
      then passed once the seam and the `contract/__init__.py` re-export landed.
      Coderabbit round 1: hardened the argv assertion to object identity (the
      seam forwards argv without copying) and pinned the help-path exit code to
      `0`.
    - [x] Work item 2: repoint `novel.main` onto the seam; migrate the 1.3.6
      routing tripwire onto `novel.drive`; prove behaviour parity.
      Done: `novel.main` now calls `drive(...)`; the import at novel.py:37 is
      `from novel_ralph_skill.contract import drive, parse_global_flags`
      (`RunContext`/`run` dropped, no suppression). The 1.3.6 tripwire is
      migrated to patch `novel.drive` with a keyword-scalar `_capture_drive`
      recorder (which needed a `# pylint: disable=too-many-arguments` — the
      ruff PLR0913 test override does not cover pylint), preserving the
      four-flag-contract assertion and updating the failure message to "shared
      drive seam". The behaviour suites
      (`test_multiplexer_behaviour`/`test_novel_main_working_dir`) pass
      unchanged. Coderabbit round 1: no findings.
    - [x] Work item 3: add the net-new structural guard (no inline
      `RunContext`/`run` Call in `novel.main`); extend the existing
      `[project.scripts]` guard rather than re-copying it.
      Done: `tests/test_entry_point_single_home.py` walks `main`'s `ast`
      `FunctionDef` and asserts no `Call` resolves to `RunContext`/`run` plus a
      positive complement (exactly one `drive` call). Verified load-bearing by a
      temporary revert (both guards go red). It references — does not duplicate —
      the existing `test_legacy_surface_retired.py` `[project.scripts]` guards
      (Decision D7). Coderabbit round 1: traversal hardened from `ast.walk`
      (which descends into nested scopes) to a `_calls_in_executable_body`
      helper that prunes at nested function/lambda/class boundaries, so a future
      nested helper cannot hide a `run`/`RunContext` call from the guard.
    - [x] Work item 4: confirm and guard the import-laziness/layering profile.
      Done: `tests/test_contract_layering.py` `ast`-walks the seam module's
      module-scope imports and asserts none targets a `commands` module
      (verified load-bearing via injected imports). The existing
      `test_multiplexer_mount_table.py` laziness guard still passes unchanged
      (the import edit swapped `RunContext, run` for `drive`, all from the
      contract layer). Coderabbit rounds 1-2 hardened the import scanner: it now
      resolves relative imports (`from ..commands import names`) against the
      module's package and recurses into top-level compound statements
      (`if TYPE_CHECKING`, `try`/`except`, loops, `match`) so a guarded or
      relative `commands` import cannot bypass the guard, while still pruning at
      function/class scope boundaries. A further round extended the scanner to
      catch module-scope dynamic imports
      (`importlib.import_module("…")`/`__import__("…")` with a string-literal
      argument, relative targets resolved against the package), so a dynamic
      `commands` import at module scope is also caught. Later rounds: record each
      `from … import member` member as a candidate module
      (`from novel_ralph_skill import commands` resolves to
      `novel_ralph_skill.commands`); honour `import_module`'s explicit `package=`
      anchor when resolving a relative dynamic import; and read the seam module's
      source statically via `find_spec` rather than importing the runner at
      collection time. The trivial "shorten private-helper docstrings" advisory
      was declined: the repo enforces the numpy docstring convention (multi-line
      docstrings are standard and pass `make lint`). A further round corrected the
      scope-pruning to scan module-scope **class** bodies (a class statement runs
      at import time, so a class-level import is a real module-scope import; only
      function/lambda bodies are pruned). A final trivial advisory to convert the
      `_callee_name`/`_string_literal` `isinstance` chains to `match`/`case` was
      declined: the in-repo ast scanners
      (`tests/test_state_sourcing_home.py`, `tests/_state_layout_scanner.py`,
      `tests/test_multiplexer_mount_table.py`) use `isinstance` chains, so the
      `match` rewrite would diverge from the prevailing style; both forms pass
      `make lint`.
    - [x] Work item 5: refresh stale docstrings and the roadmap entry; run
      markdown gates.
      Done: `novel.py`'s module and `main` docstrings now describe `main` as a
      thin entry point that delegates to the `drive` seam (no more "the five
      legacy entry points" or "the `_drive` shape the retired `stub.py` used"
      framing); the `_command_name_for` value-carrying-flag guard explanation is
      kept intact. The developers-guide entry-point paragraph names `drive` as the
      single home. Roadmap task 7.3.5 is ticked `[x]` with a "Done" note
      recording that the `stub._drive` copy was already retired by 1.2.15, so
      7.3.5 delivered the constructive single-home seam plus the migrated 1.3.6
      tripwire and the structural/layering guards. `make markdownlint` and
      `make nixie` green.

## Surprises & discoveries

    - Observation (S1): the production `stub._drive` the task targets no longer
      exists; ADR 007 / roadmap 1.2.15 (commit 9e95c49) already retired stub.py
      and COMMAND_ENTRY_POINTS, leaving a single novel.main entry point.
      Evidence: `git log --oneline -- novel_ralph_skill/commands/stub.py` shows
      the file's only commit is its deletion in 9e95c49; `grep -rn "^def main"
      novel_ralph_skill/` returns only novel.py:177; `pyproject.toml` declares
      one [project.scripts] entry (`novel = …novel:main`); the only surviving
      `_drive` symbol is the test fixture in tests/contract_drive_support.py.
      Impact: the task's "collapse two copies" framing is satisfied historically;
      this plan delivers the constructive arm (lift the plumbing into a tested
      contract-level seam) plus a guard that re-enforces single-home, rather than
      deleting a non-existent duplicate.

    - Observation (S2, review round 1): there is an existing structural tripwire,
      `tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`
      (lines 98-134), that monkeypatches `novel.run` and asserts `novel.main()`
      forwards the four-flag-contract `build_multiplexer()` app to it (roadmap
      1.3.6 / audit:1.3.6 Finding 3). After the seam extraction `main` no longer
      calls `run` directly, so this test would go red unless migrated.
      Evidence: `grep -rln 'setattr(novel, "run"' tests/` returns exactly this
      one file; the assertion at line 129 is `"novel did not route through the
      shared run seam"`.
      Impact: Work item 2 must migrate this test onto `novel.drive` (the symbol
      `main` now invokes) and Work item 1 must add a complementary seam-level
      test proving `drive` forwards to `run`, so the invariant survives
      transitively. Without this the "Expect green with no behavioural test
      changes" claim is false. This drove Decision Log D5.

    - Observation (S3, review round 1): `make all` is
      `build check-fmt lint typecheck test` (Makefile:37); it does **not** run
      `audit`. `pip-audit` runs only under the separate `make audit` target
      (Makefile:114). Evidence: Makefile line 37 and line 114.
      Impact: the validation sections invoke `make audit` as a *separate* gate,
      not as part of `make all` (Decision Log D6).

## Decision log

    - Decision (D1): treat 7.3.5 as a constructive single-home extraction, not a
      duplicate deletion. Lift novel.main's drive plumbing into a contract-level
      `drive()` seam and install a single-home regression guard.
      Rationale: the second copy (stub._drive) was retired by ADR 007 (1.2.15),
      so there is no duplicate left to collapse. The task explicitly offers
      "lift the shared body into a contract-level drive() helper" as a valid
      mechanism; the alternative ("generalise _drive to take a name resolver")
      is moot because _drive is gone. Picking one mechanism honours the standing
      rule against leaving a menu of unverified workarounds.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D2): seam signature is
      `drive(app: cyclopts.App, argv: cabc.Sequence[str], *, command: str,
      working_dir: str, human: bool) -> typ.NoReturn`, ending by calling
      `run(app, argv, RunContext(command=command, working_dir=working_dir,
      human=human))`.
      Rationale: keeping `command`/`working_dir`/`human` as keyword-only scalars
      (rather than passing a pre-built RunContext) makes the seam the single home
      for RunContext construction — the thing the structural guard pins — while
      leaving name and working_dir resolution in novel.main where the
      value-carrying-flag guard already lives. `typ.NoReturn` mirrors `run` so
      callers see it never returns. Verified against real symbols: `run` is
      `typ.NoReturn` (runner.py:190-194) and `RunContext` is a `frozen, kw_only`
      dataclass with exactly `command`/`working_dir`/`human` (runner.py:150-166).
      Date/Author: 2026-06-27, planning agent.

    - Decision (D3, pre-recorded fallback): if adding `drive` to runner.py would
      breach the 400-line cap, place it in a new
      `novel_ralph_skill/contract/drive.py` module re-exported from
      `contract/__init__.py`, and adjust Work item 1's file path accordingly.
      Rationale: AGENTS.md hard-caps modules at 400 lines; the seam must not be
      the change that breaches it. Moot in practice: runner.py is 250 lines, so
      +~35 lands at ~285, well under 400.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D4, review round 1): the `drive` docstring carries a *prose*
      usage note, not a runnable doctest.
      Rationale: `drive` is `typ.NoReturn`; a doctest would terminate the
      interpreter mid-suite. `interrogate` checks docstring *presence*, not
      examples, and `run`'s own docstring is prose-only. A prose "Examples"-style
      note ("`main` calls `drive(build_multiplexer(), residual, command=name,
      working_dir=…, human=human)`; the call never returns") satisfies AGENTS.md
      without a process-killing doctest.
      Date/Author: 2026-06-27, planning agent (addresses review advisory A2).

    - Decision (D5, review round 1): re-home the roadmap-1.3.6 routing tripwire
      onto `drive`, and prove `drive → run` separately.
      Rationale: `test_novel_entry_point_routes_through_the_shared_seam` is the
      durable structural proof of the 1.3.6 "routes through the shared seam"
      invariant. After the extraction `main` calls `run` only via `drive`, so
      monkeypatching `novel.run` no longer fires. Migrating the patch target to
      `novel.drive` (keeping the four-flag-contract assertion on the captured
      app) preserves the *entry-point* half of the invariant; a new unit test in
      Work item 1 proves the *seam* half (`drive` forwards to `run`). Together
      they pin `main → drive → run`, so the invariant is preserved transitively
      rather than dropped. This also reconciles the apparent contradiction the
      review flagged: the migrated 1.3.6 test asserts `main` routes through
      `drive` (not `run`), while Work item 3's structural guard asserts `main`
      makes no direct `run`/`RunContext` Call — both now describe the *same*
      post-extraction surface, not opposite facts.
      Date/Author: 2026-06-27, planning agent (addresses review B1 and B2).

    - Decision (D6, review round 1): the validation sections invoke `make audit`
      as a separate gate, not as part of `make all`.
      Rationale: `make all` is `build check-fmt lint typecheck test`
      (Makefile:37); `pip-audit` is the separate `make audit` target
      (Makefile:114). The earlier claim that `make all` runs `audit` was wrong.
      Date/Author: 2026-06-27, planning agent (addresses review advisory A1).

    - Decision (D7, review round 1): Work item 3 does **not** create a fresh
      `[project.scripts]`-parsing test. It extends/references the existing
      `tests/test_legacy_surface_retired.py::test_pyproject_scripts_is_novel_only`
      and `::test_script_table_is_novel_only`, which already assert
      `[project.scripts]` is exactly `novel` via the `pyproject`/`project_scripts`
      fixtures (conftest.py:135,200). Only the net-new structural guard ("no
      inline `RunContext`/`run` Call in `novel.main`") is added, in its own
      module `tests/test_entry_point_single_home.py`.
      Rationale: the developers-guide "Shared test scaffolding" rule
      (developers-guide.md:20-22) makes conftest the single home for scaffolding;
      re-parsing pyproject with a fresh stdlib `tomllib` call would re-copy
      scaffolding the existing fixtures already provide. The round-1 draft's
      guard 3a was a duplicate.
      Date/Author: 2026-06-27, planning agent (addresses review B4).

## Outcomes & retrospective

Delivered as planned, matching the Purpose. One contract-level `drive` seam
(`contract.runner.drive`) owns the build-`RunContext`-then-call-`run` plumbing,
re-exported from `contract.__init__`; `novel.main` is a thin entry point that
delegates to it. The migrated roadmap-1.3.6 routing tripwire (patching
`novel.drive`) plus the new seam-forwarding unit test pin `main → drive → run`
at both joints. A structural `ast` guard
(`tests/test_entry_point_single_home.py`) forbids re-inlining the plumbing in
`main`, and a layering guard (`tests/test_contract_layering.py`) pins that the
seam imports no `commands` module. Behaviour, exit codes, the absolute
`working_dir` stamp, the `--human` handling, and the import-laziness profile are
unchanged; `make all` (and `make markdownlint`/`make nixie` for the markdown) is
green at every work item.

Deviations from the plan, with rationale:

- The seam's five-scalar Decision-D2 signature tripped Ruff PLR0913 and Pylint
  `too-many-arguments`; resolved with the established in-repo suppression used by
  `build_envelope`/`build_finding_outcome` rather than reshaping the signature
  (which would have re-introduced the inline-`RunContext` shape the structural
  guard forbids). The migrated tripwire's keyword-scalar recorder needed the
  Pylint `too-many-arguments` disable too (the ruff test override does not cover
  Pylint).
- The structural and layering guards were hardened beyond the plan in response to
  coderabbit: the structural guard prunes nested scopes (so a nested helper
  cannot hide a `run`/`RunContext` call), and the layering guard resolves
  relative imports, recurses through module-scope compound statements
  (`if TYPE_CHECKING`, `try`, loops, `match`), and detects module-scope dynamic
  imports (`importlib.import_module`/`__import__`). Each hardening keeps the guard
  load-bearing (verified by injection) without weakening any planned assertion.

## Context and orientation

The harness exposes a single deterministic command surface, the `novel`
multiplexer, recorded in `docs/adr-007-command-surface-novel-multiplexer.md`
and `docs/novel-ralph-harness-design.md` §4 ("The deterministic commands"). The
key production files are:

- `novel_ralph_skill/commands/novel.py` — the multiplexer dispatcher and the
  sole console entry point. `main()` (lines 177-205) is the body this plan
  refactors: it calls `parse_global_flags(sys.argv[1:])` to split the single
  `--human` global flag (returning `(human, residual)`), `_command_name_for(...)`
  to resolve the spaced registry name from the residual argv, and then
  `run(build_multiplexer(), residual, RunContext(command=name,
  working_dir=str(resolved_working_dir()), human=human))`. The `RunContext`
  construction plus the `run` call are the plumbing this plan lifts into a seam.
  The module imports `RunContext, parse_global_flags, run` from
  `novel_ralph_skill.contract` (novel.py:37); after Work item 2 it imports
  `drive, parse_global_flags` (Work item 2 step 1 and review advisory A3).
- `novel_ralph_skill/contract/runner.py` — the contract runner (250 lines). It
  defines `make_contract_app` (line 52), `parse_global_flags` (line 84),
  `RunContext` (line 150, a frozen `kw_only` dataclass with
  `command`/`working_dir`/`human`), and `run` (line 190), which is
  `typ.NoReturn`: it drives a Cyclopts `App` over `argv`, builds and emits the
  envelope, and owns every `sys.exit`. The new `drive` seam lands here (or in
  `contract/drive.py` per Decision D3) and wraps `run`.
- `novel_ralph_skill/contract/__init__.py` — the contract package's public
  surface; it re-exports `RunContext`, `parse_global_flags`, `run`, etc. (an
  `__all__` list, lines 38-54). The new `drive` seam is added to its imports,
  `__all__`, and the module-docstring surface list (lines 12-13).
- `novel_ralph_skill/commands/names.py` — the command-name registry
  (`MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`); `novel._command_name_for` resolves
  through it. The seam does **not** import this; name resolution stays in
  `novel.main`.
- `novel_ralph_skill/commands/state_sourcing.py` — `resolved_working_dir()`
  (line 70), the absolute, resolved `working/` path stamped into the envelope.
  The seam does **not** import this; working_dir resolution stays in
  `novel.main`.

Terms of art, defined:

- *Entry point* / *console-script*: the function named in `pyproject.toml`
  `[project.scripts]` that the installed `novel` binary invokes. There is
  exactly one: `novel_ralph_skill.commands.novel:main`.
- *Drive plumbing*: the act of building a `RunContext` and calling `run(app,
  argv, context)`. This is the duplication-prone shape the task targets.
- *Single-home*: the step-7.3 hypothesis that a shared seam has one explicit
  owning home, so refactoring one consumer cannot silently break another.
- *Import laziness*: importing `novel.py` must not transitively import any leaf
  command module; the leaf imports are deferred inside `_build_mount_table`
  (novel.py:80-96). The new seam must not perturb this.
- *The 1.3.6 routing tripwire*:
  `tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`,
  the durable structural proof that the `novel` entry point drives the
  four-flag-contract multiplexer app through the shared `run` seam (audit:1.3.6
  Finding 3). It currently monkeypatches `novel.run`; Work item 2 migrates it
  onto `novel.drive`.

Existing test scaffolding to reuse (do not re-copy — developers-guide "Shared
test scaffolding" rule, developers-guide.md:20-22):

- `tests/conftest.py` provides the `pyproject` fixture (line 135) and the
  `project_scripts` walker fixture (line 200) used by the existing
  `[project.scripts]` guards. Work item 3 reuses these via the existing tests
  rather than re-parsing pyproject (Decision D7).
- `tests/test_legacy_surface_retired.py` already has
  `test_pyproject_scripts_is_novel_only` (line 80) and
  `test_script_table_is_novel_only` (line 75), both asserting `[project.scripts]`
  is exactly `novel`. Work item 3 references these as the existing single-entry
  guard; it does not duplicate them.
- `tests/test_contract_app_centralisation.py` is the 1.3.6 routing tripwire
  (lines 98-134). Work item 2 migrates its monkeypatch target from `novel.run`
  to `novel.drive` and keeps the `_assert_four_flag_contract` assertion on the
  captured app.
- `tests/test_multiplexer_behaviour.py` already drives `novel.main` end to end
  (`test_main_drives_the_multiplexer` at line 257,
  `test_parse_global_flags_underpins_main` at line 281) by patching `sys.argv`
  and asserting on the rendered envelope and exit code.
- `tests/test_novel_main_working_dir.py` already proves `main` stamps the
  absolute resolved `working/` path (`test_main_stamps_absolute_resolved_working_dir`
  at line 26, `test_main_surfaces_inside_working_footgun` at line 47). These are
  pure-behaviour parity oracles for Work item 2; they must stay green unchanged.
- `tests/_state_layout_scanner.py` and
  `tests/test_multiplexer_mount_table.py` demonstrate the in-repo `ast`
  module-scope/Call-node scanning pattern the structural guard (Work item 3)
  follows.
- `tests/test_console_scripts_e2e.py` builds and installs the wheel and runs the
  `novel` binary by absolute path through a local cuprum 0.1.0 catalogue
  (`ProgramCatalogue(projects=…)`, `sh.make(prog, catalogue=…)`,
  `Program`). This is the installed-boundary proof; it must stay green and needs
  no new cuprum API.

Full caller enumeration of `novel.main()` in `tests/`, classified (review B3).
`grep -rln 'novel\.main()' tests/` returns 12 files; each is classified as
*plumbing-asserting* (mutates or inspects `main`'s internal call structure) or
*pure-behaviour* (drives `main` and asserts on the rendered envelope / exit
code) or *source-scan* (the literal `novel.main()` appears only in a string or
docstring, not as a runtime call):

- `tests/test_contract_app_centralisation.py` — **plumbing-asserting.** The only
  file that monkeypatches `novel.run` and asserts on `main`'s seam call
  (`grep -rln 'setattr(novel, "run"' tests/` returns this file alone). Work
  item 2 migrates it onto `novel.drive`.
- `tests/test_legacy_surface_retired.py` — **source-scan only.** The token
  `novel.main()` appears solely inside docstrings/comments at lines 51 and 133
  (a B8 source guard); the module never *calls* `main`. No migration needed.
- `tests/test_multiplexer_behaviour.py` — **pure-behaviour.** Drives `main` and
  asserts the rendered envelope/exit code. Unaffected by the seam swap.
- `tests/test_novel_main_working_dir.py` — **pure-behaviour.** Asserts the
  absolute `working_dir` stamp from the rendered envelope. Unaffected.
- `tests/test_compile_e2e.py`, `tests/test_compile_check_integration.py`,
  `tests/test_recount_e2e.py`, `tests/test_gate_drafting_mutators_e2e.py`,
  `tests/test_reconcile_e2e.py`, `tests/test_relaxed_subset_e2e.py`,
  `tests/test_novel_state_check.py`, `tests/test_set_chapters_e2e.py` — all
  **pure-behaviour** in-process e2e suites: each calls `novel.main()` over a
  real `working_corpus`/`working/` tree and asserts on the emitted envelope and
  exit code, never on `main`'s internal calls. They route through the same
  `main → drive → run` path after the extraction and stay green unchanged.

Only one caller — `test_contract_app_centralisation.py` — asserts on `main`'s
internal plumbing; every other caller is pure-behaviour or a source scan. The
parity claim in Work item 2 therefore rests on migrating exactly one test and
leaving the other eleven untouched.

Library facts pinned for this plan (LOCKED versions):

- **cuprum 0.1.0** (`uv.lock`; source at `/data/leynos/Projects/cuprum`,
  `cuprum/catalogue.py` `ProgramCatalogue.__init__(*, projects)` line 62 and
  `.allowlist` line 70, `cuprum/sh.py` `make` line 528): cuprum is a *test-time*
  dependency used only by the installed-binary e2e to shell out to `uv`/`novel`.
  Design §4 confirms "cuprum is required only where a command shells out (none
  do in v1)". The `drive` seam shells out to nothing, so it pulls in no cuprum;
  this plan adds no new cuprum surface. The existing e2e's cuprum usage is
  unchanged. (Verified against source by the round-1 review.)
- **Cyclopts 4.18.0** (`uv.lock`): the seam treats the `App` as an opaque value
  it forwards to `run`; it constructs no new Cyclopts app and changes no
  mounting behaviour. The mounting/contract-flag behaviour pinned by the 7.3.2
  ExecPlan (Decision D2/D3 there) is untouched. No new Cyclopts behavioural
  claim is introduced, so no new Cyclopts-docs verification is needed beyond the
  already-cited locked behaviour. (The migrated 1.3.6 tripwire still asserts the
  four-flag contract via the existing `_assert_four_flag_contract`, so the
  Cyclopts-4.18.0 normalised flag forms stay pinned.)

## Plan of work

Stage A (Work item 1) extracts the seam behind a failing-first test that also
proves the seam forwards to `run`. Stage B (Work item 2) repoints `novel.main`,
migrates the 1.3.6 routing tripwire onto `drive`, and proves parity against the
pure-behaviour suites. Stage C (Work items 3-4) installs the net-new structural
guard and the layering/laziness guard. Stage D (Work item 5) refreshes
docstrings and the roadmap and runs the markdown gates. Each work item is
independently committable and gate-passable.

### Work item 1 — Add the contract-level `drive` seam (red, then green)

Implements: design §4 (single multiplexer / single entry point); ADR 003
shared interface contract (the contract package owns shared command plumbing);
the step-7.3 command-facade single-home hypothesis (roadmap 7.3.5 lead text);
developers-guide "single home" / shared-seam rule (developers-guide.md:78-86).

Read first: `docs/novel-ralph-harness-design.md` §4; `docs/adr-003-shared-
interface-contract.md`; `docs/developers-guide.md` (the `run`-seam and
single-home sections, lines ~78-90 and ~182); `novel_ralph_skill/contract/
runner.py` (`run` 190-249, `RunContext` 150-166, `parse_global_flags` 84);
AGENTS.md (400-line cap, docstring/example rule).

Skills to load: `python-router` → `python-types-and-apis` (the seam's public
signature and `typ.NoReturn`), `python-testing` (pytest fixtures, monkeypatch
of `run`, capsys/`pytest.raises(SystemExit)`). No verification adversary
(Hypothesis/CrossHair/mutmut) is warranted yet — the seam is a thin
deterministic wrapper with no invariant over a range of inputs; example-based
unit tests plus the existing behaviour suite cover it. (If a reviewer later
demands invariant coverage, route through `python-verification`.)

Steps:

1. Measure `wc -l novel_ralph_skill/contract/runner.py` (expect 250). +~35
   keeps it under 400, so add `drive` there; record the chosen home in the
   Decision Log. (Decision D3 is the recorded fallback only.)
2. Write the failing-first unit test `tests/test_contract_drive_seam.py` with
   two cases:
   a. **Forwarding + field fidelity.** Monkeypatch
      `novel_ralph_skill.contract.runner.run` with a recorder, call
      `drive(app, ["x"], command="novel state", working_dir="/abs/working",
      human=True)`, and assert the recorder captured `app` and `["x"]`
      unchanged and a `RunContext` carrying exactly those `command`/`working_dir`
      /`human` fields. This is the *seam half* of the 1.3.6 transitive invariant
      (`drive → run`), the proof Work item 2's migrated tripwire relies on.
   b. **`SystemExit` propagation.** Call `drive` against a real
      `make_contract_app("novel")` app with an argv that exits (e.g. `--help`)
      and assert it raises `SystemExit` (proving the seam does not swallow
      `run`'s exit). Use `pytest.raises(SystemExit)`.
   Run it and confirm both fail (red): the seam does not yet exist.
3. Add `drive` per Decision D2 with a full docstring (purpose, parameters,
   `Returns: typing.NoReturn`, and a **prose** usage note per Decision D4 — *not*
   a doctest). Re-export it from `novel_ralph_skill/contract/__init__.py`
   (imports, `__all__`, and the module-docstring surface list at lines 12-13).
4. Run the test (green).

Tests this item adds: `tests/test_contract_drive_seam.py` (unit) — the
forwarding/field-fidelity case and the `SystemExit`-propagation case. These are
the failing-before/passing-after tests AGENTS.md requires for new behaviour, and
case (a) is the seam half of the migrated 1.3.6 invariant.

Validation: `make all` (runs `build check-fmt lint typecheck test`;
Makefile:37). `make lint` runs Ruff, `interrogate` 100% docstring coverage, and
Pylint. Run `make audit` separately (it is not part of `make all` — Decision D6).
Expect all green; expect the two new cases to pass and to have failed before
step 3.

### Work item 2 — Repoint `novel.main` and migrate the 1.3.6 routing tripwire

Implements: design §4; ADR 007 (single entry point); roadmap 7.3.5 Success
criterion ("`novel.main` … delegate[s] to it rather than re-spelling the
plumbing"); roadmap 1.3.6 / audit:1.3.6 Finding 3 (the routing invariant, here
re-homed onto `drive`).

Read first: `novel_ralph_skill/commands/novel.py` (`main`, lines 177-205, and
the import line at 37); `tests/test_contract_app_centralisation.py` (the 1.3.6
tripwire, lines 98-134); `tests/test_multiplexer_behaviour.py`;
`tests/test_novel_main_working_dir.py`.

Skills to load: `python-router` → `python-testing` (parity assertions,
monkeypatch retargeting). Use `leta show novel.main` / `leta refs novel.main`
to confirm the caller classification recorded in "Context and orientation"
(one plumbing-asserting caller, ten pure-behaviour callers, one source-scan)
before editing.

Steps:

1. Replace the `run(build_multiplexer(), residual, RunContext(...))` call in
   `main` with a call to the seam:
   `drive(build_multiplexer(), residual, command=name,
   working_dir=str(resolved_working_dir()), human=human)`. `main` keeps
   `parse_global_flags`, `_command_name_for`, and `resolved_working_dir` — only
   the `RunContext` construction and the `run` call move into the seam. Change
   the import at novel.py:37 from
   `from novel_ralph_skill.contract import RunContext, parse_global_flags, run`
   to `from novel_ralph_skill.contract import drive, parse_global_flags` (review
   advisory A3): after the edit `main` references only `parse_global_flags`,
   `build_multiplexer`, and `drive`, so `RunContext` and `run` become unused and
   must be dropped from the import to avoid a Ruff unused-import failure. Do not
   add suppressions.
2. **Migrate the 1.3.6 routing tripwire**
   (`tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`,
   lines 98-134) onto the seam:
   - Change `monkeypatch.setattr(novel, "run", _capture_run)` (line 122) to
     `monkeypatch.setattr(novel, "drive", _capture_drive)`.
   - Adjust the recorder to the seam's keyword-scalar signature: `_capture_drive`
     takes `(app, argv, *, command, working_dir, human)` and stores `app`,
     `list(argv)`, and the three scalars into `captured`.
   - Keep the assertions that the captured app is the four-flag-contract
     `build_multiplexer()` app (`app.name == ("novel",)`,
     `_assert_four_flag_contract(app)`) and that the residual argv is `[]`.
     Update the failure message to "novel did not route through the shared
     drive seam".
   - Update the module/function docstring (lines 21-25, 101-109) to say the
     entry point routes through `drive` (which forwards to the shared `run`
     seam, proven by `tests/test_contract_drive_seam.py`), preserving the
     audit:1.3.6 cross-reference. This is the *entry-point half* of the 1.3.6
     transitive invariant; Work item 1 case (a) supplies the *seam half*.
3. Run `tests/test_contract_app_centralisation.py`,
   `tests/test_multiplexer_behaviour.py`, and
   `tests/test_novel_main_working_dir.py` — the migrated tripwire and the
   pure-behaviour suites must all be green (behaviour parity: same exit codes,
   same `working_dir` stamp, same `--human` consumption; the ten pure-behaviour
   callers are untouched).

Tests this item adds/updates: migrates
`tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`
(patch target `novel.run` → `novel.drive`; recorder signature updated; assertions
preserved). The other half of `test_contract_app_centralisation.py`
(`test_real_build_app_carries_the_four_flag_contract`) is untouched. No
pure-behaviour suite changes. If the import edit leaves an unused symbol, fix the
import; do not add suppressions.

Validation: `make all`. Expect green: the migrated 1.3.6 tripwire passes against
the new surface, and every pure-behaviour suite stays green unchanged.

### Work item 3 — Net-new structural guard (no inline `RunContext`/`run` in `main`)

Implements: the step-7.3 command-facade single-home hypothesis (roadmap 7.3.5
lead text and Success criterion — "a refactor of one cannot silently break the
other"); AGENTS.md "duplicated code" refactoring heuristic.

Read first: `tests/_state_layout_scanner.py` and
`tests/test_multiplexer_mount_table.py` (the in-repo `ast` scanner pattern);
`tests/test_legacy_surface_retired.py` (`test_pyproject_scripts_is_novel_only`
line 80, `test_script_table_is_novel_only` line 75 — the existing
single-entry-point guards).

Skills to load: `python-router` → `python-testing` (ast-based structural tests).

Steps:

1. **Do not** add a fresh `[project.scripts]`-parsing test. The "exactly one
   production entry point" invariant is already pinned by the two existing tests
   in `tests/test_legacy_surface_retired.py`
   (`test_pyproject_scripts_is_novel_only`, `test_script_table_is_novel_only`),
   which use the shared `pyproject`/`project_scripts` fixtures (conftest.py:135,
   200). Reference them in the new module's docstring as the existing
   single-entry guard (Decision D7); re-parsing pyproject here would re-copy
   scaffolding the developers-guide forbids (review B4).
2. Add `tests/test_entry_point_single_home.py` with the **one net-new** guard:
   **No inline `RunContext`/`run` construction in `novel.main`.** Walk the `ast`
   of `novel_ralph_skill/commands/novel.py`, locate the `main` `FunctionDef`,
   and assert its body contains no `Call` whose callee resolves to `RunContext`
   and no `Call` whose callee resolves to `run` — proving the plumbing lives only
   behind the seam (`main` should contain exactly one `Call` to `drive`). Mirror
   the FunctionDef-scoped `ast` walk in `tests/_state_layout_scanner.py` /
   `tests/test_multiplexer_mount_table.py` rather than a substring scan, so a
   docstring mention of `RunContext` does not false-fail. Document in the test
   that this guard and the migrated 1.3.6 tripwire describe the **same**
   post-extraction surface (`main` routes through `drive`, not `run`) — they are
   complementary, not contradictory (Decision D5).
3. Run the new test (green now); sanity-check it would go red by temporarily
   reverting Work item 2 locally (do not commit the revert).

Tests this item adds: `tests/test_entry_point_single_home.py` (one structural
ast guard). The `[project.scripts]` single-entry invariant is covered by the
existing `test_legacy_surface_retired.py` tests, which this module references
rather than duplicates.

Validation: `make all`. Expect green.

### Work item 4 — Confirm and guard import-laziness and layering

Implements: Constraints (import laziness preserved; no `contract`→`commands`
inversion introduced by the seam); ADR 003 layering; novel.py:70-72 / 80-96
laziness contract (ExecPlan 7.3.2 Decision D2).

Read first: `novel_ralph_skill/commands/novel.py` (`_build_mount_table`
deferred imports, 80-96); `tests/test_multiplexer_mount_table.py` (the existing
laziness guard); the seam module from Work item 1.

Skills to load: `python-router` → `python-testing`; consult the
`hexagonal-architecture` skill only for the ports/layering vocabulary if framing
the layering assertion (the contract layer must not depend on the commands
layer). (`arch-crate-design` is Rust-specific and not loaded.)

Steps:

1. Add (or extend the existing laziness guard with) an assertion that the seam's
   home module — `novel_ralph_skill.contract.runner` (or
   `novel_ralph_skill.contract.drive` if Decision D3 was taken) — imports **no**
   `novel_ralph_skill.commands` module: `ast`-walk the module-scope imports and
   assert none target a `commands` module, mirroring the mount-table laziness
   guard. This pins the Constraint that the seam takes resolved values as
   arguments rather than reaching into the command layer. (Review round 1
   confirmed `runner.py` imports no `commands` module today, so this guard
   pins a currently-true invariant.)
2. Confirm importing `novel_ralph_skill.commands.novel` still triggers no leaf
   import: the existing `tests/test_multiplexer_mount_table.py` laziness guard
   already proves this for the leaf modules; verify it still passes after the
   seam edit (the seam adds no module-scope leaf import to novel.py — the import
   edit in Work item 2 swaps `RunContext, run` for `drive`, all from the
   `contract` layer).

Tests this item adds/updates: extend the existing laziness/layering guard or
add `tests/test_contract_layering.py` (one `ast`-based case asserting the seam
module imports no `commands` module). Keep the existing mount-table laziness
test green unchanged.

Validation: `make all`. Expect green.

### Work item 5 — Refresh stale docstrings and the roadmap entry

Implements: AGENTS.md "Documentation maintenance" (proactively update docs when
structure changes); en-gb-oxendict; the documentation-style-guide.

Read first: `novel_ralph_skill/commands/novel.py` module docstring (lines 1-28)
and `main` docstring (lines 177-194) — they reference "the five legacy entry
points" and "the `_drive` shape the retired `stub.py` used";
`docs/developers-guide.md` line ~182 (production entry point `novel.main`);
`docs/roadmap.md` task 7.3.5 (lines 3040-3065).

Skills to load: `en-gb-oxendict` (spelling), `commit-message` (file-based
message, no `-m`).

Steps:

1. Update `novel.py`'s module docstring and `main` docstring so they describe
   the *current* shape: `main` parses `--human`, resolves the name, and
   delegates to the contract-level `drive` seam (which owns the
   `RunContext`-then-`run` plumbing). Rephrase the "Generalises the `_drive`
   shape the retired `stub.py` used" sentence (`main` docstring, line 180) and
   the "same envelope and exit codes the five legacy entry points already
   produce" sentence (module docstring, lines 9-10) so they no longer imply a
   second live entry point and instead name the `drive` seam as the single home.
   Keep the `_command_name_for` value-carrying-flag guard explanation intact (it
   is still accurate).
2. If the developers-guide describes the entry-point plumbing (around line 182),
   add one sentence naming the `drive` seam as the single home for entry-point
   drive plumbing (only if a natural home exists; do not invent a section).
3. Tick roadmap task 7.3.5 to `[x]` and append a one-line note that the
   `stub._drive` copy was already retired by 1.2.15, so 7.3.5 delivered the
   constructive single-home seam (`contract.drive`) plus the migrated 1.3.6
   routing tripwire and the structural guard (mirror the audit-trail style other
   completed reroutes use, e.g. 7.3.2's lead text). Cross-reference this ExecPlan
   path.

Tests this item adds: none (documentation only). Docstring coverage is still
enforced by `interrogate` under `make lint`.

Validation: `make all` (code/docstrings still gated); then, because `.md`
files changed, `make markdownlint` and `make nixie`. Expect all green. (`make
nixie` validates Mermaid; this plan adds no Mermaid, but the gate is run per the
standing rule for markdown changes.)

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-5`.

1. Confirm branch and clean tree:

        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-5 \
          branch --show-current
        # expect: roadmap-7-3-5

2. Work item 1 — measure, then add the seam and its red-first test:

        wc -l novel_ralph_skill/contract/runner.py
        # expect 250; add drive there. Write tests/test_contract_drive_seam.py,
        # run it red, add drive() + re-export, run it green.
        make all
        make audit   # separate gate; not part of `make all`

3. Work item 2 — repoint main, migrate the 1.3.6 tripwire, prove parity:

        # edit novel_ralph_skill/commands/novel.py main() and its import line
        # migrate tests/test_contract_app_centralisation.py: patch novel.drive
        make all
        # the migrated tripwire and the pure-behaviour suites must pass.

4. Work item 3 — net-new structural guard:

        # add tests/test_entry_point_single_home.py (no inline RunContext/run
        # in main); reference, do not duplicate, the existing pyproject guards.
        make all

5. Work item 4 — laziness/layering guard:

        # extend/add the ast import guard (seam module imports no commands module)
        make all

6. Work item 5 — docs and roadmap, then markdown gates:

        # edit novel.py docstrings, docs/roadmap.md, this ExecPlan
        make all
        make markdownlint
        make nixie

Commit after each work item with a file-based message (the `commit-message`
skill; never `-m`). Each commit must pass `make all` (and, for the
markdown-touching commit, `make markdownlint` and `make nixie`) before it lands.

## Validation and acceptance

Acceptance is behavioural and structural:

- Running `make all` passes after every work item. The new unit test
  `tests/test_contract_drive_seam.py` fails before Work item 1's seam is added
  and passes after.
- The roadmap-1.3.6 routing invariant is **preserved**, not dropped: the
  migrated `tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`
  passes (proving `main` routes the four-flag-contract app through `drive`), and
  `tests/test_contract_drive_seam.py` case (a) passes (proving `drive` forwards
  to `run`). Together they pin `main → drive → run`.
- `novel <sub>` behaviour is unchanged: the ten pure-behaviour callers
  (`tests/test_multiplexer_behaviour.py`, `tests/test_novel_main_working_dir.py`,
  and the eight in-process e2e suites) pass unchanged (same exit codes, same
  absolute resolved `working_dir` stamp, same `--human` consumption).
- The installed-binary proof `tests/test_console_scripts_e2e.py` (POSIX-only,
  ADR 006) passes: the built-and-installed `novel` binary still emits the
  contract envelope and exit codes, confirming the seam extraction did not
  perturb the real entry point.
- The structural guard `tests/test_entry_point_single_home.py` passes:
  `novel.main` constructs no inline `RunContext`/`run` Call node; the existing
  `test_legacy_surface_retired.py` `[project.scripts]` guards still pin exactly
  one entry point.
- The laziness/layering guard passes: the contract seam module imports no
  `commands` module, and importing `novel.py` still pulls in no leaf module.

Quality criteria ("done"):

- Tests: `make test` green; new seam, structural, and layering tests pass;
  the migrated 1.3.6 tripwire and all existing multiplexer, console-scripts, and
  entry-point suites stay green.
- Lint/typecheck: `make lint` (Ruff, 100% interrogate docstring coverage,
  Pylint) and `make typecheck` (`ty`) green.
- Audit: `make audit` (`pip-audit`) green — run as a *separate* gate, since
  `make all` does not include it (Decision D6).
- Markdown (Work item 5): `make markdownlint` and `make nixie` green.

Quality method: `make all` after each work item, plus `make audit` once;
`make markdownlint` and `make nixie` after the markdown-touching work item. Do
not run gates in parallel (shared build cache; sequential runs benefit from
caching).

## Idempotence and recovery

Every step is a normal source edit under version control; re-running `make all`
is safe and side-effect-free. If a work item's gate fails, fix forward within
the Tolerances; if 3 attempts fail, escalate. No step is destructive: there are
no migrations, no data changes, and no network mutation. To roll back a work
item, `git restore` the touched files (the seam, novel.py, the migrated
tripwire, the guard test, or the docs) — each work item is a separate commit, so
reverting one does not disturb the others. The `make` cache is the only shared
state and is rebuild-safe.

## Artifacts and notes

Key evidence to capture at delivery:

- The red-then-green transcript for `tests/test_contract_drive_seam.py`.
- The diff of `tests/test_contract_app_centralisation.py` showing the
  monkeypatch target migrated from `novel.run` to `novel.drive` with the
  four-flag-contract assertion preserved.
- A `make all` green transcript (and a `make audit` green transcript) after the
  final work item.
- The `git diff` of `novel.py` `main()` showing the plumbing replaced by a
  single `drive(...)` call.

## Interfaces and dependencies

New public interface, in `novel_ralph_skill/contract/runner.py` (or
`contract/drive.py` per Decision D3), re-exported from
`novel_ralph_skill/contract/__init__.py`:

        # novel_ralph_skill/contract/runner.py
        def drive(
            app: cyclopts.App,
            argv: cabc.Sequence[str],
            *,
            command: str,
            working_dir: str,
            human: bool,
        ) -> typ.NoReturn:
            """Build the RunContext and drive ``app`` through ``run``.

            ``main`` calls
            ``drive(build_multiplexer(), residual, command=name,
            working_dir=str(resolved_working_dir()), human=human)``; the call
            never returns (it exits via ``run``). Prose example only — the seam
            is ``typ.NoReturn`` (Decision D4).
            """
            run(
                app,
                argv,
                RunContext(command=command, working_dir=working_dir, human=human),
            )

Caller, in `novel_ralph_skill/commands/novel.py`:

        # novel_ralph_skill/commands/novel.py (import line 37)
        from novel_ralph_skill.contract import drive, parse_global_flags

        # novel_ralph_skill/commands/novel.py (main)
        human, residual = parse_global_flags(sys.argv[1:])
        name = _command_name_for(residual)
        drive(
            build_multiplexer(),
            residual,
            command=name,
            working_dir=str(resolved_working_dir()),
            human=human,
        )

No new external dependency. cuprum (0.1.0) and Cyclopts (4.18.0) usage is
unchanged; cuprum stays a test-only dependency for the installed-binary e2e.

## Revision note

Revision 2 (2026-06-27), addressing the round-1 Logisphere design review
(`docs/execplans/roadmap-7-3-5.logisphere-review-r1.md`). Changes:

- **B1/B2 (and the Doggylump pre-mortem) — reconcile the 1.3.6 tripwire.**
  Enumerated the existing routing tripwire
  (`test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`)
  in Surprises S2, Risks, and "Context and orientation". Work item 2 now
  *migrates* it onto `novel.drive` (keeping the four-flag-contract assertion),
  and Work item 1 adds the complementary seam-forwards-to-`run` unit test, so the
  invariant is preserved transitively (`main → drive → run`). Decision Log D5
  reconciles this with Work item 3's structural guard: both describe the same
  post-extraction surface, not opposite facts. The false "no behavioural test
  changes" claim is removed.
- **B3 — caller enumeration redone.** "Context and orientation" now lists all 12
  `novel.main()` callers and classifies each as plumbing-asserting (one:
  `test_contract_app_centralisation.py`), pure-behaviour (ten), or source-scan
  (one: `test_legacy_surface_retired.py`, where `novel.main()` appears only in
  docstrings). The parity claim now rests on migrating exactly one test.
- **B4 — no duplicate `[project.scripts]` guard.** Work item 3 step 1 now
  references the existing `test_legacy_surface_retired.py`
  `test_pyproject_scripts_is_novel_only`/`test_script_table_is_novel_only` and
  the shared `pyproject`/`project_scripts` fixtures instead of re-parsing
  pyproject. Only the net-new ast guard (no inline `RunContext`/`run` in `main`)
  is added. Decision Log D7 records this.
- **A1 — `make audit` separated.** Corrected throughout: `make all` is
  `build check-fmt lint typecheck test` and does not run `audit`; `make audit`
  is invoked as a separate gate (Decision D6).
- **A2 — prose docstring example.** The `drive` docstring carries a prose usage
  note, not a process-killing doctest (Decision D4).
- **A3 — explicit import line.** Work item 2 spells out the exact import edit
  (`from novel_ralph_skill.contract import drive, parse_global_flags`).

No remaining work is gated on an undecided fork: the seam home (D3) is
pre-decided and moot (runner.py is 250 lines), and the mechanism (constructive
single-home seam) is unchanged from round 1, which the reviewer endorsed.
