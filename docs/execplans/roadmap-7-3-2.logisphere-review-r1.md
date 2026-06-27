# Logisphere design review — roadmap 7.3.2 — Round 1

Adversarial pre-implementation review of
`docs/execplans/roadmap-7-3-2.md` (Collapse the multiplexer mount lines onto a
registry-driven construction table).

Verdict: **Proceed with conditions.** The plan's structural thesis, its
load-bearing reinterpretation of the stale roadmap text, and its single
external-library claim are all verified correct against real source. The
blocking defects are two false premises about the *test infrastructure* that
misdirect the implementer; both are mechanically fixable in the plan text
without relaxing any design constraint.

## What I verified against real source (all confirmed true)

- **Source shape.** `novel.py` lines 56–91 are exactly the five hand-copied
  mount lines under deferred imports the plan describes; `_VERB_FOR_SUBCOMMAND`
  (lines 46–48) is the registry-derived verb map. `names.py` `SUBCOMMAND_NAMES`
  (lines 40–46) is the five spaced names in surface order. `pyproject.toml`
  line 11 binds the single `novel` script. (`novel.py`, `names.py`,
  `pyproject.toml` read directly.)
- **D1 reinterpretation is correct and necessary.** `docs/roadmap.md`
  lines 2849–2871 do say "four entry-point functions" and "keyed off
  `COMMAND_ENTRY_POINTS`"; both are retired. `tests/test_legacy_surface_retired.py`
  line 66 asserts `not hasattr(names, "COMMAND_ENTRY_POINTS")`. The literal
  reading is impossible; the plan's reroute onto a `SUBCOMMAND_NAMES`-keyed
  table is the faithful interpretation.
- **Cyclopts 4.18.0 mount semantics — VERIFIED AGAINST REAL SOURCE, claim is
  true.** `App.command()` for an `App` child calls
  `_apply_parent_defaults_to_app(app, self)`, which mutates only
  `_group_commands`, `_group_parameters`, `_group_arguments`, and `version`
  (and only when unset). It does **not** touch `result_action`,
  `exit_on_error`, `print_error`, or `help_on_error`. The four-flag contract on
  each mounted leaf is preserved. (Read from the locked 4.18.0 wheel:
  `cyclopts/core.py` `command()` at line 1296 and
  `_apply_parent_defaults_to_app` at line 135.) The plan's claim "mounting
  copies only the child's group and version defaults, never its contract flags"
  is accurate, and the developers guide already documents the same policy
  (lines ~447–449). The loop calls the identical
  `app.command(build_app(), name=…)` API, so behaviour is unchanged.
