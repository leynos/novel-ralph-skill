# Logisphere design review — roadmap 7.1.3 (round 2)

Subject: `docs/execplans/roadmap-7-1-3.md` — "Single-source the
`Reconciliation` payload projection".

Verdict: **Proceed with conditions.** The round-1 blocking defect (B1, the
mischaracterised refuse snapshot) is fully and correctly resolved — every
corrected claim was re-verified against source and is accurate. The design
(one `reconciliation_payload` projection, four arms routed, dict-not-envelope,
no behaviour change) is sound and unchanged. Round 2 surfaces two **new**
implementation-accuracy defects the round-1 review did not catch, both about
guidance that would actively mislead the implementer. Neither is a design flaw;
both are addressable with prose.

## Round-1 B1 fix — re-verified against source, accepted

The round-2 plan claims B1 is resolved by prose-only edits. Independently
confirmed against source:

- `tests/test_reconcile_refuse.py:187` asserts
  `json.dumps(env, sort_keys=True) == snapshot` (keys SORTED). Confirmed.
- The stored `test_reconcile_refuse.ambr` `result` reads
  `{"action", "detail", "discrepancies"}` — alphabetical, NOT the code's
  `{action, discrepancies, detail}` insertion order. Confirmed by inspecting
  the `.ambr`.
- `render_machine` (`contract/envelope.py:151`) is `json.dumps(ordered)` with
  **no** `sort_keys`; `test_novel_state_check_disk.py:234,248` assert
  `raw == snapshot`. The stored `check_disk` `reconciliation` blocks read
  `{action, discrepancies, detail[, current, by_chapter]}` (insertion order),
  for both the `recount` and `refuse` classes — but only as `check` REPORTS
  them (READ path). Confirmed.
- The Work Item 2 `list(reconciliation_payload(...).items()) == [...]` ordered
  assertion is correctly elevated to the NAMED PRIMARY order pin for the
  write-side `REFUSE`/`NONE` `result` envelope, and flagged load-bearing.

The Constraints "base-dict order is preserved" bullet, Risk 1, Risk 3, the
"Verified external facts" snapshot entry, the Validation behaviour-acceptance
bullet, and the revision note all now describe the backstop accurately. B1 is
closed.

## New blocking

### B2 — Work Item 3's import-block heuristic points `novel_state.py` at the wrong (TYPE_CHECKING) block

Work Item 3 step 1 instructs the implementer to add `reconciliation_payload`
"to the existing `from novel_ralph_skill.state import (...)` import block
(confirm with `leta refs Reconciliation` which block already imports
`Reconciliation` here)."

That heuristic is wrong for `novel_state.py`. There are two `state` import
blocks in that file:

- the **runtime** block at `novel_state.py:80` imports
  `build_initial_document, check_disk_evidence, derive_reconciliation,
  validate_state, write_document_atomically` — and does **NOT** import
  `Reconciliation`;
- the **TYPE_CHECKING-only** block at `novel_state.py:108`
  (`if typ.TYPE_CHECKING:`) imports `Reconciliation, State, Violation`.

`novel_state.py` has `from __future__ import annotations` (line 41), so
`_render_reconciliation`'s `Reconciliation` annotation is a string and the
type-only import is sufficient — which is why `Reconciliation` lives in the
TYPE_CHECKING block. `reconciliation_payload` is **called at runtime**, so it
must go in the runtime block at line 80 (beside `derive_reconciliation`).

Following the plan's literal instruction — "the block that already imports
`Reconciliation`" — lands the import in the TYPE_CHECKING block at line 108,
which yields a `NameError` at runtime. `make all` would catch it, but the plan
must not direct the implementer to the wrong block.

Required fix (prose only): change the `novel_state.py` guidance to "add
`reconciliation_payload` to the **runtime** `from novel_ralph_skill.state
import (...)` block at line 80 that already imports `derive_reconciliation`
(NOT the `TYPE_CHECKING` block at line 108 that imports `Reconciliation` — the
file uses `from __future__ import annotations`, so the projection, a
runtime-called symbol, needs a runtime import)." The `_reconcile.py` guidance
(line 55 block, which imports both `Reconciliation` and `derive_reconciliation`
at runtime) is correct as written and needs no change.

### B3 — The byte-identity claim for `_write_outcome` rests on an unstated invariant (`action == reconciliation.action`) the plan never pins

