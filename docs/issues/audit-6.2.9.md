# Post-merge audit: roadmap task 6.2.9

Audit of the codebase following the merge of roadmap task 6.2.9, "Extend the
installed per-chapter loop re-drive to the refused-advance and crossed-gate
decisions" (commit `ab380c0`). The change adds installed BDD coverage for the
out-of-order `advance-phase` refusal over the wheel/venv boundary and a wheel-free
mark guard for it.

Scope of the merged change: `tests/features/per_chapter_loop_installed.feature`,
`tests/steps/per_chapter_loop_installed_steps.py`,
`tests/test_per_chapter_loop_installed_bdd.py`, and `docs/developers-guide.md`.

Trail followed: `docs/roadmap.md` task 6.2.9 and its step-task source
(audit:6.2.2 Finding 7); `docs/novel-ralph-harness-design.md` §3.2, §4.1, §4.5,
§5.4, §9, §10; ADR-003, ADR-006; `docs/developers-guide.md`; `AGENTS.md` code-style
and quality-gate rules. Explored with `leta`/`grep` over the test tree and traced
history with `git show ab380c0`.

Findings are listed by severity. None block the merge; all are tidy-up or
consistency items suitable for an addendum lane.

## Finding 1: Commit message overstates "crossed-gate" as a new installed scenario (low)

- **Category:** docs-gap / inconsistency
- **Location:** commit `ab380c0` message; `tests/features/per_chapter_loop_installed.feature`
- **Severity:** low

