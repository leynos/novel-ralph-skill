# Extend the command-surface matrix to a minimal error-mode slice

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.2.8 closes the last documented gap in the combinatorial
command-surface matrix
([`tests/test_command_surface_matrix.py`](../../tests/test_command_surface_matrix.py)).
The matrix proves the five read console-scripts behave correctly across the
`command x output-mode x phase` surface, but it only ever crosses *body-produced*
envelopes — exit 0/1/4. It never crosses the two **command-agnostic diagnostic
arms** the shared runner stamps *before any command body runs*: the usage-error
(exit 2, `CycloptsError`) arm and the state-error (exit 3, `StateInputError`)
arm in
[`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
(lines 223–239). These are the arms the harness gates on per the §3.2 exit-code
table, and they are exactly where the `--human` selection is stamped into an
envelope the command body never produced (the reason `parse_global_flags` runs
*before* `run`; runner.py lines 84–96).

Post-merge audit `audit-6.2.1.md` Finding 5 records this gap and offers a binary
choice grounded in design §9's "carried knowingly rather than silently"
principle: either add a minimal exit-2/exit-3 slice to the matrix, **or** name
the omission in the module's `Carried gaps` section. This plan takes the first
option — **add the slice** — because verification (see `Surprises &
Discoveries`) confirms both arms are uniform and command-agnostic across all
five commands, so a small slice is cheap, high-value, and closes the gap rather
than documenting it as carried.

After this change, a maintainer can run the matrix suite and see, for each of
the five read commands, that an empty argv-fault (unknown option) lands the
exit-2 usage envelope and a missing `working/` lands the exit-3 state envelope,
both in machine *and* human mode, with the `--human` stamp and the envelope
skeleton (`command`, `ok: false`, `working_dir`, empty `result`) pinned, and the
diagnostic message asserted by stable prefix. The developers' guide and the
module's `Carried gaps` section are updated so the surface description matches
what the matrix now covers.

You can observe success by running, from the worktree root:

```plaintext
make test
```

and seeing the two new parametrized error-mode tests pass (10 cells each:
five commands x two arms), and:

```plaintext
make markdownlint
make nixie
```

passing over the updated developers' guide.

## Constraints

Hard invariants that must hold throughout implementation.

- Work exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8`. Never edit
  the root/control worktree.
- The matrix stays **in-process** through the shared `run` seam
  (`novel_ralph_skill.contract.runner.run`). It consumes cuprum nowhere and
  carries no `slow`/`timeout` marks (module docstring line 31). The
  installed-binary crossing is the scope of task 6.2.4 and is **out of scope**
  here.
- Do not modify any production module. This is a test-and-docs task: the only
  code touched is `tests/test_command_surface_matrix.py`, its `__snapshots__`
  companion, and `docs/developers-guide.md`. The runner, the five command
  bodies, and the envelope builder must remain byte-for-byte unchanged.
- Honour the snapshot discipline in AGENTS.md ("Python verification and
  testing"): pair every snapshot with a semantic assertion, redact
  platform/locale-variable text (the OS errno string in the exit-3 message),
  and keep snapshots narrow enough that a failure signals a real contract
  change, not churn.
- Honour the single-home principle: the error-mode slice lives **in the same
  module** as the rest of the matrix (developers' guide: "the single home for
  the `command x output-mode x phase` matrix"), not in a new file.
- Prose, comments, and commit messages use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`); Markdown paragraphs wrap at 80 columns, code blocks at
  120 (AGENTS.md "Markdown guidance").
- The module already carries a `pylint: disable=too-many-lines` relaxation
  (lines 60–67). The added slice must not breach any *other* gate
  (`too-many-arguments`, `too-many-locals`). **The Pylint argument-count gate is
  live and not silenced by Ruff.** `pyproject.toml` disables `too-many-arguments`
  in the `[tool.pylint."messages control"]` `disable` block (line 186) but the
  sibling `enable` block (line 192) re-enables `too-many-arguments` (line 297),
  `too-many-locals` (line 301), and `too-many-positional-arguments` (line 303);
  `[tool.pylint.design]` sets `max-args = 4` and `max-positional-arguments = 4`
  (lines 180, 183). The Makefile runs this PyPy-backed Pylint over `tests/`
  (`PYLINT_TARGETS = PYTHON_TARGETS = novel_ralph_skill tests`, lines 15–17), and
  the Ruff per-file-ignore of `PLR0913`/`PLR0917` for `test_*.py`
  (`pyproject.toml` line 97) does **not** silence this separate Pylint pass.
  Pylint counts keyword-only parameters toward `max-args`, so a helper with four
  positional parameters plus one keyword-only `human` totals five and trips R0913
  (`Too many arguments (5/4)`) — **empirically reproduced** with the project
  runner (`uv tool run --python pypy --from
  git+https://github.com/leynos/pylint-pypy-shim.git@726d09f9 pylint-pypy
  --rcfile=pyproject.toml`); a three-positional-plus-one-keyword-only helper
  totals four and is clean (also reproduced). Therefore **every new helper and
  test signature must total at most four parameters** (positional + keyword-only
  combined). Achieve this by bundling `(command, arm)` into a single parametrize
  cell, exactly as the existing matrix bundles `(command, phase)` into
  `_CELLS: tuple[tuple[_ReadCommand, str], ...]` and unpacks `command, phase =
  cell` — reuse the existing `_ReadCommand` NamedTuple and `drive` fixture, as the
  existing tests do.

## Tolerances (exception triggers)

- Scope: if implementation requires touching more than the three files named in
  `Constraints` (the matrix module, its snapshot file, the developers' guide),
  or more than ~120 net new lines in the matrix module, stop and escalate.
- Production code: if any production module under `novel_ralph_skill/` must
  change to make the slice pass, stop and escalate — that would mean the
  error-arm behaviour this plan verified is not what the task assumes.
- Interface: if a public API signature must change, stop and escalate.
- Dependencies: if a new external dependency is required, stop and escalate.
- Iterations: if the new tests still fail after 3 focused attempts, stop and
  escalate.
- Snapshot churn: if the error-mode envelope cannot be made deterministic by
  redacting `messages` alone (i.e. some other field proves platform-variable),
  stop and escalate rather than redacting more of the contract away.
- Ambiguity: the add-the-slice-versus-document-the-gap fork is **already
  resolved** (add the slice); if implementation surfaces a reason the slice is
  not feasible (e.g. an arm turns out command-*specific*), stop and escalate to
  reconsider the carried-gap fallback rather than silently switching.

## Risks

- Risk: the exit-2 diagnostic message varies by command (`novel-compile --check`
  appends a "Did you mean --no-check?" suggestion to "Unknown option:
  --nope.").
  Severity: medium
  Likelihood: certain (observed; see `Surprises & Discoveries`)
  Mitigation: redact `messages` from the snapshot and assert the message
  *prefix* (`"Unknown option:"`) semantically, so the command-varying suffix
  does not churn a shared snapshot.

- Risk: the exit-3 message embeds the OS `strerror` text (`[Errno 2] No such
  file or directory: ...`), which is locale- and platform-dependent.
  Severity: medium
  Likelihood: high (off the development locale/OS)
  Mitigation: drive the **absent-`working/`** variant (not the unparseable
  variant, whose tomlkit message carries a churn-prone line/column), redact
  `messages` from the snapshot, and assert the message prefix
  (`"cannot load working/state.toml"`) semantically — that prefix is
  command-body-owned constant text, identical across all five commands
  (verified).

- Risk: a future Cyclopts upgrade changes the usage-error message wording,
  churning a prefix assertion.
  Severity: low
  Likelihood: low (locked at cyclopts 4.18.0 in `uv.lock`)
  Mitigation: assert on the exit *code* (2) and the redacted envelope skeleton
  as the primary contract; the message-prefix assertion is secondary and
  narrow.

- Risk: adding more cells pushes the module further over the 400-line cap and
  trips a different size gate.
  Severity: low
  Likelihood: low (cap already relaxed via `too-many-lines`)
  Mitigation: reuse the `_ReadCommand` registry, the `drive` fixture, and a
  single redaction helper; keep the slice compact (one error-arm record table
  plus two parametrized tests).

## Progress

- [x] Work item 1: Add the error-arm slice (machine envelope + human presence)
  to the matrix module with semantic assertions; generate the redacted
  snapshot. **Done** (commit `f01db74`). The two new parametrized tests report
  20 passed (10 machine + 10 human); the snapshot gained 10 redacted error-arm
  entries with `messages: ["<redacted>"]`. `make all` green. One deviation from
  the plan draft: Ruff format collapses `_ERROR_CELL_IDS` to a single-line
  comprehension (the plan showed a multi-line form); applied the formatter's
  layout. The four-parameter helper/test signatures passed the PyPy-backed
  Pylint argument-count gate as predicted (no `R0913`).
- [x] Work item 2: Update the developers' guide matrix section and the module's
  `Carried gaps` docstring so the surface description matches the new coverage.
  **Done**. Added a covered-surface paragraph to the module docstring (before
  `Carried gaps`) and a matching paragraph to the developers' guide matrix
  section describing the exit-2/exit-3 error-mode coverage. No carried-gap bullet
  understated coverage; error-mode-by-command appears only as a covered-surface
  statement, never as a carried gap (matching audit-6.2.1 Finding 5's
  documentation half). `make markdownlint`, `make nixie`, and `make all` all
  green.

### Implementation findings (coderabbit, both work items)

Across both work-item reviews, every coderabbit finding landed on the **planning
artefacts** — `docs/execplans/roadmap-6-2-8.md` and the historical review notes
`roadmap-6-2-8.review-r1.md`/`.review-r2.md` — and none on the test code, the
snapshot, the module docstring, or the developers' guide that this task touched.
All were `minor` severity: second-/first-person voice and 80-column reflow in the
plan/review prose, plus an advisory that the round-2 A1 note implied removing a
non-existent carried-gap bullet. These are recorded here rather than actioned:
the review notes are immutable historical records, and the main plan's Work item
2 guidance already says "(not a carried-gap bullet)" and only ever adds a
covered-surface statement, so the implementation is correct as shipped. The
plan's established narrative voice is left intact to preserve meaning; the
voice/reflow observations are carried as cosmetic, non-blocking advisories.

## Surprises & discoveries

- Observation: both diagnostic arms are uniform and command-agnostic across all
  five read commands when driven through `run`.
  Evidence: an in-process drive (worktree root, empty cwd) over
  `[novel-state check, novel-done, wordcount, novel-compile --check, desloppify]`
  produced, for an absent `working/`: exit 3, `ok: false`, `result: {}`,
  `messages == ["cannot load working/state.toml: [Errno 2] No such file or
  directory: 'working/state.toml'"]` — byte-identical across all five. For an
  appended unknown option (`--nope`): exit 2, `ok: false`, `result: {}`,
  message `"Unknown option: --nope."` for four commands and `"Unknown option:
  --nope. Did you mean --no-check?"` for `novel-compile --check`.
  Impact: a single shared error-arm record drives all five commands; the
  snapshot must redact `messages` (the exit-3 errno text and the exit-2 suffix
  are the only variable parts); the rest of the envelope is a stable shared
  skeleton.

- Observation: human mode stamps the command name on both arms.
  Evidence: the same drive in `human=True` produced exit 3 with first line
  `command: novel-state` (etc.) for every command — the `--human` stamp the §3.2
  arms must carry is present.
  Impact: the human-presence assertion (`rendered.strip()` non-empty and
  `command.name in rendered`) used elsewhere in the module works unchanged for
  the error arms.

- Observation: the unparseable-`state.toml` exit-3 variant carries a
  tomlkit parse message with a line/column (`Expected '=' ... at line 1, column
  6`).
  Evidence: writing invalid TOML to `working/state.toml` and driving `wordcount`
  produced exit 3 with that message.
  Impact: prefer the absent-`working/` variant for the snapshot slice (cleaner,
  command-identical message); the unparseable variant is already covered
  per-command (e.g. `tests/test_state_mutators_unit.py`,
  `tests/test_desloppify_sourcing.py`) and need not be re-crossed here.

- Observation: cuprum is not involved in this task.
  Evidence: module docstring line 31 ("consume cuprum nowhere"); the slice is
  in-process through `run`. No cuprum API is relied upon, so no cuprum-version
  pinning is required for this plan.
  Impact: the cuprum-research obligation is satisfied by exclusion; the only
  external library whose behaviour is load-bearing is Cyclopts, verified
  empirically against the locked `cyclopts 4.18.0`.

## Decision log

- Decision: take the "add the slice" fork of the audit Finding 5 binary, not the
  "document the gap" fork.
  Rationale: verification shows both arms are command-agnostic and uniform, so
  the slice is small (one record + two tests, ~80 net lines) and closes the gap
  rather than carrying it. The success clause is satisfied either way, but
  closing beats carrying when the cost is this low.
  Date/Author: 2026-06-25, planning agent.

- Decision: redact `messages` from the error-mode snapshot and assert message
  content by stable prefix instead.
  Rationale: the exit-3 message embeds locale/OS `strerror` text and the exit-2
  message has a command-varying suggestion suffix; both would churn a shared
  snapshot. The contract worth pinning is the envelope *skeleton* (`command`,
  `ok: false`, `working_dir`, `result: {}`) plus the *code*; the message is
  pinned semantically by its command-body-owned prefix. This matches AGENTS.md
  ("Redact or normalize nondeterministic fields ... before snapshotting") and
  design §9 (normalise volatile fields so a failure is a real contract change).
  Date/Author: 2026-06-25, planning agent.

- Decision: use the absent-`working/` tree for the exit-3 cell, not an
  unparseable `state.toml`.
  Rationale: the absent variant yields a command-identical, line/column-free
  message; the unparseable variant's tomlkit message is churn-prone and already
  covered per-command. The §3.2 table lists "working dir absent" as a first-class
  exit-3 trigger, so the absent variant is contract-faithful.
  Date/Author: 2026-06-25, planning agent.

- Decision: trigger the exit-2 arm with an unknown option appended to each
  command's existing read argv (`command.argv + ["--nope"]`), reusing the
  `_READ_REGISTRY`.
  Rationale: an unknown option raises `CycloptsError` uniformly for both the
  command-group surface (`novel-state`) and the default-callback surfaces, so it
  is the one command-agnostic exit-2 trigger (a bare positional does *not* fault
  uniformly — default-callback commands may accept or differently reject it).
  Verified across all five. The design §9 names "unknown subcommand or bad
  arguments -> exit 2"; an unknown option is the "bad arguments" case.
  Date/Author: 2026-06-25, planning agent.

- Decision: bundle `(command, arm)` into a single `_ERROR_CELLS` parametrize
  cell and have `_drive_error_cell` take `(cell, tmp_path, drive, *, human)`,
  rather than passing `command` and `arm` as separate parameters.
  Rationale: the project's PyPy-backed Pylint pass enforces `max-args = 4` /
  `max-positional-arguments = 4` over `tests/` and counts keyword-only
  parameters, so a `(command, arm, tmp_path, drive, *, human)` helper totals five
  and trips `R0913 (5/4)` — empirically reproduced with the project runner during
  round-2 planning. Bundling the cell drops the helper to four parameters and the
  machine/human tests to four/three, matching the existing `_CELLS`-based
  `test_machine_envelope_matrix`. This resolves round-1 review blocker B1; the
  four-parameter form was empirically confirmed clean under the same runner.
  Date/Author: 2026-06-25, planning agent (round 2).

- Decision: assert `len(messages) == 1` in the machine test, not merely a
  non-empty `messages` list.
  Rationale: the snapshot redacts `messages` to `["<redacted>"]`, which collapses
  the message-count signal; pinning the count restores it so a future arm that
  accidentally emits multiple message lines is caught (round-1 advisory A1).
  Date/Author: 2026-06-25, planning agent (round 2).

## Round-2 review resolution

Round-1 (`roadmap-6-2-8.review-r1.md`) verdict was REVISE with one blocking
defect, B1, plus three non-blocking advisories.

- **B1 (resolved).** The proposed `_drive_error_arm(command, arm, tmp_path,
  drive, *, human)` helper had five parameters and tripped Pylint `R0913 (5/4)`,
  failing `make lint`/`make all`. Fixed by bundling `(command, arm)` into a
  single `_ERROR_CELLS` cell (mirroring the existing `_CELLS` pattern) so the
  helper is now `_drive_error_cell(cell, tmp_path, drive, *, human)` — four
  parameters — and the machine/human tests are four/three parameters. The
  argument-count gate's mechanics (the `enable` block re-enabling
  `too-many-arguments`/`too-many-positional-arguments`, `max-args = 4`, Pylint
  counting keyword-only params, the Ruff ignore not silencing Pylint) are now
  pinned in Constraints, and both the failing five-parameter form and the passing
  four-parameter form were empirically reproduced with the project's PyPy-backed
  pylint runner during round-2 planning. See the new Constraints bullet, the
  rewritten Work item 1 steps 1–5, and the round-2 Decision Log entries.
- **A1 (adopted).** The machine test now asserts `len(messages) == 1` (Decision
  Log) so the redaction does not hide a multi-line-message regression.
- **A2 (acknowledged, no change).** The `"Unknown option:"` prefix assertion is
  kept deliberately narrow; exit code 2 and the redacted envelope skeleton remain
  the primary contract (already in Risks, severity low/likelihood low).
- **A3 (no change).** The close-the-gap-versus-carry-the-gap fork was rated sound
  by the reviewer; it stays as decided (close the gap).

## Outcomes & retrospective

Outcome: the purpose is met. The matrix now crosses the exit-2 (usage) and
exit-3 (state) command-agnostic arms for all five read commands in both output
modes (10 machine + 10 human cells). The machine cells pin the envelope skeleton
(`command`, `ok: false`, `working_dir: "working"`, `result: {}`) and the message
count in a redacted snapshot, with the message asserted by its
command-body-owned prefix; the human cells prove the `--human` stamp reaches the
body-less arms. The developers' guide matrix section and the module docstring
both describe the new coverage, and neither lists error-mode-by-command as a
carried gap. `make all`, `make markdownlint`, and `make nixie` are all green at
HEAD.

Retrospective: the plan's round-2 fix (bundling `(command, arm)` into a single
`_ERROR_CELLS` cell to stay within the four-parameter Pylint gate) held exactly
as predicted — the helper and tests passed `make lint` with no `R0913`. The one
deviation was cosmetic: Ruff format collapsed `_ERROR_CELL_IDS` to a single-line
comprehension where the plan draft showed a multi-line form. Verification of both
arms' command-agnostic uniformity (recorded in `Surprises & Discoveries`) proved
accurate: a single shared `_ErrorArm` record drove all five commands with no
per-command branching, so the slice was as cheap as the Decision Log anticipated.

## Context and orientation

You are a novice to this repository. Here is what you need.

The harness ships five **read** console-scripts (`novel-state check`,
`novel-done`, `wordcount`, `novel-compile --check`, `desloppify`). Each is a
[Cyclopts](https://cyclopts.readthedocs.io/) app (locked at `cyclopts 4.18.0` in
[`uv.lock`](../../uv.lock)) built via `make_contract_app` and driven through a
single shared wrapper, `run`, in
[`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py).
`run` owns every `sys.exit` and every envelope emission. Crucially for this
task, `run` has two `except` arms (runner.py lines 225–239) that fire *before or
instead of* a command body returning a value:

- `except CycloptsError` -> emits an envelope with `ExitCode.USAGE_ERROR` (2)
  and exits 2. This is the "unknown subcommand or bad arguments" arm.
- `except StateInputError` -> emits an envelope with `ExitCode.STATE_ERROR` (3)
  and exits 3. A command body raises `StateInputError` when `working/state.toml`
  is missing/unparseable or the working dir is absent.

Both arms call the same `_emit` (runner.py lines 169–187), which renders human
or machine per `RunContext.human`. So the `--human` selection is stamped onto
these arms even though the body never produced a `result`. This is the §3.2
contract the harness branches on (design table at
[`docs/novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
lines 203–230) and the §9 "CLI error-path tests" strategy (design lines
822–826: "unknown subcommand or bad arguments -> exit 2" and "missing or
unparseable `state.toml`, absent working dir -> exit 3").

The **matrix** under test is
[`tests/test_command_surface_matrix.py`](../../tests/test_command_surface_matrix.py).
Read its module docstring (lines 1–58) and the `Carried gaps` section (lines
41–57) first. Its building blocks you will reuse:

- `_ReadCommand` (lines 96–107): a NamedTuple of `(name, build_app, argv)`.
- `_READ_REGISTRY` (lines 112–118): the five read commands and their read argv.
- `_BY_NAME` (lines 145–147): name -> `_ReadCommand` lookup.
- the `drive` fixture (lines 195–235): an in-process driver that `monkeypatch.chdir`s
  to `working.parent`, calls `run(...)`, catches `SystemExit`, and returns
  `(code, out)`. **Note:** the existing `drive` chdirs to `working.parent`, where
  `working` is a *built* phase tree. For the error arms you need a directory with
  **no** `working/`, so you will chdir to a bare `tmp_path` — see Work item 1 for
  how to do this without a phase tree.
- `_assert_no_volatile_fields` (lines 238–258): the volatile-token guard.
- `_DETERMINISTIC_PATH_TOKEN` (line 143): the one allowed working-relative path.

The **snapshot** companion is
[`tests/__snapshots__/test_command_surface_matrix.ambr`](../../tests/__snapshots__/test_command_surface_matrix.ambr)
(syrupy `5.3.2`, `.ambr` AMBR format). syrupy serialises a `dict` with its
`dict()` notation; you regenerate snapshots with `pytest --snapshot-update`.

The **developers' guide** section to update is
[`docs/developers-guide.md`](../../docs/developers-guide.md) lines 87–113 ("The
combinatorial command-surface matrix"). It is the place a maintainer is told to
read before extending the matrix, so it must describe the new error-mode
coverage.

Key terms: an **envelope** is the JSON object every command prints (`command`,
`schema_version`, `ok`, `working_dir`, `result`, `messages`). **Machine mode**
prints it as JSON; **human mode** prints a line-oriented rendering. A **cell** is
one `(command, variant)` combination the matrix parametrizes over.

## Plan of work

Two atomic, independently committable work items. Item 1 adds the test slice
(self-contained: code + snapshot + green gate). Item 2 updates the prose to
match (self-contained: docs + markdown gates). Item 1 must land first so the
guide in item 2 can describe behaviour that already exists.

### Work item 1 — Add the error-mode slice to the matrix

Implements: design §2.3 (lines 125–129, the `command x output-mode x phase`
surface and its machine-snapshot / human-presence / semantic-branch strategy);
design §3.2 (lines 203–230, the exit-2 and exit-3 rows of the code table);
design §9 (lines 822–826, the "CLI error-path tests" strategy — "unknown
subcommand or bad arguments -> exit 2" and "missing or unparseable `state.toml`,
absent working dir -> exit 3"); ADR-003 §3.1 (the command-agnostic `--human`
splitter the arms depend on); audit `audit-6.2.1.md` Finding 5 (the gap and the
add-the-slice option). Closes the Finding-5 gap.

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §2.3, §3.2, §9 (the line ranges above).
- `docs/adr-003-shared-interface-contract.md` (the `--human` global flag and the
  exit-code translation `run` owns).
- `docs/issues/audit-6.2.1.md` Finding 5 (lines 151–178).
- `AGENTS.md` "Python verification and testing" (snapshot discipline:
  pair-with-semantic, redact nondeterministic fields, no brittle snapshots).
- The matrix module docstring and `Carried gaps` section (the surface bound you
  are extending).

Skills to load:

- `python-router`, then `python-testing` (pytest parametrization, fixtures,
  syrupy snapshot discipline, snapshot-plus-semantic pairing). No property or
  mutation verification is warranted: the arms are finite, enumerable, and
  exact — there is no invariant-over-a-range to fuzz (so neither `hypothesis`
  nor `crosshair`), and no surviving-mutant hunt is in scope (so not `mutmut`);
  semantic assertions plus a redacted snapshot pin the contract directly.
- `leta` for navigation within the module and the runner; `sem` if you need the
  history of the matrix module.

Concrete edits to `tests/test_command_surface_matrix.py`:

1. Add an error-arm descriptor near `_READ_REGISTRY`. A small frozen record
   naming the two arms keeps the parametrize declarative and within the
   argument-count gate:

   ```python
   class _ErrorArm(typ.NamedTuple):
       """One command-agnostic diagnostic arm of the shared ``run`` wrapper."""

       label: str                 # "usage" | "state"
       extra_argv: list[str]      # appended to the command's read argv
       build_working: bool        # whether to materialise a working/ tree
       expected_code: ExitCode
       message_prefix: str        # the stable, command-identical message prefix
   ```

   with two module-level instances (named `_USAGE_ARM` and `_STATE_ARM`, so the
   cell-builder in the next paragraph can reference them):

   - `_USAGE_ARM` — usage (exit 2): `label="usage"`, `extra_argv=["--nope"]`,
     `build_working=True` (a real tree so only the argv is at fault),
     `expected_code=ExitCode.USAGE_ERROR`, `message_prefix="Unknown option:"`.
   - `_STATE_ARM` — state (exit 3): `label="state"`, `extra_argv=[]`,
     `build_working=False` (no `working/`),
     `expected_code=ExitCode.STATE_ERROR`,
     `message_prefix="cannot load working/state.toml"`.

   Pin the verified facts in a comment citing the ExecPlan `Surprises`: both
   arms are command-agnostic; `messages` is the only variable field (exit-3
   errno text, exit-2 suggestion suffix), hence redacted from the snapshot.

   Then build the parametrize cell list and ids by crossing every read command
   with both arms, mirroring the existing `_CELLS`/`_CELL_IDS` pattern (lines
   154–159). **Bundling `(command, arm)` into one cell is the mechanism that
   keeps the helper and tests within the four-parameter Pylint gate (see
   Constraints, and B1 in the round-1 review):**

   ```python
   _ErrorCell = tuple[_ReadCommand, _ErrorArm]

   _ERROR_ARMS: tuple[_ErrorArm, ...] = (_USAGE_ARM, _STATE_ARM)
   _ERROR_CELLS: tuple[_ErrorCell, ...] = tuple(
       (command, arm) for command in _READ_REGISTRY for arm in _ERROR_ARMS
   )
   _ERROR_CELL_IDS: tuple[str, ...] = tuple(
       f"{command.name}-{arm.label}"
       for command in _READ_REGISTRY
       for arm in _ERROR_ARMS
   )
   ```

2. Add a helper that drives an error *cell*. For `build_working=False` you need
   a cwd with no `working/`. The existing `drive` fixture chdirs to
   `working.parent`; the simplest reuse is to build a *bare* directory and pass
   a synthetic `working` path under it that is **not** materialised, so
   `working.parent` is the empty cwd. **The helper takes the bundled cell, not
   `command` and `arm` separately, so its signature totals four parameters
   (three positional + one keyword-only `human`) and stays inside the Pylint
   `too-many-arguments`/`too-many-positional-arguments` gate** — the round-1 B1
   fix. A five-parameter form (`command, arm, tmp_path, drive, *, human`) trips
   `R0913 (5/4)` under the project's PyPy-backed pylint and is forbidden:

   ```python
   def _drive_error_cell(
       cell: _ErrorCell, tmp_path: Path, drive: _Driver, *, human: bool
   ) -> tuple[int, str]:
       command, arm = cell
       root = tmp_path / arm.label
       root.mkdir(exist_ok=True)
       if arm.build_working:
           working = wc.build_working_tree(wc.PHASE_STATES["drafting"], root)
       else:
           working = root / "working"  # deliberately NOT created
       argv = [*command.argv, *arm.extra_argv]
       return drive(command._replace(argv=argv), working, human=human)
   ```

   This reuses `drive` unchanged (it only reads `working.parent` and never
   stats `working` itself). Choose any coherent phase for the usage arm
   (`drafting` is fine — the body never runs, the usage error fires at parse).
   Re-verify the helper signature against the project pylint runner (not merely
   Ruff): `make lint` must report no `too-many-arguments`/
   `too-many-positional-arguments` on the module (empirically confirmed clean
   for the four-parameter form during planning).

3. Add the machine-mode error-arm test, parametrized over `_ERROR_CELLS` (10
   cells) with `ids=_ERROR_CELL_IDS`. **The test signature must total at most
   four parameters; bundling the cell makes `(cell, tmp_path, drive, snapshot)`
   exactly four, matching `test_machine_envelope_matrix` (lines 261–267):**

   ```python
   @pytest.mark.parametrize("cell", _ERROR_CELLS, ids=_ERROR_CELL_IDS)
   def test_error_arm_machine_envelope(
       cell: _ErrorCell, tmp_path: Path, drive: _Driver,
       snapshot: SnapshotAssertion,
   ) -> None:
       command, arm = cell
       ...
   ```

   - unpack `command, arm = cell`; drive the cell in machine mode via
     `_drive_error_cell(cell, tmp_path, drive, human=False)`; `json.loads` the
     output.
   - semantic assertions: `code == arm.expected_code`; `envelope["command"] ==
     command.name`; `envelope["ok"] is False`; `envelope["working_dir"] ==
     "working"`; `envelope["result"] == {}`; `messages = envelope["messages"]`
     with `len(messages) == 1` (advisory A1 — pin the count, not merely
     non-empty, so a future arm that emits multiple message lines is caught
     through the redaction) and `messages[0].startswith(arm.message_prefix)`.
   - build a redacted copy (`{**envelope, "messages": ["<redacted>"]}`), run
     `_assert_no_volatile_fields` on it, and assert `redacted == snapshot`.
     Redacting `messages` is the load-bearing normalisation (Decision Log).

4. Add the human-mode error-arm presence test, parametrized over `_ERROR_CELLS`
   (the same 10 cells) with `ids=_ERROR_CELL_IDS`. **The signature totals three
   parameters (`cell, tmp_path, drive`), within the gate:**

   ```python
   @pytest.mark.parametrize("cell", _ERROR_CELLS, ids=_ERROR_CELL_IDS)
   def test_error_arm_human_presence(
       cell: _ErrorCell, tmp_path: Path, drive: _Driver,
   ) -> None:
       command, _arm = cell
       ...
   ```

   - drive the cell in human mode via
     `_drive_error_cell(cell, tmp_path, drive, human=True)`; assert the
     rendering `.strip()` is non-empty and `command.name in rendered` — the same
     presence contract the existing `test_human_mode_presence_matrix` uses, now
     proving the `--human` stamp reaches the body-less arms (the §3.2 /
     ADR-003 §3.1 point).

5. The `ids=_ERROR_CELL_IDS` argument (built from `f"{command.name}-{arm.label}"`)
   already names each failing cell, so no further id wiring is needed.

Tests this work item adds (per AGENTS.md testing rules):

- Snapshot tests (syrupy): the machine-mode error-arm envelope per cell, with
  `messages` redacted, **paired** with the semantic assertions above (no
  snapshot-only coverage; AGENTS.md). 10 new snapshot cells.
- Unit/semantic tests: the exit-code, `ok`, `working_dir`, `result == {}`,
  `len(messages) == 1`, and message-prefix assertions per cell (machine), and the
  presence assertions per cell (human). These are the "unhappy path" coverage
  AGENTS.md requires.
- No property, behavioural (`pytest-bdd`), or e2e test is added: the arms are
  finite and exact (no range invariant -> no `hypothesis`/`crosshair`), the
  in-process matrix is unit/snapshot by design (behavioural composition is task
  6.2.2's `per_chapter_loop.feature`; installed-binary e2e is task 6.2.4), and
  the slice consumes cuprum nowhere.

Validation:

```plaintext
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8
uv run pytest tests/test_command_surface_matrix.py -k error -p no:randomly  # red first (no snapshot yet)
uv run pytest tests/test_command_surface_matrix.py -k error --snapshot-update
uv run pytest tests/test_command_surface_matrix.py                          # all green
make all
```

Expected: before adding the snapshot the two new tests fail on the missing
snapshot; after `--snapshot-update` and the semantic assertions they pass; the
pre-existing matrix tests are untouched and still pass. `make all` (build,
check-fmt, lint, typecheck, test) is green. Commit message (file-based, en-GB):
"Cross the exit-2/exit-3 error arms in the command-surface matrix".

Acceptance: `make all` passes; `uv run pytest
tests/test_command_surface_matrix.py -k error` reports 20 passed (10 machine +
10 human); the snapshot file gains 10 redacted error-arm entries whose
`messages` is `["<redacted>"]`.

### Work item 2 — Update the developers' guide and the `Carried gaps` docstring

Implements: design §9 (lines 817–821, "carried knowingly rather than silently");
audit `audit-6.2.1.md` Finding 5 (the documentation half — the surface
description must match coverage); ADR-005 (the five-script command surface the
guide describes). Keeps living documentation truthful per the project's
docs-as-source-of-truth rule.

Documentation to read first:

- `docs/developers-guide.md` lines 87–113 (the matrix section to amend).
- The matrix module docstring `Carried gaps` section (lines 41–57) — the
  error-mode-by-command bullet Finding 5 says is missing must now be *removed
  from the gap list and turned into a covered-surface statement*, because the
  slice closes it.
- `docs/issues/audit-6.2.1.md` Finding 5 (the exact wording of the gap).

Skills to load:

- `en-gb-oxendict` (Oxford spelling in the prose).
- `leta` to locate the two prose sites; no router skill is needed for a
  docs-only change.

Concrete edits:

1. In `tests/test_command_surface_matrix.py` module docstring: update the
   opening sentence and the `Carried gaps` section so the surface now includes
   the error-mode arms. Add a short paragraph (not a carried-gap bullet) noting
   the matrix crosses the two command-agnostic diagnostic arms — usage (exit 2)
   and state (exit 3) — for every read command in both output modes, with
   `messages` redacted and asserted by prefix, citing §3.2 and §9. Ensure no
   carried-gap bullet now *understates* coverage. (This is a comment/docstring
   edit in a test file, so it rides in this docs-focused commit; if your gating
   prefers it in Work item 1, move it there — either grouping is acceptable so
   long as the docstring never describes the slice as a carried gap once the
   slice exists.)

2. In `docs/developers-guide.md` matrix section (lines 87–113): add one or two
   sentences stating the matrix now also crosses the runner's command-agnostic
   exit-2 (usage) and exit-3 (state) arms — the envelopes that stamp `--human`
   before the body runs — for each read command in both output modes, with the
   message redacted and the envelope skeleton pinned, citing design §3.2 and §9.
   Keep paragraphs wrapped at 80 columns.

Tests this work item adds: none (docs-only). The behaviour the prose describes is
already pinned by Work item 1's tests.

Validation:

```plaintext
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8
make markdownlint
make nixie
make all
```

Expected: `make markdownlint` and `make nixie` pass over the updated guide;
`make all` stays green (the docstring edit is comment-only and changes no
behaviour). Commit message (file-based, en-GB): "Describe the matrix error-mode
slice in the developers' guide".

Acceptance: the developers' guide matrix section and the module docstring both
describe the exit-2/exit-3 coverage; neither lists error-mode-by-command as a
carried gap; `make markdownlint`, `make nixie`, and `make all` all pass.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8`.

1. Confirm the branch and a clean tree:

   ```plaintext
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8 branch --show-current
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-8 status
   ```

   Expect branch `roadmap-6-2-8` and a clean working tree (this plan file aside).

2. Work item 1: edit `tests/test_command_surface_matrix.py` per the plan, then:

   ```plaintext
   uv run pytest tests/test_command_surface_matrix.py -k error
   uv run pytest tests/test_command_surface_matrix.py -k error --snapshot-update
   uv run pytest tests/test_command_surface_matrix.py
   make all
   ```

   Commit (gate first; file-based message).

3. Work item 2: edit the module docstring and `docs/developers-guide.md`, then:

   ```plaintext
   make markdownlint
   make nixie
   make all
   ```

   Commit (gate first; file-based message).

4. Tick roadmap task 6.2.8 in `docs/roadmap.md` only if the workflow's
   merge/audit step expects the implementer to do so; otherwise leave the
   roadmap to the orchestration.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `uv run pytest tests/test_command_surface_matrix.py` passes; the two new
  error-mode tests report 20 passed total (10 machine + 10 human); they fail
  before the slice is added (no snapshot, no assertions) and pass after.
- Lint/typecheck/format/test: `make all` is green.
- Markdown: `make markdownlint` and `make nixie` pass over the updated guide.
- Snapshot hygiene: the 10 new `.ambr` entries carry `messages: ["<redacted>"]`
  and no absolute path, errno text, timestamp, or line/column token.

Quality method (how we check):

- Run `make all` after Work item 1 and again after Work item 2.
- Run `make markdownlint` and `make nixie` after Work item 2.
- Inspect the new snapshot entries to confirm `messages` is redacted and the
  envelope skeleton (`command`, `ok: false`, `working_dir: "working"`, `result:
  {}`) is pinned.

Behavioural acceptance a human can verify: from a directory with no `working/`,
each of the five read commands run through `run` exits 3 and prints an envelope
naming the command with `ok: false`; given an unknown option, each exits 2 with
`ok: false`; in human mode both arms render a non-empty report naming the
command. The matrix now asserts exactly this for all five commands in both
modes.

## Idempotence and recovery

- All steps are re-runnable. `--snapshot-update` is idempotent once the
  envelopes are deterministic (they are, after redacting `messages`).
- If a snapshot churns on re-run, the cause is an unredacted variable field;
  revert the snapshot (`git checkout -- tests/__snapshots__/...`), widen the
  redaction to the offending field *only if* it is genuinely platform-variable
  (else stop and escalate per Tolerances), and regenerate.
- No production code or persistent state is touched, so there is nothing to roll
  back beyond `git checkout` of the three edited files.

## Interfaces and dependencies

- Test framework: `pytest` with `syrupy` `5.3.2` (`SnapshotAssertion`), the
  `drive` fixture, and the `_ReadCommand`/`_READ_REGISTRY` already in the module.
- Runner under test: `novel_ralph_skill.contract.runner.run`,
  `RunContext`, and `ExitCode` (`USAGE_ERROR == 2`, `STATE_ERROR == 3`),
  unchanged.
- Corpus: `working_corpus.build_working_tree` / `PHASE_STATES` for the usage
  arm's real tree; no tree for the state arm.
- External library behaviour relied upon, verified against the locked versions:
  - `cyclopts 4.18.0` raises `CycloptsError` on an unknown option for both
    command-group and default-callback apps (verified empirically; the runner's
    `except CycloptsError` arm maps it to exit 2). The exit-2 message wording
    (`"Unknown option: ..."`, optionally `" Did you mean ..."`) is Cyclopts's,
    hence redacted and asserted by prefix only.
  - `tomlkit` (locked) raises a parse error with a line/column on unparseable
    TOML, which is why the state arm uses the *absent*-`working/` variant, not
    the unparseable one.
  - No cuprum API is used (the matrix is in-process; module docstring line 31).

No new module, no new public API, no new dependency is introduced.
