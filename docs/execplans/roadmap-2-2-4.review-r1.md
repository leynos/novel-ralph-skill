# Logisphere Design Review — roadmap 2.2.4 ExecPlan (Round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-4.md`.
Verdict: **REVISE**. The plan is structurally strong and its external-library
claims are verified, but the central `set-gate` happy path as written is not
reachable from a coherent prior, the named test baseline contradicts the plan's
own test recipe, and one stale fact and one code/text inconsistency must be
fixed before implementation.

## Verified-good (do not re-litigate)

- Cyclopts `bool | None = None` tri-state yields `--flag`/`--no-flag` and a
  default of "untouched" — verified live against locked Cyclopts 4.18.0.
- `set_critic_pass(*, pass_: int)` maps to `--pass`; non-integer →
  `CoercionError`
  → exit 2 — verified live.
- cuprum 0.1.0 `SafeCmd.run_sync(*, capture, echo, context)` — signature
  confirmed
  against the wheel `uv` resolves; the local `/data/leynos/Projects/cuprum`
  checkout has drifted (Surprise S1 is correct).
- Runner routing: `CycloptsError` → exit 2, `StateInputError` → exit 3
  (`contract/runner.py:225,233`). Correct.
- D3 (single-file mutators open no `[pending_turn]` and append no `log.md`
  receipt) is grounded: developers-guide §"Checker/mutator segregation" (lines
  362-381) states single-file mutators write one `Path.replace` and open no
  bracket; `set-cursor`/`advance-phase` write no receipt. The plan's escalation
  clause is the right hedge.
- D5/D6 (write-time preconditions in the body, not in `validate_state`) mirror
  `set-chapters`' `manifest_coherence_violations` precedent and ADR 008.

## BLOCKING

### B1 — `set-gate` happy path is unreachable from a coherent prior (structural)

