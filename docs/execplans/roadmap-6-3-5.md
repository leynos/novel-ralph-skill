# Make the six draft-read (exit-3) boundaries actionable

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.3.1 made the *state.toml-load* faults speak plainly: run any
`novel` command from a directory with no `working/` tree and the exit-3
envelope now carries `no novel working/ found in <cwd>; run from the novel
root, or run 'novel state init' to create one`, with no raw `Errno` and no
traceback. But the *draft-read* faults on the same
exit-3 channel were left raw. When a chapter's `draft.md` is present but
undecodable (invalid UTF-8) or unreadable (a `PermissionError`), the same
command surfaces operating-system noise instead:

```text
cannot read chapter drafts: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
```

So a dogfooding agent sees *polished* prose for one fault and *raw* OS text for
another, from the same command — the exact within-command inconsistency step
6.3 exists to close.

This change routes the six draft-read boundaries the roadmap enumerates —
`novel_state._disk_evidence_or_state_error`, `_recount._recount_or_state_error`,
`_wordcount` (its `recount_words` tail), `_novel_done` (its `evaluate_done`
tail), `_desloppify.source_chapters`, and `_compile` (its
`present_draft_bodies` and `compiled_matches_drafts` tails) — through one
shared actionable formatter analogous to 6.3.1's `_state_input_error`. After
the change, every one of those boundaries emits prose that names the `working/`
tree it read and offers an inspect/repair remedy, leaking no `Errno`, no
`{exc}` repr, and no traceback.

The seventh boundary the roadmap names — the mutator view-derivation boundary
`_state_mutators._state_view_or_state_error` — is **not** a draft-read fault.
It reports a *parsed-but-structurally-incomplete `state.toml`* (the file loaded
as TOML, but `document_to_state` found a missing table/key or a bad phase
string), which 6.3.1 Decision D8 deliberately kept distinct from the draft-read
and load faults. The roadmap mandates "an inspect/repair remedy", not the
draft-read formatter specifically; the correct inspect/repair home for a
present-but-corrupt *state document* is 6.3.1's existing `_state_input_error`
present-but-corrupt arm (`<path> is unreadable or corrupt; inspect and repair
it, or restore it from a known-good copy`). Because the document parsed,
`state.toml` exists, so that arm (not the
missing-`working/` arm) fires and names the `state.toml` *path* — the right
artefact for a state-document fault — rather than the `working/` tree a
draft-read message names. This plan therefore routes the view-derivation
boundary through `_state_input_error(state_path(), exc)`, reusing 6.3.1's
machinery and respecting D8, instead of through the new draft-read formatter
(Decision D7).

You can observe success by running the behavioural suite this plan adds. It
builds a coherent `working/` tree, corrupts a chapter `draft.md` to invalid
UTF-8 (and, for the view-derivation arm, a parseable-but-structurally-incomplete
`state.toml`), drives at least one command per boundary, and asserts exit 3
plus an actionable message that names the artefact (the `working/` tree for the
draft-read six; the `state.toml` path for the view-derivation boundary) and an
inspect/repair remedy, with no raw `Errno`/`{exc}` text. A repository-wide
sweep for the old `cannot read …: {exc}` and `structurally incomplete: {exc}`
strings backs the proof.

This is the **message-quality** half of the draft-read work. The **catch-idiom
DRY** half — consolidating the triplicated `try/except STATE_INPUT_ERRORS`
*wrapper* into one `read_drafts_or_state_error` helper — is roadmap task 7.3.3,
deferred and coordinated so the formatter this plan lands and the wrapper 7.3.3
lands share one home (the `_state_load` leaf module). This plan adds the
**formatter**; 7.3.3 later routes the **wrapper** through it.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The exit-code contract is fixed: an undecodable/unreadable `draft.md`,
  `compiled.md`, or a structurally-incomplete `state.toml` is the exit-3
  state-or-input channel, never the benign exit 1 (design §3.2, the exit-code
  table; `adr-003-shared-interface-contract.md`). This plan changes only the
  **message text**; it never changes an exit code, never alters the
  `StateInputError`-to-exit-3 mapping in
  `novel_ralph_skill/contract/runner.py`, and never moves a fault from one
  channel to another. In particular an *absent* `draft.md` stays benign (counted
  `0`) exactly as today — only a *present-but-faulted* read is reformatted.
- There must remain exactly **one** draft-read actionable-message formatter,
  living beside 6.3.1's `_state_input_error` in the dependency-free leaf module
  `novel_ralph_skill/commands/_state_load.py`. Each of the enumerated
  boundaries MUST route through it. Re-introducing per-boundary message strings
  is forbidden; it is the drift the task exists to prevent. (The formatter and
  the later 7.3.3 *wrapper* share this one home so they cannot diverge.)
- The formatter's home must not create an import cycle. `_state_load.py` imports
  only from `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner`,
  never from `novel_state` (its module docstring pins this). `_state_mutators`
  already imports one-way from `novel_state` (which re-exports `_state_load`).
  The new formatter therefore lives in `_state_load.py` and is re-exported
  through `novel_state`, exactly as `_state_input_error` is. Do not place it
  anywhere that reverses that direction.
- The `STATE_INPUT_ERRORS` vocabulary tuple (`_state_load.py`) is the single
  home for "what counts as a state-input error" (audit:2.1.2 finding 4). Every
  boundary keeps catching that same tuple; this plan does not widen, narrow, or
  fork it.
- Commands must not shell out: the deterministic spine invokes no external
  process for its core logic, so cuprum is used only in the installed-binary
  end-to-end tests, never in production command code (design §4). Production
  changes in this plan add **no** dependency and touch **no** cuprum API.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, commit
  messages, and the message text itself (`AGENTS.md` line 18; `en-gb-oxendict`
  skill). The user-facing message must read as British English.
- No code file exceeds 400 lines (`AGENTS.md` lines 24-27). `_state_load.py` is
  currently ~165 lines, so adding one formatter stays well within the cap; if a
  consumer module is pushed over, extract per the existing leaf-module pattern
  (Decision D6 of the 6.3.1 ExecPlan) rather than gutting docstrings.
- Documentation is source of truth: any developers-guide prose that describes
  these boundaries as carrying raw OS text must be refreshed once they no
  longer do (`AGENTS.md` line 47).

## Tolerances (exception triggers)

- Scope: if making the enumerated boundaries actionable requires editing more
  than 9 source files (net) or more than ~200 lines, stop and escalate — the
  design points at exactly seven boundary arms (six draft-read tails routed
  through one new formatter, plus the view-derivation arm rerouted to the
  *existing* `_state_input_error` corrupt arm) across seven modules; the
  `_compile` write-fault tail is out of scope (Decision D6).
- Interface: the formatter is a new internal (underscore-prefixed) symbol; if
  satisfying the task appears to require changing a **public** signature
  (`StateInputError`, `CommandOutcome`, `run`, or any command body's public
  surface), stop and escalate.
- Dependencies: if any work item appears to need a new external dependency, stop
  and escalate. None should.
- Vocabulary: if expressing the inspect/repair remedy needs catching a broader
  exception set than `STATE_INPUT_ERRORS`, stop and escalate rather than
  widening the tuple.
