# Settle a deliberate mutator success-result vocabulary

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Today the two load-edit-rewrite mutators of `novel-state` —
`set-cursor` and `advance-phase` — return `result={"violations": []}` on a
*successful write*. That is the read shape the `check` *query* emits
(`_check` returns `{"violations": [...]}`). A command (a write that mutated
`state.toml`) is borrowing a query's vocabulary, it disagrees with `init`'s own
write result (`{"working_dir", "slug"}`), and an empty `violations` list on a
write invites the misreading "this command checked invariants and found none".
An agent parsing the envelope cannot tell a checker envelope from a mutator one
by `result` alone.

After this change, the two write mutators return a **write-shaped** `result`
that names *what they changed*:

- `set-cursor` returns the cursor it set —
  `{"current_chapter", "current_scene", "current_beat"}`.
- `advance-phase` returns the transition — `{"from", "to"}`.

The `violations` key is reserved for the `check` query alone. The mutator
result contract is recorded once in the design and developers' guide so the
later mutators `recount` and `reconcile` inherit it rather than copying
`check`'s read shape by accident.

You can observe success three ways. First, run `novel-state set-cursor` and
`novel-state advance-phase` against a coherent `working/` and read the JSON: the
`result` object names the cursor or the transition, and the string `violations`
appears nowhere in either mutator's success envelope. Second, the syrupy
snapshot for each mutator's success envelope pins the new shape and no longer
contains `"violations"`. Third, `make all` passes — the new and amended tests
are green, lint, type-check, and format gates hold — and `make markdownlint`
plus `make nixie` pass for the documentation edits.

This is roadmap task **1.3.5** ("Settle a deliberate mutator success-result
vocabulary, distinct from `check`'s `violations` shape"). It implements the
fix proposed in `docs/issues/audit-2.2.2.md` Finding 2 and serves the step-1.3
hypothesis — one envelope contract serving all five commands without
per-command `result` drift — by fixing the write-result shape *before*
`recount` and `reconcile` copy the checker's vocabulary too.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Reserve `violations` for `check`.** After this change the key `violations`
  must appear in the `result` of exactly one `novel-state` subcommand, the
  `check` query. No mutator success or refusal envelope may carry it. (Design
  §3.3 checker/mutator segregation; audit-2.2.2 Finding 2.)
- **Do not regress the exit-code or refusal contract.** This task changes only
  the *success* `result` payload of `set-cursor` and `advance-phase`. The
  exit-code mapping (0/1/2/3/4), the exit-`3` refusal-writes-nothing guarantee,
  and the "refusal names the breached invariant in `messages`, not `result`"
  rule are untouched (design §3.2, §3.4; developers-guide.md "State mutators").
  A refusal envelope's `result` stays `{}` (the exit-`3` `run` arm emits only
  `messages`).
