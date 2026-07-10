# Relocate WORKING_DIR_NAME and the command-name vocabulary into the contract package

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (round 2 — round-1 blocking findings resolved)

## Purpose / big picture

Today two contract-level facts live in the wrong layer:

- The working-directory constant `WORKING_DIR_NAME = "working"` lives in the
  command-layer module `novel_ralph_skill/commands/state_sourcing.py`, even
  though it names the value the *contract* envelope stamps into every
  `working_dir` field.
- The envelope guard in `novel_ralph_skill/contract/envelope.py` reaches *up*
  into `novel_ralph_skill/commands/names.py` to import `ENVELOPE_COMMAND_NAMES`.
  That is a `contract` -> `commands` import — a layering inversion. Roadmap
  sub-task 1.3.1.2 audited this edge and declared it benign (a leaf
  source-of-truth module both layers may depend on), but it was never repaired.

After this change a reader can observe both repairs directly:

1. `python -c "import ast,pathlib;
   src=pathlib.Path('novel_ralph_skill/contract/envelope.py').read_text();
   print('commands' in {n for ...})"` — more practically, the new structural
   guard `tests/test_contract_names_home.py` passes, proving
   `contract/envelope.py` imports the command-name vocabulary from the
   `contract` package and imports no `commands` module at module scope.
2. `WORKING_DIR_NAME` is importable from the `contract` package
   (`from novel_ralph_skill.contract import WORKING_DIR_NAME`), and
   `state_sourcing.py` re-exports it by importing it *from* contract rather than
   defining it, so no command owns the constant.
3. Every existing suite — contract, command, registry, envelope, multiplexer,
   console-scripts e2e — stays green, proving the relocation is behaviour-neutral
   (the same names validate, the same `[project.scripts]` table is produced, the
   same envelopes render).

The win is a deliberate dependency direction: the `contract` package owns the
contract vocabulary it enforces, and the `contract` -> `commands` edge recorded
in 1.3.1.2 is removed.

This is a pure intra-package *relocation* refactor of Python module homes. It
changes no CLI surface, no envelope wire format, no exit code, and no
subprocess invocation. There is therefore **no cuprum, Cyclopts-behaviour,
`uv run`, or pytest-timeout claim load-bearing in this plan** (see Decision Log
D0 and the Risks section). The Cyclopts mounting behaviour the multiplexer
relies on is unchanged and already pinned by existing tests; this plan does not
touch it.

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- **No `contract` -> `commands` imports.** After this work, no module under
  `novel_ralph_skill/contract/` may import any `novel_ralph_skill.commands`
  module (at module scope or otherwise). This is the ADR-003 layering rule the
  task exists to enforce; it is already pinned for `contract/runner.py` by
  `tests/test_contract_layering.py` and must be extended to cover the names edge.
- **No `commands/names.py` -> `contract/` *cycle*.** `commands/names.py` legitimately
  carries the `[project.scripts]` binding (`NOVEL_MODULE`,
  `project_scripts_table`), whose target string names a `commands`-layer module.
  It may *consume* the relocated vocabulary by importing it from `contract`
  (that is the deliberate downward direction), but the relocation must not turn
  the consumer edge into a genuine import cycle. `contract` must not import
  `commands.names` back.
- **Behaviour-neutral.** The set of valid envelope command names, the
  `SUBCOMMAND_NAMES` tuple, the `[project.scripts]` table, the `working/`
  directory name, every rendered envelope, and every exit code are byte-for-byte
  unchanged. No public callable signature changes.
- **Public re-export surface preserved.** Symbols other modules and tests import
  today (`novel_ralph_skill.commands.names.SUBCOMMAND_NAMES`,
  `ENVELOPE_COMMAND_NAMES`, `MULTIPLEXER_NAME`, `project_scripts_table`,
  `NOVEL_MODULE`; `novel_ralph_skill.commands.state_sourcing.WORKING_DIR_NAME`)
  must keep importing from their current locations, via re-export, so no consumer
  outside the moved files needs editing for an import to resolve. (Consumers may
  additionally gain a contract-package import, but the existing paths must not
  break.)
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in every docstring, comment,
  test name, doc edit, and commit message (AGENTS.md "consistent spelling").
