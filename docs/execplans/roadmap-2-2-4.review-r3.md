# Logisphere Design Review — roadmap 2.2.4 ExecPlan (Round 3)

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-4.md`.
Verdict: **REVISE**. The round-2 blocking point (B4) and advisories (A5, A6)
are genuinely resolved and verified against real source. But one **new**
blocking defect surfaces from the very mechanism round 3 hardened: the no-flag
`set-gate` exit-2 path raises `cyclopts.ValidationError(msg=...)`, and that
exception cannot be stringified by the runner's `CycloptsError` arm —
`str(exc)` raises `NotImplementedError` *inside* the exception handler, so the
command crashes with an uncaught traceback instead of emitting a clean exit-2
envelope.

## Round-2 resolutions — verified against source (do not re-litigate)

- **B4 resolved (registration-site cap).** `novel_state.py` is **399** lines and
  `_state_mutators.py` is **325** (`wc -l`), matching the Constraint and Risk.
  The D11 registrar pattern is structurally sound: `make_contract_app` returns
  a plain `cyclopts.App` (`runner.py:75-81`), and `@app.command` registers a
  decorated function onto any passed-in `App` regardless of defining module
  (verified live). The deferred-import cycle reasoning is correct:
  `_state_mutators.py:35-44` imports `STATE_INPUT_ERRORS`/`state_path`/
  `working_dir` from `novel_state` at module top, so a top-level
  `_gate_drafting_mutators` import in `novel_state` would close the cycle; the
  deferred import in `build_app` avoids it, exactly as `recount`/`reconcile`/
  `set_chapters` already defer.
- **A5 resolved.** `init` writes `state.toml` *and* `log.md`, each via one
  `Path.replace`, with no bracket (developers-guide 372-382). WI6's ADR-010
  note names `init` as the receipt exception so the roadmap's "log-receipt
  discipline" wording is reconciled airtight.
- **A6 — class pinned but the pin is WRONG (see B5).**
  `cyclopts.ValidationError`
  *is* a `CycloptsError` subclass (verified live), and `runner.py:225-232` maps
  `CycloptsError` → exit 2. That much holds. What round 2/3 did **not** verify
  is that the runner can *stringify* a bare `ValidationError(msg=...)`. It
  cannot.

## External-library claims — verified live, not from memory

- **cuprum** locked 0.1.0 (`uv.lock`):
  `SafeCmd.run_sync(*, capture=True, echo=False, context=None)` — confirmed via
  `uv run inspect.signature`. The
  read-only sibling `/data/leynos/Projects/cuprum/cuprum/sh.py:441` has the
  drifted `output=RunOutputOptions` form; Surprise S1 correctly pins the locked
  wheel, and `test_set_chapters_e2e.py:107-109` already calls the locked
  `run_sync(context=, capture=)` form. The e2e plan reuses this verbatim. Sound.
- **Cyclopts** 4.18.0: `bool | None = None` yields `--flag`/`--no-flag` and a
  no-flag default of empty/None; `Annotated[int, Parameter(name="--pass")]`
  binds `--pass 2` → `pass_number == 2`. Both verified live via
  `App.parse_args(..., exit_on_error=False)`.
- **Validator gate logic** (`validate.py:248-278`): `sum(by_chapter)/target` vs
  thresholds `(0.30, 0.50, 0.80)`, binding all three knitting gates
  simultaneously (`all(flag == (ratio >= threshold))`), with a `target <= 0`
  short-circuit. The WI1 fixture arithmetic (`gate_lags_ratio` 0.45/all-false
  incoherent; `ratio_not_crossed` 0.15/all-false coherent;
  `ratio_crossed_coherent` 0.45/done_30-true coherent) is exactly right, and the
  `_variants.py:80-96` shrink-and-set recipe is constructible.
  `WorkingTreeSpec` exposes `done_30/50/80`, `final_pass_complete`,
  `draft_words`, `target_words` (`_specs.py:170-172`). The repair-mutator
  framing (D4) matches `set_cursor`'s no-prior-refusal skeleton vs
  `advance_phase`'s prior-refusal.
- **state-layout reference** (`skill/novel-ralph/references/state-layout.md`):
  "Passes are numbered from 1" (178) backs D6's `pass >= 1`;
  `last_chapter_passed` = "last chapter where fangirl ran" backs
  `0 <= last_chapter <= len(chapters)`; gates flip "after the pass is
  integrated" (199) and `final_pass_complete` at end of Phase 9 (202) back the
  repair framing. (Minor: the plan cites this as bare `state-layout.md`; it
  lives under `skill/novel-ralph/references/`, not `docs/`.)

## BLOCKING

### B5 — the no-flag `set-gate` exit-2 mechanism crashes the runner (contracts / Telefono + failure modes / Doggylump)

Decision D9 / WI1 / WI5 specify: the registrar wrapper raises
`cyclopts.ValidationError(msg="set-gate requires at least one flag")`, which
propagates through `app(..., exit_on_error=False)` as a `CycloptsError`, which
`runner.py:225-232` maps to exit 2. The first two steps hold. The third does
not.

`runner.py:230` builds the exit-2 envelope with `messages=[str(exc)]`. A bare
`ValidationError(msg=...)` raised by hand has `argument=None`, `group=None`,
`command_chain=None` (the app does **not** enrich a manually-raised error;
verified live). `ValidationError._segments()`
(`cyclopts/exceptions.py:229-265`) overrides the base and builds its body
*before* consulting `msg`: with all three of `argument`/`group`/`command_chain`
unset it reaches the final `else: raise NotImplementedError` (line 258). The
base class's `msg` short-circuit (`exceptions.py:160`, "if self.msg is not
None: yield …; return") is **never reached**, because the subclass override
does not delegate to it first. So `str(exc)` — and `__rich__` — raise
`NotImplementedError`.

Driving the **real `runner.run`** with the plan's exact mechanism:

```text
run(app, ['set-gate'], context=None)
  → except CycloptsError → CommandOutcome(..., messages=[str(exc)])
  → cyclopts/exceptions.py:188 __str__ → :258 raise NotImplementedError
  → UNCAUGHT NotImplementedError (no clean exit-2 envelope)
