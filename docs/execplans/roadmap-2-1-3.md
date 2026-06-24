# Cross-check the §5.2 validator against a live-draft oracle over the whole corpus

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 3)

## Purpose / big picture

The novel-ralph harness keeps its primary memory in `working/state.toml`. The
§5.2 validator (`novel_ralph_skill.state.validate_state`, roadmap task 2.1.2)
decides whether a parsed `state.toml` contradicts itself, reading nothing
beyond that one file. The §1.3.2 on-disk fixture corpus (roadmap task 1.3.2) is
the shared truth set every state suite is cross-checked against; it exposes a
stable invariant-name vocabulary, `CORPUS_INVARIANT_NAMES`
(`tests/working_corpus/_oracle.py`), precisely so the canonical validator can
be cross-checked against it (the 1.3.2 execplan,
`docs/execplans/roadmap-1-3-2.md`, advisory A5, records this as the wiring task
2.1.3 must complete).

An agreement suite already exists — `tests/test_validate_state_corpus.py` (237
lines). It already drives the validator from each fixture's materialised
`state.toml` (`load_state(working_dir / "state.toml")`), restricts both
verdicts to `PURE_STATE_INVARIANT_NAMES`, handles the parse-enforced
`phase-in-enum` case, and pins the scope boundary (the validator emits no
disk-evidence name).

The genuine residual gap this task closes is the one the developers' guide
names explicitly. `docs/developers-guide.md` (the "Invariant validation"
section, lines 323-334) records that **two** of the validator's owned
predicates are **pure-state proxies** for a real disk quantity, and names
*both* in the same sentence the task discharges. Verified against
`novel_ralph_skill/state/validate.py`:

- `_check_consecutive_clean_within_drafted` (lines 176-193) counts
  `word_counts.by_chapter` entries with a positive drafted total
  (`sum(1 for words in state.word_counts.by_chapter.values() if words > 0)`,
  line 187) as the pure-state proxy for the design's **"chapters drafted"**
  disk quantity; and
- `_check_gate_ratio_consistent` (lines 228-249) uses `sum(by_chapter.values())`
  (line 241) — the **drafted-words total** from the table — as its invariant-7
  numerator.

The guide closes that paragraph (lines 329-334) with the sentence this task
discharges: "reconciling the proxy against a **live draft count** is task
2.1.3's on-disk cross-check." Both proxies must therefore be reconciled against
the live drafts; round 2's plan reconciled only the gate ratio and left the
drafted-chapters proxy on its table basis, which the round-2 review flagged as
a repeat overclaim (B1-r2). A *live draft count* means the words actually
written into the on-disk `draft.md` files — a source genuinely independent of
the `[word_counts]` table the validator and the parser trust, and therefore the
only source that can catch a `[word_counts]`-table-versus-real-drafts mislabel
of either drafted **words** or drafted **chapters**.

The corpus makes both quantities recoverable. The builder writes each chapter's
`draft.md` with `draft_body(chapter.draft_words)`
(`tests/working_corpus/_builder.py` `_write_chapter`, line 169-172), and
`draft_body(n)` is exactly `n` whitespace-separated `word` tokens
(`tests/working_corpus/_specs.py` `draft_body`, lines 205-214; empty string for
`n <= 0`, so a `draft_words=0` chapter yields a zero-token `draft.md`). So from
the present `draft.md` bodies the live oracle recovers two independent numbers:

- the **live drafted-words total** — the sum of each present `draft.md`'s
  whitespace-split token count — which equals
  `sum(chapter.draft_words for present chapters)`, the honest draft total the
  oracle's `_check_gate_ratio_consistent` already uses as its invariant-7
  numerator (`tests/working_corpus/_oracle.py`, lines 190-203); and
- the **live drafted-chapters count** — the number of present `draft.md` bodies
  with a positive token count — which equals
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)`, the
  drafted-chapters basis the oracle's `_check_consecutive_clean_within_drafted`
  uses as its ceiling (`tests/working_corpus/_oracle.py`, lines 142-149).

Both are decoupled on purpose from the `[word_counts]` table so a
`by_chapter_override` or `current_words_override` cannot perturb them.

After this change, a single named acceptance test asserts that for **every**
§1.3.2 corpus fixture — every coherent tree and every incoherent variant — the
§5.2 validator's verdict, run against the materialised `state.toml`, matches a
**live-draft oracle's** verdict **exactly** once both are restricted to the
eight pure-state invariants the validator owns: coherent trees pass (empty
verdict) and each incoherent variant is rejected on its one named invariant.
The live-draft oracle recomputes **both** live quantities (drafted-words total
and drafted-chapters count) from the `draft.md` bodies on disk and cross-checks
the `[gates.knitting]` booleans (against the live drafted-words ratio) and the
`consecutive_clean` counter (against the live drafted-chapters count) against
*those independent numbers*, so the two checkers agree on quantities neither
one derived from the table they are both supposed to be validating. The
drafted-words total also feeds the table-coherence half (`by-chapter-sum`, a
table-internal read with no live analogue — see Decision Log).

Run `make test` to see it working: a new test in
`tests/test_validate_state_corpus.py` (or a sibling module) iterates the whole
corpus and asserts live-draft agreement keyed on `CORPUS_INVARIANT_NAMES`, and
the whole state suite stays green.

### Why this is a test-only task

This is an acceptance/anti-drift task, not a behaviour-change task. The §5.2
validator (`validate_state`), the corpus oracle (`corpus_check`), the corpus
fixtures, and the shared vocabulary (`PURE_STATE_INVARIANT_NAMES` /
`CORPUS_INVARIANT_NAMES`) all already exist and are locked by tasks 2.1.1,
2.1.2, 2.1.4, and 1.3.2. This plan adds the **live-draft oracle cross-check**
the design and the reroute demand and the full-vocabulary agreement assertion
keyed on `CORPUS_INVARIANT_NAMES`, and pins them so they cannot silently
degrade. No production code under `novel_ralph_skill/` changes; if
implementation reveals that honouring the acceptance clause requires a
production change, that is a tolerance breach (see `Tolerances`) and must be
escalated, not absorbed.

## Constraints

- Do not modify any production module under `novel_ralph_skill/`. This task is
  an
  acceptance clause over the task-2.1.2 validator; the validator's behaviour is
  locked. (Design §5.2; developers-guide "Invariant validation".)
- Do not modify the §1.3.2 corpus data or builder
  (`tests/working_corpus/_specs.py`, `_library.py`, `_variants.py`,
  `_builder.py`) and do not change the existing spec-keyed `corpus_check` or
  `CORPUS_INVARIANT_NAMES`. The only permitted edit to the corpus package is to
  **add** a new live-draft oracle entry point (and its fixture) if and only if
  Work item 1 concludes it belongs in the corpus package rather than the test
  module. (`docs/execplans/roadmap-1-3-2.md` Constraints; developers-guide
  "Shared test scaffolding".)
- Do not import the validator into the corpus oracle, and do not import the
  oracle's predicates into the validator: the two are deliberate twins kept
  independent on purpose, and de-duplicating them would defeat the cross-check.
  The live-draft oracle is likewise independent — it must not call
  `validate_state` and must not read the `[word_counts]` table to derive the
  drafted-words total or the drafted-chapters count it reconciles the gate
  booleans and the `consecutive_clean` counter against. (developers-guide
  "Invariant validation", deliberate-twin policy.)
- The cross-check's validator side must read the materialised `state.toml` via
  the production parser (`novel_ralph_skill.state.load_state`). The live-draft
  oracle's drafted-words total and drafted-chapters count must both come from
  the on-disk `draft.md` bodies, never from `[word_counts]`. (roadmap 2.1.3
  reroute; developers-guide lines 329-334; `docs/execplans/roadmap-1-3-2.md`
  advisory A5.)
- Tests consume the corpus by **fixture parameter name** only — never by a
  runtime value import of the `working_corpus` package; spec *types* arrive
  through the `from conftest import WorkingTreeSpec` `TYPE_CHECKING` carve-out.
  (developers-guide "Shared test scaffolding".)
- No single code file exceeds 400 lines; `tests/test_validate_state_corpus.py`
  is at 237 lines, so a substantial addition may require a sibling module or a
  small extracted helper. (AGENTS.md lines 24-27.)
- All prose, comments, docstrings, and commits use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`). (Standing rules; AGENTS.md line 18; `.rules`.)
- The validator owns eight pure-state names and must never emit any of the five
  disk-evidence names (`manifest-disk-bijection`, `done-flag-without-draft`,
  `compiled-matches-drafts`, `pending-turn-cleared`, `cursor-plan-present`);
  the agreement restriction must respect that boundary. (developers-guide
  "Invariant validation"; roadmap 2.1.2 and 2.1.4.)
- Every commit must pass all quality gates. No deliberately-red commit is
  permitted; the failing acceptance test and the live-draft oracle that
  satisfies it land in **one green commit**. (AGENTS.md lines 100 and 108.)

## Tolerances (exception triggers)