The commit subject and body state the change "Adds installed BDD scenarios and
steps for the refused-advance **and crossed-gate** decisions". In fact the
installed feature gains exactly one new scenario — the refused out-of-order
`advance-phase`. The crossed-gate behaviour is **not** a new installed scenario:
it was already asserted inside the pre-existing clean-pass scenario via the
`installed wordcount reports all three knitting gates crossed` step
(`gate_triggered_30/50/80`), and that step is unchanged by this commit. The body
later half-corrects this ("the crossed knitting gate, proven *as part of* the
clean pass"), but the headline framing reads as if a second decision crossed the
boundary here when only one did.

The `developers-guide.md` prose is accurate; the discrepancy is solely in the
commit narrative, which is now immutable history. Recording it here prevents a
future reader from grepping for a non-existent installed crossed-gate scenario.

- **Proposed fix:** No code change. Note in the roadmap 6.2.9 closure (and any
  future similar task) that the crossed-gate decision is covered *within* the
  installed clean-pass scenario, not as a standalone scenario, so the commit
  subject's "and crossed-gate" is shorthand for "asserted in the clean pass",
  not "a new scenario". If a standalone installed crossed-gate scenario is
  actually wanted for symmetry with the in-process feature, see Finding 2.

## Finding 2: Installed feature omits the standalone crossed-gate scenario the in-process feature carries (low)

- **Category:** inconsistency / test-gap
- **Location:** `tests/features/per_chapter_loop_installed.feature` vs
  `tests/features/per_chapter_loop.feature`
- **Severity:** low

The in-process feature models all four §9 deterministic decisions, with the
crossed knitting gate as its **own focused scenario** (`Scenario: a crossed
knitting gate is reported`) *in addition to* asserting gates in the clean pass.
The installed feature models three of the four and folds the crossed gate into
the clean-pass scenario only. The asymmetry is deliberate and documented (the
developers' guide calls it out, and a separate scenario over a fresh tree would
build no new behaviour at the boundary because the clean-pass tree already
crosses all three gates), so this is a consistency note rather than a defect.

The risk is that the two features now diverge in shape: a reader comparing them
expects a one-to-one scenario mapping and finds three-to-four. The reason the
installed side has no standalone crossed-gate scenario is that it would re-run
the same `wordcount` over the same all-hold tree the clean pass already drives —
pure duplication at the slow wheel boundary — so omitting it is correct, but the
rationale lives only in the developers' guide, not adjacent to the feature.

- **Proposed fix:** Add a one-line comment to the installed feature header
  (where it already enumerates "the headline clean pass … the stale-compile
  catch … the refused out-of-order advance-phase") stating explicitly that the
  crossed knitting gate is asserted *within* the clean-pass scenario and is
  intentionally **not** a standalone installed scenario, because a separate slow
  scenario over the same all-hold tree would add no boundary signal. This keeps
  the asymmetry self-documenting at the feature, closing the gap a cross-feature
  reader would otherwise hit.

## Finding 3: The two `*_carries_marks` guard tests are near-identical and invite parametrization (low)

- **Category:** duplication / similarity
- **Location:** `tests/test_per_chapter_loop_installed_bdd.py`,
  `test_installed_scenario_carries_marks` and
  `test_installed_advance_refused_carries_marks`
- **Severity:** low

The two mark-guard tests differ only in (a) the bound function whose `pytestmark`
they read (`test_installed_per_chapter_loop` vs
`test_installed_advance_phase_refused`) and (b) the noun in the assertion message.
Their bodies are otherwise byte-identical: same `typ.cast`, same `getattr(...,
"pytestmark", ())`, same `marks >= _REQUIRED_MARKS` check. As more installed
scenarios are added (the convention the developers' guide tells contributors to
follow), this copy-the-guard pattern will accrete one near-clone per scenario.

This violates the `AGENTS.md` "avoid repetition by extracting reusable logic"
rule and the design intent that the guard be a single, named safety net per
scenario rather than a duplicated block.

- **Proposed fix:** Replace the two functions with one
  `@pytest.mark.parametrize`d test over `(bound_function, label)` pairs — for
  example `pytest.param(test_installed_per_chapter_loop, "clean-pass", id=...)`
  and `pytest.param(test_installed_advance_phase_refused, "refused-advance",
  id=...)` — that asserts `marks(fn) >= _REQUIRED_MARKS` once. The parametrize
  list then becomes the single registration point a new installed scenario
  appends to, instead of a fresh copied function. This keeps each scenario named
  in the test id (so a dropped mark still fails a clearly identified case) while
  removing the cloned body, and makes "add your scenario to the guard list" a
  one-line change for future contributors.

## Finding 4: `_run_installed_argv` is a documented command-query hybrid; consider the rule's boundary (low)

- **Category:** cqs
- **Location:** `tests/steps/per_chapter_loop_installed_steps.py`,
  `_run_installed_argv`
- **Severity:** low

`_run_installed_argv` both mutates state (writes `installed.captures[capture_key]`)
and returns the same tuple, so callers may "use the helper for its side effect
alone" (its own docstring). This is a command-query separation hybrid that
`AGENTS.md` flags ("obey command/query segregation"). The docstring acknowledges
and justifies it: the `When` steps invoke it purely for the side effect, while
`_run_installed` consumes the return to stay byte-identical with the clean-pass
loop. The justification is reasonable for a test helper, and the in-process
sibling (`_run_capturing`) has the same shape, so this is a noted trade-off, not
a defect.

- **Proposed fix:** Optional. If strict CQS is wanted, split into a command
  `_capture_installed(installed, script, argv, *, key) -> None` that only writes
  the capture map, and let callers needing the value read `installed.captures[key]`
  back. Given both step modules already adopt the hybrid and document it, the
  lower-churn option is to leave it and record the deliberate exception in the
  developers' guide's test-helper conventions so the pattern is sanctioned rather
  than silently repeated.

## Finding 5: Parallel `_Outcome`/`_Installed` step harnesses share structure with no shared base (low)

- **Category:** duplication / separation-of-concerns
- **Location:** `tests/steps/per_chapter_loop_steps.py` (`_Outcome`,
  `_result`, `_run_capturing`) and
  `tests/steps/per_chapter_loop_installed_steps.py` (`_Installed`,
  `_result`, `_run_installed*`)
- **Severity:** low

The in-process and installed step modules now carry structurally parallel
machinery: a slotted dataclass with a `captures: dict[str, tuple[...]]` map and
a `state_before: bytes | None` field for the refused-advance proof; a `_result`
helper that returns `envelope["result"]` from a named capture; and a per-command
run helper. The duplication is intentional — the modules are deliberately split
so the in-process suite does not import the `cuprum` installed fixtures (design
and ExecPlan decision D-INSTALLED-SPLIT) — and the capture-tuple shapes differ
(the installed tuple carries `stderr` for the no-traceback check; the in-process
tuple does not). So this is a controlled, not accidental, parallel.

The risk is drift: the two `_result` helpers and the two `state_before`/`captures`
contracts must stay semantically aligned for the cross-boundary "same decision,
two boundaries" claim to hold, yet nothing enforces that alignment. A change to
the envelope `result` shape would need both helpers updated in lockstep with no
test linking them.

- **Proposed fix:** Do not merge the modules (the import-isolation reason is
  sound). Instead, extract the boundary-agnostic pieces — the `result`-block
  extraction and the `captures`/`state_before` field contract — into a small
  shared helper module under `tests/` (for example `tests/_loop_capture.py`) that
  both step modules import, with each module retaining only its boundary-specific
  run function. This keeps the split that matters (fixture imports) while removing
  the two `_result` clones and giving the shared capture contract a single
  definition. Lightweight; only worth doing if a third loop boundary is foreseen.

## Summary

The 6.2.9 change is well-tested, well-documented, and closes audit-6.2.2
Finding 7 cleanly: the refused out-of-order `advance-phase` crosses the wheel/venv
boundary (exit 3, `state.toml` intact, no traceback), and a wheel-free mark guard
protects the new scenario's slow/timeout/POSIX marks. The developers' guide was
updated accurately and in step with the code.

All five findings are low severity. The most actionable is Finding 3 (parametrize
the two near-identical mark guards), which both removes a clone and makes the
documented "add a guard per scenario" convention a one-line append. Findings 1 and
2 are consistency/clarity notes about the crossed-gate framing; Findings 4 and 5
are deliberate, documented test-helper trade-offs recorded for future drift watch.
