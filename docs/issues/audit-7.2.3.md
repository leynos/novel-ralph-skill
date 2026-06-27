# Post-merge audit — roadmap task 7.2.3

Task 7.2.3 relocated the two neutral scan shapes — `ScannedChapter` (the scan
input) and `LineHit` (the scan output) — out of `rulepack/detect.py` and into
`novel_ralph_skill/loaderkit/scan.py`, alongside the `scan_pattern` primitive
they belong to, so the per-line scan finally has a single, schema-agnostic home.
It also deleted the dead `rulepack._coerce._require` forwarder and the two thin
`_scan_rule`/`_scan_device` wrappers (inlining them at their call sites), and
added a callback-contract test for `scan_pattern`. The change directly addresses
Findings 1, 3, 4, and 7 of the 7.2.2 audit.

This audit reviews the merged state at `origin/main` (commit `7c0523c`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The relocation is clean and well-tested: the two shapes now carry numpydoc
docstrings in `loaderkit/scan.py`, an AST-scoped guard pins their single home and
asserts the module imports no pack domain, and a callback-contract test pins that
`scan_pattern` builds every hit through the supplied factory. The material
findings concern two things the relocation did **not** finish: (a) several
consumers still reach the relocated shapes *through* the `rulepack.detect`
re-export rather than the new neutral home, so the `ledger → rulepack` and
command → `rulepack` domain edges the move was meant to remove persist; and (b)
the `line_hit` callback's stated justification — "so this module never imports a
pack-domain hit type" — is now circular, because `LineHit` is the module's *own*
type, leaving a duplicated lambda and a vacuous indirection at both call sites.

Documentation and skills relied on for this audit:
`docs/novel-ralph-harness-design.md` (§6, §6.1), `docs/developers-guide.md`
("The shared loader primitives (`loaderkit`)", lines 1704–1762), `docs/adr-001`,
`docs/adr-003`, `docs/issues/audit-7.2.2.md` (the prior pass this task closes
out), and `AGENTS.md` (quality gates, 400-line file cap, en-GB Oxford spelling).
Code navigation used `leta`; history was traced with `sem diff --commit 7c0523c`.

## Finding 1 — Consumers still reach the relocated shapes through the `rulepack.detect` re-export

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_desloppify.py:57`
  (`from novel_ralph_skill.rulepack.detect import ScannedChapter, detect`),
  `tests/test_ledger_detect.py:27`, and `tests/test_ledger_properties.py:40`
  (each `from novel_ralph_skill.rulepack.detect import ScannedChapter`).

Task 7.2.3 established `loaderkit.scan` as the single home for `ScannedChapter`
and `LineHit`, and `ledger/detect.py` now correctly imports `ScannedChapter` from
`loaderkit.scan`. But three other consumers still obtain the *same canonical
shape* by reaching through the `rulepack.detect` re-export. Two of them are
ledger-domain tests, and one is `_desloppify.py`, the shared desloppification
command that drives *both* rule-pack and ledger detection over the same chapters.
None of these has any rule-pack-specific reason to depend on the rule-pack
package for a neutral type — they import it from `rulepack.detect` only because
that was the shape's home before this task. This is the exact `ledger → rulepack`
(and command → `rulepack`) domain leak that 7.2.2 Finding 2 recorded; 7.2.3 moved
the definition but did not repoint these import sites, so the leak persists at the
test and command layers. The result is three import sources for one type
(`loaderkit.scan`, the `loaderkit` package init, and `rulepack.detect`), which is
both a coupling smell and a quiet inconsistency with `ledger/detect.py`, which
already imports from the neutral home.

- **Proposed fix:** Repoint
  `_desloppify.py:57`, `tests/test_ledger_detect.py:27`, and
  `tests/test_ledger_properties.py:40` at the neutral home
  (`from novel_ralph_skill.loaderkit.scan import ScannedChapter`, or the
  `loaderkit` package re-export). Once no consumer reaches the shapes through
  `rulepack.detect`, decide deliberately whether `rulepack.detect` should keep
  re-exporting `ScannedChapter`/`LineHit` in its `__all__` (lines 43, 45) at all:
  if nothing external depends on the old path, drop the re-export so the rule-pack
  detector stops advertising ownership of types it no longer defines; if backward
  compatibility is wanted, keep it but add a one-line comment noting it is a
  compatibility forwarder to `loaderkit.scan`.

## Finding 2 — The `line_hit` callback is now a vacuous indirection over the module's own type

- **Category:** ergonomics
- **Severity:** medium
- **Location:** `novel_ralph_skill/loaderkit/scan.py:65-104` (`scan_pattern`'s
  `line_hit` parameter and the per-hit `line_hit(...)` call at line 99-100), with
  the byte-identical callback supplied at
  `novel_ralph_skill/rulepack/detect.py:212` and
  `novel_ralph_skill/ledger/detect.py:245`
  (`line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line)`).

`scan_pattern` takes a `line_hit: Callable[[int, int], LineHit]` factory and
constructs every hit through it. The module docstring (scan.py:12-14) and the
developers' guide (developers-guide.md:1743-1746) both justify this indirection
as "the seam that keeps it free of any `Rule`/`Device` knowledge, so this module
never imports a pack-domain hit type". That justification was true under 7.2.2,
when `LineHit` lived in `rulepack.detect`. It is now **circular**: 7.2.3 moved
`LineHit` *into* `loaderkit.scan`, so the callback constructs the very type the
module owns and already imports. The seam no longer protects against any domain
coupling — both call sites pass the identical lambda that simply forwards to the
`LineHit` constructor, so the abstraction is pure overhead: a duplicated closure
allocated inside each detector's per-entity loop, plus a callback-contract test
(`test_scan_pattern_builds_every_hit_via_line_hit_callback`) that now pins a
factory hook with no remaining purpose. This is precisely the "neutral default"
simplification 7.2.2 Finding 3 anticipated once the shapes became neutral; the
relocation landed but the simplification did not.

- **Proposed fix:** Drop the `line_hit` parameter and have `scan_pattern`
  construct `LineHit(chapter=…, line=…)` directly (it already imports the type for
  its own annotations). Remove the duplicated lambda from both
  `rulepack.detect.detect` and `ledger.detect.detect_ledger`. If a future third
  pack family genuinely needs a different hit type, reintroduce a generic
  parameter then — but for the current two callers, both of which build the same
  `LineHit`, the callback adds no value. Update the `scan.py` docstring and the
  developers' guide passage to drop the now-circular "never imports a pack-domain
  hit type" rationale (the AST guard test already proves neutrality structurally).
  Replace or retire the callback-contract test accordingly, retaining the
  scan-order and per-line-count assertions it also makes.

## Finding 3 — Stale "single home" cross-references still point at `rulepack.detect`

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/ledger/__init__.py:14` (the
  `:class:` cross-reference to
  `novel_ralph_skill.rulepack.detect.ScannedChapter` as the "input type") and
  the matching prose in `novel_ralph_skill/ledger/detect.py:22-24`.

