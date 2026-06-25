# Logisphere adversarial design review — roadmap 6.2.1 (Round 3)

Verdict: **REVISE** — the round-2 blocking defect (B4) and the A1/A2
drive-helper advisories are genuinely and correctly fixed, and every pinned
per-phase value (including the contestable `done`-tree clause set) was
independently re-captured in-process and reproduces exactly. But the
adversarial pass surfaced one *new* blocking defect of the **identical class**
as B4: the per-band failing-clause rationale the plan instructs the implementer
to bake into the Work item 3 docstring mis-attributes a clause for the
pre-drafting band, contradicting the verified envelope. The plan's own framing
("name the real failing clause per band so it cannot drift") makes this
load-bearing.

Reviewed against real source (not the planner's summary), re-capturing the full
per-phase envelope in-process over the real corpus for all five read commands:
`novel_ralph_skill/state/done_predicate.py` (lines 180-210),
`novel_ralph_skill/commands/_compile.py` (lines 76-95, 163, 239),
`_novel_done.py`, `_desloppify.py`, `_wordcount.py`, `novel_state.py`;
`tests/working_corpus/_library.py` (lines 55-118),
`tests/working_corpus/_builder.py` (lines 188-203),
`tests/working_corpus/_specs.py` (line 200),
`tests/test_novel_done_snapshots.py` (lines 44-118); `tests/conftest.py`;
`pyproject.toml` (line 97 per-file-ignores, line 326 `timeout = 30`);
`Makefile` (lines 28, 87-115); `docs/novel-ralph-harness-design.md` §2.3 (lines
125-129) / §9 (lines 811-821).

## Independent re-verification of the pinned table (load-bearing claims)

Captured in-process via `run(build_app(), argv, RunContext(..., human=False))`
over `wc.build_working_tree(wc.PHASE_STATES[phase], dest)` for every phase. All
reproduce exactly:

- novel-state check — exit 0, ok=True, violations==[] for all 11 phases. ✓
- novel-done — exit 1, ok=False for all 11; `phase_is_done` True ONLY on
  `done`. ✓
- wordcount — exit 0; zero-progress branch (`chapters==[]`, cumulative as
  below) for the 8 pre-drafting + `chapter-planning`; populated branch (3 rows,
  current 68800, all gates True, `next_gate_threshold:null`) for
  drafting/final-pass/done. ✓ exact.

  ```json
  {current:0, target:80000, percent_of_target:0.0,
   gate_triggered_*:false, next_gate_threshold:0.3, next_gate_distance:24000}
  ```

- novel-compile --check — exit 3/result={} (8 pre-drafting); exit 4/
  `diverged:true`
  (drafting); exit 0/`diverged:false` (final-pass/done). ✓ exact. Exit-3 message
  `"cannot compile: chapter manifest is absent or empty"` matches
  `_compile.py:95`. ✓
- desloppify — exit 0, ok=True, keys {findings,pack,total_words,violations}, 24
  findings every phase, violations==[], total_words 0 vs 68800. ✓ exact.

**B4 resolution confirmed.** The `done` tree's `novel-done` result re-captured
verbatim:

```json
{"phase_is_done": true, "final_pass_complete": true,
 "all_chapters_flagged": true, "knitting_gates_passed": false,
 "compile_consistent": true, "no_unresolved_blockers": true}
```

with `messages == ["knitting_gates_passed is false"]`. So `compile_consistent` is
**True** on `done`; the sole failing clause is **`knitting_gates_passed`** —
the plan now states this correctly in Surprises and WI3, and additionally pins
`result["knitting_gates_passed"] is False`,
`result["compile_consistent"] is True`, and the message in code. Root cause
verified in source: `knitting_gates_passed` (`done_predicate.py` lines 191-210)
requires both the three gate booleans **and** the three
`reviews/knitting-NN.md` files; the `done` spec leaves `knitting_reviews=()`
(`_specs.py:200`) so `_write_reviews` writes no `reviews/` dir
(`_builder.py:196`). The dedicated Surprise records this accurately. ✓

**A1/A2 resolution confirmed.** The `_drive` helper is now modelled on
`test_novel_done_snapshots.py::_run_capture` (lines 56-71), which does
`monkeypatch.chdir(working.parent)` and captures via `capsys.readouterr().out`.
The plan's correction that the *compile* suite chdirs in its test bodies (not in
`_drive_check`) matches source. xdist-safe. ✓

