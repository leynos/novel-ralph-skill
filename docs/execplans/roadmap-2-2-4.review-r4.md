# Logisphere design review — roadmap 2.2.4 ExecPlan, round 4

Verdict: **PROCEED** (satisfied=true). All five prior blocking defects
(B1/B2/B3/B4/B5) are genuinely resolved and re-verified against real source. No
new blocking defect found. The plan is implementable and design-conformant as
written.

This review read the plan from disk and re-derived every load-bearing claim
from the actual source under the worktree (and the locked wheels via `uv run`),
rather than trusting the planner's prose or the prior rounds.

## Independently verified against real source

- **B5 — the round-4 fix is correct and necessary (verified live).**
  `str(cyclopts.ValidationError(msg="..."))` raises `NotImplementedError` under
  locked Cyclopts 4.18.0 (`uv run`), and `runner.run`
  (`novel_ralph_skill/contract/runner.py:223-250`) has **no** generic
  `except Exception` after the `CycloptsError`/`StateInputError` arms, so the
  crash would propagate uncaught. The replacement pattern is real:
  `DesloppifyUsageError(EnvelopeMessagesError)` (`_desloppify.py:68`) +
  `_scan_or_usage` (`_desloppify.py:314-345`) returns
  `CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)])`
  directly. `EnvelopeMessagesError` is at `contract/errors.py:20`;
  `ExitCode.USAGE_ERROR == 2` at `contract/exit_codes.py`. The plan copies this
  shape verbatim.
- **Gate-ratio invariant (D4, Constraint).**
  `validate.py:_check_gate_ratio_consistent`
  (lines 250-278) uses `sum(by_chapter.values()) / target`, binds all three
  knitting gates via `zip(flags, GATE_THRESHOLDS)`, and short-circuits on
  `target <= 0`. The plan's account — including the deliberate `by_chapter` (not
  `current`) decoupling and the "do not fix the doc into the code" Constraint
  — is exact.
- **set_cursor vs advance_phase skeleton (D4).** `set_cursor`
  (`_state_mutators.py:176-234`) calls `_refuse_if_incoherent` on the
  **proposed** state only (line 224); `advance_phase` refuses **both** prior
  (306) and proposed (314). The repair-mutator framing (no prior-refusal) is
  correct.
- **On-disk `pass` key (WI4).** `parse.py:123` reads `raw["pass"]` into
  `pass_number`; `initial.py:97` writes `critic["pass"] = 1`. Editing
  `document["drafting"]["critic"]["pass"]` is right; the `pass_number`
  end-to-end naming + `Parameter(name="--pass")` was verified live to bind
  `pass_number == 2`.
- **Cyclopts surface (verified live).** No-flag `set-gate` parses to all-`None`
  (so the body must detect it — the adapter does); `--knitting-30`/
  `--no-knitting-30` negation works; `--pass x` raises `CoercionError` (exit 2).
- **cuprum 0.1.0 locked (verified live).**
  `SafeCmd.run_sync(*, capture=True, echo=False, context=None)`; the existing
  `test_set_chapters_e2e.py:107-109` uses the
  `run_sync(context=..., capture=True)` form the plan reuses. The local
  `/data/leynos/Projects/cuprum` checkout's `output=` form is correctly avoided
  (Surprise S1).
- **Single-file no-receipt stance (D3) is design-conformant.** developers-guide
  §"Checker/mutator segregation" (lines 362-381): the single-file mutators
  `set-cursor`/`advance-phase`/`recount` write one `Path.replace` and append
  **no** `log.md` receipt; `init` is the lone single-file-style mutator that
  writes `log.md` too. The roadmap's "log-receipt discipline" wording is
  generic and does not bind single-file mutators. The plan's A5 reconciliation
  note (name `init` as the exception) is the right defensive move. This is
  **not** a defect.
- **Line counts.** `wc -l`: novel_state.py = 399,_state_mutators.py = 325,
  _desloppify.py = 382. The B4 registrar resolution (D11) is sound: the two
  functional lines take novel_state.py to 401, and the module docstring (1-40)
  plus the `build_app` docstring have ample headroom to condense >=4 lines. The
  plan makes `wc -l <= 399` a named WI5 acceptance gate with an escalation path
  — honest.
- **Fixture construction (D8).** `build_working_tree` (`_builder.py:211`) does
  no
  validation, so the **incoherent** `gate_lags_ratio` prior is constructible;
  `WorkingTreeSpec` exposes `done_30/50/80`, `final_pass_complete`, per-chapter
  `draft_words`/`target_words` (`_specs.py:201-204`), and
  `_gate_true_below_threshold` (`_variants.py:80-96`) is the exact template
  cited. The anti-vacuity `event()`/`target` guard on the Hypothesis property
  is correctly specified.
- **ADR numbering.** ADRs 001-009 exist; ADR-010 is the next free number.

## Advisory (non-blocking) — for the implementer, not back to the planner

- **A-r4-1 (snapshot redaction).** WI1's syrupy snapshot asserts "no timestamps
  in
  this envelope". Confirm at implementation time that the write-shaped `result`/
  `messages` for `set-gate` carry no volatile field; if any appears, redact it.
  Low risk — the existing set-cursor success envelope has none.
- **A-r4-2 (xfail staging).** WI1-4 land bodies before WI5 registers them. The
  plan
  says to mark installed-e2e arms `xfail(strict=True)` or defer to WI5. Prefer
  defer-to-WI5 for the e2e arms (the in-process unit/property tests can call
  the body directly without registration), to avoid a stale strict-xfail that
  flips to XPASS the moment WI5 lands mid-series. Cosmetic; the plan already
  permits this.
- **A-r4-3 (registrar idempotence).** `register_gate_drafting_commands(app)` is
  called once from `build_app`. If any test calls `build_app()` twice against a
  shared app, double registration could raise. The existing per-call
  `make_contract_app` returns a fresh `App`, so this is not a live risk, but
  the surface-matrix test that calls the registrar directly should use a fresh
  `make_contract_app("novel-state")`, as WI5 already specifies.

## Pre-mortem (Doggylump)

The most likely six-months-on failure is **not** in this plan — it is the
standing risk the plan already names: an implementer writing the `set-gate`
happy path against a coherent baseline, finding the gate already true, and
silently weakening the test to a no-op (round-1 signal 1). The plan defuses
this structurally: D4 + D8 forbid `COHERENT_BASELINE`, name the three fixtures,
write the refusal test first, and require an observable flip via `event()`/
`target`. The second scenario — the no-flag exit-2 path crashing in production
— is the B5 defect, now closed by a real-runner / installed-binary envelope
assertion (not subclass-hood). Both have designed-in prevention.

## Alternatives checkpoint (Wafflecat)

The strongest alternative — four zero-argument `complete-knitting-NN` verbs
instead of one multi-flag `set-gate` — is recorded and reasoned away in D10:
the roadmap names `set-gate` explicitly, and the repair semantics (D4) plus
fixture recipe (D8) remove the no-op ambiguity that motivated the alternative.
The false-direction `--no-knitting-NN` is retained for symmetry only (never a
"turn a gate off" operation) and tested for its refusal arm. This is a
calibrated, auditable choice, not anchoring.

## Bottom line

This plan is implementable and design-conformant as written. The work items are
atomic, ordered (red→green per item, registration gated to WI5), testable
(unit, property, and bdd/e2e per mutator, refusal pinned first), and complete.
Validation is specified (`make all` per item; `markdownlint`/`nixie` for docs).
Nothing contradicts the deterministic/judgemental boundary (ADR-001) or the
exit-2/exit-3 contract (ADR-003). PROCEED.
