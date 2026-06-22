# Implement the shared JSON-envelope and output-mode module

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

This is roadmap task 1.3.1 (`docs/roadmap.md` lines 139-152, step 1.3). It
builds the one contract every deterministic command shares: a single
machine-mode JSON envelope on stdout, a `--human` rendering switch, and the
disambiguated exit-code table (0/1/2/3/4) — all as reusable helpers that the
five console-scripts adopt rather than each re-inventing an output shape. The
contract is fixed in `docs/adr-003-shared-interface-contract.md` and described
in `docs/novel-ralph-harness-design.md` §3.1 and §3.2.

After this change a contributor can, in Python, build an envelope for any
command and render it in either mode, and the exit code the process returns is
guaranteed to mirror the envelope's `ok` flag and the contract's code meanings.
Concretely, after this task lands:

- A new module `novel_ralph_skill/contract/` exposes the envelope data type,
  the exit-code enum, a machine-mode serialiser (`json.dumps`-based), a
  `--human` renderer, and a thin `run` wrapper that drives a Cyclopts
  application so that a usage error exits `2` (not Cyclopts's native `1`), a
  state/input error exits `3`, and a benign-negative / actionable-finding
  result exits `1` / `4` as the command body decides.
- A property-based test (Hypothesis) proves `ok is True` if and only if the
  exit code is `0`, that each of the four non-zero codes is reported as
  `ok: false`, and that the five codes carry the distinct semantics §3.2
  fixes (a malformed invocation → `2`; an unparseable or missing `state.toml`
  → `3`; codes `1` and `4` are non-interchangeable).
- Snapshot tests (syrupy) pin the rendered envelope shape — one machine-mode
  snapshot per exit code, plus a human-mode snapshot — with non-deterministic
  fields normalised, so a snapshot failure flags a real contract change.

This module is the load-bearing seam the slices in roadmap phases 2-6 reuse;
it is built once here (ADR-003 "Migration plan": "built once in roadmap task
1.3.1 and reused by every slice").

### What this task does NOT do

- It does not implement any of the five commands' `result` payloads. Those are
  per-command shapes defined in design §4 and built in later slices (ADR-003
  "Non-goals"). This task delivers the envelope *frame* and the *plumbing*;
  the command bodies remain the stubs from task 1.2.x.
- It does not rewire `pyproject.toml`'s `[project.scripts]` entry points. The
  five entry points keep pointing at
  `novel_ralph_skill.commands.stub` (verified: `pyproject.toml` lines 10-15).
  Converting a stub to use the new contract module is each command's own later
  task; doing it here would smear command logic into the scaffolding task and
  break the focused, atomic boundary.
- It does not invoke any external process, so it depends on **no** `cuprum`
  API. Design §9 states plainly: "v1 commands shell out to nothing, so the
  suite touches only the filesystem under `tmp_path`." The scripting standards
  reserve `cuprum` for "external processes" (`docs/scripting-standards.md`
  lines 35-39); this module has none, so cuprum is correctly absent from its
  imports and tests. (Stated explicitly so the implementer does not reach for
  a catalogue that this task has no use for.)

## Orientation for a newcomer

You have only this repository's working tree and this file. Key facts:

- The package is `novel_ralph_skill` (`pyproject.toml` line 2,
  `requires-python = ">=3.14"` line 6). It already contains
  `novel_ralph_skill/commands/{names.py,stub.py}` and a `pure.py`.
- The five console-script names live once, as data, in
  `novel_ralph_skill/commands/names.py`
  (`COMMAND_ENTRY_POINTS`, `COMMAND_NAMES`); never re-spell them. The new
  module will import `COMMAND_NAMES` to validate the `command` field rather
  than hard-coding a literal list.
- The CLI framework is Cyclopts, pinned at `4.18.0` (`uv.lock`), and is the
  project default (`docs/scripting-standards.md` lines 5-25). The stub module
  already builds `cyclopts.App` instances.
- `tomlkit` is the only other runtime dependency (`pyproject.toml` line 8); it
  is the state round-trip library (ADR-002), not used by this task except that
  the exit-`3` "unparseable `state.toml`" path is exercised by the property
  and CLI tests through a small helper, not by parsing real TOML here.
- Quality gates are Makefile targets (`AGENTS.md` lines 71-98): `make all`
  runs `build check-fmt lint typecheck test`; markdown changes additionally
  need `make markdownlint` and `make nixie`. `make lint` enforces 100%
  docstring coverage via `interrogate` and runs Ruff plus PyPy-Pylint.
- Tests live in the top-level `tests/` tree only (`AGENTS.md` lines 145-147);
  do not put tests inside the package.

Pinned (verified against the official Cyclopts v4.18.0 documentation; see
"Documentation to read" for the exact pages) Cyclopts behaviour, because it
dictates the shape of the `run` wrapper. Three facts are load-bearing:

1. **Usage errors exit `1` by default, not `2`.** An unknown command, an
   unknown option, and a missing required argument each raise a
   `cyclopts.exceptions.CycloptsError` subclass (`UnknownCommandError`,
   `UnknownOptionError`, `MissingArgumentError`). By default Cyclopts has
   `exit_on_error=True`, so on such an error it calls `sys.exit(1)` after
   printing a Rich panel (api.html / app_calling.html "Exception Handling and
   Exiting"). Building the app with `exit_on_error=False` makes it *raise* the
   `CycloptsError` instead of exiting; building it with `print_error=False,
   help_on_error=False` suppresses the Rich error panel so the wrapper can emit
   the contract's own diagnostics. `--help` and `--version` still exit `0`.
2. **`result_action` governs what happens to the body's *return value*, and the
   default would swallow the success path.** Per Cyclopts v4.18.0
   `packaging.html` "Result Action", `App` defaults to
   `result_action="print_non_int_sys_exit"`: an **integer** return is passed
   straight to `sys.exit(int)`, a **`None`** return calls `sys.exit(0)`, a
   **`bool`** maps `True`→`sys.exit(0)`/`False`→`sys.exit(1)`, and a **string**
   is printed then `sys.exit(0)`. Under this default, `App.__call__` itself
   terminates the process on a normal body return, so any wrapper code placed
   after `app(...)` to build and emit the success/benign/actionable envelope
   would *never run*. This is the round-1 B1 defect.
3. **`result_action="return_value"` is the fix.** Cyclopts v4.18.0 documents
   `"return_value"` as a built-in `result_action` mode that "returns the
   command's value unchanged" (api.html `App.result_action`). With the app
   constructed as `cyclopts.App(..., result_action="return_value")`, a normal
   `app(...)` call returns the body's value to the wrapper instead of exiting,
   so the wrapper owns *all* exit and envelope emission. (An equivalent
   alternative — a custom `result_action` callable, `def handler(result)` —
   exists, but `"return_value"` is simpler and keeps every exit decision in one
   place. Decision recorded in the Decision Log.)

The consequence is load-bearing and is why this module owns a `run` wrapper
rather than letting each command call its `App` directly: **the contract
demands usage errors exit `2` (design §3.2 / ADR-003 Table 2) but Cyclopts's
default is `1`, and the contract demands the wrapper emit the envelope on the
`0`/`1`/`4` success path, which the default `result_action` would pre-empt.**
The wrapper therefore (a) constructs the app with
`result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False`, (b) catches `CycloptsError` and exits `2` with a
usage-error envelope, (c) catches `StateInputError` and exits `3`, and (d) on a
normal return emits the envelope and calls `sys.exit` with the body's
`ExitCode` integer for the `0`/`1`/`4` paths.

Because this behaviour is the foundation of the whole contract and a future
`uv` re-resolution could change a Cyclopts default silently, it is **pinned by a
committed tripwire test** (Work item 1), not merely probed — mirroring the
existing `tests/test_tomlkit_dependency.py` version-and-behaviour pin.

## Constraints

Hard invariants; violation requires escalation, not a workaround.

- Do not edit `pyproject.toml`'s `[project.scripts]` table or the
  `novel_ralph_skill/commands/` modules' public behaviour. The stubs keep
  exiting `2` with their current message until their own later slices adopt the
  contract.
- Do not weaken any existing test. The task is additive.
- The five command names come from `novel_ralph_skill.commands.names`; the new
  module must not introduce a second list of names (AGENTS.md "shotgun
  surgery" / single-source-of-truth heuristic; developers-guide "Edit a command
  name there, not in five places").
- The envelope's field set and order are fixed by ADR-003 and design §3.1:
  `command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`. No
  field may be added, renamed, dropped, or reordered.
- `ok` is `true` if and only if the exit code is `0` (ADR-003 "Technical
  requirements": "`ok` mirrors the exit code: true only on 0"). `result` holds
  only machine-actionable data; `messages` holds only human prose the harness
  never parses (design §3.1; ADR-003 "Functional requirements").
- Machine mode is the default; `--human` switches stdout to the human
  rendering; diagnostics go to stderr in both modes (design §3.1).
- The envelope `schema_version` is the contract version, independent of the
  `state.toml` and rule-pack versions (design §3.1; ADR-003 "Technical
  requirements"). It is a single integer constant in this module, currently
  `1`.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
  docstrings (AGENTS.md lines 18-20; en-gb-oxendict skill), except references
  to external API names (e.g. Cyclopts's `print_error`).
- No single code file exceeds 400 lines (AGENTS.md lines 24-27). Split the
  contract package by responsibility if a file approaches the limit.
- 100% docstring coverage (`make lint` runs `interrogate`); every public
  symbol and module needs a docstring.

## Tolerances (exception triggers)

- Scope: if implementation requires changing more than 8 files or ~600 net
  lines (production + tests), stop and escalate.
- Dependencies: this plan adds exactly two dev dependencies — `hypothesis` and
  `syrupy` — to `[dependency-groups].dev` (neither is a runtime dep), each at an
  exact locked version pin. `pytest-bdd` is deliberately NOT added: design §9
  scopes behavioural (pytest-bdd) suites to concrete commands' harness-facing
  flows and assigns the exit-code contract to "CLI error-path tests", which this
  module satisfies without a behavioural suite (see Decision Log, round-2 B4).
  If a *third* new dependency, or any new *runtime* dependency, appears
  necessary, stop and escalate.
- Interface: if the envelope field set, the exit-code values, or the
  `schema_version` semantics in ADR-003 must change to make the module work,
  stop and escalate — that is an ADR amendment, not a silent change (ADR-003
  "Known risks").
- Cyclopts: if the probed exit-code behaviour above does not reproduce against
  the locked `cyclopts==4.18.0` in the project venv during Work item 1, stop
  and re-pin before writing the wrapper.
- Iterations: if a gate (`make all`) still fails after 3 fix attempts on one
  work item, stop and escalate.
- Ambiguity: if design §3.1/§3.2 and ADR-003 appear to disagree on any field,
  code, or rule, stop and present the conflict rather than choosing.

## Risks

- Risk: Cyclopts maps usage errors to exit 1, conflicting with the contract's
  exit 2. Severity: high. Likelihood: high (confirmed, not hypothetical).
  Mitigation: the `run` wrapper builds the App with `print_error=False,
  help_on_error=False` and calls it with `exit_on_error=False`, catches
  `CycloptsError`, emits the usage-error envelope, and exits 2. Pinned by the
  committed Cyclopts tripwire (Work item 1) and a CLI error-path test (Work
  item 4).
- Risk: Cyclopts's default `result_action="print_non_int_sys_exit"` calls
  `sys.exit()` on the body's return value inside `App.__call__`, pre-empting the
  wrapper's envelope emission on the success/benign/actionable path. Severity:
  high. Likelihood: high (confirmed against packaging.html). Mitigation: the
  wrapper constructs the app with `result_action="return_value"` so `app(...)`
  returns the body value to the wrapper, which owns all exit and envelope
  emission. Pinned by the Work item 1 tripwire (assert `app(...)` returns
  control) and the Work item 4 success-path tests (assert exit 0/1/4 envelopes
  are emitted).
- Risk: a future `uv` re-resolution bumps Cyclopts past 4.18.0 and changes a
  default (the `result_action` protocol, the usage-error exit code, or the
  panel-suppression kwargs), breaking the contract while `make all` stays green.
  Severity: high. Likelihood: low. Mitigation: a committed version+behaviour
  tripwire test (Work item 1) pins `LOCKED_CYCLOPTS_VERSION = "4.18.0"` and the
  three load-bearing behaviours, so a silent drift fails the suite and a
  deliberate bump updates the pin visibly (the `tests/test_tomlkit_dependency.py`
  pattern).
- Risk: Hypothesis's `function_scoped_fixture` health check fires if a `@given`
  test consumes `tmp_path` (or any function-scoped fixture). Severity: medium.
  Likelihood: medium. Mitigation: the envelope property test generates all
  inputs from strategies and never takes a function-scoped fixture inside
  `@given` (Hypothesis "Compatibility" docs: function-scoped fixtures run once
  for the whole test and raise `HealthCheck.function_scoped_fixture`). The
  "unparseable `state.toml` -> 3" case is modelled with an in-test sentinel
  exception, not a real file, so no fixture is needed.
- Risk: syrupy snapshots churn on harmless formatting or path changes.
  Severity: medium. Likelihood: medium. Mitigation: snapshot only the rendered
  envelope text with `working_dir` normalised to the fixed token `"working"`
  before snapshotting (AGENTS.md lines 148-158); pair each snapshot with a
  semantic assertion (assert the parsed JSON's `ok` matches the code). Note
  (round-1 A1): the §3.1 envelope has **no** timestamp field and only one
  path-like field, `working_dir`; the design's own example already uses the
  literal `"working"`. There is therefore nothing else to redact — normalise
  `working_dir` and do not invent timestamp/absolute-path fields the envelope
  does not carry.
- Risk: new dev deps fail to resolve under uv / Python 3.14. Severity: low.
  Likelihood: low. Mitigation: Hypothesis supports CPython 3.10+ (its
  "Compatibility" docs) and is thread-safe / multi-process-safe, so it coexists
  with pytest-xdist; syrupy targets "the latest version of Python and Pytest".
  Resolution is proven by `make build` succeeding in Work item 2.

## Progress

- [x] Work item 1: add a committed Cyclopts version+behaviour tripwire test
  pinning 4.18.0, the usage-error→`CycloptsError`-under-`exit_on_error=False`
  behaviour, `result_action="return_value"` returns control to the caller, and
  the help/version-returns-`None` behaviour (no production code). Done: see
  `tests/test_cyclopts_contract.py`. Two plan assumptions were corrected against
  the locked Cyclopts (help/version return `None` under `exit_on_error=False`;
  unknown subcommand raises `UnknownCommandError` only without a catch-all
  default) — recorded in Surprises. `make all` green; coderabbit 0 findings.
- [x] Work item 2: add hypothesis and syrupy dev dependencies (each version-
  pinned) and a version-pinning guard test. Done: hypothesis 6.155.7, syrupy
  5.3.2 in `[dependency-groups].dev`; `tests/test_contract_test_deps.py` pins
  both (syrupy via `importlib.metadata` as it lacks `__version__`). `make all`
  green; coderabbit 0 findings.
- [x] Work item 3: implement the envelope data type, exit-code enum, and
  machine-mode + human renderers, with unit and snapshot tests. Done:
  `contract/{exit_codes,envelope,__init__}.py`,
  `tests/test_contract_envelope.py`, two snapshots. `build_envelope` carries a
  dual `# noqa: PLR0913` + `pylint: disable=too-many-arguments` (the five fields
  are contract-fixed). `make all` green; coderabbit 0 findings.
- [x] Work item 4: implement the `run` wrapper and exit-code mapping (with
  `result_action="return_value"`), with CLI error-path tests covering the usage
  (2), state (3), and success/benign/actionable (0/1/4) paths plus the
  `--help`/`--version` and `--human` boundaries. Done: `contract/runner.py`
  (`StateInputError`, `CommandOutcome`, `RunContext`, `run`),
  `tests/test_contract_runner.py`. Signature uses `RunContext` (see Decision
  Log). `make all` green; coderabbit 0 findings.
- [x] Work item 5: add the Hypothesis property test for the ok/exit-code and
  five-code semantics, and the per-code envelope snapshots. Done:
  `tests/test_contract_properties.py` (biconditional + non-zero/distinct
  properties + the 2/3 mapping cases) and
  `tests/test_contract_envelope_snapshots.py` (five per-code snapshots). The
  biconditional was confirmed non-vacuous by temporarily inverting it locally
  (it failed with a shrunk counter-example), then reverting. `make all` green;
  coderabbit 0 findings.
- [x] Work item 6: document the module in the developers' guide and reify the
  roadmap checkbox; run markdown gates. Done: `docs/developers-guide.md`
  (envelope/exit-code sections name `contract/`, its public surface, the
  `result_action="return_value"` and exit-`2` translation rules, and the
  `StateInputError`→exit-`3` channel) and `docs/roadmap.md` 1.3.1 flipped to
  `[x]`. `make markdownlint` and `make nixie` green; `make all` green;
  coderabbit 0 findings.
- [x] Fix round 1 (blocking finding 1): the developers' guide claimed `run`
  "builds the app with `result_action="return_value"`", contradicting
  `runner.py`, whose module and function docstrings make plain that the caller
  builds the app and `run` only *requires* it be built with
  `result_action="return_value", exit_on_error=False, print_error=False,
  help_on_error=False`. A slice author trusting the old guide would pass a
  default `cyclopts.App`; its default `result_action="print_non_int_sys_exit"`
  would `sys.exit` on the body's `CommandOutcome` return inside `App.__call__`,
  pre-empting `run`'s envelope emission — the B1 tripwire defect. Reworded
  `docs/developers-guide.md` so the first load-bearing consequence says `run`
  *requires the caller* to build the app with that configuration so that `run`,
  not Cyclopts, owns every `sys.exit` and envelope emission.
  `make markdownlint`, `make nixie`, and `make all` green; coderabbit 0
  findings.

## Surprises & discoveries

- Observation: `msgspec` appears in Ruff's banned-from import list
  (`pyproject.toml` lines 106, 120) but is NOT a locked dependency (`uv.lock`
  has zero `msgspec` entries). Evidence: `grep -c msgspec uv.lock` returns 0;
  `pyproject.toml` lists only `cyclopts` and `tomlkit` as runtime deps. Impact:
  the envelope must be serialised with the standard library (`dataclasses` +
  `json`), NOT msgspec. Adding msgspec would be a new runtime dependency and
  breach the Tolerances. Decision recorded below.
- Observation (round-2): Cyclopts's default `result_action`
  (`"print_non_int_sys_exit"`) calls `sys.exit()` on the body's return value
  inside `App.__call__`, so wrapper code after `app(...)` cannot run on the
  success path. Evidence: Cyclopts v4.18.0 `packaging.html` "Result Action"
  (int → `sys.exit(int)`, None → `sys.exit(0)`) and `api.html`
  `App.result_action` (`"return_value"` "returns the command's value
  unchanged"), both fetched and cited during round-2 planning. Impact: the
  wrapper must build the app with `result_action="return_value"`; this is the
  resolution of round-1 blocking point B1 and is pinned by the Work item 1
  tripwire.
- Observation (implementation, 2026-06-22): two load-bearing Cyclopts claims in
  the round-2 plan did **not** reproduce against the locked `cyclopts==4.18.0`
  exactly as written, and the wrapper/tripwire were adapted to the real
  behaviour (the plan's Work item 4 note permits this: "shape the `body`
  callable ... to fit Cyclopts's idiom, provided `result_action="return_value"`,
  the exit-code mapping, and the machine-mode-default behaviour hold").
  - `--help`/`--version` do **not** raise `SystemExit` when the app is built
    with `exit_on_error=False`; they print and **return `None`** to the caller.
    (Under the default `exit_on_error=True` they do raise `SystemExit(0)`.)
    Impact: the wrapper cannot rely on Cyclopts to exit `0` for help/version.
    Instead, command bodies in this contract always return an `ExitCode`, and a
    non-`ExitCode` return from `app(...)` (i.e. the `None` from a help/version
    invocation) is the wrapper's signal to exit `0` with **no** envelope. This
    keeps the observable contract (help/version exit `0`, no envelope) intact.
  - An unknown subcommand raises `UnknownCommandError` **only when the app has
    no catch-all `@app.default(*tokens)`**; with such a default it routes to the
    default body. The wrapper's test app therefore registers named subcommands
    without a catch-all default so an unknown subcommand raises
    `UnknownCommandError` (a `CycloptsError` subclass) and the wrapper maps it to
    exit `2`. Unknown **option** and missing **argument** raise their
    `CycloptsError` subclasses regardless of the default. Evidence: empirical
    probes against the synced `.venv` during Work item 1.

## Decision log

- Decision: serialise the envelope with a frozen `@dataclass` plus
  `json.dumps`, not msgspec/attrs/pydantic. Rationale: msgspec is unlocked (see
  Surprises); the stdlib needs no new runtime dependency, produces deterministic
  key order matching the fixed field order, and keeps the module trivially
  typecheckable. The data shape is a flat record with a nested `result` mapping
  and a `messages` list — well within `dataclasses`' remit (python-data-shapes
  skill: reach for a dataclass for a plain domain record with no wire-schema
  needs). Date/Author: 2026-06-22, planning agent.
- Decision: the contract lives in a new package `novel_ralph_skill/contract/`
  (an `__init__.py` plus `envelope.py`, `exit_codes.py`, `runner.py`), not a
  single flat module. Rationale: AGENTS.md caps files at 400 lines and asks for
  coherent module boundaries; the envelope record, the exit-code vocabulary, and
  the Cyclopts-driving runner are three distinct responsibilities. Splitting now
  avoids a later refactor commit. Date/Author: 2026-06-22, planning agent.
- Decision: the `run` wrapper owns the Cyclopts-to-contract exit-code
  translation rather than each command. Rationale: Cyclopts exits 1 on usage
  errors but the contract demands 2; centralising the translation is the only
  way five commands share it "without renegotiating it" (roadmap 1.1.3 success
  criterion). Date/Author: 2026-06-22, planning agent.
- Decision (round-2, B1): construct the app with
  `result_action="return_value"` and let the wrapper own every `sys.exit` and
  envelope emission. Rationale: the default
  `result_action="print_non_int_sys_exit"` calls `sys.exit()` on the body's
  return value inside `App.__call__` (packaging.html "Result Action": int →
  `sys.exit(int)`, None → `sys.exit(0)`), so the wrapper's success-path envelope
  emission after `app(...)` would never run. `"return_value"` is a documented
  built-in mode (api.html `App.result_action`: "returns the command's value
  unchanged") and returns control to the wrapper. A custom `result_action`
  callable (`def handler(result)`) was the alternative but spreads exit logic
  across two sites; `"return_value"` keeps it in one place. `result_action` is
  added to the interface allow-list and the Work item 1 tripwire. Date/Author:
  2026-06-22, planning agent.
- Decision (round-2, B4): do NOT add `pytest-bdd` or a `tests/features` /
  `tests/steps` behavioural suite for this module. Rationale: design §9 scopes
  behavioural (`pytest-bdd`) tests to concrete commands' harness-facing flows
  (a stale `compiled.md` caught by `novel-done`; an out-of-order
  `advance-phase` refused; a knitting gate at threshold) and assigns the
  exit-code contract itself to "CLI error-path tests", explicitly stating the
  simpler surfaces need "only snapshot coverage ... not a property-based or
  behavioural suite of their own". §9 even pins the 1-versus-4 distinction to
  `novel-done`, not to this scaffolding module. Adding the project's first
  `pytest-bdd` harness here would be asserted, not derived, and would trip this
  plan's own Tolerances ("fourth dependency / unjustified scope"). The 1-vs-4
  harness meaning is instead asserted by the CLI error-path tests §9 mandates
  (Work item 4: code 1 != code 4, each with `ok: false`) plus the Hypothesis
  property (Work item 5). Date/Author: 2026-06-22, planning agent.
- Decision (round-2, B2/B3): pin exact locked versions for the Cyclopts
  tripwire and the new dev deps, matching `tests/test_tomlkit_dependency.py`'s
  `LOCKED_TOMLKIT_VERSION` single-source-of-truth tripwire. Rationale: the
  reviewer's round-1 B2/B3 finding is that a presence-only or probe-only check
  lets a silent `uv` re-resolution drift the version and break the contract
  while `make all` stays green. The committed tripwires pin
  `LOCKED_CYCLOPTS_VERSION = "4.18.0"`, `LOCKED_HYPOTHESIS_VERSION`, and
  `LOCKED_SYRUPY_VERSION` to the versions `uv.lock` resolves (read off the lock
  after `make build`), so any drift fails loudly. Date/Author: 2026-06-22,
  planning agent.

- Decision (implementation, 2026-06-22, Work item 4): the `run` signature is
  `run(app, argv, context: RunContext) -> NoReturn`, where `RunContext` is a
  frozen `kw_only` dataclass bundling `command`, `working_dir`, and `human`.
  Command bodies return a frozen `CommandOutcome(code, result, messages)` and
  `run` builds the envelope from it. Rationale: the plan's indicative signature
  (`human_flag_seen`, `body`) plus a `working_dir` parameter would have given
  `run` five positional-ish parameters and tripped Ruff/Pylint
  `too-many-arguments` (the project caps at 4); bundling the per-invocation
  context into one dataclass keeps the call ergonomic, keeps every exit decision
  in `run`, and preserves the observable contract
  (`result_action="return_value"`, the 2/3/0/1/4 mapping, machine-default /
  `--human`-switch). `RunContext` and `CommandOutcome` are added to the public
  surface. Date/Author: 2026-06-22, implementation agent.

## Outcomes & retrospective

Completed 2026-06-22. All six work items landed as atomic commits, each with
`make all` green (plus `make markdownlint` and `make nixie` for Work item 6's
markdown changes) and coderabbit reporting 0 findings on every run. The property
test asserts the ok/exit-code biconditional (confirmed non-vacuous by a local
inversion that failed with a shrunk counter-example before being reverted) and
the five-code semantics; the five per-code machine-mode snapshots plus the
success human/machine snapshots are stable; the developers' guide documents the
module and its `result_action="return_value"` / exit-`2` translation rules and
the `StateInputError`→exit-`3` channel.

Friction and lessons for future slices:

- Two of the round-2 plan's Cyclopts claims did not reproduce against the locked
  `cyclopts==4.18.0` and were adapted (recorded in Surprises and the Work item 1
  tripwire): under `exit_on_error=False`, `--help`/`--version` return `None`
  rather than raising `SystemExit`, and an unknown subcommand raises
  `UnknownCommandError` only when the app has no catch-all `@app.default`. The
  wrapper therefore treats a non-`CommandOutcome` return as the help/version
  path (exit `0`, no envelope) and the five real commands must register named
  subcommands (or accept that a catch-all default routes unknown subcommands to
  the body).
- The `run` signature was reshaped to `run(app, argv, context: RunContext)` to
  stay within the project's 4-argument cap; command bodies return a
  `CommandOutcome`. Future command slices adopt these two value types.
- The project gitignores `.hypothesis/`, so the failing-seed database is not
  checked in; the property is instead defended by the deliberate-inversion check
  noted above. No `pytest-bdd` suite was added (design §9 / round-2 B4).

## Documentation to read, and skills to load, before starting

Read first (source of truth):

- `docs/novel-ralph-harness-design.md` §3.1 (output modes / envelope), §3.2
  (exit codes), §3.3 (checker/mutator segregation, for context), §9
  (verification strategy — which test method each command earns).
- `docs/adr-003-shared-interface-contract.md` in full (the contract this task
  implements; Table 2 is the exit-code table).
- `docs/developers-guide.md` "The shared JSON envelope" and "Disambiguated exit
  codes" sections (lines 108-135).
- `docs/scripting-standards.md` (Cyclopts conventions; cuprum is NOT needed
  here — see "What this task does NOT do").
- `AGENTS.md` (quality gates lines 71-98; testing rules lines 141-166; file
  size lines 24-27; spelling lines 18-20).

External library docs (verified during planning round 2, cite when implementing
the wrapper):

- Cyclopts v4.18.0 `packaging.html` "Result Action"
  (`https://cyclopts.readthedocs.io/en/v4.18.0/packaging.html`): the default
  `result_action="print_non_int_sys_exit"` behaviour (int → `sys.exit(int)`,
  None → `sys.exit(0)`, bool → 0/1, str → print then exit 0) and the custom
  `result_action` callable signature `def handler(result)`.
- Cyclopts v4.18.0 `api.html` `App.result_action`
  (`https://cyclopts.readthedocs.io/en/v4.18.0/api.html`): the built-in mode
  `"return_value"` ("returns the command's value unchanged"), used by the
  wrapper so `app(...)` returns control instead of exiting.
- Cyclopts `app_calling.html` "Exception Handling and Exiting": `exit_on_error`
  defaults `True` → `sys.exit(1)` on a Cyclopts runtime error; `print_error`
  default `True`; under `exit_on_error=False` the `CycloptsError` subclass is
  raised for the caller to handle.

Skills to load (via the Skill tool / routers):

- `python-router` first, then the sub-skills it routes to:
  - `python-data-shapes` for the envelope dataclass choice.
  - `python-types-and-apis` for the public function signatures and the
    exit-code enum.
  - `python-errors-and-logging` for catching `CycloptsError` narrowly and the
    state-error path.
  - `python-testing` for fixture scopes, parametrization, and snapshot/syrupy
    usage.
  - `python-verification` to confirm Hypothesis is the right adversary for the
    ok/exit-code property (it is: an invariant over a range of codes), then
    `hypothesis` for writing the property test.
- `en-gb-oxendict` for prose, comments, and commit messages.
- `leta` for navigation (`leta show`, `leta refs`, `leta grep`) and `sem` for
  history.

CrossHair and mutmut are NOT required for this task: the contract surface is a
small, total mapping with a single property already covered by Hypothesis;
`python-verification` would route symbolic execution or mutation testing only
if coverage holes or weak assertions remained, which the planned property plus
snapshots close. (If the implementer finds the property test passes
vacuously, escalate and reconsider mutmut per the mutmut skill.)

## Plan of work

The work proceeds in six atomic, independently committable, gate-passable work
items. Each ends with `make all` green (and, where markdown changes, with
`make markdownlint` and `make nixie` green). Run gates sequentially, never in
parallel, to benefit from build caching (user instruction).

### Work item 1: commit a Cyclopts version+behaviour tripwire test

Purpose (round-2 B2): the entire usage-error→`2` contract and the
success-path envelope emission rest on three Cyclopts v4.18.0 behaviours. A
throwaway probe does not protect them: a future `uv` re-resolution that bumps
Cyclopts or changes a default would pass `make all` silently and break the
harness at runtime. So this work item commits a *tripwire* test that pins the
locked version and the load-bearing behaviour, exactly as
`tests/test_tomlkit_dependency.py` pins `LOCKED_TOMLKIT_VERSION = "0.15.0"` plus
a round-trip. Read that file first to match its style and docstring shape.

Steps:

1. `make build` to create `.venv` and sync the dev group.
2. Read the resolved Cyclopts version from `uv.lock` (it is `4.18.0` today) and
   set `LOCKED_CYCLOPTS_VERSION` to it.
3. Write `tests/test_cyclopts_contract.py` (an in-tree pytest module; tests live
   only under top-level `tests/`, AGENTS.md). It builds a small throwaway
   `cyclopts.App(result_action="return_value", exit_on_error=False,
   print_error=False, help_on_error=False)` with one trivial command and
   asserts:
   - `cyclopts.__version__ == LOCKED_CYCLOPTS_VERSION` (the re-resolution
     tripwire; bump in lockstep with a deliberate upgrade).
   - Calling the app with an unknown subcommand, an unknown option, and a
     missing required argument each raises a subclass of
     `cyclopts.exceptions.CycloptsError` (assert with `pytest.raises`), rather
     than calling `sys.exit`, because `exit_on_error=False`.
   - `print_error=False, help_on_error=False` suppresses the Rich panel: capture
     stderr with `capsys` and assert it is empty on the raised error.
   - `--help` and `--version` exit `0` (assert via `pytest.raises(SystemExit)`
     and `excinfo.value.code == 0`).
   - With `result_action="return_value"`, calling the app on a valid invocation
     whose body returns a sentinel object **returns that object to the caller**
     (assert the return value `is` the sentinel) and does **not** call
     `sys.exit`. This is the B1 guarantee the wrapper depends on: control comes
     back so the wrapper can emit the envelope.
4. If any assertion does not hold against the locked Cyclopts, STOP and escalate
   (Tolerances: Cyclopts) before writing the wrapper — the plan's mechanism is
   wrong and an ADR/plan revision is needed, not a workaround.

Tests to add: `tests/test_cyclopts_contract.py` (the tripwire above). It fails
if the locked Cyclopts version drifts or any pinned behaviour changes.

Validation: `make all`. Commit (this is a real, committed test, not a probe).

Docs/skills: `python-testing` (`pytest.raises`, `capsys`); scripting-standards
(Cyclopts); the Cyclopts v4.18.0 doc pages listed above; `leta` for navigation.

### Work item 2: add the two test dependencies and pin them

Purpose: the success criteria require a property test (Hypothesis) and per-code
snapshots (syrupy). Add exactly these two dev dependencies once, here, so later
work items can use them. `pytest-bdd` is deliberately excluded (round-2 B4; see
Decision Log): design §9 assigns the exit-code contract to "CLI error-path
tests", not a behavioural suite, for a scaffolding module like this one.

Edits:

- `pyproject.toml` `[dependency-groups].dev`: add `"hypothesis"` and `"syrupy"`
  (alphabetical insertion to keep the list tidy). These are dev-only; the
  runtime `dependencies` list (line 8) is untouched. Do NOT add `pytest-bdd`.

Tests to add:

- `tests/test_contract_test_deps.py`: a guard that, for each of `hypothesis`
  and `syrupy`, (a) imports the package, (b) asserts its `__version__` equals a
  module-level `LOCKED_*_VERSION` constant set to the version `uv.lock`
  resolves, and (c) asserts the dependency is declared in
  `[dependency-groups].dev` (read `pyproject.toml` with `tomllib`). This mirrors
  the **load-bearing** element of `tests/test_tomlkit_dependency.py` — the exact
  version pin (`LOCKED_TOMLKIT_VERSION = "0.15.0"`) acting as a re-resolution
  tripwire, not merely a presence check (round-2 B3). Read that file first to
  match style. Obtain the locked versions by reading `uv.lock` after `make
  build` (or `<pkg>.__version__` from the synced venv) and hard-code them as the
  pins; a silent drift then fails the guard, a deliberate bump updates it
  visibly. If `syrupy` does not expose `__version__`, pin via
  `importlib.metadata.version("syrupy")` instead and note it in the test
  docstring.

Validation: `make build` (proves uv resolves the new deps under Python 3.14),
then `make all`. Commit.

Docs/skills: `python-testing`; `leta refs` to find the existing dependency
guard.

### Work item 3: the envelope data type, exit-code enum, and renderers

Purpose: deliver the envelope frame and both renderings as pure, side-effect-
free helpers (command/query segregation, AGENTS.md).

New package `novel_ralph_skill/contract/`:

- `exit_codes.py`: an `enum.IntEnum` named `ExitCode` with members
  `SUCCESS = 0`, `BENIGN_NEGATIVE = 1`, `USAGE_ERROR = 2`, `STATE_ERROR = 3`,
  `ACTIONABLE_FINDING = 4`, each documented with its §3.2 meaning. Because it
  subclasses `int`, the value is the process exit code directly. Add a helper
  `is_ok(code: ExitCode) -> bool` returning `code is ExitCode.SUCCESS` so the
  ok/code biconditional has one home.
- `envelope.py`: a frozen
  `@dataclass(frozen=True, kw_only=True)` named `Envelope` with fields, in the
  fixed order, `command: str`, `schema_version: int`, `ok: bool`,
  `working_dir: str`, `result: Mapping[str, object]`, `messages: Sequence[str]`.
  Add `ENVELOPE_SCHEMA_VERSION: int = 1` module constant. Provide a constructor
  helper `build_envelope(*, command, working_dir, code, result, messages)` that
  derives `ok` from `is_ok(code)` (so callers cannot set `ok` inconsistently)
  and validates `command in COMMAND_NAMES` (import from
  `novel_ralph_skill.commands.names`), raising a `ValueError` otherwise.
  Provide `render_machine(env) -> str` returning `json.dumps(...)` with the
  fields serialised in contract order (build an explicit ordered dict; do not
  rely on dataclass field order leaking through), and
  `render_human(env) -> str` returning a readable multi-line rendering that
  shows `ok`, the working dir, and each message on its own line, omitting raw
  `result` JSON (messages are the human channel per §3.1).

Tests to add (`tests/test_contract_envelope.py`):

- Unit: `build_envelope` sets `ok=True` only for `ExitCode.SUCCESS` and
  `ok=False` for each non-zero code (parametrized over all five codes).
- Unit: `build_envelope` rejects a `command` outside `COMMAND_NAMES` with
  `ValueError`.
- Unit: `render_machine` emits the six keys in the fixed order and round-trips
  through `json.loads` to a dict whose `ok` equals `is_ok(code)`.
- Unit: `render_human` writes each message on its own line and does not embed
  the JSON `result` payload.
- Snapshot (syrupy): one `render_machine` snapshot for a representative
  success envelope and one `render_human` snapshot, with `working_dir`
  normalised to the literal token `"working"` (no absolute paths) so the
  snapshot is stable (AGENTS.md lines 148-158). Pair each with a semantic
  assertion as above. (The full per-code snapshot matrix lands in Work item 5,
  alongside the property test, to keep this item focused on rendering.)

Validation: `make all`. Commit.

Docs/skills: `python-data-shapes` (dataclass choice), `python-types-and-apis`
(IntEnum and signatures), `python-testing` + syrupy usage. `leta show
COMMAND_NAMES` to confirm the import path.

### Work item 4: the `run` wrapper and exit-code mapping

Purpose: centralise the Cyclopts-to-contract translation so usage errors exit
`2`, state/input errors exit `3`, and the command body's own result decides
`0`/`1`/`4` — the single shared plumbing the five commands reuse.

New `novel_ralph_skill/contract/runner.py`:

- A sentinel exception `StateInputError(Exception)` a command body raises to
  signal a state/input fault (e.g. missing or unparseable `state.toml`, absent
  working dir). Document that this is the contract's exit-`3` channel
  (design §3.2; §10 failure modes). Give it an optional `messages` payload so
  the envelope can carry human prose.
- `run(app: cyclopts.App, *, command: str, human_flag_seen, body) -> NoReturn`
  is the wrapper. Define its exact responsibilities:
  - **`result_action` is the crux (round-2 B1).** The app MUST be built with
    `result_action="return_value"` (a documented v4.18.0 built-in mode that
    "returns the command's value unchanged"; see "Documentation to read"). The
    default `"print_non_int_sys_exit"` would call `sys.exit()` on the body's
    return value *inside* `App.__call__`, so any wrapper code after `app(...)`
    that emits the success/benign/actionable envelope would never run. With
    `"return_value"`, `app(...)` returns the body's value to the wrapper, which
    then owns every `sys.exit` and every envelope emission. The wrapper builds
    the app (or asserts the caller passed one) configured as
    `result_action="return_value", exit_on_error=False, print_error=False,
    help_on_error=False` — the first returns control on success, the rest make
    Cyclopts raise rather than exit `1` and suppress its Rich panel (all four
    pinned by the Work item 1 tripwire).
  - On `cyclopts.exceptions.CycloptsError`: emit a usage-error envelope
    (`ExitCode.USAGE_ERROR`) to stdout in the active mode, diagnostics to
    stderr, and `sys.exit(2)`.
  - On `StateInputError`: emit a state-error envelope
    (`ExitCode.STATE_ERROR`) and `sys.exit(3)`.
  - On a normal return carrying an `ExitCode` from the body (success / benign
    negative / actionable finding): because `result_action="return_value"`
    handed the value back, build the envelope from that `ExitCode`, emit it, and
    `sys.exit(int(code))`, so `0`/`1`/`4` flow through unchanged.
  - `--help`/`--version` are handled by Cyclopts and exit `0` before the body
    runs; they are exempt from the envelope (matching the existing stub note in
    `novel_ralph_skill/commands/stub.py`). The wrapper must not emit an envelope
    for them — pinned by a test (round-1 A2).
  - The signature above is indicative; the implementer may shape the `body`
    callable and the `--human` plumbing to fit Cyclopts's `App.meta` /
    global-flag idiom, provided `result_action="return_value"`, the exit-code
    mapping, and the machine-mode-default / `--human`-switch behaviour hold. If
    a cleaner Cyclopts idiom (e.g. a `meta` callback owning `--human`) is found
    during implementation, record it in the Decision Log; do not change the
    observable contract or drop `result_action="return_value"`.

Tests to add:

- `tests/test_contract_runner.py` (CLI error-path, design §9 "CLI error-path
  tests" — the method §9 mandates for the exit-code contract): drive a minimal
  app through `run` and assert:
  - unknown subcommand → exit `2`, machine envelope on stdout with `ok: false`
    and `command` set;
  - bad/missing required argument → exit `2`;
  - a body raising `StateInputError` → exit `3`, envelope `ok: false`;
  - a body returning `ExitCode.SUCCESS` → exit `0`, envelope `ok: true` (this is
    the success path that only runs because `result_action="return_value"`
    returned control — the B1 regression guard);
  - a body returning `ExitCode.BENIGN_NEGATIVE` → exit `1`;
  - a body returning `ExitCode.ACTIONABLE_FINDING` → exit `4`;
  - **the 1-versus-4 harness meaning (round-2 B4):** assert that the benign
    negative and actionable finding produce *different* exit codes (`1` != `4`)
    and that both carry `ok: false` but are not interchangeable — the
    harness-meaning §9 assigns to the CLI error-path tests for this module,
    asserted here rather than via a pytest-bdd suite (see Decision Log);
  - `--help` and `--version` → exit `0` with **no** envelope on stdout (round-1
    A2: the exemption is a tested boundary, not an assumption);
  - the `--human` flag switches stdout to the human rendering while keeping the
    same exit code (assert the human text, not the JSON).
  Capture exit via `pytest.raises(SystemExit)` and `capsys` for stdout/stderr.

No behavioural (`pytest-bdd`) suite is added for this module — design §9 scopes
that to concrete commands' harness-facing flows and assigns the exit-code
contract to the CLI error-path tests above (round-2 B4; Decision Log).

Validation: `make all`. Commit.

Docs/skills: `python-errors-and-logging` (narrow `except CycloptsError`,
`raise ... from`), `python-testing` (capsys, `pytest.raises`),
`hypothesis`/`python-verification` not yet (property test is Work item 5).

### Work item 5: the ok/exit-code property test and per-code envelope snapshots

Purpose: deliver the roadmap success criterion's property test and the
per-code snapshot matrix.

Tests to add (`tests/test_contract_properties.py`):

- Hypothesis property over `ExitCode` (use `st.sampled_from(list(ExitCode))`):
  for any code, `build_envelope(...).ok is (code is ExitCode.SUCCESS)`. This is
  the ok/exit-code biconditional. Generate `command` from
  `st.sampled_from(COMMAND_NAMES)` and `messages` / `result` from small
  strategies. **No function-scoped fixture inside `@given`** (Hypothesis
  Compatibility docs: that raises `HealthCheck.function_scoped_fixture`); build
  all inputs from strategies.
- Hypothesis property asserting the four non-zero codes all yield `ok: false`
  and are pairwise distinct in meaning: assert `BENIGN_NEGATIVE != USAGE_ERROR
  != STATE_ERROR != ACTIONABLE_FINDING` as integers and that `1` and `4` are
  not interchangeable (a test that would fail if someone collapsed them).
- Semantic mapping assertions (plain `pytest`, not Hypothesis, for the
  example-specific cases the roadmap names): a malformed invocation maps to
  code `2`; an unparseable/missing `state.toml` (modelled via
  `StateInputError`) maps to code `3`. These reuse the `run` wrapper from Work
  item 4.

Snapshots to add (`tests/test_contract_envelope_snapshots.py`, syrupy):

- One `render_machine` snapshot per `ExitCode` (five snapshots), parametrized
  over the codes, with `working_dir` normalised to the fixed token `"working"`.
  (The envelope has no timestamp and no other path field, so there is nothing
  else to redact — round-1 A1.) "A snapshot pins the envelope shape for each
  code" (roadmap 1.3.1
  success criterion). Pair each with a semantic assertion that the parsed JSON
  `ok` matches the code, so the snapshot is not the only guard (AGENTS.md
  "avoid snapshot-only coverage").

Validation: `make all`. Confirm the property test does not pass vacuously by
temporarily inverting the biconditional locally and seeing it fail (then
revert); note the check in `Surprises & Discoveries` if anything is off. Commit.

Docs/skills: `python-verification` (confirm Hypothesis is right), `hypothesis`
(strategy design, the function-scoped-fixture trap, settings), `python-testing`
(syrupy parametrized snapshots).

### Work item 6: document the module and reify the roadmap checkbox

Purpose: keep the living docs current (AGENTS.md "Documentation maintenance").

Edits:

- `docs/developers-guide.md`: under "The shared JSON envelope" / "Disambiguated
  exit codes", add a short paragraph naming the new module
  (`novel_ralph_skill/contract/`), its public surface (`Envelope`,
  `build_envelope`, `render_machine`, `render_human`, `ExitCode`,
  `StateInputError`, `run`), and the rule that new commands adopt `run` rather
  than calling their `App` directly. State plainly that (a) the wrapper builds
  the app with `result_action="return_value"` so it — not Cyclopts — owns exit
  and envelope emission, and (b) it translates Cyclopts's native exit-`1` usage
  errors to the contract's exit `2`. Note for later slices (round-1 A3): a
  refused mutator request is the contract's exit `3`, never `1` (§3.2/§3.4);
  `StateInputError` is the channel a command body uses to signal that, so the
  wrapper maps it to `3`.
- `docs/roadmap.md`: change `- [ ] 1.3.1.` to `- [x] 1.3.1.` only after Work
  items 2-5 are merged and green (do this in the final commit of the task).
- If any new convention emerges (e.g. the `StateInputError` channel), record it
  in the developers' guide, not only in code.

Validation: `make markdownlint` and `make nixie` (markdown changed), then
`make all`. Commit.

Docs/skills: `en-gb-oxendict`; documentation-style-guide.

## Concrete commands

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-1`.

```bash
make build        # create .venv, sync dev group (Work item 1 & 2)
make all          # build check-fmt lint typecheck test (every work item)
make markdownlint # markdown lint (Work items touching .md)
make nixie        # Mermaid validation (Work items touching .md)
```

Expected: `make all` ends with pytest reporting all tests passed (the new
`test_contract_*` modules among them) and `interrogate` reporting 100%
coverage. A new contract test fails before its production code exists and
passes after (red/green), e.g. `tests/test_contract_envelope.py` fails before
Work item 3's module lands.

## Validation and acceptance

Acceptance is behavioural:

- Building an envelope for each `ExitCode` and rendering it in machine mode
  produces JSON whose `ok` is `true` exactly when the code is `0`; the
  Hypothesis property in `tests/test_contract_properties.py` asserts this for
  all five codes and fails before the biconditional is implemented.
- Driving the `run` wrapper with an unknown subcommand exits `2` (not Cyclopts's
  default `1`) and emits a machine envelope with `ok: false`; a body raising
  `StateInputError` exits `3`; success / benign-negative / actionable-finding
  bodies exit `0` / `1` / `4` respectively (the `0`/`1`/`4` path only runs
  because the app uses `result_action="return_value"`, returning control to the
  wrapper); `--help`/`--version` exit `0` with no envelope; `--human` switches
  the stdout rendering while preserving the exit code. The CLI error-path tests
  (Work item 4) assert the harness meaning of the 1-vs-4 split (`1` != `4`,
  both `ok: false`, not interchangeable) — design §9 assigns this distinction to
  CLI error-path tests, not a behavioural suite.
- Five per-code machine-mode snapshots and a human-mode snapshot exist and are
  stable across reruns; each is paired with a semantic assertion.

Quality criteria ("done"):

- Tests: `make test` passes; the new property test fails before and passes
  after Work item 5; the new CLI error-path tests fail before and pass after
  Work item 4.
- Lint/format/type: `make check-fmt`, `make lint` (Ruff + interrogate 100% +
  PyPy-Pylint), `make typecheck` all green.
- Audit: `make audit` clean.
- Markdown: `make markdownlint` and `make nixie` green for the doc commits.

Quality method: `make all` (plus the two markdown targets for doc commits),
run sequentially.

## Idempotence and recovery

Every work item is additive and re-runnable. `make build` is safe to repeat
(`uv sync`). If a gate fails mid-item, fix forward and re-run `make all`; no
step is destructive. The roadmap checkbox flip (Work item 6) is the only edit
to an existing doc line and is trivially reversible. If a tolerance triggers,
stop and escalate per the execplans skill's exception handling.

## Interfaces and dependencies

Use these and only these:

- Standard library: `dataclasses`, `enum.IntEnum`, `json`, `sys`,
  `collections.abc` (for `Mapping`/`Sequence`), `typing`.
- `cyclopts` (4.18.0, already a runtime dep) for the `App`, constructed with
  **`result_action="return_value"`** (so `app(...)` returns the body value to
  the wrapper instead of `sys.exit`-ing — the B1 fix), plus
  `exit_on_error=False, print_error=False, help_on_error=False`, and
  `cyclopts.exceptions.CycloptsError` for the usage-error catch. The
  `"return_value"` mode is a documented v4.18.0 built-in (api.html
  `App.result_action`).
- `novel_ralph_skill.commands.names.COMMAND_NAMES` to validate the `command`
  field (single source of truth).
- Dev/test: `pytest`, `pytest-xdist`, `pytest-timeout` (already present), plus
  new `hypothesis` and `syrupy` only. NOT `pytest-bdd` (round-2 B4).

End-state public surface (in `novel_ralph_skill/contract/`):

```python
# exit_codes.py
class ExitCode(enum.IntEnum):
    SUCCESS = 0
    BENIGN_NEGATIVE = 1
    USAGE_ERROR = 2
    STATE_ERROR = 3
    ACTIONABLE_FINDING = 4

def is_ok(code: ExitCode) -> bool: ...

# envelope.py
ENVELOPE_SCHEMA_VERSION: int = 1

@dataclass(frozen=True, kw_only=True)
class Envelope:
    command: str
    schema_version: int
    ok: bool
    working_dir: str
    result: cabc.Mapping[str, object]
    messages: cabc.Sequence[str]

def build_envelope(*, command: str, working_dir: str, code: ExitCode,
                   result: cabc.Mapping[str, object],
                   messages: cabc.Sequence[str]) -> Envelope: ...
def render_machine(env: Envelope) -> str: ...
def render_human(env: Envelope) -> str: ...

# runner.py
class StateInputError(Exception): ...

# The `app` passed in MUST be built with result_action="return_value",
# exit_on_error=False, print_error=False, help_on_error=False (the wrapper may
# construct or assert this). result_action="return_value" is load-bearing: it
# returns the body value to `run` so `run` owns all sys.exit + envelope
# emission (round-2 B1).
def run(app: cyclopts.App, *, command: str, ...) -> typ.NoReturn: ...
```

The `run` signature's trailing parameters are indicative; fix them during Work
item 4 to fit Cyclopts's `--human` idiom, recording the choice in the Decision
Log without altering the observable exit-code contract or dropping
`result_action="return_value"`.

## Revision note (2026-06-22, planning round 2)

What changed and why, in response to the round-1 Logisphere review
(`docs/execplans/roadmap-1-3-1.review-r1.md`):

- **B1 (result_action control-flow gap).** The wrapper now explicitly builds the
  Cyclopts app with `result_action="return_value"`, a documented v4.18.0
  built-in mode (verified against `api.html` and `packaging.html`) that returns
  the body value to the caller instead of `sys.exit`-ing inside `App.__call__`.
  This is added to the Orientation pinning, the Risks, the Decision Log, Work
  item 4's responsibilities, the acceptance criteria, the interface allow-list,
  and the Work item 1 verification probes. The `0`/`1`/`4` success-path envelope
  emission now has a defined mechanism.
- **B2 (load-bearing Cyclopts behaviour unpinned).** Work item 1 no longer
  produces a throwaway probe; it commits `tests/test_cyclopts_contract.py`, a
  version+behaviour tripwire pinning `LOCKED_CYCLOPTS_VERSION = "4.18.0"`, the
  `CycloptsError`-under-`exit_on_error=False` behaviour, panel suppression,
  `--help`/`--version`→0, and that `result_action="return_value"` returns
  control. This mirrors `tests/test_tomlkit_dependency.py`.
- **B3 (dependency guard weakened the cited pattern).** Work item 2's guard now
  pins exact locked versions (`LOCKED_HYPOTHESIS_VERSION`,
  `LOCKED_SYRUPY_VERSION`) read off `uv.lock`, not just presence, matching the
  tomlkit tripwire it cites.
- **B4 (pytest-bdd added without a §9 mandate).** `pytest-bdd` and the
  `tests/features` / `tests/steps` behavioural suite are dropped. Design §9
  assigns the exit-code contract to CLI error-path tests and scopes behavioural
  suites to concrete commands; the 1-vs-4 harness meaning is now asserted by the
  Work item 4 CLI error-path tests plus the Work item 5 Hypothesis property. The
  dependency count drops from three to two and the Tolerances and interface list
  are updated accordingly.
- Non-blocking A1 (snapshot redaction named non-existent fields) and A2
  (`--help`/`--version` exemption unpinned) are also resolved: redaction is
  limited to normalising `working_dir`, and a `--help`/`--version`→0-with-no-
  envelope test is added to Work item 4. A3 (mutator-refusal→3 note) is folded
  into the Work item 6 developers-guide update.

Effect on remaining work: the work-item count is unchanged (six), but Work item
1 now yields a committed test, Work item 2 adds two deps not three, and Work
item 4 fixes `result_action="return_value"` as a hard requirement. No new
ambiguities; all load-bearing Cyclopts claims are now verified-and-cited and
pinned by the Work item 1 tripwire.