- **Do not edit the root/control worktree.** All work happens in the git-donkey
  worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-6`.

## Tolerances (exception triggers)

- **Scope:** if implementation requires editing more than 14 files or more than
  ~400 net lines, stop and escalate. (Expected: ~6 source files, ~5 test files,
  2 docs.)
- **Interface:** if any public callable *signature* must change (as opposed to a
  module home), stop and escalate. None is expected.
- **Dependencies:** if a new third-party dependency is required, stop and
  escalate. None is expected; this is intra-package.
- **Cycle:** if making `contract` own the vocabulary forces a real import cycle
  that cannot be broken by a re-export, stop and escalate with the cycle trace.
- **Iterations:** if `make all` still fails after 3 fix attempts on any work
  item, stop and escalate.
- **Ambiguity:** the split between "command-name vocabulary" (moves to contract)
  and "console-script binding" (stays in commands) is fixed by Decision Log D1.
  If review rejects that split, stop and re-plan rather than improvising a
  wholesale `names.py` move into contract.

## Risks

- Risk: A genuine import cycle if `contract.names` were to need anything from
  `commands`.
  Severity: high. Likelihood: low.
  Mitigation: The relocated vocabulary is *pure data* (string literals and a
  derived tuple) with no command dependency, exactly the property 1.3.1.2 relied
  on. `contract/names.py` will import nothing from `commands`. WI1 verifies this
  with a structural guard before any consumer is repointed.

- Risk: A consumer imports a vocabulary symbol from `commands.names` by a path
  the re-export does not preserve, breaking at import time.
  Severity: medium. Likelihood: low.
  Mitigation: WI1 keeps `commands/names.py` re-exporting every moved symbol from
  contract, and `grep` over the repo (recorded in Concrete steps) enumerates
  every consumer before the move. `make all` exercises every import.

- Risk: The `contract/__init__.py` re-export surface grows and a `__all__`
  drifts from the actual exports.
  Severity: low. Likelihood: medium.
  Mitigation: WI2 adds the new names to `contract/__init__.__all__` and a test
  asserts the package re-exports them; `ruff`/`ty` catch dangling names.

- Risk: The structural layering guard (`test_contract_layering.py`) only covers
  `contract/runner.py` today; the names edge could regress un-caught.
  Severity: medium. Likelihood: medium.
  Mitigation: WI3 widens the guard (or adds a sibling) to cover
  `contract/envelope.py` and the whole `contract` package, so a future
  `contract` -> `commands` import fails CI.

## Progress

- [x] WI1 — Create `contract/names.py` owning the command-name vocabulary; make
  `commands/names.py` re-export it; **and** repoint `contract/envelope.py` at
  `contract.names` (folded in per Decision D6 to avoid a transient import cycle).
  (completed: all; remaining: —)
- [x] WI2 — Relocate `WORKING_DIR_NAME` into the `contract` package
  (`contract/names.py`); re-export from `state_sourcing.py`; add to
  `contract/__init__`. Done: identity tests pin no second copy; the
  `state_sourcing.py` docstring's "imports only from … runner" sentence is
  rewritten to add `contract.names` while keeping the no-``novel_state`` rule.
- [x] WI3 — Widen the layering guard to the whole `contract` package and repoint
  the contract-suite test imports at `contract.names` (the `envelope.py` repoint
  itself landed in WI1 per Decision D6). Done: `test_contract_layering.py` now
  walks every contract module via `pkgutil`, asserts the walk is non-empty
  (round-2 pre-mortem A), and keeps the `runner.py` test as a focused special
  case; the red/green proof below confirms the widened guard FAILs against a
  pre-edit `envelope.py` and PASSes after the repoint. `test_contract_envelope.py`
  repoints both `ENVELOPE_COMMAND_NAMES` and `SUBCOMMAND_NAMES` at `contract.names`
  (round-2 advisory 2).
- [x] WI4 — Update the developers' guide and the 1.3.1.2 roadmap record; tick
  7.3.6. Done: the developers-guide layering note is rewritten to the repaired
  downward direction (and the registry-home reference at ~line 422 corrected to
  `contract/names.py`); the roadmap 1.3.1.2 sub-task gains an "Update (from
  7.3.6)" note recording the repair; 7.3.6 is ticked with a Done record mirroring
  the 7.3.5 style. `docs/contents.md` needs no change (no new doc added —
  `contract/names.py` is code).

## Surprises & discoveries

- Observation (WI1, BLOCKING during implementation): the planned WI decomposition
  is not achievable as four *independently* green commits. The moment
  `commands/names.py` imports the vocabulary *down* from `contract.names` (WI1),
  Python executes `contract/__init__.py`, which imports `contract.envelope`,
  which still imported `ENVELOPE_COMMAND_NAMES` *up* from `commands.names` (the
  inversion WI3 was scheduled to remove). That closes a genuine circular import:
  `commands.names` -> `contract` (package init) -> `contract.envelope` ->
  `commands.names` (partially initialized). It is masked in the in-process
  `pytest` run by import ordering but fails the fresh console-script import — the
  e2e suites (`test_console_scripts_e2e.py` et al.) went red with
  `ImportError: cannot import name 'ENVELOPE_COMMAND_NAMES' from partially
  initialized module … (most likely due to a circular import)`.
  Evidence: a fresh `uv pip install . && novel state` reproduced the traceback;
  reverting to pre-change `HEAD` ran `novel state` cleanly, and repointing
  `envelope.py` at `contract.names` fixed it.
  Impact (deviation): the `contract/envelope.py` repoint (WI3 Do step 1) is
  *atomically coupled* to the WI1 re-export and was therefore folded into WI1.
  WI1 now lands the vocabulary home, the `commands.names` re-export, **and** the
  `envelope.py` repoint together (the only edge set that leaves `make all`
  green). WI3 is reduced to widening the layering guard and repointing the
  contract-suite test imports — the structural hardening — with the envelope
  source already on its contract home. Recorded as Decision D6.

- Observation (WI3, red/green proof of the widened guard): because the
  `envelope.py` repoint landed in WI1 (Decision D6), the WI3 demonstration cannot
  use the planned `git restore … envelope.py` against HEAD (HEAD already imports
  `contract.names`). Instead the proof temporarily rewrote `envelope.py`'s import
  back to `commands.names` in the working tree, ran the **widened** guard
  (`test_contract_package_imports_no_commands_module`), and observed a genuine
  FAIL naming the offender:
  `{'novel_ralph_skill.contract.envelope': ['novel_ralph_skill.commands.names',
  'novel_ralph_skill.commands.names.ENVELOPE_COMMAND_NAMES']}`. Restoring the
  `contract.names` import made the guard PASS. This proves the widened guard is
  not vacuous (it also asserts the iterated module set is non-empty) and that the
  inversion is genuinely closed. No blanket `git stash` was used (the round-1
  hazard); the single offending file was edited and restored in place.

- Observation: The roadmap text for 7.3.6 says `WORKING_DIR_NAME` lives "in the
  `novel_state` command module", but task 7.3.1 already moved it to
  `novel_ralph_skill/commands/state_sourcing.py`.
  Evidence: `grep -rn WORKING_DIR_NAME novel_ralph_skill` shows the definition at
  `commands/state_sourcing.py:56`; `commands/novel_state.py` only mentions it in
  a docstring. The 7.3.1 execplan record (roadmap line 2867 ff.) confirms the
  carve-out.
  Impact: This plan relocates the constant from `state_sourcing.py` (its real
  current home), not from `novel_state.py`. The success intent is unchanged.

## Decision log

- Decision: D0 — Treat this as a behaviour-neutral module-home relocation with
  no external-library behavioural claim load-bearing.
  Rationale: The task moves *where* Python symbols are defined. It invokes no
  subprocess, so cuprum is not involved; it changes no CLI parsing, help, or
  version handling, so Cyclopts behaviour is unchanged and already pinned by the
  multiplexer/e2e suites; it adds no test-timing or resolution concern, so
  `uv run`/pytest-timeout semantics are irrelevant. Verifying these libraries
  against their docs would be busywork that proves nothing about this change.
  The load-bearing invariants here are *import-graph* facts, which are verified
  by in-repo `ast` structural tests, not by external-library research.
  Date/Author: 2026-06-27, planning agent.

- Decision: D1 — Split `names.py`: move the *vocabulary* to contract, keep the
  *console-script binding* in commands.
  Rationale: `commands/names.py` carries two distinct responsibilities. (a) The
  command-name vocabulary — `MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`,
  `ENVELOPE_COMMAND_NAMES` — is pure contract data the envelope guard enforces;
  the task explicitly relocates it to contract. (b) `NOVEL_MODULE` and
  `project_scripts_table()` bind console-script names to a `commands`-layer
  entry-point module path (`novel_ralph_skill.commands.novel:main`); that is a
  packaging concern that legitimately *references the commands layer* and must
  not move *into* contract (doing so would make contract name a commands module,
  re-creating the inversion in the opposite sense). So (a) moves to
  `contract/names.py`; (b) stays in `commands/names.py` and *consumes* the moved
  vocabulary from contract. This keeps each layer owning what it should and
  removes the inversion. The alternative — moving the whole `names.py` into
  contract — was rejected because it would put a commands-module path string and
  the `[project.scripts]` derivation inside the contract package.
  Date/Author: 2026-06-27, planning agent.

- Decision: D2 — Preserve every existing import path by re-export.
  Rationale: Many tests and modules import `SUBCOMMAND_NAMES`,
  `ENVELOPE_COMMAND_NAMES`, `MULTIPLEXER_NAME` from `commands.names`, and
  `WORKING_DIR_NAME` from `commands.state_sourcing`. Re-exporting the moved
  symbols from their old homes keeps the blast radius to the moved-and-repointed
  files plus the guards/docs, satisfies the "public re-export surface preserved"
  Constraint, and lets `make all` prove neutrality without a sweeping rename.
  Date/Author: 2026-06-27, planning agent.

- Decision: D3 — `make audit` is a separate commit gate, run per work item.
  Rationale: Verified against the Makefile (`all: build check-fmt lint typecheck
  test`, line 37) and AGENTS.md (Auditing via `make audit`/`pip-audit`, line
  80/92). `make all` does **not** include `audit`, so each commit (WI1-WI4) runs
  `make all` then `make audit`. The round-1 plan wrongly claimed `make all` ran
  `make audit`, which would have skipped the audit gate on three of four commits
  (round-1 BLOCKING finding 1). Corrected throughout (Concrete steps "Gate
  composition", each WI's Validation, the Validation and acceptance section).
  Date/Author: 2026-06-27, planning agent (round 2).

- Decision: D4 — Prove the widened layering guard red with a *file-scoped* revert
  of `envelope.py`, never a blanket `git stash`.
  Rationale: The red/green proof is an acceptance criterion. At the point of
  demonstration both the widened-guard edit and the `envelope.py` repoint are
  uncommitted; a blanket `git stash` removes the widened guard too, so the OLD
  (`runner.py`-only) guard runs against the un-repointed `envelope.py` and
  passes — proving nothing (round-1 BLOCKING finding 2). Instead, stage the
  widened guard, then `git restore --staged --worktree
  novel_ralph_skill/contract/envelope.py` to revert *only* that file, and run the
  new guard (expect FAIL), then re-apply the repoint (expect PASS). This pins the
  demonstration to the new guard against the pre-edit envelope.
  Date/Author: 2026-06-27, planning agent (round 2).

- Decision: D5 — Scope `contract/names.py` to "contract-owned naming constants",
  and correct the `state_sourcing.py` and developers-guide provenance claims.
  Rationale: `WORKING_DIR_NAME` (a directory name) co-locates with the
  command-name vocabulary in `contract/names.py` (WI2), so the module docstring
  is scoped to "naming constants" rather than narrowly "command-name vocabulary"
  (round-1 advisory 3). The `state_sourcing.py` "imports only from … runner —
  never from `novel_state`" sentence becomes factually wrong once it imports
  `contract.names`, so WI2 *rewrites* it (round-1 advisory 2). The
  developers-guide must stop calling `commands/names.py` a dependency-free leaf,
  since re-exporting from `contract.names` drags in the whole contract package
  transitively (round-1 advisory 1) — a downward, non-cyclic edge.
  Date/Author: 2026-06-27, planning agent (round 2).

- Decision: D6 — Fold the `contract/envelope.py` repoint into WI1 (it cannot be
  deferred to WI3 without a transient import cycle).
  Rationale: see the WI1 BLOCKING observation under Surprises & discoveries.
  Adding the `commands.names` -> `contract.names` re-export (WI1) while
  `contract.envelope` still imported *up* from `commands.names` (the inversion
  WI3 was to remove) forms a real circular import that breaks the fresh
  console-script import path (the e2e suites). The two edges are inseparable: you
  cannot make `commands.names` depend on `contract` without simultaneously
  removing the `contract.envelope` -> `commands.names` edge. So WI1 now performs
  the envelope repoint as well; WI3 keeps the structural-guard widening and the
  contract-suite test repoint. The four-commit shape and every Constraint are
  preserved — only the line that flips `envelope.py` moved one work item earlier.
  Date/Author: 2026-06-27, implementing agent.

- Decision: D7 — Place `WORKING_DIR_NAME` in `contract/names.py`, not a dedicated
  `contract/paths.py`.
  Rationale: the WI2 plan defaulted to co-locating the constant with the
  command-name vocabulary to avoid a one-constant module, and the
  `contract/names.py` docstring is already scoped to "contract-owned naming
  constants" (D5) so the addition needs no re-scoping. `WORKING_DIR_NAME` is a
  naming constant (a directory token the envelope stamps), so the home is
  coherent. Recorded here as the plan instructed.
  Date/Author: 2026-06-27, implementing agent.

## Outcomes & retrospective

All four work items landed as atomic commits, each green under `make all` and
`make audit`, with a clean `coderabbit review --agent` (0 findings) per work
item.

What was delivered:

- `novel_ralph_skill/contract/names.py` (new) owns the command-name vocabulary
  (`MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`, `ENVELOPE_COMMAND_NAMES`) and
  `WORKING_DIR_NAME`, importing nothing from `commands`.
- `commands/names.py` re-exports the vocabulary and keeps only the
  `[project.scripts]` binding; `state_sourcing.py` re-exports `WORKING_DIR_NAME`;
  `contract/__init__.py` re-exports `WORKING_DIR_NAME`. Every pre-existing import
  path resolves unchanged.
- `contract/envelope.py` validates `command` against
  `contract.names.ENVELOPE_COMMAND_NAMES` — the `contract`→`commands.names`
  inversion is gone.
- `tests/test_contract_layering.py` is widened to walk the whole `contract`
  package (non-empty assertion included) and was proven red against a pre-edit
  `envelope.py`, green after.
- The developers' guide and the roadmap (1.3.1.2 record + 7.3.6 tick) are
  squared.

Key deviation: the `envelope.py` repoint was folded into WI1 rather than WI3
(Decision D6), because adding the `commands.names`→`contract.names` re-export
while `envelope.py` still imported up from `commands.names` forms a real circular
import that breaks the fresh console-script import path. The two edges are
atomically coupled and cannot be split across commits. The four-commit shape and
every Constraint held.

Lesson for future relocations: when a lower layer is made to import *down* from
a package whose `__init__` transitively imports *up* into the moving module, the
two edges must flip in the *same* commit. An in-process `pytest` run can mask the
cycle by import ordering; the fresh console-script (e2e) path is the reliable
detector. Always exercise `uv pip install . && novel …` (or the e2e suite) before
trusting that a re-export is behaviour-neutral.

## Context and orientation

You are working in the Python package `novel_ralph_skill`, a Ralph-loop novel
harness whose deterministic commands share one output contract (ADR 003). Two
layers matter here:

- `novel_ralph_skill/contract/` — the shared interface contract: the JSON
  envelope (`contract/envelope.py`), exit codes (`contract/exit_codes.py`), the
  `run`/`drive` seam (`contract/runner.py`), and the package re-export surface
  (`contract/__init__.py`). This layer sits *below* commands and must not import
  from `commands` (ADR 003; developers-guide "Disambiguated exit codes" and the
  layering note at developers-guide.md lines ~603-614).
- `novel_ralph_skill/commands/` — the command slices. Relevant files:
  - `commands/names.py` — the single source of truth for console-script and
    subcommand names. Defines `NOVEL_MODULE`, `MULTIPLEXER_NAME`,
    `SUBCOMMAND_NAMES`, `ENVELOPE_COMMAND_NAMES`, and `project_scripts_table()`.
  - `commands/state_sourcing.py` — the neutral state-sourcing home (built by
    task 7.3.1). Defines `WORKING_DIR_NAME = "working"` and the `working_dir()`,
    `state_path()`, `resolved_working_dir()` accessors that read it.
  - `commands/novel.py` — the `novel` multiplexer; imports `MULTIPLEXER_NAME`,
    `SUBCOMMAND_NAMES` from `commands.names`.
  - `commands/_desloppify.py`, `commands/_wordcount.py` — import
    `WORKING_DIR_NAME` from `state_sourcing` (these are slated for 7.3.4 to route
    through the accessors instead; this plan does **not** change that — it only
    keeps their import resolving, repointing it to the re-export if needed).

Key term definitions:

- **Command-name vocabulary** — the set of names a command may carry in its
  envelope `command` field: the five spaced `novel <verb>` names
  (`SUBCOMMAND_NAMES`) plus the bare `"novel"` (`MULTIPLEXER_NAME`), unioned as
  `ENVELOPE_COMMAND_NAMES`. The envelope guard in `build_envelope` validates
  `command` against this set.
- **Layering inversion** — an import from a lower layer (`contract`) up into a
  higher layer (`commands`). `contract/envelope.py` importing
  `commands.names.ENVELOPE_COMMAND_NAMES` is exactly this; removing it is the
  task.
- **Re-export** — a module importing a symbol from its new home and listing it
  in `__all__` so existing consumers importing it from the old home keep working.

Current consumers (enumerate again at implementation time with `grep`):

- `ENVELOPE_COMMAND_NAMES`: `contract/envelope.py`,
  `tests/test_contract_envelope.py`,
  `tests/cross_command_contract/test_error_channels.py`,
  `tests/cross_command_contract/_identity_assertions.py`.
- `SUBCOMMAND_NAMES` / `MULTIPLEXER_NAME`: `commands/novel.py` and ~8 test
  modules.
- `WORKING_DIR_NAME`: `commands/state_sourcing.py` (def),
  `commands/_desloppify.py`, `commands/_wordcount.py`,
  `tests/multiplexer_support.py`, `tests/test_state_sourcing_home.py`.

Design and standards this plan implements (cite these in each work item and in
commit bodies):

- `docs/novel-ralph-harness-design.md` §3.1 (the shared envelope, the
  `command`/`working_dir` fields) and §4 (the command surface and its layering).
- `docs/adr-003-shared-interface-contract.md` (the contract is owned by the
  `contract` package; the four-flag construction contract and the
  envelope-version vocabulary).
- `docs/developers-guide.md` lines ~603-614 (the `contract` ->
  `commands.names` edge note from 1.3.1.2) and the "Disambiguated exit codes"
  section.
- `docs/roadmap.md` task 7.3.6 (success criteria), sub-task 1.3.1.2 (the edge
  record to update), and task 7.3.1 (the state-sourcing home that owns
  `WORKING_DIR_NAME` today).
- `AGENTS.md` — quality gates, the testing rules, the en-GB convention.
- `docs/scripting-standards.md` — Python style for any touched code.

## Plan of work

Four ordered, independently committable work items. Each ends with `make all`
green and is a single atomic commit. WI1 establishes the contract vocabulary
home and proves no cycle; WI2 moves the constant the same way; WI3 removes the
actual inversion in `envelope.py` and hardens the guard; WI4 squares the docs
and the roadmap.

The order is deliberate: WI3 (the inversion removal) depends on the vocabulary
already living in contract (WI1), and WI4 documents the finished state.

### WI1 — Stand up `contract/names.py` and re-export from `commands/names.py`

**Implements:** roadmap 7.3.6 success criterion "the command-name vocabulary
lives in the `contract` package"; ADR 003 (contract owns the contract
vocabulary); design §3.1/§4.

**Read first:** `docs/adr-003-shared-interface-contract.md`;
`docs/novel-ralph-harness-design.md` §3.1 and §4; `commands/names.py` in full;
`docs/developers-guide.md` lines ~603-614.

**Skills to load:** `python-router` (route to `python-data-shapes` for the
constant/tuple home and `python-types-and-apis` for the module's public surface;
`python-testing` for the structural test). Use `leta show` / `leta refs` to
navigate, not ad-hoc grep, when inspecting symbols.

**Do:**

1. Create `novel_ralph_skill/contract/names.py`. Move the vocabulary
   definitions verbatim from `commands/names.py`: `MULTIPLEXER_NAME`,
   `SUBCOMMAND_NAMES`, `ENVELOPE_COMMAND_NAMES` (and its de-dup derivation).
   Give the module a docstring scoping it to **contract-owned naming
   constants** (the command-name vocabulary the envelope guard validates
   against now, and `WORKING_DIR_NAME` once WI2 lands it here), citing ADR 003
   and 7.3.6 — phrase the scope as "naming constants", not narrowly "command-name
   vocabulary", so WI2's addition does not require re-scoping the docstring
   (round-1 advisory finding 3). At WI1 `__all__` lists exactly these three
   names (WI2 appends `WORKING_DIR_NAME`). It imports nothing from `commands`.
2. In `commands/names.py`, delete the moved definitions and replace them with a
   re-export: `from novel_ralph_skill.contract.names import (MULTIPLEXER_NAME,
   SUBCOMMAND_NAMES, ENVELOPE_COMMAND_NAMES)`, and add these three to its
   `__all__` (add an `__all__` if absent). Keep `NOVEL_MODULE`,
   `_MULTIPLEXER_ENTRY_POINT`, and `project_scripts_table()` here — they are the
   console-script binding (Decision D1) — but have `project_scripts_table()`
   consume `MULTIPLEXER_NAME` from the re-export. Update the module docstring to
   record the split: vocabulary now lives in `contract.names`; this module owns
   the `[project.scripts]` binding and re-exports the vocabulary for back-compat.

**Tests (add/update):**

- New `tests/test_contract_names_home.py` (unit + structural):
  - `test_vocabulary_imports_from_contract_names` — the three names import from
    `novel_ralph_skill.contract.names` and have their pinned values
    (`MULTIPLEXER_NAME == "novel"`; `SUBCOMMAND_NAMES` is the five spaced names;
    `ENVELOPE_COMMAND_NAMES` is those five plus `"novel"`, de-duped,
    first-seen-order).
  - `test_contract_names_imports_no_commands_module` — parse
    `contract/names.py` with `ast` (module-scope import walk, reusing the pattern
    in `tests/test_contract_layering.py` / `tests/_state_layout_scanner.py`) and
    assert no `novel_ralph_skill.commands` import. This pins the no-cycle
    Constraint.
- Update `tests/test_command_names_registry.py` and
  `tests/test_pyproject_scripts.py`: these import from `commands.names`; the
  re-export keeps them resolving. Add one assertion that
  `commands.names.SUBCOMMAND_NAMES is contract_names.SUBCOMMAND_NAMES` (identity)
  so the re-export cannot silently fork into a second copy.
- Existing `tests/test_contract_envelope.py`, `tests/test_multiplexer_dispatch.py`,
  the cross-command contract suite, etc. must stay green unchanged (they import
  via `commands.names`, preserved by the re-export). Do not edit them in WI1.

**Validation:** `make all`, then `make audit` (both must pass before the
commit; `make all` does *not* include `audit` — see "Gate composition" in
Concrete steps, AGENTS.md line 80/92). Expect the new
`tests/test_contract_names_home.py` tests to fail before step 1-2 (module
absent) and pass after.

### WI2 — Relocate `WORKING_DIR_NAME` into the contract package

**Implements:** roadmap 7.3.6 success criterion "`WORKING_DIR_NAME` lives in the
`contract` package … no command depends on a sibling command module for the
working-dir name"; design §3.1 (the `working_dir` envelope field); ADR 003.

**Read first:** `commands/state_sourcing.py` (its docstring explicitly states the
no-`novel_state`-import constraint and the `working/` ownership);
`docs/novel-ralph-harness-design.md` §3.1; `contract/__init__.py`.

**Skills to load:** `python-router` -> `python-data-shapes` (where the constant
lives) and `python-testing`. Consider `arch-crate-design`'s reasoning on
public-vs-internal homes by analogy (Python package layering), but the Python
routers are primary.

**Do:**

1. Add `WORKING_DIR_NAME = "working"` to the contract package. Place it in
   `contract/names.py` (it is contract-level *naming* data, co-located with the
   command-name vocabulary) or, if review prefers, a dedicated
   `contract/paths.py`; default to `contract/names.py` to avoid a one-constant
   module (record the choice in Decision Log when implementing). Carry the
   existing docstring (the cwd-relative `working/` rule, design line 151,
   Decision Log B4/B5 reference) onto it.
2. Re-export it from `contract/__init__.py`: add to the imports and to
   `__all__`, and extend the package docstring's "public surface" sentence.
3. In `commands/state_sourcing.py`, delete the local definition and import it
   from contract: `from novel_ralph_skill.contract.names import WORKING_DIR_NAME`
   (this is the same downward direction the module already uses for
   `contract.runner.StateInputError`, so it does not violate the module's
   no-`novel_state`-import rule). Keep `WORKING_DIR_NAME` in
   `state_sourcing.__all__` so `_desloppify`, `_wordcount`,
   `tests/multiplexer_support.py`, and `tests/test_state_sourcing_home.py` keep
   importing it from `state_sourcing` unchanged (re-export, Decision D2).
   **Correct** the module docstring's import-provenance sentence: it currently
   states the module "imports only from `novel_ralph_skill.state` and
   `novel_ralph_skill.contract.runner` — never from `novel_state`". After this
   change the module also imports `WORKING_DIR_NAME` from
   `novel_ralph_skill.contract.names`, so that sentence is now factually wrong
   and must be rewritten (not merely annotated) to add `contract.names` to the
   allowed-imports list while preserving the "never from `novel_state`"
   guarantee. State that the constant now originates in contract and is
   re-exported here. (Round-1 advisory finding 2.)

**Tests (add/update):**

- Extend `tests/test_contract_names_home.py`:
  - `test_working_dir_name_imports_from_contract` —
    `from novel_ralph_skill.contract import WORKING_DIR_NAME` and
    `from novel_ralph_skill.contract.names import WORKING_DIR_NAME` both resolve
    to `"working"`.
  - `test_state_sourcing_reexports_contract_working_dir_name` —
    `state_sourcing.WORKING_DIR_NAME is contract_names.WORKING_DIR_NAME`
    (identity), proving no second copy.
- `tests/test_state_sourcing_home.py` already asserts `WORKING_DIR_NAME` is in
  `state_sourcing.__all__` and equals `"working"`; keep it green (the re-export
  satisfies it). Add a one-line assertion there that the symbol is now sourced
  from contract (identity check against `contract.names`), or fold that into the
  new home test — pick one to avoid duplication.

**Validation:** `make all`, then `make audit` (both must pass before the
commit; `make all` excludes `audit` — see "Gate composition", AGENTS.md
line 80/92). The `state_sourcing` and multiplexer-support imports must still
resolve; the envelope `working_dir` field must be unchanged (the multiplexer/e2e
suites prove this).

### WI3 — Remove the inversion in `envelope.py` and harden the layering guard

**Implements:** roadmap 7.3.6 success criteria "`contract/envelope.py` validates
`command` against a contract-owned name set with no import of `commands.names`"
and "the `contract` -> `commands` edge documented in 1.3.1.2 is removed"; ADR
003 layering rule.

**Read first:** `contract/envelope.py` (the `build_envelope` guard);
`tests/test_contract_layering.py` (the existing `ast` module-scope import walk —
reuse its helpers, do not re-invent them); `docs/adr-003-shared-interface-contract.md`.

**Skills to load:** `python-router` -> `python-testing` (the structural `ast`
guard is the crux). Use `leta refs ENVELOPE_COMMAND_NAMES` to confirm the only
production importer is `envelope.py` before repointing.

**Do:**

1. In `contract/envelope.py`, change the import on line 19 from
   `from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES` to
   `from novel_ralph_skill.contract.names import ENVELOPE_COMMAND_NAMES`. Update
   the `build_envelope` docstring cross-reference (currently
   `:data:`novel_ralph_skill.commands.names.ENVELOPE_COMMAND_NAMES``) to the
   contract path. No logic changes.
2. Widen the layering guard. Either generalize `tests/test_contract_layering.py`
   so its `_module_scope_imports` walk runs over *every* module in the
   `novel_ralph_skill.contract` package (iterate the package's `.py` files via
   `importlib`/`pkgutil`, reusing the existing `_read_*_source` and
   `_module_scope_imports` helpers) and asserts none imports a
   `novel_ralph_skill.commands` module; or add a sibling test
   `tests/test_contract_envelope.py::test_envelope_imports_no_commands_module`.
   Prefer widening the existing guard to the whole package so the inversion class
   is closed for good (record the choice in the Decision Log). Keep the existing
   `runner.py` assertion intact (it may become a special case of the package-wide
   walk).

**Tests (add/update):**

- The widened/sibling structural guard described above. Phrase it so the
  **widened guard fails against the pre-edit `envelope.py`** (which still
  imports `commands.names`) and **passes after the repoint** — capture this
  red/green in the Progress notes, demonstrating it with the file-scoped
  `git restore … envelope.py` sequence in this WI's Validation (never a blanket
  `git stash`, which would also remove the widened guard and falsely show green).
- `tests/test_contract_envelope.py` parametrizes over `ENVELOPE_COMMAND_NAMES`
  imported from `commands.names`; leave that import (it still resolves via the
  re-export) or repoint it at `contract.names` — repoint it, since this is the
  contract suite and should consume the contract home directly. Either way it
  stays green.

**Validation:** `make all`, then `make audit` (both must pass before the
commit; `make all` excludes `audit` — see "Gate composition", AGENTS.md
line 80/92). The contract, envelope, and cross-command contract suites must
pass. The new guard must be demonstrably red against the *pre-edit*
`envelope.py` and green after the repoint — do this with the file-scoped
sequence below, which lands the widened guard first and isolates only
`envelope.py` from the stash so the new guard, not the old one, is exercised.

Red/green proof (run from the worktree root). The key is that the **widened
guard is already on disk and staged** before `envelope.py` is reverted, so the
file-scoped stash removes *only* `envelope.py` and the new guard runs against
the un-repointed file:

    # 1. Land the widened guard (Do step 2) and the envelope.py repoint
    #    (Do step 1), then stage everything so the guard edit is protected:
    git add -A

    # 2. Pop ONLY envelope.py back to its pre-edit (commands.names) state,
    #    leaving the widened guard staged and intact:
    git restore --staged --worktree novel_ralph_skill/contract/envelope.py
    #    (envelope.py now imports commands.names again; the widened guard is
    #     still present because it was a different file.)

    # 3. Run the NEW/widened guard against the PRE-edit envelope.py — expect FAIL
    #    (envelope.py imports commands.names, which the widened guard forbids):
    uv run python -m pytest tests/test_contract_layering.py -q   # expect FAIL

    # 4. Re-apply the envelope.py repoint (Do step 1) and re-run — expect PASS:
    #    re-edit envelope.py to import from contract.names, then:
    uv run python -m pytest tests/test_contract_layering.py -q   # expect PASS

Note: a *blanket* `git stash` is forbidden here — it would remove the widened
guard as well, leaving only the old `runner.py`-scoped guard, which passes
against the un-repointed `envelope.py` and proves nothing (round-1 BLOCKING
finding 2). The file-scoped `git restore … envelope.py` above guarantees the
*new* guard is the one under test.

### WI4 — Square the developers' guide and the roadmap record

**Implements:** AGENTS.md "keep docs current"; closes roadmap 7.3.6 and updates
the 1.3.1.2 record whose benign edge this work removes.

**Read first:** `docs/developers-guide.md` lines ~595-614; `docs/roadmap.md`
sub-task 1.3.1.2 and task 7.3.6; `docs/contents.md` (the docs index — confirm no
new doc needs indexing).

**Skills to load:** `en-gb-oxendict` (spelling of the prose edits);
`python-router` not needed (docs only).

**Do:**

1. In `docs/developers-guide.md`, rewrite the lines ~603-614 note. It currently
   says `contract/` imports `ENVELOPE_COMMAND_NAMES` *up* from
   `commands/names.py` and calls the edge deliberate-but-benign. Replace it with
   the new, repaired direction: the command-name vocabulary lives in
   `novel_ralph_skill/contract/names.py`; `contract/envelope.py` validates
   `command` against it with no `commands` import; `commands/names.py` re-exports
   the vocabulary and owns the `[project.scripts]` binding (which references the
   commands-layer entry-point module). State that the dependency now points
   downward only. Note `WORKING_DIR_NAME` likewise lives in the contract package
   and is re-exported from `state_sourcing.py`. **Describe `commands/names.py`
   honestly** (round-1 advisory finding 1): after this change it is no longer a
   dependency-free "leaf source-of-truth module" — re-exporting from
   `contract.names` means importing it now transitively executes
   `contract/__init__.py` (which pulls `contract.runner`, and thus `cyclopts`).
   Remove or qualify any "lightweight leaf" wording in the guide. This is a
   transitive *contract* import in the deliberate downward direction, **not** a
   cycle (nothing under `contract/` imports `commands`), and it does not affect
   the `novel`-import laziness guard.
2. In `docs/roadmap.md`, append a short note under sub-task 1.3.1.2 recording
   that 7.3.6 *repaired* (not merely documented) the edge it audited, and tick
   task 7.3.6 `[x]` with a one-paragraph "Done (see
   docs/execplans/roadmap-7-3-6.md)" record summarizing the relocation, the
   re-export back-compat, and the widened layering guard — mirroring the 7.3.5
   done-record style.
3. Update this ExecPlan's `Outcomes & retrospective` and `Progress`.

**Tests:** none (docs only), but the markdown gates apply.

**Validation:** `make markdownlint` and `make nixie` (no Mermaid is added, but
nixie is required for any markdown change per the task rules), then `make all`
and `make audit` (the audit gate is separate from `all` — AGENTS.md line 80/92)
to confirm nothing else regressed.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-6`.

