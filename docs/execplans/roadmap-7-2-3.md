# Relocate the shared scan shapes into `loaderkit`

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE (2026-06-27; revised after design review rounds 1, 2, and 3)

## Purpose / big picture

Roadmap task 7.2.2 moved the shared per-line scan *body*
(`scan_pattern`) into the neutral `loaderkit` package but deliberately left its
input and output shapes — `ScannedChapter` and `LineHit` — stranded in the
rule-pack domain (`novel_ralph_skill/rulepack/detect.py`). The consequence is a
sibling-to-sibling domain edge the neutral home was created to remove: the
ledger domain runtime-imports `LineHit` from the rule-pack domain
(`novel_ralph_skill/ledger/detect.py:35`), and `loaderkit/scan.py` reaches back
into `rulepack.detect` (under `TYPE_CHECKING`) for the very shapes its signature
is typed against. That makes the `loaderkit/scan.py` docstring claim — "no
`Rule`/`Device` knowledge", a self-contained neutral primitive — read as a
half-truth, because the primitive's type signature still depends on shapes that
live in a consumer domain.

After this change a reader can observe the single-home property directly:
`ScannedChapter` and `LineHit` live in `loaderkit`; neither `loaderkit.scan` nor
`ledger.detect` imports them from `rulepack.detect`; the runtime `ledger →
rulepack` scan-shape edge and the `TYPE_CHECKING` `loaderkit → rulepack` edge are
both gone; and a hypothetical third pack family would inherit the two neutral
shapes from `loaderkit` instead of cloning or cross-importing them. The same pass
folds in the low-severity tidy-ups it naturally exposes: the thin duplicated
`_scan_rule`/`_scan_device` wrappers are inlined onto the `scan_pattern` call,
the dead `rulepack._coerce._require` (no caller) is deleted, the triple-stated
per-line scan docstring is single-stated, and a callback-contract test pins
`scan_pattern`'s `line_hit` factory.

You can see success by running `make all`: the rule-pack, ledger, and `loaderkit`
suites stay green, `ty check` passes with the new import graph (no
`rulepack.detect` import of the scan shapes from `loaderkit` or `ledger`), and a
new contract test demonstrates that `scan_pattern` constructs every hit through
the caller-supplied `line_hit` callable rather than importing `LineHit` itself.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation (see `Tolerances`), not a workaround.

- **No behaviour change.** This is a pure relocation plus dead-code removal and
  documentation tidy-up. The `scan_pattern` algorithm, the `DetectionReport` /
  `LedgerReport` outputs, every command's envelope, and every exit code are
  unchanged. The rule-pack and ledger detection results for any input must be
  byte-identical before and after.
