# Share the compiled-matches-drafts comparison between the §5.4 detector and the `compile_consistent` clause

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

The novel harness has two independent pieces of code that each answer the
question "does `working/manuscript/compiled.md` equal the ordered concatenation
of the present chapter drafts?":

1. the §5.4 disk-evidence detector
   `novel_ralph_skill/state/disk_evidence.py::_check_compiled_matches_drafts`,
   which recomputes the ordered draft concatenation and compares bytes, treating
   an *absent* `compiled.md` as trivially satisfied (no violation); and
2. the `compile_consistent` done-clause
   `novel_ralph_skill/state/done_predicate.py::compile_consistent_exists`, which
   today is *existence-only* (a present `compiled.md` holds, an absent one does
   not) and which roadmap task 3.1.2 is scheduled to upgrade to the full
   present-but-stale comparison.

Today the comparison logic lives only inside the detector. If 3.1.2 lands
without a shared seam, it will re-implement "compiled matches the drafts" a
third time (the detector, the future clause, and the test-side corpus oracle
each computing it), with the real risk that the detector and the clause drift to
*different verdicts on the same tree* — exactly the kind of silent disagreement
the step-3.1 hypothesis exists to prevent (every done clause evaluated
deterministically against disk, agreeing with the disk-evidence detector).

This task — roadmap 3.1.3 (`docs/roadmap.md:941-964`) — factors the comparison
into **one shared helper** `compiled_matches_drafts(state, working_dir)` in
`novel_ralph_skill/state/compile_model.py`, and routes **both** the §5.4
detector and the `compile_consistent` clause through it. Each caller supplies
its own absent-file polarity (the detector treats absent as satisfied; the
clause treats absent as not-done). After this change there is exactly one
production site that decides "compiled matches drafts", so the detector and the
predicate cannot disagree, and 3.1.2 inherits the seam rather than re-deriving
the rule.

**This is a pure, behaviour-preserving refactor.** No observable verdict
changes: the detector still fires `compiled-matches-drafts` on the same trees,
and `compile_consistent` stays existence-only (its 3.1.1-shipped semantics) until
3.1.2 swaps in the full comparison. A user running `novel-state check` or
`novel-done` before and after this change sees byte-identical envelopes on every
tree.

Success is observable by running `make all`: the done-predicate suite
(`tests/test_done_predicate.py`,
`tests/test_working_corpus_done_predicate.py`), the disk-evidence suite
(`tests/test_disk_evidence.py`,
`tests/test_working_corpus_disk_divergence.py`,
`tests/test_novel_state_check_disk.py`), and the compile suites all stay green,
and a new unit test pins the three-valued helper and the two callers' polarity
projections.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** This is a refactor. Every `novel-state check`,
  `novel-done`, and `novel-compile --check` envelope must stay byte-identical on
  every tree before and after. In particular `compile_consistent` stays
  existence-only (a present `compiled.md` holds; an absent one does not); this
  task does **not** add the present-but-stale comparison or the exit-`4`
  carve-out — those belong to roadmap 3.1.2 (`docs/roadmap.md:922-940`; design
  §4.2 status note at `docs/novel-ralph-harness-design.md:310-314`). See Decision
  Log D-SCOPE.
- **Detector absent-file polarity is preserved.** `_check_compiled_matches_drafts`
  must keep returning `None` (no violation) when `compiled.md` is absent and a
  `Violation(invariant=COMPILED_MATCHES_DRAFTS, …)` only when `compiled.md` is
  *present and diverges* (`disk_evidence.py:167-188`; design §5.4 at
  `docs/novel-ralph-harness-design.md:541-590`).
- **Clause absent-file polarity is preserved.** The `compile_consistent` clause
  must keep returning `False` for an absent `compiled.md` and `True` for a
  present one, with no inspection of content (3.1.1 D-COMPILE-EXISTENCE;
  developers' guide §"`compile_consistent` is the existence half only" at
  `docs/developers-guide.md:572-579`).
- **One production join rule only.** The helper must compute the expected
  compilation through the existing single read/join rule —
  `compile_model.present_draft_bodies` then `compile_model.concatenate_drafts`
  (`compile_model.py:38-103`) — so a freshly compiled tree stays coherent under
  the detector by construction (3.1.1/4.1.1 D-READ; design §4.3 at
  `docs/novel-ralph-harness-design.md:383-386`). No second concatenation or
  comparison may appear.
- **The corpus oracle stays an independent twin.** The test-side oracle
  `tests/working_corpus/_oracle_disk.py::_check_compiled_matches_drafts`
  (`_oracle_disk.py:137-149`) is a *deliberate independent cross-check* and must
  **not** import the production helper. The deliberate-twin policy (developers'
  guide §"Invariant validation"; `disk_evidence.py:26-34`) requires the oracle to
  re-implement the comparison so a production bug cannot mask itself. This task
  must not collapse the oracle into the helper. See Decision Log D-TWIN.
- **Read-only / CQS.** Every touched function stays a pure
  `(State, working_dir) -> …` query that writes nothing on any path (ADR-001,
  `docs/adr-001-deterministic-judgemental-boundary.md`; design §3.3 at
  `docs/novel-ralph-harness-design.md:235-307`).
