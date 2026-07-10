# Logisphere design review — roadmap 6.2.6, round 1

Verdict: REVISE (proceed with conditions once the cuprum verification trail is
corrected). The prescribed test code is correct against the locked
`cuprum==0.1.0` wheel and the design intent is sound, but the plan's
"Interfaces and dependencies" trail cites a *diverged* cuprum tree as authority
for 0.1.0, producing at least one false API claim and a set of unresolvable
line-number citations. Under the standing rule that locked-library behaviour
must be verified and cited correctly, that is blocking.

## What was verified (and holds)

- Design conformance: design §3.2 (mutator-refusal-is-3; state/input error
  exits 3), §9 (installed-binary e2es prove the exit-code contract at the
  packaging boundary; line 844 literally specifies "exiting 3 with an
  `ok: false` envelope and no traceback"), §10 (state fault → message, not
  stack trace), and ADR-003 Table 2 row 3 + the `ok`-mirrors-exit-code row all
  match the plan. Audit `docs/issues/audit-6.2.4.md` Finding 6 prescribes
  exactly this work (parametrized missing/unparseable-state exit-3 cases added
  to `test_reconcile_e2e.py` and `test_wordcount_e2e.py`, mirroring recount),
  and Findings 1/4 (scope consolidation) are genuinely out of scope.
- Reference model: `tests/test_recount_e2e.py:150` is the canonical proof; the
  plan mirrors it faithfully (two ids `missing-state`/`unparseable-state`,
  assert exit 3 + `ok: false` + no `Traceback`).
- Fault-shape soundness: `_wordcount.py:131` loads `working/state.toml` via
  `_load_or_state_error` *before* recounting drafts, so an empty-but-present
  `working/` (no `state.toml`) and an unparseable `state.toml` both route to
  exit 3. The in-process proofs `tests/test_wordcount_command.py:97,110`
  confirm both shapes. `reconcile` shares the same `state.toml` boundary.
- Fixtures: `installed_novel_state` is `scope="module"`
  (`tests/installed_binary_fixtures.py:92`), registered via `pytest_plugins`
  (`tests/conftest.py:55-60`); `single_program_catalogue` and
  `venv_scripts_dir` are function-scoped (`tests/conftest.py:246,278`);
  `_build_and_install_wordcount` is the module helper
  (`tests/test_wordcount_e2e.py:42`). No `ScopeMismatch` arises: reconcile uses
  the module fixture (built once), wordcount uses the function helper.
- Lint relief: `pyproject.toml:97` `"**/test_*.py" = ["S101", "PLR0913",
  "PLR0917", ...]` covers both target files, so bare `assert` and the 4-fixture
  signatures are permitted.

## Blocking defects

### B1 — Plan cites the post-0.1.0 cuprum *sibling checkout* as authority for 0.1.0, and at least one resulting claim is FALSE for the locked wheel

