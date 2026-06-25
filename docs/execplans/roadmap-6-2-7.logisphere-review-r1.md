# Logisphere design review — roadmap 6.2.7 (Round 1)

Reviewer: adversarial Logisphere crew. Date: 2026-06-25. Subject:
`docs/execplans/roadmap-6-2-7.md` (DRAFT).

## Verdict: PROCEED (no blocking defects)

Every load-bearing claim was verified against real source, not the planner's
summary. The plan's central mechanism was reproduced end-to-end through the
real command runner before this verdict was issued.

## Empirical verification (the decisive evidence)

Built `wc.COHERENT_BASELINE`, raised inside the §3.4 `pending_turn` bracket
declaring `working/manuscript/chapter-99/draft.md`, then drove `check`/
`reconcile` through `novel_ralph_skill.contract.runner.run(build_app(), ...)`:

- baseline `derive_reconciliation` → `none` (no recount/refuse trap; D-ONEPASS
  holds);
- producer leaves
  `PendingTurn(operation='write-draft', paths=('.../chapter-99/draft.md',))`;
- `check` → exit 4, `result.reconciliation.action == "rollback-pending-turn"`,
  `discrepancies == ['pending-turn-cleared']`;
- `reconcile` → exit 0 (single pass); follow-up `check` → exit 0;
- `pending_turn` cleared to `None`; zero `working/` files removed; drafts
  byte-for-byte identical; `log.md` carries `reconcile: rollback-pending-turn:`.

Every assertion the plan promises is confirmed.

## Source-verified claims

- Classification precedence (`reconcile.py:256-283`), `PENDING_TURN_CLEARED`
  fires whenever `state.pending_turn is not None` (`disk_evidence.py:190-205`),
  `_RECOMPUTABLE_BASENAMES = {state.toml, log.md}` (`reconcile.py:89`).
- Producer signature `pending_turn(path, *, operation, paths)` and
  leave-on-error
  contract (`document.py:222-266`).
- `_pending_turn_edit` is a no-op for ROLLBACK and deletes nothing
  (`_reconcile.py:150-180`); receipt prefix `reconcile:` (`_reconcile.py:87`).
- Envelope nesting `result.reconciliation.{action,discrepancies,detail}`
  (`novel_state.py:160-176, 230-239`).
- `build_working_tree` returns `dest/working` and writes `state.toml` there
  (`_builder.py:206-235`); `BASE = COHERENT_BASELINE`, rollback variant is BASE
  - `pending_turn` only (`_variant_base.py:25`,
  `_reconcile_variants.py:200-206`).
- Binder convention `from steps.X import *  # noqa: F403` +
  `scenarios("features/X.feature")`
  matches `tests/test_torn_turn_rollback_bdd.py`.
- Locked pins in `uv.lock`: cuprum 0.1.0, cyclopts 4.18.0, pytest-bdd 8.1.0,
  pytest-timeout 2.4.0, pytest-xdist 3.8.0 — all match the plan exactly.
- No-cuprum claim holds: no `subprocess`/cuprum call in `commands/*.py`.
- Sibling BDD tests (`test_torn_turn_recovery_bdd.py`, `test_torn_turn_bdd.py`)
  pass green under the real harness; existing rollback unit/derivation tests
  pass.
- Design §5.4 line 552 ("Rolling back removes nothing"), line 609 (unrecoverable
  artefact = `draft.md`/`done.flag`) support the plan's wording.
- `interrogate fail-under = 100` over `novel_ralph_skill tests` — plan correctly
  obliges module + per-callable docstrings on the new step module and binder.

## Crew findings (none blocking)

- 🟢 Pandalump: the roadmap clause "crashes `reconcile`" is mechanically
  impossible for ROLLBACK; the plan diagnoses this (D-MECH) and substitutes the
  faithful §3.4 producer. The deviation from the literal roadmap wording is
  sound and well-evidenced, not a structural defect.
- 🟢 Telefono: drives only locked in-process interfaces; envelope shape
  verified;
  no contract evolution. The plan asserts `action`/`discrepancies`, not the
  exact `detail` prose — correctly robust.
- 🟢 Doggylump: pre-mortem covered. The realistic failure (misclassification as
  COMPLETE/REFUSE) is pinned by an explicit `action == "rollback-pending-turn"`
  assertion and the Disposition tolerance; empirically it cannot misfire over
  the coherent baseline.
- 🟢 Buzzy Bee / Dinolump: a single throwaway-`tmp_path` BDD scenario; trivial
  cost; mirrors an existing green sibling; cognitive load minimal.
- 💡 Wafflecat (advisory): the strongest alternative is to add the
  `pending_turn`
  field at the spec level (`dc.replace(BASE, pending_turn=...)`) like the
  corpus variant rather than via the runtime bracket. The plan rightly rejects
  it: the spec field is the *hand-planted* path that already has body-call
  coverage (`test_reconcile.py`); the runtime bracket is what makes this a
  *real torn turn* and closes the genuine gap. No change required.

## Advisory (non-blocking)

- D-DUP duplicates `_run`/`_run_capturing`/capture helpers from
  `torn_turn_recovery_steps.py`. Acceptable per the established 6.2.5 precedent
  and the filed shared-driver task (7.23.3). If a future reviewer pushes, the
  extraction is a cheap addendum.
- Cosmetic: the plan's "exactly 5 files" tolerance counts the roadmap + this
  plan; the reviewer added a sixth file (this review note). It is a review
  artefact, not an implementation file, so it does not breach the file
  tolerance — but the implementer should not delete or count it.
