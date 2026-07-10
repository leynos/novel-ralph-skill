# Implement the shared compile-and-hash routine and the compile-divergence clause

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (implemented 2026-06-24; all five work items committed, `make
all` green at HEAD).

## Purpose / big picture

`novel-done` ships today with a **sound but incomplete** `compile_consistent`
clause: roadmap task 3.1.1 made the clause existence-only
(`compile_consistent_exists(working_dir)`,
`novel_ralph_skill/state/done_predicate.py:211-220`). A *present* `compiled.md`
holds and an *absent* one does not, so an absent compile can never be declared
"done". But a *present-but-stale* `compiled.md` — one that no longer matches the
chapter drafts — still passes. That is the named unsoundness window (Risk
R-STALE in `docs/execplans/roadmap-3-1-1.md:179-191`): an otherwise-complete tree
with a stale compile currently exits `0` ("done") when it should not.

This task closes that window. It swaps the existence-only half for the full
**content comparison** against the drafts, so a stale `compiled.md` whose header
count and word total coincidentally match the drafts is still reported as
divergent (design §2.3 "compile fidelity"; §4.2 lines 349-356). It then adds the
exit-code carve-out the design §4.2 names (lines 318-327): when
`compile_consistent` is the *sole* unmet clause, the manuscript is otherwise
complete and the only obstacle is a stale compile — an **actionable** finding —
so `novel-done` exits `4` (matching `novel-compile --check`, design §4.3) rather
than looping at exit `1`. While any *drafting* clause is still unmet, compile
staleness is expected mid-draft and the predicate stays at exit `1`.

This is roadmap task 3.1.2 (`docs/roadmap.md` §3.1, lines 892-910). After this
change, a user running `novel-done` from a project's process directory over an
otherwise-complete tree whose `compiled.md` is stale sees:

```console
$ novel-done; echo "exit=$?"
{"command": "novel-done", "schema_version": 1, "ok": false,
 "working_dir": "working",
 "result": {"phase_is_done": true, "final_pass_complete": true,
            "all_chapters_flagged": true, "knitting_gates_passed": true,
            "compile_consistent": false, "no_unresolved_blockers": true},
 "messages": ["compile_consistent is false"]}
exit=4
```

(the stdout is a single physical line; it is wrapped here only to fit the
margin). Observe `compile_consistent: false` is now driven by **content**, not
existence, and the exit code is `4` — the actionable carve-out — because
`compile_consistent` is the only false clause. A *mid-draft* tree whose
`compiled.md` is also stale still exits `1`, because a drafting clause is unmet
too. The `result` reports a single `compile_consistent` boolean, never the
per-chapter content it compared, so the payload size is fixed regardless of the
chapter count.

### What this task does and does not touch (the 3.1.2 / 3.1.3 boundary)

This boundary is deliberate and the implementer must respect it:

- **3.1.2 (this task)** swaps the `compile_consistent` clause from
  existence-only to the full content comparison, reusing the **already-shared**
  draft-join routine (`present_draft_bodies` + `concatenate_drafts` in
  `compile_model.py`), and adds the exit-`4`-vs-exit-`1` carve-out in the command
  body. It changes the *clause* and the *exit-code mapping*; it does not refactor
  the §5.4 disk-evidence detector.
- **3.1.3 (a separate, later roadmap task,** `docs/roadmap.md:911-934`**)** then
  factors *one* `compiled_matches_drafts(state, working_dir)` helper into
  `compile_model.py`, reconciling the **absent-file polarity** once, and has both
  the §5.4 detector (`disk_evidence._check_compiled_matches_drafts`) and the
  3.1.2 clause consume it. 3.1.2 must therefore implement the clause's comparison
  as a **single named function** the 3.1.3 unification can absorb in one edit
  (Decision D-CLAUSE-FN), not inline it into `evaluate_done`.

So 3.1.2 deliberately ships a *second* compiled-vs-drafts comparison (the clause)
beside the §5.4 detector's, differing only in absent-file polarity; 3.1.3 is the
roadmap task that removes that duplication. Re-implementing 3.1.3's unification
here would broaden this task past its roadmap boundary — do not.

This behaviour is verified through the new behavioural scenario in
`tests/features/novel_done.feature` (a stale-but-count-matching compile reported
divergent and exiting `4`; a mid-draft stale compile exiting `1`), the
predicate-truthfulness property test, and the machine-mode envelope snapshot,
all described under "Validation and acceptance".

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **The deterministic-and-judgemental boundary is absolute (ADR-001; design
  §1, §3.3).** `novel-done` remains a *checker*: it detects and reports, makes
  no narrative judgement, and writes nothing to disk on any path (design §3.3
  puts `novel-done` in the read-only checker column). The compile comparison
  reads `compiled.md` and the drafts; it never regenerates or writes
  `compiled.md` (that is `novel-compile`'s job, §4.3). It mutates no `state.toml`
  and creates no file.

- **The single shared compile-and-hash routine is mandatory (design §2.3 lines
  117-122, §4.3 lines 383-385).** The clause's content comparison **must** reuse
  `novel_ralph_skill.state.compile_model.present_draft_bodies` (the ordered
  draft-body read rule, `compile_model.py:38-78`) and
  `compile_model.concatenate_drafts` (the join rule, `compile_model.py:81-101`).
  These are *already* the routine the §5.4 detector
  `disk_evidence._check_compiled_matches_drafts` (`disk_evidence.py:167-188`)
  uses, so `novel-done` and the detector cannot disagree on what "compiled
  matches drafts" means. Do **not** invent a second join, a second draft read
  rule, or a second separator constant; do **not** add `hashlib` (see
  D-BYTE-COMPARE).

- **"Hash" here means content equality, satisfied by a byte comparison
  (D-BYTE-COMPARE).** Design §2.3/§4.2/§4.3 phrase the routine as
  "compile-and-hash" and "compare its hash". The §5.4 detector already realizes
  that comparison as a direct byte equality
  (`compiled.read_text(...) == expected`, `disk_evidence.py:183`) — no digest is
  computed. Because the clause needs only a *boolean* verdict over the same two
  in-memory strings, a byte comparison is the content-equality the design names;
  introducing a `hashlib` digest would be a *second* comparison mechanism the
  detector does not use and would risk drift. The clause therefore compares bytes
  exactly as the detector does. This is recorded so the design's "hash" wording
  is not transcribed into a gratuitous digest.

- **The clause's absent-file polarity is "absent → false" (design §4.2; B1 from
  3.1.1).** The clause keeps the existence half it already has: an *absent*
  `compiled.md` makes `compile_consistent` false (so an absent compile can never
  be declared done). This is the **opposite** polarity to the §5.4 detector,
  whose `_check_compiled_matches_drafts` treats an absent `compiled.md` as
  *vacuously satisfied* (`disk_evidence.py:180-181`; "nothing to diverge from").
  The two polarities are correct for their different jobs and must not be
  conflated in 3.1.2; 3.1.3 reconciles them in one helper. The new clause
  function therefore: absent `compiled.md` → `False`; present and byte-equal to
  the recomputed concatenation → `True`; present and not byte-equal → `False`.

- **The exit-`4` carve-out is exclusive to a sole *stale-present* compile failure
  (design §4.2 lines 318-327, §3.2; ADR-003).** `novel-done` exits `4` **iff**
  `compile_consistent` is the *only* false clause **and** `compiled.md` is present
  (a stale-present compile) — i.e.
  `failed_clause_names == ("compile_consistent",) and compiled_path.exists()` (the
  conservative reading, D-CARVE). If any other clause is also false, or if the
  sole failure is an *absent* `compiled.md`, the exit stays `1` (the benign
  negative the harness loops on): mid-draft compile staleness is expected, and an
  absent compile must not be reported as a regenerable stale one (this preserves
  the B1 fix `test_absent_compile_exits_one_not_zero` pins,
  `tests/test_novel_done_command.py:100-111`). If every clause holds, exit `0`.
  The exit-`4` member is `ExitCode.ACTIONABLE_FINDING`
  (`contract/exit_codes.py:32-34`), already used by `novel-state check`
  (`novel_state.py:235`). `ok` stays the `is_ok` biconditional — `True` iff exit
  `0` — so an exit-`4` envelope carries `ok: false`.

- **The exit-code table is otherwise unchanged (ADR-003; design §3.2).** Exit
  `0` when every clause holds; exit `1` when a *drafting* clause is unmet (alone
  or alongside a stale compile); exit `2` for a usage error (the runner's
  `CycloptsError` arm); exit `3` for a state/input error (missing/unparseable
  `state.toml`, an unreadable chapter artefact — including, now, an unreadable
  `compiled.md` or `draft.md`, per D-FAULT); exit `4` only for the sole-compile
  carve-out above.

