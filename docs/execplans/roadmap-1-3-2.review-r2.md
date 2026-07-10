# Logisphere design review — roadmap 1.3.2 (round 2)

Adversarial pre-implementation review of `docs/execplans/roadmap-1-3-2.md`
(Status: DRAFT, revised round 2). Verdict: **Revise** — one blocking contract
defect remains (a residue of the round-1 B2 fix), plus advisories.

Round-1 blocking defects B1 and B2 are otherwise well resolved and verified
against source. The plan is factually accurate: versions, paths, the phase
enum, invariants 1-7, the cuprum non-dependency, and the `tomlkit` write
mandate all check out against the design, `state-layout.md`, `pyproject.toml`,
`uv.lock`, and the read-only cuprum checkout.

Documents relied on: `docs/novel-ralph-harness-design.md` §3.4, §4.2, §4.3,
§5.1, §5.2, §5.3, §5.4, §9, §10; `skill/novel-ralph/references/state-layout.md`
(full); `docs/developers-guide.md` "Shared test scaffolding"; `AGENTS.md` lines
18-27, 71-98, 141-166; `docs/roadmap.md` 1.3.2; `tests/conftest.py`;
`/data/leynos/Projects/cuprum/cuprum/` (catalogue.py, program.py, sh.py,
builders/ present — confirms the API surface the conftest fixtures use exists);
`docs/execplans/roadmap-1-3-2.review-r1.md`. Skill: `logisphere-design-review`.

## Verification of the round-1 fixes

- **B1 resolved (verified).** Design §4.3 (lines 320-344) pins compile ordering
  as the zero-padded chapter index and the compile-and-hash routine as the sole
  fidelity mechanism; §9 (lines 705-711) and §4.2 (lines 307-318) confirm the
  only check is a content-hash comparison. §5.4 (line 499) and §10 (line 725)
  describe "a `compiled.md` referencing an absent chapter" only as informal
  prose; the design pins **no** parseable heading/separator grammar. The
  round-2 reframe to `compiled-not-concatenation-of-drafts`, detected by
  recomputing `concatenate_drafts` and comparing bytes, is design-conformant.
  The single `CORPUS_SEPARATOR` constant plus the escalation Tolerance for a
  divergent task-4.1.1 production separator is the correct hedge.
- **B2 substantially resolved (one residue — see D1).** Corpus values now route
  through `conftest` fixtures by parameter name; the `phase_state_spec`
  raw-mapping fixture is removed; the data/builder/oracle live in a dedicated
  non-`test_*` module. The remaining gap is the spec-*type* import contract.
- **No memory-based locked-library claims.** The plan scopes to `pathlib` +
  `tomlkit` + `pytest` (all locked) and cites the one external behaviour
  (pytest "Factories as fixtures") to the stable docs. No Cyclopts,
  pytest-xdist / pytest-timeout, or uv claim is made or relied upon, so there
  is nothing uncited to pin. cuprum is correctly excluded (design §9 line 711,
  "v1 commands shell out to nothing"), and its source confirms the conftest
  fixtures this task does not touch.

## Blocking defect (return to planner)

### D1 — the spec-type `TYPE_CHECKING` import is claimed as a sanctioned carve-out it is not, and the "no guide amendment" claim is self-contradictory (Telefono / Dinolump)

The plan rests its whole no-value-import resolution on this sentence (lines
276-280, echoed at 437-446 and 1032-1035): a test may name `WorkingTreeSpec` /
`ChapterSpec` by importing them from `tests/working_corpus.py` **only** under
`if TYPE_CHECKING:`, "which is the one carve-out the developers-guide
sanctions", and "This task adds no developers-guide amendment; it conforms to
the existing rule."

That is not what the guide says. The guide's carve-out (developers-guide
"Shared test scaffolding", the "One narrow exception" paragraph) is, verbatim,
"A type that describes a fixture's value … may be imported **from `conftest`**
under an `if TYPE_CHECKING:` guard (`from conftest import RepoTextReader`)."
The sanctioned exception is a type defined **in `conftest`**. The plan's spec
types live in `tests/working_corpus.py` — a third module the guide does not
mention at all. Importing `from working_corpus import WorkingTreeSpec` (even
under `TYPE_CHECKING`) is therefore **not** the documented carve-out; it is an
extension of it.

This re-introduces, one level up, exactly the internal contradiction round 1
flagged in B2 (rule restated, then bent):

- The plan says it "adds no developers-guide amendment" (line 280), yet Work
  item 5 (lines 866-881) explicitly proposes to document, in the
  developers-guide, that "the spec *types* may be imported solely under
  `if TYPE_CHECKING:`" from `tests/working_corpus.py`. Documenting a new
  import-contract clause for a new module **is** a guide amendment. The plan
  cannot both leave the guide unamended and write this clause into it.
