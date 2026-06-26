# Logisphere adversarial design review — roadmap 6.3.6, round 2

Reviewed: `docs/execplans/roadmap-6-3-6.md` (DRAFT, round-2 revision). Verdict:
**satisfied — proceed**. The round-1 blocking defect (B1) is fully corrected and
re-verified against real source; every load-bearing claim checks out. No blocking
defects remain.

Trail: design `docs/novel-ralph-harness-design.md` §3.1/§3.2/§9/§10; ADR-003
(Table 2); ADR-006; `docs/developers-guide.md` "Shared test scaffolding";
AGENTS.md (400-line cap, snapshot rules). cuprum behaviour verified against the
locked 0.1.0 wheel in this repo's `.venv` (not the `/data/leynos/Projects/cuprum`
unreleased sibling). Skills consulted: logisphere-design-review, python-testing.

## R1 blocking defect B1 — RESOLVED

B1 was: the Purpose/Surprises asserted the installed exit-0 arm "has **never**
been observed crossing the wheel/venv packaging boundary", which was false —
`test_novel_state_check.py::test_installed_novel_state_check_exits_zero` already
drives the installed `novel state check` over a coherent tree and asserts
`exit_code == 0` and `ok is True`.

The round-2 revision corrects this completely:

- Purpose (lines 21-43) now opens by naming that exact existing test and citing
  design §9 line 893 ("the existing `check` (exit 0) … proofs"). Verified: the
  test at `tests/test_novel_state_check.py` lines 316-344 is exactly as
  described — `@pytest.mark.slow`/`@pytest.mark.timeout(180)`/POSIX-`skipif`,
  builds via `installed_novel_state`, copies `baseline_tree()` into
  `dest/working`, drives `("state","check").run_sync(context=ExecutionContext(
  cwd=dest), capture=True)`, asserts `result.exit_code == 0` and
  `envelope["ok"] is True`. Nothing else.
- The residual gap is restated precisely (lines 34-43) as the *unpinned envelope-
  skeleton identity* over the wheel: six-key order vs `ENVELOPE_KEY_ORDER`,
  `schema_version == 1`, `command == "novel state"`, the resolved-absolute
  `working_dir`, `result["violations"] == []`, and `str`-typed `messages`.
- A Decision Log entry (lines 329-348) chooses **extend in place** over a new
  module, with the second-wheel-build rationale spelled out (addresses A1).
- Risk-1 (lines 179-193) and the Scaffolding/line-cap tolerances (lines 153-165)
  are rewired to measure duplication against
  `test_installed_novel_state_check_exits_zero` — the test that actually
  overlaps — not only the error-arm e2e.
- Work item 3 (lines 629-650) now demarcates the boundary against both the
  installed error-arm e2e (exit 2/3) and the in-process cross-command suite.

## What checks out (verified against real source this round)

