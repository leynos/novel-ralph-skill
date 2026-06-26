# Logisphere Design Review — roadmap 2.3.7, Round 1

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-26.

Verdict: PROCEED WITH CONDITIONS. The plan is implementable and
design-conformant. Every source claim spot-checked (line numbers, the cuprum
0.1.0 API surface, the `StateInputError`/`EnvelopeMessagesError` contract, the
`set-gate` flag mapping, the test helpers, the documentation locations)
verified against the real source. Two blocking defects and a handful of
advisories remain before implementation.

## Verification trail (claims checked against real source)

- `_check_gate_ratio_consistent` (validate.py 250-278): numerator is
  `sum(by_chapter.values())`, `target <= 0` short-circuit present, invariant
  name `GATE_RATIO_CONSISTENT`, detail renders `GATE_THRESHOLDS` — all as the
  plan states.
- `_refuse_if_incoherent(state, *, context)` (_state_mutators.py 142-173) raises
  `StateInputError(summary, *details)`; recount calls it at _recount.py line 149.
  Confirmed.
- `EnvelopeMessagesError.__init__(*messages)` (contract/errors.py 30-40) accepts
  arbitrary positional messages, so appending a remedy line as an extra
  `messages` entry is contract-legal. Confirmed.
- cuprum 0.1.0 (read-only /data/leynos/Projects/cuprum): `cuprum/sh.py` defines
  `make`, `run_sync(*, capture=True, ...)`, `ExecutionContext`; `cuprum/
  catalogue.py` defines `ProgramCatalogue`. `single_program_catalogue` is a test
  fixture, not a cuprum symbol — the plan's Decision Log phrasing implies it is
  part of "the locked cuprum 0.1.0" surface; it is actually the suite fixture.
  Harmless, but see advisory A3.
- pytest-timeout under pytest-xdist: `make test` runs `pytest -n
  $(PYTEST_XDIST_WORKERS)`; the existing slow e2e tests already carry
  `@pytest.mark.timeout(180)` and pass under that configuration. The plan reuses
  a proven in-repo pattern, not a memory claim. Acceptable.
- `set-gate` flag mapping (_gate_drafting_mutators.py 71-73): `knitting_30 ->
  done_30` etc.; Cyclopts renders the parameter as `--knitting-30`. Remedy text
  consistent.
- ADR-001, ADR-006, ADR-010 all exist and support the deterministic/judgemental
  boundary the plan respects (recount reports; the model adjudicates; the remedy
  points at a verb, never a hand-edit).

## BLOCKING

### B1 (Telefono / Doggylump) — the message template is not specified

