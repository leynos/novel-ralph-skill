# Logisphere adversarial design review — roadmap 1.3.1 ExecPlan (Round 1)

Reviewer: Logisphere crew (adversarial). Date: 2026-06-22.
Subject: `docs/execplans/roadmap-1-3-1.md` (Status: DRAFT).
Verdict: **REVISE** — blocking design defects must be resolved before implementation.

Sources consulted: `docs/adr-003-shared-interface-contract.md`,
`docs/novel-ralph-harness-design.md` §3.1/§3.2/§3.3/§9/§10,
`docs/developers-guide.md`, `AGENTS.md`, `pyproject.toml`, `uv.lock`,
`novel_ralph_skill/commands/{names.py,stub.py}`,
`tests/test_tomlkit_dependency.py`, cuprum sibling at `/data/leynos/Projects/cuprum`,
and Cyclopts v4.18.0 official docs (app_calling, packaging — firecrawl).

## Blocking defects

### B1 (Telefono / Pandalump) — `result_action` is unaddressed; the wrapper's success/benign/actionable path cannot run as designed

The plan's `run` wrapper (Work item 4) says: on a normal return carrying an
`ExitCode` from the body, "emit the envelope and exit with that code's integer
value, so 0/1/4 flow through unchanged." This is structurally impossible with a
default Cyclopts `App`. Per the official v4.18.0 docs (packaging.html, "Result
Action"), `App` defaults to `result_action="print_non_int_sys_exit"`, under
which **"Integer returns are passed to `sys.exit(int)`"** and **"`None` returns
call `sys.exit(0)`"**. `App.__call__` therefore calls `sys.exit()` on the body's
return value *itself*; any wrapper code positioned after `app(...)` to build and
emit the contract envelope never executes for the 0/1/4 paths. The plan never
mentions `result_action`, and it is absent from the "Interfaces and
dependencies" allow-list. The wrapper must either set
`result_action="return_value"` (and then own all exit + envelope emission) or
emit the envelope from a custom `result_action` callback / the body itself. As
written, the central mechanism of the task — emitting the envelope on the
success path — is undefined. Fix: specify the `result_action` strategy
explicitly in Work item 4 and the interface list, and add it to the Work item 1
verification probes.

### B2 (Doggylump / Dinolump) — the load-bearing Cyclopts behaviour is never pinned by a committed test

Work item 1 verifies the Cyclopts exit-code/exception behaviour "in-process"
and explicitly "produces no commit unless the plan is corrected." The entire
contract (usage error -> 2, panel suppression, `CycloptsError` subclasses) rests
on this behaviour, yet nothing in the suite pins it. A future `uv` re-resolution
that changes Cyclopts's defaults (e.g. the `result_action` protocol, or the
exit-on-error code) would pass `make all` silently and break the harness
contract at runtime. The established project pattern is a committed tripwire
test that pins the exact locked version and behaviour — see
`tests/test_tomlkit_dependency.py` (`LOCKED_TOMLKIT_VERSION = "0.15.0"` plus
round-trip assertions). The plan must add a committed CLI/behaviour test that
locks the Cyclopts contract (raises `CycloptsError` subclass under
`exit_on_error=False`; `--help`/`--version` exit 0; chosen `result_action`
returns control), not a throwaway probe. (Per the review brief, uncited
memory-based locked-library claims are blocking unless verified-and-cited OR
pinned by a test; the docs verification is now done — see References — but the
pin is still required.)

### B3 (Pandalump / Telefono) — the new dependency-guard test weakens the established pattern it claims to mirror

Work item 2's `tests/test_contract_test_deps.py` only asserts each dep "imports
successfully and is declared in `[dependency-groups].dev`." It claims to mirror
`tests/test_tomlkit_dependency.py`, but that file's load-bearing element is an
exact version pin (`LOCKED_TOMLKIT_VERSION`) acting as a re-resolution
tripwire, plus a behavioural round-trip. A presence-only guard does not pin the
versions of `hypothesis`/`syrupy`/`pytest-bdd`, so a silent version drift in any
of them passes the guard. Either pin the locked versions (matching the tomlkit
tripwire) or state explicitly why these dev deps do not warrant a pin —
silently diverging from the cited pattern is a single-source-of-truth /
consistency defect.

