# Logisphere design review — roadmap-2-1-2 ExecPlan, round 3

Status: REVISE (one blocking defect). Reviewer: adversarial Logisphere crew.

The round-3 revision resolves all three round-2 blockers (B4, B5, B6) cleanly
and correctly, verified against source. The plan adopts the Wafflecat
alternative (cwd-relative `working/`, `--human`-only pre-parse) faithfully. One
blocking defect remains, newly surfaced by tightening the gate-ratio quantity to
match the oracle: the validator divides by `word_counts.target` without the
`target <= 0` guard the oracle it claims parity with carries, so the gate
predicate can raise `ZeroDivisionError` instead of returning a verdict.

## Confirmed-resolved (round-2 blockers, verified against source)

- **B4 (`--working-dir` invention) — RESOLVED.** Verified: a repository-wide
  search of `docs/novel-ralph-harness-design.md`, `docs/users-guide.md`, and
  every `docs/adr-*.md` finds no `--working-dir` flag, `--working` option, or
  per-invocation working-directory override. Design line 151 fixes
  `working_dir` to the constant `"working"` (an envelope-example field); design
  line 189 defines exit `3` as "`state.toml` missing or unparseable; working dir
  absent"; ADR-003 §3.1 (Functional requirements + Table 2) mandates only the
  `--human` flag and the `working_dir` *envelope field*. The plan now stamps the
  fixed `working_dir="working"` into the `RunContext` and reads
  `Path("working") / "state.toml"` from cwd. The `--human` pre-parse is genuinely
  required: `runner.py::run` (lines 161-188) stamps `context.working_dir` and
  `context.human` into the envelope on the `CycloptsError`→exit-`2` (lines
  163-170) and `StateInputError`→exit-`3` (lines 171-177) paths where the
  command body never runs, so the human selection cannot be recovered from the
  body's return value. Sound and design-conformant.

- **B5 (`build_app()` data flow) — RESOLVED.** With B4's fixed constant the
  `check` body resolves `./working/` itself, so the zero-arg `build_app()`
  signature is consistent: the body needs nothing per-invocation to close over.
  The envelope value and the file path are the same constant string `"working"`,
  giving a single source of truth and removing the round-2 cross-command drift
  hazard. Sound.

- **B6 (stub/e2e narrowing) — RESOLVED.** Verified against the gates:
  - `test_command_stubs.py::test_entry_point_callable_exits_two` (line 74) is
    parametrized over `ENTRY_POINTS` (built from `COMMAND_ENTRY_POINTS`), sets
    `sys.argv = [name]` with no cwd control, and asserts
    `excinfo.value.code == stub.STUB_EXIT_CODE` (2). After WI2 evolves
    `stub.py::novel_state()` (line 67) to drive `run` against `Path("working")`,
    the `novel-state` parameter raises `FileNotFoundError` →
    `StateInputError` → exit **`3`**. The plan names this exit code and narrows
    the test correctly.
  - `test_console_scripts_e2e.py::_assert_scripts_exit_two` (line 60) loops the
    installed scripts and asserts exit `2`; the installed `novel-state` with no
    `working/` now exits `3`. Narrowing to the four still-stubbed names is right.
  - The three `make_stub_app`-based tests (`test_command_result_exits_two`,
    `test_unknown_option_exits_one`, `test_meta_flags_exit_zero`, lines 37/54/64)
    build `stub.make_stub_app(name)` directly and are genuinely unaffected; the
    plan correctly states they must not be touched.
  - The new subprocess e2e: `cuprum/sh.py` confirms `ExecutionContext` carries a
    `cwd: _CwdType` field (class at line 169, field at 196; `_CwdType =
    str | Path | None` at line 53) and `run_sync(*, ..., context:
    ExecutionContext | None = None)` at line 441, so `sh.make(prog,
    catalogue=...)().run_sync(context=ExecutionContext(cwd=dest), capture=True)`
    is valid — and matches the existing e2e's `sh.make(...)().run_sync(...)`
    pattern (line 73). The 180s timeout marker is grounded: the existing e2e
    documents (lines 18-19) that it is "marked `slow` and given an explicit 180s
    per-test timeout that supersedes the 30s" default. `pyproject.toml` line 325
    confirms `timeout = 30` and line 327 the `slow` marker; `pytest-timeout` and
    `pytest-xdist` are both declared deps. The pytest-timeout-under-xdist
    supersession claim is pinned by an existing gated test, not memory.

## Prior-round resolutions re-verified

