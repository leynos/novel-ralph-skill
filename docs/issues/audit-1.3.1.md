# Post-merge audit — roadmap task 1.3.1

Audit of the codebase after roadmap task 1.3.1 (implement the shared
JSON-envelope and output-mode module) merged to `main` at commit `2270db9`.
Scope is the code and documentation introduced or touched by that task: the new
`novel_ralph_skill/contract/` package (`envelope.py`, `exit_codes.py`,
`runner.py`, `__init__.py`), the four contract test modules
(`test_contract_envelope.py`, `test_contract_envelope_snapshots.py`,
`test_contract_properties.py`, `test_contract_runner.py`), and the
developer-guide updates.

Each finding records a location, a description, a concrete proposed fix, and a
severity. None of these are blocking defects; the merged slice is correct, well
documented, and well tested against ADR-003 and design §3. They are
consolidation and robustness opportunities to action before the five command
bodies adopt `run` in later slices, while the contract surface is still small
and has no real callers to migrate.

The trail followed: design `docs/novel-ralph-harness-design.md` §3.1–§3.4,
`docs/adr-003-shared-interface-contract.md`, the roadmap entry at
`docs/roadmap.md:155`, `docs/developers-guide.md` §"The shared JSON envelope",
and `docs/scripting-standards.md`. Navigation used `leta`; history used `sem`.

## Finding 1 — The shared module parses neither `--human` nor `working_dir`

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `novel_ralph_skill/contract/runner.py:82` (`RunContext`),
  `novel_ralph_skill/contract/runner.py:122` (`run`); design §3.1; ADR-003
  "Functional requirements"

