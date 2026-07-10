# Logisphere adversarial design review — roadmap 6.2.1 (Round 1)

Verdict: **REVISE** — the plan rests on a factual error about how three of the
five "read" commands behave across the eleven phase states. Several work items
as written cannot pass and would trip the plan's own escalation tolerances.

Reviewed against the real source: `novel_ralph_skill/commands/_compile.py`,
`_desloppify.py`, `_wordcount.py`, `novel_state.py`; `tests/corpus_fixtures.py`;
`tests/working_corpus/_library.py`; `tests/test_novel_done_snapshots.py`;
`tests/test_compile_check_snapshots.py`; `docs/novel-ralph-harness-design.md`
§2.3/§9; `docs/roadmap.md` 6.2.1; `pyproject.toml`; `AGENTS.md`.

## Blocking defects

### B1 — `novel-compile` registry argv `[]` runs the WRITE path (mutator), not the read checker

Work item 1 registers `("novel-compile", _compile.build_app, [])`. But
`_compile.build_app`'s default is `_compile(*, check=False)`: with no `--check`
flag it calls `compile_manuscript()`, which **writes `compiled.md` to disk**
and returns a write envelope (`{compiled, chapters, bytes}`). The read-only
checker (`check_compiled`, `{checked, chapters, diverged}`) is reached **only**
with argv `["--check"]`. The repo already documents this exact trap:
`tests/test_compile_check_snapshots.py` carries "Driver requirement
D-CHECK-ARGV … a `[]`-argv copy would capture the write envelope".

Consequences as written:

- The matrix mutates the corpus tree it is meant to read — contradicting the
  plan's own "no mutation / read surface" framing (Risks 4, Decision Log D3,
  Purpose).
- It snapshots the write envelope, not the checker, so the "phase-read" intent
  is not exercised.

Fix: register `("novel-compile", _compile.build_app, ["--check"])` and align
every reference (Purpose already says `novel-compile --check`; the registry
must match).

### B2 — `novel-compile --check` exits 3 on the eight pre-drafting phases; it is NOT phase-invariant

`PHASE_STATES` (`tests/working_corpus/_library.py` lines 67-104) builds the
eight pre-drafting phases (`premise`…`chapter-planning`) with an **empty
chapter manifest** (`chapters=()`). `check_compiled` calls
`_require_chapter_manifest`, which raises `StateInputError` (exit 3) on an
empty manifest. So across the eleven phases `novel-compile --check` yields:

- exit 3, `result={}` (state error) for the 8 pre-drafting phases;
- exit 0/4 with `{checked, chapters, diverged}` for `drafting`/`final-pass`/
  `done`.

This breaks Work item 4's `test_compile_and_desloppify_phase_invariant`, which
asserts the "result shape is stable across the eleven phases for a fixed
manuscript". There is no fixed manuscript — the trees differ per phase — and
the shape is demonstrably not stable. As written this assertion cannot pass and
would hit the "3 attempts → escalate" tolerance. The plan never reconciles the
pre-drafting empty-manifest reality with its phase-invariance claim.

Fix: either (a) restrict the compile/desloppify cells to the manifest-bearing
phases and document the pre-drafting exit-3 cells as a carried gap with a
semantic assertion that those phases route to exit 3; or (b) assert two
distinct branches explicitly (empty-manifest → exit 3; populated → checker),
citing design §10 / the `_require_chapter_manifest` contract. Pick one and pin
it.

### B3 — `desloppify` and `wordcount` cross-phase behaviour is asserted, not verified

Work item 4 asserts `desloppify` is phase-invariant and that `wordcount`'s gate
report is "the zero-progress branch the design implies" for pre-drafting
phases, but the plan never establishes what these commands actually return over
an **empty manifest**:

- `desloppify`'s `_select_chapters` over `state.chapters == ()` selects no
  chapters; the resulting `result` shape (zero findings vs a different shape)
  is unverified.
