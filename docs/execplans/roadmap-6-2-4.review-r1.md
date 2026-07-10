# Logisphere design review — roadmap 6.2.4 ExecPlan, Round 1

Verdict: REVISE (do not implement as written). The plan is exceptionally
well-grounded — almost every source-line citation verifies true against the
real code (cuprum `CommandResult`/`ExecutionContext`, `runner.run` exit-3
channel, `_recount.py`, design §3.2/§9/§10, ADR-003/006, the recount oracle
`{current: 8, by_chapter: {01: 3, 02: 5}}`, the existing cross-module import,
the `working_corpus` overrides, AGENTS.md gate line numbers). The blocking
defects are concentrated in Work item 1's fixture design and the cost claims
that rest on it.

## Blocking

1. **Fixture scope-widening fallback is mechanically impossible (WI1).** WI1 and
   its body (lines 330-334) say "function scope is the conservative default;
   only widen to session if a gate flags duplicate build cost." But the proposed
   `installed_novel_state` (Interfaces, lines 604-614) depends on `tmp_path`,
   `single_program_catalogue`, and `venv_scripts_dir` — all **function-scoped**
   (`tests/conftest.py` lines 238, 270; `tmp_path` is always function-scoped). A
   `module`/`session`-scoped fixture that depends on a function-scoped fixture
   raises `ScopeMismatch` at collection. The proven precedent the plan cites,
   `installed_desloppify` (`tests/test_ai_isms_e2e.py` lines 152-164), is
   `scope="module"` precisely because it takes `tmp_path_factory`
   (session-safe) and does **not** depend on the two function-scoped builders.
   The escape hatch the plan offers cannot be taken without also
   re-architecting the fixture's dependencies. Fix: decide the scope up front.
   To reuse the wheel, make `installed_novel_state` `module`- or
   `session`-scoped and feed it `tmp_path_factory` plus session-safe variants
   of the catalogue/scripts-dir helpers (or inline their logic), mirroring
   `installed_desloppify`. Otherwise state plainly that it is function-scoped
   and drop every reuse claim.

2. **Risk-section reuse claim contradicts the chosen implementation (WI1 /
   Risks lines 144-151).** The Risks section asserts the fixture "builds the
   wheel **once** per test that needs it, and where two cases share one install
   they share one fixture invocation (mirroring `test_ai_isms_e2e.py`'s
   `installed_desloppify` session reuse)." A function-scoped fixture does the
   **opposite**: a fresh wheel build, venv, and install for every test
   function, and — critically — a fresh build for **each parametrized case** of
   WI3's exit-3 test (two cases → two full builds), where the cited
   `installed_desloppify` pattern shares one module-scoped install across all
   its parametrized cases. The mitigation as written is not delivered by the
   implementation as written. Fix: align the claim with the scope actually
   chosen under defect 1; if reuse across the two exit-3 cases is wanted, the
   fixture must be module/session scoped (see defect 1).

## Advisory (non-blocking, fix to avoid implementer traps)

- **cwd-naming inconsistency between WI2, WI3, and the Artefacts snippet.** WI2
  step 1 defines `dest = tmp_path / "run" / "working"` and runs with
  `cwd=dest.parent` (correct: cwd contains `working/`). WI3 defines `dest` such
  that `cwd=dest` contains `working/`. The Artefacts template (lines 592-600)
  and the inline example (line 595) use `cwd=dest`. The two work items use the
  name `dest` for two different directory levels, and the shared snippet
  matches only WI3. An implementer copying the snippet into WI2 would point cwd
  at the `working/` dir itself and the run would not resolve
  `./working/state.toml`. Fix: use distinct names (e.g. `run_dir` vs
  `working_dir`) and make the snippet match each work item's own `dest` level,
  or normalize both work items to the proven `check` template shape
  (`dest = tmp_path / "run"`, materialize `dest/working/`, run with `cwd=dest`).

- **Net build-cost is flat, not improved.** The three rerouted tests already
  each
  build a wheel in-body today, so WI1 is net-neutral for them; the three new
  builds (WI2 + WI3 two cases) are inherent. With a function-scoped fixture the
  suite pays ~6 wheel builds under `-n auto`/180 s. This is acceptable but the
  plan's framing implies a saving that is not realized. State the real cost.

## What is sound (verified, no change needed)

- Exit-3 channel: `runner.run` lines 233-239 emit via `_emit` →
  `print(rendered)`
  to **stdout**, then `sys.exit(STATE_ERROR==3)`; so asserting stdout JSON
  `ok is False` AND `exit_code == 3` is correct (`exit_codes.py` line 29).
- recount routes missing/unparseable/undecodable state through `StateInputError`
  → exit 3 (`_recount.py` `_recount_or_state_error`, `recount()` lines
  139-149); in-process pins exist (`test_recount_unit.py` 198-234).
- recount oracle: `draft_words` writes an N-word `draft.md`; `recount_words`
  uses
  `len(text.split())` (`state/disk_evidence.py` line 154); overrides write the
  wrong counts; `{current: 8, by_chapter: {01: 3, 02: 5}}` is the corrected
  result and matches the in-process oracle (`test_recount_e2e.py` lines 67-69).
- Shared-scaffolding rule and the existing cross-module import are real
  (developers-guide 31-64; `test_reconcile_e2e.py` line 32); D-FIXTURE is the
  right remedy in principle — only its scope mechanics are wrong.
- Dependencies 2.1.2 and 2.3.1 are ticked `[x]` (roadmap line 407 and the 2.3.1
  family). Exit-code policy, design §9 CLI error-path prose, and §10
  message-not-traceback promise all support the assertions WI3 makes.

Docs/skills relied on: docs/novel-ralph-harness-design.md §3.2/§9/§10,
docs/adr-003 and adr-006, docs/developers-guide.md (shared scaffolding),
AGENTS.md (gates, snapshot guidance, markdown), /data/leynos/Projects/cuprum
source (sh.py), and the logisphere-design-review skill (Pandalump structural,
Buzzy Bee scaling/cost, Doggylump failure modes, Telefono contracts).
