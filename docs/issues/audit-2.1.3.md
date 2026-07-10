# Post-merge audit — roadmap task 2.1.3

Audit of the codebase after roadmap task 2.1.3 ("Assert the §5.2 validator
agrees with the corpus oracle on every fixture, keyed on
`CORPUS_INVARIANT_NAMES`") merged to `main` at commit `625d6ea`. The slice adds
a whole-corpus *live-draft* cross-check: the table-reading §5.2 validator
([`state/validate.py`](../../novel_ralph_skill/state/validate.py)) is
compared, on every corpus tree, against an independent oracle
([`tests/working_corpus/_live_draft.py`](../../tests/working_corpus/_live_draft.py))
that recomputes the two word-count proxies — the drafted-words total and the
drafted-chapters count — from the on-disk `chapter-NN/draft.md` bodies rather
than the `[word_counts]` table. A new divergent-table fixture
([`test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py))
discriminates the live read from a table read, and the shared parse-handling
helpers move into
[`_state_corpus_support.py`](../../tests/_state_corpus_support.py). The
live-draft fixtures are split into
[`corpus_live_draft_fixtures.py`](../../tests/corpus_live_draft_fixtures.py),
registered as a second pytest plugin, to keep `corpus_fixtures.py` within the
400-line cap.

The slice is sound, well documented (the developers' guide "Invariant
validation" section was extended), and well covered: the whole-corpus agreement
test, a liveness self-test, a discrimination test, and a proxy-decoupling guard
together pin the cross-check from several angles. None of the findings below is
a blocking defect; the dominant theme is duplication that the slice's own
documentation acknowledges but does not yet fold, plus minor ergonomic and
test-hygiene snags.

Trail followed: explored with `leta`/reads over `state/validate.py`,
`tests/working_corpus/_live_draft.py`, `tests/working_corpus/_oracle.py`,
`tests/working_corpus/_specs.py`, `tests/_state_corpus_support.py`,
`tests/test_validate_state_live_draft.py`,
`tests/test_validate_state_corpus.py`, `tests/conftest.py`, and
`tests/corpus_live_draft_fixtures.py`; traced history with `git show 625d6ea`
and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §5.2 and §9, `docs/developers-guide.md`
"Invariant validation", `docs/roadmap.md` task 2.1.3,
`docs/adr-003-shared-interface-contract.md`, prior
`docs/issues/audit-2.1.2.md` and `audit-2.1.4.md`, and `AGENTS.md`. Each
finding records a category, a location, a description, a concrete proposed fix,
and a severity.

## Finding 1 — The live-draft oracle re-parses `state.toml` three times per tree

- Category: complexity
- Severity: medium
- Location:
  [`tests/working_corpus/_live_draft.py`](../../tests/working_corpus/_live_draft.py)
  lines 95–107 (`_check_by_chapter_sum_live`), 110–133
  (`_check_gate_ratio_live`), 136–150 (`_check_consecutive_clean_live`),
  invoked from `live_draft_owned` (lines 183–195).
- Description: each of the three `_check_*_live` predicates independently opens,
  reads, and `tomllib.loads`-parses `working_dir / "state.toml"`. A single call
  to `live_draft_owned` therefore decodes the same `state.toml` three times,
  and a fourth time indirectly through the `corpus_check` reuse on line 184
  (which reads the materialized tree again for its own disk-evidence
  predicates). The repeated
  `state = tomllib.loads((working_dir / "state.toml").read_text(...))` line is
  a verbatim data clump copied across the three predicates. This is test-side
  code, so the cost is negligible, but the triplicated read-and-parse line is
  an ergonomic and clarity snag and a small drift surface (three places must
  agree on how the table is decoded).
- Proposed fix: parse `state.toml` once at the top of `live_draft_owned` and
  pass
  the decoded `[word_counts]` / `[gates]` / `[drafting]` sub-tables (or the
  whole mapping) into the three predicates as arguments, turning them into pure
  functions over already-decoded data. This removes two redundant reads,
  collapses the triplicated decode line to one site, and makes each predicate
  trivially unit testable without a filesystem round-trip.

## Finding 2 — The five disk-evidence invariant names are duplicated across two test modules

- Category: duplication
- Severity: medium
- Location:
  [`tests/test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
  lines 64–72 (`_DISK_EVIDENCE_NAMES`) and
  [`tests/test_validate_state_corpus.py`](../../tests/test_validate_state_corpus.py)
  lines 55–63 (`_DEFERRED_INVARIANT_NAMES`).
- Description: both modules hard-code the identical five-element frozenset
  (`manifest-disk-bijection`, `done-flag-without-draft`,
  `compiled-matches-drafts`, `pending-turn-cleared`, `cursor-plan-present`)
  under two different names. They are the same concept — the disk-evidence
  names the §5.2 validator never owns — and are written out twice as string
  literals. A name added to or removed from the disk-evidence set (for example
  when task 2.3.2 lands) must be edited in two places, and nothing pins the two
  copies equal, so they can silently drift. This is exactly the
  shared-vocabulary duplication the `_state_corpus_support.py` lift-out was
  created to avoid.
- Proposed fix: define the disk-evidence name set once in
  `tests/_state_corpus_support.py` (the existing shared home for both suites) —
  or, better, derive it as
  `set(CORPUS_INVARIANT_NAMES) - set(PURE_STATE_INVARIANT_NAMES)` so it cannot
  drift from the owned vocabulary at all — and import it into both test modules.

## Finding 3 — `by-chapter-sum` now has a third hand-copied predicate twin

- Category: similarity
- Severity: medium
- Location:
  [`tests/working_corpus/_live_draft.py`](../../tests/working_corpus/_live_draft.py)
  lines 95–107 (`_check_by_chapter_sum_live`), twinning
  [`tests/working_corpus/_oracle.py`](../../tests/working_corpus/_oracle.py)
  lines 108–119 (`_check_by_chapter_sum`) and, in spirit,
  [`novel_ralph_skill/state/validate.py`](../../novel_ralph_skill/state/validate.py)
  lines 125–135 (`_check_by_chapter_sum`).
- Description: the
  `sum([word_counts].by_chapter.values()) == [word_counts].current` predicate
  now exists in three places. The production
  validator and the `_oracle` twin are a *deliberate* independent cross-check
  (documented in the developers' guide and pinned by
  `test_incoherent_agreement_restricted_to_owned`). The live-draft copy is a
  third hand-written restatement of the *table-internal* read; its own
  docstring (lines 98–104) frames it as "a deliberate twin of
  `_oracle._check_by_chapter_sum`", but unlike the validator/oracle pair there
  is no contract test pinning the live-draft copy equal to the other two.
  Because `by-chapter-sum` is explicitly *not* a live quantity (it has no draft
  analogue), the live oracle gains nothing from re-implementing it
  independently — it is reading the same table the `_oracle` twin reads, so the
  third copy is duplication without the independent-cross-check justification
  the other two have.
- Proposed fix: have `live_draft_owned` reuse the `by-chapter-sum` verdict it
  already obtains from `corpus_check(spec, working_dir)` (line 184) instead of
  discarding it (line 188) and recomputing it via `_check_by_chapter_sum_live`,
  then delete `_check_by_chapter_sum_live`. The `corpus_check` result already
  includes `by-chapter-sum` from the `_oracle` twin, so the live oracle would
  carry it straight through — collapsing three copies of the table read to the
  two with a genuine independent-cross-check rationale. If the
  self-contained-module property is judged worth keeping, add a contract test
  pinning the live copy equal to `_oracle._check_by_chapter_sum` so the third
  twin cannot drift unnoticed.

## Finding 4 — The §5.2 gate thresholds are exposed only as a private name two suites reach into

- Category: ergonomics
- Severity: low
- Location:
  [`novel_ralph_skill/state/validate.py`](../../novel_ralph_skill/state/validate.py)
  line 73 (`_GATE_THRESHOLDS`); imported as a private name by
  [`tests/test_validate_state_corpus.py`](../../tests/test_validate_state_corpus.py)
  line 42 and
  [`tests/test_validate_state_property.py`](../../tests/test_validate_state_property.py)
  line 62.
- Description: the production gate-threshold triple `(0.30, 0.50, 0.80)` is the
  §5.2 source of truth, but it is named with a leading underscore
  (module-private) and is not re-exported from
  `novel_ralph_skill.state.__init__`. Two test modules nevertheless import
  `_GATE_THRESHOLDS` across the package boundary to pin the corpus copy and the
  property generator against it. Reaching into another module's private name is
  the cross-module-private-import smell the project has repeatedly flagged and
  lifted (the `conftest.py` rationale cites six prior audits doing exactly this
  for test helpers). A private name imported from outside also cannot be
  renamed safely despite its underscore promising it can.
- Proposed fix: promote the constant to a public, exported name —
  `GATE_THRESHOLDS` in `state/validate.py`, re-exported through
  `novel_ralph_skill.state.__init__` alongside the invariant-name constants —
  and update the two test imports. This makes the cross-module dependency a
  sanctioned public contract (the §5.2 thresholds) rather than a private-name
  reach-through, and aligns the threshold constant's visibility with the
  invariant-name constants it sits beside.

## Finding 5 — Each agreement suite re-derives the owned-name restriction inline

- Category: duplication
- Severity: low
- Location:
  [`tests/_state_corpus_support.py`](../../tests/_state_corpus_support.py)
  lines 45–48 (`validator_verdict`), with callers intersecting its result
  against the owned set inline in
  [`tests/test_validate_state_live_draft.py`](../../tests/test_validate_state_live_draft.py)
  (lines 208–219, 257, 286) and
  [`tests/test_validate_state_corpus.py`](../../tests/test_validate_state_corpus.py)
  (lines 135–146).
- Description: `validator_verdict` returns the validator's *full* verdict, and
  every call site that needs the owned subset writes
  `validator_verdict(working_dir) & owned` or
  `& set(PURE_STATE_INVARIANT_NAMES)` by hand — the `set(...)` construction and
  the intersection are repeated across both suites (nine sites). The owned
  restriction is the common operation both agreement suites actually want;
  spelling it out at each site is small but repeated boilerplate and a place a
  future reader could forget the restriction and compare a full verdict against
  an owned-only oracle by mistake.
- Proposed fix: add a thin `validator_owned_verdict(working_dir) -> set[str]`
  helper to `_state_corpus_support.py` that returns
  `validator_verdict(working_dir) & set(PURE_STATE_INVARIANT_NAMES)`, and route
  the owned-restriction call sites through it. Keep the unrestricted
  `validator_verdict` for the two tests that legitimately assert against the
  full verdict (`test_coherent_trees_pass_the_validator`,
  `test_by_chapter_sum_variant_names_only_by_chapter_sum`).

## Finding 6 — No user-facing documentation describes the `novel-state check` verdict vocabulary

- Category: docs-gap
- Severity: low
- Location:
  [`docs/users-guide.md`](../../docs/users-guide.md) (the `novel-state`
  section); the validator owns eight named invariants in
  [`novel_ralph_skill/state/validate.py`](../../novel_ralph_skill/state/validate.py)
  lines 60–69.
- Description: the §5.2 validator now emits eight named invariant verdicts
  (`phase-in-enum`, `completed-prefix`, `by-chapter-sum`, the three
  `consecutive-clean`/`convergence` sub-rules, `cursor-coherent`,
  `gate-ratio-consistent`) into the operator-facing refusal envelope, and 2.1.3
  hardened the guarantee that these names are stable and exhaustively
  cross-checked. The developers' guide documents this vocabulary thoroughly,
  but the users' guide — the operator's reference for what a
  `novel-state check` refusal *means* — does not enumerate the invariant names
  or explain what each rejection tells the operator to fix. An operator who sees
  `gate-ratio-consistent` in a refusal envelope has no user-level reference
  for it. (This compounds the open user-docs gap recorded in `audit-2.2.2.md`
  Finding 1.)
- Proposed fix: add a short "validation verdicts" subsection to the
  `novel-state`
  section of `docs/users-guide.md` listing the eight owned invariant names with
  a one-line operator-facing meaning for each (what state contradiction it
  flags and the typical corrective action), cross-referenced to the design §5.2
  wording. Fold this into the broader users-guide update `audit-2.2.2.md`
  already proposes.
