# Remove the legacy entry points and command-name registry symbols (roadmap 1.2.15)

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (round 4 — design-review blocking points B1-B8 resolved)

## Purpose / big picture

After this change the package ships exactly one console-script, `novel`, and the
command-name registry (`novel_ralph_skill/commands/names.py`) carries only the
`novel` multiplexer surface — no legacy `novel-state`/`novel-done`/
`novel-compile`/`desloppify`/`wordcount` entry points, no
`COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`/`STUB_MODULE` symbols, and no transitional
legacy-name superset in the envelope command-name guard. ADR 007 (superseding ADR
005) fixes the final surface as a single `novel` multiplexer; roadmap task 1.2.12
stood up that multiplexer additively beside the legacy five, and 1.2.13 migrated
every installed-binary e2e onto `novel <sub>`. This task retires the now-dead
legacy surface so the registry describes the surface the package actually ships.

You can see it working two ways. First, `uv tool install` (or `uv build` + `uv
pip install`) puts exactly one command, `novel`, on `PATH`; no `novel-x`,
`desloppify`, or `wordcount` script is installed. Second, a repository-wide
**word-boundary** grep for `COMMAND_NAMES`, `COMMAND_ENTRY_POINTS`, or
`STUB_MODULE` (anchored as `\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b`
so it does **not** substring-match the kept `SUBCOMMAND_NAMES`), plus the
legacy entry-point literals, returns no match in `novel_ralph_skill/` or
`tests/`, and `make all` (including the installed-binary e2e) is green.

A note on the gate patterns, because the safety of this whole plan rests on
them. Two pitfalls were found in review and are fixed throughout:

- The kept symbol `SUBCOMMAND_NAMES` *contains* the substring `COMMAND_NAMES`,
  so an unanchored `rg 'COMMAND_NAMES'` can never return empty (≈25
  `SUBCOMMAND_NAMES` references survive the task). Every registry gate is
  therefore anchored with word boundaries: `\b(COMMAND_NAMES|…)\b`, verified to
  exclude `SUBCOMMAND_NAMES` (it shares no word boundary at the leading `SUB`).
- The 12 legacy snapshots store the command name in **three** serializations
  (syrupy repr `'command': 'novel-state'`, JSON envelope `"command":
  "novel-state"`, and bare YAML `command: novel-state`), so a snapshot gate that
  matches only the syrupy-repr form misses 7 of the 12. The canonical snapshot
  gate used everywhere in this plan matches all three forms (defined once below
  as `$SNAP_GATE`).

