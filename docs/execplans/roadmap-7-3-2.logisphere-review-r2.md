# Logisphere design review — roadmap 7.3.2 — Round 2

Adversarial pre-implementation review of `docs/execplans/roadmap-7-3-2.md`
(Collapse the multiplexer mount lines onto a registry-driven construction table),
revised in round 2 to resolve the round-1 blocking defects.

Verdict: **Blocked — one load-bearing implementation/test defect.** The round-1
defects (B1 bare-`assert` false premise; B2 unimplementable fresh-import idiom)
are both correctly fixed and verified against real source. However, in tightening
the prescriptive end-state, the revision introduced a keys-vs-values confusion in
the registry iteration that makes both the central mount loop and the central
acceptance test non-functional as written. Both must be corrected before
implementation.

## What I re-verified against real source (all confirmed)

- **B1 fix is correct.** `pyproject.toml` line 93 sets
  `"**/test_*.py" = ["S101", "PLR0913", "PLR0917", "PLR2004", "PLR6301"]`; S101
  is per-file-ignored for test modules. `tests/test_multiplexer_dispatch.py`
  (lines 47, 58, 69, 99, 121, 144) uses bare `assert`. The plan now correctly
  instructs bare `assert` and drops the `AssertionError`-helper instruction.
- **B2 fix mechanism is implementable.** `grep -rn "sys.modules" tests/` returns
  zero matches; `tests/test_legacy_surface_retired.py:72` uses
  `importlib.util.find_spec` (importability, not prior import). The plan's claim
  that no reusable fresh-interpreter idiom exists is true, and the in-process
  `inspect.getsource` textual guard is mechanically feasible: confirmed in the
  project venv that `inspect.getsource(novel.build_multiplexer)` starts at
  column 0 (`def …`) with the internal leaf import indented four spaces, while a
  module-scope hoist would place `from novel_ralph_skill.commands import` at
  column 0 of `inspect.getsource(novel)`. The guard distinction holds. There are
  no column-0 leaf imports in `novel.py` today.
- **Cyclopts / cuprum / D1** — re-confirmed as in round 1; unchanged and correct.
- **developers-guide line 420 verbatim** — "The spaced subcommand names live
  once, as data, in a single registry." The plan now quotes it verbatim
  (A3 resolved). The collection-error check (A2) is folded into Work item 1.

## Blocking defect (back to the planner)

### B3 — The mount loop and the verb-set test confuse the registry dict's KEYS

The mount loop and the verb-set test confuse the registry dict's KEYS with its
VALUES; both are non-functional as written.

`_VERB_FOR_SUBCOMMAND` is `{spaced_name: verb}` — its **keys** are the spaced
registry names (`"novel state"`, `"novel done"`, …) and its **values** are the
bare mount verbs (`"state"`, `"done"`, …). Confirmed by reading
`novel.py` lines 46–48 and by executing the comprehension in the project venv:

```plaintext
list(_VERB_FOR_SUBCOMMAND)         -> ['novel state', 'novel done', ...]   # KEYS = spaced
list(_VERB_FOR_SUBCOMMAND.values()) -> ['state', 'done', 'compile', ...]    # VALUES = verbs
```

The construction table (`_build_mount_table()`) is keyed by the **bare verbs**
(`{"state": …, "done": …}`). The plan therefore breaks in two load-bearing
places:

1. **Prescriptive mount loop** (Interfaces and dependencies, lines 702–704; and
   Work item 2.2, line 470):

   ```python
   for verb in _VERB_FOR_SUBCOMMAND:        # yields "novel state", NOT "state"
       app.command(table[verb](), name=verb)
   ```

   `for verb in _VERB_FOR_SUBCOMMAND` binds `verb = "novel state"` on the first
   iteration. `table["novel state"]` raises **`KeyError: 'novel state'`** because
   the table is keyed by `"state"`. Executed in the venv: confirmed `KeyError`
   on the first iteration. Even if the lookup were patched, `name=verb` would
   register the mount as `"novel state"` rather than `"state"`, changing the
   command surface and failing
   `tests/test_multiplexer_dispatch.py::test_build_multiplexer_registers_the_five_subcommands`.
   As written, the prescribed `build_multiplexer()` never builds; every test
   fails at collection/call.

   The plan's own justification compounds the error: line 472–474 claims the loop
   makes "a verb the registry names but the table omits raise `KeyError`" — that
   reasoning only holds if the loop iterates the verbs (the table keys), which it
   does not.

2. **Prescriptive verb-set test** (Work item 1, item 1, line 399):

   ```python
   set(novel._build_mount_table()) == set(novel._VERB_FOR_SUBCOMMAND)
   ```

   LHS = `{"state","done","compile","desloppify","wordcount"}` (table keys = bare
   verbs). RHS = `{"novel state","novel done", …}` (dict keys = spaced names).
   The two sets are **disjoint**; the assertion is **always False**. Confirmed in
   the venv. The plan's central acceptance test can therefore never go green even
   after a correctly-implemented Work item 2 — red→green is unreachable.

