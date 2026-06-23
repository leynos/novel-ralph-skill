# Logisphere design review — roadmap 2.1.3 ExecPlan, round 2

Verdict: REVISE. The round-2 rewrite resolves four of round 1's five blocking
points convincingly: the live-draft oracle reading `draft.md` token counts is
genuinely independent of the `[word_counts]` table (B1); the invariant-7
numerator is pinned to the honest-draft basis with a self-test (B2); the stale
"move invariant 3 onto disk" framing is corrected (B4); and the red-commit
branch is dropped for a single green commit (B5). The cuprum exclusion remains
correct. Two blocking defects remain, both load-bearing on the design's own
definition of task 2.1.3.

## Blocking defects

### B1-r2 (Pandalump / Dinolump) — the plan reconciles only one of the two named proxies

The developers' guide (lines 323-334) names **two** pure-state proxies whose
reconciliation "against a live draft count is task 2.1.3's on-disk cross-check":

1. `gate-ratio-consistent`, numerator `sum(word_counts.by_chapter.values())`;
   and
2. `consecutive-clean-within-drafted`, whose ceiling counts
   `word_counts.by_chapter` entries with a positive drafted total as the
   pure-state proxy for the design's "chapters drafted" disk quantity (guide
   lines 329-332; mirrored in
   `validate.py::_check_consecutive_clean_within_drafted`, which counts
   `by_chapter` values `> 0`).

The plan's own Purpose (lines 31-40) recites **both** proxies verbatim and
commits to discharging the guide's promise. But the live oracle (Work item 1,
step 5, lines 541-551) reconciles only `gate-ratio-consistent` against the live
draft count; for the other six owned invariants — explicitly including
`consecutive-clean-within-drafted` (Decision Log, lines 321-333) — it reuses
the spec-keyed `corpus_check` verbatim, which counts `spec.chapters` with
`draft_words > 0`, never reading disk. So the drafted-**chapters** proxy is
never reconciled against any live disk source.

