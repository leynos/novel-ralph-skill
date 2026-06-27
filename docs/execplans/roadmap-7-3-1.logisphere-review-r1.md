# Logisphere design review — roadmap 7.3.1 (round 1)

Verdict: REVISE. The plan is well-researched and structurally close, but its
prose-cross-reference sweep (WI5/WI6) is demonstrably incomplete: renaming
`_state_load.py` to `state_sourcing.py` leaves several stale
`_state_load`-named references that the plan never enumerates and that no test
mechanically guards. The plan's own Constraints invoke the "defining-module
path is canonical" rule and AGENTS.md documentation hygiene, so these gaps are
in-scope defects, not nice-to-haves.

Reviewer trail: read the execplan from disk; verified every load-bearing claim
against `_state_load.py`, `novel_state.py`, the seven consumers, the
`_state_mutators` second-hop, the test import sites, `docs/developers-guide.md`,
`docs/roadmap.md` (7.3.1/7.3.2/7.3.3 entries), and the drift-guard suite.
Confirmed `leta mv`/`leta rename` capabilities via `leta mv --help` /
`leta rename --help`. cuprum: confirmed not on this task's path
(`grep -rn cuprum novel_ralph_skill/commands/` empty; seam uses `tomllib`/
`pathlib`, no subprocess) — Decision D4 holds.

## What holds (credit where due)

- The "seam already lives in the dependency-free leaf `_state_load.py`,
  re-exported
  by `novel_state`" observation is correct (`novel_state.py:61-73`, `__all__`
  89-102). `stub.py` genuinely no longer exists. The task is a
  rename-and-repoint.
- The seven-consumer inventory and their imported-name sets are accurate.
- The `_state_mutators` second-hop is correct: `_recount.py:22` and
  `_reconcile.py:51` import `_state_path`/`_working_dir` *from `_state_mutators`
  *, whose `__all__` re-export keeps those names; `_recount.py:29` separately
  imports `STATE_INPUT_ERRORS`/`_draft_read_error` from `novel_state` (handled
  by WI3). Both legs verified.
- The six `:func:` prose cross-references in WI5 (`_wordcount.py:112`,
  `_desloppify.py:168,176`, `_state_mutators.py:89,91,130`) match exactly the
  `novel_state._<seam>` `:func:` roles found by grep. That sub-list is complete.
- `WORKING_DIR_NAME` deferral to 7.3.6 is correct and roadmap-cited.
- `make all` target chain verified (`build check-fmt lint typecheck test`).

## Blocking defects (back to the planner)

### B1 — WI5/WI6 prose sweep misses references outside the six `:func:` roles

After `leta mv` renames the file, these `_state_load`-named references go stale.
`leta mv` updates *import statements*, and `leta rename` updates *symbol
references*; neither rewrites free-text docstring prose, `:mod:` roles, or
line-number citations. The plan must enumerate and sweep all of:

1. `novel_ralph_skill/state/compile_model.py:73` — prose names
   `commands._state_load.working_dir`. This is *outside* `commands/`, so the
   plan's WI5 list (all in `commands/`) and its WI6 (devguide only) both miss
   it. It becomes a dangling module path after the rename.
2. `novel_ralph_skill/commands/novel.py:153` — line-number citation
   `_state_load.py:32-48`. Stale filename after rename.
3. `novel_ralph_skill/commands/_state_load.py:56` — the module's *own*
   self-citation
   `_state_load.py:32-48`. WI1 says "update the module docstring … rather than
   '…400-line cap'" but does not call out this line-number self-reference.
4. `novel_ralph_skill/commands/_wordcount.py:117` — bare `_load_or_state_error`
   in free prose (not a `:func:` role). `leta rename` will not touch docstring
   free-text; WI5's six-item list does not include it.
5. `novel_ralph_skill/commands/_novel_done.py:28` — module docstring lists
   `_load_or_state_error` (bare, in prose) among the reused helpers.
6. `tests/test_state_load_actionable_parity.py:6,13` — docstring `:mod:` role
   `:mod:...._state_load` and free prose "definition module `_state_load` (not
   the `novel_state` re-export)". WI4 only generically says "if any
   string-literal module path survived (for example in a docstring) fix it" —
   it must name this file's two references explicitly, because `leta mv` will
   repoint the *import* (line 51) but leave the docstring prose pointing at the
   dead module name.

Why blocking: the plan's Constraints and WI5 explicitly invoke the
developers-guide "defining-module path is canonical, never the re-export
façade" rule and AGENTS.md documentation hygiene. A rename that leaves the
*defining module's own name* stale in six-plus places violates the very rule
the plan cites. Critically, none of these are caught by a test: the projection
drift-guard registry
(`tests/test_projection_docstring_drift_guard.py:_REGISTRY`) pins only
`compile_model.compiled_matches_drafts` and the reconciliation projections — it
does *not* cover the state-sourcing seam — so these references will silently
rot. The plan asserts WI5/WI6 make the single-home property "real", but as
written they leave a trail of dead `_state_load` names.

