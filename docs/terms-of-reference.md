# novel-ralph skill rebuild — terms of reference

## Front matter

- **Status:** Draft, v0.1.
- **Audience:** Skill maintainer, contributors building the deterministic
  spine, and reviewers of the downstream design and roadmap.
- **Companion documents:**
  - `docs/novel-ralph-harness-design.md` (technical design; expands the
    *how*).
  - `docs/roadmap.md` (sequences the *when*).
  - `skill/novel-ralph/SKILL.md` and `skill/novel-ralph/references/`
    (the artefact under rebuild).
  - `docs/scripting-standards.md` (Cyclopts, cuprum, and pathlib
    conventions the helper scripts must follow).
- **Date and version:** 2026-06-21, v0.1.

This document is written downstream of solution-space artefacts. The
`novel-ralph` skill and a detailed field report from an agent that ran it
already exist; no problem-space document preceded them. This terms of reference
reconstructs the *why*, *for whom*, and *bounded by what* from those artefacts
so that the design and roadmap rest on a stated problem rather than on instinct.

## 1. Background and motivation

The `novel-ralph` skill instructs an agent to write a complete novel under a
Ralph Loop harness: a tight loop that re-enters the model each turn with a thin
prompt until the work truthfully reports done. The skill is explicit that the
harness keeps no memory between turns beyond what is persisted to disk, so
every operation must be idempotent, resumable, and state-driven.

The skill currently ships as `SKILL.md` plus six reference files. It describes
a deterministic spine — atomic state writes, a done predicate,
compile-consistency checks, a desloppify linter, knitting gates triggered at
word-count thresholds — but ships none of it as running code. The reference
files present that spine as pseudocode and inline snippets written as if they
were tooling. The only executable snippet, the atomic state-write example at
`skill/novel-ralph/references/state-layout.md:231`, imports a third-party
dependency (`tomli_w`) that is not declared anywhere and does not run.

A field report from an agent that ran the skill end to end (drafting a
twelve-chapter novel across four context compactions) records the consequence
directly: the deterministic half of the harness was performed by hand,
inconsistently, every turn, and the judgemental half was self-marked too gently
because the same context that wrote the prose was then asked to attack it. The
report documents specific failures — state invariants drifting silently
(`consecutive_clean` documented as "always 0 or 1" but driven to 12), word
counts hand-typed from `wc -w`, the done predicate assembled as ad-hoc shell
that returned confusing results, compile-consistency "verified" by eyeballing a
header count, and a per-novel device ledger (rationed phrases and motifs)
managed entirely from memory across compactions.

The work exists now because the skill has been exercised against a real
manuscript and the gap is no longer theoretical. The field report provides
concrete evidence of where the skill's promised determinism silently diverged
from what the agent actually did. The motivation is to close that gap before
the skill is relied on again.

## 2. Domain

The skill operates in long-form fiction generation by a large language model
under an autonomous harness. The relevant field of practice spans two domains
that the skill deliberately joins.

- **Craft of long-form fiction.** Premise, treatment, character work,
  conflict structure, world-building, Save the Cat beat planning, chapter
  outlining, scene and beat decomposition, and adversarial revision. The skill
  encodes a craft pipeline across nine phases, of which drafting (Phase 8)
  holds the inner loop where most turns are spent.
- **Agentic harness engineering.** The Ralph Loop pattern assumes no
  memory between turns; state lives on disk; each turn advances state by one
  bounded unit and returns. Correctness depends on idempotent entry, atomic
  state writes, and a truthful done predicate evaluated against files on disk
  rather than against the agent's sense of completion.

Two established conventions in the second domain are load-bearing for this work:

- **Determinism belongs in code.** Operations whose correct result is a
  pure function of files on disk — aggregating word counts, validating a state
  schema, regenerating a compiled manuscript, counting phrase occurrences
  against thresholds — are mechanical. A model performing them by hand
  introduces variance the harness was designed to remove.
- **Judgement belongs to the model, and adversarial judgement belongs
  to a clean context.** Reading prose for quality, deciding whether a device is
  earned, and adjudicating whether a theme is shown or told are not mechanical.
  The skill's own most-named failure mode — "fangirl gushes", "spiteful critic
  praises" — is the structural result of asking the authoring context to mark
  its own homework.

Prior art the skill builds on includes the Save the Cat beat sheet, the
jobs-to-be-done framing for fiction, and conflict-as-attractor analysis, all
already captured in the skill's reference files. The desloppify checklist
encodes a recognisable set of large-language-model prose tells (em-dash
flooding, "it's not just X, it's Y", tricolons of abstraction, "found herself"
passives, and a high-frequency-offender table with numeric thresholds).

