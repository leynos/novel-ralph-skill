# Logisphere design review — roadmap 1.2.15 (round 2)

Verdict: **Revise**. The five round-1 blocking defects (B1-B5) are genuinely
fixed and verified against the live worktree: the three-serialisation
`$SNAP_GATE` finds all 12 snapshot files, the word-anchored `$REG_GATE` correctly
excludes the kept `SUBCOMMAND_NAMES`, the matrix idioms and symbol names
(`_ReadCommand`/`_ErrorArm`) are accurate, and the load-bearing docstring sweep
(B5) is real. The D1/D2/D5 dispositions and the cuprum/cyclopts version claims
also check out.

But round 2 fixed B3 (the dict-key/lookup stamping idiom that no `command="…"`
gate can see) **only for the single named file** `test_command_surface_matrix.py`,
rather than generalising the lesson. Two *other* modules use the same indirect
`RunContext(command=<var>)` stamping idiom, and the consumer enumeration misses
one of them entirely. That reopens the very failure mode the gate apparatus
exists to prevent: a late `build_envelope` `ValueError` after the guard narrows,
invisible to every D3 gate.

## Blocking defects

### B6 — `tests/steps/per_chapter_loop_steps.py` is a RUN-GUARD consumer that is missing from the inventory and uncovered by every gate

`tests/steps/per_chapter_loop_steps.py` drives `run()` with a legacy command name
stamped into `RunContext.command`:

- `_BUILD_APPS` (lines 66-70) maps the five **legacy** names
  (`"novel-state"`, `"novel-done"`, `"wordcount"`, `"desloppify"`,
  `"novel-compile"`) to each leaf's `build_app`.
- `_run_capturing` (lines 105-108) calls
  `run(...)` with
  `RunContext(command=command_name, working_dir="working", human=False)`.
- The `When` steps pass the legacy literal directly:
  `_run_capturing(outcome.working, "novel-state", ["recount"], …)` (line 142),
  `…"novel-done"…` (165-166), `…"wordcount"…` (182-183),
  `…"desloppify"…` (210-211), `…"novel-compile", ["--check"]…` (228-229), etc.

This module is driven by the real BDD test `tests/test_per_chapter_loop_bdd.py`.
When WI4 narrows `ENVELOPE_COMMAND_NAMES`, every one of these stamps is rejected
at `build_envelope` (`envelope.py:113`) and the BDD test raises `ValueError` —
exactly the late-runtime fault the plan claims to eliminate by construction.