- **`result` is machine-actionable; `messages` is human prose.** The new
  write-shaped `result` carries only structured data; the existing human
  `messages` strings stay as they are (design §3.1: "`result` holds the
  command-specific structured payload … `messages` holds human-oriented notes …
  never parsed").
- **`CommandOutcome.result` is frozen at construction.** `CommandOutcome`
  freezes `result` into a read-only mapping in `__post_init__`
  (`contract/runner.py`). The new payloads are plain `dict` literals passed to
  `CommandOutcome(...)`, exactly as the current code does; do not bypass the
  freeze.
- **No new external dependency, no new module.** The change lives in existing
  files. cuprum, Cyclopts argument handling, the `tomlkit` round-trip, and the
  atomic writer are all unchanged.
- **Source of truth is `docs/`.** The mutator result contract must be recorded
  in the design document and/or developers' guide so it is a documented
  contract, not a code accident (task 1.3.5 success criterion; AGENTS.md
  "Documentation maintenance").
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages (AGENTS.md "consistent spelling and grammar").
- **File-size cap.** No code file may exceed 400 lines (AGENTS.md). The edits
  are small; confirm `commands/_state_mutators.py` stays under the cap after the
  change (it is 292 lines today).

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached. They bound autonomous action;
they are not quality criteria.

- **Scope:** if implementation touches more than 6 files or more than ~150 net
  lines of non-snapshot code, stop and escalate. (Expected: two source files,
  three test files, two docs files — plus regenerated snapshot `.ambr` data.)
- **Interface:** the public callables `set_cursor` and `advance_phase` keep
  their existing signatures and return type (`CommandOutcome`). If any signature
  must change, stop and escalate.
- **Result-key choice:** the audit prescribes the exact keys
  (`{"current_chapter", "current_scene", "current_beat"}` for `set-cursor`;
  `{"from", "to"}` for `advance-phase`). If a reviewer or the design requires a
  *different* uniform field across all mutators, stop and escalate — do not
  invent a third vocabulary.
- **Dependencies:** if any work item appears to need a new library, stop and
  escalate.
- **Iterations:** if a work item's tests still fail after 3 fix attempts, stop
  and escalate.
- **Ambiguity:** `init`'s existing result (`{"working_dir", "slug"}`) is *not*
  changed by this task (the audit names only the two `violations`-echoing
  mutators). If review asks to also reshape `init` into the same vocabulary,
  treat that as a scope change and escalate before doing it.

## Risks

- Risk: changing the success `result` shape silently breaks a consumer that
  reads `result.violations` from a mutator envelope. Severity: low. Likelihood:
  low. Mitigation: a repository-wide search (`leta grep`/grep) for `violations`
  over `tests/` and `novel_ralph_skill/` enumerates every reader before the
  edit. Today no mutator *test* asserts `result["violations"]` on a success path
  (the success tests assert only the exit code and the on-disk effect), so the
  blast radius is the two mutator bodies plus new snapshots. Verify this with the
  reconnaissance search before Work Item 1 and record the result in the Decision
  Log.
- Risk: the new `set-cursor` success snapshot is nondeterministic because the
  cursor scalars echo the input, but `advance-phase`'s `{"from","to"}` depends on
  the fixture's starting phase. Severity: low. Likelihood: low. Mitigation: drive
  each success snapshot from a fixed corpus fixture (`phase_state_tree("premise")`
  gives a deterministic premise-to-treatment transition;
  `phase_state_tree("drafting")` gives a deterministic cursor). Pair each
  snapshot with a semantic assertion on the parsed `result` (AGENTS.md "pair them
  with semantic assertions"), so the snapshot is not the only guard.
- Risk: a future mutator (`recount`, `reconcile`) re-introduces the `violations`
  echo because the contract lived only in code. Severity: medium. Likelihood:
  medium. Mitigation: record the mutator result contract once in the design and
  developers' guide (Work Item 3) and add a contract guard test that asserts no
  `novel-state` mutator success envelope contains `violations` (Work Item 2), so
  a regression is caught by a test, not just by review.
- Risk: editing the design table/prose introduces a Markdown-lint or Mermaid
  regression. Severity: low. Likelihood: low. Mitigation: run `make markdownlint`
  and `make nixie` for every work item that touches a `.md` file, per AGENTS.md.

## Progress

- [x] Work Item 1 — Reshape `set-cursor`'s success `result` to the cursor
  (carries the reconnaissance notes and the set-cursor success assertion;
  green commit). Done 2026-06-23: body now returns `{"current_chapter",
  "current_scene", "current_beat"}`; contract test, extended Hypothesis
  property, and a new success snapshot pin the shape and the absence of
  `violations`. `make all` green; coderabbit 0 findings. The Hypothesis
  property captures the whole `CommandOutcome` in one local (not two) to stay
  under PLR0914's 10-local cap.
- [x] Work Item 2 — Reshape `advance-phase`'s success `result` to the
  transition, add the advance-phase success assertions, and add the
  no-`violations`-on-mutator contract guard (green commit). Done 2026-06-23:
  body returns `{"from", "to"}` (`Phase.value` strings); both advance-phase
  contract tests and a new success snapshot pin the shape and the absence of
  `violations`. The cross-subcommand guard lives in a new module
  `tests/test_novel_state_violations_ownership.py` (see Surprises) as one
  parametrized test over `init`/`set-cursor`/`advance-phase`/`check`. `make
  all` green; coderabbit raised one minor finding (assert diagnostics), now
  applied.
- [x] Work Item 3 — Record the mutator result-vocabulary contract in the design
  and developers' guide; refresh the users' guide note. Done 2026-06-23: §3.1 of
  the design now states the mutator success-result contract and reserves
  `violations` for `check`, cross-referencing §3.3; the developers' guide "State
  mutators" section gains a write-shaped-`result` bullet naming both reshaped
  payloads and the `recount`/`reconcile` obligation; the users' guide notes that
  `violations` is the checker's read shape. `make markdownlint`, `make nixie`,
  and `make all` all green; coderabbit 0 findings.

## Surprises & discoveries

- Observation: the cross-subcommand `violations`-ownership guard could not live
  inside `tests/test_novel_state_mutators.py` as the plan's prose implied.
  Evidence: adding the four-arm guard there pushed the module to 432 lines,
  breaching the 400-line file-size cap (pylint `C0302`). Impact: the guard moved
  into a dedicated module `tests/test_novel_state_violations_ownership.py`
  (145 lines) implemented as one parametrized test, per the plan's stated
  preference ("one parametrized test whose parameter id resolves to a small
  helper that builds the tree and chdir's"). To stay within pylint's
  argument-count budget (`R0913`/`R0917`, max 4), each arm's setup callable
  takes only `request` and pulls `monkeypatch`/`tmp_path`/the tree factory off
  it via `getfixturevalue`. The Hypothesis property in Work Item 1 was likewise
  kept to a single captured-outcome local to stay under PLR0914 (10 locals).
- Observation: the new `tests/test_novel_state_violations_ownership.py` imports
  `collections.abc` at runtime (not under `TYPE_CHECKING`). Evidence: `_SetUp`
  is a module-level `cabc.Callable[...]` alias evaluated at import time, so the
  import must be unconditional; `typing.Callable` is banned by ruff in favour of
  `collections.abc.Callable`. Impact: none beyond the import placement.

## Decision log

- Decision: treat this task as pure result-vocabulary plus documentation —
  cuprum is not load-bearing. Rationale: design §4 states "cuprum is required
  only where a command shells out (none do in v1)". A repository search confirms
  `cuprum` is a declared dependency in `pyproject.toml` but is imported by **no**
  command body; the mutators do filesystem and TOML work only. So no cuprum API
  (catalogue construction, allowlisting, absolute-path executables, run options)
  is exercised by this change, and none needs pinning. The only runtime libraries
  the mutators touch — `tomlkit` (round-trip) and `pathlib` (atomic write) — are
  unchanged by this task. Date/Author: 2026-06-23, planning agent.
- Decision: keep `init`'s result (`{"working_dir","slug"}`) as-is. Rationale:
  audit-2.2.2 Finding 2 names only the two `violations`-echoing mutators
  (`set-cursor`, `advance-phase`); `init` already returns a meaningful write
  result. The task is to stop the *echo*, not to impose a single uniform shape.
  Imposing a uniform field is the audit's explicit *alternative* ("If a uniform
  field is wanted … define it deliberately"), which the task statement does not
  request; doing it here would be scope creep (see Tolerances, Ambiguity).
  Date/Author: 2026-06-23, planning agent.
- Decision: use the audit's prescribed keys verbatim. Rationale: audit-2.2.2
  Finding 2 and roadmap 1.3.5 both name
  `{"current_chapter","current_scene","current_beat"}` for `set-cursor` and
  `{"from","to"}` for `advance-phase`. The `set-cursor` keys match the on-disk
  schema (`DraftingState.current_chapter/current_scene/current_beat`,
  `schema.py:173-175`), so the result reads back to disk fields without
  translation. The `advance-phase` keys `from`/`to` are *transition* labels, not
  on-disk schema field names — `state.toml` has no `[from]`/`[to]`; the on-disk
  representation is `phase.current` plus `phase.completed` (`schema.py:69-70`).
  The documentation (Work Item 3) states this distinction explicitly so a reader
  does not look for a `from` key in `state.toml` (review-r1 advisory A4).
  Date/Author: 2026-06-23, planning agent.
- Decision: every commit in this plan is green; there is no committed red
  baseline. Rationale: AGENTS.md line 100 ("Only changes that meet all quality
  gates should be committed") and line 108 ("Do not commit changes that fail any
  quality gate") forbid committing a failing test suite, and `make all` runs
  `make test`. AGENTS.md line 67 frames red→green as a failing-then-passing test
  *within one complete change*, not as a committed failing state. The plan
  therefore folds each new success assertion into the same commit as the body
  edit that makes it pass (set-cursor assertion → Work Item 1; advance-phase
  assertions → Work Item 2). The red→green observation survives as an
  in-working-tree validation step (run `make test`, watch the assertion fail
  before the body edit, pass after), never as a commit. The reconnaissance
  enumeration rides with the Work Item 1 commit via this Decision Log.
  Date/Author: 2026-06-23, planning agent (resolves review-r1 blocking point
  B1).

- Decision: reconnaissance confirms the expected `violations` blast radius.
  Rationale: a repository-wide search (`grep -rn 'violations'
  novel_ralph_skill tests`) enumerates every occurrence. The `check` query owns
  the key — `novel_state.py:156` writes `result={"violations": [...]}`, and
  `test_novel_state_check.py:86,178` read it (keep). The two mutator echoes are
  exactly `_state_mutators.py:208` (`set_cursor`) and `:288` (`advance_phase`)
  (remove). The remaining matches are unrelated: `validate.py:109,288` and
  `test_working_corpus.py:453-468` name the §5.2 validator's invariant tuple,
  not the envelope `result`. No mutator *test* asserts `result["violations"]`
  on a success path, so the blast radius is the two mutator bodies plus the new
  snapshots and assertions, as the plan predicted. Date/Author: 2026-06-23,
  implementation agent.

## Outcomes & retrospective

Delivered 2026-06-23 across three green commits, each gated by `make all`
(plus `make markdownlint`/`make nixie` for the docs commit):

1. Reshape `set-cursor` success result to the written cursor.
2. Reshape `advance-phase` result and guard `violations` ownership.
3. Record the mutator result contract in the design and guides.

Outcome against the success criteria:

- The two write mutators return a write-shaped `result` — `set-cursor` →
  `{"current_chapter", "current_scene", "current_beat"}`; `advance-phase` →
  `{"from", "to"}` (the `Phase.value` strings) — and `violations` appears in the
  `result` of exactly one subcommand, the `check` query, across both code and
  the recorded snapshots. A parametrized cross-subcommand guard enforces that
  ownership as a test.
- The mutator result-vocabulary contract is documented in the design (§3.1,
  cross-referencing §3.3), the developers' guide, and the users' guide, so
  `recount`/`reconcile` inherit it rather than copying the checker's shape.

Deviations from the plan, with rationale:

- The contract guard moved out of `tests/test_novel_state_mutators.py` (which it
  would have pushed to 432 lines, over the 400-line cap) into a dedicated module
  `tests/test_novel_state_violations_ownership.py`, implemented as the single
  parametrized test the plan preferred. See Surprises & Discoveries.
- To satisfy pylint's argument-count limit (max 4), each guard arm's setup
  callable takes only `request` and pulls `monkeypatch`/`tmp_path`/the tree
  factory off it; and the Work Item 1 Hypothesis property captures the whole
  `CommandOutcome` in one local to stay under PLR0914 (10 locals). Neither
  deviation changes the asserted contract.

Coderabbit: three runs (one per work item), one minor finding total (assert
diagnostics on the guard test, Work Item 2), applied. No tolerances breached: two
source files, four test files, three docs files plus the regenerated snapshot —
within the 6-file / 150-net-line scope bound. No signatures changed; the audit's
prescribed result keys were used verbatim; no new dependency.

## Context and orientation

You are working in the git worktree at the repository root. `novel_ralph_skill`
is a Python package of five console-script commands that read and mutate a
novel-drafting harness state stored under `working/`. Every command emits one
JSON envelope on stdout: `{command, schema_version, ok, working_dir, result,
messages}` (design §3.1, `docs/novel-ralph-harness-design.md`). The harness (an
automated agent) reads `result`; it never parses `messages` prose.

`novel-state` is one command with several subcommands split across two files:

- `novel_ralph_skill/commands/novel_state.py` holds the read-only `check`
  *query* (`_check`) and the `init` builder-*mutator* (`_init`), plus
  `build_app`.
- `novel_ralph_skill/commands/_state_mutators.py` holds the two load-edit-
  rewrite *mutators*, `set_cursor` (lines 161-210) and `advance_phase` (lines
  244-292), and their shared document-load fault helpers. This file is a sibling
  so `novel_state.py` stays under the 400-line cap.

A command body returns a `CommandOutcome(code, result, messages)`
(`novel_ralph_skill/contract/runner.py`). `run` renders that into the JSON
envelope and exits. `CommandOutcome` freezes `result` and `messages` at
construction. On the exit-`3` channel a body raises `StateInputError`, and the
`run` arm emits only `messages` (no `result`), so a *refusal* envelope's
`result` is `{}`.

Key terms:

- **Checker / query (read-only):** `novel-state check`. Validates the §5.2
  invariants and reports breaches in `result.violations`; writes nothing
  (design §3.3). Its success `result` is `{"violations": []}`; a finding is
  exit `4` with the breached names in `result.violations`.
- **Mutator (command, writes):** `init`, `set-cursor`, `advance-phase`
  (and later `recount`, `reconcile`). Validate-before-persist, write
  atomically, refuse incoherent transitions with exit `3` and no write.
- **The defect (audit-2.2.2 Finding 2):** `set_cursor` (line 208) and
  `advance_phase` (line 288) return `result={"violations": []}` on success —
  the query's read shape on a command's write.

The current success payloads to change:

```python
# novel_ralph_skill/commands/_state_mutators.py — set_cursor, line ~206
return CommandOutcome(
    code=ExitCode.SUCCESS,
    result={"violations": []},
    messages=[f"cursor set to chapter={chapter}, scene={scene}, beat={beat}"],
)

# novel_ralph_skill/commands/_state_mutators.py — advance_phase, line ~286
return CommandOutcome(
    code=ExitCode.SUCCESS,
    result={"violations": []},
    messages=[
        f"advanced phase from {prior.phase.current.value!r} to {successor.value!r}"
    ],
)
```

The on-disk schema fields the new `result` mirrors live in
`novel_ralph_skill/state/schema.py`: `DraftingState.current_chapter`,
`.current_scene`, `.current_beat` (lines 173-175); `PhaseState.current`,
`.completed` (lines 69-70); `Phase` is a `StrEnum` whose `.value` is the
on-disk string (`state/phase.py`).

Tests that pin the mutator envelopes:

- `tests/test_novel_state_mutators.py` — contract tests via the shared `run`
  wrapper. The success tests (`test_set_cursor_success` line 143,
  `test_advance_phase_success_pre_drafting` line 202,
  `test_advance_phase_success_into_drafting` line 221) assert the exit code and
  the on-disk effect but **do not** currently assert the success `result`.
- `tests/test_novel_state_mutator_snapshots.py` — syrupy envelope snapshots.
  Today it snapshots `init` *success* and the two mutator *refusal* envelopes,
  but has **no** `set-cursor`/`advance-phase` *success* snapshot. The refusal
  snapshots already show `"result": {}` (no `violations`), so they are
  unaffected by this change.
- `tests/test_state_mutators_unit.py` — direct-call unit and Hypothesis tests;
  `test_set_cursor_accepts_exactly_coherent_cursors` (line 167) asserts only
  `.code` today.
- `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr` — the recorded
  snapshot data.

The documents you will edit:

- `docs/novel-ralph-harness-design.md` — §3.1 (output modes / `result`
  semantics), §3.3 (command/query segregation), §4.1 (`novel-state`
  subcommands), §5.4 (reconciliation, where `recount`/`reconcile` results live).
- `docs/developers-guide.md` — the "State mutators (`init`, `set-cursor`,
  `advance-phase`)" section (line 417) and the `check`/`result.violations`
  description (line 375).
- `docs/users-guide.md` — the `novel-state` section (line 82) which still
  documents `result.violations` only for `check`.

## Skills and references to load before starting

- **Routing:** load the `python-router` skill first; it routes to the smaller
  Python skills below.
- **Data shape of the result payload:** `python-data-shapes` — the `result`
  payload is a small structured mapping; confirm a plain `dict[str, object]`
  literal is the right container (it is what `CommandOutcome.result` expects and
  freezes).
- **CQS / function design:** `python-errors-and-logging` is *not* needed (no new
  error types); the relevant guidance is AGENTS.md "command/query segregation",
  which this task literally enforces at the envelope level.
- **Testing:** `python-testing` for the syrupy snapshot discipline (pair each
  snapshot with a semantic assertion) and `pytest` fixture usage.
- **Verification adversary selection:** `python-verification`. For this task the
  existing Hypothesis property
  (`test_set_cursor_accepts_exactly_coherent_cursors`) is the right adversary to
  *extend* — it already generates coherent cursors; asserting the returned
  `result` echoes those exact inputs pins the write-shaped payload over the
  whole coherent input space. Load the `hypothesis` skill for that extension.
  CrossHair and mutmut are **not** warranted here: there is no contract/`assert`
  surface for CrossHair to attack beyond the existing property, and a mutation
  campaign is disproportionate to a result-key rename. Record this in the
  Decision Log if a reviewer asks for mutation testing.
- **Documentation style:** `docs/documentation-style-guide.md` and the
  `en-gb-oxendict` skill for the prose edits.
- **Design source of truth:** `docs/novel-ralph-harness-design.md` §3.1, §3.2,
  §3.3, §5.4; `docs/adr-003-shared-interface-contract.md`;
  `docs/issues/audit-2.2.2.md` Finding 2.

## Plan of work

Every work item is independently committable and leaves a **green** tree:
`make all` passes at each commit (plus `make markdownlint` + `make nixie` where
Markdown changes). There is no committed red baseline — committing a failing
test suite would breach AGENTS.md lines 100 and 108 (see Decision Log). The
red→green discipline (AGENTS.md line 67) is exercised *within* each work item as
an in-working-tree observation: add the new assertion, run `make test` and watch
it fail for the documented reason, make the one-line body edit, run `make test`
again and watch it pass, then commit the whole green change as one unit. The
new assertion and the source edit that satisfies it always land in the same
commit.

Before Work Item 1, perform the reconnaissance below; its notes ride with the
Work Item 1 commit (no separate commit).

### Reconnaissance (in-tree, no commit of its own)

Goal: prove the current shape is the read shape and enumerate every `violations`
reader before changing it.

Documents to read: `docs/issues/audit-2.2.2.md` Finding 2;
`docs/novel-ralph-harness-design.md` §3.1, §3.3. Skills: `python-router` →
`python-testing`; `leta`.

Steps:

1. With `leta grep` (fallback ripgrep), enumerate every occurrence of the string
   `violations` across `novel_ralph_skill/` and `tests/`. Record in the Decision
   Log which occurrences are the `check` query (keep) and which are the two
   mutator echoes (remove). Confirm no mutator *test* currently asserts
   `result["violations"]` on a success path. (Expected, per review-r1: the only
   readers are `_check` in `novel_state.py` and `test_novel_state_check.py`; the
   two mutator echoes are at `_state_mutators.py:208` and `:288`.)

This is a read-only step. It produces Decision Log entries, not a commit.

### Work Item 1 — Reshape `set-cursor`'s success result to the cursor

Goal: `set-cursor` returns `{"current_chapter", "current_scene",
"current_beat"}` on success; `violations` is gone from its envelope. This is a
single green commit: the new success-shape assertion and the body edit that
satisfies it land together.

Documents to read: `docs/novel-ralph-harness-design.md` §3.1, §4.1;
`docs/issues/audit-2.2.2.md` Finding 2. Skills: `python-router` →
`python-data-shapes`, `python-testing`, `hypothesis`.

Steps (perform in order; the red→green observation in step 1 is *not* committed
separately — only the final green tree is committed):

1. **Red observation first.** In `tests/test_novel_state_mutators.py`,
   strengthen `test_set_cursor_success` (line 143) to parse the success envelope
   and assert the new shape:
   `result == {"current_chapter": 2, "current_scene": 0, "current_beat": 0}` and
   `"violations" not in result`. The helper `_drive_and_capture` already returns
   `(code, envelope)`; read `envelope["result"]` (today the test discards the
   envelope). Run `make test` and watch this assertion **fail** against the
   current `{"violations": []}` — this is the red→green observation, not a
   commit. (You may instead add a focused sibling test, e.g.
   `test_set_cursor_success_result_is_the_cursor`, leaving the on-disk-effect
   assertion in the original test for independent diagnosis; either way the
   assertion lands in this same commit.)
2. In `novel_ralph_skill/commands/_state_mutators.py`, edit `set_cursor`'s
   return (line ~206) so `result` is the cursor it set:

   ```python
   return CommandOutcome(
       code=ExitCode.SUCCESS,
       result={
           "current_chapter": chapter,
           "current_scene": scene,
           "current_beat": beat,
       },
       messages=[f"cursor set to chapter={chapter}, scene={scene}, beat={beat}"],
   )
   ```

3. Update the `set_cursor` docstring's `Returns` note: it now returns
   `ExitCode.SUCCESS` carrying the written cursor in `result`, not an empty
   `violations` echo. Keep the en-GB spelling and the §-references.
4. Extend the Hypothesis property
   `test_set_cursor_accepts_exactly_coherent_cursors` in
   `tests/test_state_mutators_unit.py` (line 167). Today the property body does
   `outcome = set_cursor(...).code` inside `contextlib.suppress(StateInputError)`
   and only keeps the exit code, discarding the `CommandOutcome` (review-r1
   advisory A1). To assert the result shape you must capture the whole outcome
   on the success branch *before* reading `.code`, and assert the result shape
   **only** in the `oracle_coherent` arm (the refusal arm raises
   `StateInputError` inside the `suppress` and never returns an outcome, so it
   has no `.result` to read). Preserve the **existing** statement order: the
   `monkeypatch.chdir(working.parent)` call stays **above** the `with
   contextlib.suppress(...)` block (its true position at
   `tests/test_state_mutators_unit.py:198`). `set_cursor` reads its target with
   `_state_path()` — a cwd-relative `working/state.toml` resolved at call time
   (`_state_mutators.py:57-59`) — so it must run with cwd already at
   `working.parent`; moving the chdir below the block would call `set_cursor`
   from the wrong cwd, raise `StateInputError`, leave `result_payload` `None`,
   and make the coherent arm fail on every example. Only the new
   `result_payload`/`exit_code` capture is introduced; the chdir does not move.
   Concretely:

   ```python
   # The chdir MUST precede the suppress block (this is its existing position
   # at tests/test_state_mutators_unit.py:198). ``set_cursor`` resolves its
   # target via ``_state_path()`` = ``Path('working')/'state.toml'`` — a
   # cwd-RELATIVE path evaluated at call time
   # (_state_mutators.py:57-59). If cwd is not ``working.parent`` when
   # ``set_cursor`` runs, it cannot find ``working/state.toml``, raises
   # ``StateInputError`` (swallowed by the suppress), and ``result_payload``
   # stays ``None`` — making the ``oracle_coherent`` arm fail for every
   # coherent example. Keep the chdir above the block, exactly as it is today.
   monkeypatch.chdir(working.parent)
   result_payload: dict[str, object] | None = None
   exit_code: ExitCode | None = None
   with contextlib.suppress(StateInputError):
       outcome = set_cursor(chapter=chapter, scene=scene, beat=beat)
       exit_code, result_payload = outcome.code, dict(outcome.result)

   if oracle_coherent:
       assert exit_code == ExitCode.SUCCESS
       assert result_payload == {
           "current_chapter": chapter,
           "current_scene": scene,
           "current_beat": beat,
       }
       assert "violations" not in result_payload
   else:
       assert exit_code is None  # the body raised StateInputError (exit 3)
   ```

   (`CommandOutcome.result` is a frozen read-only mapping; wrapping it in
   `dict(...)` gives a plain comparable dict without mutating the frozen one.)
   This pins the write-shaped payload over the whole coherent input space, not
   just the one contract example.
5. Add a `set-cursor` **success** envelope snapshot to
   `tests/test_novel_state_mutator_snapshots.py`, paired with a semantic
   assertion that the parsed `result` is the cursor and contains no
   `violations` key (mirror the existing `test_init_success_envelope_snapshot`
   structure; drive from `phase_state_tree("drafting")` for a deterministic
   tree, with `--chapter 2 --scene 0 --beat 0`). Regenerate the `.ambr` with
   `--snapshot-update`, then read the new snapshot to confirm it shows the cursor
   result and **no** `violations`.

Validation: `make all`. The `set-cursor` success assertion added in step 1 now
passes; `make lint`, `make check-fmt`, `make typecheck` are green; the new
snapshot is recorded and matches. Acceptance: running
`novel-state set-cursor --chapter 2` against a coherent drafting tree emits a
JSON envelope whose `result` is `{"current_chapter": 2, "current_scene": 0,
"current_beat": 0}` and contains no `violations` key.

Tests this item adds/updates: amended (or sibling) contract test for
`test_set_cursor_success`, extended Hypothesis property
(`test_set_cursor_accepts_exactly_coherent_cursors`), new success snapshot
(`test_set_cursor_success_envelope_snapshot`) plus its `.ambr` entry. The
reconnaissance Decision Log entries ride with this commit.

Commit: one **green** commit gated by `make all` (no Markdown change in this
item, so `markdownlint`/`nixie` not required here). The new assertion and the
body edit are in the same commit; the tree passes `make all` before committing.

### Work Item 2 — Reshape `advance-phase`'s success result and add the guard

Goal: `advance-phase` returns `{"from", "to"}` on success; add a contract guard
asserting **no** `novel-state` mutator success envelope carries `violations`
while the `check` query still does. This is a single green commit: the new
assertions and the body edit that satisfies them land together.

Documents to read: `docs/novel-ralph-harness-design.md` §3.1, §3.3, §4.1;
`docs/issues/audit-2.2.2.md` Finding 2. Skills: `python-router` →
`python-data-shapes`, `python-testing`.

Steps (the red→green observation in step 1 is *not* committed separately — only
the final green tree is committed):

1. **Red observation first.** In `tests/test_novel_state_mutators.py`,
   strengthen the two advance-phase success tests to assert the new transition
   shape (read `envelope["result"]` from `_drive_and_capture`, which today they
   discard):
   - `test_advance_phase_success_pre_drafting` (line 202, driven by
     `phase_state_tree("premise")`): assert
     `result == {"from": "premise", "to": "treatment"}` and
     `"violations" not in result`.
   - `test_advance_phase_success_into_drafting` (line 221, driven by
     `populated_chapter_planning_tree()`): assert
     `result == {"from": "chapter-planning", "to": "drafting"}` and
     `"violations" not in result`. (This fixture, not `phase_state_tree`,
     produces the `chapter-planning` prior; review-r1 verified the resulting
     transition.)

   Run `make test` and watch both assertions **fail** against the current
   `{"violations": []}` — the red→green observation, not a commit. (Sibling
   focused tests are acceptable in the same spirit as Work Item 1.)
2. In `novel_ralph_skill/commands/_state_mutators.py`, edit `advance_phase`'s
   return (line ~286) so `result` names the transition:

   ```python
   return CommandOutcome(
       code=ExitCode.SUCCESS,
       result={
           "from": prior.phase.current.value,
           "to": successor.value,
       },
       messages=[
           f"advanced phase from {prior.phase.current.value!r} to {successor.value!r}"
       ],
   )
   ```

   Use `.value` (the on-disk string) so the JSON is a plain string, matching how
   `phase.current`/`completed` are stored. Run `make test` and watch the step-1
   assertions pass.
3. Update the `advance_phase` docstring `Returns` note to describe the
   transition result, noting `from`/`to` are transition labels (not on-disk
   keys; see Decision Log / Work Item 3).
4. Add an `advance-phase` **success** envelope snapshot to
   `tests/test_novel_state_mutator_snapshots.py`, paired with a semantic
   assertion on the parsed `result` (`{"from": "premise", "to": "treatment"}`
   from `phase_state_tree("premise")`) and the absence of `violations`.
   Regenerate and inspect the `.ambr` entry.
5. Add the **cross-subcommand `violations`-ownership guard**. Implement it as a
   **parametrized** test (one tuple per subcommand), *not* a single test sharing
   one cwd — `init` and the three populated subcommands have mutually
   incompatible fixture preconditions (review-r1 blocking point B2): `init`
   refuses with exit `3` if `working/state.toml` already exists
   (`test_init_refuses_existing_state`), so it must run from a *bare* `tmp_path`
   chdir, whereas `set-cursor`, `advance-phase`, and `check` each need a
   *populated, coherent* tree, and each a different one. A single shared chdir
   would drive `init` into an exit-`3` refusal, silently inverting the guard.

   Each parameter case carries: the `argv`, the fixture that builds (and
   chdir's into) the tree this case needs, the expected exit code, and whether
   `violations` must be **present** or **absent** in `result`. Name the fixtures
   exactly, one case per subcommand:

   - `init` — argv `["init", "--title", "T", "--slug", "s"]`; cwd is a *bare*
     `tmp_path` via `monkeypatch.chdir(tmp_path)` with **no** pre-existing
     `working/`; expect `ExitCode.SUCCESS`; `violations` **absent**.
   - `set-cursor` — argv
     `["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"]`; build the
     tree with `phase_state_tree("drafting")` and chdir to its parent; expect
     `ExitCode.SUCCESS`; `violations` **absent**.
   - `advance-phase` — argv `["advance-phase"]`; build the tree with
     `phase_state_tree("premise")` and chdir to its parent; expect
     `ExitCode.SUCCESS`; `violations` **absent**.
   - `check` — argv `["check"]`; build any coherent tree with `baseline_tree()`
     and chdir to its parent; expect `ExitCode.SUCCESS`; `violations`
     **present** (the empty `[]` still carries the key).

   Because the four arms need different fixtures and chdir targets, a clean
   shape is one parametrized test whose parameter id resolves to a small helper
   that *builds the tree and chdir's* for that arm (each helper takes
   `tmp_path`/`monkeypatch` and the relevant tree factory and returns nothing),
   or, equivalently, four focused sibling tests sharing one assertion helper.
   Either way:
   - The three mutator arms assert their documented success exit code (`init`,
     `set-cursor`, `advance-phase` → `ExitCode.SUCCESS`) **and**
     `"violations" not in result`.
   - The `check` arm asserts `ExitCode.SUCCESS` **and** `"violations" in result`
     (an empty `result["violations"] == []` still carries the key — presence,
     not emptiness, is the assertion). Mirror
     `test_check_coherent_tree_exits_zero` for the fixture (`baseline_tree`) and
     envelope-reading pattern.

   This pins the Constraint "`violations` belongs to exactly one subcommand" as
   a test, so a future `recount`/`reconcile` regression is caught automatically
   (Risk: "future mutator re-introduces the echo"). When `recount`/`reconcile`
   are later added as mutators, extend this parametrization with their argv +
   fixture rows asserting `violations` absent.

Validation: `make all`. The advance-phase success assertions from step 1 pass;
the parametrized guard passes (all four arms); the new snapshot is recorded.
Acceptance: running `novel-state advance-phase` against a coherent pre-drafting
tree emits a JSON envelope whose `result` is `{"from": "premise", "to":
"treatment"}` and contains no `violations` key; `novel-state check` still carries
`result.violations`.

Tests this item adds/updates: amended (or sibling) contract tests for
`test_advance_phase_success_pre_drafting` and
`test_advance_phase_success_into_drafting`, new success snapshot
(`test_advance_phase_success_envelope_snapshot`) plus its `.ambr` entry, and the
parametrized cross-subcommand `violations`-ownership guard test (four arms).

Commit: one **green** commit gated by `make all`. The new assertions and the
body edit are in the same commit; the tree passes `make all` before committing.

### Work Item 3 — Record the mutator result contract in the docs

Goal: write the mutator success-result vocabulary down once so `recount` and
`reconcile` inherit it; reserve `violations` for `check` in prose; refresh the
users' guide.

Documents to read and edit: `docs/novel-ralph-harness-design.md` §3.1, §3.3,
§4.1, §5.4; `docs/developers-guide.md` "State mutators" (line 417) and the
`check` description (line 375); `docs/users-guide.md` `novel-state` section
(line 82); `docs/documentation-style-guide.md`. Skills: `en-gb-oxendict`;
`python-router` is not needed (prose-only).

Steps:

1. In `docs/novel-ralph-harness-design.md`, add a short, normative paragraph
   (best placed in §3.1 beside the `result` description, or as a new note under
   §4.1's subcommand table) stating the mutator result contract: a mutator's
   success `result` names *what it changed* (`init` → the bootstrapped
   `working_dir`/`slug`; `set-cursor` → the cursor it set; `advance-phase` →
   the `{from, to}` transition; `recount`/`reconcile` → the counts/discrepancies
   they wrote, per §4.1/§5.4), and the `violations` key is reserved for the
   `check` query. State explicitly that `advance-phase`'s `from`/`to` are
   *transition labels* describing the move, not on-disk schema keys — `state.toml`
   has no `[from]`/`[to]`; the persisted representation is `phase.current` plus
   `phase.completed` (review-r1 advisory A4). Cross-reference §3.3 (command/query
   segregation) so the rule reads as the envelope-level expression of CQS.
2. In `docs/developers-guide.md` "State mutators" section, add a bullet
   recording the write-shaped `result` rule and naming the two reshaped payloads
   (`set-cursor` → `{current_chapter, current_scene, current_beat}`;
   `advance-phase` → `{from, to}`), explicitly noting that mutators do **not**
   echo `check`'s `violations` and that `recount`/`reconcile` must follow the
   same write-shaped discipline. Reference audit-2.2.2 Finding 2 and design
   §3.3.
3. In `docs/users-guide.md`, where the `novel-state check` exit-code table
   describes `result.violations`, add a short note that `violations` is the
   *checker's* read shape and the write mutators report what they changed in
   `result` instead (so a reader does not expect `violations` from a write).
   Keep it brief; the full mutator user docs are audit-2.2.2 Finding 1, a
   separate task.
4. Run `make markdownlint` and `make nixie`.

Validation: `make markdownlint` and `make nixie` pass; `make all` still passes
(docs-only changes do not affect tests, but run it to confirm nothing else
drifted). Acceptance: a reader of the design or developers' guide can state,
from the docs alone, what `result` each `novel-state` mutator returns on success
and that `violations` belongs to `check` only.

Tests this item adds/updates: none (documentation-only). Validation is the
Markdown gates plus a re-run of `make all`.

Commit: one commit, gated by `make markdownlint`, `make nixie`, and `make all`.

## Concrete steps

Run everything from the worktree root (the repository root of this checkout).

Reconnaissance (before Work Item 1, no commit of its own):

```bash
leta grep 'violations'        # enumerate readers; fallback: rg -n 'violations' novel_ralph_skill tests
```

Per-item red→green observation, then the green commit. The `make test` failure
below is an *in-working-tree* observation — never a committed state; commit only
after `make all` passes:

```bash
make test          # WI1/WI2: after adding the new assertion, watch it FAIL (red)
                   #          then after the body edit, re-run and watch it PASS (green)
make all           # WI1, WI2: must PASS before committing (build, check-fmt, lint, typecheck, test)
```

Snapshot regeneration (WI1, WI2) — update, then inspect the diff before
committing:

```bash
.venv/bin/pytest tests/test_novel_state_mutator_snapshots.py --snapshot-update
git --no-pager diff tests/__snapshots__/test_novel_state_mutator_snapshots.ambr
```

Expected snapshot diff (illustrative — the success envelopes gain a write-shaped
`result` and never contain `"violations"`):

```plaintext
# name: test_set_cursor_success_envelope_snapshot
  {..., "result": {"current_chapter": 2, "current_scene": 0, "current_beat": 0},
   "messages": ["cursor set to chapter=2, scene=0, beat=0"]}

# name: test_advance_phase_success_envelope_snapshot
  {..., "result": {"from": "premise", "to": "treatment"},
   "messages": ["advanced phase from 'premise' to 'treatment'"]}
```

Documentation gates (WI3):

```bash
make markdownlint
make nixie
make all
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. The amended success assertions in
  `tests/test_novel_state_mutators.py` and the extended Hypothesis property in
  `tests/test_state_mutators_unit.py` pass; the two new success snapshots are
  recorded; the cross-subcommand `violations`-ownership guard passes; every
  pre-existing mutator test still passes. Each new assertion fails before its
  source edit and passes after (red→green).
- Lint/format/types: `make lint`, `make check-fmt`, `make typecheck` pass
  (rolled up by `make all`).
- Markdown: `make markdownlint` and `make nixie` pass for the documentation
  edits.
- Contract: the string `violations` appears in the `result` of exactly one
  `novel-state` subcommand — the `check` query — across both code and the
  recorded snapshots.

Quality method (how we check):

- `make all` for code work items; `make markdownlint` + `make nixie` + `make
  all` for the documentation work item.
- Manual acceptance: run `novel-state set-cursor` and `novel-state
  advance-phase` against a coherent `working/` (or read the recorded success
  snapshots) and confirm the `result` names the change and omits `violations`,
  while `novel-state check` still reports `result.violations`.

## Idempotence and recovery

Every step is a source or documentation edit plus a test run; all are
re-runnable without side effects. The only generated artefact is the syrupy
`.ambr` snapshot file; regenerate it with `pytest --snapshot-update` and inspect
the `git diff` before committing — never commit an unexamined snapshot update.
If `make all` fails after an edit, revert the single edit (`git checkout --
<file>`) and retry; no step mutates state outside the working tree.

## Interfaces and dependencies

No new libraries, modules, or signatures. The change is confined to the bodies
of two existing functions and their tests and docs.

In `novel_ralph_skill/commands/_state_mutators.py`, the two callables keep their
signatures and return type:

```python
def set_cursor(*, chapter: int, scene: int, beat: int) -> CommandOutcome: ...
def advance_phase() -> CommandOutcome: ...
```

After this change their success `CommandOutcome.result` payloads are:

- `set_cursor` → `{"current_chapter": int, "current_scene": int,
  "current_beat": int}`
- `advance_phase` → `{"from": str, "to": str}` (the `Phase.value` strings)

`CommandOutcome` (in `novel_ralph_skill/contract/runner.py`) is unchanged; it
continues to freeze `result`/`messages` at construction. The `check` query's
`result={"violations": [...]}` in `novel_ralph_skill/commands/novel_state.py` is
unchanged and remains the sole owner of the `violations` key.

## Revision note

- Revision 3 (2026-06-23, planning round 3) — resolves the single blocking
  point from `roadmap-1-3-5.review-r2.md`.
  - **B1 (Work Item 1 step 4 chdir placement).** The Revision-2 code sketch
    placed `monkeypatch.chdir(working.parent)` *after* the
    `with contextlib.suppress(StateInputError):` block and mislabelled it as the
    existing placement. Verified against
    `tests/test_state_mutators_unit.py:198-201`: the **existing** placement is
    the chdir *before* the suppress block, and `set_cursor` resolves its target
    with `_state_path()` = `Path('working')/'state.toml'`, a cwd-relative path
    evaluated at call time (`_state_mutators.py:57-59`). With the chdir below the
    block, `set_cursor` would run from the test's default cwd, fail to find
    `working/state.toml`, raise `StateInputError` (swallowed by the suppress),
    and leave `result_payload=None`/`exit_code=None`, so the `oracle_coherent`
    arm asserting `result_payload == {...}` fails for every coherent example.
    The sketch now moves the chdir back **above** the suppress block (its true
    existing position), corrects the comment to explain the cwd-relative
    resolution and the failure mode, and the step-4 prose states that only the
    `result_payload`/`exit_code` capture is introduced — the chdir does not move.
- Revision 2 (2026-06-23, planning round 2) — resolves the two blocking points
  from `roadmap-1-3-5.review-r1.md` and folds in its advisories.
  - **B1 (committed red baseline).** Removed Work Item 0 as a standalone commit.
    The reconnaissance `violations` enumeration is now an in-tree, read-only step
    that rides with the Work Item 1 commit. The set-cursor success assertion is
    folded into Work Item 1 and the two advance-phase assertions into Work Item
    2, so every commit is green and passes `make all`. The red→green discipline
    is now an explicit in-working-tree observation inside each work item (add
    assertion → watch `make test` fail → make the body edit → watch it pass →
    commit the green tree), never a committed failing state. A new Decision Log
    entry records this and cites AGENTS.md lines 67/100/108. The Progress,
    Risks, Plan-of-work intro, and Concrete-steps sections were updated to match.
  - **B2 (under-specified contract guard).** Work Item 2 step 5 now specifies the
    guard as a parametrized test (or four focused sibling tests) with one
    `(argv, fixture/cwd-setup, expected exit, violations present/absent)` tuple
    per subcommand, naming the exact fixture per arm
    (`init` → bare `tmp_path`; `set-cursor` → `phase_state_tree("drafting")`;
    `advance-phase` → `phase_state_tree("premise")`; `check` → `baseline_tree()`),
    and stating that the `check` arm asserts `"violations" in result` (presence,
    even when empty) while the three mutator arms assert `"violations" not in
    result`. It explains why `init` cannot share a cwd with the populated arms
    (exit-`3` refusal on a pre-existing `working/`).
  - **A1.** Work Item 1 step 4 now spells out that the Hypothesis property must
    capture the whole `CommandOutcome` on the success branch before reading
    `.code`, and assert the result shape only in the `oracle_coherent` arm, with
    a code sketch.
  - **A4.** Work Item 3 step 1 and the Decision Log now state that
    `advance-phase`'s `from`/`to` are transition labels, not on-disk schema keys.
- Revision 1 — initial draft.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews and audits of step 1.3's tasks. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge. The forward-looking reminder to
extend the `violations`-ownership guard when `recount`/`reconcile` land is
already captured in `tests/test_novel_state_violations_ownership.py`'s docstring
and owned by roadmap tasks 2.3.1/2.3.2 (which inherit this task's mutator-result
contract), so it is not re-filed here.

- [ ] 1.3.5.1 — Record set-cursor's input-echo result coupling as a deliberate
  choice (from review:1.3.5, low). `set-cursor` echoes its input args as the
  success `result`; they equal the persisted scalars today, so note the coupling
  as a deliberate choice — rather than re-reading the written document to make
  the envelope structurally independent of the input path — in the design or
  developers' guide, so it is recorded as a decision and not a latent assumption.
  Gate with `make markdownlint` and `make nixie`.
- [ ] 1.3.5.2 — Assert advance-phase's `from`/`to` are transition labels, not
  `state.toml` schema keys (from audit:1.3.5, low). The from/to-are-not-schema-keys
  intent is documented across the design, the developers' guide, and the
  docstring but proven only in prose; add an on-disk behavioural test that
  re-reads the written `state.toml` to assert `phase.current` and
  `phase.completed` updated and no `from`/`to` keys were persisted, closing the
  gap between prose and test surface. Gate with `make all`.
