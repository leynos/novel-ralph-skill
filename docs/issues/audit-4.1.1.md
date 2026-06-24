# Post-merge audit — roadmap task 4.1.1

Audit of the codebase after task 4.1.1 ("Implement `novel-compile` ordered by
zero-padded chapter index") merged to `main` at commit `9c02abb`. The task added
the `novel-compile` write path: it concatenates the chapter drafts in ascending
`[chapters]`-manifest order, joined by the single production separator, and
writes `working/manuscript/compiled.md` atomically through the shared
`write_text_atomically` text writer. It reuses the one production join rule
(`concatenate_drafts` over `present_draft_bodies`) the `compiled-matches-drafts`
§5.4 disk-evidence invariant recomputes, so a freshly compiled tree is coherent
under `novel-state check` by construction. It refuses an absent or empty manifest
(and every other state/read fault) with exit `3` and writes nothing, opens no
`[pending_turn]` bracket (one `Path.replace`), and carries write-shaped success
vocabulary (no `violations`). The slice ships unit, BDD, snapshot, and e2e
coverage plus developers'- and users'-guide updates.

The implementation is of a high standard: docstrings are exhaustive and
design-cited, the read/join rules are genuinely single-homed and shared with the
detector, the exit-`3` channel discipline mirrors `_recount`, and the test suite
pins ordering, idempotence, the round-trip-oracle agreement with the §5.4
invariant, and every refusal path. The findings below are refinement
opportunities, not defects; none blocks the merge.

Trail followed: `docs/novel-ralph-harness-design.md` §§4.1/4.2/4.3/5.4,
`docs/developers-guide.md` (command surface, write discipline),
`docs/users-guide.md`, `docs/roadmap.md` tasks 4.1.1/4.1.2/3.1.2,
`docs/execplans/roadmap-4-1-1.md` (Decision Log D-PT, D-READ, D-RESULT, D-SCOPE,
D-WRITER, D-CWD), `docs/adr-001`/`adr-002`/`adr-005`, `AGENTS.md` (quality gates,
the 400-line cap, CQS, en-GB Oxford spelling), the `python-router` skill (routed
to data-shapes and errors-and-logging), and `leta`/`sem` for navigation and
history. Files inspected: `novel_ralph_skill/commands/_compile.py`,
`novel_ralph_skill/commands/_recount.py`,
`novel_ralph_skill/commands/novel_state.py`,
`novel_ralph_skill/commands/_state_mutators.py`,
`novel_ralph_skill/commands/stub.py`,
`novel_ralph_skill/state/compile_model.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/document.py`, `novel_ralph_skill/state/wordcount.py`,
`novel_ralph_skill/state/_disk_paths.py`,
`tests/test_compile_unit.py`, `tests/test_compile_e2e.py`,
`tests/features/compile.feature`, `tests/steps/compile_steps.py`.

## Finding 1 — Ad-hoc `working/manuscript/<file>` path construction is scattered

**Category:** duplication · **Severity:** medium

**Location:** `novel_ralph_skill/commands/_compile.py:104`
(`root / "manuscript" / "compiled.md"`),
`novel_ralph_skill/state/disk_evidence.py:147,179,225`,
`novel_ralph_skill/state/compile_model.py:75`,
`novel_ralph_skill/state/wordcount.py:75`,
`novel_ralph_skill/commands/_desloppify.py:109`,
`novel_ralph_skill/state/_disk_paths.py:32`.

**Description:** The `"manuscript"` directory segment and the `compiled.md` /
`chapter-NN/draft.md` leaf paths are rebuilt by hand in at least seven places.
There is already a single-homed `_chapter_dir_name` helper for the
`chapter-NN/` segment, but no equivalent accessor for the `manuscript/`
directory or the `compiled.md` path. Task 4.1.1 added two more instances
(`_compile.py` and the `present_draft_bodies` read in `compile_model.py`). The
literal `"manuscript"` and `"compiled.md"` are the de-facto contract between the
write path and the `compiled-matches-drafts` detector; today that contract is
enforced only by the round-trip-oracle test, not by a shared accessor. A
rename or relocation would require touching every site, and a missed site would
silently diverge.

**Proposed fix:** Add `manuscript_dir(working_dir)` and
`compiled_path(working_dir)` accessors beside `_chapter_dir_name` in
`state/_disk_paths.py` (the existing home of disk-path helpers), and route
`_compile.py`, `disk_evidence.py`, `compile_model.py`, and `wordcount.py`
through them. This makes the write/detector path contract a code-level
single source of truth rather than a test-only invariant.

## Finding 2 — `_COMPILED_REL` string and the write path are constructed independently

**Category:** cqs · **Severity:** low

**Location:** `novel_ralph_skill/commands/_compile.py:52` (`_COMPILED_REL =
"working/manuscript/compiled.md"`) versus `:104` (`compiled_path = root /
"manuscript" / "compiled.md"`).

**Description:** The envelope/result/message advertise the written file via the
hand-written string constant `_COMPILED_REL`, while the file actually written is
built from `working_dir()` (the `WORKING_DIR_NAME`-anchored accessor) plus
`"manuscript" / "compiled.md"`. The two encode the same path through two
independent spellings. If `WORKING_DIR_NAME` ever changed from `"working"`, the
result envelope would still report `working/...` while writing elsewhere — the
envelope would lie. The docstring justifies the literal as the deterministic
snapshot token, which is sound, but the literal need not be authored
independently of the write path.

**Proposed fix:** Derive `_COMPILED_REL` from `WORKING_DIR_NAME` and the shared
`compiled_path` accessor proposed in Finding 1 (e.g. render the working-relative
token from the same segments the write uses), so the advertised path and the
written path cannot drift. A test pinning the rendered token to
`working/manuscript/compiled.md` keeps the snapshot deterministic.

## Finding 3 — `novel-compile` resolves its load boundary through a different import surface than its mutator siblings

**Category:** inconsistency · **Severity:** low

**Location:** `novel_ralph_skill/commands/_compile.py:34-39` imports
`state_path`, `working_dir`, `_load_or_state_error` from
`novel_ralph_skill.commands.novel_state`; the sibling mutators
`_recount.py:25-31` and `_reconcile.py` import the underscore-aliased
re-exports `_state_path`, `_working_dir`, `_load_document_or_state_error` from
`novel_ralph_skill.commands._state_mutators`.

**Description:** `_state_mutators` re-exports `state_path as _state_path` and
`working_dir as _working_dir` (declared in `__all__`) precisely so the
load/refuse boundary has one canonical import home for the mutator family;
`_recount` and `_reconcile` follow that convention. `novel-compile` is a mutator
too (its own docstring calls it "a deterministic *mutator*"), but it reaches past
that surface and imports the public names directly from `novel_state`. Both
resolve to the same functions, so there is no behavioural bug — but a reader
comparing the three mutator bodies sees two different import provenances for the
same boundary, which erodes the "every mutator routes through one shared
contract" story the `_state_mutators` re-export was created to tell.

**Proposed fix:** Decide one convention and apply it. Either route
`novel-compile` through `_state_mutators` like its siblings, or (cleaner, since
`novel-compile` loads a typed `State` rather than a `tomlkit` document and so
does not need the document-shaped `_load_document_or_state_error`) document in
`_compile.py` why it imports the typed-load boundary directly from `novel_state`
while the document mutators go via `_state_mutators`. A one-line "why" comment
removes the apparent inconsistency.

## Finding 4 — Console-script entry points are split between top-level and deferred imports without a stated rule

**Category:** ergonomics · **Severity:** low

**Location:** `novel_ralph_skill/commands/stub.py:20` (`from
novel_ralph_skill.commands.novel_state import ... build_app` at module top) versus
`:113` (`from novel_ralph_skill.commands import _compile` inside
`novel_compile`) and `:136` (`from novel_ralph_skill.commands import
_desloppify` inside `desloppify`).

**Description:** `novel_state` imports its `build_app` at module top, while
`novel_compile` and `desloppify` defer their command-module imports into the
function body. The deferred imports plausibly exist to keep each console-script's
import cost lazy (and `novel_state`'s `build_app` is needed at top only because
`WORKING_DIR_NAME` is co-imported from the same module), but the rationale is
unstated, so the file reads as two inconsistent styles for the same job.

**Proposed fix:** Add a one-line comment at the first deferred import explaining
the laziness intent (mirroring the existing "imported inside the builder … to
avoid a circular import" comment in `novel_state.build_app`), or normalise all
five entry points to one import style. Either makes the choice deliberate rather
than accidental.

## Finding 5 — `_check_done_flag_without_draft` re-reads `draft.md` inline instead of via the shared read rule

**Category:** similarity · **Severity:** low

**Location:** `novel_ralph_skill/state/disk_evidence.py:152-155`
(`draft.read_text(encoding="utf-8").split()` per chapter) versus the shared
`present_draft_bodies` read rule in
`novel_ralph_skill/state/compile_model.py:38-80`.

**Description:** `_check_done_flag_without_draft` opens and decodes each
chapter's `draft.md` with its own inline `read_text` + `split` to decide whether
the draft is empty, duplicating the "read a chapter draft as UTF-8, absent means
empty" rule that `present_draft_bodies` and `recount_words` already own. The
predicate genuinely needs only the per-chapter token count, and it must remain
total over a malformed tree, so this is a soft overlap rather than a clean
extraction — but three sites now encode the same chapter-draft read boundary
with subtly different fault handling (this one treats absent as `0` inline; the
compile/recount rule centralises it).

**Proposed fix:** Consider routing the done-flag emptiness check through the same
per-chapter draft reader the compile and recount paths use (e.g. a shared
"draft token count for chapter N" helper that both `recount_words` and this
predicate call), so the "what is an empty draft, and how is an absent one
handled" rule lives in exactly one place. If the totality and per-chapter-early-
exit requirements make extraction awkward, document the overlap instead.

## Documentation and test coverage

No documentation gap was found for the delivered scope: the developers' guide and
users' guide were updated accurately and scope the `--check` flag and the
compile-and-hash routine to tasks 4.1.2 and 3.1.2. The empty-body separator
behaviour (an absent draft contributes `""`, so two adjacent absent drafts yield
a bare `"\n\n"` and a trailing draft yields a trailing separator) is coherent by
construction with the §5.4 detector and is pinned by
`test_compile_absent_draft_contributes_empty_string`, but it is not described in
prose. If a future reader is surprised by trailing/blank separators in
`compiled.md`, a one-sentence note in the users' guide that the separator is
applied between *all* manifest chapters including undrafted ones would close the
gap. This is the only test-adjacent observation; behavioural and unit coverage
of the write path is otherwise complete (ordering, idempotence, the round-trip
oracle, and every refusal channel).
