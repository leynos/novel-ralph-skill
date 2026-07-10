# Make state-input (exit-3) error messages actionable across every command

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT

## Purpose / big picture

Today, when an agent runs any `novel` command from the wrong directory — one
with no `working/` tree — the exit-3 envelope's `messages` array carries a raw
operating-system error:
`cannot load working/state.toml: [Errno 2] No such file or directory: 'working/state.toml'`.
A dogfooding agent reads that as noise, not as an instruction, and the harness
saw a real silent-failure incident because of it (roadmap §6.3 preamble). This
change replaces that raw text with an actionable message that names where the
command looked and what to do next — for the missing case:

```text
no novel working/ found in <cwd>; run from the novel root, or run 'novel state init' to create one
```

After this change, a human or agent can run, for example, `novel state check`
from `/tmp` (a directory with no `working/`), see exit code 3, and read a
message that tells them precisely how to recover, with no `Errno`, no
file-path-as-noise, and no traceback. The same actionable message appears for
**every** command — readers, checkers, and mutators alike — because both of the
two code paths that produce the message are routed through one shared helper,
so they can never drift apart (the precise inconsistency roadmap §6.3 exists to
close).

You can observe success by running the behavioural suite this plan adds: it
drives one command of each class (a mutator, a checker, and a reader) from a
`working/`-less directory and asserts exit 3 plus the actionable, cwd-naming,
remedy-bearing message with no raw `Errno`/traceback text — proving both
boundaries emit the **identical** message.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The exit-code contract is fixed: a missing or unparseable `working/state.toml`
  is the exit-3 state-or-input channel, never the benign exit 1 (design §3.2,
  lines 203-233; `adr-003-shared-interface-contract.md`). This plan changes
  only the **message text**, never the code path's exit code or the
  `StateInputError`-to-exit-3 mapping in `novel_ralph_skill/contract/runner.py`.
- There must remain exactly **one** actionable-message helper. The two existing
  producers — `_load_or_state_error` in
  `novel_ralph_skill/commands/novel_state.py` (wrapping `load_state`/`tomllib`,
  used by the reader/checker/state verbs) and `_load_document_or_state_error` in
  `novel_ralph_skill/commands/_state_mutators.py` (wrapping `load_document`/
  `tomlkit`, used by the mutators) — MUST route through that one helper.
  Re-introducing two independent message strings is forbidden; it is the drift
  the task exists to prevent.
- The shared helper's home must not create an import cycle. `_state_mutators`
  already imports from `novel_state` one-way (`_state_mutators.py` lines 35-43;
  `novel_state` imports `_state_mutators` only lazily inside a function body,
  `novel_state.py` line 346). Therefore the shared helper lives in
  `novel_state.py` alongside the existing `STATE_INPUT_ERRORS`, `working_dir`,
  and `state_path` accessors, and `_state_mutators` imports it. Do not place it
  anywhere that reverses that import direction.
- Commands must not shell out: the deterministic spine invokes no external
  process for its core logic, so cuprum is used only in the installed-binary
  end-to-end tests, never in production command code (design §4, line 276-277).
  Production changes in this plan add **no** dependency and touch **no** cuprum
  API.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, commit
  messages, and the message text itself (`AGENTS.md` line 18; `en-gb-oxendict`
  skill). The user-facing message must read as British English.
- The `STATE_INPUT_ERRORS` vocabulary tuple (`novel_state.py` lines 130-136) is
  the single home for "what counts as a state-input error" and is reused by the
  corpus test (audit:2.1.2 finding 4). Do not fork or narrow it; the helper
  keeps catching the same tuple.
- Documentation is source of truth: the developers' guide note that currently
  says the matrix "redacts the `messages` field … carrying the errno text"
  (`docs/developers-guide.md` lines 118-122) becomes stale once the message is
  no longer errno text, and must be refreshed (Work item 5).

## Tolerances (exception triggers)

- Scope: if the production change to route both boundaries through one helper
  requires editing more than 6 source files (net) or more than ~150 lines, stop
  and escalate — the design points at exactly two producer call-sites plus one
  helper.
- Interface: the shared helper is a new internal (underscore-prefixed) symbol;
  if
  satisfying the task appears to require changing a **public** signature
  (`StateInputError`, `CommandOutcome`, `run`, or any command body's public
  surface), stop and escalate.
- Dependencies: if any work item appears to need a new external dependency, stop
  and escalate. None should.