- **Fault boundary preserved.** A *missing* `draft.md` contributes `""` (benign);
  every other read fault (`PermissionError`, `IsADirectoryError`,
  `UnicodeDecodeError`) propagates for the command layer to route to exit `3`
  (`compile_model.py:64-74`; developers' guide §"The fault boundary" at
  `docs/developers-guide.md:581-586`). The helper must not catch or reshape these.
- **No single file exceeds 400 lines** (AGENTS.md:24). `compile_model.py` is 104
  lines today; the helper adds well under the cap. `disk_evidence.py` (301) and
  `done_predicate.py` shrink slightly.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, docstrings, and
  commit messages (workflow standing rules; en-gb-oxendict skill).

## Tolerances (exception triggers)

- **Scope:** if implementation requires touching more than 6 files or more than
  ~120 net lines of code, stop and escalate. Expected surface: `compile_model.py`,
  `disk_evidence.py`, `done_predicate.py`, `novel_ralph_skill/state/__init__.py`,
  one or two test files, and one developers'-guide paragraph.
- **Interface:** the helper is a *new* public symbol on `compile_model`; if any
  *existing* exported signature (`present_draft_bodies`, `concatenate_drafts`,
  `check_disk_evidence`, `evaluate_done`, `compile_consistent_exists`) must
  change shape, stop and escalate.
- **Verdict drift:** if any existing test in the done-predicate, disk-evidence,
  corpus-agreement, or compile suites changes its expected value (rather than
  merely its imports), stop and escalate — that signals a behaviour change, which
  this refactor forbids.
- **Dependencies:** no new external dependency. If one seems required, stop and
  escalate.
- **Iterations:** if `make all` still fails after 3 fix attempts on a work item,
  stop and escalate.
- **Ambiguity:** the helper's return shape is decided in D-SHAPE below; if review
  rejects the three-valued enum in favour of a different seam, stop and escalate
  rather than improvising a second shape.

## Risks

- Risk (R-SHAPE): A two-valued `bool` helper ("present and matches") cannot
  serve the detector, because the detector must distinguish *absent* (no
  violation) from *present-but-stale* (violation); a bool collapses both to
  `False`. Severity: high. Likelihood: high (this is the core design trap the
  audit names). Mitigation: the helper returns a three-valued result
  (`ABSENT` / `MATCHES` / `DIVERGES`); each caller projects it to its own
  polarity. Pinned by D-SHAPE and Work Item 1's unit test.

- Risk (R-DRIFT): Routing the detector or clause through the helper subtly
  changes a verdict (mishandling the absent case, or the empty-manifest case).
  Severity: high. Likelihood: low. Mitigation: the existing disk-evidence,
  corpus-agreement, and done-predicate suites already pin every verdict on the
  corpus trees and on tmp-path fixtures; they must stay green unmodified except
  for imports. The corpus oracle (an independent twin that does not use the
  helper) keeps cross-checking the detector on every corpus tree.

- Risk (R-PREEMPT): The helper accidentally couples the existence-only clause
  to content, pre-empting 3.1.2 and changing the exit code on a
  present-but-stale tree. Severity: medium. Likelihood: low. Mitigation: the
  clause projection maps `ABSENT` to `False` and both `MATCHES` and `DIVERGES`
  to `True`, so it ignores the `DIVERGES`/`MATCHES` distinction and stays
  existence-only. A unit test pins that a present-but-stale tree still makes
  `compile_consistent` `True` (the documented residual window). D-SCOPE.

- Risk (R-TWIN): The corpus oracle is collapsed into the helper, destroying the
  independent cross-check. Severity: medium. Likelihood: low. Mitigation:
  Constraint "corpus oracle stays an independent twin"; D-TWIN; the oracle file
  is explicitly out of scope.

## Progress

- [x] Work Item 1 — Factor the three-valued `compiled_matches_drafts` helper
  into `compile_model.py` with a unit test (not yet routed in). Done: the enum
  and helper live in `compile_model.py`, are re-exported from `state/__init__.py`,
  and are pinned by six unit tests in the new `tests/test_compiled_matches_drafts.py`
  (split out so neither `compile_model.py` nor any test module breaches the
  400-line cap; see D-TESTFILE).
- [x] Work Item 2 — Route `disk_evidence._check_compiled_matches_drafts`
  through the helper, preserving absent-file polarity. Done: the detector now
  calls `compiled_matches_drafts` and projects `DIVERGES -> Violation`, else
  `None`; the `concatenate_drafts`/`present_draft_bodies` import narrowed to the
  helper. The existing disk-evidence and corpus suites stayed green unedited, and
  a focused projection unit test was added to `tests/test_disk_evidence.py`.
  coderabbit r1: 0 findings.
- [x] Work Item 3 — Route the `compile_consistent` clause through the helper,
  preserving existence-only polarity. Done: `compile_consistent_exists` kept its
  name (D-SCOPE default) and gained a `state` parameter; it now projects
  `ABSENT -> False`, present `-> True` via the shared helper. `evaluate_done`
  passes `state`; the three calls in `test_done_predicate.py` gained the `state`
  argument with no expected-value change; the present-but-stale tree still
  asserts `True`. No snapshot churn. coderabbit r1 hit a rate limit (~8m38s),
  retried after ~9 min wait: 0 findings.
