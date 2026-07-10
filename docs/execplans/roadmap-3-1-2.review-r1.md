# Logisphere design review — roadmap 3.1.2 ExecPlan (round 1)

Verdict: **REVISE** (proceed-with-conditions blocked by one structural defect in
the carve-out predicate). Adversarial review against the locked sources, the
design doc, ADR-001/003, the roadmap, the developers' and users' guides, and
AGENTS.md. The plan is unusually rigorous and most of its load-bearing claims
verified against the real source; the blocking defects below are precise and
addressable.

## Sources relied on

- ExecPlan read in full from disk: `docs/execplans/roadmap-3-1-2.md`.
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- Verified against real source (not the planner's summary):
  - `novel_ralph_skill/state/compile_model.py` (`present_draft_bodies`,
    `concatenate_drafts`, `DRAFT_SEPARATOR`) — claims confirmed.
  - `novel_ralph_skill/state/disk_evidence.py:167-188`
    (`_check_compiled_matches_drafts`, byte compare at `:183`, absent→vacuous at
    `:180-181`) — confirmed.
  - `novel_ralph_skill/state/done_predicate.py` (`DoneClauses.all_hold`,
    `failed_clause_names`, `compile_consistent_exists:211-220`,
    `evaluate_done:259-294`) — confirmed.
  - `novel_ralph_skill/commands/_novel_done.py` (`_novel_done`, exit mapping)
    — confirmed.
  - `tests/working_corpus/_specs.py` (`compiled` field, `_resolve_compiled`,
    `COMPILED_AUTO`, `CORPUS_SEPARATOR`, `draft_body`) — confirmed.
  - `tests/working_corpus/_done_predicate_specs.py:140` — the existing
    `compile_consistent` failer uses `compiled=None` (absent).
  - `tests/test_novel_done_command.py:100-111`
    (`test_absent_compile_exits_one_not_zero`) — asserts absent compile → exit 1.
  - `docs/novel-ralph-harness-design.md` §2.3 (106-129), §4.2 (308-360).
  - `docs/roadmap.md` 892-934 (3.1.2 + 3.1.3).
  - `docs/users-guide.md` 305-335, `docs/developers-guide.md` 555-575.
  - cuprum locked source `/data/leynos/Projects/cuprum/cuprum/` exists; the
    "no external process / cuprum out of scope" claim is sound.

## Blocking defects (back to the planner)

### B-1 (Telefono / Pandalump) — the carve-out predicate is self-contradictory and, as chosen, not implementable from the specified engine output

The plan states the exit-4 carve-out predicate **two incompatible ways**:

- **D-CARVE** (lines 348-356) and the Risk R-CARVE-MISFIRE mitigation (lines
  231-236): the decision is *exactly* `clauses.failed_clause_names ==
  ("compile_consistent",)` → `ACTIONABLE_FINDING`. No existence check.
- **Work item 3** (lines 626-638) and the prescriptive **Interfaces** section
  (lines 847-850): exit 4 iff `compile_consistent` is the sole false clause
  **and** `compiled.md` *exists* (a stale present compile); an absent compile
  stays exit 1.

These are not the same predicate. The plan even argues itself from the first to
the second inside Work item 3 (lines 618-632), leaving both readings live in the
document. A planner must not ship two contradictory definitions of the one
behaviour the task exists to add.

This is not cosmetic. The **pure** D-CARVE predicate would *regress an existing,
named soundness test*: `tests/test_novel_done_command.py:100-111`
(`test_absent_compile_exits_one_not_zero`) pins an otherwise-complete tree with
an **absent** `compiled.md` to **exit 1** (the B1 fix). The existing
`compile_consistent` failer spec is `compiled=None`
(`_done_predicate_specs.py:140`), and `done_predicate.py:199`'s existing
assertion is `failed_clause_names == ("compile_consistent",)` for that absent
case. Under the pure D-CARVE predicate that tree maps to exit 4, breaking a test
the Tolerances forbid changing. So the conservative reading is **mandatory**, and
D-CARVE as written is wrong.

The conservative reading is also **not implementable from the engine output the
plan specifies**. `DoneClauses` / `failed_clause_names` carry only the six
booleans; they do *not* record whether `compile_consistent` is false because the
compile is *absent* or *stale-present* (verified: `done_predicate.py:90-142`).
The command body therefore cannot distinguish the two from `failed_clause_names`
alone. The plan's chosen predicate needs the command body to independently
`stat` `compiled.md` (`(root / "manuscript" / "compiled.md").exists()` — a
read-only op, ADR-001-safe, `root` is in scope at `_novel_done.py:63`), but **no
work item, no Interfaces clause, and no decision specifies this extra
filesystem read**. As written, Work item 3's implementation steps (replace the
two-way branch with a three-way branch keyed on `failed_clause_names`) cannot
realize the conservative predicate the same work item mandates.

