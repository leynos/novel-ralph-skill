# Add CLI mutators for the gate and drafting sub-state

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 4)

## Purpose / big picture

Roadmap task 2.2.4 closes the last hand-edit hole in the harness state. Four
fields had no validated CLI mutator, so beta testing forced direct edits of
`working/state.toml` — a direct violation of ADR 001 (all state mutation goes
through validated commands) and of the skill's "always exercise the installed
contract" rule:

- the three knitting-circle gate flags `gates.knitting.done_30`, `done_50`,
  `done_80`;
- the final-pass gate flag `gates.final.final_pass_complete`;
- the critic sub-state `drafting.critic.pass` (the on-disk key; the typed
  attribute is `CriticState.pass_number`);
- the fangirl sub-state `drafting.fangirl.last_chapter_passed`.

After this change every gate and drafting sub-state field is settable through a
`novel-state` subcommand. A user can run, for example:

```bash
novel-state set-gate --knitting-30          # asserts gates.knitting.done_30 true
novel-state complete-final-pass             # flips gates.final.final_pass_complete true
novel-state set-critic-pass --pass 2        # sets drafting.critic.pass
novel-state set-fangirl --last-chapter 6    # sets drafting.fangirl.last_chapter_passed
```

Each mutator carries the **same** discipline as the existing `set-cursor` /
`advance-phase` mutators: it loads the `tomlkit` document, edits in place, runs
the §5.2 validate-before-persist pass, writes atomically only when the proposed
state is coherent, and refuses an incoherent transition with **exit 3** (state
error), never the benign exit 1 the harness loops on. A refusal writes nothing,
leaving the prior `state.toml` byte-for-byte intact.

**What `set-gate` is for (the load-bearing semantic; design §5.2 invariant
7).** The §5.2 `gate-ratio-consistent` invariant binds *all three* knitting
gates at once: a state is coherent only when each of `done_30`/`done_50`/
`done_80` equals `drafted_ratio >= threshold`
(`validate.py:_check_gate_ratio_consistent`, lines 250-278). The harness's
primary gate transition — the ratio crossing a threshold — is performed by the
word-count mutators (`recount`/`set-cursor` update `by_chapter`, which moves
the ratio). The gate booleans, however, have no mutator that asserts the value
the ratio now mandates, so a state where the ratio has crossed 0.30 but
`done_30` is still `false` is **incoherent and unrepairable through a
command**: that is the precise hand-edit hole beta testing hit. `set-gate` is
therefore the **repair mutator for a gate that lags its ratio** — an
incoherent-prior→coherent-result transition. It follows the `set_cursor`
skeleton, which (unlike `advance-phase`) does **not** refuse an incoherent
prior; it only proves the document is structurally complete, edits the gate
boolean(s), and validates the *proposed* state. So the only observable,
validator-permitted flip is exactly the repair: load a `done_30 = false` prior
whose ratio has crossed 0.30 (incoherent), assert `done_30 = true`, and write
the now-coherent state. From an *already-coherent* prior,
`set-gate --knitting-30` is a no-op re-assertion (the gate is already at its
ratio-mandated value) and exits 0 idempotently; flipping a gate the ratio does
**not** support (true below threshold, or false above it) is refused with
exit 3. This is recorded as Decision D4 and pinned by the Work item 1 tests,
which use an incoherent prior for the observable-flip case (Decision D8; B1
resolution).

Success is observable: `novel-state check` stays coherent (exit 0) after each
mutation; an incoherent set (e.g. asserting `done_30 = false` when the drafted
ratio has crossed 0.30, or `done_30 = true` when it has not) is refused with
exit 3 and the prior file is unchanged; and behavioural plus end-to-end tests
cover each mutator at the installed-binary boundary.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **ADR 001 — validated commands only.** Every one of these fields reaches
  `state.toml` only through a validated command. No mutator may bypass the
  `tomlkit` round-trip or skip validation
  (`docs/adr-001-deterministic-judgemental-boundary.md`).
- **Validate before persist (design §3.4, §4.1).** Each mutator edits the live
  `tomlkit` document, derives the typed `State` read view through
  `document_to_state`, applies `validate_state` (the §5.2 invariants), and
  writes atomically **only** when the proposed state is coherent. A refused
  request performs **no write**; the prior `state.toml` is byte-for-byte
  unchanged.
- **Refusal is exit 3, never exit 1 (design §3.2; ADR 003 §3.2).** An incoherent
  set, or a missing/unparseable/structurally-incomplete `state.toml`, is the
  contract's exit 3 (`STATE_ERROR`), routed through `StateInputError`. A shape
  fault (a non-integer `--pass`) is the parser's exit 2 (`CoercionError`),
  handled by the shared runner — not these bodies.
- **A body-detected usage fault is exit 2, produced by an adapter — never by
  raising `cyclopts.ValidationError(msg=...)` (B5 resolution; design §3.2).**
  The one usage fault these mutators detect themselves is a no-flag `set-gate`
  (the operator named no field to change). The Cyclopts parser cannot catch it
  (a no-flag `set-gate` parses cleanly to `{}`; verified live), so it is routed
  to exit 2 the way `desloppify` already routes its body-detected usage faults:
  a domain exception `GateDraftingUsageError(EnvelopeMessagesError)` raised in
  the registered wrapper, caught by a thin adapter that returns
  `CommandOutcome(code=ExitCode.USAGE_ERROR, messages=...)` **directly**, never
  routing through the runner's `str(CycloptsError)` arm
  (`_desloppify.py:DesloppifyUsageError` + `_scan_or_usage`, lines 69 and
  315-345 — the precedent). It must **not** raise
  `cyclopts.ValidationError(msg=...)`: a bare manually-raised
  `ValidationError(msg=...)` has `argument/group/command_chain` all `None`, so
  its `_segments()` override reaches `raise NotImplementedError` before the
  base-class `msg` short-circuit, and `str(exc)` therefore raises
  `NotImplementedError` **inside** the runner's `CycloptsError` arm
  (`runner.py:230`), crashing the command with an uncaught traceback rather
  than a clean exit-2 envelope (verified live driving the real `runner.run`;
  Decision D9, Surprise S3). `StateInputError` cannot be reused here: it maps
  to exit 3 (`runner.py:233-239`), not exit 2.
- **The §5.2 `gate-ratio-consistent` invariant binds `set-gate` (design §5.2
  bullet 7).** A knitting gate boolean is coherent only when it equals
  `drafted_ratio >= threshold`, and the invariant binds all three knitting
  gates simultaneously (thresholds 0.30/0.50/0.80;
  `novel_ralph_skill/state/validate.py:_check_gate_ratio_consistent` lines
  250-278; `GATE_THRESHOLDS`). `set-gate` therefore **cannot** assert a gate
  true while the ratio is below its threshold, and **cannot** assert it false
  once crossed: the validate-before-persist pass on the proposed state refuses
  a contradicting set with exit 3. The mutator follows the `set_cursor`
  skeleton, which does **not** refuse an incoherent prior (it only proves
  structural completeness), so the legitimate, observable transition is the
  **repair** of a gate that lags its ratio (incoherent prior → coherent
  result). From an already-coherent prior the assertion is an idempotent no-op.
  This constraint is pinned by tests (Work item 1), not asserted from prose.
- **The validator's drafted ratio is `sum(by_chapter)`, not `current` — do not
  "fix" the doc into the code.** design §5.2 (lines 528-529) and the
  state-layout reference at `skill/novel-ralph/references/state-layout.md`
  (hereafter "state-layout.md"; note the path — it lives under
  `skill/novel-ralph/references/`, NOT `docs/`; A7) (lines 197-198) describe
  the gate ratio as `word_counts.current / word_counts.target`, but the
  validator deliberately uses `sum(by_chapter.values()) / target`
  (`validate.py:263`, decoupling invariant 7 from invariant 3; see the
  `_check_gate_ratio_consistent` docstring). The plan, the fixtures, and the
  tests all track the validator's `by_chapter` total. The design prose is stale
  on this one point; **do not** edit the validator to match the doc — that
  would change `check` for every existing tree and break the §5.2 contract
  (Tolerance "Validator change"). If anything is reconciled it is the doc, and
  that is out of scope for this task.
- **Single-file mutators — no `[pending_turn]` bracket.** Each of these mutators
  writes exactly one file (`state.toml`) via one `Path.replace`, exactly like
  `set-cursor` and `advance-phase`. None is a multi-file writer, so none opens a
  `[pending_turn]` record (developers-guide "Checker/mutator segregation").
  They append no `log.md` receipt either — the existing single-file mutators
  (`set-cursor`, `advance-phase`, `recount`) do not, and the roadmap's "log
  receipt" wording mirrors the multi-file mutators (`reconcile`,
  `set-chapters`); see Decision D3.
- **Write-shaped success `result`, never `check`'s read shape (design §3.3;
  audit-2.2.2 Finding 2).** A mutator's success `result` names *what it
  changed* and never echoes `check`'s `violations` key. A cross-subcommand test
  pins `violations` to `check` alone
  (`tests/test_novel_state_violations_ownership.py`).
- **Locked dependencies only.** cuprum 0.1.0, Cyclopts 4.18.0, pytest-timeout
  2.4.0, tomlkit per `uv.lock`. No version bump. No new runtime dependency
  (Decision D1).
- **400-line file cap (AGENTS.md).** No source file may exceed 400 lines. Two
  files are at the cap and both are addressed structurally, not by runtime
  escalation (B4 resolution):
  - The new mutator **bodies** live in a new sibling module
    `_gate_drafting_mutators.py`, not appended to `_state_mutators.py` (325 lines,
    verified by `wc -l`), because 325 plus four bodies would breach it.
  - The four subcommand **registrations** do **not** go into
    `novel_state.py:build_app()` (399 lines, verified by `wc -l` — one line of
    headroom). Adding four `@app.command` wrappers there (~35-45 lines measured
    against the 6-line `set-chapters`/`recount` wrappers, plus two docstring
    expansions) would breach the cap on landing. Instead the four wrappers live
    in a single registrar function `register_gate_drafting_commands(app)` **in the
    new `_gate_drafting_mutators.py` module**, and `build_app` invokes it with
    one deferred-import line plus one call line — a net **+2 lines** to
    `novel_state.py` (401 → trimmed back under 400; see Decision D11 and Risk
    "registration-site size" for the measured budget). The registrar pattern is
    a plain Cyclopts use: `@app.command` registers a decorated function onto any
    `App` instance regardless of the defining module, so the wrappers may be
    defined in the sibling and applied to the `app` `build_app` passes in.
- **en-GB Oxford spelling** in all prose, comments, docstrings, and commit
  messages (`-ize`/`-yse`/`-our`).
- **The single path accessor.** Every body resolves `working/state.toml` through
  `novel_state.state_path()` (re-exported as `_state_path`), never by
  rebuilding the path (audit-1.3.5; audit-2.2.2 Finding 3).

## Tolerances (exception triggers)

- **Scope:** if implementation needs to touch more than 8 source/test files
  beyond the new module and its tests, or more than ~450 net lines of
  production code, stop and escalate.
- **Interface:** if `build_app()`'s zero-argument signature, the
  `CommandOutcome`
  shape, or any existing mutator body must change, stop and escalate.
- **Dependencies:** if any work item appears to need a new dependency or a
  version bump, stop and escalate.
- **Validator change:** if any work item appears to need a change to
  `validate_state` or the §5.2 invariant set, stop and escalate — that is a
  design change (ADR territory), not a mutator addition (see Decision D5).
- **Iterations:** if `make all` still fails after 3 focused attempts on one work
  item, stop and escalate.
- **Ambiguity:** if the command names, the field set, or the gate semantics
  admit
  two materially different readings, stop and present options.

## Risks

