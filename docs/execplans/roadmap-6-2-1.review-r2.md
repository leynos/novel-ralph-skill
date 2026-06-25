# Logisphere adversarial design review — roadmap 6.2.1 (Round 2)

Verdict: **PROCEED WITH CONDITIONS** — the round-1 blocking defects (B1/B2/B3)
are genuinely fixed and every pinned per-phase *value* in the plan was
independently re-verified against the real commands driven in-process over the
real corpus. One blocking defect remains: a factually wrong *rationale* in the
`novel-done` ground-truth claim that the plan would propagate into a test
docstring, plus a latent corpus-coherence surprise the plan mis-explains.

Reviewed against real source (not the planner's summary): `_compile.py`,
`_novel_done.py`, `_desloppify.py`, `_wordcount.py`, `novel_state.py`,
`state/done_predicate.py`, `rulepack/detect.py`; `tests/corpus_fixtures.py`,
`tests/working_corpus/_library.py`, `tests/working_corpus/_builder.py`;
`tests/test_novel_done_snapshots.py`, `tests/test_compile_check_snapshots.py`,
`tests/test_contract_envelope_snapshots.py`; `tests/conftest.py`;
`pyproject.toml`; `Makefile`; `docs/novel-ralph-harness-design.md` §2.3/§9;
`docs/roadmap.md` 6.2.1. The full per-phase envelope was re-captured in-process
for all five commands (the same capture the plan documents in Surprises).

## Independent re-verification of the pinned table (the load-bearing claims)

Every pinned value reproduces exactly:

- novel-state check — exit 0, ok=True, violations==[] for all 11 phases. ✓
- novel-done — exit 1, ok=False for all 11 phases; `phase_is_done` True ONLY on
  `done`. ✓ (the most contestable claim — that even the `done` tree fails the
  full predicate — is correct.)
- wordcount — exit 0, ok=True; zero-progress branch for the 8 pre-drafting +
  `chapter-planning` phases (`chapters==[]`, cumulative as below);
  populated branch for drafting/final-pass/done (`current:68800`, all gates
  true, `next_gate_threshold:null`, `next_gate_distance:null`). ✓ exact.

  ```json
  {current:0, target:80000, percent_of_target:0.0, gate_triggered_*:false, next_gate_threshold:0.3, next_gate_distance:24000}
  ```

- novel-compile --check — three branches: exit 3/result={} (8 pre-drafting,
  empty manifest); exit 4/`diverged:true` (drafting, compiled absent); exit 0/
  `diverged:false` (final-pass/done). ✓ exact.
- desloppify — exit 0, ok=True, keys {pack,total_words,violations,findings},
  24 findings on every phase, violations==[], `total_words` 0 (8 pre-drafting)
  vs 68800 (3 drafting-era). ✓ exact. `findings` entries carry fixed regex
  `phrase` strings, `count:0`, `lines:[]` — deterministic, snapshots cleanly.

Locked-library / infra claims also verified in-repo (no firecrawl needed, the
repo pins them): `timeout = 30` global (`pyproject.toml:326`),
`pytest-timeout` and `pytest-xdist` locked, `**/test_*.py` per-file-ignores
cover S101/PLR2004, all `make` targets exist
(`all check-fmt lint typecheck test audit markdownlint nixie`), syrupy
one-snapshot-per-parametrised-case proven by
`test_contract_envelope_snapshots.py`, conftest re-exports spec types under
`TYPE_CHECKING`. The B1 trap is real and correctly handled:
`_compile.build_app` default writes `compiled.md`; only `["--check"]` reaches
`check_compiled`.

## Blocking defect

### B4 — the `novel-done` ground-truth rationale is wrong, and the plan would copy it into a test docstring

Surprises (lines 234-236) states the `done` tree fails the full predicate
because "`compile_consistent` is False for the eight pre-drafting + drafting
phases and the `done` tree still fails at least one clause", and WI3 (lines
536-538) instructs the implementer to write a docstring saying the aggregate
`ok` is constant-false "because the corpus never satisfies the *full*
predicate".

Captured reality for the `done` tree:

```text
result = {"phase_is_done": true, "final_pass_complete": true,
          "all_chapters_flagged": true, "knitting_gates_passed": false,
          "compile_consistent": true, "no_unresolved_blockers": true}
messages = ["knitting_gates_passed is false"]
```

So on the `done` tree `compile_consistent` is **True**; the sole failing clause
is **`knitting_gates_passed`**, not `compile_consistent`. The plan's stated
reason is incorrect. The pinned *assertions* (exit 1 / ok=False everywhere;
`phase_is_done` True only on `done`) still hold, so the tests pass — but the
plan asserts of itself that "every load-bearing per-phase envelope was captured
from the real commands … No cell is left to be decided", and this rationale
was plainly not captured: it is the same assumption-class error round 1 caught
(B1/B2/B3). An implementer following WI3 verbatim writes a misleading docstring.

