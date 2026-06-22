# Logisphere design review — roadmap 1.3.2 (round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-1-3-2.md`.
Verdict: **Revise.** The plan is well-anchored to the design and correct on
most factual claims (versions, paths, phase enum, invariants 1-7, the cuprum
non-dependency, the `tomlkit` write mandate). Two blocking defects concern
design conformance and the established cross-module-import contract; several
advisories tighten scope and coverage.

Documents relied on: `docs/novel-ralph-harness-design.md` §3.4, §4.2, §4.3,
§5.1, §5.2, §5.3, §5.4, §9, §10; `skill/novel-ralph/references/state-layout.md`
(full); `docs/developers-guide.md` "Shared test scaffolding"; `AGENTS.md` lines
18-27, 71-98, 141-166; `docs/roadmap.md` 1.3.2; `tests/conftest.py`;
`pyproject.toml` and `uv.lock` (version pins). Skill:
`logisphere-design-review`.

## Blocking defects (return to planner)

### B1 — `compiled-references-absent-chapter` variant assumes a chapter-naming convention the design does not define (Telefono / Pandalump)

Work item 3 (plan lines 546-549) builds an incoherent variant
`compiled-references-absent-chapter` described as "a `compiled.md` *naming* a
chapter with no `draft.md`", and the `corpus_check` oracle (lines 531-536) is
asserted to flag it. But the design models `compiled.md` as the **ordered
concatenation of the chapter drafts with consistent separators**, verified **by
content hash**, with no structured chapter references inside it (design §4.3
lines 322-344; §9 lines 119-121: "Compile fidelity … equals the ordered
concatenation of the chapter drafts … `novel-compile --check` … compares
content hashes rather than header[s]"). Nothing in the design defines a
parseable "chapter reference" or heading syntax inside `compiled.md`; the
separator format is named ("consistent separators") but never pinned.

Consequently the corpus-local oracle cannot detect "compiled.md references an
absent chapter" without inventing a separator/heading grammar the design does
not have — which violates the plan's own Tolerance "if the §5.1 schema fields
or §5.2 invariants … appear to need changing … stop and escalate" and the
Constraint against silent corpus changes. The contradiction §5.4/§10 actually
describe is hash-level: the compiled content does not match the concatenation
of the drafts that exist on disk.

Required fix: reframe this variant so it is detectable under the design's
actual compile model — e.g. a `compiled.md` whose content is **not** the
hash-equal concatenation of the present chapter drafts (a stale/contradictory
compile), with the oracle comparing compiled content against the concatenated
drafts rather than parsing chapter names. If the planner believes a heading
convention is intended, that is a design under-specification to **escalate**,
not to resolve by inventing a format in a test fixture.

### B2 — direct cross-module imports of the spec library, oracle, and dataclasses contradict the established no-value-import contract (Pandalump / Dinolump)

The plan routes the *builder* through fixtures (`working_tree`,
`incoherent_tree`, `done_flag_tree`) but the test code it specifies references
module-level names directly: Work item 2 writes `working_tree(PHASE_STATES[p])`
and `working_tree(PHASE_STATES["drafting"])` (lines 503, 508-510); Work item 3
references `INCOHERENT_VARIANTS` and `corpus_check` (lines 559-566); the
end-state surface lists `WorkingTreeSpec`, `ChapterSpec`, `corpus_check`,
`PHASE_STATES`, `INCOHERENT_VARIANTS`, `DONE_FLAG_PERMUTATIONS` as module-level
values (lines 706-737). For `tests/test_working_corpus.py` to use those names
it must `from working_corpus import …` — a cross-module value import.

The developers-guide is categorical: test modules consume scaffolding "by
fixture name … and never by importing from another test module or from
`conftest` itself", and "New shared scaffolding belongs in `tests/conftest.py`
as another fixture"; the **only** sanctioned exception is a
`TYPE_CHECKING`-only type import (developers-guide lines 31-52). Six prior
audits (`audit-1.2.1`…`1.2.7`, cited in `conftest.py` lines 8-10) were
specifically about cross-module imports and duplicated helpers. The plan's own
Constraint (lines 197-200) restates this rule, then the work items violate it.

This is internally contradictory: the plan adds a `phase_state_spec` fixture
returning the mapping (line 503-504) yet its example test still indexes
`PHASE_STATES[p]` rather than the fixture value. Either:

- route **all** corpus data and the oracle through fixtures (tests receive
  `PHASE_STATES`, `INCOHERENT_VARIANTS`, `corpus_check`, and spec constructors
  by parameter name), and fix every example to use the fixture value; or
- obtain an explicit, documented amendment to the developers-guide sanctioning
  imports from a dedicated non-`test_*` data module
  (`tests/working_corpus.py`) — distinct from the prohibited "another test
  module" — covering values, not just `TYPE_CHECKING` types.

As written the plan does neither cleanly; it must pick one and make every work
item conform. Note that even the builder-as-fixture pattern needs the spec
*types* (`WorkingTreeSpec`/`ChapterSpec`) to construct ad-hoc specs in tests,
so the type-import question must be resolved regardless.

## Advisories (strongly recommended, not gating the verdict alone)

### A1 — `state.toml` table coverage for "parse without loss" is under-specified (Telefono)

The success criterion and Risk #1 hinge on phase 2 (task 2.1.1) parsing the
corpus "without loss". The schema (state-layout.md §5.1 lines 63-116) carries
`[novel]` (title/slug/target_word_count/created_at), `[drafting.critic].pass`,
`last_finding_counts`, and `[drafting.fangirl].last_chapter_passed`. The
`WorkingTreeSpec` (plan lines 720-737) carries none of these; the prose says
the builder writes `[novel]`/`[drafting]`/`[drafting.critic]` tables but never
says with what values. State whether the builder emits these required tables
with fixed deterministic defaults (it must, or 2.1.1's parse hits absent
fields). Carrying them as builder constants is fine for 1.3.2; omitting them
entirely is a "consumed unchanged" hazard.

### A2 — `by_chapter` key format unpinned (Telefono)

state-layout.md keys `word_counts.by_chapter` by zero-padded **string**
(`{ "01" = 3200, … }`, line 115). The plan's
`by_chapter_override: Mapping[str, int]` and invariant-3 self-test must use
that exact key form, and the oracle's sum check must read the same keys. Pin
the key format in Work item 1 so the corpus and the eventual validator agree.

### A3 — `[pending_turn]` shape is unanchored (Telefono / Doggylump)

The design never pins `[pending_turn]` fields beyond "the operation in flight
and the paths it will write" (§3.4 lines 227-235; §5.1 line 396). The plan's
`pending_turn: Mapping[str, object] | None` is appropriately loose, but the
torn-turn variant (`uncleared-pending-turn`, lines 550-551) never says what it
contains. Anchor the variant's record to "an `operation` key and a `paths` key"
per §3.4 so task 2.3.2's reconciliation has a concrete shape to read, or state
explicitly that the precise field set is deferred to 2.3.2 and the corpus
carries only a non-empty marker.

### A4 — invariant-7 gate thresholds must be encoded, not asserted (Doggylump)

Invariant 7 (gate true only once `current/target` crosses the threshold) needs
the three thresholds (0.30/0.50/0.80, state-layout.md lines 174-177) to be a
single source of truth shared between the coherent gate booleans, the
`gate-true-below-threshold` variant, and the oracle. The plan names the variant
but not where the thresholds live; pin them once (read from the reference if
practical, mirroring the phase-order single-source approach in Work item 2).

### A5 — oracle/validator drift acknowledged but the cross-check is not wired (Wafflecat / Dinolump)

Risk #3 says task 2.1.2 "can assert the real validator agrees with the corpus
labels". For that to be possible, the corpus must expose its labels (the
coherent set and the `variant -> violated-invariant` map) as a stable,
importable contract. Confirm `INCOHERENT_VARIANTS` (variant -> invariant-name)
and the coherent set are part of the documented public surface (Work item 5
lists them, good) and that the invariant **names** the oracle returns are the
same strings 2.1.2 will key on — otherwise the cross-check the risk relies on
cannot be written. State the canonical invariant-name vocabulary explicitly.

