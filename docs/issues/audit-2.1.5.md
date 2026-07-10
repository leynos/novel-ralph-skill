# Post-merge audit — roadmap task 2.1.5

Audit of the codebase after roadmap task 2.1.5 ("Promote a `by_chapter_override`
table-versus-draft divergence variant into the §1.3.2 shared corpus so the
whole-corpus agreement loop is discriminating") merged to `main` at commit
`361642d`. The slice promotes the one-off `divergent_table_tree` fixture the
2.1.3 fix-round-1 constructed in
[`test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
into a first-class §1.3.2 corpus category. Concretely it: adds
`DIVERGENT_TABLE_VARIANTS` (one variant, `by-chapter-override-over-counts-drafts`)
to [`_variants.py`](../../tests/working_corpus/_variants.py); re-exports it from
the [`working_corpus`](../../tests/working_corpus/__init__.py) package surface;
adds a third fixture plugin
[`corpus_divergent_fixtures.py`](../../tests/corpus_divergent_fixtures.py)
(registered through `pytest_plugins` in
[`conftest.py`](../../tests/conftest.py)) exposing the category by fixture name;
retires the module-local fixture in favour of the corpus-sourced one; adds the
`TestCorpusDivergentTable` self-tests to
[`test_working_corpus.py`](../../tests/test_working_corpus.py); and refreshes the
"Invariant validation" section of
[`developers-guide.md`](../../docs/developers-guide.md).

The slice is sound and discharges its Success clause: the divergent tree is a
first-class corpus variant, the module-local fixture is gone, the live-versus-
table discrimination is driven from corpus data through the standard fixture
loop, and the disagreement is documented as a deliberate finding (not a drift to
align away) in both `_variants.py` and the developers' guide. The documentation
was refreshed in step with the code. None of the findings below is a blocking
defect; the dominant theme is *structural duplication in the fixture-plugin
layer* — 2.1.5 added a fourth near-identical "build named tree" factory closure
and a fourth "return the variant keys" fixture without consolidating the shape —
plus two smaller test-coverage and coupling observations.

Trail followed: explored with `leta` (`leta files`, `leta show` over
`derive_by_chapter`, `by_chapter_override`, `live_draft_owned`,
`CORPUS_INVARIANT_NAMES`, `incoherent_tree`, `done_flag_tree`) and targeted
reads of the three corpus fixture plugins, `tests/working_corpus/_variants.py`,
`__init__.py`, and the two live-draft / corpus self-test suites; traced history
with `git show 361642d` and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §5.2 and §9, `docs/developers-guide.md`
"Invariant validation", `docs/execplans/roadmap-2-1-5.md`, the roadmap entry
(`docs/roadmap.md` §2.1.5), prior `docs/issues/audit-2.1.3.md` /
`audit-2.1.4.md`, and `AGENTS.md` (the 400-line module cap, lines 24-27). Skills
relied on: `leta` (navigation), `sem`/`git show` (history), and `python-router`
(reviewing the test plugin and dataclass-spec code).

Each finding records a category, location, description, proposed fix, and
severity.

## 1. Fourth near-identical "build named tree" factory closure (duplication)

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/corpus_divergent_fixtures.py`](../../tests/corpus_divergent_fixtures.py)
  `divergent_table_tree._build` (lines 77-82), against
  [`tests/corpus_fixtures.py`](../../tests/corpus_fixtures.py)
  `incoherent_tree._build` (lines 297-304) and `done_flag_tree._build`
  (lines 345-350).

2.1.5 adds `divergent_table_tree`, whose `_build` closure is the third
structurally identical instance of the same factory body: look up `name` in a
module-level mapping, `dest = tmp_path / name`, `dest.mkdir(exist_ok=True)`,
`return spec, wc.build_working_tree(spec, dest)`. The only variation across the
three is the mapping named (`INCOHERENT_VARIANTS` / `DONE_FLAG_PERMUTATIONS` /
`DIVERGENT_TABLE_VARIANTS`) and whether the tuple carries the expected-invariant
name (`incoherent_tree` returns a 3-tuple, the other two a 2-tuple). The
per-`tmp_path`-subdirectory comment in `incoherent_tree` explaining *why*
`dest = tmp_path / name` is needed is not repeated in the new closure, so the
rationale lives only beside one of the three copies.

- **Proposed fix:** extract a single private helper in `working_corpus` (e.g.
  `build_named_tree(mapping, name, tmp_path) -> (spec_entry, working_dir)`) that
  owns the subdirectory-isolation logic and its comment once, and have all three
  fixtures call it (the `incoherent_tree` one re-attaching the expected name from
  its 2-element mapping value). This collapses three closures to three one-line
  fixtures and gives the isolation rationale a single home. If a helper feels
  heavier than the duplication, at minimum copy the
  "build each variant in its own subdirectory" comment into the new closure so
  the rationale is not orphaned.

## 2. Fourth near-identical "return the variant keys" fixture (similarity)

- **Category:** similarity
- **Severity:** low
- **Location:**
  [`tests/corpus_divergent_fixtures.py`](../../tests/corpus_divergent_fixtures.py)
  `divergent_table_variant_names` (lines 40-52), against
  [`tests/corpus_fixtures.py`](../../tests/corpus_fixtures.py)
  `incoherent_variant_names` (lines 259-271) and `done_flag_permutation_names`
  (lines 309-321).

The body `return tuple(wc.<MAPPING>)` and the boilerplate docstring
("Delivering the keys by fixture lets a test iterate the … set without a runtime
value import of the `<MAPPING>` mapping") are now triplicated verbatim, one per
corpus category. Each new corpus category re-pays this boilerplate. This is the
fixture-name counterpart to finding 1.

- **Proposed fix:** when consolidating finding 1, also fold the key-tuple
  fixtures behind one small factory or parametrized fixture keyed on the mapping,
  or accept the triplication explicitly. At least cross-reference the sibling
  fixtures in the docstrings so a future reader knows the pattern is intentional
  and where its peers live, rather than discovering three independent copies.

## 3. No tomlkit round-trip self-test for the divergent tree (test-gap)

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_working_corpus.py`](../../tests/test_working_corpus.py)
  `TestBuildWorkingTree.test_round_trip_idempotent` (lines 282-295) and
  `TestCorpusDivergentTable` (lines 543-599);
  [`tests/working_corpus/_variants.py`](../../tests/working_corpus/_variants.py)
  `_divergent_table_spec` (lines 248-290).

The divergent variant is the first corpus tree to set *both*
`by_chapter_override` and `current_words_override`, so its `state.toml`
`[word_counts]` table carries values the builder writes verbatim rather than
deriving from the chapter drafts. The existing byte-idempotent
`tomlkit` round-trip self-test (`test_round_trip_idempotent`, the proof a
task-2.2.1 no-op round-trip preserves a corpus state file) runs only on the
coherent `_minimal_spec`, never on the divergent tree. `TestCorpusDivergentTable`
asserts the proxy disagreement and the category exclusion but not that the
override-bearing `state.toml` survives a `tomlkit` parse-then-dump unchanged. The
builder is shared so the risk is small, but the override path is exactly the kind
of hand-set table the round-trip guard exists to protect, and it is currently
unexercised by that guard.

- **Proposed fix:** add a small case to `TestCorpusDivergentTable` (or
  parametrize `test_round_trip_idempotent` over the divergent variant via the
  `divergent_table_tree` fixture) asserting
  `tomlkit.dumps(tomlkit.parse(text)) == text` for the divergent tree's
  `state.toml`, so the override-bearing table is covered by the same idempotency
  contract the coherent corpus enjoys.

## 4. Single-element variant set behind a parametrized factory (ergonomics)

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_variants.py`](../../tests/working_corpus/_variants.py)
  `DIVERGENT_TABLE_VARIANTS` (lines 298-300);
  [`tests/test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
  `test_live_draft_discriminates_table_from_drafts` (line 173).

`DIVERGENT_TABLE_VARIANTS` holds exactly one key, yet it is wrapped in the full
name-keyed mapping + `*_variant_names` fixture + `*_tree(name)` factory
machinery copied from the multi-variant `INCOHERENT_VARIANTS`. The single-element
nature then leaks into the consumer: `test_live_draft_discriminates_table_from_drafts`
unpacks the names tuple with `(variant_name,) = divergent_table_variant_names`,
an assertion-by-unpacking that silently couples the test to the set having
exactly one member and will raise an opaque `ValueError` (not a clear test
failure) the day a second divergent variant is added. The
`TestCorpusDivergentTable` tests instead hard-code the key as the module-level
`_DIVERGENT_KEY` constant, so the two consumers disagree on how to obtain the
name.

- **Proposed fix:** decide whether the category is genuinely a set or a single
  fixture. If a set (the mapping shape hints at growth), iterate it with a
  `for name in divergent_table_variant_names:` loop in the discrimination test
  rather than tuple-unpacking, matching how `incoherent_variant_names` is
  consumed, so a second variant extends coverage instead of breaking the unpack.
  If it is expected to stay a singleton, drop the mapping/factory indirection and
  expose one `divergent_table_tree` fixture returning the single built tree
  directly, removing the `*_variant_names` fixture. Either way, make the two
  consumers agree on one access pattern.

## 5. Draft/table totals hard-coded as magic numbers in test prose and asserts (inconsistency)

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`tests/test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
  `test_live_draft_discriminates_table_from_drafts` (line 175,
  `assert live_draft_counts(working_dir) == (8000, 2)`, and the docstring
  prose "drafts of 8000 words across two chapters against a table claiming 90000
  words across three entries");
  [`tests/working_corpus/_variants.py`](../../tests/working_corpus/_variants.py)
  `_divergent_table_spec` (lines 269-290, the source of those numbers:
  two chapters × `draft_words=4000` and `by_chapter_override` 3 × 30000 with
  `current_words_override=90000`).

The live total `(8000, 2)` and the table totals `90000`/`3` are duplicated as
literals between the spec that produces them and the test that asserts them, and
again in two docstrings (the test method's and `_divergent_table_spec`'s). The
numbers are correct today, but they are coupled by convention, not by code: a
change to `_divergent_table_spec`'s `draft_words` or `by_chapter_override` would
silently invalidate the asserted `(8000, 2)` and every prose count without any
single source of truth flagging the drift.

- **Proposed fix:** derive the expected live total in the test from the spec the
  factory already returns (`spec, working_dir = divergent_table_tree(...)`;
  `expected = (sum(c.draft_words for c in spec.chapters), sum(1 for c in
  spec.chapters if c.draft_words > 0))`) and assert against that, mirroring how
  `test_live_draft_counts_equal_honest_draft_bases` already computes its
  expectations from the spec. That keeps the discrimination assertion honest
  while removing the standalone `(8000, 2)` literal; the explanatory prose counts
  can remain as illustration.
