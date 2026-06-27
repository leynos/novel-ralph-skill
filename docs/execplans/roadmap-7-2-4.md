# Repoint the scan-shape stragglers off the `rulepack.detect` re-export and settle the re-export's fate

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

Roadmap task 7.2.3 relocated the two neutral per-line-scan shapes —
`ScannedChapter` (the scan input) and `LineHit` (the scan output) — out of the
rule-pack domain (`novel_ralph_skill/rulepack/detect.py`) and into the neutral
leaf module `novel_ralph_skill/loaderkit/scan.py`, so the per-line scan finally
has one home. To stay idempotent and avoid churn, 7.2.3 left a backward-compatible
**re-export** of both shapes in `rulepack.detect` (Decision D-REEXPORT,
`docs/execplans/roadmap-7-2-3.md:341-385`). The post-merge audit
(`docs/issues/audit-7.2.3.md`, Findings 1 and 3) then recorded the unfinished
half: several consumers still reach the relocated shapes *through* that
`rulepack.detect` re-export, so the `ledger → rulepack` and `command → rulepack`
detection-shape edges the relocation set out to remove still exist at the test
and command layers, and stale Sphinx `:class:` cross-references still point a
reader at the re-export rather than the shapes' true home.

After this change, every consumer of `ScannedChapter`/`LineHit` imports them from
their single canonical home (`loaderkit.scan`, or the `loaderkit` package
re-export), no module or test reaches them through `rulepack.detect`, the stale
Sphinx cross-references point at `loaderkit.scan`, and the now-dead
`rulepack.detect` re-export is pruned (with a pinning test proving it is gone and
that the rule-pack detector's genuine contract — `DetectionReport`, `RuleFinding`,
`detect` — still exports cleanly). You can observe success by running
`make all` (the full Python gate: ruff format/lint, interrogate docstrings,
pylint, `ty` typecheck, pytest) and `make markdownlint` plus `make nixie` for the
doc edits, all green, alongside the new pinning test
`tests/test_rulepack_detect.py::test_detect_no_longer_reexports_scan_shapes`,
which fails before the prune and passes after. Success can be observed by
running these gates.

This completes the step-7.2 single-home hypothesis for the scan shapes: each
detection-pack loader-and-scan primitive — and now each of its two shapes — has
exactly one home, documented and test-pinned so it cannot silently re-fork.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The frozen rule-pack output contract (ADR-003): `DetectionReport`,
  `RuleFinding`, and `detect` **stay defined in and exported from**
  `novel_ralph_skill/rulepack/detect.py`. This task touches **only** the
  re-exported neutral shapes `ScannedChapter`/`LineHit`; it must not move,
  rename, or alter the signature of `DetectionReport`, `RuleFinding`, or
  `detect`, nor the ledger's `DeviceFinding`/`LedgerReport`/`detect_ledger`.
- The single canonical definitions of `ScannedChapter` and `LineHit` remain in
  `novel_ralph_skill/loaderkit/scan.py` (roadmap 7.2.3). This task does **not**
  edit `loaderkit/scan.py` — neither its code nor its docstrings. The
  `line_hit`-callback docstring rationale in `loaderkit/scan.py` is owned by
  roadmap tasks 7.2.3.2 and 7.8.1 (audit-7.2.3 Finding 2), **not** this task; do
  not retune it here.
- Scope fence against neighbouring tasks: do **not** drop or default the
  `line_hit` callback (7.8.1), do **not** extract a shared scan-aggregate
  skeleton or change `scan_pattern`'s return shape (7.8.2), and do **not**
  generalise the loaderkit import-direction guard (7.2.3.1). This task is purely
  import-repointing, Sphinx-reference repointing, and the re-export prune-or-keep
  decision.
- The `loaderkit` package must remain a neutral leaf that imports neither
  `rulepack` nor `ledger` (design §6, §6.3; ADR-003). This task only moves
  imports *toward* `loaderkit`; it must not introduce any edge *out of*
  `loaderkit`.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, commit
  messages, and docstrings (AGENTS.md).
- No single code file may exceed 400 lines (AGENTS.md). This task removes lines
  from `rulepack/detect.py` and edits import lines elsewhere; it cannot grow a
  file past the cap, but re-check after edits.
- Quality gates are non-negotiable: every commit must pass `make all`
  (ruff format-check, ruff lint, interrogate 100% docstring coverage, pylint,
  `ty` typecheck, pytest), and doc-only commits must additionally pass
  `make markdownlint` and `make nixie` (AGENTS.md).

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- Scope: if the change requires editing more than the enumerated files (the four
  straggler import sites, the four Sphinx-reference sites, `rulepack/detect.py`,
  one new/extended test, and `docs/developers-guide.md`), or net more than ~120
  lines, stop and escalate.
- Interface: if removing the re-export would require any change to the public
  signature of `detect`, `DetectionReport`, `RuleFinding`, `detect_ledger`,
  `DeviceFinding`, or `LedgerReport`, stop and escalate (it must not).
- Dependencies: no new external dependency is expected. If one appears necessary,
  stop and escalate.
- Iterations: if `make all` still fails after 3 fix attempts on any one work
  item, stop and escalate.
- Re-export fate ambiguity: the plan **decides** to prune the re-export (see
  Decision D-PRUNE below). If, during implementation, an out-of-tree or
  packaging-level consumer of `novel_ralph_skill.rulepack.detect.ScannedChapter`
  /`.LineHit` is discovered that cannot be repointed in this task, stop and
  escalate before pruning (the fallback is the documented retain-with-comment
  path from audit-7.2.3 Finding 1).

## Risks