1. Confirm the branch and a clean tree:

       git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-6 branch --show
       # expect: roadmap-7-3-6

2. Re-enumerate every consumer before moving anything (sanity against the
   Context list):

       grep -rn "ENVELOPE_COMMAND_NAMES\|SUBCOMMAND_NAMES\|MULTIPLEXER_NAME" --include='*.py' novel_ralph_skill tests
       grep -rn "WORKING_DIR_NAME" --include='*.py' novel_ralph_skill tests

3. WI1: create `contract/names.py`, edit `commands/names.py`, add
   `tests/test_contract_names_home.py`, then run both gates (`make all` does
   *not* include audit):

       make all
       make audit

   Expected tail: all suites pass, including the new home test, and `pip-audit`
   reports no actionable advisory. Commit:

       git add -A && git commit  # message file per commit-message skill

4. WI2: add `WORKING_DIR_NAME` to contract, re-export from `state_sourcing.py`
   and `contract/__init__.py`, extend the home test, then `make all` followed by
   `make audit`; commit.

5. WI3: land the widened guard and the `envelope.py` repoint, then prove the new
   guard red against the *pre-edit* `envelope.py` with a **file-scoped** revert
   (a blanket `git stash` is forbidden — it would also remove the widened guard
   and falsely show green; round-1 BLOCKING finding 2):

       # widened guard + envelope.py repoint are both written, then staged:
       git add -A
       # revert ONLY envelope.py to its pre-edit (commands.names) state,
       # keeping the widened guard staged and on disk:
       git restore --staged --worktree novel_ralph_skill/contract/envelope.py
       uv run python -m pytest tests/test_contract_layering.py -q  # expect FAIL
       # re-apply the envelope.py repoint (re-edit it to import contract.names):
       uv run python -m pytest tests/test_contract_layering.py -q  # expect PASS

   Then run the commit gates and commit:

       make all
       make audit