Infra claims verified in-repo (no firecrawl needed; the repo pins them):
`timeout = 30` (`pyproject.toml:326`), `**/test_*.py` per-file-ignores cover
S101/PLR2004 (`pyproject.toml:97`), all make targets exist (`make all` is
`build check-fmt lint typecheck test`; `audit`/`markdownlint`/`nixie` are
separate targets the plan invokes explicitly — consistent). No cuprum API is
relied on (in-process drive only); the cuprum deferral to 6.2.4 is correct. ✓

## Blocking defect

### B5 — pre-drafting failing-clause attribution is wrong (B4-class error, residual)

The plan instructs the WI3 implementer to write a docstring naming the real
failing clause **per band** "so it cannot drift" (line 622), and Surprises
asserts the same per-band rationale. For the pre-drafting band it states:

- Surprises lines 240-243: "the eight pre-drafting phases … have an empty
  manifest, so **`all_chapters_flagged`**, `compile_consistent` … and the
  drafting clauses are unmet";
- WI3 lines 622-624: "the eight pre-drafting phases fail on the empty manifest
  (**`all_chapters_flagged`**, `compile_consistent`, and the drafting clauses
  unmet)".

Captured reality (verbatim, driven in-process) for `premise` and
`chapter-planning`:

```json
{"phase_is_done": false, "final_pass_complete": false,
 "all_chapters_flagged": true, "knitting_gates_passed": false,
 "compile_consistent": false, "no_unresolved_blockers": true}
```

So on the pre-drafting trees **`all_chapters_flagged` is `True`**, not a
failing clause. It holds **vacuously** over the empty manifest —
`done_predicate.py` line 182 states explicitly: "An empty manifest holds
vacuously" (`all(... for chapter in state.chapters)` over `chapters==()` is
`True`). The actual failing clauses for the pre-drafting band are
`phase_is_done`, `final_pass_complete`, `knitting_gates_passed`, and
`compile_consistent` (confirmed by the captured `messages`):

```json
["phase_is_done is false", "final_pass_complete is false",
 "knitting_gates_passed is false",
 "compile_consistent is false (compiled.md missing)"]
```

`all_chapters_flagged` is `False` **only** on the `drafting` tree (3-chapter
manifest, last chapter unflagged) — and the plan *correctly* names it there
(line 624). The error is solely the pre-drafting attribution. This is the exact
same class of defect as B4: a per-band failing-clause rationale baked into
docstring guidance that contradicts the verified envelope. The round-3 revision
corrected the `done` band but left the equivalent error in the pre-drafting
band.