The hidden weight of this task is not the symbol deletion — it is the **envelope
command-name guard narrowing**. `novel_ralph_skill/contract/envelope.py`'s
`build_envelope` raises `ValueError` if `RunContext.command` is not a member of
`ENVELOPE_COMMAND_NAMES`. Today that guard is the *superset* of the legacy five
and the spaced names. The moment the legacy five leave the superset, **every
test that stamps a legacy command name into a `RunContext`** fails at
envelope-build time. There are roughly twenty-seven such modules plus nine
snapshot files (enumerated in Context). So the dominant work is a mechanical,
test-covered sweep of those stamps from `"novel-state"` → `"novel state"` (and
the four siblings), with snapshot regeneration, performed **before** the registry
narrows — not the three-line symbol deletion the roadmap title implies.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do not modify the root/control worktree. All edits land in the git-donkey
  worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-15`.
- Locked external versions are authoritative and must not change: cuprum
  `0.1.0` and cyclopts `4.18.0` (verified in `uv.lock` lines 113-114 and
  137-138). No dependency may be added, removed, or version-bumped.
- The `novel` multiplexer's runtime behaviour — the exit codes, the JSON/human
  envelope shape, and the spaced `command` names it stamps — must not change.
  This task removes a *parallel legacy surface*; it does not touch the
  multiplexer's own behaviour. The multiplexer is `novel_ralph_skill/commands/
  novel.py` and its registry inputs are `MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`
  (kept), `NOVEL_MODULE`/`_MULTIPLEXER_ENTRY_POINT`/`project_scripts_table` (kept,
  but `project_scripts_table` simplifies to a single `novel` entry).
- The envelope schema (`schema_version`, `command`, `ok`, `working_dir`,
  `result`, `messages`) and exit-code policy (`ExitCode`, design §3.2; ADR 003)
  are unchanged. Only the *set of accepted `command` values* narrows.
- Documentation prose and `SKILL.md` are **out of scope** here. Sweeping the
  design prose/diagrams and `SKILL.md` is roadmap task 1.2.14; the users'/
  developers' guides are 1.2.16. This task is code-and-test only. Stale
  `novel-state`-form prose inside docstrings of already-migrated e2e modules
  (e.g. `tests/test_drafting_bijection_e2e.py`) is left for those prose-sweep
  tasks **except** where a docstring's stale name is load-bearing for a guard
  stamp this task changes, in which case the docstring is corrected alongside
  the code in the same commit.
- en-GB Oxford spelling (`-ize`/`-yse`/`-our`) in every comment, docstring, and
  commit message touched.
- AGENTS.md quality gates apply to every commit: `make check-fmt`, `make lint`
  (Ruff + interrogate 100% docstring coverage + Pylint), `make typecheck` (`ty`),
  `make test`, `make audit`. No markdown changes are expected, so `make
  markdownlint`/`make nixie` apply only if this plan file or another `.md` is
  edited (this plan file is the one such file).

## Tolerances (exception triggers)

- Scope: the enumerated consumer set in Context is the expected blast radius
  (≈28 RUN-GUARD test modules — including the BDD step file
  `tests/steps/per_chapter_loop_steps.py`, B6 — plus the parity pair
  `tests/multiplexer_support.py`/`tests/test_multiplexer_behaviour.py` (B7),
  ≈6 in-process-e2e modules, 12 snapshot files, 3
  production modules, `pyproject.toml`). If implementation requires editing a
  *production* module outside `{names.py, stub.py, novel.py, envelope.py}`, or a
  test module not derivable from the WI-scoped greps below, stop and escalate —
  it means the consumer enumeration missed a caller.
- Snapshots: snapshot regeneration is expected for the **12** `.ambr` files
  whose `command` field carries a legacy name in any of the three serializations
  (verified, Decision Log D6). If `--snapshot-update` rewrites any field *other
  than* `command` (i.e. a behavioural change leaked in), stop and escalate. If
  fewer than 12 files change, a stamp was missed upstream — stop and escalate.
- Interface: removing a public registry symbol (`COMMAND_NAMES`,
  `COMMAND_ENTRY_POINTS`, `STUB_MODULE`) is the intended interface change and is
  in scope. If any *non-test, non-`stub.py`* production module imports one of
  these symbols, stop and escalate (the WI1 grep must show the consumer set is
  test-and-`stub.py`-only before deletion proceeds).
- Iterations: if `make test` still fails after 3 fix attempts on a single work
  item, stop and escalate with the failing node ids.
- Dependencies: if any work item appears to need a new dependency or a version
  change, stop and escalate (it would contradict the locked-version constraint).
- Ambiguity: the parity-test rework decision (Decision Log D1) is made in this
  plan, not deferred to the implementer. If the implementer discovers the chosen
  replacement cannot preserve the asserted coverage, stop and escalate rather
  than silently dropping an assertion.

## Risks

- Risk: the guard-narrowing sweep is wide (≈36 files) and a missed stamp only
  fails when the guard actually narrows, producing a late, confusing collection-
  or runtime-time `ValueError`.
  Severity: high
  Likelihood: medium
  Mitigation: WI2 sweeps **every** legacy stamp and regenerates snapshots while
  the guard *still accepts both* (the superset is untouched in WI2), so the sweep
  is independently green. The guard narrows only in WI4, gated by a grep
  (Decision Log D3) that must return no legacy-name `RunContext`/`_COMMAND`/
  snapshot match in `tests/` first. A leftover stamp is therefore caught by the
  grep *before* the narrowing, not by a runtime fault after it.

- Risk: removing `stub.py`'s entry-point functions breaks the in-process e2e
  modules that drive `stub.novel_state()`/`stub.novel_compile()` directly (6
  modules, Context inventory), which the roadmap's "registry symbols" framing
  does not call out.
  Severity: high
  Likelihood: high (certain if unhandled)
  Mitigation: WI3 re-points every in-process `stub.<entry>()` caller onto
  `novel.main()` with a `["novel", "<verb>", …]` argv before WI5 deletes the
  entry points. The WI5 deletion is gated by a grep that must return no
  `stub.novel_state(`/`stub.novel_compile(`/… match in `tests/` first.

- Risk: `tests/test_command_stubs.py` and
  `tests/test_contract_app_centralisation.py` are *about* the legacy stub entry
  points and the `make_stub_app` factory; deleting the entry points strands or
  empties them.
  Severity: medium
  Likelihood: high
  Mitigation: Decision Log D2 records the disposition of each: the
  `make_stub_app`/`STUB_EXIT_CODE` factory coverage is dead once no entry point
  uses it and is removed with `stub.py`; the four-flag-contract-and-`run`-seam
  coverage in `test_contract_app_centralisation.py` is *re-homed* onto the
  multiplexer's `build_multiplexer()` and `novel.main()` so the structural
  guarantee survives the entry-point deletion.

- Risk: the parity suite (`tests/test_multiplexer_behaviour.py`) loses its
  "legacy oracle" — but its `driver.legacy` arm already drives each leaf's
  `build_app()` directly (not the removed entry points), so the risk is mostly
  cosmetic.
  Severity: low
  Likelihood: medium
  Mitigation: Decision Log D1 fixes the concrete replacement (a reusable
  per-operation expectation driving the same `build_app` the multiplexer mounts,
  retaining full envelope-equality-modulo-`command` coverage). No coverage is
  dropped.

- Risk: regenerated snapshots churn a field beyond `command` because of an
  unrelated drift.
  Severity: low
  Likelihood: low
  Mitigation: the Tolerances snapshot rule and a reviewed `git diff` of every
  `.ambr` hunk (the only allowed change is the `command:` line).

## Progress

- [x] WI1: Enumerate and pin the consumer set (the complete-by-construction
  grep), and record the expected consumer set as an asserted manifest.
  Census recorded (2026-06-26, verified live): 1a `$REG_GATE` → 45 lines
  (COMMAND_NAMES 33, COMMAND_ENTRY_POINTS 11, STUB_MODULE 4 — `SUBCOMMAND_NAMES`
  correctly excluded); 1b stub callers → 24 lines; 1c `$SNAP_GATE` → all 12
  expected `.ambr` files; 1d `$LEGACY` over `$IDIOM_SOURCES` → 118 lines. No
  code in WI1 (manifest deferred to WI6 per the plan's step-2 decision).
- [x] WI2: Sweep every legacy command-name stamp in tests and BDD steps to the
  spaced form (including the matrix's three idioms and
  `tests/steps/per_chapter_loop_steps.py`'s dict-key/helper-argument idiom — B6)
  and regenerate the affected snapshots, while the guard still accepts both.
  (completed: 31 `_COMMAND` constants; 6 inline BDD `RunContext` stamps; the
  load-bearing docstring in `test_novel_state_mutators.py`; the matrix's three
  idioms plus two test-function renames; the per-chapter-loop dict keys, six
  call sites, capture labels, and module docstring; one direct
  `envelope["command"] == "wordcount"` assertion in `test_wordcount_command.py`;
  10 of the 12 snapshots. remaining: `test_contract_envelope.ambr` and
  `test_contract_envelope_snapshots.ambr` stay legacy until WI4 step 3 swaps
  `COMMAND_NAMES[0]`→`SUBCOMMAND_NAMES[0]` — see D6 fact 2; regenerated in WI4
  step 8.) `make all` green; coderabbit 0 findings.
- [x] WI3: Re-point the in-process `stub.<entry>()` e2e callers onto
  `novel.main()`, sweeping **every** legacy command-name assertion in the six
  re-pointed modules to the spaced form — including the human-rendered
  `command: <legacy>` substring assertion at
  `tests/test_novel_state_check.py:207` (B8) — and proving completeness with the
  in-WI3 `command:\s+$LEGACY` source gate over the WI3 module set.
  (completed: five uniform modules re-pointed via the
  `[_COMMAND, *extra]`→`[*_COMMAND.split(), *extra]` + `stub.X()`→`novel.main()`
  transform — `_COMMAND` is the spaced name from WI2, so `_COMMAND.split()` is the
  `["novel", "<verb>"]` prefix `novel.main()` expects; the bespoke
  `test_compile_check_integration.py` `_drive` helper (A7) rewritten to drop the
  `entry_point` parameter and call `novel.main()` over `["novel", "compile"]` /
  `["novel", "state", "check"]`; B8 line 207 swept to `command: novel state` with
  line 208 `working_dir` left intact; load-bearing module/helper docstrings
  updated from `stub.<entry>()` to `novel.main()`. WI3 gates (a) and (b) both
  empty; `make all` green; coderabbit 0 findings.)
- [x] WI4: Rework the parity suite per Decision Log D1 (enumerating every
  `driver.legacy(...)` call site including the hardcoded line-156 site, and
  dropping `_strip_command` at both comparison sites — B7) and re-home the
  structural seam test **first**, then narrow the envelope command-name guard and
  the registry to the multiplexer-only surface (drop the legacy
  half of `ENVELOPE_COMMAND_NAMES`). The D3 gate (over all four `$IDIOM_SOURCES`)
  runs between the test-side sweeps and the narrowing.
  (completed: parity pair reworked — `legacy` arm renamed to `direct`,
  `_Operation` carries the spaced `name`, `_strip_command` deleted, both
  comparison sites now assert full envelope equality including `command`, the
  hardcoded line-156 site swept; `conftest.py` `COMMAND_NAMES[0]`→`"novel state"`
  literal with the import dropped (D5); the four contract modules swapped
  `COMMAND_NAMES`→`SUBCOMMAND_NAMES` and dropped the legacy-subset assertion;
  `test_contract_app_centralisation.py` re-homed onto `novel.main()`/
  `build_multiplexer()` (D2); D3 gate green; `ENVELOPE_COMMAND_NAMES` narrowed to
  `(*SUBCOMMAND_NAMES, MULTIPLEXER_NAME)` with the `names.py`/`envelope.py`
  docstrings updated; the two contract-envelope snapshots regenerated (command
  field only). `make all` green; coderabbit 0 findings.)
  Deviation: `tests/test_command_stubs.py` (a pure legacy-stub-factory test, D2)
  is **deleted in WI4 rather than WI5**, because the guard narrowing in this work
  item is exactly what strands it — its `stub.<entry>()` drives stamp legacy
  names the narrowed guard rejects. Moving its deletion into the narrowing commit
  keeps WI4 `make all`-green and preserves complete-by-construction (the commit
  that breaks the test removes it). The remaining legacy-only test deletions
  (`test_installed_command_names.py`, the registry-pinning cases) stay in WI5;
  they pass under the narrowed guard because they assert registry structure, not
  envelope stamps.
- [x] WI5: Delete the five legacy `[project.scripts]` entries and `stub.py`;
  drop `COMMAND_ENTRY_POINTS`/`STUB_MODULE`/`project_scripts_table`'s legacy half;
  delete or fold the legacy-only registry/stub/pairing tests.
  (completed: WI5 gate grep showed only `names.py`/`stub.py` and the two
  legacy-only test modules; `pyproject.toml` reduced to the single `novel`
  script; `stub.py` deleted; `names.py` lost `STUB_MODULE`,
  `_COMMAND_ENTRY_POINTS`, `COMMAND_ENTRY_POINTS`, and `COMMAND_NAMES` (and the
  now-unused `import types`), `project_scripts_table()` returns the single
  `novel` entry, module docstring rewritten to the multiplexer-only surface;
  `test_installed_command_names.py` deleted; `test_command_names_registry.py`
  folded — `test_registry_pins_the_five_legacy_names`/
  `test_entry_points_resolve_to_callables`/`test_script_table_adds_the_novel_multiplexer`
  removed, replaced by `test_script_table_is_novel_only`, `stub` import dropped;
  the durable manifest `tests/test_legacy_surface_retired.py` added (six cases:
  symbol-absence, stub-module-absence, novel-only script table x2, the B3/B6/B7
  idiom source-scan — which excludes the feature-bound Gherkin decorators via
  `_stamp_lines` — and the B8 human-header source-scan). `make all` green; the
  installed-binary e2e builds a wheel exporting exactly one `novel` script
  (verified: `ls venv/bin | rg ^novel…` → only `novel`); coderabbit 1 trivial
  finding (derive the hyphenated subset from `_LEGACY_LITERALS`) applied.)
- [x] WI6: Closing grep gate + full `make all` (including installed-binary e2e),
  and update this plan's living sections.
  (completed: closing gates run — REG_GATE/`commands.stub` empty in
  `novel_ralph_skill/` and, in `tests/`, only the durable manifest's own
  absence-assertions reference the symbol names (it is not a consumer); pyproject
  legacy literals empty; human-output `command:\s+$LEGACY` over `tests/` empty;
  three-form snapshot gate empty; the idiom-aware scan has no hyphenated stamp
  outside the feature-bound Gherkin decorators. `make all` green, the two slow
  installed-e2e modules green, `make audit` green. Living sections updated.)

## Surprises & discoveries

- Observation: the task's true blast radius is the envelope-guard narrowing, not
  the symbol deletion. `build_envelope` (`novel_ralph_skill/contract/envelope.py`
  line 113) hard-rejects any `command` outside `ENVELOPE_COMMAND_NAMES`, so every
  test stamping a legacy name (about 27 `RunContext`/`_COMMAND` sites and 9
  snapshots) breaks when the legacy names leave the superset.
  Evidence: `grep -rn 'command="novel-state"' tests` and the RUN-GUARD/ASSERT-ONLY
  classification recorded in Context; `envelope.py:113`.
  Impact: WI2 (the sweep) is the largest work item and must precede the
  narrowing; the roadmap's "registry symbols" framing under-describes it.

- Observation: six in-process e2e modules drive the legacy entry points
  *directly* (`stub.novel_state()`, `stub.novel_compile()`), not via the
  installed binary. 1.2.13 migrated only the installed-binary suites.
  Evidence: `grep -rn 'stub\.\(novel_state\|novel_compile\)(' tests` →
  `test_reconcile_e2e.py` (8), `test_compile_e2e.py` (5),
  `test_compile_check_integration.py`, `test_novel_state_check.py`,
  `test_set_chapters_e2e.py`, `test_recount_e2e.py`.
  Impact: WI3 re-points these onto `novel.main()` before `stub.py` is deleted.

- Observation: the WI2 legacy→spaced map is the same positional pairing that
  `tests/test_installed_command_names.py` pins today, and that module is deleted
  in WI5. The dependency is one-directional and resolved by ordering: WI2 (which
  needs the pairing) runs before WI5 (which deletes the module asserting it), and
  the surviving coverage `test_subcommand_names_pin_the_five_spaced_operations`
  keeps the spaced set pinned after deletion. No coverage of the *pairing
  intent* is lost because the legacy half ceases to exist.
  Evidence: `rg -n 'zip\(COMMAND_NAMES, SUBCOMMAND_NAMES'
  tests/test_installed_command_names.py` confirms the positional pairing; the WI2
  map reproduces it exactly.
  Impact: none beyond honouring the WI ordering (advisory A3 from round-1
  review).

- Observation: two further RUN-GUARD idioms stamp legacy command names through
  shapes the `command="…"`/`_COMMAND = "…"` patterns cannot match, so the
  round-2 D3/closing gates would have missed them and the guard-narrowing would
  fault late (B6/B7, round-3 design review).
  Evidence (verified against the live worktree):
  - B6 — `tests/steps/per_chapter_loop_steps.py` keys the five **legacy** names
    in its `_BUILD_APPS` dict (lines 65-71) and stamps them through a
    `_run_capturing(working, command_name, …)` helper that builds
    `RunContext(command=command_name, …)` (lines 105-108); six `When`-step call
    sites pass the legacy literal positionally (lines 142, 165, 182, 210, 228,
    317). It is driven by the live binder `tests/test_per_chapter_loop_bdd.py`.
    `rg -n 'novel-state|novel-done|wordcount|desloppify|novel-compile'
    tests/steps/per_chapter_loop_steps.py` confirms the dict keys and the six
    positional arguments.
  - B7 — `tests/multiplexer_support.py:105` stamps `RunContext(command=name, …)`
    with the caller-supplied name; `tests/test_multiplexer_behaviour.py` supplies
    legacy names via `_OPERATIONS` (lines 68-72 → `driver.legacy(…, op.legacy_name)`
    lines 135-136) AND via a hardcoded `driver.legacy(_novel_done.build_app, [],
    "novel-done")` at line 156 (with `_strip_command` at line 161). Under the
    round-2 ordering (narrow the guard, *then* rework the parity suite) the
    hardcoded line-156 stamp would `ValueError` at envelope build in the window
    between the two — caught only by a failing `make all`, not by any gate.
  Impact: the WI4 step order is corrected so the parity rework (WI4 step 1) runs
  **before** the guard narrows (WI4 step 6), making the B7 fault structurally
  impossible. WI2 step 3a sweeps `per_chapter_loop_steps.py`; WI4 step 1
  enumerates **every** `driver.legacy(...)` call site (the `_OPERATIONS` field and
  the line-156 hardcoded site) and removes the `_strip_command` carve-out at both
  comparison sites; and the D3 (WI4 step 5) and closing (WI6) source gates scan
  all four idiom modules (`$IDIOM_SOURCES`) with the plain `LEGACY` pattern so the
  completeness of every sweep is proven by construction.

- Observation: a fourth RUN-GUARD escape (B8) stamps a legacy command name through
  the **human-rendered** output, which every round-3 gate structurally misses.
  Evidence (verified against the live worktree): `render_human`
  (`novel_ralph_skill/contract/envelope.py:172`) emits `f"command: {env.command}"`,
  and `tests/test_novel_state_check.py:207` asserts `assert "command: novel-state"
  in out`. That module's `_drive_entry_point` (line 191) is in the WI3
  re-point set (it drives `stub.novel_state()`); WI3 re-points it to
  `novel.main()`, which stamps `command="novel state"`, so the human output
  becomes `command: novel state` and line 207 fails — yet the D3 gate scans the
  `command="…"` equals form, `$SNAP_GATE` scans only `tests/__snapshots__`, and
  this module is not in `$IDIOM_SOURCES`. The defect would surface only at WI3's
  `make all`. `rg -nP 'command:\s+(novel-state|…)'
  tests` confirms line 207 is the only such assertion in `tests/` source.
  Impact: WI3 step 3 is broadened to sweep the human-output idiom (naming
  `test_novel_state_check.py:207-208`), WI3 gains an in-WI3 `command:\s+$LEGACY`
  source gate over the six re-pointed modules, WI6's closing gate gains a repo-wide
  spaced-only `command:` invariant, and the durable manifest gains a
  `test_no_legacy_human_command_header_in_repointed_e2e` source-scan case (D8).

- Observation (WI2 implementation, 2026-06-26): the plan's "zero `$LEGACY`"
  claim over `$IDIOM_SOURCES` is not *literally* achievable with the bare
  five-name alternation, because two classes of benign residue substring-match
  it — exactly the `SUBCOMMAND_NAMES`-contains-`COMMAND_NAMES` pitfall the plan
  already fixed for the registry gate, recurring for the legacy literals:
  - **Production module aliases.** `tests/test_command_surface_matrix.py` and
    `tests/steps/per_chapter_loop_steps.py` import the command leaf modules as
    `_desloppify`, `_wordcount` (real files
    `novel_ralph_skill/commands/_desloppify.py`, `_wordcount.py`), and the matrix
    references `_wordcount_report` and the test ids it derives. These are
    production module names, **out of scope** (the modules are kept), yet the
    bare `desloppify`/`wordcount` alternation matches them.
  - **Gherkin step-binding text.** `per_chapter_loop_steps.py`'s `@when`/`@then`
    decorator strings (e.g. `@when("novel-done runs against the loop tree")`)
    must match `tests/features/per_chapter_loop.feature` *verbatim*; sweeping the
    decorators without sweeping the feature file breaks the binding with a
    `StepDefinitionNotFoundError`. The feature step-text is scenario prose scoped
    to the 1.2.14/1.2.16 prose sweep, so it stays legacy here.
  Resolution: every load-bearing **stamp** (the `RunContext.command` value, the
  `_BUILD_APPS` dict keys, the capture-map labels, the `_ReadCommand`/`_BY_NAME`/
  `if name ==` matrix idioms, the `_COMMAND` constants, the direct
  `envelope["command"] == …` assertions, and the matching docstring spine prose)
  *is* swept; the residue is exactly (a) the kept module aliases and (b) the
  feature-bound Gherkin decorators. The completeness gate is therefore the
  **refined** idiom gate
  `rg -nP '(novel-state|novel-done|novel-compile)|(?<![\w])(?<!novel )(desloppify|wordcount)(?![\w])'`
  over each idiom source *minus* the `@when`/`@then` decorator lines — verified
  empty for both swept idiom sources. The plain `$LEGACY` scan's surviving hits
  in these two files are all module aliases or feature-bound step text, never a
  stamp the narrowed guard could reject. The WI4 D3 gate, the WI6 closing gate,
  and the durable manifest test (WI6) use this refined gate (and exclude the
  Gherkin decorators) accordingly.
  Impact: the narrowing in WI4 is still complete-by-construction — no stamp
  survives — but the gate pattern is refined exactly as the plan refined the
  registry gate, and the durable manifest scans for the *stamp* idioms, not the
  bare alternation.

- Observation (WI2 implementation, 2026-06-26): one direct legacy assertion was
  not covered by the `_COMMAND`-constant idiom — `test_wordcount_command.py:94`
  asserts `envelope["command"] == "wordcount"` against a literal, not the module
  `_COMMAND` constant (that module pins the contract by literal). Swept to
  `"novel wordcount"` (plus the two mirroring docstring lines). This is the same
  "assertion moves with the stamp" rule the plan states for `_COMMAND` modules;
  it just used a literal rather than the constant. No other direct
  `envelope["command"] == "<legacy>"` assertion exists in `tests/` (verified by
  `rg -nP '\["command"\]\s*==\s*"<legacy>"' tests`).

## Decision log

- Decision: D1 — the parity suite's legacy oracle is replaced by a **reusable
  per-operation expectation**, retaining full envelope-equality coverage modulo
  `command`. Concretely: `tests/multiplexer_support.py`'s `driver.legacy` arm
  already drives each operation's own `build_app()` through the shared `run`
  wrapper with a supplied command name — it never used a removed entry point or
  `COMMAND_NAMES`. After this task the `legacy` arm is renamed to a neutral
  `direct` arm and its supplied name becomes the **spaced** name (`"novel
  state"`, …), so each `_Operation` in `tests/test_multiplexer_behaviour.py`
  carries `(spaced_name, build_app, mux_argv)`. The behavioural test then asserts
  the multiplexer's `(exit_code, envelope)` equals driving the same `build_app`
  directly under the spaced name — i.e. exit-code AND full-envelope equality
  (now without the `_strip_command` carve-out, because both arms stamp the same
  spaced name). This is *stronger* than the old assertion (the `command` field is
  now also compared), and it provably preserves the dispatcher's
  no-behaviour-change guarantee without any legacy symbol. The envelope-equality
  coverage is therefore **preserved, not reduced**, so no Decision-Log
  justification for a reduced assertion is needed.
  Rationale: the roadmap requires the plan to choose the replacement concretely;
  the `build_app`-direct oracle already exists and survives the deletion intact,
  so reusing it is the lowest-risk, highest-coverage choice.
  Date/Author: 2026-06-26, planning agent.

- Decision: D2 — disposition of the legacy-stub-specific test modules.
  `tests/test_command_stubs.py` (drives `make_stub_app` and the five
  `stub.<entry>` callables) is **deleted** with `stub.py`: `make_stub_app`/
  `STUB_EXIT_CODE` are scaffolding retained only "for the unit tests that pin the
  stub-result exit-code contract" (`stub.py` docstring) and have no live caller
  once the entry points go, so both the factory and its test are dead.
  `tests/test_contract_app_centralisation.py` is **re-homed**, not deleted: its
  half (a) — each production `build_app` carries the four-flag contract — is
  command-name-agnostic and kept verbatim; its half (b) — each *entry point*
  routes through the `_drive`/`run` seam — is rewritten to assert that
  `novel.main()` routes `build_multiplexer()` (a four-flag-contract app) through
  `novel_ralph_skill.commands.novel.run`, monkeypatching `novel.run`. This keeps
  the "no re-inlined bare `cyclopts.App`, no re-inlined `run` plumbing"
  structural guarantee on the one surviving entry point.
  Rationale: preserve every live structural guarantee; delete only genuinely dead
  scaffolding (the roadmap's complete-by-construction discipline).
  Date/Author: 2026-06-26, planning agent.

- Decision: D3 — the guard narrows (WI4) only after a grep proves no legacy stamp
  survives in `tests/`. The gate greps (a `RunContext`/`_COMMAND` scan over
  `tests/` and a `command:` scan over `tests/__snapshots__`, both shown verbatim
  in WI4) must return no match before `ENVELOPE_COMMAND_NAMES` drops the legacy
  half.
  Rationale: a leftover stamp passes every earlier step and only faults when the
  guard narrows; the grep gate converts that late runtime fault into an explicit
  pre-condition (the roadmap's complete-by-construction rule (3)).
  Date/Author: 2026-06-26, planning agent.

- Decision: D4 — `names.py` symbol deletion (`COMMAND_NAMES`,
  `COMMAND_ENTRY_POINTS`, `STUB_MODULE`) is gated (WI5) by a grep that must return
  no match in both `tests/` and `novel_ralph_skill/` before the symbol's
  definition line is removed, and each consumer is re-pointed *and* dropped from
  its import line in the same step so no import is left dangling (the roadmap's
  complete-by-construction rule (2)/(3)). `SUBCOMMAND_NAMES`, `MULTIPLEXER_NAME`,
  `NOVEL_MODULE`, `_MULTIPLEXER_ENTRY_POINT`, and `project_scripts_table` are
  **kept** (the multiplexer and the script-table gate still consume them);
  `project_scripts_table` loses its legacy-five loop and returns the single
  `{ "novel": "novel_ralph_skill.commands.novel:main" }` entry.
  Rationale: keep exactly the symbols the surviving surface needs; remove exactly
  the dead ones.
  Date/Author: 2026-06-26, planning agent.

- Decision: D5 — the conftest `app_factory` fixture (`tests/conftest.py` line
  339) stamps `COMMAND_NAMES[0]` as a *behaviourally-inert* app name. It is
  re-pointed to the literal `"novel state"` (a member of the narrowed
  `ENVELOPE_COMMAND_NAMES`), not to a registry symbol, because the fixture's
  comment already records the name is inert for the run path; a literal avoids
  re-introducing a registry import for a value that no longer needs the single
  source of truth.
  Rationale: smallest change that keeps the fixture guard-valid without coupling
  it to a kept registry symbol.
  Date/Author: 2026-06-26, planning agent.

- Decision: D6 — the grep gates are made sound after round-1 review found them
  both false-negative and false-positive. Five facts were verified directly
  against the live worktree and now anchor every gate in this plan:
  1. Snapshots store the legacy command in **three** serializations — syrupy
     repr (`'command': 'novel-state'`, 5 files), JSON envelope (`"command":
     "novel-state"`, 7 files: `test_compile_check_snapshots`,
     `test_compile_snapshots`, `test_contract_envelope`,
     `test_contract_envelope_snapshots`, `test_novel_state_check_disk`,
     `test_novel_state_mutator_snapshots`, `test_reconcile_refuse`), and bare
     YAML (`command: novel-state`, `test_contract_envelope.ambr`). The
     syrupy-repr-only gate found 5 files; the three-form `$SNAP_GATE` finds all
     12. Evidence: three `rg -ln` runs over `tests/__snapshots__`.
  2. `test_contract_envelope.ambr` carries the bare-YAML and JSON forms, and
     `test_contract_envelope.py` line 59 stamps `command=COMMAND_NAMES[0]`; WI4
     step 3 swaps that to `SUBCOMMAND_NAMES[0]`, so this snapshot must be
     regenerated. It is now in the WI2 list (step 5) and regenerated
     unconditionally in WI4 step 8. Evidence: `sed`/`rg` on the module and its
     `.ambr`.
  3. `tests/test_command_surface_matrix.py` stamps the legacy name through
     `_ReadCommand("novel-state", …)` (lines 127-131), `_BY_NAME["novel-state"]`
     (lines 581/610/632/678/716), and `if name == "novel-done"|"novel-compile":`
     (lines 495/497) — none matched by `command="…"` or `_COMMAND = "…"`. The
     D3/closing gate now adds a plain `rg -n "$LEGACY"
     tests/test_command_surface_matrix.py` scan; WI2 step 3 sweeps all three
     idioms and asserts that scan is empty. Evidence: `rg -n
     '_ReadCommand\(|_BY_NAME\[|name == ...'` on the module.
  4. The kept symbol `SUBCOMMAND_NAMES` substring-contains `COMMAND_NAMES`, so an
     unanchored gate can never empty (≈25 surviving `SUBCOMMAND_NAMES` refs).
     `\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b` was verified to
     return nothing over `novel.py` (which references only `SUBCOMMAND_NAMES`),
     so the word boundaries correctly exclude it. Every registry gate now uses
     `$REG_GATE`. Evidence: `rg '\bCOMMAND_NAMES\b' novel_ralph_skill/commands/
     novel.py` → empty.
  5. The only inert-docstring occurrence of `command="novel-state"` in `tests/`
     is `test_novel_state_mutators.py` line 14, which documents the live
     `_COMMAND` stamp on line 38 of the same module. Rather than excluding
     docstrings from the gate (brittle), WI2 step 1 sweeps this one line under
     the Constraints docstring carve-out, so the `command="…"` D3 gate is
     genuinely empty after a correct sweep with no special-casing. Evidence:
     `rg -n 'command="novel-state"' tests` → only the 5 BDD-step code sites plus
     this one docstring line; `sed -n '1,19p'` confirms it is inside the module
     docstring.
  Rationale: convert the round-1 false-negative/false-positive gates into gates
  whose emptiness is a true proof of completeness, preserving the plan's
  complete-by-construction discipline.
  Date/Author: 2026-06-26, planning agent (round 2, post design-review).

- Decision: D7 — two further RUN-GUARD idioms (B6, B7) are brought into the
  inventory, the sweeps, and the gates; the WI4 step order is corrected so the
  parity rework precedes the guard narrowing. Three facts were verified directly
  against the live worktree:
  1. B6 — `tests/steps/per_chapter_loop_steps.py` is a RUN-GUARD consumer the
     round-2 inventory omitted. Its `_BUILD_APPS` dict keys the five **legacy**
     names (lines 65-71) and its `_run_capturing` helper stamps
     `RunContext(command=command_name, …)` (lines 105-108) from a caller-supplied
     name; six `When`-step call sites pass the legacy literal positionally (lines
     142, 165, 182, 210, 228, 317). It is driven by the live binder
     `tests/test_per_chapter_loop_bdd.py`. Resolution: WI2 step 3a sweeps the dict
     keys, the six call sites, the four legacy-shaped capture-map labels, and the
     docstring spine prose (so the file reaches zero `$LEGACY` outside benign
     residue), and the file joins `$IDIOM_SOURCES` so the D3 (WI4 step 5) and
     closing (WI6) gates scan it. Evidence: `rg -n
     'novel-state|novel-done|wordcount|desloppify|novel-compile'
     tests/steps/per_chapter_loop_steps.py`.
  2. B7 — the parity rework was ungated and the round-2 step 7 omitted a
     hardcoded legacy-name site. `tests/multiplexer_support.py:105` stamps
     `RunContext(command=name, …)` with the caller-supplied name;
     `tests/test_multiplexer_behaviour.py` supplies legacy names via `_OPERATIONS`
     (lines 68-72 → `driver.legacy(…, op.legacy_name)` lines 135-136) AND via a
     hardcoded `driver.legacy(_novel_done.build_app, [], "novel-done")` at line
     156 with `_strip_command` at line 161. Resolution: WI4 step 1 (now the first
     WI4 step) enumerates **both** name-supplying shapes — the `_OPERATIONS` field
     and the line-156 hardcoded site — drops `_strip_command` at both comparison
     sites (lines 141 and 161), and both modules join `$IDIOM_SOURCES`. Evidence:
     `rg -n 'driver\.legacy\(|_strip_command' tests/test_multiplexer_behaviour.py`.
  3. The ordering fault: the round-2 WI4 narrowed the guard (step 2) *before*
     reworking the parity suite (step 7), so the line-156 stamp would `ValueError`
     in the window between. Resolution: WI4 now reworks the parity suite (step 1)
     and runs the D3 gate (step 5) **before** narrowing the guard (step 6), so the
     B7 fault is structurally impossible, mirroring the WI-level WI2-before-WI4
     ordering.
  Rationale: extend the complete-by-construction gate apparatus to cover the two
  idioms it missed, and remove the late-`ValueError` window by ordering, so the
  plan's own Tolerances escalation rule (a missed consumer must be caught by a
  gate, not by a failing `make all`) holds for every RUN-GUARD consumer.
  Date/Author: 2026-06-26, planning agent (round 3, post design-review).

- Decision: D8 — a fourth RUN-GUARD escape (B8) is brought into the WI3 sweep and
  gated. The **human-rendered** output assertion idiom was uncovered by every
  round-3 gate, recurring the B6/B7 fault class a fourth time. Two facts were
  verified directly against the live worktree:
  1. `render_human` (`novel_ralph_skill/contract/envelope.py:172`) emits
     `f"command: {env.command}"`, so a test asserting against the **human** report
     carries the literal `command: <name>` (colon-space), distinct from the
     `command="<name>"` equals-stamp and the `"command": "<name>"` JSON form. The
     sole such assertion in the WI3 re-point set is
     `tests/test_novel_state_check.py:207` — `assert "command: novel-state" in
     out`. Its `_drive_entry_point` (line 191) drives `stub.novel_state()`, which
     WI3 re-points to `novel.main()`; `novel.main()` stamps `command="novel
     state"`, so the human output becomes `command: novel state` and line 207
     would fail at WI3's `make all`. No round-3 gate caught it: the D3 gate scans
     `command="<legacy>"` (equals, not colon-space); `$SNAP_GATE`'s bare-YAML arm
     runs only over `tests/__snapshots__`, not `tests/` source; and
     `test_novel_state_check.py` is not in `$IDIOM_SOURCES`. The adjacent line 208
     `assert "working_dir: working" in out` names `env.working_dir` (a directory),
     not a command, and is unchanged.
     Evidence: `rg -nP 'command:\s+(novel-state|…)' tests` → only line 207 in
     source (plus the `.ambr` snapshot covered by `$SNAP_GATE`); `envelope.py:172`.
  2. The idiom is genuinely isolated to that one site:
     `tests/test_console_scripts_error_arms_e2e.py:242`
     (`startswith(f"command: {_COMMAND}")`) and
     `tests/test_multiplexer_behaviour.py:297`
     (`assert "command: novel state" in out`) already use the **spaced** name —
     the former because `_COMMAND = "novel state"` (1.2.13 migration), the latter
     because it drives the multiplexer. Neither is in the WI3 set.
     Evidence: `rg -n '_COMMAND' tests/test_console_scripts_error_arms_e2e.py` →
     `_COMMAND = "novel state"`; `sed`/`rg` on line 297.
  Resolution: (1) WI3 step 3 is broadened from "any `envelope["command"] ==`
  assertion" to **every** legacy command-name assertion, explicitly naming the
  human-output substring shape and the `test_novel_state_check.py:207-208` lines
  by line; (2) WI3 adds an **in-WI3** gate (b) — `rg -nP "command:\s+$LEGACY"` over
  the six WI3 re-pointed modules — so the sweep's completeness is proven inside
  WI3, before WI3's `make all`, not discovered by it; (3) WI6's closing gate adds
  a repo-wide spaced-only `command:\s+$LEGACY` invariant over all of `tests/`; and
  (4) the durable manifest test gains a
  `test_no_legacy_human_command_header_in_repointed_e2e` source-scan case over the
  six WI3 modules, the lasting B8 guard.
  Rationale: extend the complete-by-construction gate apparatus to the
  human-render idiom — the only RUN-GUARD escape the colon-space form takes — so
  the plan's Tolerances rule (a missed stamp is caught by a gate, not by a failing
  `make all`) holds for the human output as well as the JSON envelope.
  Date/Author: 2026-06-26, planning agent (round 4, post design-review).

## Outcomes & retrospective

Completed 2026-06-26. Against Purpose: the package ships exactly one console
script — `uv build` + `uv pip install` into a throwaway venv puts only `novel`
on `PATH` (verified live: `ls venv/bin | rg '^(novel|novel-state|…)$'` → the
single line `novel`). The production tree (`novel_ralph_skill/`) carries no
`COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`/`STUB_MODULE` symbol and no
`commands.stub` reference (word-anchored gate empty); the only `tests/`
occurrences are the durable manifest `test_legacy_surface_retired.py`'s
absence-assertions, which must name the symbols to assert they are gone. No
legacy command value survives in any snapshot across all three serializations
(`$SNAP_GATE` empty over `tests/__snapshots__`). No human-rendered
`command: <legacy>` header survives in any `tests/` source (the B8 repo-wide
invariant empty). The parity coverage is preserved and strengthened (D1): both
`test_multiplexer_matches_direct_over_drafting_tree` and
`test_multiplexer_done_success_matches_direct` now assert full envelope
equality including the `command` field, with `_strip_command` deleted. `make
all` green; the two slow installed-binary e2e modules green; `make audit` green.

What deviated from the plan, and why:

- The plan's literal "zero `$LEGACY`" claim over `$IDIOM_SOURCES` and over the
  per-chapter-loop steps was not achievable with the bare five-name alternation,
  because production module aliases (`_desloppify`/`_wordcount`) and feature-bound
  Gherkin step-text substring-match it — the same substring pitfall the plan
  fixed for the registry gate (`SUBCOMMAND_NAMES` ⊃ `COMMAND_NAMES`). The
  completeness gate became the **refined** scan (hyphenated stamps, excluding the
  `@when`/`@then`/`@given` decorators); the durable manifest's
  `_stamp_lines` encodes the same exclusion. Every load-bearing *stamp* is swept;
  the residue is exactly the kept module aliases, the bare mount-verb argv tokens,
  and the Gherkin step text (scoped to 1.2.14/1.2.16).
- `tests/test_command_stubs.py` was deleted in **WI4** (the guard-narrowing
  commit) rather than WI5, because the narrowing is what strands it — keeping the
  deletion in the commit that breaks it preserves complete-by-construction and
  WI4 `make all`-greenness.
- One direct legacy assertion (`test_wordcount_command.py:94`,
  `envelope["command"] == "wordcount"`) used a literal rather than the `_COMMAND`
  constant; swept in WI2 under the same "assertion moves with the stamp" rule.

To be compared against the original Purpose (kept verbatim below for the audit
trail). Compare against Purpose: one `novel` script on `PATH`;
no legacy entry point or `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`/`STUB_MODULE`
symbol anywhere in `novel_ralph_skill/` or `tests/` (verified by the
word-anchored `\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b` gate, which
excludes the kept `SUBCOMMAND_NAMES`); no legacy command value in any snapshot
across all three serializations (the `$SNAP_GATE` gate); no legacy command
literal in any of the four idiom-bearing source modules (`$IDIOM_SOURCES` — the
matrix, the per-chapter-loop steps, and the parity pair, B3/B6/B7); no
human-rendered `command: <legacy>` header in any source module — proven by the
repo-wide spaced-only `command:\s+$LEGACY` invariant over `tests/` and the durable
`test_no_legacy_human_command_header_in_repointed_e2e` manifest case (B8); parity
coverage preserved and strengthened (D1, now comparing the `command` field too);
`make all` green.

## Context and orientation

The deterministic spine is a single `novel` Cyclopts multiplexer plus a legacy
parallel surface that this task retires. The relevant files:

- `novel_ralph_skill/commands/names.py` — the command-name single source of
  truth. Defines `STUB_MODULE`, `NOVEL_MODULE`, `COMMAND_ENTRY_POINTS`
  (legacy-name → stub-function map), `COMMAND_NAMES` (the five legacy names),
  `MULTIPLEXER_NAME` (`"novel"`), `SUBCOMMAND_NAMES` (the five spaced names),
  `ENVELOPE_COMMAND_NAMES` (the **superset** the envelope guard validates
  against), and `project_scripts_table()` (derives `[project.scripts]`). To
  remove: `STUB_MODULE`, `COMMAND_ENTRY_POINTS`, `COMMAND_NAMES`, and the legacy
  half of `ENVELOPE_COMMAND_NAMES`/`project_scripts_table`. To keep:
  `NOVEL_MODULE`, `MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`,
  `_MULTIPLEXER_ENTRY_POINT`.
- `novel_ralph_skill/commands/stub.py` — the five legacy console-script
  functions (`novel_state`, `novel_done`, `novel_compile`, `desloppify`,
  `wordcount`), the shared `_drive` helper, and the `make_stub_app`/
  `STUB_EXIT_CODE` factory. **Entire module deleted** in WI5 (no live caller
  remains after WI3).
- `novel_ralph_skill/commands/novel.py` — the surviving multiplexer
  (`build_multiplexer`, `_command_name_for`, `main`). Unchanged by this task
  except that it remains the sole entry point. It imports `MULTIPLEXER_NAME` and
  `SUBCOMMAND_NAMES` (both kept).
- `novel_ralph_skill/contract/envelope.py` — `build_envelope` (line 113) rejects
  any `command` outside `ENVELOPE_COMMAND_NAMES`. The guard *narrows* in WI4; the
  module's import of `ENVELOPE_COMMAND_NAMES` is unchanged (the tuple's contents
  shrink in `names.py`). Docstring references to "the legacy five" are updated to
  the multiplexer-only wording.
- `pyproject.toml` lines 11-16 — `[project.scripts]`: five legacy entries plus
  `novel`. The five legacy lines are deleted in WI5, leaving only
  `novel = "novel_ralph_skill.commands.novel:main"`.

Locked external libraries (verified): cuprum `0.1.0`, cyclopts `4.18.0`
(`uv.lock` lines 113-114, 137-138). The cuprum surface the surviving
installed-binary e2e relies on — `Program(str(abs_path))`, `ProgramCatalogue`,
`sh.make(prog, catalogue=…)`, `builder(*argv).run_sync(context=ExecutionContext(
cwd=…), capture=True)` — is unchanged by this task and was verified against the
locked source at `/data/leynos/Projects/cuprum` (`cuprum/program.py`,
`cuprum/catalogue.py`, `cuprum/sh.py`; version pinned at `pyproject.toml`
`version = "0.1.0"`). This task adds no new cuprum usage and changes no installed
e2e invocation, so no further cuprum verification is load-bearing here.

### The complete consumer inventory (the WI1 manifest)

Production symbol consumers (the only production edits permitted):

- `COMMAND_NAMES`: `novel_ralph_skill/commands/names.py` (definition),
  `contract/envelope.py` (docstring only — it imports `ENVELOPE_COMMAND_NAMES`,
  not `COMMAND_NAMES`).
- `COMMAND_ENTRY_POINTS`: `names.py` (definition), `stub.py` (`_NAME_FOR` map,
  deleted with the module), `names.py:project_scripts_table` (the legacy loop).
- `STUB_MODULE`: `names.py` only (definition + `project_scripts_table`).
- `ENVELOPE_COMMAND_NAMES`: `names.py` (definition), `contract/envelope.py`
  (the guard — kept, contents narrow).

Test consumers, classified by how they break when the guard narrows:

- RUN-GUARD (stamp a legacy `RunContext.command`/`_COMMAND` while driving
  `build_app()` through `run` — fail at envelope build once the guard narrows;
  ≈27 modules): `test_novel_done_command.py`, `test_novel_done_snapshots.py`,
  `test_reconcile.py`, `test_compile_check_agreement.py`,
  `test_compile_check_snapshots.py`, `test_compile_check_unit.py`,
  `test_desloppify_command.py`, `test_novel_state_check.py`,
  `test_novel_state_mutators.py`, `test_compile_snapshots.py`,
  `test_novel_state_check_disk.py`, `test_ledger_snapshots.py`,
  `tests/steps/set_chapters_steps.py`, `test_novel_state_mutator_snapshots.py`,
  `test_ledger_command.py`, `test_set_chapters_registration.py`,
  `test_current_definition.py`, `test_desloppify_snapshots.py`,
  `test_wordcount_snapshots.py`, `test_set_chapters_reconcile.py`,
  `test_wordcount_command.py`, `tests/steps/torn_turn_rollback_partial_steps.py`,
  `test_reconcile_integration.py`, `test_novel_state_violations_ownership.py`,
  `test_reconcile_refuse.py`, `tests/steps/torn_turn_recovery_steps.py`,
  `tests/steps/torn_turn_rollback_steps.py`. Plus the literal-`RunContext` BDD
  steps `tests/steps/advance_phase_steps.py`, `tests/steps/compile_steps.py`,
  `tests/steps/novel_done_steps.py`, `tests/steps/recount_steps.py`,
  `tests/steps/reconcile_steps.py` (these stamp `command="novel-state"` etc.
  inline rather than via a `_COMMAND` constant). Plus
  `tests/test_command_surface_matrix.py` (its `_ReadCommand.name` values
  `"novel-state"` … are stamped into `RunContext.command`). Plus
  `tests/steps/per_chapter_loop_steps.py` (B6 — verified against the live
  worktree): a RUN-GUARD consumer that stamps the legacy name through a
  **dict-key / helper-argument idiom** that neither the `command="…"` nor the
  `_COMMAND = "…"` pattern can see. Its `_BUILD_APPS` dict keys the five **legacy**
  names to each leaf's `build_app` (lines 65-71), and its `_run_capturing` helper
  stamps `RunContext(command=command_name, …)` (lines 105-108) from a
  caller-supplied `command_name`; six `When`-step call sites pass the legacy
  literal positionally — `_run_capturing(working, "novel-state", ["recount"], …)`
  (line 142), `"novel-done"` (line 165), `"wordcount"` (line 182), `"desloppify"`
  (line 210), `"novel-compile"` (line 228), and a second `"novel-state"` for
  `advance-phase` (line 317). It is the live binder
  `tests/test_per_chapter_loop_bdd.py` (the real BDD test). Once WI4 narrows
  `ENVELOPE_COMMAND_NAMES`, every one of those stamps is rejected at
  `build_envelope` (`envelope.py:113`), so this module is swept in WI2 (step 3a)
  and its plain `LEGACY` scan is added to the D3/closing source gate.
- ASSERT-ONLY in-process e2e (call `stub.<entry>()` directly and/or assert a
  legacy `_COMMAND`; re-pointed in WI3): `test_compile_e2e.py`,
  `test_recount_e2e.py`, `test_set_chapters_e2e.py`, `test_reconcile_e2e.py`,
  `test_novel_state_check.py` (also RUN-GUARD), `test_compile_check_integration.py`.
- Snapshot files carrying a legacy command value (all **12**, regenerated in
  WI2; the serialization form per file is recorded because the gate must match
  all three — Decision Log D6). Syrupy-repr form (`'command': 'novel-state'`):
  `test_command_surface_matrix.ambr` (65 hunks),
  `test_novel_done_snapshots.ambr` (3), `test_desloppify_snapshots.ambr` (2),
  `test_ledger_snapshots.ambr` (2), `test_wordcount_snapshots.ambr` (1).
  JSON-envelope form (`"command": "novel-state"`):
  `test_compile_check_snapshots.ambr`, `test_compile_snapshots.ambr`,
  `test_novel_state_check_disk.ambr`, `test_novel_state_mutator_snapshots.ambr`,
  `test_reconcile_refuse.ambr`, `test_contract_envelope_snapshots.ambr`, and
  `test_contract_envelope.ambr`. Bare-YAML form (`command: novel-state`):
  `test_contract_envelope.ambr` (which carries both JSON and bare-YAML). The
  syrupy-repr-only gate would miss the 7 JSON/bare-YAML files entirely.
- Legacy-symbol-only tests (deleted or folded in WI4/WI5, Decision Log D2/D4):
  `test_command_stubs.py` (deleted); `test_installed_command_names.py`
  (deleted — it pins the legacy-to-spaced pairing that no longer exists),
  `test_command_names_registry.py` (the `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`
  assertions removed; the `project_scripts_table`/`SUBCOMMAND_NAMES` assertions
  kept and updated to the single-`novel` table),
  `test_contract_app_centralisation.py` (re-homed, D2),
  `test_pyproject_scripts.py` (kept — already derives from
  `project_scripts_table`; passes unchanged once the table narrows),
  `test_contract_envelope.py` (the `set(COMMAND_NAMES) <= ENVELOPE_COMMAND_NAMES`
  assertion and the `COMMAND_NAMES[…]` stamps move to `SUBCOMMAND_NAMES`),
  `test_contract_properties.py` / `test_contract_runner.py` /
  `test_contract_envelope_snapshots.py` (swap `COMMAND_NAMES` →
  `SUBCOMMAND_NAMES`), `tests/conftest.py` line 339 (D5),
  `tests/multiplexer_support.py` + `tests/test_multiplexer_behaviour.py` (parity
  rework, D1; B7 — these are *also* RUN-GUARD: `multiplexer_support.py:105` stamps
  `RunContext(command=name, …)` with the caller-supplied name, and
  `test_multiplexer_behaviour.py` supplies legacy names **two ways** — via the
  `_OPERATIONS` tuple `legacy_name` field (lines 68-72), fed to
  `driver.legacy(op.legacy_build, op.spaced[1:], op.legacy_name)` (lines 135-136),
  AND via a **hardcoded** `driver.legacy(_novel_done.build_app, [], "novel-done")`
  at line 156 with `_strip_command` at line 161 in
  `test_multiplexer_done_success_matches_legacy`. WI4 reworks the parity suite
  (step 1) **before** it narrows the guard (step 6), and step 1 enumerates every
  `driver.legacy(...)` call site and `_strip_command` usage — including the
  line-156/161 hardcoded site — so no parity stamp is ever rejected by a narrowed
  guard; completeness is proven by the D3 (step 5) and closing (WI6) `$LEGACY`
  source-gate scan over both modules via `$IDIOM_SOURCES`),
  `tests/test_command_names_registry.py:test_registry_pins_the_five_legacy_names`
  (deleted).

The exact greps each WI runs are in Concrete steps. The single source of truth
for "did I miss a consumer" is the closing grep gate (WI6).

## Plan of work

The ordering is forced by the guard: sweep the stamps green **while both name
forms are still accepted** (WI2), re-point the in-process entry-point callers
(WI3), *then* narrow the guard and registry (WI4-WI5), each gated by a grep that
proves the prior step left nothing behind. Every work item is independently
committable and `make all`-green.

### Stage A — enumerate (WI1)

Pin the consumer set as an executable manifest so a regression that adds a new
legacy stamp fails loudly. No production behaviour changes.

### Stage B — sweep under the still-permissive guard (WI2, WI3)

Move every legacy command-name stamp to the spaced form and re-point the
in-process `stub.<entry>()` callers onto `novel.main()`. Because
`ENVELOPE_COMMAND_NAMES` still contains both forms, every change in this stage is
green on its own commit; snapshots regenerate to the spaced `command` value.

### Stage C — narrow and delete (WI4, WI5)

Narrow the guard and the registry to the multiplexer-only surface, re-home the
structural seam test, rework the parity suite, then delete `stub.py`, the five
legacy `[project.scripts]` entries, and the dead legacy-only tests. Each deletion
is grep-gated.

### Stage D — gate and validate (WI6)

Run the closing grep gate and full `make all` (including the installed-binary
e2e), then update this plan's living sections.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-15`. Use `leta`
for navigation and `sem` for history; `rg` is used for the grep gates because
they are literal-string membership checks. Validation per commit is `make all`
(AGENTS.md). Snapshot regeneration is `uv run pytest <module> --snapshot-update`
(syrupy), reviewing the diff so only the `command:` line changes.

### Canonical gate patterns (used by every WI below)

These three shell variables are defined once and reused verbatim wherever a gate
runs. They were each verified against the live worktree (see Decision Log D6).
Define them at the top of any gate step:

```bash
# Anchored registry gate: word boundaries exclude the kept SUBCOMMAND_NAMES.
# Verified: `rg '\bCOMMAND_NAMES\b' novel_ralph_skill/commands/novel.py` (which
# references only SUBCOMMAND_NAMES) returns NOTHING.
REG_GATE='\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b'

# Legacy command literals (the five legacy names). The `desloppify`/`wordcount`
# legacy forms have no hyphen, so they are matched as standalone words.
LEGACY='(novel-state|novel-done|novel-compile|desloppify|wordcount)'

# Snapshot gate: matches ALL THREE serialisations the .ambr files use —
# syrupy repr ('command': 'novel-state'), JSON envelope ("command":
# "novel-state"), and bare YAML (command: novel-state). Verified to find all 12
# legacy snapshot files (the syrupy-repr-only form found only 5).
SNAP_GATE="[\"']command[\"']:\s*[\"']$LEGACY[\"']|^\s*command:\s+$LEGACY\s*\$"

# Idiom-bearing source files: modules that stamp a legacy command name through a
# shape the narrower command="…"/_COMMAND = "…" patterns CANNOT see, so each must
# be scanned with the plain $LEGACY pattern (a true membership check on the file).
# Verified against the live worktree (Decision Log D6, D7):
#   - test_command_surface_matrix.py — _ReadCommand("novel-state",…),
#     _BY_NAME["novel-state"], `if name == "novel-state":` (D6/B3).
#   - tests/steps/per_chapter_loop_steps.py — _BUILD_APPS dict keys +
#     _run_capturing(…, "<legacy>", …) helper arguments (D7/B6).
#   - tests/multiplexer_support.py — RunContext(command=name,…) with a
#     caller-supplied name (D7/B7).
#   - tests/test_multiplexer_behaviour.py — _OPERATIONS legacy_name field +
#     hardcoded driver.legacy(…, "novel-done") (D7/B7).
IDIOM_SOURCES='tests/test_command_surface_matrix.py tests/steps/per_chapter_loop_steps.py tests/multiplexer_support.py tests/test_multiplexer_behaviour.py'
```

The plain `LEGACY` scan over `$IDIOM_SOURCES` is the **idiom-aware** source gate:
it catches every legacy-name stamp expressed as a dict key, a helper argument, a
`NamedTuple` field, an `_ReadCommand`/`_BY_NAME`/`if name ==` literal, or a
caller-supplied `RunContext(command=name, …)` value — all of which the narrower
`command="…"`/`_COMMAND = "…"` patterns cannot see (Decision Log D6 for the
matrix, D7 for the per-chapter-loop and parity modules). Because these four
modules sweep at different work items (the matrix and per-chapter loop in WI2,
the parity pair in WI4 step 1), the closing gate (WI6) scans **all four** so no
sweep's completeness depends on the work-item ordering being remembered.

Skills to load for this stage: `python-router` (already routed), then
`python-testing` for the snapshot-regeneration and BDD-step edits, and
`leta`/`sem` for navigation/history. No property/symbolic-execution adversary is
needed — this is a mechanical rename plus deletions with existing coverage — so
`hypothesis`/`crosshair`/`mutmut` are **not** loaded (the change adds no
new invariant over a range of inputs; AGENTS.md's property-test trigger does not
fire).

### WI1 — Enumerate and pin the consumer set

Docs to read: this Context inventory; AGENTS.md "Python verification and
testing"; `docs/developers-guide.md` §"Shared test scaffolding" (the
consumed-by-name rule, lines 20/52/215).

