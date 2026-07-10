# Post-merge audit — roadmap task 3.1.1

Audit of the codebase after task 3.1.1 ("Implement the per-clause `novel-done`
predicate") merged to `main` at commit `a59d787`. The task wired the `novel-done`
console-script to a real, read-only done predicate: a pure
`(State, working_dir) -> DoneClauses` engine
(`novel_ralph_skill/state/done_predicate.py`) that evaluates the six design §4.2
clauses against the typed `state.toml` and the on-disk `working/` tree and writes
nothing on any path (ADR-001). The command body
(`novel_ralph_skill/commands/_novel_done.py`) projects the clauses into the
shared envelope (exit `0` when all hold, exit `1` naming the unmet clauses, exit
`3` on a state/input fault), reusing `novel-state`'s `working_dir`, `state_path`,
`_load_or_state_error`, and `STATE_INPUT_ERRORS` seams; the `stub.py`
`novel_done()` entry point drives it through the shared `run` wrapper. The slice
ships unit, BDD, snapshot, and console-script e2e suites plus developers'- and
users'-guide updates.

The implementation is of a high standard. The engine is genuinely pure and
read-only, the fault boundary (benign-absent / propagate-everything-else) is
carefully reasoned and documented, the `KNITTING_PERCENTAGES` constant single-
homes the gate/file-name pairing so they cannot drift, `DoneClauses` is a frozen
slotted dataclass with doctested projections, and the docstrings are exhaustive
and design-cited. The developers' guide candidly records the three known
limitations (the BLOCKER brittleness, the manifest-vs-outline divergence, the
existence-only `compile_consistent`). The findings below are refinement
opportunities, not defects; none blocks the merge, and several are continuations
of items already recorded in `audit-4.1.1.md`.

Trail followed: `docs/novel-ralph-harness-design.md` §§3.2/3.3/4.2/4.3/5.2/5.4,
`docs/developers-guide.md` (done-predicate section, command surface),
`docs/users-guide.md`, `docs/roadmap.md` tasks 3.1.1/3.1.2/4.1.2,
`docs/adr-001` (deterministic/judgemental boundary), `docs/adr-005` (command
surface), `docs/issues/audit-4.1.1.md` (prior findings this slice extends),
`AGENTS.md` (quality gates, the 400-line cap, CQS, en-GB Oxford spelling), the
`python-router` skill (routed to `python-data-shapes` and
`python-errors-and-logging`), and `leta`/`sem` for navigation and history. Files
inspected: `novel_ralph_skill/state/done_predicate.py`,
`novel_ralph_skill/commands/_novel_done.py`,
`novel_ralph_skill/commands/stub.py`,
`novel_ralph_skill/commands/novel_state.py`,
`novel_ralph_skill/commands/_desloppify.py`,
`novel_ralph_skill/commands/_compile.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/_disk_paths.py`,
`tests/test_done_predicate.py`, `tests/test_novel_done_command.py`,
`tests/test_novel_done_e2e.py`, `tests/test_novel_done_snapshots.py`,
`tests/corpus_done_predicate_fixtures.py`.

## Finding 1 — `done_predicate.py` adds three more hand-built `manuscript/`/`reviews/` joins

**Category:** duplication · **Severity:** medium

**Location:** `novel_ralph_skill/state/done_predicate.py:182`
(`working_dir / "manuscript"`), `:204` (`working_dir / "reviews"`), `:220`
(`working_dir / "manuscript" / "compiled.md"`), `:250`
(`working_dir / "manuscript"`).

**Description:** `audit-4.1.1.md` Finding 1 recorded that the `"manuscript"`
directory segment and the `compiled.md` leaf are rebuilt by hand in at least
seven places, and proposed `manuscript_dir(working_dir)` and
`compiled_path(working_dir)` accessors beside `_chapter_dir_name` in
`state/_disk_paths.py`. Task 3.1.1 added four more raw joins — including a fourth
independent spelling of `working_dir / "manuscript" / "compiled.md"` that must
stay byte-identical to the one the `_compile` write path and the
`_check_compiled_matches_drafts` detector use, and a new `reviews/` literal that
the knitting-review file names depend on. The `compiled.md` path now appears in
at least three modules (`_compile.py`, `disk_evidence.py`, `done_predicate.py`),
each authored independently; a relocation would have to touch every site and a
missed one would silently diverge.

**Proposed fix:** Land the `audit-4.1.1` Finding 1 accessors
(`manuscript_dir`, `compiled_path`, and a `reviews_dir`) in
`state/_disk_paths.py` and route `done_predicate.py`'s four joins through them
together with the existing call sites. This makes the write/detector/predicate
path contract a code-level single source of truth rather than a test-only
invariant, and stops each new disk-aware module from re-spelling the layout.

## Finding 2 — `compile_consistent` existence check and the §5.4 hash detector will collide at 3.1.2

**Category:** separation-of-concerns · **Severity:** medium

**Location:** `novel_ralph_skill/state/done_predicate.py:211`
(`compile_consistent_exists`) versus
`novel_ralph_skill/state/disk_evidence.py:167`
(`_check_compiled_matches_drafts`).

**Description:** `compile_consistent_exists` is the deliberately partial v1
clause: it asserts only that `compiled.md` exists, deferring the
present-but-stale case to roadmap 3.1.2 (ExecPlan D-COMPILE-EXISTENCE). But the
full "compiled.md is the ordered concatenation of the present drafts" check
already exists, fully implemented and tested, in
`disk_evidence._check_compiled_matches_drafts`, which recomputes
`concatenate_drafts(present_draft_bodies(...))` and compares bytes. When 3.1.2
lands the hash comparison, there is a real risk it re-implements that comparison
a third time (the §5.4 detector, the future 3.1.2 clause, and the existing
oracle each computing "does compiled.md match the drafts") with subtly different
fault handling, rather than the done-predicate clause delegating to the one §5.4
rule. The two also already disagree on polarity and on the absent-compile verdict
(the §5.4 invariant treats *absent* `compiled.md` as trivially satisfied; the
done clause treats absent as *false*), so a naive reuse would be wrong — the
divergence needs a deliberate shared seam, not a copy.

**Proposed fix:** Before 3.1.2, factor the "compiled.md equals the ordered draft
concatenation" comparison into one pure helper in `compile_model.py` (e.g.
`compiled_matches_drafts(state, working_dir) -> bool`) that both
`_check_compiled_matches_drafts` and the future `compile_consistent` clause call,
each wrapping it with its own absent-file polarity. Record this as the intended
3.1.2 shape so the implementer reuses the rule rather than re-deriving it.