```plaintext
    - Risk: The implementer writes the set-gate happy-path test against
      COHERENT_BASELINE (the only named tree), finds done_30 already true, and
      either weakens it to a no-op or builds an incoherent prior without realising
      it changed the contract's meaning (round-1 pre-mortem signal 1).
      Severity: high
      Likelihood: medium
      Mitigation: D4 fixes set-gate's identity as the gate-lags-ratio repair mutator
      (set_cursor skeleton, no prior-refusal); D8 names the three exact fixtures and
      forbids reusing COHERENT_BASELINE; Work item 1 pins the refusal test first and
      the observable repair flip on the incoherent gate_lags_ratio fixture, and the
      Hypothesis property requires (event()/target) at least one observable flip so
      it cannot pass vacuously. There is no validator-bypass path and no
      free-set path.

    - Risk: Module size (body site) — appending four bodies to _state_mutators.py
      (325 lines, verified by wc -l) would breach the 400-line cap.
      Severity: medium
      Likelihood: high
      Mitigation: The new bodies live in a new module
      novel_ralph_skill/commands/_gate_drafting_mutators.py that reuses the shared
      load/refuse helpers from _state_mutators.py, exactly as _set_chapters.py and
      _recount.py do.

    - Risk: Registration-site size (B4) — novel_state.py is 399 of 400 lines
      (verified by wc -l), one line of headroom. Adding four @app.command wrappers
      to build_app (~35-45 lines measured against the 6-line set-chapters/recount
      wrappers) plus expanding the build_app and module docstrings to enumerate four
      more subcommands would breach the 400-line cap on landing, an immediate trip of
      the plan's own Tolerance. The round-2 reviewer (B4) flagged that the body-module
      extraction dodged the cap on _state_mutators.py but left the tighter
      registration site unaddressed.
      Severity: high
      Likelihood: high (certain without the mitigation)
      Mitigation: Decision D11 — the four wrappers are NOT defined in build_app. They
      live in a registrar function register_gate_drafting_commands(app) in the new
      _gate_drafting_mutators.py module; build_app calls it with one deferred-import
      line plus one call line (the no-cycle pattern recount/set-chapters already use
      for their deferred imports). The docstring expansion is also moved off
      novel_state.py: the four new subcommands are documented in the registrar's own
      docstring and in build_app's existing enumeration is extended by replacing the
      trailing clause (a net-zero-to-small edit, budgeted below). Measured net change
      to novel_state.py: +2 functional lines (deferred import + call) and a one-clause
      docstring edit; to keep a safety margin the two long build_app/module docstrings
      are condensed by >=2 lines so the post-change count is <=399 (stated and to be
      re-measured by wc -l in WI5, which is a gate-passable acceptance criterion of
      that work item). The bodies+registrar module _gate_drafting_mutators.py is a
      fresh file with ample budget: the four bodies, the registrar, AND the round-4
      B5 addition (the GateDraftingUsageError class + the _set_gate_or_usage adapter,
      ~10-15 lines with docstrings) are projected ~245-305 lines, still well under
      400; re-measured in WI5 (A8).

    - Risk: No-flag set-gate exit-2 mechanism (B5) — raising
      cyclopts.ValidationError(msg=...) in the wrapper crashes the runner. A bare
      manually-raised ValidationError(msg=...) has argument/group/command_chain all
      None, so str(exc) raises NotImplementedError inside runner.py:230's
      CycloptsError arm: an uncaught traceback and a non-contract exit, the precise
      opposite of the exit-2 envelope the plan asserts.
      Severity: high
      Likelihood: high (certain if the round-3 mechanism is coded as written)
      Mitigation: Decision D9 (revised round 4) drops ValidationError(msg=...) and
      adopts the proven _desloppify adapter pattern: a domain
      GateDraftingUsageError(EnvelopeMessagesError) raised in the wrapper, caught by
      a thin adapter (_set_gate_or_usage) returning
      CommandOutcome(code=ExitCode.USAGE_ERROR, messages=...) directly, never via the
      runner's str(CycloptsError) arm. Verified live driving the real runner.run: the
      no-flag set-gate exits 2 with {"ok": false, messages: [...]} and no traceback
      (Surprise S3). WI1 and WI5 must demonstrate the exit-2 envelope by running the
      real runner.run / installed binary, not by asserting subclass-hood.

    - Risk: critic.pass coherence — set-critic-pass could write a pass number that
      the §5.2 critic sub-rules (consecutive-clean bounds) make incoherent.
      Severity: medium
      Likelihood: low
      Mitigation: pass is not itself a §5.2-validated field (the validator bounds
      consecutive_clean and convergence_target, not pass). set-critic-pass still
      runs the full validate-before-persist pass for defence in depth, so any
      knock-on incoherence is refused with exit 3. A property test (Work item 4)
      pins that a coherent prior plus an in-range pass stays coherent, and that a
      negative pass is refused only if it makes the state incoherent (it does not,
      so the plan adds a write-time positivity precondition; Decision D6).

    - Risk: fangirl.last_chapter_passed has no §5.2 invariant, so the validator
      alone will accept any integer, including one past the manifest.
      Severity: low
      Likelihood: medium
      Mitigation: set-fangirl adds a write-time precondition
      (0 <= last_chapter <= len(chapters)), mirroring set-chapters'
      manifest_coherence_violations precedent of owning write-time preconditions
      the §5.2 set does not (ADR 008; Decision D6). Pinned by a refusal test.

    - Risk: cuprum local source has drifted ahead of the locked 0.1.0 wheel.
      Severity: medium
      Likelihood: confirmed
      Mitigation: All cuprum API claims are pinned against the locked 0.1.0
      resolved by `uv run` (Surprise S1), not the local /data/leynos/Projects/cuprum
      checkout. The e2e tests reuse the existing installed_novel_state fixture and
      the SafeCmd.run_sync(capture=True, context=...) form the existing
      set-chapters e2e already uses.
```

## Progress

```plaintext
    - [x] Work item 1: set-gate mutator (knitting + final gate flags) + tests.
      DONE: `_gate_drafting_mutators.py` created with all four bodies, the
      `GateSelection` bundle, the `GateDraftingUsageError` + `_set_gate_or_usage`
      adapter, and `register_gate_drafting_commands`; `build_app` wired (deferred
      import + registrar call) and its docstrings condensed so `novel_state.py`
      is 399 lines. set-gate unit/property/snapshot tests pass. `make all` green
      (1139 passed, 1 skipped). CodeRabbit run 1 addressed: dropped the spurious
      `# pyright: ignore` comments (the project uses `ty`, and the existing
      `build_app` wrappers carry none), and enforced the property's non-vacuity
      via a module-level flip counter asserted in `teardown_module` (event()
      alone is statistics-only), plus message-bearing asserts throughout.
      DEVIATION: the four bodies + registrar all land in this commit (not split
      across WI2-4) because the registrar references all four and the module must
      import cleanly; WI2-4 add only their tests, WI5 the surface/e2e proofs.
    - [x] Work item 2: complete-final-pass convenience mutator + tests.
      DONE: unit tests (flip+check-coherent, idempotent, missing/incomplete state
      exit 3) and a pytest-bdd scenario. SURPRISE: at 60 examples the set-gate
      property perturbed the deadline-bound Hypothesis tests in
      test_state_document under xdist (DeadlineExceeded); reduced to 25 examples,
      suite now stable across repeated runs. CodeRabbit run 2: one finding (a
      first-person verdict in review-r4.md) fixed. `make all` green.
    - [x] Work item 3: set-fangirl mutator + tests.
      DONE: unit tests (in-range exit 0 + check coherent, out-of-manifest and
      negative exit 3, non-integer exit 2) and a Hypothesis property over a band
      straddling [0, N]. CodeRabbit run 3: two majors fixed (added the
      non-integer exit-2 unit test and the post-set check assertion in the
      property), plus two execplan markdown defects. `make all` green.
    - [x] Work item 4: set-critic-pass mutator + tests.
      DONE: unit tests (--pass 2 exit 0 + check coherent, --pass 0/-1 exit 3,
      non-integer exit 2) and a Hypothesis property over a band straddling 1.
      CodeRabbit run 4: all six findings were on the historical review-r1/r2/r3
      notes (prior-round records), none on the WI4 code; left untouched to
      preserve the audit trail (see Open issues). `make all` green.
    - [x] Work item 5: register the four subcommands via the registrar
      register_gate_drafting_commands(app) (Decision D11/B4), add the no-flag
      GateDraftingUsageError + _set_gate_or_usage adapter (B5/Decision D9 round 4),
      + surface tests + the real-runner no-flag exit-2 envelope test + line-count
      gate (record wc -l for novel_state.py <=399 and _gate_drafting_mutators.py
      <=400).
      DONE: registration landed with the module in WI1 (the registrar references
      all four bodies). WI5 adds the surface tests (the four subcommands present
      via build_app, the registrar wires onto a fresh app, --pass binds
      pass_number==2) and the installed e2e arms (set-gate repair exit 0, refusal
      exit 3, no-flag exit 2 envelope at the installed boundary, set-fangirl
      out-of-manifest exit 3, set-critic-pass non-integer exit 2,
      complete-final-pass exit 0). LINE-COUNT GATE (re-measured by wc -l):
      novel_state.py = 399 (<=399), _gate_drafting_mutators.py = 399 (<=400).
      `make all` green.
    - [x] Work item 6: documentation — ADR, developers' guide, users' guide,
      SKILL bridge + markdown gates.
      DONE: ADR 010 (docs/adr-010-gate-drafting-mutators.md) records the four
      command names/shapes, the exit-2/exit-3 split, the gate-ratio repair
      semantics, the write-time preconditions, D10 (general set-gate), D11 (the
      registrar pattern), the single-file no-bracket/no-receipt stance, and the
      init-receipt reconciliation note. contents.md lists ADR 010. The
      developers' guide names the four mutators, the module, and the registrar
      pattern in both the command list and the checker/mutator-segregation
      section. The users' guide documents each subcommand's options, an example
      invocation, the exit-3 refusal contract, and the gate-ratio caveat. The
      SKILL bridge routes the knitting gates, complete-final-pass,
      set-critic-pass, and set-fangirl into their phases and replaces the
      hand-edit guidance in SKILL.md and references/state-layout.md.
      make all + make markdownlint + make nixie all green.
```

## Surprises & discoveries

```plaintext
    - Observation: The locked cuprum is 0.1.0 (the PyPI wheel uv resolves), whose
      SafeCmd.run_sync is run_sync(*, capture=True, echo=False, context=None). The
      local source at /data/leynos/Projects/cuprum is a newer, unreleased version
      whose run_sync takes output: RunOutputOptions instead. The plan pins against
      the locked 0.1.0.
      Evidence: `uv run python -c "import inspect; from cuprum.sh import SafeCmd;
      print(inspect.signature(SafeCmd.run_sync))"` →
      `(self, *, capture: 'bool' = True, echo: 'bool' = False,
      context: 'ExecutionContext | None' = None)`. The existing
      tests/test_set_chapters_e2e.py line 109 calls .run_sync(context=..., capture=True),
      which only the locked form accepts.
      Impact: e2e tests must use the locked run_sync(capture=, context=) form, not
      the local-source output= form. No new cuprum capability is needed.

    - Observation: A kw-only `bool` Cyclopts parameter yields both a positive and a
      negated flag.
      Evidence: against locked Cyclopts 4.18.0, a command with `*, knitting_30: bool
      = False` parses `--knitting-30` to True and `--no-knitting-30` to False
      (verified with App.parse_args(..., exit_on_error=False)). This mirrors the
      established `_compile.py` `--check` boolean.
      Impact: set-gate exposes one `--knitting-NN`/`--no-knitting-NN` pair per
      knitting gate plus a `--final`/`--no-final` pair, no manual flag wiring.

    - Observation: S3 — a hand-raised cyclopts.ValidationError(msg=...) CANNOT be
      stringified by the runner's CycloptsError arm; it crashes the command. The
      round-3 no-flag set-gate mechanism was therefore wrong, and the correct,
      already-proven pattern is the _desloppify domain-error + adapter (exit 2
      returned directly), verified live to produce a clean exit-2 envelope through
      the real runner.run.
      Evidence: (1) `str(cyclopts.ValidationError(msg="..."))` raises
      NotImplementedError (its argument/group/command_chain are all None, so
      ValidationError._segments() reaches `else: raise NotImplementedError`
      (cyclopts/exceptions.py:258) before the base-class msg short-circuit;
      verified live via `uv run`). (2) Driving the real
      novel_ralph_skill.contract.runner.run against a make_contract_app("novel-state")
      with a set-gate wrapper that raises a GateDraftingUsageError(EnvelopeMessagesError)
      caught by an adapter returning CommandOutcome(code=ExitCode.USAGE_ERROR, ...)
      yields exit 2 and the envelope
      `{"command": "novel-state", ..., "ok": false, "result": {},
      "messages": ["set-gate requires at least one flag"]}` — no traceback (verified
      live via `uv run`).
      Impact: D9/WI1/WI5 drop ValidationError(msg=...) and adopt the
      GateDraftingUsageError + adapter pattern; the exit-2 proof is a real-runner /
      installed-binary assertion, never a subclass-hood assertion.
