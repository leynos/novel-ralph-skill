# Settle the authoritative `current` definition and align recount and reconcile

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

The harness records a manuscript's word total in `state.toml` as
`[word_counts].current`. Two on-disk quantities could in principle define that
number: the **drafted sum** (the whitespace-split token counts of each
`working/manuscript/chapter-NN/draft.md`, summed) or the **compiled token
count** (the tokens of `working/manuscript/compiled.md`).

A novice might assume these two numbers diverge merely because `compiled.md`
joins chapters with a separator. They do **not**, for any byte-exact compile.
`concatenate_drafts` joins the present draft bodies with `DRAFT_SEPARATOR =
"\n\n"` (`novel_ralph_skill/state/compile_model.py:30`), which is whitespace,
and Python's `str.split()` (no argument) collapses every run of whitespace.
Therefore, for the bytes a clean compile produces:

```text
len(concatenate_drafts(bodies).split()) == sum(len(b.split()) for b in bodies)
```

holds **always** — the separator and any leading, trailing, or interior
whitespace never change the token count. This was verified empirically across
boundary cases (multiple chapters, leading/trailing/interior whitespace,
whitespace-only and empty bodies, and trailing whitespace on the whole file);
every case gives equality. The Decision Log records the verification.

The compiled token count can therefore differ from the drafted sum **only**
when `compiled.md` is not the byte-exact concatenation of the present drafts —
that is, a stale or hand-edited `compiled.md` carrying extra or altered
**non-whitespace** content (added, dropped, or reworded words). That exact
condition is what `_check_compiled_matches_drafts` detects: it recomputes
`concatenate_drafts(present_bodies)` and compares **bytes** against the on-disk
`compiled.md` (`novel_ralph_skill/state/disk_evidence.py:173-191`); any
mismatch is the `compiled-matches-drafts` disk-evidence finding, a REFUSE-class
contradiction reported by `check` with exit 4 and refused by `reconcile`. So the
only `compiled.md` whose token count can diverge from the drafted sum is, by
construction, the same `compiled.md` that the disk-evidence detector surfaces as
a finding — never a `current` source.

Roadmap task 2.3.1 already shipped `recount` defining `current` as the drafted
sum (`sum(by_chapter.values())`; `docs/execplans/roadmap-2-3-1.md` Decision Log
D-CURRENT), and task 2.3.2's `reconcile` RECOUNT path writes the same drafted
sum through the same shared helper (`disk_word_counts` ->`recount_words`). But two
source-of-truth documents still carry the *old, ambiguous* definition:

- `skill/novel-ralph/references/state-layout.md:114` —
  `current = 24300  # words in compiled.md (or sum of drafts)`.
- `novel_ralph_skill/state/schema.py:237` (the `WordCounts.current` docstring) —
  "The current word count, in `compiled.md` or the sum of drafts".

The "(or sum of drafts)" / "in `compiled.md` or the sum of drafts" wording
contradicts the implemented and design-mandated rule and would let a future
contributor reintroduce a compiled-token `current`, re-opening the very drift
this step exists to close.

After this change a reader can observe: (1) `state-layout.md`, the
`WordCounts.current` docstring, design §4.1/§5.4, and the 2.3.1 D-CURRENT note
all state the **same** rule — `current` is the drafted sum, and a `compiled.md`
that diverges from the drafts is surfaced as the `compiled-matches-drafts`
reconciliation finding, never as a `current` source; and (2) a new test proves
`recount` and the `reconcile` RECOUNT path write the drafted-sum `current`
irrespective of `compiled.md`, and that a bytes-divergent `compiled.md` (whose
token count genuinely differs from the drafted sum) is surfaced as the
`compiled-matches-drafts` finding without ever touching `current`. Running
`make all`, `make markdownlint`, and `make nixie` all pass.

This is, in the main, a **decision-and-reconciliation** task: the authoritative
rule is already implemented; the work records the decision once, removes the two
surviving textual contradictions, makes the design prose state the rule
explicitly, and pins the recount/reconcile agreement and the
compiled-divergence-is-a-finding boundary with a regression test so the
alignment cannot silently rot.

## Roadmap and design provenance

