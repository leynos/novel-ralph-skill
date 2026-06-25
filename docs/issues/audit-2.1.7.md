# Post-merge audit — roadmap task 2.1.7

Audit of the codebase after roadmap task 2.1.7 ("Relax the manifest-disk
bijection during drafting") merged to `main` at commit `cb20d3f`. The slice
loosens design §5.2 invariant 5 so that, during drafting, the on-disk chapter set
may honestly be a subset of the `[chapters]` manifest without the user-facing
`check` refusing the turn. It adds a keyword-only, default-strict
`relax_drafting_bijection` flag to
[`check_disk_evidence`](../../novel_ralph_skill/state/disk_evidence.py); splits
the bijection break into its two directions (`orphans = on_disk - manifest`,
`missing = manifest - on_disk`) plus a contiguity-from-1 check; lifts the
bijection predicate out of the uniform-signature `_TAIL_PREDICATES` loop so it can
the flag; mirrors the relaxation in the corpus oracle twin
([`tests/working_corpus/_oracle_disk.py`](../../tests/working_corpus/_oracle_disk.py));
threads `relax_drafting_bijection=True` only through the user-facing `check`
([`novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)) while
`derive_reconciliation`
([`reconcile.py`](../../novel_ralph_skill/state/reconcile.py)) keeps the strict
default; records [ADR 009](../../docs/adr-009-drafting-bijection-relaxation.md);
and adds unit, corpus, and end-to-end coverage.

The slice is sound and discharges its Success clause. The relaxation is correctly
phase-gated (`Phase.DRAFTING` only) and direction-scoped (orphans and gaps still
fire in every phase, re-tightening at `final-pass`/`done`), the strict default is
preserved on the `reconcile` precedence path so the torn `set-chapters` COMPLETE
arm (ADR 008) is unaffected, and the head-then-tail assembly preserves the
historical verdict order byte-for-byte. The flag is documented thoroughly across
the module docstring, the function docstring, the call-site docstrings, ADR 009,
the developers' guide, and the users' guide, and the docs were refreshed in step
with the code. Test coverage exercises strict default, relaxed-silent subset,
orphan-still-fires, non-contiguous-still-fires, the terminal-phase re-tighten, the
full phase matrix, and union-order preservation.

None of the findings below is a blocking defect. The dominant theme is *structural
duplication of the bijection set-classification* — the `orphans`/`missing`/
`contiguous`/`coherent_subset` computation now lives inline in three sites (the
production predicate, the corpus oracle twin, and the `reconcile` precedence
predicate), and the contiguity-from-1 idiom is the same literal in all three. A
secondary theme is a *diagnostic gap*: the bijection `Violation.detail` does not
name which direction broke, even though the predicate has just classified it. The
pre-existing `_coerce`/`detect` near-copy duplication between `ledger/` and
`rulepack/` is documented and deliberate (an exception-type-routing plus
frozen-loader Tolerance constraint) and is noted but not re-litigated as a 2.1.7
regression.

Trail followed: explored with `leta` (`files`, `grep`, `show` over
`state/disk_evidence.py`, `state/reconcile.py`, `state/phase.py`,
`commands/novel_state.py`, `tests/working_corpus/_oracle_disk.py`, and the
`ledger`/`rulepack` parallel modules) and targeted `grep` for the duplicated
set-classification idiom; traced history with `git show cb20d3f` and
`git log origin/main`. Source of truth consulted:
[ADR 009](../../docs/adr-009-drafting-bijection-relaxation.md),
[ADR 008](../../docs/adr-008-chapter-manifest-mutator.md),
[`developers-guide.md`](../../docs/developers-guide.md) (§5.2 invariant table and
the "drafting bijection relaxation" section), [`users-guide.md`](../../docs/users-guide.md),
[`roadmap.md`](../../docs/roadmap.md) §2.1.7, and [`AGENTS.md`](../../AGENTS.md)
(the 400-line module cap and CQS conventions). Skills relied on: `python-router`
(reviewing the predicate and reconcile code), `leta` (navigation), and `sem`/
`git show` (history).

Each finding records a category, location, description, proposed fix, and severity.

## 1. The bijection set-classification is duplicated inline across three sites

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py)
  `_check_manifest_disk_bijection` (lines 149-159);
  [`novel_ralph_skill/state/reconcile.py`](../../novel_ralph_skill/state/reconcile.py)
  `_set_chapters_turn_explains_bijection` (lines 224-236);
  [`tests/working_corpus/_oracle_disk.py`](../../tests/working_corpus/_oracle_disk.py)
  `_check_manifest_disk_bijection` (lines 93-100).

The set-theoretic classification of a manifest-vs-disk break is now computed inline
in three places. The production predicate builds `orphans = on_disk - manifest`,
`missing = manifest - on_disk`, `contiguous = sorted(manifest) == list(range(1,
len(manifest) + 1))`, and `coherent_subset = not orphans and contiguous`. The
`reconcile` precedence predicate independently recomputes the same `contiguous`
check, the same `on_disk <= manifest` subset test (equivalent to `not orphans`),
and the same `manifest - on_disk` set. The corpus oracle twin recomputes all
four verbatim. The contiguity literal `sorted(manifest) == list(range(1,
len(manifest) + 1))` appears identically at `disk_evidence.py:152`,
`reconcile.py:225`, and `_oracle_disk.py:95`. A change to the bijection's notion
of coherence — for example admitting a non-1-based manifest, or treating a
partial draft differently — must be made in three places in lockstep, and the two
production sites carry no shared
helper to keep them honest.

**Proposed fix:** extract a small pure classifier in `disk_evidence.py`, e.g.
`_classify_bijection(manifest: frozenset[int], on_disk: frozenset[int]) ->
_BijectionBreak` returning a frozen dataclass with `orphans`, `missing`,
`contiguous`, and a `coherent_subset` property. Have
`_check_manifest_disk_bijection` and `reconcile.py`'s
`_set_chapters_turn_explains_bijection` both consume it, so the two production
sites share one definition. The corpus oracle twin is a *deliberate*
independent reimplementation (the agreement suite's whole purpose is to catch a
production drift against an independently-written oracle), so it should stay a twin
rather than import the helper — but a one-line comment in each pointing at the other
as the mirror keeps the pair discoverable. This is a pure refactor with no
behavioural change.

## 2. The bijection violation detail does not name which direction broke

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py)
  `_check_manifest_disk_bijection` (lines 160-167).

Having just classified the break into `orphans`, `missing`, and the contiguity
flag, the predicate discards that classification when it builds the `Violation`:
the detail is the generic `manifest chapters {sorted(manifest)} are not in
bijection with the on-disk chapter directories {sorted(on_disk)}`. After the 2.1.7
relaxation the operator-facing question is sharper than before — "is this an
orphan draft, a manifest gap, or a missing directory the relaxation declined to
suppress (e.g. because I am past drafting)?" — yet the message leaves the
operator to diff the two sorted lists by eye to recover the direction the code
already knows. This is a diagnostic-quality gap, not a correctness one; the
verdict itself is right.

**Proposed fix:** enrich the detail to state the broken direction(s) the predicate
computed, e.g. append `; orphan directories {sorted(orphans)}` when `orphans`, `;
manifest entries without directories {sorted(missing)}` when `missing` and the
relaxation did not suppress it, and `; manifest is not contiguous from 1` when not
`contiguous`. If finding 1 is taken, the `_BijectionBreak` dataclass can carry a
`describe()` method so the production predicate and any future caller render the
same prose. Keep the existing summary line as the lead so snapshot churn is bounded
to an appended clause.

## 3. The relaxation flag's phase gate is re-read indirectly via `state.phase.current`

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py)
  `_check_manifest_disk_bijection` (line 158:
  `drafting = relax_drafting and state.phase.current == Phase.DRAFTING`).

The "is this the drafting phase?" decision lives inline in the bijection predicate.
This is a single, well-commented line today, but the predicate now owns two
concerns — the set-classification (finding 1) and the phase-gate policy. If a later
slice needs the same "relax only during drafting" gate elsewhere (for example a
sibling predicate, or the §2.3.x reconcile parity work the ADR foreshadows), the
`current == Phase.DRAFTING` test will be restated. The corpus twin already restates
it as `state["phase"]["current"] == "drafting"` against the raw string, so the gate
predicate exists in two spellings (typed enum vs raw TOML string).

**Proposed fix:** none strictly required at this size — the gate is one line and
is clearly documented against ADR 009. Recorded so that if the drafting-gated
relaxation pattern recurs, a named `_relaxation_applies(state) -> bool` (or a
`Phase.allows_drafting_skew` helper on the enum) is introduced at that point rather
than copying the comparison a third time. No change is warranted for 2.1.7 alone.

## 4. Pre-existing `ledger`/`rulepack` `_coerce` and `detect` near-copies (not a 2.1.7 regression)

- **Category:** similarity
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/ledger/_coerce.py`](../../novel_ralph_skill/ledger/_coerce.py)
  vs [`novel_ralph_skill/rulepack/_coerce.py`](../../novel_ralph_skill/rulepack/_coerce.py)
  (`_where`, `_reject_unknown_keys`, `_require`, `_require_str`, `_require_int`);
  [`novel_ralph_skill/ledger/detect.py`](../../novel_ralph_skill/ledger/detect.py)
  vs [`novel_ralph_skill/rulepack/detect.py`](../../novel_ralph_skill/rulepack/detect.py)
  (`_finding`, `detect`).

The two `_coerce` modules are a near-line-for-line copy that differs only in the
raised error type (`LedgerError` vs `RulePackError`) and the entity-naming prose
("device" vs "rule"). The two `detect` modules share the `_finding`/`detect` shape
(though `ledger/detect.py` already reuses `ScannedChapter` and `LineHit` from
`rulepack/detect.py`, so the scanning core is partly shared). The `_coerce`
duplication is *deliberate and documented*: the module docstring records that
importing the rule-pack helpers would emit the wrong typed error (the command
routes on exception type) and that refactoring the rule-pack helpers to take an
error factory would edit the frozen rule-pack loader — an ExecPlan Tolerance trip
that requires the rule-pack path stay byte-for-byte unchanged (WI1 Decision Log;
round-1 review condition 1).

**Proposed fix:** none for 2.1.7 — this predates the slice and the documented
constraint stands. Recorded only so the structural duplication is visible to a
future consolidation pass: should the frozen-loader Tolerance ever lift, the cleanest
seam is a generic `_coerce` parametrised by an error factory
(`Callable[[str, str | None], Exception]`) and a `where`-prefix builder, with the
two packages supplying their own factory and noun. Until then the near-copy is the
correct trade-off and should not be "fixed" by importing across the boundary.

## Pre-existing items not re-litigated

The `ledger`/`rulepack` `_coerce`/`detect` duplication (finding 4) predates 2.1.7
and is constrained by the documented frozen-loader Tolerance; it is recorded for
visibility only, not as a regression. No new roadmap item is proposed for it absent
a decision to relax that constraint.
