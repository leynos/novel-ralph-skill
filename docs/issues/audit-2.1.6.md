# Post-merge audit — roadmap task 2.1.6

Audit of the codebase after roadmap task 2.1.6 ("Add a symmetric under-counting
divergent-table corpus variant so the §1.3.2 working corpus exercises both
directions of table divergence") merged to `main` at commit `dbe115a`. The slice
adds a second member to `DIVERGENT_TABLE_VARIANTS` — `_under_counting_table_spec`,
keyed `by-chapter-override-under-counts-drafts` — mirroring the over-counting tree
2.1.5 promoted; switches
[`test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
from a single-variant unpack to a per-variant iteration driven by a new
`_DIVERGENT_EXPECTATIONS` table; extracts the divergent-table self-tests out of
[`test_working_corpus.py`](../../tests/test_working_corpus.py) into a focused
sibling
[`test_working_corpus_divergent.py`](../../tests/test_working_corpus_divergent.py);
and refreshes the "Invariant validation" section of
[`developers-guide.md`](../../docs/developers-guide.md).

The slice is sound and discharges its Success clause. It also incidentally
discharges three 2.1.5 addenda: the consumer test now iterates rather than
hard-unpacking `(variant_name,) = divergent_table_variant_names` (addendum
2.1.5.3); the divergent self-tests live in a focused sibling under the line cap
(addendum 2.1.5.1); and the live-draft docstring no longer frames the second
variant as a "future" landmine (addendum 2.1.5.2). The new mutant-killing rationale
(the under-counting tree kills a `min(live, table)`-style mutant of
`live_draft_counts`) is documented thoroughly across the spec docstring, the
consumer test docstring, and the developers' guide, and the documentation was
refreshed in step with the code.

None of the findings below is a blocking defect. The dominant theme is *structural
duplication in the corpus spec-builder layer* — the two divergent-table spec
factories share a near-identical uniform-chapter comprehension and `_with_chapters`
call shape, and the live-draft oracle re-parses `state.toml` three times per
verdict. The pre-existing fixture-plugin-closure duplication is already tracked
as roadmap item 7.7.1 and is not re-litigated here.

Trail followed: explored with `leta`/targeted reads over
`tests/working_corpus/_variants.py`, `_specs.py`, `_library.py`, `_live_draft.py`,
`__init__.py`, `tests/corpus_divergent_fixtures.py`,
`tests/test_working_corpus_divergent.py`, and
`tests/test_validate_state_live_draft.py`; traced history with `git show dbe115a`
and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §5.2 and §9, `docs/developers-guide.md`
("Invariant validation"), `docs/roadmap.md` §2.1.5, §2.1.6, and §7.7.1, prior
`docs/issues/audit-2.1.5.md`, and `AGENTS.md` (the 400-line module cap, lines
24-27). Skills relied on: `python-router` (reviewing the dataclass-spec builder
and test plugin code), `leta` (navigation), and `sem`/`git show` (history).

Each finding records a category, location, description, proposed fix, and severity.

## 1. The two divergent-table spec factories duplicate the chapter comprehension and builder call

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_variants.py`](../../tests/working_corpus/_variants.py)
  `_over_counting_table_spec` (lines 255-297) and `_under_counting_table_spec`
  (lines 300-352).

The two factories are structurally identical: each builds a uniform-chapter
`tuple(ChapterSpec(number=index + 1, slug=f"chapter-{index + 1:02d}",
title=f"Chapter {index + 1}", target_words=…, draft_words=…, has_done_flag=False)
for index in range(N))` and then calls `_with_chapters(chapters,
consecutive_clean=…, convergence_target=3, current_chapter=…,
by_chapter_override=…, current_words_override=…, done_30=…, done_50=…, done_80=…)`.
They differ only in `range(2)` vs `range(3)`, the `target_words`/`draft_words`
literals, the override mapping, and the three gate booleans. The same
uniform-chapter comprehension also appears a third time in
[`_library.py`](../../tests/working_corpus/_library.py) `_drafted_chapters`
(lines 47-57), so the idiom is now repeated three times across the corpus package.

**Proposed fix:** extract a `_uniform_chapters(count: int, *, target_words: int,
draft_words: int, has_done_flag: bool = False) -> tuple[ChapterSpec, ...]` helper
in `_variants.py` (or, if `_library.py` is to share it, in `_specs.py` beside
`ChapterSpec`). Each divergent factory then reads
`_uniform_chapters(2, target_words=40000, draft_words=4000)` and the body collapses
to the single distinguishing `_with_chapters(...)` call. This keeps the two
factories as the explicit, separately-documented mirror pair the mutant-kill
rationale needs while removing the boilerplate that obscures their one real
difference.

## 2. The live-draft oracle re-parses `state.toml` three times per verdict

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_live_draft.py`](../../tests/working_corpus/_live_draft.py)
  `_check_by_chapter_sum_live` (line 105), `_check_gate_ratio_live` (line 121),
  and `_check_consecutive_clean_live` (line 148).

Each of the three `_check_*_live` helpers independently re-runs
`tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))`. A single
`live_draft_owned` call therefore parses the same `state.toml` three times (plus
again inside `corpus_check`). The verbatim
`tomllib.loads(... .read_text(encoding="utf-8"))` idiom is repeated four times in
the module, and `tests/_state_corpus_support.py` already owns a `load_state`
helper, so the package has a parse routine it is not reusing.

**Proposed fix:** add a private `_load_state_toml(working_dir: Path) -> dict`
helper in `_live_draft.py` that performs the read-and-parse once, and have
`live_draft_owned` parse the state a single time and pass the parsed mapping down
to the three predicates (changing their signatures from `working_dir` to the parsed
`state` plus the live counts). This removes the triple parse and the four-fold
idiom while keeping the module self-contained (it need not import the production
`load_state`). It is a pure refactor with no behavioural change.

## 3. `_with_chapters`' honest-gate default fights divergent-table specs

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_variants.py`](../../tests/working_corpus/_variants.py)
  `_with_chapters` (lines 54-64) and `_consistent_gates` (lines 43-51), against
  `_under_counting_table_spec` (lines 300-352).

