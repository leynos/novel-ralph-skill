# novel-ralph harness roadmap

This roadmap translates the deterministic-spine design into an outcome-oriented
delivery sequence. It does not promise dates. Each phase carries one testable
idea at the GIST level: the steps underneath a phase work toward validating or
falsifying that idea, and the tasks are concrete, review-sized execution units.
The primary design document is `docs/novel-ralph-harness-design.md`; the
problem statement is `docs/terms-of-reference.md`. Architectural decisions are
recorded as ADRs in `docs/`, named `adr-NNN-short-description.md` per the
documentation style guide, as the foundational phase ratifies them.

The slices are ordered by the controlling decision in the design (§1): the
deterministic spine ships first as five installed, tested commands, then the
judgemental architecture (the device ledger, the configurable AI-isms packs,
the line editor, and the clean-context sub-agents) follows in the
deferred-extensions phase. Within the spine, `novel-state` leads because it
exercises the most architecture — the validated schema, the lossless TOML
round-trip, atomic writes, and disk-authoritative reconciliation — that every
later slice reuses.

## 1. Foundational contracts and command spine

Idea: if the rebuild settles its packaging boundary, its TOML round-trip
mechanism, and its shared command contract before any command is built, the
five slices can converge on one coherent v1 spine instead of each reworking the
envelope, the exit-code policy, and the serialisation strategy.

This phase produces no narrative-facing capability. It ratifies the
hard-to-reverse decisions the design names, stands up the console-script
packaging in `novel_ralph_skill`, and builds the shared contract scaffolding
and test corpus that the slices depend on.

### 1.1. Ratify the decisions that would otherwise force rework

This step answers which architectural choices are fixed before code lands. Its
outcome informs every command's interface and the serialisation all mutators
share. See novel-ralph-harness-design.md §1, §3, and §5.3.

- [x] 1.1.1. Record the deterministic-and-judgemental boundary as an ADR.
  - Capture the controlling rule: scripts detect and report; the model
    adjudicates. No command makes a narrative judgement.
  - See novel-ralph-harness-design.md §1.
  - Success: one accepted ADR states the boundary and the legal crossings,
    and is cited by every later slice.
- [x] 1.1.2. Record the TOML round-trip decision as an ADR.
  - Requires 1.1.1.
  - Select `tomlkit` over an owned comment-preserving serialiser, with the
    reasoning from the design.
  - See novel-ralph-harness-design.md §5.3.
  - Success: the ADR resolves open question Q1 and fixes the dependency every
    mutator builds on.
- [x] 1.1.3. Record the shared interface contract as an ADR.
  - Requires 1.1.1.
  - Fix the JSON envelope, the `--human` flag, the checker-and-mutator
    segregation, and the disambiguated exit-code table: 0 success, 1 benign
    negative (predicate not yet satisfied; the loop continues), 2 usage error,
    3 state or input error, 4 actionable finding requiring agent intervention
    (desloppify violations, compile divergence, reconciliation conflict).
  - Settle the structured-error shape: machine-actionable data lives in
    `result`; `messages` is human prose the harness never parses. Record the
    relation between the three `schema_version` fields (envelope, state, rule
    pack) and that they evolve independently.
  - See novel-ralph-harness-design.md §3.1, §3.2, and §3.3.
  - Success: the ADR resolves open question Q2; the five slices implement the
    same contract — including the code-1-versus-code-4 split — without
    renegotiating it.
- [x] 1.1.4. Record distribution as installed console-scripts as an ADR.
  - Requires 1.1.1.
  - Capture why the commands ship as console-scripts in `novel_ralph_skill`
    (terms-of-reference C3) rather than as self-contained `uv` scripts.
  - See novel-ralph-harness-design.md §2.2 and §4.
  - Success: an accepted ADR records the distribution decision and its
    rationale for future contributors.
- [x] 1.1.5. Record the command-surface shape as an ADR.
  - Requires 1.1.4.
  - Weigh five separate console-scripts against a single `novel` multiplexer,
    and record the decision to ship five named commands — each mapping 1:1 onto
    a deterministic operation, with the shared envelope enforced by the §1.3
    scaffolding rather than by a single entry point — together with the
    multiplexer trade-offs considered.
  - See novel-ralph-harness-design.md §4.
  - Success: the trade is recorded before 1.2.1 wires the entry points, so the
    five-script choice is deliberate rather than defaulted.

### 1.2. Stand up the console-script packaging boundary

This step answers whether the intended packaging — installed console-scripts in
the existing `novel_ralph_skill` package — supports local development and the
harness's invocation model. See novel-ralph-harness-design.md §2.2 and §4, and
docs/scripting-standards.md.

- [x] 1.2.1. Wire the five console-script entry points in `pyproject.toml`.
  - Requires 1.1.3 and 1.1.5.
  - Register `novel-state`, `novel-done`, `novel-compile`, `desloppify`, and
    `wordcount` against stub Cyclopts applications that exit 2 until
    implemented.
  - See novel-ralph-harness-design.md §4.
  - Success: a wheel build installs all five commands; each is invocable on
    `PATH` and reports a usage error rather than crashing.
- [x] 1.2.2. Add `tomlkit` to the package dependencies and confirm the build.
  - Requires 1.1.2 and 1.2.1.
  - Success: `make test` and the quality gates in AGENTS.md pass against the
    extended dependency set.
- [x] 1.2.3. Decide and enforce a cross-platform policy for the console-scripts
  e2e test.
  - Remediation (source: review:1.2.1; severity: low).
    `test_console_scripts_e2e.py`
    is only half-portable on Windows: the win32 branch resolves scripts via the
    `nt_user` sysconfig scheme (a roaming user path, not the venv `Scripts/` dir
    uv creates) and looks up `scripts_dir / command_name` without the `.exe`
    suffix, so either commit to Linux-only execution or make the lookup truly
    portable.
  - [x] 1.2.3.1. Index ADR 006 and the `docs/issues/` and `docs/execplans/`
    sets in `docs/contents.md`.
    - Addendum (from audit:1.2.6; severity: low). The documentation map omits
      the POSIX console-scripts ADR and the growing audit-trail and per-task
      plan sets, leaving them undiscoverable. Execute as a lightweight addendum
      pass against the 1.2.3 execplan: no plan or design-review cycle, just the
      change, the gates, and a merge.
- [x] 1.2.4. Introduce a single source of truth for the five command names.
  - Remediation (source: audit:1.2.1; severity: medium). The command-name list
    is
    duplicated across `stub.py`, `pyproject.toml`, and three test modules; a
    package registry consumed by the entry points and tests, asserted against
    `[project.scripts]`, removes the drift risk while the surface is still five
    thin stubs.
- [x] 1.2.5. Establish a docstring-coverage gate (interrogate) for the Python
  package.
  - Remediation (source: audit:1.2.1; severity: low). `interrogate` is a dev
    dependency with no configuration or Makefile/CI invocation, so docstring
    coverage is unenforced; locking the standard in now, while the modules are
    well documented, is cheapest before the command bodies expand the surface.
- [x] 1.2.6. Remove the dead `tomli_w` snippet from `state-layout.md` and
  reconcile the premature "is removed" claims.
  - Remediation (source: review:1.2.2; severity: medium). The failed `tomli_w`
    snippet still survives at `skill/novel-ralph/references/state-layout.md:229`
    and `:235`, yet ADR-002 line 77 and design §5.3 already assert it "is removed"
    while ADR-002 line 22 says it "even carries" it; delete the snippet (or
    rewrite it to `tomlkit`) and reconcile the ADR-002 and design wording, as no
    existing task owns this removal.
- [x] 1.2.7. Introduce `tests/conftest.py` to consolidate the shared test
  scaffolding.
  - Remediation (source: audit:1.2.6; severity: medium). The same project-root,
    `pyproject` parse, repo-file reader, single-program catalogue,
    `_venv_scripts_dir`, and TOML-table accessor are duplicated across the six
    test modules and re-flagged in audit-1.2.1, 1.2.3, 1.2.4, 1.2.5, and 1.2.6;
    a shared `conftest` removes the drift and cross-module private imports in one
    move while the surface is still small.
- [x] 1.2.8. Broaden the state-layout direct-edit guard to reject any
  hand-edit recipe, not just `tomli_w`.
  - Remediation (source: review:1.2.6; severity: low). The 1.2.6 guard pins only
    the literal `tomli_w` substrings, so a future `tomlkit`- or `tomllib`-based
    hand-edit of `state.toml` would pass green while re-opening the design §4.1
    "direct editing eliminated" violation; widen the guard to forbid any direct
    `state.toml`-write recipe, coordinated with task 6.2.3 which rewrites the
    reference prose to point at the `novel-state` commands.
  - [x] 1.2.8.1. Enforce a single code-fence style (MD048) in the markdownlint
    configuration.
    - Addendum (from review:1.2.8; severity: low). markdownlint accepts tilde
      fences, which made the guard bypass reachable; pinning backtick-only
      fences repo-wide is defence-in-depth. Lightweight addendum pass against
      the 1.2.8 execplan.
  - [x] 1.2.8.2. Split `tests/test_state_layout_reference.py` before it breaches
    the 400-line module cap.
    - Addendum (from review:1.2.8; severity: low). At 400 of 400 lines the next
      planted row or negative test breaks the AGENTS.md module-size gate;
      extract the recipe corpus or scanner helpers into a small support module
      (coordinate with the 1.2.7 shared conftest). Lightweight addendum pass.
  - [x] 1.2.8.3. Distinguish the live `state.toml` from its atomic `.new`
    sibling in the state-layout guard.
    - Addendum (from review:1.2.8; severity: medium). `_STATE_FILE` matches as a
      bare substring, so a fenced write-then-rename illustration (design §3.4,
      §5.3) is false-flagged because `state.toml` is a substring of
      `state.toml.new`; anchor the live-file match on a word, quote, or
      end-of-line boundary and add a negative test. Lightweight addendum pass.
  - [x] 1.2.8.4. Reconcile the developers' guide state-layout guard section with
    the merged 1.2.8 code.
    - Addendum (from audit:1.2.8; severity: medium). The guide's write-token
      list omits `.write_bytes`/`.writelines` and the executable info-string
      list omits `python3`/`py3`/`pycon`, all of which the code scans; a
      one-paragraph edit keeps the prose truthful. Lightweight addendum pass.
  - [x] 1.2.8.5. Sweep the residual hyphenated `novel-state` literals in
    `tests/test_state_layout_reference.py` to the `novel state` surface.
    - Addendum (from review:1.2.14; low). The module's docstrings and the
      negative-test fixture fence `novel-state set-cursor --chapter 7` still name
      the retired console-script; they sit outside the
      `skill/novel-ralph/references/` scope of 1.2.17 and the
      production-module-name scope of 1.2.14/1.2.16, so survive untracked. Flip
      each to the spaced `novel state` surface, preserving the negative test's
      intent. Lightweight addendum pass.
- [x] 1.2.9. Tighten the `read_repo_text` fixture signature from
  `Callable[..., str]` to a precise `(*parts: str) -> str` form.
  - Remediation (source: review:1.2.7; severity: low). The ellipsis in
    `cabc.Callable[..., str]` disables argument-count and type checking at every
    call site; a documented variadic callable signature restores the static
    arg-shape guarantee the plan's Interfaces section preferred without changing
    behaviour.
- [x] 1.2.10. Replace the bare `sh.make(...)` expression statement in
  `test_conftest_helpers` with an explicit assertion.
  - Remediation (source: review:1.2.7; severity: low). A statement that discards
    its result and asserts nothing reads as dead code and may be flagged by a
    linter; making the "does not raise" intent explicit keeps the test's
    guarantee self-evident to maintainers.
- [x] 1.2.11. Migrate `test_contract_test_deps` onto the shared conftest
  fixtures and centralise dependency-name normalisation.
  - Remediation (source: audit:1.2.7; severity: medium). The 1.2.7 consolidation
    left `test_contract_test_deps.py` re-parsing `pyproject` itself and carrying
    a second, weaker copy of the PEP 508 distribution-name normaliser; lifting a
    `dist_name` fixture into `conftest` and migrating the module onto the
    `pyproject`/`toml_table` fixtures removes both duplications in one move.
- [x] 1.2.12. Stand up the `novel` multiplexer dispatcher and entry point
  (ADR 007).
  - Requires 1.2.1 and 1.2.4.
  - Per `docs/adr-007-command-surface-novel-multiplexer.md` (superseding ADR
    005), add a single `novel` Cyclopts dispatcher that mounts the existing apps
    as a `state` subgroup plus four leaf verbs (`novel done`, `novel compile`,
    `novel desloppify`, `novel wordcount`), and register it as a `novel`
    `[project.scripts]` entry. Make the command-name single source of truth
    (`novel_ralph_skill/commands/names.py`) carry the new spaced subcommand
    names additively, and re-point the envelope command-name guard onto the
    superset. The five legacy `novel-x`/`desloppify`/`wordcount` entry points
    stay registered for now (removed in 1.2.13) so this task is independently
    landable. Add the multiplexer dispatch tests (unit + in-process behavioural
    over the corpus, exit-2/3/0 arms). Scope this task to the dispatcher only —
    do not migrate the e2e/contract suites or sweep the docs here.
  - See novel-ralph-harness-design.md §4 and adr-007-command-surface-novel-multiplexer.md.
  - Success: `novel state init`, `novel done`, `novel compile`,
    `novel desloppify`, and `novel wordcount` all dispatch correctly with the
    unchanged envelope and exit codes; the multiplexer tests pass; the five
    legacy entry points still work; and `make all` is green.
  - [x] 1.2.12.1. Guard `_command_name_for` against future multi-token global
    flags.
    - Addendum (from review:1.2.12; low). `_command_name_for` treats every
      dash-prefixed token as a value-less global flag, true only because
      `--human` is the lone global flag today; a later value-carrying global
      flag could have its value misread as the subcommand verb. Add a small
      guard or a comment pinning the single-value-less-flag assumption.
      Lightweight addendum pass.
  - [x] 1.2.12.2. Pin a bare unknown top-level verb arm (`novel bogus`) in the
    multiplexer behavioural suite.
    - Addendum (from review:1.2.12; low). The usage-fault suite covers sub-verb
      and option faults but not a leading unknown verb; the path works (stamps
      `novel`, exits 2) yet is unpinned, so a regression in `_command_name_for`
      or the parent's command routing could go uncaught. Lightweight addendum
      pass.
- [x] 1.2.13. Migrate the e2e and contract suites to invoke `novel <sub>`.
  - Requires 1.2.12.
  - Re-point the installed-binary e2e tests and the contract/command-name suites
    to invoke `novel <sub>` instead of the legacy console-scripts. This is an
    ADDITIVE migration: the five legacy `[project.scripts]` entries and the
    `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS` symbols stay in place (removed in
    1.2.15), so the legacy-vs-multiplexer parity tests still have their oracle
    and the change is low-risk and independently landable. Do not delete any
    entry point or registry symbol here.
  - See adr-007-command-surface-novel-multiplexer.md and AGENTS.md (testing).
  - Success: every e2e and contract test invokes `novel <sub>`; the legacy entry
    points and registry symbols are untouched and still pass; `make all`
    (including the installed-binary e2e) is green.
- [x] 1.2.15. Remove the legacy entry points and command-name registry symbols.
  - Requires 1.2.13.
  - Remove the five legacy `[project.scripts]` entries (`novel-state`,
    `novel-done`, `novel-compile`, `desloppify`, `wordcount`), the transitional
    legacy-name superset, and the now-dead `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`/
    `STUB_MODULE` symbols, so `novel` is the only entry point. Do the removal
    complete-by-construction: (1) first enumerate every consumer of those symbols
    with a grep that states the expected consumer set; (2) re-point each consumer
    AND drop the symbol from its import line in the same step, so no import line
    is left dangling; (3) gate the `names.py` deletion behind a grep that must
    return no match in `tests/` and `novel_ralph_skill/` before it runs — a
    leftover import would otherwise pass every earlier step and collapse `make
    all` at collection time only when the symbol is deleted. Rework the
    legacy-vs-multiplexer parity tests, which lose their legacy oracle here: the
    plan must specify the replacement concretely — either a reusable per-operation
    expectation (expected exit code AND envelope, modulo `command`, on the
    drafting corpus tree) or, if the envelope-equality coverage is consciously
    dropped, justify the reduced exit-code-and-command-name assertion in the
    execplan Decision Log. Make that judgement in the plan, not in the
    implementer.
  - See adr-007-command-surface-novel-multiplexer.md and AGENTS.md (testing).
  - Success: `uv tool install` puts exactly one command, `novel`, on `PATH`; no
    `novel-x`/`desloppify`/`wordcount` entry point and no `COMMAND_NAMES`/
    `COMMAND_ENTRY_POINTS` symbol remains; the parity coverage is preserved or its
    reduction is justified in the Decision Log; and `make all` (including the
    installed-binary e2e) is green.
  - [x] 1.2.15.1. Sweep the stale legacy command-name literals left in test and
    source prose after the surface retirement.
    - Addendum (from review:1.2.15 and audit:1.2.15; low; three near-identical
      proposals merged). After 1.2.15 retired the hyphenated surface and deleted
      `stub.py`, stale legacy-form names survive outside the
      production-module-name scope that tasks 1.2.14/1.2.16 cover:
      `tests/test_pyproject_scripts.py`'s registry-table docstring still says
      "the legacy five plus the novel multiplexer"; `tests/features/
      per_chapter_loop.feature` Gherkin step-text and the
      `tests/test_contract_app_centralisation.py` leaf labels still carry
      hyphenated `novel-x`/`desloppify`/`wordcount` names; and
      `novel_ralph_skill/commands/novel.py`'s docstrings/comments reference the
      now-deleted `stub.py` in the present tense. Refresh all to the
      spaced-surface convention the swept suite now uses. Lightweight addendum
      pass.
- [x] 1.2.14. Sweep the design document and `SKILL.md` to the `novel`
  multiplexer surface.
  - Step-task (source: audit:1.2.16; severity: high; promotes the orphaned
    roadmap block left headerless after the 1.2.15.1 edit). The 1.2.14 work was
    specified but never executed and its body was orphaned under 1.2.15.1 with no
    checkbox, so the build workflow could not track it; 44 references in
    `docs/novel-ralph-harness-design.md` and 23 in `SKILL.md` still name retired
    hyphenated console-scripts, and the `SKILL.md` Setup section verifies the
    install with the non-existent `novel-state --version`. This serves the
    step-1.2 hypothesis — whether the installed console-scripts packaging
    supports the harness's invocation model — by making the design and skill
    documentation describe the single `novel` surface the packaging now ships,
    not the retired per-command scripts.
  - Requires 1.2.15.
  - Update the design prose and diagrams and `SKILL.md` (including the Setup
    section and every bare `novel-x` reference) from the `novel-x` form to the
    `novel x` form, so no documentation describes the retired separate scripts.
    Replace the `novel-state --version` install check with a command that exists
    on the single `novel` surface.
  - See novel-ralph-harness-design.md §4 and adr-007-command-surface-novel-multiplexer.md.
  - Success: no `novel-state`/`novel-done`/`novel-compile`/`desloppify`/
    `wordcount` console-script reference survives in the design or `SKILL.md`,
    the Setup install check names a command that exists, and `make markdownlint`
    and `make nixie` pass on the edited docs.
- [x] 1.2.17. Extend the multiplexer-surface doc sweep to
  `skill/novel-ralph/references/`.
  - Step-task (source: audit:1.2.16; severity: medium). The reference files
    (`state-layout.md`, `done-conditions.md`, `critic-personas.md`) invoke
    retired commands directly but fall outside every existing success criterion
    (1.2.14 covers the design document and `SKILL.md` only; 1.2.16 covers the two
    guides only), so the retired surface survives there untracked. This serves
    the step-1.2 hypothesis — whether the installed console-scripts packaging
    supports the harness's invocation model — by making the reference
    documentation describe the single `novel` surface the packaging ships.
  - Requires 1.2.14 and 1.2.16.
  - Sweep `skill/novel-ralph/references/state-layout.md`, `done-conditions.md`,
    and `critic-personas.md` to the `novel <sub>` surface. Distinguish retired
    command invocations (e.g. `novel-state init`, which must flip to `novel state
    init`) from the noun-form `desloppify` pass, which names the desloppification
    operation rather than the retired console-script and stays; name that
    distinction explicitly so the noun form is not mis-swept.
  - See novel-ralph-harness-design.md §4 and adr-007-command-surface-novel-multiplexer.md.
  - Success: no `novel-state`/`novel-done`/`novel-compile` console-script
    invocation and no retired `desloppify`/`wordcount` console-script reference
    survives in the three reference files, the noun-form `desloppify` pass is
    preserved where it names the operation rather than the retired script, and
    `make markdownlint` and `make nixie` pass on the edited references.
  - [x] 1.2.17.1. Sweep the residual flag-bearing `desloppify --pack`/`--ledger`
    console-script invocations in `desloppify-checklist.md` to the
    `novel desloppify` surface.
    - Addendum (from review:1.2.17 and audit:1.2.17; medium; two near-identical
      proposals merged). `skill/novel-ralph/references/desloppify-checklist.md`
      (around lines 294 and 302) still presents `desloppify --pack …` and
      `desloppify --ledger …` as runnable flag-bearing invocations of the retired
      console-script; this sibling reference file sits outside 1.2.17's
      three-file success criterion, so the retired surface survives untracked.
      Flip the two flag-bearing invocations to `novel desloppify --pack …` /
      `novel desloppify --ledger …` while preserving every noun-form `desloppify`
      mention that names the operation. Lightweight addendum pass.
- [x] 1.2.16. Sweep the users' and developers' guides to the `novel` multiplexer
  surface.
  - Remediation (source: audit:1.2.13; severity: medium). Task 1.2.14's wording
    and success criterion cover only the design document and `SKILL.md`, leaving
    `docs/users-guide.md` (which still presents the legacy five console-scripts
    as the user-facing surface, with zero references to the `novel` multiplexer)
    and
    `docs/developers-guide.md` untracked; this sibling task closes that gap so no
    guide describes the retired separate scripts. Gated behind 1.2.15 so the prose
    flips once the legacy scripts are actually retired. This serves the step-1.2
    hypothesis — whether the installed console-scripts packaging supports the
    harness's invocation model — by making the user- and developer-facing
    documentation describe the single `novel` surface that the packaging ships,
    rather than the retired per-command scripts.
  - Requires 1.2.15.
  - This is a completeness-driven sweep, not an enumerated set of line repairs:
    rewrite both guides for accuracy against the post-removal single-`novel`
    surface. Beyond the command-name literals, reconcile any prose that still
    treats the retired separate scripts as present — e.g. present-tense claims
    like "the legacy scripts produce …" or additive-transition language such as
    "stands up the multiplexer additively" — to describe the current state. The
    implementer sweeps and reconciles the relevant sections (including the
    developers' guide multiplexer subsection) for truthfulness; do not restrict
    the change to a pre-enumerated repair list.
  - See novel-ralph-harness-design.md §4 and
    adr-007-command-surface-novel-multiplexer.md.
  - Success: no `novel-state`/`novel-done`/`novel-compile`/`desloppify`/
    `wordcount` console-script reference survives in `docs/users-guide.md` or
    `docs/developers-guide.md`, AND no prose in either guide describes the
    retired separate scripts as present (no present-tense or additive-transition
    reference to them remains); each guide reads truthfully against the single
    `novel <sub>` surface; `make markdownlint` and `make nixie` pass.

### 1.3. Build the shared contract scaffolding and test corpus

This step answers whether one envelope, output-mode switch, and exit-code
helper can serve all five commands. Its outcome removes per-command contract
drift and seeds the snapshot suite. See novel-ralph-harness-design.md §3 and §9.

- [x] 1.3.1. Implement the shared JSON-envelope and output-mode module.
  - Requires 1.1.3 and 1.2.1.
  - Provide the `command`, `schema_version`, `ok`, `working_dir`, `result`,
    and `messages` envelope, the `--human` rendering hook, and the exit-code
    mapping (0/1/2/3/4) as reusable helpers, with `result` carrying all
    machine-actionable data and `messages` carrying only human prose.
  - See novel-ralph-harness-design.md §3.1 and §3.2.
  - Success: a property-based test confirms `ok` is true only on exit 0; that
    each of the four non-zero codes is reported as `ok: false`; and that all
    five codes (0 success, 1 benign negative, 2 usage error, 3 state or input
    error, 4 actionable finding) map to the expected envelope semantics — a
    malformed invocation yields code 2, an unparseable or missing `state.toml`
    yields code 3, and codes 1 and 4 carry distinct, non-interchangeable
    meanings. A snapshot pins the envelope shape for each code.
  - [x] 1.3.1.1. Extract a shared wrapper-app builder fixture for the contract
    run-driver tests and fold the residual conftest table accessors.
    - Addendum (from audit:1.2.8; severity: low). The four-flag Cyclopts
      `_build_app` is duplicated across `test_contract_runner` and
      `test_contract_properties`, and `_parse_scripts` duplicates an inline
      `toml_table` access; a `wrapper_app` fixture plus a `project_scripts`
      walker in `conftest` makes both live once. Lightweight addendum pass
      against the 1.3.1 execplan.
  - [x] 1.3.1.2. Audit and document the `contract`→`commands.names` import edge.
    - Addendum (from review:1.3.6; severity: low). `contract/envelope.py` and
      `tests/conftest.py` both import `COMMAND_NAMES` from
      `novel_ralph_skill.commands.names`, crossing the `contract`→`commands`
      layering boundary; the edge is benign because `names.py` is a leaf
      source-of-truth module, but a short ADR-003 or developers'-guide note
      recording the shared registry as a leaf both layers may depend on makes the
      dependency direction deliberate. Lightweight addendum pass against the
      1.3.1 execplan.
- [x] 1.3.2. Build the on-disk `working/` fixture corpus.
  - Requires 1.2.1.
  - Provide reusable `tmp_path` fixtures spanning all eleven phase states,
    coherent and deliberately incoherent `state.toml` variants, and chapter
    drafts with `done.flag` permutations.
  - See novel-ralph-harness-design.md §5 and §9.
  - Success: the corpus is consumed unchanged by the slice suites in
    phases 2-6, so no slice re-rolls fixtures.
  - [x] 1.3.2.1. Disambiguate the three consecutive-clean sub-rules in the
    corpus oracle vocabulary.
    - Addendum (from audit:1.3.2; severity: low). Design §5.2 invariant 4
      bundles three sub-rules the oracle collapses onto the single
      `consecutive-clean-bound` name, so the set-equality self-test cannot tell
      the three targeting variants apart and two sub-rules could silently stop
      being exercised. Lightweight addendum pass.
  - [x] 1.3.2.2. Model a `done.flag` beside an absent `draft.md` in the corpus
    builder.
    - Addendum (from review:1.3.2; severity: low). The builder always writes
      `draft.md`, so the design §5.4 absent-draft contradiction has no fixture;
      add a `done-flag-absent-draft` variant keyed on `done-flag-without-draft`
      for the 2.3.2 check/reconcile consumer. Lightweight addendum pass.
- [x] 1.3.3. Hoist `parse_global_flags` and `_HUMAN_FLAG` into a shared seam
  before the second command imports them cross-command.
  - Reroute (source: audit:2.1.2; severity: low). `parse_global_flags` is a
    command-agnostic `--human` splitter (ADR-003 §3.1) currently living in the
    `novel_state` command module, so the four later commands would otherwise
    import it from a sibling or re-implement it. This advances the step-1.3
    hypothesis — one envelope, output-mode switch, and exit-code helper serving
    all five commands — by giving the splitter a neutral home before the import
    direction sets, rather than the 2.1 schema hypothesis where it was raised.
  - Requires 1.3.1.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md.
  - Success: `parse_global_flags` and `_HUMAN_FLAG` live in a shared seam (e.g.
    `contract.runner` or `commands/_global_flags.py`), every command imports the
    one splitter, and no command depends on a sibling command module.
- [x] 1.3.4. Extract a shared envelope-`messages`-carrying exception base for
      the
  domain error types.
  - Reroute (source: audit:5.1.1; severity: medium). `StateInputError`,
    `RulePackError`, and `RulePackFileError` hand-repeat the same
    `messages`-carrying `__init__` across the `contract` and `rulepack` layers,
    so a future change to the envelope-messages contract must be mirrored across
    three sites. This serves the step-1.3 shared-contract-scaffolding
    hypothesis — one envelope contract for every command — not the 5.1 rule-pack
    hypothesis where it surfaced. The cross-layer direction holds: `rulepack` may
    depend on a `contract` base, never the reverse.
  - Requires 1.3.1.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md.
  - Success: a single `EnvelopeMessagesError` base in a neutral `contract`
    module
    records `self.messages: tuple[str, ...]` once; the three domain exceptions
    subclass it (`RulePackError` adding `rule_id`), and the freeze-on-construct
    decision has one home.
- [x] 1.3.5. Settle a deliberate mutator success-result vocabulary, distinct
  from `check`'s `violations` shape.
  - Reroute (source: audit:2.2.2; severity: medium). The `set-cursor` and
    `advance-phase` mutators echo the checker's `result={"violations": []}`
    shape on a successful write, borrowing a query's vocabulary for a command
    and disagreeing with `init`'s own write result (`{"working_dir", "slug"}`),
    so an agent cannot tell a checker envelope from a mutator one by `result`
    alone. This serves the step-1.3 hypothesis — one envelope contract serving
    all five commands without per-command result drift — by fixing the
    write-result shape before `recount` and `reconcile` copy the checker's
    vocabulary too; it does not serve the step-2.2 write-discipline hypothesis
    where it was raised. Settle a write-shaped `result` for mutators (e.g.
    `set-cursor` returns the cursor it set, `advance-phase` returns the
    transition) and reserve `violations` for the `check` query, recording the
    contract in the design or developers' guide so later mutators inherit it.
  - Requires 1.3.1.
  - See novel-ralph-harness-design.md §3.1, §3.2, and §5.4;
    docs/adr-003-shared-interface-contract.md; docs/issues/audit-2.2.2.md
    (Finding 2).
  - Success: the `novel-state` write mutators return a write-shaped `result`
    that names what they changed rather than an empty `violations` echo, the
    `violations` key is reserved for `check`, and the mutator result contract is
    recorded once for `recount`/`reconcile` to follow.
  - [x] 1.3.5.1. Record set-cursor's input-echo result coupling as a deliberate
    choice.
    - Addendum (from review:1.3.5; low). `set-cursor` echoes its input args as
      the success `result`; they equal the persisted scalars today, so note the
      coupling as a deliberate choice (rather than re-reading the written
      document) in the design or developers' guide so it is not a latent
      assumption. Lightweight addendum pass.
  - [x] 1.3.5.2. Assert advance-phase's `from`/`to` are transition labels, not
    `state.toml` schema keys.
    - Addendum (from audit:1.3.5; low). Add an on-disk behavioural test that
      re-reads the written `state.toml` to assert `phase.current`/`phase.completed`
      updated and no `from`/`to` keys were persisted, closing the prose-only gap
      between the docstring intent and the test surface. Lightweight addendum
      pass.
- [x] 1.3.6. Add a shared contract-app factory for the runner's required
  four-flag `cyclopts.App`.
  - Reroute (source: audit:3.1.1; severity: low). The runner's hard requirement
    (`result_action='return_value'`, `exit_on_error=False`, `print_error=False`,
    `help_on_error=False`) is re-spelled in four `build_app()` constructors and
    validated only at runtime, and the four `stub.py` entry-point bodies copy the
    `parse_global_flags`/`run` plumbing. This serves the step-1.3 hypothesis —
    one envelope, output-mode switch, and exit-code helper serving all five
    commands — by co-locating the four-flag contract with the runner that
    enforces it, rather than the step-3.1 done-predicate hypothesis where it
    surfaced. Add a `make_contract_app(name)` factory (plus an optional `_drive`
    helper) and route every command's app construction and entry-point body
    through it.
  - Requires 1.3.1.
  - See novel-ralph-harness-design.md §3.1 and §4;
    docs/adr-003-shared-interface-contract.md;
    docs/issues/audit-3.1.1.md (Finding 5).
  - Success: a single `make_contract_app(name)` factory owns the four-flag
    contract, the four `build_app()` constructors and the `stub.py` entry-point
    bodies consume it rather than re-spelling the flags and the
    `parse_global_flags`/`run` plumbing, and the contract-runner and command
    suites stay green.
  - [x] 1.3.6.1. Add a structural tripwire pinning that the four `build_app()`
    constructors and the four real entry points consume the centralisation.
    - Addendum (from review:1.3.6 and audit:1.3.6 Finding 3; severity: medium).
      The proof that `make_contract_app`/`_drive` are on the path is only
      indirect today (console-scripts e2e plus per-command suites), so a future
      edit re-inlining a bare `cyclopts.App` in one `build_app()` or the
      `parse_global_flags`/`run` plumbing in one entry point would still pass
      every suite; add a parametrized in-process test asserting each of the four
      production `build_app` apps carries the four-flag contract and each real
      entry point routes through `_drive`/`make_contract_app`. Lightweight
      addendum pass against the 1.3.6 execplan.
  - [x] 1.3.6.2. Document the four-flag cyclopts contract and `make_contract_app`
    in ADR-003 and the developers' guide.
    - Addendum (from audit:1.3.6 Findings 1 and 6; severity: low). The four-flag
      requirement is now load-bearing contract machinery with a dedicated factory
      but is undocumented in prose (the `runner.py` docstring notes the flags
      "are not documented there"); record in ADR-003 the requirement, the
      per-flag rationale, and that `make_contract_app` is its single enforcement
      point so a future sixth command calls the factory, and add the matching
      developers'-guide note. Lightweight addendum pass against the 1.3.6
      execplan.

## 2. Vertical slice 1: trustworthy state through validated mutators

Idea: if all state mutation hides behind validated subcommands that refuse to
write an incoherent `state.toml` and can reconstruct state from disk, the
silent phase drift and hand-typed counts in the field report become impossible,
and every later slice can trust the schema as the single source of truth.

This slice delivers `novel-state` end-to-end: the validated schema, the five
subcommands, the lossless TOML round-trip, atomic writes, and
disk-authoritative reconciliation. It is sequenced first because its artefacts
— the schema, the validator, and the round-trip — underpin `novel-done`,
`novel-compile`, and `wordcount`.

### 2.1. Establish the validated schema and its invariants

This step answers whether the `state.toml` schema can be expressed as a typed
structure whose invariants a validator enforces. Its outcome is the single
source of truth the done predicate and the recount logic read. See
novel-ralph-harness-design.md §5.1 and §5.2.

- [x] 2.1.1. Implement the typed `state.toml` schema and the phase enum.
  - Requires steps 1.1-1.3.
  - Model the schema from `state-layout.md` with the dead per-chapter
    `plan.md` reference removed, encode the eleven-member phase enum in order,
    and add the three new fields: the `[chapters]` manifest (number, slug,
    title, target words), `[drafting.critic].convergence_target`, and the
    `[pending_turn]` intent record. Anchor all manuscript paths under
    `working/manuscript/`.
  - See novel-ralph-harness-design.md §5.1 and §8.
  - Success: representative states from the §1.3.2 corpus parse into the typed
    structure without loss, including the manifest and the pending-turn record.
- [x] 2.1.2. Implement the invariant validator behind `novel-state check`.
  - Requires 2.1.1.
  - Enforce phase membership, the completed-prefix ordering, the
    by-chapter-sum-to-current rule, cursor coherence, and
    gate-boolean-versus-ratio consistency. Bound `consecutive_clean` by the
    configured `convergence_target` ceiling (default 1, rejecting a target
    below 1) rather than a hard-coded 0–1 literal, so the convergence bar is a
    state-field change.
  - See novel-ralph-harness-design.md §5.2 and §2.3.
  - Success: a `hypothesis` suite over generated states shows `check` accepts
    exactly the states satisfying §5.2 and rejects the rest (the
    state-coherence property), and a state with `consecutive_clean` above its
    `convergence_target` is rejected while one within a raised target is
    accepted.
  - [x] 2.1.2.1. Make `validate._GATE_THRESHOLDS` the single source of truth for
    the `(0.30, 0.50, 0.80)` gate triple.
    - Addendum (from audit:2.1.2; medium). Import the production constant into
      the property suite and pin the corpus `_specs.GATE_THRESHOLDS` to it with
      a one-line test, so neither cross-check can drift from the validator.
      Lightweight addendum pass.
  - [x] 2.1.2.2. Add reciprocal twin cross-references between the validator
    predicates and the corpus oracle.
    - Addendum (from audit:2.1.2; low). Add the reverse pointer in `_oracle.py`
      naming the agreement suite that pins the deliberate-twin equivalence, and
      record the twin policy once in the developers' guide. Lightweight addendum
      pass.
  - [x] 2.1.2.3. Add a named in-memory unit test that `_check_phase_in_enum`
    fires for a directly-constructed out-of-enum `State`.
    - Addendum (from audit:2.1.2; low). The disk path enforces the phase enum in
      the parser, leaving the validator's safety-net layer exercised only
      indirectly; a paired in-memory test makes the two-layer design
      self-documenting. Lightweight addendum pass.
  - [x] 2.1.2.4. Extract a `_load_or_state_error` helper and a named
    state-input exception-tuple constant in `novel_state`.
    - Addendum (from audit:2.1.2; low). Lift the load-and-translate step and the
      exit-3 exception set out of `_check` so it reads as load → validate → build
      outcome, and have the corpus test reference the shared constant.
      Lightweight addendum pass.
  - [x] 2.1.2.5. Collapse the two `_check` `CommandOutcome` branches into one
    verdict-driven constructor.
    - Addendum (from audit:2.1.2; low). Compute the verdict once and build a
      single outcome whose code is `SUCCESS` on an empty verdict else
      `ACTIONABLE_FINDING`, removing the parallel result/messages plumbing.
      Lightweight addendum pass.
  - [x] 2.1.2.6. Document the design-invariant-number to owned-name mapping for
    the validator.
    - Addendum (from audit:2.1.2; low). Add a compact §5.2-invariant-number to
      owned-name(s)/deferred table to the validator docstring or the developers'
      guide so the eight-names-versus-seven-invariants relationship is checkable
      at a glance. Lightweight addendum pass.
  - [x] 2.1.2.7. Enumerate the eight `result.violations` invariant names in the
    users' guide.
    - Addendum (from audit:2.1.2; low). Add a name-to-plain-English reference
      list to the `novel-state check` section, noting the set is the pure-state
      half and disk-evidence invariants arrive later. Lightweight addendum pass.
  - [x] 2.1.2.8. Pin each predicate's `Violation.detail` prose with a focused
    test.
    - Addendum (from audit:2.1.2; low). Assert that each invariant's `detail` is
      non-empty and mentions the offending values for a known breach, bringing
      the human-facing message channel under the same coverage as the machine
      name. Lightweight addendum pass.
  - [x] 2.1.2.9. Render `Phase` members as kebab strings in the validator's
    operator-facing `Violation.detail` messages.
    - Addendum (from review:2.2.2; low). The `phase-in-enum` and
      `completed-prefix` details repr `Phase` members
      (`<Phase.PREMISE: 'premise'>`) rather than the kebab `.value` an operator
      reads in `state.toml`, and this leaks into every advance-phase and
      set-cursor refusal envelope; format members via `.value` so the detail
      matches the on-disk vocabulary. Lightweight addendum pass.
- [x] 2.1.3. Assert the §5.2 validator agrees with the corpus oracle on every
  fixture, keyed on `CORPUS_INVARIANT_NAMES`.
  - Reroute (source: review:1.3.2; severity: high). The §1.3.2 corpus exposes a
    stable invariant-name vocabulary (`CORPUS_INVARIANT_NAMES`) precisely so the
    canonical validator can be cross-checked against it; making this an explicit
    acceptance clause closes the documented oracle-drift risk (1.3.2 execplan
    Risks; advisory A5). Cross-check the verdict computed from each fixture's
    materialised on-disk `state.toml` (not from the spec), so a spec-versus-disk
    mislabel — the kind the by-chapter-sum fix-round-1 surfaced — is caught and
    the validator and oracle cannot drift on the disk-derived quantities
    (invariants 3 and 7).
  - Requires 2.1.2.
  - See novel-ralph-harness-design.md §5.2 and §9;
    docs/execplans/roadmap-1-3-2.md (advisory A5, the fix-round-1 on-disk
    decision).
  - Success: for every §1.3.2 corpus fixture the §5.2 validator's verdict, run
    against the materialised `state.toml`, matches the oracle's
    `CORPUS_INVARIANT_NAMES` labels exactly — coherent trees pass and each
    incoherent variant is rejected on its one named invariant.
  - [x] 2.1.3.1. Consolidate the live-draft oracle's repeated `state.toml`
    parsing and drop the third `by-chapter-sum` predicate twin.
    - Addendum (from audit:2.1.3; medium). The three `_check_*_live` predicates
      in `tests/working_corpus/_live_draft.py` each re-parse `state.toml`; parse
      it once in `live_draft_owned` and pass the decoded tables in, and drop
      `_check_by_chapter_sum_live` in favour of the `by-chapter-sum` verdict
      `corpus_check` already returns. Test-only cleanup of redundant reads and a
      hand-copied table twin. Lightweight addendum pass.
  - [x] 2.1.3.2. Lift the shared disk-evidence invariant-name set into one home
    for both agreement suites.
    - Addendum (from audit:2.1.3; medium). `_DISK_EVIDENCE_NAMES` and
      `_DEFERRED_INVARIANT_NAMES` are identical five-element frozensets
      hard-coded in two test modules with nothing pinning them equal; derive the
      set once in `tests/_state_corpus_support.py` (ideally as
      `set(CORPUS_INVARIANT_NAMES) - set(PURE_STATE_INVARIANT_NAMES)`) and import
      it into both. Test-only. Lightweight addendum pass.
  - [x] 2.1.3.3. Promote the §5.2 gate thresholds to a public exported constant.
    - Addendum (from audit:2.1.3; low). Two test modules import the private
      `_GATE_THRESHOLDS` across the package boundary; export `GATE_THRESHOLDS`
      from `novel_ralph_skill.state` alongside the invariant-name constants and
      update the imports, removing the cross-module-private-import smell prior
      audits repeatedly lifted. Lightweight addendum pass.
- [x] 2.1.4. Complete the corpus's invariant-6 coverage for the scene/beat
  cursor sub-clauses.
  - Reroute (source: audit:1.3.2 / review:1.3.2; severity: medium). The §1.3.2
    corpus exercises only the `current_chapter`-out-of-range clause of design
    §5.2 invariant 6; the `current_scene`/`current_beat`-zero-until-plans-exist
    and scene/beat-versus-`current_chapter` sub-clauses have no negative
    fixture, so a validator mishandling them would pass against the corpus
    undetected. Add the missing negative fixtures and extend the oracle's
    `cursor-coherent` branch (or split it) so all three sub-clauses are
    exercised; where the "zero until plans exist" clause needs scene/beat plans
    to have on-disk representation, scope the fixture to that representation.
  - Reroute (source: review:2.1.4; severity: medium). The "zero until plans
    exist" sub-clause is disk-evidence: deciding it requires reading whether
    `scenes.md`/`beats.md` exist on disk for the current chapter. The §5.2
    validator is disk-blind by construction — task 2.1.2 locked it to the
    state-only part of `cursor-coherent` and deferred every disk-evidence
    invariant to reconciliation task 2.3.2 — so the original Success clause's
    "the validator rejects" wording cannot be honoured for that sub-clause
    without breaching the locked boundary. The Success clause below is therefore
    amended: the disk-evidence "zero until plans exist" fixture is rejected by
    the corpus oracle on a new disk-evidence cursor name (`cursor-plan-present`),
    with validator rejection of that sub-clause deferred to task 2.3.2; the
    pure-state scene/beat-past-`current_chapter` fixture is rejected by both the
    corpus oracle and the validator on `cursor-coherent`.
  - Requires 2.1.2.
  - See novel-ralph-harness-design.md §5.2 (invariant 6).
  - Success: a non-zero `current_scene`/`current_beat` before its plan exists is
    a negative fixture the corpus oracle rejects on the disk-evidence
    `cursor-plan-present` name, with validator rejection deferred to task 2.3.2;
    a scene/beat cursor referencing a chapter past `current_chapter` is a
    negative fixture both the corpus oracle and the §5.2 validator reject on the
    pure-state `cursor-coherent` name.
- [x] 2.1.5. Promote a `by_chapter_override` table-versus-draft divergence
  variant into the §1.3.2 shared corpus so the whole-corpus agreement loop is
  discriminating.
  - Reroute (source: review:2.1.3 / audit:2.1.3; severity: medium). The 2.1.3
    live-draft cross-check proves the validator enforces invariants 4c and 7
    against a source genuinely independent of the `[word_counts]` table, but no
    §1.3.2 corpus tree sets `by_chapter_override`, so on every current corpus
    tree the table and the on-disk drafts are numerically equal and the
    whole-corpus agreement test alone cannot discriminate a live read from a
    table read. The 2.1.3 fix-round-1 had to construct a one-off module-local
    `divergent_table_tree` fixture to close that, and a surviving mutant
    (live reader to table reader) confirmed the gap. This serves the step-2.1
    hypothesis — that the schema's invariants can be expressed as a typed
    structure a validator enforces — by making the validator-versus-live-oracle
    cross-check discriminating from first-class corpus data and by exercising
    the validator's two table-based proxies (`gate-ratio-consistent`,
    `consecutive-clean-within-drafted`) against a genuinely divergent tree,
    rather than resting the discrimination on a bespoke per-test fixture. It is
    substantial because it adds corpus data under step-1.3.2 ownership
    (`tests/working_corpus/_variants.py` and the oracle vocabulary) and must
    keep the existing spec-keyed `corpus_check`, `CORPUS_INVARIANT_NAMES`, and
    every current agreement suite green, which warrants its own plan and review.
    Add a first-class corpus variant (positive `draft.md` bodies with a
    `by_chapter_override` that under-counts or omits a drafted chapter so the
    table mislabels the real drafts) owned by the §1.3.2 corpus, and retire the
    module-local `divergent_table_tree` fixture in favour of it.
  - Requires 2.1.3.
  - See novel-ralph-harness-design.md §5.2 and §9;
    docs/execplans/roadmap-2-1-3.md (Fix round 1, the divergent-table tree);
    docs/execplans/roadmap-1-3-2.md (the corpus-ownership constraints).
  - Success: a first-class §1.3.2 corpus variant sets `by_chapter_override` so
    the table's `by_chapter` diverges from the on-disk drafts; the whole-corpus
    live-draft agreement test discriminates the live read from a table read
    directly through the standard corpus loop (the live reader to table reader
    mutant is killed without the module-local fixture); and the module-local
    `divergent_table_tree` fixture is removed.
  - [x] 2.1.5.1. Extract the divergent-table self-tests into a focused sibling
    test module.
    - Addendum (from review:2.1.5; low). `tests/test_working_corpus.py` is 599
      lines under an inline `too-many-lines` exemption and the 2.1.5 execplan
      named extraction as the sanctioned escalation path; lift the
      divergent-table self-test class into a focused sibling module so the
      exemption can be relieved before the next variant lands. Lightweight
      addendum pass.
  - [x] 2.1.5.2. De-future the live-draft oracle docstring's
    `by_chapter_override` landmine framing.
    - Addendum (from review:2.1.5; low). `live_draft_owned`'s docstring in
      `tests/working_corpus/_live_draft.py` still frames the
      `by_chapter_override` variant as a "future" landmine, but 2.1.5 landed
      that variant; reword the stale "future" framing so the documentation trail
      describes the variant that now exists. Lightweight addendum pass.
  - [x] 2.1.5.3. Make the divergent-table consumer iterate rather than
    single-unpack the variant set.
    - Addendum (from review:2.1.5; low). `test_validate_state_live_draft.py`
      hard-codes `(variant_name,) = divergent_table_variant_names`, so the second
      variant will break it with an opaque unpacking error; iterate the variant
      set (or pin an explicit single variant) to localise that future failure.
      Lightweight addendum pass.
- [x] 2.1.6. Add a symmetric under-counting divergent-table corpus variant so the
  discrimination loop catches a mutant that mishandles only over-counts.
  - The §1.3.2 corpus now owns a single over-counting `by_chapter_override`
    divergent-table tree. Add a first-class sibling variant whose
    `by_chapter_override` under-counts or omits a drafted chapter, so the table
    mislabels the real drafts in the opposite direction; the
    `DIVERGENT_TABLE_VARIANTS` category and `divergent_table_tree` factory accept
    this by name. This serves the step-2.1 hypothesis — that the schema's
    invariants can be expressed as a typed structure a validator enforces — by
    exercising the validator's two table-based proxies
    (`gate-ratio-consistent`, `consecutive-clean-within-drafted`) against a
    genuinely divergent tree in the opposite direction, hardening the
    validator-versus-live-oracle cross-check against a mutant that only
    mishandles over-counts.
  - Requires 2.1.5.
  - See novel-ralph-harness-design.md §5.2 and §9;
    docs/execplans/roadmap-2-1-5.md (the over-counting variant and its corpus
    ownership constraints).
  - Success: a first-class §1.3.2 corpus variant sets `by_chapter_override` so
    the table under-counts or omits a drafted chapter; the whole-corpus
    live-draft agreement test discriminates the live read from a table read on
    this tree too; and a table-reading mutant of the live oracle that mishandles
    only over-counts is killed by the under-counting variant.
- [x] 2.1.7. Relax the manifest-disk bijection during drafting.
  - Requires 2.1.2 and 2.2.3.
  - §5.2 invariant 5 requires an exact `[chapters]`-manifest-to-disk bijection,
    but during drafting the manifest holds every planned chapter while only the
    drafted-so-far `chapter-NN/` directories exist, so `novel-state check` fails
    `manifest-disk-bijection` (exit 4) for the whole drafting phase — beta
    testing found `check` unusable mid-draft. Record an ADR and implement: while
    `phase.current == drafting`, relax to disk-subset-of-manifest (every on-disk
    chapter maps to a manifest entry, but not every manifest entry needs a
    directory yet), tightening back to exact bijection at final-pass and done.
  - See novel-ralph-harness-design.md §5.2 and §5.4.
  - Success: `check` passes mid-draft when the on-disk chapters are a subset of
    the manifest, still flags an on-disk chapter absent from the manifest, and
    enforces exact bijection at done — proven by tests.
  - [x] 2.1.7.1. Extract a shared manifest-disk bijection classifier and name the
    broken direction in the violation detail.
    - Addendum (from audit:2.1.7 Findings 1 and 2; low). The
      orphans/missing/contiguous/coherent-subset classification is computed inline
      in both production sites (`disk_evidence._check_manifest_disk_bijection` and
      `reconcile._set_chapters_turn_explains_bijection`), with the contiguity-from-1
      literal byte-identical, and the predicate discards the direction it just
      classified when building the `Violation`; extract a pure
      `_classify_bijection` helper consumed by both production sites (the corpus
      oracle twin staying a deliberate independent reimplementation, with a
      mirror comment) and add a `describe()`-driven directional detail. Pure
      refactor, no behavioural change. Lightweight addendum pass.
  - [x] 2.1.7.2. Extend the relaxed corpus agreement suite to a missing-directory
    subset at final-pass and done.
    - Addendum (from review:2.1.7; low). The relaxed production-vs-oracle
      agreement is asserted against coherent exact-bijection trees at the terminal
      phases, not against a subset that must fire there; add a terminal-phase
      subset agreement row so the last untested corner of the relaxed twin
      lock-step is closed. Lightweight addendum pass.
- [x] 2.1.8. Reconcile state-layout.md with the emitted state schema.
  - Requires 2.1.1.
  - `novel-state init` emits `chapters = []` (top-level) and
    `[drafting.critic].convergence_target`, both absent from
    `skill/novel-ralph/references/state-layout.md` (schema drift found in beta
    testing). Document both in the reference so it matches the shipped schema,
    and add a guard test that fails if the emitted schema drifts from the
    reference again.
  - See novel-ralph-harness-design.md §5.1.
  - Success: `state-layout.md` documents `chapters` and `convergence_target`, and
    a test pins the reference against what `init` emits.
  - [x] 2.1.8.1. Document `[pending_turn]` in `state-layout.md` to fully
    reconcile the reference with design §5.1.
    - Addendum (from review:2.1.8; low). Design §5.1 names three fields added
      beyond the reference structure (`[chapters]`, `convergence_target`, and
      `[pending_turn]`); 2.1.8 documented the first two because `init` emits
      them, leaving `[pending_turn]` — the transient mid-mutation intent record
      (§3.4) — undocumented in the authoritative on-disk reference. Document the
      `[pending_turn]` intent record so the reference mirrors the transient
      on-disk shape, not only the `init` shape; the emitted-drift guard cannot
      cover it because `init` never emits it. Lightweight addendum pass.
  - [x] 2.1.8.2. Reconcile the initial `[drafting.critic].pass` seed with its
    documented "no pass run yet" semantics and pin the initial critic sub-state.
    - Addendum (from audit:2.1.8, Findings 1 and 2; low). `init` emits
      `pass = 1` while `state-layout.md` documents `0` as "no pass run yet" — a
      schema-vs-reference value inconsistency of the class 2.1.8 set out to
      close, missed because the new guard checks key presence, not field values,
      and the initial critic sub-state (`pass`, `consecutive_clean`,
      `convergence_target`) is pinned by no test. Decide the intended value and
      make `initial.py`, the corpus builder, and the reference agree (the audit's
      lower-risk option (b) keeps `pass = 1` and corrects the reference comment
      and prose), then add an initial-document test pinning the three critic
      fields. Lightweight addendum pass.
  - [x] 2.1.8.3. Document the state-layout schema-drift guard in the developers'
    guide alongside the direct-edit guard.
    - Addendum (from audit:2.1.8, Finding 3; low). The guide has a dedicated
      subsection for the sibling write-recipe guard but none for the new
      schema-drift guard from 2.1.8, the only tripwire preventing the reference
      fence drifting from what `init` emits; the two guards both scan
      `state-layout.md` and are easily confused, so the missing paired entry is
      a discoverability gap a developer hits only when `make test` fails. A
      docs-only addition. Lightweight addendum pass.

### 2.2. Deliver lossless, atomic state mutation

This step answers whether mutators can write validated state without losing
formatting or leaving a torn file on a crash. Its outcome is the write
discipline every mutator in the spine inherits. See
novel-ralph-harness-design.md §3.4, §4.1, and §5.3.

- [x] 2.2.1. Implement the `tomlkit` round-trip and atomic write helper.
  - Requires 1.1.2 and 2.1.1.
  - Read, mutate, and re-serialise `state.toml` through `tomlkit`, writing via
    a temporary file in the target directory followed by `Path.replace`. Open a
    `[pending_turn]` intent record naming the operation and the paths it will
    write before touching any other file, and clear it only once every artefact
    is written and verified.
  - See novel-ralph-harness-design.md §5.3 and §3.4.
  - Success: a property-based test confirms a no-op mutate-and-write preserves
    on-disk formatting and comments byte-for-byte (the round-trip property), and
    a write interrupted before completion leaves a populated `[pending_turn]`
    record for the next turn to reconcile.
  - [x] 2.2.1.1. Relax the Hypothesis deadline on the `state.toml` round-trip
    property tests.
    - Addendum (from review:1.2.13; medium). The two `@given` property tests in
      `tests/test_state_document.py` inherit the default 200ms deadline, so the
      per-example `tomllib`/`tomlkit` round-trip intermittently breaches it under
      `pytest -n auto` and turns `make all` non-deterministically red; relax the
      deadline (e.g. `@settings(deadline=None)`) so the shared gate stays
      deterministic. Lightweight addendum pass.
- [x] 2.2.2. Implement `init`, `set-cursor`, and `advance-phase`.
  - Requires 2.1.2 and 2.2.1.
  - `init` creates `working/` and an initial state; `set-cursor` refuses
    incoherent cursors; `advance-phase` refuses skips and out-of-order
    completion. A refused mutator request returns exit 3 (state or input error,
    per ADR 003 and §3.2), not the benign-negative exit 1 the loop continues
    on, so the harness cannot mistake a rejected transition for progress.
  - See novel-ralph-harness-design.md §4.1 and §3.2.
  - Success: a behavioural scenario shows an out-of-order `advance-phase` is
    refused with exit 3 and leaves the prior state intact.
  - [x] 2.2.2.1. Document the `init`, `set-cursor`, and `advance-phase`
    subcommands in the users' guide.
    - Addendum (from audit:2.2.2; high). Task 2.2.2 promoted three subcommands
      from stubs to shipping commands but updated only the developers' guide;
      `users-guide.md` still describes only `novel-state check`. Extend the
      `novel-state` section with each subcommand's options, the directory
      skeleton `init` creates, and the shared validate-before-persist, exit-3
      refusal, write-nothing contract. Lightweight addendum pass.
  - [x] 2.2.2.2. Route `_check`, `init`, and the two mutators through a single
    `working/state.toml` path accessor.
    - Addendum (from audit:1.3.5; low). The canonical path is constructed in
      three places (`commands/novel_state.py` `_check` and `init`,
      `commands/_state_mutators.py` `_state_path`); promote one accessor and
      route all four through it so the path has a single home. Lightweight
      addendum pass.
  - [x] 2.2.2.3. Correct the partial-init direction in roadmap-2-2-2 Decision
    Log D3.
    - Addendum (from review:2.3.4; low). D3 describes the realisable partial-init
      as `log present, state absent`, but `init` writes `state.toml` first, so
      the realisable case is the inverse (`state present, log absent`) that task
      2.3.4 targets; correct the stale D3 prose in
      `docs/execplans/roadmap-2-2-2.md` so it agrees with the implemented
      direction. Lightweight addendum pass.
- [x] 2.2.3. Implement the validated chapter-manifest mutator that populates
  `[chapters]`.
  - Requires 2.1.1 and 2.2.2.
  - The chapter manifest is the one piece of state with no command to write it,
    so a chapter planned in `working/plan/chapter-outline.md` has no sanctioned
    path into `[chapters]` and the per-chapter drafting loop is blocked
    (demonstrated: with a draft on disk but an empty manifest, `check` exits 4 on
    `manifest-disk-bijection`, `novel-compile` exits 3, and `recount` returns an
    empty map). Per ADR 001 all state mutation goes through validated commands
    and direct `state.toml` edits are guarded against, so the manifest is no
    exception — the decision is settled in favour of a command, not a
    guard-exempt agent-write. Add a validated `novel state` mutator (e.g.
    `set-chapters`/`plan-chapters`) that ingests the agent's chapter plan
    (number, slug, title, target words) and writes `[chapters]` atomically,
    validating at write time — contiguous numbering from 1, unique numbers, and
    the required fields present — refusing an incoherent plan with exit 3, with
    the log receipt and `[pending_turn]` discipline. Record the command's input
    shape and behaviour as an ADR, and bridge it in `SKILL.md` Phase 7 so the
    agent records chapters by running the command, never by hand-editing
    `state.toml`.
  - See novel-ralph-harness-design.md §4.1, §5.1, §5.2, and
    adr-001-deterministic-judgemental-boundary.md.
  - Success: a chapter planned in `chapter-outline.md` reaches `[chapters]` only
    through the command (no hand-edit); the command refuses a non-contiguous or
    incomplete manifest with exit 3; and `check`, `recount`, and `novel-compile`
    then operate correctly on the real chapter directories — proven end-to-end.
  - [x] 2.2.3.1. Make chapter-slug handling and documentation consistent with the
    opaque `[novel].slug` stance.
    - Addendum (from audit:2.2.3; low). `ChapterPlanEntry.slug` and
      `ChapterEntry.slug` are documented "filesystem-safe" but nothing validates
      them, while the opaque-slug decision is recorded only for `[novel].slug`;
      soften the docstrings and record the opaque stance in ADR 008 / the
      developers' guide, and add the `slug` field to SKILL Phase 7's outline
      checklist, which omits it though set-chapters requires it. Lightweight
      addendum pass.
- [x] 2.2.4. Add CLI mutators for the gate and drafting sub-state.
  - Requires 2.2.2.
  - The gate flags (`gates.knitting.done_30`/`done_50`/`done_80`,
    `gates.final.final_pass_complete`) and the drafting sub-state
    (`drafting.critic.pass`, `drafting.fangirl.last_chapter_passed`) have no CLI
    mutator, so beta testing forced hand-edits of `state.toml` — a direct
    ADR-001 violation and contrary to the skill's "always exercise the installed
    contract". Add validated `novel state` mutators (e.g. `set-gate`,
    `complete-final-pass`, `set-fangirl`, `set-critic-pass`) with the same
    write-time validation, atomic-write, and log-receipt discipline as the
    existing mutators.
  - See adr-001-deterministic-judgemental-boundary.md and
    novel-ralph-harness-design.md §4.1 and §5.1.
  - Success: every gate and drafting sub-state field is settable through a
    command, no field requires a hand-edit, `check` stays coherent across the
    mutations, and behavioural tests cover each mutator.
  - [x] 2.2.4.1. Restore snapshot/BDD parity for the gate and drafting mutators.
    - Addendum (from audit:2.2.4; low). Backfill the missing success and refusal
      `result`/envelope snapshots for `complete-final-pass`, `set-fangirl`, and
      `set-critic-pass`, add a `set-gate` below-threshold refusal snapshot, and
      add a `set_gate.feature` covering the repair/refusal/usage arms, matching
      the sibling-mutator snapshot and `.feature` baseline. Lightweight addendum
      pass.

### 2.3. Deliver recount and disk-authoritative reconciliation

This step answers whether state can be re-derived from disk so it can never
drift from the manuscript. Its outcome retires hand-typed word counts and the
agent-improvised recovery routine. See novel-ralph-harness-design.md §4.1 and
§5.4.

- [x] 2.3.1. Implement `recount` as a pure aggregation over chapter drafts.
  - Requires 2.2.1.
  - Re-derive `word_counts.current` and `by_chapter` from `draft.md` files and
    write the validated result.
  - See novel-ralph-harness-design.md §4.1.
  - Success: `recount` is idempotent — a second run on unchanged drafts writes
    an identical file — and the by-chapter values sum to the current total.
  - [x] 2.3.1.1. Clear the pre-existing ty `possibly-missing-submodule` warning
    on `_recount.py` by importing `tomlkit.items` explicitly.
    - Addendum (from review:2.3.4; low). `make typecheck` is not fully clean: ty
      warns that `tomlkit.items.InlineTable` (the return annotation of
      `_inline_by_chapter`) relies on a submodule that may not have been
      imported; add a single explicit `import tomlkit.items` so the typecheck
      gate is clean. Lightweight addendum pass.
- [x] 2.3.2. Implement read-only reconciliation detection in `check` and the
  disk-authoritative write in `reconcile`.
  - Requires 2.1.2 and 2.3.1.
  - In `check` (read-only), reconstruct intended state from on-disk evidence
    (`done.flag` presence, `compiled.md` contents) where disk is internally
    consistent, report the discrepancy and the reconciliation it implies in the
    payload, and exit 4 without writing. In `reconcile` (mutator), recompute the
    same reconciliation and write the reconciled state, appending a recovery
    entry to the log and deleting no file in `working/`. Assert the
    chapter-manifest-to-disk bijection in `check` — every `chapter-NN/draft.md`
    maps to exactly one manifest entry and vice versa, contiguous from 1. Handle
    an uncleared `[pending_turn]` by having `check` report whether the partial
    write should be completed or discarded according to what landed and
    `reconcile` carry it out. Refuse to auto-repair contradictory disk evidence
    (a `done.flag` beside an empty `draft.md`; a `compiled.md` referencing an
    absent chapter): both `check` and `reconcile` report, log, and exit 4.
  - See novel-ralph-harness-design.md §3.3, §5.2, and §5.4.
  - Success: a scenario where state claims a chapter is done but no `done.flag`
    exists is detected by `check` with exit 4 and repaired by `reconcile`, while
    `check` itself writes nothing; a non-bijective manifest and a
    contradictory-evidence tree are each reported with exit 4 rather than
    silently repaired (the loud-reconciliation requirement).
  - [x] 2.3.2.1. Strengthen the reconcile log-receipt assertion from a substring
    match to a structured receipt.
    - Addendum (from test-quality benchmark; severity: low). The reconcile
      behavioural test asserts `"recount" in log`, which any incidental line
      satisfies; assert the structured reconciliation receipt the design
      mandates (the operation plus the repaired field set) so the log contract
      is actually pinned. Lightweight addendum pass.
  - [x] 2.3.2.2. Pin chapter-draft byte-integrity across a reconcile repair.
    - Addendum (from test-quality benchmark; severity: low). The reconcile
      behavioural test's `files_before <= after` proves no file was removed but
      not that the chapter drafts stayed byte-for-byte unchanged (only
      `state.toml`/`log.md` should change). Assert every `draft.md` is
      byte-identical before and after `reconcile`. Lightweight addendum pass.
  - [x] 2.3.2.3. Correct the `_reconcile.py` module docstring's helper-reuse
    attribution.
    - Addendum (from review:7.2.1; low). The `commands/_reconcile.py` module
      docstring states it "reuses that module's [`_recount`'s] load/refuse
      helpers", but `_load_document_or_state_error` and `_refuse_if_incoherent`
      are imported from `_state_mutators`, not `_recount`; after 7.2.1 routed
      `_reconcile` through `build_inline_table` it imports nothing from
      `_recount` at module level, making the pre-existing inaccuracy more
      visible. Correct the attribution to name `_state_mutators` as the helper
      home. Lightweight addendum pass.
- [x] 2.3.3. Add disk-authoritative cross-checks to the corpus oracle for the
  §5.4 structural invariants.
  - Reroute (source: review:1.3.2; severity: medium). The §1.3.2 corpus oracle
    proves only spec-internal consistency for the structural invariants, but
    design §5.4 makes disk authoritative and the `check`/`reconcile` consumers
    must detect state-versus-disk divergence. Extend the oracle to read
    `working_dir` rather than the spec for the disk-authoritative invariants —
    the manifest/disk bijection, the `done.flag`/`draft.md` contradiction, and
    the `compiled.md` content-hash — so the corpus mirrors what the real `check`
    exercises (the by-chapter-sum check already reads disk after fix-round-1;
    this generalises that move). Test/corpus-only; no design change.
  - Requires 2.3.2.
  - See novel-ralph-harness-design.md §5.4; docs/execplans/roadmap-1-3-2.md
    (the fix-round-1 on-disk decision).
  - Success: the corpus oracle's manifest-bijection, done-flag/draft, and
    compiled checks read the materialised `working_dir`, and a tree whose
    `state.toml` claims agree with disk but whose disk evidence diverges is
    flagged by the oracle from disk alone.
  - [x] 2.3.3.1. Consolidate the repeated per-predicate `state.toml` parse in
    the corpus oracle's disk-evidence checks into a single per-invocation read.
    - Addendum (from review:2.3.3; low). The disk-evidence predicates in
      `tests/working_corpus/_oracle.py` (`by-chapter-sum`, `manifest-disk-
      bijection`, `done-flag-without-draft`, `pending-turn-cleared`,
      `compiled-matches-drafts`, `word-counts-match-drafts`) each re-read and
      re-parse the materialised `state.toml`; parse it once per `corpus_check`
      and pass the decoded tables into the helpers. The production
      `disk_evidence.py` twin already takes a parsed `State` and needs no
      mirror. Lightweight addendum pass.
  - [x] 2.3.3.2. Document the disk-evidence disk-vs-disk twin discipline and
    invariant 5's delivered status in the developers' guide.
    - Addendum (from audit:2.3.3; medium). After 2.3.3 the corpus oracle reads
      disk for the §5.4 invariants, so its disk-evidence checks are now
      disk-vs-disk twins of the production `check_disk_evidence`, not the
      pure-state validator twins the guide describes; and the owned-name table
      still marks invariant 5 "deferred to task 2.3.2" though 2.3.2/2.3.3 have
      delivered it. Record the disk-vs-disk discipline and update the invariant-5
      status so the policy lives in the source of truth, not only in source
      docstrings. Lightweight addendum pass.
- [x] 2.3.4. Cover the partial-`init` bootstrap (`state.toml` present, `log.md`
  absent) in disk-authoritative reconciliation.
  - Reroute (source: review:2.2.2; severity: low). `init` writes `state.toml`
    then `log.md` and refuses any re-run while `state.toml` exists (task 2.2.2
    Decision Log D3), so a crash between the two writes leaves an unrecoverable
    partial bootstrap: `state.toml` present, `log.md` absent, and re-run
    refused. `init` deliberately opens no `[pending_turn]` bracket, so the 2.3.2
    pending-turn recovery path does not see this case. This serves the step-2.3
    hypothesis — state re-derivable from disk so it can never drift — by giving
    multi-file turn recovery, which owns torn turns, the partial-init case too;
    it does not serve the step-2.2 write-discipline hypothesis where it was
    raised. Either `check`/`reconcile` self-heal a missing `log.md` against an
    otherwise-coherent tree, or the partial-init recovery is documented as the
    operator's `init`-rerun-after-removing-`state.toml` routine, decided once.
  - Requires 2.3.2.
  - See novel-ralph-harness-design.md §3.4 and §5.4;
    docs/execplans/roadmap-2-2-2.md (Decision Log D3).
  - Success: a `working/` tree with `state.toml` present and `log.md` absent is
    either reconciled by `reconcile` (a fresh `log.md` recreated, no file in
    `working/` deleted) or the recovery routine is documented in the users'
    guide, and `check` reports the partial bootstrap rather than leaving it
    silently unrecoverable.
  - [x] 2.3.4.1. Document that `reconcile`'s recreate-log restores an empty
    `log.md` in the users' guide.
    - Addendum (from review:2.3.4; low). The `log-present` detector fires on
      `log.md` absence and cannot distinguish a clean partial-`init` crash from
      a later loss of a populated log; `reconcile` always recreates an empty
      `log.md` and exits 0, which could surprise an operator expecting prior
      receipts back. Add a one-paragraph users'-guide note that prior receipts
      are not recoverable. Lightweight addendum pass.
- [x] 2.3.5. Settle the authoritative `current` definition when `compiled.md`
  diverges from the drafted sum, and align recount and reconcile on it.
  - Step-task (source: review:2.3.1; severity: low). `recount` deliberately
    scopes `word_counts.current` to `sum(by_chapter)` (2.3.1 Decision Log
    D-CURRENT), but `state-layout.md:114` still describes `current` as "words in
    compiled.md (or sum of drafts)", and a present `compiled.md` token count can
    diverge from `sum(by_chapter)` (separator joins, trailing whitespace). This
    serves the step-2.3 hypothesis — state re-derivable from disk so it can
    never drift from the manuscript — by deciding which on-disk quantity is
    authoritative for `current` when the two diverge, so `recount` and the
    `reconcile` task (2.3.2) cannot disagree on the `current` definition and the
    reference prose stays truthful. Decide once whether `current` remains the
    drafted sum (with `compiled.md` divergence surfaced as a reconciliation
    finding, not a `current` source) or is redefined, and reconcile
    `state-layout.md`, design §5.4, and the 2.3.1 D-CURRENT note to the chosen
    rule.
  - Requires 2.3.1 and 2.3.2.
  - See novel-ralph-harness-design.md §4.1 and §5.4;
    docs/execplans/roadmap-2-3-1.md (Decision Log D-CURRENT);
    skill/novel-ralph/references/state-layout.md (line 114).
  - Success: one decision records the authoritative `current` quantity when
    `compiled.md` diverges from `sum(by_chapter)`; `recount` and `reconcile`
    apply the same rule; and `state-layout.md`, design §5.4, and the 2.3.1
    D-CURRENT note agree on the `current` definition with no surviving
    contradiction.
  - [x] 2.3.5.1. Add a check/reconcile REFUSE assertion to case 1's divergent
    `compiled.md` tree.
    - Addendum (from review:2.3.5; low). Case 1 only documents in a comment that
      the same divergent `compiled.md` "would REFUSE under check/reconcile" and
      exercises only `recount` (which ignores it); add the missing assertion (or
      reuse case 1's tree under `check`) so recount-ignores and check-refuses are
      proven on the same tree, closing the boundary loop. Lightweight addendum
      pass.
  - [x] 2.3.5.2. Harden the reconcile-path divergence guards against the
    shared-oracle and shared-validator blind spots.
    - Addendum (from review:2.3.5; low). Case 2's recount==reconcile agreement
      test uses `recount_words` as both oracle and subject, and the reconcile
      fail-red leans on `_refuse_if_incoherent`'s by-chapter-sum validator firing
      first, so a future refactor that repoints the shared helper or both
      `current` and `by_chapter` at compiled-derived values could go undetected;
      pin `by_chapter` to the honest drafted sum independently of the `current`
      write for at least one fixture so the reconcile guard is discriminating.
      Lightweight addendum pass.
  - [x] 2.3.5.3. Move the D-TOKEN-EQUALITY rationale into the durable design doc.
    - Addendum (from audit:2.3.5; low). The reason a `compiled.md` divergence can
      only come from non-whitespace content — so pinning `current` to the drafted
      sum loses no information — lives only in the ExecPlan and a test docstring
      while design §4.1/§5.4 assert only the conclusion; add one sentence to the
      design so the load-bearing rationale lives in the source of truth.
      Lightweight addendum pass.
- [x] 2.3.6. Detect `[word_counts].by_chapter` key-set divergence from the
  manifest and on-disk drafts, not only shared-key value divergence.
  - Step-task (source: review:2.3.2; severity: low). The `check`
    `word-counts-match-drafts` predicate compares only the shared (intersection)
    chapter keys (D-WC-SHARED-KEYS), and `manifest-disk-bijection` checks the
    manifest against on-disk directories, not against the `by_chapter` key set,
    so a state whose `[word_counts].by_chapter` omits a chapter that is drafted
    on disk (or carries a key the manifest lacks) falls through every current
    disk-evidence invariant. This serves the step-2.3 hypothesis — state
    re-derivable from disk so it can never drift from the manuscript — by closing
    the design §5.4 "state behind disk" key-coverage gap a `RECOUNT` would supply
    (the missing key), so a chapter drafted on disk but absent from the table is
    flagged rather than silently tolerated. It is substantial because it adds a
    new disk-evidence coverage predicate (twinned against the per-chapter disk
    oracle, distinct from the value-divergence `word-counts-match-drafts` check)
    plus a first-class §1.3.2 corpus variant, and must keep `CORPUS_INVARIANT_NAMES`,
    the agreement suites, and the existing `check`/`reconcile` behaviour green,
    which warrants its own plan and review. Add a `word-counts-cover-drafts`
    coverage predicate that reports a `by_chapter` key omitted relative to the
    drafted manifest (and any table key absent from the manifest), repaired by
    the same `RECOUNT`, and a corpus variant exercising both directions.
  - Requires 2.3.2.
  - See novel-ralph-harness-design.md §5.2 and §5.4;
    docs/execplans/roadmap-2-3-2.md (Decision Log D-WC-SHARED-KEYS,
    D-SCOPE/D-WORDCOUNT).
  - Success: a state whose `[word_counts].by_chapter` omits a chapter with a
    non-empty on-disk `draft.md` is detected by `check` with exit 4 on a named
    coverage invariant and repaired by `reconcile` via `RECOUNT`; a table key
    with no manifest entry is likewise flagged; the new predicate and its corpus
    variant agree with the disk oracle across the whole-corpus agreement loop;
    and the existing shared-key `word-counts-match-drafts` and
    `manifest-disk-bijection` invariants stay unchanged.
  - [x] 2.3.6.1. Add an entry-point e2e for the orphan-key (extra-table-key)
    reconcile direction.
    - Addendum (from review:2.3.6; low). The omit-drafted-chapter direction has
      a full `check`→`reconcile`→`check` entry-point e2e but the orphan-drop
      direction (a table key absent from the manifest) is only covered at the
      derivation/integration level; add the symmetric e2e so the user-visible
      orphan-drop path matches the plan's dual-direction behavioural acceptance.
      Lightweight addendum pass.
- [x] 2.3.7. Make recount's gate-ratio refusal actionable and document the
  recount-gate coupling.
  - Requires 2.3.1.
  - `recount` exits 3 `gate-ratio-consistent` when the recount would cross a
    30/50/80% threshold while the gate flag is still false (correctly forcing
    the knitting pass), but beta testing found the message cryptic and the
    recount-to-gate coupling undocumented. Make the message actionable — name
    the crossed threshold and the required knitting-gate action — and document
    the coupling in the developers' and users' guides and the skill.
  - See novel-ralph-harness-design.md §4.1 and §5.2.
  - Success: the refusal names the threshold and the remedy, the recount-gate
    coupling is documented, and a behavioural test asserts the actionable
    message.
  - [x] 2.3.7.1. Correct the `_refuse_if_incoherent` caller enumeration in
    `docs/execplans/roadmap-2-3-7.md`.
    - Addendum (from review:2.3.7; low). The execplan (Interfaces and
      dependencies, Work item 2) states four other callers of
      `_refuse_if_incoherent`, but the actual set is 11 call sites across five
      files; the `remedy=None`-default conclusion is unaffected, but the stale
      premise understates the keyword's blast radius. Correct the enumeration.
      Lightweight addendum pass.
  - [x] 2.3.7.2. Render the recount remedy ratio without a boundary
    self-contradiction.
    - Addendum (from review:2.3.7; low). `_recount._gate_ratio_remedy` renders
      the drafted ratio with `:.0f`, so `0.298` prints `30%` inside a "below the
      30% threshold" sentence, reading as a contradiction near a gate boundary;
      the verdict and exit code are unaffected. Render with one decimal or note
      the boundary-rounding edge. Lightweight addendum pass.
- [x] 2.3.8. Re-key `word-counts-cover-drafts` off the on-disk drafted subset so
  it stays enforced during a relaxed drafting subset.
  - Reroute (source: review:2.1.7; severity: low; two near-identical proposals
    merged). ADR 009 (Known risks, Outstanding decisions) records that
    `word-counts-cover-drafts` is un-enforced during a relaxed drafting subset
    because `_check_word_counts_cover_drafts` recomputes `by_chapter` by keying
    off the manifest and defers on any `manifest != on_disk` tree, which a relaxed
    subset always is; a `by_chapter` key-set drift on a mid-draft tree is
    therefore not caught until the tree returns to bijection or reaches
    final-pass/done. ADR 009 explicitly defers this detector redesign to a later
    roadmap task. This does not serve the step-2.1 schema hypothesis it was raised
    under; it serves the step-2.3 hypothesis — state re-derivable from disk so it
    can never drift from the manuscript — by re-keying the coverage detector off
    the on-disk drafted subset so the §5.4 stale-table coverage holds across the
    whole drafting phase rather than only at bijection or final-pass. It is
    substantial because it redesigns the cover-drafts detector and its corpus twin
    and must keep the strict-default `manifest-disk-bijection` relaxation,
    `CORPUS_INVARIANT_NAMES`, the agreement suites, and the existing
    `check`/`reconcile` behaviour green, which warrants its own plan and review.
  - Requires 2.3.6 and 2.1.7.
  - See novel-ralph-harness-design.md §5.2 and §5.4;
    docs/adr-009-drafting-bijection-relaxation.md (Known risks and limitations;
    Outstanding decisions); docs/execplans/roadmap-2-3-6.md.
  - Success: while `phase.current == drafting` and the on-disk chapters are a
    subset of the manifest, `word-counts-cover-drafts` keys off the on-disk
    drafted subset rather than the full manifest, so a `by_chapter` key omitted
    relative to a drafted chapter is flagged mid-draft and repaired by `reconcile`
    via `RECOUNT`; the detector and its corpus twin agree across the whole-corpus
    agreement loop; and the `manifest-disk-bijection` relaxation,
    `word-counts-match-drafts`, and the reconcile precedence stay unchanged.
  - [x] 2.3.8.1. Add a present-but-empty-draft case to the cover-drafts
    convergence/coherence tests.
    - Addendum (from review:2.3.8; low). Decision D6 pins "drafted means
      directory-present, not non-empty `draft.md`", but no test exercises a
      drafted chapter directory carrying an empty `draft.md` (count `0`); add a
      targeted case so a future refactor to a non-empty filter is caught.
      Lightweight addendum pass.
  - [x] 2.3.8.2. Add a direct match-drafts/cover-drafts non-co-fire assertion on
    the relaxed subset.
    - Addendum (from review:2.3.8; low). Constraint 3 (orthogonality) is proven
      only indirectly via full-verdict membership; add a direct unit assertion
      that `_check_word_counts_match_drafts` is silent on the omitted-drafted-key
      relaxed tree to harden the no-double-fire invariant. Lightweight addendum
      pass.
  - [x] 2.3.8.3. Add a BDD scenario for the mid-draft relaxed-subset RECOUNT
    recovery.
    - Addendum (from audit:2.3.8; low). The 2.3.8 headline behaviour has unit and
      e2e coverage but no black-box scenario in `reconcile.feature` pinning the
      operator-visible contract; add one (reusing the existing when/then steps
      plus a relaxed-subset `@given`) to restore coverage symmetry with the
      sibling reconcile recoveries. Lightweight addendum pass.

## 3. Vertical slice 2: a single-source done predicate

Idea: if the done predicate is the same code path the harness gates on, the
two-source divergence between the short-form and long-form predicates
disappears, and "check done every turn" becomes one trustworthy call.

This slice delivers `novel-done`: a per-clause predicate evaluated against
disk, including the hash-based compile-divergence check that a coincidentally
matching header count and word total cannot fool. It reuses the schema and
validator from phase 2.

### 3.1. Deliver the per-clause done predicate

This step answers whether every done clause can be evaluated deterministically
against disk and reported individually. Its outcome makes the predicate
auditable rather than a single opaque boolean. See
novel-ralph-harness-design.md §4.2 and §2.3.

- [x] 3.1.1. Implement the per-clause predicate and its structured result.
  - Requires phase 2.
  - Evaluate `phase_is_done`, `final_pass_complete`, `all_chapters_flagged`,
    `knitting_gates_passed`, `compile_consistent`, and
    `no_unresolved_blockers`, reporting which clauses failed.
  - See novel-ralph-harness-design.md §4.2.
  - Success: each clause can be independently driven true and false from the
    §1.3.2 corpus, and the exit code is 0 only when every clause holds.
  - [x] 3.1.1.1. Reconcile the `done-conditions.md` reference predicate to the
    manifest chapter source.
    - Addendum (from review:3.1.1 / audit:3.1.1; low). The shipped predicate
      reads per-manifest chapters (`state.chapters`) while the reference
      `novel_predicate` at `done-conditions.md:158,180` still parses
      `plan/chapter-outline.md` via a non-existent `parse_chapter_outline`;
      D-CLAUSES recorded this design §4.3-justified divergence and flagged it for
      a docs pass. Reconcile the reference prose to the manifest source so it no
      longer describes a parse path absent from the codebase. Lightweight
      addendum pass.
  - [x] 3.1.1.2. Reconcile the `done-conditions.md` predicate pseudocode to the
    zero-padded `chapter-NN` layout.
    - Addendum (from audit:3.1.5; low). The reference `novel_predicate`'s unpadded
      `chapter-{chapter_id}` path (`done-conditions.md:162,184`) contradicts the
      shipped `_chapter_dir_name` (`chapter-NN`), so a reader following it
      literally looks in the wrong directory for single-digit chapters; fix the
      pseudocode to the zero-padded layout. Docs-only one-line fix removing a
      standing docs-vs-code inconsistency. Closes audit-3.1.5 Finding 1.
      Lightweight addendum pass.
- [x] 3.1.2. Implement the shared compile-and-hash routine and the
  compile-divergence clause.
  - Requires 3.1.1.
  - Build one compile-and-hash function that concatenates the chapter drafts in
    zero-padded chapter-index order and hashes the result, and call it from the
    `compile_consistent` clause to compare against `working/manuscript/compiled.md`
    rather than comparing header counts or word totals. `novel-compile` reuses
    this same function in phase 4 so the two cannot disagree. Report only the
    `compile_consistent` boolean, never per-chapter hashes, so the payload stays
    bounded as the chapter count grows. Drive the exit-code carve-out: when
    `compile_consistent` is the sole unmet clause, exit 4 (an actionable stale
    compile, matching `novel-compile --check`); while any drafting clause is
    still unmet, stay at exit 1.
  - See novel-ralph-harness-design.md §3.2, §4.2, and §2.3.
  - Success: a stale `compiled.md` whose header count and word total
    coincidentally match the drafts is still reported as divergent (the
    predicate-truthfulness property); the `novel-done` result size is
    independent of the chapter count; and an otherwise-complete tree with only a
    stale `compiled.md` exits 4 while a mid-draft tree exits 1.
  - [x] 3.1.2.1. Pin or drop the unused `DONE_PREDICATE_OBVIOUS_STALE_COMPILE`
    corpus spec.
    - Addendum (from review:3.1.2; low). The obvious byte-and-count-divergent
      stale spec is exported through the corpus `__all__` but asserted on by no
      test, so it validates nothing while still sitting on the corpus public
      surface; either pin it with a test (the clause reports divergence and the
      tree exits 4) or drop it so the corpus exports stay load-bearing.
      Lightweight addendum pass.
- [x] 3.1.3. Share the compiled-matches-drafts comparison between the §5.4
  detector and the `compile_consistent` clause.
  - Step-task (source: audit:3.1.1; severity: medium).
    `disk_evidence._check_compiled_matches_drafts` already implements the
    compiled-versus-drafts comparison the `compile_consistent` clause is
    scheduled to gain at task 3.1.2 (with the opposite absent-file polarity), so
    3.1.2 would otherwise re-implement that comparison a third time with
    divergent fault handling. This serves the step-3.1 hypothesis — every done
    clause evaluated deterministically against disk — by giving the
    compile-consistency clause one shared comparison so the predicate and the
    §5.4 detector cannot disagree on what "compiled matches drafts" means. Factor
    a shared `compiled_matches_drafts(state, working_dir)` helper into
    `compile_model.py`, reconciling the absent-file polarity once, and have both
    the §5.4 detector and the 3.1.2 clause consume it.
  - Requires 3.1.1.
  - See novel-ralph-harness-design.md §4.2, §4.3, and §5.4;
    docs/issues/audit-3.1.1.md (Finding 2);
    novel_ralph_skill/state/disk_evidence.py.
  - Success: one `compiled_matches_drafts(state, working_dir)` helper in
    `compile_model.py` owns the compiled-versus-drafts comparison; both
    `disk_evidence._check_compiled_matches_drafts` and the `compile_consistent`
    clause consume it (each supplying its own absent-file polarity); no third
    independent re-implementation survives; and the done-predicate and
    disk-evidence suites stay green.
  - [x] 3.1.3.1. Add a clause-boundary fault-propagation test for
    `compile_consistent` with a present compile beside an unreadable draft.
    - Addendum (from review:3.1.3; low). The shared
      `compiled_matches_drafts` helper propagates `UnicodeDecodeError`/`OSError`
      when `compiled.md` is present beside an undecodable `draft.md`, but the
      done-predicate suite pins this only for an undecodable `compiled.md`; the
      present-compile-plus-unreadable-draft direction at the clause boundary —
      where the exit-3 routing actually matters — is untested. Add the focused
      fault test so the contract is pinned at the `compile_consistent` boundary.
      Lightweight addendum pass.
- [x] 3.1.4. Anchor the unresolved-BLOCKER resolution rule positionally and
  cover the false-clean direction.
  - Step-task (source: review:3.1.1 / audit:3.1.1; severity: low). The
    `no_unresolved_blockers` clause clears a blocker whenever the literal
    `[resolved]` appears anywhere on a line, so a live blocker that incidentally
    mentions `[resolved]` is wrongly declared clean — the exit-0 lie the
    predicate exists to prevent — and that false-clean direction is untested. The
    rule also mis-classifies prose mentions of resolution and case or format
    variants. This serves the step-3.1 hypothesis — every done clause evaluated
    deterministically and truthfully against disk — by making the BLOCKER clause
    sound in both directions rather than only the false-positive one. Anchor the
    resolution token to a positional marker (or a more precise grammar / a
    structured marker), keep the existing near-miss corpus spec green, and add a
    corpus near-miss exercising the false-clean direction.
  - Requires 3.1.1.
  - See novel-ralph-harness-design.md §4.2;
    skill/novel-ralph/references/done-conditions.md (the BLOCKER substring rule);
    docs/issues/audit-3.1.1.md (Finding 3).
  - Success: a live BLOCKER line that incidentally contains `[resolved]` is
    reported as unresolved (the clause stays false), a genuinely resolved blocker
    still clears, the false-clean direction is pinned by a new §1.3.2 corpus
    near-miss, and the done-predicate suite stays green.
- [x] 3.1.5. Align the `no_unresolved_blockers` recogniser to the real
  `critic-personas.md` output format and define the resolution producer contract.
  - Step-task (source: audit:3.1.4 / review:3.1.4; severity: high). Three
    near-identical proposals merged: the predicate's `no_unresolved_blockers`
    clause matches lines whose stripped text starts with `BLOCKER` and ends with
    a trailing `[resolved]` token, but `critic-personas.md` emits blockers as a
    `## BLOCKER` section heading with `### B1 — <label>` findings and defines no
    `[resolved]` marker, so the clause matches zero lines and reads clean against
    genuine critic output — the exit-0 lie the clause exists to prevent, firing
    on every real unresolved blocker. The invented line-prefix grammar (task
    3.1.4, D-BLOCKER-SCOPE) hardened a format the producer never writes, and no
    reference defines how a blocker is marked resolved. This serves the step-3.1
    hypothesis — every done clause evaluated deterministically and truthfully
    against disk — by making the BLOCKER clause sound against the format the
    critic actually produces rather than conservative-but-decorative against live
    input. Define the resolution convention in `critic-personas.md` (and
    `done-conditions.md`), realign the recogniser to the heading-based
    `## BLOCKER`/`### Bn` structure plus that documented resolution token, fold
    in the deferred case-insensitive / alternative-spelling resolution-variant
    decision (D-BLOCKER-SCOPE leaves `RESOLVED`/`(resolved)` out of scope in both
    directions), and add a §1.3.2 corpus tree built from real
    critic-personas-shaped output.
  - Requires 3.1.4.
  - See novel-ralph-harness-design.md §4.2;
    skill/novel-ralph/references/critic-personas.md (the `## BLOCKER`/`### Bn`
    format); skill/novel-ralph/references/done-conditions.md (the BLOCKER
    substring rule); docs/issues/audit-3.1.4.md.
  - Success: the resolution convention is defined once in `critic-personas.md`
    and `done-conditions.md`; the `no_unresolved_blockers` recogniser parses the
    real `## BLOCKER`/`### Bn` section structure and that documented resolution
    token (with the case/alternative-spelling-variant decision recorded); a
    §1.3.2 corpus tree built from critic-personas-shaped output drives the clause
    both clean and dirty; an unresolved blocker in genuine critic output is
    reported (the clause stays false); and the done-predicate suite stays green.
  - [x] 3.1.5.1. Pin the decorated `## BLOCKER` heading false-clean direction with
    an asserting-current-behaviour test.
    - Addendum (from review:3.1.5; low). The recogniser enters the section only
      on an exact `## BLOCKER` match, so a decorated heading
      (`## BLOCKER (chapter 3)`) reads clean by design and matches the producer
      contract, but no test pins this single-sided behaviour; add an
      asserting-current-behaviour test so a future critic-prompt change emitting
      a decorated heading cannot silently re-open the exit-0 lie, mirroring how
      D-BLOCKER-CASE is pinned. Lightweight addendum pass.
  - [x] 3.1.5.2. Add an end-to-end novel-done scenario for the cap-reached
    `[resolved]` exit-0 path.
    - Addendum (from audit:3.1.5; low). The `[resolved]` token's purpose is the
      cap-reached resolution path, yet only a unit test covers it; the exit-0
      direction is the one the harness loop terminates on, so it is the more
      consequential to pin behaviourally. Add the scenario using the existing
      all-hold tree builder and step wiring. Closes audit-3.1.5 Finding 2.
      Lightweight addendum pass.

## 4. Vertical slice 3: deterministic, outline-ordered compilation

Idea: if `compiled.md` is regenerated deterministically in outline order with
consistent separators, the ordering ambiguity of a directory glob disappears
and the compile-consistency clause has an authoritative artefact to check
against.

This slice delivers `novel-compile` as both a mutator and, under `--check`, a
read-only checker. It shares the hashing approach with the phase 3 divergence
clause so the two never disagree.

### 4.1. Deliver outline-ordered compilation and its checker

This step answers whether compilation can be made deterministic and verifiable
without writing. Its outcome resolves assumption A5 — ordering is the
zero-padded chapter index, validated against the manifest — and gives
`novel-done` a stable artefact. See novel-ralph-harness-design.md §4.3 and §2.3.

- [x] 4.1.1. Implement `novel-compile` ordered by the zero-padded chapter index.
  - Requires phase 2.
  - Concatenate chapter drafts in zero-padded chapter-index order with
    consistent separators, writing `working/manuscript/compiled.md` atomically,
    and exit 3 when the chapter manifest is absent or empty (no authoritative
    ordering). No outline prose is parsed.
  - See novel-ralph-harness-design.md §4.3 and §10.
  - Success: compilation is deterministic — identical drafts and manifest
    produce a byte-identical `compiled.md` — regardless of directory listing
    order.
  - [x] 4.1.1.1. Add a coherence integration test driving `novel-compile` then
    `novel-state check` end-to-end through the installed console scripts.
    - Addendum (from review:4.1.1; low). The round-trip oracle is pinned at the
      function level (`check_disk_evidence` over a freshly compiled tree); a thin
      integration test driving both real entry points in sequence catches future
      drift between the two commands' resolvers and envelopes the function-level
      pin cannot see. Lightweight addendum pass.
- [x] 4.1.2. Implement the `--check` read-only divergence checker.
  - Requires 4.1.1 and 3.1.2.
  - Report divergence by calling the shared compile-and-hash routine from
    3.1.2 — the same code path the `novel-done` compile clause uses — writing
    nothing and exiting 4 on divergence.
  - See novel-ralph-harness-design.md §3.3 and §4.3.
  - Success: `novel-compile --check` and the `novel-done` compile clause agree
    on every corpus fixture because they share one routine (the compile-fidelity
    property).
  - [x] 4.1.2.1. Align design §4.3 prose with the delivered absent-compile
    polarity.
    - Addendum (from review:4.1.2; low). Design §4.3 says `novel-compile --check`
      exits 4 "when the compile is stale", but the shipped, agreement-pinned
      behaviour also exits 4 when `compiled.md` is absent (matching the
      `novel-done` compile clause); reword the sentence to "stale or absent" so
      the design no longer reads as a latent doc/behaviour mismatch. Lightweight
      addendum pass.
  - [x] 4.1.2.2. Add an absent-compile case to the `novel-compile --check`
    entry-point e2e.
    - Addendum (from review:4.1.2; low). `tests/test_compile_e2e.py` pins the
      `--check` current (exit 0) and stale (exit 4) branches through the real
      console-script body but not the absent branch, which is the polarity
      decision most likely to regress; add a third e2e case (absent `compiled.md`
      → exit 4, `diverged: true`, no file created) to close the symmetry.
      Lightweight addendum pass.

## 5. Vertical slice 4: deterministic slop detection

Idea: if the desloppify checklist runs as a versioned rule pack that emits
structured per-hit output, the improvised `grep` the field report blames — with
its spurious whole-file output, non-zero-on-zero-match breakage, and mid-scan
glob expansion — is replaced by a command the model can adjudicate against.

This slice delivers `desloppify` over the §6 high-frequency-offender table as
the first rule pack. It detects and reports only; it never edits and never
judges. The rule-pack schema it establishes is reused by the AI-isms and
device-ledger packs in the deferred phase.

### 5.1. Deliver the rule-pack engine and the first pack

This step answers whether detection rules can be expressed as versioned data
and applied uniformly across a chapter or the whole manuscript. Its outcome is
the rule-pack contract the later packs extend. See
novel-ralph-harness-design.md §4.4, §6.1, and §1.

- [x] 5.1.1. Implement the versioned rule-pack loader and schema.
  - Requires steps 1.1-1.3.
  - Load a TOML pack of `pattern`, `threshold`, and `basis` rules, validating
    `schema_version` and rejecting malformed patterns with exit 2 naming the
    offending rule id.
  - See novel-ralph-harness-design.md §6.1 and §10.
  - Success: a pack with an invalid regular expression fails loudly, naming the
    rule, rather than silently skipping it.
  - [x] 5.1.1.1. Document the on-disk rule-pack TOML format for pack authors.
    - Addendum (from audit:5.1.1; medium). Add a worked fenced TOML example to
      the developers' guide "Rule packs" section showing both bases and enumerate
      the v1 key vocabulary with the strict rules the loader enforces, so an
      author has a documented format to write against. Lightweight addendum pass.
  - [x] 5.1.1.2. Make `parse_rulepack`'s total exception surface explicit in its
    docstring.
    - Addendum (from audit:5.1.1; low). State that `RulePackError` is the only
      exception the pure boundary raises and that file/decode faults belong to
      `load_rulepack` (`RulePackFileError`), pinning the contract task 5.1.2
      catches against. Lightweight addendum pass.
  - [x] 5.1.1.3. Route every per-rule diagnostic through the `_where(rule_id)`
    helper.
    - Addendum (from audit:5.1.1; low). Replace the six inline
      `f"rule {rule_id!r} …"` prefixes in the rule-specific helpers with
      `_where(rule_id)` so the rule-naming format has one home. Internal only;
      public behaviour unchanged. Lightweight addendum pass.
  - [x] 5.1.1.4. Reconcile `_entries`' concrete `list`/`dict` guard with the
    boundary's advertised `Mapping` input and pin it with a test.
    - Addendum (from audit:5.1.1; low). Pick one: tighten the documented contract
      to a `tomllib`-shaped mapping, or loosen the guards to the abstract shapes;
      then add the matching purity test for a non-`dict` mapping input so the
      contract is asserted rather than implied. Lightweight addendum pass.
  - [x] 5.1.1.5. Drop the redundant `str(...)` wrappers in the `RuleBasis`
    diagnostic builders.
    - Addendum (from audit:5.1.1; low). `RuleBasis` is a `StrEnum`, so
      `repr(member)` and `basis!r` render identically; remove the defensive
      `str(...)` in `_resolve_basis` and `_resolve_page_words`. Cosmetic;
      behaviour unchanged. Lightweight addendum pass.
  - [x] 5.1.1.6. Split `rulepack/parse.py` to bring it under the 400-line file
    cap.
    - Addendum (from audit:1.3.5; low). `rulepack/parse.py` is 515 lines,
      breaching the AGENTS.md 400-line cap; extract the scalar-coercion helpers
      into a `rulepack/_coerce.py` leaf module so the cap is met. Lightweight
      addendum pass.
- [x] 5.1.2. Implement `desloppify` detection over the §6 offender table.
  - Requires 5.1.1.
  - Emit structured output per hit — phrase, count, density per N words,
    threshold, pass or fail, and line numbers — for a chapter or the whole
    manuscript, making zero edits. Exit 0 on a clean pass, 4 when violations are
    found (an actionable finding), and 2 on a usage error, so the three are
    distinguishable by exit code alone.
  - Verify with snapshot coverage of the envelope plus boundary examples (a hit
    exactly at threshold, a clean pass), not a full property-based or
    behavioural suite — the command is a pure aggregation (§9).
  - See novel-ralph-harness-design.md §4.4 and §9.
  - Success: clean prose exits 0, a manuscript with violations exits 4, and a
    malformed invocation exits 2 — each distinguishable without parsing JSON.
  - [x] 5.1.2.1. Document the per-page density behaviour on short or near-empty
    drafts in the users' guide.
    - Addendum (from review:5.1.2; low). The §4.5 density formula lets a single
      `per_page` offender trip the threshold on a sub-page draft because a
      partial page still counts; add a one-paragraph note to the `desloppify`
      users'-guide section so an operator scanning an early or short chapter is
      not surprised by the design-correct extrapolation. Lightweight addendum
      pass.
  - [x] 5.1.2.2. Tighten the snapshot volatile-field guard from a bare slash
    check to a path/timestamp pattern.
    - Addendum (from review:5.1.2; low). `tests/test_desloppify_snapshots.py`
      asserts no `/` appears in the rendered envelope, so a future rule id, pack
      name, or message carrying a slash would fail spuriously; replace the bare
      slash check with a regex matching absolute-path or timestamp shapes so the
      guard stays durable across packs. Lightweight addendum pass.
  - [x] 5.1.2.3. Reconcile the per-hit `phrase` wording across design §4.4, the
    roadmap, and the emitted envelope.
    - Addendum (from review:5.1.2; low). The envelope emits the rule's authored
      pattern source under `phrase` while `rule_id` is the canonical slug;
      reconcile the design §4.4 and roadmap 5.1.2 "phrase, count, density…"
      wording with the shipped contract (and the users'-guide gloss) so the
      §7.1 ai-isms and device-ledger packs inherit an unambiguous per-hit output
      vocabulary rather than re-litigating whether `phrase`/`pattern` belongs in
      the envelope. Lightweight addendum pass.
  - [x] 5.1.2.4. Correct the "cannot drift from `recount_words`" docstrings under
    `--chapter` scope and test the per-page density message branch.
    - Addendum (from audit:5.1.2; medium). `detect`'s "cannot drift from
      `recount_words`" docstrings are misleading because `--chapter N` computes
      per-page density over one chapter, not the manuscript total; reword them to
      name the actual scope, and add a focused test for the untested
      `_finding_message` per-page density branch
      (`commands/_desloppify_report.py`). Both are localised to the 5.1.2
      surface. Lightweight addendum pass.

## 6. Vertical slice 5: derived word counts and gate triggers

Idea: if word counts and knitting-gate triggers are derived from disk on every
run, the repeated hand computation in the field report disappears and the 80%
gate can never fire late at 85%.

This slice delivers `wordcount` as a read-only checker reporting per-chapter
and cumulative figures alongside the next gate distance. It completes the
deterministic spine and feeds the knitting gate into the per-chapter pipeline.

### 6.1. Deliver word reporting and gate-distance computation

This step answers whether progress and gate proximity can be derived purely
from disk. Its outcome retires the last hand-computed determinism in the field
report. See novel-ralph-harness-design.md §4.5.

- [x] 6.1.1. Implement `wordcount` reporting and gate-trigger derivation.
  - Requires phase 2.
  - Report per chapter and cumulatively: words, percentage of target, distance
    to the next knitting gate, and delta against the chapter target, deriving
    the 30%, 50%, and 80% gate triggers rather than noticing them late.
  - Verify with snapshot coverage of the envelope plus boundary examples (a
    manuscript exactly on each gate), not a full property-based or behavioural
    suite — the command is a pure aggregation (§9).
  - See novel-ralph-harness-design.md §4.5 and §9.
  - Success: at a manuscript exactly on a gate threshold the corresponding gate
    is reported as just reached, and the next-gate distance is non-negative.
- [x] 6.1.2. Calibrate the skill for drafting deflation.
  - Requires 6.1.1.
  - Beta testing showed the drafting-plus-desloppify loop is net-deflationary:
    per-scene estimates ran ~20-30% high, the spiteful critic cut 10-20% per
    chapter as designed, chapters landed at 60-85% of target, and the finished
    book reached only ~90% of target (26,990 of 30,000) even after a manual
    expansion pass. Adjust the skill — either inflate the Phase 6/7 chapter
    targets by roughly +20%, or add an explicit "expand to target" step in the
    Phase 8/9 drafting and final flow — so the finished book reliably hits
    target. This is a `SKILL.md` workflow change, not a CLI change.
  - See SKILL.md Phases 6-9 and novel-ralph-harness-design.md §7.2.
  - Success: `SKILL.md` carries an explicit deflation-compensation mechanism
    (inflated planning targets or an expand-to-target step) with the rationale
    recorded.
  - Done: chose the expand-to-target step (not target inflation) to keep the
    honest target, STC sum check, and knitting-gate maths untouched. `SKILL.md`
    Phase 8 (new step d, before desloppify, current chapter only) and Phase 9
    (after the structural critic) carry it; `tests/test_skill_deflation_guard.py`
    pins it.
  - [x] 6.1.2.1. Add an ordering-aware structural assertion to the deflation
    guard.
    - Addendum (from review:6.1.2; low; two near-identical proposals merged). The
      substring guard cannot detect a wrong insertion point or re-measure
      placement and leaves the ordering to human review. Add an ordinal check:
      the Phase 8 second `wordcount` mention falls after the desloppify step, and
      the Phase 9 expand step falls after the structural critic and before
      `complete-final-pass`. Lightweight addendum pass against the 6.1.2 execplan.
  - [x] 6.1.2.2. Strengthen the deflation guard to pin the over-expansion /
    headroom cue.
    - Addendum (from review:6.1.2; low). The guard passes on `wordcount` twice
      plus the mechanism name, so it would pass even with the convergence defect
      fix-round-1 corrected; add a stable substring asserting the Phase 8 region
      budgets the destructive cut as deliberate headroom. Lightweight addendum
      pass against the 6.1.2 execplan.
  - [x] 6.1.2.3. Reconcile the Phase 8 to Phase 9 residual-deficit handoff prose
    with the artefacts produced.
    - Addendum (from review:6.1.2; low). The Phase 8 escalation defers a deficit
      to "the Phase 9 final expand pass" but no log artefact or state field
      carries it; Phase 9 re-derives it from `wordcount`. Adjust the `SKILL.md`
      prose so it does not imply an artefact that is not produced. Lightweight
      addendum pass against the 6.1.2 execplan.

### 6.2. Prove the spine end-to-end across the combinatorial surface

This step answers whether the five commands behave correctly across the full
`command × output-mode × phase` surface, not just in isolation. Its outcome is
the confidence the harness needs to gate on the spine unattended. See
novel-ralph-harness-design.md §2.3 and §9.

- [x] 6.2.1. Build the combinatorial command-surface test suite.
  - Requires phase 5 and 6.1.1.
  - Snapshot the machine-mode JSON envelope per command, assert the `--human`
    mode for presence, and carry semantic assertions over the
    phase-dependent branches across the eleven phase states.
  - See novel-ralph-harness-design.md §9 and §2.3.
  - Success: the `command × output-mode × phase` matrix is covered, with the
    knowingly carried gaps (exhaustive phase cross-products) documented rather
    than silently omitted.
- [x] 6.2.2. Build the end-to-end per-chapter deterministic-loop scenario.
  - Requires 6.2.1.
  - Drive a chapter from `recount` through `novel-done`, `wordcount`,
    `desloppify`, and `novel-compile --check` on a real `working/` tree,
    asserting the harness-facing flows from the design.
  - See novel-ralph-harness-design.md §7.2 and §9.
  - Success: a stale compile is caught, a crossed gate is reported, and an
    out-of-order phase advance is refused, all in one scripted pass.
  - [x] 6.2.2.3. Assert recount's no-op invariant at the installed boundary.
    - Addendum (from review:6.2.2; low). The installed clean-pass scenario drives
      `recount` (a mutator) before the read commands and relies on the in-process
      Risk-2 argument that it is a no-op over the all-hold tree; add an explicit
      installed assertion that the recounted `{current, by_chapter}` equals the
      drafted totals so the no-op property is proven at the real wheel boundary
      rather than inferred from the in-process suite. Lightweight addendum pass.
- [x] 6.2.3. Correct the documented skill defects and point the prose at the
  commands.
  - Requires phase 3.
  - The phase mislabel (drafting is Phase 8, not Phase 7) and the dead
    per-chapter `plan.md` entry are already corrected in the skill files by
    commit `916313c`; the remaining work is to reduce both prose copies of the
    done predicate to a pointer at `novel-done` and the developers' guide clause
    table.
  - See novel-ralph-harness-design.md §8.
  - Success: `make markdownlint` passes on the edited skill files and
    `grep -rn "novel_predicate" skill/` returns no match, so no prose copy of
    the predicate survives to diverge.
  - [x] 6.2.3.1. Repoint the `SKILL.md` reference-files table row for
    done-conditions toward `novel-done` for novel-level completion.
    - Addendum (from review:6.2.3; low). `SKILL.md` "Reference files" still
      names `done-conditions.md` as the reference for "overall completion",
      which after this task is `novel-done`'s responsibility
      (`done-conditions.md` merely redirects); a one-line table-cell tweak
      naming `novel-done` for the novel-level check removes the last soft
      pointer implying `done-conditions.md` holds the overall predicate.
      Lightweight addendum pass.
  - [x] 6.2.3.2. Reconcile design §8 and the developers' guide clause table
    after this task.
    - Addendum (from audit:6.2.3; low). Design §8's two-source-predicate bullet
      still reads future-tense ("roadmap task 6.2.3 reduces both prose copies")
      now this task has merged, and the now-authoritative developers' guide
      clause table lists the six clauses out of canonical design §4.2 order
      (`no_unresolved_blockers` and `compile_consistent` swapped); fix both
      together. Lightweight addendum pass.
- [x] 6.2.4. Broaden the installed-binary e2e coverage to `recount` and the
  exit-3 state-error paths.
  - Requires 2.1.2 and 2.3.1.
  - Today only the exit-0 path (and `desloppify`'s exit 4) crosses the real
    wheel/venv subprocess boundary; `recount` is proven only through the
    entry-point body, and the exit-3 state-error paths only in-process. Add a
    `@slow` installed-binary e2e that runs `novel-state recount` over a built
    wheel and asserts the JSON envelope, plus one that drives a missing or
    unparseable `state.toml` through the installed binary and asserts exit 3.
  - See novel-ralph-harness-design.md §9; adr-003-shared-interface-contract.md.
  - Success: `recount` and at least one exit-3 state-error path are each
    asserted against a real installed console-script, not only in-process.
- [x] 6.2.5. Add a torn-turn recovery scenario driven through a real command.
  - Requires 2.2.2 and 2.3.2.
  - The current torn-turn behavioural test exercises the `pending_turn()`
    primitive directly against a literal `state.toml`, never crossing the
    command boundary; the only real-crash coverage is an in-process integration
    test. Add a scenario that interrupts a mutator mid-write (leaving a
    populated `[pending_turn]` and partial artefacts on disk) and proves
    `novel-state check` reports the torn turn and `novel-state reconcile`
    completes or rolls it back per what landed — driven through the command
    entry points, not the bracket primitive.
  - See novel-ralph-harness-design.md §3.4 and §5.4.
  - Success: a torn write produced by an actual mutator invocation is detected
    by `check` and recovered by `reconcile`, asserted at the command boundary.
  - [x] 6.2.5.1. Pin the two-pass convergence count in the torn-turn recovery
    tests.
    - Addendum (from review:6.2.5; low). `test_reconcile_integration.py` and the
      new torn-turn BDD steps document and rely on exactly two-pass convergence
      (clear the leftover record, then re-apply recount) but only assert
      convergence within a bound (`range(3)`); tighten both to the exact pass
      count so a regression that silently raises the re-entry passes the harness
      needs to converge fails loudly. Lightweight addendum pass.
- [x] 6.2.6. Extend the installed-binary exit-3 coverage to `reconcile` and
  `wordcount`.
  - Step-task (source: audit:6.2.4 Finding 6; severity: low). Task 6.2.4 added
    installed-binary exit-3 proofs for `recount` only, yet `reconcile` and
    `wordcount` share the same state-input boundary and exit-3 contract and have
    only happy-path installed proofs. This advances the step-6.2 hypothesis —
    that the five commands behave correctly across the full `command × output-mode
    × phase` surface, not just in isolation — by closing the installed-binary
    exit-3 asymmetry across the commands the harness branches on for every
    invocation, hardening the packaging boundary the unattended gate trusts. Add
    `@slow` installed-binary e2e proofs that drive a missing or unparseable
    `state.toml` through the installed `novel-state reconcile` and `wordcount`
    console-scripts and assert exit 3, mirroring the `recount` proof 6.2.4 added.
  - Requires 6.2.4.
  - See novel-ralph-harness-design.md §9 and §2.3;
    docs/adr-003-shared-interface-contract.md;
    docs/issues/audit-6.2.4.md (Finding 6).
  - Success: `reconcile` and `wordcount` each assert exit 3 on a missing or
    unparseable `state.toml` against a real installed console-script over a built
    wheel, not only in-process, closing the installed exit-3 asymmetry left after
    6.2.4.
  - [x] 6.2.6.1. Add a missing-state-only in-process exit-3 test for `wordcount`.
    - Addendum (from review:6.2.6; low). The missing-state case (a `working/`
      directory present but `state.toml` absent) is proven in-process for
      `wordcount` only indirectly via the absent-working-dir and unparseable-state
      tests; the precise present-working-dir-without-`state.toml` shape is pinned
      in-process for `recount` but not directly for `wordcount`. Add a direct
      in-process assertion so the installed proof's truth is self-contained per
      command rather than resting on the shared boundary argument. Lightweight
      addendum pass.
  - [x] 6.2.6.2. Assert a non-empty human-facing message in the installed exit-3
    envelopes across `recount`, `reconcile`, and `wordcount`.
    - Addendum (from review:6.2.6; low). The installed exit-3 proofs assert
      exit 3 with `ok:false` and no `Traceback` but pin no message content, yet
      design §10 requires a state fault to yield a message, not a stack trace; a
      regression emitting an empty or unhelpful operator message would pass
      today. Add a small shared assertion that each installed exit-3 envelope
      carries a non-empty `messages` entry, extended across the recount proof
      6.2.4 added. Lightweight addendum pass.
- [x] 6.2.7. Add a reconcile-boundary `ROLLBACK_PENDING_TURN` recovery scenario.
  - Step-task (source: review:6.2.5; severity: low). Task 6.2.5 proves the
    `COMPLETE` disposition (both declared artefacts present) at the `reconcile`
    command boundary, but design §5.4 also covers the `ROLLBACK` disposition (an
    unrecoverable `draft.md`/`done.flag` did not land), which has no
    reconcile-command-boundary coverage. This advances the step-6.2 hypothesis —
    that the five commands behave correctly across the full surface, not just in
    isolation — by proving the symmetric half of the torn-turn recovery story at
    the same command boundary 6.2.5 covered for `COMPLETE`. Add a sibling
    scenario that crashes `reconcile` after declaring a path that does not
    materialise, driven through the command entry points, and proves `check`
    reports the torn turn and `reconcile` rolls it back per what landed.
  - Requires 6.2.5.
  - See novel-ralph-harness-design.md §3.4 and §5.4.
  - Success: a torn turn whose declared artefact did not land is detected by
    `check` and rolled back by `reconcile` at the command boundary, closing the
    symmetric `ROLLBACK` half of the disposition 6.2.5 proved for `COMPLETE`.
  - [x] 6.2.7.1. Strengthen the rollback no-deletion assertion to also forbid
    fabrication.
    - Addendum (from review:6.2.7; low). Design §5.4 item 2 says rolling back
      removes nothing and fabricates nothing; the scenario asserts non-removal via
      a subset check (`files_before <= after`) and draft-byte equality but does
      not directly assert that no unexpected `working/` file is created during
      rollback. Tighten the assertion so the after-set difference is limited to
      `{state.toml, log.md}`, catching a fabrication regression. Lightweight
      addendum pass.
- [x] 6.2.8. Extend the command-surface matrix to a minimal error-mode slice, or
  record the omission as a carried gap.
  - Step-task (source: audit:6.2.1 Finding 5; severity: low). The combinatorial
    matrix never crosses the runner's command-agnostic exit-2 (`CycloptsError`)
    and exit-3 (`StateInputError`) diagnostic arms — the very envelopes that stamp
    `--human` before the body runs — and the Carried gaps section does not name
    the omission. This advances the step-6.2 hypothesis — that the five commands
    behave correctly across the full `command × output-mode × phase` surface —
    by extending the matrix's surface to the command-agnostic error-mode
    envelopes the harness gates on, or by recording the bound explicitly per the
    design's §9 "carried knowingly rather than silently" principle. Either add a
    minimal exit-2/exit-3 envelope slice to the matrix or name the omission in the
    Carried gaps section.
  - Requires 6.2.1.
  - See novel-ralph-harness-design.md §9 and §2.3;
    docs/issues/audit-6.2.1.md (Finding 5).
  - Success: the matrix either crosses a minimal exit-2/exit-3 error-mode slice
    (asserting the `--human` stamp and envelope shape on the command-agnostic
    diagnostic arms) or its Carried gaps section names the error-mode omission
    explicitly, so the bound is carried knowingly rather than silently.
  - [x] 6.2.8.1. De-duplicate the near-degenerate error-arm snapshots in the
    command-surface matrix.
    - Addendum (from audit:6.2.8; low). The ten `test_error_arm_machine_envelope`
      snapshots redact the only command-variable field, leaving each differing
      solely by a `command` string the test body already asserts field-by-field,
      so they re-pin a skeleton with no added signal. Replace the ten `.ambr`
      blocks with one in-code expected-skeleton assertion templated on
      `command.name`/`working_dir`. Lightweight addendum pass.
- [x] 6.2.9. Extend the installed per-chapter loop re-drive to the refused-advance
  and crossed-gate decisions.
  - Step-task (source: audit:6.2.2 Finding 7; severity: low). The installed
    wheel/venv re-drive of the per-chapter loop covers only the clean pass and
    the stale-compile catch; the refused out-of-order `advance-phase` (exit 3,
    stamped by `contract/runner.py` before the body runs) and the crossed-gate
    report are exactly the POSIX exit-code-translation behaviour the installed
    boundary exists to prove, yet remain in-process-only. This advances the
    step-6.2 hypothesis — that the five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by crossing
    the refused-advance and crossed-gate decisions over the real installed
    boundary rather than inferring them from the in-process suite. Either add
    the installed re-drive of both decisions or record the in-process-only bound
    as a carried gap per design §9.
  - Requires 6.2.2.
  - See novel-ralph-harness-design.md §9 and §2.3;
    docs/issues/audit-6.2.2.md (Finding 7).
  - Success: the refused out-of-order `advance-phase` (exit 3) and the crossed-gate
    report are each proven over the real installed console-script boundary, or the
    in-process-only bound is named in the Carried gaps section so it is carried
    knowingly rather than silently.
  - [x] 6.2.9.1. Split `tests/steps/per_chapter_loop_installed_steps.py` before
    it breaches the 400-line module cap.
    - Addendum (from review:6.2.9; low). At 383 of 400 lines the next installed
      arm risks breaching the AGENTS.md module-size gate mid-task; extract the
      run/build helpers (the `_run_installed_argv`/`_run_installed`/
      `_build_installed` seam) from the step definitions into a small support
      module so future installed work stays within bounds. Lightweight addendum
      pass.
  - [x] 6.2.9.2. Correct the execplan framing of where the refused-advance exit-3
    is stamped.
    - Addendum (from review:6.2.9; low). The 6.2.9 execplan (lines 28-34) frames
      the refused-advance exit-3 as runner-stamped "before the command body runs
      (global-flag pre-parse)", but for the `completed-prefix-gap` case the exit-3
      originates from a domain `StateInputError` raised inside `advance_phase`
      (`_refuse_if_incoherent(prior)`) and is translated by the runner; reword the
      prose to distinguish the two exit-3 paths (pre-parse global-flag errors
      versus in-body domain refusals) so a later reader does not misread the
      contract surface. Lightweight addendum pass.
  - [x] 6.2.9.3. Enforce the installed step helper's capture-key single-write
    contract structurally.
    - Addendum (from review:6.2.9; low). `_run_installed_argv` is a command/query
      hybrid (it writes `installed.captures[capture_key]` and returns the tuple)
      whose single-write contract is guarded only by the module docstring; a
      future maintainer copying a `When` step could re-add `captures[...] =` and
      double-write silently. Add a small assertion that the `capture_key` is not
      already written this run so the contract is enforced rather than only
      documented. Lightweight addendum pass.
  - [x] 6.2.9.4. Parametrise the two duplicated installed-scenario mark-guard
    tests.
    - Addendum (from audit:6.2.9 Finding 3; low). The two `*_carries_marks` tests
      in `tests/test_per_chapter_loop_installed_bdd.py` are near-identical clones
      differing only in the bound function and message noun, and the developers'
      guide instructs contributors to add a guard per installed scenario, so the
      clone pattern grows one copy per future scenario; collapse them to one
      `@pytest.mark.parametrize`d test over `(function, label)` pairs so adding
      a scenario is a one-line append, keeping each scenario named in the test
      id. Lightweight addendum pass.
      Lightweight addendum pass.
  - [x] 6.2.9.5. Document the installed crossed-gate folding and step-harness
    conventions adjacent to the code.
    - Addendum (from audit:6.2.9 Findings 2, 4, 5; low). Three consistency notes
      share a root cause — rationale that lives only in the developers' guide, not
      next to the code: (1) add a one-line feature-header comment recording that
      the installed feature folds the crossed-gate into the clean-pass scenario
      rather than a standalone scenario (asymmetric with the in-process feature),
      and (2) sanction the `_run_installed_argv` command/query hybrid as a
      deliberate test-helper exception in the developers' guide's test-helper
      conventions. The audit's third, conditional note — extracting a shared
      capture-contract helper "if a third loop boundary appears" — is deferred to
      step 7.5 (shared command-driving scaffolding) and not folded here.
      Lightweight addendum pass.
- [x] 6.2.10. Cross the installed-binary command-agnostic error arms (exit 2 and
  exit 3) over a built wheel.
  - Step-task (source: review:6.2.8; severity: low). Task 6.2.8 closes the
    in-process exit-2/exit-3 matrix gap for the runner's command-agnostic
    diagnostic arms, but the installed-binary crossing — the same arms over a
    console-script entry point on a built wheel — is untested; 6.2.4's installed
    coverage proves only body-produced envelopes. This advances the step-6.2
    hypothesis — that the five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by closing
    the symmetry between the in-process error-mode matrix and the installed-binary
    matrix for the two command-agnostic diagnostic arms the harness gates on. Add
    a `@slow` installed-binary e2e that drives a usage error (exit 2) and a
    state-input fault (exit 3) through a console-script over a built wheel and
    asserts the `--human` stamp and envelope shape on both arms.
  - Requires 6.2.4 and 6.2.8.
  - See novel-ralph-harness-design.md §9 and §2.3;
    docs/adr-003-shared-interface-contract.md.
  - Success: the command-agnostic exit-2 and exit-3 diagnostic arms are each
    asserted against a real installed console-script over a built wheel, with the
    `--human` stamp and envelope shape pinned, closing the in-process-versus-binary
    asymmetry left after 6.2.8.
  - [x] 6.2.10.1. Cross the installed error arms over a second installed command
    as a command-sensitivity tripwire.
    - Addendum (from review:6.2.10; low). Decision D-ONECMD crosses only
      `novel-state` on the empirical 6.2.8 finding that the arms are
      command-agnostic; extend the installed error-arm matrix to a second
      installed command (e.g. `desloppify`, which already has an installed
      fixture) so a future change making the shared runner's arms
      command-sensitive is caught rather than silently uncovered. Lightweight
      addendum pass.
  - [x] 6.2.10.2. Pin `schema_version` (and field order) at the installed-binary
    boundary for the diagnostic arms.
    - Addendum (from review:6.2.10; low). The in-process matrix pins the full
      envelope including `schema_version` via snapshot, but the installed-boundary
      error-arm proofs assert only the command/ok/working_dir/result/messages
      skeleton; add a `schema_version` assertion (or a redacted boundary
      snapshot) so the boundary proof is a complete mirror of the in-process
      contract and a schema bump or field-order regression cannot survive
      packaging unobserved. Lightweight addendum pass.
- [ ] 6.2.11. Add an installed-binary exit-3 e2e proof for `desloppify`, the fifth
  state-input command.
  - Step-task (source: audit:6.2.6; severity: low). After 6.2.6 the installed
    exit-3 proofs cover `recount`, `reconcile`, and `wordcount`, but `desloppify`
    — which also reads `working/` and a pack file and can exit 3 — carries only
    in-process exit-3 coverage. This advances the step-6.2 hypothesis — that the
    five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by closing
    the remaining installed-versus-in-process asymmetry the 6.2.6 work set out to
    narrow, proving the last state-input command's exit-3 fault routing at the real
    packaging boundary. Best sequenced after the shared `run_installed` helper
    (7.5.3) so it is a few-line addition rather than a fourth copy of the build
    scaffolding. Add a `@slow` installed-binary e2e that drives a missing or
    unparseable `state.toml` through the installed `desloppify` console-script and
    asserts exit 3, mirroring the recount/reconcile/wordcount proofs.
  - Requires 6.2.6 and 7.5.3.
  - See novel-ralph-harness-design.md §9 and §2.3;
    docs/adr-003-shared-interface-contract.md.
  - Success: `desloppify` asserts exit 3 on a missing or unparseable `state.toml`
    against a real installed console-script over a built wheel, not only
    in-process, closing the installed exit-3 asymmetry across all five
    state-input commands.
- [x] 6.2.12. Add a command-boundary ROLLBACK scenario where the unrecoverable
  artefact partially landed.
  - Step-task (source: review:6.2.7; severity: low). Task 6.2.7 proves the
    `ROLLBACK` disposition only where the declared `draft.md` never materialises;
    design §5.4's clause that rollback "leaves the partial artefacts in place" is
    unexercised at the command boundary. This advances the step-6.2 hypothesis —
    that the five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by proving
    the second half of the rollback operational surface: a torn turn whose partial
    `draft.md` did land must be preserved on disk, unreferenced by state, once the
    record is cleared. Add a sibling scenario, driven through the command entry
    points, where a partial `draft.md` materialised before the crash and assert
    `reconcile` rolls back the record while leaving the partial artefact in place.
  - Requires 6.2.7.
  - See novel-ralph-harness-design.md §3.4 and §5.4.
  - Success: a torn turn whose declared `draft.md` partially landed is detected
    by `check` and rolled back by `reconcile` at the command boundary, with the
    partial artefact preserved on disk and unreferenced by state, closing the
    leaves-partial-artefacts-in-place half of the §5.4 rollback surface.
- [x] 6.2.13. Add a command-boundary ROLLBACK scenario for an unrecoverable
  `done.flag` (not only `draft.md`).
  - Step-task (source: audit:6.2.7; severity: low).
    `_classify_pending_turn` treats both `draft.md` and `done.flag` as
    unrecoverable `ROLLBACK` triggers, but task 6.2.7 proves only the `draft.md`
    trigger end-to-end through the runner; the `done.flag` trigger remains
    in-process-only via the pure classifier test. This advances the step-6.2
    hypothesis — that the five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by closing
    the command-boundary half of the `ROLLBACK` disposition for the second
    trigger, the same narrowing 6.2.7 was created to close for `draft.md`. A
    parametrisation over `(declared_path, expected_basename)` covers both
    triggers with one step module.
  - Requires 6.2.7.
  - See novel-ralph-harness-design.md §3.4 and §5.4;
    docs/issues/audit-6.2.7.md.
  - Success: an unrecoverable `done.flag` torn turn is detected by `check` and
    rolled back by `reconcile` at the command boundary, parametrised alongside the
    `draft.md` trigger so both `ROLLBACK` triggers are proven end-to-end through
    the runner rather than only in-process.
  - [x] 6.2.13.1. Refresh the developers' guide torn-turn behavioural-scenario
    note to enumerate the complete scenario family.
    - Addendum (from audit:6.2.12; low). The guide names only the first torn-turn
      scenario, but after 6.2.7, 6.2.12, and 6.2.13 the suite covers the
      COMPLETE, never-landed-ROLLBACK, and partial-landed-ROLLBACK halves of the
      §5.4 reconciliation surface; enumerate the full scenario family so the
      developer documentation map stays current. Lightweight addendum pass.
- [x] 6.2.14. Add a command-boundary partial-landed ROLLBACK scenario for an
  unrecoverable `done.flag`.
  - Step-task (source: review:6.2.12; severity: low). `_classify_pending_turn`
    treats both `draft.md` and `done.flag` as unrecoverable `ROLLBACK` triggers,
    and 6.2.12 closed the partial-landed cell only for `draft.md` while 6.2.13
    closed the never-landed cell for `done.flag`; the partial-landed `done.flag`
    cell remains unexercised at the command boundary. This advances the step-6.2
    hypothesis — that the five commands behave correctly across the full
    `command × output-mode × phase` surface, not just in isolation — by closing
    the last open cell of the torn-turn ROLLBACK disposition matrix at the
    command boundary, the sibling of the partial-landed `draft.md` proof 6.2.12
    added. Add
    a scenario, driven through the command entry points, where a partial
    `done.flag` materialised before the crash and assert `check` reports the torn
    turn and `reconcile` rolls back the record while leaving the partial artefact
    in place, unreferenced by state.
  - Requires 6.2.12 and 6.2.13.
  - See novel-ralph-harness-design.md §3.4 and §5.4.
  - Success: a torn turn whose declared `done.flag` partially landed is detected
    by `check` and rolled back by `reconcile` at the command boundary, with the
    partial artefact preserved on disk and unreferenced by state, closing the
    partial-landed `done.flag` cell of the §5.4 rollback surface left after 6.2.12
    and 6.2.13.

### 6.3. Make the command contract uniform, actionable, and self-documenting

This step answers whether every command presents an identical exit-code and
envelope contract, fails with actionable messages, and is documented once
without per-command drift — the properties an agent depends on when driving the
harness unattended. Its outcome is a contract a dogfooding agent can trust:
loud, consistent, and self-describing. Surfaced by dogfooding (a wrong-directory
invocation that read as a silent failure because the error was a raw errno and
the skill never said to check exit codes). See novel-ralph-harness-design.md §3
and adr-003-shared-interface-contract.md.

- [x] 6.3.1. Make state-input (exit-3) error messages actionable across every
  command.
  - Requires 2.2.2 and 1.2.12.
  - A missing or unreadable `working/state.toml` currently surfaces the raw
    `OSError` string (`[Errno 2] No such file or directory: 'working/state.toml'`)
    in the envelope `messages`. Replace it with an actionable message naming the
    directory and the remedy — e.g. `no novel working/ found in <cwd>; run from
    the novel root, or 'novel state init' to create one`. NOTE: there is NOT a
    single state-loading boundary — there are TWO producers of the raw `cannot
    load {path}: {exc}` message, and both must be fixed identically or the
    message drifts between commands (the very inconsistency 6.3 exists to close):
    `_load_or_state_error` in `novel_ralph_skill/commands/novel_state.py` (wraps
    `load_state`/`tomllib`, used by the reader/checker/state verbs) and
    `_load_document_or_state_error` in
    `novel_ralph_skill/commands/_state_mutators.py` (wraps
    `load_document`/`tomlkit`, used by the mutators). Route both through one
    shared actionable-message helper so they cannot diverge.
  - See novel-ralph-harness-design.md §3.2 and §3.4.
  - Success: a behavioural test drives a command from a directory with no
    `working/` and asserts exit 3 with an actionable message that names the cwd
    and the remedy, with no raw `Errno`/traceback text, for at least one command
    of each class (mutator, checker, reader) — proving BOTH boundaries emit the
    identical actionable message.
  - [x] 6.3.1.1.
    - Addendum (from review:6.3.1; low). Record the omitted Decision Log entry
      naming `_state_view_or_state_error` as an out-of-scope, non-producer
      boundary (parsed-but-structurally-incomplete, not a failed load) so a
      future reviewer does not mistake it for a third producer of the
      `cannot load …` message. Lightweight addendum pass.
  - [x] 6.3.1.2.
    - Addendum (from review:6.3.1; low). Add a corrupt-arm parity assertion to
      `test_state_input_message_parity.py`, which pins only the missing-`working/`
      arm, so a one-sided re-wording of the present-but-corrupt message cannot
      silently reintroduce reader/mutator drift. Lightweight addendum pass.
- [x] 6.3.2. Pin cross-command exit-code and envelope-schema consistency with a
  shared behavioural suite and snapshots.
  - Requires phase 5, 6.1.1, and 1.2.12.
  - Assert, across all five commands as one parametrised pytest-bdd suite plus
    syrupy snapshots, that the contract is identical between commands: the
    exit-code-to-`ok` mapping (exit 0 → `ok:true`; exits 1/2/3/4 → `ok:false`),
    the envelope field set and order (`command`, `schema_version`, `ok`,
    `working_dir`, `result`, `messages`), the field types, and the shape of each
    error channel (usage → 2, state/input → 3, actionable finding → 4). The
    suite must fail if any command drifts from the shared envelope or exit-code
    table.
  - See adr-003-shared-interface-contract.md and novel-ralph-harness-design.md §3.
  - Success: a single cross-command suite (pytest-bdd scenarios + syrupy
    snapshots) pins the exit-code and envelope contract for every command and
    fails on any per-command divergence.
  - [x] 6.3.2.1.
    - Addendum (from review:6.3.2; low). Add a completeness tripwire for the
      actionable-finding (exit 4) arm in the cross-command suite, asserting the
      finding cells cover exactly `{novel state, novel compile, novel
      desloppify}`, mirroring the existing diagnostic-arm guard, so an orphaned
      `_BODY_CELLS` deletion cannot silently shrink coverage under xdist.
      Lightweight addendum pass.
  - [x] 6.3.2.2.
    - Addendum (from review:6.3.2; low). Strip the two redundant `typing.cast`
      wrappers over `ChannelCell.build_app` (already typed `Callable[[], App]`)
      and the now-unused `cabc`/`cyclopts` `TYPE_CHECKING` references they
      justified, clearing the `ty check` redundant-cast warnings. Lightweight
      addendum pass.
  - [x] 6.3.2.3.
    - Addendum (from review:6.3.2; low). Correct the roadmap §6.3.2 wording that
      reads `0/1 → benign, 2/3/4 → ok:false`; per ADR-003 and design §3.1 `ok`
      is true iff exit 0, so benign-negative exit 1 is `ok:false`. Editorial
      roadmap fix. Lightweight addendum pass.
- [x] 6.3.3. Document the unified contract and command-invocation discipline in
  the skill.
  - Requires 6.3.2.
  - Add a single authoritative description of the exit-code table and the
    envelope schema to `SKILL.md` (or a reference it links once), so no
    per-command prose copy can drift, and add the command-invocation discipline
    a dogfooding agent needs: run every command from the novel root; after each
    invocation gate on the EXIT CODE, not on `ok` (which is merely `exit == 0`
    and so cannot tell a benign exit 1 from a stop-and-fix exit 4): exit 0 is
    success, exit 1 is a benign negative to handle and continue, and exits 2/3/4
    are a stop-and-fix — never an assumed success. Also record the
    install-currency note (the `uv tool` binary does not auto-update; reinstall
    with `--force`, or pin a version, before a dogfood session).
  - See novel-ralph-harness-design.md §3 and §8.
  - Success: `SKILL.md` documents the exit-code table, the envelope schema, and
    the run-from-root / check-exit-code discipline once; `make markdownlint` and
    `make nixie` pass on the edited skill.
  - [x] 6.3.3.1.
    - Addendum (from review:6.3.3; low). Reword the roadmap §6.3.3 gating prose
      that instructs treating `ok:false` as a stop-and-fix; `ok` is true iff
      exit 0, so gating on it would halt the loop on every benign exit-1 turn.
      Gate on the exit code instead, matching the shipped SKILL.md. Editorial
      roadmap fix. Lightweight addendum pass.
- [x] 6.3.4. Resolve `working/` robustly and surface the resolved path.
  - Requires 1.2.12.
  - Commands resolve `working/` relative to the current directory with no upward
    search, so beta testing hit a stray `cd` that silently broke them (resolving
    `working/working/…`). Either resolve `working/` by searching upward from the
    current directory (as git finds `.git`), or always report the resolved
    absolute `working_dir` in the envelope so a misresolution is visible — pick
    one and justify it.
  - See novel-ralph-harness-design.md §3.
  - Success: running from a subdirectory of the novel root resolves the correct
    `working/` (upward search), or the envelope `working_dir` is the absolute
    resolved path; running from inside `working/` no longer silently looks for
    `working/working`.
  - [x] 6.3.4.1.
    - Addendum (from review:6.3.4; low). Normalise the ungated POSIX-separator
      suffix assertion `result["working_dir"].endswith("/working")` in
      `tests/test_novel_state_mutators.py` (line 100) to a pathlib-based
      `.name`/`.parts` check, matching the portability convention already
      enforced on the new test modules in this task so the suite stays portable
      and consistent. Lightweight addendum pass.
  - [x] 6.3.4.2.
    - Addendum (from review:6.3.4; low). Extract one shared JSON-aware
      `working_dir` snapshot-normaliser and route both snapshot modules through
      it, replacing the brittle regex redaction in
      `tests/test_novel_state_mutator_snapshots.py` with the robust JSON-parse
      strategy so the two strategies no longer diverge and per-machine snapshot
      churn cannot reappear if the envelope renderer's key order or whitespace
      changes. Lightweight addendum pass.
- [x] 6.3.5. Make the six draft-read (exit-3) boundaries actionable, extending
  6.3.1's polish from the state.toml-load faults to the draft-read faults.
  - Step-task (source: audit:6.3.1 / audit:6.3.2; severity: medium). Serves the
    §6.3 hypothesis that every command "fails with actionable messages": 6.3.1
    polished the two state.toml-load boundaries but left six sibling draft-read
    boundaries (`_disk_evidence_or_state_error`, `_recount`, `_wordcount`,
    `_novel_done`, `_desloppify`, `_compile`) interpolating a raw `{exc}` on the
    same exit-3 channel, so the same command surfaces both polished and raw OS
    text depending on the fault. Route all six call sites through a shared
    actionable formatter analogous to `_state_input_error` that names the
    `working/` tree and offers a remedy without leaking `Errno`, and include the
    mutator view-derivation boundary `_state_mutators._state_view_or_state_error`
    in the enumeration so the structurally-incomplete arm stops leaking raw
    `{exc}` and carries an inspect/repair remedy (audit:6.3.2 folded in). This is
    the message-quality half of the draft-read work; the catch-idiom DRY half is
    7.3.3, with which it coordinates so the formatter and the wrapper share one
    home.
  - Requires 6.3.1.
  - See novel-ralph-harness-design.md §3.2 and §3.4;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_state_load.py (`_state_input_error`);
    novel_ralph_skill/commands/_state_mutators.py
    (`_state_view_or_state_error`).
  - Success: a behavioural test drives at least one command per draft-read
    boundary from a faulted-draft state and asserts exit 3 with an actionable
    message naming the `working/` tree and a remedy, with no raw `Errno`/`{exc}`
    text; all six draft-read call sites and the mutator view-derivation boundary
    emit the shared actionable prose; and the affected command suites stay green.
  - [x] 6.3.5.1.
    - Addendum (from review:6.3.5; low). Extract the shared inspect/repair remedy
      tail (`inspect and repair it, or restore it from a known-good copy`) into
      one constant both `_state_input_error` and `_draft_read_error` in
      `novel_ralph_skill/commands/_state_load.py` interpolate, so the two sibling
      formatters stop diverging on punctuation (semicolon versus em-dash) and the
      parity guarantee becomes structural rather than incidental. Lightweight
      addendum pass.
- [x] 6.3.6. Extend the cross-command identity proof to the installed-wheel
  boundary as a single tripwire.
  - Step-task (source: review:6.3.2; severity: low). Serves the §6.3 hypothesis
    that "every command presents an identical exit-code and envelope contract":
    the 6.3.2 suite proves the identity in-process through the `run` seam, but
    the installed binary is what the harness actually executes. Add a single
    installed-boundary identity tripwire reusing the existing
    `installed_novel_state` / `single_program_catalogue` cuprum fixtures (sketched
    in the 6.3.2 execplan Decision Log and Interfaces section) to close the
    residual gap between the in-process identity proof and the executed surface,
    without duplicating the full `command × channel` matrix.
  - Requires 6.3.2.
  - See adr-003-shared-interface-contract.md; novel-ralph-harness-design.md §3
    and §9; docs/execplans/roadmap-6-3-2.md (Decision Log; Interfaces);
    tests/installed_binary_fixtures.py.
  - Success: one installed-binary identity tripwire drives a representative
    command through the installed wheel and asserts its envelope skeleton and
    exit-code mapping match the in-process contract pinned by 6.3.2; the tripwire
    reuses the existing installed-binary cuprum fixtures rather than rebuilding
    the matrix; and the e2e and cross-command suites stay green.
  - [x] 6.3.6.1.
    - Addendum (from review:6.3.6; low). Make the tautological
      `envelope["ok"] is (result.exit_code == ExitCode.SUCCESS)` assertion in
      `test_installed_novel_state_check_exits_zero` load-bearing or document it
      as intent-only — either add a clarifying comment that it is a redundant
      mapping guard, or cross-arm parameterise it so the mapping check can fail
      independently of the already-asserted `exit_code == 0` and `ok is True`.
      Lightweight addendum pass.
  - [x] 6.3.6.2.
    - Addendum (from audit:6.3.6; medium). Parameterise the canonical
      `assert_envelope_skeleton` helper with an optional `working_dir` override
      (default `WORKING_DIR_CONSTANT`) and collapse the inline envelope-skeleton
      block re-spelled at `tests/test_novel_state_check.py` lines 363-380 onto a
      single helper call, keeping only the command-specific
      `result["violations"] == []` assertion, so the installed identity mirror
      and the in-process identity proof cannot drift independently. Lightweight
      addendum pass.
- [x] 6.3.7. Pin the `SKILL.md` command-contract restatement to the code with a
  drift-guard test.
  - Step-task (source: review:6.3.3 / audit:6.3.3; severity: low). Serves the
    §6.3 hypothesis that the contract is "documented once without per-command
    drift": after 6.3.3 the contract is restated in four places (ADR-003, design
    §3, the developers' guide, and `SKILL.md`), single-sourced only by prose
    pointers; the `SKILL.md` exit-code table and envelope skeleton are the one
    copy NOT pinned by a test, so a change to `ExitCode`, the envelope field set,
    or `schema_version` would silently stale the agent-facing table — the exact
    drift §6.3 exists to close. Add a docs-level drift-guard (a snapshot or
    grep-based assertion) that the `SKILL.md` contract cells match ADR-003 Table
    2 / design §3.1 and the code, following the repo's existing prose-guard
    pattern, so the guard is mechanical rather than reliant on reviewer
    diligence.
  - Requires 6.3.3.
  - See adr-003-shared-interface-contract.md (Table 2);
    novel-ralph-harness-design.md §3.1;
    novel_ralph_skill/contract/exit_codes.py;
    novel_ralph_skill/contract/envelope.py; SKILL.md.
  - Success: a drift-guard test fails if the `SKILL.md` exit-code table or
    envelope skeleton diverges from ADR-003 Table 2 / design §3.1 or from the
    `ExitCode`, envelope-field, and `schema_version` source; the guard reuses the
    repo's established prose-guard pattern; and the docs and contract suites stay
    green.
  - [x] 6.3.7.1.
    - Addendum (from review:6.3.7; low). Extend the 6.3.7 drift-guard with one
      assertion that the design §3.1 and ADR-003 `schema_version` values match
      `ENVELOPE_SCHEMA_VERSION`, closing the gap where a drift introduced in
      design §3.1 alone (e.g. `schema_version: 2`) would slip past every existing
      guard. Lightweight addendum pass.
- [x] 6.3.8. Make the remaining exit-3 write/file-fault arms actionable
  (compile-write, rule-pack read, device-ledger read).
  - Step-task (source: review:6.3.5 / audit:6.3.5 Finding 5; severity: low; two
    near-identical proposals merged). Serves the §6.3 hypothesis that every
    command "fails with actionable messages": 6.3.1 and 6.3.5 made the
    state.toml-load and draft-read exit-3 faults actionable, but the three
    write/file-fault tails `_compile.py:156` (`cannot write {_COMPILED_REL}:
    {exc}`), `_desloppify.py:270` (`cannot read rule pack: {exc}`), and
    `_desloppify_ledger.py:90` (`cannot read device ledger: {exc}`) still
    interpolate the raw caught-exception repr on the same exit-3 channel,
    violating scripting-standards.md line 678 — the last raw-OS-text leaks on the
    state-input channel and the same dogfooding-agent inconsistency §6.3 exists
    to close. They were correctly scoped out of `_draft_read_error` (D3/D6: a
    write fault wants a write-shaped remedy; a pack/ledger fault names a
    different artefact), so give each its own write-shaped or file-shaped sibling
    formatter that names the artefact and offers a remedy without leaking
    `Errno`/`{exc}`. Coordinate with 7.3.9 (the desloppify/ledger pack-detect
    pipeline consolidation) so the new formatters land on the shared seam rather
    than a parallel one.
  - Requires 6.3.5.
  - See novel-ralph-harness-design.md §3.2 and §3.4;
    docs/scripting-standards.md (line 678);
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_compile.py;
    novel_ralph_skill/commands/_desloppify.py;
    novel_ralph_skill/commands/_desloppify_ledger.py.
  - Success: a behavioural test drives each of the compile-write, rule-pack-read,
    and device-ledger-read exit-3 faults and asserts an actionable message naming
    the artefact and a remedy, with no raw `Errno`/`{exc}` text; the three call
    sites emit write-shaped or file-shaped sibling prose rather than the raw repr;
    and the compile, desloppify, and ledger suites stay green.
  - [x] 6.3.8.1.
    - Addendum (from audit:6.3.8 Findings 1-2; low). Collapse the four
      path-only file-fault formatters in `_state_load.py` onto a private
      `_file_fault_error(message)` builder and drop the dead `exc` parameter
      from the path-only formatters (no body reads it), then adjust the parity
      test to the trimmed signatures, removing the near-identical single-arm
      duplication and the misleading signature in one focused change.
      Lightweight addendum pass.
  - [x] 6.3.8.2.
    - Addendum (from audit:6.3.8 Finding 5; medium). Update the developers'
      guide exit-3 section (`docs/developers-guide.md`), which still reads "Two
      sibling formatters", to describe all five actionable formatters covered by
      6.3.8 — `_compile_write_error`, `_rule_pack_read_error`, and
      `_device_ledger_read_error` alongside `_state_input_error` and
      `_draft_read_error` — and their write-shaped/file-shaped remedies, so the
      guide no longer undercounts the formatters. Lightweight addendum pass.
  - [x] 6.3.8.3.
    - Addendum (from audit:6.3.8 Finding 6; low). Pin the actionable remedy
      wording for the three exit-3 file-fault arms by adding one stable
      remedy-substring assertion per arm (or a `_REMEDY_TOKENS` table) to the
      parity tripwire `tests/test_state_load_actionable_parity.py`, which today
      asserts only path-naming and no-raw-leak, so a regression dropping a
      remedy clause fails a test rather than passing silently. Lightweight
      addendum pass.
- [x] 6.3.9. Pin the developers'-guide contract restatement against the code with
  a drift-guard arm.
  - Step-task (source: review:6.3.7; severity: low). Serves the §6.3 hypothesis
    that the contract is "documented once without per-command drift": 6.3.7 pins
    `SKILL.md` against ADR-003, design §3.1, and the code, but the
    developers'-guide "shared JSON envelope" / "disambiguated exit codes"
    sections — which `SKILL.md` points at as its canonical source — are not
    themselves pinned by any test, leaving the fourth restatement copy unguarded.
    Add a grep/keyword drift-guard arm, following the repo's established
    prose-guard pattern, asserting the guide's exit-code and envelope-field
    vocabulary tracks the `ExitCode`, envelope-field, and `schema_version`
    source, so the last unguarded prose copy fails a test on drift and the §6.3
    "documented once" hypothesis is fully discharged.
  - Requires 6.3.7.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md (Table 2);
    docs/developers-guide.md ("shared JSON envelope" / "disambiguated exit
    codes"); novel_ralph_skill/contract/exit_codes.py;
    novel_ralph_skill/contract/envelope.py.
  - Success: a drift-guard arm fails if the developers'-guide exit-code table or
    envelope-field vocabulary diverges from the `ExitCode`, envelope-field, and
    `schema_version` source; the guard reuses the repo's established prose-guard
    pattern; no contract restatement copy remains unpinned by a test; and the
    docs and contract suites stay green.
  - [x] 6.3.9.1.
    - Addendum (from review:6.3.9 / audit:6.3.9; low). Cover the trailing-comma
      discard branch of `extract_brace_field_list`: the scanner helper documents
      that empty comma-split fragments (e.g. a trailing comma) are discarded via
      the `if field:` guard, but no unit test exercises that branch, so a
      regression removing it would pass every current test. Add one unit case
      planting `{a, b, }` and asserting `[a, b]`. Lightweight addendum pass.

## 7. Consolidate, harden, and reconcile the spine

This phase consolidates, hardens, and reconciles the deterministic spine
before any new feature work. It runs in order: first single-source the
duplicated implementations, so that hardening and documentation attach to one
canonical implementation rather than to copies that would re-diverge; then
harden the guards, detectors, and gates; then reconcile the documentation and
settle the open conventions. NOTE for the build workflow: fold post-merge
audit findings into the relevant step here (or a single debt task), filtered
by severity — do not spawn a new step per finding, which is what inflated the
earlier draft of this phase.

### 7.1. Single-source the machine-payload projections and envelopes

This step answers whether each machine-payload projection — the
compile-currency view, the reconciliation payload, and the finding-outcome
envelope — is produced by exactly one canonical function. Definition of done
for every task here: the duplication is removed, exactly one canonical
implementation survives under one name, it is documented as the single source
of truth, and a test pins it so it cannot silently re-fork.

- [x] 7.1.1. Extract a `compile_is_current` predicate and a single `compiled.md`
  path seam, and route the four consumers through them.
  - Reroute (source: audit:4.1.2; severity: low). The `MATCHES`-only
    content-polarity projection is hand-repeated at three sites
    (`done_predicate.compile_consistent`, `commands._compile.check_compiled`, and
    the `_novel_done` compile clause), and the `working/manuscript/compiled.md`
    location is constructed independently in `compile_model.py`, `_compile.py`
    (`_COMPILED_REL`), and the `done_predicate`/`_novel_done` modules. Extract a
    named `compile_is_current(verdict)` predicate and a `compiled_manuscript_path`
    / `COMPILED_REL` seam into `compile_model.py` (already the owner of the join
    rule), then have `check_compiled`, `compile_consistent`, and the `novel-done`
    compile clause consume them, so the agreement invariant the `--check`
    success criterion pins is structurally enforced rather than only test-pinned
    and `compiled.md`'s location has one definition. No behavioural change. This
    is cross-cutting compile-model DRY-and-layering hygiene, not the settled
    step-4.1 hypothesis where it was raised, so it is deferred here.
  - Requires 4.1.2.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    docs/issues/audit-4.1.2.md;
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/state/done_predicate.py;
    novel_ralph_skill/state/disk_evidence.py;
    novel_ralph_skill/commands/_compile.py.
  - Success: a named `compile_is_current` predicate over `CompiledComparison`
    lives once in `compile_model.py` and is consumed by `check_compiled`,
    `compile_consistent`, and the `novel-done` compile clause in place of their
    hand-written `is CompiledComparison.MATCHES` tests; the
    `working/manuscript/compiled.md` path and its working-relative token have one
    definition the four modules import; no behaviour changes; and every compile,
    done-predicate, and disk-evidence suite stays green.
- [x] 7.1.2. Consolidate the `CompiledComparison` absent-file projection prose
  into one authoritative docstring.
  - Reroute (source: audit:4.1.2; severity: low; carry-forward of audit-3.1.3
    Finding 3). The absent-file projection prose is now duplicated across four
    docstrings — `compiled_matches_drafts`, `compile_consistent`,
    `_check_compiled_matches_drafts`, and (since 4.1.2) `check_compiled`;
    audit-3.1.3 Finding 3 already proposed making the shared helper docstring
    authoritative and reducing each consumer to a one-sentence self-projection,
    and 4.1.2 added the fourth copy. Make `compiled_matches_drafts`'s docstring
    the single authoritative description of the three-valued verdict and the two
    opposite absent-file polarities, and trim the three consumers to a
    one-sentence note of which polarity they project. Doc-only; no behaviour
    change. This is cross-cutting documentation-DRY hygiene, not the settled
    step-4.1 hypothesis where it was raised, so it is deferred here.
  - Requires 3.1.3.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    docs/issues/audit-4.1.2.md; docs/issues/audit-3.1.3.md (Finding 3);
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/state/done_predicate.py;
    novel_ralph_skill/state/disk_evidence.py;
    novel_ralph_skill/commands/_compile.py.
  - Success: the three-valued verdict and the two opposite absent-file polarities
    are described authoritatively once in `compiled_matches_drafts`'s docstring;
    `compile_is_current` (consolidated in 7.1.1), `compile_consistent`,
    `_check_compiled_matches_drafts`, and `check_compiled` each carry only a
    one-sentence self-projection pointing at the authoritative docstring; no
    further full copy remains; and `make all` stays green.

- [x] 7.1.3. Extract a single `Reconciliation` payload projection and route the
  four arms through it.
  - Reroute (source: audit:6.2.13; severity: low). audit-2.3.2 Finding 2 recorded
    the four-site duplication of the `Reconciliation`-to-dict serialisation
    (`_render_reconciliation`, `_write_outcome`, `_refuse_outcome`, and the NONE
    arm) but, unlike the sibling `[word_counts]` theme (task 7.4.7) and the
    compile-projection theme (task 7.1), it was never promoted to a roadmap task;
    it remains open and untracked, and the 6.2.13 scenario exercises the `check`
    read-shape arm directly. A single `to_payload()` / `reconciliation_payload()`
    projection beside `Reconciliation` in `state/reconcile.py` — keeping the CQS
    read/write vocabulary split and the exit codes untouched — would stop `check`
    and `reconcile` drifting on payload shape. This serves the consolidation
    hypothesis (a canonical projection per the 8.1.5/7.1 precedent), not the
    step-6.2 surface hypothesis where it was raised, so it is rerouted here.
  - Requires 2.3.2.
  - See novel-ralph-harness-design.md §3.3 and §5.4;
    docs/issues/audit-2.3.2.md (Finding 2);
    novel_ralph_skill/state/reconcile.py.
  - Success: one `to_payload()` / `reconciliation_payload()` projection lives
    beside `Reconciliation` in `state/reconcile.py`; `_render_reconciliation`,
    `_write_outcome`, `_refuse_outcome`, and the NONE arm consume it rather than
    each spelling the `{action, discrepancies, detail}` shape; the CQS read/write
    vocabulary split and the exit-code policy are unchanged; no behaviour changes;
    and the check, reconcile, and disk-evidence suites stay green.
  - [x] 7.1.3.1. Drop the now-vestigial `action` parameter from `_write_outcome`.
    - Addendum (from review:7.1.3; low). After 7.1.3 routed `_write_outcome`
      through `reconciliation_payload`, its `action` parameter is no longer read
      by the body (the projection reads `reconciliation.action`); remove the
      parameter and simplify the two callers (`commands/_reconcile.py:299,308`),
      closing the gap where a caller could pass an `action` inconsistent with
      `reconciliation.action`. Lightweight addendum pass.
  - [x] 7.1.3.2. Replace US `serialize` with en-GB `serialise` in the developers'
    guide clean-pass section.
    - Addendum (from review:7.1.4; low). `docs/developers-guide.md:1425` carries
      `serialize`, a US spelling introduced by 7.1.3, violating the AGENTS.md en-GB
      Oxford convention; correct it to `serialise`. Lightweight addendum pass.

- [x] 7.1.4. Extract the shared finding-outcome envelope skeleton into a
  contract-package builder and route both projections through it.
  - Reroute (source: audit:8.1.3; severity: medium). After 8.1.3, `report_outcome`
    (`commands/_desloppify_report.py`) and `ledger_report_outcome`
    (`ledger/report.py`) are verbatim-identical in skeleton — the failed filter,
    the code ternary, and the `violations`/`findings`/`messages` assembly —
    differing only in the per-hit payload, the id accessor (`rule_id` versus
    `device_id`), extra result keys, and the clean-pass string. Without a shared
    builder the multi-pack surface (8.1.6/8.1.7) and any change to the
    violations-findings relationship must be kept in lockstep across two files by
    hand. This does not serve the step-8.1 hypothesis — the per-hit output
    contract is already settled — so it is rerouted here as cross-cutting
    maintainability. Extract the shared skeleton into a contract-package builder
    that injects each package's payload projection, id accessor, extra result
    keys, and clean-pass message, leaving the per-hit payload untouched. The
    exit-code-from-`failed` derivation tracked as addendum 8.1.3.2 folds into this
    builder if 7.1.4 lands after it; if 7.1.4 lands first, derive the code from
    the same `failed` list the builder filters.
  - Requires 8.1.2.
  - See novel-ralph-harness-design.md §4.4, §6.1, §6.2, and §6.3;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_desloppify_report.py;
    novel_ralph_skill/ledger/report.py.
  - Success: one shared contract-package builder owns the failed-filter,
    exit-code, and `violations`/`findings`/`messages` skeleton; both
    `report_outcome` and `ledger_report_outcome` consume it, injecting only their
    per-hit payload, id accessor, extra result keys, and clean-pass message; the
    per-hit payload projection is unchanged; the §3.2 exit-code contract and the
    slimmed clean-pass findings contract are preserved; and the desloppify and
    ledger suites (including the snapshot suites) stay green.
  - [x] 7.1.4.1. Add an end-to-end raw-JSON `result` key-order assertion per
    extra-result shape.
    - Addendum (from audit:7.1.4 Finding 1; low). The `result` key-order contract
      7.1.4 protects is guarded only at the pre-render dict level
      (`list(outcome.result)`); the e2e oracles `json.loads` stdout and the
      `.ambr` snapshots sort keys, so a stray `sort_keys=True` in `render_machine`
      would pass every suite while breaking the wire contract. Add one un-parsed
      stdout assertion per `extra_result` shape (rule-pack with
      `pack`/`total_words`, ledger without) to the desloppify/ledger e2e suites.
      Lightweight addendum pass.
  - [x] 7.1.4.2. Add a Hypothesis property pinning exit-code-from-`failed` over
    arbitrary findings vectors.
    - Addendum (from review:7.1.4; low). The four enumerated unit cases pin the
      builder's exit-code-from-`failed` contract today; add a Hypothesis property
      over arbitrary pass/fail findings vectors to harden the
      `build_finding_outcome` closure against future builder edits beyond the
      deterministic enumerable boundary. Lightweight addendum pass.

- [x] 7.1.5. Derive the envelope field order from the `Envelope` dataclass across
  the renderer and its test oracles.
  - Reroute (source: audit:6.3.7; severity: medium). Task 6.3.7 makes
    `dataclasses.fields(Envelope)` canonical for the `SKILL.md` copy of the
    contract, yet `render_machine` (`contract/envelope.py:143`) and its two test
    oracles `_FIXED_FIELD_ORDER` (`tests/test_contract_envelope.py:33`) and
    `ENVELOPE_KEY_ORDER` (`tests/cross_command_contract/__init__.py:81`) still
    hand-spell the same six-name order. Build the renderer's ordered mapping by
    iterating the dataclass fields and promote one shared `ENVELOPE_FIELD_ORDER`
    constant the two test tuples import, leaving one literal tripwire, so the
    field-order projection has a single canonical home. This serves the step-7.1
    machine-payload-projection hypothesis — each projection produced by exactly
    one canonical function — not the settled step-6.3 documentation hypothesis
    where it was raised.
  - Requires 6.3.7.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/contract/envelope.py (`render_machine`);
    tests/test_contract_envelope.py (`_FIXED_FIELD_ORDER`);
    tests/cross_command_contract/__init__.py (`ENVELOPE_KEY_ORDER`).
  - Success: `render_machine` builds its ordered mapping by iterating
    `dataclasses.fields(Envelope)` rather than a hand-spelled order; one shared
    `ENVELOPE_FIELD_ORDER` constant is imported by `_FIXED_FIELD_ORDER` and
    `ENVELOPE_KEY_ORDER` so exactly one literal tripwire survives; no module
    re-spells the six-name order; and the contract and cross-command suites stay
    green.
  - [x] 7.1.5.1. Register the envelope field-order projection row in the §7.1
    projection-docstring drift guard now 7.1.5 has merged.
    - Addendum (from review:7.1.6, audit:7.1.6; low; two near-identical proposals
      merged). 7.1.6 authored `test_projection_docstring_drift_guard.py` as an
      extensible registry and deferred 7.1.5's row to "when 7.1.5 lands"; add the
      `(authoritative, consumers, canonical_path, reexport_tail, table_markers)`
      row binding `ENVELOPE_FIELD_ORDER` to `render_machine` and the two test
      oracles so the consolidation is guard-enforced, not merely documented.
      Lightweight addendum pass.

- [x] 7.1.6. Settle the §7.1 authoritative-docstring + consumer self-projection
  convention once, with a reusable drift-guard.
  - Step task (source: audit:7.1.2 Findings 2, 3, 5; review:7.1.2; severity: low;
    near-identical proposals merged). This serves the step-7.1 hypothesis
    directly: the definition of done for every §7.1 task is that the surviving
    canonical projection "is documented as the single source of truth, and a test
    pins it so it cannot silently re-fork", yet 7.1.1/7.1.2 settled that pattern
    without a uniform cross-reference style or a drift-guard, so the
    documentation-and-test legs of the invariant are themselves un-single-sourced.
    Two of three consumers spell the authoritative target via the defining-module
    path (`novel_ralph_skill.state.compile_model.compiled_matches_drafts`) while
    `_compile.py`'s `check_compiled` and its module docstring use the re-export
    path (`novel_ralph_skill.state.compiled_matches_drafts`); both resolve, but
    the mixed spelling weakens the single-canonical-target intent and would
    dangle if the re-export were pruned. Fix the canonical cross-reference style
    to the defining-module form across the §7.1 consumers (compile-currency and
    reconciliation-payload projections), normalising the sibling
    `CompiledComparison`/`compile_is_current` mentions in `_compile.py` to match,
    and add a reusable docstring drift-guard helper that asserts the authoritative
    docstring is the single full copy and each consumer carries a resolving
    cross-reference rather than a re-enumerated projection table. Apply the
    convention and guard to the remaining §7.1 task (7.1.5) so each inherits the
    convention rather than re-deciding it. Doc-and-test only; no behaviour change.
  - Requires 7.1.2, 7.1.3, 7.1.4.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    docs/issues/audit-7.1.2.md (Findings 2, 3, 5);
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/state/done_predicate.py;
    novel_ralph_skill/state/disk_evidence.py;
    novel_ralph_skill/commands/_compile.py;
    tests/test_compile_model_seam.py.
  - Success: every §7.1 consumer names its authoritative target through the
    defining-module cross-reference path (no re-export-path or mixed spelling
    survives); a reusable drift-guard helper pins, for each consolidated
    projection, that exactly one authoritative docstring carries the full
    projection and each consumer carries only a resolving cross-reference (not a
    re-enumerated table); re-expanding any consumer's docstring or breaking a
    cross-reference reddens the guard; and the compile, done-predicate,
    disk-evidence, and reconcile suites stay green.

### 7.2. Single-source the loaders, builders, and scan primitives

This step answers whether the detection-pack loader-and-scan and the tomlkit
inline-table builder each have a single home. Definition of done for every
task here: the duplication is removed, exactly one canonical implementation
survives under one name, it is documented as the single source of truth, and a
test pins it so it cannot silently re-fork.

- [x] 7.2.1. Collapse the duplicated `tomlkit` inline-table builders onto one
  shared helper.
  - Reroute (source: audit:2.3.1; severity: low). `recount`'s
    `_inline_by_chapter` (`commands/_recount.py`) is the third copy of the same
    inline-table idiom, alongside `_inline` in `state/initial.py` — whose
    docstring already admits the drift — and `_inline` in the corpus builder
    (`tests/working_corpus/_builder.py`). A single state-package helper consumed
    by all three keeps the inline-table materialisation rule in one place,
    mirroring how `wordcount` centralised the counting rule. This is
    cross-cutting code hygiene, not the step-2.3 disk-re-derivation hypothesis
    where it was raised, so it is deferred here.
  - Requires 2.3.1.
  - See novel-ralph-harness-design.md §5.3;
    docs/adr-002-toml-round-trip-tomlkit.md.
  - Success: one `tomlkit` inline-table helper lives in the state package and is
    consumed by `recount`, `state/initial.py`, and the corpus builder; the
    initial-document docstring no longer flags a hand-copied twin; and the
    lossless round-trip and every current state and corpus test stay green.
  - [x] 7.2.1.1. Collapse the array-of-inline-tables `[[chapters]]` builder
    skeleton onto one shared helper.
    - Addendum (from audit:7.2.1, review:7.2.1; low; three near-identical
      proposals merged). 7.2.1 folded only the inner inline-table idiom into
      `build_inline_table`; the outer `tomlkit.array()` + `multiline(True)` +
      append-loop skeleton producing the four-key `[[chapters]]` array
      (`number`, `slug`, `title`, `target_words`) is still a two-site near-copy
      across `commands/_set_chapters.py` (`_chapter_array`) and
      `tests/working_corpus/_builder.py` (`_chapters_array`), explicitly
      deferred as Decision D-ARRAY-FOLLOWUP. Extract a state-package helper
      taking an ordered sequence of `(number, slug, title, target_words)`
      records and returning the multiline array, route both sites through it,
      pin it with a test, and update the developers' guide deferral note to cite
      this sub-task. Lightweight addendum pass.

- [x] 7.2.2. Consolidate the rule-pack and device-ledger TOML-loading and scan
  primitives onto shared, error-factory-parameterised helpers.
  - Reroute (source: audit:8.1.2; severity: medium). `_coerce` (an explicit
    "deliberate near-copy"), `_entries`, `_compile_pattern`,
    `_reject_duplicate_ids`, the `load_*` file-fault body, and the per-line
    `_scan_*` are duplicated near-verbatim across the `rulepack` and `ledger`
    packages, differing only in error type and noun. This does not serve the
    step-8.1 hypothesis — it is cross-cutting code-quality consolidation, not the
    per-novel-pack extension — so it is rerouted here. Extract shared coercion
    primitives parameterised on an error factory plus a shared `scan_pattern`,
    routing both packages through them while keeping each package's typed error
    channel (`RulePackError`/`RulePackFileError` versus
    `LedgerError`/`LedgerFileError`) and its device/rule-specific messages
    unchanged, so a third pack family inherits the primitives instead of
    cloning a third copy.
  - Requires 8.1.2.
  - See novel-ralph-harness-design.md §6.1, §6.2, and §6.3;
    novel_ralph_skill/rulepack/ (`_coerce.py`, `parse.py`, `detect.py`);
    novel_ralph_skill/ledger/ (`_coerce.py`, `parse.py`, `detect.py`).
  - Success: one shared module owns the coercion, entry-extraction,
    pattern-compilation, duplicate-id, file-fault, and per-line scan primitives;
    both the rule-pack and ledger packages consume them rather than carrying
    near-verbatim copies; each package's typed error type, exit-code mapping, and
    operator messages are unchanged; and the rule-pack and ledger suites stay
    green.
  - [ ] 7.2.2.1. Harden the `loaderkit` scan property test with an independent
    line-model oracle.
    - Addendum (from review:7.2.2; low). The current Hypothesis property
      recomputes the expected per-line hits with `splitlines()` — the same call
      `scan_pattern` uses — so it cannot catch a class of line-splitting
      regressions (a future move to `split("\n")` or a universal-newline edge
      case). Add a second property that derives the expected hits from an
      independent newline model, leaving the existing freeze property in place,
      so the line-attribution contract is pinned against the implementation's own
      splitting choice. Lightweight addendum pass.

- [x] 7.2.3. Relocate the shared scan shapes (`ScannedChapter`, `LineHit`) into
  `loaderkit` to finish the 7.2.2 consolidation.
  - Step-task (source: audit:7.2.2; severity: medium). Task 7.2.2 moved the
    shared scan *body* into the neutral `loaderkit` home but left its input and
    output types in `rulepack.detect`, so the ledger domain runtime-imports
    `LineHit` from the rule-pack domain (`ledger/detect.py:35`) and a hypothetical
    third pack family would have to as well — the exact sibling-to-sibling domain
    edge the neutral home was introduced to remove. It also makes
    `loaderkit/scan.py`'s "no `Rule`/`Device` knowledge" docstring untrue, because
    the primitive's signature is still typed against shapes that live in the
    rule-pack domain. This serves the step-7.2 hypothesis — that the
    detection-pack loader-and-scan primitives each have a *single* home — by giving
    the two neutral scan shapes that home rather than leaving them stranded in a
    consumer domain, completing the consolidation 7.2.2 began and deliberately
    deferred (the move was scoped out as a wider change; see
    docs/execplans/roadmap-7-2-2.md Constraints and Decision D-SCANTYPES). Relocate
    `ScannedChapter` and `LineHit` into `loaderkit`, route both detectors and the
    `loaderkit.scan` unit test at the neutral home, and fold in the low-severity
    tidy-ups the same pass naturally exposes: inline the thin duplicated
    `_scan_rule`/`_scan_device` wrappers, delete the dead
    `rulepack._coerce._require` (no caller), de-duplicate the triple-stated
    per-line scan docstring, and add a callback-contract test for
    `scan_pattern`'s `line_hit` factory.
  - Requires 7.2.2.
  - See novel-ralph-harness-design.md §6.1; docs/adr-003-shared-interface-contract.md;
    docs/execplans/roadmap-7-2-2.md (Constraints, Decision D-SCANTYPES);
    novel_ralph_skill/loaderkit/scan.py;
    novel_ralph_skill/rulepack/detect.py;
    novel_ralph_skill/ledger/detect.py.
  - Success: `ScannedChapter` and `LineHit` live in `loaderkit`; neither
    `loaderkit.scan` nor `ledger.detect` imports them from `rulepack.detect` (the
    runtime `ledger → rulepack` and the `TYPE_CHECKING` `loaderkit → rulepack`
    edges are gone); `loaderkit/scan.py`'s "no `Rule`/`Device` knowledge" docstring
    reads true; the thin `_scan_rule`/`_scan_device` wrappers and the dead
    `rulepack._coerce._require` are removed, the scan docstring is single-stated,
    and a `line_hit`-callback contract test pins `scan_pattern`; and the rule-pack,
    ledger, and `loaderkit` suites stay green.
  - [ ] 7.2.3.1. Generalise the `loaderkit` import-direction guard beyond
    `loaderkit.scan`.
    - Addendum (from review:7.2.3; low). The D-GUARD test
      `test_loaderkit_scan_imports_no_pack_domain` pins only `scan.py` against
      pack-domain imports, yet the neutral-leaf invariant (design §6/§6.3,
      ADR-003) holds for every `loaderkit` module (`coerce.py`, `load.py`,
      `__init__.py`); parametrise the guard to walk all of them so a future
      regression in any module is caught, not just one in `scan.py`. Lightweight
      addendum pass.
  - [ ] 7.2.3.2. Align `loaderkit/scan.py` docstrings with the post-7.2.3
    callback framing.
    - Addendum (from review:7.2.3; low). The module and `scan_pattern`
      docstrings still justify the `line_hit` callback as preventing import of a
      "pack-domain hit type", which is self-contradictory now `LineHit` lives in
      that module; retune both to the developers' guide's "free of any
      `Rule`/`Device` knowledge" framing. Lightweight addendum pass.

- [x] 7.2.4. Repoint the scan-shape stragglers off the `rulepack.detect`
  re-export and settle the re-export's fate.
  - Step-task (source: audit:7.2.3 Findings 1, 3; severity: medium). 7.2.3
    relocated `ScannedChapter`/`LineHit` into `loaderkit.scan`, but
    `commands/_desloppify.py` and two ledger tests
    (`tests/test_ledger_properties.py`, `tests/test_ledger_detect.py`) still
    import `ScannedChapter` through the `rulepack.detect` re-export, leaving the
    runtime `ledger → rulepack` (via the tests) and `command → rulepack`
    detection-shape edges the relocation set out to remove. Repoint every
    straggler — and the stale Sphinx `:class:` cross-references in
    `ledger/__init__.py`, `commands/_desloppify.py`, `tests/test_ledger_detect.py`,
    and `tests/test_desloppify_sourcing.py` (Finding 3) — at `loaderkit.scan`,
    then decide and document the fate of the `rulepack.detect` re-export
    (retain as a deliberate compatibility seam with a pinning test, or prune it
    and drop it from `__all__`). This serves the step-7.2 hypothesis directly —
    that each detection-pack loader-and-scan primitive has a *single* home — by
    completing the single-home consolidation 7.2.3 began but left partial.
  - Requires 7.2.3.
  - See novel-ralph-harness-design.md §6.1;
    docs/adr-003-shared-interface-contract.md;
    docs/execplans/roadmap-7-2-3.md (Decision D-SCANTYPES);
    novel_ralph_skill/rulepack/detect.py;
    novel_ralph_skill/loaderkit/scan.py;
    novel_ralph_skill/commands/_desloppify.py;
    novel_ralph_skill/ledger/__init__.py.
  - Success: no module or test imports `ScannedChapter` or `LineHit` through the
    `rulepack.detect` re-export — every consumer imports them from
    `loaderkit.scan`; the stale `rulepack.detect.ScannedChapter` Sphinx
    cross-references are repointed at `loaderkit.scan`; the `rulepack.detect`
    re-export's fate is recorded (kept with a pinning test, or pruned from
    `__all__`); and the rule-pack, ledger, desloppify, and `loaderkit` suites
    stay green.
  - [ ] 7.2.4.1. Note that `LineHit` survives as an unadvertised runtime
    attribute of `rulepack.detect`.
    - Addendum (from review:7.2.4; low). Post-prune,
      `hasattr(rulepack.detect, "LineHit")` is `True` even though `LineHit` is
      absent from `__all__`, because the detector constructs it at runtime in the
      `line_hit` lambda (Decision D-LINEHIT-RUNTIME). This is intentional and
      test-pinned, so a future reader could mistake the surviving attribute for
      an incomplete prune; add a one-line note to the developers' guide `loaderkit`
      section recording that `LineHit` remains an importable-but-unadvertised
      `rulepack.detect` attribute by design. Lightweight addendum pass.

### 7.3. Single-source the command facade, predicates, and writers

This step answers whether the command-facade and entry-point seams, the
done-predicate, and the multi-file mutator write each exist once. Definition
of done for every task here: the duplication is removed, exactly one canonical
implementation survives under one name, it is documented as the single source
of truth, and a test pins it so it cannot silently re-fork.

- [x] 7.3.1. Lift the shared state-sourcing seam out of `novel_state` into a
  dedicated module with a public `load_or_state_error`.
  - Reroute (source: audit:1.3.6 Finding 2; severity: medium).
    `_load_or_state_error` (underscore-private) plus `STATE_INPUT_ERRORS`,
    `WORKING_DIR_NAME`, `state_path`, and `working_dir` are imported across five
    sibling command modules (`_compile.py`, `_recount.py`, `_state_mutators.py`,
    `_novel_done.py`, `_desloppify.py`) and `stub.py`, making `novel_state.py` a
    de-facto shared-utility home behind a command facade; the private name
    misleads and a `novel-state` refactor risks silently breaking four commands.
    Extract them into a dedicated module (e.g. `_state_io.py` or
    `state/sourcing.py`) with a public `load_or_state_error`, continuing the
    single-home discipline of 1.3.3/1.3.4/1.3.6. This is cross-cutting command-
    layer DRY-and-layering hygiene, not the step-1.3 shared-envelope hypothesis
    where it was raised, so it is deferred here.
  - Requires 1.3.6.
  - See novel-ralph-harness-design.md §3.1 and §4;
    docs/adr-003-shared-interface-contract.md.
  - Success: the load-and-translate seam, the state-input exception-tuple, the
    `working/` directory name, and the `state_path`/`working_dir` accessors live
    in a dedicated module with a public `load_or_state_error`; the five sibling
    commands and `stub.py` import them from that neutral home rather than from
    `novel_state`; no command depends on the `novel_state` module for these
    seams; and every command suite stays green.
  - [ ] 7.3.1.1. Re-anchor the two surviving `state_sourcing.py:52-67` docstring
    citations to stable symbols rather than source line-number ranges.
    - Addendum (from review:7.3.1; trivial). The `resolved_working_dir`
      docstring at `state_sourcing.py:74` and the multiplexer-`main` docstring at
      `novel.py:153` cite the cwd-relative rule as the line range
      `state_sourcing.py:52-67`, which any header edit can silently invalidate and
      no test guards — the same drift class that broke the design-doc citation in
      fix round 1. Re-anchor both to the stable symbol (`working_dir` /
      `WORKING_DIR_NAME`, or the cwd-relative rule by name). Lightweight addendum
      pass against the 7.3.1 execplan.
  - [ ] 7.3.1.2. Correct Decision D9's Gate-2 wording in the 7.3.1 execplan
    record.
    - Addendum (from review:7.3.1; low). D9 lists `load_or_state_error` inside
      the Gate-2 alternation, but the implemented gate `novel_state\._[a-z_]*error`
      matches only the dot-underscore `novel_state._load_or_state_error` form,
      never the bare public `novel_state.load_or_state_error`; the A1 insurance
      grep is what closes that gap. Correct the D9 prose so the historical gate
      record reads true. Lightweight addendum pass against the 7.3.1 execplan.
- [x] 7.3.2. Collapse the multiplexer mount lines onto a registry-driven
  construction table.
  - Reroute (source: review:1.3.6; severity: low). This reroute was raised
    against the pre-ADR-007 surface, when four entry-point one-liners
    (`novel_state`, `novel_done`, `novel_compile`, `desloppify`) differed only by
    name and `build_app` source and could have collapsed onto a table keyed off
    `COMMAND_ENTRY_POINTS`. ADR 007 (task 1.2.15) since retired the four-script
    surface, `stub.py`, and the `COMMAND_ENTRY_POINTS` symbol, leaving a single
    `novel` multiplexer with one entry point (`novel.main`). The surviving
    repetition the reroute targets is therefore the five hand-copied mount lines
    in `build_multiplexer`, collapsed onto a single construction table keyed off
    the surviving `SUBCOMMAND_NAMES` registry (via the `_VERB_FOR_SUBCOMMAND`
    derivation) rather than the retired `COMMAND_ENTRY_POINTS` (execplan
    Decision D1). This serves the step-7.3 command-facade single-home
    hypothesis — one registry-driven home for the multiplexer's mount
    construction — not the step-1.3 shared-envelope hypothesis where it was
    raised. Coordinate with 7.3.1 so the table consumes the neutral
    state-sourcing seam.
  - Requires 1.3.6.
  - See novel-ralph-harness-design.md §4;
    docs/adr-007-command-surface-novel-multiplexer.md;
    novel_ralph_skill/commands/names.py (`SUBCOMMAND_NAMES`).
  - Success: the five hand-copied mount lines in `build_multiplexer` are produced
    from a single registry-driven construction table keyed off `SUBCOMMAND_NAMES`
    (via `_VERB_FOR_SUBCOMMAND`/`_SUBCOMMAND_FOR_VERB`) rather than re-spelling
    each mount verb inline; the public entry-point function name (`novel.main`),
    the single `[project.scripts]` target, and the import-laziness profile are
    preserved (or the laziness change is decided and recorded); and the
    multiplexer shape, behavioural-parity, and console-scripts e2e suites stay
    green.
  - [ ] 7.3.2.1. Replace the multiplexer import-laziness substring guard with an
    `ast` module-scope import walk.
    - Addendum (from audit:7.3.2 Finding 4 / review:7.3.2; low). The laziness
      guard in `tests/test_multiplexer_mount_table.py` asserts each leaf name is
      absent from the module source outside `_build_mount_table` by raw substring
      scan, which is wider than the real invariant (no module-scope leaf import)
      and false-fails the day a docstring or comment mentions a leaf module by
      name. Re-pin it with an `ast` walk over module-scope (`col_offset == 0`)
      `Import`/`ImportFrom` nodes — asserting no leaf is imported at module scope
      and each leaf is imported inside the `_build_mount_table` `FunctionDef` body
      — following the in-repo `ast` scanner pattern in
      `tests/_state_layout_scanner.py`. Lightweight addendum pass against the
      7.3.2 execplan.
  - [ ] 7.3.2.2. Tie the multiplexer test verb-sets back to the registry and
    collapse the redundant registered-mounts test.
    - Addendum (from audit:7.3.2 Findings 2 and 3; medium). The bare-verb set is
      hand-spelled as an inline literal in
      `tests/test_multiplexer_dispatch.py:47`, a fourth copy untied to the
      registry, and `test_build_multiplexer_registers_the_five_subcommands` there
      duplicates the stronger registry-tied
      `test_build_multiplexer_registers_exactly_the_table_verbs` in
      `tests/test_multiplexer_mount_table.py`. Drive the dispatch test's expected
      set from `set(novel._SUBCOMMAND_FOR_VERB)` (or repoint it at
      `set(novel._build_mount_table())`), retire or repoint the redundant
      registered-mounts test, and add a single guard that the
      `_VERB_MODULE_PAIRS`/`_OPERATIONS` fixture verb keys equal the registry's
      bare-verb set so no test surface drifts from the single registry. Lightweight
      addendum pass against the 7.3.2 execplan.
  - [ ] 7.3.2.3. Correct the developers'-guide mount-map reference and pin the
    observable mount order.
    - Addendum (from audit:7.3.2 Findings 1 and 5; low). The developers' guide
      (`docs/developers-guide.md:451-453`) names `_VERB_FOR_SUBCOMMAND` as the
      mount driver where `build_multiplexer` actually iterates
      `_SUBCOMMAND_FOR_VERB`, and the "ordered mapping in surface order" claim
      across the docstring, guide, and tests is asserted only by set-equality.
      Correct the guide to name the map the loop reads (or describe the order as
      `SUBCOMMAND_NAMES`/ADR 007 surface order), add one ordered assertion that
      the registered mount order equals `list(novel._SUBCOMMAND_FOR_VERB)`, and
      soften
      the `_build_mount_table` docstring so it does not imply the table's own
      iteration order is load-bearing. Lightweight addendum pass against the 7.3.2
      execplan.
- [x] 7.3.3. Consolidate the draft-read state-error wrapper shared by
  `wordcount`, `recount`, and `desloppify`.
  - Reroute (source: audit:6.1.1 Finding 1; severity: low). The
    `STATE_INPUT_ERRORS` → `StateInputError` draft-read idiom — call a disk
    reader, catch `STATE_INPUT_ERRORS`, and re-raise as `StateInputError` so an
    undecodable draft reaches exit `3` rather than escaping to the benign exit
    `1` — is now triplicated across `_wordcount._recount_or_state_error`,
    `_recount._recount_or_state_error`, and `_desloppify.source_chapters`, with
    `_wordcount` and `_desloppify` sharing an identical
    `f"cannot read chapter drafts: {exc}"` message string; `wordcount` added the
    third copy. Promote a single `read_drafts_or_state_error(working_dir,
    manifest)` helper (or a `state_error_on(...)` context manager) into the
    shared command home (`commands/novel_state.py` already exports
    `STATE_INPUT_ERRORS` and `_load_or_state_error`, or the dedicated
    state-sourcing module 7.3.1 carves out) and have all three call sites
    delegate to it, keeping the one exit-`3` fault-routing rule in a single
    place. This is cross-cutting command-layer DRY-and-layering hygiene, not the
    settled step-6.1 disk-derivation hypothesis where it was raised, so it is
    deferred here. Coordinate with 7.3.1 so the wrapper lands in the neutral
    state-sourcing home rather than re-pinning it to `novel_state`.
  - Requires 7.3.1.
  - See novel-ralph-harness-design.md §3.2 and §4.5;
    docs/issues/audit-6.1.1.md (Finding 1);
    novel_ralph_skill/commands/_wordcount.py;
    novel_ralph_skill/commands/_recount.py;
    novel_ralph_skill/commands/_desloppify.py.
  - Success: one `read_drafts_or_state_error` helper (or context manager) owns
    the catch-and-re-raise-as-`StateInputError` draft-read idiom; `wordcount`,
    `recount`, and `desloppify` delegate to it rather than each open-coding the
    `try/except STATE_INPUT_ERRORS` tail; the one exit-`3` fault-routing rule
    lives in a single place; and the wordcount, recount, and desloppify suites
    stay green.
- [ ] 7.3.4. Route the remaining command bodies through the shared
  `working_dir`/`state_path` accessors and a single `compiled.md` path accessor.
  - Reroute (source: audit:6.2.1 Findings 1-3; severity: medium). `_desloppify`
    and `_wordcount` bypass the documented single-source `working_dir()` /
    `state_path()` accessors with an inline
    `pathlib.Path(WORKING_DIR_NAME) / "state.toml"`, and `manuscript/compiled.md`
    is a five-site magic path (spelled two ways inside `_compile` alone, plus a
    duplicated `exists()` stat in `_novel_done` carrying an in-body race). This
    serves the step-7.3 command-facade single-home hypothesis — that the
    state-sourcing seams have explicit neutral homes so a refactor of one command
    cannot silently break the others — by routing the inline reconstructions
    through the `working_dir`/`state_path` accessors task 7.3.1 carves out, and
    by giving the `compiled.md` leaf a single owner and retiring the in-body
    race; it does not serve the step-6.2 combinatorial-surface hypothesis where
    it was raised. Coordinate with 7.4.3 so the `compiled.md` leaf is single-homed
    behind the same `compiled_path` accessor rather than a parallel one.
  - Requires 7.3.1 and 7.4.3.
  - See novel-ralph-harness-design.md §4.1 and §5.4;
    docs/issues/audit-6.2.1.md (Findings 1-3);
    novel_ralph_skill/commands/_desloppify.py;
    novel_ralph_skill/commands/_wordcount.py;
    novel_ralph_skill/commands/_novel_done.py.
  - Success: `_desloppify` and `_wordcount` source `state.toml` through the
    shared `working_dir`/`state_path` accessors rather than inline
    reconstructions; the `compiled.md` location has a single accessor owner that
    `_compile` and `_novel_done` consume; no site open-codes the path twice or
    re-stats the compile leaf in a racy in-body check; and the desloppify,
    wordcount, compile, and done-predicate suites stay green.
- [x] 7.3.5. Collapse the `novel.main`/`stub._drive` entry-point duplication
  into one shared drive seam.
  - Reroute (source: audit:1.2.12; severity: medium). `novel.main` and
    `stub._drive` share a byte-identical parse-`--human`, resolve-command-name,
    drive-via-`run` body; the duplication survives task 1.2.13, which removes
    the legacy `novel-x` entry points but not `_drive`. Generalise `_drive` to
    take a name resolver, or lift the shared body into a contract-level `drive()`
    helper, so the multiplexer entry point and the (1.2.13-residual) stub body
    consume one seam. This serves the step-7.3 command-facade single-home
    hypothesis — that the near-identical entry-point bodies collapse into one
    explicit home so a refactor of one cannot silently break the other — not the
    step-1.2 packaging-supports-invocation hypothesis where it was raised; it is
    a natural follow-on to 1.2.13. Coordinate with 7.3.2 so the
    registry-driven entry-point table and the multiplexer entry point share the
    one drive seam.
  - Requires 1.2.13 and 7.3.2.
  - See novel-ralph-harness-design.md §4;
    docs/adr-007-command-surface-novel-multiplexer.md;
    novel_ralph_skill/commands/novel.py (`main`);
    novel_ralph_skill/commands/stub.py (`_drive`).
  - Success: the parse-`--human`/resolve-name/drive-via-`run` body lives in one
    shared drive seam parametrised by the command-name resolver; `novel.main`
    and the residual `stub` entry-point body both delegate to it rather than
    re-spelling the plumbing; the import-laziness profile is preserved (or its
    change is decided and recorded); and the multiplexer, stub, and
    console-scripts suites stay green.
  - Done (see docs/execplans/roadmap-7-3-5.md). The `stub._drive` copy was
    already retired by 1.2.15 (ADR 007, commit 9e95c49), so no live duplicate
    survived to collapse; 7.3.5 delivered the constructive arm instead. The
    drive-via-`run` plumbing was lifted into the contract-level
    `contract.runner.drive` seam (keyword-scalar `command`/`working_dir`/`human`,
    `typ.NoReturn`), re-exported from the contract package, and `novel.main` now
    delegates to it rather than re-spelling the plumbing. The roadmap-1.3.6
    routing tripwire was migrated onto `novel.drive` (preserving the
    four-flag-contract assertion), a seam-forwards-to-`run` unit test pins the
    `main -> drive -> run` invariant, a structural guard
    (`tests/test_entry_point_single_home.py`) forbids re-inlining the plumbing in
    `main`, and a layering guard (`tests/test_contract_layering.py`) pins that the
    seam imports no `commands` module. Behaviour, exit codes, the absolute
    `working_dir` stamp, and the import-laziness profile are unchanged.
- [ ] 7.3.6. Relocate `WORKING_DIR_NAME` and the command-name vocabulary into
  the contract package.
  - Reroute (source: audit:1.2.12; severity: medium). `WORKING_DIR_NAME` is a
    contract-level constant living in the `novel_state` command module, and
    `contract/envelope.py` reaches up into `commands.names` for the envelope
    guard — a `contract`→`commands` layering inversion (documented as benign in
    sub-task 1.3.1.2, but not repaired). Relocate both the working-dir constant
    and the command-name vocabulary into the `contract` package so the envelope
    guard no longer depends on the command layer and no command depends on a
    sibling command module for the working-dir name; this also gives task 1.2.13
    a single contract-package edit for the legacy-name drop. This serves the
    step-7.3 command-facade single-home hypothesis — shared seams lifted into
    explicit, neutrally-named homes with the dependency direction made
    deliberate — not the step-1.2 packaging-supports-invocation hypothesis where
    it was raised. Coordinate with 7.3.1 so the state-sourcing module consumes
    the relocated `WORKING_DIR_NAME` rather than re-pinning it to `novel_state`.
  - Requires 1.3.1 and 7.3.1.
  - See novel-ralph-harness-design.md §3.1 and §4;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/novel_state.py (`WORKING_DIR_NAME`);
    novel_ralph_skill/contract/envelope.py;
    novel_ralph_skill/commands/names.py.
  - Success: `WORKING_DIR_NAME` and the command-name vocabulary live in the
    `contract` package; `contract/envelope.py` validates `command` against a
    contract-owned name set with no import of `commands.names`; no command
    depends on a sibling command module for the working-dir name; the
    `contract`→`commands` edge documented in 1.3.1.2 is removed; and the
    contract, command, registry, and envelope suites stay green.
- [ ] 7.3.7. Centralise the body-detected usage-error (exit-2) envelope in the
  contract layer.
  - Reroute (source: audit:2.2.4 Finding 1; severity: medium).
    `GateDraftingUsageError(EnvelopeMessagesError)` plus its `_set_gate_or_usage`
    adapter is now a near-verbatim second copy of
    `DesloppifyUsageError(EnvelopeMessagesError)` plus `_scan_or_usage`, and the
    exit-2 `CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages)
    or [str(exc)])` construction is duplicated at three sites
    (`_desloppify.py:256-258`, `_desloppify.py:343-345`,
    `_gate_drafting_mutators.py:204-206`). Lift the shared shape into the
    `contract` layer — a `BodyUsageError(EnvelopeMessagesError)` base (or marker)
    plus one `usage_error_outcome(exc)` helper both command modules call — so the
    exit-2 envelope has a single tested home alongside the centralised
    load/refuse helpers, while each module keeps a thin domain subclass for its
    docstring-level trigger. This serves the step-7.3 command-facade single-home
    hypothesis — the shared exit-2 envelope seam lifted into an explicit,
    neutrally-named home so a refactor of one command cannot silently break the
    others — not the settled step-2.2 write-discipline hypothesis where it was
    raised. Do it before a third command module copies the pattern again.
  - Requires 1.3.4.
  - See novel-ralph-harness-design.md §3.2 and §4;
    docs/adr-003-shared-interface-contract.md;
    docs/issues/audit-2.2.4.md (Finding 1);
    novel_ralph_skill/contract/errors.py;
    novel_ralph_skill/commands/_gate_drafting_mutators.py;
    novel_ralph_skill/commands/_desloppify.py.
  - Success: a `BodyUsageError` base and one `usage_error_outcome(exc)` helper
    live in the `contract` layer; the `set-gate` and `desloppify` usage adapters
    delegate to the shared helper rather than each re-spelling the exit-2
    `CommandOutcome`; the exit-2 envelope construction lives in exactly one
    place; a unit test pins the shared helper's envelope; and the gate/drafting,
    desloppify, and contract suites stay green.
- [ ] 7.3.8. Hoist the spaced-name-to-verb derivation into `names.py` and route
  `novel.py` and the e2e suite through it.
  - Reroute (source: audit:1.2.15; severity: medium; the audit:1.2.13 proposal it
    reproduces folded in). The `name.split(" ", 1)[1]` verb-extraction idiom is
    duplicated across `novel_ralph_skill/commands/novel.py:47` and
    `tests/test_console_scripts_e2e.py:69,123`, outside the documented
    single-source-of-truth registry. audit:1.2.13 already flagged this and
    proposed a `verb_for`/`SUBCOMMAND_VERBS` accessor; 1.2.15 reproduced the idiom
    rather than consolidating it, so the debt has persisted across two tasks. Add
    the accessor to `names.py` and route the dispatcher and the e2e suite through
    it, so the verb derivation lives once in the registry. This serves the
    step-7.3 command-facade single-home hypothesis — the command facade's shared
    seams lifted into explicit, neutrally-named homes — not the step-1.2
    packaging-supports-invocation hypothesis where it was raised; it is a natural
    follow-on to the registry consolidation.
  - Requires 1.2.15.
  - See novel-ralph-harness-design.md §4;
    docs/adr-007-command-surface-novel-multiplexer.md;
    novel_ralph_skill/commands/names.py;
    novel_ralph_skill/commands/novel.py;
    tests/test_console_scripts_e2e.py.
  - Success: a `verb_for`/`SUBCOMMAND_VERBS` accessor lives in `names.py`;
    `novel.py` and `test_console_scripts_e2e.py` derive each subcommand verb
    through it rather than re-spelling `split(" ", 1)[1]`; no spaced-name-to-verb
    split survives outside the registry; and the multiplexer, console-scripts, and
    registry suites stay green.
- [ ] 7.3.9. Unify the desloppify and ledger pack-detect pipelines onto one
  shared seam.
  - Reroute (source: audit:6.3.3 Finding 2; severity: low). `_desloppify` and
    `_desloppify_ledger` run the same load → content-error → file-error →
    source-chapters → detect → report pipeline with verbatim-copied comment
    blocks, differing only in three substitutions, so a future load-error-contract
    change must touch both with no guard they stay in step. Lift the shared
    pipeline into one seam parametrised by the three differing substitutions, with
    each command supplying only those. This serves the step-7.3 command-facade
    single-home hypothesis — shared command-body seams lifted into one explicit
    home so a refactor of one cannot silently break the other — not the settled
    step-6.3 contract-uniformity hypothesis where it was raised.
  - Requires 6.3.3.
  - See novel-ralph-harness-design.md §4 and §5.4;
    docs/issues/audit-6.3.3.md (Finding 2);
    novel_ralph_skill/commands/_desloppify.py.
  - Success: one shared seam owns the desloppify load → content-error →
    file-error → source-chapters → detect → report pipeline; `_desloppify` and
    `_desloppify_ledger` supply only the three differing substitutions rather than
    each re-spelling the body and its comment blocks; no verbatim pipeline copy
    survives; and the desloppify suites stay green.

- [ ] 7.3.10. Guard the done-predicate prose consolidation with a fence-scanning
  regression test.
  - Reroute (source: audit:6.2.3 / review:6.2.3; severity: medium; two
    near-identical proposals merged — a coarse `grep -rn "novel_predicate"
    skill/` CI guard and a richer fence-scanning test). Task 6.2.3 reduced both
    prose copies of the predicate to pointers at `novel-done`, but unlike the
    analogous state-layout prose guard (`tests/test_state_layout_reference.py`)
    there is no test stopping `SKILL.md` or `done-conditions.md` from
    re-restating the predicate; the single-source invariant is protected only by
    a one-time manual grep, so an unguarded consolidation can silently regress the
    two-source drift design §8 records as closed. Add a guard, modelled on the
    state-layout fence scanner, that asserts no prose copy of the `novel_predicate`
    body (or an equivalent clause re-enumeration) survives in the skill files, so
    a future edit reintroducing a divergent copy fails a test. This is
    cross-cutting documentation-truthfulness hardening, not the settling step-6.2
    combinatorial-surface hypothesis where it was raised, so it is deferred here.
  - Requires 6.2.3.
  - See novel-ralph-harness-design.md §8;
    docs/execplans/roadmap-6-2-3.md (Constraints 5-6, the scoped success grep);
    tests/test_state_layout_reference.py (the analogous prose guard).
  - Success: a regression test asserts no prose copy of the done predicate
    survives in `skill/` (the `grep -rn "novel_predicate" skill/` invariant is
    test-enforced, not manual); a planted re-statement of the predicate body in
    `SKILL.md` or `done-conditions.md` fails the guard; and the suite stays green.
- [ ] 7.3.11. Sweep the closed-work records for superseded `novel_predicate`
  references and annotate them as superseded by `novel-done`.
  - Reroute (source: review:6.2.3; severity: low). Task 6.2.3 deliberately left
    the `novel_predicate` mentions in the completed-work records
    (`docs/roadmap.md` addenda 3.1.1.1/3.1.1.2; `docs/execplans/roadmap-3-1-1*.md`)
    out of scope (its Constraints 5-6) so the historical record stayed intact.
    They are harmless historically but a future reader may follow them to a
    deleted symbol; a separate, clearly-scoped housekeeping pass can add a
    "superseded by `novel-done`" note beside each without gutting the historical
    record. This is cross-cutting documentation-truthfulness hygiene on closed
    records, not the settling step-6.2 hypothesis where it was raised, so it is
    deferred here.
  - Requires 6.2.3.
  - See docs/execplans/roadmap-6-2-3.md (Constraints 5-6, the out-of-scope
    closed-work records); docs/roadmap.md (the 3.1.1.1/3.1.1.2 addenda);
    docs/execplans/roadmap-3-1-1.md.
  - Success: each surviving `novel_predicate` reference in the closed-work
    records carries a brief "superseded by `novel-done`" annotation pointing a
    future reader at the live source of truth; no historical record is gutted or
    renumbered; and `make markdownlint` and `make nixie` stay green.
- [ ] 7.3.12. Add a shared clause-completeness assertion helper for `novel-done`'s
  done-predicate result.
  - Reroute (source: review:6.2.2; severity: low). Several suites (6.2.1, 6.2.2)
    assert `novel-done`'s six done clauses via `all(result.values())` or
    individual flags, which pass vacuously if a clause key is dropped or renamed.
    A shared helper that also pins the expected clause-key set would make a
    dropped or renamed clause fail loudly rather than passing silently. This
    serves the step-7.3 hypothesis — keeping the done-predicate single-source
    consolidation drift-free by an automated guard — by extending the same
    drift-proofing to the clause-key set the suites assert against, so the §4.2
    contract is hardened across suites; it is cross-cutting, not specific to one
    completed task, so it is deferred here. Add a shared assertion helper that
    pins the canonical clause-key set and have the done-predicate suites use it.
  - Requires 6.2.3.
  - See novel-ralph-harness-design.md §4.2;
    docs/developers-guide.md (the done-clause table);
    docs/issues/audit-6.2.2.md.
  - Success: a shared assertion helper pins the canonical done-clause key set;
    the 6.2.1 and 6.2.2 done-predicate suites assert through it rather than over
    `all(result.values())` alone; a dropped or renamed clause key fails the helper
    loudly; and the done-predicate suites stay green.

- [ ] 7.3.13. Route uncaught I/O faults in the multi-file mutators to the exit-3
  envelope channel.
  - Reroute (source: review:2.2.3; severity: minor). All multi-file mutators
    (`set-chapters`, `reconcile`, `recount`) let an `OSError` during their
    mid-turn writes escape `contract/runner.py::run`, so an operator hitting a
    disk-full or permission fault sees a raw Python traceback and exit 1 instead
    of a structured exit-3 envelope; the torn-turn `[pending_turn]` discipline
    keeps the state recoverable, but the failure UX is poor and inconsistent with
    the contract. This is cross-cutting reliability hardening of the shared write
    seam, not the settled step-2.2 lossless-and-atomic hypothesis where it was
    raised, so it is deferred here. Wrap the write seam so an I/O fault routes to
    `StateInputError` (exit 3) with a recovery hint pointing at `reconcile`.
  - Requires 2.2.1.
  - See novel-ralph-harness-design.md §3.2, §3.4, and §5.3;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/contract/runner.py;
    novel_ralph_skill/state/document.py.
  - Success: an `OSError` during a multi-file mutator's mid-turn write is reported
    as a structured exit-3 envelope with a recovery hint pointing at `reconcile`
    rather than a raw traceback and exit 1; `set-chapters`, `reconcile`, and
    `recount` share the one fault-routing rule; and a fault-injection test proves
    the envelope for each.
- [ ] 7.3.14. Guard the multi-file mutators against overwriting a foreign
  uncleared `[pending_turn]`.
  - Reroute (source: audit:2.2.3; severity: low). `open_pending_turn`
    (`state/document.py`) unconditionally overwrites any existing
    `[pending_turn]`, so a multi-file mutator (now `set-chapters` as well as
    `reconcile`) can silently clobber a different operation's torn-turn record,
    losing the recovery evidence the next turn needs. This is cross-cutting
    write-seam reliability hardening of a pre-existing posture surfaced by 2.2.3,
    not the settled step-2.2 lossless-and-atomic hypothesis where it was raised,
    so it is deferred here. Add a shared `assert_no_pending_turn` /
    refuse-with-exit-3 precondition so a mutator declines to open its own record
    over a foreign uncleared one and directs the operator at `reconcile`.
  - Requires 2.2.1 and 2.3.2.
  - See novel-ralph-harness-design.md §3.4 and §5.4;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/state/document.py.
  - Success: a multi-file mutator invoked over an uncleared `[pending_turn]` left
    by a different operation refuses with exit 3 and a recovery hint rather than
    overwriting the record; a mutator re-opening its own matching record is
    unaffected; and a behavioural test proves both the refusal and the preserved
    foreign record.
- [ ] 7.3.15. Extract a shared timestamped `log.md` receipt-append helper for the
  multi-file mutators.
  - Reroute (source: audit:2.2.3; severity: medium). `set-chapters` (2.2.3) and
    `reconcile` (2.3.2) carry near-identical private `_append_receipt`
    (`commands/_set_chapters.py`) and `_append_recovery_entry`
    (`commands/_reconcile.py`) helpers differing only in the operation prefix, and
    the `set-chapters` docstring already admits it mirrors `reconcile`'s.
    Centralizing a single `append_log_receipt` seam in `state/document.py` removes
    the duplication and gives the next multi-file mutator a ready,
    contract-correct seam. This is cross-cutting write-seam DRY hygiene, not the
    settled step-2.2 lossless-and-atomic hypothesis where it was raised, so it is
    deferred here.
  - Requires 2.2.3 and 2.3.2.
  - See novel-ralph-harness-design.md §3.4 and §5.3;
    docs/adr-002-toml-round-trip-tomlkit.md;
    novel_ralph_skill/state/document.py;
    novel_ralph_skill/commands/_set_chapters.py;
    novel_ralph_skill/commands/_reconcile.py.
  - Success: one `append_log_receipt` helper in `state/document.py` owns the
    timestamped `log.md` append; `set-chapters` and `reconcile` delegate to it
    rather than each carrying a private copy; the operation-prefix difference is
    a parameter rather than a duplicated body; and the set-chapters and reconcile
    suites stay green.

- [ ] 7.3.16. Extract a higher-order validate-before-persist helper for the five
  state mutators.
  - Reroute (source: audit:1.2.17; severity: low). `set_cursor` and the four
    gate/drafting mutators in `novel_ralph_skill/commands/_state_mutators.py`
    repeat a verbatim load → structural-proof → edit → re-view →
    refuse-if-incoherent → write skeleton, differing only in the edit step and
    the result shape, so the validate-before-persist ordering and the
    structural-completeness proof live in five places at once. Extract a
    higher-order helper (or context manager) so each mutator supplies only its
    edit closure and result, keeping per-mutator preconditions as an optional
    pre-edit hook. This serves the step-7.3 mutator-single-home hypothesis —
    one home for the validate-before-persist skeleton — not the step-1.2
    packaging-supports-invocation hypothesis where it was raised; it is
    cross-cutting mutator-layer DRY hardening, deferred here.
  - Requires 2.2.1.
  - See novel-ralph-harness-design.md §3.4 and §5.4;
    docs/adr-001-deterministic-judgemental-boundary.md;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_state_mutators.py.
  - Success: one higher-order helper owns the load → structural-proof → edit →
    re-view → refuse-if-incoherent → write skeleton; `set_cursor` and the four
    gate/drafting mutators each supply only their edit closure, result shape, and
    optional precondition hook rather than re-spelling the skeleton; the
    refuse-on-incoherence behaviour is unchanged; and every mutator suite stays
    green.
- [ ] 7.3.17. Close the `_state_mutators` re-export hop and make the
  single-state-sourcing-home property a structural import-graph guard.
  - Reroute-into-step (sources: audit:7.3.1 Findings 2-3; review:7.3.1, merging
    the four near-identical "structural import-graph gate" proposals; severity:
    medium). After 7.3.1 the seam lives in `state_sourcing`, but `_recount` and
    `_reconcile` still reach the `state_path`/`working_dir` accessors through a
    second-hop re-export — `_state_mutators.py` re-exports them as
    `_state_path`/`_working_dir` (`__all__` lines 71-73) and the two consumers
    import them from `_state_mutators`, not from `state_sourcing`. This swaps the
    retired `novel_state` façade for a fresh `_state_mutators` one and partially
    defeats 7.3.1's single-home goal. The structural guard
    `tests/test_state_sourcing_home.py` only forbids importing a seam symbol from
    `novel_state`; it does not flag a seam accessor imported from
    `_state_mutators`, and — because it resolves only fully-qualified absolute
    imports — it is blind to relative-import and re-pin forms. This serves the
    step-7.3 command-facade single-home hypothesis directly: the state-sourcing
    seam must exist exactly once, with the single-home property mechanically
    pinned rather than policed phrase-by-phrase across four token-scoped prose
    gates. Repoint `_recount` and `_reconcile` at `state_sourcing`, drop the
    `_state_path`/`_working_dir` re-export from `_state_mutators`, and generalise
    `test_state_sourcing_home` to resolve relative and absolute imports and walk
    the `_state_mutators` re-export tail so it flags any command module importing
    a seam accessor from anywhere but `state_sourcing`. This is the structural
    alternative Wafflecat raised in 7.3.1 round 4 and the plan recorded as a
    7.3.6 candidate; it warrants its own plan and review because it rewires
    imports across modules and rewrites the structural test, so it is filed as a
    full task here rather than a lightweight addendum.
  - Requires 7.3.1.
  - See novel-ralph-harness-design.md §3.1 and §4;
    docs/adr-003-shared-interface-contract.md;
    docs/execplans/roadmap-7-3-1.md (Decision D10; Risks; the WI5 gate block);
    novel_ralph_skill/commands/_state_mutators.py;
    novel_ralph_skill/commands/_recount.py;
    novel_ralph_skill/commands/_reconcile.py;
    tests/test_state_sourcing_home.py.
  - Success: `_recount` and `_reconcile` import `state_path`/`working_dir`
    directly from `state_sourcing`; `_state_mutators` no longer re-exports the
    `_state_path`/`_working_dir` accessors; the structural home guard resolves
    both relative and absolute imports and walks the `_state_mutators` re-export
    tail, flagging any command module that imports a seam accessor from anywhere
    but `state_sourcing`; re-pinning a seam accessor onto any non-`state_sourcing`
    home reddens the guard; and the mutator, recount, reconcile, and
    state-sourcing-home suites stay green.

### 7.4. Single-source chapter-draft sourcing, word-count, and disk-evidence

This step answers whether chapter-draft sourcing, the word-count single-source
seams, and the disk-evidence predicates each have one canonical
implementation. Definition of done for every task here: the duplication is
removed, exactly one canonical implementation survives under one name, it is
documented as the single source of truth, and a test pins it so it cannot
silently re-fork.

- [ ] 7.4.1. Collapse the desloppify and wordcount chapter-draft readers onto
  one shared helper.
  - Reroute (source: audit:5.1.2; severity: medium). `_chapter_text`
    (`commands/_desloppify.py`) and `_chapter_word_count`
    (`state/wordcount.py`) each derive the `chapter-NN/draft.md` path and absorb
    only `FileNotFoundError` as an undrafted chapter, so the design's
    "cannot drift" guarantee currently rests on two hand-kept copies; a shared
    `read_chapter_draft` helper in the state package makes the cross-module claim
    structurally true and is also wanted by the forthcoming `wordcount`
    surface (§4.5). This is cross-cutting DRY hygiene, not the settled step-5.1
    hypothesis where it was raised, so it is deferred here.
  - Requires 5.1.2 and 2.3.1.
  - See novel-ralph-harness-design.md §4.1 and §4.5;
    docs/execplans/roadmap-5-1-2.md.
  - Success: one `read_chapter_draft` helper owns the `chapter-NN/draft.md` path
    and the `FileNotFoundError`-as-absent boundary, both `desloppify` and
    `wordcount` consume it, and the desloppify and wordcount suites stay green.
- [ ] 7.4.2. Consolidate the open-coded `chapter-NN` directory-name convention
  onto one shared production helper.
  - Reroute (source: audit:2.3.3; severity: low). The
    `chapter-{number:02d}` directory-name idiom is open-coded across
    `state/disk_evidence.py` (`_chapter_dir_name`), `state/wordcount.py`, and
    `commands/_desloppify.py` (state-layout.md caps the width at two digits / 99
    chapters), so a future width or prefix change risks being applied
    inconsistently. A single shared directory-name helper in the state package,
    consumed by all three sites, removes the skew risk. This is cross-cutting
    production DRY hygiene serving the step-7.4 "express the chapter-draft
    sourcing rule once and share it" hypothesis — the directory-name segment the
    `read_chapter_draft` reader (7.4.1) derives — not the step-2.3
    disk-re-derivation hypothesis where it was raised. Coordinate with 7.4.1 so
    the shared reader consumes this helper rather than re-deriving the segment.
  - Requires 2.3.1 and 5.1.2.
  - See novel-ralph-harness-design.md §4.1 and §4.5;
    skill/novel-ralph/references/state-layout.md (the two-digit chapter width).
  - Success: one shared `chapter-NN` directory-name helper lives in the state
    package and is consumed by `disk_evidence.py`, `wordcount.py`, and
    `_desloppify.py` (and by the 7.4.1 `read_chapter_draft` reader); no site
    open-codes `chapter-{number:02d}`; and the state, desloppify, and wordcount
    suites stay green.
- [ ] 7.4.3. Single-home the `manuscript/` directory segment and the
  `compiled.md` leaf behind shared `manuscript_dir`/`compiled_path` accessors.
  - Reroute (source: audit:4.1.1; severity: medium). The `"manuscript"` segment
    and the `compiled.md` / `chapter-NN/draft.md` leaf paths are rebuilt ad hoc
    across `_compile.py`, `disk_evidence.py` (×3), `compile_model.py`,
    `wordcount.py`, and `_desloppify.py` (only `_chapter_dir_name` is already
    extracted), so the write-path-to-detector contract — the literal
    `"manuscript"`/`"compiled.md"` shared by the write path and the
    `compiled-matches-drafts` §5.4 detector — is enforced solely by the
    round-trip-oracle test, not a shared accessor; a relocation would need every
    site touched and a missed one would silently diverge. This serves the
    step-7.4 hypothesis — expressing the disk-path sourcing rule once and
    sharing it — by giving the `manuscript/`/`compiled.md` segments the same
    single-homed accessor treatment as the chapter-draft reader (7.4.1) and the
    `chapter-NN` directory-name helper (7.4.2), all in `state/_disk_paths.py`.
    It does not serve the settled step-4.1 deterministic-compilation hypothesis
    where it was raised — the paths already round-trip correctly and the
    contract holds — so it is rerouted here. Coordinate with the audit:4.1.1
    Finding 2 follow-up so the `_COMPILED_REL` snapshot token is derived from the
    same accessor rather than authored independently.
  - Requires 4.1.1 and 2.3.1.
  - See novel-ralph-harness-design.md §4.1, §4.3, and §5.4;
    docs/issues/audit-4.1.1.md (Finding 1, Finding 2);
    novel_ralph_skill/state/_disk_paths.py.
  - Success: `manuscript_dir(working_dir)` and `compiled_path(working_dir)`
    accessors live in `state/_disk_paths.py` beside `_chapter_dir_name`;
    `_compile.py`, `disk_evidence.py`, `compile_model.py`, `wordcount.py`, and
    `_desloppify.py` route through them; no site open-codes the `"manuscript"`
    segment or the `compiled.md` leaf; the write/detector path contract is a
    code-level single source of truth rather than a test-only invariant; and the
    compile, state, desloppify, and wordcount suites stay green.
- [ ] 7.4.4. Single-home the `reviews/` directory segment behind a shared
  `reviews_dir` accessor in `state/_disk_paths.py`.
  - Reroute (source: audit:3.1.1; severity: medium). The 3.1.1 done predicate
    added a `reviews/` knitting-review read, so the `reviews/` segment now joins
    the `manuscript/`/`compiled.md` leaves that task 7.4.3 single-homes — rebuilt
    by hand wherever a command reads `working/reviews/knitting-NN.md` rather than
    routed through one accessor. This serves the step-7.4 hypothesis —
    expressing the disk-path sourcing rule once and sharing it — by giving
    `reviews/` the same single-homed `_disk_paths.py` treatment as
    `manuscript_dir`/`compiled_path` (7.4.3) and the `chapter-NN` helper
    (7.4.2), not the settled step-3.1 done-predicate hypothesis where it was
    raised. Coordinate with 7.4.3 so the `manuscript/`, `compiled.md`, and
    `reviews/` accessors land as one coherent disk-path layout in
    `_disk_paths.py`.
  - Requires 7.4.3 and 3.1.1.
  - See novel-ralph-harness-design.md §4.1, §4.2, and §5.4;
    docs/issues/audit-3.1.1.md (Finding 1);
    novel_ralph_skill/state/_disk_paths.py.
  - Success: a `reviews_dir(working_dir)` accessor lives in `state/_disk_paths.py`
    beside `manuscript_dir`/`compiled_path`; every site reading
    `working/reviews/` routes through it; no site open-codes the `"reviews"`
    segment; and the done-predicate, compile, state, and disk-evidence suites
    stay green.
- [ ] 7.4.5. Carry a compile-present companion from the done predicate so the
  command layer stops re-statting `compiled.md`.
  - Reroute (source: audit:3.1.2; severity: low). `_novel_done` stats
    `manuscript/compiled.md` existence three times per run
    (`compile_consistent`, `_sole_stale_compile`, `_failed_clause_message`) to
    reconstruct *why* `compile_consistent` is false, because `DoneClauses`
    carries only the six clause booleans. Carrying a `compiled_present`
    companion (or a small `CompileVerdict`) on the predicate result would let the
    command layer read a field rather than re-statting disk. This serves the
    step-7.4 hypothesis — expressing each disk-sourcing rule once so it cannot
    be re-derived inconsistently — by collapsing the three `_novel_done` compile
    stats onto one predicate-carried fact; it does not serve the settled step-3.1
    done-predicate hypothesis where it was raised, and it pairs naturally with the
    `compiled_path` accessor work (7.4.3).
  - Requires 7.4.3 and 3.1.2.
  - See novel-ralph-harness-design.md §4.2;
    docs/issues/audit-3.1.2.md;
    novel_ralph_skill/commands/_novel_done.py.
  - Success: the done-predicate result carries a single `compiled_present`
    companion (or `CompileVerdict`); `_novel_done`'s `_sole_stale_compile` and
    `_failed_clause_message` read that field rather than re-statting
    `compiled.md`; no command-layer site stats the compile leaf more than once
    per run; and the done-predicate and `novel-done` suites stay green.

- [ ] 7.4.6. Carve the disk-evidence predicates out of `_oracle.py` into an
  `_oracle_disk.py` sibling and thread one per-invocation `state.toml` read.
  - Reroute (source: audit:2.3.3 / review:2.3.3; severity: medium). `_oracle.py`
    is at 399 of 400 lines after task 2.3.3, and the next corpus category would
    breach the `max-module-lines` cap and AGENTS.md file-size rule mid-task. A
    planned carve-out into an `_oracle_disk.py` sibling restores headroom and
    groups the disk-vs-disk checks (`by-chapter-sum`, `manifest-disk-bijection`,
    `done-flag-without-draft`, `pending-turn-cleared`, `compiled-matches-drafts`,
    `word-counts-match-drafts`). Fold the review:2.3.3 read-consolidation into the
    same move: each of these predicates currently re-parses the materialised
    `state.toml`, so as they move, parse it once per `corpus_check` and pass the
    decoded tables into the carved helpers (the production `disk_evidence.py`
    twin already takes a parsed `State` and needs no mirror). This is
    cross-cutting test-maintainability hardening, not the step-2.3
    disk-re-derivation hypothesis where it was raised, so it is deferred here.
    Coordinate with step 7.5 so the cap-driven corpus restructuring is done once.
  - Requires 2.3.3.
  - See novel-ralph-harness-design.md §5.4 and §9; docs/developers-guide.md
    ("The `working/` fixture corpus"); docs/execplans/roadmap-2-3-3.md.
  - Success: the disk-evidence predicates live in a focused `_oracle_disk.py`
    sibling, `_oracle.py` is back under the 400-line cap with headroom for the
    next category, the disk-evidence helpers consume one per-invocation
    `state.toml` parse rather than re-reading it per predicate, and every current
    corpus agreement suite stays green.

- [ ] 7.4.7. Consolidate the `[word_counts]` write across recount and reconcile
  onto one shared validated writer.
  - Reroute (source: audit:2.3.5 / audit:2.3.4; severity: medium). The two-line
    `[word_counts]` write plus its validate-before-persist tail is open-coded at
    three sites across `commands/_recount.py` and `commands/_reconcile.py`, and
    `_recount_edit`/`_pending_turn_edit` are near-identical recount closures
    (audit-2.3.5 Findings 1-3, re-flagged in audit-2.3.4). Task 2.3.5 pinned the
    single authoritative `current` rule, yet three copies enact it, so a future
    change skews easily. A shared `_write_word_counts_validated` helper gives the
    rule one enactment site and collapses the two near-identical reconcile
    closures (the function-local `disk_word_counts` import is naturally fixed in
    the same pass). This is cross-cutting code hygiene, not the step-2.3
    disk-re-derivation hypothesis where it was raised, so it is deferred here.
  - Requires 2.3.5.
  - See novel-ralph-harness-design.md §4.1 and §5.4;
    docs/issues/audit-2.3.5.md; docs/issues/audit-2.3.4.md.
  - Success: one `_write_word_counts_validated` helper owns the `[word_counts]`
    write and its validate-before-persist tail; `recount` and `reconcile`
    (including both reconcile recount closures) consume it rather than open-coding
    the pair; the function-local `disk_word_counts` import is lifted; and the
    recount, reconcile, and current-definition suites stay green.
- [ ] 7.4.8. Route the `done-flag-without-draft` token count through one shared
  whitespace-token counter.
  - Reroute (source: audit:2.3.5 / audit:2.3.6; severity: low).
    `disk_evidence._check_done_flag_without_draft` open-codes `len(text.split())`
    instead of reusing `wordcount._chapter_word_count`, leaving two production
    enactments of the one whitespace-token rule that 2.3.5's D-TOKEN-EQUALITY
    guarantee and the word-count modules' "no second counter" claim both depend
    on (audit-2.3.5 Finding 4, re-flagged as audit-2.3.6 Finding 4). Route the
    predicate through `wordcount._chapter_word_count` (or an extracted
    `_drafted_token_count`) so the production side has exactly one counter. This
    is cross-cutting counting single-source-of-truth hygiene, not the step-2.3
    disk-re-derivation hypothesis where it was raised, so it is deferred here.
    Coordinate with step 7.4, which collapses the adjacent chapter-draft
    *sourcing* readers.
  - Requires 2.3.6.
  - See novel-ralph-harness-design.md §4.1 and §4.5;
    docs/issues/audit-2.3.5.md; docs/issues/audit-2.3.6.md;
    docs/execplans/roadmap-2-3-5.md (Decision Log D-TOKEN-EQUALITY).
  - Success: `_check_done_flag_without_draft` consumes the shared whitespace-token
    counter rather than open-coding `len(text.split())`; exactly one production
    counter for the token rule remains; and the disk-evidence, desloppify, and
    wordcount suites stay green.
- [ ] 7.4.9. Introduce one `gate_triggers(ratio)` helper and reconcile
  `GATE_THRESHOLDS` with `KNITTING_PERCENTAGES`.
  - Reroute (source: audit:6.1.1; severity: medium; two near-identical findings
    merged — the re-spelled trigger derivation and the two unsynchronised gate
    encodings). The `tuple(ratio >= threshold for threshold in GATE_THRESHOLDS)`
    trigger derivation is now spelled at three sites (audit-6.1.1 Finding 2 —
    `_wordcount_report._gate_geometry`, `validate._check_gate_ratio_consistent`,
    and the corpus oracle), and the same three gates are encoded twice in
    unsynchronised forms (Finding 3 — `GATE_THRESHOLDS` ratios versus
    `done_predicate.KNITTING_PERCENTAGES` integers) with nothing pinning
    `GATE_THRESHOLDS[i] == KNITTING_PERCENTAGES[i] / 100`. The validator and the
    new `wordcount` report must agree on the triggers but are tied only by a
    shared constant, not a shared expression, so a tie-break or gate-set change
    drifts easily before the done-condition checks accrete as a fourth consumer.
    Promote a pure `gate_triggers(ratio)` helper into the `state` package beside
    `GATE_THRESHOLDS`, route `_gate_geometry` and `_check_gate_ratio_consistent`
    through it (the oracle stays an independent second opinion), and derive one
    gate tuple from the other (or assert their equivalence). This is cross-cutting
    word-count/gate single-source-of-truth hygiene, not the settled step-6.1
    disk-derivation hypothesis where it was raised, so it is deferred here.
  - Requires 6.1.1.
  - See novel-ralph-harness-design.md §4.5 and §5.2;
    docs/issues/audit-6.1.1.md (Findings 2 and 3);
    novel_ralph_skill/state/validate.py;
    novel_ralph_skill/state/done_predicate.py;
    novel_ralph_skill/commands/_wordcount_report.py.
  - Success: one pure `gate_triggers(ratio)` helper lives beside
    `GATE_THRESHOLDS` and is consumed by `_gate_geometry` and
    `_check_gate_ratio_consistent`; `GATE_THRESHOLDS` and `KNITTING_PERCENTAGES`
    are tied by derivation or a single assertion so the two encodings cannot
    drift; the `_cumulative_message` percentage rendering reads the canonical
    percentage source rather than re-deriving `* 100`; and the validator,
    wordcount, and corpus agreement suites stay green.
- [ ] 7.4.10. Guard the single gate-threshold source with a literal-scanning
  regression test over the wordcount command modules.
  - Reroute (source: review:6.1.1; severity: low). The 6.1.1 execplan's
    high-severity Risk is a second gate-threshold source drifting from
    `GATE_THRESHOLDS`; the report tests assert the derived triggers agree
    element-wise with `GATE_THRESHOLDS`, but nothing structurally stops a future
    edit from hard-coding a `0.30`/`0.50`/`0.80` literal in a command module. Add
    a lightweight source-scanning guard, modelled on the state-layout fence
    scanner the 7.3.10 proposal also references, that asserts no re-spelled
    gate-threshold literal appears in the wordcount command modules, so the
    single-source invariant is test-enforced rather than convention-enforced.
    This is cross-cutting maintainability hardening, not the settled step-6.1
    disk-derivation hypothesis where it was raised, so it is deferred here.
    Coordinate with 7.4.9 so the guard reflects the consolidated derivation.
  - Requires 7.4.9.
  - See novel-ralph-harness-design.md §4.5 and §5.2;
    docs/execplans/roadmap-6-1-1.md (the Risks single-source-of-truth entry);
    tests/test_state_layout_reference.py (the analogous fence scanner).
  - Success: a regression test scans the wordcount command modules and fails if
    a `0.30`/`0.50`/`0.80` gate-threshold literal is re-spelled outside the
    shared `GATE_THRESHOLDS` source; a planted literal fails the guard; and the
    wordcount and command suites stay green.
- [ ] 7.4.11. Unify the knitting-gate triple behind one canonical gate
  descriptor across the name, repair, and key projections.
  - Reroute (source: audit:2.3.7; severity: medium). Four parallel encodings of
    the same three knitting gates now exist, each hand-ordered to zip together:
    `validate.py` (`GATE_THRESHOLDS`, `_KNITTING_GATE_NAMES`), `_recount.py`
    (`_KNITTING_GATE_REPAIRS`), `_gate_drafting_mutators.py` (`_KNITTING_KEYS`),
    and `done_predicate.py` (`KNITTING_PERCENTAGES`). Adding or reordering a gate
    needs four coordinated edits with no automated guard against a transposed
    pair. Task 7.4.9 reconciles the `GATE_THRESHOLDS`/`KNITTING_PERCENTAGES`
    pair via a shared `gate_triggers` helper and an equivalence assertion, but
    leaves the name, repair, and arg/key projections hand-zipped. Promote a
    single `KnittingGate` descriptor (threshold, flag name, repair tuple, set-gate
    arg/key, percentage) with named projections, route `_KNITTING_GATE_NAMES`,
    `_KNITTING_GATE_REPAIRS`, and `_KNITTING_KEYS` through it, and pin the
    projections with an equality test so the cross-module ordering cannot drift.
    This is cross-cutting gate single-source-of-truth hygiene, not the settled
    step-2.3 disk-re-derivation hypothesis where it was raised, so it is deferred
    here.
  - Requires 7.4.9.
  - See novel-ralph-harness-design.md §5.2 and §4.5;
    docs/issues/audit-2.3.7.md (Finding 2);
    novel_ralph_skill/state/validate.py;
    novel_ralph_skill/commands/_recount.py;
    novel_ralph_skill/commands/_gate_drafting_mutators.py;
    novel_ralph_skill/state/done_predicate.py.
  - Success: one `KnittingGate` descriptor owns the threshold, flag name, repair
    tuple, set-gate arg/key, and percentage for each of the three gates;
    `_KNITTING_GATE_NAMES`, `_KNITTING_GATE_REPAIRS`, and `_KNITTING_KEYS` are
    projections of it rather than independent hand-ordered tuples; an equality
    test pins the projections so a transposed or reordered gate fails loudly; and
    the validate, recount, gate-drafting, done-predicate, and corpus agreement
    suites stay green.
- [ ] 7.4.12. Make the recount remedy consume the validator's gate-ratio verdict
  instead of recomputing it.
  - Reroute (source: audit:2.3.7; severity: medium; the review:2.3.7
    direction-agreement test proposal merged in as the pinning guard). The command
    layer's `_recount._gate_ratio_remedy` re-derives the entire gate-ratio
    computation (guard, drafted-sum numerator, ratio, per-gate flags, per-gate
    disagreement) that `validate._check_gate_ratio_consistent` /
    `_gate_ratio_disagreement` already performed on the same `State`, keeping the
    two disagreement enumerations in lock-step only by hand with no test binding
    them (audit-2.3.7 Finding 1; Findings 3/4/5 ride the same seam). Extract a
    shared pure `gate_ratio_disagreements` helper in the `state` package (or pass
    the validator verdict through `_refuse_if_incoherent`) so the gate the refusal
    names is provably the gate the remedy advises, and pin per-gate direction
    agreement with one equality test (subsuming the review:2.3.7 agreement-test
    proposal). This is cross-cutting gate single-source-of-truth hygiene, not the
    settled step-2.3 disk-re-derivation hypothesis where it was raised, so it is
    deferred here.
  - Requires 2.3.7.
  - See novel-ralph-harness-design.md §3.3, §5.2, and §5.4;
    docs/issues/audit-2.3.7.md (Findings 1, 3, 4, 5);
    novel_ralph_skill/state/validate.py (`_gate_ratio_disagreement`,
    `_check_gate_ratio_consistent`);
    novel_ralph_skill/commands/_recount.py (`_gate_ratio_remedy`).
  - Success: one pure `gate_ratio_disagreements` helper computes the per-gate
    disagreement set once, consumed by both `_check_gate_ratio_consistent` and the
    recount remedy (directly or via `_refuse_if_incoherent`), so the refusal and
    the remedy cannot name different gates; an equality test pins their per-gate
    direction agreement on a shared state; and the validate, recount, and corpus
    agreement suites stay green.
- [ ] 7.4.13. Extract a shared draft-read fault-routing context manager so every
  draft-read boundary routes faults to exit 3 in one place.
  - Reroute (source: audit:7.1.6; severity: low). The
    `try/except STATE_INPUT_ERRORS -> raise _draft_read_error(dir) from exc`
    envelope is hand-repeated verbatim at five draft-read boundaries (`_recount`,
    `_wordcount`, `_novel_done`, `_disk_evidence_or_state_error`, and `_compile`
    ×2): only the message is single-sourced by `_draft_read_error`, while the
    control flow that routes faults to exit 3 is not, so a missed site silently
    lets a draft-read fault escape to exit 1. A `draft_read_boundary` context
    manager in `state/_state_load.py` puts the routing contract in one place,
    completing the 6.3.5 single-sourcing of the draft-read fault path. This serves
    the step-7.4 hypothesis — express the chapter-draft-sourcing rule (here its
    fault-routing leg) once and share it — not the settled step-7.1 hypothesis
    where it was raised, so it is rerouted here. Coordinate with 7.4.1 so the
    shared `read_chapter_draft` reader routes through this boundary rather than
    re-spelling the `try/except`.
  - Requires 6.3.8.
  - See novel-ralph-harness-design.md §3.2 and §4.1;
    novel_ralph_skill/state/_state_load.py (`_draft_read_error`,
    `STATE_INPUT_ERRORS`);
    novel_ralph_skill/commands/_recount.py;
    novel_ralph_skill/commands/_wordcount_report.py;
    novel_ralph_skill/commands/_compile.py;
    novel_ralph_skill/state/disk_evidence.py.
  - Success: one `draft_read_boundary` context manager in `state/_state_load.py`
    owns the `STATE_INPUT_ERRORS -> _draft_read_error -> exit 3` routing; all five
    draft-read boundaries consume it rather than hand-repeating the `try/except`;
    a draft-read fault at any boundary routes to exit 3 (not exit 1); the exit-code
    policy and operator messages are unchanged; and the recount, wordcount,
    compile, and disk-evidence suites stay green.

### 7.5. Consolidate the corpus and end-to-end test scaffolding

This step answers whether the corpus fixture-plugin scaffolding and the
end-to-end and command-driving test harness share one set of primitives.
Definition of done for every task here: the duplication is removed, exactly
one canonical implementation survives under one name, it is documented as the
single source of truth, and a test pins it so it cannot silently re-fork.

- [ ] 7.5.1. Collapse the corpus tree-factory closures onto a shared helper and
  document the plugin-split convention.
  - Reroute (source: audit:2.1.5 / review:2.1.5; severity: low). Three corpus
    fixture plugins (`corpus_fixtures`, `corpus_live_draft_fixtures`,
    `corpus_divergent_fixtures`) now exist solely to respect the enforced
    400-line module cap, and 2.1.5 added the fourth near-identical "build named
    tree" factory closure plus "return variant keys" fixture; the duplication and
    the cap-driven plugin proliferation are now an established pattern each future
    category re-pays. A small shared helper in `working_corpus` collapsing the
    closures, plus a short developers'-guide note on when to carve a new plugin
    versus grow an existing one, gives the pattern and the subdirectory-isolation
    rationale a single home. This is cross-cutting test-maintainability hardening,
    not the step-2.1 schema hypothesis where it was raised, so it is deferred
    here. Defer until at least one further corpus category (e.g. roadmap 2.3.3's
    disk-authoritative oracle checks) has landed so the consolidation is driven
    by a real fourth category rather than a speculative one.
  - Requires 2.3.3.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("The `working/` fixture corpus"); docs/execplans/roadmap-2-1-5.md
    (Decision Log D5, the size-split plugin rationale).
  - Success: the per-category "build named tree" tree-factory closures share one
    `working_corpus` helper, the subdirectory-isolation comment has a single
    home, and the developers' guide records when to carve a new corpus fixture
    plugin versus grow an existing one; every current corpus agreement suite
    stays green.

- [ ] 7.5.2. Consolidate the installed-binary e2e build/install scaffolding into
  one binary-parametrised fixture and shared pure builders.
  - Reroute (source: audit:6.2.4 Findings 1, 2, 5 / review:6.2.4; severity:
    high). The wheel-build/venv-install body is duplicated across six sites and
    the `installed_binary_fixtures` plugin re-inlines two conftest fixtures, so
    there are now three byte-identical copies of the one-program
    `ProgramCatalogue` builder (`conftest.single_program_catalogue`,
    `installed_binary_fixtures._one_program_catalogue`,
    `test_ai_isms_e2e._one_program_catalogue`) and two copies of the
    venv-scripts-dir resolver, a divergence risk the post-merge audits repeatedly
    flag (WI1 step 2 deferred the fold-out to keep the blast radius small). A
    single binary-parametrised module-scoped fixture factory in
    `tests/installed_binary_fixtures.py`, plus shared pure builders for the
    catalogue and the scripts-dir resolver that both the function-scoped conftest
    fixtures and the module-scoped plugin delegate to, would collapse five
    near-identical helpers to one and let `installed_novel_state` become a thin
    alias. This serves the step-7.5 hypothesis — collapsing the e2e scaffolding
    onto shared homes — not the step-6.2 combinatorial-surface hypothesis where
    it was raised, so it is rerouted here.
  - Requires 6.2.4.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); docs/issues/audit-6.2.4.md (Findings 1, 2, 5).
  - Success: a single binary-parametrised module-scoped fixture factory owns the
    wheel-build/venv-install scaffolding; shared pure builders own the
    one-program catalogue and the venv-scripts-dir resolver, consumed by both the
    function-scoped conftest fixtures and the module-scoped plugin; the
    byte-identical copies in `installed_binary_fixtures` and `test_ai_isms_e2e`
    are retired; and the installed-binary e2e suites stay green.
- [ ] 7.5.3. Add a shared `run_installed` helper and unify the installed-binary
  e2e builds to module scope.
  - Reroute (source: audit:6.2.4 Findings 3, 4; severity: medium). The
    run-installed-script incantation recurs about a dozen times across the e2e
    modules, and three e2e modules rebuild the wheel per test where module scope
    would build once. This serves the step-7.5 hypothesis — collapsing the e2e
    scaffolding onto shared homes — by centralising the run convention in one
    `run_installed` helper and removing redundant slow per-test wheel rebuilds;
    it does not serve the step-6.2 surface hypothesis where it was raised.
    Coordinate with 7.5.2 so the helper consumes the shared fixture factory.
  - Requires 7.5.2.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); docs/issues/audit-6.2.4.md (Findings 3, 4).
  - Success: one shared `run_installed` helper owns the installed-script run
    convention every e2e site delegates to, the installed-binary e2e builds are
    uniformly module-scoped so each wheel is built once per module rather than per
    test, and the e2e suites stay green with no increase in total wheel builds.
- [ ] 7.5.4. Consolidate the reconcile-family command-driving scaffolding into
  one single registered plugin.
  - Reroute (source: audit:6.2.5 Findings 1, 2, 3 / review:6.2.5; severity:
    medium). The command-runner wrapper, the crash-injection seam reaching into
    a private production symbol, and the draft-bytes/present-files corpus helpers
    are duplicated across `tests/steps/torn_turn_recovery_steps.py`,
    `tests/steps/reconcile_steps.py`, and `tests/test_reconcile_integration.py`,
    and — after 6.2.12, 6.2.13, and 6.2.14 — across
    `tests/steps/torn_turn_rollback_steps.py`,
    `tests/steps/torn_turn_rollback_partial_steps.py`, and
    `tests/steps/torn_turn_rollback_partial_done_flag_steps.py` (a five-way copy
    of `_run_capturing`), so the duplication this task collapses is now load-bearing
    rather than speculative (re-flagged by review:6.2.12, audit:6.2.13, and
    review:6.2.14/audit:6.2.14), contravening the developers'-guide "shared
    scaffolding belongs in conftest or a registered plugin" rule (D-DUP deferred
    this deliberately). A single registered plugin exposing a `drive()` fixture,
    a `crash_after_recovery_receipt()` context-manager fixture, and
    `draft_bytes`/`present_files` helpers would collapse five-plus copies to one
    and give the private-seam coupling a single owner, matching the precedent set
    by `installed_binary_fixtures.py` for the e2e suites. This serves the
    step-7.5 hypothesis — collapsing the command-driving scaffolding onto a
    registered home — not the step-6.2 surface hypothesis where it was raised.
  - Requires 6.2.5.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); docs/issues/audit-6.2.5.md (Findings 1, 2, 3);
    docs/issues/audit-6.2.14.md.
  - Success: one registered plugin exposes the `drive()` fixture, the
    `crash_after_recovery_receipt()` crash-injection fixture, and the
    `draft_bytes`/`present_files` helpers; `torn_turn_recovery_steps.py`,
    `reconcile_steps.py`, `test_reconcile_integration.py`,
    `torn_turn_rollback_steps.py`, `torn_turn_rollback_partial_steps.py`, and
    `torn_turn_rollback_partial_done_flag_steps.py` delegate to it rather than each
    carrying a copy; the private production-seam coupling has a single owner; and
    the reconcile-family suites stay green.
- [ ] 7.5.5. Make the `working_corpus` package the source of truth for each
  variant's expected repaired recount.
  - Reroute (source: audit:6.2.5 Finding 6 / review:6.2.5; severity: low). The
    done-claim-stale-word-counts recount target and its `44800`/three-chapter
    total are re-literalised across at least four reconcile-family test sites
    (including the `_RECOUNT_TARGET = {01:0, 02:24000, 03:20800}` literal in
    `torn_turn_recovery_steps.py`), even though the corpus already owns the
    drafts; the corpus should expose the expected repaired counts (e.g. the
    `_expected` element callers currently discard) and let tests assert against
    it. This serves the step-7.5 hypothesis — letting the corpus own each
    variant's expected data so the command-driving tests stop re-literalising
    it — by removing a class of opaque drift when the corpus drafts change; it
    does not serve the step-6.2 surface hypothesis where it was raised.
  - Requires 7.5.4.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("The `working/` fixture corpus"); docs/issues/audit-6.2.5.md (Finding 6).
  - Success: the `working_corpus` package exposes each variant's expected
    repaired recount as data; the reconcile-family tests (including the
    torn-turn recovery steps) assert against the corpus-owned counts rather than
    re-literalising the `44800`/three-chapter total or the per-chapter targets;
    no test hard-codes the expected repaired counts; and the reconcile-family
    suites stay green.
- [ ] 7.5.6. Promote the in-process matrix drive and volatile-field-guard helpers
  to a shared conftest fixture.
  - Reroute (source: review:6.2.1; severity: low). The in-process
    drive/chdir/capture fixture, the volatile-field guard
    (`_assert_no_volatile_fields`), and the `_build_phase_tree` helper in
    `tests/test_command_surface_matrix.py` duplicate the established pattern from
    `test_novel_done_snapshots.py` and `test_compile_check_snapshots.py`; the
    execplan's Constraint deliberately kept them local until a second consumer
    existed, and the matrix is that second consumer (AGENTS.md "Shared test
    scaffolding" favours one conftest home once a second consumer exists). This
    serves the step-7.5 hypothesis — collapsing the command-driving scaffolding
    onto a shared home — by promoting the in-process drive and volatile guard to
    `conftest` before a third copy accretes; it does not serve the step-6.2
    surface hypothesis where it was raised.
  - Requires 6.2.1.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); docs/execplans/roadmap-6-2-1.md (the
    keep-it-local Constraint).
  - Success: the in-process drive/capture fixture and the volatile-field guard
    live in one `conftest` home; `test_command_surface_matrix.py`,
    `test_novel_done_snapshots.py`, and `test_compile_check_snapshots.py` consume
    it rather than each carrying a copy; no third copy of the volatile-guard
    pattern accretes; and the snapshot and matrix suites stay green.
- [ ] 7.5.7. Consolidate the in-process command-boundary driver into one shared
  registered test helper.
  - Reroute (source: audit:6.2.2 Findings 1, 2, 4, 5, 8; severity: medium). The
    run-and-capture seam — `chdir` + `redirect_stdout` +
    `pytest.raises(SystemExit)` + `json.loads(... or '{}')` over
    `run(build_app(), argv, RunContext(...))` — is duplicated across five step
    modules (`per_chapter_loop`, `torn_turn_recovery`, `compile`, `advance_phase`,
    `reconcile`), with the `_result` unwrap and the no-traceback check duplicated
    further; the 6.2.2 `_BUILD_APPS`-keyed `_run_capturing` is already the general
    form. Promote it, `_result`, and `assert_no_traceback` into a
    `tests/command_driver.py` registered plugin so the six copies of an invariant
    that can drift live once, mirroring how `conftest.py` consolidated the
    cross-module import six prior audits flagged. This serves the step-7.5
    hypothesis — collapsing the command-driving test scaffolding onto shared,
    registered homes — not the step-6.2 surface hypothesis where it was raised,
    so it is rerouted here. Coordinate with 7.5.6 (the in-process matrix drive)
    and 7.5.4 (the reconcile-family driver) so the seams converge on one home
    rather than three.
  - Requires 7.5.6.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); docs/issues/audit-6.2.2.md (Findings 1, 2, 4, 5,
    8).
  - Success: one registered `tests/command_driver.py` helper owns the in-process
    run-and-capture seam, the `_result` unwrap, and the `assert_no_traceback`
    check; `per_chapter_loop`, `torn_turn_recovery`, `compile`, `advance_phase`,
    and `reconcile` delegate to it rather than each carrying a copy; no module
    re-open-codes the seam; and the affected suites stay green.
- [ ] 7.5.8. Make `working_corpus` the source of truth for the drafted-words
  totals the per-chapter loop asserts against.
  - Reroute (source: audit:6.2.2 Finding 3; severity: medium). The drafted total
    `68800` and the per-chapter table are transcribed as literals in both 6.2.2
    step modules while the docstring claims they are derived from the corpus's
    module-private `_DRAFTED_WORDS`; a rebalance of `_DRAFTED_WORDS` would silently
    desync the loop assertions from the tree they are built against. Expose a
    public accessor (`DRAFTED_WORDS` / `drafted_total()` / `drafted_by_chapter()`)
    so the totals are the corpus's owned fact and the step modules assert against
    it. This serves the step-7.5 hypothesis — letting the corpus own each
    variant's expected data so the command-driving tests stop re-literalising
    it — by removing a class of opaque drift when the corpus drafts change; it
    does not serve the step-6.2 surface hypothesis where it was raised.
    Coordinate with 7.5.5 (the corpus-owned repaired-recount data) so the
    drafted and repaired totals share one ownership convention.
  - Requires 6.2.2.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("The `working/` fixture corpus"); docs/issues/audit-6.2.2.md (Finding 3).
  - Success: the `working_corpus` package exposes the drafted-words total and the
    per-chapter drafted table as a public accessor; both 6.2.2 step modules assert
    against the corpus-owned data rather than re-literalising `68800` or the
    per-chapter table; no test hard-codes the drafted totals; and the per-chapter
    loop suites stay green.
- [ ] 7.5.9. Expose the ROLLBACK-triggering unrecoverable basenames as
  corpus constants.
  - Reroute (source: review:6.2.13; severity: low; two near-identical proposals
    merged). The torn-turn rollback step modules hand-pick the
    `working/manuscript/chapter-99/draft.md` and `.../done.flag` literals and
    re-derive the `_RECOMPUTABLE_BASENAMES`-exclusion rule (`{state.toml, log.md}`)
    in an inline comment, rather than importing the unrecoverable basenames from
    `working_corpus`, so the same re-literalised-corpus-knowledge class
    audit-6.2.7 Finding 4 named for the recount target now applies to the ROLLBACK
    triggers. The proposals claim 7.5.5 already owns this, but 7.5.5's scope is
    the expected repaired *recount counts*, not the unrecoverable trigger
    basenames, so this is unowned. This serves the step-7.5 hypothesis — letting
    the corpus own each variant's expected data so the command-driving tests stop
    re-literalising it — by giving the ROLLBACK-trigger basenames a single
    corpus-owned source; it does not serve the step-6.2 surface hypothesis where
    it was raised. Coordinate with 7.5.5 so the corpus-owned basenames and the
    corpus-owned repaired counts share one ownership convention.
  - Requires 7.5.4.
  - See novel-ralph-harness-design.md §5.4; docs/developers-guide.md
    ("The `working/` fixture corpus"); docs/issues/audit-6.2.7.md (Finding 4);
    novel_ralph_skill/state/reconcile.py (`_RECOMPUTABLE_BASENAMES`).
  - Success: the `working_corpus` package exposes the ROLLBACK-triggering
    unrecoverable basenames (`draft.md`, `done.flag`) as named constants derived
    from (or pinned equal to) the production `_RECOMPUTABLE_BASENAMES`-exclusion
    rule; the torn-turn rollback step modules import them rather than hand-picking
    `chapter-99/draft.md`/`chapter-99/done.flag` literals or re-deriving the
    exclusion rule in comments; no rollback test re-literalises the trigger
    basename; and the reconcile-family suites stay green.
- [ ] 7.5.10. Sweep the legacy `novel-state` naming residue from the
  installed-binary e2e test scaffolding.
  - Reroute (source: review:1.2.13; severity: low). The
    `tmp_path_factory.mktemp("novel-state-install")` label in
    `tests/installed_binary_fixtures.py` and the `single_program_catalogue`
    labels (`"novel-state-run"`, `"novel-state-bijection-e2e"`,
    `"novel-state-e2e"`) across the installed e2e modules read as stale
    scaffolding names once 1.2.15 retires the legacy scripts and the single
    `novel` surface is the sole entry point; they are cosmetic catalogue/temp-dir
    labels, not the
    parametrize IDs that legitimately carry the legacy oracle command names. This
    is a cosmetic naming sweep that does not advance the step-1.2 packaging
    hypothesis where it was raised, so it is rerouted here: it serves the step-7.5
    hypothesis — collapsing the installed-binary e2e scaffolding onto shared,
    drift-free homes — by retiring the stale `novel-state-*` labels in step with
    the consolidation. Coordinate with 7.5.2 so the renamed labels land on the
    shared catalogue builder rather than the per-module copies. Do not touch the
    `tests/__snapshots__/*.ambr` parametrize IDs, which are the legacy oracle's
    command names and stay until their owning suites migrate.
  - Requires 1.2.15 and 7.5.2.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); tests/installed_binary_fixtures.py.
  - Success: no `novel-state-install`/`novel-state-run`/`novel-state-bijection-e2e`/
    `novel-state-e2e` cosmetic scaffolding label survives in the installed-binary
    e2e modules or `tests/installed_binary_fixtures.py` (each renamed to a
    surface-neutral label such as `novel-install`/`novel-run`); the
    `tests/__snapshots__/*.ambr` parametrize IDs are untouched; and the
    installed-binary e2e suites stay green.
- [ ] 7.5.11. Migrate the slow installed-binary e2es off the broken
  `capture=True` idiom and add the relaxed-subset cover-gap installed-binary e2e.
  - Reroute (source: review:2.3.8; severity: low). Task 2.3.8 Work item 5
    deliberately omitted the slow installed-binary variant for the relaxed
    cover-gap path because the sibling slow e2es call
    `SafeCmd.run_sync(..., capture=True)` — a latent `TypeError` under the locked
    cuprum 0.1.0, whose capture is `output=sh.RunOutputOptions(capture=True)`
    (Decision D5). The fast entry-point e2e proves the relaxed-subset behaviour,
    but the console-script subprocess path is currently only covered for the
    bijection case. Migrate the broken `capture=True` idiom to
    `output=sh.RunOutputOptions(capture=True)` across the slow e2es (the shared
    `run_installed` helper from 7.5.3 is the natural single home for the fixed
    idiom), then extend installed-binary coverage to the relaxed-subset cover-gap
    `check` → `reconcile` → `check` path. This serves the step-7.5 hypothesis —
    collapsing the installed-binary e2e scaffolding onto shared, drift-free homes
    (here, one correct capture idiom) — not the step-2.3 disk-re-derivation
    hypothesis where it was raised (the behaviour is already proven by the fast
    e2e), so it is rerouted here. Coordinate with 7.5.3 so the corrected capture
    idiom lands in the shared `run_installed` helper rather than per-module copies.
  - Requires 2.3.8 and 7.5.3.
  - See novel-ralph-harness-design.md §9; docs/execplans/roadmap-2-3-8.md
    (Decision D5; Work item 5); docs/adr-006-console-scripts-e2e-posix-policy.md;
    tests/installed_binary_fixtures.py.
  - Success: no slow e2e calls `SafeCmd.run_sync(..., capture=True)` (each uses
    `output=sh.RunOutputOptions(capture=True)` via the shared `run_installed`
    helper), so the latent `TypeError` is removed; an installed-binary subprocess
    e2e exercises the relaxed-subset cover-gap `check` (exit 4 on
    `word-counts-cover-drafts`), then `reconcile` (exit 0, RECOUNT), then `check`
    (exit 0) under the ADR 006 POSIX skip guard; and the installed-binary e2e
    suites
    stay green.
- [ ] 7.5.12. Rename the 6.2.12 partial-residue feature/step/binder trio to a
  `..._partial_draft` basename for symmetry with the `..._partial_done_flag`
  sibling.
  - Reroute (source: audit:6.2.14; severity: low). The two partial-residue
    ROLLBACK scenarios are now a `draft.md`/`done.flag` pair, but only the
    `done.flag` variant carries a discriminator in its filename:
    `tests/features/torn_turn_rollback_partial.feature` (with its
    `tests/steps/torn_turn_rollback_partial_steps.py` and
    `tests/test_torn_turn_rollback_partial_bdd.py` binder) reads as the parent of
    both rather than the `draft.md` cell, an asymmetry with the
    `..._partial_done_flag` sibling added by 6.2.14. This is a cosmetic naming
    sweep that does not advance the step-6.2 surface hypothesis where it was
    raised — the scenario is already proven and gated — so it is rerouted here:
    it serves the step-7.5 hypothesis — collapsing the command-driving
    scaffolding onto shared, drift-free homes — by removing the naming asymmetry
    in step with the consolidation. Rename the trio to a `..._partial_draft`
    basename and update the binder, the developers'-guide cross-reference, and the
    roadmap references in one pass. Best sequenced after 7.5.4 (which already
    touches both step modules) so the rename and the plugin extraction land
    together rather than churning the binder twice.
  - Requires 7.5.4.
  - See novel-ralph-harness-design.md §5.4; docs/developers-guide.md
    ("Shared test scaffolding"); docs/issues/audit-6.2.14.md;
    tests/features/torn_turn_rollback_partial.feature.
  - Success: the `torn_turn_rollback_partial` feature, step module, and binder are
    renamed to a `..._partial_draft` basename symmetric with the
    `..._partial_done_flag` sibling; the developers'-guide cross-reference and the
    roadmap references are updated to match; no stale `torn_turn_rollback_partial`
    basename without a `_draft`/`_done_flag` discriminator survives; and the
    reconcile-family suites stay green.
- [ ] 7.5.13. Migrate the per-module `_drive` helpers onto the shared
  `contract_drive_support.drive` seam.
  - Reroute (source: audit:6.3.2; severity: medium). The 6.3.2 change created the
    sanctioned `tests/contract_drive_support.py::drive` fixture but left about 21
    per-module hand-rolled `_drive`/`_drive_*` copies the developers'-guide
    "Shared test scaffolding" rule forbids; a drive-mechanics change today touches
    20-plus modules and each copy is a drift risk against the very contract 6.3.2
    pins. Migrate them onto `drive` (adding a machine-mode JSON adapter where a
    copy needs one), delete each local copy, and tighten the developers'-guide
    rule to name `drive` as the single in-process command-drive entry point. This
    serves the step-7.5 hypothesis — collapsing the command-driving scaffolding
    onto shared, registered homes — not the settled step-6.3 contract-uniformity
    hypothesis where it was raised. Coordinate with 7.5.7 so the in-process
    run-and-capture seam and the `drive` fixture converge on one home rather than
    two.
  - Requires 6.3.2 and 7.5.7.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); tests/contract_drive_support.py (`drive`).
  - Success: every in-process command-drive test consumes the
    `contract_drive_support.drive` seam (with a machine-mode JSON adapter where
    needed) rather than a hand-rolled `_drive`/`_drive_*` copy; no per-module
    `_drive` copy survives; the developers'-guide rule names `drive` as the single
    in-process command-drive entry point; and the affected suites stay green.

- [ ] 7.5.14. Add a shared installed success-arm run-and-assert harness mirroring
  `assert_installed_state_error`.
  - Reroute (source: audit:6.3.6; severity: low). The installed error arm already
    has a consolidated run-and-assert harness
    (`assert_installed_state_error`) while the installed success arm hand-rolls
    the same run/parse mechanics in `test_installed_novel_state_check_exits_zero`,
    leaving the next installed success-arm proof without a seam to reuse. Mirror
    the error-arm harness with an `assert_installed_success_envelope` helper in
    `tests/installed_binary_fixtures.py` and migrate the success-arm test onto it.
    This serves the step-7.5 hypothesis — collapsing the installed-binary e2e
    scaffolding onto shared homes — not the settled step-6.3 contract-uniformity
    hypothesis where it was raised. Defer until a second installed success-arm
    proof exists so the consolidation is driven by a real second consumer.
  - Requires 6.3.6 and 7.5.2.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); tests/installed_binary_fixtures.py
    (`assert_installed_state_error`).
  - Success: one `assert_installed_success_envelope` harness owns the installed
    success-arm run/parse/skeleton-assert mechanics;
    `test_installed_novel_state_check_exits_zero` (and any second consumer)
    delegates to it rather than hand-rolling the run/parse; no installed
    success-arm test re-open-codes the seam; and the installed-binary e2e suites
    stay green.
- [ ] 7.5.15. Extract a shared CommonMark fence parser for the test prose-guards.
  - Reroute (source: audit:6.3.7; severity: low). Task 6.3.7 adds the second
    hand-rolled CommonMark fence regex (`_FENCE_TEMPLATE` in
    `tests/_skill_contract_scanner.py`) alongside `_FENCE_RE` in
    `tests/_state_layout_scanner.py`; the two share a non-trivial fence grammar
    and a duplicated correctness comment. Factor the grammar into one
    `iter_fences` helper, leaving each caller's info-string selection local, so
    the correctness reasoning has one home. This serves the step-7.5
    hypothesis — the test harness sharing one set of primitives — not the settled
    step-6.3 documentation hypothesis where it was raised.
  - Requires 6.3.7.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); tests/_skill_contract_scanner.py
    (`_FENCE_TEMPLATE`); tests/_state_layout_scanner.py (`_FENCE_RE`).
  - Success: one `iter_fences` helper owns the CommonMark fence grammar and its
    correctness comment; `_skill_contract_scanner.py` and `_state_layout_scanner.py`
    consume it, each keeping only its info-string selection local; no second copy
    of the fence grammar survives; and the prose-guard suites stay green.
- [ ] 7.5.16. Consolidate the find-or-fail document slicers used by the
  prose-guards onto one shared helper.
  - Reroute (source: audit:6.3.7; severity: low). Task 6.3.7 introduces
    `slice_doc_region` (in `tests/_skill_contract_scanner.py`) as a strictly
    better, source-naming third copy of the find-or-fail slice idiom rather than
    generalising the existing `_slice_between`/`_require_index` in
    `tests/test_skill_deflation_guard.py`. Promote `slice_doc_region` (plus a
    `require_index` companion) into a shared `tests/_doc_slice.py` and migrate the
    deflation guard onto it, collapsing three slicers to one. This serves the
    step-7.5 hypothesis — the test harness sharing one set of primitives — not the
    settled step-6.3 documentation hypothesis where it was raised. Coordinate with
    7.5.15 so the fence parser and the slice helper land in coherent shared test
    homes.
  - Requires 6.3.7.
  - See novel-ralph-harness-design.md §9; docs/developers-guide.md
    ("Shared test scaffolding"); tests/_skill_contract_scanner.py
    (`slice_doc_region`); tests/test_skill_deflation_guard.py
    (`_slice_between`/`_require_index`).
  - Success: one shared `tests/_doc_slice.py` owns `slice_doc_region` and a
    `require_index` companion; the skill-contract scanner and the deflation guard
    consume it rather than each carrying a find-or-fail slicer; three slicers
    collapse to one; and the prose-guard and deflation-guard suites stay green.

### 7.6. Harden the contract guards, detectors, and gates

This step answers whether the spine's guards, detectors, gates, and recovery
paths are robust against the edge cases the audits surfaced — applied to the
now single-sourced code, so hardening lands on one implementation rather than
copies that would re-diverge.

- [ ] 7.6.1. Extend the state-layout guard fence grammar to all CommonMark
  fence forms (tilde, four-or-more backticks, indented).
  - Requires 1.2.8 and 6.2.3.
  - The `re`-based fence matcher cannot see tilde, longer-backtick, or
    list-indented fences, a structural blind spot that could silently drop a
    recipe once the reference gains list-embedded examples; a stdlib dedent
    pre-pass or vetted lightweight fence parser hardens it without breaching the
    no-AST-dependency spirit.
  - Success: planted recipes in tilde, four-backtick, and indented fences are
    all caught; the no-AST-dependency constraint holds.
- [ ] 7.6.2. Extend the state-layout write-recipe guard to rename, move, and
  in-place writers across Python and shell.
  - Requires 1.2.8 and 6.2.3.
  - `os.rename`/`os.replace`, `shutil.move`/`shutil.copy`, `sed -i`, `dd of=`,
    `sponge`, and `cp`/`mv ... working/state.toml` all currently pass the guard
    clean even though they write the state file outside `novel-state`; a
    path-anchored write-verb heuristic closes the disclosed residual hole.
  - Success: each enumerated writer idiom against `working/state.toml` is
    rejected; legitimate non-state writes are not.
- [x] 7.6.3. Extend the direct-edit guard to every skill reference that can
  carry executable recipes.
  - Requires 1.2.8.
  - 1.2.8 scoped the guard to `state-layout.md`; other references such as
    `done-conditions.md` contain executable fences and could grow a hand-edit
    recipe no guard would catch. A shared multi-file fence scanner closes that
    gap without per-file duplication.
  - Success: a planted hand-edit recipe in any executable-carrying reference is
    caught by a single shared scanner, with no per-file duplication.
  - [x] 7.6.3.1. Plant a flagged recipe for every under-exercised executable
    fence label.
    - Addendum (from audit:7.6.3; medium). Six labels (`py`, `py3`, `pycon`,
      `bash`, `shell`, `console`) are in the executable set but never planted as
      a positive case; add one flagged recipe per label so dropping a member from
      the frozenset fails a test. Lightweight addendum pass.
  - [x] 7.6.3.2. Reconcile `_iter_executable_fences`' name with its eager-list
    return.
    - Addendum (from audit:7.6.3; low). The `_iter_` prefix promises a lazy
      generator but the body returns a `list`; either yield per fence or rename
      to `_executable_fences`. Internal only. Lightweight addendum pass.
  - [x] 7.6.3.3. Express `find_direct_state_write_recipes_in_files` as a walrus
    dict comprehension.
    - Addendum (from audit:7.6.3; low). Replace the mutable-accumulator loop with
      a comprehension that calls the detector once per document, preserving the
      no-second-matcher invariant. Readability tidy-up. Lightweight addendum pass.
  - [x] 7.6.3.4. Anchor the inventory-tripwire intent on the
    `_KNOWN_SKILL_MARKDOWN` edit line.
    - Addendum (from audit:7.6.3; low). Add a comment above the constant stating
      it is hand-maintained and must not be derived from the glob, so a refactor
      cannot silently optimise the tripwire away. Lightweight addendum pass.
  - [x] 7.6.3.5. Name the `console`-fence bare-`.write(` Python-in-shell gap as
    a deferred 7.6.4 item.
    - Addendum (from audit:7.6.3; low). `console` is executable but not in the
      Python set, so a `python -c` bare-`.write(` one-liner slips the guard;
      extend the executable-set comment to record this as an accepted gap
      deferred to task 7.6.4. Lightweight addendum pass.
  - [x] 7.6.3.6. Add a tripwire for non-`.md` markdown-like skill references.
    - Addendum (from audit:7.6.3; low). The `**/*.md` discovery glob silently
      skips a `.markdown`/`.mdx`/`.mkd` reference; assert no such file appears
      under `skill/novel-ralph/`, with a message pointing at task 7.6.4 and the
      gate-assumption prose. Lightweight addendum pass.
  - [x] 7.6.3.7. Consider folding the clean-fence "not flagged" asserts into one
    parametrized table.
    - Addendum (from audit:7.6.3; low). The temp-file and unrelated-redirect
      clean cases share a "assert this fence is clean" skeleton; weigh a single
      parametrized `test_clean_fence_not_flagged` (keeping the per-row rationale
      as `ids`) against the one-test-per-rationale form. Lightweight addendum
      pass.
- [ ] 7.6.4. Add a fuzz or property check that the guard's planted-recipe forms
  survive whitespace, quoting, and flag-order variation.
  - Requires 1.2.8.
  - The parametrized matrix encodes one concrete spelling per form, sharing the
    regex's own assumptions; a property test that mutates whitespace, quoting,
    and flag ordering around each planted recipe would catch anchor-too-tight
    regressions like the no-space redirect automatically.
  - Success: a property test over whitespace, quoting, and flag-order mutations
    of each planted recipe passes, demonstrating the matcher is not
    anchor-too-tight.

- [ ] 7.6.5. Stop review-round ExecPlan scratch artefacts from breaking the
  whole-tree markdownlint gate.
  - Reroute (source: review:2.2.1; severity: low). Untracked
    `docs/execplans/*.review-r*.md` scratch files trip `make markdownlint`
    (MD013) on a whole-tree run even though they are not part of any committed
    change, so a routine review cycle can redden the aggregate gate. Adopt a
    convention that keeps these out of the gate — a `.gitignore` rule for
    `*.review-r*.md`, a markdownlint `ignores` entry, or a docs-lint scope
    limited to tracked files — without suppressing lint on the committed
    ExecPlans and their review rounds that are meant to be checked.
  - Requires 1.3.1.
  - See AGENTS.md "Markdown guidance"; `.markdownlint-cli2.jsonc`.
  - Success: `make markdownlint` stays green in the presence of an untracked
    `docs/execplans/foo.review-r1.md` scratch file, while committed ExecPlans
    and their review rounds are still linted.
- [ ] 7.6.6. Track and absorb the pytest-bdd / pytest 10 compatibility break.
  - Reroute (source: review:2.2.1; severity: low). `pytest-bdd` 8.1.0 emits a
    `PytestRemovedIn10Warning` under the current `pytest`, so a `pytest` 10
    upgrade will break the behavioural suite the spine depends on; the pin bump
    must be deliberate, taken when a compatible `pytest-bdd` ships. Either filter
    the warning with a documented rationale until then, or bump `pytest-bdd` and
    its version-pin guard in lockstep once a `pytest`-10-compatible release lands.
  - Requires 2.2.1.
  - See AGENTS.md "Python verification and testing";
    `tests/test_pytest_bdd_dependency.py`.
  - Success: the behavioural suite runs clean under the targeted `pytest`, the
    `pytest-bdd` version pin and its guard move together with any bump, and the
    `PytestRemovedIn10Warning` is either resolved or filtered with a recorded
    reason.
- [ ] 7.6.7. Constrain the `make fmt` mdformat pass so it stops reflowing every
  tracked Markdown file.
  - Reroute (source: review:6.2.4; severity: low). The 6.2.4 retrospective
    records that `make fmt` rewrote every Markdown file in the tree, forcing a
    stash of spurious churn and a manual rewrap of execplan lines — a recurring
    trap for every agent touching docs. This serves the step-7.6 hypothesis —
    that the documentation gates can be made robust to predictable churn without
    weakening their guarantees — by constraining the formatter to the files a
    change actually touches rather than the whole tree, so a docs edit no longer
    drags spurious reflow churn through the gate. Constrain mdformat to changed
    files (or remove it from the default `fmt` target) without weakening the
    markdownlint check the committed Markdown is still held to.
  - Requires 1.3.1.
  - See AGENTS.md "Markdown guidance"; the project `Makefile` (`fmt` target);
    docs/execplans/roadmap-6-2-4.md (retrospective).
  - Success: `make fmt` no longer reflows tracked Markdown files outside the
    current change set, a docs edit produces no spurious whole-tree Markdown
    churn, and `make markdownlint` still holds the committed Markdown to the same
    standard.
- [ ] 7.6.8. Define a canonical location and edit-scope policy for Logisphere
  design-review artefacts.
  - Reroute (source: review:1.2.17; severity: low). Task 1.2.17 committed
    `docs/execplans/roadmap-1-2-17.review-r1.md` alongside the ExecPlan, but the
    ExecPlan's own edit-scope Constraint names only the deliverable files, so
    review artefacts (`*.review-r*.md`, `*.logisphere-review-r*.md`) land in
    execplan-scoped edits with no declared home, creating recurring ambiguity for
    adversarial scope reviews. This serves the step-7.6 hypothesis — whether the
    documentation gates can be made robust to the predictable churn a review
    cycle leaves behind — by settling, alongside 7.6.5's gate handling, a
    repo-wide convention for where these artefacts live and whether they count
    toward a task's edit-scope, so the advisory stops recurring. It does not
    advance the step-1.2 packaging-supports-invocation hypothesis where it was
    raised; it is a cross-cutting documentation-process convention, deferred here.
  - Requires 1.3.1.
  - See AGENTS.md; docs/scripting-standards.md; the `execplans` and
    `logisphere-design-review` skills; docs/execplans/ (the existing
    `*.review-r*.md` artefacts).
  - Success: one recorded decision fixes the canonical location for design-review
    artefacts and states whether they count toward a task's declared edit-scope;
    AGENTS.md or docs/scripting-standards.md names the convention; and the
    convention is consistent with 7.6.5's gate handling for the same files.
- [ ] 7.6.9. Run the whole-tree markdownlint and nixie docs gates in CI and the
  merge gate.
  - Reroute (source: audit:6.3.3 Finding 5 / review:6.3.3; severity: low; two
    near-identical proposals merged). `make all` and CI do not run the
    `markdownlint`/`nixie` docs gates, so docs-only changes can merge without
    either gate and the project relies on the post-merge auditor to catch Markdown
    regressions — task 6.3.3's Work item 0 had to clear an MD012 baseline the
    6.3.2 commit left RED at HEAD because per-task gating passed despite a
    tree-level failure. This serves the step-7.6 hypothesis — that the
    documentation gates can be made robust without weakening their guarantees —
    by making the gate run `markdownlint` over `**/*.md` (and `nixie`) at merge
    time so a future task cannot inherit a red baseline it did not cause. Confirm
    the gate lints the whole tree as `make markdownlint` does locally, not just
    changed files. Coordinate with 7.6.5/7.6.7 so the whole-tree gate stays green
    on the scratch-artefact and reflow conventions they settle.
  - Requires 7.6.5.
  - See AGENTS.md "Markdown guidance"; the project `Makefile`
    (`markdownlint`/`nixie` targets); docs/execplans/roadmap-6-3-3.md (Work item
    0); docs/issues/audit-6.3.3.md (Finding 5).
  - Success: the CI/merge gate runs `make markdownlint` over `**/*.md` and `make
    nixie`, so a docs-only change cannot merge past a Markdown or prose
    regression; a confirmation records that the gate lints the whole tree rather
    than only changed files; and a deliberately-introduced MD012 (or nixie)
    violation reddens the gate.

- [ ] 7.6.10. Mutation-test the state validator and the oracle-agreement suites.
  - Reroute (source: review:2.1.3; severity: low). The 2.1.3 review found a
    passing suite that survived a semantically meaningful mutation (a live
    `draft.md` reader silently degraded to a `[word_counts]` table reader), an
    inert guard caught only by a one-off manual mutation probe. A scoped `mutmut`
    run over `novel_ralph_skill/state/validate.py` and the corpus oracles
    (`tests/working_corpus/_oracle.py`, `tests/working_corpus/_live_draft.py`)
    would surface such inert guards across the whole state-validation lane
    systematically, not just at the one site the review happened to probe. This
    does not serve the step-2.1 hypothesis — it is adversarial verification of an
    already-built lane, a cross-cutting quality concern — so it is deferred here
    rather than parked in 2.1.
  - Requires 2.1.3.
  - See novel-ralph-harness-design.md §9; AGENTS.md "Python verification and
    testing"; the `mutmut` skill.
  - Success: a scoped `mutmut` run over the named validator and oracle modules
    reports its surviving mutants, each surviving mutant is either killed by a
    new test or recorded with a rationale, and the mutation configuration is
    captured so the run is repeatable.

- [ ] 7.6.11. Decide and document whether `COMPLETE_PENDING_TURN` re-derives a
  present-but-stale `[word_counts]` in one pass.
  - Reroute (source: review:2.3.2; severity: low). A torn `recount` turn whose
    record is uncleared resolves to `COMPLETE_PENDING_TURN`, but
    `_pending_turn_edit` re-derives `[word_counts]` only when `state.toml` is a
    *missing* declared path (D-COMPLETE), so it merely clears the record and
    leans on a second `reconcile` pass (D-SELF-CONVERGES) to fix a still-stale
    table. This is correct under harness re-entry — the state converges and never
    drifts — so it does not advance the step-2.3 disk-re-derivation hypothesis;
    it is a single-pass-repair operability and operator-clarity concern. Make the
    house-wide decision once: either have `COMPLETE_PENDING_TURN` re-derive a
    present-but-stale `[word_counts]` within the same pass (revisiting D-COMPLETE
    and D-SELF-CONVERGES together so the dispatch and Decision Log agree), or
    record two-pass convergence as the deliberate recovery contract with its
    rationale, and capture the outcome in the developers' guide and the 2.3.2
    execplan Decision Log so no later recovery path re-litigates it.
  - Requires 2.3.2.
  - See novel-ralph-harness-design.md §3.4 and §5.4;
    docs/execplans/roadmap-2-3-2.md (Decision Log D-COMPLETE, D-SELF-CONVERGES);
    docs/developers-guide.md.
  - Success: one decision records whether a torn `recount` is repaired in a
    single `reconcile` pass or by deliberate two-pass convergence; the
    `COMPLETE_PENDING_TURN` dispatch conforms to whatever the decision settles;
    and the developers' guide and the 2.3.2 Decision Log agree on the recovery
    contract with no surviving contradiction.

- [ ] 7.6.12. Add line-wrap-tolerant matching for multi-token desloppify tells.
  - Reroute (source: review:8.1.1; severity: low). `detect.py` documents that a
    multi-token offender hard-wrapped across a newline is not detected in v1
    (single-line `finditer`), and the ai-isms phrasal tells (e.g. "plays a
    vital role") inherit this limitation. Severity is low because the writer's
    drafts wrap at sentence or paragraph granularity, but a tracked follow-up is
    warranted if false negatives surface. This does not serve the step-8.1
    hypothesis — it is a detection-engine robustness improvement cross-cutting
    every pack — so it is rerouted here rather than parked in 8.1. Add
    line-wrap-tolerant matching for multi-token tells (a bounded join or
    soft-wrap normalisation) without breaking the per-line line-number reporting
    or the no-`re.DOTALL` discipline.
  - Requires 5.1.2.
  - See novel-ralph-harness-design.md §4.4 and §6.1;
    novel_ralph_skill/rulepack/detect.py (the documented single-line limitation).
  - Success: a multi-token tell hard-wrapped across a newline is detected, the
    per-line line-number reporting and the no-flags/no-`re.DOTALL` compile
    discipline still hold, and the existing desloppify suites stay green.
- [ ] 7.6.13. Calibrate per-rule false-positive thresholds for fiction-prone
  ai-isms collocations against an ordinary-fiction corpus.
  - Reroute (source: review:8.1.1; severity: low). `vital-role` (and potential
    future role/moment templates) can fire on legitimate theatrical fiction; a
    small calibration corpus of ordinary genre fiction could justify per-rule
    non-zero thresholds, reducing model-adjudication noise on novels
    specifically. This does not serve the step-8.1 hypothesis — it is
    pack-quality calibration of an already-shipped pack, a cross-cutting
    detection-quality concern — so it is rerouted here. Assemble a small
    ordinary-fiction corpus, measure each fiction-prone collocational rule's
    false-positive rate against it, and set per-rule thresholds where a non-zero
    bar is justified by the measured rate (recording the rationale per the
    membership policy).
  - Requires 8.1.1.
  - See novel-ralph-harness-design.md §6.2;
    novel_ralph_skill/rulepack/packs/ai-isms.toml; docs/developers-guide.md
    ("Rule packs and the loader boundary").
  - Success: each fiction-prone ai-isms collocation has a measured
    false-positive rate against an ordinary-fiction corpus, any non-zero
    threshold is justified by that measurement and recorded with its rationale,
    and the ai-isms validation suite stays green.
- [ ] 7.6.14. Extend line-wrap-tolerant matching to the device-ledger detector so
  the two detector families stay aligned.
  - Reroute (source: review:8.1.2; severity: low). The ledger detector's
    `_scan_device` scans line-by-line with no-flags compilation, exactly like the
    rule-pack `_scan_rule`, so a multi-token device split across a hard line break
    is not counted and authors must use a bounded `[^\n]{0,N}?` window; this v1
    limitation is documented in both the ledger `detect.py` docstring and the
    worked example. This does not serve the step-8.1 hypothesis — it is the
    ledger-family counterpart of the rule-pack detector-robustness work, a
    cross-cutting detection-engine improvement — so it is rerouted here. Apply the
    same line-wrap-tolerant matching 7.6.12 lands for the rule-pack detector to
    the ledger detector, coordinating the two so the device and rule-pack families
    share one wrap-handling discipline rather than diverging.
  - Requires 7.6.12.
  - See novel-ralph-harness-design.md §6.3;
    novel_ralph_skill/ledger/detect.py (the documented single-line limitation).
  - Success: a multi-token device hard-wrapped across a newline is detected by the
    ledger detector, its `{chapter, line}` reporting and the no-flags/no-`re.DOTALL`
    compile discipline still hold, the ledger and rule-pack families share the
    same wrap-handling approach, and the existing ledger suites stay green.

- [ ] 7.6.15. Make the cover predicate read disk once and share one bijection
  predicate (set equality and contiguity).
  - Reroute (source: audit:2.3.6 / review:2.3.6; severity: medium). The
    `word-counts-cover-drafts` cover predicate performs a redundant full
    draft-tree read whose result is entirely discarded (audit Finding 1) and
    hand-copies the bijection guard without the contiguity clause (audit Finding
    2 / the review's latent double-fire): it defers to `manifest-disk-bijection`
    only on set-inequality of manifest versus on-disk chapter dirs, so a
    constructible non-contiguous manifest matching the disk dirs would bypass the
    deferral and let a co-occurring `by_chapter` key-set mismatch double-fire both
    invariants, narrowing the orthogonality the Constraints demand. Derive the
    cover key set from the manifest with no disk read, and extract one
    `manifest-disk-in-bijection` predicate (set equality AND contiguity) both
    invariants consult; add a §1.3.2 corpus variant pinning the deferral. This is
    cross-cutting robustness-and-maintainability hardening, not the step-2.3
    disk-re-derivation hypothesis where it was raised, so it is deferred here.
  - Requires 2.3.6.
  - See novel-ralph-harness-design.md §5.4 and §9;
    docs/issues/audit-2.3.6.md; docs/execplans/roadmap-2-3-6.md.
  - Success: the cover predicate derives its key set from the manifest with no
    redundant draft-tree read; one `manifest-disk-in-bijection` predicate (set
    equality and contiguity) is consulted by both `word-counts-cover-drafts` and
    `manifest-disk-bijection`; a non-contiguous manifest matching the disk dirs
    defers to the bijection invariant rather than double-firing, pinned by a new
    §1.3.2 corpus variant; and every current word-count and corpus agreement suite
    stays green.
- [ ] 7.6.16. Collapse the relaxed-subset reconcile pre-arm onto its detector
  (de-duplicate the subset gate and the disk reads).
  - Reroute (source: audit:2.3.8; severity: medium). Task 2.3.8's
    `_drafting_subset_cover_gap` (`novel_ralph_skill/state/_reconcile_precedence.py`)
    re-derives the relaxed-subset shape `_check_word_counts_cover_drafts` already
    gates on, encoding the same `on_disk < manifest and coherent_subset` gate
    twice (a divergence risk between the detector and the reconcile pre-arm) and
    re-globbing the manuscript directory three times per relaxed reconcile.
    Folding the phase/subset ownership into the detector and threading the
    already-computed `on_disk` set from `derive_reconciliation` removes the
    duplicated gate and the redundant disk I/O. This is robustness-and-
    maintainability hardening of the relaxed cover-drafts seam (the verdicts are
    already correct and pass); it does not advance the step-2.3 disk-re-derivation
    hypothesis where it was raised, so it is deferred here alongside the sibling
    strict-predicate single-read consolidation (7.6.15).
  - Requires 2.3.8 and 7.6.15.
  - See novel-ralph-harness-design.md §5.4; docs/execplans/roadmap-2-3-8.md
    (Decision D3, Work item 3); novel_ralph_skill/state/_reconcile_precedence.py
    (`_drafting_subset_cover_gap`); novel_ralph_skill/state/_disk_word_counts.py
    (`_check_word_counts_cover_drafts`).
  - Success: the relaxed-subset gate (`on_disk < manifest` and `coherent_subset`)
    is computed in exactly one place that both `check`'s cover-drafts detector and
    `reconcile`'s pre-arm consult; `derive_reconciliation` threads the
    already-computed `on_disk` set into the pre-arm so the manuscript directory
    is globbed once per relaxed reconcile rather than three times; and every
    current
    reconcile-precedence, cover-drafts, and corpus agreement suite stays green
    with the verdicts unchanged.
- [ ] 7.6.17. Single-home the scoped-precedence guards (the sole-refuse-class
  bijection predicate and the strict coherent-subset idiom).
  - Reroute (source: audit:2.3.8; severity: low; two near-identical findings
    merged). Task 2.3.8 left the load-bearing B2 "sole refuse-class is bijection"
    guard (`fired_refuse == {MANIFEST_DISK_BIJECTION}`) duplicated across two
    sites in `novel_ralph_skill/state/_reconcile_precedence.py` (lines 106 and
    164), and the "strict coherent subset" idiom
    (`on_disk < manifest and _classify_bijection(manifest, on_disk).coherent_subset`)
    duplicated across three production sites (`_reconcile_precedence.py`,
    `_disk_word_counts.py`, and `disk_evidence.py`). Extracting a
    `_sole_refuse_is_bijection` predicate and a
    `_BijectionBreak.strict_coherent_subset` property pins each notion to one
    definition, reducing drift risk in the precedence logic. This is cross-cutting
    maintainability hardening (the guards are already correct and pass); it does
    not advance the step-2.3 disk-re-derivation hypothesis where it was raised,
    so it is deferred here with the related bijection-definition single-homing of
    this step. Coordinate with 7.6.15, which extracts the shared
    `manifest-disk-in-bijection` predicate, so the coherence notions converge on
    one home.
  - Requires 2.3.8 and 7.6.15.
  - See novel-ralph-harness-design.md §5.4;
    docs/execplans/roadmap-2-3-8.md (Decision D3);
    novel_ralph_skill/state/_reconcile_precedence.py;
    novel_ralph_skill/state/_disk_paths.py (`_BijectionBreak`).
  - Success: the sole-refuse-class bijection guard lives in one
    `_sole_refuse_is_bijection` predicate both precedence sites consult; the
    strict coherent-subset idiom lives in one
    `_BijectionBreak.strict_coherent_subset` property every production site
    consults rather than recomputing inline; no site re-open-codes either notion;
    and every current reconcile-precedence and disk-evidence suite stays green with
    the verdicts unchanged.

- [ ] 7.6.18. Decide and apply the multi-producer hardening for the BLOCKER
  recogniser grammar.
  - Reroute (source: review:3.1.5; severity: low). The recogniser enters a
    `## BLOCKER` section and matches `### Bn` findings on an exact, case-sensitive
    grammar (D-BLOCKER-FORMAT, D-BLOCKER-CASE), which is sound while the spiteful
    critic is the only writer of `critic-notes.md`. If a second producer appears,
    a benign whitespace variant (`##  BLOCKER`, trailing spaces, a tab before the
    token) would read clean and re-open the exit-0 lie task 3.1.5 closed. Decide
    once between normalising benign whitespace defensively in the recogniser and
    adding a producer-side lint that rejects malformed `## BLOCKER` / `### Bn`
    headings, and apply the chosen approach with tests over the whitespace
    variants. This is cross-cutting robustness hygiene against a hypothetical
    second producer, not the settled step-3.1 truthful-done-clause hypothesis
    where it was raised, so it is deferred here.
  - Requires 3.1.5.
  - See novel-ralph-harness-design.md §4.2;
    skill/novel-ralph/references/critic-personas.md (the `## BLOCKER` / `### Bn`
    format); skill/novel-ralph/references/done-conditions.md;
    docs/execplans/roadmap-3-1-5.md (D-BLOCKER-FORMAT, D-BLOCKER-CASE).
  - Success: one decision records whether benign whitespace is normalised in the
    recogniser or rejected by a producer-side lint; the chosen approach is applied
    and pinned by tests over the `##  BLOCKER`, trailing-space, and
    tab-before-token variants so none silently reads clean; the documented
    case/variant out-of-scope decision (D-BLOCKER-CASE) is preserved or revisited
    explicitly; and the done-predicate suite stays green.

- [ ] 7.6.19. Add a gate that fails when an ExecPlan reads COMPLETE while its
  roadmap checkbox is still unticked.
  - Reroute (source: review:6.2.1; severity: low). The 6.2.1 implementation left
    `docs/roadmap.md` unticked despite its ExecPlan reading COMPLETE — a class of
    bookkeeping drift easy to miss in review that undermines the roadmap as the
    workflow's source of truth for task selection. This serves the step-7.6
    hypothesis — making a class of silent bookkeeping drift fail loudly at gate
    time — by adding a lightweight consistency check that cross-references each
    ExecPlan's status against its roadmap checkbox. Add a `make`/CI guard that
    fails when an ExecPlan is marked COMPLETE while its matching roadmap task is
    still `- [ ]`.
  - Requires 6.2.1.
  - See AGENTS.md "Quality gates"; docs/roadmap.md; docs/execplans/.
  - Success: a `make`/CI guard fails when any ExecPlan reads COMPLETE while its
    matching roadmap checkbox is unticked, passes when the two agree, and is
    wired into the documentation gate set so the drift is caught mechanically
    rather than in review.
- [ ] 7.6.20. Add an invariant test that the matrix's phase-set constants stay
  consistent with the `working_corpus`.
  - Reroute (source: review:6.2.1; severity: low). The machine matrix's expected
    ok-sign for `novel-compile` is hardcoded via `_COMPILE_OK_PHASES` while the
    semantic-branch tests key on `_DRAFTING_ERA_PHASES`, so a future
    `working_corpus` change could desync them silently (one updated, the other
    not). This serves the step-7.6 hypothesis — making a class of silent drift
    fail loudly — by deriving these sets from the corpus, or asserting their
    relationship, so a corpus change that desyncs them reddens a test rather than
    passing unnoticed. Add a small invariant test that derives
    `_COMPILE_OK_PHASES` and `_DRAFTING_ERA_PHASES` from the corpus or asserts the
    relationship between them.
  - Requires 6.2.1.
  - See novel-ralph-harness-design.md §9;
    tests/test_command_surface_matrix.py.
  - Success: an invariant test derives the matrix's `_COMPILE_OK_PHASES` and
    `_DRAFTING_ERA_PHASES` from the `working_corpus` (or asserts their
    relationship) so a corpus change that desyncs them fails loudly here rather
    than silently, and the matrix suite stays green.
- [ ] 7.6.21. Run the documentation lint gates inside the author's pre-merge code
  gate, not only the post-merge audit.
  - Reroute (source: audit:6.2.2 Finding 10 / audit:6.2.1 Finding 6; severity:
    medium; two near-identical proposals merged). Two consecutive tasks (6.2.1 and
    6.2.2) each landed the identical MD012 double-blank regression in
    `developers-guide.md`, each greening its own task-scoped gate while leaving
    whole-tree `markdownlint` red on `main` until the post-merge audit caught it.
    This serves the step-7.6 hypothesis — making a class of silent drift fail
    loudly through a mechanical guard rather than relying on a reviewer to spot
    it — by folding the doc-lint gates (`make markdownlint`, and `make nixie`)
    into the default `make all` so the author's pre-merge gate fails on the
    regression instead of the post-merge audit. Wire the documentation lint gates
    into the aggregate code-gate target so a doc regression reddens the author's
    gate.
  - Requires 6.2.1.
  - See AGENTS.md "Quality gates"; the project `Makefile` (`all` target);
    docs/issues/audit-6.2.2.md (Finding 10); docs/issues/audit-6.2.1.md
    (Finding 6).
  - Success: `make all` runs the documentation lint gates (`markdownlint` and
    `nixie`) so a whole-tree doc-lint regression fails the author's pre-merge gate
    rather than surfacing only in the post-merge audit; a planted MD012
    double-blank reddens `make all`; and the gate stays green on a clean tree.

- [ ] 7.6.22. Key the schema-drift guard's leaf net on `(table-path, leaf)`
  pairs and walk inline tables generically.
  - Reroute (source: review:2.1.8; severity: low; two near-identical proposals
    merged). The guard's leaf net is keyed on leaf name only, so a new emitted
    leaf whose name collides with an existing documented leaf under a different
    table passes silently (verified: a hypothetical `gates.final.current` would
    pass because `current` is documented under `[phase]`). It also hardcodes the
    single nested inline table `last_finding_counts` when harvesting inner keys,
    so a second inline table's inner keys would be uncovered. This is
    test-robustness hardening of the schema-drift guard, not the step-2.1
    schema-validator hypothesis where it was raised, so it is deferred here.
  - Requires 2.1.8.
  - See novel-ralph-harness-design.md §5.1;
    tests/test_state_layout_schema_guard.py.
  - Success: the leaf net is keyed on `(table-path, leaf)` pairs so a same-named
    leaf under a different table is required to be documented under that table
    (the `gates.final.current` masking case is caught); inline-table inner keys
    are harvested by a generic walk rather than a hardcoded
    `last_finding_counts` path, so a second inline table's inner keys are
    covered; and the schema-guard suite stays green against the current
    documented reference.

- [ ] 7.6.23. Broaden the legacy-surface-retired guard beyond its curated path
  list.
  - Reroute (source: audit:1.2.15; severity: low). `tests/
    test_legacy_surface_retired.py` scans only the hand-maintained
    `_IDIOM_SOURCES` and `_REPOINTED_E2E` path lists, so a legacy stamp
    re-introduced in any unlisted file passes green; audit:1.2.15's finding 4 is
    already a live miss of exactly this shape. Assert each listed path exists (so
    a rename silently emptying the scan fails loudly) and/or broaden the scan to
    walk `tests/` and `novel_ralph_skill/` wholesale, turning the curated list
    into a belt-and-braces fast path rather than the sole coverage. This serves
    the step-7.6 guard-hardening hypothesis — keeping the surface-retired proof
    robust against curated-list rot — not the step-1.2
    packaging-supports-invocation
    hypothesis where it was raised; it is regression-guard hardening, deferred
    here.
  - Requires 1.2.15.
  - See adr-007-command-surface-novel-multiplexer.md;
    docs/issues/audit-1.2.15.md;
    tests/test_legacy_surface_retired.py.
  - Success: the legacy-surface-retired guard asserts its curated paths exist
    and/or scans `tests/` and `novel_ralph_skill/` wholesale for retired
    hyphenated literals, so a legacy stamp re-introduced in a file outside the
    curated lists fails the guard; the production-module-name allowances remain
    excluded; and the test suite stays green.
- [ ] 7.6.24. Extend the legacy-surface-retired guard to the documentation and
  skill tree.
  - Reroute (source: audit:1.2.16; severity: medium). No test enforces the
    1.2.14/1.2.16 retired-surface criterion against `docs/` or `skill/`;
    `tests/test_legacy_surface_retired.py` scans only the source and test trees,
    so a retired console-script reference re-introduced in the design document,
    the guides, `SKILL.md`, or the reference files passes green — the doc-tree
    miss audit:1.2.16 found is exactly this shape. Add a doc-tree scan, with a
    narrow allowlist for historical ADR notes and the noun-form `desloppify`
    pass, so the prose criterion becomes an enforced invariant. This serves the
    step-7.6 guard-hardening hypothesis — keeping the surface-retired proof
    robust against curated-list rot — not the step-1.2
    packaging-supports-invocation hypothesis where it was raised; it is
    regression-guard hardening, deferred here.
  - Requires 1.2.14, 1.2.16, and 1.2.17.
  - See adr-007-command-surface-novel-multiplexer.md;
    docs/issues/audit-1.2.16.md;
    tests/test_legacy_surface_retired.py.
  - Success: the legacy-surface-retired guard scans `docs/` and `skill/` for
    retired hyphenated console-script references with a narrow allowlist for
    historical ADR notes and the noun-form `desloppify` pass, so a retired
    reference re-introduced in any swept document fails the guard; and the test
    suite stays green.

- [ ] 7.6.25. Stabilise the flaky reconcile-derivation totality property.
  - Reroute (source: review:6.3.2; severity: high). The Hypothesis property
    `test_reconcile_derivation::test_derivation_is_total_and_never_yields_none_on_a_violation`
    reproduces failing roughly 1 in 8 full-suite runs under `pytest -n auto`
    (the `make test` configuration via `PYTEST_XDIST_WORKERS=auto`); it is
    unchanged on the 6.3 branch, so it is a pre-existing latent defect that makes
    the commit gate non-deterministic for every task touching the suite.
    Investigate whether the reconcile derivation genuinely yields `None` on some
    violation (a real bug to fix in production) or the strategy/deadline needs
    tightening (a test fix), and resolve whichever it is. This serves the
    step-7.6 gate-determinism hypothesis — a gate that reddens only on a genuine
    regression — not the settled step-6.3 contract-uniformity hypothesis where it
    was raised.
  - Requires 2.3.1.
  - See novel-ralph-harness-design.md §5.4; AGENTS.md
    ("Python verification and testing"); the `hypothesis` and `crosshair` skills;
    novel_ralph_skill/state/reconcile.py;
    tests/test_reconcile_derivation.py.
  - Success: the root cause is identified as either a derivation defect (yields
    `None` on a violation, fixed in production) or a strategy/deadline weakness
    (tightened in the test), recorded in the execplan; the property passes
    deterministically across repeated full-suite `pytest -n auto` runs; and the
    reconcile suites stay green.
- [ ] 7.6.26. Root-cause and guard the transient first-invocation envelope
  field-order failures under `make all`.
  - Reroute (source: review:6.3.2; severity: medium). A single `make all`
    produced 101 failures all showing `messages` emitted before `result` —
    spanning the new cross-command suite and pre-existing snapshot tests — then
    never recurred across roughly 30 runs; `render_machine` is statically ordered
    and the install is editable, so the cause is unexplained, possibly a
    build/venv settling race between `make build` and `make test`. A wide, hard,
    non-reproducible gate failure undermines trust in the gate. Root-cause the
    field-order inversion and add a guard (e.g. ensure `make build` completes and
    the install resolves before test collection) so the race cannot recur. This
    serves the step-7.6 gate-determinism hypothesis — a gate that does not redden
    on a build/install settling artefact — not the settled step-6.3
    contract-uniformity hypothesis where it was raised.
  - Requires 6.3.2.
  - See novel-ralph-harness-design.md §3.1 and §9; the project `Makefile`
    (`build`/`test`/`all` targets); novel_ralph_skill/contract/envelope.py
    (`render_machine`).
  - Success: the first-invocation `messages`-before-`result` field-order
    inversion is root-caused and recorded (build/install settling race or
    otherwise); a guard ensures the build completes and the install resolves
    before test collection so the inversion cannot recur; and repeated `make all`
    runs produce the statically-ordered envelope with no transient field-order
    failures.

- [ ] 7.6.27. Anchor the prose-bullet drift guards to line-start bullets rather
  than substring presence.
  - Reroute (source: review:6.3.7; severity: low). Both
    `test_skill_envelope_bullets_name_every_field` (6.3.7) and the sibling
    prose-guards assert backtick-quoted field names appear anywhere in a region,
    which can false-pass when a field's defining bullet is deleted but the name
    survives in unrelated prose. Anchoring each guard to a `` - `name` ``
    line-start bullet pattern would make the guards say what their docstrings
    claim. This applies repo-wide to the prose-guard family, so it is
    guard-robustness hardening of the now-single-sourced guards, not the settled
    step-6.3 documentation hypothesis where it was raised, and it is deferred
    here. Coordinate with 7.5.15/7.5.16 so the anchored matching lands on the
    consolidated fence-and-slice primitives rather than per-guard copies.
  - Requires 6.3.7.
  - See novel-ralph-harness-design.md §3.1;
    tests/test_skill_contract_drift_guard.py;
    tests/_skill_contract_scanner.py.
  - Success: each field-name prose-guard anchors on a `` - `name` `` line-start
    bullet rather than substring presence; deleting a field's defining bullet
    while leaving its name in unrelated prose fails the guard; the anchored
    matching is applied across the prose-guard family; and the prose-guard suites
    stay green.

- [ ] 7.6.28. Carry the path and structured fault separately from any raw `{exc}`
  repr in the typed rule-pack and ledger `FileError` messages.
  - Reroute (source: review:6.3.8; severity: low). 6.3.8 closed the exit-3 leak
    at the command call sites by routing rule-pack and device-ledger faults
    through the path-only `_rule_pack_read_error`/`_device_ledger_read_error`
    formatters, but the underlying `RulePackFileError`/`LedgerFileError` messages
    (`novel_ralph_skill/rulepack/parse.py:390`,
    `novel_ralph_skill/ledger/parse.py:311`) still embed `cannot read … at
    {path}: {exc}`. Those typed-error messages are no longer surfaced on the
    exit-3 channel, so this is not a live actionability gap (the §6.3 hypothesis
    is already discharged) but a defence-in-depth hardening: make the typed
    errors carry the path and a structured fault separately from any raw `repr`
    so a future consumer that stringifies them cannot re-leak OS text, closing
    the leak at the source rather than only at the boundary. This is
    error-contract robustness hardening of the now-actionable channel, not the
    settled step-6.3 contract-uniformity hypothesis where it was raised, so it is
    deferred here.
  - Requires 6.3.8.
  - See novel-ralph-harness-design.md §3.2 and §3.4;
    docs/scripting-standards.md (line 678);
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/rulepack/parse.py (`RulePackFileError`);
    novel_ralph_skill/ledger/parse.py (`LedgerFileError`).
  - Success: the `RulePackFileError` and `LedgerFileError` messages carry the
    faulted path and a structured fault without interpolating the raw caught
    `{exc}` repr; stringifying either typed error no longer surfaces an `Errno`
    or other raw OS text; the `_rule_pack_read_error`/`_device_ledger_read_error`
    formatters continue to name the artefact and a remedy; and the rule-pack,
    ledger, and desloppify suites stay green.

- [ ] 7.6.29. Single-source the contract-guard helpers shared by the SKILL and
  developers'-guide prose drift-guards.
  - Reroute (source: audit:6.3.9; severity: medium). 6.3.9 reproduces three
    byte-identical contract helpers from the 6.3.7 SKILL guard — `_CODE_KEYWORDS`,
    `_meaning_has_keyword`, and `_envelope_field_order` — in
    `tests/test_developers_guide_contract_drift_guard.py`, re-creating the
    "documented once without drift" single-source failure mode at the test layer
    even though both guards already import the shared pure scanner module
    `tests/_skill_contract_scanner.py` that could host them. Promote
    `_CODE_KEYWORDS` and `_meaning_has_keyword` into that pure module so both
    guards consume one copy; coordinate the third helper, `_envelope_field_order`,
    with task 7.1.5 so it consumes the planned shared `ENVELOPE_FIELD_ORDER`
    constant rather than a fourth test-side copy. This does not serve the settled
    step-6.3 "documented once" hypothesis where it was raised — the prose copies
    are already pinned — but single-sources the guards themselves, the step-7.6
    robustness concern of hardening the now single-sourced guard suite, so it is
    deferred here.
  - Requires 6.3.9 and 7.1.5.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md;
    tests/_skill_contract_scanner.py;
    tests/test_skill_contract_drift_guard.py;
    tests/test_developers_guide_contract_drift_guard.py;
    novel_ralph_skill/contract/envelope.py.
  - Success: `_CODE_KEYWORDS` and `_meaning_has_keyword` live once in
    `tests/_skill_contract_scanner.py` and are imported by both the SKILL and
    developers'-guide drift-guards; the envelope field-order helper consumes the
    shared `ENVELOPE_FIELD_ORDER` constant from 7.1.5 rather than a fourth
    test-side copy; no byte-identical contract helper remains duplicated across
    the two guard modules; and the docs and contract suites stay green.

- [ ] 7.6.30. Guard the developers'-guide exit-3 formatter-count prose against the
  `_state_load` formatter set.
  - Reroute (source: audit:6.3.9; severity: low). 6.3.9 pinned the guide's
    exit-code table and envelope field set, but the adjacent "Two sibling
    formatters" prose is a code-derived count that has been stale since 6.3.8 —
    there are five actionable formatters in
    `novel_ralph_skill/commands/_state_load.py` — and no guard catches it because
    the 6.3.9 guard parses only the Markdown table, not the prose. Add a
    drift-guard arm asserting the guide's formatter count and names track the live
    `_state_load` exit-3 formatter set, following the repo's established
    prose-guard pattern. Coordinate with addendum 6.3.8.2, which corrects the
    prose text itself, so the guard pins the corrected count rather than the stale
    one. This extends the guard suite's coverage to a code-derived prose count the
    audits surfaced — a step-7.6 robustness concern — not the settled step-6.3
    "documented once" hypothesis where it was raised, so it is deferred here.
  - Requires 6.3.9.
  - See novel-ralph-harness-design.md §3.1;
    docs/developers-guide.md ("Two sibling formatters");
    novel_ralph_skill/commands/_state_load.py;
    tests/test_developers_guide_contract_drift_guard.py.
  - Success: a drift-guard arm fails if the developers'-guide exit-3 formatter
    count or named formatters diverge from the live `_state_load` actionable
    formatter set; the guard reuses the repo's established prose-guard pattern;
    the corrected prose from 6.3.8.2 passes the new guard; and the docs and
    contract suites stay green.

- [ ] 7.6.31. Rename `tests/_skill_contract_scanner.py` to a document-generic
  name.
  - Reroute (source: review:6.3.9; severity: low). The pure scanner now backs two
    guards — the `SKILL.md` guard (6.3.7) and the developers'-guide guard (6.3.9)
    — and its functions are document-generic, but its name still implies
    SKILL-only scope; the 6.3.9 execplan Decision Log explicitly defers this as
    a separate refactor. Rename it to a document-generic name (e.g.
    `tests/_contract_doc_scanner.py`) and update both importers, removing the
    misleading SKILL-only name without scope-creeping a docs guard. This is
    cross-cutting test-naming hygiene on the now-shared guard scanner — a step-7.6
    concern of hardening the single-sourced guard suite — not the settled step-6.3
    documentation hypothesis where it was raised, so it is deferred here.
  - Requires 6.3.9.
  - See tests/_skill_contract_scanner.py;
    tests/test_skill_contract_drift_guard.py;
    tests/test_developers_guide_contract_drift_guard.py;
    docs/execplans/roadmap-6-3-9.md (Decision Log).
  - Success: the pure scanner module carries a document-generic name; both the
    SKILL and developers'-guide drift-guards import it under the new name; no
    SKILL-only name remains for the document-generic scanner; and the docs and
    contract suites stay green.

- [ ] 7.6.32. Audit and document the keyword/anchor brittleness of the contract
  drift-guards.
  - Reroute (source: review:6.3.9; severity: low). The 6.3.7 and 6.3.9 guards pin
    Meaning cells by lenient single keywords and pin regions by exact H3 heading
    text, so a benign future re-heading or re-wording could red a guard on a
    non-divergence. Review the two guards together to decide whether to centralise
    the keyword and anchor tables and document the re-wording contract — so an
    editor knows the keyword and heading text are load-bearing — closing the gap
    where a routine docs edit reddens a guard without a real contract drift. This
    is cross-cutting robustness hardening of the guard suite against the brittle
    anchors the review surfaced — a step-7.6 concern — not the settled step-6.3
    documentation hypothesis where it was raised, so it is deferred here.
  - Requires 6.3.9.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md;
    tests/test_skill_contract_drift_guard.py;
    tests/test_developers_guide_contract_drift_guard.py;
    tests/_skill_contract_scanner.py.
  - Success: one recorded decision states whether the keyword and anchor tables
    are centralised and documents the re-wording contract naming the load-bearing
    keywords and heading text; if centralised, both guards consume the shared
    tables; a benign re-heading or re-wording that preserves the contract no
    longer reds a guard (or the load-bearing text is explicitly documented as such);
    and the docs and contract suites stay green.

- [ ] 7.6.33. Enable ruff `ARG` (unused-argument) in the lint select and triage
  the existing intentional unused arguments.
  - Reroute (source: audit:7.1.3 / audit:7.1.4; severity: low; two consecutive
    §7.1 audits naming the same gap, merged). The codebase's functional style —
    many small projections and mutators threaded through call sites, and (since
    7.1.4) a `build_finding_outcome` builder parameterised over four injected
    callables — makes refactor-orphaned parameters a recurring risk that a gate
    should catch rather than an audit; 7.1.3's refactor left `_write_outcome`'s
    `action` parameter dead and ruff did not flag it because `ARG` is absent from
    the `select` list. Add `"ARG"` (flake8-unused-arguments) to
    `pyproject.toml` `[tool.ruff.lint] select`, triaging the intentional unused
    arguments (interface/callback conformance) with local `# noqa: ARG00x` plus
    a one-line reason or the leading-underscore convention, turning this whole
    class of defect into a gate failure. This is cross-cutting lint-gate
    hardening, not the settled step-7.1 single-canonical-projection hypothesis
    where it was raised, so it is deferred here.
  - Requires 7.1.3, 7.1.4.
  - See AGENTS.md (quality gates); `pyproject.toml` (`[tool.ruff.lint] select`);
    docs/issues/audit-7.1.3.md (Finding 3); docs/issues/audit-7.1.4.md
    (Finding 4); novel_ralph_skill/contract/finding_outcome.py.
  - Success: `"ARG"` is in the ruff `select` list; every existing intentional
    unused argument is triaged with a local `# noqa: ARG00x` plus a reason or the
    leading-underscore convention; a deliberately-orphaned parameter reddens the
    lint gate; and `make all` stays green.

- [ ] 7.6.34. Add an enforced docstring cross-reference resolution check to the
  lint gate.
  - Reroute (source: review:7.1.2; severity: low). The spine relies heavily on
    Sphinx-style `:func:`/`:class:`/`:attr:` cross-references in docstrings as the
    primary documentation-DRY mechanism — the §7.1 consolidation adds several
    more — yet no gate validates that those targets resolve, so cross-reference
    rot is silent: a future rename could leave dangling pointers that pass
    `make all`. Add a lightweight reference-resolution check (a `sphinx -n`
    nitpicky docs build, or a custom AST/regex linter that resolves each
    cross-reference target) so a dangling `:func:` reference reddens the gate,
    protecting the consolidation pattern the whole §7.1 line invests in. This is
    cross-cutting lint-gate hardening, not the settled step-7.1
    single-canonical-projection hypothesis where it was raised, so it is deferred
    here.
  - Requires 7.1.6.
  - See AGENTS.md (quality gates); the project `Makefile`;
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/state/done_predicate.py.
  - Success: a reference-resolution check runs in the gate and resolves every
    docstring `:func:`/`:class:`/`:attr:` cross-reference; a deliberately-dangling
    cross-reference reddens the gate; and `make all` stays green on the current
    tree.

- [ ] 7.6.35. Collapse `Reconciliation`'s recount Optionals into a single co-set
  recount sub-shape.
  - Reroute (source: review:7.1.3; severity: low). `recounted_current`
    (`int | None`) and `recounted_by_chapter` (`Mapping | None`) are independent
    Optionals on the `Reconciliation` dataclass but are invariantly set together
    by the sole `_recount` constructor, and `reconciliation_payload` now leans on
    that co-set invariant (gating on `by_chapter` while emitting `current`).
    Represent the recount data as one Optional value (e.g. a frozen
    `RecountResult{current, by_chapter}`), updating the `_recount` constructor and
    the payload projection, so the co-set invariant is
    unrepresentable-when-violated and the latent `None`-`current` edge the
    projection currently inherits is removed. This hardens the reconciliation
    payload against the edge case the review surfaced — a step-7.6 concern — not
    the settled step-7.1 single-canonical-projection hypothesis where it was
    raised, so it is deferred here.
  - Requires 7.1.3.
  - See novel-ralph-harness-design.md §3.3 and §5.4;
    docs/issues/audit-7.1.3.md; novel_ralph_skill/state/reconcile.py.
  - Success: the recount data is carried by one Optional co-set value on
    `Reconciliation`; the `_recount` constructor and `reconciliation_payload`
    consume it so a present-recount with a `None` `current` is unrepresentable;
    the exit-code policy and the projected payload shape are unchanged; and the
    reconcile, check, and disk-evidence suites stay green.

- [ ] 7.6.36. Pin post-merge audit filenames to the roadmap id at merge time so
  a renumber cannot orphan an audit.
  - Reroute (source: audit:7.1.2 Finding 1; severity: high). A roadmap renumber
    left a stale `audit-7.1.2.md` auditing the device-ledger task (now roadmap
    8.1.2) under the wrong number, so a reader consulting it for the
    compile-projection consolidation found an unrelated feature; the live
    cross-package duplication finding it carried is now homed correctly by task
    7.2.2, but nothing prevents the next renumber from orphaning another audit.
    The duplication analysis itself needs no further action (7.2.2 owns it); this
    task settles the forward-looking convention. Record a build-workflow rule that
    derives the post-merge audit filename from the task's roadmap id at merge time
    (and/or carries the audited commit and roadmap-id in a header the auditor
    writes), so a later renumber cannot silently mis-file an audit; capture it in
    AGENTS.md or docs/scripting-standards.md. This serves the step-7.6
    documentation-process-robustness hypothesis — making the audit trail robust
    to predictable renumber churn — not the settled step-7.1
    single-canonical-projection hypothesis where it was raised. Coordinate with
    7.6.8 so the audit-artefact convention is consistent with the design-review
    artefact convention settled there.
  - Requires 1.3.1.
  - See AGENTS.md; docs/scripting-standards.md;
    docs/issues/audit-7.1.2.md (Finding 1); docs/issues/ (the `audit-*.md`
    artefacts); the `df12-build` workflow audit step.
  - Success: a recorded convention derives the post-merge audit filename (or a
    written-in header) from the task's roadmap id at merge time; AGENTS.md or
    docs/scripting-standards.md names the convention; the convention is consistent
    with 7.6.8's artefact handling; and a renumber scenario can no longer leave
    an audit pointing at the wrong task without a gate or header revealing it.

- [ ] 7.6.37. Guard the envelope renderers against a future `Envelope` field
  addition (machine coercion completeness and the human-channel subset).
  - Reroute (source: review:7.1.5, audit:7.1.5; severity: low; two near-identical
    renderer-drift proposals merged). 7.1.5 tied `render_machine`'s field order
    to the `Envelope` dataclass, but two renderer edges still rest on hand-kept
    knowledge that a future field addition silently breaks. (a) `_FIELD_COERCIONS`
    in `contract/envelope.py` is keyed by field name and silently passes through
    any unlisted field, so a future frozen mapping/sequence field (frozen in
    `__post_init__`) would have `json.dumps` see a `MappingProxyType`/tuple with
    no test forcing a coercion registration. (b) `render_human` emits a
    hand-spelled subset (omitting `schema_version` and `result`) with no drift
    guard and an incomplete docstring, so a new field silently leaves the human
    channel stale.
    Add a guard asserting every frozen-container `Envelope` field has a
    `_FIELD_COERCIONS` coercion (or round-trips a freshly built envelope of every
    field), and tighten `render_human`'s docstring plus a subset assertion against
    `ENVELOPE_FIELD_ORDER`. This hardens the now single-sourced renderer against
    the edge the audits surfaced — a step-7.6 robustness concern — not the settled
    step-7.1 single-canonical-projection hypothesis where it was raised, so it is
    deferred here.
  - Requires 7.1.5.
  - See novel-ralph-harness-design.md §3.1;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/contract/envelope.py (`render_machine`, `render_human`,
    `_FIELD_COERCIONS`);
    tests/test_contract_envelope.py.
  - Success: a guard fails if any frozen-container `Envelope` field lacks a
    `_FIELD_COERCIONS` coercion; `render_human`'s docstring names its deliberate
    field subset and a subset assertion fails if that subset drifts from
    `ENVELOPE_FIELD_ORDER`; adding a frozen field without a coercion, or a new
    field that silently strands the human channel, reddens a test; and the
    contract and cross-command suites stay green.

- [ ] 7.6.38. Pre-emptively split the three modules sitting against the 400-line
  cap onto a deliberate seam.
  - Reroute (source: audit:7.1.5; severity: low). Three source modules sit at
    389-399 lines against the AGENTS.md 400-line cap
    (`commands/_gate_drafting_mutators.py` at 399, `rulepack/parse.py` at 392,
    `commands/_desloppify.py` at 389), so the next routine edit will breach the
    cap and force an unplanned mid-task split. Identify a deliberate seam for each
    now — mirroring the `_skill_contract_scanner.py` and `rulepack/parse.py`
    (5.1.1.6) split patterns — and extract it, so cap pressure is relieved
    proactively rather than reactively during an unrelated task. This is standing
    maintainability hygiene against the cap risk the audit surfaced — a step-7.6
    robustness concern — not the settled step-7.1 single-canonical-projection
    hypothesis where it was raised, so it is deferred here.
  - Requires 5.1.1, 7.1.5.
  - See AGENTS.md (the 400-line module cap);
    novel_ralph_skill/commands/_gate_drafting_mutators.py;
    novel_ralph_skill/rulepack/parse.py;
    novel_ralph_skill/commands/_desloppify.py;
    docs/execplans/roadmap-5-1-1.md (the `parse.py` split pattern).
  - Success: each of the three modules is under the 400-line cap with headroom on
    a deliberate, named seam; no behaviour changes; and `make all` stays green.

- [ ] 7.6.39. Widen the §7.1 projection drift-guard registry to the
  normalised-but-unguarded compile-family siblings.
  - Reroute (source: review:7.1.6; severity: low). 7.1.6 (Work item 1) normalised
    the `concatenate_drafts` / `present_draft_bodies` / `compile_manuscript`
    cross-references for consistency but, by its recorded coverage boundary, did
    not add them as guarded rows in `test_projection_docstring_drift_guard.py`,
    so those projections are normalised-but-unguarded and could silently re-fork
    without reddening the guard. Once their wider consumer graph is audited, add
    a `(authoritative, consumers, canonical_path, reexport_tail, table_markers)`
    row per sibling so the convention 7.1.6 applied to them is enforced. This
    hardens the now single-sourced guard suite against the residual coverage gap
    the review surfaced — a step-7.6 robustness concern — not the settled
    step-7.1 single-canonical-projection hypothesis where it was raised, so it is
    deferred here.
  - Requires 7.1.6.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    docs/execplans/roadmap-7-1-6.md (Work item 1);
    tests/test_projection_docstring_drift_guard.py.
  - Success: each normalised compile-family sibling
    (`concatenate_drafts`, `present_draft_bodies`, `compile_manuscript`) carries
    a guarded registry row binding its authoritative docstring to its audited
    consumers; re-forking any of them reddens the guard; and the compile and
    contract suites stay green.

- [ ] 7.6.40. Strengthen the projection drift-guard's authoritative-table markers
  from bare substrings to structural table assertions.
  - Reroute (source: review:7.1.6; severity: low). The compile row's
    `table_markers` (`MATCHES`/`ABSENT`/`DIVERGES`) in
    `test_projection_docstring_drift_guard.py` are bare substrings that also appear
    as scattered `:attr:` references, so a hollowing that retains a single `:attr:`
    reference but deletes the polarity prose passes the guard. Assert a richer,
    table-specific phrase per authoritative symbol (as the reconciliation row's
    `{action, discrepancies, detail}` marker already does) so the inverse-of-
    accepted-residual hollowing path closes. This hardens the guard against the
    brittle-marker gap the review surfaced — a step-7.6 robustness concern — not
    the settled step-7.1 single-canonical-projection hypothesis where it was
    raised, so it is deferred here.
  - Requires 7.1.6.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    tests/test_projection_docstring_drift_guard.py.
  - Success: each authoritative symbol's `table_markers` assert a table-specific
    phrase (not a bare enum-name substring that also occurs as a scattered
    `:attr:` reference); a docstring that retains one `:attr:` reference but
    deletes the polarity/table prose reddens the guard; and the compile, reconcile,
    and contract suites stay green.

- [ ] 7.6.41. Add a completeness check tying the §7.1 drift-guard registry to the
  documented projection family.
  - Reroute (source: audit:7.1.6; severity: low). The projection drift-guard pins
    only the rows it already knows about; nothing forces a newly consolidated
    §7.1 projection to be registered, so a future task could correctly
    single-source a projection and silently omit its drift-guard row, defeating
    the single-source-of-truth invariant the convention claims. Declare a
    `CONSOLIDATED_PROJECTIONS` manifest (or equivalent) and assert it is covered
    by `_REGISTRY`, so an unregistered consolidated projection reddens a test. This
    hardens the guard's completeness invariant the audit surfaced — a step-7.6
    robustness concern — not the settled step-7.1 single-canonical-projection
    hypothesis where it was raised, so it is deferred here. Coordinate with 7.6.39,
    which fills the known coverage gap, so the manifest and the registered rows
    agree.
  - Requires 7.1.6.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    tests/test_projection_docstring_drift_guard.py.
  - Success: a declared manifest of consolidated §7.1 projections is checked
    against `_REGISTRY` so an unregistered consolidated projection fails a test;
    the manifest and the registered rows agree (with 7.6.39); and the contract and
    compile suites stay green.

- [ ] 7.6.42. Broaden the canonical-module-path drift gate to cover the design
  document and the ADRs.
  - Reroute (source: review:7.3.1; severity: low). The 7.3.1 rename gate (WI5)
    scoped its source-file citation checks to `novel_ralph_skill/`, `tests/`, and
    `docs/developers-guide.md`, leaving design-document and ADR source-file
    citations unguarded — precisely how the dangling `_state_load.py` citation at
    `docs/novel-ralph-harness-design.md:163` survived the rename and reached the
    dual review. A module rename in any future task can silently dangle a
    design-doc or ADR source-file citation with no gate to catch it. Add a guard
    (or widen the standard rename-checklist grep scope) covering
    `docs/novel-ralph-harness-design.md` and `docs/adr-*.md` for module-path and
    source-file citations, excluding the immutable historical records under
    `docs/execplans/`, `docs/issues/`, and `docs/roadmap.md`. This hardens the
    rename/citation gate against the blind spot the review surfaced — a step-7.6
    robustness concern (the spine's gates made robust against the edge cases the
    audits surfaced) — not the settled step-7.3 single-home hypothesis where it
    was raised, so it is deferred here.
  - Requires 7.3.1.
  - See novel-ralph-harness-design.md §4 and §5.4;
    docs/developers-guide.md;
    docs/novel-ralph-harness-design.md;
    docs/adr-003-shared-interface-contract.md;
    docs/execplans/roadmap-7-3-1.md (WI5 gate block; Decision D11 correction).
  - Success: the canonical-module-path / source-file citation gate covers
    `docs/novel-ralph-harness-design.md` and `docs/adr-*.md` (with the immutable
    historical records excluded); a module rename that dangles a design-doc or ADR
    source-file citation reddens the gate; the existing citations pass; and `make
    markdownlint`, `make nixie`, and `make all` stay green.
- [ ] 7.6.43. Add an ExecPlan-internal consistency gate flagging acceptance
  probes and expected-output prose unreconciled with later Decision-Log
  deviations.
  - Reroute (source: review:7.2.4; severity: low). Task 7.2.4 shipped correct
    code beneath an ExecPlan whose acceptance probes (`False False`) contradicted
    its own Decision Log and the delivered behaviour (`False True`): the drafted
    `not hasattr(detect, "LineHit")` probe was superseded by D-LINEHIT-RUNTIME yet
    the probe text was only reconciled by a follow-up fix round
    (D-PINTEST-RECONCILE), not caught at gate time. This is the same class of
    silent living-document drift 7.6.19 hardens for the COMPLETE/checkbox skew —
    expected-output text drifting from the delivered behaviour a later
    Decision-Log entry records. It does not serve the settled step-7.2 single-home
    hypothesis (the relocation is done); it makes a class of ExecPlan
    living-document drift fail loudly, a step-7.6 robustness concern, so it is
    rerouted here. Add a lightweight df12-build audit/gate check that flags an
    ExecPlan whose acceptance-criteria or expected-output text (probes, `make`
    transcripts, observable-behaviour bullets) is not reconciled with the
    deviations recorded in its Decision Log or Surprises sections, sequenced after
    7.6.19 so it builds on the same ExecPlan-consistency machinery.
  - Requires 7.6.19.
  - See AGENTS.md "Quality gates"; docs/roadmap.md; docs/execplans/;
    docs/execplans/roadmap-7-2-4.md (Decisions D-PINTEST-LINEHIT,
    D-PINTEST-RECONCILE).
  - Success: a `make`/CI check (or df12-build audit step) flags an ExecPlan whose
    acceptance probes or expected-output prose still assert an outcome a later
    Decision-Log or Surprises entry supersedes; the check reddens against the
    pre-reconciliation 7.2.4 ExecPlan state (the `False False` probe) and passes
    once the prose is reconciled with the delivered behaviour; and `make
    markdownlint`, `make nixie`, and `make all` stay green.

### 7.7. Reconcile the documentation and settle the conventions

This step answers whether the ADRs, guides, and design read true against the
shipped behaviour and the open naming, formatting, durability, and measurement
conventions are settled once.

- [ ] 7.7.1. Decide and document the fsync/durability policy for atomic state
  writes.
  - Reroute (source: review:2.2.1; severity: low). The atomic writer in
    `novel_ralph_skill/state/document.py` and the canonical
    `docs/scripting-standards.md` "Reading / writing files and atomic updates"
    pattern it follows both omit an `fsync` of the temporary file and the parent
    directory before `Path.replace`, so process-crash recovery is sound but
    power-loss durability is undefined. Make the house-wide decision once — adopt
    an `fsync`-before-replace durability guarantee, or record power-loss
    durability as explicitly out of scope with its rationale — and capture it in
    `docs/scripting-standards.md` (and design §3.4) so every mutator inheriting
    the helper shares one contract.
  - Requires 2.2.1.
  - See novel-ralph-harness-design.md §3.4 and §5.3;
    docs/scripting-standards.md "Reading / writing files and atomic updates".
  - Success: `docs/scripting-standards.md` states the durability contract for
    atomic writes explicitly, the atomic-write helper conforms to whatever the
    contract decides, and design §3.4 cross-references the decision so no later
    mutator re-litigates it.

- [ ] 7.7.2. Decide and document the structured-logging policy for the spine
  mutators.
  - Reroute (source: review:2.3.1; severity: low). `recount`, like
    `set-cursor` and `advance-phase`, emits only a human `messages` line and no
    structured operator log, so the Ralph loop has no consistent observability
    surface beyond the JSON envelope. Make the house-wide decision once: adopt a
    shared structured-logging approach across every mutator (a common log seam
    the envelope helpers feed), or record the envelope as the agreed operability
    surface with power-user logging explicitly out of scope — and capture it in
    the developers' guide so later mutators inherit one contract rather than
    accreting per-command logging.
  - Requires 2.3.1.
  - See novel-ralph-harness-design.md §3.1 and §3.2;
    docs/adr-003-shared-interface-contract.md; docs/developers-guide.md.
  - Success: the developers' guide states the mutator observability contract
    explicitly, the existing mutators conform to whatever the contract decides,
    and no later mutator re-litigates per-command logging.

- [ ] 7.7.3. Replace the "compile-and-hash" / "digest" prose with the
  byte-comparison the code performs across the four documents and the
  `_compile.py` docstring.
  - Reroute (source: audit:3.1.2 / audit:3.1.3; severity: medium; two
    near-identical proposals merged). The `compile_consistent` clause and the
    shared `compiled_matches_drafts` helper perform a direct byte comparison with
    no `hashlib`, but the design document (§2.3/§4.2/§4.3, including "the
    per-chapter hashes it computed internally"), the developers' guide
    (line 329 "compile-and-hash routine", contradicting line 592's
    "direct byte comparison, not a digest"), the roadmap prose, and the
    `_compile.py` / `compile_model.py` docstrings all still describe a
    "compile-and-hash" routine. A docs-only sweep dropping the "hash"/"digest"
    language in favour of "compile-and-compare" / byte-comparison would make the
    prose, the code (`D-BYTE-COMPARE`), and the open `--check` task (4.1.2) agree,
    and removes the developers' guide self-contradiction. This is cross-cutting
    documentation-truthfulness hygiene, not the settled step-3.1 done-predicate
    hypothesis where it was raised, so it is deferred here.
  - Requires 3.1.3.
  - See novel-ralph-harness-design.md §2.3, §4.2, and §4.3;
    docs/developers-guide.md (lines 329 and 592);
    docs/issues/audit-3.1.2.md; docs/issues/audit-3.1.3.md;
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/commands/_compile.py.
  - Success: no "compile-and-hash", "hash", or "digest" language describes the
    compile-consistency mechanism in the design document, the developers' guide,
    the roadmap prose, or the `_compile.py`/`compile_model.py` docstrings; the
    prose describes the byte comparison (`D-BYTE-COMPARE`) the code performs; the
    developers' guide no longer self-contradicts; and `make markdownlint` and
    `make nixie` stay green.

- [ ] 7.7.4. Register a shared Hypothesis profile for disk-bound property tests
  and sweep for any property still inheriting the 200ms default.
  - Reroute (source: review:3.1.2; severity: low; two near-identical proposals
    merged). The 3.1.2 property test breached the default 200ms deadline because
    it rebuilds a corpus tree per example, and several property tests independently
    re-declare the same `@settings(deadline=None, max_examples=...,
    suppress_health_check=[HealthCheck.function_scoped_fixture])`. Register one
    named Hypothesis profile (via a `conftest` `register_profile`) so the deadline
    policy is uniform and a new disk-bound property cannot silently inherit the
    fragile default, and sweep every filesystem- or parse-touching `@given` test
    to confirm it honours the policy. This is cross-cutting test-robustness
    hygiene, not the settled step-3.1 done-predicate hypothesis where it was
    raised, so it is deferred here.
  - Requires 3.1.2.
  - See novel-ralph-harness-design.md §9;
    docs/execplans/roadmap-3-1-2.md.
  - Success: one named Hypothesis profile lives in a shared `conftest` and the
    disk-bound property tests load it rather than re-declaring the deadline
    settings; an audit confirms every filesystem- or parse-touching `@given` test
    honours the no-deadline policy; and the property suite stays green.

- [ ] 7.7.5. Adopt a fixed-precision convention for derived machine-payload
  percentages across the envelope contract.
  - Reroute (source: review:6.1.1; severity: low). `wordcount` (and potentially
    other commands) emit raw, unrounded float percentages in the machine
    `result`; for ratios that do not terminate this serialises long floats and
    risks snapshot churn and awkward downstream parsing. Decide one house
    convention for the precision of derived numeric envelope fields (e.g. round
    percentages to two decimal places, or emit basis-point integers), record it
    in the design or developers' guide as part of the envelope contract, and
    apply it uniformly to every command that emits a derived percentage or ratio
    so the machine payloads are stable. This is cross-cutting
    envelope-contract-stability hygiene, not the settled step-6.1
    disk-derivation hypothesis where it was raised, so it is deferred here.
  - Requires 6.1.1.
  - See novel-ralph-harness-design.md §3.1 and §4.5;
    docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_wordcount_report.py.
  - Success: one fixed-precision (or basis-point) convention for derived
    machine-payload percentages and ratios is recorded once in the envelope
    contract documentation; every command emitting a derived percentage or ratio
    applies it so a non-terminating quotient cannot serialise as a long churning
    float; the wordcount snapshots are regenerated to the stable form; and
    `make markdownlint` and `make nixie` stay green.

- [ ] 7.7.6. Reconcile the gate-ratio prose across design §5.2 and
  `state-layout.md` with the validator's `sum(by_chapter) / target` formula.
  - Reroute (source: review:2.2.4; severity: low; two near-identical proposals
    merged). Design §5.2 (the gate-ratio-consistent invariant) and
    `skill/novel-ralph/references/state-layout.md` (the gate-ratio binding
    prose) describe the ratio as `word_counts.current / word_counts.target`, but
    `validate.py:_check_gate_ratio_consistent` deliberately uses
    `sum(by_chapter.values()) / target`, so the source-of-truth documents
    contradict the shipped behaviour and `state-layout.md`'s two adjacent
    formulae read as inconsistent. Reconcile the prose to the validator's
    drafted-ratio formula (a doc-only change — the validator is the intended
    behaviour and is not to be touched), removing a recurring source of reviewer
    and implementer confusion. This is documentation-truthfulness hardening, not
    the settled step-2.2 write-discipline hypothesis where it was raised, so it
    is deferred here.
  - Requires 2.2.4.
  - See novel-ralph-harness-design.md §5.2;
    skill/novel-ralph/references/state-layout.md;
    novel_ralph_skill/state/validate.py (`_check_gate_ratio_consistent`).
  - Success: the gate-ratio prose in design §5.2 and `state-layout.md` describes
    the ratio as `sum(by_chapter) / target`, agreeing with the validator and
    with the clarifying sentence task 2.2.4 added; the two formulae in
    `state-layout.md` no longer contradict each other; the validator is
    unchanged; and the documentation lint gates stay green.

- [ ] 7.7.7. Decide and enforce the corpus-wide spelling convention.
  - Reroute (source: audit:1.2.16; severity: low). The existing corpus uses
    `-ise`/`-isation` uniformly while the build instruction stipulates Oxford
    `-ize`/`-ization`; the two conventions are in standing tension, leaving each
    author to guess per task. Make the deliberate decision once — which
    convention governs — and add a lint or spell-check rule that holds the prose
    to it, reconciling the build instruction and the corpus so the ambiguity is
    removed rather than re-litigated. This serves the step-7.7
    spelling-convention hypothesis, not the step-1.2
    packaging-supports-invocation hypothesis where it was raised; it is a
    cross-cutting prose-quality decision, deferred here.
  - Requires 1.3.1.
  - See AGENTS.md (the en-GB Oxford-spelling convention); the `en-gb-oxendict`
    skill.
  - Success: one decision records which spelling convention governs the corpus,
    AGENTS.md and the corpus agree with it, a lint or spell-check rule enforces
    the chosen convention, and a deliberately misspelt sample fails that rule.

- [ ] 7.7.8. Instrument and measure the realised per-chapter deflation, then
  confirm or retune the acceptance bands.
  - Reroute (source: review:6.1.2; severity: medium; three near-identical
    proposals merged — a calibration probe, an end-to-end convergence fixture,
    and the band re-calibration after several novels). The Phase 8 (115–125%
    pre-cut) and Phase 9 (97–103%) bands derive from one beta run, and the
    `tests/test_skill_deflation_guard.py` substring guard pins only the mechanism's
    *presence*, never whether a full draft-plus-desloppify-plus-critic run lands
    in band. Add instrumentation (a `wordcount`/recount reporting hook, or a
    measured shrinkage report) so the realised pre-cut-to-post-cut shrinkage is
    recorded per chapter, plus a corpus-level or beta-replay convergence check
    that a representative manuscript lands within the Phase 9 band; then confirm
    the bands converge chapters within target rather than firing the
    log-and-advance escalation on most chapters, and retune the bands from the
    measured distribution if needed. This does not serve the step-6.1
    disk-derivation hypothesis — it is an empirical calibration of the model's
    expansion judgement cross-cutting the drafting workflow — so it is rerouted
    here rather than parked in 6.1.
  - Requires 6.1.2, 6.2.1.
  - See novel-ralph-harness-design.md §7.2 and §4.5; SKILL.md Phases 8-9;
    `docs/adr-001-deterministic-judgemental-boundary.md`.
  - Success: a measured per-chapter desloppify-plus-critic shrinkage distribution
    is recorded across more than one drafted manuscript, a convergence check
    confirms a representative manuscript lands within the Phase 9 97–103% band
    (or the bands are retuned from the data so it does), and the recorded headroom
    factor is justified by the measurement rather than the original estimate.

- [ ] 7.7.9. Reconcile the command surface in ADRs 008-010 and `contents.md`
  with ADR 007.
  - Reroute (source: audit:1.2.17; severity: low). ADRs 008-010 (authored
    against the `novel-state` surface) and the `docs/contents.md` index still
    name the retired surface — ADR 008 (around line 52) presents a runnable
    `novel-state set-chapters` bash example, and `contents.md`, a live index,
    names `novel-state set-chapters`, `novel-state check`, and the gate/drafting
    mutators in the retired form. ADR 007's migration plan never scoped these.
    Either flip the inline invocations to the `novel <sub>` form while preserving
    each ADR's narrative, or add an ADR-007 surface-note to ADRs 008-010;
    `contents.md`, being a live index, should name the current surface
    regardless. ADR 005 must keep the retired names as its superseded record.
    This serves the step-7.7 documentation-currency hypothesis — making the live
    indices and inline examples name the shipped surface — not the step-1.2
    packaging-supports-invocation hypothesis where it was raised; it is
    documentation reconciliation, deferred here.
  - Requires 1.2.14, 1.2.16, and 1.2.17.
  - See adr-007-command-surface-novel-multiplexer.md;
    docs/adr-008-chapter-manifest-mutator.md;
    docs/adr-009-drafting-bijection-relaxation.md;
    docs/adr-010-gate-drafting-mutators.md; docs/contents.md.
  - Success: no runnable retired `novel-state`/`novel-compile` invocation
    survives in ADRs 008-010 or `docs/contents.md` (each is flipped to the
    `novel <sub>` form or carries an explicit ADR-007 surface-note), the
    `contents.md` index names the current surface, ADR 005 keeps the retired
    names as its superseded record, and `make markdownlint` and `make nixie`
    pass on the edited docs.

- [ ] 7.7.10. Settle and apply the exit-3 message directory-naming polarity
  against the resolved `working_dir` field.
  - Reroute (source: audit:6.3.4 Findings 1-2 / audit:6.3.5 Findings 1-2;
    severity: medium; two near-identical proposals merged). 6.3.4 made the
    envelope `working_dir` field absolute/resolved while every human-readable
    message naming the same directory stayed cwd-relative (the disk-evidence
    fault, the done-predicate fault, the init refusal and success, the
    `_state_input_error` corrupt arm, and two channels within a single `init`
    envelope), and 6.3.5 then added six more relative-path message sites via
    `_draft_read_error`, widening the gap. The design document and developers'
    guide now assert a misresolution is visible "in the field the harness reads",
    which holds for the JSON field but not the prose an operator reads during a
    fault. Decide the polarity once — thread `resolved_working_dir()` into
    `_draft_read_error` and `_state_input_error` so the messages name the resolved
    path, or document relative-by-design as the deliberate contract with its
    rationale — apply it consistently across both formatters, and add a test
    driving from inside `working/` to pin the chosen polarity (the message channel
    is currently untested). This is documentation-and-message reconciliation
    fitting the §7.7 leg, not the settled step-6.3 contract-uniformity hypothesis
    where it was raised, so it is deferred here. Coordinate with 6.3.8 so the
    write/file-fault formatters adopt the same settled polarity.
  - Requires 6.3.4 and 6.3.5.
  - See novel-ralph-harness-design.md §3.2 and §3.4;
    docs/developers-guide.md; docs/adr-003-shared-interface-contract.md;
    novel_ralph_skill/commands/_state_load.py
    (`_state_input_error`, `_draft_read_error`).
  - Success: one decision records whether the exit-3 messages name the resolved
    absolute `working/` path or are relative-by-design; `_draft_read_error` and
    `_state_input_error` apply the chosen polarity consistently across every
    message site; a test driving from inside `working/` pins the chosen message
    channel; the design document and developers' guide read true against the
    settled polarity; and the state-input, draft-read, and docs lint suites stay
    green.

- [ ] 7.7.11. Settle a docstring convention barring transient plan-artefact
  citations from shipped production docstrings, and sweep the §7.1 modules clean.
  - Reroute (source: audit:7.1.6; severity: low). Several §7.1-area production
    modules embed transient ExecPlan tags, round-review points, and `audit:`
    back-references in `__doc__` (for example `compile_model.py`, the
    `_state_load.py` formatters, and `_compile.py`), coupling public docstrings
    to plan artefacts a future reader cannot resolve and pushing the prose-to-code
    ratio up against the 400-line cap. Settle one documentation-style convention
    — docstrings cite design sections, ADRs, and stable symbols, never ExecPlan
    or Decision-Log artefacts — record it in the developers' guide, and sweep the
    §7.1 modules to remove the transient citations. This serves the step-7.7
    documentation-and-convention hypothesis (the guides and code read true and the
    open conventions are settled once), not the settled step-7.1
    single-canonical-projection hypothesis where it was raised, so it is rerouted
    here. Coordinate with 7.6.38, whose cap-pressure relief this sweep partly
    serves.
  - Requires 7.1.6.
  - See novel-ralph-harness-design.md §4.3 and §5.4;
    docs/developers-guide.md;
    novel_ralph_skill/state/compile_model.py;
    novel_ralph_skill/state/_state_load.py;
    novel_ralph_skill/commands/_compile.py.
  - Success: the developers' guide records a docstring-citation convention barring
    transient ExecPlan/Decision-Log/round-review back-references from shipped
    production docstrings; the §7.1-area modules carry no such transient citation
    in `__doc__`; the lowered prose-to-code ratio relieves cap pressure on the
    affected near-cap files; and `make markdownlint`, `make nixie`, and `make all`
    stay green.

- [ ] 7.7.12. Settle the docs-voice and lint convention for frozen execplan
  review artefacts.
  - Reroute (source: review:7.2.2; severity: low). The frozen review snapshots
    under `docs/execplans/` (for example `roadmap-7-2-2.review-r1.md` and
    `.review-r2.md`, and the equivalent snapshots on prior branches) carry
    first-person voice that repeatedly trips CodeRabbit, producing recurring
    skipped-finding noise on every later task that touches the tree. Settle the
    convention once — normalise the artefacts to the impersonal docs voice in a
    one-off sweep, or record an explicit lint-exclusion for frozen review
    snapshots — and capture the decision in the developers' guide so future review
    artefacts inherit it rather than re-accreting the noise. This serves the
    step-7.7 documentation-and-convention hypothesis (the guides read true and the
    open conventions are settled once), not the step-7.2 single-home hypothesis
    where it was raised, so it is rerouted here. Distinct from 7.7.11, which
    bars transient citations from shipped *production* `__doc__`; coordinate so
    one developers'-guide section owns both the docstring-citation and the
    review-artefact-voice conventions.
  - Requires 7.2.2.
  - See novel-ralph-harness-design.md §5.4; docs/developers-guide.md;
    docs/execplans/roadmap-7-2-2.review-r1.md;
    docs/execplans/roadmap-7-2-2.review-r2.md.
  - Success: the developers' guide records the convention for frozen execplan
    review artefacts (either an impersonal-voice normalisation or an explicit
    lint-exclusion, with its rationale); the existing review snapshots conform to
    whatever the convention decides; CodeRabbit no longer reports recurring
    skipped findings against those artefacts; and `make markdownlint`, `make
    nixie`, and `make all` stay green.

- [ ] 7.7.13. Resolve the state-sourcing seam API-privacy contradiction: settle
  the cross-module actionable-message formatters as a deliberate public surface.
  - Reroute (source: audit:7.3.1 Findings 1 and 3; severity: medium). The five
    exit-`3` actionable-message formatters (`_state_input_error`,
    `_draft_read_error`, `_compile_write_error`, `_rule_pack_read_error`,
    `_device_ledger_read_error`) are declared module-private — leading
    underscore, a "module-private" docstring, and the seam-parity test imports
    them as private — yet they are imported across the sibling command modules
    (`_compile`, `_recount`, `_novel_done`, `_desloppify`, `_desloppify_ledger`,
    `_state_mutators`) and documented in the developers' guide as the
    developer-facing exit-`3` contract shared across all five commands. The
    underscore name and the guide's contract framing contradict each other.
    Settle it one way — promote them to public names (drop the leading underscore,
    update `__all__`, the module docstring, the guide `:func:` roles, and the seam
    test) or route the cross-module surface through a public dispatcher — so the
    privacy declaration and the documented contract agree. This serves the
    step-7.7 documentation-and-convention hypothesis (the guides read true and the
    open naming conventions are settled once), not the settled step-7.3
    single-home hypothesis where it was raised: the formatters already have a
    single home in `state_sourcing`; the open question is whether their API is
    public or private, a docs-truth-and-naming concern. Coordinate with 7.7.11,
    whose docstring-citation sweep touches the same formatter docstrings.
  - Requires 7.3.1.
  - See novel-ralph-harness-design.md §3.2 and §4;
    docs/adr-003-shared-interface-contract.md;
    docs/developers-guide.md;
    novel_ralph_skill/commands/state_sourcing.py;
    tests/test_state_load_actionable_parity.py.
  - Success: one decision records whether the five actionable-message formatters
    are a public seam surface or genuinely module-private; the chosen polarity is
    applied consistently across the formatter names, `state_sourcing.__all__`, the
    module docstring, the developers' guide `:func:` roles, and the seam-parity
    test; no formatter is simultaneously underscore-private and documented as the
    developer-facing exit-`3` contract; and the contract, command, and
    actionable-parity suites stay green.
- [ ] 7.7.14. Scope the format step to the files a change actually touches.
  - The `fmt` target runs `mdformat-all`, which reformats every Markdown file in
    the repository, so a change touching one file produces churn on unrelated
    files that then has to be parked and discarded (the source of a large,
    recurring stash pile during automated runs). Scope the format step — the
    `fmt`/`mdformat-all` invocation, or a changed-files wrapper around it — so it
    rewrites only the files a change touches, leaving the rest byte-unchanged.
    Mirror the fix into the df12 template so every conformant repo inherits it.
  - See AGENTS.md (quality gates) and docs/scripting-standards.md.
  - Success: running the format step after editing one file leaves every
    unrelated file unchanged; `make markdownlint` and `make nixie` stay green;
    and an automated run no longer accrues "spurious make-fmt churn" stashes.

### 7.8. Simplify the post-relocation detector scan seams

This step answers whether the detector scan seams, now that `LineHit` and
`ScannedChapter` are co-located with `scan_pattern` in `loaderkit.scan`, are as
simple as the consolidation allows — or whether they still carry indirection and
duplication that the single-home relocation made redundant. It is a
cross-cutting CQS-and-ergonomics concern distinct from the step-7.2
single-home hypothesis (which is settled) and from the step-7.6 robustness
hypothesis (these are not edge-case hardening); confirming it leaves the
detectors expressing the scan-aggregate with no vacuous seams and no near-copy
loops.

- [ ] 7.8.1. Retire the now-vacuous `line_hit` callback from
  `loaderkit.scan.scan_pattern`.
  - Reroute (source: review:7.2.3, audit:7.2.3 Finding 2; severity: medium; two
    near-identical proposals merged). The `line_hit` callback's original
    D-SCANTYPES justification — avoid importing a hit type from a consumer
    domain — dissolved once 7.2.3 relocated `LineHit` into `loaderkit.scan`
    itself; both detectors now pass an identical forwarding
    `lambda chapter, line: LineHit(chapter=chapter, line=line)` over the module's
    own type. Decide explicitly between giving `scan_pattern` a default factory
    that constructs `LineHit` directly versus retaining the seam as a deliberate
    forward-compatibility hook, then — if removed — drop the duplicated lambdas
    from `rulepack/detect.py` and `ledger/detect.py`, delete the stale "never
    imports a pack-domain hit type" rationale from the code and the developers'
    guide, and retire or replace the `line_hit`-callback contract test 7.2.3
    added. This does not serve the settled step-7.2 single-home hypothesis (the
    relocation is done) nor step-7.6 robustness; it is cross-cutting CQS
    simplification, so it is rerouted here.
  - Requires 7.2.3.
  - See novel-ralph-harness-design.md §6.1;
    docs/adr-003-shared-interface-contract.md;
    docs/execplans/roadmap-7-2-3.md (Decision D-SCANTYPES);
    novel_ralph_skill/loaderkit/scan.py;
    novel_ralph_skill/rulepack/detect.py;
    novel_ralph_skill/ledger/detect.py;
    docs/developers-guide.md.
  - Success: the `line_hit` callback's fate is decided and documented; if
    retired, `scan_pattern` constructs `LineHit` directly, both detectors no
    longer pass a forwarding lambda, the "pack-domain hit type" rationale is gone
    from the code and the developers' guide, and the callback-contract test is
    retired or replaced by an equivalent direct-construction pin; and the
    rule-pack, ledger, and `loaderkit` suites stay green.
- [ ] 7.8.2. Extract the shared detector scan-aggregate skeleton and drop the
  redundant `scan_pattern` count return.
  - Reroute (source: audit:7.2.3 Findings 4, 5; severity: low). `detect`
    (`rulepack/detect.py`) and `detect_ledger` (`ledger/detect.py`) share a
    near-identical scan-aggregate loop, and `scan_pattern` returns a count that
    is always `len(lines)`, a redundant value that invites a CQS read/derive
    split. Extract the shared scan-aggregate skeleton into a `loaderkit` helper
    (parameterised on each pack's per-rule/per-device projection) and drop the
    vacuous count return, deriving the total from the hit tuple at the seam.
    These are ergonomics/CQS cleanups, not single-home consolidation, so they do
    not serve the step-7.2 hypothesis; they are sequenced after 7.8.1 because
    retiring the `line_hit` callback unblocks a clean helper extraction.
  - Requires 7.8.1.
  - See novel-ralph-harness-design.md §6.1;
    novel_ralph_skill/loaderkit/scan.py;
    novel_ralph_skill/rulepack/detect.py;
    novel_ralph_skill/ledger/detect.py.
  - Success: one `loaderkit` helper owns the scan-aggregate skeleton both
    detectors consume, injecting only their per-hit projection; `scan_pattern` no
    longer returns the redundant `len(lines)` count (the total is derived at the
    seam); no detector carries a near-copy aggregate loop; and the rule-pack,
    ledger, and `loaderkit` suites stay green.

## 8. Features and extensions

New capabilities, deferred until the spine is consolidated and hardened in
phase 7.

### 8.1. Configurable detection packs

Make the desloppify detection packs configurable and extend the shipped set.

- [x] 8.1.1. Ship the versioned `ai-isms.toml` pack and update cadence.
  - Requires phase 5.
  - Carry the 2026 tell set as data the maintainer owns, with `schema_version`
    versioning, so new tells land without touching the command.
  - See novel-ralph-harness-design.md §6.2.
  - Success: resolves open question Q5; adding a tell is a data edit, not a
    code change.
  - [x] 8.1.1.1. Capture the maintainer's explicit ratification of the Tier B
    ai-isms membership.
    - Addendum (from review:8.1.1; low). Tier B
      (`stands-as-a-testament`, `rich-tapestry`, `vital-role`) shipped as
      "ratified-by-plan" because the maintainer was unreachable in the
      autonomous run; obtain and record the human maintainer's ratification of
      the shipped tell set so the maintainer-owned data-contract loop the plan
      opened is closed. Lightweight addendum pass.
  - [x] 8.1.1.2. Note the one-pack-per-run limit in the users' guide and resolve
    the developers' guide combine-packs cross-reference.
    - Addendum (from audit:8.1.1; low). The developers' guide says combining
      both packs in one invocation "is a separate roadmap item and is not yet
      supported" but the item was unfiled; point that cross-reference at the
      multi-pack task (8.1.7) and add a one-line note to the `desloppify` users'
      guide section that a run scans a single pack. Lightweight addendum pass.
- [x] 8.1.2. Implement the per-novel `device-ledger.toml` enforcement.
  - Requires phase 5.
  - Enforce rationing — `max_count`, `allowed_chapters`,
    `retired_after_chapter`, `reserved_for_chapter` — recomputing current
    counts from disk every run so the ledger cannot drift.
  - See novel-ralph-harness-design.md §6.3.
  - Success: resolves open question Q3; a device spent beyond its ration is
    reported deterministically while the spend decision stays with the model.
  - [ ] 8.1.2.1. Fix the recurring MD012 double-blank in the developers' guide
    left by the 8.1.2 merge.
    - Addendum (from audit:8.1.2; medium). The 8.1.2 commit left a second
      consecutive blank line above the device-ledger heading, reddening the
      whole-tree `make markdownlint` gate on `main` (the same MD012 defect
      audit:8.1.1 Finding 7 caught before it); delete the surplus blank line. The
      structural prevention is owned by roadmap 7.6.21 and is not duplicated here.
      Lightweight addendum pass.
  - [ ] 8.1.2.2. Reject `--pack` combined with `--ledger` as an exit-2 usage
    error.
    - Addendum (from review:8.1.2; low). On the ledger path `_dispatch` never
      reads `pack`, so an operator's `--pack` selection is silently dropped,
      contradicting the developers' guide framing of `--ledger` as a scan
      "instead of the rule-pack scan"; raise a body-detected
      `DesloppifyUsageError` mirroring the existing `--ledger` + `--chapter`
      rejection so the combination exits 2 and names the conflict. Lightweight
      addendum pass.
- [x] 8.1.3. Decide whether the desloppify clean-pass output is slimmed to
  non-zero findings before the multi-pack surface grows.
  - Reroute (source: review:5.1.2; severity: low). Every clean scan currently
    serialises all rules at `count: 0`, harmless for the single §6 pack but
    growing linearly as the ai-isms and device-ledger packs ship; make the
    deliberate full-audit-trail-versus-violations-only decision once, before the
    multi-pack surface lands, so the per-hit payload contract is not changed
    churnily later. This does not serve the settled step-5.1 hypothesis
    (detection expressible as versioned data, already confirmed) — it is a
    forward-looking payload-contract decision the §7.1 packs inherit, so it is
    rerouted here rather than parked in 5.1.
  - Requires 5.1.2.
  - See novel-ralph-harness-design.md §4.4 and §6.2.
  - Success: one decision records whether a clean `desloppify` envelope carries
    every rule at `count: 0` or only over-threshold findings; the contract is
    captured in the design or developers' guide; and 8.1.1/8.1.2 emit the chosen
    shape.
  - [ ] 8.1.3.1. Extend the ledger snapshot fixture to a multi-device pack.
    - Addendum (from review:8.1.3; low). The `_LEDGER` snapshot fixture is
      single-device, so the end-to-end ledger envelope never exercises a passing
      sibling device dropping out under violations-only slimming; add a
      multi-device ledger fixture so the snapshot layer gets the same sibling-drop
      coverage the rule-pack path's one-hit snapshot enjoys. Lightweight addendum
      pass.
  - [ ] 8.1.3.2. Derive the desloppify/ledger exit code from the slimmed failed
    filter.
    - Addendum (from audit:8.1.3; low). Both `report_outcome` and
      `ledger_report_outcome` derive the exit code from `report.passed` while
      `violations`/`findings` derive from the `failed` filter, leaving a latent
      self-contradictory `ok: true` envelope with non-empty `violations`; compute
      the code from the same `failed` list so the exit code and `violations`
      cannot diverge by construction, and add a unit test pinning the invariant.
      Lightweight addendum pass.
    - Subsumed by 7.1.4. The shared `build_finding_outcome` builder
      (`novel_ralph_skill/contract/finding_outcome.py`) derives the exit code
      from the `failed` list it filters, and both `report_outcome` and
      `ledger_report_outcome` now route through it, so this divergence is closed
      by construction; `tests/test_finding_outcome.py` pins the invariant.
- [ ] 8.1.4. Add a matched-text span (or human label) to each desloppify per-hit
  finding.
  - Reroute (source: review:5.1.2; severity: low). The per-hit `phrase` field
    exposes the rule's raw regex source (e.g. `(?i)\bsmirked\b`), not the actual
    flagged words, so an adjudicating agent or human reading
    `result.findings[].phrase` receives a pattern rather than the offender;
    thread the matched span already available from `finditer` through `LineHit`
    (or render a friendly per-rule label) under a distinct key, leaving the
    stable `rule_id` contract unchanged. This enriches the per-hit output
    contract the §7.1 packs inherit rather than confirming the settled step-5.1
    hypothesis, so it is rerouted here.
  - Requires 5.1.2.
  - See novel-ralph-harness-design.md §4.4 and §6.2.
  - Success: each `result.findings[]` carries the matched offender text (or a
    human-readable label) under a distinct key, the existing `rule_id` and
    `phrase` keys are unchanged, and the snapshot suite pins the enriched shape.
- [ ] 8.1.5. Give `RuleFinding`/`LineHit` a canonical payload projection ahead of
  the multi-pack work.
  - Reroute (source: audit:5.1.2; severity: low). The desloppify report module
    (`commands/_desloppify_report.py`) hand-projects every `RuleFinding`/`LineHit`
    field, so no single place owns the JSON shape of a finding; before the
    ai-isms and device-ledger packs add richer findings, consolidate the
    projection beside the data shape so the payload and any schema cannot
    diverge. This is cross-cutting contract-maintainability for the future packs,
    not the settled step-5.1 hypothesis, so it is rerouted here and sequenced
    before 8.1.4 enriches the per-hit fields.
  - Requires 5.1.2.
  - See novel-ralph-harness-design.md §4.4 and §6.1.
  - Success: one canonical projection owns the JSON shape of a finding, the
    report module consumes it rather than re-listing fields, and the desloppify
    snapshot suite stays green.
- [ ] 8.1.6. Make the shipped ai-isms pack selectable through the CLI by a
  symbolic `--pack` name without an install-path workaround.
  - Step-task (source: audit:8.1.1; severity: high). After task 8.1.1 the
    in-wheel `ai-isms.toml` is reachable only via the `importlib.resources`
    resolver `ai_isms_pack_path()`, which is never wired into the command:
    `--pack` is bound to `pathlib.Path`, and the users' guide, developers'
    guide, and desloppify checklist all document a source-tree relative path
    (`novel_ralph_skill/rulepack/packs/ai-isms.toml`) that does not exist after
    `pip install`, so an installed user gets exit-3 "cannot read rule pack".
    This serves the step-8.1 hypothesis — that the rule-pack engine can be
    extended with the moving-target packs the design defers — by making the
    deferred ai-isms pack actually reachable through the shipped command, the
    completion of 8.1.1's stated observable success ("a novelist can run the
    installed `desloppify --pack <ai-isms>`"). It is substantial — a CLI
    resolution layer plus three document corrections pinned by a test — and
    distinct from 8.1.3-8.1.5, which are payload-contract work. Add a symbolic
    `--pack ai-isms` name that resolves shipped packs through the resolver,
    falling back to a filesystem path for bespoke packs; correct the three
    documents to the symbolic invocation; and pin the documented invocation with
    a test.
  - Requires 8.1.1.
  - See novel-ralph-harness-design.md §6.2 and §4.4;
    docs/adr-006-console-scripts-e2e-posix-policy.md;
    docs/execplans/roadmap-7-1-1.md.
  - Success: `desloppify --pack ai-isms` resolves the shipped pack on an
    installed wheel and flags an ai-ism, a bespoke filesystem `--pack PATH`
    still works, the users' guide / developers' guide / desloppify checklist
    document the symbolic invocation rather than the non-existent source-tree
    path, and a test pins the documented invocation.
- [ ] 8.1.7. Support a multi-pack desloppify invocation that combines
  `offenders.toml` and `ai-isms.toml` in one run.
  - Step-task (source: review:8.1.1; severity: medium). Task 8.1.1 ships
    ai-isms as opt-in via `--pack` precisely because a single combined run is
    deferred; the disjointness guarantee the pack carries (its rule-id set is
    disjoint from offenders) exists so the two packs can be applied together
    without double-counting. This serves the step-8.1 hypothesis — that the
    phase-5 rule-pack engine can be extended to apply the moving-target packs
    the design defers — by extending the invocation surface to run both packs in
    one scan while keeping the per-hit envelope contract the §7.1 packs inherit.
    It is substantial (an engine-invocation surface plus envelope and exit-code
    behaviour across multiple packs) and warrants its own plan and review.
  - Requires 8.1.6.
  - See novel-ralph-harness-design.md §6.1, §6.2, and §4.4;
    docs/adr-003-shared-interface-contract.md.
  - Success: a single `desloppify` invocation scans both `offenders.toml` and
    `ai-isms.toml`, reports the union of findings without double-counting a
    shared offender, keeps the §3.2 exit-code contract (4 on any violation, 0 on
    a clean pass), and the developers' guide combine-packs cross-reference
    resolves to this task.
- [ ] 8.1.8. Add an optional must-appear ration floor to the device-ledger window
  constraints.
  - Step-task (source: review:8.1.2; severity: low). Task 8.1.2 reads every
    window constraint purely negatively (a hit outside the window violates), so
    a `reserved_for_chapter` bookend the author forgot entirely passes silently;
    the developers' guide records a "must appear" floor as the highest-value
    future enhancement and design §6.3 specifies no floor today, so this is a
    deliberate, design-conformant extension rather than a defect. This serves the
    step-8.1 hypothesis — that the phase-5 rule-pack engine can be extended with
    the per-novel packs the design defers — by extending the device-ledger pack
    with a new optional floor field and an under-floor breach path, while keeping
    the recompute-from-disk-every-run discipline 8.1.2 settled. It is substantial
    (a schema field, a new breach direction, an envelope finding shape, and a
    design §6.3 amendment) and warrants its own plan and review.
  - Requires 8.1.2.
  - See novel-ralph-harness-design.md §6.3; docs/developers-guide.md
    ("The device ledger and per-novel rationing", the must-appear-floor note).
  - Success: a new optional must-appear floor field lets a device demand a
    minimum spend (e.g. a `reserved_for_chapter` bookend that must land); a
    device that lands fewer times than its floor is reported deterministically on
    a distinct under-floor breach with exit 4; the negative-window reads are
    unchanged; design §6.3 and the developers' guide record the floor; and the
    existing ledger suites stay green.
- [ ] 8.1.9. Ship a filter-word and copular-overuse density pack.
  - Requires 5.1.2.
  - The shipped packs catch fixed clichés but nothing for the most common
    prose-slop dimension: overuse of filter words and copular verbs (`was`,
    `just`, `really`, `felt`, `looked`, `seemed`, `started to`, `began to`). Add
    a versioned `filter-words.toml` pack of `per_page` density rules — each a
    word-boundaried pattern with a tuned threshold so the rule flags *overuse*,
    not every legitimate use — selectable like the ai-isms pack (8.1.6) and
    combinable (8.1.7). Calibrate thresholds against the working/ fixture corpus
    to avoid fiction false-positives (cf. 7.6). This pack is a third pack family
    beyond `offenders` and `ai-isms`, so it must bind the shared `loaderkit`
    coercion, entries, and `scan_pattern` primitives (7.2.2) — supplying one more
    error-factory bundle rather than cloning a third copy — exercising the
    error-factory seam against a third consumer and hardening its
    parameterisation against regression.
  - See novel-ralph-harness-design.md §6.1 and adr-001-deterministic-judgemental-boundary.md.
  - Success: `novel desloppify --pack filter-words.toml` flags a `was`-heavy or
    filter-word-heavy draft with per-rule density and threshold, passes a clean
    draft, the thresholds do not fire on a calibrated corpus baseline, and the
    pack's loader consumes the shared `loaderkit` primitives (a third consumer of
    the error-factory seam) rather than carrying its own coercion or scan copy.
- [ ] 8.1.10. Document the desloppify `--ledger` pack schema with a complete
  example.
  - Requires 8.1.2.
  - `desloppify --ledger` requires a top-level `schema_version` and a
    per-`[[device]]` `id`, neither documented in `desloppify-checklist.md`, so
    beta testing had to iterate to discover them. Add a complete,
    copy-pasteable `--ledger` schema example to the reference.
  - See novel-ralph-harness-design.md §6.3.
  - Success: the reference carries a complete, valid ledger example that loads
    first time.

### 8.2. Clean-context judgemental passes

Add the clean-context judgemental passes on top of the deterministic spine.

- [ ] 8.2.1. Implement the line-editor pass and its boundary.
  - Requires phase 5.
  - Run a clean-context copy-editor persona after `desloppify` and before the
    critic, scoped by the sentence-versus-scene boundary test, adjudicating
    passive-voice hits, filtering words, and micro show-don't-tell.
  - See novel-ralph-harness-design.md §7.1.
  - Success: resolves open question Q4; sentence-level fixes route to the line
    editor and scene-level fixes route to the critic, with separate prompts
    and outputs.
- [ ] 8.2.2. Wire the clean-context critic, knitting circle, and resumable
  fangirl into the per-chapter pipeline.
  - Requires 8.2.1 and phase 6.
  - Run the spiteful critic and knitting circle as clean-context sub-agents at
    peer capability, the fangirl as a resumable persistent agent, with the
    knitting circle gated by the `wordcount` triggers, and all adjudication
    returning to the orchestrator.
  - See novel-ralph-harness-design.md §7 and §7.2.
  - Success: each pass runs in the context the design assigns it, no sub-agent
    mutates state or manuscript directly, and the persona-degradation guards
    re-issue the prompt on praise drift.

### 8.3. Sentence-level structural detection

Extend desloppify with sentence-level structural detection (repeated sentence
openers and similar cross-sentence repetition).

- [ ] 8.3.1. Add a structural sentence-opener detection mode to desloppify.
  - Requires 5.1.2.
  - The detector is line-based `re.finditer` with a closed `RuleBasis` of
    `manuscript`/`per_page`, so it can anchor a pattern to sentence-initial
    position but cannot compare openers across sentences; repeated sentence
    openers and other cross-sentence repetition are therefore undetectable. Add
    a sentence-aware detection mode (a new `RuleBasis` or rule kind) that
    segments the text into sentences and flags runs of consecutive sentences
    sharing an opening token (configurable run length and scope), reported as a
    deterministic finding with line numbers and the repeated opener. Record the
    detection model extension and the sentence-segmentation choice (stdlib-only,
    no new heavy dependency) as an ADR. Keep the existing pattern bases and all
    current packs unchanged.
  - See novel-ralph-harness-design.md §6.1, §6.3, and
    adr-001-deterministic-judgemental-boundary.md.
  - Success: a draft with three or more consecutive sentences opening on the same
    word is flagged deterministically with the run and line numbers; a varied
    draft passes; the existing `manuscript`/`per_page` rules and packs are
    unaffected; and the segmentation adds no heavy dependency.