- Risk: a consumer imports `ScannedChapter`/`LineHit` from `rulepack.detect`
  that the inventory missed, so pruning breaks it at import time.
  Severity: medium
  Likelihood: low
  Mitigation: the inventory below was built from an exhaustive
  `grep -rn "rulepack.detect import"` over `novel_ralph_skill/` and `tests/`
  (see Context). Work item 1 repoints every runtime importer of the neutral
  shapes *before* Work item 4 prunes the re-export, and Work item 4 adds a
  pinning test that constructs `detect`/`DetectionReport`/`RuleFinding` from
  `rulepack.detect` (proving the genuine contract survives) and asserts
  `ScannedChapter`/`LineHit` are **no longer** attributes of `rulepack.detect`.
  `make all` runs the full suite, so any missed importer fails loudly.

- Risk: after pruning, `ScannedChapter` becomes annotation-only in
  `rulepack/detect.py` (it is referenced only in the `detect` parameter
  annotation and docstring), and `from __future__ import annotations` plus Ruff
  rule TC001 (`typing-only-first-party-import`, selected in `pyproject.toml`)
  demands it move into a `TYPE_CHECKING` block. `LineHit`, by contrast, is a
  genuine runtime use — the `lambda` at `detect.py:212` constructs a `LineHit`
  instance — so it must stay a runtime import. (The `RuleFinding.lines` field
  annotation is not a runtime use: under `from __future__ import annotations`
  field annotations are strings, and the slotted dataclass derives `__slots__`
  from the annotation *keys*, not by evaluating the annotation *values*.)
  Severity: low
  Likelihood: high (this is expected, not a surprise)
  Mitigation: Work item 4 moves `ScannedChapter` into the existing
  `if typ.TYPE_CHECKING:` block in `detect.py` and keeps `LineHit` and
  `scan_pattern` as runtime imports. `make lint` (ruff TC001) and `make typecheck`
  (`ty`) confirm the split is correct. No `# noqa` is required, because
  `ScannedChapter` has no runtime use left in this module (contrast 7.2.3's
  D-REEXPORT, which needed `# noqa: TC001` only *because* the re-export forced a
  runtime import).

- Risk: a doc edit to `docs/developers-guide.md` trips `make markdownlint` or
  `make nixie`.
  Severity: low
  Likelihood: low
  Mitigation: the developers-guide edit is a one-line cross-reference clarity
  touch at most (see Work item 3); run `make markdownlint` and `make nixie`
  before committing any doc change.

## Progress