Required fix: pick one predicate (the conservative reading is the design-correct
one — design §4.2 lines 321-328 keys the carve-out on "the only obstacle is a
**stale** `compiled.md`", which an absent compile is not), make D-CARVE state it,
delete the contradictory pure-predicate phrasing from D-CARVE and
R-CARVE-MISFIRE, and **specify the mechanism**: either (a) the command body
re-stats `compiled.md` after `evaluate_done` and gates the carve-out on
`failed_clause_names == ("compile_consistent",) and compiled_path.exists()`, or
(b) the engine surfaces the absent-vs-stale distinction (heavier; likely out of
scope and risks the `DoneClauses` seam the Tolerances freeze). Option (a) is the
minimal, seam-preserving choice; whichever is chosen, it must be written into
Work item 3, the Interfaces section, and D-CARVE so they agree.

## Advisory (non-blocking) findings

### A-1 (Wafflecat / predicate-truthfulness) — the "header count" half of the success criterion is not exercised by the corpus

Roadmap success (line 906) and design §2.3 (line 121) name the property as: a
stale compile whose **header count and word total** coincidentally match is still
caught. The corpus `draft_body` (`_specs.py:222-231`) emits header-free bodies
(`"word word word"`). So every corpus draft has **zero** markdown headers, and
the plan's count-coincident stale spec (Work item 2) can only demonstrate
*word-total* coincidence; "header count" coincidence is trivially zero-equals-zero
on both sides and never genuinely stressed. The Hypothesis property (Work item 1)
does cover the general byte-divergence invariant, so this is not a soundness hole
— but the plan claims to pin the literal roadmap criterion and does not fully do
so. Either add a spec whose stale body and drafts both carry the same non-zero
count of `#`-prefixed lines, or state explicitly that "header count" is vacuous
under the header-free corpus and the word-total + byte-perturbation tests
discharge the criterion.

### A-2 (Pandalump / completeness) — removing `compile_consistent_exists` orphans a dedicated test the plan does not call out

D-CLAUSE-FN removes `compile_consistent_exists`. Verified it has exactly the
callers the plan claims (`done_predicate.py:292` + `test_done_predicate.py`). But
`test_done_predicate.py:135` (`test_compile_consistent_exists_present_and_absent`)
imports and exercises the removed function by name; Work item 1's test list does
not explicitly name it for removal/replacement. Obvious in implementation, but a
self-contained plan should list it so a novice does not leave a dangling import
and a red `make all`.

### A-3 (Telefono) — the "one shared routine" acceptance test is under-specified for divergent polarities

Validation (lines 767-770) asserts the clause's verdict equals the §5.4
detector's "on every corpus tree where their absent-file polarities agree
(present `compiled.md`)". Correct in spirit, but the plan should state that the
two are compared only over **present-compile** trees and that the absent-compile
trees are pinned *separately* (clause→False, detector→vacuously-satisfied), so
the equality test is not accidentally run over the one input where they are
*designed* to disagree. The R-EXISTENCE-REGRESS mitigation (lines 257-259) gestures
at this; make the acceptance bullet say it.

### A-4 (Doggylump) — messages prose for the absent-sole-failure exit-1 case is unspecified

With the conservative reading, an otherwise-complete tree with an *absent*
compile exits 1 with `compile_consistent` the sole failure. Work item 3 specifies
the exit-4 message ("stale compile; regenerate") and the generic exit-1 message,
but the absent-sole-failure case is an exit-1 path whose message would read
"compile_consistent is false" — which is correct but does not tell the operator
the compile is *missing* rather than *stale*. Non-blocking (the harness never
parses messages, ADR-003), but worth a line so human-mode output is not
misleading at the exact boundary the carve-out turns on.

## Crew lens summary

- **Pandalump (structure):** boundaries are sound; the 3.1.2/3.1.3 split is
  crisp and the single-named-function placement (D-CLAUSE-FN) genuinely keeps
  3.1.3 a one-edit drop-in. The one structural defect is B-1 (the engine/command
  layer split cannot carry the absent-vs-stale fact the chosen predicate needs).
- **Wafflecat (alternatives):** the strongest alternative — making the engine
  return a richer compile verdict (e.g. an enum: coherent / absent / stale) so
  the command body needs no extra stat — is rightly *rejected* here because it
  widens the `DoneClauses` seam the Tolerances freeze and pre-empts 3.1.3. The
  plan's reuse-not-reinvent stance is correct. A-1 is the residual unexplored
  corner (header-count coincidence).
- **Buzzy Bee (scaling/cost):** bounded-payload rule preserved (single boolean,
  no per-chapter content); the comparison is O(total draft bytes) read once, the
  same cost the detector already pays. No scaling concern. The byte comparison
  over large manuscripts is acceptable; no fan-out, no unbounded growth.
- **Telefono (contracts):** envelope/`schema_version`/exit-code contract held;
  the carve-out is the one contract change and it is the B-1 defect. D-BYTE-COMPARE
  (no `hashlib`) is the right contract call — it matches the detector at
  `disk_evidence.py:183` and avoids a second comparison mechanism.
- **Doggylump (failure modes):** fault boundary (D-FAULT) is faithfully the
  inherited one; undecodable `compiled.md` → exit 3 is pinned. R-FAULT-COMPILE,
  R-CARVE-MISFIRE, R-STALE-MISS, R-EXISTENCE-REGRESS, R-SNAPSHOT-CHURN are all
  real and mitigated. A-4 is the only operational nit.
- **Dinolump (viability):** read-only checker, no new deps, mainstream tooling,
  within module/line caps, TDD ordering, en-GB convention respected. Cognitive
  load is reasonable; the plan documents itself well. No long-term concern.

## Pre-mortem (Doggylump)

1. *Six months on, the harness regenerated a compile that never existed.* Cause:
   the pure D-CARVE predicate shipped and an absent-sole-failure tree exited 4,
   sending `novel-compile` to "regenerate" a compile against an incomplete or
   never-built manuscript. Prevented by B-1's conservative reading **with the
   stat** — which the plan must specify, not merely assert.
2. *A stale compile slipped through as done.* Cause: the corpus only ever
   exercised word-total coincidence and a real stale compile differed in header
   structure the test never modelled, masking an off-by-one in the join. Low
   likelihood (byte compare is total), but A-1 leaves the named criterion
   partly unproven.
3. *`make all` went red on the first commit.* Cause: removing
   `compile_consistent_exists` orphaned its import in `test_done_predicate.py`
   (A-2), which Work item 1 did not list. Cheap to prevent by naming it.

## Alternatives checkpoint (Wafflecat)

The credible alternative is engine-side: have `evaluate_done` (or a sibling)
return *why* `compile_consistent` is false so the command body needs no second
stat. It trades a wider, Tolerance-frozen `DoneClauses` seam and partial 3.1.3
pre-emption for a command body with no filesystem knowledge. Given 3.1.3 will
unify the comparison anyway, deferring the richer verdict and using a single
read-only stat in the command body (B-1 option a) is the better-calibrated
choice. No other structural alternative beats the plan's reuse approach.

## Recommended next steps (ordered)

1. Resolve **B-1**: choose the conservative carve-out, make D-CARVE /
   R-CARVE-MISFIRE / Work item 3 / Interfaces state it identically, and specify
   the command-body `compiled.md` stat (read-only) as the mechanism. (Blocking.)
2. Address **A-2**: list the orphaned `compile_consistent_exists` test for
   removal in Work item 1.
3. Address **A-1**: either add a non-zero-header count-coincident spec or state
   the header-count half is vacuous under the corpus.
4. Tighten **A-3** and **A-4** wording in Validation and Work item 3.
