# Done conditions

The Ralph Loop terminates when the agent truthfully reports done. "Truthfully"
is the operative word. The agent must not declare completion on the strength of
feeling, fatigue, or context exhaustion. Completion is a verifiable property of
files on disk.

This reference defines the done predicate at three scales:

1. Phase-level done conditions (exit criteria for each phase)
2. Chapter-level done conditions (the inner loop's exit)
3. Novel-level done predicate (the terminator)

## How to evaluate

Every turn, after the entry routine but before doing new work, evaluate the
novel-level predicate. If it passes, write a final log entry and stop.
Otherwise proceed.

```python
# Pseudocode for the predicate check
def novel_is_done(working_dir):
    state = read_state_toml(working_dir)
    if state["phase"]["current"] != "done":
        return False
    return novel_predicate(working_dir, state)
```

Phase advancement past `final-pass` to `done` happens exactly once, at the end
of Phase 9. Until then, the predicate is false.

## Phase-level exit criteria

The agent must not advance `phase.current` until the exit criteria for the
current phase are satisfied.

### Phase 0 — Premise

- `working/premise.md` exists.
- File contains a logline section (≤30 words, single sentence).
- File contains a one-paragraph premise (~150 words).

### Phase 1 — Treatment

- `working/treatment.md` exists.
- All four act sections present.
- Ending section names a final image, surviving characters, and
  what has changed.
- Themes section names 2–4 themes.

### Phase 2 — Characters

- `working/characters/_index.md` exists.
- For every character named in the treatment with a speaking role
  in more than one scene, `working/characters/<slug>.md` exists.
- Each character file has all eleven sections (name/age/role,
  motivations, goals, challenges, limitations, flaws, ambitions, quirks,
  premise-applicable traits, voice notes, attractor).
- `working/characters/relationships.md` exists and is connected
  (no character file is isolated from the graph).

### Phase 3 — Conflict & attractor analysis

- `working/plan/conflict-map.md` exists.
- Every character with an entry in `characters/` has an
  attractor named on the map.
- Every named conflict in the treatment has at least one
  attractor pair behind it.

### Phase 4 — Setting

- `working/world/setting.md` exists.
- `geography.md`, `politics.md`, `pressure-dynamics.md`,
  `physicalities.md` all exist.
- Every named location in `treatment.md` is covered in
  `geography.md`.
- Every named faction or institution in `treatment.md` is
  covered in `politics.md`.

### Phase 5 — Reader fit

- `working/reader/audience.md` exists.
- File contains: reader profile, JTBD in one sentence,
  opportunity space, three to five comps with publishers and years.
- `working/reader/comps.md` exists with anti-comps section.

### Phase 6 — Save the Cat

- `working/plan/genre-stc.md` exists.
- Selected genre named (one of the ten).
- All fifteen beats populated with target word count and
  description.
- Beat-to-treatment crosswalk has no orphans.

### Phase 7 — Chapter planning

- `working/plan/chapter-outline.md` exists.
- Every STC beat is served by at least one chapter.
- Every chapter has all required fields: number, title (working),
  POV, setting, premise, characters, conflict, outcome, beat assignment, target
  word count.
- Sum of chapter word count targets is within ±10% of
  `novel.target_word_count`.

### Phase 8 — Drafting

This phase is done when:

- Every chapter from the outline has a `done.flag`.
- All three knitting circle gates are true.
- No chapter's `critic-notes.md` has unresolved BLOCKER findings.
- `working/manuscript/compiled.md` exists and equals the
  concatenation of all chapter `draft.md` files.

### Phase 9 — Final pass

- One full-novel desloppify pass logged.
- One full-novel spiteful critic pass logged.
- Final image verification logged.
- `state.gates.final.final_pass_complete = true`.

After Phase 9 completes, `state.phase.current` advances to `done`.

## Chapter-level done conditions

A chapter is done when all of:

- `working/manuscript/chapter-NN/scenes.md` exists.
- `working/manuscript/chapter-NN/beats.md` exists.
- `working/manuscript/chapter-NN/draft.md` exists and is
  non-empty.
- Desloppification has been run against the latest draft
  (logged).
- The spiteful critic loop has either converged (a pass with no
  BLOCKER and no MAJOR) or hit the pass cap of 4, and all BLOCKER/MAJOR
  findings have been addressed.
- The fangirl pass has run and produced
  `working/manuscript/chapter-NN/fangirl-notes.md`.
- Fangirl outputs have been folded into
  `working/fangirl-running.md` (where applicable).
- `working/manuscript/chapter-NN/done.flag` is touched.

## Novel-level predicate

The terminator. The agent declares done only when this evaluates true on disk.

```python
def novel_predicate(working_dir, state):
    # 1. State machine reports done.
    if state["phase"]["current"] != "done":
        return False
    if not state["gates"]["final"]["final_pass_complete"]:
        return False

    # 2. Every planned chapter is drafted.
    planned = parse_chapter_outline(working_dir / "plan/chapter-outline.md")
    for chapter_id in planned:
        flag = working_dir / f"manuscript/chapter-{chapter_id}/done.flag"
        if not flag.exists():
            return False

    # 3. All three knitting passes ran.
    for pct in (30, 50, 80):
        review = working_dir / f"reviews/knitting-{pct}.md"
        if not review.exists():
            return False
        if not state["gates"]["knitting"][f"done_{pct}"]:
            return False

    # 4. compiled.md exists and is consistent with chapter drafts.
    compiled = working_dir / "manuscript/compiled.md"
    if not compiled.exists():
        return False
    if compiled_diverges_from_chapter_drafts(working_dir):
        return False

    # 5. No outstanding BLOCKER findings.
    for chapter_id in planned:
        notes = working_dir / f"manuscript/chapter-{chapter_id}/critic-notes.md"
        if notes.exists() and contains_unresolved_blocker(notes):
            return False

    return True
```

If any check fails, the agent identifies which one and acts on it. If all
checks pass, the agent writes one final log entry:

```markdown
## <timestamp> — turn <N> — DONE

Novel "<title>" complete.
- <X> chapters, <Y> words total.
- Spiteful critic clean: <Z> chapters converged in <K> passes
  median, <M> chapters hit the cap.
- Knitting circle passes at 30%, 50%, 80% integrated.
- Final pass complete.

Manuscript: working/manuscript/compiled.md
```

And stops.

## Failure modes for the predicate

- **State says done but chapter draft is empty.** State is lying.
  Recovery: reset `phase.current` and reconstruct. The state-layout reference
  covers this.
- **`done.flag` exists but `critic-notes.md` shows unresolved
  BLOCKER.** The flag was touched prematurely. Recovery: untouch the flag,
  return to that chapter's critic loop.
- **`compiled.md` is stale.** Regenerate from chapter drafts
  before continuing.
- **Phase 9 declares complete without actually running.** Check
  the log. The phase must have logged each step (desloppify, spiteful, image
  verification).

## Anti-patterns

- **Declaring done because the context is full.** Context
  exhaustion is not completion. Truncate, summarise, and continue.
- **Declaring done because no more changes are obvious.** The
  predicate is structural, not aesthetic. Run it.
- **Declaring done with knitting-80 unresolved because "the book
  is good enough."** The knitting pass exists precisely to contest that
  judgement. Run it.
- **Skipping the final pass because individual chapters were
  clean.** Novel-scale failures (overused phrases across chapters, sagging
  structural arc, ending drift from treatment) are invisible at chapter scale.
  The final pass is mandatory.
