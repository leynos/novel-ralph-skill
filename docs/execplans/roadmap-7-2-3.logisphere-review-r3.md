# Logisphere design review — roadmap 7.2.3 (round 3)

Verdict: REVISE. The round-1 blocker (B1, Ruff TC001) and round-2 blocker
(A2-residual, the whole-tree `load.py` double-count) are correctly resolved and
verified against source. One **new** defect survives, in the same Work item 3
acceptance machinery the last two rounds churned: the scoped grep the plan now
mandates for `rulepack/detect.py` is **vacuous** — it returns "nothing" today,
before any edit, so it cannot prove the de-duplication actually happened. The
plan also carries a factually false evidence claim built on the same mistake.
Both are cheap to fix.

## Prior-round fixes — verified resolved against source

- **B1 (TC001 on `ScannedChapter`) — RESOLVED.** Verified: `_desloppify.py:204`
  constructs `ScannedChapter` at runtime (so the import in `rulepack/detect.py`
  must stay runtime/module-top), while after Work item 3 inlines `_scan_rule`
  the only remaining `ScannedChapter` reference in `rulepack/detect.py` is the
  `detect` parameter annotation (line 238) — a string under
  `from __future__ import annotations`, so TC001 fires. The mandated
  `# noqa: TC001 - runtime re-export for _desloppify` plus committed `__all__`
  is the right fix, and the precedent is real and exact:
  `commands/novel_state.py:53` carries
  `# noqa: TC001 - runtime global for Cyclopts annotation resolution`.
  `LineHit` needs no `# noqa` (constructed at runtime by the inlined lambda).
  `rulepack/detect.py` has **no** `__all__` today, so D-REEXPORT correctly
  introduces one. Ruff 0.15.18 / ty 0.0.51 pins and the TC001 doc URL are cited.

- **A1 (AST-scoped guard) — RESOLVED.** D-GUARD (revised) mandates an
  `ast.parse` walk over `ast.Import`/`ast.ImportFrom` nodes only, with a concrete
  en-GB test sketch. Correct: `scan_pattern`'s docstring legitimately
  cross-references `:class:~novel_ralph_skill.rulepack.detect.LineHit`
  (`scan.py:13`) and names `rule`/`device`, so a substring guard would
  false-positive; the AST scoping pins exactly the load-bearing import edge.

- **A2-residual (whole-tree `load.py` double-count) — RESOLVED.** The plan no
  longer uses the whole-tree `grep -rln "cannot cross" novel_ralph_skill/`
  "exactly one path" check. `load.py:139` is correctly named as the unrelated
  out-of-scope `compile_pattern` (roadmap 5.1.1) occurrence and the acceptance is
  scoped to the two detector files. The *direction* of the round-2 fix is right.

## BLOCKING

### B2 — Work item 3 acceptance grep is vacuous for `rulepack/detect.py`

The round-3 acceptance (plan lines 794-795; mirrored in Decision D-DOCSTRING and
the Surprises section) states:

> **De-dup targets cleared:**
> `grep -rln "cannot cross" novel_ralph_skill/rulepack/detect.py novel_ralph_skill/ledger/detect.py`
> returns **nothing**.

Against the actual source this check is non-functional for `rulepack/detect.py`,
because the phrase `cannot cross` is **line-wrapped** in that file and a
single-line `grep` for `"cannot cross"` never matches it — today, or after any
edit:

- `rulepack/detect.py:13` ends with `... so ``.`` cannot` and line 14 begins
  with `cross ``\n``; ...` (module docstring).
- `rulepack/detect.py:157` ends with `... requires: ``.`` cannot` and line 158
  begins with `cross ``\n``, ...` (`_scan_rule` docstring).

Live evidence (run in the worktree):

```console
$ grep -rln "cannot cross" novel_ralph_skill/rulepack/detect.py ; echo "exit $?"
exit 1            # no match — the file is NOT listed

$ grep -rln "cannot cross" novel_ralph_skill/
novel_ralph_skill/loaderkit/load.py
novel_ralph_skill/ledger/detect.py
novel_ralph_skill/loaderkit/scan.py
                  # rulepack/detect.py is absent
```