The ubiquitous-language document `docs/context.md` does not yet exist. Terms
introduced here — *deterministic spine*, *done predicate*, *desloppify*,
*knitting circle*, *device ledger*, *clean-context sub-agent* — are candidates
for promotion to a `docs/context.md` when one is created.

## 3. Market context

The product is an internal authoring skill, not a commercial offering, so
"market" here means the alternatives an operator or agent would otherwise reach
for to do the same job.

| Alternative                        | What it offers                                          | Where it falls short                                                                                               |
| ---------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| The current `novel-ralph` skill    | A complete craft pipeline and harness contract in prose | The deterministic spine is unimplemented; the agent hand-rolls it inconsistently and self-marks judgemental passes |
| Ad-hoc drafting (no skill)         | Direct prompting to "write me a novel"                  | No phase machine, no resumability, no quality loop; produces competent slop                                        |
| General-purpose writing assistants | Fluent prose on demand                                  | No book-length state management, no truthful done predicate, no adversarial revision discipline                    |
| Manual authoring by a human        | Full craft control                                      | Not the job this skill exists to do; the skill targets autonomous generation under a harness                       |

The gap the rebuild addresses is specific: among the alternatives, only the
`novel-ralph` skill attempts a deterministic, resumable harness for book-length
generation, and that attempt is undermined by shipping its deterministic
operations as pseudocode. The competing default the rebuild must beat is
therefore the skill's own current behaviour — an agent improvising state
mutation, predicate evaluation, and linting each turn.

## 4. Users and stakeholders

The primary user is unusual: it is the harnessed agent itself, not a human. The
skill is consumed by an agent re-entered each turn, and the deterministic spine
exists to be invoked by that agent.

| Party                                                           | Type           | Context                                                                                | Cares about                                                                                         | Current alternative                                        |
| --------------------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Harnessed agent (Claude Opus, running the skill)                | Primary user   | Re-entered each turn with no memory beyond disk; finite context; subject to compaction | Idempotent operations, meaningful exit codes, zero hand-rolled determinism, clean-context judgement | Hand-rolled shell and Edit-tool state mutation             |
| Human author / operator                                         | Secondary user | Invokes the skill, supplies the premise, reads the manuscript                          | A finished novel; a harness that does not silently drift                                            | Reads `compiled.md` and the log to confirm progress        |
| Skill maintainer (df12)                                         | Stakeholder    | Owns the skill and its references; reviews this rebuild                                | A maintainable, tested spine; a clear deterministic/judgemental boundary                            | Maintaining prose references that describe unbuilt tooling |
| Clean-context sub-agents (critic, line-editor, knitting circle) | Secondary user | Spawned fresh to read prose without authorship investment                              | Faithful persona prompts; the manuscript and the context they need                                  | The authoring context performing these reads itself        |

Non-users, named to prevent scope drift:

- **Weaker models for adversarial judgement.** The field report is
  explicit that the discrimination of the spiteful critic and the knitting
  voices is the quality loop, and that a weaker model produces "competent-slop
  criticism". Adversarial reading passes are deliberately *not* for sub-peer
  models. Mechanical verification, by contrast, is not for any model — it is
  for scripts.
- **Human copy-editors and structural editors.** The skill automates
  the revision loop; a human editor is out of scope as a dependency.

A note on the primary-user inversion: because the primary user is an agent,
"usability" means machine-friendly interfaces — structured output, meaningful
exit codes, a strict separation between read-only checkers and mutators —
rather than ergonomic prose. This shapes the success criteria in §7.

## 5. Job to be done

### 5.1 Primary job (harnessed agent)

> When re-entered for another turn with no memory beyond disk, the
> agent wants to advance the novel by exactly one bounded unit and
> truthfully determine whether the work is done, so that the harness
> converges on a finished manuscript without the agent re-deriving
> deterministic facts by hand or marking its own prose too gently.

- **Functional dimension:** mutate state safely, recount words, check
  the done predicate, regenerate the compiled manuscript, lint for prose tells,
  and enforce per-novel device rationing — each as a single, repeatable
  operation.
- **Emotional dimension:** the agent should be able to *trust* the
  reported state rather than re-verify it, freeing context for craft.
- **Social dimension:** the manuscript should withstand a cold reader,
  which requires that adversarial passes be genuinely external rather than
  self-administered.
