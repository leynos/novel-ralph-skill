# Logisphere design review — roadmap 2.1.7 (Round 1)

Verdict: REVISE. The bijection-split / reconcile-flag spine (D1/D2/D3) is sound
and verified against source, but the plan does not account for the
`word-counts-cover-drafts` deferral coupling, so the relaxation is wider than the
ADR and tests claim. Fix the blocking items below before implementation.

## Blocking

1. **Unanalysed coupling: the relaxation silently disables
   `word-counts-cover-drafts` over the whole drafting-subset surface.**
   `_check_word_counts_cover_drafts` (`_disk_word_counts.py` lines 128-130)
   *defers* — returns `None` — whenever `manifest != _on_disk_chapter_numbers(...)`,
   because the recount keys off the (then-untrustworthy) manifest. A relaxed
   drafting subset always satisfies `manifest != on_disk`, so once `check`
   stops firing `manifest-disk-bijection` for that tree, `word-counts-cover-drafts`
   is *structurally unreachable* for it. Empirically confirmed: the
   `manifest-extra-entry` tree (manifest `{1,2,3,4}`, table keys `{01,02,03}`,
   recount keys `{01,02,03,04}`) fires `manifest-disk-bijection` only — cover-drafts
   already defers under strict. The plan's Decision D2 asserts "the other seven
   predicates ignore it" with no analysis. The truth is that cover-drafts coverage
   detection is *lost* during a relaxed subset: a genuinely stale `by_chapter`
   key-set mid-draft can no longer be caught by `check`. This must be (a) analysed
   and stated in ADR 009 as part of what the relaxation actually changes, and
   (b) pinned by a test (assert cover-drafts is silent on a relaxed subset, and
   confirm that is the intended boundary, not an accident). Until then the plan's
   "clean exit 0 = honest drafting tree" claim is unproven and the relaxation's
   blast radius is undocumented.

2. **The positive coherent drafting-subset fixture (Work item 3, step 3) is
   asserted, not proven, to be clean on the other seven predicates.** The plan
   says "reuse `manifest_only_numbers` on the drafting `_BASE`" and assert "no
   `manifest-disk-bijection`". But a coherent subset tree must also pass
   `cursor-plan-present`, `done-flag-without-draft`, both word-count predicates,
   etc. The `manifest-extra-entry` shape passes them today only because of the
   cover-drafts deferral (blocking item 1) and because its cursor stays low. The
   plan must specify the exact fixture and assert the *full* relaxed verdict is
   empty, not merely that the bijection name is absent — otherwise the positive
   case can silently fire a different invariant and the "exit 0" acceptance
   criterion fails.

3. **The flag-threading mechanism contradicts the `_PREDICATES` constraint.**
   `_PREDICATES` is a uniform `tuple[Callable[[State, Path], Violation | None]]`
   called in a single loop (`disk_evidence.py` lines 264-300). Work item 2,
   step 2,
   says "thread a `relax_drafting_bijection` parameter down to the bijection
   predicate", and step 3 says "Keep the `_PREDICATES` assembly total and ordered"
   while calling "the bijection predicate with the flag and the remaining
   predicates unchanged". You cannot pass a per-predicate kwarg through the uniform
   loop without either (a) lifting the bijection predicate out of `_PREDICATES`
   and calling it separately (breaking the "ordered assembly" the plan also
   demands), or (b) widening every predicate's signature. The plan gestures at a
   sibling-module extraction but never commits to one concrete wiring. Pick the
   mechanism explicitly (recommended: keep bijection out of the loop, call it
   first with the flag, then concatenate the loop's verdicts in
   `DISK_EVIDENCE_INVARIANT_NAMES` order) and state how verdict order is
   preserved.

## Advisory

- **E2e recipe is incomplete.** The plan's cuprum pattern
  (`sh.make(prog, catalogue=...).run_sync(...)`) omits the subcommand-argument
  call step. The real harness is
  `sh.make(prog, catalogue=catalogue)(*extra).run_sync(...)` with
  `_REAL_PATH_ARGV["novel-state"] == ("check",)` — a bare `novel-state` prints
  help and will not exit 4/0 as asserted. The e2e must invoke
  `...(catalogue=catalogue)("check").run_sync(...)`. (Verified in
  `tests/test_console_scripts_e2e.py` lines 44, 113-119.)

