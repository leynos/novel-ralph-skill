# Logisphere design review — ExecPlan roadmap-7-3-5, round 2

Adversarial pre-implementation review of `docs/execplans/roadmap-7-3-5.md`
(DRAFT, revision 2). Verdict: **Proceed with conditions** — every round-1
blocking defect is genuinely closed and every load-bearing claim verifies
against real source. One advisory-grade misattribution remains (the ast-scanner
exemplar) and should be corrected before implementation, but it does not gate
the design.

Trail followed: `logisphere-design-review` skill; round-1 review
(`docs/execplans/roadmap-7-3-5.logisphere-review-r1.md`); roadmap task 7.3.5
(`docs/roadmap.md:3040-3066`); real source for `novel.py`,
`contract/runner.py`, `contract/__init__.py`; the tripwire
(`tests/test_contract_app_centralisation.py`); the scanner exemplars
(`tests/_state_layout_scanner.py`, `tests/test_multiplexer_mount_table.py`,
`tests/test_loaderkit_scan.py`, `tests/test_state_sourcing_home.py`); legacy
guards (`tests/test_legacy_surface_retired.py`, `tests/conftest.py`);
`uv.lock` for cuprum/Cyclopts; `Makefile`.

## Round-1 defects — all closed

- **B1 (tripwire breaks, unmentioned).** Closed. The plan now enumerates
  `test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`
  in Surprises S2, Risks, Context, and Work item 2, which migrates the patch
  target from `novel.run` to `novel.drive`. Verified against source: that file
  is the *only* one doing `setattr(novel, "run", …)` (lines 98/112/122/129
  match the plan's citations exactly).
- **B2 (WI3 guard contradicts existing test).** Closed. Decision D5 reconciles:
  after extraction `main` routes through `drive`, so both the migrated tripwire
  ("main routes through drive") and the WI3 structural guard ("main makes no
  direct run/RunContext Call") describe the same post-extraction surface.
- **B3 (caller enumeration wrong).** Closed. `grep -rln 'novel\.main()' tests/`
  returns exactly 12 files; the plan's 1 plumbing-asserting / 10 pure-behaviour
  / 1 source-scan classification is correct. Independently confirmed none of the
  8 e2e suites patch `run`/`drive`/`RunContext` on `novel`, so they genuinely
  route `main → drive → run` unchanged.
- **B4 (duplicate pyproject guard).** Closed. Decision D7 drops the fresh
  pyproject parser and references the existing
  `test_pyproject_scripts_is_novel_only` / `test_script_table_is_novel_only`
  (both present, using the `pyproject`/`project_scripts` conftest fixtures).
- **A1 (`make all` ≠ audit).** Closed. `Makefile:37` is
  `all: build check-fmt lint typecheck test`; `audit` is the separate target at
  `:114`. Decision D6 separates the gate throughout.
- **A2 (doctest hazard).** Closed. Decision D4 specifies a prose usage note, not
  a process-killing doctest; mirrors `run`'s own prose-only docstring.
- **A3 (import line).** Closed. Work item 2 spells out the exact edit to
  `from novel_ralph_skill.contract import drive, parse_global_flags`.

## What verifies (independent of round 1)

- `runner.py` is 250 lines (D3 fallback moot); `run` is `typ.NoReturn`;
  `RunContext` is a `frozen, kw_only` dataclass with exactly
  `command`/`working_dir`/`human`. The D2 seam body type-checks against the
  real symbols.
- `contract/__init__.py` carries `__all__` and a module-docstring surface list,
  so the `drive` re-export has a defined home.
- `runner.py` imports no `commands` module today, so the WI4 layering guard
  pins a currently-true invariant.
- cuprum 0.1.0 and Cyclopts 4.18.0 are the locked versions (`uv.lock`); cuprum
  is test-only and the seam shells out to nothing, so "no new cuprum surface"
  holds. No new Cyclopts behavioural claim is introduced.
- The roadmap success criterion's "parametrized by the command-name resolver"
  is satisfied in substance by D1/D2's command-agnostic seam (taking the
  *resolved* name as an argument, leaving the resolver in `main` where the
  value-carrying-flag guard lives). The round-1 reviewer endorsed this
  mechanism; the Risks section documents the trade-off. Defensible, not
  blocking.

## Advisory (non-blocking) — correct before implementing

- **A4 — ast-scanner exemplar is misattributed.** Work items 3 and 4 tell the
  implementer to "mirror the FunctionDef-scoped `ast` walk in
  `tests/_state_layout_scanner.py` / `tests/test_multiplexer_mount_table.py`."
  Neither file uses `ast`: `_state_layout_scanner.py` is a regex markdown
  scanner, and `test_multiplexer_mount_table.py` uses `inspect.getsource` plus
  substring matching. The genuine in-repo ast exemplars are
  `tests/test_loaderkit_scan.py::test_loaderkit_scan_imports_no_pack_domain`
  (a module-scope `ast.parse` + `ast.walk` over `Import`/`ImportFrom` — the
  exact shape Work item 4's layering guard needs) and
  `tests/test_state_sourcing_home.py` (`_seam_imports_from_novel_state`,
  another `ast.walk` import scan). Re-point the "Read first" / "mirror"
  references at these two files. The prescribed *technique* (ast walk) is sound
  and achievable; only the cited exemplars are wrong.

## Pre-mortem (Doggylump)

The round-1 incident path (implementer deletes the tripwire assertion instead
of migrating it) is now designed out: Constraints forbid deletion, Work item 2
specifies the exact migration, and Risks rates it high/medium with the
mitigation pinned at both joints (`main → drive` and `drive → run`). The
residual 03:00 risk is minor: an implementer who follows the misattributed
A4 exemplars writes a substring-based guard instead of an ast guard, which the
plan's own Risk ("structural guard test is brittle") already flags. Fixing A4
removes that foot-gun.

## Alternatives checkpoint (Wafflecat)

Unchanged from round 1: folding `RunContext` construction into `run` via a
keyword-scalar overload would remove the new symbol but widen `run`'s signature
(a Tolerances escalation trigger) and blur the "run owns exit/emit; the entry
point owns resolution" boundary. The thin-wrapper seam remains the better call.
No credible alternative displaces the chosen mechanism.

## Verdict

**Proceed with conditions.** The design is implementable and design-conformant
as written. Condition: correct the A4 exemplar references (point Work items 3
and 4 at `test_loaderkit_scan.py` / `test_state_sourcing_home.py` for the ast
pattern). This is a documentation correction inside the plan, not a design
change; it does not require a further review round.
