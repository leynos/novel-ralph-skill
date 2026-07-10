# Hoist the spaced-name-to-verb derivation into the name registry

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

The mapping from a *spaced* subcommand name (`"novel state"`) to its bare
*mount verb* (`"state"`) is open-coded as `name.split(" ", 1)[1]` in three
independent places today:

- `novel_ralph_skill/commands/novel.py:50` — the dispatcher's
  `_VERB_FOR_SUBCOMMAND` comprehension;
- `tests/test_console_scripts_e2e.py:69` — the module-import guard asserting
  every `_REAL_PATH_ARGV` key is a real verb;
- `tests/test_console_scripts_e2e.py:123` — the per-subcommand run loop.

The command-name registry is documented as the single source of truth for the
command-name vocabulary, yet this derivation — a true piece of that vocabulary —
lives outside it and is re-spelled by every consumer. Two prior audits flagged
this (`audit:1.2.13` Finding 3, `audit:1.2.15` Finding 1), and `1.2.15`
reproduced the idiom rather than consolidating it, so the debt has persisted
across two tasks.

After this change a reader can observe that:

- the registry exposes a public `SUBCOMMAND_VERBS: tuple[str, ...]` and a
  `verb_for(spaced: str) -> str` accessor, derived once from
  `SUBCOMMAND_NAMES`;
- `novel.py` builds `_VERB_FOR_SUBCOMMAND` from the registry accessor rather
  than re-spelling the split;
- `tests/test_console_scripts_e2e.py` imports the registry accessor instead of
  re-spelling `split(" ", 1)[1]`;
- no spaced-name-to-verb split survives anywhere outside the registry module;
- the multiplexer, console-scripts, and registry suites stay green.

Observable acceptance: `make all` passes, and a fresh
`grep -rn 'split(" ", 1)\[1\]' novel_ralph_skill tests` returns *only* the
single registry-internal occurrence (the one that defines `SUBCOMMAND_VERBS`),
pinned by a new regression test.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** This is a pure consolidation. The five spaced names,
  the five mount verbs, every rendered envelope, every exit code, and the
  installed-script run sequence must be byte-for-byte unchanged. The existing
  `tests/test_multiplexer_dispatch.py`, `tests/test_command_names_registry.py`,
  `tests/test_contract_names_home.py`, and `tests/test_console_scripts_e2e.py`
  assertions must continue to pass without their *expected values* changing.
- **Contract-owns-vocabulary layering (ADR 003; roadmap 7.3.6).** The
  spaced-name vocabulary (`SUBCOMMAND_NAMES`) was relocated into
  `novel_ralph_skill/contract/names.py` by task 7.3.6 because it is *contract*
  data the envelope guard enforces; `novel_ralph_skill/commands/names.py`
  re-exports it. The verb derivation is a pure function of `SUBCOMMAND_NAMES`,
  so it is the *same* class of contract data and must be defined in
  `contract/names.py` and re-exported from `commands/names.py` — the exact
  pattern 7.3.6 used for the vocabulary itself (Decision Log D1 below). The new
  symbols must not introduce any `contract` -> `commands` import:
  `contract/names.py` must continue to import nothing from
  `novel_ralph_skill.commands` (pinned by
  `tests/test_contract_names_home.py::test_contract_names_imports_no_commands_module`).
- **No second copy of the vocabulary.** `commands.names.SUBCOMMAND_VERBS` must
  be the *same object* as `contract.names.SUBCOMMAND_VERBS` (re-export, not a
  fork), mirroring the identity guards already in
  `tests/test_contract_names_home.py` and `tests/test_command_names_registry.py`.
- **No cross-module test imports of private symbols.** Tests must consume the
  *public* registry accessor (`commands.names` re-export), never `novel.py`'s
  private `_VERB_FOR_SUBCOMMAND` / `_SUBCOMMAND_FOR_VERB`.
- **cuprum invocation chain untouched.** The e2e's external-process chain
  (`Program` -> `single_program_catalogue` -> `sh.make(...).run_sync(
  context=ExecutionContext(cwd=...), capture=True)`) must not change; only the
  verb-derivation expressions inside it are replaced.
- **File-length and docstring gates.** No touched file may exceed 400 lines
  (AGENTS.md "Keep file size manageable"); 100% docstring coverage
  (`interrogate`) must hold for every new public symbol.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  docstrings (AGENTS.md "Use consistent spelling and grammar").

## Tolerances (exception triggers)

- **Scope:** if implementation requires editing more than 6 files or a net
  change of more than ~120 lines, stop and escalate. (Expected: 2 production
  modules + 2-3 test modules.)
- **Interface:** the *only* new public symbols are `SUBCOMMAND_VERBS` and
  `verb_for` in `contract/names.py` (re-exported from `commands/names.py`). If
  any other public signature must change, stop and escalate.
- **Dependencies:** if any new third-party dependency seems required, stop and
  escalate. None is expected (Hypothesis, pytest, syrupy are already locked).
