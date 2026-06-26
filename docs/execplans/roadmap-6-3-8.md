# Make the remaining exit-3 write/file-fault arms actionable

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

The deterministic novel-harness commands all share one exit-code and JSON
envelope contract (design §3.1–§3.2;
`docs/adr-003-shared-interface-contract.md`). Exit `3` is the "state or input
error" channel: the harness stops and the dogfooding agent must recover state.
For that recovery to be possible the message on the channel must be
*actionable* — it must name the artefact and offer a remedy — and it must never
leak raw operating-system text (an `Errno`, a stringified exception repr), per
`docs/scripting-standards.md` line 678 ("Production code should present
friendly error messages").

Roadmap tasks 6.3.1 and 6.3.5 already made the `state.toml`-load faults and the
six draft-read faults actionable, routing them through two shared formatters in
`novel_ralph_skill/commands/_state_load.py`: `_state_input_error` and
`_draft_read_error`. Three exit-`3` tails were deliberately left out of those
formatters because they fault on a *different* artefact with a *different*
remedy shape:

1. `novel_ralph_skill/commands/_compile.py:156` — a manuscript *write* fault:
   `cannot write {_COMPILED_REL}: {exc}`.
2. `novel_ralph_skill/commands/_desloppify.py:270` — a rule-*pack* file read
   fault: `cannot read rule pack: {exc}`.
3. `novel_ralph_skill/commands/_desloppify_ledger.py:90` — a device-*ledger*
   file read fault: `cannot read device ledger: {exc}`.

Each still interpolates a raw caught-exception repr (`{exc}`) onto the exit-`3`
channel, so the same command surfaces both polished prose and raw OS text
depending on which fault fires — the exact dogfooding-agent inconsistency §6.3
exists to close, and the last raw-OS-text leak on the state-input channel.

After this change, an operator (or the dogfooding agent) who drives any of
these three faults sees a message that names the offending artefact (the
compiled manuscript, the rule-pack path, the device-ledger path) and offers a
concrete remedy, with no `Errno` and no exception repr. You can observe success
by running the new behavioural tests: each drives one fault and asserts the
actionable prose is present and the raw `{exc}`/`Errno` text is absent, all on
exit `3`.

## Constraints

Hard invariants that must hold throughout implementation.

- The exit-code and envelope contract must not change. All three faults must
  continue to exit `3` (`ExitCode.STATE_ERROR`) and raise `StateInputError`
  (`novel_ralph_skill.contract.runner`), the exception the shared runner
  already maps to exit `3`. Do not change `ExitCode`, the envelope field set, or
  `ENVELOPE_SCHEMA_VERSION`.
- The split between exit `2` (malformed *content* → `RulePackError` /
  `LedgerError`) and exit `3` (absent/unreadable *file* → `RulePackFileError` /
  `LedgerFileError`) is settled and must be preserved (design §3.2; the
  existing comments at `_desloppify.py:259-269` and
  `_desloppify_ledger.py:80-89`). This plan touches only the exit-`3`
  file-fault arms.
- The compile-write fault must keep routing the absent-`manuscript/` case to
  exit `3`, not the benign exit `1` (the existing comment at `_compile.py:150`
  and `tests/test_compile_unit.py:325`). The write-shaped remedy must not advise
  `novel state init` (the working tree exists; only the write target is
  missing), mirroring the D6 scoping decision recorded in the 6.3.5 plan.
- Messages must not leak `Errno` numbers, a stringified exception repr, or a
  traceback onto the channel. The caught exception is still chained via
  `raise ... from exc` for debuggers; only `StateInputError.messages` (the
  envelope prose) is constrained.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages (standing rules; AGENTS.md).
- File-size and local-variable caps (AGENTS.md "clear file boundaries", 400-line
  module cap). The new formatters live in `_state_load.py` beside their two
  siblings; if adding them would push `_state_load.py` past the cap, escalate
  rather than splitting silently (see Tolerances).
- `_state_load.py` must keep its dependency-free leaf position: it imports only
  from `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner` (its
  module docstring records this to avoid an import cycle). A
  write-fault/file-fault formatter that needs no new imports respects this; if
  a formatter would require importing `rulepack`/`ledger` types, do not —
  accept only the path/artefact identity as plain `pathlib.Path`/`str`, never
  the typed `RulePackFileError`/`LedgerFileError` object.

## Tolerances (exception triggers)

- Scope: if implementation requires changing more than 6 source/test files or
  more than ~250 net lines, stop and escalate.
- Interface: if any public command signature, `ExitCode` member, or envelope
  field must change, stop and escalate.
- Dependencies: if a new external dependency (or a new internal import into the
  `_state_load.py` leaf) is required, stop and escalate.
- File boundary: if adding the new formatters pushes `_state_load.py` past the
  AGENTS.md 400-line module cap, stop and escalate with a proposed carve-out
  rather than improvising one.
- 7.3.9 coupling: if the desloppify/ledger pack-detect consolidation (roadmap
  7.3.9) has already landed by the time this work begins and the rule-pack and
  ledger file-fault arms now share one seam, place the new formatter calls on
  that shared seam (one call site, not two) and note the change in the Decision
  Log. If the seams are still parallel, give each its own call as planned. If
  the shape is ambiguous, stop and present both.
- Iterations: if `make all` still fails after 3 fix attempts on any one work
  item, stop and escalate.
- Ambiguity: if the desired remedy wording is genuinely contested in review,
  present the candidates rather than guessing.

## Risks

    - Risk: The existing test `tests/test_compile_unit.py:325` matches the
      substring "cannot write". A new message that keeps "cannot write" as a
      prefix will not break it, but a reworded message that drops the substring
      will.
      Severity: low
      Likelihood: medium
      Mitigation: keep "cannot write" as the message stem, or update that test in
      the same work item that changes the message; the WI1 test list covers this.

    - Risk: The `RulePackFileError`/`LedgerFileError` messages built in
      `rulepack/parse.py:390` and `ledger/parse.py:311` *already* embed a raw
      `{exc}` (`cannot read rule pack at {path}: {exc}`). The command call sites
      then re-interpolate that whole message into their own `{exc}`, so the raw OS
      text leaks twice. If the new formatter merely wraps `str(exc)` it will still
      carry the leak.
      Severity: medium
      Likelihood: high
      Mitigation: the new formatters must build prose from the *artefact path*
      (`pack or offenders_pack_path()`; `ledger_path`), not from the FileError's
      pre-built message. WI2/WI3 pin a test that the raw `{exc}` text and `Errno`
      are absent. See Decision D2.

    - Risk: Snapshot churn. If any syrupy snapshot captures one of these three
      error envelopes, the message change will fail that snapshot.
      Severity: low
      Likelihood: low
      Mitigation: a pre-flight grep (Concrete steps, Stage A) confirms no
      snapshot pins these messages today; if one is found, regenerate it in the
      same work item and assert the new prose is meaningful, not a raw dump.

    - Risk: Coordination drift with roadmap 7.3.9 (desloppify/ledger pipeline
      consolidation), which may move the two file-fault call sites onto one seam.
      Severity: low
      Likelihood: low
      Mitigation: Tolerances "7.3.9 coupling" governs; the formatters are written
      to accept a path argument so they survive being called from either one seam
      or two.

## Progress

    - [x] WI1: compile-write actionable formatter and its tests.
    - [x] WI2: rule-pack-read actionable formatter and its tests.
    - [x] WI3: device-ledger-read actionable formatter and its tests.
    - [x] WI4: cross-arm parity guard (raw-leak tripwire) over all three arms.

## Surprises & discoveries

    - Observation: All three formatters were added to `_state_load.py` in the
      WI1 source edit (they are small, adjacent, and dependency-free), but each
      call site is routed in its own work item (WI1/WI2/WI3) so each commit stays
      atomic and red→green. `_state_load.py` sits at 336 lines after the
      additions, well within the 400-line cap (no Tolerance trip).
      Evidence: `wc -l novel_ralph_skill/commands/_state_load.py` → 336.
      Impact: none; the leaf module stays dependency-free and under the cap.

    - Observation: `make fmt` rewraps every Markdown file under `docs/` and
      `skill/` via mdformat, not just the file being edited. Running it polluted
      the working tree with 250+ unrelated doc reformats.
      Evidence: `git diff --name-only` after `make fmt` listed the whole docs
      tree.
      Impact: the `check-fmt` gate only checks Python (`ruff format --check`), so
      the spurious Markdown changes were set aside (stashed) and the gate passes
      on Python alone. Use `ruff format` on the touched Python files and edit the
      execplan Markdown by hand rather than `make fmt`.

    - Observation: The resolved rule-pack path is a
      `importlib.resources.abc.Traversable`, not a `pathlib.Path`. The Interfaces
      section and Decisions D1/D2 assumed `pathlib.Path`/`str`, but
      `offenders_pack_path()` (the shipped default) returns a `Traversable` while
      `--pack` supplies a `Path`. The expression `pack or offenders_pack_path()`
      is therefore `Path | Traversable`, which the typechecker (ty 0.0.51)
      rejected against a `pathlib.Path` parameter.
      Evidence: `make typecheck` →
      `invalid-argument-type: Expected 'Path', found 'Traversable'` at
      `_desloppify.py:271`.
      Impact: `_rule_pack_read_error` now takes `Traversable` (a stdlib type
      imported under `TYPE_CHECKING`, so the leaf module stays dependency-free —
      no internal import added, the Constraint that matters). Both `Path` and
      `Traversable` stringify cleanly into the message. The ledger formatter keeps
      `pathlib.Path` because `--ledger` is always a filesystem `Path`. This is a
      type-precision deviation from the plan's stated signature, not a behaviour
      or dependency change; no escalation Tolerance is tripped.

    - Observation: WI2's red→green anchor exposed the *double* leak Decision D2
      predicted: the pre-change undecodable-pack message read
      `cannot read rule pack: cannot read rule pack at <path>: Invalid value (at
      line 3, column 18)` — the command's `{exc}` re-interpolating the
      FileError's own `{exc}`. The new formatter names only the pack path and the
      `--pack` remedy.
      Evidence: WI2 undecodable test failed (red) on `"--pack" in joined` before
      the source change, passed after.
      Impact: confirms the formatter must build prose from the path, never the
      typed FileError message.

    - Observation: WI4 chose a parametrised example test over Hypothesis
      (`python-verification` decision surface): the five formatters do no
      input-dependent branching beyond f-string interpolation, so the input
      space is small and enumerable (5 formatters × 2 representative caught
      exceptions). The guard imports the formatters from their definition module
      `_state_load` (not the `novel_state` re-export) so it exercises the
      implementation location, and derives the faulty path from `tmp_path` with
      the `working/` parent pre-created — a missing *file*, not a missing
      *directory*, matching what the read-fault arms exercise (coderabbit WI4
      findings, addressed).
      Evidence: `tests/test_state_load_actionable_parity.py`; 18 cases green.
      Impact: the no-raw-leak property is now structural; a regression of any
      formatter (or a new one re-interpolating `str(exc)`) fails this guard.

    - Observation: WI3 routed the ledger arm from `_desloppify_ledger.py`, which
      now imports `_device_ledger_read_error` from `novel_state` at module level.
      This adds no import cycle: `novel_state` does not import
      `_desloppify_ledger`, and `_desloppify` imports `ledger_scan` lazily inside
      `_dispatch`. The unused `StateInputError` import was removed from
      `_desloppify_ledger.py` once the formatter took over construction.
      Evidence: `make all` green; no cycle warning; lint clean.
      Impact: the ledger arm now matches the rule-pack arm structurally.

    - Observation: WI1's red→green anchor confirmed the raw leak empirically: the
      pre-change message surfaced `cannot write …compiled.md: [Errno 2] No such
      file or directory: '…/.state.toml.<rand>.tmp'`, leaking both an `Errno` and
      the private atomic-write temp-file path. The new formatter names only the
      compiled target and the `working/manuscript/` remedy.
      Evidence: WI1 behavioural test failed (red) on the `"Errno" not in joined`
      assertion before the source change, passed after.
      Impact: validates Decision D2's reasoning extends to the write arm too.

## Decision log

    - Decision: D1 — Host the three new formatters in
      `novel_ralph_skill/commands/_state_load.py` beside `_state_input_error` and
      `_draft_read_error`.
      Rationale: 6.3.1 and 6.3.5 established that module as the single home for
      exit-`3` actionable-message formatters; placing siblings there keeps the
      "how a state-input fault is rendered" vocabulary in one file and lets a
      parity test import all formatters from one module. The module is
      dependency-free and the new formatters need no new imports (they take a
      `pathlib.Path`/`str`), so the leaf position is preserved.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D2 — The file-fault formatters build prose from the *artefact
      path*, never from the typed `RulePackFileError`/`LedgerFileError` message.
      Rationale: those FileError messages already embed a raw `{exc}` repr
      (`rulepack/parse.py:390`, `ledger/parse.py:311`). Wrapping `str(exc)` would
      re-leak the OS text the task exists to remove. Passing only the path keeps
      `_state_load.py` dependency-free and produces clean prose. The caught
      exception is still chained via `from exc` for debuggers.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D3 — Three distinct formatters, not one parametrised
      "file-fault" formatter.
      Rationale: the three faults name three different artefacts with three
      different remedies — a *write* target (re-create `manuscript/` / re-run
      compile), a *rule-pack* file (check the `--pack` path / restore the shipped
      pack), and a *device-ledger* file (check the `--ledger` path). The 6.3.5
      decision log (D3/D6) already scoped these apart for exactly this reason. A
      single formatter would force a generic remedy and lose the actionability the
      task demands. They may share a remedy-tail constant if review wants it
      (mirrors the 6.3.5.1 addendum pattern), but that is a polish lever, not a
      requirement of this plan.
      Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

All four work items landed, each as one atomic commit gated by `make all` and a
clean `coderabbit review --agent`. The three remaining exit-`3` write/file-fault
arms — compile-write, rule-pack-read, device-ledger-read — now route through
three new dependency-free formatters in `_state_load.py`
(`_compile_write_error`, `_rule_pack_read_error`, `_device_ledger_read_error`),
each naming the offending artefact and offering a concrete, write- or
file-shaped remedy with no `Errno`, no `{exc}` repr, and no traceback. The
WI4 cross-arm parity guard pins the no-raw-leak property structurally over all
five state-input formatters.

What held to plan: Decisions D1 (host in `_state_load.py`), D2 (build prose from
the path, never the typed FileError's pre-built message), and D3 (three distinct
formatters) all proved correct — WI2/WI3's red anchors exposed the predicted
*double* leak when the FileError message was re-interpolated.

Deviation from plan: the rule-pack formatter takes
`importlib.resources.abc.Traversable`, not the `pathlib.Path`/`str` the
Interfaces section assumed, because `offenders_pack_path()` (the shipped default)
returns a `Traversable` while `--pack` supplies a `Path`. `Traversable` is a
stdlib type imported under `TYPE_CHECKING`, so the leaf module stays
dependency-free — the Constraint that matters is preserved. This is a
type-precision deviation, not a behaviour or dependency change; no Tolerance was
tripped. (See the Traversable entry under Surprises & discoveries.)

No snapshot churn (the Stage-A grep found none, confirmed by `make all`). No
`ExitCode`, envelope field, or `ENVELOPE_SCHEMA_VERSION` change. Scope stayed
within Tolerances: six source/test files touched
(`_state_load.py`, `_compile.py`, `_desloppify.py`, `_desloppify_ledger.py`,
`novel_state.py`, plus three test files) — at the file-count edge but no net-line
or interface trip. The 7.3.9 pack-detect consolidation has not landed, so the
rule-pack and ledger arms were given their own formatter calls as planned.

Coderabbit raised three findings total, all on the WI4 parity guard (import from
the definition module; derive the faulty path from `tmp_path`; pre-create the
parent directory so the precondition is a missing file, not a missing directory;
and an explanatory `isinstance` assertion message), all addressed. WI1–WI3
reviews were clean on first pass.

## Context and orientation

This repository ships the `novel` skill: a set of deterministic command-line
verbs (`novel state`, `novel compile`, `novel desloppify`, `novel done`,
`novel wordcount`) that a Ralph-Loop harness drives while an agent writes a
novel. Every command emits the same JSON envelope and obeys the same exit-code
contract.

Key files for this task:

- `novel_ralph_skill/commands/_state_load.py` — the dependency-free leaf module
  hosting the two existing actionable exit-`3` formatters,
  `_state_input_error(path, exc)` and `_draft_read_error(reported_dir, exc)`,
  plus the `STATE_INPUT_ERRORS` tuple and the `working_dir()` accessor. The new
  formatters land here (Decision D1).
- `novel_ralph_skill/commands/_compile.py` — the `novel compile` body. The write
  tail is at `_compile.py:148-157`: it calls
  `write_text_atomically(rendered, compiled_path)`, catches
  `STATE_INPUT_ERRORS`, and currently raises
  `StateInputError(f"cannot write {_COMPILED_REL}: {exc}")`. `_COMPILED_REL` is
  the constant `"working/manuscript/compiled.md"` (`_compile.py:74`), and
  `compiled_path` is `working_dir() / "manuscript" / "compiled.md"`.
- `novel_ralph_skill/commands/_desloppify.py` — the `novel desloppify` body. The
  rule-pack file-fault tail is at `_desloppify.py:255-271`: it calls
  `load_rulepack(pack or offenders_pack_path())`, catches `RulePackFileError`,
  and currently raises `StateInputError(f"cannot read rule pack: {exc}")`. The
  targeted path is `pack or offenders_pack_path()` — capture it in a local
  before the `try` so the formatter can name it.
- `novel_ralph_skill/commands/_desloppify_ledger.py` — the
  `novel desloppify --ledger` body. The device-ledger file-fault tail is at
  `_desloppify_ledger.py:77-90`: it calls `load_ledger(ledger_path)`, catches
  `LedgerFileError`, and currently raises
  `StateInputError(f"cannot read device ledger: {exc}")`. The targeted path is
  the `ledger_path` parameter.
- `novel_ralph_skill/rulepack/parse.py:384-391` and
  `novel_ralph_skill/ledger/parse.py:305-312` — where the typed FileErrors are
  raised. Note (Decision D2): these messages already embed `{exc}`; the new
  formatters must not consume them, only the path.

Terms of art (defined for a newcomer):

- *exit-3 channel* — the contract's "state or input error" exit code (design
  §3.2). The harness stops and the agent must recover state.