- **Competing alternatives:** improvised `bash`, `wc -w`, `grep`, and
  `Edit`-tool state mutation; self-marked critic and knitting passes.

### 5.2 Secondary job (human operator)

> When commissioning a novel from the skill, the operator wants the
> harness to report progress and completion truthfully, so that "done"
> means a verifiably complete manuscript on disk rather than the agent
> running out of context.

## 6. Scope

### 6.1 Goals

The rebuild draws one hard line between the deterministic and the judgemental,
then delivers each side on the correct side of that line.

- **G1.** Replace every hand-rolled deterministic operation with a
  tested, installed command that runs identically every turn: state mutation
  and validation, the done predicate, compile-consistency, word counting and
  gate triggers, and the desloppify linter.
- **G2.** Make the deterministic commands machine-friendly for an
  agent: structured (JSON) output with a human-readable flag, read-only
  checkers strictly separated from mutators, and meaningful exit codes so the
  harness can gate on them.
- **G3.** Guarantee that the deterministic commands make zero narrative
  judgements; detection and reporting are mechanical, adjudication and edits
  remain with the model.
- **G4.** Establish a single source of truth for state and the done
  predicate, eliminating the present divergence between the short-form
  predicate in `SKILL.md` and the long-form predicate in `done-conditions.md`.
- **G5.** Reconcile state against disk authoritatively: a command must
  re-derive intended state from on-disk evidence and report discrepancies,
  implementing the recovery routine the skill currently describes as a manual
  job.
- **G6.** Correct the documented defects surfaced by the field report:
  the Phase 7/8 mislabel in `SKILL.md:107`, the two-source-of-truth done
  predicate, and the dead per-chapter `plan.md` spec in `state-layout.md:38`.
- **G7.** Define the clean-context sub-agent architecture for the
  adversarial passes (spiteful critic, knitting circle) and the longitudinal
  fangirl, and a new micro-level line-editor pass, with a stated
  model-capability requirement — even though their implementation is sequenced
  after the deterministic spine (see §6.2).
- **G8.** Specify the per-novel device ledger and the AI-isms rule pack
  as versioned configuration data that the linter enforces mechanically, so
  rationing and moving-target tells are detected deterministically while the
  decision to spend a device stays with the model.

### 6.2 Non-goals

- **N1.** Delivering the clean-context sub-agents, the line-editor pass,
  the device-ledger enforcement, and the configurable AI-isms linter in the
  first increment. v1 delivers *determinism parity* — the deterministic
  commands plus the `SKILL.md` corrections. The judgemental architecture is
  designed in §6.1 (G7, G8) and sequenced as later roadmap phases. Operators
  needing those passes in v1 should expect to run them by hand, as the skill
  describes today, until the later phases land.
- **N2.** Changing the craft pipeline itself. Phases 0–9, the Save the
  Cat structure, the conflict-attractor analysis, and the desloppify rule
  content are not under revision except where a defect requires it (G6). The
  rebuild changes *how* deterministic and judgemental work is executed, not
  *what* the craft phases are.
- **N3.** Making the deterministic commands perform any narrative
  judgement (restated from G3 as a hard exclusion). A command that starts
  deciding whether a passive is justified has crossed the line.
- **N4.** Supporting models below peer capability for adversarial
  reading passes. Mechanical work goes to scripts; adversarial reading goes to
  a peer-capability, clean-context model. Routing adversarial judgement to a
  weaker model is explicitly excluded.
- **N5.** Distribution as anything other than installed console-scripts
  within the existing `novel_ralph_skill` package. Self-contained `uv`-run
  scripts and a separate tool are out of scope for this work.
- **N6.** Rewriting the harness driver itself. This work targets the
  skill and its supporting commands, not the external loop that re-enters the
  agent.

### 6.3 Scope insurance

The goals and non-goals are deliberately balanced: each goal on the
deterministic side (G1–G6) has a paired non-goal that fences it (N1 defers the
judgemental side, N2 fences the craft pipeline, N3 fences narrative judgement
out of code). The single largest scope risk is N1 — the temptation to build the
whole field report at once. The roadmap must hold the parity-first line.

## 7. Success criteria

### 7.1 User-facing success (the harnessed agent and operator)

- Across a full novel run, the agent performs zero hand-rolled
  deterministic operations: state mutation, word counts, the done predicate,
  compile regeneration, and desloppify all go through the installed commands.
  Signal: the iteration log shows command invocations, not improvised `bash`/
  `wc`/`grep`/`Edit` for these operations.
- The done predicate is evaluated by a single command returning a
  meaningful exit code; "done" is reported only when that command passes on
  disk. Signal: no turn declares done without a passing predicate command in
  the log.