- Scope: if the change requires touching more than the test tree plus, at most,
  one additive helper in `tests/working_corpus/` (`_oracle.py`) and its fixture
  in `tests/corpus_fixtures.py`, stop and escalate. Net new test code is
  expected to be roughly 90-180 lines; if it exceeds ~260 net lines, stop and
  reconsider the decomposition.
- Production change: if making the live-draft agreement pass requires **any**
  edit
  under `novel_ralph_skill/`, stop and escalate — that means the validator and
  the live drafts disagree on a materialised tree, which is a real finding (a
  validator bug or a corpus-builder bug), not a test to be bent. Record the
  tree, the validator verdict, and the live-draft oracle verdict in
  `Decision Log` before escalating.
- Vocabulary drift: if the eight owned validator names and the oracle's matching
  `CORPUS_INVARIANT_NAMES` entries are not already equal (a precondition this
  task asserts via the existing `test_owned_names_equal_corpus_vocabulary` but
  does not establish), stop and escalate — that is a 2.1.2 regression, not a
  2.1.3 concern.
- Live-count basis: if reading from the `draft.md` bodies does **not** reproduce
  either honest-draft basis on the coherent corpus — the live drafted-words
  total must equal `sum(chapter.draft_words for present chapters)`, and the
  live drafted-chapters count must equal
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)` (the Work
  item 1 self-test pinning both live numbers to the oracle's honest-draft
  bases) — stop and escalate: the corpus builder and the `draft_body` token
  model have drifted, which is a 1.3.2 concern.
- Iterations: if the new test still fails after 3 honest attempts that do not
  edit
  production code, stop and escalate (likely a genuine validator/corpus
  disagreement).

## Risks

- Risk: The live-draft oracle re-implements the §5.2 invariant-7 rule and so
  becomes a third copy that drifts from both the validator and the spec-keyed
  `corpus_check`. Severity: medium Likelihood: medium Mitigation: The
  live-draft oracle does NOT re-read the `[word_counts]` table to compute its
  drafted-words numerator or its drafted-chapters count — it reads the
  `draft.md` bodies, which is the one genuinely independent source. It reuses
  the production-pinned `GATE_THRESHOLDS` (already pinned equal to the
  validator's by `test_corpus_gate_thresholds_equal_production`). A Work item 1
  self-test pins **both** live numbers equal to the oracle's honest-draft bases
  on every coherent tree — the live drafted-words total equal to
  `sum(chapter.draft_words)` and the live drafted-chapters count equal to
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)` — so the
  live readings cannot silently diverge from the honest bases while the corpus
  stays coherent.

- Risk: A future variant sets `by_chapter_override` so the table's `by_chapter`
  diverges from the drafts on disk (a legal "table mislabels the drafts" state
  the design permits, and exactly what 2.1.3 exists to catch) alongside a gate
  flag or a `consecutive_clean` counter. The validator reads the table for both
  proxies (invariant-7 numerator `sum(by_chapter.values())`; invariant-4c
  ceiling the count of `by_chapter` entries `> 0`), so its verdict would then
  diverge from the live oracle on whichever proxy the override perturbs.
  Severity: medium Likelihood: low Mitigation: This is the precise re-coupling
  the live-draft design exists to surface, not to suppress. The validator reads
  the table; the live oracle reads the drafts. They agree on every *current*
  corpus tree because no current variant makes the table's `by_chapter` diverge
  from the drafts (verified: `tests/working_corpus/_variants.py` —
  `by-chapter-sum-mismatch` overrides `current`, not `by_chapter`; no variant
  sets `by_chapter_override`). Document in the test docstring and Decision Log
  that the live oracle's invariant-7 numerator AND its invariant-4c ceiling are
  the **honest-draft** bases (the same bases the validator's two proxies
  mirror), so a future override-plus-gate or override-plus-`consecutive_clean`
  variant that legitimately separates the table from the drafts is a *finding
  to investigate* (which reading is wrong), not a test to "fix" by aligning the
  oracles. This is the documented landmine the round-1 pre-mortem named and the
  round-2 pre-mortem extended to the drafted-chapters proxy; the live-draft
  basis is the single honest source that defuses it for *both* proxies.

- Risk: `phase-not-in-enum` is parse-enforced (the parser raises before the
  validator runs), so a naive "validator verdict == oracle verdict" loop either
  crashes or mislabels that variant. Severity: medium Likelihood: high
  Mitigation: Reuse the existing `_load_succeeds` /
  `_PARSE_ENFORCED_INVARIANTS` / `_PARSE_ERRORS` handling already in
  `tests/test_validate_state_corpus.py`; the new live-draft assertion must
  treat a parse-rejected tree as the parser enforcing the oracle's owned label,
  exactly as the current `test_incoherent_agreement_restricted_to_owned` does.

- Risk: The corpus carries variants whose single named invariant is a
  **disk-evidence** name (for example `cursor-plan-present`,
  `manifest-disk-bijection`); the validator correctly stays silent on those, so
  a "rejected on its one named invariant" assertion fails if read too
  literally. Severity: medium Likelihood: high Mitigation: Restrict both
  verdicts to `PURE_STATE_INVARIANT_NAMES` before comparing (as the existing
  suite does); a disk-evidence variant then yields two empty restricted sets,
  which agree. Document this explicitly in the test docstring so a future
  reader does not mistake the empty case for a missing assertion.

- Risk: A new test exhausts the 400-line cap on
  `tests/test_validate_state_corpus.py`. Severity: low Likelihood: medium
  Mitigation: If the addition would breach the cap, place the live-draft oracle
  in `tests/working_corpus/_oracle.py` (additive, beside the existing checks)
  with a `check_live_draft` fixture in `tests/corpus_fixtures.py`, and put the
  new assertions in a sibling module
  (`tests/test_validate_state_live_draft.py`) consuming the same fixtures; lift
  any shared helper (`_PARSE_ERRORS`, `_load_succeeds`, `_validator_verdict`)
  into a small support module imported by both, mirroring the existing
  `corpus_fixtures` plugin split precedent.

## Progress

- [x] Work item 1: add the live-draft oracle (drafted-words total and
  drafted-chapters count from `draft.md` bodies; cross-checks the gate booleans
  against the live ratio, the `consecutive_clean` counter against the live
  drafted-chapters count, and the `[word_counts]` table-coherence half) plus
  its self-test pinning both live numbers to the honest-draft bases.
- [x] Work item 2: add the whole-corpus live-draft agreement test keyed on
  `CORPUS_INVARIANT_NAMES` and the coherent-tree pin, all green in one commit
  with Work item 1.
- [x] Work item 3: document the delivered live-draft cross-check in the
  developers' guide, correcting the guide's promise sentence to state what was
  actually delivered.

Progress notes (2026-06-23, implementation agent):

- The corpus-package path was taken. The live-draft oracle landed in a **new**
  module `tests/working_corpus/_live_draft.py` (not appended to `_oracle.py`):
  appending to `_oracle.py` pushed it to 444 lines, breaching the 400-line cap
  (`pylint C0302`), so the live oracle is a sibling module that imports
  `corpus_check` and the name constants from `_oracle`. `_check_by_chapter_sum`
  is module-private in `_oracle.py`, so the table-coherence read is
  re-implemented locally as `_check_by_chapter_sum_live` (a deliberate twin),
  keeping the cross-check self-contained.
- `live_draft_counts` and `live_draft_owned` are re-exported from
  `tests/working_corpus/__init__.py` and exposed through the `check_live_draft`
  and `live_draft_counts` fixtures in `tests/corpus_fixtures.py`.
- The new tests live in the sibling module
  `tests/test_validate_state_live_draft.py` (cap-safe). The four shared parse
  helpers (`PARSE_ERRORS`, `PARSE_ENFORCED_INVARIANTS`, `load_succeeds`,
  `validator_verdict`) were lifted into `tests/_state_corpus_support.py`,
  imported by both `test_validate_state_corpus.py` and the new live-draft
  module, per the Risks-section sibling-module prescription.
- No table-versus-draft discrepancy surfaced: the validator and the live-draft
  oracle agree on every coherent tree (empty owned verdict) and every
  incoherent variant. `make all` is green (298 passed);
  `coderabbit review --agent` returned 0 findings.

## Surprises & discoveries

- Observation: A prior 2.1.3 attempt existed on this branch and was discarded.
  Evidence: `git stash list` showed `stash@{0}: On roadmap-2-1-3: cleanup`
  based on an unreachable commit "Add full-vocabulary validator-corpus
  agreement suite" (7ae2352). Impact: The plan starts fresh from the committed
  state. Treat the stash as throwaway. The current
  `tests/test_validate_state_corpus.py` (added under 2.1.2, extended under
  2.1.4) is the real starting point.

- Observation: Design §5.2 invariant 3 is *already* read from disk by the
  oracle; only the live-draft reconciliation remained. Evidence:
  `tests/working_corpus/_oracle.py::_check_by_chapter_sum` (lines 108-119)
  already reads `[word_counts]` from the materialised `state.toml` and compares
  `sum(by_chapter) == current`; the 1.3.2 fix-round-1 decision
  (`docs/execplans/roadmap-1-3-2.md` lines 630-654) moved it there. The genuine
  residual gap the developers' guide (lines 329-334) names is the live-draft
  cross-check, not "move invariant 3 onto disk". Impact: The plan does not
  re-read invariant 3 from the table as if new; it delivers the live-draft
  reconciliation the guide promises.