- Message wording: if the missing-vs-unparseable branch (Decision D2) cannot be
  expressed without catching a broader exception set than `STATE_INPUT_ERRORS`,
  stop and escalate rather than widening the tuple.
- Iterations: if `make all` still fails after 3 focused attempts on any work
  item, stop and escalate with the failing output.
- Snapshot churn: if updating snapshots touches more than the two
  message-prefix constants this plan names, stop and inspect — an unexpected
  snapshot change signals a contract shift the plan did not intend.

## Risks

- Risk: a command passes a path that is not literally `working/state.toml`
  (e.g. `working_dir / "state.toml"` in `_desloppify.py` line 199 and
  `_wordcount.py` line 131, versus `state_path()` elsewhere), so the helper
  must derive its "directory" and "cwd" robustly from the supplied `path`
  rather than assuming a fixed string. Severity: medium. Likelihood: medium.
  Mitigation: the helper derives the reported directory from `path.parent` and
  the cwd from `pathlib.Path.cwd()`; Work item 1's unit test pins the message
  for both call shapes.
- Risk: the message must distinguish a *missing* `working/`/`state.toml` (where
  `novel state init` is the right remedy) from a *present-but-unparseable*
  `state.toml` (where `init` is the wrong advice — it would not repair a
  corrupt file). A single message for both would be misleading. Severity:
  medium. Likelihood: high. Mitigation: Decision D2 — branch on existence.
  `load_state`/`load_document` raise `FileNotFoundError` (an `OSError`) when
  the file is absent and `TOMLDecodeError`/`KeyError`/`ValueError`/`TypeError`
  when present but bad (verified: `novel_ralph_skill/state/parse.py` line 246
  opens the path, so a missing file raises before parsing). The helper inspects
  the path/parent on disk to choose the missing-remedy message versus the
  corrupt-file message. Both drop raw `Errno`/traceback text.
- Risk: existing tests assert the old `cannot load …` text and will fail.
  Severity: low. Likelihood: high (expected). Mitigation: these are the
  red-to-green proof. The known assertions are `tests/test_compile_unit.py`
  line 278, `tests/test_desloppify_sourcing.py` line 128,
  `tests/test_command_surface_matrix.py` line 220
  (`message_prefix="cannot load working/state.toml"`), and
  `tests/test_console_scripts_error_arms_e2e.py` line 138 (same prefix). Work
  items 2-4 update each to the new actionable prefix. A repository-wide grep for
  `cannot load` in `tests/` (and in `novel_ralph_skill/`) gates that none is
  missed.
- Risk: the installed-binary error-arm e2e relies on the **locked** cuprum
  0.1.0 surface, which differs from the unreleased source tree. Severity: low.
  Likelihood: low (no new cuprum call is added). Mitigation: Work item 4 reuses
  the existing fixtures unchanged; only the asserted `message_prefix` constant
  changes. The locked surface is pinned in the Decision Log (D5).

## Progress

- [x] Work item 1 — shared actionable-message helper. Added `_state_input_error`
      as the single source of truth and routed `_load_or_state_error` through it.
      Extracted the load boundary into the new dependency-free `_state_load` leaf
      module (re-exported by `novel_state`) to stay within the 400-line cap; see
      Decision D6. Unit tests cover both call shapes and both remedy arms; no
      property test was warranted (Decision D7).
- [x] Work item 2 — routed `_load_document_or_state_error` through the shared
      helper and proved byte-for-byte parity with the reader boundary
      (`tests/test_state_input_message_parity.py`).
- [x] Work item 3 — refreshed the in-process matrix `_STATE_ARM` prefix and added
      the cross-class pytest-bdd scenario (mutator/checker/reader) proving exit
      3, identical actionable prose, and no `Errno` or traceback.
- [x] Work item 4 — refreshed the installed-binary error-arm e2e `_STATE_ARM`
      prefix; no cuprum API change.
- [x] Work item 5 — refreshed the developers' guide note so it no longer claims
      the redacted `messages` field carries "the errno text".

## Surprises & discoveries

- Observation: the **locked, installed** cuprum (0.1.0) and the cuprum **source
  working tree** at `/data/leynos/Projects/cuprum` have diverged. Evidence:
  `inspect.signature(SafeCmd.run_sync)` in the worktree prints

  ```text
  (self, *, capture: bool = True, echo: bool = False, context: ExecutionContext | None = None)
  ```

  whereas the source tree's `cuprum/sh.py` defines
  `run_sync(self, *, output, timeout, context, stdin)`. The installed wheel is
  the contract the tests run against. Impact: any cuprum reference in this plan
  (Work item 4) is pinned to the **installed** 0.1.0 surface, not the source
  tree. This plan adds no new cuprum call regardless.
