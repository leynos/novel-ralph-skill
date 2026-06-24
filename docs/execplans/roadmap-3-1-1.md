# Implement the per-clause `novel-done` predicate and its structured result

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (all five work items delivered 2026-06-24)

## Purpose / big picture

Today there is no `novel-done` command: its console-script entry point is still
the "not yet implemented" stub that exits `2`
(`novel_ralph_skill/commands/stub.py:93-95`). The harness cannot ask "is the
novel done?" deterministically, so the done predicate lives only as pseudocode
in `skill/novel-ralph/references/done-conditions.md` and as the ad-hoc shell
the field report blames. This task delivers the read-only `novel-done` checker
as code: it evaluates each done clause against disk, reports which clauses hold
in a structured per-clause `result`, and returns a meaningful exit code, so
"check done every turn" is one call (design
`docs/novel-ralph-harness-design.md` §4.2).

This is roadmap task 3.1.1 (`docs/roadmap.md` §3.1, lines 852-859). The split
between 3.1.1 and 3.1.2 is deliberate **and the boundary moved during review**:

- **3.1.1 (this task)** delivers the predicate engine, the structured result,
  the entry-point wiring, the corpus fixtures the six-clause matrix needs, and a
  **sound existence-only** `compile_consistent` clause: `compiled.md` must
  exist, or the clause is false. This closes the dangerous exit-0 lie the
  reviewer identified (B1): a novel whose `compiled.md` is *absent* can never be
  declared "done" by 3.1.1. See Decision Log D-COMPILE-EXISTENCE.
- **3.1.2** swaps the existence-only half for the full shared compile-and-hash
  routine (catching a *present-but-stale* `compiled.md`) and adds the
  exit-`4`-versus-exit-`1` carve-out (`docs/roadmap.md:860-878`; design §4.2
  lines 309-316). 3.1.1 produces no exit `4`.

The residual unsoundness 3.1.1 ships is therefore narrow and named: a tree whose
`compiled.md` *exists but is stale* (diverges from the drafts) can still pass
`compile_consistent` and, if every other clause holds, exit `0`. This is the
documented unsoundness window closed by 3.1.2 (Risk R-STALE; users'/developers'
guides record it). It is strictly smaller than the round-1 plan, which let an
*absent* compile pass too.

After this change a user can run, from a project's process directory:

```console
$ novel-done
{"command": "novel-done", "schema_version": 1, "ok": false,
 "working_dir": "working",
 "result": {"phase_is_done": false, "final_pass_complete": false,
            "all_chapters_flagged": false, "knitting_gates_passed": false,
            "compile_consistent": false, "no_unresolved_blockers": true},
 "messages": ["phase_is_done is false"]}
```

(the stdout is a single physical line; it is wrapped here only to fit the
margin). Observe a single JSON object whose `result` reports each clause as a
boolean, exit code `1` (the benign "not yet done" the harness loops on) while
any clause is false, and exit code `0` only when every clause holds. A missing
or unparseable `working/state.toml`, or an unreadable chapter artefact, exits
`3` (the state-error channel), never the benign `1`.

You can see it working through the new behavioural scenario
`tests/features/novel_done.feature` (each clause driven independently true and
false over the §1.3.2 corpus, the predicate exiting `0` only when all hold) and
the machine-mode envelope snapshot, both described under "Validation and
acceptance".

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **The deterministic-and-judgemental boundary is absolute (ADR-001; design
  §1).** `novel-done` is a *checker*: it detects and reports; it makes no
  narrative judgement and writes nothing to disk on any path (design §3.3 puts
  `novel-done` in the read-only checker column). It mutates no `state.toml`,
  touches no `done.flag`, and creates no file. Any temptation to "fix up" a
  stale tree from within `novel-done` is out of scope and belongs to
  `novel-state reconcile`.