- **Acyclic import graph, enforced by `ty`.** `loaderkit` must remain a neutral
  leaf that imports neither `rulepack` nor `ledger` at runtime *or* under
  `TYPE_CHECKING` (design §6, §6.3; ADR-001/003; developers' guide "The shared
  loader primitives (`loaderkit`)"). After the move, the import direction is
  `rulepack.detect → loaderkit.scan` and `ledger.detect → loaderkit.scan`, both
  acyclic; the `loaderkit → rulepack` `TYPE_CHECKING` edge that
  Decision D-SCANTYPES of `docs/execplans/roadmap-7-2-2.md` introduced as a
  *temporary* expedient is removed, not relocated.
- **Frozen, slotted, keyword-only house style.** The relocated `ScannedChapter`
  and `LineHit` keep `@dataclasses.dataclass(frozen=True, kw_only=True,
  slots=True)` and their exact field names (`number`/`text`, `chapter`/`line`),
  so every existing construction site (`ScannedChapter(number=…, text=…)`,
  `LineHit(chapter=…, line=…)`) compiles unchanged (rule-pack/ledger schema
  house style; design §6.1).
- **Each pack's typed error channel and operator messages are untouched.** This
  task moves shapes only; `RulePackError`/`RulePackFileError`,
  `LedgerError`/`LedgerFileError`, the exit-code mappings, and all device/rule
  messages stay exactly as 7.2.2 left them (roadmap 7.2.3 Success; ADR-003).
- **The rule-pack contract stays frozen (ADR-003).** `RuleFinding` and
  `DetectionReport` continue to live in `rulepack.detect` and reference
  `LineHit`; only the *definition site* of `LineHit`/`ScannedChapter` moves. The
  rule-pack public surface (`novel_ralph_skill/rulepack/__init__.py` `__all__`)
  is unchanged.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, docstrings,
  comments, and commit messages (AGENTS.md; the `en-gb-oxendict` skill).
- **Docstring coverage stays at 100%** (`interrogate`, gated by `make lint`):
  every relocated class and any new test helper carries a docstring.

## Tolerances (exception triggers)

- **Scope:** if implementation touches more than 12 files or more than ~250 net
  lines, stop and escalate. (Estimate: 3 package modules, 2 package `__init__`s,
  4 test modules, 2 docs files — comfortably inside this bound.)
- **Interface:** if any *public* signature must change beyond the
  definition-site move and re-export (for example, if `scan_pattern`'s parameter
  or return types must change), stop and escalate.
- **Import cycle:** if `ty check` reports any cycle, or if removing the
  `loaderkit → rulepack` edge cannot be done without a runtime import of
  `rulepack`/`ledger` into `loaderkit`, stop and escalate — do **not** reach for
  a function-local import (D-SCANTYPES of roadmap-7-2-2 already rejected that as
  the weaker mechanism).
- **Iterations:** if `make all` still fails after 3 fix attempts on any one work
  item, stop and escalate.
- **Behaviour drift:** if any existing rule-pack, ledger, desloppify, or
  loaderkit test changes its *assertions* (as opposed to its *import lines*),
  stop and escalate — that signals a behaviour change this task forbids.

## Risks

    - Risk: A consumer imports `ScannedChapter`/`LineHit` from `rulepack.detect`
      that the grep below missed, so removing the definition there breaks an
      import at runtime or under `ty`.
      Severity: medium
      Likelihood: low
      Mitigation: Work item 1 enumerates every importer found by
      `grep -rn "ScannedChapter\|LineHit" novel_ralph_skill/ tests/` (see
      "Context and orientation"). To stay safe and idempotent, `rulepack.detect`
      keeps a thin re-export of both shapes from `loaderkit` (Decision
      D-REEXPORT), so any missed `from novel_ralph_skill.rulepack.detect import
      LineHit` still resolves. `ty check` over the whole tree (gated by `make
      typecheck`) is the backstop.

    - Risk: After the definition moves out and `_scan_rule` is inlined, the
      re-exported `ScannedChapter` in `rulepack/detect.py` is referenced only in
      annotations (the `detect` parameter at line 238 and its docstring). Under
      `from __future__ import annotations` those annotations are strings, so the
      runtime top-level `from novel_ralph_skill.loaderkit.scan import
      ScannedChapter` has zero runtime use *in this module* — yet
      `commands/_desloppify.py:57` imports it from `rulepack.detect` at runtime
      and constructs it (line 204), so it must stay a runtime, module-top import.
      A bare top-level import used only in annotations trips Ruff **TC001**
      (`typing-only-first-party-import`, selected at `pyproject.toml:48`,
      verified against the Ruff docs for the locked Ruff 0.15.18), so `make lint`
      fails. `LineHit` is unaffected: after Work item 3 the inlined `detect`
      lambda `LineHit(chapter=…, line=…)` is a genuine runtime use.
      Severity: high
      Likelihood: high (an implementer following the prior plan literally hits
      this gate).
      Mitigation: Work item 1 step 3 **mandates** the codebase's established
      idiom for a runtime-needed, annotation-only re-export (Decision
      D-REEXPORT, revised): an explicit `# noqa: TC001` carrying a rationale
      comment, mirroring the live precedent at
      `novel_ralph_skill/commands/novel_state.py:53`
      (`# noqa: TC001 - runtime global for Cyclopts annotation resolution`),
      **and** a committed module-level `__all__` in `rulepack/detect.py` listing
      both re-exported names. The `# noqa` is the verified, proven-in-repo
      mechanism that silences TC001 (the precedent demonstrates it under this
      codebase's Ruff config); the `__all__` documents the re-export contract.
      The work item verifies `make lint` is clean before the item is declared
      done. `LineHit` keeps no `# noqa` (it has a runtime use after Work item 3),
      but it is still listed in `__all__` so the re-export surface is explicit.

    - Risk: Moving the shapes silently reintroduces a runtime `loaderkit →
      rulepack`/`ledger` edge (for example if the shapes are placed in a new
      `loaderkit` module that imports a detector for a type hint).
      Severity: high
      Likelihood: low
      Mitigation: The shapes are standalone frozen dataclasses with only
      stdlib-typed fields (`int`, `str`); they need no `rulepack`/`ledger`
      import. Work item 1 adds an import-direction guard test
      (`tests/test_loaderkit_scan.py`) asserting `loaderkit.scan.__dict__`
      contains the shapes and that the module imports nothing from
      `rulepack`/`ledger` (Decision D-GUARD). `make typecheck` (`ty 0.0.51`)
      confirms the static graph.

    - Risk: `_desloppify.py` and `_desloppify_report.py` import scan shapes from
      `rulepack.detect`; repointing them churns command modules outside the
      stated scan-consolidation scope.
      Severity: low
      Likelihood: medium
      Mitigation: The re-export shim (D-REEXPORT) means command modules need
      **no** import change — they keep importing from `rulepack.detect`, which
      now re-exports. Only the two *detectors* and the `loaderkit.scan` unit test
      are repointed at the neutral home, exactly as roadmap 7.2.3 specifies
      ("route both detectors and the `loaderkit.scan` unit test at the neutral
      home").

    - Risk: Inlining `_scan_rule`/`_scan_device` loses the documented
      single-line-coverage rationale those wrapper docstrings carried.
      Severity: low
      Likelihood: medium
      Mitigation: The rationale already lives in the two detector **module**
      docstrings (`rulepack/detect.py:11-22`, `ledger/detect.py:11-17`) and the
      two deleted wrapper docstrings, as well as `scan_pattern`'s own docstring;
      Work item 3 single-states it at `scan_pattern` and leaves one concise
      back-reference in each detector module docstring, so no rationale is lost
      (Decision D-DOCSTRING). Note the module-docstring rationale is **separate**
      from the wrapper docstrings: deleting `_scan_rule`/`_scan_device` does not
      trim it, so Work item 3 step 3 edits both module docstrings explicitly, and
      the de-dup acceptance is wrap-insensitive (the rule-pack rationale is
      line-wrapped, so a single-line `cannot cross` grep never matches it;
      design-review round 3, B2).

## Progress

    - [x] Work item 1 (2026-06-27): relocated `ScannedChapter`/`LineHit` into
      `loaderkit.scan`, re-exported from `rulepack.detect` via a module `__all__`,
      repointed `ledger.detect`, and added the AST-scoped import-direction guard
      test (design-review A1). **Deviation from D-REEXPORT B1:** the mandated
      `# noqa: TC001` on `ScannedChapter` is **not applied** — empirically, listing
      `ScannedChapter` in `rulepack/detect.py`'s `__all__` (also mandated by
      D-REEXPORT) marks the import a runtime re-export, so Ruff 0.15.18's TC001
      does **not** fire on it; adding the `# noqa` therefore trips RUF100
      (unused-noqa) and fails `make lint`. The `__all__` entry is the load-bearing
      mechanism that satisfies the same goal the `# noqa` aimed at. Verified:
      `uv run ruff check novel_ralph_skill/rulepack/detect.py` reports "All checks
      passed!" with no `# noqa`. `make all` green;
      `import …rulepack.detect as d; d.LineHit.__module__` is now
      `novel_ralph_skill.loaderkit.scan`.
    - [x] Work item 2 (2026-06-27): deleted the dead `rulepack._coerce._require`
      (no caller) and dropped the now-unused `require` import from the
      `loaderkit.coerce` import block (Ruff F401 would otherwise flag it). The
      ledger's `_require` is untouched (`ledger/_fields.py` calls it). `make all`
      green; `grep "def _require\b" rulepack/_coerce.py` returns nothing.
    - [x] Work item 3 (2026-06-27): inlined `_scan_rule`/`_scan_device` onto the
      `scan_pattern` call in each `detect`/`detect_ledger` loop and deleted both
      wrappers; trimmed both detector **module** docstrings to reference
      `scan_pattern` for the per-line rationale (the splitlines/line-numbers-exact
      *why* is gone from each, the "line by line" fact and the v1 hard-wrap
      limitation retained as detector prose). Acceptance: `grep "def _scan_rule|def
      _scan_device"` returns nothing; both module docstrings reference
      `scan_pattern`; the wrap-insensitive `tr '\n' ' ' | grep -o "cannot  *cross"
      | wc -l` count is **0** for both `rulepack/detect.py` and `ledger/detect.py`;
      `loaderkit/scan.py` retains the phrase (home); `loaderkit/load.py` is
      byte-unchanged (`git diff --stat` empty). `make all` green with no assertion
      changes.
    - [x] Work item 4 (2026-06-27): added
      `test_scan_pattern_builds_every_hit_via_line_hit_callback` — a recording
      double that returns one shared sentinel and asserts one call per match with
      the exact `(chapter, line)` pairs in scan order, plus `hit is sentinel` for
      every returned hit (proving pass-through, never self-construction).
      **Deviation from the plan sketch:** the sentinel is a `LineHit(chapter=-1,
      line=-1)` rather than a bare `object()`, because `ty 0.0.51` rejects an
      `object`-returning callable against `scan_pattern`'s
      `Callable[[int, int], LineHit]` annotation (`invalid-argument-type`). A
      distinct `LineHit` sentinel still proves the pass-through by identity (`is`),
      and the nested double carries a docstring (interrogate gates at 100%).
      `make all` green (1464 passed).
    - [x] Work item 5 (2026-06-27): updated `docs/developers-guide.md` (the
      `loaderkit` ownership list now names the two relocated shapes; the
      `scan_pattern` paragraph now states the shapes are defined in `loaderkit.scan`
      and the `TYPE_CHECKING` `loaderkit → rulepack` edge is gone; the test-pin
      sentence names the new guard and contract tests) and
      `docs/novel-ralph-harness-design.md` §6.3 (the loaderkit-ownership sentence
      now notes the two neutral scan shapes live there too). `make markdownlint`
      (touched files clean), `make nixie` (all diagrams validated), and `make all`
      all pass. Pre-existing markdownlint failures remain in the untracked
      design-review artefacts (`roadmap-7-2-3.logisphere-review-r2.md`,
      `…-r3.md`, `…review-r1.md`), which are outside this task's edit scope and
      not committed by it.

## Surprises & discoveries

    - Observation: the re-exported `ScannedChapter` in `rulepack/detect.py` is
      annotation-only at runtime (strings under `from __future__ import
      annotations`) yet must stay a runtime import for `commands/_desloppify.py`,
      which trips Ruff TC001 and fails `make lint` unless the established
      `# noqa: TC001` idiom is applied (design-review round 1, B1).
      Evidence: Ruff TC001 docs
      (https://docs.astral.sh/ruff/rules/typing-only-first-party-import/) for the
      locked Ruff 0.15.18 (`uv.lock`); the live precedent
      `novel_ralph_skill/commands/novel_state.py:53`; `pyproject.toml:48` selects
      `TC`; `commands/_desloppify.py:57,204` imports and constructs
      `ScannedChapter` at runtime.
      Impact: Work item 1 step 3 and Decision D-REEXPORT now mandate the
      `# noqa: TC001` plus a module `__all__`; the work item gates on
      `uv run ruff check novel_ralph_skill/rulepack/detect.py` being clean.

    - Observation: a literal "exactly one path" acceptance grep for the per-line
      scan rationale is factually wrong because the phrase ``cannot cross``
      appears in a second, out-of-scope docstring (design-review round 2, A2).
      `novel_ralph_skill/loaderkit/load.py:139` carries ``.`` cannot cross ``\n``
      in the `compile_pattern` primitive's docstring (roadmap 5.1.1) — an
      unrelated compile-time phrasing of the same regex fact. `load.py` is not in
      this plan's edit scope. A whole-tree `grep -rln "cannot cross"
      novel_ralph_skill/` therefore returns `loaderkit/load.py` (out of scope,
      retained) in addition to the in-scope home, so an "exactly one path" check
      is wrong regardless of how the de-dup targets are checked.

    - Observation (corrects the round-3 evidence; design-review round 3, B2):
      the per-line scan rationale in `rulepack/detect.py` is **line-wrapped**, so
      a single-line `grep "cannot cross"` **never matches that file** and is a
      vacuous de-dup acceptance for it. The phrase straddles a line break in
      **two** places in `rulepack/detect.py`: the **module docstring** rationale
      (``cannot`` ends line 13, ``cross`` begins line 14 — the
      splitlines/line-numbers-exact passage at `rulepack/detect.py:11-22`) and the
      `_scan_rule` docstring (``cannot`` ends line 157, ``cross`` begins line 158).
      Live evidence in the worktree: `grep -rln "cannot cross"
      novel_ralph_skill/rulepack/detect.py` **exits 1 (no match)**, today and
      after any edit; `grep -rln "cannot cross" novel_ralph_skill/` lists only
      `loaderkit/load.py`, `loaderkit/scan.py`, and `ledger/detect.py` —
      `rulepack/detect.py` is **absent**. (The round-3 plan wrongly asserted this
      grep finds `rulepack/detect.py:157-158`; it does not, because the phrase is
      wrapped there. That false claim is corrected here.) Consequence: a
      single-line grep on `rulepack/detect.py` passes regardless of whether the
      implementer trims the rule-pack rationale, certifying **under-editing** — an
      implementer could delete `_scan_rule`, leave the full module-docstring
      rationale at lines 11-22 in place (violating D-DOCSTRING and the roadmap's
      "de-duplicate the triple-stated per-line scan docstring"), and the check
      still reports green. By contrast `ledger/detect.py` carries ``cannot cross``
      on **single** lines (the module docstring at line 13 and the `_scan_device`
      docstring at line 115), so a single-line grep there is valid.
      Evidence (wrap-insensitive count, the mechanism the acceptance uses):
      `tr '\n' ' ' < novel_ralph_skill/rulepack/detect.py | grep -o "cannot  *cross"
      | wc -l` returns **2** today (module docstring + `_scan_rule` docstring) and
      must return **0** after Work item 3; the same pipeline on
      `novel_ralph_skill/ledger/detect.py` returns **2** today (module docstring +
      `_scan_device` docstring) and must return **0** after Work item 3.
      Impact: Work item 3's de-dup acceptance is **wrap-insensitive** — a
      `tr '\n' ' '`-collapsed count of zero on each of `rulepack/detect.py` and
      `ledger/detect.py` — and the **primary** de-dup signal for
      `rulepack/detect.py` is the positive `scan_pattern`-reference check (the
      trimmed module docstring must reference `scan_pattern` instead of re-stating
      the splitlines/line-numbers-exact rationale). Crucially, inlining
      `_scan_rule`/`_scan_device` alone does **not** satisfy this: the **module**
      docstrings of both detectors (`rulepack/detect.py:11-22`,
      `ledger/detect.py:11-17`) carry the rationale independently of the deleted
      wrapper docstrings and must be trimmed too. A positive check that
      `loaderkit/scan.py` retains the phrase guards the home; `load.py`'s
      out-of-scope occurrence is acknowledged and untouched.

    - Observation: a whole-file substring guard for the import-direction
      invariant would false-positive on `scan_pattern`'s docstring, which
      legitimately cross-references a pack-domain class and names ``rule``/
      ``device`` (design-review round 1, A1).
      Evidence: `loaderkit/scan.py` docstrings contain
      `:class:~novel_ralph_skill.rulepack.detect.LineHit` and ``rule.compiled`` /
      ``device.compiled`` prose.
      Impact: Decision D-GUARD now mandates an `ast`-parsed,
      `Import`/`ImportFrom`-only assertion.

## Decision log

    - Decision (D-HOME): the two scan shapes are relocated into
      `novel_ralph_skill/loaderkit/scan.py` (the module that already owns
      `scan_pattern`), defined at module top above `scan_pattern`, rather than
      into a new `loaderkit/shapes.py` module.
      Rationale: `ScannedChapter` and `LineHit` are precisely the input and
      output shapes of `scan_pattern`; co-locating them with the primitive keeps
      the scan's single home complete and avoids a fourth `loaderkit` module for
      two small dataclasses. The developers' guide already describes
      `loaderkit/scan.py` as the per-line scan's home (design §6.3 lists "the
      per-line scan" among the six primitives loaderkit "owns once each"). They
      are also re-exported from `novel_ralph_skill/loaderkit/__init__.py`'s
      `__all__` so a third pack family can `from novel_ralph_skill.loaderkit
      import ScannedChapter, LineHit`.
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-REEXPORT, revised round 2): `novel_ralph_skill/rulepack/detect.py`
      keeps `ScannedChapter` and `LineHit` available as a **re-export** of the
      `loaderkit` definitions, not as a second definition. The re-export is
      written as a *single, mandated* form (no optional fork):

          from novel_ralph_skill.loaderkit.scan import (
              LineHit,
              ScannedChapter,  # noqa: TC001 - runtime re-export for _desloppify
          )

      and a committed module-level `__all__` is added to `rulepack/detect.py`
      that lists at least `LineHit` and `ScannedChapter` (alongside the existing
      public names `DetectionReport`, `RuleFinding`, `detect` if an `__all__` is
      introduced for the first time — list the module's public surface).

      Rationale: `RuleFinding` and `DetectionReport` (which stay in
      `rulepack.detect`, ADR-003 frozen contract) reference `LineHit` in their
      fields, and `commands/_desloppify.py:57`, `commands/_desloppify_report.py`,
      and `tests/test_rulepack_detect.py` import `ScannedChapter`/`LineHit` from
      `rulepack.detect`. A re-export keeps every one of those import lines valid
      with zero churn while the *single definition* lives in `loaderkit`. This is
      the smallest, most idempotent change consistent with roadmap 7.2.3's
      Success criterion, which forbids only the `ledger.detect` and
      `loaderkit.scan` imports *from* `rulepack.detect`, not a backward-compatible
      re-export *in* `rulepack.detect`. The runtime import `rulepack.detect →
      loaderkit.scan` is acyclic (loaderkit imports nothing back).

      The `# noqa: TC001` on `ScannedChapter` is **required, not optional**
      (design-review round 1, B1): after the definition moves out and `_scan_rule`
      is inlined (Work item 3), `ScannedChapter` is referenced in this module
      only inside annotations (the `detect` parameter at line 238 and its
      docstring), which `from __future__ import annotations` turns into strings.
      Ruff TC001 (`typing-only-first-party-import`, selected at
      `pyproject.toml:48`) would therefore demand the import be moved into a
      `TYPE_CHECKING` block — but it cannot be, because `commands/_desloppify.py`
      imports and *constructs* `ScannedChapter` from `rulepack.detect` at runtime.
      The `# noqa: TC001` is the codebase's proven idiom for exactly this clash:
      `novel_ralph_skill/commands/novel_state.py:53` carries
      `# noqa: TC001 - runtime global for Cyclopts annotation resolution` for an
      identical runtime-needed annotation-only import, and `ledger/detect.py`
      splits its runtime `LineHit` import from its `TYPE_CHECKING` `ScannedChapter`
      import for the same reason. `LineHit` needs **no** `# noqa`: after Work
      item 3 the inlined `detect` lambda `LineHit(chapter=…, line=…)` is a genuine
      runtime use, so TC001 does not fire on it. The `__all__` makes the
      re-export contract explicit and is the secondary signal that these names
      are a deliberate public surface, not stray imports. The Ruff TC001 rule
      semantics were verified against the official Ruff docs
      (https://docs.astral.sh/ruff/rules/typing-only-first-party-import/) for the
      locked Ruff 0.15.18 (`uv.lock`).
      Date/Author: 2026-06-27, planning agent (round 1; revised round 2 for B1).

    - Decision (D-LEDGER-REPOINT): `novel_ralph_skill/ledger/detect.py` is
      repointed to import `LineHit` (runtime, line 35) and `ScannedChapter`
      (`TYPE_CHECKING`, line 41) **from `novel_ralph_skill.loaderkit.scan`**,
      removing both `ledger → rulepack` scan-shape edges.
      Rationale: this is the exact edge roadmap 7.2.3 names ("the ledger domain
      runtime-imports `LineHit` from the rule-pack domain") and that its Success
      criterion requires gone. The ledger reuses the same neutral shapes as the
      rule pack; importing them from the neutral home is the correct direction.
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-SCAN-IMPORT): `loaderkit/scan.py` drops its `TYPE_CHECKING`
      import `from novel_ralph_skill.rulepack.detect import LineHit,
      ScannedChapter` (the temporary D-SCANTYPES expedient) because the shapes are
      now defined in that same module; `scan_pattern`'s annotations reference the
      module-local classes directly.
      Rationale: removing this edge is the central point of roadmap 7.2.3 — it
      makes `loaderkit/scan.py`'s "no `Rule`/`Device` knowledge / neutral
      primitive" docstring true (the signature no longer depends on shapes in a
      consumer domain). D-SCANTYPES of roadmap-7-2-2 explicitly scoped the move
      out as a wider change deferred to a follow-up; this is that follow-up.
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-INLINE): the thin `_scan_rule` (`rulepack/detect.py`) and
      `_scan_device` (`ledger/detect.py`) wrappers — each a one-call forwarder to
      `scan_pattern` with a `line_hit=lambda chapter, line: LineHit(...)` — are
      inlined directly into their `detect`/`detect_ledger` loops, deleting the
      wrapper functions.
      Rationale: roadmap 7.2.3 calls for "inline the thin duplicated
      `_scan_rule`/`_scan_device` wrappers". After 7.2.2 each wrapper adds no
      logic over `scan_pattern`; the lambda is short enough to read inline. The
      `Rule`/`Device` `compiled`-pattern dereference happens at the call, which is
      where the `Rule`/`Device` knowledge belongs (keeping `scan_pattern`
      neutral).
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-DOCSTRING, acceptance revised round 2): the per-line
      single-line-coverage rationale (the "`.` cannot cross `\n`, so a per-line
      scan makes line numbers exact" / ADR-001 v1 discipline) is single-stated in
      `loaderkit/scan.py` (which owns the primitive, and legitimately documents it
      at two altitudes — the module docstring and `scan_pattern`'s function
      docstring); the two detector module docstrings keep a one-line reference to
      `scan_pattern` rather than re-stating the full rationale, and the deleted
      wrapper docstrings' bodies are not reproduced inline.
      Rationale: roadmap 7.2.3 calls to "de-duplicate the triple-stated per-line
      scan docstring". The rationale currently appears in `scan_pattern`,
      `rulepack/detect.py`'s `_scan_rule` docstring, and `ledger/detect.py`'s
      `_scan_device` docstring; consolidating to one authoritative home keeps it
      from drifting. Each detector docstring still names *that* the scan is
      line-by-line and points at `scan_pattern` for *why*.
      Acceptance scoping (design-review round 2, A2; round 3, B2): two distinct
      facts shape the acceptance.
      (a) Out-of-scope occurrence: the phrase ``cannot cross`` also appears in
      `loaderkit/load.py:139` — the `compile_pattern` primitive's unrelated
      compile-time docstring (roadmap 5.1.1) — which is **out of scope** and stays
      untouched. A whole-tree "exactly one path" grep is therefore **wrong** (it
      would report `load.py` too) and is not used.
      (b) **Line-wrapping (round 3, B2):** in `rulepack/detect.py` the rationale is
      **line-wrapped** — ``cannot``/``cross`` straddle a line break in both the
      module docstring (lines 13-14) and the `_scan_rule` docstring (lines
      157-158) — so a **single-line** `grep "cannot cross"` **never matches that
      file** and is a vacuous (always-green) de-dup check for it. The acceptance
      must therefore be **wrap-insensitive**: a `tr '\n' ' '`-collapsed
      `grep -o "cannot  *cross" | wc -l` count of **0** on each of
      `rulepack/detect.py` and `ledger/detect.py`. The **primary** de-dup signal
      for `rulepack/detect.py` is the **positive** check that its trimmed module
      docstring references `scan_pattern` for the rationale instead of re-stating
      the splitlines/line-numbers-exact passage; the wrap-insensitive zero-count is
      the negative backstop. Crucially, the rationale lives in the **module**
      docstring of each detector (`rulepack/detect.py:11-22`,
      `ledger/detect.py:11-17`) *independently* of the wrapper docstrings, so
      inlining `_scan_rule`/`_scan_device` alone does **not** clear it — the module
      docstrings must be trimmed to a `scan_pattern` reference as well. A positive
      check that `loaderkit/scan.py` retains the phrase guards the home. See Work
      item 3 acceptance for the exact commands.
      Date/Author: 2026-06-27, planning agent (round 1; acceptance revised round 2
      for A2; revised round 3 for B2 — wrap-insensitive count + positive primary
      signal).

    - Decision (D-GUARD, revised round 2): a new test in
      `tests/test_loaderkit_scan.py` asserts the import direction — that
      `ScannedChapter` and `LineHit` are defined in `loaderkit.scan` (their
      `__module__` is `novel_ralph_skill.loaderkit.scan`) and that
      `loaderkit.scan`'s source imports nothing from `rulepack` or `ledger`.
      The import-direction assertion **must parse the source with `ast` and
      inspect only `ast.Import` / `ast.ImportFrom` nodes** (not a whole-file
      substring search). It walks the module AST, collects every imported module
      name (`node.module` for `ImportFrom`, each `alias.name` for `Import`), and
      asserts none begins with `novel_ralph_skill.rulepack` or
      `novel_ralph_skill.ledger`.
      Rationale: this pins the single-home and acyclic-graph invariants so they
      cannot silently re-fork (the step-7.2 definition of done: "a test pins it so
      it cannot silently re-fork"). It is a cheap structural assertion, not a
      behaviour test, so it adds no runtime coupling. AST scoping is required
      (design-review round 1, A1) because `scan_pattern`'s own docstring
      legitimately cross-references
      `:class:~novel_ralph_skill.rulepack.detect.LineHit` (an intersphinx-style
      reference that survives the docstring rewrite as a *documentation* mention
      of a pack name) and names ``rule``/``device`` in prose; a blunt
      `read_text()` substring search for `"rulepack"`/`"ledger"` would
      false-positive on that docstring and turn the guard into a flaky tripwire.
      Restricting the check to `Import`/`ImportFrom` nodes asserts exactly the
      load-bearing property — no *import* edge — and nothing else.
      Date/Author: 2026-06-27, planning agent (round 1; revised round 2 for A1).

    - Decision (D-NO-CUPRUM): this task uses **no** `cuprum` API and no external
      runtime library. It is a pure in-package relocation, dead-code removal, and
      docstring/test edit. The only test dependencies are `pytest` and
      `hypothesis`, both already present and exercised by the existing
      `tests/test_loaderkit_scan.py`. No Cyclopts, `uv run`, `pytest-timeout`, or
      subprocess behaviour is in scope, so no external-library behaviour needs
      research beyond the locked `ty 0.0.51` typechecker that gates the import
      graph.
      Rationale: confirmed by reading every module the plan touches
      (`loaderkit/scan.py`, `rulepack/detect.py`, `ledger/detect.py`,
      `rulepack/_coerce.py`) — none constructs a `cuprum` catalogue, spawns a
      subprocess, or parses CLI flags; the shapes are plain `dataclasses`.
      Date/Author: 2026-06-27, planning agent (round 1).

## Outcomes & retrospective

Completed 2026-06-27. Compared against Purpose, every success criterion holds:

- **Single neutral home.** `ScannedChapter` and `LineHit` are defined in
  `novel_ralph_skill/loaderkit/scan.py`; `d.LineHit.__module__` /
  `d.ScannedChapter.__module__` (imported via `rulepack.detect`) both report
  `novel_ralph_skill.loaderkit.scan`. `loaderkit/__init__.py` re-exports both,
  so a third pack family can `from novel_ralph_skill.loaderkit import
  ScannedChapter, LineHit`.
- **Consumer-domain edges gone.** `ledger.detect` imports both shapes from the
  neutral home (no `ledger → rulepack` scan-shape edge); `loaderkit.scan` dropped
  its `TYPE_CHECKING` `rulepack.detect` import (no `loaderkit → rulepack` edge).
  The AST-scoped guard test `test_loaderkit_scan_imports_no_pack_domain` pins this.
  `rulepack.detect` keeps a backward-compatible re-export (via its `__all__`) so
  `commands/_desloppify.py` and the rule-pack tests need no churn.
- **`loaderkit/scan.py` docstring reads true.** Its "no `Rule`/`Device`
  knowledge / imports neither `rulepack` nor `ledger`" claim is now literal —
  both shapes are stdlib-typed frozen dataclasses defined in the module.
- **Tidy-ups landed without behaviour change.** Dead `rulepack._coerce._require`
  deleted; `_scan_rule`/`_scan_device` inlined and removed; the triple-stated
  per-line rationale single-stated at `scan_pattern`; a `line_hit` callback
  contract test added. Every detector, property, and behavioural suite stayed
  green with no assertion changes (`make all`: 1464 passed, 1 skipped).

**Deviations recorded:** (1) the D-REEXPORT `# noqa: TC001` was omitted — the
mandated `__all__` already marks the re-export a runtime use, so TC001 does not
fire and a `# noqa` would trip RUF100 (Work item 1 note). (2) The Work item 4
callback double returns a `LineHit` sentinel rather than a bare `object()`, to
satisfy `ty`'s `Callable[[int, int], LineHit]` annotation; identity (`is`) still
pins the pass-through contract.

**Scope:** 7 files touched (`loaderkit/scan.py`, `loaderkit/__init__.py`,
`rulepack/detect.py`, `rulepack/_coerce.py`, `ledger/detect.py`,
`tests/test_loaderkit_scan.py`, plus the two docs) — within the 12-file / 250-line
tolerance.

## Context and orientation

You are a complete newcomer to this repository. Here is everything you need.

The repository is a Python project (`novel_ralph_skill/`) that ships a novel-
writing harness skill. Three packages matter here:

- `novel_ralph_skill/loaderkit/` — a **neutral leaf** package introduced by
  roadmap task 7.2.2. It owns the six schema-agnostic loader primitives both
  pack families share (the developers' guide section "The shared loader
  primitives (`loaderkit`)" lists them). Its modules are `coerce.py`, `load.py`,
  `scan.py`, and `__init__.py`. `scan.py` defines `scan_pattern`, the per-line
  scan primitive. The package depends only on the `contract` layer and the
  standard library; it must import neither `rulepack` nor `ledger` (design §6,
  §6.3; ADR-001/003).
- `novel_ralph_skill/rulepack/` — the rule-pack domain. `detect.py` is the pure
  `desloppify` detection core. It currently **defines** the two scan shapes
  `ScannedChapter` (chapter `number` + draft `text`, the scan input) and
  `LineHit` (a match's `chapter` + `line`, the scan output), plus `RuleFinding`
  and `DetectionReport` (which reference `LineHit`), and a thin `_scan_rule`
  wrapper around `scan_pattern`.
- `novel_ralph_skill/ledger/` — the device-ledger domain, a deliberate parallel
  of the rule pack. `detect.py` runtime-imports `LineHit` from
  `rulepack.detect` (line 35) and `ScannedChapter` under `TYPE_CHECKING` (line
  41), and has its own thin `_scan_device` wrapper around `scan_pattern`.

Terms defined:

- **Scan shape:** one of the two frozen dataclasses `ScannedChapter` /
  `LineHit`. They carry no `Rule`/`Device` knowledge; they are the neutral input
  and output of the per-line scan.
- **Re-export:** a module imports a name defined elsewhere so that
  `from this.module import Name` keeps working, without redefining `Name`.
- **`TYPE_CHECKING` import:** an import guarded by `if typing.TYPE_CHECKING:`,
  evaluated by the type checker (`ty`) but never at runtime, used here only for
  annotations under `from __future__ import annotations`.

Current importers of the two shapes (from
`grep -rn "ScannedChapter\|LineHit" novel_ralph_skill/ tests/`):

- Runtime, from `rulepack.detect`:
  `novel_ralph_skill/commands/_desloppify.py:57`
  (`from novel_ralph_skill.rulepack.detect import ScannedChapter, detect`) and
  `novel_ralph_skill/ledger/detect.py:35`
  (`from novel_ralph_skill.rulepack.detect import LineHit`).
- `TYPE_CHECKING`, from `rulepack.detect`:
  `novel_ralph_skill/loaderkit/scan.py:28`,
  `novel_ralph_skill/ledger/detect.py:41`,
  `novel_ralph_skill/commands/_desloppify_report.py:35` (imports
  `DetectionReport, RuleFinding`, not the scan shapes — left untouched).
- Tests importing from `rulepack.detect`:
  `tests/test_rulepack_detect.py:24-29` (`LineHit`, `ScannedChapter`, plus
  `DetectionReport`, `RuleFinding`, `detect`),
  `tests/test_ledger_detect.py:27`, `tests/test_ledger_properties.py:40`,
  `tests/test_loaderkit_scan.py:21`.

The dead symbol: `novel_ralph_skill/rulepack/_coerce.py:55` defines
`_require(...)` but `rulepack/parse.py` imports only `_require_int` and
`_require_str` from `_coerce` (verified by
`grep -rn "\b_require\b" novel_ralph_skill/rulepack/`, which finds only the
definition). The ledger's `_require` (`ledger/_coerce.py:58`) **is** used by
`ledger/_fields.py:22`, so only the rule-pack copy is dead.

Validation tooling (from `Makefile` and AGENTS.md):

- `make all` runs `build check-fmt lint typecheck test`.
- `make typecheck` runs `ty check` (locked `ty 0.0.51`, per `uv.lock`).
- `make test` runs `pytest -v -n <workers>` (xdist), SlipCover coverage.
- `make lint` runs Ruff plus `interrogate` (100% docstring coverage gated).
- For Markdown changes: `make markdownlint` and `make nixie` (Mermaid; this plan
  adds no Mermaid, but `make nixie` is run to satisfy the docs-change gate).

## Plan of work

Work proceeds in five ordered, independently committable work items. Each ends
with `make all` green; the two that touch Markdown also run `make markdownlint`
and `make nixie`. Commit after each (the user gates each commit).

### Work item 1 — relocate the scan shapes into `loaderkit.scan`

Implements: roadmap 7.2.3 (relocate `ScannedChapter`/`LineHit`, route both
detectors and the `loaderkit.scan` unit test at the neutral home); design §6.3
(loaderkit owns the per-line scan once); ADR-001/003 (neutral leaf, frozen
contract); Decisions D-HOME, D-REEXPORT, D-LEDGER-REPOINT, D-SCAN-IMPORT,
D-GUARD.

Docs to read first: `docs/novel-ralph-harness-design.md` §6, §6.1, §6.3;
`docs/adr-003-shared-interface-contract.md`; `docs/adr-001-*` (the detect-only,
no-flags discipline); `docs/execplans/roadmap-7-2-2.md` Constraints and Decision
D-SCANTYPES; `docs/developers-guide.md` section "The shared loader primitives
(`loaderkit`)".

Skills to load: `leta` (navigate `loaderkit.scan`, `rulepack.detect`,
`ledger.detect`, and every importer — use `leta refs ScannedChapter` /
`leta refs LineHit` before editing); `python-router` → `python-data-shapes` (the
frozen/slotted/kw-only dataclass choice for the relocated shapes is exactly its
remit) and `python-types-and-apis` (the re-export and module-boundary surface);
`arch-crate-design` (the neutral-leaf boundary and the import-direction
invariant); `sem` (entity-level diff to confirm the shapes moved, not mutated).

Steps:

1. In `novel_ralph_skill/loaderkit/scan.py`, define `ScannedChapter` and
   `LineHit` at module top (above `scan_pattern`), copied verbatim from
   `rulepack/detect.py` including their docstrings and the
   `@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)` decorator. Add
   `import dataclasses` to the runtime imports. Update `scan_pattern`'s
   annotations to reference the now-module-local classes and **remove** the
   `if typ.TYPE_CHECKING:` import `from novel_ralph_skill.rulepack.detect import
   LineHit, ScannedChapter` (D-SCAN-IMPORT). The `TYPE_CHECKING` block keeps only
   `import collections.abc as cabc` and `import re`. Rewrite the module docstring
   so the "no `Rule`/`Device` knowledge" claim is now literally true (the shapes
   are defined here and carry no `Rule`/`Device` reference) and drop the
   D-SCANTYPES sentence about referencing the shapes "only under
   `TYPE_CHECKING`". Also re-point `scan_pattern`'s docstring cross-references:
   the existing
   `:class:~novel_ralph_skill.rulepack.detect.LineHit` Sphinx references in the
   module and function docstrings now name a shape defined in *this* module, so
   rewrite them to the bare `:class:LineHit` (or
   `:class:~novel_ralph_skill.loaderkit.scan.LineHit`). This keeps the docstring
   accurate after the move and removes the last `rulepack` mention from
   `scan.py`'s prose — though the D-GUARD test asserts only on *import* nodes
   (D-GUARD, revised), so a stray docstring mention would not fail it.
2. In `novel_ralph_skill/loaderkit/__init__.py`, add `LineHit` and
   `ScannedChapter` to the `from novel_ralph_skill.loaderkit.scan import …`
   line and to `__all__` (kept alphabetical), and extend the module docstring's
   list of what `loaderkit` owns to mention the two neutral scan shapes.
3. In `novel_ralph_skill/rulepack/detect.py`, delete the two `class
   ScannedChapter` / `class LineHit` definitions and instead re-export them from
   the neutral home (D-REEXPORT, revised). Write the import in **exactly** this
   form at module top (do not leave the `# noqa` as a choice — it is mandatory to
   pass `make lint`):

       from novel_ralph_skill.loaderkit.scan import (
           LineHit,
           ScannedChapter,  # noqa: TC001 - runtime re-export for _desloppify
       )

   Then add a module-level `__all__` to `rulepack/detect.py` listing the module's
   public surface, **including** both re-exported names, e.g.
   `__all__ = ["DetectionReport", "LineHit", "RuleFinding", "ScannedChapter", "detect"]`
   (kept alphabetical). `RuleFinding`/`DetectionReport` keep referencing `LineHit`
   in their fields unchanged.

   Why the `# noqa` is required (design-review round 1, B1): after this step
   removes the class bodies and Work item 3 inlines `_scan_rule`, the only
   remaining `ScannedChapter` reference in this module is the annotation on
   `detect`'s `chapters` parameter (and its docstring). Under
   `from __future__ import annotations` that annotation is a string, so Ruff
   TC001 sees a runtime import used only for typing and demands it move into a
   `TYPE_CHECKING` block — which is impossible because `commands/_desloppify.py`
   constructs `ScannedChapter` from `rulepack.detect` at runtime. The
   `# noqa: TC001` mirrors the live precedent at
   `novel_ralph_skill/commands/novel_state.py:53` and is the verified mechanism
   that silences the rule. `LineHit` carries **no** `# noqa`: after Work item 3
   the inlined `detect` lambda `LineHit(chapter=…, line=…)` is a genuine runtime
   use, so TC001 does not fire on it (keeping a stray `# noqa` on `LineHit` would
   itself trip Ruff `RUF100`, unused-noqa). Note the runtime-use status holds at
   *this* work item's commit boundary too: at the end of Work item 1, `_scan_rule`
   still exists and its `line_hit=lambda chapter, line: LineHit(...)` constructs
   `LineHit` at runtime, while `ScannedChapter` is already annotation-only (the
   `_scan_rule` and `detect` parameter annotations are strings under
   `from __future__ import annotations`). So `LineHit` needs no `# noqa` and
   `ScannedChapter` needs the `# noqa` from Work item 1 onward — the lint posture
   is stable across the Work item 1 → Work item 3 boundary. Verify with
   `uv run ruff check novel_ralph_skill/rulepack/detect.py` (or `make lint`) that
   the module is clean — no TC001 on `ScannedChapter`, no RUF100 on `LineHit` —
   before declaring the work item done.
4. In `novel_ralph_skill/ledger/detect.py`, change the runtime import
   `from novel_ralph_skill.rulepack.detect import LineHit` to
   `from novel_ralph_skill.loaderkit.scan import LineHit` (line 35), and the
   `TYPE_CHECKING` import `from novel_ralph_skill.rulepack.detect import
   ScannedChapter` to `from novel_ralph_skill.loaderkit.scan import
   ScannedChapter` (line 41) (D-LEDGER-REPOINT). Update the module docstring
   sentence that says it "reuses
   `novel_ralph_skill.rulepack.detect.ScannedChapter` and `…LineHit`" to name the
   neutral `loaderkit` home instead.
5. Repoint the `loaderkit.scan` unit test: in `tests/test_loaderkit_scan.py`,
   change `from novel_ralph_skill.rulepack.detect import LineHit, ScannedChapter`
   to `from novel_ralph_skill.loaderkit.scan import LineHit, ScannedChapter`, and
   update the module docstring reference accordingly (it currently says it
   constructs the shapes "directly (as `tests/test_rulepack_detect.py` does)").
   Leave `tests/test_rulepack_detect.py`, `tests/test_ledger_detect.py`, and
   `tests/test_ledger_properties.py` importing from `rulepack.detect` — they
   exercise the rule-pack/ledger detectors, and the re-export keeps those imports
   valid; repointing them is out of scope for 7.2.3 (which names only the two
   detectors and the `loaderkit.scan` unit test).

Tests to add/update (this work item):

- **Update** `tests/test_loaderkit_scan.py` import line and docstring (step 5).
- **Add** the D-GUARD import-direction test in `tests/test_loaderkit_scan.py`: a
  unit test `test_scan_shapes_are_defined_in_loaderkit` asserting
  `ScannedChapter.__module__ == "novel_ralph_skill.loaderkit.scan"` and likewise
  for `LineHit`; and a test `test_loaderkit_scan_imports_no_pack_domain` that
  **parses** `novel_ralph_skill/loaderkit/scan.py` with `ast.parse(...)` and
  walks `ast.Import` / `ast.ImportFrom` nodes only, asserting no imported module
  name begins with `novel_ralph_skill.rulepack` or `novel_ralph_skill.ledger`
  (A1). Do **not** write a `Path(...).read_text()` substring check for
  `"rulepack"`/`"ledger"`: `scan_pattern`'s docstring legitimately cross-
  references `:class:~novel_ralph_skill.rulepack.detect.LineHit` and names
  ``rule``/``device`` in prose, so a substring check would false-positive. A
  sketch of the import-scoped assertion (en-GB docstring):

      def test_loaderkit_scan_imports_no_pack_domain() -> None:
          """`loaderkit.scan` imports nothing from a pack domain."""
          import ast
          import pathlib

          from novel_ralph_skill.loaderkit import scan

          source = pathlib.Path(scan.__file__).read_text(encoding="utf-8")
          tree = ast.parse(source)
          imported: list[str] = []
          for node in ast.walk(tree):
              if isinstance(node, ast.ImportFrom) and node.module:
                  imported.append(node.module)
              elif isinstance(node, ast.Import):
                  imported.extend(alias.name for alias in node.names)
          banned = ("novel_ralph_skill.rulepack", "novel_ralph_skill.ledger")
          assert not [m for m in imported if m.startswith(banned)]

  (en-GB docstrings; AGENTS.md: unit test, pins the single-home and acyclic
  invariants.)
- **No assertion changes** to any existing test — only the one import line and
  the docstring in `tests/test_loaderkit_scan.py` (Tolerance: behaviour drift).

Validation:

- `make all` — expect `ty check` to report all checks passed with the new graph
  (no `loaderkit → rulepack`/`ledger` edge; the `rulepack.detect →
  loaderkit.scan` and `ledger.detect → loaderkit.scan` edges acyclic), and the
  rule-pack, ledger, desloppify, and `loaderkit` suites green.
- **Lint-gate check (B1):** before `make all`, run
  `uv run ruff check novel_ralph_skill/rulepack/detect.py` and confirm zero
  findings — specifically no `TC001` on `ScannedChapter` (silenced by the
  mandated `# noqa`) and no `RUF100` "unused noqa" on `LineHit` (which must carry
  no `# noqa`, because its inlined construction after Work item 3 is a runtime
  use). If `TC001` still fires, the `# noqa` comment is mis-placed (it must sit
  on the `ScannedChapter` import line); fix it before continuing. This is the
  exact gate the design review flagged would otherwise fail `make lint`.
- Spot-check with `leta refs ScannedChapter` and `leta refs LineHit` that every
  reference now resolves to the `loaderkit.scan` definition (directly or via the
  `rulepack.detect` re-export).

Acceptance (observable): before this change,
`python -c "import novel_ralph_skill.rulepack.detect as d; print(d.LineHit.__module__)"`
prints `novel_ralph_skill.rulepack.detect`; after, it prints
`novel_ralph_skill.loaderkit.scan`. The new guard tests fail if anyone later
moves a shape back or reintroduces a `loaderkit → rulepack` import.

### Work item 2 — delete the dead `rulepack._coerce._require`

Implements: roadmap 7.2.3 ("delete the dead `rulepack._coerce._require` (no
caller)"); design §6 (one body of each primitive; no dead clones); the step-7.2
definition of done.

Docs to read first: `docs/developers-guide.md` "The shared loader primitives
(`loaderkit`)" (the binding-seam description, so you confirm `_require` is a
binding wrapper the rule pack never calls). `docs/execplans/roadmap-7-2-2.md`
Decision D-BINDING (the per-package binding wrappers).

Skills to load: `leta` (`leta refs _require` scoped to `rulepack` to re-confirm
zero callers before deletion); `python-router` → `python-quality-tools`
(`deadcode` is the canonical check that the symbol is unreachable);
`python-errors-and-logging` (confirm removing the wrapper does not break the
error-factory binding the other wrappers share).

Steps:

1. Re-confirm zero callers: `grep -rn "\b_require\b"
   novel_ralph_skill/rulepack/` must show only the definition at
   `novel_ralph_skill/rulepack/_coerce.py:55`. Cross-check with `leta refs
   _require` / `deadcode novel_ralph_skill/rulepack/`. (The ledger's `_require`
   is **kept** — `ledger/_fields.py` calls it.)
2. Delete the `def _require(mapping, key, *, rule_id)` function (and its
   docstring) from `novel_ralph_skill/rulepack/_coerce.py`. Leave `require`
   imported from `loaderkit.coerce` only if another rule-pack wrapper still uses
   it; if `_require` was the sole consumer of the imported `require` name in this
   module, drop `require` from the `from novel_ralph_skill.loaderkit.coerce
   import (…)` line too (Ruff F401 will flag an unused import if you miss it).

Tests to add/update: none new. The deletion is dead-code removal; the existing
rule-pack parse/coerce suites (`tests/test_rulepack_*`,
`tests/test_loaderkit_coerce.py`) must stay green, proving nothing depended on
the removed wrapper. (AGENTS.md: run the relevant unit suites before and after.)

Validation:

- `make all` — Ruff (`make lint`) flags any now-unused `require` import; `make
  test` confirms the rule-pack suites stay green. Expect no test changes.

Acceptance (observable): `grep -rn "def _require\b"
novel_ralph_skill/rulepack/_coerce.py` returns nothing after the change;
`make all` passes.

### Work item 3 — inline the thin scan wrappers and single-state the docstring

Implements: roadmap 7.2.3 ("inline the thin duplicated `_scan_rule`/`_scan_device`
wrappers" and "de-duplicate the triple-stated per-line scan docstring"); design
§6.1, §6.3; ADR-001 (the per-line, no-flags discipline whose rationale is
consolidated); Decisions D-INLINE, D-DOCSTRING.

Docs to read first: `docs/novel-ralph-harness-design.md` §6.1 and §6.3 (the
detectors' shapes and the line-by-line discipline); `docs/adr-001-*` (the
no-flags / single-line-coverage v1 rule the docstring states).

Skills to load: `leta` (`leta refs _scan_rule`, `leta refs _scan_device` to
confirm each has exactly one caller — its own `detect`/`detect_ledger` — before
inlining); `python-router` → `python-iterators-and-generators` (the
`detect`/`detect_ledger` loops the inlined call lives in) and
`python-abstractions` (judging that the wrapper adds no abstraction worth
keeping); `code-review` (a light pass to confirm readability after inlining).

Steps:

1. In `novel_ralph_skill/rulepack/detect.py`, inline `_scan_rule` into `detect`:
   replace `count, lines = _scan_rule(rule, chapters)` with
   `count, lines = scan_pattern(rule.compiled, chapters, line_hit=lambda chapter,
   line: LineHit(chapter=chapter, line=line))`, then delete the `def _scan_rule`
   function and its docstring. `scan_pattern` is already imported at module top.
2. In `novel_ralph_skill/ledger/detect.py`, inline `_scan_device` into
   `detect_ledger` the same way (`device.compiled`), then delete the `def
   _scan_device` function and its docstring.
3. Apply D-DOCSTRING: ensure the full per-line single-line-coverage rationale
   ("the no-flags compilation means `.` cannot cross `\n`, so a per-line scan
   makes line numbers exact and bounds every match to one line; ADR-001 v1
   discipline") is stated once, at `scan_pattern`'s docstring in
   `loaderkit/scan.py`. Trim the two detector **module** docstrings so each states
   *that* detection is line-by-line and references `scan_pattern` for the full
   rationale, rather than re-stating it. **Both module docstrings carry the
   rationale independently of the wrapper docstrings deleted in steps 1-2**, so
   trimming them is a *separate, required* edit — deleting `_scan_rule`/
   `_scan_device` does not remove it:
   - `rulepack/detect.py:11-22` — the passage "Detection scans **line by line**
     … so ``.`` cannot cross ``\n``; splitting each chapter into physical
     lines … makes line numbers exact, bounds every match to a single line …"
     (note the phrase is **line-wrapped**: ``cannot`` ends line 13, ``cross``
     begins line 14). Replace the splitlines/line-numbers-exact rationale with a
     one-line pointer to `scan_pattern` (keep the "line by line" statement of
     fact and the v1 hard-wrap-limitation note if it is detector-specific prose,
     but drop the *why* that now lives at `scan_pattern`).
   - `ledger/detect.py:11-17` — the mirror passage "detection scans **line by
     line** … so ``.`` cannot cross ``\n``; splitting each chapter into physical
     lines … makes the ``{chapter, line}`` attribution exact …". Trim the same
     way.
   Do not reproduce the deleted wrapper docstrings inline.

Tests to add/update: none new in this item (Work item 4 adds the callback
contract test). The existing `tests/test_rulepack_detect.py`,
`tests/test_ledger_detect.py`, `tests/test_ledger_properties.py`, and
`tests/test_loaderkit_scan.py` must stay green with no assertion changes,
proving the inlining is behaviour-preserving. (AGENTS.md: run unit, property, and
behavioural suites before and after.)

Validation:

- `make all` — Ruff flags any now-unused name; `ty check` passes; every
  detector/scan suite stays green. Expect zero assertion changes.

Acceptance (observable): `grep -rn "def _scan_rule\|def _scan_device"
novel_ralph_skill/` returns nothing; `make test -k "detect or loaderkit_scan or
ledger"` (or `make all`) passes.

For the docstring de-duplication, "single-stated" means a single *home module*
for the **per-line scan rationale**, not a single textual occurrence of the
phrase ``cannot cross`` across the whole package (design-review rounds 1-3). Three
facts matter here, and they must not be conflated:

1. `loaderkit/scan.py` legitimately states the per-line scan rationale in **both**
   its module docstring (line 6) and `scan_pattern`'s function docstring (line
   42), and **both survive** — the consolidation removes the *cross-module*
   duplication (the rule-pack and ledger detector docstrings), not the in-module
   pair that documents the same primitive at two altitudes.
2. `novel_ralph_skill/loaderkit/load.py:139` **also** contains the phrase
   ``.`` cannot cross ``\n`` — but in a *different, unrelated* docstring: the
   `compile_pattern` primitive (roadmap 5.1.1) states the same compile-time fact
   about no-flags regex for *its own* reason (matching the whole chapter at load
   time). `load.py` is **out of this plan's edit scope** — it is not touched by
   any work item and appears only in the orientation prose. Its ``cannot cross``
   occurrence is the compile-time phrasing of the same regex fact and **must
   remain untouched** (editing it would be Tolerance-forbidden scope creep).
3. **(round 3, B2) In `rulepack/detect.py` the phrase is line-wrapped**, so a
   *single-line* `grep "cannot cross" novel_ralph_skill/rulepack/detect.py`
   **never matches** — it exits 1 today and after any edit, because ``cannot``
   ends line 13 and ``cross`` begins line 14 in the module docstring, and
   ``cannot`` ends line 157 and ``cross`` begins line 158 in the `_scan_rule`
   docstring. A single-line grep is therefore a **vacuous, always-green** de-dup
   check for that file: it would certify "de-duplicated" even if the implementer
   deleted `_scan_rule` but left the full module-docstring rationale at lines
   11-22 in place. The acceptance below is **wrap-insensitive** for that reason,
   and uses a **positive** `scan_pattern`-reference check as the primary signal.
   (`ledger/detect.py` carries the phrase on single lines — 13 and 115 — so a
   single-line grep is valid there, but the same wrap-insensitive count is used
   for symmetry and to cover the module-docstring occurrence at line 13 that
   inlining `_scan_device` does **not** delete.)

A whole-package `grep -rln "cannot cross" novel_ralph_skill/` therefore returns
**two** correct paths after Work item 3 — `loaderkit/scan.py` (retained,
in-scope) and `loaderkit/load.py` (retained, out-of-scope) — and would mislead an
implementer running a literal "exactly one path" check into hunting a
non-existent duplicate or wrongly editing `load.py`. Do **not** use that
whole-tree check, and do **not** use a single-line `cannot cross` grep on
`rulepack/detect.py` (it never matches; fact 3 above). The acceptance is instead
a **positive** reference check (primary) plus a **wrap-insensitive** zero-count
backstop, plus a positive check on the retained home:

- **De-dup PRIMARY signal — module docstrings reference the home, not the
  rationale:** the two detector module docstrings must reference `scan_pattern`
  for the full rationale instead of re-stating the splitlines/line-numbers-exact
  passage. Confirm both files reference the primitive:
  `grep -rln "scan_pattern" novel_ralph_skill/rulepack/detect.py novel_ralph_skill/ledger/detect.py`
  returns **both** paths. Then read each trimmed module docstring and confirm the
  splitlines/line-numbers-exact *why* (the "splitting each chapter into physical
  lines … makes line numbers exact, bounds every match to a single line" passage)
  is **gone** from `rulepack/detect.py:11-22` and its `ledger/detect.py` mirror,
  replaced by a one-line `scan_pattern` pointer. This is the load-bearing check:
  it certifies the rationale was actually removed, not merely that a wrapper
  function was deleted.
- **De-dup BACKSTOP — wrap-insensitive zero count:** collapse newlines before
  counting so a line-wrapped occurrence is still caught:

      tr '\n' ' ' < novel_ralph_skill/rulepack/detect.py \
        | grep -o "cannot  *cross" | wc -l   # must print 0
      tr '\n' ' ' < novel_ralph_skill/ledger/detect.py \
        | grep -o "cannot  *cross" | wc -l   # must print 0

  Both print **0** after Work item 3 (each prints **2** before it — the module
  docstring plus the wrapper docstring). The `"cannot  *cross"` pattern (a space
  then zero-or-more spaces between the two words) tolerates the single space the
  line-wrap collapse introduces and any double-space. Do **not** substitute a
  plain `grep "cannot cross"` on
  `rulepack/detect.py`: it never matches the wrapped phrase and would pass
  vacuously. (`grep -Pzc "cannot\s+cross"` is **not** used — it returned 0 with
  exit 1 in this worktree's `grep`, i.e. it is unreliable here; the `tr`-collapse
  pipeline is the verified mechanism.)
- **Home retained:**
  `grep -rln "cannot cross" novel_ralph_skill/loaderkit/scan.py`
  returns **exactly that one path** — `scan.py` still owns the rationale (its
  occurrences are on single lines, so a plain grep is valid here).
- **Out-of-scope occurrence acknowledged, untouched:**
  `grep -rln "cannot cross" novel_ralph_skill/loaderkit/load.py` still returns
  `load.py` (the `compile_pattern` docstring is the unrelated compile-time
  phrasing of the same regex fact; it is not in scope and must read identically
  before and after this plan).

### Work item 4 — add the `line_hit`-callback contract test for `scan_pattern`

Implements: roadmap 7.2.3 ("add a callback-contract test for `scan_pattern`'s
`line_hit` factory"); the step-7.2 definition of done (a test pins the
primitive). Design §6.3 (the scan primitive constructs hits through a
caller-supplied factory so it holds no `Rule`/`Device` knowledge).

Docs to read first: `loaderkit/scan.py`'s `scan_pattern` docstring (the `line_hit`
parameter contract: "Constructs a `LineHit` from `(chapter_number,
line_index)`"); `docs/execplans/roadmap-7-2-2.md` Decision D-SCANTYPES (why the
factory exists — to keep the primitive from importing a hit type itself).

Skills to load: `leta` (locate `tests/test_loaderkit_scan.py` and `scan_pattern`);
`python-router` → `python-testing` (the example-based contract test design and
where it sits versus the existing Hypothesis property);
`python-verification` (decide adversary depth: an example-based callback-arg
assertion is sufficient here — a property/CrossHair pass is **not** required for
a callback-shape contract, and `python-verification` confirms when Hypothesis is
*not* the right tool, avoiding over-engineering).

Steps:

1. In `tests/test_loaderkit_scan.py`, add a contract test
   (`test_scan_pattern_builds_every_hit_via_line_hit_callback`) that proves
   `scan_pattern` invokes `line_hit` once per match with exactly
   `(chapter_number, one_based_line_index)` and uses the *returned* object as the
   hit, never constructing `LineHit` itself. Use a recording double whose
   `line_hit` appends each `(chapter, line)` argument pair to a list and returns
   a shared `sentinel = object()`. The test below is the model.

The recording-double test (indented block, en-GB docstring):

        def test_scan_pattern_builds_every_hit_via_line_hit_callback() -> None:
            """`scan_pattern` builds each hit only through the supplied factory."""
            calls: list[tuple[int, int]] = []
            sentinel = object()

            def recording_line_hit(chapter: int, line: int) -> object:
                calls.append((chapter, line))
                return sentinel

            pattern = re.compile(r"z")
            chapters = [
                ScannedChapter(number=3, text="z\nz z"),
                ScannedChapter(number=7, text="z"),
            ]
            count, hits = scan_pattern(
                pattern, chapters, line_hit=recording_line_hit
            )
            assert count == 4
            assert calls == [(3, 1), (3, 2), (3, 2), (7, 1)]
            assert all(hit is sentinel for hit in hits)

This asserts: one call per match, the exact `(chapter, line)` argument pairs in
scan order, and that every element of the returned tuple is the factory's return
value (so `scan_pattern` does not import or construct any hit type of its own).

Tests to add/update: the one new unit test above. No existing test changes.
(AGENTS.md: a unit test pinning the callback contract; CrossHair/Hypothesis not
required for a fixed-shape callback assertion, per `python-verification`.)

Validation:

- `make all` — the new test passes; the suite stays green.

Acceptance (observable): `make test -k line_hit_callback` (or
`scan_pattern_builds_every_hit`) passes; mutating `scan_pattern` to construct a
hit by any means other than calling `line_hit` would fail this test (the
`hit is sentinel` assertion).

### Work item 5 — update the developers' guide and design references; run Markdown gates

Implements: the step-7.2 definition of done ("it is documented as the single
source of truth"); roadmap 7.2.3 Success (the `loaderkit/scan.py` docstring reads
true and the single home is documented). Design §6.3 (the loaderkit ownership
sentence); `docs/developers-guide.md` "The shared loader primitives".

Docs to read first: `docs/developers-guide.md` lines around "The shared loader
primitives (`loaderkit`)" — specifically the `scan_pattern` paragraph that today
says the shapes are "(still defined in `rulepack/detect.py`)" and references the
`TYPE_CHECKING` edge; and the test-pin sentence listing
`tests/test_loaderkit_scan.py`. `AGENTS.md` "Markdown guidance".

Skills to load: `en-gb-oxendict` (Oxford spelling in the prose edits);
`execplans` (keep this plan's living sections current as the final item lands);
`leta`/`sem` only if cross-checking that the documented symbol names still match
the code.

Steps:

1. In `docs/developers-guide.md`, update the `scan_pattern` paragraph (currently
   "`scan_pattern` references the `ScannedChapter`/`LineHit` shapes (still defined
   in `rulepack/detect.py`) only under `TYPE_CHECKING`…") to state the post-7.2.3
   reality: `loaderkit` now **defines** `ScannedChapter`/`LineHit` alongside
   `scan_pattern`, both detectors import them from the neutral home, and there is
   no longer any `loaderkit → rulepack` edge (the `TYPE_CHECKING` expedient is
   gone); the `line_hit` callable remains the seam that keeps the primitive from
   importing any `Rule`/`Device` knowledge. Extend the "owns the six primitives
   once each" list (or add a clause) to note the two neutral scan shapes now live
   in `loaderkit` too. Update the test-pin sentence if the new guard/contract
   tests are worth naming.
2. In `docs/novel-ralph-harness-design.md` §6.3, confirm the sentence "The
   rule-pack (§6.1) and device-ledger (§6.3) loaders share one home for their
   schema-agnostic primitives — `novel_ralph_skill/loaderkit/`, owning the
   coercion, entry-extraction, pattern-compilation, duplicate-id, file-load, and
   per-line scan bodies once each" still reads true; if a short clause clarifies
   that the per-line scan's *shapes* now live there too, add it, keeping the
   prose ≤80 columns.
3. Mark this plan's `Progress` items complete with timestamps and fill
   `Outcomes & retrospective`.

Tests to add/update: none (documentation only).

Validation:

- `make markdownlint` — expect no MD013 (80-col prose / 120-col code) or other
  violations in the edited files.
- `make nixie` — validates Mermaid; this change adds none, but the docs-change
  gate requires running it (expect a clean pass).
- `make all` — confirm the code suites remain green (no code changed in this
  item, so this is a regression backstop).

Acceptance (observable): `make markdownlint` and `make nixie` pass; reading the
developers' guide "shared loader primitives" section, the `scan_pattern`
paragraph no longer claims the shapes live in `rulepack/detect.py` and no longer
mentions a `loaderkit → rulepack` `TYPE_CHECKING` import.

## Validation summary (all work items)

- After every code work item (1-4): `make all` (runs `build check-fmt lint
  typecheck test`). `ty 0.0.51` must report all checks passed with the new import
  graph; the rule-pack, ledger, desloppify, and `loaderkit` suites must stay
  green; Ruff and `interrogate` (100% docstring coverage) must pass.
- After the docs work item (5): `make markdownlint` and `make nixie` in addition
  to `make all`.
- Commit after each work item (the user gates each commit; en-GB Oxford-spelling
  commit messages via the `commit-message` skill).

## Revision notes

- **Round 1 → round 2 (design review round 1):** mandated the `# noqa: TC001`
  plus a module `__all__` for the `ScannedChapter` re-export in
  `rulepack/detect.py` (B1), and re-scoped the D-GUARD import-direction test to
  an `ast`-parsed `Import`/`ImportFrom` check so `scan_pattern`'s docstring
  cross-reference does not false-positive (A1). No work-item ordering changed.

- **Round 2 → round 3 (design review round 2):** corrected Work item 3's
  docstring-deduplication acceptance, which was factually wrong (A2). The
  previous check asserted `grep -rln "cannot cross" novel_ralph_skill/` returns
  "exactly one path" (`loaderkit/scan.py`), but
  `novel_ralph_skill/loaderkit/load.py:139` also carries ``cannot cross`` in the
  *unrelated, out-of-scope* `compile_pattern` docstring (roadmap 5.1.1). After
  Work item 3 deletes the `_scan_rule`/`_scan_device` wrapper docstrings, that
  whole-tree grep returns **two** paths on a *correct* implementation
  (`scan.py` and `load.py`), so an implementer running the literal check would
  see a false failure and risk wrongly editing the out-of-scope `load.py`
  docstring. The acceptance is now scoped to the two de-duplication targets
  (`rulepack/detect.py` and `ledger/detect.py` must contain no
  ``cannot cross``), with a separate positive check that `loaderkit/scan.py`
  retains it and an explicit acknowledgement that `load.py`'s occurrence is the
  unrelated compile-time phrasing and stays untouched. D-DOCSTRING and the
  Surprises section were updated to match. No code, work-item ordering, or other
  acceptance criteria changed; this is a pure acceptance-correctness fix.

- **Round 3 → round 4 (design review round 3, B2):** corrected a *second*
  factual error in Work item 3's de-dup acceptance that made it vacuous for
  `rulepack/detect.py`. The round-2 acceptance used a single-line
  `grep -rln "cannot cross" …/rulepack/detect.py` to prove the rationale was
  de-duplicated, and the Surprises section asserted that grep "finds the phrase
  in … `rulepack/detect.py:157-158`". Both were wrong: the phrase is
  **line-wrapped**
  in `rulepack/detect.py` (``cannot``/``cross`` straddle the line break in both
  the module docstring at lines 13-14 and the `_scan_rule` docstring at lines
  157-158), so the single-line grep **never matches that file** (it exits 1 in
  the worktree, today and after any edit). The check therefore passed regardless
  of whether the implementer trimmed the rule-pack rationale — certifying
  under-editing (the inverse of round 2's over-editing defect). The fix: (1) the
  Surprises section's false "finds … `rulepack/detect.py:157-158`" claim is
  corrected to record that a single-line grep does **not** list
  `rulepack/detect.py` because the phrase is wrapped; (2) the de-dup acceptance
  is now **wrap-insensitive** — a `tr '\n' ' '`-collapsed
  `grep -o "cannot  *cross" | wc -l` count of **0** on each of
  `rulepack/detect.py` and `ledger/detect.py`
  — with the **positive** `scan_pattern`-reference check (and a read-through that
  the splitlines/line-numbers-exact rationale is gone from each module docstring)
  promoted to the **primary** de-dup signal; (3) Work item 3 step 3 now names the
  two **module** docstrings (`rulepack/detect.py:11-22`, `ledger/detect.py:11-17`)
  as a separate, required trim — deleting the wrapper functions alone does not
  remove the module-docstring rationale. D-DOCSTRING, the Risks mitigation, and
  the Surprises section were updated to match. No code, work-item ordering, or
  other acceptance criteria changed; this is a pure acceptance-correctness fix.

## Addenda

- [x] **7.2.3.1 — Generalise the loaderkit import-direction guard beyond
  `loaderkit.scan`** (from review:7.2.3; low). The D-GUARD test
  `test_loaderkit_scan_imports_no_pack_domain` pins only `scan.py` against
  pack-domain imports, but the neutral-leaf invariant (design §6/§6.3, ADR-003)
  applies to every `loaderkit` module — `coerce.py`, `load.py`, and
  `__init__.py` — each of which must import neither `rulepack` nor `ledger`.
  Parametrise the guard to walk every module in the `loaderkit` package (or its
  `__init__` re-export surface) so a future regression in any of them is caught,
  not just one in `scan.py`. Test-only; no production change. Lightweight
  addendum pass.
- [x] **7.2.3.2 — Align `loaderkit/scan.py` docstrings with the post-7.2.3 callback
  framing** (from review:7.2.3; low). The `scan.py` module docstring and the
  `scan_pattern` docstring still justify the `line_hit` callback as preventing
  import of a "pack-domain hit type", which is now self-contradictory because
  `LineHit` is defined in that very module after 7.2.3 relocated it. The
  developers' guide already uses the correct "free of any `Rule`/`Device`
  knowledge" framing. Retune both docstrings to that framing so the rationale no
  longer contradicts the relocated type's home. Doc-only; no behaviour change.
  Lightweight addendum pass.
