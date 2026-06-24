# Implement `wordcount` reporting and gate-trigger derivation

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 2 — revised after Logisphere design review r1)

## Purpose / big picture

Today the `wordcount` console-script is a stub: running it prints "`wordcount`
is not yet implemented" to standard error and exits `2` (see
`novel_ralph_skill/commands/stub.py:135` and `docs/users-guide.md:85`). The
field report computed per-chapter and cumulative word counts, the percentage of
target, the distance to the next knitting gate, and the delta against each
chapter target by hand, repeatedly — and as a result the 80% knitting gate
could be noticed late, at 85% (design §4.5).

After this change a novelist (or the harness) can run `wordcount` against a
materialised `working/` tree and observe, in the shared JSON envelope, a
read-only report: per chapter and cumulatively, the words drafted, the
percentage of the novel target, the distance in words to the next knitting
gate, the delta against the chapter target, and which of the 30%, 50%, and 80%
gate triggers the drafted total has reached. A manuscript drafted to exactly a
gate threshold reports that gate as just reached, and the next-gate distance is
never negative.

You can see it working: with a `working/` tree drafted to 80% of an 80 000-word
target, running `wordcount` (machine mode) emits an envelope whose `result`
shows `gate_triggered_80: true`, the next-gate distance, and the per-chapter
table — and the process exits `0`. The previously stubbed exit-`2` behaviour is
gone, and the test-suite tripwires that assert `wordcount` is "still stubbed"
move it into the real-command set.

