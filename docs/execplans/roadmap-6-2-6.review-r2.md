# Logisphere design review — roadmap 6.2.6, round 2

Verdict: PROCEED. The round-1 blocking defect (B1 — cuprum citation trail
pointed at the diverged post-0.1.0 sibling and carried one false API claim) is
fully resolved. Every cuprum citation in the round-2 revision now resolves
*exactly* against the authoritative locked artefact, and the prescribed test
code matches both the wheel API and the existing green installed e2es. The two
non-blocking round-1 advisories (typecheck tool name, `nixie` framing) are
actioned. No blocking defects remain.

## Verification performed this round (adversarial, against the locked artefact)

The standing rule requires locked-library behaviour to be verified and cited
against the locked artefact. The planner's summary was not taken on trust; the
wheel was downloaded and unpacked, and every cited line was re-derived from it.

- **Authoritative artefact confirmed.** `uv.lock:113-118` pins
  `cuprum==0.1.0`, wheel sha256
  `b03e813bb56afe75f6cc38ec742091a0b1dc183480630abbaf8f205c984c3e72`. That
  exact wheel was downloaded from PyPI; its sha256 matched byte-for-byte. The
  sibling checkout at `/data/leynos/Projects/cuprum` is at `v0.1.0-47-gde54bff`
  (47 commits *after* the tag, HEAD "Collapse `_IOBehaviour` into the canonical
  `RunOutputOptions`"), confirming the round-1 divergence finding. All
  citations below are taken from the unpacked wheel, not the sibling.
- **`cuprum/program.py:15`** → `Program = typ.NewType("Program", str)`. Exact.
- **`cuprum/catalogue.py:30`** → `@dc.dataclass` for `class ProjectSettings`
  (fields `name`, `programs`, `documentation_locations`, `noise_rules`). Exact.
- **`cuprum/catalogue.py:56`** → `class ProgramCatalogue.__init__(self, *,
  projects: Iterable[ProjectSettings])`. Exact.
- **`cuprum/catalogue.py:76` / `:82`** → `def lookup(...)` and `raise
  UnknownProgramError(msg)` on an unregistered program. Exact; the allowlist is
  load-bearing.
- **`cuprum/sh.py:89`** → `class CommandResult` with fields `program, argv,
  exit_code, pid, stdout, stderr`; **`:116`** `ok` property `return
  self.exit_code == 0`. Exact.
- **`cuprum/sh.py:165`** → `class ExecutionContext` carrying `cwd`. Exact.
- **`cuprum/sh.py:450`** → `def run_sync(self, *, capture: bool = True, echo:
  bool = False, context: ExecutionContext | None = None) -> CommandResult`,
  inside `class SafeCmd` (lines 355-480). This is the call the test makes
  (`sh.make(...)("reconcile").run_sync(...)` yields a `SafeCmd`). The round-1
  false `RunOutputOptions` sentence is gone; `capture` is a first-class keyword
  defaulting to `True`, exactly as the round-2 plan now states. Exact.
- **`cuprum/sh.py:529`** → `def make(program, *, catalogue=DEFAULT_CATALOGUE) ->
  SafeCmdBuilder`, calling `catalogue.lookup(program)`. Exact.
- Disambiguation done: there is a second `run_sync` at `sh.py:518`, but it lives
  in `class Pipeline` and returns `PipelineResult`. The plan correctly cites the
  `SafeCmd` one at `:450`. No confusion introduced.

The `capture=True` keyword is further corroborated independently: the existing
green `tests/test_recount_e2e.py:184` and `tests/test_wordcount_e2e.py:100` both
call `run_sync(context=..., capture=True)` against this same wheel, so the API
is pinned by the passing suite, not by memory.

## Design and structural claims re-confirmed

- **Reference model.** `tests/test_recount_e2e.py:150-186`
  (`test_installed_novel_state_recount_state_error_exits_three`) exists exactly
  as described: two ids `missing-state`/`unparseable-state`, asserts exit 3 +
  `ok: false` + no `Traceback`. The plan mirrors it faithfully for both work
  items.
- **Target modules.** `test_reconcile_e2e.py` has two installed e2es (`:194`,
  `:243`) on the module-scoped `installed_novel_state` fixture, invoking
  `("reconcile")`. `test_wordcount_e2e.py` has the function-scoped
  `_build_and_install_wordcount` helper (`:42`) and
  `test_installed_wordcount_reports_gate_triggers` (`:78`) calling
  `sh.make(prog, catalogue=catalogue)()` with the empty `()` no-subcommand
  shape (`:100`). The two work items match each module's existing convention; no
  cross-module fixture import (developers-guide "Shared test scaffolding"
  respected).
- **Fault-shape soundness.** `novel_ralph_skill/commands/_wordcount.py:131`
  calls `_load_or_state_error(working_dir / "state.toml")` before any draft
  recount, so both fault shapes route to exit 3. In-process proofs
  `tests/test_wordcount_command.py:98` (absent `working/`) and `:110`
  (unparseable `state.toml`) assert `ExitCode.STATE_ERROR`. `reconcile` shares
  the same `state.toml` boundary.
- **Fixture scope / no ScopeMismatch.** `installed_novel_state` is
  `scope="module"` (`tests/installed_binary_fixtures.py:92`);
  `single_program_catalogue` (`conftest.py:246`) and `venv_scripts_dir`
  (`conftest.py:278`) are function-scoped. Reconcile reuses the module fixture
  (one build), wordcount uses the function helper (its existing convention).
- **Lint relief.** `pyproject.toml:97` `"**/test_*.py" = ["S101", "PLR0913",
  "PLR0917", "PLR2004", "PLR6301"]` covers both files; bare `assert` and
  4-fixture signatures are permitted.
- **Toolchain.** `make all = build check-fmt lint typecheck test`
  (`Makefile:28`); `test: build ...` (`Makefile:115`) builds first;
  `make typecheck` runs `ty check $(PYTHON_TARGETS)` (`Makefile:102`,
  `AGENTS.md:89`) — round-2 correctly names `ty`, not `pyright`. `nixie`
  validates Mermaid only (`Makefile:111`).
- **Boundary conformance.** This is purely additive test work re-asserting the
  exit-3 contract (design §3.2 mutator-refusal-is-3; §9 packaging boundary; §10
  message-not-stack-trace; ADR-003 Table 2 row 3 + `ok`-mirrors-exit row) at the
  installed layer. Nothing crosses the deterministic/judgemental boundary
  (ADR-001) and no contract changes.

## Minor, non-blocking citation drift (no action required)

- The plan cites `Makefile:100` for the typecheck rule; the `ty check` line is
  actually `Makefile:102` (line 100 is the `.PHONY`/comment line). Off-by-two;
  the implementer runs `make typecheck` regardless.
- The plan twice cites the in-process wordcount exit-3 tests as
  `test_wordcount_command.py:98,110` and once as `:98-122`; the two functions
  are at 98 and 110. Cosmetic.
- The fault-shape module is `novel_ralph_skill/commands/_wordcount.py:131`
  (round-1 abbreviated the path to `_wordcount.py:131`). Same file.

None of these affect implementability; an implementer following the plan lands
on the correct code in every case.

## Crew one-liners

- Pandalump (structure): boundaries sound; mirrors a proven shape, touches no
  production code. No objection.
- Wafflecat (alternatives): the one credible alternative — assert a specific
  message string — is correctly rejected (Decision Log) because the contract
  fixes the envelope/exit, not the wording. This is the minimal faithful closure
  of audit Finding 6.
- Buzzy Bee (scaling): reconcile amortises its one wheel build via the
  module-scoped fixture; wordcount's per-test rebuild is pre-existing convention,
  deliberately not widened (Findings 1/4 work). 180s timeout covers it.
- Telefono (contracts): the asserted triple (exit 3 / `ok: false` / no
  Traceback) is exactly the surface ADR-003 + design §10 fix. The round-1
  contract-trail defect (wrong cuprum citations) is now resolved.
- Doggylump (failure modes / pre-mortem): likeliest future incident is a cuprum
  bump to a release matching the sibling (`capture=` removed), breaking all
  installed e2es at once. Pre-existing exposure; 6.2.6 adds two call sites to the
  blast radius. Mitigation already in place: the `cuprum==0.1.0` pin +
  "no new dependencies" constraint. The cuprum-upgrade owner should note the
  `capture=True` call count grows by two. Idempotence/recovery section adequate;
  per-test `tmp_path` isolation holds.
- Dinolump (long-term): matches the team's existing e2e idiom exactly; docstrings
  and Decision Log serve a future reader, and the citations now resolve against
  the pinned wheel.

## Documentation / skills trail relied on

`docs/novel-ralph-harness-design.md` §3.2/§9/§10; `docs/adr-001-...` (boundary),
`docs/adr-003-shared-interface-contract.md` Table 2; `docs/adr-006-...` (POSIX
e2e policy); `docs/issues/audit-6.2.4.md` Finding 6; `docs/roadmap.md` 6.2.6;
`docs/developers-guide.md` ("Shared test scaffolding"); `AGENTS.md`; the locked
`cuprum==0.1.0` wheel (PyPI, sha256 matched to `uv.lock`). Skills: the
`logisphere-design-review` crew framework.
