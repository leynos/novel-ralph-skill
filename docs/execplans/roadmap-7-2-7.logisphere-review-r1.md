# Logisphere design review — roadmap 7.2.7, round 1

Adversarial pre-implementation review of
`docs/execplans/roadmap-7-2-7.md`. The plan was read from disk and every
load-bearing claim verified against the real source under
`novel_ralph_skill/loaderkit`, `novel_ralph_skill/rulepack`,
`novel_ralph_skill/ledger`, and `tests/`, plus the roadmap entry, ADR-003, and
ADR-001.

## Verdict: PROCEED WITH CONDITIONS (revise WI4 enumeration before implementing)

The design is sound. The mechanism choices are correct and the invariants are
genuinely protected. The blocking items below are scope-completeness gaps in
Work item 4's edit list, not design flaws: an implementer following WI4
literally could leave a dangling `_ERRORS` import or a half-repointed call site.

## What verifies (independently confirmed against source)

- The two identity-lambda seams exist exactly as described:
  `loaderkit/scan.py::scan_pattern` types `line_hit` as
  `Callable[[int, int], LineHit]` and `LineHit` is `frozen, kw_only, slots`;
  `loaderkit/parse.py::build_entries` types `build_entry` as
  `Callable[[Mapping, int], T]` and calls it positionally
  (`build_entry(entry, index)`), while `_rule`/`_device` are `*, index`.
  Both detect call sites pass the byte-identical
  `line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line)`
  (`rulepack/detect.py:207`, `ledger/detect.py:245`); both parse sites pass the
  `build_entry=lambda entry, index: …` shim (`rulepack/parse.py:279`,
  `ledger/parse.py:194`).
- The detect-site lambda captures only its own parameters, not the
  `for rule in pack.rules` loop variable, so binding `LineHit` directly carries
  no late-binding-closure hazard. WI1 is safe.
- The `_coerce.py` divergence is real: `ledger/_coerce.py` exports a bare
  `_require`; `rulepack/_coerce.py` does not. `ledger/_fields.py` consumes
  `_Mapping, _require, _require_int, _where`. D-REQUIRE-SURFACE (one uniform
  surface) is the right reconciliation.
- `functools.partial` genuinely cannot rename a keyword, so D-ID-KEYWORD's
  bound-bundle mechanism — with the public `rule_id=`/`device_id=` kept inside
  the `content_error` callable and an internal `offending_id` on the helpers —
  is the correct way to preserve the public error contract. The roadmap
  sanctions either `bind_coercion` or `partial`; the bundle is the right pick.
- `compile_pattern(pattern, *, errors: CoercionErrors, offending_id: str)`
  takes a raw `CoercionErrors`, so WI4's `errors=_COERCION.errors` is wired
  correctly **provided** `BoundCoercion` exposes `.errors` (it does, in the
  Interfaces section).
- No-external-surface finding (D-NO-EXTERNAL-RESEARCH) confirmed independently:
  `grep -rlnE "cuprum|catalogue|subprocess|sh\.run|cyclopts|pytest_timeout"`
  over the three packages returns nothing. The locked-library
  (Cyclopts / pytest-timeout / uv / cuprum) citation requirement does **not**
  bite this task; D-NO-EXTERNAL-RESEARCH is sound, not an evasion.
- ADR-001 (detect-only, message-is-behaviour) and ADR-003 (no import cycle;
  `loaderkit` imports neither pack) are preserved: `bind_coercion` stays in
  `loaderkit/coerce.py`, parameterized on `content_error` + noun pair, naming
  no pack type.
- The roadmap entry's success criteria map one-to-one onto the plan's four
  observable criteria.

## Blocking — WI4 edit list is incomplete (will break the build if followed literally)

1. **`_ERRORS` non-helper call sites are not enumerated.** Both `parse.py`
   modules import `_ERRORS` and pass it to **three** primitives, not one:
   `resolve_schema_version(..., errors=_ERRORS)`,
   `build_entries(..., errors=_ERRORS)`, and
   `compile_pattern(..., errors=_ERRORS, ...)`. WI4 edit 3 names only the
   `compile_pattern` repoint (`errors=_COERCION.errors`). If `_ERRORS` is
   removed from `_coerce.py` (replaced by `_COERCION`), the
   `resolve_schema_version` and `build_entries` call sites in both
   `rulepack/parse.py` (lines ~264, ~274) and `ledger/parse.py` (lines ~182,
   ~189) break. Either keep an `_ERRORS = _COERCION.errors` alias in each
   `_coerce.py` **or** explicitly list those two repoints per family. State
   which, and enumerate all `errors=` sites, so the implementer does not leave a
   half-repointed module.