## Pre-mortem (Doggylump)

Six months on, phase 2 lands and 2.1.2's Hypothesis validator disagrees with
the corpus on which variants are coherent, because (a) the corpus-local oracle
for `compiled-references-absent-chapter` parsed an invented heading format the
real `novel-compile` hash check never uses (B1), so the "incoherent" variant is
actually coherent-under-hash or vice versa; and/or (b) a test reached into
`working_corpus` by value import (B2), an audit flagged it post-merge as the
seventh cross-module-import finding, and the "consumed unchanged" criterion is
breached when the import is refactored. Most-likely missed signal: the corpus
self-test passes against its own oracle while the oracle encodes a compile
model the design does not have. Prevention designed in now: fix B1 so the
oracle uses the hash/concatenation model, and fix B2 so the corpus contract is
fixture- or sanctioned-module-based, both before any code.

## Alternatives checkpoint (Wafflecat)

The strongest alternative: drop the bespoke `corpus_check` oracle entirely and
prove the coherent/incoherent split structurally — coherent variants are built
by a constructor that *cannot* express a violation (types make illegal states
unrepresentable), and each incoherent variant is built by a single explicit
mutation of `COHERENT_BASELINE` whose diff *is* the proof of which invariant it
breaks. Trade-off: loses the executable "exactly one invariant violated"
assertion the plan values (Risk #2 mitigation) and the 2.1.2 cross-check hook
(A5); gains the elimination of the oracle-drift risk (Risk #3) and sidesteps B1
(no compile-parsing oracle to mis-specify). Not clearly better, but it shows
the oracle is a *choice* carrying real risk, not a given — and if B1 proves the
compile contradiction genuinely is not locally checkable, the mutation-diff
approach is the fallback.

## What the plan gets right (for the record)

- Versions verified against `uv.lock`, not memory: tomlkit 0.15.0, cuprum 0.1.0,
  hypothesis 6.155.7, syrupy 5.3.2 — all correct.
- cuprum genuinely not needed (design §9 line 711 "v1 commands shell out to
  nothing"); the existing cuprum fixtures are unrelated. Correctly excluded.
- Paths match state-layout.md / §5.1 exactly, including the correct rejection of
  the earlier-draft `working/compiled.md` and `working/chapter-NN/` paths.
- Phase enum (eleven members, order) and invariants 1-7 transcribed faithfully
  from §5.1/§5.2, including the "consecutive_clean ≤ chapters drafted" and
  "convergence_target ≥ 1" refinements.
- `tomlkit` write mandate, the read-back-with-`tomllib` and idempotent-dump
  round-trip guards (Risk #4 mitigation) are sound and directly serve task
  2.2.1.
- Determinism rules (fixed `created_at` literal matching line 70, fixed draft
  bodies, no timestamps/random ids) correctly satisfy the snapshot constraints.
- factory-as-fixture pattern matches the house style and is cited to the pytest
  stable docs.
