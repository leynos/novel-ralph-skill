# Post-merge audit — roadmap task 1.3.2

Audit of the codebase after roadmap task 1.3.2 ("Build the on-disk `working/`
fixture corpus") merged to `main` at commit `371784c`. The slice delivers the
shared [`working_corpus`](../../tests/working_corpus) package: a declarative
`WorkingTreeSpec`/`ChapterSpec` pair, a `tomlkit` tree builder, a named library
of the eleven coherent phase states, one deliberately incoherent variant per
§5.2/§5.4/§3.4 invariant, the `done.flag` permutations, and a corpus-local
structural oracle (`corpus_check`). The package is exposed by pytest fixture
name through the registered [`tests/corpus_fixtures.py`](../../tests/corpus_fixtures.py)
plugin, documented in the developers' guide, and self-tested by
[`tests/test_working_corpus.py`](../../tests/test_working_corpus.py) and
[`tests/test_working_corpus_done_flags.py`](../../tests/test_working_corpus_done_flags.py).
The slice is sound and discharges its success criterion: the corpus is built to
be consumed unchanged by phases 2-6.

This audit checks the new corpus package against the design's authoritative
artefacts and the recurring themes carried by `docs/issues/audit-1.2.1.md`
through `docs/issues/audit-1.2.11.md`. Each finding records a category, a
location, a description, a concrete proposed fix, and a severity. None is a
blocking defect; they are tidy-up and coverage opportunities.

Trail followed: explored with `leta`/`Read` over the new package and consumers,
and traced history with `git show 371784c` and `sem`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.4, §4.3, §5.1, §5.2, §5.4, and §9;
[`skill/novel-ralph/references/state-layout.md`](../../skill/novel-ralph/references/state-layout.md);
`docs/developers-guide.md`; `docs/roadmap.md`; and `AGENTS.md`. Language router:
`python-router` (Python test scaffolding, dataclasses, fixtures).

## Finding 1 — `_specs.py` module docstring describes a pre-split module

- **Category:** docs-gap
- **Severity:** medium
- **Location:**
  [`tests/working_corpus/_specs.py:1-23`](../../tests/working_corpus/_specs.py)

The `_specs.py` module docstring claims the module "declares the specification
dataclasses (`ChapterSpec`, `WorkingTreeSpec`), the `build_working_tree`
factory that materializes a `working/` tree on disk, the `compiled.md`
concatenation helper, and the named specification library consumed by the slice
suites in roadmap phases 2-6." That sentence describes the corpus *before* it
was split into sub-modules: `build_working_tree` now lives in
[`_builder.py`](../../tests/working_corpus/_builder.py), and the named
specification library (`PHASE_STATES`, `COHERENT_BASELINE`) now lives in
[`_library.py`](../../tests/working_corpus/_library.py). `_specs.py` actually
declares only the two dataclasses, the constants, and the derivation helpers
(`derive_by_chapter`, `derive_current`, `concatenate_drafts`, `draft_body`).
The whole-package summary that belongs on the docstring is already correct on
[`__init__.py:1-22`](../../tests/working_corpus/__init__.py); `_specs.py` should
describe only its own contents. A reader navigating to `_specs.py` to find the
builder is misdirected by its own docstring.

**Proposed fix:** rewrite the `_specs.py` module docstring to describe just the
specification dataclasses, the corpus constants (`CORPUS_SEPARATOR`,
`GATE_THRESHOLDS`, `COMPILED_AUTO`), and the pure derivation helpers it owns,
and drop the references to `build_working_tree` and the named library. The
"anchored to authoritative artefacts, invents no schema type" paragraph can stay
(it is module-agnostic context). `make markdownlint`/`make test` are unaffected;
this is a docstring-only change gated by `interrogate` and Ruff.

## Finding 2 — The cursor invariant is only half-modelled by the corpus and the oracle

- **Category:** test-gap
- **Severity:** medium
- **Location:**
  [`tests/working_corpus/_oracle.py:124-134`](../../tests/working_corpus/_oracle.py)
  (`_check_cursor_coherent`),
  [`tests/working_corpus/_specs.py:158-160`](../../tests/working_corpus/_specs.py)
  (`current_scene`/`current_beat` defaults),
  [`tests/working_corpus/_variants.py:127-130`](../../tests/working_corpus/_variants.py)
  (`cursor-past-current-chapter`)

Design §5.2 invariant 6 has three clauses: the cursor (a) keeps `current_chapter`
within the drafted set, (b) holds `current_scene`/`current_beat` "zero until
their plans exist", and (c) never references "a chapter past `current_chapter`".
The corpus exercises only clause (a): every coherent phase state leaves
`current_scene` and `current_beat` at their `0` default (no corpus tree ever
sets them non-zero), and the lone `cursor-past-current-chapter` variant moves
`current_chapter` only. The oracle's `_check_cursor_coherent` correspondingly
checks `0 <= current_chapter <= len(chapters)` plus non-negativity of scene and
beat, but never the "zero until plans exist" or the scene/beat-versus-cursor
relationship. Task 2.1.2's real validator must enforce all three clauses, yet
the corpus seeds no fixture that exercises a non-zero scene/beat — so a validator
that mishandled clauses (b) or (c) would pass against this corpus. This is the
one §5.2 invariant the corpus does not fully cover, and it is exactly the kind of
gap the corpus exists to close before phase 2.

**Proposed fix:** add a coherent fixture that sets a non-zero `current_scene`
and `current_beat` consistent with `current_chapter` (so the happy path is
represented), and one incoherent variant whose scene or beat references a chapter
past `current_chapter` (or is non-zero with no plan), keyed to `CURSOR_COHERENT`.
Extend `_check_cursor_coherent` to assert the scene/beat-versus-cursor
relationship so the oracle and the §5.2 text agree clause-for-clause. This keeps
the corpus's "exercise every invariant fully" guarantee honest for task 2.1.2.
`make test` over the corpus self-tests confirms isolation still holds.

## Finding 3 — Three distinct variants collapse onto one oracle invariant name, so the "every invariant exercised" self-test under-counts

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_oracle.py:94-105`](../../tests/working_corpus/_oracle.py)
  (`_check_consecutive_clean_bound`),
  [`tests/working_corpus/_variants.py:102-118`](../../tests/working_corpus/_variants.py)
  (`consecutive-clean-over-target`, `convergence-target-below-one`,
  `consecutive-clean-over-chapters-drafted`),
  [`tests/test_working_corpus.py:364-375`](../../tests/test_working_corpus.py)
  (`test_every_invariant_name_is_exercised`)

Design §5.2 invariant 4 bundles three sub-rules: `0 <= consecutive_clean <=
convergence_target`, `convergence_target >= 1`, and `consecutive_clean <=
chapters drafted`. The oracle folds all three into the single
`_check_consecutive_clean_bound` predicate returning the one name
`CONSECUTIVE_CLEAN_BOUND`, and three separate variants
(`consecutive-clean-over-target`, `convergence-target-below-one`,
`consecutive-clean-over-chapters-drafted`) each target that one name. Because
`test_every_invariant_name_is_exercised` only asserts that the *set* of targeted
names equals `CORPUS_INVARIANT_NAMES`, a single one of the three variants
satisfies the test — the other two sub-rules could silently stop being exercised
(for example if a future refactor accidentally made two variants violate the same
sub-clause) without any test failing. The corpus deliberately built three
variants here precisely because there are three sub-rules, but the self-test
cannot tell them apart.

**Proposed fix:** either (a) split the oracle predicate into three named checks
(`CONSECUTIVE_CLEAN_LE_TARGET`, `CONVERGENCE_TARGET_GE_ONE`,
`CONSECUTIVE_CLEAN_LE_DRAFTED`) so each variant maps to a distinct name and the
existing set-equality self-test guards all three; or (b) keep the single name but
add a self-test that asserts each of the three named variants is the *minimal*
mutation breaking its specific sub-clause (e.g. that raising
`convergence_target` repairs `consecutive-clean-over-target` but not
`convergence-target-below-one`). Option (a) aligns the oracle vocabulary with the
design's distinct sub-rules and is the cleaner long-term shape for task 2.1.2's
cross-check. `make test` over the corpus self-tests verifies.

## Finding 4 — The oracle re-reads `state.toml` from disk for two checks while the rest read the spec, with no single read helper

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_oracle.py:80-91`](../../tests/working_corpus/_oracle.py)
  (`_check_by_chapter_sum`),
  [`tests/working_corpus/_oracle.py:175-189`](../../tests/working_corpus/_oracle.py)
  (`_check_compiled_matches_drafts`),
  [`tests/test_working_corpus.py:31-33`](../../tests/test_working_corpus.py)
  (`_read_state`)

