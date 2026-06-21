# Conflict and attractor analysis

A novel's plot is the trajectory of characters through a phase
space in which their equilibria are incompatible. This frame is
borrowed from dynamical systems: useful because it forces the
agent to ground conflict in incompatible stable states rather
than in surface antagonism.

A character does not need a villain to have a story. They need an
attractor — a state they are pulled toward — and a force that
disturbs it. The force may be another character whose attractor
collides with theirs. It may be a structural pressure from the
world. It may be an internal contradiction that becomes
unsustainable.

This reference is the protocol for Phase 3. It produces
`working/plan/conflict-map.md`.

## Concepts

### Attractor

The equilibrium a character is pulled toward when external
pressure relaxes. It is what they would settle into if left
alone. Not what they want (that's a goal); not what they would
choose (that's agency); the state they revert to absent forcing.

A reclusive professor's attractor is solitude. Their goal might
be tenure; their want might be respect. Their attractor is the
empty study.

A reformed addict's attractor is the drug. Their goal is
sobriety; their want is dignity. The attractor is what they
fight every day to escape.

A devoted parent's attractor is the child. Goals and wants
diversify; the attractor is the gravitational pull.

Attractors can be social (a relationship), behavioural (a
practice), spatial (a place), emotional (a feeling state),
identity-bound (a self-image), or compulsive (an urge). They are
rarely conscious. Asking the character what their attractor is
usually produces a wrong answer.

### Force

Any influence that disturbs a character from their attractor.
Internal forces include flaws, fears, contradictions, drives.
External forces include other characters' attractors, world
pressures, obligations, crises.

A force does not need to be hostile. A force may be the pull of
another character whose attractor is incompatible. A character
may be drawn toward a state that contradicts their own attractor
— and this is plot.

### Trajectory

The path through phase space the character traces as forces
disturb their attractor. The plot is the composite trajectory of
the protagonist and the characters whose paths cross theirs.

### Incompatibility

Two attractors are incompatible if both cannot be satisfied
simultaneously. Examples:

- One character's attractor is solitude; another's attractor is
  this character's company.
- One character's attractor is a city; another's attractor is
  the country they would have to leave to follow them.
- One character's attractor is a moral identity that another
  character's attractor would force them to compromise.

Incompatibility is the structural source of conflict. If two
attractors are compatible, the relationship is stable and offers
no plot.

## Protocol

### Step 1 — Read the cast

Read every file under `working/characters/`. For each character,
extract or write the attractor explicitly if Phase 2's character
files do not already name one. Update the character file in place.

The attractor must be specific. "Happiness" is not an attractor.
"The kitchen of his late mother's flat in Salford" is. "Being
the person Marin used to know" is. "Solitude" is acceptable only
if you can then say what kind, where, with which exceptions.

### Step 2 — Identify forces

For each character, list:

- **Internal forces.** Their flaws (from the character file),
  fears, contradictions, compulsions. Each one is a vector
  pulling them away from their attractor.
- **External forces.** The other characters whose attractors
  pull on them, the world conditions that constrain them, the
  obligations they cannot shed.

For the protagonist, this list should be longer than for any
secondary character. If it isn't, the protagonist is
under-stressed and the novel will feel slack.

### Step 3 — Pair attractors

For each pair of significant characters, mark the relationship
between their attractors:

- **Compatible.** Both can be satisfied. Stable. No plot here
  (but may serve as a refuge point — a relationship that
  remains constant while others churn).
- **Incompatible but distant.** They could collide but currently
  do not. Latent conflict; can be activated by the catalyst.
- **Incompatible and active.** Currently in tension. The
  generative pairings for plot.
- **Mutually disturbing.** Each character's attractor disturbs
  the other's; both are being pulled out of equilibrium by the
  presence of the other. The classic engine of romance plot,
  rivalry plot, and many family dramas.

Produce this as a table in `conflict-map.md`.

### Step 4 — Map the trajectory

For the protagonist:

1. **Initial position.** What is their attractor and how stably
   are they sitting in it at the novel's open?
2. **Disturbance.** What disturbs them — the catalyst, in STC
   terms? Which forces activate?
3. **Trajectory.** Through which states do they pass as the
   disturbance plays out? At each major beat, where are they in
   phase space?
4. **Terminal position.** Where do they end? Have they returned
   to their attractor (cyclical plot), reached a new attractor
   (transformational plot), been destroyed by the inability to
   reach either (tragic plot), or entered an unstable orbit
   (unresolved/literary plot)?

The terminal position must match the treatment's ending. If it
does not, one of them is wrong; resolve before drafting.

### Step 5 — Subplot bands

For each significant secondary character, map an abbreviated
trajectory. Each subplot is a smaller orbit running alongside
the main trajectory.

Mark where each subplot intersects the main trajectory:

- **Reinforcing.** The subplot pushes the protagonist further
  along their main trajectory.
- **Counterweight.** The subplot pulls the protagonist
  sideways, complicating the main trajectory.
- **Mirror.** The subplot traces a parallel arc that comments on
  the main one (echoing, contrasting, or refuting).
- **Catalyst.** The subplot's events trigger main-trajectory
  beats.

A subplot that does none of these has no business in the novel.

## Output format

`working/plan/conflict-map.md` should contain, in order:

```markdown
# Conflict and attractor analysis

## Attractors

### <Character name>
**Attractor:** <specific state, place, relationship, or condition>
**Stability at novel's open:** <stable / disturbed / unstable>
**Notes:** <one or two sentences>

[Repeat for every named character.]

## Forces

### <Character name>
**Internal forces:**
- <flaw or compulsion> — <what direction it pulls>
- ...
**External forces:**
- <other character or world condition> — <what direction it pulls>
- ...

[Protagonist's list should be the longest.]

## Attractor pairings

| Character A | Character B | Compatibility | Active in plot? |
|---|---|---|---|
| Aoife | Marin | mutually disturbing | yes — central |
| Aoife | the village | compatible | refuge |
| Marin | Cassian | incompatible, latent | activates Act II |
| ... | ... | ... | ... |

## Protagonist trajectory

**Initial:** <state>
**Catalyst disturbs:** <which forces activate>
**Act I end:** <state in phase space>
**Midpoint:** <state>
**All Is Lost:** <state>
**Climax:** <state>
**Final:** <state>
**Trajectory type:** cyclical / transformational / tragic / unresolved

## Subplot bands

### <Secondary character> — <subplot label>
**Function:** reinforcing / counterweight / mirror / catalyst
**Intersection points:** <which beats of the main trajectory>
**Brief trajectory:** <initial → terminal in one or two sentences>

## Plot holes surfaced

[If any pairing analysis reveals a manufactured conflict, list it
here. The treatment must be revised before Phase 4.]
```

## Validation checks

Before exiting Phase 3:

- Every character has an attractor.
- The protagonist has at least three forces (more typically:
  five to seven).
- At least two "incompatible and active" or "mutually
  disturbing" pairings exist by Act II.
- Every named conflict in the treatment has an attractor pair
  behind it.
- Every subplot has a named function.
- The trajectory's terminal position matches the treatment's
  ending.

If any check fails, fix it before advancing.

## When the analysis breaks the plan

The conflict map is the first phase that can falsify earlier
work. Common breakages:

- **Two main characters' attractors turn out to be compatible.**
  The conflict between them is manufactured. Either change one
  character's attractor or invent the actual incompatibility.
- **The protagonist has too few forces.** They're not under
  enough pressure. Add an internal contradiction or an external
  obligation. Update the character file.
- **A subplot has no function.** Cut it from the treatment or
  give it one.
- **The terminal position doesn't match the treatment's ending.**
  Decide which one is right. Update the other.

These corrections happen *now*, not during drafting. A
manufactured conflict in chapter 14 is much more expensive than a
falsified treatment in Phase 3.