The plan asserts the projection body is "byte-for-byte the body already in
`_render_reconciliation` / `_write_outcome`" and that routing is a
"behaviour-preserving substitution". For three of the four arms this is
self-evident — they already key off `reconciliation.action` (or, for `NONE`,
`action = reconciliation.action` at `_reconcile.py:291`).

`_write_outcome` is the exception. Its current body builds
`"action": str(action)` from its **parameter** `action`
(`_reconcile.py:216,225`), not from `reconciliation.action`. The projection
the plan installs uses `str(reconciliation.action)`. These are byte-identical
**only if** every `_write_outcome` caller passes `action == reconciliation.action`.

Verified that they do — today:

- `_reconcile.py:322` calls `_write_outcome(action, reconciliation)` where
  `action = reconciliation.action` (`:291`). Equal.
- `_reconcile.py:313` calls
  `_write_outcome(ReconcileAction.RECREATE_LOG, reconciliation)`, and
  `derive_reconciliation` constructs the RECREATE_LOG `Reconciliation` with
  `action=ReconcileAction.RECREATE_LOG` (`reconcile.py:332-333`). Equal.
- `test_reconcile.py:262` (`result["action"] == "recreate-log"`) exercises the
  `:313` path through the routed projection, so the existing regression net
  catches a divergence on the one caller where the parameter could in
  principle differ from `reconciliation.action`.

So the substitution is genuinely behaviour-preserving and the existing suite
covers it. But the plan presents `_write_outcome` as trivially byte-identical
("byte-identical dict body to `_render_reconciliation`") and never names the
`action` (parameter) versus `reconciliation.action` distinction, nor the
invariant the substitution depends on. An implementer who notices the
mismatch mid-edit has no guidance that it is intended and covered; one who does
not notice has been told something subtly false (the bodies are NOT textually
identical — one reads `str(action)`, the other `str(reconciliation.action)`).

Required fix (prose only, no design change): in Work Item 3's `_write_outcome`
step, state that `_write_outcome` currently serialises its `action`
**parameter** (`str(action)`), whereas the projection serialises
`str(reconciliation.action)`; that this is byte-identical because both
`_write_outcome` call sites (`:313`, `:322`) pass `action ==
reconciliation.action` (the `:313` RECREATE_LOG case is the one where they are
nominally distinct symbols but equal in value, pinned by
`test_reconcile.py:262`); and that this caller invariant is what makes the
substitution safe. Add it to the "Verified external facts" so the next agent
need not re-derive it.

## Advisory

### A1 — "byte-for-byte the body already in `_render_reconciliation` / `_write_outcome`" overstates textual identity (Work Item 1)

