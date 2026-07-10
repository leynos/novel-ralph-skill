# Logisphere design review — roadmap 7.2.7, round 2

Adversarial pre-implementation review of `docs/execplans/roadmap-7-2-7.md`
(round 2). The plan was read from disk and **every** line-numbered claim in its
WI4 inventory was re-verified against the real source under
`novel_ralph_skill/loaderkit`, `novel_ralph_skill/rulepack`,
`novel_ralph_skill/ledger`, and `tests/`, plus the round-1 review, ADR-001,
ADR-003, AGENTS.md (400-line cap, interrogate `fail-under = 100`), and the ruff
`pydocstyle` numpy convention.

## Verdict: PROCEED (satisfied)

The three round-1 blocking items were scope-completeness gaps in Work item 4's
edit list. Round 2 closes all three with a source-verified, line-numbered
inventory and three new decisions (D-ERRORS-ALIAS, D-WI4-INVENTORY,
D-WI3-BUDGET). I independently re-verified the inventory line by line; it is
exact. No design change is required and none was made. The plan is
implementable and design-conformant as written.

## Round-1 blockers — all resolved and independently verified

1. **`_ERRORS` non-helper call sites.** Resolved by D-ERRORS-ALIAS: each shim
   keeps `_ERRORS = _COERCION.errors` and `type _Mapping = Mapping`, so the
   raw-`CoercionErrors` consumers stay byte-identical. Verified against source:
   the `errors=_ERRORS` sites the plan declares *unchanged* are real and at the
   cited lines — `rulepack/parse.py` 209 (`compile_pattern`), 269, 278
   (`resolve_schema_version`, `build_entries`); `ledger/parse.py` 126, 187, 193.
   All six carry `errors=_ERRORS` exactly as the plan states.

2. **`ledger/_fields.py` repoints fully enumerated.** Verified: the 9 helper
   sites are exactly `_require_int` ×1 (line 61), `_where` ×7 (63, 97, 102, 108,
   114, 172, 180), `_require` ×1 (94). The `LedgerError(...)` constructions in
   the same file (64, 100, 103, 111, 117, 176, 184) are *not* helper calls and
   are correctly excluded from the inventory. `_fields.py` imports no `_ERRORS`,
   so the plan's "no alias needed there" is correct; it keeps `_Mapping`, which
   the surviving `ledger/_coerce.py` alias supplies.

3. **`rulepack/parse.py` full inventory.** Verified: the 10 helper sites are
   exactly `_where` ×4 (113, 150, 157, 199), `_require_int` ×2 (148, 197),
   `_require_str` ×3 (196, 202, 273), `_reject_unknown_keys` ×1 (195).
   `ledger/parse.py` has exactly 2 helper sites (117, 118). The detect lambdas
   are at `rulepack/detect.py:207` and `ledger/detect.py:245` as claimed.

A repository-wide grep for `_where|_require|_require_int|_require_str|
_reject_unknown_keys` call sites confirms the 21-site total (10 + 2 + 9) is
**complete** — there is no helper usage outside the enumerated sites, the two
`_coerce.py` definitions, the import lines, and one docstring reference in
`_fields.py:73`. The round-2 inventory is exhaustive.

## What else verifies (independently confirmed)

- **WI1 / WI2 callback-convention changes are runtime-safe with the existing
  tests.** The surviving test helpers `_line_hit(chapter, line)`,
  `recording_line_hit(chapter, line)` (`test_loaderkit_scan.py`),
  `_build_thing(entry, index)`, and `recording_build(entry, index)`
  (`test_loaderkit_parse.py`) are all positional-or-keyword, so the new keyword
  invocation (`line_hit(chapter=…, line=…)`, `build_entry(entry, index=index)`)
  binds correctly and the existing assertions stay green. The plan's "stays
  green" claims hold. The new red/green pins (a keyword-only recording double
  that rejects positional calls) fail before the convention change and pass
  after — correct red/green.