This also surfaces a latent corpus surprise the plan must record, not paper
over: the corpus `done` spec sets `done_30/done_50/done_80 = True` (via
`_crossed_gates()`, `corpus_fixtures.py`) yet `knitting_gates_passed` evaluates
**False** on disk. The "coherent `done`" tree does not satisfy the done
predicate's knitting-gate clause. That is either an intended carried property
(the corpus `done` state is "phase=done but predicate-incomplete") or a corpus
defect — but it is load-bearing for any reader of this matrix and is currently
mis-explained. The plan must (a) correct the failing-clause attribution in
Surprises and WI3, and (b) record the `done_NN==True` but
`knitting_gates_passed==False` fact as an explicit Surprise so the next agent
does not re-trip it.

Fix: replace "`compile_consistent` is False … the `done` tree still fails at
least one clause" with the verified statement — pre-drafting/drafting phases
fail on the absent/stale compile and unmet drafting clauses; the `done` tree's
sole failing clause is `knitting_gates_passed` (message
`"knitting_gates_passed is false"`); and add the `done_NN`-vs-clause Surprise.
Align the WI3 docstring guidance accordingly.

## Advisory (non-blocking)

- A1 (Telefono) — drive-helper chdir contract. The plan's `_drive` helper is
  said to "chdir to `working.parent`", citing `_drive_check` as its model. But
  `_drive_check` does **not** chdir; the established in-repo pattern does the
  chdir in the test body via `monkeypatch.chdir` (`_run_capture` in
  `test_novel_done_snapshots.py`; the compile snapshot tests). Under
  `pytest-xdist` a bare `os.chdir` inside a helper leaks cwd across tests in
  the same worker. Specify that the chdir uses `monkeypatch.chdir`
  (auto-reverted) or a restoring context manager, not a bare `os.chdir`, so the
  cited model and the isolation guarantee actually match.

- A2 (Pandalump) — capture stdout via the repo convention. The in-repo drivers
  capture with the `capsys` fixture (or `redirect_stdout`); the plan says the
  helper "captures stdout" without pinning which. Either is fine, but name it
  so the helper does not silently diverge from the cited models.

- A3 (Buzzy Bee) — line budget. Re-verified the count is tight: 7 test
  functions + drive helper + registry + volatile guard + module/carried-gap
  docstrings, excluding `.ambr`. The 600-line / 6-file tolerance and the WI4
  dry-count checkpoint are sound; no change needed, but the carried-gap doc is
  the correct first thing to trim if it trips (already specified).

- A4 (Doggylump) — WI2 compile exit-3 human cell. The plan correctly notes
  `_drive` must treat the pre-drafting compile cells as `SystemExit` code 3
  with a non-empty human body and assert presence, not exit 0. Verified: the
  human renderer emits the error envelope and exits 3. Good — keep that
  explicit.

- A5 (Dinolump) — design-boundary conformance. The task adds tests only over the
  deterministic spine (ADR-001), exercises the established envelope contract
  (ADR-003), and the read-surface scoping (queries only; mutators carried as
  documented gaps, §3.3) is consistent with the deterministic/judgemental
  boundary. No boundary violation. The plan's "no production code change /
  escalate on any `novel_ralph_skill/` edit" constraint is the right guard.

## Pre-mortem

Six months on, the matrix merged and stayed green, but a corpus maintainer
"fixed" the `done` tree so `knitting_gates_passed` finally passes (making the
`done` predicate hold). `novel-done` on `done` now exits 0 / ok=True. The
machine-envelope matrix's `ok`-sign assertion for the `done` cell flips and the
snapshot churns — caught loudly, which is correct. But the WI3 docstring still
says the failure is `compile_consistent`, so the triaging engineer wastes time
looking at the wrong clause. Prevention designable now: fix B4 so the recorded
rationale names the real clause and records the `done_NN`-vs-clause fact, so
the next reader understands why the corpus `done` tree fails and what a corpus
change would do to this cell.

## Strongest alternative (Wafflecat)

The round-1 alternative (split the read surface by phase-sensitivity rather
than asserting a single false "eleven-phase invariant") has been adopted and is
the right shape. The remaining alternative worth one sentence: rather than
re-capture the envelope only in the plan prose, the implementer could add a tiny
`# ground-truth` assertion in WI3/WI4 that names the failing clause per phase
(`assert result_failing_clause(done) == "knitting_gates_passed"`), so the
rationale is enforced in code, not just asserted in a docstring that can drift.
Trade-off: a few more lines against the 600 budget, bought back by making the
B4-class error impossible to reintroduce silently. Optional, not required.

## Conditions to clear before implementation

1. (B4) Correct the `novel-done` failing-clause attribution in Surprises and in
   the WI3 docstring guidance: the `done` tree fails on `knitting_gates_passed`
   (message `"knitting_gates_passed is false"`), not `compile_consistent`
   (which is True on the `done` tree).
2. (B4) Add a Surprise recording that the corpus `done` spec sets
   `done_30/50/80=True` yet `knitting_gates_passed` evaluates False on disk, so
   the `done` tree is "phase=done but predicate-incomplete" — flag whether that
   is intended or a corpus question to escalate.
3. (A1/A2) Pin the `_drive` helper's chdir to `monkeypatch.chdir` (or a
   restoring context manager) and name the stdout-capture mechanism, so the
   helper matches its cited in-repo models and stays xdist-safe.
