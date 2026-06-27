# Logisphere design review — roadmap 7.1.3 (round 3)

Verdict: **Proceed.** No blocking defects. The two prior rounds' blocking
findings (r1 B1 — the mischaracterised `test_reconcile_refuse.ambr` snapshot;
r3-recorded B2 and B3 — the `novel_state.py` import-block misdirection and the
`_write_outcome` "byte-identical" overstatement) are all fully and correctly
resolved, and every corrected claim was re-verified against current source.
The design (one `reconciliation_payload` projection in `state/reconcile.py`,
four arms routed through it, dict-not-`CommandOutcome` return, no behaviour
change) is sound, atomic, ordered, testable, and design-conformant.

This round was genuinely adversarial: I re-read the plan from disk and
independently re-verified every load-bearing source claim rather than trusting
the planner's summary or the prior reviews. Nothing new rose to blocking.

## What was independently verified (all TRUE against source)

- **Four hand-built sites** exist exactly as described:
  `_render_reconciliation` (`novel_state.py:138-146`, `str(reconciliation.action)`,
  recount-guarded); `_write_outcome` (`_reconcile.py:224-231`, `str(action)`
  parameter, recount-guarded); `_refuse_outcome` (`_reconcile.py:250-254`, base
  three keys, `str(reconciliation.action)`); the `NONE` arm
  (`_reconcile.py:296-300`, `str(action)`, `discrepancies: []`).
- **B3 caller invariant** holds: `_write_outcome`'s `action` parameter equals
  `reconciliation.action` at both callers — `:322` passes `action` (bound to
  `reconciliation.action` at `:291`), `:313` passes the literal `RECREATE_LOG`,
  and `derive_reconciliation` builds that `Reconciliation` with
  `action=RECREATE_LOG` (`reconcile.py:332-336`). Pinned by
  `tests/test_reconcile.py:262` (`result["action"] == "recreate-log"`).
- **B2 import-block direction** holds: `novel_state.py:41` has
  `from __future__ import annotations`; the runtime `state` block at `:80`
  imports `derive_reconciliation` (not `Reconciliation`); `Reconciliation` is
  TYPE_CHECKING-only at `:103-108`. `_reconcile.py:55-63` is a runtime block
  importing both `Reconciliation` and `ReconcileAction`. The plan correctly
  directs `reconciliation_payload` into the line-80 runtime block.
- **B1 snapshot asymmetry** holds: `render_machine` (`contract/envelope.py:151`)
  is `json.dumps(ordered)` with **no** `sort_keys`, asserted `raw == snapshot`
  at `test_novel_state_check_disk.py:234,248` — pins insertion order, READ path
  only. `test_reconcile_refuse.py:187` is `json.dumps(env, sort_keys=True)`,
  and the stored `.ambr` reads `{action, detail, discrepancies}` (alphabetical),
  pinning the field set, not order. The check_disk `.ambr` stores
  `{action, discrepancies, detail, current, by_chapter}` (code order),
  including the recount-pair order. The write-side order is therefore guarded
  solely by the Work Item 2 `items()` pin — correctly named load-bearing.
- **Dataclass defaults**: `recounted_by_chapter: ... = None` (`reconcile.py:150`),
  so REFUSE/NONE reconciliations yield exactly the base three keys through the
  projection — behaviour-preserving.
- **Re-export pattern**: `state/__init__.py` imports
  `ReconcileAction, Reconciliation, derive_reconciliation` from
  `state.reconcile` and lists them in `__all__`; adding one name beside
  `derive_reconciliation` is the established mechanism.
- **Scope conformance**: roadmap 7.1.3 (`docs/roadmap.md:2513-2536`) and audit
  Finding 2 (`docs/issues/audit-2.3.2.md:68-100`) both name exactly this task,
  endorse a free function beside `Reconciliation` in `state/reconcile.py`, and
  state the read/write envelope code and exit codes "genuinely differ" and stay
  put — exactly the plan's scope and non-goals.
- **Quality gates**: `max-module-lines = 400` (`pyproject.toml:173`);
  `reconcile.py` is 341 lines, so the projection plus docstring fits.
  `interrogate fail-under = 100` (`:309`) — the function carries a docstring.
  AGENTS.md snapshot discipline (`:148-158`) — the plan pairs the projection
  with semantic `items()` assertions rather than snapshot-only coverage.
