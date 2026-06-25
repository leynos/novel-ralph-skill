# Implement the validated chapter-manifest mutator that populates `[chapters]`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (all nine work items landed; see Progress and Outcomes).

## Purpose / big picture

The chapter manifest (`[chapters]` in `working/state.toml`) is the one piece of
harness state that currently has **no sanctioned command to write it**. A
chapter planned in `working/plan/chapter-outline.md` therefore has no validated
path into `[chapters]`, and the per-chapter drafting loop is blocked: with a
draft on disk but an empty manifest, `novel-state check` exits 4 on
`manifest-disk-bijection`, `novel-compile` exits 3, and `recount` returns an
empty map. Per ADR 001 (`scripts detect and report; the model adjudicates`) and
design §4.1, **all** state mutation goes through validated commands and direct
`state.toml` edits are forbidden, so the manifest is no exception.

After this change a novelist (or the harness agent) can run a single command:

```bash
novel-state set-chapters --chapters '[
  {"number": 1, "slug": "the-summons", "title": "The Summons", "target_words": 3200},
  {"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800}
]'
```

and observe:

- `[chapters]` in `working/state.toml` is populated with the two entries, in
  ascending number order, with the file's hand-authored comments and layout
  preserved (the `tomlkit` round-trip, ADR 002);
- the on-disk chapter directories `working/manuscript/chapter-01/` and
  `chapter-02/` now exist, so `novel-state check` finds the manifest and disk
  in bijection and exits 0, and `recount`/`novel-compile` operate on the real
  directories;
- a recovery receipt is appended to `working/log.md`;
- an **incoherent** plan — numbering that is not contiguous from 1, or a
  duplicate number — is refused with **exit 3** and writes nothing, leaving the
  prior `state.toml` byte-for-byte intact;
- a **malformed** invocation — JSON that does not parse, a wrong-typed field, or
  a missing field — is refused with **exit 2** (usage error) before the body
  runs.

Success is proven end-to-end: a chapter planned in `chapter-outline.md` reaches
`[chapters]` only through the command (never a hand-edit); the command refuses
a non-contiguous or incomplete manifest with exit 3; and `check`, `recount`, and
`novel-compile` then operate correctly on the real chapter directories. This
is roadmap task 2.2.3 (`docs/roadmap.md` lines 702-727); design
`docs/novel-ralph-harness-design.md` §4.1, §5.1, §5.2; and ADR 001.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No direct `state.toml` edit; command-only.** The manifest reaches
  `[chapters]` solely through this command (ADR 001; design §4.1, §5.1 lines
  455-461). Tests must prove a chapter reaches the manifest *only* through the
  command.
