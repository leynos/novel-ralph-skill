# Post-merge audit — roadmap task 2.1.4

Audit of the codebase after roadmap task 2.1.4 ("Complete corpus invariant-6
coverage for scene/beat cursor sub-clauses") merged to `main` at commit
`eb26a5f`. The slice extends the §1.3.2 working corpus and its structural oracle
so all three sub-clauses of design §5.2 invariant 6 ("cursor coherence") are
exercised. Concretely it: adds the scene/beat-versus-`current_chapter`
pure-state sub-clause to both
[`validate.py`](../../novel_ralph_skill/state/validate.py)
`_check_cursor_coherent` and the oracle's
[`_oracle.py`](../../tests/working_corpus/_oracle.py) twin; adds a new
disk-evidence invariant name `cursor-plan-present`
([`_oracle.py`](../../tests/working_corpus/_oracle.py)
`_check_cursor_plan_present`) for the "zero until plans exist" clause, deferred
to reconciliation task 2.3.2; materialises `scenes.md` / `beats.md` plan files in
the corpus builder ([`_builder.py`](../../tests/working_corpus/_builder.py));
and adds negative fixtures and a property perturbation
([`_variants.py`](../../tests/working_corpus/_variants.py),
[`test_validate_state_property.py`](../../tests/test_validate_state_property.py)).

The slice is sound and discharges its goal: the pure-state
scene/beat-past-`current_chapter` clause is now enforced and pinned by both the
corpus agreement suite and the Hypothesis perturbation suite, and the
disk-evidence clause is honestly deferred to 2.3.2 rather than smuggled into the
disk-blind validator. None of the findings below is a blocking defect. The
dominant theme is *stale prose counts*: 2.1.4 grew the deferred set from four to
five names and made the cursor predicate a more substantial twin, but several
"four disk-evidence names" / "six deliberate twins" phrasings written for the
2.1.2 surface were not refreshed, so the documentation and a test docstring now
under-count what the code actually owns.

Trail followed: explored with `leta`/reads over `state/validate.py`,
`state/schema.py`, `state/parse.py`, `commands/novel_state.py`,
`contract/runner.py`, and the `tests/working_corpus/` package
(`_oracle.py`, `_variants.py`, `_specs.py`, `_library.py`, `_builder.py`) plus
the corpus and property suites; traced history with `git show eb26a5f` and
`git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §5.2/§5.4, `docs/developers-guide.md`
"Invariant validation", `skill/novel-ralph/references/state-layout.md`, prior
`docs/issues/audit-2.1.2.md`, and `AGENTS.md`. Each finding records a category,
a location, a description, a concrete proposed fix, and a severity.

## Finding 1 — Test docstring still says "four disk-evidence names" but the set is five

- Category: docs-gap
- Severity: medium
- Location:
  [`tests/test_validate_state_corpus.py`](../../tests/test_validate_state_corpus.py)
  line 222 (the `test_validator_never_emits_deferred_names` docstring) and the
  trailing comment at line 68 ("like the four §5.4 names").

Task 2.1.4 added `cursor-plan-present` to `_DEFERRED_INVARIANT_NAMES` (line 69),
making it a five-element set, and the module docstring (line 8) and the
constant's own comment (lines 64–68) were correctly updated to say "five
disk-evidence names". The `test_validator_never_emits_deferred_names` docstring,
however, still asserts in prose that "The validator emits none of the **four**
disk-evidence names on any tree." The test body iterates the full five-element
set, so the behaviour is correct; only the docstring count is stale. A reader
reconciling the docstring against the constant sees a contradiction and cannot
tell whether `cursor-plan-present` is deliberately in scope or an accident.

Proposed fix: change the line-222 docstring to "five disk-evidence names". While
there, prefer wording that names the set by reference (e.g. "none of the
`_DEFERRED_INVARIANT_NAMES`") rather than a hard-coded cardinal, so the next
addition to the deferred set cannot re-introduce the same drift.

## Finding 2 — "Six deliberate twins" under-counts and reads as fixed under 2.1.4

- Category: docs-gap
- Severity: low
- Location:
  [`docs/developers-guide.md`](../../docs/developers-guide.md) line 336
  ("Six of `validate_state`'s structural predicates are deliberate twins") and
  the mirror comment in
  [`tests/working_corpus/_oracle.py`](../../tests/working_corpus/_oracle.py)
  lines 77–89.

Both the developers' guide and the oracle's block comment describe "six
structural §5.2 predicates" as deliberate twins, enumerating
`_check_completed_prefix`, `_check_consecutive_clean_within_target`,
`_check_convergence_target_at_least_one`, `_check_consecutive_clean_within_drafted`,
`_check_cursor_coherent`, and `_check_gate_ratio_consistent`. The list omits
`_check_phase_in_enum`, which is in fact a same-named, same-logic twin present in
both `validate.py` (line 93) and `_oracle.py` (line 90) — so the genuine
same-named-twin count is seven, not six. (`_check_by_chapter_sum` is also
same-named but legitimately *not* a twin: the oracle's reads `state.toml` from
disk, so it is excluded for a real reason.) The under-count predates 2.1.4, but
2.1.4 is the slice that materially reworked `_check_cursor_coherent` into a
two-branch predicate, making the "six twins" phrasing the most load-bearing it
has ever been while remaining wrong about which six.

Proposed fix: either (a) correct both counts to "seven" and add
`_check_phase_in_enum` to the enumerated list, noting that `_check_by_chapter_sum`
is deliberately excluded because its oracle counterpart is disk-reading; or (b)
drop the cardinal entirely and describe the twins as "every same-named structural
predicate shared by `validate.py` and `_oracle.py`", which cannot drift as
predicates are added or split. Option (b) is the more durable wording.

## Finding 3 — Cursor-coherence "bounded" branch has no pure-state property perturbation

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_validate_state_property.py`](../../tests/test_validate_state_property.py)
  (`_perturb_cursor_past_current_chapter`, lines 235–245, and the
  `_PERTURBATIONS` table, lines 248–253).

