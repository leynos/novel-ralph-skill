# Logisphere design review — roadmap 6.2.3 ExecPlan — Round 1

Verdict: REVISE. The plan's substantive direction (consolidate the done
predicate onto `novel-done`) is design-conformant, but several load-bearing
factual premises are false on this branch, and two stated success/validation
criteria are unachievable or mis-describe the toolchain. These go back to the
planner.

## Blocking defects

1. Wrong commit citation / false chronology. The plan asserts defects (1) and
   (3) were "already fixed by commit `8d4a07c` before the design suite landed"
   and instructs the implementer to "cite commit `8d4a07c`" in the design §8
   edit. `8d4a07c` is NOT in this branch's history
   (`git merge-base --is-ancestor 8d4a07c HEAD` returns false; it lives only on
   `origin/skill-turn-around`). The Phase-8 label and absent `plan.md` ARE
   already present on this branch, but they arrived via `916313c` ("Establish
   novel-ralph design suite"), not `8d4a07c`. Citing `8d4a07c` would write a
   dangling/incorrect provenance reference into the design doc.

2. `grep -rn "novel_predicate" skill/ docs/` returns no match is unachievable
   in scope. The plan makes this its headline success criterion (WI2, Concrete
   steps, Validation). But `novel_predicate` also appears in
   `docs/roadmap.md:929,937` (closed addendum records 3.1.1.1/3.1.1.2) and in
   `docs/execplans/roadmap-3-1-1*.md`. The plan edits only five files and none
   of those. The criterion as written can never pass; either it must be scoped
   to the two files actually edited (`grep` in `skill/` only, or excluding the
   roadmap addenda and execplans), or the plan must justify why those mentions
   are out of scope. As stated it is a false gate.

3. `make all` does not run the markdown gates or audit. The plan repeatedly
   says `make all` runs "format check, lint, typecheck, markdownlint, nixie,
   tests, audit" (Purpose, Risks, Concrete steps, Validation). `Makefile:28`:
   `all: build check-fmt lint typecheck test` — no `markdownlint`, no `nixie`,
   no `audit`. The markdown gates are separate targets run on their own per
   AGENTS.md §"Markdown guidance". The plan's "run `make all` to prove the docs
   change passes the markdown gates" is incorrect; for a `.md`-only change
   AGENTS.md scopes validation to `make markdownlint` + `make nixie`. Correct
   the toolchain description and the acceptance section.

4. Work Item 3's reconciliation rationale rests on a false premise. The plan
   says the developers-guide §580-586 note can be "resolved as done" because
   "the pseudocode that iterated the outline is gone". But `done-conditions.md`
   already iterates the manifest (`state["chapters"]`, lines 157-160),
   reconciled by roadmap 3.1.1.1 — it never iterated the outline at WI2 time.
   The §580-586 note is therefore ALREADY factually stale independent of this
   plan (it describes a `done-conditions.md` state that no longer exists).
   Repointing §562-564 is still correct and necessary, but the plan must fix
   the rationale so the implementer does not record an incorrect "this plan
   performed the reconciliation" narrative. The reconciliation was 3.1.1.1's.

## Advisory (non-blocking, but address)

- Design §8 self-description vs reality. §8 (lines 774-779) explicitly states
  "the reference files still carry these defects … not a claim that the
  reference files are already fixed." On disk, SKILL.md already reads "Phase 8"
  and `plan.md` is already absent, so §8's framing is already inconsistent with
  the tree. The plan's WI1 should treat §8's editing as correcting a framing
  that is stale by content (verify by content, which the plan does), and should
  NOT lean on the §8 cited line numbers (`SKILL.md:107/304`,
  `state-layout.md:38`) as if authoritative — they are stale (Phase-8 text is
  at line 106-107; the design-suite headings shifted). The plan flags this as a
  risk, which is good; ensure WI1 records the actual provenance commit
  (`916313c`) rather than `8d4a07c`.

- "Keep the section heading so existing links survive" (WI2). No in-repo link
  targets the `## Done predicate (short form)` anchor (grep finds only prose
  mentions of "short-form", not anchor links). Keeping the heading is harmless,
  but the stated justification ("so existing links survive") is unsupported; do
  not let it constrain the edit if removing the heading reads better.

## What is sound

- The core direction — reduce both prose predicate copies to a pointer at
  `novel-done`, making the command + developers-guide six-clause table the
  single source of truth — is exactly what design §332-333 and §8 mandate and
  is consistent with ADR-001's deterministic/judgemental boundary.
- Constraint 4 (preserve phase-level/chapter-level conditions and the BLOCKER
  resolution convention) is correct and well justified; those are genuinely
  distinct artefacts (verified in `done-conditions.md` §32-143, §191-202).
- Repointing developers-guide §562-564 off the `done-conditions.md` pseudocode
  is necessary once WI2 lands; the dependency ordering (WI1 → WI2 → WI3) is
  sound.
- Documentation-only scoping and the Markdown-gate validation choice are
  correct per AGENTS.md (modulo defect 3's mis-statement of `make all`).

## Trail followed

docs/novel-ralph-harness-design.md §8/§4.2/§332-345; ADR-001;
docs/developers-guide.md §"Done predicate"; docs/roadmap.md 3.1.1.x/6.2.3;
skill/novel-ralph/SKILL.md; skill/novel-ralph/references/done-conditions.md;
state-layout.md; AGENTS.md §"Markdown guidance"; Makefile targets; git history
(`8d4a07c`, `916313c`, branch topology).
