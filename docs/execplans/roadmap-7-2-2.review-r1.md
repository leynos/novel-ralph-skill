# Logisphere design review — roadmap 7.2.2 ExecPlan (round 1)

Status: REVISE (blocking defects below). Reviewer: adversarial Logisphere crew.

Verified against worktree source on 2026-06-27: `rulepack/_coerce.py`,
`ledger/_coerce.py`, both `parse.py`, both `detect.py`, `contract/errors.py`,
the two `errors.py`, `ledger/_fields.py`, `docs/roadmap.md` §7.2.2,
`docs/developers-guide.md`, `docs/novel-ralph-harness-design.md` §6,
`docs/adr-001`, `docs/adr-003`, `AGENTS.md`, the `Makefile`, and the named test
files. The cuprum read-only sibling was not needed (plan correctly asserts and
I confirmed via grep that neither package touches cuprum).

## BLOCKING

### B1 — `entries` cannot reproduce the empty-array message verbatim (insufficient parameterization)

The plan's `entries(mapping, *, array_key, errors, offending_id)` carries only
`array_key` plus the `CoercionErrors` bundle (`per_id_noun`, `per_level_noun`).
But the empty-array message has THREE independent lexical axes between packages:

- rulepack: `"'rule' array is empty; a pack must declare at least one rule"`
- ledger:
  `"'device' array is empty; a ledger must declare at least one device"`

The pieces are: array key (`'rule'`/`'device'` = `array_key`), **container
noun** (`pack`/`ledger`), and **item noun** (`rule`/`device` = `per_id_noun`).
The container noun "pack"/"ledger" is NEITHER `per_id_noun` ("rule"/"device")
NOR `per_level_noun` ("rule pack"/"device ledger"). Work item 2 asserts "The
three messages … are copied verbatim with the array key substituted" — that
is false for this message. As specified, `entries` cannot emit byte-identical
prose for both packages, which violates the Constraints ("'array is empty' …
reproduced verbatim") and the roadmap success criterion ("operator messages are
unchanged"). Fix: give `entries` an explicit container-noun parameter (or pass
the two full message templates), or keep `_entries`/the empty-array branch
in-package and share only the structural Sequence/Mapping guards. Decide and
pin in the plan; do not leave it to implementer improvisation.

### B2 — `where(errors, None)` is the wrong prefix source for `entries`; the entries messages never used `_where`

Work item 2 instructs raising the entries faults "with the per-level noun from
`where(errors, None)`". But none of the three entries messages call `_where` in
either package today. `where(errors, None)` returns `per_level_noun` = "rule
pack"/"device ledger", which appears in NONE of the entries messages. The "at
index N must be a table" message uses the bare per-id noun (`rule`/`device`),
the "must be an array of tables" and "array is empty" messages use the quoted
array key. Following the WI2 instruction literally would inject the wrong noun
and drift every entries message. Rewrite WI2 to copy each of the three format
strings verbatim (parameterized per B1), not to route them through `where`.

### B3 — The plan's own safety net does not catch B1/B2 (silent-drift hazard)

The plan leans throughout on "the existing suites assert message substrings, so
any wording drift reddens a suite" as the contract-preservation proof (Risks
1-2, WI4/WI5 acceptance). Verified: NO existing test asserts the empty-array
message or the "at index N must be a table" message; only
`test_rulepack_loader.py:315` asserts the substring `"array of tables"` (which
the `array_key` substitution preserves). So a "pack"/"ledger" container-noun
drift from B1 would ship GREEN — no gate catches it. This breaks the plan's
central testability claim for the `entries` primitive. The new `loaderkit` unit
tests (WI2) must pin the FULL empty-array and at-index messages for BOTH noun
sets verbatim, not just assert "the array key is in the message". Until that
pin exists, the entries reroute is not testable to the standard the plan claims.

### B4 — D-SCANTYPES leaves two live mechanisms; the chosen one is unproven against `ty`

The Decision Log (D-SCANTYPES) and Work item 3 explicitly carry TWO competing
scan-layering mechanisms (TYPE_CHECKING-only import + `line_hit` callable, vs.
runtime import with a function-local import to break the cycle) and defer the
choice to implementation. An ExecPlan is meant to be decided; deferring a
load-bearing structural decision to "decide one in the Decision Log when
implementing" pushes a real risk past review. Worse, the preferred mechanism
(import `ScannedChapter`/`LineHit` only under `TYPE_CHECKING`, return type
`tuple[int, tuple[LineHit, ...]]`) is asserted to satisfy `ty` but NOT
verified; the plan's own fallback paragraph admits "`ty` cannot resolve the
string-annotated return through the callable" is a live possibility. Note also
`ledger/detect.py:34` ALREADY imports `LineHit` from `rulepack.detect` at
runtime (a runtime `ledger → rulepack.detect` edge exists today and is
sanctioned by D-SCANTYPES/Constraints). The plan must (a) pick ONE mechanism
now, and (b) either cite/prove it type-checks or pin it with a spike, before
this is implementable as written. Recommend: choose the simplest acyclic option
and demonstrate it, rather than carrying a branch.