It is **not in the plan's RUN-GUARD inventory** (Context lists
`set_chapters_steps.py`, the three `torn_turn_*` step files, the five inline BDD
steps, and the matrix — but not `per_chapter_loop_steps.py`). It is **not swept
in WI2** and **not covered by any D3 gate**: the gate (a) patterns
(`command="<legacy>"`, `_COMMAND = "<legacy>"`) do not match the dict-key /
helper-argument idiom, and the matrix-aware `LEGACY` scan is scoped only to
`test_command_surface_matrix.py`. This directly violates the plan's own
Tolerances ("a test module not derivable from the WI-scoped greps … means the
consumer enumeration missed a caller — stop and escalate").

Fix: add `per_chapter_loop_steps.py` to the WI2 RUN-GUARD sweep (the legacy
`_BUILD_APPS` keys *and* the six `_run_capturing(…, "<legacy>", …)` call sites all
move to the spaced names); and extend the D3/closing source gate so it scans the
indirect-stamping modules, not just the matrix — e.g. a plain `$LEGACY` scan over
`tests/steps/per_chapter_loop_steps.py` (and `tests/multiplexer_support.py`,
`tests/test_multiplexer_behaviour.py`; see B7) asserted empty. The robust
generalisation is to make the matrix-aware scan a scan over **every** module that
stamps `RunContext(command=<non-`_COMMAND`-variable>)`, not a single hand-named
file.

Evidence: `rg -nP 'RunContext\([^"]*command=([a-z_][\w\.\[\]"]*)' tests` shows the
indirect-stamping universe resolves to `_COMMAND` (gate-covered), `command.name`
in the matrix (matrix-scan-covered), `name` in `multiplexer_support.py:105`
(B7, no gate), and `command_name` in `per_chapter_loop_steps.py:108` (this defect,
no gate, not inventoried).

### B7 — the parity rework (WI4 step 7) has no gate, and step 7 omits a hardcoded legacy-name call site

The parity suite is the *one* place WI4 step 7 reworks legacy stamps, yet it is
also stamped indirectly and **no D3/closing gate covers it**:

- `tests/multiplexer_support.py:105` stamps `RunContext(command=name, …)` where
  `name` is supplied by the caller.
- `tests/test_multiplexer_behaviour.py` supplies legacy names two ways: the
  `_OPERATIONS` tuple (lines 68-72, `_Operation("novel-state", …)` ×5, fed to
  `driver.legacy(op.legacy_build, op.spaced[1:], op.legacy_name)` at line 135-136)
  **and** a hardcoded call:
  `driver.legacy(_novel_done.build_app, [], "novel-done")` at **line 156**, with
  `_strip_command` at line 161.

WI4 step 7 names only `_Operation` and `_strip_command`; it does **not** mention
the line-156 hardcoded `"novel-done"` site or its line-161 `_strip_command`
usage. If the implementer follows step 7 literally, `test_multiplexer_done_success_matches_legacy`
still stamps `"novel-done"` after the guard narrows → `ValueError`. And because
no gate scans this module for `$LEGACY`, the omission is caught only by `make all`
failing inside WI4 — the late, confusing fault the plan set out to prevent by
construction (the parity rework happens in WI4 step 7, *after* the guard narrows
in WI4 step 2).

Fix: (1) WI4 step 7 must enumerate *all* `driver.legacy(…)` call sites and all
`_strip_command` usages in `test_multiplexer_behaviour.py`, including the
hardcoded line-156/161 case, not just `_OPERATIONS`/the parametrized test; and
(2) add `tests/test_multiplexer_behaviour.py` (and `tests/multiplexer_support.py`)
to the D3/closing `$LEGACY` source gate so the rework's completeness is proven by
construction rather than discovered by a failing `make all`.

## Advisory (non-blocking)

- A4: Two inert legacy-name literals survive in `tests/` after the task and are
  not enumerated by the plan: `tests/test_contract_app_factory.py:25/37`
  (`make_contract_app("novel-state")` and `assert contract_app.name ==
  ("novel-state",)` — an arbitrary app-name label that never reaches
  `build_envelope`, same inert class as the D5 conftest case) and
  `tests/steps/per_chapter_loop_installed_steps.py:77-81` (legacy names used only
  as local `installed.captures[…]` dict keys and `_LOOP_ARGV` lookup keys; the
  subprocess runs the `novel` binary with spaced argv via `_run_installed_argv`).
  Neither breaks the guard, and neither violates a *stated* acceptance gate (the
  closing gate checks `$REG_GATE`, `$SNAP_GATE`, and `pyproject.toml` console-
  script literals, not a blanket `$LEGACY` scan over all of `tests/`). But the
  plan's Purpose prose ("a repository-wide … grep for … the legacy entry-point
  literals returns no match in `… tests/`") over-claims: these two literals will
  remain. Either enumerate and re-point them (preferred, to match the prose) or
  soften the Purpose/Acceptance wording to the symbol-and-`command`-value gates
  the plan actually runs.

- A5: D6 evidence says `command="novel-state"` is "5 BDD-step code sites plus this
  one docstring line"; the live grep shows **6** code sites (compile_steps.py has
  two: lines 74 and 94) plus the docstring = 7. The per-file WI2 sweep still
  catches both compile_steps lines, so this is a counting slip in the evidence
  note, not a gate defect — but correct it so the implementer does not stop after
  five.

## What checks out (verified this round; the next round need not re-verify)

- B1 fixed: `$SNAP_GATE` (three serialisations) matches exactly the 12 snapshot
  files, and the set of files carrying *any* legacy literal equals the set
  carrying a `command:`-position legacy value (no legacy name hides in args/
  messages/help). The gate is complete for snapshots.
- B4 fixed: `rg '\bCOMMAND_NAMES\b' novel_ralph_skill/commands/novel.py` returns
  nothing; the anchored `$REG_GATE` excludes `SUBCOMMAND_NAMES`.
- B3 (matrix) fixed *for the matrix file*: lines 127-131 (`_ReadCommand`), 495/497
  (`if name ==`), and 581/610/632/678/716 (`_BY_NAME[…]`) are real and now
  enumerated; symbol names `_ReadCommand`/`_ErrorArm` are correct (A1).