The locked dependency is `cuprum==0.1.0` (`uv.lock`). The sibling at
`/data/leynos/Projects/cuprum` is at HEAD `de54bff` ("Collapse `_IOBehaviour`
into the canonical `RunOutputOptions`"), which is *after* 0.1.0 and has
refactored the run API. Verified by installing the actual 0.1.0 wheel:

- 0.1.0 `SafeCmd.run_sync(self, *, capture: bool = True, echo: bool = False,
  context: ExecutionContext | None = None)` — `capture` is a **first-class
  keyword on `run_sync`**.
- Sibling `SafeCmd.run_sync(self, *, output: RunOutputOptions | None = None,
  timeout=..., context=..., stdin=...)` — **no `capture` parameter**; capture is
  routed through `RunOutputOptions`.

Consequence for the plan:

- Plan §"Interfaces and dependencies" (≈ line 522) asserts: "`capture=True` is
  the `RunOutputOptions` default (`cuprum/sh.py:281`) but is passed explicitly".
  This describes the **sibling** API. In the locked 0.1.0 wheel there is no
  `RunOutputOptions` routing on `run_sync`; `capture` is a direct keyword. The
  claim is false for the wheel the tests actually run against.
- The Constraints block (lines 63-65) and the Interfaces block (lines 517-525)
  cite `cuprum/sh.py:93-118,169-199,441,281`. Those line numbers are the
  sibling's. In the 0.1.0 wheel the same entities sit at: `CommandResult` class
  line 89, `ExecutionContext` line 165, `SafeCmd.run_sync` line 518 (the
  `capture`-bearing one). The cited `:441` in the sibling is the
  *capture-less* refactored `run_sync` — i.e. a reader who follows the citation
  to "verify" 0.1.0 behaviour lands on an API that contradicts the prescribed
  test code and could "fix" the test by deleting `capture=True`.
- `cuprum/catalogue.py:79` (lookup raise) is `:82` in 0.1.0;
  `ProjectSettings/ProgramCatalogue` `:33-65` are `:30/:56` in 0.1.0.

Why blocking: the standing rule is that locked-library behaviour must be
verified and cited against the locked artefact. The plan's trail is internally
authoritative-sounding but points at a diverged tree, and at least one claim is
flatly wrong for the wheel. The *prescribed code* happens to be correct (it
matches the green existing tests), so this is a verification-integrity defect,
not a code defect — but it is exactly the failure mode the rule guards against,
because the plan instructs the implementer to trust these citations.

Fix: re-derive every cuprum citation against the locked `cuprum==0.1.0` wheel
(not the sibling working tree), and correct the `RunOutputOptions` sentence to
state that 0.1.0's `SafeCmd.run_sync` takes `capture` as a direct keyword
(default `True`). Either pin the version the line numbers refer to, or drop the
line numbers in favour of the verified signature
`run_sync(*, capture=True, echo=False, context=None) -> CommandResult` and the
field list `CommandResult(program, argv, exit_code, pid, stdout, stderr)`.

## Advisory (non-blocking)

- A1 — Typecheck tool misnamed. Plan lines ~99 and ~443 say `pyright` ("satisfy
  `ruff`/`pyright`"); the actual gate is `ty check` (`Makefile:102`,
  `AGENTS.md:89`). Low impact (the implementer runs `make typecheck`), but the
  plan should name the real tool.
- A2 — `nixie` framing. The plan correctly notes the execplan adds no Mermaid,
  so `nixie` is a no-op; `make nixie` validates Mermaid only. Fine, but the
  prose could simply say "no Mermaid added, so `nixie` has nothing to validate"
  rather than "no-op pass over it" (nixie does not scan this file).
- A3 — Pre-mortem (Doggylump). The likeliest 6-month incident: a future cuprum
  bump (e.g. to a release matching the sibling) lands and the suite breaks on
  `capture=` keyword removal across *all* installed e2es simultaneously. This
  is pre-existing repo exposure, not introduced by 6.2.6, but the plan adds two
  more call sites to the blast radius. Mitigation already implicit: the locked
  `cuprum==0.1.0` pin in `uv.lock` plus the "no new dependencies" constraint.
  No action required for 6.2.6; flagged so the cuprum-upgrade task owner knows
  the count of `capture=True` call sites grows by two.

## Crew one-liners

- Pandalump (structure): boundaries are sound; the test mirrors a proven shape
  and touches no production code. No structural objection.
- Wafflecat (alternatives): the only credible alternative — assert a specific
  message string — is correctly rejected (Decision Log) because the contract
  fixes the envelope/exit, not the wording. No better structural option exists;
  this is the minimal faithful closure of Finding 6.
- Buzzy Bee (scaling): +1 wheel build for reconcile is amortized by the
  module-scoped fixture; wordcount's per-test rebuild is pre-existing
  convention, deliberately not widened here. 180s timeout covers it.
- Telefono (contracts): the asserted triple (exit 3 / `ok: false` / no
  Traceback) is the contract surface ADR-003 + design §10 actually fix.
  Correct. The only contract-trail problem is B1 (wrong cuprum citations).
- Doggylump (failure modes): see A3. Idempotence/recovery section is adequate;
  per-test `tmp_path` isolation holds.
- Dinolump (long-term): matches the team's existing e2e idiom exactly; a future
  reader is well served by the docstrings and Decision Log — *provided* the
  cuprum citations are corrected so they resolve against the pinned wheel.