- **B1 (drafted-total gate numerator) — holds.** `_oracle.py`
  `_check_gate_ratio_consistent` (lines 143-150) computes `drafted =
  sum(chapter.draft_words)` and `ratio = drafted / spec.target_words`;
  `_specs.py::derive_by_chapter` (line 228) yields `{key: chapter.draft_words}`
  whenever `by_chapter_override` is unset (no variant sets it), so the
  validator's `sum(by_chapter.values()) / target` equals the oracle's drafted
  ratio on every tree. On `by-chapter-sum-mismatch` the validator names exactly
  `{by-chapter-sum}`. Correct.
- **B2 (entry point on `stub`) — holds.** `stub.py::novel_state` (line 67) is the
  registered callable; evolving it in place leaves `names.py`/`pyproject.toml`
  and the three registry gates untouched.
- **B3 `--human` pre-parse — holds** (see B4 above for the runner.py evidence).
- The six owned names match `CORPUS_INVARIANT_NAMES` (`_oracle.py` lines 37-55):
  `phase-in-enum`, `completed-prefix`, `by-chapter-sum`,
  `consecutive-clean-bound`, `cursor-coherent`, `gate-ratio-consistent`; the
  four deferred disk-evidence names (`manifest-disk-bijection`,
  `done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`)
  are genuinely 2.3.2's.
- A1 (assert `current_chapter >= 0`) is folded into WI1 and the cursor predicate,
  matching `_check_cursor_coherent` (line 124: `0 <= current_chapter`).
- A2 (`TypeError` in the exit-3 set) is justified: parse.py line 57 documents
  that a malformed table "surfaces as a `KeyError` or `TypeError` at
  construction"; `load_state`'s `FileNotFoundError` is an `OSError` subclass,
  also covered.

## Blocking defect (round 3)

### B7 (Doggylump / Telefono) — the gate-ratio predicate divides by `target` with no `target <= 0` guard; the oracle it claims parity with has one

The plan pins the gate-ratio predicate to `sum(by_chapter.values()) / target`
(Interfaces, Constraints, WI1 line 704, WI3 line 916) and asserts structural
agreement with the oracle's `_check_gate_ratio_consistent`. But the oracle's
first line is a guard the plan omits:

```python
def _check_gate_ratio_consistent(spec: WorkingTreeSpec) -> bool:
    if spec.target_words <= 0:
        return True
    drafted = sum(chapter.draft_words for chapter in spec.chapters)
    ratio = drafted / spec.target_words
    ...
```

(`_oracle.py` lines 144-150.) The validator spec carries no equivalent
`target <= 0` guard, and:

- `WordCounts.target` is a plain `int` with no positivity enforcement
  (`schema.py` line 254; `__post_init__` only freezes `by_chapter`), so a
  `State` with `target == 0` or negative is structurally constructible and
  parseable.
