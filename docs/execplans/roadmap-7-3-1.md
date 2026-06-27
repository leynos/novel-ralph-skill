# Lift the shared state-sourcing seam into a neutral module with a public `load_or_state_error`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: IMPLEMENTED

## Purpose / big picture

Five sibling command modules (`_compile.py`, `_recount.py`,
`_state_mutators.py`, `_novel_done.py`, `_desloppify.py`), plus `_wordcount.py`
and `_desloppify_ledger.py`, all reach into
`novel_ralph_skill.commands.novel_state` to import the shared state-sourcing
seam: the underscore-private `_load_or_state_error`, the `STATE_INPUT_ERRORS`
exception tuple, the `WORKING_DIR_NAME` constant, and the `state_path` /
`working_dir` accessors. Those symbols physically live in the dependency-free
leaf module `novel_ralph_skill/commands/_state_load.py` but are re-exported
through `novel_state.py`, so today `novel_state` (a *command facade* for the
`novel state` subgroup) doubles as the de-facto shared-utility home. The
underscore-private `_load_or_state_error` name misleads — it is a deliberately
shared, cross-command seam, not a module-private helper — and a future
`novel-state` refactor risks silently breaking four other commands that depend
on it transitively.

After this change, the load-and-translate seam, the state-input
exception-tuple, the `working/` directory name, and the `state_path`/
`working_dir` accessors live in a dedicated, neutrally-named module with a
**public** `load_or_state_error`. The five sibling commands, `_wordcount.py`,
and `_desloppify_ledger.py` import them from that neutral home rather than from
`novel_state`; no command depends on the `novel_state` command module for these
seams; and every command suite stays green.

Success is observable three ways. First,
`grep -rn 'novel_state import' novel_ralph_skill/commands/` shows no command
importing a state-sourcing seam from `novel_state` (only `novel.py`'s import of
`resolved_working_dir`, which is itself migrated). Second, a new structural test
(`tests/test_state_sourcing_home.py`) imports `load_or_state_error` as a
public name from the neutral module and fails if any command re-pins the seam to
`novel_state`. Third, `make all` is green: the full unit, behavioural,
property, snapshot, and e2e suites pass unchanged.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** This is a pure module-boundary and rename refactor.
  Every command's exit codes, envelope shapes, and actionable-message strings
  must be byte-for-byte identical before and after. The
  `tests/test_state_input_message_*`, `tests/test_draft_read_message_*`, and
  `tests/test_state_load_actionable_parity.py` suites pin those strings; they
  must pass unchanged (after their import lines are repointed).
- **`WORKING_DIR_NAME` stays in the command layer for now.** Roadmap task 7.3.6
  (which *requires* 7.3.1) relocates `WORKING_DIR_NAME` and the command-name
  vocabulary into the `contract` package and repairs the `contract`→`commands`
  layering inversion. This plan must **not** pre-empt that move: it places
  `WORKING_DIR_NAME` in the neutral command-layer module so 7.3.6 has a single
  clean edit to make, exactly as the roadmap's 7.3.6 "Coordinate with 7.3.1"
  note requires (`docs/roadmap.md` task 7.3.6, lines 2906-2907).
- **The neutral module stays dependency-free of `novel_state`.** It must import
  only from `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner`,
  never from `novel_state`, preserving the no-cycle property the current
  `_state_load.py` already holds (`_state_load.py` lines 13-17). The mutator
  modules import *from* the neutral home, so the home importing *from* a
  command module would reintroduce the cycle the original carve-out avoided.
- **`novel_state.build_app` and its `[project.scripts]` target are unchanged.**
  The public `build_app()` signature, the `novel state` subcommand set, and the
  console-script entry points must not move or change.
- **400-line file cap (AGENTS.md "Keep file size manageable").** No touched file
  may exceed 400 lines. `_state_load.py` is 364 lines today (`wc -l`); the
  neutral module inherits that body unchanged, so it stays under the cap.
- **en-GB Oxford spelling ("-ize"/"-yse"/"-our")** in all prose, comments,
  docstrings, and commit messages (AGENTS.md "Use consistent spelling").

## Tolerances (exception triggers)

- **Scope:** if implementation requires editing more than 25 files net, stop and
  escalate. (Estimate: the neutral module, `novel_state.py`, 7 command modules,
  ~6 prose cross-references, ~5 test import sites, plus docs — roughly 18-22
  files.)
- **Interface:** the only intended public-surface change is *adding* the public
  `load_or_state_error` (and retaining the underscore alias for one transition
  step, then removing it). If any *other* public signature must change, stop
  and escalate.
- **Dependencies:** if any new third-party dependency is required, stop and
  escalate. None is expected; this is an internal move.
- **Iterations:** if `make all` still fails after 3 fix attempts on any single
  work item, stop and escalate with the failing output.
- **Ambiguity — module name:** the roadmap offers `_state_io.py` *or*
  `state/sourcing.py` as examples. The Decision Log fixes the name to
  `state_sourcing.py` (a public, neutral, flat command-layer module). If review
  prefers a `state/` sub-package, that is a one-line rename, but do not create
  a sub-package speculatively.

## Risks

- Risk: a command imports a state-sourcing seam through a path this plan
  misses (for example a deferred import inside a function body, or a
  `from . import novel_state` form), so a stale `novel_state` dependency
  survives. Severity: medium. Likelihood: low. Mitigation: work item 2 adds a
  structural test that fails if any module under `novel_ralph_skill/commands/`
  (other than `novel_state.py` itself, transitionally) imports the migrated
  seams from `novel_state`. The test is written red before the migration and
  turns green as each consumer is repointed.
