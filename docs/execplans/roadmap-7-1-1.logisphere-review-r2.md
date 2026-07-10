# Logisphere design review — roadmap 7.1.1 (round 2)

Adversarial pre-implementation review of `docs/execplans/roadmap-7-1-1.md`
(single-source the compile-currency projection and the `compiled.md` path seam).

Verdict: **Proceed.** Both round-1 blocking defects are resolved, both round-1
advisories are actioned, and every load-bearing claim — including the plan's
self-described "intended 7.1.2 prose remains" end state — was re-verified
against the worktree source and matches exactly. No new blocking defect found.

## Round-1 defect closure (re-verified against source)

- **Defect 1 (path observable overclaimed 7.1.2 prose) — RESOLVED.** Purpose
  now states the observable as the quoted code-join form
  `git grep -n '"manuscript" / "compiled.md"'` (plan lines 75-80) and
  explicitly disclaims the slash-form docstring mentions. Verified: that quoted
  form matches only the four code joins (`_compile.py:147`,
  `_novel_done.py:128,173`, `compile_model.py:105`); after WI3 only the
  `compile_model.py` seam survives.
- **Defect 2 (MATCHES observable overclaimed 7.1.2 prose) — RESOLVED.** Purpose
  now scopes to `is CompiledComparison.MATCHES` (plan lines 68-74) and disclaims
  the `:attr:` docstring refs. Verified: the `is`-prefixed form hits only the
  two routing sites (`_compile.py:221`, `done_predicate.py:263`); the bare
  docstring refs at `_compile.py:184` and `done_predicate.py:229` survive as
  intended 7.1.2 prose.
- **Advisory (WI3 step 3 phantom import block) — ACTIONED.** WI3 step 3
  (plan lines 543-551) now says to add a new
  `from novel_ralph_skill.state import compiled_manuscript_path` statement.
  Verified: `_novel_done.py` has no existing `compile_model`/state import (its
  only `state` import is `from ...state.done_predicate import DoneClauses,
  evaluate_done`, line 51); `Path` is imported only under `TYPE_CHECKING`
  (line 53-54) with `from __future__ import annotations`, but the new import is
  a runtime call (`.exists()`), so a runtime import is required and correct.
- **Advisory (red-first evidence) — ACTIONED.** WI2/Progress (plan lines
  250-257) now records the remove-member→red→restore→green dance into
  `Surprises & discoveries` so the proof survives compaction.

## Source verification (round 2, all re-confirmed)

- `is CompiledComparison.MATCHES`: exactly two sites, `_compile.py:221`,
  `done_predicate.py:263`. The seam's own projection will be the only surviving
  hit after WI3.
- `_COMPILED_REL`: 8 sites in `_compile.py` — def at 74, uses at
  156,161,165,225,229,234,240. The plan's WI3 enumeration
  "156,161,165,225,229,234,240" is exact and complete (234 is the second
  `"checked"` key, confirmed by reading the divergence branch).
- Code joins `"manuscript" / "compiled.md"`: four sites — `_compile.py:147`
  (write), `_novel_done.py:128,173` (`.exists()`), `compile_model.py:105`
  (internal read). All four are in the plan's routing set.
- The plan's combined "intended 7.1.2 prose remains" list
  (`_compile.py:5,110,184`, `_novel_done.py:164`, `done_predicate.py:86,217,229`)
  is the *exact* union of the loose path-form hits (`_compile.py:5,110`,
  `_novel_done.py:164`, `done_predicate.py:86,217`) and the loose MATCHES-form
  hits (`_compile.py:184`, `done_predicate.py:229`). No stray, no omission.
- Detector polarity untouched: `disk_evidence.py:209`
  `is not CompiledComparison.DIVERGES` — correctly excluded (non-goal).
- `working_dir()` returns the bare `working/` segment
  (`WORKING_DIR_NAME = "working"`, `_state_load.py:36-47`); the working-prefix
  asymmetry (token is `working/manuscript/compiled.md`; the `Path` join must
  not double it) holds.
- Token byte-value pinned by `test_compile_check_unit.py:117`,
  `test_compile_unit.py:114`, `contract_drive_support.py:90`
  (`DETERMINISTIC_PATH_TOKEN`), the BDD feature/steps, and the snapshot suites
  (`test_command_surface_matrix.ambr`, `test_compile_check_snapshots.ambr`,
  `test_compile_snapshots.ambr`, `cross_command_contract/.../test_error_channels.ambr`).