```

## Decision log

```plaintext
    - Decision: D1 — No new runtime dependency; reuse Cyclopts typed parameters and
      the existing _state_mutators.py shared helpers.
      Rationale: The four fields are plain bool/int scalars. Cyclopts already parses
      typed kw-only parameters (the _compile.py --check precedent), and the load /
      refuse / view helpers are already shared across mutator modules.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D2 — Command surface: set-gate (covers all four gate booleans),
      complete-final-pass (convenience), set-critic-pass, set-fangirl.
      Rationale: The roadmap names exactly these as examples ("set-gate,
      complete-final-pass, set-fangirl, set-critic-pass"). set-gate takes one
      bool per knitting gate plus the final gate, so a single mutator covers all
      gate booleans; complete-final-pass is the convenience verb the roadmap names
      for the common final-pass flip. The verbs read consistently with the
      established set-cursor / set-chapters family.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D3 — Single-file mutators open no [pending_turn] bracket and append
      no log.md receipt.
      Rationale: Each writes only state.toml via one Path.replace, exactly like
      set-cursor / advance-phase / recount (developers-guide "Checker/mutator
      segregation": single-file mutators write one Path.replace and open no
      bracket). The roadmap's "log-receipt discipline" wording is the multi-file
      mutators' contract (reconcile, set-chapters); applying it to a single-file
      mutator would diverge from every existing single-file mutator and add a write
      the atomic single-file replace does not need. If review insists on a receipt,
      that is a cross-cutting change to all single-file mutators, escalated, not
      bolted onto this task.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D4 — set-gate is the repair mutator for a gate that lags its ratio;
      it follows the set_cursor skeleton (no prior-refusal) and runs the §5.2
      validate-before-persist pass on the PROPOSED state only.
      Rationale: gate-ratio-consistent (§5.2 inv 7) binds all three knitting gates
      simultaneously, so any *coherent* prior already has each gate at its
      ratio-mandated value — from a coherent prior a flag set is a no-op (round-1
      review B1). The validator-permitted *observable* transition is therefore the
      repair of an *incoherent* prior where the ratio has crossed but the gate
      boolean still lags (e.g. recount moved the ratio past 0.30 but done_30 is
      still false). set_cursor (unlike advance-phase) does NOT call
      _refuse_if_incoherent(prior, ...): it only proves structural completeness,
      edits, and validates the proposed state. set-gate copies that skeleton, so the
      incoherent gate-lags-ratio prior is accepted, the gate is asserted to its
      mandated value, and the now-coherent proposed state writes. A set that
      contradicts the ratio (true below threshold, or false above it) makes the
      proposed state incoherent and is refused with exit 3. From an already-coherent
      prior, an assertion of the mandated value is an idempotent no-op exiting 0.
      This is the *correct* behaviour, not a limitation to route around (design
      §5.2; state-layout.md "Gates": the gate flips true "after the pass is
      integrated and logged"). The body must NOT add a prior-refusal guard.
      Date/Author: 2026-06-25, planning agent (revised round 2 for B1).

    - Decision: D5 — No change to validate_state or the §5.2 invariant set.
      Rationale: All four fields are either already §5.2-constrained
      (knitting gates via inv 7) or unconstrained by §5.2 (final_pass_complete,
      critic.pass, fangirl.last_chapter_passed). The unconstrained fields get
      write-time preconditions in their own bodies (Decision D6), mirroring
      set-chapters' manifest_coherence_violations, not new validator rules. Changing
      validate_state would change check for every existing tree (the ADR 008
      rationale against folding write-time rules into validate_state).
      Date/Author: 2026-06-25, planning agent.

    - Decision: D6 — Write-time preconditions for the §5.2-unconstrained fields.
      Rationale: set-fangirl requires 0 <= last_chapter <= len(chapters) (a fangirl
      pass cannot have run on a chapter the manifest does not contain; 0 means no
      pass yet). set-critic-pass requires pass >= 1 (passes are numbered from 1;
      state-layout.md "Critic sub-state"). These are write-time preconditions the
      §5.2 set does not own, owned in the mutator body exactly as set-chapters owns
      manifest coherence (ADR 008 "a new pure predicate ... not an addition to
      validate_state"). Each precondition refusal is exit 3, named in messages.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D7 — A new ADR (ADR 010) records the command surface and the gate
      semantics.
      Rationale: Task 2.2.3's precedent (ADR 008) recorded its mutator's input
      shape and behaviour as an ADR, and the roadmap's 2.2.4 success wording mirrors
      it. ADR 010 records: the four command names and input shapes, the exit-2/exit-3
      split, the gate-ratio binding on set-gate (the one non-obvious semantic), and
      the write-time preconditions for the unconstrained fields. It is the durable
      home for "why can't set-gate just flip the flag".
      Date/Author: 2026-06-25, planning agent.

    - Decision: D8 — Work item 1 builds three custom WorkingTreeSpec fixtures; it
      does NOT reuse PHASE_STATES["drafting"]/COHERENT_BASELINE.
      Rationale: COHERENT_BASELINE has drafted total 68800/80000 = 0.86 with all
      three knitting gates already true (tests/working_corpus/_library.py:41-42,
      60-64), so it cannot show an observable flip (round-1 review B2). The corpus
      ships no sub-threshold or gate-lagging baseline, but WorkingTreeSpec exposes
      done_30/done_50/done_80 and per-chapter draft_words/target_words explicitly,
      so each fixture is constructible exactly as _gate_true_below_threshold builds
      its incoherent variant (_variants.py:80-96). The three fixtures —
      gate_lags_ratio (0.45 ratio, all gates false: incoherent repair prior),
      ratio_not_crossed (0.15 ratio, all gates false: coherent), and
      ratio_crossed_coherent (0.45 ratio, done_30 true: coherent) — are named in
      Work item 1. The Hypothesis strategy builds the tree from drawn draft_words +
      a gate-boolean triple and requires (via event()/target) at least one
      observable flip so the property cannot pass vacuously.
      Date/Author: 2026-06-25, planning agent (round 2, B2 + pre-mortem signal 3).

    - Decision: D9 — A no-flag set-gate invocation is exit 2 (usage), realised by a
      domain GateDraftingUsageError + a thin adapter that returns an exit-2
      CommandOutcome directly; NOT by raising cyclopts.ValidationError(msg=...).
      Rationale: naming no field to change is a usage error, which ADR 003 routes to
      the exit-2 channel, not the state-semantics exit-3 channel. The round-3
      mechanism (raise cyclopts.ValidationError(msg=...) in the wrapper and rely on
      runner.py:225-232 mapping CycloptsError -> exit 2 via messages=[str(exc)]) is
      WRONG and crashes the runner (round-3 reviewer B5; Surprise S3, verified live).
      A bare hand-raised ValidationError(msg=...) has argument/group/command_chain all
      None, so ValidationError._segments() (cyclopts/exceptions.py:229-265) reaches
      its final `else: raise NotImplementedError` (line 258) before the base-class msg
      short-circuit (exceptions.py:160) is ever consulted; str(exc) therefore raises
      NotImplementedError INSIDE the runner's exception handler (runner.py:230),
      producing an uncaught traceback and a non-contract exit — the opposite of the
      clean exit-2 envelope. The class IS a CycloptsError subclass and propagation
      holds, but stringification does not; subclass-hood was never the load-bearing
      fact. Resolution (the proven precedent): the desloppify command already detects
      a body-level usage fault, raises a DOMAIN exception
      DesloppifyUsageError(EnvelopeMessagesError) (_desloppify.py:69), and a thin
      adapter _scan_or_usage (_desloppify.py:315-345) catches it and returns
      CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or
      [str(exc)]) DIRECTLY, never via the runner's str(CycloptsError) arm. set-gate
      copies this exactly: a new domain exception
      GateDraftingUsageError(EnvelopeMessagesError) is raised in the registered
      set_gate wrapper when "no flag is not None", and a thin adapter
      _set_gate_or_usage(...) catches it and returns the exit-2 CommandOutcome. The
      adapter (not the runner) owns the exit-2 envelope, so str() is never called on a
      CycloptsError. StateInputError cannot be reused: it maps to exit 3
      (runner.py:233-239), not exit 2. Verified live driving the REAL runner.run: the
      no-flag set-gate exits 2 with the envelope `{"command": "novel-state", ...,
      "ok": false, "result": {}, "messages": ["set-gate requires at least one
      flag"]}` and no traceback (Surprise S3). WI1's no-flag unit test and WI5's
      no-flag e2e arm MUST demonstrate the exit-2 envelope by running the real
      runner.run / installed binary, never by asserting subclass-hood.
      Date/Author: 2026-06-25, planning agent (round 2, A4; round 3, A6 class pin;
      round 4 rewrite, B5: drop ValidationError(msg=...) for the domain-error +
      adapter pattern, verified through the real runner.run).

    - Decision: D10 — Keep the general multi-flag set-gate; do not split into
      per-gate complete-knitting-NN verbs.
      Rationale: Wafflecat's round-1 alternative (four zero-argument
      complete-knitting-30/50/80 + complete-final-pass idempotent verbs) sidesteps
      the bool | None machinery, but the roadmap names "set-gate" explicitly and the
      single mutator covers all four gate booleans (including the false direction a
      repair could in principle need) with one body and one registration, staying
      closer to the established set-cursor/set-chapters family. The repair semantics
      (D4) and the fixture recipe (D8) remove the no-op/incoherent-prior ambiguity
      that motivated the alternative, so the general form is retained. This trade-off
      is recorded in ADR 010 so the choice is auditable. Round-3 advisory: the false
      direction (--no-knitting-NN) the bool|None flags expose can never legitimately
      WRITE false above threshold (the validator refuses it) and is already false
      below threshold, so on the happy path it is only ever a refusal or a no-op. It
      is retained for symmetry and tested for the refusal arm (ratio_crossed_coherent
      --no-knitting-30 -> exit 3, WI1); ADR 010 notes it is intentional symmetry, not
      a supported "turn a gate off" operation, so a reader does not mistake it
      (review-r2 Wafflecat second alternative).

    - Decision: D11 — The four subcommand registrations live in a registrar function
      register_gate_drafting_commands(app) in _gate_drafting_mutators.py, NOT in
      build_app, to keep novel_state.py under the 400-line cap (B4).
      Rationale: novel_state.py is 399 of 400 lines (verified by wc -l). Defining four
      @app.command wrappers in build_app would add ~35-45 lines (measured against the
      6-line set-chapters/recount wrappers) plus two docstring expansions — an
      immediate cap breach and a trip of the plan's own Tolerance. make_contract_app
      returns a plain cyclopts.App (runner.py:75-81) and @app.command registers a
      decorated function onto any App instance regardless of which module defines it,
      so the four wrappers (set_gate with its no-flag GateDraftingUsageError guard
      routed through the _set_gate_or_usage adapter, Decision D9 round-4 rewrite,
      complete_final_pass, set_fangirl, set_critic_pass with
      Annotated[int, Parameter(name="--pass")]) are defined inside
      register_gate_drafting_commands(app) in the new module and applied to the app
      build_app passes in. build_app gains exactly two lines: a deferred import
      (from novel_ralph_skill.commands import _gate_drafting_mutators) and the call
      (_gate_drafting_mutators.register_gate_drafting_commands(app)), mirroring the
      deferred-import no-cycle pattern recount/set-chapters already use. The import
      must stay deferred because _gate_drafting_mutators imports the shared helpers
      from _state_mutators, which imports from novel_state at module top
      (_state_mutators.py:35-44); a module-top import in novel_state would close the
      cycle. The four-subcommand docstring lives on the registrar, not on
      novel_state.py; build_app's existing seven-name enumeration is extended in place
      and the two long build_app/module docstrings are condensed by >=2 lines so the
      post-change count is <=399 (re-measured by wc -l in WI5 as that work item's
      acceptance gate). This removes the registration-site cap pressure structurally,
      before code, not by runtime escalation.
      Date/Author: 2026-06-26, planning agent (round 3, B4).
```

## Outcomes & retrospective

To be completed at milestones and at completion. Compare the result against the
Purpose: every gate and drafting sub-state field settable through a command, no
hand-edit required, check coherent across the mutations, behavioural + e2e
tests per mutator.

Completion (2026-06-26). All six work items landed against the Purpose. The four
fields are each settable through a validated `novel-state` subcommand; `set-gate`
repairs a knitting gate that lags its ratio (incoherent→coherent, exit 0) and is
an idempotent no-op from a coherent prior; `complete-final-pass`, `set-fangirl`,
and `set-critic-pass` write their field with `check` staying coherent;
ratio-contradicting/out-of-manifest/below-one sets are exit 3 with the file
unchanged; the no-flag `set-gate` and a non-integer `--pass`/`--last-chapter` are
exit 2. The SKILL bridge replaces every hand-edit instruction for these fields.
`make all`, `make markdownlint`, and `make nixie` are green at the final commit.

Deviation from the WI ordering: the four bodies + the registrar landed together
in the WI1 commit (the registrar references all four and the module must import
cleanly), so WI2-4 added only their tests and WI5 added the surface/e2e proofs.
The deterministic gates were green at every commit.

Lesson: a CPU-heavy Hypothesis property co-scheduled under `pytest-xdist` can push
*other* deadline-bound Hypothesis tests over their default 200ms deadline
(observed against `test_state_document`). Keeping the new properties at 25 examples
removed the perturbation; a future property near this boundary should set a modest
`max_examples` rather than assume the default deadline survives parallel load.

Open issue carried: CodeRabbit (run 4) flagged six items entirely within the
prior-round review notes (`roadmap-2-2-4.review-r1/r2/r3.md`) — stale line counts,
an exit-code left open at that round, a verdict a later round reopened. These are
append-only historical records of how the plan evolved; rewriting them to match
the final state would falsify the audit trail, so they are left as written. None
touched the implementation. The only review-file edits made were a first-person
verdict rewrite (r4, en-GB pronoun rule) and an MD040 fenced-code language tag
(r3), both cosmetic and substance-preserving.

## Context and orientation

The reader needs no prior plan. This section names every file by full path.

### What these mutators write

`working/state.toml` is the harness's primary on-disk memory. Its typed shape
is in `novel_ralph_skill/state/schema.py`:

- `Gates` → `KnittingGates(done_30, done_50, done_80: bool)` and
  `FinalGate(final_pass_complete: bool)`.
- `Drafting` → `CriticState(pass_number: int, ...)` (on-disk key `pass`) and
  `FangirlState(last_chapter_passed: int)`.

The on-disk keys (verbatim, what the bodies edit in the `tomlkit` document) are:
`[gates.knitting].done_30/done_50/done_80`,
`[gates.final].final_pass_complete`, `[drafting.critic].pass`,
`[drafting.fangirl].last_chapter_passed`. Note the critic key on disk is
`pass`, not `pass_number` (the schema renames it because `pass` is a Python
keyword; `schema.py:CriticState`).

### How the existing mutators work (the pattern to copy)

`novel_ralph_skill/commands/_state_mutators.py` holds `set_cursor` and
`advance_phase` plus the shared helpers every mutator reuses:

- `_load_document_or_state_error(path)` → loads the `tomlkit` document, mapping
  faults to exit 3 under `STATE_INPUT_ERRORS`.
- `_state_view_or_state_error(document)` → derives the typed `State` read view
  via
  `document_to_state`, mapping structural-incompleteness faults to exit 3. The
  mutators **never** call bare `document_to_state` (a structurally incomplete
  but valid-TOML file would otherwise exit 1, breaching the exit-3 contract).
- `_refuse_if_incoherent(state, *, context)` → runs `validate_state` and raises
  `StateInputError` (exit 3) naming the breached §5.2 invariants when non-empty.
- `_state_path` / `_working_dir` → re-exported single path accessors.

`set_cursor` (the closest template) is: load document → derive view (prove
structural completeness) → edit `[drafting]` scalars in place → derive proposed
view → `_refuse_if_incoherent` → write atomically → return a write-shaped
`CommandOutcome`. The four new mutators follow this skeleton exactly, swapping
the edited fields and the write-time precondition.

`novel_ralph_skill/commands/_set_chapters.py` is the precedent for a mutator
that owns a **write-time precondition** the §5.2 validator does not
(`manifest_coherence_violations`) and lives in its own module to respect the
400-line cap, reusing `_state_mutators.py`'s shared helpers. The new module
mirrors its structure.

### Registration

`novel_ralph_skill/commands/novel_state.py:build_app()` is the Cyclopts app
builder. It registers each subcommand with `@app.command`. Mutator bodies are
imported with a **deferred import inside `build_app`** (e.g.
`from novel_ralph_skill.commands import _recount`) to avoid the
`_state_mutators` → `novel_state` import cycle. The same pattern registers the
four new subcommands.

For a `bool` parameter, Cyclopts derives a `--flag`/`--no-flag` pair (verified
against locked Cyclopts 4.18.0). For an `int` parameter it derives `--name`.
`@app.command(name="set-gate")` overrides the auto-derived (underscore→hyphen)
name when needed; the existing `set-chapters` registration uses this form.

### The contract runner

`novel_ralph_skill/contract/runner.py` owns `run`, `CommandOutcome`,
`StateInputError`, and the exit-code mapping. A body returns a `CommandOutcome`
on success; `run` catches `StateInputError` → exit 3 and `CycloptsError` (a
parse/coercion fault) → exit 2. The bodies raise `StateInputError`; they never
touch exit codes directly.

### Validation surface

`novel_ralph_skill/state/validate.py:validate_state` is the §5.2 pure-state
validator. `_check_gate_ratio_consistent` and `GATE_THRESHOLDS`
(0.30/0.50/0.80) are the gate-ratio binding `set-gate` is subject to. **Do not
modify this file** (Tolerance "Validator change").

### Tests and corpora

- `tests/test_novel_state_mutators.py` — the command-contract harness for
  `init`/`set-cursor`/`advance-phase` (a `_run_mutator` driver through `run`
  plus a `_capture_envelope` reader). The new mutators' contract tests extend
  this pattern (or a sibling module if size demands).
- `tests/working_corpus/` (`build_working_tree`, `PHASE_STATES`,
  `COHERENT_BASELINE`) builds throwaway `working/` trees per phase for
  behavioural and e2e fixtures. `PHASE_STATES["drafting"]` and
  `PHASE_STATES["final-pass"]` are the relevant baselines.
- `tests/installed_binary_fixtures.py` — the module-scoped
  `installed_novel_state`
  fixture that builds a wheel, installs it into a fresh `uv` venv, and returns
  the installed `novel-state` console-script path. e2e tests drive it through
  cuprum (`sh.make(prog, catalogue=...)(...).run_sync(context=...,
  capture=True)`), POSIX-only per ADR 006.
- `tests/features/` holds the `pytest-bdd` `.feature` files; the new behavioural
  scenarios add `.feature` files here with step bindings in a `test_*_bdd.py`
  module, mirroring `advance_phase_refusal.feature` /
  `tests/test_advance_phase_bdd.py`.

### Pinned external-library behaviour (verified, not assumed)

- cuprum 0.1.0 (locked): `Program(str)` accepts an absolute path and
  `str(program)`
  returns it verbatim; `ProgramCatalogue(projects=...)`,
  `ProjectSettings(name, programs, documentation_locations, noise_rules)`;
  `sh.make(program, *, catalogue=...)` → builder → `SafeCmd`;
  `SafeCmd.run_sync(*, capture=True, echo=False, context=None)` →
  `CommandResult` with `exit_code`, `stdout`, `stderr`, `ok`;
  `ExecutionContext(cwd=...)`. Verified by
  `uv run python -c "import inspect, dataclasses; ..."` against the resolved
  wheel. The new e2e tests reuse the existing fixture and call form verbatim —
  no new cuprum API is exercised.
- Cyclopts 4.18.0 (locked): a kw-only `bool` parameter yields `--flag` and
  `--no-flag`; a kw-only `int` parameter yields `--name` and coerces a
  non-integer argument to a `CoercionError` (mapped to exit 2 by the runner).
  Verified by
  `App.parse_args(["set-gate","--knitting-30"], exit_on_error=False)`.
- pytest-timeout 2.4.0 (locked): the per-test `@pytest.mark.timeout(N)` marker
  is
  the highest-priority override and supersedes the `pyproject.toml`
  `timeout = 30` default for that test, including under `pytest-xdist` (each
  worker is a full pytest process applying the marker per item). Documented at
  <https://pypi.org/project/pytest-timeout/> ("a decorator to set the timeout
  for an individual test … will override the timeout"). The slow wheel-build
  e2e cases carry `@pytest.mark.timeout(180)`, as `test_set_chapters_e2e.py`
  does.

## Plan of work

Six ordered, independently committable work items. Each ends with `make all`
green; the documentation item adds `make markdownlint` and `make nixie`. Stage
each work item red→green: add the failing test(s) first, then the body, then
register (Work item 5 makes the registration tests pass; before it, the new
subcommands are unreachable and their installed-e2e cases are marked
`xfail(strict=True)` or deferred to Work item 5, mirroring how
`test_novel_state_mutators.py` records the 2.2.2 staging).

### Work item 1: `set-gate` mutator (knitting + final gate flags)

Implements: roadmap 2.2.4 (gate flags); design §4.1, §5.1, §5.2 bullet 7; ADR
001.

Create `novel_ralph_skill/commands/_gate_drafting_mutators.py`. Add the body
`_set_gate` (the leading underscore marks it as the private body the WI5
registrar wrapper calls; the wrapper carries the `@app.command` name and the
no-flag guard, Decision D11):

```python
def _set_gate(
    *,
    knitting_30: bool | None = None,
    knitting_50: bool | None = None,
    knitting_80: bool | None = None,
    final: bool | None = None,
) -> CommandOutcome:
    ...
```

Body skeleton (copying `set_cursor` — which does **not** refuse an incoherent
prior): load document → derive view (prove structural completeness, discard it)
→ for each non-`None` argument edit the matching on-disk key
(`document["gates"]["knitting"]["done_30"]` etc.,
`document["gates"]["final"] ["final_pass_complete"]`) → derive the proposed
view → `_refuse_if_incoherent(..., context="set-gate")` →
`write_document_atomically` → return a write-shaped `CommandOutcome` whose
`result` names the gates set (e.g.
`{"gates": {"knitting": {"done_30": true}, "final": {"final_pass_complete": ...}}}`,
only the keys actually changed). The body must **not** call
`_refuse_if_incoherent(prior, ...)` (that is `advance-phase`'s guard, which
would forbid the repair path); it validates only the proposed state, exactly as
`set_cursor` does.

Use `bool | None = None` so an omitted flag leaves the field untouched (a
partial gate update); Cyclopts renders each as `--knitting-30`/
`--no-knitting-30` etc.

**No-flag invocation is exit 2, not exit 3 — via a domain error + adapter, NOT
`cyclopts.ValidationError(msg=...)` (B5 resolution; Decision D9 round-4
rewrite).** A `set-gate` with no flag supplied is a *usage* error — the
operator named no field to change — and usage errors are the exit-2 channel,
consistent with ADR 003's exit-2 "shape/usage" vs exit-3 "state semantics"
split. The Cyclopts parser cannot catch it (a no-flag `set-gate` parses cleanly
to `{}`; verified live), so it is routed to exit 2 exactly as `desloppify`
routes its body-detected usage faults: add a domain exception
`GateDraftingUsageError(EnvelopeMessagesError)` to `_gate_drafting_mutators.py`
and a thin adapter `_set_gate_or_usage(...)` (mirroring
`_desloppify.py:DesloppifyUsageError` + `_scan_or_usage`, lines 69 and
315-345). The WI5 registrar wrapper for `set-gate` checks "at least one flag is
not `None`" and, if none is, raises
`GateDraftingUsageError("set-gate requires at least one flag")`; the adapter
catches it and returns
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)])`
**directly**, never routing through the runner's `str(CycloptsError)` arm.
**Do not raise `cyclopts.ValidationError(msg=...)`**: a bare hand-raised
`ValidationError(msg=...)` has `argument/group/command_chain` all `None`, so
`str(exc)` raises `NotImplementedError` inside `runner.py:230` and crashes the
command with a traceback (Surprise S3; verified live driving the real
`runner.run`). `StateInputError` is also wrong here — it maps to exit 3. The
guard and the adapter live in the wrapper/adapter, not the `_set_gate` body, so
the body's exit-3 channel is reserved for ratio-contradicting sets.

The §5.2 `gate-ratio-consistent` pass means asserting a knitting gate true
while its ratio is below threshold, or false after it has crossed, is refused
with exit 3 — the Constraint. `final_pass_complete` has no §5.2 binding, so
`--final` is accepted on any structurally complete prior.

Fixture construction (B2 resolution — the corpus has **no** ready sub-threshold
or gate-lagging baseline; build each with a custom `WorkingTreeSpec`). The named
`PHASE_STATES["drafting"]` / `COHERENT_BASELINE` has drafted total 68800/80000
= 0.86 with all three gates already `true`
(`tests/working_corpus/_library.py:41-42,60-64`), so it cannot exercise an
observable flip. Construct fixtures directly via
`tests.working_corpus.WorkingTreeSpec` + `build_working_tree`, mirroring the
existing `_gate_true_below_threshold` variant
(`tests/working_corpus/_variants.py:80-96`, which shrinks chapter `draft_words`/
`target_words` to move the ratio and sets the gate booleans explicitly). The
three WI1 fixtures are:

- **`gate_lags_ratio` (the repair happy path; incoherent prior).** Three
  chapters with `draft_words=12000` each (36000/80000 = 0.45: crosses 0.30, not
  0.50/0.80), `target_words=80000`, with
  `done_30=False, done_50=False, done_80=False`. This prior is **incoherent**
  (invariant 7: 0.45 mandates `done_30=True`). `set-gate --knitting-30` flips
  `done_30` true → the proposed state is coherent (0.45 ≥ 0.30 true, < 0.50
  false, < 0.80 false) → exits 0, writes `done_30 = true`, and a follow-up
  `check` exits 0. This is the observable incoherent→coherent flip; it is the
  value of the command.
- **`ratio_not_crossed` (the contradicting set; coherent prior).** Three
  chapters
  with `draft_words=4000` each (12000/80000 = 0.15: below every threshold) and
  all three gates `False` — a **coherent** prior. `set-gate --knitting-30`
  asserts `done_30=True` on a ratio of 0.15 → the proposed state is incoherent
  → exits 3 naming `gate-ratio-consistent`, `state.toml` byte-for-byte
  unchanged.
- **`ratio_crossed_coherent` (idempotent no-op + false-after-crossed refusal;
  coherent prior).** The `gate_lags_ratio` chapter words (0.45) but with
  `done_30=True, done_50=False, done_80=False` — a **coherent** prior.
  `set-gate --knitting-30` re-asserts `done_30=True` → proposed state still
  coherent → exits 0 idempotently (same bytes for that field).
  `set-gate --no-knitting-30` on this prior asserts `done_30=False` on a
  crossed ratio → proposed incoherent → exits 3. `--final` asserts
  `final_pass_complete=True` here → exits 0, `check` coherent (no §5.2 binding
  on the final gate).

Tests (this item, all in `tests/test_set_gate_*.py`):

- **Unit / contract** (`test_set_gate_unit.py`), in this order (refusal pinned
  first, the Constraint):
  - **Refusal:** on the `ratio_not_crossed` fixture, `set-gate --knitting-30`
    exits 3 naming `gate-ratio-consistent`; `state.toml` is byte-for-byte
    unchanged.
  - **False-after-crossed refusal:** on `ratio_crossed_coherent`,
    `set-gate --no-knitting-30` exits 3.
  - **Repair happy path:** on `gate_lags_ratio`, `set-gate --knitting-30`
    exits 0, writes `done_30 = true`, follow-up `check` exits 0 (observable flip).
  - **Idempotent no-op:** on `ratio_crossed_coherent`, `set-gate --knitting-30`
    exits 0 and re-writes the same `done_30 = true`.
  - **Final gate:** on `ratio_crossed_coherent`, `--final` flips
    `final_pass_complete` true and `check` stays coherent.
  - **No-flag:** `set-gate` with no flag exits 2 (usage), file unchanged. This
    test MUST drive the **real** `runner.run` (the `_run_mutator` driver through
    `run`, exactly as the other contract tests do) and assert the emitted envelope
    is `ok: false`, exit 2, with the no-flag message in `messages` and no
    traceback — proving the `GateDraftingUsageError` + `_set_gate_or_usage` adapter
    produces the clean exit-2 envelope (B5; Surprise S3). It must **not** merely
    assert `issubclass(...)` or that an exception propagates; that is the
    memory-vs-verified gap B5 caught. (A bare `cyclopts.ValidationError(msg=...)`
    would instead crash `str(exc)` inside `runner.py:230` — this test would catch
    that regression.)
- **Property** (`test_set_gate_properties.py`, Hypothesis): the strategy draws
  the three chapter `draft_words` (so `drafted_total/80000` lands in a
  controlled range) and an independent gate-boolean triple, then builds the
  tree with `WorkingTreeSpec(..., done_30=b0, done_50=b1, done_80=b2)` +
  `build_working_tree` (the prior may be coherent or not — `set-gate` does not
  refuse the prior). It then chooses a flag set equal to the proposed coherent
  triple `(ratio>=0.30, ratio>=0.50, ratio>=0.80)` and asserts `set-gate` exits
  0 and the written state is coherent; a flag set that contradicts the ratio
  asserts exit 3 and an unchanged file. To avoid a vacuous pass (Doggylump
  pre-mortem signal 3), the property uses `hypothesis.event()` /
  `hypothesis.target` to record and require at least one generated case where
  the flag set actually changes a gate value from the prior (an observable
  flip), so the strategy is not silently degenerate. This pins "set-gate
  accepts exactly the ratio-consistent flag set, and the repair flip is
  reachable".
- **Snapshot** (`test_set_gate_snapshots.py`, syrupy): the success envelope's
  write-shaped `result` for a representative `--knitting-30` success, with the
  volatile fields redacted (no timestamps in this envelope). Keep it to the
  `result`, not the whole envelope.

Docs to read: design §4.1, §5.2 (bullet 7);
`validate.py:_check_gate_ratio_consistent` (lines 250-278); `GATE_THRESHOLDS`;
`_state_mutators.py:set_cursor` (lines 176-234, the no-prior-refusal skeleton —
contrast `advance_phase`, lines 268-325, which DOES refuse the prior, the wrong
pattern here); `skill/novel-ralph/references/state-layout.md` "Gates" (A7 — the
file is under `skill/novel-ralph/references/`, not `docs/`). Fixture
construction: `tests/working_corpus/_specs.py:WorkingTreeSpec` (the `done_30`/
`done_50`/`done_80` + per-chapter `draft_words` fields) and
`tests/working_corpus/_variants.py:_gate_true_below_threshold` (lines 80-96,
the ratio-shrinking + explicit-gate pattern to copy). Skills: `python-router` →
`python-data-shapes` (the bool/int parameter shapes), `python-testing`
(snapshot plus parametrization); `python-verification` → `hypothesis` (the
ratio-consistency property and the `event()`/`target` anti-vacuity guard);
`leta` for navigation; `grepai` for search.

Validation: `make all`.

### Work item 2: `complete-final-pass` convenience mutator

Implements: roadmap 2.2.4 (`complete-final-pass` named example); design §4.1,
§5.1.

Add the body `_complete_final_pass()` to `_gate_drafting_mutators.py` (private,
called by the WI5 registrar wrapper `complete_final_pass`; Decision D11): a
zero-argument mutator that flips `[gates.final].final_pass_complete` true. It
is the convenience verb for the common final-pass flip (set-gate `--final` is
the general form; complete-final-pass is the named, argument-free idiom the
roadmap calls out and the agent runs at the end of the final-pass phase). Same
skeleton: load → view → edit → refuse-if-incoherent → write → write-shaped
`result` (`{"gates": {"final": {"final_pass_complete": true}}}`). Idempotent:
re-running on an already-true state re-writes the same value and exits 0 (no
precondition forbids it; `final_pass_complete` has no §5.2 binding).

Tests (`tests/test_complete_final_pass_*.py`):

- **Unit / contract**: on a `final-pass`-phase tree, `complete-final-pass`
  exits 0, writes `final_pass_complete = true`, and `check` stays coherent; a
  second run is idempotent (same bytes for that field). A
  missing/structurally-incomplete `state.toml` exits 3.
- **Behavioural (pytest-bdd)** `tests/features/complete_final_pass.feature` +
  `tests/test_complete_final_pass_bdd.py`: "Given a coherent final-pass tree /
  When complete-final-pass runs / Then it exits 0 and final_pass_complete is
  true and check exits 0". This is the named-command behavioural proof the
  roadmap success criterion wants.

Docs: design §4.1; `skill/novel-ralph/references/state-layout.md` "Gates"
(`final_pass_complete` flips at the end of Phase 9). Skills: `python-router` →
`python-testing`; `python-router`'s pytest guidance for the `pytest-bdd`
scenario; `leta`/`grepai`.

Validation: `make all`.

### Work item 3: `set-fangirl` mutator

Implements: roadmap 2.2.4 (`drafting.fangirl.last_chapter_passed`); design
§4.1, §5.1; ADR 008 precedent (write-time precondition).

Add the body `_set_fangirl(*, last_chapter: int)` to
`_gate_drafting_mutators.py` (private, called by the WI5 registrar wrapper
`set_fangirl`; Decision D11). Edit `[drafting.fangirl].last_chapter_passed`.
Write-time precondition (Decision D6): `0 <= last_chapter <= len(chapters)` — a
fangirl pass cannot have run on a chapter the manifest does not contain; `0`
means no pass yet. The precondition is a small pure check in the body (mirroring
`set-chapters`' `manifest_coherence_violations`), refusing with exit 3 and
naming the breached rule (e.g. `fangirl-chapter-in-manifest`) in `messages`,
**before** the §5.2 validate-before-persist pass. Then run the §5.2 pass for
defence in depth, write, and return
`{"drafting": {"fangirl": {"last_chapter_passed": last_chapter}}}`.

Tests (`tests/test_set_fangirl_*.py`):

- **Unit / contract**: on a `drafting` tree with N manifest chapters,
  `set-fangirl --last-chapter k` for `0 <= k <= N` exits 0 and `check` stays
  coherent; `--last-chapter (N+1)` and `--last-chapter -1` each exit 3 naming
  the precondition, file unchanged. A non-integer argument exits 2 (the parser
  channel, pinned at the installed boundary in Work item 5).
- **Property** (`test_set_fangirl_properties.py`, Hypothesis): for a coherent
  baseline with N chapters and `k` drawn in `[0, N]`, `set-fangirl` exits 0 and
  the result is coherent; for `k` outside `[0, N]`, exit 3 and the file is
  unchanged.

Docs: design §4.1, §5.1; `skill/novel-ralph/references/state-layout.md`
"Drafting sub-state" (fangirl); ADR 008 (write-time precondition precedent);
`_set_chapters.py:manifest_coherence_violations`. Skills: `python-router` →
`python-data-shapes`, `python-testing`; `python-verification` → `hypothesis`;
`leta`/`grepai`.

Validation: `make all`.

### Work item 4: `set-critic-pass` mutator

Implements: roadmap 2.2.4 (`drafting.critic.pass`); design §4.1, §5.1; ADR 008
precedent.

Add the body `_set_critic_pass(*, pass_number: int)` to
`_gate_drafting_mutators.py` (private, called by the WI5 registrar wrapper
`set_critic_pass`; Decision D11). The parameter is `pass_number` because `pass`
is a Python keyword; the WI5 wrapper exposes the CLI flag as `--pass` via the
explicit `cyclopts.Parameter(name="--pass")` annotation. Edit the on-disk
`[drafting.critic].pass` key. Write-time precondition (Decision D6):
`pass >= 1` (passes are numbered from 1; state-layout.md "Critic sub-state").
Refuse a `pass < 1` with exit 3 naming the rule (e.g.
`critic-pass-at-least-one`) before the §5.2 pass. Then the §5.2
validate-before-persist pass (defence in depth — the critic sub-rules bound
`consecutive_clean`/`convergence_target`, not `pass`, so a coherent prior stays
coherent), write, and return `{"drafting": {"critic": {"pass": pass_number}}}`.

Tests (`tests/test_set_critic_pass_*.py`):

- **Unit / contract**: on a `drafting` tree, `set-critic-pass --pass 2` exits 0,
  writes `pass = 2`, `check` stays coherent; `--pass 0` and `--pass -1` exit 3
  naming the precondition, file unchanged.
- **Property** (`test_set_critic_pass_properties.py`, Hypothesis): for a
  coherent
  baseline and `p >= 1`, `set-critic-pass --pass p` exits 0 and the result is
  coherent (the critic §5.2 sub-rules are unaffected by `pass`); for `p < 1`,
  exit 3 and the file is unchanged.

Docs: design §4.1, §5.1; `skill/novel-ralph/references/state-layout.md` "Critic
sub-state"; `schema.py:CriticState` (the `pass` → `pass_number` rename). Skills:
`python-router` → `python-data-shapes`, `python-testing`;
`python-verification` → `hypothesis`; `leta`/`grepai`.

Validation: `make all`.

### Work item 5: register the four subcommands + surface and e2e tests

Implements: roadmap 2.2.4 (reachability); design §4.1; ADR 003 (the shared
contract); ADR 006 (POSIX e2e policy); AGENTS.md 400-line cap (Decision D11/B4).

**Registration lives in a registrar, not in `build_app` (B4 resolution;
Decision D11).** `novel_state.py` is 399 of 400 lines (verified by `wc -l`), so
defining four `@app.command` wrappers in `build_app` (~35-45 lines plus two
docstring expansions, measured against the 6-line `set-chapters`/`recount`
wrappers) would breach the cap on landing. Instead, add a registrar function to
`_gate_drafting_mutators.py`:

```python
def register_gate_drafting_commands(app: cyclopts.App) -> None:
    """Register the four gate/drafting subcommands on ``app`` (design §4.1)."""

    @app.command(name="set-gate")
    def set_gate(
        *,
        knitting_30: bool | None = None,
        knitting_50: bool | None = None,
        knitting_80: bool | None = None,
        final: bool | None = None,
    ) -> CommandOutcome:
        """Assert gate booleans to their ratio-mandated value; refuse a
        contradicting set with exit 3, a no-flag call with exit 2."""
        return _set_gate_or_usage(
            knitting_30=knitting_30,
            knitting_50=knitting_50,
            knitting_80=knitting_80,
            final=final,
        )

    @app.command(name="complete-final-pass")
    def complete_final_pass() -> CommandOutcome:
        """Flip ``gates.final.final_pass_complete`` true (idempotent)."""
        return _complete_final_pass()

    @app.command(name="set-fangirl")
    def set_fangirl(*, last_chapter: int) -> CommandOutcome:
        """Set ``drafting.fangirl.last_chapter_passed``; refuse out-of-manifest."""
        return _set_fangirl(last_chapter=last_chapter)

    @app.command(name="set-critic-pass")
    def set_critic_pass(
        *,
        pass_number: typing.Annotated[int, cyclopts.Parameter(name="--pass")],
    ) -> CommandOutcome:
        """Set ``drafting.critic.pass``; refuse ``pass < 1`` with exit 3."""
        return _set_critic_pass(pass_number=pass_number)
```

Here `_set_gate`/`_complete_final_pass`/`_set_fangirl`/`_set_critic_pass` are
the private body functions added in WI1-4 (rename the bodies with a leading
underscore, or keep the public names and call them — the registrar wrappers
carry the `@app.command` names and the no-flag guard, the bodies carry the
validate-persist logic). The registrar and the four bodies all live in
`_gate_drafting_mutators.py`; the module also imports `cyclopts` and `typing`
(the body module already imports the shared helpers, so these two are the only
new imports, and they sit on the new module, not on `novel_state.py`).

**`build_app` gains exactly two lines** (Decision D11): a deferred import and
the registrar call, mirroring the deferred-import no-cycle pattern `recount`/
`set-chapters` already use (the import must stay deferred because
`_gate_drafting_mutators` -> `_state_mutators` -> `novel_state` would otherwise
cycle, `_state_mutators.py:35-44`):

```python
    # ... after the existing set-chapters registration, before `return app`:
    from novel_ralph_skill.commands import _gate_drafting_mutators

    _gate_drafting_mutators.register_gate_drafting_commands(app)
    return app
```

**Line budget for `novel_state.py` (B4 acceptance gate).** Adding the two
functional lines takes the file to 401, which breaches the cap, so WI5 also
condenses the two long docstrings (the module docstring, lines 1-40, and the
`build_app` docstring, lines 322-345) by **at least four lines** net so the
post-change `wc -l novel_ralph_skill/commands/novel_state.py` is **<=399**. The
`build_app` enumeration clause ("Exposes the read-only `check` … and the
`set-chapters` … mutator") is extended in place to name the four new
subcommands (a one-clause edit, not a multi-line block), and the redundant
Returns-section re-enumeration is trimmed to "and the gate/drafting mutators
(`set-gate`, `complete-final-pass`, `set-fangirl`, `set-critic-pass`)" — naming
without re-describing. **WI5 is not complete until `wc -l` reports <=399 for
`novel_state.py` and <=400 for `_gate_drafting_mutators.py`**; this measurement
is a named acceptance criterion of the work item, checked before the commit
gate. If the docstring condensation cannot reach <=399 without losing required
content, escalate per the Tolerance rather than one-lining the wrappers.

The body parameter is named `pass_number` **end to end** (A2 resolution): the
body keeps that name and the registrar wrapper exposes it under the `--pass`
CLI flag with an explicit `cyclopts.Parameter(name="--pass")` annotation — no
`pass_`-to- `pass_number` translation anywhere. Pin the `--pass` flag in
`test_command_surface_matrix.py` with
`App.parse_args(["set-critic-pass","--pass","2"], exit_on_error=False)`
returning `pass_number == 2`. The explicit `Parameter(name="--pass")` is used
rather than a trailing-underscore convention (the plan does not assume that for
locked Cyclopts 4.18.0); the flag is `--pass` (do not invent `--pass-number`).

The no-flag `set-gate` guard is realised by a domain exception **and a thin
adapter**, NOT by `cyclopts.ValidationError(msg=...)` (Decision D9 round-4
rewrite; B5). `_gate_drafting_mutators.py` gains a small domain exception and
adapter, copied verbatim in shape from `_desloppify.py:DesloppifyUsageError`
(line 69) and `_scan_or_usage` (lines 315-345):

```python
class GateDraftingUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit 2 (design §3.2).

    Raised when a gate/drafting mutator is invoked in a way the Cyclopts parser
    cannot catch -- specifically a no-flag ``set-gate``, which parses cleanly to
    ``{}``. The wrapper raises it and ``_set_gate_or_usage`` returns an exit-2
    ``CommandOutcome`` directly, never via the runner's ``str(CycloptsError)`` arm.
    """


def _set_gate_or_usage(
    *,
    knitting_30: bool | None = None,
    knitting_50: bool | None = None,
    knitting_80: bool | None = None,
    final: bool | None = None,
) -> CommandOutcome:
    """Run ``_set_gate``, mapping the no-flag usage fault to exit 2."""
    try:
        if (
            knitting_30 is None
            and knitting_50 is None
            and knitting_80 is None
            and final is None
        ):
            raise GateDraftingUsageError("set-gate requires at least one flag")
        return _set_gate(
            knitting_30=knitting_30,
            knitting_50=knitting_50,
            knitting_80=knitting_80,
            final=final,
        )
    except GateDraftingUsageError as exc:
        return CommandOutcome(
            code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
        )
```

A no-flag `set-gate` parses cleanly to `{}` (Cyclopts does not reject it on its
own; verified live), so the wrapper's "at least one flag is not `None`" check
is what raises, and the adapter — not the runner — owns the exit-2 envelope.
This is verified live driving the **real** `runner.run`: the no-flag `set-gate`
exits 2 with
`{"ok": false, "result": {}, "messages": ["set-gate requires at least one flag"]}`
and no traceback (Surprise S3). The `EnvelopeMessagesError` import comes from
`novel_ralph_skill.contract.errors` (the same base `StateInputError` and the
rulepack errors already subclass; `errors.py:20`); `ExitCode` from
`novel_ralph_skill.contract.exit_codes`. These two imports, plus `cyclopts` and
`typing` for the registrar, are the new module-level imports beyond the shared
mutator helpers.

Tests:

- **Surface matrix** (`tests/test_command_surface_matrix.py`,
  `tests/test_set_chapters_registration.py` precedent): the four new
  subcommands appear in the `novel-state` app's command set and resolve through
  `build_app()` (proving the registrar wired them onto the app `build_app`
  passes in). Assert `set-gate`, `complete-final-pass`, `set-fangirl`,
  `set-critic-pass` are present, and
  `App.parse_args(["set-critic-pass","--pass","2"], exit_on_error=False)` binds
  `pass_number == 2`. Add a direct test that
  `register_gate_drafting_commands(make_contract_app("novel-state"))` registers
  all four (the registrar is independently testable, decoupled from
  `build_app`). Extend the existing surface assertions rather than adding a
  parallel module if it stays under the cap.
- **Line-count gate (B4 acceptance criterion):** WI5 is not complete until
  `wc -l novel_ralph_skill/commands/novel_state.py` is **<=399** and
  `wc -l novel_ralph_skill/commands/_gate_drafting_mutators.py` is **<=400**.
  Run both before the commit gate; record the measured counts in the Progress
  note. If `novel_state.py` exceeds 399 after the two functional lines land,
  condense the two long docstrings further (do not one-line the registrar
  wrappers) or escalate per the Tolerance.
- **e2e** (`tests/test_gate_drafting_mutators_e2e.py`, POSIX-only, ADR 006,
  `@pytest.mark.slow`, `@pytest.mark.timeout(180)`): using the
  `installed_novel_state` fixture and the cuprum
  `run_sync(capture=True, context=ExecutionContext(cwd=run_dir))` form, against
  a throwaway tree from `working_corpus.build_working_tree`:
  - a fast in-process entry-point check (driven through `stub.novel_state()`
    like `test_set_chapters_e2e.py`) proving each subcommand resolves and exits
    0 on a coherent set;
  - the installed `novel-state set-gate --knitting-30` exits 0 on the
    `gate_lags_ratio` repair tree (incoherent prior: 0.45 ratio, `done_30 = false`)
    — `ok: true`, write-shaped envelope, the observable repair flip at the
    installed boundary (Decision D8);
  - the installed `novel-state set-gate --knitting-30` exits 3 on the
    `ratio_not_crossed` tree (coherent prior: 0.15 ratio) — `ok: false`, no
    traceback, the gate-ratio refusal at the installed boundary;
  - the installed `novel-state set-gate` with no flag exits 2 (usage; Decision
    D9),
    `ok: false`, no traceback — the installed-boundary proof that the
    `GateDraftingUsageError` + `_set_gate_or_usage` adapter produces the clean
    exit-2 envelope (B5; this arm would crash with a traceback if the
    `cyclopts.ValidationError(msg=...)` mechanism were used);
  - `novel-state set-fangirl --last-chapter (N+1)` exits 3 (`ok: false`);
  - `novel-state set-critic-pass --pass notanumber` exits 2 (the cyclopts shape
    fault, `ok: false`, no traceback);
  - `novel-state complete-final-pass` exits 0 on a final-pass tree.

Docs: ADR 003, ADR 006; `test_set_chapters_e2e.py` and
`tests/installed_binary_fixtures.py` for the cuprum call form;
`test_set_chapters_registration.py` for the surface pattern. Skills:
`python-router` → `python-testing`; `leta`/`grepai`. Use the locked cuprum
`run_sync(capture=, context=)` form (Surprise S1) — not the local-source
`output=` form.

Validation: `make all` (the slow e2e cases run under the `slow` marker; on
non-POSIX they skip per ADR 006).

### Work item 6: documentation — ADR, guides, SKILL bridge

Implements: roadmap 2.2.4 (the success wording mirrors 2.2.3's ADR
requirement); AGENTS.md documentation rule; the documentation-style-guide and
en-GB convention.

- **ADR 010** `docs/adr-010-gate-drafting-mutators.md` (next free ADR number
  after
  009): record the four command names and input shapes, the exit-2
  (shape/usage, incl. no-flag `set-gate`, realised by the
  `GateDraftingUsageError` + `_set_gate_or_usage` adapter that returns the
  exit-2 `CommandOutcome` directly — NOT `cyclopts.ValidationError(msg=...)`,
  which crashes the runner's `str(CycloptsError)` arm; B5/Decision D9) / exit-3
  (state semantics) split, the gate-ratio binding on `set-gate` and its
  identity as the **repair mutator for a gate that lags its ratio** (the one
  non-obvious semantic — "why can't set-gate just flip the flag from any
  state": it can only assert the value the ratio mandates, and its observable
  use is the incoherent→coherent repair, following the `set_cursor`
  no-prior-refusal skeleton), the write-time preconditions for the
  §5.2-unconstrained fields (Decision D6), and the single-file no-bracket
  no-receipt stance (Decision D3). **Include the A1/A5 reconciliation note
  explicitly** (so a future auditor does not read a missing receipt as an
  omission): "these are single-file mutators; they inherit the no-receipt
  stance of the `set-cursor`/`advance-phase`/`recount` sub-family. The roadmap
  2.2.4 'log-receipt discipline' wording binds the multi-file mutators
  (`reconcile`/`set-chapters`) only — developers-guide §'Checker/mutator
  segregation', which states single-file mutators write one `Path.replace` and
  open no bracket. **NB `init` is the one single-file-style mutator that *does*
  append a `log.md` receipt** (developers-guide lines 378-380); the four new
  mutators follow the `set-cursor`/`advance-phase`/`recount` no-receipt
  sub-family, not `init`, so a reader applying the roadmap's wording literally
  against `init` does not mistake the absence of a receipt here for an omission
  (A5)." Also record D10 (general `set-gate` chosen over per-gate
  `complete-knitting-NN` verbs, and the false- direction `--no-knitting-NN`
  retained for symmetry only — never a supported "turn a gate off" operation)
  and D11 (the registrar-in-sibling pattern that keeps `novel_state.py` under
  the 400-line cap). Mirror ADR 008's structure
  (Status/Context/Drivers/Decision outcome/Goals and non-goals/Known
  risks/Outstanding decisions).
- **Developers' guide** `docs/developers-guide.md`: extend the "State mutators"
  section (currently `init`/`set-cursor`/`advance-phase`) and the
  checker/mutator-segregation list to name the four new single-file mutators
  and the new module `_gate_drafting_mutators.py`. State the gate-ratio binding
  and the write-time preconditions once, citing ADR 010. Note the registrar
  pattern (`register_gate_drafting_commands(app)` lives in the body module and
  `build_app` calls it) as the established way to add subcommands without
  growing `novel_state.py` past the 400-line cap (Decision D11), so a future
  task adding more subcommands follows the same trail rather than
  re-discovering the cap pressure.
- **Users' guide** `docs/users-guide.md`: extend the `novel-state` section
  (after the `set-chapters` block) with each new subcommand's options, an
  example invocation, the exit-3 refusal contract, and the gate-ratio caveat
  ("`set-gate --knitting-30` succeeds only once drafting has crossed 30% of
  target").
- **SKILL bridge** `skill/novel-ralph/SKILL.md` (and any referenced
  `references/*.md`): bridge the four commands into the relevant phases — the
  knitting-gate flips into the knitting-circle steps, `complete-final-pass`
  into the final-pass phase, `set-critic-pass`/`set-fangirl` into the
  per-chapter drafting loop — so the agent records these fields by running the
  command, never by hand-editing `state.toml` (the ADR 001 rule the task
  closes). Grep `skill/novel-ralph/` for the current hand-edit guidance and
  replace it.

Tests: documentation has no unit test, but the surface/e2e tests from Work item
5 are the executable proof the documented commands exist and behave as written.
If any reference table in `tests/` enumerates the subcommand names (e.g. an
installed help snapshot), update it.

Docs to read: `docs/documentation-style-guide.md`, ADR 008 (structure template),
`docs/users-guide.md` and `docs/developers-guide.md` mutator sections,
`skill/novel-ralph/SKILL.md`. Skills: `en-gb-oxendict` (spelling); `leta`/
`grepai`.

Validation: `make all`, then `make markdownlint` and `make nixie` (the latter
for any Mermaid diagram touched; ADR 010 likely adds none, but run it because
markdown changed).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-4`.

First confirm the branch and a clean tree (expect `roadmap-2-2-4`):

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-4 \
  branch --show-current
```

Then, for each work item in turn:

- Write the failing test(s) first and confirm they fail with `make test`. Expect
  the new test(s) red — use `xfail(strict=True)` where the subcommand is not
  yet registered, mirroring `test_novel_state_mutators.py`.
- Add the body / registration, then run the full gate with `make all` (build,
  check-fmt, lint, typecheck, test — expect all green).
- For Work item 6 also run `make markdownlint` and `make nixie`.
- Commit each work item separately with an en-GB Oxford-spelling message
  (`commit-message` skill; never `-m`), gating each commit with `make all`.

Expected `make all` tail on success (illustrative):

```plaintext
... typecheck: ok
... NN passed in N.Ns
```

## Validation and acceptance

Acceptance is the roadmap 2.2.4 success criterion, phrased as observable
behaviour:

- **Every gate and drafting sub-state field is settable through a command.**
  `set-gate --knitting-30/--knitting-50/--knitting-80` repairs a gate that lags
  its ratio (incoherent prior → coherent result, exit 0) and is an idempotent
  no-op on an already-coherent prior; `set-gate --final`, `complete-final-pass`,
  `set-fangirl --last-chapter k`, and `set-critic-pass --pass p` each exit 0
  and write their field on a coherent tree; a follow-up `novel-state check`
  exits 0 in every case.
- **No field requires a hand-edit.** The SKILL bridge routes every field through
  its command; grep `skill/novel-ralph/` confirms no remaining "edit
  state.toml" guidance for these fields.
- **`check` stays coherent across the mutations.** Each behavioural/e2e scenario
  runs `check` after the mutation and asserts exit 0.
- **Refusals are exit 3, file unchanged.** A ratio-contradicting `set-gate`
  (asserting a gate true below threshold, or false above it), an out-of-manifest
  `set-fangirl`, and a `pass < 1` `set-critic-pass` each exit 3 with the prior
  `state.toml` byte-for-byte unchanged. Usage/shape faults are exit 2: a no-flag
  `set-gate` (Decision D9) and a non-integer `--pass`.
- **Behavioural tests cover each mutator.** At least one `pytest-bdd` scenario
  or
  installed-binary e2e per mutator (`complete-final-pass` has a `.feature`;
  `set-gate`/`set-fangirl`/`set-critic-pass` have installed e2e arms).

Quality criteria ("done"):

- Tests: `make test` green; each new test fails before its body lands and passes
  after. Property tests (Hypothesis) pass on `set-gate`, `set-fangirl`,
  `set-critic-pass`.
- Lint/typecheck: `make lint` and `make typecheck` clean (ruff, ty, 100%
  docstring coverage via interrogate — every new module, body, and helper
  carries a docstring; AGENTS.md).
- Markdown: `make markdownlint` and `make nixie` clean after Work item 6.
- File size: no file exceeds 400 lines. Specifically (B4/Decision D11):
  `wc -l novel_ralph_skill/commands/novel_state.py` <=399 after the registrar
  call and docstring condensation land;
  `wc -l novel_ralph_skill/commands/_gate_drafting_mutators.py` <=400; and any
  extended test module stays <=400. These counts are measured in WI5 before the
  commit gate.

Quality method: `make all` per commit (the AGENTS.md commit gate), plus
`make markdownlint` and `make nixie` for the documentation commit.

## Idempotence and recovery

- All steps are re-runnable. Re-running a mutator on an already-set coherent
  value
  re-writes the same bytes and exits 0 (`complete-final-pass` is explicitly
  idempotent).
- A refused mutator writes nothing, so a retry after fixing the input is safe.
- `make all` is deterministic; the shared Cargo/uv caches serialise naturally.
- No destructive step. The atomic `Path.replace` writer leaves either the old or
  the new `state.toml`, never a torn file (task 2.2.1).

## Artifacts and notes

Pinned API evidence (locked versions; reproduce from the worktree with
`uv run`):

```plaintext
    SafeCmd.run_sync sig (cuprum 0.1.0):
      (self, *, capture: bool = True, echo: bool = False,
       context: ExecutionContext | None = None) -> CommandResult

    Cyclopts 4.18.0 bool negation:
      ["set-gate","--knitting-30"]    -> {"knitting_30": True}
      ["set-gate","--no-knitting-30"] -> {"knitting_30": False}
      ["set-gate"]                    -> {}   (default applies)

    pytest-timeout 2.4.0: @pytest.mark.timeout(N) overrides the config default for
    that item (per the official docs), used as @pytest.mark.timeout(180) on the
    slow wheel-build e2e cases.
```

## Interfaces and dependencies

New module `novel_ralph_skill/commands/_gate_drafting_mutators.py` exposes the
four private body functions, one domain usage exception, one usage adapter, and
one public registrar:

```python
class GateDraftingUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit 2 (no-flag set-gate)."""

def _set_gate(
    *,
    knitting_30: bool | None = None,
    knitting_50: bool | None = None,
    knitting_80: bool | None = None,
    final: bool | None = None,
) -> CommandOutcome: ...

def _set_gate_or_usage(
    *,
    knitting_30: bool | None = None,
    knitting_50: bool | None = None,
    knitting_80: bool | None = None,
    final: bool | None = None,
) -> CommandOutcome: ...

def _complete_final_pass() -> CommandOutcome: ...

def _set_fangirl(*, last_chapter: int) -> CommandOutcome: ...

def _set_critic_pass(*, pass_number: int) -> CommandOutcome: ...

def register_gate_drafting_commands(app: cyclopts.App) -> None: ...
```

`GateDraftingUsageError` subclasses `EnvelopeMessagesError`
(`novel_ralph_skill/contract/errors.py:20`) — the same base `StateInputError`
and the rulepack errors use — and `_set_gate_or_usage` is the thin adapter
(modelled on `_desloppify.py:_scan_or_usage`, lines 315-345) that catches it
and returns `CommandOutcome(code=ExitCode.USAGE_ERROR, ...)` directly, so the
no-flag `set-gate` exit-2 envelope never routes through the runner's
`str(CycloptsError)` arm (B5; Decision D9). The set-gate registrar wrapper calls
`_set_gate_or_usage`, not `_set_gate`, so the no-flag guard is always in the
path.

`register_gate_drafting_commands(app)` defines the four `@app.command` wrappers
on the passed-in `app` (the B4 resolution that keeps the registration off
`novel_state.py`; Decision D11). The wrappers carry the subcommand names
(`set-gate`, `complete-final-pass`, `set-fangirl`, `set-critic-pass`), the
no-flag `set-gate` no-flag guard via `GateDraftingUsageError` + the
`_set_gate_or_usage` adapter (exit 2; Decision D9 round-4 rewrite — NOT
`cyclopts.ValidationError`), and the `--pass` flag for `set-critic-pass` via
`cyclopts.Parameter(name="--pass")`; the set-gate wrapper calls
`_set_gate_or_usage` (every other wrapper calls its matching private body). The
module imports the shared helpers from
`novel_ralph_skill.commands._state_mutators` (`_load_document_or_state_error`,
`_state_view_or_state_error`, `_refuse_if_incoherent`, `_state_path`,
`_working_dir`) and `write_document_atomically` from `novel_ralph_skill.state`,
exactly as `_set_chapters.py` does, plus `EnvelopeMessagesError` from
`novel_ralph_skill.contract.errors`, `ExitCode` from
`novel_ralph_skill.contract.exit_codes` (for the B5 adapter), and `cyclopts` and
`typing` for the registrar. It defines small pure write-time precondition
predicates for `set-fangirl` (`0 <= last_chapter <= len(chapters)`) and
`set-critic-pass` (`pass_number >= 1`), each returning a refusal rule name, in
the `manifest_coherence_violations` style.

`novel_ralph_skill/commands/novel_state.py:build_app()` gains exactly two lines
— a deferred `from novel_ralph_skill.commands import _gate_drafting_mutators`
and a `_gate_drafting_mutators.register_gate_drafting_commands(app)` call before
`return app` — and condenses its two long docstrings by >=4 lines so the file
stays <=399 (Decision D11; verified by `wc -l` in WI5). The deferred import is
required to avoid the `_gate_drafting_mutators` -> `_state_mutators` ->
`novel_state` cycle (`_state_mutators.py:35-44`).

No change to `validate_state`, `CommandOutcome`, `run`, `make_contract_app`,
the schema dataclasses, the `[project.scripts]` table, or any locked
dependency. The `build_app()` zero-argument signature is unchanged (it still
returns the same `cyclopts.App`; only its body grows by two lines and its
docstring is condensed).

## Revision note

Initial draft (2026-06-25). Decomposes roadmap 2.2.4 into six ordered work
items: four single-file mutators (`set-gate`, `complete-final-pass`,
`set-fangirl`, `set-critic-pass`) in a new module, their registration with
surface + installed e2e proofs, and the ADR/guide/SKILL documentation. The
load-bearing decision — that `set-gate` is bound by the §5.2
`gate-ratio-consistent` invariant and refuses a contradicting flip with exit 3
— is pinned as a Constraint and a first-written refusal test, not a workaround.
All cuprum/Cyclopts/pytest-timeout behaviour is verified against the locked
versions and cited.

Round 2 (2026-06-26). Resolves the three round-1 blocking points and four
advisories from `roadmap-2-2-4.review-r1.md`.

- **B1 (set-gate happy path unreachable from a coherent prior).** Re-framed
  `set-gate` as the **repair mutator for a gate that lags its ratio**: it
  follows the `set_cursor` skeleton (which does NOT refuse an incoherent prior,
  seen in `_state_mutators.py:176-234`), validates only the *proposed* state,
  so the only observable validator-permitted flip is the incoherent→coherent
  repair. From an already-coherent prior it is an idempotent no-op. Recorded in
  the rewritten Purpose, the gate-ratio Constraint, Decision D4 (revised), and
  ADR 010 (WI6).
- **B2 (named baseline contradicts the WI1 recipe).** Work item 1 now names
  three
  exact `WorkingTreeSpec` fixtures (`gate_lags_ratio` 0.45/all-false incoherent,
  `ratio_not_crossed` 0.15/all-false coherent, `ratio_crossed_coherent` 0.45/
  `done_30`-true coherent), built the way
  `_variants.py:_gate_true_below_threshold` builds its incoherent variant, and
  forbids reusing `COHERENT_BASELINE` (0.86, all gates already true). The
  Hypothesis strategy's tree-construction recipe and an anti-vacuity `event()`/
  `target` requirement are specified. Recorded in Decision D8.
- **B3 (stale line count).** Corrected `_state_mutators.py` 245→325 lines
  (verified
  by `wc -l`) in the Constraint and the Risk; `novel_state.py` stays 399.
- **A1 (roadmap log-receipt wording).** ADR 010 now carries an explicit
  reconciliation note that single-file mutators inherit the no-receipt stance
  and the roadmap's receipt wording binds the multi-file mutators only.
- **A2 (`pass_` vs `pass_number`).** Pinned `pass_number` end to end with an
  explicit `Parameter(name="--pass")` annotation in the WI5 wrapper; no name
  translation anywhere.
- **A3 (design prose says `current`, validator uses `by_chapter`).** Added a
  Constraint forbidding "fixing" the validator into the stale doc; plan,
  fixtures, and tests all track the validator's `sum(by_chapter)` total.
- **A4 (no-flag `set-gate` exit code).** Resolved to exit 2 (usage) via a
  Cyclopts
  group-required/usage-error raise in the wrapper, not a body
  `StateInputError`; recorded in Decision D9 and asserted in the WI5 e2e arms.
- Also recorded Decision D10 (general `set-gate` retained over Wafflecat's
  per-gate
  `complete-knitting-NN` alternative) and updated the WI5 e2e arms and the
  Acceptance section to match the repair/exit-2 semantics.

Round 3 (2026-06-26). Resolves the one round-3 blocking point (B4) and two
advisories (A5, A6) from `roadmap-2-2-4.review-r2.md`.

- **B4 (Work item 5 breaches the 400-line cap on `novel_state.py`).** Resolved
  by
  Decision D11 (option (a) of the reviewer's three): the four `@app.command`
  wrappers are NOT defined in `build_app`. They live in a registrar function
  `register_gate_drafting_commands(app)` in the new
  `_gate_drafting_mutators.py` module (verified clean: `make_contract_app`
  returns a plain `cyclopts.App`, `runner.py:75-81`, and `@app.command`
  registers a decorated function onto any `App` regardless of defining module).
  `build_app` gains exactly two lines (a deferred import + the registrar call),
  and its two long docstrings are condensed by >=4 lines so the **post-change
  `wc -l novel_state.py` is <=399** — a named WI5 acceptance gate, re-measured
  before the commit, not left to runtime escalation. The import stays deferred
  to avoid the `_gate_drafting_mutators` -> `_state_mutators` -> `novel_state`
  cycle (`_state_mutators.py:35-44`). The registration-site cap pressure is now
  a Constraint and a Risk ("registration-site size") with the measured budget.
  The bodies are renamed with a leading underscore (`_set_gate` etc.) so the
  public registrar wrappers carry the subcommand names and the no-flag guard.
  Recorded in the 400-line Constraint, the new Risk, Decision D11, the
  rewritten WI5, the Interfaces section, and ADR 010 (WI6).
- **A5 (ADR 010 reconciliation note should name `init` as the receipt
  exception).**
  The WI6 ADR-010 note now states explicitly that `init` is the one
  single-file-style mutator that DOES append a `log.md` receipt
  (developers-guide 378-380), and that the four new mutators follow the
  `set-cursor`/`advance-phase`/`recount` no-receipt sub-family, not `init`, so
  a reader applying the roadmap wording literally against `init` sees no
  omission.
- **A6 (pin `cyclopts.ValidationError(msg=...)`).** The class is pinned in
  Decision D9, WI1, and WI5: `cyclopts.ValidationError`, constructed
  `ValidationError(msg="...")`, is a `CycloptsError` subclass (verified live
  against locked Cyclopts 4.18.0), mapped to exit 2 by `runner.py:225-232`. No
  memory-vs-verified gap remains on the exit-2 path.
- Also noted (review-r2 Wafflecat second alternative) in D10 that the false
  direction `--no-knitting-NN` is retained for symmetry only — never a
  supported "turn a gate off" operation — and tested only for its refusal arm.

Round 4 (2026-06-26). Resolves the one round-3 blocking point (B5) and two
advisories (A7, A8) from `roadmap-2-2-4.review-r3.md`.

- **B5 (the no-flag `set-gate` exit-2 mechanism crashes the runner).** The
  round-3
  mechanism raised `cyclopts.ValidationError(msg=...)` in the wrapper and
  relied on `runner.py:225-232` mapping `CycloptsError` -> exit 2 via
  `messages=[str(exc)]`. Verified live: a bare hand-raised
  `ValidationError(msg=...)` has `argument/group/command_chain` all `None`, so
  `ValidationError._segments()` (`cyclopts/exceptions.py:229-265`) reaches
  `else: raise NotImplementedError` (line 258) before the base-class `msg`
  short-circuit (line 160); `str(exc)` therefore raises `NotImplementedError`
  **inside** `runner.py:230`, crashing the command with a traceback and a
  non-contract exit — the opposite of the asserted clean exit-2 envelope. Round
  3's A6 "verified live" note checked only `issubclass(...)` and propagation,
  never `str()` in the handler. **Resolution:** dropped
  `cyclopts.ValidationError(msg=...)` entirely and adopted the existing working
  `_desloppify` precedent — a domain exception
  `GateDraftingUsageError(EnvelopeMessagesError)` raised in the `set-gate`
  wrapper, caught by a thin adapter `_set_gate_or_usage` that returns
  `CommandOutcome(code=ExitCode.USAGE_ERROR, messages=...)` **directly**, never
  via the runner's `str(CycloptsError)` arm
  (`_desloppify.py:DesloppifyUsageError` line 69 + `_scan_or_usage` lines
  315-345 are copied in shape). `StateInputError` is not reusable (it maps to
  exit 3). The exit-2 envelope was **verified live driving the real `runner.run`
  **: the no-flag `set-gate` exits 2 with
  `{"ok": false, "result": {}, "messages": ["set-gate requires at least one flag"]}`
  and no traceback. WI1's no-flag unit test and WI5's no-flag e2e arm now
  require the real-runner / installed-binary exit-2 envelope assertion, never a
  subclass-hood assertion. Recorded in the new exit-2-adapter Constraint, the
  new B5 Risk, Surprise S3, the rewritten Decision D9, WI1, the rewritten WI5
  registrar (the wrapper now calls `_set_gate_or_usage`; the
  `GateDraftingUsageError` + adapter source is shown), the Interfaces section
  (A8), and ADR 010 (WI6).
- **A7 (cite `state-layout.md` at its real path).** Every "Docs to read"
  citation
  now names `skill/novel-ralph/references/state-layout.md` (it lives under
  `skill/novel-ralph/references/`, not `docs/`), with a one-line path note at
  first use in the Constraints.
- **A8 (name the exit-2 adapter in the Interfaces section, re-measure WI5
  budget).**
  The Interfaces section now enumerates `GateDraftingUsageError` and
  `_set_gate_or_usage` alongside the four bodies and the registrar; the
  `_gate_drafting_mutators.py` projection is revised to ~245-305 lines (the
  +10-15 adapter lines), still well under 400, re-measured by `wc -l` in WI5.

## Addenda

Lightweight, post-merge corrections folded onto this completed task. Each runs
as a no-plan, no-review lightweight pass.

- **Restore snapshot/BDD parity for the gate and drafting mutators** (from
  audit:2.2.4 Findings 3 and 4; low). The sibling-mutator baseline pins both a
  success and a refusal envelope snapshot per mutator
  (`tests/test_novel_state_mutator_snapshots.py`) and a behavioural `.feature`
  per refusal-bearing verb. This slice shipped only a single `set-gate` success
  `result` snapshot and only `complete_final_pass.feature`, leaving the headline
  `set-gate` repair/refusal/usage arms and the `complete-final-pass`,
  `set-fangirl`, and `set-critic-pass` envelopes without snapshot or behavioural
  regression protection. Backfill the missing success (and where applicable
  refusal) `result`/envelope snapshots for `complete-final-pass`, `set-fangirl`,
  and `set-critic-pass`, add a `set-gate` below-threshold refusal snapshot, and
  add a `set_gate.feature` covering the repair (exit 0), below-threshold refusal
  (exit 3), and no-flag usage (exit 2) arms, matching the sibling-mutator parity
  in `test_novel_state_mutator_snapshots.py` and the refusal-bearing `.feature`
  files. This restores the project's uniform coverage standard without changing
  shipped behaviour.