- **Validate before persist.** The body validates the *proposed* manifest
  before any write. A refusal (exit 3) leaves the prior `state.toml`
  byte-for-byte intact (design §3.2, §3.4; developers' guide "Validate before
  persist"). Reuse the existing `_refuse_if_incoherent` discipline in
  `novel_ralph_skill/commands/_state_mutators.py`.
- **Lossless round-trip.** Writes go through the `tomlkit` document seam
  (`load_document` → edit → `write_document_atomically`), never a re-serialised
  typed model (ADR 002; design §5.3; `novel_ralph_skill/state/document.py`).
- **Atomic, multi-file discipline.** `set-chapters` writes `state.toml`, creates
  `chapter-NN/` directories, and appends a `log.md` receipt — a genuinely
  multi-file turn — so it brackets its writes with a `[pending_turn]` intent
  record (design §3.4; developers' guide "Checker/mutator segregation"). It
  deletes no file under `working/`. The roadmap mandates this discipline
  explicitly ("writes `[chapters]` atomically … with the log receipt and
  `[pending_turn]` discipline", roadmap 2.2.3 lines 715-719), so a
  manifest-only write is **out of scope** (see Decision Log D9 for the
  trade-off analysis).
- **Manifest persists AT the intent write (round-2 B2).** Unlike `reconcile`
  (whose payload — the recount — is recomputed from disk and so persists last),
  `set-chapters`'s payload is the agent's *judgement* (slug/title/target_words)
  and is **not** recomputable from disk. It is therefore written into the
  document and persisted **together with** the `[pending_turn]` record in the
  *first* atomic write, **before** any directory is created. The fixed order
  is: edit `[chapters]` + open `[pending_turn]` → **single atomic write** →
  create `chapter-NN/` directories → append `log.md` receipt → clear
  `[pending_turn]` → final atomic write. Every torn state from the first write
  onward therefore has the full manifest on disk and only the
  deterministically-derivable empty directories outstanding.
  (`open_pending_turn` mutates the in-memory document in place, so a single
  `write_document_atomically` carries both the `[chapters]` edit and the intent
  record — verified against `state/document.py::open_pending_turn`, which only
  appends the `[pending_turn]` table and does not touch `[chapters]`.)
- **Sanctioned torn-turn recovery (round-2 B1).** A crash *after* the intent
  write leaves a populated `operation="set-chapters"` `[pending_turn]` over a
  **persisted, populated** manifest, with one or more `chapter-NN/` directories
  missing (the realistic crash, including the **partial-directory** case:
  manifest `{1,2}`, on-disk `{1}`). That partial state fires
  `manifest-disk-bijection` (a refuse-class invariant), which under the
  *current* precedence (`reconcile.py::derive_reconciliation` lines 258-264)
  short-circuits to REFUSE (exit 4) **before** the pending-turn branch runs.
  Work item 3a therefore makes a **scoped precedence change**: when an
  `operation="set-chapters"` `[pending_turn]` is present and the *only* fired
  refuse-class violation is a `manifest-disk-bijection` that is **fully
  explained by** the pending-turn's declared-but-missing chapter directories
  (manifest ⊇ on-disk, and the set difference equals exactly those missing
  declared dirs), the pending turn is classified ahead of REFUSE and COMPLETEs
  (creates the missing dirs). Any *unexplained* bijection break — a stray
  draft, an orphan directory, a manifest gap not accounted for by the pending
  turn — still REFUSEs. Recovery is a single sanctioned command:
  `novel-state reconcile`. No manual `mkdir` and no re-run of `set-chapters`
  (which D3 refuses) is required.
- **Exit-code contract.** Coherent write → exit 0; semantically incoherent
  manifest → exit 3 (`StateInputError`); malformed/ill-typed invocation → exit 2
  (`CycloptsError`, the runner's existing mapping). Never exit 1 for a refusal
  (design §3.2; `novel_ralph_skill/contract/runner.py:run`).
- **Write-shaped success vocabulary.** The success `result` names *what it
  changed* (the written chapters), never `check`'s `violations` read shape
  (developers' guide "Success `result` is write-shaped"; audit-2.2.2 Finding 2).
- **File-size cap.** No code file exceeds 400 lines (AGENTS.md "Keep file size
  manageable"). The mutator body lands in its own module
  `novel_ralph_skill/commands/_set_chapters.py`, not bolted onto
  `_state_mutators.py`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages (AGENTS.md; en-gb-oxendict).

## Tolerances (exception triggers)

- **Scope:** if implementation needs to touch more than ~12 files (net) or more
  than ~550 lines of production code (excluding tests/docs), stop and escalate.
  The count includes the two sibling-task reconcile modules Work item 3a extends
  (`state/reconcile.py`, `commands/_reconcile.py`) for torn-turn recovery
  (D8). Work item 3a is a **deliberate, design-reasoned precedence change** to
  `derive_reconciliation` (a `set-chapters` pending-turn explained by a missing
  chapter-dir set is classified ahead of the bijection REFUSE), recorded in ADR
  008 and design §5.4 (round-2 B1/B3) — it is **not** a "focused classifier
  tweak" and the plan no longer claims it is. The escalation trigger is
  narrower: if landing the precedence change requires altering the
  `Reconciliation` dataclass shape, the `derive_reconciliation` *signature*,
  the disk-evidence detector ordering, or the `check`/`reconcile`
  shared-derivation contract — or if the scoped "explained-by" predicate cannot
  be expressed without inverting the refuse-class precedence for invariants
  *other than* `manifest-disk-bijection` — stop and escalate. Adding a guarded
  branch ahead of the existing refuse arm (the planned shape) is in scope.
- **Interface:** if the existing `make_contract_app` / `run` contract, the
  `tomlkit` writer seam, or any `state/` public signature must change to land
  this, stop and escalate (this plan expects to *add*, not alter, those).
- **Dependencies:** if a new external dependency is required, stop and escalate.
  This plan requires none: cyclopts 4.18.0 and tomlkit are already locked.
- **Iterations:** if a gate (`make all`) still fails after 3 fix attempts on one
  work item, stop and escalate.
- **Ambiguity — directory creation:** if review concludes `set-chapters` must
  **not** create `chapter-NN/` directories (leaving bijection to a later loop
  step), stop and escalate — this materially changes the success criterion (see
  Decision Log D2).
- **Ambiguity — command name:** the roadmap offers `set-chapters` *or*
  `plan-chapters`. This plan picks `set-chapters` (Decision Log D1). If review
  prefers `plan-chapters`, that is a one-line change; do not block on it, but
  record it.

## Risks

```plaintext
    - Risk: cyclopts list[dataclass] JSON parsing behaves differently in the
      built/installed wheel than in-process.
      Severity: medium
      Likelihood: low
      Mitigation: the JSON-list mechanism is verified in-process against the
      locked cyclopts 4.18.0 (Surprises & Discoveries S1) and is pinned again by
      an installed-binary e2e (Work item 6), mirroring test_recount_e2e.py.

    - Risk: a crash after the intent write but before all chapter-NN/ directories
      are created leaves a populated manifest with a PARTIAL directory set
      (manifest {1,2}, on-disk {1}), so manifest-disk-bijection fires; under the
      current reconcile precedence that refuse-class violation short-circuits to
      REFUSE (exit 4) before the pending-turn branch runs, and D3 refuses a
      set-chapters re-run — so the obvious recovery is blocked. This is the most
      likely 03:00 incident (round-2 advisory A2).
      Severity: high
      Likelihood: low
      Mitigation: RESOLVED by the round-2 redesign (Decision Log D8, D10). TWO
      changes are needed and BOTH are in the plan. (1) Write ordering (B2): the
      populated manifest persists AT the intent write, together with the
      [pending_turn] record, BEFORE any directory is created (Work item 3,
      Constraint "Manifest persists AT the intent write"). So every torn state
      from the first write onward has the agent's judgement on disk and only
      empty, manifest-derivable directories outstanding — the manifest is always
      recoverable. (2) Precedence (B1): Work item 3a adds a guarded branch to
      derive_reconciliation so a set-chapters pending-turn whose missing chapter
      dirs FULLY EXPLAIN the fired manifest-disk-bijection is classified ahead of
      REFUSE and COMPLETEs (creates the missing dirs). The partial-directory case
      is the one the test in Work item 3a/5 drives explicitly (A2), not just the
      all-dirs-missing case. An unexplained bijection break still REFUSEs.

    - Risk: a non-empty prior manifest (re-running set-chapters) silently
      overwrites or leaves orphaned chapter-NN/ directories.
      Severity: medium
      Likelihood: medium
      Mitigation: Work item 3 pins the prior-manifest policy (Decision Log D3):
      refuse with exit 3 when [chapters] is already non-empty, so set-chapters is
      a one-shot populate, not an editor. A later task owns re-planning. Torn-turn
      completion is delegated to reconcile (D8), so this strict refusal does not
      strand a half-applied turn (the failure mode the round-1 reviewer raised).

    - Risk: a stray chapter-NN/ directory the manifest does not name (a leftover
      from an aborted run) breaks the bijection even after a successful
      set-chapters (the bijection is set-equality, not subset).
      Severity: low
      Likelihood: low
      Mitigation: set-chapters creates the manifest's directories but prunes none
      (the no-deletion constraint). D3's empty-prior refusal does not cover this
      case (the manifest may be empty while disk holds stray dirs). This is the
      existing draft-without-manifest-entry bijection variant that check reports
      with exit 4; reconcile's REFUSE/ROLLBACK paths surface it. Recorded as a
      known, pre-existing edge, not introduced by this task (round-1 review
      finding 5); set-chapters adds no new stray-dir behaviour.

    - Risk: the validator (validate_state, §5.2) does not own manifest
      contiguity/uniqueness as a pure-state rule, so reusing _refuse_if_incoherent
      alone would not catch a duplicate/non-contiguous manifest.
      Severity: high
      Likelihood: high (this is the core of the task)
      Mitigation: Work item 2 adds a pure manifest-coherence predicate the body
      calls *before* the §5.2 validate-before-persist pass; the two checks are
      complementary (see Decision Log D4). Confirmed: validate.py has no
      contiguity/uniqueness predicate today.

    - Risk: chapter slugs collide or are filesystem-unsafe, producing a
      directory clash.
      Severity: low
      Likelihood: low
      Mitigation: the on-disk directory name is derived from the chapter
      *number* (chapter-NN), not the slug (state/_disk_paths.py), so slug
      collisions cannot collide directories. Slug uniqueness is a manifest-quality
      concern; Work item 2 decides whether to also reject duplicate slugs
      (Decision Log D5).
```

## Progress

```plaintext
    - [x] (done) Work item 1: ChapterPlanEntry input dataclass + module
      scaffold and red unit test. Work item 0 folded in: `chapter_dir_name`
      re-exported from `novel_ralph_skill.state` (re-export of
      `_disk_paths._chapter_dir_name`, the small-diff choice, recorded as D11).
      `make all` green except the intended red
      `test_set_chapters_writes_manifest` (NotImplementedError); `make audit`
      green. CodeRabbit: 1 "critical" flagging the stub — deliberate red-green
      staging, resolved by Work item 3 in this same branch (CodeRabbit's own
      guidance accepts shipping the implementation in the PR); 1 minor execplan
      reference fix (WI3a now names `test_reconcile.py` /
      `test_reconcile_derivation.py`, not the non-existent
      `test_reconcile_unit.py`) applied.
    - [x] (done) Work item 2: pure manifest-coherence validator
      (contiguity, uniqueness, ascending order). `manifest_coherence_violations`
      lives in `_set_chapters.py` (module ~150 lines, well under the ~250
      threshold for splitting to `state/manifest.py`), with five named rule
      constants (`chapters-non-empty`, `numbers-unique`,
      `numbers-contiguous-from-1`, `slugs-unique`, `target-words-positive`) in a
      fixed `MANIFEST_COHERENCE_RULE_NAMES` order. Table-driven unit tests cover
      each breach. `make all` green except the still-red Work item 3 headline
      test; `make audit` green. CodeRabbit: 3 minor findings, all in the
      committed `*.review-*.md` design-review notes (not the WI2 code); the only
      genuine markdownlint failure (round3 MD013 line-length) was fixed, the
      fence-language findings were false positives (the fences already carry a
      `python` label).
    - [x] (done) Work item 3: set_chapters body — persist the populated
      [chapters] + [pending_turn] AT the intent write (B2/D10), THEN create
      chapter-NN/ dirs, THEN log receipt, THEN clear. Implemented as a LOCAL
      D10 bracket (`_write_manifest_turn`) rather than generalising
      `_run_reconcile_bracket`, because the ordering deliberately differs
      (Decision D12): reconcile persists its recomputable recount last, but the
      manifest persists FIRST. `SET_CHAPTERS_OPERATION = "set-chapters"` is a
      named constant in `state/schema.py` (beside `PendingTurn`), shared by the
      writer and Work item 3a's reconcile reader (no repeated literal). Unit
      tests cover the headline write (now green), the non-empty-prior refusal
      (D3), the incoherent-plan refusal, comment preservation (ADR 002
      round-trip), and the D10 ordering guarantee (mkdir-failure injection
      proves the manifest + intent persist before any directory). `make all`
      fully green (999 passed); `make audit` green. CodeRabbit: 4 minor, all in
      the execplan/review docs — fixed the genuine stray-space path typo
      (`working/manuscript/ chapter-01/`); skipped the `novel state` rename
      (false positive — `novel-state` is the canonical console-script name in
      this repo, ADR 005/`commands/names.py`), the absolute-worktree-path note
      (intentional record of this run's worktree), and the review-r1
      title-case nit (a proper-noun title, not a docs heading-style breach).
    - [x] (done) Work item 3a: scoped precedence change in
      derive_reconciliation so a set-chapters pending-turn explained by its
      missing chapter dirs is classified ahead of the bijection REFUSE and
      COMPLETEs (creates the dirs); resolves round-2 B1/B3 (D8). The guarded
      branch (`_set_chapters_turn_explains_bijection` +
      `_complete_set_chapters_turn`) precedes the refuse arm; the
      `commands/_reconcile.py` COMPLETE dispatch gains a mkdir branch keyed on
      `operation == "set-chapters"`. The pure path-parsing helpers
      (`_chapter_number_of`, `_declared_chapter_numbers`) were placed in
      `state/_disk_paths.py` (beside the sibling chapter-number parsers) to keep
      `reconcile.py` under the 400-line cap, exactly as the plan's escalation
      note anticipated. Tests: the decisive partial-directory case, the
      all-dirs-missing case, three negative still-REFUSE cases (orphan dir,
      second refuse-class violation, undeclared missing dir), and the torn
      `reconcile` regression — all green. **Amendment to Work item 3 (D13):**
      driving `check` after a real `set-chapters` exposed that the populated
      manifest out-keyed the empty `[word_counts].by_chapter`, firing the §5.4
      `word-counts-cover-drafts` and making `check` exit 4 — failing the success
      criterion. The Work item 3 body now seeds `by_chapter` with a zero entry
      per chapter (Surprise S7, Decision D13), so `check` exits 0; the WI3
      headline unit test now asserts both `validate_state` and
      `check_disk_evidence` are clean. `make all` green (1005 passed); `make
      audit` green. CodeRabbit: 1 major (bare asserts in the reconcile test) —
      fixed by adding messages to every assertion; 3 trivial/minor in the plan
      docs — the operation-constant and helper-placement findings are already
      satisfied (the literal IS a shared `SET_CHAPTERS_OPERATION` constant, and
      only the pure path parsers live in `_disk_paths.py` while the predicate
      stays in `reconcile.py`), and the stale `test_reconcile_unit.py` reference
      was already corrected in the WI1 commit (the prose explicitly states it
      does not exist).
    - [x] (done) Work item 4: register set-chapters in the novel-state app;
      command-surface matrix update. The subcommand is registered in `build_app`
      delegating to `_set_chapters.set_chapters`. Discovery: Cyclopts resolves the
      `list[ChapterPlanEntry]` annotation via `get_type_hints` against the
      command function's module `__globals__`, so `ChapterPlanEntry` must be a
      *runtime* module global of `novel_state.py` — a builder-local import is not
      in scope (verified by an in-process probe raising `NameError`). The import
      is therefore placed at the module bottom (after `STATE_INPUT_ERRORS` /
      `state_path` / `working_dir` to avoid the `_state_mutators` circular import)
      with a documented `# noqa: E402, TC001` (a permanent, rationale-bearing
      suppression, not a temporary one). **(Superseded in Work item 7, S8:** the
      bottom-import was fragile when `_set_chapters` is imported first;
      `ChapterPlanEntry` moved to the leaf module `commands/_chapter_plan_entry.py`
      and `novel_state.py` now imports it top-level, dropping the `E402`.) The two
      command-surface-matrix
      mutator-exclusion lists and the `build_app`/module docstrings now name
      `set-chapters`. An in-process registration test drives
      `novel-state set-chapters --chapters '[...]'` to exit 0 and a malformed
      `--chapters` to exit 2. `make all` green (1007 passed); `make audit` green.
      CodeRabbit: 5 findings — the `_drive` `pytest.raises(SystemExit)` without a
      `match` mirrors the established reconcile/recount `_drive` house pattern (the
      exit code is asserted explicitly afterwards), so skipped; the `ty check`
      naming is the accurate literal tool invocation, so kept; the
      helper-placement note was updated to record that only the pure path parsers
      moved to `_disk_paths.py` while the predicate stays in `reconcile.py`; the
      stray-space-path and `test_reconcile_unit.py` findings are stale (both
      already corrected in earlier commits).
    - [x] (done) Work item 5: behavioural (pytest-bdd) scenarios.
      `tests/features/set_chapters.feature` + `tests/steps/set_chapters_steps.py`
      + `tests/test_set_chapters_bdd.py` (the binder + star-import), mirroring the
      recount wiring. Five scenarios: the coherent plan reaches `[chapters]` and a
      follow-up `check` exits 0; a non-contiguous plan and a duplicate-number plan
      each refuse with exit 3 leaving `state.toml` unchanged; a re-run against a
      populated manifest refuses (D3); and the decisive **partial-directory** torn
      turn (manifest 1-3, on-disk 1) where `check` reports exit 4 and `reconcile`
      creates the missing dirs, clears the record, and a follow-up `check` exits 0.
      `make all` green (1012 passed); `make audit` green. CodeRabbit: 3 findings —
      the registration test now shares an `empty_manifest_tree` fixture across its
      two cases (trivial dedupe applied); the reconcile-test bare-assert finding is
      stale (those asserts already carry messages); and the plan's scope-tolerance
      figure was reconciled (the revision note now reads ~12 files to match the
      Tolerances section).
    - [x] (done) Work item 6: end-to-end (entry-point + installed-binary)
      proofs. `tests/test_set_chapters_e2e.py`: a fast entry-point proof through
      `stub.novel_state()` (exit 0, the `{chapters}` envelope), the installed
      exit-0 proof, two installed exit-2 shape-fault proofs (malformed JSON and a
      missing required field — both cyclopts `CoercionError` → exit 2, S2), and an
      installed exit-3 proof (a non-contiguous plan, the body's semantic refusal).
      cuprum API pinned to the same symbols `test_recount_e2e.py` uses. All five
      pass (the installed cases reuse the module wheel). `make all` green (1017
      passed); `make audit` green. CodeRabbit: 4 minor — added failure messages to
      the e2e and registration asserts (CodeRabbit flagged bare asserts even
      though the recount-e2e template uses them); the reconcile-test
      `pytest.raises(SystemExit)`-without-`match` follows the established `_drive`
      house pattern (exit code asserted explicitly), so skipped; and the
      `make fmt` docs-validation suggestion was declined deliberately — `make fmt`
      runs `mdformat-all`, which mass-reformats every doc in the tree (the
      well-known churn the repository's stash history shows is repeatedly
      discarded), so `make markdownlint` + `make nixie` remain the docs gates.
    - [x] (done) Work item 7: property test for the coherence validator.
      `python-verification` confirmed Hypothesis is the right adversary (a pure,
      total `Sequence[ChapterPlanEntry] -> tuple[str, ...]` with algebraic
      invariants). `tests/test_set_chapters_properties.py` builds coherent plans by
      construction (a shuffled `range(1, n+1)`, distinct slugs, positive targets —
      no filtering trap) and asserts an empty verdict; the perturbation properties
      derive a single breach from a coherent seed and assert the matching rule.
      **Discovery (S8):** the property test importing `_set_chapters` *first*
      exposed that Work item 4's bottom-of-module `ChapterPlanEntry` import in
      `novel_state.py` was circular when `_set_chapters` is the entry import. Fixed
      by moving `ChapterPlanEntry` to a dependency-free leaf module
      `commands/_chapter_plan_entry.py`, imported as a runtime global by both
      `novel_state.py` (top-level, `# noqa: TC001`) and `_set_chapters.py` (which
      re-exports it). `make all` green (1023 passed); `make audit` green.
      CodeRabbit: the review service stalled in the "summarizing" phase across
      three attempts (one ~15-minute hang plus two ~12-14-minute `timeout`s, with a
      60s backoff between), never reaching findings — a transient service-side hang,
      not a 429/rate-limit. Per the workflow's rate-limit policy this is recorded
      and the work item proceeds; the deterministic gates (`make all`,
      `make audit`) are green and the change is a new property file plus a clean
      leaf-module refactor. See Open issues.
    - [x] (done) Work item 8: ADR 008 + design/developers'/users' guide +
      SKILL.md Phase 7 bridge + contents index. Added
      `docs/adr-008-chapter-manifest-mutator.md` recording the name, the
      `--chapters` JSON input shape, the exit-2/exit-3 split, directory creation,
      the non-empty-prior refusal, the pure-coherence-predicate placement, the
      manifest-only rejection, the write-at-intent ordering (D10), and the
      torn-turn recovery precedence (D8). Amended the design §3.3 checker/mutator
      table, §4.1 subcommand table, §5.1 `[chapters]` bullet, and **§5.4** (the
      recomputable-artefact enumeration item 2 and the precedence statement).
      Extended the developers' guide mutator list and the multi-file-mutator note
      (the ordering difference vs reconcile, and reconcile's new COMPLETE branch).
      Documented `novel-state set-chapters` in the users' guide (the `--chapters`
      JSON input, exit 0/2/3, the `{chapters}` result, and the reconcile-recovery
      note). Bridged it into `SKILL.md` Phase 7 as the phase-exit step (the
      single-quoted multi-chapter JSON form and the reconcile recovery, never a
      re-run or hand edit). Indexed ADR 008 (and the previously-unindexed ADR 007)
      in `docs/contents.md`. `make markdownlint` and `make nixie` clean (the
      design Mermaid validates); `make all` green (1023 passed, no doc-asserting
      test broke); `make audit` green. CodeRabbit: the review service stalled in
      the "summarizing" phase again (two `timeout`s, with a 120s backoff between),
      never reaching findings — the same transient service-side hang that affected
      Work item 7. Recorded in Open issues; the deterministic gates and the
      markdown gates are green and the change is documentation only.

## Surprises & discoveries

```plaintext
    - Observation (S1): cyclopts 4.18.0 parses a list[dataclass] keyword
      parameter from a JSON array in one argument *and* from repeated single
      --chapters objects.
      Evidence: ran in the worktree venv —
      `app(["setch","--chapters","[{...},{...}]"])` produced
      `[Ch(number=1,...), Ch(number=2,...)]`; documented at
      cyclopts.readthedocs.io/en/v4.18.0/user_classes.html "JSON List Parsing".
      Impact: the chapter plan is ingested as `--chapters '<json-array>'`, no
      bespoke parser; the element type must not be union'd with str.

    - Observation (S2): malformed JSON, a missing dataclass field, and a
      wrong-typed field all raise cyclopts.exceptions.CycloptsError
      (CoercionError) at parse time, which runner.run maps to exit 2, not 3.
      Evidence: probed the same app with `"[{not json"`,
      `'[{"number":1,"slug":"a"}]'`, and a string number — each raised
      CoercionError; runner.py lines 225-232 map CycloptsError → USAGE_ERROR (2).
      Impact: "required fields present" splits across two exit codes — a missing
      field is exit 2 (cyclopts), a *semantically* incoherent plan
      (non-contiguous, duplicate) is exit 3 (the body). Both are pinned by tests
      (Decision Log D6).

    - Observation (S3): no production code creates chapter-NN/ directories
      today; state/_disk_paths.py::_chapter_dir_name is the (module-private)
      naming helper, imported directly by several state modules.
      Evidence: grep across novel_ralph_skill/ — only mkdir is in
      novel_state.py::_init (the working/ skeleton), never chapter dirs.
      Impact: set-chapters is the natural owner of chapter-directory creation;
      Work item 3 reuses the directory-name helper (Work item 0 exports it).

    - Observation (S5, corrected round 2): the existing reconcile cannot finish a
      torn set-chapters turn, AND the blocker is the refuse-class PRECEDENCE, not
      only the recomputable-basename set. Verified by source read:
      (a) derive_reconciliation (state/reconcile.py lines 258-264) evaluates the
      refuse-class FIRST — `refuse = [n for n in fired if n in _REFUSE_CLASS]; if
      refuse: return _refuse(...)` — and only THEN reaches the pending-turn branch.
      (b) _REFUSE_CLASS (lines 78-83) contains MANIFEST_DISK_BIJECTION.
      (c) _check_manifest_disk_bijection (disk_evidence.py lines 112-134) fires
      whenever `manifest != on_disk` (set-equality + contiguity), with NO
      pending-turn exemption. So a PARTIAL-directory torn set-chapters turn
      (manifest {1,2}, on-disk {1}) returns REFUSE before _classify_pending_turn
      runs — exactly the round-2 B1 finding. Editing _RECOMPUTABLE_BASENAMES /
      _classify_pending_turn alone (the round-1 plan) is therefore DEAD CODE in
      the realistic crash.
      Impact: Work item 3a must change the PRECEDENCE in derive_reconciliation
      (add a guarded branch ahead of the refuse arm), not just the classifier. The
      branch is narrowly scoped: it fires only when (i) a [pending_turn] with
      operation=="set-chapters" is present, (ii) the fired refuse-class is exactly
      {manifest-disk-bijection} (no other contradiction), and (iii) that bijection
      break is FULLY EXPLAINED by the pending-turn's declared-but-missing chapter
      dirs (manifest ⊇ on_disk and manifest \ on_disk == the missing declared
      chapter numbers). When all three hold it COMPLETEs; otherwise the existing
      REFUSE arm runs unchanged. The Reconciliation dataclass already carries
      `operation` and `missing_paths` (lines 137-145), so no shape change is
      needed; commands/_reconcile.py::_pending_turn_edit only re-derives
      [word_counts] today, so it gains a mkdir branch for the
      operation=="set-chapters" COMPLETE.

    - Observation (S6): cyclopts "JSON List Parsing" is a documented feature, not
      a memory claim. Evidence: the cyclopts Read-the-Docs user_classes page
      ("User Classes" → "JSON List Parsing": "Cyclopts also supports JSON parsing
      for lists of dataclasses. This allows you to pass multiple structured
      objects via JSON") confirmed via web search; the feature is present across
      the 4.x line and pinned for the locked 4.18.0 at
      cyclopts.readthedocs.io/en/v4.18.0/user_classes.html. The in-process probe
      against locked 4.18.0 (S1) is the canonical pin; this doc is the corroborating
      citation, replacing the round-1 memory reference (round-1 review finding 2).
      Impact: the JSON-list mechanism is both documented and in-process-verified;
      no undecided fork.

    - Observation (S4): cuprum (locked 0.1.0) is used by the test suite only to
      drive the installed console-script as a subprocess
      (sh.make/Program/ExecutionContext/single_program_catalogue), never inside a
      command body. Design §4 records "cuprum is required only where a command
      shells out (none do in v1)".
      Evidence: `grep cuprum novel_ralph_skill/` is empty; tests/test_recount_e2e.py
      imports cuprum.sh.
      Impact: set-chapters shells out to nothing — pure pathlib + tomlkit — so it
      needs no cuprum. The only cuprum use this plan adds is in the e2e test
      (Work item 6), pinned to the same API the existing recount e2e uses.

    - Observation (S7, Work item 3/3a): populating `[chapters]` WITHOUT seeding
      `[word_counts].by_chapter` makes `novel-state check` exit 4 the instant
      `set-chapters` returns — not on the bijection (the dirs are created) but on
      the §5.4 `word-counts-cover-drafts` coverage invariant (roadmap task 2.3.6,
      added after the original design), because the populated manifest out-keys
      the empty `by_chapter` table.
      Evidence: an in-process probe over a fresh `chapter-planning` tree —
      `set_chapters(...)` then `check_disk_evidence(...)` returned
      `['word-counts-cover-drafts']` with `by_chapter == {}`.
      Impact: the success criterion ("check exits 0 after set-chapters") is unmet
      unless the body also seeds `by_chapter`. The body now writes a zero entry
      per planned chapter (D13); `current` stays 0 = sum, so §5.2 invariant 3
      holds and the acceptance's "recount returns a key per chapter (values all
      0)" is satisfied by construction. The plan did not foresee this interaction
      between the manifest write and the post-2.3.6 coverage invariant.

    - Observation (S8, Work item 7): Work item 4 placed the `ChapterPlanEntry`
      import at the BOTTOM of `novel_state.py` (so the name is a runtime global for
      Cyclopts annotation resolution) to dodge the
      `_set_chapters` -> `_state_mutators` -> `novel_state` cycle. That works only
      when `novel_state` is the entry import; when `_set_chapters` is imported
      *first* (as the property suite does via
      `from novel_ralph_skill.commands._set_chapters import ...`), the chain
      re-enters `_set_chapters` while it is partially initialised and raises
      `ImportError: cannot import name 'ChapterPlanEntry'`.
      Evidence: `pytest tests/test_set_chapters_properties.py` failed at collection
      with exactly that ImportError.
      Impact: the bottom-import was fragile. `ChapterPlanEntry` moved to a
      dependency-free leaf module `commands/_chapter_plan_entry.py` that imports
      nothing from `commands`/`state`; both `novel_state.py` (top-level runtime
      import) and `_set_chapters.py` (top-level, re-exported) import it from there,
      so no import order can re-enter a partially-initialised module. The
      `# noqa: E402` is gone; only a `# noqa: TC001` (a permanent, runtime-required
      suppression) remains.
```

## Decision log

```plaintext
    - Decision (D1): name the subcommand `set-chapters` (kebab), body
      `set_chapters`.
      Rationale: the roadmap offers `set-chapters`/`plan-chapters`; `set-cursor`
      is the established sibling verb, so `set-chapters` reads consistently. The
      ADR records the chosen name.
      Date/Author: 2026-06-25, planner.

    - Decision (D2): set-chapters creates the on-disk chapter-NN/ directories so
      the §5.2 manifest-disk bijection holds immediately after the command.
      Rationale: the success criterion requires `check` to "operate correctly on
      the real chapter directories"; the bijection
      (state/disk_evidence.py::_check_manifest_disk_bijection) counts chapter-NN/
      *directories* (entry.is_dir()), independent of draft.md, so creating empty
      directories makes check exit 0. A manifest with no directories would make
      check exit 4 on manifest-disk-bijection, failing the success clause.
      Date/Author: 2026-06-25, planner. (Escalation trigger if review disagrees —
      see Tolerances.)

    - Decision (D3): refuse with exit 3 when [chapters] is already non-empty.
      Rationale: set-chapters is a one-shot populate at chapter-planning
      completion (design §5.1 "written … when chapter planning completes"), not a
      manifest editor. Overwriting a live manifest could orphan chapter
      directories and drafts. Re-planning is a distinct, later concern. This
      refusal keys off "manifest non-empty" (not "manifest non-empty AND
      bijective"); torn-turn completion is NOT delegated to a set-chapters re-run
      but to reconcile (D8), so D3 stays the simplest possible one-shot guard and
      the round-1 reviewer's "D3 blocks the only recovery" contradiction is
      resolved by giving reconcile the recovery job instead of weakening D3.
      Date/Author: 2026-06-25, planner.

    - Decision (D4): manifest coherence (contiguous from 1, unique numbers,
      ascending order) is a *new pure predicate* the body calls before the
      existing §5.2 validate-before-persist pass, not an addition to
      validate_state.
      Rationale: validate_state owns the §5.2 *self-consistency* invariants the
      check command runs every turn; manifest contiguity/uniqueness is a
      write-time precondition the §5.2 set does not currently own (confirmed:
      validate.py has no such predicate). Adding it to validate_state would
      change check's behaviour for every existing tree and is out of scope.
      Keeping it a write-time predicate mirrors advance-phase's empty-manifest
      precondition (a §4.1 precondition the §5.2 validator does not own).
      Date/Author: 2026-06-25, planner.

    - Decision (D5): reject duplicate slugs as well as duplicate numbers.
      Rationale: a unique slug per chapter keeps the manifest self-describing and
      matches the per-chapter loop's expectation; cheap to check alongside number
      uniqueness. Directory names key off number so this is a quality guard, not
      a correctness one — recorded so the test pins it.
      Date/Author: 2026-06-25, planner.

    - Decision (D6): the exit-3 channel covers *semantic* refusals (non-contiguous,
      duplicate number/slug, non-empty prior manifest); the exit-2 channel covers
      *shape* faults (bad JSON, missing/ill-typed field) and is owned by cyclopts.
      Rationale: matches the runner's existing CycloptsError→2, StateInputError→3
      split and design §3.2 (usage error vs state/input error). Both are pinned by
      tests so the boundary cannot silently drift.
      Date/Author: 2026-06-25, planner.

    - Decision (D7): ingest the plan as `--chapters '<json-array>'` (cyclopts JSON
      list parsing), one keyword parameter typed `list[ChapterPlanEntry]`.
      Rationale: verified working against locked cyclopts 4.18.0 (S1); no bespoke
      parser, no new dependency; the agent emits one JSON argument. The element
      dataclass must not be union'd with str (S1 constraint).
      Date/Author: 2026-06-25, planner.

    - Decision (D8, rewritten round 2): a torn "set-chapters" turn is recovered by
      a SCOPED PRECEDENCE CHANGE in derive_reconciliation that classifies the
      set-chapters pending-turn ahead of the manifest-disk-bijection REFUSE when
      (and only when) the bijection break is fully explained by the pending-turn's
      missing chapter directories; reconcile then COMPLETEs it by creating those
      directories. NOT by re-running set-chapters (D3 refuses) and NOT by manual
      mkdir.
      Rationale: round-2 review B1 proved the round-1 mechanism (edit only
      _RECOMPUTABLE_BASENAMES + _classify_pending_turn) is UNREACHABLE: the
      refuse-class is evaluated first (reconcile.py lines 258-264) and
      MANIFEST_DISK_BIJECTION is in it, so a partial-directory torn turn REFUSEs
      before the pending-turn branch runs (S5 corrected). The honest fix is the
      precedence change. It is scoped, not a blanket inversion: the new branch
      fires only for an operation=="set-chapters" pending-turn whose declared-
      but-missing chapter dirs EXACTLY account for the bijection break (manifest ⊇
      on_disk; manifest \ on_disk == missing declared chapter numbers; no other
      refuse-class invariant fired). Every other bijection break — a stray draft,
      an orphan dir, a manifest gap the pending turn does not explain, or any
      done-flag/compiled contradiction — still REFUSEs exactly as today. This
      preserves the §5.4 invariant that disk contradictions reconcile cannot
      resolve are refused, while letting reconcile finish a turn whose ONLY
      outstanding work is materialising deterministic, manifest-derived empty
      directories. Why an empty chapter-NN/ directory counts as recomputable: it
      carries no agent judgement and is wholly derivable from the PERSISTED
      manifest (D10 guarantees the manifest is on disk before any directory is
      created), exactly like log.md. This is a genuine amendment to the §5.4
      recomputable-artefact set and the reconcile precedence, recorded as a
      reasoned decision in ADR 008 and design §5.4 (round-2 B3), NOT slipped in as
      a mechanical tweak.
      Alternatives rejected: (b) weakening D3 to "non-empty AND bijective" so a
      re-run completes the dirs re-introduces the overwrite/orphan hazard D3
      exists to prevent (a re-run with a DIFFERENT plan) and needs an extra
      identical-plan guard; (c) documenting a manual mkdir leaves a manual step in
      the loop and is unsanctioned (ADR 001). Option (a) — the scoped precedence
      change — is design-honest and keeps recovery a single sanctioned command.
      Mechanism: set-chapters declares each working/manuscript/chapter-NN/
      directory in its [pending_turn] paths and persists the populated manifest
      with that record (D10). Work item 3a adds the guarded branch to
      derive_reconciliation and extends the COMPLETE dispatch
      (commands/_reconcile.py) to mkdir each missing chapter dir for an
      operation=="set-chapters" record, deriving the numbers from
      reconciliation.missing_paths (not a re-read manifest).
      Date/Author: 2026-06-25, planner.

    - Decision (D9): set-chapters performs the multi-file write (manifest +
      directories + receipt under a [pending_turn] bracket); a manifest-only write
      (round-2 advisory A1) is rejected.
      Rationale: A1 proposes writing only [chapters] (single atomic file, no
      bracket, no Work item 3a) and letting a later loop step or reconcile's
      draft-without-manifest-entry path materialise directories. Three facts make
      this worse, not simpler. (1) The roadmap MANDATES the bracket: task 2.2.3
      (lines 715-719) requires "writes [chapters] atomically … with the log
      receipt and [pending_turn] discipline" — manifest-only contradicts the
      task. (2) The design makes the bijection a HARD invariant that must hold
      immediately: §5.1 (lines 398-404) "novel-state check asserts a bijection …
      so the manifest order and the directory index are guaranteed to agree before
      any compile runs", and §5.2 (lines 514-519). A manifest-only write leaves
      manifest {1..n} vs on-disk {} — manifest-disk-bijection fires and check
      exits 4 the instant the command returns, FAILING the success criterion
      ("check … then operate correctly on the real chapter directories"). (3)
      reconcile's draft-without-manifest-entry path is a REFUSE, not a repair (it
      is the bijection invariant itself), so it would NOT materialise directories
      — it would stick exit 4. Deferring directory creation to "the per-chapter
      drafting step" is not in any current task and would leave the tree
      non-bijective for the whole gap. The reviewer's own A1 concedes: "If the
      bijection-immediately requirement is firm, persisting the manifest at the
      intent write is the minimum honest design." It is firm (§5.1/§5.2), so the
      multi-file path with D10 ordering is taken.
      Date/Author: 2026-06-25, planner.

    - Decision (D10, round-2 B2): the populated [chapters] manifest is persisted
      AT the intent write — written into the document and atomically persisted
      TOGETHER with the [pending_turn] record, BEFORE any chapter directory is
      created — NOT at the final clear-write the way reconcile persists its
      recount.
      Rationale: round-2 B2 proved that mirroring reconcile's ordering (intent
      write of the ORIGINAL state → in-memory edit → … → clear+write of the edited
      state) is fatal here. reconcile's payload (the recount) is RECOMPUTABLE from
      disk, so persisting it last is safe — a crash loses nothing the next
      reconcile cannot re-derive. set-chapters's payload is the agent's
      JUDGEMENT (slug/title/target_words), which is NOT on disk anywhere else. If
      it persisted last, a crash in the directory-creation window would leave the
      ORIGINAL empty manifest on disk with the agent's plan GONE, and reconcile
      mkdir-ing against an empty manifest would only WORSEN the bijection. So the
      manifest must be on disk before the first crash-able artefact. The single
      seam supports this directly: open_pending_turn mutates the document in place
      and does not touch [chapters] (verified, state/document.py lines 179-205),
      so one write_document_atomically carries both the [chapters] edit and the
      intent record. Order: (1) load; (2) read prior, refuse if non-empty (D3) or
      incoherent (Work item 2); (3) edit document["chapters"] = the ordered array;
      (4) open_pending_turn naming state.toml + each chapter dir; (5) validate the
      proposed document; (6) ONE atomic write (manifest + intent land together);
      (7) mkdir each chapter dir; (8) append log.md receipt; (9) clear_pending_turn
      + final atomic write. Steps 1-5 touch only memory, so a crash there leaves
      the prior file byte-for-byte intact (the refusal guarantee). From step 6
      onward the manifest is persisted, so every torn state is COMPLETE-able by
      D8's recovery.
      Date/Author: 2026-06-25, planner.

    - Decision (D11, Work item 0/1): export the chapter-directory-name helper by
      RE-EXPORTING `_disk_paths._chapter_dir_name` as `chapter_dir_name` from
      `novel_ralph_skill/state/__init__.py`, rather than renaming the private
      symbol and updating its three intra-package importers
      (`compile_model.py`, `done_predicate.py`, `disk_evidence.py`).
      Rationale: the plan's Work item 0 prefers the re-export to keep the diff
      small; the three existing importers keep their private import unchanged, so
      only `__init__.py` grows the package-public name the command module
      (crossing the `state` boundary) reuses. The corpus test helper
      `working_corpus.chapter_dir_name` is a separate test-only definition and is
      left untouched.
      Date/Author: 2026-06-25, implementer.

    - Decision (D12, Work item 3): implement a LOCAL D10 bracket
      (`_write_manifest_turn` in `_set_chapters.py`) rather than generalising
      `_reconcile.py::_run_reconcile_bracket`.
      Rationale: the plan offered either generalising the shared bracket or a
      local one. The orderings are fundamentally different — reconcile's fixed
      order is intent-of-PRIOR-state → edit → receipt → clear (its recomputable
      recount persists last), while set-chapters edits `[chapters]` into the
      document FIRST and lands it together with the intent record in the single
      first write (D10). Generalising `_run_reconcile_bracket` to accept a
      pre-write edit would complicate the reconcile seam for one caller with the
      opposite ordering; a small local bracket keeps each mutator's ordering
      legible at its own call site (AGENTS.md "clear file boundaries"). The
      shared LOAD/REFUSE helpers (`_load_document_or_state_error`,
      `_state_view_or_state_error`, `_refuse_if_incoherent`) are still reused, so
      no mutator-contract logic is duplicated. The operation tag
      `SET_CHAPTERS_OPERATION` lives in `state/schema.py` so the writer and Work
      item 3a's reconcile reader key on one literal.
      Date/Author: 2026-06-25, implementer.

    - Decision (D13, Work item 3, prompted by Work item 3a): `set-chapters` seeds
      `[word_counts].by_chapter` with a zero entry per planned chapter, alongside
      the manifest write.
      Rationale: the §5.4 `word-counts-cover-drafts` coverage invariant (roadmap
      task 2.3.6, post-dating the original design) compares the manifest-keyed
      recount key set against the `by_chapter` table key set. A populated manifest
      over an empty `by_chapter` therefore fires that invariant and `check` exits
      4 the instant `set-chapters` returns (Surprise S7), defeating the success
      criterion. Seeding a `0` per chapter is the honest count for a planned,
      undrafted chapter, keeps `current` at 0 = sum(by_chapter) so §5.2 invariant
      3 holds, and matches the acceptance's "recount returns a key per chapter
      (values all 0)". The seed is written into the same in-memory document before
      the single intent write, so the D10 ordering and the refusal guarantee are
      unaffected. Considered and rejected: deferring coverage to a later `recount`
      — the success criterion requires `check` to exit 0 *immediately* after
      `set-chapters`, so a deferred recount would leave `check` at exit 4 across
      the gap.
      Date/Author: 2026-06-25, implementer.
```

## Outcomes & retrospective

All nine work items (1, 2, 3, 3a, 4-8) landed as atomic, individually-gated
commits. Measured against the Purpose: a planned chapter reaches `[chapters]`
**only** through `novel-state set-chapters` (never a hand edit; the command
creates the `chapter-NN/` directories and seeds `by_chapter` so `check` exits 0
immediately); an incoherent plan (non-contiguous, duplicate number or slug,
non-positive target, empty) is refused with exit 3 and writes nothing, a
non-empty prior manifest is refused with exit 3 (D3), and a malformed `--chapters`
argument exits 2; and `check`/`recount`/`novel-compile` then operate on the real
chapter directories. The full behaviour is pinned at the unit, property,
behavioural (pytest-bdd), and end-to-end (entry-point + installed-binary) layers.

Two interactions the plan did not foresee surfaced during implementation and were
resolved in-scope:

- **S7/D13:** `set-chapters` had to seed `[word_counts].by_chapter` with a zero
  per chapter, or the post-2.3.6 `word-counts-cover-drafts` invariant fires and
  `check` exits 4 — defeating the success criterion. The plan reasoned about the
  §5.2 bijection but not the §5.4 coverage invariant.
- **S8:** Work item 4's bottom-of-module `ChapterPlanEntry` import in
  `novel_state.py` was circular when `_set_chapters` is imported first (caught by
  the Work item 7 property suite). Resolved by a dependency-free leaf module
  `commands/_chapter_plan_entry.py`, a cleaner end-state than the original
  bottom-import-with-`E402`.

The only unresolved item is the CodeRabbit review service stalling on the Work
item 7 diff (three attempts, "summarizing" phase, never reaching findings — a
transient service-side hang, not a rate limit); the deterministic gates were green
and the work item proceeded per the workflow's rate-limit policy. Every other work
item was CodeRabbit-reviewed and its actionable feedback addressed.

## Open issues

- The CodeRabbit review service stalled in its "summarizing" phase for the Work
  item 7 and Work item 8 diffs (several attempts each, with exponential backoff,
  a transient service-side hang, not a 429/rate limit). Work items 1-6 were all
  CodeRabbit-reviewed and their actionable feedback addressed; Work items 7
  (a new Hypothesis property file plus a clean leaf-module refactor) and 8
  (documentation only) are green under `make all`/`make audit` and, for the docs,
  `make markdownlint`/`make nixie`, and are consistent with the surrounding house
  style. A later CodeRabbit pass over the merged branch can re-review them.

## Context and orientation

The repository is a Python package, `novel_ralph_skill`, that ships a
deterministic command spine for a novel-writing "Ralph Loop" harness. State
lives in `working/state.toml`; commands read and mutate it.

Key files (all paths repository-relative, from the worktree root):

- `novel_ralph_skill/commands/novel_state.py` — the `novel-state` Cyclopts app
  and its subcommand registrations (`check`, `init`, `set-cursor`,
  `advance-phase`, `recount`, `reconcile`). `build_app()` registers each
  subcommand. The fixed working directory is `working/` (`working_dir()`,
  `state_path()`). `STATE_INPUT_ERRORS` is the shared "what counts as a state
  fault" tuple.
- `novel_ralph_skill/commands/_state_mutators.py` — shared mutator helpers:
  `_load_document_or_state_error`, `_state_view_or_state_error`,
  `_refuse_if_incoherent`, and the re-exported `_state_path`/`_working_dir`.
  The load-and-refuse contract every mutator reuses.
- `novel_ralph_skill/commands/_recount.py`, `_reconcile.py` — sibling mutator
  bodies. `_reconcile.py` is the **multi-file** precedent: it brackets
  `state.toml` + `log.md` with a manual `[pending_turn]` in the order intent →
  edit → receipt → clear (`_run_reconcile_bracket`, `_append_recovery_entry`).
  `set-chapters` follows this shape.
- `novel_ralph_skill/state/document.py` — the `tomlkit` round-trip seam:
  `load_document`, `document_to_state`, `write_document_atomically`,
  `open_pending_turn`, `clear_pending_turn`. The single home of the
  temp-file-plus-`Path.replace` atomic write.
- `novel_ralph_skill/state/schema.py` — frozen typed `State` and `ChapterEntry`
  (number, slug, title, target_words). The on-disk `[chapters]` shape.
- `novel_ralph_skill/state/parse.py` — `parse_state` builds the typed `State`
  from a decoded mapping; `_chapters` reads the `[[chapters]]` array of inline
  tables.
- `novel_ralph_skill/state/validate.py` — the pure §5.2 `validate_state`. It has
  **no** contiguity/uniqueness predicate today (see D4).
- `novel_ralph_skill/state/disk_evidence.py` — the §5.4 disk checks, including
  `_check_manifest_disk_bijection` (manifest numbers == on-disk chapter-NN/
  directory numbers, contiguous from 1).
- `novel_ralph_skill/state/_disk_paths.py` — `_chapter_dir_name(n)` →
  `chapter-NN`, and `_on_disk_chapter_numbers(working_dir)`.
- `novel_ralph_skill/state/initial.py` — `build_initial_document`: a fresh
  `state.toml` with an **empty** `[[chapters]]` array (the precondition state
  for `set-chapters`).
- `novel_ralph_skill/contract/runner.py` — `run(app, argv, context)`: maps
  `CycloptsError → exit 2`, `StateInputError → exit 3`, a returned
  `CommandOutcome` to its `.code`. `make_contract_app` builds the four-flag app.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode.SUCCESS=0`,
  `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`, `ACTIONABLE_FINDING=4`.
- Tests live under `tests/` (top-level only, per AGENTS.md). The closest
  precedents: `tests/test_recount_unit.py`, `tests/test_state_mutators_unit.py`
  (unit); `tests/features/recount.feature` + `tests/steps/recount_steps.py` +
  `tests/test_recount_bdd.py` (behavioural); `tests/test_recount_e2e.py`
  (entry-point + installed-binary e2e); `tests/working_corpus/` (the tree
  builder `build_working_tree(WorkingTreeSpec, dest)` with `ChapterSpec`);
  `tests/test_command_surface_matrix.py`,
  `tests/test_command_names_registry.py` (the subcommand registry).

Terms of art, defined:

- **Mutator** — a command that writes state. **Checker** — a read-only command.
  Segregated so the harness can call checkers freely (design §3.3).
- **`[pending_turn]` bracket** — an intent record written to `state.toml` before
  a multi-file turn touches any other file and cleared after every artefact is
  verified, so a torn turn is a declared, recoverable state (design §3.4).
- **Bijection** (§5.2) — the manifest numbers and the on-disk `chapter-NN/`
  directory numbers are the same set, contiguous from 1.
- **Envelope** — the shared JSON output
  `{command, schema_version, ok, working_dir, result, messages}` (ADR 003).

## Plan of work

The work is staged red-green-refactor. Each work item is independently
committable and, before commit, must pass the full per-work-item gate sequence:
`make all` **followed by** `make audit`. `make all` chains only
`build check-fmt lint typecheck test` (verified against the Makefile —
`all: build check-fmt lint typecheck test`); it does **not** run `audit`.
AGENTS.md "Quality gates" lists auditing (`make audit`, which runs `pip-audit`)
as a *distinct* gate that must pass before commit, so it is run as a separate
step. The 100%-docstring-coverage (`interrogate`) and Pylint checks AGENTS.md
also names are part of `make lint`, hence already covered by `make all`
(Makefile `lint-python` runs `ruff check`, `interrogate`, then Pylint) — they
need no separate invocation. Markdown-only items additionally run
`make markdownlint` and `make nixie`.

This is a no-new-dependency change (Tolerances: "Dependencies — none"), so
`make audit` is expected to be a green no-op; it is still run every work item
because AGENTS.md requires every gate to pass before each commit, not only on a
dependency change.

### Work item 0 (folded into Work item 1): export the chapter-directory-name helper

Promote the directory-name helper to a package-public name so the command
module (which crosses the `state` package boundary) reuses it rather than
reaching for a private symbol or duplicating the `f"chapter-{n:02d}"` literal
(AGENTS.md "Abstraction / port / helper policy": sweep for an existing helper
first — it exists as `state/_disk_paths.py::_chapter_dir_name`).

- Add `chapter_dir_name` to `novel_ralph_skill/state/__init__.py`'s exports,
  re-exporting `_disk_paths._chapter_dir_name` (or rename the private symbol to
  public and update its three intra-package importers — `compile_model.py`,
  `done_predicate.py`, `disk_evidence.py`). Prefer the re-export to keep the
  diff small; record the choice in the Decision Log when implemented.
- Docs to read: AGENTS.md "Abstraction / port / helper policy".
- Skills: `leta` (find the three `_chapter_dir_name` importers via
  `leta refs`); `arch-crate-design` is Rust-only — not applicable; rely on
  AGENTS.md file-boundary guidance.
- Tests: no new behaviour; covered by the existing `state` import tests and the
  Work item 3 directory-creation tests. If a dedicated assertion is wanted, add
  one line to an existing `tests/test_state_*` checking
  `chapter_dir_name(1) == "chapter-01"`.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 1: input dataclass + module scaffold (red)

Define the CLI input shape and a stub body so the registration and first
failing test exist.

- Add a new module `novel_ralph_skill/commands/_set_chapters.py`. Define the
  cyclopts input dataclass:

```python
@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterPlanEntry:
    """One chapter the agent plans: the CLI input shape for ``set-chapters``."""

    number: int
    slug: str
    title: str
    target_words: int
```

  This is the *input* shape (distinct from `state.schema.ChapterEntry`, the
  on-disk shape — they happen to share fields but serve different layers; do
  not conflate them). It must **not** be union'd with `str` (cyclopts JSON-list
  constraint, S1).

- Add a stub
  `set_chapters(*, chapters: list[ChapterPlanEntry]) -> CommandOutcome` that
  raises `NotImplementedError`, plus a red unit test
  `tests/test_set_chapters_unit.py::test_set_chapters_writes_manifest` that
  drives a populated empty-manifest tree and asserts the written `[chapters]` —
  expected to fail until Work item 3.
- Docs to read: design §4.1, §5.1 (lines 455-461); developers' guide "State
  mutators"; cyclopts "User Classes → JSON List Parsing"
  (cyclopts.readthedocs.io/en/v4.18.0/user_classes.html — the feature is
  web-search-confirmed, S6, and the canonical pin is the in-process probe S1,
  so the URL is corroboration, not the sole evidence).
- Skills: `python-router` → `python-data-shapes` (frozen/slotted/kw-only domain
  shape, the house style); `leta`.
- Tests: `tests/test_set_chapters_unit.py` (new, red). Per AGENTS.md, the new
  behaviour gets a failing test before the implementation.
- Validation: `make all` — the new red test must fail for the right reason
  (`NotImplementedError`), every other suite green — then `make audit`.

### Work item 2: pure manifest-coherence validator

Add the write-time precondition that makes an incoherent plan a refusal (the
core of the task), as a small, pure, total function (D4).

- In `_set_chapters.py` (or a tiny sibling
  `novel_ralph_skill/state/manifest.py` if `_set_chapters.py` would exceed ~250
  lines — decide by line count, record in Decision Log), add a pure predicate:

```python
def manifest_coherence_violations(
    entries: cabc.Sequence[ChapterPlanEntry],
) -> tuple[str, ...]:
    """Return the manifest-coherence rules ``entries`` breaks (empty == coherent)."""
```

  Rules, each a distinct named string so a refusal pins exactly the rule broken
  (mirroring `validate.py`'s one-predicate-per-invariant style):
  `chapters-non-empty` (an empty plan is refused — there is nothing to
  populate), `numbers-unique`, `numbers-contiguous-from-1` (sorted numbers ==
  `range(1, n+1)`), `slugs-unique` (D5), and `target-words-positive`
  (`target_words >= 1`; a non-positive target is meaningless). Order them so
  the verdict is deterministic.

- The body (Work item 3) calls this and, on a non-empty verdict, raises
  `StateInputError` naming the breached rules first (the exit-3 channel; the
  `run` exit-3 arm emits only `messages`, no `result`).
- Docs to read: design §5.2 (the bijection's "contiguous from 1, no gaps"
  wording the manifest must satisfy); roadmap 2.2.3 (contiguity, uniqueness,
  required fields); developers' guide "Validate before persist".
- Skills: `python-router` → `python-errors-and-logging` (narrow exception
  design, `raise … from …`, `Error`-suffixed domain errors); `leta`.
- Tests: extend `tests/test_set_chapters_unit.py` with a table-driven
  `pytest.mark.parametrize` over each breach (gap at 1, missing middle number,
  duplicate number, duplicate slug, empty plan, zero/negative target) asserting
  the exact rule name(s) returned. Property coverage lands in Work item 7.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 3: the `set_chapters` body (green)

Implement the body so Work item 1's red test passes. This is the multi-file
mutator, modelled on `_reconcile.py::_run_reconcile_bracket`.

- Behaviour, in the order D10 fixes (manifest persists AT the intent write). The
  ordering DIFFERS from `_run_reconcile_bracket` deliberately (D10): reconcile
  persists its recomputable payload last; `set-chapters` persists its
  non-recomputable manifest first.
  1. `_load_document_or_state_error(state_path())` (exit-3 on
     missing/unparseable).
  2. `_state_view_or_state_error(document)` to prove structural completeness and
     read the prior manifest.
  3. Refuse with exit 3 if `prior.chapters` is non-empty (D3). *(memory only —
     no write yet)*
  4. Call `manifest_coherence_violations(chapters)`; on any breach raise
     `StateInputError` (exit 3, no write). *(memory only)*
  5. Build a fresh `[[chapters]]` array of inline tables (number, slug, title,
     target_words) in ascending number order and assign `document["chapters"]`
     **in memory**. Run `_state_view_or_state_error` + `_refuse_if_incoherent`
     (defence in depth against the §5.2 set) on the proposed document. *(memory
     only)*
  6. `open_pending_turn(document, operation="set-chapters", paths=[...])` naming
     `working/state.toml` plus each `working/manuscript/chapter-NN/` directory
     (the *paths the turn will write*, in the `working/…` form
     `_missing_declared_paths` expects — verified against
     `reconcile.py::_missing_declared_paths`, which strips the `working/` prefix).
     `open_pending_turn` only appends the `[pending_turn]` table, so the in-memory
     `[chapters]` edit from step 5 is untouched.
  7. **ONE** `write_document_atomically(document, state_path())` — the populated
     manifest AND the `[pending_turn]` intent land together (D10/B2). From here
     the manifest is on disk and the torn turn is recoverable.
  8. Create each `working/manuscript/chapter-NN/` directory (`chapter_dir_name`,
     `mkdir(parents=True, exist_ok=True)` — idempotent).
  9. Append a `log.md` receipt (reuse `_append_recovery_entry` shape, or a local
     `set-chapters:` receipt) **before** the clear.
  10. `clear_pending_turn(document)` + final atomic write (clears last).
  - Return `CommandOutcome(code=SUCCESS, result={"chapters": […the written
    entries…]}, messages=[…])` — write-shaped success vocabulary.
- Do **not** reuse `_run_reconcile_bracket` unchanged: its fixed order is
  intent-of-PRIOR-state → edit → receipt → clear, which would persist the empty
  manifest first (the B2 bug). Either (a) generalise the bracket helper to
  accept a pre-write document edit (so the `[chapters]` edit is applied to the
  SAME document before the intent write) and factor a shared
  `commands/_pending_turn_bracket.py` (sweep first per AGENTS.md), or (b) a
  local `set-chapters` bracket implementing steps 5-10 directly. Record the
  choice in the Decision Log. Keep `_set_chapters.py` under 400 lines.
- Docs to read: design §3.4 (atomic, `[pending_turn]`, "log entry appended
  last"), §4.1, §5.1; developers' guide "Checker/mutator segregation"; Decision
  Log D10 (why the ordering differs from `reconcile`); `state/document.py`
  `open_pending_turn`/`write_document_atomically` (the seam that lets one write
  carry both edits).
- Skills: `python-router` → `python-errors-and-logging` (exit-channel mapping)
  and `python-iterators-and-generators` (building the ordered array without a
  nested loop); `hexagonal-architecture` (keep the pure validator separate from
  the I/O body); `leta`.
- Tests: Work item 1's unit test now passes; add unit tests for (a) the
  non-empty-prior refusal (exit 3, file unchanged), (b) directories created, (c)
  `state.toml` comments preserved (round-trip), (d) a `[pending_turn]`-clean
  tree on success, (e) a refusal leaves the prior file byte-for-byte intact,
  and **(f) the D10 ordering guarantee**: a test that drives the body but
  injects a failure in the directory-creation step (e.g. monkeypatch `mkdir` to
  raise after the first dir) and asserts the on-disk `state.toml` already
  carries the **populated** `[chapters]` plus the `operation="set-chapters"`
  `[pending_turn]` — proving the manifest persists before the directories (B2).
  This is the unit pin for D10.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 3a: scoped precedence change so reconcile completes a torn `set-chapters` turn

Give the harness a sanctioned command to finish a torn `set-chapters` turn. The
round-1 mechanism (edit `_RECOMPUTABLE_BASENAMES` only) is **unreachable** in
the realistic crash because `derive_reconciliation` evaluates the refuse-class
(containing `manifest-disk-bijection`) BEFORE the pending-turn branch (S5
corrected; round-2 B1). This work item makes the **scoped precedence change**
recorded in D8 and ADR 008. After it, a crash in the directory-creation window
— including the **partial-directory** case (manifest `{1,2}`, on-disk `{1}`) —
is recovered by `novel-state check` (surfaces it) then `novel-state reconcile`
(completes it), with the manifest already on disk (D10) and only empty,
manifest-derivable directories to materialise (design §3.4, §5.4).

- In `novel_ralph_skill/state/reconcile.py::derive_reconciliation`, add a
  **guarded branch ahead of the refuse arm**. Its predicate
  (`_set_chapters_turn_explains_bijection(state, working_dir, fired)` or
  similar, a pure helper) returns true only when ALL hold:
  - `state.pending_turn is not None` and `state.pending_turn.operation ==
    "set-chapters"` (a named constant, not a string literal repeated — sweep for
    an existing operation constant first per AGENTS.md);
  - the fired refuse-class set is **exactly** `{manifest-disk-bijection}` — no
    `done-flag-without-draft`, `compiled-matches-drafts`, or
    `cursor-plan-present` (those still REFUSE; the branch never masks a second
    contradiction);
  - the bijection break is **fully explained** by the pending-turn's missing
    chapter dirs: with `manifest = {c.number for c in state.chapters}` and
    `on_disk = _on_disk_chapter_numbers(working_dir)`, `on_disk ⊆ manifest`, the
    manifest is contiguous from 1, and `manifest \ on_disk` equals exactly the
    chapter numbers parsed from the pending-turn's declared-but-missing
    `chapter-NN/` paths (`_missing_declared_paths`). (If on-disk holds a number
    the manifest does not, or a missing dir is not declared by the pending turn,
    the break is NOT explained → fall through to REFUSE.)
  When the predicate holds, return a `COMPLETE_PENDING_TURN` reconciliation
  carrying `operation="set-chapters"` and `missing_paths` = the missing
  declared chapter-dir paths. Otherwise the existing refuse arm runs unchanged.
  The `Reconciliation` shape and `derive_reconciliation` signature are
  unchanged (they already carry `operation`/`missing_paths`). Keep
  `reconcile.py` under the 400-line cap. As implemented, the
  reconciliation-reasoning predicate (`_set_chapters_turn_explains_bijection`,
  which inspects `pending_turn`/`fired`) stays in `reconcile.py`; only the pure
  path parsers it calls (`_chapter_number_of`, `_declared_chapter_numbers`) moved
  to `state/_disk_paths.py` beside the sibling chapter-number parsers, which kept
  `reconcile.py` under the cap without putting reconcile logic in the path module.
- This change is **scoped, not a blanket precedence inversion**: it fires only
  for an explained `set-chapters` bijection break. The module docstring's
  precedence narrative (lines 13-44) and the `_REFUSE_CLASS` comment must be
  updated to describe the new branch and *why* it is design-honest (cite ADR
  008, §5.4).
- In `novel_ralph_skill/commands/_reconcile.py`, extend the
  `COMPLETE_PENDING_TURN` dispatch so that for a record whose
  `operation == "set-chapters"`, the COMPLETE path creates each missing
  `chapter-NN/` directory (`mkdir(parents=True, exist_ok=True)` — idempotent)
  **before** the bracket's clear. Derive the numbers from
  `reconciliation.missing_paths` (the declared-but-missing chapter-dir paths),
  not a re-read manifest. Branch on `operation` so a torn `reconcile` turn (the
  existing `_pending_turn_edit` `[word_counts]` case) is unaffected. Append a
  `complete-pending-turn` receipt as today. Confirm no-deletion: this path only
  `mkdir`s.
- Docs to read: design §3.4 (the `[pending_turn]` recovery model and "completed
  when every missing declared artefact is recomputable"); design §5.4 (the
  reconcile action table, COMPLETE vs ROLLBACK, the recomputable-artefact set
  this work item amends); the `_reconcile.py` and `reconcile.py` module
  docstrings (the precedence narrative); ADR 008 (the reasoned precedence
  decision — Work item 8 writes it; this work item implements it).
- Skills: `python-router` → `python-errors-and-logging` (keep the recovery edit
  total and narrow); `hexagonal-architecture` (keep the pure predicate in
  `state/reconcile.py` separate from the I/O mkdir in `commands/_reconcile.py`);
  `leta` (find `derive_reconciliation`, `_REFUSE_CLASS`,
  `_classify_pending_turn`, `_pending_turn_edit`, `_on_disk_chapter_numbers`
  and their callers/tests).
- Tests: extend the reconcile suites. Add unit tests driving deliberately *torn*
  `set-chapters` trees (populated `[chapters]`, populated
  `operation="set-chapters"` `[pending_turn]` naming the chapter dirs):
  - **the partial-directory case (round-2 A2): manifest `{1,2,3}`, on-disk
    `{1}`** — assert `derive_reconciliation` returns `COMPLETE_PENDING_TURN`
    (NOT REFUSE), `reconcile()` creates the missing `chapter-02/`/`chapter-03/`,
    clears the record, a follow-up `check` exits 0, and the
    `complete-pending-turn` receipt is appended. This case is the one that fires
    the bijection REFUSE under the old precedence, so it is the decisive pin for
    B1;
  - the all-dirs-missing case (manifest `{1,2}`, on-disk `{}`) — same
    assertions;
  - **negative — unexplained breaks still REFUSE**: (i) an orphan on-disk dir
    the
    manifest does not name (on-disk `{1,2,3}`, manifest `{1,2}`) with a
    `set-chapters` pending turn → REFUSE; (ii) a `set-chapters` pending turn plus
    a second refuse-class violation (e.g. a `done.flag` without a draft) → REFUSE;
    (iii) a missing dir NOT declared by the pending turn → REFUSE;
  - regression: a torn `reconcile` turn (the pre-existing `[word_counts]` case)
    is unaffected.
  Mirror `tests/test_reconcile.py` and `tests/test_reconcile_derivation.py`
  (the actual reconcile unit/derivation suites; there is no
  `tests/test_reconcile_unit.py`). These tests pin D8/B1 ("pick one and pin it
  with a test").
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 4: register `set-chapters` in the `novel-state` app

Wire the subcommand and keep the command-surface registry honest.

- In `novel_state.py::build_app`, add:

```python
@app.command(name="set-chapters")
def set_chapters(*, chapters: list[ChapterPlanEntry]) -> CommandOutcome:
    """Populate [chapters] from the agent's plan; refuse an incoherent plan with exit 3."""
    from novel_ralph_skill.commands import _set_chapters
    return _set_chapters.set_chapters(chapters=chapters)
```

  Import inside the builder (the established pattern for `recount`/`reconcile`,
  avoiding a circular import). Confirm cyclopts derives the `--chapters`
  keyword and JSON-list parsing from the `list[ChapterPlanEntry]` annotation
  (S1).

- Update the docstrings in `novel_state.py` (`build_app`, the module header)
  that enumerate the subcommands.
- Docs to read: ADR 007 (the single `novel` multiplexer surface); developers'
  guide command-surface section.
- Skills: `leta` (find every place the subcommand list is asserted —
  `tests/test_command_surface_matrix.py`,
  `tests/test_command_names_registry.py`, `tests/test_cyclopts_contract.py`).
- Tests: update the command-surface matrix / names-registry tests to include
  `set-chapters`; add an in-process invocation test that
  `novel-state set-chapters --chapters '[...]'` resolves and exits 0 against an
  init'd tree.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 5: behavioural (pytest-bdd) scenarios

Prove the user-visible workflow end-to-end at the behavioural layer (AGENTS.md:
pytest-bdd for behavioural tests; cover happy and unhappy paths).

- Add `tests/features/set_chapters.feature` with scenarios:
  - a plan reaches `[chapters]` only through the command, the chapter-NN/
    directories are created, and a follow-up `check` exits 0 (the bijection now
    holds);
  - a non-contiguous plan is refused with exit 3 and `state.toml` is unchanged;
  - a duplicate-number plan is refused with exit 3;
  - re-running against a non-empty manifest is refused with exit 3 (D3).
  - **torn-turn recovery (D8/B1, partial-directory case):** given a tree with a
    populated `[chapters]` of three chapters, a populated
    `operation="set-chapters"` `[pending_turn]` naming all three dirs, and only
    `chapter-01/` on disk (the PARTIAL case that fires the bijection REFUSE under
    the old precedence — round-2 A2), `check` reports the torn turn and a
    subsequent `reconcile` creates the missing `chapter-02/`/`chapter-03/` and
    clears the record, after which `check` exits 0. This is the behavioural proof
    of the round-2 B1 resolution; it MUST use the partial case, not the
    all-dirs-missing case, so it genuinely exercises the precedence change.
- Add `tests/steps/set_chapters_steps.py` and
  `tests/test_set_chapters_bdd.py` (the `scenarios(...)` binder + star-import),
  mirroring the `recount`/`reconcile` wiring.
- Docs to read: roadmap 2.2.3 Success clause; AGENTS.md "Python verification and
  testing"; `tests/features/recount.feature` and `reconcile.feature` as the
  templates.
- Skills: `python-router` → `python-testing` (pytest-bdd structure, fixtures);
  `leta`.
- Tests: the feature + steps above.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 6: end-to-end proofs (entry-point + installed binary)

Prove the externally observable command-line behaviour, including against a
real built-and-installed console-script (AGENTS.md: e2e where command-line
behaviour changes; ADR 006: installed e2e is POSIX-only).

- Add `tests/test_set_chapters_e2e.py`:
  - a fast entry-point proof driving `stub.novel_state()` with
    `sys.argv = ["novel-state", "set-chapters", "--chapters", "<json>"]` against
    an init'd tree; assert exit 0 and the written-chapters envelope.
  - the installed-binary proof (POSIX-only, `@pytest.mark.slow`,
    `@pytest.mark.timeout(180)`): build/install via the `installed_novel_state`
    fixture, then drive it with cuprum
    (`sh.make(prog, catalogue=…)("set-chapters", "--chapters", "<json>")
    .run_sync(context=ExecutionContext(cwd=run_dir), capture=True)`), asserting
    exit 0 and `ok: true`. cuprum API pinned to the same symbols
    `test_recount_e2e.py` uses (`cuprum.sh`, `cuprum.program.Program`,
    `cuprum.sh.ExecutionContext`, the `single_program_catalogue` fixture →
    `ProgramCatalogue(projects=[ProjectSettings(...)])`), verified against the
    locked cuprum 0.1.0 source (`cuprum/sh.py::make`,
    `cuprum/catalogue.py::ProgramCatalogue`).
  - two installed exit-2 proofs, pinning *both* shape-fault routes the plan
    asserts go to exit 2 (round-1 review finding 2 / condition 3): (i) malformed
    JSON `--chapters '[{not json'`, and (ii) a **missing required field**
    `--chapters '[{"number":1,"slug":"a"}]'` (no `title`/`target_words`). Each
    exits 2 with `ok: false` and no traceback (S2 — both raise cyclopts
    CoercionError → usage error; verified in-process, Artifacts). An installed
    exit-3 proof: a non-contiguous plan exits 3 with `ok: false`.
- Docs to read: ADR 006 (POSIX-only e2e); `tests/test_recount_e2e.py` and
  `tests/installed_binary_fixtures.py` (the fixture and catalogue shape); cuprum
  `docs/users-guide.md` (catalogue allowlisting, `ExecutionContext`).
- Skills: `python-router` → `python-testing`; `leta`.
- Tests: `tests/test_set_chapters_e2e.py` (new).
- Validation: `make all` (the slow installed cases run under the default
  suite; if they are gated, run them explicitly once and record the
  transcript), then `make audit`.

### Work item 7: property test for the coherence validator

Add an invariant-style adversary over the pure validator (AGENTS.md: property
tests when a change introduces an invariant over a range of inputs).

- Run `python-verification` to confirm the adversary. The validator is a pure
  `Sequence[ChapterPlanEntry] -> tuple[str, ...]` total function over an input
  range, so **Hypothesis** is the right tool (generate plans; assert: a plan
  whose numbers are exactly `1..n` with unique slugs and positive targets
  yields an empty verdict; any gap/duplicate yields the matching rule).
  CrossHair is a reasonable second adversary for the contiguity arithmetic if
  Hypothesis coverage feels thin — decide during implementation and record it.
- Add `tests/test_set_chapters_properties.py` mirroring
  `tests/test_validate_state_property.py`.
- Docs to read: AGENTS.md "Python verification and testing".
- Skills: `python-router` → `python-verification` → `hypothesis` (strategy
  design, the filtering trap); `leta`.
- Tests: the property module above.
- Validation: `make all`, then `make audit` (see Concrete steps).

### Work item 8: ADR 008 + design, guides, SKILL.md bridge (docs)

Record the decision and bridge the command into the agent workflow (roadmap
2.2.3: "Record the command's input shape and behaviour as an ADR, and bridge it
in SKILL.md Phase 7"). This is the markdown work item.

- Add `docs/adr-008-chapter-manifest-mutator.md` (next free number; ADRs 001-007
  exist): record the `set-chapters` name (D1), the `--chapters '<json-array>'`
  input shape and cyclopts JSON-list mechanism (D7), the exit-2/exit-3 split
  (D6), directory creation (D2), the non-empty-prior refusal (D3), the
  pure-coherence-predicate placement (D4), the **manifest-only alternative and
  why it is rejected** (D9 — the roadmap mandate plus the §5.1/§5.2 firm
  bijection requirement), the **write-ordering decision** (D10 — the manifest
  persists AT the intent write, before any directory, because the manifest is
  the agent's non-recomputable judgement, unlike reconcile's recomputable
  recount payload), and the **torn-turn recovery contract and its precedence
  change** (D8): a torn `set-chapters` turn is completed by `reconcile`, which
  now classifies a `set-chapters` `[pending_turn]` ahead of the
  `manifest-disk-bijection` REFUSE **when that break is fully explained by the
  pending-turn's missing chapter directories** (and still REFUSEs an
  unexplained break). Spell out: (a) the precedence narrative (why the
  bijection refuse-class normally dominates, and why the explained
  `set-chapters` case is the one sanctioned exception); (b) why an empty
  `chapter-NN/` directory is recomputable *given the persisted manifest* (D10)
  — it carries no agent judgement, exactly like `log.md`; (c) the scope guard
  (the branch never masks a second contradiction). This is a deliberate
  amendment to the §5.4 recomputable-artefact set and the reconcile precedence,
  not a mechanical tweak. Reference ADR 001 and design §3.4/§4.1/§5.4.
- Update `docs/novel-ralph-harness-design.md`: add `set-chapters` to the §4.1
  subcommand table and to the §3.3 checker/mutator table (Mutator row); note in
  §5.1 that the chapter-manifest command is `set-chapters`, that it creates the
  chapter directories, and that it persists the populated manifest at the
  intent write before any directory (D10); in §5.4 **amend the
  recomputable-artefact enumeration** (currently `state.toml`/`log.md`, line
  617) to add: a torn `set-chapters` turn's missing `chapter-NN/` directories
  are recomputable (empty, derived from the persisted manifest), so `reconcile`
  COMPLETEs such a turn — and **amend the precedence statement** so the
  `manifest-disk-bijection` REFUSE is documented as yielding to an explained
  `set-chapters` pending-turn; reference ADR 008. Run `make nixie` after
  touching the design doc (it carries Mermaid).
- Update `docs/developers-guide.md`: extend the mutator list and the
  multi-file-mutator note to include `set-chapters` alongside `reconcile`
  (state.toml + directories + log.md → `[pending_turn]` bracket), **noting the
  ordering difference** (set-chapters persists its manifest at the intent
  write, reconcile persists its recount last — D10, and why); document that
  reconcile's COMPLETE path now creates a torn `set-chapters` turn's missing
  chapter directories via the explained-bijection precedence branch (Work item
  3a) and explain why an empty chapter directory counts as recomputable given
  the persisted manifest.
- Update `docs/users-guide.md`: document `novel-state set-chapters`, its
  `--chapters` JSON input, the exit-0/2/3 behaviour, and the write-shaped
  `{chapters}` result, in the existing subcommand prose.
- Update `skill/novel-ralph/SKILL.md` Phase 7: instruct the agent to record the
  planned chapters by running `novel-state set-chapters --chapters '<json>'`
  (never by hand-editing `state.toml`), with the JSON shape spelled out and the
  exact single-quoted shell form shown for a multi-chapter array (so a
  ~35-chapter plan quotes cleanly — round-1 review Scenario B), as the phase
  exit step. Note that if the command is interrupted mid-write, the agent
  recovers by running `novel-state reconcile` (which completes the torn turn),
  never by re-running `set-chapters` or editing the tree by hand (D8).
- Update `docs/contents.md` to index ADR 008.
- Docs to read: documentation-style-guide; AGENTS.md "Documentation
  maintenance" and "Markdown guidance" (80-col prose wrap, 120-col code,
  dashes); en-gb-oxendict.
- Skills: `en-gb-oxendict`; `roadmap-doc`/`tech-design-doc` not required (this
  is
  an ADR edit, follow the existing ADR template).
- Tests: none (docs); but if a test asserts the design subcommand table (e.g. a
  state-layout reference scanner), update its expectation.
- Validation: `make markdownlint` and `make nixie` (Mermaid in the design doc),
  plus `make all` then `make audit` to catch any doc-asserting test and keep
  the full gate sequence green.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-3`.

Per work item:

```bash
# 1. Confirm the branch (must be roadmap-2-2-3, never main).
git branch --show-current

# 2. Make the change for the current work item (see Plan of work).

# 3. Gate the change (sequential — do not parallelise; build caching favours it).
#    make all = build check-fmt lint typecheck test (lint includes interrogate
#    docstring coverage + Pylint). It does NOT include audit.
make all

# 3a. Run the audit gate separately (AGENTS.md lists it as a distinct gate).
#     A green no-op here for this no-new-dependency change, but still required.
make audit

# 3b. For the markdown work item (8), additionally:
make markdownlint
make nixie

# 4. Commit only when every gate is green (see AGENTS.md commit message rules).
git add -A && git commit
```

`make all` chains `build check-fmt lint typecheck test` (Makefile
`all: build check-fmt lint typecheck test`); `make lint` runs `ruff check`,
`interrogate` (100% docstring coverage), and Pylint, so those AGENTS.md gates
are covered by `make all`. `make audit` (`pip-audit`) is a *separate* AGENTS.md
quality gate and is **not** part of `make all`, so it is run as its own step
before every commit. Do **not** run `make test`/`make lint`/`make audit` in
parallel — the environment uses build caching and sequential runs reuse it.

Expected first red transcript (Work item 1), abbreviated:

```plaintext
$ make all
...
FAILED tests/test_set_chapters_unit.py::test_set_chapters_writes_manifest
  - NotImplementedError
```

After Work item 3 the same test passes; after Work item 6 the installed e2e
prints an `ok: true` envelope:

```plaintext
{"command": "novel-state", "ok": true, "result": {"chapters": [ ... ]}, ...}
```

## Validation and acceptance

Acceptance is behavioural, matching the roadmap Success clause:

1. **Command-only path.** Build a fresh tree with `novel-state init`, then run
   `novel-state set-chapters --chapters '[{"number":1,...},{"number":2,...}]'`.
   `working/state.toml` `[chapters]` is populated and
   `working/manuscript/chapter-01/` and `chapter-02/` exist. No step
   hand-edited `state.toml`.
2. **Incoherent plan refused.** Run the command with a non-contiguous plan
   (numbers `[1, 3]`) and with a duplicate number (`[1, 1]`); each exits **3**,
   emits `ok: false`, and leaves `state.toml` byte-for-byte unchanged.
3. **Malformed invocation refused.** `--chapters '[{not json'` exits **2**.
4. **Downstream commands work.** After step 1, `novel-state check` exits **0**
   (bijection holds); `novel-state recount` returns a by-chapter map *with a
   key per chapter* (the values are all 0 — no drafts exist yet, so the
   assertion checks the keys, not non-zero counts, to avoid overclaiming,
   round-1 review finding 4); and `novel-compile` no longer exits 3 for an
   empty manifest.

Quality criteria ("done"):

- Tests: the new unit, behavioural (bdd), property, and e2e suites pass;
  `tests/test_set_chapters_unit.py::test_set_chapters_writes_manifest` fails
  before Work item 3 and passes after; the Work item 3a torn-turn-recovery test
  fails before 3a and passes after. Existing suites (including the reconcile
  suites) stay green.
- Lint/typecheck/format: `make all` is clean (this covers `ruff format --check`,
  `ruff check`, `interrogate` 100% docstring coverage, Pylint, `ty check`, and
  pytest).
- Audit: `make audit` (`pip-audit`) is clean — run as a separate gate, not part
  of `make all`.
- Markdown (Work item 8): `make markdownlint` and `make nixie` are clean.

Quality method: `make all` then `make audit` (and `make markdownlint` +
`make nixie` for the docs item), run sequentially from the worktree root, all
green before each commit.

## Idempotence and recovery

- Directory creation is `mkdir(parents=True, exist_ok=True)` — idempotent.
- Re-running `set-chapters` against a tree whose manifest is already populated
  is
  refused with exit 3 (D3), so the command is a safe one-shot; it never
  silently overwrites a live manifest.
- A crash mid-turn leaves a populated `operation="set-chapters"`
  `[pending_turn]`
  record over a **persisted, populated** manifest (the manifest and the intent
  land together at the first write — D10), with one or more `chapter-NN/`
  directories missing. This includes the **partial-directory** case (manifest
  `{1,2}`, on-disk `{1}`), which fires `manifest-disk-bijection`. A subsequent
  `novel-state check` reports it and `novel-state reconcile` resolves it by
  COMPLETE-ing the turn — creating the missing `chapter-NN/` directories and
  clearing the record (Work item 3a, D8; design §3.4, §5.4). The precedence
  branch (Work item 3a) is what lets `reconcile` reach COMPLETE despite the
  fired bijection refuse-class, but only when the break is fully explained by
  the pending-turn's missing dirs; an unexplained break still REFUSEs. This is
  the *only* sanctioned recovery: a `set-chapters` re-run is refused by D3 and
  no manual `mkdir` is required. The empty directories reconcile creates are
  deterministically derivable from the already-written manifest (D10 guarantees
  it is on disk), so the recovery fabricates no agent judgement (recomputable,
  exactly like reconcile re-deriving `log.md`/`[word_counts]`). Before Work
  item 3a this recovery path did not exist (the existing reconcile REFUSEs the
  partial-directory case at the bijection arm and ROLLBACKs the all-missing
  case — S5 corrected); it is the resolution of the round-2 B1 blocking point.
- A refused write leaves `state.toml` byte-for-byte intact; no recovery needed.
- All test trees are built under `tmp_path`; nothing touches the developer's
  working tree.

## Artifacts and notes

Cyclopts JSON-list verification (locked 4.18.0), run in the worktree venv:

```plaintext
$ uv run python -c '...list[Ch] app(["setch","--chapters","[{...},{...}]"])...'
cyclopts 4.18.0
OK [Ch(number=1, slug='a', ...), Ch(number=2, slug='b', ...)]
```

Cyclopts coercion-fault mapping (S2), re-run this round against locked 4.18.0
with `exit_on_error=False`:

```plaintext
badjson      -> CycloptsError: CoercionError  (runner maps -> exit 2)
missingfield -> CycloptsError: CoercionError  (runner maps -> exit 2)
wrongtype    -> CycloptsError: CoercionError  (runner maps -> exit 2)
```

The "JSON List Parsing" feature is documented (S6): the cyclopts Read-the-Docs
"User Classes" page states "Cyclopts also supports JSON parsing for lists of
dataclasses" (web-search-confirmed this round); the in-process probe above is
the canonical pin for the locked 4.18.0 behaviour.

Reconcile precedence, verified by source read this round (S5 corrected):
`derive_reconciliation` (`state/reconcile.py` lines 258-264) evaluates the
refuse-class FIRST —
`refuse = [n for n in fired if n in _REFUSE_CLASS]` then
`if refuse: return _refuse(...)` —
and `_REFUSE_CLASS` (lines 78-83) contains `MANIFEST_DISK_BIJECTION`.
`_check_manifest_disk_bijection` (`disk_evidence.py` lines 112-134) fires on any
`manifest != on_disk` with no pending-turn exemption. So a PARTIAL-directory
torn `set-chapters` turn REFUSEs before `_classify_pending_turn` runs — the
round-2 B1 finding. Work item 3a's guarded precedence branch is the fix; editing
`_RECOMPUTABLE_BASENAMES` alone (the round-1 plan) would be dead code in that
path.

cuprum API pinned for the e2e (locked 0.1.0):
`cuprum/sh.py::make(program, *, catalogue)` → `SafeCmdBuilder`;
`SafeCmd.run_sync(context=ExecutionContext(...), capture=True)`;
`cuprum/catalogue.py::ProgramCatalogue(*, projects=[...])`. Used only to drive
the installed binary as a subprocess, never inside the command (design §4:
"cuprum is required only where a command shells out (none do in v1)").

## Interfaces and dependencies

No new external dependency. Cyclopts 4.18.0 and tomlkit are already locked
(`pyproject.toml`, `uv.lock`).

New/changed symbols at completion:

- `novel_ralph_skill/commands/_set_chapters.py`:

```python
@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterPlanEntry:
    number: int
    slug: str
    title: str
    target_words: int

def manifest_coherence_violations(
    entries: cabc.Sequence[ChapterPlanEntry],
) -> tuple[str, ...]: ...

def set_chapters(*, chapters: list[ChapterPlanEntry]) -> CommandOutcome: ...
```

  (If `manifest_coherence_violations` outgrows the module, it moves to
  `novel_ralph_skill/state/manifest.py` and is exported from
  `novel_ralph_skill/state/__init__.py`.)

- `novel_ralph_skill/state/__init__.py`: export `chapter_dir_name` (re-export of
  `_disk_paths._chapter_dir_name`).
- `novel_ralph_skill/commands/novel_state.py::build_app`: a new `set-chapters`
  subcommand delegating to `_set_chapters.set_chapters`.
- `novel_ralph_skill/state/reconcile.py` (Work item 3a): `derive_reconciliation`
  gains a **guarded branch ahead of the refuse arm** (via a pure predicate, e.g.
  `_set_chapters_turn_explains_bijection`) that classifies an
  `operation="set-chapters"` `[pending_turn]` as `COMPLETE_PENDING_TURN` when
  the fired refuse-class is exactly `{manifest-disk-bijection}` AND the break
  is fully explained by the pending-turn's missing chapter dirs. Any
  unexplained break still REFUSEs. The `Reconciliation` shape and the
  `derive_reconciliation` signature are unchanged (they already carry
  `operation`/`missing_paths`); the module docstring's precedence narrative and
  the `_REFUSE_CLASS` comment are updated to describe the new branch (ADR 008,
  §5.4).
- `novel_ralph_skill/commands/_reconcile.py` (Work item 3a): the
  `COMPLETE_PENDING_TURN` dispatch is extended to
  `mkdir(parents=True, exist_ok=True)` each missing `chapter-NN/` directory
  (derived from `missing_paths`) when the torn record's
  `operation == "set-chapters"`. No deletion; the existing `reconcile`-operation
  `[word_counts]` path is unchanged.
- Reuse without change: `state/document.py`
  (`load_document`/`write_document_atomically`/`open_pending_turn`/
  `clear_pending_turn`), `commands/_state_mutators.py`
  (`_load_document_or_state_error`/`_state_view_or_state_error`/
  `_refuse_if_incoherent`), `contract/runner.py` (`run`, `CommandOutcome`,
  `StateInputError`).

## Revision note

Initial draft (2026-06-25). Decomposes roadmap task 2.2.3 into eight ordered,
independently gate-passable work items. Pins the cyclopts 4.18.0 JSON-list
input mechanism (verified in-process), the exit-2 (cyclopts shape fault) vs
exit-3 (body semantic refusal) split (verified against `runner.run`), the
directory-creation decision that makes the §5.2 bijection hold (verified against
`disk_evidence.py`), and the cuprum-for-tests-only boundary (verified against
the locked cuprum 0.1.0 and design §4). No undecided forks remain; each
behavioural claim is either verified-and-cited (Surprises S1-S4) or pinned by a
named test in the plan.

Revision 2 (2026-06-25) — round-2 design review (round 1 was "proceed with
conditions"; the two blocking points are resolved):

- **What changed.** (1) Resolved the torn-turn recovery contradiction: added
  **Work item 3a** which extends `reconcile` to COMPLETE a torn `set-chapters`
  turn by creating the manifest's missing `chapter-NN/` directories, with a new
  Decision D8 (chosen over weakening D3 or documenting a manual `mkdir`),
  verified against `state/reconcile.py::_RECOMPUTABLE_BASENAMES` /
  `_classify_pending_turn` and `commands/_reconcile.py::_pending_turn_edit`
  (S5), and pinned by a new unit test plus a BDD recovery scenario. D3 is left
  unchanged (strict one-shot guard); reconcile, not a re-run, owns recovery.
  Updated Constraints (sanctioned-recovery invariant), Risks (the torn-turn
  risk is now RESOLVED, severity raised to high to reflect the round-1
  finding), Idempotence/recovery, the §5.4 / developers-guide / ADR-008 doc
  updates, the SKILL.md bridge, and the Interfaces section. (2) Corrected the
  commit gate: `make all` is `build check-fmt lint typecheck test` (no
  `audit`); added `make audit` as a separate per-work-item gate in the
  Plan-of-work intro, Concrete steps, every work item's Validation line, and
  Quality criteria, noting `interrogate`/Pylint are inside `make lint` hence
  already covered.
- **Also tightened from round-1 advisories.** firecrawl/web-search-confirmed the
  cyclopts JSON-List-Parsing doc (S6) so the URL is corroboration not memory;
  WI6 now pins a *missing-required-field* exit-2 proof as well as malformed
  JSON; the recount acceptance no longer overclaims (asserts keys, not non-zero
  counts); added a stray-`chapter-NN/`-dir risk note. Scope tolerance raised to
  ~12 files (the value recorded in the Tolerances section) to include the two
  reconcile modules WI3a touches.
- **Effect on remaining work.** The plan now has nine work items (1, 2, 3, 3a,
  4-8). Work item 3a must land after Work item 3 (it depends on the
  `set-chapters` `[pending_turn]` shape) and before the behavioural work item 5
  (which adds the recovery scenario). No undecided forks remain.

Revision 3 (2026-06-25) — round-2 design review (verdict REVISE; three blocking
points B1/B2/B3 resolved):

- **B1 (precedence — Work item 3a was unreachable).** The round-2 reviewer
  proved
  that `derive_reconciliation` evaluates the refuse-class (containing
  `manifest-disk-bijection`) BEFORE the pending-turn branch, so the round-1
  classifier-only change was dead code for a partial-directory torn turn
  (REFUSE, exit 4, before classification). **Fix:** Work item 3a is rewritten
  as a SCOPED PRECEDENCE CHANGE — a guarded branch in `derive_reconciliation`
  that classifies a `set-chapters` `[pending_turn]` ahead of the bijection
  REFUSE *only* when the break is fully explained by the pending-turn's missing
  chapter dirs (and the fired refuse-class is exactly
  `{manifest-disk-bijection}`). Any unexplained break still REFUSEs. S5
  corrected to record the precedence finding; D8 rewritten; the Tolerances
  escalation trigger reframed (the precedence change is now the deliberate
  planned change, with a narrower escalation boundary); the partial- directory
  case (round-2 A2) is now the decisive test in Work items 3a and 5, plus three
  negative "still-REFUSE" tests.
- **B2 (write ordering made the manifest unrecoverable).** The round-1 plan
  mirrored `reconcile`'s ordering (intent write of the ORIGINAL empty manifest
  → edit → clear+write), so a crash in the directory window lost the agent's
  plan. **Fix:** new Decision D10 and a rewritten Work item 3 — the populated
  `[chapters]` manifest is edited into the document and persisted TOGETHER with
  the `[pending_turn]` record at the FIRST atomic write, before any directory
  is created (verified the seam allows it: `open_pending_turn` only appends the
  `[pending_turn]` table). New Constraint "Manifest persists AT the intent
  write"; new unit test (3f) injecting a mkdir failure and asserting the
  manifest is already persisted; Idempotence/recovery rewritten.
- **B3 (recomputable-set amendment under-justified).** Adding `chapter-NN/` to
  the
  recomputable artefacts and changing the precedence are genuine
  design-invariant changes. **Fix:** Work item 8 now records both in ADR 008
  and amends design §5.4 (the recomputable enumeration AND the precedence
  statement) and the developers' guide, with the precedence narrative and the
  persisted-manifest rationale spelt out; D8 frames it as a reasoned amendment,
  not a tweak.
- **A1 (manifest-only alternative).** New Decision D9 gives the explicit
  trade-off
  and rejects it: the roadmap MANDATES the `[pending_turn]` bracket (2.2.3
  lines 715-719) and the design makes the bijection a firm immediate invariant
  (§5.1 lines 398-404, §5.2), so manifest-only would leave `check` at exit 4
  the instant the command returns and reconcile's draft-without-manifest path
  is a REFUSE not a repair.
- **Effect on remaining work.** Still nine work items; Work items 3 (ordering)
  and
  3a (precedence) are the substantive redesigns. No undecided forks remain;
  every load-bearing claim is verified against source (S5 corrected, D10's seam
  check) or pinned by a named test.