- **The clause semantics are the §4.2 / `done-conditions.md` predicate, read on
  disk (design §2.3 "predicate truthfulness").** The six clause names are fixed
  by design §4.2's JSON (lines 320-334): `phase_is_done`, `final_pass_complete`,
  `all_chapters_flagged`, `knitting_gates_passed`, `compile_consistent`,
  `no_unresolved_blockers`. Their truth conditions are the `novel_predicate`
  body in `skill/novel-ralph/references/done-conditions.md:150-185` ("Novel-level
  predicate"), adapted to read the **manifest** chapter set rather than the
  reference's outline parse (D-CLAUSES, divergence note). The design states the
  predicate "holds **on disk**" (§2.3 line 115), so clauses that name on-disk
  artefacts (`done.flag`, `reviews/knitting-NN.md`, `critic-notes.md`,
  `compiled.md`) read those artefacts, not a state mirror of them.

- **The shared contract is fixed (ADR-003; design §3.1, §3.2).** The command
  emits the common envelope through the shared
  `novel_ralph_skill.contract.runner.run` wrapper. `result` carries the
  machine-actionable per-clause booleans; `messages` is human prose the harness
  never parses. The envelope `schema_version` is the contract's, currently `1`,
  stamped by `build_envelope`. `ok` is the exit-code biconditional
  `contract.exit_codes.is_ok` — `True` iff the exit is `0` — so a not-yet-done
  predicate (exit `1`) carries `ok: false`.

- **The exit-code table is fixed (ADR-003; design §3.2).** In 3.1.1: exit `0`
  when every clause holds; exit `1` (benign negative) when any clause is false;
  exit `2` for a usage error (handled by the runner's `CycloptsError` arm); exit
  `3` for a state/input error (missing/unparseable `state.toml`, unreadable
  chapter artefact). Exit `4` is **not** produced by 3.1.1 — the
  compile-divergence carve-out that yields exit `4` is roadmap task 3.1.2
  (design §4.2 lines 309-316). The `compile_consistent` clause in 3.1.1 reports
  existence only (D-COMPILE-EXISTENCE) and never drives exit `4`.

- **No external process; cuprum is out of scope.** `novel-done` shells out to
  nothing (design §4 line 269: "cuprum is required only where a command shells
  out (none do in v1)"). Filesystem work uses `pathlib`. Confirmed against the
  locked cuprum source: `cuprum.catalogue.ProgramCatalogue` /
  `cuprum.program.Program` (`/data/leynos/Projects/cuprum/cuprum/catalogue.py`,
  `cuprum/program.py`) exist to run allow-listed external programs, none of
  which this command invokes, so no cuprum API is load-bearing here. Do not add
  cuprum to the runtime dependencies (they remain `cyclopts` and `tomlkit`,
  `pyproject.toml:8`).

- **The compile join rule is the single shared rule.** The existence-only clause
  in 3.1.1 needs no concatenation, but the developers' guide note (Work item 5)
  must point at `novel_ralph_skill.state.compile_model.concatenate_drafts`
  (`compile_model.py:33`) — already the production twin of the corpus helper and
  already called by the `compiled-matches-drafts` disk-evidence detector
  (`disk_evidence.py:179-196`) — as the routine 3.1.2 will reuse for the hash
  half. Do not invent a second join or hash rule.

- **The word-count / token rule is the single shared rule.** Where a clause
  needs a draft's token count, it uses `len(text.split())` over the UTF-8
  body — the one rule
  `novel_ralph_skill.state.wordcount._chapter_word_count` owns. 3.1.1's clauses
  do not count words (existence checks only), but if any helper does, it reuses
  that rule. Do not invent a second counter.

- **Reuse the established command shape; do not renegotiate the contract.** The
  entry point follows the `desloppify` pattern exactly
  (`novel_ralph_skill/commands/stub.py:103-123`): pre-parse `--human` with
  `parse_global_flags`, build a single-`@app.default` Cyclopts app configured
  `result_action="return_value", exit_on_error=False, print_error=False,
  help_on_error=False` (`_desloppify.py:290-312`), and drive it through `run`.
  `novel-done` takes no positional or keyword arguments.

- **Style and quality gates (AGENTS.md).** No module exceeds 400 lines.
  Comments and prose use en-GB Oxford spelling (`-ize`/`-yse`/`-our`). Every
  public function carries a docstring with an example where it aids a caller
  (the `interrogate` gate enforces presence). All work passes `make all`.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- **Scope.** If the implementation requires changing more than 14 files or more
  than 800 net lines of code, stop and escalate. (The cap rose from round 1's
  12/700 to absorb the explicit all-hold corpus spec and its tests, B2.)
- **Interface.** If delivering 3.1.1 requires changing the signature of any
  shared seam already in use — `contract.runner.run`, `RunContext`,
  `CommandOutcome`, `build_envelope`, `ExitCode`, `is_ok`,
  `novel_state._load_or_state_error`, `wordcount.recount_words`,
  `compile_model.concatenate_drafts`, the existing `PHASE_STATES` /
  `COHERENT_BASELINE` library specs — stop and escalate. New helpers and new
  named specs beside them are fine; changing the in-use ones is not.
- **Dependencies.** If any new runtime or dev dependency appears necessary, stop
  and escalate (the runtime set is fixed at `cyclopts` + `tomlkit`; the dev set
  already carries `pytest`, `pytest-bdd`, `hypothesis`, `syrupy`,
  `pytest-timeout`, `pytest-xdist`).
- **Clause semantics.** If a clause cannot be evaluated deterministically from
  disk without an undecided design fork — for example, if the format of an
  unresolved BLOCKER in `critic-notes.md` cannot be pinned to the reference
  without a judgement call — stop and present the options with trade-offs rather
  than guessing.
- **Iterations.** If `make all` still fails after 3 fix attempts on a single
  work item, stop and escalate.

## Risks

Known uncertainties, with mitigations.

- Risk (R-STALE): the existence-only `compile_consistent` clause leaves a known
  unsoundness window — a *present but stale* `compiled.md` passes
  `compile_consistent` in 3.1.1, so an otherwise-complete tree exits `0`
  ("done") with a stale compile until 3.1.2 lands. Severity: medium (this is the
  exact "compiled.md is stale" failure mode `done-conditions.md:214` names).
  Likelihood: low for the *absent* case (now closed; B1), real but bounded for
  the *stale* case. Mitigation: (i) the clause is sound for absence — an absent
  compile is always exit `1`, never `0`; (ii) the window is documented in the
  users' guide ("v1 caveat") and developers' guide as the 3.1.2 deferral; (iii)
  the existence-only function is a single named helper a one-edit swap replaces
  (D-COMPILE-EXISTENCE), and a test pins both that it is false when `compiled.md`
  is absent and true when present (stale or not), so 3.1.2's behaviour change is
  localised and visible.

- Risk (R-ALLHOLD): no §1.3.2 corpus tree satisfies all six clauses, so the
  roadmap 3.1.1 success criterion ("exit 0 only when every clause holds") cannot
  be demonstrated without new fixture data — the existing `PHASE_STATES["done"]`
  spec lacks `reviews/knitting-NN.md` (so `knitting_gates_passed` cannot hold)
  and has no modelled `critic-notes.md`. Severity: high. Likelihood: certain
  (verified — `_library.py:79-97` builds no reviews; `_specs.py` models neither
  artefact). Mitigation: Work item 2 adds an explicit, **separate**
  all-six-clauses-hold named spec (and per-clause-isolating specs) without
  mutating the existing `PHASE_STATES`/`COHERENT_BASELINE` specs (D-CORPUS).

- Risk (R-CHURN): adding the two new artefacts to the corpus could re-baseline
  an existing snapshot or oracle suite. Severity: medium. Likelihood: low
  (verified). The disk-evidence detector reads only `manuscript/`, `compiled.md`,
  and `log.md` — never `reviews/` or `critic-notes.md`
  (`disk_evidence.py:109-266`; the `_disk_word_counts` cluster likewise) — so its
  verdicts (and `test_novel_state_check_disk.ambr`) are unaffected by the two new
  artefacts. The only `rglob("*")`-based assertions
  (`test_novel_state_check_disk.py:131-138`) run over the `done-flag-*` incoherent
  variants, not `PHASE_STATES["done"]`. Mitigation: Work item 2 adds *new* named
  specs rather than mutating the in-use ones, so every existing spec stays
  byte-identical and no snapshot re-baselines; a test asserts the new specs add
  exactly `reviews/` and `critic-notes.md` and nothing else (D-CORPUS).

- Risk (R-CLAUSE-SOURCE): reading per-manifest chapter rather than the
  reference's per-outline parse could be read as an unacknowledged departure
  from `done-conditions.md`. Severity: low (the manifest is the
  design-conformant source). Likelihood: medium. Mitigation: D-CLAUSES records
  the deliberate divergence and its design §4.3 (lines 357-369) justification —
  the manifest is the authoritative chapter set/order, there is no
  `parse_chapter_outline` in the codebase, and `novel-state check` already
  asserts the manifest⇄directory bijection — so a future reconciliation of
  `done-conditions.md` is traceable (B3).

- Risk (R-FAULT): a per-clause read fault is swallowed as a false clause and
  misreported as exit `1` instead of exit `3`. Severity: medium. Likelihood:
  medium. Mitigation: mirror the `wordcount`/`disk_evidence` fault boundary
  exactly — only an absent artefact is benign; every other read fault
  (`PermissionError`, `UnicodeDecodeError`) is re-raised as `StateInputError`
  for the exit-`3` channel (D-FAULT). A negative test pins an undecodable
  `critic-notes.md` to exit `3`.

- Risk (R-SNAPSHOT): snapshot churn from a broad result dump. Severity: low.
  Likelihood: low. Mitigation: snapshot only the machine-mode envelope for two
  pinned trees (all-clauses-hold, one-clause-fails) and pair with semantic
  per-clause assertions, per the AGENTS.md snapshot rule.

## Progress

- [x] Work item 1: the pure per-clause predicate engine and its result shape
  (no command wiring), including the existence-only `compile_consistent` clause.
  Completed 2026-06-24. Delivered `novel_ralph_skill/state/done_predicate.py`
  (`DoneClauses` with `all_hold`/`failed_clause_names`/`as_result`, one pure
  function per clause, `evaluate_done` aggregator) and
  `tests/test_done_predicate.py` (per-clause true/false, R-STALE existence pin,
  undecodable-`critic-notes.md` propagation, the conjunction/ordering property).
  `make all` green; coderabbit `--agent` reported 0 findings.
- [x] Work item 2: extend the corpus to model `reviews/knitting-NN.md` and
  `critic-notes.md`; add the all-six-clauses-hold spec and the clause-isolating
  specs; pin the BLOCKER format. Completed 2026-06-24. Added
  `ChapterSpec.critic_notes` and `WorkingTreeSpec.knitting_reviews` (both
  default-off), taught `_builder.py` to write the two artefacts, and added
  `_done_predicate_specs.py` (all-hold spec, seven per-clause failers including
  the two `knitting_gates_passed` halves, the `[resolved]`/near-miss BLOCKER
  trees) and `_done_predicate_oracle.py` (the D-TWIN review-existence and
  BLOCKER-scan twins). New `corpus_done_predicate_fixtures.py` plugin and
  `tests/test_working_corpus_done_predicate.py` pin the builder output, the
  one-clause-per-failer guarantee, the BLOCKER edges, twin agreement, and the
  R-CHURN byte-identity of the existing specs. Decision: the new specs live in
  their own modules (not `_library.py`) to keep every file under the 400-line
  cap and leave `PHASE_STATES`/`COHERENT_BASELINE` untouched (D-CORPUS). `make
  all` green; coderabbit `--agent` 0 findings.
- [x] Work item 3: wire the `novel-done` command body, app, and entry point;
  retire the stub. Completed 2026-06-24. Added
  `novel_ralph_skill/commands/_novel_done.py` (`_novel_done` body resolving
  `working_dir`/`state_path`, loading via `_load_or_state_error`, wrapping
  `evaluate_done` under `STATE_INPUT_ERRORS` for the D-FAULT exit-3 mapping, and
  the four-flag `build_app`), rewired `stub.py` `novel_done()` to mirror
  `desloppify()`. Moved `novel-done` into `_REAL_COMMANDS` in
  `test_console_scripts_e2e.py` and `test_command_stubs.py` (it now resolves
  `working/` and exits per the predicate, not the stub's 2).
  `tests/test_novel_done_command.py` pins exit 0 on all-hold, 1 on each failer
  (including absent-`compiled.md` -> benign 1, never 4), 3 on missing state and
  undecodable `critic-notes.md`, and 2 on a stray positional. `make all` green;
  coderabbit `--agent` 0 findings.
- [x] Work item 4: the six-clause behavioural, property, and snapshot suites
  and the build-and-install e2e proof. Completed 2026-06-24. Added
  `tests/features/novel_done.feature` + `tests/steps/novel_done_steps.py` +
  `tests/test_novel_done_bdd.py` (the all-hold "exits 0" named scenario plus a
  Scenario Outline driving each failer to exit 1),
  `tests/test_novel_done_snapshots.py` (two machine-mode envelope snapshots
  paired with per-clause assertions, plus the `--human` presence test), and
  `tests/test_novel_done_e2e.py` (installed-wheel POSIX e2e: all-hold -> exit 0,
  absent-`compiled.md` -> exit 1). `make all` green (672 then 670 passed);
  coderabbit `--agent` pending (rate-limited; see below).
- [x] Work item 5: documentation (users' guide v1 caveat, developers' guide
  done-predicate subsection, design cross-reference) and the contents map.
  Completed 2026-06-24. Added the `novel-done` user-guide section with the
  six-clause result, the `0`/`1`/`3` exit codes, and the R-STALE v1 caveat;
  retired the "still a stub" line. Added the developers' guide "Done predicate
  (`novel-done`)" subsection (D-CLAUSES manifest divergence, D-BLOCKER format,
  the existence-only `compile_consistent` and its 3.1.2 owner, the D-FAULT
  boundary, the D-TWIN oracle discipline). Added the design §4.2
  implementation-status note. `contents.md` already indexes execplans by the
  `roadmap-<step>-<task>.md` directory pattern, so no per-file edit was needed.
  `make all`, `make markdownlint` green; `make nixie` not required (no Mermaid
  touched).

Each work item is independently committable and must pass `make all` before its
commit. Update this section with a timestamp at every stopping point.

## Surprises & discoveries

- Observation: `corpus_fixtures.py` was already at the 400-line cap, so the
  `novel-done` corpus fixtures could not be added there. Evidence: the existing
  `corpus_live_draft_fixtures.py` / `corpus_divergent_fixtures.py` split. Impact:
  added a fourth plugin `corpus_done_predicate_fixtures.py`, registered in
  `conftest.py`'s `pytest_plugins`, following the established pattern.
- Observation: `_RESOLVED_TOKEN = "[resolved]"` trips Ruff S105
  (hardcoded-password) and the property docstrings trip the
  property-docstring-starts-with-verb rule. Evidence: the `Phase.FINAL_PASS`
  member carries the same S105 suppression. Impact: a targeted `# noqa: S105`
  with a why-comment and noun-phrase property docstrings.
- Observation: coderabbit rate-limited the Work item 4 review. Evidence: the
  `rate_limit` event with a ~4m wait. Impact: applied the exponential-backoff
  retry the task prescribes; recorded the outcome in the Outcomes section.

## Decision log

- Decision (D-CLAUSES): pin each clause's exact truth condition, with the
  manifest-source divergence from the reference made explicit. Rationale: design
  §2.3 (line 115) says the predicate "holds on disk"; the authoritative clause
  semantics are `skill/novel-ralph/references/done-conditions.md:150-185`
  ("Novel-level predicate"). The mapping is:
  - `phase_is_done` := `state.phase.current == Phase.DONE`;
  - `final_pass_complete` := `state.gates.final.final_pass_complete`;
  - `all_chapters_flagged` := every **manifest** chapter
    (`state.chapters`, each `.number`) has an on-disk
    `working/manuscript/chapter-NN/done.flag`;
  - `knitting_gates_passed` := `state.gates.knitting.done_30/done_50/done_80`
    all `True` **and** `working/reviews/knitting-{30,50,80}.md` all exist;
  - `no_unresolved_blockers` := no **manifest** chapter's
    `working/manuscript/chapter-NN/critic-notes.md` contains an unresolved
    BLOCKER (D-BLOCKER);
  - `compile_consistent` := `working/manuscript/compiled.md` **exists**
    (existence-only; D-COMPILE-EXISTENCE).

  **Deliberate divergence from the reference (B3):** the reference
  `novel_predicate` derives planned chapters from
  `parse_chapter_outline(working_dir / "plan/chapter-outline.md")` and iterates
  `reviews/` and `critic-notes.md` per *outline* chapter
  (`done-conditions.md:158, 180`). This plan reads per **manifest** chapter
  (`State.chapters`) instead, because design §4.3 (lines 357-369) pins the
  chapter set and order to the `state.toml` manifest, not to outline prose; the
  codebase has no `parse_chapter_outline`; and `novel-state check` already
  asserts the manifest⇄on-disk-directory bijection (design §5.2;
  `disk_evidence.py:109-130`), so the manifest is the authoritative,
  already-validated chapter set. This is a design-conformant substitution, not a
  transcription error; `done-conditions.md` should be reconciled to the manifest
  source in a later docs pass and this divergence is recorded so that pass is
  traceable. Date/Author: 2026-06-24, planning agent (revised round 2).

- Decision (D-COMPILE-EXISTENCE): `compile_consistent` in 3.1.1 is the **sound
  existence half** of the real clause — `working/manuscript/compiled.md` exists
  → `True`; absent → `False`. Rationale: the round-1 hardcoded `True` made the
  exit-0 path unsound, declaring a novel "done" even when `compiled.md` was
  *absent* (review B1). The cheap, sound half of design §4.2's clause is the
  existence test; deferring only the hash comparison and the exit-`4` carve-out
  to 3.1.2 (roadmap 3.1.2; design §4.2 lines 337-343) keeps the exit-0 path sound
  for the absent case from day one. The clause is a single named function
  `compile_consistent_exists(working_dir) -> bool` whose docstring names task
  3.1.2 as the owner of the hash half, so 3.1.2's swap is a localised edit. The
  residual stale-but-present window is Risk R-STALE, documented in the
  users'/developers' guides. (This is the reviewer's preferred B1 option (b) and
  the Wafflecat-recommended split.) Date/Author: 2026-06-24, planning agent
  (revised round 2).

- Decision (D-CORPUS): model the two new artefacts and the all-hold case as
  **new** named specs, leaving every existing spec byte-identical. Rationale:
  the roadmap 3.1.1 success criterion needs a tree where all six clauses hold,
  but mutating the in-use `PHASE_STATES`/`COHERENT_BASELINE` specs to gain the
  three review files would risk churning the suites that consume them (review
  B2, R-CHURN). Verified: the disk-evidence detector ignores `reviews/` and
  `critic-notes.md` (`disk_evidence.py` reads only `manuscript/`, `compiled.md`,
  `log.md`), so its verdicts and `test_novel_state_check_disk.ambr` are
  unaffected *by the artefacts themselves*; but to avoid any coupling the new
  specs are added beside the existing ones (a new `DONE_PREDICATE_STATES`
  mapping or equivalently named specs in the library), and `_drafting_spec` /
  `PHASE_STATES` are not altered. The blanket round-1 "every existing corpus spec
  stays byte-identical, no churn" claim was *true only because* no existing spec
  is mutated — this decision makes that mechanism explicit and a test asserts the
  new specs introduce exactly `reviews/knitting-NN.md` and `critic-notes.md`.
  The all-hold spec is: `phase=done`, `final_pass_complete=True`, all flags, all
  three gate booleans, all three `knitting-NN.md` present, clean/absent
  `critic-notes.md`, and a present `compiled.md` (`COMPILED_AUTO`). Date/Author:
  2026-06-24, planning agent (revised round 2).

- Decision (D-BLOCKER): pin the unresolved-BLOCKER detection format. Rationale:
  `done-conditions.md:182` names "unresolved BLOCKER findings" in
  `critic-notes.md` but pins no exact syntax. To keep the clause deterministic,
  3.1.1 defines: a `critic-notes.md` line whose stripped text starts with
  `BLOCKER` (case-sensitive, the reference's spelling) and is **not** marked
  resolved (the line does not contain the literal substring `[resolved]`) is an
  unresolved blocker. An absent `critic-notes.md` means no blockers (the
  reference treats a missing notes file as clean:
  `if notes.exists() and contains_unresolved_blocker`, `done-conditions.md:181`).
  The substring rule is acknowledged brittle (a prose mention of `[resolved]`, or
  `RESOLVED`/`(resolved)`, would mis-classify); the corpus pins this edge with a
  near-miss spec (a BLOCKER whose body merely mentions resolution; advisory A5).
  This format is recorded in the developers' guide and modelled by the corpus so
  production and corpus cannot drift; if review rejects this format, escalate
  rather than widen it silently. Date/Author: 2026-06-24, planning agent.

- Decision (D-FAULT): the per-clause fault boundary mirrors `wordcount` /
  `disk_evidence`. Rationale: an absent on-disk artefact (no `done.flag`, no
  review, no `critic-notes.md`, no `compiled.md`) is a benign "clause not
  satisfied"; every other read fault (`PermissionError`, `IsADirectoryError`,
  `UnicodeDecodeError`) is a corrupt tree and must reach exit `3`, not be
  swallowed as a false clause and misreported as exit `1`. The predicate engine
  lets such faults propagate; the command body wraps them under
  `novel_state.STATE_INPUT_ERRORS` and re-raises `StateInputError`, exactly as
  `_load_or_state_error` does (`novel_state.py:125-153`). A negative test pins an
  undecodable `critic-notes.md` to exit `3`. Date/Author: 2026-06-24, planning
  agent.

- Decision (D-TWIN): the two new disk-reading clauses get oracle twins up front,
  not "if warranted". Rationale: the developers' guide treats disk-evidence reads
  as deliberate twins with an independent oracle (`tests/working_corpus/_oracle.py`;
  `disk_evidence.py:26-34`). `knitting_gates_passed`'s review-existence read and
  `no_unresolved_blockers`'s BLOCKER scan are disk-evidence reads of the same
  shape, so Work item 2 adds a corpus-side reader for each and pins it equal to
  the production predicate by a cross-check test, mirroring how `disk_evidence`
  twins the oracle (review A4). If building the twins balloons the work item past
  the scope tolerance, escalate. Date/Author: 2026-06-24, planning agent
  (revised round 2).

- Decision (D-LOC): module placement. Rationale: the pure predicate engine
  lives in a new `novel_ralph_skill/state/done_predicate.py` beside the schema
  and the `disk_evidence` detector it parallels (both are pure
  `State` + `working_dir` -> structured verdict readers). It reuses
  `_chapter_dir_name` from `novel_ralph_skill/state/_disk_paths.py` (where it is
  defined — `disk_evidence.py` only *imports* it; advisory A1), not from
  `disk_evidence`. The command body and its app/entry wiring live in a new
  `novel_ralph_skill/commands/_novel_done.py` mirroring `_desloppify.py`'s
  placement, with the `stub.py` `novel_done()` entry point rewired to drive it.
  Keeping the pure engine out of the command module keeps each under the 400-line
  cap and lets the property tests exercise the engine without the Cyclopts shell.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-EXTERNAL): no firecrawl-sourced library behaviour is
  load-bearing. Rationale: `novel-done` reuses the cyclopts 4.18.0 (`uv.lock:137,
  146`) + runner + envelope path already shipped and gated by `novel-state` and
  `desloppify`. The `--help`/`--version` non-`CommandOutcome` handling, the
  `result_action="return_value"` seam, and the single-`@app.default` body are
  all already pinned by `tests/test_contract_runner.py` and
  `tests/test_cyclopts_contract.py`. The cyclopts **v4** API docs
  (`cyclopts.readthedocs.io/en/v4.4.1/api.html`) confirm `exit_on_error=False`
  makes the app raise rather than `sys.exit`, which is exactly why the app is
  built with `exit_on_error=False` so the wrapper owns exits; `--help`/`-h` are
  auto-added (cyclopts `docs/source/help.rst`). No new external surface is
  introduced, so no firecrawl claim is pinned beyond confirming the existing
  pattern, which the existing tests already gate (advisory A3 — citing the v4
  docs, not v5-develop). Date/Author: 2026-06-24, planning agent (revised round
  2).

## Outcomes & retrospective

Delivered 2026-06-24 across five atomic, `make all`-gated commits. The shipped
`novel-done` matches design §4.2's envelope exactly (the snapshot pins the
six-key `result` in §4.2 order with `schema_version: 1` and the `ok`/exit-code
biconditional), and the §1.3.2 corpus success criterion is met: a named
behavioural scenario proves the predicate exits `0` on the all-six-clauses-hold
tree, and a Scenario Outline drives each clause false to exit `1`. The B1
soundness fix holds end-to-end — the e2e proves an absent `compiled.md` exits `1`
(never a false `0`). The residual stale-but-present compile window (R-STALE) is
the named, documented deferral to roadmap task 3.1.2.

Lessons: (i) the corpus's plugin-per-fixture-surface split (driven by the
400-line cap) is the right place to add new fixture families — adding a fourth
plugin kept every existing module byte-stable; (ii) building the new specs as
`dataclasses.replace` of one all-hold spec made the "exactly one clause false"
guarantee mechanical and testable; (iii) the D-TWIN oracle discipline carried
over cleanly to the two new disk clauses.