- Iterations: if `make all` still fails after 3 focused attempts on any work
  item, stop and escalate with the failing output.
- Snapshot churn: if updating snapshots touches more than the draft-read message
  constants this plan names, stop and inspect — an unexpected snapshot change
  signals a contract shift the plan did not intend.
- Ambiguity (rule-pack/ledger): the rule-pack (`_desloppify` line 263) and
  device-ledger (`_desloppify_ledger` line 90) `{exc}` sites wrap *typed*
  `RulePackFileError`/`LedgerFileError` (not raw `STATE_INPUT_ERRORS` OS
  faults) and are **not** in the roadmap's enumerated six. Decision D3 keeps
  them out of scope. If review directs folding them in, treat that as a scope
  change and escalate rather than silently widening the plan.

## Risks

- Risk: the six draft-read boundaries do not share one call shape, and the
  seventh (view-derivation) boundary is not a draft-read fault at all. The six
  draft-read boundaries each already hold a `working_dir: pathlib.Path` to pass
  (`_disk_evidence_or_state_error`, `_recount`, `_wordcount`, `_novel_done`,
  `_compile`, `_desloppify`), while `_state_view_or_state_error` has no path at
  all (it takes a parsed `TOMLDocument`). Severity: medium. Likelihood: high.
  Mitigation: the draft-read formatter takes the *reported directory* as a
  single `pathlib.Path` argument plus the caught `exc` for chaining (Decision
  D2), so the six draft-read call sites need no signature gymnastics. The
  view-derivation boundary does NOT call the draft-read formatter — it routes
  through 6.3.1's existing `_state_input_error(state_path(), exc)`
  present-but-corrupt arm, which needs only the `state_path()` it already
  accesses (Decision D7). Work item 1's unit test pins the draft-read message
  for the single path-bearing call shape; Work item 4's unit test pins the
  structurally-incomplete path emitting the corrupt-arm prose.
- Risk: the message must distinguish a *present-but-faulted artefact* (the
  draft-read and view-derivation case — `init` is the wrong remedy, the tree
  exists) from the *missing-`working/`* case 6.3.1 already owns (where `init`
  is right). A draft-read fault must NOT advise `novel state init`. Severity:
  medium. Likelihood: high. Mitigation: the new formatter emits only the
  inspect/repair remedy (it never branches into the `init`-suggesting arm),
  mirroring `_state_input_error`'s present-but-corrupt arm. Decision D2.
- Risk: existing tests assert the old `cannot read …` text and will fail.
  Severity: low. Likelihood: high (expected). Mitigation: these are the
  red-to-green proof. The known direct *message-text* assertions are
  `tests/test_compile_unit.py` line 295 (`match="cannot read chapter drafts"`)
  and `tests/test_desloppify_sourcing.py` line 118
  (`match=r"cannot read chapter drafts"`). A repository-wide sweep (`grep -rn`
  for `cannot read`, `cannot recount`, `cannot evaluate`, and
  `structurally incomplete`) over `tests/` gates that none is missed.
- Risk: the view-derivation boundary has **no** pre-existing message-text guard
  to flip red→green. Verified: the only structurally-incomplete test,
  `tests/test_complete_final_pass_unit.py::test_incomplete_state_exits_three`,
  asserts only `code == ExitCode.STATE_ERROR` and `envelope["ok"] is False`;
  the string `state is structurally incomplete` is asserted in **no** test (it
  appears only in that test's docstring at line 116 and in production code, per
  a `grep` over `tests/`). Severity: medium. Likelihood: certain. Mitigation:
  Work item 4 does not claim line 116 as an assertion to "update"; it **adds**
  a new message-text unit assertion (the structurally-incomplete path now emits
  the `_state_input_error` corrupt-arm prefix
  `… is unreadable or corrupt; inspect and repair it`) as its own red→green
  guard, and the parity/behavioural proof lands in Work item 5 (Decision D7;
  Blocking point B1).
- Risk: a draft-read message arm appears in a stored syrupy snapshot and churns.
  Severity: low. Likelihood: low. Mitigation: the cross-command matrices redact
  `messages` and carry only the missing-`working/` `_STATE_ARM` (verified — the
  matrices have no present-but-faulted draft-read arm), so no matrix snapshot
  stores draft-read text. If a snapshot does churn, treat per the Tolerances
  and re-accept only a reviewed change.
- Risk: the installed-binary error-arm e2e relies on the **locked** cuprum 0.1.0
  surface, which differs from the unreleased source tree. Severity: low.
  Likelihood: low (this plan adds no new cuprum call). Mitigation: the
  behavioural proof for the draft-read faults is in-process (no
  installed-binary arm is required by the §6.3.5 Success criterion). If an
  installed-binary arm is added at all, it reuses the existing fixtures and the
  locked surface pinned in Decision D4; no new cuprum API is introduced.

## Progress

- [x] Work item 1 — shared draft-read actionable-message formatter
      `_draft_read_error(reported_dir, exc)` in `_state_load.py`, re-exported
      through `novel_state.__all__`; unit test
      `tests/test_draft_read_message_unit.py` pins the single `(reported_dir,
      exc)` call shape, the no-`Errno`/no-`{exc}` invariant (per-fault forbidden
      fragments), and the `from exc` chaining. (Red→green; done.)