- State invariants cannot drift silently. Signal: a documented
  invariant such as `consecutive_clean` cannot reach an out-of-range value (the
  field report's value of 12 against a documented range of 0–1 becomes
  impossible) because the mutator validates it.
- Compile consistency is verified by a real comparison, not an eyeball.
  Signal: a stale `compiled.md` is detected even when header counts and word
  totals coincidentally match.

### 7.2 Operational success (the codebase)

- Every deterministic command has automated `pytest` coverage,
  including happy paths, unhappy paths, and edge cases, and passes the
  repository quality gates (`make lint`, `make typecheck`, `make check-fmt`,
  `make test`, `make audit`).
- Commands are idempotent: re-running a mutator converges state without
  destructive side effects, consistent with `docs/scripting-standards.md`.
- State serialisation round-trips losslessly, preserving the on-disk
  `state.toml` formatting and comments rather than corrupting them.

### 7.3 Strategic success (the maintainer)

- The reference files no longer present unbuilt tooling as pseudocode;
  each documented deterministic operation maps to a command that exists and is
  tested.
- The deterministic/judgemental boundary is documented once and held,
  so future contributors can tell at a glance which side a new operation
  belongs on.

## 8. Constraints and assumptions

### 8.1 Hard constraints

- **C1.** The harness keeps no memory between turns beyond disk and the
  restored system prompt. Every command must be usable from a cold start,
  driven by `state.toml` and the working directory alone.
- **C2.** Disk is authoritative; `state.toml` describes disk, never the
  reverse. Reconciliation commands must treat on-disk artefacts as the source
  of truth.
- **C3.** Commands are distributed as installed console-scripts in the
  `novel_ralph_skill` package (per the settled distribution decision).
- **C4.** Scripts follow `docs/scripting-standards.md`: Cyclopts for the
  command-line interface, `cuprum` for any external process execution,
  `pathlib` for filesystem work, UNIX exit-code conventions, and idempotency.
- **C5.** The repository quality gates in `AGENTS.md` are
  non-negotiable: lint, format, typecheck, test, and audit must all pass before
  a change is committed, and each commit is gated.
- **C6.** Documentation follows the df12 style guide: British English
  with Oxford spelling, sentence-case headings, 80-column prose wrapping,
  120-column code wrapping, and captioned tables and diagrams.
- **C7.** No file in `working/` is ever deleted, and `compiled.md` is
  always regenerated rather than edited in place.

### 8.2 Assumptions

- **A1.** The `state.toml` schema in `state-layout.md` is broadly
  correct and can be adopted as the validated schema, with the dead `plan.md`
  reference removed. *Consequence if false:* the schema must be redesigned
  before the state command can validate it, widening v1 scope.
- **A2.** Lossless TOML round-tripping (preserving formatting and
  comments) is achievable with an available library or an owned serialiser.
  *Consequence if false:* either formatting is sacrificed or a custom
  serialiser is built, adding effort to the state command.
- **A3.** The desloppify checklist's §6 table and the AI-isms set are
  expressible as regular-expression rule packs over chapter or manuscript text.
  *Consequence if false:* some tells need a richer matcher than regex,
  increasing linter complexity.
- **A4.** Peer-capability, clean-context sub-agents are available to the
  harness for the later judgemental phases. *Consequence if false:* the
  judgemental phases (G7) cannot be realised as designed and the skill retains
  self-marking for those passes.
- **A5.** Chapter ordering is the zero-padded chapter-directory index
  (`chapter-01`, `chapter-02`, …), a total deterministic order that needs no
  outline-prose parsing, validated against a structured chapter manifest in
  `state.toml` written at chapter planning. The design resolves this from "can
  be derived" to "is derived by the chapter index, checked for a
  manifest-to-disk bijection" (novel-ralph-harness-design.md §4.3, §5.2).
  *Consequence if the manifest is missing or non-bijective:* compilation has no
  authoritative ordering and fails loudly rather than mis-ordering silently.

### 8.3 Dependencies

- **D1.** The existing Python package skeleton (`novel_ralph_skill`,
  hatchling wheel build) is the home for the new entrypoints. It is on the
  critical path: the package's build and console-script wiring must be in place
  before any command can be installed and invoked.
- **D2.** `docs/scripting-standards.md` and `AGENTS.md` govern how the
  scripts are written and gated; they are inputs, not deliverables.
- **D3.** A TOML round-trip library (or the decision to own a
  serialiser) is required by the state command (see A2). The specific choice is
  an open question (§9).