coderabbit verification: Work items 1-3 each reviewed clean (0 findings). Work
item 4 was rate-limited; resolved on retry under the prescribed exponential
backoff (see the Progress and Surprises entries).

## Context and orientation

A reader new to this repository needs the following map. All paths are
repository-relative to the worktree root
(`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-1`).

The harness is a set of five console-scripts in the `novel_ralph_skill` package
(design §4). Each is a Cyclopts application driven through one shared wrapper so
they share an exit-code policy and a JSON envelope. The pieces this task builds
on are already in place and stable:

- `novel_ralph_skill/contract/runner.py` — the shared `run(app, argv, context)`
  wrapper. It owns every `sys.exit` and every envelope emission. A command body
  returns a `CommandOutcome(code, result, messages)`; a body raises
  `StateInputError` to signal the exit-`3` channel; a usage error surfaces as a
  `CycloptsError` the wrapper maps to exit `2`; `--help`/`--version` return a
  non-`CommandOutcome` value the wrapper treats as exit `0`. `parse_global_flags`
  splits the `--human` flag off argv before `run` is called.
- `novel_ralph_skill/contract/envelope.py` — `build_envelope`, `render_machine`,
  `render_human`. Stamps the envelope `schema_version` and computes `ok` via
  `is_ok`.
- `novel_ralph_skill/contract/exit_codes.py` — the `ExitCode` IntEnum
  (`SUCCESS=0`, `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`) and `is_ok`.