2. **`ledger/_fields.py` repoints are under-specified.** `_fields.py` imports
   four names (`_Mapping, _require, _require_int, _where`) and calls
   `_where` / `_require_int` / `_require` across ~13 sites (`_positive_int`,
   `_allowed_chapters`, `_rationing_fields`). WI4 edit 4 names only
   `_require → _COERCION.require`. The `_where → _COERCION.where` and
   `_require_int → _COERCION.require_int` repoints, and the `_Mapping` handling
   (`_fields.py` imports `_Mapping`, so the `type _Mapping = Mapping` re-export
   must survive in `ledger/_coerce.py` or `_fields.py` must re-source it),
   are not stated. Enumerate them.

3. **`rulepack/parse.py` has ~14 helper call sites, not "etc."** `_where`,
   `_require_int`, `_require_str`, `_reject_unknown_keys` are called throughout
   `_resolve_basis`, `_resolve_page_words`, `_rule`, and `parse_rulepack`. WI4
   edit 3 gives two examples and an "etc.". For a roadmap task whose Tolerance
   caps scope at 8 files / ~250 net lines, the plan should either give the full
   per-file site count (rulepack/parse.py ~14, ledger/_fields.py ~13,
   ledger/parse.py ~4 helper sites plus the `_ERRORS` sites) or confirm the
   churn stays within the 250-line tolerance. As written, an implementer cannot
   tell from WI4 whether the change fits the declared envelope.

## Advisory — non-blocking, would strengthen the plan

- **Pre-mortem (Doggylump).** The most likely incident path is a *silent*
  message change: an implementer, repointing `_where` call sites, accidentally
  passes `offending_id` positionally where the old keyword `rule_id=`/`device_id=`
  was used, transposing it with another positional argument on a multi-arg
  helper (`reject_unknown_keys(mapping, allowed, offending_id=…)`). The snapshot
  suites are the safety net, but the plan should call out keeping `offending_id`
  **keyword** at the call sites (the bundle methods declare it `*, offending_id`
  for `reject_unknown_keys`/`require*`, positional-or-keyword only for `where`)
  so a transposition is a TypeError, not a wrong-id message. The Interfaces
  signatures already make `offending_id` keyword-only on the multi-arg
  methods — good — but WI4's example
  `_COERCION.reject_unknown_keys(entry, _RULE_KEYS, offending_id=...)`
  should be the mandated form, not illustrative.

- **Alternatives checkpoint (Wafflecat).** The strongest alternative to a
  `BoundCoercion` dataclass-of-methods is a `functools.partial` set returned in
  a frozen `NamedTuple`/`dataclass` (partials over the free functions, with
  `offending_id` left free). It trades away the keyword-rename (which is why the
  plan rejected bare `partial`) but, since `offending_id` is *not* being renamed
  (only `rule_id`/`device_id` is, and that lives inside `content_error`), a
  partial bundle is in fact viable and is shorter. The plan's bound-method
  bundle is defensible (clearer typing, one `errors` attribute for the
  `compile_pattern`/`resolve_schema_version` sites), but D-ID-KEYWORD's stated
  rationale ("partial cannot rename a keyword") slightly overstates the case:
  partial does not *need* to rename `offending_id`. Recommend tightening the
  rationale to "a partial bundle works too, but a bound dataclass gives one
  typed `.errors` handle for the raw-`CoercionErrors` consumers and explicit
  method signatures" rather than implying partial is infeasible.

- **Buzzy Bee / Dinolump.** No scaling or long-term-viability concerns: this is
  a bounded internal refactor that *reduces* surface (removes two forwarder
  modules and four lambdas). The third-family test (WI3) is the right
  anti-regression pin. Confirm the new `coerce.py` stays under 400 lines after
  the factory + `BoundCoercion` land (plan says ~254 today; the bundle plus
  factory plus docstrings could add 80–120 lines — interrogate demands 100%
  docstrings on every method — so verify the cap explicitly in WI3's
  validation, which currently asserts "coerce.py under 400 lines" but does not
  budget the docstring cost).

## Required to clear round 1

Re-issue WI4 (and WI3's line-budget check) with the full call-site inventory:
every `errors=_ERRORS` site, every `_where`/`_require*`/`_reject_unknown_keys`
site in `rulepack/parse.py`, `ledger/parse.py`, and `ledger/_fields.py`, the
`_Mapping` re-export disposition, and a statement that the total churn fits the
8-file / 250-line Tolerance. Mandate keyword `offending_id` at the multi-arg
call sites. These are addressable on paper; no design change is needed.
