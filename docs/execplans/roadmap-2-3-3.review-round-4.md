# Design review round 4 — roadmap 2.3.3

Verdict: **Proceed** (satisfied). No blocking defects.

This is the fourth adversarial Logisphere review. The round-3 blocking point (B1,
the `baseline_tree`-cannot-supply-`spec` problem) and advisories A1/A2 are
resolved. Every load-bearing claim was re-verified against source and an
independent probe, not trusted from the planner's summary.

## Independently verified (this round)

A standalone probe built each tree with `build_working_tree` and ran both a
disk-reading reimplementation and the *current* spec-reading `corpus_check`:

- D-CLEAN test 1 (AUTO compiled + count-preserving draft edit): disk-reading
  verdict `(compiled-matches-drafts,)`; spec-reading `corpus_check` returns `()`
  after the mutation (red-first holds). Confirmed.
- D-CLEAN2 test 2 (`mkdir chapter-04`): disk-reading `(manifest-disk-bijection,)`;
  spec-reading `()` after the mutation. Confirmed.
- D-COFIRE1 (rmtree a chapter dir): disk-reading
  `(manifest-disk-bijection, word-counts-match-drafts)`; spec-reading
  `(word-counts-match-drafts,)` after the mutation — so the added name
  `manifest-disk-bijection` is the red-first signal, exactly as the plan's
  local-revert guidance states. Also verified that removing a *flagged* chapter
  yields the same two-name tuple (done-flag does not fire — the directory and its
  flag are gone), so the plan's loose "any non-zero-table chapter" choice is safe.
- D-COFIRE2 (empty a flagged draft): disk-reading
  `(done-flag-without-draft, word-counts-match-drafts)`; spec-reading
  `(word-counts-match-drafts,)` after the mutation. Confirmed.
- All four unmutated baselines return `()` under `corpus_check`. Tuple order
  matches `CORPUS_INVARIANT_NAMES` exactly.

## Cross-checks against source

- `COHERENT_BASELINE = PHASE_STATES["drafting"]`: 3 chapters 24000/24000/20800,
  `has_done_flag` on chapters 1 and 2 only, `compiled=None` (no `compiled.md`).
  All three plan assumptions confirmed (`_library.py` lines 41-118).
- Production twin (`disk_evidence.py`) reads `state.chapters` for the manifest and
  globs `manuscript/chapter-*` for disk; the reroute mirrors this exactly.
- Corpus `CORPUS_SEPARATOR` and production `DRAFT_SEPARATOR` are both `"\n\n"`,
  so the compiled agreement suite stays green.
- `baseline_tree` is `Callable[[], Path]` (Path-only), confirming D-BASELINE-SPEC;
  `build_tree`/`check_corpus` signatures and the `wc`/`dc.replace` idioms in
  `test_reconcile_derivation.py` and the class form in
  `test_working_corpus_divergent.py` are as cited.
- Gates: 400-line cap, `max-args = 4` / `max-positional-arguments = 4` in
  pylint config, and the Ruff `**/test_*.py` per-file-ignores (PLR0913/PLR0917)
  that PyPy-Pylint does not honour — all confirmed. Class-form methods stay at
  `self` + 3 fixtures.
- D-DEVGUIDE: developers-guide lines 426-434 (pure-state twins) and 336-348
  (disk-evidence, neutral) make no spec/disk asymmetry claim; only
  `disk_evidence.py` lines 29-33 do. The plan's conditional edit scope is honest.
- Roadmap 2.3.3 success criterion matches the plan's acceptance criterion verbatim.
- No `cuprum` / Cyclopts / pytest-timeout / `uv` behaviour is load-bearing: the
  oracle uses `pathlib` + `tomllib` + corpus helpers only. No external-doc
  citation required; the no-cuprum claim is correct.

## Advisory (non-blocking)

- The plan cites `test_reconcile_derivation.py` line 93 as the two-line
  `spec = wc.COHERENT_BASELINE; working = build_tree(spec, tmp_path)` idiom; the
  actual line 93 is the one-line
  `working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)`.
  Cosmetic citation imprecision only — the plan explicitly offers both forms as
  acceptable and the `dc.replace` idiom is genuinely present nearby. No action
  required.
