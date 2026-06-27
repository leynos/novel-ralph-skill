# Logisphere design review — roadmap 7.2.3 (round 2)

Verdict: REVISE (one narrow, concrete defect). The round-1 blocker (B1, the Ruff
TC001 lint gate) and both round-1 advisories (A1 AST-scoped guard, A2
docstring single-home meaning) are now correctly and exhaustively resolved and
verified against source. One new defect remains: Work item 3's docstring
acceptance grep is factually wrong and will report "fail" on a correct
implementation, risking out-of-scope churn. It is cheap to fix.

## Round-1 fixes — verified resolved

- **B1 (TC001 on `ScannedChapter`) — RESOLVED.** Verified against source:
  after Work item 1 removes `class ScannedChapter` (`rulepack/detect.py:43`)
  and Work item 3 deletes `_scan_rule` (lines 149-178), `ScannedChapter`'s only
  remaining reference in the module is the `detect` parameter annotation
  (line 238) plus docstrings — all strings under
  `from __future__ import annotations`, so TC001 fires. The plan now *mandates*
  the `# noqa: TC001 - runtime re-export for _desloppify` form (D-REEXPORT
  revised, Work item 1 step 3) and a committed module `__all__`. The precedent
  is real: `commands/novel_state.py` carries
  `# noqa: TC001 - runtime global for Cyclopts annotation resolution`, and
  `ledger/detect.py:35,41` already splits a runtime `LineHit` import from a
  `TYPE_CHECKING` `ScannedChapter` import for exactly this reason. The plan's
  claim that `LineHit` needs **no** `# noqa` also holds: `LineHit` is
  constructed at runtime by the `_scan_rule` lambda (line 177) through Work
  item 1, then by the inlined lambda at Work item 3 — a genuine runtime use at
  every commit boundary, so a `# noqa` on it would itself trip RUF100. The
  "lint posture stable across the Work item 1 → 3 boundary" reasoning is
  correct. Ruff 0.15.18 and ty 0.0.51 confirmed in `uv.lock`; the TC001 doc URL
  is cited.

- **A1 (AST-scoped guard) — RESOLVED.** D-GUARD (revised) now mandates an
  `ast.parse` walk inspecting only `ast.Import`/`ast.ImportFrom` nodes, with a
  concrete en-GB test sketch
  (`test_loaderkit_scan_imports_no_pack_domain`). This correctly avoids the
  false positive from `scan_pattern`'s docstring, which legitimately
  cross-references `:class:~novel_ralph_skill.rulepack.detect.LineHit`
  (`scan.py:13`) and names `rule`/`device` in prose.

- **A2 (docstring single-*home* vs single-*occurrence*) — PARTIALLY
  RESOLVED.** The plan now states "single-stated means a single *home module*,
  not a single textual occurrence" and accepts that `scan.py`'s module
  docstring (line 6) and `scan_pattern`'s function docstring (line 42) both
  legitimately carry "cannot cross". Good. But the revised acceptance grep is
  still wrong — see ADVISORY-as-BLOCKING below.

## BLOCKING

### A2-residual — Work item 3 acceptance grep returns two paths, not one

Work item 3's acceptance check (plan lines 740-741) states:

> `grep -rln "cannot cross" novel_ralph_skill/` ... returns **exactly one
> path** — `novel_ralph_skill/loaderkit/scan.py`

This is factually false against the current tree. `grep -rln "cannot cross"
novel_ralph_skill/` today returns **three** files; after Work item 3 trims the
two detector module docstrings (`rulepack/detect.py:13`, `ledger/detect.py:13`)
and deletes `_scan_device` (which carries "cannot cross" at
`ledger/detect.py:115`), it returns **two**:

