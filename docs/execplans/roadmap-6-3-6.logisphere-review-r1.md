# Logisphere adversarial design review — roadmap 6.3.6, round 1

Reviewed: `docs/execplans/roadmap-6-3-6.md` (DRAFT). Verdict: **not satisfied**.
One blocking accuracy defect; the rest of the plan is well-grounded.

Trail: design `docs/novel-ralph-harness-design.md` §3.1, §9; ADR-003; ADR-006;
`docs/developers-guide.md` "Shared test scaffolding"; AGENTS.md. Verified cuprum
behaviour against the locked 0.1.0 wheel in this repo's `.venv` (not the
`/data/leynos/Projects/cuprum` unreleased sibling). Skills consulted:
logisphere-design-review, python-testing.

## What checks out (verified against real source)

- cuprum 0.1.0 `SafeCmd.run_sync` signature is exactly
  `(self, *, capture: bool = True, echo: bool = False, context:
  ExecutionContext | None = None) -> CommandResult` (live `inspect.signature`).
  `CommandResult` carries `exit_code`, `stdout`, `stderr`. `uv.lock` pins cuprum
  `0.1.0`. The plan's signature reconciliation is correct.
- `ENVELOPE_KEY_ORDER`, `BODY_PHASE = "final-pass"`, `WORKING_DIR_CONSTANT`
  exist as plain-value constants in `tests/cross_command_contract/__init__.py`;
  importing the constants (not fixtures) does not breach the developers-guide
  cross-module rule.
- `installed_novel_state` (module-scoped) and `single_program_catalogue` exist
  by name and use the `ProjectSettings(name, programs, documentation_locations,
  noise_rules)` / `Program(str(path))` API the plan describes
  (`tests/installed_binary_fixtures.py`, `tests/conftest.py`).
- The resolved-absolute `working_dir` reconciliation is real: the in-process
  `assert_envelope_skeleton` asserts `working_dir == "working"`
  (`_identity_assertions.py` line 112), whereas the installed boundary stamps
  `str((run_dir / "working").resolve())`
  (`test_console_scripts_error_arms_e2e.py` line 301). The plan correctly does
  NOT call `assert_envelope_skeleton` verbatim.
- `novel state` over `final-pass` is coherent: the cross-command snapshot
  `test_machine_envelope_skeleton_snapshot[novel state]` records `ok: True`
  (`__snapshots__/test_envelope_shape.ambr` line 45), so `state check` exits 0
  over `BODY_PHASE`. `final-pass` is a real key in `PHASE_STATES`
  (`tests/working_corpus/_library.py`). `result["violations"] == []` follows
  from exit 0 by the checker contract (incoherent → exit 4).
- pytest-timeout-under-xdist is empirically pinned, not a memory claim:
  `make all` -> `make test` runs `pytest -v -n auto` (Makefile line 126) with NO
  `-m "not slow"` deselect and `timeout = 30` default (pyproject line 322); the
  existing `test_console_scripts_error_arms_e2e.py` carries
  `@pytest.mark.timeout(180)` and is green in exactly this config. The 180s
  per-test override is therefore proven in-repo. Acceptable.

## BLOCKING

### B1. The plan's central premise is false: an installed exit-0 proof for `novel state check` already exists

The Purpose states (lines 21-23): "The body-producing success arm (exit 0, a
real `result` payload) has **never** been observed crossing the wheel/venv
packaging boundary against the cross-command identity skeleton." The
Surprises/Discoveries section (lines 228-240) doubles down: the installed exit-0
body skeleton is "pinned nowhere"; `test_console_scripts_error_arms_e2e.py`
covers only exit 2/3 and `test_novel_state_check.py`'s exit-0 case "uses `run` +
`capsys` ... never over the wheel."

This is wrong. `tests/test_novel_state_check.py` lines 307-345 contains
`test_installed_novel_state_check_exits_zero` — a `@pytest.mark.slow`,
`@pytest.mark.timeout(180)`, POSIX-skipif installed e2e that:

- builds and installs the wheel via `installed_novel_state`,
- materializes a coherent `working/` tree,
- drives `novel state check` through the installed script with
  `sh.make(prog, catalogue=...)("state", "check").run_sync(
  context=ExecutionContext(cwd=dest), capture=True)`,
- asserts `result.exit_code == 0` and `envelope["ok"] is True`.

The design document the plan cites as source of truth confirms this: design §9
line 893 lists "the existing `check` (exit 0) ... proofs" among the
installed-binary e2es. The plan contradicts its own cited authority.

