# Calibrate the skill for drafting deflation

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 2)

## Purpose / big picture

Beta testing of the novel-ralph skill exposed a systematic shortfall: the
drafting-plus-desloppify loop is net-deflationary. Per-scene estimates ran
~20-30% high, the spiteful critic cut 10-20% per chapter exactly as designed,
chapters landed at 60-85% of their targets, and the finished book reached only
~90% of target (26,990 of 30,000 words) even after a manual expansion pass
(roadmap 6.1.2). The deflation source is documented and deliberate: the
desloppify pass "removes more than it adds … if the chapter loses 10-20% of its
word count to desloppification, that is normal"
(`skill/novel-ralph/references/desloppify-checklist.md:314-315`), and the
spiteful critic cuts further. Nothing in the workflow puts those words back, so
the book finishes short.

This task makes the skill compensate for that deflation so a finished novel
reliably hits its target length. It is a `SKILL.md` workflow change, not a CLI
change: no command behaviour changes; `wordcount` already reports the per-chapter
delta and the percentage-of-target the agent needs (design §4.5;
`docs/execplans/roadmap-6-1-1.md`). The fix is an explicit, measured
**expand-to-target** step woven into the Phase 8 per-chapter loop and the
Phase 9 final pass, driven by the figures `wordcount` already computes.

The mechanism's placement is load-bearing and was reworked in round 2 (see
Decision Log and Revision Note). The Phase 8 expand step sits **before** the
spiteful-critic loop (step e), not after the fangirl pass, because the verified
loop order is strictly sequential — d desloppify, e spiteful-critic loop, f
fangirl, g done (`SKILL.md:358-384`) — and only the critic loop (step e) re-runs
desloppification on edited passages (`SKILL.md:406`). Inserting expansion before
step e routes the freshly written prose through both the critic and the critic
loop's embedded desloppify, so new material is reviewed and cleaned by the
existing machinery rather than smuggled past the quality gate. The step is an
explicit measure-expand-remeasure loop that re-invokes `wordcount` to confirm
the gap closed, and it is confined to the **current chapter only** so it cannot
retroactively move the cumulative drafted ratio across a knitting-gate boundary
(see Constraints). In Phase 9 the expand step is reordered so a destructive
desloppify pass is never the final operation after expansion, and the
novel-scale critic is correctly described as a structural-only pass that does
not line-vet new prose (design §7.2; `SKILL.md:470-491`).

The change is observable two ways. First, a reader of
`skill/novel-ralph/SKILL.md` finds, in the Phase 8 drafting loop and the Phase 9
final pass, an explicit deflation-compensation step that names `wordcount`, a
concrete acceptance band against target, a measure-expand-remeasure loop with a
stated termination/escalation condition, and the rationale for why it exists.
Second, a new in-process guard test (`tests/test_skill_deflation_guard.py`)
asserts that the compensation mechanism is present in `SKILL.md` and fails if a
future edit silently removes it — so the success condition is pinned by a test,
not just by prose that can drift. Because a substring guard cannot detect a
subtly wrong ordering, the prose correctness here is load-bearing and is
reviewed by a human, not delegated to the guard alone.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- This is a documentation-and-test change. Do not modify any module under
  `novel_ralph_skill/`, any console-script entry point, the state schema, or
  the JSON envelope. The roadmap fixes this explicitly: "This is a `SKILL.md`
  workflow change, not a CLI change" (roadmap 6.1.2).
- Do not change the **novel target** itself or the way targets are computed,
  validated, or reported. The STC beat-sheet sum check is "± 10%" of the target
  (`stc-beat-sheet.md:126-127`; SKILL.md Phase 6 exit), the chapter-target
  deltas and percentage-of-target in `wordcount` are computed against the real
  target (design §4.5), and the knitting gates fire at 30/50/80% of the real
  target (SKILL.md Phase 8). Inflating the target would corrupt all three. The
  compensation must operate at draft time against the honest target, not by
  moving the target.
- Preserve the deterministic-and-judgemental boundary (ADR-001,
  `docs/adr-001-deterministic-judgemental-boundary.md`): scripts detect and
  report (`wordcount` supplies the figures); the model adjudicates and writes
  prose (the expansion is a model judgement). The new step must read from
  `wordcount`, never re-derive or hand-compute word totals, and must not invite
  any hand-edit of `state.toml` (design §4.1; ADR-002).