- [x] Work item 1 — Repoint the runtime straggler imports at `loaderkit.scan`.
  Done: split `commands/_desloppify.py` (neutral `ScannedChapter` from
  `loaderkit.scan`, `detect` from `rulepack.detect`), repointed
  `tests/test_ledger_detect.py`, `tests/test_ledger_properties.py`, and split
  `tests/test_rulepack_detect.py` (neutral shapes from `loaderkit.scan`, contract
  names from `rulepack.detect`). `make all` green (1467 passed, 1 skipped); ruff
  import ordering clean, no TC001 regression. coderabbit run 1: two minor findings,
  both on docs (execplan prose voice — addressed by reflowing to impersonal voice;
  and a count mismatch in `roadmap-7-2-4.logisphere-review-r1.md`, a pre-existing
  review artifact outside this task's edit scope — skipped, see Decision Log).
- [x] Work item 2 — Repoint the stale Sphinx `:class:` cross-references in the
  test docstrings (`tests/test_ledger_detect.py`,
  `tests/test_desloppify_sourcing.py`).
  Done: both `:class:` refs now point at
  `~novel_ralph_skill.loaderkit.scan.ScannedChapter`. `make all` green
  (interrogate still 100%); coderabbit run 2: 0 findings.
- [x] Work item 3 — Repoint the stale Sphinx `:class:` cross-references in the
  package/command/dev-guide docstrings (`ledger/__init__.py`,
  `commands/_desloppify.py` docstring, `docs/developers-guide.md` if needed).
  Done: `ledger/__init__.py` docstring now describes the ledger as sharing the
  **neutral** `loaderkit.scan` scan shape (keeping the "deliberate parallel to
  rulepack" framing intact) and `commands/_desloppify.py:188` `source_chapters`
  return docstring repointed at `loaderkit.scan.ScannedChapter`.
  `docs/developers-guide.md` needed **no** edit — its loaderkit section already
  states the shapes are defined in `loaderkit/scan.py` and imported from the
  neutral home (≈1740-1748); the only `rulepack.detect` reference there
  (line 1496) is to the genuine `detect(pack, chapters)` aggregation, not the
  shapes. No `.md` touched in this commit, so the markdown gates do not apply.
  `grep -rn ":class:.*rulepack\.detect\.ScannedChapter"` over
  `novel_ralph_skill/` and `tests/` returns nothing. `make all` green;
  coderabbit run 3: 0 findings.
- [x] Work item 4 — Prune the `rulepack.detect` re-export and pin its fate with
  a test.
  Done: dropped `ScannedChapter` from the runtime `loaderkit.scan` import and
  moved it under the existing `TYPE_CHECKING` block; kept `LineHit` and
  `scan_pattern` as runtime imports (D-LINEHIT-RUNTIME); pruned `__all__` to
  `["DetectionReport", "RuleFinding", "detect"]`. Added the pinning test
  `test_detect_no_longer_reexports_scan_shapes`, verified red against the
  pre-prune tree and green after (both proven via `git stash`). `make all` green
  (1468 passed, 1 skipped); ruff TC raised no finding; `ty` clean. coderabbit
  run 4: 0 findings.
  Deviation (see Decision Log D-PINTEST-LINEHIT): the plan's drafted test and its
  acceptance probe asserted `not hasattr(detect_module, "LineHit")` / a
  `False False` probe, which is impossible under D-LINEHIT-RUNTIME — keeping
  `LineHit` as a runtime import necessarily leaves it a module attribute. The
  test was corrected to pin the achievable single-home invariant: `__all__`
  equals exactly the three contract names, neither shape is *advertised*, and
  `ScannedChapter` is not a module attribute. The observed probe is therefore
  `False True ['DetectionReport', 'RuleFinding', 'detect']`.

## Surprises & discoveries

- Observation: the task body enumerates three runtime stragglers
  (`commands/_desloppify.py`, `tests/test_ledger_properties.py`,
  `tests/test_ledger_detect.py`), but `tests/test_rulepack_detect.py:24` also
  imports the neutral `ScannedChapter`/`LineHit` *through* the `rulepack.detect`
  re-export (alongside the genuine `DetectionReport`/`RuleFinding`/`detect`).
  Evidence: `grep -rn "from novel_ralph_skill.rulepack.detect import"` over
  `novel_ralph_skill/` and `tests/` (Context inventory below); the
  `test_rulepack_detect.py` import block reads
  `DetectionReport, LineHit, RuleFinding, ScannedChapter, detect`.
  Impact: the roadmap **success criterion** ("no module or test imports
  `ScannedChapter` or `LineHit` through the `rulepack.detect` re-export") captures
  this fourth straggler even though the task body's prose under-enumerates it.
  Work item 1 therefore splits `test_rulepack_detect.py`'s import too: the neutral
  shapes from `loaderkit.scan`, the genuine contract names from `rulepack.detect`.
  This is required for the prune (Work item 4) to leave the suite green.

- Observation (Work item 4): the drafted pinning test and acceptance probe
  asserted `not hasattr(detect_module, "LineHit")` / `False False`, which
  contradicts Decision D-LINEHIT-RUNTIME. Because `LineHit` stays a runtime
  import (the `line_hit` lambda constructs it), it remains a module attribute, so
  `hasattr` is `True` by construction. The single-home invariant the prune
  actually establishes is "no longer **re-exported**" (absent from `__all__`),
  not "no longer **importable**". Resolved by D-PINTEST-LINEHIT below; the
  corrected test still discriminates (red pre-prune, green after).

## Decision log

- Decision (D-PRUNE): prune the `ScannedChapter`/`LineHit` re-export from
  `rulepack.detect` rather than retain it as a compatibility seam.
  Rationale: the exhaustive inventory shows **every** importer of these two
  shapes through `rulepack.detect` is in-tree (one command module and three test
  modules) and is repointed by this task. `novel_ralph_skill` is a single
  application package with no published `rulepack.detect` API surface that an
  out-of-tree caller depends on; the only frozen public contract (ADR-003) is
  `DetectionReport`/`RuleFinding`/`detect`, which are unaffected. Retaining a
  re-export of types the module no longer defines would re-advertise rule-pack
  ownership of neutral shapes — the precise impression Finding 3 says is no longer
  warranted — and would leave a third import source for one type. The audit's
  Finding 1 proposed fix explicitly authorises the prune "if nothing external
  depends on the old path". Pruning is the design-aligned single-home outcome.
  Date/Author: 2026-06-27, planning agent.

- Decision (D-PRUNE-FALLBACK): if Work item 1 uncovers an importer of
  `rulepack.detect.ScannedChapter`/`.LineHit` that this task cannot repoint
  (e.g. an out-of-tree or generated consumer), do **not** prune; instead retain
  the re-export with a one-line comment noting it is a compatibility forwarder to
  `loaderkit.scan`, add the same pinning test in its retain form (asserting the
  re-export resolves to the `loaderkit.scan` definitions), and record the
  deviation here. This is the documented alternative from audit-7.2.3 Finding 1.
  No such importer is expected (see D-PRUNE).
  Date/Author: 2026-06-27, planning agent.

- Decision (D-LINEHIT-RUNTIME): keep `LineHit` as a runtime import in
  `rulepack/detect.py` after the prune; move only `ScannedChapter` into
  `TYPE_CHECKING`.
  Rationale: `LineHit` is constructed at runtime in `detect`'s
  `line_hit=lambda chapter, line: LineHit(...)` (`detect.py:212`); that genuine
  constructor call is the sufficient reason it stays runtime (the
  `RuleFinding`/`DetectionReport` field annotations are stringified by
  `from __future__ import annotations` and are not evaluated at class-build time).
  `ScannedChapter` is referenced only in the `detect` parameter
  annotation, which `from __future__ import annotations` stringifies. Ruff TC001
  therefore correctly wants `ScannedChapter` (and only it) under `TYPE_CHECKING`.
  Date/Author: 2026-06-27, planning agent.

- Decision (D-PINTEST-LINEHIT): the pinning test asserts that the scan shapes are
  no longer **advertised** (absent from `__all__`) and that `ScannedChapter` is
  not a module attribute, rather than asserting `not hasattr(..., "LineHit")`.
  Rationale: D-LINEHIT-RUNTIME keeps `LineHit` a runtime import (the `line_hit`
  lambda at `detect.py:207` constructs it), and a runtime `from ... import LineHit`
  necessarily binds `LineHit` as a module attribute, so `hasattr(detect, "LineHit")`
  is `True` by construction. The drafted test body and the drafted acceptance
  probe (`False False`) contradicted D-LINEHIT-RUNTIME; only D-LINEHIT-RUNTIME is
  technically achievable, so the test was corrected to pin the real single-home
  invariant: `__all__ == {DetectionReport, RuleFinding, detect}`, neither shape
  in `__all__`, and `ScannedChapter` not a module attribute. The corrected test
  still fails pre-prune and passes post-prune (verified via `git stash`). The
  observed acceptance probe is therefore
  `False True ['DetectionReport', 'RuleFinding', 'detect']` — `ScannedChapter`
  gone as an attribute, `LineHit` retained only as
  a private internal runtime import, `__all__` pruned to the contract.
  Date/Author: 2026-06-27, implementing agent.

- Decision (D-PINTEST-RECONCILE): reconcile the three drafted passages that still
  asserted the superseded `False False` / `not hasattr(LineHit)` outcome with the
  delivered, achievable invariant under D-PINTEST-LINEHIT. The Work-item-4 test
  spec block now mirrors the delivered `tests/test_rulepack_detect.py` test
  (`__all__` equality, `"LineHit" not in __all__`, `not hasattr(..., "ScannedChapter")`);
  the Concrete-steps probe comment and the Validation/acceptance bullet now read
  `False True ['DetectionReport', 'RuleFinding', 'detect']`. Rationale: an auditor
  or follow-on agent running the probe observes `False True` (verified live), so
  the stale `False False` passages would have wrongly read as a failed prune. The
  Surprises (216-223) and D-PINTEST-LINEHIT entries already recorded the superseded
  outcome as superseded; these were the only three remaining unmarked contradictions.
  No code changed; this is a living-document correction per AGENTS.md.
  Date/Author: 2026-06-27, fix-round-1 agent.

## Outcomes & retrospective

All four work items landed; `make all` is green at HEAD (1468 passed, 1 skipped),
with `make markdownlint` and `make nixie` green for the doc commits. Compared
against Purpose:

- Every consumer imports the scan shapes from `loaderkit.scan` (or its package
  re-export); no module or test reaches them through `rulepack.detect`. The
  remaining `rulepack.detect` importers are exactly the genuine contract
  (`DetectionReport`/`RuleFinding`/`detect`).
- The `rulepack.detect` scan-shape re-export is pruned: `__all__` is exactly
  `["DetectionReport", "RuleFinding", "detect"]`, `ScannedChapter` moved under
  `TYPE_CHECKING`, and `LineHit` stays a private runtime import (not advertised).
- The four stale `:class:` Sphinx references now point at `loaderkit.scan`;
  `grep` confirms none remain. `docs/developers-guide.md` needed no edit.
- The pinning test `test_detect_no_longer_reexports_scan_shapes` pins the prune
  (red pre-prune, green after).
- The rule-pack, ledger, `desloppify`, and `loaderkit` suites stay green at every
  commit boundary.

Retrospective note: the one substantive deviation (D-PINTEST-LINEHIT) was an
internal contradiction in the plan between D-LINEHIT-RUNTIME (keep `LineHit`
runtime) and the drafted `not hasattr(LineHit)` assertion. The single-home
invariant the task actually establishes is "not **re-exported**" (absent from
`__all__`), not "not **importable**"; the test now reflects that precisely.

## Context and orientation

Read these before editing (source-of-truth docs and skills, per the standing
rules):

- `docs/novel-ralph-harness-design.md` §6 and §6.1 — the neutral-leaf
  single-home discipline for the loader/scan primitives and shapes.
- `docs/adr-003-shared-interface-contract.md` — the frozen rule-pack output
  contract (`DetectionReport`/`RuleFinding`/`detect`) that must not move.
- `docs/issues/audit-7.2.3.md` Findings 1 and 3 — the exact stragglers and stale
  cross-references this task closes (Finding 2 is **out of scope**: it is
  7.8.1/7.2.3.2).
- `docs/execplans/roadmap-7-2-3.md` Decision D-REEXPORT (lines 341-385) and
  D-SCANTYPES — why the re-export was created and the `# noqa: TC001` idiom; this
  task removes that re-export.
- `docs/developers-guide.md` "The shared loader primitives (`loaderkit`)"
  (≈lines 1704-1762) — the prose describing the relocated shapes' single home.
- `AGENTS.md` — quality gates, the 400-line file cap, en-GB Oxford spelling.

Skills to load:

- `leta` (FIRST) — navigate and confirm references in `rulepack/detect.py`,
  `loaderkit/scan.py`, `ledger/__init__.py`, `commands/_desloppify.py`, and the
  test modules instead of ad-hoc ripgrep/read-file.
- `sem` — confirm the 7.2.3 relocation history if a reference is ambiguous.
- `python-router` → it will route to `python-types-and-apis` (the TC001 /
  runtime-vs-`TYPE_CHECKING` import split) and `python-testing` (the pinning test
  and the import-source assertions). Load the routed sub-skills.

No external-library behaviour is load-bearing here. This task is pure in-repo
Python import-repointing and one re-export prune; it relies on no cuprum API
(catalogue/allowlist/run options), no Cyclopts `--help`/`--version` behaviour,
no pytest-timeout or `uv run` resolution semantics, and no `tomlkit`. The only
tool behaviour it leans on is Ruff rule **TC001** (`typing-only-first-party-import`,
selected in `pyproject.toml` and enforced by `make lint`) and `ty`'s typecheck —
both already gating in CI; the plan pins their effect with the actual gate, not
with an external claim.

### Current state (verified inventory)

The single canonical definitions live in
`novel_ralph_skill/loaderkit/scan.py` (`class ScannedChapter`, `class LineHit`),
re-exported by the `loaderkit` package init
(`novel_ralph_skill/loaderkit/__init__.py` `__all__` lists both). The rule-pack
detector re-exports them:

- `novel_ralph_skill/rulepack/detect.py:29-33` imports
  `LineHit, ScannedChapter, scan_pattern` from `loaderkit.scan` (one runtime
  import statement; `scan_pattern` and the `LineHit` lambda keep it runtime).
- `novel_ralph_skill/rulepack/detect.py:41-47` — module `__all__` lists
  `DetectionReport, LineHit, RuleFinding, ScannedChapter, detect`.

Runtime importers of the neutral shapes **through** `rulepack.detect` (the
stragglers to repoint in Work item 1):

- `novel_ralph_skill/commands/_desloppify.py:57` —
  `from novel_ralph_skill.rulepack.detect import ScannedChapter, detect`
  (`ScannedChapter` is constructed at runtime at `_desloppify.py:204`; `detect`
  stays sourced from `rulepack.detect`).
- `tests/test_ledger_detect.py:27` —
  `from novel_ralph_skill.rulepack.detect import ScannedChapter`.
- `tests/test_ledger_properties.py:40` —
  `from novel_ralph_skill.rulepack.detect import ScannedChapter`.
- `tests/test_rulepack_detect.py:24-30` — imports
  `DetectionReport, LineHit, RuleFinding, ScannedChapter, detect` from
  `rulepack.detect` (split: neutral shapes → `loaderkit.scan`; genuine contract
  → `rulepack.detect`). This is the fourth straggler the success criterion
  captures (see Surprises).

Importers of the **genuine** rule-pack contract from `rulepack.detect` (must stay
unchanged): `commands/_desloppify_report.py:35` (`DetectionReport, RuleFinding`),
`tests/test_desloppify_report.py:20` (`DetectionReport, RuleFinding`),
`tests/test_desloppify_finding_message.py:17` (`RuleFinding`).

Stale Sphinx `:class:` cross-references still pointing at
`rulepack.detect.ScannedChapter` (to repoint in Work items 2-3):

- `novel_ralph_skill/ledger/__init__.py:14` (package docstring "input type").
- `novel_ralph_skill/commands/_desloppify.py:188` (`source_chapters` return
  docstring).
- `tests/test_ledger_detect.py:8` (module docstring).
- `tests/test_desloppify_sourcing.py:5` (module docstring).

Already correct (do not touch): `ledger/detect.py:22-24` already references
`:class:~novel_ralph_skill.loaderkit.scan.ScannedChapter`/`.LineHit` (7.2.3 fixed
the `ledger/detect.py` half of Finding 3). The developers-guide passage
(≈1740-1748) describes the shapes living in `loaderkit/scan.py` and does **not**
reference the `rulepack.detect` re-export, so it needs no edit for the prune;
re-read it during Work item 3 and edit only if a sentence still implies the shapes
are reachable through `rulepack.detect` (none currently does).

## Plan of work

Four ordered, independently committable work items. Each ends with the full gate
(`make all`; plus `make markdownlint` and `make nixie` for any commit touching a
`.md` file). Order matters: every runtime importer of the neutral shapes is
repointed (Work item 1) **before** the re-export is pruned (Work item 4), so the
suite is green at every commit boundary.

### Work item 1 — Repoint the runtime straggler imports at `loaderkit.scan`

Implements: roadmap 7.2.4 (success: "every consumer imports them from
`loaderkit.scan`"); audit-7.2.3 Finding 1; design §6/§6.1; ADR-003 (the genuine
contract stays in `rulepack.detect`).

Docs to read: design §6.1; audit-7.2.3 Finding 1; `loaderkit/__init__.py` (to
confirm the package re-export is available as an alternative source).
Skills: `leta` (confirm each import site and that no other line in the file
depends on the old source); `python-router` → `python-types-and-apis` (the
`TYPE_CHECKING` split nuance for the test imports).

Edits:

1. `novel_ralph_skill/commands/_desloppify.py:57`: split the import. Source the
   neutral shape from the neutral home and keep `detect` from the rule-pack
   detector:

   ```python
   from novel_ralph_skill.loaderkit.scan import ScannedChapter
   from novel_ralph_skill.rulepack.detect import detect
   ```

   `ScannedChapter` is constructed at runtime (`_desloppify.py:204`), so it stays
   a runtime import — no `TYPE_CHECKING` move, no `# noqa`. Keep import ordering
   ruff-clean (`make lint` enforces the `loaderkit` < `rulepack` ordering).

2. `tests/test_ledger_detect.py:27`: change
   `from novel_ralph_skill.rulepack.detect import ScannedChapter` to
   `from novel_ralph_skill.loaderkit.scan import ScannedChapter`.

3. `tests/test_ledger_properties.py:40`: same repoint as (2).

4. `tests/test_rulepack_detect.py:24-30`: split the combined import:

   ```python
   from novel_ralph_skill.loaderkit.scan import LineHit, ScannedChapter
   from novel_ralph_skill.rulepack.detect import (
       DetectionReport,
       RuleFinding,
       detect,
   )
   ```

Tests for this work item: no new test file is required here; the **existing**
suites are the behavioural pin. `tests/test_rulepack_detect.py`,
`tests/test_ledger_detect.py`, `tests/test_ledger_properties.py`, and the
`desloppify` command suites (`tests/test_desloppify_sourcing.py`,
`tests/test_desloppify_report.py`, `tests/test_desloppify_finding_message.py`,
plus any `tests/test_desloppify_command*.py`) exercise the repointed imports and
must stay green — they prove the shapes resolve identically from the new source
(same class objects, since `loaderkit.scan` is the single definition). The
import-source change is structurally pinned by Work item 4's new test.

Validation: run `make all` from the worktree root. Expect ruff format/lint clean
(import ordering correct, no TC001 regression), `ty` clean, and pytest fully
green. Commit: "Repoint scan-shape imports at loaderkit.scan".

### Work item 2 — Repoint stale Sphinx cross-references in the test docstrings

Implements: roadmap 7.2.4 (success: "stale `rulepack.detect.ScannedChapter`
Sphinx cross-references are repointed at `loaderkit.scan`"); audit-7.2.3
Finding 3.

Docs to read: audit-7.2.3 Finding 3; `ledger/detect.py:22-24` as the **pattern**
to mirror (it already uses `:class:~novel_ralph_skill.loaderkit.scan.ScannedChapter`).
Skills: `leta` (locate each `:class:` reference precisely).

Edits (docstring prose only — no code-behaviour change):

1. `tests/test_ledger_detect.py:8`: change
   `:class:~novel_ralph_skill.rulepack.detect.ScannedChapter` to
   `:class:~novel_ralph_skill.loaderkit.scan.ScannedChapter`.
2. `tests/test_desloppify_sourcing.py:5`: same repoint of the `:class:`
   reference.

Tests: docstring-only edits; no test added. The change is verified by grep
(Concrete steps) and by `make all` (interrogate still reports 100% docstring
coverage; ruff/pylint unaffected). These two test files are `.py`, not `.md`, so
`make markdownlint`/`make nixie` do not apply.

Validation: `make all` green; the grep in Concrete steps shows zero
`rulepack.detect.ScannedChapter` `:class:` references remain in these two files.
Commit: "Repoint scan-shape Sphinx refs in detect/sourcing tests".

### Work item 3 — Repoint stale Sphinx cross-references in package/command/dev-guide docstrings

Implements: roadmap 7.2.4 (success: stale Sphinx cross-references repointed);
audit-7.2.3 Finding 3 (`ledger/__init__.py` cross-reference and surrounding
prose).

Docs to read: audit-7.2.3 Finding 3 (the exact prose framing — "sharing the
*neutral* loaderkit scan shape", not "borrowing a rule-pack type");
`docs/developers-guide.md` ≈1704-1762.
Skills: `leta`; `en-gb-oxendict` (apply Oxford spelling to any reworded prose).

Edits:

1. `novel_ralph_skill/ledger/__init__.py:14`: change the `:class:` reference to
   `:class:~novel_ralph_skill.loaderkit.scan.ScannedChapter`, and adjust the
   surrounding sentence so the ledger is described as **sharing the neutral
   `loaderkit` scan shape** (its true parallel to the rule pack) rather than
   borrowing the `rulepack.detect.ScannedChapter` input type. Keep the existing
   "deliberate parallel to `novel_ralph_skill.rulepack`" framing intact; only the
   shape-ownership clause changes.
2. `novel_ralph_skill/commands/_desloppify.py:188`: change the `source_chapters`
   return-docstring `:class:` reference from
   `~novel_ralph_skill.rulepack.detect.ScannedChapter` to
   `~novel_ralph_skill.loaderkit.scan.ScannedChapter`.
3. `docs/developers-guide.md`: re-read the `loaderkit` section (≈1704-1762). It
   already states the shapes live in `loaderkit/scan.py`; edit **only** if a
   sentence still implies they are reachable through `rulepack.detect` (none does
   at draft time). If no edit is needed, record that in Progress and skip the
   markdown gates for this commit. If an edit is made, run `make markdownlint`
   and `make nixie`.

Tests: docstring/doc-prose edits; no test added. Interrogate (in `make all`)
keeps docstring coverage at 100%.

Validation: `make all` green; if `docs/developers-guide.md` changed,
additionally `make markdownlint` and `make nixie` green. Grep (Concrete steps)
shows zero remaining `rulepack.detect.ScannedChapter` `:class:` references across
`novel_ralph_skill/` and `tests/`. Commit: "Repoint scan-shape Sphinx refs in
ledger and desloppify docstrings".

### Work item 4 — Prune the `rulepack.detect` re-export and pin its fate

Implements: roadmap 7.2.4 (success: "the `rulepack.detect` re-export's fate is
recorded (kept with a pinning test, or pruned from `__all__`)"); audit-7.2.3
Finding 1 proposed fix (the prune branch); Decision D-PRUNE; ADR-003 (the genuine
contract stays exported).

Docs to read: roadmap-7-2-3.md Decision D-REEXPORT (lines 341-385, the re-export
this item removes); ADR-003 (confirm `DetectionReport`/`RuleFinding`/`detect`
remain the exported contract).
Skills: `leta` (confirm no remaining in-module runtime use of `ScannedChapter`);
`python-router` → `python-types-and-apis` (the TC001 `TYPE_CHECKING` move) and
`python-testing` (the pinning test).

Edits in `novel_ralph_skill/rulepack/detect.py`:

1. In the `from novel_ralph_skill.loaderkit.scan import (...)` block
   (lines 29-33), drop `ScannedChapter` from the runtime import and keep
   `LineHit, scan_pattern` (both are runtime uses — the `line_hit` lambda at
   line 212 and `LineHit` field annotations; see Decision D-LINEHIT-RUNTIME).
2. Add `ScannedChapter` to the existing `if typ.TYPE_CHECKING:` block (lines
   36-39):

   ```python
   if typ.TYPE_CHECKING:
       import collections.abc as cabc

       from novel_ralph_skill.loaderkit.scan import ScannedChapter
       from novel_ralph_skill.rulepack.schema import Rule, RulePack
   ```

   `ScannedChapter` is referenced only in the `detect` parameter annotation
   (line 180) and docstring, which `from __future__ import annotations`
   stringifies, so the `TYPE_CHECKING` source satisfies Ruff TC001 with no
   `# noqa`.
3. Remove `"LineHit"` and `"ScannedChapter"` from the module `__all__`
   (lines 41-47), leaving `["DetectionReport", "RuleFinding", "detect"]`. The
   rule-pack detector now advertises only the types it defines.

Add a pinning test in `tests/test_rulepack_detect.py` (the natural home — it
already imports `rulepack.detect`):

```python
def test_detect_no_longer_reexports_scan_shapes() -> None:
    """`rulepack.detect` exports only its own contract, not the neutral shapes."""
    import novel_ralph_skill.rulepack.detect as detect_module

    assert set(detect_module.__all__) == {
        "DetectionReport",
        "RuleFinding",
        "detect",
    }
    assert "ScannedChapter" not in detect_module.__all__
    assert "LineHit" not in detect_module.__all__
    assert not hasattr(detect_module, "ScannedChapter")
```

This is a **unit test** (AGENTS.md: pytest in the top-level `tests/` tree). It
fails before the prune (`__all__` contains the shapes; `ScannedChapter` is still
a module attribute) and passes after, pinning the re-export's removed fate so it
cannot silently return. `LineHit` is asserted absent from `__all__` only — not
via `hasattr` — because D-PINTEST-LINEHIT (and D-LINEHIT-RUNTIME) keep it a
runtime import, so `hasattr(detect_module, "LineHit")` is `True` by construction.
The genuine contract is already exercised by the existing
`tests/test_rulepack_detect.py` cases (which import and use
`DetectionReport`/`RuleFinding`/`detect` from `rulepack.detect`), so no separate
"contract survives" assertion is needed beyond the green suite; the new test's
`__all__` equality additionally proves the three contract names remain advertised.

No property test, snapshot test, behavioural (pytest-bdd) test, or e2e test is
warranted: this work item changes only an import surface, not runtime behaviour,
input/output shapes, or the JSON envelope. The existing property tests
(`tests/test_ledger_properties.py`, the `loaderkit` scan property) and the
`desloppify` command suites already cover the runtime behaviour through the
repointed imports and must stay green.

Fallback (Decision D-PRUNE-FALLBACK): if an unrepointable importer surfaces, do
not prune; instead keep the re-export with a one-line comment marking it a
compatibility forwarder to `loaderkit.scan`, and replace the test above with its
retain form:

```python
def test_detect_reexport_resolves_to_loaderkit() -> None:
    """The compatibility re-export resolves to the single loaderkit definition."""
    import novel_ralph_skill.loaderkit.scan as scan_module
    import novel_ralph_skill.rulepack.detect as detect_module

    assert detect_module.ScannedChapter is scan_module.ScannedChapter
    assert detect_module.LineHit is scan_module.LineHit
```

Record any such deviation in the Decision Log and Surprises sections.

Validation: `make all` green; the new test
`test_detect_no_longer_reexports_scan_shapes` fails on the pre-prune tree and
passes after. Commit: "Prune rulepack.detect scan-shape re-export".

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-4`.

1. Confirm the branch and the inventory before editing:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-4 branch --show-current
   # expect: roadmap-7-2-4
   grep -rn "from novel_ralph_skill.rulepack.detect import" \
     novel_ralph_skill/ tests/
   # expect the importers listed in Context (4 straggler sites + 3 genuine-contract sites)
   ```

2. Work item 1: edit the four import sites, then gate:

   ```bash
   make all
   ```

   Expect ruff/lint/`ty`/pytest all green. Commit.

3. Work items 2-3: edit the four `:class:` Sphinx references (plus the
   `ledger/__init__.py` prose clause), then verify and gate:

   ```bash
   grep -rn ":class:.*novel_ralph_skill.rulepack.detect.ScannedChapter\b" \
     novel_ralph_skill/ tests/
   # expect: no output (every neutral-shape :class: ref now points at loaderkit.scan)
   make all
   # if docs/developers-guide.md changed:
   make markdownlint
   make nixie
   ```

   Commit each work item separately (Work item 2, then Work item 3).

4. Work item 4: add the new test first and confirm it **fails** (red), then prune
   and confirm it **passes** (green):

   ```bash
   # after adding test_detect_no_longer_reexports_scan_shapes, before pruning:
   uv run pytest tests/test_rulepack_detect.py::test_detect_no_longer_reexports_scan_shapes -q
   # expect: 1 failed (re-export still present)
   # after pruning detect.py:
   uv run pytest tests/test_rulepack_detect.py::test_detect_no_longer_reexports_scan_shapes -q
   # expect: 1 passed
   make all
   ```

   Confirm no `ScannedChapter`/`LineHit` reaches through `rulepack.detect`:

   ```bash
   python -c "import novel_ralph_skill.rulepack.detect as d; \
     print(hasattr(d, 'ScannedChapter'), hasattr(d, 'LineHit'), d.__all__)"
   # expect: False True ['DetectionReport', 'RuleFinding', 'detect']
   # (LineHit stays a runtime import per D-LINEHIT-RUNTIME, so hasattr is True;
   # the single-home invariant is its absence from __all__, not from the module.)
   ```

   Commit.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` runs `pytest -v -n <workers>` and passes. The new
  `tests/test_rulepack_detect.py::test_detect_no_longer_reexports_scan_shapes`
  fails before the Work item 4 prune and passes after. The rule-pack, ledger,
  `desloppify`, and `loaderkit` suites all stay green at every commit boundary.
- Lint/typecheck: `make lint` (ruff check + interrogate 100% docstrings + pylint)
  and `make typecheck` (`ty`) clean. In particular, Ruff TC001 raises no new
  finding: `ScannedChapter` sits under `TYPE_CHECKING` in `rulepack/detect.py`,
  `LineHit`/`scan_pattern` stay runtime.
- Format: `make check-fmt` (`ruff format --check`) clean.
- Imports: `grep -rn "from novel_ralph_skill.rulepack.detect import"` over
  `novel_ralph_skill/` and `tests/` shows **only** the genuine-contract importers
  (`DetectionReport`/`RuleFinding`/`detect`); no `ScannedChapter`/`LineHit`.
- Sphinx refs: `grep -rn ":class:.*rulepack.detect.ScannedChapter\b"` over
  `novel_ralph_skill/` and `tests/` returns nothing.
- Markdown (only if `docs/developers-guide.md` changed): `make markdownlint` and
  `make nixie` clean.

Quality method (how we check): run `make all` after every work item, plus
`make markdownlint` and `make nixie` for any commit touching a `.md` file, plus
the two greps above and the `python -c` attribute probe at the end.

Acceptance, phrased as observable behaviour:

- Running `python -c "import novel_ralph_skill.rulepack.detect as d;
  print(hasattr(d,'ScannedChapter'), hasattr(d,'LineHit'), d.__all__)"` prints
  `False True ['DetectionReport', 'RuleFinding', 'detect']`: `ScannedChapter` is
  gone as a module attribute, `LineHit` survives only as a private runtime import
  (per D-LINEHIT-RUNTIME), and neither shape remains in `__all__`.
- Running `python -c "import novel_ralph_skill.commands._desloppify"` and
  `python -c "import novel_ralph_skill.ledger.detect"` both import cleanly (no
  `ledger → rulepack` or `command → rulepack` detection-shape edge remains).
- `make all` is green; the desloppify and ledger detection behaviour is
  unchanged (same envelopes, same exit codes), proven by the unchanged,
  still-green command and property suites.

## Idempotence and recovery

Every step is a pure source edit and is safely re-runnable. If `make all` fails
after an edit, the failure names the file and rule; fix and re-run — no state is
left behind. The work items are ordered so the tree is green at every commit
boundary (all runtime importers repointed before the re-export is pruned), so a
mid-task stop leaves a consistent, buildable tree. To revert, `git restore` the
touched files or reset the offending commit; there are no migrations, generated
artefacts, or external side effects.

## Artifacts and notes

Pre-change inventory (verified during planning):

```plaintext
rulepack.detect re-exports ScannedChapter/LineHit (detect.py __all__ + import).
Straggler runtime importers of the neutral shapes via rulepack.detect:
  commands/_desloppify.py:57 (ScannedChapter, detect)
  tests/test_ledger_detect.py:27 (ScannedChapter)
  tests/test_ledger_properties.py:40 (ScannedChapter)
  tests/test_rulepack_detect.py:24 (DetectionReport, LineHit, RuleFinding,
                                     ScannedChapter, detect)
Genuine-contract importers (unchanged):
  commands/_desloppify_report.py:35 (DetectionReport, RuleFinding)
  tests/test_desloppify_report.py:20 (DetectionReport, RuleFinding)
  tests/test_desloppify_finding_message.py:17 (RuleFinding)
Stale :class: Sphinx refs at rulepack.detect.ScannedChapter:
  ledger/__init__.py:14, commands/_desloppify.py:188,
  tests/test_ledger_detect.py:8, tests/test_desloppify_sourcing.py:5
Already correct: ledger/detect.py:22-24 (loaderkit.scan refs).
```

## Interfaces and dependencies

After this task:

- `novel_ralph_skill/rulepack/detect.py` `__all__` is exactly
  `["DetectionReport", "RuleFinding", "detect"]`. `ScannedChapter` is imported
  only under `TYPE_CHECKING`; `LineHit` and `scan_pattern` are runtime imports
  from `novel_ralph_skill.loaderkit.scan`.
- `novel_ralph_skill.loaderkit.scan` remains the single definition site of
  `class ScannedChapter` and `class LineHit`, re-exported by
  `novel_ralph_skill.loaderkit` (`__init__.py` `__all__`). Every consumer of the
  scan shapes imports from one of these two neutral sources.
- No public signature changes: `detect(pack, chapters) -> DetectionReport`,
  `DetectionReport`, `RuleFinding`, `detect_ledger`, `DeviceFinding`, and
  `LedgerReport` are untouched.
- New test symbol:
  `tests/test_rulepack_detect.py::test_detect_no_longer_reexports_scan_shapes`.

## Revision note

Initial draft (2026-06-27). Decomposes roadmap 7.2.4 into four ordered, atomic,
gate-passable work items: (1) repoint the four runtime straggler imports at
`loaderkit.scan`; (2-3) repoint the four stale Sphinx `:class:` cross-references;
(4) prune the `rulepack.detect` scan-shape re-export (Decision D-PRUNE) and pin
it with a unit test, with a documented retain-fallback (D-PRUNE-FALLBACK). Scope
is fenced against neighbouring tasks 7.2.3.1 (guard generalisation), 7.2.3.2 and
7.8.1 (the `line_hit` callback rationale and retirement), and 7.8.2 (the
scan-aggregate skeleton and `count` return). No external-library behaviour is
load-bearing; the only tool behaviour relied on (Ruff TC001, `ty`) is pinned by
the gates rather than asserted.

## Addenda

Small, surgical corrections accrued after this task settled. Each runs as a
lightweight, no-plan, no-review addendum pass.

- [x] 7.2.4.1 (from review:7.2.4; low). Note that `LineHit` survives as an
  unadvertised runtime attribute of `rulepack.detect`. Post-prune,
  `hasattr(rulepack.detect, "LineHit")` is `True` even though `LineHit` is absent
  from `__all__`, because the detector constructs it at runtime in the `line_hit`
  lambda (Decision D-LINEHIT-RUNTIME above). This is intentional and test-pinned
  (`test_detect_no_longer_reexports_scan_shapes` asserts `LineHit` absent from
  `__all__`, not absent as an attribute), so a future reader could mistake the
  surviving attribute for an incomplete prune. Add a one-line note to the
  developers' guide `loaderkit` section (`docs/developers-guide.md`, "The shared
  loader primitives (`loaderkit`)") recording that `LineHit` remains an
  importable-but-unadvertised `rulepack.detect` attribute by design. Doc-only;
  run `make markdownlint` and `make nixie`.
