# State layout

The Ralph Loop assumes no memory between turns. State lives on disk. This
reference defines the working directory, the `state.toml` schema, the log
conventions, and the atomic-write discipline.

## Working directory

The skill operates inside a single working directory. Default location:
`./working/` relative to wherever the agent is run. Override via user
instruction.

```text
working/
├── state.toml                       # phase machine state
├── log.md                           # iteration log
├── premise.md                       # Phase 0 output
├── treatment.md                     # Phase 1 output
├── characters/
│   ├── _index.md                    # cast at a glance
│   ├── <slug>.md                    # per-character file
│   └── relationships.md             # relationship graph
├── world/
│   ├── setting.md
│   ├── geography.md
│   ├── politics.md
│   ├── pressure-dynamics.md
│   └── physicalities.md
├── reader/
│   ├── audience.md
│   └── comps.md
├── plan/
│   ├── conflict-map.md              # Phase 3 output
│   ├── genre-stc.md                 # Phase 6 output
│   └── chapter-outline.md           # Phase 7 output
├── manuscript/
│   ├── chapter-01/
│   │   ├── scenes.md
│   │   ├── beats.md
│   │   ├── draft.md
│   │   ├── critic-notes.md          # overwritten each spiteful pass
│   │   ├── fangirl-notes.md
│   │   └── done.flag                # touched when chapter is done
│   ├── chapter-02/
│   │   └── ...
│   └── compiled.md                  # all chapter drafts concatenated
├── reviews/
│   ├── knitting-30.md
│   ├── knitting-50.md
│   └── knitting-80.md
└── fangirl-running.md               # forward-projecting fangirl log
```

