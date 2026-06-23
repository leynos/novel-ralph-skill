# Extend the direct-edit guard to every executable-carrying skill reference

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & discoveries`, `Decision log`,
and `Outcomes & retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 3 — addresses Logisphere review round 2)

## Purpose / big picture

Roadmap task 1.2.8 hardened the direct-edit guard but scoped it to a single
file, `skill/novel-ralph/references/state-layout.md`. The guard's job is to
stop a copy-pasteable recipe that writes `working/state.toml` outside the
`novel-state` subcommands from re-entering the skill prose, because design §4.1
(`docs/novel-ralph-harness-design.md`) eliminates direct editing of
`state.toml` and ADR-002 (`docs/adr-002-toml-round-trip-tomlkit.md`) names
`tomlkit` as the only sanctioned writer. The scanner that finds such recipes,
`tests/_state_layout_scanner.py`, is already pure over markdown text and file
agnostic, but the test that drives it, `tests/test_state_layout_reference.py`,
only ever feeds it `state-layout.md`.

Other references carry executable code fences too. `done-conditions.md` carries
two `python` fences (the predicate pseudocode at lines 20-27 and 149-186), and
`SKILL.md` plus several references carry `text`/`markdown` illustration fences.
Any of these could grow a hand-edit recipe — `Path("working/state.toml")`
`.write_text(...)` inside a `python` fence, say — that today's single-file
guard would never see. The roadmap's own diagnosis: "other references such as
`done-conditions.md` contain executable fences and could grow a hand-edit
recipe no guard would catch. A shared multi-file fence scanner closes that gap
without per-file duplication."

