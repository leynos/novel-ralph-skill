# Logisphere design review — ExecPlan roadmap 7.2.2 (round 2)

Status: PROCEED (no blocking defects). Reviewer: adversarial Logisphere crew.
Date: 2026-06-27.

Scope: adversarial design review of `docs/execplans/roadmap-7-2-2.md` (round-2
DRAFT). Read from disk, not from the planner's summary. Every load-bearing
empirical claim was re-verified against the worktree source and `uv.lock`; the
four round-1 blockers (B1–B4) were checked for genuine resolution, not merely
asserted resolution.

## Verdict

PROCEED. The round-2 plan is implementable and design-conformant as written.
The four round-1 blockers are genuinely closed, and the closures rest on facts
I re-verified independently rather than on the planner's word.

## Round-1 blockers — independently re-verified as closed

- B1/B2 (entries parameterization + wrong prefix source). Verified against
  `rulepack/parse.py:96-106` and `ledger/parse.py:98-105`: the three entries
  faults (`not_array`, `empty`, `non_mapping`) embed the *quoted array key* and
  a *container/item noun* and **never** call `_where`. The empty-array
  container noun (`pack`/`ledger`) is neither `per_id_noun` (`rule`/`device`)
  nor `per_level_noun` (`rule pack`/`device ledger`). D-ENTRIES'
  full-verbatim-string `EntriesMessages` bundle is therefore the correct and
  only drift-proof shape. The *missing*-array fault correctly stays on the
  shared `require`/`where` path (`per_level_noun`), which is the right split —
  the plan handles this correctly (WI2 §1:
  `value = require(mapping, array_key, …, offending_id=None)`).
- B3 (safety net does not catch entries drift). Verified: the only existing
  assertion over any of these strings is `tests/test_rulepack_loader.py:315`
  (`"array of tables"`). The empty-array, at-index, and duplicate-id messages
  have **no** existing pin in `tests/`. WI2's verbatim pins (both noun sets)
  close the gap. Accurate.
- B4 (two scan mechanisms; chosen one unproven against `ty`). Verified:
  `uv.lock:778-779` pins `ty == 0.0.51`; `Makefile:110-112` runs `ty --version`
  then `ty check`, so the spike claim is mechanically consistent. The chosen
  TYPE_CHECKING-only-import + `line_hit`-callable mechanism is sound:
  `ledger/ detect.py:34` already imports `LineHit` at runtime from
  `rulepack.detect`, and `ScannedChapter` only under TYPE_CHECKING (line 40),
  so the acyclicity argument holds.

## Source-conformance checks (all passed)

- Message strings: `not_array`/`empty`/`non_mapping` for both packages match the
  plan's verbatim bindings byte-for-byte (`rulepack/parse.py:98,101,105`;
  `ledger/parse.py:98,101,105`).
- File-fault body: `f"cannot read {noun} at {path}: {exc}"` then
  `*FileError(msg) from exc`, returning `parse_*(raw)` — matches D-FILELOAD
  (`rulepack/parse.py:388-392`, `ledger/parse.py:309-313`). `RulePackFileError`/
  `LedgerFileError` inherit `EnvelopeMessagesError.__init__(*messages: str)`
  with no override, so `file_error=RulePackFileError` (single positional str)
  is valid.
- Error constructors: `RulePackError(*messages, rule_id=None)` /
  `LedgerError(*messages, device_id=None)` (`rulepack/errors.py:41`,
  `ledger/errors.py:43`), so the bundle lambdas
  `lambda msg, rid: RulePackError(msg, rule_id=rid)` are correct.
- Duplicate-id loop: `seen: set`, first-duplicate-in-authoring-order, verbatim
  `"{_where(id)} is defined more than once; ids must be unique"`
  (`rulepack/parse.py:289-295`, `ledger/parse.py:209-215`). Advisory A1
  preserved.