- Roadmap task: `docs/roadmap.md` task 2.3.5 ("Settle the authoritative
  `current` definition when `compiled.md` diverges from the drafted sum, and
  align recount and reconcile on it."), under step 2.3 ("Deliver recount and
  disk-authoritative reconciliation"). Requires 2.3.1 and 2.3.2 (both `[x]`).
- Design sections this plan implements:
  - `docs/novel-ralph-harness-design.md` §4.1 (`novel-state`: `recount`
    "re-derives `word_counts.current` and `by_chapter` from chapter drafts",
    line 284; "the count is a pure aggregation over
    `working/manuscript/chapter-NN/draft.md` files", lines 288-290).
  - `docs/novel-ralph-harness-design.md` §5.2 invariant 3 ("`word_counts.by_chapter`
    sums to `word_counts.current`", line 466) — the table-internal invariant the
    drafted-sum rule satisfies by construction.
  - `docs/novel-ralph-harness-design.md` §5.4 (disk-authoritative reconciliation;
    "Disk is authoritative; `state.toml` describes disk", line 501) and its v1
    scope subsection (lines 534-568), under which a bytes-divergent `compiled.md`
    is the `compiled-matches-drafts` contradiction, not a `current` source.
  - `docs/novel-ralph-harness-design.md` §4.3 (`novel-compile`: "consistent
    separators", lines 348-353) — the join rule the byte-exact concatenation
    obeys, and why only a non-concatenation `compiled.md` can diverge.
- ADRs that govern the change:
  - `docs/adr-001-deterministic-judgemental-boundary.md` — scripts detect and
    report; the model adjudicates. Recording one authoritative `current` rule and
    surfacing `compiled.md` divergence as a finding (not a silent re-projection)
    is squarely within the deterministic half.
  - `docs/adr-002-toml-round-trip-tomlkit.md` — no edit to a code path that writes
    `state.toml` is introduced here, but any test that constructs a `state.toml`
    must round-trip through `tomlkit` (via the corpus builder), never a
    hand-written serialiser.
  - `docs/adr-003-shared-interface-contract.md` — exit-code table (0 success, 4
    actionable finding). The `compiled-matches-drafts` finding already exits 4
    through `check`; this plan must not perturb that.
- Prior execplans this plan reconciles with:
  - `docs/execplans/roadmap-2-3-1.md` Decision Log D-CURRENT (the drafted-sum
    decision and its "compiled-versus-drafts reconciliation is roadmap task
    2.3.2" deferral) and D-CWD (the chdir discipline for the mutators).
  - `docs/execplans/roadmap-2-3-2.md` (the `reconcile` RECOUNT path and the
    `derive_reconciliation` precedence).
  - `docs/execplans/roadmap-2-3-3.md` (the disk-vs-disk corpus oracle twins).

## Orientation: the current state of the code

A novice should read these files before touching anything; `leta show <symbol>`
and `leta refs <symbol>` are the navigation tools, not raw `grep`.

- `novel_ralph_skill/state/wordcount.py` — `recount_words(working_dir, manifest)`
  is the **one** counting rule. It reads each manifest chapter's `draft.md`,
  takes `len(text.split())`, and returns `(sum(by_chapter.values()), by_chapter)`.
  `current` is the drafted sum *by construction* here, and the function never
  reads `compiled.md` (verified: the only path it opens is `.../chapter-NN/draft.md`,
  `wordcount.py:75`).
- `novel_ralph_skill/commands/_recount.py` — `recount()` (the `recount` mutator
  body) calls `recount_words`, then writes `document["word_counts"]["current"]`
  and `["by_chapter"]`. It never reads `compiled.md`, and it never runs the
  disk-evidence detector, so a divergent `compiled.md` does not even affect a
  `recount`.
- `novel_ralph_skill/state/disk_evidence.py` —
  - `disk_word_counts(state, working_dir)` delegates straight to `recount_words`,
    so the disk-derived `current` is *the same* drafted sum.
  - `_check_compiled_matches_drafts` (lines 173-191) owns the
    `compiled-matches-drafts` invariant: it recomputes
    `concatenate_drafts(present_draft_bodies)` and compares `compiled.md`'s
    **bytes** (`compiled.read_text() == expected`); an absent `compiled.md`
    trivially passes; on a byte mismatch it is a REFUSE-class contradiction. This
    is the *only* place a divergent `compiled.md` surfaces — never a `current`
    source. The invariant name constant is
    `COMPILED_MATCHES_DRAFTS = "compiled-matches-drafts"` (`disk_evidence.py:63`).
  - `_check_word_counts_match_drafts` owns `word-counts-match-drafts` (the
    per-chapter `by_chapter`-vs-drafts staleness that triggers a RECOUNT).
- `novel_ralph_skill/state/reconcile.py` — `derive_reconciliation(state,
  working_dir)`. Its `_recount(...)` builds a `Reconciliation` whose
  `recounted_current` is `disk_word_counts(...)[0]` — again the drafted sum. The
  `compiled-matches-drafts` violation maps to a REFUSE action (`reconcile.py:18`,
  `:66`), so a divergent `compiled.md` never reaches a `current` write.
- `novel_ralph_skill/commands/_reconcile.py` — the `reconcile` mutator. Its
  RECOUNT edit writes `document["word_counts"]["current"] =
  reconciliation.recounted_current`. So `recount` and `reconcile` already write
  the **same** `current` through the **same** helper; this plan pins that.
- `novel_ralph_skill/state/compile_model.py` — `concatenate_drafts` and
  `DRAFT_SEPARATOR = "\n\n"` (line 30). The separator is whitespace, so the
  byte-exact concatenation's token count *equals* the drafted sum (see Purpose);
  only a non-concatenation `compiled.md` can diverge.
- `skill/novel-ralph/references/state-layout.md` — the skill-facing reference;
  line 114 is a surviving contradiction (line 281's `compiled.md` mention is a
  legitimate *finding* reference and stays). The reference is scanned by
  `tests/test_state_layout_reference.py` only for hand-edit recipes, not for the
  word-count comment, so editing the comment is safe (verified: the scanner
  fixtures in `tests/_planted_recipes.py` and `tests/_state_layout_scanner.py`
  do not pin line 114's text).
- `docs/developers-guide.md:585` already states the rule correctly ("`current`
  is the drafted sum `sum(by_chapter.values())`"); it is the model for the wording
  the two contradictions should adopt.
- Test fixtures to reuse (do not reinvent):
  - `tests/working_corpus/` — `WorkingTreeSpec` carries a `compiled` field
    (`_specs.py:157-160`, `:182`): `None` writes no `compiled.md`,
    `COMPILED_AUTO` writes the byte-exact concatenation of the present drafts,
    and any other string writes those exact bytes (the stale/divergent compile).
    The spec is serialised to `state.toml` through `tomlkit` by
    `tests/working_corpus/_builder.py` (ADR-002 honoured by reuse).
  - `tests/working_corpus/_variants.py:189-192` already defines the
    `compiled-not-concatenation-of-drafts` variant
    (`compiled="not the real concatenation"`), whose four injected
    non-whitespace tokens make its compiled token count genuinely differ from the
    drafted sum **and** make it the `compiled-matches-drafts` REFUSE tree — the
    coherent single tree where both facts hold at once. This is the case-3
    fixture.
  - `tests/working_corpus/_variants.py` `done-flag-real-draft-undercount`
    variant (used by `tests/test_reconcile_derivation.py:124-134`) is a
    stale-`by_chapter` tree with a coherent (or absent) `compiled.md` that
    reaches the `reconcile` RECOUNT path — the case-2 fixture.

## The decision (the heart of this task)

This plan ratifies the rule already implemented and defers nothing:

`current` is the **drafted sum** — `sum(by_chapter.values())`, where each
`by_chapter[NN]` is `len(draft_text.split())` for `chapter-NN/draft.md`. The
compiled token count is **never** a `current` source. `recount` and the
`reconcile` RECOUNT path both write `sum(by_chapter)` irrespective of
`compiled.md`. When `compiled.md` is not the byte-exact concatenation of the
present drafts — which is the *only* way its token count can differ from the
drafted sum — that divergence is surfaced as the `compiled-matches-drafts`
disk-evidence finding (design §5.4;
`disk_evidence._check_compiled_matches_drafts`), reported by `check` with exit 4
and refused by `reconcile`. It does **not** redefine, recompute, or perturb
`current`.

Why the drafted sum and not the compiled token count:

1. It is what §4.1 already mandates ("re-derive `current` … from chapter
   drafts") and what §5.2 invariant 3 ("`by_chapter` sums to `current`") makes
   true by construction. Defining `current` from compiled tokens would break
   invariant 3 whenever `compiled.md` diverged in bytes from the drafts.
2. The drafted sum is re-derivable per chapter, so it underwrites the step-2.3
   hypothesis (state re-derivable from disk, never drifting). The compiled token
   count is a whole-file scalar with no per-chapter decomposition, so it could
   not key `by_chapter` and could not feed the `word-counts-match-drafts` /
   `RECOUNT` repair.
3. `compiled.md` is a *derived artefact* (design §4.3, regenerated by
   `novel-compile`); treating a derived artefact as the authority for a primary
   count inverts "disk is authoritative; `state.toml` describes disk" applied to
   the *source* drafts. A *stale* derived artefact, moreover, is a contradiction
   to be reported, not a number to be trusted.

No alternative is left open for the implementer: the rule is decided here, and
the two contradictions are corrected to match it, not to offer a choice.

## Constraints

- **No behaviour change to `recount`, `reconcile`, `check`, or the
  disk-evidence detector.** The drafted-sum rule is already implemented; this
  plan records and pins it. If any work item would require editing
  `wordcount.py`, `_recount.py`, `disk_evidence.py`, `reconcile.py`, or
  `_reconcile.py` to change a computed value, stop and escalate — that would mean
  the decision was *not* already implemented, which the orientation above
  contradicts. (Pure additive guards or docstring edits in those files are
  allowed.)
- **`current` is `sum(by_chapter.values())`.** Every document and docstring this
  plan touches must state exactly this, with the compiled token count named only
  as a finding source, never a `current` source. No prose, comment, or docstring
  this plan writes may claim the `"\n\n"` separator or trailing/leading
  whitespace can make `len(compiled.split()) != sum(len(draft.split()))`: for a
  byte-exact concatenation those counts are equal, and divergence requires a
  non-concatenation `compiled.md` (the `compiled-matches-drafts` REFUSE
  condition).
- **No new external dependency.** The change is documentation plus a test using
  the existing `tomlkit`, `pytest`, and `pytest-bdd` stack via the corpus
  builder. cuprum (locked at `0.1.0`, `uv.lock:113`) is **not** used: every
  module in scope is pure `pathlib`/`tomlkit` I/O and shells out to nothing
  (verified: no `cuprum`, `import sh`, or `subprocess` import in `_recount.py`,
  `_reconcile.py`, `reconcile.py`, `wordcount.py`, or `disk_evidence.py`). This
  matches the D-CUPRUM precedent recorded in `docs/execplans/roadmap-2-3-1.md`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages (AGENTS.md line 18; `en-gb-oxendict` skill).
- **Module-size and docstring gates.** No file may exceed 400 lines (AGENTS.md
  line 24); the `interrogate` docstring gate must stay green (AGENTS.md lines
  86-90). New test modules carry module and function docstrings.
- **TOML is written through `tomlkit` only** (ADR-002); test fixtures must use
  the existing corpus/`WorkingTreeSpec` builder, which serialises through
  `tomlkit`, never a hand-assembled `state.toml` string.

## Tolerances (exception triggers)

- Scope: if the change requires editing more than 6 files or more than ~120 net
  lines of code (test code included), stop and escalate — the task is scoped as
  a doc reconciliation plus one focused regression test.
- Behaviour: if pinning the recount/reconcile agreement reveals that they
  *disagree* on `current` for any tree (i.e. the test fails red for a real
  reason, not a test bug), stop and escalate — that is a latent defect in 2.3.1
  or 2.3.2, not in scope for a reconciliation task, and must be triaged
  separately.
- Interface: if any public function signature in the `state` package must
  change, stop and escalate.
- Dependencies: if any new dependency (including a new dev dependency) is
  required, stop and escalate.
- Iterations: if `make all` still fails after 3 fix attempts on any single work
  item, stop and escalate.
- Ambiguity: if a reviewer or a doc reveals a *third* `current` definition not
  named here (beyond `state-layout.md:114` and `schema.py:237`), stop and present
  it before editing.
- Arithmetic surprise: if any boundary case is found where
  `len(concatenate_drafts(bodies).split()) != sum(len(b.split()) for b in
  bodies)` for a byte-exact concatenation, stop and escalate — the whole plan's
  premise rests on that equality (verified in the Decision Log), and a
  counter-example would invalidate the fixture matrix.

## Risks

- Risk: editing state-layout.md:114 trips the state-layout reference scanner
  test (test_state_layout_reference.py). Severity: low. Likelihood: low.
  Mitigation: the scanner pins only hand-edit recipes (write primitives,
  executable info-strings), not the word-count comment; verified against
  tests/_planted_recipes.py and tests/_state_layout_scanner.py. Work item 2 runs
  `make test` after the edit to confirm.
- Risk: the recount/reconcile agreement test is a tautology (both already call
  the same helper) and proves nothing. Severity: medium. Likelihood: medium.
  Mitigation: the test is a forward-looking regression guard against a *future*
  refactor that points either path at the compiled token count. It is made
  non-tautological by (a) asserting both paths' written `current` against a
  single `recount_words(...)[0]` oracle, and (b) the work item 3 "prove it fails
  red" step, which temporarily edits a path to use `len(compiled.split())` and
  confirms the test goes red, then reverts. Recorded in the Decision Log.
- Risk (CORRECTED in round 2): a test tries to make the compiled token count
  diverge from the drafted sum via the `"\n\n"` separator or trailing
  whitespace, and the arrange-time precondition assertion fails because the
  counts are in fact equal (the round-1 B1/B3 defect). Severity: high (would
  error the test on arrange). Likelihood: n/a — eliminated by design.
  Mitigation: divergence is realised the *only* way it genuinely can be — with a
  bytes-divergent `compiled.md` carrying injected **non-whitespace** content (the
  existing `compiled-not-concatenation-of-drafts` variant, whose
  `compiled="not the real concatenation"` adds four non-draft tokens). That tree
  is *the same* `compiled-matches-drafts` REFUSE tree, so the "compiled token
  count differs from the drafted sum" assertion and the "exit 4, `current`
  untouched" assertion live together on one coherent fixture (case 3). No test
  attributes divergence to the separator or to whitespace.
- Risk (CORRECTED in round 2): the RECOUNT-path tree is required to
  *simultaneously* keep `compiled.md` a coherent concatenation **and** have a
  divergent compiled token count (the round-1 B2 impossibility). Severity: high
  (unrealisable as written). Likelihood: n/a — eliminated by design.
  Mitigation: the RECOUNT-path tree (case 2) carries only the stale-table
  property and a coherent-or-absent `compiled.md`; it does **not** assert any
  compiled-token divergence. The "not the compiled token count" assertion is
  moved entirely to case 3 (the REFUSE tree), the only tree where a divergent
  compiled token count legitimately exists.
- Risk: design §5.4 prose edit changes the documented reconciliation semantics
  and contradicts the 2.3.2/2.3.3 execplans. Severity: medium. Likelihood: low.
  Mitigation: the §5.4 edit is purely *additive clarification* — one sentence
  stating `current` is the drafted sum and a bytes-divergent `compiled.md` is
  the `compiled-matches-drafts` finding. It must not alter the v1 scope list
  (lines 534-568) or any REFUSE/RECOUNT disposition. Re-read those lines before
  editing.

## Progress

- [x] Work item 1: record the decision (Decision Log + design §4.1/§5.4
  one-line clarifications). Done 2026-06-24: added the drafted-sum sentence to
  §4.1 (the compiled token count is never a `current` source) and the
  bytes-divergence-is-a-finding sentence to the §5.4 v1-scope stale-table item;
  `make markdownlint` and `make nixie` both clean. Also corrected pre-existing
  MD007/MD032/MD013 lint in the planning-phase `review-r1`/`review-r2`
  artefacts so the repo-wide markdown gate passes (the review files follow the
  tracked convention and are committed alongside the execplan).
- [x] Work item 2: reconcile the two surviving textual contradictions
  (state-layout.md:114 and schema.py:237) onto the drafted-sum rule. Done
  2026-06-24: `state-layout.md:114` comment is now `# drafted sum (sum of
  by_chapter values)`; the `WordCounts.current` docstring states the drafted sum
  `sum(by_chapter.values())` and names a bytes-divergent `compiled.md` as the
  `compiled-matches-drafts` finding. A repo-wide search confirms no surviving
  "(or sum of drafts)"-style live `current` definition (the `state-layout.md:281`
  and design §5.4 `compiled.md` mentions are legitimate finding references). `make
  all` green (588 passed, 1 skipped), `make markdownlint`/`make nixie` clean,
  coderabbit 0 findings.
- [x] Work item 3: pin the recount/reconcile `current` agreement and the
  compiled-divergence-is-a-finding boundary with a regression test. Done
  2026-06-24: added `tests/test_current_definition.py` with the three
  D-FIXTURE-MATRIX cases. Case 1 builds a stale-table tree with a
  bytes-divergent `compiled.md` (injected non-whitespace content) and asserts
  `recount` writes the drafted sum, not the compiled token count. Case 2 uses
  the `done-flag-real-draft-undercount` variant and asserts the `reconcile`
  RECOUNT path writes the same `recount_words(...)[0]` oracle. Case 3 uses the
  `compiled-not-concatenation-of-drafts` variant and asserts `check` reports
  `compiled-matches-drafts` at exit 4 while `state.toml` is byte-for-byte
  unchanged, the drafted sum differing from the compiled token count there.
  Fail-red proven: temporarily pointing `recount_words` at the compiled token
  count turned case 1 red; reverted, production `git diff` empty. `make all`
  green at 591 passed / 1 skipped (was 588; +3 from this module).

## Surprises & discoveries

- Observation: the compiled token count cannot diverge from the drafted sum via
  the separator or whitespace; only injected non-whitespace content can make it
  differ, and that is exactly the `compiled-matches-drafts` REFUSE case.
  Evidence: `DRAFT_SEPARATOR = "\n\n"` (compile_model.py:30) is whitespace and
  `str.split()` collapses all whitespace, so
  `len(concatenate_drafts(bodies).split()) == sum(len(b.split()))` for every
  byte-exact concatenation (verified empirically across boundary cases —
  Decision Log D-TOKEN-EQUALITY). `_check_compiled_matches_drafts`
  (disk_evidence.py:173-191) compares bytes, so the only `compiled.md` that does
  not REFUSE is byte-identical to the concatenation, whose token count provably
  equals the drafted sum. Impact: the round-1 plan's separator/whitespace
  divergence premise was false; the fixture matrix is rebuilt so the divergent
  compiled token count lives only on the bytes-divergent REFUSE tree (case 3),
  and case 1/case 2 assert recount/reconcile write the drafted sum irrespective
  of `compiled.md`.
- Observation: the developers' guide already states the rule correctly.
  Evidence: docs/developers-guide.md:585 ("`current` is the drafted sum
  `sum(by_chapter.values())`, so §5.2 invariant 3 holds by construction").
  Impact: the guide needs no correction; it is the canonical wording the two
  contradictions should be brought into line with.
- Observation: recount and reconcile already share one helper and so cannot
  disagree on `current` today. Evidence: _recount.py calls recount_words;
  _reconcile.py RECOUNT writes reconciliation.recounted_current, sourced from
  disk_word_counts -> recount_words. Both = sum(by_chapter). Impact: the
  agreement test is a forward-looking regression guard, not a bug fix; it must be
  written to fail if a future change reintroduces a compiled-token `current` in
  either path (see Risks).
- Observation: an existing corpus variant already provides the bytes-divergent
  REFUSE tree. Evidence: tests/working_corpus/_variants.py:189-192 defines
  `compiled-not-concatenation-of-drafts` (`compiled="not the real
  concatenation"`), which surfaces `oracle.COMPILED_MATCHES_DRAFTS`; its four
  injected non-whitespace tokens are unrelated to the drafts, so its compiled
  token count differs from the drafted sum. Impact: case 3 reuses this variant;
  no bespoke divergent `compiled.md` need be hand-built, and ADR-002 is honoured
  through the corpus builder.

## Decision log

- Decision (D-TOKEN-EQUALITY): for any byte-exact `concatenate_drafts(bodies)`,
  `len(result.split()) == sum(len(b.split()) for b in bodies)`, because
  `DRAFT_SEPARATOR` (compile_model.py:30) is whitespace and argument-less
  `str.split()` collapses all whitespace runs. Verified empirically across
  boundary cases: multi-chapter joins, leading/trailing/interior whitespace in
  bodies, whitespace-only bodies, empty bodies, and trailing whitespace on the
  whole file — every case gave equality. Consequence: the compiled token count
  diverges from the drafted sum *only* when `compiled.md` is not the byte-exact
  concatenation (extra or altered non-whitespace content), which is precisely the
  `compiled-matches-drafts` REFUSE condition. Rationale: this corrects the
  round-1 false premise (review B1/B3) that the separator or whitespace could
  cause divergence, and re-bases the entire fixture matrix on the true mechanism.
  Date/Author: 2026-06-24, planning agent (round 2).
- Decision (D-CURRENT-AUTHORITY): `current` is the drafted sum
  `sum(by_chapter.values())`; the compiled token count is never a `current`
  source; a *bytes-divergent* `compiled.md` (the only `compiled.md` whose token
  count can differ from the drafted sum, per D-TOKEN-EQUALITY) is surfaced as the
  `compiled-matches-drafts` disk-evidence finding (design §5.4), exiting 4 in
  `check` and refused by `reconcile`, without touching `current`. Rationale: it
  is what design §4.1 and §5.2 invariant 3 already mandate and what 2.3.1/2.3.2
  already implement; it is re-derivable per chapter (underwriting step-2.3); and
  `compiled.md` is a derived artefact (§4.3) that must not become the authority
  for a primary count. The alternative (compiled-token `current`) would break
  invariant 3 on a stale compile and could not key `by_chapter`. Date/Author:
  2026-06-24, planning agent.
- Decision (D-FIXTURE-MATRIX): the regression test uses three non-contradictory
  trees. Case 1 (recount, ignores `compiled.md`): a stale-table tree; assert
  `recount` writes the drafted sum. Case 2 (reconcile RECOUNT path): the
  `done-flag-real-draft-undercount` tree (stale `by_chapter`, coherent-or-absent
  `compiled.md`, so `compiled-matches-drafts` does not REFUSE); assert
  `reconcile` writes the drafted sum, equal to the same `recount_words(...)[0]`
  oracle. Case 3 (the ONLY tree with a divergent compiled token count): the
  `compiled-not-concatenation-of-drafts` REFUSE tree; assert `check` reports
  `compiled-matches-drafts` and exits 4, that `state.toml`'s `current` is
  byte-for-byte untouched, and that the drafted sum differs from the compiled
  token count there (the "not the compiled token count" assertion lives here,
  where divergence is real). Rationale: resolves review B2 (no tree must be both
  coherent-compile and divergent-token), B3 (no arrange-time precondition that is
  false), and B4 (the divergent quantity is named correctly as bytes-divergence,
  and the "not the compiled token count" check lives only where it can hold).
  Date/Author: 2026-06-24, planning agent (round 2).
- Decision (D-NO-CODE-CHANGE): no behaviour-bearing edit to wordcount.py,
  _recount.py, disk_evidence.py, reconcile.py, or _reconcile.py. The rule is
  pinned by documentation and a regression test, because the rule is already
  implemented. If the agreement test fails red for a real reason, escalate rather
  than "fix" production (it would mean a latent 2.3.1/2.3.2 defect). Date/Author:
  2026-06-24, planning agent.
- Decision (D-CUPRUM): no cuprum API is pinned or used; every module in scope is
  pure pathlib/tomlkit I/O and shells out to nothing (verified no
  cuprum/sh/subprocess import). The locked cuprum 0.1.0 (catalogue/Program/sh)
  surface is not exercised, matching the 2.3.1 D-CUPRUM precedent. Recorded so a
  reviewer does not expect a cuprum citation. Date/Author: 2026-06-24, planning
  agent.
- Decision (D-NO-FIRECRAWL): no external-library behavioural claim is
  load-bearing here, so no firecrawl research was performed. The change leans
  only on the standard-library `str.split` token rule (verified empirically,
  D-TOKEN-EQUALITY) and `tomlkit`/`pytest`, both already locked and already
  exercised by the existing recount/reconcile suites. Recorded so a reviewer does
  not expect a cited external source. Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

Completed 2026-06-24. The four documents now agree: `state-layout.md:114`, the
`WordCounts.current` docstring, design §4.1/§5.4, and `docs/developers-guide.md`
all state `current` is the drafted sum `sum(by_chapter.values())`, with a
bytes-divergent `compiled.md` named only as the `compiled-matches-drafts`
finding, never a `current` source. The new `tests/test_current_definition.py`
guards the recount/reconcile agreement and the compiled-divergence-is-a-finding
boundary, and is demonstrably non-tautological (fail-red proven, then reverted).
`make all` passes (591 passed / 1 skipped), and `make markdownlint` / `make
nixie` pass for the Markdown changes. No behaviour-bearing code changed, exactly
as D-NO-CODE-CHANGE intended.

Process note: `make fmt` runs a repo-wide markdown reformatter that churned
100+ unrelated docs in the working tree. Per the recurring repository convention
(many "spurious make-fmt mdformat churn" stashes), that churn was stashed and
discarded; only the deterministic `make all` check-fmt gate (which passed) and
the explicit `make markdownlint` / `make nixie` gates were relied upon. The
manual line-wrapping discipline kept every touched Markdown file within the
80-column gate without invoking `make fmt`.

## Plan of work

Three ordered, independently committable work items. Each ends with the stated
validation and is gate-passable on its own.

### Work item 1 — Record the decision and clarify the design prose

Outcome: the authoritative `current` rule is recorded once in this ExecPlan's
Decision Log (already drafted as D-CURRENT-AUTHORITY/D-TOKEN-EQUALITY) and stated
explicitly in the design document, so a future contributor cannot infer a
compiled-token `current` from design prose.

Edits:

1. `docs/novel-ralph-harness-design.md` §4.1: after the existing sentence on
   `recount` (around line 288-290, "the count is a pure aggregation over
   `working/manuscript/chapter-NN/draft.md` files, so the command owns it"), add
   one sentence: `current` is exactly that drafted sum
   (`sum(by_chapter.values())`), so §5.2 invariant 3 holds by construction; the
   compiled token count is never a `current` source.
2. `docs/novel-ralph-harness-design.md` §5.4: in the v1-scope subsection (around
   lines 534-556, where the §5.4 reconciliations are enumerated), add one
   sentence stating that a `compiled.md` which is **not the byte-exact
   concatenation** of the present drafts is the `compiled-matches-drafts` finding
   (reported by `check` with exit 4, refused by `reconcile`) and never redefines
   or recomputes `current`. Do **not** alter the v1 scope list's RECOUNT/REFUSE
   dispositions. The sentence must not claim the separator can change the token
   count — name *bytes-divergence* as the trigger.

Docs to read first: `docs/novel-ralph-harness-design.md` §4.1, §4.3, §5.2,
§5.4; `docs/execplans/roadmap-2-3-1.md` Decision Log D-CURRENT;
`docs/adr-001-deterministic-judgemental-boundary.md`.

Skills to load: `execplans` (this plan is the living document);
`en-gb-oxendict` (prose spelling); `leta` (navigate the design anchors and
confirm the exact insertion points).

Tests: none — this work item edits only Markdown prose. Per AGENTS.md the
markdown gates apply.

Validation:

- Run `make markdownlint` (expect no findings on the design document).
- Run `make nixie` (expect no Mermaid-diagram findings; the design doc carries
  diagrams elsewhere — confirm none broke).
- Manually confirm §4.1 and §5.4 now state the drafted-sum rule and the
  bytes-divergence-is-a-finding rule, with no surviving "(or sum of drafts)"
  ambiguity and no separator/whitespace divergence claim in either.

Commit: a single doc commit (e.g. "Record drafted-sum `current` rule in design
§4.1/§5.4").

### Work item 2 — Reconcile the two surviving textual contradictions

Outcome: `state-layout.md:114` and the `WordCounts.current` docstring both state
`current` is the drafted sum, with the compiled token count named only as a
finding source. After this item the repository carries **no** "(or sum of
drafts)"-style alternative-source wording for `current` (the remaining hits in
`docs/roadmap.md:725` quote the old task text and in execplan history are
historical — both out of scope, confirmed by search).

Edits:

1. `skill/novel-ralph/references/state-layout.md:114`: change the inline comment
   from `# words in compiled.md (or sum of drafts)` to a drafted-sum comment,
   e.g. `# sum of chapter draft word counts (sum of by_chapter)`. Keep the
   numeric example consistent with the surrounding `by_chapter` example on line
   115 if the surrounding block makes them sum; otherwise leave the illustrative
   number and only correct the definition comment. (Verify the line-115
   `by_chapter` example does not now visibly contradict line 114; adjust the
   comment wording, not the schema.)
2. `novel_ralph_skill/state/schema.py:237` (the `WordCounts.current` Attributes
   docstring): change "The current word count, in `compiled.md` or the sum of
   drafts (`[word_counts].current`)." to state the drafted sum, e.g. "The current
   word count: the drafted sum `sum(by_chapter.values())`
   (`[word_counts].current`); a bytes-divergent `compiled.md` is the
   `compiled-matches-drafts` finding, not a `current` source."

Docs to read first: `skill/novel-ralph/references/state-layout.md` around lines
108-116 and 260-285; `novel_ralph_skill/state/schema.py` `WordCounts`
(lines 228-261); `docs/developers-guide.md:577-593` (the canonical wording to
mirror).

Skills to load: `python-router` (then follow it to `python-data-shapes` for the
`WordCounts` dataclass docstring conventions); `en-gb-oxendict`; `leta` (use
`leta show novel_ralph_skill.state.schema.WordCounts` and `leta refs WordCounts`
to confirm no other docstring repeats the old wording).

Tests: no new behavioural test is needed for the docstring edit itself, but the
existing suite must stay green:

- `make test` must continue to pass `tests/test_state_layout_reference.py`
  (confirms the state-layout edit did not trip the hand-edit scanner) and
  `tests/test_state_schema.py` (confirms the `WordCounts` change is docstring-only
  and breaks no schema assertion).
- The `interrogate` docstring gate must stay green (the edit keeps the
  `current` attribute documented).

Validation:

- Run `make all` (build, check-fmt, lint, typecheck, test). Expect all green;
  in particular `test_state_layout_reference.py` and `test_state_schema.py` pass.
- Run `make markdownlint` (state-layout.md is Markdown).
- Run `make nixie` (state-layout.md may carry fenced trees/diagrams; confirm no
  finding).
- Confirm with `leta grep` / search that no other occurrence of "in compiled.md"
  or "sum of drafts" defines `current` anywhere in `novel_ralph_skill/`,
  `skill/`, or `docs/` outside execplan history and the roadmap task text (the
  design §4.3 and §5.4 *finding* references to `compiled.md`, and
  `state-layout.md:281`, are legitimate and stay).

Commit: a single commit (e.g. "Reconcile `current` definition onto the drafted
sum in state-layout and schema").

### Work item 3 — Pin the recount/reconcile `current` agreement and the finding boundary

Outcome: a regression test proves (a) `recount` writes the drafted-sum `current`
irrespective of `compiled.md`; (b) the `reconcile` RECOUNT path writes the
identical drafted-sum `current`; and (c) a bytes-divergent `compiled.md` — the
only tree whose compiled token count differs from the drafted sum — is surfaced
as the `compiled-matches-drafts` finding (exit 4) while `current` is left
untouched, and the drafted sum genuinely differs from that compiled token count.
This guards the decision against a future refactor that reintroduces a
compiled-token `current` in either command, and pins that a divergent
`compiled.md` is a finding, not a `current` source.

New test module: `tests/test_current_definition.py` (a focused module, well
under the 400-line cap, carrying module and function docstrings).

It must contain at least these three cases (reuse the corpus/`WorkingTreeSpec`
builders; do **not** hand-write `state.toml` strings, per ADR-002):

1. `test_recount_writes_drafted_sum_irrespective_of_compiled`: arrange a
   `working/` tree whose `[word_counts]` is stale against the drafts (so `recount`
   has something to correct), with `compiled.md` present as a **bytes-divergent**
   file carrying injected non-whitespace content (so its token count differs from
   the drafted sum — assert this divergence as an arrange-time precondition,
   computing `len(compiled_text.split())` and asserting it `!=` the drafted sum,
   which holds here because the content is non-whitespace, **not** because of the
   separator). `recount` never reads `compiled.md` and never runs the
   disk-evidence detector, so it succeeds. Run `recount` (chdir into the tree's
   parent first, per `docs/execplans/roadmap-2-3-1.md` Decision Log D-CWD).
   Assert the written `[word_counts].current` equals the drafted sum
   (`recount_words(working_dir, manifest)[0]`) and does **not** equal the compiled
   token count. (The same divergent `compiled.md` would REFUSE under
   `check`/`reconcile`; case 1 is scoped to `recount`, which ignores it.)
2. `test_reconcile_recount_writes_same_current_as_recount`: arrange the
   `done-flag-real-draft-undercount` corpus variant — `[word_counts].by_chapter`
   is stale against the drafts (fires `word-counts-match-drafts`) while
   `compiled.md` is absent or an exact `concatenate_drafts` of the present drafts
   (so `compiled-matches-drafts` does NOT fire and REFUSE does not dominate).
   Run `reconcile`; assert the written `current` equals the drafted sum and
   equals what `recount` would write on the same drafts. The cleanest form
   asserts both commands' written `current` against a single
   `recount_words(working_dir, manifest)[0]` oracle. This case asserts
   recount==reconcile agreement only; it makes **no** claim about a compiled
   token count (there is no divergent compiled token count on this tree — see
   D-FIXTURE-MATRIX).
3. `test_compiled_divergence_is_a_finding_not_a_current_source`: arrange the
   `compiled-not-concatenation-of-drafts` corpus variant
   (`compiled="not the real concatenation"`), the only tree whose `compiled.md`
   token count diverges from the drafted sum (injected non-whitespace tokens).
   Run `check` (read-only, via the `test_novel_state_check_disk.py` `_drive_check`
   pattern) and assert it reports the `compiled-matches-drafts` invariant and
   exits 4 (`ExitCode.ACTIONABLE_FINDING`); assert `state.toml`'s `current` is
   byte-for-byte unchanged (the checker writes nothing); and assert the drafted
   sum (`recount_words(...)[0]`) differs from `len(compiled_text.split())` here,
   so the "not the compiled token count" property is proven on the one tree where
   a divergent compiled token count actually exists. This proves compiled
   divergence is surfaced as a finding without redefining `current`.

A property test (`hypothesis`) is **not** required: the example-based matrix above
covers the agreement guarantee and the finding boundary, and the divergence
mechanism (injected non-whitespace content) is not a fruitful generation space.
Do not add one.

Docs to read first: `tests/test_recount_unit.py` (recount invocation pattern and
the `monkeypatch.chdir(working.parent)` D-CWD discipline, plus the `_chapter` /
`_drafting_spec` / `by_chapter_override` / `current_words_override` helpers for
a stale-table tree); `tests/test_reconcile.py`,
`tests/test_reconcile_integration.py`, `tests/test_reconcile_derivation.py`
(reconcile RECOUNT invocation and the `recounted_current` assertion at
`test_reconcile_derivation.py:122-134`, which already uses the
`done-flag-real-draft-undercount` variant); `tests/test_novel_state_check_disk.py`
(the `_drive_check` helper, the `incoherent_tree` fixture, and the exit-4 +
`violations`/`reconciliation` assertion shape for case 3);
`tests/working_corpus/_specs.py:157-160,182` and `tests/working_corpus/_variants.py:189-192`
(the `compiled` field and the `compiled-not-concatenation-of-drafts` variant);
`docs/execplans/roadmap-2-3-1.md` D-CWD; `docs/execplans/roadmap-2-3-2.md` (the
RECOUNT precedence and `word-counts-match-drafts` trigger).

Skills to load: `python-router` -> `python-testing` (fixtures, parametrization,
the unit/behavioural boundary); `leta` (locate `recount`, `reconcile`,
`derive_reconciliation`, `disk_word_counts`, `recount_words`, the corpus
`WorkingTreeSpec`/variant builders, and their existing tests); `sem` (use
`sem blame`/`sem diff` to confirm how the 2.3.1/2.3.2 tests already build trees,
so the new module reuses rather than reinvents the fixtures).

Tests this work item adds: the new `tests/test_current_definition.py` module
(unit/integration scope). No behavioural `.feature` file is required — the
recount and reconcile `.feature` scenarios already exist
(`tests/features/recount.feature`, `tests/features/reconcile.feature`); this
is a focused cross-command regression guard, not a new workflow.

Validation:

- The new test must fail **red** if either path is hypothetically pointed at the
  compiled token count: demonstrate this by temporarily editing `wordcount.py`
  (e.g. counting `compiled.md` tokens) and confirming case 1/case 2 fail, then
  revert (do not commit the temporary edit). This proves the guard is
  not a tautology (Risk mitigation). Confirm `git diff` is empty for production
  before committing.
- Run `make all` and expect all suites green including
  `tests/test_current_definition.py`.
- Report the exact pass count delta from `make test`.

Commit: a single commit (e.g. "Pin recount/reconcile agreement and compiled-finding
boundary on the drafted-sum `current`").

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-5`.

1. Confirm the branch (expect `roadmap-2-3-5`):

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-5 \
     branch --show-current
   ```

2. Work item 1 — design prose. Edit
   `docs/novel-ralph-harness-design.md` §4.1 and §5.4 as described, then run
   `make markdownlint` and `make nixie`. Expect no findings. Commit.

3. Work item 2 — contradictions. Edit
   `skill/novel-ralph/references/state-layout.md:114` and
   `novel_ralph_skill/state/schema.py:237`, then run `make all`,
   `make markdownlint`, and `make nixie`. Expect all green. Commit.

4. Work item 3 — regression test. Add
   `tests/test_current_definition.py`, prove it fails red under a temporary
   compiled-token edit, revert the temporary edit (confirm production `git diff`
   is empty), then run `make all`. Expect all green with the new module included.
   Commit.

5. Update this ExecPlan's `Progress`, `Surprises & Discoveries`, and
   `Outcomes & retrospective` after each work item, and append the revision note.

## Validation and acceptance

Acceptance is observable behaviour and document agreement:

- **Document agreement.** `skill/novel-ralph/references/state-layout.md`,
  `novel_ralph_skill/state/schema.py` (`WordCounts.current`),
  `docs/novel-ralph-harness-design.md` §4.1/§5.4, and
  `docs/execplans/roadmap-2-3-1.md` D-CURRENT all state that `current` is the
  drafted sum, with a bytes-divergent `compiled.md` named as the
  `compiled-matches-drafts` finding and never a `current` source. A
  repository-wide search for "(or sum of drafts)" / "in `compiled.md` or the sum
  of drafts" returns no live `current` definition (only execplan history and the
  roadmap task text).
- **Regression guard.** `tests/test_current_definition.py` passes: `recount`
  writes `current == drafted sum` irrespective of `compiled.md`; the `reconcile`
  RECOUNT path writes the identical `current`; and a bytes-divergent `compiled.md`
  is reported by `check` with exit 4 (`compiled-matches-drafts`) while `current`
  is untouched and the drafted sum differs from the compiled token count there.
  The module fails red if either path is pointed at the compiled token count
  (demonstrated, then reverted).
- **Quality gates.** `make all` passes (build, check-fmt, lint, typecheck,
  test). `make markdownlint` and `make nixie` pass for the Markdown changes.

Quality criteria (what "done" means):

- Tests: `make test` passes, including the new module; report the pass count.
- Lint/typecheck: `make lint` and `make typecheck` clean; `interrogate`
  docstring gate green.
- Docs: `make markdownlint` and `make nixie` clean.

Quality method: run the gates sequentially (never in parallel — the build cache
serialises best that way, AGENTS.md), once per work item, before each commit.

## Idempotence and recovery

Every step is a documentation or additive-test edit and is re-runnable without
drift. The temporary compiled-token edit in work item 3 is the only mutating
detour; it must be reverted before committing (use `git diff` / `git checkout
--` to confirm the working tree carries only the intended changes). If a gate
fails, fix forward within the tolerance (3 attempts) and re-run; nothing here
touches persisted user state, so there is no rollback hazard beyond reverting the
working tree.

## Interfaces and dependencies

No new interface. The plan depends only on already-shipped symbols:

- `novel_ralph_skill.state.wordcount.recount_words(working_dir, manifest) ->
  tuple[int, Mapping[str, int]]` — the one counting rule (used as the test
  oracle).
- `novel_ralph_skill.state.disk_evidence.disk_word_counts(state, working_dir)` —
  the disk-derived `(current, by_chapter)` the reconcile RECOUNT path writes; and
  `COMPILED_MATCHES_DRAFTS = "compiled-matches-drafts"` (the finding name).
- `novel_ralph_skill.state.reconcile.derive_reconciliation` and
  `ReconcileAction.RECOUNT` / `.REFUSE` — the precedence the test arranges
  fixtures against.
- `novel_ralph_skill.commands._recount.recount` and the `reconcile` mutator in
  `novel_ralph_skill.commands._reconcile` — the two commands whose `current`
  writes are pinned equal; plus `check` driven through the
  `test_novel_state_check_disk.py` `_drive_check` pattern for case 3.
- Test stack: `pytest`, `pytest-bdd`, `tomlkit`, and the existing
  `tests/working_corpus/` `WorkingTreeSpec` builder and variants
  (`done-flag-real-draft-undercount`, `compiled-not-concatenation-of-drafts`),
  reused, not reinvented.

cuprum (`0.1.0`, `uv.lock:113`) is a transitive lock dependency but is **not**
used by any module in scope (no `cuprum`/`sh`/`subprocess` import), matching the
`docs/execplans/roadmap-2-3-1.md` D-CUPRUM precedent.

## Revision note

- 2026-06-24 (planning agent, round 1): initial DRAFT. Three work items —
  record the decision, reconcile the two contradictions, pin the
  recount/reconcile agreement with a regression test.
- 2026-06-24 (planning agent, round 2): resolved the design-review blocking
  points. (B1/B3) Struck the false premise that the `"\n\n"` separator or
  trailing/leading whitespace can make the compiled token count diverge from the
  drafted sum; recorded D-TOKEN-EQUALITY (verified empirically) establishing the
  counts are equal for any byte-exact concatenation, so divergence requires
  injected non-whitespace content (a non-concatenation `compiled.md`). Rewrote
  Purpose, Constraints, Risks, and the Decision Log accordingly. (B2) Removed the
  impossible "coherent compile with divergent token count" requirement from the
  RECOUNT-path tree (case 2 now asserts recount==reconcile agreement only).
  (B3) Work item 3 case 1 now realises the divergence with a bytes-divergent
  `compiled.md` carrying injected non-whitespace content (not the separator), and
  is scoped to `recount`, which ignores `compiled.md`. (B4) Rebuilt the fixture
  matrix (D-FIXTURE-MATRIX) so the "not the compiled token count" assertion lives
  only on case 3, the bytes-divergent `compiled-matches-drafts` REFUSE tree —
  the one tree where a divergent compiled token count legitimately exists — and
  reused the existing `compiled-not-concatenation-of-drafts` corpus variant.
  Added an arithmetic-surprise tolerance. Remaining work: implementation per the
  three items after approval.
- 2026-06-24 (implementing agent): executed all three work items. WI1 added the
  drafted-sum sentence to design §4.1 and the bytes-divergence-is-a-finding
  sentence to §5.4; WI2 corrected `state-layout.md:114` and the
  `WordCounts.current` docstring; WI3 added `tests/test_current_definition.py`
  (three D-FIXTURE-MATRIX cases, fail-red proven and reverted). `make all` green
  (591 passed / 1 skipped), `make markdownlint` / `make nixie` clean, coderabbit
  0 findings on WI1 and WI2. The repo-wide `make fmt` markdown churn was stashed
  and discarded per the recurring repository convention.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews and audits of step 2.3's tasks. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge. The substantial DRY findings
(audit-2.3.5 Findings 1-4: the `[word_counts]` write consolidation and the
single whitespace-token counter) are cross-cutting hygiene that does not serve
step 2.3's disk-re-derivation hypothesis, so they are re-routed to roadmap step
7.14 rather than filed here.

- [x] 2.3.5.1 — Add a check/reconcile REFUSE assertion to case 1's divergent
  `compiled.md` tree (from review:2.3.5, low). Case 1 documents in a comment that
  the same divergent `compiled.md` "would REFUSE under check/reconcile" but
  exercises only `recount` (which ignores it); case 3 covers the REFUSE on a
  different variant. Add the missing assertion (or reuse case 1's tree under
  `check`) so recount-ignores-it and check-refuses-it are proven on the *same*
  tree, closing the boundary loop. Gate with `make all`.
- [x] 2.3.5.2 — Harden the reconcile-path divergence guards against the
  shared-oracle and shared-validator blind spots (from review:2.3.5, low). Two
  coupled residual weaknesses: case 2's recount==reconcile agreement test uses
  `recount_words` as both oracle and subject-under-guard, so it cannot detect a
  refactor that repoints the shared counting helper; and the reconcile-path
  fail-red leans on `_refuse_if_incoherent`'s by-chapter-sum validator firing
  (exit 3) before the test's own assertion, so a future refactor pointing both
  `current` and `by_chapter` at compiled-derived values could pass the validator
  and make the shared-oracle assertion tautological. Pin `by_chapter` to the
  honest drafted sum independently of the `current` write for at least one
  fixture so the reconcile guard is discriminating. Low priority; the current
  matrix already covers the realistic refactor surface and the limitation is
  documented in this plan. Gate with `make all`.
- [x] 2.3.5.3 — Move the D-TOKEN-EQUALITY rationale into the durable design doc
  (from audit:2.3.5, low). The reason a `compiled.md` divergence can only come
  from non-whitespace content — so pinning `current` to the drafted sum loses no
  information — lives only in this ExecPlan and a test docstring, while design
  §4.1/§5.4 assert only the conclusion. Add one sentence to §4.1/§5.4 so the
  load-bearing rationale lives in the stated source of truth. Gate with `make
  markdownlint` and `make nixie`.
