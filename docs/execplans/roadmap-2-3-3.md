# Make the corpus oracle read disk for the §5.4 structural invariants

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (revised after design review round 3)

## Purpose / big picture

This is roadmap task 2.3.3 (`docs/roadmap.md` lines 660-677, step 2.3). Design
§5.4 (`docs/novel-ralph-harness-design.md` lines 484-519) makes the on-disk
`working/` tree **authoritative**: `state.toml` merely *describes* disk, and the
disk-aware `novel-state check` / `novel-state reconcile` (task 2.3.2) detect
where state has drifted from disk. The production §5.4 detector
`novel_ralph_skill.state.check_disk_evidence`
(`novel_ralph_skill/state/disk_evidence.py`) already reads the materialized
`working/` directory for all six disk-evidence invariants.

The corpus oracle `corpus_check` (`tests/working_corpus/_oracle.py`) is the
**deliberate twin** of that production detector: an independent cross-check that
proves the corpus's coherent/incoherent split and is pinned to agree with
production on every corpus tree (developers' guide §"Invariant validation",
`docs/developers-guide.md` lines 426-434). But three of the oracle's
disk-evidence predicates still read the `WorkingTreeSpec` rather than the
materialized tree, an asymmetry already flagged in
`novel_ralph_skill/state/disk_evidence.py` lines 29-33 ("Twin asymmetry
(ExecPlan advisory A1)"):

1. `_check_manifest_disk_bijection(spec)` reads `spec.chapters` /
   `spec.manifest_only_numbers` — the production twin globs
   `manuscript/chapter-*` directories and reads `state.chapters`.
2. `_check_done_flag_without_draft(spec)` keys on
   `spec.has_done_flag and spec.draft_words == 0` — the production twin reads
   each chapter's on-disk `done.flag` existence and the `draft.md` token count.
3. `_check_compiled_matches_drafts(spec, working_dir)` reads `compiled.md` from
   disk but recomputes the expected concatenation from `spec.chapters`'
   `draft_words` (`draft_body(chapter.draft_words)`) — the production twin reads
   the present `draft.md` bodies from disk.

Because the builder materializes the spec faithfully, the existing
spec-versus-disk asymmetry is invisible on the corpus today: the agreement
suites still hold. The roadmap's point is that this masks a real gap. The §5.4
consumers (`check` / `reconcile`) must catch a tree whose `state.toml` (and the
spec that built it) **agrees with itself** but whose disk evidence **diverges**:
a chapter directory removed or added on disk after the manifest was written, a
`done.flag` planted beside a draft someone emptied on disk, a `compiled.md` left
stale against a draft edited on disk. A spec-reading oracle is blind to all
three because it never looks at disk. Generalizing the move already made for the
by-chapter-sum check after fix-round-1 (`docs/execplans/roadmap-1-3-2.md`
Decision Log "fix round 1", lines 630-654; the oracle's `_check_by_chapter_sum`
now reads the materialized `state.toml`), this task reroutes the three
predicates above to read `working_dir`.

After this change a contributor can observe:

- The oracle's manifest-bijection, done-flag/draft, and compiled checks read the
  materialized `working_dir` (they take `working_dir` and glob/read disk, never
  `spec.chapters` for the disk facts).
- A new corpus self-test builds a tree whose spec is internally coherent and
  whose `state.toml` claims agree with the spec, then mutates the materialized
  disk so that disk diverges, and asserts `corpus_check` flags the matching
  disk-evidence invariant **from disk alone** — while the unmutated tree stays
  coherent. Two mutation styles are used and **each asserts the exact, verified
  `corpus_check` tuple** (in `CORPUS_INVARIANT_NAMES` vocabulary order), never a
  vague "singleton":
  - **Clean-singleton mutations** that break exactly one disk-evidence invariant
    without disturbing the `[word_counts]` table (a count-preserving draft edit
    for compiled; a **post-build** on-disk `mkdir chapter-NN` of a directory
    absent from the manifest, which the manifest-keyed word-count read never
    visits). These assert a one-name tuple, and — crucially — each is a genuine
    post-build disk-only divergence the spec-reading oracle misses (it returns
    `()`), so the red-first guarantee holds for the clean singletons too.
  - **Co-firing structural mutations** (remove a chapter directory; empty a
    drafted chapter's `draft.md`) that the design intends to disturb the
    per-chapter word-count table too. These assert the exact **two-name** tuple
    `(manifest-disk-bijection, word-counts-match-drafts)` and
    `(done-flag-without-draft, word-counts-match-drafts)` respectively — each
    co-fire verified against a concrete built-and-mutated tree and recorded as a
    Decision (D-COFIRE1, D-COFIRE2), not papered over.
- `make all` stays green: the production-versus-oracle agreement suites
  (`tests/test_novel_state_check_disk.py::test_union_detector_agrees_with_corpus_oracle`,
  `tests/test_disk_evidence.py::test_word_counts_twin_equals_corpus_oracle`,
  `tests/test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`)
  remain green because both sides now read disk for these three invariants —
  the twins become genuinely disk-vs-disk.

### What this task does NOT do

- It changes **no production code behaviour** and **no design document**. The
  roadmap entry is explicit: "Test/corpus-only; no design change." The
  production §5.4 detector already reads disk; only the test-side oracle is
  realigned. The one production-adjacent edit permitted is updating the stale
  "Twin asymmetry" comment in `novel_ralph_skill/state/disk_evidence.py` lines
  29-33 once the asymmetry is removed, and a parallel sentence in the
  developers' guide §"Invariant validation" — both are documentation of the
  twin relationship, not behaviour.
- It adds, removes, or renames **no** invariant name. The oracle's
  `CORPUS_INVARIANT_NAMES` vocabulary
  (`tests/working_corpus/_oracle.py` lines 65-80) and the production
  `DISK_EVIDENCE_INVARIANT_NAMES` (`disk_evidence.py` lines 69-76) are
  unchanged; only *how* three predicates compute their verdict changes.
- It does not touch any of the other eleven oracle predicates, the
  `_specs.py` dataclasses, the builder, the variant library, or any fixture.
  The three rerouted predicates keep their exact signatures' **verdict** on
  every existing corpus tree (the builder materializes the spec faithfully, so
  reading disk yields the same boolean); the new self-test is the only place a
  spec/disk divergence is constructed.
- It invokes **no external process**, so it depends on **no `cuprum` API**.
  Design §9 (`docs/novel-ralph-harness-design.md` line 711): "v1 commands shell
  out to nothing, so the suite touches only the filesystem under `tmp_path`."
  The oracle reads files with `pathlib` and `tomllib` only. `cuprum` 0.1.0 is
  used elsewhere in `tests/conftest.py` (the `single_program_catalogue` /
  `venv_scripts_dir` console-scripts e2e fixtures, lines 29-54, 234+), but this
  task neither touches nor needs it — verified by grepping `cuprum` against
  `tests/working_corpus/`, `tests/test_working_corpus*.py`,
  `tests/test_disk_evidence.py`, and `tests/test_novel_state_check_disk.py` (no
  hit). Stated explicitly so the implementer does not reach for a catalogue this
  task has no use for. No locked external library's documented behaviour
  (Cyclopts flag handling, pytest-timeout, `uv run` resolution) is load-bearing
  here, so no `firecrawl` research is required: an oracle predicate reads the
  filesystem and compares values; it exercises no library surface beyond the
  standard library and `tomllib`.

## Orientation for a newcomer

This repository's working tree and this file are the only available context.
Key facts:

- The package is `novel_ralph_skill` (`pyproject.toml`,
  `requires-python = ">=3.14"`). Tests live only under the top-level `tests/`
  tree (AGENTS.md lines 145-147).
- The corpus is the `tests/working_corpus/` package. Its public surface is
  re-exported from `tests/working_corpus/__init__.py`. `corpus_check`, the
  oracle entry point, lives in `tests/working_corpus/_oracle.py`. The
  specification dataclasses (`ChapterSpec`, `WorkingTreeSpec`) and the builder
  (`build_working_tree`) live in `_specs.py` / `_builder.py`. The incoherent
  variants are in `_variants.py`.
- The corpus is consumed **only by pytest fixture parameter name** — never by a
  runtime value import in a test module — except for the sanctioned
  `import working_corpus as wc` value import the existing corpus suites already
  use (`tests/test_disk_evidence.py` line 27; developers' guide §"Shared test
  scaffolding"). The fixtures live in the registered plugin
  `tests/corpus_fixtures.py` (`pytest_plugins = ("corpus_fixtures",)` in
  `conftest`). Relevant existing fixtures: `build_tree` (line 63, returns
  `build_working_tree`: a `(spec, dest) -> Path` builder), `check_corpus`
  (line 356, returns `corpus_check`), `baseline_tree` (line 207, a `() -> Path`
  factory that builds `COHERENT_BASELINE` but returns **only the `Path`**, not
  the spec — so it cannot be used where the spec is needed; see D-BASELINE-SPEC),
  `make_working_tree_spec` (line 51, returns the `WorkingTreeSpec` *constructor*,
  not a baseline spec), `coherent_oracle_cases`, `incoherent_tree`,
  `incoherent_variant_names`. The spec *type* is named in test annotations only
  via `from conftest import WorkingTreeSpec` under `if TYPE_CHECKING:` (the
  developers-guide carve-out).
- The §5.4 production detector
  `novel_ralph_skill.state.check_disk_evidence` reads disk for **all six**
  disk-evidence invariants. Its predicates are the deliberate twins of the
  oracle's same-named predicates. The two are pinned to agree on every corpus
  tree by:
  - `tests/test_novel_state_check_disk.py::test_union_detector_agrees_with_corpus_oracle`
    (the union of `validate_state` and `check_disk_evidence` equals
    `corpus_check` on every coherent tree and every incoherent variant);
  - `tests/test_disk_evidence.py::test_word_counts_twin_equals_corpus_oracle`
    (the word-count twin specifically);
  - `tests/test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`
    (the pure-state validator restricted to its owned names).
  These are the safety nets the reroute must keep green.
- Quality gates are Makefile targets (AGENTS.md lines 71-98): `make all` runs
  `build check-fmt lint typecheck test`. `make lint` enforces 100% docstring
  coverage via `interrogate` and runs Ruff plus PyPy-Pylint (which does **not**
  honour the `**/test_*.py` per-file-ignores, so a self-test that exceeds the
  argument-count ceiling must bundle fixtures, as the corpus suites already do).
  Markdown changes additionally need `make markdownlint` and `make nixie`. Run
  gates **sequentially**, never in parallel, to benefit from build caching.
- No single code file exceeds 400 lines (AGENTS.md lines 24-27).
  `tests/test_working_corpus.py` is already 534 lines, so the divergence-proof
  self-test must **not** be added there; it goes in a focused sibling module
  (`tests/test_working_corpus_disk_divergence.py`), mirroring the existing
  `tests/test_working_corpus_divergent.py` carve-out idiom (that module's
  docstring names the same cap rationale). `_oracle.py` is 366 lines today; the
  reroute removes a little spec-reading logic and adds a little disk-reading
  logic, so a net-zero-ish delta keeps it under the cap — confirm with
  `wc -l` after editing and, if it would cross 400, stop and escalate (a
  predicate-extraction split is a Tolerance trigger, not a silent move).
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (AGENTS.md lines 18-20; `en-gb-oxendict`
  skill), except external API names.

The §5.4 disk-evidence invariants (design §5.4 lines 484-519; §5.2 lines
460-465 for the bijection) the three rerouted predicates cover:

1. **Manifest/disk bijection.** Every `[chapters]` manifest entry has exactly
   one `manuscript/chapter-NN/` directory and vice versa, contiguous from 1 with
   no gaps (design §5.2 lines 460-465). The production twin globs
   `manuscript/chapter-*` and compares with `state.chapters`
   (`disk_evidence.py` lines 84-122).
2. **`done.flag` beside an empty/absent `draft.md`.** A `done.flag` beside a
   `draft.md` whose token count is zero — or beside no `draft.md` at all — is a
   contradiction `reconcile` refuses (design §5.4 lines 512-519). The production
   twin reads `done.flag` existence and the on-disk `draft.md` token count
   (`disk_evidence.py` lines 125-153).
3. **`compiled.md` content-hash against the present drafts.** `compiled.md` is
   the ordered concatenation of the present `draft.md` bodies (design §4.3 lines
   320-344); the only fidelity check is a content comparison against a fresh
   concatenation of the **present** drafts (design §9 lines 705-711). The
   production twin reads the present `draft.md` bodies from disk and concatenates
   them (`disk_evidence.py` lines 156-188).

## Constraints

Hard invariants; violation requires escalation, not a workaround.

- Change no production code behaviour and no design document. The only
  production-tree edits permitted are documentation: the stale "Twin asymmetry"
  comment in `novel_ralph_skill/state/disk_evidence.py` lines 29-33 and the
  parallel sentence in `docs/developers-guide.md` §"Invariant validation". No
  predicate logic in `disk_evidence.py` or `validate.py` changes.
- Add, remove, or rename no invariant name. `CORPUS_INVARIANT_NAMES`,
  `DISK_EVIDENCE_INVARIANT_NAMES`, and the per-name constants stay byte-for-byte.
- The three rerouted oracle predicates must return the **same verdict** on every
  existing corpus tree as they do today (the builder materializes the spec
  faithfully, so a disk read of a faithfully-built tree yields the same boolean).
  The agreement suites
  (`test_union_detector_agrees_with_corpus_oracle`,
  `test_word_counts_twin_equals_corpus_oracle`,
  `test_incoherent_agreement_restricted_to_owned`) are the safety net and must
  stay green.
- The reroute must read disk via the same on-disk conventions the production
  twin uses: glob `manuscript/chapter-*` and parse the two-digit suffix (the
  production `_on_disk_chapter_numbers`, `disk_evidence.py` lines 84-98); read
  the manifest from the materialized `state.toml` `[chapters]` array (as the
  oracle's `_disk_by_chapter` already does, `_oracle.py` lines 251-270); read
  `draft.md` as UTF-8 and take the whitespace-split token count
  (`len(text.split())`), an absent draft counting zero. Do not invent a second
  on-disk convention.
- The oracle must remain an **independent** cross-check: it must not import
  `novel_ralph_skill.state.disk_evidence` or any production predicate (the
  deliberate-twin policy, developers' guide lines 426-434). The reroute
  duplicates the disk-reading logic; it does not call production.
- `corpus_check`'s signature `corpus_check(spec, working_dir)` is unchanged. The
  three predicates change from `(spec)` to `(working_dir)` or
  `(spec, working_dir)` as the bijection/done-flag/compiled facts move to disk,
  but `corpus_check` already passes `working_dir` to the disk-evidence checks
  (`_oracle.py` lines 361-365), so the call sites stay within `corpus_check`.
- No single code file exceeds 400 lines (AGENTS.md lines 24-27). The new
  self-test lives in `tests/test_working_corpus_disk_divergence.py`, not in the
  already-534-line `tests/test_working_corpus.py`.
- en-GB Oxford spelling in all prose, comments, docstrings, and commits
  (AGENTS.md lines 18-20).
- 100% docstring coverage (`make lint` runs `interrogate`); every new test and
  any new helper carries a docstring.

## Tolerances (exception triggers)

- Scope: the planned change touches up to **five** files — the oracle reroute
  plus the `_disk_present_draft_bodies` helper
  (`tests/working_corpus/_oracle.py`), the new four-test self-test module
  (`tests/test_working_corpus_disk_divergence.py`), the `disk_evidence.py`
  comment, the roadmap checkbox (`docs/roadmap.md`), and the **conditional**
  developers'-guide sentence (`docs/developers-guide.md`, edited only if it
  makes an asymmetry claim — D-DEVGUIDE; the likely outcome is no edit, leaving
  four files). The escalation trigger is therefore set at **more than five
  files** or ~300 net lines: if the change requires touching a **sixth** file,
  or more than ~300 net lines, stop and escalate. (The cap is set at five, not
  four, so that making the conditional dev-guide edit on the literal happy path
  does not itself trip escalation — A1.)
- Production behaviour: if making the oracle read disk appears to require any
  change to a production predicate, the typed schema, or a design document, stop
  and escalate — the roadmap states "Test/corpus-only; no design change", so a
  production-behaviour need is a roadmap-scope conflict, not something to resolve
  here.
- Agreement breakage: if rerouting a predicate to disk makes any of the three
  agreement suites fail on an **existing** corpus tree, stop and investigate
  before forcing it green — a divergence on a faithfully-built tree means the
  disk read and the spec read genuinely disagree, which is a real finding (the
  exact gap this task closes for *constructed* divergences, but a surprise on an
  *unmutated* corpus tree). Document it in `Surprises & Discoveries` and escalate
  if the resolution would change a verdict.
- File cap: if `_oracle.py` would exceed 400 lines after the reroute, stop and
  escalate — splitting the disk-evidence predicates into a sibling module is a
  structural decision, not a silent move.
- Dependencies: this task adds **no** new dependency. If any appears necessary,
  stop and escalate — the oracle is `pathlib` + `tomllib` + the corpus's own
  helpers only.
- Iterations: if a gate (`make all`) still fails after 3 fix attempts on one
  work item, stop and escalate.
- Ambiguity: if the roadmap, design §5.4, and the production detector appear to
  disagree on how a disk fact is read, stop and present the conflict rather than
  guessing — the production twin in `disk_evidence.py` is the reference for the
  on-disk convention.

## Risks

- Risk: rerouting `_check_compiled_matches_drafts` to read the present
  `draft.md` bodies from disk (rather than `draft_body(spec.chapters[*].draft_words)`)
  changes the verdict on the `compiled-not-concatenation-of-drafts` variant,
  whose `compiled` bytes are a literal mismatch and whose drafts are faithfully
  built. Severity: low. Likelihood: low. Mitigation: the variant's drafts are
  built faithfully, so the disk concatenation equals the spec concatenation
  byte-for-byte (the builder uses the same `draft_body` for both the draft files
  and the `AUTO` compiled file); the literal-mismatch `compiled` still differs
  from it, so the verdict is unchanged. The `test_auto_writes_concatenation` and
  `test_explicit_string_written_verbatim` self-tests
  (`tests/test_working_corpus.py` lines 298-328) already pin the byte equality;
  the agreement suites re-confirm it.
- Risk: rerouting `_check_manifest_disk_bijection` to glob `manuscript/chapter-*`
  changes the verdict on the two bijection variants
  (`manifest-extra-entry`: a `manifest_only_numbers` entry with no directory;
  `draft-without-manifest-entry`: an `in_manifest=False` chapter directory with
  no manifest entry). Severity: low. Likelihood: low. Mitigation: the production
  twin already reads these exactly this way and its
  `test_predicate_fires_on_its_variant` parametrization
  (`tests/test_disk_evidence.py` lines 90-111) passes for both variants today, so
  the disk read yields the correct verdict; the oracle reroute mirrors the
  production glob-and-parse. The union-agreement suite is the cross-check.
- Risk: the disk-reading bijection predicate must read the **manifest** from
  `state.toml` (not `spec.chapters`) to be genuinely disk-authoritative, but
  `state.toml`'s manifest is written from the spec, so a naive read still
  indirectly trusts the spec. Severity: low. Likelihood: medium. Mitigation:
  this mirrors the production twin, which reads `state.chapters` (parsed from
  `state.toml`) and globs the directories. "Disk-authoritative" here means the
  oracle reads both sides from the materialized tree (`state.toml` for the
  manifest, the directory glob for the on-disk side) and compares them — exactly
  what the production `check` does. The divergence-proof self-test confirms a
  post-build directory removal (disk diverging from the written manifest) is
  caught, which is the genuine state-vs-disk divergence the roadmap names.
- Risk: the new self-test's post-build disk mutation leaves the tree in a state
  where a *second* invariant also fires, masking the one under test, while the
  test still asserts a single name. Severity: medium. Likelihood: high (it is the
  reason the round-1 plan was rejected). Mitigation: the co-fire is **measured,
  not guessed**, and every divergence test asserts the *exact* `corpus_check`
  tuple in `CORPUS_INVARIANT_NAMES` vocabulary order (equality, never membership
  and never a loose singleton), so any extra or missing name fails loudly. The
  verified facts, obtained by building each tree with `build_working_tree` and
  running the disk-reading `corpus_check` (planning-agent probe,
  2026-06-24; see Surprises & Discoveries S1):
  - Removing a chapter directory from `COHERENT_BASELINE` (chapters
    24000/24000/20800, all non-zero) co-fires `word-counts-match-drafts`:
    `_check_word_counts_match_drafts` reads the manifest from `state.toml` (the
    entry survives the `rmtree`), reads the now-absent `draft.md` as 0 tokens via
    `_disk_by_chapter`, and compares against the table's non-zero entry, so disk
    0 ≠ table N. The verified verdict is the **two-name** tuple
    `(manifest-disk-bijection, word-counts-match-drafts)`. A non-zero table entry
    *guarantees* this co-fire, exactly as the reviewer states; the test asserts
    the two-name tuple and records it as Decision D-COFIRE1.
  - Emptying a flagged chapter's `draft.md` on disk (24000 → 0 tokens) co-fires
    `word-counts-match-drafts` for the same reason (disk 0 vs table 24000),
    alongside the targeted `done-flag-without-draft`. `COHERENT_BASELINE` carries
    no `compiled.md`, so `compiled-matches-drafts` does **not** also fire. The
    verified verdict is the two-name tuple
    `(done-flag-without-draft, word-counts-match-drafts)`; the test asserts it and
    records it as Decision D-COFIRE2.
  - A **count-preserving** edit of a chapter's `draft.md` under an `AUTO`
    `compiled.md` (replace each `word` token with a same-count different token,
    so the whitespace-split token count is unchanged) breaks `compiled.md`'s byte
    equality without disturbing the word-count table. The verified verdict is the
    clean one-name tuple `(compiled-matches-drafts,)` (probe-confirmed).
  - A **post-build** `mkdir` of a `manuscript/chapter-NN/` directory absent from
    the manifest, carrying no `draft.md`, stays a clean `(manifest-disk-bijection,)`
    singleton on `COHERENT_BASELINE` (3-chapter manifest 1/2/3; `mkdir chapter-04`).
    The added directory is not in `state.toml`'s `[chapters]`, so the
    manifest-keyed `_disk_by_chapter` never reads it and `word-counts-match-drafts`
    stays silent; the done-flag loop iterates only manifest chapters, so
    `done-flag-without-draft` stays silent; `COHERENT_BASELINE` writes no
    `compiled.md`, so `compiled-matches-drafts` stays silent. Crucially the spec
    is unchanged and coherent across the mutation, so the **spec-reading** oracle
    returns `()` and the disk-reading oracle returns `(manifest-disk-bijection,)`
    — a genuine state-agrees/disk-diverges singleton, exactly the roadmap
    criterion (probe-confirmed; see S2 and D-CLEAN2). This replaces the round-2
    plan's `manifest-extra-entry` reuse, whose spec already declared a
    non-bijective manifest (`manifest_only_numbers=(4,)`), so the spec-reading
    oracle already fired `manifest-disk-bijection` and the test proved nothing
    about disk reading (round-2 blocking point 1).
- Risk: the oracle file crosses the 400-line cap. Severity: low. Likelihood:
  low. Mitigation: the reroute is roughly net-neutral in lines (spec logic out,
  disk logic in); `wc -l` is checked after editing, and a crossing is a
  Tolerance trigger, not a silent split.

## Progress

- [x] Work item 1: reroute the three oracle predicates
  (`_check_manifest_disk_bijection`, `_check_done_flag_without_draft`,
  `_check_compiled_matches_drafts`) to read `working_dir`, keeping every
  existing corpus verdict and all three agreement suites green. Committed
  6317185; `make all` green (549 passed, 1 skipped); the three agreement
  suites pass. `wc -l _oracle.py` = 399, under the 400-line cap (see S3).
- [x] Work item 2: add the divergence-proof self-test
  (`tests/test_working_corpus_disk_divergence.py`) — four tests asserting exact,
  probe-verified `corpus_check` tuples, **each a genuine post-build disk-only
  mutation** the spec-reading oracle misses: two clean-singleton divergences
  (`(compiled-matches-drafts,)` via a count-preserving draft edit;
  `(manifest-disk-bijection,)` via a post-build `mkdir chapter-04` absent from the
  manifest) and two co-firing structural mutations
  (`(manifest-disk-bijection, word-counts-match-drafts)` after a directory
  removal; `(done-flag-without-draft, word-counts-match-drafts)` after emptying
  a flagged draft). Each pins the exact tuple in vocabulary order; co-fires recorded
  as D-COFIRE1/D-COFIRE2, the corrected bijection singleton as D-CLEAN2. The
  three spec-needing tests obtain `COHERENT_BASELINE` through the sanctioned
  `import working_corpus as wc` value import (`spec = wc.COHERENT_BASELINE;
  working = build_tree(spec, tmp_path)`), **not** the `Path`-only `baseline_tree`
  fixture, which cannot supply the `spec` the baseline assertion needs
  (D-BASELINE-SPEC). Committed f316ab9; `make all` green (553 passed). The
  Work item 2 local-revert check was run (S4): the four asserted tuples each
  match the disk-reading verdict and each differs from a spec-reading verdict
  (compiled spec `()` vs disk `(compiled-matches-drafts,)`; mkdir spec `()` vs
  disk `(manifest-disk-bijection,)`; rmtree spec `(word-counts-match-drafts,)`
  vs disk `(manifest-disk-bijection, word-counts-match-drafts)`; empty-draft
  spec `(word-counts-match-drafts,)` vs disk `(done-flag-without-draft,
  word-counts-match-drafts)`), confirming the red-first guarantee. CodeRabbit
  flagged bare asserts in the new module; brief failure messages were added.
- [x] Work item 3: update the `disk_evidence.py` "Twin asymmetry" comment, edit
  the developers' guide disk-evidence text only if it makes an asymmetry claim
  (D-DEVGUIDE), reify the roadmap checkbox, and run the markdown gates. Done:
  the `disk_evidence.py` module docstring "Twin asymmetry" paragraph and three
  twin docstrings (`_check_manifest_disk_bijection`,
  `_check_done_flag_without_draft`, the `_present_draft_bodies` cross-reference)
  were updated to say all six twins now read disk. Per D-DEVGUIDE the
  developers' guide needs **no** edit: lines 336-348 describe the disk-evidence
  invariants neutrally and lines 426-434 describe only the six pure-state §5.2
  twins; neither asserts the oracle reads spec while production reads disk (a
  grep for "asymmetr|spec.*read" found only the unrelated divergent-table line
  400). The roadmap checkbox 2.3.3 is ticked. `make all`, `make markdownlint`,
  and `make nixie` are all green.

## Surprises & discoveries

- Observation (S1): every one of the 22 existing `INCOHERENT_VARIANTS` members
  stays a **clean singleton** under the disk-reading oracle — the reroute changes
  no existing verdict. Evidence: a planning-agent probe (2026-06-24) built each
  variant with `build_working_tree` and ran a disk-reading `corpus_check`
  (disk-reading reimplementations of the three rerouted predicates mirroring
  production `disk_evidence.py`); all 22 returned exactly their declared
  one-name tuple (`done-flag-empty-draft` → `(done-flag-without-draft,)`,
  `manifest-extra-entry` and `draft-without-manifest-entry` →
  `(manifest-disk-bijection,)`, `compiled-not-concatenation-of-drafts` →
  `(compiled-matches-drafts,)`, and so on), and `COHERENT_BASELINE` plus all
  eleven phase states returned `()`. Impact: confirms Work item 1 keeps
  `test_each_variant_breaks_exactly_its_invariant` and the three agreement suites
  green, and that the co-fire problem the round-1 review raised exists **only**
  for the new divergence mutations (which now assert exact multi-name tuples),
  not for the existing corpus. The variants stay singletons because the builder
  aligns table, manifest, and drafts: `done-flag-empty-draft` writes table
  `01:0` to match its emptied draft; `manifest-extra-entry` /
  `draft-without-manifest-entry` keep the shared word-count keys consistent, and
  `_check_word_counts_match_drafts` compares only shared keys.
- Observation (S2): a **post-build** `mkdir chapter-04` on a built
  `COHERENT_BASELINE` (manifest 1/2/3, no `compiled.md`) is a clean
  `(manifest-disk-bijection,)` singleton under the disk-reading oracle and is
  **invisible** to the spec-reading oracle. Evidence: a planning-agent probe
  (2026-06-24) built `COHERENT_BASELINE` with `build_working_tree`, asserted the
  spec-reading `corpus_check` returned `()` and a disk-reading reimplementation
  (mirroring production `disk_evidence.py`) returned `()` on the unmutated tree,
  then executed `(working / "manuscript" / "chapter-04").mkdir()` and re-ran
  both. The spec-reading `corpus_check` still returned `()` (the spec is
  unchanged), while the disk-reading reimplementation returned
  `('manifest-disk-bijection',)` alone — `word-counts-match-drafts`,
  `done-flag-without-draft`, and `compiled-matches-drafts` all stayed silent.
  Impact: this is the corrected construction for clean-singleton bijection test
  2 (D-CLEAN2), replacing the round-2 `manifest-extra-entry` reuse. Unlike that
  reuse — whose spec declared `manifest_only_numbers=(4,)`, so the spec-reading
  oracle *already* fired `manifest-disk-bijection` and the test passed against
  both the pre- and post-reroute oracle — the `mkdir` mutation leaves the spec
  coherent, so the test fails red against any spec-reading bijection predicate
  and so genuinely guards the disk path (round-2 blocking point 1; pre-mortem
  Doggylump).

- Observation (S3): the reroute was **not** line-neutral as the plan
  estimated. A faithful disk read needs more lines than the spec read it
  replaces: the bijection check reads `state.toml` and globs `manuscript/`
  (via a new `_on_disk_chapter_numbers` helper), the done-flag check iterates
  manifest chapters reading `done.flag`/`draft.md`, and the compiled check
  gains `_disk_present_draft_bodies` (over a shared `_disk_drafts` read). With
  100% docstring coverage each helper carries a mandatory docstring, so the
  file first grew to 428 lines. Resolution: no structural split (the Tolerance
  trigger is a *silent* split into a sibling module, which was avoided);
  instead the disk-evidence cluster's docstrings and the spec-twin comment
  block were tightened, and `_disk_present_draft_bodies`/`_disk_by_chapter`
  were refactored onto the shared `_disk_drafts` read, bringing the file to
  399 lines — under the cap with the predicates kept cohesive in one module.
  Date/Author: 2026-06-24, implementing agent.

- Observation (S4): the Work item 2 local-revert check (a throwaway probe that
  re-ran the four mutations against spec-reading reimplementations of the three
  rerouted predicates) reproduced the planning probe's tuples exactly. The two
  clean singletons return `()` under the spec-reading oracle (red against the
  asserted one-name tuples); both co-fires return the one-name
  `(word-counts-match-drafts,)` under spec reading (red against the asserted
  two-name tuples, with the added name contributed only by the rerouted
  predicate). No measured tuple differed from the plan, so no escalation was
  needed. Date/Author: 2026-06-24, implementing agent.

## Decision log

- Decision: keep the oracle an independent disk-reading cross-check rather than
  importing the production detector. Rationale: the deliberate-twin policy
  (developers' guide lines 426-434) requires each side to carry its own copy of
  the rule so the cross-check is genuine; importing production would collapse the
  twins and defeat the agreement suites. Date/Author: 2026-06-24, planning agent.
- Decision: read the manifest for the bijection check from the materialized
  `state.toml` `[chapters]` array (as `_disk_by_chapter` already does), and the
  on-disk side from a `manuscript/chapter-*` glob, mirroring the production twin.
  Rationale: "disk-authoritative" means the oracle compares the written manifest
  against the actual directories from the materialized tree, exactly as
  production `check` does; this is what catches a post-build directory removal.
  Date/Author: 2026-06-24, planning agent.
- Decision: place the divergence-proof self-test in a new
  `tests/test_working_corpus_disk_divergence.py` rather than extending
  `tests/test_working_corpus.py` (already 534 lines). Rationale: the 400-line cap
  (AGENTS.md lines 24-27) and the established carve-out idiom
  (`tests/test_working_corpus_divergent.py`). Date/Author: 2026-06-24, planning
  agent.
- Decision (D-COFIRE1): the directory-removal divergence test asserts the exact
  two-name tuple `(manifest-disk-bijection, word-counts-match-drafts)`, not a
  `manifest-disk-bijection` singleton. Rationale: removing a chapter directory
  from a tree whose `[word_counts].by_chapter` entry for that chapter is non-zero
  unavoidably co-fires `word-counts-match-drafts` (disk 0 vs table N), as the
  round-1 review established and the planning probe confirmed (S1). The co-fire
  is the *correct* behaviour — disk genuinely diverges on two axes — so the plan
  records it rather than contorting the tree to suppress it. Asserting the exact
  tuple keeps the test discriminating (a third name would fail). Date/Author:
  2026-06-24, planning agent (resolving review round-1 blocking points 1 and 3).
- Decision (D-COFIRE2): the empty-draft-beside-`done.flag` divergence test
  asserts the exact two-name tuple
  `(done-flag-without-draft, word-counts-match-drafts)`. Rationale: emptying a
  flagged chapter's `draft.md` (non-zero → 0 tokens) co-fires
  `word-counts-match-drafts` (disk 0 vs table N) with the targeted
  `done-flag-without-draft`, verified against a concrete tree. `COHERENT_BASELINE`
  has no `compiled.md`, so `compiled-matches-drafts` is correctly absent and the
  tuple is exactly two names. Date/Author: 2026-06-24, planning agent (resolving
  review round-1 blocking point 2).
- Decision (D-CLEAN): the suite also includes two **clean-singleton** divergence
  tests — a count-preserving draft edit under an `AUTO` `compiled.md` asserting
  `(compiled-matches-drafts,)`, and a post-build `mkdir chapter-04` asserting
  `(manifest-disk-bijection,)` (D-CLEAN2) — so each rerouted invariant is proven
  catchable from disk *in isolation* as well as in its co-firing form. The
  count-preserving edit (replace each `word` token with a same-count different
  token) is required to keep the compiled case a clean singleton; a
  non-count-preserving edit would co-fire `word-counts-match-drafts`
  (probe-confirmed). Date/Author: 2026-06-24, planning agent (resolving review
  round-1 advisory "case 3 count-preserving edit").
- Decision (D-CLEAN2): the clean-singleton bijection test
  (`test_manifest_bijection_caught_from_disk_after_extra_directory`) builds
  `COHERENT_BASELINE` and, **after the build**, executes
  `(working / "manuscript" / "chapter-04").mkdir()` — an on-disk directory absent
  from the 3-entry manifest and carrying no `draft.md` — then asserts the verdict
  is exactly `(manifest-disk-bijection,)`. Rationale: the round-2 plan reused the
  `manifest-extra-entry` variant (`_variants.py` lines 135-138,
  `manifest_only_numbers=(4,)`), whose **spec** already declares a non-bijective
  manifest, so the spec-reading oracle already returns `('manifest-disk-bijection',)`
  for it and the asserted equality passes identically against the spec-reading
  *and* the disk-reading oracle — proving nothing about disk reading, violating
  the red-first guarantee, and missing the roadmap's "state agrees, disk diverges"
  criterion (round-2 blocking point 1). The post-build `mkdir` leaves the spec
  coherent and unchanged across the mutation: the spec-reading oracle returns
  `()` (probe-confirmed, S2), so the test is red against any spec-reading
  bijection predicate, and the disk-reading oracle returns `(manifest-disk-bijection,)`
  alone (the added directory is absent from `state.toml`'s `[chapters]`, so the
  manifest-keyed `_disk_by_chapter` and the done-flag loop never visit it, and
  there is no `compiled.md`). This is a genuine post-build disk-only divergence
  — exactly the roadmap criterion. Date/Author: 2026-06-24, planning agent
  (resolving review round-2 blocking point 1).
- Decision (D-BASELINE-SPEC): the three divergence tests that need the `spec`
  to assert `corpus_check(spec, working) == ()` on the unmutated tree
  (clean-singleton bijection test 2 and both co-fire tests) build via the
  sanctioned `import working_corpus as wc` value import —
  `spec = wc.COHERENT_BASELINE; working = build_tree(spec, tmp_path)` (the exact
  idiom of `tests/test_reconcile_derivation.py` line 93; `wc.COHERENT_BASELINE`
  and `wc.build_working_tree` are public exports, `tests/working_corpus/__init__.py`
  `__all__` lines 55 and 68) — **not** the `baseline_tree` fixture. Rationale:
  `baseline_tree` (`tests/corpus_fixtures.py` line 207) returns only a `Path`
  (`Callable[[], Path]`), so it cannot supply the `spec` object the baseline
  `corpus_check` call requires, and no existing `baseline_tree` consumer calls
  `corpus_check`, so there is no idiom to copy. The round-2 plan prescribed
  `baseline_tree` for these tests, which left a novice stuck at the baseline
  assertion (review round-3 B1). The `wc` value import is the same carve-out the
  existing corpus suites use (`tests/test_disk_evidence.py` line 27); the corpus
  is still consumed by fixture for the builder (`build_tree`) and the verdict
  (`check_corpus`), with the `wc` import used only for the `COHERENT_BASELINE` /
  `COMPILED_AUTO` *values*. `baseline_tree` remains usable only where the `spec`
  is not needed; this module needs it everywhere, so it is not used here.
  Date/Author: 2026-06-24, planning agent (resolving review round-3 blocking
  point B1).
- Decision (D-TESTFORM): the new module uses the **class form**
  (`class TestCorpusDiskDivergence:` with four method tests), mirroring the
  sibling carve-out `tests/test_working_corpus_divergent.py`
  (`class TestCorpusDivergentTable:`). Each method takes `self`, `build_tree`,
  `check_corpus`, and `tmp_path` — four parameters, exactly the PyPy-Pylint
  `max-args=4` ceiling (which does not honour the `**/test_*.py`
  per-file-ignores). No method needs a fifth fixture: the `spec`/`working`
  values come from the `build_tree` call inside the body, not from extra
  parameters, so the ceiling holds with no bundling required. Rationale:
  pinning the test form and the per-test fixture count up front prevents a
  late PyPy-Pylint argument-count failure (review round-3 A2). Date/Author:
  2026-06-24, planning agent.
- Decision (D-COMPILED-HELPER): add a disk-reading draft-body helper to
  `_oracle.py`, `_disk_present_draft_bodies(working_dir)`, that reads each
  manifest chapter's `draft.md` (manifest order from `state.toml` `[chapters]`,
  an absent draft contributing the empty string) and returns the bodies in
  ascending chapter order, mirroring production
  `_present_draft_bodies(state, working_dir)` (`disk_evidence.py` lines 156-168).
  `_check_compiled_matches_drafts` computes its expected concatenation from this
  helper, so the manifest-order source is the same `state.toml` read
  `_disk_by_chapter` already uses — no second on-disk convention. Rationale: the
  oracle has no disk-reading body helper today
  (`_specs._present_draft_bodies` reads the spec), so the reroute must introduce
  one and fix its order source explicitly. Date/Author: 2026-06-24, planning agent
  (resolving review round-1 advisory "compiled-reroute helper is unnamed").
- Decision (D-DEVGUIDE): Work item 3 edits the `disk_evidence.py` "Twin
  asymmetry" docstring (lines 29-33) **only**, plus the developers' guide
  disk-evidence description at lines 336-348 *if and only if* it makes an
  asymmetry claim after re-reading; the round-1 plan's target of lines 426-434 is
  **dropped** because those lines describe the six pure-state §5.2 twins in
  `validate.py` and say nothing about a disk-evidence spec/disk asymmetry.
  Rationale: the review advisory showed lines 426-434 make no asymmetry claim, so
  editing them would invent one. Re-read lines 336-348 during implementation; they
  describe the disk-evidence invariants neutrally and likely need no change, in
  which case Work item 3's only code/doc edit is the `disk_evidence.py` comment
  plus the roadmap checkbox. Date/Author: 2026-06-24, planning agent (resolving
  review round-1 advisory "dev-guide edit targets text that does not assert the
  asymmetry").

## Outcomes & retrospective

- All three work items landed as three atomic commits (Work item 1: reroute;
  Work item 2: divergence-proof self-test; Work item 3: documentation and
  roadmap reification). `make all` is green at HEAD (553 passed, 1 skipped),
  and `make markdownlint` / `make nixie` are green for the markdown touched.
- The four expected `corpus_check` tuples held exactly as the planning probe
  predicted (S4 reproduced S1/S2), so no tuple needed re-discovery and no
  escalation arose.
- The reroute was **not** line-neutral (S3): the file first grew to 428 lines,
  over the 400-line cap. The cap was honoured without a structural split by
  tightening the disk-evidence cluster's docstrings and refactoring
  `_disk_present_draft_bodies` / `_disk_by_chapter` onto a shared `_disk_drafts`
  read, landing at 399 lines. A future plan touching this file should budget for
  the disk-read logic being heavier than the spec read it replaces.
- Work item 3 widened slightly beyond the planned single `disk_evidence.py`
  comment: three further twin docstrings in `disk_evidence.py` carried stale
  "spec-reading" / "keys on `has_done_flag`" claims about the oracle, found by
  grepping for `advisory A1` / `spec-reading`. They were corrected as part of
  the same twin-relationship realignment (still documentation-only, no
  behaviour change), keeping the scope within the five-file Tolerance.
- CodeRabbit raised one actionable code finding (bare asserts in the new test
  module, fixed with brief failure messages) and several markdown-style nits in
  the planning artefacts (second-person/first-person prose, missing fence
  languages, line length), all resolved so the markdown gates pass.

## Documentation to read, and skills to load, before starting

Read first (source of truth):

- `docs/novel-ralph-harness-design.md` §5.4 (lines 484-519, disk-authoritative
  reconciliation — the three contradictions the rerouted predicates cover), §5.2
  lines 460-465 (the manifest-disk bijection), §4.3 lines 320-344 (`compiled.md`
  is the ordered concatenation of the present drafts), and §9 lines 705-711 (the
  content-hash fidelity check over the **present** drafts).
- `docs/roadmap.md` task 2.3.3 (lines 660-677, this task) and its predecessor
  2.3.2 (lines 638-659, which built the production disk-evidence detector this
  task realigns the oracle to).
- `docs/execplans/roadmap-1-3-2.md` Decision Log "fix round 1" (lines 630-654):
  the precedent — the by-chapter-sum check was moved from a spec-internal
  comparison to reading the materialized `state.toml`; this task generalizes that
  move to three more invariants.
- `docs/developers-guide.md` §"Invariant validation" (lines 321-450), especially
  the deliberate-twin policy (lines 426-434) and the disk-evidence detector
  description (lines 336-348); and §"Shared test scaffolding" (the fixture idiom
  and the `working_corpus as wc` value-import carve-out).
- `tests/working_corpus/_oracle.py` (the file under change) and
  `novel_ralph_skill/state/disk_evidence.py` (the production twin and the
  reference for every on-disk convention; the "Twin asymmetry" comment lines
  29-33 to update).
- `AGENTS.md` quality gates (lines 71-98), testing rules (lines 141-166), file
  size (lines 24-27), spelling (lines 18-20).
- `docs/scripting-standards.md` (pathlib for filesystem work; `cuprum` is **not**
  needed here — see "What this task does NOT do").

Skills to load (via the Skill tool / routers):

- `python-router` first, then the sub-skills it routes to:
  - `python-testing` for fixture scopes, `tmp_path`, parametrization, and the
    factory-as-fixture idiom the corpus uses.
  - `python-types-and-apis` for the predicate signature change
    (`(spec) -> bool` to `(working_dir) -> bool` / `(spec, working_dir) -> bool`).
  - `python-iterators-and-generators` only if a disk read benefits from an
    extracted iterator (likely not; the existing helpers suffice).
  - `python-verification` to **confirm** (not assume) that no Hypothesis /
    CrossHair / mutmut adversary is warranted for this change: the reroute is an
    example-based equivalence (disk read equals spec read on faithfully-built
    trees) plus a constructed-divergence proof, both pinned by enumerated
    example tests and the existing whole-corpus agreement suites. If, while
    implementing, a predicate's disk read seems to warrant a generated-input
    property, escalate and reconsider per `python-verification` rather than
    adding an adversary speculatively.
- `en-gb-oxendict` for prose, comments, docstrings, and commit messages.
- `leta` for navigation (`leta show`, `leta refs`, `leta grep`) and `sem` for
  history (the fix-round-1 oracle change is the precedent to inspect).
- `commit-message` for the file-based commit messages each work item ends with.

Hypothesis, CrossHair, and mutmut are **not** required for this task. The
property suites over the corpus belong to the *consumers* (the validator's
Hypothesis suite, the round-trip property); this task's change is an equivalence
proved by the whole-corpus agreement suites already in place plus three
constructed-divergence examples.

## Plan of work

Three atomic, independently committable, gate-passable work items. Each ends
with `make all` green (run gates **sequentially**). Establish the failing
self-test before the behaviour it pins where practical (red, then green).

### Work item 1: reroute the three oracle predicates to read disk

Purpose: make `corpus_check`'s manifest-bijection, done-flag/draft, and
compiled checks read the materialized `working_dir`, so the corpus mirrors what
the real `check` exercises, keeping every existing verdict and all three
agreement suites green.

In `tests/working_corpus/_oracle.py`:

- Replace `_check_manifest_disk_bijection(spec)` (lines 158-171) with a
  disk-reading predicate that reads the manifest from the materialized
  `state.toml` `[chapters]` array and the on-disk side from a
  `working_dir / "manuscript"` glob of `chapter-*` directories (parsing the
  two-digit suffix, ignoring non-`chapter-NN` entries), then asserts the two
  sets are equal and the manifest is contiguous from 1 — the exact rule the
  production `_check_manifest_disk_bijection` /
  `_on_disk_chapter_numbers` uses (`disk_evidence.py` lines 84-122). Reuse the
  existing `state.toml` read pattern from `_disk_by_chapter` (`_oracle.py` lines
  263-264). The signature becomes `(working_dir: Path) -> bool`.
- Replace `_check_done_flag_without_draft(spec)` (lines 212-221) with a
  disk-reading predicate that, for each manifest chapter (read from
  `state.toml`), checks whether `manuscript/chapter-NN/done.flag` exists by a
  `draft.md` whose whitespace-split token count is zero (or beside no `draft.md`
  at all) — the production `_check_done_flag_without_draft` rule
  (`disk_evidence.py` lines 125-153). The signature becomes
  `(working_dir: Path) -> bool`.
- Add a disk-reading draft-body helper `_disk_present_draft_bodies(working_dir)`
  (D-COMPILED-HELPER) that reads the manifest from the materialized `state.toml`
  `[chapters]` array (the same read `_disk_by_chapter` uses, `_oracle.py` lines
  263-264), then reads each chapter's `manuscript/chapter-NN/draft.md` as UTF-8
  (an absent draft contributing the empty string) and returns the bodies in
  ascending chapter order — the disk-reading twin of production
  `_present_draft_bodies(state, working_dir)` (`disk_evidence.py` lines 156-168).
  Then change `_check_compiled_matches_drafts(spec, working_dir)` (lines 234-248)
  so the **expected** concatenation is `concatenate_drafts(`
  `_disk_present_draft_bodies(working_dir))`, rather than
  `draft_body(chapter.draft_words)` over `spec.chapters`. The signature narrows
  to `(working_dir: Path) -> bool` (the manifest order now comes from
  `state.toml`, not `spec`), consistent with the other two rerouted predicates.
  Do not invent a second on-disk convention: reuse the `state.toml` manifest
  read and the `len(text.split())` token rule the corpus already uses.
- Update the `corpus_check` body (lines 341-366): the three rerouted checks now
  take `working_dir` (and no longer `spec` for the disk facts), so move them
  from `_SPEC_CHECKS` (lines 327-338) into the disk-evidence application block
  alongside `BY_CHAPTER_SUM`, `COMPILED_MATCHES_DRAFTS`, `CURSOR_PLAN_PRESENT`,
  and `WORD_COUNTS_MATCH_DRAFTS` (lines 362-365). Update the module docstring and
  the `_SPEC_CHECKS` comment (lines 322-326) to record that
  `MANIFEST_DISK_BIJECTION` and `DONE_FLAG_WITHOUT_DRAFT` are now disk-evidence
  checks too.
- Update the reciprocal cross-reference comments so each rerouted predicate's
  docstring names its production twin and states both sides now read disk
  (removing the "Twin asymmetry (advisory A1)" caveat that no longer applies on
  the oracle side; the `disk_evidence.py` comment is updated in Work item 3).

Tests to update/confirm (no new test file in this item):

- The existing corpus self-tests in `tests/test_working_corpus.py` that exercise
  the three predicates through `corpus_check` —
  `test_each_variant_breaks_exactly_its_invariant` (line 444),
  `test_coherent_trees_pass_the_oracle` (line 458),
  `test_every_invariant_name_is_exercised` (line 471) — must still pass
  unchanged (the verdict is identical on faithfully-built trees).
- The three agreement suites must stay green:
  `tests/test_novel_state_check_disk.py::test_union_detector_agrees_with_corpus_oracle`,
  `tests/test_disk_evidence.py::test_word_counts_twin_equals_corpus_oracle`,
  `tests/test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`.

Verification method: run `make all`. Expect every suite green and the three
agreement suites unchanged. Confirm `wc -l tests/working_corpus/_oracle.py` is
under 400 (Tolerance trigger if not). Commit with a file-based message
(`commit-message` skill).

Docs/skills: `python-types-and-apis` (the signature change),
`python-testing` (the fixtures), `leta` (navigate the twin predicates),
`sem` (inspect the fix-round-1 precedent); design §5.4 / §5.2 / §4.3 / §9 and
`disk_evidence.py` as the on-disk-convention reference.

### Work item 2: the divergence-proof self-test

Purpose: prove the rerouted predicates read disk, not spec, by constructing a
tree whose spec is coherent and whose `state.toml` claims agree with the spec,
mutating the materialized disk so disk diverges, and asserting `corpus_check`
flags exactly the matching disk-evidence invariant **from disk alone** — the
roadmap success criterion ("a tree whose `state.toml` claims agree with disk but
whose disk evidence diverges is flagged by the oracle from disk alone").

New file `tests/test_working_corpus_disk_divergence.py` (kept under the 400-line
cap; mirrors the `tests/test_working_corpus_divergent.py` carve-out idiom).

**Module shape (class form, A2-resolved).** The module uses the **class form**
exactly like the sibling carve-out `tests/test_working_corpus_divergent.py`
(`class TestCorpusDivergentTable:`): one test class
`TestCorpusDiskDivergence` whose four methods are the four divergence tests.
The class form is chosen so the PyPy-Pylint `max-args=4` ceiling is respected
with headroom — see the per-test fixture counts below; each method's parameter
list (counting `self`) stays at or under four.

**How the corpus is consumed (B1-resolved — read this before writing any
test).** Three of the four tests need the `spec` object to assert
`corpus_check(spec, working) == ()` on the unmutated tree, and the
`baseline_tree` fixture (`tests/corpus_fixtures.py` line 207) returns **only a
`Path`** (`Callable[[], Path]`), so it cannot supply that `spec`. Therefore
**do not** use `baseline_tree` for any test in this module. Instead, obtain
`COHERENT_BASELINE` through the **sanctioned `working_corpus as wc` value
import** the existing corpus suites already use
(`tests/test_disk_evidence.py` line 27; `tests/test_reconcile_derivation.py`
line 93; developers' guide §"Shared test scaffolding"). Concretely, the module
header is:

```python
import working_corpus as wc
```

and each spec-needing test builds its tree with the literal idiom (the exact
pattern of `test_reconcile_derivation.py` line 93):

```python
spec = wc.COHERENT_BASELINE
working = build_tree(spec, tmp_path)
```

where `build_tree` is the existing factory fixture
(`tests/corpus_fixtures.py` line 63, returning `wc.build_working_tree`) and
`tmp_path` is pytest's per-test temporary directory. Both
`wc.COHERENT_BASELINE` and `wc.build_working_tree` are public exports of
`working_corpus` (`tests/working_corpus/__init__.py` `__all__`, lines 55 and
68); `wc.COMPILED_AUTO` (line 56) and `wc.WorkingTreeSpec` are likewise public.
This gives the test the `spec` value it needs for the baseline assertion,
which `baseline_tree` cannot. (Equivalently, `spec = wc.COHERENT_BASELINE;
working = wc.build_working_tree(spec, tmp_path)` — the `build_tree` fixture is
merely that builder wrapped, so either form is acceptable; prefer the fixture
form to keep the builder consumed by fixture, with the `wc` import reserved for
the `COHERENT_BASELINE` / `COMPILED_AUTO` *values* only.)

The module therefore consumes the corpus by the fixture `build_tree` plus the
`check_corpus` fixture (`tests/corpus_fixtures.py` line 356, returning
`corpus_check`) for the verdict, and the sanctioned `wc` value import **only**
for the `COHERENT_BASELINE` / `COMPILED_AUTO` *values* — never a value import
of `corpus_check` or the builder, which come through fixtures. It names the
spec *type* only via `from conftest import WorkingTreeSpec` under
`if TYPE_CHECKING:`.

Every test builds a coherent tree, asserts `corpus_check(spec, working) == ()` on
the **unmutated** tree (proving the flip is caused by the disk change, not by an
already-incoherent spec), then performs a **post-build disk-only mutation** (never
a spec change) and asserts the **exact** `corpus_check` tuple — equality, in
`CORPUS_INVARIANT_NAMES` vocabulary order, never membership and never a loose
"singleton". Each expected tuple below is the value the planning probe measured
against a concrete built-and-mutated tree (Surprises & Discoveries S1, S2; Risks).
The spec is **unchanged** between the two `corpus_check` calls; the divergence is
introduced purely on disk after the build, so it is a true "state agrees, disk
diverges" case — the roadmap criterion.

The red-first signal differs by test, and the implementer must know which name
carries it for each, so a local-revert check targets the right predicate:

- For the two **clean-singleton** tests, the *whole* asserted tuple is the
  red-first signal: the spec-reading oracle returns `()` after the mutation
  (count-preserving compiled edit, S1; post-build `mkdir chapter-04`, S2), so the
  one-name tuple fails red against any spec-reading version of that predicate.
- For the two **co-fire** tests, the already-disk-reading `word-counts-match-drafts`
  predicate (rerouted in task 2.3.2) *also* fires on a spec-reading oracle, which
  therefore returns the one-name tuple `(word-counts-match-drafts,)` after the
  mutation. The red-first signal is the **added** name — `manifest-disk-bijection`
  (D-COFIRE1) or `done-flag-without-draft` (D-COFIRE2) — that only the rerouted
  predicate contributes. Exact-tuple equality still fails red (the pre-reroute
  tuple has one name, the asserted tuple has two), but a local-revert check must
  revert the *bijection* / *done-flag* predicate, not `word-counts-match-drafts`,
  to observe the red (round-2 advisory). The probe-measured pre-reroute tuples are
  `(word-counts-match-drafts,)` for both co-fire mutations (S1).

Two clean-singleton tests (one rerouted invariant each, no co-fire):

1. `test_compiled_stale_against_disk_caught_after_count_preserving_edit`:
   build a coherent tree with `compiled="AUTO"` (the hash-equal compile);
   `COHERENT_BASELINE` writes no `compiled.md`, so derive an `AUTO`-compiled
   spec from it with `dataclasses.replace` —
   `spec = dc.replace(wc.COHERENT_BASELINE, compiled=wc.COMPILED_AUTO)` (the
   `dc.replace` + `COMPILED_AUTO` idiom of `test_reconcile_derivation.py` lines
   107-108; `wc.COMPILED_AUTO` is the public sentinel,
   `tests/working_corpus/__init__.py` line 56), then `working =
   build_tree(spec, tmp_path)`. Fixtures: `build_tree`, `check_corpus`,
   `tmp_path` — three parameters plus `self` = four, at the ceiling. Assert
   `()` on the unmutated tree; perform a
   **count-preserving** edit of one chapter's `draft.md` — read its token count
   `n` and overwrite with `n` same-count different tokens (e.g. `"XXXX"`), so the
   whitespace-split count is unchanged but the bytes differ from the written
   `compiled.md`; assert the verdict is exactly `(compiled-matches-drafts,)`. The
   count-preserving edit keeps `word-counts-match-drafts` silent (verified); the
   spec's `draft_words` is unchanged, so a spec-reading expected-concatenation
   would still match the stale `compiled.md`, but the disk read of the edited
   draft catches the divergence. (D-CLEAN.)
2. `test_manifest_bijection_caught_from_disk_after_extra_directory`: build
   `COHERENT_BASELINE` (3-chapter manifest 1/2/3, no `compiled.md`) via the
   sanctioned value import — `spec = wc.COHERENT_BASELINE; working =
   build_tree(spec, tmp_path)` (the `test_reconcile_derivation.py` line 93
   idiom; **not** the `baseline_tree` fixture, which returns only a `Path` and
   so cannot supply the `spec` the baseline assertion needs — B1). Fixtures:
   `build_tree`, `check_corpus`, `tmp_path` — three plus `self` = four, at the
   ceiling. Assert `()` on the unmutated tree; then perform a
   **post-build** disk-only mutation —
   `(working / "manuscript" / "chapter-04").mkdir()` — adding an on-disk chapter
   directory absent from the manifest and carrying no `draft.md`; assert the
   verdict is exactly `(manifest-disk-bijection,)`. The spec is unchanged and
   coherent across the mutation, so the spec-reading oracle returns `()`
   (probe-confirmed, S2) — the test is red against any spec-reading bijection
   predicate. The added directory is absent from `state.toml`'s `[chapters]`, so
   the manifest-keyed `_disk_by_chapter` never reads it (`word-counts-match-drafts`
   silent) and the done-flag loop never visits it (`done-flag-without-draft`
   silent); there is no `compiled.md` (`compiled-matches-drafts` silent). This
   proves the disk-reading bijection check fires in isolation from a genuine
   post-build disk-only divergence — the roadmap criterion. **Do not** reuse the
   `manifest-extra-entry` variant: its spec already declares a non-bijective
   manifest (`manifest_only_numbers=(4,)`), so the spec-reading oracle already
   fires `manifest-disk-bijection` and the test would prove nothing about disk
   reading (round-2 blocking point 1). (D-CLEAN2.)

Two co-firing structural-mutation tests (exact two-name tuple, co-fire recorded):

1. `test_manifest_bijection_and_wordcount_cofire_after_directory_removed`: build
   `COHERENT_BASELINE` (chapters 24000/24000/20800) via the sanctioned value
   import — `spec = wc.COHERENT_BASELINE; working = build_tree(spec, tmp_path)`
   (the `test_reconcile_derivation.py` line 93 idiom; **not** `baseline_tree`,
   which returns only a `Path` and so cannot supply the `spec` the baseline
   assertion needs — B1). Fixtures: `build_tree`, `check_corpus`, `tmp_path` —
   three plus `self` = four, at the ceiling. Assert `()` on the unmutated
   tree; `shutil.rmtree` one `manuscript/chapter-NN/` directory whose table entry
   is non-zero; assert the verdict is exactly
   `(manifest-disk-bijection, word-counts-match-drafts)`. The co-fire is correct
   and intended — disk diverges on both the directory set and the per-chapter word
   count — and the test pins it as the exact tuple so a regression that drops
   either name fails loudly. (D-COFIRE1.)
2. `test_done_flag_and_wordcount_cofire_after_draft_emptied`: build a coherent
   tree whose first chapter is flagged with a non-empty `draft.md`
   (`COHERENT_BASELINE` flags chapters 1 and 2) via the sanctioned value import
   — `spec = wc.COHERENT_BASELINE; working = build_tree(spec, tmp_path)` (the
   `test_reconcile_derivation.py` line 93 idiom; **not** `baseline_tree`, which
   returns only a `Path` and so cannot supply the `spec` the baseline assertion
   needs — B1). Fixtures: `build_tree`, `check_corpus`, `tmp_path` — three plus
   `self` = four, at the ceiling. Assert `()`; overwrite that
   chapter's `draft.md` with empty bytes on disk (the `done.flag` stays); assert
   the verdict is exactly `(done-flag-without-draft, word-counts-match-drafts)`.
   `COHERENT_BASELINE` writes no `compiled.md`, so `compiled-matches-drafts` is
   correctly absent. (D-COFIRE2.)

The two co-firing tests deliberately exercise the same `word-counts-match-drafts`
detector already present in the corpus; they prove that the rerouted
disk-evidence checks compose correctly with it under a genuine multi-axis disk
divergence, rather than suppressing the co-fire with an artificial tree. The
vocabulary order is fixed by `CORPUS_INVARIANT_NAMES`: `manifest-disk-bijection`
(index 6) precedes `word-counts-match-drafts` (index 13);
`done-flag-without-draft` (index 10) precedes `word-counts-match-drafts` (index
13) — both confirmed against the probe output, so the literal tuple order in each
assertion is exactly as written above.

Verification method: write the four tests **red first** against the still-spec-
reading oracle if Work item 1 is not yet merged (they fail because a spec-reading
predicate ignores the disk mutation), then green after Work item 1. If Work item
1 is already merged, the tests are green on commit; in that case, temporarily
revert the **right** predicate locally to confirm the test would have caught a
spec-reading oracle, then restore (record the check in the Decision Log; do not
commit the revert). The right predicate is the one carrying the red-first signal
(see "red-first signal differs by test" above): for the clean singletons revert
the targeted predicate (`_check_compiled_matches_drafts` for test 1,
`_check_manifest_disk_bijection` for test 2); for the co-fire tests revert the
*added*-name predicate (`_check_manifest_disk_bijection` for D-COFIRE1,
`_check_done_flag_without_draft` for D-COFIRE2) — **not** `word-counts-match-drafts`,
which already reads disk and fires on the spec-reading oracle too. Run `make all`.
Each expected tuple is already pinned by the planning probe (S1, S2), so the
implementer asserts the exact literals above and does not need to rediscover the
co-fire shape; if a measured tuple differs from the planned one, that is a
Surprise to record and escalate, not a value to silently adjust. Commit.

Docs/skills: `python-testing` (the build-then-mutate pattern, `tmp_path`,
`shutil`, the count-preserving-edit idiom), `python-types-and-apis`;
`python-verification` to **confirm** no Hypothesis/CrossHair/mutmut adversary is
warranted (these are four enumerated example divergences with exact, measured
expected tuples — example tests, not a generated-input property); design §5.4 for
the three contradictions and §4.3/§9 for the compiled content-hash.

### Work item 3: documentation and roadmap reification

Purpose: align the twin-relationship documentation with the now-symmetric
disk-reading oracle, and close the roadmap entry.

- In `novel_ralph_skill/state/disk_evidence.py`, update the "Twin asymmetry
  (ExecPlan advisory A1)" comment (lines 29-33): the corpus
  `_check_manifest_disk_bijection`, `_check_done_flag_without_draft`, and
  `_check_compiled_matches_drafts` now read disk, so the asymmetry is gone — all
  six twins read disk on both sides. Rewrite the paragraph to say so (this is a
  comment edit, not a behaviour change).
- In `docs/developers-guide.md` §"Invariant validation", **re-read lines 336-348
  and 426-434 before editing** (D-DEVGUIDE). Lines 426-434 describe the six
  pure-state §5.2 twins in `validate.py` and make **no** disk-evidence spec/disk
  asymmetry claim, so they are **not** edited (the round-1 plan's target here was
  wrong, per the review advisory; editing them would invent a claim). Lines
  336-348 describe the six disk-evidence invariants neutrally; edit them **only
  if** they currently assert that an oracle predicate reads the spec while
  production reads disk. If, after re-reading, no developers'-guide sentence makes
  such a claim, make **no** developers'-guide edit and record that in the Decision
  Log — the only twin-asymmetry statement to update is the `disk_evidence.py`
  comment above. This keeps the edit honest rather than manufacturing a sentence
  to rewrite.
- Reify the roadmap checkbox: change `docs/roadmap.md` line 660 from
  `- [ ] 2.3.3.` to `- [x] 2.3.3.`.
- Run the markdown gates for the markdown files actually touched (`docs/roadmap.md`
  always; `docs/developers-guide.md` only if edited).

Verification method: `make all`, then `make markdownlint` and `make nixie`
(markdown changed). Expect all green. Commit.

Docs/skills: `en-gb-oxendict` (the prose edits), `commit-message`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-3`.

Confirm the branch and a clean tree:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-3 \
  branch --show-current
# expect: roadmap-2-3-3
```

Work item 1 — edit `tests/working_corpus/_oracle.py`, then:

```bash
make all
wc -l tests/working_corpus/_oracle.py   # expect: < 400
```

Expected: every suite passes; the three agreement suites unchanged.

Work item 2 — add `tests/test_working_corpus_disk_divergence.py`, then:

```bash
make all
```

Expected transcript fragment:

```plaintext
tests/test_working_corpus_disk_divergence.py ....                   [100%]
```

Work item 3 — edit the two markdown files and the comment, reify the checkbox,
then:

```bash
make all
make markdownlint
make nixie
```

Expected: all green.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make all` is green. The four new divergence-proof tests in
  `tests/test_working_corpus_disk_divergence.py` each pass with their exact,
  probe-verified `corpus_check` tuples — two clean singletons
  (`(compiled-matches-drafts,)`, `(manifest-disk-bijection,)`) and two exact
  two-name co-fires (`(manifest-disk-bijection, word-counts-match-drafts)`,
  `(done-flag-without-draft, word-counts-match-drafts)`) — and each would fail
  against a spec-reading oracle (verified red-first or by the local-revert check
  in Work item 2). The three agreement suites
  (`test_union_detector_agrees_with_corpus_oracle`,
  `test_word_counts_twin_equals_corpus_oracle`,
  `test_incoherent_agreement_restricted_to_owned`) stay green, confirming the
  twins are now genuinely disk-vs-disk.
- Lint/typecheck: `make lint` and `make typecheck` (run within `make all`) pass,
  including 100% docstring coverage (`interrogate`) and PyPy-Pylint's
  argument-count gate on the new self-tests.
- File size: `tests/working_corpus/_oracle.py` and
  `tests/test_working_corpus_disk_divergence.py` are each under 400 lines.
- Markdown: `make markdownlint` and `make nixie` are green for
  `docs/developers-guide.md`, `docs/roadmap.md`, and this execplan.

Quality method (verification approach): run `make all` (then `make markdownlint`
and `make nixie` for the markdown work item) sequentially after each work item,
as described in Concrete steps. The roadmap success criterion is met when the
oracle's manifest-bijection, done-flag/draft, and compiled checks read the
materialized `working_dir` and a tree whose `state.toml` claims agree with the
spec but whose disk evidence diverges is flagged by the oracle from disk alone —
pinned by the four divergence-proof tests, every one a post-build disk-only
mutation the spec-reading oracle misses.

## Idempotence and recovery

Every step is re-runnable: the oracle edit is a pure refactor of three
predicates with no persistent side effects, and the self-tests build their trees
under pytest's `tmp_path` (function-scoped, auto-cleaned), so reruns leave no
residue. If `make all` fails after an edit, inspect the failing suite; the three
agreement suites failing on an **unmutated** corpus tree is the signal that a
disk read and a spec read genuinely disagree (escalate per Tolerances). To roll
back a work item, `git restore` the touched files — no migration or data change
is involved.

## Interfaces and dependencies

In `tests/working_corpus/_oracle.py`, after Work item 1:

```python
def _disk_present_draft_bodies(working_dir: Path) -> list[str]: ...
def _check_manifest_disk_bijection(working_dir: Path) -> bool: ...
def _check_done_flag_without_draft(working_dir: Path) -> bool: ...
def _check_compiled_matches_drafts(working_dir: Path) -> bool: ...
```

All three rerouted predicates narrow to `(working_dir: Path) -> bool` (the
compiled check reads its manifest order from `state.toml` via the new
`_disk_present_draft_bodies` helper, D-COMPILED-HELPER, so it no longer needs
`spec`). `corpus_check(spec, working_dir)` keeps its signature; the three checks
move out of `_SPEC_CHECKS` into the disk-evidence application block alongside the
existing disk-reading checks (`BY_CHAPTER_SUM`, `COMPILED_MATCHES_DRAFTS`,
`CURSOR_PLAN_PRESENT`, `WORD_COUNTS_MATCH_DRAFTS`).

The oracle must **not** import any symbol from
`novel_ralph_skill.state.disk_evidence` — the deliberate-twin policy requires the
duplication. The disk reads use `pathlib.Path` and `tomllib` only, plus the
corpus's own `concatenate_drafts` / `chapter_dir_name` helpers from `_specs.py`.

No new runtime or dev dependency is introduced. `cuprum` is not used.

## Revision note

Revision 4 (2026-06-24, after design review round 3). Resolved the single
round-3 blocking point B1 and folded in advisories A1 and A2. B1: the three
divergence tests that need the `spec` to assert
`corpus_check(spec, working) == ()` on the unmutated tree (clean-singleton
bijection test 2 and both co-fire tests) were prescribed to use the
`baseline_tree` fixture, which returns **only** a `Path`
(`tests/corpus_fixtures.py` line 207, `Callable[[], Path]`) and so cannot supply
the `spec`; no existing `baseline_tree` consumer calls `corpus_check`, leaving a
novice stuck at the baseline assertion. Work item 2 now states explicitly that
these tests build via the sanctioned `import working_corpus as wc` value
import — `spec = wc.COHERENT_BASELINE; working = build_tree(spec, tmp_path)`, the
exact
idiom of `tests/test_reconcile_derivation.py` line 93, with
`wc.COHERENT_BASELINE` and `wc.build_working_tree` confirmed public in
`tests/working_corpus/__init__.py` `__all__` (lines 55, 68) — and the
`baseline_tree` prescription is dropped for them (recorded as Decision
D-BASELINE-SPEC; the orientation fixture list now flags that `baseline_tree`
returns only a `Path`). Test 1 (compiled) is harmonized to the same `wc` import,
deriving its `AUTO`-compiled spec with `dc.replace(wc.COHERENT_BASELINE,
compiled=wc.COMPILED_AUTO)` rather than the `make_working_tree_spec` fixture, so
the whole module shares one construction idiom. A2: the module's test form is
pinned to the **class form** (`class TestCorpusDiskDivergence:`, mirroring
`tests/test_working_corpus_divergent.py`) and each test's fixture list is fixed
at `self`, `build_tree`, `check_corpus`, `tmp_path` — four parameters, at the
PyPy-Pylint `max-args=4` ceiling with no bundling needed (recorded as
D-TESTFORM). A1: the scope Tolerance is reconciled — the cap is raised from
"more than 4 files" to "more than five files", so making the conditional
developers'-guide edit on the literal happy path no longer trips the plan's own
escalation. The reroute mechanics (Work item 1), the four expected
`corpus_check` tuples, and the round-3-confirmed probe facts (S1, S2, D-COFIRE1,
D-COFIRE2, D-CLEAN2) are unchanged — the round-3 review re-verified every tuple
against source and re-ran the probe.

Revision 3 (2026-06-24, after design review round 2). Resolved the single
round-2 blocking point: clean-singleton bijection test 2 was built on a reuse of
the `manifest-extra-entry` variant, whose spec already declares a non-bijective
manifest (`manifest_only_numbers=(4,)`), so the spec-reading oracle already
returned `('manifest-disk-bijection',)` for it — the assertion passed identically
against the spec-reading and the disk-reading oracle, proving nothing about disk
reading, violating the plan's own red-first guarantee, and missing the roadmap's
"state agrees, disk diverges" criterion. Test 2 is re-specified
(`test_manifest_bijection_caught_from_disk_after_extra_directory`) around a
genuine **post-build** disk-only mutation: build `COHERENT_BASELINE`, assert `()`,
then `(working / "manuscript" / "chapter-04").mkdir()` and assert exactly
`(manifest-disk-bijection,)`. A planning-agent probe (Surprises & Discoveries S2)
independently confirmed the spec-reading oracle returns `()` after the `mkdir`
(red-first holds) while the disk-reading oracle returns `(manifest-disk-bijection,)`
alone (`word-counts-match-drafts`, `done-flag-without-draft`, and
`compiled-matches-drafts` all silent). The corrected construction is recorded as
Decision D-CLEAN2, the probe as S2, and the `manifest-extra-entry`-reuse Risks
bullet is rewritten accordingly. The two round-2 advisories are folded in: the
red-first prose now states *which* name carries the red-first signal per test (for
the co-fire tests it is the added `manifest-disk-bijection` / `done-flag-without-draft`
name, not the already-disk-reading `word-counts-match-drafts`, whose pre-reroute
tuple is `(word-counts-match-drafts,)`), and the local-revert guidance names the
right predicate to revert for each test; and the cosmetic `_oracle.py` line count
is corrected from 367 to 366. Work items 1 and 3, the two co-fire tests
(D-COFIRE1/D-COFIRE2), and the count-preserving compiled singleton (D-CLEAN) are
unchanged — the round-2 review confirmed them sound.

Revision 2 (2026-06-24, after design review round 1). Resolved all three blocking
points and the four advisories by grounding Work item 2's test design in measured
fact rather than a "singleton" promise. A planning-agent probe built each tree
with `build_working_tree` and ran a disk-reading `corpus_check` to pin the exact
`corpus_check` tuple for every divergence (recorded in Surprises & Discoveries S1
and Risks). Blocking points 1 and 3 (directory-removal co-fire): the
directory-removal divergence test now asserts the exact two-name tuple
`(manifest-disk-bijection, word-counts-match-drafts)` and records the co-fire as
Decision D-COFIRE1. Blocking point 2 (empty-draft co-fire): the empty-draft test
asserts `(done-flag-without-draft, word-counts-match-drafts)` (no `compiled.md`
co-fire on `COHERENT_BASELINE`), recorded as D-COFIRE2. Blocking point 3 (contradictory
acceptance criterion): every divergence test now asserts an exact tuple in
`CORPUS_INVARIANT_NAMES` vocabulary order — the "singleton" language is removed;
two clean-singleton tests (D-CLEAN) cover the in-isolation case with a
count-preserving compiled edit and a structural manifest mismatch. The three
advisories are folded in: the count-preserving edit is specified precisely
(D-CLEAN); the compiled helper is named `_disk_present_draft_bodies` with its
manifest-order source fixed to `state.toml` (D-COMPILED-HELPER), narrowing
`_check_compiled_matches_drafts` to `(working_dir)`; and the developers'-guide
edit is re-scoped to the `disk_evidence.py` comment, with the lines-426-434 target
dropped (D-DEVGUIDE). Work item 1 is unchanged in intent and confirmed by the
probe to keep all 22 existing variants singletons and the agreement suites green.

Initial draft (2026-06-24). Decomposes roadmap task 2.3.3 into three work items:
reroute the three spec-reading oracle predicates
(`_check_manifest_disk_bijection`, `_check_done_flag_without_draft`,
`_check_compiled_matches_drafts`) to read the materialized `working_dir`; prove
the reroute with a constructed spec-agrees-disk-diverges self-test; and align the
twin-relationship documentation plus reify the roadmap checkbox. Anchored to
design §5.4 / §5.2 / §4.3 / §9, the developers' guide deliberate-twin policy, the
production §5.4 detector in `novel_ralph_skill/state/disk_evidence.py` (the
on-disk-convention reference and the "Twin asymmetry" comment to update), and the
fix-round-1 precedent in `docs/execplans/roadmap-1-3-2.md`. Confirmed
test/corpus-only with no production-behaviour or design change, no new
dependency, and no `cuprum` use (the oracle shells out to nothing and touches
only the filesystem under `tmp_path`, per design §9 line 711).

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge review and audit of step 2.3. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge. The substantial, cross-cutting
follow-ups were re-routed off this task: the `_oracle.py` disk-evidence
predicate carve-out into an `_oracle_disk.py` sibling (audit:2.3.3 / review:2.3.3,
medium — a cap-driven test-maintainability split, which subsumes the
read-consolidation below as the predicates move) to new roadmap step 7.12, and
the open-coded `chapter-NN` directory-name production helper (audit:2.3.3, low)
to roadmap step 7.10 (task 7.10.2, the chapter-draft-sourcing hypothesis); the two
below are the small, localized follow-ups.

- [x] 2.3.3.1 — Consolidate the repeated per-predicate `state.toml` parse in the
  corpus oracle's disk-evidence checks into a single per-invocation read (from
  review:2.3.3, low). In `tests/working_corpus/_oracle.py` the disk-evidence
  predicates (`_check_by_chapter_sum`, `_check_manifest_disk_bijection`,
  `_check_done_flag_without_draft`, `_check_pending_turn_cleared`,
  `_check_compiled_matches_drafts`, `_check_word_counts_match_drafts`) each call
  `tomllib.loads((working_dir / "state.toml").read_text(...))` independently;
  parse it once in `corpus_check` and pass the decoded tables into the helpers,
  removing the redundant reads and the on-disk-convention drift surface. The
  production `disk_evidence.py` twin already receives a parsed `State` and needs
  no mirror. Keep every corpus agreement suite green. (If step 7.12's carve-out
  lands first, this is subsumed — the carve threads the single read as the
  predicates move; close this then.)
- [x] 2.3.3.2 — Document the disk-evidence disk-vs-disk twin discipline and
  invariant 5's delivered status in the developers' guide (from audit:2.3.3,
  medium). After this task the corpus oracle reads disk for the §5.4 invariants,
  so its disk-evidence checks (`tests/working_corpus/_oracle.py`) are now
  **disk-vs-disk** twins of the production `check_disk_evidence`
  (`novel_ralph_skill/state/disk_evidence.py`), not the pure-state `validate_state`
  twins the guide's twin-policy section describes. The guide's owned-name table
  also still marks §5.2 invariant 5 "deferred to task 2.3.2" though 2.3.2/2.3.3
  have delivered the §5.4 disk-evidence detectors. In
  `docs/developers-guide.md` ("The `working/` fixture corpus" / twin policy),
  add a paragraph recording the disk-vs-disk twin discipline and update the
  invariant-5 status, so maintainers learn the policy from the source of truth
  rather than only from source docstrings. Markdown-only.
