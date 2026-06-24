# Post-merge audit — roadmap task 6.2.3

Audit of the codebase after roadmap task 6.2.3 ("Correct documented skill
defects and point prose at commands") merged to `main` at commit `c92aeef`. The
slice completes the design §8 skill-defect remediation: it reduces both prose
copies of the done predicate — the short form in
[`SKILL.md`](../../skill/novel-ralph/SKILL.md) and the long-form pseudocode in
[`done-conditions.md`](../../skill/novel-ralph/references/done-conditions.md) —
to a pointer at the `novel-done` command and the developers' guide clause table,
and reconciles the §8 defect record in
[`novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md) to
on-disk reality (the phase mislabel and the dead `plan.md` entry were already
closed by commit `916313c`).

The slice is sound and of a high standard. It removes the duplicated
`novel_predicate` pseudocode that could drift from
[`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py), routes
the agent at the executable command rather than a hand-kept clause list, and the
cross-references between `SKILL.md`, `done-conditions.md`, and the developers'
guide all resolve. The en-GB Oxford-spelling convention holds throughout the new
prose.

The findings below are minor. None is a defect in the 6.2.3 diff; they are small
residual documentation, test-coverage, and code-duplication gaps in and around
the consolidated predicate that are cheap to close now that the prose is settled.

## Finding 1 — no guard test stops the prose from re-restating the predicate

- Category: test-gap
- Severity: medium
- Location: `tests/` (no covering test); the unguarded prose is
  [`SKILL.md`](../../skill/novel-ralph/SKILL.md) "Done predicate (short form)"
  and
  [`done-conditions.md`](../../skill/novel-ralph/references/done-conditions.md)
  "Novel-level predicate".

The whole point of 6.2.3 is that the two prose copies stop restating the
predicate and instead point at `novel-done`. That consolidation is unguarded.
The repository already establishes the pattern of pinning a prose-consolidation
invariant with a fence-scanning test —
[`tests/test_state_layout_reference.py`](../../tests/test_state_layout_reference.py)
forbids any direct `state.toml`-write recipe re-appearing in
`state-layout.md` — but no equivalent guard exists for the done predicate. A
future edit could silently re-introduce a `def novel_predicate(...)` pseudocode
block or a hand-numbered clause list in either file, re-opening the exact
two-source drift §8 records as closed, and nothing would fail.

Proposed fix: add a test (mirroring `test_state_layout_reference.py`'s structure
and reusing the `read_repo_text` conftest fixture) that asserts, against
`SKILL.md` and `done-conditions.md`, (a) no executable code fence in either file
defines `novel_predicate`/`novel_is_done` or re-implements the clause loop, and
(b) each file still contains the literal `novel-done` pointer. Keep the scanner
pure (extract it like `tests/_state_layout_scanner.py`) so the guard reads
markdown text without importing the package.

## Finding 2 — developers' guide clause table lists the six clauses out of canonical §4.2 order

- Category: inconsistency (docs vs code)
- Severity: low
- Location:
  [`docs/developers-guide.md`](../../docs/developers-guide.md) lines 569-581,
  "Done predicate (`novel-done`)", "The six clauses and their disk sources".

The 6.2.3 diff makes this table the *authoritative* statement of the clause
truth conditions ("This table is the authoritative statement … the skill prose
… now points here"). The canonical §4.2 order — fixed by the design JSON
([`novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
lines 354-359), preserved by `DoneClauses` field order in
[`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py) (lines
94-99), and the order `failed_clause_names` reports in — is `phase_is_done`,
`final_pass_complete`, `all_chapters_flagged`, `knitting_gates_passed`,
`compile_consistent`, `no_unresolved_blockers`. The guide's bullet list instead
places `no_unresolved_blockers` *before* `compile_consistent`. An authoritative
table that disagrees with the canonical clause order it claims to anchor is a
small but real inconsistency, and it reads oddly next to the guide's own prose,
which then discusses the BLOCKER format before `compile_consistent`.

Proposed fix: swap the last two bullets so the table runs in §4.2 order
(`compile_consistent` then `no_unresolved_blockers`), matching the design JSON,
the `DoneClauses` field order, and the order operators see in `messages`.

## Finding 3 — the `manuscript/compiled.md` path is rebuilt inline at four sites

- Category: duplication
- Severity: low
- Location:
  [`_compile.py`](../../novel_ralph_skill/commands/_compile.py) line 144,
  [`_novel_done.py`](../../novel_ralph_skill/commands/_novel_done.py) lines 126
  and 171, and
  [`compile_model.py`](../../novel_ralph_skill/state/compile_model.py) line 105.

The literal join `root / "manuscript" / "compiled.md"` is open-coded at four
call sites across three modules. The codebase already centralises the sibling
`chapter-NN` path idiom in
[`_disk_paths.py`](../../novel_ralph_skill/state/_disk_paths.py)
(`_chapter_dir_name`) precisely so the `manuscript/chapter-NN/` layout has one
definition; the `compiled.md` path has no such helper, so a future relayout of
`manuscript/` is shotgun surgery across three modules, and the existence stat in
`_novel_done._failed_clause_message` and `_novel_done._sole_stale_compile` can
silently diverge from the path `compile_model.compiled_matches_drafts` actually
reads.

Proposed fix: add a `_compiled_path(working_dir: Path) -> Path` helper beside
`_chapter_dir_name` in `_disk_paths.py` (or a `MANUSCRIPT_DIRNAME` constant plus
the helper) and route all four sites through it, so the `manuscript/compiled.md`
layout, like `chapter-NN`, has a single definition both the writer
(`novel-compile`) and the readers (`novel-done`, the §5.4 detector) share.

## Finding 4 — design §8 retains future-tense "roadmap task 6.2.3 reduces …" after the task merged

- Category: docs-gap
- Severity: low
- Location:
  [`novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
  §8 "Skill defects the rebuild corrects", the "Two-source done predicate"
  bullet (around line 786).

The 6.2.3 diff rewrote the phase-mislabel and dead-`plan.md` bullets to the past
tense ("Already corrected … landed in commit `916313c`") now that those defects
are closed, but the "Two-source done predicate" bullet — the very defect this
task closes — still reads in the future tense: "`novel-done` is the single
source of truth; roadmap task 6.2.3 reduces both prose copies to a pointer …".
Since 6.2.3 has merged, the section no longer truthfully records "how each
defect was closed" for this third defect: it describes the fix as still pending.

Proposed fix: rewrite the bullet to the past tense in line with its two
siblings, e.g. "`novel-done` is the single source of truth; roadmap task 6.2.3
reduced both prose copies to a pointer at the command and the developers' guide
clause table." This keeps the §8 record internally consistent (all three defects
described as closed) and matches the consolidation the skill files now carry.
