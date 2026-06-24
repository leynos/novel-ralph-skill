# Adversarial Logisphere design review — roadmap 2.1.6 — Round 3

Verdict: PROCEED (no blocking defects; central design re-verified against live
code; both prior-round blocking defects are resolved in the current text).

Reviewed against the real source in the worktree:
`tests/working_corpus/_variants.py`, `_oracle.py`, `_live_draft.py`, `_library.py`,
`_specs.py`, `corpus_divergent_fixtures.py`, `tests/test_working_corpus.py`,
`tests/test_validate_state_live_draft.py`, `tests/test_validate_state_corpus.py`,
`docs/developers-guide.md`, `docs/roadmap.md`, `pyproject.toml`, `Makefile`,
`AGENTS.md`. The under-counting spec, both oracle verdicts, the validator's owned
verdict, and the `min`-mutant kill/survive behaviour were executed against the live
corpus under `uv run python` during this review.

## Empirical verification (live code, this review)

Built the plan's exact under-counting spec (three chapters `draft_words=30000`/
`target_words=30000`, novel target 80000 inherited from the baseline,
`by_chapter_override={"01":4000,"02":4000}`, `current_words_override=8000`, all
gates `False`, `consecutive_clean=2`, `convergence_target=3`,
`current_chapter=3`) and the existing over-counting variant, then ran the real
oracle, validator, and a `min(live, table)` mutant:

    UNDER: spec.target_words=80000  live_draft_counts=(90000, 3)
           corpus_check=('gate-ratio-consistent',)
           live_draft_owned={'gate-ratio-consistent'}
           table read=(8000, 2)  min(live, table)=(8000, 2)  => mutant KILLED
    OVER:  live=(8000, 2)  table=(90000, 3)  min=(8000, 2)
           corpus_check=('consecutive-clean-within-drafted', 'gate-ratio-consistent')
           live_draft_owned={'consecutive-clean-within-drafted','gate-ratio-consistent'}
           min(live, table) == live  => verdict unchanged => mutant SURVIVES