- Preserve the verified Phase 8 loop order and its quality gate. The loop is
  strictly sequential — c write, d desloppify, e spiteful-critic loop, f fangirl,
  g done (`SKILL.md:358-384`) — and the **only** place desloppification re-runs
  on edited prose is inside the critic loop ("Re-run desloppification on edited
  passages", `SKILL.md:406`). Therefore any newly written substantive prose must
  enter the loop **before** step e, so it is critiqued and desloppified by the
  existing machinery. The expand step is inserted between step c (write beats)
  and step d (desloppify), as a new measure-expand-remeasure sub-step; do **not**
  insert it after the fangirl pass (between f and g), because at that point the
  critic loop has already converged and new prose would reach `done.flag`
  unreviewed. Accept that the critic may cut some of the expanded material; the
  measure-expand-remeasure loop re-measures with `wordcount` after the critic and
  fangirl passes and the expand step runs again on the next loop iteration only
  if the chapter is still short — it does not chase the band inside a single pass
  against a critic that has not yet run.
- Expansion is destructive-aware. Desloppify "removes more than it adds … 10-20%"
  (`desloppify-checklist.md:314-315`), so the expand step must not assume the
  words it adds survive. The step is specified as an explicit
  measure → expand → (let d/e/f run) → re-measure loop driven by `wordcount`,
  with a stated termination/escalation condition (see Work item 2), not a
  one-shot "expand then desloppify" that silently loses 10-20% of exactly the
  material it added. There is no separate mandatory desloppify re-run bolted onto
  the new prose; the standard step d and the critic loop's embedded desloppify do
  that cleaning, and the re-measure proves whether the band was met after they
  cut.
- Preserve knitting-gate monotonicity. The three knitting gates fire on the
  **cumulative drafted ratio** crossing 30/50/80% of target, checked after each
  chapter completes (SKILL.md Phase 8; design §4.5), and `set-gate` refuses to
  assert a gate true below its `drafted_ratio` threshold or false once crossed
  (the `gate-ratio-consistent` invariant in
  `novel_ralph_skill/commands/_gate_drafting_mutators.py:142-182`). Phase 8
  expansion is therefore confined to the **current** chapter (the one not yet
  carrying `done.flag`); it must not re-open an already-done earlier chapter,
  because doing so would raise the cumulative ratio out of drafting order and
  could newly satisfy a gate ahead of its sequence. Because chapters draft in
  order and expansion only grows the current chapter before its `done.flag`, the
  cumulative ratio stays monotonic in drafting order and gate ordering is
  preserved. Phase 9 expansion happens after all three knitting gates are already
  set true, so it can only raise the ratio further — it cannot un-cross a gate
  (gates, once true, stay true; the ratio only rises).
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") throughout prose, comments, and
  the commit message (AGENTS.md "Use consistent spelling and grammar").
- `skill/novel-ralph/SKILL.md` must stay within the 80-column prose line limit
  and dash-style bullets enforced by `.markdownlint-cli2.jsonc` (MD013 line
  length 80; MD004 dash).

## Tolerances (exception triggers)

- Scope: if the change requires editing more than 3 files (the SKILL.md, one new
  test module, and the roadmap tick), stop and escalate. The expected surface is
  `skill/novel-ralph/SKILL.md`, `tests/test_skill_deflation_guard.py`, and the
  `- [ ]` → `- [x]` flip of roadmap item 6.1.2 in `docs/roadmap.md`.
- Mechanism: the roadmap offers two mechanisms — inflate Phase 6/7 targets ~+20%,
  or add an explicit expand-to-target step in Phase 8/9. This plan selects the
  expand-to-target step (see Decision Log). If implementation discovers that the
  expand-to-target step cannot be expressed without violating the
  "do not move the target" constraint, stop and escalate rather than switching to
  target inflation silently.
- New runtime dependency: none is permitted. If one seems required, stop and
  escalate (it should not — the guard test reads `SKILL.md` text in process via
  the existing `read_repo_text` fixture, `tests/conftest.py:146`).
- Iterations: if `make markdownlint`, `make nixie`, or `make all` still fails
  after 3 attempts, stop and escalate.

## Risks

- Risk: the guard test pins SKILL.md prose so tightly (an exact sentence or
  heading) that ordinary future wording edits break it, making it brittle.
  - Severity: medium. Likelihood: medium.
  - Mitigation: assert on a small set of stable, lowercased substrings that
    capture the *mechanism* (the presence of an "expand to target" step naming
    `wordcount` in both Phase 8 and Phase 9 regions), not on whole sentences.
    Mirror the established prose-guard pattern in
    `tests/test_state_layout_reference.py`, which scans for a *pattern* rather
    than fixed prose.
- Risk: the expand step is placed where the critic/desloppify machinery does not
  re-run on it, so new substantive prose reaches `done.flag` unreviewed (Phase 8)
  or the final destructive pass re-opens the gap (Phase 9).
  - Severity: high. Likelihood: medium (it is the exact defect round 1 shipped).
  - Mitigation: the Constraints pin the Phase 8 expand step **between step c and
    step d**, so step d (desloppify) and step e (the critic loop, which re-runs
    desloppify on its edits) both process the new prose. In Phase 9 the expand
    step is ordered so desloppify and the structural critic run, then expansion,
    then a final `wordcount` re-measure — never a destructive pass last. The
    guard test cannot detect a wrong insertion point, so the implementer must
    verify the ordering by reading the edited loop end to end (Stage D).
- Risk: the measure → expand step never re-measures, so the band is asserted but
  not confirmed, and the step is untestable and incomplete.
  - Severity: high. Likelihood: medium.
  - Mitigation: the Phase 8 and Phase 9 steps both **end** by re-invoking
    `wordcount` (per ADR-001 the model reads figures, never hand-computes) and
    state an explicit termination/escalation condition: if the chapter is still
    below band after one expand-and-reprocess cycle, the agent escalates rather
    than looping unbounded, and logs the residual deficit for the Phase 9 final
    expand. The prose names `wordcount` as the re-measurement instrument.
- Risk: expanding an already-done earlier chapter raises the cumulative drafted
  ratio across a knitting-gate boundary, satisfying a gate out of drafting
  sequence (`set-gate` refuses below threshold and refuses un-crossing).
  - Severity: high. Likelihood: medium.
  - Mitigation: the Constraints confine Phase 8 expansion to the **current**
    chapter before its `done.flag`; no back-edit of done chapters for length.
    Chapters draft in order, so the ratio stays monotonic and gate ordering is
    preserved. Phase 9 runs after all gates are set, so it cannot un-cross one.
- Risk: the Phase 9 novel-scale critic is mischaracterised as line-vetting the
  newly expanded prose, when by design (`SKILL.md:479-482`) it looks **only** for
  structural issues invisible at chapter scale.
  - Severity: medium. Likelihood: low (now explicit).
  - Mitigation: the Phase 9 prose states the structural-only role plainly and
    routes line/quality cleaning of new prose through the Phase 9 desloppify pass
    that precedes expansion, not through the structural critic.
- Risk: the compensation contradicts the STC ± 10% sum check or the knitting
  gate thresholds by implying the target should move.
  - Severity: high. Likelihood: low.
  - Mitigation: the Constraints forbid moving the target; the step expands the
    *draft* toward the fixed target using the `wordcount` delta, leaving the
    target, the STC sum, and the gate maths untouched.
- Risk: markdownlint MD013 (80-column) breaks on the new prose, or a fenced
  block trips a rule.
  - Severity: low. Likelihood: medium.
  - Mitigation: wrap prose to 80 columns; keep additions inside the existing
    `text` loop fence where they belong; run `make markdownlint` and
    `make nixie` before committing (AGENTS.md markdown gates).

## Progress

- [x] Stage A — research and propose (no edits). (completed: research done,
  including the verified Phase 8/9 loop order and the `set-gate` ratio invariant;
  round-2 revision resolved all five design-review blocking points; mechanism
  approved.)
- [x] Work item 1: add the failing guard test
  `tests/test_skill_deflation_guard.py` (includes the re-measurement
  assertion: `wordcount` appears at least twice in the Phase 8 region).
  Committed together with Work item 2 to keep a green tree per commit.
- [x] Work item 2: weave the expand-to-target step into SKILL.md — Phase 8
  expand step inserted as the new step d, **between the write step (c) and
  desloppify** (renumbered e), current chapter only, with the re-measure at the
  renumbered fangirl step (g) and an explicit log-deficit-and-advance escalation;
  Phase 9 expand step inserted as step 4, **after** the destructive desloppify
  (2) and the structural-only critic (3), recompiling with `novel-compile` and
  re-measuring with `wordcount`. The guard passes; `make all`, `make markdownlint`
  and `make nixie` are green.
- [x] Work item 3: tick roadmap item 6.1.2 and record the rationale (the
  expand-to-target mechanism, the Phase 8/9 insertion points, and the guard
  test) in a `- Done:` annotation under the success criterion.

## Surprises & discoveries

- Observation: the loop steps required renumbering c→d→e→f→g→h, not just an
  insertion, because the expand step lands between the write step and
  desloppify. Evidence: `SKILL.md` Phase 8 fenced loop, the renumbered steps
  e–h. Impact: the prose at step g now references "step d" for the termination
  rule and step d names "steps e–f" for the destructive cuts, keeping the
  cross-references consistent after renumbering.
- Observation: `make markdownlint` and Python lint surfaced two incidental
  issues unrelated to the mechanism — an 81-column line in the untracked
  round-2 review note and two multi-line docstring summaries in the guard test
  (Ruff `missing-blank-line-after-summary`). Evidence: markdownlint MD013 and
  `lint-python`. Impact: wrapped the review-note line and collapsed the two
  docstring summaries to single lines; the deterministic gates went green.
- Observation: coderabbit flagged the `phase_9_region` slicer for assuming a
  trailing H2 heading. Evidence: coderabbit minor finding on
  `tests/test_skill_deflation_guard.py`. Impact: the fixture now falls back to
  end-of-file when Phase 9 is the final section, so the guard survives a future
  removal of the `## State layout summary` section.

## Decision log

- Decision: implement the **expand-to-target step** (the roadmap's second
  option) rather than inflating Phase 6/7 targets by ~+20% (the first option).
  - Rationale: inflating the target would corrupt every figure computed against
    the real target — the STC beat-sheet "± 10%" sum check (SKILL.md Phase 6
    exit; `stc-beat-sheet.md:126-127`), the `wordcount` percentage-of-target and
    chapter-target deltas (design §4.5), and the 30/50/80% knitting gate
    thresholds (SKILL.md Phase 8) — turning an honest 30,000-word target into a
    dishonest 36,000-word one that the reader-fit and beat planning were never
    sized for. The expand-to-target step keeps the target honest and applies
    compensation at the exact point of measured deflation, using figures
    `wordcount` already reports. It also respects ADR-001: detection is scripted
    (`wordcount`), expansion is model judgement.
  - Date/Author: 2026-06-26, planning agent.
- Decision: pin the success criterion with an in-process guard test rather than
  relying on prose alone.
  - Rationale: the roadmap success criterion is "`SKILL.md` carries an explicit
    deflation-compensation mechanism … with the rationale recorded". A
    prose-only change can silently regress. The repo already guards skill prose
    this way (`tests/test_state_layout_reference.py` forbids a banned recipe in
    the reference). AGENTS.md requires "behaviour changes are fully validated by
    relevant … tests"; a doc workflow guard is the matching instrument here.
  - Date/Author: 2026-06-26, planning agent.
- Decision: place the Phase 8 expand step **between step c (write beats) and
  step d (desloppify)**, not after the fangirl pass, and confine it to the
  current chapter.
  - Rationale: round 1 inserted it between f and g, which is internally
    contradictory — the critic loop (step e) has already converged there, so new
    prose reaches `done.flag` unreviewed, and the round-1 claim that "the critic
    loop re-runs desloppify there" is false (the critic loop is upstream at step
    e). The verified loop is sequential d→e→f→g (`SKILL.md:358-384`) and the only
    desloppify re-run on edits is inside the critic loop (`SKILL.md:406`).
    Inserting before step d routes new prose through desloppify and the critic
    loop, so it is reviewed and cleaned by the existing machinery. Confining to
    the current chapter keeps the cumulative drafted ratio monotonic so a late
    expansion cannot cross a knitting gate out of sequence
    (`_gate_drafting_mutators.py:142-182`). This resolves design-review blocking
    points 1, 2, and 4.
  - Date/Author: 2026-06-26, planning agent (round 2).
