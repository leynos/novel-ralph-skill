# Logisphere design review — roadmap 6.3.4 ExecPlan (Round 3)

Adversarial pre-implementation review of `docs/execplans/roadmap-6-3-4.md`.
Verdict: **Proceed** (✅). The two round-2 blockers (B5, B6) and all three
round-2 advisories (A4, A5, A6) are genuinely and verifiably resolved against
source. No new blocking defect was found. A handful of low-severity advisories
remain; none gate implementation.

## Round-2 resolutions — verified against source

- **B5 (unnamed snapshot edit site + Scope tolerance below footprint).**
  Resolved. `tests/test_novel_state_mutator_snapshots.py` is now a first-class
  Work item 1 edit site (its `_normalise` helper *and* module docstring),
  enumerated as file #7 in the Scope tolerance; the redaction analogue is
  corrected to the `created_at` **timestamp** redaction (verified: the file's
  only existing redaction is `_TIMESTAMP` at lines 37-39 / `_normalise` lines
  57-59 — there is no message redaction); the instruction is now a JSON-aware /
  scoped redaction of only `result.working_dir`, leaving the synthetic top-level
  `"working"` label untouched. The Scope tolerance is raised to the true
  12-file / ~340-line footprint, every file enumerated (Decision D7). Work
  item 0 step 4 points precisely at `test_init_success_envelope_snapshot`
  (`tests/test_novel_state_mutator_snapshots.py:62`) and `.ambr:22`.
  Independently confirmed: `grep -rn '"result":[^}]*"working_dir"'` over
  `tests/__snapshots__/` returns exactly one hit — line 22 of that `.ambr`
  (`"result": {"working_dir": "working", "slug": "s"}`). No other snapshot
  carries a body `result.working_dir`. `test_command_surface_matrix.py` excludes
  the `init` mutator (line 29) and uses the synthetic contract constant, so it is
  correctly bucketed as insulated.

