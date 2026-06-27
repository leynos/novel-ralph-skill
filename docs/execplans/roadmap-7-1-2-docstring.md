# Consolidate the `CompiledComparison` absent-file projection prose into one authoritative docstring (roadmap 7.1.2)

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

The harness decides one question in three production sites: "is
`working/manuscript/compiled.md` the ordered concatenation of the present
chapter drafts?" The answer is a three-valued verdict —
`CompiledComparison.ABSENT`, `.MATCHES`, or `.DIVERGES` — produced by the single
production helper
`novel_ralph_skill.state.compile_model.compiled_matches_drafts`. Each consumer
projects that verdict to its own *absent-file polarity*: the §5.4 disk-evidence
detector treats an absent `compiled.md` as vacuously satisfied; the `novel-done`
content clause and the `novel-compile --check` surface treat absent as
not-current.

Earlier roadmap slices removed the *code* duplication of this comparison: 3.1.3
routed all consumers through the one helper, and 7.1.1 extracted a named
`compile_is_current(verdict)` content-polarity predicate so the `MATCHES`-only
test lives once. But the *prose* that explains the three-valued verdict and the
two opposite absent-file polarities is still copied across multiple docstrings.
A future change to either polarity must currently be re-stated in several places
or they drift. `docs/issues/audit-3.1.3.md` Finding 3 first flagged this;
`docs/issues/audit-4.1.2.md` Finding 3 recorded that 4.1.2 added a further copy
and proposed the same remediation.

A round-1 design review established that those audits' "four docstrings"
enumeration is **stale**: it pre-dates roadmap task 7.1.1, which added
`compile_is_current` (`novel_ralph_skill/state/compile_model.py` lines 90-119)
whose docstring now carries a *full restatement of both polarities*. A fresh
survey of the current tree (WI0; see "Survey of the current tree" below) finds
the polarity/projection prose lives in **six** docstrings, not four. This plan
is built on that survey, not the stale enumeration.

After this change a reader gains a *single authoritative* description of the
three-valued verdict and the two opposite absent-file polarities, living in the
shared seam's docstring (`compiled_matches_drafts`). `compile_is_current` keeps
its own content-polarity statement (it *is* the named content-polarity seam) but
drops its restatement of the detector's *opposite* polarity, which is
unambiguously shared prose, and cross-references the authoritative docstring.
Each consumer docstring carries only a one-sentence note of *which* polarity it
projects, cross-referencing the authoritative docstring for the full table.
Reading the docstrings shows this working: exactly one
(`compiled_matches_drafts`) states the full projection table with both
polarities; no other docstring restates the *other* caller's polarity.

This is a documentation-only change. No runtime behaviour changes; no function
signature, return type, exit code, or control flow is touched. The success
criterion is observable purely through the docstring text and a green `make
all`.

## Survey of the current tree (authoritative inventory)

This inventory was produced by reading the four named source files and grepping
them for every docstring that names a polarity, the absent-as-satisfied
contrast, the three-valued verdict, or the `only MATCHES` / `both ABSENT and
DIVERGES` framing. It is the factual basis for the work items below and
supersedes the audits' stale "four docstrings" count. The implementer re-runs
the grep in WI0 to confirm nothing has shifted.