`_with_chapters` computes *honest* knitting gates from the drafts via
`_consistent_gates` and merges caller `changes` on top. For an honest variant this
is convenient, but for a divergent-table tree it actively works against the author:
the under-counting spec's live 1.125 ratio makes `_consistent_gates` return
all-`True`, the exact opposite of the all-`False` gates the divergence needs, so
the factory must pass `done_30=False, done_50=False, done_80=False` explicitly
(and the docstring spends a paragraph — lines 312-316 — explaining why). The
over-counting
spec hits the symmetric trap and must pass all-`True` explicitly. The honest-gate
default is silently overridden in exactly the cases where gate divergence is the
point, so the builder's helpfulness is a footgun the docstrings must defuse by
hand.

**Proposed fix:** give the spec authors a clearer seam — for example a sibling
`_with_chapters_explicit_gates(chapters, *, done_30, done_50, done_80, **changes)`
that skips `_consistent_gates` entirely, or accept a
`gates: Mapping[str, bool] | None` parameter on `_with_chapters` where a
non-`None` value bypasses the honest
default. Either makes "these gates are deliberately set against the live ratio"
explicit at the call site and lets the docstring shrink to the one-line statement
of intent. This is an ergonomic cleanup of the spec-builder API, not a correctness
fix.

## 4. The divergent variant-key strings are duplicated as constants across three modules

