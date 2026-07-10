# Retire the parse/scan identity-lambda builder seams and collapse the per-family `_coerce.py` forwarder shims

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

Roadmap task 7.2.7 retires the last two clone-per-family seams the `loaderkit`
consolidation surfaced and task 7.2.6 left standing. There are exactly two, and
they are independent:

1. **The identity-lambda builder seams.** Two shared `loaderkit` primitives force
   every caller to wrap a keyword-only constructor in a byte-identical identity
   lambda:
   - `novel_ralph_skill/loaderkit/parse.py::build_entries` types its
     `build_entry` parameter as `Callable[[Mapping, int], T]` (positional
     `index`), but the per-family builders `_rule`/`_device` are keyword-only
     (`*, index`), so both `parse_rulepack` and `parse_ledger` pass
     `build_entry=lambda entry, index: _rule(entry, index=index)` — a pure
     positional-to-keyword shim.
   - `novel_ralph_skill/loaderkit/scan.py::scan_pattern` types its `line_hit`
     parameter as `Callable[[int, int], LineHit]` (positional), but `LineHit` is
     `kw_only=True`, so both `rulepack/detect.py` and `ledger/detect.py` pass
     `line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line)`.

   A third pack family would clone a third copy of each lambda. The fix is a
   positional/keyword convention fix on the two callback seams so the keyword-only
   constructor binds **directly** (`build_entry=_rule`, `line_hit=LineHit`) with
   no wrapper.

2. **The per-family `_coerce.py` forwarder shims.**
   `novel_ralph_skill/rulepack/_coerce.py` and `novel_ralph_skill/ledger/_coerce.py`
   are near-identical thin **bindings**: each constructs one
   `loaderkit.coerce.CoercionErrors` bundle and re-exports a set of
   underscore-named one-line forwarders to the shared `loaderkit.coerce` bodies
   with the bundle bound. Their only real differentiator is the public id-keyword
   rename — `rule_id=` versus `device_id=` — and the two shim surfaces have
   **diverged**: the ledger shim additionally exports a bare `_require` (consumed
   by `ledger/_fields.py`) that the rule-pack shim does not. A third family would
   clone a third forwarder set. The fix collapses both shims onto a shared
   `bind_coercion` factory in `loaderkit/coerce.py` that returns one bound bundle
   exposing every coercion helper with the id positional/keyword already bound,
   so a third family supplies one `bind_coercion(...)` call rather than cloning
   a forwarder module.

After this change a maintainer adding a third loader family binds both seams
rather than cloning them: they pass their keyword-only builder/constructor
directly (no lambda) and call `bind_coercion(...)` once (no `_coerce.py` clone).

The public `rule_id`/`device_id` keywords on the typed error channels, each typed
error channel itself (`RulePackError`/`RulePackFileError`,
`LedgerError`/`LedgerFileError`), and every operator-facing message string stay
**byte-for-byte unchanged**. This is the success criterion the roadmap fixes and
the snapshot suites pin.

Success is observable four ways:

1. `grep -rn "lambda" novel_ralph_skill/rulepack/parse.py
   novel_ralph_skill/ledger/parse.py novel_ralph_skill/rulepack/detect.py
   novel_ralph_skill/ledger/detect.py` returns no `build_entry=`/`line_hit=`
   identity lambda.
2. `novel_ralph_skill/rulepack/_coerce.py` and
   `novel_ralph_skill/ledger/_coerce.py` either no longer exist or contain a
   single `bind_coercion(...)` binding with no per-family forwarder bodies.
3. A new `loaderkit` test pins both shared seams (the keyword-only direct bind and
   the `bind_coercion` factory) against a test-local third family with **no**
   import of any real pack type, proving a third family inherits rather than
   clones.
