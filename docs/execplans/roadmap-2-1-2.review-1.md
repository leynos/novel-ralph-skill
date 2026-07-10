# Logisphere design review — roadmap-2-1-2 ExecPlan, round 1

Status: REVISE (blocking defects below). Reviewer: adversarial Logisphere crew.

The plan is well-written and largely design-conformant in intent, but three
load-bearing claims are falsified against the real corpus oracle, the
console-script registry gates, and the contract scaffolding. Each fails as
written.

## Blocking defects

### B1 (Telefono / Pandalump) — gate-ratio quantity disagrees with the oracle on `by-chapter-sum-mismatch`

The plan pins `gate-ratio-consistent` to `word_counts.current / word_counts.target`
(Decision Log; Risk 2). The corpus oracle's `_check_gate_ratio_consistent`
(`tests/working_corpus/_oracle.py`) computes the ratio from the **honest drafted
total** `sum(chapter.draft_words)`, not from `current`.

The WI4 agreement suite parametrizes over `incoherent_variant_names`, which
includes `by-chapter-sum-mismatch`. That variant sets `current_words_override=1`
while drafts (68800 words) and `target` (80000) are unchanged, and keeps the
baseline gate booleans (all True):

- Validator (`current/target` = 1/80000 ≈ 0): all three gate booleans are now
  inconsistent → validator verdict includes BOTH `by-chapter-sum` AND
  `gate-ratio-consistent`.
- Oracle (`drafted/target` = 68800/80000 = 0.86): gates consistent → oracle
  verdict is `{by-chapter-sum}` only.

Restricted to the six owned names (both names are owned), the two verdicts
differ → WI4 "incoherent agreement, restricted to owned invariants" assertion
**fails**. The plan's claim that `current/target` "isolates invariant 7 from
invariant 3" is backwards: corrupting `current` (invariant 3) also trips the
validator's gate check, so the two are coupled in exactly the variant that is
supposed to break only invariant 3. The "drafted == current on every coherent
corpus tree" reasoning is true only for coherent trees; the agreement suite also
exercises this incoherent variant.

Resolution required: either compute the validator's gate ratio from a quantity
that equals the oracle's drafted total on the corpus (and pin which `State`
field that is — note `State` carries no separate drafted total, only `current`
and `by_chapter`), or have WI4 restrict/parametrize so the coupled variant is
adjudicated explicitly, with the design-versus-oracle nuance resolved (not
papered over). This is the Tolerances' "oracle disagreement → escalate" trigger,
and the plan currently asserts equality that will not hold.

### B2 (Pandalump / Doggylump) — rewiring the `novel-state` entry point breaks three registry gate tests the plan does not enumerate

WI2 proposes a separate module `novel_ralph_skill/commands/novel_state.py` with
a `novel_state()` entry point, and points the console-script there. But the
console-script target is governed by `novel_ralph_skill/commands/names.py`, whose
`project_scripts_table()` hardcodes a single `STUB_MODULE =
"novel_ralph_skill.commands.stub"` for **all five** entries. Three gates pin this:

- `tests/test_pyproject_scripts.py::test_project_scripts_table_lists_the_five_commands`
- `tests/test_command_names_registry.py::test_registry_matches_project_scripts`
- `tests/test_command_names_registry.py::test_entry_points_resolve_to_callables`
  (asserts every entry-point function resolves to a callable **on the `stub`
  module**).

Pointing `novel-state` at a new module fails all three unless `names.py` is
restructured to per-entry module targets. The plan never lists `names.py` or
these gates; its Tolerances escalate if "a public API beyond the new validator
module and the `novel-state` command body must change", and its file budget is
≤7 files. As written, WI2 either silently breaks these gates or trips its own
escalation. The only non-escalating path is to keep the real app inside
`stub.py`'s `novel_state()` (so the registry/pyproject stay valid) — which
contradicts the plan's "separate module" interface design. Pick one and make the
gate impact explicit.

### B3 (Telefono / Dinolump) — `--human` / `--working-dir` parsing is undefined and the plan defers to a convention that does not exist

ADR-003 §3.1 and design §3.1 mandate a `--human` switch and a `working_dir` in
every envelope. `run` (`contract/runner.py`) stamps `human` and `working_dir`
into `RunContext` **before** any envelope is emitted, including the exit-2 usage
and exit-3 state-error paths where the command body never executes. But `run`
only receives the body's return value — it cannot observe flags the Cyclopts app
parsed. No existing command resolves `--human`/`--working-dir` from argv: the
only callers are test harnesses (`test_contract_runner.py::_run`) that construct
`RunContext(... working_dir="working", human=human)` directly.

