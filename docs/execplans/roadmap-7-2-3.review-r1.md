# Logisphere design review — roadmap 7.2.3 (round 1)

Verdict: REVISE. The plan is structurally sound and design-conformant in its
intent, but D-REEXPORT contains a concrete lint-gate defect that will stop
`make all` as written, and two secondary gaps need tightening before
implementation.

## Verified against source (claims that hold)

- `loaderkit/scan.py` defines `scan_pattern`, references the shapes only under
  `TYPE_CHECKING` (line 28), and carries the D-SCANTYPES docstring. Removing
  that edge is correct and central.
- `ledger/detect.py` runtime-imports `LineHit` (line 35) and TYPE_CHECKING-imports
  `ScannedChapter` (line 41) from `rulepack.detect`. Line numbers match the plan.
- `rulepack/detect.py` defines both shapes (lines 42-74); `LineHit` is referenced
  by `RuleFinding.lines` and constructed by the `_scan_rule` lambda.
- Dead-code claim holds: `rulepack/_coerce.py:55` `_require` has no caller, and
  `require` (imported from `loaderkit.coerce`) is consumed only by `_require`, so
  deleting `_require` leaves `require` an unused F401 import — the plan
  anticipates this. The ledger's `_require` is genuinely live
  (`ledger/_fields.py:22,94`), so only the rule-pack copy is dead.
- Importer enumeration is complete for *import* sites. `test_desloppify_sourcing.py`
  mentions `ScannedChapter` only in a docstring (imports from `_desloppify`), so
  the re-export covers it. No behavioural/steps test imports the shapes.
- Developers' guide §1724-1728 says exactly "still defined in `rulepack/detect.py`"
  and references the TYPE_CHECKING edge; the test-pin sentence (§1735-1736)
  exists. Work item 5's edit targets are real.

## BLOCKING

### B1 — D-REEXPORT will fail `make lint` (Ruff TC001) on `ScannedChapter`

After Work item 1 (move definition out) and Work item 3 (inline `_scan_rule`,
deleting lines 149-178), the only remaining `ScannedChapter` references inside
`rulepack/detect.py` are annotations (`detect`'s `chapters` param, line 238, and
its docstring). Under `from __future__ import annotations` those annotations are
strings, so `ScannedChapter` has **zero runtime use** in the module. But
D-REEXPORT requires it as a **runtime, module-top** import because
`commands/_desloppify.py:57` does `from novel_ralph_skill.rulepack.detect import
ScannedChapter` at runtime and constructs it (line 204).

Ruff `TC` is selected (`pyproject.toml:48`) and is enforced: the codebase already
carries `# noqa: TC001 - runtime global for Cyclopts annotation resolution` at
`commands/novel_state.py:53` for exactly this situation, and `ledger/detect.py`
deliberately splits its runtime `LineHit` import from its TYPE_CHECKING
`ScannedChapter` import to satisfy TC. A bare top-level `import ScannedChapter`
used only in annotations therefore trips **TC001**, and `make lint` fails.

