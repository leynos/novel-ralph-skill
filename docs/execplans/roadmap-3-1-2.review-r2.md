# Logisphere design review — roadmap 3.1.2 ExecPlan (round 2)

Verdict: **PROCEED** (satisfied). Adversarial round-2 review against the locked
sources, the design doc, ADR-001/003, the roadmap, the developers' and users'
guides, and AGENTS.md. The round-1 blocking defect (B-1, the self-contradictory
carve-out predicate) is fully resolved, and all four round-1 advisories (A-1 …
A-4) are addressed in the plan text. Every load-bearing claim re-verified
against real source; no new blocking defect survives.

## Sources relied on

- ExecPlan read in full from disk: `docs/execplans/roadmap-3-1-2.md`.
- Round-1 review: `docs/execplans/roadmap-3-1-2.review-r1.md`.
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- Re-verified against real source this round (not the planner's summary):
  - `novel_ralph_skill/state/done_predicate.py` — `compile_consistent_exists`
    at `:211-220`; `evaluate_done` calls it at `:292`; `DoneClauses` carries six
    booleans only; `failed_clause_names` yields field names in design order and
    records **no** absent-vs-stale distinction (`:99-142`). Confirmed.
  - `novel_ralph_skill/state/disk_evidence.py:167-188` — detector byte-compares
    at `:183`; absent `compiled.md` → `None` (vacuously satisfied) at
    `:179-181`. Confirmed (opposite polarity to the clause).
  - `novel_ralph_skill/state/compile_model.py` — `present_draft_bodies`,
    `concatenate_drafts`, `DRAFT_SEPARATOR = "\n\n"`; absent draft → `""`, every
    other read fault propagates. Confirmed.
  - `novel_ralph_skill/commands/_novel_done.py` — `root = working_dir()` bound
    at the top of `_novel_done` (`:63`); current two-way `all_hold` →
    `SUCCESS`/`BENIGN_NEGATIVE` mapping; module docstring states "No 3.1.1 path
    produces exit 4". Confirmed.
  - `tests/working_corpus/_specs.py` — `compiled: str | None`; `_resolve_compiled`
    writes `COMPILED_AUTO` as the coherent concatenation and any other string
    verbatim; `draft_body(n)` emits header-free `"word word …"`. Confirmed
    (A-1 vacuity is real).
  - `tests/test_done_predicate.py:32, 135` — orphaned import and
    `test_compile_consistent_exists_present_and_absent` exist exactly as A-2
    describes. Confirmed.
  - `tests/test_novel_done_command.py:100-111`
    (`test_absent_compile_exits_one_not_zero`) — pins absent compile → exit 1.
    Confirmed (the test the conservative reading must keep green).
  - `tests/test_novel_done_snapshots.py` — the one-clause-fails snapshot uses
    `done_predicate_failer_tree("phase_is_done")` (`:111`), **not** a stale
    compile; the human-mode test uses the `compile_consistent` *absent* failer
    (`:130`). Confirmed: R-SNAPSHOT-CHURN reasoning holds; neither existing
    snapshot re-baselines.
  - `grep compile_consistent_exists` — callers are exactly `evaluate_done` and
    the two `test_done_predicate.py` sites. Confirmed: "no other caller" (A-2).
  - `docs/novel-ralph-harness-design.md` §2.3 (106-129) and §4.2 (302-361) —
    the carve-out fires "when every clause except `compile_consistent` is
    satisfied … the only obstacle is a **stale** `compiled.md`"; "compares
    content hashes". Confirmed: the conservative (absent ≠ stale) reading is the
    design-correct one, and the "hash" wording is a fidelity concept the
    detector already realizes as a byte compare.
  - `docs/roadmap.md:892-934` — 3.1.2 success criteria and the 3.1.3 boundary.
    Confirmed: 3.1.3 owns the cross-detector unification; 3.1.2 must not touch
    the §5.4 detector.
  - `pyproject.toml:8` — runtime is `cyclopts` + `tomlkit`; dev set carries
    `pytest`, `pytest-bdd`, `hypothesis`, `syrupy`, `pytest-timeout`,
    `pytest-xdist`. Confirmed: no new dependency.
  - `AGENTS.md` — 400-line module cap, en-GB Oxford spelling, `interrogate`
    docstring gate, `make all`. Confirmed.
  - cuprum locked source `/data/leynos/Projects/cuprum/cuprum/catalogue.py`,
    `program.py` — exist; "no external process / cuprum out of scope" is sound.

## Round-1 defect resolution

- **B-1 (RESOLVED).** The exit-4 carve-out predicate is now stated **identically**
  and **conservatively** in all four locations — D-CARVE (`:360-371`),
  R-CARVE-MISFIRE (`:238-241`), Work item 3 (`:669-671`), and the Interfaces
  section (`:944-955`):

  ```python
  clauses.failed_clause_names == ("compile_consistent",) and (
      root / "manuscript" / "compiled.md"
  ).exists()
  ```

  The contradictory pure-predicate phrasing is deleted. The **mechanism** — a
  read-only `compiled_path.exists()` stat in the command body, `root` already
  bound at `_novel_done.py:63` — is specified explicitly as the only way the
  body can tell *absent* (exit 1) from *stale-present* (exit 4), since
  `DoneClauses` / `failed_clause_names` carry only the six booleans. This
  preserves `test_absent_compile_exits_one_not_zero` (which the Tolerances
  freeze) and is ADR-001-safe (read-only). Implementable as written.
- **A-1 (ADDRESSED).** Work item 2 now states the "header count" half is vacuous
  under the header-free corpus and requires the implementer to either add a
  non-zero-header count-coincident spec (preferred) or state the vacuity plainly
  and lean on the word-total spec plus the Work-item-1 Hypothesis
  byte-perturbation property. Verified the vacuity claim against
  `_specs.py` `draft_body`.
- **A-2 (ADDRESSED).** Work item 1 now explicitly lists
  `test_compile_consistent_exists_present_and_absent` (`:135`) and its import
  (`:32`) for removal/rewrite, so the first commit does not go red on a dangling
  import. Verified both sites exist.
- **A-3 (ADDRESSED).** The "one shared routine" acceptance bullet now runs the
  clause-vs-detector equality test **only over present-compile trees** and pins
  the absent-compile trees separately (clause→False, detector→vacuous).
- **A-4 (ADDRESSED).** D-CARVE and Work items 3/4 now specify the absent
  sole-failure exit-1 message reports the compile is *missing* rather than
  *stale*, so human-mode output is not misleading at the carve-out boundary.

## Crew lens summary (round 2)

- **Pandalump (structure):** the engine/command split now carries the
  absent-vs-stale fact correctly — the engine stays at six booleans (seam
  frozen) and the command body supplies the one read-only stat. The 3.1.2/3.1.3
  boundary remains crisp; D-CLAUSE-FN keeps 3.1.3 a one-edit drop-in. No
  structural defect remains.
- **Wafflecat (alternatives):** the richer-engine-verdict alternative is rightly
  rejected (it widens the Tolerance-frozen `DoneClauses` seam and pre-empts
  3.1.3). The single read-only stat is the better-calibrated choice. A-1's
  residual corner is now disclosed rather than silently unproven.
- **Buzzy Bee (scaling/cost):** bounded-payload rule preserved (single boolean);
  comparison is O(total draft bytes) read once — the same cost the detector
  already pays. The extra `exists()` stat is negligible. No scaling concern.
- **Telefono (contracts):** envelope / `schema_version` / exit-code contract
  held; the carve-out is the one contract change and it is now consistent and
  design-conformant. D-BYTE-COMPARE (no `hashlib`) matches the detector at
  `disk_evidence.py:183` and avoids a second comparison mechanism — correct.
- **Doggylump (failure modes):** the pre-mortem's "regenerated a compile that
  never existed" path is closed by the conservative reading + the stat;
  undecodable `compiled.md` → exit 3 is pinned (R-FAULT-COMPILE); snapshot churn
  is verified absent. One non-blocking observation below.
- **Dinolump (viability):** read-only checker, no new deps, mainstream tooling,
  within module/line caps, TDD ordering, en-GB convention respected. No
  long-term concern.

## Residual non-blocking observations (advisory; not gating)

1. **TOCTOU between the engine read and the command stat (Doggylump).** The
   carve-out re-stats `compiled.md` after `evaluate_done` already read it. In a
   single-process, read-only checker with no concurrent writer during a
   `novel-done` run this is a non-issue, and the pathological race degrades
   **safely**: a compile deleted between the two reads yields exit 1 (benign),
   never a stale-compile lie. The plan's "read-only, re-running is safe"
   framing already covers it; an explicit one-line note in Work item 3 would be
   tidy but is not required.
2. **A-1 option choice.** Option 1 (a non-zero-header count-coincident spec) is
   the stronger discharge of the literal roadmap criterion; the implementer is
   permitted option 2 (state the vacuity) only when option 1 is
   disproportionate. Worth nudging the implementer toward option 1, but the plan
   already permits either and is honest about the trade — not gating.

## Pre-mortem (Doggylump, round 2)

The round-1 pre-mortem's three scenarios are all now mitigated in the plan text:
(1) regenerating a never-built compile — closed by the conservative reading +
the specified stat; (2) a stale compile slipping through on header structure —
covered by the Hypothesis byte-perturbation property plus the disclosed A-1
choice; (3) a red first commit from the orphaned import — closed by A-2's
explicit removal instruction. No new 03:00 scenario surfaced.

## Alternatives checkpoint (Wafflecat, round 2)

No credible structural alternative beats the plan's reuse-not-reinvent approach.
The engine-side richer-verdict alternative is correctly deferred to 3.1.3 (which
will unify the comparison anyway), so paying a single read-only stat in the
command body now is the right calibration. That the strongest alternative is a
deliberate deferral rather than a missed option is a strong signal the design is
on solid ground.

## Conclusion

This plan is implementable and design-conformant as
written. The work items are atomic, ordered (red→green→refactor), independently
committable, and `make all`-gated; validation is specified per item (unit,
property, behavioural, snapshot, e2e, plus markdownlint/nixie for docs); nothing
contradicts the deterministic/judgemental boundary (ADR-001 — the command writes
nothing, the stat is read-only) or the established contracts (ADR-003 — envelope,
`schema_version: 1`, six-boolean `result`, bounded payload). Proceed.