- **The fault boundary is the established one (D-FAULT, inherited from
  3.1.1).** Reading the drafts and `compiled.md` for the comparison follows the
  same rule as every other disk-aware clause: an *absent* artefact is benign
  (an absent `compiled.md` is a false clause; an absent `draft.md` contributes
  the empty body, exactly as `present_draft_bodies` already does,
  `compile_model.py:76`); every *other* read fault (`PermissionError`,
  `IsADirectoryError`, `UnicodeDecodeError` on an undecodable body) propagates
  for the command layer to translate to exit `3`. `present_draft_bodies` already
  documents and implements exactly this (`compile_model.py:60-74`).

- **The shared contract is fixed (ADR-003; design §3.1, §3.2).** The command
  emits the common envelope through `novel_ralph_skill.contract.runner.run`.
  `result` carries the six per-clause booleans (the `DoneClauses` rendered in
  §4.2 order); `messages` is human prose the harness never parses. The envelope
  `schema_version` is `1`. The `result` reports the single `compile_consistent`
  boolean, never per-chapter content, so the payload is bounded as the chapter
  count grows (design §4.2 lines 357-361).

- **No external process; cuprum is out of scope (design §4 line 269).**
  `novel-done` shells out to nothing; filesystem work uses `pathlib`. Confirmed
  against the locked cuprum source: `cuprum.catalogue.ProgramCatalogue`
  (`/data/leynos/Projects/cuprum/cuprum/catalogue.py`) and
  `cuprum.program.Program` (`/data/leynos/Projects/cuprum/cuprum/program.py`)
  exist to run allow-listed external programs, none of which this command
  invokes, so no cuprum API is load-bearing here. The runtime dependency set
  stays `cyclopts` + `tomlkit` (`pyproject.toml:8`); do not add cuprum.

- **No signature change to shared seams in use.** `present_draft_bodies`,
  `concatenate_drafts`, `DoneClauses`, `evaluate_done`, `CommandOutcome`,
  `ExitCode`, `is_ok`, `build_envelope`, `_load_or_state_error`,
  `STATE_INPUT_ERRORS` keep their existing signatures. A *new* clause function in
  `done_predicate.py` and the exit-`4` decision in `_novel_done.py` are the only
  behavioural changes; the existence-only `compile_consistent_exists` is
  superseded (see D-CLAUSE-FN for its fate).