- Observation: Both live quantities are recoverable byte-for-byte from disk.
  Evidence: `_builder.py::_write_chapter` writes
  `draft_body(chapter.draft_words)` into `draft.md`; `draft_body(n)`
  (`_specs.py` lines 205-214) is `n` whitespace-separated `word` tokens (empty
  string for `n <= 0`). So the whitespace-split token count of each present
  `draft.md` equals `chapter.draft_words`: their sum equals the oracle's
  honest-draft inv-7 numerator
  `sum(chapter.draft_words for chapter in spec.chapters)` (`_oracle.py` line
  199), and the count of those `draft.md` bodies with a positive token count
  equals the oracle's inv-4c ceiling
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)`
  (`_oracle.py` line 148). A `draft_words=0` chapter writes a zero-token
  `draft.md` (empty body), so it is correctly excluded from the live
  drafted-chapters count, matching the `> 0` filter exactly. Impact: The
  live-draft oracle reads `draft.md` files only for both proxy bases and is
  genuinely independent of the `[word_counts]` table.

- Observation: The corpus fixtures already deliver `(spec, working_dir)`, so a
  `(spec, working_dir)` live-oracle signature needs no spec reconstruction.
  Evidence: `coherent_oracle_cases` returns `list[tuple[WorkingTreeSpec, Path]]`
  (`tests/corpus_fixtures.py` lines 176-203) and `incoherent_tree(name)`
  returns `(WorkingTreeSpec, Path, str)` (lines 221-253). Both carry the spec
  the test must pass to reuse `corpus_check` for the five non-disk-derived
  invariants. Impact: The round-2 `working_dir`-only signature (which would
  have had to re-parse the spec out of `state.toml` to reuse `corpus_check`) is
  dropped for the `(spec, working_dir)` form; the spec is already in hand at
  every call site (round-2 review B2-r2).

## Decision log

- Decision: The cross-check is a **live-draft** oracle: it recomputes both the
  drafted-words total and the drafted-chapters count from the on-disk
  `draft.md` bodies (per present chapter: whitespace token count summed for the
  total; positive-token chapters counted for the chapter count) and
  cross-checks the `[gates.knitting]` booleans against the live ratio and the
  `consecutive_clean` counter against the live chapter count; it never derives
  the numbers it checks from the `[word_counts]` table it checks. Rationale:
  This is the cross-check the developers' guide (lines 329-334) and the roadmap
  reroute define, and the only construction that is genuinely independent of
  both the validator (which reads the table) and the spec. Round 1's "re-read
  `[word_counts]` via tomllib" construction consumed the same bytes and the
  same arithmetic as the validator (parse.py `_word_counts` reads the same
  three keys straight through; the validator applies the same two formulas), so
  it compared the validator against a restatement of itself and caught nothing
  (round-1 review B1). Reading the drafts fixes that. Round 2 reconciled only
  the gate ratio; round 3 adds the drafted-chapters proxy so both proxies the
  guide names are reconciled against the live drafts (round-2 review B1-r2).
  Date/Author: 2026-06-23, planning agent.

- Decision: Both live-draft proxy bases are the **honest live-draft** quantities
  read from disk, NOT their `[word_counts].by_chapter` table equivalents. The
  invariant-7 numerator is the live drafted-words total
  (`sum(len(draft.read_text().split()))` over present `draft.md`), NOT
  `sum(by_chapter.values())`; the invariant-4c ceiling is the live
  drafted-chapters count (number of present `draft.md` bodies with a positive
  token count), NOT the count of `by_chapter` entries `> 0`. Rationale: The
  oracle's `_check_gate_ratio_consistent` uses `sum(chapter.draft_words)` and
  its `_check_consecutive_clean_within_drafted` uses
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)` deliberately
  so a `by_chapter_override` cannot perturb either proxy (developers-guide
  lines 324-332; `docs/execplans/roadmap-1-3-2.md` Outcomes lines 685-686). The
  live reads reproduce exactly those honest bases from disk. Reading the table
  instead would silently re-couple both proxies to a quantity the design
  decoupled them from (round-1 review B2; round-2 review B1-r2). A self-test
  pins BOTH live numbers equal to their honest-draft bases on coherent trees so
  the readings cannot drift while the corpus stays coherent. Date/Author:
  2026-06-23, planning agent.

- Decision: The live oracle also cross-checks the `[word_counts]` table
  (`current` and the `by_chapter` per-chapter values) against the live drafted
  total, naming `by-chapter-sum` when the table is internally inconsistent
  (`sum(by_chapter) != current`) and `gate-ratio-consistent` when a gate
  boolean disagrees with the live ratio. Rationale: This makes the live oracle
  a complete owned-invariant verdict the whole-corpus agreement test can
  compare against the validator, and it catches a table-versus-real-drafts
  mislabel: the `by-chapter-sum-mismatch` variant (override `current=1`, drafts
  untouched) is named `by-chapter-sum` by the live oracle (the table is
  inconsistent) but is NOT named `gate-ratio-consistent` (the live ratio is
  unchanged), exactly as the validator labels it — the precise decoupling the
  reroute exists to verify. Date/Author: 2026-06-23, planning agent.

- Decision: For invariants the validator does not own (the five disk-evidence
  names), the live-draft agreement is asserted **only** after restricting both
  verdicts to `PURE_STATE_INVARIANT_NAMES`. Rationale: The validator is
  disk-blind by construction (boundary locked by 2.1.2 / 2.1.4); a
  disk-evidence variant must yield two empty restricted sets that agree, not a
  spurious failure. Date/Author: 2026-06-23, planning agent.

- Decision: The live oracle overrides the **three** disk-reconcilable owned
  invariants and reuses the spec-keyed `corpus_check` (restricted to the owned
  set) for the remaining five non-disk-derived owned invariants. The three it
  computes itself are: `gate-ratio-consistent` (gate booleans vs the live
  drafted-words ratio), `consecutive-clean-within-drafted` (the
  `consecutive_clean` counter vs the live drafted-chapters count), and
  `by-chapter-sum` (the table-internal `sum(by_chapter) == current` coherence
  read — see the next decision for why this one is table-internal, not "live").
  Rationale: The developers' guide (lines 323-334) names BOTH
  `gate-ratio-consistent` AND `consecutive-clean-within-drafted` as pure-state
  proxies for a real disk quantity, and closes "reconciling the proxy against a
  live draft count is task 2.1.3's on-disk cross-check" — *both* proxies, not
  one. Round 2 reconciled only the gate ratio and left
  `consecutive-clean-within-drafted` on its table basis (the round-2 review
  B1-r2 overclaim). The validator computes the drafted-chapters proxy from the
  table (`validate.py::_check_consecutive_clean_within_drafted`, line 187,
  counts `by_chapter` entries `> 0`), so a `by_chapter_override` that omits a
  chapter with a positive `draft.md` would mislabel the drafted-chapters count
  and slip through if the oracle also read the table. Reconciling it against
  the count of present positive-token `draft.md` bodies closes that gap
  (round-2 pre-mortem). The remaining five owned invariants (`phase-in-enum`,
  `completed-prefix`, `consecutive-clean-within-target`,
  `convergence-target-at-least-one`, `cursor-coherent`) are pure-state and not
  disk-derived; the spec is the right source for them and re-deriving them buys
  nothing. The cross-check's independence lives in the two **live-draft** proxy
  reconciliations (`gate-ratio-consistent`,
  `consecutive-clean-within-drafted`), which is where the live disk read
  replaces the table read. Date/Author: 2026-06-23, planning agent.

- Decision: The live oracle's signature is `live_draft_owned(spec, working_dir)`
  — the same `(spec, working_dir)` shape as `corpus_check`, NOT the
  `working_dir`-only form round 2 prescribed. Rationale: Step 5 reuses
  `corpus_check` for the five non-disk-derived owned invariants, and
  `corpus_check(spec, working_dir)` reads `spec` fields (`phase_current`,
  `phase_completed`, `consecutive_clean`, `convergence_target`,
  `current_chapter`/`current_scene`/`current_beat`) that a `working_dir`-only
  oracle would have to reconstruct from `state.toml` itself — work the round-2
  plan never specified, and an unnecessary second parser (round-2 review
  B2-r2). Both corpus fixtures that feed the whole-corpus test already hand back
  `(spec, working_dir)` pairs (`coherent_oracle_cases` returns `(spec, Path)`,
  `incoherent_tree` returns `(spec, Path, expected)`;
  `tests/corpus_fixtures.py` lines 176-203 and 221-253), so threading the spec
  costs nothing. Consequence stated plainly: the live oracle is genuinely
  *independent of the spec* only for the two live-draft proxy invariants
  (`gate-ratio-consistent`, `consecutive-clean-within-drafted`); for the
  table-coherence `by-chapter-sum` it is independent of the spec (it reads only
  the table) but not "live"; and for the other five owned invariants it derives
  the verdict from the spec via `corpus_check`, so it is NOT spec-independent
  there. That is acceptable because the cross-check's whole purpose — catching
  a table-versus-real-drafts mislabel — lives entirely in the two live-draft
  proxies, which read disk and never the spec. Date/Author: 2026-06-23,
  planning agent.