The Work Item 1 prose ("This is byte-for-byte the body already in
`_render_reconciliation` / `_write_outcome`, lifted to its owner module") is
true of `_render_reconciliation` (which reads `str(reconciliation.action)`) but
not literally of `_write_outcome` (which reads `str(action)`). Resolve together
with B3: say the projection is value-identical, and that `_write_outcome`'s
parameter equals `reconciliation.action` at both call sites.

### A2 — Confirm there is no second write-side order backstop (cross-command identity suite)

`tests/cross_command_contract/test_mutator_identity.py:89` snapshots each
mutator's success `result` via an unsorted `json.dumps(envelope)` →
`json.loads` round-trip. If `reconcile` is among `MUTATOR_CASES`, that snapshot
MAY additionally pin the write-side `result` key order for the success
(non-`REFUSE`) arms, which would make the plan's "the `items()` test is the
only write-side order pin" claim conservative rather than exhaustive — a
strengthening, not a defect. The plan need not change, but the implementer
should run `tests/cross_command_contract/` as part of the unedited regression
net (it is already inside `make all`) and not be surprised if it also guards
order. Recorded for confidence; no change required.

### A3 — Carry-over A1/A2 from round 1 are addressed

Round-1 A1 (lean WI2 harder on `items()`) is now fully absorbed: the plan names
the `items()` assertion the primary order pin and marks it load-bearing.
Round-1 A2 (NONE/RECREATE_LOG pinned by semantic, not snapshot, assertions) is
consistent with the current plan. No further action.

## Pre-mortem (Doggylump)

1. **Most likely failure (new this round):** the implementer adds the runtime
   import to the TYPE_CHECKING block (B2), or, reading "byte-identical body",
   "tidies" `_write_outcome` to drop its `action` parameter or changes a caller
   to pass a literal action that no longer equals `reconciliation.action` (B3).
   The first is caught by `make all` (runtime `NameError`); the second is
   caught by `test_reconcile.py:262` for RECREATE_LOG but is a latent trap for
   any future caller. Mitigation: B2 + B3 prose fixes.
2. **Second failure (carried):** a future field is added to `Reconciliation`
   and the projection is reordered, with the implementer trusting the refuse
   snapshot to catch it. Mitigation: already addressed — the `items()` pin is
   now the named primary order pin and the refuse snapshot's sort is
   documented.
3. **Third failure (carried):** the inlined `NONE` arm is left hand-built.
   Mitigation: the `git grep '"action": str('`-returns-one-hit observable in
   WI3 catches it; already in the plan.

## Alternatives checkpoint (Wafflecat)

Unchanged from round 1 and still correct: the roadmap permits a
`Reconciliation.to_payload()` method; the free function is the right call
(frozen `slots` data shape; module grain of free functions; 7.1.1 precedent).
No credible structurally-different alternative exists — this is a mechanical
four-site consolidation with a snapshot-pinned target shape. That the only
"alternative" is method-vs-function cosmetics confirms the design is on solid
ground.

## What was verified against source this round

- `git grep '"action": str(' novel_ralph_skill/` → exactly four sites:
  `_reconcile.py:225,251,297`, `novel_state.py:139`. After routing, the only
  remaining hit is the projection.
- `reconciliation_payload` / `to_payload` pre-exist nowhere in
  `novel_ralph_skill/` or `tests/`. Symbol is new.
- `reconcile.py` is **341** lines; +~24 → ~365, under the 400 cap
  (`pyproject.toml [tool.pylint] max-module-lines = 400`; `interrogate
  fail-under = 100`; Ruff `line-length = 88`).
- The four arms and their exact bodies: `_render_reconciliation`
  (`novel_state.py:138-146`, `str(reconciliation.action)`), `_write_outcome`
  (`_reconcile.py:224-231`, `str(action)` — parameter), `_refuse_outcome`
  (`_reconcile.py:250-254`, `str(reconciliation.action)`, base three), `NONE`
  arm (`_reconcile.py:296-300`, `str(action)` with `action =
  reconciliation.action`, `discrepancies: []`).
- `_write_outcome` callers: `_reconcile.py:313`
  (`ReconcileAction.RECREATE_LOG`, equals `reconciliation.action` per
  `reconcile.py:332-333`) and `:322` (`action`, equals `reconciliation.action`
  per `:291`). `test_reconcile.py:262` pins the RECREATE_LOG action through the
  routed path.
- Snapshot assertion modes: `test_reconcile_refuse.py:187`
  `json.dumps(env, sort_keys=True)` (sorted; field set only);
  `test_novel_state_check_disk.py:234,248` `raw == snapshot` against unsorted
  `render_machine` (insertion order, READ path).
- `state/__init__.py` re-exports `ReconcileAction, Reconciliation,
  derive_reconciliation` (import `:62-66`, `__all__` `:136-149`); adding one
  name is the established pattern.
- Both command modules have `from __future__ import annotations`
  (`novel_state.py:41`, `_reconcile.py:40`); `Reconciliation` is a
  TYPE_CHECKING-only import in `novel_state.py:108`, a runtime import in
  `_reconcile.py:55`.
- No external-library behaviour is load-bearing: no new subprocess,
  console-script path, `--flag`, or third-party import. cuprum / Cyclopts /
  pytest-timeout / uv research has no bearing on any work item. The plan's
  "Verified external facts" is correct to state this explicitly.

## Trail (docs and skills relied on)

- `docs/novel-ralph-harness-design.md` §3.3 (CQS read/write split), §5.4
  (disk-authoritative reconciliation).
- `docs/issues/audit-2.3.2.md` Finding 2; non-goal Findings 1, 3-6.
- `docs/adr-001-deterministic-judgemental-boundary.md`,
  `docs/adr-003-shared-interface-contract.md`.
- `docs/roadmap.md` entry 7.1.3; `docs/execplans/roadmap-7-1-1.md` (sibling
  precedent); `docs/execplans/roadmap-7-1-3.logisphere-review-r1.md` (round 1).
- `AGENTS.md` (snapshot discipline; test-location rule).
- Source: `state/reconcile.py`, `commands/novel_state.py`,
  `commands/_reconcile.py`, `state/__init__.py`, `contract/envelope.py`,
  `tests/test_reconcile_refuse.py`, `tests/test_novel_state_check_disk.py`,
  `tests/test_reconcile.py`, `tests/test_reconcile_e2e.py`,
  `tests/cross_command_contract/test_mutator_identity.py`, the two
  `tests/__snapshots__/*.ambr` files.
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
