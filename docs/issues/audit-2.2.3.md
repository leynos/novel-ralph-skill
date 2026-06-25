# Post-merge audit — roadmap task 2.2.3

Audit of the codebase after roadmap task 2.2.3 ("Implement the validated
chapter-manifest mutator (set-chapters)") merged to `main` at commit `0ca2767`.
The slice adds `novel-state set-chapters`, the one sanctioned, validated path
for populating `[chapters]` from the agent's plan (design §5.1; ADR 001;
ADR 008). It is the project's *second* genuinely multi-file mutator: in one turn
it persists the populated manifest plus a `[pending_turn]` intent in a single
atomic write, materialises the `working/manuscript/chapter-NN/` directories, and
appends a `log.md` receipt, leaving `novel-state check` exiting `0`. The slice
also adds the scoped `derive_reconciliation` precedence branch that lets
`reconcile` COMPLETE a torn `set-chapters` turn by creating the missing,
manifest-derived directories (ADR 008; design §5.4).

The slice is sound, idiomatic, and exceptionally well covered: unit
([`test_set_chapters_unit.py`](../../tests/test_set_chapters_unit.py)), property
([`test_set_chapters_properties.py`](../../tests/test_set_chapters_properties.py)),
reconcile-recovery
([`test_set_chapters_reconcile.py`](../../tests/test_set_chapters_reconcile.py)
— partial-dir, all-dirs-missing, orphan, second-violation, and undeclared cases),
registration
([`test_set_chapters_registration.py`](../../tests/test_set_chapters_registration.py)),
behavioural ([`set_chapters.feature`](../../tests/features/set_chapters.feature)),
and installed-binary e2e
([`test_set_chapters_e2e.py`](../../tests/test_set_chapters_e2e.py) — exit 0, exit
2 for malformed JSON and missing fields, exit 3 for an incoherent plan). The
D10 manifest-before-directories ordering is pinned by a mkdir-failure injection
test. None of the findings below is a blocking defect; the dominant themes are a
small duplication (the per-mutator `log.md` receipt-append helper) and a couple
of documentation-consistency gaps around the `slug` field.

Trail followed: created a `git-donkey` worktree off `origin/main`, explored with
reads over `commands/_set_chapters.py`, `commands/_chapter_plan_entry.py`,
`commands/_reconcile.py`, `state/reconcile.py`, `state/_disk_paths.py`,
`state/document.py`, `state/schema.py`, `state/validate.py`, and the 2.2.3 test
modules; traced history with `git show 0ca2767` and `git log origin/main`. Source
of truth consulted: `docs/adr-008-chapter-manifest-mutator.md`,
`docs/novel-ralph-harness-design.md` §5.1/§5.2/§5.4, `docs/developers-guide.md`
("State mutators" / "multi-file mutator"), `docs/users-guide.md`,
`skill/novel-ralph/SKILL.md` Phase 7, prior `docs/issues/audit-2.2.2.md` and
`audit-2.3.2.md`, and `AGENTS.md`. Each finding records a category, a
location, a description, a concrete proposed fix, and a severity.

## Finding 1 — Duplicated `log.md` receipt-append helper across the two multi-file mutators

- Category: duplication
- Severity: medium
- Location:
  [`commands/_set_chapters.py`](../../novel_ralph_skill/commands/_set_chapters.py)
  `_append_receipt` (lines 205–215) and
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  `_append_recovery_entry` (lines 78–88).

`_set_chapters._append_receipt` and `_reconcile._append_recovery_entry` are
near-identical: each takes `(working_dir, line)`, computes an RFC 3339 UTC
timestamp (`dt.datetime.now(dt.UTC).isoformat()`), opens `working/log.md` in
append mode (UTF-8), and writes `- {timestamp} {op}: {line}\n`. They differ only
in the hard-coded operation prefix (`set-chapters:` versus `reconcile:`). The
`set-chapters` docstring even states "Mirrors `_reconcile._append_recovery_entry`",
acknowledging the copy. With two callers the duplication is now a settled
pattern, not a one-off; a third multi-file mutator would copy it a third time.
There is no shared `log.md`-append seam in `state/` (confirmed: no `log.md`
helper in `state/document.py`, `state/__init__.py`, or
`commands/_state_mutators.py`), so each mutator rolls its own.

**Proposed fix:** extract one timestamped-receipt helper — e.g.
`append_log_receipt(working_dir: Path, *, operation: str, line: str) -> None` in
`state/document.py` (beside `write_document_atomically`, where the other
write-side seams live) or a small `state/_log.py` leaf — and have both mutators
call it with their operation tag. This keeps the timestamp format and the
"append before the clear" contract in one place, removes the mirrored docstring,
and gives the next multi-file mutator a ready seam.