- **`LineHit` and the keyword-only `_rule`/`_device` bind directly.** `LineHit`
  is `frozen, kw_only, slots`; `_rule`/`_device` are `*, index`. After the
  convention fix, `line_hit=LineHit` / `build_entry=_rule` bind with no wrapper.
- **No import-cycle / boundary breach.** `bind_coercion`/`BoundCoercion` land in
  `loaderkit/coerce.py`, parameterized on `content_error` + the noun pair; the
  module imports `EnvelopeMessagesError` only under `TYPE_CHECKING` and names no
  pack type (ADR-003 preserved). The public `rule_id=`/`device_id=` keyword
  stays inside each family's `content_error` lambda and never reaches the bundle
  (public error contract preserved; ADR-001 message-is-behaviour respected).
- **Size budget is hedged, not asserted.** `coerce.py` is 253 lines today
  (measured). `interrogate fail-under = 100` and ruff numpy convention require a
  docstring summary on each method but **not** Parameters/Returns sections, so
  five short bound-method docstrings plus the factory realistically add ~80–130
  lines, landing under 400. D-WI3-BUDGET pins a *measured* `wc -l < 400` gate
  with a named `loaderkit/bound.py` split contingency. Adequate.
- **Transposition hazard mandated keyword.** D-WI4-INVENTORY now mandates
  `offending_id` keyword at every multi-arg site; the `BoundCoercion` methods
  declare it `*, offending_id`, so a positional id leak is a TypeError at the
  gate, not a silent wrong-id message. The round-1 advisory is folded in.

## Pre-mortem (Doggylump)

The round-1 incident path (a silent wrong-id message from a positional
transposition during the `_where`/`_require*` repoint) is now closed by the
keyword-only `offending_id` mandate plus the per-family id-survival wiring pins
WI4 adds (`parse_rulepack`/`parse_ledger` still raise with a populated
`rule_id`/`device_id`). The snapshot suites remain the backstop, run without
`--snapshot-update`. No new incident path surfaced in round 2.

## Alternatives checkpoint (Wafflecat)

The `functools.partial`-bundle alternative was correctly assessed in round 1 and
the D-ID-KEYWORD rationale was tightened in round 2 (it no longer overstates the
partial case). The bound-dataclass choice remains defensible — it gives one
typed `.errors` handle for the three raw-`CoercionErrors` consumers per family
and explicit method signatures. No stronger alternative exists; the design is on
solid ground.

## Residual advisories (non-blocking)

- **WI1 typing precision.** Retyping `line_hit` to `Callable[..., LineHit]`
  discards the `(chapter, line)` arity from the type. The plan offers a
  `LineHitFactory` Protocol (`__call__(self, *, chapter: int, line: int)`) as the
  alternative; prefer it so the keyword contract is checker-visible, mirroring
  the `EntryBuilder[T]` Protocol WI2 introduces. Either passes the gate.
- **Margin watch on WI3.** The budget margin is thin. If the measured `wc -l`
  lands in the 380s, take the `loaderkit/bound.py` split pre-emptively rather
  than leaving 5–15 lines of headroom for a later docstring edit to breach.

Trail followed: `logisphere-design-review` skill; design §6.1/§6.3; ADR-001
(deterministic/judgemental boundary, message-is-behaviour); ADR-003 (no import
cycle, single-home discipline); AGENTS.md (400-line cap, gates, en-GB Oxford
spelling); `pyproject.toml` (`[tool.interrogate] fail-under = 100`,
`[tool.ruff.lint.pydocstyle] convention = "numpy"`). Source files re-read in
full: `loaderkit/{coerce,parse,scan,__init__}.py`,
`rulepack/{_coerce,parse,detect}.py`, `ledger/{_coerce,parse,_fields,detect}.py`,
`tests/test_loaderkit_{scan,parse}.py`.
