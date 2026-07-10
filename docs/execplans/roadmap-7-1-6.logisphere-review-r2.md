# Logisphere design review — roadmap 7.1.6 — Round 2

Verdict: 🔄 **Revise.** Round 2 correctly closed all three round-1 findings (B1
all eight refs, B2 by adopting Wafflecat's cross-reference-only discriminator,
B3 narrative). But the round-2 redesign of the discriminator introduced two new
load-bearing defects that make Work Item 3 fail `make all` on the normalized
tree as specified. Both are verified against the real source. They go back to
the planner.

## What round 2 got right (credit where due)

- **B1 resolved.** WI1 now enumerates all eight re-export references in
  `_compile.py` (lines 12, 14, 34, 104, 106, 175, 181, 186) — verified by grep,
  exact match. The post-WI1 zero-hit gate is correct.
- **B2 resolved in spirit.** The plan drops the member-enumeration heuristic and
  commits to cross-reference-first, registry-keyed discrimination, exactly the
  alternative round-1 Wafflecat recommended and the Tolerance sanctions. The
  `check_compiled`-shaped negative fixture (must PASS) is the right regression
  guard.
- **B3 resolved.** The Source-verification section and Artefacts now expect the
  three test-docstring hits as out-of-scope.
- **Registry coverage boundary** is now explicit (Decision Log "registry
  coverage"): `concatenate_drafts`/`present_draft_bodies` are
  normalized-but-unguarded by design, `compile_manuscript` is not a registry
  row. This satisfies round-1's Improvement.
- **cuprum / no-subprocess scoping** remains correct. The guard reads `__doc__`
  in process, mirroring `test_developers_guide_contract_drift_guard.py`. There is
  genuinely no Cyclopts / pytest-timeout / uv behaviour to pin; no external-lib
  citation is owed. Confirmed: `cuprum` appears only in e2e/installed-binary
  fixtures, never the in-process unit guards.

## Blocking findings

### 🔴 R2-B1 (Telefono / Pandalump) — the guard reds a registered consumer that the plan refuses to edit

WI3 step 2's consumer assertion #2 requires *each* consumer `__doc__` to contain
the canonical defining-module dotted path
(`novel_ralph_skill.state.compile_model.compiled_matches_drafts`) as a substring.
The Decision Log "registry coverage" row 1 registers four consumers, including
**`compile_model.compile_is_current`**.

But `compile_is_current`'s docstring (compile_model.py lines 90–119) does **not**
carry that string. It cross-references the projection with the *bare relative*
spelling `:func:\`compiled_matches_drafts\`` (line ~105) and points at
`:func:\`~novel_ralph_skill.state.disk_evidence._check_compiled_matches_drafts\``
— never `...state.compile_model.compiled_matches_drafts`. Verified:

```console
$ python3 -c "...region = compile_is_current docstring..."
compile_is_current carries canonical path substring? False
compile_is_current carries bare re-export tail?       False
```

The plan simultaneously asserts (Relevant files; "Source verification") that
`compile_model.py` "needs no spelling change" and registers `compile_is_current`
as a consumer whose `__doc__` the guard will require to carry the full canonical
path. These two statements contradict. On the normalized tree (WI1/WI2 do not
touch `compile_model.py`), the `compiled_matches_drafts` registry row's
consumer-cross-reference assertion **reds on `compile_is_current`**, so WI3's
positive case fails `make all` — a green-after failure baked into the plan,
exactly the class round-1 pre-mortem #2 warned about, reintroduced through the
registry.

The other three compile-family consumers are fine:

- `done_predicate.compile_consistent` carries the canonical path at lines
  224/234 (inside its docstring) — passes.
- `disk_evidence._check_compiled_matches_drafts` carries it at lines 197/209 —
  passes.
- `_compile.check_compiled` carries it after WI1 (lines 175/186 → canonical) —
  passes.

Only `compile_is_current` is the offender.

**Fix required — choose one and record it in the Decision Log:**
(a) Add a WI (or fold into WI1's scope) that normalizes `compile_is_current`'s
   bare `:func:\`compiled_matches_drafts\`` reference to the canonical
   defining-module path, so the registered consumer satisfies the guard; or
(b) Drop `compile_is_current` from the consumer set with a recorded rationale
   (it is sibling-internal to the authoritative module and uses an intra-module
   relative reference, arguably not a "cross-module consumer"). If dropped, the
   developers'-guide convention (WI4) and the guard registry must agree on the
   carve-out so a future reader is not surprised.
Whichever is chosen, the negative-fixture set should include a *bare-relative*
reference case so the chosen rule's treatment of intra-module relative refs is
pinned, not incidental.

### 🔴 R2-B2 (Telefono / Doggylump) — the "no bare re-export tail" recipe is built on a false substring premise

WI3 step 2 (consumer assertion #3) and the Interfaces helper specify the
"no bare re-export" check as:

> "every occurrence of the re-export tail (`state.compiled_matches_drafts`) is
> immediately preceded by `compile_model.` … Equivalent formulation: the count
> of the re-export tail equals the count of the canonical path."

Both formulations are **false against the actual strings**. The re-export tail
`state.compiled_matches_drafts` is *not* a substring of the canonical path
`novel_ralph_skill.state.compile_model.compiled_matches_drafts` (the canonical
contains `state.compile_model.compiled_matches_drafts`). Verified:

```console
canonical contains tail as substring? False     # state.compiled_matches_drafts not in canonical
reconcile canonical contains tail?     False
```

Consequences:

- "every occurrence of the tail is immediately preceded by `compile_model.`" is
  incoherent: on the normalized tree the tail substring `state.compiled_matches_drafts`
  occurs **zero** times (the canonical spelling does not contain it), so there is
  nothing to be "preceded." An implementer coding this literally either writes a
  vacuously-true check or, worse, mis-derives a prefix test that never matches.
- "count of re-export tail == count of canonical path" is **false** on the
  intended green state: tail count = 0, canonical count ≥ 1. An implementer who
  asserts equality here reds the passing tree.
- The plan even instructs pinning this with "its own unit assertion against both
  spellings" — that unit assertion would be authored against a premise that does
  not hold, so it cannot do what the plan claims.

The *intent* (no bare re-export spelling survives in any consumer `__doc__`) is
correct and trivially implementable; the *stated recipe* is internally
inconsistent and must not be handed to the implementer as written.

**Fix required:** restate the check as the simple, correct invariant — for each
consumer `__doc__`, the bare re-export tail substring count is **zero** (i.e.
`state.compiled_matches_drafts` does not appear), since after normalization every
reference is the canonical `state.compile_model.compiled_matches_drafts`. Drop
the false "preceded by"/"equal counts" framing entirely. If the planner wants a
belt-and-braces check that the canonical form is present *and* the bare form is
absent, state those as two independent assertions, not as a count-equality that
the strings do not satisfy. Re-pin the tail-discriminator unit test against the
two spellings using the corrected rule.

## Advisory findings

### 🟢 R2-A1 (Pandalump) — make the "needs no spelling change" claim auditable

The plan asserts `done_predicate.py` and `disk_evidence.py` already carry the
canonical path and "need no spelling change (confirm with grep before editing)."
That is true today (verified: done_predicate 224/234; disk_evidence 197/209),
but the guard's correctness *depends* on it. Add an explicit pre-flight step in
Concrete steps that greps the canonical path inside each registered consumer's
docstring region and fails loudly if any is missing — turning the "confirm with
grep" aside into a gating check, so R2-B1's class of defect cannot recur silently
for the other rows.

### 🟢 R2-A2 (Dinolump) — table-marker assertion is sound but note the asymmetry

The compile-family table markers (`MATCHES`/`ABSENT`/`DIVERGES`) are asserted
ONLY of the authoritative symbol, which is correct — `compile_is_current` and
`check_compiled` both legitimately name all three members, so any "absent in
consumers" rule would be wrong. The plan already restricts markers to the
authoritative symbol; keep that and state in the guard docstring *why* markers
are authoritative-only (so a later maintainer does not "tighten" it into a
consumer check and re-red the tree).

## Pre-mortem (Doggylump)

1. **Most likely failure:** implementer authors WI3's registry verbatim,
   `make all` reds on the `compiled_matches_drafts` row because
   `compile_is_current`'s docstring lacks the canonical path, and they burn the
   Tolerance attempts deciding whether to edit `compile_model.py` (which the plan
   forbade) or drop the consumer (which the plan did not sanction) — an
   unplanned mid-stream decision the plan should have made. *Prevention:* fix
   R2-B1 — decide edit-or-drop for `compile_is_current` up front.
2. **Second failure:** implementer codes the "no bare re-export" check as the
   "counts equal" / "preceded by `compile_model.`" recipe, the assertion is
   vacuous or reds the green tree, and the guard ships either toothless (never
   catches a real re-export) or broken. *Prevention:* fix R2-B2 — restate as
   "tail substring count is zero" and re-pin the unit test.
3. **Third failure:** a future §7.1 task (e.g. 7.1.5) adds a registry row whose
   consumer uses an intra-module relative reference like `compile_is_current`
   does, and reds the suite — because the convention WI4 documents never settled
   how relative refs are treated. *Prevention:* settle R2-B1(b)'s
   relative-reference rule and document it in WI4.

## Alternatives checkpoint (Wafflecat)

The cross-reference-only design adopted in round 2 is the right structural
choice; no stronger alternative exists for this doc-and-test task. The remaining
question is purely the *scope of the consumer set*: include `compile_is_current`
(and normalize its relative ref to canonical) versus exclude it as
intra-module. Including-and-normalizing is marginally stronger (one more pinned
cross-reference) and keeps the registry uniform; excluding is less churn but
needs a documented carve-out. Either is viable; the plan must pick one rather
than leave the contradiction.

## Next steps (ordered)

1. (R2-B1) Decide edit-or-drop for `compile_model.compile_is_current` and make
   the registry, WI scope, and the "needs no spelling change" claim mutually
   consistent. If editing, add the normalization to a work item; if dropping,
   record the carve-out and reconcile WI4's convention text.
2. (R2-B2) Replace the "no bare re-export" recipe with the correct invariant —
   bare re-export tail substring count is zero per consumer `__doc__` — and drop
   the false "preceded by"/"equal counts" formulation; re-pin the
   tail-discriminator unit test against both spellings under the corrected
   rule.
3. (R2-A1) Promote the "confirm with grep" aside on the unedited consumers into
   a gating pre-flight check in Concrete steps.
4. (R2-A2) Document in the guard module docstring why table markers are asserted
   of the authoritative symbol only.

## Documentation & skills relied on

- ExecPlan under review: `docs/execplans/roadmap-7-1-6.md` (round-2 draft);
  prior `docs/execplans/roadmap-7-1-6.logisphere-review-r1.md`.
- Roadmap: `docs/roadmap.md` §7.1.6 (Requires 7.1.2/7.1.3/7.1.4; 7.1.5 still
  open) — verified the dependency and "apply to 7.1.5" wording.
- Source verified against:
  `novel_ralph_skill/commands/_compile.py` (8 re-export lines confirmed),
  `novel_ralph_skill/commands/novel_state.py` (`_render_reconciliation` line 136),
  `novel_ralph_skill/state/compile_model.py`
  (`compile_is_current` 90–119 — the R2-B1 offender; `compiled_matches_drafts`
  authoritative markers 132–174),
  `novel_ralph_skill/state/reconcile.py` (`reconciliation_payload` line 160),
  `novel_ralph_skill/state/done_predicate.py` (canonical path 224/234),
  `novel_ralph_skill/state/disk_evidence.py` (canonical path 197/209),
  `tests/test_developers_guide_contract_drift_guard.py` (the mirrored pattern —
  keys off the `Envelope` dataclass, no subprocess, confirmed),
  `docs/developers-guide.md` (drift-guard section at line ~1302),
  `Makefile` (`all = build check-fmt lint typecheck test`),
  `pyproject.toml` (`interrogate fail-under = 100`).
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- cuprum read-only sibling at `/data/leynos/Projects/cuprum`: not exercised — the
  no-subprocess/no-cuprum scoping is correct, so no cuprum claim required
  verification this round (confirmed `cuprum` is absent from the in-process unit
  guards).