### B4 (Wafflecat / Dinolump) — `pytest-bdd` is added but design §9 does not assign a behavioural suite to this scaffolding module

The plan adds `pytest-bdd` as a "needed" dependency and Work item 4 writes
`tests/features/contract_exit_codes.feature`. But design §9 scopes behavioural
tests to "the harness-facing flows" of concrete commands (stale `compiled.md`
caught by `novel-done`; out-of-order `advance-phase` refused; knitting gate at
threshold) and scopes the exit-code contract itself to "CLI error-path tests,"
not pytest-bdd. §9 also states the simpler surfaces need "only snapshot coverage
... not a property-based or behavioural suite of their own." Adding the project's
first pytest-bdd harness, its `tests/features` + `tests/steps` layout, and the
dependency — for a contract-frame module §9 does not name as earning one — is
scope the plan asserts rather than derives. Either cite where §9/ADR-003
requires a behavioural suite for this module, or drop pytest-bdd from this task
(the 1-vs-4 harness-meaning can be asserted by the CLI error-path tests §9 does
mandate, plus the Hypothesis property). As written this risks tripping the
Tolerances' own "fourth dependency / unjustified scope" tripwire.

## Non-blocking findings

### A1 (Buzzy Bee) — snapshot redaction names fields the envelope does not have

Risks/Work-item-5 call for redacting "timestamp" and "absolute path" fields.
The envelope (§3.1) has no timestamp field, and `working_dir` is already the
literal token `"working"` in the design's own example. Harmless, but the
redaction guidance should match the actual envelope shape (normalize
`working_dir`; there is no timestamp to redact) so the implementer does not
invent fields.

### A2 (Telefono) — `--help`/`--version` exempt-from-envelope claim is plausible but unpinned

The plan asserts `--help`/`--version` exit 0 and are "exempt from the envelope."
The official docs confirm these exit 0 by default, but the plan should pin this
in the Work item 4 CLI tests (assert exit 0 and that no envelope is emitted) so
the exemption is a tested boundary, not an assumption.

### A3 (Dinolump) — `is_ok(code)` vs the §3.2 mutator-refusal nuance

`is_ok` returns `code is ExitCode.SUCCESS`; correct for the ok/exit-code
biconditional. Note for later slices (not this task): §3.2/§3.4 fix that a
refused mutator request is exit 3, never 1 — the `run` wrapper's `StateInputError`
channel is the right home for that, and the developers-guide update (Work item
6) should say so, which it already gestures at. No change required here beyond
keeping that note.

## Confirmed-sound aspects (not defects)

- "No cuprum" is correct: cuprum is a subprocess catalogue (`catalogue.py`,
  `sh.py`); this module shells out to nothing and design §9 confirms v1 commands
  touch only the filesystem. cuprum is rightly absent.
- "msgspec is banned-from-import but unlocked" is accurate (`uv.lock` has zero
  msgspec entries; Ruff bans the `from` form only). The stdlib
  `dataclasses`+`json` choice is sound and avoids a new runtime dep.
- Cyclopts exit-code claims (default exit 1 on runtime error; `exit_on_error`,
  `print_error`, `help_on_error` kwargs; `CycloptsError` subclasses raised under
  `exit_on_error=False`) are confirmed against the official v4.18.0 docs.
- The envelope field set/order, the ok-mirrors-exit-0 invariant, and the
  five-code table match ADR-003 and design §3.1/§3.2 exactly.
- `COMMAND_NAMES` single-source-of-truth import path is correct
  (`novel_ralph_skill/commands/names.py`).
- tomlkit locked at 0.15.0 (the plan's stated pin) is correct.

## References (verified)

- Cyclopts v4.18.0 packaging.html, "Result Action": default
  `result_action="print_non_int_sys_exit"`; integer returns ->
  `sys.exit(int)`; None -> `sys.exit(0)`.
- Cyclopts latest app_calling.html, "Exception Handling and Exiting":
  `exit_on_error` defaults True -> `sys.exit(1)` on Cyclopts runtime errors;
  `print_error` default True; `help_on_error` default False; under
  `exit_on_error=False`, `UnknownCommandError` (a `CycloptsError`) is raised.