## ADVISORY

### A1 — `reject_duplicate_ids` ordering/first-duplicate semantics not pinned

Both current bodies iterate the sequence and raise on the FIRST repeated id in
authoring order. The plan generalizes to `Iterable[str]` and the callers pass a
generator (`rule.id for rule in rules`). The WI2 test says "raises … naming
the first repeat" — good — but the plan should state explicitly that the shared
primitive preserves authoring-order first-duplicate detection, since a
set-based rewrite could change WHICH id is named. The message
`"<noun> '<id>' is defined more than once; ids must be unique"` is not asserted
by any test I found either; the WI2 pin should cover it verbatim for both nouns.

### A2 — `load_toml` `Traversable` import/typing not specified

WI2 types `path: Traversable` but does not say `loaderkit` must import
`importlib.resources.abc.Traversable` (both `load_*` use it today). Name the
import so `ty` resolves the annotation; trivial but currently implicit.

### A3 — `interrogate` 100% covers module-level docstrings too

The plan commits to full docstrings on functions/dataclasses (good) but
`loaderkit/__init__.py`, `coerce.py`, `load.py`, `scan.py` each need a module
docstring for `interrogate` at 100%. WI1 names the `__init__` docstring; confirm
`load.py`/`scan.py` module docstrings are in scope too.

### A4 — Verify the 400-line cap headroom claim for `coerce.py`

The plan estimates the merged `coerce.py` at ~200 lines. The two source files
are 180 and 192 lines and the merged module adds the `CoercionErrors` dataclass
and its docstring; with full NumPy docstrings the merge could exceed 200 but
should stay under 400. Acceptable, but the split fallback (`factory.py`+
`coerce.py`) should be the default if it lands over ~320, not a last-minute
scramble.

## What the plan got RIGHT (verified)

- Six primitives are genuinely the duplicated set; schema glue
  (`_resolve_basis`,
  `_rationing_fields`, `_window*`, `_rule`/`_device`) is genuinely distinct and
  correctly scoped OUT.
- Error constructors confirmed: `RulePackError(*messages, rule_id=...)`,
  `LedgerError(*messages, device_id=...)`; the `content_error` lambda bridge is
  correct, and `EnvelopeMessagesError(*messages)` is the shared base.
- File-fault message `f"cannot read {noun} at {path}: {exc}"` is byte-identical
  bar the noun across both packages — D-FILELOAD parameterization is sound.
- `_where`, `_require*`, `_reject_unknown_keys`, `_compile_pattern`,
  `_reject_duplicate_ids` (the per-id branches), and both `_scan_*` are
  correctly parameterizable on the bundle/noun pair; scan bodies are
  byte-identical.
- D-HOME (`loaderkit` neutral leaf depending only on `contract` + stdlib) keeps
  the dependency direction acyclic and matches design §3.1 / ADR-003.
- D-BINDING (thin per-package `_coerce` re-exporting the underscore wrappers,
  `_fields.py` needs no edit) is sound: `_fields.py` imports `_Mapping`,
  `_require`, `_require_int`, `_where` and the binding re-exports all four.
- cuprum / Cyclopts / pytest-timeout / uv: correctly asserted out of scope; the
  plan adds no CLI surface, no dependency, no subprocess. No external-library
  behaviour claim needs firecrawl citation because the plan moves existing
  stdlib calls verbatim rather than relying on any unpinned behaviour.
- All cited doc anchors (developers-guide ~1318/1403/1608, design §6.1/6.3,
  ADR-001/003, roadmap 7.2.2 quote) are accurate.

## Pre-mortem (Doggylump)

Six months on, a third pack family (roadmap §8.1) binds `loaderkit` and ships.
An operator hits an empty-pack and the message reads "a rule pack must declare
at least one rule" instead of "a pack must declare …" — drift introduced by
B1, never caught because B3 means no test pins it. Blast radius:
operator-facing prose only, but it silently violates the roadmap's "operator
messages unchanged" contract and the design's self-describing-envelope
guarantee. Prevention designed in now: WI2 pins every entries/scan/file message
verbatim for both noun sets (closes B3), and `entries` gets the container-noun
parameter (closes B1).

## Alternatives checkpoint (Wafflecat)

Strongest alternative to the full six-primitive extraction: extract only the
FOUR genuinely noun-clean primitives (the `_coerce` family + `compile_pattern` +
`load_toml` + `scan_pattern`) into `loaderkit`, and leave `_entries` and its
three bespoke messages in each package as a thin per-package function calling a
shared *structural* guard (Sequence/Mapping check) that takes the full message
strings. Trades: keeps two ~6-line `_entries` shells (less "one home" purity)
but sidesteps B1/B2 entirely and removes the riskiest noun-parameterization.
Gains a simpler, provably-verbatim contract. Worth weighing against forcing a
three-noun `entries` signature.