`wordcount` is a **read-only checker** (ADR-001): it reads the chapter drafts
and `state.toml`, derives the report, writes nothing to disk, and reports a
finding without editing, judging, or mutating any state (design §4.5;
`docs/developers-guide.md:177`). It shells out to nothing, so — like every v1
command — it uses no `cuprum` at runtime (design §9 line 836: "v1 commands
shell out to nothing"; `pyproject.toml:8` runtime deps are `["cyclopts",
"tomlkit"]`, with `cuprum` under the dev group at `:27`).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Read-only checker.** `wordcount` must write nothing to disk: no
  `state.toml` mutation, no `[pending_turn]` bracket, no compiled output. It is
  a checker, not a mutator (ADR-001; design §3.3, §4.5).
- **Single counting rule.** The per-chapter word count is
  `len(draft_text.split())` over the UTF-8 body of
  `working/manuscript/chapter-NN/draft.md`. `wordcount` must reuse
  `novel_ralph_skill.state.wordcount.recount_words` (and through it
  `_chapter_word_count`) — the one counting rule the corpus oracle is pinned to
  — and must not introduce a second counter (design §4.1; the existing
  `state/wordcount.py` module docstring; developers-guide "Word-count algorithm
  is fixed").
- **Single gate-threshold source.** The 30/50/80% triggers must be derived from
  the existing `novel_ralph_skill.state.GATE_THRESHOLDS = (0.30, 0.50, 0.80)`
  constant (`novel_ralph_skill/state/validate.py:76`, re-exported from
  `novel_ralph_skill.state.__init__`). Do **not** re-spell `0.30`, `0.50`, or
  `0.80` anywhere in the new command (design §5.2 bullet 7; §4.5).
- **Triggers, not gate flags.** `wordcount` reports the *derived* trigger — has
  the drafted ratio crossed the threshold — which is distinct from the recorded
  `[gates.knitting]` boolean. A recorded gate flag means "threshold crossed
  **and** the knitting pass integrated and logged" (design lines 590-592), an
  agent action disk does not store. `wordcount` derives the geometry from the
  drafted total; it must not claim a recorded gate is set, nor reconcile or
  rewrite `[gates]` (design §4.5; lines 590-596).
- **Drafted-sum numerator.** The ratio numerator is the drafted total
  `sum(by_chapter.values())` over the on-disk drafts, the same numerator
  `_check_gate_ratio_consistent` uses (`validate.py:263`), never the compiled
  token count and never `[word_counts].current` read blindly from the table.
- **Shared envelope and exit-code contract.** `wordcount` must build its app
  with `make_contract_app("wordcount")` and return a `CommandOutcome` through
  the shared `run` wrapper, exactly like `desloppify` and `novel-compile`
  (`contract/runner.py`; ADR-003; design §3.1, §3.2). The four-flag contract
  and the `--human` pre-parse are owned by the shared seam; do not renegotiate
  them.
- **Exit-code routing.** A missing or unparseable `state.toml`, an absent
  `working/`, or an unreadable/undecodable draft is the exit-`3` state channel
  (`StateInputError`); a malformed invocation Cyclopts catches (e.g. an unknown
  `--option`) is the exit-`2` usage channel. (v1 takes no `--chapter`, so there
  is no command-specific usage fault — D-SCOPE.) The successful report path is
  exit-`0` (design §3.2; ADR-003 Table 2). See Decision Log D-EXIT for the
  0-versus-4 question.
- **400-line file cap.** No single code file exceeds 400 lines (AGENTS.md "Keep
  file size manageable"). Split the command body and its envelope projection
  across two modules, mirroring `_desloppify.py` / `_desloppify_report.py`.
- **No new runtime dependency.** The package runtime dependencies stay
  `["cyclopts", "tomlkit"]` (`pyproject.toml:8`). `wordcount` adds none.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (AGENTS.md; en-gb-oxendict skill).

## Tolerances (exception triggers)

- **Scope.** If the implementation requires changing more than 8 files or more
  than ~450 net lines of non-test code, stop and escalate. (Estimate: two new
  small command modules, three test tripwire edits, two doc edits, plus new
  test files.)
- **Interface.** If a public interface beyond the new `wordcount` command body
  and its envelope projection must change — for example the shared `run`
  wrapper, `CommandOutcome`, the envelope renderer, or `recount_words`'s
  signature — stop and escalate.
- **Dependencies.** If a new external dependency (runtime or dev) appears
  necessary, stop and escalate.
- **Gate semantics ambiguity.** If the 0-versus-4 success-code question
  (Decision Log D-EXIT) proves materially contested by the design or a
  reviewer, stop and present the options rather than guessing.
- **Iterations.** If `make all` still fails after 3 focused attempts on one
  work item, stop and escalate.

## Risks

- Risk: The report could re-spell the gate thresholds or re-implement the
  counter, creating a second source of truth that drifts from the validator and
  the corpus oracle. Severity: high Likelihood: medium Mitigation: Constraints
  pin reuse of `GATE_THRESHOLDS` and `recount_words`; a unit test asserts the
  command imports the shared constant (e.g. by asserting the derived triggers
  agree with `GATE_THRESHOLDS` element-wise), and the Work-item-2 gate-boundary
  tests pin the crossing behaviour at exactly each threshold.

- Risk: Confusing the *derived trigger* with the *recorded gate flag*, leading
  `wordcount` to report `[gates.knitting]` booleans (which encode an integrated
  pass) instead of the drafted-ratio geometry. Severity: high Likelihood:
  medium Mitigation: Constraint "Triggers, not gate flags"; the envelope field
  names must say `gate_triggered_30/50/80` (or equivalent), not `done_30`; a
  unit test constructs a tree whose drafted ratio has crossed 30% but whose
  `done_30` flag is `false` and asserts the report shows the trigger reached
  while never echoing the recorded flag.

- Risk: A negative "next-gate distance" when the manuscript is past the 80%
  gate (no next gate), or off-by-one at a threshold boundary. Severity: medium
  Likelihood: medium Mitigation: The success criterion requires a non-negative
  next-gate distance; Work-item-2 boundary examples (a manuscript exactly on
  each gate, and one past 80%) pin this. Past the final knitting gate the
  report emits an explicit "no further knitting gate" signal rather than a
  negative distance.

- Risk: An undecodable or unreadable `draft.md` is swallowed as `0` and escapes
  to the benign exit `1` instead of the exit-`3` state channel. Severity:
  medium Likelihood: low Mitigation: `recount_words` already propagates every
  non-`FileNotFoundError` read fault; the command wraps it in `StateInputError`
  exactly as `_recount._recount_or_state_error` and
  `_desloppify.source_chapters` do. A CLI error-path test drives an undecodable
  draft and asserts exit `3`.

- Risk: `target <= 0` (a degenerate or pre-planning state) divides by zero in
  the ratio. Severity: medium Likelihood: low Mitigation: Mirror the
  validator's and oracle's totality guard (`validate.py:261` `if target <= 0`):
  short-circuit *every* derived percentage — the cumulative `percent_of_target`
  and each per-chapter `percent_of_chapter_target` whose chapter target is also
  non-positive — as well as the gate geometry, rather than dividing. The
  short-circuit leaves the cumulative percentage `None` and
  `next_gate_threshold`/`next_gate_distance` both `None`. A unit test pins the
  `target == 0` path.

- Risk: Wiring `wordcount` to a real app leaves the two live "still stubbed"
  test tripwires (`tests/test_command_stubs.py` and
  `tests/test_console_scripts_e2e.py`) asserting the old exit-`2` contract,
  breaking `make test`. (`tests/test_stub.py` is **not** a tripwire — see the
  Surprises entry T-STUB — so it needs no change.) Severity: medium Likelihood:
  high Mitigation: Work item 3 explicitly moves `wordcount` into the
  real-command set in both tripwires and updates the users-guide stub note,
  gated by `make test`.

- Risk: Promoting `wordcount` is promoting the **last** of the five stubs (the
  other four are already real; `names.py:21-27`, both `_REAL_COMMANDS` sets).
  Adding `"wordcount"` to each `_REAL_COMMANDS` set empties the derived "still
  stubbed" collections, which makes `test_entry_point_callable_exits_two`
  collect zero parametrize items (pytest warns "got empty parameter set" and
  silently skips it) and makes `_assert_scripts_exit_two` loop over nothing, so
  `test_console_scripts_install_and_exit_two` builds a wheel and asserts
  nothing — a slow, POSIX-only test that vacuously passes. Both guards quietly
  stop testing the installed/callable invocation surface. Severity: high
  Likelihood: high Mitigation: WI3 does not merely "add to `_REAL_COMMANDS`":
  it **repurposes** both now-dead tests into the dual all-real-commands
  assertion (every entry point drives a real app; every installed script
  resolves and runs a real app), with an explicit guard that the parametrize
  sets are non-empty so a future regression cannot silently empty them again.
  See Decision Log D-TRIPWIRE.

## Progress

- [x] (done) WI1 — Wire the `wordcount` command skeleton onto the shared
  contract (red: a failing in-process command test). Landed
  `novel_ralph_skill/commands/_wordcount.py` (`build_app`,
  `source_state_and_drafts`, `_recount_or_state_error`, a thin placeholder
  body) and `tests/test_wordcount_command.py` (coherent exit 0;
  absent/unparseable/ undecodable exit 3; unknown `--option` exit 2; meta-flags
  exit 0 with no envelope). A per-module `coherent_working` fixture bundles the
  three corpus builders to stay within the Pylint argument-count gate.
  `make all` green; coderabbit run 1 addressed (assert messages; meta-flag
  no-envelope asserted via `json.JSONDecodeError`; plan snapshot snippet and
  `target <= 0` wording fixed).
- [x] (done) WI2 — Derive and project the per-chapter and cumulative report
  with gate-trigger geometry (green: report tests and gate-boundary snapshots).
  Landed `novel_ralph_skill/commands/_wordcount_report.py` — frozen
  `ChapterReport`/`CumulativeReport`/`WordcountReport` dataclasses, the kw-only
  `build_report(*, target, manifest, by_chapter)`, and `report_outcome`. The
  numerator is `sum(by_chapter.values())`; the thresholds come from
  `GATE_THRESHOLDS` (no re-spelled literal). The `>=`-trigger / `<`-next
  tie-break is pinned; the next-gate distance uses `math.ceil` and is clamped
  non-negative; `target <= 0` short-circuits every percentage and the gate
  geometry to `None`. `_wordcount.py`'s body now calls `build_report` then
  `report_outcome`. Tests: `tests/test_wordcount_report.py` (pure aggregation),
  `tests/test_wordcount_snapshots.py` (representative snapshot plus the exact-on-
  gate, past-80%, `target == 0`, and trigger-versus-flag boundary examples) with
  a committed `.ambr`. `make all` green; coderabbit run 2 addressed (snapshot
  bare-assert messages; report triggers pinned to explicit expected tuples per
  case rather than re-deriving `ratio >= gate`). Skipped: the class-grouping
  findings (the repo convention is module-level test functions; adopting test
  classes here would be inconsistent) and the review-r2 citation finding (that is
  a review-record artefact, not the living plan).
- [x] (done) WI3 — Promote `wordcount` to the real-command set, repurposing
  the two now-dead "still stubbed" tripwires into all-real-commands assertions,
  updating the users-guide stub note, and adding the installed-binary e2e.
  `stub.wordcount()` now drives the real app via `_drive` (deferred `_wordcount`
  import); the module docstring records all five entry points as real.
  `tests/test_command_stubs.py` gained `"wordcount"` in `_REAL_COMMANDS` and a
  repurposed `test_entry_point_callable_drives_real_app` (parametrized over all
  entry points, guarded non-empty) asserting each callable takes the real exit-3
  path under an absent `working/`. `tests/test_console_scripts_e2e.py` gained
  `"wordcount"` and a repurposed `test_console_scripts_install_and_run_real`
  asserting every installed script exits 3 with no `working/`. Both account for
  `novel-state` being a command-group app via a small `_REAL_PATH_ARGV` map
  (`novel-state` needs the `check` subcommand to reach its state-resolving path;
  a deviation the plan's "bare argv exits 3" recipe missed — recorded in the
  Decision Log below). Added `tests/test_wordcount_e2e.py` (slow, POSIX-only).
  Updated `docs/users-guide.md`'s stub note to describe the real command. `make
  all`, `make markdownlint` (users-guide and execplan clean), and `make nixie`
  green; coderabbit run 3 returned one finding (the recurring review-r2
  fabricated-citation), resolved by replacing the fabricated users-guide citation
  in the living plan with `pyproject.toml:8`.

## Surprises & discoveries

- Observation: The counting rule and gate-threshold constant already exist and
  are pinned to the corpus oracle. Evidence:
  `novel_ralph_skill/state/wordcount.py` (`recount_words`,
  `_chapter_word_count`); `novel_ralph_skill/state/validate.py:76`
  (`GATE_THRESHOLDS = (0.30, 0.50, 0.80)`), re-exported from
  `novel_ralph_skill/state/__init__.py:84`. Impact: WI2 is pure aggregation and
  projection — no new counting or threshold logic — exactly as the roadmap (§9:
  "the command is a pure aggregation") and design §4.5 frame it.

- Observation: `wordcount` is already a registered console-script name and
  routes through the stub. Evidence: `novel_ralph_skill/commands/names.py:26`;
  `novel_ralph_skill/commands/stub.py:135`. Impact: WI3 is a stub-to-real
  promotion, not a new entry-point registration; `[project.scripts]` and the
  command registry need no change, only the "still stubbed" tripwires and the
  stub `wordcount()` body.

- Observation (T-STUB): `tests/test_stub.py` is **not** a stub-command tripwire.
  Evidence: its entire body is `test_hello_returns_stub_greeting`, asserting
  `novel_ralph_skill.hello() == "hello from Python"`; it contains no reference
  to the command stub set, `wordcount`, or `_REAL_COMMANDS`. Impact: WI3 must
  not touch `tests/test_stub.py`. The only live "still stubbed" tripwires are
  `tests/test_command_stubs.py` and `tests/test_console_scripts_e2e.py`; the
  round-1 review's B3 correctly flagged the phantom reference, now removed
  throughout this plan.

- Observation (T-LAST): `wordcount` is the **last** remaining stub.
  Evidence: `novel_ralph_skill/commands/names.py:21-27` registers five
  commands; the `_REAL_COMMANDS` sets in `tests/test_command_stubs.py:37-42` and
  `tests/test_console_scripts_e2e.py:42-47` each already list the other four
  (`novel-state`, `desloppify`, `novel-compile`, `novel-done`). Impact: Adding
  `"wordcount"` empties `STILL_STUBBED_ENTRY_POINTS`
  (`test_command_stubs.py:43`) and `_STILL_STUBBED_NAMES`
  (`test_console_scripts_e2e.py:48`), so the parametrize/loop bodies that
  consume them go dead. Promoting the last stub is a *different operation* from
  promoting one of several; WI3 converts those guards rather than abandoning
  them (Decision Log D-TRIPWIRE).

- Observation: `cuprum` is a dev/test dependency only and is used solely by the
  installed-binary e2e harness (to run the console-script by absolute path),
  never by a command body. Evidence: `pyproject.toml:8` runtime deps are
  `["cyclopts", "tomlkit"]`; `cuprum` appears under the dev group at
  `pyproject.toml:27`; `tests/test_desloppify_e2e.py` and
  `tests/test_console_scripts_e2e.py` are the only `cuprum` consumers. Impact:
  WI1/WI2 introduce no `cuprum`; WI3's e2e reuses the existing
  `single_program_catalogue` fixture and the cuprum absolute-path-`Program`
  pattern proven by `tests/test_desloppify_e2e.py`.

## Decision log

- Decision (D-EXIT): `wordcount`'s successful report exits `0`, never `4`.
  Rationale: `wordcount` is a *report*, not a detector that surfaces an
  actionable finding the agent must adjudicate or repair. Design §9 names the
  exit-`4` boundary only for `desloppify` ("one violation past threshold exits
  4") and `novel-done`; it describes `wordcount` purely as covering "its own
  gate-boundary envelope" (§9 line 830-831), and §4.5 frames it as reporting,
  not gating. A crossed gate is *information* the report surfaces, not a
  refusal or a stale-artefact finding. The exit-`4` `ACTIONABLE_FINDING` code
  is reserved for "a finding only the agent can adjudicate or repair"
  (`exit_codes.py:33`); a healthy manuscript at 80% is neither. Therefore the
  report path is exit-`0`; exit-`3` covers state/input faults and exit-`2`
  covers usage faults, matching every other read-only checker's success path.
  Date/Author: 2026-06-24, planning round 1.

- Decision (D-TRIPWIRE): Promoting the **last** stub repurposes — does not
  abandon — the two now-empty tripwires. `test_entry_point_callable_exits_two`
  (`test_command_stubs.py:94`) is rewritten to parametrize over **all**
  `COMMAND_ENTRY_POINTS` and assert the dual: each real console-script callable
  drives a real Cyclopts app (it does **not** exit `2` via the stub path —
  under a clean argv and an absent `working/` each resolves
  `./working/state.toml` and raises the exit-`3` state channel, the same
  behaviour `tests/test_novel_state_check.py` already relies on for
  `novel-state`). The assertion becomes "every entry point is real" (no stub
  greeting on stderr, no `STUB_EXIT_CODE`), guarded by
  `assert COMMAND_ENTRY_POINTS`, so the parametrize set can never silently
  empty. The companion `test_console_scripts_install_and_exit_two`
  (`test_console_scripts_e2e.py:101`) is rewritten so
  `_assert_scripts_exit_two` becomes an all-real-commands assertion: every
  installed console-script resolves on disk and, run by absolute path under a
  tmp cwd with no `working/`, exits `3` (its real state-error path) rather than
  the stub's `2`, with the loop guarded by `assert COMMAND_NAMES`. The
  `STUB_EXIT_CODE`/`make_stub_app` factory itself stays covered by
  `test_command_result_exits_two` (parametrized on `COMMAND_NAMES` via
  `make_stub_app`, which is independent of which entry points are live).
  Rationale: The round-1 review (B1, B2) showed that the prior tasks' "add to
  `_REAL_COMMANDS`" recipe collapses to an empty parameter set on the *last*
  promotion, leaving both the callable and the installed-binary guards silently
  vacuous — the exact regression the pre-mortem warns of. Converting them to
  the dual assertion preserves a live guard over the harness's real invocation
  surface. Deleting them was the alternative; converting is strictly stronger
  (it keeps a regression net) at no extra cost, and the all-real assertion is
  the natural terminal state of a fully-promoted command set. Date/Author:
  2026-06-24, planning round 2 (resolves review B1, B2).

- Decision (D-NOGATE): Past the final (80%) gate the report represents
  "no further knitting gate" as `next_gate_distance: null` (JSON `null`, Python
  `None`) paired with an explicit boolean `next_gate: null`/sentinel field
  `next_gate_threshold: null`. Concretely the cumulative block carries
  `next_gate_threshold: float | None` (the ratio of the next not-yet-triggered
  gate, or `null` past 80%) and `next_gate_distance: int | None` (the words to
  reach it, or `null`). `null` — never a negative number and never a magic
  sentinel string — signals "no further gate". The human prose then reads "all
  knitting gates reached" instead of a distance. Rationale: The round-1 review
  (A4) required the concrete representation be fixed now so the snapshot and
  the users-guide agree and the field is stable. `null` is the idiomatic JSON
  "absent value", round-trips through the envelope unambiguously, and is
  trivially asserted in the snapshot and boundary tests. Date/Author:
  2026-06-24, planning round 2 (resolves review A4).

- Decision (D-NUM): The gate-ratio numerator is the live drafted total
  `sum(by_chapter.values())` recomputed from disk via `recount_words`, not the
  `[word_counts].current` table value read blindly. Rationale: `wordcount` is
  disk-authoritative (design §5.4: "disk is authoritative; `state.toml`
  describes disk") and a stale or hand-edited `current` must not skew the
  report. Recomputing from disk matches `_check_gate_ratio_consistent`
  (`validate.py:263`) and the live-draft oracle
  (`tests/working_corpus/_live_draft.py:117`). The novel *target* is still read
  from `[word_counts].target` (or equivalently `[novel].target_word_count`),
  which is configured, not derived from disk. Date/Author: 2026-06-24, planning
  round 1.

- Decision (D-SPLIT): The command body lives in
  `novel_ralph_skill/commands/_wordcount.py` and its pure report derivation
  plus envelope projection in
  `novel_ralph_skill/commands/_wordcount_report.py`. Rationale: Mirrors the
  `_desloppify.py` / `_desloppify_report.py` and `_recount.py` precedents,
  keeps each module within the 400-line cap, and keeps the pure aggregation
  independently testable from the CLI wiring. Date/Author: 2026-06-24, planning
  round 1.

- Decision (D-SCOPE): `wordcount` in v1 takes **no** `--chapter` flag; the only
  scope is the whole manuscript, with per-chapter detail always present in the
  report. The `@app.default` body takes no positional or keyword arguments
  beyond the four shared contract flags. Rationale: The round-1 review (A2)
  flagged `--chapter` as speculative beyond the design and roadmap. Design §4.5
  and roadmap 6.1.1 specify "per chapter and cumulatively" as the *report
  content*, not a per-chapter filter; carrying an optional, design-unmandated
  flag through the contract, the usage-error route, and the test matrix would
  add surface for no documented requirement. The whole-manuscript report
  already covers the named requirement. Dropping `--chapter` is design-exact
  and simpler; it removes the bad-`--chapter` exit-`2` row from the WI1 test
  matrix (replaced below by an unknown-`--option` exit-`2` row, which still
  exercises the Cyclopts usage channel). If a future task wants a per-chapter
  filter, that is a scoped follow-up, not a v1 hedge. Date/Author: 2026-06-24,
  planning round 2 (resolves review A2).

- Decision (D-GROUP, implementation deviation): the repurposed tripwires drive
  `novel-state` with its read-only `check` subcommand, not a bare invocation. The
  plan's D-TRIPWIRE recipe asserted that, under a clean argv and an absent
  `working/`, *every* entry point "resolves `./working/state.toml` and raises the
  exit-`3` state channel". That holds for the four commands with a `@app.default`
  body (`desloppify`, `novel-compile`, `novel-done`, `wordcount`), but
  `novel-state` is a Cyclopts command **group**: a bare invocation with no
  subcommand prints help and exits `0`, never resolving `state.toml`. Both
  repurposed tests therefore carry a small `_REAL_PATH_ARGV` map supplying the
  `check` token for `novel-state` (empty for the others), so each command reaches
  its state-resolving path and the all-real exit-`3` assertion holds for the whole
  surface. This is the same `novel-state check` route
  `tests/test_novel_state_check.py` already drives. Date/Author: 2026-06-24,
  implementation (WI3).

## Outcomes & retrospective

Completed across the three work items (2026-06-24). Against the Purpose:
`wordcount` now reports per-chapter and cumulative words, the percentage of
target, the next-gate distance, the chapter-target delta, and the 30/50/80%
triggers, derived purely from the on-disk drafts and the shared
`GATE_THRESHOLDS` constant, with a non-negative next-gate distance at every gate
boundary and `null` past the final gate. The previously stubbed exit-`2`
behaviour is gone: all five console-scripts drive real apps, the report exits `0`
and a state/input fault exits `3`. No second counter or threshold literal was
introduced; the command body and its report projection are split across two
modules, each well within the 400-line cap, and the runtime dependency set is
unchanged.

What went smoothly: the `recount_words` and `GATE_THRESHOLDS` reuse made WI2 pure
aggregation, exactly as the Surprises foresaw; the snapshot was stable on first
generation and carries no volatile field.

What deviated: D-GROUP — the plan's "every entry point exits 3 on a bare argv"
recipe did not hold for the `novel-state` command group, which needs a subcommand
to reach its state-resolving path; both repurposed tripwires now supply `check`
for `novel-state` via a small argv map. No other deviation; scope and interface
stayed within tolerances (no shared-seam change, no new dependency).

Tooling note: `make fmt` reflows unrelated Markdown across the whole `docs/` tree
(a known recurring artefact); that churn was stashed and excluded from every
commit, leaving each commit to exactly its work item's files.

## Context and orientation

This repository packages the deterministic command spine of the novel-ralph
harness: five console-scripts (`novel-state`, `novel-done`, `novel-compile`,
`desloppify`, `wordcount`) wired through one shared output contract. The reader
needs to know the following files and concepts.

- **The command registry** lives in
  `novel_ralph_skill/commands/names.py`. It records the five console-script
  names and their stub entry-point functions once; `[project.scripts]` is
  derived from it and a gate asserts they agree. The `wordcount` name is
  already present.

- **The entry-point module** `novel_ralph_skill/commands/stub.py` hosts the
  five `def novel_state()`, …, `def wordcount()` callables. Four drive real
  Cyclopts apps through the shared `_drive` helper; `wordcount()` still calls
  `make_stub_app(...)()` and exits `2`. The work promotes `wordcount()` to
  drive a real app via `_drive`, exactly as `desloppify()` does.

- **The shared contract** is in `novel_ralph_skill/contract/`. A command builds
  its app with `make_contract_app(name)` (`runner.py:52`), registers a
  `@app.default` body that returns a `CommandOutcome` (`runner.py:126`), and
  the shared `run(app, argv, RunContext(...))` wrapper (`runner.py:190`) owns
  every `sys.exit` and emits the JSON envelope. A body raises `StateInputError`
  (`runner.py:114`) for the exit-`3` channel. The envelope shape — `command`,
  `schema_version`, `ok`, `working_dir`, `result`, `messages` — is fixed in
  `contract/envelope.py`. Exit codes are `ExitCode` in `contract/exit_codes.py`
  (`SUCCESS=0`, `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`).

- **The counting helper** is
  `novel_ralph_skill/state/wordcount.py`.
  `recount_words(working_dir, manifest)` returns `(current, by_chapter)` where
  `current == sum(by_chapter.values())` and `by_chapter` is keyed by the
  zero-padded two-digit chapter string, keyed off the manifest. An absent
  `draft.md` contributes `0`; every other read fault propagates for the command
  layer to translate to exit `3`. This is the **one** counting rule; do not
  write a second.

- **The gate thresholds** are
  `GATE_THRESHOLDS: tuple[float, float, float] = (0.30, 0.50, 0.80)` in
  `novel_ralph_skill/state/validate.py:76`, re-exported from
  `novel_ralph_skill/state/__init__.py`. The validator's
  `_check_gate_ratio_consistent` (`validate.py:250`) compares each recorded
  gate boolean against `sum(by_chapter.values()) / target >= threshold`, short-
  circuiting when `target <= 0`. The live-draft oracle
  (`tests/working_corpus/_live_draft.py:98`) does the same against the disk
  drafts. `wordcount` derives the *trigger* (`ratio >= threshold`) from the
  same numerator and the same constant, but reports the geometry rather than
  checking a recorded flag.

- **The typed schema** is `novel_ralph_skill/state/schema.py`. `State` carries
  `novel.target_word_count`, `chapters: tuple[ChapterEntry, ...]` (each with
  `number`, `slug`, `title`, `target_words`), `word_counts` (`target`,
  `current`, `by_chapter`), and `gates.knitting` (`done_30/50/80`). The
  per-chapter *target* delta uses `ChapterEntry.target_words`; the novel target
  uses `word_counts.target`.

- **State loading** for a read-only checker reuses
  `novel_ralph_skill.commands.novel_state._load_or_state_error(path)` and the
  `STATE_INPUT_ERRORS` tuple and `WORKING_DIR_NAME` constant, exactly as
  `_desloppify.source_chapters` does (`_desloppify.py:194`).

- **The test corpus** lives under `tests/working_corpus/`. `WorkingTreeSpec`
  (`_specs.py:123`) declaratively specifies a whole `working/` tree, including
  `target_words`, per-chapter `draft_words`, and the `done_30/50/80` gate
  booleans; the builder renders it to a `tmp_path`. The `baseline_tree` fixture
  (used by `tests/test_desloppify_snapshots.py:94` and
  `tests/test_novel_state_check.py:74`) materialises a drafting-era tree. A
  "manuscript exactly on a gate" is built by choosing `target_words` and
  per-chapter `draft_words` so the drafted ratio is exactly `0.30`, `0.50`, or
  `0.80`.

Terms defined: a **knitting gate** is a checkpoint at 30%, 50%, and 80% of the
novel's target word count where a knitting-circle review runs. A **gate
trigger** here is the *derived* fact that the drafted-words ratio has crossed a
threshold — distinct from the recorded `[gates.knitting]` boolean, which adds
"and the review pass was integrated and logged". The **envelope** is the single
JSON object every command prints to stdout in machine mode.

## Plan of work

Three ordered, independently committable, gate-passable work items. Each ends
with `make all` passing. Work items touching no Markdown skip
`make markdownlint`/`make nixie`; WI3 touches `docs/users-guide.md` and so runs
them.

### Work item 1 — Wire the `wordcount` command skeleton onto the shared contract

Stand up the real `wordcount` Cyclopts app with the exit-code and envelope
plumbing, but with a deliberately thin report payload, so the contract wiring
is proven before the report derivation lands.

Skill to load: `python-router` → `python-data-shapes` (the `CommandOutcome` /
frozen-dataclass house style), `python-errors-and-logging` (the
`StateInputError` exit-`3` routing). Docs to read: design §3.1, §3.2, §4.5;
ADR-001 (read-only checker), ADR-003 (shared interface contract);
`docs/scripting-standards.md` (Cyclopts conventions);
`novel_ralph_skill/commands/_desloppify.py` and
`novel_ralph_skill/contract/runner.py` as the structural model.

Steps:

1. Create `novel_ralph_skill/commands/_wordcount.py`. Add `build_app()` calling
   `make_contract_app("wordcount")` with a single `@app.default` body taking no
   arguments beyond the four shared contract flags (no `--chapter`; D-SCOPE)
   and returning a `CommandOutcome`. Add a `source_state_and_drafts()` helper
   that loads `working/state.toml` via `_load_or_state_error` (exit-`3` on
   missing / unparseable), takes the manifest chapters from the loaded `State`,
   and recounts the drafts via `recount_words`, wrapping any read fault in
   `StateInputError` under `STATE_INPUT_ERRORS` (the exit-`3` channel) exactly
   as `_recount._recount_or_state_error` does. (No `WordcountUsageError` is
   needed in v1: with no command-specific argument, the only usage faults are
   the shared Cyclopts ones — an unknown `--option` — which the framework
   routes to exit-`2` without a command-level error class.)

2. For this work item the body returns a minimal `CommandOutcome` carrying
   `code=SUCCESS`, a thin `result={"target": ..., "current": ...}`, and a single
   message — a placeholder the report work item replaces. This proves the
   four-flag wiring and the fault routing end-to-end.

3. Add `tests/test_wordcount_command.py`: drive the real app through `run` (the
   `_run_capture` pattern from `tests/test_desloppify_command.py`) and assert
   the exit-code contract at its boundaries (CLI error-path tests, design §9):
   a coherent tree exits `0`; an absent `working/` exits `3`; an unparseable
   `state.toml` exits `3`; an undecodable `draft.md` exits `3`; an unknown
   `--option` exits `2` (the Cyclopts usage channel; no `--chapter` exists per
   D-SCOPE); `--help` exits `0` with no envelope. These are *red-then-green*:
   write them first, watch them fail against the stub, then pass once the app
   is wired.

Tests this work item adds:

- `tests/test_wordcount_command.py` — in-process CLI exit-code contract (unit +
  error-path), per AGENTS.md "Cover happy paths, unhappy paths, and relevant
  edge cases" and design §9 "CLI error-path tests".

Validation: from the worktree root, `make all`. Expect `pytest` to report the
new contract tests passing and the suite green. (No Markdown changed.)

Acceptance: running the wired `wordcount` against a materialised tree exits `0`
and emits a JSON envelope with `command: "wordcount"`; the four fault routes
are each distinguishable by exit code alone.

### Work item 2 — Derive and project the per-chapter and cumulative report

Replace the placeholder payload with the full §4.5 report: per chapter and
cumulatively, words, percentage of target, distance to the next knitting gate,
delta against the chapter target, and the 30/50/80% triggers — derived from the
shared counter and the shared threshold constant.

Skills to load: `python-router` → `python-iterators-and-generators` (the
per-chapter projection), `python-data-shapes` (the report dataclass);
`python-testing` (snapshot + boundary examples). Docs to read: design §4.5, §9
(verification method for a pure aggregation), §5.2 bullet 7 (the gate-ratio
rule), design lines 590-596 (trigger-versus-flag distinction);
`novel_ralph_skill/state/validate.py:250` (`_check_gate_ratio_consistent` as
the canonical ratio rule); `tests/working_corpus/_live_draft.py:98` (the
oracle).

Steps:

1. Create `novel_ralph_skill/commands/_wordcount_report.py` holding the pure
   derivation. Define a frozen report dataclass (or a typed mapping projection)
   and a keyword-only function
   `build_report(*, target, manifest, by_chapter) -> WordcountReport` (A1: the
   kw-only form matches the house `CommandOutcome(*, …)` / `RunContext(*, …)`
   style) that computes, per chapter: drafted `words`,
   `percent_of_chapter_target` (against `ChapterEntry.target_words`), and
   `delta_against_target` (`words - target_words`); and cumulatively: `current`
   (`sum(by_chapter.values())`), `percent_of_target` (against the novel
   `target`), the three `gate_triggered_30/50/80` booleans
   (`ratio >= threshold` for each `GATE_THRESHOLDS` element),
   `next_gate_threshold` (the ratio of the next not-yet-triggered gate, or
   `None` past 80%), and `next_gate_distance` (the words needed to reach
   `next_gate_threshold`, or `None` past 80%; never a negative number, and
   `None` — JSON `null` — when no further gate remains, per D-NOGATE). The
   "next" gate is the lowest threshold the drafted ratio has **not** yet reached
   (`ratio < threshold`), so at a ratio of exactly `0.30` the 30% gate is
   *triggered* and the *next* gate is `0.50` (distance > 0), not `0.30`
   (distance 0) — pin this `>=`-trigger / `<`-next split (A3). Short-circuit
   the ratio geometry when `target <= 0` (mirror `validate.py:261`): no
   triggers, `next_gate_threshold` and `next_gate_distance` both `None`.

2. The numerator is `sum(by_chapter.values())` recomputed from disk (D-NUM); the
   thresholds come from `GATE_THRESHOLDS` imported from
   `novel_ralph_skill.state` (Constraint "Single gate-threshold source"). Do
   not re-spell `0.30/0.50/0.80`.

3. Add a `report_outcome(report)` projection returning the `CommandOutcome`:
   `result` carries the machine payload (the per-chapter list and the
   cumulative block); `messages` carries human prose (e.g. "drafted N of T
   words (P% of target); next gate at G words (D to go)"). Exit `0` (D-EXIT).
   Wire `_wordcount.py`'s body to call `build_report` then `report_outcome`.

4. Tests — snapshot the machine-mode envelope plus boundary examples (design §9:
   "snapshot coverage of their envelope plus a handful of boundary examples (a
   manuscript exactly on a gate)", roadmap 6.1.1: "snapshot coverage of the
   envelope plus boundary examples … not a full property-based or behavioural
   suite"):

   - `tests/test_wordcount_snapshots.py` — model on
     `tests/test_desloppify_snapshots.py`: snapshot the whole-manuscript machine
     envelope for a representative drafting-era tree, paired with the volatile-
     field guard (`_assert_no_volatile_fields`) and semantic assertions
     (the per-chapter table sums to `current`; `next_gate_distance` is
     non-negative; trigger booleans match `ratio >= threshold`). Pair, never
     snapshot-only (AGENTS.md).
   - Boundary examples (the §9 / roadmap success criterion): build
     `WorkingTreeSpec` trees drafted to *exactly* 30%, 50%, and 80% of the
     target (choose `target_words` and `draft_words` so the ratio is exactly the
     threshold), and assert each corresponding gate is reported "just reached"
     (`gate_triggered_NN: true`) and the next-gate distance is non-negative. At
     the exactly-30% tree assert `next_gate_threshold == 0.50` and
     `next_gate_distance > 0` (not the 30% gate at distance `0`) — this pins the
     `>=`-trigger / `<`-next tie-break so a `>` vs `>=` slip in the "next"
     selection is caught, not just non-negativity (A3). Add one tree drafted
     *past* 80% and assert the D-NOGATE shape explicitly: `gate_triggered_80:
     true`, `next_gate_threshold` is `null` and `next_gate_distance` is `null`
     (never a negative number). Add one `target == 0` tree and assert the
     short-circuit (no triggers, both `next_gate_*` fields `null`, no division).
     Add the trigger-versus-flag test from the Risks: a tree whose drafted ratio
     crosses 30% but whose `done_30` flag is `false`, asserting the report shows
     the *trigger* reached and never echoes the recorded flag.
   - `tests/test_wordcount_report.py` — unit tests for `build_report` in
     isolation (the pure aggregation): per-chapter delta arithmetic, cumulative
     percentage, and `next_gate_distance` at and between thresholds. Assert the
     derived triggers agree element-wise with `GATE_THRESHOLDS` so a future
     threshold edit propagates (Risk mitigation).

   No `hypothesis` property suite and no `pytest-bdd` behavioural feature for
   this command: roadmap 6.1.1 and design §9 explicitly scope it to snapshot +
   boundary examples because the command is a pure aggregation. (If a reviewer
   later wants a property over the ratio arithmetic, that is a
   tolerance-bounded addition — escalate rather than pre-emptively adding it.)

Validation: `make all`. Expect the new snapshot, boundary, and unit tests to
pass; run `pytest` once to generate the `.ambr` snapshot, review it, and commit
it. (No Markdown changed.)

Acceptance: at a tree drafted exactly to a gate threshold the report shows that
gate "just reached" and a non-negative next-gate distance; the per-chapter
table sums to `current`; no second counter or threshold literal exists.

### Work item 3 — Promote `wordcount` to the real-command set and update the docs

Move `wordcount` out of the "still stubbed" set everywhere the test suite and
the docs assert it, and prove the installed binary works end-to-end.

Skills to load: `python-router` → `python-testing` (the e2e and tripwire edits);
`en-gb-oxendict` (the users-guide prose). Docs to read: ADR-003, ADR-004
(console-scripts distribution), ADR-006 (POSIX e2e policy); design §9;
`tests/test_desloppify_e2e.py` and `tests/test_console_scripts_e2e.py` as the
e2e model; `tests/test_novel_state_check.py` (the precedent for a real callable
exiting `3` on an absent `working/`); `docs/users-guide.md:85-90`.

This work item promotes the **last** of the five stubs (T-LAST). That is a
different operation from the prior promotions: simply adding `"wordcount"` to
each `_REAL_COMMANDS` set empties the derived "still stubbed" collections and
silently neuters two tests (review B1, B2). Steps 2 and 3 therefore *repurpose*
those two tests into all-real-commands assertions, per D-TRIPWIRE. There is no
edit to `tests/test_stub.py`: it is not a tripwire (T-STUB; review B3).

Steps:

1. In `novel_ralph_skill/commands/stub.py`, change `def wordcount()` from
   `make_stub_app(...)()` to drive the real app via `_drive`, exactly as
   `desloppify()` does (deferred in-body import of `_wordcount`). Update the
   module docstring's "only `wordcount` remains a stub" sentence to record that
   all five entry points now drive real apps.

2. Repurpose `tests/test_command_stubs.py` (resolves B1). Add `"wordcount"` to
   `_REAL_COMMANDS` (line 37) — which makes `STILL_STUBBED_ENTRY_POINTS` (line
   43) empty — and **rewrite** `test_entry_point_callable_exits_two` (line 94)
   instead of leaving it to collect zero items. The replacement parametrizes
   over **all** `COMMAND_ENTRY_POINTS.items()` (guarded by
   `assert COMMAND_ENTRY_POINTS` so it can never silently empty) and asserts
   the dual of the old stub claim: each real console-script callable drives a
   real Cyclopts app, not the stub. Concretely, under a clean argv
   (`monkeypatch.setattr(sys, "argv", [name])`) and a cwd with no `working/`
   (`monkeypatch.chdir(tmp_path)`), the callable raises `SystemExit` with code
   `ExitCode.STATE_ERROR` (3) — the real state-error path every command takes
   when `./working/state.toml` is absent — and its stderr carries **no** stub
   greeting and no `STUB_EXIT_CODE`. This is the same real-callable behaviour
   `tests/test_novel_state_check.py` already pins for `novel-state` under an
   explicit `chdir`. Rename the test to reflect the new assertion (e.g.
   `test_entry_point_callable_drives_real_app`) and update the now-stale
   `_REAL_COMMANDS` comment block (lines 24-36) to state that all five entry
   points are real. Keep `STILL_STUBBED_ENTRY_POINTS` only if a reader
   benefits; otherwise delete it with its now-dead parametrize. The
   `make_stub_app` factory and `STUB_EXIT_CODE` remain covered by
   `test_command_result_exits_two` (parametrized on `COMMAND_NAMES` through
   `make_stub_app`, independent of which entry points are live),
   `test_unknown_option_exits_one`, and `test_meta_flags_exit_zero`, so the
   stub factory itself stays tested.

3. Repurpose `tests/test_console_scripts_e2e.py` (resolves B2). Add
   `"wordcount"` to `_REAL_COMMANDS` (line 42) — which makes
   `_STILL_STUBBED_NAMES` (line 48) empty — and **rewrite** the now-dead
   `_assert_scripts_exit_two` / `test_console_scripts_install_and_exit_two`
   pair so the slow wheel-build does not assert nothing. The replacement loops
   over **all** `COMMAND_NAMES` (guarded by `assert COMMAND_NAMES`) and asserts
   every installed console-script is a real app: each script resolves on disk
   and, run **by absolute path** through the `single_program_catalogue` fixture
   under a tmp cwd that contains no `working/` (set `ExecutionContext(cwd=...)`
   as `tests/test_desloppify_e2e.py` does), exits `3` — the real state-error
   path — rather than the stub's `2`, with no `Traceback` on stderr. Rename the
   helper and test to reflect the all-real assertion (e.g.
   `_assert_scripts_real_state_error` /
   `test_console_scripts_install_and_run_real`), and update the module
   docstring (lines 1-21) and the `_REAL_COMMANDS` comment (lines 35-41) to
   state that all five scripts now drive real apps. Keep the
   `@pytest.mark.slow` / `@pytest.mark.timeout(180)` / POSIX-skip envelope.
   (Deleting the test is the alternative; converting keeps a live
   install-and-run guard over the whole command surface — D-TRIPWIRE.)

4. Add `tests/test_wordcount_e2e.py` modelled on `tests/test_desloppify_e2e.py`:
   build a wheel, install into a throwaway venv, materialise a `working/` tree
   drafted to a known ratio, and run the installed `wordcount` **by absolute
   path** through the `single_program_catalogue` fixture (cuprum 0.1.0
   allowlists the exact absolute-path `Program` and runs it via asyncio
   subprocess — the registration is the execution gate, `cuprum/sh.py:make`).
   Assert exit `0` and that the stdout JSON envelope carries the cumulative
   report and the expected gate triggers. Mark `@pytest.mark.slow`,
   `@pytest.mark.timeout(180)`, and `skipif(os.name != "posix")` (ADR-006), as
   the desloppify e2e does. This is the AGENTS.md "add end-to-end tests where a
   change affects … command-line behaviour" requirement and the design §9
   installed-binary coverage.

5. Update `docs/users-guide.md`: replace the "`wordcount` is still a **stub**"
   paragraph (lines 87-90) with a description of the real `wordcount` report
   (per-chapter and cumulative words, percentage of target, next-gate distance —
   `null` past the final 80% gate (D-NOGATE) — chapter-target delta, and the
   30/50/80% triggers), in en-GB Oxford spelling, wrapped at 80 columns. Note
   it is read-only, takes no per-chapter flag in v1 (D-SCOPE), and exits `0` on
   a report and `3` on a state/input fault (an unknown `--option` is the shared
   exit-`2` usage channel). Add a short `wordcount` section near the `recount`
   section if the guide's structure warrants it.

Tests this work item adds/updates:

- `tests/test_wordcount_e2e.py` — new installed-binary e2e (slow, POSIX-only).
- `tests/test_command_stubs.py` — `_REAL_COMMANDS` gains `"wordcount"`;
  `test_entry_point_callable_exits_two` is *repurposed* into an
  all-real-callables assertion (exit `3` with no working tree), guarded
  non-empty (resolves B1; D-TRIPWIRE).
- `tests/test_console_scripts_e2e.py` — `_REAL_COMMANDS` gains `"wordcount"`;
  `test_console_scripts_install_and_exit_two` is *repurposed* into an
  all-real-scripts install-and-run assertion (exit `3` with no working tree),
  guarded non-empty (resolves B2; D-TRIPWIRE).
- `tests/test_stub.py` is **not** touched: it asserts only
  `hello() == "hello from Python"` and references no command stub set (T-STUB;
  resolves B3).

Validation: `make all`, then `make markdownlint` and `make nixie` (Markdown
changed). Expect the e2e to pass on POSIX (or skip off POSIX), the tripwires to
pass with `wordcount` in the real set, and markdownlint/nixie clean.

Acceptance: the installed `wordcount` console-script reports and exits `0` over
a real wheel/venv; no test asserts `wordcount` is stubbed; the users-guide
documents the real command.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-1-1`.

