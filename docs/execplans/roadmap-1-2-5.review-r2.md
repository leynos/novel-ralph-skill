# Logisphere design review — roadmap 1.2.5 — Round 2

Verdict: REVISE. One blocking defect: the edit set is incomplete. A fifth home of
the `--fail-under 100` literal — `docs/users-guide.md` line 18 — is unreconciled,
which recurs the exact failure class round 1 raised against AGENTS.md and breaches
the plan's own file-count tolerance. The technical core is sound and was
re-verified empirically against the real interrogate 1.7.0 install.

## Round-1 follow-up (resolved)

- Defect 1 (AGENTS.md staleness): resolved. AGENTS.md line 86 is now in the edit
  set (Tolerances, work item 2, Decision Log), reconciled in the same commit as
  the Makefile change, file-count tolerance raised to 7, a high-severity
  documentation-staleness risk added, option (b) recorded as escalation-only.
- Defect 2 (phantom design-doc "GitHub Actions" section): resolved. Verified by
  grep that `docs/novel-ralph-harness-design.md` contains zero hits for
  `interrogate`/`fail-under`/`docstring cover` (exit 1). All phantom references
  are removed; the only remaining mention (line 951) is the revision note
  correctly recording their removal. The design doc is dropped from the edit set.
- Advisory (guard false-pass): resolved. The Makefile guard now asserts same-line
  co-occurrence of `interrogate` and `$(PYTHON_TARGETS)` (work item 2 step 2,
  illustrative code at lines 889-897). Verified `$(PYTHON_TARGETS)` appears 8
  times, so the tightening is load-bearing.

## What was re-verified empirically (passes)

- `interrogate, version 1.7.0` on PATH via uv (matches `uv.lock`).
- Baseline: bare `uv run interrogate novel_ralph_skill tests` reports
  `RESULT: PASSED (minimum: 80.0%, actual: 100.0%)` — the 80.0% default and the
  package's genuine 100% are both confirmed.
- Central bet: with the plan's exact `[tool.interrogate]` block appended
  (`fail-under = 100` plus every `ignore-*` set to `false`) and **no** CLI flag,
  the run reports `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)`. The config
  governs the threshold; the full block is accepted by 1.7.0; the gate stays at
  100%. (Tested in a temp copy; tracked `pyproject.toml` left unmodified.)
- Interrogate source citations all match: `fail_under = attr.ib(default=80.0)`
  (config.py:57); `tool`→`interrogate` read with `--`/`-`→`_` key normalization
  (parse_pyproject_toml, lines 133-135); config injected via
  `ctx.default_map.update(config)` (read_config_file:254, so a CLI `--fail-under`
  overrides — the rationale for dropping the literal); `find_project_root` (83),
  `find_project_config` (111), `read_config_file` (196).
- Dev-dependency guard parse returns `True` against the real
  `dependency-groups.dev` (bare names, no specs). The `fail-under` parse returns
  `100`. The `tomllib` pattern mirrors the existing `test_pyproject_scripts.py`.
- cuprum v0.1.0 note is non-load-bearing context; the static-parse guard touches
  cuprum nowhere. No new dependency.
- Line citations confirmed: AGENTS.md 86; dev-guide 12 and 157; Makefile 96;
  CI `make lint` at ci.yml:45; design doc zero hits.

## Blocking defect