## Finding 2 — Hand-rolled `[pending_turn]` bracket repeated; no shared "receipt-before-clear" seam

- Category: duplication
- Severity: low
- Location:
  [`commands/_reconcile.py`](../../novel_ralph_skill/commands/_reconcile.py)
  `_run_reconcile_bracket` (lines 91–120) and
  [`commands/_set_chapters.py`](../../novel_ralph_skill/commands/_set_chapters.py)
  `_write_manifest_turn` (lines 324–355); the unused-for-this-purpose
  `pending_turn` context manager in
  [`state/document.py`](../../novel_ralph_skill/state/document.py) lines 222–267.

Both multi-file mutators bypass the `pending_turn` context manager and hand-roll
the same skeleton — `open_pending_turn` + `write_document_atomically` →
(state/artefact edits) → append `log.md` receipt → `clear_pending_turn` +
`write_document_atomically` — because the context manager clears on `__exit__`
with no hook to land the receipt *before* the clear (documented at
`developers-guide.md` lines 344–367). The two implementations diverge only in
where the payload edit sits (reconcile edits inside the bracket via an `edit`
callable; `set-chapters` edits the manifest *before* the bracket so it persists
with the intent in the first write, then creates directories inside). The shared
"intent-write → … → receipt → clear-write" envelope is nonetheless duplicated,
and `_run_reconcile_bracket` already generalises most of it (an `edit` callable
plus a `log_line`).

**Proposed fix:** this is lower priority than Finding 1 because the two orderings
are genuinely different and the divergence is deliberate. The cleanest unlock is
to land Finding 1 first (a shared receipt helper), then consider promoting a
single `run_receipted_turn(path, working_dir, *, operation, paths, edit,
log_line)` seam into `state/document.py` that both mutators call — `set-chapters`
passing an `edit` that creates the directories and a pre-bracket manifest write,
`reconcile` passing its recount/clear edit. If promotion proves awkward because
of the pre-bracket manifest write, leave the brackets as-is but record the
shared envelope as an explicit convention in the developers' guide so the next
mutator copies a documented pattern rather than reverse-engineering two.

## Finding 3 — `ChapterPlanEntry.slug` documented "filesystem-safe" but nothing validates it

- Category: docs-gap
- Severity: low
- Location:
  [`commands/_chapter_plan_entry.py`](../../novel_ralph_skill/commands/_chapter_plan_entry.py)
  lines 36–37 (the `slug` attribute doc) and
  [`commands/_set_chapters.py`](../../novel_ralph_skill/commands/_set_chapters.py)
  `manifest_coherence_violations` (lines 85–140);
  [`state/schema.py`](../../novel_ralph_skill/state/schema.py)
  `ChapterEntry.slug` line 82.

`ChapterPlanEntry.slug` and `ChapterEntry.slug` are both documented as "the
filesystem-safe chapter identifier", but no code enforces filesystem-safety:
`manifest_coherence_violations` checks slug *uniqueness* only, and the §5.2
`validate_state` set treats slugs as opaque strings (matching `init`, whose
`[novel].slug` is "stored verbatim … slug validation is not a §5.2 invariant",
per `state/initial.py` lines 60–61). An empty slug, or one containing `/`, `..`,
or whitespace, passes coherence and is written to the manifest. This is *not*
currently exploitable — the `chapter-NN/` directory name is derived from the
chapter *number*, not the slug (`state/_disk_paths.py::_chapter_dir_name`), so
the slug never reaches a path today — but the "filesystem-safe" wording is an
unenforced promise, and the project decision (slugs are opaque) is recorded only
for `[novel].slug`, not for chapter slugs.

**Proposed fix:** pick one and apply it consistently. Either (a) soften the
docstrings on both `ChapterPlanEntry.slug` and `ChapterEntry.slug` to "the
chapter identifier (stored verbatim; slug shape is the agent's responsibility, as
for `[novel].slug`)" and add a one-line note to ADR 008 / the developers' guide
that chapter slugs are opaque, mirroring `state/initial.py`; or (b) if a slug
will later seed a path, add a `slugs-non-empty` (and optionally a
`slugs-filesystem-safe`) rule to `MANIFEST_COHERENCE_RULE_NAMES` and
`manifest_coherence_violations`, with matching unit/property cases. Option (a) is
the consistent, lower-risk choice given the established opaque-slug stance.

## Finding 4 — SKILL Phase 7 outline fields omit `slug`, but `set-chapters` requires it

- Category: docs-gap
- Severity: low
- Location:
  [`skill/novel-ralph/SKILL.md`](../../skill/novel-ralph/SKILL.md) Phase 7 lines
  305–321 (the per-chapter outline record) versus lines 329–336 (the
  `set-chapters` JSON, which requires `slug`).