Why this is blocking, not cosmetic:

1. The justification for adding a *new module* rests on a false gap statement.
   The genuine residual gap is narrower and must be stated precisely: the
   existing test pins only `exit_code == 0` and `ok is True`; it does NOT pin the
   six-key order against `ENVELOPE_KEY_ORDER`, `schema_version == 1`,
   `command == "novel state"`, the resolved-absolute `working_dir`,
   `result["violations"] == []`, or message element types. The tripwire's real
   value is the full envelope-*skeleton identity* over the wheel. The plan must
   re-scope around that true delta.
2. It bears directly on the Scaffolding/duplication tolerance (lines 124-127,
   141-151) and Risk-1 ("Duplicating the installed error-arm e2e"). The actual
   duplication risk is against `test_installed_novel_state_check_exits_zero`,
   which the plan never mentions. An implementer must decide — and the plan must
   instruct — whether to (a) extend that existing test with the skeleton
   assertions, or (b) add a separate tripwire module and explicitly demarcate its
   boundary against the existing exit-0 test (as it already does against the
   error-arm module). Either is defensible, but the plan currently makes the
   decision on false information and gives the implementer no boundary note for
   the test that actually overlaps.
3. Work item 3 (developers-guide note) instructs recording the new module's
   boundary against the error-arm module and the in-process suite, but omits the
   boundary against `test_installed_novel_state_check_exits_zero` — the one
   existing installed test that already covers this exact command and arm. The
   scope note will be incomplete and slightly misleading.

Required fix: correct the Purpose and Surprises sections to acknowledge
`test_novel_state_check.py::test_installed_novel_state_check_exits_zero`; restate
the residual gap as the unpinned envelope-skeleton identity (key order,
`schema_version`, `command`, resolved `working_dir`, `result` payload, message
types) rather than "exit-0 never observed over the wheel"; add a Decision Log
entry choosing between extending the existing test vs. a new module, with
rationale; and extend Work item 3 to demarcate the boundary against that existing
test. If the chosen path is a new module, justify why the skeleton assertions
should not simply be folded into the existing exit-0 installed test (which would
avoid a second wheel build for the same command/arm — a real cost given the
module-scoped build runs once *per module*, so a new module pays a second full
wheel build).

## ADVISORY

### A1. Second wheel build cost (Buzzy Bee — scaling)

`installed_novel_state` is module-scoped: the wheel build/venv/install runs once
*per consuming module*. A new `test_installed_identity_tripwire_e2e.py` module
therefore triggers an additional full wheel build + venv + install in `make all`,
on top of the builds already paid by `test_novel_state_check.py`,
`test_console_scripts_error_arms_e2e.py`, and the other installed-e2e modules.
For a single added assertion-set over a command already installed-tested, folding
the skeleton assertions into `test_installed_novel_state_check_exits_zero`
(B1 option a) would add zero build cost. The plan should weigh this explicitly
rather than defaulting to a new module.

### A2. `command == "novel state"`, not `"novel state check"` (Telefono — contracts)

Work item 1 step 7 asserts `envelope["command"] == "novel state"`. This is
correct (the dispatcher stamps the spaced sub-app name, not the read
subcommand — confirmed by `_STATE_COMMAND.name = "novel state"` and the
snapshots), but it is a known footgun for an implementer who expects the argv
`("state", "check")` to surface as the command. The plan does name it correctly;
keep the explicit value and the `ENVELOPE_COMMAND_NAMES` membership check.

### A3. Optional snapshot adds churn for little gain (Wafflecat — alternatives)

The "Artefacts and notes" / Work item 1 optional `.ambr` snapshot redacts
`working_dir` and `messages` but keeps `result: {"violations": []}`. The
cross-command suite already snapshots the redacted skeleton in-process; an
installed snapshot would only re-pin the same fixed fields the semantic
assertions already cover, while adding a snapshot file. The plan already permits
dropping it ("prefer the semantic assertions alone"); recommend defaulting to
no snapshot to keep the module minimal and avoid a near-duplicate `.ambr`.

### A4. Teeth-check via mark selection (Doggylump — failure modes)

Work item 2 runs `uv run pytest ... -m slow` to perturb-and-revert. Confirm the
perturbation lands on an *asserted field* (e.g. expected `command`), not on the
wheel build, so a red result proves the assertion bites rather than masking a
build failure. The plan already says "goes red on the asserted field (not on a
build error)" — good; keep that explicit check in the Decision Log entry.