4. `make all` is green and the rule-pack, ledger, and `loaderkit` snapshot suites
   show no message drift.

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- **Worktree.** All edits happen inside the git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-7`. The
  root/control worktree is read-only.
- **Message stability.** Every operator-facing message string raised by the
  coercion helpers, the parse skeleton, and the two loaders is unchanged. This
  includes the unsupported-version sentences, the unknown-key listings, the
  missing/wrong-type sentences, the `allowed_chapters`/window sentences, and the
  duplicate-id and array-extraction sentences. The rule-pack and ledger snapshot
  suites (`tests/test_ledger_snapshots.py`, and the rule-pack loader/snapshot
  tests) are the pin; no `--snapshot-update` is permitted in this task.
- **Public error contract.** The typed error channels keep their names and their
  public id keyword: `RulePackError(msg, rule_id=...)`,
  `LedgerError(msg, device_id=...)`, and the `*FileError` subclasses are
  untouched. The `rule_id=`/`device_id=` keyword is the *public* surface callers
  in `parse.py`/`_fields.py` use; collapsing the shims must not change those call
  sites' keyword (see Decision D-ID-KEYWORD).
- **Fault precedence.** The rule pack's live `pack`-before-`entries` fault
  precedence (Decision D-SKELETON-HEAD-TAIL from 7.2.6) is preserved: `pack` is
  still read at the head/tail seam in `parse_rulepack`. This task touches the
  `build_entry=`/`line_hit=` argument only, never the head/tail ordering.
- **Layering / no import cycle.** `loaderkit` imports neither `rulepack` nor
  `ledger` at runtime or under `TYPE_CHECKING` (design §3.1; ADR-003). The
  `bind_coercion` factory lives in `loaderkit/coerce.py` and stays pack-agnostic:
  it is parameterized on a `content_error` callable and the noun pair, exactly as
  `CoercionErrors` already is.
- **Behaviour, not just compile.** Each work item must leave `make all` green and
  ships or updates a test that fails before the change and passes after.
- **File-size cap.** No source file exceeds the AGENTS.md 400-line cap. Both
  `_coerce.py` shims are tiny; the shared additions to `loaderkit/coerce.py` are
  small. Confirm `loaderkit/coerce.py` stays under 400 lines after the factory
  lands (it is ~254 lines today).
- **Spelling.** All prose, comments, docstrings, and commit messages use en-GB
  Oxford spelling (`-ize`/`-yse`/`-our`).

## Tolerances (exception triggers)

- **Scope.** If the implementation requires changing more than 10 source files or
  more than ~250 net lines, stop and escalate. The 10 enumerated source files are:
  the two loaderkit primitives (`loaderkit/scan.py`, `loaderkit/parse.py`),
  `loaderkit/coerce.py`, `loaderkit/__init__.py`, the two `_coerce.py` shims,
  `ledger/_fields.py`, the two `parse.py` and the two `detect.py` call sites — plus
  their tests. The verified per-file call-site inventory in Work item 4 (rule-pack
  parse 13 sites, ledger parse 5 sites, ledger `_fields` 9 sites, all in-place
  keyword renames) plus the WI3 line budget (see below) is confirmed to fit this
  envelope — see Decision D-WI4-INVENTORY and Decision D-WI3-BUDGET.
- **Interface.** If collapsing the shims forces a change to any *public* call
  site's id keyword (`rule_id=`/`device_id=` in `parse.py`/`_fields.py`) or to any
  error-channel constructor signature, stop and escalate — the roadmap fixes those
  as unchanged.
- **Message drift.** If any snapshot or message-pinning test would need updating,
  stop and escalate: the task forbids message drift.
- **Dependencies.** This task adds no external dependency. `functools.partial` (if
  used) is stdlib. If a non-stdlib dependency seems required, stop and escalate.
- **Iterations.** If `make all` still fails after 3 fix attempts on a single work
  item, stop and escalate.
- **Ambiguity.** If the `_require` divergence cannot be reconciled without a
  message change (it can — see Decision D-REQUIRE-SURFACE), stop and present
  options.

## Risks

    - Risk: Dropping the `build_entry` identity lambda changes the call
      convention the skeleton uses, so `build_entries` could call the builder with
      a positional `index` while `_rule`/`_device` are keyword-only, raising
      TypeError at runtime.
      Severity: medium
      Likelihood: medium
      Mitigation: Make `build_entries` call the builder with the keyword
      (`build_entry(entry, index=index)`) and type the parameter as a keyword
      Protocol/`Callable` (Decision D-BUILDER-KW). A unit test in
      test_loaderkit_parse.py binds a keyword-only `_build_thing(entry, *, index)`
      directly and asserts authoring order is preserved.

    - Risk: A repointed helper call site silently transposes `offending_id` with
      another positional argument (e.g. `reject_unknown_keys(mapping, allowed,
      offending_id=...)`), producing a *wrong-id* operator message that the type
      checker would not catch if `offending_id` were positional.
      Severity: high
      Likelihood: medium if unplanned
      Mitigation: Decision D-WI4-INVENTORY mandates `offending_id` is passed
      **keyword** at every multi-argument bound-method call site (`reject_unknown_keys`,
      `require`, `require_str`, `require_int`); the `BoundCoercion` methods declare
      it keyword-only (`*, offending_id`) for those, so a transposition is a
      TypeError at the gate, not a silent wrong-id message. `where(offending_id)`
      stays positional-or-keyword (single argument, no transposition hazard). The
      snapshot suites are the backstop that any surviving message drift fails the
      gate.

    - Risk: Collapsing the shims could change the *public* call sites in
      parse.py/_fields.py from `rule_id=`/`device_id=` away from the public
      keyword, a tolerance breach.
      Severity: high
      Likelihood: low (mechanism fixed)
      Mitigation: Decision D-ID-KEYWORD keeps the public `rule_id=`/`device_id=`
      keyword *inside* the `content_error` callable each `_coerce.py` supplies, so
      it never appears on the bound helpers and the error-channel constructors are
      untouched. The internal helper keyword becomes `offending_id`. A test asserts
      a `LedgerError` raised through the bound bundle still carries `device_id`.

    - Risk: The ledger `_coerce.py` exports a bare `_require` that the rule-pack
      shim does not; collapsing both onto one factory could drop `_require` and
      break `ledger/_fields.py`.
      Severity: medium
      Likelihood: medium
      Mitigation: Decision D-REQUIRE-SURFACE: the shared `BoundCoercion` bundle
      exposes the *full* helper set (`where`, `reject_unknown_keys`, `require`,
      `require_str`, `require_int`) for *every* family; the rule pack simply does
      not call `require`. One uniform surface removes the divergence rather than
      preserving it. `ledger/_fields.py` is repointed at the bundle.

    - Risk: Collapsing the `_coerce.py` shim modules could orphan the `_ERRORS`,
      `_Mapping`, `_where`, `_reject_unknown_keys`, `_require*` names that
      parse.py/_fields.py import, breaking imports with an ImportError/NameError.
      Severity: medium
      Likelihood: medium
      Mitigation: Decision D-ERRORS-ALIAS keeps `_ERRORS = _COERCION.errors` and
      `type _Mapping = Mapping` on each shim, so the three `errors=_ERRORS`
      primitive call sites per family (`resolve_schema_version`, `build_entries`,
      `compile_pattern`) and every `_Mapping` annotation stay byte-identical. Only
      the helper forwarders (`_where`/`_reject_unknown_keys`/`_require*`) are
      removed, and Decision D-WI4-INVENTORY enumerates **every** helper call site
      that must be repointed to `_COERCION.*` in the same commit. leta `refs` each
      removed name first (Concrete steps) and the typecheck/lint gate catches any
      straggler.

    - Risk: A future maintainer re-introduces an identity lambda or a per-family
      forwarder, silently re-forking the seam.
      Severity: low
      Likelihood: medium
      Mitigation: the new loaderkit third-family test binds the keyword-only
      builder and the `bind_coercion` factory directly; a re-introduced lambda is
      not *tested* but the direct-bind test documents the supported idiom, and the
      grep checks in Validation are part of acceptance.

## Progress

    - [x] Work item 1: Drop the `scan_pattern` identity-lambda seam (bind
      `LineHit` directly). Done 2026-06-27: `scan_pattern` now calls
      `line_hit(chapter=…, line=…)` and is typed `Callable[..., LineHit]`; both
      `detect.py` sites pass `line_hit=LineHit`. The scan suite's recording double
      is keyword-only (`*, chapter, line`), pinning the keyword-call convention;
      the existing properties stay green. `make all` green (1564 passed). No
      message drift. CodeRabbit on this slice raised only execplan-prose findings:
      the `> 8 source files` scope cap is corrected to `> 10` to match the
      enumerated footprint; the two logisphere-review-*.md first-person verdict
      notes are review artefacts of a prior step, left as-is (out of this task's
      implementation scope).
    - [x] Work item 2: Drop the `build_entries` identity-lambda seam (bind
      `_rule`/`_device` directly). Done 2026-06-27: added the keyword-builder
      `EntryBuilder[T]` Protocol (`__call__(self, entry, *, index)`), retyped
      `build_entries`' `build_entry` parameter to it, and call it
      `build_entry(entry, index=index)`. Both `parse.py` sites now pass
      `build_entry=_rule`/`build_entry=_device` directly. The parse suite's
      `_build_thing` and recording double are keyword-only (`*, index`), pinning
      the convention; the order-preserving and duplicate-id tests stay green.
      `make all` green (1564 passed); no snapshot drift. CodeRabbit: 0 findings.
    - [x] Work item 3: Add the shared `bind_coercion` factory and `BoundCoercion`
      bundle to `loaderkit/coerce.py`, pinned by a third-family test. Done
      2026-06-27: added the frozen `BoundCoercion` dataclass (one `errors`
      attribute plus `where`/`reject_unknown_keys`/`require`/`require_str`/
      `require_int` methods, `offending_id` keyword-only on the multi-argument
      ones) and the `bind_coercion(*, content_error, per_id_noun, per_level_noun)`
      factory, both exported through `loaderkit/__init__.py`. A new third-family
      test (`_ThingError`/`_bind_thing`, no real pack import) pins the `where`
      levels, the `require_int` bool rejection, the sorted unknown-key listing, the
      family-id survival through the bind, and the raw `.errors` handle. Measured
      `wc -l coerce.py` = 362 (< 400, D-WI3-BUDGET satisfied; the `bound.py` split
      contingency is not needed). `make all` green (1569 passed). CodeRabbit: 0
      findings.
    - [x] Work item 4: Collapse the two per-family `_coerce.py` shims onto
      `bind_coercion` (keeping the `_ERRORS = _COERCION.errors` and `_Mapping`
      aliases) and repoint the 21 helper call sites across `rulepack/parse.py` (10),
      `ledger/parse.py` (2), and `ledger/_fields.py` (9) per the D-WI4-INVENTORY
      enumeration. Done 2026-06-27: both shims now reduce to one `bind_coercion`
      call plus the `_ERRORS`/`_Mapping` aliases (no forwarder bodies). All 21
      helper sites call `_COERCION.<method>(...)` with `offending_id` kept keyword
      at the 10 multi-argument sites; the 6 `errors=_ERRORS` raw-bundle sites are
      untouched. Added `tests/test_coerce_binding_wiring.py` pinning a bad-`basis`
      rule (`rule_id="alpha"`) and a bad-`allowed_chapters`-element device
      (`device_id="sternum"`) — the latter is the only negative pin over the
      `_fields.py` `_COERCION.require`/`where` sites. `make all` green (1571
      passed); no snapshot drift. CodeRabbit: 1 minor (prefer `match=` over
      `messages[0]` indexing) — applied, keeping the id assertions separate.

## Surprises & discoveries

    - Observation: This task has **no** cuprum, subprocess, catalogue, or
      external-process surface.
      Evidence: `grep -rln "cuprum\|catalogue\|subprocess\|sh\.run"
      novel_ralph_skill/loaderkit novel_ralph_skill/rulepack
      novel_ralph_skill/ledger` returns nothing. The whole task is an internal,
      pure-Python seam refactor over `loaderkit`, `rulepack`, and `ledger`.
      Impact: cuprum-version verification and locked-external-library
      (Cyclopts/pytest-timeout/uv) research are **not load-bearing** here; no work
      item depends on any cuprum API or third-party runtime behaviour, so none is
      pinned to one. The only external surfaces touched are stdlib `functools`
      (optional, for `partial`) and the existing `re`/`tomllib` already in use,
      both unchanged by this task.

    - Observation: The two `_coerce.py` shim surfaces have already diverged.
      Evidence: `ledger/_coerce.py` exports `_require`; `rulepack/_coerce.py` does
      not. `ledger/_fields.py` consumes `_require`, `_require_int`, `_where`.
      Impact: the collapse must offer one *uniform* helper surface (Decision
      D-REQUIRE-SURFACE), not paper over the asymmetry.

## Decision log

    - Decision: D-BUILDER-KW — make `build_entries` call its builder with a
      keyword `index` and type the parameter as a keyword-accepting callable, so a
      keyword-only `_rule(entry, *, index)`/`_device(entry, *, index)` binds
      directly with no lambda.
      Rationale: the roadmap names this "a positional/keyword convention fix on the
      builder seam". `_rule`/`_device` are already `*, index`; aligning the
      skeleton's call convention to keyword lets the existing builders bind without
      a wrapper and without changing the builders. Defining a small keyword
      `Protocol` (e.g. `EntryBuilder`) makes the keyword contract explicit to the
      type checker.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-LINEHIT-KW — make `scan_pattern` call `line_hit` with keywords
      (`line_hit(chapter=..., line=...)`) and type the parameter to accept them, so
      the `kw_only` `LineHit` dataclass binds directly as `line_hit=LineHit`.
      Rationale: `LineHit` is `frozen, kw_only, slots`; passing the class itself as
      the callback removes the byte-identical lambda at both detect call sites
      while keeping the constructor seam that holds the scan body free of
      Rule/Device knowledge.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-ID-KEYWORD — collapse the shims via a `bind_coercion(...)`
      factory returning a frozen `BoundCoercion` bundle whose helper methods take
      `offending_id` (positional-or-keyword), with the family's *public* error
      keyword (`rule_id=`/`device_id=`) bound *inside* the `content_error` callable
      passed to `bind_coercion`, exactly where it is bound today.
      Rationale: a `functools.partial` *bundle* over the free functions works too —
      `offending_id` is not being renamed (only `rule_id`/`device_id` is, and that
      lives inside `content_error`), so partial does not need to rename anything.
      The bound dataclass is preferred over a partial bundle for two concrete
      reasons, not because partial is infeasible: it gives one typed `.errors`
      handle the raw-`CoercionErrors` consumers (`resolve_schema_version`,
      `build_entries`, `compile_pattern`) bind to directly (Decision D-ERRORS-ALIAS),
      and it gives each helper an explicit, checker-visible method signature.
      Internal call sites in `parse.py`/`_fields.py` move from `rule_id=`/`device_id=`
      to `offending_id=` (kept keyword — see D-WI4-INVENTORY), which is a private
      rename; the public error contract is untouched.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-REQUIRE-SURFACE — the shared `BoundCoercion` bundle exposes the
      *full* helper set (`where`, `reject_unknown_keys`, `require`, `require_str`,
      `require_int`) uniformly for every family. The rule pack does not call
      `require`; it simply does not use that attribute.
      Rationale: removes the rule-pack/ledger divergence rather than preserving it,
      so a third family inherits one complete surface.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-NO-EXTERNAL-RESEARCH — no cuprum/Cyclopts/pytest-timeout/uv
      behaviour is pinned because no work item depends on any of them (see
      Surprises). The only mechanism choices are stdlib (`functools.partial`
      optional; a hand-written bound bundle is the primary mechanism).
      Rationale: avoids inventing an unverified external dependency where the task
      is a pure internal-seam refactor.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-ERRORS-ALIAS — each collapsed `_coerce.py` keeps a single
      `_ERRORS = _COERCION.errors` alias (and the `type _Mapping = Mapping`
      re-export) alongside the one `bind_coercion(...)` binding, rather than
      deleting `_ERRORS` and repointing every `errors=_ERRORS` site individually.
      Rationale: `_ERRORS` is consumed by three primitives in each `parse.py`
      (`resolve_schema_version`, `build_entries`, `compile_pattern`), all of which
      take a *raw* `CoercionErrors` (`BoundCoercion` exposes it as `.errors`).
      Aliasing leaves those three call sites byte-identical and confines the WI4
      churn to the *helper* call sites (`_where`/`_require*`/`_reject_unknown_keys`),
      which is both smaller and lower-risk than touching the schema-version /
      entry-array / pattern-compile wiring. `_Mapping` is likewise re-exported so
      `parse.py`/`_fields.py` imports of `_Mapping` are untouched. These two
      survivors are the *only* names that remain on each shim besides `_COERCION`;
      the per-family forwarder *bodies* (`_where`, `_reject_unknown_keys`,
      `_require`, `_require_str`, `_require_int`) are all removed, satisfying the
      "single `bind_coercion(...)` binding with no per-family forwarder bodies"
      success criterion.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-WI4-INVENTORY — Work item 4 carries the full, source-verified
      per-file call-site inventory rather than examples-plus-"etc.". The helper
      call sites that change from a private `_helper(...)` name to a
      `_COERCION.method(...)` attribute access, with `offending_id` kept
      **keyword** at every multi-argument site (advisory from round 1), are:
      `rulepack/parse.py` — `_where` ×4 (lines 113, 150, 157, 199), `_require_int`
      ×2 (148, 197), `_require_str` ×3 (196, 202, 273), `_reject_unknown_keys` ×1
      (195) = 10 helper sites; `ledger/parse.py` — `_reject_unknown_keys` ×1 (117),
      `_require_str` ×1 (118) = 2 helper sites; `ledger/_fields.py` — `_require_int`
      ×1 (61), `_where` ×7 (63, 97, 102, 108, 114, 172, 180), `_require` ×1 (94) =
      9 helper sites. The `errors=_ERRORS` sites (`rulepack/parse.py` 209/269/278,
      `ledger/parse.py` 126/187/193) are **not** repointed — they keep `_ERRORS`
      via the D-ERRORS-ALIAS alias. Each helper repoint is an in-place edit of an
      existing line (rename `_where(` → `_COERCION.where(`, `_require_int(...,
      rule_id=...)` → `_COERCION.require_int(..., offending_id=...)`, etc.), so the
      net line delta on the three consumer files is ≈0; the only material net-line
      change is the shrinkage of the two `_coerce.py` shims (each from ~60–70 lines
      to ~30) and the WI3 additions. Total source churn fits the 8-file / ~250-net-
      line Tolerance with margin.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D-WI3-BUDGET — `loaderkit/coerce.py` is 253 lines today. The
      `BoundCoercion` frozen dataclass (one `errors` attribute plus five bound
      methods, each with an interrogate-mandated 100% docstring) and the
      `bind_coercion` factory (with its own docstring) are budgeted at ≈110–140
      added lines, landing `coerce.py` at ≈365–390 lines — under the 400-line cap
      but with thin margin. WI3 validation therefore asserts the *measured*
      `wc -l novel_ralph_skill/loaderkit/coerce.py` is `< 400` after the factory
      lands; if the measured count exceeds 400, stop and escalate (the contingency
      is to split the bundle into a sibling `loaderkit/bound.py`, which keeps the
      no-import-cycle layering).
      Rationale: round-1 review flagged that the docstring cost of five methods plus
      a factory was not budgeted against the cap; this pins a measured gate and a
      named contingency rather than an unchecked assertion.
      Date/Author: 2026-06-27, planning agent.

## Outcomes & retrospective

Completed 2026-06-27. All four work items landed in order, each gated green and
committed atomically. The four observable success criteria from Purpose all hold:

1. `grep` for `lambda` over the four parse/detect modules finds no surviving
   `build_entry=`/`line_hit=` identity lambda (WI1, WI2 acceptance greps clean).
2. Both `_coerce.py` shims reduce to one `bind_coercion(...)` binding plus the
   `_ERRORS = _COERCION.errors` / `type _Mapping = Mapping` aliases, with no
   per-family forwarder body (WI4 acceptance grep: zero `^def _(where|…)`).
3. The new third-family pins in `tests/test_loaderkit_coerce.py`
   (`bind_coercion`) and the keyword-only recording doubles in
   `tests/test_loaderkit_scan.py` / `tests/test_loaderkit_parse.py` exercise the
   shared seams with no import of any real pack type; the new
   `tests/test_coerce_binding_wiring.py` pins per-family id survival.
4. `make all` is green at HEAD (1571 passed, 1 skipped). The rule-pack, ledger,
   and `loaderkit` snapshot/property suites passed with **no** `--snapshot-update`,
   confirming zero message or id drift.

No decision was reversed. The four planning decisions (D-BUILDER-KW,
D-LINEHIT-KW, D-ID-KEYWORD, D-REQUIRE-SURFACE) and the supporting
D-ERRORS-ALIAS / D-WI4-INVENTORY / D-WI3-BUDGET held as written.

Deviation D-FSTRING-WRAP (2026-06-27, implementer): repointing `_where(rule_id)`
to the longer `_COERCION.where(rule_id)` pushed three single-line `msg = f"…"`
assignments in `rulepack/parse.py` (the unknown-basis, `page_words`-positive, and
`threshold`-non-negative sentences) past the 88-column ruff limit. Each was
wrapped into a parenthesized implicit-concatenation f-string that produces a
**byte-identical** runtime string; the rule-pack snapshot/loader suites confirm
no message drift. `ruff format` does not break string literals, so this manual wrap
was required and is the only net deviation from the planned in-place renames.

Budget outcome: `loaderkit/coerce.py` measured 362 lines after WI3 (cap 400; the
`loaderkit/bound.py` split contingency was not needed). Footprint: 10 source files
plus their tests, within the (corrected) 10-file Tolerance.

## Context and orientation

The relevant modules (all paths repository-relative, inside the worktree):

- `novel_ralph_skill/loaderkit/scan.py` — `scan_pattern(pattern, chapters, *,
  line_hit)` plus the `ScannedChapter`/`LineHit` frozen dataclasses. `LineHit` is
  `frozen, kw_only, slots` with fields `chapter: int`, `line: int`.
- `novel_ralph_skill/loaderkit/parse.py` — the head/tail skeleton.
  `build_entries[T](raw, *, array_key, entries_messages, errors, build_entry,
  entry_id=_entry_id)` types `build_entry` as `Callable[[Mapping, int], T]` and
  calls it positionally: `build_entry(entry, index)`.
- `novel_ralph_skill/loaderkit/coerce.py` — `CoercionErrors` (frozen bundle:
  `content_error`, `per_id_noun`, `per_level_noun`), `where`, `reject_unknown_keys`,
  `require`, `require_str`, `require_int`. Each helper takes `*, errors:
  CoercionErrors, offending_id: str | None`. This is where `bind_coercion` lands.
- `novel_ralph_skill/loaderkit/__init__.py` — the public `loaderkit` re-export
  surface; `__all__` lists every primitive. `bind_coercion`/`BoundCoercion` must
  be added here.
- `novel_ralph_skill/rulepack/_coerce.py` — the rule-pack binding: builds
  `_ERRORS = CoercionErrors(content_error=lambda msg, rule_id:
  RulePackError(msg, rule_id=rule_id), per_id_noun="rule", per_level_noun="rule
  pack")` and exports `_Mapping`, `_where`, `_reject_unknown_keys`, `_require_str`,
  `_require_int`. Imported by `rulepack/parse.py`.
- `novel_ralph_skill/ledger/_coerce.py` — the ledger binding: same shape with the
  `device_id`/`device`/`device ledger` nouns, **plus** a bare `_require`. Imported
  by `ledger/parse.py` and `ledger/_fields.py`.
- `novel_ralph_skill/rulepack/parse.py` — `parse_rulepack` passes
  `build_entry=lambda entry, index: _rule(entry, index=index)` (line ~279) and
  imports `_ERRORS, _Mapping, _reject_unknown_keys, _require_int, _require_str,
  _where` from `rulepack._coerce`.
- `novel_ralph_skill/ledger/parse.py` — `parse_ledger` passes
  `build_entry=lambda entry, index: _device(entry, index=index)` (line ~194) and
  imports `_ERRORS, _Mapping, _reject_unknown_keys, _require_str` from
  `ledger._coerce`.
- `novel_ralph_skill/ledger/_fields.py` — imports `_Mapping, _require,
  _require_int, _where` from `ledger._coerce`.
- `novel_ralph_skill/rulepack/detect.py` (line ~207) and
  `novel_ralph_skill/ledger/detect.py` (line ~245) — each pass `line_hit=lambda
  chapter, line: LineHit(chapter=chapter, line=line)`.

Existing tests that bound the seams:

- `tests/test_loaderkit_scan.py` — pins `scan_pattern` with a module-local
  `_line_hit(chapter, line)` helper.
- `tests/test_loaderkit_parse.py` — pins the head/tail skeleton against a
  test-local third family (`_Thing`, `_build_thing`), the model the new bind test
  follows.
- `tests/test_loaderkit_coerce.py` — pins the coercion helpers and the two noun
  pairs.
- `tests/test_rulepack_loader.py`, `tests/test_ledger_snapshots.py`,
  `tests/test_rulepack_properties.py`, `tests/test_ledger_properties.py` — the
  end-to-end message/behaviour pins that catch drift.

Design source-of-truth this task implements:

- `docs/novel-ralph-harness-design.md` §6.1 (rule-pack schema), §6.2 (AI-isms as
  versioned data), §6.3 (device ledger) — the two parallel detection-pack
  families whose loader-and-scan primitives must each have a single home.
- `docs/adr-003-shared-interface-contract.md` — the shared-interface/single-home
  discipline and the no-import-cycle layering the `loaderkit` primitives obey.
- `docs/adr-001-deterministic-judgemental-boundary.md` — the read-only,
  detect-only loader boundary (no message change is a behaviour change).
- `docs/developers-guide.md` — internal conventions for the loaderkit binding
  seam.
- `docs/scripting-standards.md` and `AGENTS.md` — quality gates, 400-line cap,
  testing rules, en-GB spelling.

## Plan of work

Four ordered, independently committable and gate-passable work items. Items 1 and
2 are the lambda seams (independent of each other and of items 3–4); item 3 adds
the shared factory; item 4 consumes it. Each ends with `make all` green.

### Work item 1 — Bind `LineHit` directly into `scan_pattern`

**Goal.** Remove the `line_hit=lambda chapter, line: LineHit(...)` wrapper at both
detect call sites by aligning `scan_pattern`'s callback convention to keywords so
the `kw_only` `LineHit` class binds directly.

**Docs to read.** design §6.1; ADR-001 (scan is detect-only). **Skills to load.**
`python-router` → `python-types-and-apis` (callback/Protocol typing, `kw_only`
callable signatures), `python-testing`; `leta` (navigate refs); `hypothesis`
(the scan suite already carries a property; keep it green). Use `sem` to read the
7.2.2/7.2.3 history of `scan.py` if the callback rationale is unclear.

**Edits.**

1. `novel_ralph_skill/loaderkit/scan.py`: change `scan_pattern` to call
   `line_hit(chapter=chapter.number, line=index)` and retype the `line_hit`
   parameter to a keyword-accepting callable that `LineHit` itself satisfies
   (e.g. `Callable[..., LineHit]` documented `line_hit(*, chapter, line)`, or a
   small `LineHitFactory` Protocol with a `__call__(self, *, chapter: int, line:
   int) -> LineHit`). Update the docstring's `line_hit` paragraph: the caller now
   passes the `LineHit` *class* (or any `kw_only` constructor), not a lambda.
2. `novel_ralph_skill/rulepack/detect.py` and `novel_ralph_skill/ledger/detect.py`:
   replace `line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line)`
   with `line_hit=LineHit`.

**Tests (add/update).**

- `tests/test_loaderkit_scan.py`: change the module-local `_line_hit(chapter,
  line)` helper to bind `LineHit` directly (`scan_pattern(..., line_hit=LineHit)`)
  in at least one test, and add a test asserting `scan_pattern` invokes the
  callback with keyword arguments (a recording callback `def _record(*, chapter,
  line)` that fails if called positionally). The existing Hypothesis property
  (`test_line_attribution_matches_independent_newline_model`) stays green.
- `tests/test_rulepack_detect.py` and `tests/test_ledger_detect.py`: no message
  change, so existing assertions stand; run them to confirm the direct bind
  produces identical `LineHit` tuples.

**Validation.** `make all`. Acceptance: `grep -n "lambda"
novel_ralph_skill/rulepack/detect.py novel_ralph_skill/ledger/detect.py` shows no
`line_hit=` lambda; scan and both detect suites pass.

### Work item 2 — Bind `_rule`/`_device` directly into `build_entries`

**Goal.** Remove the `build_entry=lambda entry, index: _rule(entry,
index=index)` wrapper at both parse call sites by aligning `build_entries`'
builder-call convention to a keyword `index` so the keyword-only `_rule`/`_device`
builders bind directly.

**Docs to read.** design §6.1, §6.3; ADR-003 (single-home discipline);
`docs/execplans/roadmap-7-2-6.md` Decision D-SKELETON-HEAD-TAIL (do not disturb
the head/tail seam). **Skills to load.** `python-router` →
`python-types-and-apis` (keyword `Protocol`/`Callable`), `python-abstractions`
(callback seams), `python-testing`; `leta`.

**Edits.**

1. `novel_ralph_skill/loaderkit/parse.py`: define a small keyword-builder Protocol
   (e.g. `class EntryBuilder(Protocol[T]): def __call__(self, entry: Mapping, *,
   index: int) -> T`) or retype `build_entry` to a keyword-`index` callable;
   change the call from `build_entry(entry, index)` to `build_entry(entry,
   index=index)`. Keep `entry_id`/`_entry_id` and the authoring-order/duplicate-id
   pass exactly as-is. Update the `build_entry` docstring paragraph: the builder
   is called `build_entry(entry, index=index)` and the caller passes its keyword-only
   `_rule`/`_device` directly.
2. `novel_ralph_skill/rulepack/parse.py`: replace `build_entry=lambda entry,
   index: _rule(entry, index=index)` with `build_entry=_rule`.
3. `novel_ralph_skill/ledger/parse.py`: replace the analogous lambda with
   `build_entry=_device`.

**Tests (add/update).**

- `tests/test_loaderkit_parse.py`: make `_build_thing` keyword-only
  (`def _build_thing(entry, *, index)`) and bind it directly
  (`build_entry=_build_thing`) in the order-preserving and duplicate-id tests; add
  a test asserting `build_entries` calls the builder with a keyword `index` (a
  recording builder `def _record(entry, *, index)` that captures the keyword and
  a positional-rejecting signature). The existing
  `test_tail_calls_build_entry_per_entry_in_authoring_order` and
  `test_tail_projects_ids_via_supplied_entry_id` stay green.
- `tests/test_rulepack_loader.py` and the ledger parse pins (from 7.2.6's
  `test_ledger_loader.py` if present, else `tests/test_ledger_snapshots.py`): no
  message change; run to confirm identical built tuples and unchanged fault
  precedence (`pack`-before-`entries`).

**Validation.** `make all`. Acceptance: `grep -n "lambda"
novel_ralph_skill/rulepack/parse.py novel_ralph_skill/ledger/parse.py` shows no
`build_entry=` lambda; parse skeleton and both loader suites pass; no snapshot
drift.

### Work item 3 — Add the shared `bind_coercion` factory and `BoundCoercion` bundle

**Goal.** Provide one pack-agnostic factory in `loaderkit/coerce.py` that returns
a frozen bundle exposing every coercion helper with its `errors` already bound,
so a family supplies one binding rather than a forwarder module. This item adds
the factory and its test; item 4 consumes it.

**Docs to read.** design §6.1, §6.2, §6.3; ADR-003 (shared interface, no import
cycle). **Skills to load.** `python-router` → `python-data-shapes` (frozen bundle
vs `functools.partial`; choose the bound-bundle shape per Decision D-ID-KEYWORD),
`python-types-and-apis` (callable attributes, `ParamSpec` if needed),
`python-testing`; `python-verification` then `hypothesis` only if a property is
warranted on the binding (see Tests). `leta`.

**Edits.**

1. `novel_ralph_skill/loaderkit/coerce.py`: add a frozen
   `BoundCoercion` dataclass exposing the bound helper surface — at minimum
   `where(offending_id)`, `reject_unknown_keys(mapping, allowed, *, offending_id)`,
   `require(mapping, key, *, offending_id)`, `require_str(mapping, key, *,
   offending_id)`, `require_int(mapping, key, *, offending_id)`, and the underlying
   `CoercionErrors` as a public `errors` attribute. The `.errors` attribute is
   load-bearing: WI4 binds it via `_ERRORS = _COERCION.errors` (Decision
   D-ERRORS-ALIAS) so the three raw-`CoercionErrors` consumers per family
   (`resolve_schema_version`, `build_entries`, `compile_pattern(..., errors=...,
   offending_id=...)`) keep their call sites unchanged. Add `def bind_coercion(*,
   content_error, per_id_noun, per_level_noun) -> BoundCoercion` that builds the
   `CoercionErrors` and returns the bundle with each helper bound via the existing
   free functions (a thin method delegating to the module-level `where`/`require*`/
   `reject_unknown_keys`). `offending_id` is **keyword-only** (`*, offending_id`)
   on the multi-argument methods (`reject_unknown_keys`, `require`, `require_str`,
   `require_int`) so a positional transposition at a WI4 call site is a TypeError,
   not a silent wrong-id message (round-1 advisory); `where(offending_id)` keeps
   a single positional-or-keyword parameter (no transposition hazard). The *public*
   error keyword (`rule_id=`/`device_id=`) is bound inside the `content_error`
   callable the family supplies, so it never appears on the bundle (Decision
   D-ID-KEYWORD). Keep `loaderkit/coerce.py` under 400 lines (Decision
   D-WI3-BUDGET).
2. `novel_ralph_skill/loaderkit/__init__.py`: add `bind_coercion` and
   `BoundCoercion` to the imports and `__all__` (alphabetical order as the file
   keeps).

**Tests (add).**

- `tests/test_loaderkit_coerce.py`: add a third-family binding test with **no**
  real pack import — bind `bind_coercion(content_error=lambda msg, oid:
  _ThingError(msg, thing_id=oid), per_id_noun="thing", per_level_noun="thing
  set")` and assert: (a) `bundle.where(None)` returns the per-level noun and
  `bundle.where("x")` the per-entity prefix; (b) `bundle.require_int` rejects a
  `bool` with the unchanged sentence; (c) `bundle.reject_unknown_keys` lists
  unknown and allowed keys sorted; (d) the raised error is the family's own type
  carrying the family's id (proving the public id keyword survives the bind). This
  is the pin that a third family inherits the binding rather than cloning a shim.
- No Hypothesis property is required here unless the binding introduces a branch;
  the helpers' own properties already live in `test_loaderkit_coerce.py`. Record
  in the Decision Log if a property is added.

**Validation.** `make all`. Acceptance: the new third-family test fails before the
factory exists and passes after; `loaderkit` suite green. Then assert the
**measured** size budget (Decision D-WI3-BUDGET):

    wc -l novel_ralph_skill/loaderkit/coerce.py   # expect a count < 400

`coerce.py` is 253 lines today; the bundle (one `errors` attribute, five bound
methods, each with an interrogate-mandated docstring) plus the `bind_coercion`
factory are budgeted at ≈110–140 added lines, landing at ≈365–390. If the measured
count is `>= 400`, stop and escalate; the named contingency is to move
`BoundCoercion` + `bind_coercion` into a sibling `loaderkit/bound.py` re-exported
through `loaderkit/__init__.py` (preserving the no-import-cycle layering), not to
relax the cap.

### Work item 4 — Collapse the two `_coerce.py` shims onto `bind_coercion`

**Goal.** Replace the per-family forwarder bodies with a single `bind_coercion`
binding each, and repoint `parse.py`/`_fields.py` at the bundle, removing the
divergent `_require` surface.

**Docs to read.** design §6.1, §6.3; ADR-003. **Skills to load.** `python-router`
→ `python-data-shapes`, `python-errors-and-logging` (the typed-channel keyword
binding stays inside `content_error`); `leta` (refs every imported name before
moving it); `python-testing`. Use `sem blame`/`sem diff` on `_coerce.py` to
confirm 7.2.2's binding rationale before collapsing.

This work item touches four source files (the two `_coerce.py` shims, plus
`rulepack/parse.py`, `ledger/parse.py`, `ledger/_fields.py` — five files in all)
with a fully enumerated, source-verified call-site inventory (Decision
D-WI4-INVENTORY). At every multi-argument bound-method site, `offending_id` is
passed **keyword** (the methods declare it `*, offending_id`), so a positional
transposition fails at the gate rather than emitting a wrong-id message.

**Edits.**

1. `novel_ralph_skill/rulepack/_coerce.py` — collapse to one binding plus two
   survivors (Decision D-ERRORS-ALIAS). Replace the whole forwarder body with:

       _COERCION = bind_coercion(
           content_error=lambda msg, rule_id: RulePackError(msg, rule_id=rule_id),
           per_id_noun="rule",
           per_level_noun="rule pack",
       )
       _ERRORS = _COERCION.errors
       type _Mapping = Mapping

   Remove the `_where`, `_reject_unknown_keys`, `_require_str`, `_require_int`
   forwarder *bodies*. The public error keyword `rule_id=` stays inside
   `content_error`. Update imports: drop `reject_unknown_keys, require_int,
   require_str, where` from the `loaderkit.coerce` import (keep `Mapping`,
   `CoercionErrors` is no longer needed since `bind_coercion` builds it — import
   `bind_coercion` instead).

2. `novel_ralph_skill/ledger/_coerce.py` — the same collapse with the `device`
   nouns:

       _COERCION = bind_coercion(
           content_error=lambda msg, device_id: LedgerError(msg, device_id=device_id),
           per_id_noun="device",
           per_level_noun="device ledger",
       )
       _ERRORS = _COERCION.errors
       type _Mapping = Mapping

   Remove the `_where`, `_reject_unknown_keys`, `_require`, `_require_str`,
   `_require_int` forwarder bodies. The bare `_require` divergence disappears
   because the bundle carries `require` uniformly (Decision D-REQUIRE-SURFACE).
   `_ERRORS` and `_Mapping` survive as aliases consumed by `parse.py` and
   `_fields.py`.

3. `novel_ralph_skill/rulepack/parse.py` — repoint the import and the **10 helper
   call sites**; leave the three `errors=_ERRORS` sites untouched (they bind the
   aliased `_ERRORS`). The import block changes from `_ERRORS, _Mapping,
   _reject_unknown_keys, _require_int, _require_str, _where` to `_COERCION, _ERRORS,
   _Mapping` (alphabetical). Then rewrite, in place:

   - line 113 `_where(rule_id)` → `_COERCION.where(rule_id)` (inside `_resolve_basis`).
   - line 148 `_require_int(entry, "page_words", rule_id=rule_id)` →
     `_COERCION.require_int(entry, "page_words", offending_id=rule_id)`.
   - line 150 `_where(rule_id)` → `_COERCION.where(rule_id)`.
   - line 157 `_where(rule_id)` → `_COERCION.where(rule_id)`
     (both inside `_resolve_page_words`).
   - line 195 `_reject_unknown_keys(entry, _RULE_KEYS, rule_id=rule_id)` →
     `_COERCION.reject_unknown_keys(entry, _RULE_KEYS, offending_id=rule_id)`.
   - line 196 `_require_str(entry, "pattern", rule_id=rule_id)` →
     `_COERCION.require_str(entry, "pattern", offending_id=rule_id)`.
   - line 197 `_require_int(entry, "threshold", rule_id=rule_id)` →
     `_COERCION.require_int(entry, "threshold", offending_id=rule_id)`.
   - line 199 `_where(rule_id)` → `_COERCION.where(rule_id)`.
   - line 202 `_require_str(entry, "basis", rule_id=rule_id)` →
     `_COERCION.require_str(entry, "basis", offending_id=rule_id)`
     (all inside `_rule`).
   - line 273 `_require_str(raw, "pack", rule_id=None)` →
     `_COERCION.require_str(raw, "pack", offending_id=None)` (inside `parse_rulepack`).

   Lines 209 (`compile_pattern(..., errors=_ERRORS, offending_id=rule_id)`), 269
   and 278 (`errors=_ERRORS`) are **unchanged** — they consume the raw
   `CoercionErrors` via the `_ERRORS` alias. The public `RulePackError(...,
   rule_id=...)` raises in this module stay byte-identical.

4. `novel_ralph_skill/ledger/parse.py` — repoint the import and the **2 helper
   call sites**; leave the three `errors=_ERRORS` sites untouched. The import block
   changes from `_ERRORS, _Mapping, _reject_unknown_keys, _require_str` to
   `_COERCION, _ERRORS, _Mapping`. Then:

   - line 117 `_reject_unknown_keys(entry, _DEVICE_KEYS, device_id=device_id)` →
     `_COERCION.reject_unknown_keys(entry, _DEVICE_KEYS, offending_id=device_id)`.
   - line 118 `_require_str(entry, "pattern", device_id=device_id)` →
     `_COERCION.require_str(entry, "pattern", offending_id=device_id)`.

   Lines 126 (`compile_pattern(..., errors=_ERRORS, ...)`), 187 and 193
   (`errors=_ERRORS`) are **unchanged**.

5. `novel_ralph_skill/ledger/_fields.py` — repoint the import and the **9 helper
   call sites**. The import block changes from `_Mapping, _require, _require_int,
   _where` to `_COERCION, _Mapping`. Then:

   - line 61 `_require_int(entry, key, device_id=device_id)` →
     `_COERCION.require_int(entry, key, offending_id=device_id)` (in `_positive_int`).
   - line 63 `_where(device_id)` → `_COERCION.where(device_id)`.
   - line 94 `_require(entry, "allowed_chapters", device_id=device_id)` →
     `_COERCION.require(entry, "allowed_chapters", offending_id=device_id)`.
   - lines 97, 102, 108, 114 `_where(device_id)` → `_COERCION.where(device_id)`
     (all in `_allowed_chapters`).
   - lines 172, 180 `_where(device_id)` → `_COERCION.where(device_id)`
     (in `_rationing_fields`).

   `_fields.py` keeps its `_Mapping` import (re-sourced from the surviving
   `ledger/_coerce.py` alias — Decision D-ERRORS-ALIAS). It imports no `_ERRORS`,
   so no alias is needed there.

**Tests (add/update).**

- `tests/test_rulepack_loader.py`, `tests/test_ledger_snapshots.py`,
  `tests/test_rulepack_properties.py`, `tests/test_ledger_properties.py`, plus the
  ledger loader test if present: these are the message/behaviour pins; they must
  pass **without** snapshot update, proving every operator message and the
  `rule_id`/`device_id` id are unchanged after the collapse.
- `tests/test_loaderkit_coerce.py`: the work-item-3 third-family test already pins
  the shared binding; no new test needed unless a per-family wiring assertion is
  warranted.
- Per-family wiring pins (add to `tests/test_rulepack_loader.py` and the ledger
  loader/snapshot suite if not already covered): assert `parse_rulepack` of a
  pack whose first rule has a bad `basis`/`pattern` still raises `RulePackError`
  with a populated `rule_id`, and `parse_ledger` of a ledger whose device has an
  invalid `allowed_chapters` element still raises `LedgerError` with a populated
  `device_id`. These directly exercise the repointed `_COERCION.where` /
  `_COERCION.require` / `_COERCION.require_int` sites in `_fields.py` and
  `parse.py` and prove the public id keyword survives the bind — the round-1
  transposition hazard (`offending_id` passed positionally) would surface here as
  a wrong-id or a TypeError before the snapshot pin even runs.

**Validation.** `make all`. Acceptance: both `_coerce.py` files contain a single
`bind_coercion(...)` binding (plus the `_ERRORS = _COERCION.errors` and
`type _Mapping = Mapping` aliases — Decision D-ERRORS-ALIAS) with **no per-family
forwarder bodies**; rule-pack, ledger, and loaderkit suites green; no snapshot
drift. Grep acceptance:

    # no surviving forwarder def in either shim (the def bodies are gone):
    grep -rnE "^def _(where|reject_unknown_keys|require)" \
      novel_ralph_skill/rulepack/_coerce.py \
      novel_ralph_skill/ledger/_coerce.py   # expect: no matches

    # the consumers now call the bundle, not bare helpers:
    grep -rnE "_COERCION\.(where|require|require_int|require_str|reject_unknown_keys)" \
      novel_ralph_skill/rulepack/parse.py \
      novel_ralph_skill/ledger/parse.py \
      novel_ralph_skill/ledger/_fields.py   # expect: 21 helper sites (10 + 2 + 9)

    # offending_id is keyword at every multi-arg site (no positional id leak):
    grep -rnE "(require|require_int|require_str|reject_unknown_keys)\([^)]*offending_id=" \
      novel_ralph_skill/rulepack/parse.py \
      novel_ralph_skill/ledger/parse.py \
      novel_ralph_skill/ledger/_fields.py   # expect: every multi-arg site listed

Run `leta refs _where`, `leta refs _require`, `leta refs _require_int`,
`leta refs _require_str`, `leta refs _reject_unknown_keys` after the edits and
confirm each returns **no** remaining importer outside the (now-deleted) shim
bodies — any straggler is a missed repoint.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-7`.

1. Confirm branch and clean tree:

       git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-7 \
         branch --show-current   # expect: roadmap-7-2-7

2. Before each item, enumerate the seam's references with leta rather than ad-hoc
   grep, e.g. `leta refs build_entries`, `leta refs scan_pattern`, `leta refs
   _require`, `leta refs _where`, so every importer is repointed in the same
   commit.

3. Implement work item, then gate. Format only the files you touched, then run the
   full gate:

       # for any markdown you change (the execplan itself):
       mdtablefix docs/execplans/roadmap-7-2-7.md
       markdownlint-cli2 --fix docs/execplans/roadmap-7-2-7.md
       make markdownlint
       make nixie

       # the code gate (sequential — do not parallelize; honours build cache):
       make all

   `make all` runs format-check, lint (ruff + interrogate 100% docstring + pylint),
   typecheck (`ty`), tests (`pytest -n …`, pytest-timeout 30s per test), and audit
   per AGENTS.md. Expected: all green, e.g. `N passed`.

4. Commit each work item separately with an imperative subject (≤50 chars) and a
   wrapped body explaining what and why, citing roadmap 7.2.7 and the design
   section/ADR. Gate must be green before committing.

5. After all four items, re-run `make all` once more and confirm the four
   observable success criteria from Purpose.

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests.** `make all` is green. Each work item's new/updated loaderkit test
  fails before its change and passes after (red/green). The rule-pack and ledger
  snapshot and property suites pass with **no** snapshot update, proving message
  and id stability.
- **Lint/typecheck.** `make lint` (ruff, interrogate 100% docstring coverage,
  pylint) and `make typecheck` (`ty`) pass. New `Protocol`/bundle code is fully
  docstringed and typed; no `noqa`/`pylint: disable` is added without a linked
  follow-up (none is expected — the lambda removal should *reduce* suppressions).
- **Markdown.** `make markdownlint` and `make nixie` pass for the execplan.
- **No drift.** `grep` acceptance checks in each work item pass (no residual
  identity lambdas; no per-family forwarder bodies; uniform coercion surface).

Quality method (how we check): run `make all` (plus `make markdownlint` and `make
nixie` for the markdown change) from the worktree after each work item; compare
against the indicative transcripts; confirm the four Purpose criteria at the end.

## Idempotence and recovery

Each work item is an isolated edit-and-gate cycle and is safely re-runnable: the
edits are deterministic source rewrites with no filesystem or network side
effects. If `make all` fails mid-item, fix forward (the tree is small) or
`git restore` the touched files and retry. Any churn parked for later must be
stashed with a named message, e.g. `df12-stash v1 task=7.2.7 kind=discard
reason="formatter churn"`. Never use a bare stash message. No destructive or
irreversible step is involved.

## Interfaces and dependencies

Prescriptive end-state signatures (inside the worktree):

In `novel_ralph_skill/loaderkit/scan.py`, `scan_pattern` calls its callback by
keyword and the parameter accepts a keyword constructor (called
`line_hit(*, chapter, line)`); callers pass `line_hit=LineHit` directly:

        def scan_pattern(
            pattern: re.Pattern[str],
            chapters: cabc.Sequence[ScannedChapter],
            *,
            line_hit: cabc.Callable[..., LineHit],
        ) -> tuple[int, tuple[LineHit, ...]]: ...

In `novel_ralph_skill/loaderkit/parse.py`, `build_entries` calls its builder by
keyword; callers pass `build_entry=_rule` / `build_entry=_device` directly:

        class EntryBuilder[T](typ.Protocol):
            def __call__(self, entry: Mapping, *, index: int) -> T: ...

        def build_entries[T: _HasId](
            raw: Mapping,
            *,
            array_key: str,
            entries_messages: EntriesMessages,
            errors: CoercionErrors,
            build_entry: EntryBuilder[T],
            entry_id: cabc.Callable[[T], str] = _entry_id,
        ) -> tuple[T, ...]: ...

In `novel_ralph_skill/loaderkit/coerce.py`, the shared binding factory
(`offending_id` positional-or-keyword on the bound helpers):

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class BoundCoercion:
            errors: CoercionErrors  # bound via _ERRORS = _COERCION.errors (WI4)

            # `where` takes a single positional-or-keyword id; the multi-argument
            # helpers take `offending_id` keyword-only so a positional id leak is a
            # TypeError, not a wrong-id message (Decision D-WI4-INVENTORY).
            def where(self, offending_id: str | None) -> str: ...
            def reject_unknown_keys(
                self, mapping, allowed, *, offending_id
            ) -> None: ...
            def require(self, mapping, key, *, offending_id) -> object: ...
            def require_str(self, mapping, key, *, offending_id) -> str: ...
            def require_int(self, mapping, key, *, offending_id) -> int: ...

        def bind_coercion(
            *,
            content_error: cabc.Callable[[str, str | None], EnvelopeMessagesError],
            per_id_noun: str,
            per_level_noun: str,
        ) -> BoundCoercion: ...

Each per-family `_coerce.py` reduces to one `bind_coercion(...)` call; the
  family's public error keyword (`rule_id=`/`device_id=`) is bound inside the
  `content_error` lambda and never appears on `BoundCoercion`.

Dependencies: standard library only (`dataclasses`, `typing`, optionally
`functools`). No external dependency is added or relied upon; in particular this
task touches no cuprum, subprocess, Cyclopts, pytest-timeout, or uv behaviour
(see Surprises & Discoveries).

## Revision note

Initial draft (2026-06-27): first planning round for roadmap 7.2.7. Decomposes
the task into four ordered, independently gate-passable work items: two
identity-lambda seam removals (scan, then parse) and the shim collapse (factory,
then consumption). Records four decisions (D-BUILDER-KW, D-LINEHIT-KW,
D-ID-KEYWORD, D-REQUIRE-SURFACE) and the no-external-research finding
(D-NO-EXTERNAL-RESEARCH). No remaining work yet — implementation has not begun.

Round 2 revision (2026-06-27): resolves the three round-1 Logisphere blocking
points, all in Work item 4's scope-completeness, by verifying every call site
against the real source (`rulepack/parse.py`, `ledger/parse.py`,
`ledger/_fields.py`, both `_coerce.py`).

- What changed: WI4 edits now carry the full, line-numbered call-site inventory
  rather than examples-plus-"etc." — `rulepack/parse.py` 10 helper sites,
  `ledger/parse.py` 2, `ledger/_fields.py` 9 (21 total), each repoint named.
  Added Decision D-ERRORS-ALIAS: each shim keeps `_ERRORS = _COERCION.errors` and
  `type _Mapping = Mapping`, so the three `errors=_ERRORS` primitive sites per
  family (`resolve_schema_version`, `build_entries`, `compile_pattern`) and every
  `_Mapping` annotation stay byte-identical — only the helper forwarders are
  removed. Added Decision D-WI4-INVENTORY (the enumerated sites, `offending_id`
  kept keyword) and Decision D-WI3-BUDGET (measured `wc -l` gate on `coerce.py`
  with a `loaderkit/bound.py` split as the named over-cap contingency).
- Why it changed: round 1 (PROCEED WITH CONDITIONS) found that an implementer
  following the prior WI4 literally would (1) break the two non-`compile_pattern`
  `errors=_ERRORS` sites per family, (2) under-specify the `_fields.py`
  `_where`/`_require_int` repoints and the `_Mapping` disposition, and (3) be
  unable to tell whether the change fit the 8-file/250-line Tolerance.
- How it affects remaining work: the WI4 mechanism is unchanged; only its edit
  list is now exhaustive and the churn (in-place keyword renames, net ≈0 on the
  three consumers; shim shrinkage; WI3 additions) is confirmed within Tolerance
  (Decision D-WI4-INVENTORY, D-WI3-BUDGET). Round-1 advisories folded in: the
  D-ID-KEYWORD rationale no longer overstates the partial case, the wrong-id
  transposition risk is mandated keyword-only at multi-arg sites, and WI4 adds
  per-family id-survival wiring pins. Implementation still has not begun.

## Addenda

- Addendum 7.2.7.1 (from audit:7.2.7 Finding 3; medium). The developers' guide
  `loaderkit` section still describes the pre-7.2.7 mechanisms: it says each
  package's `_coerce.py` "builds the bundle and re-exports the underscore-named
  wrappers" (the retired `_require*`/`_where` forwarder surface), and it justifies
  `scan_pattern`'s `line_hit` callable and the detectors' `line_hit` lambda as the
  seam that keeps the primitive "free of any `Rule`/`Device` knowledge" — both of
  which this task retired (the per-family shims collapsed to one `bind_coercion(...)`
  binding returning a frozen `BoundCoercion` bundle, and the identity lambdas were
  dropped so `build_entry`/`line_hit` bind directly). The new
  `bind_coercion`/`BoundCoercion` API is unnamed in the prose. Refresh the guide's
  `loaderkit` section so it names the `bind_coercion` factory and the
  `BoundCoercion` bundle, describes the shims as a single binding rather than a
  wrapper re-export, and drops the retired-lambda framing — reconciling the prose
  with the shipped code without changing behaviour. Lightweight addendum pass.
