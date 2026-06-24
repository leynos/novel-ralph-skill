# Adversarial Logisphere design review — roadmap 2.1.6 — Round 1

Verdict: PROCEED WITH CONDITIONS (two small blocking fixes; central design is
sound and empirically verified).

Reviewed against the real source in the worktree:
`tests/working_corpus/_variants.py`, `_oracle.py`, `_live_draft.py`, `_specs.py`,
`_library.py`, `tests/test_working_corpus.py`,
`tests/test_validate_state_live_draft.py`, `docs/developers-guide.md`,
`docs/roadmap.md`, `AGENTS.md`, `pyproject.toml`, `Makefile`. The under-counting
tree, the `corpus_check`/`live_draft_owned` verdicts, and the `min`-mutant
kill/survive behaviour were all executed against the live corpus under
`uv run python`.

## Empirical verification (live code)

Built the plan's under-counting spec and the existing over-counting variant and
ran the real oracle and validator:

    UNDER: live_draft_counts=(90000, 3)  corpus_check=('gate-ratio-consistent',)
           live_draft_owned={'gate-ratio-consistent'}  validator_owned=set()
           min-mutant oracle -> set()  => mutant KILLED
    OVER:  live_draft_owned={'gate-ratio-consistent','consecutive-clean-within-drafted'}
           min-mutant oracle -> unchanged  => mutant SURVIVES

The plan's central thesis holds exactly as written. D1 and D2 are true against
the code: the under-counting tree fires exactly `gate-ratio-consistent`, the
validator is silent, and the `min(live, table)` mutant survives the over-counting
tree but dies on the under-counting tree. The single-proxy asymmetry (D2) is real:
`consecutive-clean-within-drafted` cannot fire on the live side when the table
under-counts chapters.

## Blocking defects

B1. Work item 1's headline goal is false and self-contradictory. The section
title and Purpose claim the extraction "relieves the inline too-many-lines
exemption headroom", and step 4 instructs to "remove the inline
`# pylint: disable=too-many-lines` exemption ... so the cap is enforced honestly".
But `tests/test_working_corpus.py` is 599 lines; the moved block
(`_DIVERGENT_KEY` + `TestCorpusDivergentTable`, lines 540-599 = ~60 lines) plus
the two now-orphaned imports leaves the module at ~537 lines — still far over the
400 cap. The exemption CANNOT be removed. The plan's own step-4 parenthetical
admits this ("it should not be — ... still over the 400 cap"), so the section
contradicts itself: the primary stated objective is infeasible and only the
buried fallback ("keep the exemption") is achievable. Fix: rewrite Work item 1's
goal to state the truth — the extraction exists solely to give the NEW
under-counting self-test a home in a module under the cap (so the new test does
not widen an existing exemption); `test_working_corpus.py` remains over-cap and
keeps its exemption. Delete the "remove the exemption" instruction. This is the
addendum 2.1.5.1 intent correctly; the plan mis-states it.

B2. Uncited locked-library claim about the Pylint exemption mechanics. The
Constraints assert the C0302 cap is enforced by "disables `all` then re-enables
`too-many-lines`" and that `make all` "fails on any module over the cap". This is
verified true in this repo (`pyproject.toml` `max-module-lines = 400`,
`[tool.pylint."messages control"]` re-enables `too-many-lines`, and the PyPy-shim
pylint runs under `make lint`). That part is fine. However, the plan nowhere
verifies that the inline `# pylint: disable=too-many-lines` it intends to KEEP on
`test_working_corpus.py` will not itself trip any other gate after the orphaned
imports are removed (an inline disable with no remaining over-cap justification
is still valid Pylint, but `ruff` must not flag the now-unused
`validator_verdict`/`PURE_STATE_INVARIANT_NAMES` imports). The plan says to run
`ruff` to surface orphans (good) but must commit to DELETING both imports, not
merely "confirm with `leta refs` before deleting" — this review confirms lines 28
and 30 are used ONLY by the moved class (sole use at line 599), so both imports
WILL be orphaned and MUST be removed. Make that unconditional in Work item 1.

