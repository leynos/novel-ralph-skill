# Post-merge audit: roadmap task 6.2.5

Audit of the codebase after roadmap task 6.2.5 ("add a torn-turn recovery
scenario driven through a real command", commit `5e46076`) merged to `main`.
The task added a Gherkin feature (`tests/features/torn_turn_recovery.feature`),
its step module (`tests/steps/torn_turn_recovery_steps.py`), and the pytest-bdd
binding (`tests/test_torn_turn_recovery_bdd.py`). The scenario crashes a *real*
`novel-state reconcile` command at the `_reconcile._append_recovery_entry` seam
(append-then-raise), asserts the torn `[pending_turn]` is left on disk, that
`check` reports it (exit 4, `complete-pending-turn`), and that bounded
`reconcile` re-entry recovers it (each exit 0) with the drafts byte-for-byte
intact.

The change is sound, the roadmap success clause is met, and the docstrings are
unusually thorough. The clause's "driven through the command entry points, not
the bracket primitive" requirement *is* genuinely satisfied: the new BDD test
drives `run(build_app(), ...)`, where the existing integration test calls
`_reconcile.reconcile()` directly. So the new test adds real command-boundary
coverage. The findings below are duplication the new module both inherited and
extended, a private-seam coupling that has now spread to a third site, and a few
smaller consistency and documentation gaps. None block the merge.

Sources relied on: `docs/developers-guide.md` ("Shared test scaffolding", "The
`working/` fixture corpus"), `docs/novel-ralph-harness-design.md` (§3.4 atomic
writes, §5.4), `docs/roadmap.md` (task 6.2.5), and `AGENTS.md` (module and
local-variable caps, bare-`assert` policy, `tests/steps/` per-file ignores).
Loaded the `python-router` skill, routing to `python-testing`. Code navigated
with `leta`/`grep`; history traced with `git show` over commit `5e46076`.

## Finding 1: The command-runner wrapper is duplicated across four test sites

- **Category:** duplication
- **Severity:** high
- **Location:** `tests/steps/torn_turn_recovery_steps.py:107` (`_run`) and `:119`
  (`_run_capturing`); `tests/steps/reconcile_steps.py:83` (`_run`);
  `tests/test_reconcile_integration.py:52` (`_drive`).

Four near-identical helpers wrap the same body: `monkeypatch.chdir(
working.parent)`, then `run(build_app(), [command], RunContext(command=
"novel-state", working_dir="working", human=False))` inside `pytest.raises(
SystemExit)`, returning the captured exit code (and, in the capturing variants,
the parsed JSON envelope). `torn_turn_recovery_steps._run` and
`reconcile_steps._run` are byte-for-byte identical bar the inlined vs constant
`"novel-state"` literal; `torn_turn_recovery_steps._run_capturing` and
`test_reconcile_integration._drive` are identical bar the helper name. Task
6.2.5 added two fresh copies of this body.

The `docs/developers-guide.md` "Shared test scaffolding" rule is explicit: "New
shared scaffolding belongs in `tests/conftest.py` as another fixture rather than
a fresh copy in each module," and reaching into another test module's private
symbols is "forbidden here". A command-runner wrapper used by the reconcile
integration test and two BDD step modules is exactly such scaffolding.

- **Proposed fix:** Promote a single command-driver to a registered plugin (e.g.
  a `tests/command_driver.py` module added to `pytest_plugins`, mirroring
  `installed_binary_fixtures.py`). Expose one fixture returning a callable —
  `drive(working, command) -> tuple[int, dict[str, object]]` — that performs the
  `chdir`, the `run`, and the `SystemExit`/envelope capture. The non-capturing
  callers take `code, _ = drive(...)`. Replace the `_run`, `_run_capturing`, and
  `_drive` bodies with delegations. This collapses four bodies to one and brings
  the step modules onto the documented fixture-by-name path.

## Finding 2: The crash-injection seam is hand-rolled at a third site

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/torn_turn_recovery_steps.py:71` (`_CrashError`),
  `:163` (`_append_then_crash`), `:168` (the `monkeypatch.setattr`);
  `tests/test_reconcile_integration.py:146` (`_CrashError`), `:151`
  (`_append_then_crash`), `:156` (the `monkeypatch.setattr`).

The crash injection — a private `_CrashError(RuntimeError)` sentinel, a
`_append_then_crash(working_dir, line)` closure that calls the real
`_reconcile._append_recovery_entry` then raises, and the
`monkeypatch.setattr(_reconcile, "_append_recovery_entry", _append_then_crash)`
patch — is reproduced verbatim from `test_reconcile_integration.py`. Both reach
into the production module's *private* `_append_recovery_entry` symbol. The new
module's docstring (lines 8-14) cites this seam as the one
`test_reconcile_integration` already validates, so the duplication is
acknowledged but not abstracted. Patching a leading-underscore production helper
in two independent tests means a rename of `_append_recovery_entry` silently
breaks both, and any future torn-turn test must re-discover the seam.

- **Proposed fix:** Extract a context-manager fixture — e.g.
  `crash_after_recovery_receipt(monkeypatch)` — into the same shared plugin as
  Finding 1, encapsulating the sentinel, the append-then-raise closure, the
  patch, and the restore. Both the integration test and the BDD step would
  `with crash_after_recovery_receipt(): ...`. This gives the private-seam
  coupling a single owner so a rename touches one place, and documents the
  recovery test contract in one spot.

## Finding 3: `_draft_bytes` and `_present_files` are copied between the two step modules

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/torn_turn_recovery_steps.py:88` (`_draft_bytes`),
  `:102` (`_present_files`); `tests/steps/reconcile_steps.py:54` (`_draft_bytes`).

`_draft_bytes` (rglob every `draft.md`, key path→bytes) is byte-for-byte
identical between the two step modules. The "every regular file under
`working`" set is computed by `torn_turn_recovery_steps._present_files` and by
three inline `{str(p.relative_to(...)) for p in working.rglob("*") if
p.is_file()}` comprehensions in `reconcile_steps.py` (plus a fourth shape in
`test_reconcile.py:70`). These back the same draft-integrity and
"no-file-removed" invariants (design §5.4) across the suites. The new module's
docstring (lines 29-31, Decision D-DUP) justifies keeping the step helpers
self-contained on the ground that "the helpers are a handful of lines" — a
reasonable call in isolation, but with `_draft_bytes` and `_present_files` now
duplicated across modules that share the same `working_corpus` fixtures, the
draft-integrity assertion has drifted into three slightly different spellings.

- **Proposed fix:** Move `draft_bytes(working) -> dict[str, bytes]` and
  `present_files(working) -> set[str]` onto the `working_corpus` plugin (they
  operate purely on a built corpus tree) or the shared command-driver plugin
  from Finding 1, and have both step modules and `test_reconcile_integration` /
  `test_reconcile` consume them. This pins one spelling of the
  draft-integrity/no-deletion invariant the design (§5.4) requires every
  reconcile-family test to assert identically.

## Finding 4: The recovery success clause is asserted by two near-twin tests

- **Category:** similarity
- **Severity:** low
- **Location:** `tests/steps/torn_turn_recovery_steps.py` (the whole scenario)
  vs `tests/test_reconcile_integration.py:127`
  (`test_interrupted_reconcile_leaves_recoverable_record`).

The two tests share the same fixture (`done-claim-stale-word-counts`), the same
crash seam, the same bounded three-attempt recovery loop, and the same core
assertions (torn record left with `operation="reconcile"`; cleared after
recovery; `check` clean at exit 0). The legitimate delta is the entry path —
the BDD test crosses the Cyclopts app and `run` wrapper for *every* command,
including the crashing `reconcile`, whereas the integration test calls
`_reconcile.reconcile()` directly for the crash. Both the step docstrings and
the roadmap clause make that distinction load-bearing, so this is not a
redundant test; it is two tests whose overlap is large enough to drift. Worth
flagging so the pair is maintained together: if the recovery contract changes
(e.g. single-pass repair, roadmap 7.11), both the `_MAX_RECOVERY_ATTEMPTS = 3`
bound here and the `range(3)` in the integration test must move in lockstep.

- **Proposed fix:** Once Findings 1-3 land a shared driver, crash fixture, and
  corpus helpers, the residual difference between the two tests is just the
  crash entry path (command vs body). Add a cross-reference comment in each test
  naming its twin and the one axis it varies, and consider parametrizing the
  shared recovery assertions over the two entry paths so the convergence bound
  and target live in one place. No behavioural change.

## Finding 5: The recovery scenario under-asserts the audit receipt

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/steps/torn_turn_recovery_steps.py:251`
  (`reconcile_clears_record`) and the scenario as a whole; contrast
  `tests/steps/reconcile_steps.py:171` (`reconcile_logs_and_keeps_files`).

The sibling `reconcile_steps` scenario pins the `log.md` receipt with a precise
regex (`reconcile: recount: ... current 44800 across 3 chapters`), explicitly so
the assertion "survives a behaviour-preserving refactor of the prose but fails
if the operation or the repaired fields drift". The new recovery scenario
asserts the cleared `[pending_turn]` and the recounted `[word_counts]`, but
never inspects `log.md` for the `complete-pending-turn` receipt that the design
(§5.4) treats as the audited reconciliation record. Recovery could clear the
record and repair the counts while logging the wrong receipt (or none) and the
scenario would still pass. The design's §3.4 D-LOG discipline makes the receipt
the on-disk audit trail; a recovery test is the natural place to assert it
lands.

- **Proposed fix:** Add a `Then` step asserting `log.md` carries a
  `complete-pending-turn` reconcile receipt for the recovered turn (a substring
  or, preferably, a structured-line regex matching the `reconcile_steps`
  precedent). This closes the gap between "the tree settled" and "the settle was
  audited".

## Finding 6: `_RECOUNT_TARGET` restates a magic mapping the suite repeats

- **Category:** inconsistency
- **Severity:** low
- **Location:** `tests/steps/torn_turn_recovery_steps.py:68` (`_RECOUNT_TARGET =
  {"01": 0, "02": 24000, "03": 20800}`); `tests/steps/reconcile_steps.py:177`
  (same literal inline); `tests/test_reconcile_integration.py` and
  `tests/test_reconcile.py` (the `44800`-across-3-chapters total derived from
  the same drafts).

The `done-claim-stale-word-counts` recount convergence target
(`{"01": 0, "02": 24000, "03": 20800}`, summing to 44800 across 3 chapters) is
the same disk-derived fact restated in at least four test sites, each with its
own comment re-explaining where the numbers come from. If the corpus fixture's
draft bodies change, every copy must be hand-updated and any missed copy fails
opaquely. The corpus already owns these drafts, so it can own their recount.

- **Proposed fix:** Expose the expected recount for a named incoherent variant
  from the `working_corpus` package (e.g. alongside `INCOHERENT_VARIANTS`, the
  `_expected` second element the callers currently discard as `_expected`), and
  have the reconcile-family tests assert against that rather than re-literalising
  the mapping. This makes the corpus the single source of truth for both the
  tree and its repaired counts.

## Finding 7: The feature file's design citation is narrower than the scenario proves

- **Category:** docs-gap
- **Severity:** low
- **Location:** `tests/features/torn_turn_recovery.feature:9` (cites "design
  §3.4, §5.4"); the step module docstring additionally invokes ExecPlan
  Decisions D-MECH, D-INPROC, D-CONVERGE, D-DUP.

The Gherkin narrative is the operator-facing artefact, yet it cites only the two
design sections, while the substance of *why* the scenario is shaped as it is —
the bounded two-pass convergence (D-CONVERGE), the command-boundary requirement
(D-MECH/D-INPROC) — lives only in the step docstring and the (now-merged)
ExecPlan. A reader of the feature alone cannot tell why recovery needs a *loop*
rather than a single `reconcile`. This is a minor documentation-locality gap,
not an error.

- **Proposed fix:** Add one clause to the feature's free-text narrative noting
  that a crashed recount converges over a bounded re-entry loop (clear the
  leftover record, then re-apply the recount), so the operator-facing scenario
  is self-explanatory without the step module. Keep the ExecPlan-decision tags
  in the step docstring where they belong.