The plan acknowledges this ("if the existing scaffolding does not yet provide a
canonical `--human`/`--working-dir` parse, WI2 reads the tests ... and escalates
if none exists"). None exists. So by the plan's own rule WI2 escalates, meaning
the plan is not executable past WI2 without a design decision on how the global
`--human` flag and working-directory selection are parsed and threaded into
`run` ahead of envelope emission. This decision must be made in the plan, not
deferred, because it is the first command to exercise the real `run` path and it
sets the convention all four later commands inherit.

## Advisory (non-blocking, but address)

- A1 (Pandalump) — `consecutive_clean` "chapters drafted" proxy. The plan pins
  the ceiling to `len(state.chapters)` (manifest length); the oracle's
  `_check_consecutive_clean_bound` uses `drafted = sum(1 for c if c.draft_words
  > 0)` (count of non-empty drafts). These agree on every current corpus variant
  (the single divergent variant has one chapter, drafted), so WI4 passes, but the
  two proxies are **semantically different** and the design §5.2 text says
  "chapters drafted" (a disk quantity). Record the proxy explicitly as a
  deliberate pure-state approximation and note where it could diverge from the
  design intent, so task 2.1.3's on-disk cross-check (which runs the validator
  against the materialized tree) does not later surface a silent disagreement.

- A2 (Pandalump) — `cursor-coherent` boundary. The oracle uses `0 <=
  current_chapter <= len(spec.chapters)`; the plan mirrors this with
  `current_chapter <= len(state.chapters)`. Confirm `len(state.chapters)`
  (manifest entries) equals `len(spec.chapters)` (on-disk chapters) for every
  corpus tree — they coincide only when no `manifest_only_numbers` /
  `in_manifest=False` chapter is present. The two bijection variants
  (`manifest-extra-entry`, `draft-without-manifest-entry`) make manifest and
  on-disk counts diverge; verify the cursor check still agrees there (those
  variants do not perturb the cursor, so it should, but pin it in WI1).

- A3 (Telefono) — design §5.2 "cursor-coherent" wording is "never reference a
  chapter past `current_chapter`" and "scene/beat are zero until plans exist".
  The plan correctly defers the "zero until plans exist" sub-clause to task
  2.1.4/2.3.2, but the design text bounds scene/beat against `current_chapter`,
  whereas the plan bounds `current_chapter` against the manifest length and only
  checks scene/beat non-negativity. This matches the oracle, but the plan's WI1
  should record that it follows the oracle's structural reading over the design's
  literal scene-vs-`current_chapter` clause, and that 2.1.4 owns the rest.

- A4 (Doggylump) — WI2's `xfail` commit. The plan commits WI2 with the violation
  case `xfail`ed, then removes the marker in WI3. If WI3's `validate_state`
  accidentally returns empty for a genuine violation, the `xfail` removal is the
  only thing catching it; ensure the WI3 boundary tests are independent of the
  behavioural `xfail` so a silent pass cannot slip through.

## Confirmed-correct claims (the planner did this verification well)

- The cuprum claim is accurate: `cuprum` 0.1.0 is an executable allowlist
  (`DEFAULT_CATALOGUE`/`ProgramCatalogue`, verified in
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`), not exercised by a command
  that shells out to nothing. Correctly cited, correctly out of scope.
- Exit-code mapping (violation → 4, state fault → 3) matches `runner.py`,
  `exit_codes.py`, ADR-003, and design §3.2/§5.4.
- The envelope field set the behavioural suite asserts
  (`command/schema_version/ok/working_dir/result/messages`) matches
  `contract/envelope.py`.
- The scope split (2.1.2 pure-state, 2.3.2 disk-evidence) matches roadmap.md and
  design §5.4; the four deferred names are genuinely 2.3.2's.
- Hypothesis (not CrossHair/mutmut) is the right adversary per design §2.3 and
  the locked `uv.lock`; the filtering-trap mitigation is sound.
- The `by-chapter-sum` quantity (`sum(by_chapter) == current`) matches the
  oracle's on-disk `_check_by_chapter_sum`.

## Pre-mortem (most likely failure path)

Six months on, the most likely incident: WI4 lands "green" because a later editor
"fixed" the failing `by-chapter-sum-mismatch` agreement assertion (B1) by
loosening the restricted-set comparison — exactly the Tolerance the plan warns
against — so the validator silently over-reports `gate-ratio-consistent` whenever
`current` drifts. Task 2.1.3 then cross-checks against the materialized
`state.toml` and the divergence resurfaces as a "validator vs oracle" drift bug
that is now two tasks deep. Prevention: resolve B1 in the plan by pinning the gate
quantity to agree with the oracle, and keep WI4's equality strict.

## Strongest alternative (Wafflecat)

Rather than a separate `commands/novel_state.py` module plus registry rewiring
(B2's hazard), evolve `stub.py::novel_state()` in place into the real app and
leave `names.py`/`pyproject.toml`/the three registry gates untouched. This trades
the cleaner per-command module boundary for zero registry churn and no
escalation, and isolates the change to one existing function plus the new
`state/validate.py`. It also makes the e2e narrowing in
`test_console_scripts_e2e.py` the only stub-suite edit. Worth weighing against the
plan's module-per-command instinct.
