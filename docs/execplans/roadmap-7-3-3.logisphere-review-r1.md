# Logisphere design review — roadmap 7.3.3, round 1

Target: `docs/execplans/roadmap-7-3-3.md` (Consolidate the draft-read
state-error wrapper shared by `wordcount`, `recount`, and `desloppify`).

Reviewer mandate: adversarial pre-implementation design review. Assume the plan
is flawed until proven otherwise; verify every load-bearing claim against the
real source.

## Verdict: PROCEED WITH CONDITIONS (no blocking defects)

Every load-bearing claim in the plan was checked against the tree and against
the read-only cuprum sibling. The plan is implementable and design-conformant as
written. The findings below are advisory: they would sharpen the plan but none
blocks implementation, and none requires relaxing the design.

## What was verified against source (not the planner's summary)

- The three guard sites match the plan's description exactly. All three carry the
  identical `try: <read>; except STATE_INPUT_ERRORS as exc: raise
  _draft_read_error(<dir>) from exc` shell:
  - `_recount._recount_or_state_error` — body at `_recount.py:94-97`.
  - `_wordcount._recount_or_state_error` — body at `_wordcount.py:99-102`.
  - `_desloppify.source_chapters` — tail at `_desloppify.py:199-211`, with
    `load_or_state_error` and `_select_chapters` correctly *outside* the `try`.
  (The plan's cited line ranges are a few lines stale but the spans are right.)
- `state_sourcing.py` is 382 lines (the plan says 383 — immaterial; the ≤400 cap
  holds with ~18 lines of headroom before the guard, comfortably inside budget
  for a ~30-45 line addition... see advisory A1).
- `_draft_read_error(reported_dir: pathlib.Path) -> StateInputError` signature
  confirmed (`state_sourcing.py:191`); it renders from `reported_dir` alone.
- `STATE_INPUT_ERRORS` is a module-level tuple (`state_sourcing.py:103`); the
  private formatters are excluded from `__all__` (lines 43-50), consistent with
  adding `draft_read_guard` as the lone new *public* member.
- All three command modules already import `_draft_read_error` and
  `STATE_INPUT_ERRORS` from `state_sourcing` at runtime, so the plan's
  "drop-if-Ruff-flags" hedge is the correct posture (the runtime imports become
  unused only at the two reader sites; docstring `:func:` references are not
  runtime uses).
- **The WI1 mechanism is already proven in-tree.** `novel_ralph_skill/state/
  document.py:303-306` is an existing `@contextlib.contextmanager` returning
  `cabc.Iterator[TOMLDocument]`, with `import collections.abc as cabc` under
  `if typ.TYPE_CHECKING:` and `from __future__ import annotations` at the top —
  exactly the shape WI1 proposes. `ty` and Ruff already pass on it. The plan's
  worry about whether the annotation is evaluated at runtime is therefore settled
  in its favour; the `cabc`-under-`TYPE_CHECKING` placement is correct.
- `recount_words` (`state/wordcount.py:86`) and `_chapter_text` absorb the absent-
  `draft.md` fault benignly (0/""), so the guard only ever sees non-benign faults
  — the §3.2 deterministic exit-3 boundary is preserved.
- Roadmap 7.3.3 (`docs/roadmap.md:2970`) names exactly `wordcount`/`recount`/
  `desloppify` and requires the neutral state-sourcing home, not `novel_state`.
  The plan's scope decision (D2) and home constraint conform.
- The cuprum surface the e2e suites use (`cuprum.sh.make` at `sh.py:528`,
  `ExecutionContext` at `sh.py:169`, `run_sync` at `sh.py:441`, `capture` param,
  `ProgramCatalogue.lookup` at `catalogue.py:79`, `UnknownProgramError` at
  `catalogue.py:28`) is verified against the read-only sibling
  `/data/leynos/Projects/cuprum/cuprum/`. The refactor does not touch the
  binary-invocation path, so the plan's claim that the e2e suites stay green
  unedited holds.
- The plan correctly caught and corrected the roadmap's own *stale* claim that
  `_wordcount`/`_desloppify` still share `f"cannot read chapter drafts: {exc}"`:
  6.3.5 already routed all six boundaries through `_draft_read_error`. The plan's
  Surprises section documents this; the consolidation target is the control-flow
  shell, not the message. Good adversarial-resistant planning.

## Panel findings

### Pandalump (structural integrity) — sound

The boundary the guard wraps is the *exact* span the current `try` covers, and
the plan keeps `load_or_state_error`/`_select_chapters` outside it (R2). The home
(`state_sourcing`) is the dependency-free leaf the design and developers-guide
already document as the single home for fault routing. No new cross-module edge,
no cycle: the guard reuses module-local `_draft_read_error`/`STATE_INPUT_ERRORS`
and adds only stdlib imports.

🟢 A1 (advisory): the plan states the file is 383 lines and the addition is
"~30-45 lines of body plus docstring". The proposed docstring alone is ~25 lines.
382 + ~45 = ~427 would breach the 400-line cap. The plan does flag this (Risk R4,
Tolerance) and says "escalate rather than split". That is the right guard, but
the arithmetic is closer than the plan implies — the implementer should expect
to either trim the docstring example or hit the escalation point on WI1, not
treat the cap as comfortable headroom. Recommend the plan pre-state a target
docstring length (e.g. ≤18 lines incl. the one example) so WI1 lands under cap by
construction rather than by luck.

### Telefono (contracts & interfaces) — sound

`draft_read_guard(reported_dir: pathlib.Path) -> Iterator[None]` mirrors
`_draft_read_error`'s single parameter (D3), so the six sites share one signature
and the other three can adopt it later with no change. Public-in-`__all__` is the
correct seam choice (matches `load_or_state_error`). The exit-3 envelope, the
`raise … from exc` chaining, and the actionable-only `messages` channel are all
preserved verbatim.

### Doggylump (failure modes) — sound, one sharpening

The pre-mortem the plan must survive: *a draft-read fault silently routes to exit
1 and the harness loops forever on a corrupt manuscript.* The plan pins this with
the unchanged `test_draft_read_message_parity.py` (all six boundaries) plus the
new WI5 structural test. The `tuple(...)`-eager-evaluation note in WI4 is the
subtle correct call: a lazy generator would defer the reads past the `with` and
escape the guard. The plan calls this out explicitly. Good.

🟡 A2 (unresolved-risk, low): WI5's AST scan asserts "no `ExceptHandler` whose
type is the `Name` `STATE_INPUT_ERRORS` re-raising `_draft_read_error`" in the
three migrated modules. This pins *absence* of the old shell but does not, on its
own, assert the guard catches the *same tuple*. If a future edit narrows
`STATE_INPUT_ERRORS` membership, the guard quietly under-catches and the parity
test is the only net. That net is real (parity drives every member from a corrupt
tree), so this is not blocking — but WI5 would be stronger if it also asserted
each migrated module's reader is wrapped in a `with draft_read_guard(...)` (the
plan already asserts the import; assert the *use*). Cheap to add; recommend it.

