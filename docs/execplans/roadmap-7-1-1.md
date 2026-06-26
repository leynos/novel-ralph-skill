# Single-source the compile-currency projection and the `compiled.md` path

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Today the "the compile is current" decision and the location of
`working/manuscript/compiled.md` are spelled out by hand in several modules,
even though both already have a natural owner in
`novel_ralph_skill/state/compile_model.py` (the module that owns the
draft-concatenation join rule and the three-valued `CompiledComparison`
verdict).

Two specific duplications exist:

1. The *content-polarity projection* — "only `CompiledComparison.MATCHES`
   means the compile is current; `ABSENT` and `DIVERGES` are not" — is
   hand-written at two sites:
   `done_predicate.compile_consistent`
   (`novel_ralph_skill/state/done_predicate.py:263`,
   `... is CompiledComparison.MATCHES`) and
   `commands._compile.check_compiled`
   (`novel_ralph_skill/commands/_compile.py:221`,
   `if verdict is CompiledComparison.MATCHES:`). A future decision to treat,
   say, `ABSENT` differently in one consumer but not the other would silently
   break the agreement invariant that `tests/test_compile_check_agreement.py`
   pins (audit-4.1.2 Finding 1).

2. The *`compiled.md` path* is constructed independently in at least four
   places: the working-relative envelope token `_COMPILED_REL =
   "working/manuscript/compiled.md"` and the write path `root / "manuscript" /
   "compiled.md"` in `commands/_compile.py`; the read path `working_dir /
   "manuscript" / "compiled.md"` in `state/compile_model.py`; and `(root /
   "manuscript" / "compiled.md").exists()` twice in
   `commands/_novel_done.py`. They cannot drift today only because all four
   hard-code the same `"manuscript"`/`"compiled.md"` literals
   (audit-4.1.2 Finding 2).

After this change `compile_model.py` owns one named predicate
`compile_is_current(verdict)` and one path seam — a
`compiled_manuscript_path(working_dir)` join plus a `COMPILED_REL`
working-relative token constant — and the four consumers route through them.
The "the command-line `--check` surface and the `novel-done` clause agree on
whether `compiled.md` is current" invariant becomes structurally enforced
(one predicate) rather than only test-pinned, and the manuscript's on-disk
location has one definition.

You can observe success three ways. The first two observables are scoped to
**executable code** — the *projection form* `is CompiledComparison.MATCHES` and
the *code-join form* `"manuscript" / "compiled.md"`. They deliberately exclude
docstring prose (the bare `:attr:` `CompiledComparison.MATCHES` cross-references
and the slash-form `manuscript/compiled.md` path mentions), because the
absent-file projection *prose* consolidation is roadmap task **7.1.2**, a
separate doc-only follow-up that this task must not pre-empt. An auditor who
narrows the grep to these executable forms sees a clean end state; a looser grep
that also matches docstrings (e.g. `git grep -n 'manuscript/compiled.md'` or
`git grep -n 'CompiledComparison.MATCHES'` without the leading `is` token) will
still show the untouched 7.1.2 prose hits at `_compile.py:5,110,184`,
`_novel_done.py:164`, and `done_predicate.py:86,217,229`, and that is **the
intended, correct state**, not a failure — do not "fix" those by editing the
prose into 7.1.2 territory.