- Observation: no syrupy snapshot stores the raw `cannot load` text.
  Evidence: `grep -rln "cannot load\|No such file\|Errno" tests/__snapshots__/`
  returns nothing; the matrix and error-arm suites redact `messages` and assert
  by prefix instead. Impact: snapshot churn is limited to the prefix constants
  in the two suites, not to stored envelope bodies — keeping Work items 3-4
  small.

## Decision log

- Decision: the shared helper lives in
  `novel_ralph_skill/commands/novel_state.py` and is imported by
  `_state_mutators.py`. Rationale: `_state_mutators` already imports one-way
  from `novel_state` (lines 35-43); `novel_state` imports `_state_mutators`
  only lazily inside a function (line 346). Placing the helper in `novel_state`
  adds no new module- level import edge and sits beside the sibling shared
  accessors (`STATE_INPUT_ERRORS`, `working_dir`, `state_path`). Date/Author:
  2026-06-26, planner.
- Decision (D2): the message branches on existence — a missing `working/` or
  missing `state.toml` yields the `init`-remedy message; a present-but-
  unparseable `state.toml` yields a distinct "unreadable/corrupt" message that
  does **not** advise `init`. Rationale: `novel state init` repairs a missing
  tree but not a corrupt file; one message for both would mislead. Verified that
  `load_state` opens the path before parsing (`parse.py` line 246), so absence
  raises `FileNotFoundError` (an `OSError`) distinctly from a parse fault.
  Date/Author: 2026-06-26, planner.