1. Define the canonical gate patterns (see the Concrete-steps preamble:
   `REG_GATE`, `LEGACY`, `SNAP_GATE`), then run and record the four census greps
   (these are the expected consumer set; any new match in a later run is a
   regression):

   ```bash
   # 1a. Registry symbols (word-anchored so SUBCOMMAND_NAMES is NOT matched):
   rg -n "$REG_GATE" novel_ralph_skill tests
   # 1b. In-process legacy entry-point callers:
   rg -n 'stub\.(novel_state|novel_done|novel_compile|desloppify|wordcount)\(' tests
   # 1c. Snapshot legacy command values — ALL THREE serialisations:
   rg -nP "$SNAP_GATE" tests/__snapshots__
   # 1d. Idiom-aware source scan over ALL FOUR idiom-bearing modules (catches the
   #     matrix's _ReadCommand/_BY_NAME/`if name ==` idiom AND the per-chapter-loop
   #     dict-key/helper-argument idiom (B6) AND the parity pair's caller-supplied
   #     RunContext(command=name,…)/_OPERATIONS/hardcoded driver.legacy idiom (B7),
   #     none of which 1a or the command="…" pattern can see):
   rg -n "$LEGACY" $IDIOM_SOURCES
   ```

   Record the line counts of each in Progress. `rg -P` (PCRE2) is required for
   `$SNAP_GATE` because it uses `\s` and an anchored alternation.

