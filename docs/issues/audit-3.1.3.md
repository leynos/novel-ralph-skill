# Post-merge audit — roadmap task 3.1.3

Audit of the codebase after roadmap task 3.1.3 ("Share the compiled-matches-
drafts comparison across §5.4 and `compile_consistent`") merged to `main` at
commit `e4ed286`. The slice factors the "does `compiled.md` equal the ordered
draft concatenation?" comparison into a single production helper,
[`compile_model.compiled_matches_drafts`](../../novel_ralph_skill/state/compile_model.py),
returning the three-valued `CompiledComparison` (`ABSENT`/`MATCHES`/`DIVERGES`).
Both production callers — the §5.4 detector
[`disk_evidence._check_compiled_matches_drafts`](../../novel_ralph_skill/state/disk_evidence.py)
and the
[`done_predicate.compile_consistent`](../../novel_ralph_skill/state/done_predicate.py)
clause — now consume that one helper, each projecting the verdict to its own
absent-file polarity. This removes the third re-implementation of the comparison
that [`audit-3.1.1.md`](audit-3.1.1.md) Finding 2 flagged, so the predicate and
the detector can no longer disagree on what "compiled matches drafts" means. The
test-side corpus oracle keeps its own copy by design (the invariant-validation
twin policy), so a production bug cannot mask itself.

The slice is correct and of a high standard. The shared helper is total, its
fault boundary (existence check before any draft read; benign-absent draft;
propagate every other fault) is carefully reasoned and pinned by
[`test_compiled_matches_drafts.py`](../../tests/test_compiled_matches_drafts.py),
including an ordering test (`test_checks_existence_before_reading`) that locks
the short-circuit so a future refactor reading drafts unconditionally is caught.
The detector's projection has its own pin
(`test_disk_evidence.py::test_compiled_matches_drafts_projection`). The findings
below are tidy-up and consistency items, not blocking defects.

One theme dominates and is **inherited and reinforced**: the implementation
performs a **direct byte comparison** (ExecPlan decision D-BYTE-COMPARE, "not a
digest"), but the design document, the developers' guide, the roadmap, and the
`_compile.py` module docstring still describe a **compile-and-*hash*** routine
that "hashes" drafts. The 3.1.2 audit recorded this as its Finding 1 and Finding
2, but no roadmap task was opened to reconcile it, so the divergence has widened:
3.1.3 added a new shared helper whose entire job is a byte comparison while the
prose still says "hash".

Trail followed: explored with `leta`/ripgrep (`leta show`, `leta files`) and
traced history with `sem` / `git show e4ed286`. Sources of truth consulted:
`docs/novel-ralph-harness-design.md` §2.3, §4.2, §4.3, §9; `docs/developers-
guide.md`; `docs/roadmap.md` (tasks 3.1.2–3.1.4, 4.1.2, 7.10.3); ADR-001;
`docs/issues/audit-3.1.1.md` and `docs/issues/audit-3.1.2.md`; and `AGENTS.md`.
Skills loaded: `leta`, `sem`, `python-router` (routing to `python-data-shapes`
and `python-testing`).

## Finding 1 — design doc, devguide, and roadmap still describe a "compile-and-hash" routine the code does not implement

- **Category:** inconsistency
- **Severity:** medium

The implementation does no hashing anywhere. The shared
[`compiled_matches_drafts`](../../novel_ralph_skill/state/compile_model.py) helper
(lines 105–111) does `compiled.read_text(...) == concatenate_drafts(...)` — an
in-memory byte comparison of two strings — and `concatenate_drafts` imports no
`hashlib` and computes no digest. The `compile_consistent` docstring
(`done_predicate.py` lines 239–241) explicitly justifies this: "The helper
performs a direct byte comparison, not a digest (ExecPlan D-BYTE-COMPARE): a
boolean over two in-memory strings needs no `hashlib`."

Yet the prose still describes a hashing routine in many places:

- `docs/novel-ralph-harness-design.md` §2.3 (lines 121–122) "compares content
  hashes … shares one compile-and-hash routine"; §4.2 (lines 354–362) "hash each
  … `draft.md` … and compare its hash … per-chapter hashes it computed
  internally"; §4.3 (lines 387–390) "concatenating drafts in index order and
  hashing the result".
- `docs/developers-guide.md` line 329 "call the same compile-and-**hash**
  routine", which contradicts the same guide's lines 583–585 ("a direct byte
  comparison, not a digest (D-BYTE-COMPARE)").
- `docs/roadmap.md` lines 748, 906, 935–943, 1009, 1038 ("compile-and-hash
  routine … hashes the result … never per-chapter hashes … the hashing
  approach").
- `novel_ralph_skill/commands/_compile.py` module docstring (lines 26–27) "the
  `--check` divergence checker and the compile-and-hash routine are roadmap tasks
  4.1.2 and 3.1.2", which both names a routine that does not hash and carries a
  stale forward-reference (task 3.1.2 has merged).

This was [`audit-3.1.2.md`](audit-3.1.2.md) Finding 1 and Finding 2. It was not
turned into a roadmap task, so the gap remains — and 3.1.3 widened it by adding
a new helper, `compiled_matches_drafts`, whose sole purpose is the byte
comparison
the docs still call hashing. A reader cannot tell from the design doc, the
devguide, or the roadmap whether the routine hashes or compares bytes; the code
is unambiguous (it compares bytes), so the docs are wrong.

- **Proposed fix:** Reconcile the prose to the D-BYTE-COMPARE decision across all
  four documents in one sweep. Replace "compile-and-hash routine" with
  "compile-and-compare routine" (or "shared byte-comparison routine"); rewrite
  the design §4.2 paragraph to say `novel-done` recomputes the ordered
  concatenation and compares it **byte-for-byte** against `compiled.md`, dropping
  "hash each draft" and "per-chapter hashes it computed internally"; rewrite §4.3
  to "concatenating drafts in index order" without "and hashing the result"; fix
  devguide line 329; and update the roadmap's still-open downstream tasks (4.1.2
  at line 1038, plus the framing at 906/1009) so they describe a byte-comparison
  divergence checker rather than a hashing one. Keep the bounded-`result` point
  (one boolean, not the per-chapter bodies) — it holds for a byte comparison too.
  If a digest is genuinely wanted at future scale (e.g. to avoid holding both
  bodies in memory for a hundred-chapter novel), record that as a separate dated
  design note rather than describing it as current behaviour. This is a
  documentation-only reconciliation and a strong candidate for a dedicated
  roadmap task (see proposed roadmap item).

## Finding 2 — `_compile.py` module docstring carries a stale "task 3.1.2 … compile-and-hash" forward-reference

- **Category:** inconsistency
- **Severity:** low

[`_compile.py`](../../novel_ralph_skill/commands/_compile.py) lines 26–27 read:
"This is the write path only; the `--check` divergence checker and the compile-
and-hash routine are roadmap tasks 4.1.2 and 3.1.2 (ExecPlan D-SCOPE)." Two
things are now stale: (a) task 3.1.2 has merged, so the "are roadmap tasks …"
forward-reference is wrong — the shared comparison routine exists today and
`_compile.py` itself imports `concatenate_drafts`/`present_draft_bodies` from it;
and (b) the routine is named "compile-and-hash" although it performs no hashing
(Finding 1). This is a narrower instance of Finding 1 colocated with the code,
so it is unlikely to be caught by a docs-only sweep that greps the `docs/` tree.

- **Proposed fix:** Update the `_compile.py` module docstring to (a) state that
  the shared compile-and-compare routine has landed (tasks 3.1.2/3.1.3) and that
  this module reuses its `present_draft_bodies`/`concatenate_drafts` read-and-join
  rules, keeping only the genuinely-deferred `--check` divergence checker as a
  forward-reference to task 4.1.2; and (b) drop the "hash" terminology in favour
  of "compare". Fold this into the Finding 1 reconciliation so the source comment
  and the design doc move together.

## Finding 3 — three of `CompiledComparison`'s docstrings repeat the same projection-table prose

- **Category:** duplication
- **Severity:** low

The "each caller projects the three-valued verdict to its own absent-file
polarity — the detector treats absent as satisfied, the content clause treats
both absent and divergent as not-done (only `MATCHES`)" explanation is written
out three times in near-identical form: in `CompiledComparison`'s class docstring
([`compile_model.py`](../../novel_ralph_skill/state/compile_model.py) lines
48–49), in `compiled_matches_drafts`'s docstring (lines 64–70), and again in both
consumer docstrings (`disk_evidence._check_compiled_matches_drafts` lines 177–181
and `done_predicate.compile_consistent` lines 235–246). This is documentation
duplication, not code duplication — the 3.1.3 slice deliberately and correctly
removed the *code* duplication — but the same projection table is now maintained
in four docstrings, so a future change to either polarity must be reflected in
four places or they drift.

- **Proposed fix:** Make the `compiled_matches_drafts` helper docstring the single
  authoritative statement of the projection table (it is the shared seam), and
  have the two consumer docstrings state only their *own* projection ("maps
  `DIVERGES` → violation, `ABSENT`/`MATCHES` → none; see `compiled_matches_drafts`
  for the full table") rather than re-deriving the other caller's polarity. This
  trims the maintenance surface without losing the rationale. Low priority — the
  current prose is accurate, just redundant.

## Finding 4 — no behavioural/e2e test exercises a present-but-stale `compiled.md` end-to-end through both consumers on one tree

- **Category:** test-gap
- **Severity:** low

The 3.1.3 suites pin the helper in isolation
([`test_compiled_matches_drafts.py`](../../tests/test_compiled_matches_drafts.py))
and the detector's projection
(`test_disk_evidence.py::test_compiled_matches_drafts_projection`). The
`done_predicate.compile_consistent` projection of the *shared* helper, however,
is covered only transitively by the pre-existing 3.1.2 done-predicate suites; the
3.1.3 slice adds no test that drives a single tree carrying a present-but-stale
`compiled.md` through **both** consumers and asserts the deliberately-opposite
verdicts (the §5.4 detector reports a `compiled-matches-drafts` violation while
`compile_consistent` returns `False`). The whole point of the slice is that the
two cannot disagree because they share one helper; a test that asserts the two
*projections* of the same `DIVERGES` verdict on one tree would lock that
invariant directly rather than leaving it implied by two separate suites.

- **Proposed fix:** Add a small unit test (in
  `test_compiled_matches_drafts.py` or a new cross-consumer test) that builds
  one drafting tree with a stale
  `compiled.md`, then asserts in the same test that
  `disk_evidence._check_compiled_matches_drafts(...)` returns the named violation
  **and** `done_predicate.compile_consistent(...)` returns `False` — pinning the
  "same `DIVERGES`, opposite polarity, never disagree" contract on one tree.
  Optionally extend it with the `MATCHES` row (no violation / `True`) so the
  agreement is shown across two verdicts. This is the natural behavioural
  expression of the slice's stated goal and is currently only implied.

## Note — byte-comparison code duplication is now resolved

For the record: the verbatim byte-comparison body that
[`audit-3.1.2.md`](audit-3.1.2.md) recorded as still-duplicated between
`compile_consistent` and `_check_compiled_matches_drafts` (its closing Note) is
**resolved** by this slice — both now call the one `compiled_matches_drafts`
helper. The remaining duplication is documentation-only (Finding 3) and the
deliberate test-side twin in `tests/working_corpus/_oracle.py`, which is correct
by the twin policy and must not be collapsed.