## Finding 3 — The unresolved-BLOCKER substring rule can be defeated by an unrelated `[resolved]` mention

**Category:** complexity · **Severity:** low

**Location:** `novel_ralph_skill/state/done_predicate.py:223-240`
(`_contains_unresolved_blocker`), specifically the test
`stripped.startswith(_BLOCKER_PREFIX) and _RESOLVED_TOKEN not in stripped`.

**Description:** A `critic-notes.md` line is treated as a *resolved* blocker if
the literal `[resolved]` token appears *anywhere* on the line. So a genuinely
live blocker such as `BLOCKER the ending still depends on the [resolved] issue
in chapter 2` is silently classified as clean, because the substring test does
not require the token to mark *this* blocker's resolution — only to occur on the
line. The developers' guide already flags the rule as "acknowledged brittle" for
prose mentions of `[resolved]`/`RESOLVED`, and the corpus pins a near-miss where
resolution is mentioned *in prose without the token*; but the inverse false-clean
case (an unresolved blocker whose text contains the token incidentally) is not
covered by a test and would cause `novel-done` to report exit `0` on a novel that
still has a live blocker — the exact "exit-0 lie" the predicate exists to
prevent.

**Proposed fix:** Tighten the resolution rule so the token must be positional —
e.g. require the stripped line to *end with* `[resolved]` (or to match a
`BLOCKER … [resolved]` anchor), so an incidental mid-line mention does not clear
the blocker — and add a corpus near-miss whose body is `BLOCKER … [resolved] …`
mid-sentence yet remains unresolved. If the loose rule is intentional for v1,
record the false-clean direction explicitly in the developers' guide beside the
existing false-dirty caveat, so both failure directions are documented.

## Finding 4 — Task 3.1.1 perpetuates the deferred-vs-top-level entry-point import split

**Category:** inconsistency · **Severity:** low

**Location:** `novel_ralph_skill/commands/stub.py:107`
(`from novel_ralph_skill.commands import _novel_done` inside `novel_done()`),
joining the existing `:132` (`_compile`) and `:155` (`_desloppify`) deferred
imports versus the module-top `build_app` import for `novel_state`.

**Description:** `audit-4.1.1.md` Finding 4 recorded that the console-script
entry points are split between a module-top import (`novel_state`) and deferred
in-body imports (`novel_compile`, `desloppify`) with no stated rule. Task 3.1.1
added a fourth entry point, `novel_done()`, following the deferred style — so the
file now reads as three deferred bodies plus one top-level, still without the
one-line rationale the prior audit asked for. The deferred imports are
load-bearing if the intent is lazy import cost, but the choice remains
undocumented.

**Proposed fix:** As `audit-4.1.1` Finding 4 proposed, add a one-line comment at
the first deferred import explaining the laziness intent (mirroring the existing
"imported inside the builder … to avoid a circular import" note in
`novel_state.build_app`), or normalize all five entry points to one style. The
four `novel_*`/`desloppify` entry-point bodies are now near-identical
`parse_global_flags → run(build_app(), residual, RunContext(...))` skeletons (see
Finding 5), so the comment should sit with whatever factoring lands there.

## Finding 5 — The four real entry points are near-identical four-flag-app + run skeletons

**Category:** similarity · **Severity:** low