`run` accepts a fully populated `RunContext(command, working_dir, human)` and
never derives any of those three fields itself. `command` is legitimately fixed
per entry point, but `--human` and `working_dir` are two cross-cutting,
contract-level concerns that design §3.1 names as shared ("a `--human` flag
switches stdout to a human rendering"; every envelope carries `working_dir`).
The module that exists specifically to "serve all five commands" (roadmap
§1.3) leaves both to be re-implemented in each of the five command slices.
That is exactly the per-command contract drift the step set out to remove: one
command may spell the flag `--human`, another `--human-readable`; one may
resolve `working_dir` from `os.getcwd()`, another from a `--working` option,
and the envelopes will disagree. The developer guide already advertises "a
`--human` flag for readable output" (`docs/developers-guide.md:111`) as though
the shared module provides it, but it does not.

**Proposed fix:** give the shared module the single seam for both. Either have
`run` accept the raw `argv` and a working-directory resolver and itself strip a
canonical global `--human` flag (registered once as a Cyclopts meta/global
parameter) before delegating to the app, returning a populated `RunContext`; or
provide a small `RunContext.from_argv(command, argv)` constructor that
centralises flag extraction and `working_dir` resolution. Either way the
`--human` spelling and the `working_dir` source become contract-owned, not
per-command. If the boundary is intentionally deferred to a later step, record
that explicitly in the roadmap and soften the developer-guide wording so it
does not over-claim. See proposed roadmap item below.

## Finding 2 — An unexpected body exception escapes `run` as a raw traceback

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `novel_ralph_skill/contract/runner.py:155` (the `try`/`except`
  in `run`); design §3.2 (exit-code table)

`run` catches exactly `CycloptsError` (→ exit 2) and `StateInputError` (→ exit
3). Any other exception raised by a command body — an unhandled `KeyError`, an
`OSError` reading the working directory, a bug — propagates uncaught out of
`run`, so the process prints a Python traceback to stderr and exits with
CPython's default `1`. That collides with the contract's load-bearing exit `1`
(benign negative; the harness loops on it), so a genuine crash would be
misread by the harness as "not yet done" and silently looped on, and no
envelope is emitted at all. The contract has a code for input/state faults
(exit 3) and the design treats a non-zero checker exit as "a finding, not a
crash" (§3.2), so an unexpected fault should never surface as a bare traceback
mapped onto a benign code.

**Proposed fix:** add a final `except Exception` arm to `run` that emits a
contract envelope (no traceback on stdout) and exits with a non-benign code —
exit 3 (state/input error) is the closest existing fit, or introduce a distinct
"internal error" code if the design prefers to keep 3 for declared faults. The
diagnostic/traceback, if retained for debugging, must go to stderr per design
§3.1, never to the stdout envelope channel, and `ok` must be `false`. Add a
test that a body raising an arbitrary `RuntimeError` yields a non-`1`,
non-tracebacked envelope.

## Finding 3 — `_build_app` and the run-and-capture helper are duplicated across two test modules

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_contract_runner.py:32` (`_build_app`) and
  `tests/test_contract_runner.py:65` (`_run`); `tests/test_contract_properties.py:131`
  (`_build_app`) and `tests/test_contract_properties.py:162` (`_drive`)

Both contract test modules define a near-identical `_build_app(outcome)` that
stands up a Cyclopts app configured exactly as `run` requires
(`result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False`) with one `act` subcommand that returns the outcome or
raises `StateInputError`. They also each define a thin "drive `run` and assert
it exits" helper (`_run` vs `_drive`) over the same `RunContext`. The
wrapper-required `App(...)` keyword set is the single most fragile contract
detail (the round-1 B1 regression guard), and duplicating it across two files
means a future Cyclopts change has to be reconciled in two hand-written copies
that can silently drift.

**Proposed fix:** extract a shared `conftest.py` (or a small
`tests/_contract_helpers.py`) fixture/factory providing the wrapper-configured
app builder and a `drive_run` helper, and have both modules import it. This
also makes the load-bearing `App(...)` keyword set assertable in one place.

## Finding 4 — The fixed envelope field order is encoded in three places

- **Category:** similarity
- **Severity:** low
- **Location:** `novel_ralph_skill/contract/envelope.py:54` (the `Envelope`
  dataclass fields), `novel_ralph_skill/contract/envelope.py:133` (the
  `ordered` dict in `render_machine`), and
  `tests/test_contract_envelope.py:30` (`_FIXED_FIELD_ORDER`)

The contract's six-key order — `command`, `schema_version`, `ok`,
`working_dir`, `result`, `messages` — is spelled out independently three times.
`render_machine` deliberately rebuilds the ordered dict rather than leaning on
dataclass field order (a reasonable choice, documented in its docstring), but
that leaves three literal copies that must be kept in lockstep by hand. Adding
a seventh field, or reordering, touches all three with no single guard tying
them together.

**Proposed fix:** derive the renderer's key order from one declared constant —
e.g. a module-level `ENVELOPE_FIELD_ORDER: tuple[str, ...]` that
`render_machine` iterates (`{name: getattr(env, name) ...}` with the two
container fields coerced) and that the test imports instead of re-declaring
`_FIXED_FIELD_ORDER`. A `dataclasses.fields(Envelope)` assertion can then pin
the dataclass to that same constant, making field order single-sourced.

## Finding 5 — `messages` is typed `Sequence[str]` in two value types but `tuple[str, ...]` in the error channel

- **Category:** inconsistency
- **Severity:** low
- **Location:** `novel_ralph_skill/contract/runner.py:60`
  (`StateInputError.messages: tuple[str, ...]`),
  `novel_ralph_skill/contract/runner.py:79`
  (`CommandOutcome.messages: cabc.Sequence[str]`),
  `novel_ralph_skill/contract/envelope.py:59`
  (`Envelope.messages: cabc.Sequence[str]`)

The same human-prose `messages` payload travels through three carriers with two
different element-container types: `StateInputError` exposes a concrete
`tuple[str, ...]`, while `CommandOutcome` and `Envelope` use the abstract
`cabc.Sequence[str]`. `run` then bridges them with `list(exc.messages)` at
`runner.py:169` for the error path but passes `outcome.messages` through
unchanged for the success path. The inconsistency is harmless today but invites
a reader to wonder whether the tuple-vs-sequence distinction is meaningful (it
is not).

**Proposed fix:** settle one element type for the `messages` contract. Using
`cabc.Sequence[str]` uniformly on `StateInputError.messages` (storing
`self.messages = messages` from `*messages`, which is already a tuple and
satisfies `Sequence`) removes the special-cased `list(...)` bridge in `run` and
documents that all three carriers speak the same shape.

## Finding 6 — The renderers use bare `print` rather than an explicit, flushed stream

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/contract/runner.py:119` (`print(rendered)`
  in `_emit`)

`_emit` writes the envelope with a bare `print(rendered)`. The envelope
correctly belongs on stdout, so the destination is right, but the call relies
on the ambient `sys.stdout` and default buffering. Design §3.1 is explicit that
the JSON object goes to stdout and diagnostics to stderr; making the target
stream explicit at the single emission seam guards that invariant against a
caller that has reassigned `sys.stdout`, and an explicit `flush=True` ensures
the envelope reaches a pipe before the immediately following `sys.exit`, which
matters when the harness reads the command over a pipe.

**Proposed fix:** write `print(rendered, file=sys.stdout, flush=True)` (or a
`sys.stdout.write(rendered + "\n"); sys.stdout.flush()`), and add a brief
comment noting that stdout is the contract channel and stderr is reserved for
diagnostics, so the single emission point documents the §3.1 split.

## Finding 7 — `render_human` is asymmetric with `render_machine` on field coverage, undocumented as deliberate at the contract level

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/contract/envelope.py:144` (`render_human`);
  design §3.1

`render_human` omits `schema_version` and `result` and surfaces `command`,
`ok`, `working_dir`, and `messages`. Hiding `result` is correct and documented
(it is the machine channel). Omitting `schema_version` from the human view is a
reasonable choice but is undocumented, and the developer guide describes the
human mode only as "readable output" without stating which fields it carries.
A reader comparing the two renderers cannot tell whether the omission is
intentional or an oversight.

**Proposed fix:** add one sentence to the `render_human` docstring stating that
`schema_version` and `result` are intentionally elided from the human channel
(machine-only metadata and machine-only payload, respectively), and mirror that
in `docs/developers-guide.md` so the two renderings' field coverage is a
documented contract rather than an implementation accident.