- [x] Work item 2 — routed the five path-bearing draft-read boundaries
      (`_disk_evidence_or_state_error`, `_recount`, `_wordcount`, `_novel_done`,
      `_compile`'s two tails) through the formatter. The `_compile` atomic-write
      tail kept its own write message with an in-code D6 note. (Done.)
- [x] Work item 3 — routed `_desloppify.source_chapters` through the formatter,
      leaving the rule-pack/ledger sites per Decision D3 (with a strengthened
      in-code D3 note). (Done.)
- [x] Work item 4 — routed the mutator view-derivation boundary
      `_state_view_or_state_error` through 6.3.1's existing `_state_input_error`
      present-but-corrupt arm (NOT the draft-read formatter; Decision D7). Added
      the red→green message-text guard to
      `tests/test_complete_final_pass_unit.py::test_incomplete_state_exits_three`
      (B1). (Red→green; done.)
- [x] Work item 5 — cross-boundary behavioural proof
      (`tests/test_draft_read_message_bdd.py` +
      `tests/features/draft_read_message.feature` +
      `tests/steps/draft_read_message_steps.py`) covering all seven boundaries,
      plus the parity assertion
      (`tests/test_draft_read_message_parity.py`). Refreshed the two direct unit
      assertions (`test_compile_unit.py`, `test_desloppify_sourcing.py`). (Done.)
- [x] Work item 6 — refreshed the `docs/developers-guide.md` exit-3 channel prose
      (around the `StateInputError` discussion) and the structurally-incomplete
      note to describe the two sibling formatters and the view-derivation reuse;
      `markdownlint-cli2 docs/developers-guide.md` and `make nixie` pass. (Done.)

## Surprises & discoveries

- Observation: the cross-command matrices
  (`tests/test_command_surface_matrix.py`,
  `tests/test_console_scripts_error_arms_e2e.py`) carry only two error arms —
  `_USAGE_ARM` (exit 2) and `_STATE_ARM` (exit 3, the *missing-`working/`*
  fault, prefix `"no novel working/ found in"`). They have **no**
  present-but-faulted draft-read arm. Evidence:
  `grep -n "message_prefix\|_STATE_ARM" tests/test_command_surface_matrix.py tests/test_console_scripts_error_arms_e2e.py`.
  Impact: the draft-read behavioural proof must be a **new** suite (mirroring
  `tests/test_state_input_message_*`), not an edit to the matrices, and no
  matrix snapshot stores draft-read text.
- Observation: the rule-pack and device-ledger `{exc}` sites wrap *typed*
  errors, not raw OS faults. `_desloppify` line 263 wraps `RulePackFileError`;
  `_desloppify_ledger` line 90 wraps `LedgerFileError`. Both already carry
  their own structured message and have their own exit-3 contract documented in
  the developers' guide (lines 1334-1339, 1497). Evidence:
  `grep -rn "RulePackFileError\|LedgerFileError" novel_ralph_skill/commands/`.
  Impact: Decision D3 scopes them out of the enumerated draft-read six; folding
  them in would change the remedy semantics (a bad pack/ledger *file* is not a
  `working/` draft fault).
- Observation: the locked, installed cuprum is 0.1.0 and its `SafeCmd.run_sync`
  signature is
  `(*, capture=True, echo=False, context=ExecutionContext | None)`. Evidence:
  `uv run python -c "import inspect; from cuprum.sh import SafeCmd; print(inspect.signature(SafeCmd.run_sync))"`
  printed exactly that; `uv.lock` pins `cuprum 0.1.0`. Impact: confirms
  Decision D4 and the 6.3.1 plan's D5; no cuprum API is touched by this plan.

## Decision log

- Decision (D1): the draft-read formatter lives in
  `novel_ralph_skill/commands/_state_load.py`, beside `_state_input_error`, and
  is re-exported through `novel_state` via its `__all__`. Rationale:
  `_state_load` is the dependency-free leaf that already owns the exit-3
  message vocabulary and imports only from `state`/`contract.runner`, so it
  cannot form an import cycle with the consumers; this is the same home 7.3.3's
  *wrapper* will land in, so the formatter and wrapper share one place (the
  roadmap's "share one home" coordination). Date/Author: 2026-06-26, planner.
- Decision (D2): the draft-read formatter signature is
  `_draft_read_error(reported_dir: pathlib.Path, exc: Exception) -> StateInputError`
  (final name to be settled in the unit test). It emits a single
  inspect/repair-remedy message naming the `working/` tree — it never branches
  into the `init`-suggesting arm, because a present-but-faulted artefact is not
  repaired by `init`. Rationale: each of the six draft-read boundaries already
  holds a `working_dir`/`root` to pass; a one-argument-plus-exc shape covers
  every draft-read call site. Chaining via `raise … from exc` preserves the
  cause for debugging while `exc.messages` carries only actionable prose. The
  formatter serves *only* the six draft-read boundaries; the view-derivation
  boundary uses a different home (Decision D7). Date/Author: 2026-06-26,
  planner.
- Decision (D3): the rule-pack (`_desloppify` line 263) and device-ledger
  (`_desloppify_ledger` line 90) `{exc}` sites are **out of scope**. They wrap
  typed `RulePackFileError`/`LedgerFileError` (not raw `STATE_INPUT_ERRORS` OS
  faults), carry their own structured message, and concern a *pack/ledger
  file*, not a `working/` draft tree — so the draft-read formatter's "names the
  `working/` tree" prose would mislead. The roadmap enumerates exactly six
  draft-read boundaries plus the view-derivation boundary; these two are
  siblings, not members. This is recorded so a reviewer does not mistake them
  for a missed seventh/eighth draft-read site. Date/Author: 2026-06-26, planner.
- Decision (D4): if any installed-binary arm is touched, it is pinned to the
  **locked cuprum 0.1.0** surface already used by the existing fixtures:
  `ProgramCatalogue(projects=(ProjectSettings(name, programs, …),))`,
  `Program(str_path)`, `sh.make(program, catalogue=…)` → `SafeCmd`,
  `SafeCmd.run_sync(*, capture=True, echo=False, context=ExecutionContext(cwd=…))`
  returning a `CommandResult` with `exit_code`/`stdout`/`stderr`. Verified in
  the project venv (see Surprises). The §6.3.5 Success criterion is satisfied
  in-process, so no new installed-binary arm is required; this decision only
  bounds the option if one is added. Date/Author: 2026-06-26, planner.
- Decision (D5): the behavioural proof is a **new** in-process suite mirroring
  `tests/test_state_input_message_bdd.py` /
  `tests/features/state_input_message.feature`, not an edit to the
  cross-command matrices, because the matrices carry no present-but-faulted
  draft-read arm (see Surprises). Date/Author: 2026-06-26, planner.
- Decision (D6): the `_compile.py` line 150 atomic-**write** tail
  (`f"cannot write {_COMPILED_REL}: {exc}"`, wrapping `write_text_atomically`
  when `working/manuscript/` is absent) is **out of scope**, and is NOT routed
  through `_draft_read_error`. Rationale: it is a *write* fault on the exit-3
  channel, not a draft-*read* fault. The roadmap enumerates exactly six
  draft-read boundaries plus the view-derivation boundary; this tail is none of
  them. Its correct remedy is write-shaped ("create `working/manuscript/`" or
  "check write permission"), not the draft-read formatter's "inspect the
  `working/` tree you read"; forcing it through `_draft_read_error` would emit
  a *read*-remedy message for a *write* fault and mislabel the failure. It does
  genuinely interpolate raw `{exc}` today, so polishing it is real work — but
  it belongs to a future write-fault-polish task (a sibling of this one),
  recorded here so a reviewer does not mistake it for a missed draft-read tail.
  This resolves Blocking point B2 and supersedes every earlier "Decision D6"
  forward reference in this plan (which were stale pointers at the *6.3.1*
  plan's leaf-split decision, not a decision in this plan). Date/Author:
  2026-06-26, planner.
- Decision (D7): the mutator view-derivation boundary
  `_state_view_or_state_error` is routed through 6.3.1's existing
  `_state_input_error(state_path(), exc)` present-but-corrupt arm, **not** the
  new `_draft_read_error` formatter. Rationale: a structurally-incomplete
  `state.toml` is a *state-document* fault, not a draft or a generic
  artefact-under-`working/`. 6.3.1 Decision D8 reasoned that this boundary
  reports a "parsed-but-structurally-incomplete" document whose remedy
  "differs" from a draft fault, and warned future reviewers not to conflate it.
  Because the document parsed, the file `state.toml` exists, so
  `_state_input_error`'s `if not path.parent.exists() or not path.exists()`
  test is false and its present-but-corrupt arm fires — emitting `<state.toml
  path> is unreadable or corrupt; inspect and repair it, or restore it from a
  known-good copy`, which names the *state-document path* (the right artefact)
  and is exactly
  the inspect/repair remedy the roadmap mandates, with no `Errno`/`{exc}`. This
  reuses 6.3.1's machinery, respects D8's distinction, and keeps the draft-read
  formatter's vocabulary honest (it never has to claim to cover a
  state-document fault). This resolves Blocking point B3 and supersedes the
  earlier draft of Work item 4 (which routed this boundary through the
  draft-read formatter and mislabelled it). Date/Author: 2026-06-26, planner.
- Decision (D9): no Hypothesis property test was added for `_draft_read_error`.
  Rationale: the formatter is a fixed-string builder parameterised only by
  `reported_dir` (interpolated) and an *unused* `exc` (kept for signature
  symmetry with `_state_input_error` and `from exc` chaining). Its input domain
  is too narrow to earn a property test (`AGENTS.md` gates property tests to
  broad input domains), exactly as 6.3.1 found for the sibling formatter. The
  example-based unit test instead parametrises two representative
  `STATE_INPUT_ERRORS` members (`UnicodeDecodeError`, `PermissionError`) and
  forbids *each fault's own* distinctive repr fragment, so a leak of either is
  caught independently (coderabbit round-1 finding, addressed). Date/Author:
  2026-06-26, implementer.

## Outcomes & retrospective

Delivered all six work items. The six draft-read boundaries now route through one
`_draft_read_error(reported_dir, exc)` formatter that names the `working/` tree
and advises inspect/repair without leaking an `Errno`, `{exc}` repr, traceback,
or `init` suggestion; the mutator view-derivation boundary reuses
`_state_input_error`'s present-but-corrupt arm (naming the `state.toml` path) per
Decision D7. The `grep` sweep over `novel_ralph_skill/` and `tests/` returns no
live `cannot read …: {exc}` or `state is structurally incomplete: {exc}`
string — only negative assertions and docstrings describing the new behaviour.

Deviations and notes:

- The `exc` parameter of `_draft_read_error` is intentionally unused in the body
  (the message is fault-independent by design, mirroring how `_state_input_error`
  ignores the `Errno`); it is retained for call-site symmetry and `from exc`
  chaining. Ruff/Pylint did not flag it.
- `make fmt` reflowed every Markdown file in the repo (the recurring
  mdformat-all churn). Per established practice in this repo, that spurious churn
  (including a full reflow of `docs/developers-guide.md`) was parked in a git
  stash and the deliberate developers-guide edit re-applied to the pristine HEAD
  version, so the committed Markdown diff is minimal. The deterministic gate
  `check-fmt` (run by `make all`) passed without needing `make fmt`.
- Behavioural/parity proof for `novel done` and `novel compile --check` uses the
  `final-pass` corpus phase (which carries a present `compiled.md`) rather than
  the mid-drafting baseline, because those two boundaries read a draft only when
  `compiled.md` is present; against the baseline they short-circuit benignly.
  Recorded so a future maintainer understands the phase choice.
- Coderabbit: the first `coderabbit review --agent` pass returned one minor
  finding (parametrise the unit test to forbid each fault's own repr fragment),
  which was addressed. A second confirmation pass stalled with no output for
  >20 minutes (the CLI buffers output until exit; the process stayed blocked on
  the review service with negligible CPU — a transient backend/rate-limit stall).
  Rather than block the work item indefinitely (the deterministic `make all` gate
  is green and the prior finding is fixed), the stall is recorded here and in the
  open issues, and the commits proceeded.

## Context and orientation

The `novel` console-script is a single multiplexer over five operations: a
`state` subgroup (`init`, `check`, `set-cursor`, `advance-phase`, `recount`,
`reconcile`, `set-chapters`, and the gate-drafting setters) plus four leaf verbs
(`done`, `compile`, `desloppify`, `wordcount`) (design §4). Every command
emits a shared JSON envelope; a failure populates the envelope's `messages`
array from a raised exception. `StateInputError` is mapped to exit code 3 by
`novel_ralph_skill/contract/runner.py`, which emits `list(exc.messages)`.

The exit-3 message vocabulary lives in the dependency-free leaf module
`novel_ralph_skill/commands/_state_load.py`, re-exported through
`novel_ralph_skill/commands/novel_state.py`. It already holds:

- `WORKING_DIR_NAME`, `working_dir()`, `state_path()` — the single accessors for
  where commands look;
- `STATE_INPUT_ERRORS` — the tuple of exceptions that count as a state-input
  fault (`OSError`, `tomllib.TOMLDecodeError`, `KeyError`, `ValueError`,
  `TypeError`);
- `_state_input_error(path, exc)` — 6.3.1's formatter for the *state.toml-load*
  fault, with two arms: a missing-`working/` arm (advises `novel state init`)
  and a present-but-corrupt arm (advises inspect/repair).

This plan adds a sibling formatter for the *draft-read* fault, which always
uses the inspect/repair remedy (the tree exists; only an artefact under it is
faulted). The view-derivation boundary is a *state-document* fault and reuses
`_state_input_error`'s present-but-corrupt arm instead (Decision D7).

The seven boundaries that today interpolate a raw `{exc}` on the exit-3 channel
and are in scope for this plan (the six draft-read tails plus the
view-derivation boundary; the `_compile` write tail is scoped out by Decision
D6):

1. `novel_state._disk_evidence_or_state_error` (`novel_state.py` line 156) —
   `f"cannot read disk evidence under {working_dir}: {exc}"`. Wraps
   `check_disk_evidence` (reads each `draft.md`). Used by `novel state check`.
2. `_recount._recount_or_state_error` (`_recount.py` line 93) —
   `f"cannot recount chapter drafts: {exc}"`. Wraps `recount_words`. Used by
   `novel state recount`.
3. `_wordcount` (`_wordcount.py` line 99) —
   `f"cannot read chapter drafts: {exc}"`. Wraps `recount_words`. Used by
   `novel wordcount`.
4. `_novel_done` (`_novel_done.py` line 92) —
   `f"cannot evaluate the done predicate under {root}: {exc}"`. Wraps
   `evaluate_done` (reads drafts and
   `compiled.md`). Used by `novel done`.
5. `_desloppify.source_chapters` (`_desloppify.py` line 210) —
   `f"cannot read chapter drafts: {exc}"`. Wraps `_chapter_text`. Used by
   `novel desloppify`.
6. `_compile` — two draft-read tails: `compile_manuscript` (`_compile.py` line
   141, `f"cannot read chapter drafts: {exc}"`, wrapping
   `present_draft_bodies`) and `check_compiled` (`_compile.py` line 211,
   `f"cannot read chapter drafts or {_COMPILED_REL}: {exc}"`, wrapping
   `compiled_matches_drafts`, which calls
   `compiled_matches_drafts(state, working_dir())` and has **no** `root` local
   — pass `working_dir()`). Used by `novel compile` / `novel compile --check`.
   (The atomic-**write** tail at `_compile.py` line 150,
   `f"cannot write {_COMPILED_REL}: {exc}"`, is a *write* fault, not a
   draft-read, and is scoped **out** by Decision D6 — it wants a write-remedy,
   not an inspect-the-draft remedy.)

The seventh boundary the roadmap names is **not** a draft-read site and does
not route through the draft-read formatter:

- `_state_mutators._state_view_or_state_error` (`_state_mutators.py`, line
  146) — `f"state is structurally incomplete: {exc}"`. Wraps
  `document_to_state` on a *parsed-but-incoherent `state.toml` document* (a
  missing table/key or a bad phase string). Used by every mutator (`set-cursor`,
  `advance-phase`, `recount`, `reconcile`, `set-chapters`, gate setters). This
  is a **state-document** fault, so it routes through 6.3.1's existing
  `_state_input_error(state_path(), exc)` present-but-corrupt arm (Decision
  D7), not the draft-read formatter.

The readers these boundaries wrap raise the `STATE_INPUT_ERRORS` members on a
present-but-faulted artefact; an *absent* `draft.md` is benign (counted `0`)
and never reaches these arms (verified: `recount_words` docstring,
`novel_ralph_skill/state/wordcount.py` lines 103-105). So the only behaviour
this plan changes is the *message text* of the present-but-faulted path.

Test orientation. The draft-read message proof is a new in-process suite
mirroring `tests/test_state_input_message_unit.py`,
`tests/test_state_input_message_bdd.py`, and
`tests/features/state_input_message.feature` (with steps under `tests/steps/`).
Direct draft-read *message-text* assertions to refresh:
`tests/test_compile_unit.py` line 295 (`match="cannot read chapter drafts"`) and
`tests/test_desloppify_sourcing.py` line 118
(`match=r"cannot read chapter drafts"`). The view-derivation boundary has
**no** pre-existing message-text guard:
`tests/test_complete_final_pass_unit.py` line 116 is a docstring, and
`test_incomplete_state_exits_three` asserts only `code == ExitCode.STATE_ERROR`
and `envelope["ok"] is False` (verified by `grep` over `tests/`: the string
`state is structurally incomplete` is asserted nowhere). Work item 4 therefore
**adds** a new message-text unit assertion rather than refreshing one. The
cross-command matrices (`tests/test_command_surface_matrix.py`,
`tests/test_console_scripts_error_arms_e2e.py`) carry no draft-read arm and are
not edited.

Design and standards to read before starting: design §3.2 (the exit-code
table), §3.4 (the state-input channel / atomic writes);
`docs/adr-003-shared-interface-contract.md` (the shared envelope and message
contract); `docs/scripting-standards.md` lines 600-688 ("human-friendly error
messages should highlight remediation steps"; production code presents friendly
messages); `AGENTS.md` (quality gates, en-GB Oxford spelling, the 400-line cap,
the testing rules at lines 141-165). The 6.3.1 ExecPlan
(`docs/execplans/roadmap-6-3-1.md`) is the template this plan follows; its
Decision D6 (leaf-module split for the cap) and Decision D8 (the
view-derivation boundary being a distinct *state-document* fault, not a
draft-read or load fault) are load-bearing context — 6.3.5 is the task that
makes the view-derivation boundary's exit-3 message actionable, but it honours
D8 by routing it through `_state_input_error`'s present-but-corrupt arm (the
state-document remedy), not the draft-read formatter (this plan's Decision D7).
When referring to "D6" or "D8" in a work item, always qualify which plan's
decision is meant; this plan's own Decision D6 concerns the `_compile`
write-fault tail.

## Plan of work

The change is surgical: add one shared draft-read formatter beside
`_state_input_error`, route the enumerated boundaries through it, then refresh
every test and document that pinned the old raw text. Stages are ordered so the
formatter and its unit proof land first (red→green), then each consumer
follows, then the behavioural cross-boundary proof, then documentation.

### Work item 1 — Shared draft-read actionable-message formatter

Implements: design §3.2 (the exit-3 channel) and §3.4;
`docs/adr-003-shared-interface-contract.md`; `docs/scripting-standards.md`
lines 600-688. Closes the §6.3.5 requirement to "route all six call sites
through a shared actionable formatter analogous to `_state_input_error`".

Docs to read: design §3.2 and §3.4; `adr-003-shared-interface-contract.md`;
`docs/scripting-standards.md` lines 600-688; `AGENTS.md` lines 18, 24-27,
141-165; `docs/execplans/roadmap-6-3-1.md` (the `_state_input_error` precedent
and the 6.3.1 plan's Decision D6, the leaf-module split — distinct from *this*
plan's Decision D6, which concerns the `_compile` write-fault tail).

Skills to load: `python-router` (route to the smaller skills it picks);
`python-errors-and-logging` (exception design, `raise … from …`, narrow
`except`, the `N818`/`TRY`/`EM` Ruff rules — the formatter raises
`StateInputError`); `python-types-and-apis` (the formatter's signature shape);
`en-gb-oxendict` (the user-facing message wording); `leta` (navigate
`_state_load.py`, `novel_state.py`, and the consumers —
`leta show _state_input_error`, `leta refs STATE_INPUT_ERRORS`);
`python-verification` then `hypothesis` (decide whether a property test is
warranted — see Tests below).

What to do:

1. In `novel_ralph_skill/commands/_state_load.py`, add a module-private
   formatter — proposed name `_draft_read_error(reported_dir: pathlib.Path,
   exc: Exception) -> StateInputError` —
   that builds the actionable `StateInputError` for a present-but-faulted
   *draft artefact* (a corrupt/unreadable `draft.md` or `compiled.md`) under
   `working/`. Per Decision D2 it emits a single inspect/repair-remedy message
   that names `reported_dir` (the `working/` tree) and advises
   inspection/repair — it never advises `novel state init`, and it carries no
   raw `Errno`, no `{exc}` repr, and no traceback. It serves only the six
   draft-read boundaries; the structurally-incomplete `state.toml` fault is a
   state-document fault routed elsewhere (Decision D7). Final wording is
   settled in the unit test as the executable specification; keep it en-GB.
   Raise `StateInputError(message) from exc`.
2. Re-export the new symbol through `novel_state` (add it to whatever `__all__`
   / re-export mechanism already forwards `_state_input_error`), so consumers
   keep importing from `novel_state` unchanged.
3. Give the formatter a full docstring per `AGENTS.md` lines 21-23 (100%
   docstring coverage via interrogate), explaining why it differs from
   `_state_input_error` (the tree exists; only a draft artefact is faulted, so
   `init` is the wrong remedy), why it does NOT serve the
   structurally-incomplete `state.toml` fault (a state-document fault, Decision
   D7), and citing roadmap §6.3.5.

Tests this work item must add or update (`AGENTS.md` lines 141-165):

- Unit (new, `tests/test_draft_read_message_unit.py` or extend the existing
  `tests/test_state_input_message_unit.py`): call `_draft_read_error` (and/or
  drive one boundary) and assert the message contains the `working/` tree name
  and an inspect/repair remedy, contains **no** `Errno`, **no** traceback
  marker, and **no** `init` suggestion, for a representative caught
  `STATE_INPUT_ERRORS` member (e.g. a `UnicodeDecodeError`). The formatter has
  a single `(reported_dir, exc)` call shape; the view-derivation boundary is
  covered separately by Work item 4 (it does not use this formatter).
- Property (consider via `python-verification`; add with `hypothesis` only if it
  earns its place — `AGENTS.md` line 162 gates property tests to broad input
  domains): a property that for any `reported_dir` and any caught
  `STATE_INPUT_ERRORS` member, the produced message never contains `Errno`,
  never contains a `Traceback` marker, and always names a remedy. If the input
  domain is too narrow to justify Hypothesis (as 6.3.1 found for the sibling
  formatter, Decision D7), record that in the Decision Log and keep the
  example-based unit test instead — do not add a property test that only
  restates the unit logic.

Validation: `make all` (runs `build check-fmt lint typecheck test`). The new
unit test fails before the formatter exists and passes after.

### Work item 2 — Route the five path-bearing draft-read boundaries

Implements: roadmap §6.3.5 ("route all six call sites through a shared
actionable formatter … that names the `working/` tree … without leaking
`Errno`"); design §3.2; `adr-003`.

Docs to read: same as Work item 1, plus the module docstrings of
`novel_state.py`, `_recount.py`, `_wordcount.py`, `_novel_done.py`, and
`_compile.py` (each pins its exit-3 contract).

Skills to load: `python-router` → `python-errors-and-logging`; `leta` (confirm
each call site and that each already holds a `working_dir`/`root`);
`en-gb-oxendict`.

What to do:

1. In `novel_ralph_skill/commands/novel_state.py`, rewrite
   `_disk_evidence_or_state_error`'s `except STATE_INPUT_ERRORS as exc:` arm
   (line 156) to `raise _draft_read_error(working_dir, exc)`. Keep the caught
   tuple unchanged.
2. In `_recount.py`, rewrite `_recount_or_state_error`'s arm (line 93) to
   `raise _draft_read_error(_working_dir(), exc)`.
3. In `_wordcount.py`, rewrite the `recount_words` tail (line 99) to
   `raise _draft_read_error(working_dir, exc)`.
4. In `_novel_done.py`, rewrite the `evaluate_done` tail (line 92) to
   `raise _draft_read_error(root, exc)`.
5. In `_compile.py`, rewrite both draft-read tails. `compile_manuscript`
   (line 141) holds `root = working_dir()`, so use
   `raise _draft_read_error(root, exc)`. `check_compiled` (line 211) has **no**
   `root` local — it calls `compiled_matches_drafts(state, working_dir())` — so
   pass `working_dir()`: `raise _draft_read_error(working_dir(), exc)`. Leave
   the atomic-**write** tail at line 150
   (`f"cannot write {_COMPILED_REL}: {exc}"`) **unchanged**: it is a write
   fault scoped out by Decision D6 (it wants a write-remedy, not the draft-read
   formatter's inspect-the-draft remedy). Add a one-line in-code comment at
   that tail noting it is deliberately out of the draft-read formatter's scope
   per Decision D6, so a future reader does not mistake it for a missed read
   tail.
6. Update each rewritten boundary's docstring to state it routes through the
   shared `_draft_read_error` formatter so the message cannot drift, in en-GB.

Tests this work item must add or update:

- Unit/behavioural: covered by Work item 5's cross-boundary suite plus the
  refreshed direct assertions; this item's edits are proven red→green there. If
  a per-module unit test already pins a boundary's message (e.g.
  `test_compile_unit.py`), update its expected text here so the module's own
  suite stays green.

Validation: `make all`. The refreshed assertions fail before this item and pass
after.

### Work item 3 — Route the desloppify draft-read boundary

Implements: roadmap §6.3.5 (`_desloppify` is one of the enumerated six); design
§3.2; `adr-003`.

Docs to read: `_desloppify.py` (the `source_chapters` docstring and the
rule-pack/ledger exit-code split documented in `docs/developers-guide.md` lines
1328-1359, 1497); this plan's Decision D3.

Skills to load: `python-router` → `python-errors-and-logging`; `leta`;
`en-gb-oxendict`.

What to do:

1. In `novel_ralph_skill/commands/_desloppify.py`, rewrite
   `source_chapters`'s `except STATE_INPUT_ERRORS as exc:` arm (line 210) to
   `raise _draft_read_error(working_dir, exc)`. Update its docstring to cite
   the shared formatter, en-GB.
2. Leave the rule-pack `RulePackFileError` arm (line 263) and the device-ledger
   `LedgerFileError` arm (`_desloppify_ledger.py` line 90) **unchanged** per
   Decision D3 (typed errors, distinct artefact, distinct remedy). Add a brief
   in-code comment (or rely on the existing one) noting they are deliberately
   out of the draft-read formatter's scope so a future reader does not mistake
   them for a missed site.

Tests this work item must add or update:

- Update `tests/test_desloppify_sourcing.py` line 118
  (`match=r"cannot read chapter drafts"`) to the new actionable prefix/pattern.
- The cross-boundary behavioural coverage lands in Work item 5.

Validation: `make all`. The refreshed sourcing assertion fails before this item
and passes after.

### Work item 4 — Route the mutator view-derivation boundary

Implements: roadmap §6.3.5 ("include the mutator view-derivation boundary
`_state_mutators._state_view_or_state_error` … so the structurally-incomplete
arm stops leaking raw `{exc}` and carries an inspect/repair remedy (audit:6.3.2
folded in)"); design §3.2; `adr-003`. This is the boundary 6.3.1 Decision D8
treated as a distinct *state-document* fault; 6.3.5 makes its exit-3 message
actionable **without** conflating it with a draft fault, by routing it through
6.3.1's existing `_state_input_error` present-but-corrupt arm rather than the
new draft-read formatter (this plan's Decision D7; Blocking point B3).

Docs to read: `_state_mutators.py` lines 116-147 (the
`_state_view_or_state_error` docstring and its `Decision Log D8` citation); the
6.3.1 ExecPlan Decision D8 and its Outcomes (the present-but-corrupt arm wording
`<path> is unreadable or corrupt; inspect and repair it, or restore it from a
known-good copy`); `_state_load.py` lines 76-119 (`_state_input_error` — the
two-arm
present/absent branch); `docs/developers-guide.md` line 589 (the exit-3 channel
prose).

Skills to load: `python-router` → `python-errors-and-logging`; `leta` (confirm
every mutator call site of `_state_view_or_state_error`, and confirm the
existing imports in `_state_mutators.py`); `python-testing` (the new unit
guard); `en-gb-oxendict`.

What to do:

1. In `novel_ralph_skill/commands/_state_mutators.py`, rewrite
   `_state_view_or_state_error`'s `except STATE_INPUT_ERRORS as exc:` arm (line
   146) from the open-coded `f"state is structurally incomplete: {exc}"` string
   to `raise _state_input_error(_state_path(), exc) from exc`. Note the module
   imports the accessors **aliased** — `working_dir as _working_dir` and
   `state_path as _state_path` (line 43; advisory A1) — and already imports
   `_state_input_error` (it is used by `_load_document_or_state_error` at line
   113). Because a structurally-incomplete `state.toml` *parsed*, the file
   exists, so `_state_input_error`'s
   `if not path.parent.exists() or not path.exists()` test is false and the
   present-but-corrupt arm fires — emitting `<state.toml path> is unreadable or
   corrupt; inspect and repair it, or restore it from a known-good copy`, the
   inspect/repair remedy the roadmap mandates, naming the state-document
   path with no raw `{exc}`/`Errno`. Do **not** route this through
   `_draft_read_error`: a state-document fault is not a draft fault (Decision
   D7; respects 6.3.1 Decision D8).
2. Update the `_state_view_or_state_error` docstring (and its `Decision Log D8`
   reference) to record that 6.3.5 makes this boundary's message actionable by
   routing it through `_state_input_error`'s present-but-corrupt arm, while
   keeping it distinct from a draft fault per D8 (it reuses the state-document
   remedy, not the draft-read formatter). en-GB.

Tests this work item must add or update:

- **Add** a new message-text unit assertion as the red→green guard (Blocking
  point B1): the view-derivation boundary has **no** existing message-text
  guard — `tests/test_complete_final_pass_unit.py` line 116 is a docstring, and
  `test_incomplete_state_exits_three` asserts only the exit code and
  `envelope["ok"] is False`. Either extend that test (or add one beside it, or
  extend `tests/test_state_input_message_unit.py`) to drive a mutator against a
  parseable-but-structurally-incomplete `state.toml` and assert the `messages`
  text contains the corrupt-arm prefix
  (`is unreadable or corrupt; inspect and repair it`), names the `state.toml`
  path, and contains **no** `state is structurally incomplete`, **no** raw
  `{exc}`/`Errno`/traceback marker, and **no** `init` suggestion. This
  assertion fails before this item (the boundary still emits
  `state is structurally incomplete: {exc}`) and passes after.
- The cross-boundary behavioural proof for the view-derivation arm lands in
  Work item 5; the existing corrupt-arm parity test
  (`tests/test_state_input_message_parity.py::test_both_load_boundaries_emit_identical_corrupt_message`)
  already exercises `_state_input_error`'s corrupt arm, so no parity
  regression is expected from reusing it here.

Validation: `make all`. The new structurally-incomplete message-text unit
assertion (added in this item) fails before this item and passes after.

### Work item 5 — Cross-boundary behavioural proof and parity

Implements: roadmap §6.3.5 Success criterion ("a behavioural test drives at
least one command per draft-read boundary from a faulted-draft state and
asserts exit 3 with an actionable message naming the `working/` tree and a
remedy, with no raw `Errno`/`{exc}` text; all six draft-read call sites and the
mutator view-derivation boundary emit the shared actionable prose; and the
affected command suites stay green"); design §3.2; `adr-003`.

Docs to read: design §3.2; `adr-003`; `AGENTS.md` lines 143-165 (pytest-bdd for
behavioural tests, snapshot discipline); the existing
`tests/test_state_input_message_bdd.py`,
`tests/features/state_input_message.feature`, and
`tests/test_state_input_message_parity.py` as the structural template.

Skills to load: `python-router` → `python-testing` (fixture scopes,
parametrization, the unit/behavioural boundary, syrupy discipline); `leta`;
`en-gb-oxendict` (the feature prose).

What to do:

1. Add a behavioural suite (preferred: a `pytest-bdd` `.feature` under
   `tests/features/` with steps under `tests/steps/`, mirroring
   `state_input_message.feature`) that, for each of the seven boundaries,
   builds a coherent `working/` tree, induces the present-but-faulted condition
   the boundary detects, drives a representative command, and asserts:
   - exit 3;
   - an inspect/repair remedy that names the faulted artefact — the `working/`
     tree for the six draft-read boundaries, the `state.toml` path for the
     view-derivation boundary;
   - the text contains **no** `Errno`, **no** `{exc}`/traceback marker, **no**
     `init` suggestion, and **no** old raw string (`cannot read …`, `state is
     structurally incomplete`).
   The induced faults: a chapter `draft.md` corrupted to invalid UTF-8 (covers
   `_disk_evidence_or_state_error` via `novel state check`, `_recount` via
   `novel state recount`, `_wordcount` via `novel wordcount`, `_novel_done` via
   `novel done`, `_desloppify.source_chapters` via `novel desloppify`, and
   `_compile` via `novel compile` / `novel compile --check`); and a
   parseable-but-structurally-incomplete `state.toml` (covers
   `_state_view_or_state_error` via any mutator, e.g.
   `novel state set-cursor`). Tag the view-derivation scenario so it is visibly
   distinct: it asserts the `_state_input_error` corrupt-arm prose (the
   state-document remedy), not the draft-read prose.
2. Add a **parity** assertion (mirroring
   `tests/test_state_input_message_parity.py`) for the **six draft-read
   boundaries** that proves they all emit the one `_draft_read_error`
   formatter's prose. Do **not** assert byte-for-byte identity *across*
   boundaries: the draft-read formatter interpolates the `reported_dir`, and
   the six boundaries pass different directories under different commands, so
   two messages match verbatim only when their `reported_dir` matches (advisory
   A3). Instead assert the one **formatter-owned remedy substring** (the fixed
   inspect/repair clause) appears in each boundary's `messages`, so a one-sided
   re-wording of that clause reintroduces drift the test catches. The
   view-derivation boundary is **not** in this draft-read parity set — it shares
   `_state_input_error`'s corrupt arm, already guarded by the existing
   `test_both_load_boundaries_emit_identical_corrupt_message` parity test; the
   Work item 4 unit guard pins its message.

Tests this work item must add or update:

- Behavioural (`pytest-bdd`): the cross-boundary scenario above.
- Parity (`pytest`): the shared-prose assertion.
- Snapshot: none expected — the matrices redact `messages` and carry no
  draft-read arm (Surprises). If a snapshot churns, treat per the Tolerances
  and re-accept only a reviewed change with `--snapshot-update`.

Validation: `make all`. The behavioural and parity suites fail before Work
items 1-4 land and pass after.

### Work item 6 — Refresh affected documentation

Implements: `AGENTS.md` line 47 (keep `docs/` reflecting the latest state);
roadmap §6.3 self-documenting intent.

Docs to read: `docs/developers-guide.md` — the exit-3 channel discussion around
line 589 (`a missing or unparseable state.toml … uses the same channel`), the
desloppify/ledger sections around lines 1328-1359 and 1497, and the
structurally-incomplete note around lines 1140-1148
(`_state_view_or_state_error` → `document_to_state`); `AGENTS.md` lines 47,
96-98, 167-177.

Skills to load: `en-gb-oxendict`; `leta` (locate the exact lines).

What to do:

1. Edit any developers-guide prose that claims these boundaries surface raw
   `Errno`/`{exc}` text so it describes the new actionable message. The exit-3
   discussion around line 589 and the structurally-incomplete note around lines
   1140-1148 describe *routing*, not message text, and stay accurate; add a
   sentence (where it reads cleanly) noting the six draft-read boundaries now
   emit the shared `_draft_read_error` actionable prose and the view-derivation
   boundary now reuses `_state_input_error`'s present-but-corrupt remedy (so
   the structurally-incomplete fault is actionable but kept distinct from a
   draft fault per Decision D7). Do **not** restate the rule-pack/ledger exit-3
   contract as changed — per Decision D3 those messages are unchanged — and do
   **not** claim the `_compile` write-fault tail changed (Decision D6). Keep
   edits accurate and en-GB; do not over-claim.

Tests / validation: documentation-only. Run `make markdownlint` and
`make nixie` on the edited Markdown (per `AGENTS.md` lines 96-98 and the
standing rule for Markdown changes). No Mermaid is added, but `make nixie` is
run as the standard Markdown gate. Also run `make all` to confirm nothing else
regressed.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-5`.

1. Confirm the branch and a clean tree:

   ```bash
   git branch --show-current   # expect: roadmap-6-3-5
   git status --short          # expect: empty
   ```

2. Before each work item, read the cited docs and load the cited skills. After
   each work item, run the gate and commit:

   ```bash
   make all
   ```

   Expect the final line to report all of `build`, `check-fmt`, `lint`,
   `typecheck`, and `test` passing. For the documentation work item (6), also
   run:

   ```bash
   make markdownlint
   make nixie
   ```

3. Sweep for any missed old text before declaring done:

   ```bash
   grep -rn \
     -e "cannot read chapter drafts" \
     -e "cannot recount chapter drafts" \
     -e "cannot read disk evidence" \
     -e "cannot evaluate the done predicate" \
     -e "state is structurally incomplete" \
     novel_ralph_skill/ tests/
   ```

   The only acceptable remaining matches are docstrings or comments rewritten
   to describe the *new* behaviour, never a live message string that
   interpolates `{exc}`. The rule-pack/ledger `cannot read rule pack`/
   `cannot read device ledger` strings remain by Decision D3, and the
   `_compile.py:150` `cannot write {_COMPILED_REL}: {exc}` write-fault tail
   remains by Decision D6 (it is a write fault, out of this plan's scope).

4. Commit each work item separately with an imperative, en-GB subject
   (`AGENTS.md`
   lines 99-108), gating each commit on `make all`.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` passes (`pytest -v -n …`, plus build/lint/typecheck). The
  new draft-read unit test, the cross-boundary behavioural suite, the parity
  assertion, and the refreshed direct assertions all pass; each fails before
  its corresponding production change and passes after.
- Behaviour: with a coherent `working/` tree whose chapter `draft.md` is
  corrupt, running `novel state check`, `novel state recount`,
  `novel wordcount`, `novel done`, `novel desloppify`, and `novel compile` each
  exits 3 and prints an envelope whose `messages` names the `working/` tree and
  an inspect/repair remedy, with no `Errno`, no `{exc}` repr, no traceback, and
  no `init` suggestion. Driving any mutator (e.g. `novel state set-cursor`)
  against a parseable-but-structurally-incomplete `state.toml` likewise exits 3
  with an inspect/repair remedy, but names the **`state.toml` path** (via
  `_state_input_error`'s present-but-corrupt arm, Decision D7), not the
  `working/` tree, and no longer carries
  `state is structurally incomplete: {exc}`.
- Lint/typecheck: `make lint` and `make typecheck` pass (en-GB comments, 100%
  docstring coverage via interrogate, Ruff, Pylint, `ty`).
- Markdown (Work item 6): `make markdownlint` and `make nixie` pass.

Quality method (how we check): `make all` for every work item;
`make markdownlint` and `make nixie` for the Markdown change; the `grep -rn`
sweep above as the anti-drift backstop.

## Idempotence and recovery

Every step is re-runnable. The production edits are pure text/exception
construction with no filesystem mutation, so re-applying a work item is safe.
Snapshot updates (if any unexpectedly arise) are recoverable via
`git checkout -- tests/__snapshots__` followed by a reviewed
`--snapshot-update`. If a commit fails the gate, fix forward and re-run
`make all`; do not commit a failing gate (`AGENTS.md` line 108).

## Artifacts and notes

The load-bearing facts pinned during research:

- The `{exc}`-interpolating boundaries and their current strings: the six
  draft-read tails routed through `_draft_read_error` — `novel_state.py:156`,
  `_recount.py:93`, `_wordcount.py:99`, `_novel_done.py:92`,
  `_desloppify.py:210`, `_compile.py:141` and `:211`; the view-derivation
  boundary `_state_mutators.py:146` routed through `_state_input_error`'s
  present-but-corrupt arm (Decision D7, respecting 6.3.1 D8); and the
  `_compile.py:150` `cannot write {_COMPILED_REL}: {exc}` write-fault tail
  scoped **out** (Decision D6). `check_compiled` (`_compile.py:211`) has no
  `root` local and passes `working_dir()` (advisory A2); `_state_mutators.py`
  imports the accessors aliased as `_working_dir`/`_state_path` (advisory A1).
- The exit-3 mapping: `runner.py` catches `StateInputError` and exits
  `ExitCode.STATE_ERROR`, emitting `list(exc.messages)`.
- The shared vocabulary tuple and the sibling formatter both live in
  `novel_ralph_skill/commands/_state_load.py` (`STATE_INPUT_ERRORS`,
  `_state_input_error`), re-exported through `novel_state`.
- An absent `draft.md` is benign (counted `0`) and never reaches these arms
  (`novel_ralph_skill/state/wordcount.py` lines 103-105), so only the
  present-but-faulted message text changes.
- The matrices carry only the missing-`working/` `_STATE_ARM`
  (`tests/test_command_surface_matrix.py:207`,
  `tests/test_console_scripts_error_arms_e2e.py:140`), so the draft-read proof
  is a new suite, not a matrix edit.
- The locked cuprum 0.1.0 surface (verified in the project venv):
  `SafeCmd.run_sync(*, capture=True, echo=False, context=ExecutionContext)`;
  this plan touches no cuprum API.

## Interfaces and dependencies

No new external dependency. The one new internal symbol, in
`novel_ralph_skill/commands/_state_load.py`:

```python
def _draft_read_error(reported_dir: pathlib.Path, exc: Exception) -> StateInputError:
    """Build the actionable exit-3 StateInputError for a present-but-faulted
    *draft artefact* under ``working/`` (a corrupt or unreadable ``draft.md`` or
    ``compiled.md``). It names ``reported_dir`` (the ``working/`` tree) and
    advises inspect/repair; it never advises ``novel state init`` (the tree
    exists). It does **not** serve the structurally-incomplete ``state.toml``
    fault — that is a state-document fault routed through ``_state_input_error``'s
    present-but-corrupt arm (Decision D7)."""
```

It is re-exported through `novel_ralph_skill/commands/novel_state.py` exactly as
`_state_input_error` is. Each of the **six draft-read** boundaries calls it
from its `except STATE_INPUT_ERRORS as exc:` arm via
`raise _draft_read_error(dir, exc)`. The view-derivation boundary instead reuses
`_state_input_error(state_path(), exc)` (Decision D7), and the `_compile`
write-fault tail keeps its own write message (Decision D6). `StateInputError`,
`STATE_INPUT_ERRORS`, `working_dir`, `state_path`, and every command body keep
their current public shapes. The later roadmap task 7.3.3 will route its
consolidated draft-read *wrapper* through this same formatter, so the two share
one home.

## Coordination with task 7.3.3

This plan delivers the **formatter** (message quality). Task 7.3.3 later
delivers the **wrapper** (the `try/except STATE_INPUT_ERRORS` catch-idiom DRY),
promoting one `read_drafts_or_state_error(working_dir, manifest)` helper that
the `wordcount`, `recount`, and `desloppify` tails delegate to. The roadmap
pins them to "share one home": both land in the `_state_load` leaf module. To
keep that coordination clean, this plan does **not** consolidate the wrapper —
it only swaps the message string each tail raises — so 7.3.3 can lift the
wrapper without re-pinning the formatter. If, while routing the boundaries, the
implementer is tempted to also collapse the wrapper, stop: that is 7.3.3's
scope (a separate atomic refactor per `AGENTS.md` lines 137-139), and doing it
here would breach the coordination the roadmap records.