6. WI4: edit `docs/developers-guide.md` and `docs/roadmap.md`, update this plan,
   then run the markdown gates plus the code gates:

       make markdownlint
       make nixie
       make all
       make audit

   Commit.

**Gate composition (verified against the Makefile and AGENTS.md).** `make all`
expands to `all: build check-fmt lint typecheck test` (Makefile line 37) — it
runs `make build`, `make check-fmt`, `make lint`, `make typecheck`, and
`make test`, but it does **not** run `make audit`. AGENTS.md §"Change quality
and committing" lists Auditing (`make audit`, which runs `pip-audit`,
AGENTS.md line 80/92) as a separate gate that every commit must pass. Therefore
**each commit (WI1, WI2, WI3, WI4) must run `make all` followed by an explicit
`make audit`** before committing; WI4 additionally runs `make markdownlint` and
`make nixie` for its markdown edits. Do not run gates in parallel — the build
cache rewards sequential runs.

## Validation and acceptance

Acceptance is behaviour a reviewer can verify:

- **Contract owns the vocabulary.**
  `uv run python -c "from novel_ralph_skill.contract.names import
  ENVELOPE_COMMAND_NAMES, SUBCOMMAND_NAMES, MULTIPLEXER_NAME, WORKING_DIR_NAME;
  print(ENVELOPE_COMMAND_NAMES, WORKING_DIR_NAME)"` prints the five spaced names
  plus `"novel"`, and `working`.