- B5 fixed: the load-bearing docstring at `test_novel_state_mutators.py:14` is
  swept in WI2 step 1 under the Constraints carve-out; the `command="…"` D3 gate
  is genuinely empty after a correct sweep.
- Production consumer set is exactly `{names.py, stub.py, envelope.py}` for the
  doomed symbols; `ENVELOPE_COMMAND_NAMES` consumers are `envelope.py`, `names.py`,
  `test_contract_envelope.py` — all handled. `envelope.py:113` guard as described.
- D1 is implementable: `multiplexer_support.py`'s `_legacy` arm
  (line 114-118) drives `build_app()` directly, never a removed symbol; the
  rename-to-`direct` + spaced-name + full-envelope-equality (dropping
  `_strip_command`) is strictly stronger — modulo the line-156 omission (B7).
- D2 dead-scaffolding: `make_stub_app`/`STUB_EXIT_CODE` are consumed only by
  `stub.py` and `test_command_stubs.py`; both deleted. Correct.
- The 6 in-process `stub.<entry>()` e2e modules (WI3) match the live grep exactly.
- The three installed-binary e2e modules I suspected (`test_desloppify_e2e.py`,
  `test_wordcount_e2e.py`, `test_ai_isms_e2e.py`) are already on the multiplexer:
  they install `novel` and invoke `sh.make(Program(novel))("desloppify")` — the
  `"desloppify"`/`"wordcount"` strings are argv verbs, not legacy console-script
  names. No defect there.
- cuprum 0.1.0 / cyclopts 4.18.0 unchanged; task touches no cuprum call site;
  "no further cuprum verification load-bearing" stands.

## Pre-mortem

It is WI4. The implementer ran the four D3 gates (all empty, because none scans
`per_chapter_loop_steps.py` or `test_multiplexer_behaviour.py`), narrowed
`ENVELOPE_COMMAND_NAMES`, and ran `make all`. `test_per_chapter_loop_bdd.py` and
`test_multiplexer_done_success_matches_legacy` fail with
`ValueError: unknown command 'novel-state'` from `build_envelope`. The
"complete-by-construction" promise did not hold because the gates proved
emptiness over a *subset* of the stamping idioms. Recoverable (the worktree is
disposable, `make all` catches it), but it is precisely the late, confusing fault
the plan's gate apparatus is supposed to make impossible — and the fix is a
mechanical sweep plus two gate extensions, so it belongs in the plan, not in an
implementer's debugging session.

## Strongest alternative (Wafflecat)

Replace the hand-maintained file-name lists in the gates with a single
**idiom-complete** source gate: scan every test module for
`RunContext(command=X)` where `X` is *not* the swept `_COMMAND` constant, and
assert the resolved literal set is a subset of the spaced names. Concretely, a
WI6 manifest test could import each BDD-step module's `_BUILD_APPS`/`_OPERATIONS`/
`_READ_REGISTRY` table and assert every command key is in `SUBCOMMAND_NAMES`.
This is structurally stronger than enumerating file names because it cannot
silently miss a module (the matrix, `per_chapter_loop_steps`, and the parity
suite are all instances of the same "table of (name, build_app)" pattern). Trade:
slightly more upfront test scaffolding versus durable immunity to the
"missed-a-module" failure that has now recurred twice (B3, B6).

## Trail

Read (disk): execplan `roadmap-1-2-15.md`, `roadmap-1-2-15.logisphere-review-r1.md`;
`novel_ralph_skill/commands/{names,stub}.py`, `contract/envelope.py`;
`tests/multiplexer_support.py`, `tests/test_multiplexer_behaviour.py`,
`tests/test_command_surface_matrix.py`, `tests/test_contract_app_factory.py`,
`tests/steps/per_chapter_loop_steps.py`,
`tests/steps/per_chapter_loop_installed_steps.py`,
`tests/test_desloppify_e2e.py`, `tests/test_wordcount_e2e.py`; all
`tests/__snapshots__/*.ambr`; `docs/roadmap.md` (1.2.12-1.2.16). Verified the
gate patterns (`$REG_GATE`, `$SNAP_GATE`, the D3 `command=`/`_COMMAND=` scans, the
matrix-aware `$LEGACY` scan) by running them against the live worktree. cuprum
source at `/data/leynos/Projects/cuprum`. Skill: `logisphere-design-review`.