The ledger package docstring still names
`rulepack.detect.ScannedChapter` as its input type, framing the ledger as
borrowing the rule-pack domain's shape. After 7.2.3 the canonical home is
`loaderkit.scan.ScannedChapter`, and `ledger/detect.py` already imports it from
there. The docstring cross-reference therefore points a reader at a re-export
rather than the type's true definition, perpetuating the impression that the
ledger depends on the rule-pack domain for its input shape (the impression
Finding 1 shows is no longer warranted).

- **Proposed fix:** Update the cross-references in `ledger/__init__.py:14` and
  `ledger/detect.py:22-24` to point at
  `:class:`~novel_ralph_skill.loaderkit.scan.ScannedChapter``, and adjust the
  surrounding prose so the ledger is described as sharing the *neutral* loaderkit
  scan shape (its true parallel to rule-pack), not borrowing a rule-pack type.
  Fold this into the same pass as Finding 1 so code and docs move together.

## Finding 4 — `detect` and `detect_ledger` share a near-identical scan-aggregate skeleton

- **Category:** similarity
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/detect.py:178-222` (`detect`) and
  `novel_ralph_skill/ledger/detect.py:215-251` (`detect_ledger`).

Both detectors share the same outer loop shape: iterate the entity collection
(`pack.rules` / `ledger.devices`), call
`count, lines = scan_pattern(entity.compiled, chapters, line_hit=…)`, append
`_finding(entity, count=count, lines=lines, …)`, then wrap the findings in a
report with `passed=all(f.passed for f in findings)`. The bodies differ only in
the entity attribute, the `total_words` denominator (rule-pack-only), and the
report type. This is a thinner residue of the duplication 7.2.x set out to
consolidate: the inner scan body is shared, but the aggregation loop is still
hand-cloned per detector. It is not urgent — the `total_words` divergence and
the two distinct `_finding` signatures make a clean extraction non-trivial — but
it is worth recording so a future reader knows the residue is acknowledged, not
overlooked.

- **Proposed fix:** Optional. After Finding 2 removes the `line_hit` lambda, the
  remaining shared skeleton could be lifted into a small generic helper in
  `loaderkit` (for example
  `aggregate(entities, chapters, *, finding) -> tuple[Finding, ...]`) that runs
  the scan-and-`_finding` loop once and returns the findings tuple, leaving each
  detector to supply only its per-entity `_finding` closure and to assemble its
  own report (which carries the domain-specific `total_words`/report type). If
  the divergence is judged to outweigh the saving, leave the two loops as-is and
  add a one-line comment in each noting the deliberate parallel, so the pair is
  not later "re-merged" in a way that reintroduces the `total_words` coupling.

## Finding 5 — `scan_pattern` returns a count derivable from its own `lines` tuple

- **Category:** cqs
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/scan.py:65-104` (`scan_pattern`
  returns `tuple[int, tuple[LineHit, ...]]` as `(len(hits), tuple(hits))`).

