# Logisphere design review — roadmap 3.1.3 ExecPlan (Round 1)

Adversarial pre-implementation review of
`docs/execplans/roadmap-3-1-3.md`. Verdict: **Proceed with conditions**. The plan
is structurally sound, design-conformant, and atomic; the blocking items are
small factual corrections to the validation recipe, not design rework.

## What was verified against source

- Detector `_check_compiled_matches_drafts` (`disk_evidence.py:167-188`): the
  plan's quoted absent→None / present-equal→None / present-diverge→Violation
  polarity and the byte-exact `Violation.detail` string
  ("compiled.md is not the ordered concatenation of the present drafts",
  `disk_evidence.py:187`) match the real source.
- Clause `compile_consistent_exists(working_dir)` (`done_predicate.py:211-220`):
  existence-only, `(working_dir)`-only signature, assembled at
  `done_predicate.py:292`. Confirmed.
- `compile_model.py` (104 lines) imports only `_disk_paths`; it imports neither
  `disk_evidence` nor `done_predicate`, so routing both callers through it
  introduces **no import cycle**. Confirmed.
- Corpus oracle `_oracle_disk._check_compiled_matches_drafts` (`:137-149`) is the
  independent twin and is `working_dir`-only; the done-predicate oracle
  (`_done_predicate_oracle.py`) twins only `knitting_gates_passed` and
  `no_unresolved_blockers`, **not** `compile_consistent`. The plan's "oracle
  unchanged" claim therefore holds — there is no `compile_consistent` twin whose
  signature the change could ripple into.
- No production site other than the detector and the clause computes the
  *comparison*. `_compile.py` reuses `concatenate_drafts(present_draft_bodies)`
  only on the **write** path (it produces `compiled.md`; it does not compare),
  so the plan's "exactly two comparison consumers" claim is accurate.
- Audit Finding 2 and roadmap 3.1.3 (`:941-964`) confirm the named fix and the
  success criteria. The design §4.2 status note (`:310-314`) and dev-guide
  §"`compile_consistent` is the existence half only" (`:572-579`) confirm 3.1.2
  owns the behaviour swap. `done_predicate` is not in `state/__init__.__all__`,
  so the clause-signature change has no re-export ripple.

## Pandalump (structural integrity)

Boundaries hold. The seam lives in `compile_model`, the lowest module in the
dependency stack, and both higher modules already (detector) or newly (clause)
depend downward only. The CQS / read-only boundary (ADR-001) is preserved: the
helper is a pure `(State, Path) -> CompiledComparison` query.

## Wafflecat (alternatives) — and the audit deviation

The audit literally specified `compiled_matches_drafts(...) -> bool`. The plan
deviates to a three-valued `enum` (D-SHAPE). This is **the correct call, not a
defect**: a bool "present-and-matches" collapses *absent* and *diverges* to
`False`, but the detector must map absent→None and diverges→Violation. A bool
cannot serve the detector. The enum is the smallest seam that lets each caller
project its own polarity, and it still satisfies the roadmap success criterion
(one helper, both consume, each owns absent-file polarity). The deviation is
documented and gated by Tolerance "Ambiguity". Strongest surviving alternative —
a `Literal["absent","matches","diverges"]` string instead of an `enum` — trades
exhaustiveness checking for one fewer symbol; not worth reopening.

## Buzzy Bee (scaling) / Telefono (contracts) / Dinolump (viability)

No scaling surface (pure refactor over the same disk reads). The public contract
grows by exactly two symbols on `compile_model`; the only *changed* signature is
the non-exported clause gaining `state`. Long-term, the seam is exactly what
3.1.2 needs, matching the team's established deliberate-twin discipline.

## Doggylump (failure modes) / pre-mortem

Scenario 1 — silent verdict drift. Mitigated: the unmodified disk-evidence,
corpus-agreement, done-predicate, snapshot, and e2e suites are the
behaviour-preservation proof; the independent oracle keeps cross-checking.
Scenario 2 — fault-ordering bug. The helper returns `ABSENT` *before* reading
drafts, so an undecodable `draft.md` beside an **absent** `compiled.md` would not
raise. The plan's fault-propagation test correctly places a **present**
`compiled.md`, so the test exercises the path that reads drafts. No defect, but
the implementer must keep the existence check first (WI1 step 2 already says so).

## Blocking defects (factual errors in the validation recipe)

- **B1 — `make all` does not run `pip-audit`.** `all: build check-fmt lint
  typecheck test` (`Makefile:28`); `audit`/`pip-audit` is a separate target
  (`Makefile:104-105`). The "Concrete steps" §3 ("Expect: … `pip-audit` clean")
  and "Validation and acceptance" ("Audit: `make audit` (`pip-audit`) — clean")
  imply `make all` covers audit. Correct the recipe: `make all` covers
  build/check-fmt/lint(ruff+interrogate+pylint)/typecheck(ty)/test only. Since
  the diff adds no dependency, `make audit` is not load-bearing here, but the
  recipe must not assert a gate that `make all` does not run.

- **B2 — `make test PYTEST_ADDOPTS=...` is not a defined targeted hook.** The
  `test` target is `pytest -v -n $(PYTEST_XDIST_WORKERS)` (`Makefile:115-116`)
  with **no** `$(PYTEST_ADDOPTS)` interpolation. The named file would only be
  picked up because pytest itself reads the `PYTEST_ADDOPTS` *environment
  variable*, and it would then run under `-n auto` xdist (a single file fanned
  across workers). The plan presents this as "the Makefile's targeted hook" with
  an unexplained fallback. Either correct the claim (state the targeting comes
  from pytest's env var, not a Makefile parameter, and that `-n auto` still
  applies) or direct the implementer to the `uv run pytest <file>` form for
  targeted runs and reserve `make all` / `make test` for the full gate.

## Advisory (non-blocking)

- A1 — WI1's fault test should assert specifically that the helper raises only
  when `compiled.md` is **present** (the absent-first ordering), to lock the
  ordering against a future refactor that reads drafts unconditionally.
- A2 — WI3 should explicitly confirm `tests/test_done_predicate.py:33` import of
  `compile_consistent_exists` is updated for the new `(state, working_dir)` call
  even if the name is kept (the import stays valid; only the *calls* at `:144`,
  `:147`, `:149` gain a `state` argument). The plan covers this but does not name
  the import line.
- A3 — D-NO-CUPRUM is sound: the diff touches only internal pure-Python modules
  and pytest suites; no cuprum/Cyclopts/pytest-timeout/uv behaviour is
  load-bearing, so no external-doc citation is owed.