Remedy: add a verification step to WI5 (or a new sub-item) of the exact form
`grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`
must return nothing after the sweep, and enumerate items 1-6 above as the known
sites. Decide explicitly whether `tests/test_state_load_*.py` *filenames* are
renamed (the plan is silent; if not renamed, state that the filename is an
accepted residual and why).

### B2 — `test_state_load_actionable_parity.py` import-source intent is mis-specified

This test imports the *underscore-private formatters* (`_compile_write_error`,
`_device_ledger_read_error`, `_draft_read_error`, `_rule_pack_read_error`,
`_state_input_error`) directly from `_state_load` (line 51), and its docstring
(lines 13-14) states it *deliberately* imports "from their definition module …
(not the `novel_state` re-export) so the guard exercises the implementation
location". Decision D3 keeps these formatters underscore-private and does not
promote them; `leta mv` will repoint this import to `state_sourcing`
automatically. That is fine — but WI4's prose ("import the *seam* from
`state_sourcing` in tests") conflates this *formatter-set* parity test with the
*seam* tests. The plan must state that this file imports the private formatters
(not the public seam) and that the only change is the `leta mv` import repoint
plus the two docstring prose fixes from B1. As written, WI4 risks a reviewer
(or implementer) "tidying" it onto the public `load_or_state_error`, which
would break the test's stated purpose.

### B3 — WI6 changes the developers-guide formatter prose without checking the count-guard hypothesis

WI6 edits `docs/developers-guide.md:619-649`, the passage that says "Five
sibling formatters in the dependency-free leaf module `_state_load`".
`docs/issues/audit-6.3.9.md` proposed guarding this formatter-count prose
against the live `_state_load` formatter set. I confirmed no such guard test is
currently active (no test pins "five formatters" or the module name), so
editing the prose is safe today — but the plan asserts the edit only "names
`state_sourcing`" without verifying that the count claim and the module name
are unguarded. Add an explicit Decision-Log line recording the grep that
confirms `docs/developers-guide.md:619-649` is *not* pinned by any drift-guard,
so the implementer does not have to re-derive it and does not accidentally
leave the guide's "Five sibling formatters … `_state_load`" prose half-updated
(the module-name token at 620 must change even though the count does not).

## Advisory (non-blocking)

- A1: line-count drift. The plan twice states `_state_load.py` is "365 lines";
  it is 364 (`wc -l`). The 400-cap conclusion is unaffected, but the figure is
  wrong in two places — tighten for accuracy.
- A2: WI2's commit shape is left ambiguous ("xfail(strict=True) *or* split …
  Decision Log will record which"). The plan should *fix* the choice now (land
  assertion 1 green in WI2; assertion 2 as the opening red step of WI3) rather
  than deferring it to implementation, so the red-green discipline is
  pre-decided and the work items stay atomic.
- A3: WI2's AST no-dependency assertion lists the seam names to forbid, but the
  list omits `INSPECT_REPAIR_REMEDY` (a public constant in the leaf, used only
  internally) — correctly, since no consumer imports it. Worth a one-line note
  that the constant stays module-internal and is intentionally excluded from
  the forbidden-import set, so a reader does not flag it as a missed seam.
- A4: Pre-mortem. The most likely six-months-later failure for *this* class of
  refactor is exactly B1: a future `novel-state` or 7.3.6 edit, or a doc audit,
  trips over a stale `_state_load` reference that the rename left behind and
  that no guard caught, costing a confused investigation. The mitigation is the
  exhaustive `grep -rn '_state_load'`-returns-nothing gate from B1. Bake it in.

## Strongest alternative (Wafflecat)

Promote the seam into `novel_ralph_skill/state/` (a `state/sourcing.py`) rather
than keeping it flat in `commands/`. Trade-off: it would pre-resolve the
`contract`→`commands` layering tension 7.3.6 must fix and give the seam a home
above the command layer, but it *gains* nothing 7.3.1 needs and *loses* the
clean 7.3.6 coordination the roadmap explicitly sequences (`WORKING_DIR_NAME`
is to move to `contract`, not `state`, under 7.3.6). It also imports `state`,
so placing it under `state/` risks a `state`-internal dependency the design
does not sanction. The plan's flat command-layer choice (Decision D1) is
correct; the alternative is genuinely viable but trades away roadmap sequencing
for no gain. Recording it here for calibration: D1 stands.

— end round 1