Consequences, both real:

1. **False green.** The `rulepack/detect.py` half of the de-dup acceptance
   passes whether or not the implementer trims the rule-pack rationale. The
   rationale that Work item 3 is meant to remove lives in the **module
   docstring** (`rulepack/detect.py:11-22` — "Detection scans line by line ...
   so ``.`` cannot cross ``\n``; splitting each chapter into physical lines ...
   makes line numbers exact, bounds every match to a single line ...") and in
   the `_scan_rule` docstring (157-158, deleted by inlining). An implementer can
   delete `_scan_rule`, leave the full module-docstring rationale in place
   (violating D-DOCSTRING and the roadmap's "de-duplicate the triple-stated
   per-line scan docstring"), and the grep still reports "nothing" → green. The
   acceptance cannot detect the very omission it exists to catch.

2. **False evidence in the plan.** The Surprises section (lines 222-225) asserts
   `grep -rn "cannot cross" novel_ralph_skill/` "finds the phrase in ... and
   `rulepack/detect.py:157-158` carries it in the `_scan_rule` wrapper
   docstring". The live `grep -rn "cannot cross" novel_ralph_skill/` returns only
   `loaderkit/load.py`, `ledger/detect.py` (×2), and `loaderkit/scan.py` (×2) —
   `rulepack/detect.py` is not in the output. The plan's stated grep evidence is
   wrong for the rule-pack file, which is how the vacuous acceptance slipped in.

Note this is the *opposite* failure mode to round 2: round 2's grep returned a
spurious **extra** path (`load.py`) and risked over-editing; this one returns a
spurious **missing** path (`rulepack/detect.py`) and risks under-editing. The
`ledger/detect.py` half of the same check is fine — there `cannot cross` is
single-line at lines 13 and 115, so the grep is a genuine before/after signal.

Required fix (any one; all cheap):

- **Make the rule-pack check wrap-insensitive.** Assert the *rationale words* are
  gone regardless of line-wrapping, e.g. for each of `rulepack/detect.py` and
  `ledger/detect.py` confirm the file no longer contains both `cannot` and
  `cross` adjacent across whitespace — e.g.
  `grep -Pzoc "cannot[\s`*.:]*\n?[\s`*.:]*cross" <file>` returns `0`, or simply
  collapse-then-grep:
  `tr "\n" " " < <file> | tr -s " " | grep -c "cannot cross"` returns `0`.
  (Whichever form, it must catch the wrapped occurrence the plain grep misses.)
- **Or assert on the surviving reference instead.** Re-state the acceptance as a
  positive structural check: after Work item 3, `rulepack/detect.py`'s module
  docstring contains a `scan_pattern` reference and no longer states the
  `splitlines`/`line numbers exact`/`bounds every match` rationale, while
  `loaderkit/scan.py` retains it. (The plan already adds a `scan_pattern`
  positive check at lines 805-807 — promote that to the *primary* de-dup signal
  for `rulepack/detect.py`, since the "cannot cross" grep cannot serve there.)
- **At minimum**, correct the Surprises evidence (lines 222-225) so it does not
  claim a grep hit in `rulepack/detect.py` that does not exist, and flag that the
  rule-pack rationale is line-wrapped so the plain grep is not a valid acceptance
  for that file.

This is blocking because an acceptance check that passes on a non-conformant
implementation is worse than no check: it actively certifies the unfinished
work. The roadmap names docstring de-duplication as in-scope; the plan must be
able to verify it landed for *both* detectors, not just the ledger.

## Crew notes

- **Pandalump 🐼:** Structural verdict unchanged and sound. Post-move direction
  `rulepack.detect → loaderkit.scan` and `ledger.detect → loaderkit.scan` is
  acyclic; `loaderkit/__init__.py:22-23` confirms loaderkit imports neither pack.
  The re-export keeps `rulepack.detect` a compatibility seam without re-coupling
  loaderkit upward. D-GUARD (AST-scoped) pins it. No structural defect.
- **Telefono ☎️:** ADR-003 frozen contract respected — `RuleFinding` /
  `DetectionReport` stay in `rulepack.detect` and keep referencing `LineHit`
  (verified, fields at 103/116); only the definition site moves. The Work item 4
  recording-double contract test is well-formed and matches `scan_pattern`'s
  two-loop structure (`scan.py:64-70`): `calls == [(3,1),(3,2),(3,2),(7,1)]`,
  `count == 4`, every hit `is sentinel`. Correct seam to pin.
- **Doggylump 🐶:** Pre-mortem failure path is again an acceptance-check trap,
  not runtime — behaviour is provably unchanged (verbatim shape move, re-export,
  identical inlined lambda, and dead-code deletion). The worst case is B2: an
  implementer trusts the green grep and ships an un-trimmed rule-pack module
  docstring, leaving the "triple-stated" duplication the roadmap targets only
  *double*-removed. No 03:00 page; a correctness-of-acceptance defect.
- **Wafflecat 🐈🧇:** Strongest alternative is still "repoint
  `commands/_desloppify.py` + the three rule-pack/ledger tests at `loaderkit.scan`
  and drop the re-export," removing the seam and the `# noqa`. It enlarges the
  diff past the two detectors + one unit test the roadmap names and is not
  required by the Success criterion. The re-export remains the right minimal
  choice. For B2 specifically, the cheaper alternative to a wrap-insensitive grep
  is simply to make the *positive* `scan_pattern`-reference check the primary
  de-dup acceptance (the plan already half-states it).
- **Buzzy Bee 🐝 / Dinolump 🦕:** No scaling or long-term-viability concern; a
  pure relocation that reduces coupling and cognitive load.

## Cuprum / locked-library check

D-NO-CUPRUM re-verified by reading every touched module (`loaderkit/scan.py`,
`rulepack/detect.py`, `ledger/detect.py`, `rulepack/_coerce.py`): none builds a
cuprum catalogue, spawns a subprocess, or parses CLI flags; the shapes are plain
`@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)`. No
Cyclopts/uv/pytest-timeout behaviour is in scope, so the cite-or-pin rule reduces
to the single Ruff TC001 claim, which the plan cites (official docs URL) and
anchors to the proven in-repo precedent (`novel_state.py:53`). Ruff 0.15.18 / ty
0.0.51 confirmed pinned (`uv.lock`). No memory-based locked-library claim
survives uncited.

## Source verified (this round)

`loaderkit/scan.py` (TYPE_CHECKING edge at line 28, docstring cross-ref at 13),
`loaderkit/__init__.py` (`__all__`, no pack import, lines 22-23/45-59),
`loaderkit/load.py:139` (out-of-scope `compile_pattern` occurrence),
`rulepack/detect.py` (full read; `cannot`/`cross` wrapped at 13-14 and 157-158;
no `__all__`; `_scan_rule` lambda at 177; `detect` param annotation at 238),
`rulepack/_coerce.py:55` (`_require` dead — single occurrence, no caller),
`ledger/detect.py:13,35,41,108-135` (`cannot cross` single-line at 13/115,
runtime `LineHit` import at 35, TYPE_CHECKING `ScannedChapter` at 41,
`_scan_device` lambda at 134), `commands/_desloppify.py:57,164,204` (runtime
`ScannedChapter` import and construction), `commands/novel_state.py:50-54`
(TC001 idiom precedent). Live greps for `cannot cross` (single-line vs wrapped)
and `_require` run in the worktree.

## Trail

Design docs: `docs/novel-ralph-harness-design.md` §6/§6.1/§6.3;
`docs/adr-001-*`, `docs/adr-003-shared-interface-contract.md`;
`docs/developers-guide.md` "The shared loader primitives";
`docs/roadmap.md` 7.2.3; `docs/execplans/roadmap-7-2-2.md` (D-SCANTYPES);
`docs/execplans/roadmap-7-2-3.review-r1.md`,
`docs/execplans/roadmap-7-2-3.logisphere-review-r2.md`. Skills: leta, sem,
logisphere-design-review, python-router (python-data-shapes,
python-types-and-apis), arch-crate-design.