`_check_cursor_coherent` now decides on two independent branches: the `bounded`
check (`0 <= current_chapter <= len(chapters)` and non-negative scene/beat) and
the `scene_beat_past_chapter` check (`current_chapter == 0` with a non-zero
scene/beat). The property suite's `_perturb_cursor_past_current_chapter` exercises
only the second branch — it sets `current_chapter=0, current_scene=1`. The first
branch (a `current_chapter` strictly greater than `len(chapters)`, or a negative
scene/beat) is covered only by the single corpus fixture
`cursor-past-current-chapter` in `_variants.py` (a fixed `len+5`), never by a
generated perturbation over arbitrary coherent states. A regression that loosened
the upper bound (e.g. dropping the `<= len(chapters)` clause) would slip past the
generated suite and rely solely on the one hand-built example.

Proposed fix: add a second perturbation, e.g.
`_perturb_cursor_past_manifest`, that sets `current_chapter = len(chapters) + 1`
on a coherent state (leaving scene/beat at zero so only the `bounded` branch
fires), keyed to `CURSOR_COHERENT` in a parallel single-name assertion. Because
two `CURSOR_COHERENT` perturbations cannot share one key in `_PERTURBATIONS`,
add it as a standalone example-based test mirroring
`test_consecutive_clean_over_chapters_drafted_rejected`, asserting the verdict is
exactly `{CURSOR_COHERENT}`.

## Finding 4 — `_check_cursor_plan_present` double-negative return is hard to read

- Category: ergonomics
- Severity: low
- Location:
  [`tests/working_corpus/_oracle.py`](../../tests/working_corpus/_oracle.py)
  lines 265–267.

The new disk-evidence predicate ends with
`return not (spec.current_beat > 0 and not (chapter_dir / "beats.md").exists())`.
The nested `not ( … and not … )` is a triple negation a reader must unfold to
confirm it means "a non-zero beat cursor requires `beats.md`". The sibling scene
clause directly above is written in the clearer early-return form
(`if scene > 0 and not exists: return False`), so the two halves of the same
rule are expressed in two different idioms within five lines.

Proposed fix: mirror the scene clause's shape for the beat clause —
`if spec.current_beat > 0 and not (chapter_dir / "beats.md").exists(): return
False` followed by `return True`. This makes both sub-clauses read identically
("non-zero cursor without its plan file fails") and removes the double negative.

## Finding 5 — `_inline(dict(by_chapter))` re-copies an already-`dict` mapping

- Category: ergonomics
- Severity: low
- Location:
  [`tests/working_corpus/_builder.py`](../../tests/working_corpus/_builder.py)
  line 103 (`_word_counts_table`).

`derive_by_chapter(spec)` always returns a fresh `dict[str, int]` (its
[`_specs.py`](../../tests/working_corpus/_specs.py) body builds a new dict in
both branches). `_word_counts_table` binds that to `by_chapter` and then calls
`_inline(dict(by_chapter))`, re-wrapping the already-`dict` value in a second
`dict(...)` copy. The defensive copy guards nothing here because the source is
not shared, and the inner `_inline` helper already calls `table.update(pairs)`
which copies the pairs into the inline table regardless. The same pattern is
benign elsewhere but here it is pure redundancy.

Proposed fix: pass `_inline(by_chapter)` directly. `derive_by_chapter` already
owns the "return a fresh mapping" guarantee, so the extra `dict(...)` adds only
a throwaway allocation and a moment's doubt about whether aliasing matters.

## Summary

The 2.1.4 slice correctly closes the design §5.2 invariant-6 coverage gap: the
pure-state scene/beat-past-`current_chapter` clause is enforced and twin-pinned,
and the disk-evidence "zero until plans exist" clause is honestly deferred to
task 2.3.2 without breaching the disk-blind validator boundary. The findings are
all low-to-medium polish. The two documentation findings (a stale "four" in a
test docstring, an under-counted and now load-bearing "six twins" claim) are the
ones worth fixing promptly, since they misdescribe a surface 2.1.4 just enlarged;
the remaining three are small ergonomic and coverage tidy-ups. No finding blocks
the slice or threatens the §5.2 contract.