This is exactly the B3 overclaim hazard round 1 named. Work item 3 (lines
681-684) will then edit the guide to state the cross-check "reconciles the two
proxy invariants (`gate-ratio-consistent` and the
`consecutive-clean-within-drafted` ceiling's drafted-chapter basis) against it"
— a claim the delivered mechanism does not support. The drafted-chapters live
source is cheap and natural: it is the count of `chapter-NN/draft.md` files
whose token count is positive (the live oracle already reads each `draft.md` to
total tokens). Either:

- extend the live oracle to recompute the drafted-chapters count from the
  present
  `draft.md` bodies and reconcile `consecutive-clean-within-drafted` against
  *that* (matching the guide's "reconcile the proxy against a live draft count"
  for both proxies); or
- narrow the plan and the Work item 3 guide edit to claim only what is delivered
  (the `gate-ratio-consistent` reconciliation plus the table-coherence
  `by-chapter-sum` check), and justify against the guide why the
  drafted-chapters proxy is left on its table basis.

As written the plan repeats round 1's overclaim with a different proxy.

### B2-r2 (Telefono) — the prescribed `live_draft_owned` signature cannot do what step 5 requires

The Interfaces section (lines 797-819) pins the end-state contract as
`live_draft_owned(working_dir: Path) -> set[str]` (no `spec`), and the
`check_live_draft` fixture (lines 824-827) is typed
`Callable[[Path], set[str]]`. But Work item 1 step 5 (lines 541-551) requires
the oracle to obtain the six reused owned names by "running `corpus_check`
against the same tree" — and `corpus_check(spec, working_dir)` takes a `spec`
the `working_dir`-only signature does not have. `corpus_check` reads `spec`
fields (`phase_current`, `phase_completed`, `consecutive_clean`,
`convergence_target`, cursor) that the `working_dir`-only oracle would have to
reconstruct from `state.toml` itself; the plan describes no such reconstruction.

The plan leaves this as an implementer coin-flip ("If the implementer prefers a
`(spec, working_dir)` signature … that is acceptable; record the choice", lines
549-551), but the two choices yield materially different fixtures, a different
whole-corpus agreement test wiring (Work item 2 passes the fixture, not a
spec), and a different Interfaces contract. A design review cannot bless an
interface that the mechanism beneath it cannot satisfy. Resolve the signature
**in the plan**: pick `(spec, working_dir)` (then the fixture and Work item 2
must thread the spec, and the prescribed Interfaces block is wrong as written),
or keep `working_dir`-only and specify how the six reused names are recovered
from disk without `corpus_check`. Note that a `(spec, working_dir)` oracle is
no longer "genuinely independent of the spec" for six of eight invariants —
which is fine, since the independence is concentrated in the two proxy
invariants, but the plan must say so plainly rather than implying full
disk-independence.

## Advisory

- A1 (Wafflecat alternatives): the strongest alternative remains the one the
  plan
  adopted (live-draft oracle); no better structural option exists. A leaner
  variant worth weighing: since the existing
  `test_incoherent_agreement_restricted_to_owned` already discharges the
  literal roadmap Success clause (validator vs spec-oracle over the materialised
  `state.toml`, restricted to owned), the *only* genuinely new value this task
  adds is the live-draft basis for the two proxy invariants. Framing the task
  as "add the live-draft reconciliation for the two proxies, plus the
  coherent-tree pin" (Telefono A3 from round 1) would shrink it and make B1-r2
  unavoidable to confront. The three-work-item shape is acceptable but slightly
  inflates a one-mechanism change.
- A2 (Buzzy Bee): scaling is a non-issue — fixed finite corpus under `tmp_path`,
  xdist-safe (each test builds its own trees). The plan's reasoning is sound.
- A3 (Doggylump): the parse-enforced `phase-in-enum` handling, the
  `PURE_STATE_INVARIANT_NAMES` restriction, the disk-evidence-name exclusion,
  the 400-line-cap sibling-module contingency, and the honest-draft self-test
  are all correct and well-reasoned. Keep them.
- A4 (Telefono): the live oracle's `by-chapter-sum` clause (step 3) is byte-for-
  byte the same table read as the validator's `_check_by_chapter_sum` —
  correctly, because invariant 3 is table-internal coherence with no "live"
  analogue. The plan acknowledges this (lines 533-536). No concern, but the
  Work item 3 guide edit must not imply invariant 3 is "live-reconciled".
- A5 (verification): `make all`/`make markdownlint`/`make nixie` are the right
  gates; locked libraries (pytest-xdist, tomllib, uv) are used only in their
  established, already-pinned roles, so no new memory-based library claim needs
  firecrawl verification. The cuprum exclusion is verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` and `program.py`
  (`ProgramCatalogue` is a process allowlist; this task spawns no subprocess).

## Pre-mortem (Doggylump)

Six months on, a corpus maintainer adds a variant that sets
`by_chapter_override` so the `[word_counts].by_chapter` table omits a chapter
that *does* have a positive `draft.md` on disk (a legal "table mislabels the
drafts" state — exactly what 2.1.3 exists to catch). The
`gate-ratio-consistent` cross-check fires correctly (live total diverges from
the table). But because `consecutive-clean-within-drafted` was left on the
table basis (B1-r2), the drafted-**chapters** mislabel slips through silently:
the proxy counts the table's non-zero entries, the live drafts say otherwise,
and nothing compares them. The team trusts the guide's "reconciles the two
proxy invariants" sentence and never looks. Prevention: reconcile *both*
proxies against the live draft count now (B1-r2), so there is one honest disk
source for both the drafted-words and the drafted-chapters quantities.

## Docs and skills relied on

- Source verified directly against the worktree:
  `novel_ralph_skill/state/validate.py` (invariant-7 numerator
  `sum(by_chapter.values())`, line 241; drafted-chapters proxy lines 187-188),
  `novel_ralph_skill/state/parse.py` (`_word_counts`),
  `tests/working_corpus/_oracle.py` (`_check_by_chapter_sum` line 117-119,
  `_check_gate_ratio_consistent` line 199,
  `_check_consecutive_clean_within_drafted` line 148), `_specs.py`
  (`draft_body` lines 205-214, `derive_current`/ `derive_by_chapter`),
  `_variants.py` (`by-chapter-sum-mismatch` uses `current_words_override`, not
  `by_chapter_override`, line 114; `gate-true-below-threshold` lines 70-86),
  `_library.py` (`_DRAFTED_WORDS` `(24000, 24000, 20800)`, target 80000, line
  41-42), `_builder.py::_write_chapter` (lines 157-178),
  `tests/corpus_fixtures.py` (fixture surface),
  `tests/test_validate_state_corpus.py` (236 lines; helpers reused by the plan).
- `docs/developers-guide.md` "Invariant validation" (lines 286-360, especially
  the two-proxy / live-draft-count definition at 323-334 and the
  deliberate-twin policy at 336-344).
- `docs/novel-ralph-harness-design.md` §5.2 (invariants, lines 430-456 — note
  the
  design's canonical invariant-7 numerator is `current`, deliberately
  approximated by the implementation's `sum(by_chapter)`), §9 (verification
  strategy, lines 671-711).
- `docs/roadmap.md` 2.1.3 entry and reroute (lines 375-393).
- `docs/execplans/roadmap-1-3-2.md` advisory A5 (lines 940-950); note the 1.3.2
  plan originally specified `by-chapter-sum-mismatch` "via
  `by_chapter_override`" (line 969) but the implemented variant uses
  `current_words_override` — the plan's claim that no variant sets
  `by_chapter_override` is correct against the real source.
- `AGENTS.md` (400-line cap lines 24-27; quality-gate / commit discipline lines
  98-108).
- cuprum read-only sibling `/data/leynos/Projects/cuprum/cuprum/catalogue.py`,
  `program.py`.
- Skills: logisphere-design-review (this framework). Codebase navigation done by
  direct read of the worktree source named above.