### Buzzy Bee (scaling & cost) — n/a, correctly

This is a control-flow DRY refactor with zero runtime-cost or load dimension. No
allocation, no hot path, no I/O change. Buzzy Bee has nothing to bite. The plan
does not over-claim any performance benefit. Correct.

### Wafflecat (alternatives) — the rejected alternative is correctly rejected

The audit offered two shapes: a `read_drafts_or_state_error(working_dir,
manifest)` reader-function and a `state_error_on`/context-manager. The plan's D1
rejects the reader-function because the three read bodies genuinely differ (two
`recount_words` calls with *different return shapes* — `_wordcount` discards the
total, `_recount` keeps the tuple — and one `ScannedChapter` comprehension over
`_chapter_text`). I verified all three bodies; the divergence is real, so a
fixed-reader helper cannot serve all three and would re-introduce shape coupling.
The context manager is the precise abstraction. No credible alternative survives
— a strong signal the design is on solid ground.

The one genuinely-different alternative Wafflecat would float: migrate all six
sites in this slice (the guard is written to serve all six anyway). The plan
defers the other three (D2) to keep the diff inside the roadmap's named surface
and makes adopting them an *escalation point*, not an improvisation. That is the
right atomicity call given the success criterion names only three; recorded, not
silently dropped. Acceptable.

### Dinolump (long-term viability) — sound

The pattern already exists in-tree (`document.py:pending_turn`), the home is
documented, the anti-drift test institutionalizes the single-home property, and
WI6 updates the developers-guide so a future reader is not surprised the other
three sites still open-code the shell. This matches a team that already maintains
exactly this kind of structural test (`test_state_sourcing_home.py`,
`_state_layout_scanner.py`). No skills mismatch.

## Advisories (non-blocking, ordered by value)

- A1 — Pre-state a docstring length budget so WI1 lands under the 400-line cap by
  construction (the 382→~427 arithmetic is tighter than the plan's prose implies).
- A2 — Strengthen WI5 to assert each migrated reader is *inside* a
  `with draft_read_guard(...)`, not only that the import is present and the old
  handler is absent.
- A3 — The plan's WI1 code fence (line ~429) shows `import collections.abc as
  cabc` at module top-level, contradicting its own prose (lines ~466-470) and the
  proven `document.py` pattern (cabc under `TYPE_CHECKING`). Fix the fence to
  match the prose so the implementer is not handed two conflicting instructions.
- A4 — CrossHair `diffbehavior` is offered as "optional/recommended" for WI1. The
  invariant (catch-tuple → translate-and-chain) is small and enumerable; the
  parametrized unit test is the load-bearing adversary. The plan already says
  this. Keep CrossHair belt-and-braces; do not let it become a gate.

## Trail (docs and skills relied on)

- Design: `docs/novel-ralph-harness-design.md` §3.2 (five exit codes), §5.4
  (benign absent-draft absorption).
- ADR-001 (deterministic/judgemental boundary): the guard is pure deterministic
  control flow; no judgemental surface is touched.
- `docs/developers-guide.md` lines 634-682 (the exit-3 formatter / state_sourcing
  home prose WI6 extends).
- `docs/roadmap.md:2270, 2970` (7.3.3 task and success criterion).
- `docs/issues/audit-6.1.1.md` Finding 1 (origin of the triplication).
- AGENTS.md (400-line cap, atomic changes, docstring/example policy, en-GB).
- Source: `state_sourcing.py`, `_recount.py`, `_wordcount.py`, `_desloppify.py`,
  `state/wordcount.py`, `state/document.py` (proving the CM pattern),
  `tests/test_draft_read_message_parity.py`, `tests/test_state_sourcing_home.py`,
  `tests/_state_layout_scanner.py`.
- cuprum (read-only sibling `/data/leynos/Projects/cuprum/cuprum/`):
  `sh.py` (`make`, `ExecutionContext`, `run_sync`, `capture`), `catalogue.py`
  (`ProgramCatalogue.lookup`, `UnknownProgramError`).
- Skills: `logisphere-design-review` (this review), `leta`/`sem` (navigation),
  `python-router` family routing recorded in the plan.
