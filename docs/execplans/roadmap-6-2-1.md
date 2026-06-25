# Build the combinatorial command-surface test suite

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.2.1 asks for a test suite that proves the five console-scripts
behave correctly across the whole verification surface — every
`command × output-mode × phase` combination — rather than only in the isolated
slices each command's own suite already covers (`docs/roadmap.md` lines
1284-1292; `docs/novel-ralph-harness-design.md` §2.3 lines 125-129 and §9 lines
817-821).

After this change a reviewer can run `make test` and see, for each of the five
commands, a parametrised matrix that:

1. snapshots the machine-mode JSON envelope per command across the eleven
   coherent phase states,
2. asserts the `--human` rendering is present (non-empty, no crash) for the
   same cells, and
3. carries semantic assertions over the phase-dependent branches — pinned
   directly against the *verified* per-phase envelope, not against an
   assumed-invariant shape.

The surface is bounded deliberately: the design carries the exhaustive
cross-product gaps "knowingly rather than silently"
(`docs/novel-ralph-harness-design.md` §9 lines 819-821). This plan adds one
module that documents exactly which cells are covered and which combinatorial
gaps are carried, so the success criterion — "the
`command × output-mode × phase` matrix is covered, with the knowingly carried
gaps documented rather than silently omitted" (`docs/roadmap.md` lines
1290-1292) — is met in code, not in prose alone.

This is **planning round 4**. Round 1 (`roadmap-6-2-1.review-r1.md`) found
three factual errors in the per-phase behaviour assumed across the phase axis;
round 2 (`roadmap-6-2-1.review-r2.md`) confirmed every pinned *value* now
reproduces exactly, but caught one residual rationale defect (B4): a prior
draft mis-attributed the `done` tree's predicate failure to
`compile_consistent`, when the verified sole failing clause is
`knitting_gates_passed` (and `compile_consistent` is True on the `done` tree).
Round 3 corrected that attribution and added the corpus surprise; round 4
(`roadmap-6-2-1.review-r3.md`) caught a B4-class residual (B5): the
**pre-drafting** band's failing-clause rationale mis-named
`all_chapters_flagged` as a failure, when `all_chapters_flagged` is **True** on
the empty-manifest pre-drafting trees (it holds **vacuously** —
`done_predicate.py` line 182). The verified pre-drafting failing clauses are
`phase_is_done`, `final_pass_complete`, `knitting_gates_passed`, and
`compile_consistent` (compiled.md missing). This round corrects the
pre-drafting attribution in Surprises and the Work item 3 docstring guidance,
keeps the correct `drafting`-band attribution (`all_chapters_flagged` False
**only** there), and — taking the round-3 review's Wafflecat alternative — pins
the failing-clause set **in code per band** (a representative pre-drafting,
drafting, and `done` cell each assert their clause booleans), so a docstring
can no longer mis-describe a clause set the test itself pins. The round-3
corpus Surprise (the `done` spec's gate booleans are all True yet
`knitting_gates_passed` is False on disk because no `knitting_reviews` are
written) is retained. Every load-bearing per-phase envelope was captured from
the real commands driven in-process over the real corpus trees (see
`Surprises & discoveries` — the ground-truth envelope table). The plan pins
each cell to that verified envelope and a cited design clause. No cell is left
"to be decided at implementation time".