- `wordcount` recounts over an empty manifest; the report shape for zero
  chapters is unverified. The plan even flags this ("if the design does not pin
  it, stop per the Ambiguity tolerance") — which is an admission that the cell
  is currently unspecified, i.e. the plan is not implementable as written for
  these cells until the expected value is pinned from the design.

Fix: verify the actual envelope each command emits over the empty-manifest
pre-drafting trees and pin the expected branch from a cited design clause
before implementation, or scope these commands to manifest-bearing phases with
the pre-drafting cells documented as carried gaps.

## Advisory

- A1 (Telefono): design §9 line 813 requires **slugs** normalized in snapshots,
  not only timestamps/paths. The plan's reused volatile guard checks paths,
  dates, and clock times but not slugs. `wordcount`/`desloppify` results carry
  per-chapter slugs (`chapter-NN`). The corpus uses fixed deterministic slugs
  so churn risk is low, but the plan should state explicitly why slug
  normalization is unnecessary here (deterministic corpus slugs) rather than
  omitting the design's named field silently.

- A2 (Pandalump): Work item 4's `test_check_coherent_across_phases` is sound —
  every coherent phase state has empty `violations` — but it duplicates
  `tests/test_validate_state_corpus.py` / `coherent_oracle_cases`, which
  already prove the coherent corpus passes the oracle. The matrix adds value
  only by driving `novel-state check` through the command surface (envelope),
  not the oracle. Make that distinction explicit so the cell is not redundant
  coverage the Risks section warns against (Risk 3).

- A3 (Wafflecat): the "deliberately failing placeholder" in Work item 1 (a bare
  failing assert) will make `make all` red, so Work item 1 cannot be committed
  on its own under the "every work item gate-passes" rule (Plan of work, line
  296). Either drop the standalone red commit (fold Work item 1 into Work item
  2 so the first commit is green) or use `@pytest.mark.xfail(strict=True)` so
  the suite is green while the scaffold is proven. The plan's parenthetical
  "(xfail(strict=True) removed, or a bare failing assertion)" actively
  prescribes the option that breaks the commit gate.

- A4 (Buzzy Bee): the matrix is 5 commands × 11 phases × 2 modes ≈ 110 cells,
  each rebuilding a `working/` tree under `tmp_path`. Under the global
  `timeout=30` and xdist this is fine, but the 600-line / 6-file tolerance is
  tight once the `.ambr` is excluded and four semantic-assertion tests plus the
  drive helper and registry are counted. Confirm the budget against a dry line
  count before committing, or the tolerance trips mid-task.

- A5 (Dinolump): the plan claims "No external syrupy-parametrization research is
  load-bearing; the repo itself pins the behaviour" — this is correctly
  verified against `tests/test_contract_envelope_snapshots.py`. No firecrawl
  needed for syrupy/xdist/timeout: the in-process matrix carries no `@timeout`
  override and runs per-test under the existing `timeout=30`, which `make test`
  already applies under `-n`. This claim holds.

## Pre-mortem

It is six months on. The matrix merged. The incident: a refactor renamed the
compile write-path result key, and **no matrix cell caught it** because the
"compile" cells were silently snapshotting the exit-3 state-error envelope
(empty result) for 8 of 11 phases and the write envelope (B1) for the rest — so
the checker contract the task was meant to pin was never actually exercised
across the phase axis. The missed signal: the plan asserted phase-invariance
(B2) instead of verifying the real per-phase envelope, so the snapshots encoded
the wrong contract and looked green. Prevention, designable now: fix B1/B2 so
the compile cells drive `--check` and assert the empty-manifest vs populated
branches explicitly.

## Strongest alternative (Wafflecat)

Rather than one matrix module asserting a single "phase-invariant" branch for
compile/desloppify, split the read surface by phase-sensitivity: `novel-done`
and `wordcount` are genuinely phase/word-sensitive and earn the full
eleven-phase cross-product; `novel-compile --check` and `desloppify` are
manifest-sensitive, so their meaningful axis is {empty-manifest → exit 3,
populated → checker/scan}, not eleven phases. This collapses the false
"eleven-phase invariant" cells into the two branches that actually exist,
removes the contradiction in B2, and still documents the phase cross-product as
a carried gap (which design §9 explicitly sanctions). Trade-off: two assertion
styles instead of one uniform matrix, but it asserts what the commands actually
do.