- **Style and quality gates (AGENTS.md).** No module exceeds 400 lines.
  Comments and prose use en-GB Oxford spelling (`-ize`/`-yse`/`-our`). Every
  public function carries a docstring with an example where it aids a caller
  (the `interrogate` gate enforces presence). All work passes `make all`.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- **Scope.** If the implementation requires changing more than 12 files or more
  than 600 net lines of code, stop and escalate. (This is a focused swap-plus-
  carve-out, smaller than 3.1.1's build-from-scratch.)
- **Interface.** If delivering 3.1.2 requires changing the signature of any
  shared seam already in use — `present_draft_bodies`, `concatenate_drafts`,
  `DoneClauses`, `evaluate_done`, `CommandOutcome`, `ExitCode`, `is_ok`,
  `build_envelope`, `_load_or_state_error`, `STATE_INPUT_ERRORS`, the
  `_check_compiled_matches_drafts` detector, the existing corpus specs — stop and
  escalate. New helpers beside them are fine; changing in-use ones, or touching
  the §5.4 detector (that is 3.1.3's job), is not.
- **Dependencies.** If any new runtime or dev dependency appears necessary, stop
  and escalate (runtime is fixed at `cyclopts` + `tomlkit`; the dev set already
  carries `pytest`, `pytest-bdd`, `hypothesis`, `syrupy`, `pytest-timeout`,
  `pytest-xdist`).
- **The 3.1.3 boundary.** If closing the clause appears to *require* unifying the
  two compiled-vs-drafts comparisons into one shared helper now (rather than in
  3.1.3), stop and escalate rather than absorbing 3.1.3's scope silently.
- **Exit-code semantics.** If the sole-compile carve-out cannot be expressed
  without an undecided design fork — for example, if it is unclear whether a
  stale compile *plus* an unmet `no_unresolved_blockers` should exit `4` or `1`
  — stop and present the options with trade-offs. (The plan reads §4.2 as: exit
  `4` only when `compile_consistent` is the *sole* failure; any other unmet
  clause keeps exit `1`. If review disputes this reading, escalate.)
- **Iterations.** If `make all` still fails after 3 fix attempts on a single
  work item, stop and escalate.

## Risks

Known uncertainties, with mitigations.

- Risk (R-CARVE-MISFIRE): the exit-`4` carve-out fires when it should not (a
  mid-draft stale compile mis-reported as actionable, sending the harness to
  regenerate instead of continuing to draft; or an *absent* `compiled.md`
  mis-reported as actionable, telling the harness to regenerate a compile that
  was never built) or fails to fire when it should (a sole stale-present compile
  reported as benign `1`, so the harness loops on a tree it could fix).
  Severity: high (this is the carve-out's entire purpose). Likelihood: medium.
  Mitigation: the exit decision is the single explicit conservative predicate
  `clauses.failed_clause_names == ("compile_consistent",) and
  (root / "manuscript" / "compiled.md").exists()` (D-CARVE) — the sole unmet
  clause is `compile_consistent` **and** the compile is present-but-stale, so an
  *absent* sole-failure compile stays exit `1` (preserving the B1 fix pinned by
  `tests/test_novel_done_command.py:100-111`). A command-level test pins **all**
  directions — a sole stale-present compile exits `4`; a sole *absent* compile
  exits `1`; a stale compile alongside *each* other unmet clause exits `1` — and
  a behavioural scenario proves the mid-draft case stays at `1`.

- Risk (R-STALE-MISS): the content comparison fails to catch a stale compile
  whose header count and word total coincidentally match the drafts — the exact
  failure mode the task exists to close (design §2.3 line 121; §4.2 line 354).
  Severity: high. Likelihood: low (byte comparison cannot be fooled by matching
  counts). Mitigation: the corpus already models a stale compile as a **verbatim
  string** in `WorkingTreeSpec.compiled` (`_specs.py:198, 261-264`,
  `COMPILED_AUTO` writes the hash-equal concatenation, any other string is
  written verbatim). Work item 2 adds a stale-but-count-matching spec — a
  `compiled.md` body with the same `len(text.split())` token count and the same
  per-chapter header count as the drafts but altered non-whitespace bytes, and a
  test pins it divergent. This is the predicate-truthfulness property the design
  names.

- Risk (R-EXISTENCE-REGRESS): swapping the clause silently re-opens the absent-
  compile soundness fix (B1) — an absent `compiled.md` is mistakenly read as
  "vacuously consistent" (the §5.4 detector's polarity) and exits `0`. Severity:
  high (re-introduces the exit-`0` lie 3.1.1 closed). Likelihood: low.
  Mitigation: the new clause function keeps the explicit "absent → False"
  branch; the existing 3.1.1 test that pins absent-`compiled.md` to a false
  clause / benign exit is retained and extended (D-CLAUSE-FN), and a property/
  unit test asserts the absent case stays `False` while the §5.4 detector's
  absent case stays vacuously satisfied — the two polarities pinned side by side.

- Risk (R-CLAUSE-FN-LOC): placing the new comparison so that 3.1.3 cannot absorb
  it in one edit, forcing 3.1.3 to re-cut the seam. Severity: low. Likelihood:
  low. Mitigation: D-CLAUSE-FN places the comparison in one named function in
  `done_predicate.py` whose body is exactly the detector's recompute-and-compare
  with the inverted absent-file polarity, so 3.1.3's `compiled_matches_drafts`
  helper is a drop-in the clause calls with its polarity flag.

- Risk (R-SNAPSHOT-CHURN): the new exit-`4` path or the swapped clause re-
  baselines an existing snapshot. Severity: low. Likelihood: low (verified). The
  3.1.1 snapshot suite (`tests/test_novel_done_snapshots.py`) pins an all-hold
  tree (exit `0`, unchanged) and a one-clause-fails tree. If that failer tree's
  failed clause is `compile_consistent` via an *absent* compile, its envelope is
  unchanged (absent → false in both 3.1.1 and 3.1.2); the *new* exit-`4` path is
  a *stale-present* compile, a distinct tree. Mitigation: Work item 4 adds a
  **new** snapshot for the sole-stale-compile exit-`4` envelope rather than
  mutating the existing two; a test asserts the existing snapshots are
  byte-stable. If the existing one-clause-fails snapshot happened to use a
  present-but-stale compile (it does not — 3.1.1 had no stale-compile spec), it
  would re-baseline; verified it does not.

- Risk (R-FAULT-COMPILE): an unreadable `compiled.md` or `draft.md`
  (`PermissionError`, undecodable bytes) is swallowed as a false clause and
  misreported as exit `1`/`4` instead of exit `3`. Severity: medium. Likelihood:
  low. Mitigation: `present_draft_bodies` already propagates every non-absent
  read fault (`compile_model.py:60-74`); the clause's `compiled.md` read uses the
  same UTF-8 read and lets non-`FileNotFoundError` faults propagate, which the
  command body already wraps under `STATE_INPUT_ERRORS` → `StateInputError`
  (`_novel_done.py:65-69`). A negative test pins an undecodable `compiled.md` to
  exit `3`.

## Progress

- [x] Work item 1 (2026-06-24): swapped the `compile_consistent` clause to the
  shared content comparison (pure engine), retiring the existence-only half.
  `compile_consistent(state, working_dir)` reuses
  `present_draft_bodies`/`concatenate_drafts`; `compile_consistent_exists` is
  removed and `evaluate_done` points at the new function. Tests replaced the
  orphaned existence test with coherent/absent/stale/count-coincident/undecodable
  cases plus a Hypothesis byte-perturbation property. `make all` green;
  coderabbit raised only markdown-prose findings in the plan/review docs (no
  code findings), deferred to Work item 5.
- [x] Work item 1 fix round 1 (2026-06-24): stabilized the gate. The
  byte-perturbation property
  (`test_compile_consistent_byte_perturbation_property`) intermittently failed
  `make all` with `DeadlineExceeded` (e.g. 339.18ms vs the default 200ms
  deadline): each example calls `_all_hold_tree`, which materializes a full
  corpus working tree and parses `state.toml`, so per-example runtime exceeds
  the deadline under xdist contention. Added
  `@settings(deadline=None, max_examples=50,
  suppress_health_check=[HealthCheck.function_scoped_fixture])`, matching the
  convention already used by the other filesystem-heavy property tests
  (`test_compile_unit.py:338`, `test_recount_unit.py:288`,
  `test_state_mutators_unit.py:163`). The sibling in-memory property at
  `test_done_predicate.py:290` is correctly left without `@settings`. `make all`
  green (706 passed, 1 skipped); coderabbit `review --agent` returned 0
  findings.
- [x] Work item 2 (2026-06-24): modelled the stale-but-count-matching
  `compiled.md` and the sole-stale-compile / mid-draft-stale trees in the corpus.
  Added `DONE_PREDICATE_SOLE_STALE_COMPILE`, `DONE_PREDICATE_MID_DRAFT_STALE`, and
  `DONE_PREDICATE_OBVIOUS_STALE_COMPILE` to `_done_predicate_specs.py` (token swap
  `word`→`wxrd` preserves the whitespace-split count), exported them, and added
  the `sole_stale_compile_tree`/`mid_draft_stale_tree` fixtures and corpus tests.
  Took the **A-1 option 2** route: under the header-free corpus the header-count
  coincidence is vacuous (`0 == 0`), so the word-total spec plus the Work-item-1
  Hypothesis byte-perturbation property discharge the criterion; this is stated
  plainly in `_done_predicate_specs.py`. `make all` green; coderabbit raised only
  markdown-prose findings in the plan/review docs, deferred to Work item 5.
- [x] Work item 3 (2026-06-24): added the exit-`4` sole-compile carve-out to the
  command body. `_novel_done` now maps the verdict three ways via the
  conservative predicate `_sole_stale_compile(clauses, root)`
  (`failed_clause_names == ("compile_consistent",) and compiled_path.exists()`);
  `_failed_clause_message` distinguishes a *stale* compile (exit `4`) from a
  *missing* one (exit `1`, A-4). Command tests pin all directions: sole stale →
  `4`, mid-draft stale → `1`, stale + each other clause → `1`, absent sole → `1`
  with a "missing" message, undecodable `compiled.md` → `3`. `make all` green.
- [x] Work item 4 (2026-06-24): added the behavioural, snapshot, and e2e suites.
  Two new BDD scenarios (stale → exit 4; mid-draft stale → exit 1) and an
  `exits 4` step; a new sole-stale-compile envelope snapshot beside the existing
  two (verified byte-stable, no churn); a human-mode test asserting the stale and
  missing messages; and two new POSIX-only e2e cases (stale → 4, mid-draft → 1).
  The Work-item-1 Hypothesis byte-perturbation property already covers the
  predicate-truthfulness invariant. `make all` green.
- [x] Work item 5 (2026-06-24): documentation. `docs/users-guide.md` describes the
  content check, adds the exit-`4` row, and replaces the v1 caveat with the
  stale-compile-handling note; `docs/developers-guide.md` rewrites the
  `compile_consistent` subsection to the content comparison, documents the
  conservative exit-`4` carve-out, and updates the clause mapping and the
  "no exit 4" line; `docs/novel-ralph-harness-design.md` §4.2 status note records
  3.1.2's landing with 3.1.3 owning the cross-detector unification.
  `docs/contents.md` indexes execplans by directory pattern (no per-file edit, as
  3.1.1 found). `make all`, `make markdownlint` green; `make nixie` not required
  (no Mermaid touched).

Each work item is independently committable and must pass `make all` before its
commit. Update this section with a timestamp at every stopping point.

## Surprises & discoveries

- The header-free corpus (`draft_body` emits `"word word word"`) made the A-1
  "header count" coincidence vacuous, as the plan anticipated. Option 2 was taken:
  the count-coincident stale spec models the **word-total** coincidence, and the
  Work-item-1 Hypothesis byte-perturbation property discharges the byte-fidelity
  half regardless of header structure. This is stated plainly in
  `_done_predicate_specs.py` so no reviewer reads it as a literal header-count
  test.
- The Work-item-1 Hypothesis property cannot take the function-scoped `tmp_path`
  fixture (a property body receives only Hypothesis-drawn arguments), so it
  rebuilds the tree under a `tempfile.TemporaryDirectory()` per example. That
  same per-example tree materialization (plus a `state.toml` parse) is what blew
  Hypothesis's default 200ms deadline under xdist contention, so the property was
  intermittently red on `make all`; the round-1 fix adds the established
  `@settings(deadline=None, max_examples=50, …)` convention. The lesson: any
  property here whose body calls `_all_hold_tree` is filesystem-heavy and must
  carry the disk-property `@settings`, never rely on the default deadline.
- coderabbit's only findings across the work items were on the planning/review
  markdown (second-person voice, citation style, contributor-specific worktree
  paths); none touched the implementation. The load-bearing worktree paths are
  retained deliberately as the plan's navigation aids (the plan states they are
  worktree-relative); the one clearly-actionable second-person sentence was
  neutralized. The "behavioural" spelling finding was a false positive (the prose
  already reads "behavioural").

## Decision log

- Decision (D-BYTE-COMPARE): the clause realizes the design's "compile-and-hash"
  / "compare its hash" as a **direct byte comparison** of the recomputed
  concatenation against `compiled.md`'s bytes, computing no digest. Rationale:
  the §5.4 detector already does exactly this
  (`compiled.read_text(encoding="utf-8") == expected`, `disk_evidence.py:183`);
  the clause needs only a boolean verdict over the same two in-memory strings, so
  a byte comparison *is* the content equality the design names. Adding `hashlib`
  would introduce a second comparison mechanism the detector does not use, risking
  drift between the two and contradicting design §2.3's "one compile-and-hash
  routine ... so the two can never disagree". The word "hash" in §2.3/§4.2/§4.3
  is the design's name for the content-fidelity check, not a mandate for a
  cryptographic digest. Date/Author: 2026-06-24, planning agent (round 1).

- Decision (D-CLAUSE-FN): the swapped clause lives in **one named function** in
  `done_predicate.py` — `compile_consistent(state, working_dir) -> bool` — whose
  body recomputes `concatenate_drafts(present_draft_bodies(state, working_dir))`
  and compares it byte-for-byte to `compiled.md`, with the explicit "absent
  `compiled.md` → `False`" polarity (preserving the B1 soundness fix). The
  existence-only `compile_consistent_exists(working_dir)` is **removed** (it has
  no other caller: `grep` confirms it is referenced only by `evaluate_done` and
  its 3.1.1 tests), and `evaluate_done` calls the new function. The function's
  body is deliberately the §5.4 detector's recompute-and-compare with the
  inverted absent-file polarity, so roadmap task 3.1.3's
  `compiled_matches_drafts(state, working_dir)` helper is a one-edit drop-in the
  clause will call (passing its "absent → not consistent" polarity). Placing it
  as a standalone function (not inlined into `evaluate_done`) keeps the 3.1.3
  unification a localized edit (R-CLAUSE-FN-LOC). Rationale: the roadmap text
  "Build one compile-and-hash function ... and call it from the
  `compile_consistent` clause" (`roadmap.md:895-898`) is satisfied by reusing the
  *existing* shared `compile_model` routine inside this single clause function;
  3.1.2 does not own the cross-detector unification (that is 3.1.3). Date/Author:
  2026-06-24, planning agent (round 1).

- Decision (D-CARVE): the exit-`4` carve-out is computed in the **command body**
  (`_novel_done.py`), not the pure predicate engine, because exit codes are the
  command/contract layer's concern (the engine returns clause verdicts; the body
  maps them to `ExitCode`). The decision is the single **conservative** predicate

  ```python
  compiled_path = root / "manuscript" / "compiled.md"
  if clauses.all_hold:
      code = ExitCode.SUCCESS                    # exit 0
  elif (
      clauses.failed_clause_names == ("compile_consistent",)
      and compiled_path.exists()
  ):
      code = ExitCode.ACTIONABLE_FINDING         # exit 4 (stale-present compile)
  else:
      code = ExitCode.BENIGN_NEGATIVE            # exit 1
  ```

  where `root` is the `working_dir()` result already bound at the top of
  `_novel_done` (`_novel_done.py:63`). The carve-out therefore fires **iff** the
  *only* false clause is `compile_consistent` **and** `compiled.md` is present —
  i.e. it is *stale-present*, not absent. An **absent** sole-failure compile maps
  to exit `1`, preserving the B1 soundness fix that
  `tests/test_novel_done_command.py:100-111`
  (`test_absent_compile_exits_one_not_zero`) pins; a richer engine verdict is
  **not** introduced (the `DoneClauses` seam is Tolerance-frozen). The
  `compiled.md` stat is a read-only `pathlib` `exists()` call — ADR-001-safe, the
  command writes nothing — and is the **mechanism** that distinguishes
  absent-from-stale, since `DoneClauses` / `failed_clause_names` carry only the
  six booleans and cannot say *why* `compile_consistent` is false (verified
  `done_predicate.py:90-142`). `messages` names the failed clause(s) in every
  case (the stale-present exit-`4` message says "stale compile; regenerate"; the
  absent exit-`1` message says the compile is missing — A-4). Rationale: this
  mirrors `novel-state check`'s `SUCCESS if not verdict else ACTIONABLE_FINDING`
  shape (`novel_state.py:235`) and keeps the engine free of exit-code policy
  (separation the 3.1.1 D-LOC established). The conservative reading is the
  design-correct one: design §4.2 lines 321-328 key the carve-out on "the only
  obstacle is a **stale** `compiled.md`", which an absent compile is not.
  Date/Author: 2026-06-24, planning agent (round 1); revised round 2 to the
  conservative-with-stat reading (resolves review B-1).

- Decision (D-FAULT, inherited): the compile comparison's read faults follow the
  established 3.1.1 boundary — absent `compiled.md` → false clause; absent
  `draft.md` → empty body (already in `present_draft_bodies`); every other read
  fault propagates as a `ValueError`/`OSError` the command body wraps under
  `STATE_INPUT_ERRORS` → `StateInputError` (exit `3`). No new fault policy is
  introduced. Date/Author: 2026-06-24, planning agent (round 1).

- Decision (D-CORPUS-STALE): the stale-compile trees are **new** named specs
  added beside the 3.1.1 `_done_predicate_specs.py` set, not mutations of the
  all-hold or existing failer specs. The stale-but-count-matching tree is the
  all-hold spec with `compiled` set to a verbatim string that (a) preserves the
  per-chapter header count and (b) preserves the whitespace-split token count of
  the true concatenation but (c) alters at least one non-whitespace byte — so it
  is byte-divergent yet count-coincident (R-STALE-MISS). The mid-draft-stale tree
  is a *not-done* drafting tree (e.g. phase not `done`) that *also* carries the
  same stale `compiled`, proving the carve-out does not fire while a drafting
  clause is unmet (R-CARVE-MISFIRE). Rationale: D-CORPUS in 3.1.1 keeps existing
  specs byte-identical to avoid snapshot churn; this continues that discipline.
  Date/Author: 2026-06-24, planning agent (round 1).

- Decision (D-EXTERNAL): no firecrawl-sourced library behaviour is load-bearing
  in 3.1.2. Rationale: this task adds no new external surface. It reuses the
  cyclopts 4.18.0 runner/envelope path (`uv.lock`) already pinned by
  `tests/test_contract_runner.py` / `tests/test_cyclopts_contract.py` (3.1.1
  D-EXTERNAL verified the `exit_on_error=False` / `result_action="return_value"`
  seam against the cyclopts v4 API docs,
  `cyclopts.readthedocs.io/en/v4.4.1/api.html`); the only new behaviour is the
  exit-`4` mapping, which is internal to the command body and pinned by tests.
  No firecrawl claim is pinned beyond confirming the existing pattern, which the
  existing tests already gate. The cuprum non-use is confirmed against the locked
  source (Constraints "No external process"). Date/Author: 2026-06-24, planning
  agent (round 1).

## Outcomes & retrospective

Delivered exactly the planned scope in five atomic commits, each gated by
`make all`:

1. Swapped `compile_consistent` to the shared content comparison, retiring
   `compile_consistent_exists`.
2. Modelled the sole-stale-compile, mid-draft-stale, and obvious-stale specs in
   the corpus.
3. Added the conservative exit-`4` carve-out to the command body.
4. Added the behavioural, snapshot, and e2e suites for the divergence and the
   exit-`4`/exit-`1` split.
5. Closed the v1 stale caveat across the user and developer guides and the design
   status note.

No Tolerance was breached: the change touched well under 12 files, added no
dependency, did not touch the §5.4 detector (3.1.3's job), and expressed the
carve-out without an undecided fork (the conservative reading held). The
absent-vs-stale distinction proved the load-bearing subtlety: gating the carve-out
on `compiled.md` existing keeps the 3.1.1 B1 soundness fix intact while still
surfacing a regenerable stale compile as exit `4`. The clause and the §5.4
detector now share one routine, so 3.1.3's unification is a localized drop-in.

## Context and orientation

A reader new to this repository needs the following map. All paths are
repository-relative to the worktree root
(`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-2`).

The harness is a set of five console-scripts in the `novel_ralph_skill` package
(design §4). `novel-done` already exists (delivered by roadmap task 3.1.1,
`docs/execplans/roadmap-3-1-1.md`): it is a read-only Cyclopts application driven
through the shared `contract.runner.run` wrapper, evaluating six done clauses
against disk and emitting the common JSON envelope. The pieces this task builds
on are all in place and stable:

- `novel_ralph_skill/state/done_predicate.py` — the pure per-clause engine.
  `DoneClauses` (frozen, six booleans, `all_hold` / `failed_clause_names` /
  `as_result`), one pure function per clause, and `evaluate_done(state,
  working_dir) -> DoneClauses`. The `compile_consistent` slot is currently
  `compile_consistent_exists(working_dir)` (`:211-220`) — the existence-only half
  this task swaps. The fault boundary (absent → benign; everything else
  propagates) is documented at `:26-34`.
- `novel_ralph_skill/state/compile_model.py` — **the shared compile-and-hash
  routine**. `present_draft_bodies(state, working_dir) -> list[str]` (`:38-78`)
  reads each manifest chapter's `draft.md` in ascending order (absent →
  `""`, every other fault propagates); `concatenate_drafts(drafts) -> str`
  (`:81-101`) joins them with the single `DRAFT_SEPARATOR = "\n\n"` (`:34`).
  These are exactly what the new clause must reuse (Constraints).
- `novel_ralph_skill/state/disk_evidence.py` — `_check_compiled_matches_drafts`
  (`:167-188`): the §5.4 detector that recomputes
  `concatenate_drafts(present_draft_bodies(...))` and compares bytes to
  `compiled.md`, treating an **absent** `compiled.md` as vacuously satisfied
  (`:180-181`). This is the opposite absent-file polarity to the clause; 3.1.2
  must not touch this detector (3.1.3 unifies them).
- `novel_ralph_skill/commands/_novel_done.py` — the command body
  (`_novel_done() -> CommandOutcome`, `:41-80`) and `build_app()` (`:83-111`).
  The body resolves `working_dir()`, loads state via `_load_or_state_error`,
  runs `evaluate_done` wrapped under `STATE_INPUT_ERRORS`, and maps `all_hold` →
  `SUCCESS` else `BENIGN_NEGATIVE` (`:70-80`). This is the mapping the exit-`4`
  carve-out extends.
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode`
  (`SUCCESS=0`, `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`) and `is_ok`. `ACTIONABLE_FINDING` already drives
  `novel-state check`'s exit `4` (`novel_state.py:235`).
- `tests/working_corpus/` — the §1.3.2 fixture corpus. `_specs.py` declares
  `ChapterSpec`/`WorkingTreeSpec` (the `compiled: str | None` field models
  `None` = no file, `COMPILED_AUTO` = hash-equal concatenation, any other string
  = verbatim/stale bytes, `:198, 261-264`); `_builder.py` materializes a tree;
  `_done_predicate_specs.py` (3.1.1) holds the all-hold spec and the per-clause
  failers; `_done_predicate_oracle.py` holds the disk-reading twins;
  `corpus_done_predicate_fixtures.py` is the pytest plugin.
- Existing `novel-done` tests (all green): `tests/test_done_predicate.py`
  (engine unit + property), `tests/test_novel_done_command.py` (exit codes),
  `tests/test_novel_done_bdd.py` + `tests/features/novel_done.feature` +
  `tests/steps/novel_done_steps.py` (behavioural), `tests/test_novel_done_snapshots.py`
  (envelope snapshots), `tests/test_novel_done_e2e.py` (installed-wheel e2e).

Authoritative documents (read before coding the matching work item):

- Design: `docs/novel-ralph-harness-design.md` §1 (boundary), §2.3 (verification
  scope / compile fidelity / the shared compile-and-hash routine, lines 106-129),
  §3.2 (exit codes), §3.3 (checker/mutator segregation), §4.2 (`novel-done`,
  including the exit-`4` carve-out and the bounded-payload rule, lines 302-361),
  §4.3 (`novel-compile` / the shared compile-and-hash routine, lines 364-385),
  §5.4 (disk-authoritative reconciliation and the `compiled-matches-drafts`
  finding, lines 513-585).
- Reference predicate: `skill/novel-ralph/references/done-conditions.md`
  ("Novel-level predicate", "Failure modes" — the `compiled.md` stale mode at
  line 214).
- ADRs: `docs/adr-001-deterministic-judgemental-boundary.md`,
  `docs/adr-003-shared-interface-contract.md`,
  `docs/adr-005-command-surface-five-scripts.md`,
  `docs/adr-006-console-scripts-e2e-posix-policy.md`.
- Standards: `docs/scripting-standards.md` (Cyclopts/pathlib conventions),
  `docs/developers-guide.md` (the done-predicate subsection at lines 530-575, the
  twin/oracle discipline, "Invariant validation"), `AGENTS.md` (gates, testing
  rules, module cap, spelling).
- Predecessor plan: `docs/execplans/roadmap-3-1-1.md` (R-STALE, D-COMPILE-
  EXISTENCE, D-CLAUSES, D-FAULT, D-CORPUS, D-TWIN — the decisions this task
  builds on and partly supersedes).

Terms defined: a *clause* is one of the six named done conditions. The
*predicate* is the conjunction of all six. A *checker* reads and reports and
never writes. The *envelope* is the common JSON object every command emits. The
*benign negative* (exit `1`) is "not yet done", which the harness loops on. The
*actionable finding* (exit `4`) is a stale compile the harness must regenerate.
The *unsoundness window* (R-STALE) is the present-but-stale `compiled.md`
interval this task closes.

## Plan of work

Five ordered work items, each a single commit gated by `make all`. Write the
failing test(s) first (red), then the implementation (green), then refactor.

### Work item 1 — swap the `compile_consistent` clause to the shared content comparison

**Implements:** design §2.3 (compile fidelity / the one shared routine, lines
117-122), §4.2 (the content-driven `compile_consistent` clause, lines 349-356),
§4.3 (the shared compile-and-hash routine, lines 383-385); roadmap 3.1.2
(`roadmap.md:895-898`); ADR-001 (read-only boundary). **Read first:** design
§2.3, §4.2, §4.3; `compile_model.py:34-101` (`present_draft_bodies`,
`concatenate_drafts`, `DRAFT_SEPARATOR`); `disk_evidence.py:167-188` (the
detector's recompute-and-compare and its absent-file polarity);
`done_predicate.py:211-294` (the existence-only clause and `evaluate_done`).
**Skills:** `python-router` → `python-errors-and-logging` (the propagate-vs-
absorb fault boundary), `python-data-shapes` (the verdict function shape);
`python-verification` → `hypothesis` (the predicate-truthfulness invariant).

In `novel_ralph_skill/state/done_predicate.py`:

- Add `compile_consistent(state, working_dir) -> bool` (D-CLAUSE-FN): if
  `manuscript/compiled.md` is **absent**, return `False` (preserving the B1
  soundness fix); otherwise read its bytes as UTF-8 and return whether they equal
  `concatenate_drafts(present_draft_bodies(state, working_dir))` (D-BYTE-COMPARE).
  Reuse `compile_model.present_draft_bodies` / `concatenate_drafts` — do not
  re-derive the join or the read rule (Constraints). The docstring states it is
  the content comparison (the hash half 3.1.1 deferred), names roadmap 3.1.3 as
  the owner of the cross-detector unification, and records the inverted
  absent-file polarity versus the §5.4 detector.
- Remove `compile_consistent_exists(working_dir)` (no other caller; D-CLAUSE-FN)
  and point `evaluate_done`'s `compile_consistent=` slot at the new function.
- Keep the import of `present_draft_bodies` / `concatenate_drafts` from
  `compile_model` (the module already imports `_chapter_dir_name` from
  `_disk_paths`; the new import is from `compile_model`).

The fault boundary is unchanged (D-FAULT): only `FileNotFoundError` on
`compiled.md` is absorbed (→ `False`); `present_draft_bodies` already absorbs an
absent `draft.md` and propagates everything else.

Tests (this commit): extend `tests/test_done_predicate.py`. First, **remove or
rewrite** the now-orphaned `test_compile_consistent_exists_present_and_absent`
(`tests/test_done_predicate.py:135`) and its module-level
`from ... import compile_consistent_exists` (`:32`) — `compile_consistent_exists`
is deleted in this work item, so leaving the import yields a dangling reference
and a red `make all` on the first commit (A-2). Replace it with the new
`compile_consistent` content-comparison tests below.

- `compile_consistent` is `False` when `compiled.md` is **absent** (R-EXISTENCE-
  REGRESS); `True` when `compiled.md` byte-equals the recomputed concatenation;
  `False` when present but byte-divergent — including the **count-coincident**
  case (a body with the same `len(text.split())` token count but altered
  non-whitespace bytes), pinning the predicate-truthfulness property (R-STALE-
  MISS). Replace/adapt the 3.1.1 R-STALE test that asserted a present-but-stale
  compile was *true* (existence-only): it must now assert *false*, making the
  behaviour change visible.
- An undecodable `compiled.md` body raises (propagates) for the command layer to
  map to exit `3` (R-FAULT-COMPILE).
- A `hypothesis` property over randomly perturbed compiled bodies: for any
  perturbation that changes a non-whitespace byte, `compile_consistent` is
  `False`; for the exact concatenation it is `True`. Per `python-verification`,
  Hypothesis is the right adversary (an invariant over a range of perturbations);
  CrossHair/mutmut are not needed here.

### Work item 2 — model the stale-but-count-matching and mid-draft-stale trees in the corpus

**Implements:** design §2.3 / §1.3.2 corpus success criterion (a stale compile
that header count and word total cannot betray is still caught); roadmap 3.1.2
success criteria (`roadmap.md:906-910`). **Read first:**
`tests/working_corpus/_specs.py:53, 195-264` (the `compiled` field and
`_resolve_compiled`/`draft_body`/`concatenate_drafts`); `_done_predicate_specs.py`
(the all-hold spec and failer pattern); `developers-guide.md` twin/oracle
discipline. **Skills:** `python-router` → `python-testing` (corpus fixtures, the
conftest re-export rule, `dataclasses.replace` spec derivation).

Add **new** named specs to `_done_predicate_specs.py` (D-CORPUS-STALE), exported
through `tests/working_corpus/__init__.py` `__all__` and surfaced as conftest
fixtures via `corpus_done_predicate_fixtures.py`, **without mutating** the
all-hold spec or the existing failers:

- **sole-stale-compile** (the load-bearing exit-`4` fixture): the all-hold spec
  with `compiled` set to a **count-coincident but byte-divergent** body — same
  per-chapter header count, same whitespace-split token count as the true
  concatenation, at least one altered non-whitespace byte. Every other clause
  holds, so `compile_consistent` is the *sole* false clause. Provide a small
  helper that derives this body from the all-hold drafts (e.g. swap one
  `"word"` token for a different equal-length token) so the count-coincidence is
  mechanical and self-evident.
- **mid-draft-stale-compile**: a *not-done* tree (a drafting clause unmet — e.g.
  `phase_current` not `done`, or one chapter unflagged) that **also** carries the
  same count-coincident stale `compiled`, so `compile_consistent` is false
  *alongside* a drafting clause. Proves the carve-out stays at exit `1` mid-draft
  (R-CARVE-MISFIRE).
- Optionally a **byte-divergent-and-count-divergent** stale spec (a plainly
  wrong compile) as the obvious-divergence control beside the subtle one.

**On the "header count" half of the success criterion (A-1).** Roadmap success
(`roadmap.md:906`) and design §2.3 (line 121) name the property as a stale
compile whose **header count *and* word total** coincidentally match the drafts
still being caught. The corpus `draft_body` (`_specs.py:222-231`) emits
**header-free** bodies (`"word word word"`), so every corpus draft carries
**zero** markdown headers and the "header count" coincidence is vacuously
`0 == 0` on both sides — it cannot be genuinely stressed by a header-free spec.
This plan discharges the criterion two ways, and the implementer must do **one**
of them (preferring the first):

1. **Add a non-zero-header count-coincident spec.** Introduce a small spec whose
   drafts *and* whose stale `compiled` both carry the **same non-zero count of
   `#`-prefixed lines** and the same whitespace-split token count, with at least
   one altered non-whitespace byte. This requires a header-bearing draft body
   (either extend `draft_body` to optionally prefix a `# heading` line, or add a
   sibling `draft_body_with_headers` helper), so the header-count coincidence is
   genuinely exercised rather than trivially zero. Pin a test asserting both the
   stale body and the drafts have the same non-zero header count *and* the same
   token count, yet the clause reports divergence.
2. **State the vacuity explicitly** in the plan and the test docstrings: under
   the header-free corpus the "header count" half is vacuous, and the
   word-total-coincident spec plus the Work-item-1 Hypothesis byte-perturbation
   property (which falsifies any non-whitespace change regardless of header
   structure) jointly discharge the roadmap criterion. Choose this only if
   option 1 is disproportionate; if chosen, the plan must say so plainly so no
   reviewer believes the literal "header count" coincidence was tested.

Tests (this commit): a focused corpus test module (extend
`tests/test_working_corpus_done_predicate.py`) asserting: the sole-stale-compile
tree materializes a `compiled.md` that is *not* the concatenation yet has the
same token count and header count as the drafts (the R-STALE-MISS precondition);
the mid-draft-stale tree has at least one drafting clause unmet *and* a stale
compile; and the existing all-hold / failer specs materialize byte-identically
to before (no churn). Pin the new specs against the corpus oracle's compiled
twin where one exists, mirroring the D-TWIN discipline.

### Work item 3 — add the exit-`4` sole-compile carve-out to the command body

**Implements:** design §4.2 (the exit-`4` carve-out, lines 318-327), §3.2;
ADR-003. **Read first:** `_novel_done.py:41-80` (the current `all_hold` →
`SUCCESS`/`BENIGN_NEGATIVE` mapping); `novel_state.py:235` (the
`SUCCESS if not verdict else ACTIONABLE_FINDING` precedent);
`exit_codes.py:32-34` (`ACTIONABLE_FINDING`). **Skills:** `python-router` →
`python-errors-and-logging` (exit-code mapping), `python-types-and-apis` (the
`CommandOutcome` shape).

In `novel_ralph_skill/commands/_novel_done.py` `_novel_done()` (D-CARVE): after
`evaluate_done`, replace the two-way `all_hold` branch with a three-way mapping
keyed on the **conservative** carve-out predicate. `root` (the `working_dir()`
result) is already bound at the top of the body (`_novel_done.py:63`); derive
`compiled_path = root / "manuscript" / "compiled.md"` and branch:

- every clause holds → `ExitCode.SUCCESS`, `messages=["novel is done"]`;
- `clauses.failed_clause_names == ("compile_consistent",)` **and**
  `compiled_path.exists()` → `ExitCode.ACTIONABLE_FINDING` (exit `4`), `messages`
  naming the stale compile (e.g. "compile_consistent is false (stale compile;
  regenerate)") — this is the *stale-present* carve-out;
- otherwise → `ExitCode.BENIGN_NEGATIVE` (exit `1`), `messages` naming the failed
  clauses (the existing behaviour). When the sole failed clause is
  `compile_consistent` but `compiled.md` is **absent**, the message should say
  the compile is *missing* rather than stale (A-4: "compile_consistent is false
  (compiled.md missing)"), so human-mode output is not misleading at the exact
  boundary the carve-out turns on; the harness never parses `messages` (ADR-003).

The `compiled_path.exists()` stat is the **mechanism** the carve-out needs: it is
the only way the command body can tell a *stale-present* compile (exit `4`) from
an *absent* one (exit `1`), because `DoneClauses` / `failed_clause_names` carry
only the six booleans and do not record *why* `compile_consistent` is false
(verified `done_predicate.py:90-142`). The stat is a read-only `pathlib`
`exists()` call — ADR-001-safe, the command writes nothing. The absent
sole-failure case must continue to exit `1`, matching the existing soundness test
`tests/test_novel_done_command.py:100-111`
(`test_absent_compile_exits_one_not_zero`), which the Tolerances forbid changing.

`result` stays the six per-clause booleans in every case. Update the module
docstring (`:10-16`) — it currently states "No 3.1.1 path produces exit `4`"; in
3.1.2 the sole-stale-*present*-compile path *does* (the absent case still exits
`1`). Keep the body under the 400-line cap.

Tests (this commit): extend `tests/test_novel_done_command.py` (drive
`build_app()` in-process over corpus trees under `tmp_path`, chdir so `working/`
resolves):

- the all-hold tree → exit `0` (unchanged);
- the sole-stale-compile tree → exit `4` with `ok: false` and
  `compile_consistent: false` the only false clause (R-CARVE-MISFIRE forward);
- the mid-draft-stale tree → exit `1` (R-CARVE-MISFIRE reverse), and, for
  thoroughness, a stale compile paired with *each other* single unmet clause →
  exit `1` (so the carve-out is exclusive);
- an **absent**-`compiled.md` otherwise-complete tree → exit `1` (**not** `4`):
  with the conservative carve-out, a sole `compile_consistent` failure caused by
  an *absent* compile stays exit `1`, because the carve-out gates on
  `compiled.md` *existing* (a stale present compile). This is the existing
  soundness behaviour already pinned by `test_absent_compile_exits_one_not_zero`
  (`tests/test_novel_done_command.py:100-111`), which this work item must keep
  green (the Tolerances forbid changing it). Add an explicit assertion that this
  tree's exit is `BENIGN_NEGATIVE` and `compile_consistent` is its sole false
  clause, so the absent-vs-stale split is pinned on both sides;
- the **stale-present**-`compiled.md` sole-failure tree → exit `4` (the
  carve-out), the absent-vs-stale counterpart of the bullet above;
- a missing/unparseable `state.toml` → exit `3`; an undecodable `compiled.md` →
  exit `3` (R-FAULT-COMPILE); a stray positional → exit `2`.

(The carve-out predicate is therefore exactly:
`clauses.failed_clause_names == ("compile_consistent",) and
(root / "manuscript" / "compiled.md").exists()` → exit `4`; this is the single
explicit condition in the body, recorded identically in D-CARVE, R-CARVE-MISFIRE,
and the Interfaces section.)

### Work item 4 — the behavioural, property, snapshot, and e2e suites

**Implements:** design §2.3 (combinatorial surface, lines 125-129), §4.2 (the
exit-`4`/exit-`1` split); AGENTS.md testing rules. **Read first:** AGENTS.md
"Python verification and testing"; `docs/adr-006` (POSIX e2e policy);
`tests/features/novel_done.feature` + `tests/steps/novel_done_steps.py`;
`tests/test_novel_done_snapshots.py`; `tests/test_novel_done_e2e.py`. **Skills:**
`python-router` → `python-testing` (BDD, snapshot, parametrization);
`hypothesis` if a further property emerges.

Add/extend:

- `tests/features/novel_done.feature` + steps: a named scenario
  "a stale compile in an otherwise-complete tree is an actionable finding"
  driving the sole-stale-compile tree to **exit 4** with `compile_consistent`
  the only false clause; and "a stale compile mid-draft stays benign" driving the
  mid-draft-stale tree to **exit 1**. These are the literal roadmap 3.1.2 success
  criteria (`roadmap.md:906-910`). Register like the existing scenarios.
- A machine-mode envelope **snapshot** (`syrupy`) for the sole-stale-compile tree
  (exit `4`, `ok: false`, the six-key `result` with `compile_consistent: false`),
  added **beside** the existing all-hold and one-clause-fails snapshots
  (R-SNAPSHOT-CHURN); pair it with a semantic per-clause + exit-code assertion so
  the snapshot is not the only coverage (AGENTS.md snapshot rule). Assert the
  existing snapshots are byte-stable.
- A human-mode presence assertion: `--human` over the stale-present tree renders
  without error and names the stale compile; and `--human` over the
  absent-compile sole-failure tree renders without error and reports the compile
  is *missing* rather than stale (A-4), so the exit-`1` boundary is not
  misleading. (`messages` is human prose the harness never parses, ADR-003.)
- An e2e proof (extend `tests/test_novel_done_e2e.py`, POSIX-only per ADR-006,
  marked `slow`): the installed `novel-done` console-script over a real
  `working/` tree with a sole stale `compiled.md` exits `4`; over a mid-draft
  stale tree exits `1`. (Materialize the stale compile by writing the
  count-coincident body the corpus uses.)

### Work item 5 — documentation and the plan's outcomes

**Implements:** AGENTS.md "Project documentation"; the R-STALE closure; the
exit-`4` carve-out disclosure. **Read first:** `docs/users-guide.md:305-335`
(the `novel-done` section and its v1 caveat); `docs/developers-guide.md:530-575`
(the done-predicate subsection and the `compile_consistent` existence-only note);
`docs/novel-ralph-harness-design.md:308-313` (the §4.2 implementation-status
note); `docs/contents.md`. **Skills:** `en-gb-oxendict` (spelling), `execplans`
(keep this plan current).

- `docs/users-guide.md`: rewrite the **v1 caveat** (lines 328-334) — the stale
  window is now **closed**: `compile_consistent` checks the compile *content*, so
  a present-but-stale `compiled.md` is caught. Add the exit-`4` row to the
  `novel-done` exit-code list: "`4` — every clause holds *except*
  `compile_consistent`; the manuscript is otherwise complete and the only
  obstacle is a stale compile, which the harness regenerates (matching
  `novel-compile --check`)". Update the `compile_consistent` bullet (line 315) to
  drop the "see the v1 caveat" qualifier and describe the content check.
- `docs/developers-guide.md`: rewrite the "`compile_consistent` is the existence
  half only" subsection (lines 560-566) — it is now the **full content
  comparison**, reusing `compile_model.present_draft_bodies` /
  `concatenate_drafts` (the same routine the §5.4 detector uses), with the
  absent-file polarity inverted relative to that detector (absent → not
  consistent here; vacuously satisfied there) and roadmap 3.1.3 named as the
  owner of the cross-detector unification. Update the clause mapping line (542)
  from "*exists*" to the content comparison. Document the exit-`4` carve-out and
  its conservative "stale-present only, absent stays `1`" reading (D-CARVE).
  Update the "No 3.1.1 path emits exit `4`" line (575) to note 3.1.2's
  sole-stale-compile exit-`4` path.
- `docs/novel-ralph-harness-design.md`: update the §4.2 implementation-status
  note (lines 308-313) — the compile-and-hash half and the exit-`4` carve-out now
  **land** (roadmap 3.1.2), with 3.1.3 still owning the cross-detector
  unification. Otherwise leave the design body unchanged.
- `docs/contents.md`: confirm this execplan is indexed by the existing
  `roadmap-<step>-<task>.md` directory pattern (3.1.1 found no per-file edit was
  needed; verify the same here).
- Update this plan's `Progress`, `Surprises & Discoveries`, `Decision Log`,
  `Outcomes & Retrospective`, and Status.

Validation for this work item additionally runs `make markdownlint` and
`make nixie` (the latter only if any Mermaid diagram is touched; none is
expected).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-2`.

1. Confirm the branch and a clean tree:

   ```console
   $ git branch --show-current
   roadmap-3-1-2
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

3. Commit each work item separately with an en-GB Oxford-spelling message naming
   the roadmap task (3.1.2) and the design section it implements. Do not begin
   implementation until this plan is approved.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Stale compile caught by content (the predicate-truthfulness property).** Over
  an otherwise-complete tree whose `compiled.md` has the *same* header count and
  word total as the drafts but altered non-whitespace bytes, `novel-done` reports
  `compile_consistent: false` and exits `4`. The new property and behavioural
  tests fail before Work item 1 and pass after.
- **The exit-`4`/exit-`1` carve-out.** A tree whose *only* unmet clause is a
  stale present `compiled.md` exits `4` (`ok: false`); a tree with a stale
  compile *and* any unmet drafting clause exits `1`; a tree with an *absent*
  `compiled.md` as its only failure exits `1` (the conservative reading,
  D-CARVE). No tree with all clauses holding exits anything but `0`.
- **Bounded payload.** The `result` reports one `compile_consistent` boolean
  regardless of chapter count; a test asserts the envelope shape is independent
  of the number of chapters.
- **One shared routine.** The clause reuses `present_draft_bodies` /
  `concatenate_drafts`; a test pins the clause's verdict equal to the §5.4
  detector's recompute **only over trees with a present `compiled.md`**, where
  the two polarities agree, so the two cannot disagree on a present compile. The
  **absent**-`compiled.md` trees are pinned *separately* (A-3): the clause
  returns `False` there while the detector is *vacuously satisfied*
  (`disk_evidence.py:180-181`), the one input where the two are *designed* to
  disagree — so the equality test must explicitly exclude absent-compile trees,
  and the absent case is asserted on each side independently (R-EXISTENCE-REGRESS).
- **Exit-code contract intact.** Missing/unparseable `state.toml` → `3`;
  undecodable `compiled.md` → `3`; stray positional → `2`; all-hold → `0`.
- **Envelope shape.** The machine-mode snapshot pins the exit-`4`
  sole-stale-compile envelope (six-key `result`, `schema_version: 1`,
  `ok: false`). `--human` renders without error and names the stale compile.
- **Installed command.** On POSIX, the built wheel's `novel-done` console-script
  exits `4` over a real sole-stale-compile tree and `1` over a mid-draft stale
  tree (`tests/test_novel_done_e2e.py`, marked `slow`).

Quality criteria ("done" means):

- Tests: the new/updated unit, behavioural, property, snapshot, and e2e suites
  pass; the whole suite passes under `make test` (xdist; the per-test 30s timeout
  is ample for these filesystem-only tests).
- Lint/typecheck: `make lint` (ruff, `interrogate`, pylint) and `make typecheck`
  (`ty`) report no findings.
- Markdown: `make markdownlint` passes; `make nixie` passes if any Mermaid is
  touched (none expected).

Quality method: `make all` (and `make markdownlint`/`make nixie` for the
documentation work item) is the single gate run before every commit.

## Idempotence and recovery

`novel-done` is read-only, so re-running it is always safe and never mutates the
tree. The implementation steps are ordinary source edits under version control;
to retry a work item, reset the working tree (`git restore`) and re-apply. No
step is destructive and no backup is required. The corpus extensions (Work item
2) add only **new** named specs, so a half-applied change leaves every existing
fixture and snapshot byte-identical.

## Artefacts and notes

Key reuse points the implementer must not reinvent:

- `novel_ralph_skill/state/compile_model.py:38-101` — `present_draft_bodies` and
  `concatenate_drafts`, the **single shared compile-and-hash routine** the new
  clause reuses (do not re-derive the join, the read rule, or the separator).
- `novel_ralph_skill/state/disk_evidence.py:167-188` —
  `_check_compiled_matches_drafts`, the §5.4 detector whose recompute-and-compare
  the clause mirrors with the *inverted* absent-file polarity. **Do not modify
  it** (3.1.3 unifies the two).
- `novel_ralph_skill/state/done_predicate.py:211-294` — the existence-only clause
  (`compile_consistent_exists`) Work item 1 replaces, and `evaluate_done`.
- `novel_ralph_skill/commands/_novel_done.py:41-80` — the `all_hold` →
  `SUCCESS`/`BENIGN_NEGATIVE` mapping Work item 3 extends with the exit-`4`
  carve-out.
- `novel_ralph_skill/commands/novel_state.py:235` — the
  `SUCCESS if not verdict else ACTIONABLE_FINDING` precedent for the carve-out.
- `tests/working_corpus/_specs.py:53, 195-264` — the `compiled` field and
  `_resolve_compiled` (a verbatim string models a stale compile;
  `COMPILED_AUTO` the coherent one) the new specs use.
- `tests/working_corpus/_done_predicate_specs.py` — the all-hold and failer specs
  the new stale-compile specs sit beside (without mutation).

## Interfaces and dependencies

Be prescriptive. At the end of this task these must exist:

In `novel_ralph_skill/state/done_predicate.py` (the existence-only
`compile_consistent_exists` is removed):

```python
def compile_consistent(
    state: "novel_ralph_skill.state.schema.State",
    working_dir: "pathlib.Path",
) -> bool:
    """Return whether compiled.md is the ordered concatenation of the drafts.

    Absent compiled.md -> False (an absent compile is never "done"). Present and
    byte-equal to concatenate_drafts(present_draft_bodies(...)) -> True; present
    and divergent -> False. Reuses the shared compile_model routine; the opposite
    absent-file polarity to the §5.4 detector is reconciled by roadmap task 3.1.3.
    """
```

In `novel_ralph_skill/commands/_novel_done.py`, `_novel_done()` maps the clause
verdict to three exit codes via the single conservative carve-out predicate (the
same one D-CARVE and R-CARVE-MISFIRE state):

```python
compiled_path = root / "manuscript" / "compiled.md"  # root == working_dir()
if clauses.all_hold:
    code = ExitCode.SUCCESS              # exit 0
elif (
    clauses.failed_clause_names == ("compile_consistent",)
    and compiled_path.exists()
):
    code = ExitCode.ACTIONABLE_FINDING   # exit 4: stale-present compile
else:
    code = ExitCode.BENIGN_NEGATIVE      # exit 1 (includes absent-compile case)
```

The `compiled_path.exists()` stat is read-only (ADR-001-safe) and is the
mechanism that separates a *stale-present* compile (exit `4`) from an *absent*
one (exit `1`); `DoneClauses` carries only the six booleans and cannot make that
distinction (`done_predicate.py:90-142`). An absent sole-failure compile stays
exit `1`, matching `test_absent_compile_exits_one_not_zero`.

Dependencies: runtime stays `cyclopts` + `tomlkit` (`pyproject.toml:8`; no
change). Dev stays `pytest`, `pytest-bdd`, `hypothesis`, `syrupy`,
`pytest-timeout`, `pytest-xdist` (no change). cuprum is not used (no external
process; design §4 line 269; confirmed against the locked cuprum source
`cuprum/catalogue.py`, `cuprum/program.py`).

## Revision note

Round 1 (2026-06-24). Initial plan. Pins, against the LOCKED sources verified
this round:

- the **shared compile-and-hash routine** is
  `compile_model.present_draft_bodies` plus `concatenate_drafts` (verified
  `compile_model.py:38-101`), already used by the §5.4 detector
  (`disk_evidence.py:167-188`) — so 3.1.2 reuses, not reinvents (D-BYTE-COMPARE,
  D-CLAUSE-FN);
- the design's "hash" is realized as the detector's existing **byte comparison**;
  no `hashlib` digest is introduced (D-BYTE-COMPARE);
- the **3.1.2 / 3.1.3 boundary**: 3.1.2 swaps the clause and adds the carve-out;
  3.1.3 (separate task) unifies the two comparisons into one helper. 3.1.2 does
  not touch the §5.4 detector;
- the **exit-`4` carve-out** is the conservative reading — exit `4` only when the
  *sole* unmet clause is `compile_consistent` **and** `compiled.md` *exists* (a
  stale present compile); an absent compile stays exit `1` (D-CARVE), keeping the
  "regenerate the stale compile" semantics exact;
- **cuprum is not used**, confirmed against the locked source
  (`cuprum/catalogue.py`, `cuprum/program.py`);
- **no firecrawl-sourced behaviour is load-bearing** (D-EXTERNAL): the cyclopts
  runner/envelope seam is the one 3.1.1 already pinned against the cyclopts v4
  API docs; this task adds no new external surface.

Round 2 (2026-06-24). Resolves the round-1 Logisphere review
(`docs/execplans/roadmap-3-1-2.review-r1.md`). Changes:

- **B-1 (blocking) — carve-out predicate settled and made implementable.** The
  document had stated the exit-`4` carve-out two incompatible ways: a *pure*
  `failed_clause_names == ("compile_consistent",)` predicate (old D-CARVE and
  R-CARVE-MISFIRE) and a *conservative* "and `compiled.md` exists" predicate
  (Work item 3 and Interfaces). The pure predicate would have regressed the named
  soundness test `tests/test_novel_done_command.py:100-111`
  (`test_absent_compile_exits_one_not_zero`), which pins an absent sole-failure
  compile to exit `1` and which the Tolerances freeze. The plan now adopts the
  **conservative** reading everywhere
  (`clauses.failed_clause_names == ("compile_consistent",) and
  (root / "manuscript" / "compiled.md").exists()`), stated **identically** in
  D-CARVE, R-CARVE-MISFIRE, Work item 3, and the Interfaces section, with the
  contradictory pure-predicate phrasing deleted. The **mechanism** — a read-only
  `compiled_path.exists()` stat in the command body, `root` already bound at
  `_novel_done.py:63` — is now specified explicitly (it is the only way the body
  can tell *absent* from *stale-present*, since `DoneClauses` carries only the six
  booleans, verified `done_predicate.py:90-142`). It is ADR-001-safe (read-only).
- **A-2** — Work item 1 now explicitly lists the orphaned
  `test_compile_consistent_exists_present_and_absent`
  (`test_done_predicate.py:135`) and its import (`:32`) for removal/rewrite, so
  the first commit does not go red on a dangling import.
- **A-1** — Work item 2 now states the "header count" half is vacuous under the
  header-free corpus (`draft_body` emits `"word word word"`, zero headers) and
  requires the implementer to either add a non-zero-header count-coincident spec
  (preferred) or state the vacuity plainly and lean on the word-total spec plus
  the Hypothesis byte-perturbation property.
- **A-3** — the "one shared routine" acceptance bullet now says the
  clause-vs-detector equality test runs **only over present-compile trees**, with
  the absent-compile trees pinned separately (clause→False, detector→vacuous).
- **A-4** — D-CARVE and Work items 3 and 4 now specify the absent sole-failure
  exit-`1` message reports the compile is *missing* rather than stale, so
  human-mode output is not misleading at the carve-out boundary.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge review and audit of step 3.1 (`review:3.1.2`, `audit:3.1.2`). Execute
each as a small addendum pass — no plan or design-review cycle: make the change,
run `make all` (plus `make markdownlint`/`make nixie` for Markdown),
`coderabbit review --agent`, commit, and tick the matching roadmap sub-task on
merge. The substantial, cross-cutting follow-ups raised against this task were
re-routed off it rather than folded here: the "compile-and-hash"→byte-comparison
documentation reconciliation (`audit:3.1.2`, merged with `audit:3.1.3`) to a new
roadmap step 7.17 (deferred documentation-truthfulness hardening); the
`manuscript/compiled.md` path centralization in `_disk_paths` (`audit:3.1.2`, and
the related `review:3.1.2` fold-the-path-constant proposal) is already owned by
the open roadmap task 7.10.3, whose Success clause requires that no site
open-codes the `compiled.md` leaf, so it is not re-filed; the compile-present
companion that avoids triple-statting `compiled.md` (`audit:3.1.2`) to roadmap
task 7.10.5; and the disk-bound Hypothesis deadline-profile work (`review:3.1.2`,
two near-identical proposals merged) to a new roadmap step 7.18. The one below is
the small, localized fix tied to this task's corpus.

- [x] 3.1.2.1 — Pin or drop the unused `DONE_PREDICATE_OBVIOUS_STALE_COMPILE`
  corpus spec (from review:3.1.2, low; two near-identical proposals merged). The
  obvious byte-and-count-divergent stale spec is exported through the corpus
  `__all__` but asserted on by no test, so it validates nothing while remaining
  on the corpus public surface and misleads readers into assuming the obvious
  divergent case is covered. Either pin it with a focused test (the
  `compile_consistent` clause reports divergence and the otherwise-complete tree
  exits 4) or drop it from the corpus so the exports stay load-bearing.
  Test/corpus-only. Gate with `make all`.