- The WI3 `coherent_states` and `one_perturbation` Hypothesis strategies (lines
  883-902) draw `target` ("`target` such that the gate booleans are set to match
  the drafted-total ratio") but never pin `target >= 1`. If the strategy's
  `target` domain admits `0`, the gate predicate raises `ZeroDivisionError`
  mid-property — a crash, not a verdict — and the property suite fails
  non-deterministically.
- `validate_state` is pinned as a stable public surface that task 2.1.3
  cross-checks against materialized on-disk states. A `target == 0` state would
  crash the validator instead of yielding a verdict, whereas the oracle returns
  "gates consistent". The two then *disagree by exception*, which is exactly the
  silent validator-vs-oracle drift the round-1 pre-mortem warned against, one
  task deeper.

On the current corpus `target` is always positive, so WI4's agreement suite will
not surface this — which is precisely why it must be fixed in the plan rather
than left for 2.1.3 to discover as a crash.

Resolution required (pick a consistent pair, and pin it in the Interfaces gate
predicate, WI1's gate pin, and the WI3 strategy):

1. Mirror the oracle's guard in the validator: the gate predicate returns "no
   `gate-ratio-consistent` violation" when `target <= 0` (matching
   `_check_gate_ratio_consistent`'s `return True`), so `validate_state` agrees
   with the oracle structurally on arbitrary states and never divides by zero;
   and
2. Constrain the `coherent_states`/`one_perturbation` strategies to draw
   `target >= 1` (or whatever range keeps the gate booleans meaningful), so the
   property suite exercises the live ratio path without tripping the guard, and
   add a targeted example pinning the `target <= 0` guard's verdict directly
   (analogous to the `convergence_target == 0` boundary case already specified).

This is a one-line addition to the pinned quantity, but the plan currently
claims oracle parity while omitting the one branch of the oracle that prevents a
crash, so it is not implementable to "structural agreement" as written.

## Advisory (non-blocking, but address)

- A5 (Buzzy Bee) — the gate predicate compares a float `ratio >= threshold`
  against gate booleans for thresholds `0.30/0.50/0.80`. The oracle does the
  same float comparison, so floating-point parity is preserved by construction
  on the corpus. But the `coherent_states` strategy "sets the gate booleans to
  match the drafted-total ratio": if the strategy ever lands `ratio` exactly on
  a threshold (e.g. `drafted/target == 0.30`), the boolean the strategy derives
  and the boolean the validator derives must use the *identical* comparison
  (`ratio >= threshold`, not `>`), or a boundary state self-falsifies. Pin that
  the strategy derives the gate booleans with the same `>=` comparison the
  validator uses, so coherent-by-construction states cannot drift on a threshold
  tie.

- A6 (Pandalump) — WI2's behavioural cases select a fixture by
  `monkeypatch.chdir(dest)` and rely on the default `./working/`. The
  `test_entry_point_callable_exits_two` narrowing (B6) leaves the four stubbed
  entry points asserting exit `2` while running in pytest's ambient cwd. Confirm
  no stray `working/` directory exists at the pytest invocation root that would
  perturb a future real entry point's exit code; the behavioural module's
  explicit `chdir` is the right isolation and should be the only place the real
  `novel-state` callable is driven.

## Pre-mortem (most likely failure path)

Six months on: a developer implements WI3 literally, draws `target` from a
strategy that includes `0` (or a perturbation strategy that zeroes `target` while
breaking another invariant), and the Hypothesis suite flakes with a
`ZeroDivisionError` from the gate predicate on roughly one shrink in N. Under
pressure they `assume(target > 0)` inside the strategy (masking the gap) rather
than guarding the validator, so `validate_state` still crashes on a `target == 0`
state. Task 2.1.3 then runs the validator against a materialized tree whose
`target` is zero and the crash resurfaces as an oracle-vs-validator divergence
two tasks deep — the same drift class the round-1 pre-mortem flagged for B1.
Prevention: resolve B7 by mirroring the oracle's `target <= 0` guard in the
validator and pinning `target >= 1` in the coherent strategy, so the validator
total-functions over every constructible `State`.

## Strongest alternative (Wafflecat)

The plan already adopted the round-2 Wafflecat (cwd-relative `working/`); no
better structural alternative is on the table. For B7 the cleanest framing is to
make `validate_state` *total*: every predicate returns a `Violation | None` for
every constructible `State` (no partial functions, no unguarded division), with
the oracle's guards mirrored exactly. This is the design's evident intent — the
validator is a pure `State -> tuple[Violation, ...]` — and a total function is
what task 2.1.3's arbitrary-state cross-check needs.

## Verdict

REVISE. B4, B5, and B6 are correctly resolved and verified against source, as
are the prior-round B1/B2/B3 resolutions. One blocking defect remains: B7, the
unguarded `target` division in the gate-ratio predicate, which breaks the plan's
own claim of structural agreement with `_check_gate_ratio_consistent` and can
crash both the property suite and the public `validate_state` surface on a
`target <= 0` state. It is a precise, one-line fix to the pinned quantity plus a
strategy constraint. With B7 resolved the plan is implementable and
design-conformant as written.

Documentation and skills relied on: `docs/novel-ralph-harness-design.md` §5.2
(line ~visible above) / line 151 / line 189; `docs/adr-003-shared-interface-
contract.md` §3.1 + Table 2; `novel_ralph_skill/contract/runner.py` lines
161-188; `novel_ralph_skill/state/parse.py` lines 51-60, 228-248;
`novel_ralph_skill/state/schema.py` line 254; `tests/working_corpus/_oracle.py`
lines 37-55, 76-150; `tests/working_corpus/_specs.py` lines 228-260;
`tests/corpus_fixtures.py` (fixture surface); `tests/test_command_stubs.py`
lines 24-88; `tests/test_console_scripts_e2e.py` lines 18-19, 60-73;
`pyproject.toml` lines 325-327; `/data/leynos/Projects/cuprum/cuprum/sh.py`
lines 53, 169-196, 441, 528. Skills: `logisphere-design-review`, `leta`,
`python-router`, `en-gb-oxendict`.
