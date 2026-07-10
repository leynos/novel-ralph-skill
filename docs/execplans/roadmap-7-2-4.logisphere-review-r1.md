# Logisphere design review — roadmap 7.2.4 (Round 1)

Reviewer: adversarial Logisphere crew. Plan under review:
`docs/execplans/roadmap-7-2-4.md` (DRAFT, 2026-06-27).

## Verdict: PROCEED (no blocking defects)

Every load-bearing factual claim in the plan was verified against the real
source tree in this worktree (not the planner's summary). The inventory is
exhaustive and correct, the work-item ordering keeps the tree green at every
commit boundary, the deterministic/judgemental boundary (ADR-001) and the frozen
rule-pack contract (ADR-003) are untouched, and the prune decision (D-PRUNE) is
explicitly authorized by audit-7.2.3 Finding 1 and corroborated by a fresh
whole-repo grep showing no out-of-tree consumer.

One **advisory** correction (rationale imprecision under PEP 563) and a couple
of minor robustness improvements are listed below. None change the operative
outcome, so none block.

## Verification performed (claim → evidence)

- `rulepack/detect.py:29-33` runtime import of `LineHit, ScannedChapter,
  scan_pattern`; `__all__` (41-47) = `DetectionReport, LineHit, RuleFinding,
  ScannedChapter, detect`. **Confirmed verbatim.**
- The four straggler importers (`_desloppify.py:57`, `test_ledger_detect.py:27`,
  `test_ledger_properties.py:40`, `test_rulepack_detect.py:24`) and the three
  genuine-contract importers (`_desloppify_report.py:35`,
  `test_desloppify_report.py:20`, `test_desloppify_finding_message.py:17`).
  **Confirmed exactly** by `grep -rn "from novel_ralph_skill.rulepack.detect
  import"`.
- The four stale `:class:` Sphinx refs (`ledger/__init__.py:14`,
  `_desloppify.py:188`, `test_ledger_detect.py:8`,
  `test_desloppify_sourcing.py:5`). **Confirmed exactly.** `ledger/detect.py`
  already points at `loaderkit.scan` (do-not-touch). **Confirmed.**
- `LineHit` genuine runtime use at `detect.py:212` (the `line_hit` lambda).
  **Confirmed.** `ScannedChapter` appears only at import (31), `__all__` (45),
  the `detect` param annotation (180), and the docstring (198) — **no runtime
  construction in this module. Confirmed**, so the TYPE_CHECKING move is sound.
- `_desloppify.py:204` constructs `ScannedChapter` at runtime → stays a runtime
  import. **Confirmed.**
- Both ledger tests construct `ScannedChapter` at runtime
  (`test_ledger_properties.py:181`, `test_ledger_detect.py:82+`) despite
  `from __future__ import annotations`, so the plain runtime repoint is correct
  and will not trip TC001. **Confirmed.**
- `test_rulepack_detect.py` uses both `LineHit` (128-129, 146-147, 204) and
  `ScannedChapter` (73+) at runtime, so the plan's split keeps both as runtime
  imports from `loaderkit.scan`. **Confirmed correct.**
- `loaderkit/__init__.py:48-55` re-exports both shapes (alternative neutral
  source). **Confirmed.**
- Ruff `TC` family is selected in `pyproject.toml:48` (the plan says "TC001";
  the config selects the whole family, which subsumes TC001). **Confirmed.**
- `docs/developers-guide.md` contains **no** `rulepack.detect.ScannedChapter`
  reference, so the plan's "edit only if needed (none currently)" is correct.
  **Confirmed** (`grep` returns nothing).
- No `console_scripts`/packaging surface exposes `rulepack.detect`. Whole-repo
  grep (code + docs, excluding execplans/issues) shows every neutral-shape
  reach-through is one of the eight enumerated sites — the four straggler imports
  and the four stale `:class:` Sphinx refs. **The single-application-package
  premise of D-PRUNE holds; no external consumer exists. Confirmed.**

## Panel findings

### Pandalump (structural integrity) — lead

Dependency direction is the entire point of the task and it is correct: imports
move *toward* the neutral `loaderkit` leaf; nothing creates an edge *out of*
`loaderkit`. The `ledger → rulepack` and `command → rulepack` detection-shape
edges are genuinely removed. `__all__` after the prune (`DetectionReport`,
`RuleFinding`, `detect`) advertises exactly what the module defines — boundary
and ownership now coincide. No god object, no circular dependency introduced.
🟢 Sound.

### Telefono (contracts / `__all__` surface) — lead

ADR-003's frozen contract (`DetectionReport`/`RuleFinding`/`detect`) is preserved
in name, signature, and export. The pinning test asserts set-equality of
`__all__` plus `not hasattr` for the two shapes — both the additive-safety and
the removal are pinned, so the surface cannot silently re-fork or regress.
🟢 Sound. 🟢 (improvement) The `not hasattr` assertion also guards against a
future module-level `from loaderkit.scan import ScannedChapter` creeping back
even if it were dropped from `__all__`; good defensive choice.

### Doggylump (failure modes) — prune blast radius

Worst case: a missed importer breaks at import time. Mitigated three ways —
(1) exhaustive grep inventory, independently reproduced in this review;
(2) ordering (all importers repointed in WI1 before the WI4 prune);
(3) `make all` runs the full suite, so any miss fails loudly at the WI1 or WI4
gate. The D-PRUNE-FALLBACK retain-path is documented with its own test form and
an explicit escalation trigger (Tolerances). Blast radius is bounded to import
time within a single in-tree package; no data, no migration, no runtime-behaviour
change. 🟢 Sound.

### Buzzy Bee (scaling) / Dinolump (long-term viability)

No load, latency, or cost dimension. Cognitive-load impact is *positive*: one
type now has one import home instead of three, reducing the concepts a maintainer
juggles. Bus-factor neutral. 🟢 Nothing to flag.

### Wafflecat (alternatives) — checkpoint

The credible alternative is **retain the re-export as a documented compatibility
forwarder** (audit Finding 1's other branch, captured as D-PRUNE-FALLBACK).
Trade-off: retain keeps a third import source alive and re-advertises rule-pack
ownership of neutral shapes — the precise impression Finding 3 says is no longer
warranted. Prune is the design-aligned single-home outcome, and the evidence
(no external consumer) removes the only reason to prefer retain. The plan picks
prune *and* keeps retain as a tripwire-guarded fallback. This is the right
calibration; no stronger alternative exists for an internal-only package.

## Pre-mortem (Doggylump)

Six months on, the only plausible incident is "the prune broke a consumer the
inventory missed." Working backwards: the signal would be a red `make all` at the
WI1 or WI4 commit gate (caught pre-merge, never reaching production), and the
prevention is already designed in — repoint-before-prune ordering plus the
full-suite gate plus the fallback. No 03:00 page is reachable from this change.
The second, milder scenario: the new pinning test is *itself* wrong (e.g. it
asserts a stale `__all__`). Mitigated by the red→green protocol in Concrete
steps (the test must fail pre-prune and pass post-prune), which proves the test
actually discriminates.

## Advisory findings (non-blocking)

1. 🟡 **Rationale imprecision in the Risk note and D-LINEHIT-RUNTIME (does not
   change the outcome).** The plan justifies keeping `LineHit` as a runtime
   import partly by claiming the `RuleFinding`/`DetectionReport` field
   annotations (`lines: tuple[LineHit, ...]` at `detect.py:90,127`) are "read at
   class-build time via the slotted dataclass." Under `from __future__ import
   annotations` (PEP 563), **field annotations are strings and are not
   evaluated** at class-build time; a slotted dataclass derives `__slots__` from
   `__annotations__` *keys*, not from evaluating the annotation *values*. The
   **actual and sufficient** reason `LineHit` must stay runtime is the genuine
   constructor call in the lambda at `detect.py:212`. The conclusion (LineHit
   runtime, ScannedChapter → TYPE_CHECKING) is correct; only the supporting
   sentence is technically wrong. Recommend trimming the field-annotation clause
   so the rationale rests solely on the line-212 runtime construction, to avoid
   propagating a PEP 563 misconception into the codebase comments.

2. 🟢 **Tighten the Sphinx-ref grep guard.** The Validation grep
   `:class:.*rulepack.detect.ScannedChapter\b` uses an unescaped `.` for the
   dots, so it would also match e.g. `rulepackXdetectXScannedChapter` — harmless
   here (no such string exists) but consider `rulepack\.detect\.ScannedChapter`
   for precision. Optional.

3. 🟢 **WI4 pinning test could additionally assert the contract names are
   importable**, not only that they remain in `__all__`. The plan argues
   (correctly) that the existing cases already import and exercise
   `detect`/`DetectionReport`/`RuleFinding` from `rulepack.detect`, so the green
   suite proves survival. Acceptable as written; an extra `import` assertion in
   the new test would make the "contract survives" guarantee self-contained
   rather than distributed across the file. Optional.

## Scope / standing-rules conformance

- en-GB Oxford spelling observed throughout the plan prose. ✔
- 400-line file cap: the change only removes lines from `detect.py` and edits
  import lines elsewhere; cannot breach the cap. ✔
- No external-library behaviour is load-bearing; the plan correctly declines to
  cite cuprum/Cyclopts/pytest-timeout/uv and pins the only tool dependency
  (Ruff TC, `ty`) with the actual gate. ✔ (Verified: no such API is touched.)
- Neighbouring-task scope fences (7.2.3.1, 7.2.3.2/7.8.1 Finding 2, 7.8.2) are
  explicit and correct; Finding 2 is properly excluded. ✔

## Trail for the next agent

Docs consulted: `docs/execplans/roadmap-7-2-4.md`,
`docs/issues/audit-7.2.3.md` (Findings 1, 2, 3), `docs/roadmap.md` (task 7.2.4),
`docs/adr-001`, `docs/adr-003`. Source verified:
`rulepack/detect.py`, `loaderkit/__init__.py`, `commands/_desloppify.py`,
`ledger/__init__.py`, `ledger/detect.py`, and the four test modules.
Skills: `logisphere-design-review`. Lens weighting: Pandalump + Telefono lead
(boundary + `__all__` contract), Doggylump on the prune blast radius.