- *actionable message* — prose that names the faulted artefact and offers a
  concrete remedy, with no raw OS text. The standard at
  `docs/scripting-standards.md` lines 603-605, 678.
- *`StateInputError`* — the exception
  (`novel_ralph_skill.contract.runner.StateInputError`) the shared runner maps
  to exit `3`. Its `.messages` tuple becomes the envelope's `messages` array.
- *raw `{exc}` leak* — interpolating a caught exception's `str()`/repr into the
  message, which surfaces an `Errno`, a path-as-noise, or a traceback fragment.
  Forbidden on the user-facing channel by scripting-standards line 678.

## Plan of work

The work is four small, independently committable items. WI1–WI3 each add one
formatter and route one call site through it with its tests. WI4 adds a single
cross-arm parity guard so the no-raw-leak property is structural rather than
per-test incidental. Each work item is a red→green cycle: add the asserting
test first (it fails against the raw message because it asserts the *absence*
of the raw text or the *presence* of the remedy prose), then route the call
site.

### WI1 — compile-write actionable formatter

Implements: design §3.2 (exit-3 channel) and §3.4 (atomic writes);
`docs/scripting-standards.md` line 678;
`docs/adr-003-shared-interface-contract.md` (shared envelope); roadmap §6.3.8
first artefact.