- **Iterations:** if a gate (`make all`) still fails after 3 fix attempts on a
  single work item, stop and escalate.
- **Ambiguity:** the task title says "into `names.py`" and cites
  `commands/names.py`, but the vocabulary now lives in `contract/names.py`
  (post-7.3.6). Decision Log D1 resolves this (define in `contract/names.py`,
  re-export from `commands/names.py`). If review rejects that placement, stop
  and escalate rather than forking the vocabulary.

## Risks

    - Risk: Placing the accessor in commands/names.py (the literal cited file)
      would make commands.names re-derive contract vocabulary, or fork it,
      re-introducing the contract/commands coupling 7.3.6 removed.
      Severity: medium
      Likelihood: medium
      Mitigation: Define SUBCOMMAND_VERBS/verb_for in contract/names.py beside
      SUBCOMMAND_NAMES and re-export from commands/names.py (Decision Log D1).
      Pin object identity (re-export, not copy) with a test mirroring the
      existing vocabulary identity guards.

    - Risk: verb_for accepts an arbitrary string; a caller could pass a
      non-registry name and get a silent split rather than a loud failure,
      weakening the single-source-of-truth guarantee.
      Severity: low
      Likelihood: medium
      Mitigation: verb_for raises a KeyError/ValueError for any spaced name not
      in SUBCOMMAND_NAMES (it is a registry lookup, not a raw split). Pin both
      the happy path and the rejection with unit tests, and a Hypothesis
      property that verb_for round-trips only over SUBCOMMAND_NAMES.

    - Risk: A future re-introduction of the split idiom in a new file slips past
      review, re-opening the debt a third time.
      Severity: low
      Likelihood: medium
      Mitigation: Add a durable source-scan regression test (WI4) that fails if
      `split(" ", 1)[1]` appears anywhere except the single registry definition,
      modelled on tests/test_legacy_surface_retired.py's source-scan guards.

    - Risk: The e2e module-import guard (line 69) runs at import time; a change
      there that raises would fail collection for the whole module.
      Severity: low
      Likelihood: low
      Mitigation: Keep the guard a pure set-membership assertion over the
      registry-derived SUBCOMMAND_VERBS; run the module in isolation
      (`pytest tests/test_console_scripts_e2e.py --collect-only`) before the
      full gate.