- Export pattern: `state/__init__.py` import block 30-36 and `__all__`
  (`CompiledComparison` line 120, `compiled_matches_drafts` line 141) — adding
  three names mirrors the established pattern.
- `done_predicate.py` import block at 49-52; after routing, `CompiledComparison`
  remains only in docstrings (37, 224-225, 229), so the "drop iff no other
  reference remains" guard fires and Ruff F401 backstops it.
- `_compile.py` imports `CompiledComparison` at line 58 from the package
  surface; sole runtime use is line 221; after routing it survives only in
  docstrings (184-186), so the same conditional drop applies.
- `test_compile_model_seam.py` does not yet exist → WI2 red-first is genuinely
  viable.
- No external-library (cuprum / Cyclopts / pytest-timeout / uv) behaviour is
  load-bearing: no new subprocess, flag, or import crosses a library boundary.
  The plan's "Verified external facts" §1 is accurate; the existing e2e suites
  (`test_compile_e2e.py`, `test_novel_done_e2e.py`) pin installed behaviour
  through cuprum's catalogue and stay green unedited.

## Panel findings

- 🐼 **Pandalump (structural).** Boundaries are right: the projection and the
  path both move to their natural owner (`compile_model.py`), and the
  two-member seam (`compiled_manuscript_path` `Path` join + `COMPILED_REL`
  string token) correctly refuses to hide the working-prefix asymmetry. No
  layering inversion: `compile_model.py` (state) gains no command dependency;
  the consumers import down into state, as they already do. 🟢
- 🐈🧇 **Wafflecat (alternatives).** Strongest alternative — collapse to one
  member by deriving the token from
  `compiled_manuscript_path(working_dir()).as_posix()` — was examined in r1 and
  rejected for re-introducing the asymmetry-hiding transform the Decision Log
  forbids. Re-confirmed: `working_dir()` already yields `working`, so a single
  member would either double the prefix or need a special-case. The two-member
  split is the better call. No new alternative of merit. 🟢
- 🐝 **Buzzy Bee (scaling).** N/A by construction — this is a pure-function
  refactor with no new I/O, allocation, or call-graph depth. The seam functions
  are O(1) wrappers over existing literals. 🟢
- ☎️ **Telefono (contracts).** ADR-003 envelope/exit-code contract is preserved:
  no `result` key, message string, exit code, or token byte moves; the
  snapshot, BDD, and e2e suites are the contract net and stay unedited. The new
  public symbols (`compile_is_current`, `compiled_manuscript_path`,
  `COMPILED_REL`) are
  additive exports with stable signatures pinned by WI2. 🟢
- 🐶 **Doggylump (failure modes).** The r1 pre-mortem hazard — an auditor runs a
  loose grep, sees docstring hits, and "fixes" them into 7.1.2 territory — is
  now neutralized at the source: the plan's stated observables match the actual
  end state, and the Purpose section and Decision Log explicitly name the
  surviving prose hits as the *correct* state with a do-not-touch instruction
  (plan lines 62-66, 297-310). 🟢
- 🦕 **Dinolump (long-term viability).** The refactor reduces duplication and
  hands 7.1.2 a clean prose-only follow-up, with the executable/prose boundary
  drawn explicitly so the next task is unambiguous. Sustainable. 🟢

## Pre-mortem (Doggylump)

The dominant six-months-later incident from r1 (docstring drift via loose-grep
misreading) is now designed out: the observables are narrowed to executable
forms and the intended-prose-remains state is enumerated verbatim and matched
against source. The genuine residual structural hazard — the working-prefix
asymmetry producing a doubled `working/` and moving a snapshot — is defended by
(a) two distinct seam members, (b) WI2's assertion that
`compiled_manuscript_path(Path("working")).as_posix() == COMPILED_REL`, and
(c) the snapshot suites as a loud backstop (Tolerance: any snapshot move →
stop and escalate). No mitigation gap remains.

## Conditions

None. The two round-1 blocking defects are closed and re-verified; the two
advisories are actioned. The plan is implementable and design-conformant as
written.

Docs and skills relied on: `logisphere-design-review`; design doc
§4.2/§4.3/§5.4; `docs/issues/audit-4.1.2.md` (Findings 1/2 in scope, 3 = 7.1.2,
4 = out of scope); `docs/roadmap.md` 7.1.1; ADR-001 (detect-only), ADR-003
(envelope contract); AGENTS.md. Source verified directly in the worktree
(`compile_model.py`, `_compile.py`, `done_predicate.py`, `_novel_done.py`,
`_state_load.py`, `state/__init__.py`, `disk_evidence.py`, and the cited tests
and snapshots).