- **B6 (stale documented contract invariant).** Resolved. Decision D8 and Work
  item 1 fold in the correction of the now-false module docstring at
  `tests/test_novel_state_mutator_snapshots.py:5-8` (verified verbatim: "the
  envelope carries no absolute path (`working_dir` is the fixed `"working"`
  token)"), stating the new truth that `novel.main`'s envelope label and the
  `novel state init` result body carry the absolute resolved path while the
  synthetic-`RunContext` snapshots keep the injected token for the top-level
  label.

- **A4 (ADR-003 has no field description).** Resolved. Work item 3 step 2 takes
  the add-a-note path only and states there is no rich description to amend
  (verified: ADR-003 line 46 lists `working_dir` only as a field name in the
  six-field bullet).

- **A5 (devguide line drift).** Substantially resolved (see advisory below). The
  plan cites line 158 within the 155-176 block. In the live source the
  `working_dir` token of "the fixed `working_dir` constant" actually wraps onto
  line 160, with line 158 being the six-field skeleton listing; both land the
  editor in the correct paragraph, so the residual imprecision is harmless.

- **A6 (inside-`working/` e2e cwd).** Resolved. Work item 2 step 2 now reaches
  the deeper cwd by passing `run_dir / "working"` as the first argument to the
  `run_installed(run_dir, argv)` fixture rather than constructing an
  `ExecutionContext` (verified: the fixture builds `ExecutionContext(cwd=run_dir)`
  internally at lines 174-178; it does not expose `ExecutionContext` to callers).

## Independent verification (this round)

- **Production stamps.** `novel.py:152` stamps `working_dir=WORKING_DIR_NAME`;
  `novel_state.py:264` returns `result={"working_dir": WORKING_DIR_NAME, ...}`.
  Both are exactly the two in-scope production stamps the plan names. `main()`
  delegates every `sys.exit` to `run`, so the Work item 1 behavioural test must
  catch `SystemExit` + read `capsys` — which is what the plan prescribes.
- **`_init` coherence.** `_init` calls `working_dir().mkdir()` (line 248) before
  stamping the body (line 264), so `working/` exists when `resolved_working_dir()`
  resolves; the non-strict `resolve()` is correct either way.
- **`pathlib.Path.resolve()` non-strict.** Re-confirmed on Python 3.14.3:
  `chdir(tmp); Path("working").resolve()` yields `<tmp>/working`, is absolute,
  and succeeds with no `working/` present; matches `Path(tmp).resolve()/"working"`.
- **Locked cuprum.** Verified against the installed source
  `/data/leynos/Projects/novel-ralph-skill/.venv/lib/python3.14/site-packages/cuprum/sh.py`:
  <!-- markdownlint-disable-next-line MD013 -->
  `run_sync(*, capture: bool = True, echo: bool = False, context: ExecutionContext | None = None)`
  at line 450; `CommandResult.exit_code: int`, `stdout/stderr: str | None`;
  `ExecutionContext.cwd`. The git HEAD at `/data/leynos/Projects/cuprum`
  (de54bff) has collapsed `capture` into `RunOutputOptions` (the `output` kwarg),
  confirming the drift warning. The plan correctly pins to the installed wheel and
  the e2e reuses the existing call verbatim; no cuprum API is asserted from memory.
- **Roadmap criterion.** roadmap.md:2217-2229 offers upward-search OR
  absolute-`working_dir` ("pick one and justify it"); the plan picks option 2,
  justifies it (D1), and meets "running from inside `working/` no longer
  *silently* looks for `working/working`" by making the misresolution visible.
  Subdirectory auto-resolution is honestly declared a deliberately accepted
  non-goal. Design-conformant.
- **Doc targets.** design line 151 is the JSON sample value; `grep` for the
  resolution rule in the design doc returns nothing (D4 confirmed). The
  deterministic/judgemental boundary is untouched: this is a pure deterministic
  path-resolution surface change with no judgemental component.

## Advisory (non-blocking)

- **AD1 (Telefono).** The `interrogate` docstring gate runs in the Makefile
  `lint` recipe (line 106), not `check-fmt` (as AGENTS.md implies) nor
  `typecheck` (as the plan's Constraints say). Operationally irrelevant — all
  three run under `make all` — but the plan's "or the `typecheck` gate fails"
  attribution is cosmetically wrong. The substantive requirement (every new
  module/function/test carries a docstring or `make all` fails) is correct.
- **AD2 (Pandalump).** Work item 1 says to re-export `resolved_working_dir` from
  `novel_state.py` "alongside the existing exports" but does not spell out the two
  mechanical edits the module's own lint discipline requires: add the symbol to
  the `_state_load` import block (lines 61-68) AND to `__all__` (lines 83-91), per
  the comment at lines 58-60. Likewise `novel.py:36` currently imports
  `WORKING_DIR_NAME` from `novel_state`; after the change `main` no longer uses
  it and must import `resolved_working_dir` instead, or the unused-import lint
  fires.
  `make all` catches both, so this is guidance, not a gap.
- **AD3 (Doggylump).** The inside-`working/` e2e (Work item 2 step 2) runs the
  state arm from inside `working/`, so the binary looks for
  `working/working/state.toml`, exits 3, and stamps `.../working/working`. This
  is the intended visible footgun; confirmed it still yields a parseable exit-3
  machine envelope (the arm stamps the envelope before any body executes). No
  change needed — recorded so the implementer expects exit 3, not exit 0.

## Pre-mortem (Doggylump)

The round-2 pre-mortem scenario — implementer trips the undersized Scope
tolerance at the first `init`-body commit and escalates mid-stream — is now
closed: the tolerance is 12 files / ~340 lines with every file enumerated, the
snapshot module is a named edit site, and the `_normalise`/docstring edits are
scheduled in the same commit as the `novel_state.py` body change. The remaining
plausible 03:00 scenario is a per-machine snapshot churn if the `_normalise`
redaction accidentally rewrites the top-level `"working"` label instead of only
`result.working_dir`; the plan pre-empts this by mandating a JSON-aware /
`result`-anchored rewrite and an idempotence check. Mitigation already designed
in.

## Strongest alternative (Wafflecat)

The only credible alternative (drop D6, leave the `init` body literal) was
analysed in round 2 and correctly rejected: it re-opens the round-1 B2 asymmetry
(envelope loud, `init` body silent) that an earlier review demanded be closed,
and is a regression on agreed scope. No new alternative is stronger than the
chosen design. The absence of a better option is itself a signal the design is on
solid ground.

## Verdict

✅ **Proceed.** The plan is implementable and design-conformant as written. Every
load-bearing claim — line numbers, the three-bucket pin inventory, the single
init-body snapshot, the locked cuprum signature, `resolve()` non-strict
semantics, and the roadmap success criterion — was verified against real source.
The three advisories are guidance the `make all` gates already enforce.