**Required fix.** Iterate / compare against the registry's **verbs**, not its
spaced-name keys. Either:

- iterate `for verb in _VERB_FOR_SUBCOMMAND.values():` (registry order preserved,
  since dict values follow insertion order from `SUBCOMMAND_NAMES`), and compare
  `set(_build_mount_table()) == set(_VERB_FOR_SUBCOMMAND.values())`; **or**
- iterate `for verb in _SUBCOMMAND_FOR_VERB:` (its keys ARE the bare verbs, in
  registry order) and compare against `set(_SUBCOMMAND_FOR_VERB)`.

Pick one and apply it consistently across: the Interfaces-and-dependencies
prescriptive block (lines 700–704), Work item 2.2 (line 470), the Work item 1
verb-set test (line 399), and Work item 1 item 3 (line 409–411, which re-uses
`set(novel._build_mount_table())`). The KeyError-on-omission drift-guard rationale
(lines 472–474; Wafflecat alternatives note in r1) survives intact under the
`.values()` form — a verb the registry names but the table omits still raises
`KeyError` — but only once the loop iterates verbs rather than spaced names.

This is the load-bearing defect: the task warns reviewers to read the execplan
from disk because the prescriptive code is the artefact the implementer copies.
Copied literally, it produces a multiplexer that cannot build and a test that
cannot pass.

## Advisory (non-blocking)

- A5 (Telefono / typing): the prescribed return type
  `dict[str, cabc.Callable[[], cyclopts.App]]` is accurate — each leaf
  `build_app` is `() -> cyclopts.App` (verified: `novel_state.build_app:263`,
  `_compile.build_app:250`, `_wordcount.build_app:166`). `cabc` and `cyclopts`
  under `TYPE_CHECKING` is consistent with the current module (line 40–41). No
  change needed beyond fixing B3.
- A6 (Doggylump / guard precision): the laziness guard's column-0 scan should be
  explicit that it runs over `inspect.getsource(novel)` (whole module) and must
  exclude the helper's own indented import from the column-0 match set. The plan
  prose (lines 564–570) covers this but loosely; spell out that the column-0
  predicate is `line.startswith("from novel_ralph_skill.commands import")` (no
  leading whitespace) so the indented helper import is structurally excluded.
- A7 (Buzzy Bee): non-issue, as r1 A4 — table rebuilt once per `main()`; cost
  irrelevant.

## Pre-mortem (Doggylump)

1. **Most likely failure:** the implementer copies the prescriptive
   `build_multiplexer()` verbatim, `make all` fails immediately with
   `KeyError: 'novel state'`, and — because the failure is in the prescribed
   end-state rather than the implementer's own code — they burn the
   3-iteration tolerance trying to "fix" code that matches the plan, then
   escalate. Mitigation: fix B3 in the plan text (iterate `.values()` or
   `_SUBCOMMAND_FOR_VERB`).
2. **Second failure:** the implementer writes the Work item 1 verb-set test as
   prescribed, it stays red after a correct Work item 2, and they conclude the
   refactor is wrong. Mitigation: same B3 fix applied to the test.
3. **Bet that holds:** the laziness guard and the Cyclopts mount-semantics claim
   are sound (re-verified). No action.

## Alternatives checkpoint (Wafflecat)

The r1 alternative ("iterate the table directly,
`for verb, factory in table.items()`") is now *more* attractive given B3, because
it sidesteps the keys-vs-values trap entirely: `table.items()` yields
`(verb, factory)` pairs already keyed by bare verbs in registry order (the table
is built in `SUBCOMMAND_NAMES` order). It is simpler and removes the indexing
mismatch. The plan deliberately rejects it to keep the *registry* (not the table)
the single source of the verb sequence and to turn divergence into a loud
`KeyError`. That trade is still defensible — but only once the registry-iteration
form is corrected to iterate verbs. If the planner prefers minimal surface area,
adopting `table.items()` plus a separate assertion that the table keys equal the
registry verbs would achieve the same drift-guard with less rope; either is
acceptable, both require the keys-vs-values correction to be coherent.

## Bottom line

The round-1 fixes (B1, B2) are correct and verified. The revision then mis-wired
the registry iteration (keys vs. values), breaking both the prescribed
`build_multiplexer()` (KeyError on build) and the prescribed acceptance test
(always-False comparison). Fix B3 across the four cited locations — no design
constraint changes; this is a correction to the plan's prescriptive code and test
so they match the registry's actual shape — then this is implementable.