- Decision: specify the expand step as an explicit measure → expand → reprocess
  → re-measure loop with a stated termination/escalation condition, and drop the
  round-1 "re-run desloppify on the new prose" instruction.
  - Rationale: desloppify is destructive ("removes 10-20%",
    `desloppify-checklist.md:314-315`), so a one-shot expand-then-desloppify
    silently loses much of what it added and never confirms the band. Per ADR-001
    the model must read figures from `wordcount`, so the closure check is a
    re-invocation of `wordcount` after step d/e/f cut, not a hand-computed total.
    A single bounded cycle plus escalation avoids unbounded looping against a
    critic that legitimately trims. This resolves blocking points 2 and 3.
  - Date/Author: 2026-06-26, planning agent (round 2).
- Decision: reorder Phase 9 so expansion precedes nothing destructive and a final
  `wordcount` re-measure closes the pass, and describe the novel-scale critic as
  structural-only.
  - Rationale: round 1 placed expansion "before the last desloppify and critic
    passes", leaving the destructive desloppify (Phase 9 step 2) to re-open the
    gap with nothing after it to re-measure, and implied the novel-scale critic
    (step 3) line-vets new prose. But step 3 is explicitly structural-only
    (`SKILL.md:479-482`) and step 2 is destructive. The fix runs desloppify and
    the structural critic first, then the expand-to-target pass over the weakest
    chapters, then a final `wordcount` re-measure, so no destructive operation
    follows expansion. This resolves blocking point 5.
  - Date/Author: 2026-06-26, planning agent (round 2).