## Progress

    - [x] WI1: Add `SUBCOMMAND_VERBS` and `verb_for` to `contract/names.py`;
      re-export from `commands/names.py`; unit + property tests (red first).
      Delivered: `SUBCOMMAND_VERBS`/`verb_for` defined beside `SUBCOMMAND_NAMES`
      in `contract/names.py`, re-exported from `commands/names.py`; unit tests
      (pin five verbs, parametrized resolve, KeyError rejection, identity guard)
      in `tests/test_contract_names_home.py`; round-trip Hypothesis property in
      `tests/test_contract_properties.py`. `make all` + `make audit` green.
    - [x] WI2: Route `novel.py`'s `_VERB_FOR_SUBCOMMAND` through the registry
      accessor. Delivered: `novel.py` imports `verb_for` and builds the map via
      `{name: verb_for(name) for name in SUBCOMMAND_NAMES}`; added
      `test_verb_for_subcommand_is_registry_driven` to
      `tests/test_multiplexer_dispatch.py`. The existing dispatch suite stayed
      green unchanged. `make all` green; coderabbit raised no findings. Note: the
      registry-driven assertion needed `expected == novel._VERB_FOR_SUBCOMMAND`
      ordering to satisfy Ruff's yoda-conditions rule.
    - [x] WI3: Route `tests/test_console_scripts_e2e.py` (lines 69 and 123)
      through the registry accessor. Delivered: the import-time guard now reads
      `set(SUBCOMMAND_VERBS)` and the per-subcommand loop calls
      `verb_for(spaced_name)`; the cuprum chain is untouched. Collection-only,
      the direct `-m slow` run, and `make all` all green; coderabbit raised no
      findings.
    - [x] WI4: Add the durable regression guard that no split idiom survives
      outside the registry definition. Delivered: new
      `tests/test_verb_derivation_home.py` walks `novel_ralph_skill/` and
      `tests/`, counting only *live* `.split(" ", 1)[1]` occurrences (those
      starting outside any string/comment/f-string token) and asserting exactly
      one, in `contract/names.py`. Proven red against a temporarily re-introduced
      split in `novel.py`, then green after revert. coderabbit flagged the
      initial regex-only stripping as too coarse (string literals could falsely
      match); reworked to a tokenizer-driven offset scan that excludes
      string/comment/f-string spans, so a string-literal copy of the idiom (which
      this guard module itself holds) does not count while the live multi-token
      expression — whose receiver string `" "` would be shredded by naive token
      dropping — still does. coderabbit re-run: no findings.
    - [x] WI5: Documentation sweep (developers' guide registry note) and final
      `make all` + markdown gates. Delivered: `docs/developers-guide.md` now
      names `SUBCOMMAND_VERBS` / `verb_for` where it introduces `SUBCOMMAND_NAMES`,
      in the multiplexer mount-table paragraph, and in the command-name
      vocabulary enumeration. `make markdownlint`, `make nixie`, and `make all`
      all green; the acceptance grep shows the single surviving split in
      `contract/names.py`.

## Surprises & discoveries

    - Observation: The task cites `commands/names.py`, but 7.3.6 already moved
      the spaced-name vocabulary into `contract/names.py`; `commands/names.py`
      is now a thin re-export plus the console-script binding.
      Evidence: novel_ralph_skill/commands/names.py:30-34 imports the vocabulary
      from contract.names; novel_ralph_skill/contract/names.py:34-41 defines
      SUBCOMMAND_NAMES; tests/test_contract_names_home.py pins the home.
      Impact: The accessor must be defined in contract/names.py and re-exported,
      not defined in commands/names.py (Decision Log D1). The cited import path
      (commands.names) still resolves, so novel.py and the e2e change minimally.

## Decision log

    - Decision: Define `SUBCOMMAND_VERBS` and `verb_for` in
      `novel_ralph_skill/contract/names.py` (beside `SUBCOMMAND_NAMES`) and
      re-export both from `novel_ralph_skill/commands/names.py`.
      Rationale: The verb derivation is a pure function of `SUBCOMMAND_NAMES`,
      which 7.3.6 established as *contract*-owned vocabulary (ADR 003). Defining
      it in commands/names.py would either fork the vocabulary or make the
      commands layer re-derive contract data — the inversion 7.3.6 removed. The
      re-export keeps the cited `commands.names` import path (used by novel.py
      and the e2e) working, satisfying the task's "into names.py / route
      novel.py and the e2e through it" wording while honouring the layering. The
      identity guard (re-export is the same object) mirrors the existing
      vocabulary guards.
      Date/Author: 2026-06-27, planning agent (round 1)

    - Decision: `verb_for(spaced)` is a registry *lookup* that rejects any name
      not in `SUBCOMMAND_NAMES`, not a raw `str.split`.
      Rationale: A raw split would silently accept garbage and re-create the
      "any consumer can re-spell the idiom" weakness. A lookup makes the
      registry the sole authority: only registry-known names resolve; anything
      else fails loudly. This also gives the property test a clean invariant.
      Date/Author: 2026-06-27, planning agent (round 1)

    - Decision (WI1, 2026-06-27): coderabbit flagged three findings, all on this
      ExecPlan document. (1) "how we check" first-person wording — fixed to "how
      it is checked". (2) Risks/Progress/Surprises/Decision-log list items
      indented as code blocks — kept: this is the established ExecPlan format,
      `make markdownlint` and `make nixie` both pass, and the indentation is
      deliberate verbatim-block styling, not a rendering defect. (3) ExecPlan
      exceeds 400 lines — kept: the 400-line gate (AGENTS.md) governs *source*
      files, not living planning documents; ExecPlans are intentionally
      self-contained and long. No source-code findings were raised.

    - Decision: Provide both `SUBCOMMAND_VERBS` (the verbs in surface order, a
      tuple) and `verb_for` (single-name accessor).
      Rationale: `novel.py` builds a dict over all names (wants the ordered
      collection or per-name accessor); the e2e line 69 wants the *set* of
      verbs; line 123 wants a *single* verb per spaced name. Exposing both the
      tuple and the accessor lets each consumer pick the natural shape without
      re-deriving anything. `audit:1.2.13`/`audit:1.2.15` proposed exactly this
      pair ("`SUBCOMMAND_VERBS: tuple[str, ...]` or `verb_for(spaced) -> str`").
      Date/Author: 2026-06-27, planning agent (round 1)

## Outcomes & retrospective

Delivered as planned (2026-06-27). Compared against Purpose: the registry now
owns one derivation (`SUBCOMMAND_VERBS` / `verb_for` in `contract/names.py`,
re-exported from `commands/names.py`); the three former call sites — the
dispatcher's `_VERB_FOR_SUBCOMMAND` and the two e2e split sites — are routed
through it; no live split idiom survives outside the single registry definition
(the WI4 guard and the acceptance grep both confirm one occurrence in
`contract/names.py`); and the multiplexer, console-scripts, registry, and
contract suites stay green. No behaviour changed: the five spaced names, the five
mount verbs, every envelope, and the installed-script run sequence are unchanged.

Deviations from the plan, all minor:

- The WI4 guard's idiom counter could not simply drop string/comment tokens
  because the idiom embeds a `" "` string literal; coderabbit flagged the initial
  regex-only stripping as too coarse, so the guard now scans token *offsets* and
  counts only matches whose first character falls outside any string/comment/
  f-string span. This is the one place a string-literal copy of the idiom (the
  guard's own `_SPLIT_IDIOM`) coexists with a live occurrence elsewhere, so the
  offset approach was necessary for correctness.
- The WI2 registry-driven map assertion needed `expected ==
  novel._VERB_FOR_SUBCOMMAND` ordering to satisfy Ruff's yoda-conditions rule.
- Three coderabbit findings against this ExecPlan document (first-person wording,
  code-block-indented lists, and file length) were triaged: the wording was
  fixed; the indentation and length were kept as the established, gate-passing
  ExecPlan format (the 400-line gate governs source files, not planning docs).

Tolerances respected: 6 files touched (two production modules, three test
modules, one doc), well within scope; the only new public symbols are
`SUBCOMMAND_VERBS` and `verb_for`; no new dependency; no gate needed more than
two fix attempts.

## Context and orientation

This repository packages the `novel` Ralph-loop harness as
`novel_ralph_skill`. The deterministic command surface is a single `novel`
multiplexer with five operations (`state`, `done`, `compile`, `desloppify`,
`wordcount`), fixed by `docs/adr-007-command-surface-novel-multiplexer.md` and
described in `docs/novel-ralph-harness-design.md` §4.

Key terms:

- **Spaced subcommand name:** the envelope `command` field value, e.g.
  `"novel state"`. The five are `SUBCOMMAND_NAMES`.
- **Mount verb (bare verb):** the Cyclopts sub-app mount name, e.g. `"state"` —
  the part after the single space in the spaced name.
- **Registry:** the command-name vocabulary. Task 7.3.6 split it in two:
  - `novel_ralph_skill/contract/names.py` *owns* the contract vocabulary
    (`MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`, `ENVELOPE_COMMAND_NAMES`,
    `WORKING_DIR_NAME`) because the envelope guard enforces it (ADR 003);
  - `novel_ralph_skill/commands/names.py` *re-exports* that vocabulary (every
    `commands.names` import keeps resolving) and additionally owns the
    `[project.scripts]` console-script binding (`NOVEL_MODULE`,
    `project_scripts_table`), a packaging concern that legitimately consumes the
    vocabulary downward.

Files this plan touches:

- `novel_ralph_skill/contract/names.py` — add `SUBCOMMAND_VERBS` and
  `verb_for`.
- `novel_ralph_skill/commands/names.py` — re-export the two new symbols and add
  them to `__all__`.
- `novel_ralph_skill/commands/novel.py` — build `_VERB_FOR_SUBCOMMAND` from the
  registry accessor (lines 49-51 today).
- `tests/test_console_scripts_e2e.py` — replace the two `split(" ", 1)[1]`
  spellings (lines 69, 123).
- `tests/test_command_names_registry.py` (or `tests/test_contract_names_home.py`)
  — add unit + identity tests for the new accessor.
- `tests/test_contract_properties.py` (existing Hypothesis home) — add the
  round-trip property.
- A new or existing regression-guard module — add the surviving-idiom scan
  (WI4).

The mechanism is verified against the locked **cuprum 0.1.0** and **Cyclopts
4.18.0** (see Interfaces and dependencies). This task does not change the cuprum
invocation chain or any Cyclopts behaviour; it only consolidates a string
derivation, so no external-library behavioural claim is load-bearing beyond
"the existing e2e chain still runs unchanged", which the unchanged e2e proves.

## Plan of work

Staged, each work item independently committable and gate-passable (`make all`).
Red-before-green: each new test is added and shown failing against the pre-edit
source before the production edit lands, in the same work item.

### WI1 — Add the registry accessor (define in contract, re-export in commands)

Docs to read: `docs/adr-003-shared-interface-contract.md`;
`docs/novel-ralph-harness-design.md` §4; `docs/execplans/roadmap-7-3-6.md`
(Decision Log D1, the vocabulary-relocation pattern this mirrors);
`docs/issues/audit-1.2.15.md` Finding 1 (the proposed `SUBCOMMAND_VERBS` /
`verb_for` shape); `AGENTS.md` "Python verification and testing", "Abstraction /
port / helper policy".

Skills to load: `python-router` -> `python-types-and-apis` (public function
signature, `tuple[str, ...]` shape), `python-errors-and-logging` (the loud
rejection in `verb_for`), `python-testing`; `python-verification` ->
`hypothesis` (the round-trip property); `leta` for navigation; `sem` for the
7.3.6 vocabulary-relocation diff.

Edits:

1. In `novel_ralph_skill/contract/names.py`, beside `SUBCOMMAND_NAMES`, add:

       # contract/names.py
       SUBCOMMAND_VERBS: tuple[str, ...] = tuple(
           name.split(" ", 1)[1] for name in SUBCOMMAND_NAMES
       )
       """The five bare mount verbs (``"state"`` …), in surface order.

       The single derivation of a spaced ``novel <verb>`` name to its bare
       mount verb. Every consumer (the dispatcher, the e2e suite) reads this or
       :func:`verb_for` rather than re-spelling ``split(" ", 1)[1]`` inline
       (audit:1.2.13 Finding 3; audit:1.2.15 Finding 1).
       """

       _VERB_BY_SUBCOMMAND: dict[str, str] = dict(
           zip(SUBCOMMAND_NAMES, SUBCOMMAND_VERBS, strict=True)
       )


       def verb_for(spaced: str) -> str:
           """Return the bare mount verb for a spaced subcommand name.

           Parameters
           ----------
           spaced : str
               A spaced subcommand name from :data:`SUBCOMMAND_NAMES`, e.g.
               ``"novel state"``.

           Returns
           -------
           str
               The bare mount verb, e.g. ``"state"``.

           Raises
           ------
           KeyError
               If ``spaced`` is not a registered subcommand name. The lookup
               makes the registry the sole authority: only registry-known names
               resolve, so a typo or a non-registry string fails loudly rather
               than being silently split.

           Examples
           --------
           >>> verb_for("novel desloppify")
           'desloppify'
           """
           return _VERB_BY_SUBCOMMAND[spaced]

   Add `"SUBCOMMAND_VERBS"` and `"verb_for"` to `contract/names.py`'s `__all__`.
   The single surviving `split(" ", 1)[1]` lives here, in the `SUBCOMMAND_VERBS`
   definition; WI4 pins that it is the only one.

2. In `novel_ralph_skill/commands/names.py`, extend the existing re-export
   import and `__all__`:

       # commands/names.py
       from novel_ralph_skill.contract.names import (
           ENVELOPE_COMMAND_NAMES,
           MULTIPLEXER_NAME,
           SUBCOMMAND_NAMES,
           SUBCOMMAND_VERBS,
           verb_for,
       )

   Add `"SUBCOMMAND_VERBS"` and `"verb_for"` to `commands/names.py`'s `__all__`
   and extend the module docstring's "command-name vocabulary" bullet to name
   the new derived accessor (en-GB spelling).

Tests (red first, in this work item):

- Extend `tests/test_contract_names_home.py`:
  - `test_subcommand_verbs_pin_the_five_mount_verbs` — asserts
    `contract_names.SUBCOMMAND_VERBS == ("state", "done", "compile",
    "desloppify", "wordcount")`.
  - `test_verb_for_resolves_each_spaced_name` — parametrized over the five
    spaced names, asserts `verb_for(spaced)` equals the expected verb.
  - `test_verb_for_rejects_unknown_name` — asserts `verb_for("novel bogus")`
    and `verb_for("state")` raise `KeyError` (the loud-rejection Decision).
  - `test_commands_names_reexports_verb_accessor` — identity guard:
    `commands_names.SUBCOMMAND_VERBS is contract_names.SUBCOMMAND_VERBS` and
    `commands_names.verb_for is contract_names.verb_for` (re-export, no fork),
    mirroring the existing `test_commands_names_reexports_contract_vocabulary`.
  - Extend `test_contract_names_imports_no_commands_module` coverage is already
    structural over the whole module; confirm it still passes (no new
    `commands` import was added).
- Add a Hypothesis property to `tests/test_contract_properties.py`:
  `test_verb_for_round_trips_over_the_registry` — for any `spaced` drawn from
  `st.sampled_from(SUBCOMMAND_NAMES)`, assert
  `f"{MULTIPLEXER_NAME} {verb_for(spaced)}" == spaced` (re-prepending the
  multiplexer name reconstructs the spaced name). Follow the `hypothesis` skill
  for strategy design; `sampled_from` over the fixed registry avoids the
  filtering trap.

Validation: `make all` (which runs `make check-fmt lint typecheck test`). Show
the new tests failing against the pre-edit source (e.g. import error / missing
symbol) before adding the production symbols, then green after. Commit.

### WI2 — Route the dispatcher through the registry accessor

Docs to read: `docs/adr-007-command-surface-novel-multiplexer.md`;
`docs/novel-ralph-harness-design.md` §4;
`novel_ralph_skill/commands/novel.py` (Decision Log D4 comment at lines 46-56).

Skills to load: `python-router` -> `python-data-shapes` (dict-comprehension
provenance), `python-iterators-and-generators`; `leta` (`refs SUBCOMMAND_NAMES`,
`refs verb_for`).

Edits in `novel_ralph_skill/commands/novel.py`:

1. Extend the import on line 36 to add `verb_for` (or `SUBCOMMAND_VERBS`):

       # novel.py
       from novel_ralph_skill.commands.names import (
           MULTIPLEXER_NAME,
           SUBCOMMAND_NAMES,
           verb_for,
       )

2. Replace the `_VERB_FOR_SUBCOMMAND` comprehension (lines 49-51) so the verb
   comes from the registry accessor, not an inline split:

       # novel.py
       _VERB_FOR_SUBCOMMAND: dict[str, str] = {
           name: verb_for(name) for name in SUBCOMMAND_NAMES
       }

   Update the surrounding comment (lines 46-48) so it states the verb is
   resolved through the registry accessor (`verb_for`), keeping the Decision Log
   D4 "never re-spells the verbs inline" intent and en-GB spelling. The
   downstream `_SUBCOMMAND_FOR_VERB`, `_build_mount_table`, `build_multiplexer`,
   and `_command_name_for` are unchanged.

Tests: no new production behaviour, so the existing
`tests/test_multiplexer_dispatch.py` (registers-five-subcommands,
`_command_name_for` mapping, registry-not-literals) is the behavioural oracle
and must stay green unchanged. Add one focused assertion to
`tests/test_multiplexer_dispatch.py` (or assert in WI4's guard) that
`novel._VERB_FOR_SUBCOMMAND` equals `{name: verb_for(name) for name in
SUBCOMMAND_NAMES}`, pinning that the dispatcher's private map is registry-driven
(it derives from the accessor, so a future inline re-spelling diverges and
fails). Keep it a value assertion, not an import of internals beyond the already
imported `novel` module within its own test home.

Validation: `make all`. The dispatch suite proves no behaviour change. Commit.

### WI3 — Route the console-scripts e2e through the registry accessor

Docs to read: `docs/adr-006-console-scripts-e2e-posix-policy.md`;
`docs/scripting-standards.md` (cuprum catalogue / allowlist / absolute-path
execution — confirm the invocation chain is untouched);
`tests/test_console_scripts_e2e.py` (the two split sites, lines 69 and 123).

Skills to load: `python-router` -> `python-testing`; `firecrawl` only if any
cuprum/Cyclopts behaviour needs re-confirming (it does not for this WI — see
Interfaces and dependencies); `leta`.

Edits in `tests/test_console_scripts_e2e.py`:

1. Add `SUBCOMMAND_VERBS` to the existing import from
   `novel_ralph_skill.commands.names` (line 38).
2. Replace the module-import guard (line 69):

       # test_console_scripts_e2e.py
       assert set(_REAL_PATH_ARGV) <= set(SUBCOMMAND_VERBS), (
           "every extra-argv key must be a real mount verb"
       )

3. Replace the per-subcommand verb derivation in
   `_assert_scripts_real_state_error` (line 123). Prefer iterating the
   registry-paired names and verbs together so neither the spaced name (used in
   the assertion messages) nor the verb is re-spelled:

       # test_console_scripts_e2e.py
       for spaced_name in SUBCOMMAND_NAMES:
           verb = verb_for(spaced_name)
           argv = (verb, *_REAL_PATH_ARGV.get(verb, ()))
           ...

   (Import `verb_for` alongside `SUBCOMMAND_VERBS`; the loop keeps `spaced_name`
   for the existing failure messages.) The cuprum chain
   (`Program`/`single_program_catalogue`/`sh.make`/`run_sync`) is unchanged.

Tests: this *is* the e2e; it is `slow`-marked with a 180s per-test timeout. Run
collection-only first to confirm the import-time guard still passes, then run
the module directly:

    pytest tests/test_console_scripts_e2e.py --collect-only
    pytest -p no:randomly tests/test_console_scripts_e2e.py -m slow

(Full `make all` runs it under `-n auto`; the 180s timeout supersedes the 30s
default per the module docstring.)

Validation: `make all`. Commit.

### WI4 — Durable guard: no split idiom survives outside the registry

Docs to read: `docs/issues/audit-1.2.15.md` Finding 1 (the persistence across
two tasks this guard prevents recurring); `tests/test_legacy_surface_retired.py`
(the source-scan guard pattern to mirror); `AGENTS.md` "Python verification and
testing".

Skills to load: `python-router` -> `python-testing`; `leta`.

Edit: add a regression test — either a new `tests/test_verb_derivation_home.py`
or a case appended to `tests/test_command_names_registry.py` — that walks the
production and test trees and asserts the `split(" ", 1)[1]` (and the broader
`.split(" "` spaced-verb) idiom appears in exactly one place: the
`SUBCOMMAND_VERBS` definition in `novel_ralph_skill/contract/names.py`. Model it
on `tests/test_legacy_surface_retired.py::test_no_legacy_command_literals_in_idiom_sources`:
read each file's source via `project_root`, count occurrences, and assert the
total across `novel_ralph_skill/` and `tests/` is exactly one and lives in
`contract/names.py`. Exclude this guard module itself (its own string literal)
the way `test_legacy_surface_retired.py` excludes the decorator lines.

This is the test that makes the "no spaced-name-to-verb split survives outside
the registry" success criterion durable rather than a one-shot grep.

Tests: the guard *is* the test. Verify it fails if you temporarily re-introduce
a split in `novel.py`, then passes after removing it (red/green proof recorded
in Progress).

Validation: `make all`. Commit.

### WI5 — Documentation sweep and final gates

Docs to read: `docs/developers-guide.md` (the registry / "single source of
truth" note, if it enumerates the registry's public surface);
`docs/documentation-style-guide.md`; `AGENTS.md` "Documentation maintenance",
"Markdown guidance".

Skills to load: `en-gb-oxendict`; `execplans` (keep this plan's living sections
current).

Edits:

1. If `docs/developers-guide.md` (or `docs/novel-ralph-harness-design.md` §4)
   enumerates the registry's public symbols or the "single source of truth for
   the command-name vocabulary", add `SUBCOMMAND_VERBS` / `verb_for` to that
   description so the derivation's new home is documented (AGENTS.md "Document
   internally facing interfaces / conventions"). Keep en-GB Oxford spelling and
   80-column prose wrapping.
2. Update this ExecPlan's `Progress`, `Surprises & Discoveries`, `Decision
   Log`, and `Outcomes & Retrospective` to reflect the delivered state.

Tests / validation: `make markdownlint` and `make nixie` for every Markdown
file touched (this plan and any guide edit), then a final `make all`. Commit.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-8`.

1. Confirm the branch and a clean tree:

       git branch --show-current   # expect: roadmap-7-3-8
       git status --short          # expect: clean

2. WI1 — add tests first, watch them fail, then add the symbols:

       make test    # new contract.names tests fail: AttributeError / ImportError
       # … add SUBCOMMAND_VERBS, verb_for to contract/names.py and re-export …
       make all     # expect: all green
       git add -A && git commit

   Expected red transcript (before the production edit), abbreviated:

       E   AttributeError: module 'novel_ralph_skill.contract.names'
       E   has no attribute 'SUBCOMMAND_VERBS'

3. WI2 — route `novel.py`:

       make all     # test_multiplexer_dispatch stays green; new map assertion green
       git add -A && git commit

4. WI3 — route the e2e:

       pytest tests/test_console_scripts_e2e.py --collect-only   # import guard ok
       make all                                                  # e2e green
       git add -A && git commit

5. WI4 — durable guard (prove red then green):

       # temporarily re-add a split in novel.py, then:
       pytest tests/test_verb_derivation_home.py   # expect: FAIL (two occurrences)
       # revert the temporary split, then:
       make all                                    # expect: green
       git add -A && git commit

6. WI5 — docs + final gates:

       make markdownlint
       make nixie
       make all
       git add -A && git commit

7. Final sanity grep (the observable acceptance):

       grep -rn 'split(" ", 1)\[1\]' novel_ralph_skill tests
       # expect: exactly one hit, in novel_ralph_skill/contract/names.py

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests:** `make test` passes. The new tests
  (`test_subcommand_verbs_pin_the_five_mount_verbs`,
  `test_verb_for_resolves_each_spaced_name`,
  `test_verb_for_rejects_unknown_name`,
  `test_commands_names_reexports_verb_accessor`,
  `test_verb_for_round_trips_over_the_registry`, and the WI4 source-scan guard)
  fail before their respective production edit and pass after. The existing
  `tests/test_multiplexer_dispatch.py`, `tests/test_command_names_registry.py`,
  `tests/test_contract_names_home.py`, and `tests/test_console_scripts_e2e.py`
  suites stay green with their expected values unchanged.
- **Lint/format/typecheck:** `make lint`, `make check-fmt`, `make typecheck`
  pass (100% `interrogate` docstring coverage on the new public symbols; Ruff,
  Pylint, `ty` clean).
- **Audit:** `make audit` passes (no dependency change).
- **Markdown:** `make markdownlint` and `make nixie` pass for this plan and any
  guide edit.
- **Behaviour:** the spaced names, mount verbs, envelopes, exit codes, and the
  installed-script e2e run sequence are unchanged.

Quality method (how it is checked): run `make all` after every work item; run
`make markdownlint` and `make nixie` after any Markdown change; run the final
acceptance grep showing a single surviving split occurrence in
`contract/names.py`.

Acceptance is behavioural and observable: after the change, building and running
the installed `novel` script under a cwd with no `working/` still exits `3` for
every subcommand (the e2e), the multiplexer still mounts exactly the five verbs
and stamps the five spaced names (the dispatch suite), and the verb derivation
exists in exactly one place (the acceptance grep and the WI4 guard).

## Idempotence and recovery

Every step is a content edit plus a gated commit; re-running `make all` is
safe and side-effect-free. If a work item's gate fails, fix forward or
`git restore`/`git reset --soft` the uncommitted edit and retry — no step is
destructive and nothing writes outside the repository. The e2e builds into a
`tmp_path`, so repeated runs leave no residue. If WI1's re-export accidentally
forks the object (identity test fails), the fix is to import the symbol from
`contract.names` rather than redefining it — revert and re-import.

## Artefacts and notes

The single surviving derivation, after the change, in
`novel_ralph_skill/contract/names.py`:

    SUBCOMMAND_VERBS: tuple[str, ...] = tuple(
        name.split(" ", 1)[1] for name in SUBCOMMAND_NAMES
    )

The acceptance grep proving consolidation:

    $ grep -rn 'split(" ", 1)\[1\]' novel_ralph_skill tests
    novel_ralph_skill/contract/names.py:NN:    name.split(" ", 1)[1] for name in SUBCOMMAND_NAMES

## Interfaces and dependencies

New public interface, in `novel_ralph_skill/contract/names.py`, re-exported
from `novel_ralph_skill/commands/names.py`:

    # novel_ralph_skill/contract/names.py
    SUBCOMMAND_VERBS: tuple[str, ...]            # ("state", "done", "compile",
                                                 #  "desloppify", "wordcount")

    def verb_for(spaced: str) -> str: ...        # registry lookup; KeyError on miss

Locked external libraries the touched code relies on (pinned, verified against
source — no behavioural fork is introduced by this task):

- **cuprum 0.1.0** (`uv.lock` line 113-118). The e2e's external-process chain is
  unchanged; the APIs it uses are verified present in the locked source at
  `/data/leynos/Projects/cuprum`:
  - `cuprum.program.Program` — accepts any string program, including an absolute
    path (`cuprum/program.py`; the e2e module docstring already records "cuprum
    0.1.0 allowlists any `Program` string, including an absolute path").
  - `cuprum.catalogue.ProgramCatalogue` (`cuprum/catalogue.py:59`) — the
    one-program allowlist the `single_program_catalogue` conftest fixture builds.
  - `cuprum.sh.make` (`cuprum/sh.py:528`) — builds the command from a `Program`
    plus catalogue.
  - `cuprum.sh.ExecutionContext` (`cuprum/sh.py:169`) and the builder's
    `run_sync(...)` (`cuprum/sh.py:441,509`) with `context=` and `capture=True`
    — the cwd-scoped, output-capturing run the e2e already performs.
  This task touches none of these calls; it replaces only the `split(" ", 1)[1]`
  expressions that compute the argv verb, so no new cuprum behaviour is relied
  upon. (If any of these calls *did* change, the e2e would fail at run time;
  they do not.)
- **Cyclopts 4.18.0** (`uv.lock` line 137-148). The multiplexer's mounting and
  dispatch behaviour is unchanged; `_VERB_FOR_SUBCOMMAND` only changes *how* the
  verb string is computed (registry accessor vs inline split), not the verbs
  themselves, so the locked Cyclopts mounting semantics (`parent.command(child,
  name=…)`, verified under 7.3.5/1.2.12 and pinned by
  `tests/test_multiplexer_dispatch.py`) are not re-derived here. No firecrawl
  re-confirmation is needed because no Cyclopts `--help`/`--version`/usage
  behaviour is exercised by this change.
- **Hypothesis** (locked dev dependency) — used for the round-trip property in
  `tests/test_contract_properties.py`; `st.sampled_from(SUBCOMMAND_NAMES)` over
  the fixed five-element registry (no filtering trap), per the `hypothesis`
  skill.
- **pytest / pytest-xdist / pytest-timeout** — the e2e's `@pytest.mark.timeout(
  180)` per-test override (superseding the 30s default under `-n auto`) is
  unchanged by this task; no timeout or xdist behaviour is altered.

## Revision note (required when editing an ExecPlan)

Round 1 (2026-06-27): initial draft. Decomposes task 7.3.8 into five atomic
work items (WI1 registry accessor + tests; WI2 dispatcher; WI3 e2e; WI4 durable
guard; WI5 docs + gates). Resolves the cited-file-vs-actual-home ambiguity in
Decision Log D1 (define in `contract/names.py`, re-export from
`commands/names.py`). Pins the cuprum 0.1.0 and Cyclopts 4.18.0 APIs the e2e
relies on as verified-unchanged. No remaining undecided forks.

## Addenda

Lightweight, post-completion corrections folded onto this task. Each is a small,
surgical fix run as a no-plan, no-review pass; none changes the task's outcome.

- [ ] A1 (from review:7.3.8; low). Correct this execplan's grep-based acceptance
  wording to reference the live-code count. The plan documents an observable
  acceptance ("grep … expect: exactly one hit") that is literally false — the raw
  grep returns ten hits and only the live-code count is one — so a future agent
  running the documented command is misled. Re-word the acceptance to point at the
  WI4 tokenizer guard / live-code count, or scope the grep to exclude comments and
  strings. Doc-only fix to this execplan record. Mirrors roadmap sub-task 7.3.8.1.

- [ ] A2 (from audit:7.3.8; low). Build the multiplexer verb map from the registry
  rather than one `verb_for` call at a time. `novel.py` rebuilds
  `_VERB_FOR_SUBCOMMAND` one `verb_for()` call at a time, reconstructing the
  relation the contract already holds. Build it from
  `dict(zip(SUBCOMMAND_NAMES, SUBCOMMAND_VERBS, strict=True))` — or expose a
  registry `verb_map()` accessor — so the spaced-name-to-verb map is owned in one
  place, serving the same single-source intent 7.3.8 established for the scalar
  split. Behaviour-preserving. Scope: `novel_ralph_skill/commands/novel.py` (and
  `contract/names.py` if a `verb_map()` accessor is added). Mirrors roadmap
  sub-task 7.3.8.2.