`_check_gate_ratio_consistent` (`validate.py:250-278`) demands, for ALL three
knitting gates simultaneously, `flag == (drafted_ratio >= threshold)`.
Therefore any **coherent** prior already has each knitting gate at the value
the ratio mandates. From a coherent prior, `set-gate --knitting-30` is a
**no-op**: if the ratio has crossed 0.30, `done_30` is already `true`; if it
has not, flipping it `true` is refused. The plan's WI1 success narrative
("`set-gate --knitting-30` exits 0 and writes `done_30 = true`, follow-up
`check` exits 0") describes a state change that, from a coherent prior, never
changes the value. The only priors where the flip is both observable AND
validates are **incoherent** ones, which contradicts the plan's own operator
story (D4: "the operator flips the gate after the ratio crosses, which is
exactly when the set is coherent" — but at that moment a coherent prior already
has the gate true).

The plan must resolve what `set-gate` is *for*: (a) If it is the repair path
for an incoherent prior (gate lagging the ratio),
      say so explicitly, and note `set-cursor`'s pattern does NOT refuse an
      incoherent prior, so the happy path legitimately starts incoherent and ends
      coherent — and design the WI1 happy-path test on an incoherent→coherent
      transition, not a coherent→coherent no-op.
  (b) If it is meant to be idempotent (re-asserting an already-true gate, like
      `complete-final-pass`), say so, and drop the "writes done_30 = true"
      framing in favour of "re-asserts the coherent value".
Either way the plan currently mis-describes the only behaviour the validator
permits.

### B2 — Named test baseline contradicts the WI1 test recipe (testability)

WI1's unit test requires "a `drafting`-phase tree whose drafted ratio is
>= 0.30 but < 0.50". The only baseline the plan names,
>`PHASE_STATES["drafting"]`
(== `COHERENT_BASELINE`), has drafted total 24000+24000+20800 = 68800 / 80000 =
**0.86** with all three knitting gates already `true`
(`tests/working_corpus/_library.py:41-42,60-64,83-97`). No provided baseline
sits in `[0.30, 0.50)`. A sub-threshold spec is *constructible* via a custom
`WorkingTreeSpec` (low `draft_words`, explicit `done_30`/`done_50`/`done_80`),
but the plan gives no recipe and the corpus has no such fixture. Specify the
exact fixture construction (which `WorkingTreeSpec` fields produce the
ratio/gate combination each WI1 case needs), or the work item is not
implementable as written. The Hypothesis property in WI1 has the same gap: it
must generate the ratio AND set the gate triple to match — the plan does not
say how the strategy builds the underlying tree.

### B3 — Stale `_state_mutators.py` line count undermines the size argument

The plan's Constraint and Risk both assert `_state_mutators.py` is **245
lines**; it is actually **325 lines** (`wc -l`). The 400-line-cap argument for
a new module still holds (325 + four bodies would breach), so the conclusion
survives, but the load-bearing figure is wrong and must be corrected — an audit
gate that checks the plan against reality will fail on this. (`novel_state.py`
is 399, as stated.)

## ADVISORY

### A1 — Roadmap text vs D3 (log-receipt discipline)

Roadmap 2.2.4 says the new mutators carry "the same write-time validation,
atomic-write, **and log-receipt discipline** as the existing mutators." D3
reads "existing mutators" as the multi-file ones (`reconcile`/`set-chapters`)
and declines a receipt for these single-file mutators. The developers-guide
supports D3, and the plan escalates if review insists. This is defensible, but
it is a literal divergence from the roadmap success wording; the ADR 010 text
(WI6) should state the resolution explicitly so a future auditor does not read
it as an omission. Recommend a one-line note in the ADR: "single-file mutators
inherit the no-receipt stance of `set-cursor`/`advance-phase`; the roadmap's
receipt wording binds the multi-file mutators only (developers-guide
§segregation)."

### A2 — `pass_` vs `pass_number` parameter-name inconsistency

The Interfaces section declares `set_critic_pass(*, pass_number: int)`; the WI5
registration sketch declares `def set_critic_pass(*, pass_: int)`. Both target
the `--pass` CLI flag, but the registration wrapper would have to translate
`pass_` → `pass_number` when calling the body. Pick one parameter name end to
end and state the wrapper-to-body call explicitly.

### A3 — Design doc / state-layout say `current`, validator uses `by_chapter`

design §5.2 (line 528-529) and state-layout.md (line 197-198) describe the gate
ratio as `word_counts.current / word_counts.target`, but the validator
(`validate.py:263`) uses `sum(by_chapter.values())` (Decision Log B1). The plan
correctly tracks the validator ("drafted ratio"), so this is not a plan defect
— but the plan should add a one-line note that the design prose is stale on
this point so the implementer does not "fix" the validator to match the doc and
break the §5.2 contract. (Tolerance "Validator change" already forbids touching
it; make the reason explicit.)

### A4 — No-flag `set-gate` exit-code choice left open

WI1 leaves the no-flag-invocation exit code as exit 3 "default, confirm in
Decision Log if review prefers exit 2." A no-argument usage error is more
naturally the parser's exit 2 (usage) than the state channel's exit 3; but exit
3 is body-owned and consistent with the refusal channel. Resolve it in the
plan, do not defer it into implementation — it is a contract surface (ADR 003)
and an e2e assertion depends on it.

## Pre-mortem (Doggylump)

1. **Most likely failure:** the implementer writes the WI1 happy-path test
   against
   `COHERENT_BASELINE` (the only named tree), discovers `done_30` is already
   true, and either (a) silently weakens the assertion to a no-op, or (b)
   constructs an incoherent prior without realizing it has changed the
   contract's meaning. Both ship a `set-gate` whose behaviour nobody clearly
   specified. Mitigation: B1 + B2 force the prior's coherence status and the
   fixture recipe to be decided in the plan, before code.
2. **Blast radius:** contained to `set-gate`; the other three mutators are
   clean.
3. **Missed signal:** the property test passes vacuously if the strategy never
   generates a prior where the flag actually changes a value. Mitigation:
   require the WI1 property to assert at least one generated case performs an
   observable flip (a coverage/`event()` check), not only that "no
   contradiction is accepted".

## Strongest alternative (Wafflecat)

Drop `set-gate`'s general multi-flag form and ship only
`complete-knitting-30/50/80` convenience verbs plus `complete-final-pass` —
each a zero-argument idempotent "assert this gate's coherent value" mutator,
exactly parallel to `complete-final-pass`. This sidesteps B1 entirely: a
`complete-knitting-30` that runs the validate-before-persist pass simply
refuses (exit 3) until the ratio has crossed, then writes `true` idempotently,
and never needs the partial-update `bool | None` machinery or a sub-threshold
fixture. Trade-off: four verbs instead of one `set-gate`, no way to set a gate
`false` (but the design says gates only ever flip *to* true after a pass, so
the false direction is arguably not a real operation). This is meaningfully
simpler and removes the no-op/incoherent-prior ambiguity. The plan should at
least record why the general `set-gate` form was chosen over per-gate
completion verbs, given the validator makes a free-set impossible anyway.

## Trail followed

docs: roadmap.md (2.2.4), novel-ralph-harness-design.md §5.2/§5.4 (lines
524-530, 595-614), ADR 001/003/008, developers-guide.md §"Checker/mutator
segregation" (362-428), state-layout.md §Gates (195-202), AGENTS.md (400-line
cap, docstring coverage). source: validate.py:`_check_gate_ratio_consistent`,
GATE_THRESHOLDS;_state_mutators.py (set_cursor/advance_phase pattern, 325
lines); novel_state.py:build_app (registration); contract/runner.py (exit
mapping); schema.py (gate/drafting dataclasses);
tests/working_corpus/_library.py + _specs.py (baselines). cuprum READ-ONLY
sibling confirmed as drifted ahead of the locked 0.1.0 wheel. skills:
logisphere-design-review (this), leta/grepai for nav.