1. **Incomplete edit set: `docs/users-guide.md` line 18 is a fifth, unreconciled
   home of the literal.** An exhaustive `git grep` for the literal across tracked
   files (excluding execplans and `uv.lock`) returns FIVE homes, not the three the
   plan repeatedly enumerates:
   - `Makefile:96` (the source being changed)
   - `AGENTS.md:86` (in the edit set)
   - `docs/developers-guide.md:12` and `:157` (in the edit set)
   - **`docs/users-guide.md:18` (NOT in the edit set)**

   Lines 17-18 of the users' guide read: "The `lint-python` target runs Ruff,
   then Interrogate with `interrogate --fail-under 100 $(PYTHON_TARGETS)` to
   enforce 100% docstring coverage…". This is the user-facing description of what
   `lint-python` actually runs. When work item 2 drops `--fail-under 100` from the
   Makefile recipe, this statement becomes factually false — the precise outcome
   the plan's own **high-severity, high-likelihood "documentation goes stale"
   risk** (lines 216-230) describes, and which it claims to prevent by reconciling
   "all three prose statements … in the same change … so the docs and recipe never
   disagree at any committed HEAD". There is a fourth prose statement, and it is
   not reconciled. As written, the option-(a) path ships exactly the
   recipe-versus-doc contradiction the plan asserts it eliminates.

   The plan's source map is therefore still factually wrong, in the same class as
   round-1 defect 1: it asserts in the Purpose (lines 48-50), Constraints,
   Surprises (lines 285-288), Decision Log (lines 337-339), and Context that "the
   two real homes of the literal are AGENTS.md and the developers' guide" — that
   enumeration omits the users' guide.

   Secondary consequence: adding `docs/users-guide.md` makes the edit set SEVEN
   files besides this plan (eight total), which hits the plan's own Tolerances
   trigger ("more than 7 files … stop and escalate", lines 130-131) and exceeds
   the enumerated "six besides this plan". The plan must either widen the
   tolerance and edit-set enumeration to include the users' guide, or escalate.

   **Fix:** add `docs/users-guide.md` (lines 17-18) to the edit set — Purpose
   source map, Tolerances file list (raise the count and the prose), the
   "documentation goes stale" Risk enumeration, Context and orientation, and a
   work item (it is a Markdown doc, so the editing work item must also run
   `make markdownlint` and `make nixie`). State once, drop the `--fail-under 100`
   literal, and name `[tool.interrogate]` as where the threshold lives, exactly
   as for AGENTS.md and the developers' guide. Alternatively, escalate to
   option (b)
   (retain the literal in the recipe) so no doc goes stale — but that is the
   declared Makefile-recipe escalation trigger, not a silent default.

## Advisory (non-blocking)

- The four prose homes (AGENTS.md, dev-guide x2, users-guide x1) are not machine-
  pinned by the guard test, so future re-introduction of a literal in prose would
  not fail `make test`. This is consistent with the repo's other guards (none pin
  prose) and is acceptable; flagged only so the planner does not assume the guard
  protects the docs from re-drift. No action required for 1.2.5.
- Pre-existing, out of scope: `docs/developers-guide.md:155` says CI "sets up
  Python 3.13" while `pyproject.toml` requires `>=3.14`. Do not fix here — it is
  unrelated to the interrogate gate and outside 1.2.5's fence.

## Pre-mortem (Doggylump)

It is the next implementation cycle. A contributor reads `docs/users-guide.md`,
sees `interrogate --fail-under 100 $(PYTHON_TARGETS)`, copies it into a pre-commit
hook, and is later confused when the Makefile recipe shows no such flag — or worse,
a reviewer cites the users' guide as evidence the gate is "still on the CLI" and
reverts the config-as-source-of-truth migration. Blast radius: documentation
contradiction shipped at a committed HEAD, the exact integrity failure the plan
set out to prevent. Signal missed: the plan grepped the design doc (correctly) and
AGENTS.md and the dev-guide, but never ran an exhaustive repo-wide grep for the
literal, so the users' guide was invisible. Prevention designed in now: a
mandatory `git grep` for the literal across all tracked docs before declaring the
edit set complete, and the users' guide added to that set.

## Strongest alternative (Wafflecat)

Option (b) — retain `--fail-under 100` in the recipe as belt-and-braces and leave
all four prose docs untouched — is the credible alternative and the plan already
records it. It trades the "single source of truth" elegance for zero doc-staleness
risk and a one-file change. Given that round 2 has now surfaced a *fourth*
unreconciled prose home (after round 1 surfaced AGENTS.md), the cost of
option (a) is demonstrably "every doc that quotes the recipe must be hunted and
edited, and missing one ships a contradiction". That is precisely the friction
option (b) avoids. This is not a reason to overrule the planner's chosen
default, but it is a reason the planner should weigh: if a fifth grep had found
a sixth home, the file
budget would blow again. Option (a) is defensible only if the edit set is now
provably exhaustive (it is, per the `git grep` above: five homes, no more).

## Recommended next steps

1. Add `docs/users-guide.md` (lines 17-18) to the edit set: Purpose source map,
   Tolerances (raise file count to 8 / "seven besides this plan", update prose),
   the "documentation goes stale" Risk enumeration, Context, and a work item that
   also runs `make markdownlint` and `make nixie`.
2. Correct every "the two real homes" / "AGENTS.md and the developers' guide"
   enumeration to read "AGENTS.md, the developers' guide, and the users' guide".
3. Re-run an exhaustive `git grep -niE 'interrogate.*(fail.under|100)'` (excluding
   execplans and `uv.lock`) and record in the plan that it returns exactly the
   five homes, proving the edit set is complete before option (a) is committed.
