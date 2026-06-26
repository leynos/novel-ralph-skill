# Logisphere Design Review — roadmap 2.2.4 ExecPlan (Round 2)

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-4.md`.
Verdict: **REVISE**. The three round-1 blocking points (B1/B2/B3) and the four
advisories (A1-A4) are genuinely resolved and verified against real source. One
**new** blocking defect emerged that round 1 did not surface: Work item 5
registers four subcommands into `novel_state.py`, which is already at 399 of
the 400-line hard cap, with no extraction plan — the work item breaches the cap
on landing.

## Round-1 resolutions — verified against source (do not re-litigate)

- **B1 resolved (set-gate identity).** `set_cursor`
  (`_state_mutators.py:176-234`)
  does **not** call `_refuse_if_incoherent(prior, ...)`; it derives the view
  only to prove structural completeness, edits, then validates the *proposed*
  state. `advance_phase` (line 306) **does** refuse the prior. Confirmed by
  reading both bodies. The repair-mutator framing (D4) is therefore
  structurally sound: an incoherent gate-lags-ratio prior is accepted, the gate
  is asserted to its ratio-mandated value, and the now-coherent proposed state
  writes. The Purpose, Constraint, D4, and WI1 fixtures are mutually consistent
  on this.
- **B2 resolved (fixtures).** `COHERENT_BASELINE`/`PHASE_STATES["drafting"]` is
  68800/80000 = 0.86 with all three gates `true`
  (`_library.py:39-42,60-64,79-97`) — confirmed it cannot show an observable
  flip. `WorkingTreeSpec` exposes `done_30`/`done_50`/`done_80`,
  `final_pass_complete`, and per-chapter `draft_words`/`target_words`
  (`_specs.py:170-207`), and `_gate_true_below_threshold`
  (`_variants.py:80-96`) is the exact shrink-words-and-set-gates recipe D8
  cites. The three WI1 fixtures (`gate_lags_ratio` 0.45/all-false,
  `ratio_not_crossed` 0.15/all-false, `ratio_crossed_coherent`
  0.45/done_30-true) are constructible as written and the arithmetic checks out
  against `_check_gate_ratio_consistent`'s `sum(by_chapter)/target`
  (`validate.py:263`).
- **B3 resolved (line count).** `_state_mutators.py` is 325 lines (`wc -l`),
  matching the corrected Constraint and Risk. `novel_state.py` is 399.
- **A1 resolved (sufficiently).** `log.md` receipts are written only by
  `_reconcile.py`, `_set_chapters.py`, and `novel_state.py` (`init`).
  `set-cursor`, `advance-phase`, and `recount` (all in `_state_mutators.py`)
  write none. The developers-guide segregation rule (lines 372-380) confirms
  single-file mutators open no `[pending_turn]` bracket. D3's no-receipt stance
  is grounded; the ADR 010 reconciliation note (WI6) closes the roadmap-wording
  divergence. NB `init` is the one single-file-style mutator that *does* append
  a `log.md` receipt, so the roadmap's "log-receipt discipline as the existing
  mutators" is genuinely ambiguous — the ADR note should name `init` as the
  exception so the reconciliation is airtight, not merely cite the multi-file
  mutators. Advisory, not blocking.
- **A2 resolved.** `pass_number` is pinned end to end with
  `Annotated[int, Parameter(name="--pass")]`; no name translation.
- **A3 resolved.** The Constraint forbids editing the validator to match the
  stale
  `current`-vs-`by_chapter` doc prose. Verified: `validate.py:263` uses
  `sum(by_chapter)`, the design §5.2 / state-layout prose says `current`.
- **A4 resolved (mechanism verified live).** Cyclopts 4.18.0 exposes
  `ValidationError` as a `CycloptsError` subclass. A no-flag `set-gate` parses
  cleanly to `{}` (verified — Cyclopts does **not** reject it on its own), so
  the wrapper must raise. A `ValidationError(msg=...)` raised in the wrapper
  propagates as a `CycloptsError` through `app(..., exit_on_error=False)`
  (verified live), and `runner.py:225-232` maps `CycloptsError` →
  `ExitCode.USAGE_ERROR` (exit 2). D9 is implementable; the concrete class is
  `cyclopts.ValidationError` (constructor takes `msg=`).

## External-library claims — verified live, not from memory

- cuprum 0.1.0 (locked, `uv.lock`):
  `SafeCmd.run_sync(*, capture=True, echo=False, context=None)` confirmed via
  `uv run python -c "inspect.signature(...)"`. The
  local `/data/leynos/Projects/cuprum` checkout has the drifted `output=` form;
  Surprise S1 is correct to pin the locked wheel.
- Cyclopts 4.18.0 (locked): `bool | None = None` yields `--flag`/`--no-flag`
  and a
  no-flag default of untouched — verified live. `ValidationError` propagation —
  verified live (above).
- pytest-timeout 2.4.0, tomlkit 0.15.0 — versions confirmed in `uv.lock`. The
  per-test marker-override claim is cited to the official docs; acceptable.

## BLOCKING

### B4 — Work item 5 breaches the 400-line cap on `novel_state.py` (structural / Pandalump)

`novel_ralph_skill/commands/novel_state.py` is **399 lines** — one line below
the AGENTS.md hard cap. Work item 5 directs registering **four** new
subcommands into `build_app()` *in this file*, plus updating both the
`build_app` docstring and the module docstring to enumerate four more
subcommands. Measured against the existing wrappers (`set-chapters` 392-397 is
6 lines; `recount` 378-383 is 6 lines), the new registrations are realistically:

- `set-gate` (four `bool | None` params + the no-flag `ValidationError` guard +
  deferred import + call): ~8-12 lines;
- `complete-final-pass`: ~5 lines;
- `set-fangirl`: ~5 lines;
- `set-critic-pass` (`Annotated[int, Parameter(name="--pass")]` + import +
  call):
  ~6-7 lines;
- two docstring expansions naming four more subcommands: ~4-6 lines;
- possibly a new `typing`/`cyclopts.Parameter` import at module top.

That is **~35-45 new lines added to a file with one line of headroom** — an
immediate breach of the 400-line cap and an instant trip of the plan's own
Tolerance ("no source file may exceed 400 lines … stop and escalate"). The plan
created `_gate_drafting_mutators.py` precisely to keep the *bodies* off
`_state_mutators.py` (325 lines), but it overlooked that the *registration
site* is even tighter. The Risk section addresses body-module size and is
silent on `novel_state.py`. As written, Work item 5 cannot be completed without
an unplanned refactor.

**Resolve in the plan, before code.** Decide and specify one of: (a) extract
`build_app`'s registration block (or the four new wrappers) into a
      sibling registration helper the way the bodies were extracted, naming the
      module and the no-cycle import path; or
  (b) trim `novel_state.py` (e.g. condense the two long docstrings) to a
  verified
      headroom that absorbs the four wrappers with margin, and state the resulting
      line budget; or
  (c) state explicitly that registration moves wholesale into
      `_gate_drafting_mutators.py` via an `App`-extension pattern, with the import
      cycle addressed.
Whichever is chosen, give the post-change line count so the audit gate (which
checks the plan against reality) passes. Leaving this to "escalate if it
breaches" is exactly the deferral the Tolerances forbid for a known, measurable
breach.

## ADVISORY

### A5 — ADR 010 reconciliation note should name `init` as the receipt exception

`init` is a single-`Path.replace`-per-file mutator that nonetheless writes a
`log.md` receipt (developers-guide lines 378-380). The roadmap's "log-receipt
discipline as the existing mutators" wording can be read as binding `init` too.
The ADR 010 A1 note (WI6) currently cites only the multi-file mutators; add one
clause acknowledging `init` writes a receipt yet the four new mutators follow
the `set-cursor`/`advance-phase`/`recount` no-receipt sub-family, so a future
auditor reading the roadmap literally against `init` does not see an omission.

### A6 — Pin `cyclopts.ValidationError(msg=...)` in the plan, not just the channel

D9/WI1 commit to "pin the exact Cyclopts class in Work item 5." Live
verification shows it is `cyclopts.ValidationError`, constructed
`ValidationError(msg="…")`, and it propagates as a `CycloptsError`. Recording
the class name and constructor kwarg in the plan now (rather than leaving "the
exact class" open) removes the last memory-vs-verified gap on the exit-2 path
and de-risks WI5.

## Pre-mortem (Doggylump)

1. **Most likely failure (new):** the implementer lands the four bodies cleanly
   (WI1-4 green), then in WI5 adds the registrations to `novel_state.py`,
   `make all` fails the 400-line interrogate/size gate, and the implementer
   either jams the wrappers onto one line to squeak under (hurting readability
   and docstring coverage) or escalates mid-task. Mitigation: B4 forces the
   registration-site size decision into the plan before code.
2. **Blast radius:** contained to WI5 and `novel_state.py`; the bodies and their
   tests are unaffected. But WI5 is the reachability gate — the e2e arms for
   all four mutators depend on it, so a stalled WI5 blocks the acceptance proof
   for the whole task.
3. **Missed signal (carried from r1, now mitigated):** the WI1 Hypothesis
   property
   passing vacuously. D8's `event()`/`target` anti-vacuity requirement
   addresses it; keep that requirement non-negotiable in implementation.

## Strongest alternative (Wafflecat)

The r1 alternative (four zero-argument `complete-knitting-30/50/80` verbs
instead of the multi-flag `set-gate`) is now explicitly rejected in D10 with a
recorded rationale, and the repair semantics (D4) plus the fixture recipe (D8)
remove the ambiguity that motivated it. That is an adequate disposition. A
*second* alternative worth one line in D10: because the validator makes a free
gate-set impossible and the design says gates only ever flip **to** true, the
`--no-knitting-NN` (false) direction `set-gate` exposes is only ever a refusal
or a no-op in practice — it can never legitimately write `false` above
threshold, and below threshold the gate is already false. The plan keeps it for
symmetry, which is defensible, but the false direction is dead weight on the
happy path; note it as intentional so a reader does not mistake it for a
supported operation.

## Trail followed

docs: `roadmap.md` (2.2.4, lines 876-888), `novel-ralph-harness-design.md` §4.1
(mutator table) / §5.2, ADR 001 (deterministic/judgemental boundary), ADR 003
(exit-code channels), ADR 008 (write-time precondition precedent),
`developers-guide.md` §"Checker/mutator segregation" (362-423),
`state-layout.md` §Critic/§Fangirl/§Gates (91-102, 177-199),
`roadmap-2-2-4.review-r1.md`. source: `_state_mutators.py` (set_cursor
no-prior-refusal 176-234, advance_phase prior-refusal 306; 325 lines),
`validate.py:_check_gate_ratio_consistent` (250-278, `sum(by_chapter)`) and the
predicate list (no critic.pass / fangirl / final_pass binding),
`novel_state.py:build_app` (321-399, the registration site at 399 lines),
`_set_chapters.py:manifest_coherence_violations` (85, exit-3 precondition),
`schema.py` (CriticState.pass_number↔`pass`, FangirlState.last_chapter_passed),
`tests/working_corpus/_specs.py` + `_library.py` + `_variants.py` (fixtures),
`tests/working_corpus/_builder.py` (critic["pass"]=1, fangirl["
last_chapter_passed"]=0), `contract/runner.py` (CycloptsError→exit 2,
StateInputError→exit 3). live: `uv run` confirmation of cuprum 0.1.0
`run_sync`, Cyclopts `bool | None` tri-state, and `ValidationError` propagation
to a `CycloptsError`; `uv.lock` locked versions. cuprum READ-ONLY sibling
confirmed drifted ahead of the locked wheel. skills: logisphere-design-review
(this), leta/grepai for navigation.
