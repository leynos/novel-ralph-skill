# Logisphere design review — roadmap 7.1.3 (round 1)

Subject: `docs/execplans/roadmap-7-1-3.md` — "Single-source the
`Reconciliation` payload projection".

Verdict: **Proceed with conditions.** The plan is accurate, atomic, ordered,
testable, and design-conformant. Every load-bearing factual claim was verified
against source. One prose defect (an overstated snapshot claim) must be
corrected so the next implementer is not misled about what the regression net
actually guarantees; one small advisory tightens the test.

## What was verified against source (not the planner's summary)

- The four hand-built sites and their exact bodies:
  - `_render_reconciliation` (`novel_state.py:129-146`) — base three keys +
    `recounted_by_chapter is not None`-guarded recount pair. Confirmed.
  - `_write_outcome` (`_reconcile.py:215-234`) — byte-identical dict body to
    `_render_reconciliation`. Confirmed.
  - `_refuse_outcome` (`_reconcile.py:237-256`) — base three keys only.
    Confirmed.
  - `NONE` arm (`_reconcile.py:293-302`) — base three keys with `discrepancies`
    inlined as the literal `[]`. Confirmed; and `derive_reconciliation`
    constructs the `NONE` `Reconciliation` with `discrepancies=()`
    (`reconcile.py:339`), so `list(()) == []` — the routed projection is
    byte-identical, including the empty list. The plan's Risk-3 claim holds.
- `git grep '"action": str(' novel_ralph_skill/` returns exactly the four sites
  today (`_reconcile.py:225,251,297`, `novel_state.py:139`). After routing, the
  only remaining hit is inside the new function. The observable is sound.
- `reconciliation_payload` / `to_payload` do not pre-exist anywhere in
  `novel_ralph_skill/` or `tests/`. The symbol is genuinely new.
- `state/__init__.py` already re-exports `ReconcileAction`, `Reconciliation`,
  `derive_reconciliation` (import block `:62-66`, `__all__` `:136-149`); adding
  one name there is the established pattern, as claimed.
- `_reconcile.py` already imports `Reconciliation`, `ReconcileAction`,
  `derive_reconciliation` from `novel_ralph_skill.state` at top (`:55-63`), so
  adding `reconciliation_payload` to that block is a one-line edit, as claimed.
- `reconcile.py` is **341** lines (plan says 342 — immaterial). The ~24-line
  addition lands it near 365, comfortably under the 400 cap. The line-cap risk
  is real but the headroom is adequate; the Constraint to re-check after the
  addition is the correct guard.
- Roadmap entry 7.1.3 (`roadmap.md:2513-2536`) names *either*
  `to_payload()` *or* `reconciliation_payload()`; the free-function choice is
  in-scope and the Decision Log justification (module grain; 7.1.1 precedent)
  is sound.
- Audit-2.3.2 Finding 2 (`audit-2.3.2.md:68-100`) matches the plan's reading
  exactly: centralize *only* the `Reconciliation`-to-dict serialization; the
  read/write *envelope code* and *exit codes* "genuinely differ" and stay at the
  call sites. The non-goals (Findings 3-6) are correctly excluded.
- No external-library behaviour is load-bearing. This is a pure-Python refactor
  with no new subprocess, console-script path, `--flag`, or third-party import.
  The cuprum / Cyclopts / pytest-timeout / uv research mandated by the workflow
  has no bearing on any work item here — verified by inspecting the four arms
  and their callers. The plan's "Verified external facts" section is correct to
  state this explicitly rather than hedge.

## Blocking

### B1 — The plan misrepresents the `test_reconcile_refuse.ambr` snapshot as an insertion-order backstop; it is not