The Phase 7 outline-record checklist lists chapter number, title, POV, setting,
premise, characters, conflict, outcome, STC beat, and target word count — but
**not** a slug. The `set-chapters` invocation a few lines later requires a
`slug` per chapter ("filesystem-safe, unique"). An agent that fills the outline
exactly as the checklist prescribes has no slug to carry into the JSON and must
invent one ad hoc, which weakens the "outline drives the manifest" guarantee and
risks inconsistent slugs across re-runs.

**Proposed fix:** add a "**Slug.** A filesystem-safe, unique identifier (e.g.
`the-summons`)" bullet to the Phase 7 per-chapter record list so the slug is a
planned outline field, not a value conjured at `set-chapters` time. Optionally
note that `chapter-NN` is an acceptable default slug when no descriptive slug is
wanted (matching the corpus builder's convention).

## Finding 5 — A duplicate chapter number yields a two-rule verdict (`numbers-unique` + `numbers-contiguous-from-1`)

- Category: ergonomics
- Severity: low
- Location:
  [`commands/_set_chapters.py`](../../novel_ralph_skill/commands/_set_chapters.py)
  `manifest_coherence_violations` lines 132–135; pinned by
  [`test_set_chapters_unit.py`](../../tests/test_set_chapters_unit.py) lines
  142–146 (the `duplicate-number` case expects
  `(numbers-unique, numbers-contiguous-from-1)`).

A plan with a repeated chapter number — e.g. `[1, 1]` — breaks both
`numbers-unique` *and* `numbers-contiguous-from-1` (the duplicate shortens the
distinct-number set so `sorted(numbers) != range(1, n+1)`), so the refusal names
two rules for one underlying mistake. The SKILL and users' guide describe these
as distinct faults ("a gap, a duplicate number or slug"), so an agent reading
"numbers-contiguous-from-1" alongside "numbers-unique" for a pure duplicate may
hunt for a non-existent gap. The verdict is deterministic and the tests lock the
current behaviour, so this is cosmetic, not a defect.

**Proposed fix:** optionally short-circuit the contiguity rule when
`numbers-unique` has already fired (contiguity is only meaningful over a
duplicate-free set), so a duplicate names exactly `numbers-unique` and a genuine
gap names exactly `numbers-contiguous-from-1`. This would tighten the diagnostic
and the corresponding unit case. If the deliberately-stable multi-rule verdict is
preferred, instead add one sentence to the `manifest_coherence_violations`
docstring noting that a duplicate number also trips contiguity by construction,
so the doubled verdict is expected.

## Finding 6 — `set-chapters` does not guard a pre-existing (foreign) `[pending_turn]`

- Category: separation-of-concerns
- Severity: low
- Location:
  [`commands/_set_chapters.py`](../../novel_ralph_skill/commands/_set_chapters.py)
  `set_chapters` lines 278–307 and `_write_manifest_turn` lines 324–355;
  [`state/document.py`](../../novel_ralph_skill/state/document.py)
  `open_pending_turn` lines 179–204 (unconditional
  `document[_PENDING_TURN_KEY] = record`).

`set_chapters` loads the document, refuses a populated prior manifest, validates
the plan, then calls `open_pending_turn`, which *unconditionally overwrites* any
existing `[pending_turn]`. If a prior crashed turn left a populated
`[pending_turn]` of a different operation, `set-chapters` would silently clobber
that torn-turn record. In practice the harness workflow runs `reconcile` first
(and `check` exits non-zero on an uncleared `pending-turn-cleared`), and this
permissive stance is *project-wide* — `reconcile` itself overwrites the torn
record after deriving from it, and the single-file mutators open no bracket — so
this is a pre-existing design posture, not a regression introduced by 2.2.3. It
is recorded here only because `set-chapters` is the second multi-file writer to
inherit it.

**Proposed fix:** no code change is required for 2.2.3 in isolation. If the
overwrite-a-foreign-pending-turn window is judged worth closing, do it once at
the seam: have `open_pending_turn` (or a thin `assert_no_pending_turn`
precondition shared by the multi-file mutators) raise a `StateInputError` (exit
3, "run `reconcile` first") when a `[pending_turn]` whose operation differs from
the one being opened is already present. Treat that as a small cross-cutting
roadmap item rather than a 2.2.3 fix, since it touches every bracketed mutator.

## Pre-existing items not re-litigated

The hand-rolled multi-file bracket and its receipt-before-clear ordering were
introduced and documented by roadmap task 2.3.2 (`reconcile`); Findings 1 and 2
above concern the *second* occurrence that 2.2.3 added, and propose consolidating
the now-duplicated helpers rather than re-opening the 2.3.2 design. The
opaque-slug stance for `[novel].slug` predates this slice (`state/initial.py`);
Finding 3 only asks that chapter slugs be made consistent with it. No prior audit
captured a chapter-manifest-mutator item, so none is superseded here.
