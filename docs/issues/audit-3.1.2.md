# Post-merge audit — roadmap task 3.1.2

Audit of the codebase after roadmap task 3.1.2 ("Implement the shared
compile-and-hash routine and the compile-divergence clause") merged to `main` at
commit `4c578e3`. The slice swaps the `compile_consistent` done clause from an
existence-only check to a content comparison driven by the shared
[`compile_model`](../../novel_ralph_skill/state/compile_model.py)
(`present_draft_bodies` + `concatenate_drafts`), adds a conservative exit-`4`
(`ACTIONABLE_FINDING`) carve-out to
[`_novel_done`](../../novel_ralph_skill/commands/_novel_done.py) for a
stale-*present* compile, and reuses the same routine in
[`novel-compile`](../../novel_ralph_skill/commands/_compile.py) and the §5.4
detector
([`disk_evidence._check_compiled_matches_drafts`](../../novel_ralph_skill/state/disk_evidence.py))
so the write path, the detector, and the done clause cannot disagree.

The slice is correct and well-tested: the carve-out's three branches
(stale-present → exit `4`, mid-draft-stale → exit `1`, absent sole-failure →
exit `1` with a "missing" message) each carry a behavioural or unit test, and a
byte-perturbation property gate guards the content comparison. The findings
below are tidy-up opportunities, not blocking defects.

One theme dominates: the implementation deliberately performs a **direct
byte comparison** (ExecPlan decision D-BYTE-COMPARE, "not a digest"), but the
design document and one developers'-guide sentence still describe a
**compile-and-*hash*** routine that "hashes" drafts. The code and the docs now
disagree on what the routine does.

Trail followed: explored with `leta` (`leta show`, `leta refs`, `leta files`,
`leta grep`) and traced history with `sem diff --commit 4c578e3`. Sources of
truth consulted: `docs/novel-ralph-harness-design.md` §2.3, §4.2, §4.3, §9;
`docs/developers-guide.md`; `docs/users-guide.md`; ADR-001, ADR-003, ADR-005;
`docs/roadmap.md` (tasks 3.1.2–3.1.4); and `AGENTS.md`. Skills loaded: `leta`,
`sem`, `python-router` (routing to `python-data-shapes` and `python-testing`).

## Finding 1 — design doc still describes a "compile-and-hash" routine the code does not implement

- **Category:** inconsistency
- **Severity:** medium

`docs/novel-ralph-harness-design.md` describes the compile-divergence machinery
as a **hashing** routine in several places:

- §2.3 / overview (lines 121–122): "`novel-compile --check`, which compares
  content hashes … shares one compile-and-hash routine".
- §4.2 (lines 353–364): "`novel-done` calls the shared compile-and-hash routine
  (§4.3) to **hash** each … `draft.md` … and compare its **hash** to
  `working/manuscript/compiled.md` … The `result` reports a single
  `compile_consistent` boolean, not the per-chapter **hashes** it computed
  internally."
- §4.3 (lines 387–390): "The compile-and-hash work — concatenating drafts in
  index order and **hashing** the result — lives in one shared routine".

The implementation does no hashing. `compile_consistent`
([`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py) lines
266–270) and the detector
([`disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py) lines
179–184) both do `compiled.read_text(...) == concatenate_drafts(present_draft_bodies(...))`
— an in-memory byte comparison of two strings. The clause's own docstring
(`done_predicate.py` lines 233–235) explicitly justifies this: "The verdict is a
direct byte comparison, not a digest (ExecPlan D-BYTE-COMPARE) … a boolean over
two in-memory strings needs no `hashlib`." `concatenate_drafts`
([`compile_model.py`](../../novel_ralph_skill/state/compile_model.py)) imports
no `hashlib` and computes no digest. The §4.2 claim that the routine computes
"per-chapter hashes … internally" is now simply false: there is no per-chapter
hash and no internal hash at all.

The 3.1.2 commit message asserts the design was updated ("hashes the result …
updates the design") but the §4 prose was not reconciled to the D-BYTE-COMPARE
decision, leaving the document internally and externally inconsistent.

- **Proposed fix:** Edit `docs/novel-ralph-harness-design.md` §2.3, §4.2, and
  §4.3 to describe a **compile-and-compare** (byte-comparison) routine rather
  than a hashing one. Replace "compile-and-hash routine" with "compile-and-
  compare routine"; rewrite the §4.2 paragraph (lines 353–364) to say
  `novel-done` recomputes the ordered concatenation of the drafts and compares
  it **byte-for-byte** against `compiled.md`, dropping the "hash each draft" and
  "per-chapter hashes it computed internally" language; and rewrite §4.3 lines
  387–390 to "concatenating drafts in index order" without "and hashing the
  result". Keep the bounded-`result` point (the clause reports one boolean, not
  the concatenated body) — that property holds for a byte comparison too. If a
  digest is genuinely wanted at a future scale (e.g. to avoid holding both bodies
  in memory for a hundred-chapter novel), record that as a separate, dated design
  note rather than describing it as the current behaviour.

## Finding 2 — developers' guide contradicts itself: "compile-and-hash" vs "not a digest"

- **Category:** inconsistency
- **Severity:** low

`docs/developers-guide.md` line 324 says `novel-done` and `novel-compile`
"call the same compile-and-**hash** routine (roadmap tasks 4.1.2 and 3.1.2)",
yet lines 575–583 of the same document say the verdict "is a direct byte
comparison, **not a digest** (D-BYTE-COMPARE) … the comparison is over bytes,
not counts." A reader cannot tell from the guide alone whether the routine
hashes or compares bytes.

- **Proposed fix:** Change line 324's "compile-and-hash routine" to
  "compile-and-compare routine" (or "shared byte-comparison routine") so it
  agrees with lines 575–583. This is a one-line edit and should land with the
  Finding 1 design-doc reconciliation so the two documents move together.

## Finding 3 — the `manuscript/compiled.md` path is derived independently in five sites

- **Category:** duplication
- **Severity:** medium

The working-relative `compiled.md` path is hand-joined in four places and named
as a string constant in a fifth, with no shared helper:

- [`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py) line
  266: `working_dir / "manuscript" / "compiled.md"`.
- [`disk_evidence.py`](../../novel_ralph_skill/state/disk_evidence.py) line 179:
  `working_dir / "manuscript" / "compiled.md"`.
- [`_compile.py`](../../novel_ralph_skill/commands/_compile.py) line 111:
  `root / "manuscript" / "compiled.md"` (plus the parallel string constant
  `_COMPILED_REL = "working/manuscript/compiled.md"` at line 59).
- [`_novel_done.py`](../../novel_ralph_skill/commands/_novel_done.py) line 126
  (`_failed_clause_message`): `root / "manuscript" / "compiled.md"`.
- [`_novel_done.py`](../../novel_ralph_skill/commands/_novel_done.py) line 171
  (`_sole_stale_compile`): `root / "manuscript" / "compiled.md"`.

The project already centralises the sibling `chapter-NN` derivation in
[`_disk_paths._chapter_dir_name`](../../novel_ralph_skill/state/_disk_paths.py)
precisely so the layout is defined once; `compiled.md` is the one manuscript
artefact that escaped that discipline. Five independent literals are a drift
hazard: a future relayout (e.g. `manuscript/output/compiled.md`) must be edited
in five spots, and the `_COMPILED_REL` string can diverge from the joined-path
form silently.

- **Proposed fix:** Add a `_compiled_path(working_dir: Path) -> Path` helper to
  [`_disk_paths.py`](../../novel_ralph_skill/state/_disk_paths.py) (its existing
  home for manuscript-layout joins) returning
  `working_dir / "manuscript" / "compiled.md"`, and route all four joined-path
  sites through it. Derive `_COMPILED_REL` from the same helper relative to the
  working root, or replace it with the helper's `Path` rendered relative to cwd,
  so the human-message string and the filesystem path cannot drift. This is a
  small, mechanical refactor that the 3.1.3 unification (which moves the
  *comparison* into `compile_model`) does not itself cover — 3.1.3 shares the
  verdict, not the path.

## Finding 4 — `compiled.md` existence is re-stat'd up to three times per `novel-done` run

- **Category:** complexity
- **Severity:** low

Within a single `_novel_done` invocation, `compiled.md`'s existence is queried
independently by `compile_consistent`
([`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py) line
267), by `_sole_stale_compile`
([`_novel_done.py`](../../novel_ralph_skill/commands/_novel_done.py) line 171),
and by `_failed_clause_message`
([`_novel_done.py`](../../novel_ralph_skill/commands/_novel_done.py) line 126).
Each call is a fresh `Path.exists()` stat. The three stats also encode the same
"is the compile present?" question three times, which is why the carve-out
docstring has to keep re-explaining that `DoneClauses` "carries only the six
booleans and cannot say *why* `compile_consistent` is false."