- `novel_ralph_skill/state/schema.py` — the frozen typed `State` dataclass and
  its tables: `State.phase.current` (a `Phase`), `State.gates.final.
  final_pass_complete`, `State.gates.knitting.done_30/done_50/done_80`,
  `State.chapters` (the `ChapterEntry` manifest, each with `.number`).
- `novel_ralph_skill/state/phase.py` — the `Phase` enum; `Phase.DONE` is the
  terminal member.
- `novel_ralph_skill/state/disk_evidence.py` — the closest existing parallel: a
  pure `(State, working_dir) -> tuple[Violation, ...]` detector that reads the
  `working/` tree. `novel-done`'s predicate engine follows its shape (per-clause
  predicate functions, a `chapter-NN` path derivation, a benign-absent /
  propagate-everything-else fault boundary). It already contains a
  `_check_compiled_matches_drafts` (`disk_evidence.py:179-196`) reading
  `compiled.md` existence and hash — 3.1.2 will share that machinery; 3.1.1 only
  needs the existence half.
- `novel_ralph_skill/state/_disk_paths.py` — defines `_chapter_dir_name`
  (`_disk_paths.py:19-21`) and `_on_disk_chapter_numbers`; the predicate engine
  imports `_chapter_dir_name` from **here** (not from `disk_evidence`, which only
  re-imports it; advisory A1).
