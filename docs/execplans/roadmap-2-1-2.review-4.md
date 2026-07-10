# Logisphere design review — roadmap-2-1-2 ExecPlan, round 4

Status: PROCEED (no blocking defects). Reviewer: adversarial Logisphere crew.

The round-4 revision resolves the single round-3 blocker (B7) and folds in
advisories A5 and A6. Every load-bearing claim has been re-verified against
source (the cuprum read-only checkout, the corpus oracle, the schema, the
runner, and `pyproject.toml`). The plan is implementable and design-conformant
as written.

## B7 (the round-3 blocker) — RESOLVED, verified against source

The gate-ratio predicate now short-circuits to no `gate-ratio-consistent`
violation when `target <= 0`, mirroring the oracle exactly.

- `tests/working_corpus/_oracle.py` lines 144-145: `_check_gate_ratio_consistent`
  opens with `if spec.target_words <= 0: return True` before dividing — the guard
  the round-3 plan omitted and the round-4 plan now mirrors.
- `novel_ralph_skill/state/schema.py` line 254: `WordCounts.target` is a plain
  `int`; `__post_init__` (lines 258-260) freezes only `by_chapter`, so a
  `target == 0` or negative `State` is structurally constructible and parseable.
  An unguarded predicate would raise `ZeroDivisionError`.
- The round-4 plan makes `validate_state` **total**: every predicate returns
  `Violation | None` for every constructible `State`, the WI3
  `coherent_states`/`one_perturbation` strategies draw `target >= 1`, and a
  targeted example pins the `target == 0` and negative-`target` verdicts directly.
  The guard is propagated consistently across Interfaces, Constraints, the new
  Risk, WI1's gate pin, WI3's strategy/implementation note, the
  Validation/acceptance observable, and Decision Log B7. Consistent and correct.

## Advisories folded in — verified

- **A5 (float threshold-tie parity):** WI3's `coherent_states` strategy now
  derives each gate boolean with the identical `ratio >= threshold` comparison
  (not `>`) the validator and oracle use (`_oracle.py` line 150:
  `flag == (ratio >= threshold)`). A boundary-tie state cannot self-falsify.
  Pinned in WI3 and Decision Log A5.
- **A6 (cwd isolation):** WI2 records that the new behavioural module is the only
  place the real `novel-state` callable is driven, always under explicit
  `monkeypatch.chdir(dest)`, and confirms the narrowed still-stubbed entry-point
  tests are not perturbed by a stray `working/` at the pytest invocation root.
  Adequate.

## Prior-round resolutions re-verified against source

- **B1 (drafted-total gate numerator) — holds.** `_specs.py::derive_by_chapter`
  (lines 228-240) keys `by_chapter` to each chapter's `draft_words` whenever
  `by_chapter_override` is unset (no variant sets it), so the validator's
  `sum(by_chapter.values()) / target` equals the oracle's drafted ratio on every
  tree. The `by-chapter-sum-mismatch` variant (`_variants.py` line 99) forces
  `current_words_override=1` while leaving the drafts and gate booleans honest,
  so the validator names exactly `{by-chapter-sum}`. The
  `gate-true-below-threshold`
  variant (`_variants.py::_gate_true_below_threshold`) keeps `current` honest and
  forces `done_80` true on a `0.15` ratio, so the validator names exactly
  `{gate-ratio-consistent}`. Both decoupling cases hold.
- **Consecutive-clean proxy — holds and is genuinely pure-state.**
  `ChapterEntry` (`schema.py` lines 74-92) carries only
  `number`/`slug`/`title`/`target_words` — **no** `draft_words` — so the drafted
  count is genuinely a disk quantity and cannot be computed from a parsed
  `State`. The manifest-length proxy
  (`len(state.chapters)`) is the correct pure-state approximation. On the lone
  divergent variant `consecutive-clean-over-chapters-drafted` (`_variants.py`
  lines 110-118: a single chapter, `consecutive_clean=2`), oracle (`drafted=1`)
  and proxy (`len(chapters)=1`) both reject `2`. They agree; the divergence the
  plan flags (planned-but-undrafted chapters) is correctly deferred to 2.1.3.