## Advisory (non-blocking)

A1. Work item 2's prose is the weakest part of the document: a ~25-line internal
monologue that argues itself into "That violates the per-commit gate" before
reversing. The final resolution (execution order 1,4,2,3,5) is correct and the
Concrete steps encode it correctly, but the section should be cut to the
conclusion. Leave the Decision Log D4 rationale; delete the dithering.

A2. `_specs.py`'s own module docstring wrongly claims it "declares ... the
`build_working_tree` factory" (that lives in `_builder.py`). Pre-existing, out of
scope, but the plan reads `_specs.py` as a reference in Work item 2 — note it so
the implementer is not misled when locating the builder.

A3. Tolerances call the `_variants.py` margin "ample": 300 + ~45 = ~345. The
existing over-counting factory docstring is ~18 lines; a symmetric under-counting
factory with an equally thorough NumPy docstring plus the mapping entry and the
module-docstring refresh (Work item 5) is realistically 50-60 lines, landing
~355-360. Still under 400, but "ample" overstates it. Keep the docstring tight.

A4. Work item 5's mutant spot-check should pin, in Outcomes, the exact
before/after oracle verdict on BOTH trees (under: `{gate-ratio}` -> `set()`
killed; over: unchanged survives), matching the transcript in Artifacts. The plan
says to confirm the under-counting failure and "would have passed on the
over-counting variant alone" — record the over-counting survival explicitly so a
later reader sees why the second tree was necessary.

## Pre-mortem (Doggylump)

Most likely six-months-later failure: a later variant is added to
`DIVERGENT_TABLE_VARIANTS` without a matching entry in Work item 4's per-variant
expected mapping. The plan mitigates this well — it requires asserting each
iterated key has an expected entry and failing loudly with the key name on a
`KeyError`. Keep that guard; it is the single most valuable defensive line in the
plan. Second scenario: someone "tidies" `test_working_corpus.py` by deleting the
kept exemption (because B1's false framing suggested it should be removable),
reintroducing a `make all` failure. Fixing B1's wording removes that landmine.

## Alternatives checkpoint (Wafflecat)

The strongest alternative is to drive the under-counting divergence through
`consecutive-clean-within-drafted` instead of `gate-ratio-consistent`. The plan
proves (D2, confirmed here) this is IMPOSSIBLE for an under-counting table — the
table chapter count is a smaller ceiling than the live count, so the live proxy
cannot fire while the validator stays silent. So the single-proxy choice is
forced, not preferred. No credible structural alternative exists; the design space
is genuinely narrow. That is a strong signal the approach is correct.

## Conformance

- Deterministic/judgemental boundary: untouched. Test-corpus, oracle data, and
  docs only; no `novel_ralph_skill/` source changes.
- Contracts: `CORPUS_INVARIANT_NAMES`, `corpus_check`, `live_draft_counts`,
  `live_draft_owned`, `PURE_STATE_INVARIANT_NAMES` all stable. New variant is a
  value under the existing `DIVERGENT_TABLE_VARIANTS` key, no new symbol.
- Category placement: correctly `DIVERGENT_TABLE_VARIANTS`, not
  `INCOHERENT_VARIANTS` and not `coherent_oracle_cases`/`PHASE_STATES`. Verified
  against the agreement-suite iteration sets.
- Cuprum: D3 is correct — this task touches no cuprum consumer; the corpus and
  oracle run in-process over `tmp_path`. No uncited cuprum claim. No other
  locked-library behaviour (Cyclopts, pytest-timeout, uv) is asserted.
- en-GB Oxford spelling, 100% interrogate, 400-line cap, fixture-by-name rule,
  tests in top-level `tests/`: all respected by the plan as written (subject to
  B1).

Fix B1 and B2 (both are wording/commitment corrections, not design changes) and
the plan is implementable and design-conformant.