- More fundamentally, the guide as written does not authorize a `TYPE_CHECKING`
  import from any module other than `conftest`. So the plan's central claim of
  conformance is false on the page it relies on most.

Either resolution is acceptable, but the plan must pick one and make every
mention consistent:

- **(a) Conform to the literal carve-out.** Define the spec *types*
  (`WorkingTreeSpec`, `ChapterSpec`) in `tests/conftest.py` (or re-export them
  from `conftest`) so any test annotation uses
  `from conftest import WorkingTreeSpec` under `TYPE_CHECKING` — the exact form
  the guide sanctions — while the corpus *data/builder/oracle* stay in
  `tests/working_corpus.py` and reach tests only through fixtures. Then "no
  amendment" is true.
- **(b) Amend the guide deliberately.** Keep the types in `working_corpus.py`,
  but have Work item 5 **explicitly extend** the carve-out: state that a spec
  type may be imported under `if TYPE_CHECKING:` from the single dedicated
  corpus data module `tests/working_corpus.py`, that `tests/conftest.py` is the
  module's sole runtime importer, and why this does not reintroduce the
  pytest-import-mode fragility the rule guards against (a `TYPE_CHECKING`
  import is `False` at runtime). Drop every "no amendment / conforms to the
  existing rule" claim and label Work item 5 as the amendment.

Note this is not pedantry about wording: the no-value-import contract is the
thing six audits (`audit-1.2.1`…`1.2.7`) were about, and the plan's own
Constraint (lines 256-269) makes it a hard invariant. A contract that the plan
both asserts it satisfies and quietly extends is precisely the kind of "passes
its own self-test while the contract has shifted" failure the pre-mortem warns
about. Pin the contract before code, in the words the guide will actually carry.

## Advisories (strongly recommended; not the sole basis for the verdict)

### A1 — the builder's chapter-directory file set is narrower than `state-layout.md`; state that the omission is deliberate and harmless to consumers (Telefono / Pandalump)

`state-layout.md` (lines 35-44) shows each `working/manuscript/chapter-NN/`
holding `scenes.md`, `beats.md`, `draft.md`, `critic-notes.md`,
`fangirl-notes.md`, and `done.flag`. The builder (Work item 1) writes only
`draft.md` and optional `done.flag`. That is almost certainly correct — the
§5.2 bijection is between `[chapters]` manifest entries and chapter
*directories* (not their inner files), and §4.3 compiles from `draft.md` only —
so the corpus is sufficient for every consumer the plan names (2.x check /
reconcile / compile, 3.x done-predicate). But the plan never says the omission
is intentional, and Risk #1 ("consumed unchanged … without loss") invites a
reviewer to ask whether a later slice (e.g. a fangirl- or critic-note consumer)
will need `critic-notes.md` / `fangirl-notes.md` present. Add one sentence to
"What this task does NOT do" or Work item 1 stating the builder deliberately
writes only the files §5.2/§4.3 depend on (`draft.md`, `done.flag`, the
manifest, `compiled.md`, the outline), and that the other reference files are
non-load-bearing for phases 2-6; escalate only if a consumer slice is later
found to need one.

### A2 — invariant 4 ("consecutive_clean ≤ chapters drafted") has no named incoherent variant (Doggylump / Wafflecat)

Invariant 4 has three independent sub-clauses:
`0 ≤ consecutive_clean ≤ convergence_target`; `convergence_target ≥ 1`; and
`consecutive_clean ≤ number of chapters drafted`. The variant set (Work item 3)
covers the first two (`consecutive-clean-over-target`,
`convergence-target-below-one`) but provides no variant exercising the third
(e.g. `consecutive_clean = 2` on a tree with zero or one drafted chapters).
Since the oracle is asserted to implement all of invariant 4 and the "every
oracle invariant string is exercised by at least one variant" guard (lines
809-812) keys on the *invariant name* not the sub-clause, the chapters-drafted
bound could go unimplemented or untested while the guard still passes. Either
add a `consecutive-clean-over-chapters-drafted` variant or state explicitly
that the third sub-clause shares the `consecutive-clean-bound` name and is
covered by a dedicated assertion in the split self-test.

### A3 — `word_counts.current` provenance for the gate variant is unstated; guard against an accidental invariant-3 break (Doggylump)

