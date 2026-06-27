# Logisphere design review — roadmap 7.3.6, round 1

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Subject: `docs/execplans/roadmap-7-3-6.md` (DRAFT).
Verdict: **PROCEED WITH CONDITIONS** — the design is structurally sound and
behaviour-neutral, but two accuracy defects must be fixed before implementation.

## What was verified against real source

- `commands/names.py` — confirmed it owns `MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`,
  `ENVELOPE_COMMAND_NAMES` (verbatim values match the plan), plus `NOVEL_MODULE`,
  `_MULTIPLEXER_ENTRY_POINT`, `project_scripts_table()`. The vocabulary/binding
  split (Decision D1) is real and clean. `commands/names.py` imports nothing from
  `contract` today — so the re-export the plan adds does not create a cycle.
- `contract/envelope.py:19` — confirmed the sole production `contract -> commands`
  edge: `from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES`. The
  plan's "line 19" is correct.
- `contract/__init__.py` — confirmed the re-export surface and `__all__`; adding
  `WORKING_DIR_NAME` is mechanical.
- `commands/state_sourcing.py:56` — confirmed `WORKING_DIR_NAME = "working"` lives
  here (not in `novel_state.py`), exactly as the plan's Surprises note records.
- `tests/test_contract_layering.py` — confirmed the reusable `ast` helpers
  (`_module_scope_imports`, `_resolve_import_from`, `_resolve_dynamic_import`)
  exist and are sound. `_read_seam_source` is hard-wired to a single module
  (`find_spec(_SEAM_MODULE)`); widening to the whole package needs a
  `pkgutil.iter_modules` loop — feasible, the plan acknowledges it.
- Consumer enumeration — the plan's consumer lists match `grep`; one production
  importer of `ENVELOPE_COMMAND_NAMES` (envelope.py), the rest are tests.
  `tests/conftest.py` no longer imports `commands.names` (the 1.3.1.2 record's
  mention of conftest is stale but harmless).
- No cuprum / Cyclopts / uv / pytest-timeout behavioural claim is load-bearing.
  Decision D0 is correct: this is a pure module-home relocation. cuprum
  (`/data/leynos/Projects/cuprum`) is not touched. No external-doc citation is
  needed because no external behaviour is asserted.

## Findings

### BLOCKING

1. **The gate composition is stated wrongly; following the plan literally skips
   `make audit` on WI1–WI3.** Concrete-steps line ~534 asserts "Each `make all`
   runs `make check-fmt`, `make lint`, `make typecheck`, `make test`, and
   `make audit`." The Makefile defines `all: build check-fmt lint typecheck test`
   — **`audit` is NOT in `all`.** AGENTS.md §"Change quality and committing"
   requires `make audit` (pip-audit) as a separate gate before *every* commit.
   WI1, WI2, WI3 each commit but only invoke `make all`, so the plan as written
   omits the audit gate on three of four commits. Fix: state the true `all`
   composition and add an explicit `make audit` (and, where markdown changes,
   `make markdownlint` / `make nixie`) to each work item's Validation, not only
   WI4's. (Pandalump / Doggylump.)

2. **WI3's "stash to prove the guard red" recipe is unsafe as written and can
   silently prove nothing.** Concrete-steps step 5 says `git stash` then run the
   guard expecting FAIL, then `git stash pop`. By that point in WI3 the
   `envelope.py` edit and the widened-guard edit are *both* unstaged, so a blanket
   `git stash` removes the widened guard too — running the OLD guard (which only
   covers `runner.py`) against the un-edited `envelope.py` passes, falsely
   "disproving" the red. The red/green demonstration is a stated acceptance
   criterion (Validation §"No inversion"), so a recipe that can't actually show
   red is a defect. Fix: pin the demonstration to the *new* guard against the
   *old* `envelope.py` only — e.g. land the widened guard first and run it before
   editing `envelope.py`, or run the new guard against a stashed copy of just
   `envelope.py` (`git stash push -- novel_ralph_skill/contract/envelope.py`).
   Spell out the exact, file-scoped command. (Telefono / Doggylump.)

### ADVISORY (address if cheap; not blocking)

1. **Importing `commands.names` now transitively imports the whole `contract`
   package (and cyclopts).** After WI1, `commands/names.py` does
   `from novel_ralph_skill.contract.names import ...`, which executes
   `contract/__init__.py` first, which imports `contract.runner` (→ `cyclopts`).
   This is **not** a cycle (verified: nothing in the `contract` package imports
   `commands`), and it does not break the `novel`-import laziness guard
   (`tests/test_multiplexer_mount_table.py` concerns leaf *command* modules, and
   `novel` already pulls the contract package). But the developers-guide calls
   `names.py` a lightweight "leaf source-of-truth module"; after this change it
   is no longer dependency-free. The WI4 doc rewrite should say so honestly
   rather than re-describe it as a leaf. (Buzzy Bee / Dinolump.)