1. `compile_model.py` lines 48-59 — `CompiledComparison` class docstring. States
   *why three states, not a bool* ("an absent `compiled.md` is distinct from a
   present-but-stale one … each caller projecting it to its own absent-file
   polarity"). It **references** the per-caller polarity but does **not** restate
   the full table or either caller's mapping. This is the type's own rationale.
   Handled by a defended exemption (B3; Decision Log), not trimmed.
2. `compile_model.py` lines 90-119 — `compile_is_current`. States the content
   polarity in full (lines 93-100: "only `MATCHES` … both `ABSENT` and
   `DIVERGES` are not") **and** the detector's opposite polarity in full (lines
   102-107: "The §5.4 detector deliberately uses the **opposite** polarity
   inline … an absent compile is vacuously satisfied … a genuinely different
   projection"). This is the central round-1 finding (B1). Handled by WI1b.
3. `compile_model.py` lines 122-176 — `compiled_matches_drafts`. The chosen
   **authoritative** docstring. Lines 132-135 state both polarities but name only
   *two* consumers. WI1a completes it (names all three consumers; states both
   polarities crisply).
4. `done_predicate.py` lines 213-261 — `compile_consistent`. States its own
   content polarity, routes through `compile_is_current` (line 228), **and**
   restates the detector's opposite polarity in full (lines 233-236). Handled by
   WI2.
5. `_compile.py` lines 166-208 — `check_compiled`. States its own content
   polarity (exit-code mapping) **and** restates the detector's opposite polarity
   (lines 185-187: "the **opposite** polarity to the §5.4 … detector"). Handled
   by WI4.
6. `disk_evidence.py` lines 193-208 — `_check_compiled_matches_drafts`. **Already
   a self-projection**: shared-seam reference + D-READ read-and-join rule + its
   OWN polarity (`DIVERGES` = violation, `ABSENT` trivially satisfies) +
   oracle-twin note. It does **not** restate the other caller's polarity and
   carries **no** full three-valued table. This is the round-1 B2 finding: the
   prose the old WI3 claimed to remove does not exist. Handled by WI3, which at
   most adds an explicit cross-reference sentence.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Documentation-only. The plan must change *only* docstring text in the named
  functions. No edit may alter any statement, expression, return value,
  control-flow branch, signature, type annotation, decorator, import, or
  module-level constant. If a desired prose change appears to require a code
  change, stop and escalate (it does not — see Risks).
- No behaviour change. Every existing test must pass unchanged; the plan adds no
  test that asserts new runtime behaviour, because there is none. The existing
  projection pins (below) already lock the behaviour and must stay green:
  - `tests/test_compiled_matches_drafts.py` (the helper's three verdicts and
    fault boundary).
  - `tests/test_disk_evidence.py::test_compiled_matches_drafts_projection` (the
    detector's `DIVERGES`-only polarity).
  - `tests/test_compile_check_unit.py` (the `check_compiled` `MATCHES`-only
    polarity; `ABSENT`/`DIVERGES` → exit `4`).
  - `tests/test_done_predicate.py::test_compile_consistent_present_coherent_and_absent`
    (the `compile_consistent` `MATCHES`-only polarity).
  - `tests/test_compile_check_agreement.py` (the `--check`/`compile_consistent`
    agreement over corpus fixtures).
- 100% docstring coverage gate (`interrogate`, `fail-under = 100` in
  `pyproject.toml` `[tool.interrogate]` line 309, run by `make lint-python`).
  Every public module, class, and function must keep a non-empty docstring.
  Trimming a docstring to one or two sentences is fine; deleting it is not —
  interrogate would fail.
- en-GB Oxford spelling ("-ize" / "-yse" / "-our") in all docstring prose and the
  commit message (AGENTS.md "Use consistent spelling and grammar"; the
  `en-gb-oxendict` skill). The existing docstrings already follow this; preserve
  it.
- The authoritative docstring must remain truthful to the design: the §5.4
  detector's *opposite* polarity (absent = vacuously satisfied) and the
  content-clause/`--check` polarity (only `MATCHES` is current) are both correct
  for their different jobs and must both be described accurately
  (`docs/novel-ralph-harness-design.md` §4.3 lines ~320-344, §5.4 lines ~629;
  `docs/issues/audit-3.1.1.md` Finding 2).
- `compile_is_current` remains the named *content-polarity* seam (roadmap 7.1.1,
  `audit-4.1.2.md` Finding 1). WI1b must **keep** its content-polarity statement
  (that is its contract) and remove only its restatement of the detector's
  *opposite* polarity (the shared prose), leaving a cross-reference. It must not
  be reduced below a non-empty docstring, and its `Parameters`/`Returns` blocks
  stay intact.
- The `compile_model.py` module must stay within the AGENTS.md 400-line limit
  (it is currently 245 lines; this change is net-neutral to slightly shorter, so
  it stays well under).
- Do not touch the stale, COMPLETE `docs/execplans/roadmap-7-1-2.md` — it is the
  merged plan for the renumbered "per-novel `device-ledger.toml` enforcement"
  task and is unrelated to this work (see Decision Log).

## Tolerances (exception triggers)

- Scope: if implementation appears to require editing any file other than the
  **four source files** below plus this plan and the roadmap checkbox, stop and
  escalate. The four source files are:
  - `novel_ralph_skill/state/compile_model.py` (now touched at two sites:
    `compiled_matches_drafts` in WI1a and `compile_is_current` in WI1b; the
    `CompiledComparison` class docstring is left under a defended exemption — see
    B3 Decision Log)
  - `novel_ralph_skill/state/done_predicate.py`
  - `novel_ralph_skill/state/disk_evidence.py`
  - `novel_ralph_skill/commands/_compile.py`
- Code change: if any non-docstring line must change (logic, signature, import,
  constant, type), stop and escalate — that would exceed the doc-only mandate.
- Test breakage: if any existing test fails after a docstring-only edit, stop and
  escalate (a docstring edit cannot legitimately break a behavioural test; a red
  test means something non-doc was touched, or a test asserts docstring text —
  see Risks for the doctest/text-assertion check, already shown benign in WI0).
- Iterations: if `make all` still fails after 3 fix attempts on a single work
  item, stop and escalate.
- Ambiguity: if the design's two polarities cannot be stated authoritatively
  without appearing to contradict an existing docstring's claim, stop and
  present the conflict.
- Exemption challenge: if a reviewer rejects either the `CompiledComparison`
  class-docstring exemption (B3) or the decision to keep `compile_is_current`'s
  content-polarity statement (B1), stop and escalate rather than guessing a
  second framing.

## Risks

- Risk: a test or doctest asserts the *exact text* of one of the docstrings, so
  trimming it would break the suite.
  Severity: medium
  Likelihood: low
  Mitigation: WI0 greps the test tree for any reference to the docstring
  sentences and for `--doctest` configuration before any edit. The repo runs
  `pytest -v -n …` with no `--doctest-modules` in `pyproject.toml`/`Makefile`
  (confirmed by round-1 review; re-confirm in WI0); module docstrings are not
  executed as doctests. The single grep hit `tests/test_compile_e2e.py:13`
  ("vacuously satisfied") is inside a *test module* docstring describing
  behaviour, not an assertion against production docstring text — benign; WI0
  notes it so the implementer does not stall. If any real text-assertion exists,
  fold the assertion update into the same work item and record it in the
  Decision Log.

- Risk: trimming a docstring drops a *behavioural* caveat that some reader relied
  on (for example the D-BYTE-COMPARE "not a digest" note in `compile_consistent`,
  the `R-NOWRITE`/`D-RESULT` notes in `check_compiled`, or — critically —
  `compile_is_current`'s own content-polarity contract), conflating
  "projection-table prose" with "this consumer's own contract".
  Severity: medium
  Likelihood: medium
  Mitigation: only the *shared projection-table* sentences (the restatement of
  the *other* caller's polarity) move to or cross-reference the authoritative
  docstring. Each function keeps every sentence that states its *own* contract.
  In particular `compile_is_current` KEEPS its content-polarity statement (lines
  93-100) — that is its reason for existing — and loses only its opposite-polarity
  restatement (lines 102-107). WI1b-WI4 each enumerate exactly which sentences
  are shared (move/cross-reference) versus function-specific (keep). When in
  doubt, keep the sentence in the function.

- Risk: the authoritative docstring becomes incomplete — it must now carry *both*
  polarities (the detector's vacuous-absent and the content/`--check`
  not-current-absent) so the cross-references resolve to a full table.
  Severity: medium
  Likelihood: low
  Mitigation: WI1a explicitly confirms `compiled_matches_drafts` states both
  polarities and names all three consumers, so every cross-reference (from
  `compile_is_current`, `compile_consistent`, `_check_compiled_matches_drafts`,
  and `check_compiled`) resolves there before any of them is trimmed.

- Risk: after WI1b, `compile_is_current` and `compiled_matches_drafts` could
  appear to disagree on whether the content polarity "lives" in one place or two.
  Severity: low
  Likelihood: low
  Mitigation: the division is principled and stated in the Decision Log:
  `compiled_matches_drafts` is the authoritative *table* of all three verdicts
  and both polarities; `compile_is_current` states only the *content* polarity it
  computes (its contract) and cross-references the table for the *other* polarity.
  Neither restates the other caller's polarity, so there is no fourth/fifth full
  copy.

- Risk: the one-sentence consumer notes drift from the authoritative wording over
  time, re-introducing the very duplication this removes.
  Severity: low
  Likelihood: low
  Mitigation: each consumer note is a *pointer* ("see `compiled_matches_drafts`
  for the full three-valued table and the detector's opposite polarity"), not a
  restatement, so there is nothing to drift; the projection table exists in
  exactly one prose location.

## Progress

- [x] WI0 — Confirm no test or doctest pins the docstring text (note the benign
  `test_compile_e2e.py:13` hit); re-run the polarity-prose survey; record the
  baseline `make all` result. **Done (2026-06-27):** no `doctest` config in
  `pyproject.toml`/`Makefile`; the only docstring-text grep hit is
  `tests/test_compile_e2e.py:13` (a test-module docstring — benign, not a
  production-docstring assertion). The polarity-prose survey confirms the
  six-docstring inventory is current. Baseline `make all` is green (ruff
  format + check, interrogate 100%, ty, 1370 passed/1 skipped, pip-audit clean).
- [x] WI1a — Make `compiled_matches_drafts`'s docstring the single authoritative
  statement of the three-valued verdict and both opposite absent-file polarities,
  naming all three consumers. **Done (2026-06-27):** the projection paragraph now
  names all three consumers (`_check_compiled_matches_drafts`,
  `compile_consistent`, `check_compiled`) and states both polarities crisply as
  a bullet list. `make all` green; coderabbit raised one minor execplan-prose
  finding (impersonal voice), fixed in the same commit.
- [x] WI1b — Trim `compile_is_current` to keep its content-polarity contract and
  drop its restatement of the detector's opposite polarity, cross-referencing the
  authoritative docstring. **Done (2026-06-27):** kept the content-polarity
  paragraph and the "do not fix that asymmetry" scope caveat; dropped the inline
  restatement of the detector's mapping (`is not CompiledComparison.DIVERGES`:
  vacuously satisfied) and replaced it with a cross-reference to
  `compiled_matches_drafts`. `make all` green; coderabbit found nothing.
- [x] WI2 — Trim `done_predicate.compile_consistent` to a self-projection that
  drops the opposite-polarity restatement and cross-references the authoritative
  docstring. **Done (2026-06-27):** removed the third paragraph (the detector's
  vacuously-satisfied restatement) and replaced it with a one-sentence
  cross-reference to `compiled_matches_drafts`. Kept the return contract, the
  3.1.1 B1 / R-STALE notes, the `compile_is_current` routing sentence, the
  D-BYTE-COMPARE "not a digest" note, and the parameter blocks. `make all` green;
  coderabbit found nothing.
- [x] WI3 — Add (only) an explicit cross-reference sentence to
  `disk_evidence._check_compiled_matches_drafts`; it is already a self-projection
  with no table to remove. **Done (2026-06-27):** confirmed B2 — the docstring is
  already a self-projection (shared-seam reference, D-READ rule, its own
  `DIVERGES`-only polarity, oracle-twin note) with no table to remove. Appended
  a single explicit cross-reference sentence to `compiled_matches_drafts` for the
  full table; nothing else changed. Chose the explicit cross-reference (not a
  no-op) so a reader finds the authoritative table by name. `make all` green;
  coderabbit found nothing.
- [x] WI4 — Trim `commands._compile.check_compiled` to a self-projection that
  drops the opposite-polarity restatement and cross-references the authoritative
  docstring. **Done (2026-06-27):** kept the exit-code mapping (its own
  contract), the load/refuse/exit-`3` boundary, the R-NOWRITE guarantee, the
  D-RESULT note, and the parameter blocks; replaced the detector-polarity
  restatement with a cross-reference to `compiled_matches_drafts`. This removes
  the last restatement of the detector's polarity. `make all` green; coderabbit
  found nothing.
- [x] WI5 — Tick the roadmap 7.1.2 checkbox (line 2486) and run the markdown
  gates. **Done (2026-06-27):** `docs/roadmap.md` line 2486 is now `- [x]
  7.1.2.`. `make all`, `make markdownlint`, and `make nixie` all green.

## Surprises & discoveries

- Observation: the branch leaf `roadmap-7-1-2` already has a COMPLETE ExecPlan
  on disk (`docs/execplans/roadmap-7-1-2.md`), but it is the device-ledger plan
  for the *previously* numbered 7.1.2 task.
  Evidence: `git log --oneline -- docs/execplans/roadmap-7-1-2.md` shows commit
  `01d22a2` "Triage step 7.1 remediation proposals onto roadmap lanes"
  renumbered the step; the file's title is "Implement the per-novel
  `device-ledger.toml` enforcement (roadmap 7.1.2)".
  Impact: to avoid clobbering a merged plan, this plan is named
  `roadmap-7-1-2-docstring.md`. See Decision Log.

- Observation: the audits' "four docstrings" enumeration is stale; the current
  tree carries the polarity/projection prose in **six** docstrings.
  Evidence: round-1 design review (`roadmap-7-1-2-docstring.logisphere-review-r1.md`)
  and the WI0 survey: roadmap task 7.1.1 (`docs/roadmap.md` line 2456, `[x]`,
  completed) added `compile_is_current` (`compile_model.py` lines 90-119) with a
  full both-polarity docstring; both audits pre-date 7.1.1 so neither counts it.
  Impact: the plan now treats `compiled_matches_drafts` as the *only* authoritative
  table and explicitly handles `compile_is_current` (WI1b), the
  `CompiledComparison` class docstring (B3 exemption), and the already-trimmed
  `_check_compiled_matches_drafts` (WI3 is a cross-reference add, not a removal).

## Decision log

- Decision: name this plan `docs/execplans/roadmap-7-1-2-docstring.md` rather
  than overwriting `docs/execplans/roadmap-7-1-2.md`.
  Rationale: the bare-leaf name is occupied by an unrelated, merged, COMPLETE
  plan (the device-ledger task that previously held the 7.1.2 slot before the
  step was re-triaged). Overwriting it would destroy a historical, referenced
  artefact. The `-docstring` suffix preserves history and unambiguously scopes
  this plan to the current docstring-consolidation task.
  Date/Author: 2026-06-26, planning agent.

- Decision (resolves round-1 B1): `compiled_matches_drafts` is the single
  authoritative docstring for the full three-valued table and both polarities;
  `compile_is_current` keeps only its *content-polarity* statement (its contract
  as the named content-polarity seam from roadmap 7.1.1) and drops its
  restatement of the detector's *opposite* polarity, cross-referencing the
  authoritative docstring (WI1b).
  Rationale: `compile_is_current` exists precisely to be the one place the
  `MATCHES`-only content polarity is computed (`audit-4.1.2.md` Finding 1;
  roadmap 7.1.1 success text), so stating that one polarity is its own contract,
  not shared prose. Its restatement of the *detector's opposite* polarity (lines
  102-107: "The §5.4 detector deliberately uses the **opposite** polarity …")
  IS shared prose — it re-derives another caller's mapping — and is exactly the
  duplication 7.1.2 removes. Trimming only that restatement leaves the
  projection table (both polarities) in exactly one docstring
  (`compiled_matches_drafts`) while preserving `compile_is_current`'s reason for
  existing. The alternative — folding `compile_is_current`'s content statement in
  too and reducing it to a bare pointer — would weaken the named content-polarity
  seam the predecessor task deliberately created, so it is rejected.
  Date/Author: 2026-06-26, planning agent.

- Decision (resolves round-1 B2): WI3 does **not** remove a projection table from
  `_check_compiled_matches_drafts`, because none exists there.
  Rationale: the current docstring (`disk_evidence.py` lines 194-208) is already
  a self-projection — it carries the shared-seam reference, the D-READ
  read-and-join rule, its OWN polarity (`DIVERGES` = violation, `ABSENT`
  trivially satisfies), and the oracle-twin note. It does not restate the other
  caller's polarity and contains no full three-valued table. The old WI3
  instruction to "replace the longer projection-table restatement with a single
  self-projection" referenced prose that is absent (the audits' enumeration was
  stale; the consumer was trimmed in an earlier slice). WI3 is therefore scoped
  to *at most* adding one explicit cross-reference sentence ("see
  `compiled_matches_drafts` for the full table"); if the existing oracle-twin
  reference is judged a sufficient pointer, WI3 may be a deliberate no-op recorded
  as such. The Purpose no longer claims this site carries a duplicated table.
  Date/Author: 2026-06-26, planning agent.

- Decision (resolves round-1 B3): leave the `CompiledComparison` class docstring
  (`compile_model.py` lines 49-58) untouched under a defended exemption.
  Rationale: audit-3.1.3 Finding 3 (lines 132-141) counts the class docstring
  among the duplication sites ("in `CompiledComparison`'s class docstring …
  lines 48-49"), so leaving it must be justified against that cited source, not
  merely asserted. The actual text (lines 51-58) reads: "The 'is `compiled.md`
  the ordered concatenation of the present drafts?' comparison has three outcomes
  the two production callers must tell apart, not two: an *absent* `compiled.md`
  is distinct from a *present-but-stale* one. A plain `bool` … would collapse
  absent and diverging into one `False`, which neither caller can use. Hence this
  closed three-state result, with each caller projecting it to its own
  absent-file polarity (design §4.3/§5.4; audit-3.1.1 Finding 2)." This states
  *why three states, not a bool* — the type's rationale — and **references** the
  per-caller polarity ("each caller projecting it to its own absent-file
  polarity") rather than **restating** either caller's mapping or the full table.
  Under the keep/move rule (move only the restatement of another caller's
  polarity; keep each site's own contract), this is the enum type's own contract
  and stays. The §4.3/§5.4 cross-reference already points a reader at the design;
  WI1a optionally tightens it to point at `compiled_matches_drafts` if that reads
  more naturally, but the docstring is not a duplication site by the keep/move
  rule. The roadmap success text names only `compiled_matches_drafts` (authoritative)
  and the three consumers, consistent with this exemption.
  Date/Author: 2026-06-26, planning agent.

- Decision (alternatives checkpoint, raised by round-1 Wafflecat): the authoritative
  table could instead live in the `CompiledComparison` class docstring (the type
  every consumer imports). Rejected: audit-3.1.3 proposed `compiled_matches_drafts`
  and the existing both-polarity prose already lives there, so the chosen location
  minimises churn; the class-docstring alternative would require *moving* prose
  into the type *and* trimming the helper, a larger edit for no behavioural gain.
  The
  class docstring keeps its type-rationale role (B3) rather than becoming the table.
  Date/Author: 2026-06-26, planning agent.

- Decision: treat this as documentation-only with no new tests.
  Rationale: roadmap 7.1.2 is "Doc-only; no behaviour change." The projections are
  already test-pinned
  (`test_disk_evidence.py::test_compiled_matches_drafts_projection`,
  `test_compile_check_unit.py`, `test_done_predicate.py`, and the helper's
  `test_compiled_matches_drafts.py`), and the agreement is pinned by
  `test_compile_check_agreement.py`. Adding a test that asserts docstring *text*
  would create exactly the brittle text-coupling AGENTS.md warns against for
  snapshots and would lock prose the task is meant to keep editable. The gate
  that protects this change is `interrogate`'s 100% docstring-coverage check,
  which already runs under `make lint-python`.
  Date/Author: 2026-06-26, planning agent.

- Decision: no cuprum or external-library mechanism is involved; re-verified for
  round 2.
  Rationale: the task edits Python docstrings only. It invokes no subprocess,
  reads no allowlisted executable, and leans on no Cyclopts/pytest-timeout/`uv
  run` behaviour. Verification is the standard `make all` gate (Ruff format +
  lint, interrogate, Pylint, `ty`, pytest under xdist, pip-audit) plus the
  markdown gates for the roadmap-checkbox edit. There is therefore nothing to
  pin against the locked cuprum version (`/data/leynos/Projects/cuprum`) or any
  other locked external library for this slice; that research is genuinely not
  load-bearing here. No undecided fork depends on external-library behaviour.
  Date/Author: 2026-06-26, planning agent.

## Outcomes & retrospective

Completed 2026-06-27. The purpose is met:

- `compiled_matches_drafts` is now the single authoritative docstring stating the
  full three-valued verdict and both opposite absent-file polarities, naming all
  three consumers (WI1a).
- `compile_is_current` keeps its content-polarity contract and the "do not fix
  that asymmetry" caveat, and cross-references the authoritative table instead of
  restating the detector's mapping (WI1b).
- `compile_consistent` (WI2) and `check_compiled` (WI4) each kept their own
  contracts and dropped the detector-polarity restatement for a cross-reference.
- `_check_compiled_matches_drafts` was already a self-projection; it gained one
  explicit cross-reference sentence and nothing more (WI3, review B2).
- The `CompiledComparison` class docstring is unchanged, keeping its
  why-three-states type rationale (B3 exemption).
- No other docstring restates the *other* caller's polarity; the projection table
  lives in exactly one prose location.

Process notes: the change was strictly documentation-only (no signature, control
flow, or behaviour touched), so all five projection pins stayed green throughout.
Six coderabbit runs (one per WI1a–WI4 plus WI3's amend cycle); the only finding
was a minor execplan-prose impersonal-voice note on WI1a, fixed in the same
commit. `make all`, `make markdownlint`, and `make nixie` are green at HEAD.

Lesson for the next agent: the execplan progress notes repeatedly tripped the
80-column markdownlint MD013 limit; wrap progress prose tighter when editing this
plan, since `make all` does not gate markdown — only `make markdownlint` does.

## Context and orientation

This plan and the current working tree are all that is required. Work entirely
inside the git-donkey worktree
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-2`. Do not edit
anything in the root/control worktree.

The four files and the relevant docstrings (line numbers confirmed against the
current tree; re-check with `leta show` before editing):

- `novel_ralph_skill/state/compile_model.py` — owns the shared seam. Three
  docstrings here carry projection/polarity prose:
  - `CompiledComparison` (the enum, class at line 48; docstring lines 49-58).
    The *type's* own rationale ("why three states, not a bool"); it references
    but does not restate the per-caller polarity. **Exempt** (B3 Decision Log);
    do not trim it.
  - `compile_is_current` (def at line 90; docstring lines 91-118). Carries the
    content polarity in full (lines 93-100) **and** the detector's opposite
    polarity in full (lines 102-107). WI1b keeps the former (its contract) and
    drops the latter (shared prose), cross-referencing the helper.
  - `compiled_matches_drafts` (the helper, def at line 122; docstring lines
    123-169). Lines 132-135 already carry the projection-table prose
    ("each projecting the three-valued result to its own absent-file polarity —
    the detector treats absent as satisfied, the content clause treats both
    absent and divergent as not-done (only `MATCHES` holds)") but name only
    *two* consumers. This is the chosen **authoritative** location (WI1a).

- `novel_ralph_skill/state/done_predicate.py` — `compile_consistent` (def at
  line 213; docstring lines 214-260). Shared prose to drop/cross-reference: the
  third paragraph (lines 233-236) restating the detector's "**opposite**
  absent-file polarity … *vacuously satisfied* … reconciled in the one shared
  helper". Consumer-specific prose to **keep**: its first paragraph (return
  contract — absent → `False`, present → `True` iff byte-equal; the 3.1.1 B1
  soundness and R-STALE notes), the `compile_is_current` routing sentence (lines
  227-229), the D-BYTE-COMPARE "not a digest" note, and the
  `Parameters`/`Returns`/`Raises` blocks.

- `novel_ralph_skill/state/disk_evidence.py` — `_check_compiled_matches_drafts`
  (def at line 193; docstring lines 194-208). **Already a self-projection** (B2):
  it states the shared-seam reference, the D-READ read-and-join rule, its OWN
  polarity (only `DIVERGES` is a violation; `ABSENT` trivially satisfies —
  "nothing to diverge from"), and the oracle-twin note (D-COMPILE; audit-3.1.1
  Finding 2). It does **not** restate the other caller's polarity and has **no**
  three-valued table. WI3 at most adds one explicit cross-reference sentence;
  there is nothing to remove.

- `novel_ralph_skill/commands/_compile.py` — `check_compiled` (def at line 166;
  docstring lines 167-208). Shared prose to drop/cross-reference: the second
  paragraph's restatement of the "**opposite** polarity to the §5.4 …
  disk-evidence detector (absent = vacuously satisfied); both are reconciled
  inside the one shared helper" (lines 185-187). Consumer-specific prose to
  **keep**: the exit-code mapping (`MATCHES` → exit `0`; `ABSENT`/`DIVERGES` →
  exit `4`; D-POLARITY), the load/refuse/exit-`3` boundary sentence, the
  R-NOWRITE no-write guarantee, the D-RESULT bounded-`diverged` note, and the
  `Returns`/`Raises` blocks.

Definitions:

- *Absent-file polarity*: how a consumer maps the `ABSENT` verdict (an absent
  `compiled.md`). The detector maps `ABSENT` → satisfied (no violation); the
  content clause and `--check` map `ABSENT` → not-current.
- *Self-projection*: a one-sentence statement of which verdict(s) a function
  treats as satisfied/violating, without re-deriving any other caller's mapping.
- *Authoritative docstring*: the single docstring that states the full
  three-valued table and both polarities; here, `compiled_matches_drafts`.
- *Shared prose*: a sentence that restates *another* caller's polarity mapping (a
  re-derivation), as opposed to a sentence that states the function's own
  contract. Only shared prose moves or is cross-referenced.

## Plan of work

Stage A (WI0) is understand-and-verify with no source edits. Stages B–E
(WI1a, WI1b, WI2, WI3, WI4) each edit one docstring and are independently
committable and gate-passable. Stage F (WI5) ticks the roadmap and runs the
markdown gates. Each work item ends with `make all` (and WI5 adds `make
markdownlint` and `make nixie`). Do not proceed to the next work item if the
current one's validation fails.

Order rationale: WI1a first, so the authoritative docstring is *complete* (both
polarities, all three consumers named) before any docstring is trimmed to point
at it — no cross-reference dangles at any commit boundary. WI1b then trims
`compile_is_current` (which points at the now-complete helper). WI2–WI4 trim the
three consumers in any order (they are independent). WI5 closes out the roadmap.

### WI0 — Verify no test pins docstring text; re-survey; record baseline

Implements: the round-1 pre-mortem prevention ("re-survey the current tree, not
the audits").

- Documentation read: `docs/issues/audit-3.1.3.md` Finding 3;
  `docs/issues/audit-4.1.2.md` Finding 3; the round-1 review
  `docs/execplans/roadmap-7-1-2-docstring.logisphere-review-r1.md`; AGENTS.md
  "Python verification and testing" and "Change quality and committing";
  `pyproject.toml` `[tool.interrogate]` (line 309) and the pytest config;
  `Makefile` `test`/`lint` targets.
- Skills to load: `leta` (navigation), `sem` (history of the docstrings),
  `python-router` → `python-testing` (confirm the doctest posture).
- Actions:
  1. Confirm pytest is **not** configured to run module docstrings as doctests:
     grep `pyproject.toml` and `Makefile` for `--doctest-modules`/`doctest` and
     confirm absent (round-1 review confirmed this; re-confirm).
  2. Grep the `tests/` tree for any assertion against the docstring sentences
     (for example `"treats absent as satisfied"`, `"vacuously satisfied"`,
     `"only ``MATCHES`` holds"`, `.__doc__`). The only expected hit is
     `tests/test_compile_e2e.py:13`, which is inside that *test module's*
     docstring describing behaviour — **benign**, not a production-docstring-text
     assertion. Do not stall on it. If any real text-assertion exists, record it
     and fold the update into the relevant work item (Decision Log + that WI's
     test list).
  3. Re-run the polarity-prose survey over the four files to confirm the
     six-docstring inventory in "Survey of the current tree" is current:

     ```bash
     grep -rnE \
       -e "vacuously satisfied|absent as satisfied|opposite.*polar" \
       -e "only .*MATCHES|three-valued|absent-file polarity" \
       -e "nothing to diverge from" \
       novel_ralph_skill/state/compile_model.py \
       novel_ralph_skill/state/done_predicate.py \
       novel_ralph_skill/state/disk_evidence.py \
       novel_ralph_skill/commands/_compile.py
     ```

     Expect the six sites enumerated above; if the inventory has shifted, update
     the plan before editing.
  4. Run the baseline `make all` and record the pass in Progress, so any later
     red is attributable to this slice.
- Tests: none added (verification-only). The relevant suites are enumerated
  under Constraints; this WI only confirms they are green at baseline.
- Validation: `make all` passes; the grep finds no production-docstring-text
  assertion (only the benign `test_compile_e2e.py:13` test-module-docstring hit).

### WI1a — Make `compiled_matches_drafts` the authoritative projection table

Implements: roadmap 7.1.2 ("Make `compiled_matches_drafts`'s docstring the
single authoritative description of the three-valued verdict and the two
opposite absent-file polarities"); audit-3.1.3 Finding 3 (proposed fix);
audit-4.1.2 Finding 3 (proposed fix). Design basis:
`docs/novel-ralph-harness-design.md` §4.3 (the join rule and absent-compile
regeneration) and §5.4 (the detector); `docs/issues/audit-3.1.1.md` Finding 2.

- Documentation read: `compile_model.py` lines 48-176 (the enum and helper
  docstrings); design §4.3 and §5.4; audit-3.1.3 Finding 3.
- Skills to load: `leta` (`leta show compiled_matches_drafts`), `en-gb-oxendict`
  (spelling), `python-router` → `python-data-shapes` (docstring conventions for
  the enum/helper).
- Edit: in `compiled_matches_drafts`'s docstring, ensure the projection
  paragraph (currently lines 132-135) states, in one authoritative place:
  - the three outcomes (`ABSENT`/`MATCHES`/`DIVERGES`) and why three not two;
  - the detector's polarity (treats `ABSENT` as satisfied — "nothing to diverge
    from" — only `DIVERGES` is a violation);
  - the content-clause/`--check`/`compile_is_current` polarity (only `MATCHES` is
    current; both `ABSENT` and `DIVERGES` are not-current);
  - that all three named consumers
    (`disk_evidence._check_compiled_matches_drafts`,
    `done_predicate.compile_consistent`, `commands._compile.check_compiled`)
    route through this helper (the content-polarity consumers via
    `compile_is_current`) so they cannot disagree on the same tree.
  The current text already covers most of this; the edit is to (a) name all
  three consumers explicitly (it currently names two) so every consumer's
  cross-reference resolves here, and (b) state the two polarities crisply enough
  that the `compile_is_current` and consumer one-liners can simply point here.
  Keep the existing fault-boundary paragraph and the
  `Parameters`/`Returns`/`Raises` blocks unchanged.
- Tests: none added — the helper's verdicts are already pinned by
  `tests/test_compiled_matches_drafts.py` (the three outcomes, the
  existence-before-read ordering, the fault boundary). Re-run it to confirm
  green.
- Validation: `make all` passes; `tests/test_compiled_matches_drafts.py`,
  `tests/test_disk_evidence.py`, `tests/test_compile_check_unit.py`,
  `tests/test_done_predicate.py`, and `tests/test_compile_check_agreement.py`
  stay green. Commit: "Make compiled_matches_drafts the authoritative
  projection-table docstring".

### WI1b — Trim `compile_is_current` to its content polarity plus a cross-reference

Implements: roadmap 7.1.2 ("no fourth/fifth full copy remains"); resolves
round-1 B1. Design basis: §4.3/§5.4; `audit-4.1.2.md` Finding 1 (the named
content-polarity seam); roadmap 7.1.1 (which introduced this docstring's full
both-polarity prose).

- Documentation read: `compile_model.py` lines 90-119; the now-complete
  `compiled_matches_drafts` docstring (WI1a); design §5.4; the B1 Decision Log
  entry above.
- Skills to load: `leta` (`leta refs compile_is_current` to confirm no caller
  reads its `__doc__`), `en-gb-oxendict`, `python-router` → `python-data-shapes`.
- Edit: **keep** the first docstring paragraph (lines 93-100), which states this
  predicate's own content polarity ("only `MATCHES` … both `ABSENT` and
  `DIVERGES` are not"; the two consumers route through it so they cannot disagree)
  — that is `compile_is_current`'s contract. **Replace** the second paragraph
  (lines 102-107, the restatement of the §5.4 detector's *opposite* polarity)
  with a single cross-reference such as: "The §5.4 detector
  (`disk_evidence._check_compiled_matches_drafts`) deliberately projects the
  *opposite* polarity (an absent compile is vacuously satisfied); see
  `compiled_matches_drafts` for the full three-valued table and both polarities."
  Keep the `Parameters`/`Returns` blocks unchanged. The "do not 'fix' that
  asymmetry" caveat may be preserved in the cross-reference sentence if it reads
  naturally, since it is guidance about *this* predicate's scope, not a
  re-derivation of the detector's mapping.
- Tests: none added — `compile_is_current`'s behaviour is pinned transitively by
  `tests/test_compile_check_unit.py`,
  `tests/test_done_predicate.py::test_compile_consistent_present_coherent_and_absent`,
  and `tests/test_compile_check_agreement.py`. Re-run them.
- Validation: `make all` passes; the five named suites stay green. Commit: "Trim
  compile_is_current to its content polarity plus a cross-reference".

### WI2 — Trim `compile_consistent` to a self-projection plus a cross-reference

Implements: roadmap 7.1.2 ("`compile_consistent` … carry only a one-sentence
self-projection pointing at the authoritative docstring"); audit-3.1.3 Finding 3.

- Documentation read: `done_predicate.py` lines 213-261; design §4.3; the
  now-complete `compiled_matches_drafts` docstring (WI1a).
- Skills to load: `leta` (`leta refs compile_consistent` to confirm no caller
  reads its `__doc__`), `en-gb-oxendict`, `python-router` →
  `python-errors-and-logging` (the `Raises` block must remain accurate).
- Edit: replace the third paragraph (lines 233-236, the "the **opposite**
  absent-file polarity … *vacuously satisfied* … reconciled in the one shared
  helper" restatement of the *detector's* mapping) with a single cross-reference
  such as: "This clause projects the shared verdict to its content polarity —
  only `MATCHES` is 'done' (`ABSENT` and `DIVERGES` are not); see
  `compile_model.compiled_matches_drafts` for the three-valued table and the
  detector's opposite polarity." Keep: the first paragraph (return contract,
  3.1.1 B1, R-STALE), the `compile_is_current` routing sentence (lines 227-229),
  the D-BYTE-COMPARE "not a digest" note, and the `Parameters`/`Returns`/`Raises`
  blocks. (The first paragraph already states the function's own content polarity,
  so this WI removes only the *detector*'s-polarity restatement; it need not
  re-add a content-polarity sentence.)
- Tests: none added — the polarity is pinned by
  `tests/test_done_predicate.py::test_compile_consistent_present_coherent_and_absent`
  and the agreement by `tests/test_compile_check_agreement.py`. Re-run both.
- Validation: `make all` passes. Commit: "Trim compile_consistent to drop the
  detector-polarity restatement".

### WI3 — Add an explicit cross-reference to `_check_compiled_matches_drafts`

Implements: roadmap 7.1.2 ("`_check_compiled_matches_drafts` … carry only a
one-sentence self-projection"); audit-3.1.3 Finding 3. Resolves round-1 B2.
Design basis: §5.4.

- Documentation read: `disk_evidence.py` lines 193-208; design §5.4;
  audit-3.1.1 Finding 2; the B2 Decision Log entry above.
- Skills to load: `leta`, `en-gb-oxendict`, `python-router` → `python-testing`
  (the projection has a dedicated pin to keep green).
- Edit: this docstring is **already** a self-projection (shared-seam reference,
  D-READ read-and-join rule, its own `DIVERGES`-only polarity with `ABSENT`
  trivially satisfying, oracle-twin note); it carries **no** projection-table
  restatement and **no** other-caller polarity, so there is nothing to remove
  (round-1 B2). At most, append one explicit cross-reference clause to the
  existing self-projection sentence so a reader can find the full table, e.g.
  extend "… an *absent* one (`ABSENT`) trivially satisfies the check (nothing to
  diverge from) …" with "; see `compile_model.compiled_matches_drafts` for the
  full three-valued table and both polarities". Do not change the shared-seam
  reference, the D-READ sentence, or the oracle-twin note (D-COMPILE; audit-3.1.1
  Finding 2). If the existing reference to `compiled_matches_drafts` (line 197)
  is judged a sufficient pointer to the table, WI3 is a deliberate no-op — record
  that in Progress and skip the commit.
- Tests: none added — pinned by
  `tests/test_disk_evidence.py::test_compiled_matches_drafts_projection`. Re-run
  it.
- Validation: `make all` passes. Commit (only if an edit is made): "Add a
  projection-table cross-reference to the disk-evidence compile detector".

### WI4 — Trim `check_compiled` to a self-projection plus a cross-reference

Implements: roadmap 7.1.2 ("`check_compiled` … carry only a one-sentence
self-projection; no fourth full copy remains"); audit-4.1.2 Finding 3. Design
basis: §3.3 (the checker's bounded read-shape) and §4.3.

- Documentation read: `_compile.py` lines 160-245; design §3.3 and §4.3;
  ADR-001 (the deterministic/judgemental boundary the no-write guarantee rests
  on); audit-4.1.2 Finding 3; the now-complete `compiled_matches_drafts`
  docstring (WI1a).
- Skills to load: `leta`, `en-gb-oxendict`, `python-router` →
  `domain-cli-and-daemons` (the command surface and exit-code prose),
  `python-testing` (the unit pin).
- Edit: replace the second paragraph's restatement of the detector's opposite
  polarity (lines 185-187, "This is the **opposite** polarity to the §5.4 …
  detector (absent = vacuously satisfied); both are reconciled inside the one
  shared helper") with a single cross-reference such as: "This surface projects
  the shared verdict to the `compile_consistent` content polarity — `MATCHES`
  exits `0`, while `ABSENT` and `DIVERGES` are actionable findings (exit `4`;
  D-POLARITY); see `compile_model.compiled_matches_drafts` for the three-valued
  table and the detector's opposite polarity." Keep: the load/refuse/exit-`3`
  boundary paragraph, the R-NOWRITE no-write guarantee, the D-RESULT
  bounded-`diverged` note, and the `Returns`/`Raises` blocks. The existing
  exit-code mapping prose (lines 180-184) is this surface's own contract and may
  be folded into the cross-reference sentence above or kept verbatim; either way
  it stays. This removes the last restatement of the detector's polarity.
- Tests: none added — pinned by `tests/test_compile_check_unit.py` (the
  `MATCHES`-only exit-`0`, `ABSENT`/`DIVERGES` exit-`4` polarity) and
  `tests/test_compile_check_agreement.py`. Re-run both.
- Validation: `make all` passes. Commit: "Trim novel-compile --check to drop the
  detector-polarity restatement".

### WI5 — Tick the roadmap checkbox and run the markdown gates

Implements: closing roadmap 7.1.2 ("Success: … `make all` stays green").

- Documentation read: AGENTS.md "Markdown guidance"; the roadmap 7.1.2 block at
  `docs/roadmap.md` lines 2486-2511.
- Skills to load: `en-gb-oxendict`.
- Edit: change `docs/roadmap.md` line 2486 from `- [ ] 7.1.2.` to `- [x]
  7.1.2.` This is the only roadmap content edit (besides this plan), so it gates
  the markdown checks.
- Tests: none.
- Validation: `make all` passes; `make markdownlint` passes; `make nixie`
  passes (no Mermaid added, so nixie is a no-op confirmation). Confirm by reading
  the six docstrings that exactly one (`compiled_matches_drafts`) carries the full
  projection table with both polarities; that `compile_is_current` keeps its
  content-polarity contract and cross-references the helper; that
  `compile_consistent`, `_check_compiled_matches_drafts`, and `check_compiled`
  each carry their own polarity plus a cross-reference and no restatement of the
  other caller's polarity; and that the `CompiledComparison` class docstring keeps
  its type rationale. Commit: "Tick roadmap 7.1.2 (compile projection-prose
  consolidation)".

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-2`.

WI0 verification:

```bash
# No doctest execution of module docstrings, and no test asserts the text.
grep -rn "doctest" pyproject.toml Makefile || echo "no doctest config — good"
grep -rn "vacuously satisfied\|treats absent as satisfied\|__doc__" tests/ \
  || echo "no docstring-text assertion — good"
# Re-survey the six polarity-prose docstrings across the four files.
grep -rnE \
  -e "vacuously satisfied|absent as satisfied|opposite.*polar" \
  -e "only .*MATCHES|three-valued|absent-file polarity" \
  -e "nothing to diverge from" \
  novel_ralph_skill/state/compile_model.py \
  novel_ralph_skill/state/done_predicate.py \
  novel_ralph_skill/state/disk_evidence.py \
  novel_ralph_skill/commands/_compile.py
make all
```

The second grep is expected to hit only `tests/test_compile_e2e.py:13` (a
test-module docstring) — benign, not a production-docstring assertion.

Expected (abridged) transcript for `make all` at baseline and after each WI:

```plaintext
ruff format --check ...      # All checks passed!
ruff check ...               # All checks passed!
interrogate ...              # RESULT: PASSED (minimum: 100.0%, actual: 100.0%)
ty check ...                 # success
pytest -v -n ...             # ... passed
pip-audit                    # No known vulnerabilities found
```

Per-WI cycle (WI1a, WI1b, WI2, WI3, WI4): edit the one docstring with the `Edit`
tool, then:

```bash
make all
git add -A && git commit -F <(printf '%s\n' "<imperative subject>")
```

WI5:

```bash
make all
make markdownlint
make nixie
git add -A && git commit -F <(printf '%s\n' "Tick roadmap 7.1.2 (compile projection-prose consolidation)")
```

Use file-based commit messages (never `-m`) per the `commit-message` skill.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: every existing suite passes unchanged, in particular
  `tests/test_compiled_matches_drafts.py`,
  `tests/test_disk_evidence.py::test_compiled_matches_drafts_projection`,
  `tests/test_compile_check_unit.py`,
  `tests/test_done_predicate.py::test_compile_consistent_present_coherent_and_absent`,
  and `tests/test_compile_check_agreement.py`. No new test is added (the change
  is doc-only; behaviour is already pinned — see Decision Log).
- Lint/typecheck/coverage: `make lint` passes, including `interrogate` at 100%
  docstring coverage (every function keeps a non-empty docstring) and Pylint;
  `make check-fmt` and `make typecheck` (`ty`) pass; `make audit` passes.
- Docs: `make markdownlint` and `make nixie` pass for the roadmap-checkbox edit.

Quality method (verification): run `make all` after every work item, plus `make
markdownlint` and `make nixie` for WI5. Acceptance is verifiable by reading the
six docstrings: exactly one (`compiled_matches_drafts`) states the full
three-valued projection table with both polarities; `compile_is_current` states
only its own content polarity plus a cross-reference; `compile_consistent`,
`_check_compiled_matches_drafts`, and `check_compiled` each carry their own
polarity plus a cross-reference, with no restatement of the *other* caller's
polarity; and the `CompiledComparison` class docstring keeps its
*why-three-states* type rationale (B3 exemption).

## Idempotence and recovery

Every step is a docstring edit that is safe to re-run; re-applying the same edit
is a no-op. If a `make all` run fails after an edit, the failure is local to the
one docstring just changed: re-read it with `leta show`, compare against the
"keep" / "move" split in this plan's Context section, and fix the prose. No step
is destructive; `git restore <file>` reverts any single docstring edit cleanly.

## Artifacts and notes

The chosen authoritative location already carries most of the table
(`compile_model.py` lines 132-135):

```python
#     consume it, each projecting the three-valued result to its own absent-file
#     polarity — the detector treats absent as satisfied, the content clause treats
#     both absent and divergent as not-done (only ``MATCHES`` holds) — so the two
#     cannot disagree on the same tree.
```

WI1a widens "the two" to name all three consumers so every cross-reference
resolves here. WI1b then removes the *duplicate* both-polarity statement from
`compile_is_current` (the round-1 B1 fifth copy).

## Interfaces and dependencies

No interfaces change. No dependency is added or touched. The edited symbols keep
their exact signatures:

- `novel_ralph_skill.state.compile_model.compiled_matches_drafts(state: State,
  working_dir: Path) -> CompiledComparison`
- `novel_ralph_skill.state.compile_model.compile_is_current(verdict:
  CompiledComparison) -> bool`
- `novel_ralph_skill.state.done_predicate.compile_consistent(state: State,
  working_dir: Path) -> bool`
- `novel_ralph_skill.state.disk_evidence._check_compiled_matches_drafts(state:
  State, working_dir: Path) -> Violation | None`
- `novel_ralph_skill.commands._compile.check_compiled() -> CommandOutcome`

This slice changes only the docstring bodies attached to these symbols.

## Revision note

Round 2 (2026-06-26): revised to resolve all three round-1 design-review blocking
points.

- B1 (central): added WI1b to trim `compile_is_current`'s docstring — keeping its
  content-polarity contract (its reason for existing, per roadmap 7.1.1) and
  removing its restatement of the §5.4 detector's *opposite* polarity, which is
  the shared prose 7.1.2 consolidates. Added a "Survey of the current tree"
  section enumerating all six polarity-prose docstrings (replacing the audits'
  stale "four"), reconciled the Purpose, Progress, Tolerances (now naming two
  edit sites in `compile_model.py`), success criterion, and Decision Log, and
  added a WI0 re-survey step.
- B2: rewrote WI3 against the actual `_check_compiled_matches_drafts` docstring,
  which is already a self-projection with no table to remove. WI3 is now scoped
  to *at most* adding one cross-reference sentence (or a recorded no-op), and the
  Purpose no longer claims this site carries a duplicated table.
- B3: added an evidenced Decision-Log entry quoting the `CompiledComparison`
  class-docstring text (lines 51-58) to show it states the type's
  *why-three-states* rationale and only references (does not restate) the
  per-caller polarity, justifying the exemption against audit-3.1.3 Finding 3, and
  recorded the rejected "make the class docstring authoritative" alternative.

These changes are doc-and-plan only; the remaining work is the six docstring/
roadmap edits (WI1a–WI5), each independently committable and gate-passable.