```

The no-flag `set-gate` would crash with a traceback and a non-contract exit
code, the precise **opposite** of the WI5 e2e assertion ("exits 2 (usage),
`ok: false`, no traceback"). This breaks D9, the WI1 no-flag unit test, the WI5
no-flag e2e arm, and the Acceptance "usage faults are exit 2" criterion.

**This is a memory-vs-verified gap the plan explicitly claimed to have
closed.** The A6 "verified live" note checked `issubclass(...)` and
propagation, but never `str()` in the handler. Per the standing rule, an
uncited/unverified locked-library behaviour claim is a blocking defect; here
the claim was actively *wrong*.

**Resolve in the plan, before code.** Drop the
`cyclopts.ValidationError(msg=...)` mechanism. The codebase already has the
correct, working pattern: `_desloppify.py` detects a body-level usage fault,
raises a **domain** exception (`DesloppifyUsageError(EnvelopeMessagesError)`,
`_desloppify.py:69`), and a thin adapter (`_scan_or_usage`,
`_desloppify.py:315-345`) catches it and returns
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=...)` **directly**, never
routing through the runner's `str(CycloptsError)` arm. The no-flag `set-gate`
guard must do the same: raise a domain usage error and return an exit-2
`CommandOutcome` from an adapter, OR (if a `CycloptsError` is genuinely wanted)
pin and verify a concrete `CycloptsError` subclass whose `str()` succeeds with
a plain message — `ValidationError(msg=...)` is not one. Note `StateInputError`
cannot be reused: it maps to exit 3, not exit 2. Whichever is chosen, the plan
must show the exit-2 envelope is produced by *running the real `runner.run`*,
not by asserting subclass-hood.

## ADVISORY

### A7 — cite `state-layout.md` at its real path

The plan cites `state-layout.md` (bare) repeatedly; the file is
`skill/novel-ralph/references/state-layout.md`, not `docs/state-layout.md`. A
novice following the plan verbatim will not find it under `docs/`. One-line fix
in the "Docs to read" lists.

