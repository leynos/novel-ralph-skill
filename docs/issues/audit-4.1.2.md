# Post-merge audit — roadmap task 4.1.2 (`novel-compile --check`)

This audit follows the merge of roadmap task 4.1.2, which added the read-only
`--check` divergence checker to `novel-compile` (commit `fae021f`). The checker
reuses the shared verdict routine `compile_model.compiled_matches_drafts` (the
same routine the `novel-done` `compile_consistent` clause consumes), writes
nothing on any path, and exits `4` when `compiled.md` is stale or absent.

Sources of truth consulted: `docs/novel-ralph-harness-design.md` §3.3 and §4.3;
`docs/adr-001-deterministic-judgemental-boundary.md`; the developers' and users'
guides; `docs/issues/audit-3.1.1.md`, `audit-3.1.2.md`, and `audit-3.1.3.md`
(the prior compile-verdict slices). Skills relied on: `python-router` (routing),
`leta`/`grepai` for navigation, `sem`/`git` for history.

The slice is correct, thoroughly tested (unit, behavioural, agreement,
snapshot, and e2e), and exceptionally well-documented. The headline criterion —
`novel-compile --check` and `compile_consistent` agree on every corpus fixture —
is pinned directly by `tests/test_compile_check_agreement.py`. The findings
below are quality refinements; none is a correctness defect.

## Finding 1 — the "content polarity" projection is now duplicated in two call sites

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_compile.py:213`
  (`check_compiled`) and `novel_ralph_skill/state/done_predicate.py:273`
  (`compile_consistent`)

`compile_consistent` returns `compiled_matches_drafts(...) is
CompiledComparison.MATCHES`. `check_compiled` re-expresses the identical
predicate as `if verdict is CompiledComparison.MATCHES:` to choose its exit
code. Both encode the same "content polarity" decision — *only* `MATCHES` means
"the compile is current; `ABSENT` and `DIVERGES` are not". The 3.1.3 slice
collapsed the three prior re-implementations of the *comparison* into one shared
helper; 4.1.2 has now introduced a second copy of the *projection* of that
helper's result to the current/not-current boolean. A future decision to treat,
say, `ABSENT` differently in one of the two consumers would require editing both
sites and could silently break the agreement invariant between them.

- **Proposed fix:** Add a single named predicate beside the helper in
  `compile_model.py`, e.g. `def compile_is_current(verdict: CompiledComparison)
  -> bool: return verdict is CompiledComparison.MATCHES`, and have both
  `compile_consistent` and `check_compiled` call it. This makes the content
  polarity a named seam with one definition, mirroring how `compiled_matches_drafts`
  is the one comparison seam. The agreement test then pins behaviour the code
  also makes structurally impossible to drift. (Leave the detector's *opposite*
  polarity — `DIVERGES` is a violation — as its own named predicate or inline,
  since it is genuinely a different projection.)

## Finding 2 — `compiled.md`'s path has no single source of truth across four modules

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_compile.py:73,144`;
  `novel_ralph_skill/state/compile_model.py:105`;
  `novel_ralph_skill/commands/_novel_done.py:126,171`

The relative path to the compiled manuscript is built independently in at least
four places: `_compile.py` holds the working-relative string token
`_COMPILED_REL = "working/manuscript/compiled.md"` and *separately* builds
`root / "manuscript" / "compiled.md"`; `compile_model.py` builds `working_dir /
"manuscript" / "compiled.md"`; and `_novel_done.py` builds `root / "manuscript"
/ "compiled.md"` twice. The `"manuscript"` and `"compiled.md"` path segments are
literals repeated across these modules. 4.1.2 did not introduce this, but it
added the `check_compiled` consumer that re-uses `_COMPILED_REL` for its
`result`/messages while the actual filesystem read happens inside
`compile_model.py` against an independently constructed path. The two cannot
drift today only because both hard-code the same literals.

- **Proposed fix:** Promote the path construction to `compile_model.py` (which
  owns the join rule) — e.g. a `compiled_manuscript_path(working_dir: Path) ->
  Path` and a `COMPILED_REL` constant for the envelope token — and have
  `_compile.py`, `compile_model.py`, and `_novel_done.py` import them. This makes
  the manuscript's on-disk location a single named fact, consistent with the
  module's existing role as owner of `DRAFT_SEPARATOR` and the join rule.

## Finding 3 — the projection-table prose is now repeated in a fourth docstring

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_compile.py:176-184`
  (`check_compiled` docstring)

`docs/issues/audit-3.1.3.md` Finding 3 already observed that the absent-file
projection table ("the detector treats absent as satisfied, the content clause
treats both absent and divergent as not-done — only `MATCHES` holds") was
maintained in multiple docstrings. 4.1.2 adds a fourth copy: `check_compiled`'s
docstring restates the same table, including the "opposite polarity to the §5.4
detector" contrast. The prose is accurate, but a future change to either
polarity must now be reflected in four docstrings to stay truthful, and the cost
of that synchronisation grows with each consumer.

- **Proposed fix:** Adopt the remediation proposed in audit-3.1.3 Finding 3,
  extended to this new site: make the `compiled_matches_drafts` docstring in
  `compile_model.py` the single authoritative statement of the full projection
  table, and have each consumer docstring (`check_compiled`,
  `compile_consistent`, `_check_compiled_matches_drafts`) state only its *own*
  projection in one sentence and cross-reference the helper for the comparison
  rationale. This finding is a reinforcement of an existing open item, not a new
  category of problem.

## Finding 4 — `compiled_matches_drafts` has a benign exists/read race window

- **Category:** complexity
- **Severity:** low
- **Location:** `novel_ralph_skill/state/compile_model.py:106-110`

The helper performs `if not compiled.exists(): return ABSENT` and then
`compiled.read_text(...)`. Between the `exists()` probe and the `read_text()`
there is a time-of-check-to-time-of-use window: if `compiled.md` is removed in
that interval the `read_text()` raises `FileNotFoundError`, which the design
classifies (per the docstrings) as a non-absent fault that *propagates* to the
exit-`3` channel — yet a file that vanished is semantically `ABSENT`, the exit-`4`
verdict. The window is vanishingly small in the single-writer harness, so this is
not a live bug, but the two-syscall pattern is slightly more code than necessary
and encodes the absent/fault boundary in a place a race can blur.

- **Proposed fix:** Collapse the probe and read into one operation: attempt
  `compiled.read_text(encoding="utf-8")` inside a `try`, mapping
  `FileNotFoundError` to `CompiledComparison.ABSENT` and letting every other
  `OSError`/`UnicodeDecodeError` propagate unchanged. This removes the race, drops
  one syscall on the hot path, and makes "the file is absent" a single decision
  point rather than two. Pin the new behaviour with a test that deletes
  `compiled.md` is out of scope (the race is not reproducible deterministically),
  but the existing absent-file test continues to cover the common path.

## Coverage and consistency observations (no action required)

- Behavioural (`compile.feature`), agreement, snapshot, unit, and e2e tests all
  cover the `--check` path, including the no-write guarantee, the three verdicts,
  the exit-`3` fault boundary, and the kw-only `--check` flag (exit `2` on a
  stray positional). Command-query segregation is respected: the checker is a
  pure query (`check_compiled`) and never reaches the write branch.
- Developers' and users' guides were both updated and correctly note the
  "compile-and-hash" naming is historical (the verdict is a direct byte
  comparison, no `hashlib`). No documentation gap was found for the new mode.
