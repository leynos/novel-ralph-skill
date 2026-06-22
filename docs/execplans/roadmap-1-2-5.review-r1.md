# Logisphere design review — roadmap 1.2.5 — Round 1

Verdict: REVISE (proceed once the two blocking documentation defects below are
fixed). The technical core is sound and was verified empirically against the
real interrogate 1.7.0 install and the cuprum v0.1.0 tag.

## What was verified (passes)

- interrogate 1.7.0 `fail_under` default is `80.0` (`config.py` line 57). The
  `[tool.interrogate]` table is read via `tool`→`interrogate` (line 133), keys
  normalized `--`/`-`→`_` (lines 133-136), config injected into
  `ctx.default_map` (line 254) so a CLI `--fail-under` overrides it. All
  line-number citations in the plan match.
- Empirical: with `[tool.interrogate] fail-under = 100` and **no** CLI flag,
  `uv run interrogate novel_ralph_skill tests` reports
  `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)`. The central bet (drop the
  literal flag, rely on config) holds. The package is genuinely at 100%.
- Empirical: the full proposed config block (every `ignore-*` key) is accepted
  by interrogate 1.7.0 and keeps `minimum: 100.0%, actual: 100.0%`.
- Empirical: the dev-dependency guard parse
  (`spec.split()[0].split("[")[0] == "interrogate"`) returns `True` against the
  real `dependency-groups.dev` list; the `fail-under` parse returns `100`.
- cuprum v0.1.0 `__all__` (real tag) contains `ProgramCatalogue`,
  `ProjectSettings`, `Program`, `sh`, `scoped`, `CommandResult` and does **not**
  contain `Catalogue`. The plan's substantive claim is correct (though it
  presents the six as the whole list; the real `__all__` is much larger — this
  is non-load-bearing context only).
- No new dependency; `tomllib` stdlib pattern mirrors the existing
  `test_pyproject_scripts.py` / `test_command_names_registry.py` guards.

## Blocking defects

1. AGENTS.md goes stale and is not in the plan. AGENTS.md line 86 hard-codes
   `interrogate --fail-under 100 $(PYTHON_TARGETS)` as the Makefile invocation.
   Work item 2 removes `--fail-under 100` from the Makefile, which makes that
   AGENTS.md statement factually false. AGENTS.md is tracked and editable in the
   worktree. The plan never lists AGENTS.md as an edit target and never
   reconciles it. Either: (a) add AGENTS.md to the edit set and the file-count
   tolerance, updating line 86 to match the config-sourced threshold; or (b)
   adopt the belt-and-braces option (retain `--fail-under 100` in the recipe) so
   no doc goes stale — which is itself the plan's declared
   Makefile-recipe tolerance trigger, i.e. an escalation, not a silent default.
   As written the plan ships a contradiction between AGENTS.md and the Makefile.

2. Misattributed documentation source — the "design doc GitHub-Actions section"
   does not exist. The plan asserts in multiple places (Purpose/Constraints,
   Surprises, Context, Authoritative sources, and work item 3) that
   `docs/novel-ralph-harness-design.md` has a "GitHub Actions" section
   describing `interrogate --fail-under 100`. It does not: grepping the design
   doc for `interrogate`/`fail-under`/`docstring coverage` returns nothing. The
   literal lives in AGENTS.md line 86 (see defect 1) and in
   `docs/developers-guide.md` lines 12-13. Work item 3 instructs the implementer
   to "reconcile that sentence too" in a section that is absent, which is
   unimplementable as written and will waste the implementer's time hunting a
   phantom. Fix the source map: the two real homes of the literal are
   AGENTS.md and the developers' guide.

## Advisory (non-blocking)

- Guard test false-pass risk (Doggylump). The Makefile guard performs two
  independent substring checks (`"interrogate" in makefile` AND
  `"$(PYTHON_TARGETS)" in makefile`) without verifying they co-occur on the
  recipe line. `$(PYTHON_TARGETS)` appears 8 times in the Makefile, so a future
  edit could delete the interrogate recipe line entirely while some other
  `interrogate` mention survives and the test still passes. The plan flags
  brittleness only in the false-failure direction. Recommend asserting that a
  single line contains both tokens (e.g. iterate lines, assert one line has
  `interrogate` and `$(PYTHON_TARGETS)` together).
- Dev-guide line citation is lines 12-13 (line 11 is blank); the plan's
  "lines 12-13" is correct; the occasional "12-13" vs the prose is fine.

## Recommended next steps

1. Add AGENTS.md to the edit set + file-count tolerance and update line 86, OR
   escalate to belt-and-braces (keep the literal flag). Decide explicitly.
2. Correct every "design doc GitHub-Actions section" reference to name AGENTS.md
   and the developers' guide as the real homes of the literal; drop the
   instruction to edit a non-existent design-doc section.
3. (Advisory) tighten the Makefile guard to a same-line co-occurrence check.
