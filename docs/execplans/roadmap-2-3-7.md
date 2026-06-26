# Make recount's gate-ratio refusal actionable and document the recount-gate coupling

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (revised — planning round 2, design-review blocking points B1/B2
resolved; see Revision note)

## Purpose / big picture

`novel-state recount` re-derives `[word_counts]` from the on-disk chapter
drafts. When a recount would move the drafted ratio across a 30/50/80%
knitting-gate threshold while the matching gate flag is still `false`, the
recount correctly refuses with exit `3` on the `gate-ratio-consistent`
invariant (it must not silently flip a gate, because integrating a knitting
pass is the agent's judgement, not a deterministic recompute — design §5.4
recovery rule 1, lines 604-611). Beta testing found two problems: the refusal
message is cryptic, and the recount-to-gate coupling is undocumented.

After this change, an operator who hits the refusal reads a message that names
the specific crossed threshold(s) and the exact remedy — integrate the pending
knitting pass, then run `novel-state set-gate --knitting-NN` — instead of the
current raw tuple dump. The recount-gate coupling is documented in the
developers' guide, the users' guide, and the skill, so the next operator knows
why a recount can refuse and what to do about it.

You can see success by driving a recount over a tree whose drafts have grown
past a threshold while the gate flag still lags, observing exit `3` and the new
actionable message, and by reading the three documentation surfaces.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The pure-state validator `validate_state`
  (`novel_ralph_skill/state/validate.py`) must stay **pure and CLI-agnostic**:
  it must not name CLI verbs (`set-gate`, `--knitting-30`) or remedies. Its
  `Violation.detail` is a *description* of the breach, consumed identically by
  `check`, `set-gate`, `reconcile`, and `recount`. The operator remedy belongs
  in the command layer (`novel_ralph_skill/commands/_recount.py`), not the
  validator (design §3.3 checker/mutator split; §5.4 "disk is authoritative").