- Decision: make no cuprum or external-library behavioural claim.
  - Rationale: this task touches only `SKILL.md` prose and one in-process text
    guard that uses the existing `read_repo_text` fixture
    (`tests/conftest.py:146`). It invokes no console script, no cuprum
    catalogue, and no third-party runtime behaviour, so there is nothing to pin
    against the locked cuprum version or against Cyclopts/uv/pytest-timeout
    docs. The standing research mandate is conditional on the plan relying on
    such behaviour; this plan does not.
  - Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

Outcome: the roadmap 6.1.2 success criterion is met. `SKILL.md` carries an
explicit deflation-compensation mechanism — the expand-to-target step — with the
rationale recorded inline (the net-deflationary drafting-plus-desloppify loop,
the unchanged honest target), and `tests/test_skill_deflation_guard.py` pins its
presence so a future edit cannot silently remove it. The mechanism choice
(expand-to-target, not target inflation) keeps the STC ± 10% sum check, the
`wordcount` percentage-of-target, and the 30/50/80% knitting-gate thresholds
honest.

Retrospective: the plan's red-green discipline held — the guard failed against
the unedited `SKILL.md` and passed after the edit. The load-bearing insertion
points (Phase 8 step d before desloppify; Phase 9 step 4 after the structural
critic) were verified by reading the edited loops end to end (Stage D), since
the substring guard cannot prove ordering. Three coderabbit minor findings were
addressed: a more robust end-of-file fallback in `phase_9_region`, and two
impersonal-phrasing edits in the planning docs. No module under
`novel_ralph_skill/`, no console script, and no state schema changed; the
surface stayed within the planned files (`SKILL.md`, the guard test, the roadmap
tick) plus the execplan and its round-2 review note.

## Context and orientation

You are working in the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-2`, on branch
`roadmap-6-1-2`. Treat `docs/` as the source of truth.

The skill is a single Markdown file plus reference files:

- `skill/novel-ralph/SKILL.md` — the workflow the model follows to write a
  novel. The relevant regions are **Phase 8 — Drafting (the inner Ralph loop)**
  (`SKILL.md:353-468`), whose per-chapter loop is a fenced ```text``` block
  listing steps a-g (`SKILL.md:358-384`), and **Phase 9 — Final pass**
  (`SKILL.md:470-491`), a numbered list ending in `novel-done` exits 0.
- `skill/novel-ralph/references/desloppify-checklist.md` — the destructive pass
  that is the documented source of the deflation (lines 312-320). Read this to
  understand why expansion must come *after* desloppify, not instead of it.
- `skill/novel-ralph/references/critic-personas.md` — the spiteful critic that
  cuts further. Expansion runs after the critic clears.
- `skill/novel-ralph/references/stc-beat-sheet.md` — the beat-sheet sum check is
  "± 10%" of the target (lines 126-127). This is why the target must not move.

Terms of art, defined:

- **Deflation** — the manuscript finishing systematically shorter than its
  target because desloppify and the spiteful critic cut more than the draft and
  expansion add. Documented at `desloppify-checklist.md:312-316`.
- **Expand-to-target step** — a new, explicit drafting sub-step in which the
  model reads the `wordcount` delta against target and, where the draft is short
  of an acceptance band, writes *additional substantive material* (a missing
  beat, an exchange, an interiority pass) — never padding — to close the gap. In
  Phase 8 it runs on the **current chapter** between the write step (c) and
  desloppify (d), so the standard desloppify and the spiteful-critic loop then
  review and clean the new prose; after they cut, the loop re-invokes `wordcount`
  to confirm the band was met. It does not carry a separate mandatory desloppify
  re-run — that would discard 10-20% of what it just added without confirming the
  result; the existing step d and critic loop do the cleaning and the re-measure
  proves closure. In Phase 9 it runs after the final desloppify and the
  structural critic, over the weakest chapters by `wordcount` delta, followed by
  a final `wordcount` re-measure (no destructive pass after it).
- **`wordcount`** — the read-only checker that reports per-chapter and cumulative
  words, percentage of target, distance to the next knitting gate, and delta
  against the chapter target (design §4.5; `docs/execplans/roadmap-6-1-1.md`).
  It already supplies every figure the expand-to-target step needs; the step
  consumes it, it is not changed.

Validation tooling: `make all` runs build, format check, lint, typecheck, and
tests (Makefile `all:` target). For Markdown changes, `make markdownlint` lints
all `*.md` and `make nixie` validates Mermaid (AGENTS.md "Markdown files"). The
guard test runs under `make test` (`pytest -v -n …`).

## Plan of work

The work proceeds red-green: a failing guard test first (Work item 1), then the
SKILL.md edit that makes it pass (Work item 2), then the roadmap tick (Work
item 3). Each work item is independently committable and gate-passable.

### Stage A — understand and propose (no edits)

Confirm the mechanism choice (expand-to-target, not target inflation) with the
user via the approval gate. The Decision Log records the rationale. Do not edit
files until approved.

### Work item 1 — add the failing deflation guard test

Create `tests/test_skill_deflation_guard.py`. It reads `SKILL.md` in process
via the `read_repo_text` fixture (`tests/conftest.py:146`) — no subprocess, no
import of `novel_ralph_skill`, mirroring `tests/test_state_layout_reference.py`.

It asserts, case-insensitively, that the deflation-compensation mechanism is
present and recorded:

1. The string `expand to target` (or a normalised variant such as
   `expand-to-target`) appears in `SKILL.md`.
2. An expand-to-target step appears within the **Phase 8** region (between the
   `### Phase 8` heading and the `### Phase 9` heading) and names `wordcount` as
   its source of the delta.
