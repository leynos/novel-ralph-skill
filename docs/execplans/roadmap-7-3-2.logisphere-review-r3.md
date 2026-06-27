# Logisphere design review — ExecPlan roadmap 7.3.2, round 3

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-27.

## Verdict

PROCEED. The plan is implementable and design-conformant as written. Every
load-bearing claim was re-verified against real source in the worktree and the
read-only cuprum sibling checkout; the round-3 fix (the keys-vs-values
correction) resolves the only blocking defect from round 2.

## What was verified against source (not the planner's summary)

- `_SUBCOMMAND_FOR_VERB` exists at `novel.py` lines 51–53; its **keys are the
  bare verbs** `['state','done','compile','desloppify','wordcount']` in surface
  order, built from `_VERB_FOR_SUBCOMMAND.items()` which is built from
  `SUBCOMMAND_NAMES`. Confirmed in the project venv (`uv run python`):
  - `list(novel._SUBCOMMAND_FOR_VERB)` == the five bare verbs in surface order.
  - `list(novel._VERB_FOR_SUBCOMMAND)` == the five **spaced** names.
  - The two key sets are **disjoint** (overlap empty), so the round-2 comparand
    `set(table) == set(_VERB_FOR_SUBCOMMAND)` is always `False` — the bug the
    plan now fixes is real.
  - `build_multiplexer()` registers exactly `{state,done,compile,desloppify,
    wordcount}`, equal to `set(_SUBCOMMAND_FOR_VERB)`.
- The prescriptive mount loop `for verb in _SUBCOMMAND_FOR_VERB:
  app.command(table[verb](), name=verb)` binds bare verbs, indexes the table
  successfully, and registers the bare mount names the shape test expects.
- All five leaf modules expose `build_app`
  (`novel_state`,`_novel_done`,`_compile`,`_desloppify`,`_wordcount`).
- `make_contract_app(name)` at `runner.py:52`.
- `test_legacy_surface_retired.py:66` asserts
  `not hasattr(names, "COMMAND_ENTRY_POINTS")` — the symbol stays retired, so
  Decision D1's reinterpretation is mandatory, not optional.
- `test_multiplexer_dispatch.py:47` asserts the five-name set exactly.
- `pyproject.toml:11` binds the single `novel` script;
  `pyproject.toml:93` per-file-ignores S101 for `**/test_*.py` (bare `assert`
  is correct house style).
- AGENTS.md 400-line cap and 100% interrogate coverage gates exist as cited.
  `novel.py` is 165 lines; adding `_build_mount_table` keeps it far under 400.
- developers-guide line 420 reads verbatim "The spaced subcommand names live
  once, as data, in a single registry"; the `novel` multiplexer section runs
  from ~line 433, so "after line ~445" is the right landing site.
- cuprum `ProgramCatalogue` at `catalogue.py:59`, `projects=`-constructed
  (`__init__` line 62), `is_allowed`/`allowlist` (lines 70–77) — the plan's
  non-load-bearing claim is accurate. cuprum 0.1.0 / Cyclopts 4.18.0 locked.
- `inspect.getsource` works on both `_build_mount_table` (will hold the deferred
  imports) and the whole module, so the textual laziness guard is implementable
  exactly as described.

## Crew findings

- Pandalump (structure): boundaries clean. The table is local to a function-
  scoped helper, dependency direction flows leaf→table→parent, the registry
  remains the single source of the verb set. No god object, no circular import,
  no hidden coupling. The reinterpretation (D1) draws the boundary where the
  real surviving duplication lives.
- Wafflecat (alternatives): the strongest alternative — iterate
  `SUBCOMMAND_NAMES` directly and split the verb inline — was implicitly
  rejected because it would re-introduce inline verb derivation in the mount
  path, the very repetition the task removes. Keying the table by bare verb and
  iterating `_SUBCOMMAND_FOR_VERB` is the simpler, registry-anchored choice. No
  superior alternative exists; that is a strength signal.
- Buzzy Bee (scaling): irrelevant at this scale — five-entry table built once per
  `main()`. No fan-out, no unbounded operation, no cost concern. The factory-not-
  return-value table (D3) preserves build-then-mount timing.
- Telefono (contracts): no wire-format, exit-code, or signature change. The
  four-flag contract is preserved by reusing `make_contract_app` and
  `app.command`. Mount semantics (flags not copied) are pinned by the existing
  behaviour and dispatch suites, not asserted from memory.
- Doggylump (failure modes): the KeyError-on-drift behaviour is a loud,
  test-caught failure, not a silent drop. The structural test pins the verb set
  and the per-leaf identity. The laziness guard is self-proving (must go red
  against a hoisted import). Rollback is a one-file revert.
- Dinolump (viability): low cognitive load, mainstream Python, no new
  dependency, mirrors the 7.3.1 single-home refactor house style. Maintainable.

## Pre-mortem (2 scenarios)

1. A future edit hoists the table to module scope, eagerly importing the five
   leaves and breaking import laziness. Mitigated by the Work-item-3 textual
   guard (must fail against a hoist; self-proof step required).
2. A future edit drops or mis-keys a mount. Mitigated by the Work-item-1
   structural test: verb-set equality against the registry plus per-leaf
   `build_app` identity; the mount loop also raises KeyError on a registry verb
   the table omits.

## Advisory (non-blocking)

- A1 — Mount/table **order** is pinned only by construction (iterating
  `_SUBCOMMAND_FOR_VERB`, which is in surface order), not by an explicit test.
  The plan correctly notes Cyclopts mount order has no observable dispatch
  effect, so this is acceptable; no test is required. If cheap, the implementer
  could assert `list(novel._build_mount_table()) == list(novel._SUBCOMMAND_FOR_VERB)`
  (ordered) in addition to the set equality, to pin order as well as membership.
  Not blocking — order is a non-observable property and the iteration source
  guarantees it.

No design constraint was relaxed in this review. The deterministic/judgemental
boundary is untouched (pure dispatch-layer refactor). The plan is sound.