- Decision: cuprum plays no part in this task.
  Rationale: The corpus materialises trees under `tmp_path` and both checkers
  read files directly (`tomllib` / `load_state` / `draft.md` text); no
  subprocess or external executable is invoked, so the cuprum catalogue
  boundary is irrelevant. Verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` (`ProgramCatalogue` is a
  process allowlist) and `program.py` — cuprum's surface is cataloguing,
  allowlisting, and running allowlisted programs, none of which this filesystem
  agreement test performs. Round-1 review confirmed this exclusion is correct.
  Date/Author: 2026-06-23, planning agent.

## Outcomes & retrospective

Completed (2026-06-23, implementation agent):

- The live-draft agreement test `test_live_draft_agreement_over_whole_corpus`
  covers every coherent tree (baseline plus eleven phase states) and every
  incoherent variant (parse-rejection-aware, owned-restricted). The self-test
  `test_live_draft_counts_equal_honest_draft_bases` and the proxy-decoupling test
  `test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling` round out the
  module.
- The live-draft oracle reads only the `draft.md` bodies for both its
  drafted-words total and its drafted-chapters count (via `live_draft_counts`);
  it reads `[word_counts]` only for the table-internal `by-chapter-sum` coherence
  and
  `[gates.knitting]` / `[drafting.critic].consecutive_clean` for the booleans and
  counter it reconciles — never to derive either live quantity. Both proxies
  (`gate-ratio-consistent` against the live words ratio,
  `consecutive-clean-within-drafted` against the live chapter count) are reconciled
  against the live drafts; the self-test pins both live numbers to the honest-draft
  bases.
- No table-versus-draft discrepancy surfaced on either proxy: the validator and
  the live-draft oracle agree on every corpus tree, as expected with
  2.1.2/2.1.4/1.3.2 merged.
- `make all` is green (298 passed); `make markdownlint` and `make nixie` pass on
  the touched Markdown (this execplan and the developers' guide).

Deviation: the live oracle was placed in a **new** sibling module
`tests/working_corpus/_live_draft.py` rather than appended to `_oracle.py`.
Appending breached the 400-line module cap (`_oracle.py` reached 444 lines,
tripping `pylint C0302`). The plan's preferred corpus-package path is otherwise
honoured: `live_draft_owned`/`live_draft_counts` are re-exported from the
package `__init__` and fixtured in `corpus_fixtures.py`. The shared parse helpers
moved to `tests/_state_corpus_support.py` (the Risks-section sibling-module
prescription).

Process note: `make fmt`'s `mdformat-all` step reflowed every Markdown file under
`docs/`; that spurious churn was stashed aside and excluded from both commits, as
prior tasks on this repo recorded doing.

### Fix round 1 (2026-06-23, fix agent) — discriminating divergent-table tree

The dual review returned one BLOCKER (Telefono + Doggylump): the live-draft
oracle was live in its *code* but no test discriminated a live `draft.md` read
from a `[word_counts]`-table read. A mutation probe replacing the body of
`live_draft_counts` with a table-based read (`sum(by_chapter.values())`, count of
`by_chapter` entries `> 0`) left all three tests green, because no §1.3.2 corpus
tree sets `by_chapter_override`, so on every corpus tree the table and the drafts
are numerically equal and `live == table-based` for both proxy bases. The
`test_live_draft_counts_equal_honest_draft_bases` self-test also failed to
discriminate, since `sum(draft_words) == sum(by_chapter)` on every coherent tree.
The guard the plan's Risks section and Decision Log foresaw was therefore inert:
no delivered tree constructed the table-versus-drafts divergence that would
surface it.

Fix (test-only, in scope — no production code touched):

- Added a module-local `divergent_table_tree` fixture in
  `tests/test_validate_state_live_draft.py` that builds the one tree the corpus
  lacks: two chapters drafted at 4000 words each (live: 8000 words, two drafted
  chapters) against an 80000 target, with `by_chapter_override={"01": 30000,
  "02": 30000, "03": 30000}` (table: 90000 words, three entries `> 0`) and
  `current_words_override=90000` so `sum(by_chapter) == current` keeps
  `by-chapter-sum` silent. All three knitting gates are `True` and
  `consecutive_clean=3` with `convergence_target=3`. The tree is built through
  the existing corpus constructor and builder fixtures (`make_chapter_spec`,
  `make_working_tree_spec`, `build_tree`, `phase_names`), so the corpus is still
  consumed by fixture name and never by a runtime value import. The three
  constructor/builder callables are bundled through a `corpus_builders` fixture
  to keep the fixture's parameter list within the four-argument lint gate
  (mirroring the existing `compile_probe` bundling precedent).
- Added `test_live_draft_discriminates_table_from_drafts` asserting (a)
  `live_draft_counts(working_dir) == (8000, 2)` — the **draft**-derived numbers,
  never the table-derived `(90000, 3)` — and (b) the live-draft oracle and the
  table-reading §5.2 validator **disagree** on both perturbed proxies: the live
  oracle names `{gate-ratio-consistent, consecutive-clean-within-drafted}` (the
  live 0.10 ratio contradicts the all-`True` gates; `consecutive_clean=3`
  exceeds the two live drafted chapters), while the validator, reading the
  table's 1.125 ratio and three drafted entries, names neither.
- Verified the mutation is now killed: re-applying the review's table-based mutant
  to `live_draft_counts` turns the new test RED
  (`assert (90000, 3) == (8000, 2)`); the source was restored unchanged
  afterwards.
- Updated the module docstring to record that no corpus tree sets
  `by_chapter_override`, so the whole-corpus agreement test alone cannot tell a
  live read from a table read, and that the new test closes that gap.

`make all` is green (299 passed, up from 298 by the new test). The fixture was
deliberately kept module-local rather than added to `tests/corpus_fixtures.py`,
because adding it there pushed that plugin to 438 lines and tripped the 400-line
module cap (`pylint C0302`); module-locality also matches the fixture's single
consumer (one test) per the pytest fixture-locality principle.

## Context and orientation

A reader new to this repository needs the following map. All paths are
repository-relative to the worktree root
(`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-3`).

- `novel_ralph_skill/state/validate.py` — the §5.2 **pure-state** validator.
  `validate_state(state: State) -> tuple[Violation, ...]` returns the owned
  invariant names a parsed `State` violates. The eight owned name constants and
  the tuple `PURE_STATE_INVARIANT_NAMES` are defined here and re-exported from
  `novel_ralph_skill/state/__init__.py`.
  `_GATE_THRESHOLDS = (0.30, 0.50, 0.80)` is the validator's gate-threshold
  source of truth. Its `_check_gate_ratio_consistent` numerator is
  `sum(by_chapter.values())` *from the parsed table* (line 241), and its
  `_check_consecutive_clean_within_drafted` ceiling is the count of
  `by_chapter` entries `> 0` *from the parsed table* (line 187) — the two
  table-derived proxies the live oracle reconciles against the drafts.
- `novel_ralph_skill/state/parse.py` — `load_state(path) -> State` parses
  `state.toml` into the typed `State`; it raises (the production exit-3
  channel) on a structurally bad or out-of-enum `state.toml`. `_word_counts`
  (lines 161-172) reads `[word_counts].target`/`.current`/`.by_chapter`
  straight through into `WordCounts` — the same three keys a naive disk re-read
  would consume, which is why the live oracle must read the **drafts**, not the
  table.
- `tests/working_corpus/` — the §1.3.2 on-disk fixture corpus package.
  - `_specs.py` — the `ChapterSpec` / `WorkingTreeSpec` dataclasses;
    `draft_body(n)` (lines 205-214) returns exactly `n` whitespace-separated
    `word` tokens (empty for `n <= 0`); `derive_by_chapter` / `derive_current`;
    `GATE_THRESHOLDS = (0.30, 0.50, 0.80)`; `chapter_dir_name(n)` (`chapter-NN`)
    and `by_chapter_key(n)` (`"NN"`).
  - `_builder.py` — `build_working_tree(spec, dest) -> Path` materialises the
    tree; `_write_chapter` (line 169-172) writes
    `draft_body(chapter.draft_words)` into `working/manuscript/chapter-NN/draft.md`
    when `write_draft` is true (the default), suppressing it entirely when false.
  - `_oracle.py` — `corpus_check(spec, working_dir) -> tuple[str, ...]` returns
    the `CORPUS_INVARIANT_NAMES` a tree violates. `_check_by_chapter_sum` (lines
    108-119) already reads `[word_counts]` from the materialised `state.toml`;
    `_check_gate_ratio_consistent` (lines 190-203) uses `sum(chapter.draft_words)`
    — the honest-draft numerator the live oracle reproduces from disk.
  - `_library.py` — `PHASE_STATES` (the eleven coherent phase trees) and
    `COHERENT_BASELINE` (the mid-drafting tree). Drafting-era trees carry
    `draft_words=(24000, 24000, 20800)` summing to 68800 of an 80000 target (ratio
    0.86, all three gates crossed); pre-drafting phases have `chapters=()`, so no
    drafts on disk and a live count of 0 (ratio 0, all gates false).
  - `_variants.py` —
    `INCOHERENT_VARIANTS: dict[str, tuple[WorkingTreeSpec, str]]`,
    each variant breaking exactly one named invariant.
    `by-chapter-sum-mismatch` sets `current_words_override=1` (table inconsistent,
    drafts untouched); `gate-true-below-threshold` shrinks each `draft_words` to
    4000 and forces `done_80=True` against the honest ratio 0.15. No variant sets
    `by_chapter_override`.
- `tests/corpus_fixtures.py` — the pytest plugin re-exposing every corpus datum
  as a fixture: `coherent_oracle_cases` (`(spec, working_dir)` for the baseline
  and the eleven phase states), `incoherent_variant_names`,
  `incoherent_tree(name) -> (spec, working_dir, expected_name)`, `check_corpus`
  (the `corpus_check` oracle), `corpus_invariant_names`, and
  `corpus_gate_thresholds`.
- `tests/conftest.py` — registers `corpus_fixtures` via `pytest_plugins` and
  re-exports the spec types under `TYPE_CHECKING`.
- `tests/test_validate_state_corpus.py` — the **existing** validator/corpus
  agreement suite (237 lines). It restricts both verdicts to
  `PURE_STATE_INVARIANT_NAMES`, drives the validator from the on-disk
  `state.toml`, handles the parse-enforced `phase-in-enum` case
  (`_load_succeeds`, `_PARSE_ENFORCED_INVARIANTS`, `_PARSE_ERRORS`), pins the
  gate thresholds (`test_corpus_gate_thresholds_equal_production`), pins the
  vocabulary (`test_owned_names_equal_corpus_vocabulary`), and pins the scope
  boundary (`test_validator_never_emits_deferred_names`). It is the host (or
  sibling) for the new live-draft assertions and supplies the helpers they
  reuse.

Terms used below:

- **owned / pure-state invariants** — the eight names `validate_state` reports:
  `phase-in-enum`, `completed-prefix`, `by-chapter-sum`,
  `consecutive-clean-within-target`, `convergence-target-at-least-one`,
  `consecutive-clean-within-drafted`, `cursor-coherent`, `gate-ratio-consistent`
  (`PURE_STATE_INVARIANT_NAMES`).
- **disk-evidence invariants** — the five names the validator never emits;
  deferred to reconciliation task 2.3.2.
- **live draft count** — the two drafted quantities recovered from the on-disk
  `draft.md` bodies: the **drafted-words total** (whitespace-split token count
  per present chapter, summed) and the **drafted-chapters count** (number of
  present `draft.md` bodies with a positive token count); both independent of
  the `[word_counts]` table. This is the design's "live draft count"
  (developers-guide line 333), against which both proxies are reconciled.
- **proxy invariant** — an owned invariant whose validator predicate
  approximates a real disk quantity from the `[word_counts]` table:
  `gate-ratio-consistent` (numerator `sum(by_chapter.values())`, proxy for
  drafted words) and `consecutive-clean-within-drafted` (ceiling = count of
  `by_chapter` entries `> 0`, proxy for drafted chapters) are the two the guide
  names. This task reconciles **both** against the live draft count — the gate
  ratio against the live drafted-words total, the `consecutive_clean` ceiling
  against the live drafted-chapters count.
- **deliberate twin** — the validator's predicate and the oracle's same-named
  predicate are independent copies of the same rule, kept separate on purpose
  so the oracle is a true cross-check.

## Plan of work

The work is a small green-only cycle over the test tree, sequenced so the
live-draft oracle and the acceptance test it satisfies land together in one
gate-passing commit. No production code changes.

- Stage A (Work item 1): add the live-draft oracle that recomputes the
  drafted-words total and the drafted-chapters count from `draft.md` bodies and
  cross-checks the gate booleans against the live ratio, the
  `consecutive_clean` counter against the live drafted-chapters count, and the
  `[word_counts]` table-coherence half, returning an owned-invariant verdict;
  add the self-test pinning both live numbers to the oracle's honest-draft
  bases.
- Stage B (Work item 2): add the whole-corpus live-draft agreement test keyed on
  `CORPUS_INVARIANT_NAMES` and the coherent-tree pin. Author Work items 1 and 2
  so they pass together, and commit them in **one green commit**.
- Stage C (Work item 3): correct the developers' guide so its "reconcile the
  proxy
  against a live draft count" sentence describes the delivered live-draft test,
  and run the full Markdown gates.

Each stage ends with validation; do not proceed past a failing stage. Stages A
and B share a single commit (see Work item 2's "Commit").

## Work items

### Work item 1 — the live-draft oracle and its honest-draft self-test

What it implements: the design's definition of task 2.1.3 — "reconciling the
proxy against a **live draft count**" (developers-guide lines 329-334), the
genuinely-independent on-disk source the roadmap reroute requires
(`docs/roadmap.md` lines 377-393). Design references:
`docs/novel-ralph-harness-design.md` §5.2 invariants 3 and 7 (lines 438,
454-456) and §9 (the property-and-agreement verification strategy, lines
671-711); `docs/execplans/roadmap-1-3-2.md` advisory A5 and the Outcomes
honest-draft note (lines 685-686).

Docs to read first:

- `docs/developers-guide.md` "Invariant validation (`novel-state check`)", lines
  286-360 — especially lines 323-334 (the two pure-state proxies and the
  live-draft-count promise this task discharges) and lines 336-344 (the
  deliberate-twin policy the live oracle must respect).
- `docs/novel-ralph-harness-design.md` §5.2 (lines 430-456) and §9 (lines
  671-711).
- `tests/working_corpus/_oracle.py` — `_check_by_chapter_sum` (lines 108-119,
  the
  table read of invariant 3), `_check_gate_ratio_consistent` (lines 190-203,
  the honest-draft drafted-words numerator the live oracle reproduces from
  disk), `_check_consecutive_clean_within_drafted` (lines 142-149, the
  honest-draft drafted-chapters ceiling the live oracle reproduces from disk),
  and `corpus_check` (lines 288-312, the `(spec, working_dir)` entry point the
  live oracle reuses for the five non-disk-derived owned invariants).
- `novel_ralph_skill/state/validate.py` — `_check_gate_ratio_consistent`
  (lines 228-249, table numerator at line 241) and
  `_check_consecutive_clean_within_drafted` (lines 176-193, table ceiling at
  line 187) — the two validator proxies the live oracle reconciles.
- `tests/working_corpus/_specs.py` `draft_body` (lines 205-214) and
  `chapter_dir_name`/`by_chapter_key`, and `_builder.py` `_write_chapter`
  (lines 157-178) — so the live oracle reads the right files and reproduces the
  token count exactly.
- `skill/novel-ralph/references/state-layout.md` lines 38-39, 54-56, 115,
  174-177
  — the on-disk `chapter-NN/draft.md` layout, the `[word_counts].by_chapter`
  string-key form, and the `[gates.knitting]` threshold layout.

Skills to load:

- `python-router`, then `python-testing` (pytest fixtures, parametrization, the
  fast-unit boundary) and `python-data-shapes` (the small typed return of the
  live oracle).
- `leta` for navigating the validator, parser, oracle, builder, and fixtures by
  symbol (`leta show validate_state`, `leta refs corpus_check`,
  `leta show draft_body`, `leta show build_working_tree`).
- `en-gb-oxendict` for docstring prose.

Change — add the live-draft oracle. Go/no-go on placement (decide here; the
default is the corpus-package path because it keeps the test module within the
400-line cap and reads as a genuine corpus capability):

The signature is **fixed by this plan** (resolving round-2 review B2-r2): the
live oracle is `live_draft_owned(spec, working_dir)` — the same
`(spec, working_dir)` shape as `corpus_check` — NOT a `working_dir`-only form.
Step 5 reuses `corpus_check(spec, working_dir)` for the five non-disk-derived
owned invariants, and `corpus_check` reads spec fields the oracle would
otherwise have to re-parse from `state.toml`; the corpus fixtures already hand
back `(spec, working_dir)` at every call site (see Surprises & discoveries), so
the spec is free. The implementer must NOT choose a `working_dir`-only
signature.

- Preferred (corpus-package path): add an **additive** entry point to
  `tests/working_corpus/_oracle.py`,
  `live_draft_owned(spec: WorkingTreeSpec, working_dir: Path) -> set[str]`,
  leaving the existing spec-keyed `corpus_check`, the predicates, and
  `CORPUS_INVARIANT_NAMES` untouched; expose it through a `check_live_draft`
  fixture in `tests/corpus_fixtures.py`. Re-export the callable (and the
  `live_draft_counts` helper below) from `tests/working_corpus/__init__.py`
  beside `corpus_check` so the fixture imports it by name.
- Alternative (test-local path): if the implementer judges the helper purely
  test-local, add it as a module-private
  `_live_draft_owned(spec: WorkingTreeSpec, working_dir: Path) -> set[str]` in
  `tests/test_validate_state_corpus.py`. Choose this only if it does not breach
  the 400-line cap; otherwise take the corpus-package path.

Either way, the live oracle:

1. reads the materialised `working_dir / "state.toml"` with `tomllib` once, for
   the `[word_counts].target`, the `[word_counts].current`, the
   `[word_counts].by_chapter` table, and the `[gates.knitting]` booleans (it
   reads the table only to *check it against the drafts*, never to derive
   either live quantity);
2. computes **both live quantities** by globbing
   `working_dir / "manuscript" / "chapter-*" / "draft.md"`, reading each
   present file as UTF-8, and taking its whitespace-split token count
   (`len(text.split())`):
   - the **live drafted-words total** is the sum of those token counts; and
   - the **live drafted-chapters count** is the number of those `draft.md`
     bodies
     whose token count is `> 0`.
   A chapter with no `draft.md` (the `write_draft=False` case) and a chapter
   with an empty `draft.md` (`draft_words=0`, zero tokens) both contribute
   nothing to either quantity, mirroring the builder and matching the
   validator's `> 0` filter exactly. Factor this into a single
   `live_draft_counts(working_dir) -> tuple[int, int]` helper (returning
   `(words_total, chapters_count)`) so both the oracle and the self-test read
   disk through one path and cannot diverge;
3. names `by-chapter-sum` when `sum(by_chapter.values()) != current` (the
   table's
   internal invariant-3 consistency — the same comparison the existing
   `_check_by_chapter_sum` makes; this is the table-coherence half, which has
   no "live" analogue — invariant 3 is table-internal — and is kept distinct
   from the two live cross-checks below);
4. names `gate-ratio-consistent` when, with `target > 0`, any `[gates.knitting]`
   boolean disagrees with `(live_words_total / target) >= threshold` for its
   threshold in `GATE_THRESHOLDS`; short-circuits to "consistent" when
   `target <= 0` (mirroring the validator's totality guard). The numerator is
   the **live** drafted-words total, never `sum(by_chapter.values())`;
5. names `consecutive-clean-within-drafted` when the `state.toml`
   `[drafting.critic].consecutive_clean` counter exceeds the **live
   drafted-chapters count** (`consecutive_clean > live_chapters_count`). Read
   `consecutive_clean` from the parsed `state.toml` as
   `state["drafting"]["critic"]["consecutive_clean"]` (the table the builder
   writes it to — `_builder.py` line 68 — and the same field the validator
   reads via `state.drafting.critic.consecutive_clean`; it is part of the state
   under test, not a proxy), and compare it against the live drafted-chapters
   count, never against the count of `by_chapter` entries `> 0`. This is the
   second proxy reconciliation the guide names (lines 329-332) and the one
   round 2 omitted;
6. for the **other five owned invariants** (`phase-in-enum`, `completed-prefix`,
   `consecutive-clean-within-target`, `convergence-target-at-least-one`,
   `cursor-coherent`), reuses the spec-keyed `corpus_check(spec, working_dir)`
   verdict restricted to the owned set (those five are pure-state, not
   disk-derived, and the spec renders them verbatim); the live oracle
   **overrides** only the three disk-reconcilable names (`by-chapter-sum`,
   `gate-ratio-consistent`, `consecutive-clean-within-drafted`). Document in
   the docstring that the live oracle's *spec-independence* is concentrated in
   the two live-draft proxy reconciliations (`gate-ratio-consistent`,
   `consecutive-clean-within-drafted`); `by-chapter-sum` is independent of the
   spec but table-internal, not live; the other five are derived from the spec
   via `corpus_check` and are deliberately not spec-independent;
7. returns the owned-invariant `set[str]` the tree violates under the live
   reading.

Document the honest-draft bases in the helper docstring: the live drafted-words
total is the honest-draft numerator (`sum(chapter.draft_words)`) and the live
drafted-chapters count is the honest-draft ceiling
(`sum(1 for chapter in spec.chapters if chapter.draft_words > 0)`), both
recovered from disk, NEITHER taken from `[word_counts].by_chapter` — so a future
`by_chapter_override` variant that separates the table from the drafts on
either proxy is a finding to investigate, not a test to align.

Tests this work item adds:

- `test_live_draft_counts_equal_honest_draft_bases` — for every
  `coherent_oracle_cases` tree, call `live_draft_counts(working_dir)` and
  assert **both** numbers equal their honest-draft bases: the live
  drafted-words total equals
  `sum(chapter.draft_words for chapter in spec.chapters)` (the oracle's
  invariant-7 numerator) AND the live drafted-chapters count equals
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)` (the
  oracle's invariant-4c ceiling). This pins both live-count bases to the
  honest-draft bases the design names, so neither cross-check can silently
  change what number it reconciles. Expose the live reader as the
  `live_draft_counts(working_dir) -> tuple[int, int]` helper beside
  `live_draft_owned` (additive), used by both the oracle and this test;
  re-export and fixture it the same way as `live_draft_owned`.

Per AGENTS.md "Python verification and testing", these are fast unit/agreement
tests over generated fixtures, not a property suite — the property suite over
generated states is 2.1.2's `tests/test_validate_state_property.py`, which this
task does not duplicate (design §9 names the validator's verification as
property-plus-agreement; this is the agreement half). No snapshot is added; the
verdict comparison is a semantic assertion, which AGENTS.md prefers over
snapshot-only coverage for assertable logic. No behavioural (`pytest-bdd`) test
is added: §9's behavioural lane covers harness-facing flows, not the internal
validator/oracle agreement.

Validation: `make test` — the new
`test_live_draft_counts_equal_honest_draft_bases` passes and every existing
test stays green. (The whole-corpus agreement test lands in Work item 2; do not
commit until Work item 2 is also green — see Work item 2's "Commit".)

### Work item 2 — the whole-corpus live-draft agreement test (keyed on `CORPUS_INVARIANT_NAMES`)

What it implements: roadmap task 2.1.3 Success clause — "for every §1.3.2
corpus fixture the §5.2 validator's verdict, run against the materialised
`state.toml`, matches the oracle's `CORPUS_INVARIANT_NAMES` labels exactly",
with the oracle now the live-draft oracle so the match is against a genuinely
independent source. Design references: `docs/novel-ralph-harness-design.md`
§5.2 and §9; `docs/roadmap.md` lines 390-393.

Docs to read first:

- `tests/test_validate_state_corpus.py` end to end, so the new test reuses
  `_validator_verdict`, `_load_succeeds`, `_PARSE_ERRORS`, and
  `_PARSE_ENFORCED_INVARIANTS` rather than re-deriving them. If the
  sibling-module path is taken (cap reached), lift those four into a small
  support module (for example `tests/_state_corpus_support.py`) imported by
  both modules and note the move in `Decision Log`.

Skills to load: `python-router` then `python-testing`; `leta` for navigation.

Change: add a single named test, for example
`test_live_draft_agreement_over_whole_corpus`, that:

- accepts the `coherent_oracle_cases`, `incoherent_variant_names`,
  `incoherent_tree`, and the `check_live_draft` fixture (Work item 1's oracle).
  Because the live oracle is `live_draft_owned(spec, working_dir)`, the test
  threads **both** the spec and the working dir into it; both already arrive
  together from the fixtures (`coherent_oracle_cases` yields
  `(spec, working_dir)`, `incoherent_tree(name)` yields
  `(spec, working_dir, expected)`);
- for each coherent `(spec, working_dir)`: asserts the validator's owned verdict
  is empty **and** `check_live_draft(spec, working_dir)` (the live-draft
  oracle's owned verdict) is empty;
- for each incoherent variant `(spec, working_dir, expected)`: if the tree is
  parse-rejected (`not _load_succeeds(working_dir)`), asserts the live-draft
  oracle's owned verdict is a non-empty subset of `_PARSE_ENFORCED_INVARIANTS`
  (the parser enforces the owned label before the validator runs; note the live
  oracle's invariant-7/4c/3 reads use `tomllib`, which tolerates the
  out-of-enum-phase tree, but the agreement is asserted only on the
  parse-enforced owned subset); otherwise asserts the validator's owned verdict
  equals the live-draft oracle's owned verdict, and — for a variant whose
  `expected` is an owned name — that the shared verdict is exactly `{expected}`
  (the "rejected on its one named invariant" clause), while a variant whose
  `expected` is a disk-evidence name yields two empty owned sets.

Also add `test_live_draft_oracle_agrees_with_validator_on_proxy_decoupling` (or
fold the assertion into the agreement test with a comment) confirming the
load-bearing decoupling: the `by-chapter-sum-mismatch` variant (override
`current=1`, drafts untouched) is named exactly `{by-chapter-sum}` by the
live-draft oracle — NOT also `gate-ratio-consistent` (the live drafted-words
ratio is unchanged) and NOT `consecutive-clean-within-drafted` (the live
drafted-chapters count is unchanged) — matching the validator. This is the
precise table-versus-draft mislabel the reroute exists to catch, and asserting
both live proxies stay silent on the table-only override pins that the
drafted-chapters proxy is genuinely live (it would also stay silent if it had
been left on the table basis, so this assertion alone does not prove liveness —
the `live_draft_counts` self-test and the docstring carry that proof; this
assertion proves the live proxy does not *over*-fire on a pure table mismatch).

Tests this work item adds: the whole-corpus agreement test and the
proxy-decoupling assertion. Fast unit/agreement tests per AGENTS.md.

Validation: `make test` — the new agreement test passes and the existing
`test_incoherent_agreement_restricted_to_owned`,
`test_coherent_trees_pass_the_validator`,
`test_by_chapter_sum_variant_names_only_by_chapter_sum`, and
`test_validator_never_emits_deferred_names` stay green.

Commit: **one green commit** containing Work items 1 and 2 together (the
live-draft oracle, its fixture, the honest-draft self-test, the whole-corpus
agreement test, and the proxy-decoupling assertion). Per AGENTS.md lines 100
and 108 every commit must pass all quality gates, so the failing acceptance
test never exists in isolation; gate this commit with the full `make all` (Work
item 3's Markdown gates follow in its own commit). en-GB body, referencing
roadmap task 2.1.3, the reroute, and design §5.2/§9.

### Work item 3 — correct the developers' guide to describe the delivered cross-check

What it implements: the documentation half of the acceptance — the guide's
"reconcile the proxy against a live draft count" promise (developers-guide
lines 329-334) now points at the delivered live-draft test, stating exactly
what was delivered (no overclaim). Design references:
`docs/novel-ralph-harness-design.md` §5.2; developers-guide "Invariant
validation".

Docs to read first:

- `docs/developers-guide.md` lines 323-344 — the proxy paragraph ending
  "reconciling the proxy against a live draft count is task 2.1.3's on-disk
  cross-check" (the sentence to update) and the deliberate-twin policy
  paragraph.
- `docs/documentation-style-guide.md` for the prose conventions; AGENTS.md
  Markdown guidance (80-column prose wrap, dash bullets).

Skills to load: `en-gb-oxendict` for the guide prose; `python-router`/`leta`
for any symbol names cited.

Change: update the developers-guide "Invariant validation" section so the
sentence promising task 2.1.3's on-disk cross-check now describes the delivered
test. The edited prose must:

- name the live-draft agreement test
  (`tests/test_validate_state_corpus.py::test_live_draft_agreement_over_whole_corpus`
  or its sibling-module location);
- state that the cross-check recomputes **both** live quantities from the
  on-disk
  `draft.md` bodies (the drafted-words total and the drafted-chapters count,
  both independent of the `[word_counts]` table) and reconciles **both** proxy
  invariants against them: `gate-ratio-consistent` against the live
  drafted-words ratio, and the `consecutive-clean-within-drafted` ceiling
  against the live drafted-chapters count. This wording is now accurate because
  both proxies are reconciled (round-2 review B1-r2 corrected); do not write
  "the two proxies" unless both are in fact reconciled — they are;
- state the whole-corpus full-vocabulary agreement keyed on
  `CORPUS_INVARIANT_NAMES`, and that the live oracle's invariant-7 numerator
  and its invariant-4c ceiling are both the honest-draft bases (so a future
  `by_chapter_override` variant that separates the table basis from the draft
  basis on either proxy is a finding to investigate, not a drift to paper over);
- be precise about scope, claiming neither more nor less than delivered: the
  cross-check reconciles the gate booleans and the `consecutive_clean` counter
  against the live drafts, and checks the `[word_counts]` table's internal
  `by-chapter-sum` coherence; it does NOT "live-reconcile" `by-chapter-sum`
  (invariant 3 is table-internal, with no live analogue — round-2 review A4),
  and it does NOT re-run the validator as the oracle (the other five owned
  invariants come from the spec-keyed corpus oracle).

Keep the prose en-GB Oxford spelling and wrapped at 80 columns.

Tests this work item adds: none (documentation only). The behaviour is already
locked by Work items 1 and 2.

Validation:

- `make all` — `build check-fmt lint typecheck test` all pass (Ruff format and
  lint, `interrogate` 100% docstring coverage on any new test/oracle
  docstrings, Pylint via the PyPy shim, `ty` typecheck, and the full pytest run
  under `pytest-xdist`). Run it again here even though Work item 2 already ran
  it, to confirm nothing regressed.
- Because this work item edits Markdown (`docs/developers-guide.md` and this
  execplan): `make markdownlint` and `make nixie` both pass.

Commit: one commit, en-GB body, referencing roadmap 2.1.3. Mark the roadmap
checkbox `[x]` for 2.1.3 only in the merge/wrap step per the workflow's roadmap
discipline (do not pre-tick it mid-plan).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-3`.

Work items 1 and 2 (one green commit):

```bash
# After authoring the live-draft oracle, its fixture, the honest-draft self-test,
# the whole-corpus agreement test, and the proxy-decoupling assertion:
make all
# Expect: build, check-fmt, lint, typecheck, and test all pass; the new
# test_live_draft_counts_equal_honest_draft_bases,
# test_live_draft_agreement_over_whole_corpus, and the proxy-decoupling
# assertion pass; every previously green test stays green.
git add -A && git commit   # en-GB body referencing roadmap 2.1.3 + reroute
```

Work item 3 (docs + full gate):

```bash
make all
make markdownlint
make nixie
# Expect: all green. make all runs build, check-fmt, lint (ruff + interrogate +
# pylint), typecheck (ty), and test (pytest -n auto).
git add -A && git commit   # en-GB body referencing roadmap 2.1.3
```

Show a short transcript of the final `make all` tail in `Progress` as success
evidence.

## Validation and acceptance

Acceptance is behavioural over the test suite:

- The new `test_live_draft_agreement_over_whole_corpus` passes and covers every
  coherent tree (baseline plus the eleven phase states) and every incoherent
  variant (`incoherent_variant_names`).
- For every coherent tree, both the validator's owned verdict and the live-draft
  oracle's owned verdict are empty.
- For every incoherent variant whose label is an owned name, the validator's
  owned
  verdict, the live-draft oracle's owned verdict, and `{expected}` are the same
  single-name set; for a variant whose label is a disk-evidence name, both
  owned verdicts are empty; for the parse-enforced `phase-not-in-enum` variant,
  the tree is parse-rejected and the oracle's owned label is the parse-enforced
  `phase-in-enum`.
- The `by-chapter-sum-mismatch` variant is named exactly `{by-chapter-sum}` by
  the
  live-draft oracle (not `gate-ratio-consistent`, not
  `consecutive-clean-within-drafted`) — the table-versus-draft decoupling guard
  for both proxies.
- `test_live_draft_counts_equal_honest_draft_bases` passes: on every coherent
  tree
  the live drafted-words total equals `sum(chapter.draft_words)` and the live
  drafted-chapters count equals
  `sum(1 for chapter in spec.chapters if chapter.draft_words > 0)`.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new agreement test, the honest-draft self-test,
  and the proxy-decoupling assertion pass; no existing test regresses.
- Lint/typecheck: `make all` is green (Ruff format+lint, `interrogate` 100%,
  Pylint, `ty`).
- Markdown: `make markdownlint` and `make nixie` pass (this plan and the
  developers-guide edit).
- No production code under `novel_ralph_skill/` changed.
- Every commit passes all quality gates (no deliberately-red commit).

Quality method: run `make all`, `make markdownlint`, and `make nixie` from the
worktree root; capture the tails in `Progress`.

## Idempotence and recovery

Every step is re-runnable. The test fixtures materialise trees under pytest's
`tmp_path`, which is fresh per test, so reruns never inherit a previous tree.
Adding a test, an oracle entry point, or a fixture is additive; if a stage's
validation fails, revert the stage's edit (`git checkout -- <file>`) and
reapply. No destructive operations. If a genuine validator/live-draft
disagreement surfaces (a real table-versus-draft mislabel), stop per the
production-change tolerance and escalate with the tree and both verdicts
recorded — do not edit production code to mask it.

## Interfaces and dependencies

Be prescriptive about the names that must exist at the end of the task. The
default (corpus-package) placement:

```python
# tests/working_corpus/_oracle.py — additive; corpus_check and the predicates
# and CORPUS_INVARIANT_NAMES stay unchanged:
def live_draft_counts(working_dir: Path) -> tuple[int, int]:
    """Return ``(drafted_words_total, drafted_chapters_count)`` from disk.

    Globs ``working_dir/manuscript/chapter-*/draft.md``, reads each present file,
    and takes its whitespace-split token count. The first element sums those
    counts (the honest-draft numerator ``sum(chapter.draft_words)`` recovered from
    disk); the second counts the bodies whose token count is ``> 0`` (the
    honest-draft ceiling ``sum(1 for c in chapters if c.draft_words > 0)``). Both
    are independent of the ``[word_counts]`` table, so they cross-check that table
    and the gate/consecutive-clean fields, not restate them.
    """
    ...


def live_draft_owned(spec: WorkingTreeSpec, working_dir: Path) -> set[str]:
    """Return the owned invariant names a tree violates under the live-draft read.

    Overrides the three disk-reconcilable owned invariants:
    ``by-chapter-sum`` (table ``sum(by_chapter) == current`` — table-internal, no
    live analogue), ``gate-ratio-consistent`` (gate booleans vs
    ``drafted_words_total / target`` against ``GATE_THRESHOLDS``), and
    ``consecutive-clean-within-drafted`` (``[drafting.critic].consecutive_clean``
    vs ``drafted_chapters_count``). It reuses the spec-keyed ``corpus_check(spec,
    working_dir)`` (restricted to the owned set) for the other five pure-state
    owned invariants. The invariant-7 numerator and the invariant-4c ceiling are
    BOTH honest-draft live quantities, NOT their ``[word_counts].by_chapter``
    table equivalents. The ``spec`` argument feeds only the ``corpus_check``
    reuse; the two live-draft proxy reconciliations read disk and never the spec.
    """
    ...
```

```python
# tests/corpus_fixtures.py — additive fixtures:
@pytest.fixture
def check_live_draft() -> cabc.Callable[[WorkingTreeSpec, Path], set[str]]:
    """Return the live-draft owned-invariant oracle ``(spec, working_dir)``."""
    return wc.live_draft_owned


@pytest.fixture
def live_draft_counts() -> cabc.Callable[[Path], tuple[int, int]]:
    """Return the live ``(drafted_words, drafted_chapters)`` reader for draft.md."""
    return wc.live_draft_counts
```

If instead the test-local placement is chosen (cap permitting), the end-state
names are module-private
`_live_draft_counts(working_dir: Path) -> tuple[int, int]` and
`_live_draft_owned(spec: WorkingTreeSpec, working_dir: Path) -> set[str]` in
`tests/test_validate_state_corpus.py`, consumed directly by the new tests. The
`(spec, working_dir)` signature is mandatory either way (round-2 review B2-r2);
do not adopt a `working_dir`-only form.

Dependencies, pinned to the locked versions already in the tree (no new
dependency is added):

- `pytest` and `pytest-xdist` — the test runner and parallelism (`make test`
  runs `pytest -n auto`); the new tests are ordinary fixture-driven unit tests
  with no shared mutable state, so they are xdist-safe (each builds its own
  `tmp_path` trees).
- `tomllib` (standard library) — parsing the materialised `state.toml` for the
  table-coherence read, the gate booleans, and the
  `[drafting.critic].consecutive_clean` counter, exactly as
  `_check_by_chapter_sum` already reads the table. `pathlib.Path.glob` and
  `str.split` (standard library) recover both live quantities (drafted-words
  total and drafted-chapters count).
- `novel_ralph_skill.state.load_state` / `validate_state` /
  `PURE_STATE_INVARIANT_NAMES` — the validator side of the cross-check (already
  imported by the existing suite).
- The corpus fixtures from `tests/corpus_fixtures.py` — consumed by name only.
- No subprocess, no external executable, and therefore **no cuprum**: the cuprum
  `ProgramCatalogue` boundary (cuprum 0.1.0) governs allowlisted process
  execution, which this task does not perform; the corpus reads and writes
  files under `tmp_path` directly. Verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` and `program.py`.

## Revision note

Round 3 (2026-06-23): resolved the round-2 design review's two remaining
blocking points. B1-r2 — the plan reconciled only `gate-ratio-consistent` and
left the second named proxy, `consecutive-clean-within-drafted`, on its table
basis, which the Work item 3 guide edit would have overclaimed. Fixed by
extending the live oracle to recompute the **drafted-chapters count** from the
present positive-token `draft.md` bodies and reconcile
`consecutive-clean-within-drafted` (`[drafting.critic].consecutive_clean`)
against it, so **both** proxies the guide names (lines 329-334) are now
reconciled against the live drafts; the self-test pins both live numbers to
their honest-draft bases, and Work item 3's wording is made precise (gate ratio
vs live words, consecutive-clean vs live chapters; `by-chapter-sum` is
table-internal, not "live"; the validator is not re-run as the oracle). B2-r2 —
the prescribed `live_draft_owned(working_dir)` signature could not reuse
`corpus_check(spec, working_dir)` as step 5 required. Fixed by pinning the
signature to `live_draft_owned(spec, working_dir)` in the plan (the corpus
fixtures already deliver `(spec, working_dir)` at every call site, so no spec
reconstruction is needed), updating the Interfaces block and Work item 2's
fixture wiring, and stating plainly that the oracle is spec-independent only
for the two live-draft proxy invariants, table-internal for `by-chapter-sum`,
and spec-derived for the other five. The live reader is now
`live_draft_counts -> (words_total, chapters_count)` and the self-test is
`test_live_draft_counts_equal_honest_draft_bases`. The cuprum exclusion and the
single-green-commit discipline are unchanged.

Round 2 (2026-06-23): rewritten to resolve the round-1 design review's five
blocking points. The central mechanism is now a **live-draft oracle** that
recomputes the drafted total from the on-disk `draft.md` bodies (whitespace
token count) and reconciles the `[word_counts]` table and the
`[gates.knitting]` booleans against that genuinely independent number,
replacing round 1's `[word_counts]`-table re-read (which consumed the same
bytes and arithmetic as the validator and so caught nothing — B1). The
invariant-7 numerator is pinned to the honest-draft basis the design decoupled
from `by_chapter` (B2), with a self-test and an explicit Decision-Log note so a
future `by_chapter_override` variant is treated as a finding, not a drift. The
plan now delivers the live-draft reconciliation the developers' guide (lines
329-334) defines as task 2.1.3, and Work item 3 corrects the guide to state
what was actually delivered rather than overclaiming (B3). The stale "move
invariant 3 onto disk" framing is removed — invariant 3 is already disk-read by
`_check_by_chapter_sum`; the live oracle's invariant-3 clause is the
table-coherence check, distinct from the live cross-check (B4). The red-commit
branch is dropped: Work items 1 and 2 land in one green commit that passes
`make all`, per AGENTS.md lines 100 and 108 (B5).

Round 1 (2026-06-23): initial draft (superseded). Proposed a
`[word_counts]`-table re-read oracle keyed on `CORPUS_INVARIANT_NAMES`; the
design review found that construction non-independent and rescoped it to the
live-draft cross-check above.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge audit (`docs/issues/audit-2.1.3.md`). Execute each as a small
addendum pass — no plan or design-review cycle: make the change, run `make all`
(plus `make markdownlint`/`make nixie` for Markdown), `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge. The
substantial, cross-cutting follow-ups were re-routed off this task: the
first-class `by_chapter_override` corpus divergence variant (review:2.1.3 /
audit:2.1.3) to roadmap step 2.1 (task 2.1.5, because it adds §1.3.2 corpus data
and hardens the validator cross-check that proves the step-2.1 hypothesis), and
the lane-wide `mutmut` run (review:2.1.3) to roadmap step 7.6 (a deferred
verification-hardening extension); the three below are the small, localised
fixes. Audit Finding 5 (the inline owned-name restriction) and Finding 6 (the
users'-guide verdict vocabulary) are not folded here: Finding 6's vocabulary
enumeration already shipped in task 2.1.2.7, with its residual operator-meaning
prose deferred to the broader users-guide update in task 2.2.2.1.

- [x] 2.1.3.1 — Consolidate the live-draft oracle's repeated `state.toml`
  parsing and drop the third `by-chapter-sum` predicate twin (from audit:2.1.3,
  medium; Findings 1 and 3). In `tests/working_corpus/_live_draft.py`, parse
  `state.toml` once in `live_draft_owned` and pass the decoded
  `[word_counts]`/`[gates]`/`[drafting]` tables into the three `_check_*_live`
  predicates, turning them into pure functions over already-decoded data; then
  drop `_check_by_chapter_sum_live` in favour of the `by-chapter-sum` verdict
  `corpus_check(spec, working_dir)` already returns (line 184), so the
  table-internal read is no longer a third hand-copied twin. Test-only. Gate
  with `make all`.
- [x] 2.1.3.2 — Lift the shared disk-evidence invariant-name set into one home
  for both agreement suites (from audit:2.1.3, medium; Finding 2). The identical
  five-element frozensets `_DISK_EVIDENCE_NAMES`
  (`tests/test_validate_state_live_draft.py`) and `_DEFERRED_INVARIANT_NAMES`
  (`tests/test_validate_state_corpus.py`) are hard-coded in two modules with
  nothing pinning them equal. Define the set once in
  `tests/_state_corpus_support.py` — ideally derived as
  `set(CORPUS_INVARIANT_NAMES) - set(PURE_STATE_INVARIANT_NAMES)` so it cannot
  drift from the owned vocabulary — and import it into both modules. Test-only.
  Gate with `make all`.
- [x] 2.1.3.3 — Promote the §5.2 gate thresholds to a public exported constant
  (from audit:2.1.3, low; Finding 4). `tests/test_validate_state_corpus.py` and
  `tests/test_validate_state_property.py` both import the module-private
  `_GATE_THRESHOLDS` from `novel_ralph_skill/state/validate.py` across the
  package boundary — the cross-module-private-import smell prior audits
  repeatedly lifted. Export `GATE_THRESHOLDS` from `state/validate.py`,
  re-export it through `novel_ralph_skill.state.__init__` alongside the
  invariant-name constants, and update the two test imports. Gate with
  `make all`.