The plan's D-REEXPORT and Work item 1 step 3 present `__all__` as *optional*
("If `rulepack/detect.py` has or gains an `__all__`, include both names …;
otherwise the module-level import suffices"). It does **not** suffice for
`ScannedChapter`. An implementer following the plan literally hits the lint gate
and burns the "3 fix attempts then escalate" tolerance on a defect the plan
should have pre-resolved.

Required fix: the plan must *mandate* the codebase's established idiom for a
runtime-needed annotation-only re-export — an explicit `# noqa: TC001` with a
rationale comment (mirroring `novel_state.py:53`), and/or a committed module
`__all__` listing both names — and state it for `ScannedChapter` specifically.
`LineHit` is unaffected (the inlined `detect` lambda is a genuine runtime use).
Verify the chosen mechanism actually silences TC001 under the locked Ruff before
declaring the work item done.

## ADVISORY

### A1 — D-GUARD test must scope to import statements, not whole-file substring

Work item 1 specifies the guard test reads `loaderkit/scan.py` source and asserts
neither `"rulepack"` nor `"ledger"` appears "in an `import` statement" — correct
in words, but the suggested implementations (`inspect.getsource` /
`Path(...).read_text()` then substring search) are whole-file. After the docstring
rewrite the module docstring should be clean, but `scan_pattern`'s own docstring
still names "rule"/"device" (`rule.compiled`/`device.compiled`). Pin the assertion
to lines beginning with `import`/`from` (or parse with `ast` and inspect
`Import`/`ImportFrom` nodes) so a future legitimate docstring mention of a pack
name cannot cause a false failure. State this in the plan so the implementer does
not write the blunt version.

### A2 — D-DOCSTRING acceptance grep is too tight

Work item 3's acceptance says `grep -rn "cannot cross" novel_ralph_skill/`
resolves to a single authoritative statement in `loaderkit/scan.py`. But
`scan_pattern`'s docstring already states the rationale twice (module docstring
lines 6-8 *and* the function docstring lines 42-43), and both legitimately survive.
Clarify whether "single-stated" means one *module* (loaderkit/scan.py) or one
*occurrence*; as worded the grep would return at least two hits inside scan.py and
fail a literal reading of the acceptance check.

## Crew notes (non-blocking)

- Pandalump 🐼: dependency direction after the move (`rulepack.detect →
  loaderkit.scan`, `ledger.detect → loaderkit.scan`, both acyclic) is correct and
  is the right load-bearing wall. The re-export keeps `rulepack.detect` as a
  compatibility seam without re-coupling loaderkit upward. Sound.
- Telefono ☎️: ADR-003 frozen contract is respected — `RuleFinding`/`DetectionReport`
  stay in `rulepack.detect` and keep referencing `LineHit`; only the definition
  site moves. The `line_hit` callback contract (Work item 4) is the right seam to
  pin and the recording-double test is well-formed.
- Doggylump 🐶: pre-mortem failure path is the lint gate (B1), not runtime —
  behaviour is provably unchanged (re-export + verbatim move + inlined identical
  lambda). The D-GUARD test is the guard against silent re-forking; make it
  import-scoped (A1) so it does not become a flaky tripwire.
- Wafflecat 🐈🧇: the strongest alternative is to *not* re-export from
  `rulepack.detect` and instead repoint `commands/_desloppify.py` and the three
  rule-pack/ledger tests at `loaderkit.scan` directly. That removes the seam (and
  B1 with it) but enlarges the diff beyond the two detectors + one unit test the
  roadmap names, and roadmap 7.2.3 only forbids the `ledger.detect`/`loaderkit.scan`
  imports *from* `rulepack.detect`, not a backward-compatible re-export. The plan's
  re-export choice is defensible; it just must carry the `noqa`/`__all__` cost B1
  identifies.
- Buzzy Bee 🐝 / Dinolump 🦕: no scaling or long-term-viability concern; this
  is a pure relocation that reduces coupling and cognitive load. Good for the
  team.

## Trail

Design docs: `docs/novel-ralph-harness-design.md` §6/§6.1/§6.3;
`docs/adr-001-*`, `docs/adr-003-shared-interface-contract.md`;
`docs/developers-guide.md` "The shared loader primitives"; `docs/roadmap.md`
7.2.3; `docs/execplans/roadmap-7-2-2.md` (D-SCANTYPES). Source verified:
`loaderkit/scan.py`, `loaderkit/__init__.py`, `rulepack/detect.py`,
`rulepack/_coerce.py`, `rulepack/__init__.py`, `ledger/detect.py`,
`commands/_desloppify.py`, `commands/_desloppify_report.py`,
`tests/test_loaderkit_scan.py`; `pyproject.toml` Ruff config;
`commands/novel_state.py:53` (TC001 idiom precedent). Skills: leta, sem,
logisphere-design-review.