- **B2/B3/B5/B6 — hold.** `RunContext` (runner.py lines 89-104) carries
  `command`/`working_dir`/`human`; `_emit` (lines 107-126) builds the envelope
  from `context.working_dir` and selects `render_human` from `context.human`;
  `run` (lines 160-188) stamps the envelope on the usage (exit 2) and state-error
  (exit 3) body-less paths and exits 0 with no envelope on `--help`/`--version`.
  So the `--human` pre-parse and the fixed `working_dir="working"` stamp are
  genuinely required and correctly specified.
- **B4 — holds.** No `--working-dir` flag exists; the cwd-relative `working/`
  constant is the single source of truth.
- **cuprum e2e seam — holds.** `cuprum/sh.py`: `ExecutionContext.cwd: _CwdType`
  (lines 168-196, `_CwdType = str | Path | None` at line 53) and
  `run_sync(*, ..., context: ExecutionContext | None = None)` at line 441. The
  e2e's `run_sync(context=ExecutionContext(cwd=dest), capture=True)` is valid.
- **Library/timeout claims — pinned, not memory-based.** `pyproject.toml` line
  325 (`timeout = 30`), line 327 (`slow` marker), lines 25-26 (`pytest-timeout`,
  `pytest-xdist` declared); the 180s supersession is pinned by the existing
  `test_console_scripts_install_and_exit_two` gate, not asserted from memory.
- **Owned-name vocabulary — holds.** The six owned names match
  `CORPUS_INVARIANT_NAMES` (`_oracle.py` lines 37-58); the four deferred
  disk-evidence names are genuinely 2.3.2's.

## Atomicity / ordering / testability / completeness

- Work items are atomic and independently gate-passable: WI1 (analysis, Markdown
  gates), WI2 (skeleton + behavioural suite, violation case `xfail`ed), WI3
  (validator + Hypothesis suite, `xfail` removed; boundary tests assert verdicts
  independently of the behavioural `xfail`, so a silent empty-verdict bug is
  caught regardless), WI4 (corpus agreement + scope pin + docs).
- Validation is specified per work item (`make all`, `make audit`, Markdown gates
  on Markdown commits) and the acceptance section is behavioural and observable.
- The deterministic/judgemental boundary is respected: a §5.2 violation is exit
  `4` (actionable finding the agent adjudicates), not exit `1` or `3`; missing or
  unparseable `state.toml` is exit `3`. The validator is pure and read-only; the
  checker writes nothing (pinned by a before/after byte-comparison test).
- The checker/mutator scope split is respected: only the six pure-state
  invariants are owned; the four disk-evidence invariants are deferred to 2.3.2,
  pinned by a "deferred names never emitted" test.

## Pre-mortem

The round-3 pre-mortem failure path (a `ZeroDivisionError` flake on a
`target == 0` draw, papered over with `assume(target > 0)` while
`validate_state` still crashes
on a materialized `target == 0` state in 2.1.3) is now designed out: the validator
is total, the strategies draw `target >= 1`, and the guard's verdict is pinned by
a direct example rather than left to the property. No new most-likely failure path
surfaces.

## Strongest alternative (Wafflecat)

The plan already adopted the round-2 Wafflecat (cwd-relative `working/`) and the
round-3 framing of `validate_state` as a total function. No better structural
alternative is on the table; this is a strong signal the design is on solid
ground.

## Verdict

PROCEED. The single round-3 blocker (B7) is resolved correctly and verified
against source, advisories A5 and A6 are folded in, and all prior-round
resolutions still hold. The plan is implementable and design-conformant as
written. I would stake my name on it.

Documentation and skills relied on: `docs/novel-ralph-harness-design.md` §5.2 /
§5.4 / §2.3 / §3.1-§3.4 / §4.1; `docs/adr-003-shared-interface-contract.md` §3.1;
`docs/developers-guide.md`; `AGENTS.md`; `novel_ralph_skill/contract/runner.py`
lines 89-188; `novel_ralph_skill/state/schema.py` lines 74-92, 254-260;
`novel_ralph_skill/state/parse.py` lines 51-60; `tests/working_corpus/_oracle.py`
lines 37-150; `tests/working_corpus/_variants.py` lines 24-153;
`tests/working_corpus/_specs.py` lines 228-253; `pyproject.toml` lines 25-26,
325-327; `/data/leynos/Projects/cuprum/cuprum/sh.py` lines 53, 168-198, 441.
Skills: `logisphere-design-review`, `leta`, `python-router`, `en-gb-oxendict`.