The redundant stats are cheap and the TOCTOU window is benign for a read-only
checker, so this is an ergonomics/altitude finding, not a correctness one. But
the repeated "stat again to recover the reason" pattern is a smell: the command
layer keeps reaching back to disk to reconstruct information the predicate layer
already had.

- **Proposed fix:** Have the predicate layer surface *why* `compile_consistent`
  is false once, rather than the command layer re-deriving it. The lightest
  option is a small enum or `present: bool` carried alongside the clause result
  (e.g. extend `DoneClauses` with a `compiled_present: bool` companion, or return
  a `CompileVerdict` with `consistent`/`present` fields), so `_sole_stale_compile`
  and `_failed_clause_message` read a field instead of re-statting. This pairs
  naturally with the 3.1.3 shared-helper work, which already touches the
  comparison both sides consume; fold the "present?" signal into that helper's
  return rather than three independent `exists()` calls. If the extra field is
  judged not worth it, at minimum stat once in `_novel_done` and thread the
  boolean to both helpers.

## Finding 5 — `compile_model` module docstring under-describes its three production consumers

- **Category:** docs-gap
- **Severity:** low

[`compile_model.py`](../../novel_ralph_skill/state/compile_model.py)'s module
docstring (lines 1–17) frames the module solely around the §5.4 disk-evidence
detector ("the `compiled-matches-drafts` disk-evidence invariant (roadmap task
2.3.2) … needs only the *divergence verdict*") and says "the full
compile-and-hash command is roadmap task 4.1.1's". As of 3.1.2 the module has
three production consumers, not one: the detector, the `compile_consistent` done
clause, **and** the `novel-compile` write path
([`_compile.py`](../../novel_ralph_skill/commands/_compile.py) lines 106–110)
already imports and uses `present_draft_bodies` / `concatenate_drafts`. The
docstring's "task 4.1.1's" deferral now reads as stale: the write path landed and
consumes this module today. The module-level docstring also still says
"compile-and-hash", inheriting Finding 1's terminology.

- **Proposed fix:** Update the `compile_model.py` module docstring to name all
  three current consumers (the §5.4 detector, the `novel-done`
  `compile_consistent` clause, and the `novel-compile` write path), drop or
  reword the "task 4.1.1's" forward-reference now that the write path consumes
  the routine, and replace "compile-and-hash" with the byte-comparison framing
  from Finding 1.

## Note — byte-comparison duplication between the clause and the detector is already scheduled

The verbatim byte-comparison body
(`compiled.read_text(...) == concatenate_drafts(present_draft_bodies(...))`)
appears in both `done_predicate.compile_consistent` and
`disk_evidence._check_compiled_matches_drafts`, differing only in the
absent-file polarity (the clause returns `False`, the detector returns "no
violation"). This is genuine duplication, but it is **already owned by roadmap
task 3.1.3**, which schedules a shared `compiled_matches_drafts(state,
working_dir)` helper in `compile_model.py` that both sides consume, each
supplying its own absent-file polarity. It is recorded here only so the root
agent does not double-book it; no new roadmap item is proposed for it.