Why blocking, not advisory: the plan elevates the per-band rationale to a
load-bearing, drift-resistant artefact ("name the real failing clause per band
so it cannot drift", line 622) and asserts of itself (line 50) that "every
load-bearing per-phase envelope was captured from the real commands … No cell
is left to be decided". An implementer following WI3 verbatim writes a
misleading docstring claiming `all_chapters_flagged` fails on pre-drafting,
when it passes — the precise mistake round 2 demanded be eliminated. The pinned
code *assertions* still pass (WI3 asserts only `phase_is_done` per phase plus
the `done`-cell clauses), so the suite is green and the error hides in prose,
exactly as B4 did.

Fix: in Surprises (lines 240-243) and WI3 (lines 622-624), state the verified
pre-drafting failing clauses — `phase_is_done`, `final_pass_complete`,
`knitting_gates_passed`, `compile_consistent` (`compiled.md` missing) — and
note that `all_chapters_flagged` **holds vacuously** over the empty manifest
(`done_predicate.py` line 182), so it is *not* a pre-drafting failure. Keep the
correct `drafting`-band attribution (`all_chapters_flagged` False there). To
make this B-class error impossible to reintroduce silently — the round-2
Wafflecat alternative, here worth taking — add a code assertion pinning the
pre-drafting clause set (e.g. for one pre-drafting cell assert
`result["all_chapters_flagged"] is True` and
`result["compile_consistent"] is False`), so the rationale is enforced in code,
not only a docstring that can drift.

## Advisory (non-blocking)

- A1 (Telefono) — the `done`-cell code assertions (WI3) pin
  `knitting_gates_passed is False`, `compile_consistent is True`, and the
  message. Symmetry argues for the same treatment on the pre-drafting band (see
  B5 fix): one extra `assert` buys back the whole "rationale can drift" risk
  class. Folding this into B5 closes the door for good.

- A2 (Buzzy Bee) — line budget re-checked: 7 test functions + `_drive` helper +
  registry + volatile guard + module/carried-gap docstrings, `.ambr` excluded.
  Tight but within the 600-line / 6-file tolerance; the WI4 dry-count
  checkpoint and the "trim the carried-gap doc first" fallback are sound. The
  B5 fix adds ~2-4 lines (one assertion + corrected prose) — negligible against
  the budget.

- A3 (Pandalump) — registry/seam are correct: `["--check"]` for novel-compile
  (the B1 write-path trap is genuinely avoided), `["check"]` for novel-state,
  `[]` for the three single-default commands. The single-module decision and
  the read-surface-only scoping (mutators carried as documented gaps, §3.3) are
  structurally clean. No boundary leak.

- A4 (Doggylump) — WI2 exit-3 human cell verified: compile on a pre-drafting
  tree
  in human mode emits a non-empty body (shown below) and exits 3.

  ```text
  "command: novel-compile\nok: False\n… cannot compile: chapter manifest is absent or empty\n"
  ```

  The plan correctly says `_drive` catches this as SystemExit
  code 3 and WI2 asserts presence, not exit 0. ✓

- A5 (Dinolump) — design-boundary conformance holds: tests only, over the
  deterministic spine (ADR-001), exercising the established envelope contract
  (ADR-003); the "escalate on any `novel_ralph_skill/` edit" constraint is the
  right guard. No deterministic/judgemental boundary violation.

## Pre-mortem

Six months on, the matrix merged and stayed green. A corpus maintainer adds a
manifest to a pre-drafting phase fixture (e.g. populates `chapter-planning`).
`all_chapters_flagged` now genuinely depends on flags, and a triaging engineer
reads the WI3 docstring to understand why `novel-done` fails on that band — and
is sent to the wrong clause, because the docstring already claimed
`all_chapters_flagged` was the pre-drafting failure when it had in fact been
passing vacuously. Time wasted, exactly as the round-2 pre-mortem predicted for
the `done`/`compile_consistent` mix-up. Prevention designable now: fix B5 so
the recorded rationale names the real pre-drafting clauses and notes the
vacuous-truth behaviour, and pin a pre-drafting clause assertion in code.

## Strongest alternative (Wafflecat)

The split-by-phase-sensitivity structure (semantic eleven-phase cross-product
for done/wordcount/check; branch assertions for compile/desloppify) is adopted
and is the right shape — no structural alternative improves on it. The
remaining alternative is purely about *where the rationale lives*: stop
encoding per-band failing-clause rationale in prose at all, and instead assert
the full clause dict for one representative cell per band (pre-drafting,
drafting, done) directly in code. Trade-off: ~6 extra lines against the 600
budget, bought back by making the entire B4/B5 error class structurally
impossible — a docstring cannot mis-describe a clause set that the test itself
pins. Given two rounds have now tripped on exactly this, taking it is the
conservative call.

## Conditions to clear before implementation

1. (B5) Correct the **pre-drafting** failing-clause attribution in Surprises
   (lines 240-243) and WI3 (lines 622-624): the pre-drafting band fails on
   `phase_is_done`, `final_pass_complete`, `knitting_gates_passed`, and
   `compile_consistent` (`compiled.md` missing); `all_chapters_flagged` **holds
   vacuously** over the empty manifest (`done_predicate.py` line 182) and is
   NOT a pre-drafting failure. Preserve the correct `drafting`-band attribution.
2. (B5/A1) Pin the pre-drafting clause set in code for at least one pre-drafting
   cell (e.g. `result["all_chapters_flagged"] is True` and
   `result["compile_consistent"] is False`), mirroring the `done`-cell clause
   assertions, so the rationale is enforced in code rather than a drift-prone
   docstring.