- The `gate-ratio-consistent` numerator must remain the drafted total
  `sum(word_counts.by_chapter.values())`, never `current`, and the predicate
  must keep its `target <= 0` short-circuit so `validate_state` stays total over
  every constructible `State` (design §5.2; developers-guide "Two readings are
  deliberate pure-state approximations", lines 615-625; Decision Log B1/B7).
- The invariant **name** `gate-ratio-consistent` and the
  `PURE_STATE_INVARIANT_NAMES`/`CORPUS_INVARIANT_NAMES` vocabulary must not
  change. Task 2.1.3's whole-corpus agreement cross-check keys on these strings
  (`tests/test_validate_state_live_draft.py`); a name change breaks it.
- Recount must keep refusing with exit `3` (the state-or-input channel), never
  the benign exit `1`, and must leave `state.toml` byte-for-byte intact on
  refusal (design §3.2; ExecPlan Constraint "Validate before persist" carried
  from roadmap 2.3.1). The recount must not flip any `[gates]` flag itself.
- Recount must stay a single-file mutator that opens no `[pending_turn]`
  bracket (design §4.1 line 271; §3.4).
- Documentation prose must use en-GB Oxford spelling (`-ize`/`-yse`/`-our`),
  wrap at 80 columns for prose/bullets and 120 for code blocks, and use `-`
  bullets (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if implementation requires changing more than 4 non-test source files
  or more than ~120 net lines of non-test code, stop and escalate.
- Interface: if the `CommandOutcome`/envelope shape, the `StateInputError`
  contract, or any public function signature in
  `novel_ralph_skill/state/validate.py` or `_state_mutators.py` must change,
  stop and escalate.
- Dependencies: if any new runtime or dev dependency is required, stop and
  escalate (none is expected; cyclopts/tomlkit runtime, cuprum dev are locked).
- Vocabulary: if making the message actionable appears to require renaming
  `gate-ratio-consistent` or changing `CORPUS_INVARIANT_NAMES`, stop and
  escalate — that breaks the agreement cross-check and is out of scope.
- Iterations: if the new behavioural/e2e test still fails after 3 focused
  attempts, stop and escalate.
- Ambiguity: if the "crossed threshold" framing turns out to be ambiguous for
  the *downward* direction (a recount that drops the ratio below a threshold
  while a gate is still `true`), stop and present options — see Risk below.

## Risks

    - Risk: The refusal fires in two directions. The roadmap names the upward
      direction (recount crosses a threshold while the gate is false), but
      `gate-ratio-consistent` also fires downward (recount drops the ratio below
      a threshold while the gate stays true — the existing
      test_recount_legitimate_gate_breach_refuses case). The actionable message
      must read sensibly for both, or be explicitly scoped.
      Severity: medium
      Likelihood: high
      Mitigation: RESOLVED in this revision. The message enumerates, per gate,
      which flag disagrees with which threshold and in which direction, with two
      pinned line templates (Work item 2, "Pinned message template"). The
      **upward** line says "crossed the NN% knitting threshold … run `set-gate
      --knitting-NN`"; the **downward** line says "left drafting below the NN%
      knitting threshold … the recorded gate no longer matches the drafts.
      Adjudicate …" and deliberately omits the `set-gate` verb. Both directions
      are pinned by a unit test, a behavioural scenario, and an installed e2e
      (Work items 2 and 3), so the dual-direction promise is proven at the
      user-visible level, not only in a unit test (resolves design-review B2).

    - Risk: The shared Violation.detail is asserted by
      tests/test_validate_state_details.py (the GATE_RATIO_CONSISTENT case
      expects substrings "0.3", "0.5", "0.8"). Enriching the detail must keep
      those substrings present (or the case must be updated to the new prose in
      the same commit).
      Severity: low
      Likelihood: high
      Mitigation: Update the detail prose to still surface the thresholds and
      the per-gate flags, and update the detail-coverage case in the same work
      item with semantic substrings.

    - Risk: The set-gate snapshot suite
      (tests/__snapshots__/test_set_gate_snapshots.ambr) and the mutator-refusal
      snapshot (test_novel_state_mutator_snapshots.ambr) may capture the
      gate-ratio detail prose; enriching it churns the snapshots.
      Severity: low
      Likelihood: medium
      Mitigation: Locate every snapshot that captures the gate-ratio detail
      before editing, regenerate intentionally with `pytest --snapshot-update`,
      and review each regenerated `.ambr` so the churn is a real contract change,
      not noise (AGENTS.md snapshot rule).

## Progress

    - [x] (done) Work item 1: enrich the shared gate-ratio Violation.detail.
      The detail now enumerates only the *disagreeing* gates, naming each gate
      flag (`done_30`/`done_50`/`done_80`), its two-decimal threshold (so
      `0.3`/`0.5`/`0.8` stay contiguous substrings), the drafted ratio, and the
      breach direction (`above`/`below`). Added `_gate_ratio_disagreement` and
      `_KNITTING_GATE_NAMES`; kept the numerator, the `target <= 0`
      short-circuit, and the invariant name. Updated the
      `GATE_RATIO_CONSISTENT` detail-coverage case to assert the richer prose
      (`done_30=True`, `0.3`, `below`) — only the flipped gate now appears, so
      the old `0.5`/`0.8` substrings no longer apply. No snapshot captured the
      gate-ratio detail (verified). `make all` green; coderabbit returned no
      findings on the code, only pre-existing markdown-style notes on the
      planning docs.
    - [x] (done) Work item 2: add the recount-specific actionable remedy
      (pinned per-gate, per-direction template; shape 2). Added the
      `remedy: Callable[[State], Sequence[str]] | None = None` keyword to
      `_refuse_if_incoherent` (validates once, appends remedy lines after the
      per-violation details); no other caller passes it, so the remaining 10
      call sites across four files (`_reconcile` recount and reconcile,
      `_set_chapters` set-chapters, `_state_mutators` set-cursor and the two
      advance-phase calls, `_gate_drafting_mutators` set-gate,
      complete-final-pass, set-fangirl, set-critic-pass) are unchanged — shape 2
      held, no fallback to shape 1. Added `_gate_ratio_remedy(state) -> list[str]` in
      `_recount.py`, enumerating per-gate disagreements directly (no "which
      threshold crossed" recompute) and emitting the upward line (`set-gate
      --knitting-NN`) or the downward line (adjudicate, no verb). The ratio is
      rendered with `:.0f` (matching the pinned template; `round()` was wrong —
      it printed `34.0%`). Verification: example-based parametrized units, not
      Hypothesis (finite message matrix). Split the new tests into
      `tests/test_recount_actionable_unit.py` because adding them in-place pushed
      `test_recount_unit.py` past the 400-line module cap. CodeRabbit (1 run):
      strengthened the downward test to isolate the single 80% breach (recount to
      0.55, not empty drafts) and assert no `set-gate` on any line; the multi-gate
      test now asserts a distinct line per gate via `_message_for`; added an
      explicit message to the invariant-name assert.
    - [x] (done) Work item 3: behavioural + e2e proof of the actionable
      refusal, in **both** directions (upward and downward). Added two
      `tests/features/recount.feature` scenarios (upward 30% crossing, downward
      80% no-longer-matching), driven through `run` with `capsys` reading the
      exit-3 envelope's `messages`; unified the shared `When` step so all three
      scenarios bind one run step (removed the duplicate `@when`). Added the
      `does not contain` step to prove no `set-gate` verb leaks downward. Added
      a fast in-process entry-point upward proof (non-`slow`) and two installed
      `@pytest.mark.slow` e2e tests (upward + downward) in `test_recount_e2e.py`,
      reusing the cuprum `Program`/`single_program_catalogue`/`run_sync` pattern;
      the downward installed test asserts `set-gate --knitting-80` is absent from
      every messages line. The downward fixtures recount to 0.55 to isolate the
      single 80% breach. CodeRabbit (1 run): 0 findings. Refactored the step
      tree builder into a spec factory + builder to stay within pylint's 4-arg
      cap.
    - [x] (done) Work item 4: document the recount-gate coupling in the
      developers' guide. Added a "The recount-gate coupling" subsection after the
      gate-ratio numerator discussion: recount writes only `[word_counts]` and
      never `[gates]`; a threshold-crossing recount refuses with exit 3 on
      gate-ratio-consistent; the detail stays a CLI-agnostic description while the
      command layer's `_gate_ratio_remedy` adds the upward (`set-gate
      --knitting-NN`) and downward (adjudicate, no verb) advice; cross-links the
      existing set-gate "repair mutator" note. Wrapped at 80 cols, en-GB Oxford
      spelling. markdownlint + nixie + `make all` green; CodeRabbit 0 findings.
    - [x] (done) Work item 5: document the coupling in the users' guide and
      the skill. Added a forward cross-link in the users-guide recount paragraph
      (a recount refuses with exit 3 when it would cross a knitting-gate threshold
      the gates do not yet reflect, naming the threshold, pointing at the existing
      `set-gate` paragraph as the remedy) without duplicating the set-gate prose
      (advisory A1). Added a "recount-gate coupling" passage to the skill
      `state-layout.md` Gates section for the agent operator: recount never flips
      a gate; on a `gate-ratio-consistent` refusal integrate and log the pass then
      run `set-gate --knitting-NN` (upward) or adjudicate (downward), never
      hand-edit `[gates]`. Wrapped at 80 cols, en-GB Oxford spelling. markdownlint
      + nixie + `make all` green; CodeRabbit 0 findings.

## Surprises & discoveries

    - Observation: A `set-gate` mutator and `novel-state set-gate
      --knitting-NN` already exist and are documented as the *repair* for a gate
      that lags its ratio (users-guide lines 285-298; skill state-layout.md
      lines 207-215). The remedy this plan adds is therefore a *pointer to an
      existing verb*, not a new command.
      Evidence: `novel_ralph_skill/commands/_gate_drafting_mutators.py`;
      `docs/users-guide.md`; `skill/novel-ralph/references/state-layout.md`.
      Impact: No new CLI surface; the work is message text plus documentation.

## Decision log

    - Decision: Put the actionable remedy in the command layer (recount), not in
      the pure-state validator's Violation.detail.
      Rationale: The validator is consumed by check/set-gate/reconcile/recount
      and must stay CLI-agnostic and pure (design §3.3). Only recount knows the
      operator is mid-recount; the remedy ("integrate the pending knitting pass,
      then run set-gate --knitting-NN") is recount-specific operator advice. The
      shared detail is enriched to *describe* the breach precisely (which gate,
      which threshold, which direction); the command layer *prescribes* the fix.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Keep the invariant name gate-ratio-consistent unchanged; enrich
      only the human prose.
      Rationale: The agreement cross-check and corpus oracle key on the name
      (Constraints). Actionability is a prose concern, not a vocabulary concern.
      Date/Author: 2026-06-26, planning agent.

    - Decision: Use the installed-binary e2e pattern verbatim from
      tests/test_recount_e2e.py for the installed actionable-message proof.
      Rationale: That file already drives the installed `novel-state recount`
      through `Program` + the `single_program_catalogue` **suite fixture** +
      `sh.make(...).run_sync(context=ExecutionContext(cwd=run_dir),
      capture=True)`, asserting exit code and the JSON envelope. The cuprum
      symbols `make`, `run_sync`, `ExecutionContext`, `capture`, and
      `ProgramCatalogue` are present in the locked cuprum 0.1.0 (verified in
      `/data/leynos/Projects/cuprum/cuprum/sh.py` lines 169/441/528 and
      `cuprum/catalogue.py` line 59). `single_program_catalogue` is the
      **test-suite fixture** (a parameter of the e2e tests), not a cuprum export
      — corrected per advisory A3 so a future reader does not look for it in
      `cuprum/`. No new cuprum capability is needed.
      Date/Author: 2026-06-26, planning agent.

    - Decision (resolves B1/A2): Pin Work item 2 to shape 2 — a
      backward-compatible `remedy` callable keyword on `_refuse_if_incoherent`
      defaulting to `None`. Recount passes `remedy=_gate_ratio_remedy`.
      Rationale: shape 1 (re-validating `proposed` in `recount`) would validate
      twice on the refusal path; shape 2 validates once, in the helper's own
      `validate_state` call (advisory A2). The keyword defaults to `None`, so
      none of the other 10 call sites (across `_reconcile`, `_set_chapters`,
      `_state_mutators`, and `_gate_drafting_mutators`)
      changes. If implementation finds a caller would change, fall back to shape
      1 and record it (Tolerances "Interface").
      Date/Author: 2026-06-26, planning agent.

    - Decision (resolves B1/B2): Pin the actionable message as a per-gate,
      direction-aware template (see Work item 2's "Pinned message template").
      The remedy enumerates each gate whose recorded flag disagrees with
      `ratio >= threshold` and emits one line per disagreement: an **upward**
      line ("crossed the NN% knitting threshold … run `set-gate --knitting-NN`.
      Do not hand-edit [gates].") and a **downward** line ("left drafting below
      the NN% knitting threshold … the recorded gate no longer matches the
      drafts. Adjudicate … Do not hand-edit [gates] to silence this."). The
      downward line deliberately omits `set-gate --knitting-NN`, because nothing
      was crossed upward and prescribing the repair verb there would corrupt the
      gate-integration record (pre-mortem). The percentage and ratio are derived
      from `GATE_THRESHOLDS` and the recounted ratio the validator already
      computes — the command layer does not recompute "which threshold was
      crossed"; it enumerates per-gate disagreements directly.
      Date/Author: 2026-06-26, planning agent.

    - Decision (cite python-verification): the actionable message is a fixed
      template over a finite trigger matrix (three thresholds × two directions,
      plus the multi-gate fan-out), so parametrized example-based unit,
      behavioural, and e2e tests are the right adversary — **not** Hypothesis,
      CrossHair, or mutmut, since there is no new range-of-inputs invariant,
      only a finite message matrix. (Re-confirm with `python-verification` at
      implementation time.)
      Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

All five work items are implemented, gated, and committed. Against Purpose: an
operator who hits the recount gate-ratio refusal now reads a per-gate,
direction-aware message that names the crossed threshold and the exact remedy
(`set-gate --knitting-NN` upward; adjudicate, no verb, downward), instead of the
former raw tuple dump; the recount-gate coupling is documented in the
developers' guide, the users' guide, and the skill. Both directions are proven
at the user-visible level by behavioural scenarios and installed-binary e2e
tests, the direct resolution of design-review B2.

Shape 2 held: the `remedy` keyword on `_refuse_if_incoherent` defaults to `None`,
so no other caller changed — no fallback to shape 1 was needed. The invariant
name `gate-ratio-consistent`, the numerator, and the `target <= 0` short-circuit
are unchanged, so the agreement cross-check and corpus oracle stayed green.

Deviations from the plan, with rationale:

- The new actionable-message unit tests were placed in a **new** module
  `tests/test_recount_actionable_unit.py` rather than extended into
  `tests/test_recount_unit.py`, because in-place additions pushed that module
  past the 400-line cap (AGENTS.md "clear file boundaries"). The downward
  assertions the plan slated for `test_recount_legitimate_gate_breach_refuses`
  moved into the new module's dedicated downward test instead; the original test
  keeps its invariant-name assertion.
- The downward unit/e2e fixtures recount to **0.55** (not the plan's empty-draft
  0.00) so exactly **one** gate (`done_80`) disagrees, isolating the downward
  message — addressing a CodeRabbit major finding that the all-true/empty-draft
  shape mixed three downward breaches and could mask a leak on the others.
- The ratio percentage is rendered with `:.0f` (the pinned template), not
  `round()`, which printed `34.0%` and broke the substring.

## Context and orientation

You are working in the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-7` on branch
`roadmap-2-3-7`. Treat `docs/` as the source of truth. Quality gates and
testing rules live in `AGENTS.md`.

Key files (full repository-relative paths):

- `novel_ralph_skill/state/validate.py` — the pure §5.2 invariant validator.
  `_check_gate_ratio_consistent` (lines 250-278) builds the
  `Violation(invariant="gate-ratio-consistent", detail=...)` whose `detail` is
  the human prose. `GATE_THRESHOLDS = (0.30, 0.50, 0.80)` (line 76) is the
  public source of truth for the thresholds.
- `novel_ralph_skill/commands/_state_mutators.py` —
  `_refuse_if_incoherent(state, *, context)` (lines 142-173) is the shared
  validate-before-persist refusal. It raises `StateInputError(summary,
  *details)` where `summary` is `"{context} would violate: {names}"` and each
  `detail` is a violation's prose. Recount calls this with `context="recount"`.
- `novel_ralph_skill/commands/_recount.py` — the `recount()` body (lines
  106-155). Line 149 calls `_refuse_if_incoherent(proposed, context="recount")`.
  This is where the recount-specific remedy is added.
- `novel_ralph_skill/contract/runner.py` — `StateInputError` (lines 114-123)
  carries `messages` to the exit-3 envelope; the exit-3 `run` arm emits only
  `messages`, no `result`.
- `novel_ralph_skill/commands/_gate_drafting_mutators.py` — the existing
  `set-gate` mutator and its `--knitting-30/-50/-80` flag-to-`done_NN` mapping
  (lines 71-93). This is the verb the remedy points at; no change needed here.

Documentation surfaces to update:

- `docs/novel-ralph-harness-design.md` — §4.1 (recount) and §5.4 recovery rule
  1 (lines 588-620) already state the coupling rationale; verify and, if the
  reviewer asks, add at most one clarifying sentence (the design is the source
  of truth and largely already says this — keep additions minimal).
- `docs/developers-guide.md` — the §5.2 invariant table and the `gate-ratio-
  consistent` discussion (lines 605-674). Add a short subsection on the
  recount-gate coupling and the actionable refusal.
- `docs/users-guide.md` — recount (lines 241-249) and set-gate (lines 285-298).
  Cross-link: a recount can refuse on gate-ratio, and set-gate is the remedy.
- `skill/novel-ralph/references/state-layout.md` — the Gates section (lines
  205-219) and the recount mention. State the coupling for the agent operator.

Terms:

- *Knitting gate*: one of three booleans (`done_30`, `done_50`, `done_80`) that
  record that a knitting-circle pass crossing the 30/50/80% drafted-ratio
  threshold has been integrated and logged. A gate is `true` only once its
  threshold is crossed *and* the pass is integrated — disk does not store the
  "integrated" fact, so the harness never flips a gate automatically.
- *Drafted ratio*: `sum(word_counts.by_chapter.values()) / word_counts.target`.
- *gate-ratio-consistent*: the §5.2 invariant that every knitting gate boolean
  equals `drafted_ratio >= threshold` for its threshold.

## Plan of work

Five ordered, independently committable work items. Each ends with the gate
sequence in "Validation and acceptance". Items 1-3 are code (run `make all`);
items 4-5 are documentation (run `make all`, `make markdownlint`, `make nixie`).

### Work item 1 — Enrich the shared gate-ratio Violation.detail

Goal: make `_check_gate_ratio_consistent`'s `detail` name, per gate, which flag
disagrees with which threshold and in which direction, while preserving the
threshold substrings and the invariant name.

Implements: design §5.2 (invariant 7); developers-guide lines 615-625 (the
deliberate pure-state numerator). Keeps the validator pure (Constraints).

Edit `novel_ralph_skill/state/validate.py`, function
`_check_gate_ratio_consistent` (lines 250-278). Replace the single opaque
detail string with prose that, for each of the three gates, reports the gate
name (`done_30`/`done_50`/`done_80`), its recorded boolean, its threshold
(`0.30`/`0.50`/`0.80`), the computed drafted ratio, and the disagreement
direction. Keep:

- the numerator `sum(state.word_counts.by_chapter.values())` and the
  `target <= 0` short-circuit (Constraints);
- the `GATE_THRESHOLDS` source of truth;
- the threshold values rendered so `"0.3"`, `"0.5"`, `"0.8"` still appear as
  contiguous substrings (the detail-coverage case asserts these). Render each
  threshold either as the bare `GATE_THRESHOLDS` float (`0.3`/`0.5`/`0.8`) or
  with two decimals (`0.30`/`0.50`/`0.80`) — both satisfy the substring
  contract because `"0.3"` is a contiguous substring of `"0.30"` (advisory A5).
  Do **not** render at three decimals (`0.300`), which keeps the contiguous
  `0.3` but adds noise; prefer the two-decimal form for readability. State this
  rendering precision when implementing so the substring assertion passes on
  the first green cycle;
- the invariant name `gate-ratio-consistent` unchanged.

Do not introduce CLI verbs or remedies here. The richer detail describes the
breach (which gate, which threshold, which direction); the remedy is added only
in the command layer (Work item 2).

Docs to read first: design §5.2; developers-guide "Two readings are deliberate
pure-state approximations" (lines 615-625); the validator module docstring
(lines 1-28).

Skills to load: `python-router` (already routed) → `python-errors-and-logging`
(message/detail prose discipline) and `python-iterators-and-generators` only if
the per-gate enumeration reads better as a comprehension.

Tests this item must add/update:

- Update `tests/test_validate_state_details.py` — the `GATE_RATIO_CONSISTENT`
  case (`_DETAIL_CASES`, line 219). Keep/adjust the expected substrings so they
  assert the new, richer prose: the threshold values, the disagreeing gate
  name(s), and a direction word. The case must still prove the detail is
  non-empty and surfaces the offending values.
- The pure validator already has a property suite
  (`tests/test_validate_state_property.py`) and the agreement cross-check
  (`tests/test_validate_state_live_draft.py`); confirm they still pass
  unchanged (the *name* and *verdict* are unchanged, only the prose differs).
- Search for and update any snapshot capturing the gate-ratio detail:
  `tests/__snapshots__/test_set_gate_snapshots.ambr` and
  `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`. Regenerate with
  `uv run pytest <suite> --snapshot-update` and review the diff so the churn is
  a real contract change (AGENTS.md snapshot rule).

### Work item 2 — Add the recount-specific actionable remedy

Goal: when `recount()` refuses on `gate-ratio-consistent`, the exit-3 envelope
carries one extra `messages` line **per disagreeing gate**, each naming that
gate's threshold, the direction of the disagreement, and the
direction-correct remedy. The remedy is built only from facts the validator
already knows (each gate's recorded flag, its threshold, and the recounted
drafted ratio) — the command layer **does not** recompute "which threshold was
crossed"; it enumerates per-gate disagreements directly.

Implements: design §4.1 (recount), §5.4 recovery rule 1 (lines 600-611, "A
done-claim large enough to move a gate is reported and escalated, not silently
re-projected"); ADR-001/ADR-010 (remedy points at a verb, never a hand-edit).
Keeps the remedy in the command layer (Decision Log).

#### Chosen shape (pinned — resolves review B1, advisory A2)

Use **shape 2**: add a backward-compatible keyword
`remedy: cabc.Callable[[State], cabc.Sequence[str]] | None = None`
(defaulting to `None`) to `_refuse_if_incoherent`. When the verdict is
non-empty **and** `remedy is not None`, the helper appends the lines returned
by `remedy(state)` after the existing per-violation details. No other caller
passes `remedy`, so no other caller changes (verified: the other 10 call sites
are `_reconcile` recount and reconcile, `_set_chapters` set-chapters,
`_state_mutators` set-cursor and the two advance-phase calls, and
`_gate_drafting_mutators` set-gate, complete-final-pass, set-fangirl, and
set-critic-pass — Interfaces section).
Recount passes a `remedy=_gate_ratio_remedy` callable. This validates the
proposed state exactly **once** (it is the helper's own `validate_state` call),
avoiding the double-validation of the rejected shape 1 (advisory A2).

If, on implementation, adding the keyword forces any *other* caller to change
(it must not), abandon shape 2 for shape 1 (re-validate locally in `recount`)
and record the deviation in the Decision Log (Tolerances "Interface").

#### Pinned message template (resolves review B1 and B2)

The remedy callable receives the proposed `State` and the same per-gate facts
the validator computes: `flags = (done_30, done_50, done_80)`,
`GATE_THRESHOLDS = (0.30, 0.50, 0.80)`, and the recounted
`ratio = sum(by_chapter.values()) / target`. It enumerates the **three** gates
and emits **one line per gate whose flag disagrees with `ratio >= threshold`**,
choosing the line by direction. The flag→`set-gate` mapping is fixed:
`done_30 → --knitting-30`, `done_50 → --knitting-50`, `done_80 → --knitting-80`
(verified `_gate_drafting_mutators.py` lines 71-73). The threshold percentage is
rendered as an integer (`int(threshold * 100)` → `30`/`50`/`80`); the ratio is
rendered as a whole-number percentage (`ratio * 100:.0f`).

Two line forms, one per direction. Pin these exact templates (`RR` is the
recounted ratio rendered as a whole-number percentage and `NN` is the threshold
percentage; they are the only substitutions).

Upward (gate flag `false`, but `ratio >= threshold` — the roadmap's headline
case; the recount has moved drafting at or past the threshold while the gate
still lags):

    recount crossed the NN% knitting threshold (drafts now at RR% of target) but
    gate done_NN is still false: integrate the pending knitting pass and log it,
    then run `novel-state set-gate --knitting-NN`. Do not hand-edit [gates].

Downward (gate flag `true`, but `ratio < threshold` — drafts shrank, or the gate
was set prematurely; nothing was "crossed" upward, so the message must NOT tell
the operator to run `set-gate --knitting-NN`):

    recount left drafting below the NN% knitting threshold (drafts now at RR% of
    target) but gate done_NN is recorded true: the recorded gate no longer
    matches the drafts. Adjudicate — restore the drafts or clear the gate — and
    re-derive. Do not hand-edit [gates] to silence this.

Worked examples (these are the substrings the behavioural and e2e assertions
derive from — they are derivable from the plan, not the implementation):

- 30 upward (ratio 0.34, `done_30=false`): "recount crossed the 30% knitting
  threshold (drafts now at 34% of target) but gate done_30 is still false:
  integrate the pending knitting pass and log it, then run `novel-state
  set-gate --knitting-30`. Do not hand-edit [gates]."
- 50 upward (ratio 0.55, `done_50=false`): "… crossed the 50% knitting
  threshold (drafts now at 55% of target) but gate done_50 is still false: …
  `novel-state set-gate --knitting-50`. …"
- 80 upward (ratio 0.86, `done_80=false`): "… crossed the 80% knitting
  threshold (drafts now at 86% of target) but gate done_80 is still false: …
  `novel-state set-gate --knitting-80`. …"
- 80 downward (ratio 0.00, `done_80=true` — the **existing**
  `test_recount_legitimate_gate_breach_refuses` shape): "recount left drafting
  below the 80% knitting threshold (drafts now at 0% of target) but gate
  done_80 is recorded true: the recorded gate no longer matches the drafts.
  Adjudicate — restore the drafts or clear the gate — and re-derive. Do not
  hand-edit [gates] to silence this."

Note that a single recount can emit **multiple** lines (e.g. drafts grow past
both 30% and 50% while both gates lag false): the callable enumerates every
disagreeing gate, so the upward 50 case above implicitly also emits the 30 line
when `done_30` is likewise false. The behavioural and e2e scenarios choose
single-gate trigger trees so the asserted substrings are unambiguous; the unit
suite covers the multi-gate fan-out.

#### Acceptance substrings (pinned, per direction)

These are the load-bearing substrings each test asserts (so the assertions are
derived from this plan, not reverse-engineered):

- Upward (any gate `NN`): `"crossed the NN% knitting threshold"`,
  `"gate done_NN is still false"`, `"set-gate --knitting-NN"`, and
  `"Do not hand-edit [gates]"`.
- Downward (any gate `NN`): `"left drafting below the NN% knitting threshold"`,
  `"gate done_NN is recorded true"`, `"Adjudicate"`, and the **absence** of
  `"set-gate --knitting-NN"` (asserted with `assert "set-gate" not in line` on
  the downward line — proving the upward-shaped remedy cannot leak into the
  downward path, the pre-mortem's most likely incident).

Edit `novel_ralph_skill/commands/_recount.py`, function `recount()`. The current
line 149 is `_refuse_if_incoherent(proposed, context="recount")`. Add a
module-private `_gate_ratio_remedy(state: State) -> list[str]` building the
lines above, then change line 149 to
`_refuse_if_incoherent(proposed, context="recount", remedy=_gate_ratio_remedy)`.
The callable returns `[]` when no knitting gate disagrees (so it is a harmless
no-op when some *other* invariant is the sole breach — the helper only appends
when the returned sequence is non-empty).

Must keep: exit `3` (not `1`), `state.toml` byte-for-byte intact on refusal, no
`[pending_turn]` bracket, no `[gates]` write (Constraints). The remedy is
**pure text**: it reads `state` and returns strings, never mutates.

Docs to read first: design §4.1, §5.4 recovery rule 1 (lines 600-611);
users-guide set-gate (lines 285-298); the `_refuse_if_incoherent` and
`EnvelopeMessagesError`/`StateInputError` docstrings.

Skills to load: `python-router` → `python-errors-and-logging` (exception
construction, `raise … from`, message discipline);
`python-iterators-and-generators` for the per-gate enumeration;
`python-types-and-apis` for the `remedy` callable keyword's precise typing.

Tests this item must add/update:

- `tests/test_recount_unit.py` — three additions:
  1. **Upward** companion (new): a previously-coherent tree whose drafts have
     grown so a recount crosses the 30% threshold while `done_30` is still
     `false`. Assert exit `3`, that the error names `gate-ratio-consistent`,
     that its messages contain the **upward** substrings above for `NN=30`
     (`"crossed the 30% knitting threshold"`, `"set-gate --knitting-30"`,
     `"Do not hand-edit [gates]"`), and that `state.toml` is byte-for-byte
     unchanged. Use the existing `_refuses_leaving_file_intact` helper.
  2. **Downward** (extend `test_recount_legitimate_gate_breach_refuses`, line
     237): keep the existing exit-3 + invariant-name assertion, and add
     assertions for the **downward** substrings for `NN=80`
     (`"left drafting below the 80% knitting threshold"`,
     `"gate done_80 is recorded true"`, `"Adjudicate"`) **and**
     `"set-gate --knitting-80" not in <the downward remedy line>` — proving the
     upward remedy never leaks downward (resolves B2 at the unit level).
  3. **Multi-gate fan-out** (new, parametrized): a tree where a recount lifts
     the ratio past both 30% and 50% with both gates `false`; assert the
     messages contain **both** `"set-gate --knitting-30"` and
     `"set-gate --knitting-50"`.
- Verification choice (cite `python-verification`): the message is a fixed
  template over an enumerable trigger (three thresholds × two directions, plus
  the multi-gate fan-out), so parametrized example-based unit tests are the
  right adversary, **not** Hypothesis — there is no new range-of-inputs
  invariant, only a finite message matrix. Record this in the Decision Log when
  implementing.

### Work item 3 — Behavioural + e2e proof of the actionable refusal

Goal: prove the user-visible, externally observable behaviour end to end.

Implements: AGENTS.md "Add end-to-end tests where a change affects … command-
line behaviour"; the roadmap success criterion "a behavioural test asserts the
actionable message".

Add **two** behavioural scenarios (one per direction — resolves B2 at the
user-visible level):

- **Upward** scenario in `tests/features/recount.feature`: "recount refuses with
  an actionable upward message when it would cross a knitting gate". Given a
  drafting tree whose drafts have grown past the 30% threshold while `done_30`
  is still false; When recount runs; Then recount exits 3, and the message
  contains `"crossed the 30% knitting threshold"`, `"set-gate --knitting-30"`,
  and `"Do not hand-edit [gates]"`; And `state.toml` is unchanged.
- **Downward** scenario in `tests/features/recount.feature`: "recount refuses
  with a non-prescriptive downward message when the recorded gate no longer
  matches the drafts". Given a tree whose hand-typed counts cross 80% with
  `done_80` true but whose `draft.md` files are empty (the existing
  `test_recount_legitimate_gate_breach_refuses` shape); When recount runs; Then
  recount exits 3, and the message contains `"left drafting below the 80%
  knitting threshold"`, `"gate done_80 is recorded true"`, and `"Adjudicate"`;
  And the message does **not** contain `"set-gate --knitting-80"`; And
  `state.toml` is unchanged. This is the acceptance-level proof B2 requires that
  the downward path ships a coherent, non-misleading message.
- Add the matching steps to `tests/steps/recount_steps.py`, reusing the existing
  `_run_recount` driver and the `working_corpus`/tree builder. Capture the
  exit-3 envelope's `messages` (drive through `run` and read the emitted
  envelope, as the existing steps do) to assert the substrings. Add a step that
  asserts a substring is **absent** for the downward "no set-gate" assertion.

Add installed-binary e2e — **both directions** (resolves B2 end to end):

- In `tests/test_recount_e2e.py`, add two POSIX-only, `@pytest.mark.slow`,
  `@pytest.mark.timeout(180)` tests mirroring
  `test_installed_novel_state_recount_state_error_exits_three` (lines 150-181):
  - **Upward**: build a tree that triggers the upward gate-ratio refusal at 30%;
    run the installed `novel-state recount` through the established cuprum
    pattern (`Program(str(installed_novel_state))`, the
    `single_program_catalogue` **suite fixture** — not a cuprum export, see
    Artifacts/A3,
    `sh.make(prog, catalogue=catalogue)("state", "recount").run_sync(
    context=ExecutionContext(cwd=run_dir), capture=True)`); assert exit `3`,
    `envelope["ok"] is False`, the upward substrings in the envelope `messages`,
    and no `Traceback` on stderr.
  - **Downward**: build the empty-draft/`done_80=true` tree; run the same way;
    assert exit `3`, `envelope["ok"] is False`, the downward substrings, and
    `"set-gate --knitting-80"` **absent** from every `messages` entry.
  The `make`/`run_sync`/`ExecutionContext`/`ProgramCatalogue` surface is locked
  in cuprum 0.1.0 (verified in `/data/leynos/Projects/cuprum/cuprum/sh.py` lines
  169, 441, 528 and `cuprum/catalogue.py` line 59).

Docs to read first: developers-guide lines 159-186 (the entry-point e2e and the
crossed-knitting-gate proof) and lines 282-295 (set-gate as the repair mutator);
ADR-006 (POSIX-only console-script e2e).

Skills to load: `python-router` → `python-testing` (pytest-bdd scenarios,
marks, parametrization, the installed-binary fixture pattern); `python-
verification` to confirm example-based behavioural/e2e is the right level (it
is — this is a contract assertion, not a property).

Tests this item adds: two pytest-bdd scenarios (upward + downward, feature +
steps) and two installed-binary e2e tests (upward + downward), plus, if cheap, a
fast in-process entry-point variant through `stub.novel_state()` mirroring
`test_entry_point_recount_reachable_exits_zero`, asserting the exit-3 envelope
and the upward message — a fast non-`slow` proof that does not need the wheel
build. The dual-direction coverage at the behavioural and e2e levels is the
direct resolution of design-review B2.

### Work item 4 — Document the coupling in the developers' guide

Goal: a developer reading `docs/developers-guide.md` understands why a recount
can refuse on `gate-ratio-consistent` and what the actionable message says.

Implements: AGENTS.md "Document internally facing … practices in
`docs/developers-guide.md`"; design §4.1, §5.4 recovery rule 1.

Edit `docs/developers-guide.md`. After the existing `gate-ratio-consistent`
discussion (lines 615-674), add a short subsection ("The recount-gate
coupling") explaining: recount re-derives `[word_counts]` only and never writes
`[gates]`; a recount that would cross a 30/50/80% threshold while the gate flag
lags is refused with exit `3` on `gate-ratio-consistent` (it must not synthesise
the "pass integrated" fact disk does not store); the refusal message names the
crossed threshold and points at `novel-state set-gate --knitting-NN` as the
repair once the pending knitting pass is integrated. Cross-reference the
existing set-gate "repair mutator" wording (lines 282-295).

Docs to read first: design §4.1, §5.4 recovery rule 1; developers-guide lines
605-695 and 282-295.

Skills to load: `en-gb-oxendict` (Oxford spelling); no code skill.

Tests: documentation only — no unit tests. Validation is `make markdownlint`
and `make nixie` plus `make all` (the markdown lint gate). No Mermaid diagram is
added, but `make nixie` is run because the file is markdown (AGENTS.md).

### Work item 5 — Document the coupling in the users' guide and the skill

Goal: an operator (human or agent) reading `docs/users-guide.md` and the skill
knows a recount can refuse on the gate ratio and that `set-gate` is the remedy.

Implements: AGENTS.md "Update `docs/users-guide.md` for any change to
application behaviour … users should know about"; the skill is the agent's
operating manual.

Note (resolves advisory A1): the users' guide **already** documents this
coupling from the set-gate side — lines 289-298 describe
`set-gate --knitting-30` as "the **repair** for a gate that lags its ratio (for
example after a `recount` moved the ratio past 30% but `done_30` is still
off)". The recount paragraph (lines 241-249) does not yet point forward to it.
So the work here is a single **forward cross-link**, not a duplicate
description of the rule — avoid restating the set-gate prose (which would risk
drift between two copies of the same rule).

Edit `docs/users-guide.md`: in the recount paragraph (lines 241-249) add one
sentence that a recount refuses with exit `3` (writing nothing) when it would
cross a knitting-gate threshold the recorded gates do not yet reflect, naming
the crossed threshold, and cross-link **to the existing** set-gate paragraph
(lines 285-298) as the remedy once the pending knitting pass is integrated. Do
not
duplicate the set-gate "repair" wording; point at it.

Edit `skill/novel-ralph/references/state-layout.md`: in the Gates section (lines
205-219) and/or beside the recount mention, state the coupling for the agent:
after a knitting pass is integrated, run `novel-compile`/`recount` then
`set-gate --knitting-NN`; if a recount refuses on `gate-ratio-consistent`, it is
telling you a threshold was crossed but the gate still lags — integrate and flag
the pass, do not hand-edit.

Docs to read first: users-guide lines 241-298; skill state-layout.md lines
205-243; `skill/novel-ralph/SKILL.md` lines 461-465 (the existing knitting-gate
flip instruction).

Skills to load: `en-gb-oxendict`; no code skill.

Tests: documentation only. Validation is `make markdownlint`, `make nixie`, and
`make all`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-7`.

Before starting, confirm a red baseline for the new behaviour by writing the
work-item-3 behavioural step first (red), then implementing work items 1-2
(green). Per work item:

1. Make the edit(s) named in the Plan of work.
2. Run the focused suite, for example:

        uv run pytest tests/test_recount_unit.py tests/test_validate_state_details.py -q

3. Regenerate any affected snapshot intentionally and review the diff:

        uv run pytest tests/test_set_gate_snapshots.py --snapshot-update -q
        git diff -- tests/__snapshots__

4. Run the full gate before committing:

        make all

5. For documentation work items, additionally run:

        make markdownlint
        make nixie

6. Commit the work item (gated) with an en-GB Oxford-spelled message that cites
   roadmap task 2.3.7 and the design sections it implements.

Expected transcript shape for the new unit assertion (illustrative):

    tests/test_recount_unit.py::test_recount_upward_gate_breach_is_actionable PASSED

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Upward direction.** Driving `novel-state recount` over a drafting tree
  whose drafts have grown past the 30% threshold while `done_30` is still
  `false` exits `3`, writes nothing, and emits an envelope whose `messages`
  contain "crossed the 30% knitting threshold", "set-gate --knitting-30", and
  "Do not hand-edit [gates]". The upward behavioural scenario in
  `tests/features/recount.feature`
  and the upward installed e2e in `tests/test_recount_e2e.py` both fail before
  the change and pass after.
- **Downward direction.** Driving `novel-state recount` over the
  empty-draft/`done_80=true` tree exits `3`, writes nothing, and emits an
  envelope whose `messages` contain "left drafting below the 80% knitting
  threshold", "gate done_80 is recorded true", and "Adjudicate", and which do
  **not** contain "set-gate --knitting-80" (the downward path must not prescribe
  the upward repair verb). The downward behavioural scenario and the downward
  installed e2e prove this at the user-visible level (resolves B2).
- The existing recount idempotence/correctness scenario, the pure-validator
  property suite, and the whole-corpus agreement cross-check stay green
  (`gate-ratio-consistent` and its verdict are unchanged; only prose differs).
- `docs/developers-guide.md`, `docs/users-guide.md`, and
  `skill/novel-ralph/references/state-layout.md` each document the recount-gate
  coupling and the set-gate remedy.

Quality criteria (what "done" means):

- Tests: `make all` passes (it runs the unit, behavioural, property, and
  in-process e2e suites). The new behavioural scenario and installed e2e pass;
  pre-existing recount/validator/gate suites stay green.
- Lint/typecheck: `make all` includes ruff and the type check; expect no new
  violations. For the documentation items, `make markdownlint` and `make nixie`
  pass with no errors.
- Performance: not applicable.
- Security: not applicable.

Quality method (how we check): run `make all` after every work item; for
documentation items also run `make markdownlint` and `make nixie`. Review each
regenerated snapshot diff by hand.

## Idempotence and recovery

Every step is re-runnable. The edits are text edits; re-running `make all` after
a fix is safe. Snapshot regeneration is the only non-idempotent step — review
the `git diff` of `tests/__snapshots__` before committing, and revert with
`git checkout -- tests/__snapshots__` if the churn is not a real contract
change. No `working/` tree or persistent state is mutated by this work; the
behavioural and e2e tests build throwaway trees under `tmp_path`.

## Artefacts and notes

- Verified cuprum 0.1.0 API (locked, `uv.lock` line 113-118): `cuprum/sh.py`
  defines `make`, `run_sync(*, capture=True, echo, context)`, `ExecutionContext`
  (with `cwd`), and the `capture` flag; `cuprum/catalogue.py` defines
  `ProgramCatalogue`. The existing `tests/test_recount_e2e.py` uses exactly this
  surface, so the new e2e reuses it verbatim — no new cuprum capability needed.
- Verified the `set-gate` flag-to-gate mapping in
  `novel_ralph_skill/commands/_gate_drafting_mutators.py` (lines 71-93):
  `--knitting-30 → done_30`, `--knitting-50 → done_50`, `--knitting-80 →
  done_80`. The remedy line points at these existing flags.

## Interfaces and dependencies

No public interface changes are expected. The function bodies edited are:

- `novel_ralph_skill.state.validate._check_gate_ratio_consistent(state: State)
  -> Violation | None` — unchanged signature; richer `detail` prose only.
- `novel_ralph_skill.commands._recount.recount() -> CommandOutcome` — unchanged
  signature; refusal path augmented with the recount-specific remedy.
- `novel_ralph_skill.commands._state_mutators._refuse_if_incoherent(state:
  State, *, context: str, remedy: cabc.Callable[[State], cabc.Sequence[str]] |
  None = None) -> None` — the pinned shape 2 (Decision Log). A
  backward-compatible keyword defaulting to `None`; when non-`None` and the
  verdict is non-empty, the lines returned by `remedy(state)` are appended after
  the per-violation details. The keyword has 11 call sites across five files;
  recount is the sole caller that passes `remedy`. The other 10 omit it and are
  unchanged: `_reconcile.py` (recount and reconcile), `_set_chapters.py`
  (set-chapters), `_state_mutators.py` (set-cursor and two advance-phase calls),
  and `_gate_drafting_mutators.py` (set-gate, complete-final-pass, set-fangirl,
  set-critic-pass). If this would
  force any other caller to change, abandon shape 2 for shape 1 (Tolerances).
- `novel_ralph_skill.commands._recount._gate_ratio_remedy(state: State) ->
  list[str]` — new module-private pure function returning the per-gate
  direction-aware remedy lines (empty when no knitting gate disagrees).

No new runtime or dev dependencies. Locked: cyclopts + tomlkit (runtime),
cuprum 0.1.0 + pytest/pytest-bdd/syrupy/hypothesis (dev).

## Revision note

Initial draft (2026-06-26): first planning round for roadmap task 2.3.7.

Round 2 (2026-06-26): resolved both Logisphere design-review blocking points
from `roadmap-2-3-7.logisphere-review-r1.md` and folded in advisories A1-A5.

- **B1 (message template unspecified):** Work item 2 now pins the exact
  per-gate, direction-aware message template, with worked examples for 30/50/80
  upward and an 80 downward case, plus the explicit acceptance substrings each
  test asserts. The percentage and ratio are derived from the validator's own
  `GATE_THRESHOLDS` and recounted ratio; the command layer enumerates per-gate
  disagreements rather than recomputing a "crossed threshold". The shape is
  committed (shape 2, the `remedy` callable keyword), not left as a menu.
- **B2 (downward message incoherent / untested at acceptance level):** the
  downward line is specified verbatim and deliberately omits `set-gate
  --knitting-NN` ("the recorded gate no longer matches the drafts. Adjudicate
  …"). The dual-direction promise is now proven at the user-visible level: Work
  item 3 adds a downward behavioural scenario and a downward installed e2e (each
  asserting the downward substrings **and** the absence of the upward
  `set-gate` verb), alongside the upward pair; the unit suite (Work item 2) adds
  the same absence assertion. Validation/Acceptance drives both directions.
- **A1:** Work item 5 now records that the users' guide already documents the
  coupling from the set-gate side (lines 289-298) and scopes the work to a
  forward cross-link, not duplicate prose.
- **A2:** shape 2 pinned (validates once), shape 1 (double-validation) rejected.
- **A3:** Decision Log corrected — `single_program_catalogue` is the suite
  fixture, not a cuprum export.
- **A5:** Work item 1 states the threshold rendering precision (two decimals;
  not three) so the substring assertion passes on the first green cycle.

## Addenda

Lightweight, no-plan corrections to this completed task. Each runs as a
no-review lightweight pass.

- [x] **2.3.7.1 Correct the `_refuse_if_incoherent` caller enumeration (from
  review:2.3.7; low).** The Interfaces and dependencies section (and the
  Decision Log / Work item 2 reasoning) state that `_refuse_if_incoherent` has
  four other callers (`set_cursor`, `advance_phase`, `set_gate`, `reconcile`).
  The actual set is 11 call sites across five files — `commands/_reconcile.py`,
  `commands/_recount.py`, `commands/_set_chapters.py`,
  `commands/_state_mutators.py` (`set-cursor`, two `advance-phase` calls), and
  `commands/_gate_drafting_mutators.py` (`set-gate`, `complete-final-pass`,
  `set-fangirl`, `set-critic-pass`). The shape-2 `remedy=None`-default
  conclusion is unaffected (no caller changed), but the stale four-caller
  premise understates the keyword's blast radius for a future implementer.
  Correct the enumeration to the real call-site set. Lightweight addendum pass.
- [x] **2.3.7.2 Render the recount remedy ratio without a boundary
  self-contradiction (from review:2.3.7; low).**
  `_recount._gate_ratio_remedy` renders the drafted ratio
  with `f"{ratio * 100:.0f}"`, so a ratio of `0.298` prints `30%` inside the
  downward "below the … threshold (drafts now at 30% of target)" sentence,
  reading as a contradiction for an operator near a gate boundary (R2 advisory
  A8, neither mitigated nor documented). The verdict and exit code are
  unaffected; this is a cosmetic operator-UX wart. Render the ratio with one
  decimal, or document the boundary-rounding edge inline, so the message cannot
  read as self-contradictory at a gate boundary. Lightweight addendum pass.
