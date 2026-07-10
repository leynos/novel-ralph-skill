# Logisphere design review — roadmap 2.1.3 ExecPlan, round 1

Verdict: REVISE. The plan is well-written and accurate about the *test
scaffolding* (fixtures, helpers, parse-enforced phase, restriction to owned
names), and its cuprum exclusion is correct. But its central mechanism — the
"independent disk-derived oracle" for invariants 3 and 7 — does not deliver an
independent cross-check, contradicts the locked invariant-7 semantics, and
misreads what the design documents define task 2.1.3 to be. Five blocking
defects below.

## Blocking defects

### B1 (Pandalump / Telefono) — the "independent disk re-derivation" is not independent

Decision Log D1 promises an *independent* re-derivation that reads
`[word_counts].by_chapter` / `.current` / `.target` from the materialized
`state.toml` via `tomllib` and computes invariant 3 as
`sum(by_chapter.values()) == current` and invariant 7 as
`sum(by_chapter.values()) / target` against the thresholds (Work item 2, lines
466-473).

But `novel_ralph_skill/state/parse.py::_word_counts` (lines 168-171) reads
those *same three keys straight through* into `WordCounts`, and the validator's
`_check_by_chapter_sum` / `_check_gate_ratio_consistent` apply *those same two
formulas*. The plan's "oracle" therefore consumes the identical input bytes and
runs arithmetically identical logic to the validator. The new
`test_disk_derived_agreement_over_whole_corpus` would compare the validator
against a restatement of itself — catching nothing. This is exactly the failure
mode D1 says it avoids ("re-invoking the production validator as the oracle
would compare the validator against itself and catch nothing"); reading the same
`[word_counts]` table by hand instead of via `load_state` does not make it
independent.

### B2 (Telefono / Doggylump) — the invariant-7 disk numerator contradicts the locked oracle

The corpus oracle's `_check_gate_ratio_consistent` computes its ratio from
`sum(chapter.draft_words for chapter in spec.chapters)` — the honest draft
total — *deliberately* so a `by_chapter_override` cannot perturb invariant 7
(1.3.2 execplan Outcomes, lines 685-686; developers-guide lines 324-326;
`_specs.py` `by_chapter_override` doc). The plan re-derives the invariant-7
numerator as `sum(by_chapter.values())` from the `[word_counts]` table (Work
item 2, lines 470-473). These two readings diverge for any spec with
`by_chapter_override` set.

The plan never reconciles this. Its Work item 3 self-test asserts the
disk-derived oracle and the spec-keyed `corpus_check` "must coincide" on
coherent trees — but by construction they use different invariant-7 numerators,
so the self-test only passes because no *current* corpus variant combines an
override with gate flags. The plan bakes in a latent contradiction that the
next corpus addition (an override-plus-gate variant) would expose, and it does
so by silently re-coupling invariant 7 to a quantity the design explicitly
decoupled it from.

### B3 (Pandalump / Dinolump) — the plan ignores the design's own definition of 2.1.3's cross-check

The developers-guide (lines 329-334) defines task 2.1.3 precisely: the
`consecutive-clean-within-drafted` ceiling and the gate ratio are *pure-state
proxies* for "chapters drafted" / drafted words, and "reconciling the proxy
against a **live draft count** is task 2.1.3's on-disk cross-check." A live
draft count means the actual words in the on-disk `draft.md` files — a
genuinely independent source from the `[word_counts]` table the validator
trusts. That is the cross-check that would catch a
`[word_counts]`-table-versus-real-drafts mislabel.

The plan reads only the `[word_counts]` table and never touches the drafts, so
it does not deliver the cross-check the guide describes — yet Work item 3 edits
that very guide sentence to claim the promise is fulfilled. Either the plan
must perform the live-draft reconciliation the guide defines (recompute drafted
words from `draft.md` bodies, e.g. via the corpus `draft_body` token count, and
check the `[word_counts]` table against it), or it must justify, against the
design, why a weaker `[word_counts]`-only re-read discharges the promise — and
then the guide edit must say what was actually delivered, not overclaim.

### B4 (Wafflecat / structural) — invariant 3 is already disk-derived; the premise is stale

The 1.3.2 fix-round-1 decision (1.3.2 execplan lines 630-654) already moved
`_check_by_chapter_sum` to read the materialized `state.toml` ("The oracle's
`_check_by_chapter_sum` now reads the materialized `state.toml` and compares
the written `sum(by_chapter)` against the written `current`"). The oracle's
invariant 3 is therefore *already* the disk reading the validator sees. Only
invariant 7 remains spec-keyed.

The plan's Purpose, Risks, Decision Log, and Work item 2 repeatedly frame
invariant 3 as a quantity this task must move onto disk ("recompute invariant 3
… reading `[word_counts].by_chapter` and `[word_counts].current` from disk").
That is already done. The genuine residual gap is invariant 7 alone. The plan
inflates scope, re-implements an existing disk read as if new, and obscures the
one real change — which compounds B1/B2 because the "new" invariant-3 reading
it adds is a third byte-identical copy of a check that already reads disk.

### B5 (Doggylump / process) — committing a deliberately red test violates AGENTS.md gating

Work item 1 (lines 416-421) proposes committing the failing test, gated with a
narrowed `uv run pytest` over unaffected modules. AGENTS.md lines 100 and 108
are unambiguous: "Only changes that meet all quality gates should be committed"
and "Do not commit changes that fail any quality gate." The plan leaves the
fold of items 1+2 as a conditional ("If repository policy forbids committing a
red test…"). It does not; resolve this now: mandate a single green commit
(red test plus its satisfying mechanism together), and drop the red-commit
branch.

## Advisory

- A1 (Buzzy Bee): scaling is a non-issue — the corpus is a fixed finite set
  built
  under `tmp_path`; xdist-safety reasoning is sound. No concern.
- A2 (Wafflecat alternative): the strongest viable design is the one the guide
  already names — a *live-draft* oracle. Recompute the drafted-word total from
  the `draft.md` bodies on disk (the corpus writes deterministic
  `draft_body(n)` tokens, so the count is recoverable), and cross-check the
  `[word_counts]` table and the gate booleans against *that*. This is genuinely
  independent of both the validator and the spec, catches a builder-vs-table or
  table-vs-draft mislabel, and discharges the guide's "reconcile the proxy
  against a live draft count" promise. It trades a few more lines of disk
  reading for an actually load-bearing cross-check. The plan should adopt this
  or argue it down against §9 and the guide.
- A3 (Telefono): if, after B1-B4, the only honest residual gap is "move the
  *oracle's* invariant-7 numerator onto the same honest-draft basis the
  live-draft oracle uses, and assert the corpus-wide agreement," say so
  plainly. The task may be smaller and sharper than three work items: a single
  additive disk/live-draft oracle entry point plus the whole-corpus agreement
  assertion and its coherent- tree pin.
- A4 (Dinolump): the parse-enforced `phase-in-enum` handling, the restriction to
  `PURE_STATE_INVARIANT_NAMES`, the disk-evidence-name exclusion, and the
  400-line-cap sibling-module contingency are all correct and well-reasoned;
  keep them.

## Pre-mortem (Doggylump)

Six months on, the corpus gains a variant that sets `by_chapter_override`
alongside a gate flag (a perfectly legal state the design permits — `current`
is "an independently written value", state-layout line 114). The plan's disk
oracle (inv 7 numerator = `sum(by_chapter.values())`) and the spec oracle
(numerator = `sum(draft_words)`) now disagree; the Work item 3 "must coincide"
self-test fires, and a maintainer, trusting the plan's framing, "fixes" it by
aligning the oracles — silently re-coupling invariant 7 to `by_chapter`,
undoing the B1-decoupling the design intends. Signal missed: nobody
distinguished "the validator's `by_chapter` basis" from "the honest-draft
basis," because the plan treated them as one. The prevention is to read the
live draft count (A2) so there is exactly one independent honest source, named
as such.

## Docs and skills relied on

- `docs/roadmap.md` (2.1.3 entry + review:1.3.2 high-severity reroute, lines
  375-393).
- `docs/novel-ralph-harness-design.md` §5.2 (invariants, lines 430-458), §9
  (verification strategy, lines 671-711).
- `docs/developers-guide.md` "Invariant validation" (lines 291-360, especially
  the proxy / live-draft-count definition at 329-334 and the deliberate-twin
  policy at 336-344).
- `docs/execplans/roadmap-1-3-2.md` (advisory A5; fix-round-1 on-disk decision,
  lines 630-654; Outcomes invariant-7 honest-draft note, lines 685-686).
- `AGENTS.md` (400-line cap line 24; quality-gate / commit discipline lines
  100-108).
- Source verified directly: `novel_ralph_skill/state/validate.py`,
  `novel_ralph_skill/state/parse.py` (`_word_counts`, lines 161-171),
  `tests/working_corpus/_oracle.py`, `_specs.py`, `_variants.py`,
  `tests/corpus_fixtures.py`, `tests/test_validate_state_corpus.py`.
- cuprum read-only sibling: `/data/leynos/Projects/cuprum/cuprum/catalogue.py`
  (`ProgramCatalogue` is a process allowlist) — confirms the plan's
  cuprum-irrelevant Decision is correct.