### A8 — name the exit-2 adapter in the Interfaces section

If B5 is resolved with the `_desloppify` adapter pattern, the new module gains
a small usage-fault exception + adapter; the Interfaces/dependencies section
(which currently enumerates only the four bodies + registrar) should name them
so the surface stays exhaustive and the WI5 line budget (~230-290 lines
projected for `_gate_drafting_mutators.py`) absorbs the extra ~10-15 lines
without re-tripping the cap. Re-measure in WI5.

## Pre-mortem (Doggylump)

1. **Most likely failure (new):** the implementer codes WI1/WI5 exactly as
   written, the no-flag `set-gate` unit/e2e tests *crash* (uncaught
   `NotImplementedError`) rather than exiting 2, and the implementer either
   patches the runner (out of scope, a contract change) or invents an ad-hoc
   stringification — both worse than adopting the existing `_desloppify`
   adapter. Mitigation: B5 forces the correct, already-proven pattern into the
   plan.
2. **Blast radius:** contained to the no-flag `set-gate` arm and the registrar,
   but it is on the acceptance path (D9 + WI5 e2e), so it blocks the task's
   "usage faults are exit 2" sign-off. The four mutator *bodies* and their
   ratio/precondition tests are unaffected and remain sound.
3. **Carried, still mitigated:** WI1 Hypothesis vacuity — D8's `event()`/
   `target`
   anti-vacuity requirement stands; keep it non-negotiable.

## Strongest alternative (Wafflecat)

Beyond the disposed-of per-gate-verb alternative (D10) and the
`--no-knitting-NN` symmetry note (also D10): for the no-flag guard
specifically, the cleanest alternative is to make "at least one flag" a
**Cyclopts command/group validator** rather than a hand-raise. A validator
failure raises `ValidationError` *with the `group`/`command_chain` populated by
Cyclopts itself*, which stringifies cleanly (the
`else: raise NotImplementedError` branch is only hit by a bare manual raise).
That keeps the error inside Cyclopts's own machinery and the runner's
`CycloptsError` arm. Either this or the `_desloppify` domain-error adapter
resolves B5; the plan should pick one and *verify it through `runner.run`*.

## Trail followed

docs: `roadmap.md` (2.2.4, 876-895), `novel-ralph-harness-design.md` §4.1/§5.2,
ADR 001/003/006/008, `developers-guide.md` "Checker/mutator segregation"
(362-423, init-receipt 372-382), `skill/novel-ralph/references/state-layout.md`
(critic 177-180, fangirl 102, gates 199-202), `roadmap-2-2-4.md`,
`roadmap-2-2-4.review-r1.md`, `roadmap-2-2-4.review-r2.md`. source:
`novel_state.py:build_app` (321-399, deferred-import-per-wrapper pattern),
`_state_mutators.py` (set_cursor no-prior-refusal, top-level novel_state import
35-44, 325 lines), `validate.py:_check_gate_ratio_consistent` (248-278),
`_set_chapters.py:manifest_coherence_violations`, `_desloppify.py`
(DesloppifyUsageError 69, _scan_or_usage adapter 315-345), `contract/runner.py`
(make_contract_app 75-81, CycloptsError→exit2 / str(exc) 225-232), `schema.py`
(CriticState.pass_number↔`pass`, FangirlState.last_chapter_passed),
`tests/working_corpus/_specs.py` + `_variants.py:_gate_true_below_threshold`
(80-96), `tests/test_set_chapters_e2e.py` (107-109 cuprum call form),
`tests/installed_binary_fixtures.py` (installed_novel_state 93). live
(`uv run`, locked .venv): cuprum 0.1.0 `run_sync` sig; Cyclopts `bool | None`
tri-state, `--pass` annotation, `ValidationError` subclass-of-CycloptsError AND
`str(ValidationError(msg=...))` → `NotImplementedError` AND `runner.run` crash
on no-flag set-gate; `uv.lock` cuprum 0.1.0. sibling
`/data/leynos/Projects/cuprum` confirmed drifted (`output=` form). skills:
logisphere-design-review (this), leta/grepai for navigation.