- **No inversion.** `tests/test_contract_layering.py` (widened) and
  `tests/test_contract_names_home.py::test_contract_names_imports_no_commands_module`
  pass; running the layering guard against the *pre-edit* `envelope.py` fails
  (demonstrated in Concrete steps step 5).
- **Back-compat preserved.** Every previously-passing suite stays green with no
  edit to its imports: contract, command, registry, envelope, multiplexer,
  cross-command contract, console-scripts e2e.
- **Behaviour-neutral.** The console-scripts e2e and envelope-snapshot suites
  pass unchanged, proving the `[project.scripts]` table, the rendered envelopes,
  and the `working_dir` field are byte-for-byte the same.

Quality criteria ("done"):

- Tests: `make test` green; the new home/guard tests fail before their target
  edit and pass after.
- Lint/typecheck/format: `make lint`, `make typecheck`, `make check-fmt` all
  clean — these run together via `make all` (`all: build check-fmt lint
  typecheck test`, Makefile line 37).
- Audit: `make audit` (`pip-audit`) clean — this is a **separate** gate, not
  part of `make all`, and must be run before every commit (AGENTS.md line
  80/92).
- Markdown: `make markdownlint` and `make nixie` clean for the WI4 doc edits.

Quality method: `make all` **and** `make audit` per work item before each
commit; the two markdown gates additionally on WI4.

