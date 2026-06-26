# Post-merge audit — roadmap task 6.1.2

Audit of the codebase after roadmap task 6.1.2 ("calibrate the skill for
drafting deflation") merged to `main` at commit `b41e957`. The slice is
prose-and-test only: it weaves an explicit **expand-to-target** step into the
agent-facing [`SKILL.md`](../../skill/novel-ralph/SKILL.md) — a new sub-step
`d` in the Phase 8 per-chapter loop (before the destructive desloppify and
spiteful-critic passes) and a new step `4` in the Phase 9 final pass (after
those destructive passes) — to compensate for the net-deflationary
drafting-plus-desloppify loop, and pins the mechanism with a substring guard,
[`tests/test_skill_deflation_guard.py`](../../tests/test_skill_deflation_guard.py).
No `novel_ralph_skill` source changed; the console-script contract, the state
schema, the STC sum check, and the knitting-gate maths are all untouched by
design (the deliberate choice was to grow the draft toward the honest target,
not to inflate the target).

The change is well reasoned and the guard is honest about its own limits. None
of the findings below is a blocking defect; all are low-to-medium hygiene
items. The dominant theme is a **documentation-locality** gap: the slice
introduces three load-bearing numeric policy bands — the Phase 8 chapter band
(within 5% of the chapter target after cuts), the Phase 8 over-expansion target
(115–125% of the chapter target before cuts), and the Phase 9 finished-novel
band (97–103% of the novel target) — that live only in the agent-facing
`SKILL.md` and have no home in the canonical design doc, which `AGENTS.md`
names as the source of truth. The remaining items are a self-acknowledged
ordering/insertion-point test gap, a minor inconsistency between the two
finished-tolerance bands, and the usual fragile-prose-coupling note.

Trail followed: created a `git worktree` off `origin/main`; explored with
`leta` (`leta files`, `leta grep`, `leta show`) over `tests/conftest.py`,
`commands/_wordcount.py`, and `commands/_wordcount_report.py`; traced history
with `git show b41e957 --stat` and `sem`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §4.5 and §5, `docs/users-guide.md`,
`docs/developers-guide.md`, the ExecPlan `docs/execplans/roadmap-6-1-2.md`, the
referenced `skill/novel-ralph/references/desloppify-checklist.md` and
`stc-beat-sheet.md`, prior `docs/issues/audit-6.1.1.md`, and `AGENTS.md`.
Loaded the `leta`, `sem`, and `python-router` skills. Ran the new guard under
`uv run --frozen python -m pytest tests/test_skill_deflation_guard.py` (5
passed). Each finding records a category, location, description, concrete
proposed fix, and severity.

## Finding 1 — Deflation policy and its three numeric bands live only in `SKILL.md`, not the design doc

- Category: docs-gap
- Severity: medium
- Location:
  [`skill/novel-ralph/SKILL.md`](../../skill/novel-ralph/SKILL.md) Phase 8
  sub-step `d` (lines ~371–411) and Phase 9 step `4` (lines ~524–550);
  [`docs/novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
  §4.5 (`novel wordcount`, lines 430–436).

The 6.1.2 slice introduces a genuinely new operating policy — the
net-deflationary drafting loop is compensated by an explicit expand-to-target
step — and three load-bearing numeric bands that govern it: the Phase 8 chapter
acceptance band (within 5% of the chapter target *after* the destructive
passes), the Phase 8 over-expansion target (roughly 115–125% of the chapter
target *before* the cuts, budgeting the expected 15–25% desloppify-plus-critic
loss), and the Phase 9 finished-novel band (97–103% of the novel target). All
three appear only in the agent-facing `SKILL.md`. The design doc's §4.5 still
describes `wordcount` purely as a reporter (words, percentage of target,
distance to the next knitting gate, delta against the chapter target) and never
mentions deflation, the expand step, or any acceptance band; a `grep` for
`deflat`/`expand`/`97` over `docs/` and `references/` finds the concept only in
the ExecPlan and the roadmap. `AGENTS.md` names `docs/` as the source of truth,
so a numeric policy that exists only downstream in the prompt has no canonical
home: a future reader reconciling the design against the skill cannot tell
whether the 5%/3%/115–125% figures are intentional or drift, and a future band
change has nowhere to be recorded but the prompt itself.

Proposed fix: add a short subsection to the design doc — most naturally
extending §4.5 (`novel wordcount`), since the bands are read off the figures
`wordcount` already reports — that records (a) the net-deflationary finding from
beta testing, (b) the chosen compensation (expand the draft, hold the target
fixed), and (c) the three bands with their rationale (why 115–125% pre-cut, why
the finished tolerance is tighter than the planning ±10%). `SKILL.md` then
becomes the operational rendering of a design-doc-anchored policy rather than
its sole source. Cross-reference the new subsection from the `SKILL.md` Phase 8
rationale paragraph.

## Finding 2 — Guard cannot pin the load-bearing ordering or insertion point of the expand step

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_skill_deflation_guard.py`](../../tests/test_skill_deflation_guard.py)
  (`TestDeflationGuard`, all five tests).

The guard is candid in its own module docstring that it "cannot detect a wrong
insertion point (for example, the Phase 8 expand step placed after the fangirl
pass instead of before desloppify) or a wrong Phase 9 ordering (expansion
following a destructive pass)", deferring those to human review. Yet the
correctness of the entire mechanism rests precisely on that ordering: the Phase
8 expand must run *before* desloppify and the critic so they can clean the new
prose (the rationale paragraph is explicit that this is what keeps new material
inside the quality gate), and the Phase 9 expand must run *after* the
destructive passes so nothing re-opens the gap. The guard asserts only that the
strings "expand to target" and "wordcount" are present in each region and that
"wordcount" appears at least twice in Phase 8; a refactor that reorders the
lettered steps so the expand step lands after the critic would leave every
assertion green while silently breaking the mechanism the slice exists to
deliver.

Proposed fix: add two ordering assertions that operate on offsets within the
already-sliced regions — in Phase 8, assert the first index of "expand to
target" precedes the first index of "desloppify"; in Phase 9, assert the
"expand to target" index follows the "spiteful critic" (or "structural")
index. These remain substring-level (no parsing of the prose) and stay within
the file-text discipline the module already uses, but they convert the
load-bearing ordering from "human review only" into a pinned property. The
module docstring should then be narrowed to note that only the *fine* placement
(e.g. which lettered sub-step) remains human-verified.

## Finding 3 — Two finished-tolerance bands (5% chapter, 3% novel) coexist without a stated relationship

- Category: inconsistency
- Severity: low
- Location:
  [`skill/novel-ralph/SKILL.md`](../../skill/novel-ralph/SKILL.md) Phase 8
  sub-step `d` ("within 5% of its target") and Phase 9 step `4` ("97–103% of
  the novel target ... within 3%").

The slice introduces two distinct finished-tolerance bands: each chapter must
land within 5% of its chapter target after cuts, while the assembled novel must
land within 3% of the novel target. Phase 9 carefully explains why its 3% band
differs from the STC beat-sheet's planning ±10% (plan versus delivered book),
but it never reconciles the 3% novel band against the 5% per-chapter band — and
the two are in mild arithmetic tension: a set of chapters each sitting at the
edge of their individual 5% bands need not sum to within 3% of the novel total
(systematic bias in one direction would breach the tighter aggregate band even
when every chapter is "in band"). The reader is left to infer whether the 5%
chapter band is deliberately looser because Phase 9 is the backstop that tightens
the aggregate, or whether the mismatch is incidental.

Proposed fix: add one sentence to the Phase 8 sub-step `d` (or to the design-doc
subsection proposed in Finding 1) stating the relationship explicitly — i.e.
that the per-chapter 5% band is the loose, per-chapter contract and the Phase 9
3% band is the tighter aggregate backstop that catches any systematic
per-chapter bias the looser band admits, which is *why* the Phase 9 final expand
pass exists. This closes the inference gap without changing either number.

## Finding 4 — Phase-loop steps are coupled by hand-maintained letter cross-references

- Category: ergonomics
- Severity: low
- Location:
  [`skill/novel-ralph/SKILL.md`](../../skill/novel-ralph/SKILL.md) Phase 8 loop,
  sub-step `d` ("Steps e–f are destructive", "run wordcount AGAIN at step g",
  "After steps e–f have run") and sub-step `g` ("see termination rule in step
  d").

Inserting the new expand step re-lettered the Phase 8 loop from `a–g` to `a–h`,
and the new prose now cross-references sibling steps by letter four times
(`e–f`, `step g`, `step d`). The references are correct as written (verified:
`e` desloppify and `f` critic are the destructive pair, `g` is the fangirl-plus-
re-measure step, `d` carries the termination rule). But letter coupling is
brittle: any future insertion or removal of a step shifts the letters and
silently invalidates every reference, and the substring guard (Finding 2) does
not check them. This is a pre-existing house style for the loop, not a 6.1.2
regression, so it is noted lightly.

Proposed fix: when this loop is next edited, prefer naming the referenced steps
by their role ("the destructive desloppify and critic passes", "the fangirl
re-measure step") rather than by letter, so the references survive
re-lettering. Apply opportunistically rather than as a standalone change.

## Finding 5 — User and developer guides do not mention the expand/deflation discipline

- Category: docs-gap
- Severity: low
- Location:
  [`docs/users-guide.md`](../../docs/users-guide.md) (the `novel wordcount` and
  drafting-loop sections); [`docs/developers-guide.md`](../../docs/developers-guide.md).

Both guides describe `novel wordcount` as the read-only reporter (words,
percentage, deltas, gate distances) and the drafting commands, but neither
mentions that the agent now reads those deltas to drive an explicit
expand-to-target step, nor the deflation finding that motivates it. This is
defensible — the guides are scoped to the *command surface*, and the
expand step is agent behaviour driven from `SKILL.md`, not a new verb or flag —
so it is genuinely low severity. It is recorded only because a reader of the
users' guide who sees `wordcount` report a large negative chapter delta has no
pointer to what the harness does about it.

Proposed fix: if Finding 1 is actioned (a design-doc subsection on deflation
compensation), add a one-line cross-reference from the users' guide `wordcount`
section noting that the harness uses the reported delta to expand short chapters
toward target during drafting, pointing at the design subsection and `SKILL.md`
Phase 8. No command-surface documentation changes are needed.