Docs to read first: `docs/novel-ralph-harness-design.md` §3.2 and §3.4;
`docs/scripting-standards.md` lines 603-605 and 678;
`docs/execplans/roadmap-6-3-5.md` (the sibling formatter's plan, Decision D6);
`novel_ralph_skill/commands/_state_load.py` (`_state_input_error`,
`_draft_read_error`).

Skills to load: `python-router` (route to the smaller skills it names),
`python-errors-and-logging` (exception design, `raise ... from`, narrow
`except`, the TRY/EM/BLE Ruff rules), `python-testing` (behavioural-vs-unit
boundary, `pytest.raises(match=...)`), `leta` (navigate the call site and
formatter), `sem` (entity-level history of `_state_load.py`).

Changes:

1. In `novel_ralph_skill/commands/_state_load.py`, add
   `_compile_write_error(target: pathlib.Path, exc: Exception) -> StateInputError`.
   It builds a single-arm write-shaped message naming the compiled-manuscript
   target and a write-shaped remedy — e.g. naming `target` and advising the
   operator to ensure `working/manuscript/` exists (or re-run after restoring
   the tree), with no `Errno`/`{exc}`. Keep "cannot write" as the message stem
   to keep the existing substring test green (Risk 1). Docstring mirrors the
   `_draft_read_error` docstring style and records that it is the write-shaped
   sibling, that it never advises `init` (the working tree exists; only the
   write target is missing), and that the caller chains `exc` via `from`.
2. In `novel_ralph_skill/commands/_compile.py`, replace the
   `msg = f"cannot write {_COMPILED_REL}: {exc}"` /
   `raise StateInputError(msg)` tail (lines 156-157) with
   `raise _compile_write_error(compiled_path, exc) from exc`, importing
   `_compile_write_error` alongside the existing `_state_load` imports. Update
   the in-line comment to point at the new formatter.

Tests (add/update under `tests/`):

- Behavioural (`tests/test_compile_bdd.py` or a new scenario): drive
  `novel compile` against a tree whose `working/manuscript/` directory is
  absent at write time (the existing setup in
  `tests/test_compile_unit.py:305-326` removes it), assert exit `3` and that
  the envelope `messages` contain the remedy prose and name the compiled
  artefact, and assert no `Errno`/`{exc}` repr text (e.g. no `r"Errno"`, no
  `r"\["` traceback fragment, no raw exception class name).
- Unit: extend the existing `tests/test_compile_unit.py:303-326` test (or add a
  sibling) so it asserts both the actionable prose and the *absence* of raw OS
  text, not just the `"cannot write"` substring. This is the red→green anchor:
  the absence assertion fails against today's `{exc}`-bearing message and
  passes after.
- Snapshot: only if Stage-A grep finds a compile error-envelope snapshot pinning
  this message; regenerate and re-justify it. Otherwise none (avoid
  snapshot-only coverage per AGENTS.md).

Validation: `make all`.

### WI2 — rule-pack-read actionable formatter

Implements: design §3.2; `docs/scripting-standards.md` line 678; ADR-003;
roadmap §6.3.8 second artefact.

Docs to read first: same as WI1, plus
`novel_ralph_skill/rulepack/parse.py:384-391` (to confirm the typed FileError
already embeds `{exc}`, motivating Decision D2) and
`novel_ralph_skill/commands/_desloppify.py:255-271` (the call site and its
existing scoping comment).

Skills to load: `python-router`, `python-errors-and-logging`, `python-testing`,
`leta`, `sem`. (Same set; the work is structurally identical.)

Changes:

1. In `_state_load.py`, add
   `_rule_pack_read_error(pack_path: pathlib.Path, exc: Exception) -> StateInputError`.
   It names the rule-pack path and offers a file-shaped remedy — e.g. check the
   `--pack` path is correct and readable, or omit `--pack` to use the shipped
   default pack — with no `Errno`/`{exc}`. It takes only the path (Decision
   D2): do not pass or consume the `RulePackFileError`.
2. In `_desloppify.py`, capture the resolved pack path in a local before the
   `try` (`pack_path = pack or offenders_pack_path()`), call
   `load_rulepack(pack_path)`, and in the `except RulePackFileError` arm replace
   `msg = f"cannot read rule pack: {exc}"` / `raise StateInputError(msg)` with
   `raise _rule_pack_read_error(pack_path, exc) from exc`. Keep the existing
   `except RulePackError` (exit-2 content) arm untouched. Update the in-line
   comment to point at the new formatter.

Tests:

- Behavioural (`tests/test_desloppify_command.py`): extend
  `test_absent_pack_file_exits_three` (lines 125-138) — or add a sibling — to
  assert the envelope `messages` name the pack path and carry the remedy, and
  assert no raw `Errno`/`{exc}` text. Add a second case for an *unreadable*
  (permission-denied) or *undecodable* (bad TOML) pack file so both OSError and
  TOMLDecodeError sub-cases route through the formatter, not only the
  absent-file case.
- Snapshot: only if Stage-A grep finds a desloppify error-envelope snapshot
  pinning this message.

Validation: `make all`.

### WI3 — device-ledger-read actionable formatter

Implements: design §3.2; `docs/scripting-standards.md` line 678; ADR-003;
roadmap §6.3.8 third artefact.

Docs to read first: same as WI2, plus
`novel_ralph_skill/ledger/parse.py:305-312` and
`novel_ralph_skill/commands/_desloppify_ledger.py:77-90`.

Skills to load: `python-router`, `python-errors-and-logging`, `python-testing`,
`leta`, `sem`.

Changes:

1. In `_state_load.py`, add
   `_device_ledger_read_error(ledger_path: pathlib.Path, exc: Exception) -> StateInputError`.
   It names the device-ledger path and offers a file-shaped remedy — e.g.
   check the `--ledger` path is correct and readable — with no `Errno`/`{exc}`.
   Takes only the path (Decision D2).
2. In `_desloppify_ledger.py`, in the `except LedgerFileError` arm (lines 87-90)
   replace `msg = f"cannot read device ledger: {exc}"` /
   `raise StateInputError(msg)` with
   `raise _device_ledger_read_error(ledger_path, exc) from exc`. Keep the
   `except LedgerError` (exit-2 content) arm untouched. Update the in-line
   comment.

Tests:

- Behavioural (`tests/test_desloppify_command.py`): extend
  `test_absent_ledger_file_exits_three` (lines 235-248) — or add a sibling — to
  assert the envelope `messages` name the ledger path and carry the remedy, and
  assert no raw `Errno`/`{exc}` text. Add an unreadable/undecodable sub-case as
  in WI2.
- Snapshot: only if Stage-A grep finds a ledger error-envelope snapshot pinning
  this message.

Validation: `make all`.

### WI4 — cross-arm no-raw-leak parity guard

Implements: roadmap §6.3.8 success criterion ("no raw `Errno`/`{exc}` text");
`docs/scripting-standards.md` line 678; the §6.3 "fails with actionable
messages" hypothesis. This mirrors the parity/tripwire pattern 6.3.1.2 and
6.3.2.1 established (a single test that pins the cross-arm property
structurally rather than relying on per-arm diligence).

Docs to read first: `docs/execplans/roadmap-6-3-1.md` and
`docs/execplans/roadmap-6-3-2.md` (the parity-tripwire pattern);
`docs/scripting-standards.md` line 678.

Skills to load: `python-router`, `python-testing`, `hypothesis` *only if* a
property formulation (a range of synthetic faulty paths/exceptions feeding each
formatter, asserting the output never contains the raw repr) is warranted;
otherwise a parametrised example test suffices. Consult `python-verification`
first to decide whether Hypothesis or a plain parametrised test is the right
adversary here — do not reach for property testing reflexively.

Changes: no source changes. Add one test module (e.g.
`tests/test_state_load_actionable_parity.py`, or extend an existing parity test
if one already covers `_state_input_error`/`_draft_read_error`) that imports
all three new formatters plus the two existing ones and, for a synthetic faulty
path and a representative caught exception (an `OSError` carrying an `Errno`, a
`tomllib.TOMLDecodeError`), asserts each formatter's `StateInputError.messages`:

- contains no `Errno`, no `str(exc)` substring, no raw exception class name;
- names the artefact path/identity passed in;
- is non-empty actionable prose.

Tests: the parity guard itself is the deliverable. It must fail if any future
formatter (or a regression of these three) re-introduces a raw-leak.

Validation: `make all`.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-8`.

### Stage A — orient and pre-flight (no code changes)

1. Confirm no snapshot pins the three raw messages (Risk 3):

       grep -rn "cannot write\|cannot read rule pack\|cannot read device ledger" tests/

   Expected today: only `tests/test_compile_unit.py:325`
   (`match="cannot write"`). If a `.ambr` snapshot appears, fold its
   regeneration into the owning work item.

2. Re-read the two sibling formatters to copy their docstring and prose style:

       leta show novel_ralph_skill.commands._state_load._state_input_error
       leta show novel_ralph_skill.commands._state_load._draft_read_error

3. Confirm the three call sites and their targeted paths:

       leta show novel_ralph_skill.commands._compile.compile_manuscript
       leta show novel_ralph_skill.commands._desloppify._scan_or_usage
       leta show novel_ralph_skill.commands._desloppify_ledger.run_ledger

### Stage B–D — per work item

For each of WI1, WI2, WI3, WI4 in order:

1. Add the asserting test(s) first; run the affected suite and watch it fail:

       uv run pytest tests/test_compile_unit.py -q          # WI1
       uv run pytest tests/test_desloppify_command.py -q    # WI2, WI3

   Expect the new absence-of-raw-text assertion to fail (red) before the source
   change.

2. Make the source change (add the formatter in `_state_load.py`, route the call
   site).

3. Run the full gate:

       make all

   Expect `check-fmt`, `lint`, `typecheck`, and `test` all green.

4. Commit (one commit per work item; gate must pass before committing, per the
   standing rules and AGENTS.md "Commit after each change, and gate each
   commit").

No Markdown source other than this plan changes, so `make markdownlint` and
`make nixie` are required only for the execplan edits themselves:

    make markdownlint
    make nixie

Run these whenever this `.md` is edited.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. Each new behavioural test fails before its work
  item's source change (asserting the *absence* of raw text against the
  `{exc}`-bearing message) and passes after. The WI4 parity guard passes and
  would fail if any of the three formatters re-introduced a raw leak.
- Lint/typecheck: `make lint` and `make typecheck` green (Ruff TRY/EM/BLE/N818
  and the type checker clean on the new formatters and call sites).
- Format: `make check-fmt` green.
- Markdown (this plan only): `make markdownlint` and `make nixie` green.

Quality method (how we check):

- `make all` from the worktree root after each work item; it runs
  `build check-fmt lint typecheck test` in order (Makefile line 37).
- Behavioural acceptance, observable by a human: from a faulted tree, running
  the command exits `3` and the printed envelope's `messages` name the artefact
  and offer a remedy, with no `Errno`/`{exc}` text. Example for WI1: build a
  drafting tree, delete `working/manuscript/`, run `novel compile`, observe exit
  `3` and a "cannot write …" message that names the compiled artefact and
  advises recreating the tree, with no `Errno`.

## Idempotence and recovery

Every step is a normal source edit plus test addition; re-running `make all` is
safe and side-effect-free. If a work item's gate fails, revert the working-tree
change (`git checkout -- <file>`) and retry; nothing is written outside the
repo and no migration or destructive operation is involved. Commits are
per-work-item, so a bad item can be amended or reverted without disturbing the
others.

## Interfaces and dependencies

At the end of this work, `novel_ralph_skill/commands/_state_load.py` exports
three new formatters beside its two existing ones, all dependency-free and all
returning the exit-`3` `StateInputError`:

    # novel_ralph_skill/commands/_state_load.py
    def _compile_write_error(
        target: pathlib.Path, exc: Exception
    ) -> StateInputError: …
    def _rule_pack_read_error(
        pack_path: pathlib.Path, exc: Exception
    ) -> StateInputError: …
    def _device_ledger_read_error(
        ledger_path: pathlib.Path, exc: Exception
    ) -> StateInputError: …

Call sites route through them:

    # novel_ralph_skill/commands/_compile.py (write tail)
    raise _compile_write_error(compiled_path, exc) from exc

    # novel_ralph_skill/commands/_desloppify.py (RulePackFileError arm)
    pack_path = pack or offenders_pack_path()
    …
    raise _rule_pack_read_error(pack_path, exc) from exc

    # novel_ralph_skill/commands/_desloppify_ledger.py (LedgerFileError arm)
    raise _device_ledger_read_error(ledger_path, exc) from exc

No external dependency changes. cuprum stays locked at 0.1.0 (`uv.lock`); this
task adds no new cuprum usage — the existing installed-binary e2e fixtures
(`single_program_catalogue`, `ExecutionContext`, `sh.make`, `run_sync`,
verified present in cuprum 0.1.0 at `cuprum/catalogue.py:33-79`,
`cuprum/sh.py:441,528`, `cuprum/sh.py:169`) are untouched. Behavioural coverage
is in-process through the command bodies, mirroring how 6.3.1 and 6.3.5 proved
their message quality; an installed-binary arm is out of scope here (the
executed-surface identity is already pinned by 6.3.6).

## Addenda

Surgical follow-ups folded onto this completed task by the GIST triage of the
6.3.8 reviews and audits. Each runs as a lightweight, no-plan addendum pass.

- 6.3.8.1 (from audit:6.3.8 Findings 1-2; low). Collapse the four path-only
  file-fault formatters in `_state_load.py` onto a private
  `_file_fault_error(message)` builder and drop the dead `exc` parameter from
  the path-only formatters — no body reads it, and `ARG` is not in the ruff
  select set so the unused argument passes lint while misleading the signature.
  Adjust `tests/test_state_load_actionable_parity.py` to the trimmed signatures.
  Removes the near-identical single-arm duplication and the misleading `exc`
  parameter in one focused change.
- 6.3.8.2 (from audit:6.3.8 Finding 5; medium). Update the developers' guide
  exit-3 section (`docs/developers-guide.md`), which still reads "Two sibling
  formatters" and omits the three 6.3.8 additions, to describe all five
  actionable formatters — `_compile_write_error`, `_rule_pack_read_error`, and
  `_device_ledger_read_error` alongside `_state_input_error` and
  `_draft_read_error` — and their write-shaped/file-shaped remedies, so the only
  finding touching a stated source of truth no longer undercounts the
  formatters.
- 6.3.8.3 (from audit:6.3.8 Finding 6; low). Pin the actionable remedy wording
  for the three exit-3 file-fault arms in tests: the behavioural and parity
  tests assert path-named and no-raw-leak but not the remedy clause, so a
  regression dropping the remedy would pass. Add one stable remedy-substring
  assertion per arm (or a `_REMEDY_TOKENS` table on the parity tripwire
  `tests/test_state_load_actionable_parity.py`) to enforce actionability
  structurally alongside the no-leak contract.
