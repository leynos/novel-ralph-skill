# Post-merge audit — roadmap task 7.2.2

Task 7.2.2 consolidated the near-verbatim TOML-loading and per-line scan
primitives that were cloned across the `rulepack` and `ledger` packages into a
new shared `novel_ralph_skill/loaderkit/` package, parameterized on an
error-factory bundle (`CoercionErrors`) and a verbatim-message bundle
(`EntriesMessages`). Both packages now reroute their `_coerce`, `entries`,
`compile_pattern`, `reject_duplicate_ids`, `load_toml`, and `scan_pattern` onto
the shared bodies, supplying only their error type and noun pair. The change
resolves the `audit:8.1.2` reroute that flagged the deliberate near-copy.

This audit reviews the merged state at `origin/main` (commit `50d23c5`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The consolidation itself is clean, well-documented, and well-tested: the shared
`loaderkit` primitives carry thorough numpydoc docstrings, the binding seam is
recorded in the developers' guide and the harness design, and three dedicated
test modules pin the primitives. The material findings concern a **residual
cross-domain coupling** the consolidation did not finish, plus a handful of
smaller duplication, dead-code, and test-locality issues.

Documentation and skills relied on for this audit:
`docs/novel-ralph-harness-design.md` (§6, §6.1, §6.3), `docs/developers-guide.md`
("The shared loader primitives (`loaderkit`)"), `docs/adr-001`, `docs/adr-003`,
and `AGENTS.md` (quality gates, 400-line file cap, en-GB Oxford spelling). Code
navigation used `leta`; history was traced with `sem` and `git show 50d23c5`.

## Finding 1 — `ledger.detect` runtime-imports the shared scan types from `rulepack.detect` (cross-domain coupling)

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `novel_ralph_skill/ledger/detect.py:35` (runtime
  `from novel_ralph_skill.rulepack.detect import LineHit`), with the
  `ScannedChapter` type imported under `TYPE_CHECKING` at
  `novel_ralph_skill/ledger/detect.py:41`; the dependency is also documented at
  `novel_ralph_skill/ledger/__init__.py:14` and `ledger/detect.py:22-24`.

Task 7.2.2 moved the shared *scan body* into the neutral `loaderkit` home, but
left the two structural types the scan reads and writes — `ScannedChapter`
(input) and `LineHit` (output) — defined in `rulepack/detect.py`. The
device-ledger domain therefore now reaches sideways into the rule-pack domain
for those types at **runtime** (`LineHit`), not merely under `TYPE_CHECKING`.
The design states loaderkit is the single home for the schema-agnostic loader
primitives so "a third pack family inherits them instead of cloning a third
copy" (design §6); a third pack family inheriting `scan_pattern` would likewise
have to import `rulepack.detect` to obtain the hit type, which is the very
sibling-to-sibling domain edge the neutral home was introduced to remove.

`loaderkit/scan.py`'s own docstring claims it "carries no `Rule`/`Device`
knowledge", yet its public signature is typed entirely in terms of
`rulepack.detect.ScannedChapter` and `rulepack.detect.LineHit`, so the neutral
module is type-coupled to one of its two consumers. The developers' guide frames
this as acceptable because the `loaderkit → rulepack` edge is only under
`TYPE_CHECKING` and so does not form an import cycle — but that framing addresses
only the cycle risk and silently accepts the `ledger → rulepack` domain leak.

- **Proposed fix:** Move the two domain-neutral scan shapes `ScannedChapter` and
  `LineHit` out of `rulepack/detect.py` into a neutral home — most naturally a
  new `novel_ralph_skill/loaderkit/scan.py`-adjacent module (for example
  `loaderkit/hits.py`, or promote them into `loaderkit/scan.py` itself since
  `scan_pattern` already owns their semantics). Re-export them from
  `rulepack.detect` for backward compatibility if any external caller depends on
  the old path. Then retype `scan_pattern` against the neutral types, drop the
  runtime `from novel_ralph_skill.rulepack.detect import LineHit` in
  `ledger/detect.py`, and have both `rulepack.detect` and `ledger.detect` import
  the shapes from the neutral home. This removes the `ledger → rulepack` and
  `loaderkit → rulepack` edges entirely and makes loaderkit's "no `Rule`/`Device`
  knowledge" docstring literally true. Update the developers' guide passage
  ("still defined in `rulepack/detect.py`") and design §6 accordingly.

## Finding 2 — Tests and command layer reach into `rulepack.detect` for shared shapes

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** `tests/test_loaderkit_scan.py:21` and
  `tests/test_loaderkit_scan.py:5-6`,
  `tests/test_ledger_properties.py:40` (each
  `from novel_ralph_skill.rulepack.detect import ScannedChapter` /
  `LineHit`); the ledger command body
  `novel_ralph_skill/commands/_desloppify_ledger.py` constructs ledger inputs
  through the same `rulepack.detect.ScannedChapter` type.

The shared-primitive unit test for `loaderkit.scan` imports its fixtures'
`ScannedChapter`/`LineHit` from `rulepack.detect`, so a test that exists to pin
a *neutral* primitive is coupled to the rule-pack domain. Likewise the ledger
command path constructs `rulepack.detect.ScannedChapter` instances to feed the
ledger detector — a ledger-domain command reaching into the rule-pack domain for
its input shape. This is the same leak as Finding 1 surfacing at the test and
command layers, and it is symptomatic rather than independent.

- **Proposed fix:** Once Finding 1 relocates the shapes to a neutral home, repoint
  these imports (`tests/test_loaderkit_scan.py`, `tests/test_ledger_properties.py`,
  and `commands/_desloppify_ledger.py`) at the neutral module. The
  `loaderkit.scan` unit test in particular should construct its fixtures from the
  neutral types so it never imports a consumer package.

## Finding 3 — `_scan_rule` and `_scan_device` are now byte-identical thin wrappers

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/detect.py:149-178` (`_scan_rule`) and
  `novel_ralph_skill/ledger/detect.py:108-135` (`_scan_device`).

After the consolidation both private wrappers reduce to the identical body
`return scan_pattern(<entity>.compiled, chapters, line_hit=lambda chapter, line:
LineHit(chapter=chapter, line=line))`, differing only in the parameter name
(`rule` versus `device`) and a near-identical docstring. The `line_hit` lambda is
identical in both. This is a thinner residue of exactly the duplication 7.2.2 set
out to remove: the scan *body* is shared, but each detector still carries a
private one-line wrapper plus a duplicated `line_hit` closure.

- **Proposed fix:** Inline the two wrappers at their single call sites
  (`detect`/`detect_ledger` each call their wrapper exactly once), passing
  `scan_pattern(rule.compiled, chapters, line_hit=_LINE_HIT)` directly, where
  `_LINE_HIT` is a shared module-level callable. If the neutral `LineHit` from
  Finding 1 lands, the `line_hit` closure can become a single neutral default
  (for example `scan_pattern` defaulting `line_hit` to the `LineHit` constructor),
  removing the duplicated lambda from both detectors entirely. Verify no test
  imports `_scan_rule`/`_scan_device` directly before removing them.

## Finding 4 — Dead `_require` wrapper in `rulepack/_coerce.py`

- **Category:** complexity
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/_coerce.py:55-57` (`_require`).

The rule-pack binding re-exports a `_require` wrapper, but `rulepack/parse.py`
never imports it (it uses `_require_int`, `_require_str`, `_reject_unknown_keys`,
and `_where` only); a repo-wide search finds no rule-pack call site. The ledger's
mirror `_coerce.py` does need its `_require` (consumed by `ledger/_fields.py:94`
for `allowed_chapters`), so the two bindings are no longer symmetric in their used
surface — `_require` is live in `ledger` and dead in `rulepack`. This is both
dead code and a quiet inconsistency: the two `_coerce` modules read as parallel
clones but one exports an unused forwarder.

- **Proposed fix:** Delete the unused `_require` (and its import from
  `loaderkit.coerce`'s `require` if it becomes unused) from
  `rulepack/_coerce.py`. If the intent is to keep the two binding modules
  byte-symmetric for readability, document that explicitly with a one-line comment
  on the rule-pack `_require` noting it is retained for binding symmetry only;
  otherwise prefer the deletion, as `deadcode`/Ruff will flag the unused export.

## Finding 5 — The five `_coerce` binding wrappers are themselves near-duplicated across the two packages

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/_coerce.py:43-67` and
  `novel_ralph_skill/ledger/_coerce.py:46-70`.

The consolidation removed the duplicated coercion *bodies*, but each package now
carries a near-identical block of five forwarder wrappers (`_where`,
`_reject_unknown_keys`, `_require`, `_require_str`, `_require_int`, plus the
`_Mapping` alias) differing only in the keyword name (`rule_id=` versus
`device_id=`) and the bound `_ERRORS` bundle. This is a second, thinner layer of
the same cross-package similarity. It is largely justified — the differing keyword
name is the deliberate mechanism that keeps `parse.py` call sites unchanged — but
it is worth recording that the "one body each" guarantee the design claims (design
§6) holds for the primitives, not for these per-package binding shims, which
remain a near-clone pair.

- **Proposed fix:** This is acceptable as-is given the keyword-name constraint;
  no change is mandatory. If a third pack family is added (as the design
  anticipates),
  consider generating the binding shims from a single factory that takes the noun
  pair, error type, and id-keyword name, rather than hand-cloning the five
  wrappers a third time. Record the rationale (call-site stability via the
  per-package id keyword) in a short comment so a future reader does not "re-merge"
  the shims and break the `rule_id=`/`device_id=` ergonomics.

## Finding 6 — Line-by-line scan discipline is documented verbatim in three places

- **Category:** docs-gap
- **Severity:** low
- **Location:** the "`.` cannot cross `\n`, so a per-line scan makes line numbers
  exact" rationale appears in `novel_ralph_skill/loaderkit/scan.py:5-9`,
  `novel_ralph_skill/rulepack/detect.py:11-23`, and
  `novel_ralph_skill/ledger/detect.py:11-17`, each restating the same v1
  single-line-coverage limitation.

The same load-bearing discipline (no-flags compilation, per-line `finditer`,
multi-token offenders needing a bounded `[^\n]{0,N}?` window) is now explained in
full in the shared scan module *and* re-explained in both detectors. With the body
consolidated into `loaderkit.scan`, the canonical explanation should live there
once, with the detectors referring to it rather than restating it. The current
triple-statement risks the three copies drifting as the v1 limitation evolves.

- **Proposed fix:** Keep the authoritative explanation in `loaderkit/scan.py`
  (which now owns the behaviour) and trim the `rulepack.detect` and
  `ledger.detect` module docstrings to a one-line pointer
  ("scans line by line; see `loaderkit.scan` for the no-flags/per-line rationale
  and the v1 multi-line limitation"). This keeps the limitation documented once
  at its true home and removes the drift surface.

## Finding 7 — `loaderkit.scan` lacks a direct ledger-shaped regression test

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_loaderkit_scan.py` (covers the rule-pack-shaped use
  only); the ledger detector's reliance on `scan_pattern` is exercised only
  indirectly through `tests/test_ledger_properties.py` and the ledger detect
  suite.

`scan_pattern` is the single shared body both detectors now depend on, but its
dedicated unit test constructs only `rulepack`-flavoured `ScannedChapter`/`LineHit`
fixtures. The primitive is genuinely package-agnostic, so a single suite suffices
in principle; however, the test's framing ("the byte-identical behaviour the
former `_scan_rule`/`_scan_device` bodies share") asserts an equivalence it does
not directly demonstrate for the device path — it pins one caller and trusts the
other by symmetry. A regression that broke only the `line_hit` callback contract
(for example, argument order) would be caught for `rulepack` but the ledger path
relies on its own larger property suite to notice.

- **Proposed fix:** Add one explicit case to `tests/test_loaderkit_scan.py` that
  drives `scan_pattern` through a `line_hit` callback with a distinct sentinel
  return type (not `LineHit`) to pin the `(chapter_number, line_index)` callback
  contract independently of either domain's hit type. This directly proves the
  primitive's neutrality and protects the callback signature both detectors bind
  to. After Finding 1, also assert the neutral hit type is what both packages
  re-export.

## Summary

The 7.2.2 consolidation is high quality: the shared `loaderkit` primitives are
well-factored, thoroughly documented, and pinned by dedicated tests, and the
binding seam is recorded in both the design and the developers' guide. The one
finding worth promoting is the **residual cross-domain coupling** (Findings 1–2):
the shared scan *body* moved to a neutral home, but the scan's input/output types
(`ScannedChapter`, `LineHit`) stayed in `rulepack.detect`, so the `ledger` domain
— and a hypothetical third pack family — must runtime-import them from the
rule-pack domain. Relocating those two neutral shapes into `loaderkit` finishes
the consolidation, makes `loaderkit.scan`'s "no `Rule`/`Device` knowledge"
docstring literally true, and removes the `ledger → rulepack` edge. The remaining
findings (duplicated thin wrappers, a dead `_require`, triple-stated scan docs,
and a callback-contract test gap) are low-severity tidy-ups that naturally fold
into the same relocation pass.