- **Category:** duplication
- **Severity:** low
- **Location:** the dict keys in
  [`_variants.py`](../../tests/working_corpus/_variants.py) (lines 366-367), the
  `_OVER_COUNTING_KEY`/`_UNDER_COUNTING_KEY` constants in
  [`test_working_corpus_divergent.py`](../../tests/test_working_corpus_divergent.py)
  (lines 36-37), and the `_DIVERGENT_EXPECTATIONS` keys in
  [`test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
  (lines 94, 98).

The two variant-key string literals (`by-chapter-override-over-counts-drafts`,
`by-chapter-override-under-counts-drafts`) are restated as constants or dict keys
in three modules. A rename of a key in `_variants.py` silently desynchronizes the
two test modules — the consumer test would skip the renamed variant (its
`assert variant_name in _DIVERGENT_EXPECTATIONS` guard would now *catch* it, which
is the saving grace), but the self-test's literals would simply stop matching.

This duplication matches the established house style: `INCOHERENT_VARIANTS` and
`DONE_FLAG_PERMUTATIONS` keys are likewise referenced as bare string literals
across the corpus suites (for example `incoherent_tree("by-chapter-sum-mismatch")`
in `test_validate_state_corpus.py` and the `"none-flagged"`/`"all-flagged"` keys
in `test_working_corpus_done_flags.py`). So this is not a new inconsistency — it
is the corpus convention. It is recorded here only because the divergent
category's
verdict facts are *asymmetric* (one tree fires both proxies, the other only one),
which raises the cost of a silent desync above the symmetric categories.

**Proposed fix:** none strictly required given the convention and the consumer
test's announce-or-fail guard. If consolidation is wanted later, the cleanest seam
is a small `DivergentTableVariant` `StrEnum` (or two module-level constants in
`_variants.py`) re-exported through the package surface and named by the test
modules under the existing `TYPE_CHECKING`-guarded `from conftest import …`
carve-out — but only if roadmap item 7.7.1's broader corpus-key consolidation is
revisited, since fixing it for the divergent category alone would itself be an
inconsistency against the other categories.

## 5. No live-side test pins the over-counting tree's single-proxy boundary symmetry

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_working_corpus_divergent.py`](../../tests/test_working_corpus_divergent.py)
  `test_under_counting_table_breaks_only_gate_ratio` (lines 89-107) and
  `test_divergent_table_breaks_both_proxies` (lines 56-72).

The under-counting tree's distinguishing property — that
`consecutive-clean-within-drafted` *cannot* fire on the live side because the
under-counted table ceiling is smaller than the live count (Decision Log D2) — is
asserted only indirectly, by the exact verdict tuple `("gate-ratio-consistent",)`.
That assertion would still pass for a different reason (for example if
`consecutive_clean` happened to be set low for an unrelated cause), so the test
pins the *outcome* but not the *mechanism*. The mutant-kill claim that motivates
the whole variant — that a `min(live, table)` mutant collapses
`{gate-ratio-consistent}` to empty — is exercised only implicitly by
`test_live_draft_discriminates_table_from_drafts`, which reads the live counts but
does not itself simulate the mutant.

**Proposed fix:** this is well within acceptable coverage — the discrimination test
plus the exact-verdict self-tests do pin the behaviour, and a mutation-testing run
(roadmap's verification phases) is the proper place to confirm the `min(live,
table)` mutant actually dies. No code change is required. The note is recorded so
a future verification pass knows the under-counting tree is the intended assassin
for that mutant class and should confirm the kill rather than assume it.

## Pre-existing items not re-litigated

The fixture-plugin "build named tree" closure duplication
([`corpus_divergent_fixtures.py`](../../tests/corpus_divergent_fixtures.py)
`divergent_table_tree._build`, lines 77-82, mirroring the `corpus_fixtures.py`
closures) and the cap-driven plugin proliferation are already captured by **roadmap
item 7.7.1** (sourced from audit:2.1.5). 2.1.6 added no new fixture-plugin closure,
so that item stands unchanged; finding 1 above concerns the *spec-builder* layer
(the `_*_counting_table_spec` factories), which 7.7.1 does not cover.