Per work item:

```bash
# (after each work item's edits)
make all
```

For Work item 3 (Markdown changed):

```bash
make all
make markdownlint
make nixie
```

To generate/refresh the Work-item-2 snapshot once and review it before
committing:

```bash
mkdir -p .uv-cache .uv-tools; \
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools \
  uv run pytest tests/test_wordcount_snapshots.py --snapshot-update -q
# then review tests/__snapshots__/test_wordcount_snapshots.ambr and re-run
# `make test` without --snapshot-update to confirm it is stable.
```

Expected `make all` tail on success (illustrative):

```plaintext
... N passed in T s
```

Commit after each work item with an en-GB Oxford-spelled message referencing
roadmap task 6.1.1 (commit-message skill; never `-m`).

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` green, including the new
  `tests/test_wordcount_command.py`, `tests/test_wordcount_report.py`,
  `tests/test_wordcount_snapshots.py` (with a committed `.ambr`), and
  `tests/test_wordcount_e2e.py`; the three stub tripwires pass with `wordcount`
  in the real-command set. Each new test fails before its work item's code
  lands and passes after (red-green).
- Lint/typecheck: `make lint` (Ruff, Interrogate 100% docstring coverage,
  Pylint) and `make typecheck` (`ty`) clean over `novel_ralph_skill tests`.
- Format: `make check-fmt` clean.
- Markdown (WI3 only): `make markdownlint` and `make nixie` clean.

Quality method (how we check): `make all` is the aggregate gate (it runs
`build check-fmt lint typecheck test`); for the Markdown-touching work item
also run `make markdownlint` and `make nixie`.

Behavioural acceptance (a human can verify): materialise a `working/` tree
drafted to exactly 80% of an 80 000-word target, run the installed `wordcount`,
and observe `gate_triggered_80: true`, a non-negative `next_gate_distance`, the
per-chapter table summing to `current`, and exit `0`. Materialise a tree
drafted to exactly 50% and observe `gate_triggered_50: true`,
`gate_triggered_80: false`. Remove `working/` and observe exit `3`.

## Idempotence and recovery

Every work item is additive and re-runnable. The command writes nothing to
disk, so running `wordcount` any number of times is side-effect-free. The
snapshot is regenerated deterministically (`--snapshot-update`) and reviewed
before commit; if it churns, narrow the captured envelope until a failure
identifies a real contract change (AGENTS.md). The tripwire edits are
mechanical and reversible. No destructive step exists; no rollback path is
needed beyond `git restore`.

## Interfaces and dependencies

Use these existing, verified interfaces; introduce no new external dependency
(runtime stays `["cyclopts", "tomlkit"]`).

- `novel_ralph_skill.state.recount_words(working_dir, manifest)` returning
  `tuple[int, Mapping[str, int]]` (taking the working dir and the
  `Sequence[ChapterEntry]` manifest) — the one counting rule (verified in
  `state/wordcount.py`).
- `novel_ralph_skill.state.GATE_THRESHOLDS: tuple[float, float, float]` —
  `(0.30, 0.50, 0.80)` (verified in `state/validate.py:76`, re-exported from
  `state/__init__.py:84`).
- `novel_ralph_skill.contract.runner.make_contract_app(name) -> cyclopts.App`,
  `CommandOutcome(*, code, result, messages)`,
  `StateInputError(EnvelopeMessagesError)`, `RunContext`, `run` (verified in
  `contract/runner.py`).
- `novel_ralph_skill.commands.novel_state._load_or_state_error(path) -> State`,
  `STATE_INPUT_ERRORS`, `WORKING_DIR_NAME` (verified used by `_desloppify` and
  `_recount`).

New interfaces this plan creates:

- In `novel_ralph_skill/commands/_wordcount.py`:

  ```python
  def build_app() -> cyclopts.App: ...
  def source_state_and_drafts() -> tuple[
      int, tuple[ChapterEntry, ...], cabc.Mapping[str, int]
  ]: ...
  ```

  No command-specific usage-error class is created in v1: with no `--chapter`
  argument, the only usage fault is the shared Cyclopts unknown-option route to
  exit `2` (D-SCOPE).

- In `novel_ralph_skill/commands/_wordcount_report.py`:

  ```python
  def build_report(
      *,
      target: int,
      manifest: cabc.Sequence[ChapterEntry],
      by_chapter: cabc.Mapping[str, int],
  ) -> WordcountReport: ...
  def report_outcome(report: WordcountReport) -> CommandOutcome: ...
  ```

The `cuprum` library is used only by the installed-binary e2e
(`tests/test_wordcount_e2e.py`) via the existing `single_program_catalogue`
fixture and the absolute-path `Program` pattern proven in
`tests/test_desloppify_e2e.py`; cuprum 0.1.0 allowlists the exact registered
`Program` (the registration is the execution gate, `cuprum/sh.py:make` →
`catalogue.lookup`). No command body uses cuprum, because v1 commands shell out
to nothing (design §9 line 836; `pyproject.toml:8`).

## Revision note

Round 2 (2026-06-24), after Logisphere design review r1
(`docs/execplans/roadmap-6-1-1.review-r1.md`).

What changed and why:

- Resolved B1 (review): `wordcount` is the **last** stub, so adding it to
  `_REAL_COMMANDS` empties `STILL_STUBBED_ENTRY_POINTS` and silently skips
  `test_entry_point_callable_exits_two`. WI3 step 2 now *repurposes* that test
  into an all-real-callables assertion (every entry point drives a real app and
  exits `3` with no `working/`), guarded `assert COMMAND_ENTRY_POINTS` so it
  can never silently empty. Added Decision Log D-TRIPWIRE and a high-severity
  Risk.
- Resolved B2 (review): the same empty-set collapse made
  `test_console_scripts_install_and_exit_two` a no-op wheel build. New WI3 step
  3 repurposes it into an all-real-scripts install-and-run assertion (every
  installed script exits `3` with no `working/`), guarded
  `assert COMMAND_NAMES`.
- Resolved B3 (review): `tests/test_stub.py` is a phantom tripwire (it only
  asserts the package greeting). Removed it from the Risks entry, WI3 step 2,
  and the WI3 deliverables list; added Surprises entry T-STUB recording why it
  is not touched. The two live tripwires are `test_command_stubs.py` and
  `test_console_scripts_e2e.py` only.
- Resolved A1: `build_report` is now keyword-only everywhere
  (`build_report(*, target, manifest, by_chapter)`), matching the house style.
- Resolved A2: dropped the speculative `--chapter` flag for v1 (D-SCOPE
  rewritten from a hedge to a decision); removed the bad-`--chapter` exit-`2`
  test row, the `WordcountUsageError` class, the `chapter` parameter on
  `source_state_and_drafts`, and the `--chapter` mention in the exit-routing
  constraint and the users-guide step.
- Resolved A3: WI2 now pins the `>=`-trigger / `<`-next tie-break — at exactly
  30% the next gate is 0.50 with distance > 0, asserted explicitly.
- Resolved A4: fixed the "no further knitting gate" representation to
  `next_gate_threshold: null` + `next_gate_distance: null` (Decision Log
  D-NOGATE); propagated into the report fields, the past-80% and `target == 0`
  boundary tests, and the users-guide step.

How it affects remaining work: the three work items are unchanged in count and
order; WI3 gains one step (now five steps) because the two tripwire tests are
repurposed rather than abandoned. No new dependency, no interface change beyond
the now-simpler `wordcount` body (no `--chapter`, no usage-error class).