## 9. Open questions

- **Q1 — TOML round-trip mechanism.** Which mechanism preserves
  `state.toml` formatting and comments across mutation: a library such as
  `tomlkit`, or an owned serialiser over the standard-library `tomllib` reader?
  - *Why it matters:* gates the state-mutation command's
    implementation and the A2 assumption.
  - *Resolution:* an implementation spike comparing round-trip fidelity
    and a recorded ADR.
  - *Owner:* the contributor building the state command.
- **Q2 — Output contract.** What exact structured-output schema and
  exit-code convention do the deterministic commands share, so the harness can
  gate on them uniformly?
  - *Why it matters:* G2 and the per-turn predicate check depend on a
    consistent machine-readable contract.
  - *Resolution:* settle in the technical design document.
  - *Owner:* design author.
- **Q3 — Device-ledger schema.** What is the per-novel
  `device-ledger.toml` schema (phrase, maximum count, allowed chapters, count
  recomputed from disk), and how is current count derived?
  - *Why it matters:* G8 and the highest-risk manual work in the field
    report depend on it; it gates a later roadmap phase.
  - *Resolution:* design the schema in the technical design document;
    defer enforcement to the relevant phase.
  - *Owner:* design author.
- **Q4 — Line-editor persona boundary.** Where exactly does the new
  micro-level line-editor's remit end and the spiteful critic's begin, given
  that macro show-don't-tell belongs to the critic and knitting circle while
  micro passive/show-tell/filtering belong to the line editor?
  - *Why it matters:* G7; an unclear boundary dilutes both personas.
  - *Resolution:* the design document records the test (can the fix be
    done by rewriting a sentence, or does it require restaging a scene?)
    and the persona prompts are written in a later phase.
  - *Owner:* design author.
- **Q5 — AI-isms versioning cadence.** AI-isms are a moving target and
  are to be held as versioned data. What is the update mechanism, and who
  maintains the rule pack as new tells emerge?
  - *Why it matters:* G8; a stale rule pack silently misses tells.
  - *Resolution:* **Resolved (roadmap 7.1.1).** The `ai-isms.toml` pack ships as
    opt-in versioned data; the update cadence, ownership, and membership policy
    are recorded in the developers' guide ("Rule packs and the loader boundary",
    subsection "The ai-isms pack: cadence, ownership, and membership"). The skill
    maintainer owns the pack, reviews it at least each release, and adds or
    retires a cited, collocational tell by a data edit, never a code change.
  - *Owner:* skill maintainer.

## Appendices

### A. Candidate `docs/context.md` entries

The following domain terms appear in this document and are candidates for
promotion to a ubiquitous-language document when one is created: *Ralph Loop*,
*deterministic spine*, *done predicate*, *desloppify*, *knitting circle*,
*spiteful critic*, *parasocial fangirl*, *device ledger*, *clean-context
sub-agent*, *knitting gate*, *AI-isms rule pack*.

### B. ADR candidates

ADRs are recorded in `docs/`, named `adr-NNN-short-description.md` per the
documentation style guide.

- **Deterministic/judgemental boundary** (G1, G3): the organising
  principle of the rebuild; an ADR fixes it as the project's controlling
  decision.
- **TOML round-trip mechanism** (Q1): hard to reverse once the state
  serialiser is built; warrants an ADR.
- **Shared interface contract** (Q2): the JSON envelope and the
  disambiguated exit-code table (benign negative versus actionable finding); an
  ADR fixes the contract the five commands share.
- **Distribution as installed console-scripts** (C3): settled, but the
  rationale is worth recording as an ADR for future contributors who might
  reach for self-contained `uv` scripts.
- **Command-surface shape**: five separate console-scripts versus a
  single `novel` multiplexer; an ADR records the trade and the decision to ship
  five named commands.

### C. References

- `skill/novel-ralph/SKILL.md` — the skill under rebuild.
- `skill/novel-ralph/references/state-layout.md`,
  `done-conditions.md`, `desloppify-checklist.md`, `critic-personas.md` — the
  reference files whose deterministic operations ship as pseudocode.
- Agent field report supplied with the rebuild request, 2026-06-21.
- `docs/scripting-standards.md`, `AGENTS.md`,
  `docs/documentation-style-guide.md` — governing conventions.

### D. Glossary pointer

No `docs/context.md` exists yet. Until it does, the candidate entries in
Appendix A serve as the working glossary, and the reference files under
`skill/novel-ralph/references/` define the craft terminology.