- Risk: renaming `_state_load.py` → `state_sourcing.py` and
  `_load_or_state_error` → `load_or_state_error` leaves stale free-text prose,
  `:mod:`/`:func:` roles, or filename/line citations that `leta mv` (imports
  only) and `leta rename` (symbol refs only) do not rewrite, and that **no test
  guards** — the projection drift-guard
  (`tests/test_projection_docstring_drift_guard.py`) pins only the
  `compile_model`/reconciliation projections, not the state-sourcing seam, and
  the developers-guide contract drift-guard pins only the exit-code table and
  the envelope brace-list, not the formatter prose or module name. Severity:
  medium. Likelihood: high (this was the round-1 blocking defect). Mitigation:
  WI5 enumerates the full set of stale `_state_load` and
  bare-`_load_or_state_error` references (across `commands/`,
  `state/compile_model.py`, the two `test_state_load_*` files' prose, and the
  developers' guide) and gates the sweep with
  `grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`
  returning nothing, per the developers-guide "defining-module path is
  canonical" rule (`docs/developers-guide.md` lines 1080-1090). The bare-prose
  `_load_or_state_error` mentions (`_wordcount.py:117`, `_novel_done.py:28`,
  devguide 976/1242) are swept by hand because `leta rename` does not touch
  free text.
- Risk: the test suite imports the seam from both `novel_state` (the re-export
  façade) and `_state_load` (the definition), so a half-migration leaves tests
  importing a removed alias. Two test files import symbols WI5 **drops from
  `novel_state` entirely** (`tests/multiplexer_support.py` → `WORKING_DIR_NAME`;
  `tests/test_state_input_message_unit.py` → `_state_input_error`); if WI4
  omits them, WI5's commit fails `make all` with a collection-time
  `ImportError`, violating the single-gate-passing-commit invariant.
  `tests/multiplexer_support.py` is a conftest-registered plugin
  (`tests/conftest.py:64`), so its breakage takes the whole multiplexer suite
  down at collection. Severity: high. Likelihood: high (this was the round-3 B4
  defect). Mitigation: WI4 enumerates **all six** `novel_state` seam importers
  (Decision D8) and repoints them — before WI5 trims the re-exports —
  preserving each symbol set verbatim (private formatters stay private); the
  WI4 validation greps prove no seam symbol is imported from `novel_state` in
  `tests/`.
- Risk: four test-module docstrings carry `:func:` roles naming the
  `novel_state._<formatter>` re-export façade
  (`test_draft_read_message_unit.py`, `test_draft_read_message_parity.py`,
  `test_state_input_message_unit.py`, `test_state_input_message_parity.py`).
  After WI5 these are dangling/non-canonical (`_state_input_error` no longer
  exists on `novel_state`; `_draft_read_error` is no longer canonical there)
  and **no test guards them** — the `_state_load` gate does not match (they say
  `novel_state`), nixie is Mermaid-only (Makefile:121-123), and the projection
  drift-guard pins only `compile_model`/reconciliation. Severity: medium.
  Likelihood: high (round-3 B5 defect, the six-months-later trap on the test
  side). Mitigation: WI5 clean-up 2 rewrites all four roles to the canonical
  `state_sourcing._<formatter>` path, and the broadened WI5 hard gate (gate 2,
  the `novel_state\._<formatter>` pattern) returns nothing after WI5/WI6.
- Risk: a comment or docstring in `commands/` keeps **claiming `novel_state` is
  the seam/accessor home** after the migration — most acutely
  `_state_mutators.py:64-66` ("`_state_path`/`_working_dir` are re-exported from
  `novel_state` (the single accessor home)") in the very module that performs
  the second-hop re-export, and the `state_sourcing.py` module docstring's
  carve-out prose naming `novel_state` as where commands "keep importing these
  symbols from". This is a plain `:mod:` role plus free prose with no
  `_state_load` token and no `._<…>error` suffix, so **neither Gate 1 nor Gate
  2 sees it**, and a future `novel-state` refactor could re-pin the mutator
  tail back through `novel_state` (the WI2 AST guard forbids only *direct*
  seam-name imports, not the `_state_path`/`_working_dir` re-export tail),
  reintroducing the cycle this task removes. Severity: medium. Likelihood: high
  (round-4 B7 defect — the third successive fresh token to slip a token-scoped
  gate). Mitigation: WI5 clean-up 1 rewrites both sites to name
  `state_sourcing` as the single accessor home; a new **Gate 3** (the keyword
  pattern below)

  ```text
  novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)
  ```

  over `commands/` plus an enumerate-and-eyeball backstop over every residual
  `novel_state` prose mention in `commands/` proves no home claim survives and
  confirms each surviving reference is a genuine command-surface one.
  (Wafflecat's round-4 alternative — a single structural import gate walking
  the import graph including the `_state_mutators` re-export tail — is noted
  for 7.3.6's larger `contract`↔`commands` rewire; comments are not imports, so
  the prose gates still stand and are the correct fix here.)
- Risk: a reviewer reads "lift out of novel_state" as also moving
  `WORKING_DIR_NAME` into `contract`, conflating 7.3.1 with 7.3.6. Severity:
  low. Likelihood: low. Mitigation: the Constraints section and the Decision
  Log pin the boundary explicitly; the neutral module is command-layer, and
  7.3.6 owns the contract-package move.

## Progress

- [x] (done) WI1: promote `_state_load.py` to the neutral
  `state_sourcing.py` home with a public `load_or_state_error`. Commit
  `9aa87e2`. `leta mv` + `leta rename` repointed 4 + 8 files; restructured the
  module docstring into neutral-home prose, added an explicit `__all__` for the
  public seam, and fixed the `novel_state.__all__` RUF022 ordering after the
  rename. `make all` green (1422 passed, 1 skipped). Deviation note: `make fmt`
  reflows ~284 unrelated `docs/` and 5 `skill/` markdown files (the known
  mdformat-all churn); that churn was stashed and discarded, only the Python
  edits kept. The `_load_or_state_error`/`_state_load` prose roles at
  `state_sourcing.py:74,125` are deferred to WI5 per plan.
- [x] (done) WI2: add the structural home-and-import test. Commit `1272665`.
  Landed assertion 1 (public-home) green; assertion 2 (no-`novel_state`
  dependency) is staged for WI3's opening red step per the plan's commit shape.
  `make all` green (1424 passed). Coderabbit (1 minor) flagged the docstring
  describing an assertion not yet present; tightened the docstring to describe
  only the public-home check and note assertion 2 lands in WI3.
- [x] (done) WI3: repoint the seven command consumers to the neutral home.
  Commit `1d41cf4`. Repointed `_compile`, `_recount`, `_novel_done`,
  `_desloppify`, `_wordcount`, `_desloppify_ledger`, `_state_mutators` (3
  blocks), and `novel.py`. Landed assertion 2 (AST no-`novel_state` dependency);
  red-green verified by temporarily reverting `_recount` (test went red, then
  green when restored). `grep -rn 'novel_state import' novel_ralph_skill/
  commands/` returns nothing. `make all` green (1425 passed). Coderabbit: 0
  findings.
- [x] (done) WI4: repoint **every** test-suite seam-import site to the
  neutral home. Commit `d659984`. Repointed the six seam importers
  (`test_state_input_message_parity.py`, `test_state_input_message_unit.py`,
  `test_compile_unit.py`, `test_draft_read_message_unit.py`,
  `test_validate_state_corpus.py`, `multiplexer_support.py`), preserving each
  symbol set (private formatters stay private). The two `_state_load`-named
  files were already repointed automatically by WI1's `leta mv` (Group 1).
  Remaining `novel_state import` hits in tests are all `build_app` /
  `_render_reconciliation`. `make all` green (1425 passed). Coderabbit: 0
  findings.
- [x] (done) WI5: swept the stale-name trail and dropped the transitional
  re-export. Swept clean-up 1 (`_state_load` tokens: `state_sourcing.py:74`
  self-citation re-anchored to `state_sourcing.py:52-67` after the WI1 docstring
  growth shifted the cwd-relative rule; `novel.py:153` likewise;
  `state/compile_model.py:73`; `_state_mutators.py:64-66` B7 home comment; the
  three devguide tokens at 620/976/1242 folded forward so the WI5 gate is
  clean), clean-up 2 (command-module `_load_or_state_error`/`novel_state._<…>`
  roles in `_desloppify`, `_wordcount`, `_state_mutators`, `_novel_done`,
  `state_sourcing` plus the four B5 test docstring roles), and clean-up 3 (the
  `novel_state` re-export drop: import block trimmed to the six body-used seam
  symbols, `__all__` reduced to `["build_app"]`, comment rewritten to name
  `state_sourcing` as the home). Renamed the WI2 structural test function (it
  embedded `_load_or_state_error` as a substring) to `test_loader_name_is_public`
  to avoid an A1 false positive. All four
  hard gates (1/2/3 + A1) return nothing; the Gate 3 eyeball backstop confirms
  every residual `novel_state` mention in `commands/` is a genuine
  command-surface reference (the pinned kept set). `make all` green (1425
  passed); `make nixie` and `markdownlint docs/developers-guide.md` green.
  Commit: pending coderabbit.
- [x] (done) WI6: updated the developers' guide. Confirmed the formatter
  passage is unguarded (B3): `grep -n
  '_state_load\|formatter\|Five\|sibling\|state_sourcing'
  tests/test_developers_guide_contract_drift_guard.py` matched only the word
  "sibling" in an unrelated markdown-parsing comment (line 19) — neither the
  "Five" count nor a module-name token is pinned, so the edit is safe. Added a
  paragraph after the formatter section naming `state_sourcing` as the neutral
  public home with the public `load_or_state_error`, consumed directly by every
  command rather than re-exported through `novel_state`, and restating the
  no-cycle import rule. The 620/976/1242 name tokens were already folded into
  WI5 so all four gates stay green; WI6 adds the substantive home-naming prose.
  `make all`, `make nixie`, and `markdownlint docs/developers-guide.md` green.
  Design §4 and ADR-003 need no change (they describe behaviour and the
  contract, not module layout) — confirmed, see Decision D11. Commit: pending
  coderabbit.
- [x] (done, fix round 1) Repoint the one design-doc source-file citation the
  rename broke. Commit `2c1be38`. The dual review found
  `docs/novel-ralph-harness-design.md:163` still cited `the _state_load.py
  source comment` as where the cwd-relative working-directory rule lives, but
  WI1 renamed `_state_load.py` to `state_sourcing.py`, so the named file no
  longer exists; the rule comment now physically lives in
  `state_sourcing.py:52-67` (`working_dir`/`WORKING_DIR_NAME`). This is a
  module-layout citation (it names a source file), so D11's premise that the
  design doc "describes behaviour... not module layout" is false **for this
  line specifically** — see the D11 correction below. The WI5 Gate 1
  (`grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`)
  was scoped without the design doc, so it never saw this line: a blind spot
  for the one design-doc citation D11 assumed was safe. Fix: rewrote line 163
  to name `state_sourcing.py`. While bringing the markdownlint gate green (it
  was already red on this branch — over-long inline-code spans in this execplan
  and its r2/r4 review records exceeded MD013's 80-char limit), wrapped those
  grep/import/regex spans into fenced code blocks; no gate semantics changed.
  `make all`, `make markdownlint`, and `make nixie` green (1425 passed, 1
  skipped). Coderabbit: 0 findings.

## Surprises & discoveries

- Observation: the seams the roadmap describes as living "in novel_state.py"
  already physically reside in a dependency-free leaf module
  `novel_ralph_skill/commands/_state_load.py`; `novel_state.py` only re-exports
  them through its `__all__`. Evidence: `novel_state.py` lines 61-73 import the
  symbols from `_state_load`; `_state_load.py` lines 1-18 document the
  leaf-module carve-out. Impact: the task reduces to (a) renaming the leaf to a
  neutral *public* name, (b) making `load_or_state_error` public, and (c)
  repointing every consumer's import path off `novel_state` onto the neutral
  home. The cycle-avoidance property is already in place and must be preserved,
  not created.
- Observation: the roadmap names `stub.py` as one of the import sites, but no
  `stub.py` exists in the current tree. Evidence: `find . -name stub.py`
  (excluding `.git`) returns nothing; the roadmap audit text predates task
  1.2.13, which removed the legacy `novel-x` entry points and the stub body.
  Impact: there is no `stub.py` to migrate. The plan migrates the seven modules
  that actually import the seams today; the success criterion "stub.py imports
  from the neutral home" is vacuously satisfied.

## Decision log

- Decision D1: name the neutral module
  `novel_ralph_skill/commands/state_sourcing.py` (flat, public, neutral), not
  `_state_io.py` and not a `state/` sub-package. Rationale: the roadmap offers
  `_state_io.py` or `state/sourcing.py` as *examples*. A public-named module
  signals the seam is a deliberate shared home (the underscore-private name is
  exactly the "misleading" property the audit flags). A flat module avoids
  speculatively creating a sub-package for one file (which would still hold
  `_state_load`'s 364-line body) and keeps the rename to a single `leta mv`.
  `state_sourcing` reads as "where commands source their state", matching the
  roadmap's "state-sourcing seam" framing. Date/Author: 2026-06-27, planning
  agent.
- Decision D2: keep `WORKING_DIR_NAME` in the new command-layer module; do not
  move it to `contract`. Rationale: roadmap task 7.3.6 owns the
  contract-package relocation and the `contract`→`commands` layering repair,
  and explicitly says to "coordinate with 7.3.1 so the state-sourcing module
  consumes the relocated WORKING_DIR_NAME" (`docs/roadmap.md` lines 2906-2907).
  Moving it now would pre-empt 7.3.6 and split its single clean edit.
  Date/Author: 2026-06-27, planning agent.
- Decision D3: make `load_or_state_error` public; rename via `leta rename` and
  retain no underscore alias once all consumers are repointed. Rationale: the
  roadmap success criterion is "a dedicated module with a public
  `load_or_state_error`". The other migrated seams (`STATE_INPUT_ERRORS`,
  `WORKING_DIR_NAME`, `state_path`, `working_dir`, `resolved_working_dir`) are
  already public; only `_load_or_state_error` and the formatter helpers
  (`_state_input_error`, `_draft_read_error`, `_compile_write_error`,
  `_rule_pack_read_error`, `_device_ledger_read_error`) carry underscores. The
  task names only `load_or_state_error` for promotion, so the formatter helpers
  keep their underscore-private names but move with the module. Date/Author:
  2026-06-27, planning agent.
- Decision D4: cuprum is not on this task's path. Rationale: design §4 records
  that "none [of the deterministic commands] invoke an external process for its
  core logic, so cuprum is required only where a command shells out (none do in
  v1)" (`docs/novel-ralph-harness-design.md` lines 284-289).
  `grep -rn cuprum novel_ralph_skill/commands/` returns nothing. The seams
  migrated here read `state.toml` via `tomllib`/`load_state` and resolve paths
  via `pathlib`, with no subprocess. No cuprum catalogue, allowlist, or `run`/
  `output` option is involved, so there is no cuprum API to pin for this work
  item. The console-scripts e2e suite (`tests/test_console_scripts_e2e.py`)
  does build-and-install, but it is not modified by this task and its catalogue
  usage is unchanged. Date/Author: 2026-06-27, planning agent.
- Decision D5 (B1 — test-file rename policy): the **test filenames**
  `tests/test_state_load_resolved_working_dir.py` and
  `tests/test_state_load_actionable_parity.py` are an **accepted residual** and
  are **not** renamed in this task. Rationale: the `grep -rn '_state_load'`
  hard gate (WI5) scopes to *file contents* under `novel_ralph_skill/`,
  `tests/`, and `docs/developers-guide.md`, not to filenames; renaming the
  files would force a matching rename of any `pytest` selection paths and CI
  references for no behavioural or hygiene gain, and the "defining-module path
  is canonical" rule (developers-guide 1080-1090) governs *module paths cited
  in prose*, not test filenames. The gate therefore excludes filenames by
  construction (`grep -rn` searches contents, not names). The two files'
  *contents* are fully swept: the `leta mv` import repoint (lines 13 and 51
  respectively) plus the two docstring prose fixes in
  `test_state_load_actionable_parity.py` (lines 6 and 13, the `:mod:` role and
  the "definition module `_state_load`" free prose). If a future task wants the
  filenames aligned, that is a one-line `git mv` per file and is out of scope
  here. Date/Author: 2026-06-27, planning agent.
- Decision D6 (B2 — parity test imports the private formatters, not the seam):
  `tests/test_state_load_actionable_parity.py` deliberately imports the five
  **underscore-private** formatters (`_compile_write_error`,
  `_device_ledger_read_error`, `_draft_read_error`, `_rule_pack_read_error`,
  `_state_input_error`) **directly from the definition module** (today
  `_state_load`, line 51), and its docstring (lines 12-14) states this is
  intentional — "from their definition module … (not the `novel_state`
  re-export) so the guard exercises the implementation location". Decision D3
  keeps these formatters underscore-private and does **not** promote them, so
  this file must keep importing the *private formatter set*, never the public
  `load_or_state_error`. Its only changes are the automatic `leta mv` import
  repoint (the source module name moves `_state_load` → `state_sourcing`; the
  imported symbol names are unchanged) plus the two B1 docstring prose fixes.
  WI4's generic "import the seam from `state_sourcing`" guidance does **not**
  apply to this file — it is a formatter-set parity test, not a seam test.
  Date/Author: 2026-06-27, planning agent.
- Decision D7 (B3 — the devguide 619-649 formatter prose is unguarded; record
  the grep, change only the module name): a
  `grep -n "_state_load\|formatter\| Five\|sibling\|state_sourcing" tests/test_developers_guide_contract_drift_guard.py`
  returns nothing for the formatter prose — the only active developers-guide
  drift-guard (`tests/test_developers_guide_contract_drift_guard.py`) pins the
  **exit-code table** (heading-anchored slice) and the **six-field envelope
  brace-list** (`working_dir` + five others), derived from
  `dataclasses.fields(Envelope)` and the `ExitCode` enum; it does **not** pin
  the formatter *count* ("Five") or the module name token at line 620. The
  proposed count-guard from `docs/issues/audit-6.3.9.md` was confirmed never
  landed. Therefore WI6's edit to the 619-649 passage is safe: the count word
  "Five" **stays** (the formatter set is unchanged by this task), and only the
  module-name token `_state_load` at line 620 **moves** to `state_sourcing`.
  The edit must not leave the passage half-updated (count changed, name stale,
  or vice versa). Date/Author: 2026-06-27, planning agent.
- Decision D8 (B4/B6 — repoint every test that imports a seam symbol from
  `novel_state`, in WI4, before WI5 drops the re-exports): a complete
  `grep -rn 'novel_state import' tests/` inventory (run against the current
  tree) shows **six** test files import a *seam* symbol (as opposed to the
  genuine command surface `build_app`/`_render_reconciliation`) from the
  re-export façade. All six must be repointed to
  `novel_ralph_skill.commands.state_sourcing` **in WI4**, which lands *before*
  WI5 trims `novel_state`'s re-exports. Two of them import symbols WI5 **drops
  from `novel_state` entirely** — `tests/multiplexer_support.py:25`
  (`WORKING_DIR_NAME`) and `tests/test_state_input_message_unit.py:22`
  (`_state_input_error`, alongside `_load_or_state_error`/`state_path`/
  `working_dir`) — so if WI4 omitted them, WI5's commit would fail `make all`
  with a hard `ImportError` (collection error), violating the
  single-gate-passing-commit invariant. `multiplexer_support.py` is a
  conftest-registered plugin (`tests/conftest.py:64`) imported by the
  `test_multiplexer_dispatch`/`_behaviour`/`_legacy_surface_retired` suites, so
  its breakage fails the whole multiplexer suite at collection. The repoint
  preserves each file's *symbol set verbatim*; only the source module token
  changes. Two of the six import **private formatters** that Decision D3 keeps
  private (`tests/test_draft_read_message_unit.py:25` imports
  `_draft_read_error`; `tests/test_state_input_message_unit.py:22` imports
  `_state_input_error`), so WI4's generic "import the *public* seam" guidance
  does **not** apply to those rows — they keep importing the private formatter,
  only repointed to `state_sourcing`. Date/Author: 2026-06-27, planning agent.
- Decision D9 (B5 — four `novel_state._<formatter>` docstring roles become
  dangling after WI5 and no test guards them): four test-module docstrings carry
  `:func:` roles that name the re-export façade
  (`tests/test_draft_read_message_unit.py:4` and
  `tests/test_draft_read_message_parity.py:7` → `novel_state._draft_read_error`;
  `tests/test_state_input_message_unit.py:4` and
  `tests/test_state_input_message_parity.py:5` →
  `novel_state._state_input_error`). After WI5, `_state_input_error` no longer
  exists on `novel_state` at all, and `_draft_read_error` is no longer
  canonical there, so both roles violate the developers-guide "defining-module
  path is canonical, never the re-export façade" rule (lines 1080-1104) that
  this plan's Constraints invoke. These rot **silently**: the WI5 `_state_load`
  gate does not match them (they say `novel_state`), `make lint`/`nixie`
  resolve no Sphinx cross-references (nixie is Mermaid-only, Makefile:121-123),
  and the projection drift-guard pins only `compile_model`/reconciliation. They
  are therefore added to WI5 clean-up 2 (rewrite each role to the canonical
  `novel_ralph_skill.commands.state_sourcing._<formatter>` path) and the WI5
  hard gate is broadened with a second pattern, `novel_state\._[a-z_]*error`
  (Gate 2 as implemented in the WI5 gate block), that must also return nothing
  after WI5. Its `\._` anchor matches only the dot-underscore
  `novel_state._<…>error` formatter/seam roles — including
  `novel_state._load_or_state_error` — and so by construction it does **not**
  match the bare public `novel_state.load_or_state_error` re-export role (a
  `.l`, not a `._`). The WI5 re-export drop also removes that bare public
  `novel_state.load_or_state_error` path, but the role naming it on the façade
  is closed by the A1 insurance grep (`_load_or_state_error` must return
  nothing everywhere), not by Gate 2. Date/Author: 2026-06-27, planning agent.

- Decision D10 (B7 — the `_state_mutators.py:64-66` "single accessor home"
  comment and the `state_sourcing.py` docstring import-home prose are
  stale-home claims that both token gates miss; sweep them and add Gate 3):
  after WI3 repoints `_state_mutators.py`'s imports onto `state_sourcing`, the
  module's lines 64-66 comment still asserts `_state_path`/`_working_dir` are
  "re-exported from `novel_state` (the single accessor home)" — false on both
  halves (`state_sourcing` is now both the re-export source and the single
  home). This is a plain `:mod:` role plus free prose: Gate 1 matches only
  `_state_load` (absent here) and Gate 2 matches only `novel_state._<…>error`
  (no `._error` suffix here), so neither catches it. It is the third successive
  fresh token (`_state_load` → B1, `novel_state._<formatter>` → B5,
  `novel_state`-as-home → B7) to slip a gate scoped to exactly the prior token.
  The fix has three parts: (1) add `_state_mutators.py:64-66` and the
  `state_sourcing.py` docstring import-home prose to WI5 clean-up 1, rewriting
  both to name `state_sourcing` as the single accessor home; (2) add **Gate
  3**, a keyword pattern

  ```text
  novel_state.*(single accessor home|accessor home|the home|seam home| re-exported from)
  ```

  over `commands/`, that must return nothing; (3) add an enumerate-and-eyeball
  backstop (`grep novel_state` over `commands/`, minus import lines) whose
  every surviving hit must be a genuine command-surface reference, and widen
  Gate 3 if a new home phrasing appears. The genuine command-surface references
  that legitimately survive are pinned in WI5 Stage F (`_state_mutators.py:6`,
  `_chapter_plan_entry.py:6/9`, `_gate_drafting_mutators.py:11/349/353`,
  `novel.py:82/86`, and the factual cycle-rule sentence in the
  `state_sourcing.py` docstring). The chosen mechanism is a prose gate, not
  Wafflecat's structural import-graph gate, because B7 is a *comment* defect
  (comments are not imports); the structural gate is recorded as a 7.3.6
  improvement, not adopted here. Also added the A1 insurance grep
  (`_load_or_state_error` must return nothing everywhere after the public
  rename) to the WI5/WI6 gate block. Date/Author: 2026-06-27, planning agent.

- Decision D11 (WI6 — design doc and ADR confirmation): the design doc §4 and
  ADR-003 were re-read during WI6 and need no change. They describe the
  *behaviour* of the deterministic commands and the *contract* (the shared
  envelope, the exit-3 state-error channel, the single-enforcement-point
  discipline), not the command-layer module layout. This task moves no
  behaviour and changes no contract, so neither document mentions `_state_load`
  or `novel_state`-as-seam-home, and no edit is warranted. Recorded here per the
  plan rather than editing them. Date/Author: 2026-06-27, implementing agent.
  - **Correction (fix round 1):** D11's premise is sound for §4 and ADR-003 but
    false for one specific design-doc line. `docs/novel-ralph-harness-design.md:163`
    is **not** behaviour/contract prose: it names the source file that hosts the
    cwd-relative working-directory rule (`the _state_load.py source comment`),
    which is a module-layout citation. WI1 renamed that file to
    `state_sourcing.py`, so the citation dangled. The dual review flagged it as
    the round-1 blocking stale-citation defect; it was fixed in commit `2c1be38`
    by repointing line 163 onto `state_sourcing.py`. Lesson: "the design doc
    describes behaviour, not layout" is true in aggregate but must be checked
    line by line — a single source-file reference is a layout citation that a
    rename can break, and the WI5 `_state_load` gate was scoped without the
    design doc, so it could not catch it. Date/Author: 2026-06-27, fix-round-1
    agent.

## Outcomes & retrospective

Result vs. purpose: achieved. The state-sourcing seam now lives in the neutral,
public-named `novel_ralph_skill/commands/state_sourcing.py`; the public loader
`load_or_state_error` is in the module's `__all__`; no command imports a seam from
`novel_state` (it re-exports nothing it does not itself use, `__all__ =
["build_app"]`); the structural test pins both the public home and the
no-`novel_state`-dependency rule; and `make all` is green at every commit.

Deviations from the plan, with rationale:

- The cwd-relative-rule line citation moved from `_state_load.py:32-48` to
  `state_sourcing.py:52-67` rather than the plan's predicted `:32-48`. WI1's
  neutral-home docstring rewrite plus the new explicit `__all__` block grew the
  module header, shifting the `WORKING_DIR_NAME`/`working_dir` block down. The
  plan's WI5 entry anticipated this ("re-grep `working_dir` in the renamed file
  to be sure"); the citations were re-anchored to the verified current range.
- An A1 false positive surfaced: the WI2 test function
  `test_load_or_state_error_is_public` embedded the historical
  `_load_or_state_error` token as a substring, which the A1 insurance grep would
  flag. Renamed it to `test_loader_name_is_public` in WI5. The plan did not
  foresee this (the function was added in WI2, after the A1 grep was specified),
  but the rename keeps A1 honest.
- WI5 folded the three developers-guide name tokens (620/976/1242) forward so
  the WI5 hard gate — whose scope explicitly includes
  `docs/developers-guide.md` — returns nothing before WI5's commit, exactly as
  the plan's "whichever work item lands first must change it" note for line 620
  directs. WI6 then added the substantive home-naming paragraph on top of the
  already-renamed tokens, so both work items remain atomic and gate-passing.
- Coderabbit hit transient rate limits on WI5 and WI6; cleared with exponential
  backoff (120s, 60s for WI5; ~210s for WI6) and re-ran to completion with 0
  findings each. Earlier work items drew minor findings on the planning prose
  only (no code findings); those were actioned in the living plan.

The known `make fmt` mdformat-all churn (reflowing ~284 unrelated `docs/` and 5
`skill/` markdown files) was stashed and discarded at WI1; only the intended
Python edits were kept, matching the established practice on this repo.

## Context and orientation

This repository is a Python harness that drives long-form novel drafting under
a Ralph-loop. The deterministic command spine is a single `novel` multiplexer
(design §4) with a `state` subgroup and four leaf verbs (`done`, `compile`,
`desloppify`, `wordcount`). Each command is a Cyclopts application run through
a shared `run` wrapper that owns the JSON envelope and exit codes (ADR-003).

The package under change is `novel_ralph_skill/commands/`. Key files:

- `novel_ralph_skill/commands/novel_state.py` — the `novel state` Cyclopts app
  (the `check` query, the `init` builder, and the registered mutators). It
  *re-exports* the state-sourcing seam through its `__all__` (lines 89-102) so
  every command imports the seam "from `novel_state`".
- `novel_ralph_skill/commands/_state_load.py` — the dependency-free leaf module
  that actually *defines* the seam: `WORKING_DIR_NAME` (line 38), `working_dir`
  (41), `resolved_working_dir` (52), `state_path` (68), `STATE_INPUT_ERRORS`
  (85), the five actionable-message formatters `_state_input_error` (103),
  `_draft_read_error` (173), `_compile_write_error` (220),
  `_rule_pack_read_error` (259), `_device_ledger_read_error` (299), the shared
  `_file_fault_error` (146), and `_load_or_state_error` (335). It imports only
  from `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner` (lines
  26-27), never from `novel_state`.
- The seven consumers and the seam symbols each imports today
  (verified with `leta refs` and direct reads):
  - `_compile.py` (lines 46-53): `STATE_INPUT_ERRORS`, `_compile_write_error`,
    `_draft_read_error`, `_load_or_state_error`, `state_path`, `working_dir`.
  - `_recount.py` (29-32): `STATE_INPUT_ERRORS`, `_draft_read_error`.
  - `_novel_done.py` (39-45): `STATE_INPUT_ERRORS`, `_draft_read_error`,
    `_load_or_state_error`, `state_path`, `working_dir`.
  - `_desloppify.py` (46-52): `STATE_INPUT_ERRORS`, `WORKING_DIR_NAME`,
    `_draft_read_error`, `_load_or_state_error`, `_rule_pack_read_error`.
  - `_wordcount.py` (42-47): `STATE_INPUT_ERRORS`, `WORKING_DIR_NAME`,
    `_draft_read_error`, `_load_or_state_error`.
  - `_desloppify_ledger.py` (35): `_device_ledger_read_error`.
  - `_state_mutators.py` (35-44): `STATE_INPUT_ERRORS`, `_state_input_error`,
    and `state_path`/`working_dir` aliased as `_state_path`/`_working_dir`.
    `_reconcile.py` and `_recount.py` re-import `_state_path`/`_working_dir`
    *from `_state_mutators`*, so that re-export tail (`_state_mutators.__all__`,
    lines 68-76) is a second hop the plan must keep coherent.
  - `novel.py` (line 36): `resolved_working_dir` (the production entry point's
    envelope label).
- The contract layer: `novel_ralph_skill/contract/runner.py` defines
  `StateInputError` and `make_contract_app`; `contract/errors.py` defines the
  `EnvelopeMessagesError` base. These are unchanged by this task.

Terms of art:

- **State-sourcing seam.** The shared answer to "where does a command look for
  state, what counts as a state-input fault, and how is a failed load rendered
  as the exit-3 error" — concretely `WORKING_DIR_NAME`, `working_dir`,
  `state_path`, `STATE_INPUT_ERRORS`, and `load_or_state_error`.
- **Exit-3 state-error channel.** A command signals an unreadable/missing
  `state.toml` (or refuses a mutation) by raising `StateInputError`, which
  `run` maps to exit 3 (ADR-003 Table 2; developers-guide lines 614-617).
- **Re-export façade.** A module that imports a symbol solely to re-expose it in
  its own `__all__` so callers can import it "from here". `novel_state.py` is
  the current façade for the seam.

Design and decision sources this task implements:

- `docs/novel-ralph-harness-design.md` §3.1 (output modes / the envelope the
  exit-3 channel feeds) and §4 (the deterministic commands and the
  `novel state` subgroup, lines 274-318).
- `docs/adr-003-shared-interface-contract.md` (the shared envelope, the exit-3
  state-error channel, and the single-enforcement-point discipline this move
  continues).
- `docs/developers-guide.md` lines 619-649 (the five sibling formatters in the
  leaf module), lines 970-979 (`novel done` reusing the `novel state` seams),
  and lines 1080-1104 (the "defining-module path is canonical, never the
  re-export façade" rule the prose cross-references must follow).
- AGENTS.md "Use clear file boundaries", "Keep file size manageable",
  "Abstraction / port / helper policy" (sweep before adding; record the new
  home's scope in the developers' guide), and the testing rules.

This continues the single-home discipline of roadmap tasks 1.3.3/1.3.4/1.3.6
(referenced by the 7.3.1 roadmap entry, lines 2770-2773), which carved shared
seams into neutral homes behind the command facade.

## Plan of work

The work is staged so each work item is independently committable and
gate-passable (`make all` green at every commit). Stages B-G map one-to-one to
work items WI1-WI6.

### Stage A: understand and propose (no code changes — done in this plan)

The orientation above pins the exact seam symbols, their definitions in
`_state_load.py`, the seven consumers, the `_state_mutators` second-hop
re-export, the test import inventory, and the six prose cross-references. No
code changes in this stage.

### Stage B / WI1 — Promote the leaf to the neutral `state_sourcing.py` home

Rename `novel_ralph_skill/commands/_state_load.py` to
`novel_ralph_skill/commands/state_sourcing.py` using `leta mv` (which updates
import statements automatically), then rename the symbol `_load_or_state_error`
to the public `load_or_state_error` using `leta rename` (which updates every
reference site, including `novel_state.py`'s import and `__all__`, the
consumers, and the tests, atomically). Update the new module's own module
docstring (formerly `_state_load.py` lines 1-18) to describe it as the
**neutral, public state-sourcing home** for the command layer — the single
place where the `working/` location, the state-input fault vocabulary, and the
load-and-translate boundary live — rather than "re-exported by `novel_state` so
the command stays under the 400-line cap". Keep the dependency-free,
no-`novel_state`-import property and document it as a constraint, not an
incidental.

After `leta mv`/`leta rename`, the seam is *defined* in `state_sourcing.py` and
still *re-exported* by `novel_state.py` (its import block and `__all__` now name
`state_sourcing` and `load_or_state_error`). This intermediate state keeps
every consumer green because they still import "from `novel_state`". WI1's
commit therefore changes only the definition site and the façade, leaving
consumers and their behaviour untouched — `make all` must pass.

Validation: `make all` green;
`grep -rn 'load_or_state_error' novel_ralph_skill/` shows the public name;
`_state_load.py` no longer exists.

### Stage C / WI2 — Add the structural home-and-import test (red first)

Add `tests/test_state_sourcing_home.py` with two assertions, written **before**
the consumer migration so it fails red first (AGENTS.md red-green discipline):

1. **Public-home assertion.** The import below succeeds, and
   `load_or_state_error` carries no leading underscore (assert the name is in
   the module's `__all__` and is callable). This passes after WI1.

   ```python
   from novel_ralph_skill.commands.state_sourcing import (
       load_or_state_error,
       STATE_INPUT_ERRORS,
       WORKING_DIR_NAME,
       state_path,
       working_dir,
       resolved_working_dir,
   )
   ```

2. **No-`novel_state`-dependency assertion.** For each command module under
   `novel_ralph_skill/commands/` other than `novel_state.py`, parse its source
   with `ast` and assert it contains no `ImportFrom` whose module is
   `novel_ralph_skill.commands.novel_state` that imports any seam name
   (`load_or_state_error`, `STATE_INPUT_ERRORS`, `WORKING_DIR_NAME`,
   `state_path`, `working_dir`, `resolved_working_dir`, `_state_input_error`,
   `_draft_read_error`, `_compile_write_error`, `_rule_pack_read_error`,
   `_device_ledger_read_error`). This is **red** until WI3 repoints the
   consumers; it turns green as they migrate. (Use `ast` over the source text,
   not a live import, so the test names the offending module precisely and does
   not depend on import-time side effects.) Note: the public leaf constant
   `INSPECT_REPAIR_REMEDY` (`_state_load.py:100`) is **intentionally excluded**
   from the forbidden-import set — it is module-internal (used only at lines
   142 and 215, no consumer imports it), so it is not a migrated seam and a
   reader should not flag its absence as a gap.

Commit shape (fixed, not deferred): land **assertion 1 green in WI2's commit**
(it passes immediately after WI1 promotes the module). Add **assertion 2 as the
opening red step of WI3's commit** — write it red, then repoint the consumers
in the same commit so it ends green. This keeps each work item atomic and a
single gate-passing commit, and preserves the red-green proof without
committing a red test or relying on `xfail`.

Validation: `make test` runs the new file; assertion 1 passes.

### Stage D / WI3 — Repoint the seven command consumers

For each consumer, change its
`from novel_ralph_skill.commands.novel_state import (...)` block to
`from novel_ralph_skill.commands.state_sourcing import (...)`, preserving the
imported-name set exactly:

- `_compile.py` lines 46-53.
- `_recount.py` lines 29-32.
- `_novel_done.py` lines 39-45.
- `_desloppify.py` lines 46-52.
- `_wordcount.py` lines 42-47.
- `_desloppify_ledger.py` line 35.
- `_state_mutators.py` lines 35-44 (the `STATE_INPUT_ERRORS`,
  `_state_input_error`, and `state_path as _state_path` /
  `working_dir as _working_dir` aliased imports). Its `__all__` re-export tail
  (lines 68-76) is unchanged in *name* — `_state_path`/`_working_dir`/
  `_state_input_error` still re-export — only the upstream source moves, so
  `_reconcile.py` and `_recount.py` (which import `_state_path`/`_working_dir`
  from `_state_mutators`) need no edit.

Migrate `novel.py` line 36 (`resolved_working_dir`) in the same work item,
since it is the last command-layer importer of a seam from `novel_state`.

After the last consumer is repointed, WI2's no-dependency assertion turns green.

Validation after each consumer: `make test` for that command's suite, then
`make all` at the end of the work item. The assertion-2 test is green.

### Stage E / WI4 — Repoint every test-suite seam-import site

This work item must land **before** WI5 drops the transitional re-exports,
because two of the files below import symbols WI5 removes from `novel_state`
entirely; repointing them here keeps WI5's commit green (Decision D8). The
full, enumerated inventory is split into two groups.

**Group 1 — already-repointed `_state_load` importers (verify, do not
re-edit).** `leta mv` rewrites these `import` statements automatically when the
module is renamed in WI1; this work item only *confirms* the repoint landed.
Their *filenames* are kept as-is (an accepted residual — Decision D5); their
*prose* (docstring `:mod:` roles, free-text module names) is swept in WI5 under
the hard gate, not here.

- `tests/test_state_load_resolved_working_dir.py:13` — imports public symbols
  from `_state_load`; `leta mv` repoints to `state_sourcing`. Confirm.
- `tests/test_state_load_actionable_parity.py:51` — **special case (Decision
  D6).** Imports the **five underscore-private formatters**
  (`_compile_write_error`, `_device_ledger_read_error`, `_draft_read_error`,
  `_rule_pack_read_error`, `_state_input_error`) **from the definition
  module**, *deliberately* (its docstring states it exercises the
  implementation location, not the `novel_state` re-export). `leta mv` repoints
  the source module token; the symbol set is unchanged. Do **not** "tidy" this
  onto the public seam — that breaks its formatter-parity purpose. Its two
  stale docstring prose references (lines 6 and 13) are fixed in WI5.

**Group 2 — `novel_state` seam importers (this work item must hand-repoint
each).** A complete `grep -rn 'novel_state import' tests/` against the current
tree surfaces exactly **six** test files that import a *seam* symbol (not the
genuine command surface `build_app`/`_render_reconciliation`) from the
re-export façade. `leta rename` rewrote `_load_or_state_error` →
`load_or_state_error` *within* these imports, but it does **not** move the
import off the `novel_state` source module, so each must be hand-repointed to
`from novel_ralph_skill.commands.state_sourcing import (...)`, preserving the
symbol set verbatim. The classification (public seam vs private formatter; kept
vs dropped from `novel_state` by WI5) is fixed per row:

- `tests/multiplexer_support.py:25` — `WORKING_DIR_NAME` (public; **WI5 drops it
  from `novel_state`**). Repoint to `state_sourcing`. **Load-bearing for the
  single-gate invariant:** this file is a conftest-registered plugin
  (`tests/conftest.py:64`) imported by the `test_multiplexer_dispatch`,
  `test_multiplexer_behaviour`, and `test_multiplexer_legacy_surface_retired`
  suites; if it still imports `WORKING_DIR_NAME` from `novel_state` when WI5
  drops it, the whole multiplexer suite fails at collection with `ImportError`.
- `tests/test_state_input_message_unit.py:22` — `load_or_state_error` (public
  seam, kept), `_state_input_error` (**private formatter; WI5 drops it from
  `novel_state`**), `state_path`, `working_dir` (public, kept). Repoint the
  whole block to `state_sourcing`, keeping `_state_input_error` (Decision D8:
  it is a private-formatter import, so the generic "import the public seam"
  guidance does **not** force its removal). Without this repoint WI5's commit
  fails with `ImportError` on `_state_input_error`.
- `tests/test_state_input_message_parity.py:20` — `load_or_state_error` (public
  seam), `state_path` (public). Both kept by `novel_state`, but the
  canonical-path rule still requires the repoint to `state_sourcing`.
- `tests/test_draft_read_message_unit.py:25` — `_draft_read_error` (**private
  formatter**; kept by `novel_state`). Repoint to `state_sourcing` keeping the
  private formatter name (Decision D8: not the public seam).
- `tests/test_compile_unit.py:30` — `state_path`, `working_dir` (public; kept by
  `novel_state`). Repoint to `state_sourcing`.
- `tests/test_validate_state_corpus.py:30` — `STATE_INPUT_ERRORS` (public; kept
  by `novel_state`). Repoint to `state_sourcing`.

Decision: import the *seam* from `state_sourcing` in tests, **except** the
private-formatter rows above (`test_state_load_actionable_parity.py`,
`test_draft_read_message_unit.py`, and the `_state_input_error` symbol in
`test_state_input_message_unit.py`), which import the *private formatters* from
`state_sourcing` (Decisions D6/D8); tests of `build_app`, `check`, `init`, and
the mutators continue to import those from `novel_state` (the genuine
`novel state` command surface, not the seam).

Validation: `make test` green; `grep -rn 'novel_state import' tests/` must show
**only** the genuine command-surface imports `build_app` and
`_render_reconciliation`. Because some imports use the multiline
`from … import (` form (`test_state_input_message_unit.py`,
`test_state_input_message_parity.py`), inspect each `novel_state import` hit by
eye and confirm every remaining one is `build_app` or `_render_reconciliation`;
any seam or formatter name (`WORKING_DIR_NAME`, `STATE_INPUT_ERRORS`,
`state_path`, `working_dir`, `resolved_working_dir`, `load_or_state_error`, or
any `_…error` formatter) on a `novel_state` import is a miss to repoint.

### Stage F / WI5 — Sweep every stale name and drop the transitional re-export

`leta mv` rewrites only `import` statements and `leta rename` rewrites only
symbol references; **neither touches free-text docstring prose, `:mod:` roles,
or filename/line-number citations**. So after WI1's rename, a trail of stale
`_state_load`-named and bare-`_load_or_state_error` references survives that no
test guards — the projection drift-guard
(`tests/test_projection_docstring_drift_guard.py`) pins only the `compile_model`
/reconciliation projections, **not** the state-sourcing seam (it is silent on
these references). WI5 sweeps all of them and then proves the sweep
mechanically. Three clean-ups:

**1. Stale `_state_load` module-name / citation references.** After the rename
none of these may name the dead `_state_load` module. This is the full,
enumerated set (verified by
`grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`
against the current tree):

- `novel_ralph_skill/state/compile_model.py:73` — free prose
  `commands._state_load.working_dir`. **Outside `commands/`**, so it is missed
  by every other work item (WI3 is commands-only, WI6 is devguide-only) — fix
  it to `commands.state_sourcing.working_dir`.
- `novel_ralph_skill/commands/novel.py:153` — line-number citation
  `` `_state_load.py:32-48` `` → `` `state_sourcing.py:32-48` `` (re-confirm
  the cited line range still points at the cwd-relative resolution rule after
  the move; the body is copied verbatim by `leta mv`, so the offsets hold, but
  re-grep `working_dir` in the renamed file to be sure).
- `novel_ralph_skill/commands/state_sourcing.py` docstring (formerly
  `_state_load.py` lines 7-16) — the module's **own** docstring carve-out
  prose: "it is re-exported by :mod:`…novel_state`, so every command keeps
  importing these symbols from `novel_state` while the command module stays
  within the cap" (lines 8-9) and "never from `novel_state` … the
  `_state_mutators` → `novel_state` import direction" (lines 14-16). WI1
  already restructures this docstring into neutral-home prose; this entry pins
  that **no `_state_load` token AND no `novel_state`-as-the-re-export-home
  claim survives** in it (the neutral home is `state_sourcing` itself, so the
  docstring must not name `novel_state` as where commands "keep importing these
  symbols from"). Gate 1 catches the `_state_load` token; Gate 3 (added below)
  catches any residual `novel_state`-as-home prose. (A factual
  `never from novel_state` cycle-rule statement is legitimate and may stay, but
  must not assert `novel_state` is the import home.)
- `novel_ralph_skill/commands/state_sourcing.py:56` — the module's **own**
  self-citation `` `_state_load.py:32-48` `` → `` `state_sourcing.py:32-48` ``.
- `novel_ralph_skill/commands/novel_state.py:57` — the comment "lives in a
  dependency-free leaf module (`_state_load`)" → name `state_sourcing` (this
  comment is rewritten anyway when the transitional re-export is dropped in
  clean-up 3 below).
- `novel_ralph_skill/commands/_state_mutators.py:64-66` — the seam-ownership
  comment (B7 remedy). Today it reads "`_state_path` and `_working_dir` are
  re-exported from :mod:`…novel_state` (**the single accessor home**) for the
  sibling `_recount`/`_reconcile` mutator modules, which import them from
  here". After WI3 repoints this module's imports (lines 35-44) onto
  `state_sourcing`, **both halves of this comment are factually wrong**:
  `_state_path`/ `_working_dir` are then re-exported from `state_sourcing`, and
  `state_sourcing` — not `novel_state` — is the single accessor home. This is a
  plain `:mod:` role plus free prose with no `_state_load` token and no
  `._<…>error` suffix, so **neither Gate 1 nor Gate 2 can see it** (Gate 1
  matches only `_state_load`; Gate 2 matches only the `novel_state._<…>error`
  formatter/seam roles); it is the exact stale-prose-naming-the-old-home defect
  B1/B5 were created to kill, reappearing on a third token. Rewrite the comment
  to name `state_sourcing` as the single accessor home — "`_state_path`/
  `_working_dir` are re-exported from :mod:
  `novel_ralph_skill.commands.state_sourcing` (the single accessor home) for
  the sibling `_recount`/`_reconcile` mutator modules, which import them from
  here". Gate 3 (added below) proves no `novel_state`-as-home claim survives.
  This entry is the **module that performs the second-hop re-export**, so a
  stale home claim here is the precise hazard the round-3 pre-mortem named: a
  future `novel-state` refactor that re-pins the mutator tail back through
  `novel_state` would not trip the WI2 AST guard (which forbids only *direct*
  seam-name imports, not the `_state_path`/`_working_dir` re-export tail).
- `novel_ralph_skill/commands/novel_state.py:61` — `import` statement; the
  `leta mv` repoint handles this automatically, but it is dropped entirely in
  clean-up 3.
- `tests/test_state_load_resolved_working_dir.py:13` — `import`; `leta mv`
  repoints it automatically. Filename kept (Decision D5).
- `tests/test_state_load_actionable_parity.py:6` — docstring `:mod:` role
  `:mod:\`novel_ralph_skill.commands._state_load\`` → `:mod:\`
  novel_ralph_skill.commands.state_sourcing\``.
- `tests/test_state_load_actionable_parity.py:13` — docstring free prose
  "definition module `_state_load` (not the `novel_state` re-export)" → name
  `state_sourcing`. (Line 51's `import` is repointed automatically by
  `leta mv`; Decision D6 — keep the private-formatter import set, do not move
  to the public seam.)
- `tests/test_state_load_actionable_parity.py` **filename** kept as-is
  (Decision D5) — the gate searches contents, not names.
- `docs/developers-guide.md:620` — "the dependency-free leaf module
  `_state_load`" → name `state_sourcing` (this line is also touched by WI6;
  whichever work item lands first must change it, and the gate proves neither
  leaves it stale).

**2. Bare `_load_or_state_error` prose references** (the symbol is renamed
public by `leta rename`, which rewrites *code* references but **not** free-text
prose). Repoint the `:func:`/`:data:` roles and the bare-prose mentions to the
new defining-module path `novel_ralph_skill.commands.state_sourcing.…` with the
public `load_or_state_error`, per the developers-guide "defining-module path is
canonical, never the re-export façade" rule (lines 1080-1090):

- `_wordcount.py:112` — `:func:` role `novel_state._load_or_state_error`.
- `_wordcount.py:117` — **bare** `_load_or_state_error` in free prose (not a
  `:func:` role; `leta rename` will not touch it) → `load_or_state_error`.
- `_desloppify.py:168` (`novel_state._load_or_state_error`),
  `_desloppify.py:176` (`novel_state._draft_read_error`).
- `_state_mutators.py:89` (`novel_state._state_input_error`),
  `_state_mutators.py:91` (`novel_state._load_or_state_error`),
  `_state_mutators.py:130` (`novel_state._state_input_error`).
- `_novel_done.py:28` — module docstring lists `_load_or_state_error` (bare,
  in prose) among the reused helpers → `load_or_state_error`.

Also in clean-up 2 (B5 remedy — four test-module docstring `:func:` roles that
name the re-export façade and become dangling/non-canonical after WI5; none is
guarded by any test, so they rot silently). Rewrite each role from the
`novel_state._<formatter>` façade path to the canonical defining-module path
`novel_ralph_skill.commands.state_sourcing._<formatter>`, per the
developers-guide "defining-module path is canonical, never the re-export
façade" rule (lines 1080-1104). After WI5 `_state_input_error` no longer exists
on `novel_state` at all and `_draft_read_error` is no longer canonical there:

- `tests/test_draft_read_message_unit.py:4` —
  `:func:\`novel_ralph_skill.commands.novel_state._draft_read_error\`` → `
  :func:\`novel_ralph_skill.commands.state_sourcing._draft_read_error\``.
- `tests/test_draft_read_message_parity.py:7` —
  `:func:\`~novel_ralph_skill.commands.novel_state._draft_read_error\`` → `
  :func:\`~novel_ralph_skill.commands.state_sourcing._draft_read_error\``.
- `tests/test_state_input_message_unit.py:4` —
  `:func:\`novel_ralph_skill.commands.novel_state._state_input_error\`` → `
  :func:\`novel_ralph_skill.commands.state_sourcing._state_input_error\``.
- `tests/test_state_input_message_parity.py:5` —
  `:func:\`~novel_ralph_skill.commands.novel_state._state_input_error\`` → `
  :func:\`~novel_ralph_skill.commands.state_sourcing._state_input_error\``.

The developers-guide bare/role references at lines 976 and 1242 are handled in
WI6 (they live in the guide, not `commands/` or `tests/`).

**3. Drop the transitional re-export.** Remove the migrated seam symbols from
`novel_state.py`'s import block (lines 61-73) and `__all__` (lines 89-102),
keeping only what `novel_state` itself uses in its own body
(`STATE_INPUT_ERRORS`, `_draft_read_error`, `load_or_state_error`, `state_path`,
`working_dir`, `resolved_working_dir` are used by `_check`/`_init`/
`_disk_evidence_or_state_error`; keep those as *direct imports from
`state_sourcing`*, not as re-exports). Rewrite the now-obsolete re-export
comment at `novel_state.py:55-59`. The formatter helpers `novel_state` does not
call (`_compile_write_error`, `_rule_pack_read_error`,
`_device_ledger_read_error`, `_state_input_error`, `WORKING_DIR_NAME`) are
dropped from `novel_state` entirely once no consumer imports them from it.
Re-run the structural test: it must still pass, and `novel_state` must no
longer re-export any seam symbol it does not itself use.

This work item makes the single-home property real: `novel_state` becomes a
pure command facade again, and `state_sourcing` is the sole home.

**Hard gate (B1 + B5 + B7 remedy — mandatory, must pass before committing
WI5):** three patterns plus one insurance grep, each of which **must return
nothing**.

```bash
# Gate 1 (B1) — no dead `_state_load` module name survives in source, test
# contents, or the developers' guide.
grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md

# Gate 2 (B5) — no prose role or code reference names a migrated seam/formatter
# on the `novel_state` re-export façade. This catches the four dangling
# docstring roles the `_state_load` grep cannot see (they say `novel_state`).
grep -rnE \
  'novel_state\._[a-z_]*error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md

# Gate 3 (B7) — no comment or prose claims `novel_state` is the seam/accessor
# HOME. Gates 1 and 2 are token-scoped (`_state_load`; `novel_state._<…>error`)
# and cannot see a plain `:mod:`novel_state`` role or free prose asserting
# ownership, e.g. `_state_mutators.py:64-66`'s "re-exported from … novel_state
# (the single accessor home)". This pattern matches any `novel_state` mention
# co-located with a home/accessor/re-export ownership claim, in `commands/`
# only (the prose that must change lives there).
grep -rnE \
  'novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)' \
  novel_ralph_skill/commands/
```

Gates 1-3 **must return nothing**. The scope is deliberately file *contents*
under `novel_ralph_skill/`, `tests/`, and `docs/developers-guide.md` (Gate 3 is
scoped to `commands/`, where the seam-home prose lives) — it excludes test
*filenames* (an accepted residual, Decision D5) and the immutable historical
records under `docs/execplans/`, `docs/issues/`, and `docs/roadmap.md` (which
record the pre-rename name as history and must not be retro-edited). Gate 2's
pattern matches the dot-prefixed formatter/seam roles only, so it does **not**
flag the genuine command-surface references `novel_state.build_app` or
`novel_state._render_reconciliation` (a `_render_*` projection, not a migrated
seam).

**Gate 3 enumerate-and-eyeball backstop (B7).** Gate 3's keyword pattern
catches the *known* home-ownership phrasing, but the round-3 lesson is that a
token gate scoped to one phrasing can miss a new one. So WI5 also runs the
broad inventory below and eyeballs every residual `novel_state` reference in
`commands/`, confirming each surviving one is a **genuine command-surface**
reference (naming `novel_state` as the Cyclopts command module that hosts
`check`/`init`, the mutator-vs-command-module split, or the cycle-avoidance
rule) and **none** is a seam/accessor-home claim:

```bash
# Inventory every novel_state mention in commands/ that is NOT an import line,
# then read each by eye.
grep -rnE 'novel_state' novel_ralph_skill/commands/ \
  | grep -vE ':[0-9]+:(from |import )' \
  | grep -viE 'novel_state\.py'
```

The genuine command-surface references that legitimately survive (verified
against the tree) are: `_state_mutators.py:6` (`novel_state` keeps `check`/
`init`), `_chapter_plan_entry.py:6` and `:9` (the entry sits beside the command
module / the `_state_mutators → novel_state` cycle note),
`_gate_drafting_mutators.py:11`, `:349`, `:353` (registration-off-`novel_state`
prose), `novel.py:82` and `:86` (the multiplexer binds the `novel_state` app),
and the **factual** cycle-rule sentence in the `state_sourcing.py` docstring
("never imports from `novel_state`"). Every *other* residual — most importantly
`_state_mutators.py:64-66`'s "(the single accessor home)" and any
`state_sourcing.py` docstring sentence that names `novel_state` as the *import
home* — is a B7 miss to rewrite onto `state_sourcing`. If the eyeball turns up
a home claim Gate 3's keyword pattern did not match, fix the prose AND widen
Gate 3's pattern to include the new phrasing before committing, so the home
assertion lives in exactly one place (`state_sourcing`) and the codebase never
again claims otherwise.

```bash
# Insurance grep (A1) — the `_load_or_state_error` → `load_or_state_error` rename
# made the symbol public everywhere; no `_load_or_state_error` token (role or
# prose) may survive. Gate 1 cannot see these (they say `novel_state` or are
# bare) and Gate 2 passes whether a swept role reads `state_sourcing.
# load_or_state_error` (correct) or `state_sourcing._load_or_state_error` (a
# dangling underscore role resolving to no symbol). This catches a
# retained-underscore slip that nixie (Mermaid-only) and the underscore-free
# public symbol cannot.
grep -rn '_load_or_state_error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md
```

The insurance grep **must also return nothing** after WI5 (and is re-run after
WI6, since `devguide:1242` is swept there). If any grep returns a line, that
reference was missed; fix it and re-run until all four are clean. These gates
are the mechanical proof the rename and re-export drop left no dead
`_state_load` name (Gate 1), no dangling `novel_state._<formatter>` role (Gate
2), no stale-home `novel_state` claim (Gate 3), and no retained-underscore
`_load_or_state_error` (A1) behind — the exact failures the round-1 (B1),
round-3 (B5), and round-4 (B7) reviews flagged as the six-months-later trap,
each reproduced on a fresh token the prior round's gate could not see.

Validation: **all three** hard gates and the insurance grep above return
nothing; `make all` green; `make lint` (interrogate docstring coverage, ruff,
pylint) green — the cross-reference rename must not break a `:func:` role; the
projection drift-guard (`tests/test_projection_docstring_drift_guard.py`) green.

### Stage G / WI6 — Update the developers' guide and design docs

Per AGENTS.md "Document internally facing conventions in the developers' guide"
and the "Abstraction / helper policy" (record the new home's scope).

**Before editing, confirm the formatter passage is unguarded (B3 remedy).** Run
and record in the Decision Log (Decision D7 captures the expected outcome):

```bash
grep -n '_state_load\|formatter\|Five\|sibling\|state_sourcing' \
  tests/test_developers_guide_contract_drift_guard.py
```

This must return **nothing** for the formatter prose. The only active
developers-guide drift-guard pins the **exit-code table** and the **six-field
envelope brace-list** (derived from `dataclasses.fields(Envelope)` and the
`ExitCode` enum), not the formatter *count* or the `_state_load` module name.
The audit-6.3.9-proposed count-guard never landed. So the 619-649 edit is safe
today.

Then make the edits:

- `docs/developers-guide.md` **line 620** (within the 619-649 passage): the
  count
  word **"Five" stays** (this task does not change the formatter set), and only
  the module-name token `_state_load` **moves** to `state_sourcing`. The result
  reads "Five sibling formatters in the … module `state_sourcing`". Do **not**
  leave the passage half-updated (name changed but count stale, or vice versa).
  Add a sentence recording `state_sourcing` as the neutral public home for the
  state-sourcing seam with a public `load_or_state_error`, consumed by the five
  commands rather than re-exported through `novel_state`. (This line is also in
  the WI5 hard-gate enumeration; whichever work item touches it must move the
  name, and the WI5 gate proves it is not left stale.)
- `docs/developers-guide.md` **lines 970-979** (line 976): update the
  `novel done` passage that names "`novel state`'s `working_dir`, `state_path`,
  `_load_or_state_error`, and `STATE_INPUT_ERRORS` seams" to name the neutral
  `state_sourcing` home and the public `load_or_state_error`.
- `docs/developers-guide.md` **line 1242**: the two-helper document-load passage
  contrasts `_load_document_or_state_error` → `load_document` with
  `_load_or_state_error` → `load_state`. The `_load_or_state_error` token here
  is the symbol renamed public by WI1, so update it to `load_or_state_error`
  (`_load_document_or_state_error` is a *different*, still-private mutator
  helper and is **unchanged**).
- Confirm the design doc §4 and ADR-003 need no change (they describe behaviour
  and the contract, not the module layout); record that confirmation in the
  Decision Log rather than editing them.

Validation: `make markdownlint` and `make nixie` green for the docs change;
`make all` green; the WI5 hard gate (`grep -rn '_state_load' …`) still returns
nothing after WI6's edits.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-1`.

WI1:

```bash
leta mv novel_ralph_skill/commands/_state_load.py \
        novel_ralph_skill/commands/state_sourcing.py
leta rename _load_or_state_error load_or_state_error
# edit the module docstring of state_sourcing.py (neutral-home prose)
make all
```

WI2:

```bash
# add tests/test_state_sourcing_home.py (assertion 1 green; assertion 2 staged)
make test
```

WI3 (repeat per consumer, then once at the end):

```bash
# edit the import block in each of the seven consumers + novel.py
make all
```

WI4:

```bash
grep -rn 'novel_state import' tests/    # inventory: six seam files + build_app
# repoint the six seam files (Group 2, Decision D8) to state_sourcing,
# preserving each symbol set verbatim (private formatters stay private)
make test
# Verify only the genuine command surface survives on novel_state imports.
# Inspect each hit by eye (the multiline `(` form spans lines, so a single
# grep cannot bind symbol to module); every remaining one must be build_app
# or _render_reconciliation, never a seam/formatter name.
grep -rn 'novel_state import' tests/
```

WI5:

```bash
# sweep clean-up 1 (stale _state_load names AND the _state_mutators.py:64-66
# "single accessor home" comment + the state_sourcing.py docstring home prose,
# B7) + clean-up 2 (bare _load_or_state_error prose AND the four
# novel_state._<formatter> docstring roles, B5) across the enumerated sites
# trim novel_state.py import block + __all__ to drop the transitional re-exports
grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Gate 1 (B1): MUST return nothing before committing
grep -rnE \
  'novel_state\._[a-z_]*error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Gate 2 (B5): MUST return nothing before committing
grep -rnE \
  'novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)' \
  novel_ralph_skill/commands/
# ^ Gate 3 (B7): MUST return nothing before committing
# Then the enumerate-and-eyeball backstop: inventory every residual novel_state
# prose mention in commands/ and confirm each is a genuine command-surface
# reference, not a seam/accessor-home claim (see WI5 Stage F for the kept set).
grep -rnE 'novel_state' novel_ralph_skill/commands/ \
  | grep -vE ':[0-9]+:(from |import )' | grep -viE 'novel_state\.py'
grep -rn '_load_or_state_error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Insurance grep (A1): MUST return nothing before committing
make all
```

WI6:

```bash
# confirm the formatter passage is unguarded (B3) before editing
grep -n '_state_load\|formatter\|Five\|sibling\|state_sourcing' \
  tests/test_developers_guide_contract_drift_guard.py   # expect: nothing
# edit docs/developers-guide.md (line 620, lines 970-979/976, line 1242)
grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Gate 1 (B1) re-run: still MUST return nothing after WI6
grep -rnE \
  'novel_state\._[a-z_]*error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Gate 2 (B5) re-run: still MUST return nothing after WI6
grep -rnE \
  'novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)' \
  novel_ralph_skill/commands/
# ^ Gate 3 (B7) re-run: still MUST return nothing after WI6
grep -rn '_load_or_state_error' \
  novel_ralph_skill/ tests/ docs/developers-guide.md
# ^ Insurance grep (A1) re-run: still MUST return nothing after WI6 (devguide:1242)
make markdownlint
make nixie
make all
```

Expected transcript shape for `make all` at each gate:

```plaintext
... ruff format --check ... All checks passed!
... ruff check ... All checks passed!
... interrogate ... RESULT: PASSED
... pylint ... 10.00/10
... ty check ... All checks passed
... pytest ... N passed
```

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests:** `make test` passes with the same count as before, plus the new
  `tests/test_state_sourcing_home.py`. The new file's assertion 2 fails before
  WI3 and passes after (the red-green proof). The behaviour-pinning suites
  (`tests/test_state_input_message_unit.py`,
  `tests/test_state_input_message_parity.py`,
  `tests/test_draft_read_message_unit.py`,
  `tests/test_draft_read_message_parity.py`,
  `tests/test_state_load_actionable_parity.py`,
  `tests/test_state_load_resolved_working_dir.py`,
  `tests/test_desloppify_sourcing.py`, the mutator/snapshot suites) pass
  unchanged in substance — only their import lines move.
- **Lint/typecheck:** `make lint` (ruff, 100% interrogate docstring coverage,
  pylint) and `make typecheck` (`ty check`) pass. The `:func:` cross-reference
  renames must keep interrogate and the projection drift-guard green.
- **Audit:** `make audit` (pip-audit) passes (no dependency change expected).
- **Docs:** `make markdownlint` and `make nixie` pass for the WI6 docs change.
- **Structural acceptance:**
  `grep -rn 'novel_state import' novel_ralph_skill/commands/` returns no seam
  import; the only `novel_state`
  imports left are genuine command-surface ones (`build_app`). In `tests/`, the
  same grep shows only `build_app` and `_render_reconciliation`; **no** test
  imports a seam or formatter symbol (`WORKING_DIR_NAME`, `STATE_INPUT_ERRORS`,
  `state_path`, `working_dir`, `resolved_working_dir`, `load_or_state_error`,
  `_state_input_error`, `_draft_read_error`, `_compile_write_error`,
  `_rule_pack_read_error`, `_device_ledger_read_error`) from `novel_state`.
  `from novel_ralph_skill.commands.state_sourcing import load_or_state_error`
  succeeds. **Gate 1**
  (`grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`)
  returns nothing (no dead `_state_load` name in source, test contents, or the
  developers' guide). **Gate 2** (`grep -rnE 'novel_state\._[a-z_]*error' …`,
  matching every dot-prefixed formatter/seam role, which excludes `build_app`/
  `_render_reconciliation`) returns nothing (no dangling
  `novel_state._<formatter>` role survives in code or docstring prose). **Gate
  3**

  ```sh
  grep -rnE \
    'novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)' \
    novel_ralph_skill/commands/
  ```

  returns nothing (no comment or prose claims `novel_state` is the
  seam/accessor home — the B7 `_state_mutators.py:64-66` defect is swept), and
  the enumerate-and-eyeball backstop confirms every residual `novel_state`
  mention in `commands/` is a genuine command-surface reference. The **A1
  insurance grep**
  (`grep -rn '_load_or_state_error' novel_ralph_skill/ tests/ docs/developers-guide.md`)
  returns nothing (the symbol is public everywhere; no retained-underscore
  role survives).

Quality method (how we check): run `make all` (the aggregate target wiring
`build check-fmt lint typecheck test`, Makefile line 37) at the end of each
work item, and additionally `make markdownlint` and `make nixie` for WI6. Do
not proceed to the next work item if the current one's `make all` is red.

Testing-rule mapping (AGENTS.md "Python verification and testing"):

- **Unit:** the new `tests/test_state_sourcing_home.py` (public-home + AST
  no-dependency assertions) is a unit-level structural test; the migrated
  parity and message-unit suites remain unit tests.
- **Behavioural (pytest-bdd):** `tests/test_draft_read_message_bdd.py` and its
  steps exercise the exit-3 draft-read message; they import the seam and must
  pass after repointing. No new behaviour, so no new scenario is required — the
  refactor adds no user-visible behaviour to cover.
- **Property (hypothesis):** none required. This work item introduces no new
  invariant over a range of inputs; it relocates definitions without changing
  logic, so per the AGENTS.md rule ("Use property tests … when a change
  introduces an invariant over a range of inputs") no property test is added.
  If, contrary to expectation, the implementer finds a behavioural seam that
  warrants property coverage, load `python-verification` to choose between
  Hypothesis, CrossHair, and mutmut before adding one.
- **Snapshot (syrupy):** the existing mutator/gate snapshot suites
  (`tests/test_novel_state_mutator_snapshots.py`,
  `tests/test_set_gate_snapshots.py`) must stay byte-identical; no new snapshot
  is added (no new output boundary).
- **E2E:** `tests/test_console_scripts_e2e.py` (POSIX-only, ADR-006) must pass
  unchanged; the console-script surface and its catalogue usage are untouched.

## Idempotence and recovery

Each work item is a single logical commit; re-running `make all` is
non-destructive. `leta mv` and `leta rename` are deterministic; if a rename
leaves a stale reference, re-run `grep -rn` for the old name and fix the
remainder, then re-commit. If the structural test (WI2) is committed red by
mistake, `git revert` the WI2 commit or land the no-dependency assertion at the
head of WI3 instead. No data migration, no destructive filesystem operation,
and no network access is involved.

## Interfaces and dependencies

At the end of this plan the following must hold in
`novel_ralph_skill/commands/state_sourcing.py`:

```python
# Public seam (neutral home for the state-sourcing seam):
WORKING_DIR_NAME: str  # = "working"  (stays command-layer until 7.3.6)
def working_dir() -> pathlib.Path: ...
def resolved_working_dir() -> pathlib.Path: ...
def state_path() -> pathlib.Path: ...
STATE_INPUT_ERRORS: tuple[type[Exception], ...]
def load_or_state_error(path: pathlib.Path) -> State: ...  # was _load_or_state_error

# Underscore-private actionable-message formatters (move with the module,
# names unchanged — only load_or_state_error is promoted):
def _state_input_error(path: pathlib.Path, exc: Exception) -> StateInputError: ...
def _draft_read_error(reported_dir: pathlib.Path) -> StateInputError: ...
def _compile_write_error(target: pathlib.Path) -> StateInputError: ...
def _rule_pack_read_error(pack_path: Traversable) -> StateInputError: ...
def _device_ledger_read_error(ledger_path: pathlib.Path) -> StateInputError: ...
def _file_fault_error(message: str) -> StateInputError: ...
```

The module must import only from `novel_ralph_skill.state` (for `load_state`,
`State`) and `novel_ralph_skill.contract.runner` (for `StateInputError`) —
never from `novel_ralph_skill.commands.novel_state`.

`novel_ralph_skill/commands/novel_state.py` imports the seam *from*
`state_sourcing` for its own `_check`/`_init` bodies and re-exports nothing it
does not itself use. The five command consumers, `_wordcount.py`,
`_desloppify_ledger.py`, and `novel.py` import the seam from `state_sourcing`.

No new third-party dependency. No change to `pyproject.toml`,
`[project.scripts]`, or the cuprum catalogue.

## Revision note

Initial draft (2026-06-27). Decomposes roadmap task 7.3.1 into six ordered,
independently committable work items: promote the leaf to a neutral public
`state_sourcing` home with a public `load_or_state_error` (WI1), pin the home
and the no-`novel_state`-dependency rule with a structural test (WI2), repoint
the seven command consumers (WI3), repoint the test import sites (WI4), sweep
prose cross-references and drop the transitional re-export (WI5), and update
the developers' guide and design docs (WI6). The plan records that the seams
already live in the leaf `_state_load.py` (so the task is a rename-and-repoint,
not a fresh extraction), that `stub.py` no longer exists, that
`WORKING_DIR_NAME` stays command-layer pending 7.3.6, and that cuprum is not on
this task's path.

Revision 2 (2026-06-27) — design-review round 1 remediation. Resolves the three
blocking points:

- **B1 (stale-name sweep incomplete).** Rewrote Stage F/WI5 to enumerate every
  stale `_state_load` reference (`state/compile_model.py:73`, `novel.py:153`,
  `state_sourcing.py:7,56`, `novel_state.py:57`, the two `test_state_load_*`
  files' prose at lines 6/13, devguide:620) and every bare-prose
  `_load_or_state_error` mention (`_wordcount.py:117`, `_novel_done.py:28`),
  and added the mandatory hard gate
  `grep -rn '_state_load' novel_ralph_skill/ tests/ docs/developers-guide.md`
  (must return nothing) to WI5 and WI6. Added Decision D5 fixing the policy
  that the `test_state_load_*.py` **filenames** are an accepted residual (not
  renamed; the gate searches contents, not names) with the rationale. Updated
  the Risks section to record that no test guards these references and the gate
  is the mitigation.
- **B2 (WI4 mis-specifies the parity test's import source).** Added Decision D6
  and an explicit WI4 callout: `tests/test_state_load_actionable_parity.py`
  imports the five **underscore-private formatters** from the definition module
  (Decision D3 keeps them private), **not** the public `load_or_state_error`;
  its only change is the automatic `leta mv` import repoint plus the two B1
  docstring prose fixes. WI4's generic "import the seam from `state_sourcing`"
  guidance explicitly does not apply to this formatter-parity test.
- **B3 (WI6 edits the formatter prose without checking the count-guard).** Added
  Decision D7 recording the grep that confirms
  `tests/test_developers_guide_contract_drift_guard.py` pins only the exit-code
  table and envelope brace-list, not the formatter count or module name (the
  audit-6.3.9 count-guard never landed). Rewrote WI6 to require the pre-edit
  grep and to state that "Five" stays while only the `_state_load` token at
  line 620 moves to `state_sourcing`, and added devguide line 1242 to the sweep.

Also actioned the advisories: A2 (line count corrected 365 → 364 in both
places), A3 (WI2 commit shape fixed — assertion 1 green in WI2, assertion 2 as
WI3's opening red step; `INSPECT_REPAIR_REMEDY` noted as intentionally excluded
from the forbidden-import set).

Revision 3 (2026-06-27) — design-review round 2 remediation. Resolves the three
round-3 blocking points by making WI4's test inventory exhaustive and
broadening WI5's gate to the test side:

- **B4 (WI5 drops `WORKING_DIR_NAME` and `_state_input_error` from `novel_state`
  while two test files still import them).** Verified against the tree:
  `novel_state`'s body (lines >102) uses neither symbol, so clean-up 3 drops
  both; yet `tests/multiplexer_support.py:25` imports `WORKING_DIR_NAME` (and
  is a conftest-registered plugin, `tests/conftest.py:64`, feeding the
  multiplexer suite) and `tests/test_state_input_message_unit.py:22` imports
  `_state_input_error`. Rewrote Stage E/WI4 into two groups and added Decision
  D8: WI4 now enumerates **all six** `novel_state` seam importers and repoints
  each to `state_sourcing` (preserving the symbol set; private formatters stay
  private) **before** WI5 trims the re-exports, so no commit goes red. Added
  the high-severity test-import risk to the Risks section.
- **B5 (four `novel_state._<formatter>` docstring `:func:` roles rot silently
  after WI5).** Added Decision D9 and four explicit entries to WI5 clean-up 2
  (`test_draft_read_message_unit.py:4`, `test_draft_read_message_parity.py:7`,
  `test_state_input_message_unit.py:4`,
  `test_state_input_message_parity.py:5`), rewriting each role to the canonical
  `state_sourcing._<formatter>` path. Added a second hard gate to WI5/WI6 —
  `grep -rnE 'novel_state\._[a-z_]*error'` (a compact equivalent that matches
  every dot-prefixed underscore-`_…error` formatter/seam role —
  `_draft_read_error`, `_state_input_error`, `_compile_write_error`,
  `_rule_pack_read_error`, `_device_ledger_read_error` — while excluding the
  genuine command-surface references `novel_state.build_app` and
  `novel_state._render_reconciliation`). The renamed public re-export path
  `novel_state.load_or_state_error` has no leading underscore after the dot, so
  Gate 2 does **not** match it; the A1 insurance grep
  (`grep -rn '_load_or_state_error'`) and the WI5 re-export drop together remove
  any role naming the loader on the façade. Gate 2 must return nothing, catching
  exactly the underscore-formatter roles the `_state_load` grep cannot see.
  Verified against the tree: the pattern currently matches the ten pre-WI5 hits
  and none of `build_app` or `_render_*`. Added the silent-rot risk to the Risks
  section.
- **B6 (three further test files import seam symbols from `novel_state` that
  WI4's own validation forbids).** Enumerated `tests/test_compile_unit.py:30`
  (`state_path`, `working_dir`), `tests/test_validate_state_corpus.py:30`
  (`STATE_INPUT_ERRORS`), and `tests/test_draft_read_message_unit.py:25`
  (`_draft_read_error`, a private formatter) in WI4 Group 2 with their per-row
  classification, and noted (Decision D8) that the draft-read file imports the
  *private* formatter, so WI4's "import the public seam" guidance does not
  apply to it. WI4's validation grep now matches the full enumeration, removing
  the internal inconsistency between the omitted files and the final grep.

Revision 4 (2026-06-27) — design-review round 3 remediation. Resolves the
single round-3 blocking point:

- **B7 (a stale seam-home comment survives both hard gates).** After WI3
  repoints `_state_mutators.py`'s imports onto `state_sourcing`, the module's
  lines 64-66 comment still claims `_state_path`/`_working_dir` are
  "re-exported from :mod:`…novel_state` (the single accessor home)" — false on
  both halves, in the very module that performs the second-hop re-export.
  Verified against the tree: it is the only `:mod:` `novel_state` role with an
  ownership claim in `commands/`, and a plain `:mod:` role plus free prose
  carrying neither `_state_load` (Gate 1) nor an `._<…>error` suffix (Gate 2),
  so both existing gates are blind to it. Added Decision D10; added
  `_state_mutators.py:64-66` and the `state_sourcing.py` docstring import-home
  prose (formerly `_state_load.py:8-9/14/16`) to WI5 clean-up 1; added **Gate
  3** (the keyword pattern below)

  ```text
  novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)
  ```

  over `commands/` plus an enumerate-and-eyeball backstop that inventories
  every residual `novel_state` prose mention in `commands/` and confirms each
  is a genuine command-surface reference. The kept set (`_state_mutators.py:6`,
  `_chapter_plan_entry.py:6/9`, `_gate_drafting_mutators.py:11/349/353`,
  `novel.py:82/86`, and the `state_sourcing.py` cycle-rule sentence) is pinned
  in WI5 Stage F. Updated the Risks section, the Progress WI5 bullet, the
  Concrete steps for WI5/WI6, and the structural-acceptance criteria. Also
  actioned advisory **A1**: added the `grep -rn '_load_or_state_error'`
  insurance grep (must return nothing everywhere after the public rename) to
  the WI5 and WI6 gate blocks, so a retained-underscore role that Gate 2 would
  pass cannot rot silently. Recorded Wafflecat's round-4 structural-import-gate
  alternative as a 7.3.6 improvement (B7 is a comment defect, so the prose gate
  is the correct fix here, not an import-graph walk).

## Addenda

Lightweight, post-completion corrections folded onto this task. Each is a small,
surgical fix run as a no-plan, no-review pass; none changes the task's outcome.

- [x] A2 (from review:7.3.1; trivial). Prefer symbol citations over source
  line-number ranges in the two surviving docstring citations. The
  `resolved_working_dir` docstring at `state_sourcing.py:74` and the
  `main`-multiplexer docstring at `novel.py:153` both cite the cwd-relative rule
  as the line range `state_sourcing.py:52-67`; any header edit or reflow can
  silently invalidate the range and no test guards it — the same drift class
  that broke the design-doc citation in fix round 1. Re-anchor both citations to
  the stable symbol (`working_dir` / `WORKING_DIR_NAME`, or the cwd-relative
  rule by name) so they survive renames and reflows. Doc-only; no behaviour
  change. Scope: `novel_ralph_skill/commands/state_sourcing.py` (docstring at
  `resolved_working_dir`) and `novel_ralph_skill/commands/novel.py` (docstring
  at `main`).

- [x] A3 (from review:7.3.1; low). Correct Decision D9's Gate-2 wording in this
  execplan record. D9 (and its WI5 narrative) lists `load_or_state_error` inside
  the Gate-2 alternation and asserts Gate 2 "catches" the
  `novel_state.load_or_state_error` re-export role, but the gate as implemented
  is `novel_state\._[a-z_]*error` (Stage F, the gate block): the `\._` anchor
  matches only the dot-underscore form `novel_state._load_or_state_error`, never
  the bare public `novel_state.load_or_state_error` (a `.l`, not `._`). The
  bare-public façade role is in fact guarded by the A1 insurance grep
  (`_load_or_state_error` must return nothing), not by Gate 2. Correct the D9
  prose to state that Gate 2 matches the dot-underscore `._<…>error` forms only
  and that A1 closes the `load_or_state_error` gap, keeping the historical record
  precise. Doc-only; no gate semantics change. Scope: this execplan's Decision
  D9.