- **No external-library fork**: no new subprocess, console-script path, flag,
  or third-party import. The cuprum/Cyclopts/pytest-timeout/uv research has no
  bearing; the e2e suite (through cuprum) stays green unedited as the
  no-behaviour-change backstop. Correctly stated, not hedged.

## Crew lenses

- **Pandalump (structure):** Boundaries are right. The projection owns
  serialisation only; the four arms keep their `CommandOutcome`, exit code, and
  `messages`. The CQS read/write split survives. One owner module
  (`state/reconcile.py`), matching its free-function grain.
- **Wafflecat (alternatives):** The only alternative is method vs free function;
  the roadmap permits both and the module grain + 7.1.1 precedent favour the
  free function chosen. No structurally-different alternative exists — a strong
  signal the design is settled.
- **Buzzy Bee (scaling):** A pure dict projection over an immutable dataclass;
  no allocation, IO, or scaling surface. N/A by construction.
- **Telefono (contracts):** The envelope byte shape is the contract, pinned by
  two snapshots plus the new `items()` order pin. The projection reproduces it;
  the asymmetric order coverage is correctly understood and backstopped.
- **Doggylump (failure modes):** The named failure paths (reorder, incomplete
  routing leaving an inline dict, accidental recount-pair on REFUSE/NONE,
  missed export) each have a concrete catch (`items()` pin,
  `git grep '"action": str('` single-hit, `None`-default gating + sorted refuse
  snapshot, `make all` import resolution). The escalation Tolerances cover the
  "snapshot must move" case correctly — treat as behaviour drift, do not
  re-record.
- **Dinolump (viability):** A mechanical three-item consolidation mirroring the
  delivered 7.1.1 sibling. Well within team capability; reversible; additive.

## Pre-mortem

- *Reorder ships green on the write path.* Mitigated: the Work Item 2
  `list(payload.items())` assertion is the only write-side order check and is
  named load-bearing. No snapshot guards it (refuse is sorted; check_disk is
  READ-only). Plan is explicit not to weaken it.
- *Implementer puts the import in the TYPE_CHECKING block and ships a NameError.*
  Mitigated: Work Item 3 step 1 now spells out the runtime-block placement and
  forbids the old heuristic; `make all` would catch a regression anyway.
- *A future field rename silently diverges check and reconcile.* This is the
  defect the task exists to remove; after routing, the single projection makes
  divergence structurally impossible.

## Advisory (non-blocking, navigational only — do not gate on these)

- The plan states `reconcile.py` is "at 342 lines"; it is **341**. Harmless
  (still well under 400); fix opportunistically if convenient.
- The plan cites the `state/__init__.py` reconcile import block as lines
  `63-67`; it is `62-66`, and `__all__` likewise drifts by one. The symbols and
  the "beside `derive_reconciliation`" instruction are unambiguous, so this does
  not impede implementation. (The audit's own line citations have drifted
  further from source — e.g. it lists `_render_reconciliation` at 142-150 vs the
  current 138-146 — confirming this class of citation is navigational, not
  load-bearing.)

## Trail (docs and skills relied on)

- `docs/novel-ralph-harness-design.md` §3.3 (CQS read/write split), §5.4
  (disk-authoritative reconciliation).
- `docs/issues/audit-2.3.2.md` Finding 2; non-goal Findings 3-6.
- `docs/adr-001-deterministic-judgemental-boundary.md`,
  `docs/adr-003-shared-interface-contract.md`.
- `docs/roadmap.md` entry 7.1.3; `docs/execplans/roadmap-7-1-1.md` (sibling
  precedent); rounds r1 and r2 review files.
- `AGENTS.md` (snapshot discipline `:148-158`; interrogate/pylint gates);
  `pyproject.toml` (`max-module-lines`, `fail-under`).
- Source: `state/reconcile.py`, `commands/novel_state.py`,
  `commands/_reconcile.py`, `state/__init__.py`, `contract/envelope.py`,
  `tests/test_reconcile.py`, `tests/test_reconcile_refuse.py`,
  `tests/test_novel_state_check_disk.py`, the two `tests/__snapshots__/*.ambr`.
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
