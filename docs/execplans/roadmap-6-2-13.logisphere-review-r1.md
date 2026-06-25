# Logisphere design review — roadmap task 6.2.13, round 1

Adversarial pre-implementation review of
`docs/execplans/roadmap-6-2-13.md` (the command-boundary ROLLBACK proof for an
unrecoverable `done.flag`).

Verdict: **Proceed** (no blocking defects). One advisory and two minor notes.

## What was verified against real source (not the planner's summary)

- **Mechanism, empirically proven.** The review constructed the plan's proposed
  scenario (a real §3.4 `pending_turn` bracket over `COHERENT_BASELINE` declaring
  `working/manuscript/chapter-99/done.flag`, raising mid-turn) and drove `check`
  through `novel_ralph_skill.contract.runner.run`. Observed: exit `4`,
  `reconciliation.action == "rollback-pending-turn"`,
  `discrepancies == ["pending-turn-cleared"]`. The refuse-class
  `done-flag-without-draft` contradiction does **not** pre-empt. This confirms
  Decision D-DONEFLAG-CLEAN end-to-end.
- **Precedence path confirmed in source.** `derive_reconciliation`
  (`reconcile.py:256-265`) checks refuse-class first, then the pending-turn
  branch. `_check_done_flag_without_draft` (`disk_evidence.py:148-164`) iterates
  `state.chapters` (the manifest) and requires an on-disk `done.flag`; chapter-99
  is outside the manifest and nothing lands, so it cannot fire. Citations in the
  plan (`reconcile.py:89`, `:190-206`; `disk_evidence.py:136-156`) are accurate.
- **Baseline green.** `tests/test_torn_turn_rollback_bdd.py` passes as-is; the
  `draft.md` producer behaves exactly as the plan describes.
- **Infrastructure.** `make all` = `build check-fmt lint typecheck test`
  (Makefile:28). `make build`, `make markdownlint` (`**/*.md`), `make nixie` all
  exist. `pytest-bdd>=8.1.0` locked (pyproject.toml:30). Dependency 6.2.7 is
  `[x]` complete. Deferral targets 7.23.3 and 7.23.4 are real open roadmap tasks.
- **`operation` is a free string** the classifier never branches on
  (`reconcile.py:204` echoes `pending.operation`). `mark-done` is an honest verb;
  there is no canonical production flag-writing operation to match against.

## Advisory (would smooth implementation; not blocking)

- **A1. The step decorators must change from plain strings to parsers — the plan
  does not say so.** The current rollback module binds steps with plain-string
  `@given("a real pending_turn bracket raises ...")` / `@then("... write-draft
  ...")` decorators that capture **no** argument. To thread `<declared_path>` and
  `<operation>` from an `Examples` row, the decorators must be rewritten as
  `parsers.parse('... "{declared_path}" ...')` (adding `from pytest_bdd import
  parsers`), exactly as `tests/steps/novel_done_steps.py:86` does for `{clause}`.
  The plan calls this "bind it via the step's parsed argument" without naming the
  parser conversion or the import, so a literal-minded implementer could convert
  the feature to a `Scenario Outline` and stall when the placeholder does not
  reach the step. The precedent file is cited, so a careful implementer recovers,
  but spelling out "switch the producer Given and the leftover-record Then to
  `parsers.parse` with `{declared_path}`/`{operation}` placeholders" removes the
  trap.

## Minor

- **M1. `nixie` justification is imprecise.** `make nixie` validates Mermaid
  diagrams; the plan justifies it as "required because this plan file is under
  `docs/`". It is harmless to run (and house gating practice), but neither the
  ExecPlan nor the `.feature` file contains Mermaid, so the stated reason is off.
  No action required beyond running the gate.
- **M2. Line-count drift in prose.** The plan says the step module is "291 lines";
  it is 290. Immaterial to the 400-line cap.

## Crew lenses (summary)

- Pandalump — boundaries sound; single atomic commit over three coupled files is
  correctly justified; no-production-code is `git diff --stat`-verifiable.
- Wafflecat — Scenario Outline vs `parametrize` weighed (D-SHAPE) with a retained
  fallback; the house idiom choice is defensible.
- Buzzy Bee — one test row; xdist+timeout(30s) inherited from a proven-green
  sibling, no new concurrency surface.
- Telefono — the basename-exclusion contract and the JSON envelope are both
  verified against real behaviour.
- Doggylump — the sole real risk (refuse-class pre-emption) has an explicit
  escalation tolerance and was empirically ruled out.
- Dinolump — D-DUP / D-LITERAL deferrals point at open tasks 7.23.3 / 7.23.4;
  no scope creep, debt recorded.

## Pre-mortem

Most plausible failure six months out: a future third recomputable basename added
to `_RECOMPUTABLE_BASENAMES` silently reclassifies the hand-picked trigger, and
this test passes green for the wrong reason (audit Finding 4 / D-LITERAL). The
plan correctly defers the corpus-source-of-truth fix to 7.23.4 rather than
inventing it here. No incident is designed-in by this task.

Trail followed: `docs/roadmap.md` (6.2.7, 6.2.12, 6.2.13, 7.23.3, 7.23.4),
`docs/issues/audit-6.2.7.md` (Findings 3, 4), `novel-ralph-harness-design.md`
§3.4 / §5.4, `novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/disk_evidence.py`, `tests/features/novel_done.feature`,
`tests/steps/novel_done_steps.py`, the existing rollback suite, `Makefile`,
`pyproject.toml`. Skills: `logisphere-design-review`, `python-router` →
`python-testing` (pytest-bdd parser/Outline discipline).
