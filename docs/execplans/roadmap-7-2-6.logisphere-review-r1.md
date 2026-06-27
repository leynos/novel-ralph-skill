# Logisphere design review — roadmap 7.2.6 — Round 1

Verdict: **Revise** (one blocking defect; otherwise the mechanism is sound and
verified against real source).

Reviewed against: the live `loaderkit`, `rulepack/parse.py`, `ledger/parse.py`,
their `_coerce` bindings, the rule-pack fixtures and loader/property suites, the
cross-command and desloppify snapshots, the `loaderkit` import-direction guard,
and the developers' guide. Skills: `logisphere-design-review`, `python-router`
(→ `python-types-and-apis`, `python-data-shapes`). Design docs cited by the
plan (§6.1/§6.3, ADR-003) confirmed consistent with the mechanism.

## What was verified and holds

- **Skeleton API is real.** `loaderkit.coerce.reject_unknown_keys(mapping,
  allowed, *, errors, offending_id)` and `require_int(..., *, errors,
  offending_id)` exist exactly as the Work item 1 signature calls them, as do
  `loaderkit.load.entries(..., *, array_key, messages, errors)`,
  `reject_duplicate_ids(ids, *, errors)`, and `errors.content_error(msg,
  offending_id)`. The skeleton calling the `loaderkit` primitives directly
  (bypassing the per-package `_reject_unknown_keys`/`_require_int` forwarders) is
  correct: those forwarders only pre-bind the bundle and rename the id kwarg.
- **Neutral-leaf guard auto-covers the new module.**
  `tests/test_loaderkit_scan.py::_loaderkit_module_paths` globs
  `loaderkit/*.py` at collection time, so `parse.py` is picked up with no test
  edit. Work item 4's claim is correct; the focused `ast` pin in Work item 1 is
  redundant belt-and-braces, which is fine.
- **`entry_id` projection is genuinely needed and correctly handled.**
  `reject_duplicate_ids` takes `Iterable[str]`, so the `.id` projection must live
  at the call site; the `entry_id: Callable[[T], str]` parameter (default
  `lambda e: e.id`) keeps the skeleton from naming a pack attribute. Sound.
- **PEP 695 generic syntax is idiomatic here.** `requires-python >= 3.14`;
  `def f[T](...)` already used in `_freeze.py` and `contract/finding_outcome.py`.
- **D-NO-EXTERNAL-RESEARCH is appropriate.** The parse modules and `loaderkit`
  import no cuprum, Cyclopts, subprocess, `sh`, or pytest-timeout; this is a pure
  in-process `Mapping`→dataclass refactor. The absence of firecrawl/library
  citations is correct, not a gap.
- **File-size and scope tolerances hold** (rulepack/parse.py 304, ledger 226;
  both shrink). The plan's 305/227 figures are off by one — stale, immaterial.

## BLOCKING

1. **The `pack`-read reordering inverts the real fault precedence, and the plan
   mislabels that inversion as "preserving the existing fault-ordering".**
   Original `parse_rulepack` order is: reject-unknown-keys → require
   `schema_version` → version check → **require `pack`** → `entries` → build →
   dup-ids. The plan (Work item 2) moves the `pack` read to *after* the whole
   skeleton call, i.e. after `entries`/build/dup-ids, and states the read "must
   stay after the skeleton call so a malformed `schema_version` or entry array is
   reported before a missing `pack` (preserving the existing fault-ordering the
   snapshots pin)". That is backwards: in the original, a missing `pack` is
   reported *before* any entry-array fault. For an input that is simultaneously
   missing `pack` **and** carrying an absent/empty/malformed `rule` array, the
   original raises the missing-`pack` `RulePackError`; the plan would raise the
   entry-array `RulePackError` instead. Same type and `rule_id is None`, but a
   different message — a behaviour change, inside a plan whose first
   Constraint is "No behaviour change, no message change".

   Why it currently escapes the gate (and why that is not a defence): no fixture
   or snapshot combines a missing `pack` with a bad `rule` array.
   `missing-pack.toml` carries a *valid* one-rule array; `missing-rule-array.toml`
   and `empty-rule-array.toml` both carry a valid `pack`. The property generators
   mutate one field of a well-formed pack and never drop `pack` while corrupting
   the array. So all suites stay green — the regression is latent, not caught. A
   "no behaviour change" refactor that relies on the test corpus *not* exercising
   the changed path is exactly what a design review exists to stop.

   The plan's own D-SKELETON-RETURNS-TUPLE rationale concedes the mechanism: it
   says the tuple return "lets the rule-pack call site interleave its `pack` read
   between the schema-version resolve and the *result construction*" — i.e. after
   `entries`/build, not between schema-version and `entries` where the original
   reads it. The skeleton bundles unknown-keys + schema-version + entries +
   build + dup-ids into one call, so the call site can only place `pack`
   before or after the *whole* skeleton; it cannot reproduce the original
   pack-before-entries precedence by interleaving.

   Required fix (planner's choice, pick one and make it explicit):
   - **(a) Preserve true precedence.** Read `pack` *before* the skeleton call
     (after the skeleton — or a small pre-step — has run unknown-key rejection
     and the schema-version resolve, but before `entries`). This likely means the
     rule-pack call site cannot use the single all-in-one skeleton as drawn;
     either the skeleton must expose the unknown-key/schema-version resolve
     separately from the entries/build/dup-ids tail, or the `pack` read must be
     accepted as a precedence change per (b). Re-examine D-SKELETON-RETURNS-TUPLE
     against this constraint.
   - **(b) Accept the precedence change explicitly.** Drop the false
     "preserving the existing fault-ordering" claim, record in the Decision Log
     and Constraints that missing-`pack` now yields to an entry-array fault, and
     add a fixture/test (e.g. `missing-pack-and-empty-array.toml`) that pins the
     *new* precedence so it is a deliberate, tested decision rather than an
     untested accident. Note this still technically violates the stated "no
     behaviour change" Constraint, so it needs sign-off, not silent acceptance.

   Either way the plan must stop asserting, falsely, that the reorder preserves
   ordering.

## ADVISORY

- The ledger side (Work item 3) is genuinely clean: the ledger has no top-level
  string field, so there is no analogue reorder and no precedence question. Worth
  stating in the plan so the asymmetry with the rule pack is explicit.
- Work item 2's instruction "verify by running the suites" is the very check
  that masks the blocking issue — the suites pass *because* no fixture exercises
  the combined fault. Replace "verify by running the suites" with an explicit
  reasoning step about the missing-`pack` + bad-array intersection.
- Line-count figures (305/227) are stale by one; refresh to 304/226 or drop the
  exact numbers.