3. The Phase 8 region also contains a re-measurement cue: `wordcount` appears at
   least twice in that region (the measure and the re-measure), so a step that
   only reads the delta but never confirms closure cannot pass. (The guard cannot
   prove the re-measure is positioned correctly — that is a human-review item per
   Stage D — but it forbids the trivially incomplete "read delta, expand, done".)
4. An expand-to-target / final-length check appears within the **Phase 9**
   region (from `### Phase 9` to the next level-two heading) and names
   `wordcount`.
5. The rationale is recorded: a sentence near the step references the
   deflation/desloppify cut (assert the region contains both `deflation` — or
   `deflationary` — and a reference to the target).

Split the SKILL.md text into the Phase 8 and Phase 9 regions by heading offsets
(pure string slicing over the file text), then assert the substrings within each
region. Keep the assertions to stable *mechanism* substrings, not whole
sentences, per the brittleness mitigation in Risks. Note explicitly in the
module docstring that the guard cannot detect a wrong **insertion point** (e.g.
the expand step placed after the fangirl pass instead of before desloppify) or a
wrong **Phase 9 ordering** (expansion after a destructive pass); those are
load-bearing prose-correctness properties verified by human review at Stage D,
not by the substring guard. Add a module docstring (the
repo enforces 100% docstring coverage via interrogate, AGENTS.md "Linting") that
cites roadmap 6.1.2 and the design sections, and per-function docstrings that do
not merely restate the assertion (AGENTS.md "Illustrate with clear examples":
test docstrings omit examples that only restate logic).

Documentation to read first: `tests/test_state_layout_reference.py` (the prose-
guard pattern), `tests/conftest.py:146-166` (the `read_repo_text` fixture),
AGENTS.md "Quality gates" and "For Python files".

Skills to load: `python-router` first, then follow it to `python-testing` for
the pytest fixture/region-slicing structure. No property-based, mutation, or
symbolic-execution adversary is warranted: this is a deterministic substring
guard over a fixed file (design §9 matches method to need — a pure check earns
only example coverage), so do **not** reach for `hypothesis`, `crosshair`, or
`mutmut` here.

Tests this item adds: the guard module itself. There is no behavioural, snapshot,
property, or e2e suite to add — the change has no runtime surface (design §9: the
method is matched to what the property needs; a documentation invariant needs a
single deterministic guard).

Acceptance for this item: with `SKILL.md` unedited, the new test **fails**
(the `expand to target` mechanism is absent today). Run:

```bash
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-2
make test PYTEST_ARGS='tests/test_skill_deflation_guard.py' 2>&1 | tail -20
```

Expect the new test to fail (red). If `make test` does not accept
`PYTEST_ARGS`, run the whole `make test` and confirm the new test id appears as
failing. Commit the failing test on its own (red commit) only if the project
convention permits a red commit; otherwise hold it and combine with Work item 2
so the committed tree always passes its gates. **Gate before committing:**
`make all` — note the new test is expected to fail until Work item 2 lands, so
if a green tree is required at every commit, commit Work items 1 and 2 together.

### Work item 2 — weave the expand-to-target step into SKILL.md

Edit `skill/novel-ralph/SKILL.md` in two places. Read the verified loop at
`SKILL.md:358-410` and Phase 9 at `SKILL.md:470-491` before editing; the
insertion points below are exact and load-bearing.

**Phase 8 loop** (`SKILL.md:358-384`). In the fenced ```text``` per-chapter
loop, insert a new sub-step **between step `c` (write beats) and step `d`
(desloppify)** — NOT after the fangirl pass. The verified loop is sequential
(d desloppify → e critic loop → f fangirl → g done) and the only place
desloppification re-runs on edits is inside the critic loop (`SKILL.md:406`), so
the expand step must precede step d for the new prose to be desloppified and
critiqued by the existing machinery. Renumber the trailing steps (the old d-g
become e-h). The new step must:

- Run `wordcount` and read the **current chapter's** delta against its chapter
  target and its percentage-of-target (it must read these figures, never
  hand-compute them — ADR-001).
- Where the current chapter is below an explicit acceptance band (state the band,
  e.g. within 5% of the chapter target), write *additional substantive material*
  (a missing beat, an interiority pass, a richer exchange), never padding, into
  the current chapter's draft. Apply it **only to the current chapter** — never
  re-open an already-`done.flag` earlier chapter for length (this preserves
  knitting-gate monotonicity; see Constraints).
- Let the renumbered desloppify and critic-loop steps run on the expanded draft
  as normal (the loop already does this), then, as the loop reaches the
  re-measure point, run `wordcount` **again** to confirm the chapter now sits
  within the band after the destructive passes have cut.
- State the termination/escalation condition explicitly: if after one
  expand-and-reprocess cycle the chapter is still below band, do **not** loop
  unboundedly — record the residual deficit (it will be picked up by the Phase 9
  final expand pass) and advance. This bounds the loop and keeps the per-chapter
  turn finite.

