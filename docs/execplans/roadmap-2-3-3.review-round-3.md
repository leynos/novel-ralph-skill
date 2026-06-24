# Logisphere design review — roadmap 2.3.3 ExecPlan, round 3

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-24. Verdict: **Proceed with conditions** — one blocking
specification defect, otherwise implementable and design-conformant.

All load-bearing factual claims were re-verified independently against source
(`tests/working_corpus/_oracle.py`, `_library.py`, `_specs.py`, `_variants.py`,
`corpus_fixtures.py`, `novel_ralph_skill/state/disk_evidence.py`) and by
re-running the planning probe. Every probe-measured tuple matched:

- T2 post-build `mkdir chapter-04` on `COHERENT_BASELINE`: disk-reroute verdict
  `(manifest-disk-bijection,)`, spec-reading `corpus_check` `()` after mutation
  (red-first holds). Confirms D-CLEAN2 / S2.
- COFIRE1 `rmtree chapter-03`: `(manifest-disk-bijection, word-counts-match-drafts)`.
- COFIRE2 empty flagged draft: `(done-flag-without-draft, word-counts-match-drafts)`.
- T1 count-preserving compiled edit: `(compiled-matches-drafts,)`, spec `()`.
- Co-fire red-first: spec-reading `corpus_check` returns
  `(word-counts-match-drafts,)` after both co-fire mutations — so the
  local-revert guidance (revert the *bijection*/*done-flag* predicate, never
  `word-counts-match-drafts`) is correct.
- S1: all 22 `INCOHERENT_VARIANTS` stay singletons/empty under the disk reroute;
  `manifest-extra-entry`, `draft-without-manifest-entry`,
  `compiled-not-concatenation-of-drafts`, `done-flag-empty-draft` each fire
  exactly their declared invariant. Work item 1 keeps the agreement suites green.

Design-boundary and contract checks all pass: ADR-001 deterministic/judgemental
boundary untouched (test-only filesystem reads); deliberate-twin policy honoured
(no import of `disk_evidence`); roadmap success criterion mapped faithfully;
`max-args=4` PyPy-Pylint gate over `tests` confirmed (the bundle-fixtures
guidance is necessary and correct); `_oracle.py` is 366 lines, the reroute is
net-neutral, cap respected; D-DEVGUIDE correctly leaves dev-guide lines 426-434
unedited and makes 336-348 a conditional no-edit.

## Blocking

B1 (Telefono / Pandalump). Work item 2 prescribes the `baseline_tree` fixture
for test 2 and both co-fire tests, but `baseline_tree` returns **only** `Path`
(`corpus_fixtures.py` line 207, `Callable[[], Path]`). Each test must assert
`corpus_check(spec, working) == ()` on the unmutated tree, which requires the
`spec`. The plan never names how these three tests obtain `COHERENT_BASELINE`
as the spec; no existing `baseline_tree` consumer calls `corpus_check`, so there
is no idiom to copy. A novice following the plan literally is stuck at the
baseline assertion. Fix: state explicitly that these tests build via the
sanctioned value import — `spec = wc.COHERENT_BASELINE; working =
build_tree(spec, tmp_path)` (both are public exports of `working_corpus`) — and
drop the `baseline_tree` prescription for the tests that need the spec, or add a
spec-returning factory fixture. (`baseline_tree` remains usable only where the
spec is not needed.)

## Advisory

A1 (Pandalump). Scope Tolerance self-contradiction: the parenthetical enumerates
five file targets (oracle, new test module, `disk_evidence.py` comment, optional
dev-guide sentence, roadmap checkbox) but the trigger fires at "more than 4
files." Editing all five — the literal happy path if the optional dev-guide edit
is made — trips the plan's own escalation. D-DEVGUIDE makes the dev-guide edit
conditional (likely no-edit), keeping it at four, but the wording should be
reconciled (raise the cap to 5, or restate the count to exclude the conditional
dev-guide edit).

A2 (Dinolump). Test argument-count headroom: the tests sit near the
`max-args=4` ceiling once `tmp_path` plus fixtures are counted (and `self` if
class form is used, mirroring `test_working_corpus_divergent.py`). The plan
flags bundling but does not pin the test form. State whether the new module uses
the class form (as the sibling carve-out does) and confirm each test's fixture
list is <= the ceiling, so the implementer does not discover a PyPy-Pylint
failure late.

A3 (Doggylump). Pre-mortem residual: the only realistic late failure is the
implementer wiring the baseline tests against `baseline_tree` and silently
reconstructing `COHERENT_BASELINE` by hand (drift risk) rather than importing it.
B1's fix removes this trap. No other day-two failure surfaced; the change has no
runtime, no migration, no external process, and `tmp_path` auto-cleanup.

## Alternatives checkpoint (Wafflecat)

The strongest alternative — have the oracle import and delegate to the
production `check_disk_evidence` for the three predicates — is correctly and
explicitly rejected by the deliberate-twin policy (dev-guide 426-434): it would
collapse the cross-check the agreement suites exist to provide. No credible
alternative improves on the proposed reroute; the design is on solid ground.
