# Logisphere design review — roadmap 7.1.4 ExecPlan, round 2

Verdict: PROCEED. The plan is implementable and design-conformant as written.

## What was verified against real source (not the planner's summary)

- `render_machine` (`contract/envelope.py:126-151`) builds `result=dict(env.result)`
  and calls `json.dumps(ordered)` with no `sort_keys` — so `result` insertion
  order is observable in the raw machine JSON. CONFIRMED.
- `CommandOutcome.__post_init__` freezes `result` via `freeze_mapping`
  (`_freeze.py:27`), which is `MappingProxyType(dict(mapping))` — order-preserving.
  The freeze step does not reorder keys, so the builder's insertion order survives
  through to the JSON line. CONFIRMED (closes a latent gap the plan does not
  explicitly call out but relies upon).
- The `.ambr` snapshot serializes rule-pack `result` keys alphabetically
  (`findings, pack, total_words, violations` in
  `test_desloppify_snapshots.ambr`), proving syrupy sorts and the snapshots
  cannot guard insertion order. CONFIRMED.
- The cross-command matrix asserts only `set(result)`
  (`test_command_surface_matrix.py:613`). CONFIRMED.
- Live source still derives the exit code from `report.passed`
  (`_desloppify_report.py:180`, `ledger/report.py:131`); addendum 8.1.3.2 is
  `- [ ]` in `docs/roadmap.md`. So 7.1.4 lands first and owns the
  exit-code-from-`failed` derivation. CONFIRMED.
- Detection cores set `passed=all(finding.passed …)` (`rulepack/detect.py:277`,
  `ledger/detect.py:279`), so `passed == not failed` for every real report — the
  exit-code change is observationally identical on real inputs. CONFIRMED.
- The two skeletons are verbatim-identical except the five injectable details.
  CONFIRMED by reading both functions.
- `contract` is the lowest layer; both call sites already import from it; the
  no-cycle invariant is recorded (`contract/errors.py`). The builder being
  generic over a `TypeVar` finding with injected callables introduces no import.
  CONFIRMED.
- The recommended builder signature (`extra_result=...` defaulted, then
  `clean_message: str` undefaulted) is legal because both are keyword-only
  (after `*`). CONFIRMED by execution.
- No external-library (cuprum, Cyclopts, pytest-timeout, pytest-xdist, uv)
  behaviour is load-bearing: the task is in-process pure Python operating on
  in-memory dataclasses, invoking no subprocess. The decision-log claim is
  accurate; no firecrawl verification is owed. CONFIRMED.

## Round-1 defect resolution

Round 1's sole blocking defect — a false claim that the raw-JSON key order was
guarded by the e2e suites — is corrected throughout (Context, Risk #1, Decision
Log) and a real call-site key-order regression guard is promoted to a required
test and acceptance criterion in Work item 2 (`list(outcome.result)` on the real
`report_outcome`/`ledger_report_outcome`). The correction matches source.

## Panel notes (advisory only — none blocking)

- Pandalump (structure): boundaries hold; the builder sits at the correct layer
  and both call sites shrink. No 400-line breach.
- Telefono (contracts): the envelope, `result` shape/order, exit-code, and
  slimmed-findings contracts are preserved; the key-order guard is the right
  instrument. Advisory: the WI1 builder unit test should assert
  `list(result) == ["violations", "findings"]` for the no-`extra_result` case
  *and* that `extra_result` keys never collide with `violations`/`findings`
  (a caller passing `{"violations": …}` in `extra_result` would be silently
  overwritten or double-inserted) — worth one defensive assertion or a docstring
  note, though no current caller does this.
- Doggylump (failure modes / pre-mortem): the one realistic failure is a
  mis-wired `extra_result` key order at the rule-pack call site; the required
  WI2 guard catches exactly this. Advisory: when running the WI2
  `pytest --snapshot-update` no-regeneration check, run it serially (the recipe
  already omits `-n`), because syrupy `--snapshot-update` under xdist can churn
  orphaned snapshots. The recipe as written is safe.
- Buzzy Bee (scaling): N/A — O(findings) projection, unchanged.
- Wafflecat (alternatives): the strongest alternative is to inject
  `report.passed` directly rather than a `passed` callable and re-derive nothing
  — but that re-introduces the exact `passed`-vs-`failed` divergence 8.1.3.2
  names. The plan's choice (derive from the `failed` list it filters) is the
  correct one and is the whole point of folding in the addendum. No better
  alternative exists.
- Dinolump (viability): atomic, ordered, test-first, idempotent; matches the
  established roadmap-7.1.x refactor cadence.

## Advisory items (do not block merge)

1. WI1 builder test: add a defensive assertion or docstring note that
   `extra_result` keys must not shadow `violations`/`findings` (no current caller
   does, so this is hardening only).
2. WI2 snapshot no-regeneration check: keep it serial (already the case in the
   recipe); note this explicitly so an implementer does not add `-n auto`.