`corpus_check` mixes two evidence sources: eight checks read the `spec` in
memory, while `_check_by_chapter_sum` and `_check_compiled_matches_drafts` read
the materialized `working/` tree from disk. The split is documented and
deliberate (the disk checks deliberately verify the on-disk bytes task 2.1.2's
validator will see), but `_check_by_chapter_sum` open-codes its own
`tomllib.loads((working_dir / "state.toml").read_text(...))` while
`test_working_corpus.py` carries a near-identical private `_read_state` helper,
and `_check_compiled_matches_drafts` recomputes the present-draft concatenation
inline rather than reusing the `_present_draft_bodies` helper already in
[`_specs.py:208-211`](../../tests/working_corpus/_specs.py). The same
"decode `state.toml`" and "concatenate present drafts in order" idioms now live
in two or three places each, the same single-source-of-truth pattern the 1.2.x
audit series repeatedly flagged for the test scaffolding.

**Proposed fix:** add a small private `_load_state(working_dir)` helper in
`_oracle.py` (or a shared corpus reader) that both the oracle's disk check and
the self-test's `_read_state` consume, and have `_check_compiled_matches_drafts`
call the existing `_present_draft_bodies` from `_specs.py` instead of
re-deriving the ordered draft bodies. This collapses the duplicated decode and
the duplicated ordered-concatenation onto one home each. `make test` over the
corpus self-tests confirms the labels are unchanged.

