# Post-merge audit — roadmap task 7.3.3 (draft-read guard consolidation)

Audit of the codebase after roadmap task 7.3.3 ("Consolidate the draft-read
state-error wrapper shared by the drafting commands") merged to `main` at commit
`1016fbd`. The slice homes the
`try`/`except STATE_INPUT_ERRORS → _draft_read_error` shell in a new
[`draft_read_guard`](../../novel_ralph_skill/commands/state_sourcing.py) context
manager in `state_sourcing`, then routes three drafting commands —
[`_wordcount`](../../novel_ralph_skill/commands/_wordcount.py),
[`_recount`](../../novel_ralph_skill/commands/_recount.py), and
[`_desloppify`](../../novel_ralph_skill/commands/_desloppify.py) — through that
single guard, retiring their per-command copies of the idiom. It adds a
structural anti-drift test
([`tests/test_draft_read_guard_home.py`](../../tests/test_draft_read_guard_home.py))
and a behavioural unit test
([`tests/test_draft_read_guard_unit.py`](../../tests/test_draft_read_guard_unit.py)),
and documents the consolidated seam in the developers' guide.

The slice is sound and discharges its named success criterion: the three
roadmap-named commands delegate their draft read to one shared guard, the guard
chains the caught exception via `from` so the `messages` channel carries only
prose, and an AST-level structural test pins the single home so those three
modules cannot silently re-fork the shell. The guard's docstrings are
exemplary, and the behavioural unit test exercises both the re-raise arm and the
pass-through (out-of-tuple) arm.

The findings below are deferred-consolidation and consistency tidy-ups. The
most material is that four further draft-read boundaries still open-code the
exact shell the guard was built to home, and the documentation, guard docstring,
and structural test disagree on how many such boundaries remain. None is a
blocking defect; the guard itself is correct and the deferral is acknowledged in
the design, so this is fix-debt rather than a regression.

This audit reviews the merged state at `origin/main` (commit `1016fbd`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. The trail: design §3.2 (draft-read fault → exit 3), ADR 003 (shared
interface contract), the execplan
[`docs/execplans/roadmap-7-3-3.md`](../execplans/roadmap-7-3-3.md), the
Logisphere review
[`docs/execplans/roadmap-7-3-3.logisphere-review-r1.md`](../execplans/roadmap-7-3-3.logisphere-review-r1.md),
`docs/developers-guide.md`, and `AGENTS.md` (the "Duplicated code" heuristic).
Navigation used `leta` and history used `sem`.

## Finding 1 — Four draft-read boundaries still open-code the guard shell

- Category: duplication
- Severity: medium
- Location:
  [`_compile.py:144`](../../novel_ralph_skill/commands/_compile.py) and
  [`_compile.py:223`](../../novel_ralph_skill/commands/_compile.py),
  [`_novel_done.py:96`](../../novel_ralph_skill/commands/_novel_done.py), and
  [`novel_state.py:147`](../../novel_ralph_skill/commands/novel_state.py)
  (`_disk_evidence_or_state_error`).

The slice built `draft_read_guard` to be the single home for the
`try`/`except STATE_INPUT_ERRORS → raise _draft_read_error(dir) from exc` shell,
but routed only the three roadmap-named commands through it. Four further
draft-read boundaries still open-code the identical shell, each importing both
`STATE_INPUT_ERRORS` and the underscore-private `_draft_read_error` and
re-spelling the wrapper by hand:

- `_compile.py:144` wraps `present_draft_bodies(state, root)` and raises
  `_draft_read_error(root)`;
- `_compile.py:223` wraps `compiled_matches_drafts(state, working_dir())` and
  raises `_draft_read_error(working_dir())`;
- `_novel_done.py:96` wraps `evaluate_done(state, root)` and raises
  `_draft_read_error(root)`;
- `novel_state.py:147` (`_disk_evidence_or_state_error`) wraps
  `check_disk_evidence(...)` and raises `_draft_read_error(working_dir)`.

Each is structurally identical to `draft_read_guard`'s body: a single wrapped
read, one `reported_dir`, and the same re-raise. (The unrelated *write*-fault
tail at `_compile.py:149`, which routes through `_compile_write_error`, is
deliberately out of scope and should stay as it is.) Leaving these four
open-coded is precisely the duplication AGENTS.md's "Duplicated code" heuristic
flags, and the guard's own docstring names them as boundaries it is meant to
serve, so the consolidation is structurally incomplete.

Proposed fix: in a follow-up slice, replace each of the four open-coded handlers
with `with draft_read_guard(<reported_dir>): …` (passing `root` /
`working_dir()` / `working_dir` exactly as today), drop the now-unused
`_draft_read_error` and `STATE_INPUT_ERRORS` imports from those modules, and
extend `_MIGRATED_MODULES` in `tests/test_draft_read_guard_home.py` to cover
`_compile.py`, `_novel_done.py`, and `novel_state.py` so the anti-drift test
holds the full set. Keep `_draft_read_error` importable for the parity tests
that assert on its message. This should be proposed as a roadmap item rather
than folded in here (this is a read-only audit step).

## Finding 2 — Remaining-boundary count is inconsistent across docstring, guide, and test

- Category: inconsistency
- Severity: medium
- Location:
  [`state_sourcing.py:181`](../../novel_ralph_skill/commands/state_sourcing.py)
  (`_draft_read_error` docstring),
  [`docs/developers-guide.md:663`](../developers-guide.md), and
  [`tests/test_draft_read_guard_home.py`](../../tests/test_draft_read_guard_home.py)
  (module docstring, lines 23-26, and the `_MIGRATED_MODULES` comment, lines
  44-48).

Three sources disagree on how many draft-read boundaries remain open-coded after
the slice. The developers' guide (line 663) says "The three remaining draft-read
boundaries (`novel done` and both of `novel compile`'s tails)…", and the
structural test docstring likewise names only `_novel_done` and `_compile`'s two
tails. Both omit `novel_state.py`'s `_disk_evidence_or_state_error`, which is a
genuine fourth open-coded boundary (its own docstring even claims it wraps the
reader "exactly as the `recount` mutator wraps the same reader" — but `recount`
now delegates to the guard while this one still does not). Separately,
`_draft_read_error`'s docstring asserts the formatter serves "the six draft-read
boundaries" and then enumerates seven sites (`_disk_evidence_or_state_error`,
`_recount`, `_wordcount`, `_novel_done`, `_desloppify.source_chapters`, and
"`_compile`'s two tails"). The "six" figure predates the guard and no longer
matches the enumeration.

Proposed fix: settle on the true inventory — three guarded boundaries
(`_wordcount`, `_recount`, `_desloppify`) and four open-coded boundaries
(`_compile` ×2, `_novel_done`, `novel_state._disk_evidence_or_state_error`) — and
make all three texts agree. Update the developers' guide to say "four remaining"
and name `novel state check`'s disk-evidence boundary; correct the
`_draft_read_error` docstring's "six" to the actual count and reconcile its
enumeration; and update the `test_draft_read_guard_home.py` docstring/comment to
list all four excluded sites. If Finding 1 is actioned, these texts collapse to
"all boundaries are guarded" instead.

## Finding 3 — `_draft_read_error` cross-references the wrong roadmap section

- Category: docs-gap
- Severity: low
- Location:
  [`state_sourcing.py:181`](../../novel_ralph_skill/commands/state_sourcing.py)
  (`_draft_read_error` docstring) and the four open-coded call-site comments in
  `_compile.py`, `_novel_done.py`, and `novel_state.py`.

`_draft_read_error`'s docstring and the open-coded call-site comments attribute
the shared-formatter consolidation to "roadmap §6.3.5", while the guard that now
owns the shell is attributed to "roadmap §7.3.3". The formatter and the guard
are two halves of one seam (the docstrings themselves say so: the formatter owns
*what* the message says, the guard owns *which* faults route to exit 3), yet a
reader following the §6.3.5 reference will not find the guard consolidation that
§7.3.3 delivered. The mixed references make the seam's provenance harder to
trace.

Proposed fix: when the texts are next touched (e.g. under Finding 1 or 2), add a
"see also §7.3.3 / `draft_read_guard`" cross-reference to `_draft_read_error`'s
docstring so the formatter and guard halves point at each other, and ensure the
surviving open-coded call-site comments name both the formatter (§6.3.5) and the
guard (§7.3.3) seam.

## Finding 4 — Stale audit file for a different task occupied this filename

- Category: inconsistency
- Severity: low
- Location: [`docs/issues/audit-7.3.3.md`](audit-7.3.3.md) (this file's prior
  content at commit `9b2ba4d`).

Before this audit, `docs/issues/audit-7.3.3.md` held the post-merge audit for a
*different* task — "Extend the direct-edit guard to every skill-recipe
reference" at commit `b28eaad` — because the roadmap was renumbered/rerouted and
the `7.3.3` slot was reassigned to the draft-read guard consolidation. A reader
opening `audit-7.3.3.md` before this overwrite would have read an audit whose
subject did not match commit `1016fbd`'s "Consolidate the draft-read
state-error wrapper" title. The collision is a symptom of audit filenames being
keyed solely on the roadmap number, which is not stable across reroutes.

Proposed fix: this audit overwrites the stale content, resolving the immediate
collision. To prevent recurrence, consider keying post-merge audit filenames on
the merge commit SHA (or appending it), e.g. `audit-7.3.3-1016fbd.md`, so a
renumbering reroute cannot silently shadow an earlier audit. This is a
process/tooling suggestion for the root agent, not a code change.