2. Add a fast manifest test `tests/test_legacy_surface_retired.py` that is
   **skipped/xfail in WI1 and flips to active in WI6** — or, preferred, defer the
   manifest assertion to WI6's closing-gate test and use WI1 only to record the
   census in this plan's Progress/Surprises. Decision: defer the executable
   manifest to WI6 (a single `test_no_legacy_surface_symbols` that asserts the
   three greps return empty by importing `novel_ralph_skill.commands.names` and
   asserting `not hasattr(names, "COMMAND_NAMES")` etc., plus a source-scan that
   the legacy entry-point names are absent from `pyproject.toml`'s
   `project_scripts_table()`); WI1 produces no code, only the recorded census.

Tests added/updated: none in WI1 (census recorded in this plan). Validation:
`make all` (unchanged tree → green).

### WI2 — Sweep every legacy command-name stamp to the spaced form

Docs/skills: `python-testing` (snapshot regeneration, BDD-step parametrization),
`leta` (find every `_COMMAND`/`RunContext(command=` site).

For each RUN-GUARD module and BDD step file in the Context inventory, change the
stamped command name from its legacy form to the spaced form, per this fixed map
(the same positional pairing `test_installed_command_names.py` pins today):

- `"novel-state"` → `"novel state"`
- `"novel-done"` → `"novel done"`
- `"novel-compile"` → `"novel compile"`
- `"desloppify"` → `"novel desloppify"`
- `"wordcount"` → `"novel wordcount"`

