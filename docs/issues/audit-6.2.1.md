# Post-merge audit: roadmap task 6.2.1

Audit of the codebase after roadmap task 6.2.1 ("build the combinatorial
command-surface test suite", commit `dc46d4a`) merged to `main`. The task added
`tests/test_command_surface_matrix.py` and its snapshot file, documented the
matrix in `docs/developers-guide.md`, and ticked the roadmap. The new suite
drives all five read surfaces (`novel-state check`, `novel-done`, `wordcount`,
`novel-compile --check`, `desloppify`) in-process through the shared `run` seam
across the eleven coherent `working_corpus` phase states, in both output modes.

The change is sound and the roadmap success clause is met: the matrix is the
single cross-product home, the carried gaps are documented rather than silently
omitted, and every snapshot is paired with a semantic assertion as `AGENTS.md`
requires. The findings below are not regressions introduced by 6.2.1; they are
pre-existing duplication and consistency drift across the five command bodies
that 6.2.1 now exercises end-to-end, plus a small number of test/documentation
locality gaps in the new matrix module. None block the merge.

Sources relied on: `docs/novel-ralph-harness-design.md` (§2.3 verification
surface, §3.2 exit codes, §3.3 checker/mutator split, §4.1-§4.5 command bodies,
§5.4 disk evidence), `docs/adr-003-shared-interface-contract.md`,
`docs/adr-005-command-surface-five-scripts.md`, `docs/developers-guide.md` ("The
combinatorial command-surface matrix"), `docs/roadmap.md` (task 6.2.1), and
`AGENTS.md` (en-GB Oxford spelling, module/file boundaries, snapshot-plus-
semantic rule). Loaded the `python-router` skill; navigated code with
`leta`/`grep` and traced history with `git show`/`sem` over commit `dc46d4a`.

## Finding 1: The fixed `working/` accessors are bypassed by two command bodies

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_desloppify.py:194-195`
  (`source_chapters`) and `novel_ralph_skill/commands/_wordcount.py:130-131`
  (`source_state_and_drafts`).

`novel_state.py` documents `working_dir()` (line 92) and `state_path()` (line
103) as "the single `WORKING_DIR_NAME`-anchored accessor for the working root"
and "the single accessor every command routes through ... so the canonical
`state.toml` path is constructed in exactly one place (audit:1.3.5;
audit:2.2.2 Finding 3)". The `_compile`, `_novel_done`, and the mutator/`recount`
modules honour this — `_compile.py` and `_novel_done.py` import `working_dir`
and `state_path`, and `_state_mutators.py:38-44` re-exports them as
`_working_dir`/`_state_path`. But `_desloppify.source_chapters` and
`_wordcount.source_state_and_drafts` both re-spell the accessor inline:

```python
working_dir = pathlib.Path(WORKING_DIR_NAME)
state = _load_or_state_error(working_dir / "state.toml")
```

This is exactly the `pathlib.Path(WORKING_DIR_NAME)` / `/ "state.toml"`
reconstruction the `working_dir()`/`state_path()` accessors exist to abolish, and
the two modules already import `_load_or_state_error` and `WORKING_DIR_NAME` from
`novel_state`, so importing `working_dir`/`state_path` adds no new coupling and
no circular import. The drift is invisible today because both spell the same
strings, but it defeats the documented single-source invariant: a future change
to how the working root is resolved (the design notes "There is no
`--working-dir` flag" but a test seam may want one) would have to find these two
inline sites by hand.

- **Proposed fix:** Replace the two inline reconstructions with
  `working_dir()`/`state_path()` imported from `novel_state` (shadowing the local
  `working_dir` name as `_compile`/`_novel_done` already do). In `_desloppify`
  this also lets `_chapter_text` take the `working_dir()` result rather than a
  freshly built `pathlib.Path`. Net change is two import lines and two call sites;
  it brings the last two command bodies onto the accessor the module docstrings
  already claim is universal.

## Finding 2: `manuscript/compiled.md` is spelled two ways inside one module

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_compile.py:73` (`_COMPILED_REL =
  "working/manuscript/compiled.md"`) versus `:144` (`compiled_path = root /
  "manuscript" / "compiled.md"`).

`_compile.py` names the compiled-file path once as `_COMPILED_REL` "so the
written file, the success `result`, and the human message cannot drift" (line
69-72), and uses that constant for the envelope `result`, the messages, and the
error strings (lines 150-232). Yet the *actual write target* at line 144 is
rebuilt independently as `root / "manuscript" / "compiled.md"`. The two are kept
in agreement only by hand: if `_COMPILED_REL` were ever repointed (say to
`manuscript/whole.md`), the envelope would advertise the new name while the write
still landed on the old path, and `novel-compile --check` (which reads via the
shared `compiled_matches_drafts`) would then diverge from what `novel-compile`
wrote. The same physical file is also re-derived in `_novel_done.py:126,171`,
`state/compile_model.py:105`, `state/done_predicate.py`, and
`state/disk_evidence.py`, so the `manuscript/compiled.md` join is currently a
five-site magic path.

- **Proposed fix:** Derive the write target from the single constant — e.g.
  `compiled_path = root / pathlib.PurePosixPath(_COMPILED_REL).relative_to(
  WORKING_DIR_NAME)` — or, more cleanly, expose a `compiled_path(working_dir)`
  accessor in `state/compile_model.py` (which already builds `working_dir /
  "manuscript" / "compiled.md"` at line 105) and have `_compile`, `_novel_done`,
  and the disk-evidence/done-predicate readers all route through it. This makes
  the compiled-file location a single owned fact rather than a string repeated in
  five modules.

## Finding 3: The done-predicate's "compiled.md present?" stat is duplicated

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_novel_done.py:124-127`
  (`_failed_clause_message`) and `:169-171` (`_sole_stale_compile`).

Both helpers answer the same physical question — "does
`manuscript/compiled.md` exist under `root`?" — with the same inline
`(root / "manuscript" / "compiled.md").exists()` expression. They are two reads
of one fact (whether the compile is stale-present or absent) that drive the
carve-out: `_sole_stale_compile` gates the exit-4 path and
`_failed_clause_message` chooses the human wording. Because the stat is spelled
twice, a change to where `compiled.md` lives must be made in both, and the two
could silently disagree about presence between the two calls (they are separate
`stat` calls, so a deletion racing between them would already produce an
inconsistent envelope — exit 4 with a "missing" message).

- **Proposed fix:** Compute the presence once — a module-private
  `_compiled_present(root) -> bool` (or the shared accessor from Finding 2) — and
  pass the boolean to both helpers, so the carve-out decision and its message are
  driven by a single read. This also removes the in-body race between the two
  `exists()` calls.

## Finding 4: The matrix encodes per-command behaviour in two parallel tables

- **Category:** ergonomics
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:126` (`_COMPILE_OK_PHASES`)
  and `:312-336` (`_expected_ok`), against `:152` (`_DRAFTING_ERA_PHASES`).

The expected `ok` sign per cell is encoded as a hand-maintained branch ladder in
`_expected_ok` (novel-done → always False; novel-compile → `_COMPILE_OK_PHASES`;
else True), while the per-command branch tests (`test_compile_check_branches_
across_phases`, `test_wordcount_branch_across_phases`,
`test_desloppify_shape_across_phases`) re-derive the *same* phase partition from
`_DRAFTING_ERA_PHASES`. For `novel-compile`, `_COMPILE_OK_PHASES = {final-pass,
done}` and `_DRAFTING_ERA_PHASES = {drafting, final-pass, done}` are two
different slicings of the same axis kept consistent only by the author's care;
the relationship (`compile is ok on the drafting-era phases minus drafting`) is
implicit. A new phase added to `wc.PHASE_ORDER` would need both `_expected_ok`
and the per-command tables audited by hand to decide which bucket it falls in,
with no single place that says "this is the manifest/compiled partition".

- **Proposed fix:** Promote one small per-command expectation record (e.g. a
  `NamedTuple` of `ok_phases: frozenset[str]` plus the branch-shape predicate)
  keyed off the two real partitions (`_DRAFTING_ERA_PHASES` and the
  compiled-present subset), and have both `_expected_ok` and the branch tests
  read from it. This keeps the cross-product `ok` sign and the per-command branch
  assertions derived from one declared partition rather than two restatements.

## Finding 5: Error-path cells (exit 2/3 human envelopes) are not snapshotted

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:288-309`
  (`test_human_mode_presence_matrix`) and the module's `Carried gaps` section
  (lines 41-57).

The matrix snapshots the machine envelope for every cell and asserts human-mode
*presence*, but the only non-zero exit cells it crosses are the
`novel-compile --check` exit-3 pre-drafting refusals (asserted for presence,
not pinned). The contract's other diagnostic envelopes — the usage-error (exit
2) `CycloptsError` arm and the state-error (exit 3) `StateInputError` arm in
`contract/runner.py:225-239`, which stamp `--human` into an envelope *the
command body never produced* (the very reason `parse_global_flags` runs before
`run`, per `runner.py` lines 88-96) — are exercised only by per-command suites,
never by the cross-product matrix. The module docstring lists mutator-by-phase,
exhaustive-eleven-phase, incoherent-by-phase, and installed-binary as carried
gaps, but does not name the *error-mode-by-command* gap, so a reader cannot tell
whether it was a deliberate bound or an oversight.

- **Proposed fix:** Either add a small error-mode slice to the matrix (drive each
  command over a deliberately empty/absent `working/` and pin the exit-3 envelope
  plus its `--human` rendering, for at least one command, since the runner's
  exit-2/3 arms are command-agnostic), or — if that is intentionally left to the
  per-command suites — add an "error-mode-by-command cross-product" bullet to the
  `Carried gaps` section naming where it is covered, so the bound is documented
  rather than silent (design §9 "carried knowingly rather than silently").

## Finding 6: Task 6.2.1 landed an MD012 markdownlint regression in the dev guide

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `docs/developers-guide.md:86-87` (two consecutive blank lines
  before the `### The combinatorial command-surface matrix` heading the task
  added).

