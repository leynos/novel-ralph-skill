# Logisphere adversarial design review — roadmap 6.2.1 (Round 4)

Verdict: **PROCEED** — the sole round-3 blocking defect (B5, the pre-drafting
failing-clause mis-attribution) is comprehensively resolved in both prose and
code, and every load-bearing per-phase value was independently re-captured
in-process over the real corpus and reproduces exactly. No new blocking defect
surfaced. The plan is implementable and design-conformant as written.

## Independent re-verification (load-bearing claims, captured in-process)

Driven via `run(build_app(), argv, RunContext(..., human=False))` over
`wc.build_working_tree(wc.PHASE_STATES[phase], dest)` for every phase, parsing
the envelope. All reproduce exactly:

- `novel-done` clause booleans per band:
  - pre-drafting (premise…chapter-planning): `all_chapters_flagged` **True**
    (vacuous over empty manifest), `compile_consistent` False,
    `knitting_gates_passed` False, `phase_is_done` False;
  - `drafting`: `all_chapters_flagged` **False** (the only band where it
    genuinely fails), `compile_consistent` False;
  - `done`: `phase_is_done` True, `compile_consistent` **True**,
    `knitting_gates_passed` False.
  Pre-drafting `messages` verbatim: `["phase_is_done is false",
  "final_pass_complete is false", "knitting_gates_passed is false",
  "compile_consistent is false (compiled.md missing)"]`.
- `novel-compile --check`: exit 3/`{}` (8 pre-drafting); exit 4/`diverged:true`
  (drafting); exit 0/`diverged:false` (final-pass, done). Exact.
- `wordcount`: zero-progress branch (`chapters==[]`,
  `next_gate_threshold:0.3`, `next_gate_distance:24000`) for pre-drafting;
  populated branch (3 rows, current 68800, all gates True,
  `next_gate_threshold:null`) for drafting-era. Exact.
- `desloppify`: keys `{findings,pack,total_words,violations}`, 24 findings,
  `violations==[]`, `total_words` 0 vs 68800. Exact.
- `novel-state check`: exit 0, ok=True, `violations==[]` all phases. Exact.

Source confirmed: `done_predicate.py` line 182 ("An empty manifest holds
vacuously") for `all_chapters_flagged`; lines 191-210 for the
`knitting_gates_passed` booleans-and-files conjunction.

Infrastructure confirmed in-repo: `wc.PHASE_ORDER` is 11, and
`build_working_tree`/`PHASE_STATES`/`WorkingTreeSpec` all exist on the corpus
package; `test_*.py` per-file-ignores cover S101/PLR2004/PLR0913/PLR0917
(`pyproject.toml:97`); global `timeout = 30` (`pyproject.toml:326`); `make all`
= `build check-fmt lint typecheck test` (`Makefile:28`). No memory-based
locked-library claim remains: syrupy/xdist/timeout behaviour is pinned by
existing in-repo test modules, and cuprum is correctly deferred to 6.2.4
(in-process drive only, no cuprum API relied on).

## B5 resolution confirmed

The round-3 blocking defect was a docstring/Surprises mis-attribution naming
`all_chapters_flagged` as a pre-drafting failing clause when it holds vacuously
(True) over the empty manifest. Round 4 fixes it on three fronts:

1. Surprises (lines 254-265) now names the four real pre-drafting failing
   clauses and explicitly records that `all_chapters_flagged` is True/vacuous,
   with the `done_predicate.py:182` citation.
2. WI3 docstring guidance (lines 648-684) names the real pre-drafting clauses,
   explicitly forbids the `all_chapters_flagged` attribution ("that is the B5
   defect"), and preserves the correct `drafting`-band attribution.
3. The round-3 Wafflecat alternative is taken: per-band clause assertions are
   pinned **in code** — pre-drafting (`all_chapters_flagged is True` and
   `compile_consistent is False`), drafting (`all_chapters_flagged is False`),
   done (`knitting_gates_passed is False`, `compile_consistent is True`, plus
   the message). All three match the captured envelope. The B4/B5 error class
   is now structurally impossible to reintroduce silently.

Every remaining mention of `all_chapters_flagged` in the document was audited
and is consistent with the verified reality.

## Crew synthesis

- Pandalump (structure): registry/seam correct; single-module + read-surface
  scoping clean; no boundary leak. B5 fix strengthens structural integrity.
- Wafflecat (alternatives): the pin-in-code-per-band alternative is adopted; no
  better structural alternative exists.
- Buzzy Bee (scaling): 7 functions + helper + registry + guard + docstrings
  within the 600-line/6-file tolerance; WI4 dry-count checkpoint and trim
  fallback sound; the large `desloppify` `.ambr` is deterministic and flagged.
- Telefono (contracts): per-band clause assertions pin attribution in code; the
  envelope contract (ADR-003) is exercised, not re-defined.
- Doggylump (failure modes): WI2 exit-3 human cell handled (presence not exit
  0); every snapshot paired with a semantic assertion;
  escalate-on-corpus-change tolerances correct.
- Dinolump (viability): tests-only over the deterministic spine (ADR-001);
  en-GB throughout; no deterministic/judgemental boundary violation.

## Pre-mortem

The round-3 pre-mortem scenario (a maintainer populates a pre-drafting manifest
and a triaging engineer is sent to the wrong clause by a stale docstring) is
now prevented: the recorded rationale names the real clauses and the
vacuous-truth behaviour, and the pre-drafting clause set is pinned in code, so
a manifest change would flip the pinned `all_chapters_flagged` assertion loudly
rather than mislead silently. No new pre-mortem scenario identified.

## Conditions

None. The plan may proceed to implementation as written.