## Idempotence and recovery

Every work item is a module-home move plus a re-export; re-running `make all` is
safe and side-effect-free. If a step half-lands (e.g. a moved symbol with a
broken re-export), `make test` fails loudly at import time; fix the re-export
and re-run. Nothing here writes outside the repo or mutates external state, so
recovery is `git restore`/`git checkout -- <file>` on the offending file. Commit
boundaries are the natural rollback points: each WI is a single revertable
commit.

## Artefacts and notes

The load-bearing diffs to capture in commit bodies:

- `contract/names.py` (new) — the relocated vocabulary, importing nothing from
  `commands`.
- `commands/names.py` — the re-export plus the surviving `[project.scripts]`
  binding.
- `contract/envelope.py` line 19 — the import flips from `commands.names` to
  `contract.names`.
- `tests/test_contract_layering.py` — the guard widened to the whole `contract`
  package.

## Interfaces and dependencies

At the end of this work the following must exist, with these exact homes and
public surfaces:

- `novel_ralph_skill/contract/names.py` defines and exports the following
  (Python), importing nothing from `novel_ralph_skill.commands`:

      # novel_ralph_skill/contract/names.py
      MULTIPLEXER_NAME: str             # "novel"
      SUBCOMMAND_NAMES: tuple[str, ...] # the five spaced "novel <verb>" names
      ENVELOPE_COMMAND_NAMES: tuple[str, ...]  # SUBCOMMAND_NAMES + ("novel",), de-duped
      WORKING_DIR_NAME: str             # "working"  (WI2)
      __all__ = [
          "ENVELOPE_COMMAND_NAMES",
          "MULTIPLEXER_NAME",
          "SUBCOMMAND_NAMES",
          "WORKING_DIR_NAME",
      ]