Because the fenced loop is a single linear block, express the re-measure as part
of the expand sub-step's text (e.g. "after steps d-e have run, re-run
`wordcount`; if still short, log the deficit and continue") rather than adding a
second fenced block. Add one prose paragraph after the fenced block explaining
the *why*: the drafting-plus-desloppify loop is net-deflationary (cite the
10-20% desloppify cut, `desloppify-checklist.md:314-315`, and the spiteful
critic), so without an explicit expand step the book finishes short of target;
the step closes the gap at chapter time, before the critic reviews it, using the
figures `wordcount` reports, against the unchanged target.

**Phase 9 final pass** (`SKILL.md:470-491`). Do **not** place expansion before
the destructive passes. The verified Phase 9 order is: 1 concatenate, 2
desloppify (destructive), 3 one structural-only critic pass ("looking only for
structural issues invisible at chapter scale", `SKILL.md:479-482` — it does NOT
line-vet newly written prose), 4 verify final image, 5 complete-final-pass.
Insert the expand-to-target step **after** step 3 (the structural critic) and
**before** step 4 / `complete-final-pass`, and make it self-closing:

- Run `wordcount` over the assembled `compiled.md` and read the cumulative total
  against the novel target.
- If the book is short of the target band, perform a final expand-to-target pass
  across the weakest chapters (identified by their `wordcount` deltas), writing
  substantive material, not padding.
- Because expansion edits individual `chapter-NN/draft.md` files (where
  `wordcount` reads its per-chapter counts from disk — verified in
  `novel_ralph_skill/state/_disk_word_counts.py`), the `compiled.md` assembled at
  step 1 is now stale; regenerate it with `novel-compile` before the closing
  re-measure, mirroring the knitting pass's recompile discipline
  (`SKILL.md:459-462`).
- Then run `wordcount` **once more** to confirm the cumulative total now sits
  within the band — so the destructive desloppify (step 2) and the structural
  critic (step 3) have already run and nothing destructive follows the expansion
  to re-open the gap. If still short after the pass, escalate (do not silently
  ship a short book).

Do not imply the structural critic (step 3) quality-checks the expanded prose;
state that line/quality cleaning of any new Phase 9 prose is the responsibility
of the agent applying desloppify discipline as it writes, since the structural
critic by design does not.

Keep all prose within 80 columns; keep the Phase 8 additions inside the existing
fenced loop where they belong; use dash bullets. Record the rationale inline (the
guard test asserts it is present) and ensure the en-GB Oxford spelling holds.

Documentation to read first: the verified Phase 8 loop and critic loop
(`SKILL.md:358-410`, especially the sequential d-g order and the
"Re-run desloppification on edited passages" line at `SKILL.md:406`); the
verified Phase 9 steps 1-5 (`SKILL.md:470-491`, especially the structural-only
critic at `SKILL.md:479-482`); design §4.5 (what `wordcount` reports); design
§7.2 Figure 3 (the per-chapter pipeline order desloppify → critic → fangirl →
wordcount/recount → gate check); `desloppify-checklist.md:314-315` (the
10-20% destructive cut); the knitting-gate `set-gate` ratio invariant
(`novel_ralph_skill/commands/_gate_drafting_mutators.py:142-182`) to confirm why
expansion is confined to the current chapter; ADR-001 (the detect/adjudicate
boundary — the model reads `wordcount` figures and never hand-computes totals).

Skills to load: none beyond the general en-GB and execplan discipline — this is
Markdown prose. Do **not** load a language router for this item (no code is
edited). Load `en-gb-oxendict` discipline mentally; the spelling rule is in
AGENTS.md.

Tests this item updates: it makes `tests/test_skill_deflation_guard.py` pass
(green). No other test should change behaviour; confirm the full suite still
passes (the SKILL.md regions are also scanned by
`tests/test_state_layout_reference.py` and `tests/working_corpus/_specs.py`, so
run the whole suite to catch any incidental prose-guard interaction).

Acceptance for this item: the guard test passes, and the markdown gates are
clean. Run, in order:

```bash
cd /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-2
make markdownlint 2>&1 | tail -5
make nixie 2>&1 | tail -5
make all 2>&1 | tail -20
```

Expect `make markdownlint` and `make nixie` to report success and `make all`
(including the new guard test, now green) to pass. **Gate before committing:**
`make all`, `make markdownlint`, `make nixie` (AGENTS.md markdown gates).
Commit Work items 1 and 2 together if a green-tree-per-commit policy applies.

### Work item 3 — tick the roadmap and record the rationale

Edit `docs/roadmap.md`: flip roadmap item 6.1.2 from `- [ ]` to `- [x]`
(`docs/roadmap.md:1625`). Do not alter the surrounding sub-bullets except, if the
project convention is to annotate completion, append a one-line note that the
mechanism chosen was the expand-to-target step (not target inflation) and that
`SKILL.md` plus `tests/test_skill_deflation_guard.py` carry it. Keep within 80
columns and dash style.

Documentation to read first: nearby completed roadmap items (e.g. 6.1.1 at
`docs/roadmap.md:1614`) for the house annotation style.

Skills to load: none (Markdown edit).

Tests this item adds: none. The roadmap is documentation.

Acceptance for this item: `make markdownlint` passes on `docs/roadmap.md` and
`make all` stays green. **Gate before committing:** `make markdownlint`,
`make nixie`, `make all`.

### Stage D — hardening and cleanup

Re-read the edited Phase 8 and Phase 9 regions end to end as a novice would.
Because the substring guard cannot detect a wrong insertion point, explicitly
confirm by reading the prose:

- Phase 8: the expand step sits **between step c and step d**, applies only to
  the current chapter, and the loop re-runs `wordcount` after the desloppify and
  critic steps with a stated escalation when still short. New substantive prose
  is therefore desloppified (step d) and critiqued (step e) before `done.flag`.