- `novel_ralph_skill/loaderkit/scan.py` (intended — the single home), and
- `novel_ralph_skill/loaderkit/load.py:139` — a wholly separate primitive
  (`compile_pattern`, roadmap 5.1.1) whose docstring legitimately says
  "no flags means `.` cannot cross `\n`". `load.py` is **not** in this plan's
  edit scope (the plan names it only in orientation prose at line 395 as one of
  loaderkit's modules).

So an implementer who runs the literal acceptance check on a *correct*
implementation sees it "fail" with two hits. The hazard is real: to make the
check pass they may either (a) burn fix attempts hunting a non-existent extra
duplicate, or (b) wrongly edit `load.py`'s unrelated, out-of-scope docstring —
scope creep the Tolerances forbid. This is the same defect class round 1 raised
as A2 (acceptance grep too tight); the revision fixed the *intra-`scan.py`*
double-count but missed the unrelated `load.py` occurrence.

Required fix (any one):

- Scope the grep to the de-duplication target only, e.g.
  `grep -rln "cannot cross" novel_ralph_skill/rulepack/detect.py
  novel_ralph_skill/ledger/detect.py` returns **nothing** (the rationale is
  gone from both detector module docstrings), and separately assert
  `loaderkit/scan.py` retains it; or
- Re-state the acceptance as: after Work item 3, neither `rulepack/detect.py`
  nor `ledger/detect.py` re-states the per-line rationale (each only references
  `scan_pattern`), and `loaderkit/scan.py` remains the sole *detector-rationale*
  home — explicitly acknowledging `load.py` carries the unrelated
  *compile-time* phrasing of the same `.`/`\n` fact and is untouched.

## Crew notes

- **Pandalump 🐼:** Structural verdict unchanged and sound. Post-move direction
  `rulepack.detect → loaderkit.scan` and `ledger.detect → loaderkit.scan` is
  acyclic (loaderkit imports nothing back; `loaderkit/__init__.py:20-24`
  confirms the neutral-leaf invariant). The re-export keeps `rulepack.detect` a
  compatibility seam without re-coupling loaderkit upward. D-GUARD pins it.
- **Telefono ☎️:** ADR-003 frozen contract respected. `RuleFinding`/
  `DetectionReport` stay in `rulepack.detect` and keep referencing `LineHit`
  (verified lines 103-116); only the definition site moves. The `line_hit`
  callback contract (Work item 4) is the correct seam to pin; the
  recording-double test (`sentinel`/`calls == [(3,1),(3,2),(3,2),(7,1)]`) is
  well-formed and matches `scan_pattern`'s actual two-loop structure
  (`scan.py:65-69`).
- **Doggylump 🐶:** Pre-mortem failure path is the acceptance-check trap above,
  not runtime — behaviour is provably unchanged (verbatim shape move, re-export,
  and identical inlined lambda). No 03:00 page; the worst case is an implementer
  misled by the bad grep into editing `load.py`.
- **Wafflecat 🐈🧇:** Strongest alternative remains "repoint
  `commands/_desloppify.py` + the three rule-pack/ledger tests at
  `loaderkit.scan` directly and drop the re-export," which removes the seam and
  the `# noqa` cost — but enlarges the diff past the two detectors + one unit
  test the roadmap names, and roadmap 7.2.3's Success criterion forbids only the
  `ledger.detect`/`loaderkit.scan` imports *from* `rulepack.detect`, not a
  backward-compatible re-export. The plan's re-export is the right, minimal,
  idempotent choice; it carries the now-mandated `# noqa`/`__all__` cost B1
  named.
- **Buzzy Bee 🐝 / Dinolump 🦕:** No scaling or long-term-viability concern. A
  pure relocation that reduces coupling and cognitive load.

## Cuprum / locked-library check

D-NO-CUPRUM verified by reading every touched module: `loaderkit/scan.py`,
`rulepack/detect.py`, `ledger/detect.py`, `rulepack/_coerce.py` — none builds a
cuprum catalogue, spawns a subprocess, or parses CLI flags; the shapes are plain
`dataclasses`. No Cyclopts/uv/pytest-timeout behaviour is in scope, so the
"cite-or-pin locked-library claims" rule reduces to the single Ruff TC001 claim,
which the plan cites (official docs URL) and anchors to a proven in-repo
precedent. Ruff 0.15.18 / ty 0.0.51 pins confirmed in `uv.lock`. No
memory-based locked-library claim survives uncited.

## Source verified

`loaderkit/scan.py`, `loaderkit/load.py:139`, `loaderkit/__init__.py`,
`rulepack/detect.py` (all `ScannedChapter`/`LineHit` refs),
`rulepack/_coerce.py:55` (`_require` dead, single occurrence),
`ledger/detect.py:13,35,41,110-130`, `commands/_desloppify.py:57,164,204`,
`commands/_desloppify_report.py:35` (imports `DetectionReport`/`RuleFinding`
only), `commands/novel_state.py` (TC001 idiom precedent),
`tests/test_loaderkit_scan.py:21`, `tests/test_ledger_detect.py:27`,
`tests/test_ledger_properties.py:40`, `pyproject.toml` Ruff select, `uv.lock`
(ruff/ty pins), `docs/roadmap.md` 7.2.3, `docs/developers-guide.md`
1704/1724-1736.

## Trail

Design docs: `docs/novel-ralph-harness-design.md` §6/§6.1/§6.3;
`docs/adr-001-*`, `docs/adr-003-shared-interface-contract.md`;
`docs/developers-guide.md` "The shared loader primitives"; `docs/roadmap.md`
7.2.3; `docs/execplans/roadmap-7-2-2.md` (D-SCANTYPES);
`docs/execplans/roadmap-7-2-3.review-r1.md`. Skills: leta, sem,
logisphere-design-review, python-router (python-data-shapes,
python-types-and-apis), arch-crate-design.