- **pytest-timeout-under-xdist claim is uncited.** Work item 4 asserts
  "pytest-timeout per-test marks compose with the xdist run". The repo *does*
  configure a global `timeout = 30` (`pyproject.toml`) and an existing e2e uses
  `@pytest.mark.timeout(180)` + `@pytest.mark.slow`, so the pattern is locally
  proven — but the plan should cite that precedent (lines 326-328 and
  `test_console_scripts_e2e.py` lines 127-128) rather than assert the
  composition behaviour from memory. Reuse the existing 180s timeout value;
  do not invent a new one.

- **`reconcile` attaches via `derive_reconciliation`, not the relaxed verdict.**
  `_check` calls `derive_reconciliation(state, root)` only when `disk_evidence`
  fired (`novel_state.py` line 244). Once `check` relaxes, a clean drafting
  subset yields empty `disk_evidence`, so no reconciliation is attached — correct,
  but the plan never states it. Confirm the acceptance criteria account for the
  reconciliation payload being absent on a relaxed-clean tree (it is, and that is
  the right outcome).

## Verified sound (no action)

- cuprum 0.1.0 absolute-path allowlisting: confirmed against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` (`ProgramCatalogue.is_allowed`
  builds the allowlist from registered `Program`s; `Program(str(abs_path))` is
  registered, hence allowed). No cuprum surface change. Plan's claim is correct.
- D1 reconcile-strictness: `derive_reconciliation` reads
  `check_disk_evidence(state, working_dir)` (reconcile.py line 345) with no flag;
  the torn `set-chapters` test uses `phase_current="drafting"`
  (`test_set_chapters_reconcile.py` line 125). A default-strict flag leaves
  reconcile untouched. Correct.
- Strict agreement suite (`test_novel_state_check_disk.py` line 167-168) calls
  `check_disk_evidence(state, working)` with the default; a default-strict flag
  leaves it green. Correct.
- `_BASE`/`COHERENT_BASELINE == PHASE_STATES["drafting"]`
  (`_library.py` line 118); `manifest-extra-entry` is a drafting-phase
  manifest-only-without-directory tree (`_variants.py` line 144-146,
  `_builder.py` lines 109-116). Correct.
- The strict split (`orphans = on_disk - manifest`, `missing = manifest - on_disk`,
  contiguity) is byte-for-byte equivalent to today's
  `manifest == on_disk and contiguous` (`disk_evidence.py` lines 122-126). Correct.
- File-size cap: `disk_evidence.py` is 300 lines; the sibling-module escape hatch
  is a real precedent (`_disk_word_counts.py`, `_disk_paths.py`). Fine.

## Pre-mortem (Doggylump)

Six months on, an author reports `check` passed mid-draft on a tree whose
`by_chapter` table had drifted (a stale recount key), the author trusted it,
final-pass surfaced the drift late, and a compile produced a wrong word total.
Root cause: blocking item 1 — the relaxation silently disabled cover-drafts
coverage during drafting and nobody noticed because no test pinned the boundary.
Prevention designed in now: the test demanded in blocking item 1, plus an explicit
ADR sentence enumerating *every* invariant whose firing changes under the
relaxation (not just bijection).

## Strongest alternative (Wafflecat)

Rather than a `relax_drafting_bijection` flag on `check_disk_evidence`, compute
the strict verdict unconditionally and have the **command layer** (`_check`) drop
the `manifest-disk-bijection` violation iff phase==drafting and the only broken
direction is missing-directory. Trade-off: keeps `check_disk_evidence` a single
pure strict function (no parameter, no oracle-twin signature change, agreement
suite trivially untouched), and the relaxation lives entirely in the user-facing
command where it belongs — but it needs the verdict to carry enough structure for
the command to know the break was missing-direction-only (today the `Violation`
detail is a string, so the command would have to re-derive direction or the
predicate must expose it). The flag approach is defensible; this alternative is
worth one paragraph in the Decision Log explaining why the flag won, because it
materially reduces the oracle-twin and agreement-suite churn the plan signs up
for in Work item 3.