- `novel_ralph_skill/state/wordcount.py` — `_chapter_word_count` and the one
  `len(text.split())` token rule.
- `novel_ralph_skill/state/compile_model.py` — `concatenate_drafts`
  (`compile_model.py:33`), the shared draft-join helper roadmap 3.1.2's hash
  clause will call (not needed in 3.1.1's existence-only clause).
- `novel_ralph_skill/commands/novel_state.py` — the `novel-state` app, and the
  reusable boundary helpers `working_dir()` (`:88`), `state_path()` (`:99`),
  `STATE_INPUT_ERRORS` (`:116`), `_load_or_state_error` (`:125`), and
  `WORKING_DIR_NAME` (`:85`). `novel-done` imports these so it resolves the same
  fixed `working/` tree and maps load faults the same way.
- `novel_ralph_skill/commands/_desloppify.py` — the single-action checker
  template `novel-done` mirrors: a `build_app()` (`:290`) with one `@app.default`
  body (`:313`) returning a `CommandOutcome`, configured
  `result_action="return_value", exit_on_error=False` (`:307`).
- `novel_ralph_skill/commands/stub.py` — the entry points. `novel_done()`
  (lines 93-95) is currently a stub; this task rewires it like `desloppify()`
  (lines 103-123).
- `tests/working_corpus/` — the §1.3.2 fixture corpus. `_specs.py` declares
  `ChapterSpec`/`WorkingTreeSpec`; `_builder.py` materialises a tree on disk;
  `_library.py` holds `PHASE_STATES`/`COHERENT_BASELINE`; `_oracle.py`/
  `_oracle_disk.py` hold the independent cross-check oracles; `tests/conftest.py`
  re-exposes corpus data as fixtures; `tests/working_corpus/__init__.py` is the
  public surface (`__all__`). The corpus models `done.flag`
  (`ChapterSpec.has_done_flag`), gates, phase, manifest, and `compiled.md`
  (`WorkingTreeSpec.compiled`: `None`/`COMPILED_AUTO`/verbatim), but **not**
  `reviews/knitting-NN.md` or `critic-notes.md`.

Authoritative documents (read these before coding the matching work item):

- Design: `docs/novel-ralph-harness-design.md` §1 (boundary), §2.3
  (verification scope / predicate truthfulness, lines 106-129), §3.1 (envelope),
  §3.2 (exit codes), §3.3 (checker/mutator segregation), §4.2 (`novel-done`,
  lines 302-348), §4.3 (`novel-compile` / manifest-ordered, lines 350-374).
- Reference predicate: `skill/novel-ralph/references/done-conditions.md`
  ("Novel-level predicate" lines 145-204, "Phase 8 — Drafting" lines 105-114,
  "Phase 9 — Final pass" lines 115-122, "Failure modes" lines 206-219).
- ADRs: `docs/adr-001-deterministic-judgemental-boundary.md`,
  `docs/adr-003-shared-interface-contract.md`,
  `docs/adr-005-command-surface-five-scripts.md`,
  `docs/adr-006-console-scripts-e2e-posix-policy.md`.
- Standards: `docs/scripting-standards.md` (Cyclopts/pathlib conventions),
  `docs/developers-guide.md` (the twin/oracle discipline, "Invariant
  validation"), `AGENTS.md` (gates, testing rules, module cap, spelling).

Terms defined: a *clause* is one of the six named done conditions. The
*predicate* is the conjunction of all six. A *checker* reads and reports and
never writes. The *envelope* is the common JSON object every command emits. The
*benign negative* (exit `1`) is "not yet done", which the harness loops on
without intervention. The *unsoundness window* is the bounded interval where a
3.1.1 verdict can be wrong: a present-but-stale `compiled.md` (R-STALE), closed
by 3.1.2.

## Plan of work

Five ordered work items, each a single commit gated by `make all`.

### Work item 1 — the pure per-clause predicate engine

**Implements:** design §4.2 (the per-clause result, lines 318-348), §2.3
(predicate truthfulness, lines 106-129); ADR-001 (read-only boundary). **Read
first:** design §4.2, §2.3; `done-conditions.md:145-204` "Novel-level
predicate"; `disk_evidence.py` (the parallel shape); `_disk_paths.py:19-21`
(`_chapter_dir_name`). **Skills:** `python-router` → `python-data-shapes` (the
frozen result dataclass), `python-errors-and-logging` (the
propagate-vs-absorb fault boundary).

Create `novel_ralph_skill/state/done_predicate.py`. It owns:

- A frozen, slotted, keyword-only `DoneClauses` dataclass mirroring design
  §4.2's six booleans, in the design's key order (`done-conditions.md` /
  design §4.2 JSON): `phase_is_done`, `final_pass_complete`,
  `all_chapters_flagged`, `knitting_gates_passed`, `compile_consistent`,
  `no_unresolved_blockers`. It exposes `all_hold` (the conjunction) and
  `failed_clause_names` (the ordered names of the false clauses, for `messages`).
- One pure predicate function per clause. The state-only clauses
  (`phase_is_done`, `final_pass_complete`) read only `State`. The disk-aware
  clauses read `working_dir`, deriving the chapter path with the imported
  `_chapter_dir_name`:
  - `all_chapters_flagged`: every **manifest** chapter has an on-disk
    `working/manuscript/chapter-NN/done.flag` (an absent flag is a false clause,
    not a fault).
  - `knitting_gates_passed`: `state.gates.knitting.done_30/done_50/done_80`
    all `True` **and** `working/reviews/knitting-30.md`, `knitting-50.md`,
    `knitting-80.md` all exist (D-CLAUSES).
  - `no_unresolved_blockers`: no **manifest** chapter's
    `working/manuscript/chapter-NN/critic-notes.md` contains an unresolved
    BLOCKER, per the D-BLOCKER format. An absent `critic-notes.md` is clean.
  - `compile_consistent`: a one-line
    `compile_consistent_exists(working_dir) -> bool` returning whether
    `working/manuscript/compiled.md` exists, docstring-flagged as
    existence-only with the hash half owned by roadmap 3.1.2
    (D-COMPILE-EXISTENCE).
- An `evaluate_done(state, working_dir) -> DoneClauses` aggregator assembling the
  six in design order.

The fault boundary (D-FAULT): only `FileNotFoundError` is absorbed (benign
absent artefact); every other read fault propagates for the command layer to
translate. The threshold constants `(30, 50, 80)` are taken once and shared
between the gate booleans and the review-file names so they cannot drift; cite
`done-conditions.md:164-170` and design §5.2 invariant 7.

Tests (this commit): `tests/test_done_predicate.py` — a unit test per clause
proving each independently true and false over hand-built `tmp_path` trees
(state-only clauses over crafted `State` values, disk-aware clauses over written
artefacts); a test that `compile_consistent_exists` is `False` when
`compiled.md` is absent and `True` when present (including when present-but-stale
— pinning the R-STALE window so 3.1.2's swap is visible); a test that
`DoneClauses.all_hold` is the six-way conjunction and `failed_clause_names`
lists exactly the false ones in design order; a property test (`hypothesis`)
over a strategy generating the six booleans asserting `all_hold == all(...)`
and the `failed_clause_names` ordering. Per `python-verification`, Hypothesis is
the right adversary here (an invariant over the boolean cross-product);
CrossHair/mutmut are not needed for this work item.

### Work item 2 — model the two missing artefacts and the all-hold case in the corpus

**Implements:** design §2.3 / §1.3.2 corpus success criterion (each clause
driven true and false from the corpus, and an all-six-hold tree existing);
`done-conditions.md` Phase 8/9 (lines 105-122). **Read first:**
`tests/working_corpus/_specs.py`, `_builder.py`, `_library.py`, `__init__.py`;
`developers-guide.md` twin/oracle discipline. **Skills:** `python-router` →
`python-testing` (corpus fixtures, the conftest re-export rule).

Extend `ChapterSpec` with a `critic_notes: str | None = None` field
(`None` = no file; a string = the `critic-notes.md` body to write) and
`WorkingTreeSpec` with a `knitting_reviews` field
(a tuple of the percentages from `{30, 50, 80}` whose
`working/reviews/knitting-NN.md` files exist), defaulting to the empty/`None`
state so every existing corpus spec stays byte-identical. Teach `_builder.py`
`_write_chapter` to write `critic-notes.md` when set, and add a `_write_reviews`
step writing `working/reviews/knitting-NN.md` for each named percentage. Record
the D-BLOCKER format beside the field docstring so the corpus is the BLOCKER
format's worked example.

Add **new** named specs (a `DONE_PREDICATE_STATES` mapping or equivalently named
specs in `_library.py`, exported through `__init__.py` `__all__`, surfaced as
conftest fixtures) — **without altering `PHASE_STATES`/`COHERENT_BASELINE` or
`_drafting_spec`** (D-CORPUS, R-CHURN):

- **all-six-clauses-hold** (the load-bearing fixture the roadmap criterion
  needs): `phase=done`, `final_pass_complete=True`, all chapters flagged, all
  three gate booleans true, all three `knitting-{30,50,80}.md` present,
  clean/absent `critic-notes.md`, and `compiled=COMPILED_AUTO` (a present
  `compiled.md`).
- per-clause failers derived from the all-hold spec by toggling exactly one
  clause false: phase not done; final pass incomplete; one chapter unflagged;
  one review file missing (and, separately, one gate boolean false); an absent
  `compiled.md`; an unresolved BLOCKER in one `critic-notes.md`.
- a `[resolved]`-BLOCKER spec (still holds — proving the resolution token is
  honoured) and a near-miss BLOCKER spec whose body merely mentions resolution
  in prose (still an unresolved blocker — pinning the substring rule's edge;
  advisory A5).

Tests (this commit): a focused test module asserting the builder writes
`reviews/knitting-NN.md` and `critic-notes.md` exactly as specified and adds
**no other** files relative to the same spec without them (R-CHURN guard); that
the all-hold spec materialises every artefact the six clauses need; and the
oracle twins (D-TWIN): a corpus-side reader for review-existence and for the
BLOCKER scan, each pinned equal to the production predicate by a cross-check
test over the new specs, mirroring how `disk_evidence` twins `_oracle.py`. Also
assert that the existing `PHASE_STATES`/`COHERENT_BASELINE` trees materialise
byte-identically to before (no `reviews/`, no `critic-notes.md`).

### Work item 3 — wire the `novel-done` command and retire the stub

**Implements:** design §4.2, §3.1, §3.2, §3.3; ADR-003; ADR-005 (the named
five-script surface). **Read first:** `_desloppify.py:206-320` (the template),
`novel_state.py:116-153` (`_load_or_state_error`, `STATE_INPUT_ERRORS`,
`working_dir`), `runner.py`. **Skills:** `python-router` →
`python-types-and-apis` (the `build_app` signature), `python-errors-and-logging`
(StateInputError routing).

Create `novel_ralph_skill/commands/_novel_done.py`:

- A `_novel_done() -> CommandOutcome` body that resolves `working_dir()`, loads
  the state through `_load_or_state_error` (exit `3` on a bad state), runs
  `evaluate_done(state, working_dir)` wrapped so the D-FAULT non-absent read
  faults map to `StateInputError`, and builds the outcome: `result` is the six
  per-clause booleans (the `DoneClauses` rendered to a dict in design order);
  `code` is `ExitCode.SUCCESS` when `all_hold` else `ExitCode.BENIGN_NEGATIVE`;
  `messages` names the failed clauses (or "novel is done").
- A `build_app() -> cyclopts.App` with a single `@app.default` body, configured
  exactly as `desloppify`'s (`result_action="return_value", exit_on_error=False,
  print_error=False, help_on_error=False`).

Rewire `stub.py` `novel_done()` to mirror `desloppify()` (`stub.py:103-123`):
pre-parse `--human`, import `_novel_done` lazily, drive `build_app()` through
`run` with a `RunContext(command=_NAME_FOR["novel_done"],
working_dir=WORKING_DIR_NAME, human=human)`. The `novel_done` name continues to
come from the single `COMMAND_ENTRY_POINTS` registry (`stub.py:23`; roadmap
1.2.4), so no name is re-spelled.

Tests (this commit): `tests/test_novel_done_command.py` — drive `build_app()`
in-process over corpus trees materialised under `tmp_path` (chdir into the
parent so `working/` resolves), asserting exit `0` only on the all-hold tree,
exit `1` on each single-clause-fail tree (including the absent-`compiled.md`
tree — proving the existence half drives a benign `1`, never a false `0`), exit
`3` on a missing/unparseable `state.toml` and on an undecodable `critic-notes.md`
(the D-FAULT negative test), and exit `2` on a stray positional token (the
runner's `CycloptsError` arm). Assert `compile_consistent` never drives exit `4`
in 3.1.1.

### Work item 4 — the clause matrix, snapshot, and e2e suites

**Implements:** design §2.3 (combinatorial surface `command × output-mode ×
phase`, lines 125-129), §9 (coverage strategy); AGENTS.md testing rules. **Read
first:** `AGENTS.md` "Python verification and testing", `docs/adr-006` (POSIX
e2e policy), the existing `tests/test_desloppify_snapshots.py`,
`tests/test_console_scripts_e2e.py`, and the `recount.feature`/`reconcile.feature`
BDD wiring. **Skills:** `python-router` → `python-testing` (BDD, snapshot,
parametrization); `hypothesis` if a further property emerges.

Add:

- `tests/features/novel_done.feature` + `tests/steps/novel_done_steps.py` (the
  behavioural proof): scenarios driving each clause independently true and false
  over the new corpus specs and asserting the predicate exits `0` **only** on the
  all-six-clauses-hold tree — the literal roadmap 3.1.1 success criterion. The
  all-hold "exits 0" scenario is the load-bearing half (R-ALLHOLD); it must be a
  named scenario, not implied. Register the feature like the existing
  `recount.feature`/`reconcile.feature` BDD wiring.
- A machine-mode envelope snapshot suite (`syrupy`) for two pinned trees
  (all-clauses-hold → exit `0`; one-clause-fails → exit `1`), redacting nothing
  nondeterministic (the corpus uses a fixed `created_at`; `novel-done` emits no
  timestamps or paths beyond the fixed `working`). Pair every snapshot with a
  semantic per-clause assertion so the snapshot is not the only coverage
  (AGENTS.md snapshot rule).
- A human-mode presence assertion (`--human` renders without error and names the
  failed clauses), per the §2.3 "human mode asserted for presence" rule.
- An e2e proof that the installed `novel-done` console-script runs end-to-end
  on a built wheel over a real `working/` tree and exits per the predicate
  (extend or parallel `tests/test_console_scripts_e2e.py`; POSIX-only per
  ADR-006, marked `slow`).

### Work item 5 — documentation and the contents map

**Implements:** AGENTS.md "Project documentation"; design cross-reference; the
R-STALE unsoundness-window disclosure (B1). **Read first:**
`docs/users-guide.md`, `docs/developers-guide.md`, `docs/contents.md`.
**Skills:** `en-gb-oxendict` (spelling), `execplans` (keep this plan current).

- `docs/users-guide.md`: add a `novel-done` entry describing the six-clause
  result and the `0`/`1`/`3` exit codes it produces in v1, with an explicit **v1
  caveat**: `compile_consistent` in v1 checks only that `compiled.md` *exists*,
  so a present-but-stale compile is not yet caught and the exit-`4` compile
  carve-out lands with task 3.1.2 (R-STALE). State that an *absent* compile is
  always reported (never a false "done").
- `docs/developers-guide.md`: add a "Done predicate (`novel-done`)" subsection
  documenting the clause→artefact mapping (D-CLAUSES) including the
  manifest-vs-outline divergence (B3), the D-BLOCKER format, the
  existence-only `compile_consistent` placeholder and its 3.1.2 owner with the
  R-STALE window, the D-FAULT boundary, and the D-TWIN oracle discipline for the
  two new disk clauses, in the same register as the "Invariant validation"
  subsection.
- `docs/novel-ralph-harness-design.md`: add a one-line note in §4.2 that 3.1.1
  ships five sound clauses plus an existence-only `compile_consistent`, with the
  hash half and exit-`4` carve-out in 3.1.2; otherwise leave the design
  unchanged and record that in the Decision Log.
- `docs/contents.md`: index this execplan.
- Update this plan's `Progress`, `Outcomes & retrospective`, and Status.

Validation for this work item additionally runs `make markdownlint` and
`make nixie` (the latter only if any Mermaid diagram is touched; none is
expected).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-1`.

1. Confirm the branch and a clean tree:

   ```console
   $ git branch --show-current
   roadmap-3-1-1
   ```

2. For each work item, in order: write the failing test(s) first (red), then the
   implementation (green), then refactor. After each work item:

   ```console
   $ make all
   ... build check-fmt lint typecheck test all pass ...
   ```

   Expect `build`, `check-fmt`, `lint` (ruff + interrogate + pylint),
   `typecheck` (`ty`), and `test` (pytest under xdist) to pass. For the
   documentation work item also run:

   ```console
   $ make markdownlint
   ... Summary: 0 error(s) ...
   $ make nixie
   ... mermaid diagrams valid ...
   ```

3. Commit each work item separately with an en-GB Oxford-spelling message
   naming the roadmap task (3.1.1) and the design section it implements. Do not
   begin implementation until this plan is approved.

A representative transcript once the command is wired (Work item 3), over a tree
where only `phase_is_done` is unmet:

```console
$ novel-done; echo "exit=$?"
{"command": "novel-done", "schema_version": 1, "ok": false,
 "working_dir": "working",
 "result": {"phase_is_done": false, "final_pass_complete": true,
            "all_chapters_flagged": true, "knitting_gates_passed": true,
            "compile_consistent": true, "no_unresolved_blockers": true},
 "messages": ["phase_is_done is false"]}
exit=1
```

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Per-clause independence and the all-hold exit-0 (the roadmap success
  criterion).** Running the `tests/features/novel_done.feature` scenarios
  passes: each clause is driven true and false from the §1.3.2 corpus, **and** a
  named scenario proves the predicate exits `0` on the all-six-clauses-hold tree.
  The new scenarios fail before Work items 1–3 land and pass after.
- **Sound absent-compile behaviour.** Over an otherwise-complete tree whose
  `compiled.md` is *absent*, `novel-done` exits `1` (never `0`): the
  existence-only clause is false, so no false "done" is emitted (B1).
- **Exit-code contract.** Over the all-hold tree, `novel-done` exits `0` with
  `ok: true`; with any clause unmet it exits `1` with `ok: false`; with a
  missing/unparseable `state.toml` or an undecodable `critic-notes.md` it exits
  `3`; with a stray positional token it exits `2`. No 3.1.1 path exits `4`.
- **Envelope shape.** The machine-mode snapshot pins the six-key `result` in
  design §4.2 order with the contract `schema_version` and the `ok`/exit-code
  biconditional. `--human` renders without error and names the failed clauses.
- **Installed command.** On POSIX, the built wheel's `novel-done` console-script
  runs over a real `working/` tree and exits per the predicate
  (`tests/test_console_scripts_e2e.py`, marked `slow`).

Quality criteria ("done" means):

- Tests: the new unit, behavioural, property, snapshot, and e2e suites pass; the
  whole suite passes under `make test` (xdist; per-test 30s timeout is ample for
  these filesystem-only tests).
- Lint/typecheck: `make lint` (ruff, `interrogate` docstring gate, pylint) and
  `make typecheck` (`ty`) report no findings.
- Markdown: `make markdownlint` passes; `make nixie` passes if any Mermaid is
  touched.

Quality method: `make all` (and `make markdownlint`/`make nixie` for the
documentation work item) is the single gate run before every commit.

## Idempotence and recovery

`novel-done` is read-only, so re-running it is always safe and never mutates the
tree. The implementation steps are ordinary source edits under version control;
to retry a work item, reset the working tree (`git restore`) and re-apply. No
step is destructive and no backup is required. The corpus extensions (Work item
2) default to the existing behaviour and add only **new** named specs, so a
half-applied change leaves every existing fixture and snapshot byte-identical.

## Artifacts and notes

Key reuse points the implementer should not reinvent:

- `novel_ralph_skill/state/_disk_paths.py:19-21` — `_chapter_dir_name`, the
  `chapter-NN` derivation `all_chapters_flagged` and `no_unresolved_blockers`
  follow (import from `_disk_paths`, not `disk_evidence`; advisory A1).
- `novel_ralph_skill/state/disk_evidence.py:179-196` —
  `_check_compiled_matches_drafts`, the existence+hash `compiled.md` read 3.1.2
  shares; 3.1.1's `compile_consistent` reuses only its existence half.
- `novel_ralph_skill/commands/_desloppify.py:290-320` — the
  single-`@app.default` checker `build_app` template.
- `novel_ralph_skill/commands/stub.py:103-123` — the `desloppify()` entry-point
  wiring `novel_done()` is rewired to mirror.
- `novel_ralph_skill/commands/novel_state.py:116-153` — `STATE_INPUT_ERRORS`
  and `_load_or_state_error`, the load-fault → exit-`3` boundary.
- `tests/working_corpus/_library.py:79-118` — the `_drafting_spec` /
  `PHASE_STATES` / `COHERENT_BASELINE` shape the new `DONE_PREDICATE_STATES`
  specs sit beside without mutating (D-CORPUS).

## Interfaces and dependencies

Be prescriptive. At the end of this task these must exist:

In `novel_ralph_skill/state/done_predicate.py`:

```python
import dataclasses


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DoneClauses:
    phase_is_done: bool
    final_pass_complete: bool
    all_chapters_flagged: bool
    knitting_gates_passed: bool
    compile_consistent: bool
    no_unresolved_blockers: bool

    @property
    def all_hold(self) -> bool: ...

    @property
    def failed_clause_names(self) -> tuple[str, ...]: ...


def evaluate_done(
    state: "novel_ralph_skill.state.schema.State",
    working_dir: "pathlib.Path",
) -> DoneClauses: ...


def compile_consistent_exists(working_dir: "pathlib.Path") -> bool:
    """Return whether compiled.md exists.

    Existence-only in 3.1.1; roadmap task 3.1.2 adds the hash comparison and the
    exit-4 carve-out so a present-but-stale compile is caught.
    """
```

In `novel_ralph_skill/commands/_novel_done.py`:

```python
import cyclopts

from novel_ralph_skill.contract.runner import CommandOutcome


def build_app() -> cyclopts.App: ...
```

In `novel_ralph_skill/commands/stub.py`, `novel_done()` drives the real app
through `novel_ralph_skill.contract.runner.run` (no signature change to the
entry point).

Dependencies: runtime stays `cyclopts` + `tomlkit` (`pyproject.toml:8`; no
change). Dev stays `pytest`, `pytest-bdd`, `hypothesis`, `syrupy`,
`pytest-timeout`, `pytest-xdist` (no change). cuprum is not used (no external
process; design §4 line 269).

## Revision note

Round 2 (2026-06-24). Revised after Logisphere design-review round 1
(`docs/execplans/roadmap-3-1-1.review-r1.md`). Resolved blocking points:

- **B1** — replaced the hardcoded `compile_consistent = True` with the **sound
  existence half** (`compile_consistent_exists`): an *absent* `compiled.md` now
  yields a false clause and exit `1`, never a false exit-`0` "done"
  (D-COMPILE-EXISTENCE; the reviewer's preferred option (b) / Wafflecat split).
  The narrowed residual stale-but-present window is named (R-STALE) and
  disclosed in the users'/developers' guides (Work item 5).
- **B2** — added an explicit Work item 2 step constructing the
  all-six-clauses-hold spec and the per-clause failers as **new** named specs
  (D-CORPUS), leaving `PHASE_STATES`/`COHERENT_BASELINE` byte-identical;
  retracted the blanket "no churn" claim and replaced it with the verified
  mechanism — the disk-evidence detector ignores `reviews/` and `critic-notes.md`
  (`disk_evidence.py`), and the only full-tree `rglob` assertions run over the
  `done-flag-*` variants, not `PHASE_STATES["done"]` (R-CHURN). The all-hold
  exit-0 scenario is a named, load-bearing acceptance criterion (R-ALLHOLD).
- **B3** — recorded the deliberate per-manifest (not per-outline)
  chapter-source divergence and its design §4.3 justification in D-CLAUSES.

Advisories addressed: A1 (`_chapter_dir_name` imported from `_disk_paths`, not
`disk_evidence`); A2 (runtime deps cited at `pyproject.toml:8`, not line 16);
A3 (cyclopts behaviour cited against the v4 API docs, not v5-develop); A4
(D-TWIN decides up front that the two new disk clauses get oracle twins); A5 (a
near-miss BLOCKER corpus spec pins the substring rule's edge). Initial draft was
2026-06-24; this round revises the `compile_consistent` mechanism, the corpus
strategy, and the citations.

## Addenda

Lightweight post-merge corrections folded onto this completed task. Each runs as
a no-plan, no-review addendum pass (roadmap sub-task under the `[x]` 3.1.1
parent).

- **Roadmap 3.1.1.1 — reconcile `done-conditions.md` to the manifest chapter
  source** (from review:3.1.1 / audit:3.1.1; severity low). D-CLAUSES recorded
  that the shipped predicate reads per-manifest chapters (`state.chapters`)
  while the reference `novel_predicate` at
  `skill/novel-ralph/references/done-conditions.md:158,180` still parses
  `plan/chapter-outline.md` through a `parse_chapter_outline` that does not exist
  in the codebase, and flagged the reference for a later docs reconciliation. Edit
  the reference predicate prose so it iterates the manifest chapter source rather
  than the absent outline parse, keeping the design §4.3 chapter-source rule the
  single described path. Docs-only; no code or test change.