The plan's central thesis (D1, D2) holds exactly. Key confirmation: the oracle's
`_check_gate_ratio_consistent` divides `sum(spec.chapters.draft_words)` by
`spec.target_words` — the **novel** target (80000), not per-chapter targets — so
the under-counting tree's live ratio is 1.125, every gate should be `True`, and
forcing all three `False` makes `gate-ratio-consistent` fire on the live side
while the table-reading validator (0.10 ratio) stays silent.
`consecutive-clean-within-drafted` cannot fire on the live side under an
under-counting table (D2's asymmetry, real and forced). The `min`-mutant returns
the table read on the under-counting tree and collapses the owned verdict to empty
(killed) but returns the live read on the over-counting tree (survives) — exactly
the reason the second tree exists.

## Verified structural claims

- Line counts as stated: `test_working_corpus.py` 599, `_variants.py` 300,
  `corpus_divergent_fixtures.py` 84, `test_validate_state_live_draft.py` 208.
- `validator_verdict` (line 28) and `PURE_STATE_INVARIANT_NAMES` (line 30) in
  `test_working_corpus.py` are used ONLY at line 599 inside the moved
  `TestCorpusDivergentTable` class; the moved block is `_DIVERGENT_KEY` (line 540)
  plus the class (543-599), ~60 lines. After removal the module is ~537 lines,
  still over the 400 cap, so the inline `# pylint: disable=too-many-lines` (line
  17) must stay. B2 (unconditional delete) and D5 arithmetic confirmed.
- `divergent_table_variant_names` returns `tuple(wc.DIVERGENT_TABLE_VARIANTS)`;
  the new key is exposed with no fixture change.
- `test_live_draft_discriminates_table_from_drafts` line 173 hard-codes
  `(variant_name,) = divergent_table_variant_names` and asserts over-counting
  `(8000, 2)` (line 175) and
  `{GATE_RATIO_CONSISTENT, CONSECUTIVE_CLEAN_WITHIN_DRAFTED}` (line 178) —
  matching Work item 4's per-variant expected mapping.
- The corpus and live-draft agreement suites iterate only `coherent_oracle_cases`
  and `incoherent_variant_names`; the new `DIVERGENT_TABLE_VARIANTS` key never
  reaches them.
- `_live_draft.py` lines 171-172 carry the "A future `by_chapter_override`
  variant" framing Work item 5 de-futures; developers-guide line 350 names
  `DIVERGENT_TABLE_VARIANTS["by-chapter-override-over-counts-drafts"]`.
- Roadmap 2.1.6 (line 551) and addenda 2.1.5.1/.2/.3 (lines 529/537/544) exist;
  the success criteria (lines 570-573) match what the plan delivers.
- `make all = build check-fmt lint typecheck test`; `markdownlint`/`nixie`/`test`
  targets present; `max-module-lines=400`; `interrogate fail-under=100`.

## Resolution of prior-round blocking defects

- Round-1 B1 (false "remove the exemption" framing): resolved. Work item 1 step
  4 and Decision Log D5 state plainly the exemption stays.
- Round-1 B2 (conditional orphaned-import deletion): resolved. Work item 1 step
  3 deletes both imports unconditionally.
- Round-2 B1-residual (Work item 1 header "relieves the exemption"): resolved. The
  only "relieve" usages in the document now read "does NOT relieve, lift, or
  remove the inline `too-many-lines` exemption" (line 479) and "(not to relieve
  the existing exemption)" (line 1000). No header or plan-of-work sentence
  reintroduces the false framing. The pre-mortem landmine ("someone deletes the
  kept exemption") is closed.

No blocking defect remains.

## Advisory (non-blocking, carried from rounds 1-2)

A1. Work item 2 (lines ~595-624) still contains the ~25-line internal monologue
that argues into "That violates the per-commit gate" before the "Therefore this
plan reorders" reversal. It is a clarity defect only: the Concrete steps (lines
806-868), the Progress list, and the Revision note all state the correct 1,4,2,3,5
execution order unambiguously, so an implementer following the steps is not
misled. Cutting the monologue to its conclusion would still improve the document.
Not blocking.

A2. `_specs.py`'s module docstring wrongly attributes the `build_working_tree`
factory to itself; it lives in `_builder.py` (verified: `__init__.py` imports it
from `._builder`). Pre-existing, out of scope; noted so the implementer locates
the builder correctly when reading `_specs.py` as a Work item 2 reference.

A3. `_variants.py` margin: 300 + a symmetric ~45-60-line factory lands ~345-360,
under 400 but not "ample". Keep the under-counting docstring tight (the
over-counting factory's docstring is ~18 lines; match that).

A4. Work item 5 / Outcomes should pin the exact before/after mutant verdict on
BOTH trees (under: `{gate-ratio}` -> `set()` killed; over: unchanged, survives),
matching the Artifacts transcript, so a later reader sees why the second tree was
necessary.

## Pre-mortem (Doggylump)

Most likely six-months-later failure: a later `DIVERGENT_TABLE_VARIANTS` member
added without a Work item 4 expected-mapping entry. The plan's loud-`KeyError`
guard (assert each iterated key has an expected entry, fail with the key name) is
the single most valuable defensive line; keep it. The round-1/2 "someone deletes
the kept exemption" scenario is now closed by the B1-residual fix.

## Alternatives checkpoint (Wafflecat)

Re-confirmed: driving the under-counting divergence through
`consecutive-clean-within-drafted` instead of `gate-ratio-consistent` is
IMPOSSIBLE for an under-counting table (the table chapter count is a smaller
ceiling than the live count, so the live proxy cannot fire while the validator
stays silent). The single-proxy choice is forced, not preferred. No credible
structural alternative exists; the design space is genuinely narrow — a strong
signal the approach is correct.

## Conformance

- Deterministic/judgemental boundary: untouched. Test-corpus, oracle data, and
  docs only; no `novel_ralph_skill/` source change.
- Contracts: `CORPUS_INVARIANT_NAMES`, `corpus_check`, `live_draft_counts`,
  `live_draft_owned`, `PURE_STATE_INVARIANT_NAMES` all stable; the new variant is
  a value under the existing `DIVERGENT_TABLE_VARIANTS` key, no new symbol.
- Category placement: correctly `DIVERGENT_TABLE_VARIANTS`, not
  `INCOHERENT_VARIANTS` and not `coherent_oracle_cases`/`PHASE_STATES` (verified
  against the agreement-suite iteration sets).
- Cuprum (D3): correct. `grep -rl cuprum tests/` returns exactly the five files
  D3 names (`conftest.py`, `test_conftest_helpers.py`,
  `test_console_scripts_e2e.py`,
  `test_novel_state_check.py`, `test_venv_scripts_dir.py`), none of which this task
  edits. The corpus and oracle run in-process over `tmp_path`. No uncited cuprum
  claim; no Cyclopts/pytest-timeout/uv behaviour asserted; nothing requires
  firecrawl.
- en-GB Oxford spelling, 100% interrogate, 400-line cap, fixture-by-name rule,
  tests in top-level `tests/`: all respected.

Every load-bearing technical claim is verified true against live code. The plan
is implementable and design-conformant as written.

Docs/skills relied on: `docs/roadmap.md`, `docs/developers-guide.md` ("Invariant
validation"), `docs/execplans/roadmap-2-1-5.md` (Decision Logs D1/D3/D5,
Tolerances), `AGENTS.md`, `pyproject.toml`, `Makefile`; the read-only cuprum
sibling checkout at `/data/leynos/Projects/cuprum`; the `logisphere-design-review`
skill.