- [x] Work Item 4 — Update the developers' guide to record the shared seam and
  the two polarity projections. Done: the §"Done predicate" area gained a
  "One owner for ..." paragraph naming `compile_model.compiled_matches_drafts`,
  the two projections, 3.1.3 / audit-3.1.1 Finding 2, and the deliberate-twin
  carve-out; the compile-model description now says the *comparison* is shared
  too. `make markdownlint` and `make nixie` clean. coderabbit r1 rate-limited
  (~2m28s), retried after ~2.5 min: 0 findings.

## Surprises & discoveries

- Observation: `make all` does **not** run `pip-audit`; the `audit` target is
  separate. Evidence: `Makefile:28` (`all: build check-fmt lint typecheck test`)
  and `Makefile:104-105` (`audit: … pip-audit`). Impact: the validation recipe
  was corrected in planning round 2 so it no longer claims `make all` covers
  audit (B1).
- Observation: `make test` has no file-selection parameter; it is
  `pytest -v -n $(PYTEST_XDIST_WORKERS)` with `PYTEST_XDIST_WORKERS ?= auto`.
  Evidence: `Makefile:115-116` and `Makefile:14`. Impact: targeted red/green runs
  use `uv run pytest <file>` directly; `make test`/`make all` are reserved for
  the full gate (B2).
- Observation (Work Item 1): the plan placed the helper's unit tests in
  `tests/test_compile_unit.py`, but appending the six tests pushed that module to
  470 lines, over the AGENTS.md 400-line cap (caught by `pylint` `C0302`). Impact:
  the tests were moved to a dedicated `tests/test_compiled_matches_drafts.py`
  instead; `test_compile_unit.py` is unchanged from `main`. See D-TESTFILE.
- Observation (Work Item 1, coderabbit r1): coderabbit flagged the
  undecodable-draft test as too permissive (`pytest.raises(UnicodeDecodeError)`
  with no `match`). Tightened to `match="utf-8"` to pin the codec failure mode.
  The two other findings were second-person prose in `docs/execplans/` files;
  the active execplan was rewritten to impersonal voice, the historical
  `*.review-r2.md` review artifact was left untouched (a record, not a live doc).
- Observation (Work Item 3, coderabbit): the first `coderabbit review --agent`
  invocation returned a recoverable `rate_limit` (advertised wait ~8m38s). Waited
  out the window (~9 min) per the workflow backoff policy and retried once
  successfully: 0 findings. No work item was blocked.

## Decision log

- Decision (D-TESTFILE): The helper's unit tests live in a new
  `tests/test_compiled_matches_drafts.py` rather than appended to
  `tests/test_compile_unit.py` as the plan suggested. Rationale: appending the
  six tests pushed `test_compile_unit.py` to 470 lines, breaching the AGENTS.md
  400-line cap (`pylint` `C0302`). A dedicated module keeps both files under the
  cap and groups the helper's contract in one place; `test_compile_unit.py` is
  left byte-identical to `main`. Date/Author: 2026-06-24, implementer.