- **cuprum 0.1.0 `run_sync` signature** — live `inspect.signature` in this
  repo's `.venv`: `(self, *, capture: bool = True, echo: bool = False, context:
  ExecutionContext | None = None) -> CommandResult`. `uv.lock` lines 113-115 pin
  cuprum `0.1.0`. The plan correctly pins the locked `capture=` API and
  explicitly rejects the unreleased sibling's `output: RunOutputOptions`
  (Surprises, lines 272-287). Not a memory claim — verified.
- **Envelope key order** — `render_machine` (`envelope.py` lines 143-151) emits
  the ordered dict `command, schema_version, ok, working_dir, result, messages`,
  byte-identical to `ENVELOPE_KEY_ORDER` (`cross_command_contract/__init__.py`
  lines 81-88). `result` before `messages`. The `tuple(envelope) ==
  ENVELOPE_KEY_ORDER` assertion is sound over the wheel's JSON (Python preserves
  dict insertion order; `json.loads` preserves key order).
- **Production constants** — `ENVELOPE_SCHEMA_VERSION = 1` (`envelope.py` line
  25); `"novel state" in ENVELOPE_COMMAND_NAMES` confirmed live (tuple is
  `('novel state','novel done','novel compile','novel desloppify',
  'novel wordcount','novel')`). The plan's `command == "novel state"` value is
  correct (A2 footgun named correctly — the dispatcher stamps the spaced sub-app
  name, not the `check` subcommand).
- **Resolved-`working_dir` reconciliation** — the installed boundary stamps
  `str((run_dir / "working").resolve())` (`test_console_scripts_error_arms_e2e.py`
  line 301), whereas the in-process `assert_envelope_skeleton` asserts
  `working_dir == WORKING_DIR_CONSTANT` i.e. `"working"`
  (`_identity_assertions.py` lines 111-114, `__init__.py` line 76). The plan
  correctly computes the expected value from its own run dir `dest` —
  `str((dest / "working").resolve())` — and does NOT call the in-process helper
  verbatim. Same module already does this for its entry-point tests (lines 212,
  234), so the pattern is established in-file.
- **`result["violations"] == []` for the coherent baseline** — the module's own
  in-process `test_check_coherent_tree_exits_zero` (line 89) asserts exactly
  `envelope["result"]["violations"] == []` over the same `baseline_tree`, so the
  installed assertion is a true mirror, not a guess. Exit 0 over a coherent tree
  ⇒ no violations by the checker contract.
- **Constant import is permitted and resolvable** — `ENVELOPE_KEY_ORDER` is a
  plain `typ.Final` value (not a fixture), so `from cross_command_contract import
  ENVELOPE_KEY_ORDER` is not a cross-module fixture/value-import breach. The
  package resolves as a top-level import from the test tree:
  `tests/steps/cross_command_contract_steps.py` already does `from
  cross_command_contract import COMMANDS`, and the edited file already does
  `from conftest import WorkingTreeSpec` (line 47). No `pythonpath` override
  needed; `tests/` is the rootdir on `sys.path`.
- **Line-cap headroom** — file is 344 lines (`wc -l`), matching the plan. Three
  imports + ~9 assertion lines + a docstring extension lands near ~360, well
  under the 400-line cap (AGENTS.md line 24). No split, no second wheel build.
- **pytest-timeout under xdist** — empirically pinned, not a memory claim: the
  same `@pytest.mark.timeout(180)` override is carried by the green
  `test_console_scripts_error_arms_e2e.py` under `pytest -n auto` (per r1; the
  config is unchanged this round). Acceptable.
- **Snapshot drop** — A3 resolved: the plan now drops the optional `.ambr` and
  records (Decision Log / Work item 1, lines 571-576) that the semantic
  assertions are the complete primary guard, avoiding a near-duplicate snapshot
  that would only re-redact down to the very fields the assertions check. This
  conforms to AGENTS.md lines 148-158 (no snapshot-only coverage; pair with
  semantic assertions; redact nondeterministic fields).
- **Deterministic/judgemental boundary** — untouched. This is a verification
  task: no `novel_ralph_skill/` source changes; the envelope, runner, exit-code
  vocabulary, and the five `build_app()` factories stay behaviourally fixed. The
  production-divergence tolerance (lines 157-160) correctly routes any genuine
  installed-vs-contract divergence to escalation rather than a cover fix.

## Atomicity / ordering / testability / completeness

- **Atomic & ordered.** Three independently committable items: WI1 (extend the
  test), WI2 (teeth check — perturb-and-revert, no commit), WI3 (devguide note).
  WI2 depends on WI1; WI3 is independent. Order is correct.
- **Testable.** Acceptance is behavioural and falsifiable: the named single-test
  invocation passes with the eight enumerated assertions, and a deliberate
  divergence (reversed key order, bumped `schema_version`, wrong `command`,
  `ok: false`) turns it red on that field. WI2 mandates confirming the red lands
  on the asserted field, not a build error (A4 resolved, lines 599-619).
- **Validation specified.** Each WI ends with `make all`; WI3 adds `make
  markdownlint` and `make nixie`. Concrete steps (lines 658-714) re-verify the
  cuprum signature, collect-only the single id, run `-m slow`, then gate.
- **Complete.** No dangling work; the revision note (lines 804-831) records the
  r1→r2 delta accurately.

## Pre-mortem (Doggylump)

Six months on, the most plausible failure is a *silent false-green*: the
installed `result` payload drifts (e.g. a checker emits `result == {}` instead of
`{"violations": []}`) but the test still passes because an assertion is too loose.
Mitigation already designed in: the plan asserts both `isinstance(result, dict)`
*and* `result["violations"] == []` (WI1 assertion 7), and the WI2 teeth check
forces a red on a real perturbation before the green is trusted. Blast radius is
nil (single test, `tmp_path`-hermetic, idempotent). No new signal needed.

Second scenario: the constant import silently desyncs from production. Mitigated
because the test asserts against the *same* `ENVELOPE_KEY_ORDER` /
`ENVELOPE_SCHEMA_VERSION` / `ENVELOPE_COMMAND_NAMES` the in-process suite uses,
so the installed tripwire cannot diverge from the in-process proof without both
going red together (plan lines 578-582).

## Strongest alternative (Wafflecat)

The genuine alternative — a *new* `test_installed_identity_tripwire_e2e.py`
module — is correctly rejected: it buys only module isolation the existing test
already provides, at the cost of a second module-scoped wheel build for the same
command/arm (`installed_novel_state` runs once per consuming module). Extend-in-
place is the right call; the trade-off is analysed explicitly in the Decision Log
(lines 329-348). No stronger alternative exists.

## Advisory (non-blocking)

- A-r2-1 (cosmetic): WI1 assertion 1 asserts no `"Traceback"` in `result.stderr`
  (design §10). On the success arm stderr is normally empty, so this is a cheap
  belt-and-braces guard, not load-bearing. Fine to keep; if it ever proves
  flaky against build-tool chatter on stderr, narrow it to the envelope path. No
  action required now.

Verdict: **satisfied**. Implementable and design-conformant as written.