- Scan body: both `_scan_rule`/`_scan_device` are the identical
  `splitlines()`-enumerate(start=1)-`finditer` loop constructing
  `LineHit(chapter=chapter.number, line=index)` (`rulepack/detect.py:172-180`,
  `ledger/detect.py:131-137`). The `line_hit(chapter_number, line_index)` seam
  is faithful.
- `_where` bodies: `f"rule {rule_id!r}"`/`"rule pack"` and
  `f"device {device_id!r}"`/`"device ledger"` (`rulepack/_coerce.py:43`,
  `ledger/_coerce.py:54`). The `where(errors, …)` re-implementation is verbatim.
- Import graph: `_coerce` consumers are exactly `rulepack/parse.py`,
  `ledger/parse.py`, `ledger/_fields.py` (grep-confirmed). cuprum absent from
  both packages (grep-confirmed). The plan's "no cuprum claim to pin" is
  correct.
- Locked-library claims: the plan correctly asserts it leans on **no** Cyclopts
  /
  pytest-timeout / uv-run behaviour and **no** new dependency. Verified: the
  primitives are pure stdlib (`tomllib`/`re`/`collections.abc`/`typing`/
  `dataclasses`) moved verbatim, plus the in-repo `EnvelopeMessagesError`. No
  external-library behaviour requires a firecrawl citation because none is
  relied upon. This is the correct disposition, not an evasion.

## Residual advisory notes (non-blocking)

- A-r2-1 (advisory). The *missing*-array message
  (`"rule pack is missing required key 'rule'"` /
  `"device ledger is missing required key 'device'"`) has no dedicated existing
  test pin either, but it routes through the shared `require`/`where` path,
  whose prose WI1's `where` and `require` tests pin (both per-level nouns
  verbatim). This is adequately covered; no action required, but the
  implementer should ensure WI1's `require` test asserts the `where`-derived
  per-level prefix appears, so the missing-array prefix is transitively pinned.
- A-r2-2 (advisory). WI3 prose says the body constructs hits via
  `line_hit(chapter.number, index)` while the caller lambda is
  `lambda chapter, line: LineHit(chapter=chapter, line=line)`. These are
  consistent (positional: arg0 = chapter number, arg1 = line index), but the
  implementer must keep the call positional and not accidentally swap the two
  ints — a swap would type-check cleanly (`int, int`) yet invert chapter/line.
  WI3's example tests (chapter-attribution and same-line-number) catch a swap;
  keep both.
- A-r2-3 (advisory). The `make all` gate runs `interrogate` 100% and Pylint via
  a
  PyPy shim (`Makefile:106-107`); the plan's docstring-coverage mitigation is
  sound. No action.

## Pre-mortem (Doggylump)

The round-1 pre-mortem scenario (a container-noun drift shipping green) is
closed by WI2's verbatim pins. The remaining plausible 03:00 scenario is
A-r2-2: a chapter/line argument swap in a `line_hit` lambda that type-checks
but corrupts every detection report's line/chapter attribution. Mitigation
already in the plan: WI3's `test_hits_across_chapters_carry_right_chapter` and
`test_two_hits_one_line_carry_same_line_number` both fail on a swap, and the
ledger snapshot (WI5) would churn. Adequately defended.

## Alternatives checkpoint (Wafflecat)

The round-1 alternative (thin per-package `_entries` shells over a
structural-only guard) is explicitly considered and rejected in D-ENTRIES with
a sound rationale: the shell would re-fork the empty-array/at-index *control
flow*, which is exactly what 7.2.2 removes, whereas the `EntriesMessages`
bundle keeps both the guards and their ordering single-homed while guaranteeing
verbatim prose. No stronger alternative survives; this is a signal the design
is on solid ground.

## Bottom line

The plan's work items are atomic, ordered (primitives 1–3 land before reroutes
4–5; docs 6 last), independently gate-passable, and testable; validation is
specified mechanically (greps for single-definition + verbatim message pins);
and nothing contradicts the deterministic/read-only boundary (ADR-001), the
layering (ADR-003, design §3.1), or the frozen typed-error/exit-code/message
contracts. I would stake my name on it being implementable and
design-conformant as written.