- Decision (D-SHAPE): The shared helper returns a three-valued result, not a
  `bool`. Introduce `compile_model.CompiledComparison`, an `enum.Enum` with
  members `ABSENT`, `MATCHES`, `DIVERGES`, and a function
  `compiled_matches_drafts(state, working_dir) -> CompiledComparison`.
  Rationale: the detector needs to tell *absent* (mapped to `None`) from
  *present-but-stale* (mapped to a `Violation`), and the clause needs *absent*
  (mapped to `False`) from *present* (mapped to `True`). A single `bool`
  ("present and matches") loses the absent/diverges distinction the detector
  requires, so it cannot serve both callers. A three-valued result is the
  smallest seam that lets each caller project its own polarity, which is
  precisely what the audit asks for ("each wrapping it with its own absent-file
  polarity", `docs/issues/audit-3.1.1.md` Finding 2). Date/Author: 2026-06-24,
  planner.

- Decision (D-SCOPE): This task does NOT change `compile_consistent` to catch a
  present-but-stale compile, and emits no exit `4`. Rationale: 3.1.3 "Requires
  3.1.1" only (`docs/roadmap.md:955`), and no 3.1.2 ExecPlan exists yet, so
  3.1.3 lands first. The behaviour swap (existence-only to present-but-stale
  detection) and the exit-`4` carve-out are 3.1.2's deliverable
  (`docs/roadmap.md:922-940`; design status note
  `docs/novel-ralph-harness-design.md:310-314`). 3.1.3 is the *refactor that
  prepares* 3.1.2: it builds the shared seam and wires the existence-only
  clause through it without altering the clause's verdict. The clause
  projection (`ABSENT` to `False`, otherwise `True`) is exactly today's
  existence-only semantics expressed through the shared helper. Date/Author:
  2026-06-24, planner.

- Decision (D-TWIN): The test-side corpus oracle
  `tests/working_corpus/_oracle_disk.py::_check_compiled_matches_drafts` is
  left untouched and does NOT call the production helper. Rationale: the
  deliberate-twin policy makes the oracle an independent cross-check; if it
  imported the helper it would no longer catch a production bug
  (`disk_evidence.py:26-34`; developers' guide §"Invariant validation"). The
  oracle's continued agreement with the helper-routed detector (pinned by
  `tests/test_novel_state_check_disk.py`) is itself the proof the refactor
  preserved behaviour. Date/Author: 2026-06-24, planner.

- Decision (D-RECIPE): The validation recipe gates this task on `make all`
  (build / check-fmt / lint / typecheck / test) only, plus `make markdownlint`
  and `make nixie` for the markdown work item. `pip-audit` (`make audit`) is
  explicitly **not** part of the gate and is optional here, because the diff adds
  no dependency. Targeted red/green iterations use `uv run pytest <file>` (the
  `test` target has no file-selection parameter and would fan a single file
  across `-n auto` workers). Rationale: round-1 review B1/B2 found the original
  recipe asserted a `make all`-covers-`pip-audit` gate and a non-existent
  `make test PYTEST_ADDOPTS=…` hook; both were corrected against the real
  `Makefile` (`:28`, `:104-105`, `:115-116`, `:14`). Date/Author: 2026-06-24,
  planner.

- Decision (D-NO-CUPRUM): No cuprum API and no external-library behaviour is
  load-bearing for this task. Rationale: the change touches only internal
  pure-Python modules (`compile_model.py`, `disk_evidence.py`,
  `done_predicate.py`, `state/__init__.py`) and their pytest suites. There is no
  subprocess, allowlist, executable, or `uv run`/Cyclopts/pytest-timeout surface
  in the diff. Validation runs through the repo's existing `make` targets. The
  workflow's cuprum/firecrawl research mandate therefore has no target here;
  asserting a researched external behaviour would be fabrication. If review
  disagrees and identifies a concrete external surface, stop and escalate.
  Date/Author: 2026-06-24, planner.

## Outcomes & retrospective

All four work items are complete and the acceptance criteria are met:

- **One production owner.** `compile_model.compiled_matches_drafts` is the single
  production site that decides "compiled matches drafts". Its only two production
  consumers are `disk_evidence._check_compiled_matches_drafts` and the
  `compile_consistent_exists` clause; no third production re-implementation
  survives. The test-side corpus oracle still owns its independent copy and does
  not import the helper (D-TWIN), as intended.
- **No verdict changed.** Every existing disk-evidence, corpus-agreement,
  done-predicate, snapshot, command, and e2e test stayed green with no
  expected-value or snapshot edits — only the `compile_consistent_exists` test
  calls gained the new `state` argument. The present-but-stale tree still makes
  the clause `True` (the residual window), and the detector still fires
  `compiled-matches-drafts` only on a present-and-stale tree.
- **Helper and projections pinned.** Six unit tests in
  `tests/test_compiled_matches_drafts.py` cover `MATCHES`/`DIVERGES`/`ABSENT`,
  the empty-manifest vacuous case, fault propagation, and the existence-before-read
  ordering; a focused projection test in `tests/test_disk_evidence.py` pins the
  detector's absent-file polarity.
- **Gates green.** `make all` is green at HEAD; `make markdownlint` and
  `make nixie` are clean for the docs item.

Deviations from the plan: the helper's unit tests live in a dedicated test
module (D-TESTFILE) to respect the 400-line cap, rather than being appended to
`tests/test_compile_unit.py`. No scope, interface, or verdict-drift tolerance was
tripped. `coderabbit` rate-limited twice (Work Items 3 and 4) and was retried
successfully after the advertised wait; one minor coderabbit finding (a
`pytest.raises` without a `match`) was addressed in Work Item 1.

## Context and orientation

The work happens inside the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-3` on branch
`roadmap-3-1-3`. Prefer `leta` (`leta show` / `leta refs` / `leta grep`) for
navigation and `sem` for history rather than ad-hoc ripgrep. Treat `docs/` as the
source of truth.

Three production modules under `novel_ralph_skill/state/` matter:

- `compile_model.py` (104 lines) owns the §4.3/§9 *draft-concatenation model*:
  `present_draft_bodies(state, working_dir) -> list[str]` reads each manifest
  chapter's `draft.md` (an absent draft contributes `""`) in ascending chapter
  order, and `concatenate_drafts(drafts) -> str` joins them with the single
  `DRAFT_SEPARATOR` (`"\n\n"`). This is the one production join rule the compile
  write path and the disk-evidence detector both reuse.

- `disk_evidence.py` (301 lines) is the §5.4 disk-evidence detector. Its
  `_check_compiled_matches_drafts(state, working_dir) -> Violation | None`
  (`disk_evidence.py:167-188`) returns `None` when `compiled.md` is absent
  (trivially satisfied) or when its bytes equal
  `concatenate_drafts(present_draft_bodies(state, working_dir))`, and a
  `Violation(invariant=COMPILED_MATCHES_DRAFTS, …)` when present-and-diverging.
  `COMPILED_MATCHES_DRAFTS` is the string `"compiled-matches-drafts"`
  (`disk_evidence.py:89`).

- `done_predicate.py` is the §4.2 done predicate. Its `compile_consistent`
  clause is `compile_consistent_exists(working_dir) -> bool`
  (`done_predicate.py:211-220`): `True` iff `manuscript/compiled.md` exists,
  with no content inspection. `evaluate_done` assembles it into `DoneClauses`
  (`done_predicate.py:287-294`).

Key term definitions:

- *Done clause*: one boolean condition in design §4.2 that must hold for the
  novel to be "done"; `compile_consistent` is one of six.
- *Disk-evidence invariant*: one §5.4 contradiction the detector reports as a
  `Violation`; `compiled-matches-drafts` is one of eight.
- *Deliberate twin*: a function intentionally re-implemented on the test side
  (`tests/working_corpus/`) so the test cross-checks production without importing
  it; the two must agree on every corpus tree, pinned by a test.
- *Absent-file polarity*: how each caller treats an absent `compiled.md`. The
  detector treats absent as *satisfied*; the existence-only clause treats absent
  as *not done*.

Design and doc anchors this task implements:

- `docs/novel-ralph-harness-design.md` §4.2 (`:308-360`, the done predicate and
  the shared compile-and-hash routine), §4.3 (`:362-387`, the single shared
  compile-and-hash routine both `novel-compile` and the done clause call), and
  §5.4 (`:513-590`, the disk-authoritative reconciliation that owns
  `compiled-matches-drafts`).
- `docs/issues/audit-3.1.1.md` Finding 2 (the named fix: one
  `compiled_matches_drafts(state, working_dir)` helper both callers consume).
- `docs/adr-001-deterministic-judgemental-boundary.md` (read-only checker
  boundary).
- `docs/developers-guide.md` §"Done predicate" (`:540-600`) and §"Invariant
  validation" (the deliberate-twin policy).
- `AGENTS.md` (quality gates, 400-line cap, CQS, en-GB Oxford spelling).

## Plan of work

The work decomposes into four ordered, independently committable, gate-passable
work items. Items 1 then 2 then 3 are the refactor proper; item 4 is the docs
pass. Each item ends with `make all` green (item 4 additionally with
`make markdownlint` and `make nixie`).

### Work Item 1 — Factor the three-valued `compiled_matches_drafts` helper

Add the shared comparison to `compile_model.py` without yet routing any caller
through it, so the seam is landed and unit-pinned in isolation.

In `novel_ralph_skill/state/compile_model.py`:

1. Add `import enum` (stdlib) and define a small enum near the top, after
   `DRAFT_SEPARATOR`:

   ```python
   class CompiledComparison(enum.Enum):
       """Three-valued verdict for compiled.md against the present drafts."""

       ABSENT = "absent"
       MATCHES = "matches"
       DIVERGES = "diverges"
   ```

2. Define the helper:

   ```python
   def compiled_matches_drafts(
       state: State, working_dir: Path
   ) -> CompiledComparison:
       ...
   ```

   It joins `working_dir / "manuscript" / "compiled.md"`; returns
   `CompiledComparison.ABSENT` when that path does not exist; otherwise compares
   `compiled.read_text(encoding="utf-8")` against
   `concatenate_drafts(present_draft_bodies(state, working_dir))` and returns
   `MATCHES` or `DIVERGES`. The docstring must (a) name design §4.3/§5.4 and
   audit-3.1.1 Finding 2 as the rationale, (b) state that both
   `disk_evidence._check_compiled_matches_drafts` and the `compile_consistent`
   clause consume it, each projecting its own absent-file polarity, (c) state
   that read faults other than the missing `compiled.md`/`draft.md` propagate
   (it does not catch them), and (d) keep en-GB Oxford spelling.

3. Export `CompiledComparison` and `compiled_matches_drafts` from
   `novel_ralph_skill/state/__init__.py` beside the existing `compile_model`
   re-exports (`__init__.py:27-31` import block and the `__all__` list), keeping
   `__all__` alphabetised as the file already is.

Docs to read first: design §4.3 (`docs/novel-ralph-harness-design.md:362-387`)
and §5.4 (`:513-590`); `docs/issues/audit-3.1.1.md` Finding 2; the existing
`compile_model.py` docstrings.

Skills to load: `python-router`, then follow it to `python-data-shapes` (the
`enum` choice for a closed three-state result; tagged-state modelling) and
`python-errors-and-logging` (confirm the helper propagates rather than swallows
non-absent read faults). Use `leta show compile_model` /
`leta refs concatenate_drafts` to confirm call sites.

Tests this item adds (in `tests/test_compile_unit.py`, the existing
`compile_model` unit home):

- Unit, happy path: a tmp tree with chapters and a `compiled.md` equal to
  `concatenate_drafts(present_draft_bodies(...))` returns
  `CompiledComparison.MATCHES`.
- Unit, divergence: a present-but-stale `compiled.md` (bytes differ) returns
  `CompiledComparison.DIVERGES`.
- Unit, absent: no `compiled.md` returns `CompiledComparison.ABSENT` regardless
  of the drafts.
- Unit, empty manifest: a `State` with no chapters and a present empty
  `compiled.md` (`concatenate_drafts([]) == ""`) returns `MATCHES`; absent
  returns `ABSENT`. This pins the vacuous case both callers rely on.
- Unit, fault propagation: an undecodable `draft.md` (non-UTF-8 bytes) beside a
  present `compiled.md` raises `UnicodeDecodeError` (a `ValueError` subclass),
  proving the helper does not swallow the fault (mirror the existing
  `present_draft_bodies` fault expectations if any; otherwise assert with
  `pytest.raises`).
- Unit, absent-first ordering (advisory A1): the *same* undecodable `draft.md`
  beside an **absent** `compiled.md` returns `CompiledComparison.ABSENT` and does
  **not** raise. This pins that the helper performs the existence check before it
  reads any draft, so a future refactor that reads drafts unconditionally is
  caught. Pair it with the present-`compiled.md` case above so the two together
  lock the ordering (raises only when `compiled.md` is present).

No property/snapshot/e2e test is required for this item: the helper is a pure
three-way classifier with a tiny finite contract, fully covered by the
example-based units above (AGENTS.md testing rules — property tests are for
invariants over a range of inputs, which the existence-vs-content distinction is
not; snapshot tests are for multivariant *output format*, which the enum is
not). Note in the Decision Log if a reviewer asks for a Hypothesis test over
random draft sequences; the candidate property would be
`compiled_matches_drafts(state, dir) is MATCHES` whenever `compiled.md` was
written as `concatenate_drafts(present_draft_bodies(state, dir))`.

Validation: `make all`. Expect all suites green, including the new unit tests.
The new tests must fail before the helper exists (write them red first by
importing `compiled_matches_drafts`, observe `ImportError`/failure) and pass
after.

Commit message (imperative, ~50 cols): `Add shared compiled_matches_drafts
helper`.

### Work Item 2 — Route the §5.4 detector through the helper

Make `disk_evidence._check_compiled_matches_drafts` consume the shared helper,
preserving its absent-file polarity exactly.

In `novel_ralph_skill/state/disk_evidence.py`:

1. Replace the body of `_check_compiled_matches_drafts` (`:167-188`) so it calls
   `compiled_matches_drafts(state, working_dir)` and projects:
   `ABSENT -> None`, `MATCHES -> None`, `DIVERGES -> Violation(invariant=
   COMPILED_MATCHES_DRAFTS, detail="compiled.md is not the ordered
   concatenation of the present drafts")`. Keep the existing `Violation` detail
   string byte-identical (it is asserted by tests). Update the imports
   (`disk_evidence.py:67-70`) to add `CompiledComparison` and
   `compiled_matches_drafts`; remove `concatenate_drafts`/`present_draft_bodies`
   from the import only if no other code in the module still uses them (verify
   with `leta refs` — they are not used elsewhere in `disk_evidence.py`, so the
   import narrows to the helper).
2. Update the docstring to say the verdict now comes from the shared
   `compile_model.compiled_matches_drafts` helper (the single production site),
   keeping the design §4.3/§9 and ExecPlan D-READ citations.

Docs to read first: design §5.4 (`docs/novel-ralph-harness-design.md:541-590`);
`disk_evidence.py`'s module docstring on the deliberate-twin policy
(`:26-45`).

Skills to load: `python-router` → `python-errors-and-logging` (the
`Violation | None` projection and the fault boundary) and `python-data-shapes`
(matching on the enum). Use `leta refs _check_compiled_matches_drafts` and
`leta refs present_draft_bodies` to confirm no other caller breaks.

Tests this item updates/asserts:

- The existing disk-evidence unit suite `tests/test_disk_evidence.py`
  (the `compiled-not-concatenation-of-drafts -> COMPILED_MATCHES_DRAFTS` case at
  `:101`, and the twin-equality / join-helper tests at `:159-176`) must stay
  green **unchanged** — they are the behaviour-preservation proof. Do not edit
  their expectations.
- The corpus disk-divergence suite `tests/test_working_corpus_disk_divergence.py`
  and the agreement suite `tests/test_novel_state_check_disk.py` (which pins the
  detector against the *independent* corpus oracle on every corpus tree) must
  stay green unchanged. Their continued agreement is the cross-check that the
  helper-routed detector still matches the un-routed oracle (D-TWIN).
- Add one focused unit test to `tests/test_disk_evidence.py` asserting the
  *projection* directly: a present-but-stale `compiled.md` yields a
  `COMPILED_MATCHES_DRAFTS` violation, an absent one yields none, and a matching
  one yields none — naming that the detector now delegates the comparison. This
  is the unit pin for the refactor's seam (it would catch a future polarity
  regression in the projection).

Validation: `make all`. Expect the disk-evidence and corpus suites green with no
expectation edits.

Commit message: `Route §5.4 detector through shared compile helper`.

### Work Item 3 — Route the `compile_consistent` clause through the helper

Make the done-clause consume the shared helper while keeping its existence-only
verdict (D-SCOPE). After this item, both production callers consume the one
helper and no third production re-implementation survives.

In `novel_ralph_skill/state/done_predicate.py`:

1. Change `compile_consistent_exists(working_dir)` (`:211-220`) to consume the
   helper. Because the helper needs `state` (to read the drafts) while the
   current function takes only `working_dir`, give the clause the
   `(state, working_dir)` signature the other disk-aware clauses already use and
   project: `compiled_matches_drafts(state, working_dir) is not
   CompiledComparison.ABSENT`. That is exactly today's existence-only semantics
   — present (`MATCHES` or `DIVERGES`) → `True`, absent → `False` — now expressed
   through the shared helper. Consider renaming to `compile_consistent` (dropping
   the `_exists` suffix) since the function now reads the comparison; if renamed,
   update the `evaluate_done` call site (`:292`) and the unit-test import
   (`tests/test_done_predicate.py:32`). Decide and record in the Decision Log;
   the default is to **keep the name `compile_consistent_exists`** to keep the
   diff minimal and the residual-window docstring honest, since the verdict is
   still existence-only.
2. Update `evaluate_done` (`:287-294`) to pass `state` into the clause.
3. Update the docstring to say the existence verdict now comes from the shared
   `compile_model.compiled_matches_drafts` helper (projecting `ABSENT -> False`,
   present `-> True`), and that 3.1.2 will switch the projection to treat
   `DIVERGES` as `False` plus the exit-`4` carve-out. Keep the D-COMPILE-EXISTENCE
   / R-STALE citations.
4. Update imports in `done_predicate.py` to add `CompiledComparison` and
   `compiled_matches_drafts` from `compile_model`.

Docs to read first: design §4.2 (`docs/novel-ralph-harness-design.md:308-360`),
especially the status note that the hash half lands at 3.1.2 (`:310-314`); the
developers' guide §"`compile_consistent` is the existence half only"
(`docs/developers-guide.md:572-579`).

Skills to load: `python-router` → `python-data-shapes` (enum projection) and
`python-types-and-apis` (the clause signature change from `(working_dir)` to
`(state, working_dir)` and its effect on the public `evaluate_done` assembly).

Tests this item updates:

- `tests/test_done_predicate.py::test_compile_consistent_exists_present_and_absent`
  (`:135-149`) — its existing assertions are the behaviour pin: present (even
  stale) → `True`, absent → `False`. The `compile_consistent_exists` import is at
  `tests/test_done_predicate.py:32` (inside the `done_predicate` import block at
  `:29-33`); if the name is **kept** (the default, D-SCOPE), that import line
  stays valid and unchanged, and only the three *calls* at `:144`, `:147`, and
  `:149` gain a `state` argument. If the name is renamed, update both the import
  at `:32` and those three calls. Either way the **expected values must not
  change**. The line that writes `"stale content diverging from drafts"` and
  still asserts `True` (`:146-147`) is the explicit proof that the clause stays
  existence-only (D-SCOPE) — keep it and keep it asserting `True`.
- The `evaluate_done` integration test that unlinks `compiled.md` and expects
  `failed_clause_names == ("compile_consistent",)` (`:196-199`) must stay green
  unchanged.
- The corpus done-predicate suite `tests/test_working_corpus_done_predicate.py`
  must stay green unchanged.
- Snapshot suite `tests/test_novel_done_snapshots.py` and the command/e2e suites
  (`tests/test_novel_done_command.py`, `tests/test_novel_done_e2e.py`) must
  produce byte-identical snapshots/envelopes — no `--snapshot-update` is
  permitted; an unchanged snapshot is the e2e behaviour-preservation proof. If a
  snapshot churns, a verdict changed: stop and escalate (Tolerance "Verdict
  drift").

Validation: `make all`. Expect the done-predicate, corpus, snapshot, command,
and e2e suites green with no expectation edits and no snapshot updates.

Commit message: `Route compile_consistent clause through shared helper`.

### Work Item 4 — Record the shared seam in the developers' guide

Document the new single source of truth so the 3.1.2 implementer reuses it and
a reader understands the two polarity projections.

In `docs/developers-guide.md`:

1. In the §"Done predicate" area, near the existing
   §"`compile_consistent` is the existence half only" paragraph
   (`:572-579`), add a short paragraph: the "compiled.md equals the ordered draft
   concatenation" comparison now lives in one place,
   `compile_model.compiled_matches_drafts(state, working_dir) ->
   CompiledComparison` (returning `ABSENT`/`MATCHES`/`DIVERGES`), consumed by
   both the §5.4 detector `_check_compiled_matches_drafts` (projecting
   `DIVERGES -> Violation`, `ABSENT`/`MATCHES -> None`) and the
   `compile_consistent` clause (projecting `ABSENT -> False`, present `-> True`).
   Name 3.1.3 and audit-3.1.1 Finding 2, and state that 3.1.2 will switch the
   clause projection to treat `DIVERGES` as `False`.
2. Update the compile-model description around `:316-325` (which already says the
   compile write path and the detector share the join rule) to add that the
   *comparison* is now shared too, not just the join.
3. Wrap prose at 80 columns, code spans within 120, en-GB Oxford spelling.

Docs to read first: the existing developers' guide done-predicate section
(`docs/developers-guide.md:540-600`) and compile-model section (`:316-325`);
`docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` (spelling/style for the prose edit).

Tests: documentation-only, so no unit/behavioural test. Validation is the
markdown gates.

Validation: `make all` (still green), then `make markdownlint` and `make nixie`
(no Mermaid added, but run nixie per the standing rule for markdown changes).
Expect markdownlint and nixie to pass with no findings.

Commit message: `Document shared compiled-matches-drafts seam`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-3`.

1. Confirm the branch:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-3 \
     branch --show-current
   ```

   Expect `roadmap-3-1-3`.

2. For each work item: write the test(s) red, run the targeted suite to see them
   fail, implement, then run `make all`. The `make test` target is
   `pytest -v -n $(PYTEST_XDIST_WORKERS)` (`Makefile:115-116`, with
   `PYTEST_XDIST_WORKERS ?= auto` at `Makefile:14`) and exposes **no** Makefile
   parameter for selecting a file: there is no `$(PYTEST_ADDOPTS)` interpolation
   in the recipe. Run targeted red/green iterations directly with `uv run
   pytest`, which selects the file without fanning it across xdist workers:

   ```bash
   uv run pytest tests/test_compile_unit.py
   ```

   (Setting the `PYTEST_ADDOPTS` *environment variable* would also make pytest
   pick the file up, but `make test` would still run it under `-n auto` across
   all workers, so prefer the direct `uv run pytest <file>` form for targeted
   runs.) Expect the new tests to fail before the helper exists and pass after.
   Reserve `make test` and `make all` for the full gate.

3. After each work item, run the full gate and commit:

   ```bash
   make all
   ```

   `make all` is `all: build check-fmt lint typecheck test` (`Makefile:28`); it
   covers **build / check-fmt / lint (ruff + interrogate + pylint) / typecheck
   (ty) / test only**. It does **not** run `pip-audit` — that lives solely in the
   separate `audit` target (`Makefile:104-105`). Expect: Ruff format check clean,
   `ruff check` clean, interrogate at 100% docstring coverage, Pylint clean,
   `ty check` clean, and `pytest` all passed. Then commit with the per-item
   message above (file-based commit message per the commit-message skill; never
   `-m`).

   Note: `pip-audit` is **not** load-bearing for this task — the diff adds no
   dependency — so a separate `make audit` invocation is optional here. Run it if
   you wish, but do not treat it as part of the `make all` gate.

4. For Work Item 4 additionally:

   ```bash
   make markdownlint
   make nixie
   ```

   Expect both to report no findings.

## Validation and acceptance

Acceptance is behavioural and verdict-preserving:

- **One production owner.** `leta refs compiled_matches_drafts` shows exactly two
  production consumers — `disk_evidence._check_compiled_matches_drafts` and the
  `compile_consistent` clause — and `leta grep` finds no other production code
  recomputing "compiled.md == concatenate_drafts(present_draft_bodies(...))".
  The test-side corpus oracle (`tests/working_corpus/_oracle_disk.py`) is the only
  other site computing the comparison, and by policy it does not import the
  helper (D-TWIN).
- **No verdict changed.** `make all` passes with no edits to any existing
  expected value and no snapshot updates across
  `tests/test_disk_evidence.py`, `tests/test_working_corpus_disk_divergence.py`,
  `tests/test_novel_state_check_disk.py`, `tests/test_done_predicate.py`,
  `tests/test_working_corpus_done_predicate.py`,
  `tests/test_novel_done_snapshots.py`, `tests/test_novel_done_command.py`,
  `tests/test_novel_done_e2e.py`, and the compile suites.
- **Helper pinned.** The new unit tests in `tests/test_compile_unit.py` cover
  `MATCHES`/`DIVERGES`/`ABSENT`, the empty-manifest vacuous case, and fault
  propagation; they fail before the helper exists and pass after.
- **Polarity pinned.** The detector still fires `compiled-matches-drafts` only on
  a present-and-stale tree; the clause is still `True` on a present-but-stale
  tree (the documented residual window) and `False` only on an absent compile.

Quality criteria (what "done" means):

- Tests: `make test` — all passed; new compile-unit tests added; no expectation
  or snapshot churn elsewhere.
- Lint/format/types: `make lint`, `make check-fmt`, `make typecheck` — clean
  (all rolled into `make all`).
- Docstrings: interrogate at 100% (the new helper, enum, and any new test
  helpers must carry docstrings) — part of `make lint` and therefore `make all`.
- Audit: **not part of `make all`.** `make all` is
  `build check-fmt lint typecheck test` (`Makefile:28`); `pip-audit` runs only
  via the separate `make audit` target (`Makefile:104-105`). This diff adds no
  dependency, so `make audit` is not load-bearing and is optional here; it must
  not be claimed as a `make all` gate.
- Markdown (item 4): `make markdownlint` and `make nixie` — clean.

Quality method: `make all` is the single CI-equivalent gate for this task
(build / check-fmt / lint / typecheck / test); run it before each commit. Run
`make markdownlint` and `make nixie` after the docs item. `make audit` is
separate and optional here.

## Idempotence and recovery

Every work item is a pure refactor or a docs edit; re-running `make all` is
safe and side-effect-free (the suite writes only to tmp paths). If a work item's
`make all` fails, fix forward within the 3-attempt tolerance; if it still fails,
`git restore` the touched files to recover the last green commit and escalate.
No step is destructive and nothing in `working/` or `state.toml` is written by
this change.

## Interfaces and dependencies

New public surface on `novel_ralph_skill.state.compile_model` (re-exported from
`novel_ralph_skill.state`):

```python
import enum
from pathlib import Path

from novel_ralph_skill.state.schema import State


class CompiledComparison(enum.Enum):
    ABSENT = "absent"
    MATCHES = "matches"
    DIVERGES = "diverges"


def compiled_matches_drafts(
    state: State, working_dir: Path
) -> CompiledComparison: ...
```

Consumers, after this task:

- `novel_ralph_skill.state.disk_evidence._check_compiled_matches_drafts(state,
  working_dir) -> Violation | None` projects `DIVERGES -> Violation`, otherwise
  `None`. Signature unchanged.
- `novel_ralph_skill.state.done_predicate.compile_consistent_exists(state,
  working_dir) -> bool` (signature gains `state`) projects `ABSENT -> False`,
  otherwise `True`. `evaluate_done` updates its call accordingly.

No new external dependency. Stdlib `enum` only. The corpus oracle
(`tests/working_corpus/_oracle_disk.py`) is deliberately not a consumer.