The actionable message template is not specified; "pick one and pin it" defers
the load-bearing design decision. Work item 2 names two implementation shapes
(re-validate in recount vs. add an
optional `remedy` param to `_refuse_if_incoherent`) but never specifies the
actual remedy string or how the per-gate, two-direction enumeration renders.
The whole task exists to make one specific message actionable, yet the message
text — the deliverable — is left to implementation-time invention. A reviewer
cannot confirm the acceptance criterion ("names the crossed threshold and the
remedy") is met because the plan does not state what "named" looks like. Pin the
exact template (or a worked example for each of: 30 upward, 50 upward, 80
upward, and at least one downward case), so the behavioural and e2e substring
assertions are derivable from the plan rather than reverse-engineered from the
implementation. This is the difference between a plan and a wish.

### B2 (Doggylump / Pandalump) — downward framing is incoherent

The "crossed threshold" framing is incoherent for the downward direction, and
the plan does not resolve it; acceptance tests only the upward path end to end.
`gate-ratio-consistent` fires in both directions, and the plan knows this (Risk
1). But Work item 2's remedy spec instructs the message to "name the specific
crossed threshold(s) ... derived from GATE_THRESHOLDS and the proposed drafted
ratio". In the downward case (gate `true`, ratio fallen below) nothing was
"crossed" upward; the existing `test_recount_legitimate_gate_breach_refuses`
drops the ratio to 0 with all gates `true`. A message that says "you crossed the
80% threshold; run set-gate --knitting-80" is actively wrong there — the
operator should be *clearing* the gate or restoring drafts, and the plan's own
Constraints forbid prescribing a hand-edit. The plan gestures at this (lines
326-328) but leaves the downward message text and its derivation unspecified,
and the Validation/Acceptance section (lines 503-516) drives only the upward
direction through the behavioural scenario and the e2e. Required before
implementation: (a) specify the downward message text explicitly (it must not
say "crossed ... run set-gate --knitting-NN"); (b) add a behavioural or e2e
acceptance assertion for the downward direction so the dual-direction promise in
Risk 1 is actually proven at the user-visible level, not only in a unit test.
Without this, the headline feature ships a misleading message on a path that
already has a passing test.

## ADVISORY

- A1 (Wafflecat / Dinolump) — the users' guide already documents the coupling
  from the set-gate side (lines 289-298: set-gate is "the **repair** for a gate
  that lags its ratio ... after a recount moved the ratio past 30% but done_30
  is still off"), and lines 370-371 already state the recount refusal. Work item
  5's framing ("document the coupling") overstates the gap; the real work is a
  forward cross-link from the recount paragraph. Acknowledge the existing
  coverage in the plan so the implementer adds a pointer rather than duplicating
  prose (and risking drift between two descriptions of the same rule).

- A2 (Pandalump) — Work item 2 shape 1 ("re-run validate_state(proposed) in
  recount") double-validates: recount already calls `_refuse_if_incoherent`,
  which itself calls `validate_state`. Re-running it to branch on the verdict
  means validating twice on the refusal path. Harmless for correctness (pure
  function) but inelegant; prefer shape 2 (the backward-compatible `remedy`
  keyword) which validates once, and say so, rather than leaving the choice
  genuinely open.

- A3 (Telefono) — Decision Log entry 3 describes `single_program_catalogue` as
  part of "the locked cuprum 0.1.0" surface. It is the test-suite fixture, not a
  cuprum export. Correct the wording so a future reader does not go looking for
  it in `cuprum/`.

- A4 (Buzzy Bee) — scale/cost are not applicable (a message-text change plus
  docs; bounded inputs: three thresholds, two directions). No concern. Noting it
  so the panel coverage is explicit.

- A5 (Dinolump) — the detail-case substring contract (`("0.3", "0.5", "0.8")`,
  test_validate_state_details.py line 219) is satisfied even if Work item 1
  renders thresholds as `0.30/0.50/0.80`, since `"0.3"` is a substring of
  `"0.30"`. Good. But Work item 1 says to render the threshold per-gate AND keep
  the literal tuple substrings; confirm the chosen prose still emits a contiguous
  `0.3`/`0.5`/`0.8` (e.g. not `0.300`). A test will catch it, but the plan should
  state the rendering precision to avoid a wasted red cycle.

## Pre-mortem (Doggylump)

Six months out, the most likely incident: an operator hits the downward refusal
(a recount after drafts were trimmed, or a gate set prematurely), reads "you
crossed the 80% threshold — run `set-gate --knitting-80`", does exactly that,
and set-gate refuses (or worse, the operator hand-edits `state.gates` to silence
the loop), corrupting the gate-integration record the design exists to protect.
Root cause: B2 — the upward-shaped message leaking into the downward path.
Prevention designable now: specify and test the downward message separately
(B2), and keep the remedy pointing only at verbs, never edits (already a
Constraint).

## Alternatives checkpoint (Wafflecat)

Strongest alternative: enrich only the shared `Violation.detail` to be fully
self-describing (per-gate, per-direction) and have recount append a single fixed
pointer sentence ("see `novel-state set-gate`; integrating a knitting pass is a
judgement, not a recompute") without recomputing the crossed-threshold
percentage in the command layer. Trade-off: gives up the precisely-named
percentage in the recount-specific line (slightly less actionable) but removes
the upward/downward branching from the command layer entirely, sidestepping B2's
failure mode and shrinking the command-layer change to one constant string. The
proposed design is defensible if B1/B2 are pinned; this alternative is the safer
fallback if the message matrix proves fiddly.