- **cuprum is correctly scoped out.** Verified against the read-only sibling
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`: `ProgramCatalogue` is
  `projects=`-constructed (line 62) with an `allowlist` property (line 70),
  matching the plan's description. cuprum appears only in the e2e fixtures,
  which are parametrised off `SUBCOMMAND_NAMES` and never touch
  `build_multiplexer` internals — not load-bearing for this refactor.
- **Line references.** developers-guide line 420 ("The spaced subcommand names
  live once, as data, in a single registry"); the markdownlint/nixie gates
  (AGENTS.md lines 97–98, 169, 172); the 400-line cap (AGENTS.md line 24);
  `make all`/`make test`/`make markdownlint`/`make nixie` targets (Makefile
  lines 37, 125, 118, 121). All present.
- **Behaviour preservation is properly pinned**, not asserted from memory:
  `test_multiplexer_dispatch.py` (four-flag tripwire, five mount names) and
  `test_multiplexer_behaviour.py` (full envelope parity) are the unchanged
  oracles.

## Blocking defects (back to the planner)

### B1 — False premise: "test modules may not use bare `assert`"

Work item 1 instructs the implementer to load `python-testing` because "test
modules are inside `PYTHON_TARGETS` and may not use bare `assert`" and must use
"`AssertionError`-raising helpers". This is **factually wrong**.
`pyproject.toml` line 93 sets
`"**/test_*.py" = ["S101", "PLR0913", "PLR0917", "PLR2004", "PLR6301"]` — S101
(the assert rule) is **ignored for test files**. The existing
`tests/test_multiplexer_dispatch.py` (lines 47, 58, 69, 99, 121, 144) and
`tests/test_legacy_surface_retired.py` (line 66) use bare `assert` freely and
pass lint. The new `test_multiplexer_mount_table.py` is a `test_*.py` module and
inherits the same ignore.

Impact: the false constraint pushes the implementer to write contorted
helper-based assertions that diverge from the house style of the very suites
this test sits beside (the plan explicitly says to mirror
`test_multiplexer_dispatch.py`, which uses bare `assert`). Correct the plan to
state that test modules may use bare `assert` (S101 is per-file-ignored), and
either keep `python-testing` for the parametrize guidance or drop the stated
rationale.

### B2 — Non-existent "sanctioned idiom" for the fresh-interpreter laziness guard

Work item 3 instructs: import `novel` "in a *fresh* interpreter (via the
project's existing fresh-import idiom — check
`tests/test_legacy_surface_retired.py` and the contract suites for the
sanctioned `importlib`/subprocess idiom, and reuse it … per the
Shared-test-scaffolding rule)" and assert the leaf modules are absent from
`sys.modules`.

Verified: there is **no** `sys.modules`-based fresh-import idiom anywhere in
`tests/` (zero matches for `sys.modules` across the test tree).
`test_legacy_surface_retired.py` uses `importlib.util.find_spec` (line 72) —
which checks importability, **not** whether a module has already been imported
into the running interpreter — so it is not the idiom Work item 3 needs.
Several suites shell out via `subprocess`, but none does a `sys.modules`
absence check the implementer can "reuse".

Impact: the primary instruction sends the implementer hunting for an idiom that
does not exist, against the Shared-test-scaffolding rule's "reuse, don't
duplicate" framing. There is a deeper trap the plan half-sees: the same module
(`test_multiplexer_mount_table.py`) imports the five leaf modules at module
scope for the Work-item-1 identity tests
(`... is novel_state.build_app`), so by the time any test in that module runs,
the leaves are already in the process's `sys.modules`. An **in-process**
`sys.modules`-absence check is therefore structurally impossible in this module;
the guard *must* run in a child process with a clean interpreter, or fall back
to the `inspect.getsource` textual check the plan offers as a downgrade.

Required fix: the plan must either (a) specify the actual subprocess/`importlib`
mechanism to spawn a clean interpreter and inspect its `sys.modules` (spelling
it out, since no reusable idiom exists), with the leaf-import-at-module-scope
collision called out and handled; or (b) make the `inspect.getsource` in-process
guard the *primary* mechanism (not a fallback) and drop the false claim that a
sanctioned fresh-import idiom can be reused. As written, the primary path is
unimplementable as described.

## Advisory (non-blocking)

- A1 (Telefono): the new seam `_build_mount_table()` is a private module
  helper that the test reaches into by identity. That is consistent with the
  existing `_VERB_FOR_SUBCOMMAND` / `_command_name_for` private-symbol testing
  convention in `test_multiplexer_dispatch.py`, so it is acceptable — but note
  the contract being pinned (verb-set == registry, value identity == leaf
  `build_app`) is a *structural* contract on a private symbol; if a later step
  inlines the table back into `build_multiplexer`, three tests break. The plan's
  D1/D2 record makes that an intentional tripwire, which is fine; just be aware
  the test couples to an implementation seam, not a public surface.
- A2 (Dinolump): Work item 1 leaves `test_multiplexer_mount_table.py` failing
  at *collection* (import-time `AttributeError`), not at *assertion*. Under
  `pytest -n auto` a collection error in one module is reported distinctly from
  a failed test; the plan's "fails to collect (red)" expectation is correct, but
  the implementer should confirm the rest of the suite still runs green
  (collection errors can, in some pytest configs, be escalated). Low risk; worth
  an explicit check in the Work-item-1 validation step.
- A3 (Pandalump): the plan slightly misquotes developers-guide line 420
  ("spaced subcommand names live once as data" vs the actual "The spaced
  subcommand names live once, as data, in a single registry"). Substance is
  faithful; tidy the quote when the guide note is added so the new prose matches
  the source it cites.
- A4 (Buzzy Bee / scaling): non-issue, recorded for completeness. The table is
  rebuilt on every `build_multiplexer()` call (fresh dict + five attribute
  lookups). `build_multiplexer()` is called once per `main()` invocation, so
  the cost is irrelevant; D3's "build once at mount time" reasoning holds.

## Pre-mortem (Doggylump)

1. **Most likely failure:** the laziness-guard test (B2) is written in-process,
   silently passes because some *other* test module already imported a leaf into
   `sys.modules`, or silently passes because the assertion is inverted — giving
   false confidence that laziness holds while a future module-level hoist of the
   table goes uncaught. Mitigation: resolve B2 by mandating a clean-interpreter
   subprocess or the explicit `inspect.getsource` guard, and have the test prove
   itself by *failing* against a deliberately-hoisted table during authoring.
2. **Second failure:** the implementer, following B1's false constraint, writes
   helper-based assertions, trips PLR/naming rules the helpers introduce, burns
   the 3-iteration tolerance, and escalates on a self-inflicted lint problem.
   Mitigation: fix B1 so bare `assert` is sanctioned.
3. **Bet that could be wrong:** "iterating `_VERB_FOR_SUBCOMMAND` and indexing
   `table[verb]` is equivalent to the hand-copied order." Verified safe — the
   plan notes Cyclopts mount order has no dispatch effect, and
   `test_multiplexer_behaviour.py` would catch any envelope divergence. No
   action needed.

## Alternatives checkpoint (Wafflecat)

The strongest alternative is to **iterate the table directly**
(`for verb, factory in table.items(): app.command(factory(), name=verb)`)
rather than iterating `_VERB_FOR_SUBCOMMAND` and indexing. It is simpler and
removes the `KeyError`-on-omission path. The plan deliberately rejects this
(Work item 2.2): iterating the registry, not the table, keeps the *registry*
the single source of the verb set and order, and turns a table/registry
divergence into a loud `KeyError` rather than a silent under-mount. That is the
better trade for a refactor whose entire point is "the names the dispatcher
mounts cannot drift from the registry." The plan's choice is justified; the
alternative trades the drift-guard for marginal simplicity and should not be
adopted.

## Bottom line

The design is sound and the hard verifications (Cyclopts, cuprum, D1) pass.
Fix B1 and B2 in the plan text — both are test-infrastructure premises that are
demonstrably false against this repo — then this is implementable as written. Do
not relax any design constraint to clear them; the fixes are corrections to the
plan's description of the test harness, not to the design.