1. `_COMMAND` constants: edit each `_COMMAND = "<legacy>"` to the spaced literal.
   These modules drive `build_app()` through `run` and assert `envelope["command"]
   == _COMMAND`, so both the stamp and the assertion move together. One module,
   `tests/test_novel_state_mutators.py`, *also* carries a module-docstring line
   (line 14: ``RunContext(command="novel-state", working_dir="working", …)``)
   that documents the exact `_COMMAND` stamp on line 38. That docstring name is
   **load-bearing for the stamp this WI changes**, so it is swept to ``novel
   state`` in the same commit under the Constraints docstring carve-out (lines
   67-70). Sweeping it here (rather than deferring to 1.2.16) is also what keeps
   the WI4 D3 source gate's plain `LEGACY` scan honest: that one line is the only
   docstring-prose occurrence of `command="novel-state"` in `tests/` (verified,
   Decision Log D6), so once it is swept the D3 gate has no inert-prose
   false-positive and need not special-case docstrings.
2. Inline `RunContext(command="<legacy>", …)` in the five BDD step files: edit
   the literal to the spaced name. Where the step file also asserts the command
   name (e.g. against a snapshot or a `then` clause), update that too.
3. `tests/test_command_surface_matrix.py`: this module stamps the legacy name in
   **three idioms** that the `command="…"`/`_COMMAND = "…"` patterns do not see,
   so each must be swept by hand and confirmed with the matrix-aware `LEGACY`
   scan:
   - the `_ReadCommand("novel-state", …)` tuples in `_READ_REGISTRY` (lines
     127-131) — change each first-field literal to the spaced form;
   - the `_BY_NAME["novel-state"]` / `_BY_NAME["novel-done"]` … lookups (lines
     581, 610, 632, 678, 716) — change each key to the spaced form;
   - the `if name == "novel-done":` / `if name == "novel-compile":` branches
     (lines 495, 497) — change each compared literal to the spaced form.
   The module stamps `command=command.name` into `RunContext`, so renaming the
   registry names is what moves every matrix stamp. (Note: the symbol is
   `_ReadCommand`; the error arm is `_ErrorArm`, not `_ErrorCommand`. There is no
   `_ErrorCommand` symbol.) The matrix's parametrize ids change accordingly,
   which renames the snapshot keys — handled by regeneration in step 5.

   After this edit, `rg -n "$LEGACY" tests/test_command_surface_matrix.py` must
   return no match. This is the executable guarantee that the matrix names now
   equal the spaced set; it is the matrix-aware check the D3 gate (WI4) relies
   on.