1. `git grep -n "is CompiledComparison.MATCHES" novel_ralph_skill/` returns no
   hits in `done_predicate.py` or `_compile.py` (both now call
   `compile_is_current`); the only surviving **`is CompiledComparison.MATCHES`
   projection** lives inside `compile_model.py` (the helper's own definition).
   The bare `:attr:` cross-references to `CompiledComparison.MATCHES` in the
   `_compile.py` and `done_predicate.py` docstrings are deliberately left for
   7.1.2 and are not part of this observable.
2. `git grep -n '"manuscript" / "compiled.md"' novel_ralph_skill/` (the quoted
   **code-join** form) resolves every hit to the new seam in `compile_model.py`
   (`compiled_manuscript_path`); the literal join no longer appears in
   `_compile.py` or `_novel_done.py`. The slash-form `manuscript/compiled.md`
   path mentions that remain in those modules' docstrings are 7.1.2 prose and
   are intentionally untouched.
3. `make all` is green with **no test edited for new behaviour** — every
   compile, done-predicate, disk-evidence, agreement, and snapshot suite stays
   green unchanged, plus one small new test that pins the seam (the predicate's
   three-valued truth table, and that `COMPILED_REL` /
   `compiled_manuscript_path` agree with the historical literals). This is a
   pure no-behaviour-change refactor (roadmap 7.1.1 success criterion: "no
   behaviour changes").

## Scope and explicit non-goals

This task is an internal **DRY-and-layering refactor** of pure Python within
`novel_ralph_skill/state/` and `novel_ralph_skill/commands/`. It changes no
exit code, no envelope shape, no message text, no on-disk path, and no public
console-script behaviour.

In scope (roadmap 7.1.1):

- A named `compile_is_current(verdict: CompiledComparison) -> bool` predicate
  in `compile_model.py`.
- A `compiled_manuscript_path(working_dir: Path) -> Path` join and a
  `COMPILED_REL` working-relative token constant in `compile_model.py`.
- Routing the four consumers — `check_compiled`, `compile_consistent`, and the
  two `novel-done` compile-clause sites (`_failed_clause_message`,
  `_sole_stale_compile`) — through the predicate and/or the path seam.
- Exporting the new symbols from `novel_ralph_skill/state/__init__.py` beside
  the existing `compiled_matches_drafts` / `CompiledComparison` exports.
- One focused unit test pinning the seam (predicate truth table; path/token
  equivalence with the historical literals).

Explicit non-goals (other roadmap tasks own these; do **not** touch them):

- The *opposite* polarity in the §5.4 detector —
  `disk_evidence._check_compiled_matches_drafts` uses `... is not
  CompiledComparison.DIVERGES` (absent = vacuously satisfied). audit-4.1.2
  Finding 1 explicitly says to **leave the detector's opposite polarity as its
  own predicate or inline**, because it is a genuinely different projection. It
  is **not** routed through `compile_is_current`. (Roadmap 7.1.1 names exactly
  three predicate consumers — `check_compiled`, `compile_consistent`, the
  `novel-done` compile clause — not the detector.)
- The absent-file projection **prose** consolidation across the four
  docstrings — that is roadmap task 7.1.2, a separate doc-only follow-up.
- The exists/read race window in `compiled_matches_drafts` (audit-4.1.2
  Finding 4) — out of scope here; no behaviour change.
- The `Reconciliation` payload projection (7.1.3) and the finding-outcome
  envelope builder (7.1.4).

If, while implementing, it emerges that routing a consumer through the seam
forces a behaviour change (an exit code, an envelope field, a message string,
or a snapshot byte to move), **stop and escalate** (see `Tolerances`): the task
is defined as *no behavioural change*, so any required change is a signal the
seam shape is wrong, not licence to edit a snapshot.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** No exit code, envelope field, `result` key, message
  string, or on-disk path may change. Every existing test must pass **without
  edit** (snapshots included). The roadmap 7.1.1 success criterion is explicit:
  "no behaviour changes; and every compile, done-predicate, and disk-evidence
  suite stays green." (design §4.3, §5.4; ADR-003 shared interface contract.)
- **The envelope token `COMPILED_REL` keeps the exact value
  `"working/manuscript/compiled.md"`** — a working-*prefixed* POSIX string,
  byte-identical to today's `_COMPILED_REL`, because
  `tests/test_compile_check_snapshots.py`, `tests/test_compile_snapshots.py`,
  `tests/__snapshots__/test_command_surface_matrix.ambr`, and the
  `tests/contract_drive_support.py:90` `DETERMINISTIC_PATH_TOKEN` all pin it.
  Note the token is **working-prefixed** (`working/manuscript/...`) whereas the
  filesystem join `compiled_manuscript_path(working_dir())` resolves
  `working_dir()` (already the `working/` segment, `_state_load.py:39`) and
  yields a `Path` *without* a doubled `working/`. The seam therefore exposes
  two distinct things — a `Path` join and a string token — not one
  interchanged value.
- **`compile_is_current` lives in `compile_model.py`**, beside
  `compiled_matches_drafts` and `CompiledComparison`, the module the audit and
  roadmap name as the owner of the join rule and the verdict
  (audit-4.1.2 Finding 1 "Add a single named predicate beside the helper in
  `compile_model.py`"; roadmap 7.1.1).
- **The detector's opposite polarity is untouched** (see non-goals).
  `_check_compiled_matches_drafts` keeps `is not CompiledComparison.DIVERGES`.
- **Detect-only boundary (ADR-001):** no consumer gains a write; the path seam
  is read/join only. `check_compiled` still writes nothing on any path.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all new prose, comments,
  docstrings, and commit messages (workflow standing rule;
  `docs/documentation-style-guide.md`).
- **Quality gates:** 100% docstring coverage (`interrogate`, `pyproject.toml`
  `[tool.interrogate] fail-under = 100`); module line cap 400
  (`[tool.pylint.main] max-module-lines = 400` — `compile_model.py` is well
  under it; check after the additions); Ruff line-length 88; Markdown prose
  wrapped at 80 columns (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- **Behaviour drift:** if any existing test (including any snapshot) must be
  edited to keep green, stop and escalate — that means the seam moved behaviour
  (Constraints "No behaviour change").
- **Scope:** if the refactor requires editing any module beyond
  `state/compile_model.py`, `state/done_predicate.py`,
  `commands/_compile.py`, `commands/_novel_done.py`, and
  `state/__init__.py` (plus adding/extending one test file), stop and
  escalate — it has drifted beyond the four named consumers.
- **Detector contamination:** if it appears the §5.4 detector
  (`disk_evidence.py`) should also route through `compile_is_current`, stop and
  escalate — the audit explicitly excludes it (non-goals).
- **Line cap:** if any edited module would exceed 400 lines after the change,
  stop and escalate rather than splitting a module ad hoc.
- **Dependencies:** if any new third-party dependency is required, stop and
  escalate. None is expected — this is internal Python with no new imports.
- **Iterations:** if `make all` still fails after 3 focused attempts on a work
  item, stop and escalate.

## Risks

    - Risk: a consumer is routed through the path seam but the working-prefix
      asymmetry is mishandled, so the envelope token gains or loses the leading
      ``working/`` segment and a snapshot moves.
      Severity: high
      Likelihood: medium
      Mitigation: Work Item 1 defines ``COMPILED_REL`` as the verbatim string
      ``"working/manuscript/compiled.md"`` (the token, not a join of
      ``working_dir()``) and ``compiled_manuscript_path(working_dir)`` as the
      ``Path`` join that takes an already-``working/``-anchored directory. Work
      Item 2 adds a unit assertion that ``COMPILED_REL ==
      "working/manuscript/compiled.md"`` and that
      ``compiled_manuscript_path(Path("working")) == Path("working") /
      "manuscript" / "compiled.md"``, pinning the asymmetry. The existing
      snapshot suites are the backstop: they fail loudly if the token byte
      moves.

    - Risk: the predicate is introduced but a consumer keeps an inline
      ``is CompiledComparison.MATCHES`` (incomplete routing), so the
      duplication the task removes survives.
      Severity: medium
      Likelihood: low
      Mitigation: the success observation is a ``git grep`` that must return no
      ``is CompiledComparison.MATCHES`` outside ``compile_model.py``; Work
      Item 3's validation runs that grep. Work Item 2's predicate truth-table
      test pins the predicate so the routed call sites inherit one definition.

    - Risk: routing the ``novel-done`` clause through the path seam changes the
      ``compiled.md``-missing message wording or the carve-out exit-4 decision.
      Severity: high
      Likelihood: low
      Mitigation: the two ``_novel_done.py`` sites only consume
      ``compiled_manuscript_path`` for the ``.exists()`` stat; the message
      string and the carve-out logic are untouched. The existing
      ``tests/test_novel_done_command.py``, ``test_novel_done_snapshots.py``,
      and ``test_novel_done_bdd.py`` suites pin both and must stay green
      unedited (Constraints "No behaviour change").

    - Risk: the new symbols are added to ``compile_model.py`` but not exported
      from ``state/__init__.py``, so a consumer importing from the package
      surface (as ``_compile.py`` does, ``from novel_ralph_skill.state import
      ...``) cannot reach them.
      Severity: low
      Likelihood: medium
      Mitigation: Work Item 1 adds ``compile_is_current``,
      ``compiled_manuscript_path``, and ``COMPILED_REL`` to both the
      ``compile_model`` import block and the ``__all__`` of
      ``state/__init__.py``, mirroring the existing
      ``compiled_matches_drafts`` entry; ``make all`` (pyright/ty + import
      resolution) catches a missed export.

## Progress

    - [x] Work Item 1: add ``compile_is_current``,
      ``compiled_manuscript_path``, and ``COMPILED_REL`` to
      ``state/compile_model.py``; export them from ``state/__init__.py``.
      Done in commit ``Add compile-currency seam to compile_model``. The two
      functions are placed *after* the ``CompiledComparison`` class (not before)
      so ``compile_is_current``'s body reference resolves without relying on
      forward-evaluation order; the module's own read at the former line 105 now
      calls ``compiled_manuscript_path``. ``make all`` green; coderabbit 0
      findings.
    - [x] Work Item 2: pin the seam with a focused unit test (predicate truth
      table; path/token equivalence with the historical literals), red first.
      Done in commit ``Pin the compile-currency seam with a unit test``. WI1
      had already landed, so the red→green transition was demonstrated by
      temporarily dropping the ``compile_is_current`` export from
      ``state/__init__.py`` (red), then restoring it (green) — transcripts in
      `Surprises & discoveries`. ``make all`` green (1322 passed, +6).
    - [x] Work Item 3: route the four consumers through the seam
      (``compile_consistent``, ``check_compiled``, and the two
      ``_novel_done.py`` sites); replace ``_COMPILED_REL`` and the inline
      ``manuscript/compiled.md`` joins. Done in commit ``Route compile-currency
      consumers through the seam``. All three structural greps are clean: ``is
      CompiledComparison.MATCHES`` and the code-join survive only inside
      ``compile_model.py`` (the helper definitions); ``_COMPILED_REL`` survives
      only as a textual docstring-comment in ``compile_model.py`` explaining
      what ``COMPILED_REL`` replaced (no executable use). After dropping the
      inline join in ``_novel_done._failed_clause_message`` the ``if`` collapsed
      to one line, which ``ruff format`` required — applied. ``make all`` green
      (1322 passed, every pre-existing suite unedited); coderabbit 0 findings.

## Surprises & discoveries

    - Work Item 2 red→green evidence. WI1 (the seam + export) had already been
      committed, so the new test could not be red against a missing symbol
      naturally. The red was reproduced by temporarily removing the
      ``compile_is_current`` import and ``__all__`` entry from
      ``state/__init__.py``:

          === RED RUN (compile_is_current export removed) ===
          ImportError: cannot import name 'compile_is_current' from
          'novel_ralph_skill.state' (.../state/__init__.py)
          ERROR tests/test_compile_model_seam.py
          1 error in 0.25s

      Restoring the export turned it green:

          === GREEN RUN (export restored) ===
          6 passed in 0.16s

    - The two ``compile_model.py`` seam functions are deliberately placed
      *after* the ``CompiledComparison`` class (the plan's "beside" wording does
      not constrain order). ``compile_is_current``'s body references
      ``CompiledComparison`` and is only called at run time, so order is not a
      correctness issue, but defining the class first keeps the reader's eye on
      a defined name.

    - Coderabbit (WI2 run) raised two ``minor`` findings, both against the
      untracked artefact ``docs/execplans/roadmap-7-1-1.logisphere-review-r1.md``
      (the historical round-1 logisphere review), not against any file this task
      edits. They restate the round-1 observations the plan body already
      resolved in its round-2 revision (narrowed Purpose observables; the
      explicit new ``_novel_done.py`` import). The review artefact is an
      immutable record of past review and is out of this task's scope, so the
      findings are not actioned; the WI2 code and the live execplan drew no
      findings.

## Decision log

    - Decision: the stale ``ai-isms.toml`` ExecPlan previously occupying this
      file was discarded and the file rewritten for the actual roadmap 7.1.1
      task. Rationale: the roadmap was renumbered; the on-disk
      ``docs/execplans/roadmap-7-1-1.md`` described a pack-shipping task that no
      longer maps to roadmap entry 7.1.1 ("Extract a ``compile_is_current``
      predicate and a single ``compiled.md`` path seam"). The plan must match
      the task it is named for.
      Date/Author: 2026-06-26, planning agent.

    - Decision: ``compile_is_current`` routes only the two MATCHES-polarity
      consumers (``compile_consistent``, ``check_compiled``); the §5.4 detector
      keeps its own ``is not DIVERGES`` projection inline.
      Rationale: audit-4.1.2 Finding 1 is explicit — "Leave the detector's
      *opposite* polarity … as its own named predicate or inline, since it is
      genuinely a different projection." The roadmap names exactly three
      predicate consumers, none of which is the detector.
      Date/Author: 2026-06-26, planning agent.

    - Decision: the path seam is two members — a ``compiled_manuscript_path``
      ``Path`` join and a ``COMPILED_REL`` string token — not one. Rationale:
      the envelope token is working-*prefixed*
      (``working/manuscript/compiled.md``) and is a deterministic snapshot
      datum, whereas the filesystem path is built from
      ``working_dir()`` (already the ``working/`` segment) and must not double
      the prefix. A single member cannot serve both without an
      asymmetry-hiding transform, so the seam exposes both explicitly.
      Date/Author: 2026-06-26, planning agent.

    - Decision: the Purpose-section success observables are scoped to the
      *executable* forms — `is CompiledComparison.MATCHES` (projection) and
      `"manuscript" / "compiled.md"` (code-join) — and explicitly disclaim
      docstring-prose hits (`:attr:` cross-references and slash-form path
      mentions), which are roadmap 7.1.2's domain.
      Rationale: round-1 logisphere review flagged that the looser greps
      (`git grep 'manuscript/compiled.md'`, and `CompiledComparison.MATCHES`
      grepped without the leading `is` token) would still match 7.1.2 prose at
      `_compile.py:5,110,184`, `_novel_done.py:164`,
      `done_predicate.py:86,217,229` (verified by `git grep` in round 2), so a
      verbatim run would show false failures and tempt an auditor to edit prose
      into 7.1.2 territory. Narrowing the observables to the executable forms
      makes the stated end state match the actual (correct) one.
      Date/Author: 2026-06-26, planning agent (round 2).

## Outcomes & retrospective

    - Delivered in three atomic, gate-passing commits, one per work item:
      ``Add compile-currency seam to compile_model`` (the seam + export),
      ``Pin the compile-currency seam with a unit test`` (the red-first seam
      test), and ``Route compile-currency consumers through the seam`` (the
      behaviour-preserving routing). ``make all`` green at HEAD.
    - The no-behaviour-change guarantee held end to end: not one pre-existing
      compile, done-predicate, disk-evidence, agreement, snapshot, BDD, or e2e
      test was edited. The only test change is the additive
      ``tests/test_compile_model_seam.py``. No snapshot byte moved.
    - The three structural observables landed exactly as the Purpose section
      predicted: the executable ``is CompiledComparison.MATCHES`` projection and
      the ``"manuscript" / "compiled.md"`` code-join now live only in
      ``compile_model.py``, and ``_COMPILED_REL`` survives only as a textual
      docstring reference. The 7.1.2 docstring-prose hits are deliberately
      untouched.
    - One unplanned but trivial edit: removing the inline join in
      ``_novel_done._failed_clause_message`` let the ``if`` condition fit one
      line, which ``ruff format`` enforced. No tolerance was breached (no
      behaviour drift, no scope creep beyond the five named modules plus the new
      test, no line-cap breach).

## Context and orientation

Read these before starting. They are the source of truth.

- `docs/novel-ralph-harness-design.md` §4.2 (`novel done`; the exit-4
  compile-divergence carve-out and the agreement with `novel compile --check`),
  §4.3 (`novel compile` and `--check`; "consistent separators"), §5.4
  (disk-authoritative reconciliation; the detector's vacuous-satisfaction
  polarity). These establish *why* the projection and the path are shared
  facts, and why the detector's polarity is deliberately the opposite.
- `docs/issues/audit-4.1.2.md` — the originating audit. Finding 1 (the content
  polarity is duplicated; add `compile_is_current` beside the helper), Finding
  2 (`compiled.md`'s path has no single source across four modules; promote a
  `compiled_manuscript_path` + `COMPILED_REL` to `compile_model.py`). Finding 3
  (docstring prose) is roadmap 7.1.2, **not** this task; Finding 4 (the race
  window) is out of scope.
- `docs/adr-001-deterministic-judgemental-boundary.md` (detect-only;
  `check_compiled` writes nothing).
- `docs/adr-003-shared-interface-contract.md` (the envelope and exit-code
  contract this refactor must not perturb).
- `AGENTS.md` "Python verification and testing" (unit/behavioural/property
  discipline; snapshot rule) and "Markdown guidance".
- `docs/scripting-standards.md` and `docs/documentation-style-guide.md` for
  prose/comment conventions and Oxford spelling.

Key code, by full path:

- `novel_ralph_skill/state/compile_model.py` — owns `DRAFT_SEPARATOR`,
  `CompiledComparison`, `compiled_matches_drafts`, `present_draft_bodies`,
  `concatenate_drafts`. The new `compile_is_current`,
  `compiled_manuscript_path`, and `COMPILED_REL` land here. The read path it
  already builds (`compiled = working_dir / "manuscript" / "compiled.md"`,
  line 105) is the first internal call site to route through
  `compiled_manuscript_path`.
- `novel_ralph_skill/state/done_predicate.py` — `compile_consistent`
  (line 213-263) returns `compiled_matches_drafts(...) is
  CompiledComparison.MATCHES`; route it through `compile_is_current`.
- `novel_ralph_skill/commands/_compile.py` — holds `_COMPILED_REL`
  (line 74), the write join `root / "manuscript" / "compiled.md"` (line 147),
  `check_compiled` (line 169) with `if verdict is
  CompiledComparison.MATCHES:` (line 221). Route the predicate and the path
  seam; replace `_COMPILED_REL` with the imported `COMPILED_REL`.
- `novel_ralph_skill/commands/_novel_done.py` — `_failed_clause_message`
  (line 117) and `_sole_stale_compile` (line 159) each build `(root /
  "manuscript" / "compiled.md").exists()`; route through
  `compiled_manuscript_path`.
- `novel_ralph_skill/state/__init__.py` — re-exports the `compile_model`
  symbols (import block line 30-35, `__all__` line ~107-151). Add the three new
  names.
- `novel_ralph_skill/commands/_state_load.py:39` — `working_dir()` returns the
  cwd-relative `working/` directory (already the `working/` segment). This is
  what `compiled_manuscript_path` is joined onto in `compile_model.py` and
  `check_compiled`; `_novel_done.py` passes its `root` (also a `working/`
  directory).

Terms defined:

- *Content-polarity projection*: the boolean reduction of the three-valued
  `CompiledComparison` verdict to "is the compile current?" — `True` only for
  `MATCHES`. The §5.4 detector's reduction ("is this a violation?") is the
  *opposite* projection and is not this one.
- *Path seam*: a single named definition of where `compiled.md` lives — a
  `Path` join for filesystem reads/stats, and a working-relative string token
  for the deterministic envelope.
- *Working-relative token*: the POSIX string `working/manuscript/compiled.md`
  the envelope reports; it is **prefixed** with `working/`, unlike the
  filesystem `Path` built from `working_dir()`.

## Verified external facts (do not re-derive)

- **No external library behaviour is load-bearing for this task.** This is a
  pure internal-Python refactor: it adds no subprocess, no new console-script
  path, no new `--flag`, and no new third-party import. Therefore the standing
  cuprum / Cyclopts / `pytest-timeout` / `uv run` research the workflow
  mandates has **no bearing on any work item here** — there is no place in this
  plan where a cuprum catalogue, a Cyclopts argument, or a `pytest-timeout`
  override is exercised by a code change. (Verified by inspection: the four
  consumers are all reached either by direct function call in unit tests or
  through the already-existing `run(build_app(), …)` harness in the agreement
  and command suites; this task adds neither a new invocation surface nor a new
  subprocess. The existing e2e suites — `tests/test_compile_e2e.py`,
  `tests/test_novel_done_e2e.py` — already pin the installed behaviour through
  cuprum's `single_program_catalogue`, and they must stay green **unedited**,
  which is precisely the no-behaviour-change guarantee.) This is stated
  explicitly rather than hedged: there is no undecided external-library fork in
  this plan.
- The envelope token value is pinned by tests to the verbatim string
  `working/manuscript/compiled.md`: `tests/test_compile_check_unit.py:117,139`,
  `tests/test_compile_e2e.py:93,153`, `tests/test_compile_unit.py:114`,
  `tests/test_compile_snapshots.py:94`, `tests/test_compile_check_snapshots.py`,
  `tests/contract_drive_support.py:90`, and
  `tests/__snapshots__/test_command_surface_matrix.ambr`. (Verified by
  `git grep`.) `COMPILED_REL` must equal this string exactly.
- The state package already re-exports the `compile_model` surface
  (`novel_ralph_skill/state/__init__.py:30-35` import,
  `:107-151` `__all__`), so adding three names there is the established
  pattern, not a new mechanism. (Verified by inspection.)

## Plan of work

Three ordered, independently committable work items. Stage B (the seam + its
test) precedes Stage C (routing), so the routing edits land against a
pinned-and-green seam. Tests that assert *new* structure are written red first
(Work Item 2); the routing (Work Item 3) is a behaviour-preserving substitution
that the **existing, unedited** suites already cover.

### Work Item 1 — add the seam to `compile_model.py` and export it (Stage B)

In `novel_ralph_skill/state/compile_model.py`, add three members beside the
existing `DRAFT_SEPARATOR` / `CompiledComparison` / `compiled_matches_drafts`:

1. A module-level constant
   `COMPILED_REL = "working/manuscript/compiled.md"` — the working-relative
   POSIX token the envelope reports — with a docstring-comment stating it is
   the **working-prefixed** token (not a join of `working_dir()`), the single
   source for the value previously held as `_COMPILED_REL` in `_compile.py`
   (audit-4.1.2 Finding 2).
2. A function `compiled_manuscript_path(working_dir: Path) -> Path` returning
   `working_dir / "manuscript" / "compiled.md"`, with a docstring stating it
   takes an already-`working/`-anchored directory (so the result is **not**
   doubly prefixed) and is the single join rule for the compiled manuscript's
   on-disk location (audit-4.1.2 Finding 2; the module already owns
   `DRAFT_SEPARATOR` and the join rule).
3. A predicate `compile_is_current(verdict: CompiledComparison) -> bool`
   returning `verdict is CompiledComparison.MATCHES`, with a docstring stating
   it is the single content-polarity projection — only `MATCHES` is current,
   `ABSENT` and `DIVERGES` are not — and that the §5.4 detector deliberately
   uses the *opposite* polarity inline (audit-4.1.2 Finding 1; cross-reference
   the detector so a reader does not "fix" the asymmetry).

Route `compile_model.py`'s own read at line 105 through the new join:
`compiled = compiled_manuscript_path(working_dir)`.

Export all three from `novel_ralph_skill/state/__init__.py`: add them to the
`from novel_ralph_skill.state.compile_model import (...)` block and to
`__all__`, beside `compiled_matches_drafts` / `CompiledComparison`.

Validation:

- `uv run python -c "from novel_ralph_skill.state import compile_is_current,
  compiled_manuscript_path, COMPILED_REL, CompiledComparison; from pathlib
  import Path; print(COMPILED_REL); print(compiled_manuscript_path(Path('working')));
  print(compile_is_current(CompiledComparison.MATCHES),
  compile_is_current(CompiledComparison.ABSENT))"` prints
  `working/manuscript/compiled.md`, `working/manuscript/compiled.md`, and
  `True False`.
- `make all` green; commit (gate first).

Docs to read: design §4.3, §5.4; `audit-4.1.2.md` Findings 1 and 2;
`compile_model.py` as the structural template (mirror its docstring style and
the `CompiledComparison` cross-references).
Skills to load: `python-router` → `python-types-and-apis` (the predicate and
path-join signatures, the `Path` parameter typing) and `python-data-shapes`
(the `enum`-projecting predicate shape).

### Work Item 2 — pin the seam with a focused unit test (Stage B, red first)

Add the seam's pins to a new `tests/test_compile_model_seam.py` (or extend
`tests/test_compiled_matches_drafts.py` if it stays under the module cap —
prefer the dedicated file for a clean boundary). It must:

- Assert the predicate truth table exhaustively over all three
  `CompiledComparison` members:
  `compile_is_current(MATCHES) is True`;
  `compile_is_current(ABSENT) is False`;
  `compile_is_current(DIVERGES) is False`. (Parametrize over
  `CompiledComparison` so a future fourth member forces a decision — AGENTS.md
  unit discipline; this is a closed three-value enumeration, so example-based
  tests suffice and Hypothesis is not required, per `python-verification`.)
- Assert `COMPILED_REL == "working/manuscript/compiled.md"` (the byte-exact
  token; this is the same string the snapshot suites pin, restated at the seam
  so a hand-edit to the constant is red here, not only in a snapshot).
- Assert `compiled_manuscript_path(Path("working")) == Path("working") /
  "manuscript" / "compiled.md"`, and that `str(compiled_manuscript_path(
  Path("working")).as_posix()) == COMPILED_REL` — pinning the
  working-prefix asymmetry (the join of the `working/` directory reproduces the
  envelope token exactly, with no doubled prefix).

These are unit/example tests over pure functions — no `working/` tree, no
subprocess, no snapshot. Write them **red first** against the not-yet-added
symbols (import error / `AttributeError`), then green after Work Item 1 (or, if
WI1 and WI2 are committed together, watch the test fail by temporarily removing
one member, then restore — record the red/green in `Progress`).

Validation:

- `uv run pytest tests/test_compile_model_seam.py -q` passes.
- `make all` green; commit.

Docs to read: AGENTS.md "Python verification and testing" (unit + example
discipline; snapshots only for stable boundaries — this is *not* a snapshot
test); `tests/test_compiled_matches_drafts.py` as the parametrization template.
Skills to load: `python-router` → `python-testing` (parametrization over the
enum, ids) and `python-verification` (to confirm the closed enumeration needs
no Hypothesis/CrossHair/mutmut adversary — there is no generated input space
and the logic is a one-line projection).

### Work Item 3 — route the four consumers through the seam (Stage C)

Behaviour-preserving substitution. After this, no `is
CompiledComparison.MATCHES` and no inline `"manuscript" / "compiled.md"` join
remains outside `compile_model.py`.

1. `novel_ralph_skill/state/done_predicate.py:263` — replace
   `return compiled_matches_drafts(state, working_dir) is
   CompiledComparison.MATCHES` with
   `return compile_is_current(compiled_matches_drafts(state, working_dir))`.
   Add `compile_is_current` to the existing `compile_model` import block
   (line 50-51) and drop the now-unused `CompiledComparison` import **iff** no
   other reference to it remains in the module (check; the docstring references
   are textual, not imports). Trim the docstring's MATCHES explanation to a
   one-sentence "current iff `compile_is_current` holds" pointer (a light
   touch — the full prose consolidation is 7.1.2, so keep this minimal).
2. `novel_ralph_skill/commands/_compile.py` —
   - Replace the module constant `_COMPILED_REL =
     "working/manuscript/compiled.md"` (line 74) with the imported
     `COMPILED_REL`; add `COMPILED_REL`, `compiled_manuscript_path`, and
     `compile_is_current` to the `from novel_ralph_skill.state import (...)`
     block (line 58-59). Replace every `_COMPILED_REL` use (lines 156, 161,
     165, 225, 229, 234, 240) with `COMPILED_REL`.
   - Replace the write join `compiled_path = root / "manuscript" /
     "compiled.md"` (line 147) with `compiled_path =
     compiled_manuscript_path(root)`.
   - Replace `if verdict is CompiledComparison.MATCHES:` (line 221) with
     `if compile_is_current(verdict):`; drop the now-unused
     `CompiledComparison` import **iff** no other reference remains (check the
     docstring references are textual).
3. `novel_ralph_skill/commands/_novel_done.py` — replace both
   `(root / "manuscript" / "compiled.md").exists()` (lines 128, 173) with
   `compiled_manuscript_path(root).exists()`. This module currently has **no**
   `compile_model`/state-package import for the path seam — it imports only
   `DoneClauses, evaluate_done` from `novel_ralph_skill.state.done_predicate`
   (line 51) — so **add a new import statement**
   `from novel_ralph_skill.state import compiled_manuscript_path` (do not hunt
   for a block to extend; there is none). The message string and the carve-out
   logic are untouched.

No test is edited for new behaviour: the existing compile, done-predicate,
disk-evidence, agreement, snapshot, BDD, and e2e suites are the regression net
and must stay green **unedited**. That is the no-behaviour-change proof.

Validation:

- `git grep -n "is CompiledComparison.MATCHES" novel_ralph_skill/` returns
  hits only inside `compile_model.py` (the helper definition / docstring).
- `git grep -n '"manuscript" / "compiled.md"' novel_ralph_skill/` returns hits
  only inside `compile_model.py` (`compiled_manuscript_path`).
- `git grep -n '_COMPILED_REL' novel_ralph_skill/` returns nothing.
- `uv run pytest tests/test_compile_check_agreement.py
  tests/test_compile_check_unit.py tests/test_compile_unit.py
  tests/test_done_predicate.py tests/test_disk_evidence.py
  tests/test_novel_done_command.py -q` passes unchanged.
- `make all` green (full suite, including the snapshot, BDD, and e2e suites,
  all unedited); commit.

Docs to read: `audit-4.1.2.md` Findings 1 and 2; design §4.2 (the carve-out the
`_novel_done.py` sites guard); `tests/test_compile_check_agreement.py` (the
agreement invariant the predicate now structurally enforces).
Skills to load: `python-router` → `python-errors-and-logging` is **not** needed
(no error paths change); load `python-testing` only to confirm the existing
suites are the right regression net. Use `leta refs CompiledComparison` /
`leta refs compiled_matches_drafts` to confirm every MATCHES projection site is
accounted for before editing, and `leta` for the import-pruning checks.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-1`.

1. Confirm the branch and a clean tree:

        $ git branch --show
        roadmap-7-1-1
        $ git status --porcelain   # expect empty before starting

2. Work Item 1: add the seam to `compile_model.py`, route its own read, export
   from `state/__init__.py`. Verify:

        $ uv run python -c "$(printf '%s\n' \
            'from pathlib import Path' \
            'from novel_ralph_skill.state import (compile_is_current,' \
            '    compiled_manuscript_path, COMPILED_REL, CompiledComparison)' \
            'print(COMPILED_REL)' \
            'print(compiled_manuscript_path(Path(\"working\")).as_posix())' \
            'print(compile_is_current(CompiledComparison.MATCHES),' \
            '      compile_is_current(CompiledComparison.ABSENT))')"
        working/manuscript/compiled.md
        working/manuscript/compiled.md
        True False

   Then `make all`; commit (gate first).

3. Work Item 2: add `tests/test_compile_model_seam.py`, red first, then green:

        $ uv run pytest tests/test_compile_model_seam.py -q
        ... passed

   Then `make all`; commit.

4. Work Item 3: route the four consumers; then verify the duplication is gone:

        $ git grep -n "is CompiledComparison.MATCHES" novel_ralph_skill/
        novel_ralph_skill/state/compile_model.py: ...   # only the helper itself
        $ git grep -n '_COMPILED_REL' novel_ralph_skill/
        # (no output)

   Then `make all` (full suite, all unedited); commit.

Each commit is gated by `make all` per the workflow standing rule. There are no
Markdown changes in Work Items 1-3, so `make markdownlint` / `make nixie` are
**not** required for the code commits; they are required only for the ExecPlan
file itself (this document), run once when the plan is committed. Commit only
when the user has approved the plan and asked to proceed.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `tests/test_compile_model_seam.py` passes (and failed red before Work
  Item 1's symbols existed). Every pre-existing compile, done-predicate,
  disk-evidence, agreement, snapshot, BDD, and e2e suite passes **without
  edit** — that is the no-behaviour-change proof (roadmap 7.1.1 success
  criterion).
- Lint/typecheck: `make all` (build, check-fmt, lint, typecheck, test) is green
  — Ruff, `interrogate` 100% (the three new symbols carry docstrings), Pylint
  (module under the 400-line cap), `pyright`/`ty` (the new signatures and the
  three new exports resolve).
- Structural: the three `git grep` checks in Work Item 3 confirm the
  projection and the path literal each have exactly one home
  (`compile_model.py`).
- en-GB Oxford spelling throughout new docstrings and comments.

Quality method (how we check):

- Local: `make all` after each work item; the same gates run in CI
  (`.github/workflows/ci.yml`).
- Markdown gates: `make markdownlint` and `make nixie` on this ExecPlan file
  (the only Markdown this task touches). No Mermaid is added; `make nixie` is
  run per the workflow rule for Markdown changes.
- Behaviour acceptance: the agreement test
  `tests/test_compile_check_agreement.py` still passes, proving `novel compile
  --check` and `compile_consistent` agree on every corpus fixture — now backed
  by one shared `compile_is_current` predicate rather than two hand-written
  projections.

## Idempotence and recovery

- Every edit is a behaviour-preserving substitution or an additive symbol;
  re-running any work item is safe. No `working/` tree, `state.toml`, or
  `compiled.md` is mutated by any step (the refactor is read/join only;
  ADR-001).
- If a commit's gate fails, fix forward on the same work item; do not advance.
  If a snapshot moves (it must not), treat it as a Tolerance breach (behaviour
  drift) — stop and escalate rather than re-recording the snapshot.
- The new test file is additive; deleting it leaves the tree buildable. The
  routing edits are reversible by restoring the inline `is
  CompiledComparison.MATCHES` / literal joins, but there is no reason to.

## Interfaces and dependencies

- New, in `novel_ralph_skill/state/compile_model.py` (and re-exported from
  `novel_ralph_skill/state/__init__.py`):

        COMPILED_REL: str  # == "working/manuscript/compiled.md" (working-prefixed token)

        def compiled_manuscript_path(working_dir: Path) -> Path:
            """Return ``working_dir / "manuscript" / "compiled.md"`` …"""

        def compile_is_current(verdict: CompiledComparison) -> bool:
            """Return whether ``verdict`` means the compile is current …"""

- Reused, unchanged: `CompiledComparison`, `compiled_matches_drafts`,
  `present_draft_bodies`, `concatenate_drafts`, `DRAFT_SEPARATOR`;
  `commands._state_load.working_dir`; the `desloppify`/`novel-compile`/
  `novel-done` Cyclopts apps and the shared `run`/envelope machinery (all
  untouched).
- Dependencies: **no new third-party dependency**; no new import beyond the
  three new symbols crossing module boundaries. No external library behaviour
  (cuprum, Cyclopts, `pytest-timeout`, `uv run`) is exercised by any code
  change in this task (see "Verified external facts").

## Revision note

- 2026-06-26: initial DRAFT. The file previously held a stale `ai-isms.toml`
  ExecPlan that did not match the renumbered roadmap entry 7.1.1; it was
  discarded (Decision Log) and rewritten for the actual task — extracting the
  `compile_is_current` predicate and the `compiled_manuscript_path` /
  `COMPILED_REL` path seam into `compile_model.py` and routing the four
  consumers through them. Decomposed into three ordered, gate-passable work
  items (seam + export; seam test red-first; route the consumers). Pinned the
  load-bearing facts against source: the envelope token's byte-exact value and
  its snapshot pins (verified by `git grep`), the working-prefix asymmetry
  between the token and the `working_dir()`-anchored join, the detector's
  deliberately-opposite polarity that is excluded from the predicate
  (audit-4.1.2 Finding 1), and the established `state/__init__.py` re-export
  pattern. Stated explicitly that no external-library behaviour is load-bearing
  for this internal refactor — there is no undecided external fork.
- 2026-06-26 (round 2): resolved the two round-1 logisphere blocking defects.
  (1) Narrowed the Purpose-section path observable from the loose
  `git grep 'manuscript/compiled.md'` to the quoted code-join form
  `'"manuscript" / "compiled.md"'`, and (2) restricted the MATCHES observable
  to the `is CompiledComparison.MATCHES` projection form rather than all
  `CompiledComparison.MATCHES` references. Both observables are now explicitly
  scoped to executable code and disclaim the docstring-prose hits that belong to
  roadmap 7.1.2 (verified by `git grep` that those prose hits survive at
  `_compile.py:5,110,184`, `_novel_done.py:164`, `done_predicate.py:86,217,229`
  and are the intended end state, not a failure). Also actioned the round-1
  advisories: reworded WI3 step 3 to add a new
  `from novel_ralph_skill.state import compiled_manuscript_path` import in
  `_novel_done.py` (which has no existing state import to extend), and
  instructed WI2 to record the red→green evidence in `Progress`/`Surprises`. No
  work-item count, ordering, code edit, or validation command changed; this
  round is a documentation-observable correction only.