Observable success: `make test` passes; the new module
`tests/test_command_surface_matrix.py` contributes the matrix; deleting any one
command's phase branch (e.g. making `novel-done`'s `phase_is_done` clause
ignore the phase) makes a named test in the new module fail.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work happens **only** in the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-1`. The
  root/control worktree is off-limits for edits.
- **No production code changes.** This task adds tests only. If a command's
  observable behaviour turns out to be wrong, that is a defect to escalate, not
  to "fix" by adjusting an assertion or touching `novel_ralph_skill/`. The five
  command bodies, the `run` wrapper, the envelope, and the corpus are all
  consumed unchanged.
- **Consume the corpus by the repo convention.** The corpus is on `sys.path`
  through the `pytest_plugins` registration in `tests/conftest.py` (lines
  37-53), and the established convention in every corpus-consuming test module
  is a top-level `import working_corpus as wc`
  (`tests/test_compile_check_snapshots.py` line 27;
  `tests/test_compile_unit.py` line 25; `tests/test_reconcile_derivation.py`
  line 30). The new module follows that convention. Spec *types* that appear in
  annotations come through the
  `if TYPE_CHECKING: from working_corpus import WorkingTreeSpec` carve-out
  `tests/conftest.py` re-exports (lines 62-69), not a runtime annotation
  import. The phase trees are built either through the registered fixtures
  (`phase_state_tree`, `phase_names`, `baseline_tree`) or, where a test
  iterates every phase in one body, through
  `wc.build_working_tree(wc.PHASE_STATES[phase], dest)` directly under
  `tmp_path` — the exact pattern `phase_state_tree` itself uses
  (`tests/corpus_fixtures.py` lines 195-201).
- **No new shared scaffolding duplicated.** Any helper shared with another test
  module must live in `tests/conftest.py` as a fixture, not be copied
  (`AGENTS.md` "Shared test scaffolding"; developers-guide lines 35-37). The
  in-process drive helper this plan introduces is local to the new module
  unless a second module needs it.
- **Drive commands in-process, not through a wheel.** 6.2.1 is the fast
  in-process matrix; installed-binary coverage is the separate scope of roadmap
  tasks 6.2.4 and 6.2.2. New tests therefore carry **no** `@pytest.mark.slow`
  and **no** `@pytest.mark.timeout` override; the global `timeout = 30`
  (`pyproject.toml` line 326) governs them.
- **Snapshots must be reviewer-useful and non-volatile.** Redact or avoid
  timestamps, absolute paths, slugs, and ordering-dependent maps; pair every
  snapshot with a semantic assertion so no behaviour is snapshot-only
  (`AGENTS.md` "Python verification and testing" lines 148-158;
  `docs/novel-ralph-harness-design.md` §9 lines 811-813).
- **en-GB Oxford spelling** (`-ize`/`-yse`/`-our`) in all docstrings, comments,
  and the plan prose (`AGENTS.md` line 18; `en-gb-oxendict` skill).
- All quality gates in `AGENTS.md` "Change quality and committing" must pass
  before each commit.

## Tolerances (exception triggers)

- Scope: if the suite needs more than **6 new/changed files** or more than
  **600 net lines** (test bodies plus generated `.ambr` snapshots excluded from
  the line count, since syrupy generates them), stop and escalate. A dry line
  count is taken at the end of Work item 4 and recorded in Progress; if it is
  trending past 600 the carried-gap doc (Work item 5) is trimmed to a comment
  rather than a developers-guide subsection, and that choice is escalated.
- Production code: if **any** edit to `novel_ralph_skill/` appears necessary,
  stop and escalate — it means a real behavioural defect or a missing seam, not
  a test-suite task.
- Corpus gap: if a phase state the matrix needs is **not** expressible through
  the existing `working_corpus` surface (`PHASE_STATES`, `WorkingTreeSpec`),
  stop and escalate rather than extending the corpus inside a 6.2.1 commit —
  the corpus is consumed unchanged by phases 2-6 (developers-guide lines 80-81).
- Iterations: if a matrix cell's assertion still fails after **3** attempts to
  express the expected behaviour, stop and escalate. Because every expected
  value in this round-2 plan is pinned to a *verified* envelope (see
  Surprises), a third failure signals a real behavioural change in the command,
  which is a defect to adjudicate, not a test bug.
- Ambiguity: this plan carries **no** undecided cell. If implementation
  nonetheless meets a cell whose expected value the verified table does not
  cover (e.g. a corpus change landed that altered a phase tree), stop and
  re-capture the envelope before pinning, then record it in Surprises.

## Risks

    - Risk: A corpus refactor between planning and implementation changes a
      phase tree (e.g. populates a pre-drafting manifest), invalidating a pinned
      expected envelope.
      Severity: medium
      Likelihood: low
      Mitigation: Every pinned value is reproducible by re-running the
      ground-truth capture in `Surprises & discoveries`. Re-run it first if any
      semantic assertion fails unexpectedly; if the corpus changed, escalate
      (the corpus is meant to be unchanged by phases 2-6, developers-guide lines
      80-81), do not silently re-pin.

    - Risk: Snapshotting eleven phases × five commands produces a large,
      churn-prone `.ambr` file that fails on harmless formatting drift.
      Severity: medium
      Likelihood: medium
      Mitigation: Snapshot only the machine-mode envelope (already
      path/timestamp-free for these commands — proven by
      `tests/test_novel_done_snapshots.py` lines 12-14 and
      `tests/test_compile_check_snapshots.py` lines 6-9) and reuse the
      volatile-field guard from `tests/test_novel_done_snapshots.py`. Pair every
      snapshot with a direct semantic assertion so churn is distinguishable from
      a real contract change. `desloppify`'s envelope embeds the whole rule pack
      (24 findings with regex `phrase` strings); this is deterministic for the
      shipped pack, so it snapshots cleanly, but it makes the `.ambr` large —
      acceptable because it is the literal machine contract §9 line 811 asks to
      pin.

    - Risk: Over-snapshotting re-pins contracts the per-command suites already
      own, duplicating coverage and doubling the churn surface.
      Severity: low
      Likelihood: medium
      Mitigation: The matrix's job is the *cross-product* (same command across
      phases, both output modes), not re-proving a single cell the per-command
      suite already snapshots. `tests/test_compile_check_snapshots.py` already
      snapshots the `MATCHES`/`DIVERGES` envelopes on a hand-built drafting tree;
      the matrix's compile cells add value by driving `--check` across the
      **phase axis** (proving the exit-3 / exit-4 / exit-0 split is phase-keyed),
      not by re-pinning one tree. `tests/test_validate_state_corpus.py` already
      proves the coherent corpus passes the oracle; the matrix's `check` cell adds
      value only by driving `novel-state check` through the **command envelope**,
      so its assertion is on the envelope `ok`/`violations`, not the oracle
      (review advisory A2). Record the de-duplication in the Decision Log.

    - Risk: The `novel-state` command is a multi-subcommand surface; "the
      command across phases" is ambiguous (which subcommand?).
      Severity: low
      Likelihood: high
      Mitigation: Treat each *query* surface as the phase-sensitive unit:
      `novel-state check` (and the read commands `novel-done`, `wordcount`,
      `novel-compile --check`, `desloppify`). Mutators (`init`, `set-cursor`,
      `advance-phase`, `recount`, `reconcile`) are command/query-segregated
      (§3.3) and are not the phase-read surface this task targets; they are
      covered by their own suites and by tasks 6.2.2/6.2.5. Record this scoping
      in the Decision Log and in the module docstring's carried-gaps note.

## Progress

    - [x] (2026-06-25) Stage A: orientation and matrix design pinned in this
      plan. Corpus/drive/snapshot patterns surveyed; the per-phase ground-truth
      envelope for all five read commands captured in-process and recorded in
      Surprises.
    - [x] (2026-06-25) Work item 1: machine-mode envelope snapshot matrix across
      the eleven phases per command (folds the scaffold/drive helper in; first
      commit is green — review advisory A3). Delivered
      `tests/test_command_surface_matrix.py` with the `_ReadCommand` registry, the
      `drive` fixture (bundling `monkeypatch`/`capsys` to stay within the
      argument-count gate), the volatile guard, and `test_machine_envelope_matrix`
      (55 cells); `tests/__snapshots__/test_command_surface_matrix.ambr`
      generated. The ground-truth envelope table in Surprises was re-captured
      in-process and reproduced exactly. `make all` green (845 passed, 1 skipped).
    - [x] (2026-06-25) Work item 2: human-mode presence matrix across the same
      cells. Added `test_human_mode_presence_matrix` (55 cells): asserts the
      `--human` body is non-empty and names the command, with the drive catching
      the command's `SystemExit` so the compile exit-3 pre-drafting cells assert
      presence (not exit 0). Every command's human rendering carries
      `command: <name>` (verified in-process), so naming the command is a sound,
      non-volatile presence token. `make all` green (900 passed, 1 skipped);
      coderabbit: 0 findings.
    - [x] (2026-06-25) Work item 3: semantic phase-branch assertions for the
      genuinely phase/word-sensitive commands (`novel-done`, `wordcount`,
      `novel-state check`). Added `test_done_phase_clause_across_phases` (asserts
      `phase_is_done` true only on `done`, plus the per-band failing-clause set
      pinned in code: pre-drafting `all_chapters_flagged` True /
      `compile_consistent` False; `drafting` `all_chapters_flagged` False; `done`
      `knitting_gates_passed` False / `compile_consistent` True),
      `test_check_coherent_across_phases` (envelope `ok`/`violations`, not the
      oracle), and `test_wordcount_branch_across_phases` (zero-progress vs
      populated branch). A `_drive_machine_result` helper folds the per-phase
      build+drive+result extraction. The module crossed the 400-line Pylint cap,
      so a justified `# pylint: disable=too-many-lines` was added (the matrix is
      one module by Decision Log; same idiom as `test_working_corpus.py`).
      `make all` green (903 passed, 1 skipped); coderabbit: 0 findings.
    - [x] (2026-06-25) Work item 4: branch assertions for the manifest-sensitive
      commands (`novel-compile --check`, `desloppify`), pinned to the three real
      branches, not a false invariant. Added
      `test_compile_check_branches_across_phases` (exit 3 / result {} / manifest
      message for the eight pre-drafting phases; exit 4 / diverged True for
      `drafting`; exit 0 / diverged False for `final-pass`+`done`) and
      `test_desloppify_shape_across_phases` (stable key set, empty violations,
      24-rule pack on every phase; `total_words` 0 pre-drafting vs 68800 drafting
      era). A `_drive_machine_envelope` helper exposes the top-level `messages` the
      exit-3 branch asserts. Dry net line count (snapshots excluded):
      `tests/test_command_surface_matrix.py` is **558 lines**, under the 600-line
      tolerance — no escalation, the developers-guide subsection (Work item 5)
      proceeds as planned. `make all` green (905 passed, 1 skipped); coderabbit:
      0 findings.
    - [x] (2026-06-25) Work item 5: documented carried-gaps note and the
      developers-guide cross-reference; record the dry line count against the
      tolerance. The module-level `Carried gaps` docstring section was authored in
      Work item 1 (mutator-by-phase, exhaustive eleven-phase cross-product for the
      manifest-sensitive commands, incoherent-variant-by-phase, installed-binary
      crossing). Added a `### The combinatorial command-surface matrix` subsection
      to `docs/developers-guide.md` (under "Shared test scaffolding") naming the
      module as the matrix home and pointing at its carried-gap list. Net line
      count is 558 (< 600), so the developers-guide subsection was kept rather than
      trimmed to a comment — no escalation. `make all` plus `make markdownlint`
      (developers-guide: 0 errors) and `make nixie` (all diagrams valid) green;
      coderabbit: 0 findings (after waiting out a rate-limit window with
      exponential backoff).