The `gate-true-below-threshold` variant must flip a gate boolean true while the
`current/target` ratio is below its threshold, **without** disturbing invariant
3 (`by_chapter` sums to `current`). `state-layout.md` line 114 notes
`current = "words in compiled.md (or sum of drafts)"`. The plan derives
`by_chapter` from each chapter's `draft_words` and `current` should equal that
sum. The variant must therefore lower the ratio by choosing chapter
`draft_words` whose sum keeps the gate below threshold, *not* by overriding
`current` (which would also break invariant 3 and make the variant violate two
invariants — the precise hazard Risk #2 and the split self-test exist to
catch). State in Work item 3 that `gate-true-below-threshold` adjusts the gate
boolean alone against an honest `current = sum(draft_words)`, leaving invariant
3 satisfied; the split self-test will catch a double violation, but pinning the
construction avoids the wasted iteration.

### A4 — the `done.flag`-empty-draft variant overlaps the coherent done-flag permutations; keep the boundary explicit (Pandalump)

Work item 3's `done-flag-empty-draft` (incoherent, §5.4 contradictory disk) and
Work item 4's `DONE_FLAG_PERMUTATIONS` (coherent flag states) both write
`done.flag` files. The distinction is solely whether the flagged chapter has a
non-empty `draft.md`. The plan states this once (lines 834-835) but the oracle
must be unambiguous that a coherent permutation with `draft_words > 0` on every
flagged chapter returns the empty tuple, while a flagged zero-word draft returns
`"done-flag-without-draft"`. Confirm the oracle's `done-flag-without-draft`
branch keys on `has_done_flag and draft_words == 0` (not merely
`has_done_flag`), so Work item 4's permutations are not spuriously flagged
incoherent.

## Pre-mortem (Doggylump)

Six months on, phase 2 lands. The most likely incident: an `audit-2.x` flags
`tests/test_*` importing `WorkingTreeSpec` from `working_corpus` as the
seventh+ cross-module-import finding, because the contract the plan claimed was
"sanctioned by the existing rule" was never actually written into the guide
(D1) — the guide still says the carve-out is `from conftest import`. Blast
radius: the "consumed unchanged" criterion breaks when the import is refactored
across every phase-2-6 consumer that copied the pattern. Missed signal: the
corpus self-test is green throughout, because the self-test never exercises the
import *contract*, only the materialized trees. Prevention designed in now:
resolve D1 by either putting spec types in `conftest` (literal carve-out) or
amending the guide in Work item 5 and dropping the "no amendment" claim — and
have Work item 5 state the contract in the exact words the guide will carry, so
a future audit checks against a written rule, not an asserted one.

Secondary scenario: a phase-2 consumer needs `critic-notes.md` present in a
chapter directory (A1) and discovers the corpus never wrote it, forcing a
re-roll. Mitigation: A1's explicit "deliberately writes only §5.2/§4.3 files"
statement plus the escalation Tolerance.

## Alternatives checkpoint (Wafflecat)

The round-1 alternative still stands as calibration: drop the bespoke
`corpus_check` oracle and prove the split structurally (coherent specs built by
a constructor that cannot express a violation; each incoherent variant a single
explicit mutation of `COHERENT_BASELINE` whose diff *is* the proof). It trades
away the executable "exactly one invariant violated" assertion and the 2.1.2
cross-check hook (which the round-2 plan has now properly wired via
`CORPUS_INVARIANT_NAMES`), for elimination of oracle/validator-drift risk. The
round-2 plan's choice to keep the oracle is now better justified than in round
1 (the stable name vocabulary makes the 2.1.2 cross-check real), so the oracle
is a defensible choice rather than a liability — but it remains a *choice*
carrying the Risk #3 drift the plan must keep scoped to structural checks only.
No new alternative is materially stronger; the design is on solid ground apart
from D1.

## What the plan gets right (for the record)

- B1 fully and correctly resolved against §4.3/§9; the hash/concatenation model
  and the `CORPUS_SEPARATOR` + escalation Tolerance are exactly right.
- B2 resolution removes the raw-mapping fixture and routes all values through
  fixtures; the `phase_names`-vs-`state-layout.md` single-source cross-check
  and the "no `PHASE_STATES` symbol in any test" discipline are sound.
- A1-A5 advisories from round 1 are genuinely folded in: full `state.toml` table
  set with fixed defaults, zero-padded-string `by_chapter` keys, the two-key
  `[pending_turn]` marker, single-source `GATE_THRESHOLDS`, and the stable
  `CORPUS_INVARIANT_NAMES` vocabulary wiring the 2.1.2 cross-check.
- Determinism (fixed `created_at` literal, fixed draft bodies, no
  timestamps/random ids/absolute paths) satisfies the AGENTS.md snapshot rules.
- Work items remain five, atomic, independently committable, each gated by
  `make all`; the red/green sequencing and the `tomlkit` round-trip guard
  (read-back-with-`tomllib` plus idempotent dump) are well specified.