- Phase 9: the expand step runs **after** the destructive desloppify (step 2) and
  the structural-only critic (step 3), and is followed by a `wordcount`
  re-measure — no destructive operation follows expansion — and the prose does
  not claim the structural critic line-vets new prose.
- Gate safety: no instruction re-opens an already-`done.flag` chapter for length.

Confirm no module under `novel_ralph_skill/` changed (`git status` shows only the
expected files). Confirm the commit message is imperative, en-GB, references
roadmap 6.1.2 and the design sections.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-2`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-2 \
     branch --show-current
   ```

   Expect `roadmap-6-1-2`.

2. Write `tests/test_skill_deflation_guard.py` (Work item 1). Confirm it fails
   against the unedited SKILL.md (red).

3. Edit `skill/novel-ralph/SKILL.md` Phase 8 and Phase 9 (Work item 2). Re-run
   the guard test; expect green.

4. Run the markdown gates and the full suite:

   ```bash
   make markdownlint && make nixie && make all
   ```

   Expect all green.

5. Tick `docs/roadmap.md` item 6.1.2 (Work item 3). Re-run `make markdownlint`
   and `make all`.

6. Commit with an imperative, en-GB message referencing roadmap 6.1.2, design
   §4.5/§7.2, and `desloppify-checklist.md`.

## Validation and acceptance

Behaviour to observe:

- A reader of `skill/novel-ralph/SKILL.md` finds an explicit expand-to-target
  step in the Phase 8 per-chapter loop **between the write step (c) and
  desloppify (d)**, confined to the current chapter, that runs `wordcount`,
  expands where short, and re-runs `wordcount` to confirm closure with a stated
  escalation if still short; and a Phase 9 step that runs **after** the final
  desloppify and the structural critic, expands the weakest chapters, and
  re-measures with `wordcount` (no destructive pass after it). Each names
  `wordcount`, each cites an acceptance band against the unchanged target, and a
  paragraph records why the step exists (the net-deflationary
  drafting-plus-desloppify loop).
- `tests/test_skill_deflation_guard.py` fails before the SKILL.md edit and passes
  after — the red-green proof that the success criterion is pinned by a test.

Quality criteria (what "done" means):

- Tests: `make all` passes, including the new
  `tests/test_skill_deflation_guard.py`. No existing test regresses.
- Lint/format/typecheck: subsumed by `make all` (it runs `check-fmt`, `lint`,
  `typecheck`, `test`).
- Markdown: `make markdownlint` and `make nixie` both pass.
- No CLI/runtime surface changed: `git status` shows only
  `skill/novel-ralph/SKILL.md`, `tests/test_skill_deflation_guard.py`, and
  `docs/roadmap.md` (plus this execplan).

Quality method (how we check): run, from the worktree root,
`make markdownlint && make nixie && make all`, and inspect `git status`.

## Idempotence and recovery

Every step is a file edit or a re-runnable command; none is destructive. Re-
running `make all`, `make markdownlint`, or `make nixie` is safe. If the
SKILL.md edit is wrong, revert the file with `git checkout -- skill/novel-ralph/
SKILL.md` and redo. If the guard test is brittle, loosen its substrings (Risks)
rather than weakening the SKILL.md mechanism. No backups beyond git are needed.

## Artifacts and notes

Key facts pinned during research:

- Deflation source: `desloppify-checklist.md:312-316` — "If the chapter loses
  10-20% of its word count to desloppification, that is normal."
- Insertion points: SKILL.md Phase 8 loop fence (`SKILL.md:358-384`, steps a-g);
  the expand step goes **between c and d** (verified sequential order d→e→f→g,
  critic-loop desloppify re-run at `SKILL.md:406`). Phase 9 numbered list
  (`SKILL.md:470-491`); the expand step goes **after** step 3 (structural-only
  critic, `SKILL.md:479-482`) and before step 4 / `complete-final-pass`.
- Knitting-gate monotonicity: `set-gate` refuses a knitting gate true below its
  `drafted_ratio` threshold or false once crossed
  (`novel_ralph_skill/commands/_gate_drafting_mutators.py:142-182`), so Phase 8
  expansion is confined to the current chapter.
- `wordcount` already reports the delta-against-target and percentage figures the
  step consumes (design §4.5; `docs/execplans/roadmap-6-1-1.md`).
- Prose-guard precedent: `tests/test_state_layout_reference.py` with the
  `read_repo_text` fixture (`tests/conftest.py:146`).

## Interfaces and dependencies

No code interface changes. The only new artefact is a test module:

`tests/test_skill_deflation_guard.py` — pure, in-process, reads SKILL.md text via
the existing `read_repo_text` fixture from `tests/conftest.py`. It defines test
functions (no new public production API) that slice the SKILL.md text into the
Phase 8 and Phase 9 regions by heading and assert the expand-to-target mechanism
and its recorded rationale appear in each. It adds no third-party dependency:
pytest and the existing fixtures suffice.

No cuprum API, console-script, or external-library behaviour is relied upon (see
Decision Log); there is nothing to pin against the locked cuprum version or the
Cyclopts / uv / pytest-timeout documentation.

## Revision note

Round 1 (2026-06-26): initial draft. Selected the expand-to-target mechanism
over target inflation (Decision Log), scoped the change to SKILL.md plus an
in-process prose-guard test and the roadmap tick, and recorded that no cuprum or
external-library behavioural claim is made.

Fix round 1 (2026-06-26): resolved two dual-review blocking findings against
the implemented SKILL.md.

