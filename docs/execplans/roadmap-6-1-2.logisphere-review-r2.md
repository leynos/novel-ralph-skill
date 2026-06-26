# Logisphere design review — roadmap 6.1.2 (round 2)

Reviewer: adversarial design panel (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-26.

## Verdict

Proceed with conditions. The round-2 revision genuinely resolves the five
round-1 blocking points, each verified against source. No blocking defect
remains. Three advisory items should be tightened before or during
implementation; none gates the plan.

## Claims verified against source (all confirmed)

- Phase 8 loop is strictly sequential c→d→e→f→g, and the **only** desloppify
  re-run on edits is inside the critic loop (`SKILL.md:358-384`, `:406`). The
  plan's insertion point (between c and d) is correct and load-bearing.
- Deflation source: `desloppify-checklist.md:314-316` — "removes more than it
  adds … 10–20% … is normal". Quoted accurately.
- `set-gate` refuses a knitting gate true below its `drafted_ratio` threshold or
  false once crossed (`_gate_drafting_mutators.py:141-183`, `_refuse_if_incoherent`,
  §5.2 `gate-ratio-consistent`). The current-chapter-only confinement is sound.
- `wordcount`/`recount_words` reads each chapter's `draft.md` from disk, never
  `compiled.md` (`state/wordcount.py:86-105`). Cumulative re-measure is correct.
- Phase 9 step 3 is structural-only ("looking only for structural issues
  invisible at chapter scale", `SKILL.md:479-482`); the plan no longer claims it
  line-vets new prose.
- `read_repo_text` fixture exists (`tests/conftest.py:147`; plan cites 146 — a
  one-line drift, harmless). Prose-guard precedent is real
  (`tests/test_state_layout_reference.py`).
- Roadmap item 6.1.2 is at `docs/roadmap.md:1625`; 6.1.1 at `:1614`. Correct.
- `wordcount` is one of the five console-scripts SKILL.md declares, invoked by
  bare name (`SKILL.md:28-41`); the bare-name prose is consistent with the
  skill's own convention. (`novel` is the sole pyproject entry point, but that
  pre-existing inconsistency is outside this task's scope.)
- No cuprum, Cyclopts, uv, or pytest-timeout behavioural claim is made; the
  Decision Log entry is honest. The plan touches only SKILL.md prose and one
  in-process text guard. No external-library pin is required.

## Advisory findings (not blocking)

1. (Doggylump / Telefono) **Phase 9 recompile rationale is muddled.** Work item
   2 sequences "regenerate `compiled.md` with `novel-compile` before the closing
   re-measure", implying the recompile makes the re-measure accurate. It does
   not: `wordcount` reads `draft.md`, so the count is correct with or without the
   recompile. The recompile is still required — Phase 9's exit needs a current
   `compiled.md` — but for artefact freshness, not measurement. The implementer
   must not write the false "recompile so the count is right" causation into
   SKILL.md. State it as: re-measure (reads drafts), then recompile so the
   shipped `compiled.md` reflects the expanded drafts. Order is the implementer's
   to get right; the plan's stated reason is wrong.

2. (Dinolump) **Red commit conflicts with AGENTS.md.** AGENTS.md:100/108 forbid
   committing changes that fail any gate; a standalone failing guard test
   (Work item 1) fails `make test`. The plan offers "combine Work items 1 and 2"
   only as a conditional fallback. It should be the directive: Work items 1 and
   2 land in one commit. Tighten the plan's wording from "if a green tree is
   required" to "AGENTS.md requires a green tree, so commit 1 and 2 together".

3. (Buzzy Bee) **`make test PYTEST_ARGS=...` is not wired.** The Makefile test
   target (`Makefile:115-116`) hardcodes `pytest -v -n $(PYTEST_XDIST_WORKERS)`
   with no `$(PYTEST_ARGS)` interpolation, so the round-1-red acceptance command
   silently runs the full suite. The plan already hedges this, but the printed
   command is misleading. Drop `PYTEST_ARGS` or run a direct
   `uv run pytest tests/test_skill_deflation_guard.py` for the targeted red check.

## Pre-mortem (Doggylump)

- Scenario A — *the guard passes but the ordering is wrong.* The substring guard
  cannot see insertion point. The plan correctly designates Stage D human review
  as the backstop and the guard docstring must say so. Mitigation present.
- Scenario B — *future wording edit breaks the guard.* Mitigated by asserting
  stable mechanism substrings, mirroring `test_state_layout_reference.py`.
- Scenario C — *implementer writes the false recompile causation (advisory 1)
  into SKILL.md.* Mitigation: fix the rationale in the plan before implementing.

## Alternatives checkpoint (Wafflecat)

The rejected alternative (inflate Phase 6/7 targets +20%) is correctly rejected:
it would corrupt the STC ±10% sum check, the `wordcount` percentage-of-target,
and the 30/50/80% gate maths, all computed against the honest target. A second
alternative — a deterministic `wordcount`-driven *escalation* that hard-fails a
short book at Phase 9 — was not considered, but it is weaker: it detects without
repairing, leaving the deflation unaddressed. The chosen expand-to-target
mechanism is the right call. No credible structural alternative outranks it.

## Conclusion

The design is implementable and design-conformant as written, modulo the three
advisory tightenings. Recommend the planner fold advisory 1 (false recompile
causation) and advisory 2 (mandatory combined commit) into the plan text so the
implementer cannot regress them.