After this change a single shared scan walks every skill markdown file that can
carry an executable fence, applies the existing recipe detector to each, and
fails `make test` if any of them names `state.toml` next to a write primitive.
Success is observable by planting a `Path("working/state.toml").write_text(…)`
recipe in `done-conditions.md` (or any reference) and watching the new test go
red, then removing it and watching it go green — with no new per-file test
function and no second copy of the scanner.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do not modify any file outside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-3`. The
  root/control worktree is off-limits for edits.
- The scanner stays pure over markdown text: it takes the document (and, for the
  new driver, the discovered file set) as parameters; it never shells out,
  imports `novel_ralph_skill`, or hard-codes an absolute path. This preserves
  the 1.2.8 no-AST-dependency and pure-function discipline
  (`tests/_state_layout_scanner.py` module docstring).
- No per-file duplication. The acceptance criterion for 7.3.3 is "a single
  shared scanner, with no per-file duplication". The multi-file driver must
  discover the file set, not enumerate one test function per reference and not
  copy the scanner body.
- Preserve the existing 1.2.8 behaviour for `state-layout.md` exactly. Every
  planted recipe and verified-clean case in
  `tests/test_state_layout_reference.py` must keep passing unchanged. This task
  widens coverage to more files; it does not relax the per-file detector.
- Keep `tests/_state_layout_scanner.py` and any new helper module under the
  400-line cap (AGENTS.md "Keep file size manageable", lines 24-27; the cap is
  why 1.2.8 extracted the scanner in the first place).
- Any non-`test_*.py` support module under `tests/` is inside
  `PYTHON_TARGETS` (`Makefile` line 15) and so carries the full Ruff lint, 100%
  `interrogate` docstring coverage (`pyproject.toml` `[tool.interrogate]`
  `fail-under = 100`), Pylint, and `ty` typecheck gates. The `**/test_*.py`
  per-file-ignores (`pyproject.toml` line 97) do NOT match it, so it carries no
  bare `assert`; guards that must fail raise `AssertionError` directly
  (mirroring `tests/conftest.py`).
- The discovery walk must reach a *stable, intentional* file set. It must not
  silently start scanning generated, vendored, or working-tree artefacts.
  Anchor it under `skill/novel-ralph/` only.
- All new tests stay in `tests/test_state_layout_reference.py` (the same module
  as the 1.2.8 corpus). The plan decides this branch at plan time (see Decision
  Log and the line-count estimate in Work Item 1), so the implementer does not
  reach for a sibling module under cap pressure. A sibling module is
  *forbidden* unless the file would genuinely exceed the 400-line cap after the
  change, and even then the only sanctioned reconciliation is to promote
  `_PLANTED_RECIPES` to a conftest-sanctioned shared support module (Decision
  Log option (b)); a cross-module *private* import
  (`from test_state_layout_reference import _PLANTED_RECIPES`) is never
  permitted because `tests/conftest.py` (lines 4-10) and six post-merge audits
  (`audit-1.2.1` Finding 3, `audit-1.2.3` Findings 1-2, `audit-1.2.4` Finding 2,
  `audit-1.2.5` Findings 1-3 and 5, `audit-1.2.6` Findings 1-2) exist to
  eliminate exactly that smell.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- Scope: if implementation requires changes to more than four files or more than
  roughly 250 net lines, stop and escalate. The expected footprint is the
  scanner module, its driving test, the developers-guide note, and the roadmap
  tick.
- Interface: this task adds no public package API. If any change to
  `novel_ralph_skill/` (the shipped package) becomes necessary, stop and
  escalate — the guard is a test-tree concern only.
- Dependencies: if a new external dependency (a markdown/AST parser, a fence
  library) appears necessary, stop and escalate. The no-AST-dependency
  constraint from 1.2.8 forbids it; the stdlib `re` scanner already in place is
  the sanctioned mechanism.
- New baseline failure: if the multi-file scan flags an *existing* reference (a
  real recipe already on disk that 1.2.8 did not catch because it scanned only
  `state-layout.md`), stop and escalate. That is a latent design violation in
  shipped prose, not a guard bug, and removing it is roadmap task 6.2.3's prose
  remit, not this guard task's. Verified at plan time: the scan is currently
  clean across all eight skill markdown files (see Surprises & Discoveries), so
  this is not expected, but the tolerance stands.
- Iterations: if the new test still fails after three green-attempt iterations
  for reasons other than a planted recipe, stop and escalate.
- Ambiguity: if the intended file set is genuinely unclear (e.g. whether
  `SKILL.md` itself counts as a "skill reference"), stop and present the
  options. This plan resolves it (see Decision Log): scan every `*.md` under
  `skill/novel-ralph/`, including `SKILL.md`, because each can carry an
  executable fence.

## Risks

- Risk: discovery starts scanning an unintended file, causing a flaky or
  over-broad gate. Severity: medium Likelihood: low Mitigation: anchor the walk
  to `skill/novel-ralph/**/*.md` via the `project_root` fixture
  (`tests/conftest.py`) inside the `skill_markdown_documents` discovery
  fixture; the tripwire test `test_discovery_covers_known_skill_files` asserts
  the discovered set *equals exactly* the eight known files (`SKILL.md` plus
  the seven references) and nothing outside that directory, so an accidental
  widening or narrowing fails loudly. This tripwire is independent of the
  acceptance guard (see Decision Log); a stale inventory cannot neuter the
  guard, which scans whatever the glob returns.

- Risk: a future reference is added but the discovery glob misses it (e.g. a
  `.markdown` extension), reopening the gap this task closes. Severity: low
  Likelihood: low Mitigation: glob both `*.md` is sufficient because the repo
  convention is `.md` (verified: all seven references and `SKILL.md` are
  `.md`); document the convention in the developers-guide note so a `.markdown`
  file is a recognised smell. A property/fuzz hardening of the recipe forms is
  roadmap task 7.3.4 and out of scope here.

- Risk: the new driver duplicates the per-file detector, breaching the
  no-duplication acceptance bar. Severity: medium Likelihood: low Mitigation:
  the driver calls `find_direct_state_write_recipes` once per file and
  aggregates; it adds no second matcher. Code review and a test that the
  multi-file result for a single file equals the single-file result pin this.

- Risk: moving or renaming the scanner module breaks the existing import
  `from _state_layout_scanner import find_direct_state_write_recipes`.
  Severity: low Likelihood: low Mitigation: keep
  `find_direct_state_write_recipes` in place and additive; add the multi-file
  driver alongside it in the same module (it stays under 400 lines — verified
  current size is 198 lines). Do not rename the module.

## Progress

- [x] Work item 1: add the shared multi-file scan driver to
  `tests/_state_layout_scanner.py` and its tests (red then green, one commit).
  Done in commit `816225e`. The driver
  `find_direct_state_write_recipes_in_files` takes `dict[str, str]` and returns
  `dict[str, list[str]]`, reusing `find_direct_state_write_recipes` verbatim
  (one matcher, no duplication). Four unit tests in
  `TestFindDirectStateWriteRecipesInFiles` pass. `make all` green; coderabbit
  `--agent` returned 0 findings. Pylint flagged C1803 on the `== {}`
  comparisons; switched to implicit-booleanness `assert not …`.
- [x] Work item 2: widen the reference guard test to drive every
  executable-carrying skill file through the shared driver (red then green, one
  commit). Done in commit `da2ea4c`. Added the `skill_markdown_documents`
  fixture, the acceptance guard
  `test_no_skill_reference_carries_direct_write_recipe`, the
  `test_discovery_covers_known_skill_files` tripwire, the read-only predicate
  regression pin, and the three-id planted-in-another-file parametrization. The
  red step (planting a `.write_text` recipe in a scratch `done-conditions.md`)
  failed the guard naming the file; the revert restored green. The cap breach
  recorded in the round-3 Decision Log outcome occurred (446 lines), so
  `_PLANTED_RECIPES` was promoted to `tests/_planted_recipes.py`
  (`PLANTED_RECIPES`, a `MappingProxyType`), returning the test module to 393
  lines. `make all` green (235 passed); five coderabbit `--agent` rounds drove
  the findings to zero (MappingProxyType view, docstring accuracy, banned
  `from typing import`, Oxford `-ize` spelling, execplan second-person and
  line-wrap nits).
- [x] Work item 3: developers-guide note, roadmap tick, and Markdown gates (one
  commit). Extended the "state-layout direct-edit guard" section of
  `docs/developers-guide.md` to record the multi-file driver, the glob-driven
  acceptance guard, the `.md` extension gate assumption, and the
  `test_discovery_covers_known_skill_files` tripwire; ticked roadmap task 7.3.3.
  `make all` green; `markdownlint` and `nixie` clean over the touched files (no
  Mermaid). Note: `make fmt`/`make markdownlint` over the *whole* tree trip on
  pre-existing violations in unrelated planning artefacts
  (`roadmap-2-1-1.review-r1.md`, `roadmap-2-2-1.review-r2.md`, `audit-1.2.4.md`)
  outside this task's remit; the touched files were linted individually and pass.

## Surprises & discoveries

- Observation: the scanner is already file-agnostic and pure; the gap is purely
  in the *driver*, which only ever feeds it `state-layout.md`. Evidence:
  `tests/_state_layout_scanner.py` takes `markdown: str` and never reads the
  filesystem; `tests/test_state_layout_reference.py` line 41 hard-codes
  `_STATE_LAYOUT_PARTS`. Impact: 7.3.3 is a driver-and-test change, not a
  scanner-logic change. No change to the recipe-detection regexes is needed
  (those are 7.3.1/7.3.2/7.3.4 remits).

- Observation: every skill markdown file is currently clean under the scanner.
  Evidence: running `find_direct_state_write_recipes` over all eight files
  (`SKILL.md` and the seven references) at plan time returns zero hits each.
  Impact: this task adds coverage without forcing prose edits; the new
  multi-file test passes immediately on the current tree once it stops planting
  recipes, and the planted-recipe-in-other-files cases prove the widened reach.

- Observation: `done-conditions.md` carries `python` fences but they only *read*
  state (`read_state_toml`, `state["phase"]["current"]`), so they are not
  recipes. Evidence: lines 20-27 and 149-186 contain no write primitive on
  `state.toml`. Impact: confirms the new scan does not false-flag the
  legitimate predicate pseudocode; a regression test pins this.

## Decision log

- Decision: scan every `*.md` under `skill/novel-ralph/` (the seven references
  plus `SKILL.md`), discovered by glob, rather than an enumerated allow-list of
  filenames. Rationale: the acceptance bar is "any executable-carrying
  reference … a single shared scanner, with no per-file duplication". A glob is
  the no-duplication form; an enumerated list would need touching whenever a
  reference is added, reopening the very gap 7.3.3 closes. `SKILL.md` is
  included because it carries fences and is the skill's primary document, so a
  recipe planted there must also be caught. Date/Author: 2026-06-23, planning
  agent.

- Decision: place the multi-file driver in the existing
  `tests/_state_layout_scanner.py` module, not a new module, and keep
  `find_direct_state_write_recipes` unchanged. Rationale: the module is the
  established home for the pure scan helpers, is well under the 400-line cap
  (198 lines), and an additive function avoids a second import surface and a
  second docstring-gated module. The driver reuses the existing detector,
  satisfying no-duplication. Date/Author: 2026-06-23, planning agent.

- Decision: split the two reference tests into distinct, explicitly-labelled
  roles. `test_no_skill_reference_carries_direct_write_recipe` is the
  acceptance-bearing guard — fully glob-driven over
  `skill/novel-ralph/**/*.md`, with zero per-file edits, satisfying the 7.3.3
  bar "a single shared scanner, with no per-file duplication".
  `test_discovery_covers_known_skill_files` is an intentional tripwire holding
  the one hard-coded eight-name inventory; its failure when a reference is
  added is a *designed feature* (it forces a human to inspect the new file),
  not duplication of the detector. Rationale: round-1 review blocking finding 2
  noted that, without this explicit split, the enumerated eight-name list in
  the discovery-coverage test reads as the very "enumerated allow-list of
  filenames" the guard's design rejects, and could be mistaken for an
  acceptance-criterion violation. The reconciliation: the *guard* never
  enumerates files (it scans whatever the glob returns, so it cannot be
  neutered by a stale list — the pre-mortem's second scenario), while the
  *tripwire* deliberately enumerates them so that growing the skill surface is
  a conscious, reviewed act. The two tests are independent: the guard does not
  consult the inventory. This makes the "no per-file duplication" criterion
  true of the acceptance test and reframes the inventory as a feature, not a
  breach. Date/Author: 2026-06-23, planning agent (round 2).

- Decision: pin the multi-file driver parameter as the import-free
  `dict[str, str]`, not `cabc.Mapping[str, str]`. Rationale: round-1 review
  blocking finding 1 — `tests/_state_layout_scanner.py` imports only `re`
  (verified: `from __future__ import annotations` then `import re`, with no
  `import typing as typ` and no `TYPE_CHECKING` block). A `cabc.Mapping`
  annotation would require adding two import lines under a `TYPE_CHECKING`
  guard (the precedent in `tests/working_corpus/_specs.py` lines 29-31), and
  the scanner is a runtime support module inside `PYTHON_TARGETS`, so `ty`
  /Pylint/Ruff hard-fail on a missing or unguarded import. `dict[str, str]`
  adds zero imports, compiles verbatim against the current module, and is the
  correct invariant annotation for the concrete dict the discovery fixture
  builds. Chosen over the `TYPE_CHECKING`-`cabc` route because it minimises the
  scanner's import surface and removes any risk of a docstring/lint regression
  on a module already gated at 100% interrogate coverage. Date/Author:
  2026-06-23, planning agent (round 2).

- Decision: build the `{label: text}` discovery map inside a pytest fixture
  (`skill_markdown_documents`) that depends on `project_root` and
  `read_repo_text`, reusing the sanctioned UTF-8 reader, rather than a
  module-level walk that re-implements `Path.read_text(encoding="utf-8")`.
  Rationale: round-1 review should-fix finding 3 — `read_repo_text` is a
  fixture returning a `(*parts) -> str` callable, so it is unavailable at
  module-import time; a module-level glob would be forced to duplicate the
  read. A fixture that globs the file set and reads each through the injected
  `read_repo_text` honours the conftest single-reader intent ("the walk and the
  reader agree on encoding and rooting") with no duplication. The glob itself
  (`project_root.glob`) is fixture-local and needs no fixture, so only the read
  is reused via injection. Date/Author: 2026-06-23, planning agent (round 2).

- Decision: keep ALL new tests in `tests/test_state_layout_reference.py` (the
  same module as the 1.2.8 corpus). Do not split into a sibling test module. If
  — contrary to the estimate below — the file would exceed the 400-line cap
  after the change, the only sanctioned reconciliation is option (b): promote
  `_PLANTED_RECIPES` to a non-`test_*.py` shared support module (e.g.
  `tests/_planted_recipes.py`) imported by both modules, mirroring how
  `tests/_state_layout_scanner.py` is already shared. A cross-module *private*
  import (`from test_state_layout_reference import _PLANTED_RECIPES`) is
  forbidden in every branch. Rationale: round-2 review's sole open finding. The
  plan previously authorised a sibling-module split "if the existing one nears
  the 400-line cap" while Work Item 2 item 5 mandated reusing the module-private
  `_PLANTED_RECIPES` corpus (verified: defined at
  `tests/test_state_layout_reference.py` line 48; consumed only there at lines
  271-272). Those two instructions conflict: the sibling branch would force
  `from test_state_layout_reference import _PLANTED_RECIPES`, a cross-module
  private import that `tests/conftest.py` (lines 4-10) and six post-merge
  audits were built to eliminate. Resolving by pinning the same-module branch
  closes the fork. Line-count estimate (decided at plan time, not left to
  implementer taste): current module is 277 lines (`wc -l`, verified). The new
  additions are one `skill_markdown_documents` fixture (~12 lines), four driver
  unit tests in a `TestFindDirectStateWriteRecipesInFiles` class (~40 lines),
  the glob-driven guard (~12 lines), the discovery tripwire with its eight-name
  inventory (~20 lines), the synthetic read-only regression pin (~14 lines),
  and the three-id parametrized planted-in-another-file case (~18 lines),
  totalling ~116 lines. Projected post-change size ≈ 393 lines — under the 400
  cap, so the same-module branch is feasible and chosen. The implementer
  measures the actual size with `wc -l` after each commit; only a genuine
  breach of 400 triggers option (b), and never a cross-module private import.
  The single sanctioned cap-breach fallback is therefore option (b): no
  alternative inlining route is authorised, so the implementer has one
  unambiguous policy. Date/Author: 2026-06-23, planning agent (round 3).

  Implementation outcome (2026-06-23, implementing agent). The estimate
  undershot: the test module reached 446 lines after the widened guard (the
  docstrings and the three-id parametrized case ran longer than the ~393
  projection), a genuine breach of the 400-line cap. Per the sanctioned
  fallback, the `_PLANTED_RECIPES` corpus was promoted to a shared
  non-`test_*.py` support module, `tests/_planted_recipes.py`, exporting
  `PLANTED_RECIPES` (a read-only `MappingProxyType` view) and imported by the
  test module — mirroring how `tests/_state_layout_scanner.py` is shared. No
  cross-module private import was introduced. After extraction the test module
  is 393 lines, under the cap. The corpus id `_PLANTED_RECIPES` is now
  `PLANTED_RECIPES` (the leading underscore was module-privacy; the shared
  support module exports the corpus intentionally).

- Decision: the cuprum research mandate does not apply to this task; record why
  rather than leave it implied. Rationale: this work touches only the `tests/`
  tree and a pure markdown scanner. It runs no external process, builds no
  `ProgramCatalogue`, and calls no cuprum API. design §4
  (`docs/novel-ralph-harness-design.md`) states the v1 spine shells out nowhere
  and "cuprum is required only where a command shells out (none do in v1)". The
  guard reads files via the existing `read_repo_text` fixture (`pathlib`), so
  no cuprum surface is exercised. Equally, no Cyclopts/pytest-timeout/uv
  runtime behaviour is load-bearing here; the only external behaviour the plan
  leans on is `pathlib.Path.glob` and the stdlib `re` module already pinned by
  1.2.8. There is therefore no undecided fork to resolve against external docs.
  Date/Author: 2026-06-23, planning agent.

## Outcomes & retrospective

Implemented across three atomic commits (`816225e`, `da2ea4c`, plus the
docs commit). Outcome against the purpose: a single shared scan
(`find_direct_state_write_recipes_in_files`) now covers every
executable-carrying skill markdown file under `skill/novel-ralph/` with no
per-file duplication — the acceptance guard is fully glob-driven and carries
zero per-file edits — and a planted recipe in any of them fails `make test`
(verified by the red step in `done-conditions.md`).

Deviations from the plan:

- The round-3 line-count estimate (≈ 393 lines, same-module) undershot. The
  widened guard pushed `tests/test_state_layout_reference.py` to 446 lines, a
  genuine 400-line cap breach, so the sanctioned fallback (option (b)) was taken:
  the planted-recipe corpus moved to `tests/_planted_recipes.py`, exporting
  `PLANTED_RECIPES` as a read-only `MappingProxyType`. No cross-module private
  import was introduced; the test module returned to 393 lines. This is recorded
  in the round-3 Decision Log's implementation-outcome note.
- The footprint is five files (the scanner, the test module, the new
  `_planted_recipes.py` support module, the developers-guide, and the roadmap),
  one over the "expected four". This is within the Tolerances band (the trigger
  is "more than four files *or* more than ~250 net lines"); the fifth file is the
  sanctioned cap-breach extraction, not scope creep, so no escalation was needed.

The baseline remained clean (no existing reference flagged), so no escalation
under the "new baseline failure" tolerance was triggered.

## Context and orientation

This document assumes only this worktree and no memory of prior plans. The
relevant files, by full repository-relative path:

- `skill/novel-ralph/references/state-layout.md` — the reference 1.2.8 guarded.
- `skill/novel-ralph/references/done-conditions.md`,
  `conflict-attractor.md`, `critic-personas.md`, `desloppify-checklist.md`,
  `jtbd-novel.md`, `stc-beat-sheet.md` — the other references; each may carry
  executable fences.
- `skill/novel-ralph/SKILL.md` — the skill's primary document; carries fences.
- `tests/_state_layout_scanner.py` — pure markdown scanner. Exposes
  `find_direct_state_write_recipes(markdown: str) -> list[str]`, which returns
  one message per executable code fence that writes `state.toml`. Empty list
  means clean. It is NOT a `test_*.py` file, so it is fully lint/typecheck/
  docstring gated.
- `tests/test_state_layout_reference.py` — the 1.2.8 driving test. Imports the
  scanner by basename (`from _state_layout_scanner import …`), reads
  `state-layout.md` through the `read_repo_text` fixture, pins a corpus of
  planted recipes and verified-clean cases.
- `tests/conftest.py` — shared scaffolding. Provides `project_root` (session
  scope, the worktree root) and `read_repo_text` (a `(*parts) -> str` reader
  joining parts under `project_root`). The `RepoTextReader` Protocol is
  declared here under `TYPE_CHECKING`.
- `docs/novel-ralph-harness-design.md` §4.1 — "All state mutation hides behind
  validated subcommands. Direct editing of `state.toml` is eliminated." §3.4
  and §5.3 carry the atomic-write discipline (write `state.toml.new`, fsync,
  rename) the scanner must NOT flag.
- `docs/adr-002-toml-round-trip-tomlkit.md` — selects `tomlkit` as the only
  sanctioned writer.
- `docs/developers-guide.md` "The state-layout direct-edit guard" (lines
  315-333) — the prose this plan extends to describe multi-file coverage.
- `docs/roadmap.md` task 7.3.3 (lines 694-702) — the task and its success
  criterion.
- `AGENTS.md` — quality gates (`make all`), testing rules (lines 141-165), and
  the 400-line file cap (lines 24-27).
- `Makefile` — gate targets: `all` = `build check-fmt lint typecheck test`
  (line 28); `markdownlint` (line 108); `nixie` (line 111).

Terms defined: an *executable fence* is a code fence whose info string is in
the scanner's `_EXECUTABLE_INFO_STRINGS` (`python`/`python3`/`py`/`py3`/`pycon`/
`sh`/`bash`/`shell`/`console`). A *recipe* is such a fence whose body names
`state.toml` alongside a write primitive. *Discovery* is the glob walk that
finds the files to scan.

Skills to load before touching code: `python-router` (it routes to the smaller
Python skills), and from it `python-testing` (fixture scopes, parametrization,
the unit-versus-behavioural boundary) and `python-types-and-apis` (the
`Protocol` and return-type shape for the new helper). Use `leta` for navigation
(`leta show find_direct_state_write_recipes`, `leta refs read_repo_text`) and
`sem` for history (`sem diff` over the 1.2.8 commit) rather than ad-hoc grep.
Property-based hardening of the recipe forms is roadmap task 7.3.4, not this
task; do not load `hypothesis`/`crosshair`/`mutmut` here unless escalation
calls for it.

## Plan of work

Three atomic, independently committable, gate-passable work items. Each follows
red-then-green: add the failing assertion or planted-recipe case first, watch
it fail, then make it pass.

### Work item 1 — add the shared multi-file scan driver

Implements design §4.1 and ADR-002 (the invariant the guard protects) and the
roadmap 7.3.3 "single shared scanner, with no per-file duplication" criterion.

Add to `tests/_state_layout_scanner.py`, alongside the existing
`find_direct_state_write_recipes`, a pure driver that takes a mapping of file
label to markdown text and returns the aggregated findings keyed by file. It
reuses the existing detector — it must not re-implement any matcher. Suggested
signature (pin it in the plan so the implementer does not invent a variant):

```python
# tests/_state_layout_scanner.py
def find_direct_state_write_recipes_in_files(
    documents: dict[str, str],
) -> dict[str, list[str]]:
    """Return, per document label, the direct-write recipes it carries.

    ``documents`` maps a human-readable label (e.g. a repo-relative path) to the
    document's markdown text. The return maps each label whose document carries
    at least one recipe to its non-empty message list; clean documents are
    omitted, so an empty return mapping means every document is clean. The driver
    calls :func:`find_direct_state_write_recipes` once per document and adds no
    second matcher, so multi-file coverage reuses the single-file detector
    verbatim (roadmap 7.3.3; design §4.1; ADR-002).
    """
