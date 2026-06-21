---
name: novel-ralph
description: >
  Write a complete novel under a Ralph Loop harness. Use this skill whenever
  the user asks to draft, plan, outline, or write a novel, novella, or any
  book-length work of fiction (~40k words and up). Also trigger when the user
  mentions "Ralph Loop" together with prose, fiction, or storytelling; or when
  the user provides a premise and expects the agent to take it through
  treatment, character work, conflict analysis, world-building, Save the Cat
  beat planning, chapter outlining, scene and beat decomposition, drafting,
  desloppification, and structured critical revision. This skill is the
  authoritative entry point for long-form fiction generation; prefer it over
  ad-hoc drafting even when the user asks casually ("just write me a novel
  about X"). The skill assumes a harness re-enters the agent until the work
  truthfully reports done, so every operation is idempotent, resumable, and
  state-driven.
---

# novel-ralph

A skill for writing complete novels under a Ralph Loop harness — a tight agent
loop that re-enters the model on each turn until the work is truthfully
finished. The skill is the orchestrator: it owns the phase machine, the state
layout, the chapter drafting inner loop, and the adversarial review pipeline.

## Harness contract

The harness re-enters the agent repeatedly with a thin prompt of the form
"continue the novel until done." The agent has no memory between turns beyond
what it persists to disk and what the system prompt restores. This imposes four
requirements on every operation in this skill:

1. **Idempotent entry.** First action on every turn: read
   `working/state.toml`. Derive next action from state alone. Never assume
   continuity with the previous turn.
2. **Atomic state writes.** Update `state.toml` only after the work it
   describes is on disk. A crash mid-phase must leave a coherent state.
3. **Bounded turn work.** Each turn advances state by one meaningful
   unit — one scene drafted, one chapter critiqued, one beat written — then
   returns. Do not try to finish the novel in one turn.
4. **Truthful done reporting.** The agent reports "done" only when the
   predicate in `references/done-conditions.md` evaluates true against the
   manuscript on disk. Aspirational completion is a failure.

## Governing principles

1. **Plan before prose.** Premise, characters, conflict, world, audience,
   beat sheet, and chapter outline land before the first beat is drafted.
   Drafting against a vague plan produces a vague novel.

2. **Attractor analysis over conflict tropes.** Characters and forces have
   equilibria they are pulled toward. The plot is the trajectory through phase
   space when those equilibria collide. See `references/conflict-attractor.md`.

3. **The reader is a stakeholder.** A novel that no identifiable reader
   wants to read is a journal entry. The product-market fit phase is not
   ironic; it forces honesty about what the book is for. See
   `references/jtbd-novel.md`.

4. **Adversarial review is mandatory.** The spiteful critic, parasocial
   fangirl, and knitting-circle passes are not optional polish. They are the
   quality loop. Skipping them produces competent slop.

5. **Desloppification is not stylistic preference.** AI prose has a tell
   set as recognisable as a perfume. Every chapter goes through the checklist in
   `references/desloppify-checklist.md` before the critic sees it.

6. **External artefacts are authoritative.** When prose contradicts the
   character file or the world-building file, the artefact wins. Update the
   prose, not the artefact.

## Reference files

Read these as the workflow demands them. Do not pre-load everything.

| Reference                     | When to read                                          | Path                                 |
| ----------------------------- | ----------------------------------------------------- | ------------------------------------ |
| State layout                  | First entry, and whenever state mutation is involved  | `references/state-layout.md`         |
| Done conditions               | Every turn, when checking phase or overall completion | `references/done-conditions.md`      |
| Conflict & attractor analysis | Phase 3                                               | `references/conflict-attractor.md`   |
| JTBD for fiction              | Phase 5                                               | `references/jtbd-novel.md`           |
| Save the Cat beat sheet       | Phase 6                                               | `references/stc-beat-sheet.md`       |
| Desloppify checklist          | Every chapter, before critic review                   | `references/desloppify-checklist.md` |
| Critic personas               | Spiteful critic loop, fangirl pass, knitting circle   | `references/critic-personas.md`      |

## Entry routine

Every turn begins here. No exceptions.

```text
1. Ensure working/ exists. If state.toml is missing, this is turn one —
   initialise it from the user's premise or prompt and proceed to Phase 0.
2. Read working/state.toml.
3. Read working/log.md (last 200 lines) for recent context.
4. Determine phase from state.phase.current.
5. Read references/done-conditions.md to check whether the overall
   predicate is satisfied. If yes, report done and stop.
6. Otherwise, jump to the phase handler. Each phase has its own routine
   below.
7. After completing one unit of work, append a log entry summarising
   what changed, update state.toml atomically, and return.
```

## Workflow

The phases run in order. Earlier phases gate later ones. The drafting phase
(Phase 7) contains the inner Ralph loop where most turns will be spent.

### Phase 0 — Premise

Produce `working/premise.md`. Two artefacts:

- **One-sentence logline.** Protagonist + situation + central conflict +
  stakes. No subordinate clauses. No "in a world where".
- **One-paragraph premise.** ~150 words. The hook a writer would pitch to
  a friend at a bar. Names the protagonist, the inciting situation, the
  antagonistic force, the stakes, and the tonal register.

If the user supplied a premise, extract and tighten. If not, draft from context
and ask exactly one clarifying question if a fundamental choice (genre, scale,
voice) is undetermined. Otherwise pick defensibly and note the choice in
`log.md`.

**Exit:** `premise.md` exists, both sections present, logline ≤ 30 words.

### Phase 1 — Treatment

Produce `working/treatment.md`. A 2–5 page narrative synopsis covering the full
arc, beginning to end, including the ending. This is not a teaser. Write the
spoilers. The treatment exists so every later phase knows where the story is
going.

Sections:

- **Premise** (1 paragraph, lifted from `premise.md`)
- **Act I** (~25% of synopsis)
- **Act II-A** (~25%)
- **Act II-B** (~25%)
- **Act III** (~25%)
- **Ending** (explicit: who survives, what changes, what the final image
  is)
- **Themes** (2–4 thematic threads, named)

**Exit:** `treatment.md` exists, ending is unambiguous, themes named.

### Phase 2 — Characters

Produce `working/characters/_index.md` and one file per named character at
`working/characters/<slug>.md` — every character given a name in the treatment
gets a file, matching the exit rule below.

Each character file contains, in this order:

- **Name, age, role in the story.**
- **Motivations.** What the character wants. Distinguish stated desire
  from underlying need (Aristotelian want vs. need).
- **Goals.** Concrete objectives the character pursues. At least one
  scene-level, one act-level, one novel-level.
- **Challenges.** External obstacles in the character's way.
- **Limitations.** What the character cannot do, will not do, or does
  not know. Limitations create plot.
- **Flaws.** Character defects that drive bad decisions. Distinguish
  fatal flaw (will not change) from growth flaw (will, painfully).
- **Ambitions.** Where the character wants to be at the end of the
  novel, whether or not they get there.
- **Quirks.** Specific behavioural tells. Speech tics, physical
  habits, irrational preferences. Three to five.
- **Premise-applicable traits.** Properties the premise specifically
  requires of this character — magical lineage, professional expertise,
  formative trauma, whatever the world demands.
- **Voice notes.** How the character talks: register, vocabulary,
  cadence, what they refuse to say.
- **Attractor.** The equilibrium the character is pulled toward when
  not under pressure. See `references/conflict-attractor.md`.

Also produce `working/characters/relationships.md`: a relationship graph with
edge labels (rivalry, debt, attraction, contempt, owed favour, inherited
grudge) and a short note on the pressure on each edge.

**Exit:** every character with a name in the treatment has a file; the
relationship graph is connected; each character has a named attractor.

### Phase 3 — Conflict and attractor analysis

Produce `working/plan/conflict-map.md`.

Read `references/conflict-attractor.md` before starting. The output identifies:

- Each character's attractor.
- The forces acting on each character (internal: flaws, fears;
  external: obligations, relationships, world conditions).
- Points in phase space where attractors are incompatible — these are
  the conflict sources.
- The trajectory the protagonist traces as the antagonist disturbs the
  initial equilibrium.
- Secondary conflict bands (subplots) and where they intersect the
  main trajectory.

This phase reveals plot holes early. If two characters' attractors are not
actually in tension, the conflict is manufactured and the plot will feel
forced. Surface this now and revise the treatment if needed.

**Exit:** conflict-map.md exists; every named conflict in the treatment has at
least one attractor pair behind it; no character lacks an attractor.

### Phase 4 — Setting expansion

Produce files under `working/world/`:

- `setting.md` — overview, era, scale, baseline reality assumptions.
- `geography.md` — places that appear in the novel, with sensory and
  functional detail. Maps and distances if relevant.
- `politics.md` — power structures, factions, contested resources,
  current grievances. Even an intimate domestic novel has politics (household,
  workplace, family).
- `pressure-dynamics.md` — what forces are squeezing the world right
  now? Economic stress, climate shifts, generational tensions, technological
  disruption. These are the ambient pressures that characters live inside.
- `physicalities.md` — embodiment, climate, food, sleep, weather,
  fatigue, illness, what people wear, how spaces smell. The sensorium the prose
  will draw from.

Detail proportional to relevance. A novel that turns on inheritance law needs
three pages on inheritance law; a novel that takes place in a single flat needs
three pages on the flat. Padding here costs nothing in word count and saves an
enormous amount of drafting friction later.

**Exit:** all five files exist; every named location and faction in
treatment.md is covered; ambient pressures are named.

### Phase 5 — Product-market fit

Produce `working/reader/audience.md` and `working/reader/comps.md`.

Read `references/jtbd-novel.md` before starting. The output answers, without
flinching:

- **Who is the reader?** Specific enough that the agent could
  recognise one. Age range, reading habits, what shelf they pull from.
- **What job are they hiring this novel to do?** Escape, catharsis,
  social signalling, intellectual challenge, comfort, dread, vicarious
  competence — name it.
- **What is the opportunity space?** What gap in the existing market
  does this novel address? Where are readers underserved?
- **What are the comps?** Three to five published novels this book sits
  alongside on the shelf. Not "better than" — sits alongside. Include release
  year and publisher.
- **Anti-comps.** Two or three books this novel is explicitly *not*
  trying to be, to clarify by contrast.

If the answers reveal that the novel has no reader, surface it. The agent has
two honest choices: revise the premise to fit a reader, or proceed with eyes
open knowing the work is for the writer.

**Exit:** both files exist; JTBD is named in a single sentence; comps have
ISBNs or publisher confirmations where retrievable.

### Phase 6 — Save the Cat

Produce `working/plan/genre-stc.md`.

Read `references/stc-beat-sheet.md` before starting. The output:

- **Selected STC genre** (one of the ten), with a one-paragraph
  justification grounded in the premise and treatment. The ten: Monster in the
  House, Golden Fleece, Out of the Bottle, Dude with a Problem, Rites of
  Passage, Buddy Love, Whydunit, Fool Triumphant, Institutionalized, Superhero.
- **The fifteen-beat sheet** populated for this novel. Each beat gets
  a name, a target word count, and a one-paragraph description. The description
  names which characters are present, what happens, and what state change the
  beat effects.
- **Beat-to-treatment crosswalk.** Confirms every event in the
  treatment lands on a beat, and every beat has a corresponding event. Gaps
  reveal weak structure. Address them before drafting.

**Exit:** all fifteen beats populated; word count targets sum to the intended
novel length ± 10%; crosswalk has no orphans on either side.

### Phase 7 — Chapter planning

Produce `working/plan/chapter-outline.md`.

For each chapter (typically 20–35 for a novel of 80–100k words), record:

- **Chapter number and title** (working title acceptable; titles can
  be revised later).
- **POV character.**
- **Setting.** Where, when, weather, time of day.
- **Premise of the chapter.** What does this chapter exist to do for
  the novel?
- **Characters present.**
- **Conflict.** What pressure drives this chapter — between whom, over
  what?
- **Outcome.** What changes by chapter's end. State change is the test
  of necessity: if nothing changes, the chapter is filler.
- **STC beat assignment.** Which beat(s) from Phase 6 this chapter
  serves. Multiple chapters can serve one beat; one chapter can serve multiple
  beats.
- **Target word count.**

**Exit:** chapter-outline.md exists; every STC beat is covered by at least one
chapter; every chapter has a non-trivial outcome.

### Phase 8 — Drafting (the inner Ralph loop)

This is where most turns are spent. Drafting iterates chapter by chapter.
Within a chapter, the loop is:

```text
For chapter N from 1 to last:
  If state.drafting.current_chapter == N and chapter not done:
    a. Scene plan: produce working/manuscript/chapter-NN/scenes.md
       breaking the chapter into 3–7 scenes. Each scene gets a POV,
       location, characters, scene-level goal, conflict, outcome,
       and rough word count.
    b. Beat plan: produce working/manuscript/chapter-NN/beats.md
       breaking each scene into 4–12 beats. A beat is the smallest
       narrative unit — a moment, a line, an exchange, a realisation.
    c. Write beats: draft prose for each beat into
       working/manuscript/chapter-NN/draft.md. Write one scene per
       turn unless scenes are very short.
    d. Desloppify: run the checklist in
       references/desloppify-checklist.md against the chapter draft.
       Apply every required cut and rewrite.
    e. Spiteful critic loop (see below).
    f. Fangirl pass (see below).
    g. Touch working/manuscript/chapter-NN/done.flag and advance
       state.drafting.current_chapter.

At 30%, 50%, 80% of cumulative word count (compared to target):
  Knitting circle pass (see below).

When all chapters have done.flag and all three knitting passes are
done, advance to Phase 9.
```

#### Spiteful critic loop (within a chapter)

After desloppification, the chapter goes to the spiteful critic.

Read `references/critic-personas.md` for the full system prompt. The loop:

```text
pass = 0
while pass < 4:
    Run spiteful critic against working/manuscript/chapter-NN/draft.md.
    Critic produces working/manuscript/chapter-NN/critic-notes.md
    with issues classified BLOCKER | MAJOR | MINOR | TASTE.

    If no BLOCKER and no MAJOR issues:
        Break — chapter is critic-clean.

    Address every BLOCKER and MAJOR issue. Address MINOR issues at
    the agent's discretion (default: address them). Ignore TASTE
    issues unless they cluster (≥5 instances of the same tic).

    Re-run desloppification on edited passages.
    pass += 1

If pass == 4 without convergence, log the unresolved MAJOR issues
and proceed. Hitting the cap is a signal that the chapter has a
structural problem that line edits will not fix; flag it for the
knitting circle pass.
```

**The critic's findings reset each pass.** The previous pass's critic-notes.md
is overwritten. What matters is the current state of the chapter.

#### Fangirl pass (within a chapter)

After the spiteful critic clears, the chapter goes to the parasocial fangirl.
One pass, not a loop. Output goes to
`working/manuscript/chapter-NN/fangirl-notes.md` and to a forward log at
`working/fangirl-running.md`.

The fangirl pass is **additive and forward-projecting**. It does not trigger
back-edits to the chapter just completed. Its outputs feed into the planning of
subsequent chapters:

- Character behaviour patterns to maintain.
- Tensions or motifs to develop.
- Call-backs to set up.
- Continuity flags that need attention.

When planning chapter N+1, read `working/fangirl-running.md` and fold relevant
items into the scene plan.

#### Knitting circle pass (at 30%, 50%, 80%)

When cumulative completed word count crosses 30%, 50%, or 80% of the target
(and the corresponding gate in state is not yet true), assemble
`working/manuscript/compiled.md` from all done chapters and run the knitting
circle persona against it.

The knitting circle output, `working/reviews/knitting-NN.md`, lists structural
actions ranked by severity. Unlike the fangirl pass, this **can** trigger
back-edits to earlier chapters — but only structural ones (pacing, emphasis,
omission, addition). Line-level edits at this scale are out of scope; the
spiteful critic handled those at chapter time.

After integrating, regenerate `working/manuscript/compiled.md` from the current
chapter drafts (run `novel-compile`) so the compile reflects the back-edits the
knitting pass just made; the `compiled.md` assembled before the pass is now
stale. Then set the corresponding gate (`state.gates.knitting.done_30 = true`,
etc.) and continue drafting.

### Phase 9 — Final pass

Once all chapters are done and all three knitting passes are integrated, run
one final assembly:

1. Concatenate all chapters into `working/manuscript/compiled.md`.
2. Run desloppification across the full manuscript — flag any tic the
   spiteful critic missed at chapter scale that becomes obvious at novel scale
   (e.g., overused phrase across chapters).
3. One last spiteful critic pass at novel scale, looking only for
   structural issues invisible at chapter scale: opening weakness, sagging
   middle that survived the 50% knitting pass, ending that does not deliver the
   treatment's promise.
4. Verify the final image matches the planned final image from the
   treatment. If not, decide whether the novel earned the new ending or the new
   ending is a drift artefact.

**Exit:** `working/manuscript/compiled.md` exists; the done predicate in
`references/done-conditions.md` evaluates true.

## State layout summary

The working directory layout, in full, lives in `references/state-layout.md`.
Key paths:

```text
working/
├── state.toml
├── log.md
├── premise.md
├── treatment.md
├── characters/
├── world/
├── reader/
├── plan/
├── manuscript/
│   ├── chapter-NN/
│   │   ├── scenes.md
│   │   ├── beats.md
│   │   ├── draft.md
│   │   ├── critic-notes.md
│   │   ├── fangirl-notes.md
│   │   └── done.flag
│   └── compiled.md
├── reviews/
└── fangirl-running.md
```

## Done predicate (short form)

The novel is done when **all** of:

1. `state.phase.current == "done"`.
2. Every chapter directory has `done.flag`.
3. `working/reviews/knitting-30.md`, `knitting-50.md`, and
   `knitting-80.md` exist and their integration is logged.
4. `working/manuscript/compiled.md` exists and equals the
   concatenation of chapter drafts.
5. Phase 9's final pass is logged as complete.

Truthful "done" means evaluating this on disk, not asserting. See
`references/done-conditions.md` for the verification routine.

## Failure modes

- **Phase 0 produces a vague premise.** The treatment phase will paper
  over it and characters will feel uncast. Insist on a logline that names
  protagonist, situation, conflict, and stakes. Reject "a story about a man who
  learns".

- **Treatment ends ambiguously.** "And then she decides her future" is
  not an ending. Make the treatment commit. The ending can change during
  drafting if earned, but the plan must have one.

- **Character files are interchangeable.** If the cast files read like
  the same person with different names, the voices are not differentiated.
  Voice notes and quirks must be specific. Rewrite before proceeding.

- **Conflict map reveals a manufactured conflict.** If two characters'
  attractors don't actually conflict, the plot is wallpapered over a hollow.
  Revise the treatment.

- **JTBD reveals no reader.** Stop and resolve. Either revise the
  premise toward a reader or proceed knowing the novel is for the writer. Both
  are valid; pretending the question wasn't asked is not.

- **STC beat sheet has structural gaps.** Some chapters serve no beat;
  some beats have no chapter. Fix in planning, not drafting.

- **Spiteful critic loop hits the pass cap.** A chapter that cannot
  converge on line edits has a structural problem. Log the issue, flag it for
  the next knitting circle pass, and move on. Don't burn turns re-arranging
  deck chairs.

- **Knitting circle wants back-edits at 80%.** Implement only what's
  structurally necessary. At this scale, every back-edit costs meaningful
  turns. The bar for "revise chapter 4" at the 80% mark is higher than at the
  30% mark.

- **Fangirl gushes.** The persona has degraded. Re-read
  `references/critic-personas.md` and re-prompt with the anti-gush clause.

- **Spiteful critic praises.** Same. The persona has been seduced by
  prose quality or polite drift. Re-prompt.

- **Drift between artefacts and prose.** Prose says the protagonist is
  blond; character file says brunette. Artefact wins. Edit prose.

## Anti-patterns

- **The vibe draft.** Writing prose without planning beats, in the hope
  that the chapter will reveal itself. It will not. The chapter will reveal
  that the agent did not know what the chapter was for.

- **Skipping phases.** "Let's just start writing." No. The phases exist
  because each one prevents a class of catastrophic mid-draft pivot.

- **Critic-loop infinity.** Every chapter can always be polished
  further. The pass cap is hard. Respect it.

- **Knitting circle as line editor.** The knitting circle reads
  structurally. If output starts critiquing sentence-level prose, the persona
  has been miscast. Re-prompt.

- **Desloppify as cosmetic.** The checklist is a hunting list, not a
  vibe check. Every flagged item gets dealt with or explicitly justified.

- **Concatenating without compiling.** `compiled.md` is regenerated
  from chapter drafts, not edited in place. Editing in place loses the
  authoritative chapter sources.

- **Forward fangirl notes ignored.** The fangirl's continuity flags
  exist precisely because the agent will forget. Read `fangirl-running.md` at
  the start of every chapter plan.

- **The "almost done" lie.** Truthful done is on disk, not in feeling.
  Run the predicate.