3a. `tests/steps/per_chapter_loop_steps.py` (B6): this BDD step module stamps the
   legacy name through a **dict-key / helper-argument idiom** that neither the
   `command="…"` nor the `_COMMAND = "…"` pattern can see, so each site is swept
   by hand and confirmed with the plain `LEGACY` scan:
   - the `_BUILD_APPS` dict keys (lines 65-71) — change each of the five **keys**
     (`"novel-state"`, `"novel-done"`, `"wordcount"`, `"desloppify"`,
     `"novel-compile"`) to the spaced form (`"novel state"`, `"novel done"`,
     `"novel wordcount"`, `"novel desloppify"`, `"novel compile"`);
   - the six `_run_capturing(working, "<legacy>", …)` `When`-step call sites —
     `run_recount` line 142 (`"novel-state"`), `run_novel_done` line 165
     (`"novel-done"`), `run_wordcount` line 182 (`"wordcount"`), `run_desloppify`
     line 210 (`"desloppify"`), `run_compile_check` line 228 (`"novel-compile"`),
     and `run_advance_phase` line 317 (`"novel-state"`) — change each positional
     `command_name` literal to the matching spaced form. The `command_name` value
     is both the `_BUILD_APPS` dict key *and* the `RunContext(command=…)` stamp
     (lines 106-108), so the dict-key and the call-site literal must move together
     or `_BUILD_APPS[command_name]` raises `KeyError`.
   - the `_Outcome.captures` map is keyed by a per-step **capture label** set in
     each `When` step and read back in the `Then` steps; today some of those labels
     reuse a legacy command literal (`"novel-done"` lines 165/173, `"wordcount"`
     lines 182/196/201, `"desloppify"` lines 210/218, `"novel-compile"` lines
     228/236/240/271/281, `"advance-phase"` lines 316/324 — and `"recount"` line
     141 which is already non-legacy). These labels are *internal map keys*, not
     `RunContext` stamps, so they would not break under the narrowed guard — **but**
     they would defeat the closing `$LEGACY` source gate (a benign-looking
     false-positive that makes the gate's emptiness no longer a proof). To keep
     the gate a true membership check — the same discipline the matrix sweep uses
     — rename the **four** legacy-command-shaped labels to the spaced form
     (`"novel-done"` → `"novel done"`, `"wordcount"` → `"novel wordcount"`,
     `"desloppify"` → `"novel desloppify"`, `"novel-compile"` → `"novel compile"`).
     Each label appears as the `outcome.captures["<label>"] = …` write in the
     `When` step **and** as the matching read in the `Then` step — both the direct
     `outcome.captures["<label>"]` reads (lines 173, 196, 218, 236, 271, 281) and
     the `_result(outcome, "<label>")` argument (lines 157, 175, 199, 220, 240,
     275, 285) — so every write/read pair for a label moves together or the
     `Then` step raises `KeyError`. The two non-legacy labels `"recount"` and
     `"advance-phase"` carry no legacy command literal (they do not match
     `$LEGACY`) and are left unchanged. This is a pure-internal rename (no
     envelope/snapshot impact, no behaviour change) and is the cheapest way to make
     the file reach zero `$LEGACY` matches outside prose.
   - the module docstring (lines 2-9, 18-20) carries inert `novel-done`/
     `novel-compile`/`wordcount`/`desloppify` spine prose. Sweep these to the
     spaced `novel <verb>` form in the same commit under the Constraints docstring
     carve-out (lines 67-70): the carve-out permits sweeping a docstring name when
     it would otherwise leave the `$LEGACY` source gate unable to prove the file
     clean. After the dict-key, call-site, capture-label, and docstring sweeps the
     file has **zero** `$LEGACY` matches, so its scan in the D3 (WI4 step 1) and
     closing (WI6) gates is a genuine completeness proof — no per-file exception
     and no docstring exclusion is needed.

   After this edit, run the binder to confirm every stamp is accepted while the
   guard still contains both forms, then prove the file is clean:

   ```bash
   uv run pytest tests/test_per_chapter_loop_bdd.py -q
   rg -n "$LEGACY" tests/steps/per_chapter_loop_steps.py   # must return no match
   ```

   The binder must pass; a missed dict-key/call-site pairing surfaces immediately
   as a `KeyError` (mismatched key) or, once WI4 narrows the guard, a `ValueError`
   at envelope build — which is exactly why this module is now in the WI4 D3 source
   gate. The empty `$LEGACY` scan is the executable guarantee the per-chapter-loop
   stamps now equal the spaced set (the B6 fix).
4. Run the affected suites to confirm the spaced names are accepted (the guard
   still contains both forms, so this is green):

   ```bash
   uv run pytest tests/test_command_surface_matrix.py tests/test_novel_state_mutators.py \
     tests/test_reconcile.py tests/test_per_chapter_loop_bdd.py tests/steps -q
   ```

5. Regenerate **all 12** affected snapshot files and review each diff — the only
   permitted change is the `command:` value (and, for the matrix, the snapshot
   *key* name following the parametrize-id rename). The 12 modules are the
   complete set whose `.ambr` carries a legacy command value in any of the three
   serializations (verified, Decision Log D6); `test_contract_envelope` is
   included here because its `.ambr` carries the bare-YAML `command:
   novel-state` and the JSON form, and its stamp moves once `COMMAND_NAMES[0]`
   becomes `SUBCOMMAND_NAMES[0]` (that source swap happens in WI4 step 3; running
   the regeneration here keeps WI2 self-consistent and WI4 re-runs it
   unconditionally — see WI4 step 8):

   ```bash
   uv run pytest tests/test_command_surface_matrix.py tests/test_novel_done_snapshots.py \
     tests/test_desloppify_snapshots.py tests/test_ledger_snapshots.py \
     tests/test_wordcount_snapshots.py tests/test_compile_snapshots.py \
     tests/test_compile_check_snapshots.py tests/test_novel_state_check_disk.py \
     tests/test_novel_state_mutator_snapshots.py tests/test_reconcile_refuse.py \
     tests/test_contract_envelope.py tests/test_contract_envelope_snapshots.py \
     --snapshot-update
   git --no-pager diff -- tests/__snapshots__
   ```

   Then re-run the snapshot gate to prove every legacy command value is gone
   from the snapshots (all three forms):

   ```bash
   rg -nP "$SNAP_GATE" tests/__snapshots__   # must return no match
   ```

   If any non-`command` field changed, stop and escalate (Tolerances).

Tests added/updated: the ≈27 RUN-GUARD modules and 5 inline BDD step files (each
gets stamp and assertion edits), the matrix module (three idioms, step 3),
`tests/steps/per_chapter_loop_steps.py` (dict keys, six call sites, four capture
labels, docstring — step 3a, B6), the one load-bearing docstring line in
`test_novel_state_mutators.py` (step 1), and **all 12** regenerated `.ambr` files.
No new test files. This work item may be split into a few atomic commits (e.g.
"sweep the `novel-state` family", "sweep `novel-compile`/`done`", "sweep
`desloppify`/`wordcount`", "sweep per-chapter-loop steps", "regenerate
snapshots") provided each commit is `make all`-green; record the split in
Progress. Validation: `make all`, then the idiom-aware source scans
(`rg -n "$LEGACY" tests/test_command_surface_matrix.py` and
`rg -n "$LEGACY" tests/steps/per_chapter_loop_steps.py`, both empty) and the
snapshot gate (`rg -nP "$SNAP_GATE" tests/__snapshots__`, empty).

### WI3 — Re-point in-process `stub.<entry>()` callers onto `novel.main()`

Docs/skills: `python-testing`; `leta` for callers.

For each ASSERT-ONLY in-process e2e module
(`test_reconcile_e2e.py`, `test_compile_e2e.py`,
`test_compile_check_integration.py`, `test_novel_state_check.py`,
`test_set_chapters_e2e.py`, `test_recount_e2e.py`):

1. Replace `from novel_ralph_skill.commands import stub` with
   `from novel_ralph_skill.commands import novel`.
2. Replace each `monkeypatch.setattr(sys, "argv", [name, *extra]); stub.<entry>()`
   with the multiplexer form
   `monkeypatch.setattr(sys, "argv", ["novel", "<verb>", *extra]); novel.main()`,
   where `<verb>` is the mount verb (`state`/`done`/`compile`/`desloppify`/
   `wordcount`) and, for the `novel-state` command group, the read subcommand
   (`check`, etc.) is already part of `extra`.
3. Update **every** legacy command-name assertion in these modules to the spaced
   name (the multiplexer stamps `"novel state"` etc.). This is **not** limited to
   the JSON-envelope `envelope["command"] == "<legacy>"` shape; it explicitly
   includes the **human-rendered** output substring assertion, because
   `render_human` (`novel_ralph_skill/contract/envelope.py` line 172) emits
   `f"command: {env.command}"`, so the human report carries the literal
   `command: <name>`. Sweep all three shapes:
   - the JSON-envelope assertion `envelope["command"] == "<legacy>"` (and any
     `_COMMAND = "<legacy>"` module constant feeding it) → the spaced name;
   - the **human-output** assertion of the form `assert "command: <legacy>" in
     out` → `assert "command: <spaced>" in out`. In this WI3 set the only such
     site is **`tests/test_novel_state_check.py:207`** —
     `assert "command: novel-state" in out` in
     `test_entry_point_human_flag_switches_rendering` — which must become
     `assert "command: novel state" in out`. That module's `_drive_entry_point`
     (line 191) is re-pointed from `stub.novel_state()` to `novel.main()` by
     step 2, and `novel.main()` stamps `command="novel state"`, so the
     human-output substring **must** move with it or the assertion fails at WI3's
     `make all`. The **adjacent line 208** `assert "working_dir: working" in out`
     names a *directory* (`env.working_dir`), not a command, and is unchanged by
     this task — leave it exactly as-is. (Verified against the live worktree: this
     line-207 site is the only human-output `command: <legacy>` assertion in
     `tests/` source — `tests/test_console_scripts_error_arms_e2e.py:242` and
     `tests/test_multiplexer_behaviour.py:297` already use the spaced name, and
     the lone `.ambr` hit is a snapshot covered by `$SNAP_GATE`.) If a future read
     of these modules surfaces a second human-output `command: <legacy>`
     assertion, sweep it the same way; the step-3a gate below proves none remains.
4. Correct the module docstrings' `stub.novel_state()` wording to
   `novel.main()` only where the stale name is now load-bearing for the changed
   invocation (Constraints carve-out); broader prose stays for 1.2.16.

Confirm no in-process caller remains, and prove the human-output sweep is complete
by construction (the B8 fix — this gate must run **inside WI3**, not only at WI6,
so the defect cannot evade WI3's own `make all`):

```bash
# (a) no in-process legacy entry-point caller survives:
rg -n 'stub\.(novel_state|novel_done|novel_compile|desloppify|wordcount)\(' tests
# (b) no human-rendered `command: <legacy>` substring assertion survives in the
#     WI3 re-point set (the colon-space form render_human emits — NOT the
#     `command="…"` equals form D3 scans). $LEGACY is the canonical pattern from
#     the Concrete-steps preamble. Must return no match:
WI3_REPOINT='tests/test_reconcile_e2e.py tests/test_compile_e2e.py'
WI3_REPOINT="$WI3_REPOINT tests/test_compile_check_integration.py"
WI3_REPOINT="$WI3_REPOINT tests/test_novel_state_check.py"
WI3_REPOINT="$WI3_REPOINT tests/test_set_chapters_e2e.py tests/test_recount_e2e.py"
rg -nP "command:\s+$LEGACY" $WI3_REPOINT
```

Both (a) and (b) must return no match. Gate (b) is the executable guarantee that
the colon-space human-output idiom — which the D3 `command="…"` scan, the bare-YAML
arm of `$SNAP_GATE` (which runs only over `tests/__snapshots__`), and
`$IDIOM_SOURCES` (which does not list these six modules) all structurally miss —
leaves no legacy literal behind. Validation: `make all` — note this runs the
in-process e2e through `novel.main()`, exercising the surviving entry point
end-to-end; gate (b) must already be empty, so the human-output assertion can never
surface as a late `make all` failure.

### WI4 — Narrow the guard and registry; re-home the seam; rework parity

Docs/skills: `python-router` → `python-types-and-apis` only if a signature shifts
(none expected); `python-testing` for the parity rework; `arch-crate-design` is
not needed (no crate/module-boundary change).

The step ordering inside WI4 is forced by the guard, exactly as the WI-level
ordering is: **every** test-side legacy stamp — including the parity pair's — is
swept to the spaced form (steps 1-5) *before* the guard narrows (step 6), so no
stamp is ever rejected at envelope build. Step 1's parity rework therefore comes
**first**, not last; the round-2 ordering (narrow, then rework parity) would have
left the parity pair's stamps faulting between the narrowing and the rework (the
B7 fault). The single D3 gate then runs over **all four** idiom-bearing modules
(step 5) and only then does the guard narrow.

1. Rework the parity suite per D1 (B7 — this is now the **first** WI4 step, before
   the guard narrows): in `tests/multiplexer_support.py` rename the `legacy` arm
   to `direct` (keep the `mux` arm) — its `_capture` helper stamps
   `RunContext(command=name, …)` from the caller-supplied `name` (line 105), so
   the rework lives entirely in the **caller-supplied names**, not in this module's
   body; in `tests/test_multiplexer_behaviour.py` change `_Operation` to carry the
   spaced name and update **every** site that supplies a legacy name to the
   `direct`/`legacy` arm. Enumerate them exhaustively (verified against the live
   worktree — there are exactly two name-supplying shapes):
   - the `_OPERATIONS` tuple `legacy_name` field (lines 68-72) — change each of
     the five literals to the spaced form, and rename the field/`_OPERATION_IDS`
     accordingly (`legacy_name` → `name`); the parametrized call site at lines
     135-136 (`driver.legacy(op.legacy_build, op.spaced[1:], op.legacy_name)`)
     follows the renamed field;
   - the **hardcoded** `driver.legacy(_novel_done.build_app, [], "novel-done")`
     at line 156 in `test_multiplexer_done_success_matches_legacy` — change the
     third argument to `"novel done"`.

   Then drop the `_strip_command` carve-out and assert full envelope equality
   **including** `command` at **both** comparison sites (now that both arms stamp
   the same spaced name): line 141 (the parametrized
   `test_multiplexer_matches_legacy_over_drafting_tree`, replacing the
   `_strip_command(mux_out) == _strip_command(legacy_out)` pair and folding the
   two now-redundant `command`-field assertions at lines 143-144 into the equality)
   and line 161 (the hardcoded `test_multiplexer_done_success_matches_legacy`,
   replacing `_strip_command(mux_out) == _strip_command(legacy_out)`). Delete the
   `_strip_command` helper (lines 77-96) once both call sites no longer use it.
   This is *stronger* coverage than round 2 (the `command` field is now compared
   too), per D1. Keep all exit-arm coverage (0/1/2/3/4, help/version/bare). After
   this edit `rg -n "_strip_command\b" tests/test_multiplexer_behaviour.py` and
   `rg -n "$LEGACY" tests/multiplexer_support.py tests/test_multiplexer_behaviour.py`
   must both return no match — the executable guarantee the parity rework is
   complete (the B7 fix).
2. `tests/conftest.py` line 339: `make_contract_app(COMMAND_NAMES[0])` →
   `make_contract_app("novel state")` and drop the now-unused
   `from novel_ralph_skill.commands.names import COMMAND_NAMES` import (D5).
3. `tests/test_contract_envelope.py`, `test_contract_properties.py`,
   `test_contract_runner.py`, `test_contract_envelope_snapshots.py`: replace
   `COMMAND_NAMES` with `SUBCOMMAND_NAMES` (stamps and `sampled_from`), and in
   `test_contract_envelope.py` replace the
   `set(COMMAND_NAMES) <= set(ENVELOPE_COMMAND_NAMES)` assertion with
   `set(SUBCOMMAND_NAMES) <= set(ENVELOPE_COMMAND_NAMES)` and
   `assert "novel" in ENVELOPE_COMMAND_NAMES` (drop the legacy-subset line).
4. Re-home `tests/test_contract_app_centralisation.py` per D2: keep
   `test_real_build_app_carries_the_four_flag_contract`; rewrite
   `test_real_entry_point_routes_through_the_shared_seam` to monkeypatch
   `novel.run` and assert `novel.main()` (under `sys.argv = ["novel"]`) routes a
   four-flag-contract `build_multiplexer()` app through it. Update the imports
   (`from novel_ralph_skill.commands import novel`) and docstrings.
5. Run the D3 gate greps (using the canonical `LEGACY`/`SNAP_GATE`/`IDIOM_SOURCES`
   from the Concrete-steps preamble); **all must be empty** before narrowing the
   guard:

   ```bash
   # (a) explicit RunContext stamps and _COMMAND constants:
   rg -n "command=\"$LEGACY\"" tests
   rg -n "_COMMAND = \"$LEGACY\"" tests
   # (b) idiom-aware scan over ALL FOUR idiom-bearing modules — catches the
   #     matrix's _ReadCommand/_BY_NAME/`if name ==` idiom (B3), the
   #     per-chapter-loop dict-key/helper-argument idiom (B6), and the parity
   #     pair's caller-supplied RunContext(command=name,…)/_OPERATIONS/hardcoded
   #     driver.legacy idiom (B7) — none of which (a) can see:
   rg -n "$LEGACY" $IDIOM_SOURCES
   # (c) snapshots — ALL THREE serialisations (the B1 false-negative fix):
   rg -nP "$SNAP_GATE" tests/__snapshots__
   ```

   The `command="…"` scan in (a) is now genuinely empty after a correct WI2
   sweep: the only inert-docstring occurrence (`test_novel_state_mutators.py`
   line 14) was swept in WI2 step 1 under the Constraints carve-out (the B5
   false-positive fix), so no docstring/comment exclusion is needed. Scan (b) is
   empty because WI2 step 3/3a swept the matrix and the per-chapter loop and WI4
   step 1 swept the parity pair; if (b) flags the parity pair, WI4 step 1 was not
   completed — fix the rework, do not weaken the gate. If (a) still flags a
   docstring line, WI2 step 1 was not completed.
6. In `novel_ralph_skill/commands/names.py`: redefine `ENVELOPE_COMMAND_NAMES` as
   `tuple(dict.fromkeys((*SUBCOMMAND_NAMES, MULTIPLEXER_NAME)))` (drop the
   `*COMMAND_NAMES` term). Do **not** yet delete `COMMAND_NAMES`/
   `COMMAND_ENTRY_POINTS`/`STUB_MODULE` (still imported by `stub.py`, removed in
   WI5). Update the module docstring's "superset of the legacy five and the
   spaced names" wording to "the spaced `novel <verb>` names plus the bare
   `novel` surface".
7. In `novel_ralph_skill/contract/envelope.py`: update the `build_envelope`
   docstring's "superset of the legacy five and the spaced names" wording to the
   multiplexer-only description. No code change (the guard reads the narrowed
   tuple).
8. Regenerate the snapshots touched by steps 1-3. Step 3 swaps
   `COMMAND_NAMES[0]`→`SUBCOMMAND_NAMES[0]` in `test_contract_envelope.py` line
   59, so **`test_contract_envelope` is regenerated unconditionally here** (its
   `.ambr` carries the bare-YAML and JSON `command: novel-state`); regenerate
   `test_contract_envelope_snapshots` as well if its stamped names changed:

   ```bash
   uv run pytest tests/test_contract_envelope.py \
     tests/test_contract_envelope_snapshots.py --snapshot-update
   git --no-pager diff -- tests/__snapshots__/test_contract_envelope.ambr \
     tests/__snapshots__/test_contract_envelope_snapshots.ambr
   ```

   Then prove the snapshots are clean across all three serializations:

   ```bash
   rg -nP "$SNAP_GATE" tests/__snapshots__   # must return no match
   ```

   The only permitted diff is the `command:` line moving to the spaced name.

Tests updated: the parity pair (`tests/multiplexer_support.py`,
`tests/test_multiplexer_behaviour.py` — B7), the conftest fixture, the four
contract modules, and the re-homed centralization module. Validation: `make all`
— the guard now rejects legacy names; any missed stamp surfaces here, but the D3
greps (step 5, over all four idiom sources including the parity pair) should have
caught it first. Note the ordering: the parity rework (step 1) precedes the guard
narrowing (step 6), so the parity pair never stamps a legacy name into a narrowed
guard (the B7 fault is structurally impossible).

### WI5 — Delete the legacy entry points and registry symbols

Docs/skills: `python-router`; `leta` for the final consumer sweep; `sem` to
confirm the deleted symbols' last live use.

1. Gate grep (using the **word-anchored** `REG_GATE` so it does not
   substring-match the kept `SUBCOMMAND_NAMES` — the B4 fix; must be empty before
   deleting each symbol):

   ```bash
   rg -n "$REG_GATE" novel_ralph_skill tests
   rg -n 'from novel_ralph_skill\.commands import stub|commands\.stub' tests novel_ralph_skill
   ```

   The first must show only `names.py` (the definitions about to be removed) and
   any not-yet-deleted legacy-only test from step 5; the second must be empty
   (WI3 removed the last `stub` import). If either shows an unexpected consumer,
   re-point it first (complete-by-construction). Note: an unanchored
   `COMMAND_NAMES` scan would also match every surviving `SUBCOMMAND_NAMES`
   reference and never empty — always use `$REG_GATE`.
2. `pyproject.toml`: delete the five legacy `[project.scripts]` lines (11-15),
   leaving only `novel = "novel_ralph_skill.commands.novel:main"`.
3. Delete `novel_ralph_skill/commands/stub.py` entirely.
4. In `names.py`: delete `STUB_MODULE`, `_COMMAND_ENTRY_POINTS`,
   `COMMAND_ENTRY_POINTS`, and `COMMAND_NAMES`; simplify `project_scripts_table()`
   to return `{ MULTIPLEXER_NAME: f"{NOVEL_MODULE}:{_MULTIPLEXER_ENTRY_POINT}" }`;
   update the module docstring to describe only the `novel` surface.
5. Delete the legacy-only tests: `tests/test_command_stubs.py`,
   `tests/test_installed_command_names.py`, and the
   `test_registry_pins_the_five_legacy_names` /
   `test_entry_points_resolve_to_callables` /
   `test_script_table_adds_the_novel_multiplexer` cases in
   `tests/test_command_names_registry.py` (replace the last with a
   `test_script_table_is_novel_only` asserting
   `tuple(names.project_scripts_table()) == ("novel",)`); keep
   `test_subcommand_names_pin_the_five_spaced_operations`,
   `test_registry_matches_project_scripts`, `test_registry_order_matches_table`,
   and `test_multiplexer_entry_point_resolves_to_a_callable`.
   `tests/test_pyproject_scripts.py` passes unchanged (derives from the table).
6. Add the WI6 manifest test `tests/test_legacy_surface_retired.py` (see WI6) and
   confirm it passes.

Validation: `make all`, including the installed-binary e2e
(`test_console_scripts_e2e.py`) which now builds a wheel exporting exactly one
script.

### WI6 — Closing grep gate and full validation

1. Run the closing grep gate (using the canonical
   `REG_GATE`/`SNAP_GATE`/`LEGACY`/`IDIOM_SOURCES`; all must be empty in
   `novel_ralph_skill/` and `tests/`):

   ```bash
   # Registry symbols + stub module, word-anchored (B4) so SUBCOMMAND_NAMES is
   # not matched:
   rg -n "$REG_GATE|commands\.stub" novel_ralph_skill tests
   # Legacy console-script literals in pyproject:
   rg -n 'novel-state|novel-done|novel-compile' pyproject.toml
   # Idiom-aware source scan over ALL FOUR idiom-bearing modules — the matrix
   # (B3), the per-chapter-loop steps (B6), and the parity pair (B7) — none of
   # whose stamping shapes the REG_GATE/command="…" patterns can see:
   rg -n "$LEGACY" $IDIOM_SOURCES
   # Human-rendered colon-space command literal across ALL of tests/ (the B8 fix):
   # render_human (envelope.py:172) emits `command: <name>`, so a human-output
   # assertion carries `command: <legacy>` — a shape neither command="…" (D3) nor
   # the bare-YAML arm of $SNAP_GATE (which scans only tests/__snapshots__) sees.
   # This repo-wide spaced-only invariant proves no source module reintroduced it:
   rg -nP "command:\s+$LEGACY" tests
   # Snapshot legacy command values across ALL THREE serialisations (B1):
   rg -nP "$SNAP_GATE" tests/__snapshots__
   ```

2. Confirm `tests/test_legacy_surface_retired.py` asserts: `names` has no
   `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`/`STUB_MODULE` attribute (via
   `hasattr`, which is exact and immune to the substring/word-boundary concern);
   `importlib.util.find_spec("novel_ralph_skill.commands.stub") is None`;
   `tuple(names.project_scripts_table()) == ("novel",)`; and the parsed
   `pyproject.toml [project.scripts]` has exactly the `novel` key (reusing the
   `project_scripts` conftest fixture). Because this test asserts on the
   *imported symbols* and the *parsed table* rather than on grep output, it is
   immune to both gate pitfalls (the `SUBCOMMAND_NAMES` substring and the
   three-serialization snapshot forms): it is the durable regression guard that
   outlives the one-shot grep gates. It additionally carries a **source-scan**
   case `test_no_legacy_command_literals_in_idiom_sources` that reads each of the
   four `$IDIOM_SOURCES` files (`tests/test_command_surface_matrix.py`,
   `tests/steps/per_chapter_loop_steps.py`, `tests/multiplexer_support.py`,
   `tests/test_multiplexer_behaviour.py`) via `Path.read_text()` and asserts none
   contains any of the five legacy command literals (`novel-state`, `novel-done`,
   `novel-compile`, `desloppify`, `wordcount`) — the durable B3/B6/B7 guard that
   would otherwise rely only on the one-shot WI6 grep. (These four files carry no
   legitimate legacy literal after the sweeps, so a plain `in` membership test is
   exact; if a future edit re-introduces one of the idiom stamps, this case fails
   without waiting for the guard to narrow.) It also carries a
   `test_no_legacy_human_command_header_in_repointed_e2e` case (the durable **B8**
   guard) that reads each of the six WI3 re-pointed in-process e2e modules
   (`tests/test_reconcile_e2e.py`, `tests/test_compile_e2e.py`,
   `tests/test_compile_check_integration.py`, `tests/test_novel_state_check.py`,
   `tests/test_set_chapters_e2e.py`, `tests/test_recount_e2e.py`) via
   `Path.read_text()` and asserts none contains a human-rendered
   `command: <legacy>` header for any of the five legacy names — i.e. the
   colon-space form `render_human` (`envelope.py:172`) emits. This is the durable
   counterpart to WI3 gate (b): the `command="…"`/`$SNAP_GATE`/`$IDIOM_SOURCES`
   gates all structurally miss this idiom (it is a colon-space substring in a
   source assertion, not an equals-stamp, not a snapshot, and these six modules
   are not in `$IDIOM_SOURCES`), so this case is the only thing that would catch
   a re-introduced human-output legacy header in a `make test` run rather than at
   a later regression.
3. Run the full gate and the installed e2e explicitly:

   ```bash
   make all
   uv run pytest tests/test_console_scripts_e2e.py tests/test_console_scripts_error_arms_e2e.py -m slow -q
   ```

4. Update this plan's Progress, Surprises, Decision Log, and Outcomes; append the
   Revision note.

Validation: `make all` green; the two slow installed-e2e modules green; the grep
gate empty.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- Build and install into a throwaway venv; exactly one script, `novel`, appears
  in the venv `bin/`:

  ```bash
  uv build --wheel . --out-dir /tmp/w && uv venv /tmp/v \
    && uv pip install --python /tmp/v/bin/python /tmp/w/*.whl \
    && ls /tmp/v/bin | rg '^(novel|novel-state|novel-done|novel-compile|desloppify|wordcount)$'
  ```

  Expect a single line: `novel`. (This is what `test_console_scripts_e2e.py`
  automates.)

- The word-anchored registry gate
  `rg -n '\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b|commands\.stub'
  novel_ralph_skill tests` returns no match. (The word boundaries are
  load-bearing: an unanchored `COMMAND_NAMES` would match the ≈25 surviving
  `SUBCOMMAND_NAMES` references and could never return empty — see Decision Log
  D6.)
- The three-serialization snapshot gate
  `rg -nP "[\"']command[\"']:\s*[\"'](novel-state|novel-done|novel-compile|desloppify|wordcount)[\"']|^\s*command:\s+(novel-state|novel-done|novel-compile|desloppify|wordcount)\s*$"
  tests/__snapshots__` returns no match (it catches the syrupy-repr, JSON, and
  bare-YAML forms; the syrupy-repr-only form alone would miss 7 of the 12 legacy
  snapshots — Decision Log D6).
- The idiom-aware source gate
  `rg -n '(novel-state|novel-done|novel-compile|desloppify|wordcount)'
  tests/test_command_surface_matrix.py tests/steps/per_chapter_loop_steps.py
  tests/multiplexer_support.py tests/test_multiplexer_behaviour.py` returns no
  match (it catches the dict-key/helper-argument, `_ReadCommand`/`_BY_NAME`,
  `_OPERATIONS`-field, and hardcoded `driver.legacy` idioms that the
  `command="…"`/`REG_GATE` patterns cannot see — Decision Log D6/D7, B3/B6/B7).

- The parity suite still proves no-behaviour-change: running
  `uv run pytest tests/test_multiplexer_behaviour.py -q` passes;
  `test_multiplexer_matches_legacy_over_drafting_tree` **and**
  `test_multiplexer_done_success_matches_legacy` now assert full envelope equality
  **including** `command` between the multiplexer and the direct `build_app` drive
  (the `_strip_command` carve-out is removed at both sites — Decision Log D1/D7,
  B7), and `rg -n '_strip_command|driver\.legacy\("?novel-'
  tests/test_multiplexer_behaviour.py` returns no match.

Quality criteria ("done"):

- Tests: `make test` passes (the full suite, including the slow installed e2e
  under `-n auto`); the new `test_legacy_surface_retired.py` passes; the parity
  suite passes with the strengthened assertion; every regenerated snapshot's only
  change is the `command:` value/key.
- Lint/typecheck: `make lint` (Ruff + interrogate 100% + Pylint) and `make
  typecheck` (`ty`) pass.
- Audit: `make audit` (`pip-audit`) passes (no dependency change).
- Markdown: this plan file passes `make markdownlint` and `make nixie` (no
  Mermaid here, so nixie is a no-op pass).

Quality method: `make all` per commit, plus `make markdownlint` and `make nixie`
on any commit that touches this `.md`.

## Idempotence and recovery

Every work item is a sequence of edits + `make all`; re-running `make all` is
safe. Snapshot regeneration is idempotent (re-running `--snapshot-update` on an
already-swept tree is a no-op). The grep gates are read-only. If a deletion in
WI5 is found premature (a consumer surfaces), `git checkout -- <file>` restores
it; re-point the consumer, then re-delete. No destructive or irreversible step
exists; the worktree is disposable.

## Artefacts and notes

The load-bearing guard is `novel_ralph_skill/contract/envelope.py`:

```python
if command not in ENVELOPE_COMMAND_NAMES:
    msg = f"unknown command {command!r}; expected one of {ENVELOPE_COMMAND_NAMES}"
    raise ValueError(msg)
```

This is why WI2 must precede WI4: every legacy stamp must move to the spaced form
*before* `ENVELOPE_COMMAND_NAMES` sheds the legacy names, or this raises at
envelope-build time.

The kept registry shape after WI5 (`novel_ralph_skill/commands/names.py`):

```python
NOVEL_MODULE: str = "novel_ralph_skill.commands.novel"
MULTIPLEXER_NAME: str = "novel"
_MULTIPLEXER_ENTRY_POINT: str = "main"
SUBCOMMAND_NAMES: tuple[str, ...] = (
    "novel state", "novel done", "novel compile",
    "novel desloppify", "novel wordcount",
)
ENVELOPE_COMMAND_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys((*SUBCOMMAND_NAMES, MULTIPLEXER_NAME))
)

def project_scripts_table() -> dict[str, str]:
    return {MULTIPLEXER_NAME: f"{NOVEL_MODULE}:{_MULTIPLEXER_ENTRY_POINT}"}
```

## Interfaces and dependencies

Locked libraries (unchanged): cuprum `0.1.0`, cyclopts `4.18.0`. No new
dependency.

At the end of this task the public command-name registry
(`novel_ralph_skill.commands.names`) exposes exactly:

- `NOVEL_MODULE: str`
- `MULTIPLEXER_NAME: str` (`"novel"`)
- `SUBCOMMAND_NAMES: tuple[str, ...]` (the five spaced names)
- `ENVELOPE_COMMAND_NAMES: tuple[str, ...]` (the five spaced names + `"novel"`)
- `project_scripts_table() -> dict[str, str]` (the single `novel` entry)

and **does not** expose `COMMAND_NAMES`, `COMMAND_ENTRY_POINTS`, or
`STUB_MODULE`. The module `novel_ralph_skill.commands.stub` no longer exists. The
sole console-script entry point is
`novel = "novel_ralph_skill.commands.novel:main"`.

## Revision note

- Round 1 → Round 2 (2026-06-26): resolved the five blocking points from the
  Logisphere design review (`roadmap-1-2-15.logisphere-review-r1.md`), all of
  which concerned the soundness of the grep gates the plan's
  complete-by-construction guarantee rests on. Verified each fix against the
  live worktree (Decision Log D6). (WI4 internal step numbers in the bullets
  below are the round-2 numbering; round 3 reordered WI4 — see the round-3
  note — so the live WI4 now reworks parity at step 1, runs the D3 gate at
  step 5, narrows the guard at step 6, and regenerates snapshots at step 8.)
  - B1 (snapshot gate false-negative): the snapshot gate matched only the
    syrupy-repr form and missed 7 of 12 legacy snapshots stored as JSON-envelope
    or bare-YAML. Replaced with the canonical `$SNAP_GATE` (three serializations)
    in WI1, WI4-D3, WI4 step 8, WI6, and Acceptance.
  - B2 (regeneration completeness): added `test_contract_envelope` to the WI2
    step-5 regeneration list and made WI4 step 8 regenerate it **unconditionally**
    (its `.ambr` carries the JSON and bare-YAML legacy command, and its stamp
    moves when WI4 step 5 swaps `COMMAND_NAMES[0]`→`SUBCOMMAND_NAMES[0]`).
  - B3 (matrix-aware gate): WI2 step 3 now enumerates the matrix's three
    stamping idioms (`_ReadCommand(…)`, `_BY_NAME[…]`, `if name == …`) and the
    D3/closing gates add a plain `LEGACY` scan over
    `test_command_surface_matrix.py`, with WI2 asserting that scan empty.
  - B4 (registry gate unsatisfiable): all registry gates anchored with word
    boundaries (`$REG_GATE` = `\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b`),
    verified to exclude the kept `SUBCOMMAND_NAMES`, in WI1, WI5, WI6,
    Acceptance, Outcomes.
  - B5 (deferred-prose false-positive): the one inert-docstring occurrence
    (`test_novel_state_mutators.py` line 14) is swept in WI2 step 1 under the
    Constraints docstring carve-out, so the `command="…"` D3 gate is genuinely
    empty without special-casing comments/docstrings.
  - Advisories: A1 (`_ErrorCommand` → `_ErrorArm`) corrected in WI2 step 3; A2
    (snapshot count 9 → 12) standardized in Tolerances, Surprises, WI2, and the
    Context inventory; A3 (the WI2↔WI5 pairing dependency) recorded in
    Surprises & discoveries.
  - Added a "Canonical gate patterns" subsection to Concrete steps defining
    `REG_GATE`, `LEGACY`, and `SNAP_GATE` once, reused verbatim by every gate.
  - These changes affect only the gate definitions, the regeneration lists, and
    the documentation of why; the work-item ordering, the Decision Log
    dispositions D1-D5, and the production-edit set are unchanged.

- Round 2 → Round 3 (2026-06-26): resolved the two blocking points from the
  round-2 design review (`roadmap-1-2-15.logisphere-review-r2.md`), both of which
  found RUN-GUARD consumers that stamp legacy command names through idioms the
  round-2 gates could not see, violating the plan's own Tolerances escalation rule
  (a missed consumer must be caught by a gate, not by a failing `make all`).
  Verified each fix against the live worktree (Decision Log D7).
  - B6 (`per_chapter_loop_steps.py` omitted): added the module to the RUN-GUARD
    inventory and the Tolerances scope count (≈27 → ≈28), added WI2 step 3a to
    sweep its `_BUILD_APPS` dict keys, its six `_run_capturing(…, "<legacy>", …)`
    call sites, its four legacy-shaped capture-map labels, and its docstring spine
    prose, and added the module to the new `$IDIOM_SOURCES` list scanned by the
    D3 (WI4 step 5) and closing (WI6) source gates and the durable
    `test_legacy_surface_retired.py` source-scan case. The binder
    `tests/test_per_chapter_loop_bdd.py` is now exercised in WI2's validation.
  - B7 (parity rework ungated; hardcoded site omitted; ordering fault):
    reordered WI4 so the parity rework (now step 1) runs **before** the guard
    narrows (now step 6), with the D3 gate (step 5) between them — making the late
    `ValueError` window structurally impossible. WI4 step 1 now enumerates **both**
    name-supplying shapes (`_OPERATIONS.legacy_name` and the hardcoded
    `driver.legacy(_novel_done.build_app, [], "novel-done")` at line 156) and drops
    `_strip_command` at **both** comparison sites (lines 141 and 161), strengthening
    the assertion (D1). `tests/multiplexer_support.py` and
    `tests/test_multiplexer_behaviour.py` joined `$IDIOM_SOURCES`.
  - Introduced the `$IDIOM_SOURCES` shell variable (the four idiom-bearing
    modules) in the Canonical gate patterns subsection, replacing the
    single-module matrix scan in WI1 step 1d, WI4 step 5, and WI6 with a scan over
    all four; renamed the "matrix-aware" gate to the "idiom-aware" gate throughout.
  - Internal WI4 step renumbering (the parity rework moved from step 7 to step 1;
    the guard narrowing from step 2 to step 6) is reflected in every cross-
    reference (Surprises B7, Context B7, Decision Log D6 fact 2, WI2 step 5).
  - These changes extend the inventory, the WI2/WI4 sweeps, the gate set, and the
    WI4 step ordering; the Decision Log dispositions D1-D6 and the production-edit
    set (`names.py`, `stub.py`, `novel.py`, `envelope.py`, `pyproject.toml`) are
    unchanged.

- Round 3 → Round 4 (2026-06-26): resolved the single blocking point from the
  round-3 design review (`roadmap-1-2-15.logisphere-review-r3.md`), which found
  a fourth RUN-GUARD escape — the **human-rendered** output idiom — uncaught by
  every
  round-3 gate, recurring the B6/B7 fault class a fourth time and violating the
  plan's Tolerances escalation rule. Verified each fix against the live worktree
  (Decision Log D8).
  - B8 (`tests/test_novel_state_check.py:207` human-output assertion uncaught):
    `render_human` (`envelope.py:172`) emits `f"command: {env.command}"`, so line
    207's `assert "command: novel-state" in out` asserts against the colon-space
    human form. Its `_drive_entry_point` (line 191) sits in the WI3 re-point set,
    so WI3 re-points it to `novel.main()` (stamping `command="novel state"`) and
    line 207 would fail at WI3's `make all` — yet the D3 gate scans `command="…"`
    (equals), `$SNAP_GATE`'s bare-YAML arm scans only `tests/__snapshots__`, and
    the module is not in `$IDIOM_SOURCES`. Resolution: (1) broadened WI3 step 3
    from "any `envelope["command"] ==`" to **every** legacy command-name assertion,
    explicitly naming the human-output substring shape and
    `test_novel_state_check.py:207-208` by line (with line 208 `working_dir:
    working` left unchanged — it names a directory, not a command); (2) added an
    **in-WI3** gate (b), `rg -nP "command:\s+$LEGACY"` over the six WI3 re-pointed
    modules, so completeness is proven inside WI3, before its `make all`; (3) added
    a repo-wide spaced-only `command:\s+$LEGACY` invariant over `tests/` to the
    WI6 closing gate; and (4) added a
    `test_no_legacy_human_command_header_in_repointed_e2e` source-scan case to the
    durable `tests/test_legacy_surface_retired.py` manifest. Verified the idiom
    is isolated to line 207 in source:
    `tests/test_console_scripts_error_arms_e2e.py:242`
    and `tests/test_multiplexer_behaviour.py:297` already use the spaced name and
    are not in the WI3 set.
  - These changes touch only WI3 step 3, the WI3/WI6 gate sets, the durable
    manifest test, and the documentation of why; the work-item ordering, the
    Decision Log dispositions D1-D7, and the production-edit set (`names.py`,
    `stub.py`, `novel.py`, `envelope.py`, `pyproject.toml`) are unchanged.

- Round 4 → Implementation (2026-06-26): executed WI1-WI6 against the live
  worktree. The plan held; the only deviations are recorded in Outcomes &
  Retrospective and in the per-WI Progress notes:
  - The bare `$LEGACY` idiom gate is unsatisfiable over the matrix and the
    per-chapter-loop steps (production module aliases `_desloppify`/`_wordcount`
    and feature-bound Gherkin step-text substring-match it), so the completeness
    gate is the **refined** scan (hyphenated stamps minus the `@when`/`@then`/
    `@given` decorators); the durable manifest's `_stamp_lines` encodes the same
    exclusion. This is the identical substring pitfall the plan fixed for the
    registry gate, recurring for the legacy literals.
  - `tests/test_command_stubs.py` is deleted in WI4 (the guard-narrowing commit)
    rather than WI5, because the narrowing strands it.
  - One direct literal assertion (`test_wordcount_command.py:94`) was swept in
    WI2 under the "assertion moves with the stamp" rule.
  - The matrix's two operation test functions were renamed to the spaced form
    (`test_novel_wordcount_…`/`test_novel_desloppify_…`) so the test ids reflect
    the new surface; the kept production module aliases were left untouched.
  Coderabbit runs: six (one per work item), all green or with only trivial/minor
  findings addressed or skipped-with-reason (the WI1 absolute-cuprum-path note is
  a deliberate review-log provenance record; the execplans second-person voice is
  a skill convention).

## Addenda

Lightweight follow-on corrections folded onto this completed task. Each runs as
a no-plan, no-review pass: make the change, run the gates, merge.

- [x] **1.2.15.1 — Sweep the stale legacy command-name literals left in test and
  source prose after the surface retirement** (from review:1.2.15 and
  audit:1.2.15; severity: low; three near-identical proposals merged). This task
  retired the hyphenated surface, deleted `stub.py`, and (per the Constraints
  carve-out) deliberately left prose outside the production-module-name scope for
  the prose-sweep tasks. Tasks 1.2.14 and 1.2.16 cover only the design document,
  `SKILL.md`, and the users'/developers' guides, so a residue of stale
  legacy-form names survives in test and source prose:
  - `tests/test_pyproject_scripts.py`'s registry-table docstring still describes
    the `[project.scripts]` table as "the legacy five plus the novel
    multiplexer", though the table is now novel-only (the assertion is already
    correct; only the prose contradicts the code).
  - `tests/features/per_chapter_loop.feature` Gherkin step-text still names
    `novel-done`, `wordcount`, `desloppify`, and `novel-compile` in the
    hyphenated form.
  - `tests/test_contract_app_centralisation.py` labels its build-apps with the
    retired hyphenated names (`novel-state`, `novel-done`, `novel-compile`,
    `desloppify`).
  - `novel_ralph_skill/commands/novel.py`'s docstrings and comments reference the
    now-deleted `stub.py` in the present tense ("relies on", "uses"), and
    `names.py`'s docstring lead lists retired consumers.

  Refresh all to the spaced `novel <verb>` surface convention the swept suite now
  uses, so no legacy literal survives outside production module names. No
  behaviour or assertion changes; the existing suites stay green.