The Constraints section ("base-dict order is preserved … because the JSON
envelope is snapshot-pinned (`…check_disk.ambr`, `…reconcile_refuse.ambr`)")
and Risk 1 ("The two `.ambr` snapshot suites are the backstop: they fail loudly
if a byte moves") both assert that *both* snapshots pin key order. This is
false for the refuse snapshot.

Evidence:

- `tests/test_reconcile_refuse.py:187` asserts
  `json.dumps(env, sort_keys=True) == snapshot` — **keys are sorted**. The
  stored snapshot shows `result` as `{"action", "detail", "discrepancies"}`
  (alphabetical), not the `{action, discrepancies, detail}` insertion order the
  code produces. A reordered projection would therefore **not** fail this
  snapshot.
- By contrast `tests/test_novel_state_check_disk.py:234,248` assert
  `raw == snapshot` where `raw` is the unsorted `render_machine` output
  (`contract/envelope.py:126-151`, `json.dumps(ordered)` with **no**
  `sort_keys`). The stored snapshot preserves `action, discrepancies, detail,
  current, by_chapter` in insertion order. This snapshot **is** a genuine
  order backstop, for both the base shape and the recount-pair position.

Impact: the plan's stated safety argument names a backstop that does not exist.
The actual order guarantee comes from (a) the check-disk recount/refuse
snapshots and (b) the WI2 `list(payload.items())` assertion — which is why the
plan is still correct in substance. But leaving the prose as written tells the
implementer the refuse snapshot will catch a reorder, so a reorder bug could
ship green on the refuse path if the WI2 `items()` pin were ever weakened or
dropped.

Required fix (prose only, no design change): correct the Constraints and Risk-1
text to state that the **`check_disk` recount/refuse snapshots** are the
insertion-order backstop (they use raw `render_machine` output), while the
`reconcile_refuse.ambr` snapshot is `sort_keys=True` and therefore pins the
*field set*, not the order. The `list(payload.items())` ordered assertion in
WI2 must then be flagged as the *primary* order pin (not merely a convenience),
since it is the only order check that covers the write-side `REFUSE`/`NONE`
result envelope.

## Advisory

### A1 — Add an explicit write-side order assertion or lean WI2 harder on `items()`

Because the `reconcile_refuse.ambr` snapshot sorts keys (B1), the write-side
`result` envelope's *insertion order* is pinned by **no** existing snapshot —
only by the new WI2 `items()` assertion against the projection in isolation.
That is sufficient (one projection feeds all four arms), but the plan should
state this dependency plainly so the WI2 `list(payload.items())` assertions are
treated as load-bearing rather than belt-and-braces. No new test is strictly
required; the conclusion only needs to be made explicit alongside the B1 fix.

### A2 — NONE/RECREATE_LOG arms are pinned by semantic assertions, not snapshots — confirm the plan says so

The plan claims "the NONE shape is pinned by the reconcile
integration/derivation suites". Verified: `test_reconcile_integration.py:154`
and `test_reconcile.py:298` assert `result["action"] == "none"`;
`test_reconcile.py:262-266` assert the `recreate-log` action and its
discrepancy. These pin `action`/`discrepancies` through the routed projection
but not full key order for these two arms. Combined with the WI2 `items()` pin
(one shared projection) this is adequate. No change required; recorded for the
implementer's confidence.

## Pre-mortem (Doggylump)

1. **Most likely failure:** a future field is added to `Reconciliation` and the
   implementer reorders the projection dict, expecting the snapshots to catch a
   byte move. The `check_disk` snapshots catch the read path, but the write-side
   `REFUSE`/`NONE` order is caught only by the WI2 `items()` pin. If that pin
   were authored loosely (e.g. `payload == {...}` instead of
   `list(payload.items()) == [...]`), the reorder ships green on the write path.
   Mitigation: B1 + A1 — make the `items()` assertion the named primary order
   pin and document that the refuse snapshot does not cover order.
2. **Second failure:** the `reconcile.py` line cap. At 341 lines, the addition
   is safe, but a verbose docstring could brush 400. Mitigation: the Constraint
   already requires a post-addition line check; keep it.
3. **Third failure:** an arm is partially routed (most likely the inlined `NONE`
   arm), leaving one hand-built dict. Mitigation: the
   `git grep '"action": str('`-must-return-one-hit observable in WI3 catches
   this; it is already in the plan.

## Alternatives checkpoint (Wafflecat)

The roadmap permits a `Reconciliation.to_payload()` method. The plan chose a
free function. This is the right call for this module: the dataclass is a frozen
`slots` pure data shape and the module's grain is free functions over it
(`derive_reconciliation`, `_refuse`, `_recount`), and the 7.1.1 sibling set the
free-function precedent. No credible structurally-different alternative exists —
the task is a mechanical four-site consolidation with a snapshot-pinned target
shape. That the only "alternative" is method-vs-function cosmetics is a strong
signal the design is on solid ground.

## Trail (docs and skills relied on)

- `docs/novel-ralph-harness-design.md` §3.3 (CQS read/write split), §5.4
  (disk-authoritative reconciliation).
- `docs/issues/audit-2.3.2.md` Finding 2 (the originating finding) and the
  non-goal Findings 3-6.
- `docs/adr-001-deterministic-judgemental-boundary.md`,
  `docs/adr-003-shared-interface-contract.md`.
- `docs/roadmap.md` entry 7.1.3.
- `AGENTS.md` (test-location rule `:143-146`; snapshot discipline).
- Source: `state/reconcile.py`, `commands/novel_state.py`,
  `commands/_reconcile.py`, `state/__init__.py`, `contract/envelope.py`,
  `tests/test_reconcile_refuse.py`, `tests/test_novel_state_check_disk.py`,
  `tests/test_reconcile.py`, `tests/test_reconcile_integration.py`, the two
  `tests/__snapshots__/*.ambr` files.
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