**Location:** `novel_ralph_skill/commands/stub.py:72-165` (the `novel_state`,
`novel_done`, `novel_compile`, `desloppify` bodies) together with the four
`build_app()` constructors in `novel_state.py:330`, `_novel_done.py:100`,
`_compile.py:141`, and `_desloppify.py:307`.

**Description:** Two parallel duplications now stand side by side. First, every
`build_app()` opens with the identical four-flag `cyclopts.App(name=…,
result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False)` incantation — the runner's hard contract (it MUST be built
this way, per `runner.py:166`) re-spelled in four modules, so a fifth command, or
a change to the required flags, must touch every site and a mismatch is caught
only at runtime. Second, the four entry-point bodies in `stub.py` differ only in
the command name, the deferred module, and the `_NAME_FOR[...]` key; the
`parse_global_flags → run(app, residual, RunContext(command=…,
working_dir=WORKING_DIR_NAME, human=human))` shape is copied four times. Task
3.1.1 added one instance of each.

**Proposed fix:** (a) Add a small factory in the contract layer, e.g.
`make_contract_app(name)` returning the four-flag `cyclopts.App`, and have each
`build_app()` call it then register its `@app.default` body — this puts the
runner's required-flags contract in one place beside the runner that demands it.
(b) Optionally collapse the four `stub.py` entry-point bodies into one
`_drive(name, build_app)` helper that does the `parse_global_flags`/`run`
plumbing, leaving each entry point a one-liner. Both keep the per-command
specifics explicit while removing the copied boilerplate.

## Finding 6 — `_desloppify.source_chapters` still rebuilds the working dir instead of the shared accessor

**Category:** inconsistency · **Severity:** low

**Location:** `novel_ralph_skill/commands/_desloppify.py:190`
(`working_dir = pathlib.Path(WORKING_DIR_NAME)`) versus the `working_dir()`
accessor that `_novel_done.py:63` and `_compile.py:97` correctly use.

**Description:** Task 3.1.1's `_novel_done` body resolves the working root through
`working_dir()`, the `WORKING_DIR_NAME`-anchored accessor whose docstring states
it exists so callers "resolve the same cwd-relative directory rather than each
rebuilding `pathlib.Path(WORKING_DIR_NAME)`". The new code does the right thing,
which throws the older `_desloppify.source_chapters` site — which still rebuilds
`pathlib.Path(WORKING_DIR_NAME)` by hand, and additionally shadows the imported
`working_dir` *function* with a local `working_dir` *variable* — into relief as
the lone holdout. There is also a third spelling, `_working_dir()`, used by
`_recount`/`_reconcile` (noted in `audit-4.1.1` Finding 3). The accessor exists
precisely to be the single home; one site bypasses it.

**Proposed fix:** Route `_desloppify.source_chapters` through the `working_dir()`
accessor (importing it alongside the other `novel_state` seams it already
imports) and drop the local rebuild, removing both the duplicate construction and
the function-shadowing local. Track this with the `audit-4.1.1` Finding 3
decision so the three working-dir spellings converge on one.

## Finding 7 — The 3.1.1 developers'-guide diff introduced a double blank line (markdownlint MD012)

**Category:** docs-gap · **Severity:** low

**Location:** `docs/developers-guide.md:512-513` (before the new
`### Done predicate (novel-done)` heading).

**Description:** The 3.1.1 commit's developers'-guide addition prepended two
blank lines before the new `### Done predicate` heading, producing a double
blank line that fails `markdownlint` MD012/no-multiple-blanks and breaks the
repository-wide `make markdownlint` gate. The defect was introduced by the
audited task itself. Fixed in this docs-only audit pass (collapsed to a single
blank line) so the gate is green; recorded here for traceability.

**Proposed fix:** Already applied — single blank line restored. No further
action required beyond noting that the merge gate did not catch the regression,
which suggests `make markdownlint` may not have been run on the full tree before
the 3.1.1 merge.

## Documentation and test coverage

Documentation for the delivered scope is strong: the developers' guide gained a
full "Done predicate (`novel-done`)" section enumerating each clause's disk
source, the `KNITTING_PERCENTAGES` single-source rule, the manifest-vs-outline
divergence, the BLOCKER format, and the existence-only `compile_consistent`
limitation with its 3.1.2 deferral; the users' guide documents the command and
its v1 caveat. The test suite is comprehensive — per-clause unit tests, the
all-hold and per-clause-failer matrix, a working-corpus oracle, BDD, snapshot,
and console-script e2e coverage, plus the resolved-blocker and near-miss specs.

Two coverage observations, both narrow:

- The unresolved-BLOCKER substring rule's *false-clean* direction (a live
  blocker whose line incidentally contains `[resolved]`) is untested; see
  Finding 3. The existing near-miss covers only the false-dirty direction (prose
  resolution *without* the token).
- `done-conditions.md` (`skill/novel-ralph/references/`) still describes the
  reference predicate as iterating outline-parsed planned chapters, while the
  shipped predicate reads the manifest. The developers' guide records this
  divergence and flags it for "a later docs pass"; that reconciliation of the
  reference text to the manifest source remains an open documentation item rather
  than a defect.