## Surprises & discoveries

    - Observation: The `working_corpus` package already exposes every coherent
      phase state via the `phase_state_tree(phase)` fixture and `phase_names()`,
      built from `PHASE_STATES` over the eleven-member `PHASE_ORDER`.
      Evidence: `tests/corpus_fixtures.py` lines 163-203;
      `tests/working_corpus/_library.py` lines 23-118.
      Impact: 6.2.1 needs no new corpus data; it consumes the phase surface the
      task 1.3.2 corpus already built for "phases 2-6 unchanged".

    - Observation (resolves review B1/B2/B3): the per-phase ground-truth
      envelope for all five read commands was captured by driving each
      `build_app()` in-process through `run(…, RunContext(working_dir="working",
      human=False))` over `wc.build_working_tree(wc.PHASE_STATES[phase], dest)`
      and parsing stdout. The verified table is the contract this plan pins to:
      Evidence (reproducible capture):

        for phase in PHASE_ORDER:
            build_working_tree(PHASE_STATES[phase], dest)   # chdir(dest)
            run(build_app(), argv, RunContext(command=name,
                working_dir="working", human=False))        # parse stdout JSON

      Verified per-phase results:

        * novel-state check — exit 0, ok=True, result["violations"] == [] for
          ALL eleven phases (the corpus phase states are coherent by
          construction).
        * novel-done — exit 1, ok=False for ALL eleven phases (the corpus never
          reaches the full done predicate). The reasons differ by phase band, and
          were captured per clause, not assumed:
            - the eight pre-drafting phases (premise…chapter-planning) have an
              empty manifest, so the failing clauses are `phase_is_done`,
              `final_pass_complete`, `knitting_gates_passed`, and
              `compile_consistent` (compiled.md absent → ABSENT → False).
              Captured `messages` (verbatim, both `premise` and
              `chapter-planning`): `["phase_is_done is false",
              "final_pass_complete is false", "knitting_gates_passed is false",
              "compile_consistent is false (compiled.md missing)"]`. Note that
              `all_chapters_flagged` is **True** here, not a failing clause: it
              holds **vacuously** over the empty manifest
              (`all(... for chapter in state.chapters)` over `chapters == ()` is
              `True` — `novel_ralph_skill/state/done_predicate.py` line 182, "An
              empty manifest holds vacuously"). The round-3 review's B5 caught a
              prior draft mis-attributing the pre-drafting failure to
              `all_chapters_flagged`;
            - `drafting` flags all-but-last chapter and has compiled.md absent, so
              `all_chapters_flagged`, `final_pass_complete`, and
              `compile_consistent` are False;
            - the `done` tree's sole failing clause is `knitting_gates_passed`.
              Captured result on the `done` tree (verbatim, driven in-process):
              `{"phase_is_done": true, "final_pass_complete": true,
              "all_chapters_flagged": true, "knitting_gates_passed": false,
              "compile_consistent": true, "no_unresolved_blockers": true}`,
              `messages == ["knitting_gates_passed is false"]`. Note in
              particular `compile_consistent` is **True** on the `done` tree
              (it carries a matching COMPILED_AUTO); the round-2 review's B4
              caught a prior draft mis-attributing the `done` failure to
              `compile_consistent`. The verified failing clause is
              `knitting_gates_passed` (see the dedicated Surprise below for why a
              `done` tree whose gate booleans are all True still fails it).
          BUT result["phase_is_done"] is True ONLY for the `done` phase and False
          for the other ten. So the envelope `ok`/exit is a constant (1/False)
          across phases, while `phase_is_done` is the phase-keyed datum.
        * wordcount — exit 0, ok=True for ALL eleven phases. The eight
          pre-drafting phases plus the `chapter-planning` phase (empty manifest,
          chapters=()) emit the zero-progress branch:
          result["chapters"] == [] and result["cumulative"] ==
          {"current": 0, "target": 80000, "percent_of_target": 0.0,
           "gate_triggered_30": false, "gate_triggered_50": false,
           "gate_triggered_80": false, "next_gate_threshold": 0.3,
           "next_gate_distance": 24000}. The three drafting-era phases
          (drafting/final-pass/done) emit the populated branch (three chapter
          rows, current 68800, all three gates triggered,
          next_gate_threshold null). This pins review B3's "zero-progress branch
          the design implies" to a *verified* value (the design pins the
          totality guard at `_wordcount_report._gate_geometry`, §4.5 and
          `validate.py:261`).
        * desloppify — exit 0, ok=True for ALL eleven phases. The result *shape*
          is stable: keys {pack, total_words, violations, findings};
          violations == [] (no rule over threshold on the clean corpus);
          findings is the full 24-rule pack on EVERY phase (a zero-chapter scan
          still emits every rule with count 0). total_words is the only
          phase-varying datum: 0 for the eight empty-manifest pre-drafting
          phases, 68800 for the three drafting-era phases. So desloppify is
          shape-invariant but NOT value-invariant across phases — review B3's
          concern, now verified and pinned.
        * novel-compile --check — THREE distinct branches across the phase axis
          (review B1/B2):
            - exit 3, ok=False, result={} for the eight pre-drafting phases
              (premise…chapter-planning): empty manifest, `_require_chapter_
              manifest` raises StateInputError (_compile.py lines 76-96, 207;
              design §10 lines 811-815). messages ==
              ["cannot compile: chapter manifest is absent or empty"].
            - exit 4, ok=False, result={"checked": "working/manuscript/
              compiled.md", "chapters": 3, "diverged": true} for `drafting`
              (compiled.md ABSENT on the drafting tree → ABSENT projects to the
              actionable-finding branch, _compile.py lines 178-184, 223-236).
            - exit 0, ok=True, result={…, "diverged": false} for `final-pass`
              and `done` (those trees carry COMPILED_AUTO, so MATCHES,
              _library.py lines 81-97, _compile.py lines 213-222).
      Impact: review B1 is fixed by registering argv ["--check"] (the bare []
      write path would mutate the tree and capture the write envelope; the repo
      documents this trap at `tests/test_compile_check_snapshots.py` lines 13-16).
      Review B2 is fixed by asserting the three real branches, not a false
      invariant. Review B3 is fixed by pinning the verified zero-progress /
      shape-stable envelopes above.

    - Observation (resolves review B4 — load-bearing corpus surprise): the
      `working_corpus` `done` spec sets the three knitting-gate booleans
      `done_30/done_50/done_80 = True` (via `_crossed_gates()`, which returns
      `(True, True, True)` because the 68800 drafted words are 0.86 of the 80000
      target — `tests/working_corpus/_library.py` lines 60-64, 83-96), yet the
      `knitting_gates_passed` clause evaluates **False** on disk for that tree.
      Evidence (re-captured in-process, verbatim): the `done` tree's
      `novel-done` result is
      `{"phase_is_done": true, "final_pass_complete": true,
      "all_chapters_flagged": true, "knitting_gates_passed": false,
      "compile_consistent": true, "no_unresolved_blockers": true}` with
      `messages == ["knitting_gates_passed is false"]`. Root cause, verified in
      source: `knitting_gates_passed` (D-CLAUSES) requires **both** the three
      gate booleans **and** the three `reviews/knitting-{30,50,80}.md` files to
      exist (`novel_ralph_skill/state/done_predicate.py` lines 191-210). The
      `_library.py` `done` spec leaves `knitting_reviews=()` (the default,
      `tests/working_corpus/_specs.py` line 200), so the builder writes **no**
      `reviews/` directory (`tests/working_corpus/_builder.py` lines 188-201,
      guard at line 196: "created only when `knitting_reviews` is non-empty"). So
      the gate booleans are True in `state.toml` but the review files are absent
      on disk, and the clause is False.
      Impact / adjudication: this is an **intended carried property**, not a
      corpus defect to escalate. The `_library.py` phase corpus builds trees that
      are *phase-coherent* (each `state.toml` is internally consistent), but the
      `done` tree is deliberately "phase=done but predicate-incomplete": it never
      sets `knitting_reviews`. The corpus that *does* satisfy the full done
      predicate lives in a separate module,
      `tests/working_corpus/_done_predicate_specs.py`
      (`DONE_PREDICATE_ALL_HOLD` with `knitting_reviews=ALL_KNITTING_REVIEWS`,
      lines 164, 194), which is owned by the done-predicate suites, not by this
      phase matrix. Because the corpus is consumed unchanged by phases 2-6
      (developers-guide lines 80-81), the matrix pins `phase_is_done=True` only
      and the aggregate `ok=False` for the `done` cell, and records here that the
      sole failing clause is `knitting_gates_passed`. Should a future corpus
      change add `knitting_reviews` to the `done` spec, the `done` cell would flip
      to exit 0/`ok=True`; the machine-envelope `ok`-sign assertion (Work item 1)
      and the snapshot would catch that loudly — which is correct — and the
      Iterations/Corpus-gap tolerances require re-capturing and escalating, not
      silently re-pinning. The Work item 3 docstring must name
      `knitting_gates_passed` as the `done` tree's failing clause, never
      `compile_consistent`; and (round 4, B5) must name the pre-drafting band's
      failing clauses as `phase_is_done`, `final_pass_complete`,
      `knitting_gates_passed`, and `compile_consistent`, never
      `all_chapters_flagged` (which holds vacuously over the empty manifest —
      `done_predicate.py` line 182). Both attributions are pinned in code by the
      per-band clause assertions (Work item 3), not by docstring alone.

    - Observation: The in-process drive-and-snapshot pattern this task needs is
      already established and locked-version-proven, and the corpus is consumed by
      a top-level `import working_corpus as wc`.
      Evidence: `tests/test_novel_done_snapshots.py` drives `build_app()` through
      `run(...)` with a `RunContext`, captures stdout, parses the envelope,
      snapshots it, and guards volatile fields; `tests/test_compile_check_
      snapshots.py` lines 27, 44-53 show the `import working_corpus as wc` and the
      `["--check"]` driver; `tests/test_contract_envelope_snapshots.py` proves
      syrupy generates one snapshot per parametrised case keyed by the test id
      under the locked syrupy version.
      Impact: No external syrupy/xdist/timeout research is load-bearing; the repo
      itself pins the behaviour (review advisory A5). The round-1 Constraint
      forbidding a runtime `import working_corpus` was wrong against the repo
      convention and is corrected in this revision.

    - Observation (Work item 1 implementation): the reused `_VOLATILE_PATTERN`
      from `test_novel_done_snapshots.py` has a `/[^/"\s]+/` middle-segment clause
      that fires on the compile checker's *legitimate* working-relative token
      `working/manuscript/compiled.md` (which novel-done's envelope never carries,
      so the guard never tripped there). That token is a fixed contract constant
      by construction (`tests/test_compile_check_snapshots.py` line 8, D-RESULT),
      not a per-run volatile path. The guard now redacts that one constant to
      `<compiled>` before scanning, so it still catches genuine volatile paths and
      the snapshot still pins the token verbatim. This is recorded in the module
      docstring's slug/path note (Decision A1 family).

    - Observation (Work item 1 implementation): two repo-wide lint gates bite the
      new module. (1) The `×` MULTIPLICATION SIGN trips Ruff RUF002
      (ambiguous-unicode in docstrings); the module spells the cross-product as
      `command x output-mode x phase` in ASCII. (2) Pylint enables
      `too-many-arguments`/`too-many-positional-arguments` globally (no test-path
      exemption, unlike Ruff's `per-file-ignores`), so the drive helper and the
      parametrised test must stay within four arguments. Resolved structurally
      rather than with `# pylint: disable`: a `_ReadCommand` NamedTuple bundles
      `(name, build_app, argv)`, a `drive` fixture bundles `monkeypatch`/`capsys`,
      and the parametrised test takes a single `cell` tuple. This mirrors the
      repo's fixture-bundling idiom (`test_wordcount_snapshots.py::build_at_ratio`).

    - Observation / hazard (Work item 1): `make fmt` runs `mdformat-all`, which
      reflows *every* markdown file in the repo (docs/ and skill/), producing a
      large unrelated diff that must not be committed. This is a known recurring
      trap (the worktree carried many prior "spurious make-fmt mdformat churn"
      stashes). Lesson: format Python with `uv run ruff format novel_ralph_skill
      tests` directly, never `make fmt`, and verify with `make all` (whose
      `check-fmt` only checks the Python format). The mdformat churn was stashed
      out, leaving only the intended files.

## Decision log

    - Decision: Add exactly one new test module,
      `tests/test_command_surface_matrix.py`, rather than spreading the matrix
      across the per-command suites.
      Rationale: The task is the *cross-product* view (§2.3 "the combinatorial
      surface is `command × output-mode × phase`"); one module makes the carried
      gaps documentable in one place and keeps each per-command suite focused on
      its own boundary pairs.
      Date/Author: 2026-06-25, planning agent.

    - Decision: Drive every command in-process through
      `novel_ralph_skill.contract.runner.run(build_app(), argv, RunContext(...))`,
      not through the installed console-script.
      Rationale: 6.2.1 is the fast matrix; installed-binary coverage is the
      explicit scope of 6.2.4 and the end-to-end loop scope of 6.2.2
      (`docs/roadmap.md` lines 1293-1341). The in-process drive is the same seam
      `tests/test_novel_done_snapshots.py` and `tests/test_compile_check_
      snapshots.py` use. cuprum is therefore **not** load-bearing for the new
      tests; the installed-binary `cuprum.ProgramCatalogue`/`ProjectSettings`
      seam belongs to 6.2.4 (verified against
      `/data/leynos/Projects/cuprum/cuprum/catalogue.py` lines 33-91 and
      `program.py` line 16). No cuprum API is relied on by this plan.
      Date/Author: 2026-06-25, planning agent.

    - Decision (resolves review B1): register the `novel-compile` read surface as
      `("novel-compile", _compile.build_app, ["--check"])`, never `[]`.
      Rationale: `_compile.build_app`'s default callback is
      `_compile(*, check=False)`; argv `[]` runs `compile_manuscript()`, which
      **writes** `compiled.md` and returns the write envelope `{compiled,
      chapters, bytes}` — a mutator, contradicting the read-surface framing. Only
      `["--check"]` reaches `check_compiled` (`_compile.py` lines 260-263). The
      repo documents exactly this trap (`tests/test_compile_check_snapshots.py`
      lines 13-16, "Driver requirement (ExecPlan D-CHECK-ARGV)").
      Date/Author: 2026-06-25, planning agent.

    - Decision (resolves review B2/B3): split the read surface by
      phase-sensitivity into two assertion styles, per the review's strongest
      alternative (Wafflecat).
      Rationale: `novel-done`, `wordcount`, and `novel-state check` are genuinely
      phase/word-sensitive and earn the full eleven-phase semantic cross-product
      (Work item 3). `novel-compile --check` and `desloppify` are
      manifest-sensitive, not eleven-phase-invariant: compile has three branches
      keyed on the manifest+compiled state (exit 3 / exit 4 / exit 0), and
      desloppify is shape-stable but value-varying (`total_words` 0 vs 68800).
      Asserting a single "eleven-phase invariant" for these two (as round 1 did)
      is false and would trip the 3-attempts tolerance; instead Work item 4
      asserts the real branches, pinned to the verified envelopes in Surprises
      and to §10 / `_require_chapter_manifest` (compile) and §4.4 / §3.3
      (desloppify). The eleven-phase exhaustive cross-product collapse is then a
      documented carried gap (§9 lines 819-821), not a silent omission.
      Date/Author: 2026-06-25, planning agent.

    - Decision (resolves review advisory A3): make the first commit green. Fold
      the drive helper, the registry, and the volatile guard into Work item 1
      (the machine-mode matrix), so the module's first commit is a passing
      snapshot matrix, not a deliberately-red placeholder. No bare failing assert
      and no `xfail` scaffold commit, which would break the "every work item
      gate-passes" rule.
      Date/Author: 2026-06-25, planning agent.

    - Decision (resolves review advisory A1): do not add slug normalisation to
      the volatile guard. The corpus slugs are fixed deterministic
      `chapter-NN` strings built from the manifest index (`_library.py` lines
      45-57), so they do not churn; the snapshot pins them verbatim as part of
      the machine contract. State this explicitly in the module docstring rather
      than omitting the design's named "slugs" field (§9 line 813) silently.
      Date/Author: 2026-06-25, planning agent.

## Outcomes & retrospective

Completed 2026-06-25. All five work items landed as five atomic, gate-passing
commits; every deterministic gate (`make all`) and, for the markdown change,
`make markdownlint`/`make nixie` are green at HEAD; coderabbit returned 0 findings
on the delivered test/doc changes across all five reviews.

Against the roadmap success criterion ("the `command x output-mode x phase` matrix
is covered, with the knowingly carried gaps documented rather than silently
omitted"): the matrix delivers 55 machine-mode snapshot cells, 55 human-mode
presence cells, and five per-command semantic branch tests, all pinned to the
verified per-phase envelopes captured in-process over the real corpus. The carried
gaps are documented in code (the module's `Carried gaps` docstring) and in the
developers-guide, not in prose alone. The regression-catching property holds:
deleting a command's phase branch (e.g. making `novel-done`'s `phase_is_done`
ignore the phase) fails a named test.

No production code or corpus file changed (tests-only, as constrained). No design
clause was found under-specified; every pinned value reproduced the design's §4.2
/ §4.5 / §10 behaviour exactly. Two implementation lessons worth carrying forward
(recorded in Surprises): the reused volatile-field guard needed a one-token
exemption for the deterministic `working/manuscript/compiled.md` path, and `make
fmt` must be avoided in favour of `uv run ruff format` because `mdformat-all`
reflows every repo markdown file.

## Context and orientation

The reader is assumed to know nothing of this repository. Orientation:

- This is a Python package, `novel_ralph_skill`, that ships five console-scripts
  forming a deterministic "spine" for a novel-writing harness: `novel-state`,
  `novel-done`, `novel-compile`, `desloppify`, and `wordcount`
  (`docs/adr-005-command-surface-five-scripts.md`;
  `novel_ralph_skill/commands/names.py`).
- Every command shares one JSON-envelope contract. A command body returns a
  `CommandOutcome` (exit code plus `result`/`messages`); the shared wrapper
  `run` builds the envelope and exits. The envelope carries `command`,
  `schema_version`, `ok`, `working_dir`, `result`, and `messages`
  (`docs/novel-ralph-harness-design.md` §3.1;
  `novel_ralph_skill/contract/runner.py`).
- Each command exposes a `build_app() -> cyclopts.App`. `novel-state` registers
  subcommands (`check`, `init`, `set-cursor`, `advance-phase`, `recount`,
  `reconcile`); the other four register a single default
  (`novel_ralph_skill/commands/novel_state.py`; `_novel_done.py`, `_compile.py`,
  `_desloppify.py`, `_wordcount.py` each at their `build_app`).
  `novel-compile`'s default callback writes `compiled.md` **unless** `--check`
  is passed, in which case it is the read-only divergence checker
  (`_compile.py` lines 239-265).
- Output mode: the default is machine JSON; `--human` switches to a
  human-readable rendering; both go to stdout
  (`docs/novel-ralph-harness-design.md` §3.1;
  `novel_ralph_skill/contract/runner.py`).
- The eleven lifecycle phases are the closed `Phase` enum (`premise … done`), in
  canonical §5.1 order (`novel_ralph_skill/state/phase.py`;
  `docs/novel-ralph-harness-design.md` §5.1). The corpus mirrors this order in
  `tests/working_corpus/_library.py::PHASE_ORDER`.

Existing test scaffolding the matrix builds on:

- The `working_corpus` package (roadmap task 1.3.2) builds a `working/` tree for
  each of the eleven coherent phase states. It is on `sys.path` via the
  `pytest_plugins` registration in `tests/conftest.py` (lines 37-53) and is
  imported by every corpus-consuming test as `import working_corpus as wc`. The
  pre-drafting phases (premise…chapter-planning) carry an **empty** chapter
  manifest (`chapters=()`, `_library.py` lines 67-76); the drafting/final-pass/
  done phases carry a three-chapter manifest, with compiled.md present only for
  final-pass and done (`_library.py` lines 79-97).
- The fixtures: `phase_state_tree(phase) -> Path` (a `(phase) -> Path` factory
  that builds each phase under its own `tmp_path/<phase>` subdir,
  `tests/corpus_fixtures.py` lines 178-203), `phase_names() -> tuple[str, ...]`
  (lines 163-176), `baseline_tree`, `build_tree`, `make_working_tree_spec`,
  `make_chapter_spec` (`tests/corpus_fixtures.py`).
- The in-process drive-and-snapshot pattern: build the tree, change directory to
  the tree parent with `monkeypatch.chdir(working.parent)` (auto-reverted,
  xdist-safe — never a bare `os.chdir`), run `build_app()` through
  `run(app, argv, RunContext(command=..., working_dir="working", human=...))`
  inside `pytest.raises(SystemExit)`, capture stdout with the `capsys` fixture
  (`capsys.readouterr().out`), parse the envelope, snapshot it, and assert the
  parsed `ok`/`result` (`tests/test_novel_done_snapshots.py::_run_capture`
  lines 56-71; the compile suite chdirs in its test bodies at
  `tests/test_compile_check_snapshots.py` lines 89/111 and captures via
  `_drive_check`'s `redirect_stdout` lines 44-53 — this plan follows the
  `_run_capture` `monkeypatch`/`capsys` variant for xdist safety).
- The volatile-field guard `_assert_no_volatile_fields` and its
  `_VOLATILE_PATTERN` regex, which catch absolute paths, ISO dates, and clock
  times (`tests/test_novel_done_snapshots.py` lines 47-84). Reuse this pattern.
- syrupy generates one `.ambr` snapshot per parametrised case, keyed by test id,
  under the locked syrupy version — proven in-repo by
  `tests/test_contract_envelope_snapshots.py`.

Terms defined:

- **Machine mode**: the default JSON-envelope rendering on stdout.
- **Human mode**: the `--human` rendering on stdout; the design asserts it for
  *presence* (non-empty, renders without error), not byte-for-byte
  (`docs/novel-ralph-harness-design.md` §2.3 lines 127-129, §9 lines 817-819).
- **Phase-sensitive command**: one whose *machine result value* varies with the
  phase tree — `novel-done` (`phase_is_done`), `wordcount` (chapter rows + gate
  geometry), `novel-compile --check` (the three manifest branches), and
  `desloppify` (`total_words`).
- **Phase-invariant envelope value**: a datum constant across all eleven phases
  — e.g. `novel-state check`'s empty `violations`, `novel-done`'s exit 1, and
  desloppify's `result` *shape* (keys) and `violations`.
- **Carried gap**: a combinatorial cell the design deliberately does not cover
  (e.g. every mutator × every phase; the exhaustive eleven-phase cross-product
  for the manifest-sensitive commands), documented rather than silently omitted
  (`docs/novel-ralph-harness-design.md` §9 lines 819-821).

## Plan of work

The work is one new test module assembled in five atomic, independently
committable, gate-passable work items. Every work item's first commit is green
(no red-scaffold commit; Decision Log / review advisory A3). No production file
changes.

### Stage A — understand and propose (this document)

Complete: the corpus phase surface, the in-process drive pattern, the
snapshot+guard pattern, and — crucially for round 2 — the verified per-phase
envelope for all five read commands are surveyed and recorded in Surprises.
Go/no-go: proceed only if the in-process drive and the corpus cover all eleven
phases without touching the corpus or production code (they do).

### Work item 1 — machine-mode envelope snapshot matrix (with the drive helper)

Create `tests/test_command_surface_matrix.py` with:

- A module docstring stating the surface (`command × output-mode × phase`), the
  in-process drive decision, the read-surface scoping (mutators excluded), the
  slug-normalisation note (Decision A1), and the carried gaps, citing §2.3 and
  §9.
- A top-level `import working_corpus as wc` (the repo convention) and the
  command registry: an ordered tuple of
  `(console_name, build_app_callable, argv)` for the five **read** surfaces —
  `("novel-state", novel_state.build_app, ["check"])`,
  `("novel-done", _novel_done.build_app, [])`,
  `("wordcount", _wordcount.build_app, [])`,
  `("novel-compile", _compile.build_app, ["--check"])`,  **(B1 fix)**
  `("desloppify", _desloppify.build_app, [])`.
- A `_drive(name, build_app, argv, working, monkeypatch, capsys, *, human)`
  helper modelled on `tests/test_novel_done_snapshots.py::_run_capture` (lines
  56-71), which is the established matching pattern (the compile suite's
  `_drive_check` does **not** itself chdir; its test bodies call
  `monkeypatch.chdir` at lines 89/111). The helper changes directory with
  `monkeypatch.chdir(working.parent)` — **not** a bare `os.chdir` — so the cwd
  is auto-reverted after the test and does not leak across tests sharing a
  `pytest-xdist` worker (review condition A1). It runs
  `run(build_app(), argv, RunContext(command=name, working_dir="working", human=human))`
  inside `pytest.raises(SystemExit)`, captures stdout with the `capsys` fixture
  (`capsys.readouterr().out`, the exact mechanism `_run_capture` uses — review
  condition A2; not `redirect_stdout`), and returns `(exit_code, stdout_text)`.
  Each parametrised test therefore declares `monkeypatch: pytest.MonkeyPatch`
  and `capsys: pytest.CaptureFixture[str]` parameters and threads them into
  `_drive`, mirroring every signature in `test_novel_done_snapshots.py`. For
  machine mode the caller `json.loads` the text; for human mode the caller
  keeps the raw text.
- The reused `_assert_no_volatile_fields` guard (copy the pattern; promote to a
  `conftest` fixture only if a second module later needs it — Constraint).
- `test_machine_envelope_matrix`, parametrised over `wc.PHASE_ORDER` × the
  read-command registry with explicit `ids` so each `.ambr` entry is keyed by
  `command-phase`. For each cell: build the tree with
  `wc.build_working_tree(wc.PHASE_STATES[phase], tmp_path / phase)`, drive in
  machine mode, parse the envelope, assert
  `envelope["command"] == console_name`, assert `envelope["ok"]` matches the
  verified sign for that cell (Surprises table — e.g. `novel-done` is
  `ok=False` for all eleven phases, `novel-compile` is `ok=False` for the eight
  pre-drafting + drafting phases and `ok=True` for final-pass/done), run
  `_assert_no_volatile_fields(envelope)`, and `assert envelope == snapshot`.

Generate snapshots with the syrupy update flow (Concrete steps), review the
`.ambr` for churn-prone fields, and narrow the captured object if any appear
(none expected — the envelopes are deterministic).

Tests added: `test_machine_envelope_matrix[<command>-<phase>]` (55 cells: 5
commands × 11 phases); new
`tests/__snapshots__/test_command_surface_matrix.ambr`.

Implements: §9 lines 811-813 (machine-mode snapshot pinning); §2.3 lines
125-129; `AGENTS.md` snapshot rules (lines 148-158). Folds in the scaffold so
the first commit is green (Decision A3).

### Work item 2 — human-mode presence matrix

`test_human_mode_presence_matrix`, parametrised over the same cells; drive with
`human=True`. Assert the rendered stdout is non-empty and the drive did not
raise — the §2.3 "human mode asserted for presence" rule (lines 127-129). Do
**not** snapshot human text (presence-only by design). Add one targeted
assertion per command that the human rendering names the command or a
phase-salient token (mirroring `tests/test_novel_done_snapshots.py`'s
human-mode assertion) so "presence" is meaningful, not a bare truthiness check.
The drive must not raise even on the compile exit-3 pre-drafting cells: `run`
renders the error envelope in human mode and exits 3, which `_drive` catches as
a `SystemExit` with a non-empty human body — assert presence, not exit 0.

Tests added: `test_human_mode_presence_matrix[<command>-<phase>]`.

Implements: §2.3 lines 127-129; §9 lines 817-819.

### Work item 3 — semantic assertions for the phase/word-sensitive commands

Assert the phase-keyed branch the design pins, directly (not via snapshot),
across the relevant phases, for the three genuinely phase-sensitive commands:

- `test_done_phase_clause_across_phases`: drive `novel-done` (argv `[]`) across
  all eleven phases; assert `result["phase_is_done"] is True` only when the
  phase is `done` and `False` for the other ten (§4.2 done predicate;
  `phase.py` enum order). Verified value: Surprises table (exactly the `done`
  row carries `phase_is_done=True`). The docstring must state, **accurately**,
  that the envelope `ok`/exit is a constant 1/False across phases because the
  corpus never satisfies the *full* predicate, and must name the real failing
  clause per band so it cannot drift (review B4/B5): the eight pre-drafting
  phases fail on `phase_is_done`, `final_pass_complete`,
  `knitting_gates_passed`, and `compile_consistent` (compiled.md missing) —
  **not** `all_chapters_flagged`, which is **True** on these trees because it
  holds **vacuously** over the empty manifest (`done_predicate.py` line 182,
  "An empty manifest holds vacuously"); the captured pre-drafting `messages`
  are `["phase_is_done is false", "final_pass_complete is false",
  "knitting_gates_passed is false",
  "compile_consistent is false (compiled.md missing)"]`.
  Do **not** attribute the pre-drafting failure to `all_chapters_flagged` —
  that is the B5 defect. `drafting` fails on the unflagged last chapter and the
  absent compile (`all_chapters_flagged` is False **only** here, plus
  `final_pass_complete` and `compile_consistent`); and the **`done` tree's sole
  failing clause is `knitting_gates_passed`** (message
  `"knitting_gates_passed is false"`), while `compile_consistent` is **True** on
  `done`. Do **not** attribute the `done` failure to `compile_consistent` —
  that is the B4 defect. The reason the `done` tree fails
  `knitting_gates_passed` despite its gate booleans all being True is recorded
  in the dedicated Surprise (the `done` spec leaves `knitting_reviews` empty,
  so no `reviews/knitting-NN.md` files exist on disk, and the clause needs both
  the booleans and the files — `done_predicate.py` lines 191-210). The test
  therefore asserts the `phase_is_done` clause, the phase-keyed datum, not the
  aggregate `ok`. To make the rationale impossible to reintroduce silently
  (review's optional Wafflecat alternative, taken in round 4), the test
  additionally asserts the failing-clause set **in code, per band**, so the
  rationale cannot drift in prose:

  - for the `done` cell, `result["knitting_gates_passed"] is False` **and**
    `result["compile_consistent"] is True` and
    `"knitting_gates_passed is false"` is in `messages`;
  - for a representative pre-drafting cell (e.g. `premise` or
    `chapter-planning`), `result["all_chapters_flagged"] is True` **and**
    `result["compile_consistent"] is False` (mirroring the round-4 B5 fix:
    `all_chapters_flagged` passes vacuously on the empty manifest, and the real
    failing clause for the band is `compile_consistent`, not
    `all_chapters_flagged`);
  - for the `drafting` cell, `result["all_chapters_flagged"] is False` (the
    one tree where it genuinely fails — last chapter unflagged).

  These per-band clause assertions pin the failing-clause attribution in code
  rather than only in the docstring, making the B4/B5 error class structurally
  impossible to reintroduce silently.
- `test_check_coherent_across_phases`: drive `novel-state check` (argv
  `["check"]`) across all eleven phases; assert exit 0, `ok is True`, and
  `result["violations"] == []` (§5.2; the corpus phase states are coherent by
  construction). The docstring states this drives the **command envelope**, not
  the oracle, so it is not a duplicate of `tests/test_validate_state_corpus.py`
  (review advisory A2; Risk 3).
- `test_wordcount_branch_across_phases`: drive `wordcount` (argv `[]`) across
  all
  eleven phases; assert the **two verified branches** (§4.5; the gate
  geometry's totality guard at `_wordcount_report._gate_geometry` and
  `validate.py:261`):
  - the eight pre-drafting phases plus `chapter-planning` (empty manifest)
    emit `result["chapters"] == []` and the zero-progress cumulative block
    `{current:0, target:80000, percent_of_target:0.0, gate_triggered_*:false,
    next_gate_threshold:0.3, next_gate_distance:24000}` (B3 fix: the verified
    zero-progress branch, not an assumed one);
  - the three drafting-era phases emit three chapter rows, `current == 68800`,
    all three gate triggers True, and `next_gate_threshold is None`
    (past the final gate; D-NOGATE).

Each assertion cites its design clause inline in the test docstring and pins to
the verified Surprises envelope.

Tests added: `test_done_phase_clause_across_phases`,
`test_check_coherent_across_phases`, `test_wordcount_branch_across_phases`.

Implements: §4.2, §4.5, §5.2; §9 lines 817-819 (semantic branch coverage).

### Work item 4 — branch assertions for the manifest-sensitive commands (B2/B3 fix)

`novel-compile --check` and `desloppify` are **not** eleven-phase-invariant.
Assert their real branches, pinned to the verified Surprises envelopes:

- `test_compile_check_branches_across_phases`: drive `novel-compile` with argv
  `["--check"]` across all eleven phases and assert the three branches (§10
  lines 811-815; `_compile._require_chapter_manifest` and `check_compiled`):
  - the eight pre-drafting phases (empty manifest) → exit 3, `ok is False`,
    `result == {}`, and the message names the empty-manifest refusal;
  - `drafting` (compiled.md absent) → exit 4, `ok is False`,
    `result == {"checked": "working/manuscript/compiled.md", "chapters": 3,
    "diverged": True}`;
  - `final-pass` and `done` (compiled.md present and matching) → exit 0,
    `ok is True`, `result["diverged"] is False`.
  The docstring states this is the **phase-axis** proof (the exit-3/4/0 split
  is keyed on the manifest+compiled state), distinct from
  `tests/test_compile_check_snapshots.py`, which pins the MATCHES/DIVERGES
  envelopes on one hand-built tree (Risk 3).
- `test_desloppify_shape_across_phases`: drive `desloppify` (argv `[]`) across
  all eleven phases and assert: exit 0, `ok is True`, `result` keys are exactly
  `{"pack", "total_words", "violations", "findings"}`, `violations == []`, and
  `len(result["findings"]) == 24` (the full shipped pack on every phase). Then
  assert the one phase-varying datum: `result["total_words"] == 0` for the
  eight empty-manifest pre-drafting phases and `== 68800` for the three
  drafting-era phases (§4.4; §3.3 checker read shape). This is the B3 fix: the
  verified shape-stable-but-value-varying envelope, asserted, not assumed
  phase-invariant.

The eleven-phase exhaustive cross-product collapse for these two commands is
then a documented carried gap (Work item 5), which §9 lines 819-821 sanctions.

Tests added: `test_compile_check_branches_across_phases`,
`test_desloppify_shape_across_phases`.

Implements: §10 lines 811-815, §4.4, §3.3; §9 lines 817-821 (semantic branches
and carried gaps). At the end of this item, record the dry net line count in
Progress and compare against the 600-line tolerance.

### Work item 5 — documented carried-gaps note and developers-guide pointer

- Add a module-level `# Carried gaps:` docstring section enumerating exactly
  what
  the matrix does **not** cover and why: mutator × phase cross-products
  (command/query segregation, §3.3; covered by 6.2.2/6.2.5), the exhaustive
  eleven-phase cross-product for the manifest-sensitive commands
  (`novel-compile --check`, `desloppify` collapse to their manifest branches,
  not eleven independent cells), exhaustive incoherent-variant × phase
  cross-products (covered by the validator suites), and installed-binary
  crossing (6.2.4). This is the literal "documented rather than silently
  omitted" success criterion (`docs/roadmap.md` lines 1290-1292;
  `docs/novel-ralph-harness-design.md` §9 lines 819-821).
- Add a short cross-reference in `docs/developers-guide.md` (near "The five
  commands" or a new "Combinatorial command-surface matrix" subsection) naming
  `tests/test_command_surface_matrix.py` as the home of the
  `command × output-mode × phase` matrix and its carried-gap list. This is the
  only `.md` change, so it triggers `make markdownlint` and `make nixie`. If
  the net line count is trending past the 600-line tolerance (recorded at Work
  item 4), drop the developers-guide subsection in favour of the in-module
  comment and escalate the choice (Tolerances).

Tests added: none (documentation + comment). The carried-gap list is implicit
in the matrix's parametrisation (the excluded surfaces are not parametrised).

Implements: §9 lines 819-821; `AGENTS.md` "Documentation maintenance"
(developers-guide update for internal conventions).

### Stage D — hardening

Re-review the `.ambr` for any field that would churn on a harmless change; tie
each snapshot to a paired semantic assertion; confirm no production file or
corpus file changed (`git status`); confirm the registry uses `["--check"]` for
novel-compile (B1) and that no `[]`-argv copy snapshots the write envelope.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-1`.

Before starting, confirm the branch and a clean tree:

    git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-1 \
      branch --show-current
    git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-2-1 status

Expected: branch `roadmap-6-2-1`, working tree clean apart from this plan.

For each work item, the loop is:

1. Write or extend `tests/test_command_surface_matrix.py`.
2. Generate snapshots when a snapshot test is added or changed:

        uv run pytest tests/test_command_surface_matrix.py --snapshot-update

   Then review `tests/__snapshots__/test_command_surface_matrix.ambr` and
   narrow any churn-prone capture.
3. Run the focused module to confirm green:

        uv run pytest -v tests/test_command_surface_matrix.py

   Expected after Work item 1 onward: all matrix cells pass (no red-scaffold
   commit).
4. Run the full gate suite before committing:

        make check-fmt
        make lint
        make typecheck
        make test
        make audit

   For the Work item 5 documentation change, additionally:

        make markdownlint
        make nixie

   The aggregate gate is `make all` (run it as the final pre-commit check):

        make all

5. Commit the work item with an imperative subject (`commit-message` skill),
   only once every gate passes.

Expected `make test` transcript shape after Work item 1 (abbreviated):

    tests/test_command_surface_matrix.py::test_machine_envelope_matrix[novel-state-premise] PASSED
    tests/test_command_surface_matrix.py::test_machine_envelope_matrix[novel-compile-premise] PASSED
    tests/test_command_surface_matrix.py::test_machine_envelope_matrix[novel-compile-done] PASSED
    …
    ===== N passed in X.XXs =====

## Validation and acceptance

Acceptance is behavioural and reviewer-checkable:

- Run `uv run pytest -v tests/test_command_surface_matrix.py`: every matrix cell
  passes, and the test ids enumerate `command × phase` for both output modes so
  a reviewer can read the covered surface from the test names.
- Demonstrate the matrix catches a real regression: temporarily make
  `novel-done`'s `phase_is_done` clause ignore the phase (a scratch edit, not
  committed) and confirm `test_done_phase_clause_across_phases` fails; revert.
- Demonstrate the B1 guard: temporarily change the compile registry argv to `[]`
  (scratch) and confirm `test_compile_check_branches_across_phases` fails (the
  write envelope has no `diverged` key and mutates the tree); revert.
- Run `make all`: formatting, lint (Ruff + interrogate 100% docstring + Pylint),
  `ty` typecheck, full `pytest`, and `pip-audit` all pass.
- For the documentation change, `make markdownlint` and `make nixie` pass.

Quality criteria (what "done" means):

- Tests: the new matrix module passes; `make test` is green; no per-command
  suite regresses.
- Lint/typecheck: `make lint` and `make typecheck` clean (the new module is a
  `test_*.py`, inheriting the `per-file-ignores`).
- Snapshots: `tests/__snapshots__/test_command_surface_matrix.ambr` carries no
  volatile field; the volatile-field guard passes for every cell.
- Coverage of the surface: all five read commands across the eleven coherent
  phases in both output modes, with the genuinely phase-sensitive branches
  asserted semantically, the manifest-sensitive branches asserted as their real
  exit-3/4/0 (compile) and shape-stable/value-varying (desloppify) cases, and
  the mutator/installed-binary/exhaustive-cross-product gaps documented in the
  module and the developers-guide.

Quality method (how we check): `make all` plus `make markdownlint`/`make nixie`
for the markdown change, run sequentially (build-cache discipline, never in
parallel; `~/.claude/CLAUDE.md` "Commands").

## Idempotence and recovery

- Every step is re-runnable. `--snapshot-update` is idempotent given unchanged
  behaviour; rerun it if a snapshot review prompts a narrower capture.
- If a semantic assertion fails unexpectedly, re-run the ground-truth capture in
  Surprises before re-pinning. If the captured envelope differs from the pinned
  value, the corpus or a command changed: escalate (the corpus is meant to be
  unchanged by phases 2-6), do not silently re-pin.
- If `git status` shows any change under `novel_ralph_skill/` or
  `tests/working_corpus/`, revert it: this task is tests-only.
- No destructive operations. The only generated artefact is the `.ambr`
  snapshot file, safe to delete and regenerate. The compile registry uses
  `["--check"]`, so no test cell writes `compiled.md` into a corpus tree (B1).

## Artifacts and notes

Key reused patterns (cite, do not re-derive):

- Drive + `["--check"]` + snapshot + guard:
  `tests/test_compile_check_snapshots.py` lines 27, 44-53, 13-16;
  `tests/test_novel_done_snapshots.py` lines 47-101.
- Parametrised one-snapshot-per-case:
  `tests/test_contract_envelope_snapshots.py`.
- Phase-state corpus: `tests/corpus_fixtures.py` lines 163-203;
  `tests/working_corpus/_library.py` lines 23-118.
- In-process drive seam: `novel_ralph_skill/contract/runner.py` (`run`,
  `RunContext`).
- The verified per-phase envelope table: `Surprises & discoveries`, second
  observation. Every Work item 3/4 expected value is pinned to it.

## Interfaces and dependencies

- Library versions are locked: `cuprum 0.1.0`, `cyclopts 4.18.0`,
  `pytest-bdd>=8.1.0`, plus `syrupy`, `hypothesis`, `pytest-timeout`,
  `pytest-xdist` (`uv.lock`; `pyproject.toml`). This task adds **no**
  dependency. cuprum is not exercised (in-process drive only; Decision Log).
- New file: `tests/test_command_surface_matrix.py`. It imports each command's
  `build_app` (`novel_ralph_skill.commands.novel_state.build_app`,
  `..._novel_done.build_app`, `..._compile.build_app`,
  `..._desloppify.build_app`, `..._wordcount.build_app`), the drive seam
  `novel_ralph_skill.contract.runner.run` with `RunContext`, and the corpus via
  `import working_corpus as wc`.
- New generated file: `tests/__snapshots__/test_command_surface_matrix.ambr`.
- Edited file: `docs/developers-guide.md` (one cross-reference subsection).
- The module must end with these test functions present (the public contract a
  reviewer reads):

        def test_machine_envelope_matrix(…): …
        def test_human_mode_presence_matrix(…): …
        def test_done_phase_clause_across_phases(…): …
        def test_check_coherent_across_phases(…): …
        def test_wordcount_branch_across_phases(…): …
        def test_compile_check_branches_across_phases(…): …
        def test_desloppify_shape_across_phases(…): …

## Documentation and skills signposting

Docs to read before implementing (source of truth):

- `docs/novel-ralph-harness-design.md` §2.3 (the `command × output-mode × phase`
  surface), §3.1 (output modes and envelope), §3.3 (command/query segregation),
  §4.2 (done predicate / `phase_is_done`), §4.4 (desloppify report shape), §4.5
  (word reporting and gate derivation), §5.1 (phase enum), §5.2 (invariants),
  §9 (verification strategy and carried gaps), §10 (the empty-manifest exit-3
  refusal that drives the compile branches).
- ADRs: `docs/adr-003-shared-interface-contract.md` (the envelope and
  output-mode contract), `docs/adr-005-command-surface-five-scripts.md` (the
  five-command surface), `docs/adr-001-deterministic-judgemental-boundary.md`
  (why the spine is deterministically testable).
- `docs/developers-guide.md`: "Shared test scaffolding", "The `working/` fixture
  corpus", "The five commands", "The shared JSON envelope".
- `docs/scripting-standards.md`: Cyclopts, cuprum, pathlib, and testing
  conventions (read for the cmd-mox boundary note, even though this in-process
  task mocks nothing).
- `AGENTS.md`: "Python verification and testing" (snapshot discipline, test-tree
  placement, e2e/property rules), "Change quality and committing", "Markdown
  guidance".

Skills to load per work item:

- All items: `python-router` → then `python-testing` (fixtures, parametrisation,
  marks, snapshot/syrupy discipline) as the primary follow-on.
- Work item 1-2 (snapshots): `python-testing` "snapshot and approval tests"
  guidance; the syrupy update flow.
- Work items 3-4 (semantic branches): `python-router`. Property testing
  (`hypothesis`/`crosshair`) is **not** required: the surface is a closed
  eleven-member phase set already exhausted by parametrisation, and the design
  pins snapshot + semantic assertions for these aggregations (§9), so a
  property suite would be over-engineering for a bounded enum. No `mutmut`
  either: this is a test-adding task, not a coverage-hardening task.
- Documentation (Work item 5): `en-gb-oxendict` for spelling; `commit-message`
  for each commit.
- Navigation throughout: `leta` (show/refs/grep) and `sem` for history, per the
  standing rules.

## Revision note

Round-5 revision (2026-06-25). Resolves the dual-review blocking finding raised
after the task landed (`roadmap-6-2-1` fix round 1):

- **Roadmap checkbox**: `docs/roadmap.md` task 6.2.1 was ticked from `- [ ]` to
  `- [x]`. The completing commit (`a64bc24`) set this ExecPlan to COMPLETE but
  left the roadmap box open, so the workflow's source of truth still showed the
  task as selectable. The repo convention — verified against siblings 6.1.1
  (`e0c6cf5`) and 6.2.3 (`c92aeef`), each ticked in its own completing commit —
  is that the implementer flips the box when the task lands.
- **Markdown gate hygiene**: `make markdownlint` was red on this branch because
  the round-2/3/4 review sidecars and this ExecPlan carried over-long inline
  JSON literals (MD013) and a hyphen-led prose line parsed as a list (MD032).
  The long literals were wrapped across lines (keeping the established
  wrapped-inline-code-span style in the ExecPlan, fenced `text`/`json` blocks in
  the review sidecars where that file's first code block already sets a fenced
  convention) and the stray list line was reflowed. No semantic content changed;
  every captured value is byte-for-byte the same as before, only re-wrapped.

Round-4 revision (2026-06-25). Resolves the single residual blocking defect
(B5) in `roadmap-6-2-1.review-r3.md`, a B4-class error in the *pre-drafting*
band:

- **B5 (pre-drafting failing-clause attribution)**: the Surprises `novel-done`
  row and the Work item 3 docstring guidance previously named
  `all_chapters_flagged` as a pre-drafting failing clause. Re-verified in
  source: `all_chapters_flagged` (`novel_ralph_skill/state/done_predicate.py`
  line 182, "An empty manifest holds vacuously") is **True** on every
  empty-manifest pre-drafting tree, because
  `all(... for chapter in state.chapters)` over `chapters == ()` is vacuously
  `True`. The verified pre-drafting failing clauses are `phase_is_done`,
  `final_pass_complete`, `knitting_gates_passed`, and `compile_consistent`
  (compiled.md missing), with captured `messages`
  `["phase_is_done is false", "final_pass_complete is false",
  "knitting_gates_passed is false",
  "compile_consistent is false (compiled.md missing)"]`.
  Surprises and Work item 3 now state this; the correct `drafting`-band
  attribution (`all_chapters_flagged` False **only** there) is preserved.
- **B5/A1 (pin the rationale in code, per band)**: taking the round-3 review's
  Wafflecat alternative, `test_done_phase_clause_across_phases` now asserts the
  failing-clause set **in code** for one representative cell per band: the
  pre-drafting cell asserts `result["all_chapters_flagged"] is True` and
  `result["compile_consistent"] is False`; the `drafting` cell asserts
  `result["all_chapters_flagged"] is False`; the `done` cell asserts
  `result["knitting_gates_passed"] is False`,
  `result["compile_consistent"] is True`, and the
  `"knitting_gates_passed is false"` message. A docstring can no longer
  mis-describe a clause set the test itself pins, making the entire B4/B5 error
  class structurally impossible to reintroduce silently.

Round-3 revision (2026-06-25). Resolves the residual blocking defect (B4) and
the chdir/capture advisories in `roadmap-6-2-1.review-r2.md`:

- **B4 (failing-clause attribution)**: the Surprises `novel-done` row and the
  Work item 3 docstring guidance previously implied the `done` tree fails on
  `compile_consistent`. Re-captured in-process, the `done` tree's result is
  `{"phase_is_done": true, "final_pass_complete": true,
  "all_chapters_flagged": true, "knitting_gates_passed": false,
  "compile_consistent": true, "no_unresolved_blockers": true}`
  with `messages == ["knitting_gates_passed is false"]`. The plan now states
  the verified sole failing clause on `done` is **`knitting_gates_passed`**
  (with `compile_consistent` True), and Work item 3 additionally asserts
  `result["knitting_gates_passed"] is False`,
  `result["compile_consistent"] is True`, and the
  `"knitting_gates_passed is false"` message for the `done` cell, so the
  attribution is enforced in code, not only a docstring.
- **B4 (latent corpus surprise)**: a dedicated Surprise now records that the
  `_library.py` `done` spec sets `done_30/50/80=True` (via `_crossed_gates`) yet
  `knitting_gates_passed` is False on disk, because that clause
  (`done_predicate.py` lines 191-210) requires the three
  `reviews/knitting-NN.md` files too, and the `done` spec leaves
  `knitting_reviews=()` so the builder writes no `reviews/` directory
  (`_builder.py` line 196). It is adjudicated as an **intended carried
  property** ("phase=done but predicate-incomplete"): the
  full-predicate-satisfying tree lives in
  `tests/working_corpus/_done_predicate_specs.py` (`DONE_PREDICATE_ALL_HOLD`/
  `ALL_KNITTING_REVIEWS`), owned by the done-predicate suites, not this phase
  matrix.
- **A1/A2 (drive helper)**: the `_drive` helper is now modelled on
  `test_novel_done_snapshots.py::_run_capture`, changing directory with
  `monkeypatch.chdir` (auto-reverted, xdist-safe — not a bare `os.chdir`) and
  capturing stdout via the `capsys` fixture, with the cited model corrected
  (the compile suite chdirs in its test bodies, not in `_drive_check`). The
  Context orientation and Interfaces sections are aligned.

Round-2 revision (2026-06-25). Resolves the three blocking defects in
`roadmap-6-2-1.review-r1.md`:

- **B1**: the `novel-compile` read-surface registry argv is now `["--check"]`
  (was `[]`, which ran the write/mutator path and captured the write envelope).
  Aligned across the registry, Decision Log, Surprises, Validation, and the
  Idempotence note.
- **B2**: `novel-compile --check` is no longer asserted "phase-invariant". Work
  item 4 now asserts the three verified branches across the phase axis: exit 3
  (eight pre-drafting empty-manifest phases), exit 4 (drafting, compiled
  absent), exit 0 (final-pass/done, matches), pinned to §10 /
  `_require_chapter_manifest` and the verified Surprises envelope.
- **B3**: `desloppify` and `wordcount` over the empty pre-drafting manifest are
  now *verified*, not assumed. The exact zero-chapter envelopes were captured
  in-process and pinned: `wordcount` emits the zero-progress branch
  (`chapters==[]`, `next_gate_threshold==0.3`, `next_gate_distance==24000`);
  `desloppify` is shape-stable (24-rule pack, empty violations) but
  value-varying (`total_words` 0 vs 68800). No cell is left to the Ambiguity
  tolerance.

Also corrected: the round-1 Constraint forbidding a runtime
`import working_corpus` (wrong against the repo convention — every corpus test
imports `working_corpus as wc`); the round-1 red-scaffold placeholder (folded
into Work item 1 so the first commit is green — advisory A3);
slug-normalisation note added (advisory A1); the `novel-state check` cell's
distinction from the oracle suite made explicit (advisory A2); and the verified
fact that `novel-done` is exit 1/`ok=False` for all eleven phases (so Work item
3 asserts the `phase_is_done` clause, not the aggregate `ok`). The work plan is
now five green-committable items split by phase-sensitivity, with every
expected value pinned to the verified envelope table in Surprises.