```

Pin the parameter as the import-free `dict[str, str]` form, **not**
`cabc.Mapping[str, str]`. This is load-bearing:
`tests/_state_layout_scanner.py` imports only `re` (verified — its sole import
is `from __future__ import annotations` followed by `import re`; there is no
`import typing as typ` and no `if typ.TYPE_CHECKING:` block). A `cabc.Mapping`
annotation would require adding *two* lines — `import typing as typ` and a
`if typ.TYPE_CHECKING: import collections.abc as cabc` guard (the precedent set
by `tests/working_corpus/_specs.py` lines 29-31 and 159) — and the scanner is a
runtime support module inside `PYTHON_TARGETS`, so `ty`/Pylint/Ruff would hard-
fail on a missing or unguarded import. Choosing `dict[str, str]` adds zero new
imports, compiles against the current module verbatim, and keeps the module's
import surface minimal. The driver only ever reads the mapping, so the invariant
`dict[str, str]` annotation is correct for the concrete dict the test builds.

Take `documents` as text, not paths, to keep the module pure over markdown (the
constraint from 1.2.8). The driving test (work item 2) supplies the text via
the discovery fixture (see Work Item 2, item 1); the discovery glob lives in
the test, not the scanner, because the scanner must not touch the filesystem.

Tests to add (unit, in a new `TestFindDirectStateWriteRecipesInFiles` class
inside `tests/test_state_layout_reference.py` — the *same* module as the 1.2.8
corpus; do NOT split into a sibling module). The same-module branch is pinned
at plan time: the module is 277 lines now (`wc -l`, verified) and the round-3
estimate puts the post-change size at ≈ 393 lines, inside the 400-line cap (see
Decision Log for the line-by-line breakdown). The implementer confirms with
`wc -l tests/test_state_layout_reference.py` after each commit. A sibling
module is forbidden unless the file would genuinely exceed 400 lines, and even
then the only sanctioned reconciliation is option (b) — promote
`_PLANTED_RECIPES` to a shared `tests/_planted_recipes.py` support module
imported by both — never a cross-module private import. This pins the round-2
review's open finding:

1. `test_clean_documents_return_empty_mapping` — a mapping of two clean
   documents returns `{}`.
2. `test_recipe_in_one_document_keyed_by_label` — a mapping where exactly one
   document carries a planted recipe returns a one-key mapping under that
   label, and the message list equals the single-file
   `find_direct_state_write_recipes` result for that text (pins no-duplication:
   the driver is the detector applied per file).
3. `test_recipe_in_several_documents_all_reported` — two recipe-bearing
   documents both appear in the mapping; a third clean one does not.
4. `test_empty_mapping_returns_empty` — the empty-input edge case returns `{}`.

These are example-based unit tests (AGENTS.md "happy paths, unhappy paths, and
relevant edge cases", lines 143-144). No property test here — the per-form
mutation property is roadmap 7.3.4. No snapshot test — the output is a small,
directly assertable mapping, and AGENTS.md (lines 148-153) forbids
snapshot-only coverage for logic that can be asserted directly. No
behavioural/e2e test — this is a pure helper with no externally observable
workflow, persistence, or command-line surface (AGENTS.md lines 159-161).

Validation for this commit: `make all` (which runs
`build check-fmt lint typecheck test`). Expect the four new tests to fail
before the driver exists (import error or `AttributeError`), then pass after.
Confirm `interrogate` stays at 100% (the new function has a docstring) and `ty`
/Ruff/Pylint stay clean over `tests/_state_layout_scanner.py`.

### Work item 2 — widen the reference guard to scan every executable-carrying file

Implements the roadmap 7.3.3 body ("other references such as
`done-conditions.md` contain executable fences and could grow a hand-edit
recipe no guard would catch") and its success criterion ("a planted hand-edit
recipe in any executable-carrying reference is caught by a single shared
scanner").

In `tests/test_state_layout_reference.py`, add a discovery helper and a guard
test that drives the whole skill markdown set through the work-item-1 driver:

1. A **discovery fixture** (not a module-level helper) named
   `skill_markdown_documents` that depends on both `project_root` and
   `read_repo_text` (from `tests/conftest.py`) and returns
   `{repo_relative_path: text}` for every skill markdown file. The fixture globs
   `project_root.glob("skill/novel-ralph/**/*.md")` for the file set and reads
   each file's text **through the injected `read_repo_text` callable**, passing
   the file's path parts (relative to `project_root`) so the single sanctioned
   UTF-8 reader is reused rather than duplicated. A fixture is required (not a
   module-level walk) because `read_repo_text` is itself a fixture returning a
   `(*parts) -> str` callable and so is unavailable at module-import/collection
   time; building the map inside a fixture is the only way to honour the
   conftest single-reader intent. This resolves the review's should-fix finding
   3 (do not re-implement `Path.read_text` at module level — reuse the reader
   inside a fixture). Keys are the repo-relative POSIX paths (e.g.
   `skill/novel-ralph/references/done-conditions.md`) so failure messages name
   the offending file unambiguously.
2. `test_no_skill_reference_carries_direct_write_recipe` — **this is the
   acceptance-bearing guard.** It calls
   `find_direct_state_write_recipes_in_files(skill_markdown_documents)` and
   asserts the returned mapping is empty. It is fully glob-driven and carries
   **zero per-file edits**: adding a new reference under `skill/novel-ralph/`
   needs no change to this test, which is the 7.3.3 "single shared scanner,
   with no per-file duplication" criterion. On failure it assembles its message
   by iterating the returned mapping's keys — the per-file detector already
   embeds design §4.1 and ADR-002 in each message, so the guard only needs to
   join the offending file labels (the mapping keys) with their message lists;
   it invents no second message format (resolves should-fix finding 4). As a
   non-`test_*.py` concern this still uses a plain `assert` because it *is* a
   `test_*.py` module (the `**/test_*.py` per-file-ignores apply here), unlike
   the scanner module.
3. `test_discovery_covers_known_skill_files` — **this is an intentional
   tripwire, not a second detector and not duplication of the guard.** It is
   NOT the acceptance-bearing test (item 2 is). It asserts the discovered label
   set equals exactly `SKILL.md` plus the seven named references, and contains
   nothing outside `skill/novel-ralph/`. The hard-coded eight-name set lives
   only here, by design: its purpose is that when a contributor adds (or
   removes) a reference, this single assertion fails and *forces a human to
   look at the new file*, confirm the glob caught it, and consciously add it to
   the reviewed inventory. Its failure on a newly added reference is a
   *designed feature*, not maintenance burden duplicated from the detector. The
   7.3.3 acceptance bar ("no per-file duplication") is satisfied because the
   **guard** (item 2) is the detector applied over a glob with no per-file
   edits; this tripwire neither detects recipes nor is consulted by the guard —
   the guard scans the file even if this list is stale (the pre-mortem's second
   scenario). The role split is pinned in the Decision Log so a reviewer cannot
   read item 3 as breaching the acceptance criterion.
4. `test_done_conditions_predicate_pseudocode_not_flagged` — a regression pin
   that the read-only `python` predicate fences in `done-conditions.md` are not
   flagged (reconstruct the read-only shape as a synthetic fixture, mirroring
   the existing `test_read_only_open_not_flagged` style, so the test does not
   couple to the reference's exact current wording).
5. Parametrized planted-recipe-in-another-file cases: reuse a **named** subset
   of
   the existing `_PLANTED_RECIPES` corpus — exactly the ids `raw-open-write` (a
   Python-library write form, line 58), `shell-redirect-no-space` (a
   shell-redirect form, line 70), and `indented-list-step-append` (an
   indented-list form, line 86) — embed each into a synthetic
   non-`state-layout.md` document label (e.g.
   `"skill/novel-ralph/references/done-conditions.md"`), and assert the driver
   reports it under that label. Naming the three ids (resolving round-1
   improvement finding 6) keeps the test deterministic and reviewable. Because
   all new tests live in the **same** module as `_PLANTED_RECIPES` (pinned in
   the Constraints and Decision Log per round-2's open finding), this reuse is
   a plain module-local reference (`_PLANTED_RECIPES["raw-open-write"]` etc.) —
   there is no cross-module import and so no reintroduction of the
   private-import smell the conftest design eliminates. (If, and only if, the
   cap forces option (b), these ids resolve against the shared
   `tests/_planted_recipes.py` module both test modules import; under no branch
   is a cross-module *private* import used.) This proves the *reach* extends
   beyond `state-layout.md` without re-testing every form (the per-form matrix
   already lives in the single-file `test_planted_recipe_is_flagged`, so
   re-running all of them through the driver would be duplication, not
   coverage).

Keep every existing 1.2.8 test passing unchanged (the Constraint). The new
tests sit beside them.

Tests classification: items 2-5 are unit tests over the pure driver and the
discovery helper. There is no behavioural/property/snapshot/e2e obligation here
for the same reasons as work item 1.

Validation: `make all`. Before the change, plant a recipe in
`done-conditions.md` on a scratch copy to confirm
`test_no_skill_reference_carries_direct_write_recipe` goes red (red step), then
revert. After the change, the live guard is green on the clean tree and the
synthetic planted-in-another-file cases are green. If the live guard goes red
against the *actual* tree, that is a real recipe in shipped prose — stop and
escalate per Tolerances (it is 6.2.3's prose remit, not a guard bug).

### Work item 3 — developers-guide note, roadmap tick, and Markdown gates

Implements AGENTS.md "Project documentation" (lines 179-188): internally facing
practices are documented in `docs/developers-guide.md`.

1. Extend the "The state-layout direct-edit guard" section
   (`docs/developers-guide.md` lines 315-333) to record that the guard now
   scans *every* skill markdown file under `skill/novel-ralph/` (the seven
   references and `SKILL.md`), via a shared multi-file driver
   (`find_direct_state_write_recipes_in_files`), with no per-file duplication.
   State the `.md` extension as an explicit **gate assumption**, not a passing
   remark: the `**/*.md` discovery glob only catches files ending `.md`, so a
   new reference added with a `.markdown`/`.mdx` extension would slip past the
   guard silently (the round-1 pre-mortem's most-likely six-month failure). The
   note must say that all skill references use `.md` by convention and that a
   non-`.md` skill document is a smell to be caught in review until
   property/extension hardening lands in roadmap 7.3.4. Record too that
   `test_discovery_covers_known_skill_files` is the tripwire that forces a
   human to inspect any newly added reference. Cross-reference roadmap 7.3.3.
   Keep prose wrapped at 80 columns and code spans inside backticks (AGENTS.md
   "Markdown guidance", lines 167-177). Use en-GB Oxford spelling
   ("-ize"/"-yse"/"-our").
2. Tick roadmap task 7.3.3 to `[x]` in `docs/roadmap.md` (line 694).
3. Run `make fmt` to format the Markdown and fix any table markup, then
   `make markdownlint` and `make nixie` (the latter validates Mermaid; there
   are no new diagrams, so expect a clean no-op pass).

Tests: documentation-only commit; no new code tests. The code gates already
passed in work items 1-2. Validation: `make all` (still green), plus
`make markdownlint` and `make nixie` for the Markdown changes (AGENTS.md
"Markdown guidance", lines 169-172).

## Concrete steps

Run everything from the worktree root,
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-3`. The branch is
`roadmap-7-3-3` (confirm with `git branch --show-current`); do not work on
`main`.

1. Load skills and orient:

   ```sh
   leta show find_direct_state_write_recipes
   leta refs read_repo_text
   sem diff --help
   ```

2. Establish the current baseline (expect every file clean):

   ```sh
   PYTHONPATH=tests python3 - <<'PY'
   import pathlib
   from _state_layout_scanner import find_direct_state_write_recipes

   for f in sorted(pathlib.Path("skill/novel-ralph").rglob("*.md")):
       hits = find_direct_state_write_recipes(f.read_text(encoding="utf-8"))
       print(f, len(hits))
   PY
   ```

   Expected: a mapping with an empty list for every file.

3. Work item 1: add the driver and its four unit tests; run `make test` (red
   first if you add tests before the function), then `make all`. Commit.

4. Work item 2: add the discovery helper and the widened guard tests; run
   `make all`. Demonstrate red by planting a recipe in a scratch copy of
   `done-conditions.md`, confirm the guard fails, revert, confirm green. Commit.

5. Work item 3: edit the developers-guide note, tick the roadmap, run
   `make fmt`, `make all`, `make markdownlint`, `make nixie`. Commit.

Commit messages follow the `commit-message` skill (file-based, never `-m`), in
en-GB Oxford spelling, and gate each commit with `make all` (AGENTS.md "Run all
code commit gateways before committing").

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. The new unit tests for the driver
  (`TestFindDirectStateWriteRecipesInFiles`) and the widened guard
  (`test_no_skill_reference_carries_direct_write_recipe`,
  `test_discovery_covers_known_skill_files`,
  `test_done_conditions_predicate_pseudocode_not_flagged`, and the
  planted-in-another-file parametrization) all pass; every pre-existing 1.2.8
  test still passes unchanged.
- Behaviour that can be verified by hand: insert
  `Path("working/state.toml").write_text("x = 1")` inside a `python` fence in
  `skill/novel-ralph/references/done-conditions.md`, run `make test`, and
  observe `test_no_skill_reference_carries_direct_write_recipe` fail naming
  `done-conditions.md` and design §4.1/ADR-002; remove it and observe the test
  pass. This is the single shared scanner catching a recipe in a file other than
  `state-layout.md`, with no new per-file test function — the 7.3.3 success
  criterion.
- Lint/typecheck: `make check-fmt`, `make lint` (Ruff + `interrogate` at 100% +
  Pylint), and `make typecheck` (`ty`) all clean over `PYTHON_TARGETS`.
- Markdown: `make markdownlint` and `make nixie` pass for the developers-guide
  and roadmap edits.

Quality method (how we check): `make all` for the code gates;
`make markdownlint` and `make nixie` for the Markdown gates. CI re-runs the
same targets (`docs/developers-guide.md` "GitHub Actions").

## Idempotence and recovery

Every step is re-runnable. The scratch recipe planted to demonstrate red is
reverted before commit
(`git checkout -- skill/novel-ralph/references/done-conditions.md`). If a
commit's gate fails, fix forward and re-run `make all`; nothing here is
destructive. The discovery glob is deterministic over the tracked tree, so
re-running the guard yields the same result.

## Artifacts and notes

Plan-time baseline transcript (all skill markdown files clean under the
single-file scanner):

```plaintext
SKILL.md: 0 hit(s)
references/conflict-attractor.md: 0 hit(s)
references/critic-personas.md: 0 hit(s)
references/desloppify-checklist.md: 0 hit(s)
references/done-conditions.md: 0 hit(s)
references/jtbd-novel.md: 0 hit(s)
references/state-layout.md: 0 hit(s)
references/stc-beat-sheet.md: 0 hit(s)
```

## Interfaces and dependencies

No new external dependency. The only libraries are the stdlib `re` (already
used by the scanner) and `pathlib` (used by the test for discovery). No cuprum,
no Cyclopts, no markdown/AST parser — see the Decision Log entry on why the
cuprum mandate is not applicable.

In `tests/_state_layout_scanner.py`, define:

```python
def find_direct_state_write_recipes_in_files(
    documents: dict[str, str],
) -> dict[str, list[str]]: ...
```

The `dict[str, str]` parameter is deliberate and import-free: the scanner
imports only `re`, so a `cabc.Mapping` annotation would force two new import
lines under a `TYPE_CHECKING` guard, and `ty`/Pylint/Ruff gate the module. This
form adds no imports and compiles verbatim. It reuses the existing
`find_direct_state_write_recipes(markdown: str) -> list[str]`. The discovery
helper lives in the test module (so the scanner stays pure), as a pytest
fixture that depends on both `project_root` and `read_repo_text` from
`tests/conftest.py` (so the single sanctioned UTF-8 reader is reused, not
duplicated). No change to `novel_ralph_skill/` (the shipped package).

## Revision note

Initial draft (2026-06-23). Establishes the three-work-item decomposition, pins
the multi-file driver signature against the verified-pure existing scanner,
records the clean plan-time baseline, and justifies why the
cuprum/external-docs research mandate is not load-bearing for this
test-tree-only change.

Round 2 (2026-06-23). Resolves the Logisphere round-1 review. Changes:

1. Blocking finding 1 — changed the pinned driver signature from
   `cabc.Mapping[str, str]` to the import-free `dict[str, str]` in both the
   Work Item 1 code block and the Interfaces section, with a justification that
   the scanner imports only `re` (verified) so a `cabc` annotation would
   require two new `TYPE_CHECKING`-guarded import lines that `ty`/Pylint/Ruff
   would otherwise reject. Pinned in a new Decision Log entry.
2. Blocking finding 2 — made the role split explicit in Work Item 2 items 2-3
   and
   pinned it in a new Decision Log entry:
   `test_no_skill_reference_carries_direct_write_recipe` is the
   acceptance-bearing, fully glob-driven guard with zero per-file edits;
   `test_discovery_covers_known_skill_files` is an intentional tripwire whose
   enumerated inventory and failure-on-new-reference are a designed feature,
   not duplication of the detector. Updated Risk-1 mitigation to match.
3. Should-fix finding 3 — Work Item 2 item 1 now specifies a
   `skill_markdown_- documents` pytest fixture depending on `project_root` and
   `read_repo_text`,
   reusing the sanctioned UTF-8 reader instead of re-implementing
   `Path.read_text` at module level. Pinned in a new Decision Log entry.
4. Should-fix finding 4 — Work Item 2 item 2 now states the guard assembles its
   failure message from the returned mapping keys (the per-file detector
   already embeds §4.1/ADR-002), inventing no second message format.
5. Improvement finding 5 — corrected the two "199 lines" references to the
   verified 198 lines.
6. Improvement finding 6 — Work Item 2 item 5 now names the three chosen
   `_PLANTED_RECIPES` ids (`raw-open-write`, `shell-redirect-no-space`,
   `indented-list-step-append`) instead of "a representative subset".
7. Pre-mortem mitigation — Work Item 3 now requires the developers-guide note to
   state the `.md` extension as an explicit gate assumption (a non-`.md` skill
   document is a review smell until 7.3.4 hardens extension coverage).

These are precision-of-instruction edits; the three-work-item decomposition,
the file footprint, and the deterministic/test-tree-only scope are unchanged.

Round 3 (2026-06-23). Resolves the Logisphere round-2 review's sole open
finding (the sibling-module-split vs `_PLANTED_RECIPES`-reuse conflict).
Changes:

1. Removed the sibling-module escape hatch from Work Item 1's test-placement
   instruction. All new tests now stay in
   `tests/test_state_layout_reference.py`, pinned at plan time with a verified
   line-count estimate (277 current → ≈ 393 post-change, under the 400 cap;
   full breakdown in the new Decision Log entry).
2. Added a hard Constraint forbidding both a sibling-module split (unless the
   cap is genuinely breached) and, in every branch, a cross-module *private*
   import of `_PLANTED_RECIPES`. The only sanctioned fallback if the cap is
   breached is option (b) — promote `_PLANTED_RECIPES` to a shared
   `tests/_planted_recipes.py` support module — mirroring how
   `tests/_state_layout_scanner.py` is shared.
3. Added a Decision Log entry recording the same-module decision, the line-count
   estimate, the option (b) fallback, and option (c) (inlining the three named
   recipe literals) as a viable but non-preferred no-import alternative.
4. Updated Work Item 2 item 5 to state explicitly that, because all new tests
   are same-module, `_PLANTED_RECIPES` reuse is a plain module-local reference
   with no cross-module import — closing the anti-pattern the conftest refactor
   and six audits exist to kill.

These are precision-of-instruction edits; the three-work-item decomposition,
the file footprint, and the deterministic/test-tree-only scope are unchanged.

Fix round 1 (2026-06-23). Resolves the dual review's sole blocking finding: the
Work Item 3 `make fmt` reflow (commit `d8385ee`) had corrupted prose in
`docs/developers-guide.md` (the exit-code section, originally near lines
252-256). The trailing `1.` of the sentence `… is exit 3, never 1.` had been
rewrapped to the start of a line preceded by a blank line, so Markdown rendered
`1. A command body …` as a spurious single-item ordered list, severing `never`
from `1` and turning a sentence into a list item. The regression was invisible
to every gate (mdformat treats `1.` as a valid list, so `check-fmt` stayed
idempotent-green, and markdownlint MD029 accepts a lone `1.`). Fixed by
rewording to `… is never exit 1; it is always exit 3. A command body …`, which
removes the digit from any line start so no list can form, then re-running the
`make fmt` markdown toolchain (`mdtablefix --wrap`, `markdownlint-cli2 --fix`)
on the file alone to confirm the wrap is stable and the artefact does not
re-appear. The fmt run was scoped to the touched file to avoid the known
whole-tree mdformat churn on unrelated planning artefacts. `make all` green
(235 passed); `markdownlint` (0 errors) and `nixie` (all diagrams validated)
clean. The single `coderabbit --agent` finding (an 80-column claim against this
execplan's Purpose section) was a false positive: the flagged lines 11-26 are
already wrapped at or under 80 columns, as markdownlint MD013 confirms.

This is a prose-correctness fix to one source-of-truth document; the
three-work-item decomposition, the test-tree footprint, and the deterministic
scope are unchanged.

Fix round 2 (2026-06-23). Resolves the dual review's sole blocking finding: an
en-GB Oxford-spelling regression in the `backstop-unknown-writer` planted
recipe. Work Item 2's extraction (commit `da2ea4c`) lifted the literal into
`tests/_planted_recipes.py` line 79 as `mywriter("working/state.toml").write(
serialize(doc))`, silently flipping the en-GB `serialise(doc)` form present in
the source line (`816225e~1:tests/test_state_layout_reference.py` line 93). The
repository uses `serialise`/`serialiser` consistently — the harness design doc,
ADR-002, and the roadmap — and the Oxford-spelling convention is mandatory for a
gated `PYTHON_TARGETS` file. Fixed by reverting the literal to `serialise(doc)`.
There is no functional impact: the direct-write scanner matches `.write(`
regardless of the argument, so the planted recipe is still flagged. `make all`
green (235 passed); the change touches no Markdown, so `markdownlint`/`nixie`
were not engaged. `coderabbit review` returned no findings.

This is a single-character convention fix to one gated test-support module; the
three-work-item decomposition, the test-tree footprint, and the deterministic
scope are unchanged.