## Finding 5 — The `_consistent_gates` ratio computation is duplicated between the library and the variants module

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_library.py:60-64`](../../tests/working_corpus/_library.py)
  (`_crossed_gates`),
  [`tests/working_corpus/_variants.py:24-32`](../../tests/working_corpus/_variants.py)
  (`_consistent_gates`),
  [`tests/working_corpus/_oracle.py:137-150`](../../tests/working_corpus/_oracle.py)
  (`_check_gate_ratio_consistent`)

Three functions independently compute "the knitting-gate booleans honestly
crossed by a draft total against `GATE_THRESHOLDS`". `_library._crossed_gates`
does it for the shared drafted total, `_variants._consistent_gates` does it per
chapter tuple, and `_oracle._check_gate_ratio_consistent` does it as a
validation. All three unpack `GATE_THRESHOLDS` into `low, mid, high` and compare
`ratio >=` each. The constant is shared (good), but the gate-derivation logic is
written three times; a change to how the ratio maps to the three booleans (for
example a "strictly greater than" boundary fix, or a fourth gate) would need
re-applying in three files, and a drift between the library/variant builders and
the oracle would silently produce a tree the oracle then mislabels.

**Proposed fix:** lift a single `gates_for_ratio(drafted, target)` (or
`gates_for_drafts(chapters, target)`) helper into `_specs.py` beside
`GATE_THRESHOLDS`, returning the three booleans, and have `_library`,
`_variants`, and the oracle all call it (the oracle comparing the stored gate
booleans against its return). This makes the gate-threshold mapping live exactly
once. `make test` over the corpus self-tests verifies the coherent/incoherent
split is unchanged.

## Finding 6 — `_check_by_chapter_sum`'s docstring mis-numbers the manifest-bijection check as "invariant 5"

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`tests/working_corpus/_oracle.py:108-115`](../../tests/working_corpus/_oracle.py)
  (`_check_manifest_disk_bijection`),
  [`docs/novel-ralph-harness-design.md` §5.2](../novel-ralph-harness-design.md)

The oracle docstrings annotate each check with a design invariant number
(`invariant 1` … `invariant 7`). Design §5.2 lists the invariants as bullets in
this order: phase membership (1), completed prefix (2), by-chapter sum (3),
consecutive-clean bound (4), manifest/disk bijection (5), cursor coherence (6),
gate ratio (7). The `_check_manifest_disk_bijection` docstring correctly says
"inv 5" and `_check_cursor_coherent` says "invariant 6" — these match. However
the numbering is fragile: the design bullets are unnumbered prose, so any future
re-ordering or insertion in §5.2 silently desynchronizes every "invariant N"
annotation in the oracle, and there is nothing pinning the mapping. This is a
latent docs-drift hazard rather than a present error.

**Proposed fix:** either number the §5.2 bullets in the design explicitly (so the
oracle annotations cite a stable label) or replace the numeric annotations in the
oracle docstrings with the stable `CORPUS_INVARIANT_NAMES` strings the module
already owns (e.g. "the manifest/disk bijection invariant, §5.2") so the citation
survives a design re-ordering. The named-string form is preferable because those
strings are already the cross-check contract with task 2.1.2. Docstring/prose
change only; `make markdownlint`/`interrogate` gate it.

## Notes on what was checked and found sound

- The coherent/incoherent split is genuinely isolated: each
  `INCOHERENT_VARIANTS` entry is a minimal `dc.replace` of `COHERENT_BASELINE`,
  and `test_each_variant_breaks_exactly_its_invariant` proves each breaks
  exactly its one named invariant while every coherent tree passes clean.
- The by-chapter-sum violation is a *real on-disk* violation:
  `current_words_override` writes `current` verbatim while `by_chapter` still
  derives from the drafts, and the oracle reads it back through `tomllib`, so the
  fixture exercises exactly what task 2.1.2's validator will see (not a
  corpus-internal mismatch).
- The compile check uses the design's §4.3/§9 content-hash model
  (recompute-and-compare bytes) rather than inventing a separator/heading grammar
  the design does not define — the design-review B1 concern is correctly honoured.
- `build_working_tree` carries every §5.1 schema table (`schema_version`,
  `[novel]`, `[phase]`, `[drafting]` with critic/fangirl, `[gates]`,
  `[word_counts]`, `[chapters]`, and conditional `[pending_turn]`), the
  round-trip self-test proves a `tomlkit` parse-then-dump is byte-idempotent, and
  the fixed `created_at` literal keeps later snapshot suites stable.
- The fixture-only consumption contract is honoured: `corpus_fixtures.py` is the
  single runtime importer of `working_corpus`, the self-tests name only the spec
  *types* under the sanctioned `TYPE_CHECKING` `from conftest import …`
  carve-out, and the developers' guide documents the surface and the
  consumption rule. Splitting the fixtures into a registered plugin to stay under
  the 400-line `conftest` cap is `conftest`-equivalent for fixture resolution.