The 6.2.1 commit inserted the new matrix section into the developers' guide with
two blank lines before its heading, which trips `MD012/no-multiple-blanks`. As a
result `make markdownlint` over the whole tree fails on `main` at commit
`dc46d4a` (the task's commit message claims to "green the markdownlint gate",
but the gate is red post-merge). This was fixed as part of recording this audit
(the docs-only change is committed alongside this file) by collapsing the double
blank to a single line; the finding is recorded so the regression — a quality
gate reported green while red — is not lost.

- **Proposed fix:** Already applied: removed the extra blank line at
  `docs/developers-guide.md:86`. No further action needed beyond noting that the
  6.2.1 gating run did not exercise `make markdownlint` over the full tree, or it
  would have caught this; the post-merge audit gate is what surfaced it.

## Finding 7: The matrix module is exempted from the line cap without a §-cited basis

- **Category:** docs-gap
- **Severity:** low
- **Location:** `tests/test_command_surface_matrix.py:60-67` (the
  `pylint: disable=too-many-lines` rationale comment).

The `too-many-lines` relaxation is justified by analogy ("for the same reason
`tests/test_working_corpus.py` and `tests/test_validate_state_property.py`
relax it") and by the design's "single home for the whole matrix" intent. That
is reasonable, but the `developers-guide.md` matrix section (lines 88-113) — the
documented place a maintainer is told to "read before extending the matrix" —
does not record that the module is over cap or *why* the cap is relaxed, so the
rationale lives only in an inline lint-disable comment. A maintainer adding a new
cell from the guide would not learn the module is already at its size ceiling.

- **Proposed fix:** Add one sentence to the developers' guide matrix section
  noting the module is deliberately over the 400-line cap (it co-locates the
  snapshot matrix, the human-presence matrix, and the per-command branch
  assertions by design) and cross-referencing the in-module rationale, so the
  size decision is documented where extenders are sent.