`scan_pattern`'s return pairs a `count` with the `lines` tuple, but `count` is
always exactly `len(lines)` — the function computes `return len(hits),
tuple(hits)`. Both call sites destructure `count, lines = scan_pattern(...)` and
pass both onward to `_finding`, so the redundant scalar propagates through the
detector signatures (`_finding(..., count=count, lines=lines)`) even though
`count == len(lines)` is an invariant. This is mild redundant API surface: a
caller could let `count` and `lines` drift apart only by misusing the tuple, and
nothing documents that they are guaranteed equal.

- **Proposed fix:** Either return only `tuple[LineHit, ...]` and let callers use
  `len(...)` where they need the count (the simplest, since both callers already
  hold the tuple), or keep the pair but document in the `Returns` section that
  `count == len(lines)` by construction so the redundancy is a deliberate
  convenience, not a contract a caller must maintain. The first option is
  preferred; it removes a value that cannot disagree with the tuple and trims the
  `_finding` plumbing accordingly.

## Summary

The 7.2.3 relocation is high quality and closes most of the 7.2.2 audit: the two
neutral scan shapes now live in `loaderkit.scan` with thorough docstrings, the
dead `_require` and the thin scan wrappers are gone, and an AST guard plus a
callback test pin the new home. Two findings are worth promoting because they are
the *unfinished half* of this very task. First, three consumers
(`commands/_desloppify.py` and two ledger tests) still import the relocated
`ScannedChapter` through the `rulepack.detect` re-export, so the
`ledger → rulepack` and command → `rulepack` domain edges the move targeted
persist; repointing them at `loaderkit.scan` (and deciding the fate of the
re-export) finishes the relocation (Finding 1). Second, now that `LineHit` lives
in `loaderkit.scan`, the `line_hit` callback is a circular indirection over the
module's own type — both detectors pass the identical lambda — so it should be
dropped in favour of constructing `LineHit` directly, with the stale
"never imports a pack-domain hit type" rationale removed from the code and the
developers' guide (Finding 2). The remaining findings (a stale ledger docstring
cross-reference, a near-duplicated detector skeleton, and a redundant `count`
return) are low-severity tidy-ups that fold naturally into the same pass.
