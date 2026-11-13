# Architectural decision record (ADR) 001: deterministic and judgemental boundary

## Status

Accepted, 2026-06-21. Every operation in the `novel-ralph` harness is placed on
one side of a hard line: deterministic operations become tested installed
commands; judgemental operations go to the model, with the adversarial reads
isolated in clean-context sub-agents.

## Date

2026-06-21.

## Context and problem statement

The `novel-ralph` skill describes a deterministic spine for a Ralph Loop
harness but ships it as pseudocode. A field report from an agent that ran the
skill records two consequences. First, the agent hand-rolled every
deterministic operation — word counts, the done predicate, slop detection —
inconsistently each turn, because no installed command owned the work. Second,
the agent self-marked the judgemental passes too gently, because a context that
has just written twelve chapters cannot read its own prose as a cold reader
would.

Both failures share a root cause: the skill never decided which work is a pure
function of files on disk and which work requires reading prose for quality,
intent, or earned meaning. Without that decision, deterministic work drifts and
judgemental work flatters itself. The rebuild needs the boundary fixed as its
controlling decision before any command or sub-agent is built, because every
later choice — the command surface, the contract, the sub-agent architecture —
follows from where the line sits.

## Decision drivers

- The field report's two named failure modes: inconsistent hand-rolled
  determinism and soft self-marking.
- The need for results that are identical every turn for the mechanical work.
- The need for genuine independence from authorship for the adversarial reads.
- A boundary stable enough that every later slice can cite it without
  renegotiation.

## Requirements

### Functional requirements

- Each harness operation is classified as deterministic or judgemental.
- Deterministic operations run identically every turn and make zero narrative
  judgements.
- Judgemental operations that are adversarial run in a context independent of
  the authoring context.

### Technical requirements

- Deterministic operations are installed, tested commands (see ADR 004).
- The only legal crossing is: a command detects and reports; the model
  adjudicates and edits. No command mutates narrative meaning; no judgemental
  pass writes state or manuscript directly.

## Options considered

### Option A: Fix the boundary as the controlling decision

Classify every operation up front. Deterministic work is owned by installed
commands; judgemental work is owned by the model. The boundary is the first
thing the design states and the thing every later section refers back to.

### Option B: Leave the boundary implicit

Build commands where they seem convenient and let the model do the rest,
deciding case by case. This is the status quo the field report describes.

| Topic                   | Option A: explicit boundary      | Option B: implicit                |
| ----------------------- | -------------------------------- | --------------------------------- |
| Determinism consistency | Guaranteed by installed commands | Drifts, as the field report shows |
| Self-marking risk       | Removed for adversarial reads    | Persists                          |
| Later-slice coherence   | Each slice cites one boundary    | Each slice relitigates it         |
| Up-front design cost    | Higher                           | Lower                             |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A. The non-negotiable rule is: **scripts detect and report; the
model adjudicates.** A command that begins deciding whether a passive
construction is justified has crossed the line and is a defect. Mechanical
verification is delegated to a script, never to a weaker model; adversarial
reading is delegated to a clean-context peer-capability sub-agent, never to a
script. The boundary is drawn in novel-ralph-harness-design.md §1 and
illustrated there.

## Goals and non-goals

- Goals:
  - Fix the deterministic and judgemental split as the project's controlling
    decision.
  - Make the field report's two failure modes structurally impossible.
- Non-goals:
  - Specifying the individual commands (novel-ralph-harness-design.md §4) or
    the sub-agent personas (§7); this ADR fixes only the boundary.

## Known risks and limitations

- A future operation may sit awkwardly on the line — part mechanical, part
  judgemental. The rule resolves this by splitting it: the mechanical part
  becomes a detector, the judgemental part an adjudication.
- The boundary forbids a tempting shortcut — a command that "just flags obvious
  prose problems" — because that is narrative judgement in a script. The cost
  is accepted deliberately.

## Outstanding decisions

None. This ADR is accepted and fixes the boundary. Dependent decisions are
recorded in ADR 002 (TOML round-trip), ADR 003 (interface contract), ADR 004
(distribution), and ADR 005 (command surface).