- `novel_ralph_skill/contract/__init__.py` re-exports `WORKING_DIR_NAME` (and
  optionally the vocabulary) and lists it in `__all__`.

- `novel_ralph_skill/commands/names.py` re-exports the vocabulary from
  `contract.names`, retains `NOVEL_MODULE`, `_MULTIPLEXER_ENTRY_POINT`, and
  `project_scripts_table() -> dict[str, str]` (unchanged signature), and lists
  the re-exported names in `__all__`.

- `novel_ralph_skill/commands/state_sourcing.py` imports `WORKING_DIR_NAME` from
  `contract.names` and keeps it in its own `__all__` (re-export); the accessors
  `working_dir() -> pathlib.Path`, `state_path() -> pathlib.Path`,
  `resolved_working_dir() -> pathlib.Path` keep their signatures.

- `novel_ralph_skill/contract/envelope.py` imports `ENVELOPE_COMMAND_NAMES` from
  `contract.names`; `build_envelope(...)` keeps its signature and its
  `ValueError`-on-unknown-command contract.

No third-party interface is involved; the only dependencies are intra-package
imports in the deliberate `commands -> contract` direction.

## Revision note

Initial draft (2026-06-27). Decomposes 7.3.6 into four atomic work items: WI1
stands up `contract/names.py` for the command-name vocabulary with a no-cycle
guard; WI2 relocates `WORKING_DIR_NAME` into the contract package; WI3 removes
the `contract/envelope.py` -> `commands.names` inversion and widens the layering
guard to the whole contract package; WI4 squares the developers' guide and the
roadmap (1.3.1.2 record + 7.3.6 tick). Recorded D0 (no external-library claim is
load-bearing — pure module-home relocation, so no cuprum/Cyclopts/uv research is
warranted), D1 (split the vocabulary into contract while the `[project.scripts]`
binding stays in commands), and D2 (preserve every existing import path by
re-export). No remaining undecided forks.