- Decision (D3): the helper takes the same `path: pathlib.Path` the two
  producers already receive, derives the reported directory from `path.parent`,
  and names the cwd via `pathlib.Path.cwd()`. Rationale: callers pass either
  `state_path()` or `working_dir / "state.toml"`; deriving from the argument
  keeps one signature for both. The cwd is what the remedy ("run from the novel
  root") refers to, so it must be reported explicitly. Date/Author: 2026-06-26,
  planner.
- Decision (D4): the helper keeps catching the existing
  `STATE_INPUT_ERRORS` tuple unchanged and raises `StateInputError` with the
  new message; it does not widen or fork the tuple. Rationale: constraint —
  `STATE_INPUT_ERRORS` is the single state-input-error vocabulary (audit:2.1.2
  finding 4). The branch (D2) is driven by on-disk existence checks, not by
  widening the caught set. Date/Author: 2026-06-26, planner.
- Decision (D5): the installed-binary error-arm e2e (Work item 4) is pinned to
  the **locked cuprum 0.1.0** surface already used by the existing fixtures:
  `ProgramCatalogue(projects=(ProjectSettings(name, programs, …),))`,
  `Program(str_path)`, `sh.make(program, catalogue=…)` → `builder(*argv)` →
  `SafeCmd`, and
  `SafeCmd.run_sync(*, capture=True, context=ExecutionContext(cwd=…))`
  returning a `CommandResult` with `exit_code`/`stdout`/`stderr`. Verified in
  the worktree venv (see Surprises). No new cuprum call is introduced; only the
  asserted message prefix changes. Date/Author: 2026-06-26, planner.
- Decision (D6, deviation): adding the ~50-line shared helper plus its expanded
  docstrings pushed `novel_state.py` from 399 to 451 lines, over the 400-line cap
  (AGENTS.md). Rather than gut the load-bearing rationale from the docstrings, the
  load boundary and its accessors (`WORKING_DIR_NAME`, `working_dir`, `state_path`,
  `STATE_INPUT_ERRORS`, `_state_input_error`, `_load_or_state_error`) were extracted
  into a new dependency-free leaf module `novel_ralph_skill/commands/_state_load.py`
  and re-exported from `novel_state` via `__all__`. This honours the Constraint
  "the helper's home must not create an import cycle": `_state_load` imports only
  from `state` and `contract.runner`, never from `novel_state`, so the
  `_state_mutators` → `novel_state` direction is preserved and every existing
  importer keeps importing from `novel_state` unchanged. It mirrors the prior
  `_state_mutators` carve-out, which was itself split off for the same cap. Net
  source files touched: 3 production + 6 test/doc, within the Tolerance bound of
  6 source files. Date/Author: 2026-06-26, implementer.
- Decision (D7): no Hypothesis property test was added. The example-based unit
  tests already pin both call shapes and both remedy arms, and the input domain
  (a `pathlib.Path` plus a caught `STATE_INPUT_ERRORS` member) is too narrow to
  earn a property test that would only restate the unit logic (AGENTS.md line 162;
  `python-verification`). Date/Author: 2026-06-26, implementer.
- Decision (D8): `_state_view_or_state_error` in `_state_mutators.py` is **not**
  routed through the shared `_state_input_error` helper and is not a producer of
  the `cannot load …`/`unreadable or corrupt` message. Rationale: it reports a
  *parsed-but-structurally-incomplete* document — a `state.toml` that parsed as
  TOML but failed `document_to_state` (a missing table or key, or a bad phase
  string) — not a failed *load*. Its remedy ("the state is structurally
  incomplete") differs from the load boundary's ("run from the novel root" or
  "inspect and repair"), so sharing the load helper would mislead. It is an
  out-of-scope, non-producer boundary for §6.3.1, deliberately left distinct. A
  future reviewer must not mistake it for a third producer of the load message,
  route it through `_state_input_error`, or flag a false drift. This records the
  entry Work item 2 step 3 directed; the code already cites "Decision Log D8".
  Date/Author: 2026-06-26, implementer (addendum 6.3.1.1).

## Outcomes & retrospective

Delivered. The shipped missing-case message matches the Purpose verbatim:
`no novel working/ found in <cwd>; run from the novel root, or run 'novel state
init' to create one`. The present-but-corrupt arm emits a distinct repair message
(`<path> is unreadable or corrupt; inspect and repair it, or restore it from a
known-good copy`) that deliberately omits the `init` remedy (Decision D2). The
cross-class pytest-bdd scenario proves a mutator, a checker, and a reader emit
byte-for-byte identical actionable prose with no `Errno`/traceback, and the
`grep -rn "cannot load"` sweep over `novel_ralph_skill/` and `tests/` returns
nothing. The one deviation from the plan as drafted is the `_state_load` module
extraction (Decision D6), forced by the 400-line cap; the helper still lives on
the correct side of the import boundary. No wording was changed during review
beyond the corrupt-arm phrasing settled in the unit test.

## Context and orientation

The `novel` console-script is a single multiplexer over five operations: a
`state` subgroup (`init`, `check`, `set-cursor`, `advance-phase`, `recount`,
`reconcile`, `set-chapters`, and the gate-drafting setters) plus four leaf verbs
(`done`, `compile`, `desloppify`, `wordcount`) (design §4). Every command
emits a shared JSON envelope; a failure populates the envelope's `messages`
array from a raised exception. A missing or unparseable `working/state.toml`
raises `StateInputError`, which `novel_ralph_skill/contract/runner.py` (lines
233-239) maps to exit code 3, emitting `list(exc.messages)`.

There are two — and only two — code paths that build that exit-3 message for a
failed state load:

1. `_load_or_state_error(path)` in
   `novel_ralph_skill/commands/novel_state.py` (lines 139-167). It wraps
   `load_state` (which uses `tomllib`), catches `STATE_INPUT_ERRORS` (lines
   130-136), and raises `StateInputError(f"cannot load {path}: {exc}")`. Used
   by the **readers and checkers and the `state check` path**: `_wordcount.py`
   (line 131), `_novel_done.py` (line 88), `_compile.py` (lines 135, 206),
   `_desloppify.py` (line 199), and `novel_state._check` (line 243).

2. `_load_document_or_state_error(path)` in
   `novel_ralph_skill/commands/_state_mutators.py` (lines 78-106). It wraps
   `load_document` (which uses `tomlkit`), catches the same
   `STATE_INPUT_ERRORS`, and raises the identical
   `StateInputError(f"cannot load {path}: {exc}")`. Used by the **mutators**:
   `_recount.py` (line 222), `_reconcile.py` (lines 114, 288),
   `_set_chapters.py` (line 280), and `_gate_drafting_mutators.py` (lines 169,
   243, 279, 328).

Both presently build the same string independently, so a change to one would
silently diverge from the other — the drift roadmap §6.3 exists to prevent.

Key supporting symbols, all in `novel_state.py`: `working_dir()` (line 102)
returns the fixed cwd-relative `pathlib.Path("working")`; `state_path()` (line
113) returns `working_dir() / "state.toml"`; `STATE_INPUT_ERRORS` (line 130) is
the shared "what counts as a state-input error" tuple (`OSError`,
`tomllib.TOMLDecodeError`, `KeyError`, `ValueError`, `TypeError`).

Test orientation. The cross-command contract is pinned in
`tests/test_command_surface_matrix.py` (the in-process matrix; its `_STATE_ARM`
at line 215 sets `message_prefix="cannot load working/state.toml"`) and
`tests/test_console_scripts_error_arms_e2e.py` (the installed-binary matrix; its
`_STATE_ARM` at line 133 carries the same prefix; it drives the real wheel via
cuprum). Direct unit assertions on the old text live at
`tests/test_compile_unit.py` line 278 and `tests/test_desloppify_sourcing.py`
line 128. Behavioural (`pytest-bdd`) suites live under `tests/features/` with
steps under `tests/steps/`; snapshot suites use `syrupy` and redact `messages`.

Relevant design and standards sections to read before starting: design §3.2
(exit codes), §3.4 (atomic writes / state-input channel),
`adr-003-shared-interface-contract.md` (the shared envelope and message
contract), `docs/scripting-standards.md` lines 603-605 and 678 ("human-friendly
error messages should highlight remediation steps"; production code presents
friendly messages), and `AGENTS.md` (quality gates and en-GB Oxford spelling).

## Plan of work

The change is small and surgical: introduce one shared actionable-message
helper, route both producers through it, then refresh every test and document
that pinned the old text. Stages are ordered so the helper and its proof land
first (red→green), then each consumer and its documentation follow.

### Work item 1 — Shared actionable-message helper (the single source of truth)

Implements: design §3.2 (exit-3 channel), §3.4; `adr-003`
(`docs/adr-003-shared-interface-contract.md`); `scripting-standards.md` lines
603-605, 678. Closes the roadmap §6.3.1 requirement that both producers "route
through one shared actionable-message helper so they cannot diverge".

Docs to read: design §3.2 and §3.4; `adr-003-shared-interface-contract.md`;
`scripting-standards.md` lines 600-688; `AGENTS.md` lines 18, 141-172.

Skills to load: `python-router` (route to the smaller skills it picks);
`python-errors-and-logging` (exception design, `raise … from …`, narrow
`except`, `N818`/`TRY`/`EM` rules — the helper raises `StateInputError`);
`en-gb-oxendict` (the user-facing message wording); `leta` (navigate
`novel_state.py`, `_state_mutators.py`, and the consumers);
`python-verification` then `hypothesis` (decide whether a property test is
warranted for the message — see Tests below).

What to do:

1. In `novel_ralph_skill/commands/novel_state.py`, add a module-private helper —
   proposed name
   `_state_input_error(path: pathlib.Path, exc: Exception) -> StateInputError` —
   that builds the actionable `StateInputError` from the failed-load context.
   Per Decision D2 it inspects existence:
   - If the `working/` directory (derived as `path.parent`) or the `state.toml`
     file does not exist on disk, the message is:
     `no novel working/ found in {cwd}; run from the novel root, or run 'novel
     state init' to create one`, where `{cwd}` is `pathlib.Path.cwd()`.
   - Otherwise (the file exists but failed to parse or is structurally
     incomplete), the message names the path and that it is unreadable/corrupt
     and advises inspection/repair, **without** suggesting `init`. It must carry
     no raw `Errno` text and no traceback. (Final wording to be settled in the
     unit test as the executable specification; keep both arms en-GB.)
   - In both arms, raise `StateInputError(message) from exc` so the chained
     cause is preserved for debugging while `exc.messages` carries only the
     actionable prose (the envelope emits `messages`, never the chained repr).
2. Rewrite `_load_or_state_error` (lines 163-167) so its
   `except STATE_INPUT_ERRORS as exc:` arm delegates to the new helper:
   `raise _state_input_error(path, exc)`. Keep the caught tuple unchanged (D4).
3. Update the `_load_or_state_error` docstring to describe the actionable
   message and point at the shared helper, in en-GB.

Tests this work item must add or update (`AGENTS.md` lines 141-164):

- Unit (new, `tests/`): a focused test module (e.g.
  `tests/test_state_input_message_unit.py`) that calls `_state_input_error`
  (and/or drives `_load_or_state_error`) and asserts, for the **missing** case,
  that the message contains the cwd, the `working/` mention, and the
  `novel state init` remedy, and contains **no** `Errno` and **no**
  path-as-noise; and for the **unparseable** case (a `state.toml` present but
  corrupt), that the message is the distinct corrupt-file message and does
  **not** mention `init`. Cover both call shapes from Risk 1 (path as
  `state_path()` and as `working_dir / "state.toml"`).
- Property (consider via `python-verification`; add with `hypothesis` only if it
  earns its place — `AGENTS.md` line 162 gates property tests to "broad input
  domains"): a property that for any cwd path and any caught
  `STATE_INPUT_ERRORS` member, the produced message never contains the substring
  `Errno` and never contains a `Traceback` marker, and always names a remedy.
  If the input domain proves too narrow to justify Hypothesis, record that in
  the Decision Log and keep the example-based unit test instead — do not add a
  property test that only restates the unit logic.
- Update the two direct unit assertions on the old text:
  `tests/test_compile_unit.py` line 278 (`match="cannot load"`) and
  `tests/test_desloppify_sourcing.py` line 128
  (`match=r"cannot load .*state\.toml"`) to the new actionable prefix/pattern.

Validation: `make all` (runs `build check-fmt lint typecheck test`). The new
unit test fails before the helper exists and passes after.

### Work item 2 — Route the mutator boundary through the shared helper

Implements: roadmap §6.3.1 ("BOTH boundaries emit the identical actionable
message"); design §3.2; `adr-003`.

Docs to read: same as Work item 1, plus `_state_mutators.py` lines 1-140 (the
module docstring's exit-3 contract note and the existing
`_load_document_or_state_error`).

Skills to load: `python-router` → `python-errors-and-logging`; `leta` (confirm
the import direction and every mutator call-site); `en-gb-oxendict`.

What to do:

1. In `novel_ralph_skill/commands/_state_mutators.py`, import the shared helper
   from `novel_state` (alongside the existing `STATE_INPUT_ERRORS`/`working_dir`
   / `state_path` imports at lines 35-43; respect the `__all__` re-export
   pattern if the symbol needs forwarding). Rewrite
   `_load_document_or_state_error`'s `except STATE_INPUT_ERRORS as exc:` arm
   (lines 104-106) to delegate: `raise _state_input_error(path, exc)`. Keep the
   caught tuple unchanged.
2. Update the `_load_document_or_state_error` docstring to state that it shares
   the message helper with the reader boundary so the two cannot drift, in
   en-GB.
3. Leave `_state_view_or_state_error` (the "state is structurally incomplete"
   message at lines 136-140) as-is: it reports a *parsed-but-incoherent
   document*, a distinct condition from a *failed load*, and is out of scope
   for §6.3.1 (which targets the load boundary). Note this boundary in the
   Decision Log so a reviewer does not mistake it for a third producer.

Tests this work item must add or update:

- Unit (new or extend Work item 1's module): assert that
  `_load_document_or_state_error`, driven from a `working/`-less directory,
  raises a `StateInputError` whose message is **byte-for-byte identical** to
  the one `_load_or_state_error` raises for the same cwd — the explicit
  anti-drift proof. Use a shared expected-message constant or compare the two
  helpers' outputs directly so the test fails if either boundary diverges.

Validation: `make all`. The parity unit test fails if the two boundaries' text
differs.

### Work item 3 — Cross-class behavioural proof (mutator, checker, reader)

Implements: roadmap §6.3.1 Success criterion ("a behavioural test drives a
command from a directory with no `working/` … for at least one command of each
class (mutator, checker, reader) — proving BOTH boundaries emit the identical
actionable message"); design §3.2; `adr-003`.

Docs to read: design §3.2; `adr-003`; `AGENTS.md` lines 143-164 (pytest-bdd for
behavioural tests); the in-process matrix docstring in
`tests/test_command_surface_matrix.py` (its `Carried gaps` note) before
extending it.

Skills to load: `python-router` → `python-testing` (fixture scopes,
parametrization, the unit/behavioural boundary); `leta`; `en-gb-oxendict` (the
feature prose, if a `.feature` file is added).

What to do:

1. Update the in-process matrix's `_STATE_ARM.message_prefix` in
   `tests/test_command_surface_matrix.py` (line 220) from
   `"cannot load working/state.toml"` to the new actionable prefix (e.g. the
   stable leading substring `no novel working/ found in`). This already crosses
   every read command, satisfying the checker/reader classes.
2. Add an explicit **mutator** state-arm proof. The matrix's `_READ_REGISTRY`
   covers readers/checkers only; the success criterion names a mutator
   explicitly. Add a behavioural scenario (preferred: a `pytest-bdd` `.feature`
   - steps under `tests/features/`/`tests/steps/`, following the existing
   mutator BDD suites such as `tests/features/recount.feature` and
   `tests/steps/recount_steps.py`) that drives one mutator (e.g.
   `novel state recount`) from a `working/`-less directory and asserts exit 3
   with the actionable, cwd-naming, remedy-bearing message and no `Errno`.
   Cross it with a reader (e.g. `novel wordcount`) and a checker (e.g.
   `novel state check` or `novel done`) so all three classes are proven in one
   suite, and assert the message is identical across them.
   - If extending the existing matrix parametrization is cleaner than a new
     `.feature`, that is acceptable provided the mutator class is genuinely
     exercised; record the choice in the Decision Log. Do not claim the
     criterion met if only readers/checkers run.

Tests this work item must add or update:

- Behavioural (`pytest-bdd`): the cross-class scenario above (mutator, checker,
  reader), asserting exit 3, the actionable message, identical text across
  classes, and absence of `Errno`/traceback.
- Matrix: the updated `_STATE_ARM` prefix constant.
- Snapshot: none expected — the matrix redacts `messages`. If a snapshot does
  churn, treat per the Tolerances ("Snapshot churn") and re-accept only a
  reviewed change with `--snapshot-update`, confirming the redaction still
  holds.

Validation: `make all`. The cross-class scenario fails before Work items 1-2
land and passes after.

### Work item 4 — Installed-binary error-arm e2e refresh

Implements: roadmap §6.3.1 (the message holds for the real installed command,
not just in-process); `adr-006-console-scripts-e2e-posix-policy.md`
(POSIX-only); design §4 (single console-script).

Docs to read: `adr-006-console-scripts-e2e-posix-policy.md`; the e2e fixture
`tests/installed_binary_fixtures.py` and
`tests/test_console_scripts_error_arms_e2e.py`; this plan's Decision D5 (the
locked cuprum 0.1.0 surface).

Skills to load: `python-router` → `python-testing`; `leta`; `en-gb-oxendict`.
Do **not** consult the cuprum source working tree for the API — it has diverged
from the locked wheel (see Surprises); rely on D5 and the existing fixtures.

What to do:

1. Update `_STATE_ARM.message_prefix` in
   `tests/test_console_scripts_error_arms_e2e.py` (line 138) from
   `"cannot load working/state.toml"` to the same actionable prefix used in
   Work item 3. The fixture, catalogue construction, `sh.make`,
   `ExecutionContext`, and `run_sync` calls are unchanged — they already use
   the locked cuprum 0.1.0 surface (D5). No new cuprum API is introduced.

Tests this work item must add or update:

- e2e: the existing installed error-arm matrix, with the refreshed prefix
  constant; it continues to drive the real wheel via cuprum on POSIX.

Validation: `make all`. On POSIX the installed e2e exercises the actual binary
and asserts the actionable message; per ADR-006 it is skipped off-POSIX.

### Work item 5 — Refresh the developers' guide note

Implements: AGENTS.md docs-currency rule (line 47, keep `docs/` reflecting the
latest state); roadmap §6.3 self-documenting intent.

Docs to read: `docs/developers-guide.md` lines 113-133 (the matrix note);
`AGENTS.md` lines 47, 96-98, 169-172.

Skills to load: `en-gb-oxendict`; `leta` (to locate the exact lines).

What to do:

1. Edit `docs/developers-guide.md` lines 118-122 so the description of the
   redacted `messages` field no longer says it carries "the errno text". After
   this change the state-arm message is a stable actionable string (the matrix
   asserts it by prefix), and only the usage suggestion suffix remains
   genuinely command-variable. Keep the note accurate and en-GB; do not
   over-claim.

Tests / validation: documentation-only. Run `make markdownlint` and
`make nixie` on the edited Markdown (per AGENTS.md lines 96-98 and the standing
rule for Markdown changes). No Mermaid is added, but `make nixie` is run as the
standard Markdown gate. Also run `make all` to confirm nothing else regressed.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-1`.

1. Confirm the branch and a clean tree:

   ```bash
   git branch --show-current   # expect: roadmap-6-3-1
   git status --short          # expect: empty
   ```

2. Before each work item, read the cited docs and load the cited skills. After
   each work item, run the gate and commit:

   ```bash
   make all
   ```

   Expect the final line to report all of `build`, `check-fmt`, `lint`,
   `typecheck`, and `test` passing. For the documentation work item (5), also
   run:

   ```bash
   make markdownlint
   make nixie
   ```

3. Sweep for any missed old text before declaring done:

   ```bash
   grep -rn "cannot load" novel_ralph_skill/ tests/   # expect: no exit-3 message strings remain
   ```

   The only acceptable remaining matches are docstrings or comments that have
   been rewritten to describe the *new* behaviour, never a live message string.

4. Commit each work item separately with an imperative, en-GB subject (AGENTS.md
   lines 99-108), gating each commit on `make all`.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` passes (`pytest -v -n …`, plus build/lint/typecheck). The
  new
  unit test, the helper-parity unit test, the cross-class behavioural scenario,
  and the refreshed matrix/e2e arms all pass; each fails before its
  corresponding production change and passes after.
- Behaviour: running `novel state check`, `novel wordcount`, and
  `novel state recount` from a directory with no `working/` each exits 3 and
  prints an
  envelope whose `messages` contains the actionable, cwd-naming,
  `novel state init`-suggesting text, with no `Errno` and no traceback, and the
  text is identical across the three commands.
- Lint/typecheck: `make lint` and `make typecheck` pass (en-GB comments, 100%
  docstring coverage via interrogate, Ruff, Pylint, `ty`).
- Markdown (Work item 5): `make markdownlint` and `make nixie` pass.

Quality method (how we check): `make all` for every work item;
`make markdownlint` and `make nixie` for the Markdown change; the
`grep -rn "cannot load"` sweep as the anti-drift backstop.

## Idempotence and recovery

Every step is re-runnable. The production edits are pure text/exception
construction with no filesystem mutation, so re-applying a work item is safe.
Snapshot updates (if any unexpectedly arise) are recoverable via
`git checkout -- tests/__snapshots__` followed by a reviewed
`--snapshot-update`. If a commit fails the gate, fix forward and re-run
`make all`; do not commit a failing gate (AGENTS.md line 108).

## Artefacts and notes

The load-bearing facts pinned during research:

- The two producers and their identical old message:
  `novel_state.py:166` and `_state_mutators.py:105` both build
  `f"cannot load {path}: {exc}"`.
- The exit-3 mapping: `runner.py:233-239` catches `StateInputError` and exits
  `ExitCode.STATE_ERROR`, emitting `list(exc.messages)`.
- The shared vocabulary tuple: `novel_state.py:130-136` `STATE_INPUT_ERRORS`.
- The locked cuprum 0.1.0 e2e surface (verified in the worktree venv):
  `SafeCmd.run_sync(*, capture=True, echo=False, context=ExecutionContext)`,
  `ExecutionContext` carries `cwd`, `CommandResult` carries `exit_code`/`stdout`
  /`stderr`, `sh.make(program, catalogue=…)`,
  `ProgramCatalogue(projects=(ProjectSettings(name, programs, …),))`.

## Interfaces and dependencies

No new external dependency. The one new internal symbol:

In `novel_ralph_skill/commands/novel_state.py`:

```python
def _state_input_error(path: pathlib.Path, exc: Exception) -> StateInputError:
    """Build the actionable exit-3 StateInputError for a failed state load."""
```

Both producers — `_load_or_state_error` (same module) and
`_load_document_or_state_error` (in
`novel_ralph_skill/commands/_state_mutators.py`, importing the helper from
`novel_state`) — call it from their `except STATE_INPUT_ERRORS as exc:` arm via
`raise _state_input_error(path, exc)`. `StateInputError`, `STATE_INPUT_ERRORS`,
`working_dir`, and `state_path` keep their current public shapes.

## Addenda

- [x] 6.3.1.1 (from review:6.3.1; low). Record the omitted Decision Log entry that
  Work item 2 step 3 directed: `_state_view_or_state_error` in
  `_state_mutators.py` reports a *parsed-but-structurally-incomplete* document,
  not a failed load, so it is an out-of-scope, non-producer boundary for §6.3.1
  and is deliberately not routed through the shared `_state_input_error` helper.
  A future reviewer must not mistake it for a third producer of the
  `cannot load …` message and over-refactor it or flag a false drift. Pure
  documentation; no code change. Lightweight addendum pass.
- [x] 6.3.1.2 (from review:6.3.1; low). Add a corrupt-arm parity assertion to
  `test_state_input_message_parity.py`, which currently pins reader/mutator
  parity only for the missing-`working/` arm. The present-but-corrupt
  `state.toml` message is byte-identical across the `tomllib` (reader) and
  `tomlkit` (mutator) boundaries today but no test pins it, so a one-sided
  re-wording would silently reintroduce drift — the exact failure §6.3 exists
  to prevent. Lightweight addendum pass.