Chapter directory names are zero-padded to two digits up to 99 chapters. Beyond
99, use three digits. (Almost no novel reaches 99 chapters; if yours does,
that's a structural conversation.)

## state.toml schema

The agent's primary memory. Read at the start of every turn, written atomically
(write to `state.toml.new`, fsync, rename) at the end.

```toml
schema_version = 1

[novel]
title = "Working Title"            # may be provisional
slug = "working-title"             # filesystem-safe identifier
target_word_count = 80000
created_at = "2026-05-23T14:00:00Z"

[phase]
current = "drafting"               # see phase enum below
completed = [
    "premise",
    "treatment",
    "characters",
    "conflict-analysis",
    "setting",
    "reader-fit",
    "stc",
    "chapter-planning",
]

[drafting]
current_chapter = 7
current_scene = 2                  # 0 if scene plan not yet drafted
current_beat = 4                   # 0 if beats not yet drafted

[drafting.critic]
pass = 1                           # current pass number; seeds at 1 (pending)
consecutive_clean = 0              # passes with no BLOCKER/MAJOR
convergence_target = 1             # ceiling for consecutive_clean (default 1)
last_finding_counts = {            # most recent pass result
    blocker = 0,
    major = 2,
    minor = 4,
    taste = 7,
}

[drafting.fangirl]
last_chapter_passed = 6            # last chapter where fangirl ran

[gates.knitting]
done_30 = true                     # 30% gate passed and integrated
done_50 = false
done_80 = false

[gates.final]
final_pass_complete = false

[word_counts]
# Updated each turn; used to determine knitting circle gates.
target = 80000
current = 24300                    # drafted sum (sum of by_chapter values)
by_chapter = { "01" = 3200, "02" = 3500, "03" = 3700, ... }

# Ordered chapter manifest, written only by `novel-state set-chapters`.
# One [[chapters]] entry per planned chapter; never edited by hand.
[[chapters]]
number = 1
slug = "the-summons"               # filesystem-safe identifier
title = "The Summons"
target_words = 3200

# Transient intent record; present only mid-mutation, absent once settled.
# Written before any artefact, cleared after every artefact is verified.
[pending_turn]
operation = "set-chapters"                  # the mutation in flight
paths = ["working/manuscript/chapter-01"]   # the paths it will write
```

### Phase enum

In order:

```text
premise
treatment
characters
conflict-analysis
setting
reader-fit
stc
chapter-planning
drafting          # contains the inner Ralph loop
final-pass
done
```

`phase.current` reflects the active phase. `phase.completed` contains all
phases that have produced their exit artefacts. Phases must be completed in
order; the entry routine refuses to jump phases.

### Drafting sub-state

Drafting is the only phase with structured sub-state, because it is the only
phase that takes many turns. The sub-state lets the agent resume mid-chapter
without re-drafting.

`current_chapter`, `current_scene`, `current_beat` form a cursor. The entry
routine reads the cursor and advances the smallest applicable unit:

- If `current_beat` is mid-scene, write the next beat.
- If a scene is complete and more scenes remain, advance to the
  next scene's first beat.
- If the chapter's beats are complete, run desloppify.
- If desloppify is run, advance to the spiteful critic loop.
- If spiteful critic converges or hits cap, run fangirl.
- If fangirl is done, touch `done.flag` and advance to chapter
  N+1.

Each sub-step is its own state transition, logged.

### Critic sub-state

`drafting.critic.pass` is the current pass number for the current chapter.
Passes are numbered from 1, so a fresh `state.toml` and each new chapter seed
`pass = 1` — the first pass, pending rather than run. It increments as the
spiteful critic loop runs. Set it by running
`novel-state set-critic-pass --pass N` — never by a direct `state.toml` edit, per
ADR-001 and ADR-010; the command refuses a pass below 1 with exit 3.

`consecutive_clean` is currently always 0 or 1 (one clean pass is sufficient
for convergence). Reserved for future tightening if the loop turns out to be
too easy on chapters.

`convergence_target` is the configured ceiling for `consecutive_clean` (default
1), replacing the previously hard-coded literal. Raising it tightens the
convergence bar — `novel-state check` requires
`0 ≤ consecutive_clean ≤ convergence_target` and rejects a target below 1 — so
the bar can be lifted without editing the validator (design §5.1).

`last_finding_counts` is the most recent critic pass's tally. Used for logging
and for deciding whether to re-run after edits.

### Fangirl sub-state

`drafting.fangirl.last_chapter_passed` is the last chapter the parasocial fangirl
pass ran on; `0` means no pass yet. Set it by running
`novel-state set-fangirl --last-chapter N` — never by a direct `state.toml` edit,
per ADR-001 and ADR-010. The command refuses a chapter outside
`[0, number-of-manifest-chapters]` with exit 3.

### Gates

The knitting circle gates trigger when
`word_counts.current / word_counts.target` crosses 0.30, 0.50, and 0.80
respectively, and the corresponding gate is still false. After the pass is
integrated and logged, flip the gate by running
`novel-state set-gate --knitting-30` (or `--knitting-50`/`--knitting-80`) — never
by a direct `state.toml` edit, per ADR-001 and ADR-010. The command asserts the
value the drafted ratio mandates and refuses with exit 3 if the ratio has not
crossed the threshold (the gate-ratio binding; `novel-state check` validates the
gate against `sum(by_chapter) / target`).

This binding couples `recount` to the gates. `novel-state recount` re-derives
`[word_counts]` from the drafts and never flips a gate — disk does not store the
"pass integrated" fact, so the harness will not synthesise it. If a recount
refuses on `gate-ratio-consistent`, it is telling you the re-derived ratio
crossed a knitting threshold the recorded gates do not yet reflect: integrate
and log the pending knitting pass, then run
`novel-state set-gate --knitting-NN`.
Do not hand-edit `[gates]` to silence it. (If instead the message says a gate is
recorded true while drafting has dropped *below* its threshold, the recorded
gate no longer matches the drafts — adjudicate by restoring the drafts or
clearing the gate, then re-derive.)

`final_pass_complete` flips to true at the end of Phase 9. Flip it by running
`novel-state complete-final-pass` (or `novel-state set-gate --final`), never by
a direct `state.toml` edit.

### Chapter manifest

The `[chapters]` array is the ordered record of each planned chapter — its
`number`, `slug`, `title`, and `target_words`. It is the authoritative set
against which `novel-state check` validates the on-disk `chapter-NN/`
directories, and its order mirrors the zero-padded directory index
`novel-compile` follows. It is written only by `novel-state set-chapters` when
chapter planning completes — never by a direct `state.toml` edit, per ADR-001
and ADR-008 — because the manifest is the agent's non-recomputable judgement
(design §5.1). A freshly initialised `state.toml` carries an empty
`chapters = []`; `set-chapters` populates it.

### Pending turn

The `[pending_turn]` table is a transient intent record for a multi-file
mutation (design §3.4). A single `state.toml` rename is atomic, but a turn that
touches several files — a draft, a `done.flag`, a recount — is not atomic as a
whole. So a mutator opens `[pending_turn]` *before* it writes any other
artefact, naming the `operation` in flight and the `paths` it will write, and
clears the record once every artefact is written and verified. It is present
**only** while a multi-file mutation is mid-write; a settled `state.toml`
carries no `[pending_turn]` at all, and a freshly initialised one never writes
it. On the next turn, an uncleared `[pending_turn]` is the signature of a torn
turn: `novel-state check` reads it, compares the named paths against disk, and
reports the reconciliation `novel-state reconcile` carries out (design §5.1,
§5.4).

Because `novel-state init` never emits `[pending_turn]`, the emitted-schema
drift guard (`tests/test_state_layout_schema_guard.py`) cannot cover it; this
subsection is the only reconciliation between the reference and the transient
on-disk shape design §5.1 names.

## log.md

Append-only iteration log. One entry per turn. Format:

```markdown
## 2026-05-23T14:32:11Z — turn 47

**Phase:** drafting
**Cursor:** chapter 07, scene 2, beat 5
**Action:** Wrote beats 4–5 of scene 2.
**Word count:** 24,820 (chapter 07: 1,820 so far)
**Notes:**
- The confrontation lands harder than planned; revisit the chapter
  plan if beat 6 needs to give the scene more breathing room.
- Fangirl-running.md flagged that Aoife's reaction in chapter 3
  was sharper; folded a hint of that register here.

**Next:** Beat 6 of scene 2, then beat 1 of scene 3.
```

The log serves two functions:

1. **Recovery.** If a turn crashes or context is lost, the log
   plus state.toml tells the next turn what was in flight.
2. **Audit.** A drift detection trail. If the agent has been
   working on chapter 4 for 18 turns and the log shows it re-drafting the same
   beat, something is wrong.

Read the last 200 lines on every entry. Don't try to load the whole log into
context; it grows.

## Atomic writes

State integrity matters. The agent must not leave the working directory in a
state where `state.toml` says "chapter 7 is done" but the chapter draft is
incomplete.

Discipline:

1. Write the actual work first (draft.md, critic-notes.md,
   etc.).
2. After the work is on disk and verified (file exists, size is
   non-zero), update state.toml.
3. Write state.toml via a temporary file in working/, then atomically
   rename it over working/state.toml, so a crash mid-write never leaves a torn
   file.
4. Append to log.md last. The log entry is the receipt that the
   state transition happened.

## Initialisation

First turn: working/ does not exist.

```text
1. mkdir -p working/{characters,world,reader,plan,manuscript,reviews}
2. Create state.toml with:
   - phase.current = "premise"
   - phase.completed = []
   - novel.target_word_count from user input or default 80000
   - novel.title and slug provisional
3. Create empty log.md.
4. Proceed to Phase 0.
```

## Resumption

Any subsequent turn:

```text
1. Read state.toml.
2. Read last 200 lines of log.md.
3. If phase.current is "drafting", read working/fangirl-running.md
   (forward-projecting continuity notes) when it exists. On the first
   drafting turn no fangirl pass has run yet, so the file is absent;
   treat its absence as an empty log rather than failing.
4. Jump to the phase handler.
```

The agent does not need to re-read prior phase outputs unless its current task
depends on them. Cursor-driven loading.

## Working directory hygiene

- Never delete files in `working/`. State is precious.
- Never edit `compiled.md` directly. It is regenerated.
- `done.flag` is an empty file (`touch`). Its presence is the
  signal.
- All Markdown is UTF-8. All filenames are lowercase ASCII with
  hyphens.
- Code identifiers in TOML use snake_case. Document terminology
  uses kebab-case where filename-equivalent.

## When state is suspect

If the agent reads state.toml and finds it incoherent with what is on disk
(state says "chapter 5 done" but no `done.flag` exists in chapter-05/), the
agent must:

1. Stop.
2. Reconstruct the intended state from on-disk evidence (which
   chapters have done.flag, what's in compiled.md, etc.).
3. Write a recovery log entry naming the discrepancy.
4. Update state.toml to match disk reality.
5. Proceed.

Disk is authoritative. State.toml describes disk. Never the reverse.