- Phase 8 headroom (finding 1): the round-2 step d expanded the draft to within
  5% of the chapter target *before* the destructive desloppify and critic passes
  and re-measured *after* them. Because desloppify removes 10–20%
  (`desloppify-checklist.md:314-315`) and the critic cuts further, a chapter
  expanded only to the band pre-cut lands 15–25% short post-cut, so the step g
  re-measure essentially always failed the band and the single-cycle bound fired
  the log-and-advance escalation on nearly every chapter — structurally unable to
  converge at chapter time and deferring the deflation Phase 8 exists to fix onto
  Phase 9 every chapter (defeating the Decision Log rationale, lines 272–298).
  Fixed by instructing step d to OVER-expand the pre-cut draft to roughly
  115–125% of the chapter target — budgeting the anticipated
  desloppify-plus-critic loss as deliberate headroom on top of any shortfall — so
  the chapter lands within the band *after* the cuts. The why-paragraph after the
  fenced loop now states this headroom rationale explicitly.
- Phase 9 band (finding 2): step 4 referenced "the target band" / "within the
  band" three times but never defined a Phase 9 threshold, leaving the agent no
  closure/escalation criterion. Fixed by stating an explicit **97–103% (within
  3%)** acceptance band and reconciling it with the STC ± 10% sum check
  (`stc-beat-sheet.md:126-127`): the ± 10% bounds the *planned* beat targets, the
  3% bounds the *finished* manuscript, both against one unchanged target, so the
  two figures are not in silent tension.
- Gating: the deflation guard test and `make all` stayed green (1170 passed);
  `make markdownlint` and `make nixie` passed; `coderabbit review --agent`
  returned 0 findings. Committed atomically (SKILL.md only).

Round 2 (2026-06-26): resolved all five design-review blocking points after
verifying the loop and gate code.

- Ordering (point 1): moved the Phase 8 expand step from "after fangirl, before
  done.flag" to **between step c (write) and step d (desloppify)**, because the
  verified loop is sequential d→e→f→g and the critic loop's desloppify re-run is
  at `SKILL.md:406`; at the f→g point the critic has already converged, so new
  prose would reach `done.flag` unreviewed. Updated the Constraint, the Risks
  ordering entry, Work item 2, Validation, and Artifacts accordingly.
- Destructive re-run (point 2): dropped the "re-run desloppify on the new prose"
  instruction (it would discard 10-20% of the added material) and replaced it
  with a measure → expand → reprocess (via the existing d/e) → re-measure loop;
  the existing step d and critic loop do the cleaning.
- Re-measurement / termination (point 3): both Phase 8 and Phase 9 steps now end
  by re-invoking `wordcount` (ADR-001: read figures, never hand-compute) and
  state an escalation when still short after one cycle. The guard test now also
  asserts `wordcount` appears twice in the Phase 8 region.
- Knitting-gate interaction (point 4): added a Constraint and Risk confining
  Phase 8 expansion to the **current** chapter (no back-edit of done chapters),
  grounded in the `set-gate` ratio invariant
  (`_gate_drafting_mutators.py:142-182`); Phase 9 expansion runs after all gates
  are set so it cannot un-cross one.
- Phase 9 mischaracterisation (point 5): reordered the Phase 9 expand step to run
  **after** the destructive desloppify (step 2) and the structural-only critic
  (step 3), followed by a closing `wordcount` re-measure, and stopped implying
  the structural critic line-vets new prose (`SKILL.md:479-482`).

Remaining work: user approval, then Work items 1-3.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews of the deflation-calibration change. Execute each as a small addendum
pass — no plan or design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. These are the small,
surgical guard and prose fixes only; the substantial empirical band-calibration
work (instrumentation and a beta-replay convergence fixture) was rerouted to
roadmap step 7.34, because it does not advance step 6.1's disk-derivation
hypothesis.

- [x] 6.1.2.1 — Add an ordering-aware structural assertion to the deflation
  guard (from review:6.1.2; severity: low; two near-identical proposals merged).
  The current substring guard cannot detect a wrong insertion point or
  re-measure placement and leaves the load-bearing ordering to human Stage-D
  review (Risks entry 2; module docstring caveat). Add a lightweight ordinal
  check over the file offsets: in the Phase 8 region, assert the second
  `wordcount` mention falls **after** the `desloppify` step heading; in the
  Phase 9 region, assert the expand step's offset falls **after** the
  structural-critic step's offset and **before** `complete-final-pass`, so a
  destructive pass can never sit last after expansion. Mechanise the ordering
  property the guard currently leaves to manual review, reducing regression risk
  on future `SKILL.md` refactors. Confine the change to
  `tests/test_skill_deflation_guard.py`.
- [x] 6.1.2.2 — Strengthen the deflation guard to pin the over-expansion /
  headroom cue (from review:6.1.2; severity: low). The guard passes on
  `wordcount` appearing twice plus the mechanism name, so it would pass even
  with the convergence defect that fix-round-1 corrected (a pre-cut draft
  expanded only to the band lands short after the destructive cut). Add a stable
  mechanism substring asserting the Phase 8 region budgets the destructive cut as
  deliberate headroom (an over-expand / 115–125% / headroom cue), narrowing the
  gap between what the guard pins and the load-bearing prose-correctness
  property. Confine the change to `tests/test_skill_deflation_guard.py`.
- [x] 6.1.2.3 — Reconcile the Phase 8→Phase 9 residual-deficit handoff prose
  with the artefacts actually produced (from review:6.1.2; severity: low). The
  Phase 8 escalation defers a short chapter's deficit to "the Phase 9 final
  expand pass",
  but no log artefact or state field carries that handoff; Phase 9 re-derives it
  from `wordcount`. Adjust the `SKILL.md` prose so it does not imply an artefact
  that is not produced — make explicit that Phase 9 re-derives the deficit from
  `wordcount` rather than reading a deficit log — keeping the workflow prose
  truthful. A formal deficit log or state field is deliberately out of scope (it
  would touch the schema, which 6.1.2 forbids). Confine the change to
  `skill/novel-ralph/SKILL.md` and, if the wording shifts a guarded substring, to
  `tests/test_skill_deflation_guard.py`.
