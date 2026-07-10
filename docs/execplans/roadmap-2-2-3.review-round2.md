# Logisphere design review — roadmap 2.2.3, round 2

Verdict: **REVISE**. The plan's headline claim — that round-1 blocking point 1
(torn-turn recovery) is resolved by Work item 3a — does not hold against the
real `reconcile` source. The recovery mechanism, as specified, cannot fire.

## Blocking defects

### B1 — refuse-class bijection dominates the pending-turn branch; Work item 3a is unreachable

`derive_reconciliation` (`novel_ralph_skill/state/reconcile.py`, lines 258-264)
evaluates **refuse-class first**:

```python
refuse = [name for name in fired if name in _REFUSE_CLASS]
if refuse:
    return _refuse(refuse)                       # exit 4, REFUSE
if state.pending_turn is not None and PENDING_TURN_CLEARED in fired:
    return _classify_pending_turn(...)           # the branch WI3a edits
```

`MANIFEST_DISK_BIJECTION` is in `_REFUSE_CLASS`. A torn `set-chapters` turn
whose directory set is *partial* (manifest `{1,2}`, on-disk `{1}`) fires
`manifest-disk-bijection` (`disk_evidence.py::_check_manifest_disk_bijection`,
set-equality + contiguity), so `derive_reconciliation` returns REFUSE **before**
`_classify_pending_turn` is ever called. Work item 3a only edits
`_RECOMPUTABLE_BASENAMES` and `_classify_pending_turn`; in the
partial-directory torn state that code is dead. The plan's D8/Idempotence claim
("`check` surfaces the torn turn; `reconcile` COMPLETEs it") is false for the
realistic crash.

Making this recovery work requires changing `derive_reconciliation`'s
**precedence** (classify a `set-chapters` `[pending_turn]` ahead of the
bijection refuse-class). That is exactly the "refactor of the reconcile
derivation precedence" the plan's own Tolerances flag as a
**stop-and-escalate** trigger. The plan asserts the change is "a focused
classifier + mkdir change"; it is not.

### B2 — Work item 3's write ordering makes the manifest unrecoverable, so even fixing precedence does not save the recovery

Work item 3 writes the populated `[chapters]` array only at the **final**
clear-write (step 9), mirroring `_run_reconcile_bracket` (intent write →
in-memory edit → log append → clear+write). The intent write at step 5 persists
the *original empty* manifest plus the `[pending_turn]`. Directories are
created at step 7, before the manifest persists at step 9.

Consequences for the two real torn states:

- **Crash in steps 5-7 (no/partial dirs, manifest still empty on disk):** the
  agent's plan (slug/title/target_words) is **gone** — it was never persisted.
  An empty `chapter-NN/` directory holds none of it. The plan's central premise
  ("an empty chapter directory is recomputable from the manifest, exactly like
  `log.md`", D8) is false here: there is no manifest on disk to recompute from.
  If reconcile mkdir'd dirs against the empty manifest it would *break* the
  bijection (on-disk `{1,2}` vs manifest `{}`), making the tree worse.
- **There is no torn state where the manifest is persisted-populated and only
  empty dirs are missing** — the state the plan's recovery assumes — because
  the manifest persists last. The recovery model and the write ordering
  contradict each other.

A real fix must persist the populated manifest **at the intent write** (before
directory creation), so a torn turn always has the agent's judgement on disk
and only the deterministically-derivable directories outstanding. The plan does
the opposite. (And even with that fix, B1 still blocks classification.)

### B3 — adding `chapter-NN/` to the recomputable set is a genuine design change, not a mechanical extension

Design §5.4 (lines 616-619) enumerates the recomputable torn-turn artefacts as
exactly `state.toml`/`log.md`, and the no-deletion / "fabricates no agent
judgement" rationale (§5.4 lines 626-628) turns on the artefact being derivable
from what remains on disk. An empty `chapter-NN/` directory is only
"recomputable" *given a persisted manifest* (see B2). Work item 3a + the §5.4
doc edit therefore amend a load-bearing recovery invariant; that belongs in ADR
008 as a reasoned design decision with the precedence change spelled out, not
as a "focused classifier" tweak slipped into a sibling task's modules under a
~11-file tolerance.

## Advisory

- A1 (Wafflecat — simpler alternative). The whole torn-`set-chapters` problem is
  manufactured by the decision (D2) to create directories inside
  `set-chapters`. A genuinely-considered alternative: write the manifest only
  (single-file, already atomic, **no `[pending_turn]`, no Work item 3a, no
  reconcile change**), and let a later loop step (or `reconcile`'s existing
  `draft-without-manifest-entry` / bijection path) materialize directories — or
  have the per-chapter drafting step create its own directory on demand. The
  plan rejects this only implicitly (D2 escalation trigger). Given that D2 is
  what forces the multi-file bracket, the torn-turn hazard, the reconcile
  precedence problem, and a whole extra work item, the "manifest-only" option
  deserves an explicit trade-off analysis in the plan before the heavier path
  is chosen. If the bijection-immediately requirement is firm, persisting the
  manifest at the intent write (B2) is the minimum honest design.
- A2 (Doggylump — pre-mortem). The most likely 03:00 incident is precisely the
  partial-directory crash: the agent runs `set-chapters` for a 35-chapter plan,
  the process dies after some `mkdir`s, `check` reports exit 4 (REFUSE), the
  agent runs `reconcile`, reconcile *also* refuses (exit 4), and D3 refuses a
  re-run — the tree is stuck with no sanctioned recovery, which is the exact
  round-1 contradiction the plan claims to have closed. Add a test that drives
  a **partial-directory** torn turn (not just an all-dirs-missing one) and
  asserts reconcile completes it; the plan's Work item 3a/5 tests as written
  ("one or more `chapter-NN/` directories absent") would pass on the
  all-missing case and silently miss the partial case that actually fires the
  bijection.
- A3 (verified, not blocking). cuprum API (`sh.make`, `ExecutionContext`,
  `run_sync`, `ProgramCatalogue`, `ProjectSettings`) confirmed against the
  locked `/data/leynos/Projects/cuprum` source. The exit-2 (CycloptsError) /
  exit-3 (StateInputError) split is confirmed against `contract/runner.py`. The
  compile-exit-3-on-empty-manifest claim is confirmed against `_compile.py`.
  The cyclopts JSON-list mechanism is corroborated (S6) and pinned by an
  in-process probe (S1); acceptable.

## Trail

Source verified: `state/reconcile.py`, `commands/_reconcile.py`,
`state/disk_evidence.py`, `state/_disk_paths.py`, `state/document.py`,
`commands/_state_mutators.py`, `commands/_recount.py`, `commands/_compile.py`;
`docs/novel-ralph-harness-design.md` §3.4/§5.4; cuprum locked source
(`cuprum/sh.py`, `cuprum/catalogue.py`). Skills: logisphere-design-review.
