# Post-merge audit: roadmap task 6.2.8

Audit of the codebase after roadmap task 6.2.8 ("extend the command-surface
matrix to a minimal error-mode slice", commit `a7eaf1e`) merged to `main`. The
task closed `audit:6.2.1` Finding 5: the combinatorial `command x output-mode x
phase` matrix never crossed the runner's command-agnostic exit-2
(`CycloptsError`) and exit-3 (`StateInputError`) diagnostic arms — the envelopes
that stamp `--human` before any command body runs. Task 6.2.8 added an
`_ErrorArm`-keyed slice (`_USAGE_ARM`, `_STATE_ARM`) crossing both arms with
every read command in both output modes, snapshotting the redacted machine
envelope and asserting human-mode presence, plus a developers'-guide paragraph
describing the slice.

The new work is correct, accurately documented, and properly paired with
semantic assertions (so no behaviour is snapshot-only, per AGENTS.md). The line
citations in the new docstrings and the developers' guide check out
(`runner.py:225-239` is the two-arm `try/except`; design §3.2 opens at line 203).
The findings below are low-severity hygiene observations on the new slice, plus
one pre-existing duplication theme that this task did **not** widen but that the
slice newly leans on. None block the merge.

Sources relied on: `docs/issues/audit-6.2.1.md` (Finding 5, the finding this task
closes); `docs/issues/audit-6.2.6.md` and `docs/issues/audit-6.1.1.md` (the
prior duplication-by-copy-paste audits); `docs/roadmap.md` (tasks 6.2.8, 7.16.3,
7.16.4); `docs/developers-guide.md` ("command-surface matrix"); `docs/novel-
ralph-harness-design.md` (§3.2 exit codes, §9 carried gaps); `docs/adr-003-
shared-interface-contract.md` (§3.1 `--human` stamp, Table 2 exit-code table);
and `AGENTS.md` (snapshot-pairing, en-GB Oxford spelling). Code navigated with
`leta`/`grep`; history traced with `git show` over commit `a7eaf1e`. Skills
consulted: `python-router`, which routed to `python-testing` (snapshot and
parametrize discipline) and `python-errors-and-logging` (the `raise … from …`
re-raise idiom).

## Finding 1: The ten error-arm machine snapshots are near-degenerate

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:420-451`
  (`test_error_arm_machine_envelope`) and the ten
  `test_error_arm_machine_envelope[*]` blocks in
  `tests/__snapshots__/test_command_surface_matrix.ambr`.

The error-arm snapshot redacts the only command- and platform-variable field
(`messages` → `["<redacted>"]`), so each of the ten stored snapshots (five
commands × two arms) differs from the others by exactly one datum: the `command`
string. That datum is already asserted in code (`assert envelope["command"] ==
command.name`), and the skeleton (`ok: false`, empty `result`, `working_dir:
"working"`, `schema_version: 1`) is identical across all ten and already asserted
field-by-field in the test body. The snapshot therefore re-pins a skeleton the
code already checks while contributing no signal the in-code assertions do not —
the redaction has collapsed the one cell the snapshot was meant to add. This is
the inverse of the snapshot-pairing intent: here the *semantic* assertions carry
all the contract and the snapshot is the redundant half.

- **Proposed fix:** Either (a) drop the snapshot from
  `test_error_arm_machine_envelope` and keep the field-by-field assertions as the
  sole oracle (the skeleton is small and fully named, so a snapshot buys little),
  or (b) replace the ten near-identical snapshots with a single parametrized
  assertion against an in-code expected skeleton dict templated on `command.name`
  and `working_dir`, asserting the redacted envelope equals it. Both remove nine
  redundant `.ambr` blocks while preserving the exact contract.

## Finding 2: State-arm prefix couples the matrix to the shared loader's wording

- **Category:** inconsistency
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:211-217` (`_STATE_ARM`,
  `message_prefix="cannot load working/state.toml"`) and
  `tests/test_command_surface_matrix.py:448`
  (`assert messages[0].startswith(arm.message_prefix)`).

The state arm asserts that **all five** read commands emit a message beginning
`cannot load working/state.toml` when `working/` is absent. That holds only
because every read body funnels its first disk touch through
`novel_state._load_or_state_error`, whose message is `f"cannot load {path}:
{exc}"` (`novel_state.py:155`) — so the absent-`working/` fault is raised there
before any command reaches its own `cannot read chapter drafts` /
`cannot evaluate the done predicate` wrapper. The matrix docstring explains *why*
the prefix is command-body-owned but does not state that this five-way uniformity
is a load-ordering invariant: if a future command grew a pre-state disk read (or
`_load_or_state_error` were inlined per command, as the open task 7.16.4
contemplates), the prefix would diverge and this assertion would fail for reasons
unrelated to the contract under test. The coupling is correct today but
undocumented as a precondition.

- **Proposed fix:** Add one sentence to the `_STATE_ARM` docstring (or the module
  docstring's drive-seam note) recording that the uniform `cannot load
  working/state.toml` prefix depends on every read body resolving
  `working/state.toml` through the shared `_load_or_state_error` *before* any
  draft read, so the invariant is named rather than implicit. No code change.

## Finding 3: The two human-presence assertions are duplicated verbatim

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:356-377`
  (`test_human_mode_presence_matrix`) and
  `tests/test_command_surface_matrix.py:454-470`
  (`test_error_arm_human_presence`).

Both human-presence tests share an identical two-line oracle — `assert
rendered.strip(), "human mode must render a non-empty report"` followed by
`assert command.name in rendered` — over a different cell source (phase cells
versus error cells). The duplication is small and the split is justified by the
different parametrize sources, but the shared oracle is open-coded twice rather
than factored.

- **Proposed fix:** Extract a one-line `_assert_human_presence(command, rendered)`
  helper carrying the message string and the `command.name in rendered` check, and
  have both tests call it. This keeps the "presence means non-empty *and* names
  the command" contract in one place so the two tests cannot drift.

## Finding 4: The draft-read `StateInputError` re-raise idiom remains triplicated

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_wordcount.py:98-100`,
  `novel_ralph_skill/commands/_desloppify.py:205-207`,
  `novel_ralph_skill/commands/_compile.py:140-142` (and `:210-212`), each open-
  coding `except STATE_INPUT_ERRORS as exc: msg = f"cannot read chapter drafts:
  {exc}"; raise StateInputError(msg) from exc`. Twelve `raise
  StateInputError(msg) from exc` sites exist across `commands/`.

This is the duplication that `audit:6.1.1` Finding 1 raised and that roadmap task
7.16.3 already tracks (consolidate the draft-read state-error wrapper). Task 6.2.8
did not add a copy, but its `_STATE_ARM` slice now *exercises* the exit-3 channel
these wrappers feed, so the slice is a fresh consumer of the un-consolidated
idiom. Worth noting because the matrix would be a natural regression guard for
the 7.16.3 consolidation: once a single `read_drafts_or_state_error` helper owns
the idiom, the matrix's exit-3 arm proves the envelope shape is unchanged.

- **Proposed fix:** No new work — task 7.16.3 already owns the consolidation. When
  7.16.3 lands, reference the command-surface matrix's `_STATE_ARM` slice as the
  envelope-shape regression guard so the refactor is proven not to alter the
  exit-3 contract. (7.16.3's named call sites are `_wordcount`, `_recount`, and
  `_desloppify`; the two `_compile` draft-read copies are a candidate to fold in
  under the same helper and could be added to that task's scope.)

## Finding 5: Docstring and developers'-guide line-number citations are fragile

(pre-existing house convention; recorded as a carried note)

- **Category:** docs-gap
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py` module and `_ErrorArm`
  docstrings (e.g. "§3.2 lines 203-230", "runner.py lines 225-239") and the
  developers'-guide paragraph (design §3.2 and §9).

The new docstrings cite design-document and `runner.py` *line ranges*, not just
section numbers. The citations are accurate at this commit, but line ranges churn
whenever the cited file gains or loses lines above the reference, and nothing
gates their continued accuracy. This is a house-wide convention rather than a
6.2.8-specific defect (the matrix module already cited line ranges before this
task), so it is recorded as a carried documentation-fragility note, not a defect
introduced here.

- **Proposed fix:** Prefer section/anchor citations (§3.2, ADR-003 §3.1) over raw
  line ranges in docstrings, reserving line numbers for in-repo code the test
  drives against (where a stale citation is at least caught by code review of the
  same file). No immediate change required; fold into any future docstring-
  citation hygiene pass if one is opened.