Round 2 (2026-06-27). Resolved both round-1 BLOCKING findings and folded in the
named advisories. (1) Corrected the gate composition: `make all` is `build
check-fmt lint typecheck test` and does **not** include `audit`; added an
explicit `make audit` to the Validation of WI1-WI4 and to the Concrete steps,
and recorded Decision D3. (2) Replaced the unsafe blanket-`git stash` red/green
recipe with a file-scoped `git restore --staged --worktree
novel_ralph_skill/contract/envelope.py` that proves the *widened* guard red
against the *pre-edit* `envelope.py`, recorded as Decision D4. Advisories: WI2
now *corrects* (not annotates) the `state_sourcing.py` "imports only from …
runner" docstring sentence; `contract/names.py` is scoped to "contract-owned
naming constants"; WI4 describes `commands/names.py` honestly as no longer a
dependency-free leaf (transitive contract import, not a cycle) — recorded as
Decision D5. No new undecided forks; no external-library claim is load-bearing
(D0 unchanged, confirmed by the round-1 reviewer).

## Addenda

Lightweight, post-completion corrections folded onto this task. Each is a small,
surgical fix run as a no-plan, no-review pass; none changes the task's outcome.

- [ ] A1 (from review:7.3.6; low). De-tense the now-complete forward-looking
  conditional in the `contract/names.py` docstring. The module retains a clause
  ("once roadmap task 7.3.6 WI2 lands it") that is now factually complete, so the
  shipped docstring reads as if the relocation were still pending. Re-word the
  clause to the settled present tense so the docstring describes the delivered
  state. Doc-only; no behaviour change. Scope:
  `novel_ralph_skill/contract/names.py` (module docstring). Mirrors roadmap
  sub-task 7.3.6.1.