2. **`state_sourcing.py`'s docstring makes a hard import claim the plan softens.**
   The current module docstring states it "imports only from
   `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner` — never from
   `novel_state`". After WI2 it also imports from `novel_ralph_skill.contract.names`.
   The plan says "note the constant now originates in contract", but the
   *imports-only-from* sentence is a specific factual claim that must be
   *corrected*, not merely annotated. Make WI2 rewrite that sentence. (Telefono.)

3. **WI2 puts a directory name in a module called `names`.** Co-locating
   `WORKING_DIR_NAME` with the command-name vocabulary in `contract/names.py` is
   defensible (it is "naming data") but slightly muddies the module's single
   responsibility. The plan offers `contract/paths.py` as an alternative and
   defaults to `names.py` "to avoid a one-constant module". Acceptable, but record
   the decision in the Decision Log at implementation time as the plan already
   instructs, and ensure the `contract/names.py` docstring scopes itself to
   "contract-owned naming constants" rather than only "command-name vocabulary".
   (Wafflecat / Pandalump.)

4. **Identity assertions are the right neutrality proof — keep them.** The plan's
   `commands.names.SUBCOMMAND_NAMES is contract_names.SUBCOMMAND_NAMES` and the
   analogous `WORKING_DIR_NAME` identity checks are exactly what prevents a silent
   second copy. Good. No change; flagged so the implementer does not drop them
   under time pressure. (Telefono.)

## Pre-mortem (Doggylump)

- *Scenario A — the audit gate slips.* Six weeks later a `pip-audit` advisory
  fires on a transitive dep that was already vulnerable at 7.3.6 commit time but
  never run because WI1–WI3 only ran `make all`. Blast radius: a red `main` and
  a bisect that wrongly fingers 7.3.6. Prevention: BLOCKING finding 1 — run
  `make audit` per WI.
- *Scenario B — the layering guard is theatre.* The widened guard is committed
  but, because the red demonstration was botched (finding 2), it actually has a
  bug (e.g. it never reads `envelope.py`'s source, or `iter_modules` misses
  `__init__.py`) and would pass even with the inversion present. A later refactor
  re-introduces a `contract -> commands` import and CI stays green. Prevention:
  BLOCKING finding 2 — a real, file-scoped red/green proof against the *new*
  guard.
- *Scenario C — import-time surprise.* A future contributor adds a heavy import
  to `contract/runner.py`; because `commands.names` now drags in the whole
  contract package at import, an unrelated tool that only wanted the script-name
  table pays the cost. Low severity, but advisory 1's honest documentation is the
  cheap hedge.

## Alternatives checkpoint (Wafflecat)

Strongest alternative: **move the *entire* `names.py` into `contract`** and have
`commands` re-export, rather than splitting vocabulary from the `[project.scripts]`
binding. Trade: one fewer module, simpler mental model — but it parks a
`commands`-layer entry-point path string (`novel_ralph_skill.commands.novel:main`)
and the `[project.scripts]` derivation *inside* the contract package, recreating
the inversion in the opposite sense (contract naming a commands module). The plan
rejects this in Decision D1 for exactly that reason, and the rejection is correct.
A second alternative — leave the edge and only document it (the 1.3.1.2 status
quo) — is foreclosed by the roadmap success criterion that the edge be *removed*,
not re-documented. No superior alternative exists; the split design is on solid
ground.

## Conformance check

- ADR-003 layering rule (contract below commands): the plan *enforces* it; aligns.
- Deterministic/judgemental boundary: untouched (no CLI, envelope, or exit-code
  change). Aligns.
- Behaviour-neutrality: backed by identity tests + the unchanged e2e/snapshot
  suites. Sound.
- en-GB Oxford spelling: the plan demands it in docstrings/commits; no violations
  introduced by the plan text itself.
- Work items: atomic, ordered (WI1→WI2→WI3→WI4 with WI3 correctly depending on
  WI1), independently committable, each with named tests and a red/green claim.
  Complete against the roadmap 7.3.6 success criteria.

## Required changes before implementation

1. Correct the gate composition and add `make audit` (plus `make markdownlint` /
   `make nixie` where markdown changes) to the Validation of WI1, WI2, WI3 — not
   only WI4. (BLOCKING)
2. Replace the WI3 red/green recipe with a file-scoped demonstration that runs the
   *new/widened* guard against the *pre-edit* `envelope.py` and shows a genuine
   FAIL, then PASS after the edit. (BLOCKING)
3. (Advisory) In WI4, describe `commands/names.py` honestly post-change (no longer
   a dependency-free leaf); in WI2, *correct* the `state_sourcing.py`
   "imports only from … runner" docstring sentence; scope the `contract/names.py`
   docstring to contract-owned naming constants.
